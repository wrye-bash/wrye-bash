#!/usr/bin/env python2
# -*- coding: utf-8 -*-

# GPL License and Copyright Notice ============================================
#  This file is part of Wrye Bash.
#
#  Wrye Bash is free software; you can redistribute it and/or
#  modify it under the terms of the GNU General Public License
#  as published by the Free Software Foundation; either version 2
#  of the License, or (at your option) any later version.
#
#  Wrye Bash is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
#
#  You should have received a copy of the GNU General Public License
#  along with Wrye Bash; if not, write to the Free Software Foundation,
#  Inc., 59 Temple Place - Suite 330, Boston, MA  02111-1307, USA.
#
#  Wrye Bash copyright (C) 2005-2009 Wrye, 2010-2019 Wrye Bash Team
#  https://github.com/wrye-bash
#
# =============================================================================

import logging
import math
import os
import subprocess
import sys
import urllib2


# verbosity:
#  quiet (warnings and above)
#  regular (info and above)
#  verbose (all messages)
def setup_log(logger, verbosity=logging.INFO, logfile=None):
    logger.setLevel(logging.DEBUG)
    stdout_handler = logging.StreamHandler(sys.stdout)
    stdout_formatter = logging.Formatter("%(message)s")
    stdout_handler.setFormatter(stdout_formatter)
    stdout_handler.setLevel(verbosity)
    logger.addHandler(stdout_handler)
    if logfile is not None:
        file_handler = logging.FileHandler(logfile)
        file_formatter = logging.Formatter("[%(name)s]: %(message)s")
        file_handler.setFormatter(file_formatter)
        logger.addHandler(file_handler)


# sets up common parser options
def setup_common_parser(parser):
    verbose_group = parser.add_mutually_exclusive_group()
    verbose_group.add_argument(
        "-v",
        "--verbose",
        action="store_const",
        const=logging.DEBUG,
        dest="verbosity",
        help="Print all output to console.",
    )
    verbose_group.add_argument(
        "-q",
        "--quiet",
        action="store_const",
        const=logging.WARNING,
        dest="verbosity",
        help="Do not print any output to console.",
    )
    parser.set_defaults(verbosity=logging.INFO)


def convert_bytes(size_bytes):
    if size_bytes == 0:
        return "0B"
    size_name = ("B", "KB", "MB", "GB", "TB", "PB", "EB", "ZB", "YB")
    i = int(math.floor(math.log(size_bytes, 1024)))
    p = math.pow(1024, i)
    s = round(size_bytes / p, 2)
    return "{}{}".format(s, size_name[i])


def download_file(url, fpath):
    file_name = os.path.basename(fpath)
    response = urllib2.urlopen(url)
    meta = response.info()
    file_size = int(meta.getheaders("Content-Length")[0])
    converted_size = convert_bytes(file_size)
    file_size_dl = 0
    block_sz = 8192
    with open(fpath, "wb") as dl_file:
        while True:
            buff = response.read(block_sz)
            if not buff:
                break
            file_size_dl += len(buff)
            dl_file.write(buff)
            percentage = file_size_dl * 100.0 / file_size
            status = "{0:>20}  -----  [{3:6.2f}%] {1:>10}/{2}".format(
                file_name, convert_bytes(file_size_dl), converted_size, percentage
            )
            status = status + chr(8) * (len(status) + 1)
            print status,
    print


def run_subprocess(command, logger, **kwargs):
    sp = subprocess.Popen(
        command, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, **kwargs
    )
    logger.debug("Running command: {}".format(" ".join(command)))
    stdout, _ = sp.communicate()
    if sp.returncode != 0:
        logger.error(stdout)
        raise subprocess.CalledProcessError(sp.returncode, " ".join(command))
    logger.debug("--- COMMAND OUTPUT START ---")
    logger.debug(stdout)
    logger.debug("---  COMMAND OUTPUT END  ---")


def relpath(path):
    return os.path.relpath(path, os.getcwd())
