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

# Patchers: 30 ----------------------------------------------------------------
class _AActorTweak(AMultiTweakItem):
    """Hasty abstraction over PBash/CBash records differences to allow moving
    wants_record overrides into the abstract classes."""
    _player_fid = None # override in implementations

    @staticmethod
    def _get_skeleton_path(record):
        """Retrieves an actor's skeleton model path from the specified record.
        May return None if the path is not present."""
        raise AbstractError(u'_get_skeleton_path not implemented')

    @staticmethod
    def _get_sound_type(creature_sound):
        """Returns the sound type of the specified creature sound."""
        raise AbstractError(u'_get_sound_type not implemented')

    @staticmethod
    def _is_female(record):
        """Returns True if the specified record is a female NPC."""
        raise AbstractError(u'_is_female not implemented')

    @staticmethod
    def _is_male(record):
        """Returns True if the specified record is a male NPC."""
        raise AbstractError(u'_is_male not implemented')

    @staticmethod
    def _is_templated(record, flag_name):
        """Checks if the specified record has a template record and the
        appropriate template flag set."""
        raise AbstractError(u'_is_templated not implemented')

class _BasalActorTweaker(MultiTweakItem, _AActorTweak):
    """Base for all PBash actor tweaks."""
    def buildPatch(self,log,progress,patchFile):
        raise AbstractError(u'buildPatch not implemented')

    @staticmethod
    def _get_skeleton_path(record):
        try:
            return record.model.modPath
        except AttributeError:
            # Some weird plugins have NPCs with no skeleton assigned to them
            return None

    @staticmethod
    def _is_templated(record, flag_name):
        return (getattr(record, u'template', None) is not None
                and getattr(record.templateFlags, flag_name))

class BasalNPCTweaker(_BasalActorTweaker):
    """Base for all PBash NPC tweaks."""
    tweak_read_classes = b'NPC_',
    _player_fid = (GPath(bush.game.master_file), 0x000007)

    @staticmethod
    def _is_female(record): return record.flags.female

    @staticmethod
    def _is_male(record): return not record.flags.female

class BasalCreatureTweaker(_BasalActorTweaker):
    """Base for all PBash Creature tweaks."""
    tweak_read_classes = b'CREA',

    @staticmethod
    def _get_sound_type(creature_sound):
        return creature_sound.type

class _ActorCTweak(CBash_MultiTweakItem, _AActorTweak):
    """Base for all CBash actor tweaks."""
    @staticmethod
    def _get_skeleton_path(record): return record.modPath

    @staticmethod
    def _is_templated(record, flag_name):
        return False # CBash is Oblivion-only for now, so no template flags

class _NpcCTweak(_ActorCTweak):
    """Base for all CBash NPC tweaks."""
    tweak_read_classes = b'NPC_',
    _player_fid = FormID(GPath(bush.game.master_file), 0x000007)

    @staticmethod
    def _is_female(record): return record.IsFemale

    @staticmethod
    def _is_male(record): return record.IsMale

class _CreaCTweak(_ActorCTweak):
    """Base for all CBash Creature tweaks."""
    tweak_read_classes = b'CREA',

    @staticmethod
    def _get_sound_type(creature_sound):
        return creature_sound.soundType

class _AFemaleOnlyTweak(_AActorTweak):
    """Provides a PBash/CBash-agnostic implementation of wants_record for
    female-only tweaks. Shared by Sexy and Real Walk tweaks."""
    def wants_record(self, record):
        ##: != player_fid part was in CBash impls only, verify
        return record.fid != self._player_fid and self._is_female(record)

#------------------------------------------------------------------------------
class _ASkeletonTweak(_AActorTweak):
    """Shared code of CBash/PBash MAO/VORB skeleton tweaks."""
    def _get_target_skeleton(self, record):
        """Returns the skeleton path that we want to change the skeleton of the
        specified record to."""
        raise AbstractError(u'_get_target_skeleton not implemented')

    def wants_record(self, record):
        chosen_gender = self.choiceValues[self.chosen][0]
        if chosen_gender == 1 and self._is_male(record): return False
        elif chosen_gender == 2 and self._is_female(record): return False
        return (record.fid != self._player_fid and
                self._get_skeleton_path(record) !=
                self._get_target_skeleton(record))

