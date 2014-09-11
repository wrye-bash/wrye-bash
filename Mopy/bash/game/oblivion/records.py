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

#--Mod I/O
from ...bolt import StateError, Flags, BoltError, sio
from ...brec import MelRecord, BaseRecordHeader, ModError, MelStructs, null3, \
    null4, ModSizeError, MelObject, MelGroups, MelStruct, FID, MelGroup, \
    MelString, MreLeveledListBase, MelSet, MelFid, null2, MelNull, MelOptStruct, \
    MelFids, MreHeaderBase, MelBase, MelUnicode, MelXpci, MelModel, MelFull0
from ...bush import genericAVEffects, mgef_school, mgef_basevalue, actorValues
from oblivion_const import allConditions, fid1Conditions, fid2Conditions

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
        """Returns the record header packed into a string for writing to file."""
        if self.recType == 'GRUP':
            if isinstance(self.label,str):
                return struct.pack('=4sI4sII',self.recType,self.size,self.label,self.groupType,self.stamp)
            elif isinstance(self.label,tuple):
                return struct.pack('=4sIhhII',self.recType,self.size,self.label[0],self.label[1],self.groupType,self.stamp)
            else:
                return struct.pack('=4s4I',self.recType,self.size,self.label,self.groupType,self.stamp)
        else:
            return struct.pack('=4s4I',self.recType,self.size,self.flags1,self.fid,self.flags2)

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

#------------------------------------------------------------------------------
class MelBipedFlags(Flags):
    """Biped flags element. Includes biped flag set by default."""
    mask = 0xFFFF
    def __init__(self,default=0L,newNames=None):
        names = Flags.getNames('head', 'hair', 'upperBody', 'lowerBody', 'hand', 'foot', 'rightRing', 'leftRing', 'amulet', 'weapon', 'backWeapon', 'sideWeapon', 'quiver', 'shield', 'torch', 'tail')
        if newNames: names.update(newNames)
        Flags.__init__(self,default,names)

#------------------------------------------------------------------------------
class MelConditions(MelStructs):
    """Represents a set of quest/dialog conditions. Difficulty is that FID state
    of parameters depends on function index."""
    def __init__(self):
        """Initialize."""
        MelStructs.__init__(self,'CTDA','B3sfIii4s','conditions',
            'operFlag',('unused1',null3),'compValue','ifunc','param1','param2',('unused2',null4))

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
            MelStruct.__init__(self,'SCIT','II4sB3s',(FID,'script',None),('school',0),
                ('visual','\x00\x00\x00\x00'),(MelEffects.seFlags,'flags',0x0L),('unused1',null3))
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
                #--The script fid for MS40TestSpell doesn't point to a valid script.
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
            MelStruct('EFIT','4s4Ii',('name','REHE'),'magnitude','area','duration','recipient','actorValue'),
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
                        effectName = re.sub(_(u'(Attribute|Skill)'),aValues[effect.actorValue],effectName)
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
            format,attrs = ((self.format,self.attrs),('iI',('level','listId'),))[size==8]####might be h2sI
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
        MelLevListLvlo('LVLO','h2sIh2s','entries','level',('unused1',null2),(FID,'listId',None),('count',1),('unused2',null2)),
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

# Oblivion Records ------------------------------------------------------------
#------------------------------------------------------------------------------
#------------------------------------------------------------------------------
class MreHeader(MreHeaderBase):
    """TES4 Record.  File header."""
    classType = 'TES4'

    #--Data elements
    melSet = MelSet(
        MelStruct('HEDR','f2I',('version',0.8),'numRecords',('nextObject',0xCE6)),
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
        MelOptStruct('XLOD','3f',('lod1',None),('lod2',None),('lod3',None)), ####Distant LOD Data, unknown
        MelOptStruct('XESP','IB3s',(FID,'parent'),(_flags,'parentFlags'),('unused1',null3)),
        MelFid('XMRC','merchantContainer'),
        MelFid('XHRS','horse'),
        MelBase('XRGD','xrgd_p'), ###Ragdoll Data, ByteArray
        MelOptStruct('XSCL','f',('scale',1.0)),
        MelOptStruct('DATA','=6f',('posX',None),('posY',None),('posZ',None),('rotX',None),('rotY',None),('rotZ',None)),
    )
    __slots__ = MelRecord.__slots__ + melSet.getSlotsUsed()

class MreAcre(MelRecord): # Placed Creature
    classType = 'ACRE'
    _flags = Flags(0L,Flags.getNames('oppositeParent'))
    melSet=MelSet(
        MelString('EDID','eid'),
        MelFid('NAME','base'),
        MelOwnership(),
        MelOptStruct('XLOD','3f',('lod1',None),('lod2',None),('lod3',None)), ####Distant LOD Data, unknown
        MelOptStruct('XESP','IB3s',(FID,'parent'),(_flags,'parentFlags'),('unused1',null3)),
        MelBase('XRGD','xrgd_p'), ###Ragdoll Data, ByteArray
        MelOptStruct('XSCL','f',('scale',1.0)),
        MelOptStruct('DATA','=6f',('posX',None),('posY',None),('posZ',None),('rotX',None),('rotY',None),('rotZ',None)),
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
        MelStruct('DATA','fB3sIfH','speed',(_flags,'flags',0L),('unused1',null3),'value','weight','damage'),
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
        MelStruct('DATA','=BIff',('apparatus',0),('value',25),('weight',1),('quality',10)),
        )
    __slots__ = MelRecord.__slots__ + melSet.getSlotsUsed()

class MreArmo(MelRecord):
    """Armor record."""
    classType = 'ARMO'
    _flags = MelBipedFlags(0L,Flags.getNames((16,'hideRings'),(17,'hideAmulet'),(22,'notPlayable'),(23,'heavyArmor')))
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
        MelStruct('DATA', '=BbIf',(_flags,'flags',0L),('teaches',-1),'value','weight'),
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
