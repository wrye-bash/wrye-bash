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
"""This module contains the skyrim record classes."""
import itertools
import struct

from .constants import allConditions, fid1Conditions, fid2Conditions, \
    fid5Conditions
from ... import brec
from ...bass import null1, null2, null3, null4
from ...bolt import Flags, DataDict, winNewLines, encode, struct_pack, \
    struct_unpack
from ...brec import MelRecord, MelStructs, MelObject, MelGroups, MelStruct, \
    FID, MelGroup, MelString, MreLeveledListBase, MelSet, MelFid, MelNull, \
    MelOptStruct, MelFids, MreHeaderBase, MelBase, MelUnicode, MelFidList, \
    MelStructA, MreRecord, MreGmstBase, MelLString, MelCountedFidList, \
    MelCountedFids, MelSortedFidList, MelStrings, MelMODS, MreHasEffects
from ...exception import BoltError, ModError, ModSizeError, StateError
# Set MelModel in brec but only if unset, otherwise we are being imported from
# fallout4.records
if brec.MelModel is None:
    class _MelModel(brec.MelGroup):
        """Represents a model record."""
        # MODB and MODD are no longer used by TES5Edit
        typeSets = {'MODL': ('MODL', 'MODT', 'MODS'),
                    'MOD2': ('MOD2', 'MO2T', 'MO2S'),
                    'MOD3': ('MOD3', 'MO3T', 'MO3S'),
                    'MOD4': ('MOD4', 'MO4T', 'MO4S'),
                    'MOD5': ('MOD5', 'MO5T', 'MO5S'),
                    'DMDL': ('DMDL', 'DMDT', 'DMDS'), }

        def __init__(self, attr='model', subType='MODL'):
            """Initialize."""
            types = self.__class__.typeSets[subType]
            MelGroup.__init__(self, attr, MelString(types[0], 'modPath'),
                              # Ignore texture hashes - they're only an
                              # optimization, plenty of records in Skyrim.esm
                              # are missing them
                              MelNull(types[1]),
                              MelMODS(types[2], 'alternateTextures'), )

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
class MelBipedObjectData(MelStruct):
    """Handler for BODT/BOD2 subrecords.  Reads both types, writes only BOD2"""
    BipedFlags = Flags(0L,Flags.getNames(
            (0, 'head'),
            (1, 'hair'),
            (2, 'body'),
            (3, 'hands'),
            (4, 'forearms'),
            (5, 'amulet'),
            (6, 'ring'),
            (7, 'feet'),
            (8, 'calves'),
            (9, 'shield'),
            (10, 'bodyaddon1_tail'),
            (11, 'long_hair'),
            (12, 'circlet'),
            (13, 'bodyaddon2'),
            (14, 'dragon_head'),
            (15, 'dragon_lwing'),
            (16, 'dragon_rwing'),
            (17, 'dragon_body'),
            (18, 'bodyaddon7'),
            (19, 'bodyaddon8'),
            (20, 'decapate_head'),
            (21, 'decapate'),
            (22, 'bodyaddon9'),
            (23, 'bodyaddon10'),
            (24, 'bodyaddon11'),
            (25, 'bodyaddon12'),
            (26, 'bodyaddon13'),
            (27, 'bodyaddon14'),
            (28, 'bodyaddon15'),
            (29, 'bodyaddon16'),
            (30, 'bodyaddon17'),
            (31, 'fx01'),
        ))

    ## Legacy Flags, (For BODT subrecords) - #4 is the only one not discarded.
    LegacyFlags = Flags(0L,Flags.getNames(
            (0, 'modulates_voice'), #{>>> From ARMA <<<}
            (1, 'unknown_2'),
            (2, 'unknown_3'),
            (3, 'unknown_4'),
            (4, 'non_playable'), #{>>> From ARMO <<<}
        ))

    ArmorTypeFlags = Flags(0L,Flags.getNames(
        (0, 'light_armor'),
        (1, 'heavy_armor'),
        (2, 'clothing'),
        ))

    def __init__(self):
        MelStruct.__init__(self,'BOD2','=2I',(MelBipedObjectData.BipedFlags,'bipedFlags',0L),(MelBipedObjectData.ArmorTypeFlags,'armorFlags',0L))

    def getLoaders(self,loaders):
        # Loads either old style BODT or new style BOD2 records
        loaders['BOD2'] = self
        loaders['BODT'] = self

    def loadData(self, record, ins, sub_type, size_, readId):
        if sub_type == 'BODT':
            # Old record type, use alternate loading routine
            if size_ == 8:
                # Version 20 of this subrecord is only 8 bytes (armorType omitted)
                bipedFlags,legacyData = ins.unpack('=2I', size_, readId)
                armorFlags = 0
            elif size_ != 12:
                raise ModSizeError(ins.inName, readId, 12, size_, True)
            else:
                bipedFlags,legacyData,armorFlags = ins.unpack('=3I', size_, readId)
            # legacyData is discarded except for non-playable status
            setter = record.__setattr__
            setter('bipedFlags',MelBipedObjectData.BipedFlags(bipedFlags))
            legacyFlags = MelBipedObjectData.LegacyFlags(legacyData)
            record.flags1[2] = legacyFlags[4]
            setter('armorFlags',MelBipedObjectData.ArmorTypeFlags(armorFlags))
        else:
            # BOD2 - new style, MelStruct can handle it
            MelStruct.loadData(self, record, ins, sub_type, size_, readId)

class MelAttackData(MelStruct):
    """Wrapper around MelStruct to share some code between the NPC_ and RACE
    definitions."""
    DataFlags = Flags(0L, Flags.getNames('ignoreWeapon', 'bashAttack',
                                         'powerAttack', 'leftAttack',
                                         'rotatingAttack', 'unknown6',
                                         'unknown7', 'unknown8', 'unknown9',
                                         'unknown10', 'unknown11', 'unknown12',
                                         'unknown13', 'unknown14', 'unknown15',
                                         'unknown16',))

    def __init__(self):
        MelStruct.__init__(self, 'ATKD', '2f2I3fI3f', 'damageMult',
                           'attackChance', (FID, 'attackSpell'),
                           (MelAttackData.DataFlags, 'attackDataFlags', 0L),
                           'attackAngle', 'strikeAngle', 'stagger',
                           (FID, 'attackType'), 'knockdown', 'recoveryTime',
                           'staminaMult')

#------------------------------------------------------------------------------
class MelBounds(MelStruct):
    def __init__(self):
        MelStruct.__init__(self,'OBND','=6h',
            'boundX1','boundY1','boundZ1',
            'boundX2','boundY2','boundZ2')

#------------------------------------------------------------------------------
class MelCoed(MelOptStruct):
    """Needs custom unpacker to look at FormID type of owner.  If owner is an
    NPC then it is followed by a FormID.  If owner is a faction then it is
    followed by an signed integer or '=Iif' instead of '=IIf' """ # see #282
    def __init__(self):
        MelOptStruct.__init__(self,'COED','=IIf',(FID,'owner'),(FID,'glob'),
                              'itemCondition')
#------------------------------------------------------------------------------
class MelColorN(MelOptStruct):
        def __init__(self):
                MelOptStruct.__init__(self,'CNAM','=4B',
                        'red','green','blue','unused')

#------------------------------------------------------------------------------
class MelComponents(MelStructs):
    """Handle writing COCT subrecord for the CNTO subrecord"""
    def dumpData(self,record,out):
        components = record.__getattribute__(self.attr)
        if components:
            # Only write the COCT/CNTO subrecords if count > 0
            out.packSub('COCT','I',len(components))
            MelStructs.dumpData(self,record,out)

#------------------------------------------------------------------------------
class MelCTDAHandler(MelStructs):
    """Represents the CTDA subrecord and it components. Difficulty is that FID
    state of parameters depends on function index."""
    def __init__(self):
        """Initialize."""
        MelStructs.__init__(self,'CTDA','=B3sfH2siiIIi','conditions',
            'operFlag',('unused1',null3),'compValue','ifunc',('unused2',null2),
            'param1','param2','runOn','reference','param3')

    def getDefault(self):
        """Returns a default copy of object."""
        target = MelStructs.getDefault(self)
        target.form12345 = 'iiIIi'
        return target

    def hasFids(self,formElements):
        """Include self if has fids."""
        formElements.add(self)

    def loadData(self, record, ins, sub_type, size_, readId):
        """Reads data from ins into record attribute."""
        if sub_type == 'CTDA':
            if size_ != 32 and size_ != 28 and size_ != 24 and size_ != 20:
                raise ModSizeError(ins.inName, readId, 32, size_, False)
        else:
            raise ModError(ins.inName,_(u'Unexpected subrecord: ')+readId)
        target = MelObject()
        record.conditions.append(target)
        target.__slots__ = self.attrs
        unpacked1 = ins.unpack('=B3sfH2s',12,readId)
        (target.operFlag,target.unused1,target.compValue,ifunc,target.unused2) = unpacked1
        #--Get parameters
        if ifunc not in allConditions:
            raise BoltError(u'Unknown condition function: %d\nparam1: %08X\nparam2: %08X' % (ifunc,ins.unpackRef(), ins.unpackRef()))
        # Form1 is Param1
        form1 = 'I' if ifunc in fid1Conditions else 'i'
        # Form2 is Param2
        form2 = 'I' if ifunc in fid2Conditions else 'i'
        # Form3 is runOn
        form3 = 'I'
        # Form4 is reference, this is a formID when runOn = 2
        form4 = 'I'
        # Form5 is Param3
        form5 = 'I' if ifunc in fid5Conditions else 'i'
        if size_ == 32:
            form12345 = form1+form2+form3+form4+form5
            unpacked2 = ins.unpack(form12345,20,readId)
            (target.param1,target.param2,target.runOn,target.reference,target.param3) = unpacked2
        elif size_ == 28:
            form12345 = form1+form2+form3+form4
            unpacked2 = ins.unpack(form12345,16,readId)
            (target.param1,target.param2,target.runOn,target.reference) = unpacked2
            target.param3 = null4
        elif size_ == 24:
            form12345 = form1+form2+form3
            unpacked2 = ins.unpack(form12345,12,readId)
            (target.param1,target.param2,target.runOn) = unpacked2
            target.reference = null4
            target.param3 = null4
        elif size_ == 20:
            form12345 = form1+form2
            unpacked2 = ins.unpack(form12345,8,readId)
            (target.param1,target.param2) = unpacked2
            target.runOn = null4
            target.reference = null4
            target.param3 = null4
        # form12 = form1+form2
        # unpacked2 = ins.unpack(form12,8,readId)
        # (target.param1,target.param2) = unpacked2
        # target.unused3,target.reference,target.unused4 = ins.unpack('=4s2I',12,readId)
        else:
            raise ModSizeError(ins.inName, readId, 32, size_, False)
        (target.ifunc,target.form12345) = (ifunc,form12345)
        if self._debug:
            unpacked = unpacked1+unpacked2
            print u' ',zip(self.attrs,unpacked)
            if len(unpacked) != len(self.attrs):
                print u' ',unpacked

    def dumpData(self,record,out):
        """Dumps data from record to outstream."""
        for target in record.conditions:
            ##format = '=B3sfH2s'+target.form12345,
            out.packSub('CTDA','=B3sfH2s'+target.form12345,
                target.operFlag, target.unused1, target.compValue,
                target.ifunc, target.unused2, target.param1, target.param2,
                target.runOn, target.reference, target.param3)

    def mapFids(self,record,function,save=False):
        """Applies function to fids. If save is true, then fid is set
        to result of function."""
        for target in record.conditions:
            form12345 = target.form12345
            if form12345[0] == 'I':
                result = function(target.param1)
                if save: target.param1 = result
            if form12345[1] == 'I':
                result = function(target.param2)
                if save: target.param2 = result
            # runOn is intU32, never FID, and Enum in TES5Edit
            #0:Subject,1:Target,2:Reference,3:Combat Target,4:Linked Reference
            #5:Quest Alias,6:Package Data,7:Event Data'
            if len(form12345) > 3 and form12345[3] == 'I' and target.runOn == 2:
                result = function(target.reference)
                if save: target.reference = result
            if len(form12345) > 4 and form12345[4] == 'I':
                result = function(target.param3)
                if save: target.param3 = result

class MelConditions(MelGroups):
    """Represents a set of quest/dialog/etc conditions"""

    def __init__(self,attr='conditions'):
        """Initialize elements."""
        MelGroups.__init__(self,attr,
            MelCTDAHandler(),
            MelString('CIS1','param_cis1'),
            MelString('CIS2','param_cis2'),
            )

#------------------------------------------------------------------------------
class MelDecalData(MelOptStruct):
    """Represents Decal Data."""

    DecalDataFlags = Flags(0L,Flags.getNames(
            (0, 'parallax'),
            (1, 'alphaBlending'),
            (2, 'alphaTesting'),
            (3, 'noSubtextures'),
        ))

    def __init__(self,attr='decals'):
        """Initialize elements."""
        MelOptStruct.__init__(self,'DODT','7f2B2s3Bs','minWidth','maxWidth','minHeight',
                  'maxHeight','depth','shininess','parallaxScale',
                  'parallaxPasses',(MelDecalData.DecalDataFlags,'flags',0L),('unknownDecal1',null2),
                  'redDecal','greenDecal','blueDecal',('unknownDecal2',null1),
            )

#------------------------------------------------------------------------------
class MelDestructible(MelGroup):
    """Represents a set of destruct record."""

    MelDestStageFlags = Flags(0L,Flags.getNames(
        (0, 'capDamage'),
        (1, 'disable'),
        (2, 'destroy'),
        (3, 'ignoreExternalDmg'),
        ))

    def __init__(self,attr='destructible'):
        """Initialize elements."""
        MelGroup.__init__(self,attr,
            MelStruct('DEST','i2B2s','health','count','vatsTargetable','dest_unused'),
            MelGroups('stages',
                MelStruct('DSTD','=4Bi2Ii','health','index','damageStage',
                         (MelDestructible.MelDestStageFlags,'flags',0L),'selfDamagePerSecond',
                         (FID,'explosion',None),(FID,'debris',None),'debrisCount'),
                MelModel('model','DMDL'),
                MelBase('DSTF','footer'),
            ),
        )

#------------------------------------------------------------------------------
class MelEffects(MelGroups):
    """Represents ingredient/potion/enchantment/spell effects."""

    def __init__(self,attr='effects'):
        """Initialize elements."""
        MelGroups.__init__(self,attr,
            MelFid('EFID','name'), # baseEffect, name
            MelStruct('EFIT','f2I','magnitude','area','duration',),
            MelConditions(),
            )

#------------------------------------------------------------------------------
class MelIcons(MelGroup):
    """Handles ICON and MICO."""

    def __init__(self,attr='iconsIaM'):
        """Initialize."""
        # iconsIaM = icons ICON and MICO
        MelGroup.__init__(self,attr,
            MelString('ICON','iconPath'),
            MelString('MICO','smallIconPath'),
        )
    def dumpData(self,record,out):
        """Dumps data from record to outstream."""
        if record.iconsIaM and record.iconsIaM.iconPath:
            MelGroup.dumpData(self,record,out)
        if record.iconsIaM and record.iconsIaM.smallIconPath:
            MelGroup.dumpData(self,record,out)

#------------------------------------------------------------------------------
class MelIcons2(MelGroup):
    """Handles ICON and MICO."""

    def __init__(self,attr='iconsIaM2'):
        """Initialize."""
        # iconsIaM = icons ICON and MICO
        MelGroup.__init__(self,attr,
            MelString('ICO2','iconPath2'),
            MelString('MIC2','smallIconPath2'),
        )
    def dumpData(self,record,out):
        """Dumps data from record to outstream."""
        if record.iconsIaM and record.iconsIaM.iconPath2:
            MelGroup.dumpData(self,record,out)
        if record.iconsIaM and record.iconsIaM.smallIconPath2:
            MelGroup.dumpData(self,record,out)

#------------------------------------------------------------------------------
class MelKeywords(MelCountedFidList):
    """Wraps MelCountedFidList for the common task of defining a list of
    keywords"""
    def __init__(self):
        MelCountedFidList.__init__(self, countedType='KWDA', attr='keywords',
                                   counterType='KSIZ')

#------------------------------------------------------------------------------
class MelOwnership(MelGroup):
    """Handles XOWN, XRNK for cells and cell children."""

    def __init__(self,attr='ownership'):
        """Initialize."""
        MelGroup.__init__(self,attr,
            MelFid('XOWN','owner'),
            MelOptStruct('XRNK','i',('rank',None)),
        )

    def dumpData(self,record,out):
        """Dumps data from record to outstream."""
        if record.ownership and record.ownership.owner:
            MelGroup.dumpData(self,record,out)

#------------------------------------------------------------------------------
class MelPerks(MelStructs):
    """Handle writing PRKZ subrecord for the PRKR subrecord"""
    def dumpData(self,record,out):
        perks = record.__getattribute__(self.attr)
        if perks:
            out.packSub('PRKZ','<I',len(perks))
            MelStructs.dumpData(self,record,out)

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

# Probably obsolete.  Included for reference and testing.
#------------------------------------------------------------------------------
class MelString16(MelString):
    """Represents a mod record string element."""
    def loadData(self, record, ins, sub_type, size_, readId):
        """Reads data from ins into record attribute."""
        strLen, = ins.unpack('H',2,readId)
        value = ins.readString(strLen,readId)
        record.__setattr__(self.attr,value)
        if self._debug: print u' ',record.__getattribute__(self.attr)

    def dumpData(self,record,out):
        """Dumps data from record to outstream."""
        value = record.__getattribute__(self.attr)
        if value is not None:
            if self.maxSize:
                value = winNewLines(value.rstrip())
                str_size = min(self.maxSize,len(value))
                test,encoding_ = encode(value,returnEncoding=True)
                extra_encoded = len(test) - self.maxSize
                if extra_encoded > 0:
                    total = 0
                    i = -1
                    while total < extra_encoded:
                        total += len(value[i].encode(encoding_))
                        i -= 1
                    str_size += i + 1
                    value = value[:str_size]
                    value = encode(value,firstEncoding=encoding_)
                else:
                    value = test
            else:
                value = encode(value)
            value = struct_pack('H',len(value))+value
            out.packSub0(self.subType,value)

#------------------------------------------------------------------------------
class MelString32(MelString):
    """Represents a mod record string element."""
    def loadData(self, record, ins, sub_type, size_, readId):
        """Reads data from ins into record attribute."""
        strLen, = ins.unpack('I',4,readId)
        value = ins.readString(strLen,readId)
        record.__setattr__(self.attr,value)
        if self._debug: print u' ',record.__getattribute__(self.attr)

    def dumpData(self,record,out):
        """Dumps data from record to outstream."""
        value = record.__getattribute__(self.attr)
        if value is not None:
            if self.maxSize:
                value = winNewLines(value.rstrip())
                str_size = min(self.maxSize,len(value))
                test,encoding_ = encode(value,returnEncoding=True)
                extra_encoded = len(test) - self.maxSize
                if extra_encoded > 0:
                    total = 0
                    i = -1
                    while total < extra_encoded:
                        total += len(value[i].encode(encoding_))
                        i -= 1
                    str_size += i + 1
                    value = value[:str_size]
                    value = encode(value,firstEncoding=encoding_)
                else:
                    value = test
            else:
                value = encode(value)
            value = struct_pack('I',len(value))+value
            out.packSub0(self.subType,value)

#------------------------------------------------------------------------------
class MelVmad(MelBase):
    """Virtual Machine data (VMAD)"""
    # Maybe use this later for better access to Fid,Aid pairs?
    ##ObjectRef = collections.namedtuple('ObjectRef',['fid','aid'])
    class FragmentInfo(object):
        __slots__ = ('unk','fileName',)
        def __init__(self):
            self.unk = 2
            self.fileName = u''

        def loadData(self,ins,Type,readId):
            if Type == 'INFO':
                # INFO record fragment scripts are by default stored in a TIF file,
                # i.e., a file named "TIF_<editorID>_<formID>". Since most INFO records
                # do not have an editorID, this actually ends up being "TIF__<formID>"
                # (with two underscores, not one).
                raise Exception(u"Fragment Scripts for 'INFO' records are not implemented.")
            elif Type == 'PACK':
                self.unk,count = ins.unpack('=bB',2,readId)
                self.fileName = ins.readString16(readId)
                count = bin(count).count('1')
            elif Type == 'PERK':
                self.unk, = ins.unpack('=b',1,readId)
                self.fileName = ins.readString16(readId)
                count, = ins.unpack('=H',2,readId)
            elif Type == 'QUST':
                self.unk,count = ins.unpack('=bH',3,readId)
                self.fileName = ins.readString16(readId)
            elif Type == 'SCEN':
                # SCEN record fragment scripts are by default stored in a SF file,
                # i.e., a file named "SF_<editorID>_<formID>".
                raise Exception(u"Fragment Scripts for 'SCEN' records are not implemented.")
            else:
                raise Exception(u"Unexpected Fragment Scripts for record type '%s'." % Type)
            return count

        def dumpData(self,Type,count):
            fileName = encode(self.fileName)
            if Type == 'INFO':
                raise Exception(u"Fragment Scripts for 'INFO' records are not implemented.")
            elif Type == 'PACK':
                # TODO: check if this is right!
                count = int(count*'1',2)
                data = struct_pack('=bBH', self.unk, count,
                                   len(fileName)) + fileName
            elif Type == 'PERK':
                data = struct_pack('=bH', self.unk, len(fileName)) + fileName
                data += struct_pack('=H', count)
            elif Type == 'QUST':
                data = struct_pack('=bHH', self.unk, count,
                                   len(fileName)) + fileName
            elif Type == 'SCEN':
                raise Exception(u"Fragment Scripts for 'SCEN' records are not implemented.")
            else:
                raise Exception(u"Unexpected Fragment Scripts for record type '%s'." % Type)
            return data

    class INFOFragment(object):
        pass

    class PACKFragment(object):
        __slots__ = ('unk','scriptName','fragmentName',)
        def __init__(self):
            self.unk = 0
            self.scriptName = u''
            self.fragmentName = u''

        def loadData(self,ins,readId):
            self.unk, = ins.unpack('=b',1,readId)
            self.scriptName = ins.readString16(readId)
            self.fragmentName = ins.readString16(readId)

        def dumpData(self):
            scriptName = encode(self.scriptName)
            fragmentName = encode(self.fragmentName)
            data = struct_pack('=bH', self.unk, len(scriptName)) + scriptName
            data += struct_pack('=H', len(fragmentName)) + fragmentName
            return data

    class PERKFragment(object):
        __slots__ = ('index','unk1','unk2','scriptName','fragmentName',)
        def __init__(self):
            self.index = -1
            self.unk1 = 0
            self.unk2 = 0
            self.scriptName = u''
            self.fragmentName= u''

        def loadData(self,ins,readId):
            self.index,self.unk1,self.unk2 = ins.unpack('=Hhb',4,readId)
            self.scriptName = ins.readString16(readId)
            self.fragmentName = ins.readString16(readId)

        def dumpData(self):
            scriptName = encode(self.scriptName)
            fragmentName = encode(self.fragmentName)
            data = struct_pack('=HhbH', self.index, self.unk1, self.unk2,
                               len(scriptName)) + scriptName
            data += struct_pack('=H', len(fragmentName)) + fragmentName
            return data

    class QUSTFragment(object):
        __slots__ = ('index','unk1','logentry','unk2','scriptName','fragmentName',)
        def __init__(self):
            self.index = -1
            self.unk1 = 0
            self.logentry = 0
            self.unk2 = 1
            self.scriptName = u''
            self.fragmentName = u''

        def loadData(self,ins,readId):
            self.index,self.unk1,self.logentry,self.unk2 = ins.unpack('=Hhib',9,readId)
            self.scriptName = ins.readString16(readId)
            self.fragmentName = ins.readString16(readId)

        def dumpData(self):
            scriptName = encode(self.scriptName)
            fragmentName = encode(self.fragmentName)
            data = struct_pack('=HhibH', self.index, self.unk1, self.logentry,
                               self.unk2, len(scriptName)) + scriptName
            data += struct_pack('=H', len(fragmentName)) + fragmentName
            return data

    class SCENFragment(object):
        pass

    FragmentMap = {'INFO': INFOFragment,
                   'PACK': PACKFragment,
                   'PERK': PERKFragment,
                   'QUST': QUSTFragment,
                   'SCEN': SCENFragment,
                   }

    class Property(object):
        __slots__ = ('name','status','value',)
        def __init__(self):
            self.name = u''
            self.status = 1
            self.value = None

        def loadData(self,ins,version,objFormat,readId):
            insUnpack = ins.unpack
            # Script Property
            self.name = ins.readString16(readId)
            if version >= 4:
                Type,self.status = insUnpack('=2B',2,readId)
            else:
                Type, = insUnpack('=B',1,readId)
                self.status = 1
            # Data
            if Type == 1:
                # Object (8 Bytes)
                if objFormat == 1:
                    fid,aid,nul = insUnpack('=IHH',8,readId)
                else:
                    nul,aid,fid = insUnpack('=HHI',8,readId)
                self.value = (fid,aid)
            elif Type == 2:
                # String
                self.value = ins.readString16(readId)
            elif Type == 3:
                # Int32
                self.value, = insUnpack('=i',4,readId)
            elif Type == 4:
                # Float
                self.value, = insUnpack('=f',4,readId)
            elif Type == 5:
                # Bool (Int8)
                self.value = bool(insUnpack('=b',1,readId)[0])
            elif Type == 11:
                # List of Objects
                count, = insUnpack('=I',4,readId)
                if objFormat == 1: # (fid,aid,nul)
                    value = insUnpack('='+count*'IHH',count*8,readId)
                    self.value = zip(value[::3],value[1::3]) # list of (fid,aid)'s
                else: # (nul,aid,fid)
                    value = insUnpack('='+count*'HHI',count*8,readId)
                    self.value = zip(value[2::3],value[1::3]) # list of (fid,aid)'s
            elif Type == 12:
                # List of Strings
                count, = insUnpack('=I',4,readId)
                self.value = [ins.readString16(readId) for i in xrange(count)]
            elif Type == 13:
                # List of Int32s
                count, = insUnpack('=I',4,readId)
                self.value = list(insUnpack('='+`count`+'i',count*4,readId))
            elif Type == 14:
                # List of Floats
                count, = insUnpack('=I',4,readId)
                self.value = list(insUnpack('='+`count`+'f',count*4,readId))
            elif Type == 15:
                # List of Bools (int8)
                count, = insUnpack('=I',4,readId)
                self.value = map(bool,insUnpack('='+`count`+'b',count,readId))
            else:
                raise Exception(u'Unrecognized VM Data property type: %i' % Type)

        def dumpData(self):
            ## Property Entry
            # Property Name
            name = encode(self.name)
            data = struct_pack('=H', len(name)) + name
            # Property Type
            value = self.value
            # Type 1 - Object Reference
            if isinstance(value,tuple):
                # Object Format 1 - (Fid, Aid, NULL)
                #data += structPack('=BBIHH',1,self.status,value[0],value[1],0)
                # Object Format 2 - (NULL, Aid, Fid)
                data += struct_pack('=BBHHI', 1, self.status, 0, value[1],
                                    value[0])
            # Type 2 - String
            elif isinstance(value,basestring):
                value = encode(value)
                data += struct_pack('=BBH', 2, self.status, len(value)) + value
            # Type 3 - Int
            elif isinstance(value,(int,long)) and not isinstance(value,bool):
                data += struct_pack('=BBi', 3, self.status, value)
            # Type 4 - Float
            elif isinstance(value,float):
                data += struct_pack('=BBf', 4, self.status, value)
            # Type 5 - Bool
            elif isinstance(value,bool):
                data += struct_pack('=BBb', 5, self.status, value)
            # Type 11 -> 15 - lists, Only supported if vmad version >= 5
            elif isinstance(value,list):
                # Empty list, fail to object refereneces?
                count = len(value)
                if not count:
                    data += struct_pack('=BBI', 11, self.status, count)
                else:
                    Type = value[0]
                    # Type 11 - Object References
                    if isinstance(Type,tuple):
                        # Object Format 1 - value = [fid,aid,NULL, fid,aid,NULL, ...]
                        #value = list(from_iterable([x+(0,) for x in value]))
                        #data += structPack('=BBI'+count*'IHH',11,self.status,count,*value)
                        # Object Format 2 - value = [NULL,aid,fid, NULL,aid,fid, ...]
                        value = list(from_iterable([(0,aid,fid) for fid,aid in value]))
                        data += struct_pack('=BBI' + count * 'HHI', 11,
                                            self.status, count, *value)
                    # Type 12 - Strings
                    elif isinstance(Type,basestring):
                        data += struct_pack('=BBI', 12, self.status, count)
                        for string in value:
                            string = encode(string)
                            data += struct_pack('=H', len(string)) + string
                    # Type 13 - Ints
                    elif isinstance(Type,(int,long)) and not isinstance(
                            Type,bool):
                        data += struct_pack('=BBI' + `count` + 'i', 13,
                                            self.status, count, *value)
                    # Type 14 - Floats
                    elif isinstance(Type,float):
                        data += struct_pack('=BBI' + `count` + 'f', 14,
                                            self.status, count, *value)
                    # Type 15 - Bools
                    elif isinstance(Type,bool):
                        data += struct_pack('=BBI' + `count` + 'b', 15,
                                            self.status, count, *value)
                    else:
                        raise Exception(u'Unrecognized VMAD property type: %s' % type(Type))
            else:
                raise Exception(u'Unrecognized VMAD property type: %s' % type(value))
            return data

    class Script(object):
        __slots__ = ('name','status','properties',)
        def __init__(self):
            self.name = u''
            self.status = 0
            self.properties = []

        def loadData(self,ins,version,objFormat,readId):
            Property = MelVmad.Property
            self.properties = []
            propAppend = self.properties.append
            # Script Entry
            self.name = ins.readString16(readId)
            if version >= 4:
                self.status,propCount = ins.unpack('=BH',3,readId)
            else:
                self.status = 0
                propCount, = ins.unpack('=H',2,readId)
            # Properties
            for x in xrange(propCount):
                prop = Property()
                prop.loadData(ins,version,objFormat,readId)
                propAppend(prop)

        def dumpData(self):
            ## Script Entry
            # scriptName
            name = encode(self.name)
            data = struct_pack('=H', len(name)) + name
            # status, property count
            data += struct_pack('=BH', self.status, len(self.properties))
            # properties
            for prop in self.properties:
                data += prop.dumpData()
            return data

        def mapFids(self,record,function,save=False):
            for prop in self.properties:
                value = prop.value
                # Type 1 - Object Reference: (fid,aid)
                if isinstance(value,tuple):
                    value = (function(value[0]),value[1])
                    if save:
                        prop.value = value
                # Type 11 - List of Object References: [(fid,aid), (fid,aid), ...]
                elif isinstance(value,list) and value and isinstance(value[0],tuple):
                    value = [(function(x[0]),x[1]) for x in value]
                    if save:
                        prop.value = value

    class Alias(object):
        __slots__ = ('fid','aid','scripts',)
        def __init__(self):
            self.fid = None
            self.aid = 0
            self.scripts = []

        def loadData(self,ins,version,objFormat,readId):
            insUnpack = ins.unpack
            if objFormat == 1:
                self.fid,self.aid,nul = insUnpack('=IHH',8,readId)
            else:
                nul,self.aid,self.fid = insUnpack('=HHI',8,readId)
            # _version - always the same as the primary script's version.
            # _objFormat - always the same as the primary script's objFormat.
            _version,_objFormat,count = insUnpack('=hhH',6,readId)
            Script = MelVmad.Script
            self.scripts = []
            scriptAppend = self.scripts.append
            for x in xrange(count):
                script = Script()
                script.loadData(ins,version,objFormat,readId)
                scriptAppend(script)

        def dumpData(self):
            # Object Format 2 - (NULL, Aid, Fid)
            data = struct_pack('=HHI', 0, self.aid, self.fid)
            # vmad version, object format, script count
            data += struct_pack('=3H', 5, 2, len(self.scripts))
            # Primary Scripts
            for script in self.scripts:
                data += script.dumpData()
            return data

        def mapFids(self,record,function,save=False):
            if self.fid:
                fid = function(self.fid)
                if save: self.fid = fid
            for script in self.scripts:
                script.mapFids(record,function,save)

    class Vmad(object):
        __slots__ = ('scripts','fragmentInfo','fragments','aliases',)
        def __init__(self):
            self.scripts = []
            self.fragmentInfo = None
            self.fragments = None
            self.aliases = None

        def loadData(self, record, ins, size_, readId):
            insTell = ins.tell
            endOfField = insTell() + size_
            self.scripts = []
            scriptsAppend = self.scripts.append
            Script = MelVmad.Script
            # VMAD Header
            version,objFormat,scriptCount = ins.unpack('=3H',6,readId)
            # Primary Scripts
            for x in xrange(scriptCount):
                script = Script()
                script.loadData(ins,version,objFormat,readId)
                scriptsAppend(script)
            # Script Fragments
            if insTell() < endOfField:
                self.fragmentInfo = MelVmad.FragmentInfo()
                Type = record.recType
                fragCount = self.fragmentInfo.loadData(ins,Type,readId)
                self.fragments = []
                fragAppend = self.fragments.append
                Fragment = MelVmad.FragmentMap[Type]
                for x in xrange(fragCount):
                    frag = Fragment()
                    frag.loadData(ins,readId)
                    fragAppend(frag)
                # Alias Scripts
                if Type == 'QUST':
                    aliasCount, = ins.unpack('=H',2,readId)
                    Alias = MelVmad.Alias
                    self.aliases = []
                    aliasAppend = self.aliases.append
                    for x in xrange(aliasCount):
                        alias = Alias()
                        alias.loadData(ins,version,objFormat,readId)
                        aliasAppend(alias)
                else:
                    self.aliases = None
            else:
                self.fragmentInfo = None
                self.fragments = None
                self.aliases = None

        def dumpData(self,record):
            # Header
            #data = structPack('=3H',4,1,len(self.scripts)) # vmad version, object format, script count
            data = struct_pack('=3H', 5, 2, len(self.scripts)) # vmad version, object format, script count
            # Primary Scripts
            for script in self.scripts:
                data += script.dumpData()
            # Script Fragments
            if self.fragments:
                Type = record.recType
                data += self.fragmentInfo.dumpData(Type,len(self.fragments))
                for frag in self.fragments:
                    data += frag.dumpData()
                if Type == 'QUST':
                    # Alias Scripts
                    aliases = self.aliases
                    data += struct_pack('=H', len(aliases))
                    for alias in aliases:
                        data += alias.dumpData()
            return data

        def mapFids(self,record,function,save=False):
            for script in self.scripts:
                script.mapFids(record,function,save)
            if not self.aliases:
                return
            for alias in self.aliases:
                alias.mapFids(record,function,save)

    def __init__(self, subType='VMAD', attr='vmdata'):
        MelBase.__init__(self, subType, attr)

    def hasFids(self,formElements):
        """Include self if has fids."""
        formElements.add(self)

    def setDefault(self,record):
        record.__setattr__(self.attr,None)

    def getDefault(self):
        target = MelObject()
        return self.setDefault(target)

    def loadData(self, record, ins, sub_type, size_, readId):
        vmad = MelVmad.Vmad()
        vmad.loadData(record, ins, size_, readId)
        record.__setattr__(self.attr,vmad)

    def dumpData(self,record,out):
        """Dumps data from record to outstream"""
        vmad = record.__getattribute__(self.attr)
        if vmad is None: return
        # Write
        out.packSub(self.subType,vmad.dumpData(record))

    def mapFids(self,record,function,save=False):
        """Applies function to fids.  If save is true, then fid is set
           to result of function."""
        vmad = record.__getattribute__(self.attr)
        if vmad is None: return
        vmad.mapFids(record,function,save)

