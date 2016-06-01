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

"""This module contains the oblivion MultitweakItem patcher classes that tweak
races records. As opposed to the rest of the multitweak items these are not
grouped by a MultiTweaker but by the RacePatcher (also in this module) which
is a SpecialPatcher. Notice the PBash ones do not log in buildPatch - the
RacesTweaker patcher was calling their "log" method - now super's _patchLog()
"""

import random
import re
# Internal
from ... import bush # for defaultEyes (?)
from ... import bosh # for modInfos
from ... import load_order
from ...bolt import SubProgress, BoltError, GPath, deprint
from ...brec import MreRecord, MelObject, strFid
from ...cint import ValidateDict, FormID
from ...patcher.base import AMultiTweakItem
from ...patcher.patch_files import PatchFile
from .base import MultiTweakItem, CBash_MultiTweakItem, SpecialPatcher, \
    DoublePatcher, CBash_DoublePatcher
from ...parsers import LoadFactory, ModFile

# Patchers: 40 ----------------------------------------------------------------
class ARaceTweaker_BiggerOrcsAndNords(AMultiTweakItem):

    #--Config Phase -----------------------------------------------------------
    def __init__(self):
        super(ARaceTweaker_BiggerOrcsAndNords, self).__init__(
            _(u"Bigger Nords and Orcs"),
            _(u'Adjusts the Orc and Nord race records to be taller/heavier '
              u'- to be more lore friendly.'),
            u'BiggerOrcsandNords',
            # ('Example',(Nordmaleheight,NordFheight,NordMweight,
            # NordFweight,Orcmaleheight,OrcFheight,OrcMweight,OrcFweight))
            (u'Bigger Nords and Orcs',
             ((1.09, 1.09, 1.13, 1.06), (1.09, 1.09, 1.13, 1.0))),
            (u'MMM Resized Races',
                ((1.08, 1.07, 1.28, 1.19), (1.09, 1.06, 1.36, 1.3))),
            (u'RBP', ((1.075,1.06,1.20,1.125),(1.06,1.045,1.275,1.18)))
            )
        self.logMsg = u'* '+ _(u'Races tweaked') + u': %d'

class RaceTweaker_BiggerOrcsAndNords(ARaceTweaker_BiggerOrcsAndNords,
                                     MultiTweakItem):
    """Adjusts the Orc and Nord race records to be taller/heavier."""
    #--Patch Phase ------------------------------------------------------------
    def getReadClasses(self):
        """Returns load factory classes needed for reading."""
        return 'RACE',

    def getWriteClasses(self):
        """Returns load factory classes needed for writing."""
        return 'RACE',

    def scanModFile(self,modFile,progress,patchFile):
        mapper = modFile.getLongMapper()
        patchRecords = patchFile.RACE
        for record in modFile.RACE.getActiveRecords():
            if not record.full: continue
            if not u'orc' in record.full.lower() and not u'nord' in \
                    record.full.lower(): continue
            record = record.getTypeCopy(mapper)
            patchRecords.setRecord(record)

    def buildPatch(self,progress,patchFile,extra):
        """Edits patch file as desired."""
        count = self.count = {}
        keep = patchFile.getKeeper()
        for record in patchFile.RACE.records:
            if not record.full: continue
            if u'nord' in record.full.lower():
                for attr, value in zip(
                        ['maleHeight', 'femaleHeight', 'maleWeight',
                         'femaleWeight'],
                        self.choiceValues[self.chosen][0][0]):
                    setattr(record,attr,value)
                keep(record.fid)
                srcMod = record.fid[0]
                count[srcMod] = count.get(srcMod,0) + 1
                continue
            elif u'orc' in record.full.lower():
                for attr, value in zip(
                        ['maleHeight', 'femaleHeight', 'maleWeight',
                         'femaleWeight'],
                        self.choiceValues[self.chosen][0][1]):
                    setattr(record,attr,value)
                keep(record.fid)
                srcMod = record.fid[0]
                count[srcMod] = count.get(srcMod,0) + 1

class CBash_RaceTweaker_BiggerOrcsAndNords(ARaceTweaker_BiggerOrcsAndNords,
                                           CBash_MultiTweakItem):
    """Changes all Orcs and Nords to be bigger."""
    name = _(u"Bigger Nords and Orcs")

    #--Config Phase -----------------------------------------------------------
    def __init__(self):
        super(CBash_RaceTweaker_BiggerOrcsAndNords, self).__init__()
        self.attrs = ['maleHeight','femaleHeight','maleWeight','femaleWeight']

    def getTypes(self):
        return ['RACE']

    #--Patch Phase ------------------------------------------------------------
    def apply(self,modFile,record,bashTags):
        """Edits patch file as desired. """
        if not record.full: return
        if u'nord' in record.full.lower():
            newValues = self.choiceValues[self.chosen][0][0]
        elif u'orc' in record.full.lower():
            newValues = self.choiceValues[self.chosen][0][1]
        else:
            return

        oldValues = tuple(map(record.__getattribute__, self.attrs))
        if oldValues != newValues:
            override = record.CopyAsOverride(self.patchFile)
            if override:
                map(override.__setattr__, self.attrs, newValues)
                mod_count = self.mod_count
                mod_count[modFile.GName] = mod_count.get(modFile.GName,0) + 1
                record.UnloadRecord()
                record._RecordID = override._RecordID
                return

class ARaceTweaker_MergeSimilarRaceHairs(AMultiTweakItem):
    """Merges similar race's hairs (kinda specifically designed for SOVVM's
    bearded races)."""

    #--Config Phase -----------------------------------------------------------
    def __init__(self):
        super(ARaceTweaker_MergeSimilarRaceHairs, self).__init__(
            _(u"Merge Hairs from similar races"),
            _(u'Merges hair lists from similar races (f.e. give RBP khajit '
              u'hair to all the other varieties of khajits in Elsweyr)'),
            u'MergeSimilarRaceHairLists',
            (_(u'Merge hairs only from vanilla races'), 1),
            (_(u'Full hair merge between similar races'), 0),
            )
        self.logMsg = u'* '+ _(u'Races tweaked') + u': %d'

class RaceTweaker_MergeSimilarRaceHairs(ARaceTweaker_MergeSimilarRaceHairs,
                                        MultiTweakItem):
    #--Patch Phase ------------------------------------------------------------
    def getReadClasses(self):
        """Returns load factory classes needed for reading."""
        return 'RACE',

    def getWriteClasses(self):
        """Returns load factory classes needed for writing."""
        return 'RACE',

    def scanModFile(self,modFile,progress,patchFile):
        mapper = modFile.getLongMapper()
        patchRecords = patchFile.RACE
        for record in modFile.RACE.getActiveRecords():
            if not record.full: continue
            patchRecords.setRecord(record.getTypeCopy(mapper))

    def buildPatch(self,progress,patchFile,extra):
        """Edits patch file as desired."""
        count = self.count = {}
        #process hair lists
        changedHairs = {}
        vanilla = ['argonian', 'breton', 'dremora', 'dark elf', 'dark seducer',
                   'golden saint', 'high elf', 'imperial', 'khajiit', 'nord',
                   'orc', 'redguard', 'wood elf']
        if self.choiceValues[self.chosen][0] == 1:  # merge hairs only from
            # vanilla races to custom hairs.
            for race in extra:
                for r in vanilla:
                    if r in race:
                        if extra[r]['hairs'] != extra[race]['hairs']:
                            changedHairs[race] = list(set(
                                extra[r]['hairs'] + extra[race][
                                    'hairs']))  # yuach nasty but quickly
                                    # and easily removes duplicates.
        else: # full back and forth merge!
            for race in extra:
                #nasty processing slog
                rs = race.split('(')
                rs = rs[0].split()
                if len(rs) > 1 and rs[1] in ['elf','seducer']:
                    rs[0] = rs[0]+' '+rs[1]
                    del(rs[1])
                for r in extra:
                    if r == race: continue
                    for s in rs:
                        if s in r:
                            if extra[r]['hairs'] != extra[race]['hairs']:
                                changedHairs[race] = list(set(
                                    extra[r]['hairs'] + extra[race]['hairs']))
                                # list(set([]) disgusting thing again
        keep = patchFile.getKeeper()
        for record in patchFile.RACE.records:
            if not record.full: continue
            if not record.full.lower() in changedHairs: continue
            record.hairs = changedHairs[record.full.lower()]
            keep(record.fid)
            srcMod = record.fid[0]
            count[srcMod] = count.get(srcMod,0) + 1

