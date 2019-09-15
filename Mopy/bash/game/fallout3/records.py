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
"""This module contains the fallout3 record classes. You must import from it
__once__ only in game.fallout3.Fallout3GameInfo#init. No other game.records
file must be imported till then."""
import itertools
import struct
from operator import attrgetter
from ... import brec
from ... import bush
from ...bass import null1, null2, null3, null4
from ...bolt import Flags, DataDict, GPath, struct_unpack, struct_pack
from ...brec import MelRecord, MelStructs, MelObject, MelGroups, MelStruct, \
    FID, MelGroup, MelString, MelSet, MelFid, MelNull, MelOptStruct, MelFids, \
    MreHeaderBase, MelBase, MelUnicode, MelFidList, MelStructA, MreGmstBase, \
    MelStrings, MelFull0, MelTuple, MelMODS, MreHasEffects
from ...exception import BoltError, ModError, ModSizeError, StateError
# Set MelModel in brec but only if unset
if brec.MelModel is None:
    class _MelModel(brec.MelGroup):
        """Represents a model record."""
        typeSets = (('MODL', 'MODB', 'MODT', 'MODS', 'MODD'),
                    ('MOD2', 'MO2B', 'MO2T', 'MO2S', 'MO2D'),
                    ('MOD3', 'MO3B', 'MO3T', 'MO3S', 'MOSD'),
                    ('MOD4', 'MO4B', 'MO4T', 'MO4S', 'MO4D'),)

        def __init__(self, attr='model', index=0):
            """Initialize. Index is 0,2,3,4 for corresponding type id."""
            types = self.__class__.typeSets[(0, index - 1)[index > 0]]
            MelGroup.__init__(self, attr, MelString(types[0], 'modPath'),
                              MelBase(types[1], 'modb_p'),
                              ### Bound Radius, Float
                              MelBase(types[2], 'modt_p'),
                              ###Texture Files Hashes, Byte Array
                              MelMODS(types[3], 'alternateTextures'),
                              MelBase(types[4], 'modd_p'), )

        def debug(self, on=True):
            """Sets debug flag on self."""
            for element in self.elements[:2]: element.debug(on)
            return self
    brec.MelModel = _MelModel

from ...brec import MelModel

from_iterable = itertools.chain.from_iterable

#------------------------------------------------------------------------------
# Record Elements    ----------------------------------------------------------
#------------------------------------------------------------------------------
class MreActor(MelRecord):
    """Creatures and NPCs."""

    def mergeFilter(self,modSet):
        """Filter out items that don't come from specified modSet.
        Filters spells, factions and items."""
        if not self.longFids: raise StateError(_("Fids not in long format"))
        self.spells = [x for x in self.spells if x[0] in modSet]
        self.factions = [x for x in self.factions if x.faction[0] in modSet]
        self.items = [x for x in self.items if x.item[0] in modSet]

#------------------------------------------------------------------------------
class MelBipedFlags(Flags):
    """Biped flags element. Includes biped flag set by default."""
    mask = 0xFFFF
    def __init__(self,default=0L,newNames=None):
        names = Flags.getNames(
            'head', 'hair', 'upperBody', 'leftHand', 'rightHand', 'weapon',
            'pipboy', 'backpack', 'necklace', 'headband', 'hat', 'eyeGlasses',
            'noseRing', 'earrings', 'mask', 'choker', 'mouthObject',
            'bodyAddOn1', 'bodyAddOn2', 'bodyAddOn3')
        if newNames: names.update(newNames)
        Flags.__init__(self,default,names)

#------------------------------------------------------------------------------
class MelConditions(MelStructs):
    """Represents a set of quest/dialog conditions. Difficulty is that FID state
    of parameters depends on function index."""
    def __init__(self):
        """Initialize."""
        MelStructs.__init__(self,'CTDA','=B3sfH2siiII','conditions',
            'operFlag',('unused1',null3),'compValue','ifunc',('unused2',null2),
            'param1','param2','runOn','reference')

    def getDefault(self):
        """Returns a default copy of object."""
        target = MelStructs.getDefault(self)
        target.form1234 = 'iiII'
        return target

    def hasFids(self,formElements):
        """Include self if has fids."""
        formElements.add(self)

    def loadData(self, record, ins, sub_type, size_, readId):
        """Reads data from ins into record attribute."""
        if sub_type == 'CTDA':
            if size_ != 28 and size_ != 24 and size_ != 20:
                raise ModSizeError(ins.inName, readId, 28, size_, False)
        else:
            raise ModError(ins.inName,_(u'Unexpected subrecord: ')+readId)
        target = MelObject()
        record.conditions.append(target)
        target.__slots__ = self.attrs
        unpacked1 = ins.unpack('=B3sfH2s',12,readId)
        (target.operFlag,target.unused1,target.compValue,ifunc,target.unused2) = unpacked1
        #--Get parameters
        if ifunc not in bush.game.allConditions:
            raise BoltError(u'Unknown condition function: %d\nparam1: %08X\nparam2: %08X' % (ifunc,ins.unpackRef(), ins.unpackRef()))
        # Form1 is Param1
        form1 = 'I' if ifunc in bush.game.fid1Conditions else 'i'
        # Form2 is Param2
        form2 = 'I' if ifunc in bush.game.fid2Conditions else 'i'
        # Form3 is runOn
        form3 = 'I'
        # Form4 is reference, this is a formID when runOn = 2
        form4 = 'I'
        if size_ == 28:
            form1234 = form1+form2+form3+form4
            unpacked2 = ins.unpack(form1234,16,readId)
            (target.param1,target.param2,target.runOn,target.reference) = unpacked2
        elif size_ == 24:
            form1234 = form1+form2+form3
            unpacked2 = ins.unpack(form1234,12,readId)
            (target.param1,target.param2,target.runOn) = unpacked2
            target.reference = null4
        elif size_ == 20:
            form1234 = form1+form2
            unpacked2 = ins.unpack(form1234,8,readId)
            (target.param1,target.param2) = unpacked2
            target.runOn = null4
            target.reference = null4
        else:
            raise ModSizeError(ins.inName, readId, 28, size_, False)
        (target.ifunc,target.form1234) = (ifunc,form1234)
        if self._debug:
            unpacked = unpacked1+unpacked2
            print u' ',zip(self.attrs,unpacked)
            if len(unpacked) != len(self.attrs):
                print u' ',unpacked

    def dumpData(self,record,out):
        """Dumps data from record to outstream."""
        for target in record.conditions:
            out.packSub('CTDA','=B3sfH2s'+target.form1234,
                target.operFlag, target.unused1, target.compValue,
                target.ifunc, target.unused2, target.param1, target.param2,
                target.runOn, target.reference)

    def mapFids(self,record,function,save=False):
        """Applies function to fids. If save is true, then fid is set
        to result of function."""
        for target in record.conditions:
            form1234 = target.form1234
            if form1234[0] == 'I':
                result = function(target.param1)
                if save: target.param1 = result
            if form1234[1] == 'I':
                result = function(target.param2)
                if save: target.param2 = result
            # runOn is intU32, never FID, and Enum in FO3Edit/FNVEdit
            #0:Subject,1:Target,2:Reference,3:Combat Target,4:Linked Reference
            if len(form1234) > 3 and form1234[3] == 'I' and target.runOn == 2:
                result = function(target.reference)
                if save: target.reference = result

#------------------------------------------------------------------------------
class MelDestructible(MelGroup):
    """Represents a set of destruct record."""

    MelDestVatsFlags = Flags(0L,Flags.getNames(
        (0, 'vatsTargetable'),
        ))

    MelDestStageFlags = Flags(0L,Flags.getNames(
        (0, 'capDamage'),
        (1, 'disable'),
        (2, 'destroy'),
        ))

    def __init__(self,attr='destructible'):
        """Initialize elements."""
        MelGroup.__init__(self,attr,
            MelStruct('DEST','i2B2s','health','count',
                     (MelDestructible.MelDestVatsFlags,'flagsDest',0L),'unused'),
            MelGroups('stages',
                MelStruct('DSTD','=4Bi2Ii','health','index','damageStage',
                          (MelDestructible.MelDestStageFlags,'flagsDest',0L),'selfDamagePerSecond',
                          (FID,'explosion',None),(FID,'debris',None),'debrisCount'),
                MelString('DMDL','model'),
                MelBase('DMDT','dmdt'),
                MelBase('DSTF','footer'),
                ),
        )

#------------------------------------------------------------------------------
class MelEffects(MelGroups):
    """Represents ingredient/potion/enchantment/spell effects."""

    def __init__(self,attr='effects'):
        """Initialize elements."""
        MelGroups.__init__(self,attr,
            MelFid('EFID','baseEffect'),
            MelStruct('EFIT','4Ii','magnitude','area','duration','recipient','actorValue'),
            MelConditions(),
            )

#------------------------------------------------------------------------------
class MreLeveledList(MelRecord):
    """Leveled item/creature/spell list.."""
    _flags = Flags(0,Flags.getNames('calcFromAllLevels','calcForEachItem','useAllSpells'))
    #--Special load classes
    class MelLevListLvld(MelStruct):
        """Subclass to support alternate format."""
        def loadData(self, record, ins, sub_type, size_, readId):
            MelStruct.loadData(self, record, ins, sub_type, size_, readId)
            if record.chanceNone > 127:
                record.flags.calcFromAllLevels = True
                record.chanceNone &= 127

    class MelLevListLvlo(MelStruct):
        """Subclass to support alternate format."""
        def loadData(self, record, ins, sub_type, size_, readId):
            if size_ == 12:
                MelStruct.loadData(self, record, ins, sub_type, size_, readId)
                return
            elif size_ == 8:
                format,attrs = ('iI',('level','listId'))####might be h2sI
            else:
                raise "Unexpected size encountered for LVLO subrecord: %s" % size_
            unpacked = ins.unpack(format, size_, readId)
            setter = record.__setattr__
            for attr,value,action in zip(attrs,unpacked,self.actions):
                if callable(action): value = action(value)
                setter(attr,value)
            if self._debug: print unpacked
    #--Element Set
    melSet = MelSet(
        MelString('EDID','eid'),
        MelStruct('OBND','=6h',
                  'boundX1','boundY1','boundZ1',
                  'boundX2','boundY2','boundZ2'),
        MelLevListLvld('LVLD','B','chanceNone'),
        MelStruct('LVLF','B',(_flags,'flags',0L)),
        MelFid('SCRI','script'),
        MelFid('TNAM','template'),
        MelFid('LVLG','glob'),
        MelGroups('entries',
                  MelLevListLvlo('LVLO','h2sIh2s','level',('unused1',null2),(FID,'listId',None),('count',1),('unused2',null2)),
                  MelOptStruct('COED','IIf',(FID,'owner',None),(FID,'glob',None),('condition',1.0)),
                  ),
        MelModel(),
        )
    __slots__ = melSet.getSlotsUsed() + ['mergeOverLast', 'mergeSources',
                                         'items', 'delevs', 'relevs']

    def __init__(self, header, ins=None, do_unpack=False):
        """Initialize."""
        MelRecord.__init__(self, header, ins, do_unpack)
        self.mergeOverLast = False #--Merge overrides last mod merged
        self.mergeSources = None #--Set to list by other functions
        self.items  = None #--Set of items included in list
        self.delevs = None #--Set of items deleted by list (Delev and Relev mods)
        self.relevs = None #--Set of items relevelled by list (Relev mods)

    def mergeFilter(self,modSet):
        """Filter out items that don't come from specified modSet."""
        if not self.longFids: raise StateError(_("Fids not in long format"))
        self.entries = [entry for entry in self.entries if entry.listId[0] in modSet]

    def mergeWith(self,other,otherMod):
        """Merges newLevl settings and entries with self.
        Requires that: self.items, other.delevs and other.relevs be defined."""
        if not self.longFids: raise StateError(_("Fids not in long format"))
        if not other.longFids: raise StateError(_("Fids not in long format"))
        #--Relevel or not?
        if other.relevs:
            self.chanceNone = other.chanceNone
            self.script = other.script
            self.template = other.template
            self.flags = other.flags()
            self.glob = other.glob
        else:
            self.chanceNone = other.chanceNone or self.chanceNone
            self.script   = other.script or self.script
            self.template = other.template or self.template
            self.flags |= other.flags
            self.glob = other.glob or self.glob
        #--Remove items based on other.removes
        if other.delevs or other.relevs:
            removeItems = self.items & (other.delevs | other.relevs)
            self.entries = [entry for entry in self.entries if entry.listId not in removeItems]
            self.items = (self.items | other.delevs) - other.relevs
        hasOldItems = bool(self.items)
        #--Add new items from other
        newItems = set()
        entriesAppend = self.entries.append
        newItemsAdd = newItems.add
        for entry in other.entries:
            if entry.listId not in self.items:
                entriesAppend(entry)
                newItemsAdd(entry.listId)
        if newItems:
            self.items |= newItems
            self.entries.sort(key=attrgetter('listId','level','count','owner','condition'))
        #--Is merged list different from other? (And thus written to patch.)
        if (self.chanceNone != other.chanceNone or
            self.script != other.script or
            self.template != other.template or
            #self.flags != other.flags or
            self.glob != other.glob or
            len(self.entries) != len(other.entries)
            ):
            self.mergeOverLast = True
        else:
            otherlist = other.entries
            otherlist.sort(key=attrgetter('listId','level','count','owner','condition'))
            for selfEntry,otherEntry in zip(self.entries,otherlist):
                if (selfEntry.listId != otherEntry.listId or
                    selfEntry.level != otherEntry.level or
                    selfEntry.count != otherEntry.count or
                    selfEntry.owner != otherEntry.owner or
                    selfEntry.condition != otherEntry.condition):
                    self.mergeOverLast = True
                    break
            else:
                self.mergeOverLast = False
        if self.mergeOverLast:
            self.mergeSources.append(otherMod)
        else:
            self.mergeSources = [otherMod]
        #--Done
        self.setChanged(self.mergeOverLast)

#------------------------------------------------------------------------------
class MelOwnership(MelGroup):
    """Handles XOWN, XRNK, and XGLB for cells and cell children."""

    def __init__(self,attr='ownership'):
        """Initialize."""
        MelGroup.__init__(self,attr,
            MelFid('XOWN','owner'),
            MelOptStruct('XRNK','i',('rank',None)),
            # Double check XGLB it's not used in FO3Edit/FNVEdit
            MelFid('XGLB','global'),
        )

    def dumpData(self,record,out):
        """Dumps data from record to outstream."""
        if record.ownership and record.ownership.owner:
            MelGroup.dumpData(self,record,out)

#------------------------------------------------------------------------------
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
# Fallout3 Records ------------------------------------------------------------
#------------------------------------------------------------------------------
class MreHeader(MreHeaderBase):
    """TES4 Record.  File header."""
    classType = 'TES4'

    #--Data elements
    melSet = MelSet(
        MelStruct('HEDR','f2I',('version',0.94),'numRecords',('nextObject',0xCE6)),
        MelBase('OFST','ofst_p',),  #--Obsolete?
        MelBase('DELE','dele_p',),  #--Obsolete?
        MelUnicode('CNAM','author',u'',512),
        MelUnicode('SNAM','description',u'',512),
        MreHeaderBase.MelMasterName('MAST','masters'),
        MelNull('DATA'), # 8 Bytes in Length
        MelFidList('ONAM','overrides'),
        MelBase('SCRN', 'scrn_p'),
        )
    __slots__ = melSet.getSlotsUsed()

#------------------------------------------------------------------------------
class MreAchr(MelRecord):
    """Placed NPC"""
    classType = 'ACHR'
    _flags = Flags(0L,Flags.getNames('oppositeParent','popIn'))
    _variableFlags = Flags(0L,Flags.getNames('isLongOrShort'))
    melSet=MelSet(
        MelString('EDID','eid'),
        MelFid('NAME','base'),
        MelFid('XEZN','encounterZone'),
        MelBase('XRGD','ragdollData'),
        MelBase('XRGB','ragdollBipedData'),
        MelGroup('patrolData',
            MelStruct('XPRD','f','idleTime'),
            MelBase('XPPA','patrolScriptMarker'),
            MelFid('INAM', 'idle'),
            MelStruct('SCHR','4s4I',('unused1',null4),'numRefs','compiledSize','lastIndex','scriptType'),
            MelBase('SCDA','compiled_p'),
            MelString('SCTX','scriptText'),
            MelGroups('vars',
                MelStruct('SLSD','I12sB7s','index',('unused1',null4+null4+null4),(_variableFlags,'flags',0L),('unused2',null4+null3)),
                MelString('SCVR','name')),
            MelScrxen('SCRV/SCRO','references'),
            MelFid('TNAM','topic'),
            ),
        MelStruct('XLCM','i','levelModifier'),
        MelFid('XMRC','merchantContainer',),
        MelStruct('XCNT','i','count'),
        MelStruct('XRDS','f','radius',),
        MelStruct('XHLP','f','health',),
        MelStructs('XDCR','II','linkedDecals',(FID,'reference'),'unknown'), # ??
        MelFid('XLKR','linkedReference'),
        MelOptStruct('XCLP','8B','linkStartColorRed','linkStartColorGreen','linkStartColorBlue',('linkColorUnused1',null1),
                     'linkEndColorRed','linkEndColorGreen','linkEndColorBlue',('linkColorUnused2',null1)),
        MelGroup('activateParents',
            MelStruct('XAPD','B','flags'),
            MelStructs('XAPR','If','activateParentRefs',(FID,'reference'),'delay')
            ),
        MelOptStruct('XESP','IB3s',(FID,'parent'),(_flags,'parentFlags'),('unused1',null3)),
        MelOptStruct('XEMI','I',(FID,'emittance')),
        MelFid('XMBR','multiboundReference'),
        MelBase('XIBS','ignoredBySandbox'),
        MelOptStruct('XSCL','f',('scale',1.0)),
        MelOptStruct('DATA','=6f',('posX',None),('posY',None),('posZ',None),('rotX',None),('rotY',None),('rotZ',None)),
    )
    __slots__ = melSet.getSlotsUsed()

#------------------------------------------------------------------------------
class MreAcre(MelRecord):
    """Placed Creature"""
    classType = 'ACRE'
    _flags = Flags(0L,Flags.getNames('oppositeParent','popIn'))
    _variableFlags = Flags(0L,Flags.getNames('isLongOrShort'))
    melSet=MelSet(
        MelString('EDID','eid'),
        MelFid('NAME','base'),
        MelFid('XEZN','encounterZone'),
        MelBase('XRGD','ragdollData'),
        MelBase('XRGB','ragdollBipedData'),
        MelGroup('patrolData',
            MelStruct('XPRD','f','idleTime'),
            MelBase('XPPA','patrolScriptMarker'),
            MelFid('INAM', 'idle'),
            MelStruct('SCHR','4s4I',('unused1',null4),'numRefs','compiledSize','lastIndex','scriptType'),
            MelBase('SCDA','compiled_p'),
            MelString('SCTX','scriptText'),
            MelGroups('vars',
                MelStruct('SLSD','I12sB7s','index',('unused1',null4+null4+null4),(_variableFlags,'flags',0L),('unused2',null4+null3)),
                MelString('SCVR','name')),
            MelScrxen('SCRV/SCRO','references'),
            MelFid('TNAM','topic'),
            ),
        MelStruct('XLCM','i','levelModifier'),
        MelOwnership(),
        MelFid('XMRC','merchantContainer'),
        MelStruct('XCNT','i','count'),
        MelStruct('XRDS','f','radius',),
        MelStruct('XHLP','f','health',),
        MelStructs('XDCR','II','linkedDecals',(FID,'reference'),'unknown'), # ??
        MelFid('XLKR','linkedReference'),
        MelOptStruct('XCLP','8B','linkStartColorRed','linkStartColorGreen','linkStartColorBlue',('linkColorUnused1',null1),
                     'linkEndColorRed','linkEndColorGreen','linkEndColorBlue',('linkColorUnused2',null1)),
        MelGroup('activateParents',
            MelStruct('XAPD','B','flags'),
            MelStructs('XAPR','If','activateParentRefs',(FID,'reference'),'delay')
            ),
        MelOptStruct('XESP','IB3s',(FID,'parent'),(_flags,'parentFlags'),('unused1',null3)),
        MelOptStruct('XEMI','I',(FID,'emittance')),
        MelFid('XMBR','multiboundReference'),
        MelBase('XIBS','ignoredBySandbox'),
        MelOptStruct('XSCL','f',('scale',1.0)),
        MelOptStruct('DATA','=6f',('posX',None),('posY',None),('posZ',None),('rotX',None),('rotY',None),('rotZ',None)),
    )
    __slots__ = melSet.getSlotsUsed()

#------------------------------------------------------------------------------
class MreActi(MelRecord):
    """Activator record."""
    classType = 'ACTI'
    melSet = MelSet(
        MelString('EDID','eid'),
        MelStruct('OBND','=6h',
                  'boundX1','boundY1','boundZ1',
                  'boundX2','boundY2','boundZ2'),
        MelString('FULL','full'),
        MelModel(),
        MelFid('SCRI','script'),
        MelDestructible(),
        MelFid('SNAM','soundLooping'),
        MelFid('VNAM','soundActivation'),
        MelFid('RNAM','radioStation'),
        MelFid('WNAM','waterType'),
        )
    __slots__ = melSet.getSlotsUsed()

#------------------------------------------------------------------------------
class MreAddn(MelRecord):
    """Addon"""
    classType = 'ADDN'
    melSet = MelSet(
        MelString('EDID','eid'),
        MelStruct('OBND','=6h',
                  'boundX1','boundY1','boundZ1',
                  'boundX2','boundY2','boundZ2'),
        MelModel(),
        MelStruct('DATA','i','nodeIndex'),
        MelOptStruct('SNAM','I',(FID,'ambientSound')),
        MelStruct('DNAM','H2s','mastPartSysCap','unknown',),
        )
    __slots__ = melSet.getSlotsUsed()

#------------------------------------------------------------------------------
class MreAlch(MelRecord,MreHasEffects):
    """ALCH (potion) record."""
    classType = 'ALCH'
    _flags = Flags(0L,Flags.getNames('autoCalc','isFood','medicine',))
    melSet = MelSet(
        MelString('EDID','eid'),
        MelStruct('OBND','=6h',
                  'boundX1','boundY1','boundZ1',
                  'boundX2','boundY2','boundZ2'),
        MelFull0(),
        MelModel(),
        MelString('ICON','iconPath'),
        MelString('MICO','smallIconPath'),
        MelFid('SCRI','script'),
        MelDestructible(),
        MelFid('YNAM','pickupSound'),
        MelFid('ZNAM','dropSound'),
        #-1:None,0:Big Guns,1:Energy Weapons,2:Small Guns,3:Melee Weapons,
        #4:Unarmed Weapon,5:Thrown Weapons,6:Mine,7:Body Wear,8:Head Wear,
        #9:Hand Wear,10:Chems,11:Stimpack,12:Food,13:Alcohol
        MelStruct('ETYP','i',('etype',-1)),
        MelStruct('DATA','f','weight'),
        MelStruct('ENIT','iB3sIfI','value',(_flags,'flags',0L),('unused1',null3),
                  (FID,'withdrawalEffect',None),'addictionChance',(FID,'soundConsume',None)),
        MelEffects(),
        )
    __slots__ = melSet.getSlotsUsed()