#------------------------------------------------------------------------------
# Skyrim Records --------------------------------------------------------------
#------------------------------------------------------------------------------
class MreHeader(MreHeaderBase):
    """TES4 Record.  File header."""
    classType = 'TES4'

    #--Data elements
    melSet = MelSet(
        MelStruct('HEDR','f2I',('version',1.7),'numRecords',('nextObject',0xCE6)),
        MelUnicode('CNAM','author',u'',512),
        MelUnicode('SNAM','description',u'',512),
        MreHeaderBase.MelMasterName('MAST','masters'),
        MelNull('DATA'), # 8 Bytes in Length
        MelFidList('ONAM','overrides',),
        MelBase('SCRN', 'scrn_p'),
        MelBase('INTV','intv_p'),
        MelBase('INCC', 'incc_p'),
        )
    __slots__ = melSet.getSlotsUsed()

# MAST and DATA need to be grouped together like MAST DATA MAST DATA, are they that way already?
#------------------------------------------------------------------------------
class MreAact(MelRecord):
    """Action record."""
    classType = 'AACT'
    melSet = MelSet(
        MelString('EDID','eid'),
        MelColorN(),
        )
    __slots__ = melSet.getSlotsUsed()

# Verified for 305
#------------------------------------------------------------------------------
class MreAchr(MelRecord):
    """Placed NPC"""
    classType = 'ACHR'
    _flags = Flags(0L,Flags.getNames('oppositeParent','popIn'))

    # 'Parent Activate Only'
    ActivateParentsFlags = Flags(0L,Flags.getNames(
            (0, 'parentActivateOnly'),
        ))

    # XLCM Level Modifiers wbEnum in TES5Edit
    # 'Easy',
    # 'Medium',
    # 'Hard',
    # 'Very Hard'

    # PDTO Topic Data wbEnum in TES5Edit
    # 'Topic Ref',
    # 'Topic Subtype'

    # class MelACHRPDTOHandeler
    # if 'type' in PDTO is equal to 1 then 'data' is '4s' not FID

    melSet = MelSet(
        MelString('EDID','eid'),
        MelVmad(),
        MelFid('NAME','base'),
        MelFid('XEZN','encounterZone'),

        # {--- Ragdoll ---}

        MelBase('XRGD','ragdollData'),
        MelBase('XRGB','ragdollBipedData'),

        # {--- Patrol Data ---}

        MelGroup('patrolData',
            MelStruct('XPRD','f','idleTime',),
            MelNull('XPPA'),
            MelFid('INAM','idle'),
            MelGroup('patrolData',
                MelBase('SCHR','schr_p'),
                MelBase('SCDA','scda_p'),
                MelBase('SCTX','sctx_p'),
                MelBase('QNAM','qnam_p'),
                MelBase('SCRO','scro_p'),
            ),
            # Should Be -> MelACHRPDTOHandeler(),
            MelStructs('PDTO','2I','topicData','type',(FID,'data'),),
            MelFid('TNAM','topic'),
        ),

        # {--- Leveled Actor ----}
        MelStruct('XLCM','i','levelModifier'),

        # {--- Merchant Container ----}
        MelFid('XMRC','merchantContainer',),

        # {--- Extra ---}
        MelStruct('XCNT','i','count'),
        MelStruct('XRDS','f','radius',),
        MelStruct('XHLP','f','health',),
        MelGroup('linkedReferences',
            MelSortedFidList('XLKR', 'fids'),
        ),

        # {--- Activate Parents ---}
        MelGroup('activateParents',
            MelStruct('XAPD','I',(ActivateParentsFlags,'flags',0L),),
            MelGroups('activateParentRefs',
                MelStruct('XAPR','If',(FID,'reference'),'delay',),
            ),
        ),

        # {--- Linked Ref ---}
        MelStruct('XCLP','3Bs3Bs','startColorRed','startColorGreen','startColorBlue',
                  'startColorUnknown','endColorRed','endColorGreen','endColorBlue',
                  'endColorUnknown',),
        MelFid('XLCN','persistentLocation',),
        MelFid('XLRL','locationReference',),
        MelNull('XIS2'),
        MelFidList('XLRT','locationRefType',),
        MelFid('XHOR','horse',),
        MelStruct('XHTW','f','headTrackingWeight',),
        MelStruct('XFVC','f','favorCost',),

        # {--- Enable Parent ---}
        MelOptStruct('XESP','IB3s',(FID,'parent'),(_flags,'parentFlags'),'unused',),

        # {--- Ownership ---}
        MelOwnership(),

        # {--- Emittance ---}
        MelOptStruct('XEMI','I',(FID,'emittance')),

        # {--- MultiBound ---}
        MelFid('XMBR','multiBoundReference',),

        # {--- Flags ---}
        MelNull('XIBS'),

        # {--- 3D Data ---}
        MelOptStruct('XSCL','f',('scale',1.0)),
        MelOptStruct('DATA','=6f',('posX',None),('posY',None),('posZ',None),('rotX',None),('rotY',None),('rotZ',None)),
        )
    __slots__ = melSet.getSlotsUsed()

# Verified for 305
#------------------------------------------------------------------------------
class MreActi(MelRecord):
    """Activator."""
    classType = 'ACTI'

    ActivatorFlags = Flags(0L,Flags.getNames(
        (0, 'noDisplacement'),
        (1, 'ignoredBySandbox'),
    ))

    melSet = MelSet(
        MelString('EDID','eid'),
        MelVmad(),
        MelBounds(),
        MelLString('FULL','full'),
        MelModel(),
        MelDestructible(),
        MelKeywords(),
        MelStruct('PNAM','=4B','red','green','blue','unused'),
        MelOptStruct('SNAM','I',(FID,'dropSound')),
        MelOptStruct('VNAM','I',(FID,'pickupSound')),
        MelOptStruct('WNAM','I',(FID,'water')),
        MelLString('RNAM','rnam_p'),
        MelOptStruct('FNAM','H',(ActivatorFlags,'flags',0L),),
        MelOptStruct('KNAM','I',(FID,'keyword')),
        )
    __slots__ = melSet.getSlotsUsed()

# Verified for 305
#------------------------------------------------------------------------------
class MreAddn(MelRecord):
    """Addon"""
    classType = 'ADDN'
    melSet = MelSet(
        MelString('EDID','eid'),
        MelBounds(),
        MelModel(),
        MelBase('DATA','data_p'),
        MelOptStruct('SNAM','I',(FID,'ambientSound')),
        MelBase('DNAM','addnFlags'),
        )
    __slots__ = melSet.getSlotsUsed()

# Verified for 305
#------------------------------------------------------------------------------
class MreAlch(MelRecord,MreHasEffects):
    """Ingestible"""
    classType = 'ALCH'

    # {0x00000001} 'No Auto-Calc (Unused)',
    # {0x00000002} 'Food Item',
    # {0x00000004} 'Unknown 3',
    # {0x00000008} 'Unknown 4',
    # {0x00000010} 'Unknown 5',
    # {0x00000020} 'Unknown 6',
    # {0x00000040} 'Unknown 7',
    # {0x00000080} 'Unknown 8',
    # {0x00000100} 'Unknown 9',
    # {0x00000200} 'Unknown 10',
    # {0x00000400} 'Unknown 11',
    # {0x00000800} 'Unknown 12',
    # {0x00001000} 'Unknown 13',
    # {0x00002000} 'Unknown 14',
    # {0x00004000} 'Unknown 15',
    # {0x00008000} 'Unknown 16',
    # {0x00010000} 'Medicine',
    # {0x00020000} 'Poison'
    IngestibleFlags = Flags(0L,Flags.getNames(
        (0, 'autoCalc'),
        (1, 'isFood'),
        (16, 'medicine'),
        (17, 'poison'),
    ))

    melSet = MelSet(
        MelString('EDID','eid'),
        MelBounds(),
        MelLString('FULL','full'),
        MelKeywords(),
        MelLString('DESC','description'),
        MelModel(),
        MelDestructible(),
        MelString('ICON','iconPath'),
        MelString('MICO','smallIconPath'),
        MelOptStruct('YNAM','I',(FID,'pickupSound')),
        MelOptStruct('ZNAM','I',(FID,'dropSound')),
        MelOptStruct('ETYP','I',(FID,'equipType')),
        MelStruct('DATA','f','weight'),
        MelStruct('ENIT','i2IfI','value',(IngestibleFlags,'flags',0L),
                  'addiction','addictionChance','soundConsume',),
        MelEffects(),
        )
    __slots__ = melSet.getSlotsUsed()

# Verified for 305
#------------------------------------------------------------------------------
class MreAmmo(MelRecord):
    """Ammo record (arrows)"""
    classType = 'AMMO'

    AmmoTypeFlags = Flags(0L,Flags.getNames(
        (0, 'notNormalWeapon'),
        (1, 'nonPlayable'),
        (2, 'nonBolt'),
    ))

    melSet = MelSet(
        MelString('EDID','eid'),
        MelBounds(),
        MelLString('FULL','full'),
        MelModel(),
        MelString('ICON','iconPath'),
        MelString('MICO','smallIconPath'),
        MelDestructible(),
        MelFid('YNAM','pickupSound'),
        MelFid('ZNAM','dropSound'),
        MelLString('DESC','description'),
        MelKeywords(),
        MelStruct('DATA','IIfI',(FID,'projectile'),(AmmoTypeFlags,'flags',0L),'damage','value'),
        MelString('ONAM','onam_n'),
        )
    __slots__ = melSet.getSlotsUsed()

# Verified for 305
#------------------------------------------------------------------------------
class MreAnio(MelRecord):
    """Anio record (Animated Object)"""
    classType = 'ANIO'
    melSet = MelSet(
        MelString('EDID','eid'),
        MelModel(),
        MelString('BNAM','animationId'),
        )
    __slots__ = melSet.getSlotsUsed()

# Verified for 305
#------------------------------------------------------------------------------
class MreAppa(MelRecord):
    """Appa record (Alchemical Apparatus)"""
    classType = 'APPA'

    # QUAL has wbEnum in TES5Edit
    # Assigned to 'quality' for WB
    # 0 :'novice',
    # 1 :'apprentice',
    # 2 :'journeyman',
    # 3 :'expert',
    # 4 :'master',

    melSet = MelSet(
        MelString('EDID','eid'),
        MelVmad(),
        MelBounds(),
        MelLString('FULL','full'),
        MelModel(),
        MelString('ICON','iconPath'),
        MelString('MICO','smallIconPath'),
        MelDestructible(),
        MelFid('YNAM','pickupSound'),
        MelFid('ZNAM','dropSound'),
        MelStruct('QUAL','I','quality'),
        MelLString('DESC','description'),
        MelStruct('DATA','If','value','weight'),
        )
    __slots__ = melSet.getSlotsUsed()

# Verified for 305
#------------------------------------------------------------------------------
class MreArma(MelRecord):
    """Armor addon record."""
    classType = 'ARMA'

    # {0x01} 'Unknown 0',
    # {0x02} 'Enabled'
    WeightSliderFlags = Flags(0L,Flags.getNames(
            (0, 'unknown0'),
            (1, 'enabled'),
        ))

    melSet = MelSet(
        MelString('EDID','eid'),
        MelBipedObjectData(),
        MelFid('RNAM','race'),
        MelStruct('DNAM','4B2sBsf','malePriority','femalePriority',
                  (WeightSliderFlags,'maleFlags',0L),
                  (WeightSliderFlags,'femaleFlags',0L),
                  'unknown','detectionSoundValue','unknown1','weaponAdjust',),
        MelModel('male_model','MOD2'),
        MelModel('female_model','MOD3'),
        MelModel('male_model_1st','MOD4'),
        MelModel('female_model_1st','MOD5'),
        MelOptStruct('NAM0','I',(FID,'skin0')),
        MelOptStruct('NAM1','I',(FID,'skin1')),
        MelOptStruct('NAM2','I',(FID,'skin2')),
        MelOptStruct('NAM3','I',(FID,'skin3')),
        MelFids('MODL','races'),
        MelOptStruct('SNDD','I',(FID,'footstepSound')),
        MelOptStruct('ONAM','I',(FID,'art_object')),
        )
    __slots__ = melSet.getSlotsUsed()

# Verified for 305
#------------------------------------------------------------------------------
class MreArmo(MelRecord):
    """Armor"""
    classType = 'ARMO'

    melSet = MelSet(
        MelString('EDID','eid'),
        MelVmad(),
        MelBounds(),
        MelLString('FULL','full'),
        MelOptStruct('EITM','I',(FID,'enchantment')),
        MelOptStruct('EAMT','H','enchantmentAmount',),
        MelModel('model2','MOD2'),
        MelString('ICON','maleIconPath'),
        MelString('MICO','maleSmallIconPath'),
        MelModel('model4','MOD4'),
        MelString('ICO2','femaleIconPath'),
        MelString('MIC2','femaleSmallIconPath'),
        MelBipedObjectData(),
        MelDestructible(),
        MelOptStruct('YNAM','I',(FID,'pickupSound')),
        MelOptStruct('ZNAM','I',(FID,'dropSound')),
        MelString('BMCT','ragdollTemplatePath'), #Ragdoll Constraint Template
        MelOptStruct('ETYP','I',(FID,'equipType')),
        MelOptStruct('BIDS','I',(FID,'bashImpact')),
        MelOptStruct('BAMT','I',(FID,'material')),
        MelOptStruct('RNAM','I',(FID,'race')),
        MelKeywords(),
        MelLString('DESC','description'),
        MelFids('MODL','addons'),
        MelStruct('DATA','=if','value','weight'),
        MelStruct('DNAM','i','armorRating'),
        MelFid('TNAM','templateArmor'),
        )
    __slots__ = melSet.getSlotsUsed()

# Verified for 305
#------------------------------------------------------------------------------
class MreArto(MelRecord):
    """Arto record (Art effect object)"""
    classType = 'ARTO'

    #{0x00000001} 'Magic Casting',
    #{0x00000002} 'Magic Hit Effect',
    #{0x00000004} 'Enchantment Effect'
    ArtoTypeFlags = Flags(0L,Flags.getNames(
            (0, 'magic_casting'),
            (1, 'magic_hit_effect'),
            (2, 'enchantment_effect'),
        ))

    melSet = MelSet(
        MelString('EDID','eid'),
        MelBounds(),
        MelModel(),
        MelStruct('DNAM','I',(ArtoTypeFlags,'flags',0L)),
        )
    __slots__ = melSet.getSlotsUsed()

# Verified for 305
#------------------------------------------------------------------------------
class MreAspc(MelRecord):
    """Aspc record (Acoustic Space)"""
    classType = 'ASPC'
    melSet = MelSet(
        MelString('EDID','eid'),
        MelBounds(),
        MelOptStruct('SNAM','I',(FID,'ambientSound')),
        MelOptStruct('RDAT','I',(FID,'regionData')),
        MelOptStruct('BNAM','I',(FID,'reverb')),
        )
    __slots__ = melSet.getSlotsUsed()

# Verified for 305
#------------------------------------------------------------------------------
class MreAstp(MelRecord):
    """Astp record (Association type)"""
    classType = 'ASTP'

    # DATA Flags
    # {0x00000001} 'Related'
    AstpTypeFlags = Flags(0L,Flags.getNames('related'))

    melSet = MelSet(
        MelString('EDID','eid'),
        MelString('MPRT','maleParent'),
        MelString('FPRT','femaleParent'),
        MelString('MCHT','maleChild'),
        MelString('FCHT','femaleChild'),
        MelStruct('DATA','I',(AstpTypeFlags,'flags',0L)),
        )
    __slots__ = melSet.getSlotsUsed()

# Verified for 305
#------------------------------------------------------------------------------
class MreAvif(MelRecord):
    """ActorValue Information record."""
    classType = 'AVIF'

    #--CNAM loader
    class MelCnamLoaders(DataDict):
        """Since CNAM subrecords occur in two different places, we need
        to replace ordinary 'loaders' dictionary with a 'dictionary' that will
        return the correct element to handle the CNAM subrecord. 'Correct'
        element is determined by which other subrecords have been encountered."""
        def __init__(self,loaders,actorinfo,perks):
            self.data = loaders
            self.type_cnam = {'EDID':actorinfo, 'PNAM':perks}
            self.cnam = actorinfo #--Which cnam element loader to use next.
        def __getitem__(self,key):
            if key == 'CNAM': return self.cnam
            self.cnam = self.type_cnam.get(key, self.cnam)
            return self.data[key]

    melSet = MelSet(
        MelString('EDID','eid'),
        MelLString('FULL','full'),
        MelLString('DESC','description'),
        MelString('ANAM','abbreviation'),
        MelBase('CNAM','cnam_p'),
        MelOptStruct('AVSK','4f','skillUseMult','skillOffsetMult','skillImproveMult',
                     'skillImproveOffset',),
        MelGroups('perkTree',
            MelFid('PNAM', 'perk',),
            MelBase('FNAM','fnam_p'),
            MelStruct('XNAM','I','perkGridX'),
            MelStruct('YNAM','I','perkGridY'),
            MelStruct('HNAM','f','horizontalPosition'),
            MelStruct('VNAM','f','verticalPosition'),
            MelFid('SNAM','associatedSkill',),
            MelStructs('CNAM','I','connections','lineToIndex',),
            MelStruct('INAM','I','index',),
        ),
    )
    melSet.loaders = MelCnamLoaders(melSet.loaders,melSet.elements[4],melSet.elements[6])
    __slots__ = melSet.getSlotsUsed()

# Verified for 305
#------------------------------------------------------------------------------
class MelBookData(MelStruct):
    """Determines if the book teaches the player a Skill or Spell.
    skillOrSpell is FID when flag teachesSpell is set."""
    # {0x01} 'Teaches Skill',
    # {0x02} 'Can''t be Taken',
    # {0x04} 'Teaches Spell',
    bookTypeFlags = Flags(0L,Flags.getNames(
        (0, 'teachesSkill'),
        (1, 'cantBeTaken'),
        (2, 'teachesSpell'),
    ))

    # DATA Book Type is wbEnum in TES5Edit
    # Assigned to 'bookType' for WB
    # 0, 'Book/Tome',
    # 255, 'Note/Scroll'

    # DATA has wbSkillEnum in TES5Edit
    # Assigned to 'skillOrSpell' for WB
    # -1 :'None',
    #  7 :'One Handed',
    #  8 :'Two Handed',
    #  9 :'Archery',
    #  10:'Block',
    #  11:'Smithing',
    #  12:'Heavy Armor',
    #  13:'Light Armor',
    #  14:'Pickpocket',
    #  15:'Lockpicking',
    #  16:'Sneak',
    #  17:'Alchemy',
    #  18:'Speech',
    #  19:'Alteration',
    #  20:'Conjuration',
    #  21:'Destruction',
    #  22:'Illusion',
    #  23:'Restoration',
    #  24:'Enchanting',

    def __init__(self, subType='DATA'):
        """Initialize."""
        MelStruct.__init__(self, subType, '2B2siIf', (MelBookData.bookTypeFlags, 'flags', 0L),
                           ('bookType',0), ('unused',null2), ('skillOrSpell',0),'value','weight'),

    def hasFids(self,formElements):
        """Include self if has fids."""
        formElements.add(self)

    def mapFids(self,record,function,save=False):
        if record.flags.teachesSpell:
            result = function(record.skillOrSpell)
            if save: record.skillOrSpell = result

class MreBook(MelRecord):
    """Book Item"""
    classType = 'BOOK'
    melSet = MelSet(
        MelString('EDID','eid'),
        MelVmad(),
        MelBounds(),
        MelLString('FULL','full'),
        MelModel(),
        MelString('ICON','iconPath'),
        MelString('MICO','smallIconPath'),
        MelLString('DESC','description'),
        MelDestructible(),
        MelOptStruct('YNAM','I',(FID,'pickupSound')),
        MelOptStruct('ZNAM','I',(FID,'dropSound')),
        MelKeywords(),
        MelBookData(),
        MelFid('INAM','inventoryArt'),
        MelLString('CNAM','text'),
        )
    __slots__ = melSet.getSlotsUsed() + ['modb']

# Verified for 305
#------------------------------------------------------------------------------
class MreBptd(MelRecord):
    """Body part data record."""
    classType = 'BPTD'

    # BPND has two wbEnum in TES5Edit
    # for 'actorValue' refer to wbActorValueEnum
    # 'bodyPartType' is defined as follows
    # 0 :'Torso',
    # 1 :'Head',
    # 2 :'Eye',
    # 3 :'LookAt',
    # 4 :'Fly Grab',
    # 5 :'Saddle'

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
                elif sub_type == 'BPNN': # for NVVoidBodyPartData, NVraven02
                    target = self.getDefault()
                    record.__getattribute__(self.attr).append(target)
            target.__slots__ = [s for element in self.elements for s in
                                element.getSlotsUsed()]
            self.loaders[sub_type].loadData(target, ins, sub_type, size_,
                                            readId)
    melSet = MelSet(
        MelString('EDID','eid'),
        MelModel(),
        MelBptdGroups('bodyParts',
            MelString('BPTN','partName'),
            MelString('PNAM','poseMatching'),
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
            # Ignore texture hashes - they're only an optimization, plenty of
            # records in Skyrim.esm are missing them
            MelNull('NAM5'),
            ),
        )
    __slots__ = melSet.getSlotsUsed()

# Verified for 305
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
    # 'Location-Lead Actor'

    # 'Target-Attacker',
    # 'Target-Projectile',
    # 'Target-Target',
    # 'Target-Lead Actor'

    CamsFlagsFlags = Flags(0L,Flags.getNames(
            (0, 'positionFollowsLocation'),
            (1, 'rotationFollowsTarget'),
            (2, 'dontFollowBone'),
            (3, 'firstPersonCamera'),
            (4, 'noTracer'),
            (5, 'startAtTimeZero'),
        ))

    class MelCamsData(MelStruct):
        """Handle older truncated DATA for CAMS subrecord."""
        def loadData(self, record, ins, sub_type, size_, readId):
            if size_ == 44:
                MelStruct.loadData(self, record, ins, sub_type, size_, readId)
                return
            elif size_ == 40:
                unpacked = ins.unpack('4I6f', size_, readId)
            else:
                raise ModSizeError(record.inName, readId, 44, size_, True)
            unpacked += self.defaults[len(unpacked):]
            setter = record.__setattr__
            for attr,value,action in zip(self.attrs,unpacked,self.actions):
                if callable(action): value = action(value)
                setter(attr,value)
            if self._debug: print unpacked

    melSet = MelSet(
        MelString('EDID','eid'),
        MelModel(),
        MelCamsData('DATA','4I7f','action','location','target',
                  (CamsFlagsFlags,'flags',0L),'timeMultPlayer',
                  'timeMultTarget','timeMultGlobal','maxTime','minTime',
                  'targetPctBetweenActors','nearTargetDistance',),
        MelFid('MNAM','imageSpaceModifier',),
        )
    __slots__ = melSet.getSlotsUsed()

# Verified for 305
#------------------------------------------------------------------------------
class MreCell(MelRecord):
    """Cell"""
    classType = 'CELL'

    # {0x0001} 'Is Interior Cell',
    # {0x0002} 'Has Water',
    # {0x0004} 'Can''t Travel From Here',
    # {0x0008} 'No LOD Water',
    # {0x0010} 'Unknown 5',
    # {0x0020} 'Public Area',
    # {0x0040} 'Hand Changed',
    # {0x0080} 'Show Sky',
    # {0x0100} 'Use Sky Lighting'
    CellDataFlags1 = Flags(0L,Flags.getNames(
        (0,'isInterior'), # isInteriorCell
        (1,'hasWater'),
        (2,'cantFastTravel'),
        (3,'noLODWater'),
        (5,'publicPlace'),
        (6,'handChanged'),
        # showSky
        (7,'showSky'),
        ))

    CellDataFlags2 = Flags(0L,Flags.getNames(
        # useSkyLighting
        (0,'useSkyLighting'),
        ))

    # {0x00000001}'Ambient Color',
    # {0x00000002}'Directional Color',
    # {0x00000004}'Fog Color',
    # {0x00000008}'Fog Near',
    # {0x00000010}'Fog Far',
    # {0x00000020}'Directional Rotation',
    # {0x00000040}'Directional Fade',
    # {0x00000080}'Clip Distance',
    # {0x00000100}'Fog Power',
    # {0x00000200}'Fog Max',
    # {0x00000400}'Light Fade Distances'
    CellInheritedFlags = Flags(0L,Flags.getNames(
            (0, 'ambientColor'),
            (1, 'directionalColor'),
            (2, 'fogColor'),
            (3, 'fogNear'),
            (4, 'fogFar'),
            (5, 'directionalRotation'),
            (6, 'directionalFade'),
            (7, 'clipDistance'),
            (8, 'fogPower'),
            (9, 'fogMax'),
            (10, 'lightFadeDistances'),
        ))

    # 'Force Hide Land' flags
    CellFHLFlags = Flags(0L,Flags.getNames(
            (0, 'quad1'),
            (1, 'quad2'),
            (2, 'quad3'),
            (3, 'quad4'),
        ))

    class MelCellXcll(MelOptStruct):
        """Handle older truncated XCLL for CELL subrecord."""
        def loadData(self, record, ins, sub_type, size_, readId):
            if size_ == 92:
                MelStruct.loadData(self, record, ins, sub_type, size_, readId)
                return
            elif size_ == 64:
                unpacked = ins.unpack('BBBsBBBsBBBsffiifffBBBsBBBsBBBsBBBsBBBsBBBs', size_, readId)
            elif size_ == 24:
                unpacked = ins.unpack('BBBsBBBsBBBsffi', size_, readId)
            else:
                raise ModSizeError(record.inName, readId, 92, size_, True)
            unpacked += self.defaults[len(unpacked):]
            setter = record.__setattr__
            for attr,value,action in zip(self.attrs,unpacked,self.actions):
                if callable(action): value = action(value)
                setter(attr,value)
            if self._debug: print unpacked, record.flags.getTrueAttrs()

    class MelCellData(MelStruct):
        """Handle older truncated DATA for CELL subrecord."""
        def loadData(self, record, ins, sub_type, size_, readId):
            if size_ == 2:
                MelStruct.loadData(self, record, ins, sub_type, size_, readId)
                return
            elif size_ == 1:
                unpacked = ins.unpack('B', size_, readId)
            else:
                raise ModSizeError(record.inName, readId, 2, size_, True)
            unpacked += self.defaults[len(unpacked):]
            setter = record.__setattr__
            for attr,value,action in zip(self.attrs,unpacked,self.actions):
                if callable(action): value = action(value)
                setter(attr,value)
            if self._debug: print unpacked, record.flags.getTrueAttrs()

    class MelWaterHeight(MelOptStruct):
        default_heights = {4294953216.0, -2147483648.0,
            -3.4028234663852886e+38, 3.4028234663852886e+38} # unused, see #302

        def loadData(self, record, ins, sub_type, size_, readId):
            # from brec.MelStruct#loadData - formatLen is 0 for MelWaterHeight
            waterHeight = ins.unpack(self.format, size_, readId)
            # print u' ', zip(self.attrs, waterHeight)
            # if len(waterHeight) != len(self.attrs):
            #     print u' ', waterHeight
            if not record.flags.isInterior: # drop interior cells for Skyrim
                attr,value = self.attrs[0],waterHeight[0]
                # if value in __default_heights:
                #     value = 3.4028234663852886e+38 # normalize values
                record.__setattr__(attr, value)
                # print u'SET %s' % record.__getattribute__(attr)

        def dumpData(self,record,out):
            if not record.flags.isInterior:
                MelOptStruct.dumpData(self,record,out)

