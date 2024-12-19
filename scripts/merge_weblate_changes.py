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
#  Wrye Bash copyright (C) 2005-2009 Wrye, 2010-2024 Wrye Bash Team
#  https://github.com/wrye-bash
#
# =============================================================================
"""This script will pull the newest changes from weblate and safely merge them
(by locking the repo before beginning, then unlocking it afterwards). Needs wlc
installed and API keys set on your machine."""
import contextlib
import logging
import sys
import time

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
_DEFAULT_BRANCH = 'dev'
# We need exactly one remote whose URL includes this URL fragment
_REMOTE_BRANCH_URL = 'github.com/wrye-bash/wrye-bash'

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
        origin_remotes = [r for r in repo.remotes
                          if _REMOTE_BRANCH_URL in r.url]
        if len(origin_remotes) != 1:
            _LOGGER.error('In order for merge_weblate_changes to work, you '
                          'need to have a remote with the WB URL (only *one* '
                          'with that URL). Usually this one is called '
                          '"origin".')
            sys.exit(2)
        origin_remote = origin_remotes[0]
        _LOGGER.debug(f'Found fitting remote named {origin_remote.name} with '
                      f'URL {origin_remote.url}')
        _LOGGER.info('Running initial fetch to update repository...')
        origin_remote.fetch(prune=pygit2.enums.FetchPrune.NO_PRUNE)
        if _DEFAULT_BRANCH not in repo.branches.local:
            _LOGGER.error(f'You have not checked out {_DEFAULT_BRANCH} yet. '
                          f'Do that before running merge_weblate_changes')
            sys.exit(3)
        local_def_commit = repo.lookup_branch(_DEFAULT_BRANCH).target.hex
        remote_def_commit = repo.lookup_branch(
            f'{origin_remote.name}/{_DEFAULT_BRANCH}',
            pygit2.enums.BranchType.REMOTE).target.hex
        if local_def_commit != remote_def_commit:
            _LOGGER.error(f'Your {_DEFAULT_BRANCH} does not match the remote '
                          f'(your latest commit is {local_def_commit}, but '
                          f'the latest remote commit is {remote_def_commit}). '
                          f'Either pull or push before running '
                          f'merge_weblate_changes.')
            sys.exit(4)
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
            next_commit_sha = prev_commit_sha
            wait_for = 0
            _LOGGER.info('Fetching Weblate-pushed changes...')
            while next_commit_sha == prev_commit_sha:
                next_commit_sha = fetch_and_set_changes(repo, origin_remote)
                time.sleep(wait_for := wait_for + 0.1)
            # 5. Extract author info and edit readme, commit that
            # TODO
            # 6. Here comes the manual part
            _LOGGER.info('=> This is where the manual part begins.')
            _LOGGER.info('Please clean up the branch now. Tasks to do:')
            _LOGGER.info(" - Edit each commit's author and co-authors as you "
                         "see fit.")
            _LOGGER.info('  - You may want to remove the weblate author from '
                         'regular human translations, for example.')
            _LOGGER.info(" - Squash all the translation 'updates' where no "
                         "human was involved, just the msgmerge hook.")
            _LOGGER.info(' - Squash all the template.pot updates.')
            _LOGGER.info("Once you're done, type 'continue' here to keep "
                         "going.")
            curr_input = ''
            while curr_input != 'continue':
                curr_input = input("Enter 'continue' once done >>> ")
            _LOGGER.info('Thank you :)')
            # 7. TODO

def fetch_and_set_changes(repo: pygit2.Repository, remote: pygit2.Remote):
    """Helper to fetch changes from the specified remote, check out the
    branch (using logic similar to git's default checkout logic, i.e. creating
    it from the remote if it doesn't exist locally), hard-reset the branch to
    match origin, and return the SHA of the commit that is now at the HEAD of
    this branch."""
    branch_ref_name = f'refs/heads/{_WEBLATE_OUT_BRANCH}'
    remote.fetch(prune=pygit2.enums.FetchPrune.NO_PRUNE)
    remote_branch = f'{remote.name}/{_WEBLATE_OUT_BRANCH}'
    remote_commit, remote_ref = repo.resolve_refish(remote_branch)
    if _WEBLATE_OUT_BRANCH not in repo.branches.local:
        # We need to set up a local branch and make it track the remote
        if remote_branch not in repo.branches.remote:
            _LOGGER.error(f'Branch {_WEBLATE_OUT_BRANCH} not found in '
                          f'local or remote branches, does it exist?')
            sys.exit(20)
        repo.create_reference(branch_ref_name, remote_commit.hex)
        _LOGGER.debug('Created local branch from remote branch')
    branch_reference = repo.lookup_reference(branch_ref_name)
    # ~= git checkout <branch>
    repo.checkout(branch_reference)
    _LOGGER.debug(f'Checked out {_WEBLATE_OUT_BRANCH} branch')
    # ~= git reset --hard origin/<branch>
    repo.reset(remote_ref.target, pygit2.enums.ResetMode.HARD)
    return branch_reference.target.hex

@contextlib.contextmanager
def lock_component(weblate_component: wlc.Component):
    """Small helper to safely perform operations on a Weblate component by
    locking and unlocking it. Keeps it locked if an exception occurs."""
    component_name = getattr(weblate_component, "name", "<unknown name>")
    try:
        _LOGGER.info(f'Locking component "{component_name}"...')
        # weblate_component.lock()
        yield
        _LOGGER.info(f'Unlocking component "{component_name}"...')
        # weblate_component.unlock()
    except:
        _LOGGER.error(f'Unexpected error, leaving Weblate component '
                      f'"{component_name}" locked just in case')
        raise


if __name__ == '__main__':
    run_script(main, __doc__, _LOGFILE)
