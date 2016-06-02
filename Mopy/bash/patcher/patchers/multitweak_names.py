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
to the Names Multitweaker - as well as the NamesTweaker itself."""

import re
# Internal
from ... import load_order
from ...patcher.base import AMultiTweakItem, AMultiTweaker
from ...patcher.patchers.base import MultiTweakItem, CBash_MultiTweakItem
from ...patcher.patchers.base import MultiTweaker, CBash_MultiTweaker

class _AMultiTweakItem_Names(MultiTweakItem):

    def _patchLog(self, log, count):
        # --Log - Notice self.logMsg is not used - so (apart from
        # NamesTweak_BodyTags and NamesTweak_Body where it is not defined in
        # the ANamesTweakXX common superclass) self.logMsg wastes space and the
        # CBash implementations which _do_ use it produce different logs. TODO:
        # unify C/P logs by using self.logMsg (mind the classes mentioned)
        log(u'* %s: %d' % (self.label,sum(count.values())))
        for srcMod in load_order.get_ordered(count.keys()):
            log(u'  * %s: %d' % (srcMod.s,count[srcMod]))

# Patchers: 30 ----------------------------------------------------------------
class ANamesTweak_BodyTags(AMultiTweakItem):
    #--Config Phase -----------------------------------------------------------
    def __init__(self):
        super(ANamesTweak_BodyTags, self).__init__(
            _(u"Body Part Codes"),
            _(u'Sets body part codes used by Armor/Clothes name tweaks. A: '
            u'Amulet, R: Ring, etc.'),
            u'bodyTags',
            (u'ARGHTCCPBS',u'ARGHTCCPBS'),
            (u'ABGHINOPSL',u'ABGHINOPSL'),)

class NamesTweak_BodyTags(ANamesTweak_BodyTags,MultiTweakItem):

    def buildPatch(self,log,progress,patchFile):
        """Edits patch file as desired. Will write to log."""
        patchFile.bodyTags = self.choiceValues[self.chosen][0]

class CBash_NamesTweak_BodyTags(ANamesTweak_BodyTags,CBash_MultiTweakItem):

    def buildPatchLog(self,log):
        """Will write to log."""
        pass

#------------------------------------------------------------------------------
class NamesTweak_Body(_AMultiTweakItem_Names):
    """Names tweaker for armor and clothes."""
    #--Patch Phase ------------------------------------------------------------
    def getReadClasses(self):
        """Returns load factory classes needed for reading."""
        return self.key,

    def getWriteClasses(self):
        """Returns load factory classes needed for writing."""
        return self.key,

    def scanModFile(self,modFile,progress,patchFile):
        mapper = modFile.getLongMapper()
        patchBlock = getattr(patchFile,self.key)
        id_records = patchBlock.id_records
        for record in getattr(modFile,self.key).getActiveRecords():
            if record.full and mapper(record.fid) not in id_records:
                record = record.getTypeCopy(mapper)
                patchBlock.setRecord(record)

    def buildPatch(self,log,progress,patchFile):
        """Edits patch file as desired. Will write to log."""
        count = {}
        format_ = self.choiceValues[self.chosen][0]
        showStat = u'%02d' in format_
        keep = patchFile.getKeeper()
        codes = getattr(patchFile,'bodyTags','ARGHTCCPBS')
        amulet,ring,gloves,head,tail,robe,chest,pants,shoes,shield = [
            x for x in codes]
        for record in getattr(patchFile,self.key).records:
            if not record.full: continue
            if record.full[0] in u'+-=.()[]': continue
            flags = record.flags
            if flags.head or flags.hair: type_ = head
            elif flags.rightRing or flags.leftRing: type_ = ring
            elif flags.amulet: type_ = amulet
            elif flags.upperBody and flags.lowerBody: type_ = robe
            elif flags.upperBody: type_ = chest
            elif flags.lowerBody: type_ = pants
            elif flags.hand: type_ = gloves
            elif flags.foot: type_ = shoes
            elif flags.tail: type_ = tail
            elif flags.shield: type_ = shield
            else: continue
            if record.recType == 'ARMO':
                type_ += 'LH'[record.flags.heavyArmor]
            if showStat:
                record.full = format_ % (
                    type_, record.strength / 100) + record.full
            else:
                record.full = format_ % type_ + record.full
            keep(record.fid)
            srcMod = record.fid[0]
            count[srcMod] = count.get(srcMod,0) + 1
        self._patchLog(log, count)

class CBash_NamesTweak_Body(CBash_MultiTweakItem):
    """Names tweaker for armor and clothes."""

    #--Config Phase -----------------------------------------------------------
    def __init__(self, label, tip, key, *choices, **kwargs):
        super(CBash_NamesTweak_Body, self).__init__(label, tip, key, *choices,
                                                    **kwargs)
        self.logMsg = u'* ' + _(u'%(record_type)s Renamed') % {
            'record_type': (u'%s ' % self.key)} + u': %d'

    def getTypes(self):
        return [self.key]

    #--Patch Phase ------------------------------------------------------------
    def apply(self,modFile,record,bashTags):
        """Edits patch file as desired. """
        if record.IsNonPlayable: return
        newFull = record.full
        if newFull:
            if record.IsHead or record.IsHair: type_ = self.head
            elif record.IsRightRing or record.IsLeftRing: type_ = self.ring
            elif record.IsAmulet: type_ = self.amulet
            elif record.IsUpperBody and record.IsLowerBody: type_ = self.robe
            elif record.IsUpperBody: type_ = self.chest
            elif record.IsLowerBody: type_ = self.pants
            elif record.IsHand: type_ = self.gloves
            elif record.IsFoot: type_ = self.shoes
            elif record.IsTail: type_ = self.tail
            elif record.IsShield: type_ = self.shield
            else: return
            if record._Type == 'ARMO':
                type_ += 'LH'[record.IsHeavyArmor]
            if self.showStat:
                newFull = self.format % (
                    type_, record.strength / 100) + newFull
            else:
                newFull = self.format % type_ + newFull
            if record.full != newFull:
                override = record.CopyAsOverride(self.patchFile)
                if override:
                    override.full = newFull
                    mod_count = self.mod_count
                    mod_count[modFile.GName] = mod_count.get(modFile.GName,
                                                             0) + 1
                    record.UnloadRecord()
                    record._RecordID = override._RecordID

#------------------------------------------------------------------------------
class ANamesTweak_Potions(AMultiTweakItem):
    """Names tweaker for potions."""
    reOldLabel = re.compile(u'^(-|X) ',re.U)
    reOldEnd = re.compile(u' -$',re.U)

    #--Config Phase -----------------------------------------------------------
    def __init__(self):
        super(ANamesTweak_Potions, self).__init__(_(u"Potions"),
            _(u'Label potions to sort by type and effect.'),
            'ALCH',
            (_(u'XD Illness'),  u'%s '),
            (_(u'XD. Illness'), u'%s. '),
            (_(u'XD - Illness'),u'%s - '),
            (_(u'(XD) Illness'),u'(%s) '),
            )
        self.logMsg = u'* ' + _(u'%(record_type)s Renamed') % {
            'record_type': (u'%s ' % self.key)} + u': %d'

class NamesTweak_Potions(ANamesTweak_Potions,_AMultiTweakItem_Names):
    #--Patch Phase ------------------------------------------------------------
    def getReadClasses(self):
        """Returns load factory classes needed for reading."""
        return 'ALCH',

    def getWriteClasses(self):
        """Returns load factory classes needed for writing."""
        return 'ALCH',

    def scanModFile(self,modFile,progress,patchFile):
        mapper = modFile.getLongMapper()
        patchBlock = patchFile.ALCH
        id_records = patchBlock.id_records
        for record in modFile.ALCH.getActiveRecords():
            if mapper(record.fid) in id_records: continue
            record = record.getTypeCopy(mapper)
            patchBlock.setRecord(record)

    def buildPatch(self,log,progress,patchFile):
        """Edits patch file as desired. Will write to log."""
        count = {}
        format_ = self.choiceValues[self.chosen][0]
        hostileEffects = patchFile.getMgefHostiles()
        keep = patchFile.getKeeper()
        reOldLabel = self.__class__.reOldLabel
        reOldEnd = self.__class__.reOldEnd
        mgef_school = patchFile.getMgefSchool()
        for record in patchFile.ALCH.records:
            if not record.full: continue
            school = 6 #--Default to 6 (U: unknown)
            for index,effect in enumerate(record.effects):
                effectId = effect.name
                if index == 0:
                    if effect.scriptEffect:
                        school = effect.scriptEffect.school
                    else:
                        school = mgef_school.get(effectId,6)
                #--Non-hostile effect?
                if effect.scriptEffect:
                    if not effect.scriptEffect.flags.hostile:
                        isPoison = False
                        break
                elif effectId not in hostileEffects:
                    isPoison = False
                    break
            else:
                isPoison = True
            full = reOldLabel.sub(u'',record.full) #--Remove existing label
            full = reOldEnd.sub(u'',full)
            if record.flags.isFood:
                record.full = u'.'+full
            else:
                label = (u'X' if isPoison else u'') + u'ACDIMRU'[school]
                record.full = format_ % label + full
            keep(record.fid)
            srcMod = record.fid[0]
            count[srcMod] = count.get(srcMod,0) + 1
        self._patchLog(log, count)

class CBash_NamesTweak_Potions(ANamesTweak_Potions,CBash_MultiTweakItem):
    #--Config Phase -----------------------------------------------------------
    def getTypes(self):
        return ['ALCH']

    #--Patch Phase ------------------------------------------------------------
    def apply(self,modFile,record,bashTags):
        """Edits patch file as desired. """
        newFull = record.full
        if newFull:
            mgef_school = self.patchFile.mgef_school
            hostileEffects = self.patchFile.hostileEffects
            schoolType = 6 #--Default to 6 (U: unknown)
            for index,effect in enumerate(record.effects):
                effectId = effect.name
                if index == 0:
                    if effect.script:
                        schoolType = effect.schoolType
                    else:
                        schoolType = mgef_school.get(effectId,6)
                #--Non-hostile effect?
                if effect.script:
                    if not effect.IsHostile:
                        isPoison = False
                        break
                elif effectId not in hostileEffects:
                    isPoison = False
                    break
            else:
                isPoison = True
            newFull = self.reOldLabel.sub(u'',newFull) #--Remove existing label
            newFull = self.reOldEnd.sub(u'',newFull)
            if record.IsFood:
                newFull = u'.' + newFull
            else:
                label = (u'X' if isPoison else u'') + u'ACDIMRU'[schoolType]
                newFull = self.format % label + newFull
            if record.full != newFull:
                override = record.CopyAsOverride(self.patchFile)
                if override:
                    override.full = newFull
                    mod_count = self.mod_count
                    mod_count[modFile.GName] = mod_count.get(modFile.GName,
                                                             0) + 1
                    record.UnloadRecord()
                    record._RecordID = override._RecordID

#------------------------------------------------------------------------------
reSpell = re.compile(u'^(\([ACDIMR]\d\)|\w{3,6}:) ',re.U) # compile once

class ANamesTweak_Scrolls(AMultiTweakItem):
    reOldLabel = reSpell
    #--Config Phase -----------------------------------------------------------
    def __init__(self):
        super(ANamesTweak_Scrolls,self).__init__(_(u"Notes and Scrolls"),
            _(u'Mark notes and scrolls to sort separately from books'),
            u'scrolls',
            (_(u'~Fire Ball'),    u'~'),
            (_(u'~D Fire Ball'),  u'~%s '),
            (_(u'~D. Fire Ball'), u'~%s. '),
            (_(u'~D - Fire Ball'),u'~%s - '),
            (_(u'~(D) Fire Ball'),u'~(%s) '),
            (u'----',u'----'),
            (_(u'.Fire Ball'),    u'.'),
            (_(u'.D Fire Ball'),  u'.%s '),
            (_(u'.D. Fire Ball'), u'.%s. '),
            (_(u'.D - Fire Ball'),u'.%s - '),
            (_(u'.(D) Fire Ball'),u'.(%s) '),
            )
        self.logMsg = u'* '+_(u'Items Renamed') + u': %d'

    def save_tweak_config(self, configs):
        """Save config to configs dictionary."""
        super(ANamesTweak_Scrolls,self).save_tweak_config(configs)
        rawFormat = self.choiceValues[self.chosen][0]
        self.orderFormat = (u'~.',u'.~')[rawFormat[0] == u'~']
        self.magicFormat = rawFormat[1:]

class NamesTweak_Scrolls(ANamesTweak_Scrolls,_AMultiTweakItem_Names):
    #--Patch Phase ------------------------------------------------------------
    def getReadClasses(self):
        """Returns load factory classes needed for reading."""
        return 'BOOK','ENCH',

    def getWriteClasses(self):
        """Returns load factory classes needed for writing."""
        return 'BOOK','ENCH',

    def scanModFile(self,modFile,progress,patchFile):
        mapper = modFile.getLongMapper()
        #--Scroll Enchantments
        if self.magicFormat:
            patchBlock = patchFile.ENCH
            id_records = patchBlock.id_records
            for record in modFile.ENCH.getActiveRecords():
                if mapper(record.fid) in id_records: continue
                if record.itemType == 0:
                    record = record.getTypeCopy(mapper)
                    patchBlock.setRecord(record)
        #--Books
        patchBlock = patchFile.BOOK
        id_records = patchBlock.id_records
        for record in modFile.BOOK.getActiveRecords():
            if mapper(record.fid) in id_records: continue
            if record.flags.isScroll and not record.flags.isFixed:
                record = record.getTypeCopy(mapper)
                patchBlock.setRecord(record)

    def buildPatch(self,log,progress,patchFile):
        """Edits patch file as desired. Will write to log."""
        count = {}
        reOldLabel = self.__class__.reOldLabel
        orderFormat, magicFormat = self.orderFormat, self.magicFormat
        keep = patchFile.getKeeper()
        id_ench = patchFile.ENCH.id_records
        mgef_school = patchFile.getMgefSchool()
        for record in patchFile.BOOK.records:
            if not record.full or not record.flags.isScroll or \
                    record.flags.isFixed: continue
            #--Magic label
            isEnchanted = bool(record.enchantment)
            if magicFormat and isEnchanted:
                school = 6 #--Default to 6 (U: unknown)
                enchantment = id_ench.get(record.enchantment)
                if enchantment and enchantment.effects:
                    effect = enchantment.effects[0]
                    effectId = effect.name
                    if effect.scriptEffect:
                        school = effect.scriptEffect.school
                    else:
                        school = mgef_school.get(effectId,6)
                record.full = reOldLabel.sub(u'',record.full) #--Remove
                # existing label
                record.full = magicFormat % 'ACDIMRU'[school] + record.full
            #--Ordering
            record.full = orderFormat[isEnchanted] + record.full
            keep(record.fid)
            srcMod = record.fid[0]
            count[srcMod] = count.get(srcMod,0) + 1
        self._patchLog(log, count)

class CBash_NamesTweak_Scrolls(ANamesTweak_Scrolls,CBash_MultiTweakItem):
    """Names tweaker for scrolls."""

    #--Config Phase -----------------------------------------------------------
    def getTypes(self):
        return ['BOOK']

    #--Patch Phase ------------------------------------------------------------
    def apply(self,modFile,record,bashTags):
        """Edits patch file as desired. """
        newFull = record.full
        if newFull and record.IsScroll and not record.IsFixed:
            #--Magic label
            isEnchanted = bool(record.enchantment)
            magicFormat = self.magicFormat
            if magicFormat and isEnchanted:
                schoolType = 6 #--Default to 6 (U: unknown)
                enchantment = record.enchantment
                if enchantment:
                    enchantment = self.patchFile.Current.LookupRecords(
                        enchantment)
                    if enchantment:
                        #Get the winning record
                        enchantment = enchantment[0]
                        Effects = enchantment.effects
                    else:
                        Effects = None
                    if Effects:
                        effect = Effects[0]
                        if effect.script:
                            schoolType = effect.schoolType
                        else:
                            schoolType = self.patchFile.mgef_school.get(
                                effect.name, 6)
                newFull = self.__class__.reOldLabel.sub(u'',newFull) #--Remove
                # existing label
                newFull = magicFormat % u'ACDIMRU'[schoolType] + newFull
            #--Ordering
            newFull = self.orderFormat[isEnchanted] + newFull
            if record.full != newFull:
                override = record.CopyAsOverride(self.patchFile)
                if override:
                    override.full = newFull
                    mod_count = self.mod_count
                    mod_count[modFile.GName] = mod_count.get(modFile.GName,
                                                             0) + 1
                    record.UnloadRecord()
                    record._RecordID = override._RecordID

#------------------------------------------------------------------------------
class ANamesTweak_Spells(AMultiTweakItem):
    """Names tweaker for spells."""
    #--Config Phase -----------------------------------------------------------
    reOldLabel = reSpell
    def __init__(self):
        super(ANamesTweak_Spells, self).__init__(_(u"Spells"),
            _(u'Label spells to sort by school and level.'),
            'SPEL',
            (_(u'Fire Ball'),  u'NOTAGS'),
            (u'----',u'----'),
            (_(u'D Fire Ball'),  u'%s '),
            (_(u'D. Fire Ball'), u'%s. '),
            (_(u'D - Fire Ball'),u'%s - '),
            (_(u'(D) Fire Ball'),u'(%s) '),
            (u'----',u'----'),
            (_(u'D2 Fire Ball'),  u'%s%d '),
            (_(u'D2. Fire Ball'), u'%s%d. '),
            (_(u'D2 - Fire Ball'),u'%s%d - '),
            (_(u'(D2) Fire Ball'),u'(%s%d) '),
            )
        self.logMsg = u'* '+_(u'Spells Renamed') + u': %d'

class NamesTweak_Spells(ANamesTweak_Spells,_AMultiTweakItem_Names):
    #--Patch Phase ------------------------------------------------------------
    def getReadClasses(self):
        """Returns load factory classes needed for reading."""
        return 'SPEL',

    def getWriteClasses(self):
        """Returns load factory classes needed for writing."""
        return 'SPEL',

    def scanModFile(self,modFile,progress,patchFile):
        mapper = modFile.getLongMapper()
        patchBlock = patchFile.SPEL
        id_records = patchBlock.id_records
        for record in modFile.SPEL.getActiveRecords():
            if mapper(record.fid) in id_records: continue
            if record.spellType == 0:
                record = record.getTypeCopy(mapper)
                patchBlock.setRecord(record)

    def buildPatch(self,log,progress,patchFile):
        """Edits patch file as desired. Will write to log."""
        count = {}
        format_ = self.choiceValues[self.chosen][0]
        removeTags = u'%s' not in format_
        showLevel = u'%d' in format_
        keep = patchFile.getKeeper()
        reOldLabel = self.__class__.reOldLabel
        mgef_school = patchFile.getMgefSchool()
        for record in patchFile.SPEL.records:
            if record.spellType != 0 or not record.full: continue
            school = 6 #--Default to 6 (U: unknown)
            if record.effects:
                effect = record.effects[0]
                effectId = effect.name
                if effect.scriptEffect:
                    school = effect.scriptEffect.school
                else:
                    school = mgef_school.get(effectId,6)
            newFull = reOldLabel.sub(u'',record.full) #--Remove existing label
            if not removeTags:
                if showLevel:
                    newFull = format_ % (
                        u'ACDIMRU'[school], record.level) + newFull
                else:
                    newFull = format_ % u'ACDIMRU'[school] + newFull
            if newFull != record.full:
                record.full = newFull
                keep(record.fid)
                srcMod = record.fid[0]
                count[srcMod] = count.get(srcMod,0) + 1
        self._patchLog(log, count)

class CBash_NamesTweak_Spells(ANamesTweak_Spells,CBash_MultiTweakItem):
    #--Config Phase -----------------------------------------------------------
    def getTypes(self):
        return ['SPEL']

    def save_tweak_config(self, configs):
        """Save config to configs dictionary."""
        super(CBash_NamesTweak_Spells, self).save_tweak_config(configs)
        self.format = self.choiceValues[self.chosen][0]
        self.removeTags = u'%s' not in self.format
        self.showLevel = u'%d' in self.format

    #--Patch Phase ------------------------------------------------------------
    def apply(self,modFile,record,bashTags):
        """Edits patch file as desired. """
        newFull = record.full
        if newFull and record.IsSpell:
            #--Magic label
            schoolType = 6 #--Default to 6 (U: unknown)
            Effects = record.effects
            if Effects:
                effect = Effects[0]
                if effect.script:
                    schoolType = effect.schoolType
                else:
                    schoolType = self.patchFile.mgef_school.get(effect.name,6)
            newFull = self.__class__.reOldLabel.sub(u'',newFull) #--Remove
            # existing label
            if not self.removeTags:
                if self.showLevel:
                    newFull = self.format % (
                        u'ACDIMRU'[schoolType], record.levelType) + newFull
                else:
                    newFull = self.format % u'ACDIMRU'[schoolType] + newFull

            if record.full != newFull:
                override = record.CopyAsOverride(self.patchFile)
                if override:
                    override.full = newFull
                    mod_count = self.mod_count
                    mod_count[modFile.GName] = mod_count.get(modFile.GName,
                                                             0) + 1
                    record.UnloadRecord()
                    record._RecordID = override._RecordID

#------------------------------------------------------------------------------
class ANamesTweak_Weapons(AMultiTweakItem):
    """Names tweaker for weapons and ammo."""
    #--Config Phase -----------------------------------------------------------
    def __init__(self):
        super(ANamesTweak_Weapons, self).__init__(_(u"Weapons"),
            _(u'Label ammo and weapons to sort by type and damage.'),
            u'WEAP',
            (_(u'B Iron Bow'),  u'%s '),
            (_(u'B. Iron Bow'), u'%s. '),
            (_(u'B - Iron Bow'),u'%s - '),
            (_(u'(B) Iron Bow'),u'(%s) '),
            (u'----',u'----'),
            (_(u'B08 Iron Bow'),  u'%s%02d '),
            (_(u'B08. Iron Bow'), u'%s%02d. '),
            (_(u'B08 - Iron Bow'),u'%s%02d - '),
            (_(u'(B08) Iron Bow'),u'(%s%02d) '),
            )
        self.logMsg = u'* '+_(u'Items Renamed') + u': %d'

class NamesTweak_Weapons(ANamesTweak_Weapons,_AMultiTweakItem_Names):
    #--Patch Phase ------------------------------------------------------------
    def getReadClasses(self):
        """Returns load factory classes needed for reading."""
        return 'AMMO','WEAP',

    def getWriteClasses(self):
        """Returns load factory classes needed for writing."""
        return 'AMMO','WEAP',

    def scanModFile(self,modFile,progress,patchFile):
        mapper = modFile.getLongMapper()
        for blockType in ('AMMO','WEAP'):
            modBlock = getattr(modFile,blockType)
            patchBlock = getattr(patchFile,blockType)
            id_records = patchBlock.id_records
            for record in modBlock.getActiveRecords():
                if mapper(record.fid) not in id_records:
                    record = record.getTypeCopy(mapper)
                    patchBlock.setRecord(record)

    def buildPatch(self,log,progress,patchFile):
        """Edits patch file as desired. Will write to log."""
        count = {}
        format_ = self.choiceValues[self.chosen][0]
        showStat = u'%02d' in format_
        keep = patchFile.getKeeper()
        for record in patchFile.AMMO.records:
            if not record.full: continue
            if record.full[0] in u'+-=.()[]': continue
            if showStat:
                record.full = format_ % (u'A',record.damage) + record.full
            else:
                record.full = format_ % u'A' + record.full
            keep(record.fid)
            srcMod = record.fid[0]
            count[srcMod] = count.get(srcMod,0) + 1
        for record in patchFile.WEAP.records:
            if not record.full: continue
            if showStat:
                record.full = format_ % (
                    u'CDEFGB'[record.weaponType], record.damage) + record.full
            else:
                record.full = format_ % u'CDEFGB'[
                    record.weaponType] + record.full
            keep(record.fid)
            srcMod = record.fid[0]
            count[srcMod] = count.get(srcMod,0) + 1
        self._patchLog(log, count)

class CBash_NamesTweak_Weapons(ANamesTweak_Weapons,CBash_MultiTweakItem):
    #--Config Phase -----------------------------------------------------------
    def getTypes(self):
        return ['AMMO','WEAP']

    def save_tweak_config(self, configs):
        """Save config to configs dictionary."""
        super(CBash_NamesTweak_Weapons, self).save_tweak_config(configs)
        self.format = self.choiceValues[self.chosen][0]
        self.showStat = u'%02d' in self.format

    #--Patch Phase ------------------------------------------------------------
    def apply(self,modFile,record,bashTags):
        """Edits patch file as desired. """
        newFull = record.full
        if newFull:
            if record._Type == 'AMMO':
                if newFull[0] in u'+-=.()[]': return
                type_ = 6
            else:
                type_ = record.weaponType
            if self.showStat:
                newFull = self.format % (
                    u'CDEFGBA'[type_], record.damage) + newFull
            else:
                newFull = self.format % u'CDEFGBA'[type_] + newFull
            if record.full != newFull:
                override = record.CopyAsOverride(self.patchFile)
                if override:
                    override.full = newFull
                    mod_count = self.mod_count
                    mod_count[modFile.GName] = mod_count.get(modFile.GName,
                                                             0) + 1
                    record.UnloadRecord()
                    record._RecordID = override._RecordID

#------------------------------------------------------------------------------
class ATextReplacer(AMultiTweakItem):
    """Base class for replacing any text via regular expressions."""
    #--Config Phase -----------------------------------------------------------
    def __init__(self, reMatch, reReplace, label, tip, key, choices):
        super(ATextReplacer, self).__init__(label, tip, key, choices)
        self.reMatch = reMatch
        self.reReplace = reReplace
        self.logMsg = u'* '+_(u'Items Renamed') + u': %d'

class TextReplacer(ATextReplacer,_AMultiTweakItem_Names):
    #--Config Phase -----------------------------------------------------------
    def __init__(self, reMatch, reReplace, label, tip, key, choices):
        super(TextReplacer, self).__init__(reMatch, reReplace, label, tip, key,
                                           choices)
        self.activeTypes = ['ALCH','AMMO','APPA','ARMO','BOOK','BSGN',
                            'CLAS','CLOT','CONT','CREA','DOOR',
                            'ENCH','EYES','FACT','FLOR','FURN','GMST',
                            'HAIR','INGR','KEYM','LIGH','LSCR','MGEF',
                            'MISC','NPC_','QUST','RACE','SCPT','SGST',
                            'SKIL','SLGM','SPEL','WEAP']

    #--Patch Phase ------------------------------------------------------------
    def getReadClasses(self):
        """Returns load factory classes needed for reading."""
        return tuple(self.activeTypes)

    def getWriteClasses(self):
        """Returns load factory classes needed for writing."""
        return tuple(self.activeTypes)

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
        reMatch = re.compile(self.reMatch)
        reReplace = self.reReplace
        for type_ in self.activeTypes:
            if type_ not in patchFile.tops: continue
            for record in patchFile.tops[type_].records:
                changed = False
                if hasattr(record, 'full'):
                    changed = reMatch.search(record.full or u'')
                if not changed:
                    if hasattr(record, 'effects'):
                        Effects = record.effects
                        for effect in Effects:
                            try:
                                changed = reMatch.search(
                                    effect.scriptEffect.full or u'')
                            except AttributeError:
                                continue
                            if changed: break
                if not changed:
                    if hasattr(record, 'text'):
                        changed = reMatch.search(record.text or u'')
                if not changed:
                    if hasattr(record, 'description'):
                        changed = reMatch.search(record.description or u'')
                if not changed:
                    if type_ == 'GMST' and record.eid[0] == u's':
                        changed = reMatch.search(record.value or u'')
                if not changed:
                    if hasattr(record, 'stages'):
                        Stages = record.stages
                        for stage in Stages:
                            for entry in stage.entries:
                                changed = reMatch.search(entry.text or u'')
                                if changed: break
                if not changed:
                    if type_ == 'SKIL':
                        changed = reMatch.search(record.apprentice or u'')
                        if not changed:
                            changed = reMatch.search(record.journeyman or u'')
                        if not changed:
                            changed = reMatch.search(record.expert or u'')
                        if not changed:
                            changed = reMatch.search(record.master or u'')
                if changed:
                    if hasattr(record, 'full'):
                        newString = record.full
                        if record:
                            record.full = reMatch.sub(reReplace, newString)
                    if hasattr(record, 'effects'):
                        Effects = record.effects
                        for effect in Effects:
                            try:
                                newString = effect.scriptEffect.full
                            except AttributeError:
                                continue
                            if newString:
                                effect.scriptEffect.full = reMatch.sub(
                                    reReplace, newString)
                    if hasattr(record, 'text'):
                        newString = record.text
                        if newString:
                            record.text = reMatch.sub(reReplace, newString)
                    if hasattr(record, 'description'):
                        newString = record.description
                        if newString:
                            record.description = reMatch.sub(reReplace,
                                                             newString)
                    if type_ == 'GMST' and record.eid[0] == u's':
                        newString = record.value
                        if newString:
                            record.value = reMatch.sub(reReplace, newString)
                    if hasattr(record, 'stages'):
                        Stages = record.stages
                        for stage in Stages:
                            for entry in stage.entries:
                                newString = entry.text
                                if newString:
                                    entry.text = reMatch.sub(reReplace,
                                                             newString)
                    if type_ == 'SKIL':
                        newString = record.apprentice
                        if newString:
                            record.apprentice = reMatch.sub(reReplace,
                                                            newString)
                        newString = record.journeyman
                        if newString:
                            record.journeyman = reMatch.sub(reReplace,
                                                            newString)
                        newString = record.expert
                        if newString:
                            record.expert = reMatch.sub(reReplace, newString)
                        newString = record.master
                        if newString:
                            record.master = reMatch.sub(reReplace, newString)
                    keep(record.fid)
                    srcMod = record.fid[0]
                    count[srcMod] = count.get(srcMod,0) + 1
        self._patchLog(log, count)

class CBash_TextReplacer(ATextReplacer,CBash_MultiTweakItem):
    #--Config Phase -----------------------------------------------------------
    def getTypes(self):
        ##: note it differs only in 'CELLS' from TextReplacer.activeTypes
        return ['ALCH','AMMO','APPA','ARMO','BOOK','BSGN',
                'CELLS','CLAS','CLOT','CONT','CREA','DOOR',
                'ENCH','EYES','FACT','FLOR','FURN','GMST',
                'HAIR','INGR','KEYM','LIGH','LSCR','MGEF',
                'MISC','NPC_','QUST','RACE','SCPT','SGST',
                'SKIL','SLGM','SPEL','WEAP']

    def save_tweak_config(self, configs):
        """Save config to configs dictionary."""
        super(CBash_TextReplacer, self).save_tweak_config(configs)
        self.format = self.choiceValues[self.chosen][0]
        self.showStat = u'%02d' in self.format

    #--Patch Phase ------------------------------------------------------------
    def apply(self,modFile,record,bashTags):
        """Edits patch file as desired. """
        reMatch = re.compile(self.reMatch)
        changed = False
        if hasattr(record, 'full'):
            changed = reMatch.search(record.full or u'')
        if not changed:
            if hasattr(record, 'effects'):
                Effects = record.effects
                for effect in Effects:
                    changed = reMatch.search(effect.full or u'')
                    if changed: break
        if not changed:
            if hasattr(record, 'text'):
                changed = reMatch.search(record.text or u'')
        if not changed:
            if hasattr(record, 'description'):
                changed = reMatch.search(record.description or u'')
        if not changed:
            if record._Type == 'GMST' and record.eid[0] == u's':
                changed = reMatch.search(record.value or u'')
        if not changed:
            if hasattr(record, 'stages'):
                Stages = record.stages
                for stage in Stages:
                    for entry in stage.entries:
                        changed = reMatch.search(entry.text or u'')
                        if changed: break
##### CRUFT: is this code needed ?
##                        compiled = entry.compiled_p
##                        if compiled:
##                            changed = reMatch.search(struct.pack('B' * len(compiled), *compiled) or '')
##                            if changed: break
##                        changed = reMatch.search(entry.scriptText or '')
##                        if changed: break
##        if not changed:
##            if hasattr(record, 'scriptText'):
##                changed = reMatch.search(record.scriptText or '')
##                if not changed:
##                    compiled = record.compiled_p
##                    changed = reMatch.search(struct.pack('B' * len(compiled), *compiled) or '')
        if not changed:
            if record._Type == 'SKIL':
                changed = reMatch.search(record.apprentice or u'')
                if not changed:
                    changed = reMatch.search(record.journeyman or u'')
                if not changed:
                    changed = reMatch.search(record.expert or u'')
                if not changed:
                    changed = reMatch.search(record.master or u'')

        # Could support DIAL/INFO as well, but skipping since they're often
        # voiced as well
        if changed:
            override = record.CopyAsOverride(self.patchFile)
            if override:
                if hasattr(override, 'full'):
                    newString = override.full
                    if newString:
                        override.full = reMatch.sub(self.reReplace, newString)
                if hasattr(override, 'effects'):
                    Effects = override.effects
                    for effect in Effects:
                        newString = effect.full
                        if newString:
                            effect.full = reMatch.sub(self.reReplace, newString)
                if hasattr(override, 'text'):
                    newString = override.text
                    if newString:
                        override.text = reMatch.sub(self.reReplace, newString)
                if hasattr(override, 'description'):
                    newString = override.description
                    if newString:
                        override.description = reMatch.sub(self.reReplace,
                                                           newString)
                if override._Type == 'GMST' and override.eid[0] == u's':
                    newString = override.value
                    if newString:
                        override.value = reMatch.sub(self.reReplace, newString)
                if hasattr(override, 'stages'):
                    Stages = override.stages
                    for stage in Stages:
                        for entry in stage.entries:
                            newString = entry.text
                            if newString:
                                entry.text = reMatch.sub(self.reReplace, newString)
##### CRUFT: is this code needed ?
##                            newString = entry.compiled_p
##                            if newString:
##                                nSize = len(newString)
##                                newString = reMatch.sub(self.reReplace, struct.pack('B' * nSize, *newString))
##                                nSize = len(newString)
##                                entry.compiled_p = struct.unpack('B' * nSize, newString)
##                                entry.compiledSize = nSize
##                            newString = entry.scriptText
##                            if newString:
##                                entry.scriptText = reMatch.sub(self.reReplace, newString)
##
##                if hasattr(override, 'scriptText'):
##                    newString = override.compiled_p
##                    if newString:
##                        nSize = len(newString)
##                        newString = reMatch.sub(self.reReplace, struct.pack('B' * nSize, *newString))
##                        nSize = len(newString)
##                        override.compiled_p = struct.unpack('B' * nSize, newString)
##                        override.compiledSize = nSize
##                    newString = override.scriptText
##                    if newString:
##                        override.scriptText = reMatch.sub(self.reReplace, newString)
                if override._Type == 'SKIL':
                    newString = override.apprentice
                    if newString:
                        override.apprentice = reMatch.sub(self.reReplace,
                                                          newString)
                    newString = override.journeyman
                    if newString:
                        override.journeyman = reMatch.sub(self.reReplace,
                                                          newString)
                    newString = override.expert
                    if newString:
                        override.expert = reMatch.sub(self.reReplace,
                                                      newString)
                    newString = override.master
                    if newString:
                        override.master = reMatch.sub(self.reReplace,
                                                      newString)
                mod_count = self.mod_count
                mod_count[modFile.GName] = mod_count.get(modFile.GName,0) + 1
                record.UnloadRecord()
                record._RecordID = override._RecordID

#------------------------------------------------------------------------------
class _ANamesTweaker(AMultiTweaker):
    """Tweaks record full names in various ways."""
    scanOrder = 32
    editOrder = 32
    name = _(u'Tweak Names')
    text = _(u"Tweak object names in various ways such as lore friendliness or"
             u" show type/quality.")
    _namesTweaksBody = ((_(u"Armor"),
                         _(u"Rename armor to sort by type."),
                         'ARMO',
                         (_(u'BL Leather Boots'), u'%s '),
                         (_(u'BL. Leather Boots'), u'%s. '),
                         (_(u'BL - Leather Boots'), u'%s - '),
                         (_(u'(BL) Leather Boots'), u'(%s) '),
                         (u'----', u'----'),
                         (_(u'BL02 Leather Boots'), u'%s%02d '),
                         (_(u'BL02. Leather Boots'), u'%s%02d. '),
                         (_(u'BL02 - Leather Boots'), u'%s%02d - '),
                         (_(u'(BL02) Leather Boots'), u'(%s%02d) '),),
                        (_(u"Clothes"),
                         _(u"Rename clothes to sort by type."),
                         'CLOT',
                         (_(u'P Grey Trousers'),  u'%s '),
                         (_(u'P. Grey Trousers'), u'%s. '),
                         (_(u'P - Grey Trousers'),u'%s - '),
                         (_(u'(P) Grey Trousers'),u'(%s) '),),)
    _txtReplacer = ((ur'\b(d|D)(?:warven|warf)\b', ur'\1wemer',
                     _(u"Lore Friendly Text: Dwarven -> Dwemer"),
                     _(u'Replace any occurrences of the words "Dwarf" or'
                       u' "Dwarven" with "Dwemer" to better follow lore.'),
                     u'Dwemer',
                     (u'Lore Friendly Text: Dwarven -> Dwemer', u'Dwemer'),),
                    (ur'\b(d|D)(?:warfs)\b',ur'\1warves',
                     _(u"Proper English Text: Dwarfs -> Dwarves"),
                     _(u'Replace any occurrences of the words "Dwarfs" with '
                       u'"Dwarves" to better follow proper English.'),
                     u'Dwarfs',
                     (u'Proper English Text: Dwarfs -> Dwarves', u'Dwarves'),),
                    (ur'\b(s|S)(?:taffs)\b',ur'\1taves',
                     _(u"Proper English Text: Staffs -> Staves"),
                     _(u'Replace any occurrences of the words "Staffs" with'
                       u' "Staves" to better follow proper English.'),
                     u'Staffs',
                    (u'Proper English Text: Staffs -> Staves', u'Staves'),),)

class NamesTweaker(_ANamesTweaker,MultiTweaker):
    tweaks = sorted(
        [NamesTweak_Body(*x) for x in _ANamesTweaker._namesTweaksBody] + [
            TextReplacer(*x) for x in _ANamesTweaker._txtReplacer] + [
            NamesTweak_Potions(), NamesTweak_Scrolls(), NamesTweak_Spells(),
            NamesTweak_Weapons()], key=lambda a: a.label.lower())
    tweaks.insert(0, NamesTweak_BodyTags())

    #--Patch Phase ------------------------------------------------------------
    def getReadClasses(self):
        """Returns load factory classes needed for reading."""
        if not self.isActive: return tuple()
        classTuples = [tweak.getReadClasses() for tweak in self.enabledTweaks]
        return sum(classTuples,tuple())

    def getWriteClasses(self):
        """Returns load factory classes needed for writing."""
        if not self.isActive: return tuple()
        classTuples = [tweak.getWriteClasses() for tweak in self.enabledTweaks]
        return sum(classTuples,tuple())

    def scanModFile(self,modFile,progress):
        if not self.isActive: return
        for tweak in self.enabledTweaks:
            tweak.scanModFile(modFile,progress,self.patchFile)

class CBash_NamesTweaker(_ANamesTweaker,CBash_MultiTweaker):
    tweaks = sorted(
        [CBash_NamesTweak_Body(*x) for x in _ANamesTweaker._namesTweaksBody] +
        [CBash_TextReplacer(*x) for x in _ANamesTweaker._txtReplacer] + [
            CBash_NamesTweak_Potions(), CBash_NamesTweak_Scrolls(),
            CBash_NamesTweak_Spells(), CBash_NamesTweak_Weapons()],
        key=lambda a: a.label.lower())
    tweaks.insert(0,CBash_NamesTweak_BodyTags())

    #--Config Phase -----------------------------------------------------------
    def initPatchFile(self,patchFile,loadMods):
        self.patchFile = patchFile
        for tweak in self.tweaks[1:]:
            tweak.patchFile = patchFile
        bodyTagPatcher = self.tweaks[0]
        patchFile.bodyTags = \
            bodyTagPatcher.choiceValues[bodyTagPatcher.chosen][0]
        patchFile.indexMGEFs = True

    def initData(self,group_patchers,progress):
        if not self.isActive: return
        for tweak in self.enabledTweaks:
            for type_ in tweak.getTypes():
                group_patchers.setdefault(type_,[]).append(tweak)
            tweak.format = tweak.choiceValues[tweak.chosen][0]
            if isinstance(tweak, CBash_NamesTweak_Body):
                tweak.showStat = u'%02d' in tweak.format
                tweak.codes = getattr(self.patchFile,'bodyTags',u'ARGHTCCPBS')
                tweak.amulet, tweak.ring, tweak.gloves, tweak.head, \
                tweak.tail, tweak.robe, tweak.chest, tweak.pants, \
                tweak.shoes, tweak.shield = [
                    x for x in tweak.codes]
