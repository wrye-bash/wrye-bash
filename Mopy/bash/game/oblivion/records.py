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
"""This module contains the oblivion record classes."""
from .constants import condition_function_data
from ... import brec
from ...bolt import Flags
from ...brec import MelRecord, MelGroups, MelStruct, FID, MelGroup, \
    MelString, MreLeveledListBase, MelSet, MelFid, MelNull, MelOptStruct, \
    MelFids, MreHeaderBase, MelBase, MelUnicode, MelFidList, MelStrings, \
    MreGmstBase, MreHasEffects, MelReferences, MelRegnEntrySubrecord, \
    MelFloat, MelSInt16, MelSInt32, MelUInt8, MelUInt16, MelUInt32, \
    MelOptFloat, MelOptSInt32, MelOptUInt8, MelOptUInt16, MelOptUInt32, \
    MelRaceParts, MelRaceVoices, null1, null2, null3, null4, MelScriptVars, \
    MelSequential, MelUnion, FlagDecider, AttrValDecider, PartialLoadDecider, \
    MelTruncatedStruct, MelCoordinates, MelIcon, MelIco2, MelEdid, MelFull, \
    MelArray, MelWthrColors
from ...exception import BoltError, ModSizeError, StateError
# Set brec MelModel to the one for Oblivion
if brec.MelModel is None:

    class _MelModel(MelGroup):
        """Represents a model record."""
        typeSets = (('MODL','MODB','MODT'),
                    ('MOD2','MO2B','MO2T'),
                    ('MOD3','MO3B','MO3T'),
                    ('MOD4','MO4B','MO4T'))

        def __init__(self,attr='model',index=0):
            """Initialize. Index is 0,2,3,4 for corresponding type id."""
            types = self.__class__.typeSets[(0,index-1)[index>0]]
            MelGroup.__init__(
                self, attr,
                MelString(types[0], 'modPath'),
                MelFloat(types[1], 'modb'),
                # Texture File Hashes
                MelBase(types[2], 'modt_p')
            )

    brec.MelModel = _MelModel
from ...brec import MelModel

#------------------------------------------------------------------------------
# Record Elements -------------------------------------------------------------
#------------------------------------------------------------------------------
class MreActor(MelRecord):
    """Creatures and NPCs."""

    def mergeFilter(self,modSet):
        """Filter out items that don't come from specified modSet.
        Filters spells, factions and items."""
        if not self.longFids: raise StateError(u"Fids not in long format")
        self.spells = [x for x in self.spells if x[0] in modSet]
        self.factions = [x for x in self.factions if x.faction[0] in modSet]
        self.items = [x for x in self.items if x.item[0] in modSet]

#------------------------------------------------------------------------------
class MelBipedFlags(Flags):
    """Biped flags element. Includes biped flag set by default."""
    mask = 0xFFFF
    def __init__(self,default=0,newNames=None):
        names = Flags.getNames('head', 'hair', 'upperBody', 'lowerBody',
                               'hand', 'foot', 'rightRing', 'leftRing',
                               'amulet', 'weapon', 'backWeapon', 'sideWeapon',
                               'quiver', 'shield', 'torch', 'tail')
        if newNames: names.update(newNames)
        Flags.__init__(self,default,names)

#------------------------------------------------------------------------------
class MelConditions(MelGroups):
    """Represents a set of quest/dialog conditions. Difficulty is that FID
    state of parameters depends on function index."""
    class MelCtda(MelStruct):
        def getLoaders(self,loaders):
            # Older CTDT type for ai package records.
            loaders[self.subType] = loaders['CTDT']= self

        def setDefault(self, record):
            MelStruct.setDefault(self, record)
            record.form12 = 'ii'

        def hasFids(self, formElements):
            formElements.add(self)

        def loadData(self, record, ins, sub_type, size_, readId):
            if sub_type == 'CTDA' and size_ != 24:
                raise ModSizeError(ins.inName, readId, (24,), size_)
            if sub_type == 'CTDT' and size_ != 20:
                raise ModSizeError(ins.inName, readId, (20,), size_)
            unpacked1 = ins.unpack('B3sfI', 12, readId)
            (record.operFlag, record.unused1, record.compValue,
             ifunc) = unpacked1
            #--Get parameters
            if ifunc not in condition_function_data:
                raise BoltError(u'Unknown condition function: %d\nparam1: '
                                u'%08X\nparam2: %08X' % (
                    ifunc, ins.unpackRef(), ins.unpackRef()))
            form1 = 'iI'[condition_function_data[ifunc][1] == 2] # 2 means fid
            form2 = 'iI'[condition_function_data[ifunc][2] == 2]
            form12 = form1 + form2
            unpacked2 = ins.unpack(form12,8,readId)
            record.param1, record.param2 = unpacked2
            if size_ == 24:
                record.unused2 = ins.read(4)
            else: # size == 20, verified at the start
                record.unused2 = null4
            record.ifunc, record.form12 = ifunc, form12

        def dumpData(self,record,out):
            out.packSub('CTDA','B3sfI'+ record.form12 + '4s',
                record.operFlag, record.unused1, record.compValue,
                record.ifunc, record.param1, record.param2, record.unused2)

        def mapFids(self,record,function,save=False):
            form12 = record.form12
            if form12[0] == 'I':
                result = function(record.param1)
                if save: record.param1 = result
            if form12[1] == 'I':
                result = function(record.param2)
                if save: record.param2 = result

        @property
        def signatures(self):
            return {'CTDA', 'CTDT'}

    def __init__(self):
        MelGroups.__init__(self, 'conditions',
            MelConditions.MelCtda(
                'CTDA', 'B3sfIii4s', 'operFlag', ('unused1', null3),
                'compValue', 'ifunc', 'param1', 'param2', ('unused2',null4)),
        )

#------------------------------------------------------------------------------
# A distributor config for use with MelEffects, since MelEffects also contains
# a FULL subrecord
_effects_distributor = {
    'FULL': 'full', # don't rely on EDID being present
    'EFID': {
        'FULL': 'effects',
    }
}

class MelEffects(MelGroups):
    """Represents ingredient/potion/enchantment/spell effects."""

    seFlags = Flags(0x0, Flags.getNames('hostile'))

     # TODO(inf) Do we really need to do this? It's an unused test spell
    class MelEffectsScit(MelTruncatedStruct):
        """The script fid for MS40TestSpell doesn't point to a valid script,
        so this class drops it."""
        def _pre_process_unpacked(self, unpacked_val):
            if len(unpacked_val) == 1:
                if unpacked_val[0] & 0xFF000000:
                    unpacked_val = (0,) # Discard bogus MS40TestSpell fid
            return MelTruncatedStruct._pre_process_unpacked(self, unpacked_val)

    def __init__(self,attr='effects'):
        MelGroups.__init__(self,attr,
            MelStruct('EFID','4s',('name','REHE')),
            MelStruct('EFIT', '4s4Ii', ('name', 'REHE'), 'magnitude', 'area',
                      'duration', 'recipient', 'actorValue'),
            MelGroup('scriptEffect',
                MelEffects.MelEffectsScit(
                    'SCIT', 'II4sB3s', (FID, 'script', None), ('school', 0),
                    ('visual', null4), (MelEffects.seFlags, 'flags', 0x0),
                    ('unused1', null3), old_versions={'2I4s', 'I'}),
                MelFull(),
            ),
        )

#------------------------------------------------------------------------------
class MelEmbeddedScript(MelSequential):
    """Handles an embedded script, a SCHR/SCDA/SCTX/SLSD/SCVR/SCRO/SCRV
    subrecord combo. SLSD and SCVR can optionally be disabled."""
    def __init__(self, with_script_vars=False):
        seq_elements = [
            MelUnion({
                'SCHR': MelStruct('SCHR', '4s4I', ('unused1', null4),
                                  'num_refs', 'compiled_size', 'last_index',
                                  'script_type'),
                'SCHD': MelBase('SCHD', 'old_script_header'),
            }),
            MelBase('SCDA', 'compiled_script'),
            MelString('SCTX', 'script_source')
        ]
        if with_script_vars: seq_elements += [MelScriptVars()]
        MelSequential.__init__(self, *(seq_elements + [MelReferences()]))

