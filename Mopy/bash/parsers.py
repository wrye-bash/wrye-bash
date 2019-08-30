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

"""This module contains the parser classes used by the importer patcher classes
and the Mod_Import/Export Mods menu."""
import ctypes
from _ctypes import POINTER
from ctypes import cast, c_ulong
from operator import attrgetter, itemgetter
from collections import defaultdict
import re
# Internal
import bolt
import brec
import bush # for game
import bosh # for modInfos
import env
import load_order
from balt import Progress
from bolt import GPath, decode, deprint, CsvReader, csvFormat, SubProgress, \
    struct_pack, struct_unpack
from bass import dirs, inisettings
from brec import MreRecord, MelObject, _coerce, genFid, ModReader, ModWriter, \
    RecordHeader
from cint import ObCollection, FormID, aggregateTypes, validTypes, \
    MGEFCode, ActorValue, ValidateList, pickupables, ExtractExportList, \
    ValidateDict, IUNICODE, getattr_deep, setattr_deep
from exception import ArgumentError, MasterMapError, ModError, StateError
from record_groups import MobDials, MobICells, MobWorlds, MobObjects, MobBase

class ActorFactions:
    """Factions for npcs and creatures with functions for
    importing/exporting from/to mod/text file."""

    def __init__(self,aliases=None):
        self.types = tuple([MreRecord.type_class[x] for x in ('CREA','NPC_')])
        self.type_id_factions = {'CREA':{},'NPC_':{}} #--factions =
        # type_id_factions[type][longid]
        self.id_eid = {}
        self.aliases = aliases or {}
        self.gotFactions = set()

    def readFactionEids(self,modInfo):
        """Extracts faction editor ids from modInfo and its masters."""
        loadFactory = LoadFactory(False,MreRecord.type_class['FACT'])
        for modName in (modInfo.get_masters() + [modInfo.name]):
            if modName in self.gotFactions: continue
            modFile = ModFile(bosh.modInfos[modName],loadFactory)
            modFile.load(True)
            mapper = modFile.getLongMapper()
            for record in modFile.FACT.getActiveRecords():
                self.id_eid[mapper(record.fid)] = record.eid
            self.gotFactions.add(modName)

    def readFromMod(self,modInfo):
        """Imports faction data from specified mod."""
        self.readFactionEids(modInfo)
        type_id_factions,types,id_eid = self.type_id_factions,self.types,\
                                        self.id_eid
        loadFactory = LoadFactory(False,*types)
        modFile = ModFile(modInfo,loadFactory)
        modFile.load(True)
        mapper = modFile.getLongMapper()
        for type_ in (x.classType for x in types):
            typeBlock = modFile.tops.get(type_,None)
            if not typeBlock: continue
            id_factions = type_id_factions[type_]
            for record in typeBlock.getActiveRecords():
                longid = mapper(record.fid)
                if record.factions:
                    id_eid[longid] = record.eid
                    id_factions[longid] = [(mapper(x.faction),x.rank) for x in
                                           record.factions]

    def writeToMod(self,modInfo):
        """Exports faction data to specified mod."""
        type_id_factions,types = self.type_id_factions,self.types
        loadFactory = LoadFactory(True,*types)
        modFile = ModFile(modInfo,loadFactory)
        modFile.load(True)
        mapper = modFile.getLongMapper()
        shortMapper = modFile.getShortMapper()
        changed = defaultdict(int) # {'CREA':0,'NPC_':0}
        for type_ in (x.classType for x in types):
            id_factions = type_id_factions.get(type_,None)
            typeBlock = modFile.tops.get(type_,None)
            if not id_factions or not typeBlock: continue
            for record in typeBlock.records:
                longid = mapper(record.fid)
                if longid not in id_factions: continue
                newFactions = set(id_factions[longid])
                curFactions = set(
                    (mapper(x.faction),x.rank) for x in record.factions)
                changes = newFactions - curFactions
                if not changes: continue
                for faction,rank in changes:
                    faction = shortMapper(faction)
                    for entry in record.factions:
                        if entry.faction == faction:
                            entry.rank = rank
                            break
                    else:
                        entry = MelObject()
                        entry.faction = faction
                        entry.rank = rank
                        entry.unused1 = 'ODB'
                        record.factions.append(entry)
                    record.setChanged()
                changed[type_] += 1
        #--Done
        if sum(changed.values()): modFile.safeSave()
        return changed

    def readFromText(self,textPath):
        """Imports faction data from specified text file."""
        type_id_factions = self.type_id_factions
        aliases = self.aliases
        with CsvReader(textPath) as ins:
            for fields in ins:
                if len(fields) < 8 or fields[3][:2] != u'0x': continue
                type_,aed,amod,aobj,fed,fmod,fobj,rank = fields[:9]
                amod = GPath(amod)
                fmod = GPath(fmod)
                aid = (aliases.get(amod,amod),int(aobj[2:],16))
                fid = (aliases.get(fmod,fmod),int(fobj[2:],16))
                rank = int(rank)
                id_factions = type_id_factions[type_]
                factions = id_factions.get(aid)
                factiondict = dict(factions or [])
                factiondict.update({fid:rank})
                id_factions[aid] = [(fid,rank) for fid,rank in
                                    factiondict.iteritems()]

    def writeToText(self,textPath):
        """Exports faction data to specified text file."""
        type_id_factions,id_eid = self.type_id_factions,self.id_eid
        headFormat = u'"%s","%s","%s","%s","%s","%s","%s","%s"\n'
        rowFormat = u'"%s","%s","%s","0x%06X","%s","%s","0x%06X","%s"\n'
        with textPath.open('w',encoding='utf-8-sig') as out:
            out.write(headFormat % (
                _(u'Type'),_(u'Actor Eid'),_(u'Actor Mod'),_(u'Actor Object'),
                _(u'Faction Eid'),_(u'Faction Mod'),_(u'Faction Object'),
                _(u'Rank')))
            for type_ in sorted(type_id_factions):
                id_factions = type_id_factions[type_]
                for id_ in sorted(id_factions,
                                  key=lambda x:id_eid.get(x).lower()):
                    actorEid = id_eid.get(id_,u'Unknown')
                    for faction,rank in sorted(id_factions[id_],
                                               key=lambda x:id_eid.get(
                                                       x[0]).lower()):
                        factionEid = id_eid.get(faction,u'Unknown')
                        out.write(rowFormat % (
                            type_,actorEid,id_[0].s,id_[1],factionEid,
                            faction[0].s,faction[1],rank))

class CBash_ActorFactions:
    """Factions for npcs and creatures with functions for
    importing/exporting from/to mod/text file."""

    def __init__(self,aliases=None):
        self.group_fid_factions = {'CREA':{},'NPC_':{}} #--factions =
        # group_fid_factions[group][longid]
        self.fid_eid = {}
        self.aliases = aliases or {}
        self.gotFactions = set()

    def readFromMod(self,modInfo):
        """Imports faction data from specified mod."""
        group_fid_factions,fid_eid,gotFactions = self.group_fid_factions,\
                                                 self.fid_eid,self.gotFactions
        with ObCollection(ModsPath=dirs['mods'].s) as Current:
            importFile = Current.addMod(modInfo.getPath().stail,Saveable=False)
            Current.load()
            for modFile in Current.LoadOrderMods:
                modName = modFile.GName
                if modName in gotFactions: continue
                for record in modFile.FACT:
                    fid_eid[record.fid] = record.eid
                if modFile != importFile: continue
                types = dict((('CREA', modFile.CREA),('NPC_', modFile.NPC_)))
                for group,block in types.iteritems():
                    fid_factions = group_fid_factions[group]
                    for record in block:
                        fid = record.fid
                        factions = record.factions_list
                        if factions:
                            fid_eid[fid] = record.eid
                            fid_factions[fid] = factions
                modFile.Unload()
                gotFactions.add(modName)

    def writeToMod(self,modInfo):
        """Exports faction data to specified mod."""
        group_fid_factions = self.group_fid_factions
        with ObCollection(ModsPath=dirs['mods'].s) as Current:
            modFile = Current.addMod(modInfo.getPath().stail,LoadMasters=False)
            Current.load()
            changed = defaultdict(int) # {'CREA':0,'NPC_':0}
            types = dict((('CREA', modFile.CREA),('NPC_', modFile.NPC_)))
            for group,block in types.iteritems():
                fid_factions = group_fid_factions.get(group,None)
                if fid_factions is not None:
                    fid_factions = FormID.FilterValidDict(fid_factions,modFile,
                                                          True,False)
                    for record in block:
                        fid = record.fid
                        if fid not in fid_factions: continue
                        newFactions = set([(faction,rank) for faction,rank in
                                           fid_factions[fid] if
                                           faction.ValidateFormID(modFile)])
                        curFactions = set([(faction,rank) for faction,rank in
                                           record.factions_list if
                                           faction.ValidateFormID(modFile)])
                        changes = newFactions - curFactions
                        if not changes: continue
                        for faction,rank in changes:
                            for entry in record.factions:
                                if entry.faction == faction:
                                    entry.rank = rank
                                    break
                            else:
                                entry = record.create_faction()
                                entry.faction = faction
                                entry.rank = rank
                        changed[group] += 1
            #--Done
            if sum(changed.values()): modFile.save()
            return changed

    def readFromText(self,textPath):
        """Imports faction data from specified text file."""
        group_fid_factions = self.group_fid_factions
        aliases = self.aliases
        with CsvReader(textPath) as ins:
            for fields in ins:
                if len(fields) < 8 or fields[3][:2] != u'0x': continue
                group,aed,amod,aobj,fed,fmod,fobj,rank = fields[:9]
                group = _coerce(group,unicode)
                amod = GPath(_coerce(amod,unicode))
                fmod = GPath(_coerce(fmod,unicode))
                aid = FormID(aliases.get(amod,amod),_coerce(aobj[2:],int,16))
                fid = FormID(aliases.get(fmod,fmod),_coerce(fobj[2:],int,16))
                rank = _coerce(rank, int)
                fid_factions = group_fid_factions[group]
                factions = fid_factions.get(aid)
                factiondict = dict(factions or [])
                factiondict.update({fid:rank})
                fid_factions[aid] = [(fid,rank) for fid,rank in
                                     factiondict.iteritems()]

    def writeToText(self,textPath):
        """Exports faction data to specified text file."""
        group_fid_factions,fid_eid = self.group_fid_factions, self.fid_eid
        headFormat = u'"%s","%s","%s","%s","%s","%s","%s","%s"\n'
        rowFormat = u'"%s","%s","%s","0x%06X","%s","%s","0x%06X","%s"\n'
        with textPath.open('w',encoding='utf-8-sig') as out:
            out.write(headFormat % (
                _(u'Type'),_(u'Actor Eid'),_(u'Actor Mod'),_(u'Actor Object'),
                _(u'Faction Eid'),_(u'Faction Mod'),_(u'Faction Object'),
                _(u'Rank')))
            for group in sorted(group_fid_factions):
                fid_factions = group_fid_factions[group]
                for fid in sorted(fid_factions,key = lambda x: fid_eid.get(x)):
                    actorEid = fid_eid.get(fid,u'Unknown')
                    for faction,rank in sorted(fid_factions[fid],
                                               key=lambda x:fid_eid.get(x[0])):
                        factionEid = fid_eid.get(faction,u'Unknown')
                        out.write(rowFormat % (
                            group,actorEid,fid[0].s,fid[1],factionEid,
                            faction[0].s,faction[1],rank))

#------------------------------------------------------------------------------
class ActorLevels:
    """Package: Functions for manipulating actor levels."""

    def __init__(self,aliases=None):
        self.mod_id_levels = {} #--levels = mod_id_levels[mod][longid]
        self.aliases = aliases or {}
        self.gotLevels = set()

    def readFromMod(self,modInfo):
        """Imports actor level data from the specified mod and its masters."""
        mod_id_levels, gotLevels = self.mod_id_levels, self.gotLevels
        loadFactory = LoadFactory(False,MreRecord.type_class['NPC_'])
        for modName in (modInfo.get_masters() + [modInfo.name]):
            if modName in gotLevels: continue
            modFile = ModFile(bosh.modInfos[modName],loadFactory)
            modFile.load(True)
            mapper = modFile.getLongMapper()
            for record in modFile.NPC_.getActiveRecords():
                id_levels = mod_id_levels.setdefault(modName,{})
                id_levels[mapper(record.fid)] = (
                    record.eid, bool(record.flags.pcLevelOffset),
                    record.level,record.calcMin,record.calcMax)
            gotLevels.add(modName)

    def writeToMod(self,modInfo):
        """Exports actor levels to specified mod."""
        mod_id_levels = self.mod_id_levels
        loadFactory = LoadFactory(True,MreRecord.type_class['NPC_'])
        modFile = ModFile(modInfo,loadFactory)
        modFile.load(True)
        mapper = modFile.getLongMapper()
        changed = 0
        id_levels = mod_id_levels.get(modInfo.name,
                                      mod_id_levels.get(GPath(u'Unknown'),
                                                        None))
        if id_levels:
            for record in modFile.NPC_.records:
                fid = mapper(record.fid)
                if fid in id_levels:
                    eid,isOffset,level,calcMin,calcMax = id_levels[fid]
                    if ((record.level,record.calcMin,record.calcMax) != (
                            level,calcMin,calcMax)):
                        (record.level,record.calcMin,record.calcMax) = (
                            level,calcMin,calcMax)
                        record.setChanged()
                        changed += 1
                    # else: print mod_id_levels
        #--Done
        if changed: modFile.safeSave()
        return changed

    def readFromText(self,textPath):
        """Imports NPC level data from specified text file."""
        mod_id_levels = self.mod_id_levels
        aliases = self.aliases
        with CsvReader(textPath) as ins:
            for fields in ins:
                if fields[0][:2] == u'0x': #old format
                    fid,eid,offset,calcMin,calcMax = fields[:5]
                    source = GPath(u'Unknown')
                    fidObject = _coerce(fid[4:], int, 16)
                    fid = (GPath(bush.game.masterFiles[0]), fidObject)
                    eid = _coerce(eid, unicode)
                    offset = _coerce(offset, int)
                    calcMin = _coerce(calcMin, int)
                    calcMax = _coerce(calcMax, int)
                else:
                    if len(fields) < 7 or fields[3][:2] != u'0x': continue
                    source,eid,fidMod,fidObject,offset,calcMin,calcMax = \
                        fields[:7]
                    source = _coerce(source, unicode)
                    if source.lower() in (u'none', bush.game.masterFiles[0].lower()): continue
                    source = GPath(source)
                    eid = _coerce(eid, unicode)
                    fidMod = GPath(_coerce(fidMod, unicode))
                    if fidMod.s.lower() == u'none': continue
                    fidObject = _coerce(fidObject[2:], int, 16)
                    if fidObject is None: continue
                    fid = (aliases.get(fidMod,fidMod),fidObject)
                    offset = _coerce(offset, int)
                    calcMin = _coerce(calcMin, int)
                    calcMax = _coerce(calcMax, int)
                id_levels = mod_id_levels.setdefault(source, {})
                id_levels[fid] = (eid, 1, offset, calcMin, calcMax)

    def writeToText(self,textPath):
        """Export NPC level data to specified text file."""
        mod_id_levels = self.mod_id_levels
        headFormat = u'"%s","%s","%s","%s","%s","%s","%s","%s","%s","%s",' \
                     u'"%s"\n'
        rowFormat = u'"%s","%s","%s","0x%06X","%d","%d","%d"'
        extendedRowFormat = u',"%d","%d","%d","%d"\n'
        blankExtendedRow = u',,,,\n'
        with textPath.open('w',encoding='utf') as out:
            out.write(headFormat % (
                _(u'Source Mod'),_(u'Actor Eid'),_(u'Actor Mod'),
                _(u'Actor Object'),_(u'Offset'),_(u'CalcMin'),_(u'CalcMax'),
                _(u'Old IsPCLevelOffset'),_(u'Old Offset'),_(u'Old CalcMin'),
                _(u'Old CalcMax')))
            #Sorted based on mod, then editor ID
            obId_levels = mod_id_levels[GPath(bush.game.masterFiles[0])]
            for mod in sorted(mod_id_levels):
                if mod.s.lower() == bush.game.masterFiles[0].lower(): continue
                id_levels = mod_id_levels[mod]
                for id_ in sorted(id_levels,key=lambda k:(
                        k[0].s.lower(),id_levels[k][0].lower())):
                    eid,isOffset,offset,calcMin,calcMax = id_levels[id_]
                    if isOffset:
                        source = mod.s
                        fidMod, fidObject = id_[0].s,id_[1]
                        out.write(rowFormat % (
                            source,eid,fidMod,fidObject,offset,calcMin,
                            calcMax))
                        oldLevels = obId_levels.get(id_,None)
                        if oldLevels:
                            oldEid,wasOffset,oldOffset,oldCalcMin,oldCalcMax\
                                = oldLevels
                            out.write(extendedRowFormat % (
                                wasOffset,oldOffset,oldCalcMin,oldCalcMax))
                        else:
                            out.write(blankExtendedRow)

class CBash_ActorLevels:
    """Package: Functions for manipulating actor levels."""

    def __init__(self,aliases=None):
        self.mod_fid_levels = {} #--levels = mod_id_levels[mod][longid]
        self.aliases = aliases or {}
        self.gotLevels = set()

    def readFromMod(self,modInfo):
        """Imports actor level data from the specified mod and its masters."""
        mod_fid_levels, gotLevels = self.mod_fid_levels, self.gotLevels
        with ObCollection(ModsPath=dirs['mods'].s) as Current:
            Current.addMod(u'Oblivion.esm', Saveable=False)
            Current.addMod(modInfo.getPath().stail, Saveable=False)
            Current.load()
            for modFile in Current.LoadOrderMods:
                modName = modFile.GName
                if modName in gotLevels: continue
                fid_levels = mod_fid_levels.setdefault(modName, {})
                for record in modFile.NPC_:
                    fid_levels[record.fid] = (
                        record.eid,record.IsPCLevelOffset and 1 or 0,
                        record.level,record.calcMin,record.calcMax)
                modFile.Unload()
                gotLevels.add(modName)

    def writeToMod(self,modInfo):
        """Exports actor levels to specified mod."""
        mod_fid_levels = self.mod_fid_levels
        with ObCollection(ModsPath=dirs['mods'].s) as Current:
            modFile = Current.addMod(modInfo.getPath().stail,LoadMasters=False)
            Current.load()
            changed = 0
            fid_levels = mod_fid_levels.get(modFile.GName,mod_fid_levels.get(
                GPath(u'Unknown'),None))
            if fid_levels:
                for record in modFile.NPC_:
                    fid = record.fid
                    if fid not in fid_levels: continue
                    eid,isOffset,level,calcMin,calcMax = fid_levels[fid]
                    if ((record.level,record.calcMin,record.calcMax) != (
                            level,calcMin,calcMax)):
                        (record.level,record.calcMin,record.calcMax) = (
                            level,calcMin,calcMax)
                        changed += 1
            #--Done
            if changed: modFile.save()
            return changed

    def readFromText(self,textPath):
        """Imports NPC level data from specified text file."""
        mod_fid_levels = self.mod_fid_levels
        aliases = self.aliases
        with CsvReader(textPath) as ins:
            for fields in ins:
                if fields[0][:2] == u'0x': #old format
                    fid,eid,offset,calcMin,calcMax = fields[:5]
                    source = GPath(u'Unknown')
                    fidObject = _coerce(fid[4:], int, 16)
                    fid = FormID(GPath(u'Oblivion.esm'), fidObject)
                    eid = _coerce(eid, unicode, AllowNone=True)
                    offset = _coerce(offset, int)
                    calcMin = _coerce(calcMin, int)
                    calcMax = _coerce(calcMax, int)
                else:
                    if len(fields) < 7 or fields[3][:2] != u'0x': continue
                    source,eid,fidMod,fidObject,offset,calcMin,calcMax = \
                        fields[:7]
                    source = _coerce(source, unicode)
                    if source.lower() in (u'none', u'oblivion.esm'): continue
                    source = GPath(source)
                    eid = _coerce(eid, unicode, AllowNone=True)
                    fidMod = GPath(_coerce(fidMod, unicode))
                    if fidMod.s.lower() == u'none': continue
                    fidObject = _coerce(fidObject[2:], int, 16)
                    if fidObject is None: continue
                    fid = FormID(aliases.get(fidMod,fidMod),fidObject)
                    offset = _coerce(offset, int)
                    calcMin = _coerce(calcMin, int)
                    calcMax = _coerce(calcMax, int)
                fid_levels = mod_fid_levels.setdefault(source, {})
                fid_levels[fid] = (eid, 1, offset, calcMin, calcMax)

    def writeToText(self,textPath):
        """Export NPC level data to specified text file."""
        mod_fid_levels = self.mod_fid_levels
        headFormat = u'"%s","%s","%s","%s","%s","%s","%s","%s","%s","%s",' \
                     u'"%s"\n'
        rowFormat = u'"%s","%s","%s","0x%06X","%d","%d","%d"'
        extendedRowFormat = u',"%d","%d","%d","%d"\n'
        blankExtendedRow = u',,,,\n'
        with textPath.open('w',encoding='utf-8-sig') as out:
            out.write(headFormat % (
                _(u'Source Mod'),_(u'Actor Eid'),_(u'Actor Mod'),
                _(u'Actor Object'),_(u'Offset'),_(u'CalcMin'),_(u'CalcMax'),
                _(u'Old IsPCLevelOffset'),_(u'Old Offset'),_(u'Old CalcMin'),
                _(u'Old CalcMax')))
            #Sorted based on mod, then editor ID
            obfid_levels = mod_fid_levels[GPath(u'Oblivion.esm')]
            for mod in sorted(mod_fid_levels):
                if mod.s.lower() == u'oblivion.esm': continue
                fid_levels = mod_fid_levels[mod]
                for fid in sorted(fid_levels,
                                  key=lambda k:(k[0].s,fid_levels[k][0])):
                    eid, isOffset, offset, calcMin, calcMax = fid_levels[fid]
                    if isOffset:
                        source = mod.s
                        fidMod,fidObject = fid[0].s,fid[1]
                        out.write(rowFormat % (
                            source,eid,fidMod,fidObject,offset,calcMin,
                            calcMax))
                        oldLevels = obfid_levels.get(fid,None)
                        if oldLevels:
                            oldEid,wasOffset,oldOffset,oldCalcMin,oldCalcMax\
                                = oldLevels
                            out.write(extendedRowFormat % (
                                wasOffset,oldOffset,oldCalcMin,oldCalcMax))
                        else:
                            out.write(blankExtendedRow)

