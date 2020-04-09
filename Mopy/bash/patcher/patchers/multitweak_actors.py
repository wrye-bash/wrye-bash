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
    tweak_choices = [(_(u'All NPCs'), 0), (_(u'Only Female NPCs'), 1),
                     (_(u'Only Male NPCs'), 2)]
    tweak_log_msg = _(u'Skeletons Tweaked: %(total_changed)d')

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
    def tweak_record(self, record):
        record.model.modPath = self._get_target_skeleton(record)

class _CSkeletonTweak(_ASkeletonTweak, _NpcCTweak):
    """Shared code of CBash MAO/VORB skeleton tweaks."""
    def tweak_record(self, record):
        record.modPath = self._get_target_skeleton(record)

#------------------------------------------------------------------------------
class AMAONPCSkeletonPatcher(_ASkeletonTweak):
    """Changes all NPCs to use the right Mayu's Animation Overhaul Skeleton
    for use with MAO."""
    tweak_name = _(u"Mayu's Animation Overhaul Skeleton Tweaker")
    tweak_tip = _(u'Changes all (modded and vanilla) NPCs to use the MAO '
                  u'skeletons.  Not compatible with VORB.  Note: ONLY use if '
                  u'you have MAO installed.')
    tweak_key = u'MAO Skeleton'
    tweak_log_header = _(u'MAO Skeleton Setter')
    _sheo_skeleton = u'characters\\_male\\skeletonsesheogorath.nif'
    _sheo_skeleton_mao = (u"Mayu's Projects[M]\\Animation Overhaul\\Vanilla\\"
                          u'SkeletonSESheogorath.nif')
    _skeleton_mao = (u"Mayu's Projects[M]\\Animation Overhaul\\Vanilla\\"
                     u'SkeletonBeast.nif')

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
    tweak_key = u'VORB'
    tweak_log_header = _(u"VadersApp's Oblivion Real Bodies")
    _skeleton_dir = GPath(u'Characters').join(u'_male')

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
            return self._skeleton_dir.join(special_skel_mesh)
        else:
            random.seed(record.fid) # make it deterministic ##: record.fid[1]?
            rand_index = random.randint(1, len(skeleton_list)) - 1
            return self._skeleton_dir.join(skeleton_list[rand_index]).s

class VORB_NPCSkeletonPatcher(AVORB_NPCSkeletonPatcher, _PSkeletonTweak): pass
class CBash_VORB_NPCSkeletonPatcher(AVORB_NPCSkeletonPatcher,
                                    _CSkeletonTweak): pass

#------------------------------------------------------------------------------
class AVanillaNPCSkeletonPatcher(_ASkeletonTweak):
    """Changes all NPCs to use the vanilla beast race skeleton."""
    tweak_name = _(u'Vanilla Beast Skeleton Tweaker')
    tweak_tip = _(u'Avoids visual glitches if an NPC is a beast race but has '
                  u'the regular skeleton.nif selected, but can cause '
                  u'performance issues.')
    tweak_key = u'Vanilla Skeleton'
    tweak_choices = [(u'1.0', u'1.0')]
    tweak_log_header = _(u'Vanilla Beast Skeleton')
    _new_skeleton = u'Characters\\_Male\\SkeletonBeast.nif'
    _old_skeleton = u'characters\\_male\\skeleton.nif'

    def wants_record(self, record):
        old_mod_path = self._get_skeleton_path(record)
        return old_mod_path and old_mod_path.lower() == self._old_skeleton

    def _get_target_skeleton(self, record):
        return self._new_skeleton

class VanillaNPCSkeletonPatcher(AVanillaNPCSkeletonPatcher,
                                _PSkeletonTweak): pass
class CBash_VanillaNPCSkeletonPatcher(AVanillaNPCSkeletonPatcher,
                                      _CSkeletonTweak):
    scanOrder = 31 #Run before MAO
    editOrder = 31

#------------------------------------------------------------------------------
class ARedguardNPCPatcher(_AActorTweak):
    """Changes all Redguard NPCs texture symmetry for Better Redguard
    Compatibility."""
    tweak_name = _(u'Redguard FGTS Patcher')
    tweak_tip = _(u'Nulls FGTS of all Redguard NPCs - for compatibility with '
                  u'Better Redguards.')
    tweak_key = u'RedguardFGTSPatcher'
    tweak_log_msg = _(u'Redguard NPCs Tweaked: %(total_changed)d')
    tweak_choices = [(u'1.0', u'1.0')]
    _redguard_fid = None # override in implementations

    def wants_record(self, record):
        # Only affect NPCs with the redguard race
        return record.race == self.__class__._redguard_fid

