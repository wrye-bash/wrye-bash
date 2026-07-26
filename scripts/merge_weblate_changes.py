#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# GPL License and Copyright Notice ============================================
#  This file is part of Wrye Bash.
#
#  Wrye Bash is free software: you can redistribute it and/or
#  modify it under the terms of the GNU General Public License
#  as published by the Free Software Foundation, either version 3
#  of the License, or (at your option) any later version.
#
#  Wrye Bash is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
#
#  You should have received a copy of the GNU General Public License
#  along with Wrye Bash.  If not, see <https://www.gnu.org/licenses/>.
#
#  Wrye Bash copyright (C) 2005-2009 Wrye, 2010-2026 Wrye Bash Team
#  https://github.com/wrye-bash
#
# =============================================================================
"""This script will pull the newest changes from weblate and safely merge them
(by locking the repo before beginning, then unlocking it afterwards). Needs wlc
installed and API keys set on your machine."""
import contextlib
import logging
import re
import subprocess
import sys
import time
from typing import NamedTuple

from helpers.utils import ROOT_PATH, dependency_missing, mk_logfile, \
    run_script, setup_log

try:
    import pygit2
except ModuleNotFoundError:
    dependency_missing(__file__, 'pygit2')

try:
    import wlc
    import wlc.config
except ModuleNotFoundError:
    dependency_missing(__file__, 'wlc')

_LOGGER = logging.getLogger(__name__)
_LOGFILE = mk_logfile(__file__)

# The name of the Weblate component (slug) to work on
_WEBLATE_COMPONENT = 'wrye-bash/wrye-bash'
# The name of the branch onto which Weblate pushes its output
_WEBLATE_OUT_BRANCH = 'weblate-out'
# The name of the branch on which all development happens
_DEV_BRANCH = 'dev'
# We need exactly one remote whose URL includes this URL fragment
_REMOTE_URL_FRAGS = ('github.com/wrye-bash/wrye-bash',
                     'github.com:wrye-bash/wrye-bash') # git protocol
_MAX_WAIT = 20.0 # when polling for weblate changes
_WAIT_FOR = 2.0 # poll interval

