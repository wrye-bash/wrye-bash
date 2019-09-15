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
import struct
from .constants import allConditions, fid1Conditions, fid2Conditions
from ... import brec
from ...bass import null1, null2, null3, null4
from ...bolt import Flags, DataDict, struct_pack
from ...brec import MelRecord, MelStructs, MelObject, MelGroups, MelStruct, \
    FID, MelGroup, MelString, MreLeveledListBase, MelSet, MelFid, MelNull, \
    MelOptStruct, MelFids, MreHeaderBase, MelBase, MelUnicode, MelXpci, \
    MelFull0, MelFidList, MelStructA, MelStrings, MreRecord, MreGmstBase, \
    MelTuple, MreHasEffects
from ...exception import BoltError, ModError, ModSizeError, StateError
# Set brec MelModel to the one for Oblivion
if brec.MelModel is None:

    class _MelModel(brec.MelGroup):
        """Represents a model record."""
        typeSets = (
            ('MODL','MODB','MODT'),
            ('MOD2','MO2B','MO2T'),
            ('MOD3','MO3B','MO3T'),
            ('MOD4','MO4B','MO4T'),)

        def __init__(self,attr='model',index=0):
            """Initialize. Index is 0,2,3,4 for corresponding type id."""
            types = self.__class__.typeSets[(0,index-1)[index>0]]
            MelGroup.__init__(self,attr,
                MelString(types[0],'modPath'),
                MelStruct(types[1],'f','modb'), ### Bound Radius, Float
                MelBase(types[2],'modt_p'),) ###Texture Files Hashes, Byte Array

        def debug(self,on=True):
            """Sets debug flag on self."""
            for element in self.elements[:2]: element.debug(on)
            return self

    brec.MelModel = _MelModel

from ...brec import MelModel

#------------------------------------------------------------------------------
# Record Elements    ----------------------------------------------------------
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

class MelBipedFlags(Flags):
    """Biped flags element. Includes biped flag set by default."""
    mask = 0xFFFF
    def __init__(self,default=0L,newNames=None):
        names = Flags.getNames('head', 'hair', 'upperBody', 'lowerBody',
                               'hand', 'foot', 'rightRing', 'leftRing',
                               'amulet', 'weapon', 'backWeapon', 'sideWeapon',
                               'quiver', 'shield', 'torch', 'tail')
        if newNames: names.update(newNames)
        Flags.__init__(self,default,names)

class MelConditions(MelStructs):
    """Represents a set of quest/dialog conditions. Difficulty is that FID
    state of parameters depends on function index."""
    def __init__(self):
        """Initialize."""
        MelStructs.__init__(self,'CTDA','B3sfIii4s','conditions',
            'operFlag',('unused1',null3),'compValue','ifunc','param1','param2',
            ('unused2',null4))

    def getLoaders(self,loaders):
        """Adds self as loader for type."""
        loaders[self.subType] = self
        loaders['CTDT'] = self #--Older CTDT type for ai package records.

    def getDefault(self):
        """Returns a default copy of object."""
        target = MelStructs.getDefault(self)
        target.form12 = 'ii'
        return target

    def hasFids(self,formElements):
        """Include self if has fids."""
        formElements.add(self)

    def loadData(self, record, ins, sub_type, size_, readId):
        """Reads data from ins into record attribute."""
        if sub_type == 'CTDA' and size_ != 24:
            raise ModSizeError(ins.inName, readId, 24, size_, True)
        if sub_type == 'CTDT' and size_ != 20:
            raise ModSizeError(ins.inName, readId, 20, size_, True)
        target = MelObject()
        record.conditions.append(target)
        target.__slots__ = self.attrs
        unpacked1 = ins.unpack('B3sfI',12,readId)
        (target.operFlag,target.unused1,target.compValue,ifunc) = unpacked1
        #--Get parameters
        if ifunc not in allConditions:
            raise BoltError(u'Unknown condition function: %d' % ifunc)
        form1 = 'iI'[ifunc in fid1Conditions]
        form2 = 'iI'[ifunc in fid2Conditions]
        form12 = form1+form2
        unpacked2 = ins.unpack(form12,8,readId)
        (target.param1,target.param2) = unpacked2
        if size_ == 24:
            target.unused2 = ins.read(4)
        else:
            target.unused2 = null4
        (target.ifunc,target.form12) = (ifunc,form12)
        if self._debug:
            unpacked = unpacked1+unpacked2
            print u' ',zip(self.attrs,unpacked)
            if len(unpacked) != len(self.attrs):
                print u' ',unpacked

    def dumpData(self,record,out):
        """Dumps data from record to outstream."""
        for target in record.conditions:
            ##format = 'B3sfI'+target.form12+'4s'
            out.packSub('CTDA','B3sfI'+target.form12+'4s',
                target.operFlag, target.unused1, target.compValue,
                target.ifunc, target.param1, target.param2, target.unused2)

    def mapFids(self,record,function,save=False):
        """Applies function to fids. If save is true, then fid is set
        to result of function."""
        for target in record.conditions:
            form12 = target.form12
            if form12[0] == 'I':
                result = function(target.param1)
                if save: target.param1 = result
            if form12[1] == 'I':
                result = function(target.param2)
                if save: target.param2 = result

class MelEffects(MelGroups):
    """Represents ingredient/potion/enchantment/spell effects."""

    #--Class Data
    seFlags = Flags(0x0L,Flags.getNames('hostile'))
    class MelEffectsScit(MelStruct):
        """Subclass to support alternate format."""
        def __init__(self):
            MelStruct.__init__(self, 'SCIT', 'II4sB3s', (FID, 'script', None),
                               ('school', 0), ('visual', '\x00\x00\x00\x00'),
                               (MelEffects.seFlags, 'flags', 0x0L),
                               ('unused1', null3))
        def loadData(self, record, ins, sub_type, size_, readId):
            #--Alternate formats
            if size_ == 16:
                attrs,actions = self.attrs,self.actions
                unpacked = ins.unpack(self.format, size_, readId)
            elif size_ == 12:
                attrs,actions = ('script','school','visual'),(0,0,0)
                unpacked = ins.unpack('II4s', size_, readId)
                record.unused1 = null3
            else: #--size == 4
                # --The script fid for MS40TestSpell doesn't point to a
                # valid script.
                #--But it's not used, so... Not a problem! It's also t
                record.unused1 = null3
                attrs,actions = ('script',),(0,)
                unpacked = ins.unpack('I', size_, readId)
                if unpacked[0] & 0xFF000000L:
                    unpacked = (0L,) #--Discard bogus MS40TestSpell fid
            #--Unpack
            record.__slots__ = self.attrs
            setter = record.__setattr__
            for attr,value,action in zip(attrs,unpacked,actions):
                if callable(action): value = action(value)
                setter(attr,value)
            if self._debug: print u' ',unpacked

    #--Instance methods
    def __init__(self,attr='effects'):
        """Initialize elements."""
        MelGroups.__init__(self,attr,
            MelStruct('EFID','4s',('name','REHE')),
            MelStruct('EFIT', '4s4Ii', ('name', 'REHE'), 'magnitude', 'area',
                      'duration', 'recipient', 'actorValue'),
            MelGroup('scriptEffect',
                MelEffects.MelEffectsScit(),
                MelString('FULL','full'),
                ),
            )

class MreLeveledList(MreLeveledListBase):
    """Leveled item/creature/spell list.."""
    copyAttrs = ('script','template','chanceNone',)

    #--Special load classes
    class MelLevListLvld(MelStruct):
        """Subclass to support alternate format."""
        def loadData(self, record, ins, sub_type, size_, readId):
            MelStruct.loadData(self, record, ins, sub_type, size_, readId)
            if record.chanceNone > 127:
                record.flags.calcFromAllLevels = True
                record.chanceNone &= 127

    class MelLevListLvlo(MelStructs):
        """Subclass to support alternate format."""
        def loadData(self, record, ins, sub_type, size_, readId):
            target = self.getDefault()
            record.__getattribute__(self.attr).append(target)
            target.__slots__ = self.attrs
            format, attrs = \
                ((self.format, self.attrs), ('iI', ('level', 'listId'),))[
                    size_ == 8]  # ###might be h2sI
            unpacked = ins.unpack(format, size_, readId)
            setter = target.__setattr__
            map(setter,attrs,unpacked)
    #--Element Set
    melSet = MelSet(
        MelString('EDID','eid'),
        MelLevListLvld('LVLD','B','chanceNone'),
        MelStruct('LVLF','B',(MreLeveledListBase._flags,'flags',0L)),
        MelFid('SCRI','script'),
        MelFid('TNAM','template'),
        MelLevListLvlo('LVLO','h2sIh2s','entries','level',('unused1',null2),
                       (FID,'listId',None),('count',1),('unused2',null2)),
        MelNull('DATA'),
        )
    __slots__ = melSet.getSlotsUsed()

class MelOwnership(MelGroup):
    """Handles XOWN, XRNK, and XGLB for cells and cell children."""

    def __init__(self,attr='ownership'):
        """Initialize."""
        MelGroup.__init__(self,attr,
            MelFid('XOWN','owner'),
            MelOptStruct('XRNK','i',('rank',None)),
            MelFid('XGLB','global'),
        )

    def dumpData(self,record,out):
        """Dumps data from record to outstream."""
        if record.ownership and record.ownership.owner:
            MelGroup.dumpData(self,record,out)

class MelScrxen(MelFids):
    """Handles mixed sets of SCRO and SCRV for scripts, quests, etc."""

    def getLoaders(self,loaders):
        loaders['SCRV'] = self
        loaders['SCRO'] = self

    def loadData(self, record, ins, sub_type, size_, readId):
        isFid = (sub_type == 'SCRO')
        if isFid: value = ins.unpackRef()
        else: value, = ins.unpack('I',4,readId)
        record.__getattribute__(self.attr).append((isFid,value))

    def dumpData(self,record,out):
        for isFid,value in record.__getattribute__(self.attr):
            if isFid: out.packRef('SCRO',value)
            else: out.packSub('SCRV','I',value)

    def mapFids(self,record,function,save=False):
        scrxen = record.__getattribute__(self.attr)
        for index,(isFid,value) in enumerate(scrxen):
            if isFid:
                result = function(value)
                if save: scrxen[index] = (isFid,result)

#------------------------------------------------------------------------------
# Oblivion Records ------------------------------------------------------------
#------------------------------------------------------------------------------
class MreHeader(MreHeaderBase):
    """TES4 Record.  File header."""
    classType = 'TES4'

    #--Data elements
    melSet = MelSet(MelStruct('HEDR', 'f2I', ('version', 0.8), 'numRecords',
                              ('nextObject', 0xCE6)),
        MelBase('OFST','ofst_p',),  #--Obsolete?
        MelBase('DELE','dele_p',),  #--Obsolete?
        MelUnicode('CNAM','author',u'',512),
        MelUnicode('SNAM','description',u'',512),
        MreHeaderBase.MelMasterName('MAST','masters'),
        MelNull('DATA'),
        )
    __slots__ = melSet.getSlotsUsed()

