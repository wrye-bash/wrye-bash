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
"""This module contains the oblivion record classes."""
import io
import re
from collections import OrderedDict
from itertools import chain

from ... import brec
from ...bolt import Flags
from ...brec import MelRecord, MelGroups, MelStruct, FID, MelGroup, \
    MelString, MreLeveledListBase, MelSet, MelFid, MelNull, MelOptStruct, \
    MelFids, MreHeaderBase, MelBase, MelFidList, MelStrings, \
    MreGmstBase, MelReferences, MelRegnEntrySubrecord, \
    MelFloat, MelSInt16, MelSInt32, MelUInt8, MelUInt16, MelUInt32, \
    MelOptFloat, MelOptSInt32, MelOptUInt8, MelOptUInt16, MelOptUInt32, \
    MelRaceParts, MelRaceVoices, null1, null2, null3, null4, MelScriptVars, \
    MelSequential, MelUnion, FlagDecider, AttrValDecider, PartialLoadDecider, \
    MelTruncatedStruct, MelSkipInterior, MelIcon, MelIco2, MelEdid, MelFull, \
    MelArray, MelWthrColors, MelObject, MreActorBase, MreWithItems, \
    MelReadOnly, MelCtda, MelRef3D, MelXlod, MelWorldBounds, MelEnableParent, \
    MelRefScale, MelMapMarker, MelActionFlags, MelPartialCounter, MelScript, \
    MelDescription, BipedFlags, MelSpells, MelUInt8Flags, MelUInt32Flags
# Set brec MelModel to the one for Oblivion
if brec.MelModel is None:

    class _MelModel(MelGroup):
        """Represents a model record."""
        typeSets = ((b'MODL', b'MODB', b'MODT'),
                    (b'MOD2', b'MO2B', b'MO2T'),
                    (b'MOD3', b'MO3B', b'MO3T'),
                    (b'MOD4', b'MO4B', b'MO4T'))

        def __init__(self, attr=u'model', index=0):
            """Initialize. Index is 0,2,3,4 for corresponding type id."""
            types = self.__class__.typeSets[index - 1 if index > 1 else 0]
            super(_MelModel, self).__init__(attr,
                MelString(types[0], u'modPath'),
                # None here is on purpose - 0 is a legitimate value
                MelOptFloat(types[1], u'modb', None),
                # Texture File Hashes
                MelBase(types[2], u'modt_p')
            )

    brec.MelModel = _MelModel
from ...brec import MelModel, MelLists

#------------------------------------------------------------------------------
# Record Elements -------------------------------------------------------------
#------------------------------------------------------------------------------
class MelConditions(MelGroups):
    """A list of conditions. Can contain the old CTDT format as well, which
    will be upgraded on dump."""
    def __init__(self):
        super(MelConditions, self).__init__(u'conditions', MelUnion({
            b'CTDA': MelCtda(suffix_fmt=u'4s',
                suffix_elements=[(u'unused3', null4)]),
            # The old (CTDT) format is length 20 and has no suffix
            b'CTDT': MelReadOnly(MelCtda(b'CTDT', suffix_fmt=u'4s',
                suffix_elements=[(u'unused3', null4)], old_suffix_fmts={u''})),
            }),
        )

#------------------------------------------------------------------------------
# A distributor config for use with MelEffects, since MelEffects also contains
# a FULL subrecord
_effects_distributor = {
    b'FULL': u'full', # don't rely on EDID being present
    b'EFID': {
        b'FULL': u'effects',
    },
    b'EFXX': {
        b'FULL': u'obme_full',
    },
}

class MelObmeScitGroup(MelGroup):
    """Fun HACK for the whole family. We need to carry efix_param_info into
    this group, since '../' syntax is not yet supported (see MrePerk in Skyrim
    for another part of the code that's suffering from this). And we can't
    simply not put this in a group, because a bunch of code relies on a group
    called 'scriptEffect' existing..."""
    def load_mel(self, record, ins, sub_type, size_, *debug_strs):
        target = getattr(record, self.attr)
        if target is None:
            class _MelHackyObject(MelObject):
                @property
                def efix_param_info(self):
                    return record.efix_param_info
                @efix_param_info.setter
                def efix_param_info(self, new_efix_info):
                    record.efix_param_info = new_efix_info
            target = _MelHackyObject()
            for element in self.elements:
                element.setDefault(target)
            target.__slots__ = [s for element in self.elements for s in
                                element.getSlotsUsed()]
            setattr(record, self.attr, target)
        self.loaders[sub_type].load_mel(target, ins, sub_type, size_, *debug_strs)

# TODO(inf) Do we really need to do this? It's an unused test spell
class MelEffectsScit(MelTruncatedStruct):
    """The script fid for MS40TestSpell doesn't point to a valid script,
    so this class drops it."""
    def _pre_process_unpacked(self, unpacked_val):
        if len(unpacked_val) == 1:
            if unpacked_val[0] & 0xFF000000:
                unpacked_val = (0,) # Discard bogus MS40TestSpell fid
        return super(MelEffectsScit, self)._pre_process_unpacked(unpacked_val)

##: Should we allow mixing regular effects and OBME ones? This implementation
# assumes no, but xEdit's is broken right now, so...
class MelEffects(MelSequential):
    """Represents ingredient/potion/enchantment/spell effects. Supports OBME,
    which is why it's so complex. The challenge is that we basically have to
    redirect every procedure to one of two lists of elements, depending on
    whether an 'OBME' subrecord exists or not."""
    _se_flags = Flags(0, Flags.getNames(u'hostile'))

    def __init__(self):
        # Vanilla Elements ----------------------------------------------------
        self._vanilla_elements = [
            MelGroups(u'effects',
                # REHE is Restore target's Health - EFID.effect_sig
                # must be the same as EFIT.effect_sig
                MelStruct(b'EFID', u'4s', (u'effect_sig', b'REHE')),
                MelStruct(b'EFIT', u'4s4Ii', (u'effect_sig', b'REHE'),
                          u'magnitude', u'area', u'duration', u'recipient',
                          u'actorValue'),
                MelGroup(u'scriptEffect',
                    MelEffectsScit(b'SCIT', u'2I4sB3s', (FID, u'script'),
                        u'school', (u'visual', null4),
                        (MelEffects._se_flags, u'flags'),
                        (u'unused1', null3), old_versions={u'2I4s', u'I'}),
                    MelFull(),
                ),
            ),
        ]
        # OBME Elements -------------------------------------------------------
        self._obme_elements = [
            MelGroups(u'effects',
                MelObme(b'EFME', extra_format=u'2B',
                        extra_contents=[u'efit_param_info',
                                        u'efix_param_info'],
                        reserved_byte_count=10),
                MelStruct(b'EFID', u'4s', (u'effect_sig', b'REHE')),
                MelUnion({
                    0: MelStruct(b'EFIT', u'4s4I4s', (u'unused_name', null4),
                                 u'magnitude', u'area', u'duration',
                                 u'recipient', (u'efit_param', null4)),
                    ##: Test this! Does this actually work?
                    (1, 3): MelStruct(b'EFIT', u'4s5I',
                        (u'unused_name', null4), u'magnitude', u'area',
                        u'duration', u'recipient', (FID, u'efit_param')),
                    ##: This case needs looking at, OBME docs say this about
                    # efit_param in case 2: 'If >= 0x80000000 lowest byte is
                    # Mod Index, otherwise no resolution'
                    2: MelStruct(b'EFIT', u'4s4I4s', (u'unused_name', null4),
                                 u'magnitude', u'area', u'duration',
                                 u'recipient', (u'efit_param', b'REHE')),
                }, decider=AttrValDecider(u'efit_param_info')),
                MelObmeScitGroup(u'scriptEffect',
                    ##: Test! xEdit has all this in EFIX, but it also
                    #  hard-crashes when I try to add EFIX subrecords... this
                    #  is adapted from OBME's official docs, but those could be
                    #  wrong. Also, same notes as above for case 2 and 3.
                    MelUnion({
                        0: MelStruct(b'SCIT', u'4sI4sB3s',
                                     (u'efix_param', null4), u'school',
                                     (u'visual', null4),
                                     (MelEffects._se_flags, u'flags'),
                                     (u'unused1', null3)),
                        1: MelStruct(b'SCIT', u'2I4sB3s', (FID, u'efix_param'),
                                     u'school', (u'visual', null4),
                                     (MelEffects._se_flags, u'flags'),
                                     (u'unused1', null3)),
                        2: MelStruct(b'SCIT', u'4sI4sB3s',
                                     (u'efix_param', b'REHE'), u'school',
                                     (u'visual', null4),
                                     (MelEffects._se_flags, u'flags'),
                                     (u'unused1', null3)),
                        3: MelStruct(b'SCIT', u'2I4sB3s', (FID, u'efit_param'),
                                     u'school', (u'visual', null4),
                                     (MelEffects._se_flags, u'flags'),
                                     (u'unused1', null3)),
                    }, decider=AttrValDecider(u'efix_param_info')),
                    MelFull(),
                ),
                MelString(b'EFII', u'obme_icon'),
                ##: Again, FID here needs testing
                MelOptStruct(b'EFIX', u'2Ifi16s', u'efix_override_mask',
                    u'efix_flags', u'efix_base_cost', (FID, u'resist_av'),
                    (u'efix_reserved', null1 * 16)),
            ),
            MelBase(b'EFXX', u'effects_end_marker', b''),
        ]
        # Split everything by Vanilla/OBME
        self._vanilla_loaders = {}
        self._vanilla_form_elements = set()
        self._obme_loaders = {}
        self._obme_form_elements = set()
        # Only for setting the possible signatures, redirected in load_mel etc.
        super(MelEffects, self).__init__(*(self._vanilla_elements +
                                           self._obme_elements))

    # Note that we only support creating vanilla effects, as our records system
    # isn't expressive enough to pass more info along here
    def getDefaulters(self, defaulters, base):
        for element in self._vanilla_elements:
            element.getDefaulters(defaulters, base)

    def getLoaders(self, loaders):
        # We need to collect all signatures and assign ourselves for them all
        # to always gain control of load_mel so we can redirect it properly
        for element in self._vanilla_elements:
            element.getLoaders(self._vanilla_loaders)
        for element in self._obme_elements:
            element.getLoaders(self._obme_loaders)
        for signature in chain(self._vanilla_loaders, self._obme_loaders):
            loaders[signature] = self

    def hasFids(self, formElements):
        for element in self._vanilla_elements:
            element.hasFids(self._vanilla_form_elements)
        for element in self._obme_elements:
            element.hasFids(self._obme_form_elements)
        if self._vanilla_form_elements or self._obme_form_elements:
            formElements.add(self)

    def load_mel(self, record, ins, sub_type, size_, *debug_strs):
        target_loaders = (self._obme_loaders
                          if record.obme_record_version is not None
                          else self._vanilla_loaders)
        target_loaders[sub_type].load_mel(record, ins, sub_type, size_, *debug_strs)

    def dumpData(self, record, out):
        target_elements = (self._obme_elements
                           if record.obme_record_version is not None
                           else self._vanilla_elements)
        for element in target_elements:
            element.dumpData(record, out)

    def mapFids(self, record, function, save=False):
        target_form_elements = (self._obme_form_elements
                                if record.obme_record_version is not None
                                else self._vanilla_form_elements)
        for form_element in target_form_elements:
            form_element.mapFids(record, function, save)

