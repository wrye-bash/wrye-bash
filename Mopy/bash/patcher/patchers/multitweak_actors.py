# -*- coding: utf-8 -*-
#
# GPL License and Copyright Notice ============================================
#  This file is part of Wrye Bash.
#
#  Wrye Bash is free software: you can redistribute it and/or
#  modify it under the terms of the GNU General Public License
#  as published by the Free Software Foundation, either version 3
#  of the License, or (at your option) any later version.
#
#  Wrye Bash is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
#
#  You should have received a copy of the GNU General Public License
#  along with Wrye Bash.  If not, see <https://www.gnu.org/licenses/>.
#
#  Wrye Bash copyright (C) 2005-2009 Wrye, 2010-2021 Wrye Bash Team
#  https://github.com/wrye-bash
#
# =============================================================================

"""This module contains oblivion multitweak item patcher classes that belong
to the Actors Multitweaker - as well as the TweakActors itself."""

import random
import re
# Internal
from .base import MultiTweakItem, MultiTweaker, is_templated
from ... import bass, bush
from ...bolt import GPath
from ...exception import AbstractError

class _AActorTweak(MultiTweakItem):
    """Base for all actor tweaks."""
    @staticmethod
    def _get_skeleton_path(record):
        """Retrieves an actor's skeleton model path from the specified record.
        May return None if the path is not present."""
        try:
            return record.model.modPath
        except AttributeError:
            # Some weird plugins have NPCs with no skeleton assigned to them
            return None

class _ANpcTweak(_AActorTweak):
    """Base for all NPC_ tweaks."""
    tweak_read_classes = b'NPC_',
    _player_fid = (GPath(bush.game.master_file), 0x000007)

class _ACreatureTweak(_AActorTweak):
    """Base for all CREA tweaks."""
    tweak_read_classes = b'CREA',

class _AFemaleOnlyTweak(_ANpcTweak):
    """Provides an implementation of wants_record for female-only tweaks.
    Shared by Sexy and Real Walk tweaks."""
    def wants_record(self, record):
        return record.fid != self._player_fid and record.flags.female

#------------------------------------------------------------------------------
class _ASkeletonTweak(_ANpcTweak):
    """Shared code of MAO/VORB skeleton tweaks."""
    tweak_choices = [(_(u'All NPCs'), 0), (_(u'Only Female NPCs'), 1),
                     (_(u'Only Male NPCs'), 2)]
    tweak_log_msg = _(u'Skeletons Tweaked: %(total_changed)d')

    def _get_target_skeleton(self, record):
        """Returns the skeleton path that we want to change the skeleton of the
        specified record to."""
        raise AbstractError(u'_get_target_skeleton not implemented')

    def wants_record(self, record):
        chosen_gender = self.choiceValues[self.chosen][0]
        if chosen_gender == 1 and not record.flags.female: return False
        elif chosen_gender == 2 and record.flags.female: return False
        return (record.fid != self._player_fid and
                self._get_skeleton_path(record) !=
                self._get_target_skeleton(record))

    def tweak_record(self, record):
        record.model.modPath = self._get_target_skeleton(record)

#------------------------------------------------------------------------------
class MAONPCSkeletonPatcher(_ASkeletonTweak):
    """Changes all NPCs to use the right Mayu's Animation Overhaul Skeleton
    for use with MAO."""
    tweak_name = _(u"Mayu's Animation Overhaul Skeleton Tweaker")
    tweak_tip = _(u'Changes all (modded and vanilla) NPCs to use the MAO '
                  u'skeletons.  Not compatible with VORB.  Note: ONLY use if '
                  u'you have MAO installed.')
    tweak_key = u'MAO Skeleton'
    tweak_log_header = _(u'MAO Skeleton Setter')
    tweak_order = 11 # Run after the vanilla skeleton tweak for consistency
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

#------------------------------------------------------------------------------
class VORB_NPCSkeletonPatcher(_ASkeletonTweak):
    """Changes all NPCs to use the diverse skeleton for different look."""
    tweak_name = _(u"VadersApp's Oblivion Real Bodies Skeleton Tweaker")
    tweak_tip = _(u"Changes all (modded and vanilla) NPCs to use diverse "
                  u"skeletons for different look.  Not compatible with MAO, "
                  u"Requires VadersApp's Oblivion Real Bodies.")
    tweak_key = u'VORB'
    tweak_log_header = _(u"VadersApp's Oblivion Real Bodies")
    _skeleton_dir = u'Characters\\_male'

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
            skeleton_specials = {x.s for x in skel_nifs
                                 if x not in set_skeleton_list}
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
            return u'%s\\%s' % (self._skeleton_dir, special_skel_mesh)
        else:
            random.seed(record.fid[1]) # make it deterministic
            rand_index = random.randint(1, len(skeleton_list)) - 1 ##: choice?
            return u'%s\\%s' % (self._skeleton_dir, skeleton_list[rand_index])

#------------------------------------------------------------------------------
class VanillaNPCSkeletonPatcher(_ASkeletonTweak):
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

#------------------------------------------------------------------------------
class RedguardNPCPatcher(_ANpcTweak):
    """Changes all Redguard NPCs texture symmetry for Better Redguard
    Compatibility."""
    tweak_name = _(u'Redguard FGTS Patcher')
    tweak_tip = _(u'Nulls FGTS of all Redguard NPCs - for compatibility with '
                  u'Better Redguards.')
    tweak_key = u'RedguardFGTSPatcher'
    tweak_log_msg = _(u'Redguard NPCs Tweaked: %(total_changed)d')
    tweak_choices = [(u'1.0', u'1.0')]
    _redguard_fid = (GPath(bush.game.master_file), 0x00000D43)

    def wants_record(self, record):
        # Only affect NPCs with the redguard race
        return (record.race == self.__class__._redguard_fid and
                record.fgts_p != b'\x00' * 200)

    def tweak_record(self, record):
        record.fgts_p = b'\x00' * 200

