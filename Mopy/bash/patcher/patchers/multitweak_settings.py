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
to the Settings Multitweaker - as well as the tweaker itself."""

from .base import MultiTweakItem, MultiTweaker, CustomChoiceTweak
from ... import bush  # for game

class _ASettingsTweak(MultiTweakItem):
    """Shared code of GLOB and GMST tweaks."""
    tweak_log_msg = u'' # not logged for GMST tweaks
    show_key_for_custom = True

class _AGlobalsTweak(_ASettingsTweak, CustomChoiceTweak):
    """Sets a global to specified value."""
    tweak_read_classes = b'GLOB',

    @property
    def chosen_value(self):
        # Globals are always stored as floats, regardless of what the CS says
        return float(self.choiceValues[self.chosen][0])

    def wants_record(self, record):
        return (record.eid and # skip missing and empty EDID
                record.eid.lower() == self.tweak_key and
                record.global_value != self.chosen_value)

    def tweak_record(self, record):
        record.global_value = self.chosen_value

    def tweak_log(self, log, count):
        log(u'* ' + _(u'%s set to: %4.2f') % (
            self.tweak_name, self.chosen_value))

#------------------------------------------------------------------------------
class GlobalsTweak_Timescale(_AGlobalsTweak):
    tweak_name = _(u'World: Timescale')
    tweak_tip = _(u'Timescale will be set to:')
    tweak_key = u'timescale'
    tweak_choices = [(u'1',         1),
                     (u'8',         8),
                     (u'10',        10),
                     (u'12',        12),
                     (u'20',        20),
                     (u'24',        24),
                     (u'30',        30),
                     (u'40',        40)]
    default_choice = u'30'

class GlobalsTweak_Timescale_Tes5(GlobalsTweak_Timescale):
    default_choice = u'20'

#------------------------------------------------------------------------------
class GlobalsTweak_ThievesGuild_QuestStealingPenalty(_AGlobalsTweak):
    tweak_name = _(u'Thieves Guild: Quest Stealing Penalty')
    tweak_tip = _(u'The penalty (in Septims) for stealing while doing a '
                  u'Thieves Guild job:')
    tweak_key = u'tgpricesteal'
    tweak_choices = [(u'100',     100),
                     (u'150',     150),
                     (u'200',     200),
                     (u'300',     300),
                     (u'400',     400)]
    default_choice = u'200'

#------------------------------------------------------------------------------
class GlobalsTweak_ThievesGuild_QuestKillingPenalty(_AGlobalsTweak):
    tweak_name = _(u'Thieves Guild: Quest Killing Penalty')
    tweak_tip = _(u'The penalty (in Septims) for killing while doing a '
                  u'Thieves Guild job:')
    tweak_key = u'tgpriceperkill'
    tweak_choices = [(u'250',     250),
                     (u'500',     500),
                     (u'1000',   1000),
                     (u'1500',   1500),
                     (u'2000',   2000)]
    default_choice = u'1000'

#------------------------------------------------------------------------------
class GlobalsTweak_ThievesGuild_QuestAttackingPenalty(_AGlobalsTweak):
    tweak_name = _(u'Thieves Guild: Quest Attacking Penalty')
    tweak_tip = _(u'The penalty (in Septims) for attacking while doing a '
                  u'Thieves Guild job:')
    tweak_key = u'tgpriceattack'
    tweak_choices = [(u'100',     100),
                     (u'250',     250),
                     (u'500',     500),
                     (u'750',     750),
                     (u'1000',   1000)]
    default_choice = u'500'

#------------------------------------------------------------------------------
class GlobalsTweak_Crime_ForceJail(_AGlobalsTweak):
    tweak_name = _(u'Crime: Force Jail')
    tweak_tip = _(u'The amount of Bounty at which a jail sentence is '
                  u'mandatory')
    tweak_key = u'crimeforcejail'
    tweak_choices = [(u'1000',   1000),
                     (u'2500',   2500),
                     (u'5000',   5000),
                     (u'7500',   7500),
                     (u'10000', 10000)]
    default_choice = u'5000'

#------------------------------------------------------------------------------
class _AGmstTweak(_ASettingsTweak):
    """Sets a GMST to specified value."""
    tweak_read_classes = b'GMST',

    @property
    def chosen_eids(self):
        return ((self.tweak_key,), self.tweak_key)[isinstance(self.tweak_key,
                                                              tuple)]

    @property
    def chosen_values(self): return self.choiceValues[self.chosen]

    @property
    def eid_was_itpo(self):
        try:
            return self._eid_was_itpo
        except AttributeError:
            self._eid_was_itpo = {e.lower(): False for e in self.chosen_eids}
            return self._eid_was_itpo

    def _find_chosen_value(self, wanted_eid):
        """Returns the value the user chose for the game setting with the
        specified editor ID. Note that wanted_eid must be lower-case!"""
        for test_eid, test_val in zip(self.chosen_eids, self.chosen_values):
            if wanted_eid == test_eid.lower():
                return test_val
        return None

    def _find_original_eid(self, lower_eid):
        """We need to find the original case of the EDID, otherwise getFMSTFid
        blows - plus the dumped record will look nicer :)."""
        for orig_eid in self.chosen_eids:
            if lower_eid == orig_eid.lower():
                return orig_eid
        return lower_eid # fallback, should never happen

    def validate_values(self, chosen_values):
        if bush.game.fsName == u'Oblivion': ##: add a comment why TES4 only!
            for target_value in chosen_values:
                if target_value < 0:
                    return _(u"Oblivion GMST values can't be negative")
        for target_eid, target_value in zip(self.chosen_eids, chosen_values):
            if target_eid.startswith(u'f') and not isinstance(
                    target_value, float):
                    return _(u"The value chosen for GMST '%s' must be a "
                             u'float, but is currently of type %s (%s).') % (
                        target_eid, type(target_value).__name__, target_value)
        return super(_AGmstTweak, self).validate_values(chosen_values)

    def wants_record(self, record):
        if record.fid[0] not in bush.game.bethDataFiles:
            return False # Avoid adding new masters just for a game setting
        rec_eid = record.eid.lower()
        if rec_eid not in self.eid_was_itpo: return False # not needed
        target_val = self._find_chosen_value(rec_eid)
        ret_val = record.value != target_val
        # Remember whether the last entry was ITPO or not
        self.eid_was_itpo[rec_eid] = not ret_val
        return ret_val

    def tweak_record(self, record):
        rec_eid = record.eid.lower()
        # We don't need to create a GMST for this EDID anymore
        self.eid_was_itpo[rec_eid] = True
        record.value = self._find_chosen_value(rec_eid)

    def tweak_log(self, log, count): # count is ignored here
        if len(self.choiceLabels) > 1:
            chosen_label = self.choiceLabels[self.chosen]
            if chosen_label == self.custom_choice:
                if isinstance(self.chosen_values[0], str):
                    log(u'* %s: %s %s' % (self.tweak_name, chosen_label,
                                          self.chosen_values[0]))
                else:
                    log(u'* %s: %s %4.2f' % (self.tweak_name, chosen_label,
                                             self.chosen_values[0]))
            else:
                log(u'* %s: %s' % (self.tweak_name, chosen_label))
        else:
            log(u'* ' + self.tweak_name)

    def finish_tweaking(self, patch_file):
        # Create new records for any remaining EDIDs
        for remaining_eid, was_itpo in self.eid_was_itpo.items():
            if not was_itpo:
                patch_file.new_gmst(self._find_original_eid(remaining_eid),
                    self._find_chosen_value(remaining_eid))

class _AGmstCCTweak(_AGmstTweak, CustomChoiceTweak):
    """Variant of _AGmstTweak that also includes CustomChoiceTweak."""

class _AGmstCCSecondsTweak(_AGmstTweak):
    """Variant of _AGmstTweak to factor out 'in seconds' custom tweaks."""
    custom_choice = _(u'Custom (in seconds)')

class _AGmstCCUnitsTweak(_AGmstTweak):
    """Variant of _AGmstTweak to factor out 'in units' custom tweaks."""
    custom_choice = _(u'Custom (in units)')

class _AMsgTweak(_AGmstCCTweak):
    """Base class for GMST tweaks in the Msg: category."""
    tweak_choices = [(_(u'None'),           u' '),
                     (u'.',                 u'.'),
                     (_(u'Hmm...'), _(u'Hmm...'))]
    default_choice = _(u'None')

class _AAllowTweak(_AGmstTweak):
    """Base class for GMST tweaks that have allow/disallow choices."""
    tweak_choices = [(_(u'Allow'),    1),
                     (_(u'Disallow'), 0)]
    default_choice = _(u'Disallow')

class _ALeveledDiffTweak(_AGmstCCTweak):
    """Base class for Level Difference tweaks."""
    tweak_choices = [(u'1',               1),
                     (u'5',               5),
                     (u'8',               8),
                     (u'10',             10),
                     (u'20',             20),
                     (_(u'Unlimited'), 9999)]
    default_choice = u'8'

class _ASoulTrapTweak(_AGmstCCTweak):
    """Base class for Soul Trap tweaks."""
    tweak_choices = [(u'4',   4),
                     (u'16', 16),
                     (u'28', 28),
                     (u'38', 38)]

class _ATauntTweak(_AGmstTweak):
    """Base class for tweaks that change the chance of actors taunting or
    speaking when certain events (e.g. being hit) occur."""
    tweak_choices = [(_(u'0% (Disabled)'), 0.0),
                     (u'1%',              0.01),
                     (u'20%',              0.2),
                     (u'25%',             0.25),
                     (u'50%',              0.5),
                     (u'75%',             0.75),
                     (_(u'100% (Always)'), 1.0)]
    custom_choice = _(u'Custom (Max: 1.0)')

#------------------------------------------------------------------------------
class GmstTweak_Arrow_LitterCount(_AGmstCCTweak):
    tweak_name = _(u'Arrow: Litter Count')
    tweak_tip = _(u'Maximum number of spent arrows allowed in cell.')
    tweak_key = (u'iArrowMaxRefCount',)
    tweak_choices = [(u'15',   15),
                     (u'25',   25),
                     (u'35',   35),
                     (u'50',   50),
                     (u'100', 100),
                     (u'500', 500)]
    default_choice = u'15'

#------------------------------------------------------------------------------
class GmstTweak_Arrow_LitterTime(_AGmstCCSecondsTweak):
    tweak_name = _(u'Arrow: Litter Time')
    tweak_tip = _(u'Time before spent arrows fade away from cells and actors.')
    tweak_key = (u'fArrowAgeMax',)
    tweak_choices = [(_(u'1 Minute'),     60.0),
                     (_(u'1.5 Minutes'),  90.0),
                     (_(u'2 Minutes'),   120.0),
                     (_(u'3 Minutes'),   180.0),
                     (_(u'5 Minutes'),   300.0),
                     (_(u'10 Minutes'),  600.0),
                     (_(u'30 Minutes'), 1800.0),
                     (_(u'1 Hour'),     3600.0)]
    default_choice = _(u'1.5 Minutes')

#------------------------------------------------------------------------------
class GmstTweak_Arrow_RecoveryFromActor(_AGmstCCTweak):
    tweak_name = _(u'Arrow: Recovery From Actor')
    tweak_tip = _(u'Chance that an arrow shot into an actor can be recovered.')
    tweak_key = (u'iArrowInventoryChance',)
    tweak_choices = [(u'33%',   33),
                     (u'50%',   50),
                     (u'60%',   60),
                     (u'70%',   70),
                     (u'80%',   80),
                     (u'90%',   90),
                     (u'100%', 100)]
    default_choice = u'50%'

class GmstTweak_Arrow_RecoveryFromActor_Tes5(
    GmstTweak_Arrow_RecoveryFromActor):
    default_choice = u'33%'

#------------------------------------------------------------------------------
class GmstTweak_Arrow_Speed(_AGmstCCTweak):
    tweak_name = _(u'Arrow: Speed')
    tweak_tip = _(u'Speed of a full power arrow.')
    tweak_key = (u'fArrowSpeedMult',)
    tweak_choices = [(u'x1.0', 1500.0),
                     (u'x1.2', 1800.0),
                     (u'x1.4', 2100.0),
                     (u'x1.6', 2400.0),
                     (u'x1.8', 2700.0),
                     (u'x2.0', 3000.0),
                     (u'x2.2', 3300.0),
                     (u'x2.4', 3600.0),
                     (u'x2.6', 3900.0),
                     (u'x2.8', 4200.0),
                     (u'x3.0', 4500.0)]
    default_choice = u'x1.0'

#------------------------------------------------------------------------------
class GmstTweak_Camera_ChaseTightness(_AGmstCCTweak):
    tweak_name = _(u'Camera: Chase Tightness')
    tweak_tip = _(u'Tightness of chase camera to player turning.')
    tweak_key = (u'fChase3rdPersonVanityXYMult', u'fChase3rdPersonXYMult')
    tweak_choices = [(u'x1.5',                              6.0, 6.0),
                     (u'x2.0',                              8.0, 8.0),
                     (u'x3.0',                            12.0, 12.0),
                     (u'x5.0',                            20.0, 20.0),
                     (_(u'ChaseCameraMod.esp (x 24.75)'), 99.0, 99.0)]

#------------------------------------------------------------------------------
class GmstTweak_Camera_ChaseDistance(_AGmstCCTweak):
    tweak_name = _(u'Camera: Chase Distance')
    tweak_tip = _(u'Distance camera can be moved away from PC using mouse '
                  u'wheel.')
    tweak_key = (u'fVanityModeWheelMax', u'fChase3rdPersonZUnitsPerSecond',
                 u'fVanityModeWheelMult')
    tweak_choices = [(u'x1.5', 900.0, 450.0, 0.15),
                     (u'x2',   1200.0, 600.0, 0.2),
                     (u'x3',   1800.0, 900.0, 0.3),
                     (u'x5',  3000.0, 1000.0, 0.3),
                     (u'x10', 6000.0, 2000.0, 0.3)]

class GmstTweak_Camera_ChaseDistance_Fo3(GmstTweak_Camera_ChaseDistance):
    tweak_key = (u'fVanityModeWheelMax', u'fChase3rdPersonZUnitsPerSecond')
    tweak_choices = [(u'x1.5', 900.0, 1200.0),
                     (u'x2',  1200.0, 1600.0),
                     (u'x3',  1800.0, 2400.0),
                     (u'x5',  3000.0, 4000.0),
                     (u'x10', 6000.0, 5000.0)]

#------------------------------------------------------------------------------
class GmstTweak_Magic_ChameleonRefraction(_AGmstCCTweak):
    tweak_name = _(u'Magic: Chameleon Refraction')
    tweak_tip = _(u'Chameleon with transparency instead of refraction effect.')
    tweak_key = (u'fChameleonMinRefraction', u'fChameleonMaxRefraction')
    tweak_choices = [(_(u'Zero'),    0.0, 0.0),
                     (_(u'Normal'), 0.01, 1.0),
                     (_(u'Full'),    1.0, 1.0)]
    default_choice = _(u'Normal')

#------------------------------------------------------------------------------
class GmstTweak_Compass_Disable(_AGmstTweak):
    tweak_name = _(u'Compass: Disable')
    tweak_tip = _(u'No quest and/or points of interest markers on compass.')
    tweak_key = (u'iMapMarkerRevealDistance',)
    tweak_choices = [(_(u'Quests'),          1803),
                     (_(u'POIs'),            1802),
                     (_(u'Quests and POIs'), 1801)]

#------------------------------------------------------------------------------
class GmstTweak_Compass_RecognitionDistance(_AGmstCCTweak):
    tweak_name = _(u'Compass: Recognition Distance')
    tweak_tip = _(u'Distance at which markers (dungeons, towns etc.) begin to '
                  u'show on the compass.')
    tweak_key = (u'iMapMarkerVisibleDistance',)
    tweak_choices = [(_(u'75% Shorter'),  3125),
                     (_(u'50% Shorter'),  6250),
                     (_(u'25% Shorter'),  9375),
                     (_(u'Default'),     12500),
                     (_(u'25% Further'), 15625),
                     (_(u'50% Further'), 18750),
                     (_(u'75% Further'), 21875)]
    default_choice = _(u'Default')

#------------------------------------------------------------------------------
class GmstTweak_Actor_UnconsciousnessDuration(_AGmstCCSecondsTweak):
    tweak_name = _(u'Actor: Unconsciousness Duration')
    tweak_tip = _(u'Time which essential NPCs stay unconscious.')
    tweak_key = (u'fEssentialDeathTime',)
    tweak_choices = [(_(u'10 Seconds'),    10.0),
                     (_(u'20 Seconds'),    20.0),
                     (_(u'30 Seconds'),    30.0),
                     (_(u'1 Minute'),      60.0),
                     (_(u'1 1/2 Minutes'), 90.0),
                     (_(u'2 Minutes'),    120.0),
                     (_(u'3 Minutes'),    180.0),
                     (_(u'5 Minutes'),    300.0)]
    default_choice = _(u'10 Seconds')

#------------------------------------------------------------------------------
class GmstTweak_Movement_FatigueFromRunningEncumbrance(_AGmstCCTweak):
    tweak_name = _(u'Movement: Fatigue From Running/Encumbrance')
    tweak_tip = _(u'Fatigue cost of running and encumbrance.')
    tweak_key = (u'fFatigueRunBase', u'fFatigueRunMult')
    tweak_choices = [(u'x1.5', 12.0, 6.0),
                     (u'x2',   16.0, 8.0),
                     (u'x3',  24.0, 12.0),
                     (u'x4',  32.0, 16.0),
                     (u'x5',  40.0, 20.0)]

#------------------------------------------------------------------------------
class GmstTweak_Player_HorseTurningSpeed(_AGmstTweak):
    tweak_name = _(u'Player: Horse Turning Speed')
    tweak_tip = _(u'Speed at which your horse can turn.')
    tweak_key = (u'iHorseTurnDegreesPerSecond',
                 u'iHorseTurnDegreesRampUpPerSecond')
    tweak_choices = [(_(u'Default'), 45, 80),
                     (u'x1.5',      68, 120),
                     (u'x2',        90, 160),
                     (u'x3',       135, 240)]
    default_choice = _(u'Default')
    custom_choice = _(u'Custom (Turning and ramp-up speeds)')

#------------------------------------------------------------------------------
class GmstTweak_Camera_PCDeathTime(_AGmstCCTweak):
    tweak_name = _(u'Camera: PC Death Time')
    tweak_tip = _(u"Time after player's death before the last save is "
                  u"loaded/the reload menu appears.")
    tweak_key = (u'fPlayerDeathReloadTime',)
    tweak_choices = [(_(u'15 Seconds'),     15.0),
                     (_(u'30 Seconds'),     30.0),
                     (_(u'1 Minute'),       60.0),
                     (_(u'5 Minute'),      300.0),
                     (_(u'Unlimited'), 9999999.0)]

#------------------------------------------------------------------------------
class GmstTweak_World_CellRespawnTime(_AGmstTweak):
    tweak_name = _(u'World: Cell Respawn Time')
    tweak_tip = _(u'Time before unvisited cells respawn. Longer times '
                  u'increase save sizes.')
    tweak_key = (u'iHoursToRespawnCell',)
    tweak_choices = [(_(u'1 Day'),      24),
                     (_(u'3 Days'),     72),
                     (_(u'5 Days'),    120),
                     (_(u'10 Days'),   240),
                     (_(u'20 Days'),   480),
                     (_(u'1 Month'),   720),
                     (_(u'6 Months'), 4368),
                     (_(u'1 Year'),   8760)]
    default_choice = _(u'3 Days')
    custom_choice = _(u'Custom (in hours)')

class GmstTweak_World_CellRespawnTime_Tes5(GmstTweak_World_CellRespawnTime):
    default_choice = _(u'10 Days')

#------------------------------------------------------------------------------
class GmstTweak_Combat_RechargeWeapons(_AAllowTweak):
    tweak_name = _(u'Combat: Recharge Weapons')
    tweak_tip = _(u'Allow recharging weapons during combat.')
    tweak_key = (u'iAllowRechargeDuringCombat',)
    default_choice = _(u'Allow')

#------------------------------------------------------------------------------
class GmstTweak_Magic_BoltSpeed(_AGmstCCTweak):
    tweak_name = _(u'Magic: Bolt Speed')
    tweak_tip = _(u'Speed of magic bolt/projectile.')
    tweak_key = (u'fMagicProjectileBaseSpeed',)
    tweak_choices = [(u'x1.2', 1200.0),
                     (u'x1.4', 1400.0),
                     (u'x1.6', 1600.0),
                     (u'x1.8', 1800.0),
                     (u'x2.0', 2000.0),
                     (u'x2.2', 2200.0),
                     (u'x2.4', 2400.0),
                     (u'x2.6', 2600.0),
                     (u'x2.8', 2800.0),
                     (u'x3.0', 3000.0)]

#------------------------------------------------------------------------------
class GmstTweak_Msg_EquipMiscItem(_AMsgTweak):
    tweak_name = _(u'Msg: Equip Misc. Item')
    tweak_tip = _(u'Message upon equipping misc. item.')
    tweak_key = (u'sCantEquipGeneric',)

#------------------------------------------------------------------------------
class GmstTweak_Msg_AutoSaving(_AMsgTweak):
    tweak_name = _(u'Msg: Auto Saving')
    tweak_tip = _(u'Message upon auto saving.')
    tweak_key = (u'sAutoSaving',)

#------------------------------------------------------------------------------
class GmstTweak_Msg_HarvestFailure(_AMsgTweak):
    tweak_name = _(u'Msg: Harvest Failure')
    tweak_tip = _(u'Message upon failure at harvesting flora.')
    tweak_key = (u'sFloraFailureMessage',)

#------------------------------------------------------------------------------
class GmstTweak_Msg_HarvestSuccess(_AMsgTweak):
    tweak_name = _(u'Msg: Harvest Success')
    tweak_tip = _(u'Message upon success at harvesting flora.')
    tweak_key = (u'sFloraSuccessMessage',)

#------------------------------------------------------------------------------
class GmstTweak_Msg_QuickSave(_AMsgTweak):
    tweak_name = _(u'Msg: Quick Save')
    tweak_tip = _(u'Message upon quick saving.')
    tweak_key = (u'sQuickSaving',)

#------------------------------------------------------------------------------
class GmstTweak_Msg_HorseStabled(_AMsgTweak):
    tweak_name = _(u'Msg: Horse Stabled')
    tweak_tip = _(u'Message upon fast traveling with a horse to a city.')
    tweak_key = (u'sFastTravelHorseatGate',)

#------------------------------------------------------------------------------
class GmstTweak_Msg_NoFastTravel(_AMsgTweak):
    tweak_name = _(u'Msg: No Fast Travel')
    tweak_tip = _(u'Message when attempting to fast travel when fast travel '
                  u'is unavailable due to location.')
    tweak_key = (u'sNoFastTravelScriptBlock',)

#------------------------------------------------------------------------------
class GmstTweak_Msg_LoadingArea(_AMsgTweak):
    tweak_name = _(u'Msg: Loading Area')
    tweak_tip = _(u'Message when background loading area.')
    tweak_key = (u'sLoadingArea',)

#------------------------------------------------------------------------------
class GmstTweak_Msg_QuickLoad(_AMsgTweak):
    tweak_name = _(u'Msg: Quick Load')
    tweak_tip = _(u'Message when quick loading.')
    tweak_key = (u'sQuickLoading',)

#------------------------------------------------------------------------------
class GmstTweak_Msg_NotEnoughCharge(_AMsgTweak):
    tweak_name = _(u'Msg: Not Enough Charge')
    tweak_tip = _(u'Message when enchanted item is out of charge.')
    tweak_key = (u'sNoCharge',)

class GmstTweak_Msg_NotEnoughCharge_Tes5(GmstTweak_Msg_NotEnoughCharge):
    tweak_key = (u'sEnchantInsufficientCharge',)

#------------------------------------------------------------------------------
class GmstTweak_CostMultiplier_Repair(_AGmstCCTweak):
    tweak_name = _(u'Cost Multiplier: Repair')
    tweak_tip = _(u'Cost factor for repairing items.')
    tweak_key = (u'fRepairCostMult',)
    tweak_choices = [(u'0.1', 0.1),
                     (u'0.2', 0.2),
                     (u'0.3', 0.3),
                     (u'0.4', 0.4),
                     (u'0.5', 0.5),
                     (u'0.6', 0.6),
                     (u'0.7', 0.7),
                     (u'0.8', 0.8),
                     (u'0.9', 0.9),
                     (u'1.0', 1.0)]
    default_choice = u'0.9'

class GmstTweak_CostMultiplier_Repair_Fo3(GmstTweak_CostMultiplier_Repair):
    tweak_key = (u'fItemRepairCostMult',)
    tweak_choices = [(u'1.0',   1.0),
                     (u'1.25', 1.25),
                     (u'1.5',   1.5),
                     (u'1.75', 1.75),
                     (u'2.0',   2.0),
                     (u'2.5',   2.5),
                     (u'3.0',   3.0)]
    default_choice = u'2.0'

#------------------------------------------------------------------------------
class GmstTweak_Actor_GreetingDistance(_AGmstCCTweak):
    tweak_name = _(u'Actor: Greeting Distance')
    tweak_tip = _(u'Distance (in units) at which NPCs will greet the player.')
    tweak_key = (u'fAIMinGreetingDistance',)
    tweak_choices = [(u'50',   50.0),
                     (u'100', 100.0),
                     (u'125', 125.0),
                     (u'150', 150.0),
                     (u'200', 200.0),
                     (u'300', 300.0)]
    default_choice = u'150'

#------------------------------------------------------------------------------
class GmstTweak_CostMultiplier_Recharge(_AGmstCCTweak):
    tweak_name = _(u'Cost Multiplier: Recharge')
    tweak_tip = _(u'Cost factor for recharging items.')
    tweak_key = (u'fRechargeGoldMult',)
    tweak_choices = [(u'0.1', 0.1),
                     (u'0.2', 0.2),
                     (u'0.3', 0.3),
                     (u'0.5', 0.5),
                     (u'0.7', 0.7),
                     (u'1.0', 1.0),
                     (u'1.5', 1.5),
                     (u'2.0', 2.0)]
    default_choice = u'2.0'

#------------------------------------------------------------------------------
class GmstTweak_MasterOfMercantileExtraGoldAmount(_AGmstCCTweak):
    tweak_name = _(u'Master Of Mercantile Extra Gold Amount')
    tweak_tip = _(u'How much more barter gold all merchants have for a master '
                  u'of mercantile.')
    tweak_key = (u'iPerkExtraBarterGoldMaster',)
    tweak_choices = [(u'300',   300),
                     (u'400',   400),
                     (u'500',   500),
                     (u'600',   600),
                     (u'800',   800),
                     (u'1000', 1000)]
    default_choice = u'500'

#------------------------------------------------------------------------------
class GmstTweak_Combat_MaxActors(_AGmstCCTweak):
    tweak_name = _(u'Combat: Max Actors')
    tweak_tip = _(u'Maximum number of actors that can actively be in combat '
                  u'with the player.')
    tweak_key = (u'iNumberActorsInCombatPlayer',)
    tweak_choices = [(u'10', 10),
                     (u'15', 15),
                     (u'20', 20),
                     (u'30', 30),
                     (u'40', 40),
                     (u'50', 50),
                     (u'80', 80)]
    default_choice = u'10'

class GmstTweak_Combat_MaxActors_Tes5(GmstTweak_Combat_MaxActors):
    default_choice = u'20'

#------------------------------------------------------------------------------
class GmstTweak_Crime_AlarmDistance(_AGmstCCTweak):
    tweak_name = _(u'Crime: Alarm Distance')
    tweak_tip = _(u'Distance from player that NPCs (guards) will be alerted '
                  u'of a crime.')
    tweak_key = (u'iCrimeAlarmRecDistance',)
    tweak_choices = [(u'8000', 8000),
                     (u'6000', 6000),
                     (u'4000', 4000),
                     (u'3000', 3000),
                     (u'2000', 2000),
                     (u'1000', 1000),
                     (u'500',   500)]
    default_choice = u'4000'

#------------------------------------------------------------------------------
class GmstTweak_Crime_PrisonDurationModifier(_AGmstCCTweak):
    tweak_name = _(u'Crime: Prison Duration Modifier')
    tweak_tip = _(u'Days in prison is your bounty divided by this number.')
    tweak_key = (u'iCrimeDaysInPrisonMod',)
    tweak_choices = [(u'50',   50),
                     (u'60',   60),
                     (u'70',   70),
                     (u'80',   80),
                     (u'90',   90),
                     (u'100', 100)]
    default_choice = u'100'

#------------------------------------------------------------------------------
class GmstTweak_CostMultiplier_Enchantment(_AGmstCCTweak):
    tweak_name = _(u'Cost Multiplier: Enchantment')
    tweak_tip = _(u'Cost factor for enchanting items.')
    tweak_key = (u'fEnchantmentGoldMult',)
    tweak_choices = [(u'10',                    10.0),
                     (u'20',                    20.0),
                     (u'30',                    30.0),
                     (u'50',                    50.0),
                     (u'70',                    70.0),
                     (u'90',                    90.0),
                     (_(u'120 (OOO default)'), 120.0),
                     (u'150',                  150.0)]
    default_choice = u'10'

#------------------------------------------------------------------------------
class GmstTweak_CostMultiplier_SpellMaking(_AGmstCCTweak):
    tweak_name = _(u'Cost Multiplier: Spell Making')
    tweak_tip = _(u'Cost factor for making spells.')
    tweak_key = (u'fSpellmakingGoldMult',)
    tweak_choices = [(u'3',   3.0),
                     (u'5',   5.0),
                     (u'8',   8.0),
                     (u'10', 10.0),
                     (u'15', 15.0)]
    default_choice = u'3'

#------------------------------------------------------------------------------
class GmstTweak_AI_MaxActiveActors(_AGmstCCTweak):
    tweak_name = _(u'AI: Max Active Actors')
    tweak_tip = _(u'Maximum actors whose AI can be active. Must be higher '
                  u'than Combat: Max Actors')
    tweak_key = (u'iAINumberActorsComplexScene',)
    tweak_choices = [(u'20',                 20),
                     (u'25',                 25),
                     (u'30',                 30),
                     (u'35',                 35),
                     (_(u'MMM Default: 40'), 40),
                     (u'50',                 50),
                     (u'60',                 60),
                     (u'100',               100)]
    default_choice = u'25'

class GmstTweak_AI_MaxActiveActors_Tes5(GmstTweak_AI_MaxActiveActors):
    default_choice = u'20'

#------------------------------------------------------------------------------
class GmstTweak_Magic_MaxPlayerSummons(_AGmstCCTweak):
    tweak_name = _(u'Magic: Max Player Summons')
    tweak_tip = _(u'Maximum number of creatures the player can summon.')
    tweak_key = (u'iMaxPlayerSummonedCreatures',)
    tweak_choices = [(u'1',   1),
                     (u'3',   3),
                     (u'5',   5),
                     (u'8',   8),
                     (u'10', 10)]
    default_choice = u'1'

#------------------------------------------------------------------------------
class GmstTweak_Combat_MaxAllyHits(_AGmstCCTweak):
    tweak_name = _(u'Combat: Max Ally Hits')
    tweak_tip = _(u'Maximum number of hits on an ally allowed in combat '
                  u'before the ally will attack the hitting character.')
    tweak_key = (u'iAllyHitAllowed',)
    tweak_choices = [(u'0',   0),
                     (u'3',   3),
                     (u'5',   5),
                     (u'8',   8),
                     (u'10', 10),
                     (u'15', 15)]
    default_choice = u'5'

class GmstTweak_Combat_MaxAllyHits_Tes5(GmstTweak_Combat_MaxAllyHits):
    tweak_tip = _(u'Number of hits allowed by allies out of combat before '
                  u'attacking the player.')
    tweak_key = (u'iAllyHitNonCombatAllowed',)
    default_choice = u'3'

#------------------------------------------------------------------------------
class GmstTweak_Magic_MaxNPCSummons(_AGmstCCTweak):
    tweak_name = _(u'Magic: Max NPC Summons')
    tweak_tip = _(u'Maximum number of creatures that each NPC can summon')
    tweak_key = (u'iAICombatMaxAllySummonCount',)
    tweak_choices = [(u'1',   1),
                     (u'3',   3),
                     (u'5',   5),
                     (u'8',   8),
                     (u'10', 10),
                     (u'15', 15)]
    default_choice = u'3'

#------------------------------------------------------------------------------
class GmstTweak_Bounty_Assault(_AGmstCCTweak):
    tweak_name = _(u'Bounty: Assault')
    tweak_tip = _(u"Bounty for attacking a 'good' npc.")
    tweak_key = (u'iCrimeGoldAttackMin',)
    tweak_choices = [(u'40',   40),
                     (u'100', 100),
                     (u'200', 200),
                     (u'300', 300),
                     (u'400', 400),
                     (u'500', 500),
                     (u'650', 650),
                     (u'800', 800)]
    default_choice = u'500'

class GmstTweak_Bounty_Assault_Tes5(GmstTweak_Bounty_Assault):
    tweak_key = (u'iCrimeGoldAttack',)
    default_choice = u'40'

#------------------------------------------------------------------------------
class GmstTweak_Bounty_HorseTheft(_AGmstCCTweak):
    tweak_name = _(u'Bounty: Horse Theft')
    tweak_tip = _(u'Bounty for horse theft.')
    tweak_key = (u'iCrimeGoldStealHorse',)
    tweak_choices = [(u'10',   10),
                     (u'25',   25),
                     (u'50',   50),
                     (u'100', 100),
                     (u'200', 200),
                     (u'250', 250),
                     (u'300', 300),
                     (u'450', 450)]
    default_choice = u'250'

class GmstTweak_Bounty_HorseTheft_Tes5(GmstTweak_Bounty_HorseTheft):
    default_choice = u'100'

#------------------------------------------------------------------------------
class GmstTweak_Bounty_Theft(_AGmstCCTweak):
    tweak_name = _(u'Bounty: Theft')
    tweak_tip = _(u'Bounty for stealing, as fraction of item value.')
    tweak_key = (u'fCrimeGoldSteal',)
    tweak_choices = [(u'1/4', 0.25),
                     (u'1/2',  0.5),
                     (u'3/4', 0.75),
                     (u'1',    1.0)]
    default_choice = u'1/2'

#------------------------------------------------------------------------------
class GmstTweak_Combat_Alchemy(_AAllowTweak):
    tweak_name = _(u'Combat: Alchemy')
    tweak_tip = _(u'Allow alchemy during combat.')
    tweak_key = (u'iAllowAlchemyDuringCombat',)

#------------------------------------------------------------------------------
class GmstTweak_Combat_Repair(_AAllowTweak):
    tweak_name = _(u'Combat: Repair')
    tweak_tip = _(u'Allow repairing armor/weapons during combat.')
    tweak_key = (u'iAllowRepairDuringCombat',)

#------------------------------------------------------------------------------
class GmstTweak_Actor_MaxCompanions(_AGmstCCTweak):
    tweak_name = _(u'Actor: Max Companions')
    tweak_tip = _(u'Maximum number of actors following the player.')
    tweak_key = (u'iNumberActorsAllowedToFollowPlayer',)
    tweak_choices = [(u'2',   2),
                     (u'4',   4),
                     (u'6',   6),
                     (u'8',   8),
                     (u'10', 10)]
    default_choice = u'6'

#------------------------------------------------------------------------------
class GmstTweak_Actor_TrainingLimit(_AGmstCCTweak):
    tweak_name = _(u'Actor: Training Limit')
    tweak_tip = _(u'Maximum number of Training allowed by trainers.')
    tweak_key = (u'iTrainingSkills',)
    tweak_choices = [(u'1',               1),
                     (u'5',               5),
                     (u'8',               8),
                     (u'10',             10),
                     (u'20',             20),
                     (_(u'Unlimited'), 9999)]
    default_choice = u'5'

class GmstTweak_Actor_TrainingLimit_Tes5(GmstTweak_Actor_TrainingLimit):
    tweak_key = (u'iTrainingNumAllowedPerLevel',)

#------------------------------------------------------------------------------
class GmstTweak_Combat_MaximumArmorRating(_AGmstCCTweak):
    tweak_name = _(u'Combat: Maximum Armor Rating')
    tweak_tip = _(u'The Maximum amount of protection you will get from armor.')
    tweak_key = (u'fMaxArmorRating',)
    tweak_choices = [(u'50',   50.0),
                     (u'75',   75.0),
                     (u'85',   85.0),
                     (u'90',   90.0),
                     (u'95',   95.0),
                     (u'100', 100.0)]
    default_choice = u'85'

class GmstTweak_Combat_MaximumArmorRating_Tes5(
    GmstTweak_Combat_MaximumArmorRating):
    default_choice = u'90'

#------------------------------------------------------------------------------
class GmstTweak_Warning_InteriorDistanceToHostiles(_AGmstCCUnitsTweak):
    tweak_name = _(u'Warning: Interior Distance To Hostiles')
    tweak_tip = _(u'The minimum distance hostile actors have to be to be '
                  u'allowed to sleep, travel etc, when inside interiors.')
    tweak_key = (u'fHostileActorInteriorDistance',)
    tweak_choices = [(u'10',     10.0),
                     (u'100',   100.0),
                     (u'500',   500.0),
                     (u'1000', 1000.0),
                     (u'2000', 2000.0),
                     (u'3000', 3000.0),
                     (u'4000', 4000.0)]
    default_choice = u'2000'

#------------------------------------------------------------------------------
class GmstTweak_Warning_ExteriorDistanceToHostiles(_AGmstCCUnitsTweak):
    tweak_name = _(u'Warning: Exterior Distance To Hostiles')
    tweak_tip = _(u'The minimum distance hostile actors have to be to be '
                  u'allowed to sleep, travel etc, when outside.')
    tweak_key = (u'fHostileActorExteriorDistance',)
    tweak_choices = [(u'10',     10.0),
                     (u'100',   100.0),
                     (u'500',   500.0),
                     (u'1000', 1000.0),
                     (u'2000', 2000.0),
                     (u'3000', 3000.0),
                     (u'4000', 4000.0),
                     (u'5000', 5000.0),
                     (u'6000', 6000.0)]
    default_choice = u'3000'

#------------------------------------------------------------------------------
class GmstTweak_UOPVampireAgingAndFaceFix(_AGmstTweak):
    tweak_name = _(u'UOP Vampire Aging And Face Fix')
    tweak_tip = _(u"Duplicate of UOP component that disables vampire aging "
                  u"(fixes a bug). Use instead of 'UOP Vampire Aging & Face "
                  u"Fix.esp' to save an esp slot.")
    tweak_key = (u'iVampirismAgeOffset',)
    tweak_choices = [(u'Fix it!', 0)]
    default_enabled = True

#------------------------------------------------------------------------------
class GmstTweak_AI_MaxDeadActors(_AGmstCCTweak):
    tweak_name = _(u'AI: Max Dead Actors')
    tweak_tip = _(u"Maximum number of dead actors allowed before they're "
                  u"removed.")
    tweak_key = (u'iRemoveExcessDeadCount',
                 u'iRemoveExcessDeadTotalActorCount',
                 u'iRemoveExcessDeadComplexTotalActorCount',
                 u'iRemoveExcessDeadComplexCount', u'fRemoveExcessDeadTime',
                 u'fRemoveExcessComplexDeadTime')
    tweak_choices = [(u'x1',      15, 20, 20, 3, 10.0, 2.5),
                     (u'x1.5',    22, 30, 30, 6, 30.0, 7.5),
                     (u'x2',     30, 40, 40, 9, 50.0, 12.5),
                     (u'x2.5',  37, 50, 50, 12, 70.0, 17.5),
                     (u'x3',    45, 60, 60, 15, 90.0, 22.5),
                     (u'x3.5', 52, 70, 70, 18, 110.0, 27.5),
                     (u'x4',   60, 80, 80, 21, 130.0, 32.5)]
    default_choice = u'x1'

#------------------------------------------------------------------------------
class GmstTweak_Player_InventoryQuantityPrompt(_AGmstCCTweak):
    tweak_name = _(u'Player: Inventory Quantity Prompt')
    tweak_tip = _(u'Number of items in a stack at which point the game '
                  u'prompts for a quantity.')
    tweak_key = (u'iInventoryAskQuantityAt',)
    tweak_choices = [(_(u'Always Prompt'),    1),
                     (u'2',                   2),
                     (u'3',                   3),
                     (u'4',                   4),
                     (u'5',                   5),
                     (u'10',                 10),
                     (u'20',                 20),
                     (_(u'Never Prompt'), 99999)]
    default_choice = u'5'

class GmstTweak_Player_InventoryQuantityPrompt_Tes4(
    GmstTweak_Player_InventoryQuantityPrompt):
    default_choice = u'3'

#------------------------------------------------------------------------------
class GmstTweak_Bounty_Trespassing(_AGmstCCTweak):
    tweak_name = _(u'Bounty: Trespassing')
    tweak_tip = _(u'Bounty for trespassing.')
    tweak_key = (u'iCrimeGoldTresspass',) # (sic), corrected in Skyrim
    tweak_choices = [(u'1',   1),
                     (u'5',   5),
                     (u'8',   8),
                     (u'10', 10),
                     (u'20', 20)]
    default_choice = u'5'

class GmstTweak_Bounty_Trespassing_Tes5(GmstTweak_Bounty_Trespassing):
    tweak_key = (u'iCrimeGoldTrespass',)

#------------------------------------------------------------------------------
class GmstTweak_Bounty_Pickpocketing(_AGmstCCTweak):
    tweak_name = _(u'Bounty: Pickpocketing')
    tweak_tip = _(u'Bounty for pickpocketing.')
    tweak_key = (u'iCrimeGoldPickpocket',)
    tweak_choices = [(u'5',     5),
                     (u'8',     8),
                     (u'10',   10),
                     (u'25',   25),
                     (u'50',   50),
                     (u'100', 100)]
    default_choice = u'25'

#------------------------------------------------------------------------------
class GmstTweak_LevelDifference_CreatureMax(_ALeveledDiffTweak):
    tweak_name = _(u'Level Difference: Creature Max')
    tweak_tip = _(u'Maximum difference to player level for leveled creatures.')
    tweak_key = (u'iLevCreaLevelDifferenceMax',)

#------------------------------------------------------------------------------
class GmstTweak_LevelDifference_ItemMax(_ALeveledDiffTweak):
    tweak_name = _(u'Level Difference: Item Max')
    tweak_tip = _(u'Maximum difference to player level for leveled items.')
    tweak_key = (u'iLevItemLevelDifferenceMax',)

#------------------------------------------------------------------------------
class GmstTweak_Actor_StrengthEncumbranceMultiplier(_AGmstCCTweak):
    tweak_name = _(u'Actor: Strength Encumbrance Multiplier')
    tweak_tip = _(u"Actor's Strength X this = Actor's Encumbrance capacity.")
    tweak_key = (u'fActorStrengthEncumbranceMult',)
    tweak_choices = [(u'1',                 1.0),
                     (u'3',                 3.0),
                     (u'5',                 5.0),
                     (u'8',                 8.0),
                     (u'10',               10.0),
                     (u'20',               20.0),
                     (_(u'Unlimited'), 999999.0)]
    default_choice = u'5'

#------------------------------------------------------------------------------
class GmstTweak_Visuals_NPCBlood(_AGmstCCTweak):
    tweak_name = _(u'Visuals: NPC Blood')
    tweak_tip = _(u'Changes or disables NPC Blood splatter textures.')
    tweak_key = (u'sBloodTextureDefault', u'sBloodTextureExtra1',
                 u'sBloodTextureExtra2', u'sBloodParticleDefault',
                 u'sBloodParticleExtra1', u'sBloodParticleExtra2')
    tweak_choices = [(_(u'No Blood'), u'', u'', u'', u'', u'', u'')]

#------------------------------------------------------------------------------
class GmstTweak_AI_MaxSmileDistance(_AGmstCCTweak):
    tweak_name = _(u'AI: Max Smile Distance')
    tweak_tip = _(u'Maximum distance for NPCs to start smiling.')
    tweak_key = (u'fAIMaxSmileDistance',)
    tweak_choices = [(_(u'No Smiles'),       0.0),
                     (_(u'Default (128)'), 128.0)]
    default_choice = _(u'Default (128)')

#------------------------------------------------------------------------------
class GmstTweak_Player_MaxDraggableWeight(_AGmstCCTweak):
    tweak_name = _(u'Player: Max Draggable Weight')
    tweak_tip = _(u'Maximum weight to be able move things with the drag key.')
    tweak_key = (u'fMoveWeightMax',)
    tweak_choices = [(u'115',                          115.0),
                     (u'150',                          150.0),
                     (u'250',                          250.0),
                     (u'500',                          500.0),
                     (_(u'MovableBodies.esp (1500)'), 1500.0)]
    default_choice = u'150'

class GmstTweak_Player_MaxDraggableWeight_Tes5(
    GmstTweak_Player_MaxDraggableWeight):
    default_choice = u'115'

#------------------------------------------------------------------------------
class GmstTweak_AI_ConversationChance(_AGmstCCTweak):
    tweak_name = _(u'AI: Conversation Chance')
    tweak_tip = _(u'Chance of NPCs engaging in conversation.')
    tweak_key = (u'fAISocialchanceForConversation',)
    tweak_choices = [(u'10%',   10.0),
                     (u'25%',   25.0),
                     (u'50%',   50.0),
                     (u'100%', 100.0)]
    default_choice = u'100%'

class GmstTweak_AI_ConversationChance_Tes5(GmstTweak_AI_ConversationChance):
    default_choice = u'25%'

#------------------------------------------------------------------------------
class GmstTweak_AI_ConversationChance_Interior(_AGmstCCTweak):
    tweak_name = _(u'AI: Conversation Chance - Interior')
    tweak_tip = _(u'Chance of NPCs engaging in conversation - in interiors.')
    tweak_key = (u'fAISocialchanceForConversationInterior',)
    tweak_choices = [(u'10%',   10.0),
                     (u'25%',   25.0),
                     (u'50%',   50.0),
                     (u'100%', 100.0)]
    default_choice = u'25%'

#------------------------------------------------------------------------------
class GmstTweak_Crime_PickpocketingChance(_AGmstTweak):
    tweak_name = _(u'Crime: Pickpocketing Chance')
    tweak_tip = _(u'Improve chances of successful pickpocketing.')
    tweak_key = (u'fPickPocketMinChance', u'fPickPocketMaxChance')
    tweak_choices = [(_(u'0% to 50%'),     0.0, 50.0),
                     (_(u'0% to 75%'),     0.0, 75.0),
                     (_(u'0% to 90%'),     0.0, 90.0),
                     (_(u'0% to 100%'),   0.0, 100.0),
                     (_(u'25% to 100%'), 25.0, 100.0),
                     (_(u'50% to 100%'), 50.0, 100.0)]
    default_choice = _(u'0% to 90%')
    custom_choice = _(u'Custom (Min and Max Chance)')

#------------------------------------------------------------------------------
class GmstTweak_Actor_MaxJumpHeight(_AGmstCCTweak):
    tweak_name = _(u'Actor: Max Jump Height')
    tweak_tip = _(u'Increases the height to which you can jump.')
    tweak_key = (u'fJumpHeightMin',)
    tweak_choices = [(u'0.5x', 38.0),
                     (u'1x',   76.0),
                     (u'2x',  152.0),
                     (u'3x',  228.0),
                     (u'4x',  304.0)]
    default_choice = u'1x'

class GmstTweak_Actor_MaxJumpHeight_Tes4(GmstTweak_Actor_MaxJumpHeight):
    tweak_tip = _(u'Increases the height to which you can jump. First value '
                  u'is min, second is max.')
    tweak_key = (u'fJumpHeightMin', u'fJumpHeightMax')
    tweak_choices = [(u'0.5x', 38.0, 82.0),
                     (u'1x',  76.0, 164.0),
                     (u'2x', 152.0, 328.0),
                     (u'3x', 228.0, 492.0),
                     (u'4x', 304.0, 656.0)]

#------------------------------------------------------------------------------
class GmstTweak_Bounty_Murder(_AGmstCCTweak):
    tweak_name = _(u'Bounty: Murder')
    tweak_tip = _(u'Bounty for committing a witnessed murder.')
    tweak_key = (u'iCrimeGoldMurder',)
    tweak_choices = [(u'500',   500),
                     (u'750',   750),
                     (u'1000', 1000),
                     (u'1250', 1250),
                     (u'1500', 1500)]
    default_choice = u'1000'

#------------------------------------------------------------------------------
class GmstTweak_Bounty_Jailbreak(_AGmstCCTweak):
    tweak_name = _(u'Bounty: Jailbreak')
    tweak_tip = _(u'Bounty for escaping from jail.')
    tweak_key = (u'iCrimeGoldJailBreak',)
    tweak_choices = [(u'50',   50),
                     (u'100', 100),
                     (u'125', 125),
                     (u'150', 150),
                     (u'175', 175),
                     (u'200', 200)]
    default_choice = u'50'

class GmstTweak_Bounty_Jailbreak_Tes5(GmstTweak_Bounty_Jailbreak):
    tweak_key = (u'iCrimeGoldEscape',)
    default_choice = u'100'

#------------------------------------------------------------------------------
class GmstTweak_Gore_CombatDismemberPartChance(_AGmstCCTweak):
    tweak_name = _(u'Gore: Combat Dismember Part Chance')
    tweak_tip = _(u'The chance that body parts will be dismembered.')
    tweak_key = (u'iCombatDismemberPartChance',)
    tweak_choices = [(u'0',     0),
                     (u'25',   25),
                     (u'50',   50),
                     (u'80',   80),
                     (u'100', 100)]
    default_choice = u'50'

#------------------------------------------------------------------------------
class GmstTweak_Gore_CombatExplodePartChance(_AGmstCCTweak):
    tweak_name = _(u'Gore: Combat Explode Part Chance')
    tweak_tip = _(u'The chance that body parts will explode.')
    tweak_key = (u'iCombatExplodePartChance',)
    tweak_choices = [(u'0',     0),
                     (u'25',   25),
                     (u'50',   50),
                     (u'75',   75),
                     (u'100', 100)]
    default_choice = u'75'

#------------------------------------------------------------------------------
class GmstTweak_Movement_BaseSpeed(_AGmstCCTweak):
    tweak_name = _(u'Movement: Base Speed')
    tweak_tip = _(u'Changes base movement speed.')
    tweak_key = (u'fMoveBaseSpeed',)
    tweak_choices = [(u'77.0', 77.0),
                     (u'90.0', 90.0)]
    default_choice = u'77.0'

#------------------------------------------------------------------------------
class GmstTweak_Movement_SneakMultiplier(_AGmstCCTweak):
    tweak_name = _(u'Movement: Sneak Multiplier')
    tweak_tip = _(u'Movement speed is multiplied by this when the actor is '
                  u'sneaking.')
    tweak_key = (u'fMoveSneakMult',)
    tweak_choices = [(u'0.57', 0.57),
                     (u'0.66', 0.66)]
    default_choice = u'0.57'

#------------------------------------------------------------------------------
class GmstTweak_Combat_VATSPlayerDamageMultiplier(_AGmstCCTweak):
    tweak_name = _(u'Combat: VATS Player Damage Multiplier')
    tweak_tip = _(u'Multiplier of damage that player receives in VATS.')
    tweak_key = (u'fVATSPlayerDamageMult',)
    tweak_choices = [(u'0.10',  0.1),
                     (u'0.25', 0.25),
                     (u'0.50',  0.5),
                     (u'0.75', 0.75),
                     (u'1.00',  1.0)]
    default_choice = u'0.75'

#------------------------------------------------------------------------------
class GmstTweak_Combat_AutoAimFix(_AGmstTweak):
    tweak_name = _(u'Combat: Auto Aim Fix')
    tweak_tip = _(u'Increase Auto Aim settings to a level at which snipers '
                  u'can benefit from them.')
    tweak_key = (u'fAutoAimMaxDistance', u'fAutoAimScreenPercentage',
                 u'fAutoAimMaxDegrees', u'fAutoAimMissRatioLow',
                 u'fAutoAimMissRatioHigh', u'fAutoAimMaxDegreesMiss')
    tweak_choices = [(u'Harder', 50000.0, -180.0, 1.1, 1.0, 1.3, 3.0)]

#------------------------------------------------------------------------------
class GmstTweak_Player_PipBoyLightKeypressDelay(_AGmstCCTweak):
    tweak_name = _(u'Player: PipBoy Light Keypress Delay')
    tweak_tip = _(u'Seconds of delay until the PipBoy light switches on.')
    tweak_key = (u'fPlayerPipBoyLightTimer',)
    tweak_choices = [(u'0.3', 0.3),
                     (u'0.4', 0.4),
                     (u'0.5', 0.5),
                     (u'0.6', 0.6),
                     (u'0.7', 0.7),
                     (u'0.8', 0.8),
                     (u'1.0', 1.0)]
    default_choice = u'0.8'

#------------------------------------------------------------------------------
class GmstTweak_Combat_VATSPlaybackDelay(_AGmstCCTweak):
    tweak_name = _(u'Combat: VATS Playback Delay')
    tweak_tip = _(u'Seconds of delay after the VATS Camera finished playback.')
    tweak_key = (u'fVATSPlaybackDelay',)
    tweak_choices = [(u'0.01', 0.01),
                     (u'0.05', 0.05),
                     (u'0.10',  0.1),
                     (u'0.17', 0.17),
                     (u'0.25', 0.25)]
    default_choice = u'0.17'

#------------------------------------------------------------------------------
class GmstTweak_Combat_NPCDeathXPThreshold(_AGmstCCTweak):
    tweak_name = _(u'Combat: NPC Death XP Threshold')
    tweak_tip = _(u'Percentage of total damage you have to inflict in order '
                  u'to get XP.')
    tweak_key = (u'iXPDeathRewardHealthThreshold',)
    tweak_choices = [(u'0%',   0),
                     (u'25%', 25),
                     (u'40%', 40),
                     (u'50%', 50),
                     (u'75%', 75)]
    default_choice = u'40%'

#------------------------------------------------------------------------------
class GmstTweak_Hacking_MaximumNumberOfWords(_AGmstCCTweak):
    tweak_name = _(u'Hacking: Maximum Number Of Words')
    tweak_tip = _(u'The maximum number of words appearing in the terminal '
                  u'hacking mini-game.')
    tweak_key = (u'iHackingMaxWords',)
    tweak_choices = [(u'1',   1),
                     (u'4',   4),
                     (u'8',   8),
                     (u'12', 12),
                     (u'16', 16),
                     (u'20', 20)]
    default_choice = u'20'

#------------------------------------------------------------------------------
class GmstTweak_Visuals_ShellCameraDistance(_AGmstCCTweak):
    tweak_name = _(u'Visuals: Shell Camera Distance')
    tweak_tip = _(u'Maximum distance at which gun arisings (shell case, '
                  u'particle, decal) show from camera.')
    tweak_key = (u'fGunParticleCameraDistance', u'fGunShellCameraDistance',
                 u'fGunDecalCameraDistance')
    tweak_choices = [(u'x1.5',  3072.0, 768.0, 3072.0),
                     (u'x2',   4096.0, 1024.0, 4096.0),
                     (u'x3',   6144.0, 1536.0, 6144.0),
                     (u'x4',   8192.0, 2048.0, 8192.0),
                     (u'x5', 10240.0, 2560.0, 10240.0)]

#------------------------------------------------------------------------------
class GmstTweak_Visuals_ShellLitterTime(_AGmstCCSecondsTweak):
    tweak_name = _(u'Visuals: Shell Litter Time')
    tweak_tip = _(u'Time before shell cases fade away from cells.')
    tweak_key = (u'fGunShellLifetime',)
    tweak_choices = [(_(u'10 Seconds'), 10.0),
                     (_(u'20 Seconds'), 20.0),
                     (_(u'30 Seconds'), 30.0),
                     (_(u'1 Minute'),   60.0),
                     (_(u'3 Minutes'), 180.0),
                     (_(u'5 Minutes'), 300.0)]
    default_choice = _(u'10 Seconds')

#------------------------------------------------------------------------------
class GmstTweak_Visuals_ShellLitterCount(_AGmstCCTweak):
    tweak_name = _(u'Visuals: Shell Litter Count')
    tweak_tip = _(u'Maximum number of debris (shell case, etc) allowed in '
                  u'cell.')
    tweak_key = (u'iDebrisMaxCount',)
    tweak_choices = [(u'50',     50),
                     (u'100',   100),
                     (u'500',   500),
                     (u'1000', 1000),
                     (u'3000', 3000)]
    default_choice = u'50'

#------------------------------------------------------------------------------
class GmstTweak_Hacking_TerminalSpeedAdjustment(_AGmstCCTweak):
    tweak_name = _(u'Hacking: Terminal Speed Adjustment')
    tweak_tip = _(u'The display speed at the time of terminal hacking.')
    tweak_key = (u'iHackingDumpRate', u'iHackingInputRate',
                 u'iHackingOutputRate', u'iHackingFlashOffDuration',
                 u'iHackingFlashOnDuration', u'iComputersDisplayRateMenus',
                 u'iComputersDisplayRateNotes')
    tweak_choices = [(u'x2', 1000, 40, 134, 250, 375, 300, 300),
                     (u'x4', 2000, 80, 268, 125, 188, 600, 600),
                     (u'x6', 3000, 120, 402, 83, 126, 900, 900)]
    default_choice = u'x6'

#------------------------------------------------------------------------------
class GmstTweak_Msg_SoulCaptured(_AMsgTweak):
    tweak_name = _(u'Msg: Soul Captured')
    tweak_tip = _(u'Message upon capturing a soul in a Soul Gem.')
    tweak_key = (u'sSoulCaptured',)

#------------------------------------------------------------------------------
class GmstTweak_World_CellRespawnTime_Cleared(_AGmstTweak):
    tweak_name = _(u'World: Cell Respawn Time (Cleared)')
    tweak_tip = _(u'Time before cleared cells respawn. Longer times increase '
                  u'save sizes.')
    tweak_key = (u'iHoursToRespawnCellCleared',)
    tweak_choices = [(_(u'10 Days'),   240),
                     (_(u'15 Days'),   360),
                     (_(u'20 Days'),   480),
                     (_(u'25 Days'),   600),
                     (_(u'30 Days'),   720),
                     (_(u'2 Months'), 1440),
                     (_(u'6 Months'), 4320),
                     (_(u'1 Year'),   8760)]
    default_choice = _(u'30 Days')
    custom_choice = _(u'Custom (in hours)')

#------------------------------------------------------------------------------
class GmstTweak_Magic_MaxResistance(_AGmstCCTweak):
    tweak_name = _(u'Magic: Max Resistance')
    tweak_tip = _(u'Maximum level of resistance a player can have to various '
                  u'forms of magic and disease.')
    tweak_key = (u'fPlayerMaxResistance',)
    tweak_choices = [(u'50%',   50.0),
                     (u'60%',   60.0),
                     (u'70%',   70.0),
                     (u'80%',   80.0),
                     (u'85%',   85.0),
                     (u'90%',   90.0),
                     (u'100%', 100.0)]
    default_choice = u'85%'

#------------------------------------------------------------------------------
class GmstTweak_Magic_MaxSummons(_AGmstCCTweak):
    tweak_name = _(u'Magic: Max Summons')
    tweak_tip = _(u'Maximum number of creatures an actor can summon (affects '
                  u'both NPCs and the player).')
    tweak_key = (u'iMaxSummonedCreatures',)
    tweak_choices = [(u'1',   1),
                     (u'3',   3),
                     (u'5',   5),
                     (u'8',   8),
                     (u'10', 10)]
    default_choice = u'1'

#------------------------------------------------------------------------------
class GmstTweak_Actor_VerticalObjectDetection(_AGmstCCTweak):
    tweak_name = _(u'Actor: Vertical Object Detection')
    tweak_tip = _(u'Changes the vertical range in which NPCs detect objects. '
                  u'The first value must be >= 0 and the second one must be '
                  u'<= 0.')
    tweak_key = (u'fSandboxCylinderTop', u'fSandboxCylinderBottom')
    tweak_choices = [(u'x1', 150.0, -100.0),
                     (u'x2', 300.0, -200.0),
                     (u'x3', 450.0, -300.0),
                     (u'x4', 600.0, -400.0),
                     (u'x5', 750.0, -500.0)]
    default_choice = u'x1'

#------------------------------------------------------------------------------
class GmstTweak_Player_FastTravelTimeMultiplier(_AGmstCCTweak):
    tweak_name = _(u'Player: Fast Travel Time Multiplier')
    tweak_tip = _(u'Changes how much time passes while fast traveling. By '
                  u'default, it passes ~3x slower than if you had walked the '
                  u'distance.')
    tweak_key = (u'fFastTravelSpeedMult',)
    tweak_choices = [(_(u'Default Speed'), 1.0),
                     (_(u'Walking Speed'), 3.5),
                     (_(u'Horse Speed'),   4.0)]
    default_choice = _(u'Default Speed')

#------------------------------------------------------------------------------
class GmstTweak_Combat_CriticalHitChance(_AGmstTweak):
    tweak_name = _(u'Combat: Critical Hit Chance')
    tweak_tip = _(u'The chance of a strike being a critical hit.')
    tweak_key = (u'fWeaponConditionCriticalChanceMult',)
    tweak_choices = [(_(u'0% (Disabled)'), 0.0),
                     (u'1%',              0.01),
                     (u'5%',              0.05),
                     (u'10%',              0.1),
                     (u'25%',             0.25),
                     (u'50%',              0.5),
                     (_(u'100% (Always)'), 1.0)]
    default_choice = u'10%'
    custom_choice = _(u'Custom (Max: 1.0)')

#------------------------------------------------------------------------------
class GmstTweak_Arrow_MaxArrowsAttachedToNPC(_AGmstCCTweak):
    tweak_name = _(u'Arrow: Max Arrows Attached To NPC')
    tweak_tip = _(u'The Maximum number of arrows that can be sticking out of '
                  u'an actor.')
    tweak_key = (u'iMaxAttachedArrows',)
    tweak_choices = [(u'3',     3),
                     (u'10',   10),
                     (u'30',   30),
                     (u'50',   50),
                     (u'100', 100)]
    default_choice = u'3'

#------------------------------------------------------------------------------
class GmstTweak_Combat_DisableProjectileDodging(_AGmstTweak):
    tweak_name = _(u'Combat: Disable Projectile Dodging')
    tweak_tip = _(u'Removes the ability of NPCs to dodge projectiles being '
                  u'launched at them from range.')
    tweak_key = (u'fCombatDodgeChanceMax',)
    tweak_choices = [(_(u'Enabled'), 0.0)]

#------------------------------------------------------------------------------
class GmstTweak_Actor_MerchantRestockTime(_AGmstTweak):
    tweak_name = _(u'Actor: Merchant Restock Time')
    tweak_tip = _(u'The amount of time required for vendors to restock items '
                  u'and gold.')
    tweak_key = (u'iDaysToRespawnVendor',)
    tweak_choices = [(_(u'Instant'),    0),
                     (_(u'1 Day'),      1),
                     (_(u'2 Days'),     2),
                     (_(u'4 Days'),     4),
                     (_(u'1 Week'),     7),
                     (_(u'2 Weeks'),   14),
                     (_(u'1 Month'),   28),
                     (_(u'Never'),  99999)]
    default_choice = _(u'2 Days')
    custom_choice = _(u'Custom (in days)')

#------------------------------------------------------------------------------
class GmstTweak_Player_FallDamageThreshold(_AGmstCCUnitsTweak):
    tweak_name = _(u'Player: Fall Damage Threshold')
    tweak_tip = _(u'Changes the height at which you take fall damage.')
    tweak_key = (u'fJumpFallHeightMin',)
    tweak_choices = [(u'0.5x',                300.0),
                     (u'1x',                  600.0),
                     (u'2x',                 1200.0),
                     (u'3x',                 1800.0),
                     (u'4x',                 2400.0),
                     (u'5x',                 3000.0),
                     (_(u'No Fall Damage'), 99999.0)]
    default_choice = u'1x'

#------------------------------------------------------------------------------
class GmstTweak_Player_SprintingCost(_AGmstTweak):
    tweak_name = _(u'Player: Sprinting Cost')
    tweak_tip = _(u'Changes the stamina drain that occurs when sprinting.')
    tweak_key = (u'fSprintStaminaDrainMult',)
    tweak_choices = [(_(u'None'),     0.0),
                     (_(u'Halved'),   3.5),
                     (_(u'Default'),  7.0),
                     (_(u'Doubled'), 14.0),
                     (_(u'Tripled'), 21.0)]
    default_choice = _(u'Default')
    custom_choice = _(u'Custom (Lower = Less Drain)')

#------------------------------------------------------------------------------
class GmstTweak_Visuals_MasserSize(_AGmstCCTweak):
    tweak_name = _(u'Visuals: Masser Size')
    tweak_tip = _(u'Changes the size of the moon Masser (the larger one) in '
                  u'the night sky.')
    tweak_key = (u'iMasserSize',)
    tweak_choices = [(_(u'50% Smaller'), 45),
                     (_(u'25% Smaller'), 68),
                     (_(u'Default'),     90),
                     (_(u'25% Larger'), 113),
                     (_(u'50% Larger'), 135)]
    default_choice = _(u'Default')

#------------------------------------------------------------------------------
class GmstTweak_Visuals_MasserSpeed(_AGmstCCUnitsTweak):
    tweak_name = _(u'Visuals: Masser Speed')
    tweak_tip = _(u'Changes how quickly the moon Masser (the larger one) '
                  u'moves in the night sky.')
    tweak_key = (u'fMasserSpeed',)
    tweak_choices = [(u'0.5x', 0.125),
                     (u'1x',    0.25),
                     (u'2x',     0.5),
                     (u'3x',    0.75)]
    default_choice = u'1x'

#------------------------------------------------------------------------------
class GmstTweak_Visuals_SecundaSize(_AGmstCCTweak):
    tweak_name = _(u'Visuals: Secunda Size')
    tweak_tip = _(u'Changes the size of the moon Secunda (the smaller one) '
                  u'in the night sky.')
    tweak_key = (u'iSecundaSize',)
    tweak_choices = [(_(u'50% Smaller'), 20),
                     (_(u'25% Smaller'), 30),
                     (_(u'Default'),     40),
                     (_(u'25% Larger'),  50),
                     (_(u'50% Larger'),  60)]
    default_choice = _(u'Default')

#------------------------------------------------------------------------------
class GmstTweak_Visuals_SecundaSpeed(_AGmstCCUnitsTweak):
    tweak_name = _(u'Visuals: Secunda Speed')
    tweak_tip = _(u'Changes how quickly the moon Secunda (the smaller one) '
                  u'moves in the night sky.')
    tweak_key = (u'fSecundaSpeed',)
    tweak_choices = [(u'0.5x', 0.15),
                     (u'1x',    0.3),
                     (u'2x',    0.6),
                     (u'3x',    0.9)]
    default_choice = u'1x'

#------------------------------------------------------------------------------
class GmstTweak_AI_BumpReactionDelay(_AGmstCCTweak):
    tweak_name = _(u'AI: Bump Reaction Delay')
    tweak_tip = _(u'Changes how long it takes until NPCs (particularly '
                  u'followers) that have commented on you bumping into them '
                  u'repeat that dialogue. Infinite effectively disables it.')
    tweak_key = (u'fBumpReactionSmallDelayTime',)
    tweak_choices = [(_(u'Infinite'), 99999.0),
                     (_(u'10x Longer'),  10.0),
                     (_(u'5x Longer'),    5.0),
                     (_(u'Default'),      1.0)]
    default_choice = _(u'Default')

#------------------------------------------------------------------------------
class GmstTweak_Magic_MaxActiveRunes(_AGmstCCTweak):
    tweak_name = _(u'Magic: Max Active Runes')
    tweak_tip = _(u'How many rune spells the player can have active '
                  u'simultaneously.')
    tweak_key = (u'iMaxPlayerRunes',)
    tweak_choices = [(u'1',               1),
                     (u'3',               3),
                     (u'5',               5),
                     (u'10',             10),
                     (u'50',             50),
                     (_(u'No Limit'), 99999)]
    default_choice = u'1'

#------------------------------------------------------------------------------
class GmstTweak_Actor_FasterShouts(_AGmstTweak):
    tweak_name = _(u'Actor: Faster Shouts')
    tweak_tip = _(u'Decreases the time that the shout key must be held to '
                  u'shout multiple words. Custom is for the first word and '
                  u'the rest of the shout.')
    tweak_key = (u'fShoutTime1', u'fShoutTime2')
    tweak_choices = [(_(u'4x Faster'), 0.05, 0.225),
                     (_(u'2x Faster'),   0.1, 0.45),
                     (_(u'Default'),      0.2, 0.9),
                     (_(u'2x Slower'),    0.4, 1.8),
                     (_(u'4x Slower'),    0.8, 3.6)]
    default_choice = _(u'Default')
    custom_choice = _(u'Custom (in milliseconds)')

#------------------------------------------------------------------------------
class GmstTweak_Combat_FasterTwo_HandedWeapons(_AGmstCCTweak):
    tweak_name = _(u'Combat: Faster Two-Handed Weapons')
    tweak_tip = _(u'Changes 2-hand weapon animation speed.')
    tweak_key = (u'fWeaponTwoHandedAnimationSpeedMult',)
    tweak_choices = [(_(u'50% Slower'),  0.75),
                     (_(u'25% Slower'), 1.125),
                     (_(u'Default'),      1.5),
                     (_(u'25% Faster'), 1.875),
                     (_(u'50% Faster'),  2.25)]
    default_choice = _(u'Default')

#------------------------------------------------------------------------------
class GmstTweak_Player_UnderwaterBreathControl(_AGmstTweak):
    tweak_name = _(u'Player: Underwater Breath Control')
    tweak_tip = _(u'How long the player can hold their breath while swimming '
                  u'- does not affect Argonians.')
    tweak_key = (u'fActorSwimBreathBase', u'fActorSwimBreathMult')
    tweak_choices = [(_(u'10 Seconds'),  10.0, 0.3),
                     (_(u'20 Seconds'),  20.0, 0.3),
                     (_(u'40 Seconds'), 40.0, 0.45),
                     (_(u'60 Seconds'),  60.0, 0.6)]
    default_choice = _(u'10 Seconds')
    custom_choice = _(u'Custom (Base and Multiplier)')

#------------------------------------------------------------------------------
class GmstTweak_Combat_StealthDamageBonus(_AGmstTweak):
    tweak_name = _(u'Combat: Stealth Damage Bonus')
    tweak_tip = _(u'Increases the amount of damage you do with daggers, bows '
                  u'and crossbows while sneaking.')
    tweak_key = (u'fCombatSneak1HDaggerMult', u'fCombatSneakBowMult',
                 u'fCombatSneakCrossbowMult')
    tweak_choices = [(u'1x',  3.0, 2.0, 2.0),
                     (u'2x',  6.0, 4.0, 4.0),
                     (u'3x',  9.0, 6.0, 6.0),
                     (u'4x', 12.0, 8.0, 8.0)]
    default_choice = u'1x'
    custom_choice = _(u'Custom (Dagger, Bow, Crossbow)')

#------------------------------------------------------------------------------
class GmstTweak_Msg_CannotEquipItemFix(_AGmstTweak):
    tweak_name = _(u'Msg: Cannot Equip Item Fix')
    tweak_tip = _(u"Disables the 'You cannot equip this item' message because "
                  u"some Skyrim mods (e.g. Frostfall) use activatable misc "
                  u"objects that require it to be disabled.")
    tweak_key = (u'sCantEquipGeneric',)
    tweak_choices = [(_(u'Enabled'), u'')]
    default_enabled = True

#------------------------------------------------------------------------------
class GmstTweak_Msg_CarryingTooMuch(_AMsgTweak):
    tweak_name = _(u'Msg: Carrying Too Much')
    tweak_tip = _(u'Message when you are carrying too much to run.')
    tweak_key = (u'sOverEncumbered',)

#------------------------------------------------------------------------------
class GmstTweak_Magic_InvisibilityDetectionDifficulty(_AGmstCCTweak):
    tweak_name = _(u'Magic: Invisibility Detection Difficulty')
    tweak_tip = _(u'Determines how difficult it is for NPCs to see you while '
                  u'you are invisible.')
    tweak_key = (u'fSneakStealthBoyMult',)
    tweak_choices = [(_(u'Impossible'),           0.0),
                     (_(u'75% Harder'),          0.25),
                     (_(u'50% Harder'),           0.5),
                     (_(u'25% Harder'),          0.75),
                     (_(u'Nullify Invisibility'), 1.0)]
    default_choice = _(u'Impossible')

#------------------------------------------------------------------------------
class GmstTweak_Bounty_Shapeshifting(_AGmstCCTweak):
    tweak_name = _(u'Bounty: Shapeshifting')
    tweak_tip = _(u'The bounty for transforming into a vampire lord or '
                  u'werewolf in front of people.')
    tweak_key = (u'iCrimeGoldWerewolf',)
    tweak_choices = [(u'500',   500),
                     (u'750',   750),
                     (u'1000', 1000),
                     (u'1250', 1250),
                     (u'1500', 1500)]
    default_choice = u'1000'

#------------------------------------------------------------------------------
class GmstTweak_SoulTrap_LesserSoulLevel(_ASoulTrapTweak):
    tweak_name = _(u'Soul Trap: Lesser Soul Level')
    tweak_tip = _(u"The level at which NPC souls are considered 'lesser'.")
    tweak_key = (u'iLesserSoulActorLevel',)
    default_choice = u'4'

#------------------------------------------------------------------------------
class GmstTweak_SoulTrap_CommonSoulLevel(_ASoulTrapTweak):
    tweak_name = _(u'Soul Trap: Common Soul Level')
    tweak_tip = _(u"The level at which NPC souls are considered 'common'.")
    tweak_key = (u'iCommonSoulActorLevel',)
    default_choice = u'16'

#------------------------------------------------------------------------------
class GmstTweak_SoulTrap_GreaterSoulLevel(_ASoulTrapTweak):
    tweak_name = _(u'Soul Trap: Greater Soul Level')
    tweak_tip = _(u"The level at which NPC souls are considered 'greater'.")
    tweak_key = (u'iGreaterSoulActorLevel',)
    default_choice = u'28'

#------------------------------------------------------------------------------
class GmstTweak_SoulTrap_GrandSoulLevel(_ASoulTrapTweak):
    tweak_name = _(u'Soul Trap: Grand Soul Level')
    tweak_tip = _(u"The level at which NPC souls are considered 'grand'.")
    tweak_key = (u'iGrandSoulActorLevel',)
    default_choice = u'38'

#------------------------------------------------------------------------------
class GmstTweak_Prompt_Activate(_AGmstCCTweak):
    tweak_name = _(u'Prompt: Activate')
    tweak_tip = _(u"Changes the text on the 'Activate' prompt shown when "
                  u'interacting with objects.')
    tweak_key = (u'sActivate',)
    tweak_choices = [(_(u'Interact'), _(u'Interact'))]

class GmstTweak_Prompt_Activate_Tes4(GmstTweak_Prompt_Activate):
    tweak_key = (u'sTargetTypeActivate',)

#------------------------------------------------------------------------------
class GmstTweak_Prompt_Open(_AGmstCCTweak):
    tweak_name = _(u'Prompt: Open')
    tweak_tip = _(u"Changes the text on the 'Open' prompt shown when trying "
                  u'to open a door.')
    tweak_key = (u'sOpen',)
    tweak_choices = [(_(u'Enter'), _(u'Enter'))]

class GmstTweak_Prompt_Open_Tes4(GmstTweak_Prompt_Open):
    tweak_key = (u'sTargetTypeOpenDoor',)

#------------------------------------------------------------------------------
class GmstTweak_Prompt_Read(_AGmstCCTweak):
    tweak_name = _(u'Prompt: Read')
    tweak_tip = _(u"Changes the text on the 'Read' prompt shown when "
                  u'interacting with books.')
    tweak_key = (u'sRead',)
    tweak_choices = [(_(u'View'), _(u'View'))]

class GmstTweak_Prompt_Read_Tes4(GmstTweak_Prompt_Read):
    tweak_key = (u'sTargetTypeRead',)

#------------------------------------------------------------------------------
class GmstTweak_Prompt_Sit(_AGmstCCTweak):
    tweak_name = _(u'Prompt: Sit')
    tweak_tip = _(u"Changes the text on the 'Sit' prompt shown when "
                  u'interacting with chairs.')
    tweak_key = (u'sSit',)
    tweak_choices = [(_(u'Sit Down'), _(u'Sit Down'))]

class GmstTweak_Prompt_Sit_Tes4(GmstTweak_Prompt_Sit):
    tweak_key = (u'sTargetTypeSit',)

#------------------------------------------------------------------------------
class GmstTweak_Prompt_Take(_AGmstCCTweak):
    tweak_name = _(u'Prompt: Take')
    tweak_tip = _(u"Changes the text on the 'Take' prompt shown when taking "
                  u'items.')
    tweak_key = (u'sTake',)
    tweak_choices = [(_(u'Grab'), _(u'Grab'))]

class GmstTweak_Prompt_Take_Tes4(GmstTweak_Prompt_Take):
    tweak_key = (u'sTargetTypeTake',)

#------------------------------------------------------------------------------
class GmstTweak_Prompt_Talk(_AGmstCCTweak):
    tweak_name = _(u'Prompt: Talk')
    tweak_tip = _(u"Changes the text on the 'Talk' prompt shown when "
                  u'interacting with people.')
    tweak_key = (u'sTalk',)
    tweak_choices = [(_(u'Speak'), _(u'Speak'))]

class GmstTweak_Prompt_Talk_Tes4(GmstTweak_Prompt_Talk):
    tweak_key = (u'sTargetTypeTalk',)

#------------------------------------------------------------------------------
class GmstTweak_Msg_NoSoulGemLargeEnough(_AMsgTweak):
    tweak_name = _(u'Msg: No Soul Gem Large Enough')
    tweak_tip = _(u'Message when there is no soul gem large enough for a '
                  u'captured soul.')
    tweak_key = (u'sSoulGemTooSmall',)

#------------------------------------------------------------------------------
class GmstTweak_Combat_SpeakOnAttackChance(_ATauntTweak):
    tweak_name = _(u'Combat: Speak on Attack Chance')
    tweak_tip = _(u'The chance that an actor will speak after performing an '
                  u'attack.')
    tweak_key = (u'fCombatSpeakAttackChance',)
    tweak_choices = [(_(u'0% (Disabled)'), 0.0),
                     (u'8%',              0.08),
                     (u'25%',             0.25),
                     (u'50%',              0.5),
                     (u'75%',             0.75),
                     (_(u'100% (Always)'), 1.0)]
    default_choice = u'8%'

#------------------------------------------------------------------------------
class GmstTweak_Combat_SpeakOnHitChance(_ATauntTweak):
    tweak_name = _(u'Combat: Speak on Hit Chance')
    tweak_tip = _(u'The chance that an actor will speak after being hit with '
                  u'a weapon.')
    tweak_key = (u'fCombatSpeakHitChance',)
    default_choice = u'1%'

class GmstTweak_Combat_SpeakOnHitChance_Tes4(
    GmstTweak_Combat_SpeakOnHitChance):
    default_choice = u'20%'

#------------------------------------------------------------------------------
class GmstTweak_Combat_SpeakOnHitThreshold(_ATauntTweak):
    tweak_name = _(u'Combat: Speak on Hit Threshold')
    tweak_tip = _(u"The percentage of an actor's health an attack must deal "
                  u'for the actor to speak when hit.')
    tweak_key = (u'fCombatSpeakHitThreshold',)
    tweak_choices = [(_(u'0% (Always)'), 0.0),
                     (u'1%',              0.01),
                     (u'10%',              0.1),
                     (u'25%',             0.25),
                     (u'50%',              0.5),
                     (u'75%',             0.75),
                     (_(u'100% (Disabled)'), 1.0)]
    default_choice = u'1%'

class GmstTweak_Combat_SpeakOnHitThreshold_Tes4(
    GmstTweak_Combat_SpeakOnHitThreshold):
    default_choice = u'10%'

#------------------------------------------------------------------------------
class GmstTweak_Combat_SpeakOnPowerAttackChance(_ATauntTweak):
    tweak_name = _(u'Combat: Speak on Power Attack Chance')
    tweak_tip = _(u'The chance that an actor will speak after performing a '
                  u'power attack.')
    tweak_key = (u'fCombatSpeakPowerAttackChance',)

class GmstTweak_Combat_SpeakOnPowerAttackChance_Tes4(
    GmstTweak_Combat_SpeakOnPowerAttackChance):
    default_choice = _(u'100% (Always)')

#------------------------------------------------------------------------------
class GmstTweak_Combat_RandomTauntChance(_ATauntTweak):
    tweak_name = _(u'Combat: Random Taunt Chance')
    tweak_tip = _(u'Determines how often actors randomly taunt during combat.')
    tweak_key = (u'fCombatSpeakTauntChance',)

#------------------------------------------------------------------------------
class GmstTweak_LevelUp_SkillCount(_AGmstCCTweak):
    tweak_name = _(u'Level Up: Skill Count')
    tweak_tip = _(u'The number of major skill point increases needed to level '
                  u'up.')
    tweak_key = (u'iLevelUpSkillCount',)
    tweak_choices = [(u'1',   1),
                     (u'5',   5),
                     (u'10', 10),
                     (u'20', 20)]
    default_choice = u'10'

#------------------------------------------------------------------------------
class TweakSettingsPatcher(MultiTweaker):
    """Tweaks GLOB and GMST records in various ways."""
    _tweak_classes = {globals()[t] for t in bush.game.settings_tweaks}