# Flags can be itU8, but CELL\DATA has a critical role in various wbImplementation.pas routines
# and replacing it with wbUnion generates error when setting for example persistent flag in REFR.
# So let it be always itU16
    melSet = MelSet(
        MelString('EDID','eid'),
        MelLString('FULL','full'),
        MelCellData('DATA','BB',(CellDataFlags1,'flags',0L),(CellDataFlags2,'skyFlags',0L),),
        MelOptStruct('XCLC','2iI',('posX', 0),('posY', 0),(CellFHLFlags,'fhlFlags',0L),),
        MelCellXcll('XCLL','BBBsBBBsBBBsffiifffBBBsBBBsBBBsBBBsBBBsBBBsBBBsfBBBsfffI',
                 'ambientRed','ambientGreen','ambientBlue',('unused1',null1),
                 'directionalRed','directionalGreen','directionalBlue',('unused2',null1),
                 'fogRed','fogGreen','fogBlue',('unused3',null1),
                 'fogNear','fogFar','directionalXY','directionalZ',
                 'directionalFade','fogClip','fogPower',
                 'redXplus','greenXplus','blueXplus',('unknownXplus',null1), # 'X+'
                 'redXminus','greenXminus','blueXminus',('unknownXminus',null1), # 'X-'
                 'redYplus','greenYplus','blueYplus',('unknownYplus',null1), # 'Y+'
                 'redYminus','greenYminus','blueYminus',('unknownYminus',null1), # 'Y-'
                 'redZplus','greenZplus','blueZplus',('unknownZplus',null1), # 'Z+'
                 'redZminus','greenZminus','blueZminus',('unknownZminus',null1), # 'Z-'
                 'redSpec','greenSpec','blueSpec',('unknownSpec',null1), # Specular Color Values
                 'fresnelPower', # Fresnel Power
                 'fogColorFarRed','fogColorFarGreen','fogColorFarBlue',('unused4',null1),
                 'fogMax','lightFadeBegin','lightFadeEnd',(CellInheritedFlags,'inherits',0L),
             ),
        MelBase('TVDT','occlusionData'),
        # Decoded in xEdit, but properly reading it is relatively slow - see
        # 'Simple Records' option in xEdit - so we skip that for now
        MelBase('MHDT','maxHeightData'),
        MelFid('LTMP','lightTemplate',),
        # leftover flags, they are now in XCLC
        MelBase('LNAM','unknown_LNAM'),
        # XCLW sometimes has $FF7FFFFF and causes invalid floatation point
        MelWaterHeight('XCLW','f',('waterHeight',-2147483649)),
        MelString('XNAM','waterNoiseTexture'),
        MelFidList('XCLR','regions'),
        MelFid('XLCN','location',),
        MelBase('XWCN','unknown_XWCN'), # leftover
        MelBase('XWCS','unknown_XWCS'), # leftover
        MelOptStruct('XWCU', '3f4s3f', ('xOffset', 0.0), ('yOffset', 0.0),
                     ('zOffset', 0.0), ('unk1XWCU', null4), ('xAngle', 0.0),
                     ('yAngle', 0.0), ('zAngle', 0.0), dumpExtra='unk2XWCU',),
        MelFid('XCWT','water'),

        # {--- Ownership ---}
        MelOwnership(),
        MelFid('XILL','lockList',),
        MelString('XWEM','waterEnvironmentMap'),
        # skyWeatherFromRegion
        MelFid('XCCM','climate',),
        MelFid('XCAS','acousticSpace',),
        MelFid('XEZN','encounterZone',),
        MelFid('XCMO','music',),
        MelFid('XCIM','imageSpace',),
        )
    __slots__ = melSet.getSlotsUsed()

# Verified for 305
#------------------------------------------------------------------------------
class MreClas(MelRecord):
    """Clas record (Alchemical Apparatus)"""
    classType = 'CLAS'

    # DATA has wbEnum in TES5Edit
    # Assigned to 'teaches' for WB
    # 0 :'One Handed',
    # 1 :'Two Handed',
    # 2 :'Archery',
    # 3 :'Block',
    # 4 :'Smithing',
    # 5 :'Heavy Armor',
    # 6 :'Light Armor',
    # 7 :'Pickpocket',
    # 8 :'Lockpicking',
    # 9 :'Sneak',
    # 10 :'Alchemy',
    # 11 :'Speech',
    # 12 :'Alteration',
    # 13 :'Conjuration',
    # 14 :'Destruction',
    # 15 :'Illusion',
    # 16 :'Restoration',
    # 17 :'Enchanting'

    melSet = MelSet(
        MelString('EDID','eid'),
        MelLString('FULL','full'),
        MelLString('DESC','description'),
        MelString('ICON','iconPath'),
        MelString('MICO','smallIconPath'),
        MelStruct('DATA','4sb19BfI4B','unknown','teaches','maximumtraininglevel',
                  'skillWeightsOneHanded','skillWeightsTwoHanded',
                  'skillWeightsArchery','skillWeightsBlock',
                  'skillWeightsSmithing','skillWeightsHeavyArmor',
                  'skillWeightsLightArmor','skillWeightsPickpocket',
                  'skillWeightsLockpicking','skillWeightsSneak',
                  'skillWeightsAlchemy','skillWeightsSpeech',
                  'skillWeightsAlteration','skillWeightsConjuration',
                  'skillWeightsDestruction','skillWeightsIllusion',
                  'skillWeightsRestoration','skillWeightsEnchanting',
                  'bleedoutDefault','voicePoints',
                  'attributeWeightsHealth','attributeWeightsMagicka',
                  'attributeWeightsStamina','attributeWeightsUnknown',),
        )
    __slots__ = melSet.getSlotsUsed()

# Verified for 305
#------------------------------------------------------------------------------
class MreClfm(MelRecord):
    """Clfm Item"""
    classType = 'CLFM'
    melSet = MelSet(
        MelString('EDID','eid'),
        MelLString('FULL','full'),
        MelColorN(),
        # 'playable' is a Boolean value
        MelStruct('FNAM','I','playable'),
        )
    __slots__ = melSet.getSlotsUsed()

# Verified for 305
#------------------------------------------------------------------------------
class MreClmt(MelRecord):
    """Climate"""
    classType = 'CLMT'
    melSet = MelSet(
        MelString('EDID','eid',),
        MelStructA('WLST','IiI','weatherTypes',(FID,'weather',None),'chance',(FID,'global',None),),
        MelString('FNAM','sunPath',),
        MelString('GNAM','glarePath',),
        MelModel(),
        MelStruct('TNAM','6B','riseBegin','riseEnd','setBegin','setEnd','volatility','phaseLength',),
        )
    __slots__ = melSet.getSlotsUsed()

# Verified for 305
#------------------------------------------------------------------------------
class MreCobj(MelRecord):
    """Constructible Object record (recipies)"""
    classType = 'COBJ'
    isKeyedByEid = True # NULL fids are acceptible

    class MelCobjCnto(MelGroups):
        def __init__(self):
            MelGroups.__init__(self,'items',
                MelStruct('CNTO','=Ii',(FID,'item',None),'count'),
                MelCoed(),
                )

        def dumpData(self,record,out):
            # Only write the COCT/CNTO/COED subrecords if count > 0
            out.packSub('COCT','I',len(record.items))
            MelGroups.dumpData(self,record,out)

    melSet = MelSet(
        MelString('EDID','eid'),
        MelNull('COCT'), # Handled by MelCobjCnto
        MelCobjCnto(),
        MelConditions(),
        MelFid('CNAM','resultingItem'),
        MelFid('BNAM','craftingStation'),
        MelStruct('NAM1','H','resultingQuantity'),
        )
    __slots__ = melSet.getSlotsUsed()

# Verified for 305
#------------------------------------------------------------------------------
class MreColl(MelRecord):
    """Collision Layer"""
    classType = 'COLL'

    CollisionLayerFlags = Flags(0L,Flags.getNames(
        (0,'triggerVolume'),
        (1,'sensor'),
        (2,'navmeshObstacle'),
    ))

    melSet = MelSet(
        MelString('EDID','eid'),
        MelLString('DESC','description'),
        MelStruct('BNAM','I','layerID'),
        MelStruct('FNAM','=4B','red','green','blue','unused'),
        MelStruct('GNAM','I',(CollisionLayerFlags,'flags',0L),),
        MelString('MNAM','name',),
        MelStruct('INTV','I','interactablesCount'),
        MelFidList('CNAM','collidesWith',),
        )
    __slots__ = melSet.getSlotsUsed()

# Verified for 305
#------------------------------------------------------------------------------
class MreCont(MelRecord):
    """Container"""
    classType = 'CONT'

    class MelContCnto(MelGroups):
        def __init__(self):
            MelGroups.__init__(self,'items',
                MelStruct('CNTO','Ii',(FID,'item',None),'count'),
                MelCoed(),
                )

        def dumpData(self,record,out):
            # Only write the COCT/CNTO/COED subrecords if count > 0
            out.packSub('COCT','I',len(record.items))
            MelGroups.dumpData(self,record,out)


    # {0x01} 'Allow Sounds When Animation',
    # {0x02} 'Respawns',
    # {0x04} 'Show Owner'
    ContTypeFlags = Flags(0L,Flags.getNames(
        (0, 'allowSoundsWhenAnimation'),
        (1, 'respawns'),
        (2, 'showOwner'),
    ))

    melSet = MelSet(
        MelString('EDID','eid'),
        MelVmad(),
        MelBounds(),
        MelLString('FULL','full'),
        MelModel(),
        MelNull('COCT'),
        MelContCnto(),
        MelDestructible(),
        MelStruct('DATA','=Bf',(ContTypeFlags,'flags',0L),'weight'),
        MelFid('SNAM','soundOpen'),
        MelFid('QNAM','soundClose'),
        )
    __slots__ = melSet.getSlotsUsed()

# Verified for 305
#------------------------------------------------------------------------------
class MreCpth(MelRecord):
    """Camera Path"""
    classType = 'CPTH'

    # DATA 'Camera Zoom' isn wbEnum
    # 0, 'Default, Must Have Camera Shots',
    # 1, 'Disable, Must Have Camera Shots',
    # 2, 'Shot List, Must Have Camera Shots',
    # 128, 'Default',
    # 129, 'Disable',
    # 130, 'Shot List'

    melSet = MelSet(
        MelString('EDID','eid'),
        MelConditions(),
        MelFidList('ANAM','relatedCameraPaths',),
        MelStruct('DATA','B','cameraZoom',),
        MelFids('SNAM','cameraShots',),
        )
    __slots__ = melSet.getSlotsUsed()

# Verified for 305
#------------------------------------------------------------------------------
class MreCsty(MelRecord):
    """Csty Item"""
    classType = 'CSTY'

    # {0x01} 'Dueling',
    # {0x02} 'Flanking',
    # {0x04} 'Allow Dual Wielding'
    CstyTypeFlags = Flags(0L,Flags.getNames(
        (0, 'dueling'),
        (1, 'flanking'),
        (2, 'allowDualWielding'),
    ))

    melSet = MelSet(
        MelString('EDID','eid'),
        # esm = Equipment Score Mult
        MelStruct('CSGD','10f','offensiveMult','defensiveMult','groupOffensiveMult',
        'esmMelee','esmMagic','esmRanged','esmShout','esmUnarmed','esmStaff',
        'avoidThreatChance',),
        MelBase('CSMD','unknownValue'),
        MelStruct('CSME','8f','atkStaggeredMult','powerAtkStaggeredMult','powerAtkBlockingMult',
        'bashMult','bashRecoilMult','bashAttackMult','bashPowerAtkMult','specialAtkMult',),
        MelStruct('CSCR','4f','circleMult','fallbackMult','flankDistance','stalkTime',),
        MelStruct('CSLR','f','strafeMult'),
        MelStruct('CSFL','8f','hoverChance','diveBombChance','groundAttackChance','hoverTime',
        'groundAttackTime','perchAttackChance','perchAttackTime','flyingAttackChance',),
        MelStruct('DATA','I',(CstyTypeFlags,'flags',0L),),
        )
    __slots__ = melSet.getSlotsUsed()

# Verified for 305
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
            self.attrs,self.defaults,self.actions,self.formAttrs = MelBase.parseElements(*self._elements)
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

# Verified for 305
#------------------------------------------------------------------------------
class MreDial(brec.MreDial):
    """Dialogue Records"""

    # DATA has wbEnum in TES5Edit
    # Assigned to 'subtype' for WB
    # it has 102 different values, refer to
    # wbStruct(DATA, 'Data', in TES5Edit

    # DATA has wbEnum in TES5Edit
    # Assigned to 'category' for WB
    # {0} 'Topic',
    # {1} 'Favor', // only in DA14 quest topics
    # {2} 'Scene',
    # {3} 'Combat',
    # {4} 'Favors',
    # {5} 'Detection',
    # {6} 'Service',
    # {7} 'Miscellaneous'

    DialTopicFlags = Flags(0L,Flags.getNames(
        (0, 'doAllBeforeRepeating'),
    ))

    melSet = MelSet(
        MelString('EDID','eid'),
        MelLString('FULL','full'),
        MelStruct('PNAM','f','priority',),
        MelFid('BNAM','branch',),
        MelFid('QNAM','quest',),
        MelStruct('DATA','2BH',(DialTopicFlags,'flags_dt',0L),'category',
                  'subtype',),
        # SNAM is a 4 byte string no length byte
        MelStruct('SNAM','4s','subtypeName',),
        MelStruct('TIFC','I','infoCount',),
        )
    __slots__ = melSet.getSlotsUsed()

# Verified for 305
#------------------------------------------------------------------------------
class MreDlbr(MelRecord):
    """Dialog Branch"""
    classType = 'DLBR'

    DialogBranchFlags = Flags(0L,Flags.getNames(
        (0,'topLevel'),
        (1,'blocking'),
        (2,'exclusive'),
    ))

    melSet = MelSet(
        MelString('EDID','eid'),
        MelFid('QNAM','quest',),
        MelStruct('TNAM','I','unknown'),
        MelStruct('DNAM','I',(DialogBranchFlags,'flags',0L),),
        MelFid('SNAM','startingTopic',),
        )
    __slots__ = melSet.getSlotsUsed()

# Verified for 305
#------------------------------------------------------------------------------
class MreDlvw(MelRecord):
    """Dialog View"""
    classType = 'DLVW'

    melSet = MelSet(
        MelString('EDID','eid'),
        MelFid('QNAM','quest',),
        MelFids('BNAM','branches',),
        MelGroups('unknownTNAM',
            MelBase('TNAM','unknown',),
            ),
        MelBase('ENAM','unknownENAM'),
        MelBase('DNAM','unknownDNAM'),
        )
    __slots__ = melSet.getSlotsUsed()

# Verified for 305
#------------------------------------------------------------------------------
class MreDobj(MelRecord):
    """Default Object Manager"""
    classType = 'DOBJ'
    melSet = MelSet(
        MelString('EDID','eid'),
        MelGroups('objects',
            MelStruct('DNAM','2I','objectUse',(FID,'objectID',None),),
            ),
        )
    __slots__ = melSet.getSlotsUsed()

# Verified for 305
#------------------------------------------------------------------------------
class MreDoor(MelRecord):
    """Door Record"""
    classType = 'DOOR'

    DoorTypeFlags = Flags(0L,Flags.getNames(
        (1, 'automatic'),
        (2, 'hidden'),
        (3, 'minimalUse'),
        (4, 'slidingDoor'),
        (5, 'doNotOpenInCombatSearch'),
    ))

    melSet = MelSet(
        MelString('EDID','eid'),
        MelVmad(),
        MelBounds(),
        MelLString('FULL','full'),
        MelModel(),
        MelDestructible(),
        MelFid('SNAM','soundOpen'),
        MelFid('ANAM','soundClose'),
        MelFid('BNAM','soundLoop'),
        MelStruct('FNAM','B',(DoorTypeFlags,'flags',0L),),
        )
    __slots__ = melSet.getSlotsUsed()

# Verified for 305
#------------------------------------------------------------------------------
class MreDual(MelRecord):
    """Dual Cast Data"""
    classType = 'DUAL'

    DualCastDataFlags = Flags(0L,Flags.getNames(
        (0,'hitEffectArt'),
        (1,'projectile'),
        (2,'explosion'),
    ))

    melSet = MelSet(
        MelString('EDID','eid'),
        MelBounds(),
        MelStruct('DATA','6I',(FID,'projectile'),(FID,'explosion'),(FID,'effectShader'),
                  (FID,'hitEffectArt'),(FID,'impactDataSet'),(DualCastDataFlags,'flags',0L),),
        )
    __slots__ = melSet.getSlotsUsed()

# Verified for 305
#------------------------------------------------------------------------------
class MreEczn(MelRecord):
    """Encounter Zone record."""
    classType = 'ECZN'

    EcznTypeFlags = Flags(0L,Flags.getNames(
            (0, 'neverResets'),
            (1, 'matchPCBelowMinimumLevel'),
            (2, 'disableCombatBoundary'),
        ))

    class MelEcznData(MelStruct):
        """Handle older truncated DATA for ECZN subrecord."""
        def loadData(self, record, ins, sub_type, size_, readId):
            if size_ == 12:
                MelStruct.loadData(self, record, ins, sub_type, size_, readId)
                return
            elif size_ == 8:
                unpacked = ins.unpack('II', size_, readId)
            else:
                raise ModSizeError(record.inName, readId, 12, size_, True)
            unpacked += self.defaults[len(unpacked):]
            setter = record.__setattr__
            for attr,value,action in zip(self.attrs,unpacked,self.actions):
                if callable(action): value = action(value)
                setter(attr,value)
            if self._debug: print unpacked

    melSet = MelSet(
        MelString('EDID','eid'),
        MelEcznData('DATA','2I2bBb',(FID,'owner',None),(FID,'location',None),
                    ('rank',0),('minimumLevel',0),(EcznTypeFlags,'flags',0L),
                    ('maxLevel',0)),
        )
    __slots__ = melSet.getSlotsUsed()

# Verified for 305
#------------------------------------------------------------------------------
class MreEfsh(MelRecord):
    """Efsh Record"""
    classType = 'EFSH'

    EfshGeneralFlags = Flags(0L,Flags.getNames(
        (0, 'noMembraneShader'),
        (1, 'membraneGrayscaleColor'),
        (2, 'membraneGrayscaleAlpha'),
        (3, 'noParticleShader'),
        (4, 'edgeEffectInverse'),
        (5, 'affectSkinOnly'),
        (6, 'ignoreAlpha'),
        (7, 'projectUVs'),
        (8, 'ignoreBaseGeometryAlpha'),
        (9, 'lighting'),
        (10, 'noWeapons'),
        (11, 'unknown11'),
        (12, 'unknown12'),
        (13, 'unknown13'),
        (14, 'unknown14'),
        (15, 'particleAnimated'),
        (16, 'particleGrayscaleColor'),
        (17, 'particleGrayscaleAlpha'),
        (18, 'unknown18'),
        (19, 'unknown19'),
        (20, 'unknown20'),
        (21, 'unknown21'),
        (22, 'unknown22'),
        (23, 'unknown23'),
        (24, 'useBloodGeometry'),
    ))

    class MelEfshData(MelStruct):
        """Handle older truncated DATA for EFSH subrecord."""
        def loadData(self, record, ins, sub_type, size_, readId):
            if size_ == 400:
                MelStruct.loadData(self, record, ins, sub_type, size_, readId)
                return
            elif size_ == 396:
                unpacked = ins.unpack('4s3I3Bs9f3Bs8f5I19f3Bs3Bs3Bs11fI5f3Bsf2I6fI3Bs3Bs9f8I2f', size_, readId)
            elif size_ == 344:
                unpacked = ins.unpack('4s3I3Bs9f3Bs8f5I19f3Bs3Bs3Bs11fI5f3Bsf2I6fI3Bs3Bs6f', size_, readId)
            elif size_ == 312:
                unpacked = ins.unpack('4s3I3Bs9f3Bs8f5I19f3Bs3Bs3Bs11fI5f3Bsf2I6fI', size_, readId)
            elif size_ == 308:
                unpacked = ins.unpack('4s3I3Bs9f3Bs8f5I19f3Bs3Bs3Bs11fI5f3Bsf2I6f', size_, readId)
            else:
                raise ModSizeError(record.inName, readId, 400, size_, True)
            unpacked += self.defaults[len(unpacked):]
            setter = record.__setattr__
            for attr,value,action in zip(self.attrs,unpacked,self.actions):
                if callable(action): value = action(value)
                setter(attr,value)
            if self._debug: print unpacked

    melSet = MelSet(
        MelString('EDID','eid'),
        MelString('ICON','fillTexture'),
        MelString('ICO2','particleShaderTexture'),
        MelString('NAM7','holesTexture'),
        MelString('NAM8','membranePaletteTexture'),
        MelString('NAM9','particlePaletteTexture'),
        MelEfshData('DATA','4s3I3Bs9f3Bs8f5I19f3Bs3Bs3Bs11fI5f3Bsf2I6fI3Bs3Bs9f8I2fI',
                  'unused1','memSBlend','memBlendOp','memZFunc','fillRed',
                  'fillGreen','fillBlue','unused2','fillAlphaIn','fillFullAlpha',
                  'fillAlphaOut','fillAlphaRatio','fillAlphaAmp','fillAlphaPulse',
                  'fillAnimSpeedU','fillAnimSpeedV','edgeEffectOff','edgeRed',
                  'edgeGreen','edgeBlue','unused3','edgeAlphaIn','edgeFullAlpha',
                  'edgeAlphaOut','edgeAlphaRatio','edgeAlphaAmp','edgeAlphaPulse',
                  'fillFullAlphaRatio','edgeFullAlphaRatio','memDestBlend',
                  'partSourceBlend','partBlendOp','partZTestFunc','partDestBlend',
                  'partBSRampUp','partBSFull','partBSRampDown','partBSRatio',
                  'partBSPartCount','partBSLifetime','partBSLifetimeDelta',
                  'partSSpeedNorm','partSAccNorm','partSVel1','partSVel2',
                  'partSVel3','partSAccel1','partSAccel2','partSAccel3',
                  'partSKey1','partSKey2','partSKey1Time','partSKey2Time',
                  'key1Red','key1Green','key1Blue','unused4','key2Red',
                  'key2Green','key2Blue','unused5','key3Red','key3Green',
                  'key3Blue','unused6','colorKey1Alpha','colorKey2Alpha',
                  'colorKey3Alpha','colorKey1KeyTime','colorKey2KeyTime',
                  'colorKey3KeyTime','partSSpeedNormDelta','partSSpeedRotDeg',
                  'partSSpeedRotDegDelta','partSRotDeg','partSRotDegDelta',
                  (FID,'addonModels'),'holesStart','holesEnd','holesStartVal',
                  'holesEndVal','edgeWidthAlphaUnit','edgeAlphRed',
                  'edgeAlphGreen','edgeAlphBlue','unused7','expWindSpeed',
                  'textCountU','textCountV','addonModelIn','addonModelOut',
                  'addonScaleStart','addonScaleEnd','addonScaleIn','addonScaleOut',
                  (FID,'ambientSound'),'key2FillRed','key2FillGreen',
                  'key2FillBlue','unused8','key3FillRed','key3FillGreen',
                  'key3FillBlue','unused9','key1ScaleFill','key2ScaleFill',
                  'key3ScaleFill','key1FillTime','key2FillTime','key3FillTime',
                  'colorScale','birthPosOffset','birthPosOffsetRange','startFrame',
                  'startFrameVariation','endFrame','loopStartFrame',
                  'loopStartVariation','frameCount','frameCountVariation',
                  (EfshGeneralFlags,'flags',0L),'fillTextScaleU',
                  'fillTextScaleV','sceneGraphDepthLimit',
                  ),
        )
    __slots__ = melSet.getSlotsUsed()

# Verified for 305
#------------------------------------------------------------------------------
class MreEnch(MelRecord,MreHasEffects):
    """Enchants"""
    classType = 'ENCH'

    # ENIT has wbEnum in TES5Edit
    # Assigned to 'enchantType' for WB
    # $06, 'Enchantment',
    # $0C, 'Staff Enchantment'

    EnchGeneralFlags = Flags(0L,Flags.getNames(
        (0, 'noAutoCalc'),
        (1, 'unknownTwo'),
        (2, 'extendDurationOnRecast'),
    ))

    class MelEnchEnit(MelStruct):
        """Handle older truncated ENIT for ENCH subrecord."""
        def loadData(self, record, ins, sub_type, size_, readId):
            if size_ == 36:
                MelStruct.loadData(self, record, ins, sub_type, size_, readId)
                return
            elif size_ == 32:
                unpacked = ins.unpack('i2Ii2IfI', size_, readId)
            else:
                raise ModSizeError(record.inName, readId, 36, size_, True)
            unpacked += self.defaults[len(unpacked):]
            setter = record.__setattr__
            for attr,value,action in zip(self.attrs,unpacked,self.actions):
                if callable(action): value = action(value)
                setter(attr,value)
            if self._debug: print unpacked

    melSet = MelSet(
        MelString('EDID','eid'),
        MelBounds(),
        MelLString('FULL','full'),
        MelEnchEnit('ENIT','i2Ii2If2I','enchantmentCost',(EnchGeneralFlags,
                  'generalFlags',0L),'castType','enchantmentAmount','targetType',
                  'enchantType','chargeTime',(FID,'baseEnchantment'),
                  (FID,'wornRestrictions'),
            ),
        MelEffects(),
        )
    __slots__ = melSet.getSlotsUsed()

# Verified for 305
#------------------------------------------------------------------------------
class MreEqup(MelRecord):
    """Equp Item"""
    classType = 'EQUP'
    melSet = MelSet(
        MelString('EDID','eid'),
        MelFidList('PNAM','canBeEquipped'),
        # DATA is either True Of False
        MelStruct('DATA','I','useAllParents'),
        )
    __slots__ = melSet.getSlotsUsed()

# Verified for 305
#------------------------------------------------------------------------------
class MreExpl(MelRecord):
    """Explosion record."""
    classType = 'EXPL'

    # 'Unknown 0',
    # 'Always Uses World Orientation',
    # 'Knock Down - Always',
    # 'Knock Down - By Formula',
    # 'Ignore LOS Check',
    # 'Push Explosion Source Ref Only',
    # 'Ignore Image Space Swap',
    # 'Chain',
    # 'No Controller Vibration'
    ExplTypeFlags = Flags(0L,Flags.getNames(
        (1, 'alwaysUsesWorldOrientation'),
        (2, 'knockDownAlways'),
        (3, 'knockDownByFormular'),
        (4, 'ignoreLosCheck'),
        (5, 'pushExplosionSourceRefOnly'),
        (6, 'ignoreImageSpaceSwap'),
        (7, 'chain'),
        (8, 'noControllerVibration'),
    ))

    class MelExplData(MelStruct):
        """Handle older truncated DATA for EXPL subrecord."""
        def loadData(self, record, ins, sub_type, size_, readId):
            if size_ == 52:
                MelStruct.loadData(self, record, ins, sub_type, size_, readId)
                return
            elif size_ == 48:
                unpacked = ins.unpack('6I5fI', size_, readId)
            elif size_ == 44:
                unpacked = ins.unpack('6I5f', size_, readId)
            elif size_ == 40:
                unpacked = ins.unpack('6I4f', size_, readId)
            else:
                raise ModSizeError(record.inName, readId, 52, size_, True)
            unpacked += self.defaults[len(unpacked):]
            setter = record.__setattr__
            for attr,value,action in zip(self.attrs,unpacked,self.actions):
                if callable(action): value = action(value)
                setter(attr,value)
            if self._debug: print unpacked, record.flags.getTrueAttrs()

    melSet = MelSet(
        MelString('EDID','eid'),
        MelBounds(),
        MelLString('FULL','full'),
        MelModel(),
        MelFid('EITM','objectEffect'),
        MelFid('MNAM','imageSpaceModifier'),
        MelExplData('DATA','6I5f2I',(FID,'light',None),(FID,'sound1',None),(FID,'sound2',None),
                  (FID,'impactDataset',None),(FID,'placedObject',None),(FID,'spawnProjectile',None),
                  'force','damage','radius','isRadius','verticalOffsetMult',
                  (ExplTypeFlags,'flags',0L),'soundLevel',
            ),
        )
    __slots__ = melSet.getSlotsUsed()

# Verified for 305
#------------------------------------------------------------------------------
class MreEyes(MelRecord):
    """Eyes Item"""
    classType = 'EYES'

    # {0x01}'Playable',
    # {0x02}'Not Male',
    # {0x04}'Not Female',
    EyesTypeFlags = Flags(0L,Flags.getNames(
            (0, 'playable'),
            (1, 'notMale'),
            (2, 'notFemale'),
        ))

    melSet = MelSet(
        MelString('EDID','eid'),
        MelLString('FULL','full'),
        MelString('ICON','iconPath'),
        MelString('MICO','smallIconPath'),
        MelStruct('DATA','B',(EyesTypeFlags,'flags',0L)),
        )
    __slots__ = melSet.getSlotsUsed()

# Verified for 305
#------------------------------------------------------------------------------
class MreFact(MelRecord):
    """Fact Faction Records"""
    classType = 'FACT'

    # {0x00000001}'Hidden From NPC',
    # {0x00000002}'Special Combat',
    # {0x00000004}'Unknown 3',
    # {0x00000008}'Unknown 4',
    # {0x00000010}'Unknown 5',
    # {0x00000020}'Unknown 6',
    # {0x00000040}'Track Crime',
    # {0x00000080}'Ignore Crimes: Murder',
    # {0x00000100}'Ignore Crimes: Assault',
    # {0x00000200}'Ignore Crimes: Stealing',
    # {0x00000400}'Ignore Crimes: Trespass',
    # {0x00000800}'Do Not Report Crimes Against Members',
    # {0x00001000}'Crime Gold - Use Defaults',
    # {0x00002000}'Ignore Crimes: Pickpocket',
    # {0x00004000}'Vendor',
    # {0x00008000}'Can Be Owner',
    # {0x00010000}'Ignore Crimes: Werewolf',
    FactGeneralTypeFlags = Flags(0L,Flags.getNames(
        (0, 'hiddenFromPC'),
        (1, 'specialCombat'),
        (2, 'unknown3'),
        (3, 'unknown4'),
        (4, 'unknown5'),
        (5, 'unknown6'),
        (6, 'trackCrime'),
        (7, 'ignoreCrimesMurder'),
        (8, 'ignoreCrimesAssult'),
        (9, 'ignoreCrimesStealing'),
        (10, 'ignoreCrimesTrespass'),
        (11, 'doNotReportCrimesAgainstMembers'),
        (12, 'crimeGold-UseDefaults'),
        (13, 'ignoreCrimesPickpocket'),
        (14, 'allowSell'), # vendor
        (15, 'canBeOwner'),
        (16, 'ignoreCrimesWerewolf'),
    ))

    # ENIT has wbEnum in TES5Edit
    # Assigned to 'combatReaction' for WB
    # 0 :'Neutral',
    # 1 :'Enemy',
    # 2 :'Ally',
    # 3 :'Friend'

