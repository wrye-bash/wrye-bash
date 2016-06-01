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

"""This module contains oblivion multitweak item patcher classes that belong
to the Assorted Multitweaker - as well as the AssortedTweaker itself."""

import random
import re
# Internal
from ...bolt import GPath
from ...brec import MreRecord
from ... import load_order
from ... import bush # from ....bush import game ? # should be set by now !
from ...cint import MGEFCode
from ...patcher.base import AMultiTweakItem
from ...patcher.patchers.base import MultiTweakItem, CBash_MultiTweakItem
from ...patcher.patchers.base import MultiTweaker, CBash_MultiTweaker

# Patchers: 30 ----------------------------------------------------------------
class AssortedTweak_ArmorShows(MultiTweakItem):
    """Fix armor to show amulets/rings."""

    #--Config Phase -----------------------------------------------------------
    def __init__(self,label,tip,key):
        super(AssortedTweak_ArmorShows, self).__init__(label,tip,key)
        self.hidesBit = {u'armorShowsRings':16,u'armorShowsAmulets':17}[key]
        self.logMsg = u'* '+_(u'Armor Pieces Tweaked') + u': %d'

    #--Patch Phase ------------------------------------------------------------
    def getReadClasses(self):
        """Returns load factory classes needed for reading."""
        return 'ARMO',

    def getWriteClasses(self):
        """Returns load factory classes needed for writing."""
        return 'ARMO',

    def scanModFile(self,modFile,progress,patchFile):
        mapper = modFile.getLongMapper()
        patchRecords = patchFile.ARMO
        hidesBit = self.hidesBit
        for record in modFile.ARMO.getActiveRecords():
            if record.flags[hidesBit] and not record.flags.notPlayable:
                record = record.getTypeCopy(mapper)
                patchRecords.setRecord(record)

    def buildPatch(self,log,progress,patchFile):
        """Edits patch file as desired. Will write to log."""
        count = {}
        keep = patchFile.getKeeper()
        hidesBit = self.hidesBit
        for record in patchFile.ARMO.records:
            if record.flags[hidesBit] and not record.flags.notPlayable:
                record.flags[hidesBit] = False
                keep(record.fid)
                srcMod = record.fid[0]
                count[srcMod] = count.get(srcMod,0) + 1
        self._patchLog(log,count)

class CBash_AssortedTweak_ArmorShows(CBash_MultiTweakItem):
    """Fix armor to show amulets/rings."""
    name = _(u'Armor Tweaks')

    #--Config Phase -----------------------------------------------------------
    def __init__(self,label,tip,key):
        super(CBash_AssortedTweak_ArmorShows, self).__init__(label,tip,key)
        self.hideFlag = {u'armorShowsRings': 'IsHideRings',
                         u'armorShowsAmulets': 'IsHideAmulets'}[key]
        self.logMsg = u'* '+_(u'Armor Pieces Tweaked') + u': %d'

    def getTypes(self):
        """Returns the group types that this patcher checks"""
        return ['ARMO']
    #--Patch Phase ------------------------------------------------------------
    def apply(self,modFile,record,bashTags):
        """Edits patch file as desired."""
        if record.IsNonPlayable:
            return
        if getattr(record, self.hideFlag):
            override = record.CopyAsOverride(self.patchFile)
            if override:
                setattr(override, self.hideFlag, False)
                mod_count = self.mod_count
                mod_count[modFile.GName] = mod_count.get(modFile.GName,0) + 1
                record.UnloadRecord()
                record._RecordID = override._RecordID

#------------------------------------------------------------------------------
class AssortedTweak_ClothingShows(MultiTweakItem):
    """Fix robes, gloves and the like to show amulets/rings."""

    #--Config Phase -----------------------------------------------------------
    def __init__(self,label,tip,key):
        super(AssortedTweak_ClothingShows, self).__init__(label,tip,key)
        self.hidesBit = \
            {u'ClothingShowsRings': 16, u'ClothingShowsAmulets': 17}[key]
        self.logMsg = u'* '+_(u'Clothing Pieces Tweaked') + u': %d'

    #--Patch Phase ------------------------------------------------------------
    def getReadClasses(self):
        """Returns load factory classes needed for reading."""
        return 'CLOT',

    def getWriteClasses(self):
        """Returns load factory classes needed for writing."""
        return 'CLOT',

    def scanModFile(self,modFile,progress,patchFile):
        mapper = modFile.getLongMapper()
        patchRecords = patchFile.CLOT
        hidesBit = self.hidesBit
        for record in modFile.CLOT.getActiveRecords():
            if record.flags[hidesBit] and not record.flags.notPlayable:
                record = record.getTypeCopy(mapper)
                patchRecords.setRecord(record)

    def buildPatch(self,log,progress,patchFile):
        """Edits patch file as desired. Will write to log."""
        count = {}
        keep = patchFile.getKeeper()
        hidesBit = self.hidesBit
        for record in patchFile.CLOT.records:
            if record.flags[hidesBit] and not record.flags.notPlayable:
                record.flags[hidesBit] = False
                keep(record.fid)
                srcMod = record.fid[0]
                count[srcMod] = count.get(srcMod,0) + 1
        self._patchLog(log,count)

class CBash_AssortedTweak_ClothingShows(CBash_MultiTweakItem):
    """Fix robes, gloves and the like to show amulets/rings."""
    name = _(u'Clothing Tweaks')

    #--Config Phase -----------------------------------------------------------
    def __init__(self,label,tip,key):
        super(CBash_AssortedTweak_ClothingShows, self).__init__(label,tip,key)
        self.hideFlag = {u'ClothingShowsRings': 'IsHideRings',
                         u'ClothingShowsAmulets': 'IsHideAmulets'}[key]
        self.logMsg = u'* '+_(u'Clothing Pieces Tweaked') + u': %d'

    def getTypes(self):
        return ['CLOT']

    #--Patch Phase ------------------------------------------------------------
    def apply(self,modFile,record,bashTags):
        """Edits patch file as desired."""
        if record.IsNonPlayable:
            return
        if getattr(record, self.hideFlag):
            override = record.CopyAsOverride(self.patchFile)
            if override:
                setattr(override, self.hideFlag, False)
                mod_count = self.mod_count
                mod_count[modFile.GName] = mod_count.get(modFile.GName,0) + 1
                record.UnloadRecord()
                record._RecordID = override._RecordID

#------------------------------------------------------------------------------
class AAssortedTweak_BowReach(AMultiTweakItem):
    """Fix bows to have reach = 1.0."""

    #--Config Phase -----------------------------------------------------------
    def __init__(self):
        super(AAssortedTweak_BowReach, self).__init__(_(u"Bow Reach Fix"),
            _(u'Fix bows with zero reach. (Zero reach causes CTDs.)'),
            u'BowReach',
            (u'1.0',  u'1.0'),
            )
        self.defaultEnabled = True
        self.logMsg = u'* '+_(u'Bows fixed') + u': %d'

class AssortedTweak_BowReach(AAssortedTweak_BowReach,MultiTweakItem):
    #--Patch Phase ------------------------------------------------------------
    def getReadClasses(self):
        """Returns load factory classes needed for reading."""
        return 'WEAP',

    def getWriteClasses(self):
        """Returns load factory classes needed for writing."""
        return 'WEAP',

    def scanModFile(self,modFile,progress,patchFile):
        mapper = modFile.getLongMapper()
        patchRecords = patchFile.WEAP
        for record in modFile.WEAP.getActiveRecords():
            if record.weaponType == 5 and record.reach <= 0:
                record = record.getTypeCopy(mapper)
                patchRecords.setRecord(record)

    def buildPatch(self,log,progress,patchFile):
        """Edits patch file as desired. Will write to log."""
        count = {}
        keep = patchFile.getKeeper()
        for record in patchFile.WEAP.records:
            if record.weaponType == 5 and record.reach <= 0:
                record.reach = 1
                keep(record.fid)
                srcMod = record.fid[0]
                count[srcMod] = count.get(srcMod,0) + 1
        self._patchLog(log,count)

class CBash_AssortedTweak_BowReach(AAssortedTweak_BowReach,
                                   CBash_MultiTweakItem):
    name = _(u'Bow Reach Fix')

    #--Config Phase -----------------------------------------------------------
    def getTypes(self):
        return ['WEAP']

    #--Patch Phase ------------------------------------------------------------
    def apply(self,modFile,record,bashTags):
        """Edits patch file as desired."""
        if record.IsBow and record.reach <= 0:
            override = record.CopyAsOverride(self.patchFile)
            if override:
                override.reach = 1.0
                mod_count = self.mod_count
                mod_count[modFile.GName] = mod_count.get(modFile.GName,0) + 1
                record.UnloadRecord()
                record._RecordID = override._RecordID

#------------------------------------------------------------------------------
class AAssortedTweak_SkyrimStyleWeapons(AMultiTweakItem):
    """Sets all one handed weapons as blades, two handed weapons as blunt."""

    #--Config Phase -----------------------------------------------------------
    def __init__(self):
        super(AAssortedTweak_SkyrimStyleWeapons, self).__init__(
            _(u"Skyrim-style Weapons"),
            _(u'Sets all one handed weapons as blades, two handed weapons '
              u'as blunt.'), u'skyrimweaponsstyle', (u'1.0', u'1.0'), )
        self.logMsg = u'* '+_(u'Weapons Adjusted') + u': %d'

class AssortedTweak_SkyrimStyleWeapons(AAssortedTweak_SkyrimStyleWeapons,
                                       MultiTweakItem):
    #--Patch Phase ------------------------------------------------------------
    def getReadClasses(self):
        """Returns load factory classes needed for reading."""
        return 'WEAP',

    def getWriteClasses(self):
        """Returns load factory classes needed for writing."""
        return 'WEAP',

    def scanModFile(self,modFile,progress,patchFile):
        mapper = modFile.getLongMapper()
        patchRecords = patchFile.WEAP
        for record in modFile.WEAP.getActiveRecords():
            if record.weaponType in [1,2]:
                record = record.getTypeCopy(mapper)
                patchRecords.setRecord(record)

    def buildPatch(self,log,progress,patchFile):
        """Edits patch file as desired. Will write to log."""
        count = {}
        keep = patchFile.getKeeper()
        for record in patchFile.WEAP.records:
            if record.weaponType == 1:
                record.weaponType = 3
                keep(record.fid)
                srcMod = record.fid[0]
                count[srcMod] = count.get(srcMod,0) + 1
            elif record.weaponType == 2:
                record.weaponType = 0
                keep(record.fid)
                srcMod = record.fid[0]
                count[srcMod] = count.get(srcMod,0) + 1
        self._patchLog(log,count)

class CBash_AssortedTweak_SkyrimStyleWeapons(AAssortedTweak_SkyrimStyleWeapons,
                                             CBash_MultiTweakItem):
    name = _(u'Skyrim-style Weapons')

    #--Config Phase -----------------------------------------------------------
    def getTypes(self):
        return ['WEAP']

    #--Patch Phase ------------------------------------------------------------
    def apply(self,modFile,record,bashTags):
        """Edits patch file as desired."""
        if record.IsBlade2Hand or record.IsBlunt1Hand:
            override = record.CopyAsOverride(self.patchFile)
            if override:
                if override.IsBlade2Hand:
                    override.IsBlunt2Hand = True
                else:
                    override.IsBlade1Hand = True
                mod_count = self.mod_count
                mod_count[modFile.GName] = mod_count.get(modFile.GName,0) + 1
                record.UnloadRecord()
                record._RecordID = override._RecordID

#------------------------------------------------------------------------------
class AAssortedTweak_ConsistentRings(AMultiTweakItem):
    """Sets rings to all work on same finger."""

    #--Config Phase -----------------------------------------------------------
    def __init__(self):
        super(AAssortedTweak_ConsistentRings, self).__init__(
            _(u"Right Hand Rings"),
            _(u'Fixes rings to unequip consistently by making them prefer '
              u'the right hand.'), u'ConsistentRings', (u'1.0', u'1.0'), )
        self.defaultEnabled = True
        self.logMsg = u'* '+_(u'Rings fixed') + u': %d'