#------------------------------------------------------------------------------
class EditorIds:
    """Editor ids for records, with functions for importing/exporting
    from/to mod/text file."""

    def __init__(self,types=None,aliases=None):
        self.type_id_eid = {} #--eid = eids[type][longid]
        self.old_new = {}
        if types:
            self.types = types
        else:
            self.types = set(MreRecord.simpleTypes)
            self.types.discard('CELL')
        self.aliases = aliases or {}

    def readFromMod(self,modInfo):
        """Imports eids from specified mod."""
        type_id_eid,types = self.type_id_eid,self.types
        classes = [MreRecord.type_class[x] for x in types]
        loadFactory = LoadFactory(False,*classes)
        modFile = ModFile(modInfo,loadFactory)
        modFile.load(True)
        mapper = modFile.getLongMapper()
        for type_ in types:
            typeBlock = modFile.tops.get(type_)
            if not typeBlock: continue
            if type_ not in type_id_eid: type_id_eid[type_] = {}
            id_eid = type_id_eid[type_]
            for record in typeBlock.getActiveRecords():
                longid = mapper(record.fid)
                if record.eid: id_eid[longid] = record.eid

    def writeToMod(self,modInfo):
        """Exports eids to specified mod."""
        type_id_eid,types = self.type_id_eid,self.types
        classes = [MreRecord.type_class[x] for x in types]
        loadFactory = LoadFactory(True,*classes)
        loadFactory.addClass(MreRecord.type_class['SCPT'])
        loadFactory.addClass(MreRecord.type_class['QUST'])
        modFile = ModFile(modInfo,loadFactory)
        modFile.load(True)
        mapper = modFile.getLongMapper()
        changed = []
        for type_ in types:
            id_eid = type_id_eid.get(type_,None)
            typeBlock = modFile.tops.get(type_,None)
            if not id_eid or not typeBlock: continue
            for record in typeBlock.records:
                longid = mapper(record.fid)
                newEid = id_eid.get(longid)
                oldEid = record.eid
                if newEid and record.eid and newEid != oldEid:
                    record.eid = newEid
                    record.setChanged()
                    changed.append((oldEid,newEid))
        #--Update scripts
        old_new = dict(self.old_new)
        old_new.update(
            dict([(oldEid.lower(),newEid) for oldEid,newEid in changed]))
        changed.extend(self.changeScripts(modFile,old_new))
        #--Done
        if changed: modFile.safeSave()
        return changed

    def changeScripts(self,modFile,old_new):
        """Changes scripts in modfile according to changed."""
        changed = []
        if not old_new: return changed
        reWord = re.compile('\w+')
        def subWord(match):
            word = match.group(0)
            newWord = old_new.get(word.lower())
            if not newWord:
                return word
            else:
                return newWord
        #--Scripts
        for script in sorted(modFile.SCPT.records,key=attrgetter('eid')):
            if not script.scriptText: continue
            newText = reWord.sub(subWord,script.scriptText)
            if newText != script.scriptText:
                # header = u'\r\n\r\n; %s %s\r\n' % (script.eid,u'-' * (77 -
                # len(script.eid))) # unused - bug ?
                script.scriptText = newText
                script.setChanged()
                changed.append((_(u"Script"),script.eid))
        #--Quest Scripts
        for quest in sorted(modFile.QUST.records,key=attrgetter('eid')):
            questChanged = False
            for stage in quest.stages:
                for entry in stage.entries:
                    oldScript = entry.scriptText
                    if not oldScript: continue
                    newScript = reWord.sub(subWord,oldScript)
                    if newScript != oldScript:
                        entry.scriptText = newScript
                        questChanged = True
            if questChanged:
                changed.append((_(u"Quest"),quest.eid))
                quest.setChanged()
        #--Done
        return changed

    def readFromText(self,textPath,questionableEidsSet=None,badEidsList=None):
        """Imports eids from specified text file."""
        type_id_eid = self.type_id_eid
        aliases = self.aliases
        with CsvReader(textPath) as ins:
            reValidEid = re.compile(u'^[a-zA-Z0-9]+$')
            reGoodEid = re.compile(u'^[a-zA-Z]')
            for fields in ins:
                if len(fields) < 4 or fields[2][:2] != u'0x': continue
                group,mod,objectIndex,eid = fields[:4]
                group = _coerce(group,unicode)
                mod = GPath(_coerce(mod,unicode))
                longid = (aliases.get(mod,mod),_coerce(objectIndex[2:],int,16))
                eid = _coerce(eid,unicode, AllowNone=True)
                if not reValidEid.match(eid):
                    if badEidsList is not None:
                        badEidsList.append(eid)
                    continue
                if questionableEidsSet is not None and not reGoodEid.match(
                        eid):
                    questionableEidsSet.add(eid)
                id_eid = type_id_eid.setdefault(group, {})
                id_eid[longid] = eid
                #--Explicit old to new def? (Used for script updating.)
                if len(fields) > 4:
                    self.old_new[_coerce(fields[4], unicode).lower()] = eid

    def writeToText(self,textPath):
        """Exports eids to specified text file."""
        type_id_eid = self.type_id_eid
        headFormat = u'"%s","%s","%s","%s"\n'
        rowFormat = u'"%s","%s","0x%06X","%s"\n'
        with textPath.open('w',encoding='utf-8-sig') as out:
            out.write(headFormat % (
                _(u'Type'),_(u'Mod Name'),_(u'ObjectIndex'),_(u'Editor Id')))
            for type_ in sorted(type_id_eid):
                id_eid = type_id_eid[type_]
                for id_ in sorted(id_eid,key = lambda a: id_eid[a].lower()):
                    out.write(rowFormat % (type_,id_[0].s,id_[1],id_eid[id_]))

class CBash_EditorIds:
    """Editor ids for records, with functions for importing/exporting
    from/to mod/text file."""

    def __init__(self,types=None,aliases=None):
        self.group_fid_eid = {} #--eid = group_fid_eid[group][longid]
        self.old_new = {}
        if types:
            self.groups = set(types)
        else:
            self.groups = aggregateTypes
        self.aliases = aliases or {}

    def readFromMod(self,modInfo):
        """Imports eids from specified mod."""
        group_fid_eid,groups = self.group_fid_eid,self.groups
        with ObCollection(ModsPath=dirs['mods'].s) as Current:
            modFile = Current.addMod(modInfo.getPath().stail,Saveable=False,
                                     LoadMasters=False)
            Current.load()
            for group in groups:
                fid_eid = group_fid_eid.setdefault(group[:4], {})
                for record in getattr(modFile, group):
                    eid = record.eid
                    if eid: fid_eid[record.fid] = eid
                modFile.Unload()

    def writeToMod(self,modInfo):
        """Exports eids to specified mod."""
        group_fid_eid = self.group_fid_eid
        with ObCollection(ModsPath=dirs['mods'].s) as Current:
            modFile = Current.addMod(modInfo.getPath().stail,LoadMasters=False)
            Current.load()
            changed = []
            for group,block in modFile.aggregates.iteritems():
                fid_eid = group_fid_eid.get(group[:4],None)
                if not fid_eid: continue
                for record in block:
                    fid = record.fid
                    newEid = fid_eid.get(fid)
                    oldEid = record.eid
                    if newEid and newEid != oldEid:
                        record.eid = newEid
                        if record.eid == newEid: #Can silently fail if a
                            # record keyed by editorID (GMST,MGEF) already has
                            # the value
                            changed.append((oldEid or u'',newEid or u''))
            #--Update scripts
            old_new = dict(self.old_new)
            old_new.update(
                dict([(oldEid.lower(),newEid) for oldEid,newEid in changed]))
            changed.extend(self.changeScripts(modFile,old_new))
            #--Done
            if changed: modFile.save()
            return changed

    def changeScripts(self,modFile,old_new):
        """Changes scripts in modfile according to changed."""
        changed = []
        if not old_new: return changed
        reWord = re.compile('\w+')
        def subWord(match):
            word = match.group(0)
            newWord = old_new.get(word.lower())
            if not newWord:
                return word
            else:
                return newWord
        #--Scripts
        for script in sorted(modFile.SCPT,key=attrgetter('eid')):
            if not script.scriptText: continue
            newText = reWord.sub(subWord,script.scriptText)
            if newText != script.scriptText:
                script.scriptText = newText
                changed.append((_(u"Script"),script.eid))
        #--Quest Scripts
        for quest in sorted(modFile.QUST,key=attrgetter('eid')):
            questChanged = False
            for stage in quest.stages:
                for entry in stage.entries:
                    oldScript = entry.scriptText
                    if not oldScript: continue
                    newScript = reWord.sub(subWord,oldScript)
                    if newScript != oldScript:
                        entry.scriptText = newScript
                        questChanged = True
            if questChanged:
                changed.append((_(u"Quest"),quest.eid))
        #--Done
        return changed

    def readFromText(self,textPath,questionableEidsSet=None,badEidsList=None):
        """Imports eids from specified text file."""
        group_fid_eid = self.group_fid_eid
        aliases = self.aliases
        with CsvReader(textPath) as ins:
            reValidEid = re.compile(u'^[a-zA-Z0-9]+$')
            reGoodEid = re.compile(u'^[a-zA-Z]')
            for fields in ins:
                if len(fields) < 4 or fields[2][:2] != u'0x': continue
                group,mod,objectIndex,eid = fields[:4]
                group = _coerce(group,unicode)[:4]
                if group not in validTypes: continue
                mod = GPath(_coerce(mod,unicode))
                longid = FormID(aliases.get(mod,mod),
                                _coerce(objectIndex[2:],int,16))
                eid = _coerce(eid,unicode, AllowNone=True)
                if not reValidEid.match(eid):
                    if badEidsList is not None:
                        badEidsList.append(eid)
                    continue
                if questionableEidsSet is not None and not reGoodEid.match(
                        eid):
                    questionableEidsSet.add(eid)
                fid_eid = group_fid_eid.setdefault(group, {})
                fid_eid[longid] = eid
                #--Explicit old to new def? (Used for script updating.)
                if len(fields) > 4:
                    self.old_new[_coerce(fields[4], unicode).lower()] = eid

    def writeToText(self,textPath):
        """Exports eids to specified text file."""
        group_fid_eid = self.group_fid_eid
        headFormat = u'"%s","%s","%s","%s"\n'
        rowFormat = u'"%s","%s","0x%06X","%s"\n'
        with textPath.open('w',encoding='utf-8-sig') as out:
            out.write(headFormat % (
                _(u'Type'),_(u'Mod Name'),_(u'ObjectIndex'),_(u'Editor Id')))
            for group in sorted(group_fid_eid):
                fid_eid = group_fid_eid[group]
                for fid in sorted(fid_eid,key = lambda a: fid_eid[a]):
                    out.write(rowFormat % (group,fid[0].s,fid[1],fid_eid[fid]))

#------------------------------------------------------------------------------
class FactionRelations:
    """Faction relations."""

    def __init__(self,aliases=None):
        self.id_relations = {} #--(otherLongid,otherDisp) = id_relation[longid]
        self.id_eid = {} #--For all factions.
        self.aliases = aliases or {}
        self.gotFactions = set()

    def readFactionEids(self,modInfo):
        """Extracts faction editor ids from modInfo and its masters."""
        loadFactory = LoadFactory(False,MreRecord.type_class['FACT'])
        for modName in (modInfo.get_masters() + [modInfo.name]):
            if modName in self.gotFactions: continue
            modFile = ModFile(bosh.modInfos[modName],loadFactory)
            modFile.load(True)
            mapper = modFile.getLongMapper()
            for record in modFile.FACT.getActiveRecords():
                self.id_eid[mapper(record.fid)] = record.eid
            self.gotFactions.add(modName)

    def readFromMod(self,modInfo):
        """Imports faction relations from specified mod."""
        self.readFactionEids(modInfo)
        loadFactory = LoadFactory(False,MreRecord.type_class['FACT'])
        modFile = ModFile(modInfo,loadFactory)
        modFile.load(True)
        modFile.convertToLongFids(('FACT',))
        for record in modFile.FACT.getActiveRecords():
            #--Following is a bit messy. If already have relations for a
            # given mod, want to do an in-place update. Otherwise do an append.
            relations = self.id_relations.get(record.fid)
            if relations is None:
                relations = self.id_relations[record.fid] = []
            other_index = dict((y[0],x) for x,y in enumerate(relations))
            for relation in record.relations:
                other,disp = relation.faction,relation.mod
                if other in other_index:
                    relations[other_index[other]] = (other,disp)
                else:
                    relations.append((other,disp))

    def readFromText(self,textPath):
        """Imports faction relations from specified text file."""
        id_relations = self.id_relations
        aliases = self.aliases
        with CsvReader(textPath) as ins:
            for fields in ins:
                if len(fields) < 7 or fields[2][:2] != u'0x': continue
                med,mmod,mobj,oed,omod,oobj,disp = fields[:9]
                mmod = _coerce(mmod, unicode)
                omod = _coerce(omod, unicode)
                mid = (GPath(aliases.get(mmod,mmod)),_coerce(mobj[2:],int,16))
                oid = (GPath(aliases.get(omod,omod)),_coerce(oobj[2:],int,16))
                disp = _coerce(disp, int)
                relations = id_relations.get(mid)
                if relations is None:
                    relations = id_relations[mid] = []
                for index,entry in enumerate(relations):
                    if entry[0] == oid:
                        relations[index] = (oid,disp)
                        break
                else:
                    relations.append((oid,disp))

    def writeToMod(self,modInfo):
        """Exports faction relations to specified mod."""
        id_relations = self.id_relations
        loadFactory= LoadFactory(True,MreRecord.type_class['FACT'])
        modFile = ModFile(modInfo,loadFactory)
        modFile.load(True)
        mapper = modFile.getLongMapper()
        shortMapper = modFile.getShortMapper()
        changed = 0
        for record in modFile.FACT.getActiveRecords():
            longid = mapper(record.fid)
            if longid not in id_relations: continue
            newRelations = set(id_relations[longid])
            curRelations = set(
                (mapper(x.faction),x.mod) for x in record.relations)
            changes = newRelations - curRelations
            if not changes: continue
            for faction,mod in changes:
                faction = shortMapper(faction)
                for entry in record.relations:
                    if entry.faction == faction:
                        entry.mod = mod
                        break
                else:
                    entry = MelObject()
                    entry.faction = faction
                    entry.mod = mod
                    record.relations.append(entry)
                record.setChanged()
            changed += 1
        #--Done
        if changed: modFile.safeSave()
        return changed

    def writeToText(self,textPath):
        """Exports faction relations to specified text file."""
        id_relations,id_eid = self.id_relations, self.id_eid
        headFormat = u'"%s","%s","%s","%s","%s","%s","%s"\n'
        rowFormat = u'"%s","%s","0x%06X","%s","%s","0x%06X","%s"\n'
        with textPath.open('w',encoding='utf-8-sig') as out:
            out.write(headFormat % (
                _(u'Main Eid'),_(u'Main Mod'),_(u'Main Object'),
                _(u'Other Eid'),_(u'Other Mod'),_(u'Other Object'),_(u'Disp')))
            for main in sorted(id_relations,
                               key=lambda x:id_eid.get(x).lower()):
                mainEid = id_eid.get(main,u'Unknown')
                for other,disp in sorted(id_relations[main],
                                         key=lambda x:id_eid.get(
                                                 x[0]).lower()):
                    otherEid = id_eid.get(other,u'Unknown')
                    out.write(rowFormat % (
                        mainEid,main[0].s,main[1],otherEid,other[0].s,other[1],
                        disp))

class CBash_FactionRelations:
    """Faction relations."""

    def __init__(self,aliases=None):
        self.fid_faction_mod = {}
        self.fid_eid = {} #--For all factions.
        self.aliases = aliases or {}
        self.gotFactions = set()

    def readFromMod(self,modInfo):
        """Imports faction relations from specified mod."""
        fid_faction_mod,fid_eid,gotFactions = self.fid_faction_mod,\
                                              self.fid_eid,self.gotFactions
        importFile = modInfo.getPath().tail
        with ObCollection(ModsPath=dirs['mods'].s) as Current:
            importFile = Current.addMod(importFile.s, Saveable=False)
            Current.load()
            for modFile in Current.LoadOrderMods:
                modName = modFile.GName
                if modName in gotFactions: continue
                if modFile == importFile:
                    for record in modFile.FACT:
                        fid = record.fid
                        fid_eid[fid] = record.eid
                        relations = record.relations_list
                        if relations:
                            faction_mod = fid_faction_mod.setdefault(fid,{})
                            faction_mod.update(relations)
                else:
                    for record in modFile.FACT:
                        fid_eid[record.fid] = record.eid
                modFile.Unload()
                gotFactions.add(modName)

    def readFromText(self,textPath):
        """Imports faction relations from specified text file."""
        fid_faction_mod = self.fid_faction_mod
        aliases = self.aliases
        with CsvReader(textPath) as ins:
            for fields in ins:
                if len(fields) < 7 or fields[2][:2] != u'0x': continue
                med,mmod,mobj,oed,omod,oobj,disp = fields[:9]
                mmod = _coerce(mmod,unicode)
                omod = _coerce(omod,unicode)
                mid = FormID(GPath(aliases.get(mmod,mmod)),
                             _coerce(mobj[2:],int,16))
                oid = FormID(GPath(aliases.get(omod,omod)),
                             _coerce(oobj[2:],int,16))
                disp = _coerce(disp,int)
                faction_mod = fid_faction_mod.setdefault(mid,{})
                faction_mod[oid] = disp

    def writeToMod(self,modInfo):
        """Exports faction relations to specified mod."""
        fid_faction_mod = self.fid_faction_mod
        with ObCollection(ModsPath=dirs['mods'].s) as Current:
            modFile = Current.addMod(modInfo.getPath().stail,LoadMasters=False)
            Current.load()
            changed = 0
            for record in modFile.FACT:
                fid = record.fid
                if fid not in fid_faction_mod: continue
                faction_mod = FormID.FilterValidDict(fid_faction_mod[fid],
                                                     modFile,True,False)
                newRelations = set([(faction,mod) for faction,mod in
                                    FormID.FilterValidDict(faction_mod,modFile,
                                                           True,
                                                           False).iteritems()])
                curRelations = set(
                    [(faction,mod) for faction,mod in record.relations_list if
                     faction.ValidateFormID(modFile)])
                changes = newRelations - curRelations
                if not changes: continue
                for faction,mod in changes:
                    for entry in record.relations:
                        if entry.faction == faction:
                            entry.mod = mod
                            break
                    else:
                        entry = record.create_relation()
                        entry.faction = faction
                        entry.mod = mod
                changed += 1
            #--Done
            if changed: modFile.save()
            return changed

    def writeToText(self,textPath):
        """Exports faction relations to specified text file."""
        fid_faction_mod,fid_eid = self.fid_faction_mod, self.fid_eid
        headFormat = u'"%s","%s","%s","%s","%s","%s","%s"\n'
        rowFormat = u'"%s","%s","0x%06X","%s","%s","0x%06X","%s"\n'
        with textPath.open('w',encoding='utf-8-sig') as out:
            out.write(headFormat % (
                _(u'Main Eid'),_(u'Main Mod'),_(u'Main Object'),
                _(u'Other Eid'),_(u'Other Mod'),_(u'Other Object'),_(u'Disp')))
            for main in sorted(fid_faction_mod, key=lambda x: fid_eid.get(x)):
                mainEid = fid_eid.get(main,u'Unknown')
                faction_mod = fid_faction_mod[main]
                for other,disp in sorted(faction_mod.items(),
                                         key=lambda x:fid_eid.get(x[0])):
                    otherEid = fid_eid.get(other,u'Unknown')
                    out.write(rowFormat % (
                        mainEid,main[0].s,main[1],otherEid,other[0].s,other[1],
                        disp))

#------------------------------------------------------------------------------
class FidReplacer:
    """Replaces one set of fids with another."""

    def __init__(self,types=None,aliases=None):
        self.types = types or MreRecord.simpleTypes
        self.aliases = aliases or {} #--For aliasing mod names
        self.old_new = {} #--Maps old fid to new fid
        self.old_eid = {} #--Maps old fid to old editor id
        self.new_eid = {} #--Maps new fid to new editor id

    def readFromText(self,textPath):
        """Reads replacement data from specified text file."""
        old_new,old_eid,new_eid = self.old_new,self.old_eid,self.new_eid
        aliases = self.aliases
        with CsvReader(textPath) as ins:
            for fields in ins:
                if len(fields) < 7 or fields[2][:2] != u'0x'\
                        or fields[6][:2] != u'0x': continue
                oldMod,oldObj,oldEid,newEid,newMod,newObj = fields[1:7]
                oldMod = _coerce(oldMod, unicode)
                oldEid = _coerce(oldEid, unicode, AllowNone=True)
                newEid = _coerce(newEid, unicode, AllowNone=True)
                newMod = _coerce(newMod, unicode)
                oldMod,newMod = map(GPath,(oldMod,newMod))
                oldId = (
                    GPath(aliases.get(oldMod,oldMod)),_coerce(oldObj,int,16))
                newId = (
                    GPath(aliases.get(newMod,newMod)),_coerce(newObj,int,16))
                old_new[oldId] = newId
                old_eid[oldId] = oldEid
                new_eid[newId] = newEid

    def updateMod(self,modInfo,changeBase=False):
        """Updates specified mod file."""
        types = self.types
        classes = [MreRecord.type_class[type_] for type_ in types]
        loadFactory = LoadFactory(True,*classes)
        modFile = ModFile(modInfo,loadFactory)
        modFile.load(True)
        #--Create  filtered versions of mappers.
        mapper = modFile.getShortMapper()
        masters = modFile.tes4.masters + [modFile.fileInfo.name]
        short = dict((oldId,mapper(oldId)) for oldId in self.old_eid if
                     oldId[0] in masters)
        short.update((newId,mapper(newId)) for newId in self.new_eid if
                     newId[0] in masters)
        old_eid = dict(
            (short[oldId],eid) for oldId,eid in self.old_eid.iteritems() if
            oldId in short)
        new_eid = dict(
            (short[newId],eid) for newId,eid in self.new_eid.iteritems() if
            newId in short)
        old_new = dict((short[oldId],short[newId]) for oldId,newId in
                       self.old_new.iteritems() if
                       (oldId in short and newId in short))
        if not old_new: return False
        #--Swapper function
        old_count = {}
        def swapper(oldId):
            newId = old_new.get(oldId,None)
            if newId:
                old_count.setdefault(oldId,0)
                old_count[oldId] += 1
                return newId
            else:
                return oldId
        #--Do swap on all records
        for type_ in types:
            for record in getattr(modFile,type_).getActiveRecords():
                if changeBase: record.fid = swapper(record.fid)
                record.mapFids(swapper,True)
                record.setChanged()
        #--Done
        if not old_count: return False
        modFile.safeSave()
        entries = [(count,old_eid[oldId],new_eid[old_new[oldId]]) for
                   oldId,count in old_count.iteritems()]
        entries.sort(key=itemgetter(1))
        return '\n'.join(['%3d %s >> %s' % entry for entry in entries])

