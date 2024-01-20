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

import os

from helpers._i18n import msgfmt
from helpers.utils import L10N_PATH

def main():
    source_files = [f for f in L10N_PATH.iterdir() if f.suffix == '.po']
    print('Starting compilation of localizations')
    for i, po in enumerate(source_files, start=1):
        print(f'Compiling localization {po.stem} ({i}/{len(source_files)})...')
        po_str = os.fspath(po) # msgfmt wants a string
        mo_output = po_str[:-2] + 'mo'
        msgfmt.make(po_str, mo_output)
    print('Compilation of localizations succeeded!')

if __name__ == '__main__':
    main()
