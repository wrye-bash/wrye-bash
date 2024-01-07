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
"""Tmp module to get mergeability stuff out of bosh.__init__.py."""
import os

from .. import bush
from ..bolt import sig_to_str
from ..exception import ModError
from ..mod_files import LoadFactory, ModFile, ModHeaderReader

def _pbash_mergeable_no_load(modInfo, minfos, reasons):
    verbose = reasons is not None
    _exit = lambda x: not verbose or reasons.append(x) # append returns None
    if modInfo.has_esm_flag() and _exit(_('This plugin has the ESM flag.')):
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
                          'file.') % {'bsa_ext': bush.game.Bsa.bsa_extension}):
        return False
    if has_blocking_resources:
        dir_list = '\n  - '.join(f'{pnd}{os.sep}%(blocking_plugin_name)s'
            for pnd in bush.game.plugin_name_specific_dirs if pnd)
        if _exit((_('Has plugin-specific directory - one of the following:') +
              f'\n  - {dir_list}') % {'blocking_plugin_name': modInfo.fn_key}):
            return False
    #--Missing Strings Files?
    if modInfo.isMissingStrings():
        if not verbose: return False
        from . import oblivionIni
        strings_example = (f'{os.path.join("Strings", modInfo.fn_key.fn_body)}'
                           f'_{oblivionIni.get_ini_language()}.STRINGS')
        reasons.append(_('Missing string translation files '
                         '(%(strings_example)s, etc).') % {
            'strings_example': strings_example})
    # Client must make sure NoMerge tag not in tags - if in tags
    # don't show up as mergeable.
    return False if reasons else True

def isPBashMergeable(modInfo, minfos, reasons):
    """Returns True or error message indicating whether specified mod is mergeable."""
    verbose = reasons is not None
    if not _pbash_mergeable_no_load(modInfo, minfos, reasons) and not verbose:
        return False  # non verbose mode
    _exit = lambda x: not verbose or reasons.append(x) # append returns None
    if not bush.game.Esp.canBash and _exit(
        _('Wrye Bash does not currently support loading plugins for '
          '%(game_name)s.') % {'game_name': bush.game.display_name}):
        return False
    #--Load test: use generic MreRecord (without unpacking). ModFile.load will
    # unpack the header which is enough for record.flags1|fid checks
    merge_types_fact = LoadFactory(False, generic=bush.game.mergeable_sigs)
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
                if not verbose: return False
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
    dependent = [mname for mname, info in minfos.items() if not info.isBP() and
                 minfo_key in info.masterNames and mname not in
                 minfos.mergeable_plugins]
    return dependent

def is_esl_capable(modInfo, _minfos, reasons):
    """Determine whether or not the specified mod can be converted to a light
    plugin. Optionally also return the reasons it can't be converted.

    :param modInfo: The mod to check.
    :param _minfos: Ignored. Needed to mirror the signature of
                    isPBashMergeable.
    :param reasons: A list of strings that should be filled with the reasons
                    why this mod can't be ESL flagged, or None if only the
                    return value of this method is of interest.
    :return: True if the specified mod could be flagged as ESL."""
    verbose = reasons is not None
    _exit = lambda x: not verbose or reasons.append(x) # append returns None
    if modInfo.is_esl() and _exit(_('This plugin is already ESL-flagged.')):
        return False
    if modInfo.is_overlay() and _exit(_('This plugin has the Overlay flag.')):
        return False
    formids_valid = True
    try:
        formids_valid = ModHeaderReader.formids_in_esl_range(modInfo)
    except ModError as e:
        if _exit(f'{e}.'): return False
    if not formids_valid and _exit(_('This plugin contains records with '
                                     'FormIDs greater than 0xFFF.')):
        return False
    return False if reasons else True

def is_overlay_capable(modInfo, _minfos, reasons):
    """Determine whether or not the specified mod can be converted to an
    overlay plugin. Optionally also return the reasons it can't be converted.

    :param modInfo: The mod to check.
    :param _minfos: Ignored. Needed to mirror the signature of
        isPBashMergeable.
    :param reasons: A list of strings that should be filled with the reasons
        why this mod can't be Overlay-flagged, or None if only the return value
        of this method is of interest.
    :return: True if the specified mod could be flagged as Overlay."""
    verbose = reasons is not None
    _exit = lambda x: not verbose or reasons.append(x) # append returns None
    if modInfo.is_overlay() and _exit(_('This plugin is already '
                                        'Overlay-flagged.')):
        return False
    if modInfo.is_esl() and _exit(_('This plugin has the ESL flag.')):
        return False
    if not modInfo.masterNames and _exit(_('This plugin does not have any '
                                           'masters.')):
        return False
    has_new_recs = False
    try:
        has_new_recs = ModHeaderReader.has_new_records(modInfo)
    except ModError as e:
        if _exit(f'{e}.'): return False
    if has_new_recs and _exit(_('This plugin contains new records.')):
        return False
    return False if reasons else True
