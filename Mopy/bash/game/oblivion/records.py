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
#  Wrye Bash copyright (C) 2005-2009 Wrye, 2010-2014 Wrye Bash Team
#  https://github.com/wrye-bash
#
# =============================================================================

"""This module contains the oblivion record classes. Ripped from oblivion.py"""
import re
import struct
from . import esp
from ...bolt import StateError, Flags, BoltError, sio
from ...brec import MelRecord, BaseRecordHeader, ModError, MelStructs, null3, \
    null4, ModSizeError, MelObject, MelGroups, MelStruct, FID, MelGroup, \
    MelString, MreLeveledListBase, MelSet, MelFid, null2, MelNull, \
    MelOptStruct, MelFids, MreHeaderBase, MelBase, MelUnicode, MelXpci, \
    MelModel, MelFull0, null1, MelFidList, MelStructA, MelStrings, MreRecord, \
    MreGmstBase
from ...bush import genericAVEffects, mgef_school, mgef_basevalue, actorValues
from oblivion_const import allConditions, fid1Conditions, fid2Conditions

#--Mod I/O
class RecordHeader(BaseRecordHeader):
    size = 20

    def __init__(self,recType='TES4',size=0,arg1=0,arg2=0,arg3=0,*extra):
        self.recType = recType
        self.size = size
        if recType == 'GRUP':
            self.label = arg1
            self.groupType = arg2
            self.stamp = arg3
        else:
            self.flags1 = arg1
            self.fid = arg2
            self.flags2 = arg2
        self.extra = extra

    @staticmethod
    def unpack(ins):
        """Returns a RecordHeader object by reading the input stream."""
        type,size,uint0,uint1,uint2 = ins.unpack('=4s4I',20,'REC_HEADER')
        #--Bad?
        if type not in esp.recordTypes:
            raise ModError(ins.inName,u'Bad header type: '+repr(type))
        #--Record
        if type != 'GRUP':
            pass
        #--Top Group
        elif uint1 == 0: # groupType == 0 (Top Group)
            str0 = struct.pack('I',uint0)
            if str0 in esp.topTypes:
                uint0 = str0
            elif str0 in esp.topIgTypes:
                uint0 = esp.topIgTypes[str0]
            else:
                raise ModError(ins.inName,u'Bad Top GRUP type: '+repr(str0))
        return RecordHeader(type,size,uint0,uint1,uint2)

    def pack(self):
        """Returns the record header packed into a string for writing to
        file."""
        if self.recType == 'GRUP':
            if isinstance(self.label, str):
                return struct.pack('=4sI4sII', self.recType, self.size,
                                   self.label, self.groupType, self.stamp)
            elif isinstance(self.label, tuple):
                return struct.pack('=4sIhhII', self.recType, self.size,
                                   self.label[0], self.label[1],
                                   self.groupType, self.stamp)
            else:
                return struct.pack('=4s4I', self.recType, self.size,
                                   self.label, self.groupType, self.stamp)
        else:
            return struct.pack('=4s4I', self.recType, self.size, self.flags1,
                               self.fid, self.flags2)

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

    def loadData(self,record,ins,type,size,readId):
        """Reads data from ins into record attribute."""
        if type == 'CTDA' and size != 24:
            raise ModSizeError(ins.inName,readId,24,size,True)
        if type == 'CTDT' and size != 20:
            raise ModSizeError(ins.inName,readId,20,size,True)
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
        if size == 24:
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
        def loadData(self,record,ins,type,size,readId):
            #--Alternate formats
            if size == 16:
                attrs,actions = self.attrs,self.actions
                unpacked = ins.unpack(self.format,size,readId)
            elif size == 12:
                attrs,actions = ('script','school','visual'),(0,0,0)
                unpacked = ins.unpack('II4s',size,readId)
                record.unused1 = null3
            else: #--size == 4
                # --The script fid for MS40TestSpell doesn't point to a
                # valid script.
                #--But it's not used, so... Not a problem! It's also t
                record.unused1 = null3
                attrs,actions = ('script',),(0,)
                unpacked = ins.unpack('I',size,readId)
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

