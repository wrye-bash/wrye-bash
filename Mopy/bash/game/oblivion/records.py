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
#  Wrye Bash copyright (C) 2005-2009 Wrye, 2010-2022 Wrye Bash Team
#  https://github.com/wrye-bash
#
# =============================================================================
"""This module contains the oblivion record classes."""
import io
import re
from collections import OrderedDict

from ...bolt import Flags, int_or_zero, structs_cache, str_or_none, \
    int_or_none, str_to_sig, sig_to_str
from ...brec import MelRecord, MelGroups, MelStruct, FID, MelGroup, MelString, \
    AMreLeveledList, MelSet, MelFid, MelNull, MelOptStruct, MelFids, \
    AMreHeader, MelBase, MelSimpleArray, MelBodyParts, MelAnimations, \
    MelReferences, MelRegnEntrySubrecord, MelSorted, MelRegions, \
    MelFloat, MelSInt16, MelSInt32, MelUInt8, MelUInt16, MelUInt32, \
    MelRaceParts, MelRaceVoices, null2, MelScriptVars, MelRelations, MelRace, \
    MelSequential, MelUnion, FlagDecider, AttrValDecider, PartialLoadDecider, \
    MelTruncatedStruct, MelSkipInterior, MelIcon, MelIco2, MelEdid, MelFull, \
    MelArray, MelWthrColors, MelEffectsTes4, AMreActor, AMreWithItems, \
    MelReadOnly, MelRef3D, MelXlod, MelWorldBounds, MelEnableParent, MelObme, \
    MelRefScale, MelMapMarker, MelActionFlags, MelPartialCounter, MelScript, \
    MelDescription, BipedFlags, MelUInt8Flags, MelUInt32Flags, MelLists, \
    MelConditionsTes4, MelRaceData, MelFactions, MelActorSounds, MelBaseR, \
    MelClmtWeatherTypes, MelFactRanks, MelLscrLocations, attr_csv_struct, \
    MelEnchantment, MelValueWeight, null4, SpellFlags, MelOwnership, \
    MelSound, MelWeight, MelEffectsTes4ObmeFull, MelBookText, MelClmtTiming, \
    MelClmtTextures, MelSoundClose, AMelItems, AMelLLItems, MelContData, \
    MelDoorFlags, MelSoundLooping, MelRandomTeleports, MelHairFlags, \
    MelSeasons, MelIngredient, MelGrasData, MelIdleRelatedAnims, \
    MelLandShared, AMreCell, AMreWrld

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
aiService = Flags.from_names(
    (0,'weapons'),
    (1,'armor'),
    (2,'clothing'),
    (3,'books'),
    (4,'ingredients'),
    (7,'lights'),
    (8,'apparatus'),
    (10,'miscItems'),
    (11,'spells'),
    (12,'magicItems'),
    (13,'potions'),
    (14,'training'),
    (16,'recharge'),
    (17,'repair')
)

#------------------------------------------------------------------------------
# A distributor config for use with MelEffectsTes4, since MelEffectsTes4 also
# contains a FULL subrecord
_effects_distributor = {
    b'FULL': u'full', # don't rely on EDID being present
    b'EFID': {
        b'FULL': u'effects',
    },
    b'EFXX': {
        b'FULL': u'obme_full',
    },
}

#------------------------------------------------------------------------------
class MelEmbeddedScript(MelSequential):
    """Handles an embedded script, a SCHR/SCDA/SCTX/SLSD/SCVR/SCRO/SCRV
    subrecord combo. SLSD and SCVR can optionally be disabled."""
    def __init__(self, with_script_vars=False):
        seq_elements = [
            MelUnion({
                b'SCHR': MelStruct(b'SCHR', [u'4s', u'4I'], u'unused1',
                                  u'num_refs', u'compiled_size', u'last_index',
                                  u'script_type'),
                b'SCHD': MelBase(b'SCHD', u'old_script_header'),
            }),
            MelBase(b'SCDA', u'compiled_script'),
            MelString(b'SCTX', u'script_source'),
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
class MelLevListLvld(MelUInt8):
    """Subclass to handle chanceNone and flags.calcFromAllLevels."""
    def __init__(self):
        super(MelLevListLvld, self).__init__(b'LVLD', u'chanceNone')

    def load_mel(self, record, ins, sub_type, size_, *debug_strs):
        super(MelLevListLvld, self).load_mel(record, ins, sub_type, size_,
                                             *debug_strs)
        if record.chanceNone > 127:
            record.flags.calcFromAllLevels = True
            record.chanceNone &= 127

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
class MelSpellsTes4(MelFids): ##: HACKy workaround, see docstring
    """Handles the common SPLO subrecord. This is a workaround to fix Oblivion
    hanging on load in some edge cases. The CS does some sort of processing or
    sorting to SPLOs that we don't fully understand yet. All we know for sure
    so far is that it always seems to put SPLOs that link to LVSPs after ones
    that link to SPELs, and we can't handle that without loading the plugin's
    masters (see #282 and #577 for two issues that need this as well)."""
    def __init__(self):
        super().__init__('spells', MelFid(b'SPLO'))

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

class MreHasEffects(object):
    """Mixin class for magic items."""
    __slots__ = ()
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
        _('Script ObjectIndex')), lambda val:(
    '"None","None"' if val is None else '"%s","0x%06X"' % val)]

    @classmethod
    def parse_csv_line(cls, csv_fields, index_dict, reuse=False):
        effects_tuple = index_dict.pop('effects', None)
        attr_dex = super(MreHasEffects, cls).parse_csv_line(csv_fields,
                                                            index_dict, reuse)
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
        spellSchool = [0,0]
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
        buff = io.StringIO()
        avEffects = MreMgef.generic_av_effects
        aValues = actor_values
        buffWrite = buff.write
        if self.effects:
            school = self._get_spell_school()
            buffWrite(aValues[20 + school] + u'\n')
        for index, effect in enumerate(self.effects):
            if effect.scriptEffect: ##: #480 - setDefault commit - return None
                effectName = effect.scriptEffect.full or u'Script Effect'
            else:
                effectName = MreMgef.mgef_name[effect.effect_sig]
                if effect.effect_sig in avEffects:
                    effectName = re.sub(_(u'(Attribute|Skill)'),
                                        aValues[effect.actorValue], effectName)
            buffWrite('o+*'[effect.recipient] + f' {effectName}')
            if effect.magnitude: buffWrite(f' {effect.magnitude}m')
            if effect.area: buffWrite(f' {effect.area}a')
            if effect.duration > 1: buffWrite(f' {effect.duration}d')
            buffWrite(u'\n')
        return buff.getvalue()

    @classmethod
    def _read_effects(cls, _effects, _coerce_fid, *,
                      __packer=structs_cache['I'].pack):
        schoolTypeName_Number = cls._school_name_number
        recipientTypeName_Number = cls._recipient_name_number
        actorValueName_Number = cls._actor_val_name_number
        effects_list = []
        while len(_effects) >= 13:
            _effect,_effects = _effects[1:13],_effects[13:]
            eff_name,magnitude,area,duration,range_,actorvalue,semod,seobj,\
            seschool,sevisual,se_hostile,sename = _effect
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
            sevisuals = int_or_none(sevisual) #OBME not
            # supported (support requires adding a mod/objectid format to
            # the csv, this assumes visual MGEFCode is raw)
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
        effectFormat = ',,"%s","%d","%d","%d","%s","%s"'
        scriptEffectFormat = ',"%s","0x%06X","%s","%s","%s","%s"'
        noscriptEffectFiller = ',"None","None","None","None","None","None"'
        output = []
        for effect in effects:
            efname, magnitude, area, duration, range_, actorvalue = \
                sig_to_str(effect.effect_sig), effect.magnitude, effect.area, \
                effect.duration, effect.recipient, effect.actorValue
            range_ = recipientTypeNumber_Name.get(range_,range_)
            actorvalue = actorValueNumber_Name.get(actorvalue,actorvalue)
            output.append(effectFormat % (
                efname,magnitude,area,duration,range_,actorvalue))
            if effect.scriptEffect: ##: #480 - setDefault commit - return None
                se = effect.scriptEffect
                longid, seschool, sevisual, seflags, sename = \
                    se.script_fid, se.school, se.visual, se.flags, se.full
                sevisual = 'NONE' if sevisual == null4 else sig_to_str(
                    sevisual)
                seschool = schoolTypeNumber_Name.get(seschool,seschool)
                output.append(scriptEffectFormat % (*longid,
                    seschool, sevisual, bool(int(seflags)), sename))
            else:
                output.append(noscriptEffectFiller)
        return ''.join(output)

    # Tweaks APIs -------------------------------------------------------------
    def is_harmful(self, cached_hostile):
        """Return True if all of the effects on the specified record are
        harmful/hostile."""
        for rec_eff in self.effects:
            is_effect_hostile = se.flags.hostile if (se := rec_eff.scriptEffect
                ) else rec_eff.effect_sig in cached_hostile
            if not is_effect_hostile:
                return False
        return True

#------------------------------------------------------------------------------
class MreLeveledList(AMreLeveledList):
    """Leveled item/creature/spell list."""
    top_copy_attrs = ('script_fid', 'template', 'chanceNone',)

    melSet = MelSet(
        MelEdid(),
        MelLevListLvld(),
        MelUInt8Flags(b'LVLF', u'flags', AMreLeveledList._flags),
        MelScript(), # LVLC only
        MelFid(b'TNAM','template'),
        MelLLItems(),
        MelNull(b'DATA'),
    )