#------------------------------------------------------------------------------
class MelItems(MelGroups):
    """Wraps MelGroups for the common task of defining a list of items."""
    def __init__(self):
        MelGroups.__init__(self, 'items',
            MelStruct('CNTO', 'Ii', (FID, 'item'), 'count'),
        ),

#------------------------------------------------------------------------------
class MreLeveledList(MreLeveledListBase):
    """Leveled item/creature/spell list.."""
    top_copy_attrs = ('script','template','chanceNone',)

    class MelLevListLvld(MelUInt8):
        """Subclass to handle chanceNone and flags.calcFromAllLevels."""
        def __init__(self):
            MelUInt8.__init__(self, 'LVLD', 'chanceNone')

        def loadData(self, record, ins, sub_type, size_, readId):
            MelStruct.loadData(self, record, ins, sub_type, size_, readId)
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
            return MelTruncatedStruct._pre_process_unpacked(self, unpacked_val)

    melSet = MelSet(
        MelEdid(),
        MelLevListLvld(),
        MelUInt8('LVLF', (MreLeveledListBase._flags, 'flags', 0)),
        MelFid('SCRI','script'), # LVLC only
        MelFid('TNAM','template'),
        MelGroups('entries',
            MelLevListLvlo('LVLO', 'h2sIh2s', 'level', ('unused1', null2),
                           (FID, 'listId', None), ('count', 1),
                           ('unused2', null2), old_versions={'iI'}),
        ),
        MelNull('DATA'),
    )
    __slots__ = melSet.getSlotsUsed()

#------------------------------------------------------------------------------
class MelOwnership(MelGroup):
    """Handles XOWN, XRNK, and XGLB for cells and cell children."""
    def __init__(self,attr='ownership'):
        MelGroup.__init__(self,attr,
            MelFid('XOWN','owner'),
            MelOptSInt32('XRNK', ('rank',None)),
            MelFid('XGLB','global'),
        )

    def dumpData(self,record,out):
        if record.ownership and record.ownership.owner:
            MelGroup.dumpData(self,record,out)

#------------------------------------------------------------------------------
# Oblivion Records ------------------------------------------------------------
#------------------------------------------------------------------------------
class MreTes4(MreHeaderBase):
    """TES4 Record.  File header."""
    classType = 'TES4'

    melSet = MelSet(MelStruct('HEDR', 'f2I', ('version', 0.8), 'numRecords',
                              ('nextObject', 0x800)),
        MelBase('OFST','ofst_p',),  #--Obsolete?
        MelBase('DELE','dele_p',),  #--Obsolete?
        MelUnicode('CNAM','author',u'',512),
        MelUnicode('SNAM','description',u'',512),
        MreHeaderBase.MelMasterNames(),
        MelNull('DATA'),
    )
    __slots__ = melSet.getSlotsUsed()

class MreAchr(MelRecord):
    """Placed NPC."""
    classType = 'ACHR'

    _flags = Flags(0, Flags.getNames('oppositeParent'))

    melSet = MelSet(
        MelEdid(),
        MelFid('NAME','base'),
        # both unused
        MelNull('XPCI'),
        MelNull('FULL'),
        MelOptStruct('XLOD', '3f', ('lod1', None), ('lod2', None),
                     ('lod3', None)),
        MelOptStruct('XESP', 'IB3s', (FID, 'parent'), (_flags, 'parentFlags'),
                     ('unused1', null3)),
        MelFid('XMRC','merchantContainer'),
        MelFid('XHRS','horse'),
        MelBase('XRGD','xrgd_p'),
        MelOptFloat('XSCL', ('scale', 1.0)),
        MelOptStruct('DATA', '=6f', ('posX', None), ('posY', None),
                     ('posZ', None), ('rotX', None), ('rotY', None),
                     ('rotZ', None)),
    )
    __slots__ = melSet.getSlotsUsed()

class MreAcre(MelRecord):
    """Placed Creature."""
    classType = 'ACRE'

    _flags = Flags(0, Flags.getNames('oppositeParent'))

    melSet = MelSet(
        MelEdid(),
        MelFid('NAME','base'),
        MelOwnership(),
        MelOptStruct('XLOD', '3f', ('lod1', None), ('lod2', None),
                     ('lod3', None)), # ###Distant LOD Data, unknown
        MelOptStruct('XESP', 'IB3s', (FID, 'parent'), (_flags, 'parentFlags'),
                     ('unused1', null3)),
        MelBase('XRGD','xrgd_p'), ###Ragdoll Data, ByteArray
        MelOptFloat('XSCL', ('scale', 1.0)),
        MelOptStruct('DATA', '=6f', ('posX', None), ('posY', None),
                     ('posZ', None), ('rotX', None), ('rotY', None),
                     ('rotZ', None)),
    )
    __slots__ = melSet.getSlotsUsed()

class MreActi(MelRecord):
    """Activator."""
    classType = 'ACTI'

    melSet = MelSet(
        MelEdid(),
        MelFull(),
        MelModel(),
        MelFid('SCRI','script'),
        MelFid('SNAM','sound'),
    )
    __slots__ = melSet.getSlotsUsed()

class MreAlch(MelRecord,MreHasEffects):
    """Potion."""
    classType = 'ALCH'

    _flags = Flags(0, Flags.getNames('autoCalc','isFood'))

    melSet = MelSet(
        MelEdid(),
        MelFull(),
        MelModel(),
        MelIcon(),
        MelFid('SCRI','script'),
        MelFloat('DATA', 'weight'),
        MelStruct('ENIT','iB3s','value',(_flags,'flags',0),('unused1',null3)),
        MelEffects(),
    ).with_distributor(_effects_distributor)
    __slots__ = melSet.getSlotsUsed()

class MreAmmo(MelRecord):
    """Ammunition."""
    classType = 'AMMO'

    _flags = Flags(0, Flags.getNames('notNormalWeapon'))

    melSet = MelSet(
        MelEdid(),
        MelFull(),
        MelModel(),
        MelIcon(),
        MelFid('ENAM','enchantment'),
        MelOptUInt16('ANAM', 'enchantPoints'),
        MelStruct('DATA', 'fB3sIfH', 'speed', (_flags, 'flags', 0),
                  ('unused1', null3), 'value', 'weight', 'damage'),
    )
    __slots__ = melSet.getSlotsUsed()

class MreAnio(MelRecord):
    """Animation Object."""
    classType = 'ANIO'

    melSet = MelSet(
        MelEdid(),
        MelModel(),
        MelFid('DATA','animationId'),
    )
    __slots__ = melSet.getSlotsUsed()

class MreAppa(MelRecord):
    """Alchemical Apparatus."""
    classType = 'APPA'

    melSet = MelSet(
        MelEdid(),
        MelFull(),
        MelModel(),
        MelIcon(),
        MelFid('SCRI','script'),
        MelStruct('DATA', '=BIff', ('apparatus', 0), ('value', 25),
                  ('weight', 1), ('quality', 10)),
    )
    __slots__ = melSet.getSlotsUsed()

class MreArmo(MelRecord):
    """Armor."""
    classType = 'ARMO'

    _flags = MelBipedFlags(0, Flags.getNames((16, 'hideRings'),
                                             (17, 'hideAmulet'),
                                             (22, 'notPlayable'),
                                             (23, 'heavyArmor')))

    melSet = MelSet(
        MelEdid(),
        MelFull(),
        MelFid('SCRI','script'),
        MelFid('ENAM','enchantment'),
        MelOptUInt16('ANAM', 'enchantPoints'),
        MelUInt32('BMDT', (_flags, 'flags', 0)),
        MelModel('maleBody',0),
        MelModel('maleWorld',2),
        MelIcon('maleIconPath'),
        MelModel('femaleBody',3),
        MelModel('femaleWorld',4),
        MelIco2('femaleIconPath'),
        MelStruct('DATA','=HIIf','strength','value','health','weight'),
    )
    __slots__ = melSet.getSlotsUsed()