class _PSkeletonTweak(_ASkeletonTweak, BasalNPCTweaker):
    """Shared code of PBash MAO/VORB skeleton tweaks."""
    def buildPatch(self,log,progress,patchFile):
        """Edits patch file as desired. Will write to log."""
        count = Counter()
        keep = patchFile.getKeeper()
        for record in patchFile.NPC_.records:
            if self.wants_record(record):
                record.model.modPath = self._get_target_skeleton(record)
                keep(record.fid)
                count[record.fid[0]] += 1
        self._patchLog(log, count)

class _CSkeletonTweak(_ASkeletonTweak, _NpcCTweak):
    """Shared code of CBash MAO/VORB skeleton tweaks."""
    def apply(self, modFile, record, bashTags):
        """Edits patch file as desired. """
        if self.wants_record(record):
            override = record.CopyAsOverride(self.patchFile)
            if override:
                override.modPath = self._get_target_skeleton(record)
                self.mod_count[modFile.GName] += 1
                record.UnloadRecord()
                record._RecordID = override._RecordID

#------------------------------------------------------------------------------
class AMAONPCSkeletonPatcher(_ASkeletonTweak):
    """Changes all NPCs to use the right Mayu's Animation Overhaul Skeleton
    for use with MAO."""
    tweak_name = _(u"Mayu's Animation Overhaul Skeleton Tweaker")
    tweak_tip = _(u'Changes all (modded and vanilla) NPCs to use the MAO '
                  u'skeletons.  Not compatible with VORB.  Note: ONLY use if '
                  u'you have MAO installed.')
    _sheo_skeleton = u'characters\\_male\\skeletonsesheogorath.nif'
    _sheo_skeleton_mao = (u"Mayu's Projects[M]\\Animation Overhaul\\Vanilla\\"
                          u'SkeletonSESheogorath.nif')
    _skeleton_mao = (u"Mayu's Projects[M]\\Animation Overhaul\\Vanilla\\"
                     u'SkeletonBeast.nif')

    def __init__(self):
        super(AMAONPCSkeletonPatcher, self).__init__(u'MAO Skeleton',
            (_(u'All NPCs'), 0), (_(u'Only Female NPCs'), 1),
            (_(u'Only Male NPCs'), 2))
        self.logHeader = u'=== ' + _(u'MAO Skeleton Setter')
        self.logMsg = u'* ' + _(u'Skeletons Tweaked: %d')

    def _get_target_skeleton(self, record):
        # Don't change Sheo's skeleton to a beast skeleton if it's already the
        # mao version
        return (self._sheo_skeleton_mao if self._get_skeleton_path(record) in (
            self._sheo_skeleton, self._sheo_skeleton_mao)
                else self._skeleton_mao)

class MAONPCSkeletonPatcher(AMAONPCSkeletonPatcher, _PSkeletonTweak): pass
class CBash_MAONPCSkeletonPatcher(AMAONPCSkeletonPatcher,
                                  _CSkeletonTweak): pass