class AssortedTweak_ConsistentRings(AAssortedTweak_ConsistentRings,
                                    MultiTweakItem):

    #--Patch Phase ------------------------------------------------------------
    def getReadClasses(self):
        """Returns load factory classes needed for reading."""
        return 'CLOT',

    def getWriteClasses(self):
        """Returns load factory classes needed for writing."""
        return 'CLOT',

    def scanModFile(self,modFile,progress,patchFile):
        mapper = modFile.getLongMapper()
        patchRecords = patchFile.CLOT
        for record in modFile.CLOT.getActiveRecords():
            if record.flags.leftRing:
                record = record.getTypeCopy(mapper)
                patchRecords.setRecord(record)

    def buildPatch(self,log,progress,patchFile):
        """Edits patch file as desired. Will write to log."""
        count = {}
        keep = patchFile.getKeeper()
        for record in patchFile.CLOT.records:
            if record.flags.leftRing:
                record.flags.leftRing = False
                record.flags.rightRing = True
                keep(record.fid)
                srcMod = record.fid[0]
                count[srcMod] = count.get(srcMod,0) + 1
        self._patchLog(log,count)

class CBash_AssortedTweak_ConsistentRings(AAssortedTweak_ConsistentRings,
                                          CBash_MultiTweakItem):
    name = _(u'Right Hand Rings')

    #--Config Phase -----------------------------------------------------------
    def getTypes(self):
        return ['CLOT']

    #--Patch Phase ------------------------------------------------------------
    def apply(self,modFile,record,bashTags):
        """Edits patch file as desired. """
        if record.IsLeftRing:
            override = record.CopyAsOverride(self.patchFile)
            if override:
                override.IsLeftRing = False
                override.IsRightRing = True
                mod_count = self.mod_count
                mod_count[modFile.GName] = mod_count.get(modFile.GName,0) + 1
                record.UnloadRecord()
                record._RecordID = override._RecordID
#------------------------------------------------------------------------------
rePlayableSkips = re.compile(
    ur'(?:skin)|(?:test)|(?:mark)|(?:token)|(?:willful)|(?:see.*me)|('
    ur'?:werewolf)|(?:no wings)|(?:tsaesci tail)|(?:widget)|(?:dummy)|('
    ur'?:ghostly immobility)|(?:corpse)', re.I)

class AAssortedTweak_ClothingPlayable(AMultiTweakItem):
    """Sets all clothes to playable"""

    #--Config Phase -----------------------------------------------------------
    def __init__(self):
        super(AAssortedTweak_ClothingPlayable, self).__init__(
            _(u"All Clothing Playable"),
            _(u'Sets all clothing to be playable.'), u'PlayableClothing',
            (u'1.0', u'1.0'), )
        self.logHeader = u'=== '+_(u'Playable Clothes')
        self.logMsg = u'* '+_(u'Clothes set as playable') + u': %d'

class AssortedTweak_ClothingPlayable(AAssortedTweak_ClothingPlayable,
                                     MultiTweakItem):

    #--Patch Phase ------------------------------------------------------------
    def getReadClasses(self):
        """Returns load factory classes needed for reading."""
        return 'CLOT',

    def getWriteClasses(self):
        """Returns load factory classes needed for writing."""
        return 'CLOT',

    def scanModFile(self,modFile,progress,patchFile):
        mapper = modFile.getLongMapper()
        patchRecords = patchFile.CLOT
        for record in modFile.CLOT.getActiveRecords():
            if record.flags.notPlayable:
                record = record.getTypeCopy(mapper)
                patchRecords.setRecord(record)

    def buildPatch(self,log,progress,patchFile):
        """Edits patch file as desired. Will write to log."""
        count = {}
        keep = patchFile.getKeeper()
        for record in patchFile.CLOT.records:
            if record.flags.notPlayable:
                full = record.full
                if not full: continue
                if record.script: continue
                if rePlayableSkips.search(full): continue  # probably truly
                # shouldn't be playable
                # If only the right ring and no other body flags probably a
                # token that wasn't zeroed (which there are a lot of).
                if record.flags.leftRing != 0 or record.flags.foot != 0 or \
                                record.flags.hand != 0 or \
                                record.flags.amulet != 0 or \
                                record.flags.lowerBody != 0 or \
                                record.flags.upperBody != 0 or \
                                record.flags.head != 0 or record.flags.hair \
                        != 0 or record.flags.tail != 0:
                    record.flags.notPlayable = 0
                    keep(record.fid)
                    srcMod = record.fid[0]
                    count[srcMod] = count.get(srcMod,0) + 1
        self._patchLog(log,count)

class CBash_AssortedTweak_ClothingPlayable(AAssortedTweak_ClothingPlayable,
                                           CBash_MultiTweakItem):
    scanOrder = 29 #Run before the show clothing tweaks
    editOrder = 29
    name = _(u'Playable Clothes')

    #--Config Phase -----------------------------------------------------------
    def getTypes(self):
        return ['CLOT']

    #--Patch Phase ------------------------------------------------------------
    def apply(self,modFile,record,bashTags):
        """Edits patch file as desired. """
        if record.IsNonPlayable:
            full = record.full
            if not full: return
            if record.script: return
            if rePlayableSkips.search(full): return  # probably truly
            # shouldn't be playable
            # If only the right ring and no other body flags probably a
            # token that wasn't zeroed (which there are a lot of).
            if record.IsLeftRing or record.IsFoot or record.IsHand or \
                    record.IsAmulet or record.IsLowerBody or \
                    record.IsUpperBody or record.IsHead or record.IsHair or \
                    record.IsTail:
                override = record.CopyAsOverride(self.patchFile)
                if override:
                    override.IsNonPlayable = False
                    mod_count = self.mod_count
                    mod_count[modFile.GName] = mod_count.get(modFile.GName,
                                                             0) + 1
                    record.UnloadRecord()
                    record._RecordID = override._RecordID

class AAssortedTweak_ArmorPlayable(AMultiTweakItem):
    """Sets all armors to be playable"""

    #--Config Phase -----------------------------------------------------------
    def __init__(self):
        super(AAssortedTweak_ArmorPlayable, self).__init__(
            _(u"All Armor Playable"), _(u'Sets all armor to be playable.'),
            u'PlayableArmor', (u'1.0', u'1.0'), )
        self.logHeader = u'=== '+_(u'Playable Armor')
        self.logMsg = u'* '+_(u'Armor pieces set as playable') + u': %d'

class AssortedTweak_ArmorPlayable(AAssortedTweak_ArmorPlayable,MultiTweakItem):
    #--Patch Phase ------------------------------------------------------------
    def getReadClasses(self):
        """Returns load factory classes needed for reading."""
        return 'ARMO',

    def getWriteClasses(self):
        """Returns load factory classes needed for writing."""
        return 'ARMO',

    def scanModFile(self,modFile,progress,patchFile):
        mapper = modFile.getLongMapper()
        patchRecords = patchFile.ARMO
        for record in modFile.ARMO.getActiveRecords():
            if record.flags.notPlayable:
                record = record.getTypeCopy(mapper)
                patchRecords.setRecord(record)

    def buildPatch(self,log,progress,patchFile):
        """Edits patch file as desired. Will write to log."""
        count = {}
        keep = patchFile.getKeeper()
        for record in patchFile.ARMO.records:
            if record.flags.notPlayable:
                full = record.full
                if not full: continue
                if record.script: continue
                if rePlayableSkips.search(full): continue  # probably truly
                # shouldn't be playable
                # We only want to set playable if the record has at least
                # one body flag... otherwise most likely a token.
                if record.flags.leftRing != 0 or record.flags.rightRing != 0\
                        or record.flags.foot != 0 or record.flags.hand != 0 \
                        or record.flags.amulet != 0 or \
                                record.flags.lowerBody != 0 or \
                                record.flags.upperBody != 0 or \
                                record.flags.head != 0 or record.flags.hair \
                        != 0 or record.flags.tail != 0 or \
                                record.flags.shield != 0:
                    record.flags.notPlayable = 0
                    keep(record.fid)
                    srcMod = record.fid[0]
                    count[srcMod] = count.get(srcMod,0) + 1
        self._patchLog(log,count)

class CBash_AssortedTweak_ArmorPlayable(AAssortedTweak_ArmorPlayable,
                                        CBash_MultiTweakItem):
    scanOrder = 29 #Run before the show armor tweaks
    editOrder = 29
    name = _(u'Playable Armor')
    #--Config Phase -----------------------------------------------------------
    def getTypes(self):
        return ['ARMO']

    #--Patch Phase ------------------------------------------------------------
    def apply(self,modFile,record,bashTags):
        """Edits patch file as desired. """
        if record.IsNonPlayable:
            full = record.full
            if not full: return
            if record.script: return
            if rePlayableSkips.search(full): return  # probably truly
            # shouldn't be playable
            # If no body flags are set it is probably a token.
            if record.IsLeftRing or record.IsRightRing or record.IsFoot or \
                    record.IsHand or record.IsAmulet or record.IsLowerBody \
                    or record.IsUpperBody or record.IsHead or record.IsHair \
                    or record.IsTail or record.IsShield:
                override = record.CopyAsOverride(self.patchFile)
                if override:
                    override.IsNonPlayable = False
                    mod_count = self.mod_count
                    mod_count[modFile.GName] = mod_count.get(modFile.GName,
                                                             0) + 1
                    record.UnloadRecord()
                    record._RecordID = override._RecordID

#------------------------------------------------------------------------------
class AAssortedTweak_DarnBooks(AMultiTweakItem):
    """DarNifies books.""" ##: C and P implementations have very similar code
    reColor = re.compile(ur'<font color="?([a-fA-F0-9]+)"?>',re.I+re.M)
    reTagInWord = re.compile(ur'([a-z])<font face=1>',re.M)
    reFont1 = re.compile(ur'(<?<font face=1( ?color=[0-9a-zA]+)?>)+',re.I|re.M)
    reDiv = re.compile(ur'<div',re.I+re.M)
    reFont = re.compile(ur'<font',re.I+re.M)
    reHead2 = re.compile(ur'^(<<|\^\^|>>|)==\s*(\w[^=]+?)==\s*\r\n',re.M)
    reHead3 = re.compile(ur'^(<<|\^\^|>>|)===\s*(\w[^=]+?)\r\n',re.M)
    reBold = re.compile(ur'(__|\*\*|~~)')
    reAlign = re.compile(ur'^(<<|\^\^|>>)',re.M)

    #--Config Phase -----------------------------------------------------------
    def __init__(self):
        super(AAssortedTweak_DarnBooks, self).__init__(_(u"DarNified Books"),
            _(u'Books will be reformatted for DarN UI.'),
            u'DarnBooks',
            (u'default',  u'default'),
            )
        self.logMsg = u'* '+_(u'Books DarNified') + u': %d'

class AssortedTweak_DarnBooks(AAssortedTweak_DarnBooks,MultiTweakItem):
    #--Patch Phase ------------------------------------------------------------
    def getReadClasses(self):
        """Returns load factory classes needed for reading."""
        return 'BOOK',

    def getWriteClasses(self):
        """Returns load factory classes needed for writing."""
        return 'BOOK',

    def scanModFile(self,modFile,progress,patchFile):
        # maxWeight = self.choiceValues[self.chosen][0] # TODO: is this
        # supposed to be used ?
        mapper = modFile.getLongMapper()
        patchBlock = patchFile.BOOK
        id_records = patchBlock.id_records
        for record in modFile.BOOK.getActiveRecords():
            if mapper(record.fid) in id_records: continue
            if not record.enchantment:
                record = record.getTypeCopy(mapper)
                patchBlock.setRecord(record)

    def buildPatch(self,log,progress,patchFile):
        """Edits patch file as desired. Will write to log."""
        count = {}
        reColor = self.__class__.reColor
        reTagInWord = self.__class__.reTagInWord
        reFont1 = self.__class__.reFont1
        reDiv = self.__class__.reDiv
        reFont = self.__class__.reFont
        reHead2 = self.__class__.reHead2
        reHead3 = self.__class__.reHead3
        reBold = self.__class__.reBold
        reAlign = self.__class__.reAlign
        keep = patchFile.getKeeper()
        align_text = {u'^^':u'center',u'<<':u'left',u'>>':u'right'}
        self.inBold = False
        def replaceBold(mo):
            self.inBold = not self.inBold
            return u'<font face=3 color=%s>' % (
                u'440000' if self.inBold else u'444444')
        def replaceAlign(mo):
            return u'<div align=%s>' % align_text[mo.group(1)]
        for record in patchFile.BOOK.records:
            if record.text and not record.enchantment:
                text = record.text
                text = text.replace(u'\u201d', u'')  # there are some FUNKY
                # quotes that don't translate properly. (they are in *latin*
                # encoding not even cp1252 or something normal but non-unicode)
                if reHead2.match(text):
                    self.inBold = False
                    text = reHead2.sub(
                        ur'\1<font face=1 color=220000>\2<font face=3 '
                        ur'color=444444>\r\n', text)
                    text = reHead3.sub(
                        ur'\1<font face=3 color=220000>\2<font face=3 '
                        ur'color=444444>\r\n',
                        text)
                    text = reAlign.sub(replaceAlign,text)
                    text = reBold.sub(replaceBold,text)
                    text = re.sub(ur'\r\n',ur'<br>\r\n',text)
                else:
                    maColor = reColor.search(text)
                    if maColor:
                        color = maColor.group(1)
                    elif record.flags.isScroll:
                        color = u'000000'
                    else:
                        color = u'444444'
                    fontFace = u'<font face=3 color='+color+u'>'
                    text = reTagInWord.sub(ur'\1',text)
                    text.lower()
                    if reDiv.search(text) and not reFont.search(text):
                        text = fontFace+text
                    else:
                        text = reFont1.sub(fontFace,text)
                if text != record.text:
                    record.text = text
                    keep(record.fid)
                    srcMod = record.fid[0]
                    count[srcMod] = count.get(srcMod,0) + 1
        self._patchLog(log,count)

