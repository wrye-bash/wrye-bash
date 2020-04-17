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
to the Actors Multitweaker - as well as the TweakActors itself."""

import random
import re
from collections import Counter
# Internal
from ... import bass, bush
from ...bolt import GPath
from ...cint import FormID
from ...exception import AbstractError
from ...patcher.base import AMultiTweakItem
from .base import MultiTweakItem, CBash_MultiTweakItem, MultiTweaker, \
    CBash_MultiTweaker

def _is_templated(record, flag_name):
    """Checks if the specified record has a template record and the
    appropriate template flag set."""
    return (getattr(record, 'template', None) is not None
            and getattr(record.templateFlags, flag_name))

# Patchers: 30 ----------------------------------------------------------------
class BasalNPCTweaker(MultiTweakItem):
    """Base for all NPC tweakers"""
    tweak_read_classes = 'NPC_',

    def scanModFile(self,modFile,progress,patchFile):
        mapper = modFile.getLongMapper()
        patchRecords = patchFile.NPC_
        for record in modFile.NPC_.getActiveRecords():
            record = record.getTypeCopy(mapper)
            patchRecords.setRecord(record)

    def buildPatch(self,log,progress,patchFile): raise AbstractError

class BasalCreatureTweaker(MultiTweakItem):
    """Base for all Creature tweakers"""
    tweak_read_classes = 'CREA',

    def scanModFile(self,modFile,progress,patchFile):
        mapper = modFile.getLongMapper()
        patchRecords = patchFile.CREA
        for record in modFile.CREA.getActiveRecords():
            record = record.getTypeCopy(mapper)
            patchRecords.setRecord(record)

    def buildPatch(self,log,progress,patchFile): raise AbstractError

class _NpcCTweak(CBash_MultiTweakItem):
    tweak_read_classes = 'NPC_',
    playerFid = FormID(GPath(u'Oblivion.esm'), 0x000007) # used in 4/6 derived

class _CreaCTweak(CBash_MultiTweakItem):
    tweak_read_classes = 'CREA',

#------------------------------------------------------------------------------
class AMAONPCSkeletonPatcher(AMultiTweakItem):
    """Changes all NPCs to use the right Mayu's Animation Overhaul Skeleton
    for use with MAO."""
    tweak_name = _(u"Mayu's Animation Overhaul Skeleton Tweaker")
    tweak_tip = _(u'Changes all (modded and vanilla) NPCs to use the MAO '
                  u'skeletons.  Not compatible with VORB.  Note: ONLY use if '
                  u'you have MAO installed.')

    def __init__(self):
        super(AMAONPCSkeletonPatcher, self).__init__(u'MAO Skeleton',
            (_(u'All NPCs'), 0), (_(u'Only Female NPCs'), 1),
            (_(u'Only Male NPCs'), 2))
        self.logHeader = u'=== '+_(u'MAO Skeleton Setter')
        self.logMsg = u'* '+_(u'Skeletons Tweaked') + u': %d'

class MAONPCSkeletonPatcher(AMAONPCSkeletonPatcher,BasalNPCTweaker):

    def buildPatch(self,log,progress,patchFile):
        """Edits patch file as desired. Will write to log."""
        count = Counter()
        keep = patchFile.getKeeper()
        for record in patchFile.NPC_.records:
            if self.choiceValues[self.chosen][
                0] == 1 and not record.flags.female:
                continue
            elif self.choiceValues[self.chosen][
                0] == 2 and record.flags.female:
                continue
            if record.fid == (GPath(u'Oblivion.esm'), 0x000007): continue  #
            # skip player record
            try:
                oldModPath = record.model.modPath
            except AttributeError:  # for freaking weird esps with NPC's
                # with no skeleton assigned to them(!)
                continue
            newModPath = u"Mayu's Projects[M]\\Animation " \
                         u"Overhaul\\Vanilla\\SkeletonBeast.nif"
            try:
                if oldModPath.lower() == \
                        u'characters\\_male\\skeletonsesheogorath.nif':
                    newModPath = u"Mayu's Projects[M]\\Animation " \
                                 u"Overhaul\\Vanilla\\SkeletonSESheogorath.nif"
            except AttributeError:  # in case modPath was None. Try/Except
                # has no overhead if exception isn't thrown.
                pass
            if newModPath != oldModPath:
                record.model.modPath = newModPath
                keep(record.fid)
                count[record.fid[0]] += 1
        self._patchLog(log,count)

class CBash_MAONPCSkeletonPatcher(AMAONPCSkeletonPatcher, _NpcCTweak):

    def apply(self, modFile, record, bashTags,
              __player_fid=_NpcCTweak.playerFid):
        """Edits patch file as desired. """
        if record.fid != __player_fid: #skip player record
            choice = self.choiceValues[self.chosen][0]
            if choice == 1 and record.IsMale: return
            elif choice == 2 and record.IsFemale: return
            oldModPath = record.modPath
            newModPath = u"Mayu's Projects[M]\\Animation " \
                         u"Overhaul\\Vanilla\\SkeletonBeast.nif"
            try:
                if oldModPath == \
                        u'characters\\_male\\skeletonsesheogorath.nif':  #
                    # modPaths do case insensitive comparisons by default
                    newModPath = u"Mayu's Projects[M]\\Animation " \
                                 u"Overhaul\\Vanilla\\SkeletonSESheogorath.nif"
            except AttributeError:  # in case modPath was None. Try/Except
                # has no overhead if exception isn't thrown.
                pass
            if newModPath != oldModPath:
                override = record.CopyAsOverride(self.patchFile)
                if override:
                    override.modPath = newModPath
                    self.mod_count[modFile.GName] += 1
                    record.UnloadRecord()
                    record._RecordID = override._RecordID

#------------------------------------------------------------------------------
class AVORB_NPCSkeletonPatcher(AMultiTweakItem):
    """Changes all NPCs to use the diverse skeleton for different look."""
    tweak_name = _(u"VadersApp's Oblivion Real Bodies Skeleton Tweaker")
    tweak_tip = _(u"Changes all (modded and vanilla) NPCs to use diverse "
                  u"skeletons for different look.  Not compatible with MAO, "
                  u"Requires VadersApp's Oblivion Real Bodies.")

    def __init__(self):
        super(AVORB_NPCSkeletonPatcher, self).__init__(u'VORB',
            (_(u'All NPCs'), 0), (_(u'Only Female NPCs'), 1),
            (_(u'Only Male NPCs'), 2))
        self.logHeader = u'=== '+_(u"VadersApp's Oblivion Real Bodies")
        self.logMsg = u'* '+_(u'Skeletons Tweaked') + u': %d'

    @staticmethod
    def _initSkeletonCollections():
        """ construct skeleton mesh collections
            skeletonList gets files that match the pattern "skel_*.nif",
            but not "skel_special_*.nif"
            skeletonSetSpecial gets files that match "skel_special_*.nif" """
        # Since bass.dirs hasn't been populated when __init__ executes,
        # we do this here
        skeletonDir = bass.dirs['mods'].join(u'Meshes', u'Characters',
                                                  u'_male')
        list_skel_dir = skeletonDir.list() # empty if dir does not exist
        skel_nifs = [x for x in list_skel_dir if
                     x.cs.startswith(u'skel_') and x.cext == u'.nif']
        skeletonList = [x for x in skel_nifs if
                        not x.cs.startswith(u'skel_special_')]
        set_skeletonList = set(skeletonList)
        skeletonSetSpecial = set(
            x.s for x in skel_nifs if x not in set_skeletonList)
        return skeletonList, skeletonSetSpecial

class VORB_NPCSkeletonPatcher(AVORB_NPCSkeletonPatcher,BasalNPCTweaker):

    def buildPatch(self,log,progress,patchFile):
        """Edits patch file as desired.  Will write to log."""
        count = Counter()
        keep = patchFile.getKeeper()
        #--Some setup
        modSkeletonDir = GPath(u'Characters').join(u'_male')
        skeletonList, skeletonSetSpecial = \
            AVORB_NPCSkeletonPatcher._initSkeletonCollections()
        if skeletonList:
            femaleOnly = self.choiceValues[self.chosen][0] == 1
            maleOnly = self.choiceValues[self.chosen][0] == 2
            playerFid = (GPath(u'Oblivion.esm'),0x000007)
            for record in patchFile.NPC_.records:
                # skip records (male only, female only, player)
                if femaleOnly and not record.flags.female: continue
                elif maleOnly and record.flags.female: continue
                if record.fid == playerFid: continue
                try:
                    oldModPath = record.model.modPath
                except AttributeError:  # for freaking weird esps with
                    # NPC's with no skeleton assigned to them(!)
                    continue
                specialSkelMesh = u"skel_special_%X.nif" % record.fid[1]
                if specialSkelMesh in skeletonSetSpecial:
                    newModPath = modSkeletonDir.join(specialSkelMesh)
                else:
                    random.seed(record.fid)
                    randomNumber = random.randint(1, len(skeletonList))-1
                    newModPath = modSkeletonDir.join(
                        skeletonList[randomNumber])
                if newModPath != oldModPath:
                    record.model.modPath = newModPath.s
                    keep(record.fid)
                    count[record.fid[0]] += 1
        self._patchLog(log, count)

class CBash_VORB_NPCSkeletonPatcher(AVORB_NPCSkeletonPatcher, _NpcCTweak):

    def __init__(self): # TODO(ut) dispose of this
        super(CBash_VORB_NPCSkeletonPatcher, self).__init__()
        self.modSkeletonDir = GPath(u'Characters').join(u'_male')
        self.skeletonList = None
        self.skeletonSetSpecial = None

    #--Patch Phase ------------------------------------------------------------
    def apply(self,modFile,record,bashTags,
              __player_fid=_NpcCTweak.playerFid):
        """Edits patch file as desired. """
        recordId = record.fid
        if recordId != __player_fid: #skip player record
            choice = self.choiceValues[self.chosen][0]
            if choice == 1 and record.IsMale: return
            elif choice == 2 and record.IsFemale: return
            if self.skeletonList is None:
                self.skeletonList, self.skeletonSetSpecial = \
                    AVORB_NPCSkeletonPatcher._initSkeletonCollections()
            if len(self.skeletonList) == 0: return
            try:
                oldModPath = record.modPath.lower()
            except AttributeError:  # for freaking weird esps with NPC's with
                # no skeleton assigned to them(!)
                pass
            specialSkelMesh = u"skel_special_%X.nif" % recordId[1]
            if specialSkelMesh in self.skeletonSetSpecial:
                newModPath = self.modSkeletonDir.join(specialSkelMesh)
            else:
                random.seed(recordId)
                randomNumber = random.randint(1, len(self.skeletonList)) - 1
                newModPath = self.modSkeletonDir.join(
                    self.skeletonList[randomNumber])
            if newModPath.cs != oldModPath:
                override = record.CopyAsOverride(self.patchFile)
                if override:
                    override.modPath = newModPath.s
                    self.mod_count[modFile.GName] += 1
                    record.UnloadRecord()
                    record._RecordID = override._RecordID

#------------------------------------------------------------------------------
class AVanillaNPCSkeletonPatcher(AMultiTweakItem):
    """Changes all NPCs to use the vanilla beast race skeleton."""
    tweak_name = _(u'Vanilla Beast Skeleton Tweaker')
    tweak_tip = _(u'Avoids visual glitches if an NPC is a beast race but has '
                  u'the regular skeleton.nif selected, but can cause '
                  u'performance issues.')

    def __init__(self):
        super(AVanillaNPCSkeletonPatcher, self).__init__(u'Vanilla Skeleton',
            (u'1.0', u'1.0'))
        self.logHeader = u'=== '+_(u'Vanilla Beast Skeleton')
        self.logMsg = u'* '+_(u'Skeletons Tweaked') + u': %d'

class VanillaNPCSkeletonPatcher(AVanillaNPCSkeletonPatcher,BasalNPCTweaker):

    def scanModFile(self,modFile,progress,patchFile):
        mapper = modFile.getLongMapper()
        patchRecords = patchFile.NPC_
        for record in modFile.NPC_.getActiveRecords():
            record = record.getTypeCopy(mapper)
            if not record.model: continue #for freaking weird esps with NPC's
            # with no skeleton assigned to them(!)
            model = record.model.modPath
            if model.lower() == u'characters\\_male\\skeleton.nif':
                patchRecords.setRecord(record)

    def buildPatch(self,log,progress,patchFile):
        """Edits patch file as desired. Will write to log."""
        count = Counter()
        keep = patchFile.getKeeper()
        newModPath = u"Characters\\_Male\\SkeletonBeast.nif"
        for record in patchFile.NPC_.records:
            try:
                oldModPath = record.model.modPath
            except AttributeError: #for freaking weird esps with NPC's with no
                # skeleton assigned to them(!)
                continue
            try:
                if oldModPath.lower() != u'characters\\_male\\skeleton.nif':
                    continue
            except AttributeError: #in case oldModPath was None. Try/Except has
                # no overhead if exception isn't thrown.
                pass
            if newModPath != oldModPath:
                record.model.modPath = newModPath
                keep(record.fid)
                count[record.fid[0]] += 1
        self._patchLog(log,count)

class CBash_VanillaNPCSkeletonPatcher(AVanillaNPCSkeletonPatcher, _NpcCTweak):
    scanOrder = 31 #Run before MAO
    editOrder = 31

    def apply(self,modFile,record,bashTags):
        """Edits patch file as desired. """
        oldModPath = record.modPath
        newModPath = u"Characters\\_Male\\SkeletonBeast.nif"
        try:
            if oldModPath != u'characters\\_male\\skeleton.nif': #modPaths do
                # case insensitive comparisons by default
                return
        except AttributeError: #in case modPath was None. Try/Except has no
            # overhead if exception isn't thrown.
            pass
        if newModPath != oldModPath:
            override = record.CopyAsOverride(self.patchFile)
            if override:
                override.modPath = newModPath
                self.mod_count[modFile.GName] += 1
                record.UnloadRecord()
                record._RecordID = override._RecordID

#------------------------------------------------------------------------------
class ARedguardNPCPatcher(AMultiTweakItem):
    """Changes all Redguard NPCs texture symmetry for Better Redguard
    Compatibility."""
    tweak_name = _(u'Redguard FGTS Patcher')
    tweak_tip = _(u'Nulls FGTS of all Redguard NPCs - for compatibility with '
                  u'Better Redguards.')

    def __init__(self):
        super(ARedguardNPCPatcher, self).__init__(u'RedguardFGTSPatcher',
            (u'1.0', u'1.0'))
        self.logHeader = u'=== '+_(u'Redguard FGTS Patcher')
        self.logMsg = u'* '+_(u'Redguard NPCs Tweaked') + u': %d'

class RedguardNPCPatcher(ARedguardNPCPatcher,BasalNPCTweaker):

    def buildPatch(self,log,progress,patchFile):
        """Edits patch file as desired. Will write to log."""
        count = Counter()
        keep = patchFile.getKeeper()
        for record in patchFile.NPC_.records:
            if not record.race: continue
            if record.race[1] == 0x00d43:
                record.fgts_p = '\x00'*200
                keep(record.fid)
                count[record.fid[0]] += 1
        self._patchLog(log,count)

class CBash_RedguardNPCPatcher(ARedguardNPCPatcher, _NpcCTweak):
    redguardId = FormID(GPath(u'Oblivion.esm'),0x00000D43)

    def apply(self,modFile,record,bashTags):
        """Edits patch file as desired. """
        if record.race == self.__class__.redguardId: #Only affect npc's with
            # the Redguard race
            oldFGTS_p = record.fgts_p
            newFGTS_p = [0x00] * 200
            if newFGTS_p != oldFGTS_p:
                override = record.CopyAsOverride(self.patchFile)
                if override:
                    override.fgts_p = newFGTS_p
                    self.mod_count[modFile.GName] += 1
                    record.UnloadRecord()
                    record._RecordID = override._RecordID

#------------------------------------------------------------------------------
class ANoBloodCreaturesPatcher(AMultiTweakItem):
    """Set all creatures to have no blood records."""
    tweak_name = _(u'No Bloody Creatures')
    tweak_tip = _(u'Set all creatures to have no blood records, will have '
                  u'pretty much no effect when used with MMM since the MMM '
                  u'blood uses a different system.')

    def __init__(self):
        super(ANoBloodCreaturesPatcher, self).__init__(u'No bloody creatures',
            (u'1.0', u'1.0'))
        self.logMsg = u'* '+_(u'Creatures Tweaked') + u': %d'

class NoBloodCreaturesPatcher(ANoBloodCreaturesPatcher,BasalCreatureTweaker):

    def buildPatch(self,log,progress,patchFile):
        """Edits patch file as desired. Will write to log."""
        count = Counter()
        keep = patchFile.getKeeper()
        for record in patchFile.CREA.records:
            if record.bloodDecalPath or record.bloodSprayPath:
                record.bloodDecalPath = None
                record.bloodSprayPath = None
                record.flags.noBloodSpray = True
                record.flags.noBloodDecal = True
                keep(record.fid)
                count[record.fid[0]] += 1
        #--Log
        self._patchLog(log, count)

class CBash_NoBloodCreaturesPatcher(ANoBloodCreaturesPatcher, _CreaCTweak):

    def apply(self,modFile,record,bashTags):
        """Edits patch file as desired. """
        if record.bloodDecalPath or record.bloodSprayPath:
            override = record.CopyAsOverride(self.patchFile)
            if override:
                override.bloodDecalPath = None
                override.bloodSprayPath = None
                override.IsNoBloodSpray = True
                override.IsNoBloodDecal = True
                self.mod_count[modFile.GName] += 1
                record.UnloadRecord()
                record._RecordID = override._RecordID

#------------------------------------------------------------------------------
class AAsIntendedImpsPatcher(AMultiTweakItem):
    """Set all imps to have the Bethesda imp spells that were never assigned
    (discovered by the UOP team, made into a mod by Tejon)."""
    reImpModPath = re.compile(u'' r'(imp(?!erial)|gargoyle)\\.', re.I | re.U)
    reImp  = re.compile(u'(imp(?!erial)|gargoyle)',re.I|re.U)
    tweak_name = _(u'As Intended: Imps')
    tweak_tip = _(u'Set imps to have the unassigned Bethesda Imp Spells as '
                  u'discovered by the UOP team and made into a mod by Tejon.')

    def __init__(self):
        super(AAsIntendedImpsPatcher, self).__init__(u'vicious imps!',
            (_(u'All imps'), u'all'), (_(u'Only fullsize imps'), u'big'),
            (_(u'Only implings'), u'small'))
        self.logMsg = u'* '+_(u'Imps Tweaked') + u': %d'

class AsIntendedImpsPatcher(AAsIntendedImpsPatcher,BasalCreatureTweaker):

    def buildPatch(self,log,progress,patchFile):
        """Edits patch file as desired. Will write to log."""
        count = Counter()
        keep = patchFile.getKeeper()
        spell = (GPath(u'Oblivion.esm'), 0x02B53F)
        reImp  = self.reImp
        reImpModPath = self.reImpModPath
        for record in patchFile.CREA.records:
            try:
                oldModPath = record.model.modPath
            except AttributeError:
                continue
            if not reImpModPath.search(oldModPath or u''): continue

            for bodyPart in record.bodyParts:
                if reImp.search(bodyPart):
                    break
            else:
                continue
            if record.baseScale < 0.4:
                if u'big' in self.choiceValues[self.chosen]:
                    continue
            elif u'small' in self.choiceValues[self.chosen]:
                continue
            if spell not in record.spells:
                record.spells.append(spell)
                keep(record.fid)
                count[record.fid[0]] += 1
        self._patchLog(log,count)

class CBash_AsIntendedImpsPatcher(AAsIntendedImpsPatcher, _CreaCTweak):
    spell = FormID(GPath(u'Oblivion.esm'), 0x02B53F)

    def apply(self,modFile,record,bashTags):
        """Edits patch file as desired. """
        if not self.reImpModPath.search(record.modPath or u''): return
        reImp  = self.reImp
        for bodyPart in record.bodyParts:
            if reImp.search(bodyPart):
                break
        else:
            return
        if record.baseScale < 0.4:
            if u'big' in self.choiceValues[self.chosen]:
                return
        elif u'small' in self.choiceValues[self.chosen]:
            return
        spells = record.spells
        newSpell = self.spell
        if newSpell not in spells:
            override = record.CopyAsOverride(self.patchFile)
            if override:
                spells.append(newSpell)
                override.spells = spells
                self.mod_count[modFile.GName] += 1
                record.UnloadRecord()
                record._RecordID = override._RecordID

#------------------------------------------------------------------------------
class AAsIntendedBoarsPatcher(AMultiTweakItem):
    """Set all boars to have the Bethesda boar spells that were never
    assigned (discovered by the UOP team, made into a mod by Tejon)."""
    reBoarModPath = re.compile(u'' r'(boar)\\.', re.I | re.U)
    reBoar  = re.compile(u'(boar)', re.I|re.U)
    tweak_name = _(u'As Intended: Boars')
    tweak_tip = _(u'Set boars to have the unassigned Bethesda Boar Spells as '
                  u'discovered by the UOP team and made into a mod by Tejon.')

    def __init__(self):
        super(AAsIntendedBoarsPatcher, self).__init__(u'vicious boars!',
            (u'1.0', u'1.0'))
        self.logMsg = u'* '+_(u'Boars Tweaked') + u': %d'

class AsIntendedBoarsPatcher(AAsIntendedBoarsPatcher,BasalCreatureTweaker):

    def buildPatch(self,log,progress,patchFile):
        """Edits patch file as desired. Will write to log."""
        count = Counter()
        spell = (GPath(u'Oblivion.esm'), 0x02B54E)
        keep = patchFile.getKeeper()
        reBoar  = self.reBoar
        reBoarModPath = self.reBoarModPath
        for record in patchFile.CREA.records:
            try:
                oldModPath = record.model.modPath
            except AttributeError:
                continue
            if not reBoarModPath.search(oldModPath or u''): continue

            for bodyPart in record.bodyParts:
                if reBoar.search(bodyPart):
                    break
            else:
                continue
            if spell not in record.spells:
                record.spells.append(spell)
                keep(record.fid)
                count[record.fid[0]] += 1
        self._patchLog(log,count)

class CBash_AsIntendedBoarsPatcher(AAsIntendedBoarsPatcher, _CreaCTweak):
    spell = FormID(GPath(u'Oblivion.esm'), 0x02B54E)

    def apply(self,modFile,record,bashTags):
        """Edits patch file as desired. """
        if not self.reBoarModPath.search(record.modPath or ''): return
        reBoar  = self.reBoar
        for bodyPart in record.bodyParts:
            if reBoar.search(bodyPart):
                break
        else:
            return
        spells = record.spells
        newSpell = self.spell
        if newSpell not in spells:
            override = record.CopyAsOverride(self.patchFile)
            if override:
                spells.append(newSpell)
                override.spells = spells
                self.mod_count[modFile.GName] += 1
                record.UnloadRecord()
                record._RecordID = override._RecordID

#------------------------------------------------------------------------------
class ASWALKNPCAnimationPatcher(AMultiTweakItem):
    """Changes all female NPCs to use Mur Zuk's Sexy Walk."""
    tweak_name = _(u'Sexy Walk for female NPCs')
    tweak_tip = _(u"Changes all female NPCs to use Mur Zuk's Sexy Walk - "
                  u"Requires Mur Zuk's Sexy Walk animation file.")

    def __init__(self):
        super(ASWALKNPCAnimationPatcher, self).__init__(u'Mur Zuk SWalk',
            (u'1.0', u'1.0'))
        self.logMsg = u'* '+_(u'NPCs Tweaked') + u' :%d'