class MreBook(MelRecord):
    """Book."""
    classType = 'BOOK'

    _flags = Flags(0,Flags.getNames('isScroll','isFixed'))

    melSet = MelSet(
        MelEdid(),
        MelFull(),
        MelModel(),
        MelIcon(),
        MelString('DESC','text'),
        MelFid('SCRI','script'),
        MelFid('ENAM','enchantment'),
        MelOptUInt16('ANAM', 'enchantPoints'),
        MelStruct('DATA', '=BbIf', (_flags, 'flags', 0), ('teaches', -1),
                  'value', 'weight'),
    )
    __slots__ = melSet.getSlotsUsed() + ['modb']

class MreBsgn(MelRecord):
    """Birthsign."""
    classType = 'BSGN'

    melSet = MelSet(
        MelEdid(),
        MelFull(),
        MelIcon(),
        MelString('DESC','text'),
        MelFids('SPLO','spells'),
    )
    __slots__ = melSet.getSlotsUsed()

class MreCell(MelRecord):
    """Cell."""
    classType = 'CELL'

    cellFlags = Flags(0, Flags.getNames(
        (0,'isInterior'),
        (1,'hasWater'),
        (2,'invertFastTravel'),
        (3,'forceHideLand'),
        (5,'publicPlace'),
        (6,'handChanged'),
        (7,'behaveLikeExterior')
        ))

    melSet = MelSet(
        MelEdid(),
        MelFull(),
        MelUInt8('DATA', (cellFlags, 'flags', 0)),
        MelCoordinates('XCLC', '2i', ('posX', None), ('posY', None),
                       is_optional=True, old_versions=set()),
        MelOptStruct('XCLL', '=3Bs3Bs3Bs2f2i2f', 'ambientRed', 'ambientGreen',
                     'ambientBlue', ('unused1', null1), 'directionalRed',
                     'directionalGreen', 'directionalBlue', ('unused2', null1),
                     'fogRed', 'fogGreen', 'fogBlue', ('unused3', null1),
                     'fogNear', 'fogFar', 'directionalXY', 'directionalZ',
                     'directionalFade', 'fogClip'),
        MelFidList('XCLR','regions'),
        MelOptUInt8('XCMT', 'music'),
        # CS default for water is -2147483648, but by setting default here
        # to -2147483649, we force the bashed patch to retain the value of
        # the last mod.
        MelOptFloat('XCLW', ('waterHeight', -2147483649)),
        MelFid('XCCM','climate'),
        MelFid('XCWT','water'),
        MelOwnership(),
    )
    __slots__ = melSet.getSlotsUsed()

class MreClas(MelRecord):
    """Class."""
    classType = 'CLAS'

    _flags = Flags(0, Flags.getNames(
        ( 0,'Playable'),
        ( 1,'Guard'),
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
        MelString('DESC','description'),
        MelIcon(),
        MelTruncatedStruct('DATA', '2iI7i2IbB2s', 'primary1', 'primary2',
                           'specialization', 'major1', 'major2', 'major3',
                           'major4', 'major5', 'major6', 'major7',
                           (_flags, 'flags', 0), (aiService, 'services', 0),
                           ('trainSkill', 0), ('trainLevel', 0),
                           ('unused1', null2), old_versions={'2iI7i2I'}),
    )
    __slots__ = melSet.getSlotsUsed()

class MreClmt(MelRecord):
    """Climate."""
    classType = 'CLMT'

    melSet = MelSet(
        MelEdid(),
        MelArray('weather_types',
            MelStruct('WLST','Ii', (FID, 'weather'), 'chance'),
        ),
        MelString('FNAM','sunPath'),
        MelString('GNAM','glarePath'),
        MelModel(),
        MelStruct('TNAM', '6B', 'riseBegin', 'riseEnd', 'setBegin', 'setEnd',
                  'volatility', 'phaseLength'),
    )
    __slots__ = melSet.getSlotsUsed()

class MreClot(MelRecord):
    """Clothing."""
    classType = 'CLOT'

    _flags = MelBipedFlags(0, Flags.getNames((16, 'hideRings'),
                                              (17, 'hideAmulet'),
                                              (22, 'notPlayable')))

    melSet = MelSet(
        MelEdid(),
        MelFull(),
        MelFid('SCRI','script'),
        MelFid('ENAM','enchantment'),
        MelOptUInt16('ANAM', 'enchantPoints'),
        MelUInt32('BMDT', (_flags, 'flags', 0)),
        MelModel('maleBody',0),
        MelModel('maleWorld',2),
        MelIcon('maleIconPath'),
        MelModel('femaleBody',3),
        MelModel('femaleWorld',4),
        MelIco2('femaleIconPath'),
        MelStruct('DATA','If','value','weight'),
    )
    __slots__ = melSet.getSlotsUsed()

class MreCont(MelRecord):
    """Container."""
    classType = 'CONT'

    _flags = Flags(0,Flags.getNames(None,'respawns'))

    melSet = MelSet(
        MelEdid(),
        MelFull(),
        MelModel(),
        MelFid('SCRI','script'),
        MelItems(),
        MelStruct('DATA','=Bf',(_flags,'flags',0),'weight'),
        MelFid('SNAM','soundOpen'),
        MelFid('QNAM','soundClose'),
    )
    __slots__ = melSet.getSlotsUsed()

class MreCrea(MreActor):
    """Creature."""
    classType = 'CREA'

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
        MelFids('SPLO','spells'),
        MelStrings('NIFZ','bodyParts'),
        MelBase('NIFT','nift_p'), # Texture File Hashes
        MelStruct('ACBS','=I3Hh2H',
            (_flags,'flags',0),'baseSpell','fatigue','barterGold',
            ('level',1),'calcMin','calcMax'),
        MelGroups('factions',
            MelStruct('SNAM', 'IB3s', (FID, 'faction', None), 'rank',
                      ('unused1', 'IFZ')),
        ),
        MelFid('INAM','deathItem'),
        MelFid('SCRI','script'),
        MelItems(),
        MelStruct('AIDT','=4BIbB2s',
            ('aggression',5),('confidence',50),('energyLevel',50),
            ('responsibility',50),(aiService,'services',0),'trainSkill',
            'trainLevel',('unused1',null2)),
        MelFids('PKID','aiPackages'),
        MelStrings('KFFZ','animations'),
        MelStruct('DATA','=5BsH2sH8B','creatureType','combatSkill','magic',
                  'stealth','soul',('unused2',null1),'health',
                  ('unused3',null2),'attackDamage','strength','intelligence',
                  'willpower','agility','speed','endurance','personality',
                  'luck'),
        MelUInt8('RNAM', 'attackReach'),
        MelFid('ZNAM','combatStyle'),
        MelFloat('TNAM', 'turningSpeed'),
        MelFloat('BNAM', 'baseScale'),
        MelFloat('WNAM', 'footWeight'),
        MelFid('CSCR','inheritsSoundsFrom'),
        MelString('NAM0','bloodSprayPath'),
        MelString('NAM1','bloodDecalPath'),
        MelGroups('sounds',
            MelUInt32('CSDT', 'type'),
            MelFid('CSDI','sound'),
            MelUInt8('CSDC', 'chance'),
        ),
    )
    __slots__ = melSet.getSlotsUsed()

class MreCsty(MelRecord):
    """Combat Style."""
    classType = 'CSTY'
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
            'CSTD', '2B2s8f2B2s3fB3s2f5B3s2f2B2s7fB3sfI', 'dodgeChance',
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
        MelOptStruct('CSAD', '21f', 'dodgeFMult', 'dodgeFBase', 'encSBase',
                     'encSMult', 'dodgeAtkMult', 'dodgeNAtkMult',
                     'dodgeBAtkMult', 'dodgeBNAtkMult', 'dodgeFAtkMult',
                     'dodgeFNAtkMult', 'blockMult', 'blockBase',
                     'blockAtkMult', 'blockNAtkMult', 'atkMult', 'atkBase',
                     'atkAtkMult', 'atkNAtkMult', 'atkBlockMult', 'pAtkFBase',
                     'pAtkFMult'),
        )
    __slots__ = melSet.getSlotsUsed()