class CBash_RaceTweaker_MergeSimilarRaceHairs(
    ARaceTweaker_MergeSimilarRaceHairs, CBash_MultiTweakItem):
    name = _(u"Merge Hairs from similar races")

    #--Config Phase -----------------------------------------------------------
    def getTypes(self):
        return ['RACE']

    #--Patch Phase ------------------------------------------------------------
    def finishPatch(self,patchFile,progress):
        """Edits the bashed patch file directly."""
        Current = patchFile.Current
        subProgress = SubProgress(progress)
        subProgress.setFull(max(len(Current.LoadOrderMods) * 2,1))
        races_data = patchFile.races_data
        races_vanilla = patchFile.races_vanilla
        changedHairs = {}
        mod_count = self.mod_count
        #process hair list:s
        if self.choiceValues[self.chosen][0] == 1:  # merge hairs only from
            # vanilla races to custom hairs.
            for race in races_data:
                for r in races_vanilla:
                    if r in race:
                        if races_data[r]['hairs'] != races_data[race]['hairs']:
                            changedHairs[race] = list(set(
                                races_data[r]['hairs'] + races_data[race][
                                    'hairs']))  # yuach nasty but quickly
                                    # and easily removes duplicates.
        else: # full back and forth merge!
            for race in races_data:
                #nasty processing slog
                rs = race.split('(')
                rs = rs[0].split()
                if len(rs) > 1 and rs[1] in ['elf','seducer']:
                    rs[0] = rs[0]+' '+rs[1]
                    del(rs[1])
                for r in races_data:
                    if r == race: continue
                    for s in rs:
                        if s in r:
                            if races_data[r]['hairs'] != races_data[race][
                                'hairs']:
                                # list(set([]) disgusting thing again
                                changedHairs[race] = list(set(
                                    races_data[r]['hairs'] + races_data[race][
                                        'hairs']))
        pstate = 0
        for modFile in Current.LoadOrderMods:
            subProgress(pstate, _(u'Merging hairs...')+u'\n')
            for race in modFile.RACE:
                if not race.full: continue
                if not race.full.lower() in changedHairs: continue
                if race.IsWinning():
                    if race.hairs != changedHairs[race.full.lower()]:
                        override = race.CopyAsOverride(patchFile)
                        if override:
                            override.hairs = changedHairs[race.full.lower()]
                            mod_count[modFile.GName] = mod_count.get(
                                modFile.GName, 0) + 1
                            race.UnloadRecord()
                            race._RecordID = override._RecordID

class ARaceTweaker_MergeSimilarRaceEyes(AMultiTweakItem):
    """Merges similar race's eyes."""

    #--Config Phase -----------------------------------------------------------
    def __init__(self):
        super(ARaceTweaker_MergeSimilarRaceEyes, self).__init__(
            _(u"Merge Eyes from similar races"),
            _(u'Merges eye lists from similar races (f.e. give RBP khajit '
              u'eyes to all the other varieties of khajits in Elsweyr)'),
            u'MergeSimilarRaceEyeLists',
            (_(u'Merge eyes only from vanilla races'), 1),
            (_(u'Full eye merge between similar races'), 0),
            )
        self.logMsg = u'* '+ _(u'Races tweaked') + u': %d'

class RaceTweaker_MergeSimilarRaceEyes(ARaceTweaker_MergeSimilarRaceEyes,
                                       MultiTweakItem):
    #--Patch Phase ------------------------------------------------------------
    def getReadClasses(self):
        """Returns load factory classes needed for reading."""
        return 'RACE',

    def getWriteClasses(self):
        """Returns load factory classes needed for writing."""
        return 'RACE',

    def scanModFile(self,modFile,progress,patchFile):
        mapper = modFile.getLongMapper()
        patchRecords = patchFile.RACE
        for record in modFile.RACE.getActiveRecords():
            if not record.full: continue
            patchRecords.setRecord(record.getTypeCopy(mapper))

    def buildPatch(self,progress,patchFile,extra):
        """Edits patch file as desired."""
        count = self.count = {}
        #process hair lists
        changedEyes = {}
        vanilla = ['argonian', 'breton', 'dremora', 'dark elf', 'dark seducer',
                   'golden saint', 'high elf', 'imperial', 'khajiit', 'nord',
                   'orc', 'redguard', 'wood elf']
        if self.choiceValues[self.chosen][0] == 1:  # merge eyes only from
            # vanilla races to custom eyes.
            for race in extra:
                for r in vanilla:
                    if r in race:
                        if extra[r]['eyes'] != extra[race]['eyes']:
                            changedEyes[race] = list(set(
                                extra[r]['eyes'] + extra[race][
                                    'eyes']))  # yuach nasty but quickly and
                                    #  easily removes duplicates.
        else: # full back and forth merge!
            for race in extra:
                #nasty processing slog
                rs = race.split('(')
                rs = rs[0].split()
                if len(rs) > 1 and rs[1] in ['elf','seducer']:
                    rs[0] = rs[0]+' '+rs[1]
                    del(rs[1])
                for r in extra:
                    if r == race: continue
                    for s in rs:
                        if s in r:
                            if extra[r]['eyes'] != extra[race]['eyes']:
                                changedEyes[race] = list(set(
                                    changedEyes.setdefault(race, []) +
                                    extra[r]['eyes'] + extra[race]['eyes']))
                                # list(set([]) disgusting thing again
        keep = patchFile.getKeeper()
        for record in patchFile.RACE.records:
            if not record.full: continue
            if not record.full.lower() in changedEyes: continue
            record.eyes = changedEyes[record.full.lower()]
            keep(record.fid)
            srcMod = record.fid[0]
            count[srcMod] = count.get(srcMod,0) + 1

class CBash_RaceTweaker_MergeSimilarRaceEyes(ARaceTweaker_MergeSimilarRaceEyes,
                                             CBash_MultiTweakItem):
    """Merges similar race's eyes."""
    name = _(u"Merge Eyes from similar races")

    #--Config Phase -----------------------------------------------------------
    def getTypes(self):
        return ['RACE']

    #--Patch Phase ------------------------------------------------------------
    def finishPatch(self,patchFile,progress):
        """Edits the bashed patch file directly."""
        Current = patchFile.Current
        subProgress = SubProgress(progress)
        subProgress.setFull(max(len(Current.LoadOrderMods) * 2,1))
        races_data = patchFile.races_data
        races_vanilla = patchFile.races_vanilla
        changedEyes = {}
        mod_count = self.mod_count
        #process hair list:s
        if self.choiceValues[self.chosen][0] == 1:  # merge hairs only from
            # vanilla races to custom hairs.
            for race in races_data:
                for r in races_vanilla:
                    if r in race:
                        if races_data[r]['eyes'] != races_data[race]['eyes']:
                            changedEyes[race] = list(set(
                                races_data[r]['eyes'] + races_data[race][
                                    'eyes']))  # yuach nasty but quickly and
                                    #  easily removes duplicates.
        else: # full back and forth merge!
            for race in races_data:
                #nasty processing slog
                rs = race.split('(')
                rs = rs[0].split()
                if len(rs) > 1 and rs[1] in ['elf','seducer']:
                    rs[0] = rs[0]+' '+rs[1]
                    del(rs[1])
                for r in races_data:
                    if r == race: continue
                    for s in rs:
                        if s in r:
                            if races_data[r]['eyes'] != races_data[race][
                                'eyes']:
                                # list(set([]) disgusting thing again
                                changedEyes[race] = list(set(
                                    changedEyes.setdefault(race, []) +
                                    races_data[r]['eyes'] + races_data[race][
                                        'eyes']))
        pstate = 0
        for modFile in Current.LoadOrderMods:
            subProgress(pstate, _(u'Merging eyes...')+u'\n')
            for race in modFile.RACE:
                if not race.full: continue
                if not race.full.lower() in changedEyes: continue
                if race.IsWinning():
                    if race.eyes != changedEyes[race.full.lower()]:
                        override = race.CopyAsOverride(patchFile)
                        if override:
                            override.eyes = changedEyes[race.full.lower()]
                            mod_count[modFile.GName] = mod_count.get(
                                modFile.GName, 0) + 1
                            race.UnloadRecord()
                            race._RecordID = override._RecordID

class ARaceTweaker_AllHairs(AMultiTweakItem):
    """Gives all races ALL hairs."""

    #--Config Phase -----------------------------------------------------------
    def __init__(self):
        super(ARaceTweaker_AllHairs, self).__init__(_(u"Races Have All Hairs"),
            _(u'Gives all races every available hair.'),
            u'hairyraces',
            (u'get down tonight',1)
            )
        self.logMsg = u'* '+ _(u'Races tweaked') + u': %d'

class RaceTweaker_AllHairs(ARaceTweaker_AllHairs,MultiTweakItem):
    #--Patch Phase ------------------------------------------------------------
    def getReadClasses(self):
        """Returns load factory classes needed for reading."""
        return 'RACE',

    def getWriteClasses(self):
        """Returns load factory classes needed for writing."""
        return 'RACE',

    def scanModFile(self,modFile,progress,patchFile):
        mapper = modFile.getLongMapper()
        patchRecords = patchFile.RACE
        for record in modFile.RACE.getActiveRecords():
            patchRecords.setRecord(record.getTypeCopy(mapper))

    def buildPatch(self,progress,patchFile,extra):
        """Edits patch file as desired."""
        count = self.count = {}
        hairs = extra['HAIR']
        keep = patchFile.getKeeper()
        for record in patchFile.RACE.records:
            if record.hairs == hairs: continue
            record.hairs = hairs
            keep(record.fid)
            srcMod = record.fid[0]
            count[srcMod] = count.get(srcMod,0) + 1

class CBash_RaceTweaker_AllHairs(ARaceTweaker_AllHairs,CBash_MultiTweakItem):
    name = _(u"Races Have All Hairs")

    #--Config Phase -----------------------------------------------------------
    def getTypes(self):
        return ['RACE']

    #--Patch Phase ------------------------------------------------------------
    def apply(self,modFile,record,bashTags):
        """Edits patch file as desired. """
        if record.hairs != self.patchFile.races_data['HAIR']:
            override = record.CopyAsOverride(self.patchFile)
            if override:
                override.hairs = self.patchFile.races_data['HAIR']
                mod_count = self.mod_count
                mod_count[modFile.GName] = mod_count.get(modFile.GName,0) + 1
                record.UnloadRecord()
                record._RecordID = override._RecordID
                return

class ARaceTweaker_AllEyes(AMultiTweakItem):
    """Gives all races ALL eyes."""

    #--Config Phase -----------------------------------------------------------
    def __init__(self,opt=(u'what a lot of eyes you have dear',1)):
        super(ARaceTweaker_AllEyes, self).__init__(_(u"Races Have All Eyes"),
            _(u'Gives all races every available eye.'),
            u'eyeyraces',
            opt
            )
        self.logMsg = u'* '+ _(u'Races tweaked') + u': %d'

