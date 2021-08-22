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
"""This module contains the falloutnv record classes."""
# Set MelModel in brec, in this case it's identical to the fallout 3 one
from ..fallout3.records import MelDestructible, MelConditions
from ...bolt import Flags, struct_calcsize
from ...brec import MelModel # set in Mopy/bash/game/fallout3/records.py
from ...brec import MelRecord, MelGroups, MelStruct, FID, MelString, MelSet, \
    MelFid, MelFids, MelBase, MelFidList, MreHeaderBase, MelFloat, MelUInt8, \
    MelUInt32, MelBounds, null1, MelTruncatedStruct, MelIcons, MelIcon, \
    MelIco2, MelEdid, MelFull, MelArray, MelObject, MelNull, MelScript, \
    MelDescription, MelPickupSound, MelDropSound, MelUInt8Flags, MelSInt32, \
    MelSorted
from ...exception import ModSizeError

#------------------------------------------------------------------------------
# FalloutNV Records -----------------------------------------------------------
#------------------------------------------------------------------------------
class MreTes4(MreHeaderBase):
    """TES4 Record.  File header."""
    rec_sig = b'TES4'

    melSet = MelSet(
        MelStruct(b'HEDR', [u'f', u'2I'], ('version', 1.34), 'numRecords',
                  ('nextObject', 0x800)),
        MelNull(b'OFST'), # Not even CK/xEdit can recalculate these right now
        MelBase(b'DELE','dele_p',),  #--Obsolete?
        MreHeaderBase.MelAuthor(),
        MreHeaderBase.MelDescription(),
        MreHeaderBase.MelMasterNames(),
        MelFidList(b'ONAM','overrides'),
        MelBase(b'SCRN', 'screenshot'),
    )
    __slots__ = melSet.getSlotsUsed()

#------------------------------------------------------------------------------
class MreAloc(MelRecord):
    """Media Location Controller."""
    rec_sig = b'ALOC'

    melSet = MelSet(
        MelEdid(),
        MelFull(),
        MelUInt32(b'NAM1', 'flags'),
        MelUInt32(b'NAM2', 'num2'),
        MelUInt32(b'NAM3', 'nam3'),
        MelUInt32(b'NAM4', 'locationDelay'),
        MelUInt32(b'NAM5', 'dayStart'),
        MelUInt32(b'NAM6', 'nightStart'),
        MelUInt32(b'NAM7', 'retrigerDelay'),
        MelSorted(MelFids(b'HNAM', 'neutralSets')),
        MelSorted(MelFids(b'ZNAM', 'allySets')),
        MelSorted(MelFids(b'XNAM', 'friendSets')),
        MelSorted(MelFids(b'YNAM', 'enemySets')),
        MelSorted(MelFids(b'LNAM', 'locationSets')),
        MelSorted(MelFids(b'GNAM', 'battleSets')),
        MelFid(b'RNAM','conditionalFaction'),
        MelUInt32(b'FNAM', 'fnam'),
    )
    __slots__ = melSet.getSlotsUsed()

#------------------------------------------------------------------------------
class MreAmef(MelRecord):
    """Ammo Effect."""
    rec_sig = b'AMEF'

    melSet = MelSet(
        MelEdid(),
        MelFull(),
        MelStruct(b'DATA', [u'2I', u'f'],'type','operation','value'),
    )
    __slots__ = melSet.getSlotsUsed()

#------------------------------------------------------------------------------
class MreCcrd(MelRecord):
    """Caravan Card."""
    rec_sig = b'CCRD'

    melSet = MelSet(
        MelEdid(),
        MelBounds(),
        MelFull(),
        MelModel(),
        MelIcons(),
        MelScript(),
        MelPickupSound(),
        MelDropSound(),
        MelString(b'TX00','textureFace'),
        MelString(b'TX01','textureBack'),
        MelUInt32(b'INTV', 'card_suit'),
        MelUInt32(b'INTV', 'card_value'),
        MelUInt32(b'DATA', 'value'),
    ).with_distributor({
        b'INTV': (u'card_suit', {
            b'INTV': u'card_value',
        }),
    })
    __slots__ = melSet.getSlotsUsed()

#------------------------------------------------------------------------------
class MreCdck(MelRecord):
    """Caravan Deck."""
    rec_sig = b'CDCK'

    melSet = MelSet(
        MelEdid(),
        MelFull(),
        MelSorted(MelFids(b'CARD', 'cards')),
        MelUInt32(b'DATA', 'count'), # 'Count (broken)' in xEdit - unused?
    )
    __slots__ = melSet.getSlotsUsed()