#------------------------------------------------------------------------------
class AVORB_NPCSkeletonPatcher(_ASkeletonTweak):
    """Changes all NPCs to use the diverse skeleton for different look."""
    tweak_name = _(u"VadersApp's Oblivion Real Bodies Skeleton Tweaker")
    tweak_tip = _(u"Changes all (modded and vanilla) NPCs to use diverse "
                  u"skeletons for different look.  Not compatible with MAO, "
                  u"Requires VadersApp's Oblivion Real Bodies.")
    skeleton_dir = GPath(u'Characters').join(u'_male')

    def __init__(self):
        super(AVORB_NPCSkeletonPatcher, self).__init__(u'VORB',
            (_(u'All NPCs'), 0), (_(u'Only Female NPCs'), 1),
            (_(u'Only Male NPCs'), 2))
        self.logHeader = u'=== ' + _(u"VadersApp's Oblivion Real Bodies")
        self.logMsg = u'* ' + _(u'Skeletons Tweaked: %d')

    def _get_skeleton_collections(self):
        """construct skeleton mesh collections. skeleton_list gets files that
        match the pattern "skel_*.nif", but not "skel_special_*.nif".
        skeleton_specials gets files that match "skel_special_*.nif". Cached
        for reuse later."""
        try:
            return self._skeleton_list, self._skeleton_specials
        except AttributeError:
            # Since bass.dirs hasn't been populated when __init__ executes,
            # we do this here
            skeleton_dir = bass.dirs[u'mods'].join(u'Meshes', u'Characters',
                                                   u'_male')
            list_skel_dir = skeleton_dir.list() # empty if dir does not exist
            skel_nifs = [x for x in list_skel_dir if
                         x.cs.startswith(u'skel_') and x.cext == u'.nif']
            skeleton_list = [x for x in skel_nifs
                             if not x.cs.startswith(u'skel_special_')]
            set_skeleton_list = set(skeleton_list)
            skeleton_specials = set(
                x.s for x in skel_nifs if x not in set_skeleton_list)
            self._skeleton_list, self._skeleton_specials = (skeleton_list,
                                                            skeleton_specials)
            return skeleton_list, skeleton_specials

    def _get_target_skeleton(self, record):
        # Cached, so calling this over and over is fine
        skeleton_list, skeleton_specials = self._get_skeleton_collections()
        if not skeleton_list:
            return self._get_skeleton_path(record) # leave unchanged
        special_skel_mesh = u'skel_special_%X.nif' % record.fid[1]
        if special_skel_mesh in skeleton_specials:
            return self.skeleton_dir.join(special_skel_mesh)
        else:
            random.seed(record.fid) # make it deterministic ##: record.fid[1]?
            rand_index = random.randint(1, len(skeleton_list)) - 1
            return self.skeleton_dir.join(skeleton_list[rand_index]).s

class VORB_NPCSkeletonPatcher(AVORB_NPCSkeletonPatcher, _PSkeletonTweak): pass
class CBash_VORB_NPCSkeletonPatcher(AVORB_NPCSkeletonPatcher,
                                    _CSkeletonTweak): pass

#------------------------------------------------------------------------------
class AVanillaNPCSkeletonPatcher(_AActorTweak):
    """Changes all NPCs to use the vanilla beast race skeleton."""
    tweak_name = _(u'Vanilla Beast Skeleton Tweaker')
    tweak_tip = _(u'Avoids visual glitches if an NPC is a beast race but has '
                  u'the regular skeleton.nif selected, but can cause '
                  u'performance issues.')
    _new_skeleton = u'Characters\\_Male\\SkeletonBeast.nif'
    _old_skeleton = u'characters\\_male\\skeleton.nif'

    def __init__(self):
        super(AVanillaNPCSkeletonPatcher, self).__init__(u'Vanilla Skeleton',
            (u'1.0', u'1.0'))
        self.logHeader = u'=== ' + _(u'Vanilla Beast Skeleton')
        self.logMsg = u'* ' + _(u'Skeletons Tweaked: %d')

    def wants_record(self, record):
        old_mod_path = self._get_skeleton_path(record)
        return old_mod_path and old_mod_path.lower() == self._old_skeleton

class VanillaNPCSkeletonPatcher(AVanillaNPCSkeletonPatcher,BasalNPCTweaker):
    def buildPatch(self,log,progress,patchFile):
        """Edits patch file as desired. Will write to log."""
        count = Counter()
        keep = patchFile.getKeeper()
        for record in patchFile.NPC_.records:
            if self.wants_record(record):
                record.model.modPath = self._new_skeleton
                keep(record.fid)
                count[record.fid[0]] += 1
        self._patchLog(log,count)

class CBash_VanillaNPCSkeletonPatcher(AVanillaNPCSkeletonPatcher, _NpcCTweak):
    scanOrder = 31 #Run before MAO
    editOrder = 31

    def apply(self,modFile,record,bashTags):
        """Edits patch file as desired. """
        if self.wants_record(record):
            override = record.CopyAsOverride(self.patchFile)
            if override:
                override.modPath = self._new_skeleton
                self.mod_count[modFile.GName] += 1
                record.UnloadRecord()
                record._RecordID = override._RecordID