class MreDial(brec.MreDial):
    """Dialogue."""
    melSet = MelSet(
        MelEdid(),
        MelFids('QSTI','quests'),
        MelFids('QSTR','quests2'), # xEdit calls it 'Quests?'
        MelFull(),
        MelUInt8('DATA', 'dialType'),
    )
    __slots__ = melSet.getSlotsUsed()

class MreDoor(MelRecord):
    """Door."""
    classType = 'DOOR'

    _flags = Flags(0, Flags.getNames('oblivionGate', 'automatic', 'hidden',
                                     'minimalUse'))

    melSet = MelSet(
        MelEdid(),
        MelFull(),
        MelModel(),
        MelFid('SCRI','script'),
        MelFid('SNAM','soundOpen'),
        MelFid('ANAM','soundClose'),
        MelFid('BNAM','soundLoop'),
        MelUInt8('FNAM', (_flags, 'flags', 0)),
        MelFids('TNAM','destinations'),
    )
    __slots__ = melSet.getSlotsUsed()

class MreEfsh(MelRecord):
    """Effect Shader."""
    classType = 'EFSH'

    _flags = Flags(0, Flags.getNames(
        ( 0,'noMemShader'),
        ( 3,'noPartShader'),
        ( 4,'edgeInverse'),
        ( 5,'memSkinOnly'),
        ))

    melSet = MelSet(
        MelEdid(),
        MelIcon('fillTexture'),
        MelIco2('particleTexture'),
        MelTruncatedStruct(
            'DATA', 'B3s3I3Bs9f3Bs8f5I19f3Bs3Bs3Bs6f', (_flags, 'flags'),
            ('unused1', null3), 'memSBlend', 'memBlendOp', 'memZFunc',
            'fillRed', 'fillGreen', 'fillBlue', ('unused2', null1), 'fillAIn',
            'fillAFull', 'fillAOut', 'fillAPRatio', 'fillAAmp', 'fillAFreq',
            'fillAnimSpdU', 'fillAnimSpdV', 'edgeOff', 'edgeRed', 'edgeGreen',
            'edgeBlue', ('unused3', null1), 'edgeAIn', 'edgeAFull', 'edgeAOut',
            'edgeAPRatio', 'edgeAAmp', 'edgeAFreq', 'fillAFRatio',
            'edgeAFRatio', 'memDBlend', ('partSBlend', 5), ('partBlendOp', 1),
            ('partZFunc', 4), ('partDBlend', 6), ('partBUp', 0.0),
            ('partBFull', 0.0), ('partBDown', 0.0), ('partBFRatio', 1.0),
            ('partBPRatio', 1.0), ('partLTime', 1.0), ('partLDelta', 0.0),
            ('partNSpd', 0.0), ('partNAcc', 0.0), ('partVel1', 0.0),
            ('partVel2', 0.0), ('partVel3', 0.0), ('partAcc1', 0.0),
            ('partAcc2', 0.0), ('partAcc3', 0.0), ('partKey1', 1.0),
            ('partKey2', 1.0), ('partKey1Time', 0.0), ('partKey2Time', 1.0),
            ('key1Red', 255), ('key1Green', 255), ('key1Blue', 255),
            ('unused4', null1), ('key2Red', 255), ('key2Green', 255),
            ('key2Blue', 255), ('unused5', null1), ('key3Red', 255),
            ('key3Green', 255), ('key3Blue', 255), ('unused6', null1),
            ('key1A', 1.0), ('key2A', 1.0), ('key3A', 1.0), ('key1Time', 0.0),
            ('key2Time', 0.5), ('key3Time', 1.0),
            old_versions={'B3s3I3Bs9f3Bs8fI'}),
    )
    __slots__ = melSet.getSlotsUsed()

class MreEnch(MelRecord,MreHasEffects):
    """Enchantment."""
    classType = 'ENCH'

    _flags = Flags(0, Flags.getNames('noAutoCalc'))

    melSet = MelSet(
        MelEdid(),
        MelFull(), #--At least one mod has this. Odd.
        MelStruct('ENIT', '3IB3s', 'itemType', 'chargeAmount', 'enchantCost',
                  (_flags, 'flags', 0), ('unused1', null3)),
        MelEffects(),
    ).with_distributor(_effects_distributor)
    __slots__ = melSet.getSlotsUsed()

class MreEyes(MelRecord):
    """Eyes."""
    classType = 'EYES'

    _flags = Flags(0, Flags.getNames('playable',))

    melSet = MelSet(
        MelEdid(),
        MelFull(),
        MelIcon(),
        MelUInt8('DATA', (_flags, 'flags')),
    )
    __slots__ = melSet.getSlotsUsed()

class MreFact(MelRecord):
    """Faction."""
    classType = 'FACT'

    _flags = Flags(0, Flags.getNames('hiddenFromPC','evil','specialCombat'))

    melSet = MelSet(
        MelEdid(),
        MelFull(),
        MelGroups('relations',
            MelStruct('XNAM', 'Ii', (FID, 'faction'), 'mod'),
        ),
        MelUInt8('DATA', (_flags, 'flags', 0)),
        MelOptFloat('CNAM', ('crimeGoldMultiplier', None)),
        MelGroups('ranks',
            MelSInt32('RNAM', 'rank'),
            MelString('MNAM','male'),
            MelString('FNAM','female'),
            MelString('INAM','insigniaPath')),
    )
    __slots__ = melSet.getSlotsUsed()

class MreFlor(MelRecord):
    """Flora."""
    classType = 'FLOR'

    melSet = MelSet(
        MelEdid(),
        MelFull(),
        MelModel(),
        MelFid('SCRI','script'),
        MelFid('PFIG','ingredient'),
        MelStruct('PFPC','4B','spring','summer','fall','winter'),
    )
    __slots__ = melSet.getSlotsUsed()

class MreFurn(MelRecord):
    """Furniture."""
    classType = 'FURN'

    _flags = Flags() #--Governs type of furniture and which anims are available
    #--E.g., whether it's a bed, and which of the bed entry/exit animations
    # are available

    melSet = MelSet(
        MelEdid(),
        MelFull(),
        MelModel(),
        MelFid('SCRI','script'),
        MelUInt32('MNAM', (_flags, 'activeMarkers', 0)), # ByteArray in xEdit
    )
    __slots__ = melSet.getSlotsUsed()

class MreGmst(MreGmstBase):
    """Game Setting."""

class MreGras(MelRecord):
    """Grass."""
    classType = 'GRAS'

    _flags = Flags(0,Flags.getNames('vLighting','uScaling','fitSlope'))

    melSet = MelSet(
        MelEdid(),
        MelModel(),
        MelStruct('DATA', '3BsH2sI4fB3s', 'density', 'minSlope', 'maxSlope',
                  ('unused1', null1), 'waterDistance', ('unused2', null2),
                  'waterOp', 'posRange', 'heightRange', 'colorRange',
                  'wavePeriod', (_flags, 'flags'), ('unused3', null3)),
    )
    __slots__ = melSet.getSlotsUsed()

class MreHair(MelRecord):
    """Hair."""
    classType = 'HAIR'

    _flags = Flags(0, Flags.getNames('playable','notMale','notFemale','fixed'))

    melSet = MelSet(
        MelEdid(),
        MelFull(),
        MelModel(),
        MelIcon(),
        MelUInt8('DATA', (_flags, 'flags')),
    )
    __slots__ = melSet.getSlotsUsed()

