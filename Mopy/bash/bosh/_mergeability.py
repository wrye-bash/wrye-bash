# -*- coding: utf-8 -*-
#
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
"""Tmp module to get mergeability stuff out of bosh.__init__.py."""
from .. import bass, bush
from ..bolt import GPath
from ..cint import ObCollection
from ..exception import ModError
from ..load_order import cached_is_active
from ..parsers import ModFile, LoadFactory

def _is_mergeable_no_load(modInfo, reasons):
    verbose = reasons is not None
    if modInfo.has_esm_flag():
        if not verbose: return False
        reasons.append(_(u'Is esm.'))
    #--Bashed Patch
    if modInfo.isBP():
        if not verbose: return False
        reasons.append(_(u'Is Bashed Patch.'))
    #--Bsa / blocking resources?
    has_resources = modInfo.hasResources()
    if tuple(has_resources) != (False, False):
        if not verbose: return False
        hasBsa, has_blocking_resources = has_resources
        if hasBsa:
            reasons.append(_(u'Has BSA archive.'))
        if has_blocking_resources:
            facegen_dir_1 = _format_blocking_dir(bush.game.pnd.facegen_dir_1)
            facegen_dir_2 = _format_blocking_dir(bush.game.pnd.facegen_dir_2)
            voice_dir = _format_blocking_dir(bush.game.pnd.voice_dir)
            dir_list = u''
            for blocking_dir in (facegen_dir_1, facegen_dir_2, voice_dir):
                if blocking_dir:
                    dir_list += u'\n  - ' + blocking_dir
            reasons.append(_(u'Has plugin-specific directory - one of the '
                             u'following:' + dir_list) %
                           ({'plugin_name': modInfo.name.s}))
    # Client must make sure NoMerge tag not in tags - if in tags
    # don't show up as mergeable.
    return False if reasons else True

def _format_blocking_dir(blocking_dir):
    """Formats a path with path separators. Returns u'' for empty paths."""
    if blocking_dir:
        return u'\\'.join(blocking_dir) + u'\\%(plugin_name)s'
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
    if not  _pbash_mergeable_no_load(modInfo, reasons) and not verbose:
        return False  # non verbose mode
    #--Load test
    mergeTypes = set(recClass.classType for recClass in bush.game.mergeClasses)
    modFile = ModFile(modInfo, LoadFactory(False, *mergeTypes))
    try:
        modFile.load(True,loadStrings=False)
    except ModError as error:
        if not verbose: return False
        reasons.append(u'%s.' % error)
    #--Skipped over types?
    if modFile.topsSkipped:
        if not verbose: return False
        reasons.append(_(u'Unsupported types: ')+u', '.join(sorted(modFile.topsSkipped))+u'.')
    #--Empty mod
    elif not modFile.tops:
        if not verbose: return False
        reasons.append(_(u'Empty mod.'))
    #--New record
    lenMasters = len(modFile.tes4.masters)
    newblocks = []
    for top_type,block in modFile.tops.iteritems():
        for record in block.getActiveRecords():
            if record.fid >> 24 >= lenMasters:
                if record.flags1.deleted: continue #if new records exist but are deleted just skip em.
                if not verbose: return False
                newblocks.append(top_type)
                break
    if newblocks: reasons.append(_(u'New record(s) in block(s): ')+u', '.join(sorted(newblocks))+u'.')
    dependent = _dependent(modInfo, minfos)
    if dependent:
        if not verbose: return False
        reasons.append(_(u'Is a master of mod(s): ')+u', '.join(sorted(dependent))+u'.')
    return False if reasons else True

def _dependent(modInfo, minfos):
    """Get mods for which modInfo is a master mod (excluding BPs and
    mergeable)."""
    dependent = [mname.s for mname, info in minfos.iteritems() if
                 not info.isBP() and modInfo.name in info.get_masters() and
                 mname not in minfos.mergeable]
    return dependent