class CBash_AssortedTweak_DarnBooks(AAssortedTweak_DarnBooks,
                                    CBash_MultiTweakItem):
    name = _(u'Books DarNified')

    #--Config Phase -----------------------------------------------------------
    def getTypes(self):
        return ['BOOK']

    #--Patch Phase ------------------------------------------------------------
    def apply(self,modFile,record,bashTags):
        """Edits patch file as desired."""
        def replaceBold(mo):
            self.inBold = not self.inBold
            return u'<font face=3 color=%s>' % (
                u'440000' if self.inBold else u'444444')
        def replaceAlign(mo):
            return u'<div align=%s>' % align_text[mo.group(1)]

        if record.text and not record.enchantment:
            text = record.text
            text = text.replace(u'\u201d', u'')  # there are some FUNKY
            # quotes that don't translate properly. (they are in *latin*
            # encoding not even cp1252 or something normal but non-unicode)
            reColor = self.__class__.reColor
            reTagInWord = self.__class__.reTagInWord
            reFont1 = self.__class__.reFont1
            reDiv = self.__class__.reDiv
            reFont = self.__class__.reFont
            reHead2 = self.__class__.reHead2
            reHead3 = self.__class__.reHead3
            reBold = self.__class__.reBold
            reAlign = self.__class__.reAlign
            align_text = {u'^^':u'center',u'<<':u'left',u'>>':u'right'}
            self.inBold = False
            if reHead2.match(text):
                text = reHead2.sub(
                    ur'\1<font face=1 color=220000>\2<font face=3 '
                    ur'color=444444>\r\n', text)
                text = reHead3.sub(
                    ur'\1<font face=3 color=220000>\2<font face=3 '
                    ur'color=444444>\r\n', text)
                text = reAlign.sub(replaceAlign,text)
                text = reBold.sub(replaceBold,text)
                text = re.sub(ur'\r\n',r'<br>\r\n',text)
            else:
                maColor = reColor.search(text)
                if maColor:
                    color = maColor.group(1)
                elif record.IsScroll:
                    color = u'000000'
                else:
                    color = u'444444'
                fontFace = u'<font face=3 color='+color+u'>'
                text = reTagInWord.sub(ur'\1',text)
                text.lower()
                if reDiv.search(text) and not reFont.search(text):
                    text = fontFace+text
                else:
                    text = reFont1.sub(fontFace,text)
            if text != record.text:
                override = record.CopyAsOverride(self.patchFile)
                if override:
                    override.text = text
                    mod_count = self.mod_count
                    mod_count[modFile.GName] = mod_count.get(modFile.GName,
                                                             0) + 1
                    record.UnloadRecord()
                    record._RecordID = override._RecordID

#------------------------------------------------------------------------------
class AAssortedTweak_FogFix(AMultiTweakItem):
    """Fix fog in cell to be non-zero."""

    #--Config Phase -----------------------------------------------------------
    def __init__(self):
        super(AAssortedTweak_FogFix, self).__init__(_(u"Nvidia Fog Fix"),
            _(u'Fix fog related Nvidia black screen problems.'),
            u'FogFix',
            (u'0.0001',  u'0.0001'),
            )
        self.defaultEnabled = True

    def _patchLog(self, log, count):
        log.setHeader(self.logHeader)
        for srcMod in load_order.get_ordered(count.keys()):
            log(u'  * %s: %d' % (srcMod.s, count[srcMod]))

class AssortedTweak_FogFix(AAssortedTweak_FogFix,MultiTweakItem):
    #--Patch Phase ------------------------------------------------------------
    def getReadClasses(self):
        """Returns load factory classes needed for reading."""
        return 'CELL','WRLD',

    def getWriteClasses(self):
        """Returns load factory classes needed for writing."""
        return 'CELL','WRLD',

    def scanModFile(self, modFile, progress,patchFile):
        """Add lists from modFile."""
        if 'CELL' not in modFile.tops: return
        patchCells = patchFile.CELL
        modFile.convertToLongFids(('CELL',))
        for cellBlock in modFile.CELL.cellBlocks:
            cell = cellBlock.cell
            if not (cell.fogNear or cell.fogFar or cell.fogClip):
                patchCells.setCell(cell)

    def buildPatch(self,log,progress,patchFile):
        """Adds merged lists to patchfile."""
        keep = patchFile.getKeeper()
        count = {}
        for cellBlock in patchFile.CELL.cellBlocks:
            for cellBlock in patchFile.CELL.cellBlocks:
                cell = cellBlock.cell
                if not (cell.fogNear or cell.fogFar or cell.fogClip):
                    cell.fogNear = 0.0001
                    keep(cell.fid)
                    count.setdefault(cell.fid[0],0)
                    count[cell.fid[0]] += 1
        self._patchLog(log, count)

class CBash_AssortedTweak_FogFix(AAssortedTweak_FogFix,CBash_MultiTweakItem):
    name = _(u'Nvidia Fog Fix')

    #--Config Phase -----------------------------------------------------------
    def getTypes(self):
        return ['CELLS']  # or 'CELL', but we want this patcher to run in
        # the same group as the CellImporter, so we'll have to skip
        # worldspaces.  It shouldn't be a problem in those CELLs.

    #--Patch Phase ------------------------------------------------------------
    def apply(self,modFile,record,bashTags):
        """Edits patch file as desired."""
        if record.Parent:  # It's a CELL that showed up because we said
            # 'CELLS' instead of 'CELL'
            return
        if not (record.fogNear or record.fogFar or record.fogClip):
            override = record.CopyAsOverride(self.patchFile)
            if override:
                override.fogNear = 0.0001
                mod_count = self.mod_count
                mod_count[modFile.GName] = mod_count.get(modFile.GName,0) + 1
                record.UnloadRecord()
                record._RecordID = override._RecordID

#------------------------------------------------------------------------------
class AAssortedTweak_NoLightFlicker(AMultiTweakItem):
    """Remove light flickering for low end machines."""

    #--Config Phase -----------------------------------------------------------
    def __init__(self):
        super(AAssortedTweak_NoLightFlicker, self).__init__(
            _(u"No Light Flicker"),
            _(u'Remove flickering from lights. For use on low-end machines.'),
            u'NoLightFlicker',
            (u'1.0',  u'1.0'),
            )
        self.logMsg = u'* '+_(u'Lights unflickered') + u': %d'

class AssortedTweak_NoLightFlicker(AAssortedTweak_NoLightFlicker,
                                   MultiTweakItem):
    #--Config Phase -----------------------------------------------------------
    def __init__(self):
        super(AssortedTweak_NoLightFlicker, self).__init__()
        self.flags = flags = MreRecord.type_class['LIGH']._flags()
        flags.flickers = flags.flickerSlow = flags.pulse = flags.pulseSlow =\
            True

    #--Patch Phase ------------------------------------------------------------
    def getReadClasses(self):
        """Returns load factory classes needed for reading."""
        return 'LIGH',

    def getWriteClasses(self):
        """Returns load factory classes needed for writing."""
        return 'LIGH',

    def scanModFile(self,modFile,progress,patchFile):
        flickerFlags = self.flags
        mapper = modFile.getLongMapper()
        patchRecords = patchFile.LIGH
        for record in modFile.LIGH.getActiveRecords():
            if record.flags & flickerFlags:
                record = record.getTypeCopy(mapper)
                patchRecords.setRecord(record)

    def buildPatch(self,log,progress,patchFile):
        """Edits patch file as desired. Will write to log."""
        count = {}
        flickerFlags = self.flags
        notFlickerFlags = ~flickerFlags
        keep = patchFile.getKeeper()
        for record in patchFile.LIGH.records:
            if int(record.flags & flickerFlags):
                record.flags &= notFlickerFlags
                keep(record.fid)
                srcMod = record.fid[0]
                count[srcMod] = count.get(srcMod,0) + 1
        self._patchLog(log,count)

class CBash_AssortedTweak_NoLightFlicker(AAssortedTweak_NoLightFlicker,
                                         CBash_MultiTweakItem):
    name = _(u'No Light Flicker')

    #--Config Phase -----------------------------------------------------------
    def getTypes(self):
        return ['LIGH']

    #--Patch Phase ------------------------------------------------------------
    def apply(self,modFile,record,bashTags):
        """Edits patch file as desired. """
        if record.IsFlickers or record.IsFlickerSlow or record.IsPulse or \
                record.IsPulseSlow:
            override = record.CopyAsOverride(self.patchFile)
            if override:
                override.IsFlickers = False
                override.IsFlickerSlow = False
                override.IsPulse = False
                override.IsPulseSlow = False
                mod_count = self.mod_count
                mod_count[modFile.GName] = mod_count.get(modFile.GName,0) + 1
                record.UnloadRecord()
                record._RecordID = override._RecordID

#------------------------------------------------------------------------------

class AMultiTweakItem_Weight(AMultiTweakItem):

    @property
    def weight(self): return self.choiceValues[self.chosen][0]

    def _patchLog(self, log, count):
        """Will write to log for a class that has a weight field"""
        log.setHeader(self.logHeader)
        log(self.logWeightValue % self.weight)
        log(self.logMsg % sum(count.values()))
        for srcMod in load_order.get_ordered(count.keys()):
            log(u'  * %s: %d' % (srcMod.s,count[srcMod]))

class CBash_MultiTweakItem_Weight(CBash_MultiTweakItem,
                                  AMultiTweakItem_Weight): pass

class AAssortedTweak_PotionWeight(AMultiTweakItem_Weight):
    """Reweighs standard potions down to 0.1."""

    #--Config Phase -----------------------------------------------------------
    def __init__(self):
        super(AAssortedTweak_PotionWeight, self).__init__(
            _(u"Reweigh: Potions (Maximum)"),
            _(u'Potion weight will be capped.'),
            u'MaximumPotionWeight',
            (u'0.1',  0.1),
            (u'0.2',  0.2),
            (u'0.4',  0.4),
            (u'0.6',  0.6),
            (_(u'Custom'),0.0),
            )
        self.logWeightValue = _(u'Potions set to maximum weight of ') + u'%f'
        self.logMsg = u'* '+_(u'Potions Reweighed') + u': %d'

class AssortedTweak_PotionWeight(AAssortedTweak_PotionWeight,MultiTweakItem):
    #--Patch Phase ------------------------------------------------------------
    def getReadClasses(self):
        """Returns load factory classes needed for reading."""
        return 'ALCH',

    def getWriteClasses(self):
        """Returns load factory classes needed for writing."""
        return 'ALCH',

    def scanModFile(self,modFile,progress,patchFile):
        maxWeight = self.weight
        mapper = modFile.getLongMapper()
        patchBlock = patchFile.ALCH
        id_records = patchBlock.id_records
        for record in modFile.ALCH.getActiveRecords():
            if mapper(record.fid) in id_records: continue
            if maxWeight < record.weight < 1:
                record = record.getTypeCopy(mapper)
                patchBlock.setRecord(record)

    def buildPatch(self,log,progress,patchFile):
        """Edits patch file as desired. Will write to log."""
        maxWeight = self.weight
        count = {}
        keep = patchFile.getKeeper()
        for record in patchFile.ALCH.records:
            if maxWeight < record.weight < 1 and not (
                    'SEFF', 0) in record.getEffects():
                record.weight = maxWeight
                keep(record.fid)
                srcMod = record.fid[0]
                count[srcMod] = count.get(srcMod,0) + 1
        self._patchLog(log, count)

