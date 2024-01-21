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
"""This script will compile all .po files from Mopy/bash/l10n to .mo files.
Automatically run by build.py, but you will have to run this manually this if
you want to test non-English localizations in a development environment."""

__author__ = 'Infernio'

import argparse
import logging
import os

from helpers._i18n import msgfmt
from helpers.utils import L10N_PATH, SCRIPTS_PATH, setup_common_parser, \
    setup_log, setup_parser_logfile

LOGGER = logging.getLogger(__name__)

LOGFILE = SCRIPTS_PATH / 'compile_l10n.log'

def main(verbosity=logging.INFO, logfile=LOGFILE):
    setup_log(LOGGER, verbosity=verbosity, logfile=logfile)
    source_files = [f for f in L10N_PATH.iterdir() if f.suffix == '.po']
    LOGGER.info('Starting compilation of localizations')
    for i, po in enumerate(source_files, start=1):
        LOGGER.info(f'Compiling localization {po.stem} '
                    f'({i}/{len(source_files)})...')
        po_str = os.fspath(po) # msgfmt wants a string
        mo_output = po_str[:-2] + 'mo'
        msgfmt.make(po_str, mo_output)
    LOGGER.info('Compilation of localizations succeeded!')

if __name__ == '__main__':
    argparser = argparse.ArgumentParser(description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter)
    setup_common_parser(argparser)
    setup_parser_logfile(argparser, LOGFILE)
    parsed_args = argparser.parse_args()
    with open(parsed_args.logfile, 'w', encoding='utf-8'): pass
    main(parsed_args.verbosity, parsed_args.logfile)
