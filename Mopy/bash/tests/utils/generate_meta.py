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
#  Wrye Bash copyright (C) 2005-2009 Wrye, 2010-2023 Wrye Bash Team
#  https://github.com/wrye-bash
#
# =============================================================================
"""Script for generating .meta files for each type of resource. Must be run on
files inside the correct folder, as how to read the file is deduced based on
the file extension and the name of the game folder it is in.

Note also that you should double-check the results, because the information
stored in the resulting .meta file is of course read through Wrye Bash's
internal APIs. If there is a bug in there, such a test file most likely won't
catch it."""
import argparse
import os
import sys

from .. import resource_to_unique_display_name, set_game
from ... import bush
from ...bosh.cosaves import _xSEHeader, get_cosave_types, xSECosave

def generate_meta_bsa(target_file):
    print(u"Skipping '%s': bsa .meta generation not implemented yet" %
          target_file)

def generate_meta_cosave_xse(target_file):
    gm_name = os.path.basename(os.path.dirname(target_file))
    try:
        gm_unique_dn = resource_to_unique_display_name[gm_name]
    except KeyError:
        print(f"No valid game found in parent directories of file '"
              f"{target_file}'")
        sys.exit(4)
    set_game(gm_unique_dn)
    get_cosave_types(bush.game.fsName, None, bush.game.Se.cosave_tag,
                     bush.game.Se.cosave_ext)
    test_cosave = xSECosave(target_file)
    test_cosave.read_cosave()
    with open(target_file + u'.meta', u'w', encoding=u'utf-8') as out:
        # xSE cosave header ---------------------------------------------------
        cosv_header = test_cosave.cosave_header # type: _xSEHeader
        out.write(u'[cosave_header]\n')
        out.write(u'savefile_tag = "%s"\n' % cosv_header.savefile_tag)
        out.write(u'format_version = %u\n' % cosv_header.format_version)
        out.write(u'se_version = %u\n' % cosv_header.se_version)
        out.write(u'se_minor_version = %u\n' % cosv_header.se_minor_version)
        out.write(u'game_version = 0x%08X\n' % cosv_header.game_version)
        out.write(u'num_plugin_chunks = %u\n' % cosv_header.num_plugin_chunks)
        out.write(u'\n[cosave_body]\n')
        out.write(u'cosave_masters = [\n')
        for m in test_cosave.get_master_list():
            out.write(u'    "%s",\n' % m)
        out.write(u']\n')
        accurate_masters = (not bush.game.has_esl or
                            test_cosave.has_accurate_master_list())
        out.write(u'masters_are_accurate = %s\n' %
                  str(accurate_masters).lower())
    ##: Once all are implemented, move to process_file
    print(u"Metadata successfully generated and written to '%s'" % (
            target_file + u'.meta'))

def generate_meta_cosave_pluggy(target_file):
    print(u"Skipping '%s': pluggy .meta generation not implemented yet" %
          target_file)

def generate_meta_plugin(target_file):
    print(u"Skipping '%s': plugin .meta generation not implemented yet" %
          target_file)

def generate_meta_save(target_file):
    print(u"Skipping '%s': save .meta generation not implemented yet" %
          target_file)

def process_file(target_file):
    if not os.path.isfile(target_file):
        print(u"Target file '%s' does not exist or is not a "
              u"file" % target_file)
        sys.exit(1)
    target_ext = os.path.splitext(target_file)[1]
    try:
        _generator_mapping[target_ext](target_file)
    except KeyError:
        print(u"Could not deduce resource type from extension "
              u"'%s'" % target_ext)
        sys.exit(2)

_generator_mapping = {
    u'.ba2': generate_meta_bsa,
    u'.bsa': generate_meta_bsa,
    u'.ess': generate_meta_save,
    u'.fos': generate_meta_save,
    u'.pluggy': generate_meta_cosave_pluggy,
}

for e in (u'.obse', u'.fose', u'.nvse', u'.skse', u'.f4se'):
    _generator_mapping[e] = generate_meta_cosave_xse

if __name__ == u'__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument(u'target_file_or_folder', type=str,
                        help=u'the file to generate a .meta file for')
    parsed_args = parser.parse_args()
    target_file_or_folder = parsed_args.target_file_or_folder
    if not os.path.isabs(target_file_or_folder):
        target_file_or_folder = os.path.abspath(target_file_or_folder)
    all_files = ([target_file_or_folder]
                 if os.path.isfile(target_file_or_folder)
                 else os.listdir(target_file_or_folder))
    for curr_file in all_files:
        # Skip .meta files, for obvious reasons
        if not curr_file.endswith(u'.meta'):
            if not os.path.isabs(curr_file):
                curr_file = os.path.join(target_file_or_folder, curr_file)
            process_file(curr_file)