class RaceTweaker_AllEyes(ARaceTweaker_AllEyes,MultiTweakItem):

    #--Patch Phase ------------------------------------------------------------
    def getReadClasses(self):
        """Returns load factory classes needed for reading."""
        return 'RACE',

    def getWriteClasses(self):
        """Returns load factory classes needed for writing."""
        return 'RACE',

    def scanModFile(self,modFile,progress,patchFile):
        mapper = modFile.getLongMapper()
        patchRecords = patchFile.RACE
        for record in modFile.RACE.getActiveRecords():
            patchRecords.setRecord(record.getTypeCopy(mapper))

    def buildPatch(self,progress,patchFile,extra):
        """Edits patch file as desired."""
        count = self.count = {}
        eyes = extra['EYES']
        keep = patchFile.getKeeper()
        for record in patchFile.RACE.records:
            if record.eyes == eyes: continue
            record.eyes = eyes
            keep(record.fid)
            srcMod = record.fid[0]
            count[srcMod] = count.get(srcMod,0) + 1

class CBash_RaceTweaker_AllEyes(ARaceTweaker_AllEyes,CBash_MultiTweakItem):
    name = _(u"Races Have All Eyes")

    #--Config Phase -----------------------------------------------------------
    def __init__(self):
        super(CBash_RaceTweaker_AllEyes, self).__init__(
            opt=(u'them races are a real eye full', 1)
        )

    def getTypes(self):
        return ['RACE']

    #--Patch Phase ------------------------------------------------------------
    def apply(self,modFile,record,bashTags):
        """Edits patch file as desired. """
        if record.eyes != self.patchFile.races_data['EYES']:
            override = record.CopyAsOverride(self.patchFile)
            if override:
                override.eyes = self.patchFile.races_data['EYES']
                mod_count = self.mod_count
                mod_count[modFile.GName] = mod_count.get(modFile.GName,0) + 1
                record.UnloadRecord()
                record._RecordID = override._RecordID
                return

class ARaceTweaker_PlayableEyes(AMultiTweakItem):
    """Sets all eyes to be playable."""

    #--Config Phase -----------------------------------------------------------
    def __init__(self):
        super(ARaceTweaker_PlayableEyes, self).__init__(_(u"Playable Eyes"),
            _(u'Sets all eyes to be playable.'),
            u'playableeyes',
            (u'Get it done', 1),
            )
        self.logMsg = u'* '+ _(u'Eyes tweaked') + u': %d'

class RaceTweaker_PlayableEyes(ARaceTweaker_PlayableEyes,MultiTweakItem):
    #--Patch Phase ------------------------------------------------------------
    def getReadClasses(self):
        """Returns load factory classes needed for reading."""
        return 'EYES',

    def getWriteClasses(self):
        """Returns load factory classes needed for writing."""
        return 'EYES',

    def scanModFile(self,modFile,progress,patchFile):
        mapper = modFile.getLongMapper()
        patchRecords = patchFile.EYES
        for record in modFile.EYES.getActiveRecords():
            if record.flags.playable: continue
            patchRecords.setRecord(record.getTypeCopy(mapper))

    def buildPatch(self,progress,patchFile,extra):
        """Edits patch file as desired."""
        count = self.count = {}
        keep = patchFile.getKeeper()
        for record in patchFile.EYES.records:
            if record.flags.playable: continue
            record.flags.playable = True
            keep(record.fid)
            srcMod = record.fid[0]
            count[srcMod] = count.get(srcMod,0) + 1

class CBash_RaceTweaker_PlayableEyes(ARaceTweaker_PlayableEyes,
                                     CBash_MultiTweakItem):
    """Sets all eyes to be playable."""
    name = _(u"Playable Eyes")

    #--Config Phase -----------------------------------------------------------
    def getTypes(self):
        return ['EYES']

    #--Patch Phase ------------------------------------------------------------
    def apply(self,modFile,record,bashTags):
        """Edits patch file as desired. """
        if record.IsPlayable: return
        override = record.CopyAsOverride(self.patchFile)
        if override:
            override.IsPlayable = True
            mod_count = self.mod_count
            mod_count[modFile.GName] = mod_count.get(modFile.GName,0) + 1
            record.UnloadRecord()
            record._RecordID = override._RecordID
            return

class ARaceTweaker_PlayableHairs(AMultiTweakItem):
    """Sets all hairs to be playable."""

    #--Config Phase -----------------------------------------------------------
    def __init__(self):
        super(ARaceTweaker_PlayableHairs, self).__init__(_(u"Playable Hairs"),
            _(u'Sets all Hairs to be playable.'),
            u'playablehairs',
            (u'Get it done', 1),
            )
        self.logMsg = u'* '+ _(u'Hairs tweaked') + u': %d'

class RaceTweaker_PlayableHairs(ARaceTweaker_PlayableHairs,MultiTweakItem):
    #--Patch Phase ------------------------------------------------------------
    def getReadClasses(self):
        """Returns load factory classes needed for reading."""
        return 'HAIR',

    def getWriteClasses(self):
        """Returns load factory classes needed for writing."""
        return 'HAIR',

    def scanModFile(self,modFile,progress,patchFile):
        mapper = modFile.getLongMapper()
        patchRecords = patchFile.HAIR
        for record in modFile.HAIR.getActiveRecords():
            if record.flags.playable: continue
            patchRecords.setRecord(record.getTypeCopy(mapper))

    def buildPatch(self,progress,patchFile,extra):
        """Edits patch file as desired."""
        count = self.count = {}
        keep = patchFile.getKeeper()
        for record in patchFile.HAIR.records:
            if record.flags.playable: continue
            record.flags.playable = True
            keep(record.fid)
            srcMod = record.fid[0]
            count[srcMod] = count.get(srcMod,0) + 1

class CBash_RaceTweaker_PlayableHairs(ARaceTweaker_PlayableHairs,
                                      CBash_MultiTweakItem):
    """Sets all hairs to be playable."""
    name = _(u"Playable Hairs")

    #--Config Phase -----------------------------------------------------------
    def getTypes(self):
        return ['HAIR']

    #--Patch Phase ------------------------------------------------------------
    def apply(self,modFile,record,bashTags):
        """Edits patch file as desired. """
        if record.IsPlayable: return
        override = record.CopyAsOverride(self.patchFile)
        if override:
            override.IsPlayable = True
            mod_count = self.mod_count
            mod_count[modFile.GName] = mod_count.get(modFile.GName,0) + 1
            record.UnloadRecord()
            record._RecordID = override._RecordID
            return

class ARaceTweaker_SexlessHairs(AMultiTweakItem):
    """Sets all hairs to be playable by both males and females."""

    #--Config Phase -----------------------------------------------------------
    def __init__(self):
        super(ARaceTweaker_SexlessHairs, self).__init__(_(u"Sexless Hairs"),
            _(u'Lets any sex of character use any hair.'),
            u'sexlesshairs',
            (u'Get it done', 1),
            )
        self.logMsg = u'* '+ _(u'Hairs tweaked') + u': %d'

class RaceTweaker_SexlessHairs(ARaceTweaker_SexlessHairs,MultiTweakItem):
    #--Patch Phase ------------------------------------------------------------
    def getReadClasses(self):
        """Returns load factory classes needed for reading."""
        return 'HAIR',

    def getWriteClasses(self):
        """Returns load factory classes needed for writing."""
        return 'HAIR',

    def scanModFile(self,modFile,progress,patchFile):
        mapper = modFile.getLongMapper()
        patchRecords = patchFile.HAIR
        for record in modFile.HAIR.getActiveRecords():
            if record.flags.notMale or record.flags.notFemale:
                patchRecords.setRecord(record.getTypeCopy(mapper))

    def buildPatch(self,progress,patchFile,extra):
        """Edits patch file as desired."""
        count = self.count = {}
        keep = patchFile.getKeeper()
        for record in patchFile.HAIR.records:
            if record.flags.notMale or record.flags.notFemale:
                record.flags.notMale = 0
                record.flags.notFemale = 0
                keep(record.fid)
                srcMod = record.fid[0]
                count[srcMod] = count.get(srcMod,0) + 1

class CBash_RaceTweaker_SexlessHairs(ARaceTweaker_SexlessHairs,
                                     CBash_MultiTweakItem):
    name = _(u"Sexless Hairs")

    #--Config Phase -----------------------------------------------------------
    def getTypes(self):
        return ['HAIR']

    #--Patch Phase ------------------------------------------------------------
    def apply(self,modFile,record,bashTags):
        """Edits patch file as desired. """
        if record.IsNotFemale or record.IsNotMale:
            override = record.CopyAsOverride(self.patchFile)
            if override:
                override.IsNotFemale = False
                override.IsNotMale = False
                mod_count = self.mod_count
                mod_count[modFile.GName] = mod_count.get(modFile.GName,0) + 1
                record.UnloadRecord()
                record._RecordID = override._RecordID
                return