_manual_msg = f"""=> This is where the manual part begins.
Please clean up the rewritten {_WEBLATE_OUT_BRANCH} branch now. Tasks to do:
 - check each commit's message and author/co-authors
 - verify the rebased branch matches the remote.
 - add any manual commits needed (e.g. README updates, etc.)
Then"""
def main(args):
    setup_log(_LOGGER, args)
    wlc_config = wlc.config.WeblateConfig()
    _LOGGER.debug(f'Temporarily changing working dir to {ROOT_PATH}')
    # Change working directory because load() down below reads the config in
    # the current working directory as well (no way to change that)
    with contextlib.chdir(ROOT_PATH):
        _LOGGER.debug('Loading wlc config')
        wlc_config.load()
        weblate = wlc.Weblate(config=wlc_config)
        wb_component: wlc.Component = weblate.get_component(_WEBLATE_COMPONENT)
        repo = pygit2.Repository(ROOT_PATH)
        # Preparation: Ensure no developer nukes their changes this way
        if any(v != pygit2.enums.FileStatus.IGNORED
               for v in repo.status().values()):
            _LOGGER.error('You have uncommitted changes in your repo. Stash '
                          'or commit them before running '
                          'merge_weblate_changes.')
            sys.exit(1)
        origin_remotes = [r for r in repo.remotes if
                          any((fr in r.url) for fr in _REMOTE_URL_FRAGS)]
        if len(origin_remotes) != 1:
            _LOGGER.error('In order for merge_weblate_changes to work, you '
                          'need to have a remote with the WB URL (only *one* '
                          'with that URL). Usually this one is called '
                          '"origin".')
            sys.exit(2)
        origin_remote = origin_remotes[0]
        rem_name, rem_url = map(str, [origin_remote.name, origin_remote.url])
        _LOGGER.debug(f'Found fitting remote named {rem_name} with URL '
                      f'{rem_url}')
        _LOGGER.info('Running initial fetch to update repository...')
        dev_head = fetch_and_set_changes(repo, origin_remote,
                                         branch=_DEV_BRANCH, is_default=True)
        # 1. Lock the component so no one can possibly lose their changes
        with lock_component(wb_component):
            _LOGGER.info(f'Fetching latest version of {_WEBLATE_OUT_BRANCH} '
                         f'branch...')
            # 2. Make sure our repo has the newest changes
            prev_commit_sha = fetch_and_set_changes(repo, origin_remote)
            # 3. Make Weblate commit and push all changes (this will always
            # cause a rewrite and force-push, leading the next fetch to get new
            # commits with different SHAs)
            _LOGGER.info('Telling Weblate to commit its changes...')
            wb_component.commit()
            _LOGGER.info('Telling Weblate to push its committed changes...')
            wb_component.push()
            # 4. Fetch those new commits - we may have to try a couple times,
            # so include a sleep in between to not hammer the remote
            _LOGGER.info('Fetching Weblate-pushed changes...')
            deadline = time.monotonic() + _MAX_WAIT
            while time.monotonic() < deadline:
                next_commit_sha = fetch_and_set_changes(repo, origin_remote)
                if next_commit_sha != prev_commit_sha:
                    _LOGGER.info("Detected new Weblate commit.")
                    break
                time.sleep(_WAIT_FOR)
            else:
                _LOGGER.info('No new commits appeared after %.0f seconds; '
                    'assuming Weblate had nothing new to push.', _MAX_WAIT)
            # 5. Prepare the rebase by squashing and rewriting authors
            _prepare_rebase(repo, next_commit_sha, dev_head)
            # 6. Here comes the manual part
            _pause(_manual_msg, 6, f'git rebase -i --autosquash {_DEV_BRANCH}')
            _pause('Please inspect the rebase then', 7, f'git checkout '
              f'{_DEV_BRANCH}', f'git merge --no-ff {_WEBLATE_OUT_BRANCH} -e')
            cmds = ('git checkout weblate-in', f'git reset --hard '
                    f'{_DEV_BRANCH}', f'git push {rem_name} -f')
            _pause('Please inspect the merge then', 8, *cmds)
            _pause(f'Please manually push {_DEV_BRANCH} then', -1,
                   cmd_msg='wlc reset/unlock')
            wb_component.reset()
        _LOGGER.info('Thank you :)')

def _pause(msg, err_code, *cmds, cmd_msg=''):
    cmd_msg = cmd_msg or '\n'.join(cmds)
    _LOGGER.info(f"{msg} type 'continue' here to run `{cmd_msg}`")
    curr_input = ''
    while curr_input != 'continue':
        curr_input = input("Enter 'continue' once done >>> ")
    try:
        for cmd in cmds:
            subprocess.run(cmd.split(), check=True, text=True,
                           capture_output=True)
    except subprocess.CalledProcessError as e:
        # Command 'cmd' returned non-zero exit status 1.\nerror: ...
        _LOGGER.error(f'{e}\n{e.stderr}')
        sys.exit(err_code)

