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
#  Wrye Bash copyright (C) 2005-2009 Wrye, 2010-2022 Wrye Bash Team
#  https://github.com/wrye-bash
#
# =============================================================================
"""Tmp module to get mergeability stuff out of bosh.__init__.py."""
import os

from .. import bush
from ..bolt import sig_to_str
from ..exception import ModError
from ..mod_files import LoadFactory, ModHeaderReader, ModFile

def _is_mergeable_no_load(modInfo, reasons):
    verbose = reasons is not None
    if modInfo.has_esm_flag():
        if not verbose: return False
        reasons.append(_(u'Has ESM flag.'))
    #--Bashed Patch
    if modInfo.isBP():
        if not verbose: return False
        reasons.append(_(u'Is Bashed Patch.'))
    #--Bsa / blocking resources?
    has_resources = modInfo.hasResources()
    if has_resources != (False, False):
        if not verbose: return False
        hasBsa, has_blocking_resources = has_resources
        if hasBsa:
            reasons.append(_(u'Has BSA archive.'))
        if has_blocking_resources:
            dir_list = u''
            for pnd in bush.game.plugin_name_specific_dirs:
                blocking_dir = _format_blocking_dir(pnd)
                if blocking_dir:
                    dir_list += u'\n  - ' + blocking_dir
            reasons.append((_(u'Has plugin-specific directory - one of the '
                              u'following:') + dir_list) % {
                u'plugin_name': modInfo.ci_key})
    # Client must make sure NoMerge tag not in tags - if in tags
    # don't show up as mergeable.
    return False if reasons else True

def _format_blocking_dir(blocking_dir):
    """Formats a path with path separators. Returns u'' for empty paths."""
    if blocking_dir:
        return blocking_dir + os.sep + u'%(plugin_name)s'
    else:
        return u''

def _pbash_mergeable_no_load(modInfo, reasons):
    verbose = reasons is not None
    if not _is_mergeable_no_load(modInfo, reasons) and not verbose:
        return False  # non verbose mode
    #--Missing Strings Files?
    if modInfo.isMissingStrings():
        if not verbose: return False
        from . import oblivionIni
        reasons.append(_(u'Missing String Translation Files (Strings\\%s_%s.STRINGS, etc).') % (
            modInfo.name.sbody, oblivionIni.get_ini_language()))
    return False if reasons else True

def isPBashMergeable(modInfo, minfos, reasons):
    """Returns True or error message indicating whether specified mod is mergeable."""
    verbose = reasons is not None
    if not _pbash_mergeable_no_load(modInfo, reasons) and not verbose:
        return False  # non verbose mode
    #--Load test: use generic MreRecord (without unpacking). ModFile.load will
    # unpack the header which is enough for record.flags1|fid checks
    merge_types_fact = LoadFactory(False, generic=bush.game.mergeable_sigs)
    modFile = ModFile(modInfo, merge_types_fact)
    try:
        modFile.load(True,loadStrings=False)
    except ModError as error:
        if not verbose: return False
        reasons.append(u'%s.' % error)
    #--Skipped over types?
    if modFile.topsSkipped:
        if not verbose: return False
        reasons.append(
            _(u'Unsupported types: ') + f'{_join_sigs(modFile.topsSkipped)}.')
    #--Empty mod
    elif not modFile.tops:
        if not verbose: return False
        reasons.append(_(u'Empty mod.'))
    #--New record
    newblocks = []
    self_name = modInfo.ci_key
    for top_type,block in modFile.tops.items():
        for rfid, record in block.iter_present_records(): # skip deleted/ignored
            if rfid[0] == self_name:
                if not verbose: return False
                newblocks.append(top_type)
                break
    if newblocks: reasons.append(
        _(u'New record(s) in block(s): ') + f'{_join_sigs(newblocks)}.')
    dependent = _dependent(self_name, minfos)
    if dependent:
        if not verbose: return False
        reasons.append(_(u'Is a master of non-mergeable mod(s): ')+u', '.join(sorted(dependent))+u'.')
    return False if reasons else True

def _join_sigs(sigs):
    return ', '.join(map(sig_to_str, sorted(sigs)))

def _dependent(minfo_key, minfos):
    """Get mods for which modInfo is a master mod (excluding BPs and
    mergeable)."""
    dependent = [mname.s for mname, info in minfos.items() if
                 not info.isBP() and minfo_key in info.masterNames and
                 mname not in minfos.mergeable]
    return dependent

def is_esl_capable(modInfo, _minfos, reasons):
    """Determines whether or not the specified mod can be converted to a light
    plugin. Optionally also returns the reasons it can't be converted.

    :param modInfo: The mod to check.
    :param _minfos: Ignored. Needed to mirror the signature of
                    isPBashMergeable.
    :param reasons: A list of strings that should be filled with the reasons
                    why this mod can't be ESL flagged, or None if only the
                    return value of this method is of interest.
    :return: True if the specified mod could be flagged as ESL."""
    verbose = reasons is not None
    formids_valid = True
    try:
        formids_valid = ModHeaderReader.formids_in_esl_range(modInfo)
    except ModError as e:
        if not verbose: return False
        reasons.append(u'%s.' % e)
    if not formids_valid:
        if not verbose: return False
        reasons.append(_(u'New FormIDs greater than 0xFFF.'))
    return False if reasons else True
