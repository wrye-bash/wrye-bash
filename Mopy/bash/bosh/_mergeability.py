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
#  Wrye Bash copyright (C) 2005-2009 Wrye, 2010-2015 Wrye Bash Team
#  https://github.com/wrye-bash
#
# =============================================================================
"""Tmp module to get mergeability stuff out of bosh.__init__.py."""
# FIXME(ut): methods return True or a list resulting in if result == True tests and complicated logic
from .. import bass, bush
from ..bolt import GPath
from ..brec import ModError
from ..cint import ObCollection
from ..load_order import cached_is_active
from ..parsers import ModFile, LoadFactory

def _is_mergeable_no_load(modInfo, verbose):
    reasons = []
    if modInfo.isEsm():
        if not verbose: return False
        reasons.append(u'\n.    '+_(u'Is esm.'))
    #--Bashed Patch
    if modInfo.header.author == u'BASHED PATCH':
        if not verbose: return False
        reasons.append(u'\n.    '+_(u'Is Bashed Patch.'))
    #--Bsa / voice?
    if modInfo.isMod() and tuple(modInfo.hasResources()) != (False,False):
        if not verbose: return False
        hasBsa, hasVoices = modInfo.hasResources()
        if hasBsa:
            reasons.append(u'\n.    '+_(u'Has BSA archive.'))
        if hasVoices:
            reasons.append(u'\n.    '+_(u'Has associated voice directory (Sound\\Voice\\%s).') % modInfo.name.s)
    #-- Check to make sure NoMerge tag not in tags - if in tags don't show up as mergeable.
    if reasons: return reasons
    return True

def pbash_mergeable_no_load(modInfo, verbose):
    reasons = _is_mergeable_no_load(modInfo, verbose)
    if isinstance(reasons, list):
        reasons = u''.join(reasons)
    elif not reasons:
        return False # non verbose mode
    else: # True
        reasons = u''
    #--Missing Strings Files?
    if modInfo.isMissingStrings():
        if not verbose: return False
        from . import oblivionIni
        reasons += u'\n.    '+_(u'Missing String Translation Files (Strings\\%s_%s.STRINGS, etc).') % (
            modInfo.name.sbody, oblivionIni.get_ini_language())
    if reasons: return reasons
    return True

def isPBashMergeable(modInfo, minfos, verbose):
    """Returns True or error message indicating whether specified mod is mergeable."""
    reasons = pbash_mergeable_no_load(modInfo, verbose)
    if isinstance(reasons, unicode):
        pass
    elif not reasons:
        return False # non verbose mode
    else: # True
        reasons = u''
    #--Load test
    mergeTypes = set(recClass.classType for recClass in bush.game.mergeClasses)
    modFile = ModFile(modInfo, LoadFactory(False, *mergeTypes))
    try:
        modFile.load(True,loadStrings=False)
    except ModError as error:
        if not verbose: return False
        reasons += u'\n.    %s.' % error
    #--Skipped over types?
    if modFile.topsSkipped:
        if not verbose: return False
        reasons += u'\n.    '+_(u'Unsupported types: ')+u', '.join(sorted(modFile.topsSkipped))+u'.'
    #--Empty mod
    elif not modFile.tops:
        if not verbose: return False
        reasons += u'\n.    '+ u'Empty mod.'
    #--New record
    lenMasters = len(modFile.tes4.masters)
    newblocks = []
    for type,block in modFile.tops.iteritems():
        for record in block.getActiveRecords():
            if record.fid >> 24 >= lenMasters:
                if record.flags1.deleted: continue #if new records exist but are deleted just skip em.
                if not verbose: return False
                newblocks.append(type)
                break
    if newblocks: reasons += u'\n.    '+_(u'New record(s) in block(s): ')+u', '.join(sorted(newblocks))+u'.'
    dependent = [name.s for name, info in minfos.iteritems()
                 if info.header.author != u'BASHED PATCH'
                 if modInfo.name in info.header.masters]
    if dependent:
        if not verbose: return False
        reasons += u'\n.    '+_(u'Is a master of mod(s): ')+u', '.join(sorted(dependent))+u'.'
    if reasons: return reasons
    return True

def cbash_mergeable_no_load(modInfo, verbose):
    """Check if mod is mergeable without taking into account the rest of mods"""
    return _is_mergeable_no_load(modInfo, verbose)

def _modIsMergeableLoad(modInfo, minfos, verbose):
    """Check if mod is mergeable, loading it and taking into account the
    rest of mods."""
    allowMissingMasters = {u'Filter', u'IIM', u'InventOnly'}
    tags = modInfo.getBashTags()
    reasons = []

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
            reasons.append(u'\n.    '+_(u'Masters missing: ')+u'\n    * %s' % (u'\n    * '.join(sorted(missingMasters))))
        if len(nonActiveMasters):
            if not verbose: return False
            reasons.append(u'\n.    '+_(u'Masters not active: ')+u'\n    * %s' % (u'\n    * '.join(sorted(nonActiveMasters))))
        #--Empty mod
        if modFile.IsEmpty():
            if not verbose: return False
            reasons.append(u'\n.    '+_(u'Empty mod.'))
        #--New record
        else:
            if not tags & allowMissingMasters:
                newblocks = modFile.GetNewRecordTypes()
                if newblocks:
                    if not verbose: return False
                    reasons.append(u'\n.    '+_(u'New record(s) in block(s): %s.') % u', '.join(sorted(newblocks)))
        # dependent mods mergeability should be determined BEFORE their masters
        dependent = [name.s for name, info in minfos.iteritems()
            if info.header.author != u'BASHED PATCH' and
            modInfo.name in info.header.masters and name not in minfos.mergeable]
        if dependent:
            if not verbose: return False
            reasons.append(u'\n.    '+_(u'Is a master of non-mergeable mod(s): %s.') % u', '.join(sorted(dependent)))
        if reasons: return reasons
        return True

def isCBashMergeable(modInfo, minfos, verbose):
    """Returns True or error message indicating whether specified mod is mergeable."""
    if modInfo.name.s == u"Oscuro's_Oblivion_Overhaul.esp":
        if verbose: return u'\n.    ' + _(
            u'Marked non-mergeable at request of mod author.')
        return False
    canmerge = cbash_mergeable_no_load(modInfo, verbose)
    if verbose:
        loadreasons = _modIsMergeableLoad(modInfo, minfos, verbose)
        reasons = []
        if canmerge != True:
            reasons = canmerge
        if loadreasons != True:
            reasons.extend(loadreasons)
        if reasons: return u''.join(reasons)
        return True
    else:
        if canmerge == True:
            return _modIsMergeableLoad(modInfo, minfos, verbose)
        return False
