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

"""This module contains oblivion multitweak item patcher classes that belong
to the Names Multitweaker - as well as the NamesTweaker itself."""

from __future__ import division
import re
from collections import Counter
# Internal
from ... import load_order
from ...patcher.base import AMultiTweakItem, AMultiTweaker, DynamicNamedTweak
from ...patcher.patchers.base import MultiTweakItem, CBash_MultiTweakItem
from ...patcher.patchers.base import MultiTweaker, CBash_MultiTweaker

class _AMultiTweakItem_Names(MultiTweakItem):

    def _patchLog(self, log, count):
        # --Log - Notice self.logMsg is not used - so (apart from
        # NamesTweak_BodyTags and NamesTweak_Body where it is not defined in
        # the ANamesTweak_XX common superclass) the
        # CBash implementations which _do_ use it produce different logs. TODO:
        # unify C/P logs by using self.logMsg (mind the classes mentioned)
        log(u'* %s: %d' % (self.tweak_name,sum(count.values())))
        for srcMod in load_order.get_ordered(count.keys()):
            log(u'  * %s: %d' % (srcMod.s,count[srcMod]))

# Patchers: 30 ----------------------------------------------------------------
class _ANamesTweak_BodyTags(AMultiTweakItem):
    """Only exists to change _PFile.bodyTags - see _ANamesTweaker.__init__ for
    the implementation."""
    tweak_name = _(u'Body Part Codes')
    tweak_tip = _(u'Sets body part codes used by Armor/Clothes name tweaks. '
                  u'A: Amulet, R: Ring, etc.')

    def __init__(self):
        super(_ANamesTweak_BodyTags, self).__init__(u'bodyTags', (
            u'ARGHTCCPBS', u'ARGHTCCPBS'), (u'ABGHINOPSL', u'ABGHINOPSL'))

class NamesTweak_BodyTags(_ANamesTweak_BodyTags, MultiTweakItem): pass

class CBash_NamesTweak_BodyTags(_ANamesTweak_BodyTags, CBash_MultiTweakItem):
    def buildPatchLog(self, log): pass

#------------------------------------------------------------------------------
class NamesTweak_Body(DynamicNamedTweak, _AMultiTweakItem_Names):
    """Names tweaker for armor and clothes."""

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
        count = Counter()
        format_ = self.choiceValues[self.chosen][0]
        showStat = u'%02d' in format_
        keep = patchFile.getKeeper()
        codes = patchFile.bodyTags
        amulet,ring,gloves,head,tail,robe,chest,pants,shoes,shield = [
            x for x in codes]
        for record in getattr(patchFile,self.key).records:
            if not record.full: continue
            if record.full[0] in u'+-=.()[]': continue
            rec_flgs = record.flags
            if rec_flgs.head or rec_flgs.hair: type_ = head
            elif rec_flgs.rightRing or rec_flgs.leftRing: type_ = ring
            elif rec_flgs.amulet: type_ = amulet
            elif rec_flgs.upperBody and rec_flgs.lowerBody: type_ = robe
            elif rec_flgs.upperBody: type_ = chest
            elif rec_flgs.lowerBody: type_ = pants
            elif rec_flgs.hand: type_ = gloves
            elif rec_flgs.foot: type_ = shoes
            elif rec_flgs.tail: type_ = tail
            elif rec_flgs.shield: type_ = shield
            else: continue
            if record.recType == 'ARMO':
                type_ += 'LH'[record.flags.heavyArmor]
            if showStat:
                record.full = format_ % (
                    type_, record.strength / 100) + record.full
            else:
                record.full = format_ % type_ + record.full
            keep(record.fid)
            count[record.fid[0]] += 1
        self._patchLog(log, count)

class CBash_NamesTweak_Body(DynamicNamedTweak, CBash_MultiTweakItem):
    """Names tweaker for armor and clothes."""

    def __init__(self, tweak_name, tweak_tip, key, *choices, **kwargs):
        super(CBash_NamesTweak_Body, self).__init__(tweak_name, tweak_tip, key,
                                                    *choices, **kwargs)
        self.logMsg = u'* ' + _(u'{} Renamed: %d').format(self.key)

    def getTypes(self):
        return [self.key]

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
                    self.mod_count[modFile.GName] += 1
                    record.UnloadRecord()
                    record._RecordID = override._RecordID