#------------------------------------------------------------------------------
class MreAmmo(MelRecord):
    """Ammo (arrow) record."""
    classType = 'AMMO'
    _flags = Flags(0L,Flags.getNames('notNormalWeapon','nonPlayable'))
    melSet = MelSet(
        MelString('EDID','eid'),
        MelStruct('OBND','=6h',
                  'boundX1','boundY1','boundZ1',
                  'boundX2','boundY2','boundZ2'),
        MelString('FULL','full'),
        MelModel(),
        MelString('ICON','iconPath'),
        MelString('MICO','smallIconPath'),
        MelDestructible(),
        MelFid('YNAM','pickupSound'),
        MelFid('ZNAM','dropSound'),
        MelStruct('DATA','fB3siB','speed',(_flags,'flags',0L),('ammoData1',null3),
                  'value','clipRounds'),
        MelString('ONAM','shortName'),
        )
    __slots__ = melSet.getSlotsUsed()

#------------------------------------------------------------------------------
class MreAnio(MelRecord):
    """Animation object record."""
    classType = 'ANIO'
    melSet = MelSet(
        MelString('EDID','eid'),
        MelModel(),
        MelFid('DATA','animationId'),
        )
    __slots__ = melSet.getSlotsUsed()

#------------------------------------------------------------------------------
class MreArma(MelRecord):
    """Armor addon record."""
    classType = 'ARMA'
    _flags = MelBipedFlags(0L,Flags.getNames())
    _dnamFlags = Flags(0L,Flags.getNames(
        (0,'modulatesVoice'),
    ))
    _generalFlags = Flags(0L,Flags.getNames(
        (5,'powerArmor'),
        (6,'notPlayable'),
        (7,'heavyArmor')
    ))
    melSet = MelSet(
        MelString('EDID','eid'),
        MelStruct('OBND','=6h',
                  'boundX1','boundY1','boundZ1',
                  'boundX2','boundY2','boundZ2'),
        MelString('FULL','full'),
        MelStruct('BMDT','=2I',(_flags,'bipedFlags',0L),(_generalFlags,'generalFlags',0L)),
        MelModel('maleBody'),
        MelModel('maleWorld',2),
        MelString('ICON','maleIconPath'),
        MelString('MICO','maleSmallIconPath'),
        MelModel('femaleBody',3),
        MelModel('femaleWorld',4),
        MelString('ICO2','femaleIconPath'),
        MelString('MIC2','femaleSmallIconPath'),
        #-1:None,0:Big Guns,1:Energy Weapons,2:Small Guns,3:Melee Weapons,
        #4:Unarmed Weapon,5:Thrown Weapons,6:Mine,7:Body Wear,8:Head Wear,
        #9:Hand Wear,10:Chems,11:Stimpack,12:Food,13:Alcohol
        MelStruct('ETYP','i',('etype',-1)),
        MelStruct('DATA','IIf','value','health','weight'),
        MelStruct('DNAM','hH','ar',(_dnamFlags,'dnamFlags',0L),),
        )
    __slots__ = melSet.getSlotsUsed()

#------------------------------------------------------------------------------
class MreArmo(MelRecord):
    """Armor record."""
    classType = 'ARMO'
    _flags = MelBipedFlags(0L,Flags.getNames())
    _dnamFlags = Flags(0L,Flags.getNames(
        (0,'modulatesVoice'),
    ))
    _generalFlags = Flags(0L,Flags.getNames(
        (5,'powerArmor'),
        (6,'notPlayable'),
        (7,'heavyArmor')
    ))
    melSet = MelSet(
        MelString('EDID','eid'),
        MelStruct('OBND','=6h',
                  'boundX1','boundY1','boundZ1',
                  'boundX2','boundY2','boundZ2'),
        MelString('FULL','full'),
        MelFid('SCRI','script'),
        MelFid('EITM','objectEffect'),
        MelStruct('BMDT','=IB3s',(_flags,'bipedFlags',0L),
                  (_generalFlags,'generalFlags',0L),('armoBMDT1',null3),),
        MelModel('maleBody'),
        MelModel('maleWorld',2),
        MelString('ICON','maleIconPath'),
        MelString('MICO','maleSmallIconPath'),
        MelModel('femaleBody',3),
        MelModel('femaleWorld',4),
        MelString('ICO2','femaleIconPath'),
        MelString('MIC2','femaleSmallIconPath'),
        MelString('BMCT','ragdollTemplatePath'),
        MelDestructible(),
        MelFid('REPL','repairList'),
        MelFid('BIPL','bipedModelList'),
        #-1:None,0:Big Guns,1:Energy Weapons,2:Small Guns,3:Melee Weapons,
        #4:Unarmed Weapon,5:Thrown Weapons,6:Mine,7:Body Wear,8:Head Wear,
        #9:Hand Wear,10:Chems,11:Stimpack,12:Food,13:Alcohol
        MelStruct('ETYP','i',('etype',-1)),
        MelFid('YNAM','pickupSound'),
        MelFid('ZNAM','dropSound'),
        MelStruct('DATA','=2if','value','health','weight'),
        MelStruct('DNAM','=hH','ar',(_dnamFlags,'dnamFlags',0L),),
        )
    __slots__ = melSet.getSlotsUsed()

#------------------------------------------------------------------------------
class MreAspc(MelRecord):
    """Acoustic space record."""
    classType = 'ASPC'
    melSet = MelSet(
        MelString('EDID','eid'),
        MelStruct('OBND','=6h',
                  'boundX1','boundY1','boundZ1',
                  'boundX2','boundY2','boundZ2'),
        MelFid('SNAM','soundLooping'),
        MelFid('RDAT','useSoundFromRegion'),
        MelStruct('ANAM','I','environmentType'),
        )
    __slots__ = melSet.getSlotsUsed()

#------------------------------------------------------------------------------
class MreAvif(MelRecord):
    """ActorValue Information record."""
    classType = 'AVIF'
    melSet = MelSet(
        MelString('EDID','eid'),
        MelString('FULL','full'),
        MelString('DESC','description'),
        MelString('ICON','iconPath'),
        MelString('MICO','smallIconPath'),
        MelString('ANAM','shortName'),
    )
    __slots__ = melSet.getSlotsUsed()

#------------------------------------------------------------------------------
class MreBook(MelRecord):
    """BOOK record."""
    classType = 'BOOK'
    # FO3Edit '', 'Can''t be Taken'
    _flags = Flags(0,Flags.getNames('isScroll','isFixed'))
    melSet = MelSet(
        MelString('EDID','eid'),
        MelStruct('OBND','=6h',
                  'boundX1','boundY1','boundZ1',
                  'boundX2','boundY2','boundZ2'),
        MelString('FULL','full'),
        MelModel(),
        MelString('ICON','iconPath'),
        MelString('MICO','smallIconPath'),
        MelFid('SCRI','script'),
        MelString('DESC','text'),
        MelDestructible(),
        MelOptStruct('YNAM','I',(FID,'pickupSound')),
        MelOptStruct('ZNAM','I',(FID,'dropSound')),
        MelStruct('DATA', '=BbIf',(_flags,'flags',0L),('teaches',-1),'value','weight'),
        )
    __slots__ = melSet.getSlotsUsed() + ['modb']

#------------------------------------------------------------------------------
class MreBptd(MelRecord):
    """Body part data record."""
    classType = 'BPTD'
    _flags = Flags(0L,Flags.getNames('severable','ikData','ikBipedData',
        'explodable','ikIsHead','ikHeadtracking','toHitChanceAbsolute'))
    class MelBptdGroups(MelGroups):
        def loadData(self, record, ins, sub_type, size_, readId):
            """Reads data from ins into record attribute."""
            if sub_type == self.type0:
                target = self.getDefault()
                record.__getattribute__(self.attr).append(target)
            else:
                targets = record.__getattribute__(self.attr)
                if targets:
                    target = targets[-1]
                # Fallout 3 RadScorpionBodyPart
                # Fallout NV NVVoidBodyPartData, NVraven02
                elif sub_type == 'BPNN':
                    target = self.getDefault()
                    record.__getattribute__(self.attr).append(target)
            slots = []
            for element in self.elements:
                slots.extend(element.getSlotsUsed())
            target.__slots__ = slots
            self.loaders[sub_type].loadData(target, ins, sub_type, size_, readId)
    melSet = MelSet(
        MelString('EDID','eid'),
        MelModel(),
        MelBptdGroups('bodyParts',
            MelString('BPTN','partName'),
            MelString('BPNN','nodeName'),
            MelString('BPNT','vatsTarget'),
            MelString('BPNI','ikDataStartNode'),
            MelStruct('BPND','f3Bb2BH2I2fi2I7f2I2B2sf','damageMult',
                      (_flags,'flags'),'partType','healthPercent','actorValue',
                      'toHitChance','explodableChancePercent',
                      'explodableDebrisCount',(FID,'explodableDebris',0L),
                      (FID,'explodableExplosion',0L),'trackingMaxAngle',
                      'explodableDebrisScale','severableDebrisCount',
                      (FID,'severableDebris',0L),(FID,'severableExplosion',0L),
                      'severableDebrisScale','goreEffectPosTransX',
                      'goreEffectPosTransY','goreEffectPosTransZ',
                      'goreEffectPosRotX','goreEffectPosRotY','goreEffectPosRotZ',
                      (FID,'severableImpactDataSet',0L),
                      (FID,'explodableImpactDataSet',0L),'severableDecalCount',
                      'explodableDecalCount',('unused',null2),
                      'limbReplacementScale'),
            MelString('NAM1','limbReplacementModel'),
            MelString('NAM4','goreEffectsTargetBone'),
            MelBase('NAM5','endMarker'),
            ),
        MelFid('RAGA','ragdoll'),
        )
    __slots__ = melSet.getSlotsUsed()

#------------------------------------------------------------------------------
class MreCams(MelRecord):
    """Cams Type"""
    classType = 'CAMS'

    # DATA 'Action','Location','Target' is wbEnum
    # 'Action-Shoot',
    # 'Action-Fly',
    # 'Action-Hit',
    # 'Action-Zoom'

    # 'Location-Attacker',
    # 'Location-Projectile',
    # 'Location-Target',

    # 'Target-Attacker',
    # 'Target-Projectile',
    # 'Target-Target',

    CamsFlagsFlags = Flags(0L,Flags.getNames(
            (0, 'positionFollowsLocation'),
            (1, 'rotationFollowsTarget'),
            (2, 'dontFollowBone'),
            (3, 'firstPersonCamera'),
            (4, 'noTracer'),
            (5, 'startAtTimeZero'),
        ))

    melSet = MelSet(
        MelString('EDID','eid'),
        MelString('DATA','eid'),
        MelModel(),
        MelStruct('DATA','4I6f','action','location','target',
                  (CamsFlagsFlags,'flags',0L),'timeMultPlayer',
                  'timeMultTarget','timeMultGlobal','maxTime','minTime',
                  'targetPctBetweenActors',),
        MelFid('MNAM','imageSpaceModifier',),
        )
    __slots__ = melSet.getSlotsUsed()

#------------------------------------------------------------------------------
class MreCell(MelRecord):
    """Cell record."""
    classType = 'CELL'
    cellFlags = Flags(0L,Flags.getNames((0, 'isInterior'),(1,'hasWater'),(2,'invertFastTravel'),
        (3,'forceHideLand'),(5,'publicPlace'),(6,'handChanged'),(7,'behaveLikeExterior')))
    inheritFlags = Flags(0L,Flags.getNames('ambientColor','directionalColor','fogColor','fogNear','fogFar',
        'directionalRotation','directionalFade','clipDistance','fogPower'))
    class MelCoordinates(MelOptStruct):
        """Handle older truncated XCLC for CELL subrecord."""
        def loadData(self, record, ins, sub_type, size_, readId):
            if size_ == 12:
                MelStruct.loadData(self, record, ins, sub_type, size_, readId)
                return
            elif size_ == 8:
                unpacked = ins.unpack('ii',size_,readId)
            else:
                raise "Unexpected size encountered for XCLC subrecord: %s" % size_
            unpacked += self.defaults[len(unpacked):]
            setter = record.__setattr__
            for attr,value,action in zip(self.attrs,unpacked,self.actions):
                if callable(action): value = action(value)
                setter(attr,value)
            if self._debug: print unpacked, record.flags.getTrueAttrs()
        def dumpData(self,record,out):
            if not record.flags.isInterior:
                MelOptStruct.dumpData(self,record,out)
    class MelCellXcll(MelOptStruct):
        """Handle older truncated XCLL for CELL subrecord."""
        def loadData(self, record, ins, sub_type, size_, readId):
            if size_ == 40:
                MelStruct.loadData(self, record, ins, sub_type, size_, readId)
                return
            elif size_ == 36:
                unpacked = ins.unpack('=3Bs3Bs3Bs2f2i2f',size_,readId)
            else:
                raise "Unexpected size encountered for XCLL subrecord: %s" % size_
            unpacked += self.defaults[len(unpacked):]
            setter = record.__setattr__
            for attr,value,action in zip(self.attrs,unpacked,self.actions):
                if callable(action): value = action(value)
                setter(attr,value)
            if self._debug: print unpacked, record.flags.getTrueAttrs()
    melSet = MelSet(
        MelString('EDID','eid'),
        MelString('FULL','full'),
        MelStruct('DATA','B',(cellFlags,'flags',0L)),
        MelCoordinates('XCLC','iiI',('posX',None),('posY',None),('forceHideLand',0L)),
        MelCellXcll('XCLL','=3Bs3Bs3Bs2f2i3f','ambientRed','ambientGreen','ambientBlue',
            ('unused1',null1),'directionalRed','directionalGreen','directionalBlue',
            ('unused2',null1),'fogRed','fogGreen','fogBlue',
            ('unused3',null1),'fogNear','fogFar','directionalXY','directionalZ',
            'directionalFade','fogClip','fogPower'),
        MelBase('IMPF','footstepMaterials'), #--todo rewrite specific class.
        MelFid('LTMP','lightTemplate'),
        MelOptStruct('LNAM','I',(inheritFlags,'lightInheritFlags',0L)),
        #--CS default for water is -2147483648, but by setting default here to -2147483649,
        #  we force the bashed patch to retain the value of the last mod.
        MelOptStruct('XCLW','f',('waterHeight',-2147483649)),
        MelString('XNAM','waterNoiseTexture'),
        MelFidList('XCLR','regions'),
        MelFid('XCIM','imageSpace'),
        MelOptStruct('XCET','B','xcet_p'),
        MelFid('XEZN','encounterZone'),
        MelFid('XCCM','climate'),
        MelFid('XCWT','water'),
        MelOwnership(),
        MelFid('XCAS','acousticSpace'),
        MelOptStruct('XCMT','B','xcmt_p'),
        MelFid('XCMO','music'),
        )
    __slots__ = melSet.getSlotsUsed()

#------------------------------------------------------------------------------
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
        (4,'foods'),
        (5,'chems'),
        (6,'stimpacks'),
        (7,'lights'),
        (10,'miscItems'),
        (13,'potions'),
        (14,'training'),
        (16,'recharge'),
        (17,'repair'),))

        # trainSkill
        # -1, None
        #  0, Barter
        #  1, Big Guns (obsolete)
        #  2, Energy Weapons
        #  3, Explosives
        #  4, Lockpick
        #  5, Medicine
        #  6, Melee Weapons
        #  7, Repair
        #  8, Science
        #  9, Guns
        # 10, Sneak
        # 11, Speech
        # 12, Survival
        # 13, Unarmed

    melSet = MelSet(
        MelString('EDID','eid'),
        MelString('FULL','full'),
        MelString('DESC','description'),
        MelString('ICON','iconPath'),
        MelStruct('DATA','4i2IbB2s','tagSkill1','tagSkill2','tagSkill3',
            'tagSkill4',(_flags,'flags',0L),(aiService,'services',0L),
            ('trainSkill',-1),('trainLevel',0),('clasData1',null2)),
        # MelTuple('ATTR','7B','attributes',[0]*7),
        MelStructA('ATTR','7B','attributes','strength','perception','endurance',
                   'charisma','intelligence','agility','luck'),
        )
    __slots__ = melSet.getSlotsUsed()

#------------------------------------------------------------------------------
class MreClmt(MelRecord):
    """Climate record."""
    classType = 'CLMT'
    melSet = MelSet(
        MelString('EDID','eid'),
        MelStructA('WLST','IiI', 'Weather', (FID,'weather'), 'chance', (FID,'global')),
        MelString('FNAM','sunPath'),
        MelString('GNAM','glarePath'),
        MelModel(),
        MelStruct('TNAM','6B','riseBegin','riseEnd','setBegin','setEnd',
                  'volatility','phaseLength',),
        )
    __slots__ = melSet.getSlotsUsed()

#------------------------------------------------------------------------------
class MreCobj(MelRecord):
    """Constructible Object record (recipies)"""
    classType = 'COBJ'

    melSet = MelSet(
        MelString('EDID','eid'),
        MelStruct('OBND','=6h',
                  'boundX1','boundY1','boundZ1',
                  'boundX2','boundY2','boundZ2'),
        MelString('FULL','full'),
        MelModel(),
        MelString('ICON','iconPath'),
        MelString('MICO','smallIconPath'),
        MelFid('SCRI','script'),
        MelFid('YNAM','pickupSound'),
        MelFid('ZNAM','dropSound'),
        MelStruct('DATA','if','value','weight'),
        )
    __slots__ = melSet.getSlotsUsed()

#------------------------------------------------------------------------------
class MreCont(MelRecord):
    """Container record."""
    classType = 'CONT'
    _flags = Flags(0,Flags.getNames(None,'respawns'))
    melSet = MelSet(
        MelString('EDID','eid'),
        MelStruct('OBND','=6h',
                  'boundX1','boundY1','boundZ1',
                  'boundX2','boundY2','boundZ2'),
        MelString('FULL','full'),
        MelModel(),
        MelFid('SCRI','script'),
        MelGroups('items',
            MelStruct('CNTO','Ii',(FID,'item',None),('count',1)),
            MelOptStruct('COED','IIf',(FID,'owner',None),(FID,'glob',None),('condition',1.0)),
        ),
        MelDestructible(),
        MelStruct('DATA','=Bf',(_flags,'flags',0L),'weight'),
        MelFid('SNAM','soundOpen'),
        MelFid('QNAM','soundClose'),
        )
    __slots__ = melSet.getSlotsUsed()

#------------------------------------------------------------------------------
class MreCpth(MelRecord):
    """Camera Path"""
    classType = 'CPTH'

    # DATA 'Camera Zoom' isn wbEnum
    # 0, 'Default, Must Have Camera Shots',
    # 1, 'Disable, Must Have Camera Shots',
    # 2, 'Shot List, Must Have Camera Shots',

    melSet = MelSet(
        MelString('EDID','eid'),
        MelConditions(),
        MelFidList('ANAM','relatedCameraPaths',),
        MelStruct('DATA','B','cameraZoom',),
        MelFids('SNAM','cameraShots',),
        )
    __slots__ = melSet.getSlotsUsed()

#------------------------------------------------------------------------------
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
        (20,'noVATSMelee'),
        (21,'allowPCDialogue'),
        (22,'cantOpenDoors'),
        (23,'immobile'),
        (24,'tiltFrontBack'),
        (25,'tiltLeftRight'),
        (26,'noKnockDown'),
        (27,'notPushable'),
        (28,'allowPickpocket'),
        (29,'isGhost'),
        (30,'noRotatingHeadTrack'),
        (31,'invulnerable'),))
    #--AI Service flags
    aiService = Flags(0L,Flags.getNames(
        (0,'weapons'),
        (1,'armor'),
        (2,'clothing'),
        (3,'books'),
        (4,'foods'),
        (5,'chems'),
        (6,'stimpacks'),
        (7,'lights'),
        (10,'miscItems'),
        (13,'potions'),
        (14,'training'),
        (16,'recharge'),
        (17,'repair'),))
    aggroflags = Flags(0L,Flags.getNames('aggroRadiusBehavior',))

    #--Mel Set
    melSet = MelSet(
        MelString('EDID','eid'),
        MelStruct('OBND','=6h',
                  'boundX1','boundY1','boundZ1',
                  'boundX2','boundY2','boundZ2'),
        MelString('FULL','full'),
        MelModel(),
        MelFids('SPLO','spells'),
        MelFid('EITM','effect'),
        MelStruct('EAMT','H', 'eamt'),
        MelStrings('NIFZ','bodyParts'),
        MelBase('NIFT','nift_p'), ###Texture File hashes, Byte Array
        MelStruct('ACBS','=I2Hh3HfhH',(_flags,'flags',0L),'fatigue',
            'barterGold',('level',1),'calcMin','calcMax','speedMultiplier',
            'karma','dispotionBase','templateFlags'),
        MelStructs('SNAM','=IB3s','factions',
            (FID,'faction',None),'rank',('unused1','IFZ')),
        MelFid('INAM','deathItem'),
        MelFid('VTCK','voice'),
        MelFid('TPLT','template'),
        MelDestructible(),
        MelFid('SCRI','script'),
        MelGroups('items',
            MelStruct('CNTO','Ii',(FID,'item',None),('count',1)),
            MelOptStruct('COED','IIf',(FID,'owner',None),(FID,'glob',None),
                ('condition',1.0)),
        ),
        MelStruct('AIDT','=5B3sIbBbBi',
        #0:Unaggressive,1:Aggressive,2:Very Aggressive,3:Frenzied
        ('aggression',0),
        #0:Cowardly,1:Cautious,2:Average,3:Brave,4:Foolhardy
        ('confidence',2),
        ('energyLevel',50),('responsibility',50),
        #0:Neutral,1:Afraid,2:Annoyed,3:Cocky,4:Drugged,5:Pleasant,6:Angry,7:Sad
        ('mood',0),
        ('unused_aidt',null3),(aiService,'services',0L),
        #-1:None,0:Barter,1:Big Guns (obsolete),2:Energy Weapons,3:Explosives
        #4:Lockpick,5:Medicine,6:Melee Weapons,7:Repair,8:Science,9:Guns,10:Sneak
        #11:Speech,12:Survival,13:Unarmed,
        ('trainSkill',-1),
        'trainLevel',
        #0:Helps Nobody,1:Helps Allies,2:Helps Friends and Allies
        ('assistance',0),
        (aggroflags,'aggroRadiusBehavior',0L),'aggroRadius'),
        MelFids('PKID','aiPackages'),
        MelStrings('KFFZ','animations'),
        MelStruct('DATA','=4Bh2sh7B','type','combatSkill','magicSkill',
            'stealthSkill','health',('unused2',null2),'damage','strength',
            'perception','endurance','charisma','intelligence','agility',
            'luck'),
        MelStruct('RNAM','B','attackReach'),
        MelFid('ZNAM','combatStyle'),
        MelFid('PNAM','bodyPartData'),
        MelStruct('TNAM','f','turningSpeed'),
        MelStruct('BNAM','f','baseScale'),
        MelStruct('WNAM','f','footWeight'),
        MelStruct('NAM4','I',('impactMaterialType',0L)),
        MelStruct('NAM5','I',('soundLevel',0L)),
        MelFid('CSCR','inheritsSoundsFrom'),
        MelGroups('sounds',
            MelStruct('CSDT','I','type'),
            MelFid('CSDI','sound'),
            MelStruct('CSDC','B','chance'),
        ),
        MelFid('CNAM','impactDataset'),
        MelFid('LNAM','meleeWeaponList'),
        )
    __slots__ = MreActor.__slots__ + melSet.getSlotsUsed()