#   wbPLVD := wbStruct(PLVD, 'Location', [
#     wbInteger('Type', itS32, wbLocationEnum),
#     wbUnion('Location Value', wbTypeDecider, [
#       {0} wbFormIDCkNoReach('Reference', [NULL, DOOR, PLYR, ACHR, REFR, PGRE, PHZD, PARW, PBAR, PBEA, PCON, PFLA]),
#       {1} wbFormIDCkNoReach('Cell', [NULL, CELL]),
#       {2} wbByteArray('Near Package Start Location', 4, cpIgnore),
#       {3} wbByteArray('Near Editor Location', 4, cpIgnore),
#       {4} wbFormIDCkNoReach('Object ID', [NULL, ACTI, DOOR, STAT, FURN, SPEL, SCRL, NPC_, CONT, ARMO, AMMO, MISC, WEAP, BOOK, KEYM, ALCH, INGR, LIGH, FACT, FLST, IDLM, SHOU]),
#       {5} wbInteger('Object Type', itU32, wbObjectTypeEnum),
#       {6} wbFormIDCk('Keyword', [NULL, KYWD]),
#       {7} wbByteArray('Unknown', 4, cpIgnore),
#       {8} wbInteger('Alias ID', itU32),
#       {9} wbFormIDCkNoReach('Reference', [NULL, DOOR, PLYR, ACHR, REFR, PGRE, PHZD, PARW, PBAR, PBEA, PCON, PFLA]),
#      {10} wbByteArray('Unknown', 4, cpIgnore),
#      {11} wbByteArray('Unknown', 4, cpIgnore),
#      {12} wbByteArray('Unknown', 4, cpIgnore)
#     ]),
#     wbInteger('Radius', itS32)
#   ]);

    class MelFactCrva(MelStruct):
        """Handle older truncated CRVA for FACT subrecord."""
        def loadData(self, record, ins, sub_type, size_, readId):
            if size_ == 20:
                MelStruct.loadData(self, record, ins, sub_type, size_, readId)
                return
            elif size_ == 16:
                unpacked = ins.unpack('2B5Hf', size_, readId)
            elif size_ == 12:
                unpacked = ins.unpack('2B5H', size_, readId)
            else:
                raise ModSizeError(record.inName, readId, 20, size_, True)
            unpacked += self.defaults[len(unpacked):]
            setter = record.__setattr__
            for attr,value,action in zip(self.attrs,unpacked,self.actions):
                if callable(action): value = action(value)
                setter(attr,value)
            if self._debug: print unpacked

    melSet = MelSet(
        MelString('EDID','eid'),
        MelLString('FULL','full'),
        MelStructs('XNAM','IiI','relations',(FID,'faction'),'mod','combatReaction',),
        MelStruct('DATA','I',(FactGeneralTypeFlags,'flags',0L),),
        MelFid('JAIL','exteriorJailMarker'),
        MelFid('WAIT','followerWaitMarker'),
        MelFid('STOL','stolenGoodsContainer'),
        MelFid('PLCN','playerInventoryContainer'),
        MelFid('CRGR','sharedCrimeFactionList'),
        MelFid('JOUT','jailOutfit'),
        # These are Boolean values
        # 'arrest', 'attackOnSight',
        MelFactCrva('CRVA','2B5Hf2H','arrest','attackOnSight','murder','assult',
        'trespass','pickpocket','unknown','stealMultiplier','escape','werewolf'),
        MelGroups('ranks',
            MelStruct('RNAM','I','rank'),
            MelLString('MNAM','maleTitle'),
            MelLString('FNAM','femaleTitle'),
            MelString('INAM','insigniaPath'),
        ),
        MelFid('VEND','vendorBuySellList'),
        MelFid('VENC','merchantContainer'),
        MelStruct('VENV','3H2s2B2s','startHour','endHour','radius','unknownOne',
                  'onlyBuysStolenItems','notSellBuy','UnknownTwo'),
        MelOptStruct('PLVD','iIi','type',(FID,'locationValue'),'radius',),
        MelStruct('CITC','I','conditionCount'),
        MelConditions(),
        )
    __slots__ = melSet.getSlotsUsed()

    def dumpData(self,out):
        conditions = self.conditions
        if conditions:
            self.conditionCount = len(conditions) if conditions else 0
            MelRecord.dumpData(self,out)

# Verified for 305
#------------------------------------------------------------------------------
class MreFlor(MelRecord):
    """Flor Item"""
    classType = 'FLOR'

    melSet = MelSet(
        MelString('EDID','eid'),
        MelVmad(),
        MelBounds(),
        MelLString('FULL','full'),
        MelModel(),
        MelDestructible(),
        MelKeywords(),
        MelBase('PNAM','unknown01'),
        MelLString('RNAM','activateTextOverride'),
        MelBase('FNAM','unknown02'),
        MelFid('PFIG','ingredient'),
        MelFid('SNAM','harvestSound'),
        MelStruct('PFPC','4B','spring','summer','fall','winter',),
        )
    __slots__ = melSet.getSlotsUsed()

# Verified for 305
#------------------------------------------------------------------------------
class MreFlst(MelRecord):
    """FormID list record."""
    classType = 'FLST'
    melSet = MelSet(
        MelString('EDID','eid'),
        MelFids('LNAM','formIDInList'),
        )
    __slots__ = (melSet.getSlotsUsed() +
        ['mergeOverLast','mergeSources','items','deflsts', 'canListMerge'])

    """ Skyrim's FLST can't always be merged if a mod depends on the order of
    the LNAM records for the Papyrus scripts.

    Solution: Create a Bash tag that indicates when a list cannot be merged.
    If even one mod has this tag then the list is not merged into the
    Bash Patch."""

    # The same with Relev, Delev the 'NoFlstMerge' tag applies to the entire mod
    # even if only one FLST requires it.  When parsing the FLSTs from other mods
    # Wrye Bash should skip any FLST from a mod with the 'NoFlstMerge' tag.
    # Example, ModA has 10 FLST, MODB has 11 FLST.  Ten of the lists are the same
    # Between the two mods.  Since only one list is different, only one FLST is
    # different then only one FLST would be mergable.

    # New Bash Tag 'NoFlstMerge'
    def __init__(self, header, ins=None, do_unpack=False):
        """Initialize."""
        MelRecord.__init__(self, header, ins, do_unpack)
        self.mergeOverLast = False #--Merge overrides last mod merged
        self.mergeSources = None #--Set to list by other functions
        self.items  = None #--Set of items included in list
        #--Set of items deleted by list (Deflst mods) unused for Skyrim
        self.deflsts = None

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
            self.formIDInList = [fid for fid in self.formIDInList if fid not in removeItems]
            self.items = (self.items | other.deflsts)
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
            # self.formIDInList.sort() # most likely shouldn't sort for skyrim
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

# Verified for 305
#------------------------------------------------------------------------------
class MreFstp(MelRecord):
    """Footstep"""
    classType = 'FSTP'
    melSet = MelSet(
        MelString('EDID','eid'),
        MelFid('DATA','impactSet'),
        MelString('ANAM','tag'),
        )
    __slots__ = melSet.getSlotsUsed()

# Verified for 305
#------------------------------------------------------------------------------
class MreFsts(MelRecord):
    """Footstep Set."""
    classType = 'FSTS'
    melSet = MelSet(
        MelString('EDID','eid'),
        MelStruct('XCNT','5I','walkForward','runForward','walkForwardAlt',
                  'runForwardAlt','walkForwardAlternate2',
            ),
        MelFidList('DATA','footstepSets'),
        )
    __slots__ = melSet.getSlotsUsed()

# Verified for 305
#------------------------------------------------------------------------------
class MreFurn(MelRecord):
    """Furniture"""
    classType = 'FURN'

    # {0x0001} 'Unknown 0',
    # {0x0002} 'Ignored By Sandbox'
    FurnGeneralFlags = Flags(0L,Flags.getNames(
        (1, 'ignoredBySandbox'),
    ))

    # {0x00000001} 'Sit 0',
    # {0x00000002} 'Sit 1',
    # {0x00000004} 'Sit 2',
    # {0x00000008} 'Sit 3',
    # {0x00000010} 'Sit 4',
    # {0x00000020} 'Sit 5',
    # {0x00000040} 'Sit 6',
    # {0x00000080} 'Sit 7',
    # {0x00000100} 'Sit 8',
    # {0x00000200} 'Sit 9',
    # {0x00000400} 'Sit 10',
    # {0x00000800} 'Sit 11',
    # {0x00001000} 'Sit 12',
    # {0x00002000} 'Sit 13',
    # {0x00004000} 'Sit 14',
    # {0x00008000} 'Sit 15',
    # {0x00010000} 'Sit 16',
    # {0x00020000} 'Sit 17',
    # {0x00040000} 'Sit 18',
    # {0x00080000} 'Sit 19',
    # {0x00100000} 'Sit 20',
    # {0x00200000} 'Sit 21',
    # {0x00400000} 'Sit 22',
    # {0x00800000} 'Sit 23',
    # {0x01000000} 'Unknown 25',
    # {0x02000000} 'Disables Activation',
    # {0x04000000} 'Is Perch',
    # {0x08000000} 'Must Exit to Talk',
    # {0x10000000} 'Unknown 29',
    # {0x20000000} 'Unknown 30',
    # {0x40000000} 'Unknown 31',
    # {0x80000000} 'Unknown 32'
    FurnActiveMarkerFlags = Flags(0L,Flags.getNames(
        (0, 'sit0'),
        (1, 'sit1'),
        (2, 'sit2'),
        (3, 'sit3'),
        (4, 'sit4'),
        (5, 'sit5'),
        (6, 'sit6'),
        (7, 'sit7'),
        (8, 'sit8'),
        (9, 'sit9'),
        (10, 'sit10'),
        (11, 'sit11'),
        (12, 'sit12'),
        (13, 'sit13'),
        (14, 'sit14'),
        (15, 'sit15'),
        (16, 'sit16'),
        (17, 'sit17'),
        (18, 'sit18'),
        (19, 'sit19'),
        (20, 'sit20'),
        (21, 'Sit21'),
        (22, 'Sit22'),
        (23, 'sit23'),
        (24, 'unknown25'),
        (25, 'disablesActivation'),
        (26, 'isPerch'),
        (27, 'mustExittoTalk'),
        (28, 'unknown29'),
        (29, 'unknown30'),
        (30, 'unknown31'),
        (31, 'unknown32'),
    ))

    # {0x01} 'Front',
    # {0x02} 'Behind',
    # {0x04} 'Right',
    # {0x08} 'Left',
    # {0x10} 'Up'
    MarkerEntryPointFlags = Flags(0L,Flags.getNames(
            (0, 'front'),
            (1, 'behind'),
            (2, 'right'),
            (3, 'left'),
            (4, 'up'),
        ))

    # FNPR has wbEnum in TES5Edit
    # Assigned to 'MarkerType' for WB
    # 0 :'',
    # 1 :'Sit',
    # 2 :'Lay',
    # 3 :'',
    # 4 :'Lean'

    # WBDT has wbEnum in TES5Edit
    # Assigned to 'benchType' for WB
    # 0 :'None',
    # 1 :'Create object',
    # 2 :'Smithing Weapon',
    # 3 :'Enchanting',
    # 4 :'Enchanting Experiment',
    # 5 :'Alchemy',
    # 6 :'Alchemy Experiment',
    # 7 :'Smithing Armor'

    # WBDT has wbEnum in TES5Edit
    # Assigned to 'usesSkill' for WB
    # Refer to wbSkillEnum is TES5Edit for values

    melSet = MelSet(
        MelString('EDID','eid'),
        MelVmad(),
        MelBounds(),
        MelLString('FULL','full'),
        MelModel(),
        MelDestructible(),
        MelKeywords(),
        MelBase('PNAM','pnam_p'),
        MelStruct('FNAM','H',(FurnGeneralFlags,'general_f',None),),
        MelFid('KNAM','interactionKeyword'),
        MelStruct('MNAM','I',(FurnActiveMarkerFlags,'activeMarkers',None)),
        MelStruct('WBDT','Bb','benchType','usesSkill',),
        MelFid('NAM1','associatedSpell'),
        MelGroups('markers',
            MelStruct('ENAM','I','markerIndex',),
            MelStruct('NAM0','2sH','unknown',(MarkerEntryPointFlags,'disabledPoints_f',None),),
            MelFid('FNMK','markerKeyword',),
            ),
        MelStructs('FNPR','2H','entryPoints','markerType',(MarkerEntryPointFlags,'entryPointsFlags',None),),
        MelString('XMRK','modelFilename'),
        )
    __slots__ = melSet.getSlotsUsed()

# Verified for 305
#------------------------------------------------------------------------------
# Marker for organization please don't remove ---------------------------------
# GLOB ------------------------------------------------------------------------
# Defined in brec.py as class MreGlob(MelRecord) ------------------------------
#------------------------------------------------------------------------------
class MreGmst(MreGmstBase):
    """Skyrim GMST record"""
    isKeyedByEid = True # NULL fids are acceptable.

# Verified for 305
#------------------------------------------------------------------------------
class MreGras(MelRecord):
    """Grass record."""
    classType = 'GRAS'

    GrasTypeFlags = Flags(0L,Flags.getNames(
            (0, 'vertexLighting'),
            (1, 'uniformScaling'),
            (2, 'fitToSlope'),
        ))

    # DATA has wbEnum in TES5Edit
    # Assigned to 'unitsFromWaterType' for WB
    # 0 :'Above - At Least',
    # 1 :'Above - At Most',
    # 2 :'Below - At Least',
    # 3 :'Below - At Most',
    # 4 :'Either - At Least',
    # 5 :'Either - At Most',
    # 6 :'Either - At Most Above',
    # 7 :'Either - At Most Below'

    melSet = MelSet(
        MelString('EDID','eid'),
        MelBounds(),
        MelModel(),
        MelStruct('DATA','3BsH2sI4fB3s','density','minSlope','maxSlope',
                  ('unkGras1', null1),'unitsFromWater',('unkGras2', null2),
                  'unitsFromWaterType','positionRange','heightRange',
                  'colorRange','wavePeriod',(GrasTypeFlags,'flags',0L),
                  ('unkGras3', null3),
                  ),
        )
    __slots__ = melSet.getSlotsUsed()

# Verified for 305
#------------------------------------------------------------------------------
class MreHazd(MelRecord):
    """Hazard"""
    classType = 'HAZD'

    # {0x01} 'Affects Player Only',
    # {0x02} 'Inherit Duration from Spawn Spell',
    # {0x04} 'Align to Impact Normal',
    # {0x08} 'Inherit Radius from Spawn Spell',
    # {0x10} 'Drop to Ground'
    HazdTypeFlags = Flags(0L,Flags.getNames(
        (0, 'affectsPlayerOnly'),
        (1, 'inheritDurationFromSpawnSpell'),
        (2, 'alignToImpactNormal'),
        (3, 'inheritRadiusFromSpawnSpell'),
        (4, 'dropToGround'),
    ))

    melSet = MelSet(
        MelString('EDID','eid'),
        MelBounds(),
        MelLString('FULL','full'),
        MelModel(),
        MelFid('MNAM','imageSpaceModifier'),
        MelStruct('DATA','I4f5I','limit','radius','lifetime',
                  'imageSpaceRadius','targetInterval',(HazdTypeFlags,'flags',0L),
                  (FID,'spell'),(FID,'light'),(FID,'impactDataSet'),(FID,'sound'),),
        )
    __slots__ = melSet.getSlotsUsed()

# Verified for 305
#------------------------------------------------------------------------------
class MreHdpt(MelRecord):
    """Head Part"""
    classType = 'HDPT'

    # NAM0 has wbEnum in TES5Edit
    # Assigned to 'headPartType' for WB
    # 0 :'Race Morph',
    # 1 :'Tri',
    # 2 :'Chargen Morph'

    # PNAM has wbEnum in TES5Edit
    # Assigned to 'hdptTypes' for WB
    # 0 :'Misc',
    # 1 :'Face',
    # 2 :'Eyes',
    # 3 :'Hair',
    # 4 :'Facial Hair',
    # 5 :'Scar',
    # 6 :'Eyebrows'

    # {0x01} 'Playable',
    # {0x02} 'Male',
    # {0x04} 'Female',
    # {0x10} 'Is Extra Part',
    # {0x20} 'Use Solid Tint'
    HdptTypeFlags = Flags(0L,Flags.getNames(
        (0, 'playable'),
        (1, 'male'),
        (2, 'female'),
        (3, 'isExtraPart'),
        (4, 'useSolidTint'),
    ))

    melSet = MelSet(
        MelString('EDID','eid'),
        MelLString('FULL','full'),
        MelModel(),
        MelStruct('DATA','B',(HdptTypeFlags,'flags',0L),),
        MelStruct('PNAM','I','hdptTypes',),
        MelFids('HNAM','extraParts'),
        MelGroups('partsData',
            MelStruct('NAM0','I','headPartType',),
            MelString('NAM1','filename'),
            ),
        MelFid('TNAM','textureSet'),
        MelFid('CNAM','color'),
        MelFid('RNAM','validRaces'),
        )
    __slots__ = melSet.getSlotsUsed()

# Verified for 305
#------------------------------------------------------------------------------
class MreIdle(MelRecord):
    """Idle record."""
    classType = 'IDLE'

    IdleTypeFlags = Flags(0L,Flags.getNames(
            (0, 'parent'),
            (1, 'sequence'),
            (2, 'noAttacking'),
            (3, 'blocking'),
        ))

    melSet = MelSet(
        MelString('EDID','eid'),
        MelConditions(),
        MelString('DNAM','filename'),
        MelString('ENAM','animationEvent'),
        MelGroups('idleAnimations',
            MelStruct('ANAM','II',(FID,'parent'),(FID,'prevId'),),
            ),
        MelStruct('DATA','4BH','loopMin','loopMax',(IdleTypeFlags,'flags',0L),
                  'animationGroupSection','replayDelay',),
        )
    __slots__ = melSet.getSlotsUsed()

# Verified for 305
#------------------------------------------------------------------------------
class MreIdlm(MelRecord):
    """Idle marker record."""
    classType = 'IDLM'

    IdlmTypeFlags = Flags(0L,Flags.getNames(
        (0, 'runInSequence'),
        (1, 'unknown1'),
        (2, 'doOnce'),
        (3, 'unknown3'),
        (4, 'ignoredBySandbox'),
    ))

    melSet = MelSet(
        MelString('EDID','eid'),
        MelBounds(),
        MelStruct('IDLF','B',(IdlmTypeFlags,'flags',0L),),
        MelStruct('IDLC','B','animationCount',),
        MelStruct('IDLT','f','idleTimerSetting'),
        MelFidList('IDLA','animations'),
        MelModel(),
        )
    __slots__ = melSet.getSlotsUsed()

# Verified for 305
#------------------------------------------------------------------------------
class MreInfo(MelRecord):
    """Dialog response"""
    classType = 'INFO'

    # TRDT has wbEnum in TES5Edit
    # Assigned to 'emotionType' for WB
    # {0} 'Neutral',
    # {1} 'Anger',
    # {2} 'Disgust',
    # {3} 'Fear',
    # {4} 'Sad',
    # {5} 'Happy',
    # {6} 'Surprise',
    # {7} 'Puzzled'

    # CNAM has wbEnum in TES5Edit
    # Assigned to 'favorLevel' for WB
    # 0 :'None',
    # 1 :'Small',
    # 2 :'Medium',
    # 3 :'Large'

    # 'Use Emotion Animation'
    InfoResponsesFlags = Flags(0L,Flags.getNames(
            (0, 'useEmotionAnimation'),
        ))

    # {0x0001} 'Goodbye',
    # {0x0002} 'Random',
    # {0x0004} 'Say once',
    # {0x0008} 'Unknown 4',
    # {0x0010} 'Unknown 5',
    # {0x0020} 'Random end',
    # {0x0040} 'Invisible continue',
    # {0x0080} 'Walk Away',
    # {0x0100} 'Walk Away Invisible in Menu',
    # {0x0200} 'Force subtitle',
    # {0x0400} 'Can move while greeting',
    # {0x0800} 'No LIP File',
    # {0x1000} 'Requires post-processing',
    # {0x2000} 'Audio Output Override',
    # {0x4000} 'Spends favor points',
    # {0x8000} 'Unknown 16'
    EnamResponseFlags = Flags(0L,Flags.getNames(
            (0, 'goodbye'),
            (1, 'random'),
            (2, 'sayonce'),
            (3, 'unknown4'),
            (4, 'unknown5'),
            (5, 'randomend'),
            (6, 'invisiblecontinue'),
            (7, 'walkAway'),
            (8, 'walkAwayInvisibleinMenu'),
            (9, 'forcesubtitle'),
            (10, 'canmovewhilegreeting'),
            (11, 'noLIPFile'),
            (12, 'requirespostprocessing'),
            (13, 'audioOutputOverride'),
            (14, 'spendsfavorpoints'),
            (15, 'unknown16'),
        ))

    melSet = MelSet(
        MelString('EDID','eid'),
        MelVmad(),
        MelBase('DATA','data_p'),
        MelStruct('ENAM','2H',(EnamResponseFlags,'flags',0L),'resetHours',),
        MelFid('TPIC','topic',),
        MelFid('PNAM','prevInfo',),
        MelStruct('CNAM','I','favorLevel',),
        MelFids('TCLT','response',),
        MelFid('DNAM','responseData',),
        # {>>> Unordered, CTDA can appear before or after LNAM <- REQUIRES CONFIRMATION <<<}
        MelGroups('responses',
            MelStruct('TRDT','II4sB3sIB3s','emotionType','emotionValue',
                      'unused','responsenumber','unused',(FID,'sound'),
                      (InfoResponsesFlags,'flags',0L),'unused',),
            MelLString('NAM1','responseText'),
            MelString('NAM2','scriptNotes'),
            MelString('NAM3','edits'),
            MelFid('SNAM','idleAnimationsSpeaker',),
            MelFid('LNAM','idleAnimationsListener',),
            ),

        MelConditions(),

        MelGroups('leftOver',
            MelBase('SCHR','unknown1'),
            MelFid('QNAM','unknown2'),
            MelNull('NEXT'),
            ),
        MelLString('RNAM','prompt'),
        MelFid('ANAM','speaker',),
        MelFid('TWAT','walkAwayTopic',),
        MelFid('ONAM','audioOutputOverride',),
        )
    __slots__ = melSet.getSlotsUsed()

# Verified for 305
#------------------------------------------------------------------------------
class MreImad(MelRecord):
    """Image Space Adapter"""
    classType = 'IMAD'

    # {0x00000001}'Use Target',
    # {0x00000002}'Unknown 2',
    # {0x00000004}'Unknown 3',
    # {0x00000008}'Unknown 4',
    # {0x00000010}'Unknown 5',
    # {0x00000020}'Unknown 6',
    # {0x00000040}'Unknown 7',
    # {0x00000080}'Unknown 8',
    # {0x00000100}'Mode - Front',
    # {0x00000200}'Mode - Back',
    # {0x00000400}'No Sky',
    # {0x00000800}'Blur Radius Bit 2',
    # {0x00001000}'Blur Radius Bit 1',
    # {0x00002000}'Blur Radius Bit 0'
    ImadDoFFlags = Flags(0L,Flags.getNames(
            (0, 'useTarget'),
            (1, 'unknown2'),
            (2, 'unknown3'),
            (3, 'unknown4'),
            (4, 'unknown5'),
            (5, 'unknown6'),
            (6, 'unknown7'),
            (7, 'unknown8'),
            (8, 'modeFront'),
            (9, 'modeBack'),
            (10, 'noSky'),
            (11, 'blurRadiusBit2'),
            (12, 'blurRadiusBit1'),
            (13, 'blurRadiusBit0'),
        ))

    ImadUseTargetFlags = Flags(0L,Flags.getNames(
            (0, 'useTarget'),
        ))

    ImadAnimatableFlags = Flags(0L,Flags.getNames(
            (0, 'animatable'),
        ))

    melSet = MelSet(
        MelString('EDID','eid'),
        # 'unknown' is 192 bytes in TES5Edit
        # 'unknown1' is 4 bytes repeated 3 times for 12 bytes in TES5Edit
        MelStruct('DNAM','If192sI2f12sI',(ImadAnimatableFlags,'aniFlags',0L),'duration',
                  'unknown',(ImadUseTargetFlags,'flags',0L),'radialBlurCenterX',
                  'radialBlurCenterY','unknown1',(ImadDoFFlags,'dofFlags',0L),
                  dumpExtra='unknownExtra1',),
        # Blur
        MelStruct('BNAM','2f','blurUnknown','blurRadius',dumpExtra='unknownExtra2',),
        # Double Vision
        MelStruct('VNAM','2f','dvUnknown','dvStrength',dumpExtra='unknownExtra3',),
        # Cinematic Colors
        MelStruct('TNAM','5f','unknown4','tintRed','tintGreen','tintBlue',
                  'tintAlpha',dumpExtra='unknownExtra4',),
        MelStruct('NAM3','5f','unknown5','fadeRed','fadeGreen','fadeBlue',
                  'fadeAlpha',dumpExtra='unknownExtra5',),
        # {<<<< Begin Radial Blur >>>>}
        MelStruct('RNAM','2f','unknown6','rnamStrength',dumpExtra='unknownExtra6',),
        MelStruct('SNAM','2f','unknown7','rampup',dumpExtra='unknownExtra7',),
        MelStruct('UNAM','2f','unknown8','start',dumpExtra='unknownExtra8',),
        MelStruct('NAM1','2f','unknown9','rampdown',dumpExtra='unknownExtra9',),
        MelStruct('NAM2','2f','unknown10','downstart',dumpExtra='unknownExtra10',),
        # {<<<< End Radial Blur >>>>}
        # {<<<< Begin Depth of Field >>>>}
        MelStruct('WNAM','2f','unknown11','wnamStrength',dumpExtra='unknownExtra11',),
        MelStruct('XNAM','2f','unknown12','distance',dumpExtra='unknownExtra12',),
        MelStruct('YNAM','2f','unknown13','range',dumpExtra='unknownExtra13',),
        # {<<<< FullScreen Motion Blur >>>>}
        MelStruct('NAM4','2f','unknown14','nam4Strength',dumpExtra='unknownExtra14',),
        # {<<<< End Depth of Field >>>>}
        # {<<<< Begin HDR >>>>}
        MelStructA('\x00IAD','2f','eyeAdaptSpeedMult','time1','value1'),
        MelStructA('\x40IAD','2f','eyeAdaptSpeedAdd','time2','value2'),
        MelStructA('\x01IAD','2f','bloomBlurRadiusMult','time3','value3'),
        MelStructA('\x41IAD','2f','bloomBlurRadiusAdd','time4','value4'),
        MelStructA('\x02IAD','2f','bloomThresholdMult','time5','value5'),
        MelStructA('\x42IAD','2f','bloomThresholdAdd','time6','value6'),
        MelStructA('\x03IAD','2f','bloomScaleMult','time7','value7'),
        MelStructA('\x43IAD','2f','bloomScaleAdd','time8','value8'),
        MelStructA('\x04IAD','2f','targetLumMinMult','time9','value9'),
        MelStructA('\x44IAD','2f','targetLumMinAdd','time10','value10'),
        MelStructA('\x05IAD','2f','targetLumMaxMult','time11','value11'),
        MelStructA('\x45IAD','2f','targetLumMaxAdd','time12','value12'),
        MelStructA('\x06IAD','2f','sunlightScaleMult','time13','value13'),
        MelStructA('\x46IAD','2f','sunlightScaleAdd','time14','value14'),
        MelStructA('\x07IAD','2f','skyScaleMult','time15','value15'),
        MelStructA('\x47IAD','2f','skyScaleAdd','time16','value16'),
        # {<<<< End HDR >>>>}
        MelBase('\x08IAD','isd08IAD_p'),
        MelBase('\x48IAD','isd48IAD_p'),
        MelBase('\x09IAD','isd09IAD_p'),
        MelBase('\x49IAD','isd49IAD_p'),
        MelBase('\x0AIAD','isd0aIAD_p'),
        MelBase('\x4AIAD','isd4aIAD_p'),
        MelBase('\x0BIAD','isd0bIAD_p'),
        MelBase('\x4BIAD','isd4bIAD_p'),
        MelBase('\x0CIAD','isd0cIAD_p'),
        MelBase('\x4CIAD','isd4cIAD_p'),
        MelBase('\x0DIAD','isd0dIAD_p'),
        MelBase('\x4DIAD','isd4dIAD_p'),
        MelBase('\x0EIAD','isd0eIAD_p'),
        MelBase('\x4EIAD','isd4eIAD_p'),
        MelBase('\x0FIAD','isd0fIAD_p'),
        MelBase('\x4FIAD','isd4fIAD_p'),
        MelBase('\x10IAD','isd10IAD_p'),
        MelBase('\x50IAD','isd50IAD_p'),
        # {<<<< Begin Cinematic >>>>}
        MelStructA('\x11IAD','2f','saturationMult','time17','value17'),
        MelStructA('\x51IAD','2f','saturationAdd','time18','value18'),
        MelStructA('\x12IAD','2f','brightnessMult','time19','value19'),
        MelStructA('\x52IAD','2f','brightnessAdd','time20','value20'),
        MelStructA('\x13IAD','2f','contrastMult','time21','value21'),
        MelStructA('\x53IAD','2f','contrastAdd','time22','value22'),
        # {<<<< End Cinematic >>>>}
        MelBase('\x14IAD','isd14IAD_p'),
        MelBase('\x54IAD','isd54IAD_p'),
        )
    __slots__ = melSet.getSlotsUsed()

# Verified for 305
#------------------------------------------------------------------------------
class MreImgs(MelRecord):
    """Imgs Item"""
    classType = 'IMGS'

    # DNAM has wbEnum in TES5Edit
    # Assigned to 'skyBlurRadius' for WB
    # 16384 :'Radius 0',
    # 16672 :'Radius 1',
    # 16784 :'Radius 2',
    # 16848 :'Radius 3',
    # 16904 :'Radius 4',
    # 16936 :'Radius 5',
    # 16968 :'Radius 6',
    # 17000 :'Radius 7',
    # 16576 :'No Sky, Radius 0',
    # 16736 :'No Sky, Radius 1',
    # 16816 :'No Sky, Radius 2',
    # 16880 :'No Sky, Radius 3',
    # 16920 :'No Sky, Radius 4',
    # 16952 :'No Sky, Radius 5',
    # 16984 :'No Sky, Radius 6',
    # 17016 :'No Sky, Radius 7'

    melSet = MelSet(
        MelString('EDID','eid'),
        MelBase('ENAM','eman_p'),
        MelStruct('HNAM','9f','eyeAdaptSpeed','bloomBlurRadius','bloomThreshold','bloomScale',
                  'receiveBloomThreshold','white','sunlightScale','skyScale',
                  'eyeAdaptStrength',),
        MelStruct('CNAM','3f','Saturation','Brightness','Contrast',),
        MelStruct('TNAM','4f','tintAmount','tintRed','tintGreen','tintBlue',),
        MelStruct('DNAM','3f2sH','dofStrength','dofDistance','dofRange','unknown',
                  'skyBlurRadius',),
        )
    __slots__ = melSet.getSlotsUsed()

# Verified for 305
#------------------------------------------------------------------------------
class MreIngr(MelRecord,MreHasEffects):
    """INGR (ingredient) record."""
    classType = 'INGR'

    IngrTypeFlags = Flags(0L,Flags.getNames(
            (0, 'No auto-calculation'),
            (1, 'Food item'),
            (2, 'Unknown 3'),
            (3, 'Unknown 4'),
            (4, 'Unknown 5'),
            (5, 'Unknown 6'),
            (6, 'Unknown 7'),
            (7, 'Unknown 8'),
            (8, 'References Persist'),
    ))

    melSet = MelSet(
        MelString('EDID','eid'),
        MelVmad(),
        MelBounds(),
        MelLString('FULL','full'),
        MelKeywords(),
        MelModel(),
        MelString('ICON','iconPath'),
        MelString('MICO','smallIconPath'),
        MelFid('ETYP','equipmentType',),
        MelFid('YNAM','pickupSound'),
        MelFid('ZNAM','dropSound'),
        MelStruct('DATA','if','value','weight'),
        MelStruct('ENIT','iI','ingrValue',(IngrTypeFlags,'flags',0L),),
        MelEffects(),
        )
    __slots__ = melSet.getSlotsUsed()

