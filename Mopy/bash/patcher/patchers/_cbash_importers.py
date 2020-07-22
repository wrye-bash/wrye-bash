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
#  Wrye Bash copyright (C) 2005-2009 Wrye, 2010-2020 Wrye Bash Team
#  https://github.com/wrye-bash
#
# =============================================================================
"""Temp module to house CBash importers until CBash is dropped entirely."""
from collections import defaultdict, Counter
# Internal
from ._shared import _AImportInventory, _ANamesPatcher, _ANpcFacePatcher, \
    _ASpellsPatcher, _AStatsPatcher
from .base import CBash_ImportPatcher
from ... import bush, load_order
from ...bolt import GPath, MemorySet
from ...cint import ValidateDict, ValidateList, FormID, validTypes
from ...parsers import CBash_ActorFactions, CBash_FactionRelations, \
    CBash_FullNames, CBash_ItemStats, CBash_SpellRecords

class _RecTypeModLogging(CBash_ImportPatcher):
    """Import patchers that log type -> [mod-> count]"""
    listSrcs = True # whether or not to list sources
    logModRecs = u'* ' + _(u'Modified %(type)s Records: %(count)d')
    logMsg = u'\n=== ' + _(u'Modified Records')

    def __init__(self, p_name, p_file, p_sources):
        super(_RecTypeModLogging, self).__init__(p_name, p_file, p_sources)
        self.mod_count = defaultdict(Counter)
        self.fid_attr_value = defaultdict(dict) # used in some

    def _clog(self, log):
        """Used in: CBash_SoundPatcher, CBash_ImportScripts,
        CBash_ActorImporter, CBash_GraphicsPatcher. Adding
        AImportPatcher.srcsHeader attribute absorbed CBash_NamesPatcher and
        CBash_StatsPatcher. Adding logModRecs, listSrcs class variables
        absorbs CBash_ImportFactions and CBash_ImportInventory.
        """
        # TODO(ut): remove logModRecs - not yet though - adds noise to the
        # patch comparisons
        mod_count = self.mod_count
        if self.__class__.listSrcs:
            self._srcMods(log)
            log(self.__class__.logMsg)
        for group_sig in sorted(mod_count.keys()):
            log(self.__class__.logModRecs % {'type': u'%s ' % group_sig,
                              'count': sum(mod_count[group_sig].values())})
            for srcMod in load_order.get_ordered(mod_count[group_sig].keys()):
                log(u'  * %s: %d' % (srcMod.s, mod_count[group_sig][srcMod]))
        self.mod_count = defaultdict(Counter)

    def scan(self,modFile,record,bashTags):
        """Records information needed to apply the patch."""
        attr_value = record.ConflictDetails(self.class_attrs[record._Type])
        if not attr_value: return
        if not ValidateDict(attr_value, self.patchFile):
            self.patchFile.patcher_mod_skipcount[self._patcher_name][
                modFile.GName] += 1
            return
        self.fid_attr_value[record.fid].update(attr_value)

# Patchers: 20 ----------------------------------------------------------------
class CBash_CellImporter(CBash_ImportPatcher):
    logMsg = u'* ' + _(u'Cells/Worlds Patched') + u': %d'
    _read_write_records = ('CELLS',)
    tag_attrs = {
        u'C.Climate': ('climate', 'IsBehaveLikeExterior'),
        u'C.Music': ('musicType',),
        u'C.Name': ('full',),
        u'C.Owner': ('owner', 'rank', 'globalVariable', 'IsPublicPlace'),
        u'C.Water': ('water', 'waterHeight', 'IsHasWater'),
        u'C.Light': (
            'ambientRed', 'ambientGreen', 'ambientBlue', 'directionalRed',
            'directionalGreen', 'directionalBlue', 'fogRed', 'fogGreen',
            'fogBlue', 'fogNear', 'fogFar', 'directionalXY', 'directionalZ',
            'directionalFade', 'fogClip'),
        u'C.RecordFlags': ('flags1',) # Yes seems funky but thats the way it is
    }

    def __init__(self, p_name, p_file, p_sources):
        super(CBash_CellImporter, self).__init__(p_name, p_file, p_sources)
        self.fid_attr_value = defaultdict(dict)

    def scan(self,modFile,record,bashTags):
        """Records information needed to apply the patch."""
        for bashKey in bashTags & self.autoKey:
            attr_value = record.ConflictDetails(self.tag_attrs[bashKey])
            if not ValidateDict(attr_value, self.patchFile):
                self.patchFile.patcher_mod_skipcount[self._patcher_name][
                    modFile.GName] += 1
                continue
            self.fid_attr_value[record.fid].update(attr_value)

    def apply(self,modFile,record,bashTags):
        """Edits patch file as desired."""
        self.scan_more(modFile,record,bashTags)
        recordId = record.fid
        prev_attr_value = self.fid_attr_value.get(recordId,None)
        if prev_attr_value:
            cur_attr_value = dict(
                (attr, getattr(record, attr)) for attr in prev_attr_value)
            if cur_attr_value != prev_attr_value:
                override = record.CopyAsOverride(self.patchFile)
                if override:
                    for attr, value in prev_attr_value.iteritems():
                        setattr(override,attr,value)
                    self.mod_count[modFile.GName] += 1
                    record.UnloadRecord()
                    record._RecordID = override._RecordID

