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
from ... import bush, brec
from ...bolt import Flags, struct_unpack, struct_pack
from ...brec import MelRecord, MelGroups, MelStruct, FID, MelGroup, \
    MelString, MelSet, MelFid, MelNull, MelOptStruct, MelFids, MreHeaderBase, \
    MelBase, MelUnicode, MelFidList, MreGmstBase, MelStrings, MelMODS, \
    MreHasEffects, MelReferences, MelColorInterpolator, MelValueInterpolator, \
    MelUnion, AttrValDecider, MelRegnEntrySubrecord, SizeDecider, MelFloat, \
    MelSInt8, MelSInt16, MelSInt32, MelUInt8, MelUInt16, MelUInt32, \
    MelOptFid, MelOptFloat, MelOptSInt16, MelOptSInt32, MelOptUInt8, \
    MelOptUInt16, MelOptUInt32, MelPartialCounter, MelRaceParts, \
    MelRaceVoices, MelBounds, null1, null2, null3, null4, MelScriptVars, \
    MelSequential, MelTruncatedStruct, PartialLoadDecider, MelReadOnly, \
    MelCoordinates, MelIcons, MelIcons2, MelIcon, MelIco2, MelEdid, MelFull, \
    MelArray, MelWthrColors, MreLeveledListBase
from ...exception import BoltError, ModError, ModSizeError, StateError
# Set MelModel in brec but only if unset
if brec.MelModel is None:

    class _MelModel(MelGroup):
        """Represents a model record."""
        typeSets = (('MODL', 'MODB', 'MODT', 'MODS', 'MODD'),
                    ('MOD2', 'MO2B', 'MO2T', 'MO2S'),
                    ('MOD3', 'MO3B', 'MO3T', 'MO3S', 'MOSD'),
                    ('MOD4', 'MO4B', 'MO4T', 'MO4S'))

        _facegen_model_flags = Flags(0, Flags.getNames(
            'head',
            'torso',
            'rightHand',
            'leftHand',
        ))

        def __init__(self, attr='model', index=0, with_facegen_flags=True):
            """Initialize. Index is 0,2,3,4 for corresponding type id."""
            types = self.__class__.typeSets[(0, index - 1)[index > 0]]
            model_elements = [
                MelString(types[0], 'modPath'),
                MelBase(types[1], 'modb_p'),
                # Texture File Hashes
                MelBase(types[2], 'modt_p'),
                MelMODS(types[3], 'alternateTextures'),
            ]
            # No MODD/MOSD equivalent for MOD2 and MOD4
            if len(types) == 5 and with_facegen_flags:
                model_elements += [
                    MelOptUInt8(types[4], (_MelModel._facegen_model_flags,
                                           'facegen_model_flags'))
                ]
            MelGroup.__init__(self, attr, *model_elements)

    brec.MelModel = _MelModel
from ...brec import MelModel

#------------------------------------------------------------------------------
# Record Elements    ----------------------------------------------------------
#------------------------------------------------------------------------------
class MreActor(MelRecord):
    """Creatures and NPCs."""
    TemplateFlags = Flags(0, Flags.getNames(
        'useTraits',
        'useStats',
        'useFactions',
        'useActorEffectList',
        'useAIData',
        'useAIPackages',
        'useModelAnimation',
        'useBaseData',
        'useInventory',
        'useScript',
    ))

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
    def __init__(self,default=0,newNames=None):
        names = Flags.getNames(
            'head', 'hair', 'upperBody', 'leftHand', 'rightHand', 'weapon',
            'pipboy', 'backpack', 'necklace', 'headband', 'hat', 'eyeGlasses',
            'noseRing', 'earrings', 'mask', 'choker', 'mouthObject',
            'bodyAddOn1', 'bodyAddOn2', 'bodyAddOn3')
        if newNames: names.update(newNames)
        Flags.__init__(self,default,names)

#------------------------------------------------------------------------------
class MelConditions(MelGroups):
    """Represents a set of quest/dialog conditions. Difficulty is that FID
    state of parameters depends on function index."""
    class MelCtda(MelStruct):
        def setDefault(self, record):
            MelStruct.setDefault(self, record)
            record.form1234 = 'iiII'

        def hasFids(self, formElements):
            formElements.add(self)

        def loadData(self, record, ins, sub_type, size_, readId):
            if size_ not in (28, 24, 20):
                raise ModSizeError(ins.inName, readId, (28, 24, 20), size_)
            unpacked1 = ins.unpack('B3sfH2s', 12, readId)
            (record.operFlag, record.unused1, record.compValue, ifunc,
             record.unused2) = unpacked1
            #--Get parameters
            if ifunc not in bush.game.condition_function_data:
                raise BoltError(u'Unknown condition function: %d\nparam1: '
                                u'%08X\nparam2: %08X' % (
                    ifunc, ins.unpackRef(), ins.unpackRef()))
            # Form1 is Param1 - 2 means fid
            form1 = ('I' if bush.game.condition_function_data[ifunc][1] == 2
                     else 'i')
            # Form2 is Param2
            form2 = ('I' if bush.game.condition_function_data[ifunc][2] == 2
                     else 'i')
            # Form3 is runOn
            form3 = 'I'
            # Form4 is reference, this is a formID when runOn = 2
            form4 = 'I'
            if size_ == 28:
                form1234 = form1 + form2 + form3 + form4
                unpacked2 = ins.unpack(form1234, 16, readId)
                (record.param1, record.param2, record.runOn,
                 record.reference) = unpacked2
            elif size_ == 24:
                form1234 = form1 + form2 + form3
                unpacked2 = ins.unpack(form1234, 12, readId)
                record.param1, record.param2, record.runOn = unpacked2
                record.reference = null4
            else: # size_ == 20, verified at the start
                form1234 = form1 + form2
                unpacked2 = ins.unpack(form1234, 8, readId)
                record.param1, record.param2 = unpacked2
                record.runOn, record.reference = null4, null4
            record.ifunc, record.form1234 = ifunc, form1234

        def dumpData(self,record,out):
            out.packSub('CTDA', '=B3sfH2s' + record.form1234,
                record.operFlag, record.unused1, record.compValue,
                record.ifunc, record.unused2, record.param1, record.param2,
                record.runOn, record.reference)

        def mapFids(self,record,function,save=False):
            form1234 = record.form1234
            if form1234[0] == 'I':
                result = function(record.param1)
                if save: record.param1 = result
            if form1234[1] == 'I':
                result = function(record.param2)
                if save: record.param2 = result
            # runOn is uint32, never FID
            #0:Subject,1:Target,2:Reference,3:Combat Target,4:Linked Reference
            if len(form1234) > 3 and form1234[3] == 'I' and record.runOn == 2:
                result = function(record.reference)
                if save: record.reference = result

    def __init__(self):
        MelGroups.__init__(self, 'conditions',
            MelConditions.MelCtda(
                'CTDA','B3sfH2siiII', 'operFlag', ('unused1', null3),
                'compValue', 'ifunc', ('unused2', null2), 'param1', 'param2',
                'runOn', 'reference'),
        )