#------------------------------------------------------------------------------
class ARedguardNPCPatcher(_AActorTweak):
    """Changes all Redguard NPCs texture symmetry for Better Redguard
    Compatibility."""
    tweak_name = _(u'Redguard FGTS Patcher')
    tweak_tip = _(u'Nulls FGTS of all Redguard NPCs - for compatibility with '
                  u'Better Redguards.')
    _redguard_fid = None # override in implementations

    def __init__(self):
        super(ARedguardNPCPatcher, self).__init__(u'RedguardFGTSPatcher',
            (u'1.0', u'1.0'))
        self.logHeader = u'=== ' + _(u'Redguard FGTS Patcher')
        self.logMsg = u'* ' + _(u'Redguard NPCs Tweaked: %d')

    def wants_record(self, record):
        # Only affect NPCs with the redguard race
        return record.race == self.__class__._redguard_fid

class RedguardNPCPatcher(ARedguardNPCPatcher,BasalNPCTweaker):
    _redguard_fid = (GPath(bush.game.master_file), 0x00000D43)

    def buildPatch(self,log,progress,patchFile):
        """Edits patch file as desired. Will write to log."""
        count = Counter()
        keep = patchFile.getKeeper()
        for record in patchFile.NPC_.records:
            if self.wants_record(record):
                record.fgts_p = '\x00'*200
                keep(record.fid)
                count[record.fid[0]] += 1
        self._patchLog(log,count)

class CBash_RedguardNPCPatcher(ARedguardNPCPatcher, _NpcCTweak):
    _redguard_fid = FormID(GPath(bush.game.master_file), 0x00000D43)

    def apply(self,modFile,record,bashTags):
        """Edits patch file as desired. """
        if self.wants_record(record):
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
class ANoBloodCreaturesPatcher(_AActorTweak):
    """Set all creatures to have no blood records."""
    tweak_name = _(u'No Bloody Creatures')
    tweak_tip = _(u'Set all creatures to have no blood records, will have '
                  u'pretty much no effect when used with MMM since the MMM '
                  u'blood uses a different system.')

    def __init__(self):
        super(ANoBloodCreaturesPatcher, self).__init__(u'No bloody creatures',
            (u'1.0', u'1.0'))
        self.logMsg = u'* ' + _(u'Creatures Tweaked: %d')

    def wants_record(self, record):
        return record.bloodDecalPath or record.bloodSprayPath

class NoBloodCreaturesPatcher(ANoBloodCreaturesPatcher,BasalCreatureTweaker):
    def buildPatch(self,log,progress,patchFile):
        """Edits patch file as desired. Will write to log."""
        count = Counter()
        keep = patchFile.getKeeper()
        for record in patchFile.CREA.records:
            if self.wants_record(record):
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
        if self.wants_record(record):
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
class AAsIntendedImpsPatcher(_AActorTweak):
    """Set all imps to have the Bethesda imp spells that were never assigned
    (discovered by the UOP team, made into a mod by Tejon)."""
    reImpModPath = re.compile(u'' r'(imp(?!erial)|gargoyle)\\.', re.I | re.U)
    reImp  = re.compile(u'(imp(?!erial)|gargoyle)',re.I|re.U)
    tweak_name = _(u'As Intended: Imps')
    tweak_tip = _(u'Set imps to have the unassigned Bethesda Imp Spells as '
                  u'discovered by the UOP team and made into a mod by Tejon.')
    _imp_spell = None # override in implementations

    def __init__(self):
        super(AAsIntendedImpsPatcher, self).__init__(u'vicious imps!',
            (_(u'All imps'), u'all'), (_(u'Only fullsize imps'), u'big'),
            (_(u'Only implings'), u'small'))
        self.logMsg = u'* ' + _(u'Imps Tweaked: %d')

    def wants_record(self, record):
        old_mod_path = self._get_skeleton_path(record)
        if not old_mod_path or not self.reImpModPath.search(old_mod_path):
            return False
        if not any(self.reImp.search(bp) for bp in record.bodyParts):
            return False
        if record.baseScale < 0.4:
            if u'big' in self.choiceValues[self.chosen]: return False
        elif u'small' in self.choiceValues[self.chosen]: return False
        return self._imp_spell not in record.spells