class CBash_FidReplacer:
    """Replaces one set of fids with another."""

    def __init__(self,types=None,aliases=None):
        self.aliases = aliases or {} #--For aliasing mod names
        self.old_new = {} #--Maps old fid to new fid
        self.old_eid = {} #--Maps old fid to old editor id
        self.new_eid = {} #--Maps new fid to new editor id

    def readFromText(self,textPath):
        """Reads replacement data from specified text file."""
        old_new,old_eid,new_eid = self.old_new,self.old_eid,self.new_eid
        aliases = self.aliases
        with CsvReader(textPath) as ins:
            for fields in ins:
                if len(fields) < 7 or fields[2][:2] != u'0x'\
                        or fields[6][:2] != u'0x': continue
                oldMod,oldObj,oldEid,newEid,newMod,newObj = fields[1:7]
                oldMod = _coerce(oldMod, unicode)
                oldEid = _coerce(oldEid, unicode)
                newEid = _coerce(newEid, unicode, AllowNone=True)
                newMod = _coerce(newMod, unicode, AllowNone=True)
                oldMod,newMod = map(GPath,(oldMod,newMod))
                oldId = FormID(GPath(aliases.get(oldMod,oldMod)),
                               _coerce(oldObj,int,16))
                newId = FormID(GPath(aliases.get(newMod,newMod)),
                               _coerce(newObj,int,16))
                old_new[oldId] = newId
                old_eid[oldId] = oldEid
                new_eid[newId] = newEid

    def updateMod(self,modInfo,changeBase=False):
        """Updates specified mod file."""
        old_new,old_eid,new_eid = self.old_new,self.old_eid,self.new_eid
        #Filter the fid replacements to only include existing mods
        existing = bosh.modInfos.keys()
        old_new = dict((oldId,newId) for oldId,newId in old_new.iteritems() if
                       oldId[0] in existing and newId[0] in existing)
        if not old_new: return False
        # old_count = {} # unused - was meant to be used ?
        with ObCollection(ModsPath=dirs['mods'].s) as Current:
            for newId in set(old_new.values()):
                Current.addMod(bosh.modInfos[newId[0]].getPath().stail,
                               Saveable=False)
            modFile = Current.addMod(modInfo.getPath().stail)
            Current.load()
            counts = modFile.UpdateReferences(old_new)
            #--Done
            if not sum(counts): return False
            modFile.save()
            entries = [(count,old_eid[oldId],new_eid[newId]) for
                       count,oldId,newId in
                       zip(counts,old_new.keys(),old_new.values())]
            entries.sort(key=itemgetter(1))
            return u'\n'.join([u'%3d %s >> %s' % entry for entry in entries])

#------------------------------------------------------------------------------
class FullNames:
    """Names for records, with functions for importing/exporting from/to
    mod/text file."""

    def __init__(self,types=None,aliases=None):
        self.type_id_name = {} #--(eid,name) = type_id_name[type][longid]
        self.types = types or bush.game.namesTypes
        self.aliases = aliases or {}

    def readFromMod(self,modInfo):
        """Imports type_id_name from specified mod."""
        type_id_name,types = self.type_id_name, self.types
        classes = [MreRecord.type_class[x] for x in self.types]
        loadFactory = LoadFactory(False,*classes)
        modFile = ModFile(modInfo,loadFactory)
        modFile.load(True)
        mapper = modFile.getLongMapper()
        for type_ in types:
            typeBlock = modFile.tops.get(type_,None)
            if not typeBlock: continue
            if type_ not in type_id_name: type_id_name[type_] = {}
            id_name = type_id_name[type_]
            for record in typeBlock.getActiveRecords():
                longid = mapper(record.fid)
                full = record.full or (type_ == 'LIGH' and u'NO NAME')
                if record.eid and full:
                    id_name[longid] = (record.eid,full)

    def writeToMod(self,modInfo):
        """Exports type_id_name to specified mod."""
        type_id_name,types = self.type_id_name,self.types
        classes = [MreRecord.type_class[x] for x in self.types]
        loadFactory = LoadFactory(True,*classes)
        modFile = ModFile(modInfo,loadFactory)
        modFile.load(True)
        mapper = modFile.getLongMapper()
        changed = {}
        for type_ in types:
            id_name = type_id_name.get(type_,None)
            typeBlock = modFile.tops.get(type_,None)
            if not id_name or not typeBlock: continue
            for record in typeBlock.records:
                longid = mapper(record.fid)
                full = record.full
                eid,newFull = id_name.get(longid,(0,0))
                if newFull and newFull not in (full,u'NO NAME'):
                    record.full = newFull
                    record.setChanged()
                    changed[eid] = (full,newFull)
        if changed: modFile.safeSave()
        return changed

    def readFromText(self,textPath):
        """Imports type_id_name from specified text file."""
        textPath = GPath(textPath)
        type_id_name = self.type_id_name
        aliases = self.aliases
        with CsvReader(textPath) as ins:
            for fields in ins:
                if len(fields) < 5 or fields[2][:2] != u'0x': continue
                group,mod,objectIndex,eid,full = fields[:5]
                group = _coerce(group, unicode)
                mod = GPath(_coerce(mod, unicode))
                longid = (aliases.get(mod,mod),_coerce(objectIndex[2:],int,16))
                eid = _coerce(eid, unicode, AllowNone=True)
                full = _coerce(full, unicode, AllowNone=True)
                if group in type_id_name:
                    type_id_name[group][longid] = (eid,full)
                else:
                    type_id_name[group] = {longid:(eid,full)}

    def writeToText(self,textPath):
        """Exports type_id_name to specified text file."""
        textPath = GPath(textPath)
        type_id_name = self.type_id_name
        headFormat = u'"%s","%s","%s","%s","%s"\n'
        rowFormat = u'"%s","%s","0x%06X","%s","%s"\n'
        with textPath.open('w',encoding='utf-8-sig') as out:
            out.write(headFormat % (
                _(u'Type'),_(u'Mod Name'),_(u'ObjectIndex'),_(u'Editor Id'),
                _(u'Name')))
            for type_ in sorted(type_id_name):
                id_name = type_id_name[type_]
                longids = id_name.keys()
                longids.sort(key=lambda a: id_name[a][0].lower())
                longids.sort(key=itemgetter(0))
                for longid in longids:
                    eid,name = id_name[longid]
                    out.write(rowFormat % (
                        type_,longid[0].s,longid[1],eid,
                        name.replace(u'"',u'""')))

class CBash_FullNames:
    """Names for records, with functions for importing/exporting from/to
    mod/text file."""
    defaultTypes = {"CLAS","FACT","HAIR","EYES","RACE","MGEF","ENCH","SPEL",
                    "BSGN","ACTI","APPA","ARMO","BOOK","CLOT","CONT","DOOR",
                    "INGR","LIGH","MISC","FLOR","FURN","WEAP","AMMO","NPC_",
                    "CREA","SLGM","KEYM","ALCH","SGST","WRLD","CELLS","DIAL",
                    "QUST"}

    def __init__(self,types=None,aliases=None):
        self.group_fid_name = {} #--(eid,name) = group_fid_name[group][longid]
        self.types = types or CBash_FullNames.defaultTypes
        self.aliases = aliases or {}

    def readFromMod(self,modInfo):
        """Imports type_id_name from specified mod."""
        group_fid_name = self.group_fid_name
        with ObCollection(ModsPath=dirs['mods'].s) as Current:
            modFile = Current.addMod(modInfo.getPath().stail,Saveable=False,
                                     LoadMasters=False)
            Current.load()
            for group in self.types:
                fid_name = group_fid_name.setdefault(group[:4],{})
                for record in getattr(modFile,group):
                    if hasattr(record, 'full'):
                        full = record.full or (group == 'LIGH' and u'NO NAME')
                        eid = record.eid
                        if eid and full:
                            fid_name[record.fid] = (eid,full)
                modFile.Unload()

    def writeToMod(self,modInfo):
        """Exports type_id_name to specified mod."""
        group_fid_name = self.group_fid_name
        with ObCollection(ModsPath=dirs['mods'].s) as Current:
            modFile = Current.addMod(modInfo.getPath().stail,LoadMasters=False)
            Current.load()
            changed = {}
            for group in self.types:
                fid_name = group_fid_name.get(group,None)
                if not fid_name: continue
                fid_name = FormID.FilterValidDict(fid_name,modFile,True,False)
                for record in getattr(modFile,group):
                    fid = record.fid
                    full = record.full
                    eid,newFull = fid_name.get(fid,(0,0))
                    if newFull and newFull not in (full,u'NO NAME'):
                        record.full = newFull
                        changed[eid] = (full,newFull)
            if changed: modFile.save()
            return changed

    def readFromText(self,textPath):
        """Imports type_id_name from specified text file."""
        textPath = GPath(textPath)
        group_fid_name = self.group_fid_name
        aliases = self.aliases
        with CsvReader(textPath) as ins:
            for fields in ins:
                if len(fields) < 5 or fields[2][:2] != u'0x': continue
                group,mod,objectIndex,eid,full = fields[:5]
                group = _coerce(group,unicode)
                mod = GPath(_coerce(mod,unicode))
                longid = FormID(aliases.get(mod,mod),
                                _coerce(objectIndex[2:],int,16))
                eid = _coerce(eid,unicode,AllowNone=True)
                full = _coerce(full,unicode,AllowNone=True)
                group_fid_name.setdefault(group,{})[longid] = (eid,full)

    def writeToText(self,textPath):
        """Exports type_id_name to specified text file."""
        textPath = GPath(textPath)
        group_fid_name = self.group_fid_name
        headFormat = u'"%s","%s","%s","%s","%s"\n'
        rowFormat = u'"%s","%s","0x%06X","%s","%s"\n'
        with textPath.open('w',encoding='utf-8-sig') as out:
            outWrite = out.write
            outWrite(headFormat % (
                _(u'Type'),_(u'Mod Name'),_(u'ObjectIndex'),_(u'Editor Id'),
                _(u'Name')))
            for group in sorted(group_fid_name):
                fid_name = group_fid_name[group]
                longids = fid_name.keys()
                longids.sort(key=lambda a: fid_name[a][0])
                longids.sort(key=itemgetter(0))
                for longid in longids:
                    eid,name = fid_name[longid]
                    outWrite(rowFormat % (
                        group,longid[0],longid[1],eid,
                        name.replace(u'"',u'""')))

#------------------------------------------------------------------------------
class ItemStats:
    """Statistics for armor and weapons, with functions for
    importing/exporting from/to mod/text file."""

    @staticmethod
    def sstr(value):
        return _coerce(value, unicode, AllowNone=True)

    @staticmethod
    def sfloat(value):
        return _coerce(value, float, AllowNone=True)

    @staticmethod
    def sint(value):
        return _coerce(value, int, AllowNone=False)

    @staticmethod
    def snoneint(value):
        x = _coerce(value, int, AllowNone=True)
        if x == 0: return None
        return x

    def __init__(self,types=None,aliases=None):
        self.class_attrs = bush.game.statsTypes
        self.class_fid_attr_value = defaultdict(lambda : defaultdict(dict))
        self.aliases = aliases or {} #--For aliasing mod names
        if bush.game.fsName in (u'Enderal', u'Skyrim',
                                u'Skyrim Special Edition'):
            self.attr_type = {'eid':self.sstr,
                              'weight':self.sfloat,
                              'value':self.sint,
                              'damage':self.sint,
                              'armorRating':self.sint,
                              'duration':self.sint,
                              'speed':self.sfloat,
                              'reach':self.sfloat,
                              'stagger':self.sfloat,
                              'enchantPoints':self.sint,
                              'critDamage':self.sint,
                              'criticalMultiplier':self.sfloat,
                              'criticalEffect':self.sint,}
        elif bush.game.fsName in (u'FalloutNV', u'Fallout3'):
            self.attr_type = {'eid':self.sstr,
                              'weight':self.sfloat,
                              'value':self.sint,
                              'damage':self.sint,
                              'speed':self.sfloat,
                              'enchantPoints':self.snoneint,
                              'health':self.sint,
                              'strength':self.sint,
                              'duration':self.sint,
                              'quality':self.sfloat,
                              'uses':self.sint,
                              'reach':self.sfloat,
                              'clipRounds':self.sint,
                              'projPerShot':self.sint,
                              'ar':self.sint,
                              'dt':self.sfloat,
                              'clipsize':self.sint,
                              'animationMultiplier':self.sfloat,
                              'ammoUse':self.sint,
                              'minSpread':self.sfloat,
                              'spread':self.sfloat,
                              'sightFov':self.sfloat,
                              'baseVatsToHitChance':self.sint,
                              'projectileCount':self.sint,
                              'minRange':self.sfloat,
                              'maxRange':self.sfloat,
                              'animationAttackMultiplier':self.sfloat,
                              'fireRate':self.sfloat,
                              'overrideActionPoint':self.sfloat,
                              'rumbleLeftMotorStrength':self.sfloat,
                              'rumbleRightMotorStrength':self.sfloat,
                              'rumbleDuration':self.sfloat,
                              'overrideDamageToWeaponMult':self.sfloat,
                              'attackShotsPerSec':self.sfloat,
                              'reloadTime':self.sfloat,
                              'jamTime':self.sfloat,
                              'aimArc':self.sfloat,
                              'rambleWavelangth':self.sfloat,
                              'limbDmgMult':self.sfloat,
                              'sightUsage':self.sfloat,
                              'semiAutomaticFireDelayMin':self.sfloat,
                              'semiAutomaticFireDelayMax':self.sfloat,
                              'strengthReq':self.sint,
                              'regenRate':self.sfloat,
                              'killImpulse':self.sfloat,
                              'impulseDist':self.sfloat,
                              'skillReq':self.sint,
                              'criticalDamage':self.sint,
                              'criticalMultiplier':self.sfloat,
                              'vatsSkill':self.sfloat,
                              'vatsDamMult':self.sfloat,
                              'vatsAp':self.sfloat,}
        elif bush.game.fsName == u'Oblivion':
            self.attr_type = {'eid':self.sstr,
                              'weight':self.sfloat,
                              'value':self.sint,
                              'damage':self.sint,
                              'speed':self.sfloat,
                              'enchantPoints':self.sint,
                              'health':self.sint,
                              'strength':self.sint,
                              'duration':self.sint,
                              'quality':self.sfloat,
                              'uses':self.sint,
                              'reach':self.sfloat,}

    def readFromMod(self,modInfo):
        """Reads stats from specified mod."""
        typeClasses = [MreRecord.type_class[x] for x in self.class_attrs]
        loadFactory = LoadFactory(False,*typeClasses)
        modFile = ModFile(modInfo,loadFactory)
        modFile.load(True)
        modFile.convertToLongFids()
        for group, attrs in self.class_attrs.iteritems():
            for record in getattr(modFile,group).getActiveRecords():
                self.class_fid_attr_value[group][record.fid].update(
                    zip(attrs, map(record.__getattribute__, attrs)))

    def writeToMod(self,modInfo):
        """Writes stats to specified mod."""
        typeClasses = [MreRecord.type_class[x] for x in self.class_attrs]
        loadFactory = LoadFactory(True,*typeClasses)
        modFile = ModFile(modInfo,loadFactory)
        modFile.load(True)
        modFile.convertToLongFids()
        changed = defaultdict(int) #--changed[modName] = numChanged
        for group, fid_attr_value in self.class_fid_attr_value.iteritems():
            attrs = self.class_attrs[group]
            for record in getattr(modFile,group).getActiveRecords():
                longid = record.fid
                itemStats = fid_attr_value.get(longid,None)
                if not itemStats: continue
                oldValues = dict(zip(attrs,map(record.__getattribute__,attrs)))
                if oldValues != itemStats:
                    for attr, value in itemStats.iteritems():
                        setattr(record,attr,value)
                    record.setChanged()
                    changed[longid[0]] += 1
        if changed: modFile.safeSave()
        return changed

    def readFromText(self,textPath):
        """Reads stats from specified text file."""
        aliases = self.aliases
        with CsvReader(textPath) as ins:
            attr_type = self.attr_type
            for fields in ins:
                if len(fields) < 3 or fields[2][:2] != u'0x': continue
                group,modName,objectStr = fields[0:3]
                modName = GPath(_coerce(modName,unicode))
                longid = (GPath(aliases.get(modName,modName)),
                    _coerce(objectStr,int,16))
                attrs = self.class_attrs[group]
                attr_value = {}
                for attr, value in zip(attrs, fields[3:3+len(attrs)]):
                    attr_value[attr] = attr_type[attr](value)
                self.class_fid_attr_value[group][longid].update(attr_value)

    def writeToText(self,textPath):
        """Writes stats to specified text file."""
        class_fid_attr_value = self.class_fid_attr_value
        def getSortedIds(fid_attr_value):
            longids = fid_attr_value.keys()
            longids.sort(key=lambda a: fid_attr_value[a]['eid'].lower())
            longids.sort(key=itemgetter(0))
            return longids
        with textPath.open('w',encoding='utf-8-sig') as out:
            def write(out, attrs, values):
                attr_type = self.attr_type
                csvFormat = u''
                sstr = self.sstr
                sint = self.sint
                snoneint = self.snoneint
                sfloat = self.sfloat
                for index, attr in enumerate(attrs):
                    if attr == 'enchantPoints':
                        stype = self.snoneint
                    else:
                        stype = attr_type[attr]
                    values[index] = stype(values[index]) #sanitize output
                    if values[index] is None:
                        csvFormat += u',"{0[%d]}"' % index
                    elif stype is sstr: csvFormat += u',"{0[%d]}"' % index
                    elif stype is sint or stype is snoneint: csvFormat += \
                        u',"{0[%d]:d}"' % index
                    elif stype is sfloat: csvFormat += u',"{0[%d]:f}"' % index
                csvFormat = csvFormat[1:] #--Chop leading comma
                out.write(csvFormat.format(values) + u'\n')
            for group,header in bush.game.statsHeaders:
                fid_attr_value = class_fid_attr_value[group]
                if not fid_attr_value: continue
                attrs = self.class_attrs[group]
                out.write(header)
                for longid in getSortedIds(fid_attr_value):
                    out.write(
                        u'"%s","%s","0x%06X",' % (group,longid[0].s,longid[1]))
                    attr_value = fid_attr_value[longid]
                    write(out, attrs, map(attr_value.get, attrs))

class CBash_ItemStats:
    """Statistics for armor and weapons, with functions for
    importing/exporting from/to mod/text file."""

    @staticmethod
    def sstr(value):
        return _coerce(value, unicode, AllowNone=True)

    @staticmethod
    def sfloat(value):
        return _coerce(value, float, AllowNone=True)

    @staticmethod
    def sint(value):
        return _coerce(value, int, AllowNone=True)

    @staticmethod
    def snoneint(value):
        x = _coerce(value, int, AllowNone=True)
        if x == 0: return None
        return x

    def __init__(self,types=None,aliases=None):
        self.class_attrs = bush.game.statsTypes
        self.class_fid_attr_value = defaultdict(lambda : defaultdict(dict))
        self.aliases = aliases or {} #--For aliasing mod names
        self.attr_type = {'eid':self.sstr,
                          'weight':self.sfloat,
                          'value':self.sint,
                          'damage':self.sint,
                          'speed':self.sfloat,
                          'enchantPoints':self.snoneint,
                          'health':self.sint,
                          'strength':self.sint,
                          'duration':self.sint,
                          'quality':self.sfloat,
                          'uses':self.sint,
                          'reach':self.sfloat,}

    def readFromMod(self,modInfo):
        """Reads stats from specified mod."""
        with ObCollection(ModsPath=dirs['mods'].s) as Current:
            modFile = Current.addMod(modInfo.getPath().stail,LoadMasters=False)
            Current.load()
            for group, attrs in self.class_attrs.iteritems():
                for record in getattr(modFile,group):
                    self.class_fid_attr_value[group][record.fid].update(
                        zip(attrs,map(record.__getattribute__,attrs)))

    def writeToMod(self,modInfo):
        """Exports type_id_name to specified mod."""
        with ObCollection(ModsPath=dirs['mods'].s) as Current:
            modFile = Current.addMod(modInfo.getPath().stail,LoadMasters=False)
            Current.load()
            changed = defaultdict(int) #--changed[modName] = numChanged
            for group, fid_attr_value in self.class_fid_attr_value.iteritems():
                attrs = self.class_attrs[group]
                fid_attr_value = FormID.FilterValidDict(fid_attr_value,modFile,
                                                        True,False)
                for fid, attr_value in fid_attr_value.iteritems():
                    record = modFile.LookupRecord(fid)
                    if record and record._Type == group:
                        oldValues = dict(
                            zip(attrs,map(record.__getattribute__,attrs)))
                        if oldValues != attr_value:
                            for attr, value in attr_value.iteritems():
                                setattr(record,attr,value)
                            changed[fid[0]] += 1
            if changed: modFile.save()
            return changed

    def readFromText(self,textPath):
        """Reads stats from specified text file."""
        aliases = self.aliases
        with CsvReader(textPath) as ins:
            attr_type = self.attr_type
            for fields in ins:
                if len(fields) < 3 or fields[2][:2] != u'0x': continue
                group,modName,objectStr = fields[0:3]
                modName = GPath(_coerce(modName,unicode))
                longid = FormID(GPath(aliases.get(modName,modName)),
                                _coerce(objectStr,int,16))
                attrs = self.class_attrs[group]
                attr_value = {}
                for attr, value in zip(attrs, fields[3:3+len(attrs)]):
                    attr_value[attr] = attr_type[attr](value)
                self.class_fid_attr_value[group][longid].update(attr_value)

    def writeToText(self,textPath):
        """Writes stats to specified text file."""
        class_fid_attr_value = self.class_fid_attr_value
        def getSortedIds(fid_attr_value):
            longids = fid_attr_value.keys()
            longids.sort(key=lambda a: fid_attr_value[a]['eid'])
            longids.sort(key=itemgetter(0))
            return longids
        with textPath.open('w',encoding='utf-8-sig') as out:
            def write(out, attrs, values):
                attr_type = self.attr_type
                _csvFormat = u''
                sstr = self.sstr
                sint = self.sint
                snoneint = self.snoneint
                sfloat = self.sfloat
                for index, attr in enumerate(attrs):
                    stype = attr_type[attr]
                    values[index] = stype(values[index]) #sanitize output
                    if values[index] is None:
                        _csvFormat += u',"{0[%d]}"' % index
                    elif stype is sstr: _csvFormat += u',"{0[%d]}"' % index
                    elif stype is sint or stype is snoneint: _csvFormat += \
                        u',"{0[%d]:d}"' % index
                    elif stype is sfloat: _csvFormat += u',"{0[%d]:f}"' % index
                _csvFormat = _csvFormat[1:] #--Chop leading comma
                out.write(_csvFormat.format(values) + u'\n')
            for group,header in bush.game.statsHeaders:
                fid_attr_value = class_fid_attr_value[group]
                if not fid_attr_value: continue
                attrs = self.class_attrs[group]
                out.write(header)
                for longid in getSortedIds(fid_attr_value):
                    out.write(
                        u'"%s","%s","0x%06X",' % (group,longid[0],longid[1]))
                    attr_value = fid_attr_value[longid]
                    write(out, attrs, map(attr_value.get, attrs))