#------------------------------------------------------------------------------
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

    #--Mel Set
    melSet = MelSet(
        MelString('EDID','eid'),
        MelOptStruct('CSTD', '2B2s8f2B2s3fB3s2f5B3s2fH2s2B2sf','dodgeChance',
                    'lrChance',('unused1',null2),'lrTimerMin','lrTimerMax',
                    'forTimerMin','forTimerMax','backTimerMin','backTimerMax',
                    'idleTimerMin','idleTimerMax','blkChance','atkChance',
                    ('unused2',null2),'atkBRecoil','atkBunc','atkBh2h',
                    'pAtkChance',('unused3',null3),'pAtkBRecoil','pAtkBUnc',
                    'pAtkNormal','pAtkFor','pAtkBack','pAtkL','pAtkR',
                    ('unused4',null3),'holdTimerMin','holdTimerMax',
                    (_flagsA,'flagsA'),('unused5',null2),'acroDodge',
                    ('rushChance',25),('unused6',null3),('rushMult',1.0),),
        MelOptStruct('CSAD', '21f', 'dodgeFMult', 'dodgeFBase', 'encSBase', 'encSMult',
                     'dodgeAtkMult', 'dodgeNAtkMult', 'dodgeBAtkMult', 'dodgeBNAtkMult',
                     'dodgeFAtkMult', 'dodgeFNAtkMult', 'blockMult', 'blockBase',
                     'blockAtkMult', 'blockNAtkMult', 'atkMult','atkBase', 'atkAtkMult',
                     'atkNAtkMult', 'atkBlockMult', 'pAtkFBase', 'pAtkFMult'),
        MelOptStruct('CSSD', '9f4sI5f', 'coverSearchRadius', 'takeCoverChance',
                     'waitTimerMin', 'waitTimerMax', 'waitToFireTimerMin',
                     'waitToFireTimerMax', 'fireTimerMin', 'fireTimerMax'
                     'rangedWeaponRangeMultMin','unknown1','weaponRestrictions',
                     'rangedWeaponRangeMultMax','maxTargetingFov','combatRadius',
                     'semiAutomaticFireDelayMultMin','semiAutomaticFireDelayMultMax'),
        )
    __slots__ = melSet.getSlotsUsed()

#------------------------------------------------------------------------------
class MreDebr(MelRecord):
    """Debris record."""
    classType = 'DEBR'

    dataFlags = Flags(0L,Flags.getNames('hasCollissionData'))
    class MelDebrData(MelStruct):
        subType = 'DATA'
        _elements = (('percentage',0),('modPath',null1),('flags',0),)
        def __init__(self):
            """Initialize."""
            self.attrs,self.defaults,self.actions,self.formAttrs = self.parseElements(*self._elements)
            self._debug = False
        def loadData(self, record, ins, sub_type, size_, readId):
            """Reads data from ins into record attribute."""
            data = ins.read(size_, readId)
            (record.percentage,) = struct_unpack('B',data[0:1])
            record.modPath = data[1:-2]
            if data[-2] != null1:
                raise ModError(ins.inName,_('Unexpected subrecord: ')+readId)
            (record.flags,) = struct_unpack('B',data[-1])
        def dumpData(self,record,out):
            """Dumps data from record to outstream."""
            data = ''
            data += struct_pack('B',record.percentage)
            data += record.modPath
            data += null1
            data += struct_pack('B',record.flags)
            out.packSub('DATA',data)
    melSet = MelSet(
        MelString('EDID','eid'),
        MelGroups('models',
            MelDebrData(),
            MelBase('MODT','modt_p'),
        ),
    )
    __slots__ = melSet.getSlotsUsed()

#------------------------------------------------------------------------------
class MreDial(brec.MreDial):
    """Dialog record."""
    _flags = Flags(0,Flags.getNames('rumors','toplevel',))
    class MelDialData(MelStruct):
        """Handle older truncated DATA for DIAL subrecord."""
        def loadData(self, record, ins, sub_type, size_, readId):
            if size_ == 2:
                MelStruct.loadData(self, record, ins, sub_type, size_, readId)
                return
            elif size_ == 1:
                unpacked = ins.unpack('B', size_, readId)
            else:
                raise "Unexpected size encountered for DIAL subrecord: %s" %\
                      size_
            unpacked += self.defaults[len(unpacked):]
            setter = record.__setattr__
            for attr,value,action in zip(self.attrs,unpacked,self.actions):
                if callable(action): value = action(value)
                setter(attr,value)
            if self._debug: print unpacked, record.flags.getTrueAttrs()

    melSet = MelSet(
        MelString('EDID','eid'),
        MelFids('QSTI','quests'),
        MelFids('QSTR','rQuests'),
        MelString('FULL','full'),
        MelStruct('PNAM','f','priority'),
        MelDialData('DATA','BB','dialType',(_flags,'dialFlags',0L)),
    )
    __slots__ = melSet.getSlotsUsed()

#------------------------------------------------------------------------------
class MreDobj(MelRecord):
    """Default object manager record."""
    classType = 'DOBJ'
    melSet = MelSet(
        MelString('EDID','eid'),
        MelStruct('DATA','21I',(FID,'stimpack'),(FID,'superStimpack'),(FID,'radX'),(FID,'radAway'),
            (FID,'morphine'),(FID,'perkParalysis'),(FID,'playerFaction'),(FID,'mysteriousStrangerNpc'),
            (FID,'mysteriousStrangerFaction'),(FID,'defaultMusic'),(FID,'battleMusic'),(FID,'deathMusic'),
            (FID,'successMusic'),(FID,'levelUpMusic'),(FID,'playerVoiceMale'),(FID,'playerVoiceMaleChild'),
            (FID,'playerVoiceFemale'),(FID,'playerVoiceFemaleChild'),(FID,'eatPackageDefaultFood'),
            (FID,'everyActorAbility'),(FID,'drugWearsOffImageSpace'),),
        )
    __slots__ = melSet.getSlotsUsed()

#------------------------------------------------------------------------------
class MreDoor(MelRecord):
    """Container record."""
    classType = 'DOOR'
    _flags = Flags(0,Flags.getNames(
        ( 1,'automatic'),
        ( 2,'hidden'),
        ( 3,'minimalUse'),
        ( 4,'slidingDoor',),
    ))
    melSet = MelSet(
        MelString('EDID','eid'),
        MelStruct('OBND','=6h',
                  'boundX1','boundY1','boundZ1',
                  'boundX2','boundY2','boundZ2'),
        MelString('FULL','full'),
        MelModel(),
        MelFid('SCRI','script'),
        MelDestructible(),
        MelFid('SNAM','soundOpen'),
        MelFid('ANAM','soundClose'),
        MelFid('BNAM','soundLoop'),
        MelStruct('FNAM','B',(_flags,'flags',0L)),
        )
    __slots__ = melSet.getSlotsUsed()

#------------------------------------------------------------------------------
class MreEczn(MelRecord):
    """Encounter Zone record."""
    classType = 'ECZN'
    _flags = Flags(0L,Flags.getNames('neverResets','matchPCBelowMinimumLevel'))
    melSet = MelSet(
        MelString('EDID','eid'),
        MelStruct('DATA','=I2bBs',(FID,'owner',None),'rank','minimumLevel',
                  (_flags,'flags',0L),('unused1',null1)),
        )
    __slots__ = melSet.getSlotsUsed()

#------------------------------------------------------------------------------
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
            if size_ == 308:
                MelStruct.loadData(self, record, ins, sub_type, size_, readId)
                return
            elif size_ == 300:
                unpacked = ins.unpack('B3s3I3Bs9f3Bs8f5I19f3Bs3Bs3Bs11fI5f3Bsf2I4f', size_, readId)
            elif size_ == 284:
                unpacked = ins.unpack('B3s3I3Bs9f3Bs8f5I19f3Bs3Bs3Bs11fI5f3Bsf2I', size_, readId)
            elif size_ == 248:
                unpacked = ins.unpack('B3s3I3Bs9f3Bs8f5I19f3Bs3Bs3Bs11fI', size_, readId)
            elif size_ == 244:
                unpacked = ins.unpack('B3s3I3Bs9f3Bs8f5I19f3Bs3Bs3Bs11f', size_, readId)
            # Size of Test Plugin and FormID 00000144 in FalloutNV.esm
            elif size_ == 224:
                unpacked = ins.unpack('B3s3I3Bs9f3Bs8f5I19f3Bs3Bs3Bs6f', size_, readId)
            else:
                raise "Unexpected size encountered for EFSH:DATA subrecord: %s" % size_
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
        MelString('NAM7','holesTexture'),
        MelEfshData('DATA','B3s3I3Bs9f3Bs8f5I19f3Bs3Bs3Bs11fI5f3Bsf2I6f',
            (_flags,'flags'),('unused1',null3),
            ('memSBlend',5),('memBlendOp',1),('memZFunc',3),
            'fillRed','fillGreen','fillBlue',
            ('unused2',null1),'fillAIn','fillAFull','fillAOut','fillAPRatio',
            'fillAAmp','fillAFreq','fillAnimSpdU','fillAnimSpdV','edgeOff',
            'edgeRed','edgeGreen','edgeBlue',('unused3',null1),'edgeAIn',
            'edgeAFull','edgeAOut','edgeAPRatio','edgeAAmp','edgeAFreq',
            'fillAFRatio','edgeAFRatio',('memDBlend',6),('partSBlend',5),
            ('partBlendOp',1),('partZFunc',4),('partDBlend',6),('partBUp',0.0),
            ('partBFull',0.0),('partBDown',0.0),('partBFRatio',1.0),
            ('partBPRatio',1.0),('partLTime',1.0),('partLDelta',0.0),
            ('partNSpd',0.0),('partNAcc',0.0),('partVel1',0.0),('partVel2',0.0),
            ('partVel3',0.0),('partAcc1',0.0),('partAcc2',0.0),('partAcc3',0.0),
            ('partKey1',1.0),('partKey2',1.0),('partKey1Time',0.0),
            ('partKey2Time',1.0),('key1Red',255),('key1Green',255),
            ('key1Blue',255),('unused4',null1),('key2Red',255),('key2Green',255),
            ('key2Blue',255),('unused5',null1),('key3Red',255),('key3Green',255),
            ('key3Blue',255),('unused6',null1),('key1A',1.0),('key2A',1.0),
            ('key3A',1.0),('key1Time',0.0),('key2Time',0.5),('key3Time',1.0),
            ('partNSpdDelta',0.00000),('partRot',0.00000),
            ('partRotDelta',0.00000),('partRotSpeed',0.00000),
            ('partRotSpeedDelta',0.00000),(FID,'addonModels',None),
            ('holesStartTime',0.00000),('holesEndTime',0.00000),
            ('holesStartVal',0.00000),('holesEndVal',0.00000),
            ('edgeWidth',0.00000),('edgeRed',255),('edgeGreen',255),
            ('edgeBlue',255),('unused7',null1),('explosionWindSpeed',0.00000),
            ('textureCountU',1),('textureCountV',1),
            ('addonModelsFadeInTime',1.00000),('addonModelsFadeOutTime',1.00000),
            ('addonModelsScaleStart',1.00000),('addonModelsScaleEnd',1.00000),
            ('addonModelsScaleInTime',1.00000),('addonModelsScaleOutTime',1.00000),
            ),
        )
    __slots__ = melSet.getSlotsUsed()

#------------------------------------------------------------------------------
class MreEnch(MelRecord,MreHasEffects):
    """Enchantment (Object Effect) record."""
    classType = 'ENCH'
    _flags = Flags(0L,Flags.getNames('noAutoCalc',None,'hideEffect'))
    melSet = MelSet(
        MelString('EDID','eid'),
        MelFull0(), #--At least one mod has this. Odd.
        MelStruct('ENIT','3IB3s','itemType','chargeAmount','enchantCost',
                  (_flags,'flags',0L),('unused1',null3)),
        #--itemType = 0: Scroll, 1: Staff, 2: Weapon, 3: Apparel
        MelEffects(),
        )
    __slots__ = melSet.getSlotsUsed()

#------------------------------------------------------------------------------
class MreExpl(MelRecord):
    """Explosion record."""
    classType = 'EXPL'
    _flags = Flags(0,Flags.getNames(
        (1, 'alwaysUsesWorldOrientation'),
        (2, 'knockDownAlways'),
        (3, 'knockDownByFormular'),
        (4, 'ignoreLosCheck'),
        (5, 'pushExplosionSourceRefOnly'),
        (6, 'ignoreImageSpaceSwap'),
    ))
    melSet = MelSet(
        MelString('EDID','eid'),
        MelStruct('OBND','=6h',
                  'boundX1','boundY1','boundZ1',
                  'boundX2','boundY2','boundZ2'),
        MelString('FULL','full'),
        MelModel(),
        MelFid('EITM','objectEffect'),
        MelFid('MNAM','imageSpaceModifier'),
        MelStruct('DATA','fffIIIfIIfffI','force','damage','radius',(FID,'light',None),
                  (FID,'sound1',None),(_flags,'flags'),'isRadius',(FID,'impactDataset',None),
                  (FID,'sound2',None),'radiationLevel','radiationTime','radiationRadius','soundLevel'),
        MelFid('INAM','placedImpactObject'),
        )
    __slots__ = melSet.getSlotsUsed()

#------------------------------------------------------------------------------
class MreEyes(MelRecord):
    """Eyes record."""
    classType = 'EYES'
    _flags = Flags(0L,Flags.getNames(
            (0, 'playable'),
            (1, 'notMale'),
            (2, 'notFemale'),
    ))
    melSet = MelSet(
        MelString('EDID','eid'),
        MelString('FULL','full'),
        MelString('ICON','iconPath'),
        MelStruct('DATA','B',(_flags,'flags')),
        )
    __slots__ = melSet.getSlotsUsed()

#------------------------------------------------------------------------------
class MreFact(MelRecord):
    """Faction record."""
    classType = 'FACT'
    _flags = Flags(0L,Flags.getNames('hiddenFromPC','evil','specialCombat'))
    _flags2 = Flags(0L,Flags.getNames('trackCrime','allowSell',))

    class MelFactData(MelStruct):
        """Handle older truncated DATA for FACT subrecord."""
        def loadData(self, record, ins, sub_type, size_, readId):
            if size_ == 4:
                MelStruct.loadData(self, record, ins, sub_type, size_, readId)
                return
            elif size_ == 2:
                #--Else 2 byte record
                unpacked = ins.unpack('2B', size_, readId)
            elif size_ == 1:
                #--Else 1 byte record
                unpacked = ins.unpack('B', size_, readId)
            else:
                raise "Unexpected size encountered for FACT:DATA subrecord: %s" % size_
            unpacked += self.defaults[len(unpacked):]
            setter = record.__setattr__
            for attr,value,action in zip(self.attrs,unpacked,self.actions):
                if callable(action): value = action(value)
                setter(attr,value)
            if self._debug: print unpacked

    melSet = MelSet(
        MelString('EDID','eid'),
        MelString('FULL','full'),
        MelStructs('XNAM','IiI','relations',(FID,'faction'),'mod','groupCombatReaction'),
        MelFactData('DATA','2B2s',(_flags,'flags',0L),'flagsFact','unknown'),
        MelOptStruct('CNAM','f',('crimeGoldMultiplier',None)),
        MelGroups('ranks',
            MelStruct('RNAM','i','rank'),
            MelString('MNAM','male'),
            MelString('FNAM','female'),
            MelString('INAM','insigniaPath'),),
        )
    __slots__ = melSet.getSlotsUsed()

#------------------------------------------------------------------------------
class MreFlst(MelRecord):
    """FormID list record."""
    classType = 'FLST'
    melSet = MelSet(
        MelString('EDID','eid'),
        MelFids('LNAM','formIDInList'),
        )
    __slots__ = melSet.getSlotsUsed() + ['mergeOverLast', 'mergeSources',
                                         'items', 'deflsts']

    def __init__(self, header, ins=None, do_unpack=False):
        """Initialize."""
        MelRecord.__init__(self, header, ins, do_unpack)
        self.mergeOverLast = False #--Merge overrides last mod merged
        self.mergeSources = None #--Set to list by other functions
        self.items  = None #--Set of items included in list
        #--Set of items deleted by list (Deflst mods) unused for Skyrim
        self.deflsts = None #--Set of items deleted by list (Deflst mods)

    def mergeFilter(self,modSet):
        """Filter out items that don't come from specified modSet."""
        if not self.longFids: raise StateError(_("Fids not in long format"))
        self.formIDInList = [fid for fid in self.formIDInList if fid[0] in modSet]

    def mergeWith(self,other,otherMod):
        """Merges newLevl settings and entries with self.
        Requires that: self.items, other.deflsts be defined."""
        if not self.longFids: raise StateError(_("Fids not in long format"))
        if not other.longFids: raise StateError(_("Fids not in long format"))
        #--Remove items based on other.removes
        if other.deflsts:
            removeItems = self.items & other.deflsts
            #self.entries = [entry for entry in self.entries if entry.listId not in removeItems]
            self.formIDInList = [fid for fid in self.formIDInList if fid not in removeItems]
            self.items = (self.items | other.deflsts)
        hasOldItems = bool(self.items)
        #--Add new items from other
        newItems = set()
        formIDInListAppend = self.formIDInList.append
        newItemsAdd = newItems.add
        for fid in other.formIDInList:
            if fid not in self.items:
                formIDInListAppend(fid)
                newItemsAdd(fid)
        if newItems:
            self.items |= newItems
            #self.fids.sort(key=attrgetter('level'))
            self.formIDInList.sort
        #--Is merged list different from other? (And thus written to patch.)
        if len(self.formIDInList) != len(other.formIDInList):
            self.mergeOverLast = True
        else:
            for selfEntry,otherEntry in zip(self.formIDInList,other.formIDInList):
                if selfEntry != otherEntry:
                    self.mergeOverLast = True
                    break
            else:
                self.mergeOverLast = False
        if self.mergeOverLast:
            self.mergeSources.append(otherMod)
        else:
            self.mergeSources = [otherMod]
        #--Done
        self.setChanged()

#------------------------------------------------------------------------------
class MreFurn(MelRecord):
    """Furniture record."""
    classType = 'FURN'
    _flags = Flags() #--Governs type of furniture and which anims are available
    #--E.g., whether it's a bed, and which of the bed entry/exit animations are available
    melSet = MelSet(
        MelString('EDID','eid'),
        MelStruct('OBND','=6h',
                  'boundX1','boundY1','boundZ1',
                  'boundX2','boundY2','boundZ2'),
        MelString('FULL','full'),
        MelModel(),
        MelFid('SCRI','script'),
        MelDestructible(),
        MelStruct('MNAM','I',(_flags,'activeMarkers',0L)), ####ByteArray
        )
    __slots__ = melSet.getSlotsUsed()

#------------------------------------------------------------------------------
# Marker for organization please don't remove ---------------------------------
# GLOB ------------------------------------------------------------------------
# Defined in brec.py as class MreGlob(MelRecord) ------------------------------
#------------------------------------------------------------------------------
class MreGmst(MreGmstBase):
    """Fallout 3 GMST record"""
    isKeyedByEid = True # NULL fids are acceptable.

#------------------------------------------------------------------------------
class MreGras(MelRecord):
    """Grass record."""
    classType = 'GRAS'
    _flags = Flags(0,Flags.getNames('vLighting','uScaling','fitSlope'))
    melSet = MelSet(
        MelString('EDID','eid'),
        MelStruct('OBND','=6h',
                  'boundX1','boundY1','boundZ1',
                  'boundX2','boundY2','boundZ2'),
        MelModel(),
        MelStruct('DATA','3BsH2sI4fB3s','density','minSlope',
                  'maxSlope',('unused1',null1),'waterDistance',('unused2',null2),
                  'waterOp','posRange','heightRange','colorRange',
                  'wavePeriod',(_flags,'flags'),('unused3',null3)),
        )
    __slots__ = melSet.getSlotsUsed()

#------------------------------------------------------------------------------
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

#------------------------------------------------------------------------------
class MreHdpt(MelRecord):
    """Head part record."""
    classType = 'HDPT'
    _flags = Flags(0L,Flags.getNames('playable',))
    melSet = MelSet(
        MelString('EDID','eid'),
        MelString('FULL','full'),
        MelModel(),
        MelStruct('DATA','B',(_flags,'flags')),
        MelFids('HNAM','extraParts'),
        )
    __slots__ = melSet.getSlotsUsed()

#------------------------------------------------------------------------------
class MreIdle(MelRecord):
    """Idle record."""
    classType = 'IDLE'
    #--Mel IDLE DATA
    class MelIdleData(MelStruct):
        """Handle older truncated DATA for IDLE subrecord."""
        def loadData(self, record, ins, sub_type, size_, readId):
            if size_ == 8:
                MelStruct.loadData(self, record, ins, sub_type, size_, readId)
                return
            elif size_ == 6:
                #--Else 6 byte record (skips flags and unknown2...
                unpacked = ins.unpack('3Bsh', size_, readId)
            else:
                raise "Unexpected size encountered for IDLE:DATA subrecord: %s" % size_
            unpacked += self.defaults[len(unpacked):]
            setter = record.__setattr__
            for attr,value,action in zip(self.attrs,unpacked,self.actions):
                if callable(action): value = action(value)
                setter(attr,value)
            if self._debug: print unpacked, record.flags.getTrueAttrs()
    melSet = MelSet(
        MelString('EDID','eid'),
        MelModel(),
        MelConditions(),
        MelStruct('ANAM','II',(FID,'parent'),(FID,'prevId')),
        MelIdleData('DATA','3BshBs','group','loopMin','loopMax',('unknown1',null1),
                    'delay','flags',('unknown2',null1)),
        )
    __slots__ = melSet.getSlotsUsed()