# Verified for 305
#------------------------------------------------------------------------------
class MreIpctData(MelStruct):
    """Ipct Data Custom Unpacker"""

    # DATA has wbEnums in TES5Edit
    # 'effectDuration' is defined as follows
    # 0 :'Surface Normal',
    # 1 :'Projectile Vector',
    # 2 :'Projectile Reflection'

    # 'impactResult' is defined as follows
    # 0 :'Default',
    # 1 :'Destroy',
    # 2 :'Bounce',
    # 3 :'Impale',
    # 4 :'Stick'

    # for 'soundLevel' refer to wbSoundLevelEnum

    # {0x01} 'No Decal Data'
    IpctTypeFlags = Flags(0L,Flags.getNames(
        (0, 'noDecalData'),
    ))

    def __init__(self, subType='DATA'):
        MelStruct.__init__(self, subType, 'fI2fI2B2s', 'effectDuration', 'effectOrientation',
                  'angleThreshold','placementRadius','soundLevel',
                           (MreIpctData.IpctTypeFlags,'ipctFlags',0L),'impactResult',('unkIpct1',null1),),

    def loadData(self, record, ins, sub_type, size_, readId):
        """Handle older truncated DATA for IPCT subrecord."""
        if size_ == 24:
            MelStruct.loadData(self, record, ins, sub_type, size_, readId)
            return
        elif size_ == 16:
            unpacked = ins.unpack('=fI2f', size_, readId) #  + (0,0,0,0,)
        else:
            raise ModSizeError(record.inName, readId, 24, size_, True)
        unpacked += self.defaults[len(unpacked):]
        setter = record.__setattr__
        for attr,value,action in zip(self.attrs,unpacked,self.actions):
            if callable(action): value = action(value)
            setter(attr,value)
        if self._debug:
            print u' ',zip(self.attrs,unpacked)
            if len(unpacked) != len(self.attrs):
                print u' ',unpacked

class MreIpct(MelRecord):
    """Impact record."""
    classType = 'IPCT'

    melSet = MelSet(
        MelString('EDID','eid'),
        MelModel(),
        MreIpctData(),
        MelDecalData(),
        MelFid('DNAM','textureSet'),
        MelFid('ENAM','secondarytextureSet'),
        MelFid('SNAM','sound1'),
        MelFid('NAM1','sound2'),
        MelFid('NAM2','hazard'),
        )
    __slots__ = melSet.getSlotsUsed()

# Verified for 305
#------------------------------------------------------------------------------
class MreIpds(MelRecord):
    """Ipds Item"""
    classType = 'IPDS'
    melSet = MelSet(
        MelString('EDID','eid'),
        # This is a repeating subrecord of 8 bytes, 2 FormIDs First is MATT second is IPCT
        MelStructs('PNAM','2I','impactData',(FID,'material'),(FID,'impact'),),
        )
    __slots__ = melSet.getSlotsUsed()

# Verified for 305
#------------------------------------------------------------------------------
class MreKeym(MelRecord):
    """KEYM Key records."""
    classType = 'KEYM'

    melSet = MelSet(
        MelString('EDID','eid'),
        MelVmad(),
        MelBounds(),
        MelLString('FULL','full'),
        MelModel(),
        MelString('ICON','iconPath'),
        MelString('MICO','smallIconPath'),
        MelDestructible(),
        MelFid('YNAM','pickupSound'),
        MelFid('ZNAM','dropSound'),
        MelKeywords(),
        MelStruct('DATA','if','value','weight'),
        )
    __slots__ = melSet.getSlotsUsed()

# Verified for 305
#------------------------------------------------------------------------------
class MreKywd(MelRecord):
    """Keyword record."""
    classType = 'KYWD'
    melSet = MelSet(
        MelString('EDID','eid'),
        MelColorN(),
        )
    __slots__ = melSet.getSlotsUsed()

# Verified for 305
#------------------------------------------------------------------------------
# Commented out for performance reasons. Slows down loading quite a bit.
# If Bash ever wants to be able to add masters to a mod, this minimal definition is required
# It has to be able to convert the formIDs found in BTXT, ATXT, and VTEX to not break the mod
#
#class MreLand(MelRecord):
#    """Land structure. Part of exterior cells."""
#
#    classType = 'LAND'
#    melSet = MelSet(
#        MelBase('DATA','data_p'),
#        MelBase('VNML','normals_p'),
#        MelBase('VHGT','heights_p'),
#        MelBase('VCLR','vertexColors_p'),
#        # wbRUnion Needed (BTXT) or ('ATXT' and 'VTXT'), not both
#        MelStructs('BTXT','IBsh','baseTextures', (FID,'texture'), 'quadrant', 'unknown', 'layer'),
#        MelGroups('alphaLayers',
#            MelStruct('ATXT','IBsh',(FID,'texture'), 'quadrant', 'unknown', 'layer'),
#            MelStructA('VTXT','H2Bf', 'opacities', 'position', 'unknown', 'opacity'),
#        ),
#        MelFidList('VTEX','vertexTextures'),
#    )
#    __slots__ = melSet.getSlotsUsed()
# --
# Likely not a good idea to use because of performance
#------------------------------------------------------------------------------
class MreLcrt(MelRecord):
    """Location Reference Type record."""
    classType = 'LCRT'
    melSet = MelSet(
        MelString('EDID','eid'),
        MelColorN(),
        )
    __slots__ = melSet.getSlotsUsed()

# Verified for 305
#------------------------------------------------------------------------------
class MreLctn(MelRecord):
    """Location"""
    classType = 'LCTN'

    melSet = MelSet(
        MelString('EDID','eid'),

        MelStructA('ACPR','2I2h','actorCellPersistentReference',
                   (FID,'actor'),(FID,'location'),'gridX','gridY',),
        MelStructA('LCPR','2I2h','locationCellPersistentReference',
                     (FID,'actor'),(FID,'location'),'gridX','gridY',),
        # From Danwguard.esm, Does not follow similar previous patterns
        MelFidList('RCPR','referenceCellPersistentReference',),

        MelStructA('ACUN','3I','actorCellUnique',
                     (FID,'actor'),(FID,'eef'),(FID,'location'),),
        MelStructA('LCUN','3I','locationCellUnique',
                     (FID,'actor'),(FID,'ref'),(FID,'location'),),
        # in Unofficial Skyrim patch
        MelFidList('RCUN','referenceCellUnique',),

        MelStructA('ACSR','3I2h','actorCellStaticReference',
                     (FID,'locRefType'),(FID,'marker'),(FID,'location'),
                     'gridX','gridY',),
        MelStructA('LCSR','3I2h','locationCellStaticReference',
                     (FID,'locRefType'),(FID,'marker'),(FID,'location'),
                     'gridX','gridY',),
        # Seen in Open Cities
        MelFidList('RCSR','referenceCellStaticReference',),

        MelStructs('ACEC','I','actorCellEncounterCell',
                  (FID,'actor'), dumpExtra='gridsXYAcec',),
        MelStructs('LCEC','I','locationCellEncounterCell',
                  (FID,'actor'), dumpExtra='gridsXYLcec',),
        # Seen in Open Cities
        MelStructs('RCEC','I','referenceCellEncounterCell',
                  (FID,'actor'), dumpExtra='gridsXYRcec',),

        MelFidList('ACID','actorCellMarkerReference',),
        MelFidList('LCID','locationCellMarkerReference',),

        MelStructA('ACEP','2I2h','actorCellEnablePoint',
                     (FID,'actor'),(FID,'ref'),'gridX','gridY',),
        MelStructA('LCEP','2I2h','locationCellEnablePoint',
                     (FID,'actor'),(FID,'ref'),'gridX','gridY',),

        MelLString('FULL','full'),
        MelKeywords(),
        MelFid('PNAM','parentLocation',),
        MelFid('NAM1','music',),
        MelFid('FNAM','unreportedCrimeFaction',),
        MelFid('MNAM','worldLocationMarkerRef',),
        MelOptStruct('RNAM','f','worldLocationRadius',),
        MelFid('NAM0','horseMarkerRef',),
        MelColorN(),
    )
    __slots__ = melSet.getSlotsUsed()

# Verified for 305
#------------------------------------------------------------------------------
class MreLgtm(MelRecord):
    """Lgtm Item"""
    classType = 'LGTM'

    class MelLgtmDalc(MelStruct):
        """Handle older truncated DALC for LGTM subrecord."""
        def loadData(self, record, ins, sub_type, size_, readId):
            if size_ == 32:
                MelStruct.loadData(self, record, ins, sub_type, size_, readId)
                return
            elif size_ == 24:
                unpacked = ins.unpack('=4B4B4B4B4B4B', size_, readId)
            else:
                raise ModSizeError(record.inName, readId, 32, size_, True)
            unpacked += self.defaults[len(unpacked):]
            setter = record.__setattr__
            for attr,value,action in zip(self.attrs,unpacked,self.actions):
                if callable(action): value = action(value)
                setter(attr,value)
            if self._debug: print unpacked

    melSet = MelSet(
        MelString('EDID','eid'),
        # 92 Bytes
        # WindhelmLightingTemplate [LGTM:0007BA87] unknown1 only 24 Bytes
        MelStruct('DATA','3Bs3Bs3Bs2f2i3f32s3Bs3f4s',
            'redLigh','greenLigh','blueLigh','unknownLigh',
            'redDirect','greenDirect','blueDirect','unknownDirect',
            'redFog','greenFog','blueFog','unknownFog',
            'fogNear','fogFar','dirRotXY','dirRotZ',
            'directionalFade','fogClipDist','fogPower',
            ('unknownData',null4+null4+null4+null4+null4+null4+null4+null4),
            'redFogFar','greenFogFar','blueFogFar','unknownFogFar',
            'fogMax','lightFaceStart','lightFadeEnd',
            ('unknownData2',null4),
            ),
        MelLgtmDalc('DALC','=4B4B4B4B4B4B4Bf',
            'redXplus','greenXplus','blueXplus','unknownXplus', # 'X+'
            'redXminus','greenXminus','blueXminus','unknownXminus', # 'X-'
            'redYplus','greenYplus','blueYplus','unknownYplus', # 'Y+'
            'redYminus','greenYminus','blueYminus','unknownYminus', # 'Y-'
            'redZplus','greenZplus','blueZplus','unknownZplus', # 'Z+'
            'redZminus','greenZminus','blueZminus','unknownZminus', # 'Z-'
            'redSpec','greenSpec','blueSpec','unknownSpec', # Specular Color Values
            'fresnelPower', # Fresnel Power
            ),
        )
    __slots__ = melSet.getSlotsUsed()

# Verified for 305
#------------------------------------------------------------------------------
class MreLigh(MelRecord):
    """Light"""
    classType = 'LIGH'

    # {0x00000001} 'Dynamic',
    # {0x00000002} 'Can be Carried',
    # {0x00000004} 'Negative',
    # {0x00000008} 'Flicker',
    # {0x00000010} 'Unknown',
    # {0x00000020} 'Off By Default',
    # {0x00000040} 'Flicker Slow',
    # {0x00000080} 'Pulse',
    # {0x00000100} 'Pulse Slow',
    # {0x00000200} 'Spot Light',
    # {0x00000400} 'Shadow Spotlight',
    # {0x00000800} 'Shadow Hemisphere',
    # {0x00001000} 'Shadow Omnidirectional',
    # {0x00002000} 'Portal-strict'
    LighTypeFlags = Flags(0L,Flags.getNames(
            (0, 'dynamic'),
            (1, 'canbeCarried'),
            (2, 'negative'),
            (3, 'flicker'),
            (4, 'unknown'),
            (5, 'offByDefault'),
            (6, 'flickerSlow'),
            (7, 'pulse'),
            (8, 'pulseSlow'),
            (9, 'spotLight'),
            (10, 'shadowSpotlight'),
            (11, 'shadowHemisphere'),
            (12, 'shadowOmnidirectional'),
            (13, 'portalstrict'),
        ))

    melSet = MelSet(
        MelString('EDID','eid'),
        MelVmad(),
        MelBounds(),
        MelModel(),
        MelDestructible(),
        MelLString('FULL','full'),
        MelString('ICON','iconPath'),
        MelString('MICO','smallIconPath'),
        # fe = 'Flicker Effect'
        MelStruct('DATA','iI4BI6fIf','duration','radius','red','green','blue',
                  'unknown',(LighTypeFlags,'flags',0L),'falloffExponent','fov',
                  'nearClip','fePeriod','feIntensityAmplitude',
                  'feMovementAmplitude','value','weight',),
        MelStruct('FNAM','f','fadevalue',),
        MelFid('SNAM','sound'),
        )
    __slots__ = melSet.getSlotsUsed()

# Verified for 305
#------------------------------------------------------------------------------
class MreLscr(MelRecord):
    """Load screen."""
    classType = 'LSCR'

    melSet = MelSet(
        MelString('EDID','eid'),
        MelString('ICON','iconPath'),
        MelString('MICO','smallIconPath'),
        MelLString('DESC','description'),
        MelConditions(),
        MelFid('NNAM','loadingScreenNIF'),
        MelStruct('SNAM','f','initialScale',),
        MelStruct('RNAM','3h','rotGridY','rotGridX','rotGridZ',),
        MelStruct('ONAM','2h','rotOffsetMin','rotOffsetMax',),
        MelStruct('XNAM','3f','transGridY','transGridX','transGridZ',),
        MelString('MOD2','cameraPath'),
        )
    __slots__ = melSet.getSlotsUsed()

# Verified for 305
#------------------------------------------------------------------------------
class MreLtex(MelRecord):
    """Landscape Texture."""
    classType = 'LTEX'

    melSet = MelSet(
        MelString('EDID','eid'),
        MelFid('TNAM','textureSet',),
        MelFid('MNAM','materialType',),
        MelStruct('HNAM','BB','friction','restitution',),
        MelStruct('SNAM','B','textureSpecularExponent',),
        MelFids('GNAM','grasses'),
        )
    __slots__ = melSet.getSlotsUsed()

# Verified for 305
#------------------------------------------------------------------------------
class MreLeveledList(MreLeveledListBase):
    """Skyrim Leveled item/creature/spell list."""

    class MelLevListLvlo(MelGroups):
        def __init__(self):
            MelGroups.__init__(self,'entries',
                MelStruct('LVLO','=HHIHH','level',('unknown1',null2),
                          (FID,'listId',None),('count',1),('unknown2',null2)),
                MelCoed(),
                )
        def dumpData(self,record,out):
            out.packSub('LLCT','B',len(record.entries))
            MelGroups.dumpData(self,record,out)

    __slots__ = []

# Verified Correct for Skyrim 1.8
#------------------------------------------------------------------------------
class MreLvli(MreLeveledList):
    classType = 'LVLI'
    copyAttrs = ('chanceNone','glob',)

    melSet = MelSet(
        MelString('EDID','eid'),
        MelBounds(),
        MelStruct('LVLD','B','chanceNone'),
        MelStruct('LVLF','B',(MreLeveledListBase._flags,'flags',0L)),
        MelOptStruct('LVLG','I',(FID,'glob')),
        MelNull('LLCT'),
        MreLeveledList.MelLevListLvlo(),
        )
    __slots__ = melSet.getSlotsUsed()

# Verified for 305
#------------------------------------------------------------------------------
class MreLvln(MreLeveledList):
    classType = 'LVLN'
    copyAttrs = ('chanceNone','model','modt_p',)

    melSet = MelSet(
        MelString('EDID','eid'),
        MelBounds(),
        MelStruct('LVLD','B','chanceNone'),
        MelStruct('LVLF','B',(MreLeveledListBase._flags,'flags',0L)),
        MelOptStruct('LVLG','I',(FID,'glob')),
        MelNull('LLCT'),
        MreLeveledList.MelLevListLvlo(),
        MelString('MODL','model'),
        MelBase('MODT','modt_p'),
        )
    __slots__ = melSet.getSlotsUsed()

# Verified for 305
#------------------------------------------------------------------------------
class MreLvsp(MreLeveledList):
    classType = 'LVSP'
    copyAttrs = ('chanceNone',)

    melSet = MelSet(
        MelString('EDID','eid'),
        MelBounds(),
        MelStruct('LVLD','B','chanceNone'),
        MelStruct('LVLF','B',(MreLeveledListBase._flags,'flags',0L)),
        MelNull('LLCT'),
        MreLeveledList.MelLevListLvlo(),
        )
    __slots__ = melSet.getSlotsUsed()

# Verified for 305
#------------------------------------------------------------------------------
class MreMato(MelRecord):
    """Material Object Records"""
    classType = 'MATO'

    MatoTypeFlags = Flags(0L,Flags.getNames(
            (0, 'singlePass'),
        ))

    class MelMatoData(MelStruct):
        """Handle older truncated DATA for MATO subrecord."""
        def loadData(self, record, ins, sub_type, size_, readId):
            if size_ == 48:
                MelStruct.loadData(self, record, ins, sub_type, size_, readId)
                return
            elif size_ == 28:
                unpacked = ins.unpack('fffffff', size_, readId)
            else:
                raise ModSizeError(record.inName, readId, 48, size_, True)
            unpacked += self.defaults[len(unpacked):]
            setter = record.__setattr__
            for attr,value,action in zip(self.attrs,unpacked,self.actions):
                if callable(action): value = action(value)
                setter(attr,value)
            if self._debug: print unpacked

    melSet = MelSet(
        MelString('EDID','eid'),
        MelModel(),
        MelGroups('wordsOfPower',
            MelBase('DNAM','propertyData',),
            ),
        MelMatoData('DATA','11fI','falloffScale','falloffBias','noiseUVScale',
                  'materialUVScale','projectionVectorX','projectionVectorY',
                  'projectionVectorZ','normalDampener',
                  'singlePassColor','singlePassColor',
                  'singlePassColor',(MatoTypeFlags,'flags',0L),),
        )
    __slots__ = melSet.getSlotsUsed()

# Verified for 305
#------------------------------------------------------------------------------
class MreMatt(MelRecord):
    """Material Type Record."""
    classType = 'MATT'

    MattTypeFlags = Flags(0L,Flags.getNames(
            (0, 'stairMaterial'),
            (1, 'arrowsStick'),
        ))

    melSet = MelSet(
        MelString('EDID','eid'),
        MelFid('PNAM', 'materialParent',),
        MelString('MNAM','materialName'),
        MelStruct('CNAM','3f','red','green','blue',),
        MelStruct('BNAM','f','buoyancy',),
        MelStruct('FNAM','I',(MattTypeFlags,'flags',0L),),
        MelFid('HNAM', 'havokImpactDataSet',),
    )
    __slots__ = melSet.getSlotsUsed()

# Verified for 305
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
        MelLString('DESC','description'),
        MelLString('FULL','full'),
        # 'INAM' leftover
        MelFid('INAM','iconUnused'),
        MelFid('QNAM','materialParent'),
        MelStruct('DNAM','I',(MesgTypeFlags,'flags',0L),),
        # Don't Show
        MelStruct('TNAM','I','displayTime',),
        MelGroups('menuButtons',
            MelLString('ITXT','buttonText'),
            MelConditions(),
            ),
    )
    __slots__ = melSet.getSlotsUsed()

# Verified for 305
#------------------------------------------------------------------------------
class MreMgef(MelRecord):
    """Mgef Item"""
    classType = 'MGEF'

    # MGEF has many wbEnum in TES5Edit
    # 'magicSkill', 'resistValue', 'mgefArchtype',
    # 'actorValue', 'castingType', 'delivery', 'secondActorValue'
    # 'castingSoundLevel', 'soundType'
    # refer to TES5Edit for values

    MgefGeneralFlags = Flags(0L,Flags.getNames(
            (0, 'hostile'),
            (1, 'recover'),
            (2, 'detrimental'),
            (3, 'snaptoNavmesh'),
            (4, 'noHitEvent'),
            (5, 'unknown6'),
            (6, 'unknown7'),
            (7, 'unknown8'),
            (8, 'dispellwithKeywords'),
            (9, 'noDuration'),
            (10, 'noMagnitude'),
            (11, 'noArea'),
            (12, 'fXPersist'),
            (13, 'unknown14'),
            (14, 'goryVisuals'),
            (15, 'hideinUI'),
            (16, 'unknown17'),
            (17, 'noRecast'),
            (18, 'unknown19'),
            (19, 'unknown20'),
            (20, 'unknown21'),
            (21, 'powerAffectsMagnitude'),
            (22, 'powerAffectsDuration'),
            (23, 'unknown24'),
            (24, 'unknown25'),
            (25, 'unknown26'),
            (26, 'painless'),
            (27, 'noHitEffect'),
            (28, 'noDeathDispel'),
            (29, 'unknown30'),
            (30, 'unknown31'),
            (31, 'unknown32'),
    ))

    melSet = MelSet(
        MelString('EDID','eid'),
        MelVmad(),
        MelLString('FULL','full'),
        MelFid('MDOB','harvestIngredient'),
        MelKeywords(),
        MelStruct('DATA','IfIiiH2sIfIIIIffffIiIIIIiIIIfIfI4s4sIIIIff',
            (MgefGeneralFlags,'flags',0L),'baseCost',(FID,'assocItem'),
            'magicSkill','resistValue',
            # 'counterEffectCount' is a count of ESCE records
            'counterEffectCount',
            ('unknown1',null2),(FID,'castingLight'),'taperWeight',(FID,'hitShader'),
            (FID,'enchantShader'),'minimumSkillLevel','spellmakingArea',
            'spellmakingCastingTime','taperCurve','taperDuration',
            'secondAvWeight','mgefArchtype','actorValue',(FID,'projectile'),
            (FID,'explosion'),'castingType','delivery','secondActorValue',
            (FID,'castingArt'),(FID,'hitEffectArt'),(FID,'impactData'),
            'skillUsageMultiplier',(FID,'dualCastingArt'),'dualCastingScale',
            (FID,'enchantArt'),('unknown2',null4),('unknown3',null4),(FID,'equipAbility'),
            (FID,'imageSpaceModifier'),(FID,'perkToApply'),'castingSoundLevel',
            'scriptEffectAiScore','scriptEffectAiDelayTime',),
        MelFids('ESCE','counterEffects'),
        MelStructA('SNDD','2I','sounds','soundType',(FID,'sound')),
        MelLString('DNAM','magicItemDescription'),
        MelConditions(),
        )
    __slots__ = melSet.getSlotsUsed()

    def dumpData(self,out):
        counterEffects = self.counterEffects
        self.counterEffectCount = len(counterEffects) if counterEffects else 0
        MelRecord.dumpData(self,out)

# Verified for 305
#------------------------------------------------------------------------------
class MreMisc(MelRecord):
    """Misc. Item"""
    classType = 'MISC'
    melSet = MelSet(
        MelString('EDID','eid'),
        MelVmad(),
        MelBounds(),
        MelLString('FULL','full'),
        MelModel(),
        MelString('ICON','iconPath'),
        MelString('MICO','smallIconPath'),
        MelDestructible(),
        MelOptStruct('YNAM','I',(FID,'pickupSound')),
        MelOptStruct('ZNAM','I',(FID,'dropSound')),
        MelKeywords(),
        MelStruct('DATA','=If','value','weight'),
        )
    __slots__ = melSet.getSlotsUsed()

# Verified for 305
#------------------------------------------------------------------------------
class MreMovt(MelRecord):
    """Movt Item"""
    classType = 'MOVT'
    class MelMovtSped(MelStruct):
        """Handle older truncated SPED for MOVT subrecord."""
        def loadData(self, record, ins, sub_type, size_, readId):
            if size_ == 44:
                MelStruct.loadData(self, record, ins, sub_type, size_, readId)
                return
            elif size_ == 40:
                unpacked = ins.unpack('10f', size_, readId)
            else:
                raise ModSizeError(record.inName, readId, 44, size_, True)
            unpacked += self.defaults[len(unpacked):]
            setter = record.__setattr__
            for attr,value,action in zip(self.attrs,unpacked,self.actions):
                if callable(action): value = action(value)
                setter(attr,value)
            if self._debug: print unpacked

    melSet = MelSet(
        MelString('EDID','eid'),
        MelString('MNAM','mnam_n'),
        MelMovtSped('SPED','11f','leftWalk','leftRun','rightWalk','rightRun',
                  'forwardWalk','forwardRun','backWalk','backRun',
                  'rotateInPlaceWalk','rotateInPlaceRun',
                  'rotateWhileMovingRun'),
        MelOptStruct('INAM','3f','directional','movementSpeed','rotationSpeed'),
        )
    __slots__ = melSet.getSlotsUsed()

# Verified for 305
#------------------------------------------------------------------------------
class MreMstt(MelRecord):
    """Moveable static record."""
    classType = 'MSTT'

    MsttTypeFlags = Flags(0L,Flags.getNames(
        (0, 'onLocalMap'),
        (1, 'unknown2'),
    ))

    melSet = MelSet(
        MelString('EDID','eid'),
        MelBounds(),
        MelLString('FULL','full'),
        MelModel(),
        MelDestructible(),
        MelStruct('DATA','B',(MsttTypeFlags,'flags',0L),),
        MelFid('SNAM','sound'),
    )
    __slots__ = melSet.getSlotsUsed()

# Verified for 305
#------------------------------------------------------------------------------
class MreMusc(MelRecord):
    """Music type record."""
    classType = 'MUSC'

    MuscTypeFlags = Flags(0L,Flags.getNames(
            (0,'playsOneSelection'),
            (1,'abruptTransition'),
            (2,'cycleTracks'),
            (3,'maintainTrackOrder'),
            (4,'unknown5'),
            (5,'ducksCurrentTrack'),
        ))

    melSet = MelSet(
        MelString('EDID','eid'),
        MelStruct('FNAM','I',(MuscTypeFlags,'flags',0L),),
        # Divided by 100 in TES5Edit, probably for editing only
        MelStruct('PNAM','2H','priority','duckingDB'),
        MelStruct('WNAM','f','fadeDuration'),
        MelFidList('TNAM','musicTracks'),
        )
    __slots__ = melSet.getSlotsUsed()

# Verified for 305
#------------------------------------------------------------------------------
class MreMust(MelRecord):
    """Music Track"""
    classType = 'MUST'

    # CNAM has wbEnum in TES5Edit
    # Assigned to 'trackType' for WB
    # Int64($23F678C3) :'Palette',
    # Int64($6ED7E048) :'Single Track',
    # Int64($A1A9C4D5) :'Silent Track'

    melSet = MelSet(
        MelString('EDID','eid'),
        MelStruct('CNAM','I','trackType'),
        MelOptStruct('FLTV','f','duration'),
        MelOptStruct('DNAM','I','fadeOut'),
        MelString('ANAM','trackFilename'),
        MelString('BNAM','finaleFilename'),
        MelStructA('FNAM','f','points',('cuePoints',0.0)),
        MelOptStruct('LNAM','2fI','loopBegins','loopEnds','loopCount',),
        MelStruct('CITC','I','conditionCount'),
        MelConditions(),
        MelFidList('SNAM','tracks',),
        )
    __slots__ = melSet.getSlotsUsed()

    def dumpData(self,out):
        conditions = self.conditions
        self.conditionCount = len(conditions) if conditions else 0
        MelRecord.dumpData(self,out)

# Verified for 305
#------------------------------------------------------------------------------
class MreNavi(MelRecord):
    """Navigation Mesh Info Map"""
    classType = 'NAVI'

    melSet = MelSet(
        MelString('EDID','eid'),
        MelStruct('NVER','I','version'),
        # NVMI and NVPP would need special routines to handle them
        # If no mitigation is needed, then leave it as MelBase
        MelBase('NVMI','navigationMapInfos',),
        MelBase('NVPP','preferredPathing',),
        MelFidList('NVSI','navigationMesh'),
        )
    __slots__ = melSet.getSlotsUsed()

# Verified for 305, Not Mergable - FormIDs unaccounted for
#------------------------------------------------------------------------------
class MreNavm(MelRecord):
    """Navigation Mesh"""
    classType = 'NAVM'

    # 'Edge 0-1 link',
    # 'Edge 1-2 link',
    # 'Edge 2-0 link',
    # 'Unknown 4',
    # 'Unknown 5',
    # 'Unknown 6',
    # 'Preferred',
    # 'Unknown 8',
    # 'Unknown 9',
    # 'Water',
    # 'Door',
    # 'Found',
    # 'Unknown 13',
    # 'Unknown 14',
    # 'Unknown 15',
    # 'Unknown 16'
    NavmTrianglesFlags = Flags(0L,Flags.getNames(
            (0, 'edge01link'),
            (1, 'edge12link'),
            (2, 'edge20link'),
            (3, 'unknown4'),
            (4, 'unknown5'),
            (5, 'unknown6'),
            (6, 'preferred'),
            (7, 'unknown8'),
            (8, 'unknown9'),
            (9, 'water'),
            (10, 'door'),
            (11, 'found'),
            (12, 'unknown13'),
            (13, 'unknown14'),
            (14, 'unknown15'),
            (15, 'unknown16'),
        ))

    # 'Edge 0-1 wall',
    # 'Edge 0-1 ledge cover',
    # 'Unknown 3',
    # 'Unknown 4',
    # 'Edge 0-1 left',
    # 'Edge 0-1 right',
    # 'Edge 1-2 wall',
    # 'Edge 1-2 ledge cover',
    # 'Unknown 9',
    # 'Unknown 10',
    # 'Edge 1-2 left',
    # 'Edge 1-2 right',
    # 'Unknown 13',
    # 'Unknown 14',
    # 'Unknown 15',
    # 'Unknown 16'
    NavmCoverFlags = Flags(0L,Flags.getNames(
            (0, 'edge01wall'),
            (1, 'edge01ledgecover'),
            (2, 'unknown3'),
            (3, 'unknown4'),
            (4, 'edge01left'),
            (5, 'edge01right'),
            (6, 'edge12wall'),
            (7, 'edge12ledgecover'),
            (8, 'unknown9'),
            (9, 'unknown10'),
            (10, 'edge12left'),
            (11, 'edge12right'),
            (12, 'unknown13'),
            (13, 'unknown14'),
            (14, 'unknown15'),
            (15, 'unknown16'),
        ))

    melSet = MelSet(
        MelString('EDID','eid'),
        # NVNM, ONAM, PNAM, NNAM would need special routines to handle them
        # If no mitigation is needed, then leave it as MelBase
        MelBase('NVNM','navMeshGeometry'),
        MelBase('ONAM','onam_p'),
        MelBase('PNAM','pnam_p'),
        MelBase('NNAM','nnam_p'),
        )
    __slots__ = melSet.getSlotsUsed()

# Verified for 305, Not Mergable - FormIDs unaccounted for
#------------------------------------------------------------------------------
class MelNpcCnto(MelGroups):
    def __init__(self):
        MelGroups.__init__(self,'items',
            MelStruct('CNTO','=Ii',(FID,'item',None),'count'),
            MelCoed(),
            )

    def dumpData(self,record,out):
        # Only write the COCT/CNTO/COED subrecords if count > 0
        out.packSub('COCT','I',len(record.items))
        MelGroups.dumpData(self,record,out)