class MreAchr(MelRecord): # Placed NPC
    classType = 'ACHR'
    _flags = Flags(0L,Flags.getNames('oppositeParent'))
    melSet=MelSet(
        MelString('EDID','eid'),
        MelFid('NAME','base'),
        MelXpci('XPCI'),
        MelOptStruct('XLOD', '3f', ('lod1', None), ('lod2', None),
                     ('lod3', None)), # ###Distant LOD Data, unknown
        MelOptStruct('XESP', 'IB3s', (FID, 'parent'), (_flags, 'parentFlags'),
                     ('unused1', null3)),
        MelFid('XMRC','merchantContainer'),
        MelFid('XHRS','horse'),
        MelBase('XRGD','xrgd_p'), ###Ragdoll Data, ByteArray
        MelOptStruct('XSCL','f',('scale',1.0)),
        MelOptStruct('DATA', '=6f', ('posX', None), ('posY', None),
                     ('posZ', None), ('rotX', None), ('rotY', None),
                     ('rotZ', None)),
    )
    __slots__ = melSet.getSlotsUsed()

class MreAcre(MelRecord): # Placed Creature
    classType = 'ACRE'
    _flags = Flags(0L,Flags.getNames('oppositeParent'))
    melSet=MelSet(
        MelString('EDID','eid'),
        MelFid('NAME','base'),
        MelOwnership(),
        MelOptStruct('XLOD', '3f', ('lod1', None), ('lod2', None),
                     ('lod3', None)), # ###Distant LOD Data, unknown
        MelOptStruct('XESP', 'IB3s', (FID, 'parent'), (_flags, 'parentFlags'),
                     ('unused1', null3)),
        MelBase('XRGD','xrgd_p'), ###Ragdoll Data, ByteArray
        MelOptStruct('XSCL','f',('scale',1.0)),
        MelOptStruct('DATA', '=6f', ('posX', None), ('posY', None),
                     ('posZ', None), ('rotX', None), ('rotY', None),
                     ('rotZ', None)),
    )
    __slots__ = melSet.getSlotsUsed()

class MreActi(MelRecord):
    """Activator record."""
    classType = 'ACTI'
    melSet = MelSet(
        MelString('EDID','eid'),
        MelString('FULL','full'),
        MelModel(),
        MelFid('SCRI','script'),
        MelFid('SNAM','sound'),
        )
    __slots__ = melSet.getSlotsUsed()

class MreAlch(MelRecord,MreHasEffects):
    """ALCH (potion) record."""
    classType = 'ALCH'
    _flags = Flags(0L,Flags.getNames('autoCalc','isFood'))
    melSet = MelSet(
        MelString('EDID','eid'),
        MelFull0(),
        MelModel(),
        MelString('ICON','iconPath'),
        MelFid('SCRI','script'),
        MelStruct('DATA','f','weight'),
        MelStruct('ENIT','iB3s','value',(_flags,'flags',0L),('unused1',null3)),
        MelEffects(),
        )
    __slots__ = melSet.getSlotsUsed()

class MreAmmo(MelRecord):
    """Ammo (arrow) record."""
    classType = 'AMMO'
    _flags = Flags(0L,Flags.getNames('notNormalWeapon'))
    melSet = MelSet(
        MelString('EDID','eid'),
        MelString('FULL','full'),
        MelModel(),
        MelString('ICON','iconPath'),
        MelFid('ENAM','enchantment'),
        MelOptStruct('ANAM','H','enchantPoints'),
        MelStruct('DATA', 'fB3sIfH', 'speed', (_flags, 'flags', 0L),
                  ('unused1', null3), 'value', 'weight', 'damage'),
        )
    __slots__ = melSet.getSlotsUsed()

class MreAnio(MelRecord):
    """Animation object record."""
    classType = 'ANIO'
    melSet = MelSet(
        MelString('EDID','eid'),
        MelModel(),
        MelFid('DATA','animationId'),
        )
    __slots__ = melSet.getSlotsUsed()

class MreAppa(MelRecord):
    """Alchemical apparatus record."""
    classType = 'APPA'
    melSet = MelSet(
        MelString('EDID','eid'),
        MelString('FULL','full'),
        MelModel(),
        MelString('ICON','iconPath'),
        MelFid('SCRI','script'),
        MelStruct('DATA', '=BIff', ('apparatus', 0), ('value', 25),
                  ('weight', 1), ('quality', 10)),
        )
    __slots__ = melSet.getSlotsUsed()

class MreArmo(MelRecord):
    """Armor record."""
    classType = 'ARMO'
    _flags = MelBipedFlags(0L, Flags.getNames((16, 'hideRings'),
                                              (17, 'hideAmulet'),
                                              (22, 'notPlayable'),
                                              (23, 'heavyArmor')))
    melSet = MelSet(
        MelString('EDID','eid'),
        MelString('FULL','full'),
        MelFid('SCRI','script'),
        MelFid('ENAM','enchantment'),
        MelOptStruct('ANAM','H','enchantPoints'),
        MelStruct('BMDT','I',(_flags,'flags',0L)),
        MelModel('maleBody',0),
        MelModel('maleWorld',2),
        MelString('ICON','maleIconPath'),
        MelModel('femaleBody',3),
        MelModel('femaleWorld',4),
        MelString('ICO2','femaleIconPath'),
        MelStruct('DATA','=HIIf','strength','value','health','weight'),
        )
    __slots__ = melSet.getSlotsUsed()

class MreBook(MelRecord):
    """BOOK record."""
    classType = 'BOOK'
    _flags = Flags(0,Flags.getNames('isScroll','isFixed'))
    melSet = MelSet(
        MelString('EDID','eid'),
        MelString('FULL','full'),
        MelModel(),
        MelString('ICON','iconPath'),
        MelString('DESC','text'),
        MelFid('SCRI','script'),
        MelFid('ENAM','enchantment'),
        MelOptStruct('ANAM','H','enchantPoints'),
        MelStruct('DATA', '=BbIf', (_flags, 'flags', 0L), ('teaches', -1),
                  'value', 'weight'),
        )
    __slots__ = melSet.getSlotsUsed() + ['modb']

class MreBsgn(MelRecord):
    """Birthsign record."""
    classType = 'BSGN'
    melSet = MelSet(
        MelString('EDID','eid'),
        MelString('FULL','full'),
        MelString('ICON','iconPath'),
        MelString('DESC','text'),
        MelFids('SPLO','spells'),
        )
    __slots__ = melSet.getSlotsUsed()

class MreCell(MelRecord):
    """Cell record."""
    classType = 'CELL'
    cellFlags = Flags(0L,Flags.getNames(
        (0,'isInterior'),
        (1,'hasWater'),
        (2,'invertFastTravel'),
        (3,'forceHideLand'),
        (5,'publicPlace'),
        (6,'handChanged'),
        (7,'behaveLikeExterior')
        ))
    class MelCoordinates(MelOptStruct):
        def dumpData(self,record,out):
            if not record.flags.isInterior:
                MelOptStruct.dumpData(self,record,out)

    melSet = MelSet(
        MelString('EDID','eid'),
        MelString('FULL','full'),
        MelStruct('DATA','B',(cellFlags,'flags',0L)),
        MelCoordinates('XCLC','ii',('posX',None),('posY',None)),
        MelOptStruct('XCLL', '=3Bs3Bs3Bs2f2i2f', 'ambientRed', 'ambientGreen',
                     'ambientBlue', ('unused1', null1), 'directionalRed',
                     'directionalGreen', 'directionalBlue', ('unused2', null1),
                     'fogRed', 'fogGreen', 'fogBlue', ('unused3', null1),
                     'fogNear', 'fogFar', 'directionalXY', 'directionalZ',
                     'directionalFade', 'fogClip'),
        MelFidList('XCLR','regions'),
        MelOptStruct('XCMT','B','music'),
        #--CS default for water is -2147483648, but by setting default here
        # to -2147483649, we force the bashed patch to retain the value of
        # the last mod.
        MelOptStruct('XCLW','f',('waterHeight',-2147483649)),
        MelFid('XCCM','climate'),
        MelFid('XCWT','water'),
        MelOwnership(),
        )
    __slots__ = melSet.getSlotsUsed()