class MreHasEffects:
    """Mixin class for magic items."""
    def getEffects(self):
        """Returns a summary of effects. Useful for alchemical catalog."""
        effects = []
        avEffects = genericAVEffects
        effectsAppend = effects.append
        for effect in self.effects:
            mgef, actorValue = effect.name, effect.actorValue
            if mgef not in avEffects:
                actorValue = 0
            effectsAppend((mgef,actorValue))
        return effects

    def getSpellSchool(self,mgef_school=mgef_school):
        """Returns the school based on the highest cost spell effect."""
        spellSchool = [0,0]
        for effect in self.effects:
            school = mgef_school[effect.name]
            effectValue = mgef_basevalue[effect.name]
            if effect.magnitude:
                effectValue *=  effect.magnitude
            if effect.area:
                effectValue *=  (effect.area/10)
            if effect.duration:
                effectValue *=  effect.duration
            if spellSchool[0] < effectValue:
                spellSchool = [effectValue,school]
        return spellSchool[1]

    def getEffectsSummary(self,mgef_school=None,mgef_name=None):
        """Return a text description of magic effects."""
        mgef_school = mgef_school or mgef_school
        mgef_name = mgef_name or mgef_name
        with sio() as buff:
            avEffects = genericAVEffects
            aValues = actorValues
            buffWrite = buff.write
            if self.effects:
                school = self.getSpellSchool(mgef_school)
                buffWrite(actorValues[20+school] + u'\n')
            for index,effect in enumerate(self.effects):
                if effect.scriptEffect:
                    effectName = effect.scriptEffect.full or u'Script Effect'
                else:
                    effectName = mgef_name[effect.name]
                    if effect.name in avEffects:
                        effectName = re.sub(_(u'(Attribute|Skill)'),
                                            aValues[effect.actorValue],
                                            effectName)
                buffWrite(u'o+*'[effect.recipient]+u' '+effectName)
                if effect.magnitude: buffWrite(u' %sm'%effect.magnitude)
                if effect.area: buffWrite(u' %sa'%effect.area)
                if effect.duration > 1: buffWrite(u' %sd'%effect.duration)
                buffWrite(u'\n')
                return buff.getvalue()

class MreLeveledList(MreLeveledListBase):
    """Leveled item/creature/spell list.."""
    copyAttrs = ('script','template','chanceNone',)

    #--Special load classes
    class MelLevListLvld(MelStruct):
        """Subclass to support alternate format."""
        def loadData(self,record,ins,type,size,readId):
            MelStruct.loadData(self,record,ins,type,size,readId)
            if record.chanceNone > 127:
                record.flags.calcFromAllLevels = True
                record.chanceNone &= 127

    class MelLevListLvlo(MelStructs):
        """Subclass to support alternate format."""
        def loadData(self,record,ins,type,size,readId):
            target = self.getDefault()
            record.__getattribute__(self.attr).append(target)
            target.__slots__ = self.attrs
            format, attrs = \
                ((self.format, self.attrs), ('iI', ('level', 'listId'),))[
                    size == 8]  # ###might be h2sI
            unpacked = ins.unpack(format,size,readId)
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
    __slots__ = MreLeveledListBase.__slots__ + melSet.getSlotsUsed()

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

    def loadData(self,record,ins,type,size,readId):
        isFid = (type == 'SCRO')
        if isFid: value = ins.unpackRef(readId)
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
    __slots__ = MreHeaderBase.__slots__ + melSet.getSlotsUsed()

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
    __slots__ = MelRecord.__slots__ + melSet.getSlotsUsed()

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
    __slots__ = MelRecord.__slots__ + melSet.getSlotsUsed()

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
    __slots__ = MelRecord.__slots__ + melSet.getSlotsUsed()

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
    __slots__ = MelRecord.__slots__ + melSet.getSlotsUsed()

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
    __slots__ = MelRecord.__slots__ + melSet.getSlotsUsed()

