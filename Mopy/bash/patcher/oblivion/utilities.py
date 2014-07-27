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
#  Wrye Bash copyright (C) 2005-2009 Wrye, 2010-2014 Wrye Bash Team
#  https://github.com/wrye-bash
#
# =============================================================================

"""This module contains the utility classes used by the oblivion patchers,
 originally in bosh.py. It should be further split into a package and the
 classes unified under Abstract Base classes (see
 https://github.com/wrye-bash/wrye-bash/issues/1)."""

import re

from bash import bolt
from bash.bolt import GPath
from bash.bosh import LoadFactory, ModFile, dirs
from bash.brec import MreRecord, MelObject, _coerce
from bash.cint import ObCollection, FormID, aggregateTypes, validTypes
from operator import attrgetter

class ActorFactions:
    """Factions for npcs and creatures with functions for
    importing/exporting from/to mod/text file."""

    def __init__(self,aliases=None):
        """Initialize."""
        self.types = tuple([MreRecord.type_class[x] for x in ('CREA','NPC_')])
        self.type_id_factions = {'CREA':{},'NPC_':{}} #--factions =
        # type_id_factions[type][longid]
        self.id_eid = {}
        self.aliases = aliases or {}
        self.gotFactions = set()

    def readFactionEids(self,modInfo):
        """Extracts faction editor ids from modInfo and its masters."""
        loadFactory = LoadFactory(False,MreRecord.type_class['FACT'])
        from bash.bosh import modInfos
        for modName in (modInfo.header.masters + [modInfo.name]):
            if modName in self.gotFactions: continue
            modFile = ModFile(modInfos[modName],loadFactory)
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
        changed = {'CREA':0,'NPC_':0}
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
        type_id_factions,id_eid = self.type_id_factions,self.id_eid
        aliases = self.aliases
        with bolt.CsvReader(textPath) as ins:
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
        """Initialize."""
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
            importFile = Current.addMod(modInfo.getPath().stail, Saveable=False)
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
        group_fid_factions,fid_eid = self.group_fid_factions,self.fid_eid
        with ObCollection(ModsPath=dirs['mods'].s) as Current:
            modFile = Current.addMod(modInfo.getPath().stail,LoadMasters=False)
            Current.load()
            changed = {'CREA':0,'NPC_':0}
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
        group_fid_factions,fid_eid = self.group_fid_factions, self.fid_eid
        aliases = self.aliases
        with bolt.CsvReader(textPath) as ins:
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
        """Initialize."""
        self.mod_id_levels = {} #--levels = mod_id_levels[mod][longid]
        self.aliases = aliases or {}
        self.gotLevels = set()

    def readFromMod(self,modInfo):
        """Imports actor level data from the specified mod and its masters."""
        mod_id_levels, gotLevels = self.mod_id_levels, self.gotLevels
        loadFactory = LoadFactory(False,MreRecord.type_class['NPC_'])
        from bash.bosh import modInfos
        for modName in (modInfo.header.masters + [modInfo.name]):
            if modName in gotLevels: continue
            modFile = ModFile(modInfos[modName],loadFactory)
            modFile.load(True)
            mapper = modFile.getLongMapper()
            for record in modFile.NPC_.getActiveRecords():
                id_levels = mod_id_levels.setdefault(modName,{})
                id_levels[mapper(record.fid)] = (
                    record.eid,record.flags.pcLevelOffset and 1 or 0,
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
        with bolt.CsvReader(textPath) as ins:
            for fields in ins:
                if fields[0][:2] == u'0x': #old format
                    fid,eid,offset,calcMin,calcMax = fields[:5]
                    source = GPath(u'Unknown')
                    fidObject = _coerce(fid[4:], int, 16)
                    fid = (GPath(u'Oblivion.esm'), fidObject)
                    eid = _coerce(eid, unicode)
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
            obId_levels = mod_id_levels[GPath(u'Oblivion.esm')]
            for mod in sorted(mod_id_levels):
                if mod.s.lower() == u'oblivion.esm': continue
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
        """Initialize."""
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
        with bolt.CsvReader(textPath) as ins:
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
        """Initialize."""
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
                header = u'\r\n\r\n; %s %s\r\n' % (
                    script.eid,u'-' * (77 - len(script.eid)))
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
        with bolt.CsvReader(textPath) as ins:
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
        """Initialize."""
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
        with bolt.CsvReader(textPath) as ins:
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
        """Initialize."""
        self.id_relations = {} #--(otherLongid,otherDisp) = id_relation[longid]
        self.id_eid = {} #--For all factions.
        self.aliases = aliases or {}
        self.gotFactions = set()

    def readFactionEids(self,modInfo):
        """Extracts faction editor ids from modInfo and its masters."""
        loadFactory = LoadFactory(False,MreRecord.type_class['FACT'])
        from bash.bosh import modInfos
        for modName in (modInfo.header.masters + [modInfo.name]):
            if modName in self.gotFactions: continue
            modFile = ModFile(modInfos[modName],loadFactory)
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
            if relations == None:
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
        id_relations,id_eid = self.id_relations, self.id_eid
        aliases = self.aliases
        with bolt.CsvReader(textPath) as ins:
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
        id_relations,id_eid = self.id_relations, self.id_eid
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
        """Initialize."""
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
        fid_faction_mod,fid_eid = self.fid_faction_mod, self.fid_eid
        aliases = self.aliases
        with bolt.CsvReader(textPath) as ins:
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
        fid_faction_mod,fid_eid = self.fid_faction_mod, self.fid_eid

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
