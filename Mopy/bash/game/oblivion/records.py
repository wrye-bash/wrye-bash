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
#  Wrye Bash copyright (C) 2005-2009 Wrye, 2010-2024 Wrye Bash Team
#  https://github.com/wrye-bash
#
# =============================================================================
"""This module contains the oblivion record classes."""
import random
import re

from ...bolt import Flags, LowerDict, flag, int_or_none, int_or_zero, \
    sig_to_str, str_or_none, str_to_sig, structs_cache
from ...brec import FID, AMelItems, AMelLLItems, AMreActor, AMreCell, \
    AMreHeader, AMreLeveledList, AMreRace, AMreWithItems, AMreWrld, AMreWthr, \
    AttrValDecider, BipedFlags, FlagDecider, MelActionFlags, MelActorSounds, \
    MelAnimations, MelArray, MelBase, MelBaseR, MelBodyParts, MelBookText, \
    MelClmtTextures, MelClmtTiming, MelClmtWeatherTypes, MelCombatStyle, \
    MelConditionsTes4, MelContData, MelDeathItem, MelDescription, AMreGlob, \
    MelDoorFlags, MelEdid, MelEffectsTes4, MelEffectsTes4ObmeFull, \
    MelEnableParent, MelEnchantment, MelFactions, MelFactRanks, MelFid, \
    MelFloat, MelFull, MelGrasData, MelGroup, MelGroups, MelSimpleGroups, \
    MelHairFlags, MelIco2, MelIcon, MelIdleRelatedAnims, MelIngredient, \
    MelLandShared, MelLighFade, MelLists, MelLLChanceNone, MelLLFlags, \
    MelLscrLocations, MelLtexGrasses, MelLtexSnam, MelMapMarker, MelNull, \
    MelObme, MelOwnership, MelMgefEsceTes4, MelMgefData, MelRace, \
    MelRaceData, MelRaceParts, MelRaceVoices, MelRandomTeleports, \
    MelReadOnly, MelRecord, MelRef3D, MelReferences, MelRefScale, MelRegions, \
    MelRegnEntryMusicType, MelRelations, MelScript, MelScriptVars, \
    MelSeasons, MelSequential, MelSet, MelSimpleArray, MelSInt16, MelSInt32, \
    MelSkipInterior, MelSorted, MelSound, MelSoundClose, MelSoundLooping, \
    MelString, MelStruct, MelTruncatedStruct, MelUInt8, MelUInt8Flags, \
    MelUInt16, MelUInt32, MelUInt32Flags, MelUnion, MelValueWeight, \
    MelWeight, MelWorldBounds, MelWthrColors, MelXlod, PartialLoadDecider, \
    SpellFlags, attr_csv_struct, color_attrs, null2, null4, MelMgefEdidTes4, \
    AMgefFlagsTes4, MelNpcClass, MelAIPackages, MelInheritsSoundsFrom, \
    PackGeneralOldFlags, MelPackScheduleOld, AMreRegn, MelColor, \
    MelWorldspace, MelRegnAreas, MelRegnRdat, MelRegnEntryObjects, \
    MelRegnEntrySoundsOld, MelRegnEntryWeatherTypes, MelRegnEntryGrasses, \
    MelRegnEntryMapName

#------------------------------------------------------------------------------
# Record Elements -------------------------------------------------------------
#------------------------------------------------------------------------------
class MelModel(MelGroup):
    """Represents a model subrecord."""
    typeSets = {
        b'MODL': (b'MODL', b'MODB', b'MODT'),
        b'MOD2': (b'MOD2', b'MO2B', b'MO2T'),
        b'MOD3': (b'MOD3', b'MO3B', b'MO3T'),
        b'MOD4': (b'MOD4', b'MO4B', b'MO4T'),
    }

    def __init__(self, mel_sig=b'MODL', attr='model'):
        types = self.__class__.typeSets[mel_sig]
        super().__init__(attr,
            MelString(types[0], 'modPath'),
            MelFloat(types[1], 'modb'),
            MelBase(types[2], 'modt_p') # Texture File Hashes
        )

#------------------------------------------------------------------------------
# Common Flags
class ServiceFlags(Flags):
    weapons: bool = flag(0)
    armor: bool = flag(1)
    clothing: bool = flag(2)
    books: bool = flag(3)
    ingredients: bool = flag(4)
    lights: bool = flag(7)
    apparatus: bool = flag(8)
    miscItems: bool = flag(10)
    spells: bool = flag(11)
    magicItems: bool = flag(12)
    potions: bool = flag(13)
    training: bool = flag(14)
    recharge: bool = flag(16)
    repair: bool = flag(17)

#------------------------------------------------------------------------------
# A distributor config for use with MelEffectsTes4, since MelEffectsTes4 also
# contains a FULL subrecord
_effects_distributor = {
    b'FULL': 'full', # don't rely on EDID being present
    b'EFID': {
        b'FULL': 'effects',
    },
    b'EFXX': {
        b'FULL': 'obme_full',
    },
}

#------------------------------------------------------------------------------
class MelAidt(MelStruct):
    """Handles the CREA/NPC_ subrecord AIDT (AI Data)."""
    def __init__(self):
        super().__init__(b'AIDT', ['4B', 'I', 'b', 'B', '2s'], 'ai_aggression',
            'ai_confidence', 'ai_energy_level', 'ai_responsibility',
            (ServiceFlags, 'ai_service_flags'), 'ai_train_skill',
            'ai_train_level', 'ai_unused')

#------------------------------------------------------------------------------
class MelEmbeddedScript(MelSequential):
    """Handles an embedded script, a SCHR/SCDA/SCTX/SLSD/SCVR/SCRO/SCRV
    subrecord combo. SLSD and SCVR can optionally be disabled."""
    def __init__(self, with_script_vars=False):
        ##: is_required below added for the create_record call in ScriptText.
        # _additional_processing - we should instead assign required fields there
        seq_elements = [
            MelUnion({
                b'SCHR': MelStruct(b'SCHR', ['4s', '4I'], 'unused1',
                                   'num_refs', 'compiled_size', 'last_index',
                                   'script_type', is_required=True),
                b'SCHD': MelBase(b'SCHD', 'old_script_header'),
            }),
            MelBase(b'SCDA', 'compiled_script'),
            MelString(b'SCTX', 'script_source'),
            MelReferences(), # MelScriptVars goes before here (index 3)
        ]
        if with_script_vars: seq_elements.insert(3, MelScriptVars())
        super(MelEmbeddedScript, self).__init__(*seq_elements)

#------------------------------------------------------------------------------
class MelItems(AMelItems):
    """Handles the CNTO subrecords defining items."""
    def __init__(self):
        super().__init__(with_coed=False, with_counter=False)

#------------------------------------------------------------------------------
##: Old format might be h2sI instead, which would retire this whole class
class MelLevListLvlo(MelTruncatedStruct):
    """Older format skips unused1, which is in the middle of the record."""
    def _pre_process_unpacked(self, unpacked_val):
        if len(unpacked_val) == 2:
            # Pad it in the middle, then let our parent deal with the rest
            unpacked_val = (unpacked_val[0], null2, unpacked_val[1])
        return super()._pre_process_unpacked(unpacked_val)

#------------------------------------------------------------------------------
class MelLLItems(AMelLLItems):
    """Handles the LVLO subrecords defining leveled list entries."""
    def __init__(self):
        super().__init__(MelLevListLvlo(b'LVLO', ['h', '2s', 'I', 'h', '2s'],
            'level', 'unused1', (FID, 'listId'), ('count', 1), 'unused2',
            old_versions={'iI'}), with_coed=False, with_counter=False)

#------------------------------------------------------------------------------
class MelOwnershipTes4(MelOwnership):
    """Handles XOWN, XRNK, and XGLB for cells and cell children."""
    def __init__(self, attr='ownership'):
        super(MelOwnership, self).__init__(attr,
            MelFid(b'XOWN', 'owner'),
            MelSInt32(b'XRNK', 'rank'),
            MelFid(b'XGLB', 'global'),
        )

#------------------------------------------------------------------------------
class MelSpellsTes4(MelSimpleGroups): ##: HACKy workaround, see docstring
    """Handles the common SPLO subrecord. This is a workaround to fix Oblivion
    hanging on load in some edge cases. The CS does some sort of processing or
    sorting to SPLOs that we don't fully understand yet. All we know for sure
    so far is that it always seems to put SPLOs that link to LVSPs after ones
    that link to SPELs, and we can't handle that without loading the plugin's
    masters (see #282 and #577 for two issues that need this as well). So we
    don't sort yet, that way it can't really be *our* fault when it hangs."""
    def __init__(self):
        super().__init__('spells', MelFid(b'SPLO'))

#------------------------------------------------------------------------------
class _AMreLeveledListTes4(AMreLeveledList):
    """The leveled list subrecords LVLD and LVLF require special handling in
    Oblivion. This has to be done after all subrecords are loaded, since those
    two subrecords can be out of order in some plugins.

    See also wbLVLAfterLoad in xEdit's wbDefinitionsTES4.pas."""
    lvl_chance_none: int

    def loadData(self, ins, endPos, *, file_offset=0):
        super().loadData(ins, endPos, file_offset=file_offset)
        if self.lvl_chance_none >= 128:
            self.flags.calc_from_all_levels = True
            self.lvl_chance_none -= 128

#------------------------------------------------------------------------------
##: Could technically be reworked for non-Oblivion games, but is broken and
# unused outside of Oblivion right now - for actor values in particular see
# FO3/FNV: https://geck.bethsoft.com/index.php?title=Actor_Value_Codes
# TES5: https://en.uesp.net/wiki/Tes5Mod:Actor_Value_Indices
actor_values = [ # Human-readable names for each actor value
    _('Strength'), #--00
    _('Intelligence'),
    _('Willpower'),
    _('Agility'),
    _('Speed'),
    _('Endurance'),
    _('Personality'),
    _('Luck'),
    _('Health'),
    _('Magicka'),
    _('Fatigue'), #--10
    _('Encumbrance'),
    _('Armorer'),
    _('Athletics'),
    _('Blade'),
    _('Block'),
    _('Blunt'),
    _('Hand To Hand'),
    _('Heavy Armor'),
    _('Alchemy'),
    _('Alteration'), #--20
    _('Conjuration'),
    _('Destruction'),
    _('Illusion'),
    _('Mysticism'),
    _('Restoration'),
    _('Acrobatics'),
    _('Light Armor'),
    _('Marksman'),
    _('Mercantile'),
    _('Security'), #--30
    _('Sneak'),
    _('Speechcraft'),
    'Aggression', # TODO(inf) Why do the translations stop here??
    'Confidence',
    'Energy',
    'Responsibility',
    'Bounty',
    'UNKNOWN 38',
    'UNKNOWN 39',
    'MagickaMultiplier', #--40
    'NightEyeBonus',
    'AttackBonus',
    'DefendBonus',
    'CastingPenalty',
    'Blindness',
    'Chameleon',
    'Invisibility',
    'Paralysis',
    'Silence',
    'Confusion', #--50
    'DetectItemRange',
    'SpellAbsorbChance',
    'SpellReflectChance',
    'SwimSpeedMultiplier',
    'WaterBreathing',
    'WaterWalking',
    'StuntedMagicka',
    'DetectLifeRange',
    'ReflectDamage',
    'Telekinesis', #--60
    'ResistFire',
    'ResistFrost',
    'ResistDisease',
    'ResistMagic',
    'ResistNormalWeapons',
    'ResistParalysis',
    'ResistPoison',
    'ResistShock',
    'Vampirism',
    'Darkness', #--70
    'ResistWaterDamage',
]

_ATTRIB = re.escape(_('Attribute'))
_SKILL = re.escape(_('Skill'))
_ATTRIB_SKILL_REGEX = re.compile(f'(?:{_ATTRIB}|{_SKILL})')