#------------------------------------------------------------------------------
class MelDestructible(MelGroup):
    """Represents a set of destruct record."""

    MelDestVatsFlags = Flags(0, Flags.getNames(
        (0, 'vatsTargetable'),
        ))
    MelDestStageFlags = Flags(0, Flags.getNames(
        (0, 'capDamage'),
        (1, 'disable'),
        (2, 'destroy'),
        ))

    def __init__(self,attr='destructible'):
        MelGroup.__init__(self,attr,
            MelStruct('DEST','i2B2s','health','count',
                     (MelDestructible.MelDestVatsFlags,'flagsDest',0),'unused'),
            MelGroups('stages',
                MelStruct('DSTD','=4Bi2Ii','health','index','damageStage',
                          (MelDestructible.MelDestStageFlags,'flagsDest',0),'selfDamagePerSecond',
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
        MelGroups.__init__(self, attr,
            MelFid('EFID','baseEffect'),
            MelStruct('EFIT','4Ii','magnitude','area','duration','recipient','actorValue'),
            MelConditions(),
        )

#------------------------------------------------------------------------------
class MelEmbeddedScript(MelSequential):
    """Handles an embedded script, a SCHR/SCDA/SCTX/SLSD/SCVR/SCRO/SCRV
    subrecord combo."""
    _script_header_flags = Flags(0, Flags.getNames('enabled'))

    def __init__(self):
        MelSequential.__init__(self,
            MelStruct('SCHR', '4s3I2H', ('unused1', null4), 'num_refs',
                      'compiled_size', 'last_index', 'script_type',
                      (self._script_header_flags, 'schr_flags', 0)),
            MelBase('SCDA', 'compiled_script'),
            MelString('SCTX', 'script_source'),
            MelScriptVars(),
            MelReferences(),
        )

#------------------------------------------------------------------------------
class MreLeveledList(MreLeveledListBase):
    """Leveled item/creature/spell list.."""
    top_copy_attrs = ('chanceNone', 'glob')
    entry_copy_attrs = ('listId', 'level', 'count', 'owner', 'condition')

    class MelLevListLvld(MelStruct):
        """Subclass to support alternate format."""
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
        MelBounds(),
        MelLevListLvld('LVLD','B','chanceNone'),
        MelUInt8('LVLF', (MreLeveledListBase._flags, 'flags', 0)),
        MelFid('LVLG','glob'),
        MelGroups('entries',
            MelLevListLvlo('LVLO', 'h2sIh2s', 'level', ('unused1', null2),
                           (FID, 'listId', None), ('count', 1),
                           ('unused2', null2), old_versions={'iI'}),
            MelOptStruct('COED', '2If', (FID, 'owner', None),
                         (FID, 'glob', None), ('condition', 1.0)),
        ),
        MelModel(),
    )
    __slots__ = melSet.getSlotsUsed()

#------------------------------------------------------------------------------
class MelOwnership(MelGroup):
    """Handles XOWN, XRNK, and XGLB for cells and cell children."""

    def __init__(self,attr='ownership'):
        MelGroup.__init__(self,attr,
            MelFid('XOWN','owner'),
            MelOptSInt32('XRNK', ('rank', None)),
            ##: Double check XGLB it's not used in FO3Edit/FNVEdit
            MelFid('XGLB','global'),
        )

    def dumpData(self,record,out):
        if record.ownership and record.ownership.owner:
            MelGroup.dumpData(self,record,out)

#------------------------------------------------------------------------------
class MelRaceHeadPart(MelGroup):
    """Implements special handling for ears, which can only contain an icon
    or a model, not both. Has to be here, since it's used by lambdas inside
    the RACE definition so it can't be a subclass."""
    def __init__(self, part_indx):
        self._modl_loader = MelModel()
        self._icon_loader = MelIcons(mico_attr='')
        self._mico_loader = MelIcons(icon_attr='')
        MelGroup.__init__(self, 'head_part',
            self._modl_loader,
            self._icon_loader,
            self._mico_loader,
        )
        self._part_indx = part_indx

    def dumpData(self, record, out):
        if self._part_indx == 1:
            target_head_part = getattr(record, self.attr)
            # Special handling for ears: If ICON or MICO is present, don't
            # dump the model
            has_icon = hasattr(target_head_part, 'iconPath')
            has_mico = hasattr(target_head_part, 'smallIconPath')
            if not has_icon and not has_mico:
                self._modl_loader.dumpData(target_head_part, out)
            else:
                if has_icon: self._icon_loader.dumpData(target_head_part, out)
                if has_mico: self._mico_loader.dumpData(target_head_part, out)
            return
        # Otherwise, delegate the dumpData call to MelGroup
        MelGroup.dumpData(self, record, out)

#------------------------------------------------------------------------------
# Fallout3 Records ------------------------------------------------------------
#------------------------------------------------------------------------------
class MreTes4(MreHeaderBase):
    """TES4 Record.  File header."""
    classType = 'TES4'

    melSet = MelSet(
        MelStruct('HEDR', 'f2I', ('version', 0.94), 'numRecords',
                  ('nextObject', 0x800)),
        MelBase('OFST','ofst_p',),  #--Obsolete?
        MelBase('DELE','dele_p',),  #--Obsolete?
        MelUnicode('CNAM','author',u'',512),
        MelUnicode('SNAM','description',u'',512),
        MreHeaderBase.MelMasterNames(),
        MelFidList('ONAM','overrides'),
        MelBase('SCRN', 'screenshot'),
    )
    __slots__ = melSet.getSlotsUsed()

#------------------------------------------------------------------------------
class MreAchr(MelRecord):
    """Placed NPC."""
    classType = 'ACHR'

    _flags = Flags(0, Flags.getNames('oppositeParent','popIn'))

    melSet = MelSet(
        MelEdid(),
        MelFid('NAME','base'),
        MelFid('XEZN','encounterZone'),
        MelBase('XRGD','ragdollData'),
        MelBase('XRGB','ragdollBipedData'),
        MelGroup('patrolData',
            MelFloat('XPRD', 'idleTime'),
            MelBase('XPPA','patrolScriptMarker'),
            MelFid('INAM', 'idle'),
            MelEmbeddedScript(),
            MelFid('TNAM','topic'),
        ),
        MelSInt32('XLCM', 'levelModifier'),
        MelFid('XMRC','merchantContainer',),
        MelSInt32('XCNT', 'count'),
        MelFloat('XRDS', 'radius'),
        MelFloat('XHLP', 'health'),
        MelGroups('linkedDecals',
            MelStruct('XDCR', '2I', (FID, 'reference'), 'unknown'),
        ),
        MelFid('XLKR','linkedReference'),
        MelOptStruct('XCLP','8B','linkStartColorRed','linkStartColorGreen','linkStartColorBlue',('linkColorUnused1',null1),
                     'linkEndColorRed','linkEndColorGreen','linkEndColorBlue',('linkColorUnused2',null1)),
        MelGroup('activateParents',
            MelUInt8('XAPD', 'flags'),
            MelGroups('activateParentRefs',
                MelStruct('XAPR', 'If', (FID, 'reference'), 'delay'),
            ),
        ),
        MelOptStruct('XESP','IB3s',(FID,'parent'),(_flags,'parentFlags'),('unused1',null3)),
        MelOptFid('XEMI', 'emittance'),
        MelFid('XMBR','multiboundReference'),
        MelBase('XIBS','ignoredBySandbox'),
        MelOptFloat('XSCL', ('scale', 1.0)),
        MelOptStruct('DATA','=6f',('posX',None),('posY',None),('posZ',None),('rotX',None),('rotY',None),('rotZ',None)),
    )
    __slots__ = melSet.getSlotsUsed()

#------------------------------------------------------------------------------
class MreAcre(MelRecord):
    """Placed Creature."""
    classType = 'ACRE'

    _flags = Flags(0, Flags.getNames('oppositeParent','popIn'))

    melSet = MelSet(
        MelEdid(),
        MelFid('NAME','base'),
        MelFid('XEZN','encounterZone'),
        MelBase('XRGD','ragdollData'),
        MelBase('XRGB','ragdollBipedData'),
        MelGroup('patrolData',
            MelFloat('XPRD', 'idleTime'),
            MelBase('XPPA','patrolScriptMarker'),
            MelFid('INAM', 'idle'),
            MelEmbeddedScript(),
            MelFid('TNAM','topic'),
        ),
        MelSInt32('XLCM', 'levelModifier'),
        MelOwnership(),
        MelFid('XMRC','merchantContainer'),
        MelSInt32('XCNT', 'count'),
        MelFloat('XRDS', 'radius'),
        MelFloat('XHLP', 'health'),
        MelGroups('linkedDecals',
            MelStruct('XDCR', '2I', (FID, 'reference'), 'unknown'),
        ),
        MelFid('XLKR','linkedReference'),
        MelOptStruct('XCLP','8B','linkStartColorRed','linkStartColorGreen','linkStartColorBlue',('linkColorUnused1',null1),
                     'linkEndColorRed','linkEndColorGreen','linkEndColorBlue',('linkColorUnused2',null1)),
        MelGroup('activateParents',
            MelUInt8('XAPD', 'flags'),
            MelGroups('activateParentRefs',
                MelStruct('XAPR', 'If', (FID, 'reference'), 'delay'),
            ),
        ),
        MelOptStruct('XESP','IB3s',(FID,'parent'),(_flags,'parentFlags'),('unused1',null3)),
        MelOptFid('XEMI', 'emittance'),
        MelFid('XMBR','multiboundReference'),
        MelBase('XIBS','ignoredBySandbox'),
        MelOptFloat('XSCL', ('scale', 1.0)),
        MelOptStruct('DATA','=6f',('posX',None),('posY',None),('posZ',None),('rotX',None),('rotY',None),('rotZ',None)),
    )
    __slots__ = melSet.getSlotsUsed()

#------------------------------------------------------------------------------
class MreActi(MelRecord):
    """Activator."""
    classType = 'ACTI'

    melSet = MelSet(
        MelEdid(),
        MelBounds(),
        MelFull(),
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
    """Addon Node."""
    classType = 'ADDN'

    melSet = MelSet(
        MelEdid(),
        MelBounds(),
        MelModel(),
        MelOptSInt32('DATA', 'nodeIndex'),
        MelOptFid('SNAM', 'ambientSound'),
        MelStruct('DNAM','H2s','mastPartSysCap','unknown',),
    )
    __slots__ = melSet.getSlotsUsed()

#------------------------------------------------------------------------------
class MreAlch(MelRecord,MreHasEffects):
    """Ingestible."""
    classType = 'ALCH'

    _flags = Flags(0, Flags.getNames('autoCalc','isFood','medicine',))

    melSet = MelSet(
        MelEdid(),
        MelBounds(),
        MelFull(),
        MelModel(),
        MelIcons(),
        MelFid('SCRI','script'),
        MelDestructible(),
        MelFid('YNAM','pickupSound'),
        MelFid('ZNAM','dropSound'),
        MelSInt32('ETYP', ('etype', -1)),
        MelFloat('DATA', 'weight'),
        MelStruct('ENIT','iB3sIfI','value',(_flags,'flags',0),('unused1',null3),
                  (FID,'withdrawalEffect',None),'addictionChance',(FID,'soundConsume',None)),
        MelEffects(),
    )
    __slots__ = melSet.getSlotsUsed()

#------------------------------------------------------------------------------
class MreAmmo(MelRecord):
    """Ammunition."""
    classType = 'AMMO'

    _flags = Flags(0, Flags.getNames('notNormalWeapon','nonPlayable'))

    melSet = MelSet(
        MelEdid(),
        MelBounds(),
        MelFull(),
        MelModel(),
        MelIcons(),
        MelDestructible(),
        MelFid('YNAM','pickupSound'),
        MelFid('ZNAM','dropSound'),
        MelStruct('DATA','fB3siB','speed',(_flags,'flags',0),('ammoData1',null3),
                  'value','clipRounds'),
        MelString('ONAM','shortName'),
    )
    __slots__ = melSet.getSlotsUsed()

#------------------------------------------------------------------------------
class MreAnio(MelRecord):
    """Animation Object."""

    classType = 'ANIO'

    melSet = MelSet(
        MelEdid(),
        MelModel(),
        MelFid('DATA','animationId'),
    )
    __slots__ = melSet.getSlotsUsed()

#------------------------------------------------------------------------------
class MreArma(MelRecord):
    """Armor Addon."""
    classType = 'ARMA'

    _flags = MelBipedFlags(0)
    _dnamFlags = Flags(0, Flags.getNames(
        (0,'modulatesVoice'),
    ))
    _generalFlags = Flags(0, Flags.getNames(
        (5,'powerArmor'),
        (6,'notPlayable'),
        (7,'heavyArmor')
    ))

    melSet = MelSet(
        MelEdid(),
        MelBounds(),
        MelFull(),
        MelStruct('BMDT','=2I',(_flags,'bipedFlags',0),(_generalFlags,'generalFlags',0)),
        MelModel('maleBody'),
        MelModel('maleWorld',2),
        MelIcons('maleIconPath', 'maleSmallIconPath'),
        MelModel('femaleBody',3),
        MelModel('femaleWorld',4),
        MelIcons2(),
        MelSInt32('ETYP', ('etype', -1)),
        MelStruct('DATA','IIf','value','health','weight'),
        MelStruct('DNAM','hH','ar',(_dnamFlags,'dnamFlags',0),),
    )
    __slots__ = melSet.getSlotsUsed()

#------------------------------------------------------------------------------
class MreArmo(MelRecord):
    """Armor."""
    classType = 'ARMO'

    _flags = MelBipedFlags(0, Flags.getNames())

    _dnamFlags = Flags(0, Flags.getNames(
        (0,'modulatesVoice'),
    ))
    _generalFlags = Flags(0, Flags.getNames(
        (5,'powerArmor'),
        (6,'notPlayable'),
        (7,'heavyArmor')
    ))

    melSet = MelSet(
        MelEdid(),
        MelBounds(),
        MelFull(),
        MelFid('SCRI','script'),
        MelFid('EITM','objectEffect'),
        MelStruct('BMDT','=IB3s',(_flags,'bipedFlags',0),
                  (_generalFlags,'generalFlags',0),('armoBMDT1',null3),),
        MelModel('maleBody'),
        MelModel('maleWorld',2),
        MelIcons('maleIconPath', 'maleSmallIconPath'),
        MelModel('femaleBody',3),
        MelModel('femaleWorld',4),
        MelIcons2(),
        MelString('BMCT','ragdollTemplatePath'),
        MelDestructible(),
        MelFid('REPL','repairList'),
        MelFid('BIPL','bipedModelList'),
        MelSInt32('ETYP', ('etype', -1)),
        MelFid('YNAM','pickupSound'),
        MelFid('ZNAM','dropSound'),
        MelStruct('DATA','=2if','value','health','weight'),
        MelStruct('DNAM','=hH','ar',(_dnamFlags,'dnamFlags',0),),
    )
    __slots__ = melSet.getSlotsUsed()

#------------------------------------------------------------------------------
class MreAspc(MelRecord):
    """Acoustic Space."""
    classType = 'ASPC'

    melSet = MelSet(
        MelEdid(),
        MelBounds(),
        MelFid('SNAM','soundLooping'),
        MelFid('RDAT','useSoundFromRegion'),
        MelUInt32('ANAM', 'environmentType'),
    )
    __slots__ = melSet.getSlotsUsed()

#------------------------------------------------------------------------------
class MreAvif(MelRecord):
    """Actor Value Information."""
    classType = 'AVIF'

    melSet = MelSet(
        MelEdid(),
        MelFull(),
        MelString('DESC','description'),
        MelIcons(),
        MelString('ANAM','shortName'),
    )
    __slots__ = melSet.getSlotsUsed()

#------------------------------------------------------------------------------
class MreBook(MelRecord):
    """BOOK record."""
    classType = 'BOOK'

    _flags = Flags(0,Flags.getNames('isScroll','isFixed'))

    melSet = MelSet(
        MelEdid(),
        MelBounds(),
        MelFull(),
        MelModel(),
        MelIcons(),
        MelFid('SCRI','script'),
        MelString('DESC','text'),
        MelDestructible(),
        MelOptFid('YNAM', 'pickupSound'),
        MelOptFid('ZNAM', 'dropSound'),
        MelStruct('DATA', '=BbIf',(_flags,'flags',0),('teaches',-1),'value','weight'),
    )
    __slots__ = melSet.getSlotsUsed() + ['modb']

#------------------------------------------------------------------------------
class MreBptd(MelRecord):
    """Body Part Data."""
    classType = 'BPTD'

    _flags = Flags(0, Flags.getNames('severable','ikData','ikBipedData',
        'explodable','ikIsHead','ikHeadtracking','toHitChanceAbsolute'))

    melSet = MelSet(
        MelEdid(),
        MelModel(),
        MelGroups('bodyParts',
            MelUnion({
                'BPTN': MelString('BPTN', 'partName'),
                'BPNN': MelString('BPNN', 'nodeName'),
            }),
            MelString('BPNT','vatsTarget'),
            MelString('BPNI','ikDataStartNode'),
            MelStruct('BPND','f3Bb2BH2I2fi2I7f2I2B2sf','damageMult',
                      (_flags,'flags'),'partType','healthPercent','actorValue',
                      'toHitChance','explodableChancePercent',
                      'explodableDebrisCount',(FID,'explodableDebris',0),
                      (FID,'explodableExplosion',0),'trackingMaxAngle',
                      'explodableDebrisScale','severableDebrisCount',
                      (FID,'severableDebris',0),(FID,'severableExplosion',0),
                      'severableDebrisScale','goreEffectPosTransX',
                      'goreEffectPosTransY','goreEffectPosTransZ',
                      'goreEffectPosRotX','goreEffectPosRotY','goreEffectPosRotZ',
                      (FID,'severableImpactDataSet',0),
                      (FID,'explodableImpactDataSet',0),'severableDecalCount',
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
    """Camera Shot."""
    classType = 'CAMS'

    CamsFlagsFlags = Flags(0, Flags.getNames(
            (0, 'positionFollowsLocation'),
            (1, 'rotationFollowsTarget'),
            (2, 'dontFollowBone'),
            (3, 'firstPersonCamera'),
            (4, 'noTracer'),
            (5, 'startAtTimeZero'),
        ))

    melSet = MelSet(
        MelEdid(),
        MelString('DATA','eid'),
        MelModel(),
        MelStruct('DATA','4I6f','action','location','target',
                  (CamsFlagsFlags,'flags',0),'timeMultPlayer',
                  'timeMultTarget','timeMultGlobal','maxTime','minTime',
                  'targetPctBetweenActors',),
        MelFid('MNAM','imageSpaceModifier',),
    )
    __slots__ = melSet.getSlotsUsed()

#------------------------------------------------------------------------------
class MreCell(MelRecord):
    """Cell."""
    classType = 'CELL'

    cellFlags = Flags(0, Flags.getNames(
        (0, 'isInterior'),
        (1, 'hasWater'),
        (2, 'invertFastTravel'),
        (3, 'noLODWater'),
        (5, 'publicPlace'),
        (6, 'handChanged'),
        (7, 'behaveLikeExterior')
    ))

    inheritFlags = Flags(0, Flags.getNames(
        'ambientColor',
        'directionalColor',
        'fogColor',
        'fogNear',
        'fogFar',
        'directionalRotation',
        'directionalFade',
        'clipDistance',
        'fogPower'
    ))

    # 'Force Hide Land' flags
    CellFHLFlags = Flags(0, Flags.getNames(
        (0, 'quad1'),
        (1, 'quad2'),
        (2, 'quad3'),
        (3, 'quad4'),
    ))

    melSet = MelSet(
        MelEdid(),
        MelFull(),
        MelUInt8('DATA', (cellFlags, 'flags', 0)),
        MelCoordinates('XCLC', '2iI', ('posX', None), ('posY', None),
                       (CellFHLFlags, 'fhlFlags', 0), is_optional=True,
                       old_versions={'2i'}),
        MelTruncatedStruct('XCLL', '=3Bs3Bs3Bs2f2i3f', 'ambientRed',
                           'ambientGreen', 'ambientBlue', ('unused1', null1),
                           'directionalRed', 'directionalGreen',
                           'directionalBlue', ('unused2', null1), 'fogRed',
                           'fogGreen', 'fogBlue', ('unused3', null1),
                           'fogNear', 'fogFar', 'directionalXY',
                           'directionalZ', 'directionalFade', 'fogClip',
                           'fogPower', is_optional=True,
                           old_versions={'3Bs3Bs3Bs2f2i2f'}),
        MelBase('IMPF','footstepMaterials'), #--todo rewrite specific class.
        MelFid('LTMP','lightTemplate'),
        MelOptUInt32('LNAM', (inheritFlags, 'lightInheritFlags', 0)),
        # GECK default for water is -2147483648, but by setting default here to
        # -2147483649, we force the Bashed Patch to retain the value of the
        # last mod.
        MelOptFloat('XCLW', ('waterHeight', -2147483649)),
        MelString('XNAM','waterNoiseTexture'),
        MelFidList('XCLR','regions'),
        MelFid('XCIM','imageSpace'),
        MelOptUInt8('XCET', 'xcet_p'),
        MelFid('XEZN','encounterZone'),
        MelFid('XCCM','climate'),
        MelFid('XCWT','water'),
        MelOwnership(),
        MelFid('XCAS','acousticSpace'),
        MelOptUInt8('XCMT', 'xcmt_p'),
        MelFid('XCMO','music'),
    )
    __slots__ = melSet.getSlotsUsed()

#------------------------------------------------------------------------------
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
        (4,'foods'),
        (5,'chems'),
        (6,'stimpacks'),
        (7,'lights'),
        (10,'miscItems'),
        (13,'potions'),
        (14,'training'),
        (16,'recharge'),
        (17,'repair'),))

    melSet = MelSet(
        MelEdid(),
        MelFull(),
        MelString('DESC','description'),
        MelIcon(),
        MelStruct('DATA','4i2IbB2s','tagSkill1','tagSkill2','tagSkill3',
            'tagSkill4',(_flags,'flags',0),(aiService,'services',0),
            ('trainSkill',-1),('trainLevel',0),('clasData1',null2)),
        MelStruct('ATTR', '7B', 'strength', 'perception', 'endurance',
                  'charisma', 'intelligence', 'agility', 'luck'),
    )
    __slots__ = melSet.getSlotsUsed()

#------------------------------------------------------------------------------
class MreClmt(MelRecord):
    """Climate."""
    classType = 'CLMT'

    melSet = MelSet(
        MelEdid(),
        MelArray('weather_types',
            MelStruct('WLST', 'IiI', (FID,'weather'), 'chance',
                      (FID, 'global')),
        ),
        MelString('FNAM','sunPath'),
        MelString('GNAM','glarePath'),
        MelModel(),
        MelStruct('TNAM','6B','riseBegin','riseEnd','setBegin','setEnd',
                  'volatility','phaseLength',),
    )
    __slots__ = melSet.getSlotsUsed()

#------------------------------------------------------------------------------
class MreCobj(MelRecord):
    """Constructible Object (Recipes)."""
    classType = 'COBJ'

    melSet = MelSet(
        MelEdid(),
        MelBounds(),
        MelFull(),
        MelModel(),
        MelIcons(),
        MelFid('SCRI','script'),
        MelFid('YNAM','pickupSound'),
        MelFid('ZNAM','dropSound'),
        MelStruct('DATA','if','value','weight'),
    )
    __slots__ = melSet.getSlotsUsed()

#------------------------------------------------------------------------------
class MreCont(MelRecord):
    """Container."""
    classType = 'CONT'

    _flags = Flags(0,Flags.getNames(None,'respawns'))

    melSet = MelSet(
        MelEdid(),
        MelBounds(),
        MelFull(),
        MelModel(),
        MelFid('SCRI','script'),
        MelGroups('items',
            MelStruct('CNTO','Ii',(FID,'item',None),('count',1)),
            MelOptStruct('COED','IIf',(FID,'owner',None),(FID,'glob',None),('condition',1.0)),
        ),
        MelDestructible(),
        MelStruct('DATA','=Bf',(_flags,'flags',0),'weight'),
        MelFid('SNAM','soundOpen'),
        MelFid('QNAM','soundClose'),
    )
    __slots__ = melSet.getSlotsUsed()

#------------------------------------------------------------------------------
class MreCpth(MelRecord):
    """Camera Path."""
    classType = 'CPTH'

    melSet = MelSet(
        MelEdid(),
        MelConditions(),
        MelFidList('ANAM','relatedCameraPaths',),
        MelUInt8('DATA', 'cameraZoom'),
        MelFids('SNAM','cameraShots',),
    )
    __slots__ = melSet.getSlotsUsed()

#------------------------------------------------------------------------------
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
    aiService = Flags(0, Flags.getNames(
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
    aggroflags = Flags(0, Flags.getNames('aggroRadiusBehavior',))

    melSet = MelSet(
        MelEdid(),
        MelBounds(),
        MelFull(),
        MelModel(),
        MelFids('SPLO','spells'),
        MelFid('EITM','effect'),
        MelUInt16('EAMT', 'eamt'),
        MelStrings('NIFZ','bodyParts'),
        MelBase('NIFT','nift_p'), # Texture File Hashes
        MelStruct('ACBS','=I2Hh3HfhH',(_flags,'flags',0),'fatigue',
            'barterGold',('level',1),'calcMin','calcMax','speedMultiplier',
            'karma', 'dispositionBase',
            (MreActor.TemplateFlags, 'templateFlags', 0)),
        MelGroups('factions',
            MelStruct('SNAM', 'IB3s', (FID, 'faction', None), 'rank',
                      ('unused1', 'IFZ')),
        ),
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
        MelStruct('AIDT','=5B3sIbBbBi', ('aggression', 0), ('confidence', 2),
                  ('energyLevel', 50), ('responsibility', 50), ('mood', 0),
                  ('unused_aidt', null3), (aiService, 'services', 0),
                  ('trainSkill', -1), 'trainLevel', ('assistance', 0),
                  (aggroflags, 'aggroRadiusBehavior', 0), 'aggroRadius'),
        MelFids('PKID','aiPackages'),
        MelStrings('KFFZ','animations'),
        MelStruct('DATA','=4Bh2sh7B','creatureType','combatSkill','magicSkill',
            'stealthSkill','health',('unused2',null2),'damage','strength',
            'perception','endurance','charisma','intelligence','agility',
            'luck'),
        MelUInt8('RNAM', 'attackReach'),
        MelFid('ZNAM','combatStyle'),
        MelFid('PNAM','bodyPartData'),
        MelFloat('TNAM', 'turningSpeed'),
        MelFloat('BNAM', 'baseScale'),
        MelFloat('WNAM', 'footWeight'),
        MelUInt32('NAM4', ('impactMaterialType', 0)),
        MelUInt32('NAM5', ('soundLevel', 0)),
        MelFid('CSCR','inheritsSoundsFrom'),
        MelGroups('sounds',
            MelUInt32('CSDT', 'type'),
            MelFid('CSDI','sound'),
            MelUInt8('CSDC', 'chance'),
        ),
        MelFid('CNAM','impactDataset'),
        MelFid('LNAM','meleeWeaponList'),
    )
    __slots__ = melSet.getSlotsUsed()

#------------------------------------------------------------------------------
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

    melSet = MelSet(
        MelEdid(),
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
    """Debris."""
    classType = 'DEBR'

    dataFlags = Flags(0, Flags.getNames('hasCollissionData'))

    class MelDebrData(MelStruct):
        def __init__(self):
            # Format doesn't matter, see {load,dump}Data below
            MelStruct.__init__(self, 'DATA', '', ('percentage', 0),
                               ('modPath', null1), ('flags', 0))

        def loadData(self, record, ins, sub_type, size_, readId):
            data = ins.read(size_, readId)
            (record.percentage,) = struct_unpack('B',data[0:1])
            record.modPath = data[1:-2]
            if data[-2] != null1:
                raise ModError(ins.inName,u'Unexpected subrecord: %s' % readId)
            (record.flags,) = struct_unpack('B',data[-1])

        def dumpData(self,record,out):
            data = ''
            data += struct_pack('B',record.percentage)
            data += record.modPath
            data += null1
            data += struct_pack('B',record.flags)
            out.packSub('DATA',data)

    melSet = MelSet(
        MelEdid(),
        MelGroups('models',
            MelDebrData(),
            MelBase('MODT','modt_p'),
        ),
    )
    __slots__ = melSet.getSlotsUsed()

#------------------------------------------------------------------------------
class MreDial(brec.MreDial):
    """Dialogue."""
    _DialFlags = Flags(0, Flags.getNames('rumors', 'toplevel'))

    melSet = MelSet(
        MelEdid(),
        MelFids('QSTI','quests'),
        MelFids('QSTR','rQuests'),
        MelFull(),
        MelFloat('PNAM', 'priority'),
        MelTruncatedStruct('DATA', '2B', 'dialType',
                           (_DialFlags, 'dialFlags', 0), old_versions={'B'}),
    )
    __slots__ = melSet.getSlotsUsed()

#------------------------------------------------------------------------------
class MreDobj(MelRecord):
    """Default Object Manager."""
    classType = 'DOBJ'

    melSet = MelSet(
        MelEdid(),
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
    """Door."""
    classType = 'DOOR'

    _flags = Flags(0,Flags.getNames(
        ( 1,'automatic'),
        ( 2,'hidden'),
        ( 3,'minimalUse'),
        ( 4,'slidingDoor',),
    ))

    melSet = MelSet(
        MelEdid(),
        MelBounds(),
        MelFull(),
        MelModel(),
        MelFid('SCRI','script'),
        MelDestructible(),
        MelFid('SNAM','soundOpen'),
        MelFid('ANAM','soundClose'),
        MelFid('BNAM','soundLoop'),
        MelUInt8('FNAM', (_flags, 'flags', 0)),
    )
    __slots__ = melSet.getSlotsUsed()

#------------------------------------------------------------------------------
class MreEczn(MelRecord):
    """Encounter Zone."""
    classType = 'ECZN'

    _flags = Flags(0, Flags.getNames('neverResets','matchPCBelowMinimumLevel'))

    melSet = MelSet(
        MelEdid(),
        MelStruct('DATA','=I2bBs',(FID,'owner',None),'rank','minimumLevel',
                  (_flags,'flags',0),('unused1',null1)),
    )
    __slots__ = melSet.getSlotsUsed()

#------------------------------------------------------------------------------
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
        MelString('NAM7','holesTexture'),
        MelTruncatedStruct(
            'DATA', 'B3s3I3Bs9f3Bs8f5I19f3Bs3Bs3Bs11fI5f3Bsf2I6f',
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
            old_versions={'B3s3I3Bs9f3Bs8f5I19f3Bs3Bs3Bs11fI5f3Bsf2I4f',
                          'B3s3I3Bs9f3Bs8f5I19f3Bs3Bs3Bs11fI5f3Bsf2I',
                          'B3s3I3Bs9f3Bs8f5I19f3Bs3Bs3Bs11fI',
                          'B3s3I3Bs9f3Bs8f5I19f3Bs3Bs3Bs11f',
                          'B3s3I3Bs9f3Bs8f5I19f3Bs3Bs3Bs6f'}),
    )
    __slots__ = melSet.getSlotsUsed()

#------------------------------------------------------------------------------
class MreEnch(MelRecord,MreHasEffects):
    """Object Effect."""
    classType = 'ENCH'

    _flags = Flags(0, Flags.getNames('noAutoCalc',None,'hideEffect'))

    melSet = MelSet(
        MelEdid(),
        MelFull(),
        MelStruct('ENIT','3IB3s','itemType','chargeAmount','enchantCost',
                  (_flags,'flags',0),('unused1',null3)),
        MelEffects(),
    )
    __slots__ = melSet.getSlotsUsed()

#------------------------------------------------------------------------------
class MreExpl(MelRecord):
    """Explosion."""
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
        MelEdid(),
        MelBounds(),
        MelFull(),
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
    """Eyes."""
    classType = 'EYES'

    _flags = Flags(0, Flags.getNames(
            (0, 'playable'),
            (1, 'notMale'),
            (2, 'notFemale'),
    ))

    melSet = MelSet(
        MelEdid(),
        MelFull(),
        MelIcon(),
        MelUInt8('DATA', (_flags, 'flags')),
    )
    __slots__ = melSet.getSlotsUsed()

#------------------------------------------------------------------------------
class MreFact(MelRecord):
    """Faction."""
    classType = 'FACT'

    _flags = Flags(0, Flags.getNames('hiddenFromPC','evil','specialCombat'))
    _flags2 = Flags(0, Flags.getNames('trackCrime','allowSell',))

    melSet = MelSet(
        MelEdid(),
        MelFull(),
        MelGroups('relations',
            MelStruct('XNAM', 'IiI', (FID, 'faction'), 'mod',
                      'groupCombatReaction'),
        ),
        MelTruncatedStruct('DATA', '2B2s', (_flags, 'flags', 0), 'flagsFact',
                           'unknown', old_versions={'2B', 'B'}),
        MelOptFloat('CNAM', ('crimeGoldMultiplier', None)),
        MelGroups('ranks',
            MelSInt32('RNAM', 'rank'),
            MelString('MNAM','male'),
            MelString('FNAM','female'),
            MelString('INAM','insigniaPath')
        ),
    )
    __slots__ = melSet.getSlotsUsed()

#------------------------------------------------------------------------------
class MreFlst(MelRecord):
    """FormID List."""
    classType = 'FLST'

    melSet = MelSet(
        MelEdid(),
        MelFids('LNAM','formIDInList'),
    )
    __slots__ = melSet.getSlotsUsed() + ['mergeOverLast', 'mergeSources',
                                         'items', 'deflsts']

    def __init__(self, header, ins=None, do_unpack=False):
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
        if not self.longFids or not other.longFids:
            raise StateError(_("Fids not in long format"))
        #--Remove items based on other.removes
        if other.deflsts:
            removeItems = self.items & other.deflsts
            #self.entries = [entry for entry in self.entries if entry.listId not in removeItems]
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
        self.setChanged()

#------------------------------------------------------------------------------
class MreFurn(MelRecord):
    """Furniture."""
    classType = 'FURN'

    _flags = Flags() #--Governs type of furniture and which anims are available
    #--E.g., whether it's a bed, and which of the bed entry/exit animations are available

    melSet = MelSet(
        MelEdid(),
        MelBounds(),
        MelFull(),
        MelModel(),
        MelFid('SCRI','script'),
        MelDestructible(),
        MelUInt32('MNAM', (_flags, 'activeMarkers', 0)),
    )
    __slots__ = melSet.getSlotsUsed()

#------------------------------------------------------------------------------
# Marker for organization please don't remove ---------------------------------
# GLOB ------------------------------------------------------------------------
# Defined in brec.py as class MreGlob(MelRecord) ------------------------------
#------------------------------------------------------------------------------
class MreGmst(MreGmstBase):
    """Game Setting."""
    isKeyedByEid = True # NULL fids are acceptable.

#------------------------------------------------------------------------------
class MreGras(MelRecord):
    """Grass."""
    classType = 'GRAS'

    _flags = Flags(0,Flags.getNames('vLighting','uScaling','fitSlope'))

    melSet = MelSet(
        MelEdid(),
        MelBounds(),
        MelModel(),
        MelStruct('DATA','3BsH2sI4fB3s','density','minSlope',
                  'maxSlope',('unused1',null1),'waterDistance',('unused2',null2),
                  'waterOp','posRange','heightRange','colorRange',
                  'wavePeriod',(_flags,'flags'),('unused3',null3)),
    )
    __slots__ = melSet.getSlotsUsed()

#------------------------------------------------------------------------------
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

#------------------------------------------------------------------------------
class MreHdpt(MelRecord):
    """Head Part."""
    classType = 'HDPT'

    _flags = Flags(0, Flags.getNames('playable',))

    melSet = MelSet(
        MelEdid(),
        MelFull(),
        MelModel(),
        MelUInt8('DATA', (_flags, 'flags')),
        MelFids('HNAM','extraParts'),
    )
    __slots__ = melSet.getSlotsUsed()

#------------------------------------------------------------------------------
class MreIdle(MelRecord):
    """Idle Animation."""
    classType = 'IDLE'

    melSet = MelSet(
        MelEdid(),
        MelModel(),
        MelConditions(),
        MelStruct('ANAM','II',(FID,'parent'),(FID,'prevId')),
        MelTruncatedStruct('DATA', '3BshBs', 'group', 'loopMin', 'loopMax',
                           ('unknown1', null1), 'delay', 'flags',
                           ('unknown2', null1), old_versions={'3Bsh'}),
    )
    __slots__ = melSet.getSlotsUsed()

#------------------------------------------------------------------------------
class MreIdlm(MelRecord):
    """Idle Marker."""
    classType = 'IDLM'

    _flags = Flags(0, Flags.getNames('runInSequence',None,'doOnce'))

    melSet = MelSet(
        MelEdid(),
        MelBounds(),
        MelUInt8('IDLF', (_flags, 'flags')),
        MelPartialCounter(MelTruncatedStruct(
            'IDLC', 'B3s', 'animation_count', ('unused', null3),
            old_versions={'B'}),
            counter='animation_count', counts='animations'),
        MelFloat('IDLT', 'idleTimerSetting'),
        MelFidList('IDLA','animations'),
    )
    __slots__ = melSet.getSlotsUsed()

#------------------------------------------------------------------------------
class MreImad(MelRecord):
    """Image Space Adapter."""
    classType = 'IMAD'

    _ImadDofFlags = Flags(0, Flags.getNames(
        (0, 'useTarget'),
    ))
    _ImadAnimatableFlags = Flags(0, Flags.getNames(
        (0, 'animatable'),
    ))
    _ImadRadialBlurFlags = Flags(0, Flags.getNames(
        (0, 'useTarget')
    ))

    melSet = MelSet(
        MelEdid(),
        MelStruct('DNAM', 'If49I2f8I', (_ImadAnimatableFlags, 'aniFlags', 0),
                  'duration', 'eyeAdaptSpeedMult', 'eyeAdaptSpeedAdd',
                  'bloomBlurRadiusMult', 'bloomBlurRadiusAdd',
                  'bloomThresholdMult', 'bloomThresholdAdd', 'bloomScaleMult',
                  'bloomScaleAdd', 'targetLumMinMult', 'targetLumMinAdd',
                  'targetLumMaxMult', 'targetLumMaxAdd', 'sunlightScaleMult',
                  'sunlightScaleAdd', 'skyScaleMult', 'skyScaleAdd',
                  'unknown08Mult', 'unknown48Add', 'unknown09Mult',
                  'unknown49Add', 'unknown0AMult', 'unknown4AAdd',
                  'unknown0BMult', 'unknown4BAdd', 'unknown0CMult',
                  'unknown4CAdd', 'unknown0DMult', 'unknown4DAdd',
                  'unknown0EMult', 'unknown4EAdd', 'unknown0FMult',
                  'unknown4FAdd', 'unknown10Mult', 'unknown50Add',
                  'saturationMult', 'saturationAdd', 'brightnessMult',
                  'brightnessAdd', 'contrastMult', 'contrastAdd',
                  'unknown14Mult', 'unknown54Add',
                  'tintColor', 'blurRadius', 'doubleVisionStrength',
                  'radialBlurStrength', 'radialBlurRampUp', 'radialBlurStart',
                  (_ImadRadialBlurFlags, 'radialBlurFlags', 0),
                  'radialBlurCenterX', 'radialBlurCenterY', 'dofStrength',
                  'dofDistance', 'dofRange', (_ImadDofFlags, 'dofFlags', 0),
                  'radialBlurRampDown', 'radialBlurDownStart', 'fadeColor',
                  'motionBlurStrength'),
        MelValueInterpolator('BNAM', 'blurRadiusInterp'),
        MelValueInterpolator('VNAM', 'doubleVisionStrengthInterp'),
        MelColorInterpolator('TNAM', 'tintColorInterp'),
        MelColorInterpolator('NAM3', 'fadeColorInterp'),
        MelValueInterpolator('RNAM', 'radialBlurStrengthInterp'),
        MelValueInterpolator('SNAM', 'radialBlurRampUpInterp'),
        MelValueInterpolator('UNAM', 'radialBlurStartInterp'),
        MelValueInterpolator('NAM1', 'radialBlurRampDownInterp'),
        MelValueInterpolator('NAM2', 'radialBlurDownStartInterp'),
        MelValueInterpolator('WNAM', 'dofStrengthInterp'),
        MelValueInterpolator('XNAM', 'dofDistanceInterp'),
        MelValueInterpolator('YNAM', 'dofRangeInterp'),
        MelValueInterpolator('NAM4', 'motionBlurStrengthInterp'),
        MelValueInterpolator('\x00IAD', 'eyeAdaptSpeedMultInterp'),
        MelValueInterpolator('\x40IAD', 'eyeAdaptSpeedAddInterp'),
        MelValueInterpolator('\x01IAD', 'bloomBlurRadiusMultInterp'),
        MelValueInterpolator('\x41IAD', 'bloomBlurRadiusAddInterp'),
        MelValueInterpolator('\x02IAD', 'bloomThresholdMultInterp'),
        MelValueInterpolator('\x42IAD', 'bloomThresholdAddInterp'),
        MelValueInterpolator('\x03IAD', 'bloomScaleMultInterp'),
        MelValueInterpolator('\x43IAD', 'bloomScaleAddInterp'),
        MelValueInterpolator('\x04IAD', 'targetLumMinMultInterp'),
        MelValueInterpolator('\x44IAD', 'targetLumMinAddInterp'),
        MelValueInterpolator('\x05IAD', 'targetLumMaxMultInterp'),
        MelValueInterpolator('\x45IAD', 'targetLumMaxAddInterp'),
        MelValueInterpolator('\x06IAD', 'sunlightScaleMultInterp'),
        MelValueInterpolator('\x46IAD', 'sunlightScaleAddInterp'),
        MelValueInterpolator('\x07IAD', 'skyScaleMultInterp'),
        MelValueInterpolator('\x47IAD', 'skyScaleAddInterp'),
        MelBase('\x08IAD', 'unknown08IAD'),
        MelBase('\x48IAD', 'unknown48IAD'),
        MelBase('\x09IAD', 'unknown09IAD'),
        MelBase('\x49IAD', 'unknown49IAD'),
        MelBase('\x0AIAD', 'unknown0aIAD'),
        MelBase('\x4AIAD', 'unknown4aIAD'),
        MelBase('\x0BIAD', 'unknown0bIAD'),
        MelBase('\x4BIAD', 'unknown4bIAD'),
        MelBase('\x0CIAD', 'unknown0cIAD'),
        MelBase('\x4CIAD', 'unknown4cIAD'),
        MelBase('\x0DIAD', 'unknown0dIAD'),
        MelBase('\x4DIAD', 'unknown4dIAD'),
        MelBase('\x0EIAD', 'unknown0eIAD'),
        MelBase('\x4EIAD', 'unknown4eIAD'),
        MelBase('\x0FIAD', 'unknown0fIAD'),
        MelBase('\x4FIAD', 'unknown4fIAD'),
        MelBase('\x10IAD', 'unknown10IAD'),
        MelBase('\x50IAD', 'unknown50IAD'),
        MelValueInterpolator('\x11IAD', 'saturationMultInterp'),
        MelValueInterpolator('\x51IAD', 'saturationAddInterp'),
        MelValueInterpolator('\x12IAD', 'brightnessMultInterp'),
        MelValueInterpolator('\x52IAD', 'brightnessAddInterp'),
        MelValueInterpolator('\x13IAD', 'contrastMultInterp'),
        MelValueInterpolator('\x53IAD', 'contrastAddInterp'),
        MelBase('\x14IAD', 'unknown14IAD'),
        MelBase('\x54IAD', 'unknown54IAD'),
    )
    __slots__ = melSet.getSlotsUsed()

#------------------------------------------------------------------------------
class MreImgs(MelRecord):
    """Image Space."""
    classType = 'IMGS'

    _dnam_flags = Flags(0, Flags.getNames(
        'saturation',
        'contrast',
        'tint',
        'brightness'
    ))

    # Struct elements shared by all three DNAM alternatives. Note that we can't
    # just use MelTruncatedStruct, because upgrading the format breaks interior
    # lighting for some reason.
    ##: If this becomes common, extract into dedicated class
    _dnam_common = [
        'eyeAdaptSpeed', 'blurRadius', 'blurPasses', 'emissiveMult',
        'targetLUM', 'upperLUMClamp', 'brightScale', 'brightClamp',
        'lumRampNoTex', 'lumRampMin', 'lumRampMax', 'sunlightDimmer',
        'grassDimmer', 'treeDimmer', 'skinDimmer', 'bloomBlurRadius',
        'bloomAlphaMultInterior', 'bloomAlphaMultExterior', 'getHitBlurRadius',
        'getHitBlurDampingConstant', 'getHitDampingConstant',
        'nightEyeTintRed', 'nightEyeTintGreen', 'nightEyeTintBlue',
        'nightEyeBrightness', 'cinematicSaturation', 'cinematicAvgLumValue',
        'cinematicValue', 'cinematicBrightnessValue', 'cinematicTintRed',
        'cinematicTintGreen', 'cinematicTintBlue', 'cinematicTintValue',
    ]

    melSet = MelSet(
        MelEdid(),
        MelUnion({
            152: MelStruct(
                'DNAM', '33f4s4s4s4sB3s', *(_dnam_common + [
                    ('unused1', null4), ('unused2', null4), ('unused3', null4),
                    ('unused4',null4), (_dnam_flags, 'dnam_flags'),
                    ('unused5', null3),
                ])),
            148: MelStruct(
                'DNAM', '33f4s4s4s4s', *(_dnam_common + [
                    ('unused1', null4), ('unused2', null4), ('unused3', null4),
                    ('unused4',null4),
                ])),
            132: MelStruct('DNAM', '33f', *_dnam_common),
        }, decider=SizeDecider()),
    )
    __slots__ = melSet.getSlotsUsed()

#------------------------------------------------------------------------------
class MreInfo(MelRecord):
    """Dialog Response."""
    classType = 'INFO'

    _flags = Flags(0,Flags.getNames(
        'goodbye','random','sayOnce','runImmediately','infoRefusal','randomEnd',
        'runForRumors','speechChallenge',))
    _flags2 = Flags(0,Flags.getNames(
        'sayOnceADay','alwaysDarken',))

    melSet = MelSet(
        MelTruncatedStruct('DATA', '4B', 'dialType', 'nextSpeaker',
                           (_flags, 'flags'), (_flags2, 'flagsInfo'),
                           old_versions={'2B'}),
        MelFid('QSTI','quests'),
        MelFid('TPIC','topic'),
        MelFid('PNAM','prevInfo'),
        MelFids('NAME','addTopics'),
        MelGroups('responses',
            MelStruct('TRDT','Ii4sB3sIB3s','emotionType','emotionValue',('unused1',null4),'responseNum',('unused2','\xcd\xcd\xcd'),
                      (FID,'sound'),'flags',('unused3','\xcd\xcd\xcd')),
            MelString('NAM1','responseText'),
            MelString('NAM2','actorNotes'),
            MelString('NAM3','edits'),
            MelFid('SNAM','speakerAnimation'),
            MelFid('LNAM','listenerAnimation'),
        ),
        MelConditions(),
        MelFids('TCLT','choices'),
        MelFids('TCLF','linksFrom'),
        MelGroup('scriptBegin',
            MelEmbeddedScript(),
        ),
        MelGroup('scriptEnd',
            MelBase('NEXT','marker'),
            MelEmbeddedScript(),
        ),
        MelFid('SNDD','sndd_p'),
        MelString('RNAM','prompt'),
        MelFid('ANAM','speaker'),
        MelFid('KNAM','acterValuePeak'),
        MelUInt32('DNAM', 'speechChallenge')
    )
    __slots__ = melSet.getSlotsUsed()

#------------------------------------------------------------------------------
class MreIngr(MelRecord,MreHasEffects):
    """Ingredient."""
    classType = 'INGR'

    _flags = Flags(0, Flags.getNames('noAutoCalc','isFood'))

    melSet = MelSet(
        MelEdid(),
        MelBounds(),
        MelFull(),
        MelModel(),
        MelIcon(),
        MelFid('SCRI','script'),
        MelSInt32('ETYP', ('etype', -1)),
        MelFloat('DATA', 'weight'),
        MelStruct('ENIT','iB3s','value',(_flags,'flags',0),('unused1',null3)),
        MelEffects(),
    )
    __slots__ = melSet.getSlotsUsed()

#------------------------------------------------------------------------------
class MreIpct(MelRecord):
    """Impact."""
    classType = 'IPCT'

    DecalDataFlags = Flags(0, Flags.getNames(
            (0, 'parallax'),
            (0, 'alphaBlending'),
            (0, 'alphaTesting'),
        ))

    melSet = MelSet(
        MelEdid(),
        MelModel(),
        MelStruct('DATA','fIffII','effectDuration','effectOrientation',
                  'angleThreshold','placementRadius','soundLevel','flags'),
        MelOptStruct('DODT','7fBB2s3Bs','minWidth','maxWidth','minHeight',
                     'maxHeight','depth','shininess','parallaxScale',
                     'parallaxPasses',(DecalDataFlags,'decalFlags',0),
                     ('unused1',null2),'red','green','blue',('unused2',null1)),
        MelFid('DNAM','textureSet'),
        MelFid('SNAM','sound1'),
        MelFid('NAM1','sound2'),
    )
    __slots__ = melSet.getSlotsUsed()

#------------------------------------------------------------------------------
class MreIpds(MelRecord):
    """Impact Dataset."""
    classType = 'IPDS'

    melSet = MelSet(
        MelEdid(),
        MelTruncatedStruct(
            'DATA', '12I', (FID, 'stone', 0), (FID, 'dirt', 0),
            (FID, 'grass', 0), (FID, 'glass', 0), (FID, 'metal', 0),
            (FID, 'wood', 0), (FID, 'organic', 0), (FID, 'cloth', 0),
            (FID, 'water', 0), (FID, 'hollowMetal', 0), (FID, 'organicBug', 0),
            (FID, 'organicGlow', 0), old_versions={'10I', '9I'}),
    )
    __slots__ = melSet.getSlotsUsed()

#------------------------------------------------------------------------------
class MreKeym(MelRecord):
    """Key."""
    classType = 'KEYM'

    melSet = MelSet(
        MelEdid(),
        MelBounds(),
        MelFull(),
        MelModel(),
        MelIcons(),
        MelFid('SCRI','script'),
        MelDestructible(),
        MelFid('YNAM','pickupSound'),
        MelFid('ZNAM','dropSound'),
        MelStruct('DATA','if','value','weight'),
    )
    __slots__ = melSet.getSlotsUsed()

#------------------------------------------------------------------------------
class MreLgtm(MelRecord):
    """Lighting Template."""
    classType = 'LGTM'

    melSet = MelSet(
        MelEdid(),
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
    """Light."""
    classType = 'LIGH'

    _flags = Flags(0, Flags.getNames('dynamic','canTake','negative','flickers',
        'unk1','offByDefault','flickerSlow','pulse','pulseSlow','spotLight','spotShadow'))

    melSet = MelSet(
        MelEdid(),
        MelBounds(),
        MelModel(),
        MelFid('SCRI','script'),
        MelDestructible(),
        MelFull(),
        MelIcon(),
        MelStruct('DATA','iI3BsI2fIf','duration','radius','red','green','blue',
                  ('unused1',null1),(_flags,'flags',0),'falloff','fov','value',
                  'weight'),
        MelOptFloat('FNAM', ('fade', None)),
        MelFid('SNAM','sound'),
    )
    __slots__ = melSet.getSlotsUsed()

#------------------------------------------------------------------------------
class MreLscr(MelRecord):
    """Load Screen."""
    classType = 'LSCR'

    melSet = MelSet(
        MelEdid(),
        MelIcon(),
        MelString('DESC','text'),
        MelGroups('locations',
            MelStruct('LNAM', 'I8s', (FID, 'cell'),
                      ('unused1', null4 + null4)),
        ),
    )
    __slots__ = melSet.getSlotsUsed()

#------------------------------------------------------------------------------
class MreLtex(MelRecord):
    """Landscape Texture."""
    classType = 'LTEX'

    melSet = MelSet(
        MelEdid(),
        MelIcon(),
        MelFid('TNAM', 'texture'),
        MelOptStruct('HNAM','3B','materialType','friction','restitution'),
        MelOptUInt8('SNAM', 'specular'),
        MelFids('GNAM', 'grass'),
    )
    __slots__ = melSet.getSlotsUsed()

#------------------------------------------------------------------------------
class MreLvlc(MreLeveledList):
    """Leveled Creature."""
    classType = 'LVLC'
    __slots__ = []

#------------------------------------------------------------------------------
class MreLvli(MreLeveledList):
    """Leveled Item."""
    classType = 'LVLI'
    __slots__ = []

#------------------------------------------------------------------------------
class MreLvln(MreLeveledList):
    """Leveled NPC."""
    classType = 'LVLN'
    __slots__ = []

#------------------------------------------------------------------------------
class MreMesg(MelRecord):
    """Message."""
    classType = 'MESG'

    MesgTypeFlags = Flags(0, Flags.getNames(
            (0, 'messageBox'),
            (1, 'autoDisplay'),
        ))

    melSet = MelSet(
        MelEdid(),
        MelString('DESC','description'),
        MelFull(),
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
        MelUInt32('DNAM', (MesgTypeFlags, 'flags', 0)),
        MelUInt32('TNAM', 'displayTime'),
        MelGroups('menuButtons',
            MelString('ITXT','buttonText'),
            MelConditions(),
        ),
    )
    __slots__ = melSet.getSlotsUsed()

#------------------------------------------------------------------------------
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
        MelPartialCounter(MelStruct(
            'DATA','IfI2iH2sIf6I2fIi', (_flags, 'flags'), 'baseCost',
            (FID, 'associated'), 'school', 'resistValue', 'counterEffectCount',
            ('unused1', null2), (FID, 'light', 0), 'projectileSpeed',
            (FID, 'effectShader' ,0), (FID, 'objectDisplayShader', 0),
            (FID, 'castingSound', 0), (FID, 'boltSound', 0),
            (FID, 'hitSound', 0), (FID, 'areaSound', 0),
            ('cefEnchantment', 0.0), ('cefBarter', 0.0), 'archType',
            'actorValue'),
            counter='counterEffectCount', counts='counterEffects'),
        MelGroups('counterEffects',
            MelOptFid('ESCE', 'counterEffectCode', 0),
        ),
    )
    __slots__ = melSet.getSlotsUsed()

#------------------------------------------------------------------------------
class MreMicn(MelRecord):
    """Menu Icon."""
    classType = 'MICN'
    melSet = MelSet(
        MelEdid(),
        MelIcons(),
    )
    __slots__ = melSet.getSlotsUsed()

#------------------------------------------------------------------------------
class MreMisc(MelRecord):
    """Misc. Item."""
    classType = 'MISC'

    melSet = MelSet(
        MelEdid(),
        MelBounds(),
        MelFull(),
        MelModel(),
        MelIcons(),
        MelFid('SCRI','script'),
        MelDestructible(),
        MelFid('YNAM','pickupSound'),
        MelFid('ZNAM','dropSound'),
        MelStruct('DATA','if','value','weight'),
    )
    __slots__ = melSet.getSlotsUsed()

#------------------------------------------------------------------------------
class MreMstt(MelRecord):
    """Moveable Static."""
    classType = 'MSTT'

    melSet = MelSet(
        MelEdid(),
        MelBounds(),
        MelFull(),
        MelModel(),
        MelDestructible(),
        MelBase('DATA','data_p'),
        MelFid('SNAM','sound'),
    )
    __slots__ = melSet.getSlotsUsed()

#------------------------------------------------------------------------------
class MreMusc(MelRecord):
    """Music Type."""
    classType = 'MUSC'

    melSet = MelSet(
        MelEdid(),
        MelString('FNAM','filename'),
    )
    __slots__ = melSet.getSlotsUsed()

#------------------------------------------------------------------------------
class MreNavi(MelRecord):
    """Navigation Mesh Info Map."""
    classType = 'NAVI'

    melSet = MelSet(
        MelEdid(),
        MelUInt32('NVER', ('version', 11)),
        MelGroups('nav_map_infos',
            # Contains fids, but we probably won't ever be able to merge NAVI,
            # so leaving this as MelBase for now
            MelBase('NVMI', 'nav_map_info'),
        ),
        MelFidList('NVCI','unknownDoors',),
    )
    __slots__ = melSet.getSlotsUsed()

#------------------------------------------------------------------------------
class MreNavm(MelRecord):
    """Navigation Mesh."""
    classType = 'NAVM'

    melSet = MelSet(
        MelEdid(),
        MelUInt32('NVER', ('version', 11)),
        MelStruct('DATA','I5I',(FID,'cell'),'vertexCount','triangleCount','enternalConnectionsCount','nvcaCount','doorsCount'),
        MelArray('vertices',
            MelStruct('NVVX', '3f', 'vertexX', 'vertexY', 'vertexZ'),
        ),
        MelArray('triangles',
            MelStruct('NVTR', '6hI', 'vertex0', 'vertex1', 'vertex2',
                      'triangle0', 'triangle1', 'triangle2', 'flags'),
        ),
        MelOptSInt16('NVCA', 'nvca_p'),
        MelArray('doors',
            MelStruct('NVDP', 'IH2s', (FID, 'doorReference'), 'door_triangle',
                      'doorUnknown'),
        ),
        MelBase('NVGD','nvgd_p'),
        MelArray('externalConnections',
            MelStruct('NVEX', '=4sIH', 'nvexUnknown', (FID, 'navigationMesh'),
                      'triangle'),
        ),
    )
    __slots__ = melSet.getSlotsUsed()

#------------------------------------------------------------------------------
class MreNote(MelRecord):
    """Note."""
    classType = 'NOTE'

    melSet = MelSet(
        MelEdid(),
        MelBounds(),
        MelFull(),
        MelModel(),
        MelIcons(),
        MelFid('YNAM','pickupSound'),
        MelFid('ZNAM','dropSound'),
        MelUInt8('DATA', 'dataType'),
        MelFidList('ONAM','quests'),
        MelString('XNAM','texture'),
        MelUnion({
            3: MelFid('TNAM', 'textTopic'),
        }, decider=AttrValDecider('dataType'),
            fallback=MelString('TNAM', 'textTopic')),
        MelFid('SNAM', 'soundNpc'),
    )
    __slots__ = melSet.getSlotsUsed()

#------------------------------------------------------------------------------
class MreNpc(MreActor):
    """Non-Player Character."""
    classType = 'NPC_'

    _flags = Flags(0, Flags.getNames(
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
    aiService = Flags(0, Flags.getNames(
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
    aggroflags = Flags(0, Flags.getNames('aggroRadiusBehavior',))

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

        def dumpData(self,record,out):
            recordGetAttr = record.__getattribute__
            values = [recordGetAttr('health')]+recordGetAttr('attributes')
            if len(recordGetAttr('attributes')) == 7:
                out.packSub(self.subType,'=I7B',*values)
            else:
                out.packSub(self.subType,'=I21B',*values)

    class MelNpcDnam(MelStruct):
        """Convert npc stats into skills."""
        def loadData(self, record, ins, sub_type, size_, readId):
            unpacked = list(ins.unpack('=28B', size_, readId))
            recordSetAttr = record.__setattr__
            recordSetAttr('skillValues',unpacked[:14])
            recordSetAttr('skillOffsets',unpacked[14:])

        def dumpData(self,record,out):
            recordGetAttr = record.__getattribute__
            values = recordGetAttr('skillValues')+recordGetAttr('skillOffsets')
            out.packSub(self.subType,'=28B',*values)

    melSet = MelSet(
        MelEdid(),
        MelBounds(),
        MelFull(),
        MelModel(),
        MelStruct('ACBS','=I2Hh3Hf2H',
            (_flags,'flags',0),'fatigue','barterGold',
            ('level',1),'calcMin','calcMax','speedMultiplier','karma',
            'dispositionBase', (MreActor.TemplateFlags, 'templateFlags', 0)),
        MelGroups('factions',
            MelStruct('SNAM', 'IB3s', (FID, 'faction', None), 'rank',
                      ('unused1', 'ODB')),
        ),
        MelFid('INAM','deathItem'),
        MelFid('VTCK','voice'),
        MelFid('TPLT','template'),
        MelFid('RNAM','race'),
        MelFid('EITM','unarmedAttackEffect'),
        MelUInt16('EAMT', 'unarmedAttackAnimation'),
        MelDestructible(),
        MelFids('SPLO','spells'),
        MelFid('SCRI','script'),
        MelGroups('items',
            MelStruct('CNTO','Ii',(FID,'item',None),('count',1)),
            MelOptStruct('COED','IIf',(FID,'owner',None),(FID,'glob',None),('condition',1.0)),
        ),
        MelStruct('AIDT','=5B3sIbBbBi', ('aggression', 0), ('confidence',2),
                  ('energyLevel', 50),('responsibility', 50), ('mood', 0),
                  ('unused_aidt', null3),(aiService, 'services', 0),
                  ('trainSkill', -1), 'trainLevel', ('assistance', 0),
                  (aggroflags, 'aggroRadiusBehavior', 0), 'aggroRadius'),
        MelFids('PKID','aiPackages'),
        MelStrings('KFFZ','animations'),
        MelFid('CNAM','iclass'),
        MelNpcData('DATA','','health',('attributes',[0]*21)),
        MelFids('PNAM','headParts'),
        MelNpcDnam('DNAM','',('skillValues',[0]*14),('skillOffsets',[0]*14)),
        MelFid('HNAM','hair'),
        MelOptFloat('LNAM', ('hairLength', 1)),
        MelFid('ENAM','eye'), ####fid Array
        MelStruct('HCLR','3Bs','hairRed','hairBlue','hairGreen',('unused3',null1)),
        MelFid('ZNAM','combatStyle'),
        MelUInt32('NAM4', ('impactMaterialType', 0)),
        MelBase('FGGS','fggs_p'), ####FaceGen Geometry-Symmetric
        MelBase('FGGA','fgga_p'), ####FaceGen Geometry-Asymmetric
        MelBase('FGTS','fgts_p'), ####FaceGen Texture-Symmetric
        MelUInt16('NAM5', ('unknown', 0)),
        MelFloat('NAM6', ('height', 0)),
        MelFloat('NAM7', ('weight', 0)),
    )
    __slots__ = melSet.getSlotsUsed()

#------------------------------------------------------------------------------
class MrePack(MelRecord):
    """Package."""
    classType = 'PACK'

    _flags = Flags(0,Flags.getNames(
        'offersServices','mustReachLocation','mustComplete','lockAtStart',
        'lockAtEnd','lockAtLocation','unlockAtStart','unlockAtEnd',
        'unlockAtLocation','continueIfPcNear','oncePerDay',None,
        'skipFallout','alwaysRun',None,None,
        None,'alwaysSneak','allowSwimming','allowFalls',
        'unequipArmor','unequipWeapons','defensiveCombat','useHorse',
        'noIdleAnims',))

    class MelIdleHandler(MelGroup):
        """Occurs three times in PACK, so moved here to deduplicate the
        definition a bit."""
        # The subrecord type used for the marker
        _attr_lookup = {
            'on_begin': 'POBA',
            'on_change': 'POCA',
            'on_end': 'POEA',
        }
        _variableFlags = Flags(0, Flags.getNames('isLongOrShort'))

        def __init__(self, attr):
            MelGroup.__init__(self, attr,
                MelBase(self._attr_lookup[attr], attr + '_marker'),
                MelFid('INAM', 'idle_anim'),
                MelEmbeddedScript(),
                MelFid('TNAM', 'topic'),
            )

    melSet = MelSet(
        MelEdid(),
        MelTruncatedStruct('PKDT', 'I2HI', (_flags, 'flags'), 'aiType',
                           'falloutBehaviorFlags', 'typeSpecificFlags',
                           old_versions={'I2H'}),
        MelUnion({
            0: MelOptStruct('PLDT', 'iIi', 'locType', (FID, 'locId'),
                            'locRadius'),
            1: MelOptStruct('PLDT', 'iIi', 'locType', (FID, 'locId'),
                            'locRadius'),
            2: MelOptStruct('PLDT', 'i4si', 'locType', 'locId', 'locRadius'),
            3: MelOptStruct('PLDT', 'i4si', 'locType', 'locId', 'locRadius'),
            4: MelOptStruct('PLDT', 'iIi', 'locType', (FID, 'locId'),
                            'locRadius'),
            5: MelOptStruct('PLDT', 'iIi', 'locType', 'locId', 'locRadius'),
            6: MelOptStruct('PLDT', 'i4si', 'locType', 'locId', 'locRadius'),
            7: MelOptStruct('PLDT', 'i4si', 'locType', 'locId', 'locRadius'),
        }, decider=PartialLoadDecider(
            loader=MelSInt32('PLDT', 'locType'),
            decider=AttrValDecider('locType'),
        )),
        MelUnion({
            0: MelOptStruct('PLD2', 'iIi', 'locType2', (FID, 'locId2'),
                            'locRadius2'),
            1: MelOptStruct('PLD2', 'iIi', 'locType2', (FID, 'locId2'),
                            'locRadius2'),
            2: MelOptStruct('PLD2', 'i4si', 'locType2', 'locId2',
                            'locRadius2'),
            3: MelOptStruct('PLD2', 'i4si', 'locType2', 'locId2',
                            'locRadius2'),
            4: MelOptStruct('PLD2', 'iIi', 'locType2', (FID, 'locId2'),
                            'locRadius2'),
            5: MelOptStruct('PLD2', 'iIi', 'locType2', 'locId2', 'locRadius2'),
            6: MelOptStruct('PLD2', 'i4si', 'locType2', 'locId2',
                            'locRadius2'),
            7: MelOptStruct('PLD2', 'i4si', 'locType2', 'locId2',
                            'locRadius2'),
        }, decider=PartialLoadDecider(
            loader=MelSInt32('PLD2', 'locType2'),
            decider=AttrValDecider('locType2'),
        )),
        MelStruct('PSDT','2bBbi','month','day','date','time','duration'),
        MelUnion({
            0: MelTruncatedStruct(
                'PTDT', 'iIif', 'targetType', (FID, 'targetId'), 'targetCount',
                'targetUnknown1', is_optional=True, old_versions={'iIi'}),
            1: MelTruncatedStruct(
                'PTDT', 'iIif', 'targetType', (FID, 'targetId'), 'targetCount',
                'targetUnknown1', is_optional=True, old_versions={'iIi'}),
            2: MelTruncatedStruct(
                'PTDT', 'iIif', 'targetType', 'targetId', 'targetCount',
                'targetUnknown1', is_optional=True, old_versions={'iIi'}),
            3: MelTruncatedStruct(
                'PTDT', 'i4sif', 'targetType', 'targetId', 'targetCount',
                'targetUnknown1', is_optional=True, old_versions={'iIi'}),
        }, decider=PartialLoadDecider(
            loader=MelSInt32('PTDT', 'targetType'),
            decider=AttrValDecider('targetType'),
        )),
        MelConditions(),
        MelGroup('idleAnimations',
            MelUInt8('IDLF', 'animationFlags'),
            MelPartialCounter(MelStruct('IDLC', 'B3s', 'animation_count',
                                        'unused'),
                              counter='animation_count', counts='animations'),
            MelFloat('IDLT', 'idleTimerSetting'),
            MelFidList('IDLA','animations'),
            MelBase('IDLB','idlb_p'),
        ),
        MelBase('PKED','eatMarker'),
        MelOptUInt32('PKE2', 'escortDistance'),
        MelFid('CNAM','combatStyle'),
        MelOptFloat('PKFD', 'followStartLocationTrigerRadius'),
        MelBase('PKPT','patrolFlags'), # byte or short
        MelOptStruct('PKW3','IBB3Hff4s','weaponFlags','fireRate','fireCount','numBursts',
                     'shootPerVolleysMin','shootPerVolleysMax','pauseBetweenVolleysMin','pauseBetweenVolleysMax','weaponUnknown'),
        MelUnion({
            0: MelTruncatedStruct(
                'PTD2', 'iIif', 'targetType2', (FID, 'targetId2'),
                'targetCount2', 'targetUnknown2', is_optional=True,
                old_versions={'iIi'}),
            1: MelTruncatedStruct(
                'PTD2', 'iIif', 'targetType2', (FID, 'targetId2'),
                'targetCount2', 'targetUnknown2', is_optional=True,
                old_versions={'iIi'}),
            2: MelTruncatedStruct(
                'PTD2', 'iIif', 'targetType2', 'targetId2', 'targetCount2',
                'targetUnknown2', is_optional=True, old_versions={'iIi'}),
            3: MelTruncatedStruct(
                'PTD2', 'i4sif', 'targetType2', 'targetId2', 'targetCount2',
                'targetUnknown2', is_optional=True, old_versions={'iIi'}),
        }, decider=PartialLoadDecider(
            loader=MelSInt32('PTD2', 'targetType2'),
            decider=AttrValDecider('targetType2'),
        )),
        MelBase('PUID','useItemMarker'),
        MelBase('PKAM','ambushMarker'),
        MelTruncatedStruct('PKDD', 'f2I4sI4s', 'dialFov', 'dialTopic',
                           'dialFlags', 'dialUnknown1', 'dialType',
                           'dialUnknown2', is_optional=True,
                           old_versions={'f2I4sI', 'f2I4s', 'f2I'}),
        MelIdleHandler('on_begin'),
        MelIdleHandler('on_end'),
        MelIdleHandler('on_change'),
    ).with_distributor({
        'POBA': {
            'INAM|SCHR|SCDA|SCTX|SLSD|SCVR|SCRO|SCRV|TNAM': 'on_begin',
        },
        'POEA': {
            'INAM|SCHR|SCDA|SCTX|SLSD|SCVR|SCRO|SCRV|TNAM': 'on_begin',
        },
        'POCA': {
            'INAM|SCHR|SCDA|SCTX|SLSD|SCVR|SCRO|SCRV|TNAM': 'on_begin',
        },
    })
    __slots__ = melSet.getSlotsUsed()

#------------------------------------------------------------------------------
class MrePerk(MelRecord):
    """Perk."""
    classType = 'PERK'

    _PerkScriptFlags = Flags(0, Flags.getNames(
        (0, 'runImmediately'),
    ))

    melSet = MelSet(
        MelEdid(),
        MelFull(),
        MelString('DESC','description'),
        MelIcons(),
        MelConditions(),
        MelTruncatedStruct('DATA', '5B', ('trait', 0), ('minLevel', 0),
                           ('ranks', 0), ('playable', 0), ('hidden', 0),
                           old_versions={'4B'}),
        MelGroups('effects',
            MelStruct('PRKE', '3B', 'type', 'rank', 'priority'),
            MelUnion({
                0: MelStruct('DATA', 'IB3s', (FID, 'quest'), 'quest_stage',
                             'unusedDATA'),
                1: MelFid('DATA', 'ability'),
                2: MelStruct('DATA', '3B', 'entry_point', 'function',
                             'perk_conditions_tab_count'),
            }, decider=AttrValDecider('type')),
            MelGroups('effectConditions',
                MelSInt8('PRKC', 'runOn'),
                MelConditions(),
            ),
            MelGroups('effectParams',
                # EPFT has the following meanings:
                #  0: Unknown
                #  1: EPFD=float
                #  2: EPFD=float, float
                #  3: EPFD=fid (LVLI)
                #  4: EPFD=Null (Script)
                # TODO(inf) there is a special case: If EPFT is 2 and
                #  DATA/function is 5, then:
                #  EPFD=uint32, float
                #  See commented out skeleton below - needs '../' syntax
                MelUInt8('EPFT', 'function_parameter_type'),
                MelUnion({
                    0: MelBase('EPFD', 'param1'),
                    1: MelFloat('EPFD', 'param1'),
                    2: MelStruct('EPFD', 'If', 'param1', 'param2'),
#                    2: MelUnion({
#                        5: MelStruct('EPFD', 'If', 'param1', 'param2'),
#                    }, decider=AttrValDecider('../function',
#                                                 assign_missing=-1),
#                        fallback=MelStruct('EPFD', '2f', 'param1', 'param2')),
                    3: MelFid('EPFD', 'param1'),
                    4: MelBase('EPFD', 'param1'),
                }, decider=AttrValDecider('function_parameter_type')),
                MelString('EPF2','buttonLabel'),
                MelUInt16('EPF3', (_PerkScriptFlags, 'script_flags', 0)),
                MelEmbeddedScript(),
            ),
            MelBase('PRKF','footer'),
        ),
    ).with_distributor({
        'DESC': {
            'CTDA|CIS1|CIS2': 'conditions',
            'DATA': 'trait',
        },
        'PRKE': {
            'CTDA|CIS1|CIS2|DATA': 'effects',
        },
    })
    __slots__ = melSet.getSlotsUsed()

#------------------------------------------------------------------------------
class MrePgre(MelRecord):
    """Placed Grenade."""
    classType = 'PGRE'

    _flags = Flags(0, Flags.getNames('oppositeParent'))
    _watertypeFlags = Flags(0, Flags.getNames('reflection','refraction'))

    melSet = MelSet(
        MelEdid(),
        MelFid('NAME','base'),
        MelFid('XEZN','encounterZone'),
        MelBase('XRGD','ragdollData'),
        MelBase('XRGB','ragdollBipedData'),
        MelGroup('patrolData',
            MelFloat('XPRD', 'idleTime'),
            MelBase('XPPA','patrolScriptMarker'),
            MelFid('INAM', 'idle'),
            MelEmbeddedScript(),
            MelFid('TNAM','topic'),
        ),
        MelOwnership(),
        MelSInt32('XCNT', 'count'),
        MelFloat('XRDS', 'radius'),
        MelFloat('XHLP', 'health'),
        MelGroups('reflectedRefractedBy',
            MelStruct('XPWR','2I',(FID,'waterReference'),(_watertypeFlags,'waterFlags',0),),
        ),
        MelGroups('linkedDecals',
            MelStruct('XDCR', '2I', (FID, 'reference'), 'unknown'),
        ),
        MelFid('XLKR','linkedReference'),
        MelOptStruct('XCLP','8B','linkStartColorRed','linkStartColorGreen','linkStartColorBlue',('linkColorUnused1',null1),
                     'linkEndColorRed','linkEndColorGreen','linkEndColorBlue',('linkColorUnused2',null1)),
        MelGroup('activateParents',
            MelUInt8('XAPD', 'flags'),
            MelGroups('activateParentRefs',
                MelStruct('XAPR', 'If', (FID, 'reference'), 'delay'),
            ),
        ),
        MelOptStruct('XESP','IB3s',(FID,'parent'),(_flags,'parentFlags'),('unused1',null3)),
        MelOptFid('XEMI', 'emittance'),
        MelFid('XMBR','multiboundReference'),
        MelBase('XIBS','ignoredBySandbox'),
        MelOptFloat('XSCL', ('scale', 1.0)),
        MelOptStruct('DATA','=6f',('posX',None),('posY',None),('posZ',None),('rotX',None),('rotY',None),('rotZ',None)),
    )
    __slots__ = melSet.getSlotsUsed()

#------------------------------------------------------------------------------
class MrePmis(MelRecord):
    """Placed Missile."""
    classType = 'PMIS'

    _flags = Flags(0, Flags.getNames('oppositeParent'))
    _watertypeFlags = Flags(0, Flags.getNames('reflection','refraction'))

    melSet = MelSet(
        MelEdid(),
        MelFid('NAME','base'),
        MelFid('XEZN','encounterZone'),
        MelBase('XRGD','ragdollData'),
        MelBase('XRGB','ragdollBipedData'),
        MelGroup('patrolData',
            MelFloat('XPRD', 'idleTime'),
            MelBase('XPPA','patrolScriptMarker'),
            MelFid('INAM', 'idle'),
            MelEmbeddedScript(),
            MelFid('TNAM','topic'),
        ),
        MelOwnership(),
        MelSInt32('XCNT', 'count'),
        MelFloat('XRDS', 'radius'),
        MelFloat('XHLP', 'health'),
        MelGroups('reflectedRefractedBy',
            MelStruct('XPWR','2I',(FID,'waterReference'),(_watertypeFlags,'waterFlags',0),),
        ),
        MelGroups('linkedDecals',
            MelStruct('XDCR', '2I', (FID, 'reference'), 'unknown'),
        ),
        MelFid('XLKR','linkedReference'),
        MelOptStruct('XCLP','8B','linkStartColorRed','linkStartColorGreen','linkStartColorBlue',('linkColorUnused1',null1),
                     'linkEndColorRed','linkEndColorGreen','linkEndColorBlue',('linkColorUnused2',null1)),
        MelGroup('activateParents',
            MelUInt8('XAPD', 'flags'),
            MelGroups('activateParentRefs',
                MelStruct('XAPR', 'If', (FID, 'reference'), 'delay'),
            ),
        ),
        MelOptStruct('XESP','IB3s',(FID,'parent'),(_flags,'parentFlags'),('unused1',null3)),
        MelOptFid('XEMI', 'emittance'),
        MelFid('XMBR','multiboundReference'),
        MelBase('XIBS','ignoredBySandbox'),
        MelOptFloat('XSCL', ('scale', 1.0)),
        MelOptStruct('DATA','=6f',('posX',None),('posY',None),('posZ',None),('rotX',None),('rotY',None),('rotZ',None)),
    )
    __slots__ = melSet.getSlotsUsed()

#------------------------------------------------------------------------------
class MreProj(MelRecord):
    """Projectile."""
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
        MelEdid(),
        MelBounds(),
        MelFull(),
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
        MelUInt32('VNAM', 'soundLevel'),
    )
    __slots__ = melSet.getSlotsUsed()

#------------------------------------------------------------------------------
class MrePwat(MelRecord):
    """Placeable Water."""
    classType = 'PWAT'

    _flags = Flags(0, Flags.getNames(
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
        MelEdid(),
        MelBounds(),
        MelModel(),
        MelStruct('DNAM','2I',(_flags,'flags'),(FID,'water'))
    )
    __slots__ = melSet.getSlotsUsed()

#------------------------------------------------------------------------------
class MreQust(MelRecord):
    """Quest."""
    classType = 'QUST'

    _questFlags = Flags(0,Flags.getNames('startGameEnabled',None,'repeatedTopics','repeatedStages'))
    stageFlags = Flags(0,Flags.getNames('complete'))
    targetFlags = Flags(0,Flags.getNames('ignoresLocks'))

    melSet = MelSet(
        MelEdid(),
        MelFid('SCRI','script'),
        MelFull(),
        MelIcon(),
        MelTruncatedStruct('DATA', '2B2sf', (_questFlags, 'questFlags', 0),
                           ('priority', 0), ('unused2', null2),
                           ('questDelay', 0.0), old_versions={'2B'}),
        MelConditions(),
        MelGroups('stages',
            MelSInt16('INDX', 'stage'),
            MelGroups('entries',
                MelUInt8('QSDT', (stageFlags, 'flags')),
                MelConditions(),
                MelString('CNAM','text'),
                MelEmbeddedScript(),
                MelFid('NAM0', 'nextQuest'),
            ),
        ),
        MelGroups('objectives',
            MelSInt32('QOBJ', 'index'),
            MelString('NNAM','description'),
            MelGroups('targets',
                MelStruct('QSTA','IB3s',(FID,'targetId'),(targetFlags,'flags'),('unused1',null3)),
                MelConditions(),
            ),
        ),
    ).with_distributor({
        'EDID|DATA': { # just in case one is missing
            'CTDA': 'conditions',
        },
        'INDX': {
            'CTDA': 'stages',
        },
        'QOBJ': {
            'CTDA': 'objectives',
        },
    })
    __slots__ = melSet.getSlotsUsed()

#------------------------------------------------------------------------------
class MreRace(MelRecord):
    """Race."""
    classType = 'RACE'

    _flags = Flags(0, Flags.getNames('playable', None, 'child'))

    # TODO(inf) Using this for Oblivion would be nice, but faces.py seems to
    #  use those attributes directly, so that would need rewriting
    class MelRaceFaceGen(MelGroup):
        """Defines facegen subrecords for RACE."""
        def __init__(self, facegen_attr):
            MelGroup.__init__(self, facegen_attr,
                MelBase('FGGS', 'fggs_p'), # FaceGen Geometry - Symmetric
                MelBase('FGGA', 'fgga_p'), # FaceGen Geometry - Asymmetric
                MelBase('FGTS', 'fgts_p'), # FaceGen Texture  - Symmetric
                MelStruct('SNAM', '2s', ('snam_p', null2)))

    melSet = MelSet(
        MelEdid(),
        MelFull(),
        MelString('DESC','text'),
        MelGroups('relations',
            MelStruct('XNAM', 'I2i', (FID, 'faction'), 'mod',
                      'groupCombatReaction'),
        ),
        MelStruct('DATA','14b2s4fI','skill1','skill1Boost','skill2','skill2Boost',
                  'skill3','skill3Boost','skill4','skill4Boost','skill5','skill5Boost',
                  'skill6','skill6Boost','skill7','skill7Boost',('unused1',null2),
                  'maleHeight','femaleHeight','maleWeight','femaleWeight',(_flags,'flags',0)),
        MelFid('ONAM','Older'),
        MelFid('YNAM','Younger'),
        MelBase('NAM2','_nam2',''),
        MelRaceVoices('VTCK', '2I', (FID, 'maleVoice'), (FID, 'femaleVoice')),
        MelOptStruct('DNAM','2I',(FID,'defaultHairMale',0),(FID,'defaultHairFemale',0)),
        # Int corresponding to GMST sHairColorNN
        MelStruct('CNAM','2B','defaultHairColorMale','defaultHairColorFemale'),
        MelOptFloat('PNAM', 'mainClamp'),
        MelOptFloat('UNAM', 'faceClamp'),
        MelStruct('ATTR','2B','maleBaseAttribute','femaleBaseAttribute'),
        MelBase('NAM0', 'head_data_marker', ''),
        MelBase('MNAM', 'male_head_data_marker', ''),
        MelRaceParts({
            0: 'maleHead',
            1: 'maleEars',
            2: 'maleMouth',
            3: 'maleTeethLower',
            4: 'maleTeethUpper',
            5: 'maleTongue',
            6: 'maleLeftEye',
            7: 'maleRightEye',
        }, group_loaders=lambda indx: (MelRaceHeadPart(indx),)),
        MelBase('FNAM', 'female_head_data_marker', ''),
        MelRaceParts({
            0: 'femaleHead',
            1: 'femaleEars',
            2: 'femaleMouth',
            3: 'femaleTeethLower',
            4: 'femaleTeethUpper',
            5: 'femaleTongue',
            6: 'femaleLeftEye',
            7: 'femaleRightEye',
        }, group_loaders=lambda indx: (MelRaceHeadPart(indx),)),
        MelBase('NAM1', 'body_data_marker', ''),
        MelBase('MNAM', 'male_body_data_marker', ''),
        MelRaceParts({
            0: 'maleUpperBody',
            1: 'maleLeftHand',
            2: 'maleRightHand',
            3: 'maleUpperBodyTexture',
        }, group_loaders=lambda _indx: (
            MelIcons(),
            MelModel(),
        )),
        MelBase('FNAM', 'female_body_data_marker', ''),
        MelRaceParts({
            0: 'femaleUpperBody',
            1: 'femaleLeftHand',
            2: 'femaleRightHand',
            3: 'femaleUpperBodyTexture',
        }, group_loaders=lambda _indx: (
            MelIcons(),
            MelModel()
        )),
        MelFidList('HNAM','hairs'),
        MelFidList('ENAM','eyes'),
        MelBase('MNAM', 'male_facegen_marker', ''),
        MelRaceFaceGen('maleFaceGen'),
        MelBase('FNAM', 'female_facegen_marker', ''),
        MelRaceFaceGen('femaleFaceGen'),
    ).with_distributor({
        'NAM0': {
            'MNAM': ('male_head_data_marker', {
                'INDX|ICON|MICO|MODL|MODB|MODT|MODS|MODD': 'maleHead',
            }),
            'FNAM': ('female_head_data_marker', {
                'INDX|ICON|MICO|MODL|MODB|MODT|MODS|MODD': 'femaleHead',
            }),
        },
        'NAM1': {
            'MNAM': ('male_body_data_marker', {
                'INDX|ICON|MICO|MODL|MODB|MODT|MODS|MODD': 'maleUpperBody',
            }),
            'FNAM': ('female_body_data_marker', {
                'INDX|ICON|MICO|MODL|MODB|MODT|MODS|MODD': 'femaleUpperBody',
            }),
        },
        'ENAM': {
            'MNAM': ('male_facegen_marker', {
                'FGGS|FGGA|FGTS|SNAM': 'maleFaceGen',
            }),
            'FNAM': ('female_facegen_marker', {
                'FGGS|FGGA|FGTS|SNAM': 'femaleFaceGen',
            }),
        },
    })
    __slots__ = melSet.getSlotsUsed()

#------------------------------------------------------------------------------
class MreRads(MelRecord):
    """Radiation Stage."""
    classType = 'RADS'
    melSet = MelSet(
        MelEdid(),
        MelStruct('DATA','2I','trigerThreshold',(FID,'actorEffect')),
    )
    __slots__ = melSet.getSlotsUsed()

#------------------------------------------------------------------------------
class MreRefr(MelRecord):
    """Placed Object."""
    classType = 'REFR'

    _marker_flags = Flags(0, Flags.getNames(
        'visible',
        'can_travel_to',
        'show_all_hidden',
    ))
    _parentFlags = Flags(0, Flags.getNames('oppositeParent'))
    _actFlags = Flags(0, Flags.getNames('useDefault', 'activate','open','openByDefault'))
    _lockFlags = Flags(0, Flags.getNames(None, None, 'leveledLock'))
    _destinationFlags = Flags(0, Flags.getNames('noAlarm'))
    reflectFlags = Flags(0, Flags.getNames('reflection', 'refraction'))

    melSet = MelSet(
        MelEdid(),
        MelOptStruct('RCLR','8B','referenceStartColorRed','referenceStartColorGreen','referenceStartColorBlue',('referenceColorUnused1',null1),
                     'referenceEndColorRed','referenceEndColorGreen','referenceEndColorBlue',('referenceColorUnused2',null1)),
        MelFid('NAME','base'),
        MelFid('XEZN','encounterZone'),
        MelBase('XRGD','ragdollData'),
        MelBase('XRGB','ragdollBipedData'),
        MelOptStruct('XPRM','3f3IfI','primitiveBoundX','primitiveBoundY','primitiveBoundX',
                     'primitiveColorRed','primitiveColorGreen','primitiveColorBlue','primitiveUnknown','primitiveType'),
        MelOptUInt32('XTRI', 'collisionLayer'),
        MelBase('XMBP','multiboundPrimitiveMarker'),
        MelOptStruct('XMBO','3f','boundHalfExtentsX','boundHalfExtentsY','boundHalfExtentsZ'),
        MelOptStruct('XTEL','I6fI',(FID,'destinationFid'),'destinationPosX','destinationPosY',
            'destinationPosZ','destinationRotX','destinationRotY','destinationRotZ',(_destinationFlags,'destinationFlags')),
        MelGroup('map_marker',
            MelBase('XMRK', 'marker_data'),
            MelOptUInt8('FNAM', (_marker_flags, 'marker_flags')),
            MelFull(),
            MelOptStruct('TNAM', 'Bs', 'marker_type', 'unused1'),
        ),
        MelFid('XTRG','targetId'),
        MelOptSInt32('XLCM', ('levelMod', None)),
        MelGroup('patrolData',
            MelFloat('XPRD', 'idleTime'),
            MelBase('XPPA','patrolScriptMarker'),
            MelFid('INAM', 'idle'),
            MelEmbeddedScript(),
            MelFid('TNAM','topic'),
        ),
        MelOptStruct('XRDO','fIfI','rangeRadius','broadcastRangeType','staticPercentage',(FID,'positionReference')),
        MelOwnership(),
        ##: I dropped special handling here, looks like a regular truncated
        # record to me - but no way to test since we don't load this yet
        MelTruncatedStruct(
            'XLOC', 'B3sI4sB3s4s', 'lockLevel', ('unused1',null3),
            (FID, 'lockKey'), ('unused2', null4), (_lockFlags, 'lockFlags'),
            ('unused3', null3), ('unused4', null4), is_optional=True,
            old_versions={'B3sI4s'}),
        MelOptSInt32('XCNT', 'count'),
        MelOptFloat('XRDS', 'radius'),
        MelOptFloat('XHLP', 'health'),
        MelOptFloat('XRAD', 'radiation'),
        MelOptFloat('XCHG', ('charge', None)),
        MelGroup('ammo',
            MelFid('XAMT','type'),
            MelUInt32('XAMC', 'count'),
        ),
        MelGroups('reflectedByWaters',
            MelStruct('XPWR', '2I', (FID, 'reference'),
                      (reflectFlags, 'reflection_type')),
        ),
        MelFids('XLTW','litWaters'),
        MelGroups('linkedDecals',
            MelStruct('XDCR', '2I', (FID, 'reference'), 'unknown'),
        ),
        MelFid('XLKR','linkedReference'),
        MelOptStruct('XCLP','8B','linkStartColorRed','linkStartColorGreen','linkStartColorBlue',('linkColorUnused1',null1),
                     'linkEndColorRed','linkEndColorGreen','linkEndColorBlue',('linkColorUnused2',null1)),
        MelGroup('activateParents',
            MelUInt8('XAPD', 'flags'),
            MelGroups('activateParentRefs',
                MelStruct('XAPR', 'If', (FID, 'reference'), 'delay'),
            ),
        ),
        MelOptStruct('XESP','IB3s',(FID,'parent'),(_parentFlags,'parentFlags'),('unused6',null3)),
        MelOptFid('XEMI', 'emittance'),
        MelFid('XMBR','multiboundReference'),
        MelOptUInt32('XACT', (_actFlags, 'actFlags', 0)),
        MelBase('ONAM','onam_p'),
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
        MelOptStruct('XLOD','3f',('lod1',None),('lod2',None),('lod3',None)),
        MelOptFloat('XSCL', ('scale', 1.0)),
        MelOptStruct('DATA','=6f',('posX',None),('posY',None),('posZ',None),('rotX',None),('rotY',None),('rotZ',None)),
    )
    __slots__ = melSet.getSlotsUsed()

#------------------------------------------------------------------------------
class MreRegn(MelRecord):
    """Region."""
    classType = 'REGN'

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
    rdatFlags = Flags(0, Flags.getNames(
        ( 0,'Override'),))

    melSet = MelSet(
        MelEdid(),
        MelIcons(),
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
            MelRegnEntrySubrecord(4, MelString('RDMP', 'mapName')),
            MelRegnEntrySubrecord(6, MelArray('grasses',
                MelStruct('RDGS', 'I4s', (FID, 'grass'), ('unknown', null4)),
            )),
            MelRegnEntrySubrecord(7, MelOptUInt32('RDMD', 'musicType')),
            MelRegnEntrySubrecord(7, MelFid('RDMO', 'music')),
            MelRegnEntrySubrecord(7, MelArray('sounds',
                MelStruct('RDSD', '3I', (FID, 'sound'), (sdflags, 'flags'),
                          'chance'),
            )),
            MelRegnEntrySubrecord(3, MelArray('weatherTypes',
                MelStruct('RDWT', '3I', (FID, 'weather', None), 'chance',
                          (FID, 'global', None)),
            )),
        ),
    )
    __slots__ = melSet.getSlotsUsed()

#------------------------------------------------------------------------------
class MreRgdl(MelRecord):
    """Ragdoll."""
    classType = 'RGDL'

    _flags = Flags(0, Flags.getNames('disableOnMove'))

    melSet = MelSet(
        MelEdid(),
        MelUInt32('NVER', 'version'),
        MelStruct('DATA','I4s5Bs','boneCount','unused1','feedback',
            'footIK','lookIK','grabIK','poseMatching','unused2'),
        MelFid('XNAM','actorBase'),
        MelFid('TNAM','bodyPartData'),
        MelStruct('RAFD','13f2i','keyBlendAmount','hierarchyGain','positionGain',
            'velocityGain','accelerationGain','snapGain','velocityDamping',
            'snapMaxLinearVelocity','snapMaxAngularVelocity','snapMaxLinearDistance',
            'snapMaxAngularDistance','posMaxVelLinear',
            'posMaxVelAngular','posMaxVelProjectile','posMaxVelMelee'),
        MelArray('feedbackDynamicBones',
            MelUInt16('RAFB', 'bone'),
        ),
        MelStruct('RAPS','3HBs4f','matchBones1','matchBones2','matchBones3',
            (_flags,'flags'),'unused3','motorsStrength',
            'poseActivationDelayTime','matchErrorAllowance',
            'displacementToDisable',),
        MelString('ANAM','deathPose'),
    )
    __slots__ = melSet.getSlotsUsed()

#------------------------------------------------------------------------------
class MreScol(MelRecord):
    """Static Collection."""
    classType = 'SCOL'

    melSet = MelSet(
        MelEdid(),
        MelBounds(),
        MelModel(),
        MelGroups('parts',
            MelFid('ONAM','static'),
            MelArray('placements',
                MelStruct('DATA', '7f', ('posX', None), ('posY', None),
                          ('posZ', None), ('rotX', None), ('rotY', None),
                          ('rotZ', None), ('scale', None)),
            ),
        ),
    )
    __slots__ = melSet.getSlotsUsed()

#------------------------------------------------------------------------------
class MreScpt(MelRecord):
    """Script."""
    classType = 'SCPT'

    melSet = MelSet(
        MelEdid(),
        MelEmbeddedScript(),
    )
    __slots__ = melSet.getSlotsUsed()

#------------------------------------------------------------------------------
class MreSoun(MelRecord):
    """Sound."""
    classType = 'SOUN'

    _flags = Flags(0, Flags.getNames(
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

    melSet = MelSet(
        MelEdid(),
        MelBounds(),
        MelString('FNAM','soundFile'),
        MelStruct('SNDD', '2BbsIh2B6h3i', 'minDist', 'maxDist', 'freqAdj',
                  ('unusedSndd', null1), (_flags, 'flags'), 'staticAtten',
                  'stopTime', 'startTime', 'point0', 'point1', 'point2',
                  'point3', 'point4', 'reverb', 'priority', 'xLoc', 'yLoc'),
        # These are the older format - read them, but only write out SNDD
        MelReadOnly(
            MelStruct('SNDX', '2BbsIh2B', 'minDist', 'maxDist', 'freqAdj',
                      ('unusedSndd', null1), (_flags, 'flags'), 'staticAtten',
                      'stopTime', 'startTime'),
            MelStruct('ANAM', '5h', 'point0', 'point1', 'point2', 'point3',
                      'point4'),
            MelSInt16('GNAM', 'reverb'),
            MelSInt32('HNAM', 'priority'),
        ),
    )
    __slots__ = melSet.getSlotsUsed()

#------------------------------------------------------------------------------
class MreSpel(MelRecord,MreHasEffects):
    """Actor Effect"""
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
    )
    __slots__ = melSet.getSlotsUsed()

#------------------------------------------------------------------------------
class MreStat(MelRecord):
    """Static."""
    classType = 'STAT'

    melSet = MelSet(
        MelEdid(),
        MelBounds(),
        MelModel(),
    )
    __slots__ = melSet.getSlotsUsed()

#------------------------------------------------------------------------------
class MreTact(MelRecord):
    """Talking Activator."""
    classType = 'TACT'

    melSet = MelSet(
        MelEdid(),
        MelBounds(),
        MelFull(),
        MelModel('model'),
        MelFid('SCRI','script'),
        MelDestructible(),
        MelFid('SNAM','sound'),
        MelFid('VNAM','voiceType'),
    )
    __slots__ = melSet.getSlotsUsed()

#------------------------------------------------------------------------------
class MreTerm(MelRecord):
    """Terminal."""
    classType = 'TERM'

    _flags = Flags(0, Flags.getNames('leveled','unlocked','alternateColors','hideWellcomeTextWhenDisplayingImage'))
    _menuFlags = Flags(0, Flags.getNames('addNote','forceRedraw'))

    melSet = MelSet(
        MelEdid(),
        MelBounds(),
        MelFull(),
        MelModel(),
        MelFid('SCRI','script'),
        MelDestructible(),
        MelString('DESC','description'),
        MelFid('SNAM','soundLooping'),
        MelFid('PNAM','passwordNote'),
        MelTruncatedStruct('DNAM', '3Bs', 'baseHackingDifficulty',
                           (_flags,'flags'), 'serverType', 'unused1',
                           old_versions={'3B'}),
        MelGroups('menuItems',
            MelString('ITXT','itemText'),
            MelString('RNAM','resultText'),
            MelUInt8('ANAM', (_menuFlags, 'menuFlags')),
            MelFid('INAM','displayNote'),
            MelFid('TNAM','subMenu'),
            MelEmbeddedScript(),
            MelConditions(),
        ),
    )
    __slots__ = melSet.getSlotsUsed()

#------------------------------------------------------------------------------
class MreTree(MelRecord):
    """Tree."""
    classType = 'TREE'

    melSet = MelSet(
        MelEdid(),
        MelBounds(),
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

#------------------------------------------------------------------------------
class MreTxst(MelRecord):
    """Texture Set."""
    classType = 'TXST'

    TxstTypeFlags = Flags(0, Flags.getNames(
        (0, 'noSpecularMap'),
    ))
    DecalDataFlags = Flags(0, Flags.getNames(
            (0, 'parallax'),
            (0, 'alphaBlending'),
            (0, 'alphaTesting'),
            (0, 'noSubtextures'),
        ))

    melSet = MelSet(
        MelEdid(),
        MelBounds(),
        MelString('TX00','baseImage'),
        MelString('TX01','normalMap'),
        MelString('TX02','environmentMapMask'),
        MelString('TX03','growMap'),
        MelString('TX04','parallaxMap'),
        MelString('TX05','environmentMap'),
        MelOptStruct('DODT','7fBB2s3Bs','minWidth','maxWidth','minHeight',
                     'maxHeight','depth','shininess','parallaxScale',
                     'parallaxPasses',(DecalDataFlags,'decalFlags',0),
                     ('unused1',null2),'red','green','blue',('unused2',null1)),
        MelUInt16('DNAM', (TxstTypeFlags, 'flags', 0)),
    )
    __slots__ = melSet.getSlotsUsed()

#------------------------------------------------------------------------------
class MreVtyp(MelRecord):
    """Voice Type."""
    classType = 'VTYP'

    _flags = Flags(0, Flags.getNames('allowDefaultDialog','female'))

    melSet = MelSet(
        MelEdid(),
        MelUInt8('DNAM', (_flags, 'flags')),
    )
    __slots__ = melSet.getSlotsUsed()

#------------------------------------------------------------------------------
class MreWatr(MelRecord):
    """Water."""
    classType = 'WATR'

    _flags = Flags(0, Flags.getNames('causesDmg','reflective'))

    # TODO(inf) Actually two separate DATA subrecords - union + distributor
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
                raise ModSizeError(ins.inName, readId, (186, 2), size_)

        def dumpData(self,record,out):
            out.packSub(self.subType,'H',record.damage)

    class MelWatrDnam(MelTruncatedStruct):
        # TODO(inf) Why do we do this?
        def _pre_process_unpacked(self, unpacked_val):
            if len(unpacked_val) == 55:
                unpacked_val = unpacked_val[:-1]
            return MelTruncatedStruct._pre_process_unpacked(self, unpacked_val)

    melSet = MelSet(
        MelEdid(),
        MelFull(),
        MelString('NNAM','texture'),
        MelUInt8('ANAM', 'opacity'),
        MelUInt8('FNAM', (_flags, 'flags', 0)),
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
            old_versions={'10f3Bs3Bs3BsI32f'}),
        MelFidList('GNAM','relatedWaters'),
    )
    __slots__ = melSet.getSlotsUsed()

#------------------------------------------------------------------------------
class MreWeap(MelRecord):
    """Weapon."""
    classType = 'WEAP'

    _flags = Flags(0, Flags.getNames('notNormalWeapon'))
    _dflags1 = Flags(0, Flags.getNames(
            'ignoresNormalWeaponResistance',
            'isAutomatic',
            'hasScope',
            'cantDrop',
            'hideBackpack',
            'embeddedWeapon',
            'dontUse1stPersonISAnimations',
            'nonPlayable',
        ))
    _dflags2 = Flags(0, Flags.getNames(
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
    _cflags = Flags(0, Flags.getNames(
            'onDeath',
            'unknown1','unknown2','unknown3','unknown4',
            'unknown5','unknown6','unknown7',
        ))

    melSet = MelSet(
        MelEdid(),
        MelBounds(),
        MelFull(),
        MelModel('model'),
        MelIcons(),
        MelFid('SCRI','script'),
        MelFid('EITM','objectEffect'),
        MelOptUInt16('EAMT', 'objectEffectPoints'),
        MelFid('NAM0','ammo'),
        MelDestructible(),
        MelFid('REPL','repairList'),
        MelSInt32('ETYP', ('etype', -1)),
        MelFid('BIPL','bipedModelList'),
        MelFid('YNAM','pickupSound'),
        MelFid('ZNAM','dropSound'),
        MelModel('shellCasingModel',2),
        MelModel('scopeModel', 3, with_facegen_flags=False),
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
        MelTruncatedStruct('DNAM', 'I2f4B5fI4B2f2I11fiI2fi3f',
                    'animationType','animationMultiplier','reach',
                    (_dflags1,'dnamFlags1',0),('gripAnimation',255),'ammoUse',
                    'reloadAnimation','minSpread','spread','weapDnam1','sightFov',
                    ('weapDnam2',0.0),(FID,'projectile',0),'baseVatsToHitChance',
                    ('attackAnimation',255),'projectileCount','embeddedWeaponActorValue',
                    'minRange','maxRange','onHit',(_dflags2,'dnamFlags2',0),
                    'animationAttackMultiplier','fireRate','overrideActionPoint',
                    'rumbleLeftMotorStrength','rumbleRightMotorStrength',
                    'rumbleDuration','overrideDamageToWeaponMult','attackShotsPerSec',
                    'reloadTime','jamTime','aimArc',('skill',45),'rumblePattern',
                    'rambleWavelangth','limbDmgMult',('resistType',-1),
                    'sightUsage','semiAutomaticFireDelayMin',
                    'semiAutomaticFireDelayMax',
                    old_versions={'I2f4B5fI4B2f2I11fiI2fi',
                                  'I2f4B5fI4B2f2I11fiI2f'}),
        MelOptStruct('CRDT','H2sfB3sI',('criticalDamage', 0),('weapCrdt1', null2),
                     ('criticalMultiplier', 0.0),(_cflags,'criticalFlags', 0),
                     ('weapCrdt2', null3),(FID,'criticalEffect', 0)),
        MelBase('VNAM','soundLevel'),
    )
    __slots__ = melSet.getSlotsUsed()

#------------------------------------------------------------------------------
class MreWrld(MelRecord):
    """Worldspace."""
    classType = 'WRLD'

    _flags = Flags(0, Flags.getNames('smallWorld','noFastTravel','oblivionWorldspace',None,
        'noLODWater','noLODNoise','noAllowNPCFallDamage'))
    pnamFlags = Flags(0, Flags.getNames(
        'useLandData','useLODData','useMapData','useWaterData','useClimateData',
        'useImageSpaceData',None,'needsWaterAdjustment'))

    melSet = MelSet(
        MelEdid(),
        MelFull(),
        MelFid('XEZN','encounterZone'),
        MelFid('WNAM','parent'),
        MelOptStruct('PNAM','BB',(pnamFlags,'parentFlags',0),('unknownff',0xff)),
        MelFid('CNAM','climate'),
        MelFid('NAM2','water'),
        MelFid('NAM3','waterType'),
        MelFloat('NAM4', 'waterHeight'),
        MelStruct('DNAM','ff','defaultLandHeight','defaultWaterHeight'),
        MelIcon('mapPath'),
        MelOptStruct('MNAM','2i4h',('dimX',None),('dimY',None),('NWCellX',None),('NWCellY',None),('SECellX',None),('SECellY',None)),
        MelStruct('ONAM','fff','worldMapScale','cellXOffset','cellYOffset'),
        MelFid('INAM','imageSpace'),
        MelUInt8('DATA', (_flags, 'flags', 0)),
        MelStruct('NAM0', '2f', 'object_bounds_min_x', 'object_bounds_min_y'),
        MelStruct('NAM9', '2f', 'object_bounds_max_x', 'object_bounds_max_y'),
        MelFid('ZNAM','music'),
        MelString('NNAM','canopyShadow'),
        MelString('XNAM','waterNoiseTexture'),
        MelGroups('swappedImpacts',
            MelStruct('IMPS', '3I', 'materialType', (FID, 'old'),
                      (FID, 'new')),
        ),
        MelBase('IMPF','footstepMaterials'), #--todo rewrite specific class.
        MelBase('OFST','ofst_p'),
    )
    __slots__ = melSet.getSlotsUsed()

#------------------------------------------------------------------------------
class MreWthr(MelRecord):
    """Weather."""
    classType = 'WTHR'

    melSet = MelSet(
        MelEdid(),
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
        MelArray('cloudColors',
            MelWthrColors('PNAM'),
        ),
        MelArray('daytimeColors',
            MelWthrColors('NAM0'),
        ),
        MelStruct('FNAM','6f','fogDayNear','fogDayFar','fogNightNear','fogNightFar','fogDayPower','fogNightPower'),
        MelBase('INAM', 'unused1', null1 * 304),
        MelStruct('DATA','15B',
            'windSpeed','lowerCloudSpeed','upperCloudSpeed','transDelta',
            'sunGlare','sunDamage','rainFadeIn','rainFadeOut','boltFadeIn',
            'boltFadeOut','boltFrequency','weatherType','boltRed','boltBlue','boltGreen'),
        MelGroups('sounds',
            MelStruct('SNAM', '2I', (FID, 'sound'), 'type'),
        ),
    )
    __slots__ = melSet.getSlotsUsed()