#------------------------------------------------------------------------------
class CBash_GraphicsPatcher(_RecTypeModLogging):
    _read_write_records = (
        'BSGN', 'LSCR', 'CLAS', 'LTEX', 'REGN', 'ACTI', 'DOOR', 'FLOR', 'FURN',
        'GRAS', 'STAT', 'ALCH', 'AMMO', 'APPA', 'BOOK', 'INGR', 'KEYM', 'LIGH',
        'MISC', 'SGST', 'SLGM', 'WEAP', 'TREE', 'ARMO', 'CLOT', 'CREA', 'MGEF',
        'EFSH')

    def __init__(self, p_name, p_file, p_sources):
        super(CBash_GraphicsPatcher, self).__init__(p_name, p_file, p_sources)
        model = ('modPath','modb','modt_p')
        icon = ('iconPath',)
        class_attrs = self.class_attrs = dict.fromkeys(
            ['BSGN', 'LSCR', 'CLAS', 'LTEX', 'REGN'], icon)
        class_attrs.update(dict.fromkeys(
            ['ACTI', 'DOOR', 'FLOR', 'FURN', 'GRAS', 'STAT'], model))
        class_attrs.update(dict.fromkeys(
            ['ALCH', 'AMMO', 'APPA', 'BOOK', 'INGR', 'KEYM', 'LIGH', 'MISC',
             'SGST', 'SLGM', 'WEAP', 'TREE'], icon + model))
        class_attrs['CLOT'] = class_attrs['ARMO'] = (
            'maleBody_list', 'maleWorld_list', 'maleIconPath',
            'femaleBody_list', 'femaleWorld_list', 'femaleIconPath', 'flags')
        class_attrs['CREA'] = ('bodyParts', 'nift_p')
        class_attrs['MGEF'] = icon + model + ('effectShader',
                                              'enchantEffect','light')
        class_attrs['EFSH'] = ('fillTexturePath','particleTexturePath','flags','memSBlend','memBlendOp',
                               'memZFunc','fillRed','fillGreen','fillBlue','fillAIn','fillAFull',
                               'fillAOut','fillAPRatio','fillAAmp','fillAFreq','fillAnimSpdU',
                               'fillAnimSpdV','edgeOff','edgeRed','edgeGreen','edgeBlue','edgeAIn',
                               'edgeAFull','edgeAOut','edgeAPRatio','edgeAAmp','edgeAFreq',
                               'fillAFRatio','edgeAFRatio','memDBlend','partSBlend','partBlendOp',
                               'partZFunc','partDBlend','partBUp','partBFull','partBDown',
                               'partBFRatio','partBPRatio','partLTime','partLDelta','partNSpd',
                               'partNAcc','partVel1','partVel2','partVel3','partAcc1','partAcc2',
                               'partAcc3','partKey1','partKey2','partKey1Time','partKey2Time',
                               'key1Red','key1Green','key1Blue','key2Red','key2Green','key2Blue',
                               'key3Red','key3Green','key3Blue','key1A','key2A','key3A',
                               'key1Time','key2Time','key3Time')

    def apply(self,modFile,record,bashTags):
        """Edits patch file as desired."""
        self.scan_more(modFile,record,bashTags)
        prev_attr_value = self.fid_attr_value.get(record.fid,None)
        if prev_attr_value:
            cur_attr_value = dict(
                (attr, getattr(record, attr)) for attr in prev_attr_value)
            if cur_attr_value != prev_attr_value:
                override = record.CopyAsOverride(self.patchFile)
                if override:
                    for attr, value in prev_attr_value.iteritems():
                        setattr(override,attr,value)
                    self.mod_count[record._Type][modFile.GName] += 1
                    record.UnloadRecord()
                    record._RecordID = override._RecordID