class SWALKNPCAnimationPatcher(ASWALKNPCAnimationPatcher,BasalNPCTweaker):

    def buildPatch(self,log,progress,patchFile):
        """Edits patch file as desired. Will write to log."""
        count = Counter()
        keep = patchFile.getKeeper()
        for record in patchFile.NPC_.records:
            if record.flags.female == 1:
                record.animations += [u'0sexywalk01.kf']
                keep(record.fid)
                count[record.fid[0]] += 1
        self._patchLog(log,count)

class CBash_SWALKNPCAnimationPatcher(ASWALKNPCAnimationPatcher, _NpcCTweak):

    def apply(self,modFile,record,bashTags,
              __player_fid=_NpcCTweak.playerFid):
        """Edits patch file as desired. """
        if record.fid != __player_fid: #skip player record
            if record.IsFemale:
                override = record.CopyAsOverride(self.patchFile)
                if override:
                    override.animations += [u'0sexywalk01.kf']
                    self.mod_count[modFile.GName] += 1
                    record.UnloadRecord()
                    record._RecordID = override._RecordID

#------------------------------------------------------------------------------
class ARWALKNPCAnimationPatcher(AMultiTweakItem):
    """Changes all female NPCs to use Mur Zuk's Real Walk."""
    tweak_name = _(u'Real Walk for female NPCs')
    tweak_tip = _(u"Changes all female NPCs to use Mur Zuk's Real Walk - "
                  u"Requires Mur Zuk's Real Walk animation file.")

    def __init__(self):
        super(ARWALKNPCAnimationPatcher, self).__init__(u'Mur Zuk RWalk',
            (u'1.0', u'1.0'))
        self.logMsg = u'* '+_(u'NPCs Tweaked') + u': %d'