#------------------------------------------------------------------------------
class MreIdlm(MelRecord):
    """Idle marker record."""
    classType = 'IDLM'
    _flags = Flags(0L,Flags.getNames('runInSequence',None,'doOnce'))
    class MelIdlmIdlc(MelStruct):
        """Handle older truncated IDLC for IDLM subrecord."""
        def loadData(self, record, ins, sub_type, size_, readId):
            if size_ == 4:
                MelStruct.loadData(self, record, ins, sub_type, size_, readId)
                return
            elif size_ == 1:
                unpacked = ins.unpack('B', size_, readId)
            else:
                raise "Unexpected size encountered for IDLM:IDLC subrecord: %s" % size_
            unpacked += self.defaults[len(unpacked):]
            setter = record.__setattr__
            for attr,value,action in zip(self.attrs,unpacked,self.actions):
                if callable(action): value = action(value)
                setter(attr,value)
            if self._debug: print unpacked
    melSet = MelSet(
        MelString('EDID','eid'),
        MelStruct('OBND','=6h',
                  'boundX1','boundY1','boundZ1',
                  'boundX2','boundY2','boundZ2'),
        MelStruct('IDLF','B',(_flags,'flags')),
        MelIdlmIdlc('IDLC','B3s','animationCount',('unused',null3)),
        MelStruct('IDLT','f','idleTimerSetting'),
        MelFidList('IDLA','animations'),
        )
    __slots__ = melSet.getSlotsUsed()

#------------------------------------------------------------------------------
class MreImad(MelRecord):
    """Image space modifier record."""
    classType = 'IMAD'
    melSet = MelSet(
        MelString('EDID','eid'),
        MelBase('DNAM','dnam_p'),
        MelBase('BNAM','bnam_p'),
        MelBase('VNAM','vnam_p'),
        MelBase('TNAM','tnam_p'),
        MelBase('NAM3','nam3_p'),
        MelBase('RNAM','rnam_p'),
        MelBase('SNAM','snam_p'),
        MelBase('UNAM','unam_p'),
        MelBase('NAM1','nam1_p'),
        MelBase('NAM2','nam2_p'),
        MelBase('WNAM','wnam_p'),
        MelBase('XNAM','xnam_p'),
        MelBase('YNAM','ynam_p'),
        MelBase('NAM4','nam4_p'),
        MelBase('\x00IAD','_00IAD'),
        MelBase('\x40IAD','_atiad_p'),
        MelBase('\x01IAD','_01IAD'),
        MelBase('AIAD','aiad_p'),
        MelBase('\x02IAD','_02IAD'),
        MelBase('BIAD','biad_p'),
        MelBase('\x03IAD','_03IAD'),
        MelBase('CIAD','ciad_p'),
        MelBase('\x04IAD','_04IAD'),
        MelBase('DIAD','diad_p'),
        MelBase('\x05IAD','_05IAD'),
        MelBase('EIAD','eiad_p'),
        MelBase('\x06IAD','_06IAD'),
        MelBase('FIAD','fiad_p'),
        MelBase('\x07IAD','_07IAD'),
        MelBase('GIAD','giad_p'),
        MelBase('\x08IAD','_08IAD'),
        MelBase('HIAD','hiad_p'),
        MelBase('\x09IAD','_09IAD'),
        MelBase('IIAD','iiad_p'),
        MelBase('\x0aIAD','_0aIAD'),
        MelBase('JIAD','jiad_p'),
        MelBase('\x0bIAD','_0bIAD'),
        MelBase('KIAD','kiad_p'),
        MelBase('\x0cIAD','_0cIAD'),
        MelBase('LIAD','liad_p'),
        MelBase('\x0dIAD','_0dIAD'),
        MelBase('MIAD','miad_p'),
        MelBase('\x0eIAD','_0eIAD'),
        MelBase('NIAD','niad_p'),
        MelBase('\x0fIAD','_0fIAD'),
        MelBase('OIAD','oiad_p'),
        MelBase('\x10IAD','_10IAD'),
        MelBase('PIAD','piad_p'),
        MelBase('\x11IAD','_11IAD'),
        MelBase('QIAD','qiad_p'),
        MelBase('\x12IAD','_12IAD'),
        MelBase('RIAD','riad_p'),
        MelBase('\x13IAD','_13iad_p'),
        MelBase('SIAD','siad_p'),
        MelBase('\x14IAD','_14iad_p'),
        MelBase('TIAD','tiad_p'),
    )
    __slots__ = melSet.getSlotsUsed()

#------------------------------------------------------------------------------
class MreImgs(MelRecord):
    """Image Space"""
    classType = 'IMGS'

    _flags = Flags(0L,Flags.getNames(
        'saturation',
        'contrast',
        'tint',
        'brightness'
    ))

    # Original Size 152 Bytes, FNVEdit says it can be 132 or 148 also
    class MelDnamData(MelStruct):
        """Handle older truncated DNAM for IMGS subrecord."""
        def loadData(self, record, ins, sub_type, size_, readId):
            if size_ == 152:
                MelStruct.loadData(self, record, ins, sub_type, size_, readId)
                return
            elif size_ == 148:
                unpacked = ins.unpack('33f4s4s4s4s', size_, readId)
            elif size_ == 132:
                unpacked = ins.unpack('33f', size_, readId)
            else:
                raise "Unexpected size encountered for IMGS:DNAM subrecord: %s" % size_
            unpacked += self.defaults[len(unpacked):]
            setter = record.__setattr__
            for attr,value,action in zip(self.attrs,unpacked,self.actions):
                if callable(action): value = action(value)
                setter(attr,value)
            if self._debug: print unpacked, record.flags.getTrueAttrs()

    melSet = MelSet(
        MelString('EDID','eid'),
        MelDnamData('DNAM','33f4s4s4s4sB3s','eyeAdaptSpeed','blurRadius','blurPasses',
                  'emissiveMult','targetLUM','upperLUMClamp','brightScale',
                  'brightClamp','lumRampNoTex','lumRampMin','lumRampMax',
                  'sunlightDimmer','grassDimmer','treeDimmer','skinDimmer',
                  'bloomBlurRadius','bloomAlphaMultInterior',
                  'bloomAlphaMultExterior','getHitBlurRadius',
                  'getHitBlurDampingConstant','getHitDampingConstant',
                  'nightEyeTintRed','nightEyeTintGreen','nightEyeTintBlue',
                  'nightEyeBrightness','cinematicSaturation',
                  'cinematicAvgLumValue','cinematicValue',
                  'cinematicBrightnessValue','cinematicTintRed',
                  'cinematicTintGreen','cinematicTintBlue','cinematicTintValue',
                  ('unused1',null4),('unused2',null4),('unused3',null4),('unused4',null4),
                  (_flags,'flags'),('unused5',null3)),
        )
    __slots__ = melSet.getSlotsUsed()

#------------------------------------------------------------------------------
class MreInfo(MelRecord):
    """Info (dialog entry) record."""
    classType = 'INFO'
    _flags = Flags(0,Flags.getNames(
        'goodbye','random','sayOnce','runImmediately','infoRefusal','randomEnd',
        'runForRumors','speechChallenge',))
    _flags2 = Flags(0,Flags.getNames(
        'sayOnceADay','alwaysDarken',))
    _variableFlags = Flags(0L,Flags.getNames('isLongOrShort'))
    class MelInfoData(MelStruct):
        """Support older 2 byte version."""
        def loadData(self, record, ins, sub_type, size_, readId):
            if size_ != 2:
                MelStruct.loadData(self, record, ins, sub_type, size_, readId)
                return
            unpacked = ins.unpack('2B', size_, readId)
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
        MelInfoData('DATA','HH','dialType','nextSpeaker',(_flags,'flags'),(_flags2,'flagsInfo'),),
        MelFid('QSTI','quests'),
        MelFid('TPIC','topic'),
        MelFid('PNAM','prevInfo'),
        MelFids('NAME','addTopics'),
        MelGroups('responses',
            MelStruct('TRDT','Ii4sB3sIB3s','emotionType','emotionValue',('unused1',null4),'responseNum',('unused2','0xcd0xcd0xcd'),
                      (FID,'sound'),'flags',('unused3','0xcd0xcd0xcd')),
            MelString('NAM1','responseText'),
            MelString('NAM2','actorNotes'),
            MelString('NAM3','edits'),
            MelFid('SNAM','speakerAnimation'),
            MelFid('LNAM','listenerAnimation'),
            ),
        MelConditions(),
        MelFids('TCLT','choices'),
        MelFids('TCLF','linksFrom'),
        # MelBase('SCHD','schd_p'), #--Old format script header?
        MelGroup('scriptBegin',
            MelInfoSchr('SCHR','4s4I',('unused2',null4),'numRefs','compiledSize','lastIndex','scriptType'),
            MelBase('SCDA','compiled_p'),
            MelString('SCTX','scriptText'),
            MelGroups('vars',
                MelStruct('SLSD','I12sB7s','index',('unused1',null4+null4+null4),(_variableFlags,'flags',0L),('unused2',null4+null3)),
                MelString('SCVR','name')),
            MelScrxen('SCRV/SCRO','references'),
            ),
        MelGroup('scriptEnd',
            MelBase('NEXT','marker'),
            MelInfoSchr('SCHR','4s4I',('unused2',null4),'numRefs','compiledSize','lastIndex','scriptType'),
            MelBase('SCDA','compiled_p'),
            MelString('SCTX','scriptText'),
            MelGroups('vars',
                MelStruct('SLSD','I12sB7s','index',('unused1',null4+null4+null4),(_variableFlags,'flags',0L),('unused2',null4+null3)),
                MelString('SCVR','name')),
            MelScrxen('SCRV/SCRO','references'),
            ),
        # MelFid('SNDD','sndd_p'),
        MelString('RNAM','prompt'),
        MelFid('ANAM','speaker'),
        MelFid('KNAM','acterValuePeak'),
        MelStruct('DNAM', 'I', 'speechChallenge')
        )
    __slots__ = melSet.getSlotsUsed()

#------------------------------------------------------------------------------
class MreIngr(MelRecord,MreHasEffects):
    """INGR (ingredient) record."""
    classType = 'INGR'
    _flags = Flags(0L,Flags.getNames('noAutoCalc','isFood'))
    # Equiptment Type
    # -1, None
    #  0, Big Guns',
    #  1, Energy Weapons',
    #  2, Small Guns',
    #  3, Melee Weapons',
    #  4, Unarmed Weapon',
    #  5, Thrown Weapons',
    #  6, Mine',
    #  7, Body Wear',
    #  8, Head Wear',
    #  9, Hand Wear',
    # 10, Chems',
    # 11, Stimpack',
    # 12, Food',
    # 13, Alcohol'
    melSet = MelSet(
        MelString('EDID','eid'),
        MelStruct('OBND','=6h',
                  'boundX1','boundY1','boundZ1',
                  'boundX2','boundY2','boundZ2'),
        MelFull0(),
        MelModel(),
        MelString('ICON','iconPath'),
        MelFid('SCRI','script'),
        #-1:None,0:Big Guns,1:Energy Weapons,2:Small Guns,3:Melee Weapons,
        #4:Unarmed Weapon,5:Thrown Weapons,6:Mine,7:Body Wear,8:Head Wear,
        #9:Hand Wear,10:Chems,11:Stimpack,12:Food,13:Alcohol
        MelStruct('ETYP','i',('etype',-1)),
        MelStruct('DATA','f','weight'),
        MelStruct('ENIT','iB3s','value',(_flags,'flags',0L),('unused1',null3)),
        MelEffects(),
        )
    __slots__ = melSet.getSlotsUsed()

#------------------------------------------------------------------------------
class MreIpct(MelRecord):
    """Impact record."""
    classType = 'IPCT'

    DecalDataFlags = Flags(0L,Flags.getNames(
            (0, 'parallax'),
            (0, 'alphaBlending'),
            (0, 'alphaTesting'),
        ))

    melSet = MelSet(
        MelString('EDID','eid'),
        MelModel(),
        MelStruct('DATA','fIffII','effectDuration','effectOrientation',
                  'angleThreshold','placementRadius','soundLevel','flags'),
        MelOptStruct('DODT','7fBB2s3Bs','minWidth','maxWidth','minHeight',
                     'maxHeight','depth','shininess','parallaxScale',
                     'parallaxPasses',(DecalDataFlags,'decalFlags',0L),
                     ('unused1',null2),'red','green','blue',('unused2',null1)),
        MelFid('DNAM','textureSet'),
        MelFid('SNAM','sound1'),
        MelFid('NAM1','sound2'),
        )
    __slots__ = melSet.getSlotsUsed()

#------------------------------------------------------------------------------
class MreIpds(MelRecord):
    """Impact Dataset record."""
    classType = 'IPDS'
    class MelIpdsData(MelStruct):
        """Handle older truncated DATA for IPDS subrecord."""
        def loadData(self, record, ins, sub_type, size_, readId):
            if size_ == 48:
                MelStruct.loadData(self, record, ins, sub_type, size_, readId)
                return
            elif size_ == 40:
                unpacked = ins.unpack('10I', size_, readId)
            elif size_ == 36:
                unpacked = ins.unpack('9I', size_, readId)
            else:
                raise "Unexpected size encountered for IPDS:DATA subrecord: %s" % size_
            unpacked += self.defaults[len(unpacked):]
            setter = record.__setattr__
            for attr,value,action in zip(self.attrs,unpacked,self.actions):
                if callable(action): value = action(value)
                setter(attr,value)
            if self._debug: print unpacked
    melSet = MelSet(
        MelString('EDID','eid'),
        MelIpdsData('DATA','12I',(FID,'stone',0),(FID,'dirt',0),
                    (FID,'grass',0),(FID,'glass',0),(FID,'metal',0),
                    (FID,'wood',0),(FID,'organic',0),(FID,'cloth',0),
                    (FID,'water',0),(FID,'hollowMetal',0),(FID,'organicBug',0),
                    (FID,'organicGlow',0)),
        )
    __slots__ = melSet.getSlotsUsed()

#------------------------------------------------------------------------------
class MreKeym(MelRecord):
    """MISC (miscellaneous item) record."""
    classType = 'KEYM'
    melSet = MelSet(
        MelString('EDID','eid'),
        MelStruct('OBND','=6h',
                  'boundX1','boundY1','boundZ1',
                  'boundX2','boundY2','boundZ2'),
        MelString('FULL','full'),
        MelModel(),
        MelString('ICON','iconPath'),
        MelString('MICO','smallIconPath'),
        MelFid('SCRI','script'),
        MelDestructible(),
        MelFid('YNAM','pickupSound'),
        MelFid('ZNAM','dropSound'),
        MelStruct('DATA','if','value','weight'),
        )
    __slots__ = melSet.getSlotsUsed()

#------------------------------------------------------------------------------
class MreLgtm(MelRecord):
    """Lgtm Item"""
    classType = 'LGTM'

    melSet = MelSet(
        MelString('EDID','eid'),
        MelStruct('DATA','3Bs3Bs3Bs2f2i3f',
            'redLigh','greenLigh','blueLigh','unknownLigh',
            'redDirect','greenDirect','blueDirect','unknownDirect',
            'redFog','greenFog','blueFog','unknownFog',
            'fogNear','fogFar',
            'dirRotXY','dirRotZ',
            'directionalFade','fogClipDist','fogPower',),
        )
    __slots__ = melSet.getSlotsUsed()

#------------------------------------------------------------------------------
class MreLigh(MelRecord):
    """Light source record."""
    classType = 'LIGH'
    _flags = Flags(0L,Flags.getNames('dynamic','canTake','negative','flickers',
        'unk1','offByDefault','flickerSlow','pulse','pulseSlow','spotLight','spotShadow'))
    melSet = MelSet(
        MelString('EDID','eid'),
        MelStruct('OBND','=6h',
                  'boundX1','boundY1','boundZ1',
                  'boundX2','boundY2','boundZ2'),
        MelModel(),
        MelFid('SCRI','script'),
        MelDestructible(),
        MelString('FULL','full'),
        MelString('ICON','iconPath'),
        MelStruct('DATA','iI3BsI2fIf','duration','radius','red','green','blue',
                  ('unused1',null1),(_flags,'flags',0L),'falloff','fov','value',
                  'weight'),
        MelOptStruct('FNAM','f',('fade',None)),
        MelFid('SNAM','sound'),
        )
    __slots__ = melSet.getSlotsUsed()

#------------------------------------------------------------------------------
class MreLscr(MelRecord):
    """Load screen."""
    classType = 'LSCR'
    melSet = MelSet(
        MelString('EDID','eid'),
        MelString('ICON','iconPath'),
        MelString('DESC','text'),
        MelStructs('LNAM','I8s','locations',(FID,'cell'),('unknown',null4+null4),),
        )
    __slots__ = melSet.getSlotsUsed()

#------------------------------------------------------------------------------
class MreLtex(MelRecord):
    """Landscape Texture."""
    classType = 'LTEX'
    melSet = MelSet(
        MelString('EDID','eid'),
        MelString('ICON','iconPath'),
        MelFid('TNAM', 'texture'),
        MelOptStruct('HNAM','3B','materialType','friction','restitution'),
        MelOptStruct('SNAM','B','specular'),
        MelFids('GNAM', 'grass'),
        )
    __slots__ = melSet.getSlotsUsed()

#------------------------------------------------------------------------------
class MreLvlc(MreLeveledList):
    """LVLC record. Leveled list for creatures."""
    classType = 'LVLC'
    __slots__ = MreLeveledList.__slots__

#------------------------------------------------------------------------------
class MreLvli(MreLeveledList):
    """LVLI record. Leveled list for items."""
    classType = 'LVLI'
    __slots__ = MreLeveledList.__slots__

#------------------------------------------------------------------------------
class MreLvln(MreLeveledList):
    """LVLN record. Leveled list for NPC."""
    classType = 'LVLN'
    __slots__ = MreLeveledList.__slots__

#------------------------------------------------------------------------------
class MreMesg(MelRecord):
    """Message Record."""
    classType = 'MESG'

    MesgTypeFlags = Flags(0L,Flags.getNames(
            (0, 'messageBox'),
            (1, 'autoDisplay'),
        ))

    melSet = MelSet(
        MelString('EDID','eid'),
        MelString('DESC','description'),
        MelString('FULL','full'),
        MelFid('INAM','icon'),
        MelBase('NAM0', 'unused_0'),
        MelBase('NAM1', 'unused_1'),
        MelBase('NAM2', 'unused_2'),
        MelBase('NAM3', 'unused_3'),
        MelBase('NAM4', 'unused_4'),
        MelBase('NAM5', 'unused_5'),
        MelBase('NAM6', 'unused_6'),
        MelBase('NAM7', 'unused_7'),
        MelBase('NAM8', 'unused_8'),
        MelBase('NAM9', 'unused_9'),
        MelStruct('DNAM','I',(MesgTypeFlags,'flags',0L),),
        MelStruct('TNAM','I','displayTime',),
        MelGroups('menuButtons',
            MelString('ITXT','buttonText'),
            MelConditions(),
            ),
    )
    __slots__ = melSet.getSlotsUsed()

#------------------------------------------------------------------------------
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

    melSet = MelSet(
        MelString('EDID','eid'),
        MelString('FULL','full'),
        MelString('DESC','text'),
        MelString('ICON','iconPath'),
        MelModel(),
        # 'counterEffectCount' is a count of ESCE and should be updated
        MelStruct('DATA','IfI2iH2sIf6I2fIi',
            (_flags,'flags'),'baseCost',(FID,'associated'),'school','resistValue',
            'counterEffectCount',('unused1',null2),(FID,'light',0),'projectileSpeed',
            (FID,'effectShader',0),(FID,'objectDisplayShader',0),
            (FID,'castingSound',0),(FID,'boltSound',0),(FID,'hitSound',0),
            # cefEnchantment and cefBarter are unused
            (FID,'areaSound',0),('cefEnchantment',0.0),('cefBarter',0.0),
            'archType','actorValue'),
        MelGroups('counterEffects',
            MelOptStruct('ESCE','I',(FID,'counterEffectCode',0)),),
        )
    __slots__ = melSet.getSlotsUsed()

    def dumpData(self,out):
        counterEffects = self.counterEffects
        self.counterEffectCount = len(counterEffects) if counterEffects else 0
        MelRecord.dumpData(self,out)

#------------------------------------------------------------------------------
class MreMicn(MelRecord):
    """Menu icon record."""
    classType = 'MICN'
    melSet = MelSet(
        MelString('EDID','eid'),
        MelString('ICON','iconPath'),
        MelString('MICO','smallIconPath'),
        )
    __slots__ = melSet.getSlotsUsed()

#------------------------------------------------------------------------------
class MreMisc(MelRecord):
    """MISC (miscellaneous item) record."""
    classType = 'MISC'
    melSet = MelSet(
        MelString('EDID','eid'),
        MelStruct('OBND','=6h',
                  'boundX1','boundY1','boundZ1',
                  'boundX2','boundY2','boundZ2'),
        MelString('FULL','full'),
        MelModel(),
        MelString('ICON','iconPath'),
        MelString('MICO','smallIconPath'),
        MelFid('SCRI','script'),
        MelDestructible(),
        MelFid('YNAM','pickupSound'),
        MelFid('ZNAM','dropSound'),
        MelStruct('DATA','if','value','weight'),
        )
    __slots__ = melSet.getSlotsUsed()

#------------------------------------------------------------------------------
class MreMstt(MelRecord):
    """Moveable static record."""
    classType = 'MSTT'
    melSet = MelSet(
        MelString('EDID','eid'),
        MelStruct('OBND','=6h',
                  'boundX1','boundY1','boundZ1',
                  'boundX2','boundY2','boundZ2'),
        MelString('FULL','full'),
        MelModel(),
        MelDestructible(),
        MelBase('DATA','data_p'),
        MelFid('SNAM','sound'),
    )
    __slots__ = melSet.getSlotsUsed()

#------------------------------------------------------------------------------
class MreMusc(MelRecord):
    """Music type record."""
    classType = 'MUSC'
    melSet = MelSet(
        MelString('EDID','eid'),
        MelString('FNAM','filename'),
        )
    __slots__ = melSet.getSlotsUsed()