class RacePatcher(SpecialPatcher,DoublePatcher):
    """Merged leveled lists mod file."""
    name = _(u'Race Records')
    text = (_(u"Merge race eyes, hair, body, voice from ACTIVE AND/OR MERGED"
              u" mods.  Any non-active, non-merged mods in the following list"
              u" will be IGNORED.") + u'\n\n' +
            _(u"Even if none of the below mods are checked, this will sort"
              u" hairs and eyes and attempt to remove googly eyes from all"
              u" active mods.  It will also randomly assign hairs and eyes to"
              u" npcs that are otherwise missing them.")
            )
    tip = _(u"Merge race eyes, hair, body, voice from mods.")
    autoRe = re.compile(r'^UNDEFINED$',re.I)
    autoKey = (u'Hair',u'Eyes-D',u'Eyes-R',u'Eyes-E',u'Eyes',u'Body-M',
        u'Body-F',u'Body-Size-M',u'Body-Size-F',u'Voice-M',u'Voice-F',
        u'R.Relations',u'R.Teeth',u'R.Mouth',u'R.Ears',u'R.Head',
        u'R.Attributes-F',u'R.Attributes-M',u'R.Skills',u'R.Description',
        u'R.AddSpells',u'R.ChangeSpells',)
    forceAuto = True
    subLabel = _(u'Race Tweaks')
    races_data = {'EYES':[],'HAIR':[]}
    tweaks = sorted([
        RaceTweaker_BiggerOrcsAndNords(),
        RaceTweaker_MergeSimilarRaceHairs(),
        RaceTweaker_MergeSimilarRaceEyes(),
        RaceTweaker_PlayableEyes(),
        RaceTweaker_PlayableHairs(),
        RaceTweaker_SexlessHairs(),
        RaceTweaker_AllEyes(),
        RaceTweaker_AllHairs(),
        ],key=lambda a: a.label.lower())

    #--Config Phase -----------------------------------------------------------
    def getAutoItems(self):
        """Returns list of items to be used for automatic configuration."""
        autoItems = []
        autoRe = self.__class__.autoRe
        autoKey = set(self.__class__.autoKey)
        dex = load_order.loIndexCached
        for modInfo in bosh.modInfos.values():
            name = modInfo.name
            if dex(name) >= dex(PatchFile.patchName): continue
            if autoRe.match(name.s) or (autoKey & set(modInfo.getBashTags())):
                autoItems.append(name)
        return autoItems

    #--Patch Phase ------------------------------------------------------------
    def initPatchFile(self,patchFile,loadMods):
        super(RacePatcher, self).initPatchFile(patchFile, loadMods)
        self.races_data = {'EYES':[],'HAIR':[]}
        self.raceData = {} #--Race eye meshes, hair,eyes
        self.tempRaceData = {}
        #--Restrict srcs to active/merged mods.
        self.srcs = [x for x in self.srcs if x in patchFile.allSet]
        self.isActive = True #--Always enabled to support eye filtering
        self.bodyKeys = {'TailModel', 'UpperBodyPath', 'LowerBodyPath',
                         'HandPath', 'FootPath', 'TailPath'}
        self.sizeKeys = {'Height', 'Weight'}
        self.raceAttributes = {'Strength', 'Intelligence', 'Willpower',
                               'Agility', 'Speed', 'Endurance', 'Personality',
                               'Luck'}
        self.raceSkills = {'skill1', 'skill1Boost', 'skill2', 'skill2Boost',
                           'skill3', 'skill3Boost', 'skill4', 'skill4Boost',
                           'skill5', 'skill5Boost', 'skill6', 'skill6Boost',
                           'skill7', 'skill7Boost'}
        self.eyeKeys = {u'Eyes-D', u'Eyes-R', u'Eyes-E', u'Eyes'}
        #--Mesh tuple for each defined eye. Derived from race records.
        defaultMesh = (u'characters\\imperial\\eyerighthuman.nif',
                       u'characters\\imperial\\eyelefthuman.nif')
        self.eye_mesh = {}
        self.scanTypes = {'RACE', 'EYES', 'HAIR', 'NPC_'}

    def initData(self,progress):
        """Get data from source files."""
        if not self.isActive or not self.srcs: return
        loadFactory = LoadFactory(False,MreRecord.type_class['RACE'])
        progress.setFull(len(self.srcs))
        cachedMasters = {}
        for index,srcMod in enumerate(self.srcs):
            if srcMod not in bosh.modInfos: continue
            srcInfo = bosh.modInfos[srcMod]
            srcFile = ModFile(srcInfo,loadFactory)
            srcFile.load(True)
            masters = srcInfo.header.masters
            bashTags = srcInfo.getBashTags()
            if 'RACE' not in srcFile.tops: continue
            srcFile.convertToLongFids(('RACE',))
            self.tempRaceData = {} #so as not to carry anything over!
            if u'R.ChangeSpells' in bashTags and u'R.AddSpells' in bashTags:
                raise BoltError(
                    u'WARNING mod %s has both R.AddSpells and R.ChangeSpells '
                    u'tags - only one of those tags should be on a mod at '
                    u'one time' % srcMod.s)
            for race in srcFile.RACE.getActiveRecords():
                tempRaceData = self.tempRaceData.setdefault(race.fid,{})
                raceData = self.raceData.setdefault(race.fid,{})
                if u'Hair' in bashTags:
                    raceHair = raceData.setdefault('hairs',[])
                    for hair in race.hairs:
                        if hair not in raceHair: raceHair.append(hair)
                if self.eyeKeys & bashTags:
                    tempRaceData['rightEye'] = race.rightEye
                    tempRaceData['leftEye'] = race.leftEye
                    raceEyes = raceData.setdefault('eyes',[])
                    for eye in race.eyes:
                        if eye not in raceEyes: raceEyes.append(eye)
                if u'Voice-M' in bashTags:
                    tempRaceData['maleVoice'] = race.maleVoice
                if u'Voice-F' in bashTags:
                    tempRaceData['femaleVoice'] = race.femaleVoice
                if u'Body-M' in bashTags:
                    for key in ['male'+key for key in self.bodyKeys]:
                        tempRaceData[key] = getattr(race,key)
                if u'Body-F' in bashTags:
                    for key in ['female'+key for key in self.bodyKeys]:
                        tempRaceData[key] = getattr(race,key)
                if u'Body-Size-M' in bashTags:
                    for key in ['male'+key for key in self.sizeKeys]:
                        tempRaceData[key] = getattr(race,key)
                if u'Body-Size-F' in bashTags:
                    for key in ['female'+key for key in self.sizeKeys]:
                        tempRaceData[key] = getattr(race,key)
                if u'R.Teeth' in bashTags:
                    for key in ('teethLower','teethUpper'):
                        tempRaceData[key] = getattr(race,key)
                if u'R.Mouth' in bashTags:
                    for key in ('mouth','tongue'):
                        tempRaceData[key] = getattr(race,key)
                if u'R.Head' in bashTags:
                    tempRaceData['head'] = race.head
                if u'R.Ears' in bashTags:
                    for key in ('maleEars','femaleEars'):
                        tempRaceData[key] = getattr(race,key)
                if u'R.Relations' in bashTags:
                    relations = raceData.setdefault('relations',{})
                    for x in race.relations:
                        relations[x.faction] = x.mod
                if u'R.Attributes-F' in bashTags:
                    for key in ['female'+key for key in self.raceAttributes]:
                        tempRaceData[key] = getattr(race,key)
                if u'R.Attributes-M' in bashTags:
                    for key in ['male'+key for key in self.raceAttributes]:
                        tempRaceData[key] = getattr(race,key)
                if u'R.Skills' in bashTags:
                    for key in self.raceSkills:
                        tempRaceData[key] = getattr(race,key)
                if u'R.AddSpells' in bashTags:
                    tempRaceData['AddSpells'] = race.spells
                if u'R.ChangeSpells' in bashTags:
                    raceData['spellsOverride'] = race.spells
                if u'R.Description' in bashTags:
                    tempRaceData['text'] = race.text
            for master in masters:
                if not master in bosh.modInfos: continue  # or break
                # filter mods
                if master in cachedMasters:
                    masterFile = cachedMasters[master]
                else:
                    masterInfo = bosh.modInfos[master]
                    masterFile = ModFile(masterInfo,loadFactory)
                    masterFile.load(True)
                    if 'RACE' not in masterFile.tops: continue
                    masterFile.convertToLongFids(('RACE',))
                    cachedMasters[master] = masterFile
                for race in masterFile.RACE.getActiveRecords():
                    if race.fid not in self.tempRaceData: continue
                    tempRaceData = self.tempRaceData[race.fid]
                    raceData = self.raceData[race.fid]
                    if 'AddSpells' in tempRaceData:
                        raceData.setdefault('AddSpells', [])
                        for spell in tempRaceData['AddSpells']:
                            if spell not in race.spells:
                                if spell not in raceData['AddSpells']:
                                    raceData['AddSpells'].append(spell)
                        del tempRaceData['AddSpells']
                    for key in tempRaceData:
                        if not tempRaceData[key] == getattr(race,key):
                            raceData[key] = tempRaceData[key]
            progress.plus()

    def getReadClasses(self):
        """Returns load factory classes needed for reading."""
        return ('RACE','EYES','HAIR','NPC_',) if self.isActive else ()

    def getWriteClasses(self):
        """Returns load factory classes needed for writing."""
        return ('RACE','EYES','HAIR','NPC_',) if self.isActive else ()

    def scanModFile(self, modFile, progress):
        """Add appropriate records from modFile."""
        if not self.isActive: return
        races_data = self.races_data
        eye_mesh = self.eye_mesh
        modName = modFile.fileInfo.name
        mapper = modFile.getLongMapper()
        if not (set(modFile.tops) & self.scanTypes): return
        modFile.convertToLongFids(('RACE','EYES','HAIR','NPC_'))
        srcEyes = set(
            [record.fid for record in modFile.EYES.getActiveRecords()])
        #--Eyes, Hair
        for type in ('EYES','HAIR'):
            patchBlock = getattr(self.patchFile,type)
            id_records = patchBlock.id_records
            for record in getattr(modFile,type).getActiveRecords():
                races_data[type].append(record.fid)
                if record.fid not in id_records:
                    patchBlock.setRecord(record.getTypeCopy(mapper))
        #--Npcs with unassigned eyes
        patchBlock = self.patchFile.NPC_
        id_records = patchBlock.id_records
        for record in modFile.NPC_.getActiveRecords():
            if not record.eye and record.fid not in id_records:
                patchBlock.setRecord(record.getTypeCopy(mapper))
        #--Race block
        patchBlock = self.patchFile.RACE
        id_records = patchBlock.id_records
        for record in modFile.RACE.getActiveRecords():
            if record.fid not in id_records:
                patchBlock.setRecord(record.getTypeCopy(mapper))
            if not record.rightEye or not record.leftEye:
                deprint(_(u'No right and/or no left eye recorded in race %s, '
                          u'from mod %s') % (
                            record.full, modName))
                continue
            for eye in record.eyes:
                if eye in srcEyes:
                    eye_mesh[eye] = (record.rightEye.modPath.lower(),
                                     record.leftEye.modPath.lower())
        for tweak in self.enabledTweaks:
            tweak.scanModFile(modFile,progress,self.patchFile)

    def buildPatch(self,log,progress):
        """Updates races as needed."""
        debug = False
        extra = self.races_data
        if not self.isActive: return
        patchFile = self.patchFile
        keep = patchFile.getKeeper()
        if 'RACE' not in patchFile.tops: return
        racesPatched = []
        racesSorted = []
        racesFiltered = []
        mod_npcsFixed = {}
        reProcess = re.compile(
            ur'(?:dremora)|(?:akaos)|(?:lathulet)|(?:orthe)|(?:ranyu)',
            re.I | re.U)
        #--Import race info
        for race in patchFile.RACE.records:
            #~~print 'Building',race.eid
            raceData = self.raceData.get(race.fid,None)
            if not raceData: continue
            raceChanged = False
            #-- Racial Hair and  Eye sets
            if 'hairs' in raceData and (
                        set(race.hairs) != set(raceData['hairs'])):
                race.hairs = raceData['hairs']
                raceChanged = True
            if 'eyes' in raceData:
                if set(race.eyes) != set(raceData['eyes']):
                    race.eyes = raceData['eyes']
                    raceChanged = True
            #-- Eye paths:
            if 'rightEye' in raceData:
                if not race.rightEye:
                    deprint(_(
                        u'Very odd race %s found - no right eye assigned') %
                            race.full)
                else:
                    if race.rightEye.modPath != raceData['rightEye'].modPath:
                        race.rightEye.modPath = raceData['rightEye'].modPath
                        raceChanged = True
            if 'leftEye' in raceData:
                if not race.leftEye:
                    deprint(_(
                        u'Very odd race %s found - no left eye assigned') %
                            race.full)
                else:
                    if race.leftEye.modPath != raceData['leftEye'].modPath:
                        race.leftEye.modPath = raceData['leftEye'].modPath
                        raceChanged = True
            #--Teeth/Mouth/head/ears/description
            for key in ('teethLower', 'teethUpper', 'mouth', 'tongue', 'text',
                    'head'):
                if key in raceData:
                    if getattr(race,key) != raceData[key]:
                        setattr(race,key,raceData[key])
                        raceChanged = True
            #--spells
            if 'spellsOverride' in raceData:
                race.spells = raceData['spellsOverride']
            if 'AddSpells' in raceData:
                raceData['spells'] = race.spells
                for spell in raceData['AddSpells']:
                    raceData['spells'].append(spell)
                race.spells = raceData['spells']
            #--skills
            for key in self.raceSkills:
                if key in raceData:
                    if getattr(race,key) != raceData[key]:
                        setattr(race,key,raceData[key])
                        raceChanged = True
            #--Gender info (voice, gender specific body data)
            for gender in ('male','female'):
                bodyKeys = self.bodyKeys.union(self.raceAttributes.union(
                    {'Ears', 'Voice'}))
                bodyKeys = [gender+key for key in bodyKeys]
                for key in bodyKeys:
                    if key in raceData:
                        if getattr(race,key) != raceData[key]:
                            setattr(race,key,raceData[key])
                            raceChanged = True
            #--Relations
            if 'relations' in raceData:
                relations = raceData['relations']
                oldRelations = set((x.faction,x.mod) for x in race.relations)
                newRelations = set(relations.iteritems())
                if newRelations != oldRelations:
                    del race.relations[:]
                    for faction,mod in newRelations:
                        entry = MelObject()
                        entry.faction = faction
                        entry.mod = mod
                        race.relations.append(entry)
                    raceChanged = True
            #--Changed
            if raceChanged:
                racesPatched.append(race.eid)
                keep(race.fid)
        #--Eye Mesh filtering
        eye_mesh = self.eye_mesh
        try:
            blueEyeMesh = eye_mesh[(GPath(u'Oblivion.esm'),0x27308)]
        except KeyError:
            print u'error getting blue eye mesh:'
            print u'eye meshes:', eye_mesh
            raise
        argonianEyeMesh = eye_mesh[(GPath(u'Oblivion.esm'),0x3e91e)]
        if debug:
            print u'== Eye Mesh Filtering'
            print u'blueEyeMesh',blueEyeMesh
            print u'argonianEyeMesh',argonianEyeMesh
        for eye in (
            (GPath(u'Oblivion.esm'),0x1a), #--Reanimate
            (GPath(u'Oblivion.esm'),0x54bb9), #--Dark Seducer
            (GPath(u'Oblivion.esm'),0x54bba), #--Golden Saint
            (GPath(u'Oblivion.esm'),0x5fa43), #--Ordered
            ):
            eye_mesh.setdefault(eye,blueEyeMesh)
        def setRaceEyeMesh(race,rightPath,leftPath):
            race.rightEye.modPath = rightPath
            race.leftEye.modPath = leftPath
        for race in patchFile.RACE.records:
            if debug: print u'===', race.eid
            if not race.eyes: continue  #--Sheogorath. Assume is handled
            # correctly.
            if not race.rightEye or not race.leftEye: continue #--WIPZ race?
            if re.match(u'^117[a-zA-Z]', race.eid, flags=re.U): continue  #--
            #  x117 race?
            raceChanged = False
            mesh_eye = {}
            for eye in race.eyes:
                if eye not in eye_mesh:
                    deprint(
                        _(u'Mesh undefined for eye %s in race %s, eye removed '
                          u'from race list.') % (
                            strFid(eye), race.eid,))
                    continue
                mesh = eye_mesh[eye]
                if mesh not in mesh_eye:
                    mesh_eye[mesh] = []
                mesh_eye[mesh].append(eye)
            currentMesh = (
                race.rightEye.modPath.lower(), race.leftEye.modPath.lower())
            try:
                maxEyesMesh = \
                    sorted(mesh_eye.keys(), key=lambda a: len(mesh_eye[a]),
                           reverse=True)[0]
            except IndexError:
                maxEyesMesh = blueEyeMesh
            #--Single eye mesh, but doesn't match current mesh?
            if len(mesh_eye) == 1 and currentMesh != maxEyesMesh:
                setRaceEyeMesh(race,*maxEyesMesh)
                raceChanged = True
            #--Multiple eye meshes (and playable)?
            if debug:
                for mesh,eyes in mesh_eye.iteritems():
                    print mesh
                    for eye in eyes: print ' ',strFid(eye)
            if len(mesh_eye) > 1 and (race.flags.playable or race.fid == (
                    GPath('Oblivion.esm'), 0x038010)):
                #--If blueEyeMesh (mesh used for vanilla eyes) is present,
                # use that.
                if blueEyeMesh in mesh_eye and currentMesh != argonianEyeMesh:
                    setRaceEyeMesh(race,*blueEyeMesh)
                    race.eyes = mesh_eye[blueEyeMesh]
                    raceChanged = True
                elif argonianEyeMesh in mesh_eye:
                    setRaceEyeMesh(race,*argonianEyeMesh)
                    race.eyes = mesh_eye[argonianEyeMesh]
                    raceChanged = True
                #--Else figure that current eye mesh is the correct one
                elif currentMesh in mesh_eye:
                    race.eyes = mesh_eye[currentMesh]
                    raceChanged = True
                #--Else use most popular eye mesh
                else:
                    setRaceEyeMesh(race,*maxEyesMesh)
                    race.eyes = mesh_eye[maxEyesMesh]
                    raceChanged = True
            if raceChanged:
                racesFiltered.append(race.eid)
                keep(race.fid)
            if race.full:
                extra[race.full.lower()] = {'hairs': race.hairs,
                                            'eyes': race.eyes,
                                            'relations': race.relations}
        for tweak in self.enabledTweaks:
            tweak.buildPatch(progress,self.patchFile,extra)
        #--Sort Eyes/Hair
        defaultEyes = {}
        defaultMaleHair = {}
        defaultFemaleHair = {}
        eyeNames  = dict((x.fid,x.full) for x in patchFile.EYES.records)
        hairNames = dict((x.fid,x.full) for x in patchFile.HAIR.records)
        maleHairs = set(
            x.fid for x in patchFile.HAIR.records if not x.flags.notMale)
        femaleHairs = set(
            x.fid for x in patchFile.HAIR.records if not x.flags.notFemale)
        for race in patchFile.RACE.records:
            if (race.flags.playable or race.fid == (
                    GPath(u'Oblivion.esm'), 0x038010)) and race.eyes:
                defaultEyes[race.fid] = [x for x in
                                         bush.defaultEyes.get(race.fid,
                                             []) if x in race.eyes]
                if not defaultEyes[race.fid]:
                    defaultEyes[race.fid] = [race.eyes[0]]
                defaultMaleHair[race.fid] = [x for x in race.hairs if
                                             x in maleHairs]
                defaultFemaleHair[race.fid] = [x for x in race.hairs if
                                               x in femaleHairs]
                race.hairs.sort(key=lambda x: hairNames.get(x))
                race.eyes.sort(key=lambda x: eyeNames.get(x))
                racesSorted.append(race.eid)
                keep(race.fid)
        #--Npcs with unassigned eyes/hair
        for npc in patchFile.NPC_.records:
            if npc.fid == (GPath(u'Oblivion.esm'), 0x000007): continue  #
            # skip player
            if npc.full is not None and npc.race == (
                    GPath(u'Oblivion.esm'), 0x038010) and not reProcess.search(
                    npc.full): continue
            raceEyes = defaultEyes.get(npc.race)
            if not npc.eye and raceEyes:
                npc.eye = random.choice(raceEyes)
                srcMod = npc.fid[0]
                if srcMod not in mod_npcsFixed: mod_npcsFixed[srcMod] = set()
                mod_npcsFixed[srcMod].add(npc.fid)
                keep(npc.fid)
            raceHair = (
                (defaultMaleHair, defaultFemaleHair)[npc.flags.female]).get(
                npc.race)
            if not npc.hair and raceHair:
                npc.hair = random.choice(raceHair)
                srcMod = npc.fid[0]
                if srcMod not in mod_npcsFixed: mod_npcsFixed[srcMod] = set()
                mod_npcsFixed[srcMod].add(npc.fid)
                keep(npc.fid)
            if not npc.hairLength:
                npc.hairLength = random.random()
                srcMod = npc.fid[0]
                if srcMod not in mod_npcsFixed: mod_npcsFixed[srcMod] = set()
                keep(npc.fid)
                if npc.fid in mod_npcsFixed[srcMod]: continue
                mod_npcsFixed[srcMod].add(npc.fid)

        #--Done
        log.setHeader(u'= '+self.__class__.name)
        self._srcMods(log)
        log(u'\n=== '+_(u'Merged'))
        if not racesPatched:
            log(u'. ~~%s~~'%_(u'None'))
        else:
            for eid in sorted(racesPatched):
                log(u'* '+eid)
        log(u'\n=== '+_(u'Eyes/Hair Sorted'))
        if not racesSorted:
            log(u'. ~~%s~~'%_(u'None'))
        else:
            for eid in sorted(racesSorted):
                log(u'* '+eid)
        log(u'\n=== '+_(u'Eye Meshes Filtered'))
        if not racesFiltered:
            log(u'. ~~%s~~'%_(u'None'))
        else:
            log(_(u"In order to prevent 'googly eyes', incompatible eyes have "
                  u"been removed from the following races."))
            for eid in sorted(racesFiltered):
                log(u'* '+eid)
        if mod_npcsFixed:
            log(u'\n=== '+_(u'Eyes/Hair Assigned for NPCs'))
            for srcMod in sorted(mod_npcsFixed):
                log(u'* %s: %d' % (srcMod.s,len(mod_npcsFixed[srcMod])))
        for tweak in self.enabledTweaks:
            tweak._patchLog(log,tweak.count)

