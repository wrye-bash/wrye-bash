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
"""Provides various utility functions to scripts."""

from __future__ import annotations

import argparse
import logging
import math
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path
from urllib.request import urlopen

import pygit2

# Reusable path definitions
SCRIPTS_PATH = Path(__file__).absolute().parent.parent
ROOT_PATH = SCRIPTS_PATH.parent
WBSA_PATH = SCRIPTS_PATH / 'build' / 'standalone'
DIST_PATH = SCRIPTS_PATH / 'dist'
MOPY_PATH = ROOT_PATH / 'Mopy'
APPS_PATH = MOPY_PATH / 'Apps'
NSIS_PATH = SCRIPTS_PATH / 'build' / 'nsis'
LOG_PATH = SCRIPTS_PATH / 'log'
L10N_PATH = MOPY_PATH / 'bash' / 'l10n'
TESTS_PATH = MOPY_PATH / 'bash' / 'tests'
TAGLISTS_PATH = MOPY_PATH / 'taglists'
IDEA_PATH = ROOT_PATH / '.idea'
VSCODE_PATH = ROOT_PATH / '.vscode'
OUT_PATH = SCRIPTS_PATH / 'out'
CHANGELOGS_PATH = SCRIPTS_PATH / 'changelogs'
WB_STATUS_PATH = ROOT_PATH.parent / 'wb_status'
TAGINFO = SCRIPTS_PATH / 'taginfo.txt'

# Other constants
DEFAULT_MILESTONE_TITLE = 'Bug fixes and enhancements'
DEFAULT_AUTHORS = 'Various community members'
ALL_ISSUES = 'all'

class _StreamRedirector:
    """Useful for redirecting the vendored _i18n scripts' print statements to a
    proper logger."""
    def __init__(self, logger: logging.Logger, level=logging.INFO):
       self.logger = logger
       self.level = level
       self.linebuf = ''

    def write(self, str_buffer: str):
       for l in str_buffer.rstrip().splitlines():
          self.logger.log(self.level, l.rstrip())

    def flush(self):
        pass

# verbosity:
#  quiet (WARNING and above)
#  regular (INFO and above)
#  verbose (all messages)
def setup_log(logger, args):
    logger.setLevel(logging.DEBUG)
    stdout_handler = logging.StreamHandler(sys.stdout)
    stdout_formatter = logging.Formatter('%(message)s')
    stdout_handler.setFormatter(stdout_formatter)
    stdout_handler.setLevel(args.verbosity)
    logger.addHandler(stdout_handler)
    if (chosen_logfile := args.logfile) is not None:
        os.makedirs(os.path.dirname(chosen_logfile), exist_ok=True)
        file_handler = logging.FileHandler(chosen_logfile)
        file_formatter = logging.Formatter('%(levelname)s: %(message)s')
        file_handler.setFormatter(file_formatter)
        logger.addHandler(file_handler)
        sys.stdout = _StreamRedirector(logger)
        sys.stderr = _StreamRedirector(logger, logging.WARNING)

# sets up common parser options
def setup_common_parser(parser: argparse.ArgumentParser, logfile: Path):
    verbose_group = parser.add_mutually_exclusive_group()
    verbose_group.add_argument(
        '-v',
        '--verbose',
        action='store_const',
        const=logging.DEBUG,
        dest='verbosity',
        help='Print all output to console.',
    )
    verbose_group.add_argument(
        '-q',
        '--quiet',
        action='store_const',
        const=logging.WARNING,
        dest='verbosity',
        help='Do not print any output to console.',
    )
    try:
        nicer_logfile = logfile.relative_to(Path.cwd())
    except ValueError:
        nicer_logfile = logfile # can't be made relative
    parser.add_argument(
        '-l',
        '--logfile',
        default=logfile,
        help=f'Where to store the log. [default: {nicer_logfile}]',
    )
    parser.set_defaults(verbosity=logging.INFO)

def run_script(main, script_doc: str, logfile: Path, logger: logging.Logger,
        *, custom_setup=None):
    """The main entry point for Wrye Bash's modern script API. Sets up an
    argument parser, logging, etc. and calls the main method.

    :param main: The main method to call.
    :param script_doc: Set to your script's __doc__.
    :param logfile: The default path to the script's log file.
    :param logger: The logger for this script.
    :param custom_setup: If not None, this will be called with the created
        ArgumentParser instance as a single parameter. This gives you a chance
        to add custom arguments."""
    argparser = argparse.ArgumentParser(description=script_doc,
        formatter_class=argparse.RawDescriptionHelpFormatter)
    setup_common_parser(argparser, logfile)
    if custom_setup:
        custom_setup(argparser)
    parsed_args = argparser.parse_args()
    rm(parsed_args.logfile)
    setup_log(logger, parsed_args)
    main(parsed_args)