class MreNpc(MelRecord):
    """Npc"""
    classType = 'NPC_'

    # {0x0001} 'Use Traits',
    # {0x0002} 'Use Stats',
    # {0x0004} 'Use Factions',
    # {0x0008} 'Use Spell List',
    # {0x0010} 'Use AI Data',
    # {0x0020} 'Use AI Packages',
    # {0x0040} 'Use Model/Animation?',
    # {0x0080} 'Use Base Data',
    # {0x0100} 'Use Inventory',
    # {0x0200} 'Use Script',
    # {0x0400} 'Use Def Pack List',
    # {0x0800} 'Use Attack Data',
    # {0x1000} 'Use Keywords'
    NpcFlags2 = Flags(0L,Flags.getNames(
            (0, 'useTraits'),
            (1, 'useStats'),
            (2, 'useFactions'),
            (3, 'useSpellList'),
            (4, 'useAIData'),
            (5, 'useAIPackages'),
            (6, 'useModelAnimation?'),
            (7, 'useBaseData'),
            (8, 'useInventory'),
            (9, 'useScript'),
            (10, 'useDefPackList'),
            (11, 'useAttackData'),
            (12, 'useKeywords'),
        ))

    # {0x00000001} 'Female',
    # {0x00000002} 'Essential',
    # {0x00000004} 'Is CharGen Face Preset',
    # {0x00000008} 'Respawn',
    # {0x00000010} 'Auto-calc stats',
    # {0x00000020} 'Unique',
    # {0x00000040} 'Doesn''t affect stealth meter',
    # {0x00000080} 'PC Level Mult',
    # {0x00000100} 'Use Template?',
    # {0x00000200} 'Unknown 9',
    # {0x00000400} 'Unknown 10',
    # {0x00000800} 'Protected',
    # {0x00001000} 'Unknown 12',
    # {0x00002000} 'Unknown 13',
    # {0x00004000} 'Summonable',
    # {0x00008000} 'Unknown 15',
    # {0x00010000} 'Doesn''t bleed',
    # {0x00020000} 'Unknown 17',
    # {0x00040000} 'Bleedout Override',
    # {0x00080000} 'Opposite Gender Anims',
    # {0x00100000} 'Simple Actor',
    # {0x00200000} 'looped script?',
    # {0x00400000} 'Unknown 22',
    # {0x00800000} 'Unknown 23',
    # {0x01000000} 'Unknown 24',
    # {0x02000000} 'Unknown 25',
    # {0x04000000} 'Unknown 26',
    # {0x08000000} 'Unknown 27',
    # {0x10000000} 'looped audio?',
    # {0x20000000} 'Is Ghost',
    # {0x40000000} 'Unknown 30',
    # {0x80000000} 'Invulnerable'
    NpcFlags1 = Flags(0L,Flags.getNames(
            (0, 'female'),
            (1, 'essential'),
            (2, 'isCharGenFacePreset'),
            (3, 'respawn'),
            (4, 'autoCalc'),
            (5, 'unique'),
            (6, 'doesNotAffectStealth'),
            (7, 'pcLevelMult'),
            (8, 'useTemplate?'),
            (9, 'unknown9'),
            (10, 'unknown10'),
            (11, 'protected'),
            (12, 'unknown12'),
            (13, 'unknown13'),
            (14, 'summonable'),
            (15, 'unknown15'),
            (16, 'doesNotBleed'),
            (17, 'unknown17'),
            (18, 'bleedoutOverride'),
            (19, 'oppositeGenderAnims'),
            (20, 'simpleActor'),
            (21, 'loopedscript?'),
            (22, 'unknown22'),
            (23, 'unknown23'),
            (24, 'unknown24'),
            (25, 'unknown25'),
            (26, 'unknown26'),
            (27, 'unknown27'),
            (28, 'loopedaudio?'),
            (29, 'isGhost'),
            (30, 'unknown30'),
            (31, 'invulnerable'),
        ))

    melSet = MelSet(
        MelString('EDID', 'eid'),
        MelVmad(),
        MelBounds(),
        MelStruct('ACBS','IHHhHHHhHHH',
                  (NpcFlags1,'flags',0L),'magickaOffset',
                  'staminaOffset','level','calcMin',
                  'calcMax','speedMultiplier','dispotionBase',
                  (NpcFlags2,'npcFlags2',0L),'healthOffset','bleedoutOverride',
                  ),
        MelStructs('SNAM','IB3s','factions',(FID, 'faction'), 'rank', 'snamUnused'),
        MelOptStruct('INAM', 'I', (FID, 'deathItem')),
        MelOptStruct('VTCK', 'I', (FID, 'voice')),
        MelOptStruct('TPLT', 'I', (FID, 'template')),
        MelFid('RNAM','race'),
        MelCountedFids('SPLO', 'spells', 'SPCT'),
        MelDestructible(),
        MelOptStruct('WNAM','I',(FID, 'wormArmor')),
        MelOptStruct('ANAM','I',(FID, 'farawaymodel')),
        MelOptStruct('ATKR','I',(FID, 'attackRace')),
        MelGroups('attacks',
            MelAttackData(),
            MelString('ATKE', 'attackEvents')
        ),
        MelOptStruct('SPOR', 'I', (FID, 'spectator')),
        MelOptStruct('OCOR', 'I', (FID, 'observe')),
        MelOptStruct('GWOR', 'I', (FID, 'guardWarn')),
        MelOptStruct('ECOR', 'I', (FID, 'combat')),
        MelOptStruct('PRKZ','I','perkCount'),
        MelGroups('perks',
            MelOptStruct('PRKR','IB3s',(FID, 'perk'),'rank','prkrUnused'),
            ),
        MelNull('COCT'),
        MelNpcCnto(),
        MelStruct('AIDT', 'BBBBBBBBIII', 'aggression', 'confidence',
                  'engergy', 'responsibility', 'mood', 'assistance',
                  'aggroRadiusBehavior',
                  'aidtUnknown', 'warn', 'warnAttack', 'attack'),
        MelFids('PKID', 'packages',),
        MelKeywords(),
        MelFid('CNAM', 'class'),
        MelLString('FULL','full'),
        MelLString('SHRT', 'shortName'),
        MelBase('DATA', 'marker'),
        MelStruct('DNAM','36BHHH2sfB3s',
            'oneHandedSV','twoHandedSV','marksmanSV','blockSV','smithingSV',
            'heavyArmorSV','lightArmorSV','pickpocketSV','lockpickingSV',
            'sneakSV','alchemySV','speechcraftSV','alterationSV','conjurationSV',
            'destructionSV','illusionSV','restorationSV','enchantingSV',
            'oneHandedSO','twoHandedSO','marksmanSO','blockSO','smithingSO',
            'heavyArmorSO','lightArmorSO','pickpocketSO','lockpickingSO',
            'sneakSO','alchemySO','speechcraftSO','alterationSO','conjurationSO',
            'destructionSO','illusionSO','restorationSO','enchantingSO',
            'health','magicka','stamina',('dnamUnused1',null2),
            'farawaymodeldistance','gearedupweapons',('dnamUnused2',null3)),
        MelFids('PNAM', 'head_part_addons',),
        MelOptStruct('HCLF', '<I', (FID, 'hair_color')),
        MelOptStruct('ZNAM', '<I', (FID, 'combat_style')),
        MelOptStruct('GNAM', '<I', (FID, 'gifts')),
        MelBase('NAM5', 'nam5_p'),
        MelStruct('NAM6', '<f', 'height'),
        MelStruct('NAM7', '<f', 'weight'),
        MelStruct('NAM8', '<I', 'sound_level'),
        MelGroups('event_sound',
            MelStruct('CSDT', '<I', 'sound_type'),
            MelGroups('sound',
                MelStruct('CSDI', '<I', (FID, 'sound')),
                MelStruct('CSDC', '<B', 'chance')
                )
            ),
        MelOptStruct('CSCR', '<I', (FID, 'audio_template')),
        MelOptStruct('DOFT', '<I', (FID, 'default_outfit')),
        MelOptStruct('SOFT', '<I', (FID, 'sleep_outfit')),
        MelOptStruct('DPLT', '<I', (FID, 'default_package')),
        MelOptStruct('CRIF', '<I', (FID, 'crime_faction')),
        MelOptStruct('FTST', '<I', (FID, 'face_texture')),
        MelOptStruct('QNAM', '<fff', 'skin_tone_r' ,'skin_tone_g', 'skin_tone_b'),
        MelOptStruct('NAM9', '<fffffffffffffffffff', 'nose_long', 'nose_up',
                     'jaw_up', 'jaw_wide', 'jaw_forward', 'cheeks_up', 'cheeks_back',
                     'eyes_up', 'eyes_out', 'brows_up', 'brows_out', 'brows_forward',
                     'lips_up', 'lips_out', 'chin_wide', 'chin_down', 'chin_underbite',
                     'eyes_back', 'nam9_unused'),
        MelOptStruct('NAMA', '<IiII', 'nose', 'unknown', 'eyes', 'mouth'),
        MelGroups('face_tint_layer',
            MelStruct('TINI', '<H', 'tint_item'),
            MelStruct('TINC', '<4B', 'tintRed', 'tintGreen', 'tintBlue' ,'tintAlpha'),
            MelStruct('TINV', '<i', 'tint_value'),
            MelStruct('TIAS', '<h', 'preset'),
            ),
        )
    __slots__ = melSet.getSlotsUsed()

    def dumpData(self,out):
        perks = self.perks
        self.perkCount = len(perks) if perks else 0
        MelRecord.dumpData(self,out)

# Verified for 305
#------------------------------------------------------------------------------
class MreOtft(MelRecord):
    """Otft Item"""
    classType = 'OTFT'
    melSet = MelSet(
        MelString('EDID','eid'),
        MelFidList('INAM','items'),
        )
    __slots__ = melSet.getSlotsUsed()

# Verified for 305
#------------------------------------------------------------------------------
# Marker for organization please don't remove ---------------------------------
# PACK ------------------------------------------------------------------------
class MrePack(MelRecord):
    """Package"""
    classType = 'PACK'

    PackFlags10 = Flags(0L,Flags.getNames(
            (0, 'successCompletesPackage'),
        ))

    # 'Repeat when Complete',
    # 'Unknown 1'
    PackFlags9 = Flags(0L,Flags.getNames(
            (0, 'repeatwhenComplete'),
            (1, 'unknown1'),
        ))

    # wbPKDTFlags
    PackFlags1 = Flags(0L,Flags.getNames(
            (0, 'offersServices'),
            (1, 'unknown2'),
            (2, 'mustcomplete'),
            (3, 'maintainSpeedatGoal'),
            (4, 'unknown5'),
            (5, 'unknown6'),
            (6, 'unlockdoorsatpackagestart'),
            (7, 'unlockdoorsatpackageend'),
            (8, 'unknown9'),
            (9, 'continueifPCNear'),
            (10, 'onceperday'),
            (11, 'unknown12'),
            (12, 'unknown13'),
            (13, 'preferredSpeed'),
            (14, 'unknown15'),
            (15, 'unknown16'),
            (16, 'unknown17'),
            (17, 'alwaysSneak'),
            (18, 'allowSwimming'),
            (19, 'unknown20'),
            (20, 'ignoreCombat'),
            (21, 'weaponsUnequipped'),
            (22, 'unknown23'),
            (23, 'weaponDrawn'),
            (24, 'unknown25'),
            (25, 'unknown26'),
            (26, 'unknown27'),
            (27, 'noCombatAlert'),
            (28, 'unknown29'),
            (29, 'wearSleepOutfitunused'),
            (30, 'unknown31'),
            (31, 'unknown32'),
        ))

    # wbPKDTInterruptFlags
    PackFlags2 = Flags(0L,Flags.getNames(
            (0, 'hellostoplayer'),
            (1, 'randomconversations'),
            (2, 'observecombatbehavior'),
            (3, 'greetcorpsebehavior'),
            (4, 'reactiontoplayeractions'),
            (5, 'friendlyfirecomments'),
            (6, 'aggroRadiusBehavior'),
            (7, 'allowIdleChatter'),
            (8, 'unknown9'),
            (9, 'worldInteractions'),
            (10, 'unknown11'),
            (11, 'unknown12'),
            (12, 'unknown13'),
            (13, 'unknown14'),
            (14, 'unknown15'),
            (15, 'unknown16'),
        ))

    # UNAM, Data Inputs Flags
    PackFlags3 = Flags(0L,Flags.getNames(
            (0, 'public'),
        ))

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
                unpacked = ins.unpack('iIi', size_, readId)
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
            for subType in ('POBA','POEA','POCA'):
                loaders[subType] = self
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
            # 'SCHR','SCDA','SCTX','SLSD','SCVR','SCRV','SCRO',
            # All older Script records chould be discarded if found
            for subtype in ('INAM','TNAM'):
                self.melSet.loaders[subtype] = element
            element.loadData(self, record, ins, sub_type, size_, readId)

    #--MelSet
    melSet = MelSet(
        MelString('EDID','eid'),
        MelVmad(),
        MelStruct('PKDT','I3BsH2s',(PackFlags1,'generalFlags',0L),'type','interruptOverride',
                  'preferredSpeed','unknown',(PackFlags2,'interruptFlags',0L),'unknown',),
        MelStruct('PSDT','2bB2b3si','month','dayofweek','date','hour','minute',
                  'unused','durationminutes',),
        MelConditions(),
        MelGroup('idleAnimations',
            MelStruct('IDLF','I','type'),
            MelStruct('IDLC','B3s','count','unknown',),
            MelStruct('IDLT','f','timerSetting',),
            MelFidList('IDLA','animation'),
            MelBase('IDLB','unknown'),
        ),
        # End 'idleAnimations'
        MelFid('CNAM','combatStyle',),
        MelFid('QNAM','ownerQuest',),
        MelStruct('PKCU','3I','dataInputCount',(FID,'packageTemplate'),
                  'versionCount',),
        MelGroup('packageData',
            MelGroups('inputValues',
                MelString('ANAM','type'),
                # CNAM Needs Union Decider, No FormID
                MelBase('CNAM','unknown',),
                MelBase('BNAM','unknown',),
                # PDTO Needs Union Decider
                MelStructs('PDTO','2I','topicData','type',(FID,'data'),),
                # PLDT Needs Union Decider, No FormID
                MelStruct('PLDT','iIi','locationType','locationValue','radius',),
                # PTDA Needs Union Decider
                MelStruct('PTDA','iIi','targetDataType',(FID,'targetDataTarget'),
                          'targetDataCountDist',),
                MelBase('TPIC','unknown',),
                ),
                # End 'inputValues'
            MelGroups('dataInputs',
                MelStruct('UNAM','b','index'),
                MelString('BNAM','name',),
                MelStruct('PNAM','I',(PackFlags1,'flags',0L),),
                ),
                # End 'dataInputs' - wbUNAMs
        ),
        # End 'packageData'
        MelBase('XNAM','marker',),

        )
    __slots__ = melSet.getSlotsUsed()

# Needs Updating
#------------------------------------------------------------------------------
class MrePerk(MelRecord):
    """Perk Item"""
    classType = 'PERK'

    # EPFT has wbEnum in TES5Edit
    # Assigned to 'functionParameterType' for WB
    # {0} 'None',
    # {1} 'Float',
    # {2} 'Float/AV,Float',
    # {3} 'LVLI',
    # {4} 'SPEL,lstring,flags',
    # {5} 'SPEL',
    # {6} 'string',
    # {7} 'lstring'

    # DATA below PRKE needs union decider
    # 3B definition has two wbEnum in TES5Edit
    # Refer to wbEntryPointsEnum for 'entryPoint'
    # 'function' is defined as follows
    # {0} 'Unknown 0',
    # {1} 'Set Value',  // EPFT=1
    # {2} 'Add Value', // EPFT=1
    # {3} 'Multiply Value', // EPFT=1
    # {4} 'Add Range To Value', // EPFT=2
    # {5} 'Add Actor Value Mult', // EPFT=2
    # {6} 'Absolute Value', // no params
    # {7} 'Negative Absolute Value', // no params
    # {8} 'Add Leveled List', // EPFT=3
    # {9} 'Add Activate Choice', // EPFT=4
    # {10} 'Select Spell', // EPFT=5
    # {11} 'Select Text', // EPFT=6
    # {12} 'Set to Actor Value Mult', // EPFT=2
    # {13} 'Multiply Actor Value Mult', // EPFT=2
    # {14} 'Multiply 1 + Actor Value Mult', // EPFT=2
    # {15} 'Set Text' // EPFT=7

    # PRKE has wbEnum in TES5Edit
    # Assigned to 'effectType' for WB
    # 'Quest + Stage',
    # 'Ability',
    # 'Entry Point'

    # 'Run Immediately',
    # 'Replace Default'
    PerkScriptFlagsFlags = Flags(0L,Flags.getNames(
            (0, 'runImmediately'),
            (1, 'replaceDefault'),
        ))

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
            for attr,value,action in zip(self.attrs,unpacked,self.actions):
                if callable(action): value = action(value)
                setter(attr,value)
            if self._debug: print unpacked, record.flagsA.getTrueAttrs()

    class MelPerkEffectData(MelBase):
        def hasFids(self,formElements):
            formElements.add(self)
        def loadData(self, record, ins, sub_type, size_, readId):
            target = MelObject()
            record.__setattr__(self.attr,target)
            if record.type == 0:
                format,attrs = ('II',('quest','queststage'))
            elif record.type == 1:
                format,attrs = ('I',('ability',))
            elif record.type == 2:
                format,attrs = ('HB',('entrypoint','function'))
            else:
                raise ModError(ins.inName,_('Unexpected type: %d') % record.type)
            unpacked = ins.unpack(format, size_, readId)
            setter = target.__setattr__
            for attr,value in zip(attrs,unpacked):
                setter(attr,value)
            if self._debug: print unpacked
        def dumpData(self,record,out):
            target = record.__getattribute__(self.attr)
            if not target: return
            if record.type == 0:
                format,attrs = ('II',('quest','queststage'))
            elif record.type == 1:
                format,attrs = ('I',('ability',))
            elif record.type == 2:
                format,attrs = ('HB',('entrypoint','function'))
            else:
                raise ModError(record.inName, # untested
                               _('Unexpected type: %d') % record.type)
            values = []
            valuesAppend = values.append
            getter = target.__getattribute__
            for attr in attrs:
                value = getter(attr)
                valuesAppend(value)
            try:
                out.packSub(self.subType,format,*values)
            except struct.error:
                print self.subType,format,values
                raise
        def mapFids(self,record,function,save=False):
            target = record.__getattribute__(self.attr)
            if not target: return
            if record.type == 0:
                result = function(target.quest)
                if save: target.quest = result
            elif record.type == 1:
                result = function(target.ability)
                if save: target.ability = result

    class MelPerkEffects(MelGroups):
        def __init__(self,attr,*elements):
            MelGroups.__init__(self,attr,*elements)
        def setMelSet(self,melSet):
            self.melSet = melSet
            self.attrLoaders = {}
            for element in melSet.elements:
                attr = element.__dict__.get('attr',None)
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
            if sub_type in ('EPFT', 'EPF2', 'EPF3', 'EPFD'):
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
        def dumpData(self,record,out):
            for target in record.__getattribute__(self.attr):
                element = self.loaders[target.recordType]
                if not element:
                    raise ModError(record.inName, _(
                        'Unexpected type: %d') % target.recordType)
                element.dumpData(target,out)

    melSet = MelSet(
        MelString('EDID','eid'),
        MelVmad(),
        MelLString('FULL','full'),
        MelLString('DESC','description'),
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
                MelStruct('EPFT','B','_epft'),
                MelString('EPF2','buttonLabel'),
                MelStruct('EPF3','H','scriptFlag'),
                MelBase('EPFD', 'floats'), # [Float] or [Float,Float], todo rewrite specific class
            ),
            MelBase('PRKF','footer'),
            ),
        )
    melSet.elements[-1].setMelSet(melSet)
    __slots__ = melSet.getSlotsUsed()

# Needs Verification
#------------------------------------------------------------------------------
class MreProj(MelRecord):
    """Projectile record."""
    classType = 'PROJ'

    # VNAM has wbEnum in TES5Edit
    # Assigned to 'soundLevel' for WB
    # 0 :'Loud',
    # 1 :'Normal',
    # 2 :'Silent',
    # 3 :'Very Loud'

    # DATA has wbEnum in TES5Edit
    # Assigned to 'projectileTypes' for WB
    # $01 :'Missile',
    # $02 :'Lobber',
    # $04 :'Beam',
    # $08 :'Flame',
    # $10 :'Cone',
    # $20 :'Barrier',
    # $40 :'Arrow'

    ProjTypeFlags = Flags(0L,Flags.getNames(
        (0, 'hitscan'),
        (1, 'explosive'),
        (2, 'altTriger'),
        (3, 'muzzleFlash'),
        (4, 'unknown4'),
        (5, 'canbeDisable'),
        (6, 'canbePickedUp'),
        (7, 'superSonic'),
        (8, 'pinsLimbs'),
        (9, 'passThroughSmallTransparent'),
        (10, 'disableCombatAimCorrection'),
        (11, 'rotation'),
    ))

    class MelProjData(MelStruct):
        """Handle older truncated DATA for PROJ subrecord."""
        def loadData(self, record, ins, sub_type, size_, readId):
            if size_ == 92:
                MelStruct.loadData(self, record, ins, sub_type, size_, readId)
                return
            elif size_ == 88:
                unpacked = ins.unpack('2H3f2I3f2I3f3I4fI', size_, readId)
            elif size_ == 84:
                unpacked = ins.unpack('2H3f2I3f2I3f3I4f', size_, readId)
            else:
                raise ModSizeError(record.inName, readId, 92, size_, True)
            unpacked += self.defaults[len(unpacked):]
            setter = record.__setattr__
            for attr,value,action in zip(self.attrs,unpacked,self.actions):
                if callable(action): value = action(value)
                setter(attr,value)
            if self._debug: print unpacked

    melSet = MelSet(
        MelString('EDID','eid'),
        MelBounds(),
        MelLString('FULL','full'),
        MelModel(),
        MelDestructible(),
        MelProjData('DATA','2H3f2I3f2I3f3I4f2I',(ProjTypeFlags,'flags',0L),'projectileTypes',
                  ('gravity',0.00000),('speed',10000.00000),('range',10000.00000),
                  (FID,'light',0),(FID,'muzzleFlash',0),('tracerChance',0.00000),
                  ('explosionAltTrigerProximity',0.00000),('explosionAltTrigerTimer',0.00000),
                  (FID,'explosion',0),(FID,'sound',0),('muzzleFlashDuration',0.00000),
                  ('fadeDuration',0.00000),('impactForce',0.00000),
                  (FID,'soundCountDown',0),(FID,'soundDisable',0),(FID,'defaultWeaponSource',0),
                  ('coneSpread',0.00000),('collisionRadius',0.00000),('lifetime',0.00000),
                  ('relaunchInterval',0.00000),(FID,'decalData',0),(FID,'collisionLayer',0),
                  ),
        MelGroup('models',
            MelString('NAM1','muzzleFlashPath'),
            # Ignore texture hashes - they're only an optimization, plenty of
            # records in Skyrim.esm are missing them
            MelNull('NAM2'),
        ),
        MelStruct('VNAM','I','soundLevel',),
        )
    __slots__ = melSet.getSlotsUsed()

# Verified for 305
#------------------------------------------------------------------------------
class MelItems(MelGroups):
    """Handle writing out a preceding COCT subrecord for count of CNTO/COED subrecords."""
    NullLoader = MelNull('ANY')
    def __init__(self, attr='items'):
        MelGroups.__init__(self,attr,
            MelStruct('CNTO','=Ii',(FID,'item',None),'count'),
            MelCoed(),
            )

    def getLoaders(self, loaders):
        MelGroups.getLoaders(self,loaders)
        loaders['COCT'] = MelItems.NullLoader

    def dumpData(self,record,out):
        value = record.__getattribute__(self.attr)
        # Only write the COCT/CNTO/COED subrecords if count > 0
        if value:
            out.packSub('COCT','<I',len(value))
            MelGroups.dumpData(self,record,out)

class MreQust(MelRecord):
    """Quest"""
    classType = 'QUST'
    _questFlags = Flags(0,Flags.getNames(
        (0,'startGameEnabled'),
        (2,'wildernessEncounter'),
        (3,'allowRepeatedStages'),
        (8,'runOnce'),
        (9,'excludeFromDialogueExport'),
        (10,'warnOnAliasFillFailure'),
    ))
    _stageFlags = Flags(0,Flags.getNames(
        (0,'unknown0'),
        (1,'startUpStage'),
        (2,'startDownStage'),
        (3,'keepInstanceDataFromHereOn'),
    ))
    stageEntryFlags = Flags(0,Flags.getNames('complete','fail'))
    objectiveFlags = Flags(0,Flags.getNames('oredWithPrevious'))
    targetFlags = Flags(0,Flags.getNames('ignoresLocks'))
    aliasFlags = Flags(0,Flags.getNames(
        (0,'reservesLocationReference'),
        (1,'optional'),
        (2,'questObject'),
        (3,'allowReuseInQuest'),
        (4,'allowDead'),
        (5,'inLoadedArea'),
        (6,'essential'),
        (7,'allowDisabled'),
        (8,'storesText'),
        (9,'allowReserved'),
        (10,'protected'),
        (11,'noFillType'),
        (12,'allowDestroyed'),
        (13,'closest'),
        (14,'usesStoredText'),
        (15,'initiallyDisabled'),
        (16,'allowCleared'),
        (17,'clearsNameWhenRemoved'),
    ))

    #--Condition loader
    class MelQuestLoaders(DataDict):
        """Since CTDA/CIS1/CIS2 and FNAM subrecords occur in two different places,
        we need to replace ordinary 'loaders' dictionary with a 'dictionary' that will
        return the correct element to handle the CTDA/CIS1/CIS2/FNAM subrecord. 'Correct'
        element is determined by which other subrecords have been encountered."""
        def __init__(self,loaders,
                     dialogueConditions,
                     eventConditions,
                     stages,
                     objectives,
                     aliases,
                     description,
                     targets
            ):
            self.data = loaders
            self.type_conditions = {
                'EDID':dialogueConditions,
                'NEXT':eventConditions,
                'INDX':stages,
                'QOBJ':objectives,
                'ALID':aliases,
                'ALED':targets,
            }
            self.conditions = dialogueConditions
            self.type_fnam = {
                'EDID':objectives,
                'ANAM':aliases,
            }
            self.fnam = objectives
            self.type_nnam = {
                'EDID':objectives,
                'ANAM':description,
            }
            self.nnam = objectives
            self.type_targets = {
                'EDID':objectives,
                'ANAM':targets,
            }
            self.targets = objectives
        def __getitem__(self,key):
            if key in ('CTDA','CIS1','CIS2'): return self.conditions
            if key == 'FNAM': return self.fnam
            if key == 'NNAM': return self.nnam
            if key == 'QSTA': return self.targets
            self.conditions = self.type_conditions.get(key, self.conditions)
            self.fnam = self.type_fnam.get(key, self.fnam)
            self.nnam = self.type_nnam.get(key, self.nnam)
            self.targets = self.type_targets.get(key, self.targets)
            return self.data[key]

    class MelAliasGroups(MelGroups):
        def loadData(self, record, ins, sub_type, size_, readId):
            """Reads data from ins into record attribute."""
            if sub_type in ('ALST', 'ALLS'):
                target = self.getDefault()
                record.__getattribute__(self.attr).append(target)
            else:
                target = record.__getattribute__(self.attr)[-1]
            target.__slots__ = [s for element in self.elements for s in
                                element.getSlotsUsed()]
            self.loaders[sub_type].loadData(target, ins, sub_type, size_,
                                            readId)

    melSet = MelSet(
        MelString('EDID','eid'),
        MelVmad(),
        MelLString('FULL','full'),
        MelStruct('DNAM','=H2BiI',(_questFlags,'questFlags',0L),'priority','formVersion','unknown','questType'),
        MelOptStruct('ENAM','4s',('event',None)),
        MelFids('QTGL','textDisplayGlobals'),
        MelString('FLTR','objectWindowFilter'),
        MelConditions('dialogueConditions'),
        MelBase('NEXT','marker'),
        MelConditions('eventConditions'),
        MelGroups('stages',
            MelStruct('INDX','hBb','index',(_stageFlags,'flags',0L),'unknown'),
            MelGroups('logEntries',
                MelStruct('QSDT','B',(stageEntryFlags,'stageFlags',0L)),
                MelConditions(),
                MelLString('CNAM','text'),
                MelFid('NAM0', 'nextQuest'),
                MelGroup('unused',
                    MelBase('SCHR','schr_p'),
                    MelBase('SCDA','scda_p'),
                    MelBase('SCTX','sctx_p'),
                    MelBase('QNAM','qnam_p'),
                    MelBase('SCRO','scro_p'),
                    ),
                ),
            ),
        MelGroups('objectives',
            MelStruct('QOBJ','h','index'),
            MelStruct('FNAM','I',(objectiveFlags,'flags',0L)),
            MelLString('NNAM','description'),
            MelGroups('targets',
                MelStruct('QSTA','iB3s','alias',(targetFlags,'flags'),('unused1',null3)),
                MelConditions(),
                ),
            ),
        MelBase('ANAM','aliasMarker'),
        MelAliasGroups('aliases',
            MelOptStruct('ALST','I',('aliasId',None)),
            MelOptStruct('ALLS','I',('aliasIdLocation',None)),
            MelString('ALID', 'aliasName'),
            MelStruct('FNAM','I',(aliasFlags,'flags',0L)),
            MelOptStruct('ALFI','i',('forcedIntoAlias',None)),
            MelFid('ALFL','specificLocation'),
            MelFid('ALFR','forcedReference'),
            MelFid('ALUA','uniqueActor'),
            MelGroup('locationAliasReference',
                MelStruct('ALFA','I','alias'),
                MelFid('KNAM','keyword'),
                MelFid('ALRT','referenceType'),
                ),
            MelGroup('externalAliasReference',
                MelFid('ALEQ','quest'),
                MelStruct('ALEA','I','alias'),
                ),
            MelGroup('createReferenceToObject',
                MelFid('ALCO','object'),
                MelStruct('ALCA','I','createAt'),
                MelStruct('ALCL','I','createLevel'),
                ),
            MelGroup('findMatchingReferenceNearAlias',
                MelStruct('ALNA','I','alias'),
                MelStruct('ALNT','I','type'),
                ),
            MelGroup('findMatchingReferenceFromEvent',
                MelStruct('ALFE','4s',('fromEvent',null4)),
                MelStruct('ALFD','4s',('eventData',null4)),
                ),
            MelConditions(),
            MelKeywords(),
            MelItems(),
            MelFid('SPOR','spectatorOverridePackageList'),
            MelFid('OCOR','observeDeadBodyOverridePackageList'),
            MelFid('GWOR','guardWarnOverridePackageList'),
            MelFid('ECOR','combatOverridePackageList'),
            MelFid('ALDN','displayName'),
            MelFids('ALSP','aliasSpells'),
            MelFids('ALFC','aliasFactions'),
            MelFids('ALPC','aliasPackageData'),
            MelFid('VTCK','voiceType'),
            MelBase('ALED','aliasEnd'),
            ),
        MelLString('NNAM','description'),
        MelGroups('targets',
            MelStruct('QSTA','iB3s','alias',(targetFlags,'flags'),('unused1',null3)),
            MelConditions(),
            ),
        )
    melSet.loaders = MelQuestLoaders(melSet.loaders,
                                     melSet.elements[7],  # dialogueConditions
                                     melSet.elements[9],  # eventConditions
                                     melSet.elements[10], # stages
                                     melSet.elements[11], # objectives
                                     melSet.elements[13], # aliases
                                     melSet.elements[14], # description
                                     melSet.elements[15], # targets
        )
    __slots__ = melSet.getSlotsUsed()

