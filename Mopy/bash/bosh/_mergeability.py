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
"""Tmp module to get mergeability stuff out of bosh.__init__.py."""
import os

from ..bolt import sig_to_str
from ..exception import ModError
from ..game import MasterFlag, MergeabilityCheck
from ..mod_files import LoadFactory, ModFile
__exit = lambda x: True # trick to exit early on non-verbose mode

def _pbash_mergeable_no_load(modInfo, minfos, reasons, game_handle):
    _exit = __exit if reasons is None else reasons.append # append returns None
    if MasterFlag.ESM.has_flagged(modInfo) and _exit(_('This plugin has the ESM flag.')):
        return False
    #--Bashed Patch
    if modInfo.isBP() and _exit(_('This plugin is a Bashed Patch.')):
        return False
    # Plugin INIs would get deactivated if the plugin got merged
    if ((plugin_ini_name := modInfo.get_ini_name()) in minfos.plugin_inis and
            _exit(_('This plugin has an associated INI file '
                    '(%(plugin_ini_name)s).') % {
                'plugin_ini_name': plugin_ini_name})):
        return False
    #--Bsa / blocking resources?
    hasBsa, has_blocking_resources = modInfo.hasResources()
    if hasBsa and _exit(_('This plugin has an associated %(bsa_ext)s '
                          'file.') % {'bsa_ext': game_handle.Bsa.bsa_extension}):
        return False
    if has_blocking_resources:
        dir_list = '\n  - '.join(f'{pnd}{os.sep}%(blocking_plugin_name)s'
            for pnd in game_handle.plugin_name_specific_dirs if pnd)
        if _exit((_('Has plugin-specific directory - one of the following:') +
              f'\n  - {dir_list}') % {'blocking_plugin_name': modInfo.fn_key}):
            return False
    #--Missing Strings Files?
    if modInfo.fn_key in minfos.missing_strings:
        if reasons is None: return False
        from . import oblivionIni
        i_lang = oblivionIni.get_ini_language(game_handle.Ini.default_game_lang)
        strings_example = (f'{os.path.join("Strings", modInfo.fn_key.fn_body)}'
                           f'_{i_lang}.STRINGS')
        reasons.append(_('Missing string translation files '
                         '(%(strings_example)s, etc).') % {
            'strings_example': strings_example})
    # Client must make sure NoMerge tag not in tags - if in tags
    # don't show up as mergeable.
    return False if reasons else True

def isPBashMergeable(modInfo, minfos, reasons, game_handle):
    """Returns True or error message indicating whether specified mod is mergeable."""
    if not _pbash_mergeable_no_load(modInfo, minfos, reasons, game_handle) \
            and reasons is None:
        return False  # non verbose mode
    _exit = __exit if reasons is None else reasons.append # append returns None
    if not game_handle.Esp.canBash and _exit(
        _('Wrye Bash does not currently support loading plugins for '
          '%(game_name)s.') % {'game_name': game_handle.display_name}):
        return False
    #--Load test: use generic MreRecord (without unpacking). ModFile.load will
    # unpack the header which is enough for record.flags1|fid checks
    merge_types_fact = LoadFactory(False, generic=game_handle.mergeable_sigs)
    modFile = ModFile(modInfo, merge_types_fact)
    try:
        modFile.load_plugin(loadStrings=False, catch_errors=False)
    except ModError as error:
        if _exit(f'{error}.'): return False
    #--Skipped over types?
    if modFile.topsSkipped and _exit(
            _('Wrye Bash does not support the following record types: '
              '%(unsupported_rec_types)s.') % {
                'unsupported_rec_types': _join_sigs(modFile.topsSkipped)}):
        return False
    #--Empty mod
    elif not modFile.tops and _exit(_('This plugin is empty.')):
        return False
    #--New record
    newblocks = []
    self_name = modInfo.fn_key
    for top_sig, block in modFile.tops.items():
        for candidate_rec in block.iter_records(): # skip deleted/ignored
            if candidate_rec.group_key().mod_fn == self_name:
                if reasons is None: return False
                newblocks.append(top_sig)
                break
    if newblocks: reasons.append(
        _('This plugin has new records in the following groups: '
          '%(new_rec_groups)s.') % {'new_rec_groups': _join_sigs(newblocks)})
    dependent = _dependent(self_name, minfos)
    if dependent and _exit(_('This plugin is a master of the following non-mergeable '
              'plugins: %(non_mergeable_plugins)s.') % {
                'non_mergeable_plugins': ', '.join(sorted(dependent))}):
        return False
    return False if reasons else True

def _join_sigs(rec_sigs):
    return ', '.join(map(sig_to_str, sorted(rec_sigs)))

def _dependent(minfo_key, minfos):
    """Get mods for which modInfo is a master mod (excluding BPs and
    mergeable)."""
    dependent = [mname for mname, info in minfos.items() if
                 not info.isBP() and minfo_key in info.masterNames and
                 MergeabilityCheck.MERGE not in info.merge_types]
    return dependent