class MreAnio(MelRecord):
    """Animation object record."""
    classType = 'ANIO'
    melSet = MelSet(
        MelString('EDID','eid'),
        MelModel(),
        MelFid('DATA','animationId'),
        )
    __slots__ = MelRecord.__slots__ + melSet.getSlotsUsed()

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
    __slots__ = MelRecord.__slots__ + melSet.getSlotsUsed()

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
    __slots__ = MelRecord.__slots__ + melSet.getSlotsUsed()

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
    __slots__ = MelRecord.__slots__ + melSet.getSlotsUsed() + ['modb']

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
    __slots__ = MelRecord.__slots__ + melSet.getSlotsUsed()

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
    __slots__ = MelRecord.__slots__ + melSet.getSlotsUsed()

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
        def loadData(self,record,ins,type,size,readId):
            if size == 52:
                MelStruct.loadData(self,record,ins,type,size,readId)
                return
            #--Else 42 byte record (skips trainSkill, trainLevel,unused1...
            unpacked = ins.unpack('2iI7i2I',size,readId)
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
    __slots__ = MelRecord.__slots__ + melSet.getSlotsUsed()

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
    __slots__ = MelRecord.__slots__ + melSet.getSlotsUsed()

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
    __slots__ = MelRecord.__slots__ + melSet.getSlotsUsed()

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
    __slots__ = MelRecord.__slots__ + melSet.getSlotsUsed()

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
        def loadData(self,record,ins,type,size,readId):
            if size == 124:
                MelStruct.loadData(self,record,ins,type,size,readId)
                return
            elif size == 120:
                #--Else 120 byte record (skips flagsB
                unpacked = ins.unpack('2B2s8f2B2s3fB3s2f5B3s2f2B2s7fB3sf',
                                      size, readId)
            elif size == 112:
                #--112 byte record (skips flagsB, rushChance, unused6, rushMult
                unpacked = ins.unpack('2B2s8f2B2s3fB3s2f5B3s2f2B2s7f', size,
                                      readId)
            elif size == 104:
                # --104 byte record (skips flagsB, rushChance, unused6,
                #  rushMult, rStand, groupStand
                #-- only one occurence (AndragilTraining
                unpacked = ins.unpack('2B2s8f2B2s3fB3s2f5B3s2f2B2s5f', size,
                                      readId)
            elif size == 92:
                #--92 byte record (skips flagsB, rushChance, unused6, rushMult,
                #  rStand, groupStand mDistance, rDistance, buffStand
                #-- These records keep getting shorter and shorter...
                #-- This one is used by quite a few npcs
                unpacked = ins.unpack('2B2s8f2B2s3fB3s2f5B3s2f2B2s2f', size,
                                      readId)
            elif size == 84:
                #--84 byte record (skips flagsB, rushChance, unused6, rushMult,
                #  rStand, groupStand mDistance, rDistance, buffStand,
                #  rMultOpt, rMultMax
                #-- This one is present once: VidCaptureNoAttacks and it
                # isn't actually used.
                unpacked = ins.unpack('2B2s8f2B2s3fB3s2f5B3s2f2B2s', size,
                                      readId)
            else:
                raise ModError(ins.inName,
                               u'Unexpected size encountered for CSTD '
                               u'subrecord: %i' % size)
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
    __slots__ = MelRecord.__slots__ + melSet.getSlotsUsed()