class RedguardNPCPatcher(ARedguardNPCPatcher,BasalNPCTweaker):
    _redguard_fid = (GPath(bush.game.master_file), 0x00000D43)

    def wants_record(self, record):
        return (super(RedguardNPCPatcher, self).wants_record(record) and
                record.fgts_p != b'\x00' * 200)

    def tweak_record(self, record):
        record.fgts_p = b'\x00' * 200

class CBash_RedguardNPCPatcher(ARedguardNPCPatcher, _NpcCTweak):
    _redguard_fid = FormID(GPath(bush.game.master_file), 0x00000D43)

    def wants_record(self, record):
        return (super(CBash_RedguardNPCPatcher, self).wants_record(record) and
                record.fgts_p != [0x00] * 200)

    def tweak_record(self, record):
        record.fgts_p = [0x00] * 200

#------------------------------------------------------------------------------
class ANoBloodCreaturesPatcher(_AActorTweak):
    """Set all creatures to have no blood records."""
    tweak_name = _(u'No Bloody Creatures')
    tweak_tip = _(u'Set all creatures to have no blood records, will have '
                  u'pretty much no effect when used with MMM since the MMM '
                  u'blood uses a different system.')
    tweak_key = u'No bloody creatures'
    tweak_choices = [(u'1.0', u'1.0')]
    tweak_log_msg = _(u'Creatures Tweaked: %(total_changed)d')

    def wants_record(self, record):
        return record.bloodDecalPath or record.bloodSprayPath

class NoBloodCreaturesPatcher(ANoBloodCreaturesPatcher,BasalCreatureTweaker):
    def tweak_record(self, record):
        record.bloodDecalPath = None
        record.bloodSprayPath = None
        record.flags.noBloodSpray = True
        record.flags.noBloodDecal = True

class CBash_NoBloodCreaturesPatcher(ANoBloodCreaturesPatcher, _CreaCTweak):
    def tweak_record(self, record):
        record.bloodDecalPath = None
        record.bloodSprayPath = None
        record.IsNoBloodSpray = True
        record.IsNoBloodDecal = True

#------------------------------------------------------------------------------
class AAsIntendedImpsPatcher(_AActorTweak):
    """Set all imps to have the Bethesda imp spells that were never assigned
    (discovered by the UOP team, made into a mod by Tejon)."""
    tweak_name = _(u'As Intended: Imps')
    tweak_tip = _(u'Set imps to have the unassigned Bethesda Imp Spells as '
                  u'discovered by the UOP team and made into a mod by Tejon.')
    tweak_key = u'vicious imps!'
    tweak_choices = [(_(u'All imps'), u'all'),
                     (_(u'Only fullsize imps'), u'big'),
                     (_(u'Only implings'), u'small')]
    tweak_log_msg = _(u'Imps Tweaked: %(total_changed)d')
    _imp_mod_path = re.compile(u'' r'(imp(?!erial)|gargoyle)\\.', re.I | re.U)
    _imp_part  = re.compile(u'(imp(?!erial)|gargoyle)', re.I | re.U)
    _imp_spell = None # override in implementations

    def wants_record(self, record):
        old_mod_path = self._get_skeleton_path(record)
        if not old_mod_path or not self._imp_mod_path.search(old_mod_path):
            return False
        if not any(self._imp_part.search(bp) for bp in record.bodyParts):
            return False
        if record.baseScale < 0.4:
            if u'big' in self.choiceValues[self.chosen]: return False
        elif u'small' in self.choiceValues[self.chosen]: return False
        return self._imp_spell not in record.spells

    def tweak_record(self, record):
        # Can't use append because of cint __get__/__set__ nonsense
        record.spells += [self._imp_spell]

class AsIntendedImpsPatcher(AAsIntendedImpsPatcher,BasalCreatureTweaker):
    _imp_spell = (GPath(bush.game.master_file), 0x02B53F)

class CBash_AsIntendedImpsPatcher(AAsIntendedImpsPatcher, _CreaCTweak):
    _imp_spell = FormID(GPath(bush.game.master_file), 0x02B53F)