class CBash_AssortedTweak_PotionWeight(AAssortedTweak_PotionWeight,
                                       CBash_MultiTweakItem_Weight):
    name = _(u"Reweigh: Potions (Maximum)")

    #--Config Phase -----------------------------------------------------------
    def __init__(self):
        super(CBash_AssortedTweak_PotionWeight, self).__init__()
        # see https://github.com/wrye-bash/wrye-bash/commit/3aa3c941b2de6d751f71e50613ba20ac14f477e8
        # CBash only, PBash gets away with just knowing the FormID of SEFF
        # and always assuming it exists, since it's from Oblivion.esm. CBash
        #  handles this by making sure the MGEF records are almost always
        # read in, and always before patchers that will need them
        self.SEFF = MGEFCode('SEFF')

    def getTypes(self):
        return ['ALCH']

    #--Patch Phase ------------------------------------------------------------
    def apply(self,modFile,record,bashTags):
        """Edits patch file as desired. """
        maxWeight = self.weight
        if maxWeight < record.weight < 1.0:
            for effect in record.effects:
                if effect.name == self.SEFF:
                    return
            override = record.CopyAsOverride(self.patchFile)
            if override:
                override.weight = maxWeight
                mod_count = self.mod_count
                mod_count[modFile.GName] = mod_count.get(modFile.GName,0) + 1
                record.UnloadRecord()
                record._RecordID = override._RecordID

#------------------------------------------------------------------------------
class AAssortedTweak_IngredientWeight(AMultiTweakItem_Weight):
    """Reweighs standard ingredients down to 0.1."""

    #--Config Phase -----------------------------------------------------------
    def __init__(self):
        super(AAssortedTweak_IngredientWeight, self).__init__(
            _(u"Reweigh: Ingredients"),
            _(u'Ingredient weight will be capped.'),
            u'MaximumIngredientWeight',
            (u'0.1',  0.1),
            (u'0.2',  0.2),
            (u'0.4',  0.4),
            (u'0.6',  0.6),
            (_(u'Custom'),0.0),
            )
        self.logWeightValue = _(u'Ingredients set to maximum weight of') + \
                              u' %f'
        self.logMsg = u'* '+_(u'Ingredients Reweighed') + u': %d'

class AssortedTweak_IngredientWeight(AAssortedTweak_IngredientWeight,
                                     MultiTweakItem):
    #--Patch Phase ------------------------------------------------------------
    def getReadClasses(self):
        """Returns load factory classes needed for reading."""
        return 'INGR',

    def getWriteClasses(self):
        """Returns load factory classes needed for writing."""
        return 'INGR',

    def scanModFile(self,modFile,progress,patchFile):
        maxWeight = self.weight
        mapper = modFile.getLongMapper()
        patchBlock = patchFile.INGR
        id_records = patchBlock.id_records
        for record in modFile.INGR.getActiveRecords():
            if mapper(record.fid) in id_records: continue
            if record.weight > maxWeight:
                record = record.getTypeCopy(mapper)
                patchBlock.setRecord(record)

    def buildPatch(self,log,progress,patchFile):
        """Edits patch file as desired. Will write to log."""
        maxWeight = self.weight
        count = {}
        keep = patchFile.getKeeper()
        for record in patchFile.INGR.records:
            if record.weight > maxWeight:
                record.weight = maxWeight
                keep(record.fid)
                srcMod = record.fid[0]
                count[srcMod] = count.get(srcMod,0) + 1
        self._patchLog(log, count)

class CBash_AssortedTweak_IngredientWeight(AAssortedTweak_IngredientWeight,
                                           CBash_MultiTweakItem_Weight):
    name = _(u'Reweigh: Ingredients')

    #--Config Phase -----------------------------------------------------------
    def __init__(self):
        super(CBash_AssortedTweak_IngredientWeight, self).__init__()
        self.SEFF = MGEFCode('SEFF')

    def getTypes(self):
        return ['INGR']

    #--Patch Phase ------------------------------------------------------------
    def apply(self,modFile,record,bashTags):
        """Edits patch file as desired. """
        maxWeight = self.weight
        if record.weight > maxWeight:
            for effect in record.effects:
                if effect.name == self.SEFF:
                    return
            override = record.CopyAsOverride(self.patchFile)
            if override:
                override.weight = maxWeight
                mod_count = self.mod_count
                mod_count[modFile.GName] = mod_count.get(modFile.GName,0) + 1
                record.UnloadRecord()
                record._RecordID = override._RecordID

#------------------------------------------------------------------------------
class AAssortedTweak_PotionWeightMinimum(AMultiTweakItem_Weight):
    """Reweighs any potions up to 4."""

    #--Config Phase -----------------------------------------------------------
    def __init__(self):
        super(AAssortedTweak_PotionWeightMinimum, self).__init__(
            _(u"Reweigh: Potions (Minimum)"),
            _(u'Potion weight will be floored.'),
            u'MinimumPotionWeight',
            (u'1',  1),
            (u'2',  2),
            (u'3',  3),
            (u'4',  4),
            (_(u'Custom'),0.0),
            )
        self.logWeightValue = _(u'Potions set to minimum weight of ') + u'%f'
        self.logMsg = u'* '+_(u'Potions Reweighed') + u': %d'

class AssortedTweak_PotionWeightMinimum(AAssortedTweak_PotionWeightMinimum,
                                        MultiTweakItem):
    #--Patch Phase ------------------------------------------------------------
    def getReadClasses(self):
        """Returns load factory classes needed for reading."""
        return 'ALCH',

    def getWriteClasses(self):
        """Returns load factory classes needed for writing."""
        return 'ALCH',

    def scanModFile(self,modFile,progress,patchFile):
        minWeight = self.weight
        mapper = modFile.getLongMapper()
        patchBlock = patchFile.ALCH
        id_records = patchBlock.id_records
        for record in modFile.ALCH.getActiveRecords():
            if mapper(record.fid) in id_records: continue
            if record.weight < minWeight:
                record = record.getTypeCopy(mapper)
                patchBlock.setRecord(record)

    def buildPatch(self,log,progress,patchFile):
        """Edits patch file as desired. Will write to log."""
        minWeight = self.weight
        count = {}
        keep = patchFile.getKeeper()
        for record in patchFile.ALCH.records:
            if record.weight < minWeight:
                record.weight = minWeight
                keep(record.fid)
                srcMod = record.fid[0]
                count[srcMod] = count.get(srcMod,0) + 1
        self._patchLog(log, count)

class CBash_AssortedTweak_PotionWeightMinimum(
    AAssortedTweak_PotionWeightMinimum, CBash_MultiTweakItem_Weight):
    scanOrder = 33 #Have it run after the max weight for consistent results
    editOrder = 33
    name = _(u'Reweigh: Potions (Minimum)')

    #--Config Phase -----------------------------------------------------------
    def getTypes(self):
        return ['ALCH']

    #--Patch Phase ------------------------------------------------------------
    def apply(self,modFile,record,bashTags):
        """Edits patch file as desired. """
        minWeight = self.weight
        if record.weight < minWeight:
            override = record.CopyAsOverride(self.patchFile)
            if override:
                override.weight = minWeight
                mod_count = self.mod_count
                mod_count[modFile.GName] = mod_count.get(modFile.GName,0) + 1
                record.UnloadRecord()
                record._RecordID = override._RecordID

#------------------------------------------------------------------------------
class AAssortedTweak_StaffWeight(AMultiTweakItem_Weight):
    """Reweighs staffs."""

    #--Config Phase -----------------------------------------------------------
    def __init__(self):
        super(AAssortedTweak_StaffWeight, self).__init__(
            _(u"Reweigh: Staffs/Staves"),
            _(u'Staff weight will be capped.'),
            u'StaffWeight',
            (u'1',  1.0),
            (u'2',  2.0),
            (u'3',  3.0),
            (u'4',  4.0),
            (u'5',  5.0),
            (u'6',  6.0),
            (u'7',  7.0),
            (u'8',  8.0),
            (_(u'Custom'),0.0),
            )
        self.logWeightValue = _(u'Staffs/Staves set to maximum weight of') + \
                              u' %f'
        self.logMsg = u'* '+_(u'Staffs/Staves Reweighed') + u': %d'

class AssortedTweak_StaffWeight(AAssortedTweak_StaffWeight,MultiTweakItem):
    #--Patch Phase ------------------------------------------------------------
    def getReadClasses(self):
        """Returns load factory classes needed for reading."""
        return 'WEAP',

    def getWriteClasses(self):
        """Returns load factory classes needed for writing."""
        return 'WEAP',

    def scanModFile(self,modFile,progress,patchFile):
        maxWeight = self.weight
        mapper = modFile.getLongMapper()
        patchBlock = patchFile.WEAP
        id_records = patchBlock.id_records
        for record in modFile.WEAP.getActiveRecords():
            if mapper(record.fid) in id_records: continue
            if record.weaponType == 4 and record.weight > maxWeight:
                record = record.getTypeCopy(mapper)
                patchBlock.setRecord(record)

    def buildPatch(self,log,progress,patchFile):
        """Edits patch file as desired. Will write to log."""
        maxWeight = self.weight
        count = {}
        keep = patchFile.getKeeper()
        for record in patchFile.WEAP.records:
            if record.weaponType == 4 and record.weight > maxWeight:
                record.weight = maxWeight
                keep(record.fid)
                srcMod = record.fid[0]
                count[srcMod] = count.get(srcMod,0) + 1
        self._patchLog(log, count)

class CBash_AssortedTweak_StaffWeight(AAssortedTweak_StaffWeight,
                                      CBash_MultiTweakItem_Weight):
    name = _(u'Reweigh: Staffs/Staves')

    #--Config Phase -----------------------------------------------------------
    def getTypes(self):
        return ['WEAP']

    #--Patch Phase ------------------------------------------------------------
    def apply(self,modFile,record,bashTags):
        """Edits patch file as desired. """
        maxWeight = self.weight
        if record.IsStaff and record.weight > maxWeight:
            override = record.CopyAsOverride(self.patchFile)
            if override:
                override.weight = maxWeight
                mod_count = self.mod_count
                mod_count[modFile.GName] = mod_count.get(modFile.GName,0) + 1
                record.UnloadRecord()
                record._RecordID = override._RecordID

#------------------------------------------------------------------------------
class AAssortedTweak_ArrowWeight(AMultiTweakItem_Weight):

    #--Config Phase -----------------------------------------------------------
    def __init__(self):
        super(AAssortedTweak_ArrowWeight, self).__init__(_(u"Reweigh: Arrows"),
            _(u'Arrow weights will be capped.'),
            u'MaximumArrowWeight',
            (u'0',    0.0),
            (u'0.1',  0.1),
            (u'0.2',  0.2),
            (u'0.4',  0.4),
            (u'0.6',  0.6),
            (_(u'Custom'),0.0),
            )
        self.logWeightValue = _(u'Arrows set to maximum weight of ') + u'%f'
        self.logMsg = u'* '+_(u'Arrows Reweighed') + u': %d'

class AssortedTweak_ArrowWeight(AAssortedTweak_ArrowWeight,MultiTweakItem):
    #--Patch Phase ------------------------------------------------------------
    def getReadClasses(self):
        """Returns load factory classes needed for reading."""
        return 'AMMO',

    def getWriteClasses(self):
        """Returns load factory classes needed for writing."""
        return 'AMMO',

    def scanModFile(self,modFile,progress,patchFile):
        maxWeight = self.weight
        mapper = modFile.getLongMapper()
        patchBlock = patchFile.AMMO
        id_records = patchBlock.id_records
        for record in modFile.AMMO.getActiveRecords():
            if mapper(record.fid) in id_records: continue
            if record.weight > maxWeight:
                record = record.getTypeCopy(mapper)
                patchBlock.setRecord(record)

    def buildPatch(self,log,progress,patchFile):
        """Edits patch file as desired. Will write to log."""
        maxWeight = self.weight
        count = {}
        keep = patchFile.getKeeper()
        for record in patchFile.AMMO.records:
            if record.weight > maxWeight:
                record.weight = maxWeight
                keep(record.fid)
                srcMod = record.fid[0]
                count[srcMod] = count.get(srcMod,0) + 1
        self._patchLog(log, count)

class CBash_AssortedTweak_ArrowWeight(AAssortedTweak_ArrowWeight,
                                      CBash_MultiTweakItem_Weight):
    name = _(u'Reweigh: Arrows')

    #--Config Phase -----------------------------------------------------------
    def getTypes(self):
        return ['AMMO']

    #--Patch Phase ------------------------------------------------------------
    def apply(self,modFile,record,bashTags):
        """Edits patch file as desired. """
        maxWeight = self.weight
        if record.weight > maxWeight:
            override = record.CopyAsOverride(self.patchFile)
            if override:
                override.weight = maxWeight
                mod_count = self.mod_count
                mod_count[modFile.GName] = mod_count.get(modFile.GName,0) + 1
                record.UnloadRecord()
                record._RecordID = override._RecordID

