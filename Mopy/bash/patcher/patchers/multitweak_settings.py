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
"""This module contains oblivion multitweak item patcher classes that belong
to the Gmst Multitweaker - as well as the GmstTweaker itself. Gmst stands
for game settings."""
from ... import bush # for game
from ...bolt import SubProgress, deprint
from ...brec import MreRecord, RecordHeader
from ...exception import StateError
from ...patcher.patchers.base import MultiTweakItem, CBash_MultiTweakItem
from ...patcher.patchers.base import MultiTweaker, CBash_MultiTweaker
from ...patcher.base import AMultiTweaker

# Patchers: 30 ----------------------------------------------------------------
class GlobalsTweak(MultiTweakItem):
    """set a global to specified value"""
    #--Patch Phase ------------------------------------------------------------
    def buildPatch(self,patchFile,keep,log):
        """Build patch."""
        value = self.choiceValues[self.chosen][0]
        for record in patchFile.GLOB.records:
            if hasattr(record,'eid'):
                if record.eid.lower() == self.key:
                    if record.value != value:
                        record.value = value
                        keep(record.fid)
                    break
        log(u'* ' + _(u'%(label)s set to') % {
            'label': (u'%s ' % self.label)} + (u': %4.2f' % value))

class CBash_GlobalsTweak(CBash_MultiTweakItem):
    """Sets a global to specified value"""
    scanOrder = 29
    editOrder = 29
    tweak_read_classes = 'GLOB',

    #--Patch Phase ------------------------------------------------------------
    def apply(self,modFile,record,bashTags):
        """Edits patch file as desired. """
        if record.eid == self.key: #eid is case insensitive on comparisons by
            #  default
            value = self.value = self.choiceValues[self.chosen][0]
            if record.value != value:
                self.count = 1
                override = record.CopyAsOverride(self.patchFile)
                if override:
                    override.value = float(value) #Globals are always stored as
                    # floats, regardless of what the CS says
                    record.UnloadRecord()
                    record._RecordID = override._RecordID

    def buildPatchLog(self,log):
        """Will write to log."""
        #--Log
        if self.count: log(u'* ' + _(u'%(label)s set to') % {
            'label': (u'%s ' % self.label)} + (u': %4.2f' % self.value))

#------------------------------------------------------------------------------
class GmstTweak(MultiTweakItem):
    #--Patch Phase ------------------------------------------------------------
    def buildPatch(self,patchFile,keep,log):
        """Build patch."""
        eids = ((self.key,),self.key)[isinstance(self.key,tuple)]
        isOblivion = bush.game.fsName.lower() == u'oblivion'
        for eid,value in zip(eids,self.choiceValues[self.chosen]):
            if isOblivion and value < 0:
                deprint(_(u"GMST values can't be negative - currently %s - "
                          u"skipping setting GMST.") % value)
                return
            eidLower = eid.lower()
            for record in patchFile.GMST.records:
                if record.eid.lower() == eidLower:
                    if record.value != value:
                        record.value = value
                        keep(record.fid)
                    break
            else:
                gmst = MreRecord.type_class['GMST'](
                    RecordHeader('GMST', 0, 0, 0, 0))
                gmst.eid,gmst.value,gmst.longFids = eid,value,True
                fid = gmst.fid = keep(gmst.getGMSTFid())
                patchFile.GMST.setRecord(gmst)
        if len(self.choiceLabels) > 1:
            if self.choiceLabels[self.chosen].startswith(_(u'Custom')):
                if isinstance(self.choiceValues[self.chosen][0],basestring):
                    log(u'* %s: %s %s' % (
                        self.label, self.choiceLabels[self.chosen],
                        self.choiceValues[self.chosen][0]))
                else:
                    log(u'* %s: %s %4.2f' % (
                        self.label, self.choiceLabels[self.chosen],
                        self.choiceValues[self.chosen][0]))
            else:
                log(u'* %s: %s' % (self.label, self.choiceLabels[self.chosen]))
        else:
            log(u'* ' + self.label)