#------------------------------------------------------------------------------
class CBash_ActorImporter(_RecTypeModLogging):
    _read_write_records = ('CREA', 'NPC_')
    class_tag_attrs = {
      'NPC_': {
        u'Actors.AIData': ('aggression', 'confidence', 'energyLevel',
            'responsibility', 'services', 'trainSkill', 'trainLevel'),
        u'Actors.Stats': ('armorer', 'athletics', 'blade', 'block', 'blunt',
            'h2h', 'heavyArmor', 'alchemy', 'alteration', 'conjuration',
            'destruction', 'illusion', 'mysticism', 'restoration',
            'acrobatics', 'lightArmor', 'marksman', 'mercantile', 'security',
            'sneak', 'speechcraft', 'health', 'strength', 'intelligence',
            'willpower', 'agility', 'speed', 'endurance', 'personality',
            'luck',),
        u'Actors.ACBS': (('baseSpell', 'fatigue', 'level', 'calcMin',
                          'calcMax', 'IsPCLevelOffset', 'IsAutoCalc',),
            'barterGold', 'IsFemale', 'IsEssential', 'IsRespawn',
            'IsNoLowLevel', 'IsNoRumors', 'IsSummonable', 'IsNoPersuasion',
            'IsCanCorpseCheck',),
        u'NPC.Class': ('iclass',),
        u'NPC.Race': ('race',),
        u'Actors.CombatStyle': ('combatStyle',),
        u'Creatures.Blood': (),
        u'Creatures.Type': (),
        u'Actors.Skeleton': ('modPath', 'modb', 'modt_p'),
      },
      'CREA': {
        u'Actors.AIData': (
            'aggression', 'confidence', 'energyLevel', 'responsibility',
            'services', 'trainSkill', 'trainLevel'),
            u'Actors.Stats': (
            'combat', 'magic', 'stealth', 'soulType', 'health', 'attackDamage',
            'strength', 'intelligence', 'willpower', 'agility', 'speed',
            'endurance', 'personality', 'luck'),
            u'Actors.ACBS': (('baseSpell', 'fatigue', 'level', 'calcMin',
                              'calcMax', 'IsPCLevelOffset',),
            'barterGold', 'IsBiped', 'IsEssential', 'IsWeaponAndShield',
            'IsRespawn', 'IsSwims', 'IsFlies', 'IsWalks', 'IsNoLowLevel',
            'IsNoBloodSpray', 'IsNoBloodDecal', 'IsNoHead', 'IsNoRightArm',
            'IsNoLeftArm', 'IsNoCombatInWater', 'IsNoShadow',
            'IsNoCorpseCheck',),
        u'NPC.Class': (),
        u'NPC.Race': (),
        u'Actors.CombatStyle': ('combatStyle',),
        u'Creatures.Blood': ('bloodSprayPath', 'bloodDecalPath'),
        u'Creatures.Type': ('creatureType',),
        u'Actors.Skeleton': ('modPath', 'modb', 'modt_p',),
      }
    }

    def scan(self,modFile,record,bashTags):
        """Records information needed to apply the patch."""
        if modFile.GName == record.fid[0]: return
        for bashKey in bashTags & self.autoKey:
            attrs = self.class_tag_attrs[record._Type].get(bashKey, None)
            if attrs:
                attr_value = record.ConflictDetails(attrs)
                if not attr_value: continue
                if not ValidateDict(attr_value, self.patchFile):
                    self.patchFile.patcher_mod_skipcount[self._patcher_name][
                        modFile.GName] += 1
                    continue
                self.fid_attr_value[record.fid].update(attr_value)

    def apply(self,modFile,record,bashTags):
        """Edits patch file as desired."""
        self.scan_more(modFile,record,bashTags)
        recordId = record.fid
        prev_attr_value = self.fid_attr_value.get(recordId,None)
        if prev_attr_value:
            cur_attr_value = dict((attr,getattr(record,attr)) for attr in prev_attr_value)
            if cur_attr_value != prev_attr_value:
                override = record.CopyAsOverride(self.patchFile)
                if override:
                    for attr, value in prev_attr_value.iteritems():
                        setattr(override,attr,value)
                    self.mod_count[record._Type][modFile.GName] += 1
                    record.UnloadRecord()
                    record._RecordID = override._RecordID

#------------------------------------------------------------------------------
class CBash_KFFZPatcher(CBash_ImportPatcher):
    logMsg = u'* ' + _(u'Imported Animations') + u': %d'
    _read_write_records = ('CREA', 'NPC_')

    def __init__(self, p_name, p_file, p_sources):
        super(CBash_KFFZPatcher, self).__init__(p_name, p_file, p_sources)
        self.id_animations = defaultdict(list)

    def scan(self,modFile,record,bashTags):
        """Records information needed to apply the patch."""
        animations = self.id_animations[record.fid]
        animations.extend(
            [anim for anim in record.animations if anim not in animations])

    def apply(self,modFile,record,bashTags):
        """Edits patch file as desired."""
        self.scan_more(modFile,record,bashTags)
        recordId = record.fid
        if recordId in self.id_animations and record.animations != \
                self.id_animations[recordId]:
            override = record.CopyAsOverride(self.patchFile)
            if override:
                override.animations = self.id_animations[recordId]
                self.mod_count[modFile.GName] += 1
                record.UnloadRecord()
                record._RecordID = override._RecordID