def with_args(args=None, **kwargs):
    """Hacky way to pass custom arguments to another script."""
    class _CustomArgs:
        def __getattr__(self, item):
            if item in kwargs:
                return kwargs[item]
            return getattr(args, item)
    return _CustomArgs()

def convert_bytes(size_bytes):
    if size_bytes == 0:
        return '0B'
    size_name = ('B', 'KB', 'MB', 'GB', 'TB', 'PB', 'EB', 'ZB', 'YB')
    i = int(math.floor(math.log(size_bytes, 1024)))
    p = math.pow(1024, i)
    s = round(size_bytes / p, 2)
    return f'{s}{size_name[i]}'

def download_file(url, fpath):
    file_name = os.path.basename(fpath)
    response = urlopen(url)
    meta = response.info()
    file_size = int(meta.get('Content-Length'))
    converted_size = convert_bytes(file_size)
    file_size_dl = 0
    block_sz = 8192
    with open(fpath, 'wb') as dl_file:
        while True:
            buff = response.read(block_sz)
            if not buff:
                break
            file_size_dl += len(buff)
            dl_file.write(buff)
            percentage = file_size_dl * 100.0 / file_size
            status = f'{file_name:>20}  -----  [{percentage:6.2f}%] ' \
                     f'{convert_bytes(file_size_dl):>10}/{converted_size}'
            status += chr(8) * (len(status) + 1)
            print(status, end=' ')
    print()

def run_subprocess(command, logger, **kwargs):
    sp = subprocess.Popen(
        command,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        universal_newlines=True,
        **kwargs
    )
    logger.debug(f'Running command: {u" ".join(command)}')
    stdout, _stderr = sp.communicate()
    if sp.returncode != 0:
        logger.error(stdout)
        raise subprocess.CalledProcessError(sp.returncode, ' '.join(command))
    logger.debug('--- COMMAND OUTPUT START ---')
    logger.debug(stdout)
    logger.debug('---  COMMAND OUTPUT END  ---')

def get_repo_sig(repo):
    """Wrapper around pygit2 that shows a helpful error message to the user if
    their credentials have not been configured yet."""
    try:
        return repo.default_signature
    except KeyError:
        print('\n'.join(['', # empty line before the error
            'ERROR: You have not set up your git identity yet.',
            'This is necessary for the git operations that the build script '
            'uses.',
            'You can configure them as follows:',
            '   git config --global user.name "Your Name"',
            '   git config --global user.email "you@example.com"']),
            file=sys.stderr)
        sys.exit(1)

def commit_changes(*, changed_paths: list[os.PathLike | str], commit_msg: str,
        repo_path: os.PathLike | str = ROOT_PATH):
    """Commit changes to the specified files by creating a commit with the
    specified message."""
    repo = pygit2.Repository(repo_path)
    user = get_repo_sig(repo)
    parent = [repo.head.target]
    for cf in changed_paths:
        rel_path = os.path.relpath(cf, repo.workdir).replace('\\', '/')
        if repo.status_file(rel_path) == pygit2.GIT_STATUS_WT_MODIFIED:
            repo.index.add(rel_path)
    tree = repo.index.write_tree()
    repo.create_commit('HEAD', user, user, commit_msg, tree, parent)
    repo.index.write()

def out_path(dir_=OUT_PATH, name='out.txt'):
    """Returns a path joining the dir_ and name parameters. Will create the
    dirs in dir_ if not existing.

    :param dir_: a directory path
    :param name: a filename"""
    os.makedirs(dir_, exist_ok=True)
    return os.path.join(dir_, name)

def fatal_error(msg: str, *, exit_code: int, log_traceback=False,
        logger: logging.Logger):
    """Print an ERROR level message and optionally print the current
    exception's traceback, then exit with the provided exit code.

    :param logger: The logger to use for printing.
    :param msg: The message to print.
    :param exit_code: The exit code to terminate the script with.
    :param log_traceback: If True, log the current exception's traceback."""
    logger.error(msg, exc_info=log_traceback)
    sys.exit(exit_code)

def open_wb_file(*parts, logger: logging.Logger):
    """Open a Wrye Bash source code file relative to the Mopy folder in
    read-write mode. Note that the file *must* have UTF-8 encoding!"""
    try:
        return open(os.path.join(MOPY_PATH, *parts), 'r+', encoding='utf-8')
    except FileNotFoundError:
        fatal_error(f'File {os.path.join(*parts)} not found, this script '
                    f'probably needs to be updated',
            exit_code=100, logger=logger)

