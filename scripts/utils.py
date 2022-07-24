#!/usr/bin/env python3
# -*- coding: utf-8 -*-

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
#  Wrye Bash copyright (C) 2005-2009 Wrye, 2010-2022 Wrye Bash Team
#  https://github.com/wrye-bash
#
# =============================================================================

from __future__ import annotations

import logging
import math
import os
import re
import subprocess
import sys
from urllib.request import urlopen

# verbosity:
#  quiet (warnings and above)
#  regular (info and above)
#  verbose (all messages)
def setup_log(logger, verbosity=logging.INFO, logfile=None):
    logger.setLevel(logging.DEBUG)
    stdout_handler = logging.StreamHandler(sys.stdout)
    stdout_formatter = logging.Formatter(u'%(message)s')
    stdout_handler.setFormatter(stdout_formatter)
    stdout_handler.setLevel(verbosity)
    logger.addHandler(stdout_handler)
    if logfile is not None:
        file_handler = logging.FileHandler(logfile)
        file_formatter = logging.Formatter(u'%(levelname)s: %(message)s')
        file_handler.setFormatter(file_formatter)
        logger.addHandler(file_handler)

# sets up common parser options
def setup_common_parser(parser):
    verbose_group = parser.add_mutually_exclusive_group()
    verbose_group.add_argument(
        u'-v',
        u'--verbose',
        action=u'store_const',
        const=logging.DEBUG,
        dest=u'verbosity',
        help=u'Print all output to console.',
    )
    verbose_group.add_argument(
        u'-q',
        u'--quiet',
        action=u'store_const',
        const=logging.WARNING,
        dest=u'verbosity',
        help=u'Do not print any output to console.',
    )
    parser.set_defaults(verbosity=logging.INFO)

def convert_bytes(size_bytes):
    if size_bytes == 0:
        return u'0B'
    size_name = (u'B', u'KB', u'MB', u'GB', u'TB', u'PB', u'EB', u'ZB', u'YB')
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
    with open(fpath, u'wb') as dl_file:
        while True:
            buff = response.read(block_sz)
            if not buff:
                break
            file_size_dl += len(buff)
            dl_file.write(buff)
            percentage = file_size_dl * 100.0 / file_size
            status = f'{file_name:>20}  -----  [{percentage:6.2f}%] ' \
                     f'{convert_bytes(file_size_dl):>10}/{converted_size}'
            status = status + chr(8) * (len(status) + 1)
            print(status, end=u' ')
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
        raise subprocess.CalledProcessError(sp.returncode, u' '.join(command))
    logger.debug(u'--- COMMAND OUTPUT START ---')
    logger.debug(stdout)
    logger.debug(u'---  COMMAND OUTPUT END  ---')

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