#-------------------------- CBash only RacePatchers --------------------------#
class CBash_RacePatcher_Relations(SpecialPatcher):
    """Merges changes to race relations."""
    autoKey = {'R.Relations'}
    iiMode = False
    allowUnloaded = True
    scanRequiresChecked = True
    applyRequiresChecked = False

    #--Config Phase -----------------------------------------------------------
    def initPatchFile(self,srcs,patchFile,loadMods):
        self.patchFile = patchFile
        self.srcs = srcs
        self.isActive = bool(srcs)
        if not self.isActive: return
        self.racesPatched = set()
        self.fid_faction_mod = {}

    def initData(self,group_patchers,progress):
        if not self.isActive: return
        for type in self.getTypes():
            group_patchers.setdefault(type,[]).append(self)

    def getTypes(self):
        return ['RACE']
    #--Patch Phase ------------------------------------------------------------
    def scan(self,modFile,record,bashTags):
        """Records information needed to apply the patch."""
        if bashTags & self.autoKey:
            relations = record.ConflictDetails(('relations_list',))
            if relations:
                self.fid_faction_mod.setdefault(record.fid, {}).update(
                    relations['relations_list'])

    def apply(self,modFile,record,bashTags):
        """Edits patch file as desired."""
        self.scan_more(modFile,record,bashTags)
        fid = record.fid
        if fid in self.fid_faction_mod:
            newRelations = set((faction, mod) for faction, mod in
                               self.fid_faction_mod[fid].iteritems() if
                               faction.ValidateFormID(self.patchFile))
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
                    self.racesPatched.add(record.eid)
                    record.UnloadRecord()
                    record._RecordID = override._RecordID