#------------------------------------------------------------------------------
class AAssortedTweak_ScriptEffectSilencer(AMultiTweakItem):
    """Silences the script magic effect and gives it an extremely high
    speed."""

    #--Config Phase -----------------------------------------------------------
    def __init__(self):
        super(AAssortedTweak_ScriptEffectSilencer, self).__init__(
            _(u"Magic: Script Effect Silencer"),
            _(u'Script Effect will be silenced and have no graphics.'),
            u'SilentScriptEffect',
            (u'0',    0),
            )
        self.defaultEnabled = True

    def _patchLog(self,log):
        log.setHeader(self.logHeader)
        log(_(u'Script Effect silenced.'))

class AssortedTweak_ScriptEffectSilencer(AAssortedTweak_ScriptEffectSilencer,
                                         MultiTweakItem):
    #--Patch Phase ------------------------------------------------------------
    def getReadClasses(self):
        """Returns load factory classes needed for reading."""
        return 'MGEF',

    def getWriteClasses(self):
        """Returns load factory classes needed for writing."""
        return 'MGEF',

    def scanModFile(self,modFile,progress,patchFile):
        mapper = modFile.getLongMapper()
        patchBlock = patchFile.MGEF
        id_records = patchBlock.id_records
        modFile.convertToLongFids(('MGEF',))
        for record in modFile.MGEF.getActiveRecords():
            fid = record.fid
            if not record.longFids: fid = mapper(fid)
            if fid in id_records: continue
            if record.eid != 'SEFF': continue
            patchBlock.setRecord(record.getTypeCopy(mapper))

    def buildPatch(self,log,progress,patchFile):
        """Edits patch file as desired. Will write to log."""
        nullRef = (GPath(u'Oblivion.esm'),0)
        silentattrs = {
            'model' : None,
            'projectileSpeed' : 9999,
            'light' : nullRef,
            'effectShader' : nullRef,
            'enchantEffect' : nullRef,
            'castingSound' : nullRef,
            'boltSound' : nullRef,
            'hitSound' : nullRef,
            'areaSound' : nullRef}
        keep = patchFile.getKeeper()
        for record in patchFile.MGEF.records:
            if record.eid != 'SEFF' or not record.longFids: continue
            record.flags.noHitEffect = True
            for attr in silentattrs:
                if getattr(record,attr) != silentattrs[attr]:
                    setattr(record,attr,silentattrs[attr])
                    keep(record.fid)
        self._patchLog(log)

class CBash_AssortedTweak_ScriptEffectSilencer(
    AAssortedTweak_ScriptEffectSilencer, CBash_MultiTweakItem):
    name = _(u'Magic: Script Effect Silencer')

    #--Config Phase -----------------------------------------------------------
    def __init__(self):
        super(CBash_AssortedTweak_ScriptEffectSilencer, self).__init__()
        self.attrs = ['modPath', 'modb', 'modt_p', 'projectileSpeed', 'light',
                      'effectShader', 'enchantEffect', 'castingSound',
                      'boltSound', 'hitSound', 'areaSound', 'IsNoHitEffect']
        self.newValues = [None, None, None, 9999, None, None, None, None, None,
                          None, None, True]
        self.SEFF = MGEFCode('SEFF')
        # TODO THIS IS ONE OF THE FEW THAT HAS no self.mod_count = {} - maybe
        # should call the constructor directly instead of super() ?
        self.buildPatchLog=self._patchLog # AAssortedTweak_ScriptEffectSilencer

    def getTypes(self):
        return ['MGEF']

    #--Patch Phase ------------------------------------------------------------
    def apply(self,modFile,record,bashTags):
        """Edits patch file as desired. """
        if record.eid == self.SEFF[0]:
            attrs = self.attrs
            newValues = self.newValues
            oldValues = map(record.__getattribute__, attrs)
            if oldValues != newValues:
                override = record.CopyAsOverride(self.patchFile)
                if override:
                    map(override.__setattr__, attrs, newValues)
                    record.UnloadRecord()
                    record._RecordID = override._RecordID

#------------------------------------------------------------------------------
class AAssortedTweak_HarvestChance(AMultiTweakItem):
    """Adjust Harvest Chances."""

    #--Config Phase -----------------------------------------------------------
    def __init__(self):
        super(AAssortedTweak_HarvestChance, self).__init__(
            _(u"Harvest Chance"),
            _(u'Harvest chances on all plants will be set to the chosen '
                u'percentage.'),
            u'HarvestChance',
            (u'10%',  10),
            (u'20%',  20),
            (u'30%',  30),
            (u'40%',  40),
            (u'50%',  50),
            (u'60%',  60),
            (u'70%',  70),
            (u'80%',  80),
            (u'90%',  90),
            (u'100%', 100),
            (_(u'Custom'),0),
            )
        self.logMsg = u'* '+_(u'Harvest Chances Changed') + u': %d'

class AssortedTweak_HarvestChance(AAssortedTweak_HarvestChance,MultiTweakItem):
    #--Patch Phase ------------------------------------------------------------
    def getReadClasses(self):
        """Returns load factory classes needed for reading."""
        return 'FLOR',

    def getWriteClasses(self):
        """Returns load factory classes needed for writing."""
        return 'FLOR',

    def scanModFile(self,modFile,progress,patchFile):
        chance = self.choiceValues[self.chosen][0]
        mapper = modFile.getLongMapper()
        patchBlock = patchFile.FLOR
        id_records = patchBlock.id_records
        for record in modFile.FLOR.getActiveRecords():
            if record.eid.startswith('Nirnroot'): continue #skip Nirnroots
            if mapper(record.fid) in id_records: continue
            for attr in ['spring','summer','fall','winter']:
                if getattr(record,attr) != chance:
                    record = record.getTypeCopy(mapper)
                    patchBlock.setRecord(record)
                    break

    def buildPatch(self,log,progress,patchFile):
        """Edits patch file as desired. Will write to log."""
        chance = self.choiceValues[self.chosen][0]
        count = {}
        keep = patchFile.getKeeper()
        for record in patchFile.FLOR.records:
            record.spring, record.summer, record.fall, record.winter = \
                chance, chance, chance, chance
            keep(record.fid)
            srcMod = record.fid[0]
            count[srcMod] = count.get(srcMod,0) + 1
        self._patchLog(log,count)

class CBash_AssortedTweak_HarvestChance(AAssortedTweak_HarvestChance,
                                        CBash_MultiTweakItem):
    name = _(u'Harvest Chance')

    #--Config Phase -----------------------------------------------------------
    def __init__(self):
        super(CBash_AssortedTweak_HarvestChance, self).__init__()
        self.attrs = ['spring','summer','fall','winter']

    def getTypes(self):
        return ['FLOR']

    #--Patch Phase ------------------------------------------------------------
    def apply(self,modFile,record,bashTags):
        """Edits patch file as desired. """
        if record.eid.startswith(u'Nirnroot'): return #skip Nirnroots
        newValues = [self.choiceValues[self.chosen][0]] * 4
        oldValues = map(record.__getattribute__, self.attrs)
        if oldValues != newValues:
            override = record.CopyAsOverride(self.patchFile)
            if override:
                map(override.__setattr__, self.attrs, newValues)
                mod_count = self.mod_count
                mod_count[modFile.GName] = mod_count.get(modFile.GName,0) + 1
                record.UnloadRecord()
                record._RecordID = override._RecordID

#------------------------------------------------------------------------------
class AAssortedTweak_WindSpeed(AMultiTweakItem):
    """Disables Weather winds."""

    #--Config Phase -----------------------------------------------------------
    def __init__(self):
        super(AAssortedTweak_WindSpeed, self).__init__(_(u"Disable Wind"),
            _(u'Disables the wind on all weathers.'),
            u'windSpeed',
            (_(u'Disable'),  0),
            )
        self.logMsg = u'* '+_(u'Winds Disabled') + u': %d'

class AssortedTweak_WindSpeed(AAssortedTweak_WindSpeed,MultiTweakItem):
    #--Patch Phase ------------------------------------------------------------
    def getReadClasses(self):
        """Returns load factory classes needed for reading."""
        return 'WTHR',

    def getWriteClasses(self):
        """Returns load factory classes needed for writing."""
        return 'WTHR',

    def scanModFile(self,modFile,progress,patchFile):
        mapper = modFile.getLongMapper()
        patchBlock = patchFile.WTHR
        id_records = patchBlock.id_records
        for record in modFile.WTHR.getActiveRecords():
            if mapper(record.fid) in id_records: continue
            if record.windSpeed != 0:
                record = record.getTypeCopy(mapper)
                patchBlock.setRecord(record)

    def buildPatch(self,log,progress,patchFile):
        """Edits patch file as desired. Will write to log."""
        count = {}
        keep = patchFile.getKeeper()
        for record in patchFile.WTHR.records:
            if record.windSpeed != 0:
                record.windSpeed = 0
                keep(record.fid)
                srcMod = record.fid[0]
                count[srcMod] = count.get(srcMod,0) + 1
        self._patchLog(log,count)

class CBash_AssortedTweak_WindSpeed(AAssortedTweak_WindSpeed,
                                    CBash_MultiTweakItem):
    name = _(u'Disable Wind')

    #--Config Phase -----------------------------------------------------------
    def getTypes(self):
        return ['WTHR']

    #--Patch Phase ------------------------------------------------------------
    def apply(self,modFile,record,bashTags):
        """Edits patch file as desired. """
        if record.windSpeed != 0:
            override = record.CopyAsOverride(self.patchFile)
            if override:
                override.windSpeed = 0
                mod_count = self.mod_count
                mod_count[modFile.GName] = mod_count.get(modFile.GName,0) + 1
                record.UnloadRecord()
                record._RecordID = override._RecordID

#------------------------------------------------------------------------------
class AAssortedTweak_UniformGroundcover(AMultiTweakItem):
    """Eliminates random variation in groundcover."""

    #--Config Phase -----------------------------------------------------------
    def __init__(self):
        super(AAssortedTweak_UniformGroundcover, self).__init__(
            _(u"Uniform Groundcover"),
            _(u'Eliminates random variation in groundcover (grasses, '
              u'shrubs, etc.).'),
            u'UniformGroundcover',
            (u'1.0', u'1.0'),
            )
        self.logMsg = u'* '+_(u'Grasses Normalized') + u': %d'

class AssortedTweak_UniformGroundcover(AAssortedTweak_UniformGroundcover,
                                       MultiTweakItem):
    #--Patch Phase ------------------------------------------------------------
    def getReadClasses(self):
        """Returns load factory classes needed for reading."""
        return 'GRAS',

    def getWriteClasses(self):
        """Returns load factory classes needed for writing."""
        return 'GRAS',

    def scanModFile(self,modFile,progress,patchFile):
        mapper = modFile.getLongMapper()
        patchBlock = patchFile.GRAS
        id_records = patchBlock.id_records
        for record in modFile.GRAS.getActiveRecords():
            if mapper(record.fid) in id_records: continue
            if record.heightRange != 0:
                record = record.getTypeCopy(mapper)
                patchBlock.setRecord(record)

    def buildPatch(self,log,progress,patchFile):
        """Edits patch file as desired. Will write to log."""
        count = {}
        keep = patchFile.getKeeper()
        for record in patchFile.GRAS.records:
            if record.heightRange != 0:
                record.heightRange = 0
                keep(record.fid)
                srcMod = record.fid[0]
                count[srcMod] = count.get(srcMod,0) + 1
        self._patchLog(log,count)

class CBash_AssortedTweak_UniformGroundcover(AAssortedTweak_UniformGroundcover,
                                             CBash_MultiTweakItem):
    name = _(u'Uniform Groundcover')

    #--Config Phase -----------------------------------------------------------
    def getTypes(self):
        return ['GRAS']

    #--Patch Phase ------------------------------------------------------------
    def apply(self,modFile,record,bashTags):
        """Edits patch file as desired. """
        if record.heightRange != 0:
            override = record.CopyAsOverride(self.patchFile)
            if override:
                override.heightRange = 0
                mod_count = self.mod_count
                mod_count[modFile.GName] = mod_count.get(modFile.GName,0) + 1
                record.UnloadRecord()
                record._RecordID = override._RecordID