#------------------------------------------------------------------------------
class MreNavi(MelRecord):
    """Navigation Mesh Info Map."""
    classType = 'NAVI'
    class MelNaviNvmi(MelStructs):
        """Handle older truncated NVMI for NAVI subrecord."""
        def loadData(self, record, ins, sub_type, size_, readId):
            if size_ <= 16:
                raise "Unexpected size encountered for NAVI subrecord: %s" % size_
            format = '4s2I2H %ds'%(size_ - 16)
            target = self.getDefault()
            record.__getattribute__(self.attr).append(target)
            target.__slots__ = self.attrs
            unpacked = ins.unpack(format, size_, readId)
            setter = target.__setattr__
            for attr,value,action in zip(self.attrs,unpacked,self.actions):
                if callable(action): value = action(value)
                setter(attr,value)
            if self._debug: print unpacked, target.flags.getTrueAttrs()
        def dumpData(self,record,out):
            """Dumps data from record to outstream."""
            for target in record.__getattribute__(self.attr):
                format = '4s2I2H %ds'%len(target.unknown2)
                values = []
                valuesAppend = values.append
                getter = target.__getattribute__
                for attr,action in zip(self.attrs,self.actions):
                    value = getter(attr)
                    if action: value = value.dump()
                    valuesAppend(value)
                try:
                    out.packSub(self.subType,format,*values)
                except struct.error:
                    print self.subType,format,values
                    raise
    melSet = MelSet(
        MelString('EDID','eid'),
        MelStruct('NVER','I',('version',11)),
        MelNaviNvmi('NVMI','','unknowns',
                   'unknown1',(FID,'navigationMesh'),(FID,'location'),'gridX','gridY','unknown2'),
        MelFidList('NVCI','unknownDoors',),
       )
    __slots__ = melSet.getSlotsUsed()

#------------------------------------------------------------------------------
class MreNavm(MelRecord):
    """Navigation Mesh."""
    classType = 'NAVM'
    melSet = MelSet(
        MelString('EDID','eid'),
        MelStruct('NVER','I',('version',11)),
        MelStruct('DATA','I5I',(FID,'cell'),'vertexCount','triangleCount','enternalConnectionsCount','nvcaCount','doorsCount'),
        MelStructA('NVVX','3f','vertices','vertexX','vertexY','vertexZ'),
        MelStructA('NVTR','6hI','triangles','vertex0','vertex1','vertex2','triangle0','triangle1','triangle2','flags'),
        MelOptStruct('NVCA','h','nvca_p'),
        MelStructA('NVDP','II','doors',(FID,'doorReference'),'doorUnknown'),
        MelBase('NVGD','nvgd_p'),
        MelStructA('NVEX','=IIH','externalConnections','nvexUnknown',(FID,'navigationMesh'),'triangle'),
       )
    __slots__ = melSet.getSlotsUsed()

#------------------------------------------------------------------------------
class MreNote(MelRecord):
    """Note record."""
    classType = 'NOTE'

    class MelNoteTnam(MelBase):
        """text or topic"""

        def hasFids(self, formElements):
            formElements.add(self)

        def loadData(self, record, ins, sub_type, size_, readId):
            # 0:'sound',1:'text',2:'image',3:'voice'
            if record.dataType == 1:  # text (string)
                value = ins.readString(size_, readId)
                record.__setattr__(self.attr, (False, value))
            elif record.dataType == 3:  # voice (fid:DIAL)
                (value,) = ins.unpack('I', size_, readId)
                record.__setattr__(self.attr, (True, value))
            else:
                raise ModError(ins.inName, _('Unexpected type: %d') % record.type)
            if self._debug: print value

        def dumpData(self, record, out):
            value = record.__getattribute__(self.attr)
            if value is None: return
            (isFid, value) = value
            if value is not None:
                # 0:'sound',1:'text',2:'image',3:'voice'
                if record.dataType == 1:  # text (string)
                    out.packSub0(self.subType, value)
                elif record.dataType == 3:  # voice (fid:DIAL)
                    out.packRef(self.subType, value)
                else:
                    raise ModError(record.inName, _('Unexpected type: %d') % record.type)

        def mapFids(self, record, function, save=False):
            value = record.__getattribute__(self.attr)
            if value is None: return
            (isFid, value) = value
            if isFid:
                result = function(value)
                if save: record.__setattr__(self.attr, (isFid, result))

    class MelNoteSnam(MelBase):
        """sound or npc"""

        def hasFids(self, formElements):
            formElements.add(self)

        def loadData(self, record, ins, sub_type, size_, readId):
            # 0:'sound',1:'text',2:'image',3:'voice'
            if record.dataType == 0:  # sound (fid:SOUN)
                (value,) = ins.unpack('I', size_, readId)
                record.__setattr__(self.attr, (True, value))
            elif record.dataType == 3:  # voice (fid:NPC_)
                (value,) = ins.unpack('I', size_, readId)
                record.__setattr__(self.attr, (True, value))
            else:
                raise ModError(ins.inName, _('Unexpected type: %d') % record.type)
            if self._debug: print value

        def dumpData(self, record, out):
            value = record.__getattribute__(self.attr)
            if value is None: return
            (isFid, value) = value
            if value is not None: out.packRef(self.subType, value)

        def mapFids(self, record, function, save=False):
            value = record.__getattribute__(self.attr)
            if value is None: return
            (isFid, value) = value
            if isFid:
                result = function(value)
                if save: record.__setattr__(self.attr, (isFid, result))

    melSet = MelSet(
        MelString('EDID','eid'),
        MelStruct('OBND','=6h',
                  'boundX1','boundY1','boundZ1',
                  'boundX2','boundY2','boundZ2'),
        MelString('FULL','full'),
        MelModel(),
        MelString('ICON','iconPath'),
        MelString('MICO','smallIconPath'),
        MelFid('YNAM','pickupSound'),
        MelFid('ZNAM','dropSound'),
        #0:'sound',1:'text',2:'image',3:'voice'
        MelStruct('DATA','B','dataType'),
        MelFidList('ONAM','quests'),
        MelString('XNAM','texture'),
        MelNoteTnam('TNAM', 'textTopic'),
        MelNoteSnam('SNAM', 'soundNpc'),
        )
    __slots__ = melSet.getSlotsUsed()

#------------------------------------------------------------------------------
class MreNpc(MreActor):
    """NPC Record. Non-Player Character."""
    classType = 'NPC_'
    #--Main flags
    _flags = Flags(0L,Flags.getNames(
        ( 0,'female'),
        ( 1,'essential'),
        ( 2,'isChargenFacePreset'),
        ( 3,'respawn'),
        ( 4,'autoCalc'),
        ( 7,'pcLevelOffset'),
        ( 8,'useTemplate'),
        ( 9,'noLowLevel'),
        (11,'noBloodSpray'),
        (12,'noBloodDecal'),
        (20,'noVATSMelee'),
        (22,'canBeAllRaces'),
        (23,'autocalcService'), # FNV Only
        (26,'noKnockDown'),
        (27,'notPushable'),
        (30,'noRotatingHeadTrack'),))
    #--AI Service flags
    aiService = Flags(0L,Flags.getNames(
        (0,'weapons'),
        (1,'armor'),
        (2,'clothing'),
        (3,'books'),
        (4,'foods'),
        (5,'chems'),
        (6,'stimpacks'),
        (7,'lights'),
        (10,'miscItems'),
        (13,'potions'),
        (14,'training'),
        (16,'recharge'),
        (17,'repair'),))
    aggroflags = Flags(0L,Flags.getNames('aggroRadiusBehavior',))
    #--Mel NPC DATA
    class MelNpcData(MelStruct):
        """Convert npc stats into skills, health, attributes."""
        def loadData(self, record, ins, sub_type, size_, readId):
            if size_ == 11:
                unpacked = list(ins.unpack('=I7B', size_, readId))
            else:
                unpacked = list(ins.unpack('=I21B', size_, readId))
            recordSetAttr = record.__setattr__
            recordSetAttr('health',unpacked[0])
            recordSetAttr('attributes',unpacked[1:])
            if self._debug: print unpacked[0],unpacked[1:]
        def dumpData(self,record,out):
            """Dumps data from record to outstream."""
            recordGetAttr = record.__getattribute__
            values = [recordGetAttr('health')]+recordGetAttr('attributes')
            if len(recordGetAttr('attributes')) == 7:
                out.packSub(self.subType,'=I7B',*values)
            else:
                out.packSub(self.subType,'=I21B',*values)

    #--Mel NPC DNAM
    class MelNpcDnam(MelStruct):
        """Convert npc stats into skills."""
        def loadData(self, record, ins, sub_type, size_, readId):
            unpacked = list(ins.unpack('=28B', size_, readId))
            recordSetAttr = record.__setattr__
            recordSetAttr('skillValues',unpacked[:14])
            recordSetAttr('skillOffsets',unpacked[14:])
            if self._debug: print unpacked[:14]+unpacked[14:]
        def dumpData(self,record,out):
            """Dumps data from record to outstream."""
            recordGetAttr = record.__getattribute__
            values = recordGetAttr('skillValues')+recordGetAttr('skillOffsets')
            out.packSub(self.subType,'=28B',*values)

    #--Mel Set
    melSet = MelSet(
        MelString('EDID','eid'),
        MelStruct('OBND','=6h',
                  'boundX1','boundY1','boundZ1',
                  'boundX2','boundY2','boundZ2'),
        MelString('FULL','full'),
        MelModel(),
        MelStruct('ACBS','=I2Hh3Hf2H',
            (_flags,'flags',0L),'fatigue','barterGold',
            ('level',1),'calcMin','calcMax','speedMultiplier','karma',
            'dispotionBase','templateFlags'),
        MelStructs('SNAM','=IB3s','factions',
            (FID,'faction',None),'rank',('unused1','ODB')),
        MelFid('INAM','deathItem'),
        MelFid('VTCK','voice'),
        MelFid('TPLT','template'),
        MelFid('RNAM','race'),
        #MelFid('????','actorEffects'),
        MelFid('EITM','unarmedAttackEffect'),
        MelStruct('EAMT','H', 'unarmedAttackAnimation'),
        MelDestructible(),
        MelFids('SPLO','spells'),
        MelFid('SCRI','script'),
        MelGroups('items',
            MelStruct('CNTO','Ii',(FID,'item',None),('count',1)),
            MelOptStruct('COED','IIf',(FID,'owner',None),(FID,'glob',None),('condition',1.0)),
        ),
        MelStruct('AIDT','=5B3sIbBbBi',
        #0:Unaggressive,1:Aggressive,2:Very Aggressive,3:Frenzied
        ('aggression',0),
        #0:Cowardly,1:Cautious,2:Average,3:Brave,4:Foolhardy
        ('confidence',2),
        ('energyLevel',50),('responsibility',50),
        #0:Neutral,1:Afraid,2:Annoyed,3:Cocky,4:Drugged,5:Pleasant,6:Angry,7:Sad
        ('mood',0),
        ('unused_aidt',null3),(aiService,'services',0L),
        #-1:None,0:Barter,1:Big Guns (obsolete),2:Energy Weapons,3:Explosives
        #4:Lockpick,5:Medicine,6:Melee Weapons,7:Repair,8:Science,9:Guns,10:Sneak
        #11:Speech,12:Survival,13:Unarmed,
        ('trainSkill',-1),
        'trainLevel',
        #0:Helps Nobody,1:Helps Allies,2:Helps Friends and Allies
        ('assistance',0),
        (aggroflags,'aggroRadiusBehavior',0L),'aggroRadius'),
        MelFids('PKID','aiPackages'),
        MelStrings('KFFZ','animations'),
        MelFid('CNAM','iclass'),
        MelNpcData('DATA','','health',('attributes',[0]*21)),
        MelFids('PNAM','headParts'),
        MelNpcDnam('DNAM','',('skillValues',[0]*14),('skillOffsets',[0]*14)),
        MelFid('HNAM','hair'),
        MelOptStruct('LNAM','f',('hairLength',1)),
        MelFid('ENAM','eye'), ####fid Array
        MelStruct('HCLR','3Bs','hairRed','hairBlue','hairGreen',('unused3',null1)),
        MelFid('ZNAM','combatStyle'),
        MelStruct('NAM4','I',('impactMaterialType',0L)),
        MelBase('FGGS','fggs_p'), ####FaceGen Geometry-Symmetric
        MelBase('FGGA','fgga_p'), ####FaceGen Geometry-Asymmetric
        MelBase('FGTS','fgts_p'), ####FaceGen Texture-Symmetric
        MelStruct('NAM5','H',('unknown',0L)),
        MelStruct('NAM6','f',('height',0L)),
        MelStruct('NAM7','f',('weight',0L)),
        )
    __slots__ = MreActor.__slots__ + melSet.getSlotsUsed()

#------------------------------------------------------------------------------
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
    _variableFlags = Flags(0L,Flags.getNames('isLongOrShort'))
    class MelPackPkdt(MelStruct):
        """Support older 8 byte version."""
        def loadData(self, record, ins, sub_type, size_, readId):
            if size_ == 12:
                MelStruct.loadData(self, record, ins, sub_type, size_, readId)
                return
            elif size_ == 8:
                unpacked = ins.unpack('IHH', size_, readId)
            else:
                raise "Unexpected size encountered for PACK:PKDT subrecord: %s" % size_
            unpacked += self.defaults[len(unpacked):]
            setter = record.__setattr__
            for attr,value,action in zip(self.attrs,unpacked,self.actions):
                if callable(action): value = action(value)
                setter(attr,value)
            if self._debug: print unpacked
    class MelPackPkdd(MelOptStruct):
        """Handle older truncated PKDD for PACK subrecord."""
        def loadData(self, record, ins, sub_type, size_, readId):
            if size_ == 24:
                MelStruct.loadData(self, record, ins, sub_type, size_, readId)
                return
            elif size_ == 20:
                unpacked = ins.unpack('fII4sI',size_,readId)
            elif size_ == 16:
                unpacked = ins.unpack('fII4s',size_,readId)
            elif size_ == 12:
                unpacked = ins.unpack('fII',size_,readId)
            else:
                raise "Unexpected size encountered for PACK:PKDD subrecord: %s" % size_
            unpacked += self.defaults[len(unpacked):]
            setter = record.__setattr__
            for attr,value,action in zip(self.attrs,unpacked,self.actions):
                if callable(action): value = action(value)
                setter(attr,value)
            if self._debug: print unpacked
    class MelPackLT(MelOptStruct):
        """For PLDT and PTDT. Second element of both may be either an FID or a long,
        depending on value of first element."""
        def loadData(self, record, ins, sub_type, size_, readId):
            if ((self.subType == 'PLDT' and size_ == 12) or
                (self.subType == 'PLD2' and size_ == 12) or
                (self.subType == 'PTDT' and size_ == 16) or
                (self.subType == 'PTD2' and size_ == 16)):
                MelOptStruct.loadData(self, record, ins, sub_type, size_, readId)
                return
            elif ((self.subType == 'PTDT' and size_ == 12) or
                  (self.subType == 'PTD2' and size_ == 12)):
                unpacked = ins.unpack('iIi',size_,readId)
            else:
                raise "Unexpected size encountered for PACK:%s subrecord: %s" % (self.subType, size_)
            unpacked += self.defaults[len(unpacked):]
            setter = record.__setattr__
            for attr,value,action in zip(self.attrs,unpacked,self.actions):
                if callable(action): value = action(value)
                setter(attr,value)
            if self._debug: print unpacked
        def hasFids(self,formElements):
            formElements.add(self)
        def dumpData(self,record,out):
            if ((self.subType == 'PLDT' and (record.locType or record.locId)) or
                (self.subType == 'PLD2' and (record.locType2 or record.locId2)) or
                (self.subType == 'PTDT' and (record.targetType or record.targetId)) or
                (self.subType == 'PTD2' and (record.targetType2 or record.targetId2))):
                MelStruct.dumpData(self,record,out)
        def mapFids(self,record,function,save=False):
            """Applies function to fids. If save is true, then fid is set
            to result of function."""
            if self.subType == 'PLDT' and record.locType != 5:
                result = function(record.locId)
                if save: record.locId = result
            elif self.subType == 'PLD2' and record.locType2 != 5:
                result = function(record.locId2)
                if save: record.locId2 = result
            elif self.subType == 'PTDT' and record.targetType != 2:
                result = function(record.targetId)
                if save: record.targetId = result
            elif self.subType == 'PTD2' and record.targetType2 != 2:
                result = function(record.targetId2)
                if save: record.targetId2 = result
    class MelPackDistributor(MelNull):
        """Handles embedded script records. Distributes load
        duties to other elements as needed."""
        def __init__(self):
            self._debug = False
        def getLoaders(self,loaders):
            """Self as loader for structure types."""
            for type_ in ('POBA','POEA','POCA'):
                loaders[type_] = self
        def setMelSet(self,melSet):
            """Set parent melset. Need this so that can reassign loaders later."""
            self.melSet = melSet
            self.loaders = {}
            for element in melSet.elements:
                attr = element.__dict__.get('attr',None)
                if attr: self.loaders[attr] = element
        def loadData(self, record, ins, sub_type, size_, readId):
            if sub_type == 'POBA':
                element = self.loaders['onBegin']
            elif sub_type == 'POEA':
                element = self.loaders['onEnd']
            elif sub_type == 'POCA':
                element = self.loaders['onChange']
            for subtype in ('INAM','SCHR','SCDA','SCTX','SLSD','SCVR','SCRV','SCRO','TNAM'):
                self.melSet.loaders[subtype] = element
            element.loadData(record, ins, sub_type, size_, readId)
    #--MelSet
    melSet = MelSet(
        MelString('EDID','eid'),
        MelPackPkdt('PKDT','IHHI',(_flags,'flags'),'aiType','falloutBehaviorFlags','typeSpecificFlags'),
        MelPackLT('PLDT','iIi','locType','locId','locRadius'),
        MelPackLT('PLD2','iIi','locType2','locId2','locRadius2'),
        MelStruct('PSDT','2bBbi','month','day','date','time','duration'),
        MelPackLT('PTDT','iIif','targetType','targetId','targetCount','targetUnknown1'),
        MelConditions(),
        MelGroup('idleAnimations',
            MelStruct('IDLF','B','animationFlags'),
            MelBase('IDLC','animationCount'), # byte or short
            MelStruct('IDLT','f','idleTimerSetting'),
            MelFidList('IDLA','animations'),
            MelBase('IDLB','idlb_p'),
            ),
        MelBase('PKED','eatMarker'),
        MelOptStruct('PKE2','I','escordDistance'),
        MelFid('CNAM','combatStyle'),
        MelOptStruct('PKFD','f','followStartLocationTrigerRadius'),
        MelBase('PKPT','patrolFlags'), # byte or short
        MelOptStruct('PKW3','IBB3Hff4s','weaponFlags','fireRate','fireCount','numBursts',
                     'shootPerVolleysMin','shootPerVolleysMax','pauseBetweenVolleysMin','pauseBetweenVolleysMax','weaponUnknown'),
        MelPackLT('PTD2','iIif','targetType2','targetId2','targetCount2','targetUnknown2'),
        MelBase('PUID','useItemMarker'),
        MelBase('PKAM','ambushMarker'),
        MelPackPkdd('PKDD','fII4sI4s','dialFov','dialTopic','dialFlags','dialUnknown1','dialType','dialUnknown2'),
        MelGroup('onBegin',
            MelBase('POBA', 'marker', ''), #### onBegin Marker, wbEmpty
            MelFid('INAM', 'idle'),
            MelStruct('SCHR','4s4I',('unused1',null4),'numRefs','compiledSize','lastIndex','scriptType'),
            MelBase('SCDA','compiled_p'),
            MelString('SCTX','scriptText'),
            MelGroups('vars',
                MelStruct('SLSD','I12sB7s','index',('unused1',null4+null4+null4),(_variableFlags,'flags',0L),('unused2',null4+null3)),
                MelString('SCVR','name')),
            MelScrxen('SCRV/SCRO','references'),
            MelFid('TNAM', 'topic'),
            ),
        MelGroup('onEnd',
            MelBase('POEA', 'marker', ''), #### onEnd Marker, wbEmpty
            MelFid('INAM', 'idle'),
            MelStruct('SCHR','4s4I',('unused1',null4),'numRefs','compiledSize','lastIndex','scriptType'),
            MelBase('SCDA','compiled_p'),
            MelString('SCTX','scriptText'),
            MelGroups('vars',
                MelStruct('SLSD','I12sB7s','index',('unused1',null4+null4+null4),(_variableFlags,'flags',0L),('unused2',null4+null3)),
                MelString('SCVR','name')),
            MelScrxen('SCRV/SCRO','references'),
            MelFid('TNAM', 'topic'),
            ),
        MelGroup('onChange',
            MelBase('POCA', 'marker', ''), #### onChange Marker, wbEmpty
            MelFid('INAM', 'idle'),
            MelStruct('SCHR','4s4I',('unused1',null4),'numRefs','compiledSize','lastIndex','scriptType'),
            MelBase('SCDA','compiled_p'),
            MelString('SCTX','scriptText'),
            MelGroups('vars',
                MelStruct('SLSD','I12sB7s','index',('unused1',null4+null4+null4),(_variableFlags,'flags',0L),('unused2',null4+null3)),
                MelString('SCVR','name')),
            MelScrxen('SCRV/SCRO','references'),
            MelFid('TNAM', 'topic'),
            ),
        #--Distributor for embedded script entries.
        MelPackDistributor(),
        )
    melSet.elements[-1].setMelSet(melSet)
    __slots__ = melSet.getSlotsUsed()