#------------------------------------------------------------------------------
class MreChal(MelRecord):
    """Challenge."""
    rec_sig = b'CHAL'

    melSet = MelSet(
        MelEdid(),
        MelFull(),
        MelIcons(),
        MelScript(),
        MelDescription(),
        MelStruct(b'DATA', [u'4I', u'2s', u'2s', u'4s'],'type','threshold','flags','interval',
                  'dependOnType1','dependOnType2','dependOnType3'),
        MelFid(b'SNAM','dependOnType4'),
        MelFid(b'XNAM','dependOnType5'),
    )
    __slots__ = melSet.getSlotsUsed()

#------------------------------------------------------------------------------
class MreChip(MelRecord):
    """Casino Chip."""
    rec_sig = b'CHIP'

    melSet = MelSet(
        MelEdid(),
        MelBounds(),
        MelFull(),
        MelModel(),
        MelIcons(),
        MelDestructible(),
        MelPickupSound(),
        MelDropSound(),
    )
    __slots__ = melSet.getSlotsUsed()

#------------------------------------------------------------------------------
class MreCmny(MelRecord):
    """Caravan Money."""
    rec_sig = b'CMNY'

    melSet = MelSet(
        MelEdid(),
        MelBounds(),
        MelFull(),
        MelModel(),
        MelIcons(),
        MelPickupSound(),
        MelDropSound(),
        MelUInt32(b'DATA', 'absoluteValue'),
    )
    __slots__ = melSet.getSlotsUsed()

#------------------------------------------------------------------------------
class MreCsno(MelRecord):
    """Casino."""
    rec_sig = b'CSNO'

    melSet = MelSet(
        MelEdid(),
        MelFull(),
        MelStruct(b'DATA', [u'2f', u'9I', u'2I', u'I'],'decksPercentBeforeShuffle','BlackjackPayoutRatio',
            'slotReel0','slotReel1','slotReel2','slotReel3','slotReel4','slotReel5','slotReel6',
            'numberOfDecks','maxWinnings',(FID,'currency'),(FID,'casinoWinningQuest'),'flags'),
        MelGroups('chipModels',
            MelString(b'MODL','model')
        ),
        MelString(b'MOD2','slotMachineModel'),
        MelString(b'MOD3','blackjackTableModel'),
        MelString(b'MODT','extraBlackjackTableModel'),
        MelString(b'MOD4','rouletteTableModel'),
        MelGroups('slotReelTextures',
            MelIcon(u'texture'),
        ),
        MelGroups('blackjackDecks',
            MelIco2(u'texture'),
        ),
    )
    __slots__ = melSet.getSlotsUsed()

#------------------------------------------------------------------------------
class MreDehy(MelRecord):
    """Dehydration Stage."""
    rec_sig = b'DEHY'

    melSet = MelSet(
        MelEdid(),
        MelStruct(b'DATA', [u'2I'],'trigerThreshold',(FID,'actorEffect')),
    )
    __slots__ = melSet.getSlotsUsed()

#------------------------------------------------------------------------------
class MreDial(MelRecord):
    """Dialogue."""
    rec_sig = b'DIAL'

    _DialFlags = Flags(0, Flags.getNames('rumors', 'toplevel'))

    melSet = MelSet(
        MelEdid(),
        # Handle broken records that have INFC/INFX without a preceding QSTI
        # (e.g. [DIAL:001287C6] and [DIAL:000E9084])
        MelFid(b'INFC', 'broken_infc'),
        MelFid(b'INFX', 'broken_infx'),
        MelSorted(MelGroups('added_quests',
            MelFid(b'QSTI', 'added_quest'),
            MelGroups('shared_infos',
                MelFid(b'INFC', 'info_connection'),
                MelSInt32(b'INFX', 'info_index'),
            ),
        ), sort_by_attrs='added_quest'),
        # Apparently unused, but xEdit has it so we should keep it too
        MelSorted(MelFids(b'QSTR', 'removed_quests')),
        MelFull(),
        MelFloat(b'PNAM', 'priority'),
        MelString(b'TDUM', 'dumb_response'),
        MelTruncatedStruct(b'DATA', [u'2B'], 'dialType',
                           (_DialFlags, u'dialFlags'), old_versions={'B'}),
    ).with_distributor({
        b'INFC': u'broken_infc',
        b'INFX': u'broken_infx',
        b'QSTI': {
            b'INFC|INFX': u'added_quests',
        },
    })
    __slots__ = melSet.getSlotsUsed()

#------------------------------------------------------------------------------
class MreHung(MelRecord):
    """Hunger Stage."""
    rec_sig = b'HUNG'

    melSet = MelSet(
        MelEdid(),
        MelStruct(b'DATA', [u'2I'],'trigerThreshold',(FID,'actorEffect')),
    )
    __slots__ = melSet.getSlotsUsed()

