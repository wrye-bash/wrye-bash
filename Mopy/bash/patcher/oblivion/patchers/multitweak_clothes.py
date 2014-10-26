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

"""This module contains oblivion multitweak item patcher classes that belong
to the Clothes Multitweaker - as well as the ClothesTweaker itself."""
# TODO:DOCS
import bash # FIXME - why ?
from bash.patcher.base import AMultiTweakItem
from bash.patcher.oblivion.patchers.base import MultiTweakItem, \
    CBash_MultiTweakItem
from bash.patcher.oblivion.patchers.base import MultiTweaker, \
    CBash_MultiTweaker

# Patchers: 30 ----------------------------------------------------------------
class AClothesTweak(AMultiTweakItem):
    flags = {
        u'hoods':    0x00000002,
        u'shirts':   0x00000004,
        u'pants':    0x00000008,
        u'gloves':   0x00000010,
        u'amulets':  0x00000100,
        u'rings2':   0x00010000,
        u'amulets2': 0x00020000,
        #--Multi
        u'robes':    0x0000000C,
        u'rings':    0x000000C0,
        }
        # u'robes':   (1<<2) + (1<<3),
        # u'rings':   (1<<6) + (1<<7),

    #--Config Phase -----------------------------------------------------------
    def __init__(self,label,tip,key,*choices):
        super(AClothesTweak,self).__init__(label,tip,key,*choices)
        typeKey = key[:key.find(u'.')]
        self.orTypeFlags = typeKey == u'rings'
        self.typeFlags = self.__class__.flags[typeKey]

    def isMyType(self,record):
        """Returns true to save record for late processing."""
        recTypeFlags = int(record.flags) & 0xFFFF
        myTypeFlags = self.typeFlags
        return ((recTypeFlags == myTypeFlags) or (
            self.orTypeFlags and (recTypeFlags & myTypeFlags == recTypeFlags)))

class ClothesTweak(AClothesTweak,MultiTweakItem):
    def isMyType(self,record):
        """Returns true to save record for late processing."""
        # TODO : needed in CBash ?
        if record.flags.notPlayable: return False #--Ignore non-playable items.
        return super(ClothesTweak,self).isMyType(record)

class CBash_ClothesTweak(AClothesTweak,CBash_MultiTweakItem): pass

#------------------------------------------------------------------------------
class ClothesTweak_MaxWeight(ClothesTweak):
    """Enforce a max weight for specified clothes."""
    #--Patch Phase ------------------------------------------------------------
    def buildPatch(self,patchFile,keep,log):
        """Build patch."""
        tweakCount = 0
        maxWeight = self.choiceValues[self.chosen][0] # TODO:weight
        superWeight = max(10,5*maxWeight) #--Guess is intentionally overweight
        for record in patchFile.CLOT.records:
            weight = record.weight
            if self.isMyType(record) and maxWeight < weight < superWeight:
                record.weight = maxWeight
                keep(record.fid)
                tweakCount += 1
        log(u'* %s: [%4.2f]: %d' % (self.label,maxWeight,tweakCount))

class CBash_ClothesTweak_MaxWeight(CBash_ClothesTweak):
    """Enforce a max weight for specified clothes."""
    name = _(u'Reweigh Clothes')

    #--Config Phase -----------------------------------------------------------
    def __init__(self,label,tip,key,*choices):
        super(CBash_ClothesTweak_MaxWeight, self).__init__(label, tip, key,
                                                           *choices)
        self.matchFlags = {'amulets.maxWeight':('IsAmulet',),
                         'rings.maxWeight':('IsRightRing','IsLeftRing'),
                         'hoods.maxWeight':('IsHair',)
                         }[key]
        self.logMsg = u'* '+_(u'Clothes Reweighed: %d')

    def getTypes(self):
        return ['CLOT']
    #--Patch Phase ------------------------------------------------------------
    def apply(self,modFile,record,bashTags):
        """Edits patch file as desired. """
        if record.IsNonPlayable:
            return
        maxWeight = self.choiceValues[self.chosen][0] # TODO:weight
        superWeight = max(10,5*maxWeight) #--Guess is intentionally overweight
        if (record.weight > maxWeight) and self.isMyType(record) and (
                    record.weight < superWeight):
            for attr in self.matchFlags:
                if getattr(record, attr):
                    break
            else:
                return
            override = record.CopyAsOverride(self.patchFile)
            if override:
                override.weight = maxWeight
                mod_count = self.mod_count
                mod_count[modFile.GName] = mod_count.get(modFile.GName,0) + 1
                record.UnloadRecord()
                record._RecordID = override._RecordID

    def buildPatchLog(self,log):
        """Will write to log."""
        #--Log
        mod_count = self.mod_count
        maxWeight = self.choiceValues[self.chosen][0] # TODO:weight
        log.setHeader(self.logHeader)
        log(self.logMsg % sum(mod_count.values()))
        for srcMod in bash.bosh.modInfos.getOrdered(mod_count.keys()):
            log(u'  * %s: [%4.2f]: %d' % (
                srcMod.s, maxWeight, mod_count[srcMod]))
        self.mod_count = {}