#------------------------------------------------------------------------------
class MrePerk(MelRecord):
    """Perk record."""
    classType = 'PERK'

    class MelPerkData(MelStruct):
        """Handle older truncated DATA for PERK subrecord."""

        def loadData(self, record, ins, sub_type, size_, readId):
            if size_ == 5:
                MelStruct.loadData(self, record, ins, sub_type, size_, readId)
                return
            elif size_ == 4:
                unpacked = ins.unpack('BBBB', size_, readId)
            else:
                raise "Unexpected size encountered for DATA subrecord: %s" % size_
            unpacked += self.defaults[len(unpacked):]
            setter = record.__setattr__
            for attr, value, action in zip(self.attrs, unpacked, self.actions):
                if callable(action): value = action(value)
                setter(attr, value)
            if self._debug: print unpacked, record.flagsA.getTrueAttrs()

    class MelPerkEffectData(MelBase):
        def hasFids(self, formElements):
            formElements.add(self)

        def loadData(self, record, ins, sub_type, size_, readId):
            target = MelObject()
            record.__setattr__(self.attr, target)
            if record.type == 0:
                format, attrs = ('II', ('quest', 'queststage'))
            elif record.type == 1:
                format, attrs = ('I', ('ability',))
            elif record.type == 2:
                format, attrs = ('HB', ('entrypoint', 'function'))
            else:
                raise ModError(ins.inName, _('Unexpected type: %d') % record.type)
            unpacked = ins.unpack(format, size_, readId)
            setter = target.__setattr__
            for attr, value in zip(attrs, unpacked):
                setter(attr, value)
            if self._debug: print unpacked

        def dumpData(self, record, out):
            target = record.__getattribute__(self.attr)
            if not target: return
            if record.type == 0:
                format, attrs = ('II', ('quest', 'queststage'))
            elif record.type == 1:
                format, attrs = ('I', ('ability',))
            elif record.type == 2:
                format, attrs = ('HB', ('entrypoint', 'function'))
            else:
                raise ModError(record.inName, _('Unexpected type: %d') % record.type)
            values = []
            valuesAppend = values.append
            getter = target.__getattribute__
            for attr in attrs:
                value = getter(attr)
                valuesAppend(value)
            try:
                out.packSub(self.subType, format, *values)
            except struct.error:
                print self.subType, format, values
                raise

        def mapFids(self, record, function, save=False):
            target = record.__getattribute__(self.attr)
            if not target: return
            if record.type == 0:
                result = function(target.quest)
                if save: target.quest = result
            elif record.type == 1:
                result = function(target.ability)
                if save: target.ability = result

    class MelPerkEffects(MelGroups):
        def __init__(self, attr, *elements):
            MelGroups.__init__(self, attr, *elements)

        def setMelSet(self, melSet):
            self.melSet = melSet
            self.attrLoaders = {}
            for element in melSet.elements:
                attr = element.__dict__.get('attr', None)
                if attr: self.attrLoaders[attr] = element

        def loadData(self, record, ins, sub_type, size_, readId):
            if sub_type == 'DATA' or sub_type == 'CTDA':
                effects = record.__getattribute__(self.attr)
                if not effects:
                    if sub_type == 'DATA':
                        element = self.attrLoaders['_data']
                    elif sub_type == 'CTDA':
                        element = self.attrLoaders['conditions']
                    element.loadData(record, ins, sub_type, size_, readId)
                    return
            MelGroups.loadData(self, record, ins, sub_type, size_, readId)

    class MelPerkEffectParams(MelGroups):
        def loadData(self, record, ins, sub_type, size_, readId):
            if sub_type in ('EPFD', 'EPFT', 'EPF2', 'EPF3', 'SCHR'):
                target = self.getDefault()
                record.__getattribute__(self.attr).append(target)
            else:
                target = record.__getattribute__(self.attr)[-1]
            element = self.loaders[sub_type]
            slots = ['recordType']
            slots.extend(element.getSlotsUsed())
            target.__slots__ = slots
            target.recordType = sub_type
            element.loadData(target, ins, sub_type, size_, readId)

        def dumpData(self, record, out):
            for target in record.__getattribute__(self.attr):
                element = self.loaders[target.recordType]
                if not element:
                    raise ModError(record.inName, _('Unexpected type: %d') % target.recordType)
                element.dumpData(target, out)

    melSet = MelSet(
        MelString('EDID','eid'),
        MelString('FULL','full'),
        MelString('DESC','description'),
        MelString('ICON','iconPath'),
        MelString('MICO','smallIconPath'),
        MelConditions(),
        MelGroup('_data',
            MelPerkData('DATA', 'BBBBB', ('trait',0), ('minLevel',0), ('ranks',0), ('playable',0), ('hidden',0)),
            ),
        MelPerkEffects('effects',
            MelStruct('PRKE', 'BBB', 'type', 'rank', 'priority'),
            MelPerkEffectData('DATA','effectData'),
            MelGroups('effectConditions',
                MelStruct('PRKC', 'B', 'runOn'),
                MelConditions(),
            ),
            MelPerkEffectParams('effectParams',
                MelBase('EPFD', 'floats'), # [Float] or [Float,Float], todo rewrite specific class
                MelStruct('EPFT','B','_epft'),
                MelString('EPF2','buttonLabel'),
                MelStruct('EPF3','H','scriptFlag'),
                MelGroup('embeddedScript',
                    MelStruct('SCHR','4s4I',('unused1',null4),'numRefs','compiledSize','lastIndex','scriptType'),
                    MelBase('SCDA','compiled_p'),
                    MelString('SCTX','scriptText'),
                    MelScrxen('SCRV/SCRO','references'),
                ),
            ),
            MelBase('PRKF','footer'),
            ),
        )
    melSet.elements[-1].setMelSet(melSet)
    __slots__ = melSet.getSlotsUsed()

#------------------------------------------------------------------------------
class MrePgre(MelRecord):
    """Placed Grenade"""
    classType = 'PGRE'
    _flags = Flags(0L,Flags.getNames('oppositeParent'))
    _variableFlags = Flags(0L,Flags.getNames('isLongOrShort'))
    _watertypeFlags = Flags(0L,Flags.getNames('reflection','refraction'))
    melSet=MelSet(
        MelString('EDID','eid'),
        MelFid('NAME','base'),
        MelFid('XEZN','encounterZone'),
        MelBase('XRGD','ragdollData'),
        MelBase('XRGB','ragdollBipedData'),
        MelGroup('patrolData',
            MelStruct('XPRD','f','idleTime'),
            MelBase('XPPA','patrolScriptMarker'),
            MelFid('INAM', 'idle'),
            MelStruct('SCHR','4s4I',('unused1',null4),'numRefs','compiledSize','lastIndex','scriptType'),
            MelBase('SCDA','compiled_p'),
            MelString('SCTX','scriptText'),
            MelGroups('vars',
                MelStruct('SLSD','I12sB7s','index',('unused1',null4+null4+null4),(_variableFlags,'flags',0L),('unused2',null4+null3)),
                MelString('SCVR','name')),
            MelScrxen('SCRV/SCRO','references'),
            MelFid('TNAM','topic'),
            ),
        MelOwnership(),
        MelStruct('XCNT','i','count'),
        MelStruct('XRDS','f','radius',),
        MelStruct('XHLP','f','health',),
        MelGroups('reflectedRefractedBy',
            MelStruct('XPWR','2I',(FID,'waterReference'),(_watertypeFlags,'waterFlags',0L),),
        ),
        MelStructs('XDCR','II','linkedDecals',(FID,'reference'),'unknown'),
        MelFid('XLKR','linkedReference'),
        MelOptStruct('XCLP','8B','linkStartColorRed','linkStartColorGreen','linkStartColorBlue',('linkColorUnused1',null1),
                     'linkEndColorRed','linkEndColorGreen','linkEndColorBlue',('linkColorUnused2',null1)),
        MelGroup('activateParents',
            MelStruct('XAPD','B','flags'),
            MelStructs('XAPR','If','activateParentRefs',(FID,'reference'),'delay')
            ),
        MelOptStruct('XESP','IB3s',(FID,'parent'),(_flags,'parentFlags'),('unused1',null3)),
        MelOptStruct('XEMI','I',(FID,'emittance')),
        MelFid('XMBR','multiboundReference'),
        MelBase('XIBS','ignoredBySandbox'),
        MelOptStruct('XSCL','f',('scale',1.0)),
        MelOptStruct('DATA','=6f',('posX',None),('posY',None),('posZ',None),('rotX',None),('rotY',None),('rotZ',None)),
    )
    __slots__ = melSet.getSlotsUsed()

#------------------------------------------------------------------------------
class MrePmis(MelRecord):
    """Placed Missile"""
    classType = 'PMIS'
    _flags = Flags(0L,Flags.getNames('oppositeParent'))
    _variableFlags = Flags(0L,Flags.getNames('isLongOrShort'))
    _watertypeFlags = Flags(0L,Flags.getNames('reflection','refraction'))
    melSet=MelSet(
        MelString('EDID','eid'),
        MelFid('NAME','base'),
        MelFid('XEZN','encounterZone'),
        MelBase('XRGD','ragdollData'),
        MelBase('XRGB','ragdollBipedData'),
        MelGroup('patrolData',
            MelStruct('XPRD','f','idleTime'),
            MelBase('XPPA','patrolScriptMarker'),
            MelFid('INAM', 'idle'),
            MelStruct('SCHR','4s4I',('unused1',null4),'numRefs','compiledSize','lastIndex','scriptType'),
            MelBase('SCDA','compiled_p'),
            MelString('SCTX','scriptText'),
            MelGroups('vars',
                MelStruct('SLSD','I12sB7s','index',('unused1',null4+null4+null4),(_variableFlags,'flags',0L),('unused2',null4+null3)),
                MelString('SCVR','name')),
            MelScrxen('SCRV/SCRO','references'),
            MelFid('TNAM','topic'),
            ),
        MelOwnership(),
        MelStruct('XCNT','i','count'),
        MelStruct('XRDS','f','radius',),
        MelStruct('XHLP','f','health',),
        MelGroups('reflectedRefractedBy',
            MelStruct('XPWR','2I',(FID,'waterReference'),(_watertypeFlags,'waterFlags',0L),),
        ),
        MelStructs('XDCR','II','linkedDecals',(FID,'reference'),'unknown'),
        MelFid('XLKR','linkedReference'),
        MelOptStruct('XCLP','8B','linkStartColorRed','linkStartColorGreen','linkStartColorBlue',('linkColorUnused1',null1),
                     'linkEndColorRed','linkEndColorGreen','linkEndColorBlue',('linkColorUnused2',null1)),
        MelGroup('activateParents',
            MelStruct('XAPD','B','flags'),
            MelStructs('XAPR','If','activateParentRefs',(FID,'reference'),'delay')
            ),
        MelOptStruct('XESP','IB3s',(FID,'parent'),(_flags,'parentFlags'),('unused1',null3)),
        MelOptStruct('XEMI','I',(FID,'emittance')),
        MelFid('XMBR','multiboundReference'),
        MelBase('XIBS','ignoredBySandbox'),
        MelOptStruct('XSCL','f',('scale',1.0)),
        MelOptStruct('DATA','=6f',('posX',None),('posY',None),('posZ',None),('rotX',None),('rotY',None),('rotZ',None)),
    )
    __slots__ = melSet.getSlotsUsed()

#------------------------------------------------------------------------------
class MreProj(MelRecord):
    """Projectile record."""
    classType = 'PROJ'
    _flags = Flags(0,Flags.getNames(
        'hitscan',
        'explosive',
        'altTriger',
        'muzzleFlash',
        None,
        'canbeDisable',
        'canbePickedUp',
        'superSonic',
        'pinsLimbs',
        'passThroughSmallTransparent'
        ))
    melSet = MelSet(
        MelString('EDID','eid'),
        MelStruct('OBND','=6h',
                  'boundX1','boundY1','boundZ1',
                  'boundX2','boundY2','boundZ2'),
        MelString('FULL','full'),
        MelModel(),
        MelDestructible(),
        MelStruct('DATA','HHfffIIfffIIfffIII',(_flags,'flags'),'type',
                  ('gravity',0.00000),('speed',10000.00000),('range',10000.00000),
                  (FID,'light',0),(FID,'muzzleFlash',0),('tracerChance',0.00000),
                  ('explosionAltTrigerProximity',0.00000),('explosionAltTrigerTimer',0.00000),
                  (FID,'explosion',0),(FID,'sound',0),('muzzleFlashDuration',0.00000),
                  ('fadeDuration',0.00000),('impactForce',0.00000),
                  (FID,'soundCountDown',0),(FID,'soundDisable',0),
                  (FID,'defaultWeaponSource',0),),
        MelString('NAM1','muzzleFlashPath'),
        MelBase('NAM2','_nam2'),
        MelStruct('VNAM','I','soundLevel'),
        )
    __slots__ = melSet.getSlotsUsed()

#------------------------------------------------------------------------------
class MrePwat(MelRecord):
    """Placeable water record."""
    classType = 'PWAT'
    _flags = Flags(0L,Flags.getNames(
        ( 0,'reflects'),
        ( 1,'reflectsActers'),
        ( 2,'reflectsLand'),
        ( 3,'reflectsLODLand'),
        ( 4,'reflectsLODBuildings'),
        ( 5,'reflectsTrees'),
        ( 6,'reflectsSky'),
        ( 7,'reflectsDynamicObjects'),
        ( 8,'reflectsDeadBodies'),
        ( 9,'refracts'),
        (10,'refractsActors'),
        (11,'refractsLands'),
        (16,'refractsDynamicObjects'),
        (17,'refractsDeadBodies'),
        (18,'silhouetteReflections'),
        (28,'depth'),
        (29,'objectTextureCoordinates'),
        (31,'noUnderwaterFog'),
        ))
    melSet = MelSet(
        MelString('EDID','eid'),
        MelStruct('OBND','=6h',
                  'boundX1','boundY1','boundZ1',
                  'boundX2','boundY2','boundZ2'),
        MelModel(),
        MelStruct('DNAM','2I',(_flags,'flags'),(FID,'water'))
        )
    __slots__ = melSet.getSlotsUsed()

#------------------------------------------------------------------------------
class MreQust(MelRecord):
    """Quest record."""
    classType = 'QUST'
    _questFlags = Flags(0,Flags.getNames('startGameEnabled',None,'repeatedTopics','repeatedStages'))
    _variableFlags = Flags(0L,Flags.getNames('isLongOrShort'))
    stageFlags = Flags(0,Flags.getNames('complete'))
    targetFlags = Flags(0,Flags.getNames('ignoresLocks'))

    #--CDTA loader
    class MelQustLoaders(DataDict):
        """Since CDTA subrecords occur in three different places, we need
        to replace ordinary 'loaders' dictionary with a 'dictionary' that will
        return the correct element to handle the CDTA subrecord. 'Correct'
        element is determined by which other subrecords have been encountered."""
        def __init__(self,loaders,quest,stages,targets):
            self.data = loaders
            self.type_ctda = {'EDID':quest, 'INDX':stages, 'QSTA':targets}
            self.ctda = quest #--Which ctda element loader to use next.
        def __getitem__(self,key):
            if key == 'CTDA': return self.ctda
            self.ctda = self.type_ctda.get(key, self.ctda)
            return self.data[key]

    class MelQustData(MelStruct):
        """Handle older truncated DATA for QUST subrecord."""
        def loadData(self, record, ins, sub_type, size_, readId):
            if size_ == 8:
                MelStruct.loadData(self, record, ins, sub_type, size_, readId)
                return
            elif size_ == 2:
                #--Else 2 byte record
                unpacked = ins.unpack('BB', size_, readId)
            else:
                raise "Unexpected size encountered for QUST:DATA subrecord: %s" % size_
            unpacked += self.defaults[len(unpacked):]
            setter = record.__setattr__
            for attr,value,action in zip(self.attrs,unpacked,self.actions):
                if callable(action): value = action(value)
                setter(attr,value)
            if self._debug: print unpacked

    #--MelSet
    melSet = MelSet(
        MelString('EDID','eid'),
        MelFid('SCRI','script'),
        MelString('FULL','full'),
        MelString('ICON','iconPath'),
        MelQustData('DATA','=BB2sf',(_questFlags,'questFlags',0),('priority',0),('unused2',null2),('questDelay',0.0)),
        MelConditions(),
        MelGroups('stages',
            MelStruct('INDX','h','stage'),
            MelGroups('entries',
                MelStruct('QSDT','B',(stageFlags,'flags')),
                MelConditions(),
                MelString('CNAM','text'),
                MelStruct('SCHR','4s4I',('unused1',null4),'numRefs','compiledSize','lastIndex','scriptType'),
                MelBase('SCDA','compiled_p'),
                MelString('SCTX','scriptText'),
                MelGroups('vars',
                    MelStruct('SLSD','I12sB7s','index',('unused1',null4+null4+null4),(_variableFlags,'flags',0L),('unused2',null4+null3)),
                    MelString('SCVR','name')),
                MelScrxen('SCRV/SCRO','references'),
                MelFid('NAM0', 'nextQuest'),
                ),
            ),
        MelGroups('objectives',
             MelStruct('QOBJ','i','index'),
             MelString('NNAM','description'),
             MelGroups('targets',
                 MelStruct('QSTA','IB3s',(FID,'targetId'),(targetFlags,'flags'),('unused1',null3)),
                 MelConditions(),
                 ),
             ),
        )
    melSet.loaders = MelQustLoaders(melSet.loaders,*melSet.elements[5:8])
    __slots__ = melSet.getSlotsUsed()

#------------------------------------------------------------------------------
class MreRace(MelRecord):
    """Race record.

    This record is complex to read and write. Relatively simple problems are the VNAM
    which can be empty or zeroed depending on relationship between voices and
    the fid for the race.

    The face and body data is much more complicated, with the same subrecord types
    mapping to different attributes depending on preceding flag subrecords (NAM0, NAM1,
    NMAN, FNAM and INDX.) These are handled by using the MelRaceDistributor class
    to dynamically reassign melSet.loaders[type] as the flag records are encountered.

    It's a mess, but this is the shortest, clearest implementation that I could
    think of."""

    classType = 'RACE'
    _flags = Flags(0L,Flags.getNames('playable', None, 'child'))

    class MelRaceVoices(MelStruct):
        """Set voices to zero, if equal race fid. If both are zero, then don't skip dump."""
        def dumpData(self,record,out):
            if record.maleVoice == record.fid: record.maleVoice = 0L
            if record.femaleVoice == record.fid: record.femaleVoice = 0L
            if (record.maleVoice,record.femaleVoice) != (0,0):
                MelStruct.dumpData(self,record,out)

    class MelRaceHeadModel(MelGroup):
        """Most face data, like a MelModel + ICON + MICO. Load is controlled by MelRaceDistributor."""
        def __init__(self,attr,index):
            MelGroup.__init__(self,attr,
                MelString('MODL','modPath'),
                MelBase('MODB','modb_p'),
                MelBase('MODT','modt_p'),
                MelBase('MODS','mods_p'),
                MelOptStruct('MODD','B','modd_p'),
                MelString('ICON','iconPath'),
                MelBase('MICO','mico'))
            self.index = index
        def dumpData(self,record,out):
            out.packSub('INDX','I',self.index)
            MelGroup.dumpData(self,record,out)

    class MelRaceBodyModel(MelGroup):
        """Most body data, like a MelModel - MODB + ICON + MICO. Load is controlled by MelRaceDistributor."""
        def __init__(self,attr,index):
            MelGroup.__init__(self,attr,
                MelString('ICON','iconPath'),
                MelBase('MICO','mico'),
                MelString('MODL','modPath'),
                MelBase('MODT','modt_p'),
                MelBase('MODS','mods_p'),
                MelOptStruct('MODD','B','modd_p'))
            self.index = index
        def dumpData(self,record,out):
            out.packSub('INDX','I',self.index)
            MelGroup.dumpData(self,record,out)

    class MelRaceIcon(MelString):
        """Most body data plus eyes for face. Load is controlled by MelRaceDistributor."""
        def __init__(self,attr,index):
            MelString.__init__(self,'ICON',attr)
            self.index = index
        def dumpData(self,record,out):
            out.packSub('INDX','I',self.index)
            MelString.dumpData(self,record,out)

    class MelRaceFaceGen(MelGroup):
        """Most fecegen data. Load is controlled by MelRaceDistributor."""
        def __init__(self,attr):
            MelGroup.__init__(self,attr,
                MelBase('FGGS','fggs_p'), ####FaceGen Geometry-Symmetric
                MelBase('FGGA','fgga_p'), ####FaceGen Geometry-Asymmetric
                MelBase('FGTS','fgts_p'), ####FaceGen Texture-Symmetric
                MelStruct('SNAM','2s',('snam_p',null2)))

    class MelRaceDistributor(MelNull):
        """Handles NAM0, NAM1, MNAM, FMAN and INDX records. Distributes load
        duties to other elements as needed."""
        def __init__(self):
            headAttrs = ('Head', 'Ears', 'Mouth', 'TeethLower', 'TeethUpper', 'Tongue', 'LeftEye', 'RightEye')
            bodyAttrs = ('UpperBody','LeftHand','RightHand','UpperBodyTexture')
            self.headModelAttrs = {
                'MNAM':tuple('male'+text for text in headAttrs),
                'FNAM':tuple('female'+text for text in headAttrs),
                }
            self.bodyModelAttrs = {
                'MNAM':tuple('male'+text for text in bodyAttrs),
                'FNAM':tuple('female'+text for text in bodyAttrs),
                }
            self.attrs = {
                'NAM0':self.headModelAttrs,
                'NAM1':self.bodyModelAttrs
                }
            self.facegenAttrs = {'MNAM':'maleFaceGen','FNAM':'femaleFaceGen'}
            self._debug = False

        def getSlotsUsed(self):
            return '_loadAttrs', '_modelAttrs'

        def getLoaders(self,loaders):
            """Self as loader for structure types."""
            for type_ in ('NAM0','NAM1','MNAM','FNAM','INDX'):
                loaders[type_] = self

        def setMelSet(self,melSet):
            """Set parent melset. Need this so that can reassign loaders later."""
            self.melSet = melSet
            self.loaders = {}
            for element in melSet.elements:
                attr = element.__dict__.get('attr',None)
                if attr: self.loaders[attr] = element

        def loadData(self, record, ins, sub_type, size_, readId):
            if sub_type in ('NAM0', 'NAM1'):
                record._modelAttrs = self.attrs[sub_type]
                return
            elif sub_type in ('MNAM', 'FNAM'):
                record._loadAttrs = record._modelAttrs[sub_type]
                attr = self.facegenAttrs.get(sub_type)
                element = self.loaders[attr]
                for sub_type in ('FGGS', 'FGGA', 'FGTS', 'SNAM'):
                    self.melSet.loaders[sub_type] = element
            else: #--INDX
                index, = ins.unpack('I',4,readId)
                attr = record._loadAttrs[index]
                element = self.loaders[attr]
                for sub_type in ('MODL', 'MODB', 'MODT', 'MODS', 'MODD', 'ICON', 'MICO'):
                    self.melSet.loaders[sub_type] = element

    #--Mel Set
    melSet = MelSet(
        MelString('EDID','eid'),
        MelString('FULL','full'),
        MelString('DESC','text'),
        MelStruct('DATA','14b2s4fI','skill1','skill1Boost','skill2','skill2Boost',
                  'skill3','skill3Boost','skill4','skill4Boost','skill5','skill5Boost',
                  'skill6','skill6Boost','skill7','skill7Boost',('unused1',null2),
                  'maleHeight','femaleHeight','maleWeight','femaleWeight',(_flags,'flags',0L)),
        MelFid('ONAM','Older'),
        MelFid('YNAM','Younger'),
        MelBase('NAM2','_nam2',''),
        MelRaceVoices('VTCK','2I',(FID,'maleVoice'),(FID,'femaleVoice')), #--0 same as race fid.
        MelOptStruct('DNAM','2I',(FID,'defaultHairMale',0L),(FID,'defaultHairFemale',0L)), #--0=None
        MelStruct('CNAM','2B','defaultHairColorMale','defaultHairColorFemale'), #--Int corresponding to GMST sHairColorNN
        MelOptStruct('PNAM','f','mainClamp'),
        MelOptStruct('UNAM','f','faceClamp'),
        MelStruct('ATTR','2B','maleBaseAttribute','femaleBaseAttribute'),
        #--Begin Indexed entries
        MelBase('NAM0','_nam0',''), ####Face Data Marker, wbEmpty
        MelBase('MNAM','_mnam',''),
        MelRaceHeadModel('maleHead',0),
        MelRaceIcon('maleEars',1),
        MelRaceHeadModel('maleMouth',2),
        MelRaceHeadModel('maleTeethLower',3),
        MelRaceHeadModel('maleTeethUpper',4),
        MelRaceHeadModel('maleTongue',5),
        MelRaceHeadModel('maleLeftEye',6),
        MelRaceHeadModel('maleRightEye',7),
        MelBase('FNAM','_fnam',''),
        MelRaceHeadModel('femaleHead',0),
        MelRaceIcon('femaleEars',1),
        MelRaceHeadModel('femaleMouth',2),
        MelRaceHeadModel('femaleTeethLower',3),
        MelRaceHeadModel('femaleTeethUpper',4),
        MelRaceHeadModel('femaleTongue',5),
        MelRaceHeadModel('femaleLeftEye',6),
        MelRaceHeadModel('femaleRightEye',7),
        MelBase('NAM1','_nam1',''), ####Body Data Marker, wbEmpty
        MelBase('MNAM','_mnam',''), ####Male Body Data Marker, wbEmpty
        MelRaceBodyModel('maleUpperBody',0),
        MelRaceBodyModel('maleLeftHand',1),
        MelRaceBodyModel('maleRightHand',2),
        MelRaceBodyModel('maleUpperBodyTexture',3),
        MelBase('FNAM','_fnam',''), ####Female Body Data Marker, wbEmpty
        MelRaceBodyModel('femaleUpperBody',0),
        MelRaceBodyModel('femaleLeftHand',1),
        MelRaceBodyModel('femaleRightHand',2),
        MelRaceBodyModel('femaleUpperBodyTexture',3),
        #--Normal Entries
        MelFidList('HNAM','hairs'),
        MelFidList('ENAM','eyes'),
        #--FaceGen Entries
        MelBase('MNAM','_mnam',''),
        MelRaceFaceGen('maleFaceGen'),
        MelBase('FNAM','_fnam',''),
        MelRaceFaceGen('femaleFaceGen'),
        #--Distributor for face and body entries.
        MelRaceDistributor(),
        )
    melSet.elements[-1].setMelSet(melSet)
    __slots__ = melSet.getSlotsUsed()