class CBash_RacePatcher_Imports(SpecialPatcher):
    """Imports various race fields."""
    autoKey = {'Hair', 'Body-M', 'Body-F', 'Voice-M', 'Voice-F', 'R.Teeth',
               'R.Mouth', 'R.Ears', 'R.Head', 'R.Attributes-F',
               'R.Attributes-M', 'R.Skills', 'R.Description', 'Body-Size-F',
               'Body-Size-M'}
    tag_attrs = {
        'Hair'  : ('hairs',),
        'Body-M': ('maleTail_list','maleUpperBodyPath','maleLowerBodyPath',
                   'maleHandPath','maleFootPath','maleTailPath'),
        'Body-F': ('femaleTail_list','femaleUpperBodyPath',
                   'femaleLowerBodyPath', 'femaleHandPath','femaleFootPath',
                   'femaleTailPath'),
        'Body-Size-M': ('maleHeight','maleWeight'),
        'Body-Size-F': ('femaleHeight','femaleWeight'),
        'Voice-M': ('maleVoice',),
        'Voice-F': ('femaleVoice',),
        'R.Teeth': ('teethLower_list','teethUpper_list',),
        'R.Mouth': ('mouth_list','tongue_list',),
        'R.Ears': ('maleEars_list','femaleEars_list',),
        'R.Head': ('head_list','fggs_p','fgga_p','fgts_p','snam_p'),
        'R.Attributes-M': ('maleStrength','maleIntelligence','maleWillpower',
                           'maleAgility','maleSpeed','maleEndurance',
                           'malePersonality','maleLuck'),
        'R.Attributes-F': ('femaleStrength','femaleIntelligence',
                           'femaleWillpower','femaleAgility','femaleSpeed',
                           'femaleEndurance','femalePersonality','femaleLuck'),
        'R.Skills': ('skill1','skill1Boost','skill2','skill2Boost','skill3',
                     'skill3Boost','skill4','skill4Boost','skill5',
                     'skill5Boost','skill6','skill6Boost','skill7',
                     'skill7Boost'),
        'R.Description': ('text',),
        }
    iiMode = False
    allowUnloaded = True
    scanRequiresChecked = True
    applyRequiresChecked = False

    #--Config Phase -----------------------------------------------------------
    def initPatchFile(self,srcs,patchFile,loadMods):
        self.patchFile = patchFile
        self.srcs = srcs
        self.isActive = bool(srcs)
        if not self.isActive: return
        self.racesPatched = set()
        self.fid_attr_value = {}

    def initData(self,group_patchers,progress):
        if not self.isActive: return
        for type in self.getTypes():
            group_patchers.setdefault(type,[]).append(self)

    def getTypes(self):
        return ['RACE']
    #--Patch Phase ------------------------------------------------------------
    def scan(self,modFile,record,bashTags):
        """Records information needed to apply the patch."""
        recordId = record.fid
        for bashKey in bashTags & self.autoKey:
            attrs = self.tag_attrs[bashKey]
            if bashKey == 'Hair':
                hairs = self.fid_attr_value.setdefault(recordId, {}).get(
                    'hairs', [])
                hairs.extend([hair for hair in record.hairs if
                              hair.ValidateFormID(
                                  self.patchFile) and hair not in hairs])
                attr_value = {'hairs':hairs}
            else:
                attr_value = record.ConflictDetails(attrs)
                if not ValidateDict(attr_value, self.patchFile):
                    mod_skipcount = \
                        self.patchFile.patcher_mod_skipcount.setdefault(
                        self.name, {})
                    mod_skipcount[modFile.GName] = mod_skipcount.setdefault(
                        modFile.GName, 0) + 1
                    continue
            self.fid_attr_value.setdefault(recordId,{}).update(attr_value)

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
                    self.racesPatched.add(record.eid)
                    record.UnloadRecord()
                    record._RecordID = override._RecordID

class CBash_RacePatcher_Spells(SpecialPatcher):
    """Merges changes to race spells."""
    autoKey = {'R.AddSpells', 'R.ChangeSpells'}
    iiMode = False
    allowUnloaded = True
    scanRequiresChecked = True
    applyRequiresChecked = False

    #--Config Phase -----------------------------------------------------------
    def initPatchFile(self,srcs,patchFile,loadMods):
        self.patchFile = patchFile
        self.srcs = srcs
        self.isActive = bool(srcs)
        if not self.isActive: return
        self.racesPatched = set()
        self.id_spells = {}

    def initData(self,group_patchers,progress):
        if not self.isActive: return
        for type in self.getTypes():
            group_patchers.setdefault(type,[]).append(self)

    def getTypes(self):
        return ['RACE']

    #--Patch Phase ------------------------------------------------------------
    def scan(self,modFile,record,bashTags):
        """Records information needed to apply the patch."""
        tags = bashTags & self.autoKey
        if tags:
            if 'R.ChangeSpells' in tags and 'R.AddSpells' in tags:
                raise BoltError(
                    u'WARNING mod %s has both R.AddSpells and R.ChangeSpells '
                    u'tags - only one of those tags should be on a mod at '
                    u'one time' % modFile.ModName)
            curSpells = set([spell for spell in record.spells if
                             spell.ValidateFormID(self.patchFile)])
            if curSpells:
                spells = self.id_spells.setdefault(record.fid,set())
                if 'R.ChangeSpells' in tags:
                    spells = curSpells
                elif 'R.AddSpells' in tags:
                    spells |= curSpells

    def apply(self,modFile,record,bashTags):
        """Edits patch file as desired."""
        self.scan_more(modFile,record,bashTags)
        recordId = record.fid
        if recordId in self.id_spells:
            newSpells = self.id_spells[recordId]
            curSpells = set(record.spells)
            changed = newSpells - curSpells
            if changed:
                override = record.CopyAsOverride(self.patchFile)
                if override:
                    override.spells = newSpells
                    self.racesPatched.add(record.eid)
                    record.UnloadRecord()
                    record._RecordID = override._RecordID