#------------------------------------------------------------------------------
class _ANamesTweak_Potions(AMultiTweakItem):
    """Names tweaker for potions."""
    reOldLabel = re.compile(u'^(-|X) ',re.U)
    reOldEnd = re.compile(u' -$',re.U)
    tweak_read_classes = 'ALCH',
    tweak_name = _(u'Potions')
    tweak_tip = _(u'Label potions to sort by type and effect.')

    def __init__(self):
        super(_ANamesTweak_Potions, self).__init__(u'ALCH', # key, not sig!
            (_(u'XD Illness'), u'%s '), (_(u'XD. Illness'), u'%s. '),
            (_(u'XD - Illness'), u'%s - '), (_(u'(XD) Illness'), u'(%s) '))
        self.logMsg = u'* ' + _(u'{} Renamed: %d').format(self.key)

class NamesTweak_Potions(_ANamesTweak_Potions, _AMultiTweakItem_Names):

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
        count = Counter()
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
            count[record.fid[0]] += 1
        self._patchLog(log, count)

class CBash_NamesTweak_Potions(_ANamesTweak_Potions, CBash_MultiTweakItem):

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
                    self.mod_count[modFile.GName] += 1
                    record.UnloadRecord()
                    record._RecordID = override._RecordID

#------------------------------------------------------------------------------
reSpell = re.compile(u'^(\([ACDIMR]\d\)|\w{3,6}:) ',re.U) # compile once

class _ANamesTweak_Scrolls(AMultiTweakItem):
    reOldLabel = reSpell
    tweak_name = _(u'Notes and Scrolls')
    tweak_tip = _(u'Mark notes and scrolls to sort separately from books')

    def __init__(self):
        super(_ANamesTweak_Scrolls, self).__init__(u'scrolls',
            (_(u'~Fire Ball'), u'~'), (_(u'~D Fire Ball'), u'~%s '),
            (_(u'~D. Fire Ball'), u'~%s. '), (_(u'~D - Fire Ball'), u'~%s - '),
            (_(u'~(D) Fire Ball'), u'~(%s) '), (u'----', u'----'),
            (_(u'.Fire Ball'), u'.'), (_(u'.D Fire Ball'), u'.%s '),
            (_(u'.D. Fire Ball'), u'.%s. '), (_(u'.D - Fire Ball'), u'.%s - '),
            (_(u'.(D) Fire Ball'), u'.(%s) '))
        self.logMsg = u'* ' + _(u'Items Renamed: %d')

    def save_tweak_config(self, configs):
        """Save config to configs dictionary."""
        super(_ANamesTweak_Scrolls, self).save_tweak_config(configs)
        rawFormat = self.choiceValues[self.chosen][0]
        self.orderFormat = (u'~.',u'.~')[rawFormat[0] == u'~']
        self.magicFormat = rawFormat[1:]

class NamesTweak_Scrolls(_ANamesTweak_Scrolls, _AMultiTweakItem_Names):
    tweak_read_classes = 'BOOK','ENCH',

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
        count = Counter()
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
            count[record.fid[0]] += 1
        self._patchLog(log, count)

class CBash_NamesTweak_Scrolls(_ANamesTweak_Scrolls, CBash_MultiTweakItem):
    """Names tweaker for scrolls."""
    tweak_read_classes = 'BOOK',

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
                    self.mod_count[modFile.GName] += 1
                    record.UnloadRecord()
                    record._RecordID = override._RecordID