#------------------------------------------------------------------------------
class MreRads(MelRecord):
    """Radiation Stage record."""
    classType = 'RADS'
    melSet = MelSet(
        MelString('EDID','eid'),
        MelStruct('DATA','2I','trigerThreshold',(FID,'actorEffect')),
        )
    __slots__ = melSet.getSlotsUsed()

#------------------------------------------------------------------------------
class MreRefr(MelRecord):
    """Placed Object"""
    classType = 'REFR'
    _flags = Flags(0L,Flags.getNames('visible', 'canTravelTo','showAllHidden'))
    _parentFlags = Flags(0L,Flags.getNames('oppositeParent'))
    _actFlags = Flags(0L,Flags.getNames('useDefault', 'activate','open','openByDefault'))
    _lockFlags = Flags(0L,Flags.getNames(None, None, 'leveledLock'))
    _destinationFlags = Flags(0L,Flags.getNames('noAlarm'))
    _variableFlags = Flags(0L,Flags.getNames('isLongOrShort'))
    class MelRefrXloc(MelOptStruct):
        """Handle older truncated XLOC for REFR subrecord."""
        def loadData(self, record, ins, sub_type, size_, readId):
            if size_ == 20:
                MelStruct.loadData(self, record, ins, sub_type, size_, readId)
                return
            #elif size == 16:
            #    unpacked = ins.unpack('B3sIB3s',size,readId)
            elif size_ == 12:
                unpacked = ins.unpack('B3sI4s',size_,readId)
            else:
                print ins.unpack(('%dB' % size_),size_)
                raise ModError(ins.inName,_('Unexpected size encountered for REFR:XLOC subrecord: ')+str(size_))
            unpacked = unpacked[:-2] + self.defaults[len(unpacked)-2:-2] + unpacked[-2:]
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
            (type_, size_) = insUnpack('4sH', 6, readId + '.FULL')
            while type_ in ['FNAM','FULL','TNAM','WMI1']:
                if type_ == 'FNAM':
                    value = insUnpack('B', size_, readId)
                    record.flags = MreRefr._flags(*value)
                elif type_ == 'FULL':
                    record.full = ins.readString(size_, readId)
                elif type_ == 'TNAM':
                    record.markerType, record.unused5 = insUnpack('Bs', size_, readId)
                # WMI1 not used in FO3, leaving so it doesn't break something
                elif type_ == 'WMI1':
                    record.reputation = insUnpack('I', size_, readId)
                pos = insTell()
                (type_, size_) = insUnpack('4sH', 6, readId + '.FULL')
            ins.seek(pos)
            if self._debug: print ' ',record.flags,record.full,record.markerType
        def dumpData(self,record,out):
            if (record.flags,record.full,record.markerType,record.unused5,record.reputation) != self.defaults[1:]:
                record.hasXmrk = True
            if record.hasXmrk:
                try:
                    out.write(struct_pack('=4sH','XMRK',0))
                    out.packSub('FNAM','B',record.flags.dump())
                    value = record.full
                    if value is not None:
                        out.packSub0('FULL',value)
                    out.packSub('TNAM','Bs',record.markerType, record.unused5)
                    # WMI1 not used in FO3, leaving so it doesn't break something
                    out.packRef('WMI1',record.reputation)
                except struct.error:
                    print self.subType,self.format,record.flags,record.full,record.markerType
                    raise

    melSet = MelSet(
        MelString('EDID','eid'),
        MelOptStruct('RCLR','8B','referenceStartColorRed','referenceStartColorGreen','referenceStartColorBlue',('referenceColorUnused1',null1),
                     'referenceEndColorRed','referenceEndColorGreen','referenceEndColorBlue',('referenceColorUnused2',null1)),
        MelFid('NAME','base'),
        MelFid('XEZN','encounterZone'),
        MelBase('XRGD','ragdollData'),
        MelBase('XRGB','ragdollBipedData'),
        MelOptStruct('XPRM','3f3IfI','primitiveBoundX','primitiveBoundY','primitiveBoundX',
                     'primitiveColorRed','primitiveColorGreen','primitiveColorBlue','primitiveUnknown','primitiveType'),
        MelOptStruct('XTRI','I','collisionLayer'),
        MelBase('XMBP','multiboundPrimitiveMarker'),
        MelOptStruct('XMBO','3f','boundHalfExtentsX','boundHalfExtentsY','boundHalfExtentsZ'),
        MelOptStruct('XTEL','I6fI',(FID,'destinationFid'),'destinationPosX','destinationPosY',
            'destinationPosZ','destinationRotX','destinationRotY','destinationRotZ',(_destinationFlags,'destinationFlags')),
        MelRefrXmrk('XMRK','',('hasXmrk',False),(_flags,'flags',0L),'full','markerType',('unused5',null1),(FID,'reputation')), ####Map Marker Start Marker, wbEmpty
        MelFid('XTRG','targetId'),
        MelOptStruct('XLCM','i',('levelMod',None)),
        MelGroup('patrolData',
            MelStruct('XPRD','f','idleTime'),
            MelBase('XPPA','patrolScriptMarker'),
            MelFid('INAM', 'idle'),
            MelStruct('SCHR','4s4I',('unused1',null4),'numRefs','compiledSize','lastIndex','scriptType'),
            MelBase('SCDA','compiled_p'),
            MelString('SCTX','scriptText'),
            MelGroups('vars',
                MelStruct('SLSD','I12sB7s','index',('unused1',null4+null4+null4),(_variableFlags,'flags',0L),('unused2',null4+null3)),
                MelString('SCVR','name')),
            MelScrxen('SCRV/SCRO','references'),
            MelFid('TNAM','topic'),
            ),
        MelOptStruct('XRDO','fIfI','rangeRadius','broadcastRangeType','staticPercentage',(FID,'positionReference')),
        MelOwnership(),
        MelRefrXloc('XLOC','B3sI4sB3s4s','lockLevel',('unused1',null3),(FID,'lockKey'),('unused2',null4),(_lockFlags,'lockFlags'),('unused3',null3),('unused4',null4)),
        MelOptStruct('XCNT','i','count'),
        MelOptStruct('XRDS','f','radius'),
        MelOptStruct('XHLP','f','health'),
        MelOptStruct('XRAD','f','radiation'),
        MelOptStruct('XCHG','f',('charge',None)),
        MelGroup('ammo',
            MelFid('XAMT','type'),
            MelStruct('XAMC','I','count'),
            ),
        MelStructs('XPWR','II','reflectedByWaters',(FID,'reference'),'type'),
        MelFids('XLTW','litWaters'),
        MelStructs('XDCR','II','linkedDecals',(FID,'reference'),'unknown'), # ??
        MelFid('XLKR','linkedReference'),
        MelOptStruct('XCLP','8B','linkStartColorRed','linkStartColorGreen','linkStartColorBlue',('linkColorUnused1',null1),
                     'linkEndColorRed','linkEndColorGreen','linkEndColorBlue',('linkColorUnused2',null1)),
        MelGroup('activateParents',
            MelStruct('XAPD','B','flags'),
            MelStructs('XAPR','If','activateParentRefs',(FID,'reference'),'delay')
            ),
        MelOptStruct('XESP','IB3s',(FID,'parent'),(_parentFlags,'parentFlags'),('unused6',null3)),
        MelOptStruct('XEMI','I',(FID,'emittance')),
        MelFid('XMBR','multiboundReference'),
        MelOptStruct('XACT','I',(_actFlags,'actFlags',0L)), ####Action Flag
        MelBase('ONAM','onam_p'), ####Open by Default, wbEmpty
        MelBase('XIBS','ignoredBySandbox'),
        MelOptStruct('XNDP','2I',(FID,'navMesh'),'unknown'),
        MelOptStruct('XPOD','II',(FID,'portalDataRoom0'),(FID,'portalDataRoom1')),
        MelOptStruct('XPTL','9f','portalWidth','portalHeight','portalPosX','portalPosY','portalPosZ',
                     'portalRot1','portalRot2','portalRot3','portalRot4'),
        MelBase('XSED','speedTreeSeed'),
        ####SpeedTree Seed, if it's a single byte then it's an offset into the list of seed values in the TREE record
        ####if it's 4 byte it's the seed value directly.
        MelGroup('roomData',
            MelStruct('XRMR','H2s','linkedRoomsCount','unknown'),
            MelFids('XLRM','linkedRoom'),
            ),
        MelOptStruct('XOCP','9f','occlusionPlaneWidth','occlusionPlaneHeight','occlusionPlanePosX','occlusionPlanePosY','occlusionPlanePosZ',
                     'occlusionPlaneRot1','occlusionPlaneRot2','occlusionPlaneRot3','occlusionPlaneRot4'),
        MelOptStruct('XORD','4I',(FID,'linkedOcclusionPlane0'),(FID,'linkedOcclusionPlane1'),(FID,'linkedOcclusionPlane2'),(FID,'linkedOcclusionPlane3')),
        MelOptStruct('XLOD','3f',('lod1',None),('lod2',None),('lod3',None)), ####Distant LOD Data, unknown
        MelOptStruct('XSCL','f',('scale',1.0)),
        MelOptStruct('DATA','=6f',('posX',None),('posY',None),('posZ',None),('rotX',None),('rotY',None),('rotZ',None)),

        ##Oblivion subrecords
        #MelOptStruct('XHLT','i',('health',None)),
        #MelXpci('XPCI'), ####fid, unknown
        #MelFid('XRTM','xrtm'), ####unknown
        #MelOptStruct('XSOL','B',('soul',None)), ####Was entirely missing. Confirmed by creating a test mod...it isn't present in any of the official esps
    )
    __slots__ = melSet.getSlotsUsed()

#------------------------------------------------------------------------------
class MreRegn(MelRecord):
    """Region record."""
    classType = 'REGN'
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
    rdatFlags = Flags(0L,Flags.getNames(
        ( 0,'Override'),))

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
        MelString('MICO','smallIconPath'),
        MelStruct('RCLR','3Bs','mapRed','mapBlue','mapGreen',('unused1',null1)),
        MelFid('WNAM','worldspace'),
        MelGroups('areas',
            MelStruct('RPLI','I','edgeFalloff'),
            MelStructA('RPLD','2f','points','posX','posY')),
        MelGroups('entries',
            #2:Objects,3:Weather,4:Map,5:Land,6:Grass,7:Sound
            MelStruct('RDAT', 'I2B2s','entryType', (rdatFlags,'flags'), 'priority', ('unused1',null2)),
            MelRegnStructA('RDOT', 'IH2sf4B2H4s4f3H2s4s', 'objects', (FID,'objectId'), 'parentIndex',
                ('unused1',null2), 'density', 'clustering', 'minSlope', 'maxSlope',
                (obflags, 'flags'), 'radiusWRTParent', 'radius', ('unk1',null4),
                'maxHeight', 'sink', 'sinkVar', 'sizeVar', 'angleVarX',
                'angleVarY',  'angleVarZ', ('unused2',null2), ('unk2',null4)),
            MelRegnString('RDMP', 'mapName'),
            MelRegnStructA('RDGS', 'I4s', 'grass', ('unknown',null4)),
            MelRegnOptStruct('RDMD', 'I', 'musicType'),
            MelFid('RDMO','music'),
            MelRegnStructA('RDSD', '3I', 'sounds', (FID, 'sound'), (sdflags, 'flags'), 'chance'),
            MelRegnStructA('RDWT', '3I', 'weather', (FID, 'weather', None), 'chance', (FID, 'global', None)),
            ),
        )
    __slots__ = melSet.getSlotsUsed()

#------------------------------------------------------------------------------
class MreRgdl(MelRecord):
    """Ragdoll"""
    classType = 'RGDL'
    _flags = Flags(0L,Flags.getNames('disableOnMove'))
    melSet = MelSet(
        MelString('EDID','eid'),
        MelStruct('NVER','I','version'),
        MelStruct('DATA','I4s5Bs','boneCount','unused1','feedback',
            'footIK','lookIK','grabIK','poseMatching','unused2'),
        MelFid('XNAM','actorBase'),
        MelFid('TNAM','bodyPartData'),
        MelStruct('RAFD','13f2i','keyBlendAmount','hierarchyGain','positionGain',
            'velocityGain','accelerationGain','snapGain','velocityDamping',
            'snapMaxLinearVelocity','snapMaxAngularVelocity','snapMaxLinearDistance',
            'snapMaxAngularDistance','posMaxVelLinear',
            'posMaxVelAngular','posMaxVelProjectile','posMaxVelMelee'),
        MelStructA('RAFB','H','feedbackDynamicBones','bone'),
        MelStruct('RAPS','3HBs4f','matchBones1','matchBones2','matchBones3',
            (_flags,'flags'),'unused3','motorsStrength',
            'poseActivationDelayTime','matchErrorAllowance',
            'displacementToDisable',),
        MelString('ANAM','deathPose'),
        )
    __slots__ = melSet.getSlotsUsed()

#------------------------------------------------------------------------------
class MreScol(MelRecord):
    """Static Collection"""
    classType = 'SCOL'
    melSet = MelSet(
        MelString('EDID','eid'),
        MelStruct('OBND','=6h',
                  'boundX1','boundY1','boundZ1',
                  'boundX2','boundY2','boundZ2'),
        MelModel(),
        MelGroups('parts',
            MelFid('ONAM','static'),
            MelStructA('DATA','=7f','placement',('posX',None),('posY',None),('posZ',None),('rotX',None),('rotY',None),('rotZ',None),('scale',None),),
        ),
    )
    __slots__ = melSet.getSlotsUsed()

#------------------------------------------------------------------------------
class MreScpt(MelRecord):
    """Script record."""
    classType = 'SCPT'
    _flags = Flags(0L,Flags.getNames('isLongOrShort'))
    schrFlags = Flags(0L,Flags.getNames('enabled'))
    melSet = MelSet(
        MelString('EDID','eid'),
        #scriptType:0:Object,1:Quest,0x100:Magic Effect
        MelStruct('SCHR','4s3I2H',('unused1',null4),'numRefs','compiledSize',
                  'lastIndex','scriptType',(schrFlags,'enableflag',0L),),
        MelBase('SCDA','compiled_p'),
        MelString('SCTX','scriptText'),
        MelGroups('vars',
            MelStruct('SLSD','I12sB7s','index',('unused1',null4+null4+null4),(_flags,'flags',0L),('unused2',null4+null3)),
            MelString('SCVR','name')),
        MelScrxen('SCRV/SCRO','references'),
    )
    __slots__ = melSet.getSlotsUsed()

#------------------------------------------------------------------------------
class MreSoun(MelRecord):
    """Sound record."""
    classType = 'SOUN'

    # {0x0001} 'Random Frequency Shift',
    # {0x0002} 'Play At Random',
    # {0x0004} 'Environment Ignored',
    # {0x0008} 'Random Location',
    # {0x0010} 'Loop',
    # {0x0020} 'Menu Sound',
    # {0x0040} '2D',
    # {0x0080} '360 LFE',
    # {0x0100} 'Dialogue Sound',
    # {0x0200} 'Envelope Fast',
    # {0x0400} 'Envelope Slow',
    # {0x0800} '2D Radius',
    # {0x1000} 'Mute When Submerged',
    # {0x2000} 'Start at Random Position'
    _flags = Flags(0L,Flags.getNames(
            'randomFrequencyShift',
            'playAtRandom',
            'environmentIgnored',
            'randomLocation',
            'loop',
            'menuSound',
            'twoD',
            'three60LFE',
            'dialogueSound',
            'envelopeFast',
            'envelopeSlow',
            'twoDRadius',
            'muteWhenSubmerged',
        ))

    class MelSounSndx(MelStruct):
        """SNDX is a reduced version of SNDD. Allow it to read in, but not set defaults or write."""
        def loadData(self, record, ins, sub_type, size_, readId):
            MelStruct.loadData(self, record, ins, sub_type, size_, readId)
            record.point0 = 0
            record.point1 = 0
            record.point2 = 0
            record.point3 = 0
            record.point4 = 0
            record.reverb = 0
            record.priority = 0
            record.xLoc = 0
            record.yLoc = 0
        def getSlotsUsed(self):
            return ()
        def setDefault(self,record): return
        def dumpData(self,record,out): return

    melSet = MelSet(
        MelString('EDID','eid'),
        MelStruct('OBND','=6h',
                  'boundX1','boundY1','boundZ1',
                  'boundX2','boundY2','boundZ2'),
        MelString('FNAM','soundFile'),
        MelOptStruct('SNDD','=2BbsIh2B6h3i',('minDist',0), ('maxDist',0),
                    ('freqAdj',0), ('unusedSndd',null1),(_flags,'flags',0L),
                    ('staticAtten',0),('stopTime',0),('startTime',0),
                    ('point0',0),('point1',0),('point2',0),('point3',0),('point4',0),
                    ('reverb',0),('priority',0), ('xLoc',0), ('yLoc',0),),
        MelSounSndx('SNDX','=2BbsIh2B',('minDist',0), ('maxDist',0),
                   ('freqAdj',0), ('unusedSndd',null1),(_flags,'flags',0L),
                   ('staticAtten',0),('stopTime',0),('startTime',0),),
        MelBase('ANAM','_anam'), #--Should be a struct. Maybe later.
        MelBase('GNAM','_gnam'), #--Should be a struct. Maybe later.
        MelBase('HNAM','_hnam'), #--Should be a struct. Maybe later.
        )
    __slots__ = melSet.getSlotsUsed()

#------------------------------------------------------------------------------
class MreSpel(MelRecord,MreHasEffects):
    """Actor Effect"""
    classType = 'SPEL'
    class SpellFlags(Flags):
        """For SpellFlags, immuneSilence activates bits 1 AND 3."""
        def __setitem__(self,index,value):
            setter = Flags.__setitem__
            setter(self,index,value)
            if index == 1:
                setter(self,3,value)
    flags = SpellFlags(0L,Flags.getNames('noAutoCalc', 'immuneToSilence',
        'startSpell',None,'ignoreLOS','scriptEffectAlwaysApplies',
        'disallowAbsorbReflect','touchExplodesWOTarget'))
    melSet = MelSet(
        MelString('EDID','eid'),
        MelFull0(),
        MelStruct('SPIT','3IB3s','spellType','cost','level',(flags,'flags',0L),('unused1',null3)),
        # spellType = 0: Spell, 1: Disease, 3: Lesser Power, 4: Ability, 5: Poison
        MelEffects(),
        )
    __slots__ = melSet.getSlotsUsed()

#------------------------------------------------------------------------------
class MreStat(MelRecord):
    """Static model record."""
    classType = 'STAT'
    melSet = MelSet(
        MelString('EDID','eid'),
        MelStruct('OBND','=6h',
                  'boundX1','boundY1','boundZ1',
                  'boundX2','boundY2','boundZ2'),
        MelModel(),
        )
    __slots__ = melSet.getSlotsUsed()

#------------------------------------------------------------------------------
class MreTact(MelRecord):
    """Talking activator record."""
    classType = 'TACT'
    melSet = MelSet(
        MelString('EDID','eid'),
        MelStruct('OBND','=6h',
                  'boundX1','boundY1','boundZ1',
                  'boundX2','boundY2','boundZ2'),
        MelString('FULL','full'),
        MelModel('model'),
        MelFid('SCRI','script'),
        MelDestructible(),
        MelFid('SNAM','sound'),
        MelFid('VNAM','voiceType'),
        )
    __slots__ = melSet.getSlotsUsed()