#------------------------------------------------------------------------------
class ClothesTweak_Unblock(ClothesTweak):
    """Unlimited rings, amulets."""
    #--Config Phase -----------------------------------------------------------
    def __init__(self,label,tip,key,*choices):
        super(ClothesTweak_Unblock,self).__init__(label,tip,key,*choices)
        self.unblockFlags = self.__class__.flags[key[key.rfind('.')+1:]]

    #--Patch Phase ------------------------------------------------------------
    def buildPatch(self,patchFile,keep,log):
        """Build patch."""
        tweakCount = 0
        for record in patchFile.CLOT.records:
            if self.isMyType(record) and int(record.flags & self.unblockFlags):
                record.flags &= ~self.unblockFlags
                keep(record.fid)
                tweakCount += 1
        log(u'* %s: %d' % (self.label,tweakCount))

class CBash_ClothesTweak_Unblock(CBash_ClothesTweak):
    """Unlimited rings, amulets."""
    scanOrder = 31
    editOrder = 31

    #--Config Phase -----------------------------------------------------------
    def __init__(self,label,tip,key):
        super(CBash_ClothesTweak_Unblock,self).__init__(label,tip,key)
        self.hideFlags = {'amulets.unblock.amulets':('IsAmulet',),
                         'robes.show.amulets2':('IsHideAmulets',),
                         'rings.unblock.rings':('IsRightRing','IsLeftRing'),
                         'gloves.unblock.rings2':('IsHideRings',),
                         'robes.unblock.pants':('IsLowerBody',)
                         }[key]
        self.logMsg = u'* '+_(u'Clothing Pieces Tweaked: %d')

    def getTypes(self):
        return ['CLOT']
    #--Patch Phase ------------------------------------------------------------
    def apply(self,modFile,record,bashTags):
        """Edits patch file as desired. """
        if record.IsNonPlayable:
            return
        if self.isMyType(record):
            for flag in self.hideFlags:
                if getattr(record, flag):
                    break
            else:
                return
            override = record.CopyAsOverride(self.patchFile)
            if override:
                for attr in self.hideFlags:
                    setattr(override, attr, False)
                mod_count = self.mod_count
                mod_count[modFile.GName] = mod_count.get(modFile.GName,0) + 1
                record.UnloadRecord()
                record._RecordID = override._RecordID