class RWALKNPCAnimationPatcher(ARWALKNPCAnimationPatcher,BasalNPCTweaker):

    def buildPatch(self,log,progress,patchFile):
        count = Counter()
        keep = patchFile.getKeeper()
        for record in patchFile.NPC_.records:
            if record.flags.female == 1:
                record.animations += [u'0realwalk01.kf']
                keep(record.fid)
                count[record.fid[0]] += 1
        self._patchLog(log,count)

class CBash_RWALKNPCAnimationPatcher(ARWALKNPCAnimationPatcher, _NpcCTweak):

    #--Patch Phase ------------------------------------------------------------
    def apply(self,modFile,record,bashTags,
              __player_fid=_NpcCTweak.playerFid):
        """Edits patch file as desired. """
        if record.fid != __player_fid: #skip player record
            if record.IsFemale:
                override = record.CopyAsOverride(self.patchFile)
                if override:
                    override.animations += [u'0realwalk01.kf']
                    self.mod_count[modFile.GName] += 1
                    record.UnloadRecord()
                    record._RecordID = override._RecordID

#------------------------------------------------------------------------------
class AQuietFeetPatcher(AMultiTweakItem):
    """Removes 'foot' sounds from all/specified creatures - like the mod by
    the same name but works on all modded creatures."""
    tweak_name = _(u'Quiet Feet')
    tweak_tip = _(u"Removes all/some 'foot' sounds from creatures; on some"
                  u" computers can have a significant performance boost.")

    def __init__(self):
        super(AQuietFeetPatcher, self).__init__(u'silent n sneaky!',
            (_(u'All Creature Foot Sounds'), u'all'),
            (_(u'Only 4 Legged Creature Foot Sounds'), u'partial'),
            (_(u'Only Mount Foot Sounds'), u'mounts'))
        self.logMsg = u'* '+_(u'Creatures Tweaked') + u': %d'