class CBash_RacePatcher_Eyes(SpecialPatcher):
    """Merges and filters changes to race eyes."""
    autoKey = {'Eyes-D', 'Eyes-R', 'Eyes-E', 'Eyes'}
    blueEye = FormID(GPath(u'Oblivion.esm'),0x27308)
    argonianEye = FormID(GPath(u'Oblivion.esm'),0x3e91e)
    dremoraRace = FormID(GPath(u'Oblivion.esm'),0x038010)
##    defaultMesh = (r'characters\imperial\eyerighthuman.nif',
#  r'characters\imperial\eyelefthuman.nif')
    reX117 = re.compile(u'^117[a-z]',re.I|re.U)
    iiMode = False
    allowUnloaded = True
    scanRequiresChecked = False
    applyRequiresChecked = False

    #--Config Phase -----------------------------------------------------------
    def initPatchFile(self,srcs,patchFile,loadMods):
        self.patchFile = patchFile
        self.srcs = srcs
        self.isActive = True #--Always partially enabled to support eye
        # filtering
        self.racesPatched = set()
        self.racesSorted = set()
        self.racesFiltered = []
        self.mod_npcsFixed = {}
        self.hairNames = {}
        self.eyeNames = {}
        self.maleHairs = set()
        self.femaleHairs = set()
        self.id_meshes = {}
        self.id_eyes = {}
        self.srcEyes = {}
        self.eye_meshes = {}
        self.finishedOnce = False

    def initData(self,group_patchers,progress):
        if not self.isActive: return
        for type in self.getTypes():
            group_patchers.setdefault(type,[]).append(self)

    def getTypes(self):
        return ['EYES','HAIR','RACE']

    #--Patch Phase ------------------------------------------------------------
    def scan(self,modFile,record,bashTags):
        """Records information needed to apply the patch."""
        recordId = record.fid
        if record._Type == 'RACE':
            if record.IsWinning():
                if record.full:
                    self.patchFile.races_data[record.full.lower()] = {
                        'hairs': record.hairs, 'eyes': record.eyes,
                        'relations': record.relations}
            eye_meshes = self.eye_meshes
            srcEyes = self.srcEyes.get(modFile.GName,set())
            curEyes = set([eye for eye in record.eyes if
                           eye.ValidateFormID(self.patchFile)])
            eyePaths = (record.rightEye.modPath, record.leftEye.modPath)
            for eye in curEyes:
                # only map eyes that are (re)defined in this mod
                if eye not in eye_meshes or eye in srcEyes:
                    eye_meshes[eye] = eyePaths
            if modFile.GName in self.srcs and self.autoKey & bashTags:
                allEyes = self.id_eyes.setdefault(recordId,set())
                allEyes |= curEyes
                self.id_meshes[recordId] = eyePaths
        else:
            if not recordId.ValidateFormID(self.patchFile):
                mod_skipcount = self.patchFile.patcher_mod_skipcount\
                    .setdefault(self.name, {})
                mod_skipcount[modFile.GName] = mod_skipcount.setdefault(
                    modFile.GName, 0) + 1
                return

            if record._Type == 'HAIR':
                self.patchFile.races_data['HAIR'].append(recordId)
                if record.IsMale:
                    self.maleHairs.add(recordId)
                else:
                    self.femaleHairs.add(recordId)
                self.hairNames.update({recordId:record.full})
            else: #record._Type == 'EYES'
                self.patchFile.races_data['EYES'].append(recordId)
                self.eyeNames.update({recordId:record.full})
                self.srcEyes.setdefault(modFile.GName,set()).add(recordId)

    def apply(self,modFile,record,bashTags):
        """Edits patch file as desired."""
        self.scan(modFile,record,bashTags)
        if record._Type in ('HAIR','EYES'):
            return

        recordId = record.fid
        if self.isActive and (recordId in self.id_eyes):
            curEyes = set(record.eyes)
            newEyes = self.id_eyes[recordId]
            changed = newEyes - curEyes
            if not changed:
                newRightEye, newLeftEye = self.id_meshes[recordId]
                curRightEye, curLeftEye = (
                    record.rightEye.modPath, record.leftEye.modPath)
                changed = (newRightEye, newLeftEye) != \
                          (curRightEye, curLeftEye) #modPaths do case
                          #  insensitive comparison by default
            if changed:
                override = record.CopyAsOverride(self.patchFile)
                if override:
                    override.eyes = newEyes
                    override.rightEye.modPath, override.leftEye.modPath = \
                        self.id_meshes[recordId]
                    self.racesPatched.add(record.eid)
                    record.UnloadRecord()
                    record._RecordID = override._RecordID

    def finishPatch(self,patchFile,progress):
        """Edits the bashed patch file directly."""
        #The patcher gets registered multiple times due to the multiple
        # getTypes
        #This ensures the finishPatch only runs once per bashed patch
        if self.finishedOnce: return
        self.finishedOnce = True
        racesSorted = self.racesSorted
        racesFiltered = self.racesFiltered
        mod_npcsFixed = self.mod_npcsFixed
        Current = patchFile.Current
        subProgress = SubProgress(progress)
        subProgress.setFull(max(len(Current.LoadOrderMods) * 2,1))
        reX117 = self.reX117
        defaultEyes = {}
        defaultMaleHair = {}
        defaultFemaleHair = {}
        hairNames = self.hairNames
        eyeNames = self.eyeNames
        maleHairs = self.maleHairs
        femaleHairs = self.femaleHairs
        playableRaces = {self.dremoraRace}

        #--Eye Mesh filtering
        eye_meshes = self.eye_meshes
        try:
            blueEyeMeshes = eye_meshes[self.blueEye]
        except KeyError:
            print _(
                u"Wrye Bash is low on memory and cannot complete building "
                u"the patch. This will likely succeed if you restart Wrye "
                u"Bash and try again. If it fails repeatedly, please report "
                u"it at the current official Wrye Bash thread at "
                u"http://forums.bethsoft.com/index.php?/forum/25-mods/. We "
                u"apologize for the inconvenience.")
            return
        try:
            argonianEyeMeshes = eye_meshes[self.argonianEye]
        except KeyError:
            print _(
                u"Wrye Bash is low on memory and cannot complete building "
                u"the patch. This will likely succeed if you restart Wrye "
                u"Bash and try again. If it fails repeatedly, please report "
                u"it at the current official Wrye Bash thread at "
                u"http://forums.bethsoft.com/index.php?/forum/25-mods/. We "
                u"apologize for the inconvenience.")
            return
        fixedRaces = set()
        fixedNPCs = {
        FormID(GPath(u'Oblivion.esm'), 0x000007)}  #causes player to be skipped
        for eye in (
            FormID(GPath(u'Oblivion.esm'),0x1a), #--Reanimate
            FormID(GPath(u'Oblivion.esm'),0x54bb9), #--Dark Seducer
            FormID(GPath(u'Oblivion.esm'),0x54bba), #--Golden Saint
            FormID(GPath(u'Oblivion.esm'),0x5fa43), #--Ordered
            self.dremoraRace,
            ):
            eye_meshes.setdefault(eye,blueEyeMeshes)
        def setRaceEyeMesh(race,rightPath,leftPath):
            race.rightEye.modPath = rightPath
            race.leftEye.modPath = leftPath
        #Scan hairs and eyes for later sorting and/or assigning to non-haired
        # npcs
        pstate = 0
        noEyes = 0
        noHair = 0
        for modFile in Current.LoadOrderMods:
            subProgress(pstate, _(u'Filtering eyes...')+u'\n')
            for race in modFile.RACE:
                recordId = race.fid
                if race.IsPlayable:
                    playableRaces.add(recordId)
                currentEyes = race.eyes
                if not currentEyes: continue  #--Sheogorath. Assume is
                # handled correctly.
                if not race.rightEye or not race.leftEye: continue  # no eye
                #  set for either right or left... skip.
                curRightEye, curLeftEye = race.rightEye.modPath, \
                                          race.leftEye.modPath
                if not curRightEye or not curLeftEye: continue  # --WIPZ race?
                if reX117.match(race.eid): continue  #-- x117 race?
                if recordId in fixedRaces: continue  #--already processed
                # once (added to patchFile, and now the patchFile is being
                # processed)
                #IsNewest
                if race.IsWinning():
                    raceChanged = False
                    currentMeshes = (curRightEye, curLeftEye)
                    meshes_eyes = {}
                    for eye in currentEyes:
                        if eye not in eye_meshes:
                            deprint(
                                _(u'Mesh undefined for eye %s in race %s') % (
                                    eye, race.eid))
                            continue
                        rightEye, leftEye = eye_meshes[eye]
                        meshes_eyes.setdefault((rightEye, leftEye), []).append(
                            eye)
                    try:
                        maxEyesMeshes = sorted(meshes_eyes.keys(),
                                               key=lambda a: len(
                                                   meshes_eyes[a]),
                                               reverse=True)[0]
                    except IndexError:
                        maxEyesMeshes = blueEyeMeshes
                    meshesCount = len(meshes_eyes)
                    #--Single eye mesh, but doesn't match current mesh?
                    if meshesCount == 1 and currentMeshes != maxEyesMeshes:
                        currentMeshes = maxEyesMeshes
                        currentEyes = meshes_eyes[maxEyesMeshes]
                        raceChanged = True
                    #--Multiple eye meshes (and playable)?
                    elif meshesCount > 1 and recordId in playableRaces:
                        #--If blueEyeMesh (mesh used for vanilla eyes) is
                        # present, use that.
                        if blueEyeMeshes in meshes_eyes and currentMeshes !=\
                                argonianEyeMeshes:
                            currentMeshes = blueEyeMeshes
                            currentEyes = meshes_eyes[blueEyeMeshes]
                            raceChanged = True
                        elif argonianEyeMeshes in meshes_eyes:
                            currentMeshes = argonianEyeMeshes
                            currentEyes = meshes_eyes[argonianEyeMeshes]
                            raceChanged = True
                        #--Else figure that current eye mesh is the correct one
                        elif currentMeshes in meshes_eyes:
                            currentEyes = meshes_eyes[currentMeshes]
                            raceChanged = True
                        #--Else use most popular eye mesh
                        else:
                            currentMeshes = maxEyesMeshes
                            currentEyes = meshes_eyes[maxEyesMeshes]
                            raceChanged = True
                    if raceChanged:
                        racesFiltered.append(race.eid)

                    #--Sort Eyes/Hair
                    oldHairs = race.hairs
                    currentHairs = oldHairs
                    if recordId in playableRaces:
                        currentHairs = sorted(oldHairs,
                                              key=lambda x: hairNames.get(x))
                        if currentHairs != oldHairs:
                            racesSorted.add(race.eid)
                            raceChanged = True
                        oldEyes = currentEyes
                        currentEyes = sorted(oldEyes,
                                             key=lambda x: eyeNames.get(x))
                        if currentEyes != oldEyes:
                            racesSorted.add(race.eid)
                            raceChanged = True
                        defaultEyes[recordId] = [
                            x for x in bush.defaultEyes.get(recordId, [])
                            if x in currentEyes] or currentEyes
                        defaultMaleHair[recordId] = [x for x in currentHairs if
                                                     x in maleHairs]
                        defaultFemaleHair[recordId] = [x for x in currentHairs
                                                       if x in femaleHairs]

                    if raceChanged:
                        fixedRaces.add(recordId)
                        override = race.CopyAsOverride(patchFile)
                        if override:
                            override.eyes = currentEyes
                            override.hairs = currentHairs
                            override.rightEye.modPath, \
                            override.leftEye.modPath = currentMeshes
                race.UnloadRecord()
            pstate += 1
        for modFile in Current.LoadOrderMods:
            #--Npcs with unassigned eyes/hair
            #--Must run after all race records have been processed
            subProgress(pstate, _(
                u'Assigning random eyes and hairs to npcs missing them...')
                        + u'\n')
            reProcess = re.compile(
                ur'(?:dremora)|(?:akaos)|(?:lathulet)|(?:orthe)|(?:ranyu)',
                re.I | re.U)
            for npc in modFile.NPC_:
                recordId = npc.fid
                if recordId in fixedNPCs: continue  #--already processed
                # once (added to patchFile, and now the patchFile is being
                # processed)
                raceId = npc.race
                if raceId not in playableRaces: continue
                if npc.full is not None and raceId == self.dremoraRace and \
                        not reProcess.search(
                        npc.full): continue  # So as not to give OOO's
                # spectral warriors different hairs/eyes since they are
                # dremora race.
                #IsNewest
                if npc.IsWinning():
                    npcChanged = False
                    raceEyes = defaultEyes.get(raceId)
                    eye = npc.eye
                    if eye is None and raceEyes:
                        eye = random.choice(raceEyes)
                        npcChanged = True
                    raceHair = ((defaultMaleHair, defaultFemaleHair)[
                            npc.IsFemale]).get(raceId)
                    hair = npc.hair
                    if hair is None and raceHair:
                        hair = random.choice(raceHair)
                        npcChanged = True
                    if npcChanged:
                        fixedNPCs.add(recordId)
                        override = npc.CopyAsOverride(patchFile)
                        if override:
                            override.eye = eye
                            override.hair = hair
                            if not override.hairLength:
                                override.hairLength = random.random()
                            mod_npcsFixed.setdefault(modFile.GName, set()).add(
                                recordId)
                npc.UnloadRecord()
            pstate += 1