#------------------------------------------------------------------------------
class _ScriptText(object):
    """import & export functions for script text."""

    def __init__(self,types=None,aliases=None):
        self.eid_data = {}
        self.aliases = aliases or {} #--For aliasing mod names

    def writeToText(self,textPath,skip,folder,deprefix,esp,skipcomments):
        """Writes stats to specified text file."""
        eid_data = self.eid_data
        x = len(skip)
        exportedScripts = []
        y = len(eid_data)
        z = 0
        num = 0
        r = len(deprefix)
        with Progress(_(u"Export Scripts")) as progress:
            for eid in sorted(eid_data, key=lambda b: (b, eid_data[b][1])):
                text, longid = eid_data[eid]
                text = decode(text) # TODO(ut) was only present in PBash version - needed ?
                if skipcomments:
                    tmp = u''
                    for line in text.split(u'\n'):
                        pos = line.find(u';')
                        if pos == -1:
                            tmp += line + u'\n'
                        elif pos == 0:
                            continue
                        else:
                            if line[:pos].isspace(): continue
                            tmp += line[:pos] + u'\n'
                    text = tmp
                z += 1
                progress((0.5 + 0.5 / y * z),_(u"Exporting script %s.") % eid)
                if x == 0 or skip.lower() != eid[:x].lower():
                    fileName = eid
                    if r >= 1 and deprefix == fileName[:r]:
                        fileName = fileName[r:]
                    num += 1
                    outpath = dirs['patches'].join(folder).join(
                        fileName + inisettings['ScriptFileExt'])
                    with outpath.open('wb',encoding='utf-8-sig') as out:
                        formid = u'0x%06X' % longid[1]
                        out.write(u';' + longid[0].s + u'\r\n;' + formid + u'\r\n;' + eid + u'\r\n' + text)
                    exportedScripts.append(eid)
        return (_(u'Exported %d scripts from %s:') + u'\n') % (
            num,esp) + u'\n'.join(exportedScripts)

class ScriptText(_ScriptText):

    def readFromMod(self, modInfo, file_):
        """Reads stats from specified mod."""
        eid_data = self.eid_data
        loadFactory = LoadFactory(False,MreRecord.type_class['SCPT'])
        modFile = ModFile(modInfo,loadFactory)
        modFile.load(True)
        mapper = modFile.getLongMapper()
        with Progress(_(u"Export Scripts")) as progress:
            records = modFile.SCPT.getActiveRecords()
            y = len(records)
            z = 0
            for record in records:
                z += 1
                progress((0.5/y*z),_(u"Reading scripts in %s.")% file_)
                eid_data[record.eid] = (record.scriptText,mapper(record.fid))

    def writeToMod(self, modInfo, makeNew=False):
        """Writes scripts to specified mod."""
        eid_data = self.eid_data
        changed = []
        added = []
        loadFactory = LoadFactory(True,MreRecord.type_class['SCPT'])
        modFile = ModFile(modInfo,loadFactory)
        modFile.load(True)
        for record in modFile.SCPT.getActiveRecords():
            eid = record.eid
            data = eid_data.get(eid,None)
            if data is not None:
                newText, longid = data
                oldText = record.scriptText
                if oldText.lower() != newText.lower():
                    record.scriptText = newText
                    record.setChanged()
                    changed.append(eid)
                del eid_data[eid]
        if makeNew and eid_data:
            tes4 = modFile.tes4
            for eid, data in eid_data.iteritems():
                newText, longid = data
                scriptFid = genFid(len(tes4.masters),tes4.getNextObject())
                newScript = MreRecord.type_class['SCPT'](
                    ModReader.recHeader('SCPT',0,0x40000,scriptFid,0))
                newScript.eid = eid
                newScript.scriptText = newText
                newScript.setChanged()
                modFile.SCPT.records.append(newScript)
                added.append(eid)
        if changed or added: modFile.safeSave()
        return changed, added

    def readFromText(self,textPath,modInfo):
        """Reads scripts from files in specified mods' directory in bashed
        patches folder."""
        eid_data = self.eid_data
        textPath = GPath(textPath)
        with Progress(_(u"Import Scripts")) as progress:
            for root_dir, dirs, files in textPath.walk():
                y = len(files)
                z = 0
                for name in files:
                    z += 1
                    if name.cext != inisettings['ScriptFileExt']:
                        progress(((1/y)*z),_(u"Skipping file %s.") % name.s)
                        continue
                    progress(((1 / y) * z),_(u"Reading file %s.") % name.s)
                    with root_dir.join(name).open('r', encoding='utf-8-sig') \
                            as text:
                        lines = text.readlines()
                    try:
                        modName,FormID,eid = lines[0][1:-2],lines[1][1:-2], \
                                             lines[2][1:-2]
                    except:
                        deprint(
                            _(u"%s has malformed script header lines - was "
                              u"skipped") % name)
                        continue
                    scriptText = u''.join(lines[3:])
                    eid_data[eid] = (scriptText, FormID)
        if eid_data: return True
        return False

class CBash_ScriptText(_ScriptText):

    def readFromMod(self, modInfo, file_):
        """Reads stats from specified mod."""
        eid_data = self.eid_data
        with ObCollection(ModsPath=dirs['mods'].s) as Current:
            modFile = Current.addMod(modInfo.getPath().stail,LoadMasters=False)
            Current.load()
            with Progress(_(u"Export Scripts")) as progress:
                records = modFile.SCPT
                y = len(records)
                z = 0
                for record in records:
                    z += 1
                    progress((0.5/y*z),_(u"Reading scripts in %s.") % file_)
                    eid_data[record.eid] = (record.scriptText,record.fid)

    def writeToMod(self, modInfo, makeNew=False):
        """Writes scripts to specified mod."""
        eid_data = self.eid_data
        changed = []
        added = []
        with ObCollection(ModsPath=dirs['mods'].s) as Current:
            modFile = Current.addMod(modInfo.getPath().stail,LoadMasters=False)
            Current.load()
            for record in modFile.SCPT:
                eid = record.eid
                data = eid_data.get(eid,None)
                if data is not None:
                    newText, longid = data
                    oldText = record.scriptText
                    if oldText != newText:
                        record.scriptText = newText
                        changed.append(eid)
                    del eid_data[eid]
            if makeNew and eid_data:
                for eid, data in eid_data.iteritems():
                    newText, longid = data
                    newScript = modFile.create_SCPT()
                    if newScript is not None:
                        newScript.eid = eid
                        newScript.scriptText = newText
                        added.append(eid)
            if changed or added: modFile.save()
            return changed, added

    def readFromText(self,textPath,modInfo):
        """Reads scripts from files in specified mods' directory in bashed
        patches folder."""
        eid_data = self.eid_data
        textPath = GPath(textPath)
        with Progress(_(u"Import Scripts")) as progress:
            for root_dir, dirs, files in textPath.walk():
                y = len(files)
                z = 0
                for name in files:
                    z += 1
                    if name.cext != inisettings['ScriptFileExt']:
                        progress(((1/y)*z),_(u"Skipping file %s.") % name.s)
                        continue
                    progress(((1 / y) * z),_(u"Reading file %s.") % name.s)
                    with root_dir.join(name).open('r', encoding='utf-8-sig') \
                            as text:
                        lines = text.readlines()
                    if not lines: continue
                    modName,formID,eid = lines[0][1:-2],lines[1][1:-2],\
                                         lines[2][1:-2]
                    scriptText = u''.join(lines[3:])
                    eid_data[IUNICODE(eid)] = (
                        IUNICODE(scriptText),formID) #script text is case
                    # insensitive
        if eid_data: return True
        return False

#------------------------------------------------------------------------------
class _UsesEffectsMixin(object):
    """Mixin class to support reading/writing effect data to/from csv files"""
    headers = (
        _(u'Effect'),_(u'Name'),_(u'Magnitude'),_(u'Area'),_(u'Duration'),
        _(u'Range'),_(u'Actor Value'),_(u'SE Mod Name'),_(u'SE ObjectIndex'),
        _(u'SE school'),_(u'SE visual'),_(u'SE Is Hostile'),_(u'SE Name'))
    headerFormat = u'"%s","%s","%s","%s","%s","%s","%s","%s","%s","%s","%s",' \
                   u'"%s","%s"'
    recipientTypeNumber_Name = {None:u'NONE',0:u'Self',1:u'Touch',2:u'Target',}
    recipientTypeName_Number = dict(
        [(y.lower(),x) for x,y in recipientTypeNumber_Name.iteritems() if
         x is not None])
    actorValueNumber_Name = dict(
        [(x,y) for x,y in enumerate(brec.actorValues)])
    actorValueNumber_Name[None] = u'NONE'
    actorValueName_Number = dict(
        [(y.lower(),x) for x,y in actorValueNumber_Name.iteritems() if
         x is not None])
    schoolTypeNumber_Name = {None:u'NONE',0:u'Alteration',1:u'Conjuration',
                             2:u'Destruction',3:u'Illusion',4:u'Mysticism',
                             5:u'Restoration',}
    schoolTypeName_Number = dict(
        [(y.lower(),x) for x,y in schoolTypeNumber_Name.iteritems() if
         x is not None])

    def readEffects(self,_effects,aliases,doCBash):
        schoolTypeName_Number = _UsesEffectsMixin.schoolTypeName_Number
        recipientTypeName_Number = _UsesEffectsMixin.recipientTypeName_Number
        actorValueName_Number = _UsesEffectsMixin.actorValueName_Number
        effects = []
        while len(_effects) >= 13:
            _effect,_effects = _effects[1:13],_effects[13:]
            name,magnitude,area,duration,range_,actorvalue,semod,seobj,\
            seschool,sevisual,seflags,sename = tuple(_effect)
            name = _coerce(name,unicode,AllowNone=True) #OBME not supported
            # (support requires adding a mod/objectid format to the
            # csv, this assumes all MGEFCodes are raw)
            magnitude = _coerce(magnitude,int,AllowNone=True)
            area = _coerce(area,int,AllowNone=True)
            duration = _coerce(duration,int,AllowNone=True)
            range_ = _coerce(range_,unicode,AllowNone=True)
            if range_:
                range_ = recipientTypeName_Number.get(range_.lower(),
                                                      _coerce(range_,int))
            actorvalue = _coerce(actorvalue, unicode, AllowNone=True)
            if actorvalue:
                actorvalue = actorValueName_Number.get(actorvalue.lower(),
                                                       _coerce(actorvalue,int))
            if None in (name,magnitude,area,duration,range_,actorvalue):
                continue
            if doCBash:
                effect = [MGEFCode(name),magnitude,area,duration,range_,
                          ActorValue(actorvalue)]
            else:
                effect = [name,magnitude,area,duration,range_,actorvalue]
            semod = _coerce(semod, unicode, AllowNone=True)
            seobj = _coerce(seobj, int, 16, AllowNone=True)
            seschool = _coerce(seschool, unicode, AllowNone=True)
            if seschool:
                seschool = schoolTypeName_Number.get(seschool.lower(),
                                                     _coerce(seschool,int))
            sevisuals = _coerce(sevisual,int,AllowNone=True) #OBME not
            # supported (support requires adding a mod/objectid format to
            # the csv, this assumes visual MGEFCode is raw)
            if sevisuals is None:
                sevisuals = _coerce(sevisual, unicode, AllowNone=True)
            else:
                sevisuals = ctypes.cast(ctypes.byref(ctypes.c_ulong(sevisuals))
                    ,ctypes.POINTER(ctypes.c_char * 4)).contents.value
            if doCBash:
                if sevisuals == '':
                    sevisuals = 0
            else:
                if sevisuals == '' or sevisuals is None:
                    sevisuals = u'\x00\x00\x00\x00'
            sevisual = sevisuals
            seflags = _coerce(seflags, int, AllowNone=True)
            sename = _coerce(sename, unicode, AllowNone=True)
            if None in (semod,seobj,seschool,sevisual,seflags,sename):
                if doCBash:
                    effect.extend(
                        [FormID(None,None),None,MGEFCode(None,None),None,None])
                else:
                    effect.append([])
            else:
                if doCBash:
                    effect.extend(
                        [FormID(GPath(aliases.get(semod,semod)),seobj),
                         seschool,MGEFCode(sevisual),seflags,sename])
                else:
                    effect.append(
                        [(GPath(aliases.get(semod,semod)),seobj),seschool,
                         sevisual,seflags,sename])
            if doCBash:
                effects.append(tuple(effect))
            else:
                effects.append(effect)
        return effects

    def writeEffects(self,effects,doCBash):
        schoolTypeNumber_Name = _UsesEffectsMixin.schoolTypeNumber_Name
        recipientTypeNumber_Name = _UsesEffectsMixin.recipientTypeNumber_Name
        actorValueNumber_Name = _UsesEffectsMixin.actorValueNumber_Name
        effectFormat = u',,"%s","%d","%d","%d","%s","%s"'
        scriptEffectFormat = u',"%s","0x%06X","%s","%s","%s","%s"'
        noscriptEffectFiller = u',"None","None","None","None","None","None"'
        output = []
        for effect in effects:
            if doCBash:
                efname,magnitude,area,duration,range_,actorvalue = effect[:6]
                efname = efname[1] # OBME not supported (support requires
                # adding a mod/objectid format to the csv, this assumes all
                # MGEFCodes are raw)
                actorvalue = actorvalue[1] # OBME not supported (support
                # requires adding a mod/objectid format to the csv,
                # this assumes all ActorValues are raw)
            else:
                efname,magnitude,area,duration,range_,actorvalue = effect[:-1]
            range_ = recipientTypeNumber_Name.get(range_,range_)
            actorvalue = actorValueNumber_Name.get(actorvalue,actorvalue)
            if doCBash:
                scripteffect = effect[6:]
            else:
                scripteffect = effect[-1]
            output.append(effectFormat % (
                efname,magnitude,area,duration,range_,actorvalue))
            if doCBash:
                if None in scripteffect:
                    output.append(noscriptEffectFiller)
                else:
                    semod,seobj,seschool,sevisual,seflags,sename = \
                        scripteffect[0][0],scripteffect[0][1],scripteffect[1],\
                        scripteffect[2],scripteffect[3],scripteffect[4]
                    seschool = schoolTypeNumber_Name.get(seschool,seschool)
                    sevisual = sevisual[1] # OBME not supported (support
                    #  requires adding a mod/objectid format to the csv,
                    # this assumes visual MGEFCode is raw)
                    if sevisual in (None, 0, ''):
                        sevisual = u'NONE'
                    output.append(scriptEffectFormat % (
                        semod,seobj,seschool,sevisual,seflags,sename))
            else:
                if len(scripteffect):
                    longid,seschool,sevisual,seflags,sename = scripteffect
                    if sevisual == '\x00\x00\x00\x00':
                        sevisual = u'NONE'
                    seschool = schoolTypeNumber_Name.get(seschool,seschool)
                    output.append(scriptEffectFormat % (
                        longid[0].s,longid[1],seschool,sevisual,seflags,
                        sename))
                else:
                    output.append(noscriptEffectFiller)
        return u''.join(output)

#------------------------------------------------------------------------------
class SigilStoneDetails(_UsesEffectsMixin):
    """Details on SigilStones, with functions for importing/exporting
    from/to mod/text file."""

    def __init__(self,types=None,aliases=None):
        self.fid_stats = {}
        self.aliases = aliases or {} #--For aliasing mod names

    def readFromMod(self,modInfo):
        """Reads stats from specified mod."""
        fid_stats = self.fid_stats
        loadFactory = LoadFactory(False,MreRecord.type_class['SGST'])
        modFile = ModFile(modInfo,loadFactory)
        modFile.load(True)
        modFile.convertToLongFids(['SGST'])
        for record in modFile.SGST.getActiveRecords():
            effects = []
            for effect in record.effects:
                effectlist = [effect.name,effect.magnitude,effect.area,
                              effect.duration,effect.recipient,
                              effect.actorValue]
                if effect.scriptEffect:
                    effectlist.append(
                        [effect.scriptEffect.script,effect.scriptEffect.school,
                         effect.scriptEffect.visual,
                         effect.scriptEffect.flags.hostile,
                         effect.scriptEffect.full])
                else: effectlist.append([])
                effects.append(effectlist)
            fid_stats[record.fid] = [record.eid,record.full,
                                     record.model.modPath,
                                     round(record.model.modb,6),
                                     record.iconPath,record.script,record.uses,
                                     record.value,round(record.weight,6),
                                     effects]

    def writeToMod(self,modInfo):
        """Writes stats to specified mod."""
        fid_stats = self.fid_stats
        loadFactory = LoadFactory(True,MreRecord.type_class['SGST'])
        modFile = ModFile(modInfo,loadFactory)
        modFile.load(True)
        mapper = modFile.getLongMapper()
        shortMapper = modFile.getShortMapper()
        changed = [] #eids
        for record in modFile.SGST.getActiveRecords():
            newStats = fid_stats.get(mapper(record.fid),None)
            if not newStats: continue
            effects = []
            for effect in record.effects:
                effectlist = [effect.name,effect.magnitude,effect.area,
                              effect.duration,effect.recipient,
                              effect.actorValue]
                if effect.scriptEffect:
                    effectlist.append([mapper(effect.scriptEffect.script),
                                       effect.scriptEffect.school,
                                       effect.scriptEffect.visual,
                                       effect.scriptEffect.flags.hostile,
                                       effect.scriptEffect.full])
                else: effectlist.append([])
                effects.append(effectlist)
            oldStats = [record.eid,record.full,record.model.modPath,
                        round(record.model.modb,6),record.iconPath,
                        mapper(record.script),record.uses,record.value,
                        round(record.weight,6),effects]
            if oldStats != newStats:
                changed.append(oldStats[0]) #eid
                record.eid,record.full,record.model.modPath,\
                record.model.modb,record.iconPath,script,record.uses,\
                record.value,record.weight,effects = newStats
                record.script = shortMapper(script)
                record.effects = []
                for effect in effects:
                    neweffect = record.getDefault('effects')
                    neweffect.name,neweffect.magnitude,neweffect.area,\
                    neweffect.duration,neweffect.recipient,\
                    neweffect.actorValue,scripteffect = effect
                    if len(scripteffect):
                        scriptEffect = record.getDefault(
                            'effects.scriptEffect')
                        script,scriptEffect.school,scriptEffect.visual,\
                        scriptEffect.flags.hostile,scriptEffect.full = \
                            scripteffect
                        scriptEffect.script = shortMapper(script)
                        neweffect.scriptEffect = scriptEffect
                    record.effects.append(neweffect)
                record.setChanged()
        if changed: modFile.safeSave()
        return changed

    def readFromText(self,textPath):
        """Imports stats from specified text file."""
        fid_stats,aliases = self.fid_stats,self.aliases
        with CsvReader(textPath) as ins:
            for fields in ins:
                if len(fields) < 12 or fields[1][:2] != u'0x': continue
                mmod,mobj,eid,full,modPath,modb,iconPath,smod,sobj,uses,\
                value,weight = fields[:12]
                mmod = _coerce(mmod,unicode)
                mid = (GPath(aliases.get(mmod,mmod)),_coerce(mobj,int,16))
                smod = _coerce(smod,unicode,AllowNone=True)
                if smod is None: sid = None
                else: sid = (
                    GPath(aliases.get(smod,smod)),_coerce(sobj,int,16))
                eid = _coerce(eid,unicode,AllowNone=True)
                full = _coerce(full,unicode,AllowNone=True)
                modPath = _coerce(modPath,unicode,AllowNone=True)
                modb = _coerce(modb,float)
                iconPath = _coerce(iconPath,unicode,AllowNone=True)
                uses = _coerce(uses,int)
                value = _coerce(value,int)
                weight = _coerce(weight,float)
                effects = self.readEffects(fields[12:],aliases,False)
                fid_stats[mid] = [eid,full,modPath,modb,iconPath,sid,uses,
                                  value,weight,effects]

    def writeToText(self,textPath):
        """Exports stats to specified text file."""
        fid_stats = self.fid_stats
        header = (_(u'Mod Name'),_(u'ObjectIndex'),_(u'Editor Id'),_(u'Name'),
                  _(u'Model Path'),_(u'Bound Radius'),_(u'Icon Path'),
                  _(u'Script Mod Name'),_(u'Script ObjectIndex'),_(u'Uses'),
                  _(u'Value'),_(u'Weight'),) + _UsesEffectsMixin.headers * 2 +\
                     (_(u'Additional Effects (Same format)'),)
        headFormat = u','.join([u'"%s"'] * len(header)) + u'\n'
        rowFormat = u'"%s","0x%06X","%s","%s","%s","%f","%s","%s","0x%06X",' \
                    u'"%d","%d","%f"'
        altrowFormat = u'"%s","0x%06X","%s","%s","%s","%f","%s","%s","%s",' \
                       u'"%d","%d","%f"'
        with textPath.open('w',encoding='utf-8-sig') as out:
            outWrite = out.write
            outWrite(headFormat % header)
            for fid in sorted(fid_stats,key=lambda x:fid_stats[x][0].lower()):
                eid,name,modpath,modb,iconpath,scriptfid,uses,value,weight,\
                effects = fid_stats[fid]
                scriptfid = scriptfid or (GPath(u'None'),None)
                try:
                    output = rowFormat % (
                        fid[0].s,fid[1],eid,name,modpath,modb,iconpath,
                        scriptfid[0].s,scriptfid[1],uses,value,weight)
                except TypeError:
                    output = altrowFormat % (
                        fid[0].s,fid[1],eid,name,modpath,modb,iconpath,
                        scriptfid[0].s,scriptfid[1],uses,value,weight)
                output += self.writeEffects(effects,False)
                output += u'\n'
                outWrite(output)