class QuietFeetPatcher(AQuietFeetPatcher,BasalCreatureTweaker):

    def buildPatch(self,log,progress,patchFile):
        """Edits patch file as desired. Will write to log."""
        count = Counter()
        keep = patchFile.getKeeper()
        chosen = self.choiceValues[self.chosen][0]
        for record in patchFile.CREA.records:
            # Check if we're templated first (only relevant on FO3/FNV)
            if _is_templated(record, 'useModelAnimation'): continue
            sounds = record.sounds
            if chosen == u'all':
                sounds = [sound for sound in sounds if
                          sound.type not in [0, 1, 2, 3]]
            elif chosen == u'partial':
                for sound in record.sounds:
                    if sound.type in [2,3]:
                        sounds = [sound for sound in sounds if
                                  sound.type not in [0, 1, 2, 3]]
                        break
            else: # really is: "if chosen == 'mounts':", but less cpu to do it
                # as else.
                if record.creatureType == 4:
                    sounds = [sound for sound in sounds if
                              sound.type not in [0, 1, 2, 3]]
            if sounds != record.sounds:
                record.sounds = sounds
                keep(record.fid)
                count[record.fid[0]] += 1
        self._patchLog(log,count)

class CBash_QuietFeetPatcher(AQuietFeetPatcher, _CreaCTweak):

    def apply(self,modFile,record,bashTags):
        """Edits patch file as desired. """
        chosen = self.choiceValues[self.chosen][0]
        if chosen == u'partial':
            for sound in record.sounds:
                if sound.IsLeftBackFoot or sound.IsRightBackFoot:
                    break
            else:
                return
        elif chosen == u'mounts' and not record.IsHorse:
            return
        # equality operator not implemented for ObCREARecord.Sound class,
        # so use the list version instead
        # 0 = IsLeftFoot, 1 = IsRightFoot, 2 = IsLeftBackFoot,
        # 3 = IsRightBackFoot
        sounds_list = [(soundType, sound, chance) for soundType, sound, chance
                       in record.sounds_list if soundType not in [0, 1, 2, 3]]
        if sounds_list != record.sounds_list:
            override = record.CopyAsOverride(self.patchFile)
            if override:
                override.sounds_list = sounds_list
                self.mod_count[modFile.GName] += 1
                record.UnloadRecord()
                record._RecordID = override._RecordID