#------------------------------------------------------------------------------
class CBash_NPCAIPackagePatcher(CBash_ImportPatcher):
    scanRequiresChecked = False
    logMsg = u'* ' + _(u'AI Package Lists Changed') + u': %d'
    _read_write_records = ('CREA', 'NPC_')

    def __init__(self, p_name, p_file, p_sources):
        super(CBash_NPCAIPackagePatcher, self).__init__(p_name, p_file,
                                                        p_sources)
        self.previousPackages = {}
        self.mergedPackageList = {}

    def scan(self,modFile,record,bashTags):
        """Records information needed to apply the patch."""
        aiPackages = record.aiPackages
        if not ValidateList(aiPackages, self.patchFile):
            self.patchFile.patcher_mod_skipcount[self._patcher_name][
                modFile.GName] += 1
            return

        recordId = record.fid
        newPackages = MemorySet(aiPackages)
        self.previousPackages.setdefault(recordId, {})[
            modFile.GName] = newPackages

        if modFile.GName in self.srcs:
            masterPackages = self.previousPackages[recordId].get(recordId[0],
                                                                 None)
            # can't just do "not masterPackages ^ newPackages" since the
            # order may have changed
            if masterPackages is not None and masterPackages == newPackages:
                return
            mergedPackages = self.mergedPackageList.setdefault(recordId,
                                                               newPackages)
            if newPackages == mergedPackages: return  # same as the current
            # list, just skip.
            for master in reversed(modFile.TES4.masters):
                masterPath = GPath(master)
                masterPackages = self.previousPackages[recordId].get(
                    masterPath, None)
                if masterPackages is None: continue

                # Get differences from master
                added = newPackages - masterPackages
                sameButReordered = masterPackages & newPackages
                prevDeleted = MemorySet(mergedPackages.discarded)
                newDeleted = masterPackages - newPackages

                # Merge those changes into mergedPackages
                mergedPackages |= newPackages
                if u'Actors.AIPackagesForceAdd' not in bashTags:
                    prevDeleted -= newPackages
                prevDeleted |= newDeleted
                mergedPackages -= prevDeleted
                self.mergedPackageList[recordId] = mergedPackages
                break

    def apply(self,modFile,record,bashTags):
        """Edits patch file as desired."""
        self.scan_more(modFile,record,bashTags)
        recordId = record.fid
        if recordId in self.mergedPackageList:
            mergedPackages = list(self.mergedPackageList[recordId])
            if record.aiPackages != mergedPackages:
                override = record.CopyAsOverride(self.patchFile)
                if override:
                    try:
                        override.aiPackages = mergedPackages
                    except:
                        newMergedPackages = []
                        for pkg in mergedPackages:
                            if not pkg[0] is None: newMergedPackages.append(
                                pkg)
                        override.aiPackages = newMergedPackages
                    self.mod_count[modFile.GName] += 1
                    record.UnloadRecord()
                    record._RecordID = override._RecordID

#------------------------------------------------------------------------------
class CBash_DeathItemPatcher(CBash_ImportPatcher):
    logMsg = u'* ' + _(u'Imported Death Items') + u': %d'
    _read_write_records = ('CREA', 'NPC_')

    def __init__(self, p_name, p_file, p_sources):
        super(CBash_DeathItemPatcher, self).__init__(p_name, p_file, p_sources)
        self.id_deathItem = {}

    def scan(self,modFile,record,bashTags):
        """Records information needed to apply the patch."""
        deathitem = record.ConflictDetails(('deathItem',))
        if deathitem:
            if deathitem['deathItem'].ValidateFormID(self.patchFile):
                self.id_deathItem[record.fid] = deathitem['deathItem']
            else:
                # Ignore the record. Another option would be to just ignore
                # the invalid formIDs
                self.patchFile.patcher_mod_skipcount[self._patcher_name][
                    modFile.GName] += 1

    def apply(self,modFile,record,bashTags):
        """Edits patch file as desired."""
        self.scan_more(modFile,record,bashTags)
        recordId = record.fid
        if recordId in self.id_deathItem and record.deathItem != \
                self.id_deathItem[recordId]:
            override = record.CopyAsOverride(self.patchFile)
            if override:
                override.deathItem = self.id_deathItem[recordId]
                self.mod_count[modFile.GName] += 1
                record.UnloadRecord()
                record._RecordID = override._RecordID

    def _clog(self,log): # type 2
        self._srcMods(log)
        super(CBash_DeathItemPatcher, self)._clog(log)

#------------------------------------------------------------------------------
class CBash_ImportFactions(_RecTypeModLogging):
    listSrcs = False
    logModRecs = u'* ' + _(u'Refactioned %(type)s Records: %(count)d')
    _read_write_records = ('CREA', 'NPC_')

    def __init__(self, p_name, p_file, p_sources):
        super(CBash_ImportFactions, self).__init__(p_name, p_file, p_sources)
        self.id_factions = {}
        self.csvId_factions = {}

    def initData(self, progress):
        if not self.isActive: return
        super(CBash_ImportFactions, self).initData(progress)
        actorFactions = self._parse_texts(CBash_ActorFactions, progress)
        #--Finish
        csvId_factions = self.csvId_factions
        for group, aFid_factions in \
                actorFactions.group_fid_factions.iteritems():
            if group not in ('CREA','NPC_'): continue
            for fid,factions in aFid_factions.iteritems():
                csvId_factions[fid] = factions

    def scan(self,modFile,record,bashTags):
        """Records information needed to apply the patch."""
        if modFile.GName == record.fid[0]: return
        factions = record.ConflictDetails(('factions_list',))
        if factions:
            masterRecord = self.patchFile.Current.LookupRecords(record.fid)[-1]
            masterFactions = masterRecord.factions_list
            masterDict = dict((x[0],x[1]) for x in masterFactions)
            # Initialize the factions list with what's in the master record
            self.id_factions.setdefault(record.fid, masterDict)
            # Only add/remove records if different than the master record
            thisFactions = factions['factions_list']
            masterFids = set([x[0] for x in masterFactions])
            thisFids = set([x[0] for x in thisFactions])
            removedFids = masterFids - thisFids
            addedFids = thisFids - masterFids
            # Add new factions
            self.id_factions[record.fid].update(
                dict((x[0], x[1]) for x in thisFactions if x[0] in addedFids))
            # Remove deleted factions
            for fid in removedFids:
                self.id_factions[record.fid].pop(fid,None)

    def apply(self,modFile,record,bashTags):
        """Edits patch file as desired."""
        self.scan_more(modFile,record,bashTags)
        fid = record.fid
        if fid in self.csvId_factions:
            newFactions = set(
                [(faction, rank) for faction, rank in self.csvId_factions[fid]
                 if faction.ValidateFormID(self.patchFile)])
        elif fid in self.id_factions:
            newFactions = set([(faction, rank) for faction, rank in
                               self.id_factions[fid].iteritems() if
                               faction.ValidateFormID(self.patchFile)])
        else:
            return
        curFactions = set(
            [(faction[0], faction[1]) for faction in record.factions_list if
             faction[0].ValidateFormID(self.patchFile)])
        changed = newFactions - curFactions
        removed = curFactions - newFactions
        if changed or removed:
            override = record.CopyAsOverride(self.patchFile)
            if override:
                for faction,rank in changed:
                    for entry in override.factions:
                        if entry.faction == faction:
                            entry.rank = rank
                            break
                    else:
                        entry = override.create_faction()
                        entry.faction = faction
                        entry.rank = rank
                override.factions_list = [(faction, rank) for faction, rank in
                                          override.factions_list if
                                          (faction, rank) not in removed]
                self.mod_count[record._Type][modFile.GName] += 1
                record.UnloadRecord()
                record._RecordID = override._RecordID