class AsIntendedImpsPatcher(AAsIntendedImpsPatcher,BasalCreatureTweaker):
    _imp_spell = (GPath(bush.game.master_file), 0x02B53F)

    def buildPatch(self,log,progress,patchFile):
        """Edits patch file as desired. Will write to log."""
        count = Counter()
        keep = patchFile.getKeeper()
        for record in patchFile.CREA.records:
            if self.wants_record(record):
                record.spells.append(self._imp_spell)
                keep(record.fid)
                count[record.fid[0]] += 1
        self._patchLog(log,count)

class CBash_AsIntendedImpsPatcher(AAsIntendedImpsPatcher, _CreaCTweak):
    _imp_spell = FormID(GPath(bush.game.master_file), 0x02B53F)

    def apply(self,modFile,record,bashTags):
        """Edits patch file as desired. """
        if self.wants_record(record):
            override = record.CopyAsOverride(self.patchFile)
            if override:
                # Can't use append because of cint __get__/__set__ nonsense
                override.spells += [self._imp_spell]
                self.mod_count[modFile.GName] += 1
                record.UnloadRecord()
                record._RecordID = override._RecordID

#------------------------------------------------------------------------------
class AAsIntendedBoarsPatcher(_AActorTweak):
    """Set all boars to have the Bethesda boar spells that were never
    assigned (discovered by the UOP team, made into a mod by Tejon)."""
    reBoarModPath = re.compile(u'' r'(boar)\\.', re.I | re.U)
    reBoar  = re.compile(u'(boar)', re.I|re.U)
    tweak_name = _(u'As Intended: Boars')
    tweak_tip = _(u'Set boars to have the unassigned Bethesda Boar Spells as '
                  u'discovered by the UOP team and made into a mod by Tejon.')
    _boar_spell = None # override in implementations

    def __init__(self):
        super(AAsIntendedBoarsPatcher, self).__init__(u'vicious boars!',
            (u'1.0', u'1.0'))
        self.logMsg = u'* ' + _(u'Boars Tweaked: %d')

    def wants_record(self, record):
        old_mod_path = self._get_skeleton_path(record)
        if not old_mod_path or not self.reBoarModPath.search(old_mod_path):
            return False
        if not any(self.reBoar.search(bp) for bp in record.bodyParts):
            return False
        return self._boar_spell not in record.spells

class AsIntendedBoarsPatcher(AAsIntendedBoarsPatcher,BasalCreatureTweaker):
    _boar_spell = (GPath(bush.game.master_file), 0x02B54E)

    def buildPatch(self,log,progress,patchFile):
        """Edits patch file as desired. Will write to log."""
        count = Counter()
        keep = patchFile.getKeeper()
        for record in patchFile.CREA.records:
            if self.wants_record(record):
                record.spells.append(self._boar_spell)
                keep(record.fid)
                count[record.fid[0]] += 1
        self._patchLog(log,count)

class CBash_AsIntendedBoarsPatcher(AAsIntendedBoarsPatcher, _CreaCTweak):
    _boar_spell = FormID(GPath(bush.game.master_file), 0x02B54E)

    def apply(self,modFile,record,bashTags):
        """Edits patch file as desired. """
        if self.wants_record(record):
            override = record.CopyAsOverride(self.patchFile)
            if override:
                # Can't use append because of cint __get__/__set__ nonsense
                override.spells += [self._boar_spell]
                self.mod_count[modFile.GName] += 1
                record.UnloadRecord()
                record._RecordID = override._RecordID