def is_esl_capable(modInfo, _minfos, reasons):
    """Determines whether or not the specified mod can be converted to a light
    plugin. Optionally also returns the reasons it can't be converted.

    :param modInfo: The mod to check.
    :param _minfos: Ignored. Needed to mirror the signature of isPBashMergeable
                    and isCBashMergeable.
    :param reasons: A list of strings that should be filled with the reasons
                    why this mod can't be ESL flagged, or None if only the
                    return value of this method is of interest.
    :return: True if the specified mod could be flagged as ESL."""
    verbose = reasons is not None
    if modInfo.isBP():
        if not verbose: return False
        reasons.append(_(u'Is Bashed Patch.'))
    # FIXME check all record types - return undecidable (False) if record not decoded
    modFile = ModFile(modInfo, LoadFactory(False, *set(
        recClass.classType for recClass in bush.game.mergeClasses)))
    try:
        modFile.load(True,loadStrings=False)
    except ModError as error:
        if not verbose: return False
        reasons.append(u'%s.' % error)
    #--Skipped over types?
    if modFile.topsSkipped:
        if not verbose: return False
        reasons.append(_(u'Record type: ') + u', '.join(sorted(
            modFile.topsSkipped)) + u' ; currently unsupported by ESLify ' \
                                    u'verification. Use xEdit to check ESL '
                                    u'qualifications and modify ESL flag.')
    #--Form greater then 0xFFF
    lenMasters = len(modFile.tes4.masters)
    for rec_typ,block in modFile.tops.iteritems():
        for record in block.getActiveRecords():
            if record.fid >> 24 >= lenMasters:
                if (record.fid & 0xFFFFFF) > 0xFFF:
                    if not verbose: return False
                    reasons.append(_(u'New Forms greater than 0xFFF.'))
                    break
        else:
            continue
        break
    return False if reasons else True

def _modIsMergeableLoad(modInfo, minfos, reasons):
    """Check if mod is mergeable, loading it and taking into account the
    rest of mods."""
    verbose = reasons is not None
    allowMissingMasters = {u'Filter', u'IIM', u'InventOnly'}
    tags = modInfo.getBashTags()
    #--Load test
    with ObCollection(ModsPath=bass.dirs['mods'].s) as Current:
        #MinLoad, InLoadOrder, AddMasters, TrackNewTypes, SkipAllRecords
        modFile = Current.addMod(modInfo.getPath().stail, Flags=0x00002129)
        Current.load()
        missingMasters = []
        nonActiveMasters = []
        masters = modFile.TES4.masters
        for master in masters:
            master = GPath(master)
            if not tags & allowMissingMasters:
                if master not in minfos:
                    if not verbose: return False
                    missingMasters.append(master.s)
                elif not cached_is_active(master):
                    if not verbose: return False
                    nonActiveMasters.append(master.s)
        #--masters not present in mod list?
        if len(missingMasters):
            if not verbose: return False
            reasons.append(_(u'Masters missing: ')+u'\n    * %s' % (u'\n    * '.join(sorted(missingMasters))))
        if len(nonActiveMasters):
            if not verbose: return False
            reasons.append(_(u'Masters not active: ')+u'\n    * %s' % (u'\n    * '.join(sorted(nonActiveMasters))))
        #--Empty mod
        if modFile.IsEmpty():
            if not verbose: return False
            reasons.append(_(u'Empty mod.'))
        #--New record
        else:
            if not tags & allowMissingMasters:
                newblocks = modFile.GetNewRecordTypes()
                if newblocks:
                    if not verbose: return False
                    reasons.append(_(u'New record(s) in block(s): %s.') % u', '.join(sorted(newblocks)))
        # dependent mods mergeability should be determined BEFORE their masters
        dependent = _dependent(modInfo, minfos)
        if dependent:
            if not verbose: return False
            reasons.append(_(u'Is a master of non-mergeable mod(s): %s.') % u', '.join(sorted(dependent)))
    return False if reasons else True

def isCBashMergeable(modInfo, minfos, reasons):
    """Returns True or error message indicating whether specified mod is mergeable."""
    verbose = reasons is not None
    if modInfo.name.s == u"Oscuro's_Oblivion_Overhaul.esp":
        if verbose: return [u'\n.    ' +
            _(u'Marked non-mergeable at request of mod author.')]
        return False
    if not  _is_mergeable_no_load(modInfo, reasons) and not verbose:
        return False
    if not _modIsMergeableLoad(modInfo, minfos, reasons) and not verbose:
        return False
    return False if reasons else True