class MreDial(MelRecord):
    """Dialog record."""
    classType = 'DIAL'
    melSet = MelSet(
        MelString('EDID','eid'),
        MelFids('QSTI','quests'), ### QSTRs?
        MelString('FULL','full'),
        MelStruct('DATA','B','dialType'),
    )
    __slots__ = MelRecord.__slots__ + melSet.getSlotsUsed() + ['infoStamp',
                                                               'infos']

    def __init__(self,header,ins=None,unpack=False):
        """Initialize."""
        MelRecord.__init__(self,header,ins,unpack)
        self.infoStamp = 0 #--Stamp for info GRUP
        self.infos = []

    def loadInfos(self,ins,endPos,infoClass):
        """Load infos from ins. Called from MobDials."""
        infos = self.infos
        recHead = ins.unpackRecHeader
        infosAppend = infos.append
        while not ins.atEnd(endPos,'INFO Block'):
            #--Get record info and handle it
            header = recHead()
            recType = header.recType
            if recType == 'INFO':
                info = infoClass(header,ins,True)
                infosAppend(info)
            else:
                raise ModError(ins.inName,u'Unexpected %s record in %s group.'
                    % (recType,"INFO"))

    def dump(self,out):
        """Dumps self., then group header and then records."""
        MreRecord.dump(self,out)
        if not self.infos: return
        # Magic number '20': size of Oblivion's record header
        # Magic format '4sIIII': format for Oblivion's GRUP record
        size = 20 + sum([20 + info.getSize() for info in self.infos])
        out.pack('4sIIII','GRUP',size,self.fid,7,self.infoStamp)
        for info in self.infos: info.dump(out)

    def updateMasters(self,masters):
        """Updates set of master names according to masters actually used."""
        MelRecord.updateMasters(self,masters)
        for info in self.infos:
            info.updateMasters(masters)

    def convertFids(self,mapper,toLong):
        """Converts fids between formats according to mapper.
        toLong should be True if converting to long format or False if
        converting to short format."""
        MelRecord.convertFids(self,mapper,toLong)
        for info in self.infos:
            info.convertFids(mapper,toLong)

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
    __slots__ = MelRecord.__slots__ + melSet.getSlotsUsed()

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
        def loadData(self,record,ins,type,size,readId):
            if size == 224:
                MelStruct.loadData(self,record,ins,type,size,readId)
                return
            elif size == 96:
                #--Else 96 byte record (skips particle variables, and color
                # keys. Only used twice in test shaders (0004b6d5, 0004b6d6)
                unpacked = ins.unpack('B3s3I3Bs9f3Bs8fI',size,readId)
            else:
                raise ModError(ins.inName,
                               u'Unexpected size encountered for EFSH '
                               u'subrecord: %i' % size)
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
    __slots__ = MelRecord.__slots__ + melSet.getSlotsUsed()

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
    __slots__ = MelRecord.__slots__ + melSet.getSlotsUsed()

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
    __slots__ = MelRecord.__slots__ + melSet.getSlotsUsed()

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
    __slots__ = MelRecord.__slots__ + melSet.getSlotsUsed()

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
    __slots__ = MelRecord.__slots__ + melSet.getSlotsUsed()

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
    __slots__ = MelRecord.__slots__ + melSet.getSlotsUsed()

class MreGmst(MreGmstBase):
    """Oblivion gmst record"""
    Master = u'Oblivion'

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
    __slots__ = MelRecord.__slots__ + melSet.getSlotsUsed()

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
    __slots__ = MelRecord.__slots__ + melSet.getSlotsUsed()

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
    __slots__ = MelRecord.__slots__ + melSet.getSlotsUsed()

class MreInfo(MelRecord):
    """Info (dialog entry) record."""
    classType = 'INFO'
    _flags = Flags(0, Flags.getNames('goodbye', 'random', 'sayOnce',
                                     'runImmediately', 'infoRefusal',
                                     'randomEnd', 'runForRumors'))
    class MelInfoData(MelStruct):
        """Support truncated 2 byte version."""
        def loadData(self,record,ins,type,size,readId):
            if size != 2:
                MelStruct.loadData(self,record,ins,type,size,readId)
                return
            unpacked = ins.unpack('H',size,readId)
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
    __slots__ = MelRecord.__slots__ + melSet.getSlotsUsed()

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
    __slots__ = MelRecord.__slots__ + melSet.getSlotsUsed()

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
    __slots__ = MelRecord.__slots__ + melSet.getSlotsUsed()
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
##    __slots__ = MelRecord.__slots__ + melSet.getSlotsUsed()
#------------------------------------------------------------------------------