class MelEffectsObmeFull(MelString):
    """Hacky class for handling the extra FULL that OBME includes after the
    effects for some reason. We can't just pack this one into MelEffects above
    since otherwise we'd have duplicate signatures in the same load, and
    MelDistributor would just distribute the load to the same MelGroups
    backend, which would blindly use the last FULL. Did I ever mention that
    OBME is an awfully hacky mess?"""
    def __init__(self):
        super(MelEffectsObmeFull, self).__init__(b'FULL', u'obme_full')

#------------------------------------------------------------------------------
class MelEmbeddedScript(MelSequential):
    """Handles an embedded script, a SCHR/SCDA/SCTX/SLSD/SCVR/SCRO/SCRV
    subrecord combo. SLSD and SCVR can optionally be disabled."""
    def __init__(self, with_script_vars=False):
        seq_elements = [
            MelUnion({
                b'SCHR': MelStruct(b'SCHR', u'4s4I', (u'unused1', null4),
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
class MelItems(MelGroups):
    """Wraps MelGroups for the common task of defining a list of items."""
    def __init__(self):
        super(MelItems, self).__init__(u'items',
            MelStruct(b'CNTO', u'Ii', (FID, u'item'), u'count'),
        ),

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
        return super(MelLevListLvlo, self)._pre_process_unpacked(unpacked_val)

class MreLeveledList(MreLeveledListBase):
    """Leveled item/creature/spell list."""
    top_copy_attrs = ('script','template','chanceNone',)

    melSet = MelSet(
        MelEdid(),
        MelLevListLvld(),
        MelUInt8Flags(b'LVLF', u'flags', MreLeveledListBase._flags),
        MelScript(), # LVLC only
        MelFid(b'TNAM','template'),
        MelGroups('entries',
            MelLevListLvlo(b'LVLO', u'h2sIh2s', u'level', (u'unused1', null2),
                           (FID, u'listId'), (u'count', 1),
                           (u'unused2', null2), old_versions={u'iI'}),
        ),
        MelNull(b'DATA'),
    )
    __slots__ = melSet.getSlotsUsed()

#------------------------------------------------------------------------------
class MelObme(MelOptStruct):
    """Oblivion Magic Extender subrecord. Prefixed every attribute with obme_
    both for easy grouping in debugger views and to differentiate them from
    vanilla attrs."""
    def __init__(self, struct_sig=b'OBME', extra_format=u'',
            extra_contents=None, reserved_byte_count=28):
        """Initializes a MelObme instance. Supports customization for the
        variations that exist for effects subrecords and MGEF records."""
        # Always begins with record version and OBME version - None here is on
        # purpose, to differentiate from 0 which is almost always the record
        # version in plugins using OBME
        if extra_contents is None:
            extra_contents = []
        struct_contents = [(u'obme_record_version', None),
                           u'obme_version_beta', u'obme_version_minor',
                           u'obme_version_major']
        # Then comes any extra info placed in the middle
        struct_contents += extra_contents
        # Always ends with a statically sized reserved byte array
        struct_contents += [(u'obme_unused', null1 * reserved_byte_count)]
        super(MelObme, self).__init__(
            struct_sig, u'4B{}{}s'.format(extra_format, reserved_byte_count),
            *struct_contents)

#------------------------------------------------------------------------------
class MelOwnershipTes4(brec.MelOwnership):
    """Handles XOWN, XRNK, and XGLB for cells and cell children."""
    def __init__(self, attr=u'ownership'):
        super(brec.MelOwnership, self).__init__(attr,
            MelFid(b'XOWN', u'owner'),
            # None here is on purpose - rank == 0 is a valid value, but XRNK
            # does not have to be present
            MelOptSInt32(b'XRNK', u'rank', None),
            MelFid(b'XGLB', u'global'),
        )

##: Could technically be reworked for non-Oblivion games, but is broken and
# unused outside of Oblivion right now
class MreHasEffects(object):
    """Mixin class for magic items."""
    __slots__ = []

    def getEffects(self):
        """Returns a summary of effects. Useful for alchemical catalog."""
        from ... import bush
        effects = []
        effectsAppend = effects.append
        for effect in self.effects:
            mgef, actorValue = effect.effect_sig, effect.actorValue
            if mgef not in bush.game.generic_av_effects:
                actorValue = 0
            effectsAppend((mgef,actorValue))
        return effects

    def getSpellSchool(self):
        """Returns the school based on the highest cost spell effect."""
        from ... import bush
        spellSchool = [0,0]
        for effect in self.effects:
            school = bush.game.mgef_school[effect.effect_sig]
            effectValue = bush.game.mgef_basevalue[effect.effect_sig]
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
        from ... import bush
        buff = io.StringIO()
        avEffects = bush.game.generic_av_effects
        aValues = bush.game.actor_values
        buffWrite = buff.write
        if self.effects:
            school = self.getSpellSchool()
            buffWrite(aValues[20 + school] + u'\n')
        for index, effect in enumerate(self.effects):
            if effect.scriptEffect:
                effectName = effect.scriptEffect.full or u'Script Effect'
            else:
                effectName = bush.game.mgef_name[effect.effect_sig]
                if effect.effect_sig in avEffects:
                    effectName = re.sub(_(u'(Attribute|Skill)'),
                                        aValues[effect.actorValue], effectName)
            buffWrite(u'o+*'[effect.recipient] + u' ' + effectName)
            if effect.magnitude: buffWrite(u' %sm' % effect.magnitude)
            if effect.area: buffWrite(u' %sa' % effect.area)
            if effect.duration > 1: buffWrite(u' %sd' % effect.duration)
            buffWrite(u'\n')
        return buff.getvalue()

#------------------------------------------------------------------------------
# Oblivion Records ------------------------------------------------------------
#------------------------------------------------------------------------------
class MreTes4(MreHeaderBase):
    """TES4 Record.  File header."""
    rec_sig = b'TES4'

    melSet = MelSet(
        MelStruct(b'HEDR', u'f2I', (u'version', 1.0), u'numRecords',
            (u'nextObject', 0x800)),
        MelNull(b'OFST'), # Not even CK/xEdit can recalculate these right now
        MelBase(b'DELE','dele_p',),  #--Obsolete?
        MreHeaderBase.MelAuthor(),
        MreHeaderBase.MelDescription(),
        MreHeaderBase.MelMasterNames(),
        MelNull(b'DATA'),
    )
    __slots__ = melSet.getSlotsUsed()

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
    __slots__ = melSet.getSlotsUsed()

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
    __slots__ = melSet.getSlotsUsed()

class MreActi(MelRecord):
    """Activator."""
    rec_sig = b'ACTI'

    melSet = MelSet(
        MelEdid(),
        MelFull(),
        MelModel(),
        MelScript(),
        MelFid(b'SNAM','sound'),
    )
    __slots__ = melSet.getSlotsUsed()

class MreAlch(MelRecord,MreHasEffects):
    """Potion."""
    rec_sig = b'ALCH'

    _flags = Flags(0, Flags.getNames('autoCalc','isFood'))

    melSet = MelSet(
        MelEdid(),
        MelObme(),
        MelFull(),
        MelModel(),
        MelIcon(),
        MelScript(),
        MelFloat(b'DATA', 'weight'),
        MelStruct(b'ENIT','iB3s','value',(_flags,'flags',0),('unused1',null3)),
        MelEffects(),
        MelEffectsObmeFull(),
    ).with_distributor(_effects_distributor)
    __slots__ = melSet.getSlotsUsed()

class MreAmmo(MelRecord):
    """Ammunition."""
    rec_sig = b'AMMO'

    _flags = Flags(0, Flags.getNames('notNormalWeapon'))

    melSet = MelSet(
        MelEdid(),
        MelFull(),
        MelModel(),
        MelIcon(),
        MelFid(b'ENAM','enchantment'),
        MelOptUInt16(b'ANAM', 'enchantPoints'),
        MelStruct(b'DATA', 'fB3sIfH', 'speed', (_flags, 'flags', 0),
                  ('unused1', null3), 'value', 'weight', 'damage'),
    )
    __slots__ = melSet.getSlotsUsed()

class MreAnio(MelRecord):
    """Animation Object."""
    rec_sig = b'ANIO'

    melSet = MelSet(
        MelEdid(),
        MelModel(),
        MelFid(b'DATA','animationId'),
    )
    __slots__ = melSet.getSlotsUsed()

class MreAppa(MelRecord):
    """Alchemical Apparatus."""
    rec_sig = b'APPA'

    melSet = MelSet(
        MelEdid(),
        MelFull(),
        MelModel(),
        MelIcon(),
        MelScript(),
        MelStruct(b'DATA', '=BIff', ('apparatus', 0), ('value', 25),
                  ('weight', 1), ('quality', 10)),
    )
    __slots__ = melSet.getSlotsUsed()

class MreArmo(MelRecord):
    """Armor."""
    rec_sig = b'ARMO'

    _flags = BipedFlags(0, Flags.getNames((16, u'hideRings'),
                                          (17, u'hideAmulet'),
                                          (22, u'notPlayable'),
                                          (23, u'heavyArmor')))

    melSet = MelSet(
        MelEdid(),
        MelFull(),
        MelScript(),
        MelFid(b'ENAM','enchantment'),
        MelOptUInt16(b'ANAM', 'enchantPoints'),
        MelUInt32Flags(b'BMDT', u'biped_flags', _flags),
        MelModel(u'maleBody', 0),
        MelModel(u'maleWorld', 2),
        MelIcon(u'maleIconPath'),
        MelModel(u'femaleBody', 3),
        MelModel(u'femaleWorld', 4),
        MelIco2(u'femaleIconPath'),
        MelStruct(b'DATA','=HIIf','strength','value','health','weight'),
    )
    __slots__ = melSet.getSlotsUsed()

class MreBook(MelRecord):
    """Book."""
    rec_sig = b'BOOK'

    _flags = Flags(0,Flags.getNames('isScroll','isFixed'))

    melSet = MelSet(
        MelEdid(),
        MelFull(),
        MelModel(),
        MelIcon(),
        MelDescription(u'book_text'),
        MelScript(),
        MelFid(b'ENAM','enchantment'),
        MelOptUInt16(b'ANAM', 'enchantPoints'),
        MelStruct(b'DATA', '=BbIf', (_flags, 'flags', 0), ('teaches', -1),
                  'value', 'weight'),
    )
    __slots__ = melSet.getSlotsUsed() + ['modb']

class MreBsgn(MelRecord):
    """Birthsign."""
    rec_sig = b'BSGN'

    melSet = MelSet(
        MelEdid(),
        MelFull(),
        MelIcon(),
        MelDescription(u'text'),
        MelSpells(),
    )
    __slots__ = melSet.getSlotsUsed()

class MreCell(MelRecord):
    """Cell."""
    rec_sig = b'CELL'

    cellFlags = Flags(0, Flags.getNames(
        (0, u'isInterior'),
        (1, u'hasWater'),
        (2, u'invertFastTravel'),
        (3, u'forceHideLand'),
        (5, u'publicPlace'),
        (6, u'handChanged'),
        (7, u'behaveLikeExterior')
    ))

    melSet = MelSet(
        MelEdid(),
        MelFull(),
        MelUInt8Flags(b'DATA', u'flags', cellFlags),
        # None defaults here are on purpose - XCLC does not necessarily exist,
        # but 0 is a valid value for both coordinates (duh)
        MelSkipInterior(MelOptStruct(b'XCLC', u'2i', (u'posX', None),
            (u'posY', None))),
        MelOptStruct(b'XCLL', u'=3Bs3Bs3Bs2f2i2f', u'ambientRed',
            u'ambientGreen', u'ambientBlue', (u'unused1', null1),
            u'directionalRed', u'directionalGreen', u'directionalBlue',
            (u'unused2', null1), u'fogRed', u'fogGreen', u'fogBlue',
            (u'unused3', null1), u'fogNear', u'fogFar', u'directionalXY',
            u'directionalZ', (u'directionalFade', 1.0), u'fogClip'),
        MelFidList(b'XCLR', u'regions'),
        MelOptUInt8(b'XCMT', u'music'),
        # CS default for water is -2147483648, but by setting default here
        # to -2147483649, we force the bashed patch to retain the value of
        # the last mod.
        MelOptFloat(b'XCLW', u'waterHeight', -2147483649),
        MelFid(b'XCCM', u'climate'),
        MelFid(b'XCWT', u'water'),
        MelOwnershipTes4(),
    )
    __slots__ = melSet.getSlotsUsed()

class MreClas(MelRecord):
    """Class."""
    rec_sig = b'CLAS'

    _flags = Flags(0, Flags.getNames(
        u'class_playable',
        u'class_guard',
    ))
    aiService = Flags(0, Flags.getNames(
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
        (17,'repair'),))

    melSet = MelSet(
        MelEdid(),
        MelFull(),
        MelDescription(),
        MelIcon(),
        MelTruncatedStruct(b'DATA', '2iI7i2IbB2s', 'primary1', 'primary2',
                           'specialization', 'major1', 'major2', 'major3',
                           'major4', 'major5', 'major6', 'major7',
                           (_flags, 'flags', 0), (aiService, 'services', 0),
                           ('trainSkill', 0), ('trainLevel', 0),
                           ('unused1', null2), old_versions={'2iI7i2I'}),
    )
    __slots__ = melSet.getSlotsUsed()

class MreClmt(MelRecord):
    """Climate."""
    rec_sig = b'CLMT'

    melSet = MelSet(
        MelEdid(),
        MelArray('weather_types',
            MelStruct(b'WLST','Ii', (FID, 'weather'), 'chance'),
        ),
        MelString(b'FNAM','sunPath'),
        MelString(b'GNAM','glarePath'),
        MelModel(),
        MelStruct(b'TNAM', '6B', 'riseBegin', 'riseEnd', 'setBegin', 'setEnd',
                  'volatility', 'phaseLength'),
    )
    __slots__ = melSet.getSlotsUsed()

class MreClot(MelRecord):
    """Clothing."""
    rec_sig = b'CLOT'

    _flags = BipedFlags(0, Flags.getNames((16, u'hideRings'),
                                          (17, u'hideAmulet'),
                                          (22, u'notPlayable')))

    melSet = MelSet(
        MelEdid(),
        MelFull(),
        MelScript(),
        MelFid(b'ENAM','enchantment'),
        MelOptUInt16(b'ANAM', 'enchantPoints'),
        MelUInt32Flags(b'BMDT', u'biped_flags', _flags),
        MelModel(u'maleBody', 0),
        MelModel(u'maleWorld', 2),
        MelIcon(u'maleIconPath'),
        MelModel(u'femaleBody', 3),
        MelModel(u'femaleWorld', 4),
        MelIco2(u'femaleIconPath'),
        MelStruct(b'DATA','If','value','weight'),
    )
    __slots__ = melSet.getSlotsUsed()

class MreCont(MreWithItems):
    """Container."""
    rec_sig = b'CONT'

    _flags = Flags(0,Flags.getNames(None,'respawns'))

    melSet = MelSet(
        MelEdid(),
        MelFull(),
        MelModel(),
        MelScript(),
        MelItems(),
        MelStruct(b'DATA','=Bf',(_flags,'flags',0),'weight'),
        MelFid(b'SNAM','soundOpen'),
        MelFid(b'QNAM','soundClose'),
    )
    __slots__ = melSet.getSlotsUsed()

class MreCrea(MreActorBase):
    """Creature."""
    rec_sig = b'CREA'

    _flags = Flags(0, Flags.getNames(
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
        ))
    aiService = Flags(0, Flags.getNames(
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
        (17,'repair'),))

    melSet = MelSet(
        MelEdid(),
        MelFull(),
        MelModel(),
        MelSpells(),
        MelStrings(b'NIFZ','bodyParts'),
        MelBase(b'NIFT','nift_p'), # Texture File Hashes
        MelStruct(b'ACBS','=I3Hh2H',
            (_flags,'flags',0),'baseSpell','fatigue','barterGold',
            ('level',1),'calcMin','calcMax'),
        MelGroups(u'factions',
            MelStruct(b'SNAM', u'IB3s', (FID, u'faction'), u'rank',
                      (u'unused1', b'IFZ')),
        ),
        MelFid(b'INAM','deathItem'),
        MelScript(),
        MelItems(),
        MelStruct(b'AIDT','=4BIbB2s',
            ('aggression',5),('confidence',50),('energyLevel',50),
            ('responsibility',50),(aiService,'services',0),'trainSkill',
            'trainLevel',('unused1',null2)),
        MelFids(b'PKID','aiPackages'),
        MelStrings(b'KFFZ','animations'),
        MelStruct(b'DATA','=5BsH2sH8B','creatureType','combatSkill','magic',
                  'stealth','soul',('unused2',null1),'health',
                  ('unused3',null2),'attackDamage','strength','intelligence',
                  'willpower','agility','speed','endurance','personality',
                  'luck'),
        MelUInt8(b'RNAM', 'attackReach'),
        MelFid(b'ZNAM','combatStyle'),
        MelFloat(b'TNAM', 'turningSpeed'),
        MelFloat(b'BNAM', 'baseScale'),
        MelFloat(b'WNAM', 'footWeight'),
        MelFid(b'CSCR','inheritsSoundsFrom'),
        MelString(b'NAM0','bloodSprayPath'),
        MelString(b'NAM1','bloodDecalPath'),
        MelGroups('sounds',
            MelUInt32(b'CSDT', 'type'),
            MelFid(b'CSDI','sound'),
            MelUInt8(b'CSDC', 'chance'),
        ),
    )
    __slots__ = melSet.getSlotsUsed()

class MreCsty(MelRecord):
    """Combat Style."""
    rec_sig = b'CSTY'
    _flagsA = Flags(0, Flags.getNames(
        ( 0,'advanced'),
        ( 1,'useChanceForAttack'),
        ( 2,'ignoreAllies'),
        ( 3,'willYield'),
        ( 4,'rejectsYields'),
        ( 5,'fleeingDisabled'),
        ( 6,'prefersRanged'),
        ( 7,'meleeAlertOK'),
        ))
    _flagsB = Flags(0, Flags.getNames(
        ( 0,'doNotAcquire'),
        ))

    melSet = MelSet(
        MelEdid(),
        MelTruncatedStruct(
            b'CSTD', '2B2s8f2B2s3fB3s2f5B3s2f2B2s7fB3sfI', 'dodgeChance',
            'lrChance', ('unused1', null2), 'lrTimerMin', 'lrTimerMax',
            'forTimerMin', 'forTimerMax', 'backTimerMin', 'backTimerMax',
            'idleTimerMin', 'idleTimerMax', 'blkChance', 'atkChance',
            ('unused2', null2), 'atkBRecoil', 'atkBunc', 'atkBh2h',
            'pAtkChance', ('unused3', null3), 'pAtkBRecoil', 'pAtkBUnc',
            'pAtkNormal', 'pAtkFor', 'pAtkBack', 'pAtkL', 'pAtkR',
            ('unused4', null3), 'holdTimerMin', 'holdTimerMax',
            (_flagsA, 'flagsA'), 'acroDodge', ('unused5', null2),
            ('rMultOpt', 1.0), ('rMultMax', 1.0), ('mDistance', 250.0),
            ('rDistance', 1000.0), ('buffStand', 325.0), ('rStand', 500.0),
            ('groupStand', 325.0), ('rushChance', 25), ('unused6', null3),
            ('rushMult', 1.0), (_flagsB, 'flagsB'), old_versions={
                '2B2s8f2B2s3fB3s2f5B3s2f2B2s7fB3sf',
                '2B2s8f2B2s3fB3s2f5B3s2f2B2s7f',
                '2B2s8f2B2s3fB3s2f5B3s2f2B2s5f',
                '2B2s8f2B2s3fB3s2f5B3s2f2B2s2f',
                '2B2s8f2B2s3fB3s2f5B3s2f2B2s',
            }),
        MelOptStruct(b'CSAD', '21f', 'dodgeFMult', 'dodgeFBase', 'encSBase',
                     'encSMult', 'dodgeAtkMult', 'dodgeNAtkMult',
                     'dodgeBAtkMult', 'dodgeBNAtkMult', 'dodgeFAtkMult',
                     'dodgeFNAtkMult', 'blockMult', 'blockBase',
                     'blockAtkMult', 'blockNAtkMult', 'atkMult', 'atkBase',
                     'atkAtkMult', 'atkNAtkMult', 'atkBlockMult', 'pAtkFBase',
                     'pAtkFMult'),
        )
    __slots__ = melSet.getSlotsUsed()

class MreDial(MelRecord):
    """Dialogue."""
    rec_sig = b'DIAL'

    melSet = MelSet(
        MelEdid(),
        MelFids(b'QSTI', u'quests'),
        MelFids(b'QSTR', u'quests2'), # xEdit calls it 'Quests?'
        MelFull(),
        MelUInt8(b'DATA', u'dialType'),
    )
    __slots__ = melSet.getSlotsUsed()

class MreDoor(MelRecord):
    """Door."""
    rec_sig = b'DOOR'

    _flags = Flags(0, Flags.getNames('oblivionGate', 'automatic', 'hidden',
                                     'minimalUse'))

    melSet = MelSet(
        MelEdid(),
        MelFull(),
        MelModel(),
        MelScript(),
        MelFid(b'SNAM','soundOpen'),
        MelFid(b'ANAM','soundClose'),
        MelFid(b'BNAM','soundLoop'),
        MelUInt8Flags(b'FNAM', u'flags', _flags),
        MelFids(b'TNAM','destinations'),
    )
    __slots__ = melSet.getSlotsUsed()

class MreEfsh(MelRecord):
    """Effect Shader."""
    rec_sig = b'EFSH'

    _flags = Flags(0, Flags.getNames(
        (0, u'noMemShader'),
        (3, u'noPartShader'),
        (4, u'edgeInverse'),
        (5, u'memSkinOnly'),
    ))

    melSet = MelSet(
        MelEdid(),
        MelIcon(u'fillTexture'),
        MelIco2(u'particleTexture'),
        MelTruncatedStruct(b'DATA', u'B3s3I3Bs9f3Bs8f5I19f3Bs3Bs3Bs6f',
            (_flags, u'flags'), (u'unused1', null3), u'memSBlend',
            u'memBlendOp', u'memZFunc', u'fillRed', u'fillGreen', u'fillBlue',
            (u'unused2', null1), u'fillAIn', u'fillAFull', u'fillAOut',
            u'fillAPRatio', u'fillAAmp', u'fillAFreq', u'fillAnimSpdU',
            u'fillAnimSpdV', u'edgeOff', u'edgeRed', u'edgeGreen', u'edgeBlue',
            (u'unused3', null1), u'edgeAIn', u'edgeAFull', u'edgeAOut',
            u'edgeAPRatio', u'edgeAAmp', u'edgeAFreq', u'fillAFRatio',
            u'edgeAFRatio', u'memDBlend', (u'partSBlend', 5),
            (u'partBlendOp', 1), (u'partZFunc', 4), (u'partDBlend', 6),
            u'partBUp', u'partBFull', u'partBDown', (u'partBFRatio', 1.0),
            (u'partBPRatio', 1.0), (u'partLTime', 1.0), u'partLDelta',
            u'partNSpd', u'partNAcc', u'partVel1', u'partVel2', u'partVel3',
            u'partAcc1', u'partAcc2', u'partAcc3', u'partKey1',
            (u'partKey2', 1.0), u'partKey1Time', (u'partKey2Time', 1.0),
            (u'key1Red', 255), (u'key1Green', 255), (u'key1Blue', 255),
            (u'unused4', null1), (u'key2Red', 255), (u'key2Green', 255),
            (u'key2Blue', 255), (u'unused5', null1), (u'key3Red', 255),
            (u'key3Green', 255), (u'key3Blue', 255), (u'unused6', null1),
            (u'key1A', 1.0), (u'key2A', 1.0), (u'key3A', 1.0), u'key1Time',
            (u'key2Time', 0.5), (u'key3Time', 1.0),
            old_versions={u'B3s3I3Bs9f3Bs8fI'}),
    )
    __slots__ = melSet.getSlotsUsed()

class MreEnch(MelRecord,MreHasEffects):
    """Enchantment."""
    rec_sig = b'ENCH'

    _flags = Flags(0, Flags.getNames('noAutoCalc'))

    melSet = MelSet(
        MelEdid(),
        MelObme(),
        MelFull(), #--At least one mod has this. Odd.
        MelStruct(b'ENIT', '3IB3s', 'itemType', 'chargeAmount', 'enchantCost',
                  (_flags, 'flags', 0), ('unused1', null3)),
        MelEffects(),
        MelEffectsObmeFull(),
    ).with_distributor(_effects_distributor)
    __slots__ = melSet.getSlotsUsed()

class MreEyes(MelRecord):
    """Eyes."""
    rec_sig = b'EYES'

    _flags = Flags(0, Flags.getNames('playable',))

    melSet = MelSet(
        MelEdid(),
        MelFull(),
        MelIcon(),
        MelUInt8Flags(b'DATA', u'flags', _flags),
    )
    __slots__ = melSet.getSlotsUsed()

class MreFact(MelRecord):
    """Faction."""
    rec_sig = b'FACT'

    _general_flags = Flags(0, Flags.getNames(u'hidden_from_pc', u'evil',
                                             u'special_combat'))

    melSet = MelSet(
        MelEdid(),
        MelFull(),
        MelGroups(u'relations',
            MelStruct(b'XNAM', u'Ii', (FID, u'faction'), u'mod'),
        ),
        MelUInt8Flags(b'DATA', u'general_flags', _general_flags),
        # None here is on purpose! See AssortedTweak_FactioncrimeGoldMultiplier
        MelOptFloat(b'CNAM', u'crime_gold_multiplier', None),
        MelGroups(u'ranks',
            MelSInt32(b'RNAM', u'rank_level'),
            MelString(b'MNAM', u'male_title'),
            MelString(b'FNAM', u'female_title'),
            MelString(b'INAM', u'insignia_path')),
    )
    __slots__ = melSet.getSlotsUsed()

class MreFlor(MelRecord):
    """Flora."""
    rec_sig = b'FLOR'

    melSet = MelSet(
        MelEdid(),
        MelFull(),
        MelModel(),
        MelScript(),
        MelFid(b'PFIG','ingredient'),
        MelStruct(b'PFPC','4B','spring','summer','fall','winter'),
    )
    __slots__ = melSet.getSlotsUsed()

class MreFurn(MelRecord):
    """Furniture."""
    rec_sig = b'FURN'

    _flags = Flags() #--Governs type of furniture and which anims are available
    #--E.g., whether it's a bed, and which of the bed entry/exit animations
    # are available

    melSet = MelSet(
        MelEdid(),
        MelFull(),
        MelModel(),
        MelScript(),
        MelUInt32Flags(b'MNAM', u'activeMarkers', _flags), # ByteArray in xEdit
    )
    __slots__ = melSet.getSlotsUsed()

class MreGmst(MreGmstBase):
    """Game Setting."""

class MreGras(MelRecord):
    """Grass."""
    rec_sig = b'GRAS'

    _flags = Flags(0,Flags.getNames('vLighting','uScaling','fitSlope'))

    melSet = MelSet(
        MelEdid(),
        MelModel(),
        MelStruct(b'DATA', '3BsH2sI4fB3s', 'density', 'minSlope', 'maxSlope',
                  ('unused1', null1), 'waterDistance', ('unused2', null2),
                  'waterOp', 'posRange', 'heightRange', 'colorRange',
                  'wavePeriod', (_flags, 'flags'), ('unused3', null3)),
    )
    __slots__ = melSet.getSlotsUsed()

class MreHair(MelRecord):
    """Hair."""
    rec_sig = b'HAIR'

    _flags = Flags(0, Flags.getNames('playable','notMale','notFemale','fixed'))

    melSet = MelSet(
        MelEdid(),
        MelFull(),
        MelModel(),
        MelIcon(),
        MelUInt8Flags(b'DATA', u'flags', _flags),
    )
    __slots__ = melSet.getSlotsUsed()

class MreIdle(MelRecord):
    """Idle Animation."""
    rec_sig = b'IDLE'

    melSet = MelSet(
        MelEdid(),
        MelModel(),
        MelConditions(),
        MelUInt8(b'ANAM', 'group'),
        MelArray('related_animations',
            MelStruct(b'DATA', '2I', (FID, 'parent'), (FID, 'prevId')),
        ),
    )
    __slots__ = melSet.getSlotsUsed()

class MreInfo(MelRecord):
    """Dialog Response."""
    rec_sig = b'INFO'

    _flags = Flags(0, Flags.getNames(u'goodbye', u'random', u'sayOnce',
        u'runImmediately', u'infoRefusal', u'randomEnd', u'runForRumors'))

    melSet = MelSet(
        MelTruncatedStruct(b'DATA', u'3B', u'dialType', u'nextSpeaker',
                           (_flags, u'flags'), old_versions={u'H'}),
        MelFid(b'QSTI', u'info_quest'),
        MelFid(b'TPIC', u'info_topic'),
        MelFid(b'PNAM', u'prevInfo'),
        MelFids(b'NAME', u'addTopics'),
        MelGroups(u'responses',
            MelStruct(b'TRDT', u'Ii4sB3s', u'emotionType', u'emotionValue',
                (u'unused1', null4), u'responseNum', (u'unused2', null3)),
            MelString(b'NAM1', u'responseText'),
            MelString(b'NAM2', u'actorNotes'),
        ),
        MelConditions(),
        MelFids(b'TCLT', u'choices'),
        MelFids(b'TCLF', u'linksFrom'),
        MelEmbeddedScript(),
    )
    __slots__ = melSet.getSlotsUsed()

class MreIngr(MelRecord,MreHasEffects):
    """Ingredient."""
    rec_sig = b'INGR'

    _flags = Flags(0, Flags.getNames('noAutoCalc','isFood'))

    melSet = MelSet(
        MelEdid(),
        MelObme(),
        MelFull(),
        MelModel(),
        MelIcon(),
        MelScript(),
        MelFloat(b'DATA', 'weight'),
        MelStruct(b'ENIT','iB3s','value',(_flags,'flags',0),('unused1',null3)),
        MelEffects(),
        MelEffectsObmeFull(),
    ).with_distributor(_effects_distributor)
    __slots__ = melSet.getSlotsUsed()

class MreKeym(MelRecord):
    """Key."""
    rec_sig = b'KEYM'

    melSet = MelSet(
        MelEdid(),
        MelFull(),
        MelModel(),
        MelIcon(),
        MelScript(),
        MelStruct(b'DATA','if','value','weight'),
    )
    __slots__ = melSet.getSlotsUsed()

class MreLigh(MelRecord):
    """Light."""
    rec_sig = b'LIGH'

    _flags = Flags(0,  Flags.getNames(
        'dynamic', 'canTake', 'negative', 'flickers', 'unk1', 'offByDefault',
        'flickerSlow', 'pulse', 'pulseSlow', 'spotLight', 'spotShadow'))

    melSet = MelSet(
        MelEdid(),
        MelModel(),
        MelScript(),
        MelFull(),
        MelIcon(),
        MelTruncatedStruct(b'DATA', 'iI3BsIffIf', 'duration', 'radius', 'red',
                           'green', 'blue', ('unused1', null1),
                           (_flags, 'flags', 0), 'falloff', 'fov', 'value',
                           'weight', old_versions={'iI3BsI2f'}),
        # None here is on purpose! See AssortedTweak_LightFadeValueFix
        MelOptFloat(b'FNAM', u'fade', None),
        MelFid(b'SNAM','sound'),
    )
    __slots__ = melSet.getSlotsUsed()

class MreLscr(MelRecord):
    """Load Screen."""
    rec_sig = b'LSCR'

    melSet = MelSet(
        MelEdid(),
        MelIcon(),
        MelDescription(),
        MelGroups('locations',
            MelStruct(b'LNAM', '2I2h', (FID, 'direct'), (FID, 'indirect'),
                      'gridy', 'gridx'),
        ),
    )
    __slots__ = melSet.getSlotsUsed()

class MreLtex(MelRecord):
    """Landscape Texture."""
    rec_sig = b'LTEX'

    _flags = Flags(0, Flags.getNames(
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
        (14,'snow'),))

    melSet = MelSet(
        MelEdid(),
        MelIcon(),
        MelOptStruct(b'HNAM', '3B', (_flags, 'flags'), 'friction',
                     'restitution'), ##: flags are actually an enum....
        MelOptUInt8(b'SNAM', 'specular'),
        MelFids(b'GNAM', 'grass'),
    )
    __slots__ = melSet.getSlotsUsed()

class MreLvlc(MreLeveledList):
    """Leveled Creature."""
    rec_sig = b'LVLC'
    __slots__ = []

class MreLvli(MreLeveledList):
    """Leveled Item."""
    rec_sig = b'LVLI'
    __slots__ = []

class MreLvsp(MreLeveledList):
    """Leveled Spell."""
    rec_sig = b'LVSP'
    __slots__ = []

class MreMgef(MelRecord):
    """Magic Effect."""
    rec_sig = b'MGEF'

    _obme_flag_overrides = Flags(0, Flags.getNames(
        (2,  u'ov_param_flag_a'),
        (3,  u'ov_beneficial'),
        (16, u'ov_param_flag_b'),
        (17, u'ov_magnitude_is_range'),
        (18, u'ov_atomic_resistance'),
        (19, u'ov_param_flag_c'),
        (20, u'ov_param_flag_d'),
        (30, u'ov_hidden'),
    ))
    _flags = Flags(0, Flags.getNames(
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
        (27, u'noHitEffect'),))

    melSet = MelSet(
        MelEdid(),
        MelObme(extra_format=u'2B2s4sI4s', extra_contents=[
            u'obme_param_a_info', u'obme_param_b_info', u'obme_unused_mgef',
            u'obme_handler', (_obme_flag_overrides, u'obme_flag_overrides'),
            u'obme_param_b']),
        MelUnion({
            None: MelNull(b'EDDX'), # discard for non-OBME records
        }, decider=AttrValDecider(u'obme_record_version'),
            fallback=MelString(b'EDDX', u'obme_eid')),
        MelFull(),
        MelString(b'DESC', u'text'),
        MelIcon(),
        MelModel(),
        MelPartialCounter(MelTruncatedStruct(
            b'DATA', u'IfIiiH2sIf6I2f', (_flags, u'flags'), u'base_cost',
            (FID, u'associated_item'), u'school', u'resist_value',
            u'counter_effect_count', (u'unused1', null2),
            (FID, u'light'), u'projectileSpeed', (FID, u'effectShader'),
            (FID, u'enchantEffect'), (FID, u'castingSound'),
            (FID, u'boltSound'), (FID, u'hitSound'), (FID, u'areaSound'),
            u'cef_enchantment', u'cef_barter', old_versions={u'IfIiiH2sIfI'}),
            counter=u'counter_effect_count', counts=u'counter_effects'),
        MelArray(u'counter_effects',
            MelStruct(b'ESCE', u'4s', u'counter_effect_code'),
        ),
    )
    __slots__ = melSet.getSlotsUsed()

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
            False: MelStruct(b'DATA', u'if', u'value', u'weight'),
            True: MelStruct(b'DATA', u'2I', (FID, u'value'), u'weight'),
        }, decider=FlagDecider(u'flags1', u'borderRegion', u'turnFireOff')),
    )
    __slots__ = melSet.getSlotsUsed()

class MreNpc(MreActorBase):
    """Non-Player Character."""
    rec_sig = b'NPC_'

    _flags = Flags(0, Flags.getNames(
        ( 0,'female'),
        ( 1,'essential'),
        ( 3,'respawn'),
        ( 4,'autoCalc'),
        ( 7,'pcLevelOffset'),
        ( 9,'noLowLevel'),
        (13,'noRumors'),
        (14,'summonable'),
        (15,'noPersuasion'),
        (20,'canCorpseCheck'),))

    aiService = Flags(0, Flags.getNames(
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
        (17,'repair'),))

    class MelNpcData(MelLists):
        """Convert npc stats into skills, health, attributes."""
        _attr_indexes = OrderedDict( # 21 skills and 7 attributes
            [(u'skills', slice(21)), (u'health', 21), (u'unused2', 22),
             (u'attributes', slice(23, None))])

    melSet = MelSet(
        MelEdid(),
        MelFull(),
        MelModel(),
        MelStruct(b'ACBS','=I3Hh2H',
            (_flags,'flags',0),'baseSpell','fatigue','barterGold',
            ('level',1),'calcMin','calcMax'),
        MelGroups(u'factions',
            MelStruct(b'SNAM', u'IB3s', (FID, u'faction'), u'rank',
                      (u'unused1', b'ODB')),
        ),
        MelFid(b'INAM','deathItem'),
        MelFid(b'RNAM','race'),
        MelSpells(),
        MelScript(),
        MelItems(),
        MelStruct(b'AIDT', '=4BIbB2s', ('aggression', 5), ('confidence', 50),
                  ('energyLevel', 50), ('responsibility', 50),
                  (aiService, 'services', 0), 'trainSkill', 'trainLevel',
                  ('unused1', null2)),
        MelFids(b'PKID','aiPackages'),
        MelStrings(b'KFFZ','animations'),
        MelFid(b'CNAM','iclass'),
        MelNpcData(b'DATA', u'=21BH2s8B', (u'skills', [0 for _x in range(21)]),
                   u'health', (u'unused2', null2),
                   (u'attributes', [0 for _y in range(8)])),
        MelFid(b'HNAM','hair'),
        # None here is on purpose, for race patcher
        MelOptFloat(b'LNAM', u'hairLength', None),
        MelFid(b'ENAM','eye'), ####fid Array
        MelStruct(b'HCLR', '3Bs', 'hairRed', 'hairBlue', 'hairGreen',
                  ('unused3', null1)),
        MelFid(b'ZNAM','combatStyle'),
        MelBase(b'FGGS','fggs_p'), ####FaceGen Geometry-Symmetric
        MelBase(b'FGGA','fgga_p'), ####FaceGen Geometry-Asymmetric
        MelBase(b'FGTS','fgts_p'), ####FaceGen Texture-Symmetric
        MelUInt16(b'FNAM', 'fnam'), ####Byte Array
    )
    __slots__ = melSet.getSlotsUsed()

    def setRace(self,race):
        """Set additional race info."""
        self.race = race
        if not self.model:
            self.model = self.getDefault('model')
        if race in (0x23fe9,0x223c7):
            self.model.modPath = u"Characters\\_Male\\SkeletonBeast.NIF"
        else:
            self.model.modPath = u"Characters\\_Male\\skeleton.nif"
        fnams = {
            0x23fe9 : 0x3cdc ,#--Argonian
            0x224fc : 0x1d48 ,#--Breton
            0x191c1 : 0x5472 ,#--Dark Elf
            0x19204 : 0x21e6 ,#--High Elf
            0x00907 : 0x358e ,#--Imperial
            0x22c37 : 0x5b54 ,#--Khajiit
            0x224fd : 0x03b6 ,#--Nord
            0x191c0 : 0x0974 ,#--Orc
            0x00d43 : 0x61a9 ,#--Redguard
            0x00019 : 0x4477 ,#--Vampire
            0x223c8 : 0x4a2e ,#--Wood Elf
            }
        self.fnam = fnams.get(race,0x358e)

class MrePack(MelRecord):
    """AI Package."""
    rec_sig = b'PACK'

    _flags = Flags(0,Flags.getNames(
        'offersServices','mustReachLocation','mustComplete','lockAtStart',
        'lockAtEnd','lockAtLocation','unlockAtStart','unlockAtEnd',
        'unlockAtLocation','continueIfPcNear','oncePerDay',None,
        'skipFallout','alwaysRun',None,None,
        None,'alwaysSneak','allowSwimming','allowFalls',
        'unequipArmor','unequipWeapons','defensiveCombat','useHorse',
        'noIdleAnims',))

    melSet = MelSet(
        MelEdid(),
        MelTruncatedStruct(b'PKDT', 'IB3s', (_flags, 'flags'), 'aiType',
                           ('unused1', null3), old_versions={'HBs'}),
        MelUnion({
            (0, 1, 2, 3, 4): MelStruct(b'PLDT', u'iIi', u'locType',
                (FID, u'locId'), u'locRadius'),
            5: MelStruct(b'PLDT', u'iIi', u'locType', u'locId', u'locRadius'),
        }, decider=PartialLoadDecider(
            loader=MelSInt32(b'PLDT', u'locType'),
            decider=AttrValDecider(u'locType'),
        )),
        MelStruct(b'PSDT', u'2bBbi', u'month', u'day', u'date', u'time',
            u'duration'),
        MelUnion({
            (0, 1): MelOptStruct(b'PTDT', u'iIi', u'targetType',
                (FID, u'targetId'), u'targetCount'),
            2: MelOptStruct(b'PTDT', u'iIi', u'targetType', u'targetId',
                u'targetCount'),
        }, decider=PartialLoadDecider(
            loader=MelSInt32(b'PTDT', u'targetType'),
            decider=AttrValDecider(u'targetType'),
        )),
        MelConditions(),
    )
    __slots__ = melSet.getSlotsUsed()

class MrePgrd(MelRecord):
    """Path Grid."""
    rec_sig = b'PGRD'

    # Most of these MelBases could be loaded via MelArray, but they're really
    # big, don't contain FormIDs and are too complex to manipulate
    melSet = MelSet(
        MelUInt16(b'DATA', u'point_count'),
        MelBase(b'PGRP', u'point_array'),
        MelBase(b'PGAG', u'unknown1'),
        MelBase(b'PGRR', u'point_to_point_connections'),
        MelBase(b'PGRI', u'inter_cell_connections'),
        MelGroups(u'point_to_reference_mappings',
            MelArray(u'mapping_points', MelUInt32(b'PGRL', u'm_point'),
                prelude=MelFid(b'PGRL', u'mapping_reference'))
        ),
    )
    __slots__ = melSet.getSlotsUsed()

class MreQust(MelRecord):
    """Quest."""
    rec_sig = b'QUST'

    _questFlags = Flags(0, Flags.getNames('startGameEnabled', None,
                                          'repeatedTopics', 'repeatedStages'))
    stageFlags = Flags(0,Flags.getNames('complete'))
    targetFlags = Flags(0,Flags.getNames('ignoresLocks'))

    melSet = MelSet(
        MelEdid(),
        MelScript(),
        MelFull(),
        MelIcon(),
        MelStruct(b'DATA','BB',(_questFlags,'questFlags',0),'priority'),
        MelConditions(),
        MelGroups('stages',
            MelSInt16(b'INDX', 'stage'),
            MelGroups('entries',
                MelUInt8Flags(b'QSDT', u'flags', stageFlags),
                MelConditions(),
                MelString(b'CNAM','text'),
                MelEmbeddedScript(),
            ),
        ),
        MelGroups('targets',
            MelStruct(b'QSTA', 'IB3s', (FID, 'targetId'),
                      (targetFlags, 'flags'), ('unused1', null3)),
            MelConditions(),
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
    __slots__ = melSet.getSlotsUsed()

class MreRace(MelRecord):
    """Race."""
    rec_sig = b'RACE'

    _flags = Flags(0, Flags.getNames('playable'))

    melSet = MelSet(
        MelEdid(),
        MelFull(),
        MelDescription(u'text'),
        MelSpells(),
        MelGroups(u'relations',
            MelStruct(b'XNAM', 'Ii', (FID, 'faction'), 'mod'),
        ),
        MelStruct(b'DATA', '14b2s4fI', 'skill1', 'skill1Boost', 'skill2',
                  'skill2Boost', 'skill3', 'skill3Boost', 'skill4',
                  'skill4Boost', 'skill5', 'skill5Boost', 'skill6',
                  'skill6Boost', 'skill7', 'skill7Boost', ('unused1', null2),
                  'maleHeight', 'femaleHeight', 'maleWeight', 'femaleWeight',
                  (_flags, 'flags', 0)),
        MelRaceVoices(b'VNAM', '2I', (FID, 'maleVoice'), (FID, 'femaleVoice')),
        MelOptStruct(b'DNAM', '2I', (FID, 'defaultHairMale', 0),
                     (FID, 'defaultHairFemale', 0)),
        # Corresponds to GMST sHairColorNN
        MelUInt8(b'CNAM', 'defaultHairColor'),
        MelOptFloat(b'PNAM', 'mainClamp'),
        MelOptFloat(b'UNAM', 'faceClamp'),
        MelStruct(b'ATTR', '16B', 'maleStrength', 'maleIntelligence',
                  'maleWillpower', 'maleAgility', 'maleSpeed', 'maleEndurance',
                  'malePersonality', 'maleLuck', 'femaleStrength',
                  'femaleIntelligence', 'femaleWillpower', 'femaleAgility',
                  'femaleSpeed', 'femaleEndurance', 'femalePersonality',
                  'femaleLuck'),
        # Indexed Entries
        MelBase(b'NAM0', u'face_data_marker', b''),
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
            # None here is on purpose - 0 is a legitimate value
            MelOptFloat(b'MODB', u'modb', None),
            MelBase(b'MODT', 'modt_p'),
            MelIcon(),
        )),
        MelBase(b'NAM1', u'body_data_marker', b''),
        MelBase(b'MNAM', u'male_body_data_marker', b''),
        MelModel(u'maleTailModel'),
        MelRaceParts({
            0: u'maleUpperBodyPath',
            1: u'maleLowerBodyPath',
            2: u'maleHandPath',
            3: u'maleFootPath',
            4: u'maleTailPath',
        }, group_loaders=lambda _indx: (MelIcon(),)),
        MelBase(b'FNAM', u'female_body_data_marker', b''),
        MelModel(u'femaleTailModel'),
        MelRaceParts({
            0: u'femaleUpperBodyPath',
            1: u'femaleLowerBodyPath',
            2: u'femaleHandPath',
            3: u'femaleFootPath',
            4: u'femaleTailPath',
        }, group_loaders=lambda _indx: (MelIcon(),)),
        # Normal Entries
        MelFidList(b'HNAM','hairs'),
        MelFidList(b'ENAM','eyes'),
        MelBase(b'FGGS','fggs_p'), ####FaceGen Geometry-Symmetric
        MelBase(b'FGGA','fgga_p'), ####FaceGen Geometry-Asymmetric
        MelBase(b'FGTS','fgts_p'), ####FaceGen Texture-Symmetric
        MelStruct(b'SNAM','2s',('snam_p',null2)),
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
    __slots__ = melSet.getSlotsUsed()

class MreRefr(MelRecord):
    """Placed Object."""
    rec_sig = b'REFR'

    _lockFlags = Flags(0, Flags.getNames((2, u'leveledLock')))

    class MelRefrXloc(MelTruncatedStruct):
        """Skips unused2, in the middle of the struct."""
        def _pre_process_unpacked(self, unpacked_val):
            if len(unpacked_val) == 5:
                unpacked_val = (unpacked_val[:-2]
                                + self.defaults[len(unpacked_val) - 2:-2]
                                + unpacked_val[-2:])
            return unpacked_val

    melSet = MelSet(
        MelEdid(),
        MelFid(b'NAME', u'base'),
        MelOptStruct(b'XTEL', u'I6f', (FID, u'destinationFid'),
            u'destinationPosX', u'destinationPosY', u'destinationPosZ',
            u'destinationRotX', u'destinationRotY', u'destinationRotZ'),
        MelRefrXloc(b'XLOC', u'B3sI4sB3s', u'lockLevel', (u'unused1', null3),
            (FID, u'lockKey'), (u'unused2', null4), (_lockFlags, u'lockFlags'),
            (u'unused3', null3), is_optional=True, old_versions={u'B3sIB3s'}),
        MelOwnershipTes4(),
        MelEnableParent(),
        MelFid(b'XTRG', u'targetId'),
        MelBase(b'XSED', u'seed_p'),
        ####SpeedTree Seed, if it's a single byte then it's an offset into
        # the list of seed values in the TREE record
        ####if it's 4 byte it's the seed value directly.
        MelXlod(),
        MelOptFloat(b'XCHG', u'charge'),
        MelOptSInt32(b'XHLT', u'health'),
        MelNull(b'XPCI'), # These two are unused
        MelReadOnly(MelFull()), # Can't use MelNull, we need to distribute
        MelOptSInt32(b'XLCM', u'levelMod'),
        MelFid(b'XRTM', u'teleport_ref'),
        MelActionFlags(),
        MelOptSInt32(b'XCNT', u'count'),
        MelMapMarker(),
        MelBase(b'ONAM', u'open_by_default'),
        MelBase(b'XRGD', u'xrgd_p'), # Ragdoll Data, bytearray
        MelRefScale(),
        MelOptUInt8(b'XSOL', u'ref_soul'),
        MelRef3D(),
    ).with_distributor({
        b'FULL': u'full', # unused, but still need to distribute it
        b'XMRK': {
            b'FULL': u'map_marker',
        },
    })
    __slots__ = melSet.getSlotsUsed()

class MreRegn(MelRecord):
    """Region."""
    rec_sig = b'REGN'

    rdatFlags = Flags(0, Flags.getNames(
        ( 0,'Override'),))
    obflags = Flags(0, Flags.getNames(
        ( 0,'conform'),
        ( 1,'paintVertices'),
        ( 2,'sizeVariance'),
        ( 3,'deltaX'),
        ( 4,'deltaY'),
        ( 5,'deltaZ'),
        ( 6,'Tree'),
        ( 7,'hugeRock'),))
    sdflags = Flags(0, Flags.getNames(
        ( 0,'pleasant'),
        ( 1,'cloudy'),
        ( 2,'rainy'),
        ( 3,'snowy'),))

    melSet = MelSet(
        MelEdid(),
        MelIcon(),
        MelStruct(b'RCLR','3Bs','mapRed','mapBlue','mapGreen',('unused1',null1)),
        MelFid(b'WNAM','worldspace'),
        MelGroups('areas',
            MelUInt32(b'RPLI', 'edgeFalloff'),
            MelArray('points',
                MelStruct(b'RPLD', '2f', 'posX', 'posY'),
            ),
        ),
        MelGroups('entries',
            MelStruct(b'RDAT', 'I2B2s', 'entryType', (rdatFlags, 'flags'),
                      'priority', ('unused1', null2)),
            MelRegnEntrySubrecord(2, MelArray('objects',
                MelStruct(
                    b'RDOT', 'IH2sf4B2H5f3H2s4s', (FID, 'objectId'),
                    'parentIndex', ('unk1', null2), 'density', 'clustering',
                    'minSlope', 'maxSlope', (obflags, 'flags'),
                    'radiusWRTParent', 'radius', 'minHeight', 'maxHeight',
                    'sink', 'sinkVar', 'sizeVar', 'angleVarX', 'angleVarY',
                    'angleVarZ', ('unk2', null2), ('unk3', null4)),
            )),
            ##: Was disabled previously - not in xEdit either...
            # MelRegnEntrySubrecord(5, MelIcon()),
            MelRegnEntrySubrecord(4, MelString(b'RDMP', 'mapName')),
            MelRegnEntrySubrecord(6, MelArray('grasses',
                MelStruct(b'RDGS', 'I4s', (FID, 'grass'), ('unknown', null4)),
            )),
            MelRegnEntrySubrecord(7, MelOptUInt32(b'RDMD', 'musicType')),
            MelRegnEntrySubrecord(7, MelArray('sounds',
                MelStruct(b'RDSD', '3I', (FID, 'sound'), (sdflags, 'flags'),
                          'chance'),
            )),
            MelRegnEntrySubrecord(3, MelArray('weatherTypes',
                MelStruct(b'RDWT', u'2I', (FID, u'weather'), u'chance')
            )),
        ),
    )
    __slots__ = melSet.getSlotsUsed()

class MreRoad(MelRecord):
    """Road. Part of large worldspaces."""
    ####Could probably be loaded via MelArray,
    ####but little point since it is too complex to manipulate
    rec_sig = b'ROAD'

    melSet = MelSet(
        MelBase(b'PGRP','points_p'),
        MelBase(b'PGRR','connections_p'),
    )
    __slots__ = melSet.getSlotsUsed()

class MreSbsp(MelRecord):
    """Subspace."""
    rec_sig = b'SBSP'

    melSet = MelSet(
        MelEdid(),
        MelStruct(b'DNAM','3f','sizeX','sizeY','sizeZ'),
    )
    __slots__ = melSet.getSlotsUsed()

class MreScpt(MelRecord):
    """Script."""
    rec_sig = b'SCPT'

    melSet = MelSet(
        MelEdid(),
        MelEmbeddedScript(with_script_vars=True),
    )
    __slots__ = melSet.getSlotsUsed()

class MreSgst(MelRecord,MreHasEffects):
    """Sigil Stone."""
    rec_sig = b'SGST'

    melSet = MelSet(
        MelEdid(),
        MelObme(),
        MelFull(),
        MelModel(),
        MelIcon(),
        MelScript(),
        MelEffects(),
        MelEffectsObmeFull(),
        MelStruct(b'DATA','=BIf','uses','value','weight'),
    ).with_distributor(_effects_distributor)
    __slots__ = melSet.getSlotsUsed()

class MreSkil(MelRecord):
    """Skill."""
    rec_sig = b'SKIL'

    melSet = MelSet(
        MelEdid(),
        MelSInt32(b'INDX', 'skill'),
        MelDescription(),
        MelIcon(),
        MelStruct(b'DATA','2iI2f','action','attribute','specialization',('use0',1.0),'use1'),
        MelString(b'ANAM','apprentice'),
        MelString(b'JNAM','journeyman'),
        MelString(b'ENAM','expert'),
        MelString(b'MNAM','master'),
    )
    __slots__ = melSet.getSlotsUsed()

class MreSlgm(MelRecord):
    """Soul Gem."""
    rec_sig = b'SLGM'

    melSet = MelSet(
        MelEdid(),
        MelFull(),
        MelModel(),
        MelIcon(),
        MelScript(),
        MelStruct(b'DATA','If','value','weight'),
        MelUInt8(b'SOUL', u'soul'),
        MelUInt8(b'SLCP', u'capacity', 1),
    )
    __slots__ = melSet.getSlotsUsed()

class MreSoun(MelRecord):
    """Sound."""
    rec_sig = b'SOUN'
    _has_duplicate_attrs = True # SNDD is an older version of SNDX

    _flags = Flags(0, Flags.getNames('randomFrequencyShift', 'playAtRandom',
        'environmentIgnored', 'randomLocation', 'loop','menuSound', '2d', '360LFE'))

    melSet = MelSet(
        MelEdid(),
        MelString(b'FNAM','soundFile'),
        # This is the old format of SNDX - read it, but dump SNDX only
        MelReadOnly(
            MelStruct(b'SNDD', u'2BbsH2s', u'minDistance', u'maxDistance',
                u'freqAdjustment', (u'unused1', null1), (_flags, u'flags'),
                (u'unused2', null2))
        ),
        MelStruct(b'SNDX', u'2BbsH2sH2B', u'minDistance', u'maxDistance',
            u'freqAdjustment', (u'unused1', null1), (_flags, u'flags'),
            (u'unused2', null2), u'staticAtten', u'stopTime', u'startTime'),
    )
    __slots__ = melSet.getSlotsUsed()

class MreSpel(MelRecord,MreHasEffects):
    """Spell."""
    rec_sig = b'SPEL'

    class SpellFlags(Flags):
        """For SpellFlags, immuneToSilence activates bits 1 AND 3."""
        def __setitem__(self,index,value):
            setter = Flags.__setitem__
            setter(self,index,value)
            if index == 1:
                setter(self,3,value)

    _SpellFlags = SpellFlags(0, Flags.getNames('noAutoCalc','immuneToSilence',
        'startSpell', None, 'ignoreLOS', 'scriptEffectAlwaysApplies',
        'disallowAbsorbReflect', 'touchExplodesWOTarget'))

    melSet = MelSet(
        MelEdid(),
        MelObme(),
        MelFull(),
        MelStruct(b'SPIT', '3IB3s', 'spellType', 'cost', 'level',
                  (_SpellFlags, 'flags', 0), ('unused1', null3)),
        MelEffects(),
        MelEffectsObmeFull(),
    ).with_distributor(_effects_distributor)
    __slots__ = melSet.getSlotsUsed()

class MreStat(MelRecord):
    """Static."""
    rec_sig = b'STAT'

    melSet = MelSet(
        MelEdid(),
        MelModel(),
    )
    __slots__ = melSet.getSlotsUsed()

class MreTree(MelRecord):
    """Tree."""
    rec_sig = b'TREE'

    melSet = MelSet(
        MelEdid(),
        MelModel(),
        MelIcon(),
        MelArray('speedTree',
            MelUInt32(b'SNAM', 'seed'),
        ),
        MelStruct(b'CNAM','5fi2f', 'curvature','minAngle','maxAngle',
                  'branchDim','leafDim','shadowRadius','rockSpeed',
                  'rustleSpeed'),
        MelStruct(b'BNAM','2f','widthBill','heightBill'),
    )
    __slots__ = melSet.getSlotsUsed()

class MelWatrData(MelTruncatedStruct):
    """Chop off two junk bytes at the end of each older format."""
    def _pre_process_unpacked(self, unpacked_val):
        if len(unpacked_val) != 36:
            unpacked_val = unpacked_val[:-1]
        return super(MelWatrData, self)._pre_process_unpacked(unpacked_val)

class MreWatr(MelRecord):
    """Water."""
    rec_sig = b'WATR'

    _flags = Flags(0, Flags.getNames('causesDmg','reflective'))

    melSet = MelSet(
        MelEdid(),
        MelString(b'TNAM','texture'),
        MelUInt8(b'ANAM', 'opacity'),
        MelUInt8Flags(b'FNAM', u'flags', _flags),
        MelString(b'MNAM','material'),
        MelFid(b'SNAM','sound'),
        MelWatrData(
            b'DATA', '11f3Bs3Bs3BsB3s10fH', ('windVelocity', 0.100),
            ('windDirection', 90.0), ('waveAmp', 0.5), ('waveFreq', 1.0),
            ('sunPower', 50.0), ('reflectAmt', 0.5), ('fresnelAmt', 0.0250),
            ('xSpeed', 0.0), ('ySpeed', 0.0), ('fogNear', 27852.8),
            ('fogFar', 163840.0), ('shallowRed', 0), ('shallowGreen', 128),
            ('shallowBlue', 128), ('unused1', null1), ('deepRed', 0),
            ('deepGreen', 0), ('deepBlue', 25), ('unused2', null1),
            ('reflRed', 255), ('reflGreen', 255), ('reflBlue', 255),
            ('unused3', null1), ('blend', 50), ('unused4', null3),
            ('rainForce', 0.1000), ('rainVelocity', 0.6000),
            ('rainFalloff', 0.9850), ('rainDampner', 2.0000),
            ('rainSize', 0.0100), ('dispForce', 0.4000),
            ('dispVelocity', 0.6000), ('dispFalloff', 0.9850),
            ('dispDampner', 10.0000), ('dispSize', 0.0500), ('damage', 0),
            old_versions={'11f3Bs3Bs3BsB3s6f2s', '11f3Bs3Bs3BsB3s2s',
                          '10f2s', '2s'}),
        MelFidList(b'GNAM','relatedWaters'),
    )
    __slots__ = melSet.getSlotsUsed()

class MreWeap(MelRecord):
    """Weapon."""
    rec_sig = b'WEAP'

    _flags = Flags(0, Flags.getNames('notNormalWeapon'))

    melSet = MelSet(
        MelEdid(),
        MelFull(),
        MelModel(),
        MelIcon(),
        MelScript(),
        MelFid(b'ENAM','enchantment'),
        MelOptUInt16(b'ANAM', 'enchantPoints'),
        MelStruct(b'DATA','I2f3IfH','weaponType','speed','reach',(_flags,'flags',0),
            'value','health','weight','damage'),
    )
    __slots__ = melSet.getSlotsUsed()

class MreWrld(MelRecord):
    """Worldspace."""
    rec_sig = b'WRLD'

    _flags = Flags(0, Flags.getNames('smallWorld','noFastTravel','oblivionWorldspace',None,'noLODWater'))

    melSet = MelSet(
        MelEdid(),
        MelFull(),
        MelFid(b'WNAM','parent'),
        MelFid(b'CNAM','climate'),
        MelFid(b'NAM2','water'),
        MelIcon(u'mapPath'),
        MelStruct(b'MNAM', u'2i4h', u'dimX', u'dimY', u'NWCellX', u'NWCellY',
                  u'SECellX', u'SECellY'),
        MelUInt8Flags(b'DATA', u'flags', _flags),
        MelWorldBounds(),
        MelOptUInt32(b'SNAM', 'sound'),
        MelNull(b'OFST'), # Not even CK/xEdit can recalculate these right now
    )
    __slots__ = melSet.getSlotsUsed()

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
        MelStruct(b'FNAM','4f','fogDayNear','fogDayFar','fogNightNear','fogNightFar'),
        MelStruct(b'HNAM','14f',
            'eyeAdaptSpeed', 'blurRadius', 'blurPasses', 'emissiveMult',
            'targetLum', 'upperLumClamp', 'brightScale', 'brightClamp',
            'lumRampNoTex', 'lumRampMin', 'lumRampMax', 'sunlightDimmer',
            'grassDimmer', 'treeDimmer'),
        MelStruct(b'DATA','15B',
            'windSpeed','lowerCloudSpeed','upperCloudSpeed','transDelta',
            'sunGlare','sunDamage','rainFadeIn','rainFadeOut','boltFadeIn',
            'boltFadeOut','boltFrequency','weatherType','boltRed','boltBlue','boltGreen'),
        MelGroups('sounds',
            MelStruct(b'SNAM', '2I', (FID, 'sound'), 'type'),
        ),
    )
    __slots__ = melSet.getSlotsUsed()