#------------------------------------------------------------------------------
class AAssortedTweak_SetCastWhenUsedEnchantmentCosts(AMultiTweakItem):
    """Sets Cast When Used Enchantment number of uses."""
    #--Config Phase -----------------------------------------------------------
    def __init__(self):
        super(AAssortedTweak_SetCastWhenUsedEnchantmentCosts, self).__init__(
            _(u"Number of uses for pre-enchanted weapons and Staffs/Staves"),
            _(u'The charge amount and cast cost will be edited so that all '
              u'enchanted weapons and Staffs/Staves have the amount of '
              u'uses specified. Cost will be rounded up to 1 (unless set '
              u'to unlimited) so number of uses may not exactly match for '
              u'all weapons.'),
            u'Number of uses:',
            (u'1', 1),
            (u'5', 5),
            (u'10', 10),
            (u'20', 20),
            (u'30', 30),
            (u'40', 40),
            (u'50', 50),
            (u'80', 80),
            (u'100', 100),
            (u'250', 250),
            (u'500', 500),
            (_(u'Unlimited'), 0),
            (_(u'Custom'),0),
            )
        self.logHeader = u'=== '+_(u'Set Enchantment Number of Uses')
        self.logMsg = u'* '+_(u'Enchantments set') + u': %d'

class AssortedTweak_SetCastWhenUsedEnchantmentCosts(
    AAssortedTweak_SetCastWhenUsedEnchantmentCosts, MultiTweakItem):
    #info: 'itemType','chargeAmount','enchantCost'
    #--Patch Phase ------------------------------------------------------------
    def getReadClasses(self):
        """Returns load factory classes needed for reading."""
        return 'ENCH',

    def getWriteClasses(self):
        """Returns load factory classes needed for writing."""
        return 'ENCH',

    def scanModFile(self,modFile,progress,patchFile):
        mapper = modFile.getLongMapper()
        patchBlock = patchFile.ENCH
        id_records = patchBlock.id_records
        for record in modFile.ENCH.getActiveRecords():
            if mapper(record.fid) in id_records: continue
            if record.itemType in [1,2]:
                record = record.getTypeCopy(mapper)
                patchBlock.setRecord(record)

    def buildPatch(self,log,progress,patchFile):
        """Edits patch file as desired. Will write to log."""
        count = {}
        keep = patchFile.getKeeper()
        for record in patchFile.ENCH.records:
            if record.itemType in [1,2]:
                uses = self.choiceValues[self.chosen][0]
                cost = uses
                if uses != 0:
                    cost = max(record.chargeAmount/uses,1)
                record.enchantCost = cost
                record.chargeAmount = cost * uses
                keep(record.fid)
                srcMod = record.fid[0]
                count[srcMod] = count.get(srcMod,0) + 1
        self._patchLog(log,count)

class CBash_AssortedTweak_SetCastWhenUsedEnchantmentCosts(
    AAssortedTweak_SetCastWhenUsedEnchantmentCosts, CBash_MultiTweakItem):
    name = _(u'Set Enchantment Number of Uses')

    #--Config Phase -----------------------------------------------------------
    def getTypes(self):
        return ['ENCH']

    #--Patch Phase ------------------------------------------------------------
    def apply(self,modFile,record,bashTags):
        """Edits patch file as desired. """
        if record.IsStaff or record.IsWeapon:
            uses = self.choiceValues[self.chosen][0]
            cost = uses
            if uses != 0:
                cost = max(record.chargeAmount/uses,1)
            amount = cost * uses
            if record.enchantCost != cost or record.chargeAmount != amount:
                override = record.CopyAsOverride(self.patchFile)
                if override:
                    override.enchantCost = cost
                    override.chargeAmount = amount
                    mod_count = self.mod_count
                    mod_count[modFile.GName] = mod_count.get(modFile.GName,
                                                             0) + 1
                    record.UnloadRecord()
                    record._RecordID = override._RecordID

#------------------------------------------------------------------------------
class AAssortedTweak_DefaultIcons(AMultiTweakItem):
    """Sets a default icon for any records that don't have any icon
    assigned."""
    #--Config Phase -----------------------------------------------------------
    def __init__(self):
        super(AAssortedTweak_DefaultIcons,self).__init__(_(u"Default Icons"),
            _(u"Sets a default icon for any records that don't have any icon"
              u" assigned"),
            u'icons',
            (u'1', 1),
            )
        self.defaultEnabled = True
        self.logMsg = u'* '+_(u'Default Icons set') + u': %d'

class AssortedTweak_DefaultIcons(AAssortedTweak_DefaultIcons,MultiTweakItem):
    #--Config Phase -----------------------------------------------------------
    def __init__(self):
        self.activeTypes = ['ALCH','AMMO','APPA','ARMO','BOOK','BSGN',
                            'CLAS','CLOT','FACT','INGR','KEYM','LIGH',
                            'MISC','QUST','SGST','SLGM','WEAP']
        super(AssortedTweak_DefaultIcons,self).__init__()
    #--Patch Phase ------------------------------------------------------------
    def getReadClasses(self):
        """Returns load factory classes needed for reading."""
        return ('ALCH','AMMO','APPA','ARMO','BOOK','BSGN',
                'CLAS','CLOT','FACT','INGR','KEYM','LIGH',
                'MISC','QUST','SGST','SLGM','WEAP',
                )

    def getWriteClasses(self):
        """Returns load factory classes needed for writing."""
        return ('ALCH','AMMO','APPA','ARMO','BOOK','BSGN',
                'CLAS','CLOT','FACT','INGR','KEYM','LIGH',
                'MISC','QUST','SGST','SLGM','WEAP',
                )

    def scanModFile(self,modFile,progress,patchFile):
        mapper = modFile.getLongMapper()
        for blockType in self.activeTypes:
            if blockType not in modFile.tops: continue
            modBlock = getattr(modFile,blockType)
            patchBlock = getattr(patchFile,blockType)
            id_records = patchBlock.id_records
            for record in modBlock.getActiveRecords():
                if mapper(record.fid) not in id_records:
                    record = record.getTypeCopy(mapper)
                    patchBlock.setRecord(record)

    def buildPatch(self,log,progress,patchFile):
        count = {}
        keep = patchFile.getKeeper()
        for type_ in self.activeTypes:
            if type_ not in patchFile.tops: continue
            for record in patchFile.tops[type_].records:
                if getattr(record, 'iconPath', None): continue
                if getattr(record, 'maleIconPath', None): continue
                if getattr(record, 'femaleIconPath', None): continue
                changed = False
                if type_ == 'ALCH':
                    record.iconPath = u"Clutter\\Potions\\IconPotion01.dds"
                    changed = True
                elif type_ == 'AMMO':
                    record.iconPath = u"Weapons\\IronArrow.dds"
                    changed = True
                elif type_ == 'APPA':
                    record.iconPath = u"Clutter\\IconMortarPestle.dds"
                    changed = True
                elif type_ == 'AMMO':
                    record.iconPath = u"Weapons\\IronArrow.dds"
                    changed = True
                elif type_ == 'ARMO':
                    if record.flags.notPlayable: continue
                    #choose based on body flags:
                    if record.flags.upperBody != 0:
                        record.maleIconPath = u"Armor\\Iron\\M\\Cuirass.dds"
                        record.femaleIconPath = u"Armor\\Iron\\F\\Cuirass.dds"
                        changed = True
                    elif record.flags.lowerBody != 0:
                        record.maleIconPath = u"Armor\\Iron\\M\\Greaves.dds"
                        record.femaleIconPath = u"Armor\\Iron\\F\\Greaves.dds"
                        changed = True
                    elif record.flags.head != 0 or record.flags.hair != 0:
                        record.maleIconPath = u"Armor\\Iron\\M\\Helmet.dds"
                        changed = True
                    elif record.flags.hand != 0:
                        record.maleIconPath = u"Armor\\Iron\\M\\Gauntlets.dds"
                        record.femaleIconPath =u"Armor\\Iron\\F\\Gauntlets.dds"
                        changed = True
                    elif record.flags.foot != 0:
                        record.maleIconPath = u"Armor\\Iron\\M\\Boots.dds"
                        changed = True
                    elif record.flags.shield != 0:
                        record.maleIconPath = u"Armor\\Iron\\M\\Shield.dds"
                        changed = True
                    else: #Default icon, probably a token or somesuch
                        record.maleIconPath = u"Armor\\Iron\\M\\Shield.dds"
                        changed = True
                elif type_ in ['BOOK', 'BSGN', 'CLAS']:  # just a random book
                    # icon for class/birthsign as well.
                    record.iconPath = u"Clutter\\iconbook%d.dds" % (
                        random.randint(1, 13))
                    changed = True
                elif type_ == 'CLOT':
                    if record.flags.notPlayable: continue
                    #choose based on body flags:
                    if record.flags.upperBody != 0:
                        record.maleIconPath = \
                            u"Clothes\\MiddleClass\\01\\M\\Shirt.dds"
                        record.femaleIconPath = \
                            u"Clothes\\MiddleClass\\01\\F\\Shirt.dds"
                        changed = True
                    elif record.flags.lowerBody != 0:
                        record.maleIconPath = \
                            u"Clothes\\MiddleClass\\01\\M\\Pants.dds"
                        record.femaleIconPath = \
                            u"Clothes\\MiddleClass\\01\\F\\Pants.dds"
                        changed = True
                    elif record.flags.head or record.flags.hair:
                        record.maleIconPath = \
                            u"Clothes\\MythicDawnrobe\\hood.dds"
                        changed = True
                    elif record.flags.hand != 0:
                        record.maleIconPath = \
                         u"Clothes\\LowerClass\\Jail\\M\\JailShirtHandcuff.dds"
                        changed = True
                    elif record.flags.foot != 0:
                        record.maleIconPath = \
                            u"Clothes\\MiddleClass\\01\\M\\Shoes.dds"
                        record.femaleIconPath = \
                            u"Clothes\\MiddleClass\\01\\F\\Shoes.dds"
                        changed = True
                    elif record.flags.leftRing or record.flags.rightRing:
                        record.maleIconPath = u"Clothes\\Ring\\RingNovice.dds"
                        changed = True
                    else: #amulet
                        record.maleIconPath = \
                            u"Clothes\\Amulet\\AmuletSilver.dds"
                        changed = True
                elif type_ == 'FACT':
                    #todo
                    #changed = True
                    pass
                elif type_ == 'INGR':
                    record.iconPath = u"Clutter\\IconSeeds.dds"
                    changed = True
                elif type_ == 'KEYM':
                    record.iconPath = \
                        [u"Clutter\\Key\\Key.dds", u"Clutter\\Key\\Key02.dds"][
                            random.randint(0, 1)]
                    changed = True
                elif type_ == 'LIGH':
                    if not record.flags.canTake: continue
                    record.iconPath = u"Lights\\IconTorch02.dds"
                    changed = True
                elif type_ == 'MISC':
                    record.iconPath = u"Clutter\\Soulgems\\AzurasStar.dds"
                    changed = True
                elif type_ == 'QUST':
                    if not record.stages: continue
                    record.iconPath = u"Quest\\icon_miscellaneous.dds"
                    changed = True
                elif type_ == 'SGST':
                    record.iconPath = u"IconSigilStone.dds"
                    changed = True
                elif type_ == 'SLGM':
                    record.iconPath = u"Clutter\\Soulgems\\AzurasStar.dds"
                    changed = True
                elif type_ == 'WEAP':
                    if record.weaponType == 0:
                        record.iconPath = u"Weapons\\IronDagger.dds"
                    elif record.weaponType == 1:
                        record.iconPath = u"Weapons\\IronClaymore.dds"
                    elif record.weaponType == 2:
                        record.iconPath = u"Weapons\\IronMace.dds"
                    elif record.weaponType == 3:
                        record.iconPath = u"Weapons\\IronBattleAxe.dds"
                    elif record.weaponType == 4:
                        record.iconPath = u"Weapons\\Staff.dds"
                    elif record.weaponType == 5:
                        record.iconPath = u"Weapons\\IronBow.dds"
                    else: #Should never reach this point
                        record.iconPath = u"Weapons\\IronDagger.dds"
                    changed = True
                if changed:
                    keep(record.fid)
                    srcMod = record.fid[0]
                    count[srcMod] = count.get(srcMod,0) + 1
        self._patchLog(log,count)