# Needs testing should be mergable
#------------------------------------------------------------------------------
# Marker for organization please don't remove ---------------------------------
# RACE ------------------------------------------------------------------------
class MreRace(MelRecord):
    """Race"""
    classType = 'RACE'

    melSet = MelSet(
        MelString('EDID','eid'),
        MelLString('FULL','full'),
        )
    __slots__ = melSet.getSlotsUsed()

# Needs Updating
#------------------------------------------------------------------------------
class MreRefr(MelRecord):
    """Placed Object"""
    classType = 'REFR'
    _flags = Flags(0L,Flags.getNames('visible', 'canTravelTo','showAllHidden',))
    _parentFlags = Flags(0L,Flags.getNames('oppositeParent','popIn',))
    _actFlags = Flags(0L,Flags.getNames('useDefault', 'activate','open','openByDefault'))
    _lockFlags = Flags(0L,Flags.getNames(None, None, 'leveledLock'))
    _destinationFlags = Flags(0L,Flags.getNames('noAlarm'))
    _parentActivate = Flags(0L,Flags.getNames('parentActivateOnly'))
    reflectFlags = Flags(0L,Flags.getNames('reflection', 'refraction'))
    roomDataFlags = Flags(0L,Flags.getNames(
        (6,'hasImageSpace'),
        (7,'hasLightingTemplate'),
    ))

    class MelRefrXloc(MelOptStruct):
        """Handle older truncated XLOC for REFR subrecord."""
        def loadData(self, record, ins, sub_type, size_, readId):
            if size_ == 20:
                MelStruct.loadData(self, record, ins, sub_type, size_, readId)
                return
            elif size_ == 16:
                unpacked = ins.unpack('B3sIB3s4s', size_, readId)
            elif size_ == 12:
                unpacked = ins.unpack('B3sIB3s', size_, readId)
            else:
                raise ModSizeError(record.inName, readId, 20, size_, True)
            #     print ins.unpack(('%dB' % size),size)
            #     raise ModError(ins.inName,_('Unexpected size encountered for REFR:XLOC subrecord: ')+str(size))
            # unpacked = unpacked[:-2] + self.defaults[len(unpacked)-2:-2] + unpacked[-2:]
            # setter = record.__setattr__
            # for attr,value,action in zip(self.attrs,unpacked,self.actions):
            #     if callable(action): value = action(value)
            #     setter(attr,value)
            # if self._debug: print unpacked
            unpacked += self.defaults[len(unpacked):]
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
            while sub_type_ in ['FNAM', 'FULL', 'TNAM', ]: # 'WMI1'
                if sub_type_ == 'FNAM':
                    value = insUnpack('B', size_, readId)
                    record.flags = MreRefr._flags(*value)
                elif sub_type_ == 'FULL':
                    record.full = ins.readString(size_, readId)
                elif sub_type_ == 'TNAM':
                    record.markerType, record.unused5 = insUnpack('Bs', size_, readId)
                # elif type == 'WMI1':
                #     record.reputation = insUnpack('I',size,readId)
                pos = insTell()
                (sub_type_, size_) = insUnpack('4sH', 6, readId + '.FULL')
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
                    # out.packRef('WMI1',record.reputation)
                except struct.error:
                    print self.subType,self.format,record.flags,record.full,record.markerType
                    raise

    melSet = MelSet(
        MelString('EDID','eid'),
        MelVmad(),
        MelFid('NAME','base'),

        # {--- Bound Contents ---}
        # {--- Bound Data ---}
        MelOptStruct('XMBO','3f','boundHalfExtentsX','boundHalfExtentsY','boundHalfExtentsZ'),

        # {--- Primitive ---}
        MelOptStruct('XPRM','fffffffI','primitiveBoundX','primitiveBoundY','primitiveBoundZ',
                     'primitiveColorRed','primitiveColorGreen','primitiveColorBlue',
                     'primitiveUnknown','primitiveType'),
        MelBase('XORD','xord_p'),
        MelOptStruct('XOCP','9f','occlusionPlaneWidth','occlusionPlaneHeight',
                     'occlusionPlanePosX','occlusionPlanePosY','occlusionPlanePosZ',
                     'occlusionPlaneRot1','occlusionPlaneRot2','occlusionPlaneRot3',
                     'occlusionPlaneRot4'),
        MelStructA('XPOD','II','portalData',(FID,'portalOrigin'),(FID,'portalDestination')),
        MelOptStruct('XPTL','9f','portalWidth','portalHeight','portalPosX','portalPosY','portalPosZ',
                     'portalRot1','portalRot2','portalRot3','portalRot4'),

        MelGroup('roomData',
            MelStruct('XRMR','BB2s','linkedRoomsCount',(roomDataFlags,'roomFlags'),'unknown'),
            MelFid('LNAM', 'lightingTemplate'),
            MelFid('INAM', 'imageSpace'),
            MelFids('XLRM','linkedRoom'),
            ),
        MelBase('XMBP','multiboundPrimitiveMarker'),

        MelBase('XRGD','ragdollData'),
        MelBase('XRGB','ragdollBipedData'),
        MelOptStruct('XRDS','f','radius'),

        # {--- Reflected By / Refracted By ---}
        MelStructs('XPWR','II','reflectedByWaters',(FID,'reference'),(reflectFlags,'type',),),

        # {--- Lit Water ---}
        MelFids('XLTW','litWaters'),

        # {--- Emittance ---}
        MelOptStruct('XEMI','I',(FID,'emittance')),
        MelOptStruct('XLIG','ff4sf4s','fov90Delta','fadeDelta','unknown','shadowDepthBias','unknown',),
        MelOptStruct('XALP','BB','cutoffAlpha','baseAlpha',),

        # {--- Teleport ---}
        MelOptStruct('XTEL','I6fI',(FID,'destinationFid'),'destinationPosX',
                     'destinationPosY','destinationPosZ','destinationRotX',
                     'destinationRotY','destinationRotZ',
                     (_destinationFlags,'destinationFlags')),
        MelFids('XTNM','teleportMessageBox'),

        # {--- MultiBound ---}
        MelFid('XMBR','multiboundReference'),

        MelBase('XWCN', 'xwcn_p',),
        MelBase('XWCS', 'xwcs_p',),
        MelOptStruct('XWCU','3f4s3f4s','offsetX','offsetY','offsetZ','unknown',
                     'angleX','angleY','angleZ','unknown'),
        MelOptStruct('XCVL','4sf4s','unknown','angleX','unknown',),
        MelFid('XCZR','unknownRef'),
        MelBase('XCZA', 'xcza_p',),
        MelFid('XCZC','unknownRef2'),
        MelOptStruct('XSCL','f',('scale',1.0)),
        MelFid('XSPC','spawnContainer'),

        # {--- Activate Parents ---}
        MelGroup('activateParents',
            MelStruct('XAPD','B',(_parentActivate,'flags',None),),
            MelStructs('XAPR','If','activateParentRefs',(FID,'reference'),'delay')
            ),

        MelFid('XLIB','leveledItemBaseObject'),
        MelStruct('XLCM','i','levelModifier'),
        MelFid('XLCN','persistentLocation',),
        MelOptStruct('XTRI','I','collisionLayer'),

        # {--- Lock ---}
        # {>>Lock Tab for REFR when 'Locked' is Unchecked this record is not present <<<}
        MelRefrXloc('XLOC','B3sIB3s8s','lockLevel',('unused1',null3),
                    (FID,'lockKey'),(_lockFlags,'lockFlags'),('unused3',null3),
                    ('unused4',null4+null4)),
        MelFid('XEZN','encounterZone'),

        # {--- Generated Data ---}
        MelOptStruct('XNDP','IH2s',(FID,'navMesh'),'teleportMarkerTriangle','unknown'),
        MelFidList('XLRT','locationRefType',),
        MelNull('XIS2',),

        # {--- Ownership ---}
        MelOwnership(),
        MelOptStruct('XCNT','i','count'),
        MelOptStruct('XCHG','f',('charge',None)),
        MelFid('XLRL','locationReference'),
        MelOptStruct('XESP','IB3s',(FID,'parent'),(_parentFlags,'parentFlags'),('unused6',null3)),
        MelStructs('XLKR','II','linkedReference',(FID,'keywordRef'),(FID,'linkedRef')),
        MelGroup('patrolData',
            MelStruct('XPRD','f','idleTime'),
            MelBase('XPPA','patrolScriptMarker'),
            MelFid('INAM', 'idle'),
            MelBase('SCHR','schr_p',),
            MelBase('SCTX','sctx_p',),
            MelStructs('PDTO','2I','topicData','type',(FID,'data'),),
            ),

        # {--- Flags ---}
        MelOptStruct('XACT','I',(_actFlags,'actFlags',0L)),
        MelOptStruct('XHTW','f','headTrackingWeight',),
        MelOptStruct('XFVC','f','favorCost',),
        MelBase('ONAM','onam_p'),

        # {--- Map Data ---}
        MelGroup('markerData',
            MelNull('XMRK',),
            MelOptStruct('FNAM','B','mapFlags',),
            MelString('FULL','full'),
            MelOptStruct('TNAM','Bs','markerType','unknown',),
            ),

        # {--- Attach reference ---}
        MelFid('XATR', 'attachRef'),
        MelOptStruct('XLOD','3f',('lod1',None),('lod2',None),('lod3',None)),
        MelOptStruct('DATA','=6f',('posX',None),('posY',None),('posZ',None),
                     ('rotX',None),('rotY',None),('rotZ',None)),
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
            elif record.entryType == 7 and self.subType == 'RDSA':
                MelStructA.loadData(self, record, ins, sub_type, size_, readId)

        def dumpData(self,record,out):
            """Conditionally dumps data."""
            if record.entryType == 2 and self.subType == 'RDOT':
                MelStructA.dumpData(self,record,out)
            elif record.entryType == 3 and self.subType == 'RDWT':
                MelStructA.dumpData(self,record,out)
            elif record.entryType == 6 and self.subType == 'RDGS':
                MelStructA.dumpData(self,record,out)
            elif record.entryType == 7 and self.subType == 'RDSA':
                MelStructA.dumpData(self,record,out)

    class MelRegnString(MelString):
        """Handler for regn record. Conditionally dumps next items."""
        def loadData(self, record, ins, sub_type, size_, readId):
            if record.entryType == 4 and self.subType == 'RDMP':
                MelString.loadData(self, record, ins, sub_type, size_, readId)
            # elif record.entryType == 5 and self.subType == 'ICON':
            #     MelString.loadData(self,record,ins,type,size,readId)

        def dumpData(self,record,out):
            """Conditionally dumps data."""
            if record.entryType == 4 and self.subType == 'RDMP':
                MelString.dumpData(self,record,out)
            # elif record.entryType == 5 and self.subType == 'ICON':
            #     MelString.dumpData(self,record,out)

    class MelRegnGroups(MelGroups):
        def loadData(self, record, ins, sub_type, size_, readId):
            """Reads data from ins into record attribute."""
            if sub_type == self.type0:
                target = self.getDefault()
                record.__getattribute__(self.attr).append(target)
            else:
                targets = record.__getattribute__(self.attr)
                if targets:
                    target = targets[-1]
                # BPNN for NVVoidBodyPartData, NVraven02
                # What does this do?
                elif sub_type == 'RDSA':
                    target = self.getDefault()
                    record.__getattribute__(self.attr).append(target)
            target.__slots__ = [s for element in self.elements for s in
                                element.getSlotsUsed()]
            self.loaders[sub_type].loadData(target, ins, sub_type, size_,
                                            readId)

    melSet = MelSet(
        MelString('EDID','eid'),
        MelStruct('RCLR','3Bs','mapRed','mapBlue','mapGreen',('unused1',null1)),
        MelFid('WNAM','worldspace'),
        MelGroups('areas',
            MelStruct('RPLI','I','edgeFalloff'),
            MelStructA('RPLD','2f','points','posX','posY')),
        MelRegnGroups('entries',
            MelStruct('RDAT', 'I2B2s','entryType', (rdatFlags,'flags'), 'priority',
                     ('unused1',null2)),
            MelString('ICON','iconPath'),
            # Dont Show RDMO and RDSA when entryType is <> 7
            MelFid('RDMO','music'),
            MelRegnStructA('RDSA', '2If', 'sounds', (FID, 'sound'), (sdflags, 'flags'), 'chance'),
            # Dont Show RDMP is <> 4
            MelRegnString('RDMP', 'mapName'),
            # Dont Show RDOT is <> 2
            MelRegnStructA('RDOT', 'IH2sfBBBBH4sffffHHH2s4s', 'objects',
                          (FID,'objectId'),
                           'parentIndex',('unused1',null2), 'density', 'clustering',
                           'minSlope', 'maxSlope',(obflags, 'flags'), 'radiusWRTParent',
                           'radius', ('unk1',null4),'maxHeight', 'sink', 'sinkVar',
                           'sizeVar', 'angleVarX','angleVarY',  'angleVarZ',
                           ('unused2',null2), ('unk2',null4)),
            # Dont Show RDGS is <> 6
            MelRegnStructA('RDGS', 'I4s', 'grass', ('unknown',null4)),
            # Dont Show RDWT is <> 3
            MelRegnStructA('RDWT', '3I', 'weather', (FID, 'weather', None), 'chance', (FID, 'global', None)),
        ),
        )
    __slots__ = melSet.getSlotsUsed()
#------------------------------------------------------------------------------
class MreRela(MelRecord):
    """Relationship"""
    classType = 'RELA'

    # DATA has wbEnum in TES5Edit
    # Assigned to 'rankType' for WB
    # 0 :'Lover'
    # 1 :'Ally'
    # 2 :'Confidant'
    # 3 :'Friend'
    # 4 :'Acquaitance'
    # 5 :'Rival'
    # 6 :'Foe'
    # 7 :'Enemy'
    # 8 :'Archnemesis'

    RelationshipFlags = Flags(0L,Flags.getNames(
        (0,'Unknown 1'),
        (1,'Unknown 2'),
        (2,'Unknown 3'),
        (3,'Unknown 4'),
        (4,'Unknown 5'),
        (5,'Unknown 6'),
        (6,'Unknown 7'),
        (7,'Secret'),
    ))

    melSet = MelSet(
        MelString('EDID','eid'),
        MelStruct('DATA','2IHsBI',(FID,'parent'),(FID,'child'),'rankType',
                  'unknown',(RelationshipFlags,'relaFlags',0L),(FID,'associationType'),),
        )
    __slots__ = melSet.getSlotsUsed()

# Verified for 305
#------------------------------------------------------------------------------
class MreRevb(MelRecord):
    """Reverb Parameters"""
    classType = 'REVB'

    melSet = MelSet(
        MelString('EDID','eid'),
        MelStruct('DATA','2H4b6B','decayTimeMS','hfReferenceHZ','roomFilter',
                  'hfRoomFilter','reflections','reverbAmp','decayHFRatio',
                  'reflectDelayMS','reverbDelayMS','diffusion','density',
                  'unknown',),
        )
    __slots__ = melSet.getSlotsUsed()

# Verified for 305
#------------------------------------------------------------------------------
class MreRfct(MelRecord):
    """Rfct Item"""
    classType = 'RFCT'

    # {0x00000001}'Rotate to Face Target',
    # {0x00000002}'Attach to Camera',
    # {0x00000004}'Inherit Rotation'
    RfctTypeFlags = Flags(0L,Flags.getNames(
        (0, 'rotateToFaceTarget'),
        (1, 'attachToCamera'),
        (2, 'inheritRotation'),
    ))

    melSet = MelSet(
        MelString('EDID','eid'),
        MelStruct('DATA','3I',(FID,'impactSet'),(FID,'impactSet'),(RfctTypeFlags,'flags',0L),),
        )
    __slots__ = melSet.getSlotsUsed()

# Verified for 305
#------------------------------------------------------------------------------
class MreScen(MelRecord):
    """Scene"""
    classType = 'SCEN'

    # {0x00000001} 'Unknown 1',
    # {0x00000002} 'Unknown 2',
    # {0x00000004} 'Unknown 3',
    # {0x00000008} 'Unknown 4',
    # {0x00000010} 'Unknown 5',
    # {0x00000020} 'Unknown 6',
    # {0x00000040} 'Unknown 7',
    # {0x00000080} 'Unknown 8',
    # {0x00000100} 'Unknown 9',
    # {0x00000200} 'Unknown 10',
    # {0x00000400} 'Unknown 11',
    # {0x00000800} 'Unknown 12',
    # {0x00001000} 'Unknown 13',
    # {0x00002000} 'Unknown 14',
    # {0x00003000} 'Unknown 15',
    # {0x00004000} 'Face Target',
    # {0x00010000} 'Looping',
    # {0x00020000} 'Headtrack Player'
    ScenFlags5 = Flags(0L,Flags.getNames(
            (0, 'unknown1'),
            (1, 'unknown2'),
            (2, 'unknown3'),
            (3, 'unknown4'),
            (4, 'unknown5'),
            (5, 'unknown6'),
            (6, 'unknown7'),
            (7, 'unknown8'),
            (8, 'unknown9'),
            (9, 'unknown10'),
            (10, 'unknown11'),
            (11, 'unknown12'),
            (12, 'unknown13'),
            (13, 'unknown14'),
            (14, 'unknown15'),
            (15, 'faceTarget'),
            (16, 'looping'),
            (17, 'headtrackPlayer'),
        ))

    # ANAM has wbEnum in TES5Edit
    # Assigned to 'actionType' for WB
    # 0 :'dialogue'
    # 1 :'package'
    # 2 :'timer'

    # DEMO has wbEnum in TES5Edit
    # Assigned to 'emotionType' for WB
    # 0 :'Neutral',
    # 1 :'Anger',
    # 2 :'Disgust',
    # 3 :'Fear',
    # 4 :'Sad',
    # 5 :'Happy',
    # 6 :'Surprise',
    # 7 :'Puzzled'

    # 'Death Pause (unsused)',
    # 'Death End',
    # 'Combat Pause',
    # 'Combat End',
    # 'Dialogue Pause',
    # 'Dialogue End',
    # 'OBS_COM Pause',
    # 'OBS_COM End'
    ScenFlags3 = Flags(0L,Flags.getNames(
            (0, 'deathPauseunsused'),
            (1, 'deathEnd'),
            (2, 'combatPause'),
            (3, 'combatEnd'),
            (4, 'dialoguePause'),
            (5, 'dialogueEnd'),
            (6, 'oBS_COMPause'),
            (7, 'oBS_COMEnd'),
        ))

    # 'No Player Activation',
    # 'Optional'
    ScenFlags2 = Flags(0L,Flags.getNames(
            (0, 'noPlayerActivation'),
            (1, 'optional'),
        ))

    # 'Begin on Quest Start',
    # 'Stop on Quest End',
    # 'Unknown 3',
    # 'Repeat Conditions While True',
    # 'Interruptible'
    ScenFlags1 = Flags(0L,Flags.getNames(
            (0, 'beginonQuestStart'),
            (1, 'stoponQuestEnd'),
            (2, 'unknown3'),
            (3, 'repeatConditionsWhileTrue'),
            (4, 'interruptible'),
        ))

    melSet = MelSet(
        MelString('EDID','eid'),
        MelVmad(),
        MelStruct('FNAM','I',(ScenFlags1,'flags',0L),),
        MelGroups('phases',
            MelNull('HNAM'),
            MelString('NAM0','name',),
            MelGroup('startConditions',
                MelConditions(),
                ),
            MelNull('NEXT'),
            MelGroup('completionConditions',
                MelConditions(),
                ),
            # BEGIN leftover from earlier CK versions
            MelGroup('unused',
                MelBase('SCHR','schr_p'),
                MelBase('SCDA','scda_p'),
                MelBase('SCTX','sctx_p'),
                MelBase('QNAM','qnam_p'),
                MelBase('SCRO','scro_p'),
                ),
            MelNull('NEXT'),
            MelGroup('unused',
                MelBase('SCHR','schr_p'),
                MelBase('SCDA','scda_p'),
                MelBase('SCTX','sctx_p'),
                MelBase('QNAM','qnam_p'),
                MelBase('SCRO','scro_p'),
                ),
            # End leftover from earlier CK versions
        MelStruct('WNAM','I','editorWidth',),
        # Marker Phase End
        MelNull('HNAM'),
        ),

        MelGroups('actors',
            MelStruct('ALID','I','actorID',),
            MelStruct('LNAM','I',(ScenFlags2,'scenFlags2',0L),),
            MelStruct('DNAM','I',(ScenFlags3,'flags3',0L),),
            ),
        MelGroups('actions',
            MelStruct('ANAM','H','actionType'),
            MelString('NAM0','name',),
            MelStruct('ALID','I','actorID',),
            MelBase('LNAM','lnam_p',),
            MelStruct('INAM','I','index',),
            MelStruct('FNAM','I',(ScenFlags5,'flags',0L),),
            MelStruct('SNAM','I','startPhase',),
            MelStruct('ENAM','I','endPhase',),
            MelStruct('SNAM','f','timerSeconds',),
            MelFids('PNAM','packages'),
            MelFid('DATA','topic'),
            MelStruct('HTID','I','headtrackActorID',),
            MelStruct('DMAX','f','loopingMax',),
            MelStruct('DMIN','f','loopingMin',),
            MelStruct('DEMO','I','emotionType',),
            MelStruct('DEVA','I','emotionValue',),
            # BEGIN leftover from earlier CK versions
            MelGroup('unused',
                MelBase('SCHR','schr_p'),
                MelBase('SCDA','scda_p'),
                MelBase('SCTX','sctx_p'),
                MelBase('QNAM','qnam_p'),
                MelBase('SCRO','scro_p'),
                ),
            # End leftover from earlier CK versions
            MelNull('ANAM'),
        ),
        # BEGIN leftover from earlier CK versions
        MelGroup('unused',
            MelBase('SCHR','schr_p'),
            MelBase('SCDA','scda_p'),
            MelBase('SCTX','sctx_p'),
            MelBase('QNAM','qnam_p'),
            MelBase('SCRO','scro_p'),
            ),
        MelNull('NEXT'),
        MelGroup('unused',
            MelBase('SCHR','schr_p'),
            MelBase('SCDA','scda_p'),
            MelBase('SCTX','sctx_p'),
            MelBase('QNAM','qnam_p'),
            MelBase('SCRO','scro_p'),
            ),
        # End leftover from earlier CK versions

        MelFid('PNAM','quest',),
        MelStruct('INAM','I','lastActionIndex'),
        MelBase('VNAM','vnam_p'),
        MelConditions(),
        )
    __slots__ = melSet.getSlotsUsed()

# Verified Correct for Skyrim 1.8
#------------------------------------------------------------------------------
class MreScrl(MelRecord,MreHasEffects):
    """Scroll record."""
    classType = 'SCRL'

    # SPIT has several wbEnum refer to wbSPIT in TES5Edit

    ScrollDataFlags = Flags(0L,Flags.getNames(
        (0,'manualCostCalc'),
        (1,'unknown2'),
        (2,'unknown3'),
        (3,'unknown4'),
        (4,'unknown5'),
        (5,'unknown6'),
        (6,'unknown7'),
        (7,'unknown8'),
        (8,'unknown9'),
        (9,'unknown10'),
        (10,'unknown11'),
        (11,'unknown12'),
        (12,'unknown13'),
        (13,'unknown14'),
        (14,'unknown15'),
        (15,'unknown16'),
        (16,'unknown17'),
        (17,'pcStartSpell'),
        (18,'unknown19'),
        (19,'areaEffectIgnoresLOS'),
        (20,'ignoreResistance'),
        (21,'noAbsorbReflect'),
        (22,'unknown23'),
        (23,'noDualCastModification'),
        (24,'unknown25'),
        (25,'unknown26'),
        (26,'unknown27'),
        (27,'unknown28'),
        (28,'unknown29'),
        (29,'unknown30'),
        (30,'unknown31'),
        (31,'unknown32'),
    ))

    melSet = MelSet(
        MelString('EDID','eid'),
        MelBounds(),
        MelLString('FULL','full'),
        MelKeywords(),
        MelFids('MDOB','menuDisplayObject'),
        MelFid('ETYP','equipmentType',),
        MelLString('DESC','description'),
        MelModel(),
        MelDestructible(),
        MelFid('YNAM','pickupSound',),
        MelFid('ZNAM','dropSound',),
        MelStruct('DATA','If','itemValue','itemWeight',),
        MelStruct('SPIT','IIIfIIffI','baseCost',(ScrollDataFlags,'dataFlags',0L),
                  'scrollType','chargeTime','castType','targetType',
                  'castDuration','range',(FID,'halfCostPerk'),),
        MelEffects(),
        )
    __slots__ = melSet.getSlotsUsed()

# Verified for 305
#------------------------------------------------------------------------------
class MreShou(MelRecord):
    """Shout Records"""
    classType = 'SHOU'
    melSet = MelSet(
        MelString('EDID','eid'),
        MelLString('FULL','full'),
        MelFid('MDOB','menuDisplayObject'),
        MelLString('DESC','description'),
        # Don't sort
        MelGroups('wordsOfPower',
            MelStruct('SNAM','2If',(FID,'word',None),(FID,'spell',None),'recoveryTime',),
            ),
        )
    __slots__ = melSet.getSlotsUsed()

# Verified for 305
#------------------------------------------------------------------------------
class MreSlgm(MelRecord):
    """Soul gem record."""
    classType = 'SLGM'

    # SOUL and SLCP have wbEnum in TES5Edit
    # Assigned to 'soul' and 'capacity' for WB
    # 0 :'None',
    # 1 :'Petty',
    # 2 :'Lesser',
    # 3 :'Common',
    # 4 :'Greater',
    # 5 :'Grand'

    melSet = MelSet(
        MelString('EDID','eid'),
        MelBounds(),
        MelLString('FULL','full'),
        MelModel(),
        MelString('ICON','iconPath'),
        MelString('MICO','smallIconPath'),
        MelDestructible(),
        MelFid('YNAM','pickupSound'),
        MelFid('ZNAM','dropSound'),
        MelKeywords(),
        MelStruct('DATA','If','value','weight'),
        MelStruct('SOUL','B',('soul',0),),
        MelStruct('SLCP','B',('capacity',1),),
        MelFid('NAM0','linkedTo'),
        )
    __slots__ = melSet.getSlotsUsed()

# Verified for 305
#------------------------------------------------------------------------------
class MreSmbn(MelRecord):
    """Story Manager Branch Node"""
    classType = 'SMBN'

    SmbnNodeFlags = Flags(0L,Flags.getNames(
        (0,'Random'),
        (1,'noChildWarn'),
    ))

    melSet = MelSet(
        MelString('EDID','eid'),
        MelFid('PNAM','parent',),
        MelFid('SNAM','child',),
        MelStruct('CITC','I','conditionCount'),
        MelConditions(),
        MelStruct('DNAM','I',(SmbnNodeFlags,'nodeFlags',0L),),
        MelBase('XNAM','xnam_p'),
        )
    __slots__ = melSet.getSlotsUsed()

    def dumpData(self,out):
        conditions = self.conditions
        self.conditionCount = len(conditions) if conditions else 0
        MelRecord.dumpData(self,out)

# Verified for 305
#------------------------------------------------------------------------------
class MreSmen(MelRecord):
    """Story Manager Event Node"""
    classType = 'SMEN'

    SmenNodeFlags = Flags(0L,Flags.getNames(
        (0,'Random'),
        (1,'noChildWarn'),
    ))

    # ENAM is four chars with no length byte, like AIPL, or CHRR
    melSet = MelSet(
        MelString('EDID','eid'),
        MelFid('PNAM','parent',),
        MelFid('SNAM','child',),
        MelStruct('CITC','I','conditionCount'),
        MelConditions(),
        MelStruct('DNAM','I',(SmenNodeFlags,'nodeFlags',0L),),
        MelBase('XNAM','xnam_p'),
        MelString('ENAM','type'),
        )
    __slots__ = melSet.getSlotsUsed()

    def dumpData(self,out):
        conditions = self.conditions
        self.conditionCount = len(conditions) if conditions else 0
        MelRecord.dumpData(self,out)

# Verified for 305
#------------------------------------------------------------------------------
class MreSmqn(MelRecord):
    """Story Manager Quest Node"""
    classType = 'SMQN'

    # "Do all" = "Do all before repeating"
    SmqnQuestFlags = Flags(0L,Flags.getNames(
        (0,'doAll'),
        (1,'sharesEvent'),
        (2,'numQuestsToRun'),
    ))

    SmqnNodeFlags = Flags(0L,Flags.getNames(
        (0,'Random'),
        (1,'noChildWarn'),
    ))

    melSet = MelSet(
        MelString('EDID','eid'),
        MelFid('PNAM','parent',),
        MelFid('SNAM','child',),
        MelStruct('CITC','I','conditionCount'),
        MelConditions(),
        MelStruct('DNAM','2H',(SmqnNodeFlags,'nodeFlags',0L),(SmqnQuestFlags,'questFlags',0L),),
        MelStruct('XNAM','I','maxConcurrentQuests'),
        MelOptStruct('MNAM','I',('numQuestsToRun',None)),
        MelStruct('QNAM','I','questCount'),
        MelGroups('quests',
            MelFid('NNAM','quest',),
            MelBase('FNAM','fnam_p'),
            MelOptStruct('RNAM','f',('hoursUntilReset',None)),
            )
        )
    __slots__ = melSet.getSlotsUsed()

    def dumpData(self,out):
        quests = self.quests
        self.questCount = len(quests) if quests else 0
        conditions = self.conditions
        self.conditionCount = len(conditions) if conditions else 0
        MelRecord.dumpData(self,out)

# Verified for 305
#------------------------------------------------------------------------------
class MreSnct(MelRecord):
    """Sound Category"""
    classType = 'SNCT'

    SoundCategoryFlags = Flags(0L,Flags.getNames(
        (0,'muteWhenSubmerged'),
        (1,'shouldAppearOnMenu'),
    ))

    melSet = MelSet(
        MelString('EDID','eid'),
        MelLString('FULL','full'),
        MelStruct('FNAM','I',(SoundCategoryFlags,'flags',0L),),
        MelFid('PNAM','parent',),
        MelStruct('VNAM','H','staticVolumeMultiplier'),
        MelStruct('UNAM','H','defaultMenuValue'),
        )
    __slots__ = melSet.getSlotsUsed()

# Verified for 305
#------------------------------------------------------------------------------
class MreSndr(MelRecord):
    """Sound Descriptor"""
    classType = 'SNDR'

    # LNAM has wbEnum in TES5Edit
    # Assigned to 'looping' for WB
    # $00 , 'None',
    # $08 , 'Loop',
    # $10 , 'Envelope Fast',
    # $20 , 'Envelope Slow'

    melSet = MelSet(
        MelString('EDID','eid'),
        MelBase('CNAM','cnam_p'),
        MelFid('GNAM','category',),
        MelFid('SNAM','altSoundFor',),
        MelStrings('ANAM','sounds',),
        MelFid('ONAM','outputModel',),
        MelLString('FNAM','string'),
        MelConditions(),
        MelStruct('LNAM','sBsB',('unkSndr1',null1),'looping',
                  ('unkSndr2',null1),'rumbleSendValue',),
        MelStruct('BNAM','2b2BH','pctFrequencyShift','pctFrequencyVariance','priority',
                  'dbVariance','staticAttenuation',),
        )
    __slots__ = melSet.getSlotsUsed()

# Verified for 305
#------------------------------------------------------------------------------
class MelSopmData(MelStruct):
    def __init__(self, subType='ONAM'):
        MelStruct.__init__(self, subType, '=24B',
                           'ch0_l','ch0_r','ch0_c','ch0_lFE','ch0_rL','ch0_rR','ch0_bL','ch0_bR',
                           'ch1_l','ch1_r','ch1_c','ch1_lFE','ch1_rL','ch1_rR','ch1_bL','ch1_bR',
                           'ch2_l','ch2_r','ch2_c','ch2_lFE','ch2_rL','ch2_rR','ch2_bL','ch2_bR',
                           )

class MreSopm(MelRecord):
    """Sound Output Model"""
    classType = 'SOPM'

    # MNAM has wbEnum in TES5Edit
    # Assigned to 'outputType' for WB
    # 0 :'Uses HRTF'
    # 1 :'Defined Speaker Output'

    # 'Attenuates With Distance',
    # 'Allows Rumble'
    SopmFlags = Flags(0L,Flags.getNames(
            (0, 'attenuatesWithDistance'),
            (1, 'allowsRumble'),
        ))

    melSet = MelSet(
        MelString('EDID','eid'),
        MelStruct('NAM1','B2sB',(SopmFlags,'flags',0L),'unknown1','reverbSendpct',),
        MelBase('FNAM','fnam_p'),
        MelStruct('MNAM','I','outputType',),
        MelBase('CNAM','cnam_p'),
        MelBase('SNAM','snam_p'),
        MelSopmData(),
        MelStruct('ANAM','4s2f5B','unknown2','minDistance','maxDistance',
                  'curve1','curve2','curve3','curve4','curve5',
                   dumpExtra='extraData',),
        )
    __slots__ = melSet.getSlotsUsed()

# Verified for 305
#------------------------------------------------------------------------------
class MreSoun(MelRecord):
    """Soun Item"""
    classType = 'SOUN'
    melSet = MelSet(
        MelString('EDID','eid'),
        MelBounds(),
        # FNAM Leftover, Unused
        MelString('FNAM','soundFileUnused'),
        # SNDD Leftover, Unused
        MelBase('SNDD','soundDataUnused'),
        MelFid('SDSC','soundDescriptor'),
        )
    __slots__ = melSet.getSlotsUsed()

# Verified for 305
#------------------------------------------------------------------------------
class MreSpel(MelRecord,MreHasEffects):
    """Spell record."""
    classType = 'SPEL'

    # currently not used for Skyrim needs investigated to see if TES5Edit does this
    # class SpellFlags(Flags):
    #     """For SpellFlags, immuneSilence activates bits 1 AND 3."""
    #     def __setitem__(self,index,value):
    #         setter = Flags.__setitem__
    #         setter(self,index,value)
    #         if index == 1:
    #             setter(self,3,value)

    # SPIT has several wbEnum refer to wbSPIT in TES5Edit

    # flags = SpellFlags(0L,Flags.getNames
    SpelTypeFlags = Flags(0L,Flags.getNames(
        ( 0,'manualCostCalc'),
        ( 1,'unknown2'),
        ( 2,'unknown3'),
        ( 3,'unknown4'),
        ( 4,'unknown5'),
        ( 5,'unknown6'),
        ( 6,'unknown7'),
        ( 7,'unknown8'),
        ( 8,'unknown9'),
        ( 9,'unknown10'),
        (10,'unknown11'),
        (11,'unknown12'),
        (12,'unknown13'),
        (13,'unknown14'),
        (14,'unknown15'),
        (15,'unknown16'),
        (16,'unknown17'),
        (17,'pcStartSpell'),
        (18,'unknown19'),
        (19,'areaEffectIgnoresLOS'),
        (20,'ignoreResistance'),
        (21,'noAbsorbReflect'),
        (22,'unknown23'),
        (23,'noDualCastModification'),
        (24,'unknown25'),
        (25,'unknown26'),
        (26,'unknown27'),
        (27,'unknown28'),
        (28,'unknown29'),
        (29,'unknown30'),
        (30,'unknown31'),
        (31,'unknown32'),
         ))

    melSet = MelSet(
        MelString('EDID','eid'),
        MelBounds(),
        MelLString('FULL','full'),
        MelKeywords(),
        MelFid('MDOB', 'menuDisplayObject'),
        MelFid('ETYP', 'equipmentType'),
        MelLString('DESC','description'),
        MelStruct('SPIT','IIIfIIffI','cost',(SpelTypeFlags,'dataFlags',0L),
                  'scrollType','chargeTime','castType','targetType',
                  'castDuration','range',(FID,'halfCostPerk'),),
        MelEffects(),
        )
    __slots__ = melSet.getSlotsUsed()

# Verified for 305
#------------------------------------------------------------------------------
class MelSpgdData(MelStruct):
    SpgdDataFlags = Flags(0L, Flags.getNames(
        (0, 'rain'),
        (1, 'snow'),
    ))

    def __init__(self, subType='DATA'):
        MelStruct.__init__(self, subType, '=7f4If', 'gravityVelocity',
            'rotationVelocity', 'particleSizeX', 'particleSizeY',
            'centerOffsetMin', 'centerOffsetMax', 'initialRotationRange',
            'numSubtexturesX', 'numSubtexturesY',
            (MelSpgdData.SpgdDataFlags, 'typeFlags', 0L), ('boxSize', 0),
            ('particleDensity', 0),
        )

    def loadData(self, record, ins, sub_type, size_, readId):
        """Reads data from ins into record attribute."""
        if size_ == 40:
            # 40 Bytes for legacy data post Skyrim 1.5 DATA is always 48 bytes
            # fffffffIIIIf
            # Type is an Enum 0 = Rain; 1 = Snow
            unpacked = ins.unpack('=7f3I', size_, readId) + (0, 0,)
            setter = record.__setattr__
            for attr,value,action in zip(self.attrs,unpacked,self.actions):
                if action: value = action(value)
                setter(attr,value)
            if self._debug:
                print u' ',zip(self.attrs,unpacked)
                if len(unpacked) != len(self.attrs):
                    print u' ',unpacked
        elif size_ != 48:
            raise ModSizeError(record.inName, readId, 48, size_, True)
        else:
            MelStruct.loadData(self, record, ins, sub_type, size_, readId)

class MreSpgd(MelRecord):
    """Spgd Item"""
    classType = 'SPGD'

    melSet = MelSet(
        MelString('EDID','eid'),
        MelSpgdData(),
        MelString('ICON','icon'),
        )
    __slots__ = melSet.getSlotsUsed()


#------------------------------------------------------------------------------
class MreStat(MelRecord):
    """Static model record."""
    classType = 'STAT'
    melSet = MelSet(
        MelString('EDID','eid'),
        MelBounds(),
        MelModel(),
        MelStruct('DNAM','fI','maxAngle30to120',(FID,'material'),),
        # Contains null-terminated mesh filename followed by random data
        # up to 260 bytes and repeats 4 times
        MelBase('MNAM','distantLOD'),
        )
    __slots__ = melSet.getSlotsUsed()

# Verified for 305
# MNAM Should use a custom unpacker if needed for the patcher otherwise MelBase
#------------------------------------------------------------------------------
class MreTact(MelRecord):
    """Talking Activator"""
    classType = 'TACT'
    melSet = MelSet(
        MelString('EDID','eid'),
        MelVmad(),
        MelBounds(),
        MelLString('FULL','full'),
        MelModel(),
        MelDestructible(),
        MelKeywords(),
        MelBase('PNAM','pnam_p'),
        MelOptStruct('SNAM','I',(FID,'soundLoop')),
        MelBase('FNAM','fnam_p'),
        MelOptStruct('VNAM','I',(FID,'voiceType')),
        )
    __slots__ = melSet.getSlotsUsed()

# Verified for 305
#------------------------------------------------------------------------------
class MreTree(MelRecord):
    """Tree Item"""
    classType = 'TREE'

    melSet = MelSet(
        MelString('EDID','eid'),
        MelVmad(),
        MelBounds(),
        MelModel(),
        MelFid('PFIG','harvestIngredient'),
        MelFid('SNAM','harvestSound'),
        MelStruct('PFPC','4B','spring','summer','fall','wsinter',),
        MelLString('FULL','full'),
        MelStruct('CNAM','ff32sff','trunkFlexibility','branchFlexibility',
                  'unknown','leafAmplitude','leafFrequency',),
        )
    __slots__ = melSet.getSlotsUsed()

# Verified for 305
#------------------------------------------------------------------------------
class MreTxst(MelRecord):
    """Texture Set"""
    classType = 'TXST'

    # {0x0001}'No Specular Map',
    # {0x0002}'Facegen Textures',
    # {0x0004}'Has Model Space Normal Map'
    TxstTypeFlags = Flags(0L,Flags.getNames(
        (0, 'noSpecularMap'),
        (1, 'facegenTextures'),
        (2, 'hasModelSpaceNormalMap'),
    ))

    melSet = MelSet(
        MelString('EDID','eid'),
        MelBounds(),
        MelGroups('destructionData',
            MelString('TX00','difuse'),
            MelString('TX01','normalGloss'),
            MelString('TX02','enviroMaskSubSurfaceTint'),
            MelString('TX03','glowDetailMap'),
            MelString('TX04','height'),
            MelString('TX05','environment'),
            MelString('TX06','multilayer'),
            MelString('TX07','backlightMaskSpecular'),
            ),
        MelDecalData(),
        MelStruct('DNAM','H',(TxstTypeFlags,'flags',0L),),
        )
    __slots__ = melSet.getSlotsUsed()

# Verified for 305
#------------------------------------------------------------------------------
class MreVtyp(MelRecord):
    """Vtyp Item"""
    classType = 'VTYP'

    # 'Allow Default Dialog',
    # 'Female'
    VtypTypeFlags = Flags(0L,Flags.getNames(
            (0, 'allowDefaultDialog'),
            (1, 'female'),
        ))

    melSet = MelSet(
        MelString('EDID','eid'),
        MelStruct('DNAM','B',(VtypTypeFlags,'flags',0L),),
        )
    __slots__ = melSet.getSlotsUsed()

# Verified for 305
#------------------------------------------------------------------------------
class MreWatr(MelRecord):
    """Water"""
    classType = 'WATR'

    WatrTypeFlags = Flags(0L,Flags.getNames(
            (0, 'causesDamage'),
        ))

    melSet = MelSet(
        MelString('EDID','eid'),
        MelLString('FULL','full'),
        MelGroups('unused',
            MelString('NNAM','noiseMap',),
            ),
        MelStruct('ANAM','B','opacity'),
        MelStruct('FNAM','B',(WatrTypeFlags,'flags',0L),),
        MelBase('MNAM','unused1'),
        MelFid('TNAM','material',),
        MelFid('SNAM','openSound',),
        MelFid('XNAM','spell',),
        MelFid('INAM','imageSpace',),
        MelStruct('DATA','H','damagePerSecond'),
        MelStruct('DNAM','7f4s2f3Bs3Bs3Bs4s43f','unknown1','unknown2','unknown3',
                  'unknown4','specularPropertiesSunSpecularPower',
                  'waterPropertiesReflectivityAmount',
                  'waterPropertiesFresnelAmount',('unknown5',null4),
                  'fogPropertiesAboveWaterFogDistanceNearPlane',
                  'fogPropertiesAboveWaterFogDistanceFarPlane',
                  # Shallow Color
                  'red_sc','green_sc','blue_sc','unknown_sc',
                  # Deep Color
                  'red_dc','green_dc','blue_dc','unknown_dc',
                  # Reflection Color
                  'red_rc','green_rc','blue_rc','unknown_rc',
                  ('unknown6',null4),'unknown7','unknown8','unknown9','unknown10',
                  'displacementSimulatorStartingSize',
                  'displacementSimulatorForce','displacementSimulatorVelocity',
                  'displacementSimulatorFalloff','displacementSimulatorDampner',
                  'unknown11','noisePropertiesNoiseFalloff',
                  'noisePropertiesLayerOneWindDirection',
                  'noisePropertiesLayerTwoWindDirection',
                  'noisePropertiesLayerThreeWindDirection',
                  'noisePropertiesLayerOneWindSpeed',
                  'noisePropertiesLayerTwoWindSpeed',
                  'noisePropertiesLayerThreeWindSpeed',
                  'unknown12','unknown13','fogPropertiesAboveWaterFogAmount',
                  'unknown14','fogPropertiesUnderWaterFogAmount',
                  'fogPropertiesUnderWaterFogDistanceNearPlane',
                  'fogPropertiesUnderWaterFogDistanceFarPlane',
                  'waterPropertiesRefractionMagnitude',
                  'specularPropertiesSpecularPower',
                  'unknown15','specularPropertiesSpecularRadius',
                  'specularPropertiesSpecularBrightness',
                  'noisePropertiesLayerOneUVScale',
                  'noisePropertiesLayerTwoUVScale',
                  'noisePropertiesLayerThreeUVScale',
                  'noisePropertiesLayerOneAmplitudeScale',
                  'noisePropertiesLayerTwoAmplitudeScale',
                  'noisePropertiesLayerThreeAmplitudeScale',
                  'waterPropertiesReflectionMagnitude',
                  'specularPropertiesSunSparkleMagnitude',
                  'specularPropertiesSunSpecularMagnitude',
                  'depthPropertiesReflections','depthPropertiesRefraction',
                  'depthPropertiesNormals','depthPropertiesSpecularLighting',
                  'specularPropertiesSunSparklePower',
                  ),
        MelBase('GNAM','unused2'),
        # Linear Velocity
        MelStruct('NAM0','3f','linv_x','linv_y','linv_z',),
        # Angular Velocity
        MelStruct('NAM1','3f','andv_x','andv_y','andv_z',),
        MelString('NAM2','noiseTexture'),
        MelString('NAM3','unused3'),
        MelString('NAM4','unused4'),
        )
    __slots__ = melSet.getSlotsUsed()

# Verified for 305
#------------------------------------------------------------------------------
class MreWeap(MelRecord):
    """Weapon"""
    classType = 'WEAP'

    # 'On Death'
    WeapFlags3 = Flags(0L,Flags.getNames(
        (0, 'onDeath'),
    ))

    # {0x00000001}'Player Only',
    # {0x00000002}'NPCs Use Ammo',
    # {0x00000004}'No Jam After Reload (unused)',
    # {0x00000008}'Unknown 4',
    # {0x00000010}'Minor Crime',
    # {0x00000020}'Range Fixed',
    # {0x00000040}'Not Used in Normal Combat',
    # {0x00000080}'Unknown 8',
    # {0x00000100}'Don''t Use 3rd Person IS Anim (unused)',
    # {0x00000200}'Unknown 10',
    # {0x00000400}'Rumble - Alternate',
    # {0x00000800}'Unknown 12',
    # {0x00001000}'Non-hostile',
    # {0x00002000}'Bound Weapon'
    WeapFlags2 = Flags(0L,Flags.getNames(
            (0, 'playerOnly'),
            (1, 'nPCsUseAmmo'),
            (2, 'noJamAfterReloadunused'),
            (3, 'unknown4'),
            (4, 'minorCrime'),
            (5, 'rangeFixed'),
            (6, 'notUsedinNormalCombat'),
            (7, 'unknown8'),
            (8, 'don'),
            (9, 'unknown10'),
            (10, 'rumbleAlternate'),
            (11, 'unknown12'),
            (12, 'nonhostile'),
            (13, 'boundWeapon'),
        ))

    # {0x0001}'Ignores Normal Weapon Resistance',
    # {0x0002}'Automatic (unused)',
    # {0x0004}'Has Scope (unused)',
    # {0x0008}'Can''t Drop',
    # {0x0010}'Hide Backpack (unused)',
    # {0x0020}'Embedded Weapon (unused)',
    # {0x0040}'Don''t Use 1st Person IS Anim (unused)',
    # {0x0080}'Non-playable'
    WeapFlags1 = Flags(0L,Flags.getNames(
            (0, 'ignoresNormalWeaponResistance'),
            (1, 'automaticunused'),
            (2, 'hasScopeunused'),
            (3, 'can'),
            (4, 'hideBackpackunused'),
            (5, 'embeddedWeaponunused'),
            (6, 'don'),
            (7, 'nonplayable'),
        ))

    melSet = MelSet(
        MelString('EDID','eid'),
        MelVmad(),
        MelBounds(),
        MelLString('FULL','full'),
        MelModel('model1','MODL'),
        MelString('ICON','iconPath'),
        MelString('MICO','smallIconPath'),
        MelFid('EITM','enchantment',),
        MelOptStruct('EAMT','H','enchantPoints'),
        MelDestructible(),
        MelFid('ETYP','equipmentType',),
        MelFid('BIDS','blockBashImpactDataSet',),
        MelFid('BAMT','alternateBlockMaterial',),
        MelFid('YNAM','pickupSound',),
        MelFid('ZNAM','dropSound',),
        MelKeywords(),
        MelLString('DESC','description'),
        MelModel('model2','MOD3'),
        MelBase('NNAM','unused1'),
        MelFid('INAM','impactDataSet',),
        MelFid('WNAM','firstPersonModelObject',),
        MelFid('SNAM','attackSound',),
        MelFid('XNAM','attackSound2D',),
        MelFid('NAM7','attackLoopSound',),
        MelFid('TNAM','attackFailSound',),
        MelFid('UNAM','idleSound',),
        MelFid('NAM9','equipSound',),
        MelFid('NAM8','unequipSound',),
        MelStruct('DATA','IfH','value','weight','damage',),
        MelStruct('DNAM','B3s2fH2sf4s4B2f2I5f12si8si4sf','animationType',
                  ('dnamUnk1',null3),'speed','reach',
                  (WeapFlags1,'dnamFlags1',None),('dnamUnk2',null2),'sightFOV',
                  ('dnamUnk3',null4),'baseVATSToHitChance','attackAnimation',
                  'numProjectiles','embeddedWeaponAVunused','minRange',
                  'maxRange','onHit',(WeapFlags2,'dnamFlags2',None),
                  'animationAttackMultiplier',('dnamUnk4',0.0),
                  'rumbleLeftMotorStrength','rumbleRightMotorStrength',
                  'rumbleDuration',('dnamUnk5',null4+null4+null4),'skill',
                  ('dnamUnk6',null4+null4),'resist',('dnamUnk7',null4),'stagger',),
        MelStruct('CRDT','H2sfB3sI','critDamage',('crdtUnk1',null2),'criticalMultiplier',
                  (WeapFlags3,'criticalFlags',0L),('crdtUnk2',null3),(FID,'criticalEffect',None),),
        MelStruct('VNAM','I','detectionSoundLevel'),
        MelFid('CNAM','template',),
        )
    __slots__ = melSet.getSlotsUsed()

# Verified for 305
#------------------------------------------------------------------------------
class MreWoop(MelRecord):
    """Word of Power"""
    classType = 'WOOP'
    melSet = MelSet(
        MelString('EDID','eid'),
        MelLString('FULL','full'),
        MelLString('TNAM','translation'),
        )
    __slots__ = melSet.getSlotsUsed()

# Verified for 305
#------------------------------------------------------------------------------
class MreWrld(MelRecord):
    """Worldspace"""
    classType = 'WRLD'

    # {0x01} 'Small World',
    # {0x02} 'Can''t Fast Travel',
    # {0x04} 'Unknown 3',
    # {0x08} 'No LOD Water',
    # {0x10} 'No Landscape',
    # {0x20} 'Unknown 6',
    # {0x40} 'Fixed Dimensions',
    # {0x80} 'No Grass'
    WrldFlags2 = Flags(0L,Flags.getNames(
            (0, 'smallWorld'),
            (1, 'noFastTravel'),
            (2, 'unknown3'),
            (3, 'noLODWater'),
            (4, 'noLandscape'),
            (5, 'unknown6'),
            (6, 'fixedDimensions'),
            (7, 'noGrass'),
        ))

    # {0x0001}'Use Land Data',
    # {0x0002}'Use LOD Data',
    # {0x0004}'Don''t Use Map Data',
    # {0x0008}'Use Water Data',
    # {0x0010}'Use Climate Data',
    # {0x0020}'Use Image Space Data (unused)',
    # {0x0040}'Use Sky Cell'
    WrldFlags1 = Flags(0L,Flags.getNames(
            (0, 'useLandData'),
            (1, 'useLODData'),
            (2, 'don'),
            (3, 'useWaterData'),
            (4, 'useClimateData'),
            (5, 'useImageSpaceDataunused'),
            (6, 'useSkyCell'),
        ))

    class MelWrldMnam(MelOptStruct):
        """Handle older truncated MNAM for WRLD subrecord."""
        def loadData(self, record, ins, sub_type, size_, readId):
            if size_ == 28:
                MelStruct.loadData(self, record, ins, sub_type, size_, readId)
                return
            elif size_ == 24:
                unpacked = ins.unpack('2i4h2f', size_, readId)
            elif size_ == 16:
                unpacked = ins.unpack('2i4h', size_, readId)
            else:
                raise ModSizeError(record.inName, readId, 28, size_, True)
            unpacked += self.defaults[len(unpacked):]
            setter = record.__setattr__
            for attr,value,action in zip(self.attrs,unpacked,self.actions):
                if callable(action): value = action(value)
                setter(attr,value)
            if self._debug: print unpacked, record.flags.getTrueAttrs()

    melSet = MelSet(
        MelString('EDID','eid'),
        # {>>> BEGIN leftover from earlier CK versions <<<}
        MelGroups('unusedRNAM',
            MelBase('RNAM','unknown',),
        ),
        # {>>> END leftover from earlier CK versions <<<}
        MelBase('MHDT','maxHeightData'),
        MelLString('FULL','full'),
        # Fixed Dimensions Center Cell
        MelOptStruct('WCTR','2h',('fixedX', 0),('fixedY', 0),),
        MelFid('LTMP','interiorLighting',),
        MelFid('XEZN','encounterZone',),
        MelFid('XLCN','location',),
        MelGroup('parent',
            MelFid('WNAM','worldspace',),
            MelStruct('PNAM','Bs',(WrldFlags1,'parentFlags',0L),'unknown',),
        ),
        MelFid('CNAM','climate',),
        MelFid('NAM2','water',),
        MelFid('NAM3','lODWaterType',),
        MelOptStruct('NAM4','f',('lODWaterHeight', 0.0),),
        MelOptStruct('DNAM','2f',('defaultLandHeight', 0.0),
                     ('defaultWaterHeight', 0.0),),
        MelString('ICON','mapImage'),
        MelModel('cloudModel','MODL',),
        MelWrldMnam('MNAM','2i4h3f','usableDimensionsX','usableDimensionsY',
                  'cellCoordinatesX','cellCoordinatesY','seCellX','seCellY',
                  'cameraDataMinHeight','cameraDataMaxHeight',
                  'cameraDataInitialPitch',),
        MelStruct('ONAM','4f','worldMapScale','cellXOffset','cellYOffset',
                  'cellZOffset',),
        MelStruct('NAMA','f','distantLODMultiplier',),
        MelStruct('DATA','B',(WrldFlags2,'dataFlags',0L),),
        # {>>> Object Bounds doesn't show up in CK <<<}
        MelStruct('NAM0','2f','minObjX','minObjY',),
        MelStruct('NAM9','2f','maxObjX','maxObjY',),
        MelFid('ZNAM','music',),
        MelString('NNAM','canopyShadowunused'),
        MelString('XNAM','waterNoiseTexture'),
        MelString('TNAM','hDLODDiffuseTexture'),
        MelString('UNAM','hDLODNormalTexture'),
        MelString('XWEM','waterEnvironmentMapunused'),
        MelBase('OFST','unknown'),
        )
    __slots__ = melSet.getSlotsUsed()

# # Many Things Marked MelBase that need updated
#------------------------------------------------------------------------------
class MreWthr(MelRecord):
    """Weather"""
    classType = 'WTHR'

    WthrFlags2 = Flags(0L,Flags.getNames(
            (0, 'layer_0'),
            (1, 'layer_1'),
            (2, 'layer_2'),
            (3, 'layer_3'),
            (4, 'layer_4'),
            (5, 'layer_5'),
            (6, 'layer_6'),
            (7, 'layer_7'),
            (8, 'layer_8'),
            (9, 'layer_9'),
            (10, 'layer_10'),
            (11, 'layer_11'),
            (12, 'layer_12'),
            (13, 'layer_13'),
            (14, 'layer_14'),
            (15, 'layer_15'),
            (16, 'layer_16'),
            (17, 'layer_17'),
            (18, 'layer_18'),
            (19, 'layer_19'),
            (20, 'layer_20'),
            (21, 'layer_21'),
            (22, 'layer_22'),
            (23, 'layer_23'),
            (24, 'layer_24'),
            (25, 'layer_25'),
            (26, 'layer_26'),
            (27, 'layer_27'),
            (28, 'layer_28'),
            (29, 'layer_29'),
            (30, 'layer_30'),
            (31, 'layer_31'),
        ))

    # {0x01} 'Weather - Pleasant',
    # {0x02} 'Weather - Cloudy',
    # {0x04} 'Weather - Rainy',
    # {0x08} 'Weather - Snow',
    # {0x10} 'Sky Statics - Always Visible',
    # {0x20} 'Sky Statics - Follows Sun Position'
    WthrFlags1 = Flags(0L,Flags.getNames(
            (0, 'weatherPleasant'),
            (1, 'weatherCloudy'),
            (2, 'weatherRainy'),
            (3, 'weatherSnow'),
            (4, 'skyStaticsAlwaysVisible'),
            (5, 'skyStaticsFollowsSunPosition'),
        ))

    class MelWthrDalc(MelStructs):
        """Handle older truncated DALC for WTHR subrecord."""
        def loadData(self, record, ins, sub_type, size_, readId):
            if size_ == 32:
                MelStructs.loadData(self, record, ins, sub_type, size_, readId)
                return
            elif size_ == 24:
                unpacked = ins.unpack('=4B4B4B4B4B4B', size_, readId)
            else:
                raise ModSizeError(record.inName, readId, 32, size_, True)
            unpacked += self.defaults[len(unpacked):]
            target = MelObject()
            record.__getattribute__(self.attr).append(target)
            target.__slots__ = self.attrs
            setter = target.__setattr__
            for attr,value,action in zip(self.attrs,unpacked,self.actions):
                if callable(action): value = action(value)
                setter(attr,value)
            if self._debug: print unpacked

    melSet = MelSet(
        MelString('EDID','eid'),
        MelString('\x300TX','cloudTextureLayer_0'),
        MelString('\x310TX','cloudTextureLayer_1'),
        MelString('\x320TX','cloudTextureLayer_2'),
        MelString('\x330TX','cloudTextureLayer_3'),
        MelString('\x340TX','cloudTextureLayer_4'),
        MelString('\x350TX','cloudTextureLayer_5'),
        MelString('\x360TX','cloudTextureLayer_6'),
        MelString('\x370TX','cloudTextureLayer_7'),
        MelString('\x380TX','cloudTextureLayer_8'),
        MelString('\x390TX','cloudTextureLayer_9'),
        MelString('\x3A0TX','cloudTextureLayer_10'),
        MelString('\x3B0TX','cloudTextureLayer_11'),
        MelString('\x3C0TX','cloudTextureLayer_12'),
        MelString('\x3D0TX','cloudTextureLayer_13'),
        MelString('\x3E0TX','cloudTextureLayer_14'),
        MelString('\x3F0TX','cloudTextureLayer_15'),
        MelString('\x400TX','cloudTextureLayer_16'),
        MelString('A0TX','cloudTextureLayer_17'),
        MelString('B0TX','cloudTextureLayer_18'),
        MelString('C0TX','cloudTextureLayer_19'),
        MelString('D0TX','cloudTextureLayer_20'),
        MelString('E0TX','cloudTextureLayer_21'),
        MelString('F0TX','cloudTextureLayer_22'),
        MelString('G0TX','cloudTextureLayer_23'),
        MelString('H0TX','cloudTextureLayer_24'),
        MelString('I0TX','cloudTextureLayer_25'),
        MelString('J0TX','cloudTextureLayer_26'),
        MelString('K0TX','cloudTextureLayer_27'),
        MelString('L0TX','cloudTextureLayer_28'),
        MelBase('DNAM','dnam_p'),
        MelBase('CNAM','cnam_p'),
        MelBase('ANAM','anam_p'),
        MelBase('BNAM','bnam_p'),
        MelBase('LNAM','lnam_p'),
        MelFid('MNAM','precipitationType',),
        MelFid('NNAM','visualEffect',),
        MelBase('ONAM','onam_p'),
        MelBase('RNAM','cloudSpeedY'),
        MelBase('QNAM','cloudSpeedX'),
        MelStructA('PNAM','3Bs3Bs3Bs3Bs','cloudColors',
            'riseRedPnam','riseGreenPnam','riseBluePnam',('unused1',null1),
            'dayRedPnam','dayGreenPnam','dayBluePnam',('unused2',null1),
            'setRedPnam','setGreenPnam','setBluePnam',('unused3Pnam',null1),
            'nightRedPnam','nightGreenPnam','nightBluePnam',('unused4',null1),
            ),
        MelStructA('JNAM','4f','cloudAlphas','sunAlpha','dayAlpha','setAlpha','nightAlpha',),
        MelStructA('NAM0','3Bs3Bs3Bs3Bs','daytimeColors',
            'riseRed','riseGreen','riseBlue',('unused5',null1),
            'dayRed','dayGreen','dayBlue',('unused6',null1),
            'setRed','setGreen','setBlue',('unused7',null1),
            'nightRed','nightGreen','nightBlue',('unused8',null1),
            ),
        MelStruct('FNAM','8f','dayNear','dayFar','nightNear','nightFar',
                  'dayPower','nightPower','dayMax','nightMax',),
        MelStruct('DATA','B2s16B','windSpeed',('unknown',null2),'transDelta',
                  'sunGlare','sunDamage','precipitationBeginFadeIn',
                  'precipitationEndFadeOut','thunderLightningBeginFadeIn',
                  'thunderLightningEndFadeOut','thunderLightningFrequency',
                  (WthrFlags1,'wthrFlags1',0L),'red','green','blue',
                  'visualEffectBegin','visualEffectEnd',
                  'windDirection','windDirectionRange',),
        MelStruct('NAM1','I',(WthrFlags2,'wthrFlags2',0L),),
        MelStructs('SNAM','2I','sounds',(FID,'sound'),'type'),
        MelFids('TNAM','skyStatics',),
        MelStruct('IMSP','4I',(FID,'imageSpacesSunrise'),(FID,'imageSpacesDay'),
                  (FID,'imageSpacesSunset'),(FID,'imageSpacesNight'),),
        MelWthrDalc('DALC','=4B4B4B4B4B4B4Bf','wthrAmbientColors',
            'redXplus','greenXplus','blueXplus','unknownXplus', # 'X+'
            'redXminus','greenXminus','blueXminus','unknownXminus', # 'X-'
            'redYplus','greenYplus','blueYplus','unknownYplus', # 'Y+'
            'redYminus','greenYminus','blueYminus','unknownYminus', # 'Y-'
            'redZplus','greenZplus','blueZplus','unknownZplus', # 'Z+'
            'redZminus','greenZminus','blueZminus','unknownZminus', # 'Z-'
            'redSpec','greenSpec','blueSpec','unknownSpec', # Specular Color Values
            'fresnelPower', # Fresnel Power
            ),
        MelBase('NAM2','nam2_p'),
        MelBase('NAM3','nam3_p'),
        MelModel('aurora','MODL'),
        )
    __slots__ = melSet.getSlotsUsed()

# Verified for 305
# Some things Marked MelBase could be updated if mitigation needed