class CBash_SigilStoneDetails(_UsesEffectsMixin):
    """Details on SigilStones, with functions for importing/exporting
    from/to mod/text file."""

    def __init__(self,types=None,aliases=None):
        self.fid_stats = {}
        self.aliases = aliases or {} #--For aliasing mod names

    def readFromMod(self,modInfo):
        """Reads stats from specified mod."""
        fid_stats = self.fid_stats
        with ObCollection(ModsPath=dirs['mods'].s) as Current:
            modFile = Current.addMod(modInfo.getPath().stail,Saveable=False,
                                     LoadMasters=False)
            Current.load()
            for record in modFile.SGST:
                fid_stats[record.fid] = [record.eid,record.full,record.modPath,
                                         record.modb,record.iconPath,
                                         record.script,record.uses,
                                         record.value,record.weight,
                                         record.effects_list]

    def writeToMod(self,modInfo):
        """Writes stats to specified mod."""
        fid_stats = self.fid_stats
        changed = []
        with ObCollection(ModsPath=dirs['mods'].s) as Current:
            modFile = Current.addMod(modInfo.getPath().stail,LoadMasters=False)
            Current.load()
            fid_stats = FormID.FilterValidDict(fid_stats,modFile,True,False)
            for record in modFile.SGST:
                newStats = fid_stats.get(record.fid,None)
                if not newStats: continue
                if not ValidateList(newStats,modFile): continue
                oldStats = [record.eid,record.full,record.modPath,record.modb,
                            record.iconPath,record.script,record.uses,
                            record.value,record.weight,record.effects_list]
                if oldStats != newStats:
                    changed.append(oldStats[0]) #eid
                    record.eid,record.full,record.modPath,record.modb,\
                    record.iconPath,record.script,record.uses,record.value,\
                    record.weight,effects = newStats
                    record.effects_list = effects
            if changed: modFile.save()
            return changed

    def readFromText(self,textPath):
        """Imports stats from specified text file."""
        fid_stats,aliases = self.fid_stats,self.aliases
        with CsvReader(textPath) as ins:
            for fields in ins:
                if len(fields) < 12 or fields[1][:2] != u'0x': continue
                mmod,mobj,eid,full,modPath,modb,iconPath,smod,sobj,uses,\
                value,weight = fields[:12]
                mmod = _coerce(mmod,unicode)
                mid = FormID(GPath(aliases.get(mmod,mmod)),
                             _coerce(mobj,int,16))
                smod = _coerce(smod,unicode,AllowNone=True)
                if smod is None: sid = FormID(None,None)
                else: sid = FormID(GPath(aliases.get(smod,smod)),
                                   _coerce(sobj,int,16))
                eid = _coerce(eid,unicode,AllowNone=True)
                full = _coerce(full,unicode,AllowNone=True)
                modPath = _coerce(modPath,unicode,AllowNone=True)
                modb = _coerce(modb,float)
                iconPath = _coerce(iconPath,unicode,AllowNone=True)
                uses = _coerce(uses,int)
                value = _coerce(value,int)
                weight = _coerce(weight,float)
                effects = self.readEffects(fields[12:],aliases,True)
                fid_stats[mid] = [eid,full,modPath,modb,iconPath,sid,uses,
                                  value,weight,effects]

    def writeToText(self,textPath):
        """Exports stats to specified text file."""
        fid_stats = self.fid_stats
        header = (_(u'Mod Name'),_(u'ObjectIndex'),_(u'Editor Id'),_(u'Name'),
                  _(u'Model Path'),_(u'Bound Radius'),_(u'Icon Path'),
                  _(u'Script Mod Name'),_(u'Script ObjectIndex'),_(u'Uses'),
                  _(u'Value'),_(u'Weight'),) + _UsesEffectsMixin.headers * 2 +\
                     (_(u'Additional Effects (Same format)'),)
        headFormat = u','.join([u'"%s"'] * len(header)) + u'\n'
        rowFormat = u'"%s","0x%06X","%s","%s","%s","%f","%s","%s","0x%06X",' \
                    u'"%d","%d","%f"'
        altrowFormat = u'"%s","0x%06X","%s","%s","%s","%f","%s","%s","%s",' \
                       u'"%d","%d","%f"'
        with textPath.open('w',encoding='utf-8-sig') as out:
            outWrite = out.write
            outWrite(headFormat % header)
            for fid in sorted(fid_stats,key=lambda x:fid_stats[x][0]):
                eid,name,modpath,modb,iconpath,scriptfid,uses,value,weight,\
                effects = fid_stats[fid]
                scriptfid = scriptfid or (GPath(u'None'),None)
                try:
                    output = rowFormat % (
                        fid[0],fid[1],eid,name,modpath,modb,iconpath,
                        scriptfid[0],scriptfid[1],uses,value,weight)
                except TypeError:
                    output = altrowFormat % (
                        fid[0],fid[1],eid,name,modpath,modb,iconpath,
                        scriptfid[0],scriptfid[1],uses,value,weight)
                output += self.writeEffects(effects,True)
                output += u'\n'
                outWrite(output)

#------------------------------------------------------------------------------
class _ItemPrices(object):
    item_prices_attrs = ('value', 'eid', 'full')

class ItemPrices(_ItemPrices):
    """Function for importing/exporting from/to mod/text file only the
    value, name and eid of records."""

    def __init__(self,types=None,aliases=None):
        self.class_fid_stats = bush.game.pricesTypes
        self.aliases = aliases or {} #--For aliasing mod names

    def readFromMod(self,modInfo):
        """Reads data from specified mod."""
        class_fid_stats = self.class_fid_stats
        typeClasses = [MreRecord.type_class[x] for x in class_fid_stats]
        loadFactory = LoadFactory(False,*typeClasses)
        modFile = ModFile(modInfo,loadFactory)
        modFile.load(True)
        mapper = modFile.getLongMapper()
        attrs = self.item_prices_attrs
        for group, fid_stats in class_fid_stats.iteritems():
            for record in getattr(modFile,group).getActiveRecords():
                fid_stats[mapper(record.fid)] = map(record.__getattribute__,
                                                    attrs)

    def writeToMod(self,modInfo):
        """Writes stats to specified mod."""
        class_fid_stats = self.class_fid_stats
        typeClasses = [MreRecord.type_class[x] for x in class_fid_stats]
        loadFactory = LoadFactory(True,*typeClasses)
        modFile = ModFile(modInfo,loadFactory)
        modFile.load(True)
        mapper = modFile.getLongMapper()
        changed = defaultdict(int) #--changed[modName] = numChanged
        for group, fid_stats in class_fid_stats.iteritems():
            for record in getattr(modFile,group).getActiveRecords():
                longid = mapper(record.fid)
                stats = fid_stats.get(longid,None)
                if not stats: continue
                value = stats[0]
                if record.value != value:
                    record.value = value
                    changed[longid[0]] += 1
                    record.setChanged()
        if changed: modFile.safeSave()
        return changed

    def readFromText(self,textPath):
        """Reads stats from specified text file."""
        class_fid_stats, aliases = self.class_fid_stats, self.aliases
        with CsvReader(textPath) as ins:
            for fields in ins:
                if len(fields) < 6 or fields[1][:2] != u'0x': continue
                mmod,mobj,value,eid,name,group = fields[:6]
                mmod = GPath(_coerce(mmod, unicode))
                longid = (GPath(aliases.get(mmod,mmod)),_coerce(mobj, int, 16))
                value = _coerce(value, int)
                eid = _coerce(eid, unicode, AllowNone=True)
                name = _coerce(name, unicode, AllowNone=True)
                group = _coerce(group, unicode)
                class_fid_stats[group][longid] = [value,eid,name]

    def writeToText(self,textPath):
        """Writes stats to specified text file."""
        class_fid_stats = self.class_fid_stats
        with textPath.open('w',encoding='utf-8-sig') as out:
            format_,header = csvFormat(u'iss'),(u'"' + u'","'.join((
                _(u'Mod Name'),_(u'ObjectIndex'),_(u'Value'),_(u'Editor Id'),
                _(u'Name'),_(u'Type'))) + u'"\n')
            for group, fid_stats in sorted(class_fid_stats.iteritems()):
                if not fid_stats: continue
                out.write(header)
                for fid in sorted(fid_stats,key=lambda x:(
                        fid_stats[x][1].lower(),fid_stats[x][0])):
                    out.write(u'"%s","0x%06X",' % (fid[0].s,fid[1]))
                    out.write(
                        format_ % tuple(fid_stats[fid]) + u',%s\n' % group)

class CBash_ItemPrices(_ItemPrices):
    """Function for importing/exporting from/to mod/text file only the
    value, name and eid of records."""

    def __init__(self,types=None,aliases=None):
        self.class_fid_stats = {'ALCH':{},'AMMO':{},'APPA':{},'ARMO':{},
                                'BOOK':{},'CLOT':{},'INGR':{},'KEYM':{},
                                'LIGH':{},'MISC':{},'SGST':{},'SLGM':{},
                                'WEAP':{}}
        self.aliases = aliases or {} #--For aliasing mod names

    def readFromMod(self,modInfo):
        """Reads data from specified mod."""
        class_fid_stats, attrs = self.class_fid_stats, self.item_prices_attrs
        with ObCollection(ModsPath=dirs['mods'].s) as Current:
            modFile = Current.addMod(modInfo.getPath().stail,LoadMasters=False)
            Current.load()
            for group, fid_stats in class_fid_stats.iteritems():
                for record in getattr(modFile,group):
                    fid_stats[record.fid] = map(record.__getattribute__,attrs)

    def writeToMod(self,modInfo):
        """Writes stats to specified mod."""
        class_fid_stats = self.class_fid_stats
        with ObCollection(ModsPath=dirs['mods'].s) as Current:
            modFile = Current.addMod(modInfo.getPath().stail,LoadMasters=False)
            Current.load()
            changed = defaultdict(int) #--changed[modName] = numChanged
            for group,fid_stats in class_fid_stats.iteritems():
                fid_stats = FormID.FilterValidDict(fid_stats,modFile,True,
                                                   False)
                for fid,stats in fid_stats.iteritems():
                    record = modFile.LookupRecord(fid)
                    if record and record._Type == group:
                        value = stats[0]
                        if record.value != value:
                            record.value = value
                            changed[fid[0]] += 1
            if changed: modFile.save()
            return changed

    def readFromText(self,textPath):
        """Reads stats from specified text file."""
        class_fid_stats, aliases = self.class_fid_stats, self.aliases
        with CsvReader(textPath) as ins:
            for fields in ins:
                if len(fields) < 6 or fields[1][:2] != u'0x': continue
                mmod,mobj,value,eid,name,group = fields[:6]
                mmod = GPath(_coerce(mmod, unicode))
                longid = FormID(GPath(aliases.get(mmod,mmod)),
                                _coerce(mobj,int,16))
                value = _coerce(value, int)
                eid = _coerce(eid, unicode, AllowNone=True)
                name = _coerce(name, unicode, AllowNone=True)
                group = _coerce(group, unicode)
                class_fid_stats[group][longid] = [value,eid,name]

    def writeToText(self,textPath):
        """Writes stats to specified text file."""
        class_fid_stats = self.class_fid_stats
        with textPath.open('w',encoding='utf-8-sig') as out:
            format_,header = csvFormat(u'iss'),(u'"' + u'","'.join((
                _(u'Mod Name'),_(u'ObjectIndex'),_(u'Value'),_(u'Editor Id'),
                _(u'Name'),_(u'Type'))) + u'"\n')
            for group,fid_stats in sorted(class_fid_stats.iteritems()):
                if not fid_stats: continue
                out.write(header)
                for fid in sorted(fid_stats,key=lambda x:(
                        fid_stats[x][1],fid_stats[x][0])):
                    out.write(u'"%s","0x%06X",' % (fid[0],fid[1]))
                    out.write(
                        format_ % tuple(fid_stats[fid]) + u',%s\n' % group)

#------------------------------------------------------------------------------
class CompleteItemData(_UsesEffectsMixin): #Needs work
    """Statistics for armor and weapons, with functions for
    importing/exporting from/to mod/text file."""

    def __init__(self,types=None,aliases=None):
        self.type_stats = {'ALCH':{},'AMMO':{},'APPA':{},'ARMO':{},'BOOK':{},
                           'CLOT':{},'INGR':{},'KEYM':{},'LIGH':{},'MISC':{},
                           'SGST':{},'SLGM':{},'WEAP':{}}
        self.type_attrs = {'ALCH':('eid','full','weight','value','iconPath',
                                   'model','IsFood','IsNoAutoCalc','script',
                                   'effects'),#TODO: proper effects export
                           'AMMO':('eid','full','weight','value','damage',
                                   'speed','enchantPoints','iconPath','model',
                                   'script','enchantment','IsNormal'),
                           'APPA':('eid','full','weight','value','quality',
                                   'iconPath'),
                           'ARMO':('eid','full','weight','value','health',
                                   'strength','maleIconPath','femaleIconPath'),
                           'BOOK':('eid','full','weight','value',
                                   'enchantPoints','iconPath'),
                           'CLOT':('eid','full','weight','value',
                                   'enchantPoints','maleIconPath',
                                   'femaleIconPath'),
                           'INGR':('eid','full','weight','value','iconPath'),
                           'KEYM':('eid','full','weight','value','iconPath'),
                           'LIGH':('eid','full','weight','value','duration',
                                   'iconPath'),
                           'MISC':('eid','full','weight','value','iconPath'),
                           'SGST':('eid','full','weight','value','uses',
                                   'iconPath'),
                           'SLGM':('eid','full','weight','value','iconPath'),
                           'WEAP':('eid','full','weight','value','health',
                                   'damage','speed','reach','enchantPoints',
                                   'iconPath'),
        }
        self.aliases = aliases or {} #--For aliasing mod fulls

    def readFromMod(self,modInfo):
        """Reads stats from specified mod."""
        self.model = {}
        self.Mmodel = {}
        self.Fmodel = {}
        self.MGndmodel = {}
        self.FGndmodel = {}
        typeClasses = [MreRecord.type_class[x] for x in (
            'ALCH','AMMO','APPA','ARMO','BOOK','CLOT','INGR','KEYM','LIGH',
            'MISC','SGST','SLGM','WEAP')]
        loadFactory = LoadFactory(False,*typeClasses)
        modFile = ModFile(modInfo,loadFactory)
        modFile.load(True)
        mapper = modFile.getLongMapper()
        for type_ in self.type_stats:
            stats,attrs = self.type_stats[type_],self.type_attrs[type_]
            for record in getattr(modFile,type_).getActiveRecords():
                longid = mapper(record.fid)
                recordGetAttr = record.__getattribute__
                stats[longid] = tuple(recordGetAttr(attr) for attr in attrs)
                if type_ in ['ALCH','AMMO','APPA','BOOK','INGR','KEYM','LIGH',
                             'MISC','SGST','SLGM','WEAP']:
                    if record.model:
                        self.model[longid] = record.model.modPath
                elif type_ in ['CLOT','ARMO']:
                    if record.maleBody:
                        self.Mmodel[longid] = record.maleBody.modPath
                    if record.maleWorld:
                        self.MGndmodel[longid] = record.maleWorld.modPath
                    if record.femaleBody:
                        self.Fmodel[longid] = record.femaleBody.modPath
                    if record.femaleWorld:
                        self.FGndmodel[longid] = record.femaleWorld.modPath

    def writeToMod(self,modInfo):
        """Writes stats to specified mod."""
        typeClasses = [MreRecord.type_class[x] for x in (
            'ALCH','AMMO','APPA','ARMO','BOOK','CLOT','INGR','KEYM','LIGH',
            'MISC','SGST','SLGM','WEAP')]
        loadFactory = LoadFactory(True,*typeClasses)
        modFile = ModFile(modInfo,loadFactory)
        modFile.load(True)
        mapper = modFile.getLongMapper()
        changed = defaultdict(int) #--changed[modName] = numChanged
        for type_ in self.type_stats:
            stats,attrs = self.type_stats[type_],self.type_attrs[type_]
            for record in getattr(modFile,type_).getActiveRecords():
                longid = mapper(record.fid)
                itemStats = stats.get(longid,None)
                if not itemStats: continue
                map(record.__setattr__,attrs,itemStats)
                record.setChanged()
                changed[longid[0]] += 1
        if changed: modFile.safeSave()
        return changed

    def readFromText(self,textPath):
        """Reads stats from specified text file."""
        alch,ammo,appa,armor,books,clothing,ingredients,keys,lights,misc,\
        sigilstones,soulgems,weapons = [
            self.type_stats[type_] for type_ in (
                'ALCH','AMMO','APPA','ARMO','BOOK','CLOT','INGR','KEYM','LIGH',
                'MISC','SGST','SLGM','WEAP')]
        aliases = self.aliases
        with CsvReader(textPath) as ins:
            sfloat = lambda a:struct_unpack('f',struct_pack('f',float(a)))[
                0] #--Force standard precision
            for fields in ins:
                if len(fields) < 3 or fields[2][:2] != '0x': continue
                type_,modName,objectStr,eid = fields[0:4]
                modName = GPath(modName)
                longid = (
                    GPath(aliases.get(modName,modName)),int(objectStr[2:],16))
                if type_ == 'ALCH':
                    alch[longid] = (eid,) + tuple(
                        func(field) for func,field in #--(weight, value)
                        zip((decode,sfloat,int,decode),fields[4:8]))
                elif type_ == 'AMMO':
                    ammo[longid] = (eid,) + tuple(func(field) for func,field in
                        #--(weight, value, damage, speed, enchantPoints)
                        zip((decode,sfloat,int,int,sfloat,int,decode),
                            fields[4:11]))
                elif type_ == 'APPA':
                    appa[longid] = (eid,) + tuple(func(field) for func,field in
                        #--(weight,value,quantity)
                        zip((decode,sfloat,int,sfloat,decode),fields[4:9]))
                elif type_ == 'ARMO':
                    armor[longid] = (eid,) + tuple(
                        func(field) for func,field in
                        #--(weight, value, health, strength)
                        zip((decode,sfloat,int,int,int,decode,decode),
                            fields[4:10]))
                elif type_ == 'BOOK':
                    books[longid] = (eid,) + tuple(
                        func(field) for func,field in
                        #--(weight, value, echantPoints)
                        zip((decode,sfloat,int,int,decode),fields[4:9]))
                elif type_ == 'CLOT':
                    clothing[longid] = (eid,) + tuple(
                        func(field) for func,field in
                        #--(weight, value, echantPoints)
                        zip((decode,sfloat,int,int,decode,decode),
                            fields[4:10]))
                elif type_ == 'INGR':
                    ingredients[longid] = (eid,) + tuple(
                        func(field) for func,field in #--(weight, value)
                        zip((decode,sfloat,int,decode),fields[4:8]))
                elif type_ == 'KEYM':
                    keys[longid] = (eid,) + tuple(
                        func(field) for func,field in #--(weight, value)
                        zip((decode,sfloat,int,decode),fields[4:8]))
                elif type_ == 'LIGH':
                    lights[longid] = (eid,) + tuple(
                        func(field) for func,field in
                        #--(weight, value, duration)
                        zip((decode,sfloat,int,int,decode),fields[4:9]))
                elif type_ == 'MISC':
                    misc[longid] = (eid,) + tuple(
                        func(field) for func,field in #--(weight, value)
                        zip((decode,sfloat,int,decode),fields[4:8]))
                elif type_ == 'SGST':
                    sigilstones[longid] = (eid,) + tuple(
                        func(field) for func,field in #--(weight, value, uses)
                        zip((decode,sfloat,int,int,decode),fields[4:9]))
                elif type_ == 'SLGM':
                    soulgems[longid] = (eid,) + tuple(
                        func(field) for func,field in #--(weight, value)
                        zip((decode,sfloat,int,decode),fields[4:8]))
                elif type_ == 'WEAP':
                    weapons[longid] = (eid,) + tuple(func(field) for func,field
                        in #--(weight, value, health, damage, speed, reach,
                        #  epoints)
                        zip((decode,sfloat,int,int,int,sfloat,sfloat,int,
                             decode),fields[4:13]))

    def writeToText(self,textPath):
        """Writes stats to specified text file."""
        def getSortedIds(stats):
            longids = stats.keys()
            longids.sort(key=lambda a:stats[a][0])
            longids.sort(key=itemgetter(0))
            return longids
        with textPath.open('w',encoding='utf-8-sig') as out:
            for type_,format_,header in (
                    #--Alch
                    ('ALCH',csvFormat(u'ssfiss') + u'\n',(
                                    u'"' + u'","'.join((
                                        _(u'Type'),_(u'Mod Name'),
                                        _(u'ObjectIndex'),_(u'Editor Id'),
                                        _(u'Name'),_(u'Weight'),_(u'Value'),
                                        _(u'Icon Path'),
                                        _(u'Model'))) + u'"\n')),
                    #--Ammo
                    ('AMMO',csvFormat(u'ssfiifiss') + u'\n',(
                                    u'"' + u'","'.join((
                                        _(u'Type'),_(u'Mod Name'),
                                        _(u'ObjectIndex'),_(u'Editor Id'),
                                        _(u'Name'),_(u'Weight'),_(u'Value'),
                                        _(u'Damage'),_(u'Speed'),_(u'EPoints'),
                                        _(u'Icon Path'),
                                        _(u'Model'))) + u'"\n')),
                    #--Apparatus
                    ('APPA',csvFormat(u'ssfifss') + u'\n',(
                                    u'"' + u'","'.join((
                                        _(u'Type'),_(u'Mod Name'),
                                        _(u'ObjectIndex'),_(u'Editor Id'),
                                        _(u'Name'),_(u'Weight'),_(u'Value'),
                                        _(u'Quantity'),_(u'Icon Path'),
                                        _(u'Model'))) + u'"\n')),
                    #--Armor
                    ('ARMO',csvFormat(u'ssfiiissssss') + u'\n',(
                                    u'"' + u'","'.join((
                                        _(u'Type'),_(u'Mod Name'),
                                        _(u'ObjectIndex'),_(u'Editor Id'),
                                        _(u'Name'),_(u'Weight'),_(u'Value'),
                                        _(u'Health'),_(u'AR'),
                                        _(u'Male Icon Path'),
                                        _(u'Female Icon Path'),
                                        _(u'Male Model Path'),
                                        _(u'Female Model Path'),
                                        _(u'Male World Model Path'),
                                        _(u'Female World Model '
                                          u'Path'))) + u'"\n')),#Books
                    ('BOOK',csvFormat(u'ssfiiss') + u'\n',(
                                    u'"' + u'","'.join((
                                        _(u'Type'),_(u'Mod Name'),
                                        _(u'ObjectIndex'),_(u'Editor Id'),
                                        _(u'Name'),_(u'Weight'),_(u'Value'),
                                        _(u'EPoints'),_(u'Icon Path'),
                                        _(u'Model'))) + u'"\n')),
                    #--Clothing
                    ('CLOT',csvFormat(u'ssfiissssss') + u'\n',(
                                    u'"' + u'","'.join((
                                        _(u'Type'),_(u'Mod Name'),
                                        _(u'ObjectIndex'),_(u'Editor Id'),
                                        _(u'Name'),_(u'Weight'),_(u'Value'),
                                        _(u'EPoints'),_(u'Male Icon Path'),
                                        _(u'Female Icon Path'),
                                        _(u'Male Model Path'),
                                        _(u'Female Model Path'),
                                        _(u'Male World Model Path'),
                                        _(u'Female World Model '
                                          u'Path'))) + u'"\n')),
                    #--Ingredients
                    ('INGR',csvFormat(u'ssfiss') + u'\n',(
                                    u'"' + u'","'.join((
                                        _(u'Type'),_(u'Mod Name'),
                                        _(u'ObjectIndex'),_(u'Editor Id'),
                                        _(u'Name'),_(u'Weight'),_(u'Value'),
                                        _(u'Icon Path'),
                                        _(u'Model'))) + u'"\n')),
                    #--Keys
                    ('KEYM',csvFormat(u'ssfiss') + u'\n',(
                                    u'"' + u'","'.join((
                                        _(u'Type'),_(u'Mod Name'),
                                        _(u'ObjectIndex'),_(u'Editor Id'),
                                        _(u'Name'),_(u'Weight'),_(u'Value'),
                                        _(u'Icon Path'),
                                        _(u'Model'))) + u'"\n')),
                    #--Lights
                    ('LIGH',csvFormat(u'ssfiiss') + u'\n',(
                                    u'"' + u'","'.join((
                                        _(u'Type'),_(u'Mod Name'),
                                        _(u'ObjectIndex'),_(u'Editor Id'),
                                        _(u'Name'),_(u'Weight'),_(u'Value'),
                                        _(u'Duration'),_(u'Icon Path'),
                                        _(u'Model'))) + u'"\n')),
                    #--Misc
                    ('MISC',csvFormat(u'ssfiss') + u'\n',(u'"' + u'","'.join((
                                        _(u'Type'),_(u'Mod Name'),
                                        _(u'ObjectIndex'),_(u'Editor Id'),
                                        _(u'Name'),_(u'Weight'),_(u'Value'),
                                        _(u'Icon Path'),
                                        _(u'Model'))) + u'"\n')),
                    #--Sigilstones
                    ('SGST',csvFormat(u'ssfiiss') + u'\n',(
                                    u'"' + u'","'.join((
                                        _(u'Type'),_(u'Mod Name'),
                                        _(u'ObjectIndex'),_(u'Editor Id'),
                                        _(u'Name'),_(u'Weight'),_(u'Value'),
                                        _(u'Uses'),_(u'Icon Path'),
                                        _(u'Model'))) + u'"\n')),
                    #--Soulgems
                    ('SLGM',csvFormat(u'ssfiss') + u'\n',(
                                    u'"' + u'","'.join((
                                        _(u'Type'),_(u'Mod Name'),
                                        _(u'ObjectIndex'),_(u'Editor Id'),
                                        _(u'Name'),_(u'Weight'),_(u'Value'),
                                        _(u'Icon Path'),
                                        _(u'Model'))) + u'"\n')),
                    #--Weapons
                    ('WEAP',csvFormat(u'ssfiiiffiss') + u'\n',(
                                    u'"' + u'","'.join((
                                        _(u'Type'),_(u'Mod Name'),
                                        _(u'ObjectIndex'),_(u'Editor Id'),
                                        _(u'Name'),_(u'Weight'),_(u'Value'),
                                        _(u'Health'),_(u'Damage'),_(u'Speed'),
                                        _(u'Reach'),_(u'EPoints'),
                                        _(u'Icon Path'),
                                        _(u'Model'))) + u'"\n')),
            ):
                stats = self.type_stats[type_]
                if not stats: continue
                out.write(u'\n' + header)
                for longid in getSortedIds(stats):
                    out.write(
                        u'"%s","%s","0x%06X",' % (type_,longid[0].s,longid[1]))
                    tempstats = list(stats[longid])
                    if type_ == 'ARMO' or type_ == 'CLOT':
                        tempstats.append(self.Mmodel.get(longid,u'NONE'))
                        tempstats.append(self.Fmodel.get(longid,u'NONE'))
                        tempstats.append(self.MGndmodel.get(longid,u'NONE'))
                        tempstats.append(self.FGndmodel.get(longid,u'NONE'))
                    else:
                        tempstats.append(self.model.get(longid,u'NONE'))
                    finalstats = tuple(tempstats)
                    out.write(format_ % finalstats)