#------------------------------------------------------------------------------
class CBash_ImportRelations(CBash_ImportPatcher):
    logMsg = u'* ' + _(u'Re-Relationed Records') + u': %d'
    _read_write_records = ('FACT',)

    def __init__(self, p_name, p_file, p_sources):
        super(CBash_ImportRelations, self).__init__(p_name, p_file, p_sources)
        self.fid_faction_mod = {}
        self.csvFid_faction_mod = {}

    def initData(self, progress):
        if not self.isActive: return
        super(CBash_ImportRelations, self).initData(progress)
        factionRelations = self._parse_texts(CBash_FactionRelations, progress)
        #--Finish
        self.csvFid_faction_mod.update(factionRelations.fid_faction_mod)

    def scan(self,modFile,record,bashTags):
        """Records information needed to apply the patch."""
        relations = record.ConflictDetails(('relations_list',))
        if relations:
            self.fid_faction_mod.setdefault(record.fid, {}).update(
                relations['relations_list'])

    def apply(self,modFile,record,bashTags):
        """Edits patch file as desired."""
        self.scan_more(modFile,record,bashTags)
        fid = record.fid
        if fid in self.csvFid_faction_mod:
            newRelations = set((faction, mod) for faction, mod in
                               self.csvFid_faction_mod[fid].iteritems() if
                               faction.ValidateFormID(self.patchFile))
        elif fid in self.fid_faction_mod:
            newRelations = set((faction, mod) for faction, mod in
                               self.fid_faction_mod[fid].iteritems() if
                               faction.ValidateFormID(self.patchFile))
        else:
            return
        curRelations = set(record.relations_list)
        changed = newRelations - curRelations
        if changed:
            override = record.CopyAsOverride(self.patchFile)
            if override:
                for faction,mod in changed:
                    for relation in override.relations:
                        if relation.faction == faction:
                            relation.mod = mod
                            break
                    else:
                        relation = override.create_relation()
                        relation.faction,relation.mod = faction,mod
                self.mod_count[modFile.GName] += 1
                record.UnloadRecord()
                record._RecordID = override._RecordID

#------------------------------------------------------------------------------
class CBash_ImportScripts(_RecTypeModLogging):
    _read_write_records = ('ACTI', 'ALCH', 'APPA', 'ARMO', 'BOOK', 'CLOT',
        'CONT', 'CREA', 'DOOR', 'FLOR', 'FURN', 'INGR', 'KEYM', 'LIGH', 'LVLC',
        'MISC', 'NPC_', 'QUST', 'SGST', 'SLGM', 'WEAP')

    def __init__(self, p_name, p_file, p_sources):
        super(CBash_ImportScripts, self).__init__(p_name, p_file, p_sources)
        self.id_script = {}

    def scan(self,modFile,record,bashTags):
        """Records information needed to apply the patch."""
        script = record.ConflictDetails(('script',))
        if script:
            script = script['script']
            if script.ValidateFormID(self.patchFile):
                # Only save if different from the master record
                if record.GetParentMod().GName != record.fid[0]:
                    history = record.History()
                    if history and len(history) > 0:
                        masterRecord = history[0]
                        if masterRecord.GetParentMod().GName == record.fid[
                            0] and masterRecord.script == record.script:
                            return # Same
                self.id_script[record.fid] = script
            else:
                # Ignore the record. Another option would be to just ignore
                # the invalid formIDs
                self.patchFile.patcher_mod_skipcount[self._patcher_name][
                    modFile.GName] += 1

    def apply(self,modFile,record,bashTags):
        """Edits patch file as desired."""
        self.scan_more(modFile,record,bashTags)
        recordId = record.fid
        if recordId in self.id_script and record.script != self.id_script[
            recordId]:
            override = record.CopyAsOverride(self.patchFile)
            if override:
                override.script = self.id_script[recordId]
                self.mod_count[record._Type][modFile.GName] += 1
                record.UnloadRecord()
                record._RecordID = override._RecordID