#------------------------------------------------------------------------------
class AAsIntendedBoarsPatcher(_AActorTweak):
    """Set all boars to have the Bethesda boar spells that were never
    assigned (discovered by the UOP team, made into a mod by Tejon)."""
    tweak_name = _(u'As Intended: Boars')
    tweak_tip = _(u'Set boars to have the unassigned Bethesda Boar Spells as '
                  u'discovered by the UOP team and made into a mod by Tejon.')
    tweak_key = u'vicious boars!'
    tweak_choices = [(u'1.0', u'1.0')]
    tweak_log_msg = _(u'Boars Tweaked: %(total_changed)d')
    _boar_mod_path = re.compile(u'' r'(boar)\\.', re.I | re.U)
    _boar_part  = re.compile(u'(boar)', re.I | re.U)
    _boar_spell = None # override in implementations

    def wants_record(self, record):
        old_mod_path = self._get_skeleton_path(record)
        if not old_mod_path or not self._boar_mod_path.search(old_mod_path):
            return False
        if not any(self._boar_part.search(bp) for bp in record.bodyParts):
            return False
        return self._boar_spell not in record.spells

    def tweak_record(self, record):
        # Can't use append because of cint __get__/__set__ nonsense
        record.spells += [self._boar_spell]

class AsIntendedBoarsPatcher(AAsIntendedBoarsPatcher,BasalCreatureTweaker):
    _boar_spell = (GPath(bush.game.master_file), 0x02B54E)

class CBash_AsIntendedBoarsPatcher(AAsIntendedBoarsPatcher, _CreaCTweak):
    _boar_spell = FormID(GPath(bush.game.master_file), 0x02B54E)

#------------------------------------------------------------------------------
class ASWALKNPCAnimationPatcher(_AFemaleOnlyTweak):
    """Changes all female NPCs to use Mur Zuk's Sexy Walk."""
    tweak_name = _(u'Sexy Walk for female NPCs')
    tweak_tip = _(u"Changes all female NPCs to use Mur Zuk's Sexy Walk - "
                  u"Requires Mur Zuk's Sexy Walk animation file.")
    tweak_key = u'Mur Zuk SWalk'
    tweak_choices = [(u'1.0', u'1.0')]
    tweak_log_msg = _(u'NPCs Tweaked: %(total_changed)d')

    def tweak_record(self, record):
        # Can't use append because of cint __get__/__set__ nonsense
        record.animations += [u'0sexywalk01.kf']

class SWALKNPCAnimationPatcher(ASWALKNPCAnimationPatcher,
                               BasalNPCTweaker): pass
class CBash_SWALKNPCAnimationPatcher(ASWALKNPCAnimationPatcher,
                                     _NpcCTweak): pass

#------------------------------------------------------------------------------
class ARWALKNPCAnimationPatcher(_AFemaleOnlyTweak):
    """Changes all female NPCs to use Mur Zuk's Real Walk."""
    tweak_name = _(u'Real Walk for female NPCs')
    tweak_tip = _(u"Changes all female NPCs to use Mur Zuk's Real Walk - "
                  u"Requires Mur Zuk's Real Walk animation file.")
    tweak_key = u'Mur Zuk RWalk'
    tweak_choices = [(u'1.0', u'1.0')]
    tweak_log_msg = _(u'NPCs Tweaked: %(total_changed)d')

    def tweak_record(self, record):
        # Can't use append because of cint __get__/__set__ nonsense
        record.animations += [u'0realwalk01.kf']

class RWALKNPCAnimationPatcher(ARWALKNPCAnimationPatcher,
                               BasalNPCTweaker): pass
class CBash_RWALKNPCAnimationPatcher(ARWALKNPCAnimationPatcher,
                                     _NpcCTweak): pass

#------------------------------------------------------------------------------
class AQuietFeetPatcher(_AActorTweak):
    """Removes 'foot' sounds from all/specified creatures - like the mod by
    the same name but works on all modded creatures."""
    tweak_name = _(u'Quiet Feet')
    tweak_tip = _(u"Removes all/some 'foot' sounds from creatures; on some "
                  u'computers can have a significant performance boost.')
    tweak_key = u'silent n sneaky!'
    tweak_choices = [(_(u'All Creature Foot Sounds'), u'all'),
                     (_(u'Only 4 Legged Creature Foot Sounds'), u'partial'),
                     (_(u'Only Mount Foot Sounds'), u'mounts')]
    tweak_log_msg = _(u'Creatures Tweaked: %(total_changed)d')
    # Sound Types: 0 = left foot, 1 = right foot, 2 = left back foot,
    # 3 = right back foot

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

    def tweak_record(self, record):
        record.sounds = self._get_silenced_sounds(record)