class CBash_AssortedTweak_DefaultIcons(AAssortedTweak_DefaultIcons,
                                       CBash_MultiTweakItem):
    """Sets a default icon for any records that don't have any icon
    assigned."""
    name = _(u'Default Icons')
    type_defaultIcon = {
                'ALCH': u"Clutter\\Potions\\IconPotion01.dds",
                'AMMO': u"Weapons\\IronArrow.dds",
                'APPA': u"Clutter\\IconMortarPestle.dds",
                'ARMO': ((u"Armor\\Iron\\M\\Cuirass.dds",
                          u"Armor\\Iron\\F\\Cuirass.dds"),
                         (u"Armor\\Iron\\M\\Greaves.dds",
                          u"Armor\\Iron\\F\\Greaves.dds"),
                         (u"Armor\\Iron\\M\\Helmet.dds",),
                         (u"Armor\\Iron\\M\\Gauntlets.dds",
                          u"Armor\\Iron\\F\\Gauntlets.dds"),
                         (u"Armor\\Iron\\M\\Boots.dds",),
                         (u"Armor\\Iron\\M\\Shield.dds",),
                         (u"Armor\\Iron\\M\\Shield.dds",), #Default Armor icon
                         ),
                'BOOK': u"Clutter\\iconbook%d.dds",
                'BSGN': u"Clutter\\iconbook%d.dds",
                'CLAS': u"Clutter\\iconbook%d.dds",
                'CLOT': ((u"Clothes\\MiddleClass\\01\\M\\Shirt.dds",
                          u"Clothes\\MiddleClass\\01\\F\\Shirt.dds"),
                         (u"Clothes\\MiddleClass\\01\\M\\Pants.dds",
                          u"Clothes\\MiddleClass\\01\\F\\Pants.dds"),
                         (u"Clothes\\MythicDawnrobe\\hood.dds",),
                         (u"Clothes\\LowerClass\\Jail\\M\\"
                          u"JailShirtHandcuff.dds",),
                         (u"Clothes\\MiddleClass\\01\\M\\Shoes.dds",
                          u"Clothes\\MiddleClass\\01\\F\\Shoes.dds"),
                         (u"Clothes\\Ring\\RingNovice.dds",),
                         (u"Clothes\\Amulet\\AmuletSilver.dds",),
                         ),
##                'FACT': u"", ToDo
                'INGR': u"Clutter\\IconSeeds.dds",
                'KEYM': (u"Clutter\\Key\\Key.dds",u"Clutter\\Key\\Key02.dds"),
                'LIGH': u"Lights\\IconTorch02.dds",
                'MISC': u"Clutter\\Soulgems\\AzurasStar.dds",
                'QUST': u"Quest\\icon_miscellaneous.dds",
                'SGST': u"IconSigilStone.dds",
                'SLGM': u"Clutter\\Soulgems\\AzurasStar.dds",
                'WEAP': (u"Weapons\\IronDagger.dds",
                         u"Weapons\\IronClaymore.dds",
                         u"Weapons\\IronMace.dds",
                         u"Weapons\\IronBattleAxe.dds",
                         u"Weapons\\Staff.dds",
                         u"Weapons\\IronBow.dds",
                         ),
                }

    #--Config Phase -----------------------------------------------------------
    def getTypes(self):
        return [_type for _type in self.type_defaultIcon.keys()]

    #--Patch Phase ------------------------------------------------------------
    def apply(self,modFile,record,bashTags):
        """Edits patch file as desired. """
        if getattr(record, 'iconPath', None): return
        if getattr(record, 'maleIconPath', None): return
        if getattr(record, 'femaleIconPath', None): return
        if record._Type == 'LIGH' and not record.IsCanTake: return
        if record._Type == 'QUST' and not record.stages: return
        if record._Type in ['ARMO','CLOT'] and not record.IsPlayable: return
        override = record.CopyAsOverride(self.patchFile)
        if override:
            icons = self.type_defaultIcon[override._Type]
            if isinstance(icons, tuple):
                if override._Type == 'ARMO':
                    #choose based on body flags:
                    if override.IsUpperBody:
                        icons = icons[0]
                    elif override.IsLowerBody:
                        icons = icons[1]
                    elif override.IsHead or record.IsHair:
                        icons = icons[2]
                    elif override.IsHand:
                        icons = icons[3]
                    elif override.IsFoot:
                        icons = icons[4]
                    elif override.IsShield:
                        icons = icons[5]
                    else: #default icon, probably a token or somesuch
                        icons = icons[6]
                elif override._Type == 'CLOT':
                    #choose based on body flags:
                    if override.IsUpperBody:
                        icons = icons[0]
                    elif override.IsLowerBody:
                        icons = icons[1]
                    elif override.IsHead or record.IsHair:
                        icons = icons[2]
                    elif override.IsHand:
                        icons = icons[3]
                    elif override.IsFoot:
                        icons = icons[4]
                    elif override.IsLeftRing or override.IsRightRing:
                        icons = icons[5]
                    else:
                        icons = icons[6]
                elif override._Type == 'KEYM':
                    icons = icons[random.randint(0,1)]
                elif override._Type == 'WEAP':
                    #choose based on weapon type:
                    try:
                        icons = icons[override.weaponType]
                    except IndexError: #just in case
                        icons = icons[0]
            else:
                if override._Type in ['BOOK', 'BSGN', 'CLAS']:  # just a
                    # random book icon for class/birthsign as well.
                    icons = icons % (random.randint(1,13))
            try:
                if isinstance(icons, tuple):
                    if len(icons) == 1:
                        override.maleIconPath = icons[0]
                    else:
                        override.maleIconPath, override.femaleIconPath = icons
                else:
                    override.iconPath = icons
            except ValueError as error:
                print override._Type
                print icons
                print error
                print self.patchFile.Current.Debug_DumpModFiles()
                raise
            mod_count = self.mod_count
            mod_count[modFile.GName] = mod_count.get(modFile.GName,0) + 1
            record.UnloadRecord()
            record._RecordID = override._RecordID

#------------------------------------------------------------------------------
class AAssortedTweak_SetSoundAttenuationLevels(AMultiTweakItem):
    """Sets Sound Attenuation Levels for all records except Nirnroots."""
    #--Config Phase -----------------------------------------------------------
    def __init__(self):
        super(AAssortedTweak_SetSoundAttenuationLevels,self).__init__(
            _(u"Set Sound Attenuation Levels"),
            _(u'The sound attenuation levels will be set to tweak%*current'
              u' level, thereby increasing (or decreasing) the sound volume.'),
            u'Attenuation%:',
            (u'0%', 0),
            (u'5%', 5),
            (u'10%', 10),
            (u'20%', 20),
            (u'50%', 50),
            (u'80%', 80),
            (_(u'Custom'),0),
            )
        self.logMsg = u'* '+_(u'Sounds Modified') + u': %d'

class AssortedTweak_SetSoundAttenuationLevels(
    AAssortedTweak_SetSoundAttenuationLevels, MultiTweakItem):
    #--Patch Phase ------------------------------------------------------------
    def getReadClasses(self):
        """Returns load factory classes needed for reading."""
        return 'SOUN',

    def getWriteClasses(self):
        """Returns load factory classes needed for writing."""
        return 'SOUN',

    def scanModFile(self,modFile,progress,patchFile):
        mapper = modFile.getLongMapper()
        patchBlock = patchFile.SOUN
        id_records = patchBlock.id_records
        for record in modFile.SOUN.getActiveRecords():
            if mapper(record.fid) in id_records: continue
            if record.staticAtten:
                record = record.getTypeCopy(mapper)
                patchBlock.setRecord(record)

    def buildPatch(self,log,progress,patchFile):
        """Edits patch file as desired. Will write to log."""
        count = {}
        keep = patchFile.getKeeper()
        for record in patchFile.SOUN.records:
            if record.staticAtten:
                record.staticAtten = record.staticAtten * \
                                     self.choiceValues[self.chosen][0] / 100
                keep(record.fid)
                srcMod = record.fid[0]
                count[srcMod] = count.get(srcMod,0) + 1
        self._patchLog(log,count)

class CBash_AssortedTweak_SetSoundAttenuationLevels(
    AAssortedTweak_SetSoundAttenuationLevels, CBash_MultiTweakItem):
    name = _(u'Set Sound Attenuation Levels')

    #--Config Phase -----------------------------------------------------------
    def getTypes(self):
        return ['SOUN']

    #--Patch Phase ------------------------------------------------------------
    def apply(self,modFile,record,bashTags):
        """Edits patch file as desired. """
        choice = self.choiceValues[self.chosen][0] / 100
        if choice == 1:  # Prevent any pointless changes if a custom value
            # of 100 is used.
            return
        if record.staticAtten:
            override = record.CopyAsOverride(self.patchFile)
            if override:
                override.staticAtten *= choice
                mod_count = self.mod_count
                mod_count[modFile.GName] = mod_count.get(modFile.GName,0) + 1
                record.UnloadRecord()
                record._RecordID = override._RecordID

#------------------------------------------------------------------------------
class AAssortedTweak_SetSoundAttenuationLevels_NirnrootOnly(AMultiTweakItem):
    """Sets Sound Attenuation Levels for Nirnroots."""
    #--Config Phase -----------------------------------------------------------
    def __init__(self):
        super(AAssortedTweak_SetSoundAttenuationLevels_NirnrootOnly,
              self).__init__(
            _(u"Set Sound Attenuation Levels: Nirnroots Only"),
            _(u'The sound attenuation levels will be set to tweak%*current '
              u'level, thereby increasing (or decreasing) the sound '
              u'volume. This one only affects Nirnroots.'),
            u'Nirnroot Attenuation%:',
            (u'0%', 0),
            (u'5%', 5),
            (u'10%', 10),
            (u'20%', 20),
            (u'50%', 50),
            (u'80%', 80),
            (_(u'Custom'),0),
            )
        self.logMsg = u'* '+_(u'Sounds Modified') + u': %d'

class AssortedTweak_SetSoundAttenuationLevels_NirnrootOnly(
    AAssortedTweak_SetSoundAttenuationLevels_NirnrootOnly, MultiTweakItem):
    #--Patch Phase ------------------------------------------------------------
    def getReadClasses(self):
        """Returns load factory classes needed for reading."""
        return 'SOUN',

    def getWriteClasses(self):
        """Returns load factory classes needed for writing."""
        return 'SOUN',

    def scanModFile(self,modFile,progress,patchFile):
        mapper = modFile.getLongMapper()
        patchBlock = patchFile.SOUN
        id_records = patchBlock.id_records
        for record in modFile.SOUN.getActiveRecords():
            if mapper(record.fid) in id_records: continue
            if record.staticAtten and u'nirnroot' in record.eid.lower():
                record = record.getTypeCopy(mapper)
                patchBlock.setRecord(record)

    def buildPatch(self,log,progress,patchFile):
        """Edits patch file as desired. Will write to log."""
        count = {}
        keep = patchFile.getKeeper()
        for record in patchFile.SOUN.records:
            if record.staticAtten and u'nirnroot' in record.eid.lower():
                record.staticAtten = record.staticAtten * \
                                     self.choiceValues[self.chosen][0] / 100
                keep(record.fid)
                srcMod = record.fid[0]
                count[srcMod] = count.get(srcMod,0) + 1
        self._patchLog(log,count)

class CBash_AssortedTweak_SetSoundAttenuationLevels_NirnrootOnly(
    AAssortedTweak_SetSoundAttenuationLevels_NirnrootOnly,
    CBash_MultiTweakItem):
    name = _(u'Set Sound Attenuation Levels: Nirnroots Only')

    #--Config Phase -----------------------------------------------------------
    def getTypes(self):
        return ['SOUN']

    #--Patch Phase ------------------------------------------------------------
    def apply(self,modFile,record,bashTags):
        """Edits patch file as desired. """
        choice = self.choiceValues[self.chosen][0] / 100
        if choice == 1:  # Prevent any pointless changes if a custom value
            # of 100 is used.
            return
        if record.staticAtten and u'nirnroot' in record.eid.lower() :
            override = record.CopyAsOverride(self.patchFile)
            if override:
                override.staticAtten *= choice
                mod_count = self.mod_count
                mod_count[modFile.GName] = mod_count.get(modFile.GName,0) + 1
                record.UnloadRecord()
                record._RecordID = override._RecordID

#------------------------------------------------------------------------------
class AAssortedTweak_FactioncrimeGoldMultiplier(AMultiTweakItem):
    """Fix factions with unset crimeGoldMultiplier to have a
    crimeGoldMultiplier of 1.0."""

    #--Config Phase -----------------------------------------------------------
    def __init__(self):
        super(AAssortedTweak_FactioncrimeGoldMultiplier,self).__init__(
            _(u"Faction crime Gold Multiplier Fix"),
            _(u'Fix factions with unset crimeGoldMultiplier to have a '
              u'crimeGoldMultiplier of 1.0.'),
            u'FactioncrimeGoldMultiplier',
            (u'1.0',  u'1.0'),
            )
        self.logMsg = u'* '+_(u'Factions fixed') + u': %d'

