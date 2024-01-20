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
"""This module generates the changelog for a milestone by reading its
metadata."""
import argparse
import base64
import io
import os.path
import shutil
import subprocess
import sys
from datetime import date
from functools import partial
from html import escape as html_escape

from helpers import github_login
from helpers.github_wrapper import get_closed_issues
from helpers.html_gen import a, bb_list, closed_issue, h3, markdown_escape, \
    markdown_link, markdown_list, size, spoiler, ul
from helpers.utils import CHANGELOGS_PATH, DEFAULT_AUTHORS, \
    DEFAULT_MILESTONE_TITLE, out_path

if sys.version_info[0] < 3:
    raise RuntimeError('Python 3 is required for running this script')

_CHANGELOG_TITLE_SIZE = 5
_PROMPT = 'PROMPT'

# Functions ===================================================================
class _Parser:
    def __init__(self, description, add_h=True):
        self.parser = argparse.ArgumentParser(description=description,
                        add_help=add_h,
                        formatter_class=argparse.ArgumentDefaultsHelpFormatter)
        # actions to be run on options if not specified
        self.actions = []

    def milestone(self, help_='Specify the milestone for latest release.'):
        action = self.parser.add_argument('-m', '--milestone',
            dest='milestone', default=_PROMPT, type=str, help=help_)
        self.actions.append(action)
        return self

    def milestone_title(self,
            help_='Specify a title for the milestone changelog.'):
        action = self.parser.add_argument('-t', '--title', dest='title',
            default=DEFAULT_MILESTONE_TITLE, type=str, help=help_)
        self.actions.append(action)
        return self

    def overwrite(self):
        self.parser.add_argument('-o', '--overwrite', dest='overwrite',
            action='store_false', help='Do NOT overwrite existing file(s)')
        return self

    def offline(self):
        self.parser.add_argument('--offline', dest='offline',
            action='store_true', help='Do not hit github - you must have '
                                       'the issue list available offline')
        return self

    def editor(self, help_='Path to editor executable to launch.',
               help_no_editor='Never launch an editor'):
        editor_group = self.parser.add_mutually_exclusive_group()
        if os.name == 'nt':
            default_editor = os.path.expandvars(os.path.join(
                '%PROGRAMFILES%', 'Notepad++', 'notepad++.exe'))
        else:
            default_editor = shutil.which('vim')
        editor_group.add_argument('-e', '--editor', dest='editor',
            default=default_editor, type=str, help=help_)
        editor_group.add_argument('-ne', '--no-editor', dest='no_editor',
            action='store_true', default=False, help=help_no_editor)
        return self

    def authors(self, help_='Specify the authors (comma separated strings as '
                            'in: Me,"Some Others".'):
        action = self.parser.add_argument('--authors', dest='authors',
            default=DEFAULT_AUTHORS, type=str, help=help_)
        self.actions.append(action)
        return self

    @staticmethod
    def get_editor(args):
        """Handles default fallbacks for the --editor option"""
        if not hasattr(args, 'editor'):
            if hasattr(args, 'no_editor'):
                args.editor = None
            return
        if os.path.exists(args.editor):
            return
        path = os.path.normcase(args.editor)
        path = os.path.normpath(path)
        path = os.path.expandvars(path)
        parts = path.split(os.path.sep)
        # If 'Program Files' was in the path, try 'Program Files (x86)',
        # and vice versa
        part1 = os.path.normcase('Program Files')
        part2 = os.path.normcase('Program Files (x86)')
        check = ''
        if part1 in parts:
            idex = parts.index(part1)
            parts[idex] = part2
            check = os.path.join(*parts)
        elif part2 in parts:
            idex = parts.index(part2)
            parts[idex] = part1
            check = os.path.join(*parts)
        if check and os.path.exists(check):
            args.editor = check
            return
        print('Specified editor does not exist, please enter a valid path:')
        check = input('>')
        if not check:
            args.no_editor = True
        if not os.path.exists(check):
            print('Specified editor does not exists, assuming --no-editor')
            args.no_editor = True
        else:
            args.editor = check
        if args.no_editor:
            args.editor = None

    def parse(self):
        """
        Return an object which can be used to get the arguments as in:
            parser_instance.parse().milestone

        :return: ArgumentParser
        """
        args = self.parser.parse_args()
        # see: http://stackoverflow.com/a/21588198/281545
        for a in self.actions:
            if getattr(args, a.dest) == a.default and a.default == _PROMPT:
                print('Please specify %s' % a.dest)
                values = input('>')
                setattr(args, a.dest, values)
        # Special handler for --editor:
        _Parser.get_editor(args)
        return args

def _parse_args():
    return _Parser(description='Generate Changelog').editor().milestone(
        help_='Specify the milestone for latest release.').authors(
    ).offline().overwrite().milestone_title().parse()

def _title(title, authors=None):
    title = title + '[' + date.today().strftime('%Y/%m/%d') + ']'
    if not authors: return title
    return title + ' [' + ', '.join(authors) + ']'

def _changelog_bbcode(issues, title, out):
    out.write(size(_CHANGELOG_TITLE_SIZE, _title(title)))
    out.write('\n'.join(spoiler('\n'.join(bb_list(issues)))))
    out.write('\n')