#------------------------------------------------------------------------------
class AIrresponsibleCreaturesPatcher(AMultiTweakItem):
    """Sets responsibility to 0 for all/specified creatures - like the mod
    by the name of Irresponsible Horses but works on all modded creatures."""
    tweak_name = _(u'Irresponsible Creatures')
    tweak_tip = _(u"Sets responsibility to 0 for all/specified creatures - so "
                  u"they can't report you for crimes.")

    def __init__(self):
        super(AIrresponsibleCreaturesPatcher, self).__init__(
            u'whatbadguarddogs',
            (_(u'All Creatures'), u'all'),
            (_(u'Only Horses'), u'mounts'))
        self.logMsg = u'* '+_(u'Creatures Tweaked') + u': %d'

class IrresponsibleCreaturesPatcher(AIrresponsibleCreaturesPatcher,
                                    BasalCreatureTweaker):

    def buildPatch(self,log,progress,patchFile):
        """Edits patch file as desired. Will write to log."""
        count = Counter()
        keep = patchFile.getKeeper()
        chosen = self.choiceValues[self.chosen][0]
        for record in patchFile.CREA.records:
            if record.responsibility == 0: continue
            # Check if we're templated first (only relevant on FO3/FNV)
            if _is_templated(record, 'useAIData'): continue
            if chosen == u'all':
                record.responsibility = 0
                keep(record.fid)
                count[record.fid[0]] += 1
            else: # really is: "if chosen == 'mounts':", but less cpu to do it
                # as else.
                if record.creatureType == 4:
                    record.responsibility = 0
                    keep(record.fid)
                    count[record.fid[0]] += 1
        self._patchLog(log,count)