#------------------------------------------------------------------------------
class MreImod(MelRecord):
    """Item Mod."""
    rec_sig = b'IMOD'

    melSet = MelSet(
        MelEdid(),
        MelBounds(),
        MelFull(),
        MelModel(),
        MelIcons(),
        MelScript(),
        MelDescription(),
        MelDestructible(),
        MelPickupSound(),
        MelDropSound(),
        MelStruct(b'DATA', [u'I', u'f'],'value','weight'),
    )
    __slots__ = melSet.getSlotsUsed()

#------------------------------------------------------------------------------
class MreLsct(MelRecord):
    """Load Screen Type."""
    rec_sig = b'LSCT'

    melSet = MelSet(
        MelEdid(),
        MelStruct(b'DATA', [u'5I', u'f', u'I', u'3f', u'I', u'20s', u'I', u'3f', u'4s', u'I'],'type','data1X','data1Y','data1Width',
                         'data1Height','data1Orientation',
            'data1Font','data1ColorR','data1ColorG','data1ColorB','data1Align','unknown1',
            'data2Font','data2ColorR','data2ColorG','data2ColorB','unknown2','stats'),
    )
    __slots__ = melSet.getSlotsUsed()

#------------------------------------------------------------------------------
class MreMset(MelRecord):
    """Media Set."""
    rec_sig = b'MSET'

    _flags = Flags(0, Flags.getNames(
        ( 0,'dayOuter'),
        ( 1,'dayMiddle'),
        ( 2,'dayInner'),
        ( 3,'nightOuter'),
        ( 4,'nightMiddle'),
        ( 5,'nightInner'),
        ))

    melSet = MelSet(
        MelEdid(),
        MelFull(),
        MelUInt32(b'NAM1', 'type'),
        MelString(b'NAM2','nam2'),
        MelString(b'NAM3','nam3'),
        MelString(b'NAM4','nam4'),
        MelString(b'NAM5','nam5'),
        MelString(b'NAM6','nam6'),
        MelString(b'NAM7','nam7'),
        MelFloat(b'NAM8', 'nam8'),
        MelFloat(b'NAM9', 'nam9'),
        MelFloat(b'NAM0', 'nam0'),
        MelFloat(b'ANAM', 'anam'),
        MelFloat(b'BNAM', 'bnam'),
        MelFloat(b'CNAM', 'cnam'),
        MelFloat(b'JNAM', 'jnam'),
        MelFloat(b'KNAM', 'knam'),
        MelFloat(b'LNAM', 'lnam'),
        MelFloat(b'MNAM', 'mnam'),
        MelFloat(b'NNAM', 'nnam'),
        MelFloat(b'ONAM', 'onam'),
        MelUInt8Flags(b'PNAM', u'enableFlags', _flags),
        MelFloat(b'DNAM', 'dnam'),
        MelFloat(b'ENAM', 'enam'),
        MelFloat(b'FNAM', 'fnam'),
        MelFloat(b'GNAM', 'gnam'),
        MelFid(b'HNAM', 'hnam'),
        MelFid(b'INAM', 'inam'),
        MelBase(b'DATA','data'),
    )
    __slots__ = melSet.getSlotsUsed()

#------------------------------------------------------------------------------
class MreRcct(MelRecord):
    """Recipe Category."""
    rec_sig = b'RCCT'

    melSet = MelSet(
        MelEdid(),
        MelFull(),
        MelUInt8(b'DATA', 'flags'),
    )
    __slots__ = melSet.getSlotsUsed()

#------------------------------------------------------------------------------
class MreRcpe(MelRecord):
    """Recipe."""
    rec_sig = b'RCPE'

    melSet = MelSet(
        MelEdid(),
        MelFull(),
        MelConditions(),
        MelStruct(b'DATA', [u'4I'],'skill','level',(FID,'category'),(FID,'subCategory')),
        MelGroups('ingredients',
            MelFid(b'RCIL','item'),
            MelUInt32(b'RCQY', 'quantity'),
        ),
        MelGroups('outputs',
            MelFid(b'RCOD','item'),
            MelUInt32(b'RCQY', 'quantity'),
        ),
    ).with_distributor({
        b'RCIL': {
            b'RCQY': u'ingredients',
        },
        b'RCOD': {
            b'RCQY': u'outputs',
        },
    })
    __slots__ = melSet.getSlotsUsed()

#------------------------------------------------------------------------------
class MreRepu(MelRecord):
    """Reputation."""
    rec_sig = b'REPU'

    melSet = MelSet(
        MelEdid(),
        MelFull(),
        MelIcons(),
        MelFloat(b'DATA', 'value'),
    )
    __slots__ = melSet.getSlotsUsed()

#------------------------------------------------------------------------------
class MreSlpd(MelRecord):
    """Sleep Deprivation Stage."""
    rec_sig = b'SLPD'

    melSet = MelSet(
        MelEdid(),
        MelStruct(b'DATA', [u'2I'],'trigerThreshold',(FID,'actorEffect')),
    )
    __slots__ = melSet.getSlotsUsed()