class MreClas(MelRecord):
    """Class record."""
    classType = 'CLAS'
    _flags = Flags(0L,Flags.getNames(
        ( 0,'Playable'),
        ( 1,'Guard'),
        ))
    aiService = Flags(0L,Flags.getNames(
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
    class MelClasData(MelStruct):
        """Handle older truncated DATA for CLAS subrecords."""
        def loadData(self, record, ins, sub_type, size_, readId):
            if size_ == 52:
                MelStruct.loadData(self, record, ins, sub_type, size_, readId)
                return
            #--Else 42 byte record (skips trainSkill, trainLevel,unused1...
            unpacked = ins.unpack('2iI7i2I', size_, readId)
            unpacked += self.defaults[len(unpacked):]
            setter = record.__setattr__
            for attr,value,action in zip(self.attrs,unpacked,self.actions):
                if callable(action): value = action(value)
                setter(attr,value)
            if self._debug: print unpacked, record.flags.getTrueAttrs()
    melSet = MelSet(
        MelString('EDID','eid'),
        MelString('FULL','full'),
        MelString('DESC','description'),
        MelString('ICON','iconPath'),
        MelClasData('DATA', '2iI7i2IbB2s', 'primary1', 'primary2',
                    'specialization', 'major1', 'major2', 'major3', 'major4',
                    'major5', 'major6', 'major7', (_flags, 'flags', 0L),
                    (aiService, 'services', 0L), ('trainSkill', 0),
                    ('trainLevel', 0), ('unused1', null2)),
        )
    __slots__ = melSet.getSlotsUsed()

class MreClmt(MelRecord):
    """Climate record."""
    classType = 'CLMT'
    melSet = MelSet(
        MelString('EDID','eid'),
        MelStructA('WLST','Ii', 'Weather', (FID,'weather'), 'chance'),
        MelString('FNAM','sunPath'),
        MelString('GNAM','glarePath'),
        MelModel(),
        MelStruct('TNAM', '6B', 'riseBegin', 'riseEnd', 'setBegin', 'setEnd',
                  'volatility', 'phaseLength'),
        )
    __slots__ = melSet.getSlotsUsed()

class MreClot(MelRecord):
    """Clothing record."""
    classType = 'CLOT'
    _flags = MelBipedFlags(0L, Flags.getNames((16, 'hideRings'),
                                              (17, 'hideAmulet'),
                                              (22, 'notPlayable')))
    melSet = MelSet(
        MelString('EDID','eid'),
        MelString('FULL','full'),
        MelFid('SCRI','script'),
        MelFid('ENAM','enchantment'),
        MelOptStruct('ANAM','H','enchantPoints'),
        MelStruct('BMDT','I',(_flags,'flags',0L)),
        MelModel('maleBody',0),
        MelModel('maleWorld',2),
        MelString('ICON','maleIconPath'),
        MelModel('femaleBody',3),
        MelModel('femaleWorld',4),
        MelString('ICO2','femaleIconPath'),
        MelStruct('DATA','If','value','weight'),
        )
    __slots__ = melSet.getSlotsUsed()

class MreCont(MelRecord):
    """Container record."""
    classType = 'CONT'
    _flags = Flags(0,Flags.getNames(None,'respawns'))
    melSet = MelSet(
        MelString('EDID','eid'),
        MelString('FULL','full'),
        MelModel(),
        MelFid('SCRI','script'),
        MelStructs('CNTO','Ii','items',(FID,'item'),'count'),
        MelStruct('DATA','=Bf',(_flags,'flags',0L),'weight'),
        MelFid('SNAM','soundOpen'),
        MelFid('QNAM','soundClose'),
        )
    __slots__ = melSet.getSlotsUsed()

class MreCrea(MreActor):
    """Creature Record."""
    classType = 'CREA'
    #--Main flags
    _flags = Flags(0L,Flags.getNames(
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
#    #--AI Service flags
    aiService = Flags(0L,Flags.getNames(
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
    #--Mel Set
    melSet = MelSet(
        MelString('EDID','eid'),
        MelString('FULL','full'),
        MelModel(),
        MelFids('SPLO','spells'),
        MelStrings('NIFZ','bodyParts'),
        MelBase('NIFT','nift_p'), ###Texture File hashes, Byte Array
        MelStruct('ACBS','=I3Hh2H',
            (_flags,'flags',0L),'baseSpell','fatigue','barterGold',
            ('level',1),'calcMin','calcMax'),
        MelStructs('SNAM','=IB3s','factions',
            (FID,'faction',None),'rank',('unused1','IFZ')),
        MelFid('INAM','deathItem'),
        MelFid('SCRI','script'),
        MelStructs('CNTO','Ii','items',(FID,'item',None),('count',1)),
        MelStruct('AIDT','=4BIbB2s',
            ('aggression',5),('confidence',50),('energyLevel',50),
            ('responsibility',50),(aiService,'services',0L),'trainSkill',
            'trainLevel',('unused1',null2)),
        MelFids('PKID','aiPackages'),
        MelStrings('KFFZ','animations'),
        MelStruct('DATA','=5BsH2sH8B','creatureType','combat','magic','stealth',
                  'soul',('unused2',null1),'health',('unused3',null2),
                  'attackDamage','strength','intelligence','willpower',
                  'agility','speed','endurance','personality','luck'),
        MelStruct('RNAM','B','attackReach'),
        MelFid('ZNAM','combatStyle'),
        MelStruct('TNAM','f','turningSpeed'),
        MelStruct('BNAM','f','baseScale'),
        MelStruct('WNAM','f','footWeight'),
        MelFid('CSCR','inheritsSoundsFrom'),
        MelString('NAM0','bloodSprayPath'),
        MelString('NAM1','bloodDecalPath'),
        MelGroups('sounds',
            MelStruct('CSDT','I','type'),
            MelFid('CSDI','sound'),
            MelStruct('CSDC','B','chance'),
        ),
        )
    __slots__ = MreActor.__slots__ + melSet.getSlotsUsed()

class MreCsty(MelRecord):
    """CSTY Record. Combat Styles."""
    classType = 'CSTY'
    _flagsA = Flags(0L,Flags.getNames(
        ( 0,'advanced'),
        ( 1,'useChanceForAttack'),
        ( 2,'ignoreAllies'),
        ( 3,'willYield'),
        ( 4,'rejectsYields'),
        ( 5,'fleeingDisabled'),
        ( 6,'prefersRanged'),
        ( 7,'meleeAlertOK'),
        ))
    _flagsB = Flags(0L,Flags.getNames(
        ( 0,'doNotAcquire'),
        ))

    class MelCstdData(MelStruct):
        """Handle older truncated DATA for CSTD subrecord."""
        def loadData(self, record, ins, sub_type, size_, readId):
            if size_ == 124:
                MelStruct.loadData(self, record, ins, sub_type, size_, readId)
                return
            elif size_ == 120:
                #--Else 120 byte record (skips flagsB
                unpacked = ins.unpack('2B2s8f2B2s3fB3s2f5B3s2f2B2s7fB3sf',
                                      size_, readId)
            elif size_ == 112:
                #--112 byte record (skips flagsB, rushChance, unused6, rushMult
                unpacked = ins.unpack('2B2s8f2B2s3fB3s2f5B3s2f2B2s7f', size_,
                                      readId)
            elif size_ == 104:
                # --104 byte record (skips flagsB, rushChance, unused6,
                #  rushMult, rStand, groupStand
                #-- only one occurrence (AndragilTraining
                unpacked = ins.unpack('2B2s8f2B2s3fB3s2f5B3s2f2B2s5f', size_,
                                      readId)
            elif size_ == 92:
                #--92 byte record (skips flagsB, rushChance, unused6, rushMult,
                #  rStand, groupStand mDistance, rDistance, buffStand
                #-- These records keep getting shorter and shorter...
                #-- This one is used by quite a few npcs
                unpacked = ins.unpack('2B2s8f2B2s3fB3s2f5B3s2f2B2s2f', size_,
                                      readId)
            elif size_ == 84:
                #--84 byte record (skips flagsB, rushChance, unused6, rushMult,
                #  rStand, groupStand mDistance, rDistance, buffStand,
                #  rMultOpt, rMultMax
                #-- This one is present once: VidCaptureNoAttacks and it
                # isn't actually used.
                unpacked = ins.unpack('2B2s8f2B2s3fB3s2f5B3s2f2B2s', size_,
                                      readId)
            else:
                raise ModError(ins.inName,
                               u'Unexpected size encountered for CSTD '
                               u'subrecord: %i' % size_)
            unpacked += self.defaults[len(unpacked):]
            setter = record.__setattr__
            for attr,value,action in zip(self.attrs,unpacked,self.actions):
                if callable(action): value = action(value)
                setter(attr,value)
            if self._debug: print unpacked, record.flagsA.getTrueAttrs()
    #--Mel Set
    melSet = MelSet(
        MelString('EDID','eid'),
        MelCstdData('CSTD', '2B2s8f2B2s3fB3s2f5B3s2f2B2s7fB3sfI',
                    'dodgeChance', 'lrChance', ('unused1', null2),
                    'lrTimerMin', 'lrTimerMax', 'forTimerMin', 'forTimerMax',
                    'backTimerMin', 'backTimerMax', 'idleTimerMin',
                    'idleTimerMax', 'blkChance', 'atkChance',
                    ('unused2', null2), 'atkBRecoil', 'atkBunc', 'atkBh2h',
                    'pAtkChance', ('unused3', null3), 'pAtkBRecoil',
                    'pAtkBUnc', 'pAtkNormal', 'pAtkFor', 'pAtkBack', 'pAtkL',
                    'pAtkR', ('unused4', null3), 'holdTimerMin',
                    'holdTimerMax', (_flagsA, 'flagsA'), 'acroDodge',
                    ('unused5', null2), ('rMultOpt', 1.0), ('rMultMax', 1.0),
                    ('mDistance', 250.0), ('rDistance', 1000.0),
                    ('buffStand', 325.0), ('rStand', 500.0),
                    ('groupStand', 325.0), ('rushChance', 25),
                    ('unused6', null3), ('rushMult', 1.0),
                    (_flagsB, 'flagsB')),
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
    """Dialog record."""
    melSet = MelSet(
        MelString('EDID','eid'),
        MelFids('QSTI','quests'), ### QSTRs?
        MelString('FULL','full'),
        MelStruct('DATA','B','dialType'),
    )
    __slots__ = melSet.getSlotsUsed()

class MreDoor(MelRecord):
    """Container record."""
    classType = 'DOOR'
    _flags = Flags(0, Flags.getNames('oblivionGate', 'automatic', 'hidden',
                                     'minimalUse'))
    melSet = MelSet(
        MelString('EDID','eid'),
        MelString('FULL','full'),
        MelModel(),
        MelFid('SCRI','script'),
        MelFid('SNAM','soundOpen'),
        MelFid('ANAM','soundClose'),
        MelFid('BNAM','soundLoop'),
        MelStruct('FNAM','B',(_flags,'flags',0L)),
        MelFids('TNAM','destinations'),
        )
    __slots__ = melSet.getSlotsUsed()

class MreEfsh(MelRecord):
    """Effect shader record."""
    classType = 'EFSH'
    _flags = Flags(0L,Flags.getNames(
        ( 0,'noMemShader'),
        ( 3,'noPartShader'),
        ( 4,'edgeInverse'),
        ( 5,'memSkinOnly'),
        ))

    class MelEfshData(MelStruct):
        """Handle older truncated DATA for EFSH subrecord."""
        def loadData(self, record, ins, sub_type, size_, readId):
            if size_ == 224:
                MelStruct.loadData(self, record, ins, sub_type, size_, readId)
                return
            elif size_ == 96:
                #--Else 96 byte record (skips particle variables, and color
                # keys. Only used twice in test shaders (0004b6d5, 0004b6d6)
                unpacked = ins.unpack('B3s3I3Bs9f3Bs8fI', size_, readId)
            else:
                raise ModError(ins.inName,
                               u'Unexpected size encountered for EFSH '
                               u'subrecord: %i' % size_)
            unpacked += self.defaults[len(unpacked):]
            setter = record.__setattr__
            for attr,value,action in zip(self.attrs,unpacked,self.actions):
                if callable(action): value = action(value)
                setter(attr,value)
            if self._debug: print unpacked, record.flags.getTrueAttrs()
    melSet = MelSet(
        MelString('EDID','eid'),
        MelString('ICON','fillTexture'),
        MelString('ICO2','particleTexture'),
        MelEfshData('DATA', 'B3s3I3Bs9f3Bs8f5I19f3Bs3Bs3Bs6f',
                    (_flags, 'flags'), ('unused1', null3), 'memSBlend',
                    'memBlendOp', 'memZFunc', 'fillRed', 'fillGreen',
                    'fillBlue', ('unused2', null1), 'fillAIn', 'fillAFull',
                    'fillAOut', 'fillAPRatio', 'fillAAmp', 'fillAFreq',
                    'fillAnimSpdU', 'fillAnimSpdV', 'edgeOff', 'edgeRed',
                    'edgeGreen', 'edgeBlue', ('unused3', null1), 'edgeAIn',
                    'edgeAFull', 'edgeAOut', 'edgeAPRatio', 'edgeAAmp',
                    'edgeAFreq', 'fillAFRatio', 'edgeAFRatio', 'memDBlend',
                    ('partSBlend', 5), ('partBlendOp', 1), ('partZFunc', 4),
                    ('partDBlend', 6), ('partBUp', 0.0), ('partBFull', 0.0),
                    ('partBDown', 0.0), ('partBFRatio', 1.0),
                    ('partBPRatio', 1.0), ('partLTime', 1.0),
                    ('partLDelta', 0.0), ('partNSpd', 0.0), ('partNAcc', 0.0),
                    ('partVel1', 0.0), ('partVel2', 0.0), ('partVel3', 0.0),
                    ('partAcc1', 0.0), ('partAcc2', 0.0), ('partAcc3', 0.0),
                    ('partKey1', 1.0), ('partKey2', 1.0),
                    ('partKey1Time', 0.0), ('partKey2Time', 1.0),
                    ('key1Red', 255), ('key1Green', 255), ('key1Blue', 255),
                    ('unused4', null1), ('key2Red', 255), ('key2Green', 255),
                    ('key2Blue', 255), ('unused5', null1), ('key3Red', 255),
                    ('key3Green', 255), ('key3Blue', 255), ('unused6', null1),
                    ('key1A', 1.0), ('key2A', 1.0), ('key3A', 1.0),
                    ('key1Time', 0.0), ('key2Time', 0.5), ('key3Time', 1.0)),
        )
    __slots__ = melSet.getSlotsUsed()

class MreEnch(MelRecord,MreHasEffects):
    """Enchantment record."""
    classType = 'ENCH'
    _flags = Flags(0L,Flags.getNames('noAutoCalc'))
    melSet = MelSet(
        MelString('EDID','eid'),
        MelFull0(), #--At least one mod has this. Odd.
        MelStruct('ENIT', '3IB3s', 'itemType', 'chargeAmount', 'enchantCost',
                  (_flags, 'flags', 0L), ('unused1', null3)),
        #--itemType = 0: Scroll, 1: Staff, 2: Weapon, 3: Apparel
        MelEffects(),
        )
    __slots__ = melSet.getSlotsUsed()

class MreEyes(MelRecord):
    """Eyes record."""
    classType = 'EYES'
    _flags = Flags(0L,Flags.getNames('playable',))
    melSet = MelSet(
        MelString('EDID','eid'),
        MelString('FULL','full'),
        MelString('ICON','iconPath'),
        MelStruct('DATA','B',(_flags,'flags')),
        )
    __slots__ = melSet.getSlotsUsed()

class MreFact(MelRecord):
    """Faction record."""
    classType = 'FACT'
    _flags = Flags(0L,Flags.getNames('hiddenFromPC','evil','specialCombat'))
    melSet = MelSet(
        MelString('EDID','eid'),
        MelString('FULL','full'),
        MelStructs('XNAM','Ii','relations',(FID,'faction'),'mod'),
        MelStruct('DATA','B',(_flags,'flags',0L)),
        MelOptStruct('CNAM','f',('crimeGoldMultiplier',None)),
        MelGroups('ranks',
            MelStruct('RNAM','i','rank'),
            MelString('MNAM','male'),
            MelString('FNAM','female'),
            MelString('INAM','insigniaPath'),),
        )
    __slots__ = melSet.getSlotsUsed()

class MreFlor(MelRecord):
    """Flora (plant) record."""
    classType = 'FLOR'
    melSet = MelSet(
        MelString('EDID','eid'),
        MelString('FULL','full'),
        MelModel(),
        MelFid('SCRI','script'),
        MelFid('PFIG','ingredient'),
        MelStruct('PFPC','4B','spring','summer','fall','winter'),
        )
    __slots__ = melSet.getSlotsUsed()

class MreFurn(MelRecord):
    """Furniture record."""
    classType = 'FURN'
    _flags = Flags() #--Governs type of furniture and which anims are available
    #--E.g., whether it's a bed, and which of the bed entry/exit animations
    # are available
    melSet = MelSet(
        MelString('EDID','eid'),
        MelString('FULL','full'),
        MelModel(),
        MelFid('SCRI','script'),
        MelStruct('MNAM','I',(_flags,'activeMarkers',0L)), ####ByteArray
        )
    __slots__ = melSet.getSlotsUsed()

class MreGmst(MreGmstBase):
    """Oblivion gmst record"""

class MreGras(MelRecord):
    """Grass record."""
    classType = 'GRAS'
    _flags = Flags(0,Flags.getNames('vLighting','uScaling','fitSlope'))
    melSet = MelSet(
        MelString('EDID','eid'),
        MelModel(),
        MelStruct('DATA', '3BsH2sI4fB3s', 'density', 'minSlope', 'maxSlope',
                  ('unused1', null1), 'waterDistance', ('unused2', null2),
                  'waterOp', 'posRange', 'heightRange', 'colorRange',
                  'wavePeriod', (_flags, 'flags'), ('unused3', null3)),
        )
    __slots__ = melSet.getSlotsUsed()

class MreHair(MelRecord):
    """Hair record."""
    classType = 'HAIR'
    _flags = Flags(0L,Flags.getNames('playable','notMale','notFemale','fixed'))
    melSet = MelSet(
        MelString('EDID','eid'),
        MelString('FULL','full'),
        MelModel(),
        MelString('ICON','iconPath'),
        MelStruct('DATA','B',(_flags,'flags')),
        )
    __slots__ = melSet.getSlotsUsed()

class MreIdle(MelRecord):
    """Idle record."""
    classType = 'IDLE'
    melSet = MelSet(
        MelString('EDID','eid'),
        MelModel(),
        MelConditions(),
        MelStruct('ANAM','B','group'),
        MelStruct('DATA','II',(FID,'parent'),(FID,'prevId')),####Array?
        )
    __slots__ = melSet.getSlotsUsed()

class MreInfo(MelRecord):
    """Info (dialog entry) record."""
    classType = 'INFO'
    _flags = Flags(0, Flags.getNames('goodbye', 'random', 'sayOnce',
                                     'runImmediately', 'infoRefusal',
                                     'randomEnd', 'runForRumors'))
    class MelInfoData(MelStruct):
        """Support truncated 2 byte version."""
        def loadData(self, record, ins, sub_type, size_, readId):
            if size_ != 2:
                MelStruct.loadData(self, record, ins, sub_type, size_, readId)
                return
            unpacked = ins.unpack('H', size_, readId)
            unpacked += self.defaults[len(unpacked):]
            setter = record.__setattr__
            for attr,value,action in zip(self.attrs,unpacked,self.actions):
                if callable(action): value = action(value)
                setter(attr,value)
            if self._debug: print (record.dialType,record.flags.getTrueAttrs())

    class MelInfoSchr(MelStruct):
        """Print only if schd record is null."""
        def dumpData(self,record,out):
            if not record.schd_p:
                MelStruct.dumpData(self,record,out)
    #--MelSet
    melSet = MelSet(
        MelInfoData('DATA','3B','dialType','nextSpeaker',(_flags,'flags')),
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
        MelInfoSchr('SCHR', '4s4I', ('unused1', null4), 'numRefs',
                    'compiledSize', 'lastIndex', 'scriptType'),
        # Old format script header would need dumpExtra to handle it
        MelBase('SCHD','schd_p'),
        MelBase('SCDA','compiled_p'),
        MelString('SCTX','scriptText'),
        MelScrxen('SCRV/SCRO','references')
        )
    __slots__ = melSet.getSlotsUsed()

class MreIngr(MelRecord,MreHasEffects):
    """INGR (ingredient) record."""
    classType = 'INGR'
    _flags = Flags(0L,Flags.getNames('noAutoCalc','isFood'))
    melSet = MelSet(
        MelString('EDID','eid'),
        MelFull0(),
        MelModel(),
        MelString('ICON','iconPath'),
        MelFid('SCRI','script'),
        MelStruct('DATA','f','weight'),
        MelStruct('ENIT','iB3s','value',(_flags,'flags',0L),('unused1',null3)),
        MelEffects(),
        )
    __slots__ = melSet.getSlotsUsed()

class MreKeym(MelRecord):
    """MISC (miscellaneous item) record."""
    classType = 'KEYM'
    melSet = MelSet(
        MelString('EDID','eid'),
        MelString('FULL','full'),
        MelModel(),
        MelString('ICON','iconPath'),
        MelFid('SCRI','script'),
        MelStruct('DATA','if','value','weight'),
        )
    __slots__ = melSet.getSlotsUsed()
#------------------------------------------------------------------------------
## Commented out for performance reasons. Slows down loading quite a bit.
## If Bash ever wants to be able to add masters to a mod, this minimal definition is required
## It has to be able to convert the formIDs found in BTXT, ATXT, and VTEX to not break the mod
##class MreLand(MelRecord):
##    """Land structure. Part of exterior cells."""
##    ####Could probably be loaded via MelStructA,
##    ####but little point since it is too complex to manipulate
##    classType = 'LAND'
##    melSet = MelSet(
##        MelBase('DATA','data_p'),
##        MelBase('VNML','normals_p'),
##        MelBase('VHGT','heights_p'),
##        MelBase('VCLR','vertexColors_p'),
##        MelStructs('BTXT','IBBh','baseTextures', (FID,'texture'), 'quadrant', 'unused1', 'layer'),
##        MelGroups('alphaLayers',
##            MelStruct('ATXT','IBBh',(FID,'texture'), 'quadrant', 'unused1', 'layer'),
##            MelStructA('VTXT','H2Bf', 'opacities', 'position', 'unused1', 'opacity'),
##        ),
##        MelFidList('VTEX','vertexTextures'),
##    )
##    __slots__ = melSet.getSlotsUsed()
#------------------------------------------------------------------------------
class MreLigh(MelRecord):
    """Light source record."""
    classType = 'LIGH'
    _flags = Flags(0L,
                   Flags.getNames('dynamic', 'canTake', 'negative', 'flickers',
                                  'unk1', 'offByDefault', 'flickerSlow',
                                  'pulse', 'pulseSlow', 'spotLight',
                                  'spotShadow'))
    #--Mel NPC DATA
    class MelLighData(MelStruct):
        """Handle older truncated DATA for LIGH subrecord."""
        def loadData(self, record, ins, sub_type, size_, readId):
            if size_ == 32:
                MelStruct.loadData(self, record, ins, sub_type, size_, readId)
                return
            elif size_ == 24:
                #--Else 24 byte record (skips value and weight...
                unpacked = ins.unpack('iI3BsIff', size_, readId)
            else:
                raise ModError(ins.inName, _(
                    'Unexpected size encountered for LIGH:DATA subrecord: '
                    '%i') % size_)
            unpacked += self.defaults[len(unpacked):]
            setter = record.__setattr__
            for attr,value,action in zip(self.attrs,unpacked,self.actions):
                if callable(action): value = action(value)
                setter(attr,value)
            if self._debug: print unpacked, record.flags.getTrueAttrs()
    melSet = MelSet(
        MelString('EDID','eid'),
        MelModel(),
        MelFid('SCRI','script'),
        MelString('FULL','full'),
        MelString('ICON','iconPath'),
        MelLighData('DATA', 'iI3BsIffIf', 'duration', 'radius', 'red', 'green',
                    'blue', ('unused1', null1), (_flags, 'flags', 0L),
                    'falloff', 'fov', 'value', 'weight'),
        MelOptStruct('FNAM','f',('fade',None)),
        MelFid('SNAM','sound'),
        )
    __slots__ = melSet.getSlotsUsed()

class MreLscr(MelRecord):
    """Load screen."""
    classType = 'LSCR'
    melSet = MelSet(
        MelString('EDID','eid'),
        MelString('ICON','iconPath'),
        MelString('DESC','text'),
        MelStructs('LNAM', '2I2h', 'Locations', (FID, 'direct'),
                   (FID, 'indirect'), 'gridy', 'gridx'),
        )
    __slots__ = melSet.getSlotsUsed()

class MreLtex(MelRecord):
    """Landscape Texture."""
    _flags = Flags(0L,Flags.getNames(
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
    classType = 'LTEX'
    melSet = MelSet(
        MelString('EDID','eid'),
        MelString('ICON','iconPath'),
        MelOptStruct('HNAM', '3B', (_flags, 'flags'), 'friction',
                     'restitution'), # ###flags are actually an enum....
        MelOptStruct('SNAM','B','specular'),
        MelFids('GNAM', 'grass'),
        )
    __slots__ = melSet.getSlotsUsed()

class MreLvlc(MreLeveledList):
    """LVLC record. Leveled list for creatures."""
    classType = 'LVLC'
    __slots__ = MreLeveledList.__slots__

class MreLvli(MreLeveledList):
    """LVLI record. Leveled list for items."""
    classType = 'LVLI'
    __slots__ = MreLeveledList.__slots__

class MreLvsp(MreLeveledList):
    """LVSP record. Leveled list for items."""
    classType = 'LVSP'
    __slots__ = MreLeveledList.__slots__

class MreMgef(MelRecord):
    """MGEF (magic effect) record."""
    classType = 'MGEF'
    #--Main flags
    _flags = Flags(0L,Flags.getNames(
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

    #--Mel NPC DATA
    class MelMgefData(MelStruct):
        """Handle older truncated DATA for DARK subrecord."""
        def loadData(self, record, ins, sub_type, size_, readId):
            if size_ == 64:
                MelStruct.loadData(self, record, ins, sub_type, size_, readId)
                return
            elif size_ == 36:
                #--Else is data for DARK record, read it all.
                unpacked = ins.unpack('IfIiiH2sIfI', size_, readId)
            else:
                raise ModError(ins.inName,
                               u'Unexpected size encountered for MGEF:DATA '
                               u'subrecord: %i' % size_)
            unpacked += self.defaults[len(unpacked):]
            setter = record.__setattr__
            for attr,value,action in zip(self.attrs,unpacked,self.actions):
                if callable(action): value = action(value)
                setter(attr,value)
            if self._debug: print unpacked
    melSet = MelSet(
        MelString('EDID','eid'),
        MelString('FULL','full'),
        MelString('DESC','text'),
        MelString('ICON','iconPath'),
        MelModel(),
        MelMgefData('DATA', 'IfIiiH2sIf6I2f', (_flags, 'flags'), 'baseCost',
                    (FID, 'associated'), 'school', 'resistValue',
                    'numCounters', ('unused1', null2), (FID, 'light'),
                    'projectileSpeed', (FID, 'effectShader'),
                    (FID, 'enchantEffect', 0), (FID, 'castingSound', 0),
                    (FID, 'boltSound', 0), (FID, 'hitSound', 0),
                    (FID, 'areaSound', 0), ('cefEnchantment', 0.0),
                    ('cefBarter', 0.0)),
        MelStructA('ESCE','4s','counterEffects','effect'),
        )
    __slots__ = melSet.getSlotsUsed()

class MreMisc(MelRecord):
    """MISC (miscellaneous item) record."""
    classType = 'MISC'
    melSet = MelSet(
        MelString('EDID','eid'),
        MelString('FULL','full'),
        MelModel(),
        MelString('ICON','iconPath'),
        MelFid('SCRI','script'),
        # DATA can have a FormID in it, this
        # should be rewriten
        MelStruct('DATA','if','value','weight'),
        )
    __slots__ = melSet.getSlotsUsed()

class MreNpc(MreActor):
    """NPC Record. Non-Player Character."""
    classType = 'NPC_'
    #--Main flags
    _flags = Flags(0L,Flags.getNames(
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
    #--AI Service flags
    aiService = Flags(0L,Flags.getNames(
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
    #--Mel NPC DATA
    class MelNpcData(MelStruct):
        """Convert npc stats into skills, health, attributes."""
        def loadData(self, record, ins, sub_type, size_, readId):
            unpacked = list(ins.unpack('=21BH2s8B', size_, readId))
            recordSetAttr = record.__setattr__
            recordSetAttr('skills',unpacked[:21])
            recordSetAttr('health',unpacked[21])
            recordSetAttr('unused1',unpacked[22])
            recordSetAttr('attributes',unpacked[23:])
            if self._debug: print unpacked[:21],unpacked[21],unpacked[23:]
        def dumpData(self,record,out):
            """Dumps data from record to outstream."""
            recordGetAttr = record.__getattribute__
            values = recordGetAttr('skills') + [recordGetAttr('health')] + [
                recordGetAttr('unused1')] + recordGetAttr('attributes')
            out.packSub(self.subType,'=21BH2s8B',*values)
    #--Mel Set
    melSet = MelSet(
        MelString('EDID','eid'),
        MelString('FULL','full'),
        MelModel(),
        MelStruct('ACBS','=I3Hh2H',
            (_flags,'flags',0L),'baseSpell','fatigue','barterGold',
            ('level',1),'calcMin','calcMax'),
        MelStructs('SNAM','=IB3s','factions',
            (FID,'faction',None),'rank',('unused1','ODB')),
        MelFid('INAM','deathItem'),
        MelFid('RNAM','race'),
        MelFids('SPLO','spells'),
        MelFid('SCRI','script'),
        MelStructs('CNTO','Ii','items',(FID,'item',None),('count',1)),
        MelStruct('AIDT', '=4BIbB2s', ('aggression', 5), ('confidence', 50),
                  ('energyLevel', 50), ('responsibility', 50),
                  (aiService, 'services', 0L), 'trainSkill', 'trainLevel',
                  ('unused1', null2)),
        MelFids('PKID','aiPackages'),
        MelStrings('KFFZ','animations'),
        MelFid('CNAM','iclass'),
        MelNpcData('DATA', '', ('skills', [0] * 21), 'health',
                   ('unused2', null2), ('attributes', [0] * 8)),
        MelFid('HNAM','hair'),
        MelOptStruct('LNAM','f',('hairLength',None)),
        MelFid('ENAM','eye'), ####fid Array
        MelStruct('HCLR', '3Bs', 'hairRed', 'hairBlue', 'hairGreen',
                  ('unused3', null1)),
        MelFid('ZNAM','combatStyle'),
        MelBase('FGGS','fggs_p'), ####FaceGen Geometry-Symmetric
        MelBase('FGGA','fgga_p'), ####FaceGen Geometry-Asymmetric
        MelBase('FGTS','fgts_p'), ####FaceGen Texture-Symmetric
        MelStruct('FNAM','H','fnam'), ####Byte Array
        )
    __slots__ = MreActor.__slots__ + melSet.getSlotsUsed()

    def setRace(self,race):
        """Set additional race info."""
        self.race = race
        #--Model
        if not self.model:
            self.model = self.getDefault('model')
        if race in (0x23fe9,0x223c7):
            self.model.modPath = u"Characters\\_Male\\SkeletonBeast.NIF"
        else:
            self.model.modPath = u"Characters\\_Male\\skeleton.nif"
        #--FNAM
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
    """AI package record."""
    classType = 'PACK'
    _flags = Flags(0,Flags.getNames(
        'offersServices','mustReachLocation','mustComplete','lockAtStart',
        'lockAtEnd','lockAtLocation','unlockAtStart','unlockAtEnd',
        'unlockAtLocation','continueIfPcNear','oncePerDay',None,
        'skipFallout','alwaysRun',None,None,
        None,'alwaysSneak','allowSwimming','allowFalls',
        'unequipArmor','unequipWeapons','defensiveCombat','useHorse',
        'noIdleAnims',))
    class MelPackPkdt(MelStruct):
        """Support older 4 byte version."""
        def loadData(self, record, ins, sub_type, size_, readId):
            if size_ != 4:
                MelStruct.loadData(self, record, ins, sub_type, size_, readId)
            else:
                record.flags,record.aiType,junk = ins.unpack('HBs',4,readId)
                record.flags = MrePack._flags(record.flags)
                record.unused1 = null3
                if self._debug: print (
                    record.flags.getTrueAttrs(), record.aiType, record.unused1)
    class MelPackLT(MelStruct):
        """For PLDT and PTDT. Second element of both may be either an FID or a
        long, depending on value of first element."""
        def hasFids(self,formElements):
            formElements.add(self)
        def dumpData(self,record,out):
            if (self.subType == 'PLDT' and (record.locType or record.locId)) \
                    or (self.subType == 'PTDT' and
                            (record.targetType or record.targetId)):
                MelStruct.dumpData(self,record,out)
        def mapFids(self,record,function,save=False):
            """Applies function to fids. If save is true, then fid is set
            to result of function."""
            if self.subType == 'PLDT' and record.locType != 5:
                result = function(record.locId)
                if save: record.locId = result
            elif self.subType == 'PTDT' and record.targetType != 2:
                result = function(record.targetId)
                if save: record.targetId = result
    #--MelSet
    melSet = MelSet(
        MelString('EDID','eid'),
        MelPackPkdt('PKDT','IB3s',(_flags,'flags'),'aiType',('unused1',null3)),
        MelPackLT('PLDT','iIi','locType','locId','locRadius'),
        MelStruct('PSDT','2bBbi','month','day','date','time','duration'),
        MelPackLT('PTDT','iIi','targetType','targetId','targetCount'),
        MelConditions(),
        )
    __slots__ = melSet.getSlotsUsed()
#------------------------------------------------------------------------------
## See the comments on MreLand. Commented out for same reasons.
##class MrePgrd(MelRecord):
##    """Path grid structure. Part of cells."""
##    ####Could probably be loaded via MelStructA,
##    ####but little point since it is too complex to manipulate
##    classType = 'PGRD'
##    class MelPgrl(MelStructs):
##        """Handler for pathgrid pgrl record."""
##        def loadData(self,record,ins,type,size,readId):
##            """Reads data from ins into record attribute."""
##            if(size % 4 != 0):
##                raise "Unexpected size encountered for pathgrid PGRL subrecord: %s" % size
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
##            """Dumps data from record to outstream."""
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
    """Quest record."""
    classType = 'QUST'
    _questFlags = Flags(0, Flags.getNames('startGameEnabled', None,
                                          'repeatedTopics', 'repeatedStages'))
    stageFlags = Flags(0,Flags.getNames('complete'))
    targetFlags = Flags(0,Flags.getNames('ignoresLocks'))

    #--CDTA loader
    class MelQustLoaders(DataDict):
        """Since CDTA subrecords occur in three different places, we need
        to replace ordinary 'loaders' dictionary with a 'dictionary' that will
        return the correct element to handle the CDTA subrecord. 'Correct'
        element is determined by which other subrecords have been encountered.
        """
        def __init__(self,loaders,quest,stages,targets):
            self.data = loaders
            self.type_ctda = {'EDID':quest, 'INDX':stages, 'QSTA':targets}
            self.ctda = quest #--Which ctda element loader to use next.
        def __getitem__(self,key):
            if key == 'CTDA': return self.ctda
            self.ctda = self.type_ctda.get(key, self.ctda)
            return self.data[key]

    #--MelSet
    melSet = MelSet(
        MelString('EDID','eid'),
        MelFid('SCRI','script'),
        MelString('FULL','full'),
        MelString('ICON','iconPath'),
        MelStruct('DATA','BB',(_questFlags,'questFlags',0),'priority'),
        MelConditions(),
        MelGroups('stages',
            MelStruct('INDX','h','stage'),
            MelGroups('entries',
                MelStruct('QSDT','B',(stageFlags,'flags')),
                MelConditions(),
                MelString('CNAM','text'),
                MelStruct('SCHR', '4s4I', ('unused1', null4), 'numRefs',
                          'compiledSize', 'lastIndex', 'scriptType'),
                MelBase('SCDA','compiled_p'),
                MelString('SCTX','scriptText'),
                MelScrxen('SCRV/SCRO','references')
                ),
            ),
        MelGroups('targets', MelStruct('QSTA', 'IB3s', (FID, 'targetId'),
                                       (targetFlags, 'flags'),
                                       ('unused1', null3)),
            MelConditions(),
            ),
        )
    melSet.loaders = MelQustLoaders(melSet.loaders,*melSet.elements[5:8])
    __slots__ = melSet.getSlotsUsed()

class MreRace(MelRecord):
    """Race record.

    This record is complex to read and write. Relatively simple problems are
    the VNAM which can be empty or zeroed depending on relationship between
    voices and the fid for the race.

    The face and body data is much more complicated, with the same subrecord
    types mapping to different attributes depending on preceding flag
    subrecords (NAM0, NAM1, NMAN, FNAM and INDX.) These are handled by using
    the MelRaceDistributor class to dynamically reassign melSet.loaders[type]
    as the flag records are encountered.

    It's a mess, but this is the shortest, clearest implementation that I could
    think of."""

    classType = 'RACE'
    _flags = Flags(0L,Flags.getNames('playable'))

    class MelRaceVoices(MelStruct):
        """Set voices to zero, if equal race fid. If both are zero,
        then don't skip dump."""
        def dumpData(self,record,out):
            if record.maleVoice == record.fid: record.maleVoice = 0L
            if record.femaleVoice == record.fid: record.femaleVoice = 0L
            if (record.maleVoice,record.femaleVoice) != (0,0):
                MelStruct.dumpData(self,record,out)

    class MelRaceModel(MelGroup):
        """Most face data, like a MelModel - MODT + ICON. Load is controlled
        by MelRaceDistributor."""
        def __init__(self,attr,index):
            MelGroup.__init__(self,attr,
                MelString('MODL','modPath'),
                MelBase('MODB','modb_p'),
                MelBase('MODT','modt_p'),
                MelString('ICON','iconPath'),)
            self.index = index

        def dumpData(self,record,out):
            out.packSub('INDX','I',self.index)
            MelGroup.dumpData(self,record,out)

    class MelRaceIcon(MelString):
        """Most body data plus eyes for face. Load is controlled by
        MelRaceDistributor."""
        def __init__(self,attr,index):
            MelString.__init__(self,'ICON',attr)
            self.index = index
        def dumpData(self,record,out):
            out.packSub('INDX','I',self.index)
            MelString.dumpData(self,record,out)

    class MelRaceDistributor(MelNull):
        """Handles NAM0, NAM1, MNAM, FMAN and INDX records. Distributes load
        duties to other elements as needed."""
        def __init__(self):
            bodyAttrs = ('UpperBodyPath', 'LowerBodyPath', 'HandPath',
                         'FootPath', 'TailPath')
            self.attrs = {
                'MNAM':tuple('male'+text for text in bodyAttrs),
                'FNAM':tuple('female'+text for text in bodyAttrs),
                'NAM0':('head', 'maleEars', 'femaleEars', 'mouth',
                'teethLower', 'teethUpper', 'tongue', 'leftEye', 'rightEye',)
                }
            self.tailModelAttrs = {'MNAM': 'maleTailModel',
                                   'FNAM': 'femaleTailModel'}
            self._debug = False

        def getSlotsUsed(self):
            return '_loadAttrs',

        def getLoaders(self,loaders):
            """Self as loader for structure types."""
            for subType in ('NAM0','MNAM','FNAM','INDX'):
                loaders[subType] = self

        def setMelSet(self,melSet):
            """Set parent melset. Need this so that can reassign loaders
            later."""
            self.melSet = melSet
            self.loaders = {}
            for element in melSet.elements:
                attr = element.__dict__.get('attr',None)
                if attr: self.loaders[attr] = element

        def loadData(self, record, ins, sub_type, size_, readId):
            if sub_type in ('NAM0', 'MNAM', 'FNAM'):
                record._loadAttrs = self.attrs[sub_type]
                attr = self.tailModelAttrs.get(sub_type)
                if not attr: return
            else: #--INDX
                index, = ins.unpack('I',4,readId)
                attr = record._loadAttrs[index]
            element = self.loaders[attr]
            for sub_type_ in ('MODL', 'MODB', 'MODT', 'ICON'):
                self.melSet.loaders[sub_type_] = element

    #--Mel Set
    melSet = MelSet(
        MelString('EDID','eid'),
        MelString('FULL','full'),
        MelString('DESC','text'),
        MelFids('SPLO','spells'),
        MelStructs('XNAM','Ii','relations',(FID,'faction'),'mod'),
        MelStruct('DATA', '14b2s4fI', 'skill1', 'skill1Boost', 'skill2',
                  'skill2Boost', 'skill3', 'skill3Boost', 'skill4',
                  'skill4Boost', 'skill5', 'skill5Boost', 'skill6',
                  'skill6Boost', 'skill7', 'skill7Boost', ('unused1', null2),
                  'maleHeight', 'femaleHeight', 'maleWeight', 'femaleWeight',
                  (_flags, 'flags', 0L)),
        MelRaceVoices('VNAM','2I',(FID,'maleVoice'),
                      (FID,'femaleVoice')), #--0 same as race fid.
        MelOptStruct('DNAM', '2I', (FID, 'defaultHairMale', 0L),
                     (FID, 'defaultHairFemale', 0L)), # --0=None
        MelStruct('CNAM', 'B', 'defaultHairColor'), #--Int corresponding to
        # GMST sHairColorNN
        MelOptStruct('PNAM','f','mainClamp'),
        MelOptStruct('UNAM','f','faceClamp'),
        #--Male: Str,Int,Wil,Agi,Spd,End,Per,luck; Female Str,Int,...
        MelStruct('ATTR', '16B', 'maleStrength', 'maleIntelligence',
                  'maleWillpower', 'maleAgility', 'maleSpeed', 'maleEndurance',
                  'malePersonality', 'maleLuck', 'femaleStrength',
                  'femaleIntelligence', 'femaleWillpower', 'femaleAgility',
                  'femaleSpeed', 'femaleEndurance', 'femalePersonality',
                  'femaleLuck'),
        #--Begin Indexed entries
        MelBase('NAM0','_nam0',''), ####Face Data Marker, wbEmpty
        MelRaceModel('head',0),
        MelRaceModel('maleEars',1),
        MelRaceModel('femaleEars',2),
        MelRaceModel('mouth',3),
        MelRaceModel('teethLower',4),
        MelRaceModel('teethUpper',5),
        MelRaceModel('tongue',6),
        MelRaceModel('leftEye',7),
        MelRaceModel('rightEye',8),
        MelBase('NAM1','_nam1',''), ####Body Data Marker, wbEmpty
        MelBase('MNAM','_mnam',''), ####Male Body Data Marker, wbEmpty
        MelModel('maleTailModel'),
        MelRaceIcon('maleUpperBodyPath',0),
        MelRaceIcon('maleLowerBodyPath',1),
        MelRaceIcon('maleHandPath',2),
        MelRaceIcon('maleFootPath',3),
        MelRaceIcon('maleTailPath',4),
        MelBase('FNAM','_fnam',''), ####Female Body Data Marker, wbEmpty
        MelModel('femaleTailModel'),
        MelRaceIcon('femaleUpperBodyPath',0),
        MelRaceIcon('femaleLowerBodyPath',1),
        MelRaceIcon('femaleHandPath',2),
        MelRaceIcon('femaleFootPath',3),
        MelRaceIcon('femaleTailPath',4),
        #--Normal Entries
        MelFidList('HNAM','hairs'),
        MelFidList('ENAM','eyes'),
        MelBase('FGGS','fggs_p'), ####FaceGen Geometry-Symmetric
        MelBase('FGGA','fgga_p'), ####FaceGen Geometry-Asymmetric
        MelBase('FGTS','fgts_p'), ####FaceGen Texture-Symmetric
        MelStruct('SNAM','2s',('snam_p',null2)),
        #--Distributor for face and body entries.
        MelRaceDistributor(),
        )
    melSet.elements[-1].setMelSet(melSet)
    __slots__ = melSet.getSlotsUsed()

class MreRefr(MelRecord):
    classType = 'REFR'
    _flags = Flags(0L,Flags.getNames('visible', 'canTravelTo'))
    _parentFlags = Flags(0L,Flags.getNames('oppositeParent'))
    _actFlags = Flags(0L, Flags.getNames('useDefault', 'activate', 'open',
                                         'openByDefault'))
    _lockFlags = Flags(0L,Flags.getNames(None, None, 'leveledLock'))
    class MelRefrXloc(MelOptStruct):
        """Handle older truncated XLOC for REFR subrecord."""
        def loadData(self, record, ins, sub_type, size_, readId):
            if size_ == 16:
                MelStruct.loadData(self, record, ins, sub_type, size_, readId)
                return
            elif size_ == 12:
                #--Else is skipping unused2
                unpacked = ins.unpack('B3sIB3s', size_, readId)
            else:
                raise ModError(ins.inName,
                               u'Unexpected size encountered for REFR:XLOC '
                               u'subrecord: %i' % size_)
            unpacked = unpacked[:-2] + self.defaults[
                                       len(unpacked) - 2:-2] + unpacked[-2:]
            setter = record.__setattr__
            for attr,value,action in zip(self.attrs,unpacked,self.actions):
                if callable(action): value = action(value)
                setter(attr,value)
            if self._debug: print unpacked

    class MelRefrXmrk(MelStruct):
        """Handler for xmrk record. Conditionally loads next items."""
        def loadData(self, record, ins, sub_type, size_, readId):
            """Reads data from ins into record attribute."""
            junk = ins.read(size_, readId)
            record.hasXmrk = True
            insTell = ins.tell
            insUnpack = ins.unpack
            pos = insTell()
            (sub_type_, size_) = insUnpack('4sH', 6, readId + '.FULL')
            while sub_type_ in ['FNAM', 'FULL', 'TNAM']:
                if sub_type_ == 'FNAM':
                    value = insUnpack('B', size_, readId)
                    record.flags = MreRefr._flags(*value)
                elif sub_type_ == 'FULL':
                    record.full = ins.readString(size_, readId)
                elif sub_type_ == 'TNAM':
                    record.markerType, record.unused5 = insUnpack('Bs', size_,
                                                                  readId)
                pos = insTell()
                (sub_type_, size_) = insUnpack('4sH', 6, readId + '.FULL')
            ins.seek(pos)
            if self._debug: print ' ', record.flags, record.full, \
                record.markerType

        def dumpData(self,record,out):
            if (record.flags, record.full, record.markerType,
                record.unused5) != self.defaults[1:]:
                record.hasXmrk = True
            if record.hasXmrk:
                try:
                    out.write(struct_pack('=4sH','XMRK',0))
                    out.packSub('FNAM','B',record.flags.dump())
                    value = record.full
                    if value is not None:
                        out.packSub0('FULL',value)
                    out.packSub('TNAM','Bs',record.markerType, record.unused5)
                except struct.error:
                    print self.subType, self.format, record.flags, \
                        record.full, record.markerType
                    raise

    melSet = MelSet(
        MelString('EDID','eid'),
        MelFid('NAME','base'),
        MelOptStruct('XTEL', 'I6f', (FID, 'destinationFid'), 'destinationPosX',
                     'destinationPosY', 'destinationPosZ', 'destinationRotX',
                     'destinationRotY', 'destinationRotZ'),
        MelRefrXloc('XLOC', 'B3sI4sB3s', 'lockLevel', ('unused1', null3),
                    (FID, 'lockKey'), ('unused2', null4),
                    (_lockFlags, 'lockFlags'), ('unused3', null3)),
        MelOwnership(),
        MelOptStruct('XESP','IB3s',(FID,'parent'),
                     (_parentFlags,'parentFlags'),('unused4',null3)),
        MelFid('XTRG','targetId'),
        MelBase('XSED','seed_p'),
        ####SpeedTree Seed, if it's a single byte then it's an offset into
        # the list of seed values in the TREE record
        ####if it's 4 byte it's the seed value directly.
        MelOptStruct('XLOD', '3f', ('lod1', None), ('lod2', None),
                     ('lod3', None)), # ###Distant LOD Data, unknown
        MelOptStruct('XCHG','f',('charge',None)),
        MelOptStruct('XHLT','i',('health',None)),
        MelXpci('XPCI'), ####fid, unknown
        MelOptStruct('XLCM','i',('levelMod',None)),
        MelFid('XRTM','xrtm'), ####unknown
        MelOptStruct('XACT','I',(_actFlags,'actFlags',0L)), ####Action Flag
        MelOptStruct('XCNT','i','count'),
        MelRefrXmrk('XMRK', '', ('hasXmrk', False), (_flags, 'flags', 0L),
                    'full', 'markerType', ('unused5', null1)),
        ####Map Marker Start Marker, wbEmpty
        MelBase('ONAM','onam_p'), ####Open by Default, wbEmpty
        MelBase('XRGD','xrgd_p'),
        MelOptStruct('XSCL','f',('scale',1.0)),
        MelOptStruct('XSOL', 'B', ('soul', None)),
        ####Was entirely missing. Confirmed by creating a test mod...it
        # isn't present in any of the official esps
        MelOptStruct('DATA', '=6f', ('posX', None), ('posY', None),
                     ('posZ', None), ('rotX', None), ('rotY', None),
                     ('rotZ', None)),
    )
    __slots__ = melSet.getSlotsUsed()

class MreRegn(MelRecord):
    """Region record."""
    classType = 'REGN'
    _flags = Flags(0L,Flags.getNames(
        ( 2,'objects'),
        ( 3,'weather'),
        ( 4,'map'),
        ( 6,'grass'),
        ( 7,'sound'),))
    obflags = Flags(0L,Flags.getNames(
        ( 0,'conform'),
        ( 1,'paintVertices'),
        ( 2,'sizeVariance'),
        ( 3,'deltaX'),
        ( 4,'deltaY'),
        ( 5,'deltaZ'),
        ( 6,'Tree'),
        ( 7,'hugeRock'),))
    sdflags = Flags(0L,Flags.getNames(
        ( 0,'pleasant'),
        ( 1,'cloudy'),
        ( 2,'rainy'),
        ( 3,'snowy'),))

    ####Lazy hacks to correctly read/write regn data
    class MelRegnStructA(MelStructA):
        """Handler for regn record. Conditionally dumps next items."""
        def loadData(self, record, ins, sub_type, size_, readId):
            if record.entryType == 2 and self.subType == 'RDOT':
                MelStructA.loadData(self, record, ins, sub_type, size_, readId)
            elif record.entryType == 3 and self.subType == 'RDWT':
                MelStructA.loadData(self, record, ins, sub_type, size_, readId)
            elif record.entryType == 6 and self.subType == 'RDGS':
                MelStructA.loadData(self, record, ins, sub_type, size_, readId)
            elif record.entryType == 7 and self.subType == 'RDSD':
                MelStructA.loadData(self, record, ins, sub_type, size_, readId)

        def dumpData(self,record,out):
            """Conditionally dumps data."""
            if record.entryType == 2 and self.subType == 'RDOT':
                MelStructA.dumpData(self,record,out)
            elif record.entryType == 3 and self.subType == 'RDWT':
                MelStructA.dumpData(self,record,out)
            elif record.entryType == 6 and self.subType == 'RDGS':
                MelStructA.dumpData(self,record,out)
            elif record.entryType == 7 and self.subType == 'RDSD':
                MelStructA.dumpData(self,record,out)

    class MelRegnString(MelString):
        """Handler for regn record. Conditionally dumps next items."""
        def loadData(self, record, ins, sub_type, size_, readId):
            if record.entryType == 4 and self.subType == 'RDMP':
                MelString.loadData(self, record, ins, sub_type, size_, readId)
            elif record.entryType == 5 and self.subType == 'ICON':
                MelString.loadData(self, record, ins, sub_type, size_, readId)

        def dumpData(self,record,out):
            """Conditionally dumps data."""
            if record.entryType == 4 and self.subType == 'RDMP':
                MelString.dumpData(self,record,out)
            elif record.entryType == 5 and self.subType == 'ICON':
                MelString.dumpData(self,record,out)

    class MelRegnOptStruct(MelOptStruct):
        """Handler for regn record. Conditionally dumps next items."""
        def loadData(self, record, ins, sub_type, size_, readId):
            if record.entryType == 7 and self.subType == 'RDMD':
                MelOptStruct.loadData(self, record, ins, sub_type, size_, readId)

        def dumpData(self,record,out):
            """Conditionally dumps data."""
            if record.entryType == 7 and self.subType == 'RDMD':
                MelOptStruct.dumpData(self,record,out)

    melSet = MelSet(
        MelString('EDID','eid'),
        MelString('ICON','iconPath'),
        MelStruct('RCLR','3Bs','mapRed','mapBlue','mapGreen',('unused1',null1)),
        MelFid('WNAM','worldspace'),
        MelGroups('areas',
            MelStruct('RPLI','I','edgeFalloff'),
            MelStructA('RPLD','2f','points','posX','posY')),
        MelGroups('entries',
                  MelStruct('RDAT', 'I2B2s', 'entryType', (_flags, 'flags'),
                            'priority', ('unused1', null2)),
                  ####flags actually an enum...
                  MelRegnStructA('RDOT', 'IH2sf4B2H4s4f3H2s4s', 'objects',
                                 (FID, 'objectId'), 'parentIndex',
            ('unused1',null2), 'density', 'clustering', 'minSlope', 'maxSlope',
            (obflags, 'flags'), 'radiusWRTParent', 'radius', ('unk1',null4),
            'maxHeight', 'sink', 'sinkVar', 'sizeVar', 'angleVarX',
            'angleVarY',  'angleVarZ', ('unused2',null2), ('unk2',null4)),
            MelRegnString('RDMP', 'mapName'),
## Disabled support due to bug when loading.
## Apparently group records can't contain subrecords that are also present
# outside of the group.
##          MelRegnString('ICON', 'iconPath'),  ####Obsolete? Only one
# record in oblivion.esm
            MelRegnStructA('RDGS', 'I4s', 'grasses', (FID,'grass'),
                           ('unk1',null4)),
            MelRegnOptStruct('RDMD', 'I', ('musicType',None)),
            MelRegnStructA('RDSD', '3I', 'sounds', (FID, 'sound'),
                           (sdflags, 'flags'), 'chance'),
            MelRegnStructA('RDWT', '2I', 'weather', (FID, 'weather'),
                           'chance')),
    )
    __slots__ = melSet.getSlotsUsed()

class MreRoad(MelRecord):
    """Road structure. Part of large worldspaces."""
    ####Could probably be loaded via MelStructA,
    ####but little point since it is too complex to manipulate
    classType = 'ROAD'
    melSet = MelSet(
        MelBase('PGRP','points_p'),
        MelBase('PGRR','connections_p'),
    )
    __slots__ = melSet.getSlotsUsed()

class MreSbsp(MelRecord):
    """Subspace record."""
    classType = 'SBSP'
    melSet = MelSet(
        MelString('EDID','eid'),
        MelStruct('DNAM','3f','sizeX','sizeY','sizeZ'),
    )
    __slots__ = melSet.getSlotsUsed()

class MreScpt(MelRecord):
    """Script record."""
    classType = 'SCPT'
    _flags = Flags(0L,Flags.getNames('isLongOrShort'))
    melSet = MelSet(
        MelString('EDID','eid'),
        MelStruct('SCHR','4s4I',('unused1',null4),'numRefs','compiledSize','lastIndex','scriptType'),
        #--Type: 0: Object, 1: Quest, 0x100: Magic Effect
        MelBase('SCDA','compiled_p'),
        MelString('SCTX','scriptText'),
        MelGroups('vars',
            MelStruct('SLSD','I12sB7s','index',('unused1',null4+null4+null4),(_flags,'flags',0L),('unused2',null4+null3)),
            MelString('SCVR','name')),
        MelScrxen('SCRV/SCRO','references'),
    )
    __slots__ = melSet.getSlotsUsed()

class MreSgst(MelRecord,MreHasEffects):
    """Sigil stone record."""
    classType = 'SGST'
    melSet = MelSet(
        MelString('EDID','eid'),
        MelFull0(),
        MelModel(),
        MelString('ICON','iconPath'),
        MelFid('SCRI','script'),
        MelEffects(),
        MelStruct('DATA','=BIf','uses','value','weight'),
        )
    __slots__ = melSet.getSlotsUsed()

class MreSkil(MelRecord):
    """Skill record."""
    classType = 'SKIL'
    melSet = MelSet(
        MelString('EDID','eid'),
        MelStruct('INDX','i','skill'),
        MelString('DESC','description'),
        MelString('ICON','iconPath'),
        MelStruct('DATA','2iI2f','action','attribute','specialization',('use0',1.0),'use1'),
        MelString('ANAM','apprentice'),
        MelString('JNAM','journeyman'),
        MelString('ENAM','expert'),
        MelString('MNAM','master'),
        )
    __slots__ = melSet.getSlotsUsed()

class MreSlgm(MelRecord):
    """Soul gem record."""
    classType = 'SLGM'
    melSet = MelSet(
        MelString('EDID','eid'),
        MelString('FULL','full'),
        MelModel(),
        MelString('ICON','iconPath'),
        MelFid('SCRI','script'),
        MelStruct('DATA','If','value','weight'),
        MelStruct('SOUL','B',('soul',0)),
        MelStruct('SLCP','B',('capacity',1)),
        )
    __slots__ = melSet.getSlotsUsed()

class MreSoun(MelRecord):
    """Sound record."""
    classType = 'SOUN'
    _flags = Flags(0L,Flags.getNames('randomFrequencyShift', 'playAtRandom',
        'environmentIgnored', 'randomLocation', 'loop','menuSound', '2d', '360LFE'))
    class MelSounSndd(MelStruct):
        """SNDD is an older version of SNDX. Allow it to read in, but not set defaults or write."""
        def loadData(self, record, ins, sub_type, size_, readId):
            MelStruct.loadData(self, record, ins, sub_type, size_, readId)
            record.staticAtten = 0
            record.stopTime = 0
            record.startTime = 0
        def getSlotsUsed(self):
            return ()
        def setDefault(self,record): return
        def dumpData(self,record,out): return
    melSet = MelSet(
        MelString('EDID','eid'),
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
    """Spell record."""
    classType = 'SPEL'
    class SpellFlags(Flags):
        """For SpellFlags, immuneSilence activates bits 1 AND 3."""
        def __setitem__(self,index,value):
            setter = Flags.__setitem__
            setter(self,index,value)
            if index == 1:
                setter(self,3,value)
    flags = SpellFlags(0L,Flags.getNames('noAutoCalc', 'immuneToSilence',
        'startSpell', None,'ignoreLOS','scriptEffectAlwaysApplies','disallowAbsorbReflect','touchExplodesWOTarget'))
    melSet = MelSet(
        MelString('EDID','eid'),
        MelFull0(),
        MelStruct('SPIT','3IB3s','spellType','cost','level',(flags,'flags',0L),('unused1',null3)),
        # spellType = 0: Spell, 1: Disease, 3: Lesser Power, 4: Ability, 5: Poison
        MelEffects(),
        )
    __slots__ = melSet.getSlotsUsed()

class MreStat(MelRecord):
    """Static model record."""
    classType = 'STAT'
    melSet = MelSet(
        MelString('EDID','eid'),
        MelModel(),
        )
    __slots__ = melSet.getSlotsUsed()

class MreTree(MelRecord):
    """Tree record."""
    classType = 'TREE'
    melSet = MelSet(
        MelString('EDID','eid'),
        MelModel(),
        MelString('ICON','iconPath'),
        MelStructA('SNAM','I','speedTree','seed'),
        MelStruct('CNAM','5fi2f', 'curvature','minAngle','maxAngle',
                  'branchDim','leafDim','shadowRadius','rockSpeed',
                  'rustleSpeed'),
        MelStruct('BNAM','2f','widthBill','heightBill'),
        )
    __slots__ = melSet.getSlotsUsed()

class MreWatr(MelRecord):
    """Water record."""
    classType = 'WATR'
    _flags = Flags(0L,Flags.getNames('causesDmg','reflective'))
    class MelWatrData(MelStruct):
        """Handle older truncated DATA for WATR subrecord."""
        def loadData(self, record, ins, sub_type, size_, readId):
            if size_ == 102:
                MelStruct.loadData(self, record, ins, sub_type, size_, readId)
                return
            elif size_ == 86:
                #--Else 86 byte record (skips dispVelocity,
                #-- dispFalloff, dispDampner, dispSize, and damage
                #-- Two junk? bytes are tacked onto the end
                #-- Hex editing and the CS confirms that it is NOT
                #-- damage, so it is probably just filler
                unpacked = ins.unpack('11f3Bs3Bs3BsB3s6f2s', size_, readId)
            elif size_ == 62:
                #--Else 62 byte record (skips most everything
                #-- Two junk? bytes are tacked onto the end
                #-- No testing done, but assumed that its the same as the
                #-- previous truncated record.
                unpacked = ins.unpack('11f3Bs3Bs3BsB3s2s', size_, readId)
            elif size_ == 42:
                #--Else 42 byte record (skips most everything
                #-- Two junk? bytes are tacked onto the end
                #-- No testing done, but assumed that its the same as the
                #-- previous truncated record.
                unpacked = ins.unpack('10f2s', size_, readId)
            elif size_ == 2:
                #--Else 2 byte record (skips everything
                #-- Two junk? bytes are tacked onto the end
                #-- No testing done, but assumed that its the same as the
                #-- previous truncated record.
                unpacked = ins.unpack('2s', size_, readId)
            else:
                raise ModError(ins.inName, _('Unexpected size encountered for WATR subrecord: %i') % size_)
            unpacked = unpacked[:-1]
            unpacked += self.defaults[len(unpacked):]
            setter = record.__setattr__
            for attr,value,action in zip(self.attrs,unpacked,self.actions):
                if callable(action): value = action(value)
                setter(attr,value)
            if self._debug: print unpacked

    melSet = MelSet(
        MelString('EDID','eid'),
        MelString('TNAM','texture'),
        MelStruct('ANAM','B','opacity'),
        MelStruct('FNAM','B',(_flags,'flags',0)),
        MelString('MNAM','material'),
        MelFid('SNAM','sound'),
        MelWatrData('DATA', '11f3Bs3Bs3BsB3s10fH',('windVelocity',0.100),
                    ('windDirection',90.0),('waveAmp',0.5),('waveFreq',1.0),('sunPower',50.0),
                    ('reflectAmt',0.5),('fresnelAmt',0.0250),('xSpeed',0.0),('ySpeed',0.0),
                    ('fogNear',27852.8),('fogFar',163840.0),('shallowRed',0),('shallowGreen',128),
                    ('shallowBlue',128),('unused1',null1),('deepRed',0),('deepGreen',0),
                    ('deepBlue',25),('unused2',null1),('reflRed',255),('reflGreen',255),
                    ('reflBlue',255),('unused3',null1),('blend',50),('unused4',null3),('rainForce',0.1000),
                    ('rainVelocity',0.6000),('rainFalloff',0.9850),('rainDampner',2.0000),
                    ('rainSize',0.0100),('dispForce',0.4000),('dispVelocity', 0.6000),
                    ('dispFalloff',0.9850),('dispDampner',10.0000),('dispSize',0.0500),('damage',0)),
        MelFidList('GNAM','relatedWaters'),
        )
    __slots__ = melSet.getSlotsUsed()

class MreWeap(MelRecord):
    """Weapon record."""
    classType = 'WEAP'
    _flags = Flags(0L,Flags.getNames('notNormalWeapon'))
    melSet = MelSet(
        MelString('EDID','eid'),
        MelString('FULL','full'),
        MelModel(),
        MelString('ICON','iconPath'),
        MelFid('SCRI','script'),
        MelFid('ENAM','enchantment'),
        MelOptStruct('ANAM','H','enchantPoints'),
        MelStruct('DATA','I2f3IfH','weaponType','speed','reach',(_flags,'flags',0L),
            'value','health','weight','damage'),
        #--weaponType = 0: Blade 1Hand, 1: Blade 2Hand, 2: Blunt 1Hand, 3: Blunt 2Hand, 4: Staff, 5: Bow
        )
    __slots__ = melSet.getSlotsUsed()

class MreWrld(MelRecord):
    """Worldspace record."""
    classType = 'WRLD'
    _flags = Flags(0L,Flags.getNames('smallWorld','noFastTravel','oblivionWorldspace',None,'noLODWater'))
    melSet = MelSet(
        MelString('EDID','eid'),
        MelString('FULL','full'),
        MelFid('WNAM','parent'),
        MelFid('CNAM','climate'),
        MelFid('NAM2','water'),
        MelString('ICON','mapPath'),
        MelOptStruct('MNAM','2i4h',('dimX',None),('dimY',None),('NWCellX',None),('NWCellY',None),('SECellX',None),('SECellY',None)),
        MelStruct('DATA','B',(_flags,'flags',0L)),
        MelTuple('NAM0','ff','unknown0',(None,None)),
        MelTuple('NAM9','ff','unknown9',(None,None)),
        MelOptStruct('SNAM','I','sound'),
        MelBase('OFST','ofst_p'),
    )
    __slots__ = melSet.getSlotsUsed()

class MreWthr(MelRecord):
    """Weather record."""
    classType = 'WTHR'
    melSet = MelSet(
        MelString('EDID','eid'),
        MelString('CNAM','lowerLayer'),
        MelString('DNAM','upperLayer'),
        MelModel(),
        MelStructA('NAM0','3Bs3Bs3Bs3Bs','colors','riseRed','riseGreen','riseBlue',('unused1',null1),
                   'dayRed','dayGreen','dayBlue',('unused2',null1),
                   'setRed','setGreen','setBlue',('unused3',null1),
                   'nightRed','nightGreen','nightBlue',('unused4',null1),
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
        MelStructs('SNAM','2I','sounds',(FID,'sound'),'type'),
        )
    __slots__ = melSet.getSlotsUsed()