class AssortedTweak_FactioncrimeGoldMultiplier(
    AAssortedTweak_FactioncrimeGoldMultiplier, MultiTweakItem):
    #--Patch Phase ------------------------------------------------------------
    def getReadClasses(self):
        """Returns load factory classes needed for reading."""
        return 'FACT',

    def getWriteClasses(self):
        """Returns load factory classes needed for writing."""
        return 'FACT',

    def scanModFile(self,modFile,progress,patchFile):
        mapper = modFile.getLongMapper()
        patchRecords = patchFile.FACT
        for record in modFile.FACT.getActiveRecords():
            if not isinstance(record.crimeGoldMultiplier,float):
                record = record.getTypeCopy(mapper)
                patchRecords.setRecord(record)

    def buildPatch(self,log,progress,patchFile):
        """Edits patch file as desired. Will write to log."""
        count = {}
        keep = patchFile.getKeeper()
        for record in patchFile.FACT.records:
            if not isinstance(record.crimeGoldMultiplier,float):
                record.crimeGoldMultiplier = 1.0
                keep(record.fid)
                srcMod = record.fid[0]
                count[srcMod] = count.get(srcMod,0) + 1
        self._patchLog(log,count)

class CBash_AssortedTweak_FactioncrimeGoldMultiplier(
    AAssortedTweak_FactioncrimeGoldMultiplier, CBash_MultiTweakItem):
    name = _(u'Faction crime Gold Multiplier Fix')

    #--Config Phase -----------------------------------------------------------
    def getTypes(self):
        return ['FACT']

    #--Patch Phase ------------------------------------------------------------
    def apply(self,modFile,record,bashTags):
        """Edits patch file as desired."""
        if record.crimeGoldMultiplier is None:
            override = record.CopyAsOverride(self.patchFile)
            if override:
                override.crimeGoldMultiplier = 1.0
                mod_count = self.mod_count
                mod_count[modFile.GName] = mod_count.get(modFile.GName,0) + 1
                record.UnloadRecord()
                record._RecordID = override._RecordID

#------------------------------------------------------------------------------
class AAssortedTweak_LightFadeValueFix(AMultiTweakItem):
    """Remove light flickering for low end machines."""

    #--Config Phase -----------------------------------------------------------
    def __init__(self):
        super(AAssortedTweak_LightFadeValueFix, self).__init__(
            _(u"No Light Fade Value Fix"),
            _(u"Sets Light's Fade values to default of 1.0 if not set."),
            u'NoLightFadeValueFix',
            (u'1.0',  u'1.0'),
            )
        self.logMsg = u'* '+_(u'Lights with fade values added') + u': %d'

class AssortedTweak_LightFadeValueFix(AAssortedTweak_LightFadeValueFix,
                                      MultiTweakItem):
    #--Patch Phase ------------------------------------------------------------
    def getReadClasses(self):
        """Returns load factory classes needed for reading."""
        return 'LIGH',

    def getWriteClasses(self):
        """Returns load factory classes needed for writing."""
        return 'LIGH',

    def scanModFile(self,modFile,progress,patchFile):
        mapper = modFile.getLongMapper()
        patchRecords = patchFile.LIGH
        for record in modFile.LIGH.getActiveRecords():
            if not isinstance(record.fade,float):
                record = record.getTypeCopy(mapper)
                patchRecords.setRecord(record)

    def buildPatch(self,log,progress,patchFile):
        """Edits patch file as desired. Will write to log."""
        count = {}
        keep = patchFile.getKeeper()
        for record in patchFile.LIGH.records:
            if not isinstance(record.fade,float):
                record.fade = 1.0
                keep(record.fid)
                srcMod = record.fid[0]
                count[srcMod] = count.get(srcMod,0) + 1
        self._patchLog(log,count)

class CBash_AssortedTweak_LightFadeValueFix(AAssortedTweak_LightFadeValueFix,
                                            CBash_MultiTweakItem):
    name = _(u'No Light Fade Value Fix')

    #--Config Phase -----------------------------------------------------------
    def getTypes(self):
        return ['LIGH']

    #--Patch Phase ------------------------------------------------------------
    def apply(self,modFile,record,bashTags):
        """Edits patch file as desired. """
        if record.fade is None:
            override = record.CopyAsOverride(self.patchFile)
            if override:
                override.fade = 1.0
                mod_count = self.mod_count
                mod_count[modFile.GName] = mod_count.get(modFile.GName,0) + 1
                record.UnloadRecord()
                record._RecordID = override._RecordID

#------------------------------------------------------------------------------
class AAssortedTweak_TextlessLSCRs(AMultiTweakItem):
    """Removes the description from loading screens."""
    #--Config Phase -----------------------------------------------------------
    def __init__(self):
        super(AAssortedTweak_TextlessLSCRs, self).__init__(
            _(u"No Description Loading Screens"),
            _(u"Removes the description from loading screens."),
            u'NoDescLSCR',
            (u'1.0',  u'1.0'),
            )
        self.logMsg = u'* '+_(u'Loading screens tweaked') + u': %d'

class AssortedTweak_TextlessLSCRs(AAssortedTweak_TextlessLSCRs,MultiTweakItem):
    #--Patch Phase ------------------------------------------------------------
    def getReadClasses(self):
        """Returns load factory classes needed for reading."""
        return 'LSCR',

    def getWriteClasses(self):
        """Returns load factory classes needed for writing."""
        return 'LSCR',

    def scanModFile(self,modFile,progress,patchFile):
        mapper = modFile.getLongMapper()
        patchRecords = patchFile.LSCR
        for record in modFile.LSCR.getActiveRecords():
            if record.text:
                record = record.getTypeCopy(mapper)
                patchRecords.setRecord(record)

    def buildPatch(self,log,progress,patchFile):
        """Edits patch file as desired. Will write to log."""
        count = {}
        keep = patchFile.getKeeper()
        for record in patchFile.LSCR.records:
            if record.text:
                record.text = u''
                keep(record.fid)
                srcMod = record.fid[0]
                count[srcMod] = count.get(srcMod,0) + 1
        self._patchLog(log,count)

class CBash_AssortedTweak_TextlessLSCRs(AAssortedTweak_TextlessLSCRs,
                                        CBash_MultiTweakItem):
    name = _(u"No Description Loading Screens")

    #--Config Phase -----------------------------------------------------------
    def getTypes(self):
        return ['LSCR']

    #--Patch Phase ------------------------------------------------------------
    def apply(self,modFile,record,bashTags):
        """Edits patch file as desired. """
        if record.text:
            override = record.CopyAsOverride(self.patchFile)
            if override:
                override.text = u''
                mod_count = self.mod_count
                mod_count[modFile.GName] = mod_count.get(modFile.GName,0) + 1
                record.UnloadRecord()
                record._RecordID = override._RecordID

class AssortedTweaker(MultiTweaker):
    """Tweaks assorted stuff. Sub-tweaks behave like patchers themselves."""
    scanOrder = 32
    editOrder = 32
    name = _(u'Tweak Assorted')
    text = _(u"Tweak various records in miscellaneous ways.")
    # CONFIG DEFAULTS
    default_isEnabled = True

    if bush.game.fsName == u'Oblivion':
        tweaks = sorted([
            AssortedTweak_ArmorShows(_(u"Armor Shows Amulets"),
                _(u"Prevents armor from hiding amulets."),
                u'armorShowsAmulets',
                ),
            AssortedTweak_ArmorShows(_(u"Armor Shows Rings"),
                _(u"Prevents armor from hiding rings."),
                u'armorShowsRings',
                ),
            AssortedTweak_ClothingShows(_(u"Clothing Shows Amulets"),
                _(u"Prevents Clothing from hiding amulets."),
                u'ClothingShowsAmulets',
                ),
            AssortedTweak_ClothingShows(_(u"Clothing Shows Rings"),
                _(u"Prevents Clothing from hiding rings."),
                u'ClothingShowsRings',
                ),
            AssortedTweak_ArmorPlayable(),
            AssortedTweak_ClothingPlayable(),
            AssortedTweak_BowReach(),
            AssortedTweak_ConsistentRings(),
            AssortedTweak_DarnBooks(),
            AssortedTweak_FogFix(),
            AssortedTweak_NoLightFlicker(),
            AssortedTweak_PotionWeight(),
            AssortedTweak_PotionWeightMinimum(),
            AssortedTweak_StaffWeight(),
            AssortedTweak_SetCastWhenUsedEnchantmentCosts(),
            AssortedTweak_WindSpeed(),
            AssortedTweak_UniformGroundcover(),
            AssortedTweak_HarvestChance(),
            AssortedTweak_IngredientWeight(),
            AssortedTweak_ArrowWeight(),
            AssortedTweak_ScriptEffectSilencer(),
            AssortedTweak_DefaultIcons(),
            AssortedTweak_SetSoundAttenuationLevels(),
            AssortedTweak_SetSoundAttenuationLevels_NirnrootOnly(),
            AssortedTweak_FactioncrimeGoldMultiplier(),
            AssortedTweak_LightFadeValueFix(),
            AssortedTweak_SkyrimStyleWeapons(),
            AssortedTweak_TextlessLSCRs(),
            ],key=lambda a: a.label.lower())

    #--Patch Phase ------------------------------------------------------------
    def getReadClasses(self):
        """Returns load factory classes needed for reading."""
        if not self.isActive: return tuple()
        classNames = [tweak.getReadClasses() for tweak in self.enabledTweaks]
        return sum(classNames,tuple())

    def getWriteClasses(self):
        """Returns load factory classes needed for writing."""
        if not self.isActive: return tuple()
        classTuples = [tweak.getWriteClasses() for tweak in self.enabledTweaks]
        return sum(classTuples,tuple())

    def scanModFile(self,modFile,progress):
        if not self.isActive: return
        for tweak in self.enabledTweaks:
            tweak.scanModFile(modFile,progress,self.patchFile)

class CBash_AssortedTweaker(CBash_MultiTweaker):
    """Tweaks assorted stuff. Sub-tweaks behave like patchers themselves."""
    scanOrder = 32
    editOrder = 32
    name = _(u'Tweak Assorted')
    text = _(u"Tweak various records in miscellaneous ways.")
    # CONFIG DEFAULTS
    default_isEnabled = True

    tweaks = sorted([
        CBash_AssortedTweak_ArmorShows(_(u"Armor Shows Amulets"),
            _(u"Prevents armor from hiding amulets."),
            u'armorShowsAmulets',
            ),
        CBash_AssortedTweak_ArmorShows(_(u"Armor Shows Rings"),
            _(u"Prevents armor from hiding rings."),
            u'armorShowsRings',
            ),
        CBash_AssortedTweak_ClothingShows(_(u"Clothing Shows Amulets"),
            _(u"Prevents Clothing from hiding amulets."),
            u'ClothingShowsAmulets',
            ),
        CBash_AssortedTweak_ClothingShows(_(u"Clothing Shows Rings"),
            _(u"Prevents Clothing from hiding rings."),
            u'ClothingShowsRings',
            ),
        CBash_AssortedTweak_ArmorPlayable(),
        CBash_AssortedTweak_ClothingPlayable(),
        CBash_AssortedTweak_BowReach(),
        CBash_AssortedTweak_ConsistentRings(),
        CBash_AssortedTweak_DarnBooks(),
        CBash_AssortedTweak_FogFix(),
        CBash_AssortedTweak_NoLightFlicker(),
        CBash_AssortedTweak_PotionWeight(),
        CBash_AssortedTweak_PotionWeightMinimum(),
        CBash_AssortedTweak_StaffWeight(),
        CBash_AssortedTweak_SetCastWhenUsedEnchantmentCosts(),
        CBash_AssortedTweak_HarvestChance(),
        CBash_AssortedTweak_WindSpeed(),
        CBash_AssortedTweak_UniformGroundcover(),
        CBash_AssortedTweak_IngredientWeight(),
        CBash_AssortedTweak_ArrowWeight(),
        CBash_AssortedTweak_ScriptEffectSilencer(),
        CBash_AssortedTweak_DefaultIcons(),
        CBash_AssortedTweak_SetSoundAttenuationLevels(),
        CBash_AssortedTweak_SetSoundAttenuationLevels_NirnrootOnly(),
        CBash_AssortedTweak_FactioncrimeGoldMultiplier(),
        CBash_AssortedTweak_LightFadeValueFix(),
        CBash_AssortedTweak_SkyrimStyleWeapons(),
        CBash_AssortedTweak_TextlessLSCRs(),
        ],key=lambda a: a.label.lower())

    #--Config Phase -----------------------------------------------------------
    def initPatchFile(self,patchFile,loadMods):
        self.patchFile = patchFile
        for tweak in self.tweaks:
            tweak.patchFile = patchFile