class CBash_IrresponsibleCreaturesPatcher(AIrresponsibleCreaturesPatcher,
                                          _CreaCTweak):

    def apply(self,modFile,record,bashTags):
        """Edits patch file as desired. """
        if record.responsibility == 0: return
        if self.choiceValues[self.chosen][
            0] == u'mounts' and not record.IsHorse: return
        override = record.CopyAsOverride(self.patchFile)
        if override:
            override.responsibility = 0
            self.mod_count[modFile.GName] += 1
            record.UnloadRecord()
            record._RecordID = override._RecordID

#------------------------------------------------------------------------------
class _AOppositeGenderAnimsPatcher(BasalNPCTweaker):
    """Enables or disables the 'Opposite Gender Anims' flag on all male or
    female NPCs. Similar to the 'Feminine Females' mod, but applies to the
    whole load order."""
    # Whether this patcher wants female or male NPCs
    targets_female_npcs = False

    def __init__(self, tweak_key):
        super(_AOppositeGenderAnimsPatcher, self).__init__(
            tweak_key,
            (_(u'Always Disable'), u'disable_all'),
            (_(u'Always Enable'), u'enable_all'),
        )
        self.logMsg = u'* '+_(u'NPCs Tweaked') + u': %d'

    def buildPatch(self, log, progress, patchFile):
        tweaked_count = Counter()
        keep = patchFile.getKeeper()
        # What we want to set the 'Opposite Gender Anims' flag to
        oga_target = self.choiceValues[self.chosen][0] == u'enable_all'
        gender_target = self.targets_female_npcs
        for curr_record in patchFile.NPC_.records:
            # Skip any NPCs that don't match this patcher's target gender
            if gender_target != curr_record.flags.female: continue
            if curr_record.flags.oppositeGenderAnims != oga_target:
                curr_record.flags.oppositeGenderAnims = oga_target
                keep(curr_record.fid)
                tweaked_count[curr_record.fid[0]] += 1
        self._patchLog(log, tweaked_count)