#------------------------------------------------------------------------------
class CBash_ImportInventory(_AImportInventory, _RecTypeModLogging):
    _read_write_records = ('CREA', 'NPC_', 'CONT')
    listSrcs=False
    logModRecs = u'%(type)s ' + _(u'Inventories Changed') + u': %(count)d'
    allowUnloaded = False # FIXME CORRECT? comments seem to say so

    def scan(self,modFile,record,bashTags):
        """Records information needed to apply the patch."""
        #--Source mod?
        masters = record.History()
        if not masters: return
        entries = record.items_list
        modItems = set((item, count) for item, count in entries if
                       item.ValidateFormID(self.patchFile))
        masterEntries = []
        id_deltas = self.id_deltas
        fid = record.fid
        for masterEntry in masters:
            masterItems = set(
                (item, count) for item, count in masterEntry.items_list if
                item.ValidateFormID(self.patchFile))
            removeItems = (masterItems - modItems
                           if u'Invent.Remove' in bashTags else set())
            addItems = (modItems - masterItems
                        if u'Invent.Add' in bashTags else set())
            if removeItems or addItems:
                id_deltas[fid].append(({item for item, count in removeItems},
                                       addItems))

    def apply(self,modFile,record,bashTags):
        """Edits patch file as desired."""
        self.scan_more(modFile,record,bashTags)
        deltas = self.id_deltas[record.fid]
        if not deltas: return
        #If only the inventory is imported, the deltas have to be applied to
        #whatever record would otherwise be winning
        if modFile.GName in self.inventOnlyMods:
            conflicts = record.Conflicts()
            if conflicts:
                #If this isn't actually the winning record, use it.
                #This could be the case if a record was already copied into
                # the patch
                if conflicts[0] != record:
                    record = conflicts[0]
                #Otherwise, use the previous one.
                else:
                    record = conflicts[1]

        removable = set(entry.item for entry in record.items)
        items = record.items_list
        for removeItems,addEntries in reversed(deltas):
            if removeItems:
                #--Skip if some items to be removed have already been removed
                if not removeItems.issubset(removable): continue
                items = [(item, count) for item, count in items if
                         item not in removeItems]
                removable -= removeItems
            if addEntries:
                current = set(item for item,count in items)
                for item,count in addEntries:
                    if item not in current:
                        items.append((item,count))

        if len(items) != len(record.items_list) or set(
                (item, count) for item, count in record.items_list) != set(
                (item, count) for item, count in items):
            override = record.CopyAsOverride(self.patchFile)
            if override:
                override.items_list = items
                self.mod_count[record._Type][modFile.GName] += 1
                record.UnloadRecord()
                record._RecordID = override._RecordID

#------------------------------------------------------------------------------
class CBash_ImportActorsSpells(CBash_ImportPatcher):
    logMsg = u'* '+_(u'Imported Spell Lists') + u': %d'
    _read_write_records = ('CREA', 'NPC_')

    def __init__(self, p_name, p_file, p_sources):
        super(CBash_ImportActorsSpells, self).__init__(p_name, p_file,
                                                       p_sources)
        self.id_spells = {}

    def scan(self,modFile,record,bashTags):
        """Records information needed to apply the patch."""
        curData = {'deleted':[],'merged':[]}
        curspells = FormID.FilterValid(record.spells, self.patchFile)
        parentRecords = record.History()
        if parentRecords:
            parentSpells = FormID.FilterValid(parentRecords[-1].spells,
                                              self.patchFile)
            if parentSpells != curspells or u'Actors.SpellsForceAdd' in \
                    bashTags:
                for spell in parentSpells:
                    if spell not in curspells:
                        curData['deleted'].append(spell)
            curData['merged'] = curspells
            if record.fid not in self.id_spells:
                self.id_spells[record.fid] = curData
            else:
                id_spells = self.id_spells[record.fid]
                for spell in curData['deleted']:
                    if spell in id_spells['merged']:
                        id_spells['merged'].remove(spell)
                    id_spells['deleted'].append(spell)
                for spell in curData['merged']:
                    if spell in id_spells['merged']: continue  # don't want
                    # to add 20 copies of the spell afterall
                    if spell not in id_spells[
                        'deleted'] or u'Actors.SpellsForceAdd' in bashTags:
                        id_spells['merged'].append(spell)

    def apply(self,modFile,record,bashTags):
        """Edits patch file as desired."""
        self.scan_more(modFile,record,bashTags)
        recordId = record.fid
        mergedSpells = self.id_spells.get(recordId,None)
        if mergedSpells:
            if sorted(record.spells) != sorted(mergedSpells['merged']):
                override = record.CopyAsOverride(self.patchFile)
                if override:
                    override.spells = mergedSpells['merged']
                    self.mod_count[modFile.GName] += 1
                    record.UnloadRecord()
                    record._RecordID = override._RecordID

    def _clog(self,log): # type 2
        self._srcMods(log)
        super(CBash_ImportActorsSpells, self)._clog(log)