class MreHasEffects(MelRecord):
    """Mixin class for magic items."""
    _recipient_number_name = {None: 'NONE', 0: 'Self', 1: 'Touch', 2: 'Target'}
    _recipient_name_number = {y.lower(): x for x, y in
                              _recipient_number_name.items() if x is not None}
    _actor_val_number_name = {x: y for x, y in enumerate(actor_values)}
    _actor_val_name_number = {y.lower(): x for x, y
                              in _actor_val_number_name.items()}
    _actor_val_number_name[None] = 'NONE'
    _school_number_name = {None: 'NONE', 0: 'Alteration', 1: 'Conjuration',
                           2: 'Destruction', 3: 'Illusion', 4: 'Mysticism',
                           5: 'Restoration'}
    _school_name_number = {y.lower(): x for x, y in _school_number_name.items()
                           if x is not None}
    # Add 'effects/script_fid' to attr_csv_struct (column headers are tuples!)
    _effect_headers = (
        _('Effect'), _('Name'), _('Magnitude'), _('Area'), _('Duration'),
        _('Range'), _('Actor Value'), _('SE Mod Name'), _('SE ObjectIndex'),
        _('SE school'), _('SE visual'), _('SE Is Hostile'), _('SE Name'))
    _effect_headers = (
        *_effect_headers * 2, _('Additional Effects (Same format)'))
    attr_csv_struct['effects'] = [None, _effect_headers, lambda val:
        MreHasEffects._write_effects(val)[1:]] # chop off the first comma...
    attr_csv_struct['script_fid'] = [None, (_('Script Mod Name'),
        _('Script ObjectIndex')), lambda val: '"None","None"' if val is None
            else f'"{val.mod_fn}","0x{val.object_dex:06X}"']
    # typing to silence IDE's warnings - move to pyi stubs!
    effects: list

    @classmethod
    def parse_csv_line(cls, csv_fields, index_dict, reuse=False):
        effects_tuple = index_dict.pop('effects', None)
        attr_dex = super().parse_csv_line(csv_fields, index_dict, reuse)
        if effects_tuple is not None:
            effects_start, coerce_fid = effects_tuple
            attr_dex['effects'] = cls._read_effects(csv_fields[effects_start:],
                                                    coerce_fid)
            if not reuse:
                index_dict['effects'] = effects_tuple
        return attr_dex

    def getEffects(self):
        """Returns a summary of effects. Useful for alchemical catalog."""
        return [(mgef := effect.effect_sig,
            effect.actorValue if mgef in MreMgef.generic_av_effects else 0)
                for effect in self.effects]

    def _get_spell_school(self):
        """Returns the school based on the highest cost spell effect."""
        spellSchool = [0, 0]
        for effect in self.effects:
            school = MreMgef.mgef_school[effect.effect_sig]
            effectValue = MreMgef.mgef_basevalue[effect.effect_sig]
            if effect.magnitude:
                effectValue *= effect.magnitude
            if effect.area:
                effectValue *= (effect.area // 10)
            if effect.duration:
                effectValue *= effect.duration
            if spellSchool[0] < effectValue:
                spellSchool = [effectValue,school]
        return spellSchool[1]

    def getEffectsSummary(self):
        """Return a text description of magic effects."""
        buff = []
        avEffects = MreMgef.generic_av_effects
        aValues = actor_values
        buffWrite = buff.append
        if self.effects:
            school = self._get_spell_school()
            buffWrite(f'{aValues[20 + school]}\n')
        for index, effect in enumerate(self.effects):
            if effect.scriptEffect: ##: #480 - setDefault commit - return None
                effectName = effect.scriptEffect.full or 'Script Effect'
            else:
                effectName = MreMgef.mgef_name[effect.effect_sig]
                if effect.effect_sig in avEffects:
                    effectName = _ATTRIB_SKILL_REGEX.sub(
                        aValues[effect.actorValue], effectName)
            buffWrite('o+*'[effect.recipient] + f' {effectName}')
            if effect.magnitude: buffWrite(f' {effect.magnitude}m')
            if effect.area: buffWrite(f' {effect.area}a')
            if effect.duration > 1: buffWrite(f' {effect.duration}d')
            buffWrite('\n')
        return ''.join(buff)

    @classmethod
    def _read_effects(cls, _effects, _coerce_fid, *,
                      __packer=structs_cache['I'].pack):
        schoolTypeName_Number = cls._school_name_number
        recipientTypeName_Number = cls._recipient_name_number
        actorValueName_Number = cls._actor_val_name_number
        effects_list = []
        while len(_effects) >= 13:
            _effect,_effects = _effects[1:13],_effects[13:]
            eff_name, magnitude, area, duration, range_, actorvalue, semod, \
                seobj, seschool, sevisual, se_hostile, sename = _effect
            eff_name = str_or_none(eff_name) #OBME not supported
            # (support requires adding a mod/objectid format to the
            # csv, this assumes all MGEFCodes are raw)
            magnitude, area, duration = map(int_or_none,
                                            (magnitude, area, duration))
            range_ = str_or_none(range_)
            if range_:
                range_ = recipientTypeName_Number.get(range_.lower(),
                                                      int_or_zero(range_))
            actorvalue = str_or_none(actorvalue)
            if actorvalue:
                actorvalue = actorValueName_Number.get(actorvalue.lower(),
                                                       int_or_zero(actorvalue))
            if None in (eff_name,magnitude,area,duration,range_,actorvalue):
                continue
            eff = cls.getDefault('effects')
            effects_list.append(eff)
            eff.effect_sig = str_to_sig(eff_name)
            eff.magnitude = magnitude
            eff.area = area
            eff.duration = duration
            eff.recipient = range_
            eff.actorValue = actorvalue
            # script effect
            semod = str_or_none(semod)
            if semod is None or not seobj.startswith('0x'):
                continue
            se_hostile = str_or_none(se_hostile)
            if se_hostile is None:
                continue
            seschool = str_or_none(seschool)
            if seschool:
                seschool = schoolTypeName_Number.get(seschool.lower(),
                                                     int_or_zero(seschool))
            seflags = MelEffectsTes4.se_flags(0)
            seflags.hostile = se_hostile.lower() == 'true'
            sename = str_or_none(sename)
            if None in (seschool, sename):
                continue
            eff.scriptEffect = se = cls.getDefault('effects.scriptEffect')
            se.full = sename
            se.script_fid = _coerce_fid(semod, seobj)
            se.school = seschool
            # OBME not supported (support requires adding a mod/objectid format
            # to the csv, this assumes visual MGEFCode is raw)
            sevisuals = int_or_none(sevisual)
            if sevisuals is None: # it was no int try to read unicode MGEF Code
                sevisuals = str_or_none(sevisual)
                sevisuals = str_to_sig(sevisuals) if sevisuals else null4
            else: # pack int to bytes
                sevisuals = __packer(sevisuals)
            sevisual = sevisuals
            se.visual = sevisual
            se.flags = seflags
        return effects_list

    @classmethod
    def _write_effects(cls, effects):
        schoolTypeNumber_Name = cls._school_number_name
        recipientTypeNumber_Name = cls._recipient_number_name
        actorValueNumber_Name = cls._actor_val_number_name
        output = []
        for effect in effects:
            efname, magnitude, area, duration, range_, actorvalue = \
                sig_to_str(effect.effect_sig), effect.magnitude, effect.area, \
                effect.duration, effect.recipient, effect.actorValue
            range_ = recipientTypeNumber_Name.get(range_,range_)
            actorvalue = actorValueNumber_Name.get(actorvalue,actorvalue)
            output.append(f',,"{efname}","{magnitude:d}","{area:d}",'
                          f'"{duration:d}","{range_}","{actorvalue}"')
            if effect.scriptEffect: ##: #480 - setDefault commit - return None
                se = effect.scriptEffect
                longid, seschool, sevisual, seflags, sename = \
                    se.script_fid, se.school, se.visual, se.flags, se.full
                sevisual = 'NONE' if sevisual == null4 else sig_to_str(
                    sevisual)
                seschool = schoolTypeNumber_Name.get(seschool,seschool)
                output.append(
                    f',"{longid.mod_fn}","0x{longid.object_dex:06X}",'
                    f'"{seschool}","{sevisual}","{bool(int(seflags))}",'
                    f'"{sename}"')
            else:
                output.append(',"None","None","None","None","None","None"')
        return ''.join(output)

    # Tweaks APIs -------------------------------------------------------------
    def is_harmful(self, cached_hostile):
        """Return True if all the effects on the specified record are
        harmful/hostile."""
        for rec_eff in self.effects:
            is_effect_hostile = se.flags.hostile if (se := rec_eff.scriptEffect
                ) else rec_eff.effect_sig in cached_hostile
            if not is_effect_hostile:
                return False
        return True

    def get_spell_school(self, tweak_mgef_school=None): # param unused in Oblivion
        if self.effects:
            first_eff = self.effects[0]
            school = se.school if (se := first_eff.scriptEffect) else \
                MreMgef.mgef_school.get(first_eff.effect_sig, 6)
            return 'ACDIMRU'[school]
        return 'U' # default to 'U' (unknown)

    def get_spell_level(self):
        """Return the level for this spell as an integer:
          0: Novice
          1: Apprentice
          2: Journeyman
          3: Expert
          4: Master
        """
        return self.level

#------------------------------------------------------------------------------
# Oblivion Records ------------------------------------------------------------
#------------------------------------------------------------------------------
class MreTes4(AMreHeader):
    """TES4 Record.  File header."""
    rec_sig = b'TES4'
    _post_masters_sigs = set()
    next_object_default = 0x800

    melSet = MelSet(
        MelStruct(b'HEDR', ['f', '2I'], ('version', 1.0), 'numRecords',
                  ('nextObject', next_object_default), is_required=True),
        MelNull(b'OFST'), # obsolete
        MelNull(b'DELE'), # obsolete
        AMreHeader.MelAuthor(),
        AMreHeader.MelDescription(),
        AMreHeader.MelMasterNames(),
    )

#------------------------------------------------------------------------------
class MreAchr(MelRecord):
    """Placed NPC."""
    rec_sig = b'ACHR'

    melSet = MelSet(
        MelEdid(),
        MelFid(b'NAME', 'base'),
        # both unused
        MelNull(b'XPCI'),
        MelNull(b'FULL'),
        MelXlod(),
        MelEnableParent(),
        MelFid(b'XMRC', 'merchantContainer'),
        MelFid(b'XHRS', 'horse'),
        MelBase(b'XRGD', 'xrgd_p'), # Ragdoll Data, bytearray
        MelRefScale(),
        MelRef3D(),
    )

#------------------------------------------------------------------------------
class MreAcre(MelRecord):
    """Placed Creature."""
    rec_sig = b'ACRE'

    melSet = MelSet(
        MelEdid(),
        MelFid(b'NAME', 'base'),
        MelOwnershipTes4(),
        MelBase(b'XRGD', 'xrgd_p'), # Ragdoll Data, bytearray
        MelXlod(),
        MelEnableParent(),
        MelRefScale(),
        MelRef3D(),
    )

#------------------------------------------------------------------------------
class MreActi(MelRecord):
    """Activator."""
    rec_sig = b'ACTI'

    melSet = MelSet(
        MelEdid(),
        MelFull(),
        MelModel(),
        MelScript(),
        MelSound(),
    )

#------------------------------------------------------------------------------
class _ObIcon(MelRecord):
    _default_icons = None

    def can_set_icon(self):
        """Return True if we *can* tweak this record's icon."""
        return not self.iconPath

    def set_default_icon(self):
        self.iconPath = self._default_icons

class MreAlch(MreHasEffects, _ObIcon):
    """Potion."""
    rec_sig = b'ALCH'
    _default_icons = 'Clutter\\Potions\\IconPotion01.dds'

    class _AlchFlags(Flags):
        alch_auto_calc: bool
        alch_is_food: bool

    melSet = MelSet(
        MelEdid(),
        MelObme(),
        MelFull(),
        MelModel(),
        MelIcon(),
        MelScript(),
        MelWeight(),
        MelStruct(b'ENIT', ['i', 'B', '3s'], 'value', (_AlchFlags, 'flags'),
                  'unused1'),
        MelEffectsTes4(),
        MelEffectsTes4ObmeFull(),
    ).with_distributor(_effects_distributor)

#------------------------------------------------------------------------------
class MreAmmo(_ObIcon):
    """Ammunition."""
    rec_sig = b'AMMO'
    _default_icons = 'Weapons\\IronArrow.dds'

    class _AmmoFlags(Flags):
        notNormalWeapon: bool

    melSet = MelSet(
        MelEdid(),
        MelFull(),
        MelModel(),
        MelIcon(),
        MelEnchantment(b'ENAM'),
        MelUInt16(b'ANAM', 'enchantPoints'),
        MelStruct(b'DATA', ['f', 'B', '3s', 'I', 'f', 'H'], 'speed',
                  (_AmmoFlags, 'flags'), 'unused1', 'value', 'weight',
                  'damage'),
    )

#------------------------------------------------------------------------------
class MreAnio(MelRecord):
    """Animated Object."""
    rec_sig = b'ANIO'

    melSet = MelSet(
        MelEdid(),
        MelModel(),
        MelFid(b'DATA', 'animationId'),
    )

#------------------------------------------------------------------------------
class MreAppa(_ObIcon):
    """Alchemical Apparatus."""
    rec_sig = b'APPA'
    _default_icons = 'Clutter\\IconMortarPestle.dds'

    melSet = MelSet(
        MelEdid(),
        MelFull(),
        MelModel(),
        MelIcon(),
        MelScript(),
        MelStruct(b'DATA', ['B', 'I', 'f', 'f'], 'apparatus', 'value',
                  'weight', 'quality'),
    )

#------------------------------------------------------------------------------
class _CommonBipedFlags(BipedFlags):
    head: bool
    hair: bool
    upperBody: bool
    lowerBody: bool
    hand: bool
    foot: bool
    rightRing: bool
    leftRing: bool
    amulet: bool
    weapon: bool
    backWeapon: bool
    sideWeapon: bool
    quiver: bool
    shield: bool
    torch: bool
    tail: bool

    _not_playable_flags = {'backWeapon', 'quiver', 'weapon', 'torch',
                           'rightRing', 'sideWeapon'}

class _ObPlayable(_ObIcon):
    not_playable_flag = ('biped_flags', 'notPlayable')
    maleIconPath: str
    femaleIconPath: str
    biped_flags: _CommonBipedFlags

    def can_set_icon(self):
        return not self.is_not_playable() and not self.maleIconPath and not \
            self.femaleIconPath

    def set_default_icon(self):
        # Choose based on body flags:
        body_flags = self.biped_flags
        if body_flags.upperBody:
            return self._default_icons[0]
        elif body_flags.lowerBody:
            return self._default_icons[1]
        elif body_flags.head or body_flags.hair:
            return self._default_icons[2]
        elif body_flags.hand:
            return self._default_icons[3]
        elif body_flags.foot:
            return self._default_icons[4]
        return None

class MreArmo(_ObPlayable):
    """Armor."""
    rec_sig = b'ARMO'
    _default_icons = (
        ['Armor\\Iron\\M\\Cuirass.dds', 'Armor\\Iron\\F\\Cuirass.dds'],
        ['Armor\\Iron\\M\\Greaves.dds', 'Armor\\Iron\\F\\Greaves.dds'],
        ['Armor\\Iron\\M\\Helmet.dds'],
        ['Armor\\Iron\\M\\Gauntlets.dds', 'Armor\\Iron\\F\\Gauntlets.dds'],
        ['Armor\\Iron\\M\\Boots.dds'],
        ['Armor\\Iron\\M\\Shield.dds'],
        ['Armor\\Iron\\M\\Shield.dds'])  # Default Armor icon

    class _ArmoBipedFlags(_CommonBipedFlags):
        hideRings: bool = flag(16)
        hideAmulet: bool = flag(17)
        notPlayable: bool = flag(22)
        heavy_armor: bool = flag(23)

    melSet = MelSet(
        MelEdid(),
        MelFull(),
        MelScript(),
        MelEnchantment(b'ENAM'),
        MelUInt16(b'ANAM', 'enchantPoints'),
        MelUInt32Flags(b'BMDT', 'biped_flags', _ArmoBipedFlags),
        MelModel(b'MODL', 'maleBody'),
        MelModel(b'MOD2', 'maleWorld'),
        MelIcon('maleIconPath'),
        MelModel(b'MOD3', 'femaleBody'),
        MelModel(b'MOD4', 'femaleWorld'),
        MelIco2('femaleIconPath'),
        MelStruct(b'DATA', ['H', 'I', 'I', 'f'], 'strength', 'value', 'health',
                  'weight'),
    )

    def set_default_icon(self):
        if not(ic := super().set_default_icon()):
            ic = self._default_icons[5 if self.biped_flags.shield else
                6] # Default icon, probably a token or somesuch
        for att, val in zip(('maleIconPath', 'femaleIconPath'), ic):
            setattr(self, att, val)

#------------------------------------------------------------------------------
class _RandIco(_ObIcon):
    def set_default_icon(self):
        # Just a random book icon - for class/birthsign as well.
        random.seed(self.fid.object_dex) # make it deterministic
        self.iconPath = f'Clutter\\iconbook{random.randint(1, 13):d}.dds'

class MreBook(_RandIco):
    """Book."""
    rec_sig = b'BOOK'

    class _BookFlags(Flags):
        isScroll: bool
        isFixed: bool

    melSet = MelSet(
        MelEdid(),
        MelFull(),
        MelModel(),
        MelIcon(),
        MelBookText(),
        MelScript(),
        MelEnchantment(b'ENAM'),
        MelUInt16(b'ANAM', 'enchantPoints'),
        MelStruct(b'DATA', ['B', 'b', 'I', 'f'], (_BookFlags, 'flags'),
                  'teaches', 'value', 'weight'),
    )

#------------------------------------------------------------------------------
class MreBsgn(_RandIco):
    """Birthsign."""
    rec_sig = b'BSGN'

    melSet = MelSet(
        MelEdid(),
        MelFull(),
        MelIcon(),
        MelDescription(),
        MelSpellsTes4(),
    )

#------------------------------------------------------------------------------
class MreCell(AMreCell):
    """Cell."""
    ref_types = {b'ACHR', b'ACRE', b'REFR'}
    interior_temp_extra = [b'PGRD']

    class _CellFlags(Flags):
        isInterior: bool = flag(0)
        hasWater: bool = flag(1)
        invertFastTravel: bool = flag(2)
        forceHideLand: bool = flag(3)
        publicPlace: bool = flag(5)
        handChanged: bool = flag(6)
        behaveLikeExterior: bool = flag(7)

    melSet = MelSet(
        MelEdid(),
        MelFull(),
        MelUInt8Flags(b'DATA', 'flags', _CellFlags, is_required=True),
        MelSkipInterior(MelStruct(b'XCLC', ['2i'], 'posX', 'posY')),
        MelStruct(b'XCLL', ['3B', 's', '3B', 's', '3B', 's', '2f', '2i', '2f'],
            'ambientRed', 'ambientGreen', 'ambientBlue', 'unused1',
            'directionalRed', 'directionalGreen', 'directionalBlue', 'unused2',
            'fogRed', 'fogGreen', 'fogBlue', 'unused3', 'fogNear', 'fogFar',
            'directionalXY', 'directionalZ', 'directionalFade', 'fogClip'),
        MelRegions(),
        MelUInt8(b'XCMT', 'music'),
        MelFloat(b'XCLW', 'waterHeight'),
        MelFid(b'XCCM', 'climate'),
        MelFid(b'XCWT', 'water'),
        MelOwnershipTes4(),
    )

#------------------------------------------------------------------------------
class MreClas(_RandIco):
    """Class."""
    rec_sig = b'CLAS'

    class _ClasFlags(Flags):
        class_playable: bool
        class_guard: bool

    melSet = MelSet(
        MelEdid(),
        MelFull(),
        MelDescription(),
        MelIcon(),
        MelTruncatedStruct(b'DATA', ['2i', 'I', '7i', '2I', 'b', 'B', '2s'],
            'primary1', 'primary2', 'specialization', 'major1', 'major2',
            'major3', 'major4', 'major5', 'major6', 'major7',
            (_ClasFlags, 'flags'), (ServiceFlags, 'class_service_flags'),
            'class_train_skill', 'class_train_level', 'unused1',
            old_versions={'2iI7i2I'}),
    )

#------------------------------------------------------------------------------
class MreClmt(MelRecord):
    """Climate."""
    rec_sig = b'CLMT'

    melSet = MelSet(
        MelEdid(),
        MelClmtWeatherTypes(with_global=False),
        MelClmtTextures(),
        MelModel(),
        MelClmtTiming(),
    )

#------------------------------------------------------------------------------
class MreClot(_ObPlayable):
    """Clothing."""
    rec_sig = b'CLOT'
    _default_icons = 'Clothes\\MiddleClass\\01\\%s.dds' # to wrap better
    _default_icons = (
        (_default_icons % 'M\\Shirt', _default_icons % 'F\\Shirt'),
        (_default_icons % 'M\\Pants', _default_icons % 'F\\Pants'),
        ('Clothes\\MythicDawnrobe\\hood.dds',),
        ('Clothes\\LowerClass\\Jail\\M\\JailShirtHandcuff.dds',),
        (_default_icons % 'M\\Shoes', _default_icons % 'F\\Shoes'),
        ('Clothes\\Ring\\RingNovice.dds',),
        ('Clothes\\Amulet\\AmuletSilver.dds',)
    )

    class _ClotBipedFlags(_CommonBipedFlags):
        hideRings: bool = flag(16)
        hideAmulet: bool = flag(17)
        notPlayable: bool = flag(22)

    melSet = MelSet(
        MelEdid(),
        MelFull(),
        MelScript(),
        MelEnchantment(b'ENAM'),
        MelUInt16(b'ANAM', 'enchantPoints'),
        MelUInt32Flags(b'BMDT', 'biped_flags', _ClotBipedFlags),
        MelModel(b'MODL', 'maleBody'),
        MelModel(b'MOD2', 'maleWorld'),
        MelIcon('maleIconPath'),
        MelModel(b'MOD3', 'femaleBody'),
        MelModel(b'MOD4', 'femaleWorld'),
        MelIco2('femaleIconPath'),
        MelValueWeight(),
    )

    def set_default_icon(self):
        if not(ic := super().set_default_icon()):
            ring = self.biped_flags.leftRing or self.biped_flags.rightRing
            ic = self._default_icons[5 if ring else 6]
        for att, val in zip(('maleIconPath', 'femaleIconPath'), ic):
            setattr(self, att, val)

#------------------------------------------------------------------------------
class MreCont(AMreWithItems):
    """Container."""
    rec_sig = b'CONT'

    melSet = MelSet(
        MelEdid(),
        MelFull(),
        MelModel(),
        MelScript(),
        MelItems(),
        MelContData(),
        MelSound(),
        MelSoundClose(),
    )

#------------------------------------------------------------------------------
class MreCrea(AMreActor):
    """Creature."""
    rec_sig = b'CREA'

    class _CreaFlags(Flags):
        crea_biped: bool = flag(0)
        crea_essential: bool = flag(1)
        weapon_and_shield: bool = flag(2)
        crea_respawn: bool = flag(3)
        crea_swims: bool = flag(4)
        crea_flies: bool = flag(5)
        crea_walks: bool = flag(6)
        pc_level_offset: bool = flag(7)
        no_low_level: bool = flag(9)
        crea_no_blood_spray: bool = flag(11)
        crea_no_blood_decal: bool = flag(12)
        no_head: bool = flag(15)
        no_right_arm: bool = flag(16)
        no_left_arm: bool = flag(17)
        crea_no_combat_in_water: bool = flag(18)
        crea_no_shadow: bool = flag(19)
        no_corpse_check: bool = flag(20)

    melSet = MelSet(
        MelEdid(),
        MelFull(),
        MelModel(),
        MelItems(),
        MelSpellsTes4(),
        MelBodyParts(),
        MelBase(b'NIFT', 'model_list_textures'), # Texture File Hashes
        MelStruct(b'ACBS', ['I', '3H', 'h', '2H'],
            (_CreaFlags, 'crea_flags'), 'base_spell', 'fatigue', 'barter_gold',
            'level_offset', 'calc_min_level', 'calc_max_level'),
        MelFactions(with_unused=True),
        MelDeathItem(),
        MelScript(),
        MelAidt(),
        MelAIPackages(),
        MelAnimations(),
        MelStruct(b'DATA', ['5B', 's', 'H', '2s', 'H', '8B'], 'creature_type',
                  'combat_skill', 'magic', 'stealth', 'soul', 'unused2',
                  'health', 'unused3', 'attackDamage', 'strength',
                  'intelligence', 'willpower', 'agility', 'speed', 'endurance',
                  'personality', 'luck'),
        MelUInt8(b'RNAM', 'attack_reach'),
        MelCombatStyle(),
        MelFloat(b'TNAM', 'turning_speed'),
        MelFloat(b'BNAM', 'base_scale'),
        MelFloat(b'WNAM', 'foot_weight'),
        MelString(b'NAM0', 'blood_spray_path'),
        MelString(b'NAM1', 'blood_decal_path'),
        MelInheritsSoundsFrom(),
        MelActorSounds(),
    )

#------------------------------------------------------------------------------
class MreCsty(MelRecord):
    """Combat Style."""
    rec_sig = b'CSTY'

    class _CstyFlags1(Flags):
        advanced: bool
        use_chance_for_attack: bool
        ignore_allies: bool
        will_yield: bool
        rejects_yields: bool
        fleeing_disabled: bool
        prefers_ranged: bool
        melee_alert_ok: bool

    class _CstyFlags2(Flags):
        do_not_acquire: bool

    melSet = MelSet(
        MelEdid(),
        MelTruncatedStruct(b'CSTD',
            ['2B', '2s', '8f', '2B', '2s', '3f', 'B', '3s', '2f', '5B', '3s',
             '2f', '2B', '2s', '7f', 'B', '3s', 'f', 'I'], 'dodge_chance',
            'lr_chance', 'unused1', 'lr_timer_min', 'lr_timer_max',
            'for_timer_min', 'for_timer_max', 'back_timer_min',
            'back_timer_max', 'idle_timer_min', 'idle_timer_max', 'blk_chance',
            'atk_chance', 'unused2', 'atk_brecoil', 'atk_bunc', 'atk_bh_2_h',
            'p_atk_chance', 'unused3', 'p_atk_brecoil', 'p_atk_bunc',
            'p_atk_normal', 'p_atk_for', 'p_atk_back', 'p_atk_l', 'p_atk_r',
            'unused4', 'hold_timer_min', 'hold_timer_max',
            (_CstyFlags1, 'csty_flags1'), 'acro_dodge', 'unused5',
            'r_mult_opt', 'r_mult_max', 'm_distance', 'r_distance',
            'buff_stand', 'r_stand', 'group_stand', 'rush_chance', 'unused6',
            'rush_mult', (_CstyFlags2, 'csty_flags2'), old_versions={
                '2B2s8f2B2s3fB3s2f5B3s2f2B2s7fB3sf',
                '2B2s8f2B2s3fB3s2f5B3s2f2B2s7f',
                '2B2s8f2B2s3fB3s2f5B3s2f2B2s5f',
                '2B2s8f2B2s3fB3s2f5B3s2f2B2s2f',
                '2B2s8f2B2s3fB3s2f5B3s2f2B2s',
            }),
        MelStruct(b'CSAD', ['21f'], 'dodge_fmult', 'dodge_fbase', 'enc_sbase',
            'enc_smult', 'dodge_atk_mult', 'dodge_natk_mult',
            'dodge_batk_mult', 'dodge_bnatk_mult', 'dodge_fatk_mult',
            'dodge_fnatk_mult', 'block_mult', 'block_base', 'block_atk_mult',
            'block_natk_mult', 'atk_mult', 'atk_base', 'atk_atk_mult',
            'atk_natk_mult', 'atk_block_mult', 'p_atk_fbase', 'p_atk_fmult'),
        )

#------------------------------------------------------------------------------
class MreDial(MelRecord):
    """Dialogue."""
    rec_sig = b'DIAL'

    @classmethod
    def nested_records_sigs(cls):
        return {b'INFO'}

    melSet = MelSet(
        MelEdid(),
        MelSorted(MelSimpleGroups('added_quests', MelFid(b'QSTI'))),
        MelSorted(MelSimpleGroups('removed_quests', MelFid(b'QSTR'))),
        MelFull(),
        MelUInt8(b'DATA', 'dialType'),
    )

#------------------------------------------------------------------------------
class MreDoor(MelRecord):
    """Door."""
    rec_sig = b'DOOR'

    melSet = MelSet(
        MelEdid(),
        MelFull(),
        MelModel(),
        MelScript(),
        MelSound(),
        MelSoundClose(b'ANAM'),
        MelSoundLooping(),
        MelDoorFlags(),
        MelRandomTeleports(),
    )

#------------------------------------------------------------------------------
class MreEfsh(MelRecord):
    """Effect Shader."""
    rec_sig = b'EFSH'

    class _EfshFlags(Flags):
        no_membrane_shader: bool = flag(0)
        no_particle_shader: bool = flag(3)
        ee_inverse: bool = flag(4)
        affect_skin_only: bool = flag(5)

    melSet = MelSet(
        MelEdid(),
        MelIcon('fill_texture'),
        MelIco2('particle_texture'),
        MelTruncatedStruct(b'DATA',
            ['B', '3s', '3I', '3B', 's', '9f', '3B', 's', '8f', '5I', '19f',
             '3B', 's', '3B', 's', '3B', 's', '6f'],
            (_EfshFlags, 'efsh_flags'), 'unused1', 'ms_source_blend_mode',
            'ms_blend_operation', 'ms_z_test_function',
            *color_attrs('fill_color1'), 'fill_alpha_fade_in_time',
            'fill_full_alpha_time', 'fill_alpha_fade_out_time',
            'fill_persistent_alpha_ratio', 'fill_alpha_pulse_amplitude',
            'fill_alpha_pulse_frequency', 'fill_texture_animation_speed_u',
            'fill_texture_animation_speed_v', 'ee_fall_off',
            *color_attrs('ee_color'), 'ee_alpha_fade_in_time',
            'ee_full_alpha_time', 'ee_alpha_fade_out_time',
            'ee_persistent_alpha_ratio', 'ee_alpha_pulse_amplitude',
            'ee_alpha_pulse_frequency', 'fill_full_alpha_ratio',
            'ee_full_alpha_ratio', 'ms_dest_blend_mode',
            'ps_source_blend_mode', 'ps_blend_operation', 'ps_z_test_function',
            'ps_dest_blend_mode', 'ps_particle_birth_ramp_up_time',
            'ps_full_particle_birth_time', 'ps_particle_birth_ramp_down_time',
            'ps_full_particle_birth_ratio',
            'ps_persistent_particle_birth_ratio', 'ps_particle_lifetime',
            'ps_particle_lifetime_delta',
            'ps_initial_speed_along_normal', 'ps_acceleration_along_normal',
            'ps_initial_velocity1', 'ps_initial_velocity2',
            'ps_initial_velocity3', 'ps_acceleration1', 'ps_acceleration2',
            'ps_acceleration3', 'ps_scale_key1', 'ps_scale_key2',
            'ps_scale_key1_time', 'ps_scale_key2_time',
            *color_attrs('color_key1', rename_alpha=True),
            *color_attrs('color_key2', rename_alpha=True),
            *color_attrs('color_key3', rename_alpha=True), 'color_key1_alpha',
            'color_key2_alpha', 'color_key3_alpha', 'color_key1_time',
            'color_key2_time', 'color_key3_time',
            old_versions={'B3s3I3Bs9f3Bs8fI'}),
    )

#------------------------------------------------------------------------------
class MreEnch(MreHasEffects, MelRecord):
    """Enchantment."""
    rec_sig = b'ENCH'

    class _EnitFlags(Flags):
        ench_no_auto_calc: bool

    melSet = MelSet(
        MelEdid(),
        MelObme(),
        MelFull(), #--At least one mod has this. Odd.
        MelStruct(b'ENIT', ['3I', 'B', '3s'], 'item_type', 'charge_amount',
            'enchantment_cost', (_EnitFlags, 'enit_flags'), 'unused1'),
        MelEffectsTes4(),
        MelEffectsTes4ObmeFull(),
    ).with_distributor(_effects_distributor)

#------------------------------------------------------------------------------
class MreFact(MelRecord):
    """Faction."""
    rec_sig = b'FACT'

    class _FactFlags(Flags):
        hidden_from_pc: bool
        evil: bool
        special_combat: bool

    melSet = MelSet(
        MelEdid(),
        MelFull(),
        MelRelations(with_gcr=False),
        MelUInt8Flags(b'DATA', 'fact_flags', _FactFlags),
        MelFloat(b'CNAM', 'crime_gold_multiplier'),
        MelFactRanks(),
    )

#------------------------------------------------------------------------------
class MreFlor(MelRecord):
    """Flora."""
    rec_sig = b'FLOR'

    melSet = MelSet(
        MelEdid(),
        MelFull(),
        MelModel(),
        MelScript(),
        MelIngredient(),
        MelSeasons(),
    )

#------------------------------------------------------------------------------
class MreFurn(MelRecord):
    """Furniture."""
    rec_sig = b'FURN'

    melSet = MelSet(
        MelEdid(),
        MelFull(),
        MelModel(),
        MelScript(),
        MelBase(b'MNAM', 'active_markers_flags'), # not decoded in xEdit
    )

#------------------------------------------------------------------------------
class MreGras(MelRecord):
    """Grass."""
    rec_sig = b'GRAS'

    melSet = MelSet(
        MelEdid(),
        MelModel(),
        MelGrasData(),
    )

#------------------------------------------------------------------------------
class MreGlob(AMreGlob):
    """Global."""

#------------------------------------------------------------------------------
class MreHair(MelRecord):
    """Hair."""
    rec_sig = b'HAIR'

    melSet = MelSet(
        MelEdid(),
        MelFull(),
        MelModel(),
        MelIcon(),
        MelHairFlags(),
    )

#------------------------------------------------------------------------------
class MreIdle(MelRecord):
    """Idle Animation."""
    rec_sig = b'IDLE'

    melSet = MelSet(
        MelEdid(),
        MelModel(),
        MelConditionsTes4(),
        MelUInt8(b'ANAM', 'animation_group_section'),
        MelIdleRelatedAnims(b'DATA'),
    )

#------------------------------------------------------------------------------
class MreInfo(MelRecord):
    """Dialog Response."""
    rec_sig = b'INFO'

    class _InfoResponseFlags(Flags):
        goodbye: bool
        random: bool
        say_once: bool
        run_immediately: bool
        info_refusal: bool
        random_end: bool
        run_for_rumors: bool

    melSet = MelSet(
        MelTruncatedStruct(b'DATA', ['3B'], 'info_type', 'next_speaker',
            (_InfoResponseFlags, 'response_flags'), old_versions={'2B'}),
        MelFid(b'QSTI', 'info_quest'),
        MelFid(b'TPIC', 'info_topic'),
        MelFid(b'PNAM', 'prev_info'),
        MelSimpleGroups('add_topics', MelFid(b'NAME')),
        MelGroups('info_responses',
            MelStruct(b'TRDT', ['I', 'i', '4s', 'B', '3s'], 'rd_emotion_type',
                'rd_emotion_value', 'rd_unused1', 'rd_response_number',
                'rd_unused2'),
            MelString(b'NAM1', 'response_text'),
            MelString(b'NAM2', 'script_notes'),
        ),
        MelConditionsTes4(),
        MelSimpleGroups('info_choices', MelFid(b'TCLT')),
        MelSimpleGroups('link_from', MelFid(b'TCLF')),
        MelEmbeddedScript(),
    )

#------------------------------------------------------------------------------
class MreIngr(MreHasEffects, _ObIcon):
    """Ingredient."""
    rec_sig = b'INGR'
    _default_icons = 'Clutter\\IconSeeds.dds'

    class _IngrFlags(Flags):
        ingr_no_auto_calc: bool
        ingr_is_food: bool

    melSet = MelSet(
        MelEdid(),
        MelObme(),
        MelFull(),
        MelModel(),
        MelIcon(),
        MelScript(),
        MelWeight(),
        MelStruct(b'ENIT', ['i', 'B', '3s'], 'value', (_IngrFlags, 'flags'),
                  'unused1'),
        MelEffectsTes4(),
        MelEffectsTes4ObmeFull(),
    ).with_distributor(_effects_distributor)

#------------------------------------------------------------------------------
class MreKeym(_ObIcon):
    """Key."""
    rec_sig = b'KEYM'
    _default_icons = ('Clutter\\Key\\Key.dds', 'Clutter\\Key\\Key02.dds')

    melSet = MelSet(
        MelEdid(),
        MelFull(),
        MelModel(),
        MelIcon(),
        MelScript(),
        MelValueWeight(),
    )

    def set_default_icon(self):
        random.seed(self.fid.object_dex)  # make it deterministic
        self.iconPath = self._default_icons[random.randint(0, 1)]

#------------------------------------------------------------------------------
class MreLand(MelRecord):
    """Landscape."""
    rec_sig = b'LAND'

    melSet = MelSet(
        MelLandShared(with_vtex=True),
    )

#------------------------------------------------------------------------------
class MreLigh(_ObIcon):
    """Light."""
    rec_sig = b'LIGH'
    _default_icons = 'Lights\\IconTorch02.dds'

    class _LighFlags(Flags):
        light_dynamic: bool = flag(0)
        light_can_take: bool = flag(1)
        light_negative: bool = flag(2)
        light_flickers: bool = flag(3)
        light_off_by_default: bool = flag(5)
        light_flickers_slow: bool = flag(6)
        light_pulses: bool = flag(7)
        light_pulses_slow: bool = flag(8)
        light_spot_light: bool = flag(9)
        light_shadow_spotlight: bool = flag(10)

    light_flags: _LighFlags

    melSet = MelSet(
        MelEdid(),
        MelModel(),
        MelScript(),
        MelFull(),
        MelIcon(),
        MelTruncatedStruct(b'DATA',
            ['i', 'I', '3B', 's', 'I', 'f', 'f', 'I', 'f'], 'duration',
            'light_radius', *color_attrs('light_color'),
            (_LighFlags, 'light_flags'), 'light_falloff', 'light_fov',
            'value', 'weight', old_versions={'iI3BsI2f'}),
        MelLighFade(),
        MelSound(),
    )

    def can_set_icon(self):
        return self.light_flags.light_can_take and super().can_set_icon()

#------------------------------------------------------------------------------
class MreLscr(MelRecord):
    """Load Screen."""
    rec_sig = b'LSCR'

    melSet = MelSet(
        MelEdid(),
        MelIcon(),
        MelDescription(),
        MelLscrLocations(),
    )

#------------------------------------------------------------------------------
class MreLtex(MelRecord):
    """Landscape Texture."""
    rec_sig = b'LTEX'

    melSet = MelSet(
        MelEdid(),
        MelIcon(),
        MelStruct(b'HNAM', ['3B'], 'hd_material_type', 'hd_friction',
                  'hd_restitution'), # hd = 'Havok Data'
        MelLtexSnam(),
        MelLtexGrasses(),
    )

#------------------------------------------------------------------------------
class MreLvlc(_AMreLeveledListTes4):
    """Leveled Creature."""
    rec_sig = b'LVLC'
    _top_copy_attrs = ('lvl_chance_none', 'script_fid', 'creature_template')
    _entry_copy_attrs = ('level', 'listId', 'count')

    melSet = MelSet(
        MelEdid(),
        MelLLChanceNone(),
        MelLLFlags(),
        MelLLItems(),
        MelScript(),
        MelFid(b'TNAM', 'creature_template'),
    )

#------------------------------------------------------------------------------
class MreLvli(_AMreLeveledListTes4):
    """Leveled Item."""
    rec_sig = b'LVLI'
    _top_copy_attrs = ('lvl_chance_none',)
    _entry_copy_attrs = ('level', 'listId', 'count')

    melSet = MelSet(
        MelEdid(),
        MelLLChanceNone(),
        MelLLFlags(),
        MelLLItems(),
        MelNull(b'DATA'),
    )

#------------------------------------------------------------------------------
class MreLvsp(_AMreLeveledListTes4):
    """Leveled Spell."""
    rec_sig = b'LVSP'
    _top_copy_attrs = ('lvl_chance_none',)
    _entry_copy_attrs = ('level', 'listId', 'count')

    melSet = MelSet(
        MelEdid(),
        MelLLChanceNone(),
        MelLLFlags(),
        MelLLItems(),
    )

#------------------------------------------------------------------------------
class MreMgef(MelRecord):
    """Magic Effect."""
    rec_sig = b'MGEF'

    class _ObmeFlagOverrides(Flags):
        ov_param_flag_a: bool = flag(2)
        ov_beneficial: bool = flag(3)
        ov_param_flag_b: bool = flag(16)
        ov_magnitude_is_range: bool = flag(17)
        ov_atomic_resistance: bool = flag(18)
        ov_param_flag_c: bool = flag(19)
        ov_param_flag_d: bool = flag(20)
        ov_hidden: bool = flag(30)

    class _MgefFlags(AMgefFlagsTes4):
        magnitude_pct: bool = flag(3)
        spellmaking: bool = flag(11)
        enchanting: bool = flag(12)
        no_ingredient: bool = flag(13)
        use_weapon: bool = flag(16)
        use_armor: bool = flag(17)
        use_creature: bool = flag(18)
        use_actor_value: bool = flag(24)

    _magic_effects = { # effect_sig -> (school, name, value)
        b'ABAT': [5, _('Absorb Attribute'), 0.95],
        b'ABFA': [5, _('Absorb Fatigue'), 6],
        b'ABHE': [5, _('Absorb Health'), 16],
        b'ABSK': [5, _('Absorb Skill'), 2.1],
        b'ABSP': [5, _('Absorb Magicka'), 7.5],
        b'BA01': [1, _('Bound Armor Extra 01'), 0],#--Formid == 0
        b'BA02': [1, _('Bound Armor Extra 02'), 0],#--Formid == 0
        b'BA03': [1, _('Bound Armor Extra 03'), 0],#--Formid == 0
        b'BA04': [1, _('Bound Armor Extra 04'), 0],#--Formid == 0
        b'BA05': [1, _('Bound Armor Extra 05'), 0],#--Formid == 0
        b'BA06': [1, _('Bound Armor Extra 06'), 0],#--Formid == 0
        b'BA07': [1, _('Bound Armor Extra 07'), 0],#--Formid == 0
        b'BA08': [1, _('Bound Armor Extra 08'), 0],#--Formid == 0
        b'BA09': [1, _('Bound Armor Extra 09'), 0],#--Formid == 0
        b'BA10': [1, _('Bound Armor Extra 10'), 0],#--Formid == 0
        b'BABO': [1, _('Bound Boots'), 12],
        b'BACU': [1, _('Bound Cuirass'), 12],
        b'BAGA': [1, _('Bound Gauntlets'), 8],
        b'BAGR': [1, _('Bound Greaves'), 12],
        b'BAHE': [1, _('Bound Helmet'), 12],
        b'BASH': [1, _('Bound Shield'), 12],
        b'BRDN': [0, _('Burden'), 0.21],
        b'BW01': [1, _('Bound Order Weapon 1'), 1],
        b'BW02': [1, _('Bound Order Weapon 2'), 1],
        b'BW03': [1, _('Bound Order Weapon 3'), 1],
        b'BW04': [1, _('Bound Order Weapon 4'), 1],
        b'BW05': [1, _('Bound Order Weapon 5'), 1],
        b'BW06': [1, _('Bound Order Weapon 6'), 1],
        b'BW07': [1, _('Summon Staff of Sheogorath'), 1],
        b'BW08': [1, _('Bound Priest Dagger'), 1],
        b'BW09': [1, _('Bound Weapon Extra 09'), 0],#--Formid == 0
        b'BW10': [1, _('Bound Weapon Extra 10'), 0],#--Formid == 0
        b'BWAX': [1, _('Bound Axe'), 39],
        b'BWBO': [1, _('Bound Bow'), 95],
        b'BWDA': [1, _('Bound Dagger'), 14],
        b'BWMA': [1, _('Bound Mace'), 91],
        b'BWSW': [1, _('Bound Sword'), 235],
        b'CALM': [3, _('Calm'), 0.47],
        b'CHML': [3, _('Chameleon'), 0.63],
        b'CHRM': [3, _('Charm'), 0.2],
        b'COCR': [3, _('Command Creature'), 0.6],
        b'COHU': [3, _('Command Humanoid'), 0.75],
        b'CUDI': [5, _('Cure Disease'), 1400],
        b'CUPA': [5, _('Cure Paralysis'), 500],
        b'CUPO': [5, _('Cure Poison'), 600],
        b'DARK': [3, _('DO NOT USE - Darkness'), 0],
        b'DEMO': [3, _('Demoralize'), 0.49],
        b'DGAT': [2, _('Damage Attribute'), 100],
        b'DGFA': [2, _('Damage Fatigue'), 4.4],
        b'DGHE': [2, _('Damage Health'), 12],
        b'DGSP': [2, _('Damage Magicka'), 2.45],
        b'DIAR': [2, _('Disintegrate Armor'), 6.2],
        b'DISE': [2, _('Disease Info'), 0], #--Formid == 0
        b'DIWE': [2, _('Disintegrate Weapon'), 6.2],
        b'DRAT': [2, _('Drain Attribute'), 0.7],
        b'DRFA': [2, _('Drain Fatigue'), 0.18],
        b'DRHE': [2, _('Drain Health'), 0.9],
        b'DRSK': [2, _('Drain Skill'), 0.65],
        b'DRSP': [2, _('Drain Magicka'), 0.18],
        b'DSPL': [4, _('Dispel'), 3.6],
        b'DTCT': [4, _('Detect Life'), 0.08],
        b'DUMY': [2, _('Mehrunes Dagon'), 0], #--Formid == 0
        b'FIDG': [2, _('Fire Damage'), 7.5],
        b'FISH': [0, _('Fire Shield'), 0.95],
        b'FOAT': [5, _('Fortify Attribute'), 0.6],
        b'FOFA': [5, _('Fortify Fatigue'), 0.04],
        b'FOHE': [5, _('Fortify Health'), 0.14],
        b'FOMM': [5, _('Fortify Magicka Multiplier'), 0.04],
        b'FOSK': [5, _('Fortify Skill'), 0.6],
        b'FOSP': [5, _('Fortify Magicka'), 0.15],
        b'FRDG': [2, _('Frost Damage'), 7.4],
        b'FRNZ': [3, _('Frenzy'), 0.04],
        b'FRSH': [0, _('Frost Shield'), 0.95],
        b'FTHR': [0, _('Feather'), 0.1],
        b'INVI': [3, _('Invisibility'), 40],
        b'LGHT': [3, _('Light'), 0.051],
        b'LISH': [0, _('Shock Shield'), 0.95],
        b'LOCK': [0, _('DO NOT USE - Lock'), 30],
        b'MYHL': [1, _('Summon Mythic Dawn Helm'), 110],
        b'MYTH': [1, _('Summon Mythic Dawn Armor'), 120],
        b'NEYE': [3, _('Night-Eye'), 22],
        b'OPEN': [0, _('Open'), 4.3],
        b'PARA': [3, _('Paralyze'), 475],
        b'POSN': [2, _('Poison Info'), 0],
        b'RALY': [3, _('Rally'), 0.03],
        b'REAN': [1, _('Reanimate'), 10],
        b'REAT': [5, _('Restore Attribute'), 38],
        b'REDG': [4, _('Reflect Damage'), 2.5],
        b'REFA': [5, _('Restore Fatigue'), 2],
        b'REHE': [5, _('Restore Health'), 10],
        b'RESP': [5, _('Restore Magicka'), 2.5],
        b'RFLC': [4, _('Reflect Spell'), 3.5],
        b'RSDI': [5, _('Resist Disease'), 0.5],
        b'RSFI': [5, _('Resist Fire'), 0.5],
        b'RSFR': [5, _('Resist Frost'), 0.5],
        b'RSMA': [5, _('Resist Magic'), 2],
        b'RSNW': [5, _('Resist Normal Weapons'), 1.5],
        b'RSPA': [5, _('Resist Paralysis'), 0.75],
        b'RSPO': [5, _('Resist Poison'), 0.5],
        b'RSSH': [5, _('Resist Shock'), 0.5],
        b'RSWD': [5, _('Resist Water Damage'), 0], #--Formid == 0
        b'SABS': [4, _('Spell Absorption'), 3],
        b'SEFF': [0, _('Script Effect'), 0],
        b'SHDG': [2, _('Shock Damage'), 7.8],
        b'SHLD': [0, _('Shield'), 0.45],
        b'SLNC': [3, _('Silence'), 60],
        b'STMA': [2, _('Stunted Magicka'), 0],
        b'STRP': [4, _('Soul Trap'), 30],
        b'SUDG': [2, _('Sun Damage'), 9],
        b'TELE': [4, _('Telekinesis'), 0.49],
        b'TURN': [1, _('Turn Undead'), 0.083],
        b'VAMP': [2, _('Vampirism'), 0],
        b'WABR': [0, _('Water Breathing'), 14.5],
        b'WAWA': [0, _('Water Walking'), 13],
        b'WKDI': [2, _('Weakness to Disease'), 0.12],
        b'WKFI': [2, _('Weakness to Fire'), 0.1],
        b'WKFR': [2, _('Weakness to Frost'), 0.1],
        b'WKMA': [2, _('Weakness to Magic'), 0.25],
        b'WKNW': [2, _('Weakness to Normal Weapons'), 0.25],
        b'WKPO': [2, _('Weakness to Poison'), 0.1],
        b'WKSH': [2, _('Weakness to Shock'), 0.1],
        b'Z001': [1, _('Summon Rufio\'s Ghost'), 13],
        b'Z002': [1, _('Summon Ancestor Guardian'), 33.3],
        b'Z003': [1, _('Summon Spiderling'), 45],
        b'Z004': [1, _('Summon Flesh Atronach'), 1],
        b'Z005': [1, _('Summon Bear'), 47.3],
        b'Z006': [1, _('Summon Gluttonous Hunger'), 61],
        b'Z007': [1, _('Summon Ravenous Hunger'), 123.33],
        b'Z008': [1, _('Summon Voracious Hunger'), 175],
        b'Z009': [1, _('Summon Dark Seducer'), 1],
        b'Z010': [1, _('Summon Golden Saint'), 1],
        b'Z011': [1, _('Wabba Summon'), 0],
        b'Z012': [1, _('Summon Decrepit Shambles'), 45],
        b'Z013': [1, _('Summon Shambles'), 87.5],
        b'Z014': [1, _('Summon Replete Shambles'), 150],
        b'Z015': [1, _('Summon Hunger'), 22],
        b'Z016': [1, _('Summon Mangled Flesh Atronach'), 22],
        b'Z017': [1, _('Summon Torn Flesh Atronach'), 32.5],
        b'Z018': [1, _('Summon Stitched Flesh Atronach'), 75.5],
        b'Z019': [1, _('Summon Sewn Flesh Atronach'), 195],
        b'Z020': [1, _('Extra Summon 20'), 0],
        b'ZCLA': [1, _('Summon Clannfear'), 75.56],
        b'ZDAE': [1, _('Summon Daedroth'), 123.33],
        b'ZDRE': [1, _('Summon Dremora'), 72.5],
        b'ZDRL': [1, _('Summon Dremora Lord'), 157.14],
        b'ZFIA': [1, _('Summon Flame Atronach'), 45],
        b'ZFRA': [1, _('Summon Frost Atronach'), 102.86],
        b'ZGHO': [1, _('Summon Ghost'), 22],
        b'ZHDZ': [1, _('Summon Headless Zombie'), 56],
        b'ZLIC': [1, _('Summon Lich'), 350],
        b'ZSCA': [1, _('Summon Scamp'), 30],
        b'ZSKA': [1, _('Summon Skeleton Guardian'), 32.5],
        b'ZSKC': [1, _('Summon Skeleton Champion'), 152],
        b'ZSKE': [1, _('Summon Skeleton'), 11.25],
        b'ZSKH': [1, _('Summon Skeleton Hero'), 66],
        b'ZSPD': [1, _('Summon Spider Daedra'), 195],
        b'ZSTA': [1, _('Summon Storm Atronach'), 125],
        b'ZWRA': [1, _('Summon Faded Wraith'), 87.5],
        b'ZWRL': [1, _('Summon Gloom Wraith'), 260],
        b'ZXIV': [1, _('Summon Xivilai'), 200],
        b'ZZOM': [1, _('Summon Zombie'), 16.67],
    }
    mgef_school = {x: y[0] for x, y in _magic_effects.items()}
    mgef_name = {x: y[1] for x, y in _magic_effects.items()}
    mgef_basevalue = {x: y[2] for x, y in _magic_effects.items()}

    # Doesn't list MGEFs that use actor values, but rather MGEFs that have a
    # generic name.
    # Ex: Absorb Attribute becomes Absorb Magicka if the effect's actorValue
    #     field contains 9, but it is actually using an attribute rather than
    #     an actor value
    # Ex: Burden uses an actual actor value (encumbrance) but it isn't listed
    #     since its name doesn't change
    generic_av_effects = {
        b'ABAT', #--Absorb Attribute (Use Attribute)
        b'ABSK', #--Absorb Skill (Use Skill)
        b'DGAT', #--Damage Attribute (Use Attribute)
        b'DRAT', #--Drain Attribute (Use Attribute)
        b'DRSK', #--Drain Skill (Use Skill)
        b'FOAT', #--Fortify Attribute (Use Attribute)
        b'FOSK', #--Fortify Skill (Use Skill)
        b'REAT', #--Restore Attribute (Use Attribute)
    }
    # MGEFs that are considered hostile
    hostile_effects = {
        b'ABAT', #--Absorb Attribute
        b'ABFA', #--Absorb Fatigue
        b'ABHE', #--Absorb Health
        b'ABSK', #--Absorb Skill
        b'ABSP', #--Absorb Magicka
        b'BRDN', #--Burden
        b'DEMO', #--Demoralize
        b'DGAT', #--Damage Attribute
        b'DGFA', #--Damage Fatigue
        b'DGHE', #--Damage Health
        b'DGSP', #--Damage Magicka
        b'DIAR', #--Disintegrate Armor
        b'DIWE', #--Disintegrate Weapon
        b'DRAT', #--Drain Attribute
        b'DRFA', #--Drain Fatigue
        b'DRHE', #--Drain Health
        b'DRSK', #--Drain Skill
        b'DRSP', #--Drain Magicka
        b'FIDG', #--Fire Damage
        b'FRDG', #--Frost Damage
        b'FRNZ', #--Frenzy
        b'PARA', #--Paralyze
        b'SHDG', #--Shock Damage
        b'SLNC', #--Silence
        b'STMA', #--Stunted Magicka
        b'STRP', #--Soul Trap
        b'SUDG', #--Sun Damage
        b'TURN', #--Turn Undead
        b'WKDI', #--Weakness to Disease
        b'WKFI', #--Weakness to Fire
        b'WKFR', #--Weakness to Frost
        b'WKMA', #--Weakness to Magic
        b'WKNW', #--Weakness to Normal Weapons
        b'WKPO', #--Weakness to Poison
        b'WKSH', #--Weakness to Shock
    }

    melSet = MelSet(
        MelMgefEdidTes4(),
        MelObme(extra_format=['2B', '2s', '4s', 'I', '4s'], extra_contents=[
            'obme_param_a_info', 'obme_param_b_info', 'obme_unused_mgef',
            'obme_handler', (_ObmeFlagOverrides, 'obme_flag_overrides'),
            'obme_param_b']),
        MelUnion({
            None: MelNull(b'EDDX'), # discard for non-OBME records
        }, decider=AttrValDecider('obme_record_version'),
            fallback=MelString(b'EDDX', 'obme_eid')),
        MelFull(),
        MelDescription(),
        MelIcon(),
        MelModel(),
        MelMgefData(MelTruncatedStruct(b'DATA',
            ['I', 'f', 'I', 'i', 'i', 'H', '2s', 'I', 'f', '6I', '2f'],
            (_MgefFlags, 'flags'), 'base_cost', (FID, 'associated_item'),
            'school', 'resist_value', 'counter_effect_count', 'unused1',
            (FID, 'light'), 'projectileSpeed', (FID, 'effectShader'),
            (FID, 'enchantEffect'), (FID, 'castingSound'), (FID, 'boltSound'),
            (FID, 'hitSound'), (FID, 'areaSound'), 'cef_enchantment',
            'cef_barter', old_versions={'IfIiiH2sIfI'})),
        MelMgefEsceTes4(),
    )

#------------------------------------------------------------------------------
class MreMisc(_ObIcon):
    """Misc. Item."""
    rec_sig = b'MISC'
    _default_icons = 'Clutter\\Soulgems\\AzurasStar.dds'

    class HeaderFlags(MelRecord.HeaderFlags):
        @property
        def misc_actor_value(self) -> bool:
            """The ActorValue flag is encoded in bits 6-7.  It might
            actually be treated as an int with different meanings for values
            0, 1, 2, 3, but current code requires both bits set."""
            return (self._field & 0b01100000) == 0b01100000

        @misc_actor_value.setter
        def misc_actor_value(self, new_av: bool) -> None:
            new_bits = 0b01100000 if new_av else 0
            self._field = (self._field & ~0b01100000) | new_bits

    melSet = MelSet(
        MelEdid(),
        MelFull(),
        MelModel(),
        MelIcon(),
        MelScript(),
        MelUnion({
            False: MelValueWeight(),
            True: MelStruct(b'DATA', ['2I'], (FID, 'value'), 'weight'),
        }, decider=FlagDecider('flags1', ['misc_actor_value'])),
    )

#------------------------------------------------------------------------------
class MreNpc_(AMreActor):
    """Non-Player Character."""
    rec_sig = b'NPC_'
    model: object

    class NpcFlags(Flags):
        npc_female: bool = flag(0)
        npc_essential: bool = flag(1)
        npc_respawn: bool = flag(3)
        npc_auto_calc: bool = flag(4)
        pc_level_offset: bool = flag(7)
        no_low_level: bool = flag(9)
        no_rumors: bool = flag(13)
        npc_summonable: bool = flag(14)
        no_persuasion: bool = flag(15)
        can_corpse_check: bool = flag(20)

    class MelNpcData(MelLists):
        """Convert npc stats into skills, health, attributes."""
        # 21 skills and 7 attributes
        _attr_indexes = {'skills': slice(21), 'health': 21, 'unused2': 22,
                         'attributes': slice(23, None)}

    melSet = MelSet(
        MelEdid(),
        MelFull(),
        MelModel(),
        MelStruct(b'ACBS', ['I', '3H', 'h', '2H'], (NpcFlags, 'npc_flags'),
            'base_spell', 'fatigue', 'barter_gold', 'level_offset',
            'calc_min_level', 'calc_max_level'),
        MelFactions(with_unused=True),
        MelDeathItem(),
        MelRace(),
        MelSpellsTes4(),
        MelScript(),
        MelItems(),
        MelAidt(),
        MelAIPackages(),
        MelAnimations(),
        MelNpcClass(),
        MelNpcData(b'DATA', ['21B', 'H', '2s', '8B'], 'skills', 'health',
                   'unused2', 'attributes'),
        MelFid(b'HNAM', 'hair'),
        MelFloat(b'LNAM', 'hairLength'),
        ##: This is a FormID array in xEdit, but I haven't found any NPC_
        # records with >1 eye. Changing it would also break the NPC Checker
        MelFid(b'ENAM', 'eye'),
        MelStruct(b'HCLR', ['3B', 's'], 'hairRed', 'hairBlue', 'hairGreen',
                  'unused3'),
        MelCombatStyle(),
        MelBase(b'FGGS', 'fggs_p'), ##: rename to face_gen_geometry_symmetric
        MelBase(b'FGGA', 'fgga_p'), ##: rename to face_gen_geometry_asymmetric
        MelBase(b'FGTS', 'fgts_p'), ##: rename to face_gen_texture_symmetric
        MelBase(b'FNAM', 'fnam'),
    )

    def setRace(self, race):
        """Set additional race info."""
        self.race = race
        if not self.model:
            self.model = self.getDefault('model')
        if race in (0x23fe9, 0x223c7): # Argonian & Khajiit
            self.model.modPath = r'Characters\_Male\SkeletonBeast.NIF'
        else:
            self.model.modPath = r'Characters\_Male\skeleton.nif'
        fnams = {
            0x23fe9: b'\xdc<',    # Argonian
            0x224fc: b'H\x1d',    # Breton
            0x191c1: b'rT',       # Dark Elf
            0x19204: b'\xe6!',    # High Elf
            0x00907: b'\x8e5',    # Imperial
            0x22c37: b'T[',       # Khajiit
            0x224fd: b'\xb6\x03', # Nord
            0x191c0: b't\t',      # Orc
            0x00d43: b'\xa9a',    # Redguard
            0x00019: b'wD',       # Vampire
            0x223c8: b'.J',       # Wood Elf
        }
        self.fnam = fnams.get(race, b'\x8e5') # default to Imperial

#------------------------------------------------------------------------------
class MrePack(MelRecord):
    """AI Package."""
    rec_sig = b'PACK'

    melSet = MelSet(
        MelEdid(),
        MelTruncatedStruct(b'PKDT', ['I', 'B', '3s'],
            (PackGeneralOldFlags, 'package_flags'), 'package_ai_type',
            'unused1', old_versions={'HBs'}),
        MelUnion({
            (0, 1, 2, 3, 4): MelStruct(b'PLDT', ['i', 'I', 'i'],
                'package_location_type', (FID, 'package_location_value'),
                'package_location_radius'),
            5: MelStruct(b'PLDT', ['i', 'I', 'i'],
                'package_location_type', 'package_location_value',
                'package_location_radius'),
        }, decider=PartialLoadDecider(
            loader=MelSInt32(b'PLDT', 'package_location_type'),
            decider=AttrValDecider('package_location_type'),
        ), fallback=MelNull(b'NULL')), # ignore
        MelPackScheduleOld(is_required=False), ##: might actually be required?
        MelUnion({
            (0, 1): MelStruct(b'PTDT', ['i', 'I', 'i'], 'package_target_type',
                (FID, 'package_target_value'), 'package_target_count'),
            2: MelStruct(b'PTDT', ['i', 'I', 'i'], 'package_target_type',
                'package_target_value', 'package_target_count'),
        }, decider=PartialLoadDecider(
            loader=MelSInt32(b'PTDT', 'package_target_type'),
            decider=AttrValDecider('package_target_type'),
        ), fallback=MelNull(b'NULL')), # ignore
        MelConditionsTes4(),
    )

#------------------------------------------------------------------------------
class MrePgrd(MelRecord):
    """Path Grid."""
    rec_sig = b'PGRD'

    # Most of these MelBases could be loaded via MelArray, but they're really
    # big, don't contain FormIDs and are too complex to manipulate
    melSet = MelSet(
        MelUInt16(b'DATA', 'point_count'),
        MelBase(b'PGRP', 'point_array'),
        MelBase(b'PGAG', 'unknown1'),
        MelBase(b'PGRR', 'point_to_point_connections'), # sorted
        MelBase(b'PGRI', 'inter_cell_connections'), # sorted
        MelSorted(MelGroups('point_to_reference_mappings',
            MelSorted(MelArray(
                'mapping_points', MelUInt32(b'PGRL', 'm_point'),
                prelude=MelFid(b'PGRL', 'mapping_reference')
            ), sort_by_attrs='m_point'),
        ), sort_special=lambda e: tuple(p.m_point for p in e.mapping_points)),
    )

#------------------------------------------------------------------------------
class MreQust(_ObIcon):
    """Quest."""
    rec_sig = b'QUST'
    _default_icons = 'Quest\\icon_miscellaneous.dds'
    stages: list

    class _QustFlags(Flags):
        startGameEnabled: bool
        repeatedTopics: bool = flag(2)
        repeatedStages: bool

    class _StageFlags(Flags):
        complete: bool

    class _TargetFlags(Flags):
        ignoresLocks: bool

    melSet = MelSet(
        MelEdid(),
        MelScript(),
        MelFull(),
        MelIcon(),
        MelStruct(b'DATA', ['B', 'B'], (_QustFlags, 'questFlags'), 'priority'),
        MelConditionsTes4(),
        MelSorted(MelGroups('stages',
            MelSInt16(b'INDX', 'stage'),
            MelGroups('entries',
                MelUInt8Flags(b'QSDT', 'flags', _StageFlags),
                MelConditionsTes4(),
                MelString(b'CNAM','text'),
                MelEmbeddedScript(),
            ),
        ), sort_by_attrs='stage'),
        MelGroups('targets',
            MelStruct(b'QSTA', ['I', 'B', '3s'], (FID, 'package_target_value'),
                (_TargetFlags, 'flags'), 'unused1'),
            MelConditionsTes4(),
        ),
    ).with_distributor({
        b'EDID|DATA': { # just in case one is missing
            b'CTDA': 'conditions',
        },
        b'INDX': {
            b'CTDA': 'stages',
        },
        b'QSTA': {
            b'CTDA': 'targets',
        },
    })

    def can_set_icon(self):
        return self.stages and super().can_set_icon()

#------------------------------------------------------------------------------
class MreRace(AMreRace):
    """Race."""
    rec_sig = b'RACE'

    class _RaceFlags(Flags):
        playable: bool

    melSet = MelSet(
        MelEdid(),
        MelFull(),
        MelDescription(),
        MelSpellsTes4(),
        MelRelations(with_gcr=False),
        MelRaceData(b'DATA', ['14b', '2s', '4f', 'I'], 'skills', 'unused1',
                    'maleHeight', 'femaleHeight', 'maleWeight', 'femaleWeight',
                    (_RaceFlags, 'flags')),
        MelRaceVoices(b'VNAM', ['2I'], (FID, 'maleVoice'),
                      (FID, 'femaleVoice')),
        MelStruct(b'DNAM', ['2I'], (FID, 'defaultHairMale'),
                  (FID, 'defaultHairFemale')),
        # Corresponds to GMST sHairColorNN
        MelUInt8(b'CNAM', 'defaultHairColor'),
        MelFloat(b'PNAM', 'mainClamp'),
        MelFloat(b'UNAM', 'faceClamp'),
        MelStruct(b'ATTR', ['16B'], 'maleStrength', 'maleIntelligence',
                  'maleWillpower', 'maleAgility', 'maleSpeed', 'maleEndurance',
                  'malePersonality', 'maleLuck', 'femaleStrength',
                  'femaleIntelligence', 'femaleWillpower', 'femaleAgility',
                  'femaleSpeed', 'femaleEndurance', 'femalePersonality',
                  'femaleLuck'),
        # Indexed Entries
        MelBaseR(b'NAM0', 'face_data_marker'),
        MelRaceParts({
            0: 'head',
            1: 'maleEars',
            2: 'femaleEars',
            3: 'mouth',
            4: 'teethLower',
            5: 'teethUpper',
            6: 'tongue',
            7: 'leftEye',
            8: 'rightEye',
        }, group_loaders=lambda _indx: (
            # TODO(inf) Can't use MelModel here, since some patcher code
            #  directly accesses these - MelModel would put them in a group,
            #  which breaks that. Change this to a MelModel, then hunt down
            #  that code and change it
            MelString(b'MODL', 'modPath'),
            MelFloat(b'MODB', 'modb'),
            MelBase(b'MODT', 'modt_p'),
            MelIcon(),
        )),
        MelBaseR(b'NAM1', 'body_data_marker'),
        MelBaseR(b'MNAM', 'male_body_data_marker'),
        MelModel(b'MODL', 'maleTailModel'),
        MelRaceParts({
            0: 'maleUpperBodyPath',
            1: 'maleLowerBodyPath',
            2: 'maleHandPath',
            3: 'maleFootPath',
            4: 'maleTailPath',
        }, group_loaders=lambda _indx: (MelIcon(),)),
        MelBaseR(b'FNAM', 'female_body_data_marker'),
        MelModel(b'MODL', 'femaleTailModel'),
        MelRaceParts({
            0: 'femaleUpperBodyPath',
            1: 'femaleLowerBodyPath',
            2: 'femaleHandPath',
            3: 'femaleFootPath',
            4: 'femaleTailPath',
        }, group_loaders=lambda _indx: (MelIcon(),)),
        # Normal Entries
        # Note: xEdit marks both HNAM and ENAM as sorted. They are not, but
        # changing it would cause too many conflicts. We do *not* want to mark
        # them as sorted here, because that's what the Race Checker is for!
        MelSimpleArray('hairs', MelFid(b'HNAM')),
        MelSimpleArray('eyes', MelFid(b'ENAM')),
        MelBase(b'FGGS', 'fggs_p'), ##: rename to face_gen_geometry_symmetric
        MelBase(b'FGGA', 'fgga_p'), ##: rename to face_gen_geometry_asymmetric
        MelBase(b'FGTS', 'fgts_p'), ##: rename to face_gen_texture_symmetric
        MelStruct(b'SNAM', ['2s'], 'snam_p'),
    ).with_distributor({
        b'NAM0': {
            b'INDX|MODL|MODB|MODT|ICON': 'head',
        },
        b'MNAM': {
            b'MODL|MODB|MODT': 'maleTailModel',
            b'INDX|ICON': 'maleUpperBodyPath',
        },
        b'FNAM': {
            b'MODL|MODB|MODT': 'femaleTailModel',
            b'INDX|ICON': 'femaleUpperBodyPath',
        },
    })

#------------------------------------------------------------------------------
class MreRefr(MelRecord):
    """Placed Object."""
    rec_sig = b'REFR'

    class HeaderFlags(MelRecord.HeaderFlags):
        persistent: bool = flag(10)
        casts_shadows: bool = flag(9)   # REFR to LIGH?

    class _LockFlags(Flags):
        leveledLock: bool = flag(2)

    class MelRefrXloc(MelTruncatedStruct):
        """Skips unused2, in the middle of the struct - don't apply an action
        to it!"""
        def _pre_process_unpacked(self, unpacked_val):
            if len(unpacked_val) == 5:
                unpacked_val = (*unpacked_val[:3], self.defaults[3],
                                *unpacked_val[3:])
            return super()._pre_process_unpacked(unpacked_val)

    melSet = MelSet(
        MelEdid(),
        MelFid(b'NAME', 'base'),
        MelStruct(b'XTEL', ['I', '6f'], (FID, 'destinationFid'),
            'destinationPosX', 'destinationPosY', 'destinationPosZ',
            'destinationRotX', 'destinationRotY', 'destinationRotZ'),
        MelRefrXloc(b'XLOC', ['B', '3s', 'I', '4s', 'B', '3s'], 'lockLevel',
            'unused1', (FID, 'lockKey'), 'unused2', (_LockFlags, 'lockFlags'),
            'unused3', old_versions={'B3sIB3s'}),
        MelOwnershipTes4(),
        MelEnableParent(),
        MelFid(b'XTRG', 'package_target_value'),
        MelBase(b'XSED', 'seed_p'),
        ####SpeedTree Seed, if it's a single byte then it's an offset into
        # the list of seed values in the TREE record
        ####if it's 4 byte it's the seed value directly.
        MelXlod(),
        MelFloat(b'XCHG', 'charge'),
        MelSInt32(b'XHLT', 'health'),
        MelNull(b'XPCI'), # These two are unused
        MelReadOnly(MelFull()), # Can't use MelNull, we need to distribute
        MelSInt32(b'XLCM', 'levelMod'),
        MelFid(b'XRTM', 'teleport_ref'),
        MelActionFlags(),
        MelSInt32(b'XCNT', 'count'),
        MelMapMarker(),
        MelBase(b'ONAM', 'open_by_default'),
        MelBase(b'XRGD', 'xrgd_p'), # Ragdoll Data, bytearray
        MelRefScale(),
        MelUInt8(b'XSOL', 'ref_soul'),
        MelRef3D(),
    ).with_distributor({
        b'FULL': 'full', # unused, but still need to distribute it
        b'XMRK': {
            b'FULL': 'map_marker',
        },
    })

#------------------------------------------------------------------------------
class MreRegn(AMreRegn):
    """Region."""
    melSet = MelSet(
        MelEdid(),
        MelIcon(),
        MelColor(b'RCLR'),
        MelWorldspace(),
        MelRegnAreas(),
        MelSorted(MelGroups('regn_entries',
            MelRegnRdat(),
            MelRegnEntryObjects(),
            MelRegnEntryMapName(),
            MelRegnEntryGrasses(),
            MelRegnEntryMusicType(),
            MelRegnEntrySoundsOld(),
            MelRegnEntryWeatherTypes(with_global=False),
        ), sort_by_attrs='regn_data_type'),
    )

#------------------------------------------------------------------------------
class MreRoad(MelRecord):
    """Road."""
    ####Could probably be loaded via MelArray,
    ####but little point since it is too complex to manipulate
    rec_sig = b'ROAD'

    melSet = MelSet(
        MelBase(b'PGRP', 'points_p'),
        MelBase(b'PGRR', 'connections_p'),
    )

#------------------------------------------------------------------------------
class MreSbsp(MelRecord):
    """Subspace."""
    rec_sig = b'SBSP'

    melSet = MelSet(
        MelEdid(),
        MelStruct(b'DNAM', ['3f'], 'sizeX', 'sizeY', 'sizeZ'),
    )

#------------------------------------------------------------------------------
class MreScpt(MelRecord):
    """Script."""
    rec_sig = b'SCPT'

    melSet = MelSet(
        MelEdid(),
        MelEmbeddedScript(with_script_vars=True),
    )

#------------------------------------------------------------------------------
class MreSgst(MreHasEffects, _ObIcon):
    """Sigil Stone."""
    rec_sig = b'SGST'
    _default_icons = 'IconSigilStone.dds'

    melSet = MelSet(
        MelEdid(),
        MelObme(),
        MelFull(),
        MelModel(),
        MelIcon(),
        MelScript(),
        MelEffectsTes4(),
        MelEffectsTes4ObmeFull(),
        MelStruct(b'DATA', ['B', 'I', 'f'], 'uses', 'value', 'weight'),
    ).with_distributor(_effects_distributor)

#------------------------------------------------------------------------------
class MreSkil(MelRecord):
    """Skill."""
    rec_sig = b'SKIL'

    melSet = MelSet(
        MelEdid(),
        MelSInt32(b'INDX', 'skill'),
        MelDescription(),
        MelIcon(),
        MelStruct(b'DATA', ['2i', 'I', '2f'], 'action', 'attribute',
                  'specialization', 'use0', 'use1'),
        MelString(b'ANAM', 'apprentice'),
        MelString(b'JNAM', 'journeyman'),
        MelString(b'ENAM', 'expert'),
        MelString(b'MNAM', 'master'),
    )

#------------------------------------------------------------------------------
class MreSlgm(_ObIcon):
    """Soul Gem."""
    rec_sig = b'SLGM'
    _default_icons = 'Clutter\\Soulgems\\AzurasStar.dds'

    melSet = MelSet(
        MelEdid(),
        MelFull(),
        MelModel(),
        MelIcon(),
        MelScript(),
        MelValueWeight(),
        MelUInt8(b'SOUL', 'soul'),
        MelUInt8(b'SLCP', 'capacity'),
    )

#------------------------------------------------------------------------------
class MreSoun(MelRecord):
    """Sound."""
    rec_sig = b'SOUN'
    _has_duplicate_attrs = True # SNDD is an older version of SNDX

    class _SounFlags(Flags):
        randomFrequencyShift: bool
        playAtRandom: bool
        environmentIgnored: bool
        randomLocation: bool
        loop: bool
        menuSound: bool
        twoD: bool
        three60LFE: bool

    melSet = MelSet(
        MelEdid(),
        MelString(b'FNAM','soundFile'),
        # This is the old format of SNDX - read it, but dump SNDX only
        MelReadOnly(
            MelStruct(b'SNDD', ['2B', 'b', 's', 'H', '2s'], 'minDistance',
                'maxDistance', 'freqAdjustment', 'unused1',
                (_SounFlags, 'flags'), 'unused2')
        ),
        MelStruct(b'SNDX', ['2B', 'b', 's', 'H', '2s', 'H', '2B'],
            'minDistance', 'maxDistance', 'freqAdjustment', 'unused1',
            (_SounFlags, 'flags'), 'unused2', 'staticAtten', 'stopTime',
            'startTime'),
    )

#------------------------------------------------------------------------------
class MreSpel(MreHasEffects, MelRecord):
    """Spell."""
    rec_sig = b'SPEL'
    _spell_type_name_num = LowerDict(
        {'Spell': 0, 'Disease': 1, 'Power': 2, 'LesserPower': 3, 'Ability': 4,
         'Poison': 5})
    _spell_type_num_name = {y: x for x, y in _spell_type_name_num.items()}
    _spell_type_num_name[None] = 'NONE'
    _level_type_name_num = LowerDict(
        {'Novice': 0, 'Apprentice': 1, 'Journeyman': 2, 'Expert': 3,
         'Master': 4})
    _level_type_num_name = {y: x for x, y in _level_type_name_num.items()}
    _level_type_num_name[None] = 'NONE'
    attr_csv_struct['level'][2] = \
        lambda val: f'"{MreSpel._level_type_num_name.get(val, val)}"'
    attr_csv_struct['spellType'][2] = \
        lambda val: f'"{MreSpel._spell_type_num_name.get(val, val)}"'

    melSet = MelSet(
        MelEdid(),
        MelObme(),
        MelFull(),
        MelStruct(b'SPIT', ['3I', 'B', '3s'], 'spellType', 'cost', 'level',
                  (SpellFlags, 'spell_flags'), 'unused1'),
        MelEffectsTes4(),
        MelEffectsTes4ObmeFull(),
    ).with_distributor(_effects_distributor)

    @classmethod
    def parse_csv_line(cls, csv_fields, index_dict, reuse=False):
        attr_dict = super().parse_csv_line(csv_fields, index_dict, reuse)
        try:
            lvl = attr_dict['level'] # KeyError on 'detailed' pass
            attr_dict['level'] = cls._level_type_name_num.get(lvl,
                int_or_zero(lvl))
            stype = attr_dict['spellType']
            attr_dict['spellType'] = cls._spell_type_name_num.get(stype,
                int_or_zero(stype))
            attr_dict['spell_flags'] = SpellFlags(
                attr_dict.get('spell_flags', 0))
        except KeyError:
            """We are called for reading the 'detailed' attributes"""
        return attr_dict

#------------------------------------------------------------------------------
class MreStat(MelRecord):
    """Static."""
    rec_sig = b'STAT'

    melSet = MelSet(
        MelEdid(),
        MelModel(),
    )

#------------------------------------------------------------------------------
class MreTree(MelRecord):
    """Tree."""
    rec_sig = b'TREE'

    melSet = MelSet(
        MelEdid(),
        MelModel(),
        MelIcon(),
        MelSorted(MelArray('speedTree', MelUInt32(b'SNAM', 'seed')),
                  sort_by_attrs='seed'),
        MelStruct(b'CNAM', ['5f', 'i', '2f'], 'curvature', 'minAngle',
                  'maxAngle', 'branchDim', 'leafDim', 'shadowRadius',
                  'rockSpeed', 'rustleSpeed'),
        MelStruct(b'BNAM', ['2f'], 'widthBill', 'heightBill'),
    )

class MelWatrData(MelTruncatedStruct):
    """Chop off two junk bytes at the end of each older format."""
    def _pre_process_unpacked(self, unpacked_val):
        if len(unpacked_val) != 36:
            unpacked_val = unpacked_val[:-1]
        return super()._pre_process_unpacked(unpacked_val)

#------------------------------------------------------------------------------
class MreWatr(MelRecord):
    """Water."""
    rec_sig = b'WATR'

    class _WatrFlags(Flags):
        causesDmg: bool
        reflective: bool

    melSet = MelSet(
        MelEdid(),
        MelString(b'TNAM','texture'),
        MelUInt8(b'ANAM', 'opacity'),
        MelUInt8Flags(b'FNAM', 'flags', _WatrFlags),
        MelString(b'MNAM','material'),
        MelSound(),
        MelWatrData(b'DATA',
            ['11f', '3B', 's', '3B', 's', '3B', 's', 'B', '3s', '10f', 'H'],
            'windVelocity', 'windDirection', 'waveAmp', 'waveFreq', 'sunPower',
            'reflectAmt', 'fresnelAmt', 'xSpeed', 'ySpeed', 'fogNear',
            'fogFar', 'shallowRed', 'shallowGreen', 'shallowBlue', 'unused1',
            'deepRed', 'deepGreen', 'deepBlue', 'unused2', 'reflRed',
            'reflGreen', 'reflBlue', 'unused3', 'blend', 'unused4',
            'rainForce', 'rainVelocity', 'rainFalloff', 'rainDampner',
            'rainSize', 'dispForce', 'dispVelocity', 'dispFalloff',
            'dispDampner', 'dispSize', 'damage',
            old_versions={'11f3Bs3Bs3BsB3s6f2s', '11f3Bs3Bs3BsB3s2s',
                          '10f2s', '2s'}),
        MelSimpleArray('relatedWaters', MelFid(b'GNAM')),
    )

#------------------------------------------------------------------------------
class MreWeap(_ObIcon):
    """Weapon."""
    rec_sig = b'WEAP'
    _default_icons = ('Weapons\\IronDagger.dds', 'Weapons\\IronClaymore.dds',
                      'Weapons\\IronMace.dds', 'Weapons\\IronBattleAxe.dds',
                      'Weapons\\Staff.dds', 'Weapons\\IronBow.dds')
    weaponType: int

    class _WeapFlags(Flags):
        notNormalWeapon: bool

    melSet = MelSet(
        MelEdid(),
        MelFull(),
        MelModel(),
        MelIcon(),
        MelScript(),
        MelEnchantment(b'ENAM'),
        MelUInt16(b'ANAM', 'enchantPoints'),
        MelStruct(b'DATA', ['I', '2f', '3I', 'f', 'H'], 'weaponType', 'speed',
                  'reach', (_WeapFlags, 'flags'), 'value', 'health', 'weight',
                  'damage'),
    )

    def set_default_icon(self):
        # Choose based on weapon type:
        try:
            self.iconPath = self._default_icons[self.weaponType]
        except IndexError:  # just in case
            self.iconPath = self._default_icons[0]

#------------------------------------------------------------------------------
class MreWrld(AMreWrld):
    """Worldspace."""
    ref_types = MreCell.ref_types
    exterior_temp_extra = [b'LAND', b'PGRD']
    wrld_children_extra = [b'ROAD', b'CELL'] # CELL for the persistent block

    class _WrldFlags(Flags):
        smallWorld: bool
        noFastTravel: bool
        oblivionWorldspace: bool
        noLODWater: bool = flag(4)

    melSet = MelSet(
        MelEdid(),
        MelFull(),
        MelWorldspace('wrld_parent'),
        MelFid(b'CNAM', 'climate'),
        MelFid(b'NAM2', 'water'),
        MelIcon('mapPath'),
        MelStruct(b'MNAM', ['2i', '4h'], 'dimX', 'dimY', 'NWCellX', 'NWCellY',
                  'SECellX', 'SECellY'),
        MelUInt8Flags(b'DATA', 'flags', _WrldFlags),
        MelWorldBounds(),
        MelUInt32(b'SNAM', 'music_type'),
        MelNull(b'OFST'), # Not even CK/xEdit can recalculate these right now
    )

#------------------------------------------------------------------------------
class MreWthr(AMreWthr):
    """Weather."""
    rec_sig = b'WTHR'

    melSet = MelSet(
        MelEdid(),
        MelString(b'CNAM', 'lowerLayer'),
        MelString(b'DNAM', 'upperLayer'),
        MelModel(),
        MelArray('colors', MelWthrColors(b'NAM0')),
        MelStruct(b'FNAM', ['4f'], 'fogDayNear', 'fogDayFar', 'fogNightNear',
                  'fogNightFar'),
        MelStruct(b'HNAM', ['14f'], 'eyeAdaptSpeed', 'blurRadius',
                  'blurPasses', 'emissiveMult', 'targetLum', 'upperLumClamp',
                  'brightScale', 'brightClamp', 'lumRampNoTex', 'lumRampMin',
                  'lumRampMax', 'sunlightDimmer', 'grassDimmer', 'treeDimmer'),
        MelStruct(b'DATA', ['15B'], 'windSpeed', 'lowerCloudSpeed',
                  'upperCloudSpeed', 'transDelta', 'sunGlare', 'sunDamage',
                  'rainFadeIn', 'rainFadeOut', 'boltFadeIn', 'boltFadeOut',
                  'boltFrequency', 'weatherType', 'boltRed', 'boltBlue',
                  'boltGreen'),
        MelGroups('sounds', MelStruct(b'SNAM', ['2I'], (FID, 'sound'), 'type'))
    )