class CBash_CompleteItemData(_UsesEffectsMixin): #Needs work
    """Statistics for armor and weapons, with functions for
    importing/exporting from/to mod/text file."""

    @staticmethod
    def sstr(value):
        return _coerce(value,unicode,AllowNone=True)

    @staticmethod
    def sfloat(value):
        return _coerce(value,float,AllowNone=True)

    @staticmethod
    def sint(value):
        return _coerce(value,int,AllowNone=True)

    @staticmethod
    def snoneint(value):
        x = _coerce(value,int,AllowNone=True)
        if x == 0: return None
        return x

    @staticmethod
    def sbool(value):
        return _coerce(value,bool)

    def __init__(self,types=None,aliases=None):
        self.class_fid_values = {}
        self.aliases = aliases or {} #--For aliasing mod names

    def readFromMod(self,modInfo):
        """Reads stats from specified mod."""
        class_fid_values = self.class_fid_values
        with ObCollection(ModsPath=dirs['mods'].s) as Current:
            modFile = Current.addMod(modInfo.getPath().stail,LoadMasters=False)
            Current.load()
            for group in pickupables:
                for record in getattr(modFile,group):
                    values = ExtractExportList(record)
                    print values
                    print
                    print
                    class_fid_values.setdefault(group,{})[record.fid] = values
                    break

    def writeToMod(self,modInfo):
        """Exports type_id_name to specified mod."""
        with ObCollection(ModsPath=dirs['mods'].s) as Current:
            modFile = Current.addMod(modInfo.getPath().stail,LoadMasters=False)
            Current.load()
            changed = defaultdict(int) #--changed[modName] = numChanged
            for group,fid_attr_value in self.class_fid_attr_value.iteritems():
                attrs = self.class_attrs[group]
                fid_attr_value = FormID.FilterValidDict(fid_attr_value,modFile,
                                                        True,False)
                for fid,attr_value in fid_attr_value.iteritems():
                    record = modFile.LookupRecord(fid)
                    if record and record._Type == group:
                        if not ValidateDict(attr_value,modFile): continue
                        oldValues = map(record.__getattribute__,attrs)
                        if oldValues != attr_value:
                            map(record.__setattr__,attrs,attr_value)
                            changed[fid[0]] += 1
            if changed: modFile.save()
            return changed

    def readEffectsFromText(self,fields):
        effects = []
        _effects = fields[12:]
        actorValueName_Number = _UsesEffectsMixin.actorValueName_Number
        recipientTypeName_Number = _UsesEffectsMixin.recipientTypeName_Number
        aliases = self.aliases
        while len(_effects) >= 13:
            _effect,_effects = _effects[1:13],_effects[13:]
            name,magnitude,area,duration,range_,actorvalue,semod,seobj,\
            seschool,sevisual,seflags,sename = tuple(
                _effect)
            name = _coerce(name,unicode,
                           AllowNone=True) #OBME not supported (support
            # requires adding a mod/objectid format to the
            # csv, this assumes all MGEFCodes are raw)
            magnitude = _coerce(magnitude,int,AllowNone=True)
            area = _coerce(area,int,AllowNone=True)
            duration = _coerce(duration,int,AllowNone=True)
            range_ = _coerce(range_,unicode,AllowNone=True)
            if range_:
                range_ = recipientTypeName_Number.get(range_.lower(),
                                                      _coerce(range_,int))
            actorvalue = _coerce(actorvalue,unicode,AllowNone=True)
            if actorvalue:
                actorvalue = actorValueName_Number.get(actorvalue.lower(),
                                                       _coerce(actorvalue,int))
            if None in (name,magnitude,area,duration,range_,actorvalue):
                continue
            effect = [MGEFCode(name),magnitude,area,duration,range_,
                      ActorValue(actorvalue)]
            semod = _coerce(semod,unicode,AllowNone=True)
            seobj = _coerce(seobj,int,16,AllowNone=True)
            seschool = _coerce(seschool,int,AllowNone=True)
            sevisual = _coerce(sevisual,int,AllowNone=True)
            seflags = _coerce(seflags,int,AllowNone=True)
            sename = _coerce(sename,unicode,AllowNone=True)
            if None in (semod,seobj,seschool,sevisual,seflags,sename):
                effect.extend(
                    [FormID(None,None),None,MGEFCode(None,None),None,None])
            else:
                effect.extend(
                    [FormID(GPath(aliases.get(semod,semod)),seobj),seschool,
                     MGEFCode(sevisual),seflags,sename])
            effects.append(tuple(effect))
        return effects

    def readSGSTFromText(self,fields):
        aliases = self.aliases
        eid,full,weight,value,uses,iconPath,modPath,modb,smod,sobj = fields[
                                                                     :10]
        fields = fields[:10]
        smod = _coerce(smod,unicode,AllowNone=True)
        if smod is None: sid = FormID(None,None)
        else: sid = FormID(GPath(aliases.get(smod,smod)),_coerce(sobj,int,16))
        eid = _coerce(eid,unicode,AllowNone=True)
        full = _coerce(full,unicode,AllowNone=True)
        modPath = _coerce(modPath,unicode,AllowNone=True)
        modb = _coerce(modb,float)
        iconPath = _coerce(iconPath,unicode,AllowNone=True)
        uses = _coerce(uses,int)
        value = _coerce(value,int)
        weight = _coerce(weight,float)
        effects = self.readEffectsFromText(fields)
        return [eid,full,weight,value,uses,iconPath,modPath,modb,sid,effects]

    def readFromText(self,textPath):
        """Reads stats from specified text file."""
        class_fid_attr_value,aliases = self.class_fid_attr_value,self.aliases
        with CsvReader(textPath) as ins:
            for fields in ins:
                if len(fields) < 3 or fields[2][:2] != u'0x': continue
                group,modName,objectStr = fields[:3]
                fields = fields[3:]
                modName = GPath(_coerce(modName,unicode))
                longid = FormID(GPath(aliases.get(modName,modName)),
                                _coerce(objectStr,int,16))
                if group == 'ALCH':
                    pass
                elif group == 'AMMO':
                    pass
                elif group == 'SGST':
                    class_fid_attr_value[group][
                        longid] = self.readSGSTFromText(fields)

    # noinspection PyUnreachableCode
    def writeToText(self,textPath):
        """Writes stats to specified text file."""
        return
        class_fid_attr_value = self.class_fid_attr_value
        with textPath.open('w',encoding='utf-8-sig') as out:
            def write(out,attrs,values):
                attr_type = self.attr_type
                csvFormat = u''
                sstr = self.sstr
                sint = self.sint
                snoneint = self.snoneint
                sfloat = self.sfloat
                for index,attr in enumerate(attrs):
                    stype = attr_type[attr]
                    values[index] = stype(values[index]) #sanitize output
                    if values[
                        index] is None: csvFormat += u',"{0[%d]}"' % index
                    elif stype is sstr: csvFormat += u',"{0[%d]}"' % index
                    elif stype is sint or stype is snoneint: csvFormat += \
                        u',"{0[%d]:d}"' % index
                    elif stype is sfloat: csvFormat += u',"{0[%d]:f}"' % index
                csvFormat = csvFormat[1:] #--Chop leading comma
                out.write(csvFormat.format(values) + u'\n')
            for group,header in (
                    #--Alch
                    ('ALCH',(u'"' + u'","'.join((
                            _(u'Type'),_(u'Mod Name'),_(u'ObjectIndex'),
                            _(u'Editor Id'),_(u'Weight'),
                            _(u'Value'))) + u'"\n')),
                    ('AMMO',(u'"' + u'","'.join((
                            _(u'Type'),_(u'Mod Name'),_(u'ObjectIndex'),
                            _(u'Editor Id'),_(u'Weight'),_(u'Value'),
                            _(u'Damage'),_(u'Speed'),
                            _(u'EPoints'))) + u'"\n')),
                    #--Apparatus
                    ('APPA',(u'"' + u'","'.join((
                            _(u'Mod Name'),_(u'ObjectIndex'),_(u'Editor Id'),
                            _(u'Weight'),_(u'Value'),
                            _(u'Quality'))) + u'"\n')),
                    #--Armor
                    ('ARMO',(u'"' + u'","'.join((
                            _(u'Type'),_(u'Mod Name'),_(u'ObjectIndex'),
                            _(u'Editor Id'),_(u'Weight'),_(u'Value'),
                            _(u'Health'),_(u'AR'))) + u'"\n')),
                    #--Books
                    ('BOOK',(u'"' + u'","'.join((
                            _(u'Type'),_(u'Mod Name'),_(u'ObjectIndex'),
                            _(u'Editor Id'),_(u'Weight'),_(u'Value'),
                            _(u'EPoints'))) + u'"\n')),
                    #--Clothing
                    ('CLOT',(u'"' + u'","'.join((
                            _(u'Type'),_(u'Mod Name'),_(u'ObjectIndex'),
                            _(u'Editor Id'),_(u'Weight'),_(u'Value'),
                            _(u'EPoints'))) + u'"\n')),
                    #--Ingredients
                    ('INGR',(u'"' + u'","'.join((
                            _(u'Type'),_(u'Mod Name'),_(u'ObjectIndex'),
                            _(u'Editor Id'),_(u'Weight'),
                            _(u'Value'))) + u'"\n')),
                    #--Keys
                    ('KEYM',(u'"' + u'","'.join((
                            _(u'Type'),_(u'Mod Name'),_(u'ObjectIndex'),
                            _(u'Editor Id'),_(u'Weight'),
                            _(u'Value'))) + u'"\n')),
                    #--Lights
                    ('LIGH',(u'"' + u'","'.join((
                            _(u'Type'),_(u'Mod Name'),_(u'ObjectIndex'),
                            _(u'Editor Id'),_(u'Weight'),_(u'Value'),
                            _(u'Duration'))) + u'"\n')),
                    #--Misc
                    ('MISC',(u'"' + u'","'.join((
                            _(u'Type'),_(u'Mod Name'),_(u'ObjectIndex'),
                            _(u'Editor Id'),_(u'Weight'),
                            _(u'Value'))) + u'"\n')),
                    #--Sigilstones
                    ('SGST',(u'"' + u'","'.join((
                            _(u'Type'),_(u'Mod Name'),_(u'ObjectIndex'),
                            _(u'Editor Id'),_(u'Weight'),_(u'Value'),
                            _(u'Uses'))) + u'"\n')),
                    #--Soulgems
                    ('SLGM',(u'"' + u'","'.join((
                            _(u'Type'),_(u'Mod Name'),_(u'ObjectIndex'),
                            _(u'Editor Id'),_(u'Weight'),
                            _(u'Value'))) + u'"\n')),
                    #--Weapons
                    ('WEAP',(u'"' + u'","'.join((
                            _(u'Type'),_(u'Mod Name'),_(u'ObjectIndex'),
                            _(u'Editor Id'),_(u'Weight'),_(u'Value'),
                            _(u'Health'),_(u'Damage'),_(u'Speed'),_(u'Reach'),
                            _(u'EPoints'))) + u'"\n')),
            ):
                fid_attr_value = class_fid_attr_value[group]
                if not fid_attr_value: continue
                attrs = self.class_attrs[group]
                out.write(header)
                for longid in getSortedIds(fid_attr_value):
                    out.write(
                        u'"%s","%s","0x%06X",' % (group,longid[0].s,longid[1]))
                    attr_value = fid_attr_value[longid]
                    write(out,attrs,map(attr_value.get,attrs))