#------------------------------------------------------------------------------
# Oblivion Records ------------------------------------------------------------
#------------------------------------------------------------------------------
class MreTes4(AMreHeader):
    """TES4 Record.  File header."""
    rec_sig = b'TES4'
    _post_masters_sigs = set()

    melSet = MelSet(
        MelStruct(b'HEDR', [u'f', u'2I'], (u'version', 1.0), u'numRecords',
            (u'nextObject', 0x800)),
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
        MelFid(b'NAME', u'base'),
        # both unused
        MelNull(b'XPCI'),
        MelNull(b'FULL'),
        MelXlod(),
        MelEnableParent(),
        MelFid(b'XMRC', u'merchantContainer'),
        MelFid(b'XHRS', u'horse'),
        MelBase(b'XRGD', u'xrgd_p'), # Ragdoll Data, bytearray
        MelRefScale(),
        MelRef3D(),
    )

#------------------------------------------------------------------------------
class MreAcre(MelRecord):
    """Placed Creature."""
    rec_sig = b'ACRE'

    melSet = MelSet(
        MelEdid(),
        MelFid(b'NAME', u'base'),
        MelOwnershipTes4(),
        MelEnableParent(),
        MelBase(b'XRGD', u'xrgd_p'), # Ragdoll Data, bytearray
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
class MreAlch(MreHasEffects, MelRecord):
    """Potion."""
    rec_sig = b'ALCH'

    _flags = Flags.from_names('autoCalc', 'alch_is_food')

    melSet = MelSet(
        MelEdid(),
        MelObme(),
        MelFull(),
        MelModel(),
        MelIcon(),
        MelScript(),
        MelWeight(),
        MelStruct(b'ENIT', [u'i', u'B', u'3s'],'value',(_flags, u'flags'),'unused1'),
        MelEffectsTes4(),
        MelEffectsTes4ObmeFull(),
    ).with_distributor(_effects_distributor)

#------------------------------------------------------------------------------
class MreAmmo(MelRecord):
    """Ammunition."""
    rec_sig = b'AMMO'

    _flags = Flags.from_names('notNormalWeapon')

    melSet = MelSet(
        MelEdid(),
        MelFull(),
        MelModel(),
        MelIcon(),
        MelEnchantment(b'ENAM'),
        MelUInt16(b'ANAM', 'enchantPoints'),
        MelStruct(b'DATA', [u'f', u'B', u'3s', u'I', u'f', u'H'], 'speed', (_flags, u'flags'),
                  'unused1', 'value', 'weight', 'damage'),
    )

#------------------------------------------------------------------------------
class MreAnio(MelRecord):
    """Animation Object."""
    rec_sig = b'ANIO'

    melSet = MelSet(
        MelEdid(),
        MelModel(),
        MelFid(b'DATA','animationId'),
    )

#------------------------------------------------------------------------------
class MreAppa(MelRecord):
    """Alchemical Apparatus."""
    rec_sig = b'APPA'

    melSet = MelSet(
        MelEdid(),
        MelFull(),
        MelModel(),
        MelIcon(),
        MelScript(),
        MelStruct(b'DATA', [u'B', u'I', u'f', u'f'], 'apparatus', ('value', 25),
                  ('weight', 1), ('quality', 10)),
    )

#------------------------------------------------------------------------------
class MreArmo(MelRecord):
    """Armor."""
    rec_sig = b'ARMO'

    _flags = BipedFlags.from_names((16, u'hideRings'), (17, u'hideAmulet'),
                                   (22, u'notPlayable'), (23, u'heavy_armor'))

    melSet = MelSet(
        MelEdid(),
        MelFull(),
        MelScript(),
        MelEnchantment(b'ENAM'),
        MelUInt16(b'ANAM', 'enchantPoints'),
        MelUInt32Flags(b'BMDT', u'biped_flags', _flags),
        MelModel(b'MODL', 'maleBody'),
        MelModel(b'MOD2', 'maleWorld'),
        MelIcon(u'maleIconPath'),
        MelModel(b'MOD3', 'femaleBody'),
        MelModel(b'MOD4', 'femaleWorld'),
        MelIco2(u'femaleIconPath'),
        MelStruct(b'DATA', [u'H', u'I', u'I', u'f'],'strength','value','health','weight'),
    )

#------------------------------------------------------------------------------
class MreBook(MelRecord):
    """Book."""
    rec_sig = b'BOOK'

    _flags = Flags.from_names('isScroll', 'isFixed')

    melSet = MelSet(
        MelEdid(),
        MelFull(),
        MelModel(),
        MelIcon(),
        MelBookText(),
        MelScript(),
        MelEnchantment(b'ENAM'),
        MelUInt16(b'ANAM', 'enchantPoints'),
        MelStruct(b'DATA', [u'B', u'b', u'I', u'f'], (_flags, u'flags'), ('teaches', -1),
                  'value', 'weight'),
    )

#------------------------------------------------------------------------------
class MreBsgn(MelRecord):
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

    cellFlags = Flags.from_names(
        (0, u'isInterior'),
        (1, u'hasWater'),
        (2, u'invertFastTravel'),
        (3, u'forceHideLand'),
        (5, u'publicPlace'),
        (6, u'handChanged'),
        (7, u'behaveLikeExterior')
    )

    melSet = MelSet(
        MelEdid(),
        MelFull(),
        MelUInt8Flags(b'DATA', u'flags', cellFlags),
        # None defaults here are on purpose - XCLC does not necessarily exist,
        # but 0 is a valid value for both coordinates (duh)
        MelSkipInterior(MelOptStruct(b'XCLC', ['2i'],
                                     ('posX', None), ('posY', None))),
        MelOptStruct(b'XCLL', ['3B', 's', '3B', 's', '3B', 's', '2f', '2i',
            '2f'], 'ambientRed', 'ambientGreen', 'ambientBlue', 'unused1',
            'directionalRed', 'directionalGreen', 'directionalBlue', 'unused2',
            'fogRed', 'fogGreen', 'fogBlue', 'unused3', 'fogNear', 'fogFar',
            'directionalXY', 'directionalZ', 'directionalFade', 'fogClip'),
        MelRegions(),
        MelUInt8(b'XCMT', u'music'),
        MelFloat(b'XCLW', u'waterHeight'),
        MelFid(b'XCCM', u'climate'),
        MelFid(b'XCWT', u'water'),
        MelOwnershipTes4(),
    )

#------------------------------------------------------------------------------
class MreClas(MelRecord):
    """Class."""
    rec_sig = b'CLAS'

    _flags = Flags.from_names(u'class_playable', u'class_guard')

    melSet = MelSet(
        MelEdid(),
        MelFull(),
        MelDescription(),
        MelIcon(),
        MelTruncatedStruct(b'DATA', [u'2i', u'I', u'7i', u'2I', u'b', u'B', u'2s'], 'primary1', 'primary2',
                           'specialization', 'major1', 'major2', 'major3',
                           'major4', 'major5', 'major6', 'major7',
                           (_flags, u'flags'), (aiService, u'services'),
                           'trainSkill', 'trainLevel',
                           'unused1', old_versions={'2iI7i2I'}),
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
class MreClot(MelRecord):
    """Clothing."""
    rec_sig = b'CLOT'

    _flags = BipedFlags.from_names((16, u'hideRings'), (17, u'hideAmulet'),
                                   (22, u'notPlayable'))

    melSet = MelSet(
        MelEdid(),
        MelFull(),
        MelScript(),
        MelEnchantment(b'ENAM'),
        MelUInt16(b'ANAM', 'enchantPoints'),
        MelUInt32Flags(b'BMDT', u'biped_flags', _flags),
        MelModel(b'MODL', 'maleBody'),
        MelModel(b'MOD2', 'maleWorld'),
        MelIcon(u'maleIconPath'),
        MelModel(b'MOD3', 'femaleBody'),
        MelModel(b'MOD4', 'femaleWorld'),
        MelIco2(u'femaleIconPath'),
        MelValueWeight(),
    )

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

    _flags = Flags.from_names(
        ( 0,'biped'),
        ( 1,'essential'),
        ( 2,'weaponAndShield'),
        ( 3,'respawn'),
        ( 4,'swims'),
        ( 5,'flies'),
        ( 6,'walks'),
        ( 7,'pcLevelOffset'),
        ( 9,'noLowLevel'),
        (11,'noBloodSpray'),
        (12,'noBloodDecal'),
        (15,'noHead'),
        (16,'noRightArm'),
        (17,'noLeftArm'),
        (18,'noCombatInWater'),
        (19,'noShadow'),
        (20,'noCorpseCheck'),
    )

    melSet = MelSet(
        MelEdid(),
        MelFull(),
        MelModel(),
        MelItems(),
        MelSpellsTes4(),
        MelBodyParts(),
        MelBase(b'NIFT','nift_p'), # Texture File Hashes
        MelStruct(b'ACBS', [u'I', u'3H', u'h', u'2H'],
            (_flags, u'flags'),'baseSpell','fatigue','barterGold',
            ('level_offset',1),'calcMin','calcMax'),
        MelFactions(),
        MelFid(b'INAM','deathItem'),
        MelScript(),
        MelStruct(b'AIDT', [u'4B', u'I', u'b', u'B', u'2s'],
            ('aggression',5),('confidence',50),('energyLevel',50),
            ('responsibility',50),(aiService, u'services'),'trainSkill',
            'trainLevel','unused1'),
        MelFids('aiPackages', MelFid(b'PKID')),
        MelAnimations(),
        MelStruct(b'DATA', [u'5B', u's', u'H', u'2s', u'H', u'8B'],'creatureType','combatSkill','magic',
                  'stealth','soul','unused2','health',
                  'unused3','attackDamage','strength','intelligence',
                  'willpower','agility','speed','endurance','personality',
                  'luck'),
        MelUInt8(b'RNAM', 'attackReach'),
        MelFid(b'ZNAM','combatStyle'),
        MelFloat(b'TNAM', 'turningSpeed'),
        MelFloat(b'BNAM', 'baseScale'),
        MelFloat(b'WNAM', 'footWeight'),
        MelString(b'NAM0','bloodSprayPath'),
        MelString(b'NAM1','bloodDecalPath'),
        MelFid(b'CSCR','inheritsSoundsFrom'),
        MelActorSounds(),
    )

#------------------------------------------------------------------------------
class MreCsty(MelRecord):
    """Combat Style."""
    rec_sig = b'CSTY'

    _csty_flags1 = Flags.from_names(
        'advanced',
        'use_chance_for_attack',
        'ignore_allies',
        'will_yield',
        'rejects_yields',
        'fleeing_disabled',
        'prefers_ranged',
        'melee_alert_ok',
    )
    _csty_flags2 = Flags.from_names('do_not_acquire')

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
            (_csty_flags1, 'csty_flags1'), 'acro_dodge', 'unused5',
            ('r_mult_opt', 1.0), ('r_mult_max', 1.0), ('m_distance', 250.0),
            ('r_distance', 1000.0), ('buff_stand', 325.0), ('r_stand', 500.0),
            ('group_stand', 325.0), ('rush_chance', 25), 'unused6',
            ('rush_mult', 1.0), (_csty_flags2, 'csty_flags2'), old_versions={
                '2B2s8f2B2s3fB3s2f5B3s2f2B2s7fB3sf',
                '2B2s8f2B2s3fB3s2f5B3s2f2B2s7f',
                '2B2s8f2B2s3fB3s2f5B3s2f2B2s5f',
                '2B2s8f2B2s3fB3s2f5B3s2f2B2s2f',
                '2B2s8f2B2s3fB3s2f5B3s2f2B2s',
            }),
        MelOptStruct(b'CSAD', ['21f'], 'dodge_fmult', 'dodge_fbase',
            'enc_sbase', 'enc_smult', 'dodge_atk_mult', 'dodge_natk_mult',
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
        MelSorted(MelFids('added_quests', MelFid(b'QSTI'))),
        MelSorted(MelFids('removed_quests', MelFid(b'QSTR'))),
        MelFull(),
        MelUInt8(b'DATA', u'dialType'),
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

    _efsh_flags = Flags.from_names(
        (0, 'no_membrane_shader'),
        (3, 'no_particle_shader'),
        (4, 'ee_inverse'),
        (5, 'affect_skin_only'),
    )

    melSet = MelSet(
        MelEdid(),
        MelIcon('fill_texture'),
        MelIco2('particle_texture'),
        MelTruncatedStruct(b'DATA',
            ['B', '3s', '3I', '3B', 's', '9f', '3B', 's', '8f', '5I', '19f',
             '3B', 's', '3B', 's', '3B', 's', '6f'],
            (_efsh_flags, 'efsh_flags'), 'unused1', 'ms_source_blend_mode',
            'ms_blend_operation', 'ms_z_test_function', 'fill_color1_red',
            'fill_color1_green', 'fill_color1_blue', 'unused2',
            'fill_alpha_fade_in_time', 'fill_full_alpha_time',
            'fill_alpha_fade_out_time', 'fill_persistent_alpha_ratio',
            'fill_alpha_pulse_amplitude', 'fill_alpha_pulse_frequency',
            'fill_texture_animation_speed_u', 'fill_texture_animation_speed_v',
            'ee_fall_off', 'ee_color_red', 'ee_color_green', 'ee_color_blue',
            'unused3', 'ee_alpha_fade_in_time', 'ee_full_alpha_time',
            'ee_alpha_fade_out_time', 'ee_persistent_alpha_ratio',
            'ee_alpha_pulse_amplitude', 'ee_alpha_pulse_frequency',
            'fill_full_alpha_ratio', 'ee_full_alpha_ratio',
            'ms_dest_blend_mode', ('ps_source_blend_mode', 5),
            ('ps_blend_operation', 1), ('ps_z_test_function', 4),
            ('ps_dest_blend_mode', 6), 'ps_particle_birth_ramp_up_time',
            'ps_full_particle_birth_time', 'ps_particle_birth_ramp_down_time',
            ('ps_full_particle_birth_ratio', 1.0),
            ('ps_persistent_particle_birth_ratio', 1.0),
            ('ps_particle_lifetime', 1.0), 'ps_particle_lifetime_delta',
            'ps_initial_speed_along_normal', 'ps_acceleration_along_normal',
            'ps_initial_velocity1', 'ps_initial_velocity2',
            'ps_initial_velocity3', 'ps_acceleration1', 'ps_acceleration2',
            'ps_acceleration3', 'ps_scale_key1', ('ps_scale_key2', 1.0),
            'ps_scale_key1_time', ('ps_scale_key2_time', 1.0),
            ('color_key1_red', 255), ('color_key1_green', 255),
            ('color_key1_blue', 255), 'unused4', ('color_key2_red', 255),
            ('color_key2_green', 255), ('color_key2_blue', 255), 'unused5',
            ('color_key3_red', 255), ('color_key3_green', 255),
            ('color_key3_blue', 255), 'unused6', ('color_key1_alpha', 1.0),
            ('color_key2_alpha', 1.0), ('color_key3_alpha', 1.0),
            'color_key1_time', ('color_key2_time', 0.5),
            ('color_key3_time', 1.0), old_versions={'B3s3I3Bs9f3Bs8fI'}),
    )

#------------------------------------------------------------------------------
class MreEnch(MreHasEffects, MelRecord):
    """Enchantment."""
    rec_sig = b'ENCH'

    _enit_flags = Flags.from_names('ench_no_auto_calc')

    melSet = MelSet(
        MelEdid(),
        MelObme(),
        MelFull(), #--At least one mod has this. Odd.
        MelStruct(b'ENIT', ['3I', 'B', '3s'], 'item_type', 'charge_amount',
            'enchantment_cost', (_enit_flags, 'enit_flags'), 'unused1'),
        MelEffectsTes4(),
        MelEffectsTes4ObmeFull(),
    ).with_distributor(_effects_distributor)

#------------------------------------------------------------------------------
class MreFact(MelRecord):
    """Faction."""
    rec_sig = b'FACT'

    _fact_flags = Flags.from_names('hidden_from_pc', 'evil', 'special_combat')

    melSet = MelSet(
        MelEdid(),
        MelFull(),
        MelRelations(with_gcr=False),
        MelUInt8Flags(b'DATA', 'fact_flags', _fact_flags),
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

    _info_response_flags = Flags.from_names('goodbye', 'random', 'say_once',
        'run_immediately', 'info_refusal', 'random_end', 'run_for_rumors')

    melSet = MelSet(
        MelTruncatedStruct(b'DATA', ['3B'], 'info_type', 'next_speaker',
            (_info_response_flags, 'response_flags'), old_versions={'2B'}),
        MelFid(b'QSTI', 'info_quest'),
        MelFid(b'TPIC', 'info_topic'),
        MelFid(b'PNAM', 'prev_info'),
        MelFids('add_topics', MelFid(b'NAME')),
        MelGroups('info_responses',
            MelStruct(b'TRDT', ['I', 'i', '4s', 'B', '3s'], 'rd_emotion_type',
                'rd_emotion_value', 'rd_unused1', 'rd_response_number',
                'rd_unused2'),
            MelString(b'NAM1', 'response_text'),
            MelString(b'NAM2', 'script_notes'),
        ),
        MelConditionsTes4(),
        MelFids('info_choices', MelFid(b'TCLT')),
        MelFids('link_from', MelFid(b'TCLF')),
        MelEmbeddedScript(),
    )

#------------------------------------------------------------------------------
class MreIngr(MreHasEffects, MelRecord):
    """Ingredient."""
    rec_sig = b'INGR'

    _flags = Flags.from_names('ingr_no_auto_calc', 'ingr_is_food')

    melSet = MelSet(
        MelEdid(),
        MelObme(),
        MelFull(),
        MelModel(),
        MelIcon(),
        MelScript(),
        MelWeight(),
        MelStruct(b'ENIT', [u'i', u'B', u'3s'],'value',(_flags, u'flags'),'unused1'),
        MelEffectsTes4(),
        MelEffectsTes4ObmeFull(),
    ).with_distributor(_effects_distributor)

#------------------------------------------------------------------------------
class MreKeym(MelRecord):
    """Key."""
    rec_sig = b'KEYM'

    melSet = MelSet(
        MelEdid(),
        MelFull(),
        MelModel(),
        MelIcon(),
        MelScript(),
        MelValueWeight(),
    )

#------------------------------------------------------------------------------
class MreLand(MelRecord):
    """Landscape."""
    rec_sig = b'LAND'

    melSet = MelSet(
        MelLandShared(),
    )

#------------------------------------------------------------------------------
class MreLigh(MelRecord):
    """Light."""
    rec_sig = b'LIGH'

    _flags = Flags.from_names(
        'dynamic', 'canTake', 'negative', 'flickers', 'unk1', 'offByDefault',
        'flickerSlow', 'pulse', 'pulseSlow', 'spotLight', 'spotShadow')

    melSet = MelSet(
        MelEdid(),
        MelModel(),
        MelScript(),
        MelFull(),
        MelIcon(),
        MelTruncatedStruct(b'DATA',
            [u'i', u'I', u'3B', u's', u'I', u'f', u'f', u'I', u'f'],
            'duration', 'radius', 'red', 'green', 'blue', 'unused1',
            (_flags, u'flags'), 'falloff', 'fov', 'value', 'weight',
            old_versions={'iI3BsI2f'}),
        MelFloat(b'FNAM', u'fade'),
        MelSound(),
    )

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

    _flags = Flags.from_names(
        ( 0,'stone'),
        ( 1,'cloth'),
        ( 2,'dirt'),
        ( 3,'glass'),
        ( 4,'grass'),
        ( 5,'metal'),
        ( 6,'organic'),
        ( 7,'skin'),
        ( 8,'water'),
        ( 9,'wood'),
        (10,'heavyStone'),
        (11,'heavyMetal'),
        (12,'heavyWood'),
        (13,'chain'),
        (14,'snow')
    )

    melSet = MelSet(
        MelEdid(),
        MelIcon(),
        MelOptStruct(b'HNAM', [u'3B'], (_flags, 'flags'), 'friction',
                     'restitution'), ##: flags are actually an enum....
        MelUInt8(b'SNAM', 'specular'),
        MelSorted(MelFids('grass', MelFid(b'GNAM'))),
    )

#------------------------------------------------------------------------------
class MreLvlc(MreLeveledList):
    """Leveled Creature."""
    rec_sig = b'LVLC'

#------------------------------------------------------------------------------
class MreLvli(MreLeveledList):
    """Leveled Item."""
    rec_sig = b'LVLI'

#------------------------------------------------------------------------------
class MreLvsp(MreLeveledList):
    """Leveled Spell."""
    rec_sig = b'LVSP'

#------------------------------------------------------------------------------
class MreMgef(MelRecord):
    """Magic Effect."""
    rec_sig = b'MGEF'

    _obme_flag_overrides = Flags.from_names(
        ( 2,  u'ov_param_flag_a'),
        ( 3,  u'ov_beneficial'),
        (16, u'ov_param_flag_b'),
        (17, u'ov_magnitude_is_range'),
        (18, u'ov_atomic_resistance'),
        (19, u'ov_param_flag_c'),
        (20, u'ov_param_flag_d'),
        (30, u'ov_hidden'),
    )
    _flags = Flags.from_names(
        ( 0, u'hostile'),
        ( 1, u'recover'),
        ( 2, u'detrimental'),
        ( 3, u'magnitude'),
        ( 4, u'self'),
        ( 5, u'touch'),
        ( 6, u'target'),
        ( 7, u'noDuration'),
        ( 8, u'noMagnitude'),
        ( 9, u'noArea'),
        (10, u'fxPersist'),
        (11, u'spellmaking'),
        (12, u'enchanting'),
        (13, u'noIngredient'),
        (16, u'useWeapon'),
        (17, u'useArmor'),
        (18, u'useCreature'),
        (19, u'useSkill'),
        (20, u'useAttr'),
        (24, u'useAV'),
        (25, u'sprayType'),
        (26, u'boltType'),
        (27, u'noHitEffect')
    )

    _magic_effects = {
        b'ABAT': [5, _(u'Absorb Attribute'), 0.95],
        b'ABFA': [5, _(u'Absorb Fatigue'), 6],
        b'ABHE': [5, _(u'Absorb Health'), 16],
        b'ABSK': [5, _(u'Absorb Skill'), 2.1],
        b'ABSP': [5, _(u'Absorb Magicka'), 7.5],
        b'BA01': [1, _(u'Bound Armor Extra 01'), 0],#--Formid == 0
        b'BA02': [1, _(u'Bound Armor Extra 02'), 0],#--Formid == 0
        b'BA03': [1, _(u'Bound Armor Extra 03'), 0],#--Formid == 0
        b'BA04': [1, _(u'Bound Armor Extra 04'), 0],#--Formid == 0
        b'BA05': [1, _(u'Bound Armor Extra 05'), 0],#--Formid == 0
        b'BA06': [1, _(u'Bound Armor Extra 06'), 0],#--Formid == 0
        b'BA07': [1, _(u'Bound Armor Extra 07'), 0],#--Formid == 0
        b'BA08': [1, _(u'Bound Armor Extra 08'), 0],#--Formid == 0
        b'BA09': [1, _(u'Bound Armor Extra 09'), 0],#--Formid == 0
        b'BA10': [1, _(u'Bound Armor Extra 10'), 0],#--Formid == 0
        b'BABO': [1, _(u'Bound Boots'), 12],
        b'BACU': [1, _(u'Bound Cuirass'), 12],
        b'BAGA': [1, _(u'Bound Gauntlets'), 8],
        b'BAGR': [1, _(u'Bound Greaves'), 12],
        b'BAHE': [1, _(u'Bound Helmet'), 12],
        b'BASH': [1, _(u'Bound Shield'), 12],
        b'BRDN': [0, _(u'Burden'), 0.21],
        b'BW01': [1, _(u'Bound Order Weapon 1'), 1],
        b'BW02': [1, _(u'Bound Order Weapon 2'), 1],
        b'BW03': [1, _(u'Bound Order Weapon 3'), 1],
        b'BW04': [1, _(u'Bound Order Weapon 4'), 1],
        b'BW05': [1, _(u'Bound Order Weapon 5'), 1],
        b'BW06': [1, _(u'Bound Order Weapon 6'), 1],
        b'BW07': [1, _(u'Summon Staff of Sheogorath'), 1],
        b'BW08': [1, _(u'Bound Priest Dagger'), 1],
        b'BW09': [1, _(u'Bound Weapon Extra 09'), 0],#--Formid == 0
        b'BW10': [1, _(u'Bound Weapon Extra 10'), 0],#--Formid == 0
        b'BWAX': [1, _(u'Bound Axe'), 39],
        b'BWBO': [1, _(u'Bound Bow'), 95],
        b'BWDA': [1, _(u'Bound Dagger'), 14],
        b'BWMA': [1, _(u'Bound Mace'), 91],
        b'BWSW': [1, _(u'Bound Sword'), 235],
        b'CALM': [3, _(u'Calm'), 0.47],
        b'CHML': [3, _(u'Chameleon'), 0.63],
        b'CHRM': [3, _(u'Charm'), 0.2],
        b'COCR': [3, _(u'Command Creature'), 0.6],
        b'COHU': [3, _(u'Command Humanoid'), 0.75],
        b'CUDI': [5, _(u'Cure Disease'), 1400],
        b'CUPA': [5, _(u'Cure Paralysis'), 500],
        b'CUPO': [5, _(u'Cure Poison'), 600],
        b'DARK': [3, _(u'DO NOT USE - Darkness'), 0],
        b'DEMO': [3, _(u'Demoralize'), 0.49],
        b'DGAT': [2, _(u'Damage Attribute'), 100],
        b'DGFA': [2, _(u'Damage Fatigue'), 4.4],
        b'DGHE': [2, _(u'Damage Health'), 12],
        b'DGSP': [2, _(u'Damage Magicka'), 2.45],
        b'DIAR': [2, _(u'Disintegrate Armor'), 6.2],
        b'DISE': [2, _(u'Disease Info'), 0], #--Formid == 0
        b'DIWE': [2, _(u'Disintegrate Weapon'), 6.2],
        b'DRAT': [2, _(u'Drain Attribute'), 0.7],
        b'DRFA': [2, _(u'Drain Fatigue'), 0.18],
        b'DRHE': [2, _(u'Drain Health'), 0.9],
        b'DRSK': [2, _(u'Drain Skill'), 0.65],
        b'DRSP': [2, _(u'Drain Magicka'), 0.18],
        b'DSPL': [4, _(u'Dispel'), 3.6],
        b'DTCT': [4, _(u'Detect Life'), 0.08],
        b'DUMY': [2, _(u'Mehrunes Dagon'), 0], #--Formid == 0
        b'FIDG': [2, _(u'Fire Damage'), 7.5],
        b'FISH': [0, _(u'Fire Shield'), 0.95],
        b'FOAT': [5, _(u'Fortify Attribute'), 0.6],
        b'FOFA': [5, _(u'Fortify Fatigue'), 0.04],
        b'FOHE': [5, _(u'Fortify Health'), 0.14],
        b'FOMM': [5, _(u'Fortify Magicka Multiplier'), 0.04],
        b'FOSK': [5, _(u'Fortify Skill'), 0.6],
        b'FOSP': [5, _(u'Fortify Magicka'), 0.15],
        b'FRDG': [2, _(u'Frost Damage'), 7.4],
        b'FRNZ': [3, _(u'Frenzy'), 0.04],
        b'FRSH': [0, _(u'Frost Shield'), 0.95],
        b'FTHR': [0, _(u'Feather'), 0.1],
        b'INVI': [3, _(u'Invisibility'), 40],
        b'LGHT': [3, _(u'Light'), 0.051],
        b'LISH': [0, _(u'Shock Shield'), 0.95],
        b'LOCK': [0, _(u'DO NOT USE - Lock'), 30],
        b'MYHL': [1, _(u'Summon Mythic Dawn Helm'), 110],
        b'MYTH': [1, _(u'Summon Mythic Dawn Armor'), 120],
        b'NEYE': [3, _(u'Night-Eye'), 22],
        b'OPEN': [0, _(u'Open'), 4.3],
        b'PARA': [3, _(u'Paralyze'), 475],
        b'POSN': [2, _(u'Poison Info'), 0],
        b'RALY': [3, _(u'Rally'), 0.03],
        b'REAN': [1, _(u'Reanimate'), 10],
        b'REAT': [5, _(u'Restore Attribute'), 38],
        b'REDG': [4, _(u'Reflect Damage'), 2.5],
        b'REFA': [5, _(u'Restore Fatigue'), 2],
        b'REHE': [5, _(u'Restore Health'), 10],
        b'RESP': [5, _(u'Restore Magicka'), 2.5],
        b'RFLC': [4, _(u'Reflect Spell'), 3.5],
        b'RSDI': [5, _(u'Resist Disease'), 0.5],
        b'RSFI': [5, _(u'Resist Fire'), 0.5],
        b'RSFR': [5, _(u'Resist Frost'), 0.5],
        b'RSMA': [5, _(u'Resist Magic'), 2],
        b'RSNW': [5, _(u'Resist Normal Weapons'), 1.5],
        b'RSPA': [5, _(u'Resist Paralysis'), 0.75],
        b'RSPO': [5, _(u'Resist Poison'), 0.5],
        b'RSSH': [5, _(u'Resist Shock'), 0.5],
        b'RSWD': [5, _(u'Resist Water Damage'), 0], #--Formid == 0
        b'SABS': [4, _(u'Spell Absorption'), 3],
        b'SEFF': [0, _(u'Script Effect'), 0],
        b'SHDG': [2, _(u'Shock Damage'), 7.8],
        b'SHLD': [0, _(u'Shield'), 0.45],
        b'SLNC': [3, _(u'Silence'), 60],
        b'STMA': [2, _(u'Stunted Magicka'), 0],
        b'STRP': [4, _(u'Soul Trap'), 30],
        b'SUDG': [2, _(u'Sun Damage'), 9],
        b'TELE': [4, _(u'Telekinesis'), 0.49],
        b'TURN': [1, _(u'Turn Undead'), 0.083],
        b'VAMP': [2, _(u'Vampirism'), 0],
        b'WABR': [0, _(u'Water Breathing'), 14.5],
        b'WAWA': [0, _(u'Water Walking'), 13],
        b'WKDI': [2, _(u'Weakness to Disease'), 0.12],
        b'WKFI': [2, _(u'Weakness to Fire'), 0.1],
        b'WKFR': [2, _(u'Weakness to Frost'), 0.1],
        b'WKMA': [2, _(u'Weakness to Magic'), 0.25],
        b'WKNW': [2, _(u'Weakness to Normal Weapons'), 0.25],
        b'WKPO': [2, _(u'Weakness to Poison'), 0.1],
        b'WKSH': [2, _(u'Weakness to Shock'), 0.1],
        b'Z001': [1, _(u'Summon Rufio\'s Ghost'), 13],
        b'Z002': [1, _(u'Summon Ancestor Guardian'), 33.3],
        b'Z003': [1, _(u'Summon Spiderling'), 45],
        b'Z004': [1, _(u'Summon Flesh Atronach'), 1],
        b'Z005': [1, _(u'Summon Bear'), 47.3],
        b'Z006': [1, _(u'Summon Gluttonous Hunger'), 61],
        b'Z007': [1, _(u'Summon Ravenous Hunger'), 123.33],
        b'Z008': [1, _(u'Summon Voracious Hunger'), 175],
        b'Z009': [1, _(u'Summon Dark Seducer'), 1],
        b'Z010': [1, _(u'Summon Golden Saint'), 1],
        b'Z011': [1, _(u'Wabba Summon'), 0],
        b'Z012': [1, _(u'Summon Decrepit Shambles'), 45],
        b'Z013': [1, _(u'Summon Shambles'), 87.5],
        b'Z014': [1, _(u'Summon Replete Shambles'), 150],
        b'Z015': [1, _(u'Summon Hunger'), 22],
        b'Z016': [1, _(u'Summon Mangled Flesh Atronach'), 22],
        b'Z017': [1, _(u'Summon Torn Flesh Atronach'), 32.5],
        b'Z018': [1, _(u'Summon Stitched Flesh Atronach'), 75.5],
        b'Z019': [1, _(u'Summon Sewn Flesh Atronach'), 195],
        b'Z020': [1, _(u'Extra Summon 20'), 0],
        b'ZCLA': [1, _(u'Summon Clannfear'), 75.56],
        b'ZDAE': [1, _(u'Summon Daedroth'), 123.33],
        b'ZDRE': [1, _(u'Summon Dremora'), 72.5],
        b'ZDRL': [1, _(u'Summon Dremora Lord'), 157.14],
        b'ZFIA': [1, _(u'Summon Flame Atronach'), 45],
        b'ZFRA': [1, _(u'Summon Frost Atronach'), 102.86],
        b'ZGHO': [1, _(u'Summon Ghost'), 22],
        b'ZHDZ': [1, _(u'Summon Headless Zombie'), 56],
        b'ZLIC': [1, _(u'Summon Lich'), 350],
        b'ZSCA': [1, _(u'Summon Scamp'), 30],
        b'ZSKA': [1, _(u'Summon Skeleton Guardian'), 32.5],
        b'ZSKC': [1, _(u'Summon Skeleton Champion'), 152],
        b'ZSKE': [1, _(u'Summon Skeleton'), 11.25],
        b'ZSKH': [1, _(u'Summon Skeleton Hero'), 66],
        b'ZSPD': [1, _(u'Summon Spider Daedra'), 195],
        b'ZSTA': [1, _(u'Summon Storm Atronach'), 125],
        b'ZWRA': [1, _(u'Summon Faded Wraith'), 87.5],
        b'ZWRL': [1, _(u'Summon Gloom Wraith'), 260],
        b'ZXIV': [1, _(u'Summon Xivilai'), 200],
        b'ZZOM': [1, _(u'Summon Zombie'), 16.67],
    }
    mgef_school = {x: y for x, [y, z, a] in _magic_effects.items()}
    mgef_name = {x: z for x, [y, z, a] in _magic_effects.items()}
    mgef_basevalue = {x: a for x, [y, z, a] in _magic_effects.items()}

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
        MelEdid(),
        MelObme(extra_format=['2B', '2s', '4s', 'I', '4s'], extra_contents=[
            u'obme_param_a_info', u'obme_param_b_info', u'obme_unused_mgef',
            u'obme_handler', (_obme_flag_overrides, u'obme_flag_overrides'),
            u'obme_param_b']),
        MelUnion({
            None: MelNull(b'EDDX'), # discard for non-OBME records
        }, decider=AttrValDecider(u'obme_record_version'),
            fallback=MelString(b'EDDX', u'obme_eid')),
        MelFull(),
        MelDescription(),
        MelIcon(),
        MelModel(),
        MelPartialCounter(MelTruncatedStruct(b'DATA',
            ['I', 'f', 'I', 'i', 'i', 'H', '2s', 'I', 'f', '6I',
             '2f'], (_flags, 'flags'), 'base_cost', (FID, 'associated_item'),
            'school', 'resist_value', 'counter_effect_count', 'unused1',
            (FID, 'light'), 'projectileSpeed', (FID, 'effectShader'),
            (FID, 'enchantEffect'), (FID, 'castingSound'), (FID, 'boltSound'),
            (FID, 'hitSound'), (FID, 'areaSound'), 'cef_enchantment',
            'cef_barter', old_versions={'IfIiiH2sIfI'}),
            counters={'counter_effect_count': 'counter_effects'}),
        MelSorted(MelArray(u'counter_effects',
            MelStruct(b'ESCE', [u'4s'], u'counter_effect_code'),
        ), sort_by_attrs='counter_effect_code'),
    )

#------------------------------------------------------------------------------
class MreMisc(MelRecord):
    """Misc. Item."""
    rec_sig = b'MISC'

    melSet = MelSet(
        MelEdid(),
        MelFull(),
        MelModel(),
        MelIcon(),
        MelScript(),
        MelUnion({
            False: MelValueWeight(),
            True: MelStruct(b'DATA', [u'2I'], (FID, u'value'), u'weight'),
        }, decider=FlagDecider(u'flags1', [u'borderRegion', u'turnFireOff'])),
    )

#------------------------------------------------------------------------------
class MreNpc_(AMreActor):
    """Non-Player Character."""
    rec_sig = b'NPC_'

    _flags = Flags.from_names(
        ( 0,'female'),
        ( 1,'essential'),
        ( 3,'respawn'),
        ( 4,'autoCalc'),
        ( 7,'pcLevelOffset'),
        ( 9,'noLowLevel'),
        (13,'noRumors'),
        (14,'summonable'),
        (15,'noPersuasion'),
        (20,'canCorpseCheck')
    )

    class MelNpcData(MelLists):
        """Convert npc stats into skills, health, attributes."""
        _attr_indexes = OrderedDict( # 21 skills and 7 attributes
            [(u'skills', slice(21)), (u'health', 21), (u'unused2', 22),
             (u'attributes', slice(23, None))])

    melSet = MelSet(
        MelEdid(),
        MelFull(),
        MelModel(),
        MelStruct(b'ACBS', [u'I', u'3H', u'h', u'2H'],
            (_flags, u'flags'),'baseSpell','fatigue','barterGold',
            ('level_offset',1),'calcMin','calcMax'),
        MelFactions(),
        MelFid(b'INAM','deathItem'),
        MelRace(),
        MelSpellsTes4(),
        MelScript(),
        MelItems(),
        MelStruct(b'AIDT', [u'4B', u'I', u'b', u'B', u'2s'], ('aggression', 5), ('confidence', 50),
                  ('energyLevel', 50), ('responsibility', 50),
                  (aiService, u'services'), 'trainSkill', 'trainLevel',
                  'unused1'),
        MelFids('aiPackages', MelFid(b'PKID')),
        MelAnimations(),
        MelFid(b'CNAM','iclass'),
        MelNpcData(b'DATA', [u'21B', u'H', u'2s', u'8B'],
                   (u'skills', [0 for _x in range(21)]), u'health',
                   u'unused2', (u'attributes', [0 for _y in range(8)])),
        MelFid(b'HNAM', 'hair'),
        MelFloat(b'LNAM', u'hairLength'),
        ##: This is a FormID array in xEdit, but I haven't found any NPC_
        # records with >1 eye. Changing it would also break the NPC Checker
        MelFid(b'ENAM', 'eye'),
        MelStruct(b'HCLR', [u'3B', u's'], 'hairRed', 'hairBlue', 'hairGreen',
                  'unused3'),
        MelFid(b'ZNAM','combatStyle'),
        MelBase(b'FGGS','fggs_p'), ####FaceGen Geometry-Symmetric
        MelBase(b'FGGA','fgga_p'), ####FaceGen Geometry-Asymmetric
        MelBase(b'FGTS','fgts_p'), ####FaceGen Texture-Symmetric
        MelBase(b'FNAM', 'fnam'),
    )

    def setRace(self,race):
        """Set additional race info."""
        self.race = race
        if not self.model:
            self.model = self.getDefault('model')
        if race in (0x23fe9, 0x223c7): # Argonian & Khajiit
            self.model.modPath = u"Characters\\_Male\\SkeletonBeast.NIF"
        else:
            self.model.modPath = u"Characters\\_Male\\skeleton.nif"
        fnams = {
            0x23fe9 : b'\xdc<',    # Argonian
            0x224fc : b'H\x1d',    # Breton
            0x191c1 : b'rT',       # Dark Elf
            0x19204 : b'\xe6!',    # High Elf
            0x00907 : b'\x8e5',    # Imperial
            0x22c37 : b'T[',       # Khajiit
            0x224fd : b'\xb6\x03', # Nord
            0x191c0 : b't\t',      # Orc
            0x00d43 : b'\xa9a',    # Redguard
            0x00019 : b'wD',       # Vampire
            0x223c8 : b'.J',       # Wood Elf
        }
        self.fnam = fnams.get(race, b'\x8e5') # default to Imperial

#------------------------------------------------------------------------------
class MrePack(MelRecord):
    """AI Package."""
    rec_sig = b'PACK'

    _flags = Flags.from_names(
        'offersServices','mustReachLocation','mustComplete','lockAtStart',
        'lockAtEnd','lockAtLocation','unlockAtStart','unlockAtEnd',
        'unlockAtLocation','continueIfPcNear','oncePerDay',None,
        'skipFallout','alwaysRun',None,None,
        None,'alwaysSneak','allowSwimming','allowFalls',
        'unequipArmor','unequipWeapons','defensiveCombat','useHorse',
        'noIdleAnims',)

    melSet = MelSet(
        MelEdid(),
        MelTruncatedStruct(b'PKDT', [u'I', u'B', u'3s'], (_flags, 'flags'),
            'aiType', 'unused1', old_versions={'HBs'}),
        MelUnion({
            (0, 1, 2, 3, 4): MelOptStruct(b'PLDT', ['i', 'I', 'i'], 'locType',
                (FID, 'locId'), 'locRadius'),
            5: MelOptStruct(b'PLDT', ['i', 'I', 'i'], 'locType', 'locId',
                'locRadius'),
        }, decider=PartialLoadDecider(
            loader=MelSInt32(b'PLDT', 'locType'),
            decider=AttrValDecider('locType'),
        )),
        MelStruct(b'PSDT', ['2b', 'B', 'b', 'i'], 'month', 'day', 'date',
            'time', 'duration'),
        MelUnion({
            (0, 1): MelOptStruct(b'PTDT', ['i', 'I', 'i'], 'targetType',
                (FID, 'targetId'), 'targetCount'),
            2: MelOptStruct(b'PTDT', ['i', 'I', 'i'], 'targetType', 'targetId',
                'targetCount'),
        }, decider=PartialLoadDecider(
            loader=MelSInt32(b'PTDT', 'targetType'),
            decider=AttrValDecider('targetType'),
        )),
        MelConditionsTes4(),
    )

#------------------------------------------------------------------------------
class MrePgrd(MelRecord):
    """Path Grid."""
    rec_sig = b'PGRD'

    # Most of these MelBases could be loaded via MelArray, but they're really
    # big, don't contain FormIDs and are too complex to manipulate
    melSet = MelSet(
        MelUInt16(b'DATA', u'point_count'),
        MelBase(b'PGRP', u'point_array'),
        MelBase(b'PGAG', u'unknown1'),
        MelBase(b'PGRR', u'point_to_point_connections'), # sorted
        MelBase(b'PGRI', u'inter_cell_connections'), # sorted
        MelSorted(MelGroups(u'point_to_reference_mappings',
            MelSorted(MelArray(
                u'mapping_points', MelUInt32(b'PGRL', u'm_point'),
                prelude=MelFid(b'PGRL', u'mapping_reference')
            ), sort_by_attrs='m_point'),
        ##: This will sort *before* the sort above, it should be the other way
        # around. Maybe do all this pre-dump processing (sorting, updating
        # counters, etc.) in a new recursive method called before dumpData?
        ), sort_special=lambda e: tuple(p.m_point for p in e.mapping_points)),
    )

#------------------------------------------------------------------------------
class MreQust(MelRecord):
    """Quest."""
    rec_sig = b'QUST'

    _questFlags = Flags.from_names('startGameEnabled', None, 'repeatedTopics',
                                   'repeatedStages')
    stageFlags = Flags.from_names('complete')
    targetFlags = Flags.from_names('ignoresLocks')

    melSet = MelSet(
        MelEdid(),
        MelScript(),
        MelFull(),
        MelIcon(),
        MelStruct(b'DATA', [u'B', u'B'],(_questFlags, u'questFlags'),'priority'),
        MelConditionsTes4(),
        MelSorted(MelGroups('stages',
            MelSInt16(b'INDX', 'stage'),
            MelGroups('entries',
                MelUInt8Flags(b'QSDT', u'flags', stageFlags),
                MelConditionsTes4(),
                MelString(b'CNAM','text'),
                MelEmbeddedScript(),
            ),
        ), sort_by_attrs='stage'),
        MelGroups('targets',
            MelStruct(b'QSTA', [u'I', u'B', u'3s'], (FID, 'targetId'),
                      (targetFlags, 'flags'), 'unused1'),
            MelConditionsTes4(),
        ),
    ).with_distributor({
        b'EDID|DATA': { # just in case one is missing
            b'CTDA': u'conditions',
        },
        b'INDX': {
            b'CTDA': u'stages',
        },
        b'QSTA': {
            b'CTDA': u'targets',
        },
    })

#------------------------------------------------------------------------------
class MreRace(MelRecord):
    """Race."""
    rec_sig = b'RACE'

    _flags = Flags.from_names(u'playable')

    melSet = MelSet(
        MelEdid(),
        MelFull(),
        MelDescription(),
        MelSpellsTes4(),
        MelRelations(with_gcr=False),
        MelRaceData(b'DATA', ['14b', '2s', '4f', 'I'], ('skills', [0] * 14),
                    'unused1', 'maleHeight', 'femaleHeight', 'maleWeight',
                    'femaleWeight', (_flags, u'flags')),
        MelRaceVoices(b'VNAM', ['2I'], (FID, 'maleVoice'), (FID, 'femaleVoice')),
        MelOptStruct(b'DNAM', [u'2I'], (FID, u'defaultHairMale'),
                     (FID, u'defaultHairFemale')),
        # Corresponds to GMST sHairColorNN
        MelUInt8(b'CNAM', 'defaultHairColor'),
        MelFloat(b'PNAM', 'mainClamp'),
        MelFloat(b'UNAM', 'faceClamp'),
        MelStruct(b'ATTR', [u'16B'], 'maleStrength', 'maleIntelligence',
                  'maleWillpower', 'maleAgility', 'maleSpeed', 'maleEndurance',
                  'malePersonality', 'maleLuck', 'femaleStrength',
                  'femaleIntelligence', 'femaleWillpower', 'femaleAgility',
                  'femaleSpeed', 'femaleEndurance', 'femalePersonality',
                  'femaleLuck'),
        # Indexed Entries
        MelBaseR(b'NAM0', 'face_data_marker'),
        MelRaceParts({
            0: u'head',
            1: u'maleEars',
            2: u'femaleEars',
            3: u'mouth',
            4: u'teethLower',
            5: u'teethUpper',
            6: u'tongue',
            7: u'leftEye',
            8: u'rightEye',
        }, group_loaders=lambda _indx: (
            # TODO(inf) Can't use MelModel here, since some patcher code
            #  directly accesses these - MelModel would put them in a group,
            #  which breaks that. Change this to a MelModel, then hunt down
            #  that code and change it
            MelString(b'MODL', u'modPath'),
            MelFloat(b'MODB', u'modb'),
            MelBase(b'MODT', 'modt_p'),
            MelIcon(),
        )),
        MelBaseR(b'NAM1', 'body_data_marker'),
        MelBaseR(b'MNAM', 'male_body_data_marker'),
        MelModel(b'MODL', 'maleTailModel'),
        MelRaceParts({
            0: u'maleUpperBodyPath',
            1: u'maleLowerBodyPath',
            2: u'maleHandPath',
            3: u'maleFootPath',
            4: u'maleTailPath',
        }, group_loaders=lambda _indx: (MelIcon(),)),
        MelBaseR(b'FNAM', 'female_body_data_marker'),
        MelModel(b'MODL', 'femaleTailModel'),
        MelRaceParts({
            0: u'femaleUpperBodyPath',
            1: u'femaleLowerBodyPath',
            2: u'femaleHandPath',
            3: u'femaleFootPath',
            4: u'femaleTailPath',
        }, group_loaders=lambda _indx: (MelIcon(),)),
        # Normal Entries
        # Note: xEdit marks both HNAM and ENAM as sorted. They are not, but
        # changing it would cause too many conflicts. We do *not* want to mark
        # them as sorted here, because that's what the Race Checker is for!
        MelSimpleArray('hairs', MelFid(b'HNAM')),
        MelSimpleArray('eyes', MelFid(b'ENAM')),
        MelBase(b'FGGS','fggs_p'), ####FaceGen Geometry-Symmetric
        MelBase(b'FGGA','fgga_p'), ####FaceGen Geometry-Asymmetric
        MelBase(b'FGTS','fgts_p'), ####FaceGen Texture-Symmetric
        MelStruct(b'SNAM', [u'2s'],'snam_p'),
    ).with_distributor({
        b'NAM0': {
            b'INDX|MODL|MODB|MODT|ICON': u'head',
        },
        b'MNAM': {
            b'MODL|MODB|MODT': u'maleTailModel',
            b'INDX|ICON': u'maleUpperBodyPath',
        },
        b'FNAM': {
            b'MODL|MODB|MODT': u'femaleTailModel',
            b'INDX|ICON': u'femaleUpperBodyPath',
        },
    })

#------------------------------------------------------------------------------
class MreRefr(MelRecord):
    """Placed Object."""
    rec_sig = b'REFR'

    _lockFlags = Flags.from_names((2, u'leveledLock'))

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
        MelFid(b'NAME', u'base'),
        MelOptStruct(b'XTEL', [u'I', u'6f'], (FID, u'destinationFid'),
            u'destinationPosX', u'destinationPosY', u'destinationPosZ',
            u'destinationRotX', u'destinationRotY', u'destinationRotZ'),
        MelRefrXloc(b'XLOC',
            [u'B', u'3s', u'I', u'4s', u'B', u'3s'], u'lockLevel', u'unused1',
            (FID, u'lockKey'), u'unused2', (_lockFlags, u'lockFlags'),
            u'unused3', is_optional=True, old_versions={u'B3sIB3s'}),
        MelOwnershipTes4(),
        MelEnableParent(),
        MelFid(b'XTRG', u'targetId'),
        MelBase(b'XSED', u'seed_p'),
        ####SpeedTree Seed, if it's a single byte then it's an offset into
        # the list of seed values in the TREE record
        ####if it's 4 byte it's the seed value directly.
        MelXlod(),
        MelFloat(b'XCHG', u'charge'),
        MelSInt32(b'XHLT', u'health'),
        MelNull(b'XPCI'), # These two are unused
        MelReadOnly(MelFull()), # Can't use MelNull, we need to distribute
        MelSInt32(b'XLCM', u'levelMod'),
        MelFid(b'XRTM', u'teleport_ref'),
        MelActionFlags(),
        MelSInt32(b'XCNT', u'count'),
        MelMapMarker(),
        MelBase(b'ONAM', u'open_by_default'),
        MelBase(b'XRGD', u'xrgd_p'), # Ragdoll Data, bytearray
        MelRefScale(),
        MelUInt8(b'XSOL', u'ref_soul'),
        MelRef3D(),
    ).with_distributor({
        b'FULL': u'full', # unused, but still need to distribute it
        b'XMRK': {
            b'FULL': u'map_marker',
        },
    })

#------------------------------------------------------------------------------
class MreRegn(MelRecord):
    """Region."""
    rec_sig = b'REGN'

    rdatFlags = Flags.from_names('Override')
    obflags = Flags.from_names(
        ( 0,'conform'),
        ( 1,'paintVertices'),
        ( 2,'sizeVariance'),
        ( 3,'deltaX'),
        ( 4,'deltaY'),
        ( 5,'deltaZ'),
        ( 6,'Tree'),
        ( 7,'hugeRock'),)
    sdflags = Flags.from_names(
        ( 0,'pleasant'),
        ( 1,'cloudy'),
        ( 2,'rainy'),
        ( 3,'snowy'),)

    melSet = MelSet(
        MelEdid(),
        MelIcon(),
        MelStruct(b'RCLR', [u'3B', u's'],'mapRed','mapBlue','mapGreen','unused1'),
        MelFid(b'WNAM','worldspace'),
        MelGroups('areas',
            MelUInt32(b'RPLI', 'edgeFalloff'),
            MelArray('points',
                MelStruct(b'RPLD', [u'2f'], 'posX', 'posY'),
            ),
        ),
        MelSorted(MelGroups('entries',
            MelStruct(b'RDAT', [u'I', u'2B', u'2s'], 'entryType', (rdatFlags, 'flags'),
                      'priority', 'unused1'),
            MelRegnEntrySubrecord(2, MelArray('objects',
                MelStruct(b'RDOT',
                    [u'I', u'H', u'2s', u'f', u'4B', u'2H', u'5f', u'3H',
                     u'2s', u'4s'], (FID, 'objectId'), 'parentIndex',
                    'unk1', 'density', 'clustering', 'minSlope',
                    'maxSlope', (obflags, 'flags'), 'radiusWRTParent',
                    'radius', 'minHeight', 'maxHeight', 'sink', 'sinkVar',
                    'sizeVar', 'angleVarX', 'angleVarY', 'angleVarZ',
                    'unk2', 'unk3'),
            )),
            ##: Was disabled previously - not in xEdit either...
            # MelRegnEntrySubrecord(5, MelIcon()),
            MelRegnEntrySubrecord(4, MelString(b'RDMP', 'mapName')),
            MelRegnEntrySubrecord(6, MelSorted(MelArray('grasses',
                MelStruct(b'RDGS', [u'I', u'4s'], (FID, 'grass'), 'unknown'),
            ), sort_by_attrs='grass')),
            MelRegnEntrySubrecord(7, MelUInt32(b'RDMD', 'musicType')),
            MelRegnEntrySubrecord(7, MelSorted(MelArray('sounds',
                MelStruct(b'RDSD', [u'3I'], (FID, 'sound'), (sdflags, 'flags'),
                          'chance'),
            ), sort_by_attrs='sound')),
            MelRegnEntrySubrecord(3, MelSorted(MelArray('weatherTypes',
                MelStruct(b'RDWT', [u'2I'], (FID, u'weather'), u'chance')
            ), sort_by_attrs='weather')),
        ), sort_by_attrs='entryType'),
    )

#------------------------------------------------------------------------------
class MreRoad(MelRecord):
    """Road. Part of large worldspaces."""
    ####Could probably be loaded via MelArray,
    ####but little point since it is too complex to manipulate
    rec_sig = b'ROAD'

    melSet = MelSet(
        MelBase(b'PGRP','points_p'),
        MelBase(b'PGRR','connections_p'),
    )

#------------------------------------------------------------------------------
class MreSbsp(MelRecord):
    """Subspace."""
    rec_sig = b'SBSP'

    melSet = MelSet(
        MelEdid(),
        MelStruct(b'DNAM', [u'3f'],'sizeX','sizeY','sizeZ'),
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
class MreSgst(MreHasEffects, MelRecord):
    """Sigil Stone."""
    rec_sig = b'SGST'

    melSet = MelSet(
        MelEdid(),
        MelObme(),
        MelFull(),
        MelModel(),
        MelIcon(),
        MelScript(),
        MelEffectsTes4(),
        MelEffectsTes4ObmeFull(),
        MelStruct(b'DATA', [u'B', u'I', u'f'],'uses','value','weight'),
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
        MelStruct(b'DATA', [u'2i', u'I', u'2f'],'action','attribute','specialization',('use0',1.0),'use1'),
        MelString(b'ANAM','apprentice'),
        MelString(b'JNAM','journeyman'),
        MelString(b'ENAM','expert'),
        MelString(b'MNAM','master'),
    )

#------------------------------------------------------------------------------
class MreSlgm(MelRecord):
    """Soul Gem."""
    rec_sig = b'SLGM'

    melSet = MelSet(
        MelEdid(),
        MelFull(),
        MelModel(),
        MelIcon(),
        MelScript(),
        MelValueWeight(),
        MelUInt8(b'SOUL', u'soul'),
        MelUInt8(b'SLCP', 'capacity'),
    )

#------------------------------------------------------------------------------
class MreSoun(MelRecord):
    """Sound."""
    rec_sig = b'SOUN'
    _has_duplicate_attrs = True # SNDD is an older version of SNDX

    _flags = Flags.from_names('randomFrequencyShift', 'playAtRandom',
        'environmentIgnored', 'randomLocation', 'loop','menuSound', '2d', '360LFE')

    melSet = MelSet(
        MelEdid(),
        MelString(b'FNAM','soundFile'),
        # This is the old format of SNDX - read it, but dump SNDX only
        MelReadOnly(
            MelStruct(b'SNDD', [u'2B', u'b', u's', u'H', u'2s'], u'minDistance', u'maxDistance',
                u'freqAdjustment', u'unused1', (_flags, u'flags'),
                u'unused2')
        ),
        MelStruct(b'SNDX', [u'2B', u'b', u's', u'H', u'2s', u'H', u'2B'], u'minDistance', u'maxDistance',
            u'freqAdjustment', u'unused1', (_flags, u'flags'),
            u'unused2', u'staticAtten', u'stopTime', u'startTime'),
    )

#------------------------------------------------------------------------------
class MreSpel(MreHasEffects, MelRecord):
    """Spell."""
    rec_sig = b'SPEL'
    ##: use LowerDict and get rid of the lower() in callers
    _spell_type_num_name = {None: u'NONE',
                            0   : u'Spell',
                            1   : u'Disease',
                            2   : u'Power',
                            3   : u'LesserPower',
                            4   : u'Ability',
                            5   : u'Poison'}
    _spell_type_name_num = {y.lower(): x for x, y in
                            _spell_type_num_name.items() if x is not None}
    _level_type_num_name = {None : u'NONE',
                            0    : u'Novice',
                            1    : u'Apprentice',
                            2    : u'Journeyman',
                            3    : u'Expert',
                            4    : u'Master'}
    _level_type_name_num = {y.lower(): x for x, y in
                            _level_type_num_name.items() if x is not None}
    attr_csv_struct[u'level'][2] = \
        lambda val: f'"{MreSpel._level_type_num_name.get(val, val)}"'
    attr_csv_struct[u'spellType'][2] = \
        lambda val: f'"{MreSpel._spell_type_num_name.get(val, val)}"'

    melSet = MelSet(
        MelEdid(),
        MelObme(),
        MelFull(),
        MelStruct(b'SPIT', [u'3I', u'B', u'3s'], 'spellType', 'cost', 'level',
                  (SpellFlags, 'spell_flags'), 'unused1'),
        MelEffectsTes4(),
        MelEffectsTes4ObmeFull(),
    ).with_distributor(_effects_distributor)

    @classmethod
    def parse_csv_line(cls, csv_fields, index_dict, reuse=False):
        attr_dict = super(MreSpel, cls).parse_csv_line(csv_fields, index_dict,
                                                       reuse)
        try:
            lvl = attr_dict[u'level'] # KeyError on 'detailed' pass
            attr_dict[u'level'] = cls._level_type_name_num.get(lvl.lower(),
                int_or_zero(lvl))
            stype = attr_dict[u'spellType']
            attr_dict[u'spellType'] = cls._spell_type_name_num.get(
                stype.lower(), int_or_zero(stype))
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
        MelSorted(MelArray('speedTree',
            MelUInt32(b'SNAM', 'seed'),
        ), sort_by_attrs='seed'),
        MelStruct(b'CNAM', [u'5f', u'i', u'2f'], 'curvature','minAngle','maxAngle',
                  'branchDim','leafDim','shadowRadius','rockSpeed',
                  'rustleSpeed'),
        MelStruct(b'BNAM', [u'2f'],'widthBill','heightBill'),
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

    _flags = Flags.from_names('causesDmg', 'reflective')

    melSet = MelSet(
        MelEdid(),
        MelString(b'TNAM','texture'),
        MelUInt8(b'ANAM', 'opacity'),
        MelUInt8Flags(b'FNAM', u'flags', _flags),
        MelString(b'MNAM','material'),
        MelSound(),
        MelWatrData(b'DATA',
            [u'11f', u'3B', u's', u'3B', u's', u'3B', u's', u'B', u'3s',
             u'10f', u'H'], ('windVelocity', 0.100),
            ('windDirection', 90.0), ('waveAmp', 0.5), ('waveFreq', 1.0),
            ('sunPower', 50.0), ('reflectAmt', 0.5), ('fresnelAmt', 0.0250),
            'xSpeed', 'ySpeed', ('fogNear', 27852.8),
            ('fogFar', 163840.0), 'shallowRed', ('shallowGreen', 128),
            ('shallowBlue', 128), 'unused1', 'deepRed',
            'deepGreen', ('deepBlue', 25), 'unused2',
            ('reflRed', 255), ('reflGreen', 255), ('reflBlue', 255),
            'unused3', ('blend', 50), 'unused4',
            ('rainForce', 0.1000), ('rainVelocity', 0.6000),
            ('rainFalloff', 0.9850), ('rainDampner', 2.0000),
            ('rainSize', 0.0100), ('dispForce', 0.4000),
            ('dispVelocity', 0.6000), ('dispFalloff', 0.9850),
            ('dispDampner', 10.0000), ('dispSize', 0.0500), 'damage',
            old_versions={'11f3Bs3Bs3BsB3s6f2s', '11f3Bs3Bs3BsB3s2s',
                          '10f2s', '2s'}),
        MelSimpleArray('relatedWaters', MelFid(b'GNAM')),
    )

#------------------------------------------------------------------------------
class MreWeap(MelRecord):
    """Weapon."""
    rec_sig = b'WEAP'

    _flags = Flags.from_names('notNormalWeapon')

    melSet = MelSet(
        MelEdid(),
        MelFull(),
        MelModel(),
        MelIcon(),
        MelScript(),
        MelEnchantment(b'ENAM'),
        MelUInt16(b'ANAM', 'enchantPoints'),
        MelStruct(b'DATA', [u'I', u'2f', u'3I', u'f', u'H'],'weaponType','speed','reach',(_flags, u'flags'),
            'value','health','weight','damage'),
    )

#------------------------------------------------------------------------------
class MreWrld(AMreWrld):
    """Worldspace."""
    ref_types = MreCell.ref_types
    exterior_temp_extra = [b'LAND', b'PGRD']
    wrld_children_extra = [b'ROAD', b'CELL'] # CELL for the persistent block

    _flags = Flags.from_names('smallWorld', 'noFastTravel',
                              'oblivionWorldspace', None, 'noLODWater')

    melSet = MelSet(
        MelEdid(),
        MelFull(),
        MelFid(b'WNAM','parent'),
        MelFid(b'CNAM','climate'),
        MelFid(b'NAM2','water'),
        MelIcon(u'mapPath'),
        MelStruct(b'MNAM', [u'2i', u'4h'], u'dimX', u'dimY', u'NWCellX', u'NWCellY',
                  u'SECellX', u'SECellY'),
        MelUInt8Flags(b'DATA', u'flags', _flags),
        MelWorldBounds(),
        MelUInt32(b'SNAM', 'music_type'),
        MelNull(b'OFST'), # Not even CK/xEdit can recalculate these right now
    )

#------------------------------------------------------------------------------
class MreWthr(MelRecord):
    """Weather."""
    rec_sig = b'WTHR'

    melSet = MelSet(
        MelEdid(),
        MelString(b'CNAM','lowerLayer'),
        MelString(b'DNAM','upperLayer'),
        MelModel(),
        MelArray('colors',
            MelWthrColors(b'NAM0'),
        ),
        MelStruct(b'FNAM', [u'4f'],'fogDayNear','fogDayFar','fogNightNear','fogNightFar'),
        MelStruct(b'HNAM', [u'14f'],
            'eyeAdaptSpeed', 'blurRadius', 'blurPasses', 'emissiveMult',
            'targetLum', 'upperLumClamp', 'brightScale', 'brightClamp',
            'lumRampNoTex', 'lumRampMin', 'lumRampMax', 'sunlightDimmer',
            'grassDimmer', 'treeDimmer'),
        MelStruct(b'DATA', [u'15B'],
            'windSpeed','lowerCloudSpeed','upperCloudSpeed','transDelta',
            'sunGlare','sunDamage','rainFadeIn','rainFadeOut','boltFadeIn',
            'boltFadeOut','boltFrequency','weatherType','boltRed','boltBlue','boltGreen'),
        MelGroups('sounds',
            MelStruct(b'SNAM', [u'2I'], (FID, 'sound'), 'type'),
        ),
    )