def _changelog_txt(issues, title, out):
    issue_template = 'https://github.com/wrye-bash/wrye-bash/issues/%u'
    def add_link(issue_line):
        issue_num, issue_rest = issue_line.split(':', 1)
        issue_link = a(issue_num, href=issue_template % int(issue_num[1:]))
        return issue_link + ':' + html_escape(issue_rest)
    out.write(h3(html_escape(_title(title))))
    out.write('\n'.join(ul(issues, f=add_link)))
    out.write('\n\n')  # needs blank line for Version History.html

def _changelog_markdown(issues, title, out):
    issue_template = 'https://github.com/wrye-bash/wrye-bash/issues/%u'
    def add_link(issue_line):
        issue_num, issue_rest = issue_line.split(':', 1)
        issue_link = markdown_link(issue_num,
            href=issue_template % int(issue_num[1:]))
        return issue_link + ':' + markdown_escape(issue_rest)
    out.write(markdown_escape(_title(title)))
    out.write('\n\n')
    out.write('\n'.join(markdown_list(issues, f=add_link)))
    out.write('\n')

def _changelog_b64(issues, title, out):
    temp_out = io.StringIO()
    _changelog_txt(issues, title, temp_out)
    b64_encoded = base64.b64encode(temp_out.getvalue().encode('utf-8'))
    out.write(b64_encoded.decode('utf-8'))

# API =========================================================================
print(f'Changelogs will be placed in {CHANGELOGS_PATH}')

def _write_changelog(issue_list, num, title=DEFAULT_MILESTONE_TITLE,
        overwrite=False, extension='.txt', logic=_changelog_txt):
    """Write 'Changelog - <milestone>.txt'"""
    if issue_list is None:
        issue_list, _ = __get_issue_list(num)
    out_file = out_path(dir_=CHANGELOGS_PATH,
        name='Changelog - ' + num + extension)
    print(out_file)
    if os.path.isfile(out_file) and not overwrite: return
    title = num + ' ' + title + ' ' if title else num
    with open(out_file, 'w', encoding='utf-8') as out:
        logic(issue_list, title, out)

def _write_changelog_bbcode(issue_list, num, title=DEFAULT_MILESTONE_TITLE,
        overwrite=False):
    """Write 'Changelog - <milestone>.bbcode.txt'"""
    return _write_changelog(issue_list, num, title, overwrite,
        extension='.bbcode.txt', logic=_changelog_bbcode)

def _write_changelog_markdown(issue_list, num, title=DEFAULT_MILESTONE_TITLE,
        overwrite=False):
    """Write 'Changelog - <milestone>.md'"""
    return _write_changelog(issue_list, num, title, overwrite, extension='.md',
        logic=_changelog_markdown)

def _write_changelog_b64(issue_list, num, title=DEFAULT_MILESTONE_TITLE,
        overwrite=False):
    """Write 'Changelog - <milestone>.b64'"""
    return _write_changelog(issue_list, num, title, overwrite,
        extension='.b64', logic=_changelog_b64)

def main():
    opts = _parse_args()  # TODO per game # if opts.game:...
    issue_list, milestone = __get_issue_list(
        opts.milestone, opts.editor, opts if not opts.offline else None)
    if issue_list is None: return
    num = milestone.title if milestone else opts.milestone
    print('Writing changelogs')
    globals()['_title'] = partial(_title, authors=(opts.authors.split(',')))
    _write_changelog(issue_list, num, opts.title, opts.overwrite)
    _write_changelog_markdown(issue_list, num, opts.title, opts.overwrite)
    # BBCode changelog is now unused
    #_write_changelog_bbcode(issue_list, num, opts.title, opts.overwrite)
    _write_changelog_b64(issue_list, num, opts.title, opts.overwrite)
    print('Changelogs generated.')

def __get_issue_list(miles_num, editor=None, opts=None):
    issue_list = milestone = None
    issue_list_txt = 'issue_list.' + miles_num + '.txt'
    if opts: # get the issues from github and save them in a text file
        git_ = github_login.hub(miles_num)
        if git_ is not None:
            repo, milestone = git_[0], git_[1]
            issues = get_closed_issues(repo, milestone)
            issue_list = list(map(closed_issue, issues))
            issue_list = _dump_plain_issue_list(editor, issue_list,
                issue_list_txt)
    else: # work offline, if it blows on you you get a black star for not RTM
        issue_list = _read_plain_issue_list(issue_list_txt)
        # print issue_list
    return issue_list, milestone

def _dump_plain_issue_list(editor, issue_list, txt_):
    with open(out_path(dir_=CHANGELOGS_PATH, name=txt_), 'w') as out:
        out.write('\n'.join(issue_list))
    if editor:
        print('Please edit the issues as you want them to appear on '
              'the changelogs:' + str(out.name))
        subprocess.call([editor, out.name])  # TODO block
        _ = input('Press enter when done>')
        issue_list = _read_plain_issue_list(txt_)
    return issue_list

def _read_plain_issue_list(txt_):
    with open(out_path(dir_=CHANGELOGS_PATH, name=txt_), 'r') as in_:
        return in_.read().splitlines()

if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print('Aborted')
