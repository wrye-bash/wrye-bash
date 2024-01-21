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
"""This script will gather all translatable strings from WB, then update the
Mopy/bash/l10n/template.pot file with these translatable strings. It is meant
to be run automatically, via CI, to push the output to a weblate input
branch."""

__author__ = 'Infernio'

import logging
import os
import pkgutil
import re
import sys

from helpers._i18n import pygettext
from helpers.utils import L10N_PATH, MOPY_PATH, fatal_error, edit_wb_file, \
    run_script, mk_logfile, setup_log

_LOGGER = logging.getLogger(__name__)
_LOGFILE = mk_logfile(__file__)

# We need the AppVersion for the Project-Id-Version
sys.path.insert(0, str(MOPY_PATH))
from bash import bass

def _find_all_bash_modules(bash_path, cur_dir, _files=None):
    """Internal helper function. Returns a list of all Wrye Bash files as
    relative paths to the Mopy directory.

    :param bash_path: The relative path from Mopy.
    :param cur_dir: The directory to look for modules in.
    :param _files: Internal parameter used to collect files recursively."""
    if _files is None: _files = []
    _files.extend([os.path.join(bash_path, m) for m in os.listdir(cur_dir)
                   if m.lower().endswith(('.py', '.pyw'))]) ##: glob?
    # Find packages - returned format is (module_loader, name, is_pkg)
    for module_loader, pkg_name, is_pkg in pkgutil.iter_modules([cur_dir]):
        if not is_pkg: # Skip it if it's not a package
            continue
        # Recurse into the package we just found
        _find_all_bash_modules(
            os.path.join(bash_path, pkg_name) if bash_path else 'bash',
            os.path.join(cur_dir, pkg_name), _files)
    return _files

def main(args):
    setup_log(_LOGGER, args)
    old_pot = L10N_PATH / 'template.pot'
    new_pot = L10N_PATH / 'template_new.pot'
    gt_args = ['_ignored', '-a', '-o', new_pot]
    _LOGGER.info('Crawling Mopy for Python modules')
    gt_args.extend(_find_all_bash_modules('Mopy', MOPY_PATH))
    _LOGGER.info('Calling pygettext with discovered modules')
    old_argv = sys.argv[:]
    sys.argv = gt_args
    pygettext.main()
    sys.argv = old_argv
    # Add the project name and current version
    def edit_project_id(_ma):
        return fr'"Project-Id-Version: Wrye Bash v{bass.AppVersion}\n"'
    _LOGGER.debug('Fixing Project-Id-Version')
    edit_wb_file('bash', 'l10n', 'template_new.pot',
        trigger_regex=re.compile(r'^"Project-Id-Version: PACKAGE '
                                 r'VERSION\\n"$'),
        edit_callback=edit_project_id, logger=_LOGGER)
    # Fix the POT creation date in place to avoid tons of commits
    def edit_pot_creation_date(_ma):
        return r'"POT-Creation-Date: 2024-01-07 22:03+0100\n"'
    _LOGGER.debug('Fixing POT-Creation-Date')
    edit_wb_file('bash', 'l10n', 'template_new.pot',
        trigger_regex=re.compile(r'^"POT-Creation-Date: [^\\]+\\n"$'),
        edit_callback=edit_pot_creation_date, logger=_LOGGER)
    # pygettext always throws an extra newline at the end, get rid of that
    # (otherwise git's newline checks prevent you from committing it)
    _LOGGER.debug('Removing extraneous newline')
    with new_pot.open('r+', encoding='utf-8') as pot:
        pot_data = pot.read()
        pot.seek(0, os.SEEK_SET)
        pot.truncate(0)
        pot.write(pot_data[:-1])
    _LOGGER.info('Overwriting template.pot with new data')
    try:
        os.rename(new_pot, old_pot)
    except OSError:
        fatal_error('Failed to replace old l10n template with new version:',
            exit_code=3, log_traceback=True, logger=_LOGGER)
    _LOGGER.info('Successfully updated template.pot')

if __name__ == '__main__':
    run_script(main, __doc__, _LOGFILE)