#------------------------------------------------------------------------------
class MreTerm(MelRecord):
    """Terminal record."""
    classType = 'TERM'
    _flags = Flags(0L,Flags.getNames('leveled','unlocked','alternateColors','hideWellcomeTextWhenDisplayingImage'))
    _menuFlags = Flags(0L,Flags.getNames('addNote','forceRedraw'))
    _variableFlags = Flags(0L,Flags.getNames('isLongOrShort'))
    class MelTermDnam(MelStruct):
        """Handle older truncated DNAM for TERM subrecord."""
        def loadData(self, record, ins, sub_type, size_, readId):
            if size_ == 4:
                MelStruct.loadData(self, record, ins, sub_type, size_, readId)
                return
            elif size_ == 3:
                unpacked = ins.unpack('BBB', size_, readId)
            else:
                raise "Unexpected size encountered for TERM:DNAM subrecord: %s" % size_
            unpacked += self.defaults[len(unpacked):]
            setter = record.__setattr__
            for attr,value,action in zip(self.attrs,unpacked,self.actions):
                if callable(action): value = action(value)
                setter(attr,value)
            if self._debug: print unpacked
    melSet = MelSet(
        MelString('EDID','eid'),
        MelStruct('OBND','=6h',
                  'boundX1','boundY1','boundZ1',
                  'boundX2','boundY2','boundZ2'),
        MelString('FULL','full'),
        MelModel(),
        MelFid('SCRI','script'),
        MelDestructible(),
        MelString('DESC','description'),
        MelFid('SNAM','soundLooping'),
        MelFid('PNAM','passwordNote'),
        MelTermDnam('DNAM','BBBs','baseHackingDifficulty',(_flags,'flags'),
                    'serverType','unused1',),
        MelGroups('menuItems',
            MelString('ITXT','itemText'),
            MelString('RNAM','resultText'),
            MelStruct('ANAM','B',(_menuFlags,'menuFlags')),
            MelFid('INAM','displayNote'),
            MelFid('TNAM','subMenu'),
            MelStruct('SCHR','4s4I',('unused2',null4),'numRefs','compiledSize',
                      'lastIndex','scriptType'),
            MelBase('SCDA','compiled_p'),
            MelString('SCTX','scriptText'),
            MelGroups('vars',
                MelStruct('SLSD','I12sB7s','index',('unused3',null4+null4+null4),
                         (_variableFlags,'flags',0L),('unused4',null4+null3)),
                MelString('SCVR','name')),
            MelScrxen('SCRV/SCRO','references'),
            MelConditions(),
        ),
    )
    __slots__ = melSet.getSlotsUsed()

#------------------------------------------------------------------------------
class MreTree(MelRecord):
    """Tree record."""
    classType = 'TREE'
    melSet = MelSet(
        MelString('EDID','eid'),
        MelStruct('OBND','=6h',
                  'boundX1','boundY1','boundZ1',
                  'boundX2','boundY2','boundZ2'),
        MelModel(),
        MelString('ICON','iconPath'),
        MelStructA('SNAM','I','speedTree','seed'),
        MelStruct('CNAM','5fi2f', 'curvature','minAngle','maxAngle',
                  'branchDim','leafDim','shadowRadius','rockSpeed',
                  'rustleSpeed'),
        MelStruct('BNAM','2f','widthBill','heightBill'),
        )
    __slots__ = melSet.getSlotsUsed()

#------------------------------------------------------------------------------
class MreTxst(MelRecord):
    """Texture set record."""
    classType = 'TXST'
    TxstTypeFlags = Flags(0L,Flags.getNames(
        (0, 'noSpecularMap'),
    ))

    DecalDataFlags = Flags(0L,Flags.getNames(
            (0, 'parallax'),
            (0, 'alphaBlending'),
            (0, 'alphaTesting'),
            (0, 'noSubtextures'),
        ))

    melSet = MelSet(
        MelString('EDID','eid'),
        MelStruct('OBND','=6h',
                  'boundX1','boundY1','boundZ1',
                  'boundX2','boundY2','boundZ2'),
        MelString('TX00','baseImage'),
        MelString('TX01','normalMap'),
        MelString('TX02','environmentMapMask'),
        MelString('TX03','growMap'),
        MelString('TX04','parallaxMap'),
        MelString('TX05','environmentMap'),
        MelOptStruct('DODT','7fBB2s3Bs','minWidth','maxWidth','minHeight',
                     'maxHeight','depth','shininess','parallaxScale',
                     'parallaxPasses',(DecalDataFlags,'decalFlags',0L),
                     ('unused1',null2),'red','green','blue',('unused2',null1)),
        MelStruct('DNAM','H',(TxstTypeFlags,'flags',0L),),
        )
    __slots__ = melSet.getSlotsUsed()

#------------------------------------------------------------------------------
class MreVtyp(MelRecord):
    """Voice type record."""
    classType = 'VTYP'
    _flags = Flags(0L,Flags.getNames('allowDefaultDialog','female'))
    melSet = MelSet(
        MelString('EDID','eid'),
        MelStruct('DNAM','B',(_flags,'flags')),
        )
    __slots__ = melSet.getSlotsUsed()

#------------------------------------------------------------------------------
class MreWatr(MelRecord):
    """Water record."""
    classType = 'WATR'
    _flags = Flags(0L,Flags.getNames('causesDmg','reflective'))
    class MelWatrData(MelStruct):
        """Handle older truncated DATA for WATR subrecord."""
        def loadData(self, record, ins, sub_type, size_, readId):
            if size_ == 186:
                MelStruct.loadData(self, record, ins, sub_type, size_, readId)
                return
            elif size_ == 2:
                (record.damage,) = ins.unpack('H', size_, readId)
                return
            else:
                raise "Unexpected size encountered for WATR subrecord: %s" % size_
        def dumpData(self,record,out):
            out.packSub(self.subType,'H',record.damage)

    class MelWatrDnam(MelStruct):
        """Handle older truncated DNAM for WATR subrecord."""
        def loadData(self, record, ins, sub_type, size_, readId):
            if size_ == 196:
                MelStruct.loadData(self, record, ins, sub_type, size_, readId)
                return
            elif size_ == 184:
                unpacked = ins.unpack('10f3Bs3Bs3BsI32f', size_, readId)
            else:
                raise ModError(ins.inName, _('Unexpected size encountered for WATR subrecord: ') + str(size_))
            unpacked = unpacked[:-1]
            unpacked += self.defaults[len(unpacked):]
            setter = record.__setattr__
            for attr,value,action in zip(self.attrs,unpacked,self.actions):
                if callable(action): value = action(value)
                setter(attr,value)
            if self._debug: print unpacked

    melSet = MelSet(
        MelString('EDID','eid'),
        MelString('FULL','full'),
        MelString('NNAM','texture'),
        MelStruct('ANAM','B','opacity'),
        MelStruct('FNAM','B',(_flags,'flags',0)),
        MelString('MNAM','material'),
        MelFid('SNAM','sound',),
        MelFid('XNAM','effect'),
        MelWatrData('DATA','10f3Bs3Bs3BsI32fH',('windVelocity',0.100),('windDirection',90.0),
            ('waveAmp',0.5),('waveFreq',1.0),('sunPower',50.0),('reflectAmt',0.5),
            ('fresnelAmt',0.0250),('unknown1',0.0),('fogNear',27852.8),('fogFar',163840.0),
            ('shallowRed',0),('shallowGreen',128),('shallowBlue',128),('unused1',null1),
            ('deepRed',0),('deepGreen',0),('deepBlue',25),('unused2',null1),
            ('reflRed',255),('reflGreen',255),('reflBlue',255),('unused3',null1),
            ('unknown2',0),
            ('rainForce',0.1000),('rainVelocity',0.6000),('rainFalloff',0.9850),('rainDampner',2.0000),('rainSize',0.0100),
            ('dispForce',0.4000),('dispVelocity', 0.6000),('dispFalloff',0.9850),('dispDampner',10.0000),('dispSize',0.0500),
            ('noiseNormalsScale',1.8000),('noiseLayer1WindDirection',0.0000),('noiseLayer2WindDirection',-431602080.0500),
            ('noiseLayer3WindDirection',-431602080.0500),('noiseLayer1WindVelocity',0.0000),
            ('noiseLayer2WindVelocity',-431602080.0500),('noiseLayer3WindVelocity',-431602080.0500),
            ('noiseNormalsDepthFalloffStart',0.00000),('noiseNormalsDepthFalloffEnd',0.10000),
            ('fogAboveWaterAmount',1.00000),('noiseNormalsUvScale',500.00000),
            ('fogUnderWaterAmount',1.00000),('fogUnderWaterNear',0.00000),('fogUnderWaterFar',1000.00000),
            ('distortionAmount',250.00000),('shininess',100.00000),('reflectHdrMult',1.00000),
            ('lightRadius',10000.00000),('lightBrightness',1.00000),
            ('noiseLayer1UvScale',100.00000),('noiseLayer2UvScale',100.00000),('noiseLayer3UvScale',100.00000),
            ('damage',0)),
        MelWatrDnam('DNAM','10f3Bs3Bs3BsI35f',('windVelocity',0.100),('windDirection',90.0),
            ('waveAmp',0.5),('waveFreq',1.0),('sunPower',50.0),('reflectAmt',0.5),
            ('fresnelAmt',0.0250),('unknown1',0.0),('fogNear',27852.8),('fogFar',163840.0),
            ('shallowRed',0),('shallowGreen',128),('shallowBlue',128),('unused1',null1),
            ('deepRed',0),('deepGreen',0),('deepBlue',25),('unused2',null1),
            ('reflRed',255),('reflGreen',255),('reflBlue',255),('unused3',null1),
            ('unknown2',0),
            ('rainForce',0.1000),('rainVelocity',0.6000),('rainFalloff',0.9850),('rainDampner',2.0000),('rainSize',0.0100),
            ('dispForce',0.4000),('dispVelocity', 0.6000),('dispFalloff',0.9850),('dispDampner',10.0000),('dispSize',0.0500),
            ('noiseNormalsScale',1.8000),('noiseLayer1WindDirection',0.0000),('noiseLayer2WindDirection',-431602080.0500),
            ('noiseLayer3WindDirection',-431602080.0500),('noiseLayer1WindVelocity',0.0000),
            ('noiseLayer2WindVelocity',-431602080.0500),('noiseLayer3WindVelocity',-431602080.0500),
            ('noiseNormalsDepthFalloffStart',0.00000),('noiseNormalsDepthFalloffEnd',0.10000),
            ('fogAboveWaterAmount',1.00000),('noiseNormalsUvScale',500.00000),
            ('fogUnderWaterAmount',1.00000),('fogUnderWaterNear',0.00000),('fogUnderWaterFar',1000.00000),
            ('distortionAmount',250.00000),('shininess',100.00000),('reflectHdrMult',1.00000),
            ('lightRadius',10000.00000),('lightBrightness',1.00000),
            ('noiseLayer1UvScale',100.00000),('noiseLayer2UvScale',100.00000),('noiseLayer3UvScale',100.00000),
            ('noiseLayer1Amp',0.00000),('noiseLayer2Amp',0.00000),('noiseLayer3Amp',0.00000),
            ),
        MelFidList('GNAM','relatedWaters'),
        )
    __slots__ = melSet.getSlotsUsed()

#------------------------------------------------------------------------------
class MreWeap(MelRecord):
    """Weapon record."""
    classType = 'WEAP'
    _flags = Flags(0L,Flags.getNames('notNormalWeapon'))
    _dflags1 = Flags(0L,Flags.getNames(
            'ignoresNormalWeaponResistance',
            'isAutomatic',
            'hasScope',
            'cantDrop',
            'hideBackpack',
            'embeddedWeapon',
            'dontUse1stPersonISAnimations',
            'nonPlayable',
        ))
    _dflags2 = Flags(0L,Flags.getNames(
            'playerOnly',
            'npcsUseAmmo',
            'noJamAfterReload',
            'overrideActionPoint',
            'minorCrime',
            'rangeFixed',
            'notUseInNormalCombat',
            'overrideDamageToWeaponMult',
            'dontUse3rdPersonISAnimations',
            'shortBurst',
            'RumbleAlternate',
            'longBurst',
        ))
    _cflags = Flags(0L,Flags.getNames(
            'onDeath',
            'unknown1','unknown2','unknown3','unknown4',
            'unknown5','unknown6','unknown7',
        ))

    class MelWeapDnam(MelStruct):
        """Handle older truncated DNAM for WEAP subrecord."""
        def loadData(self, record, ins, sub_type, size_, readId):
            if size_ == 136:
                MelStruct.loadData(self, record, ins, sub_type, size_, readId)
                return
            elif size_ == 124:
                #--Else 124 byte record (skips sightUsage, semiAutomaticFireDelayMin and semiAutomaticFireDelayMax...
                unpacked = ins.unpack('IffBBBBfffffIBBBBffIIfffffffffffiIffi', size_, readId)
            elif size_ == 120:
                #--Else 120 byte record (skips resistType, sightUsage, semiAutomaticFireDelayMin and semiAutomaticFireDelayMax...
                unpacked = ins.unpack('IffBBBBfffffIBBBBffIIfffffffffffiIff', size_, readId)
            else:
                raise "Unexpected size encountered for WEAP:DNAM subrecord: %s" % size_
            unpacked += self.defaults[len(unpacked):]
            setter = record.__setattr__
            for attr,value,action in zip(self.attrs,unpacked,self.actions):
                if callable(action): value = action(value)
                setter(attr,value)
            if self._debug: print unpacked

    melSet = MelSet(
        MelString('EDID','eid'),
        MelStruct('OBND','=6h',
                  'boundX1','boundY1','boundZ1',
                  'boundX2','boundY2','boundZ2'),
        MelString('FULL','full'),
        MelModel('model'),
        MelString('ICON','iconPath'),
        MelString('MICO','smallIconPath'),
        MelFid('SCRI','script'),
        MelFid('EITM','objectEffect'),
        MelOptStruct('EAMT','H','objectEffectPoints'),
        MelFid('NAM0','ammo'),
        MelDestructible(),
        MelFid('REPL','repairList'),
        #0:bigGuns,1:energyWeapons,2:smallGuns,3:meleeWeapons,4:unarmedWeapon,5:thrownWeapons,6:mine,
        MelStruct('ETYP','i',('etype',-1)),
        MelFid('BIPL','bipedModelList'),
        MelFid('YNAM','pickupSound'),
        MelFid('ZNAM','dropSound'),
        MelModel('shellCasingModel',2),
        MelModel('scopeModel',3),
        MelFid('EFSD','scopeEffect'),
        MelModel('worldModel',4),
        MelString('NNAM','embeddedWeaponNode'),
        MelFid('INAM','impactDataset'),
        MelFid('WNAM','firstPersonModel'),
        MelFid('SNAM','soundGunShot3D'),
        MelFid('XNAM','soundGunShot2D'),
        MelFid('NAM7','soundGunShot3DLooping'),
        MelFid('TNAM','soundMeleeSwingGunNoAmmo'),
        MelFid('NAM6','soundBlock'),
        MelFid('UNAM','idleSound',),
        MelFid('NAM9','equipSound',),
        MelFid('NAM8','unequipSound',),
        MelStruct('DATA','2IfHB','value','health','weight','damage','clipsize'),
        MelWeapDnam('DNAM','IffBBBBfffffIBBBBffIIfffffffffffiIffifff',
                    'animationType','animationMultiplier','reach',
                    (_dflags1,'dnamFlags1',0L),('gripAnimation',255),'ammoUse',
                    'reloadAnimation','minSpread','spread','weapDnam1','sightFov',
                    ('weapDnam2',0.0),(FID,'projectile',0L),'baseVatsToHitChance',
                    ('attackAnimation',255),'projectileCount','embeddedWeaponActorValue',
                    'minRange','maxRange','onHit',(_dflags2,'dnamFlags2',0L),
                    'animationAttackMultiplier','fireRate','overrideActionPoint',
                    'rumbleLeftMotorStrength','rumbleRightMotorStrength',
                    'rumbleDuration','overrideDamageToWeaponMult','attackShotsPerSec',
                    'reloadTime','jamTime','aimArc',('skill',45),'rumblePattern',
                    'rambleWavelangth','limbDmgMult',('resistType',-1),
                    'sightUsage','semiAutomaticFireDelayMin',
                    'semiAutomaticFireDelayMax',),
        MelOptStruct('CRDT','H2sfB3sI',('criticalDamage', 0),('weapCrdt1', null2),
                     ('criticalMultiplier', 0.0),(_cflags,'criticalFlags', 0L),
                     ('weapCrdt2', null3),(FID,'criticalEffect', 0)),
        MelBase('VNAM','soundLevel'),
        )
    __slots__ = melSet.getSlotsUsed()

#------------------------------------------------------------------------------
class MreWrld(MelRecord):
    """Worldspace record."""
    classType = 'WRLD'
    _flags = Flags(0L,Flags.getNames('smallWorld','noFastTravel','oblivionWorldspace',None,
        'noLODWater','noLODNoise','noAllowNPCFallDamage'))
    pnamFlags = Flags(0L,Flags.getNames(
        'useLandData','useLODData','useMapData','useWaterData','useClimateData',
        'useImageSpaceData',None,'needsWaterAdjustment'))
    melSet = MelSet(
        MelString('EDID','eid'),
        MelString('FULL','full'),
        MelFid('XEZN','encounterZone'),
        MelFid('WNAM','parent'),
        MelOptStruct('PNAM','BB',(pnamFlags,'parentFlags',0L),('unknownff',0xff)),
        MelFid('CNAM','climate'),
        MelFid('NAM2','water'),
        MelFid('NAM3','waterType'),
        MelStruct('NAM4','f','waterHeight'),
        MelStruct('DNAM','ff','defaultLandHeight','defaultWaterHeight'),
        MelString('ICON','mapPath'),
        MelOptStruct('MNAM','2i4h',('dimX',None),('dimY',None),('NWCellX',None),('NWCellY',None),('SECellX',None),('SECellY',None)),
        MelStruct('ONAM','fff','worldMapScale','cellXOffset','cellYOffset'),
        MelFid('INAM','imageSpace'),
        MelStruct('DATA','B',(_flags,'flags',0L)),
        MelTuple('NAM0','ff','unknown0',(None,None)),
        MelTuple('NAM9','ff','unknown9',(None,None)),
        MelFid('ZNAM','music'),
        MelString('NNAM','canopyShadow'),
        MelString('XNAM','waterNoiseTexture'),
        MelStructs('IMPS','III','swappedImpacts', 'materialType',(FID,'old'),(FID,'new')),
        MelBase('IMPF','footstepMaterials'), #--todo rewrite specific class.
        MelBase('OFST','ofst_p'),
    )
    __slots__ = melSet.getSlotsUsed()

#------------------------------------------------------------------------------
class MelPnamNam0Handler(MelStructA):
    """Handle older truncated PNAM for WTHR subrecord."""
    def __init__(self, type_, attr):
        MelStructA.__init__(self, type_, '3Bs3Bs3Bs3Bs', attr,
            'riseRed','riseGreen','riseBlue', ('unused1',null1),
            'dayRed','dayGreen','dayBlue', ('unused2',null1),
            'setRed','setGreen','setBlue', ('unused3',null1),
            'nightRed','nightGreen','nightBlue', ('unused4',null1),
                            )

    def loadData(self, record, ins, sub_type, size_, readId):
        """Handle older truncated PNAM for WTHR subrecord."""
        if (sub_type == 'PNAM' and size_ == 64) or (sub_type == 'NAM0' and size_ ==
            160):
            MelStructA.loadData(self, record, ins, sub_type, size_, readId)
            return
        elif (sub_type == 'PNAM' and size_ == 48) or (sub_type == 'NAM0' and size_ == 120):
            oldFormat = '3Bs3Bs3Bs'
            ## Following code works completely, but it's depend on the implementation of MelStructA.loadData and MelStruct.loadData.
            # newFormat = self.format
            # self.format = oldFormat # temporarily set to older format
            # MelStructA.loadData(self,record,ins,type,size,readId)
            # self.format = newFormat
            ## Following code is redundant but independent and robust.
            selfDefault = self.getDefault
            recordAppend = record.__getattribute__(self.attr).append
            selfAttrs = self.attrs
            itemSize = struct.calcsize(oldFormat)
            for x in xrange(size_/itemSize):
                target = selfDefault()
                recordAppend(target)
                target.__slots__ = selfAttrs
                unpacked = ins.unpack(oldFormat,itemSize,readId)
                setter = target.__setattr__
                for attr,value,action in zip(selfAttrs,unpacked,self.actions):
                    if action: value = action(value)
                    setter(attr,value)
        else:
            raise ModSizeError(record.inName, record.recType +'.' + sub_type, (64 if sub_type == 'PNAM' else 160), size_, True)

class MreWthr(MelRecord):
    """Weather record."""
    classType = 'WTHR'
    melSet = MelSet(
        MelString('EDID','eid'),
        MelFid("\x00IAD", 'sunriseImageSpaceModifier'),
        MelFid("\x01IAD", 'dayImageSpaceModifier'),
        MelFid("\x02IAD", 'sunsetImageSpaceModifier'),
        MelFid("\x03IAD", 'nightImageSpaceModifier'),
        MelString('DNAM','upperLayer'),
        MelString('CNAM','lowerLayer'),
        MelString('ANAM','layer2'),
        MelString('BNAM','layer3'),
        MelModel(),
        MelBase('LNAM','unknown1'),
        MelStruct('ONAM','4B','cloudSpeed0','cloudSpeed1','cloudSpeed3','cloudSpeed4'),
        # MelPnamNam0Handler('PNAM','cloudColors'),
        MelStructA('PNAM','3Bs3Bs3Bs3Bs','cloudColors',
            'riseRed','riseGreen','riseBlue',('unused1',null1),
            'dayRed','dayGreen','dayBlue',('unused2',null1),
            'setRed','setGreen','setBlue',('unused3',null1),
            'nightRed','nightGreen','nightBlue',('unused4',null1),
            ),
        # MelPnamNam0Handler('NAM0','daytimeColors'),
        MelStructA('NAM0','3Bs3Bs3Bs3Bs','daytimeColors',
            'riseRed','riseGreen','riseBlue',('unused1',null1),
            'dayRed','dayGreen','dayBlue',('unused2',null1),
            'setRed','setGreen','setBlue',('unused3',null1),
            'nightRed','nightGreen','nightBlue',('unused4',null1),
            ),
        MelStruct('FNAM','6f','fogDayNear','fogDayFar','fogNightNear','fogNightFar','fogDayPower','fogNightPower'),
        MelBase('INAM','_inam'), #--Should be a struct. Maybe later.
        MelStruct('DATA','15B',
            'windSpeed','lowerCloudSpeed','upperCloudSpeed','transDelta',
            'sunGlare','sunDamage','rainFadeIn','rainFadeOut','boltFadeIn',
            'boltFadeOut','boltFrequency','weatherType','boltRed','boltBlue','boltGreen'),
        MelStructs('SNAM','2I','sounds',(FID,'sound'),'type'),
        )
    __slots__ = melSet.getSlotsUsed()