#------------------------------------------------------------------------------
class NoBloodCreaturesPatcher(_ACreatureTweak):
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

    def tweak_record(self, record):
        record.bloodDecalPath = None
        record.bloodSprayPath = None
        record.flags.noBloodSpray = True
        record.flags.noBloodDecal = True

#------------------------------------------------------------------------------
class AsIntendedImpsPatcher(_ACreatureTweak):
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
    _imp_mod_path = re.compile(r'(imp(?!erial)|gargoyle)\\.', re.I | re.U)
    _imp_part  = re.compile(u'(imp(?!erial)|gargoyle)', re.I | re.U)
    _imp_spell = (GPath(bush.game.master_file), 0x02B53F)

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
        record.spells.append(self._imp_spell)

#------------------------------------------------------------------------------
class AsIntendedBoarsPatcher(_ACreatureTweak):
    """Set all boars to have the Bethesda boar spells that were never
    assigned (discovered by the UOP team, made into a mod by Tejon)."""
    tweak_name = _(u'As Intended: Boars')
    tweak_tip = _(u'Set boars to have the unassigned Bethesda Boar Spells as '
                  u'discovered by the UOP team and made into a mod by Tejon.')
    tweak_key = u'vicious boars!'
    tweak_choices = [(u'1.0', u'1.0')]
    tweak_log_msg = _(u'Boars Tweaked: %(total_changed)d')
    _boar_mod_path = re.compile(r'(boar)\\.', re.I | re.U)
    _boar_part  = re.compile(u'(boar)', re.I | re.U)
    _boar_spell = (GPath(bush.game.master_file), 0x02B54E)

    def wants_record(self, record):
        old_mod_path = self._get_skeleton_path(record)
        if not old_mod_path or not self._boar_mod_path.search(old_mod_path):
            return False
        if not any(self._boar_part.search(bp) for bp in record.bodyParts):
            return False
        return self._boar_spell not in record.spells

    def tweak_record(self, record):
        record.spells.append(self._boar_spell)

#------------------------------------------------------------------------------
class SWALKNPCAnimationPatcher(_AFemaleOnlyTweak):
    """Changes all female NPCs to use Mur Zuk's Sexy Walk."""
    tweak_name = _(u'Sexy Walk For Female NPCs')
    tweak_tip = _(u"Changes all female NPCs to use Mur Zuk's Sexy Walk - "
                  u"Requires Mur Zuk's Sexy Walk animation file.")
    tweak_key = u'Mur Zuk SWalk'
    tweak_choices = [(u'1.0', u'1.0')]
    tweak_log_msg = _(u'NPCs Tweaked: %(total_changed)d')

    ##: wants_record to check if it's not already there?
    def tweak_record(self, record):
        record.animations.append(u'0sexywalk01.kf')

#------------------------------------------------------------------------------
class RWALKNPCAnimationPatcher(_AFemaleOnlyTweak):
    """Changes all female NPCs to use Mur Zuk's Real Walk."""
    tweak_name = _(u'Real Walk For Female NPCs')
    tweak_tip = _(u"Changes all female NPCs to use Mur Zuk's Real Walk - "
                  u"Requires Mur Zuk's Real Walk animation file.")
    tweak_key = u'Mur Zuk RWalk'
    tweak_choices = [(u'1.0', u'1.0')]
    tweak_log_msg = _(u'NPCs Tweaked: %(total_changed)d')

    ##: wants_record to check if it's not already there?
    def tweak_record(self, record):
        record.animations.append(u'0realwalk01.kf')

#------------------------------------------------------------------------------
class QuietFeetPatcher(_ACreatureTweak):
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

    @staticmethod
    def _get_silenced_sounds(record):
        """Returns the sounds of the specified record, with all footstep sound
        silenced."""
        return [s for s in record.sounds if s.type not in (0, 1, 2, 3)]

    def wants_record(self, record):
        # Check if we're templated first (only relevant on FO3/FNV)
        if is_templated(record, u'useModelAnimation'): return False
        chosen_target = self.choiceValues[self.chosen][0]
        if chosen_target == u'partial' and not any(
                s.type in (2, 3) for s in record.sounds):
            return False
        elif chosen_target == u'mounts' and record.creatureType != 4:
            return False
        return record.sounds != self._get_silenced_sounds(record)

    def tweak_record(self, record):
        record.sounds = self._get_silenced_sounds(record)

#------------------------------------------------------------------------------
class IrresponsibleCreaturesPatcher(_ACreatureTweak):
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
        return (not is_templated(record, u'useAIData')
                and record.responsibility != 0
                and (self.choiceValues[self.chosen][0] == u'all'
                     or record.creatureType == 4))

    def tweak_record(self, record):
        record.responsibility = 0

#------------------------------------------------------------------------------
class _AOppositeGenderAnimsPatcher(_ANpcTweak):
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
class TweakActorsPatcher(MultiTweaker):
    """Sets Creature stuff or NPC Skeletons, Animations or other settings to
    better work with mods or avoid bugs."""
    _tweak_classes = {globals()[t] for t in bush.game.actor_tweaks}