#------------------------------------------------------------------------------
class _ANamesTweak_Spells(AMultiTweakItem):
    """Names tweaker for spells."""
    tweak_read_classes = 'SPEL',
    tweak_name = _(u'Spells')
    tweak_tip = _(u'Label spells to sort by school and level.')

    reOldLabel = reSpell
    def __init__(self):
        super(_ANamesTweak_Spells, self).__init__(
            u'SPEL', # key, not sig!
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
        self.logMsg = u'* '+_(u'Spells Renamed: %d')

class NamesTweak_Spells(_ANamesTweak_Spells, _AMultiTweakItem_Names):

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
        count = Counter()
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
                count[record.fid[0]] += 1
        self._patchLog(log, count)

class CBash_NamesTweak_Spells(_ANamesTweak_Spells, CBash_MultiTweakItem):

    def save_tweak_config(self, configs):
        """Save config to configs dictionary."""
        super(CBash_NamesTweak_Spells, self).save_tweak_config(configs)
        self.format = self.choiceValues[self.chosen][0]
        self.removeTags = u'%s' not in self.format
        self.showLevel = u'%d' in self.format

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
                    self.mod_count[modFile.GName] += 1
                    record.UnloadRecord()
                    record._RecordID = override._RecordID

#------------------------------------------------------------------------------
class _ANamesTweak_Weapons(AMultiTweakItem):
    """Names tweaker for weapons and ammo."""
    tweak_read_classes = 'AMMO','WEAP',
    tweak_name = _(u'Weapons')
    tweak_tip = _(u'Label ammo and weapons to sort by type and damage.')

    def __init__(self):
        super(_ANamesTweak_Weapons, self).__init__(
            u'WEAP', # key, not sig!
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
        self.logMsg = u'* '+_(u'Items Renamed: %d')

class NamesTweak_Weapons(_ANamesTweak_Weapons, _AMultiTweakItem_Names):

    #--Patch Phase ------------------------------------------------------------
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
        count = Counter()
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
            count[record.fid[0]] += 1
        for record in patchFile.WEAP.records:
            if not record.full: continue
            if showStat:
                record.full = format_ % (
                    u'CDEFGB'[record.weaponType], record.damage) + record.full
            else:
                record.full = format_ % u'CDEFGB'[
                    record.weaponType] + record.full
            keep(record.fid)
            count[record.fid[0]] += 1
        self._patchLog(log, count)

class CBash_NamesTweak_Weapons(_ANamesTweak_Weapons, CBash_MultiTweakItem):

    def save_tweak_config(self, configs):
        """Save config to configs dictionary."""
        super(CBash_NamesTweak_Weapons, self).save_tweak_config(configs)
        self.format = self.choiceValues[self.chosen][0]
        self.showStat = u'%02d' in self.format

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
                    self.mod_count[modFile.GName] += 1
                    record.UnloadRecord()
                    record._RecordID = override._RecordID

#------------------------------------------------------------------------------
class _ATextReplacer(DynamicNamedTweak):
    """Base class for replacing any text via regular expressions."""
    tweak_read_classes = (
        b'ALCH', b'AMMO', b'APPA', b'ARMO', b'BOOK', b'BSGN', b'CLAS', b'CLOT',
        b'CONT', b'CREA', b'DOOR', b'ENCH', b'EYES', b'FACT', b'FLOR', b'FURN',
        b'GMST', b'HAIR', b'INGR', b'KEYM', b'LIGH', b'LSCR', b'MGEF', b'MISC',
        b'NPC_', b'QUST', b'RACE', b'SCPT', b'SGST', b'SKIL', b'SLGM', b'SPEL',
        b'WEAP'
    )

    def __init__(self, reMatch, reReplace, label, tweak_tip, key, choices):
        super(_ATextReplacer, self).__init__(label, tweak_tip, key, choices)
        self.reMatch = reMatch
        self.reReplace = reReplace
        self.logMsg = u'* '+_(u'Items Renamed: %d')

class TextReplacer(_ATextReplacer, _AMultiTweakItem_Names):

    def scanModFile(self,modFile,progress,patchFile):
        mapper = modFile.getLongMapper()
        for blockType in self.tweak_read_classes:
            if blockType not in modFile.tops: continue
            modBlock = getattr(modFile,blockType)
            patchBlock = getattr(patchFile,blockType)
            id_records = patchBlock.id_records
            for record in modBlock.getActiveRecords():
                if mapper(record.fid) not in id_records:
                    record = record.getTypeCopy(mapper)
                    patchBlock.setRecord(record)

    def buildPatch(self,log,progress,patchFile):
        count = Counter()
        keep = patchFile.getKeeper()
        reMatch = re.compile(self.reMatch)
        reReplace = self.reReplace
        for type_ in self.tweak_read_classes:
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
                    count[record.fid[0]] += 1
        self._patchLog(log, count)

class CBash_TextReplacer(_ATextReplacer, CBash_MultiTweakItem):
    tweak_read_classes = (b'CELLS',) + _ATextReplacer.tweak_read_classes

    def save_tweak_config(self, configs):
        """Save config to configs dictionary."""
        super(CBash_TextReplacer, self).save_tweak_config(configs)
        self.format = self.choiceValues[self.chosen][0]
        self.showStat = u'%02d' in self.format

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
                self.mod_count[modFile.GName] += 1
                record.UnloadRecord()
                record._RecordID = override._RecordID

#------------------------------------------------------------------------------
class _ANamesTweaker(AMultiTweaker):
    """Tweaks record full names in various ways."""
    scanOrder = 32
    editOrder = 32
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
    _txtReplacer = ((u'' r'\b(d|D)(?:warven|warf)\b', u'' r'\1wemer',
                     _(u'Lore Friendly Text: Dwarven -> Dwemer'),
                     _(u'Replace any occurrences of the word "dwarf" or '
                       u'"dwarven" with "dwemer" to better follow lore.'),
                     u'Dwemer',
                     (u'Lore Friendly Text: Dwarven -> Dwemer', u'Dwemer'),),
                    (u'' r'\b(d|D)(?:warfs)\b', u'' r'\1warves',
                     _(u'Proper English Text: Dwarfs -> Dwarves'),
                     _(u'Replace any occurrences of the word "dwarfs" with '
                       u'"dwarves" to better follow proper English.'),
                     u'Dwarfs',
                     (u'Proper English Text: Dwarfs -> Dwarves', u'Dwarves'),),
                    (u'' r'\b(s|S)(?:taffs)\b', u'' r'\1taves',
                     _(u'Proper English Text: Staffs -> Staves'),
                     _(u'Replace any occurrences of the word "staffs" with '
                       u'"staves" to better follow proper English.'),
                     u'Staffs',
                    (u'Proper English Text: Staffs -> Staves', u'Staves'),),)

    def __init__(self, p_name, p_file, enabled_tweaks):
        super(_ANamesTweaker, self).__init__(p_name, p_file, enabled_tweaks)
        body_tags_tweak = enabled_tweaks[0]
        if isinstance(body_tags_tweak, _ANamesTweak_BodyTags):
            p_file.bodyTags = \
                body_tags_tweak.choiceValues[body_tags_tweak.chosen][0]

class NamesTweaker(_ANamesTweaker,MultiTweaker):

    @classmethod
    def tweak_instances(cls):
        instances = sorted(
            [NamesTweak_Body(*x) for x in cls._namesTweaksBody] + [
                TextReplacer(*x) for x in cls._txtReplacer] + [
                NamesTweak_Potions(), NamesTweak_Scrolls(),
                NamesTweak_Spells(), NamesTweak_Weapons()],
            key=lambda a: a.tweak_name.lower())
        instances.insert(0, NamesTweak_BodyTags())
        return instances

class CBash_NamesTweaker(_ANamesTweaker,CBash_MultiTweaker):

    @classmethod
    def tweak_instances(cls):
        instances = sorted(
            [CBash_NamesTweak_Body(*x) for x in cls._namesTweaksBody] + [
                CBash_TextReplacer(*x) for x in cls._txtReplacer] + [
                CBash_NamesTweak_Potions(), CBash_NamesTweak_Scrolls(),
                CBash_NamesTweak_Spells(), CBash_NamesTweak_Weapons()],
            key=lambda a: a.tweak_name.lower())
        instances.insert(0, CBash_NamesTweak_BodyTags())
        return instances

    def __init__(self, p_name, p_file, enabled_tweaks):
        super(CBash_NamesTweaker, self).__init__(p_name, p_file,
                                                 enabled_tweaks)
        # Potions, scrolls and spells names tweaks need MGEFs to be indexed -
        # PBash does this JIT, CBash needs this to be specified when
        # constructing patchers
        p_file.indexMGEFs = True

    def initData(self, progress):
        if not self.isActive: return
        for tweak in self.enabled_tweaks:
            for top_group_sig in tweak.getTypes():
                self.patchFile.group_patchers[top_group_sig].append(tweak)
            tweak.format = tweak.choiceValues[tweak.chosen][0]
            if isinstance(tweak, CBash_NamesTweak_Body):
                tweak.showStat = u'%02d' in tweak.format
                tweak.codes = self.patchFile.bodyTags
                tweak.amulet, tweak.ring, tweak.gloves, tweak.head, \
                tweak.tail, tweak.robe, tweak.chest, tweak.pants, \
                tweak.shoes, tweak.shield = [
                    x for x in tweak.codes]