class MreIdle(MelRecord):
    """Idle Animation."""
    classType = 'IDLE'

    melSet = MelSet(
        MelEdid(),
        MelModel(),
        MelConditions(),
        MelUInt8('ANAM', 'group'),
        MelArray('related_animations',
            MelStruct('DATA', '2I', (FID, 'parent'), (FID, 'prevId')),
        ),
    )
    __slots__ = melSet.getSlotsUsed()

class MreInfo(MelRecord):
    """Dialog Response."""
    classType = 'INFO'

    _flags = Flags(0, Flags.getNames('goodbye', 'random', 'sayOnce',
                                     'runImmediately', 'infoRefusal',
                                     'randomEnd', 'runForRumors'))

    melSet = MelSet(
        MelTruncatedStruct('DATA', '3B', 'dialType', 'nextSpeaker',
                           (_flags, 'flags'), old_versions={'H'}),
        MelFid('QSTI','quests'),
        MelFid('TPIC','topic'),
        MelFid('PNAM','prevInfo'),
        MelFids('NAME','addTopics'),
        MelGroups('responses',
            MelStruct('TRDT', 'Ii4sB3s', 'emotionType', 'emotionValue',
                      ('unused1', null4), 'responseNum', ('unused2', null3)),
            MelString('NAM1','responseText'),
            MelString('NAM2','actorNotes'),
        ),
        MelConditions(),
        MelFids('TCLT','choices'),
        MelFids('TCLF','linksFrom'),
        MelEmbeddedScript(),
    )
    __slots__ = melSet.getSlotsUsed()

class MreIngr(MelRecord,MreHasEffects):
    """Ingredient."""
    classType = 'INGR'

    _flags = Flags(0, Flags.getNames('noAutoCalc','isFood'))

    melSet = MelSet(
        MelEdid(),
        MelFull(),
        MelModel(),
        MelIcon(),
        MelFid('SCRI','script'),
        MelFloat('DATA', 'weight'),
        MelStruct('ENIT','iB3s','value',(_flags,'flags',0),('unused1',null3)),
        MelEffects(),
    ).with_distributor(_effects_distributor)
    __slots__ = melSet.getSlotsUsed()

class MreKeym(MelRecord):
    """Key."""
    classType = 'KEYM'

    melSet = MelSet(
        MelEdid(),
        MelFull(),
        MelModel(),
        MelIcon(),
        MelFid('SCRI','script'),
        MelStruct('DATA','if','value','weight'),
    )
    __slots__ = melSet.getSlotsUsed()

class MreLigh(MelRecord):
    """Light."""
    classType = 'LIGH'

    _flags = Flags(0,  Flags.getNames(
        'dynamic', 'canTake', 'negative', 'flickers', 'unk1', 'offByDefault',
        'flickerSlow', 'pulse', 'pulseSlow', 'spotLight', 'spotShadow'))

    melSet = MelSet(
        MelEdid(),
        MelModel(),
        MelFid('SCRI','script'),
        MelFull(),
        MelIcon(),
        MelTruncatedStruct('DATA', 'iI3BsIffIf', 'duration', 'radius', 'red',
                           'green', 'blue', ('unused1', null1),
                           (_flags, 'flags', 0), 'falloff', 'fov', 'value',
                           'weight', old_versions={'iI3BsI2f'}),
        MelOptFloat('FNAM', ('fade', None)),
        MelFid('SNAM','sound'),
    )
    __slots__ = melSet.getSlotsUsed()

class MreLscr(MelRecord):
    """Load Screen."""
    classType = 'LSCR'

    melSet = MelSet(
        MelEdid(),
        MelIcon(),
        MelString('DESC','text'),
        MelGroups('locations',
            MelStruct('LNAM', '2I2h', (FID, 'direct'), (FID, 'indirect'),
                      'gridy', 'gridx'),
        ),
    )
    __slots__ = melSet.getSlotsUsed()

class MreLtex(MelRecord):
    """Landscape Texture."""
    classType = 'LTEX'

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
        MelOptStruct('HNAM', '3B', (_flags, 'flags'), 'friction',
                     'restitution'), ##: flags are actually an enum....
        MelOptUInt8('SNAM', 'specular'),
        MelFids('GNAM', 'grass'),
    )
    __slots__ = melSet.getSlotsUsed()

class MreLvlc(MreLeveledList):
    """Leveled Creature."""
    classType = 'LVLC'
    __slots__ = []

class MreLvli(MreLeveledList):
    """Leveled Item."""
    classType = 'LVLI'
    __slots__ = []

class MreLvsp(MreLeveledList):
    """Leveled Spell."""
    classType = 'LVSP'
    __slots__ = []

class MreMgef(MelRecord):
    """Magic Effect."""
    classType = 'MGEF'

    _flags = Flags(0, Flags.getNames(
        ( 0,'hostile'),
        ( 1,'recover'),
        ( 2,'detrimental'),
        ( 3,'magnitude'),
        ( 4,'self'),
        ( 5,'touch'),
        ( 6,'target'),
        ( 7,'noDuration'),
        ( 8,'noMagnitude'),
        ( 9,'noArea'),
        (10,'fxPersist'),
        (11,'spellmaking'),
        (12,'enchanting'),
        (13,'noIngredient'),
        (16,'useWeapon'),
        (17,'useArmor'),
        (18,'useCreature'),
        (19,'useSkill'),
        (20,'useAttr'),
        (24,'useAV'),
        (25,'sprayType'),
        (26,'boltType'),
        (27,'noHitEffect'),))

    melSet = MelSet(
        MelEdid(),
        MelFull(),
        MelString('DESC','text'),
        MelIcon(),
        MelModel(),
        MelTruncatedStruct(
            'DATA', 'IfIiiH2sIf6I2f', (_flags, 'flags'), 'baseCost',
            (FID, 'associated'), 'school', 'resistValue', 'numCounters',
            ('unused1', null2), (FID, 'light'), 'projectileSpeed',
            (FID, 'effectShader'), (FID, 'enchantEffect', 0),
            (FID, 'castingSound', 0), (FID, 'boltSound', 0),
            (FID, 'hitSound', 0), (FID, 'areaSound', 0),
            ('cefEnchantment', 0.0), ('cefBarter', 0.0),
            old_versions={'IfIiiH2sIfI'}),
        MelArray('counterEffects',
            MelStruct('ESCE', '4s', 'effect'),
        ),
    )
    __slots__ = melSet.getSlotsUsed()

class MreMisc(MelRecord):
    """Misc. Item."""
    classType = 'MISC'

    melSet = MelSet(
        MelEdid(),
        MelFull(),
        MelModel(),
        MelIcon(),
        MelFid('SCRI','script'),
        MelUnion({
            False: MelStruct('DATA', 'if', 'value', 'weight'),
            True: MelStruct('DATA', '2I', (FID, 'value'), 'weight'),
        }, decider=FlagDecider('flags1', 'borderRegion', 'turnFireOff')),
    )
    __slots__ = melSet.getSlotsUsed()