def edit_wb_file(*parts, trigger_regex: re.Pattern, edit_callback,
        logger: logging.Logger):
    """Edit a Wrye Bash source code file relative to the Mopy folder. Look for
    lines matching trigger_regex and replace them with the result of calling
    edit_callback (with the resulting re.Match object passed to edit_callback
    as an argument)."""
    new_wbpy_lines = []
    with open_wb_file(*parts, logger=logger) as wbpy:
        wbpy_lines = wbpy.read().splitlines()
        for wbpy_line in wbpy_lines:
            if wbpy_ma := trigger_regex.match(wbpy_line):
                new_wbpy_lines.append(edit_callback(wbpy_ma))
            else:
                new_wbpy_lines.append(wbpy_line)
        if wbpy_lines == new_wbpy_lines:
            fatal_error(f'Nothing edited in file {os.path.join(*parts)}, this '
                        f'script probably needs to be updated',
                exit_code=101, logger=logger)
        wbpy.seek(0, os.SEEK_SET)
        wbpy.truncate(0)
        wbpy.write('\n'.join(new_wbpy_lines) + '\n')

def edit_bass_version(new_ver: str, logger: logging.Logger):
    """Change the AppVersion in bass.py to the specified version."""
    def edit_bass(bass_ma):
        return f"AppVersion = '{new_ver}'{bass_ma.group(1)}"
    edit_wb_file('bash', 'bass.py',
        trigger_regex=re.compile(r"^AppVersion = '\d+(?:\.\d+)?'(.*)$"),
        edit_callback=edit_bass, logger=logger)

def rm(node: str | os.PathLike):
    """Removes a file or directory if it exists"""
    if os.path.isfile(node):
        os.remove(node)
    elif os.path.isdir(node):
        shutil.rmtree(node)

def mv(src: str | os.PathLike, dst: str | os.PathLike):
    """Moves a file or directory if it exists"""
    if os.path.exists(src):
        shutil.move(src, dst)

def cp(src: str | os.PathLike, dst: str | os.PathLike):
    """Moves a file to a destination, creating the target
       directory as needed."""
    if os.path.isdir(src):
        if not os.path.exists(dst):
            os.makedirs(dst)
    else:
        # file
        dstdir = os.path.dirname(dst)
        if not os.path.exists(dstdir):
            os.makedirs(dstdir)
        shutil.copy2(src, dst)

def mk_logfile(dunder_file: str):
    log_fname = os.path.splitext(os.path.basename(dunder_file))[0] + '.log'
    return LOG_PATH / log_fname

# Copy-pasted from bolt.py
# We need to split every time we hit a new 'type' of component. So greedily
# match as many of one type as possible (except dots and dashes, since those
# are guaranteed to start a new component)
_component_re = re.compile(r'(\.|-|\d+|[^\d.-]+)')
_separators = frozenset({'.', '-'})
class LooseVersion:
    """A class for representing and comparing versions, where the term
    'version' refers to any and every possible string. The way this class works
    is pretty simple: there are three 'types' of components to a LooseVersion:

     - separators (dots and dashes)
     - digits
     - everything else

    Separators begin a new component to the version, but are not part of the
    version themselves. Digits are compared numerically, so 2 < 10. Everything
    else is compared alphabetically, so 'a' < 'm'. A whole version is compared
    by comparing the components in it as a tuple."""
    _parsed_version: tuple[int | str]

    def __init__ (self, ver_string: str):
        ver_components = _component_re.split(ver_string)
        parsed_version = []
        for ver_comp in ver_components:
            if not ver_comp or ver_comp in _separators:
                # Empty components and separators are not part of the version
                continue
            try:
                parsed_version.append(int(ver_comp))
            except ValueError:
                parsed_version.append(ver_comp)
        self._parsed_version = tuple(parsed_version)

    def __repr__(self):
        return '.'.join([str(c) for c in self._parsed_version])

    def __eq__(self, other):
        if not isinstance(other, LooseVersion):
            return NotImplemented
        return self._parsed_version == other._parsed_version

    def __lt__(self, other):
        if not isinstance(other, LooseVersion):
            return NotImplemented
        return self._parsed_version < other._parsed_version

    def __le__(self, other):
        if not isinstance(other, LooseVersion):
            return NotImplemented
        return self._parsed_version <= other._parsed_version

    def __gt__(self, other):
        if not isinstance(other, LooseVersion):
            return NotImplemented
        return self._parsed_version > other._parsed_version

    def __ge__(self, other):
        if not isinstance(other, LooseVersion):
            return NotImplemented
        return self._parsed_version >= other._parsed_version
