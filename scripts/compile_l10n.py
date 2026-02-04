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
"""This script will compile all .po files from Mopy/bash/l10n to .mo files.
Automatically run by build.py, but you will have to run this manually if
you want to test non-English localizations in a development environment."""

__author__ = 'Infernio'

import logging
import os
from pathlib import Path

from helpers._i18n import msgfmt
from helpers.utils import L10N_PATH, run_script, mk_logfile, setup_log

_LOGGER = logging.getLogger(__name__)
_LOGFILE = mk_logfile(__file__)

def main(args, po_files=()):
    setup_log(_LOGGER, args)
    _LOGGER.info('Starting compilation of localizations')
    po_files: list[Path] = [*po_files] or [f for f in L10N_PATH.iterdir() if
                                           f.suffix == '.po']
    mos, len_po = set(), len(po_files)
    for i, po in enumerate(po_files, start=1):
        _LOGGER.info(f'Compiling localization {po.stem} ({i}/{len_po})...')
        mos.add(mo_output := po.with_suffix('.mo'))
        # msgfmt caches its messages between runs for some godforsaken reason,
        # so explicitly clear that
        msgfmt.MESSAGES = {}
        msgfmt.make(*map(os.fspath, (po, mo_output))) # msgfmt wants a string
    _LOGGER.info('Compilation of localizations succeeded!')
    return sorted(mos)

if __name__ == '__main__':
    run_script(main, __doc__, _LOGFILE)