#------------------------------------------------------------------------------
class MelWthrColorsFnv(MelArray):
    """Used twice in WTHR for PNAM and NAM0. Needs to handle older versions
    as well. Can't simply use MelArray because MelTruncatedStruct does not
    have a static_size."""
    # TODO(inf) Rework MelArray - instead of static_size, have a
    #  get_entry_size that receives the total size_ of load_mel.
    #  MelTruncatedStruct could override that and make a guess based on its
    #  sizes. If that guess doesn't work, a small override class can be
    #  created by hand
    _new_sizes = {b'PNAM': 96, b'NAM0': 240}
    _old_sizes = {b'PNAM': 64, b'NAM0': 160}

    def __init__(self, wthr_sub_sig, wthr_attr):
        struct_definition = [
            [u'3B', u's', u'3B', u's', u'3B', u's', u'3B', u's', u'3B', u's',
             u'3B', u's'], u'riseRed', u'riseGreen', u'riseBlue',
            u'unused1', u'dayRed', u'dayGreen', u'dayBlue',
            u'unused2', u'setRed', u'setGreen', u'setBlue',
            u'unused3', u'nightRed', u'nightGreen', u'nightBlue',
            u'unused4', u'noonRed', u'noonGreen', u'noonBlue',
            u'unused5', u'midnightRed', u'midnightGreen',
            u'midnightBlue', u'unused6'
        ]
        super(MelWthrColorsFnv, self).__init__(wthr_attr,
            MelStruct(wthr_sub_sig, *struct_definition),
        )
        self._element_old = MelTruncatedStruct(
            wthr_sub_sig, *struct_definition,
            old_versions={u'3Bs3Bs3Bs3Bs'})

    def load_mel(self, record, ins, sub_type, size_, *debug_strs):
        if size_ == self._new_sizes[sub_type]:
            super(MelWthrColorsFnv, self).load_mel(record, ins, sub_type,
                                                   size_, *debug_strs)
        elif size_ == self._old_sizes[sub_type]:
            # Copied and adjusted from MelArray. Yuck. See comment below
            # docstring for some ideas for getting rid of this
            append_entry = getattr(record, self.attr).append
            entry_slots = self._element_old.attrs
            entry_size = struct_calcsize(u'3Bs3Bs3Bs3Bs')
            load_entry = self._element_old.load_mel
            for x in range(size_ // entry_size):
                arr_entry = MelObject()
                append_entry(arr_entry)
                arr_entry.__slots__ = entry_slots
                load_entry(arr_entry, ins, sub_type, entry_size, *debug_strs)
        else:
            _expected_sizes = (self._new_sizes[sub_type],
                               self._old_sizes[sub_type])
            raise ModSizeError(ins.inName, debug_strs, _expected_sizes, size_)

class MreWthr(MelRecord):
    """Weather."""
    rec_sig = b'WTHR'

    melSet = MelSet(
        MelEdid(),
        MelFid(b'\x00IAD', 'sunriseImageSpaceModifier'),
        MelFid(b'\x01IAD', 'dayImageSpaceModifier'),
        MelFid(b'\x02IAD', 'sunsetImageSpaceModifier'),
        MelFid(b'\x03IAD', 'nightImageSpaceModifier'),
        MelFid(b'\x04IAD', 'unknown1ImageSpaceModifier'),
        MelFid(b'\x05IAD', 'unknown2ImageSpaceModifier'),
        MelString(b'DNAM','upperLayer'),
        MelString(b'CNAM','lowerLayer'),
        MelString(b'ANAM','layer2'),
        MelString(b'BNAM','layer3'),
        MelModel(),
        MelBase(b'LNAM','unknown1'),
        MelStruct(b'ONAM', [u'4B'],'cloudSpeed0','cloudSpeed1','cloudSpeed3','cloudSpeed4'),
        MelWthrColorsFnv(b'PNAM', u'cloudColors'),
        MelWthrColorsFnv(b'NAM0', u'daytimeColors'),
        MelStruct(b'FNAM', [u'6f'],'fogDayNear','fogDayFar','fogNightNear','fogNightFar','fogDayPower','fogNightPower'),
        MelBase(b'INAM', 'unused1', null1 * 304),
        MelStruct(b'DATA', [u'15B'],
            'windSpeed','lowerCloudSpeed','upperCloudSpeed','transDelta',
            'sunGlare','sunDamage','rainFadeIn','rainFadeOut','boltFadeIn',
            'boltFadeOut','boltFrequency','weatherType','boltRed','boltBlue','boltGreen'),
        MelGroups('sounds',
            MelStruct(b'SNAM', [u'2I'], (FID, 'sound'), 'type'),
        ),
    )
    __slots__ = melSet.getSlotsUsed()