#------------------------------------------------------------------------------
class SpellRecords(_UsesEffectsMixin):
    """Statistics for spells, with functions for importing/exporting from/to
    mod/text file."""

    def __init__(self,types=None,aliases=None,detailed=False):
        self.fid_stats = {}
        self.aliases = aliases or {} #--For aliasing mod names
        self.attrs = ('eid', 'full', 'cost', 'level', 'spellType')
        self.detailed = detailed
        if detailed:
            self.attrs += ('flags.noAutoCalc', 'flags.startSpell',
              'flags.immuneToSilence', 'flags.ignoreLOS',
              'flags.scriptEffectAlwaysApplies', 'flags.disallowAbsorbReflect',
              'flags.touchExplodesWOTarget') #, 'effects_list' is special cased
        self.spellTypeNumber_Name = {None:'NONE',
                                     0 : 'Spell',
                                     1 : 'Disease',
                                     2 : 'Power',
                                     3 : 'LesserPower',
                                     4 : 'Ability',
                                     5 : 'Poison',}
        self.spellTypeName_Number = dict(
            [(y.lower(),x) for x,y in self.spellTypeNumber_Name.iteritems() if
             x is not None])
        self.levelTypeNumber_Name = {None : 'NONE',
                                     0 : 'Novice',
                                     1 : 'Apprentice',
                                     2 : 'Journeyman',
                                     3 : 'Expert',
                                     4 : 'Master',}
        self.levelTypeName_Number = dict(
            [(y.lower(),x) for x,y in self.levelTypeNumber_Name.iteritems() if
             x is not None])

    def readFromMod(self,modInfo):
        """Reads stats from specified mod."""
        fid_stats, attrs = self.fid_stats, self.attrs
        detailed = self.detailed
        loadFactory= LoadFactory(False,MreRecord.type_class['SPEL'])
        modFile = ModFile(modInfo,loadFactory)
        modFile.load(True)
        modFile.convertToLongFids(['SPEL'])
        for record in modFile.SPEL.getActiveRecords():
            fid_stats[record.fid] = [getattr_deep(record,attr) for attr in
                                     attrs]
            if detailed:
                effects = []
                for effect in record.effects:
                    effectlist = [effect.name,effect.magnitude,effect.area,
                                  effect.duration,effect.recipient,
                                  effect.actorValue]
                    if effect.scriptEffect:
                        effectlist.append([effect.scriptEffect.script,
                                           effect.scriptEffect.school,
                                           effect.scriptEffect.visual,
                                           effect.scriptEffect.flags.hostile,
                                           effect.scriptEffect.full])
                    else: effectlist.append([])
                    effects.append(effectlist)
                fid_stats[record.fid].append(effects)

    def writeToMod(self,modInfo):
        """Writes stats to specified mod."""
        fid_stats, attrs = self.fid_stats, self.attrs
        detailed = self.detailed
        loadFactory= LoadFactory(True,MreRecord.type_class['SPEL'])
        modFile = ModFile(modInfo,loadFactory)
        modFile.load(True)
        mapper = modFile.getLongMapper()
        shortMapper = modFile.getShortMapper()
        changed = [] #eids
        for record in modFile.SPEL.getActiveRecords():
            newStats = fid_stats.get(mapper(record.fid), None)
            if not newStats: continue
            oldStats = [getattr_deep(record, attr) for attr in attrs]
            if detailed:
                effects = []
                for effect in record.effects:
                    effectlist = [effect.name,effect.magnitude,effect.area,
                                  effect.duration,effect.recipient,
                                  effect.actorValue]
                    if effect.scriptEffect:
                        effectlist.append([mapper(effect.scriptEffect.script),
                                           effect.scriptEffect.school,
                                           effect.scriptEffect.visual,
                                           effect.scriptEffect.flags.hostile,
                                           effect.scriptEffect.full])
                    else: effectlist.append([])
                    effects.append(effectlist)
                oldStats.append(effects)
            if oldStats != newStats:
                changed.append(oldStats[0]) #eid
                for attr, value in zip(attrs, newStats):
                    setattr_deep(record, attr, value)
                if detailed and len(newStats) > len(attrs):
                    effects = newStats[-1]
                    record.effects = []
                    for effect in effects:
                        neweffect = record.getDefault('effects')
                        neweffect.name,neweffect.magnitude,neweffect.area,\
                        neweffect.duration,neweffect.recipient,\
                        neweffect.actorValue,scripteffect = effect
                        if len(scripteffect):
                            scriptEffect = record.getDefault(
                                'effects.scriptEffect')
                            script,scriptEffect.school,scriptEffect.visual,\
                            scriptEffect.flags.hostile,scriptEffect.full = \
                                scripteffect
                            scriptEffect.script = shortMapper(script)
                            neweffect.scriptEffect = scriptEffect
                        record.effects.append(neweffect)
                record.setChanged()
        if changed: modFile.safeSave()
        return changed

    def readFromText(self,textPath):
        """Imports stats from specified text file."""
        detailed,aliases,spellTypeName_Number,levelTypeName_Number = \
            self.detailed,self.aliases,self.spellTypeName_Number,\
            self.levelTypeName_Number
        fid_stats = self.fid_stats
        with CsvReader(textPath) as ins:
            for fields in ins:
                if len(fields) < 8 or fields[2][:2] != u'0x': continue
                group,mmod,mobj,eid,full,cost,levelType,spellType = fields[:8]
                fields = fields[8:]
                group = _coerce(group, unicode)
                if group.lower() != u'spel': continue
                mmod = _coerce(mmod, unicode)
                mid = (GPath(aliases.get(mmod,mmod)),_coerce(mobj,int,16))
                eid = _coerce(eid, unicode, AllowNone=True)
                full = _coerce(full, unicode, AllowNone=True)
                cost = _coerce(cost, int)
                levelType = _coerce(levelType, unicode)
                levelType = levelTypeName_Number.get(levelType.lower(),
                                                     _coerce(levelType,
                                                             int) or 0)
                spellType = _coerce(spellType, unicode)
                spellType = spellTypeName_Number.get(spellType.lower(),
                                                     _coerce(spellType,
                                                             int) or 0)
                if not detailed or len(fields) < 7:
                    fid_stats[mid] = [eid,full,cost,levelType,spellType]
                    continue
                mc,ss,its,aeil,saa,daar,tewt = fields[:7]
                fields = fields[7:]
                mc = _coerce(mc, bool)
                ss = _coerce(ss, bool)
                its = _coerce(its, bool)
                aeil = _coerce(aeil, bool)
                saa = _coerce(saa, bool)
                daar = _coerce(daar, bool)
                tewt = _coerce(tewt, bool)
                effects = self.readEffects(fields, aliases, False)
                fid_stats[mid] = [eid,full,cost,levelType,spellType,mc,ss,its,
                                  aeil,saa,daar,tewt,effects]

    def writeToText(self,textPath):
        """Exports stats to specified text file."""
        detailed,fid_stats,spellTypeNumber_Name,levelTypeNumber_Name = \
            self.detailed,self.fid_stats,self.spellTypeNumber_Name,\
            self.levelTypeNumber_Name
        header = (_(u'Type'),_(u'Mod Name'),_(u'ObjectIndex'),_(u'Editor Id'),
                  _(u'Name'),_(u'Cost'),_(u'Level Type'),_(u'Spell Type'))
        rowFormat = u'"%s","%s","0x%06X","%s","%s","%d","%s","%s"'
        if detailed:
            header = header + (
                _(u'Manual Cost'),_(u'Start Spell'),_(u'Immune To Silence'),
                _(u'Area Effect Ignores LOS'),_(u'Script Always Applies'),
                _(u'Disallow Absorb and Reflect'),
                _(u'Touch Explodes Without Target'),
            ) + _UsesEffectsMixin.headers * 2 + (
                         _(u'Additional Effects (Same format)'),)
            rowFormat += u',"%s","%s","%s","%s","%s","%s","%s"'
        headFormat = u','.join([u'"%s"'] * len(header)) + u'\n'
        with textPath.open('w',encoding='utf-8-sig') as out:
            out.write(headFormat % header)
            for fid in sorted(fid_stats,
                              key=lambda x:(fid_stats[x][0].lower(),x[0])):
                if detailed:
                    eid,name,cost,levelType,spellType,mc,ss,its,aeil,saa,\
                    daar,tewt,effects = \
                    fid_stats[fid]
                    levelType = levelTypeNumber_Name.get(levelType,levelType)
                    spellType = spellTypeNumber_Name.get(spellType,spellType)
                    output = rowFormat % (
                    u'SPEL',fid[0].s,fid[1],eid,name,cost,levelType,spellType,
                    mc,ss,its,aeil,saa,daar,tewt)
                    output += self.writeEffects(effects, False)
                else:
                    eid,name,cost,levelType,spellType = fid_stats[fid]
                    levelType = levelTypeNumber_Name.get(levelType,levelType)
                    spellType = spellTypeNumber_Name.get(spellType,spellType)
                    output = rowFormat % (
                    u'SPEL',fid[0].s,fid[1],eid,name,cost,levelType,spellType)
                output += u'\n'
                out.write(output)

class CBash_SpellRecords(_UsesEffectsMixin):
    """Statistics for spells, with functions for importing/exporting from/to
    mod/text file."""

    def __init__(self,types=None,aliases=None,detailed=False):
        self.fid_stats = {}
        self.aliases = aliases or {} #--For aliasing mod names
        self.attrs = ('eid', 'full', 'cost', 'levelType', 'spellType')
        self.detailed = detailed
        if detailed:
            self.attrs += ('IsManualCost','IsStartSpell','IsSilenceImmune',
                'IsAreaEffectIgnoresLOS','IsScriptAlwaysApplies',
                'IsDisallowAbsorbReflect','IsTouchExplodesWOTarget',
                'effects_list')
        self.spellTypeNumber_Name = {None : u'NONE',
                                     0 : u'Spell',
                                     1 : u'Disease',
                                     2 : u'Power',
                                     3 : u'LesserPower',
                                     4 : u'Ability',
                                     5 : u'Poison',}
        self.spellTypeName_Number = dict(
            [(y.lower(),x) for x,y in self.spellTypeNumber_Name.iteritems() if
             x is not None])
        self.levelTypeNumber_Name = {None : u'NONE',
                                     0 : u'Novice',
                                     1 : u'Apprentice',
                                     2 : u'Journeyman',
                                     3 : u'Expert',
                                     4 : u'Master',}
        self.levelTypeName_Number = dict(
            [(y.lower(),x) for x,y in self.levelTypeNumber_Name.iteritems() if
             x is not None])

    def readFromMod(self,modInfo):
        """Reads stats from specified mod."""
        fid_stats, attrs = self.fid_stats, self.attrs
        with ObCollection(ModsPath=dirs['mods'].s) as Current:
            modFile = Current.addMod(modInfo.getPath().stail,LoadMasters=False)
            Current.load()
            for record in modFile.SPEL:
                fid_stats[record.fid] = map(record.__getattribute__, attrs)

    def writeToMod(self,modInfo):
        """Writes stats to specified mod."""
        fid_stats, attrs = self.fid_stats, self.attrs
        with ObCollection(ModsPath=dirs['mods'].s) as Current:
            modFile = Current.addMod(modInfo.getPath().stail,LoadMasters=False)
            Current.load()
            changed = []
            for record in modFile.SPEL:
                newStats = fid_stats.get(record.fid, None)
                if not newStats: continue
                if not ValidateList(newStats, modFile): continue
                oldStats = map(record.__getattribute__,attrs)
                if oldStats != newStats:
                    changed.append(oldStats[0]) #eid
                    map(record.__setattr__,attrs,newStats)
            #--Done
            if changed: modFile.save()
            return changed

    def readFromText(self,textPath):
        """Imports stats from specified text file."""
        detailed,aliases,spellTypeName_Number,levelTypeName_Number = \
            self.detailed,self.aliases,self.spellTypeName_Number,\
            self.levelTypeName_Number
        fid_stats = self.fid_stats
        with CsvReader(textPath) as ins:
            for fields in ins:
                if len(fields) < 8 or fields[2][:2] != u'0x': continue
                group,mmod,mobj,eid,full,cost,levelType,spellType = fields[:8]
                fields = fields[8:]
                group = _coerce(group, unicode)
                if group.lower() != u'spel': continue
                mmod = _coerce(mmod, unicode)
                mid = FormID(GPath(aliases.get(mmod,mmod)),
                             _coerce(mobj,int,16))
                eid = _coerce(eid, unicode, AllowNone=True)
                full = _coerce(full, unicode, AllowNone=True)
                cost = _coerce(cost, int)
                levelType = _coerce(levelType, unicode)
                levelType = levelTypeName_Number.get(levelType.lower(),
                                                     _coerce(levelType,
                                                             int) or 0)
                spellType = _coerce(spellType, unicode)
                spellType = spellTypeName_Number.get(spellType.lower(),
                                                     _coerce(spellType,
                                                             int) or 0)
                if not detailed or len(fields) < 7:
                    fid_stats[mid] = [eid,full,cost,levelType,spellType]
                    continue
                mc,ss,its,aeil,saa,daar,tewt = fields[:7]
                fields = fields[7:]
                mc = _coerce(mc, bool)
                ss = _coerce(ss, bool)
                its = _coerce(its, bool)
                aeil = _coerce(aeil, bool)
                saa = _coerce(saa, bool)
                daar = _coerce(daar, bool)
                tewt = _coerce(tewt, bool)
                effects = self.readEffects(fields, aliases, True)
                fid_stats[mid] = [eid,full,cost,levelType,spellType,mc,ss,its,
                                  aeil,saa,daar,tewt,effects]

    def writeToText(self,textPath):
        """Exports stats to specified text file."""
        detailed,fid_stats,spellTypeNumber_Name,levelTypeNumber_Name = \
            self.detailed,self.fid_stats,self.spellTypeNumber_Name,\
            self.levelTypeNumber_Name
        header = (_(u'Type'),_(u'Mod Name'),_(u'ObjectIndex'),_(u'Editor Id'),
                  _(u'Name'),_(u'Cost'),_(u'Level Type'),_(u'Spell Type'))
        rowFormat = u'"%s","%s","0x%06X","%s","%s","%d","%s","%s"'
        if detailed:
            header = header + (
                _(u'Manual Cost'),_(u'Start Spell'),_(u'Immune To Silence'),
                _(u'Area Effect Ignores LOS'),_(u'Script Always Applies'),
                _(u'Disallow Absorb and Reflect'),
                _(u'Touch Explodes Without Target'),
            ) + _UsesEffectsMixin.headers * 2 + (
                         _(u'Additional Effects (Same format)'),)
            rowFormat += u',"%s","%s","%s","%s","%s","%s","%s"'
        headFormat = u','.join([u'"%s"'] * len(header)) + u'\n'
        with textPath.open('w',encoding='utf-8-sig') as out:
            out.write(headFormat % header)
            for fid in sorted(fid_stats,key=lambda x:(fid_stats[x][0],x[0])):
                if detailed:
                    eid,name,cost,levelType,spellType,mc,ss,its,aeil,saa,\
                    daar,tewt,effects = fid_stats[fid]
                    levelType = levelTypeNumber_Name.get(levelType,levelType)
                    spellType = spellTypeNumber_Name.get(spellType,spellType)
                    output = rowFormat % (
                        u'SPEL',fid[0],fid[1],eid,name,cost,levelType,
                        spellType,mc,ss,its,aeil,saa,daar,tewt)
                    output += self.writeEffects(effects, True)
                else:
                    eid,name,cost,levelType,spellType = fid_stats[fid]
                    levelType = levelTypeNumber_Name.get(levelType,levelType)
                    spellType = spellTypeNumber_Name.get(spellType,spellType)
                    output = rowFormat % (
                        u'SPEL',fid[0],fid[1],eid,name,cost,levelType,
                        spellType)
                output += u'\n'
                out.write(output)

#------------------------------------------------------------------------------
class IngredientDetails(_UsesEffectsMixin):
    """Details on Ingredients, with functions for importing/exporting
    from/to mod/text file."""

    def __init__(self,types=None,aliases=None):
        self.fid_stats = {}
        self.aliases = aliases or {} #--For aliasing mod names

    def readFromMod(self,modInfo):
        """Reads stats from specified mod."""
        fid_stats = self.fid_stats
        loadFactory= LoadFactory(False,MreRecord.type_class['INGR'])
        modFile = ModFile(modInfo,loadFactory)
        modFile.load(True)
        modFile.convertToLongFids(['INGR'])
        for record in modFile.INGR.getActiveRecords():
            effects = []
            for effect in record.effects:
                effectlist = [effect.name,effect.magnitude,effect.area,
                              effect.duration,effect.recipient,
                              effect.actorValue]
                if effect.scriptEffect:
                    effectlist.append(
                        [effect.scriptEffect.script,effect.scriptEffect.school,
                         effect.scriptEffect.visual,
                         effect.scriptEffect.flags.hostile,
                         effect.scriptEffect.full])
                else: effectlist.append([])
                effects.append(effectlist)
            fid_stats[record.fid] = [record.eid,record.full,
                                     record.model.modPath,
                                     round(record.model.modb,6),
                                     record.iconPath,record.script,
                                     record.value,round(record.weight,6),
                                     effects]

    def writeToMod(self,modInfo):
        """Writes stats to specified mod."""
        fid_stats = self.fid_stats
        loadFactory = LoadFactory(True,MreRecord.type_class['INGR'])
        modFile = ModFile(modInfo,loadFactory)
        modFile.load(True)
        mapper = modFile.getLongMapper()
        shortMapper = modFile.getShortMapper()
        changed = [] #eids
        for record in modFile.INGR.getActiveRecords():
            newStats = fid_stats.get(mapper(record.fid), None)
            if not newStats: continue
            effects = []
            for effect in record.effects:
                effectlist = [effect.name,effect.magnitude,effect.area,
                              effect.duration,effect.recipient,
                              effect.actorValue]
                if effect.scriptEffect:
                    effectlist.append([mapper(effect.scriptEffect.script),
                                       effect.scriptEffect.school,
                                       effect.scriptEffect.visual,
                                       effect.scriptEffect.flags.hostile,
                                       effect.scriptEffect.full])
                else: effectlist.append([])
                effects.append(effectlist)
            oldStats = [record.eid,record.full,record.model.modPath,
                        round(record.model.modb,6),record.iconPath,
                        mapper(record.script),record.value,
                        round(record.weight,6),effects]
            if oldStats != newStats:
                changed.append(oldStats[0]) #eid
                record.eid,record.full,record.model.modPath,\
                record.model.modb,record.iconPath,script,record.value,\
                record.weight,effects = newStats
                record.script = shortMapper(script)
                record.effects = []
                for effect in effects:
                    neweffect = record.getDefault('effects')
                    neweffect.name,neweffect.magnitude,neweffect.area,\
                    neweffect.duration,neweffect.recipient,\
                    neweffect.actorValue,scripteffect = effect
                    if len(scripteffect):
                        scriptEffect = record.getDefault(
                            'effects.scriptEffect')
                        script,scriptEffect.school,scriptEffect.visual,\
                        scriptEffect.flags.hostile.hostile,scriptEffect.full\
                            = scripteffect
                        scriptEffect.script = shortMapper(script)
                        neweffect.scriptEffect = scriptEffect
                    record.effects.append(neweffect)
                record.setChanged()
        if changed: modFile.safeSave()
        return changed

    def readFromText(self,textPath):
        """Imports stats from specified text file."""
        fid_stats,aliases = self.fid_stats, self.aliases
        with CsvReader(textPath) as ins:
            for fields in ins:
                if len(fields) < 11 or fields[1][:2] != u'0x': continue
                mmod,mobj,eid,full,modPath,modb,iconPath,smod,sobj,value,\
                weight = fields[:11]
                mmod = _coerce(mmod, unicode)
                mid = (GPath(aliases.get(mmod,mmod)),_coerce(mobj,int,16))
                smod = _coerce(smod, unicode, AllowNone=True)
                if smod is None: sid = None
                else: sid = (
                    GPath(aliases.get(smod,smod)),_coerce(sobj,int,16))
                eid = _coerce(eid, unicode, AllowNone=True)
                full = _coerce(full, unicode, AllowNone=True)
                modPath = _coerce(modPath, unicode, AllowNone=True)
                modb = _coerce(modb, float)
                iconPath = _coerce(iconPath, unicode, AllowNone=True)
                value = _coerce(value, int)
                weight = _coerce(weight, float)
                effects = self.readEffects(fields[11:], aliases, False)
                fid_stats[mid] = [eid,full,modPath,modb,iconPath,sid,value,
                                  weight,effects]

    def writeToText(self,textPath):
        """Exports stats to specified text file."""
        fid_stats = self.fid_stats
        header = (_(u'Mod Name'),_(u'ObjectIndex'),_(u'Editor Id'),_(u'Name'),
                  _(u'Model Path'),_(u'Bound Radius'),_(u'Icon Path'),
                  _(u'Script Mod Name'),_(u'Script ObjectIndex'),_(u'Value'),
                  _(u'Weight'),) + _UsesEffectsMixin.headers * 2 + (
                     _(u'Additional Effects (Same format)'),)
        headFormat = u','.join([u'"%s"'] * len(header)) + u'\n'
        rowFormat = u'"%s","0x%06X","%s","%s","%s","%f","%s","%s","0x%06X",' \
                    u'"%d","%f"'
        altrowFormat = u'"%s","0x%06X","%s","%s","%s","%f","%s","%s","%s",' \
                       u'"%d","%f"'
        with textPath.open('w',encoding='utf-8-sig') as out:
            out.write(headFormat % header)
            for fid in sorted(fid_stats,key=lambda x:fid_stats[x][0].lower()):
                eid,name,modpath,modb,iconpath,scriptfid,value,weight,\
                effects = fid_stats[fid]
                scriptfid = scriptfid or (GPath(u'None'), None)
                try:
                    output = rowFormat % (
                        fid[0].s,fid[1],eid,name,modpath,modb,iconpath,
                        scriptfid[0].s,scriptfid[1],value,weight)
                except TypeError:
                    output = altrowFormat % (
                        fid[0].s,fid[1],eid,name,modpath,modb,iconpath,
                        scriptfid[0].s,scriptfid[1],value,weight)
                output += self.writeEffects(effects, False)
                output += u'\n'
                out.write(output)

class CBash_IngredientDetails(_UsesEffectsMixin):
    """Details on SigilStones, with functions for importing/exporting
    from/to mod/text file."""

    def __init__(self,types=None,aliases=None):
        self.fid_stats = {}
        self.aliases = aliases or {} #--For aliasing mod names

    def readFromMod(self,modInfo):
        """Reads stats from specified mod."""
        fid_stats = self.fid_stats
        with ObCollection(ModsPath=dirs['mods'].s) as Current:
            modFile = Current.addMod(modInfo.getPath().stail,Saveable=False,
                                     LoadMasters=False)
            Current.load()
            for record in modFile.INGR:
                fid_stats[record.fid] = [record.eid,record.full,record.modPath,
                                         record.modb,record.iconPath,
                                         record.script,record.value,
                                         record.weight,record.effects_list]

    def writeToMod(self,modInfo):
        """Writes stats to specified mod."""
        fid_stats = self.fid_stats
        changed = []
        with ObCollection(ModsPath=dirs['mods'].s) as Current:
            modFile = Current.addMod(modInfo.getPath().stail,LoadMasters=False)
            Current.load()
            fid_stats = FormID.FilterValidDict(fid_stats, modFile, True, False)
            for record in modFile.INGR:
                newStats = fid_stats.get(record.fid, None)
                if not newStats: continue
                if not ValidateList(newStats, modFile): continue
                oldStats = [record.eid,record.full,record.modPath,record.modb,
                            record.iconPath,record.script,record.value,
                            record.weight,record.effects_list]
                if oldStats != newStats:
                    changed.append(oldStats[0]) #eid
                    record.eid,record.full,record.modPath,record.modb,\
                    record.iconPath,record.script,record.value,\
                    record.weight,effects = newStats
                    record.effects_list = effects
            if changed: modFile.save()
            return changed

    def readFromText(self,textPath):
        """Imports stats from specified text file."""
        fid_stats,aliases = self.fid_stats, self.aliases
        with CsvReader(textPath) as ins:
            for fields in ins:
                if len(fields) < 11 or fields[1][:2] != u'0x': continue
                mmod,mobj,eid,full,modPath,modb,iconPath,smod,sobj,value,\
                weight = fields[:11]
                mmod = _coerce(mmod, unicode)
                mid = FormID(GPath(aliases.get(mmod,mmod)),
                             _coerce(mobj,int,16))
                smod = _coerce(smod, unicode, AllowNone=True)
                if smod is None: sid = FormID(None,None)
                else: sid = FormID(GPath(aliases.get(smod,smod)),
                                   _coerce(sobj,int,16))
                eid = _coerce(eid, unicode, AllowNone=True)
                full = _coerce(full, unicode, AllowNone=True)
                modPath = _coerce(modPath, unicode, AllowNone=True)
                modb = _coerce(modb, float)
                iconPath = _coerce(iconPath, unicode, AllowNone=True)
                value = _coerce(value, int)
                weight = _coerce(weight, float)
                effects = self.readEffects(fields[11:], aliases, True)
                fid_stats[mid] = [eid,full,modPath,modb,iconPath,sid,value,
                                  weight,effects]

    def writeToText(self,textPath):
        """Exports stats to specified text file."""
        fid_stats = self.fid_stats
        header = (_(u'Mod Name'),_(u'ObjectIndex'),_(u'Editor Id'),_(u'Name'),
                  _(u'Model Path'),_(u'Bound Radius'),_(u'Icon Path'),
                  _(u'Script Mod Name'),_(u'Script ObjectIndex'),_(u'Value'),
                  _(u'Weight'),) + _UsesEffectsMixin.headers * 2 + (
                     _(u'Additional Effects (Same format)'),)
        headFormat = u','.join([u'"%s"'] * len(header)) + u'\n'
        rowFormat = u'"%s","0x%06X","%s","%s","%s","%f","%s","%s","0x%06X",' \
                    u'"%d","%f"'
        altrowFormat = u'"%s","0x%06X","%s","%s","%s","%f","%s","%s","%s",' \
                       u'"%d","%f"'
        with textPath.open('w',encoding='utf-8-sig') as out:
            outWrite = out.write
            outWrite(headFormat % header)
            for fid in sorted(fid_stats,key = lambda x: fid_stats[x][0]):
                eid,name,modpath,modb,iconpath,scriptfid,value,weight,\
                effects = fid_stats[fid]
                scriptfid = scriptfid or (GPath(u'None'), None)
                try:
                    output = rowFormat % (
                    fid[0],fid[1],eid,name,modpath,modb,iconpath,scriptfid[0],
                    scriptfid[1],value,weight)
                except TypeError:
                    output = altrowFormat % (
                    fid[0],fid[1],eid,name,modpath,modb,iconpath,scriptfid[0],
                    scriptfid[1],value,weight)
                output += self.writeEffects(effects, True)
                output += u'\n'
                outWrite(output)