class CBash_RacePatcher(SpecialPatcher, CBash_DoublePatcher):
    """Merged leveled lists mod file."""
    name = _(u'Race Records')
    text = (_(u"Merge race eyes, hair, body, voice from ACTIVE AND/OR MERGED"
              u" mods.  Any non-active, non-merged mods in the following list"
              u" will be IGNORED.") + u'\n\n' +
            _(u"Even if none of the below mods are checked, this will sort"
              u" hairs and eyes and attempt to remove googly eyes from all"
              u" active mods.  It will also randomly assign hairs and eyes to"
              u" npcs that are otherwise missing them.")
            )
    tip = _(u"Merge race eyes, hair, body, voice from mods.")
    autoRe = re.compile(ur'^UNDEFINED$',re.I|re.U)
    autoKey = {'Hair', 'Eyes-D', 'Eyes-R', 'Eyes-E', 'Eyes', 'Body-M',
               'Body-F', 'Voice-M', 'Voice-F', 'R.Relations', 'R.Teeth',
               'R.Mouth', 'R.Ears', 'R.Head', 'R.Attributes-F',
               'R.Attributes-M', 'R.Skills', 'R.Description', 'R.AddSpells',
               'R.ChangeSpells', 'Body-Size-M', 'Body-Size-F'}
    forceAuto = True
    tweakers = [
        CBash_RacePatcher_Relations(),
        CBash_RacePatcher_Imports(),
        CBash_RacePatcher_Spells(),
        CBash_RacePatcher_Eyes(),
        ]
    subLabel = _(u'Race Tweaks')
    tweaks = sorted([
        CBash_RaceTweaker_BiggerOrcsAndNords(),
        CBash_RaceTweaker_PlayableHairs(),
        CBash_RaceTweaker_PlayableEyes(),
        CBash_RaceTweaker_SexlessHairs(),
        CBash_RaceTweaker_MergeSimilarRaceHairs(),
        CBash_RaceTweaker_MergeSimilarRaceEyes(),
        CBash_RaceTweaker_AllEyes(),
        CBash_RaceTweaker_AllHairs(),
        ],key=lambda a: a.label.lower())

    #--Config Phase -----------------------------------------------------------
    def initPatchFile(self,patchFile,loadMods):
        super(CBash_RacePatcher, self).initPatchFile(patchFile, loadMods)
        #This single tweak is broken into several parts to make it easier to
        # manage
        #Each part is a group of tags that are processed similarly
        for tweak in self.tweakers:
            tweak.initPatchFile(self.srcs,patchFile,loadMods)
        for tweak in self.tweaks:
            tweak.patchFile = patchFile

    def initData(self,group_patchers,progress):
        for tweak in self.tweakers:
            tweak.initData(group_patchers,progress)
        for tweak in self.enabledTweaks:
            for type in tweak.getTypes():
                group_patchers.setdefault(type,[]).append(tweak)

    #--Patch Phase ------------------------------------------------------------
    def buildPatchLog(self,log):
        """Will write to log."""
        racesPatched = set()
        racesSorted = set()
        racesFiltered = []
        mod_npcsFixed = {}
        for tweak in self.tweakers:
            if hasattr(tweak, 'racesPatched'):
                racesPatched |= tweak.racesPatched
            if hasattr(tweak, 'racesSorted'):
                racesSorted |= tweak.racesSorted
            if hasattr(tweak, 'racesFiltered'):
                racesFiltered += tweak.racesFiltered
            if hasattr(tweak, 'mod_npcsFixed'):
                mod_npcsFixed.update(tweak.mod_npcsFixed)
        #--Done
        log.setHeader(u'= '+self.__class__.name)
        self._srcMods(log)
        log(u'\n=== '+_(u'Merged'))

        if not racesPatched:
            log(u'. ~~%s~~'%_(u'None'))
        else:
            for eid in sorted(racesPatched):
                log(u'* '+eid)
        log(u'\n=== '+_(u'Eyes/Hair Sorted'))
        if not racesSorted:
            log(u'. ~~%s~~'%_(u'None'))
        else:
            for eid in sorted(racesSorted):
                log(u'* '+eid)
        log(u'\n=== '+_(u'Eye Meshes Filtered'))
        if not racesFiltered:
            log(u'. ~~%s~~'%_(u'None'))
        else:
            log(_(u"In order to prevent 'googly eyes', incompatible eyes have "
                  u"been removed from the following races."))
            for eid in sorted(racesFiltered):
                log(u'* '+eid)
        if mod_npcsFixed:
            log(u'\n=== '+_(u'Eyes/Hair Assigned for NPCs'))
            for srcMod in sorted(mod_npcsFixed):
                if srcMod.cext == u'.tmp':
                    name = srcMod.sbody
                else:
                    name = srcMod.s
                log(u'* %s: %d' % (name,len(mod_npcsFixed[srcMod])))
        for tweak in self.enabledTweaks:
            tweak.buildPatchLog(log)