#------------------------------------------------------------------------------
# TODO: eliminate duplicate strings (here and elsewhere in multitweakers)
class ClothesTweaker(MultiTweaker):
    """Patches clothes in miscellaneous ways."""
    scanOrder = 31
    editOrder = 31
    name = _(u'Tweak Clothes')
    text = _(u"Tweak clothing weight and blocking.")
    tweaks = sorted([
        ClothesTweak_Unblock(_(u"Unlimited Amulets"),
            _(u"Wear unlimited number of amulets - but they won't display."),
            u'amulets.unblock.amulets'),
        ClothesTweak_Unblock(_(u"Unlimited Rings"),
            _(u"Wear unlimited number of rings - but they won't display."),
            u'rings.unblock.rings'),
        ClothesTweak_Unblock(_(u"Gloves Show Rings"),
            _(u"Gloves will always show rings. (Conflicts with Unlimited Rings.)"),
            u'gloves.unblock.rings2'),
        ClothesTweak_Unblock(_(u"Robes Show Pants"),
            _(u"Robes will allow pants, greaves, skirts - but they'll clip."),
            u'robes.unblock.pants'),
        ClothesTweak_Unblock(_(u"Robes Show Amulets"),
            _(u"Robes will always show amulets. (Conflicts with Unlimited Amulets.)"),
            u'robes.show.amulets2'),
        ClothesTweak_MaxWeight(_(u"Max Weight Amulets"),
            _(u"Amulet weight will be capped."),
            u'amulets.maxWeight',
            (u'0.0',0),
            (u'0.1',0.1),
            (u'0.2',0.2),
            (u'0.5',0.5),
            (_(u'Custom'),0),
            ),
        ClothesTweak_MaxWeight(_(u"Max Weight Rings"),
            _(u'Ring weight will be capped.'),
            u'rings.maxWeight',
            (u'0.0',0),
            (u'0.1',0.1),
            (u'0.2',0.2),
            (u'0.5',0.5),
            (_(u'Custom'),0),
            ),
        ClothesTweak_MaxWeight(_(u"Max Weight Hoods"),
            _(u'Hood weight will be capped.'),
            u'hoods.maxWeight',
            (u'0.2',0.2),
            (u'0.5',0.5),
            (u'1.0',1.0),
            (_(u'Custom'),0),
            ),
        ],key=lambda a: a.label.lower())

    #--Patch Phase ------------------------------------------------------------
    def getReadClasses(self):
        """Returns load factory classes needed for reading."""
        return ('CLOT',) if self.isActive else ()

    def getWriteClasses(self):
        """Returns load factory classes needed for writing."""
        return ('CLOT',) if self.isActive else ()

    def scanModFile(self,modFile,progress):
        if not self.isActive or 'CLOT' not in modFile.tops: return
        mapper = modFile.getLongMapper()
        patchRecords = self.patchFile.CLOT
        id_records = patchRecords.id_records
        for record in modFile.CLOT.getActiveRecords():
            if mapper(record.fid) in id_records: continue
            for tweak in self.enabledTweaks:
                if tweak.isMyType(record):
                    record = record.getTypeCopy(mapper)
                    patchRecords.setRecord(record)
                    break

    def buildPatch(self,log,progress):
        """Applies individual clothes tweaks."""
        if not self.isActive: return
        keep = self.patchFile.getKeeper()
        log.setHeader(u'= '+self.__class__.name)
        for tweak in self.enabledTweaks:
            tweak.buildPatch(self.patchFile,keep,log)

class CBash_ClothesTweaker(CBash_MultiTweaker):
    """Patches clothes in miscellaneous ways."""
    scanOrder = 31
    editOrder = 31
    name = _(u'Tweak Clothes')
    text = _(u"Tweak clothing weight and blocking.")
    tweaks = sorted([
        CBash_ClothesTweak_Unblock(_(u"Unlimited Amulets"),
            _(u"Wear unlimited number of amulets - but they won't display."),
            u'amulets.unblock.amulets'),
        CBash_ClothesTweak_Unblock(_(u"Unlimited Rings"),
            _(u"Wear unlimited number of rings - but they won't display."),
            u'rings.unblock.rings'),
        CBash_ClothesTweak_Unblock(_(u"Gloves Show Rings"),
            _(u"Gloves will always show rings. (Conflicts with Unlimited Rings.)"),
            u'gloves.unblock.rings2'),
        CBash_ClothesTweak_Unblock(_(u"Robes Show Pants"),
            _(u"Robes will allow pants, greaves, skirts - but they'll clip."),
            u'robes.unblock.pants'),
        CBash_ClothesTweak_Unblock(_(u"Robes Show Amulets"),
            _(u"Robes will always show amulets. (Conflicts with Unlimited Amulets.)"),
            u'robes.show.amulets2'),
        CBash_ClothesTweak_MaxWeight(_(u"Max Weight Amulets"),
            _(u"Amulet weight will be capped."),
            u'amulets.maxWeight',
            (u'0.0',0.0),
            (u'0.1',0.1),
            (u'0.2',0.2),
            (u'0.5',0.5),
            (_(u'Custom'),0.0),
            ),
        CBash_ClothesTweak_MaxWeight(_(u"Max Weight Rings"),
            _(u'Ring weight will be capped.'),
            u'rings.maxWeight',
            (u'0.0',0.0),
            (u'0.1',0.1),
            (u'0.2',0.2),
            (u'0.5',0.5),
            (_(u'Custom'),0.0),
            ),
        CBash_ClothesTweak_MaxWeight(_(u"Max Weight Hoods"),
            _(u'Hood weight will be capped.'),
            u'hoods.maxWeight',
            (u'0.2',0.2),
            (u'0.5',0.5),
            (u'1.0',1.0),
            (_(u'Custom'),0.0),
            ),
        ],key=lambda a: a.label.lower())

    #--Config Phase -----------------------------------------------------------
    def initPatchFile(self,patchFile,loadMods):
        self.patchFile = patchFile
        for tweak in self.tweaks:
            tweak.patchFile = patchFile