#------------------------------------------------------------------------------
# CBASH ONLY
#------------------------------------------------------------------------------
class CBash_MapMarkers:
    """Map marker references, with functions for importing/exporting from/to
    mod/text file."""

    def __init__(self,types=None,aliases=None):
        self.fid_markerdata = {}
        self.aliases = aliases or {}
        self.markerFid = FormID(GPath(u'Oblivion.esm'), 0x000010)
        self.attrs = ['eid','markerName','markerType','IsVisible',
                      'IsCanTravelTo','posX','posY','posZ','rotX','rotY',
                      'rotZ']
        self.markerTypeNumber_Name = {
            None : u'NONE',
            0 : u'NONE',
            1 : u'Camp',
            2 : u'Cave',
            3 : u'City',
            4 : u'Elven Ruin',
            5 : u'Fort Ruin',
            6 : u'Mine',
            7 : u'Landmark',
            8 : u'Tavern',
            9 : u'Settlement',
            10 : u'Daedric Shrine',
            11 : u'Oblivion Gate',
            12 : u'?',
            13 : u'Ayleid Well',
            14 : u'Wayshrine',
            15 : u'Magical Stone',
            16 : u'Spire',
            17 : u'Obelisk of Order',
            18 : u'House',
            19 : u'Player marker (flag)',
            20 : u'Player marker (Q flag)',
            21 : u'Player marker (i flag)',
            22 : u'Player marker (? flag)',
            23 : u'Harbor/dock',
            24 : u'Stable',
            25 : u'Castle',
            26 : u'Farm',
            27 : u'Chapel',
            28 : u'Merchant',
            29 : u'Ayleid Step (old Ayleid ruin icon)',}
        self.markerTypeName_Number = dict(
            [(y.lower(),x) for x,y in self.markerTypeNumber_Name.iteritems() if
             x is not None])

    def readFromMod(self,modInfo):
        """Imports type_id_name from specified mod."""
        fid_markerdata,markerFid,attrs = self.fid_markerdata,self.markerFid,\
                                         self.attrs
        with ObCollection(ModsPath=dirs['mods'].s) as Current:
            modFile = Current.addMod(modInfo.getPath().stail,Saveable=False,
                                     LoadMasters=False)
            Current.load()
            for record in modFile.REFRS:
                if record.base == markerFid:
                    fid_markerdata[record.fid] = [getattr(record,attr) for attr
                                                  in attrs]
                record.UnloadRecord()

    def writeToMod(self,modInfo):
        """Imports type_id_name to specified mod."""
        fid_markerdata,markerFid,attrs = self.fid_markerdata,self.markerFid,\
                                         self.attrs
        changed = []
        with ObCollection(ModsPath=dirs['mods'].s) as Current:
            modFile = Current.addMod(modInfo.getPath().stail,LoadMasters=False)
            Current.load()
            fid_markerdata = FormID.FilterValidDict(fid_markerdata,modFile,
                                                    True,False)
            fid_markerdata = FormID.FilterValidDict(fid_markerdata,modFile,
                                                    True,False)
            for record in modFile.REFRS:
                fid = record.fid
                if not fid in fid_markerdata or record.base != markerFid:
                    record.UnloadRecord()
                    continue
                oldValues = [getattr(record, attr) for attr in attrs]
                newValues = fid_markerdata[fid]
                if oldValues == newValues:
                    record.UnloadRecord()
                    continue
                changed.append(oldValues[0]) #eid
                for attr, value in zip(attrs, newValues):
                    setattr(record, attr, value)
            if changed: modFile.save()
            return changed

    def readFromText(self,textPath):
        """Imports type_id_name from specified text file."""
        fid_markerdata,aliases,markerTypeName_Number = self.fid_markerdata,\
                                        self.aliases,self.markerTypeName_Number
        with CsvReader(GPath(textPath)) as ins:
            for fields in ins:
                if len(fields) < 13 or fields[1][:2] != u'0x': continue
                mod,objectIndex,eid,markerName,_markerType,IsVisible,\
                IsCanTravelTo,posX,posY,posZ,rotX,rotY,rotZ = fields[:13]
                mod = GPath(_coerce(mod, unicode))
                longid = FormID(aliases.get(mod,mod),
                                _coerce(objectIndex,int,16))
                eid = _coerce(eid, unicode, AllowNone=True)
                markerName = _coerce(markerName, unicode, AllowNone=True)
                markerType = _coerce(_markerType, int)
                if markerType is None: #coercion failed
                    markerType = markerTypeName_Number.get(_markerType.lower(),
                                                           0)
                IsVisible = _coerce(IsVisible, bool)
                IsCanTravelTo = _coerce(IsCanTravelTo, bool)
                posX = _coerce(posX, float)
                posY = _coerce(posY, float)
                posZ = _coerce(posZ, float)
                rotX = _coerce(rotX, float)
                rotY = _coerce(rotY, float)
                rotZ = _coerce(rotZ, float)
                fid_markerdata[longid] = [eid,markerName,markerType,IsVisible,
                                          IsCanTravelTo,posX,posY,posZ,rotX,
                                          rotY,rotZ]

    def writeToText(self,textPath):
        """Exports markers to specified text file."""
        fid_markerdata,markerTypeNumber_Name = self.fid_markerdata,\
                                               self.markerTypeNumber_Name
        textPath = GPath(textPath)
        headFormat = u'"%s","%s","%s","%s","%s","%s","%s","%s","%s","%s",' \
                     u'"%s","%s","%s"\n'
        rowFormat = u'"%s","0x%06X","%s","%s","%s","%s","%s","%s","%s","%s",' \
                    u'"%s","%s","%s"\n'
        with textPath.open('w',encoding='utf-8-sig') as out:
            outWrite = out.write
            outWrite(headFormat % (
                _(u'Mod Name'),_(u'ObjectIndex'),_(u'Editor Id'),_(u'Name'),
                _(u'Type'),_(u'IsVisible'),_(u'IsCanTravelTo'),_(u'posX'),
                _(u'posY'),_(u'posZ'),_(u'rotX'),_(u'rotY'),_(u'rotZ')))
            longids = fid_markerdata.keys()
            longids.sort(key=lambda a: fid_markerdata[a][0])
            longids.sort(key=itemgetter(0))
            for longid in longids:
                eid,markerName,markerType,IsVisible,IsCanTravelTo,posX,posY,\
                posZ,rotX,rotY,rotZ = fid_markerdata[longid]
                markerType = markerTypeNumber_Name.get(markerType,markerType)
                outWrite(rowFormat % (
                    longid[0],longid[1],eid,markerName,markerType,IsVisible,
                    IsCanTravelTo,posX,posY,posZ,rotX,rotY,rotZ))

#------------------------------------------------------------------------------
class CBash_CellBlockInfo:
    """Map marker references, with functions for importing/exporting from/to
    mod/text file."""

    def __init__(self,types=None,aliases=None):
        self.celldata = {}
        self.aliases = aliases or {}

    def readFromMod(self,modInfo):
        """Imports type_id_name from specified mod."""
        celldata = self.celldata
        with ObCollection(ModsPath=dirs['mods'].s) as Current:
            modFile = Current.addMod(modInfo.getPath().stail,Saveable=False,
                                     LoadMasters=False)
            Current.load()
            for record in modFile.CELLS:
                celldata[record.eid] = record.bsb
                record.UnloadRecord()

    def writeToText(self,textPath):
        """Exports markers to specified text file."""
        celldata = self.celldata
        textPath = GPath(textPath)
        headFormat = u'"%s","%s","%s",\n'
        rowFormat  = u'"%s","%s","%s",\n'
        with textPath.open('w',encoding='utf-8-sig') as out:
            out.write(
                headFormat % (_(u'Editor Id'),_(u'Block'),_(u'Sub-Block')))
            eids = celldata.keys()
            eids.sort()
            for eid in eids:
                block, subblock = celldata[eid]
                out.write(rowFormat % (eid, block, subblock))

#------------------------------------------------------------------------------
# Mod Blocks, File ------------------------------------------------------------
#------------------------------------------------------------------------------
class MasterMap:
    """Serves as a map between two sets of masters."""
    def __init__(self,inMasters,outMasters):
        """Initiation."""
        map = {}
        outMastersIndex = outMasters.index
        for index,master in enumerate(inMasters):
            if master in outMasters:
                map[index] = outMastersIndex(master)
            else:
                map[index] = -1
        self.map = map

    def __call__(self,fid,default=-1):
        """Maps a fid from first set of masters to second. If no mapping
        is possible, then either returns default (if defined) or raises MasterMapError."""
        if not fid: return fid
        inIndex = int(fid >> 24)
        outIndex = self.map.get(inIndex,-2)
        if outIndex >= 0:
            return (long(outIndex) << 24 ) | (fid & 0xFFFFFFL)
        elif default != -1:
            return default
        else:
            raise MasterMapError(inIndex)

class MasterSet(set):
    """Set of master names."""

    def add(self,element):
        """Add an element it's not empty. Special handling for tuple."""
        if isinstance(element,tuple):
            set.add(self,element[0])
        elif element:
            set.add(self,element)

    def getOrdered(self):
        """Returns masters in proper load order."""
        return load_order.get_ordered(self)

class LoadFactory:
    """Factory for mod representation objects."""
    def __init__(self,keepAll,*recClasses):
        self.keepAll = keepAll
        self.recTypes = set()
        self.topTypes = set()
        self.type_class = {}
        self.cellType_class = {}
        addClass = self.addClass
        for recClass in recClasses:
            addClass(recClass)

    def addClass(self,recClass):
        """Adds specified class."""
        cellTypes = ('WRLD','ROAD','CELL','REFR','ACHR','ACRE','PGRD','LAND')
        if isinstance(recClass,basestring):
            recType = recClass
            recClass = MreRecord
        else:
            recType = recClass.classType
        #--Don't replace complex class with default (MreRecord) class
        if recType in self.type_class and recClass == MreRecord:
            return
        self.recTypes.add(recType)
        self.type_class[recType] = recClass
        #--Top type
        if recType in cellTypes:
            topAdd = self.topTypes.add
            topAdd('CELL')
            topAdd('WRLD')
            if self.keepAll:
                setterDefault = self.type_class.setdefault
                for type in cellTypes:
                    setterDefault(type,MreRecord)
        elif recType == 'INFO':
            self.topTypes.add('DIAL')
        else:
            self.topTypes.add(recType)

    def getRecClass(self,type):
        """Returns class for record type or None."""
        default = (self.keepAll and MreRecord) or None
        return self.type_class.get(type,default)

    def getCellTypeClass(self):
        """Returns type_class dictionary for cell objects."""
        if not self.cellType_class:
            types = ('REFR','ACHR','ACRE','PGRD','LAND','CELL','ROAD')
            getterRecClass = self.getRecClass
            self.cellType_class.update((x,getterRecClass(x)) for x in types)
        return self.cellType_class

    def getUnpackCellBlocks(self,topType):
        """Returns whether cell blocks should be unpacked or not. Only relevant
        if CELL and WRLD top types are expanded."""
        return (
            self.keepAll or
            (self.recTypes & {'REFR', 'ACHR', 'ACRE', 'PGRD', 'LAND'}) or
            (topType == 'WRLD' and 'LAND' in self.recTypes))

    def getTopClass(self, top_rec_type):
        """Return top block class for top block type, or None.
        :rtype: type[record_groups.MobBase]
        """
        if top_rec_type in self.topTypes:
            if   top_rec_type == 'DIAL': return MobDials
            elif top_rec_type == 'CELL': return MobICells
            elif top_rec_type == 'WRLD': return MobWorlds
            else: return MobObjects
        elif self.keepAll:
            return MobBase
        else:
            return None

class ModFile(object):
    """TES4 file representation.

    Will load only the top record types specified in its LoadFactory. Overrides
    __getattr__ to return its collection of records for a top record type.
    """
    def __init__(self, fileInfo,loadFactory=None):
        self.fileInfo = fileInfo
        self.loadFactory = loadFactory or LoadFactory(True)
        #--Variables to load
        self.tes4 = bush.game_mod.records.MreHeader(ModReader.recHeader())
        self.tes4.setChanged()
        self.strings = bolt.StringTable()
        self.tops = {} #--Top groups.
        self.topsSkipped = set() #--Types skipped
        self.longFids = False
        #--Cached data
        self.mgef_school = None
        self.mgef_name = None
        self.hostileEffects = None

    def __getattr__(self,topType):
        """Returns top block of specified topType, creating it, if necessary."""
        if topType in self.tops:
            return self.tops[topType]
        elif topType in RecordHeader.topTypes:
            topClass = self.loadFactory.getTopClass(topType)
            self.tops[topType] = topClass(ModReader.recHeader('GRUP',0,topType,0,0),self.loadFactory)
            self.tops[topType].setChanged()
            return self.tops[topType]
        elif topType == '__repr__':
            raise AttributeError
        else:
            raise ArgumentError(u'Invalid top group type: '+topType)

    def load(self, do_unpack=False, progress=None, loadStrings=True):
        """Load file."""
        progress = progress or bolt.Progress()
        progress.setFull(1.0)
        with ModReader(self.fileInfo.name,self.fileInfo.getPath().open('rb')) as ins:
            insRecHeader = ins.unpackRecHeader
            #--TES4 Header of the mod file
            header = insRecHeader()
            self.tes4 = bush.game_mod.records.MreHeader(header,ins,True)
            #--Strings
            self.strings.clear()
            if do_unpack and self.tes4.flags1[7] and loadStrings:
                stringsProgress = SubProgress(progress,0,0.1) # Use 10% of progress bar for strings
                lang = bosh.oblivionIni.get_ini_language()
                stringsPaths = self.fileInfo.getStringsPaths(lang)
                stringsProgress.setFull(max(len(stringsPaths),1))
                for i,path in enumerate(stringsPaths):
                    self.strings.loadFile(path,SubProgress(stringsProgress,i,i+1),lang)
                    stringsProgress(i)
                ins.setStringTable(self.strings)
                subProgress = SubProgress(progress,0.1,1.0)
            else:
                ins.setStringTable(None)
                subProgress = progress
            #--Raw data read
            subProgress.setFull(ins.size)
            insAtEnd = ins.atEnd
            insSeek = ins.seek
            insTell = ins.tell
            while not insAtEnd():
                #--Get record info and handle it
                header = insRecHeader()
                type = header.recType
                if type != 'GRUP' or header.groupType != 0:
                    raise ModError(self.fileInfo.name,u'Improperly grouped file.')
                label,size = header.label,header.size
                topClass = self.loadFactory.getTopClass(label)
                try:
                    if topClass:
                        self.tops[label] = topClass(header, self.loadFactory)
                        self.tops[label].load(ins, do_unpack and (topClass != MobBase))
                    else:
                        self.topsSkipped.add(label)
                        insSeek(size-header.__class__.rec_header_size,1,type + '.' + label)
                except:
                    print u'Error in',self.fileInfo.name.s
                    deprint(u' ',traceback=True)
                    break
                subProgress(insTell())
        #--Done Reading

    def load_unpack(self):
        """Unpacks blocks."""
        factoryTops = self.loadFactory.topTypes
        selfTops = self.tops
        for rec_type in RecordHeader.topTypes:
            if rec_type in selfTops and rec_type in factoryTops:
                selfTops[rec_type].load(None,True)

    def load_UI(self):
        """Convenience function. Loads, then unpacks, then indexes."""
        self.load()
        self.load_unpack()
        #self.load_index()

    def askSave(self,hasChanged=True):
        """CLI command. If hasSaved, will ask if user wants to save the file,
        and then save if the answer is yes. If hasSaved == False, then does nothing."""
        if not hasChanged: return
        fileName = self.fileInfo.name
        if re.match(ur'\s*[yY]',raw_input(u'\nSave changes to '+fileName.s+u' [y\n]?: '),flags=re.U):
            self.safeSave()
            print fileName.s,u'saved.'
        else:
            print fileName.s,u'not saved.'

    def safeSave(self):
        """Save data to file safely.  Works under UAC."""
        self.fileInfo.tempBackup()
        filePath = self.fileInfo.getPath()
        self.save(filePath.temp)
        if self.fileInfo.mtime is not None: # fileInfo created before the file
            filePath.temp.mtime = self.fileInfo.mtime
        # FIXME If saving a locked (by TES4Edit f.i.) bashed patch a bogus UAC
        # permissions dialog is displayed (should display file in use)
        env.shellMove(filePath.temp, filePath, parent=None) # silent=True just returns - no error!
        self.fileInfo.extras.clear()

    def save(self,outPath=None):
        """Save data to file.
        outPath -- Path of the output file to write to. Defaults to original file path."""
        if not self.loadFactory.keepAll: raise StateError(u"Insufficient data to write file.")
        outPath = outPath or self.fileInfo.getPath()
        with ModWriter(outPath.open('wb')) as out:
            #--Mod Record
            self.tes4.setChanged()
            self.tes4.numRecords = sum(block.getNumRecords() for block in self.tops.values())
            self.tes4.getSize()
            self.tes4.dump(out)
            #--Blocks
            selfTops = self.tops
            for rec_type in RecordHeader.topTypes:
                if rec_type in selfTops:
                    selfTops[rec_type].dump(out)

    def getLongMapper(self):
        """Returns a mapping function to map short fids to long fids."""
        masters = self.tes4.masters+[self.fileInfo.name]
        maxMaster = len(masters)-1
        def mapper(fid):
            if fid is None: return None
            if isinstance(fid,tuple): return fid
            mod,object = int(fid >> 24),int(fid & 0xFFFFFFL)
            return masters[min(mod,maxMaster)],object
        return mapper

    def getShortMapper(self):
        """Returns a mapping function to map long fids to short fids."""
        masters = self.tes4.masters + [self.fileInfo.name]
        indices = dict((name, index) for index, name in enumerate(masters))
        gLong = self.getLongMapper()
        def mapper(fid):
            if fid is None: return None
            if isinstance(fid, (long, int)):
                fid = gLong(fid)
            modName, object_id = fid
            long_id = long(object_id)
            mod = indices[modName] if long_id >= 0x800 else 0
            return (long(mod) << 24) | long_id
        return mapper

    def convertToLongFids(self,types=None):
        """Convert fids to long format (modname,objectindex).
        :type types: list[str] | tuple[str] | set[str]
        """
        mapper = self.getLongMapper()
        if types is None: types = self.tops.keys()
        else: assert isinstance(types, (list, tuple, set))
        selfTops = self.tops
        for type in types:
            if type in selfTops:
                selfTops[type].convertFids(mapper,True)
        #--Done
        self.longFids = True

    def convertToShortFids(self):
        """Convert fids to short (numeric) format."""
        mapper = self.getShortMapper()
        selfTops = self.tops
        for type in selfTops:
            selfTops[type].convertFids(mapper,False)
        #--Done
        self.longFids = False

    def getMastersUsed(self):
        """Updates set of master names according to masters actually used."""
        if not self.longFids: raise StateError(u"ModFile fids not in long form.")
        for fname in bush.game.masterFiles:
            if dirs['mods'].join(fname).exists():
                masters = MasterSet([GPath(fname)])
                break
        for block in self.tops.values():
            block.updateMasters(masters)
        return masters.getOrdered()

    def getMgefSchool(self, _reload=False): # _reload param never used
        """Return a dictionary mapping magic effect code to magic effect school.
        This is intended for use with the patch file when it records for all magic effects.
        If magic effects are not available, it will revert to bush.py version."""
        if self.mgef_school and not _reload:
            return self.mgef_school
        mgef_school = self.mgef_school = brec.mgef_school.copy()
        if 'MGEF' in self.tops:
            for record in self.MGEF.getActiveRecords():
                if isinstance(record,MreRecord.type_class['MGEF']):
                    if bush.game.fsName == u'Oblivion':
                        mgef_school[record.eid] = record.school
                    else:
                        mgef_school[record.eid] = record.magicSkill
        return mgef_school

    def getMgefHostiles(self, _reload=False): # _reload param never used
        """Return a set of hostile magic effect codes.
        This is intended for use with the patch file when it records for all magic effects.
        If magic effects are not available, it will revert to bush.py version."""
        if self.hostileEffects and not _reload:
            return self.hostileEffects
        hostileEffects = self.hostileEffects = brec.hostileEffects.copy()
        if 'MGEF' in self.tops:
            hostile = set()
            nonhostile = set()
            for record in self.MGEF.getActiveRecords():
                if isinstance(record,MreRecord.type_class['MGEF']):
                    if record.flags.hostile:
                        hostile.add(record.eid)
                        hostile.add(cast(record.eid, POINTER(c_ulong)).contents.value)
                    else:
                        nonhostile.add(record.eid)
                        nonhostile.add(cast(record.eid, POINTER(c_ulong)).contents.value)
            hostileEffects = (hostileEffects - nonhostile) | hostile
        return hostileEffects

    def getMgefName(self, _reload=False): # _reload param never used
        """Return a dictionary mapping magic effect code to magic effect name.
        This is intended for use with the patch file when it records for all magic effects.
        If magic effects are not available, it will revert to bush.py version."""
        if self.mgef_name and not _reload:
            return self.mgef_name
        mgef_name = self.mgef_name = brec.mgef_name.copy()
        if 'MGEF' in self.tops:
            for record in self.MGEF.getActiveRecords():
                if isinstance(record,MreRecord.type_class['MGEF']):
                    mgef_name[record.eid] = record.full
        return mgef_name