class QuietFeetPatcher(AQuietFeetPatcher, BasalCreatureTweaker): pass
class CBash_QuietFeetPatcher(AQuietFeetPatcher, _CreaCTweak): pass

#------------------------------------------------------------------------------
class AIrresponsibleCreaturesPatcher(_AActorTweak):
    """Sets responsibility to 0 for all/specified creatures - like the mod
    by the name of Irresponsible Horses but works on all modded creatures."""
    tweak_name = _(u'Irresponsible Creatures')
    tweak_tip = _(u'Sets responsibility to 0 for all/specified creatures - so '
                  u"they can't report you for crimes.")
    tweak_key = u'whatbadguarddogs'
    tweak_choices = [(_(u'All Creatures'), u'all'),
                     (_(u'Only Horses'), u'mounts')]
    tweak_log_msg = _(u'Creatures Tweaked: %(total_changed)d')

    def wants_record(self, record):
        # Must not be templated (FO3/FNV only), the creature must not be
        # irresponsible already, and if we're in 'only horses' mode, the
        # creature must be a horse
        return (not self._is_templated(record, u'useAIData')
                and record.responsibility != 0
                and (self.choiceValues[self.chosen][0] == u'all'
                     or record.creatureType == 4))

    def tweak_record(self, record):
        record.responsibility = 0

class IrresponsibleCreaturesPatcher(AIrresponsibleCreaturesPatcher,
                                    BasalCreatureTweaker): pass
class CBash_IrresponsibleCreaturesPatcher(AIrresponsibleCreaturesPatcher,
                                          _CreaCTweak): pass

#------------------------------------------------------------------------------
class _AOppositeGenderAnimsPatcher(BasalNPCTweaker):
    """Enables or disables the 'Opposite Gender Anims' flag on all male or
    female NPCs. Similar to the 'Feminine Females' mod, but applies to the
    whole load order."""
    tweak_choices = [(_(u'Always Disable'), u'disable_all'),
                     (_(u'Always Enable'), u'enable_all'),]
    tweak_log_msg = _(u'NPCs Tweaked: %(total_changed)d')
    # Whether this patcher wants female or male NPCs
    _targets_female_npcs = False

    @property
    def oga_target(self):
        return self.choiceValues[self.chosen][0] == u'enable_all'

    def wants_record(self, record):
        # Skip any NPCs that don't match this patcher's target gender
        return (record.flags.female == self._targets_female_npcs
                and record.flags.oppositeGenderAnims != self.oga_target)

    def tweak_record(self, record):
        record.flags.oppositeGenderAnims = self.oga_target

class OppositeGenderAnimsPatcher_Female(_AOppositeGenderAnimsPatcher):
    tweak_name = _(u'Opposite Gender Anims: Female')
    tweak_tip = _(u"Enables or disables the 'Opposite Gender Anims' for all "
                  u"female NPCs. Similar to the 'Feminine Females' mod.")
    tweak_key = u'opposite_gender_anims_female'
    _targets_female_npcs = True

class OppositeGenderAnimsPatcher_Male(_AOppositeGenderAnimsPatcher):
    tweak_name =  _(u'Opposite Gender Anims: Male')
    tweak_tip = _(u"Enables or disables the 'Opposite Gender Anims' for all "
                  u"male NPCs. Similar to the 'Feminine Females' mod.")
    tweak_key = u'opposite_gender_anims_male'

#------------------------------------------------------------------------------
class TweakActors(MultiTweaker):
    """Sets Creature stuff or NPC Skeletons, Animations or other settings to
    better work with mods or avoid bugs."""
    _tweak_classes = [globals()[t] for t in bush.game.actor_tweaks]

class CBash_TweakActors(CBash_MultiTweaker):
    """Sets Creature stuff or NPC Skeletons, Animations or other settings to
    better work with mods or avoid bugs."""
    _tweak_classes = (
        [globals()[u'CBash_' + t] for t in bush.game.actor_tweaks]
        if bush.game.Esp.canCBash else [])