class MreNpc(MreActor):
    """Non-Player Character."""
    classType = 'NPC_'

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

    class MelNpcData(MelStruct):
        """Convert npc stats into skills, health, attributes."""
        def loadData(self, record, ins, sub_type, size_, readId):
            unpacked = list(ins.unpack('=21BH2s8B', size_, readId))
            recordSetAttr = record.__setattr__
            recordSetAttr('skills',unpacked[:21])
            recordSetAttr('health',unpacked[21])
            recordSetAttr('unused1',unpacked[22])
            recordSetAttr('attributes',unpacked[23:])

        def dumpData(self,record,out):
            recordGetAttr = record.__getattribute__
            values = recordGetAttr('skills') + [recordGetAttr('health')] + [
                recordGetAttr('unused1')] + recordGetAttr('attributes')
            out.packSub(self.subType,'=21BH2s8B',*values)

    melSet = MelSet(
        MelEdid(),
        MelFull(),
        MelModel(),
        MelStruct('ACBS','=I3Hh2H',
            (_flags,'flags',0),'baseSpell','fatigue','barterGold',
            ('level',1),'calcMin','calcMax'),
        MelGroups('factions',
            MelStruct('SNAM', 'IB3s', (FID, 'faction', None), 'rank',
                      ('unused1', 'ODB')),
        ),
        MelFid('INAM','deathItem'),
        MelFid('RNAM','race'),
        MelFids('SPLO','spells'),
        MelFid('SCRI','script'),
        MelItems(),
        MelStruct('AIDT', '=4BIbB2s', ('aggression', 5), ('confidence', 50),
                  ('energyLevel', 50), ('responsibility', 50),
                  (aiService, 'services', 0), 'trainSkill', 'trainLevel',
                  ('unused1', null2)),
        MelFids('PKID','aiPackages'),
        MelStrings('KFFZ','animations'),
        MelFid('CNAM','iclass'),
        MelNpcData('DATA', '', ('skills', [0] * 21), 'health',
                   ('unused2', null2), ('attributes', [0] * 8)),
        MelFid('HNAM','hair'),
        MelOptFloat('LNAM', ('hairLength', None)),
        MelFid('ENAM','eye'), ####fid Array
        MelStruct('HCLR', '3Bs', 'hairRed', 'hairBlue', 'hairGreen',
                  ('unused3', null1)),
        MelFid('ZNAM','combatStyle'),
        MelBase('FGGS','fggs_p'), ####FaceGen Geometry-Symmetric
        MelBase('FGGA','fgga_p'), ####FaceGen Geometry-Asymmetric
        MelBase('FGTS','fgts_p'), ####FaceGen Texture-Symmetric
        MelUInt16('FNAM', 'fnam'), ####Byte Array
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
    classType = 'PACK'

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
        MelTruncatedStruct('PKDT', 'IB3s', (_flags, 'flags'), 'aiType',
                           ('unused1', null3), old_versions={'HBs'}),
        MelUnion({
            0: MelStruct('PLDT', 'iIi', 'locType', (FID, 'locId'),
                         'locRadius'),
            1: MelStruct('PLDT', 'iIi', 'locType', (FID, 'locId'),
                         'locRadius'),
            2: MelStruct('PLDT', 'iIi', 'locType', (FID, 'locId'),
                         'locRadius'),
            3: MelStruct('PLDT', 'iIi', 'locType', (FID, 'locId'),
                         'locRadius'),
            4: MelStruct('PLDT', 'iIi', 'locType', (FID, 'locId'),
                         'locRadius'),
            5: MelStruct('PLDT', 'iIi', 'locType', 'locId', 'locRadius'),
        }, decider=PartialLoadDecider(
            loader=MelSInt32('PLDT', 'locType'),
            decider=AttrValDecider('locType'),
        )),
        MelStruct('PSDT','2bBbi','month','day','date','time','duration'),
        MelUnion({
            0: MelStruct('PTDT', 'iIi', 'targetType', (FID, 'targetId'),
                         'targetCount'),
            1: MelStruct('PTDT', 'iIi', 'targetType', (FID, 'targetId'),
                         'targetCount'),
            2: MelStruct('PTDT', 'iIi', 'targetType', 'targetId',
                         'targetCount'),
        }, decider=PartialLoadDecider(
            loader=MelSInt32('PTDT', 'targetType'),
            decider=AttrValDecider('targetType'),
        )),
        MelConditions(),
    )
    __slots__ = melSet.getSlotsUsed()

#------------------------------------------------------------------------------
## See the comments on MreLand. Commented out for same reasons.
##class MrePgrd(MelRecord):
##    """Path grid structure. Part of cells."""
##    ####Could probably be loaded via MelArray,
##    ####but little point since it is too complex to manipulate
##    classType = 'PGRD'
##    class MelPgrl(MelStructs):
##        """Handler for pathgrid pgrl record."""
##        def loadData(self,record,ins,type,size,readId):
##            if(size % 4 != 0):
##                raise ModError(
##                    ins.inName, u'%s: Expected subrecord of size divisible '
##                                u'by 4, but got %u' % (readId, size_))
##            format = 'I' * (size % 4)
##            attrs = self.attrs
##            target = self.getDefault()
##            record.__getattribute__(self.attr).append(target)
##            target.__slots__ = self.attrs
##            unpacked = ins.unpack(format,size,readId)
##            setter = target.__setattr__
##            map(setter,attrs,(unpacked[0], unpacked[1:]))
##
##        def dumpData(self,record,out):
##            for target in record.__getattribute__(self.attr):
##                out.packSub(self.subType,'I' + 'I'*(len(target.points)), target.reference, target.points)
##
##    melSet = MelSet(
##        MelBase('DATA','data_p'),
##        MelBase('PGRP','points_p'),
##        MelBase('PGAG','pgag_p'),
##        MelBase('PGRR','pgrr_p'),
##        MelBase('PGRI','pgri_p'),
##        MelPgrl('PGRL','','pgrl',(FID,'reference'),'points'),
##    )
##    __slots__ = melSet.getSlotsUsed()

class MreQust(MelRecord):
    """Quest."""
    classType = 'QUST'

    _questFlags = Flags(0, Flags.getNames('startGameEnabled', None,
                                          'repeatedTopics', 'repeatedStages'))
    stageFlags = Flags(0,Flags.getNames('complete'))
    targetFlags = Flags(0,Flags.getNames('ignoresLocks'))

    melSet = MelSet(
        MelEdid(),
        MelFid('SCRI','script'),
        MelFull(),
        MelIcon(),
        MelStruct('DATA','BB',(_questFlags,'questFlags',0),'priority'),
        MelConditions(),
        MelGroups('stages',
            MelSInt16('INDX', 'stage'),
            MelGroups('entries',
                MelUInt8('QSDT', (stageFlags, 'flags')),
                MelConditions(),
                MelString('CNAM','text'),
                MelEmbeddedScript(),
            ),
        ),
        MelGroups('targets',
            MelStruct('QSTA', 'IB3s', (FID, 'targetId'),
                      (targetFlags, 'flags'), ('unused1', null3)),
            MelConditions(),
        ),
    ).with_distributor({
        'EDID|DATA': { # just in case one is missing
            'CTDA': 'conditions',
        },
        'INDX': {
            'CTDA': 'stages',
        },
        'QSTA': {
            'CTDA': 'targets',
        },
    })
    __slots__ = melSet.getSlotsUsed()