#------------------------------------------------------------------------------
class ASWALKNPCAnimationPatcher(_AFemaleOnlyTweak):
    """Changes all female NPCs to use Mur Zuk's Sexy Walk."""
    tweak_name = _(u'Sexy Walk for female NPCs')
    tweak_tip = _(u"Changes all female NPCs to use Mur Zuk's Sexy Walk - "
                  u"Requires Mur Zuk's Sexy Walk animation file.")

    def __init__(self):
        super(ASWALKNPCAnimationPatcher, self).__init__(u'Mur Zuk SWalk',
            (u'1.0', u'1.0'))
        self.logMsg = u'* ' + _(u'NPCs Tweaked: %d')

class SWALKNPCAnimationPatcher(ASWALKNPCAnimationPatcher,BasalNPCTweaker):
    def buildPatch(self,log,progress,patchFile):
        """Edits patch file as desired. Will write to log."""
        count = Counter()
        keep = patchFile.getKeeper()
        for record in patchFile.NPC_.records:
            if self.wants_record(record):
                record.animations += [u'0sexywalk01.kf']
                keep(record.fid)
                count[record.fid[0]] += 1
        self._patchLog(log,count)

class CBash_SWALKNPCAnimationPatcher(ASWALKNPCAnimationPatcher, _NpcCTweak):
    def apply(self,modFile,record,bashTags):
        """Edits patch file as desired. """
        if self.wants_record(record):
            override = record.CopyAsOverride(self.patchFile)
            if override:
                override.animations += [u'0sexywalk01.kf']
                self.mod_count[modFile.GName] += 1
                record.UnloadRecord()
                record._RecordID = override._RecordID

#------------------------------------------------------------------------------
class ARWALKNPCAnimationPatcher(_AFemaleOnlyTweak):
    """Changes all female NPCs to use Mur Zuk's Real Walk."""
    tweak_name = _(u'Real Walk for female NPCs')
    tweak_tip = _(u"Changes all female NPCs to use Mur Zuk's Real Walk - "
                  u"Requires Mur Zuk's Real Walk animation file.")

    def __init__(self):
        super(ARWALKNPCAnimationPatcher, self).__init__(u'Mur Zuk RWalk',
            (u'1.0', u'1.0'))
        self.logMsg = u'* ' + _(u'NPCs Tweaked: %d')

class RWALKNPCAnimationPatcher(ARWALKNPCAnimationPatcher,BasalNPCTweaker):
    def buildPatch(self,log,progress,patchFile):
        count = Counter()
        keep = patchFile.getKeeper()
        for record in patchFile.NPC_.records:
            if self.wants_record(record):
                record.animations += [u'0realwalk01.kf']
                keep(record.fid)
                count[record.fid[0]] += 1
        self._patchLog(log,count)

class CBash_RWALKNPCAnimationPatcher(ARWALKNPCAnimationPatcher, _NpcCTweak):
    def apply(self,modFile,record,bashTags):
        """Edits patch file as desired. """
        if self.wants_record(record):
            override = record.CopyAsOverride(self.patchFile)
            if override:
                override.animations += [u'0realwalk01.kf']
                self.mod_count[modFile.GName] += 1
                record.UnloadRecord()
                record._RecordID = override._RecordID

#------------------------------------------------------------------------------
class AQuietFeetPatcher(_AActorTweak):
    """Removes 'foot' sounds from all/specified creatures - like the mod by
    the same name but works on all modded creatures."""
    tweak_name = _(u'Quiet Feet')
    tweak_tip = _(u"Removes all/some 'foot' sounds from creatures; on some"
                  u" computers can have a significant performance boost.")
    # Sound Types: 0 = left foot, 1 = right foot, 2 = left back foot,
    # 3 = right back foot

    def __init__(self):
        super(AQuietFeetPatcher, self).__init__(u'silent n sneaky!',
            (_(u'All Creature Foot Sounds'), u'all'),
            (_(u'Only 4 Legged Creature Foot Sounds'), u'partial'),
            (_(u'Only Mount Foot Sounds'), u'mounts'))
        self.logMsg = u'* ' + _(u'Creatures Tweaked: %d')

    def _get_silenced_sounds(self, record):
        """Returns the sounds of the specified record, with all footstep sound
        silenced."""
        return [s for s in record.sounds if self._get_sound_type(s)
                not in (0, 1, 2, 3)]

    def wants_record(self, record):
        # Check if we're templated first (only relevant on FO3/FNV)
        if self._is_templated(record, u'useModelAnimation'): return False
        chosen_target = self.choiceValues[self.chosen][0]
        if chosen_target == u'partial' and not any(
                self._get_sound_type(s) in (2, 3) for s in record.sounds):
            return False
        elif chosen_target == u'mounts' and record.creatureType != 4:
            return False
        return record.sounds != self._get_silenced_sounds(record)