#------------------------------------------------------------------------------
class CBash_NamesPatcher(_ANamesPatcher, _RecTypeModLogging):
    _read_write_records = (
        'CLAS', 'FACT', 'HAIR', 'EYES', 'RACE', 'MGEF', 'ENCH', 'SPEL', 'BSGN',
        'ACTI', 'APPA', 'ARMO', 'BOOK', 'CLOT', 'CONT', 'DOOR', 'INGR', 'LIGH',
        'MISC', 'FLOR', 'FURN', 'WEAP', 'AMMO', 'NPC_', 'CREA', 'SLGM', 'KEYM',
        'ALCH', 'SGST', 'WRLD', 'CELLS', 'DIAL', 'QUST')

    def __init__(self, p_name, p_file, p_sources):
        super(CBash_NamesPatcher, self).__init__(p_name, p_file, p_sources)
        self.id_full = {}
        self.csvId_full = {}

    def initData(self, progress):
        if not self.isActive: return
        super(CBash_NamesPatcher, self).initData(progress)
        fullNames = self._parse_texts(CBash_FullNames, progress)
        #--Finish
        csvId_full = self.csvId_full
        for group,fid_name in fullNames.group_fid_name.iteritems():
            if group not in validTypes: continue
            for fid, (eid, name_) in fid_name.iteritems():
                if name_ != u'NO NAME':
                    csvId_full[fid] = name_

    def scan(self,modFile,record,bashTags):
        """Records information needed to apply the patch."""
        full = record.ConflictDetails(('full',))
        if full:
            self.id_full[record.fid] = full['full']

    def apply(self,modFile,record,bashTags):
        """Edits patch file as desired."""
        self.scan_more(modFile,record,bashTags)
        recordId = record.fid
        full = self.id_full.get(recordId, None)
        full = self.csvId_full.get(recordId, full)
        if full and record.full != full:
            override = record.CopyAsOverride(self.patchFile)
            if override:
                override.full = full
                self.mod_count[record._Type][modFile.GName] += 1
                record.UnloadRecord()
                record._RecordID = override._RecordID

#------------------------------------------------------------------------------
class CBash_NpcFacePatcher(_ANpcFacePatcher,CBash_ImportPatcher):
    logMsg = u'* '+_(u'Faces Patched') + u': %d'

    def __init__(self, p_name, p_file, p_sources):
        super(CBash_NpcFacePatcher, self).__init__(p_name, p_file, p_sources)
        self.id_face = {}
        self.faceData = (
            'fggs_p', 'fgga_p', 'fgts_p', 'eye', 'hair', 'hairLength',
            'hairRed', 'hairBlue', 'hairGreen')

    def scan(self,modFile,record,bashTags):
        """Records information needed to apply the patch."""
        attrs = []
        if u'NpcFacesForceFullImport' in bashTags:
            face = dict((attr,getattr(record,attr)) for attr in self.faceData)
            if ValidateDict(face, self.patchFile):
                self.id_face[record.fid] = face
            else:
                self._ignore_record(modFile.GName)
            return
        elif u'NpcFaces' in bashTags:
            attrs = self.faceData
        else:
            if u'Npc.HairOnly' in bashTags:
                attrs = ['hair', 'hairLength','hairRed','hairBlue','hairGreen']
            if u'Npc.EyesOnly' in bashTags:
                attrs += ['eye']
        if not attrs:
            return
        face = record.ConflictDetails(attrs)
        if ValidateDict(face, self.patchFile):
            fid = record.fid
            # Only save if different from the master record
            if record.GetParentMod().GName != fid[0]:
                history = record.History()
                if history and len(history) > 0:
                    masterRecord = history[0]
                    if masterRecord.GetParentMod().GName == record.fid[0]:
                        for attr, value in face.iteritems():
                            if getattr(masterRecord,attr) != value:
                                break
                        else:
                            return
            self.id_face.setdefault(fid,{}).update(face)
        else:
            self._ignore_record(modFile.GName)

    def apply(self,modFile,record,bashTags):
        """Edits patch file as desired."""
        self.scan_more(modFile,record,bashTags)

        recordId = record.fid
        prev_face_value = self.id_face.get(recordId,None)
        if prev_face_value:
            cur_face_value = dict(
                (attr, getattr(record, attr)) for attr in prev_face_value)
            if cur_face_value != prev_face_value:
                override = record.CopyAsOverride(self.patchFile)
                if override:
                    for attr, value in prev_face_value.iteritems():
                        setattr(override,attr,value)
                    self.mod_count[modFile.GName] += 1
                    record.UnloadRecord()
                    record._RecordID = override._RecordID

    def _clog(self,log): # type 2
        self._srcMods(log)
        super(CBash_NpcFacePatcher, self)._clog(log)