class MreRace(MelRecord):
    """Race."""
    classType = 'RACE'

    _flags = Flags(0, Flags.getNames('playable'))

    melSet = MelSet(
        MelEdid(),
        MelFull(),
        MelString('DESC','text'),
        MelFids('SPLO','spells'),
        MelGroups('relations',
            MelStruct('XNAM', 'Ii', (FID, 'faction'), 'mod'),
        ),
        MelStruct('DATA', '14b2s4fI', 'skill1', 'skill1Boost', 'skill2',
                  'skill2Boost', 'skill3', 'skill3Boost', 'skill4',
                  'skill4Boost', 'skill5', 'skill5Boost', 'skill6',
                  'skill6Boost', 'skill7', 'skill7Boost', ('unused1', null2),
                  'maleHeight', 'femaleHeight', 'maleWeight', 'femaleWeight',
                  (_flags, 'flags', 0)),
        MelRaceVoices('VNAM', '2I', (FID, 'maleVoice'), (FID, 'femaleVoice')),
        MelOptStruct('DNAM', '2I', (FID, 'defaultHairMale', 0),
                     (FID, 'defaultHairFemale', 0)),
        # Corresponds to GMST sHairColorNN
        MelUInt8('CNAM', 'defaultHairColor'),
        MelOptFloat('PNAM', 'mainClamp'),
        MelOptFloat('UNAM', 'faceClamp'),
        MelStruct('ATTR', '16B', 'maleStrength', 'maleIntelligence',
                  'maleWillpower', 'maleAgility', 'maleSpeed', 'maleEndurance',
                  'malePersonality', 'maleLuck', 'femaleStrength',
                  'femaleIntelligence', 'femaleWillpower', 'femaleAgility',
                  'femaleSpeed', 'femaleEndurance', 'femalePersonality',
                  'femaleLuck'),
        # Indexed Entries
        MelBase('NAM0', 'face_data_marker', ''),
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
            MelString('MODL', 'modPath'),
            MelFloat('MODB', 'modb'),
            MelBase('MODT', 'modt_p'),
            MelIcon(),
        )),
        MelBase('NAM1', 'body_data_marker', ''),
        MelBase('MNAM', 'male_body_data_marker', ''),
        MelModel('maleTailModel'),
        MelRaceParts({
            0: 'maleUpperBodyPath',
            1: 'maleLowerBodyPath',
            2: 'maleHandPath',
            3: 'maleFootPath',
            4: 'maleTailPath',
        }, group_loaders=lambda _indx: (MelIcon(),)),
        MelBase('FNAM', 'female_body_data_marker', ''),
        MelModel('femaleTailModel'),
        MelRaceParts({
            0: 'femaleUpperBodyPath',
            1: 'femaleLowerBodyPath',
            2: 'femaleHandPath',
            3: 'femaleFootPath',
            4: 'femaleTailPath',
        }, group_loaders=lambda _indx: (MelIcon(),)),
        # Normal Entries
        MelFidList('HNAM','hairs'),
        MelFidList('ENAM','eyes'),
        MelBase('FGGS','fggs_p'), ####FaceGen Geometry-Symmetric
        MelBase('FGGA','fgga_p'), ####FaceGen Geometry-Asymmetric
        MelBase('FGTS','fgts_p'), ####FaceGen Texture-Symmetric
        MelStruct('SNAM','2s',('snam_p',null2)),
    ).with_distributor({
        'NAM0': {
            'INDX|MODL|MODB|MODT|ICON': 'head',
        },
        'MNAM': {
            'MODL|MODB|MODT': 'maleTailModel',
            'INDX|ICON': 'maleUpperBodyPath',
        },
        'FNAM': {
            'MODL|MODB|MODT': 'femaleTailModel',
            'INDX|ICON': 'femaleUpperBodyPath',
        },
    })
    __slots__ = melSet.getSlotsUsed()

class MreRefr(MelRecord):
    """Placed Object."""
    classType = 'REFR'

    _marker_flags = Flags(0, Flags.getNames(
        'visible',
        'can_travel_to',
    ))
    _parentFlags = Flags(0, Flags.getNames('oppositeParent'))
    _actFlags = Flags(0, Flags.getNames('useDefault', 'activate', 'open',
                                         'openByDefault'))
    _lockFlags = Flags(0, Flags.getNames(None, None, 'leveledLock'))

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
        MelFid('NAME','base'),
        MelOptStruct('XTEL', 'I6f', (FID, 'destinationFid'), 'destinationPosX',
                     'destinationPosY', 'destinationPosZ', 'destinationRotX',
                     'destinationRotY', 'destinationRotZ'),
        MelRefrXloc('XLOC', 'B3sI4sB3s', 'lockLevel', ('unused1', null3),
                    (FID, 'lockKey'), ('unused2', null4),
                    (_lockFlags, 'lockFlags'), ('unused3', null3),
                    is_optional=True, old_versions={'B3sIB3s'}),
        MelOwnership(),
        MelOptStruct('XESP','IB3s',(FID,'parent'),
                     (_parentFlags,'parentFlags'),('unused4',null3)),
        MelFid('XTRG','targetId'),
        MelBase('XSED','seed_p'),
        ####SpeedTree Seed, if it's a single byte then it's an offset into
        # the list of seed values in the TREE record
        ####if it's 4 byte it's the seed value directly.
        MelOptStruct('XLOD', '3f', ('lod1', None), ('lod2', None),
                     ('lod3', None)),
        MelOptFloat('XCHG', ('charge', None)),
        MelOptSInt32('XHLT', ('health', None)),
        # both unused
        MelNull('XPCI'),
        MelNull('FULL'),
        MelOptSInt32('XLCM', ('levelMod', None)),
        MelFid('XRTM','xrtm'),
        MelOptUInt32('XACT', (_actFlags, 'actFlags', 0)),
        MelOptSInt32('XCNT', 'count'),
        MelGroup('map_marker',
            MelBase('XMRK', 'marker_data'),
            MelOptUInt8('FNAM', (_marker_flags, 'marker_flags')),
            MelFull(),
            MelOptStruct('TNAM', 'Bs', 'marker_type', 'unused1'),
        ),
        MelBase('ONAM','onam_p'),
        MelBase('XRGD','xrgd_p'),
        MelOptFloat('XSCL', ('scale', 1.0)),
        MelOptUInt8('XSOL', ('soul', None)),
        MelOptStruct('DATA', '=6f', ('posX', None), ('posY', None),
                     ('posZ', None), ('rotX', None), ('rotY', None),
                     ('rotZ', None)),
    )
    __slots__ = melSet.getSlotsUsed()

class MreRegn(MelRecord):
    """Region."""
    classType = 'REGN'

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
        MelStruct('RCLR','3Bs','mapRed','mapBlue','mapGreen',('unused1',null1)),
        MelFid('WNAM','worldspace'),
        MelGroups('areas',
            MelUInt32('RPLI', 'edgeFalloff'),
            MelArray('points',
                MelStruct('RPLD', '2f', 'posX', 'posY'),
            ),
        ),
        MelGroups('entries',
            MelStruct('RDAT', 'I2B2s', 'entryType', (rdatFlags, 'flags'),
                    'priority', ('unused1', null2)),
            MelRegnEntrySubrecord(2, MelArray('objects',
                MelStruct(
                    'RDOT', 'IH2sf4B2H5f3H2s4s', (FID, 'objectId'),
                    'parentIndex', ('unk1', null2), 'density', 'clustering',
                    'minSlope', 'maxSlope', (obflags, 'flags'),
                    'radiusWRTParent', 'radius', 'minHeight', 'maxHeight',
                    'sink', 'sinkVar', 'sizeVar', 'angleVarX', 'angleVarY',
                    'angleVarZ', ('unk2', null2), ('unk3', null4)),
            )),
            ##: Was disabled previously - not in xEdit either...
            # MelRegnEntrySubrecord(5, MelIcon()),
            MelRegnEntrySubrecord(4, MelString('RDMP', 'mapName')),
            MelRegnEntrySubrecord(6, MelArray('grasses',
                MelStruct('RDGS', 'I4s', (FID, 'grass'), ('unknown', null4)),
            )),
            MelRegnEntrySubrecord(7, MelOptUInt32('RDMD', 'musicType')),
            MelRegnEntrySubrecord(7, MelArray('sounds',
                MelStruct('RDSD', '3I', (FID, 'sound'), (sdflags, 'flags'),
                          'chance'),
            )),
            MelRegnEntrySubrecord(3, MelArray('weatherTypes',
                MelStruct('RDWT', '2I', (FID, 'weather'), 'chance')
            )),
        ),
    )
    __slots__ = melSet.getSlotsUsed()

class MreRoad(MelRecord):
    """Road. Part of large worldspaces."""
    ####Could probably be loaded via MelArray,
    ####but little point since it is too complex to manipulate
    classType = 'ROAD'

    melSet = MelSet(
        MelBase('PGRP','points_p'),
        MelBase('PGRR','connections_p'),
    )
    __slots__ = melSet.getSlotsUsed()

class MreSbsp(MelRecord):
    """Subspace."""
    classType = 'SBSP'

    melSet = MelSet(
        MelEdid(),
        MelStruct('DNAM','3f','sizeX','sizeY','sizeZ'),
    )
    __slots__ = melSet.getSlotsUsed()

class MreScpt(MelRecord):
    """Script."""
    classType = 'SCPT'

    melSet = MelSet(
        MelEdid(),
        MelEmbeddedScript(with_script_vars=True),
    )
    __slots__ = melSet.getSlotsUsed()