class OppositeGenderAnimsPatcher_Female(_AOppositeGenderAnimsPatcher):
    targets_female_npcs = True
    tweak_name = _(u'Opposite Gender Anims: Female')
    tweak_tip = _(u"Enables or disables the 'Opposite Gender Anims' for all "
                  u"female NPCs. Similar to the 'Feminine Females' mod.")

    def __init__(self):
        super(OppositeGenderAnimsPatcher_Female, self).__init__(
            u'opposite_gender_anims_female')

class OppositeGenderAnimsPatcher_Male(_AOppositeGenderAnimsPatcher):
    tweak_name =  _(u'Opposite Gender Anims: Male')
    tweak_tip = _(u"Enables or disables the 'Opposite Gender Anims' for all "
                  u"male NPCs. Similar to the 'Feminine Females' mod.")

    def __init__(self):
        super(OppositeGenderAnimsPatcher_Male, self).__init__(
            u'opposite_gender_anims_male')

#------------------------------------------------------------------------------
class TweakActors(MultiTweaker):
    """Sets Creature stuff or NPC Skeletons, Animations or other settings to
    better work with mods or avoid bugs."""
    _tweak_classes = sorted(
        [globals()[tweak_name] for tweak_name in bush.game.actor_tweaks],
        key=lambda a: a.tweak_name.lower())

class CBash_TweakActors(CBash_MultiTweaker):
    """Sets Creature stuff or NPC Skeletons, Animations or other settings to
    better work with mods or avoid bugs."""
    _tweak_classes = [CBash_VORB_NPCSkeletonPatcher,
        CBash_MAONPCSkeletonPatcher, CBash_VanillaNPCSkeletonPatcher,
        CBash_RedguardNPCPatcher, CBash_NoBloodCreaturesPatcher,
        CBash_AsIntendedImpsPatcher, CBash_AsIntendedBoarsPatcher,
        CBash_QuietFeetPatcher, CBash_IrresponsibleCreaturesPatcher,
        CBash_RWALKNPCAnimationPatcher, CBash_SWALKNPCAnimationPatcher]