def fetch_and_set_changes(repo: pygit2.Repository, remote: pygit2.Remote,*,
        branch=_WEBLATE_OUT_BRANCH, is_default=False) -> pygit2.Oid:
    """Helper to fetch changes from the specified remote, check out the
    branch (using logic similar to git's default checkout logic, i.e. creating
    it from the remote if it doesn't exist locally), hard-reset the branch to
    match origin, and return the commit that is now at the HEAD of this branch.
    If is_default is True, the function will check that the local branch exists
    and matches the remote."""
    branch_ref_name = f'refs/heads/{branch}'
    try:
        remote.fetch(prune=pygit2.enums.FetchPrune.NO_PRUNE)
    except pygit2.GitError:
        try:
            subprocess.run(['git', 'fetch', f'{remote.name}'], check=True)
        except subprocess.CalledProcessError as e:
            _LOGGER.error(f'Can not fetch from {remote.url}:\n{e}')
            sys.exit(3)
    remote_branch = f'{remote.name}/{branch}'
    remote_commit, remote_ref = repo.resolve_refish(remote_branch)
    rem_head = remote_commit.id
    if branch not in repo.branches.local:
        # We need to set up a local branch and make it track the remote
        if remote_branch not in repo.branches.remote:
            _LOGGER.error(f'Branch {branch} not found in local or remote '
                          f'branches, does it exist?')
            sys.exit(4)
        repo.create_reference(branch_ref_name, rem_head)
        _LOGGER.debug('Created local branch from remote branch')
    branch_reference = repo.lookup_reference(branch_ref_name)
    branch_head = branch_reference.target
    if is_default:
        if branch_head != rem_head:
            _LOGGER.error(f'Your {branch} does not match the remote (your '
                          f'latest commit is {branch_head}, but the latest '
                          f'remote commit is {rem_head}). Either pull '
                          f'or push before running merge_weblate_changes.')
            sys.exit(5)
    else: # ~= git checkout <branch>
        repo.checkout(branch_reference)
        _LOGGER.debug(f'Checked out {branch} branch')
        # ~= git reset --hard origin/<branch>
        repo.reset(remote_ref.target, pygit2.enums.ResetMode.HARD)
    return rem_head

_HOSTED = 'hosted@weblate.org'
_RE_COAUTHOR = re.compile(r'^Co-authored-by:\s*(.*?)\s*<(.*?)>$', re.M)
class ReplayCommit(NamedTuple):
    tree_id: pygit2.Oid
    author: pygit2.Signature
    message: str

_keep_lines = ('Translate-URL:', 'Co-authored-by:', 'Translation:',
               'Translate', 'Add translation')
_auto_title = 'Update translation files'
def _prepare_rebase(repo: pygit2.Repository, webl_out_head: pygit2.Oid,
                    rebase_head: pygit2.Oid):
    """Prepare the weblate-out branch to rebase:
         - mark for squash all the translation 'updates' where no human was
           involved, just the msgmerge hook
         - squash all the template.pot updates
         - rewrite authors for non-automated commits."""
    replay = [webl_in := repo.revparse_single('origin/weblate-in')]
    walker = repo.walk(webl_out_head, pygit2.enums.SortMode.REVERSE)
    walker.hide(webl_in.id)
    auto_commit = None
    for com in walker:
        msg = com.message.rstrip()
        coauthors = _RE_COAUTHOR.findall(msg)
        if humans := [(n, e) for n, e in coauthors if e != _HOSTED]:
            author = pygit2.Signature(*humans[0], com.author.time,
                                      com.author.offset)
            lines, skip = [], False
            for li in msg.splitlines():
                if not (skip := li.startswith(_auto_title) or (
                        skip and not li.startswith(_keep_lines))):
                    if (m := _RE_COAUTHOR.match(li)) is None or m.groups() != \
                            humans[0]: # skip the main author
                        lines.append(li)
            msg = '\n'.join(lines).strip()
        else:
            author = com.author
            if auto_commit is None:
                auto_commit = com
                msg = _auto_title if (dex := msg.rfind(_auto_title)) == -1 \
                    else msg[dex:]
            else:
                msg = f'squash! {_auto_title}'
        replay.append(ReplayCommit(com.tree_id, author, msg))
    for c in replay:
        rebase_head = repo.create_commit(None, c.author,
            repo.default_signature, c.message, c.tree_id, [rebase_head])
    repo.lookup_branch(_WEBLATE_OUT_BRANCH).set_target(rebase_head)

@contextlib.contextmanager
def lock_component(weblate_component: wlc.Component):
    """Small helper to safely perform operations on a Weblate component by
    locking and unlocking it. Keeps it locked if an exception occurs."""
    component_name = getattr(weblate_component, "name", "<unknown name>")
    try:
        _LOGGER.info(f'Locking component "{component_name}"...')
        weblate_component.lock()
        yield
        _LOGGER.info(f'Unlocking component "{component_name}"...')
        weblate_component.unlock()
    except:
        _LOGGER.error(f'Unexpected error, leaving Weblate component '
                      f'"{component_name}" locked just in case')
        raise

if __name__ == '__main__':
    run_script(main, __doc__, _LOGFILE)