#------------------------------------------------------------------------------
class CBash_SoundPatcher(_RecTypeModLogging):
    """Imports sounds from source mods into patch."""
    _read_write_records = (
        'ACTI', 'CONT', 'CREA', 'DOOR', 'LIGH', 'MGEF', 'WTHR')

    def __init__(self, p_name, p_file, p_sources):
        super(CBash_SoundPatcher, self).__init__(p_name, p_file, p_sources)
        class_attrs = self.class_attrs = {}
        class_attrs['ACTI'] = ('sound',)
        class_attrs['CONT'] = ('soundOpen','soundClose')
        class_attrs['CREA'] = ('footWeight','inheritsSoundsFrom','sounds_list')
        class_attrs['DOOR'] = ('soundOpen','soundClose','soundLoop')
        class_attrs['LIGH'] = ('sound',)
        class_attrs['MGEF'] = (
            'castingSound', 'boltSound', 'hitSound', 'areaSound')
        ##        class_attrs['REGN'] = ('sound','sounds_list')
        class_attrs['WTHR'] = ('sounds_list',)

    def apply(self,modFile,record,bashTags):
        """Edits patch file as desired."""
        self.scan_more(modFile,record,bashTags)
        recordId = record.fid
        prev_attr_value = self.fid_attr_value.get(recordId,None)
        if prev_attr_value:
            cur_attr_value = dict(
                (attr, getattr(record, attr)) for attr in prev_attr_value)
            if cur_attr_value != prev_attr_value:
                override = record.CopyAsOverride(self.patchFile)
                if override:
                    for attr, value in prev_attr_value.iteritems():
                        setattr(override,attr,value)
                    self.mod_count[record._Type][modFile.GName] += 1
                    record.UnloadRecord()
                    record._RecordID = override._RecordID

#------------------------------------------------------------------------------
class CBash_StatsPatcher(_AStatsPatcher, _RecTypeModLogging):

    def __init__(self, p_name, p_file, p_sources):
        super(CBash_StatsPatcher, self).__init__(p_name, p_file, p_sources)
        self.csvFid_attr_value = {}
        self.class_attrs = bush.game.statsTypes

    def initData(self, progress):
        """Compiles material, i.e. reads source text, esp's, etc. as
        necessary."""
        if not self.isActive: return
        super(CBash_StatsPatcher, self).initData(progress)
        itemStats = self._parse_texts(CBash_ItemStats, progress)
        #--Finish
        for group,nId_attr_value in itemStats.class_fid_attr_value.iteritems():
            if group not in validTypes: continue
            self.csvFid_attr_value.update(nId_attr_value)

    def getTypes(self):
        """Returns the group types that this patcher checks"""
        return self.class_attrs.keys()

    def apply(self,modFile,record,bashTags):
        """Edits patch file as desired."""
        self.scan_more(modFile,record,bashTags)
        recordId = record.fid
        prev_attr_value = self.fid_attr_value.get(recordId, None)
        csv_attr_value = self.csvFid_attr_value.get(recordId, None)
        if csv_attr_value and ValidateDict(csv_attr_value, self.patchFile):
            prev_attr_value = csv_attr_value
        if prev_attr_value:
            cur_attr_value = dict((attr,getattr(record,attr)) for attr in prev_attr_value)
            if cur_attr_value != prev_attr_value:
                override = record.CopyAsOverride(self.patchFile)
                if override:
                    for attr, value in prev_attr_value.iteritems():
                        setattr(override,attr,value)
                    self.mod_count[record._Type][modFile.GName] += 1
                    record.UnloadRecord()
                    record._RecordID = override._RecordID

#------------------------------------------------------------------------------
class CBash_SpellsPatcher(CBash_ImportPatcher, _ASpellsPatcher):
    logMsg = u'* ' + _(u'Modified SPEL Stats') + u': %d'

    def __init__(self, p_name, p_file, p_sources):
        super(CBash_SpellsPatcher, self).__init__(p_name, p_file, p_sources)
        self.id_stats = {}
        self.csvId_stats = {}
        self.spell_attrs = None #set in initData

    def initData(self, progress):
        if not self.isActive: return
        super(CBash_SpellsPatcher, self).initData(progress)
        spellStats = self._parse_texts(CBash_SpellRecords, progress)
        self.spell_attrs = spellStats.attrs
        #--Finish
        self.csvId_stats.update(spellStats.fid_stats)

    def scan(self,modFile,record,bashTags):
        """Records information needed to apply the patch."""
        conflicts = record.ConflictDetails(self.spell_attrs)
        if conflicts:
            if ValidateDict(conflicts, self.patchFile):
                self.id_stats.setdefault(record.fid,{}).update(conflicts)
            else:
                #Ignore the record. Another option would be to just ignore the invalid formIDs
                self.patchFile.patcher_mod_skipcount[self._patcher_name][
                    modFile.GName] += 1

    def apply(self,modFile,record,bashTags):
        """Edits patch file as desired."""
        self.scan_more(modFile,record,bashTags)
        recordId = record.fid
        prev_values = self.id_stats.get(recordId, None)
        csv_values = self.csvId_stats.get(recordId, None)
        if csv_values and ValidateDict(csv_values, self.patchFile):
            prev_values = csv_values
        if prev_values:
            rec_values = dict(
                (attr, getattr(record, attr)) for attr in prev_values)
            if rec_values != prev_values:
                override = record.CopyAsOverride(self.patchFile)
                if override:
                    for attr, value in prev_values.iteritems():
                        setattr(override,attr,value)
                    self.mod_count[modFile.GName] += 1
                    record.UnloadRecord()
                    record._RecordID = override._RecordID