class MreSgst(MelRecord,MreHasEffects):
    """Sigil Stone."""
    classType = 'SGST'

    melSet = MelSet(
        MelEdid(),
        MelFull(),
        MelModel(),
        MelIcon(),
        MelFid('SCRI','script'),
        MelEffects(),
        MelStruct('DATA','=BIf','uses','value','weight'),
    ).with_distributor(_effects_distributor)
    __slots__ = melSet.getSlotsUsed()

class MreSkil(MelRecord):
    """Skill."""
    classType = 'SKIL'

    melSet = MelSet(
        MelEdid(),
        MelSInt32('INDX', 'skill'),
        MelString('DESC','description'),
        MelIcon(),
        MelStruct('DATA','2iI2f','action','attribute','specialization',('use0',1.0),'use1'),
        MelString('ANAM','apprentice'),
        MelString('JNAM','journeyman'),
        MelString('ENAM','expert'),
        MelString('MNAM','master'),
    )
    __slots__ = melSet.getSlotsUsed()

class MreSlgm(MelRecord):
    """Soul Gem."""
    classType = 'SLGM'

    melSet = MelSet(
        MelEdid(),
        MelFull(),
        MelModel(),
        MelIcon(),
        MelFid('SCRI','script'),
        MelStruct('DATA','If','value','weight'),
        MelUInt8('SOUL', ('soul', 0)),
        MelUInt8('SLCP', ('capacity', 1)),
    )
    __slots__ = melSet.getSlotsUsed()

class MreSoun(MelRecord):
    """Sound."""
    classType = 'SOUN'

    _flags = Flags(0, Flags.getNames('randomFrequencyShift', 'playAtRandom',
        'environmentIgnored', 'randomLocation', 'loop','menuSound', '2d', '360LFE'))

    class MelSounSndd(MelStruct):
        """SNDD is an older version of SNDX. Allow it to read in, but not set defaults or write."""
        def loadData(self, record, ins, sub_type, size_, readId):
            MelStruct.loadData(self, record, ins, sub_type, size_, readId)
            record.staticAtten = 0
            record.stopTime = 0
            record.startTime = 0
        def getSlotsUsed(self): return ()
        def setDefault(self,record): return
        def dumpData(self,record,out): return

    melSet = MelSet(
        MelEdid(),
        MelString('FNAM','soundFile'),
        MelSounSndd('SNDD', '=2BbsH2s', 'minDistance', 'maxDistance',
                    'freqAdjustment', ('unused1', null1), (_flags, 'flags'),
                    ('unused2', null2)),
        MelOptStruct('SNDX', '=2BbsH2sH2B', ('minDistance', None),
                     ('maxDistance', None), ('freqAdjustment', None),
                     ('unused1', null1), (_flags, 'flags', None),
                     ('unused2', null2), ('staticAtten', None),
                     ('stopTime', None), ('startTime', None), )
    )
    __slots__ = melSet.getSlotsUsed()

class MreSpel(MelRecord,MreHasEffects):
    """Spell."""
    classType = 'SPEL'

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
        MelFull(),
        MelStruct('SPIT', '3IB3s', 'spellType', 'cost', 'level',
                  (_SpellFlags, 'flags', 0), ('unused1', null3)),
        MelEffects(),
    ).with_distributor(_effects_distributor)
    __slots__ = melSet.getSlotsUsed()

class MreStat(MelRecord):
    """Static."""
    classType = 'STAT'

    melSet = MelSet(
        MelEdid(),
        MelModel(),
    )
    __slots__ = melSet.getSlotsUsed()

class MreTree(MelRecord):
    """Tree."""
    classType = 'TREE'

    melSet = MelSet(
        MelEdid(),
        MelModel(),
        MelIcon(),
        MelArray('speedTree',
            MelUInt32('SNAM', 'seed'),
        ),
        MelStruct('CNAM','5fi2f', 'curvature','minAngle','maxAngle',
                  'branchDim','leafDim','shadowRadius','rockSpeed',
                  'rustleSpeed'),
        MelStruct('BNAM','2f','widthBill','heightBill'),
    )
    __slots__ = melSet.getSlotsUsed()

class MreWatr(MelRecord):
    """Water."""
    classType = 'WATR'

    _flags = Flags(0, Flags.getNames('causesDmg','reflective'))

    class MelWatrData(MelTruncatedStruct):
        """Chop off two junk bytes at the end of each older format."""
        def _pre_process_unpacked(self, unpacked_val):
            if len(unpacked_val) != 36:
                unpacked_val = unpacked_val[:-1]
            return MelTruncatedStruct._pre_process_unpacked(self, unpacked_val)

    melSet = MelSet(
        MelEdid(),
        MelString('TNAM','texture'),
        MelUInt8('ANAM', 'opacity'),
        MelUInt8('FNAM', (_flags, 'flags', 0)),
        MelString('MNAM','material'),
        MelFid('SNAM','sound'),
        MelWatrData(
            'DATA', '11f3Bs3Bs3BsB3s10fH', ('windVelocity', 0.100),
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
        MelFidList('GNAM','relatedWaters'),
    )
    __slots__ = melSet.getSlotsUsed()

class MreWeap(MelRecord):
    """Weapon."""
    classType = 'WEAP'

    _flags = Flags(0, Flags.getNames('notNormalWeapon'))

    melSet = MelSet(
        MelEdid(),
        MelFull(),
        MelModel(),
        MelIcon(),
        MelFid('SCRI','script'),
        MelFid('ENAM','enchantment'),
        MelOptUInt16('ANAM', 'enchantPoints'),
        MelStruct('DATA','I2f3IfH','weaponType','speed','reach',(_flags,'flags',0),
            'value','health','weight','damage'),
    )
    __slots__ = melSet.getSlotsUsed()

class MreWrld(MelRecord):
    """Worldspace."""
    classType = 'WRLD'

    _flags = Flags(0, Flags.getNames('smallWorld','noFastTravel','oblivionWorldspace',None,'noLODWater'))

    melSet = MelSet(
        MelEdid(),
        MelFull(),
        MelFid('WNAM','parent'),
        MelFid('CNAM','climate'),
        MelFid('NAM2','water'),
        MelIcon('mapPath'),
        MelOptStruct('MNAM','2i4h',('dimX',None),('dimY',None),('NWCellX',None),('NWCellY',None),('SECellX',None),('SECellY',None)),
        MelUInt8('DATA', (_flags, 'flags', 0)),
        MelStruct('NAM0', '2f', 'object_bounds_min_x', 'object_bounds_min_y'),
        MelStruct('NAM9', '2f', 'object_bounds_max_x', 'object_bounds_max_y'),
        MelOptUInt32('SNAM', 'sound'),
        MelBase('OFST','ofst_p'),
    )
    __slots__ = melSet.getSlotsUsed()

class MreWthr(MelRecord):
    """Weather."""
    classType = 'WTHR'

    melSet = MelSet(
        MelEdid(),
        MelString('CNAM','lowerLayer'),
        MelString('DNAM','upperLayer'),
        MelModel(),
        MelArray('colors',
            MelWthrColors('NAM0'),
        ),
        MelStruct('FNAM','4f','fogDayNear','fogDayFar','fogNightNear','fogNightFar'),
        MelStruct('HNAM','14f',
            'eyeAdaptSpeed', 'blurRadius', 'blurPasses', 'emissiveMult',
            'targetLum', 'upperLumClamp', 'brightScale', 'brightClamp',
            'lumRampNoTex', 'lumRampMin', 'lumRampMax', 'sunlightDimmer',
            'grassDimmer', 'treeDimmer'),
        MelStruct('DATA','15B',
            'windSpeed','lowerCloudSpeed','upperCloudSpeed','transDelta',
            'sunGlare','sunDamage','rainFadeIn','rainFadeOut','boltFadeIn',
            'boltFadeOut','boltFrequency','weatherType','boltRed','boltBlue','boltGreen'),
        MelGroups('sounds',
            MelStruct('SNAM', '2I', (FID, 'sound'), 'type'),
        ),
    )
    __slots__ = melSet.getSlotsUsed()