class QuietFeetPatcher(AQuietFeetPatcher,BasalCreatureTweaker):
    def buildPatch(self,log,progress,patchFile):
        """Edits patch file as desired. Will write to log."""
        count = Counter()
        keep = patchFile.getKeeper()
        for record in patchFile.CREA.records:
            if self.wants_record(record):
                record.sounds = self._get_silenced_sounds(record)
                keep(record.fid)
                count[record.fid[0]] += 1
        self._patchLog(log,count)

class CBash_QuietFeetPatcher(AQuietFeetPatcher, _CreaCTweak):
    def apply(self,modFile,record,bashTags):
        """Edits patch file as desired. """
        if self.wants_record(record):
            override = record.CopyAsOverride(self.patchFile)
            if override:
                override.sounds = self._get_silenced_sounds(record)
                self.mod_count[modFile.GName] += 1
                record.UnloadRecord()
                record._RecordID = override._RecordID

#------------------------------------------------------------------------------
class AIrresponsibleCreaturesPatcher(_AActorTweak):
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
        self.logMsg = u'* ' + _(u'Creatures Tweaked: %d')

    def wants_record(self, record):
        # Must not be templated (FO3/FNV only), the creature must not be
        # irresponsible already, and if we're in 'only horses' mode, the
        # creature must be a horse
        return (not self._is_templated(record, u'useAIData')
                and record.responsibility != 0
                and (self.choiceValues[self.chosen][0] == u'all'
                     or record.creatureType == 4))

class IrresponsibleCreaturesPatcher(AIrresponsibleCreaturesPatcher,
                                    BasalCreatureTweaker):
    def buildPatch(self,log,progress,patchFile):
        """Edits patch file as desired. Will write to log."""
        count = Counter()
        keep = patchFile.getKeeper()
        for record in patchFile.CREA.records:
            if self.wants_record(record):
                record.responsibility = 0
                keep(record.fid)
                count[record.fid[0]] += 1
        self._patchLog(log,count)

class CBash_IrresponsibleCreaturesPatcher(AIrresponsibleCreaturesPatcher,
                                          _CreaCTweak):
    def apply(self,modFile,record,bashTags):
        """Edits patch file as desired. """
        if self.wants_record(record):
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
        self.logMsg = u'* ' + _(u'NPCs Tweaked: %d')

    def wants_record(self, record):
        # Skip any NPCs that don't match this patcher's target gender
        oga_target = self.choiceValues[self.chosen][0] == u'enable_all'
        return (record.flags.female == self.targets_female_npcs
                and record.flags.oppositeGenderAnims != oga_target)

    def buildPatch(self, log, progress, patchFile):
        count = Counter()
        keep = patchFile.getKeeper()
        # What we want to set the 'Opposite Gender Anims' flag to
        oga_target = self.choiceValues[self.chosen][0] == u'enable_all'
        for record in patchFile.NPC_.records:
            if self.wants_record(record):
                record.flags.oppositeGenderAnims = oga_target
                keep(record.fid)
                count[record.fid[0]] += 1
        self._patchLog(log, count)

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
        (globals()[t] for t in bush.game.actor_tweaks),
        key=lambda a: a.tweak_name.lower())

class CBash_TweakActors(CBash_MultiTweaker):
    """Sets Creature stuff or NPC Skeletons, Animations or other settings to
    better work with mods or avoid bugs."""
    _tweak_classes = sorted(
        (globals()[u'CBash_' + t] for t in bush.game.actor_tweaks),
        key=lambda a: a.tweak_name.lower()) if bush.game.Esp.canCBash else []