class CBash_GmstTweak(CBash_MultiTweakItem):
    """Sets a gmst to specified value"""
    scanOrder = 29
    editOrder = 29
    tweak_read_classes = 'GMST',

    #--Patch Phase ------------------------------------------------------------
    def apply(self,modFile,record,bashTags):
        """Edits patch file as desired. """
        values = self.values = self.choiceValues[self.chosen]
        recEid = record.eid
        for eid,value in zip(self.key,values):
            if eid == recEid:
                newValue = value
                break
        else:
            return
        if recEid.startswith(u"f") and type(newValue) != float:
            deprint(_(u"converting custom value to float for GMST %s: %s") % (
                recEid, newValue))
            newValue = float(newValue)
        if record.value != newValue:
            self.eid_count[eid] = 1
            if newValue < 0:
                deprint(_(u"GMST values can't be negative - currently %s - "
                          u"skipping setting GMST.") % newValue)
                return
            override = record.CopyAsOverride(self.patchFile)
            if override:
                override.value = newValue
                record.UnloadRecord()
                record._RecordID = override._RecordID

    def finishPatch(self,patchFile,progress):
        """Edits the bashed patch file directly."""
        subProgress = SubProgress(progress)
        values = self.values = self.choiceValues[self.chosen]
        subProgress.setFull(max(len(values),1))
        pstate = 0
        for eid,value in zip(self.key,values):
            subProgress(pstate, _(u"Finishing GMST Tweaks..."))
            if not self.eid_count.get(eid,0):
                self.eid_count[eid] = 1
                record = patchFile.create_GMST(eid)
                if not record:
                    print eid
                    print patchFile.Current.Debug_DumpModFiles()
                    for conflict in patchFile.Current.LookupRecords(eid,False):
                        print conflict.GetParentMod().ModName
                    raise StateError(u"Tweak Settings: Unable to create GMST!")
                if eid.startswith("f") and type(value) != float:
                    deprint(_(u"converting custom value to float for GMST"
                              u" %s: %s") % (eid, value))
                    value = float(value)
                record.value = value
            pstate += 1

    def buildPatchLog(self,log):
        """Will write to log."""
        #--Log
        if len(self.choiceLabels) > 1:
            if self.choiceLabels[self.chosen].startswith(_(u'Custom')):
                if isinstance(self.values[0],basestring):
                    log(u'  * %s: %s %s' % (
                        self.label, self.choiceLabels[self.chosen],
                        self.values[0]))
                else:
                    log(u'  * %s: %s %4.2f' % (
                        self.label, self.choiceLabels[self.chosen],
                        self.values[0]))
            else:
                log(u'  * %s: %s' % (
                    self.label, self.choiceLabels[self.chosen]))
        else:
            log(u'  * ' + self.label)

#------------------------------------------------------------------------------
class _AGmstTweaker(AMultiTweaker):
    """Tweaks miscellaneous gmsts in miscellaneous ways."""
    name = _(u'Tweak Settings')
    text = _(u"Tweak game settings.")
    tweaks = []

class GmstTweaker(MultiTweaker, _AGmstTweaker):
    """Tweaks miscellaneous gmsts in miscellaneous ways."""
    scanOrder = 29
    editOrder = 29
    class_tweaks = [(GlobalsTweak, bush.game.GlobalsTweaks),
                    (GmstTweak, bush.game.GmstTweaks)]

    #--Patch Phase ------------------------------------------------------------
    def getReadClasses(self):
        """Returns load factory classes needed for writing."""
        return ('GMST','GLOB') if self.isActive else ()

    def getWriteClasses(self):
        """Returns load factory classes needed for writing."""
        return ('GMST','GLOB') if self.isActive else ()

    def scanModFile(self,modFile,progress):
        if not self.isActive: return
        mapper = modFile.getLongMapper()
        for blockType in ['GMST','GLOB']:
            if blockType not in modFile.tops: continue
            modBlock = getattr(modFile,blockType)
            patchBlock = getattr(self.patchFile,blockType)
            id_records = patchBlock.id_records
            for record in modBlock.getActiveRecords():
                if mapper(record.fid) not in id_records:
                    record = record.getTypeCopy(mapper)
                    patchBlock.setRecord(record)

    def buildPatch(self,log,progress):
        """Edits patch file as desired. Will write to log."""
        if not self.isActive: return
        keep = self.patchFile.getKeeper()
        log.setHeader(u'= '+self.__class__.name)
        for tweak in self.enabledTweaks:
            tweak.buildPatch(self.patchFile,keep,log)

class CBash_GmstTweaker(CBash_MultiTweaker, _AGmstTweaker):
    """Tweaks miscellaneous gmsts in miscellaneous ways."""
    class_tweaks = [(CBash_GlobalsTweak, bush.game.GlobalsTweaks),
                    (CBash_GmstTweak, bush.game.GmstTweaks)]

    #--Patch Phase ------------------------------------------------------------
    def initPatchFile(self, patchFile):
        self.patchFile = patchFile
        for tweak in self.tweaks:
            tweak.patchFile = patchFile
            if isinstance(tweak,CBash_GlobalsTweak):
                tweak.count = 0
            else:
                tweak.eid_count = {}
