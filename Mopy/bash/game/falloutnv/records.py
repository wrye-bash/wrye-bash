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
"""This module contains the falloutnv record classes."""
from ..fallout3.records import MelDestructible, MelModel
from ...bolt import Flags
from ...brec import MelRecord, MelGroups, MelStruct, FID, MelString, MelSet, \
    MelFid, MelFids, MelBase, MelSimpleArray, AMreHeader, MelFloat, MelEdid, \
    MelUInt32, MelBounds, MelTruncatedStruct, MelIcons, MelIcon, MelUInt8, \
    MelFull, MelNull, MelScript, MelDescription, MelSoundPickupDrop, MelIco2, \
    MelUInt8Flags, MelSInt32, MelSorted, MelValueWeight, MelConditionsFo3

#------------------------------------------------------------------------------
# FalloutNV Records -----------------------------------------------------------
#------------------------------------------------------------------------------
class MreTes4(AMreHeader):
    """TES4 Record.  File header."""
    rec_sig = b'TES4'
    _post_masters_sigs = {b'ONAM', b'SCRN'}

    melSet = MelSet(
        MelStruct(b'HEDR', [u'f', u'2I'], ('version', 1.34), 'numRecords',
                  ('nextObject', 0x800)),
        MelNull(b'OFST'), # obsolete
        MelNull(b'DELE'), # obsolete
        AMreHeader.MelAuthor(),
        AMreHeader.MelDescription(),
        AMreHeader.MelMasterNames(),
        MelSimpleArray('overrides', MelFid(b'ONAM')),
        MelBase(b'SCRN', 'screenshot'),
    )

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
        MelSorted(MelFids('neutralSets', MelFid(b'HNAM'))),
        MelSorted(MelFids('allySets', MelFid(b'ZNAM'))),
        MelSorted(MelFids('friendSets', MelFid(b'XNAM'))),
        MelSorted(MelFids('enemySets', MelFid(b'YNAM'))),
        MelSorted(MelFids('locationSets', MelFid(b'LNAM'))),
        MelSorted(MelFids('battleSets', MelFid(b'GNAM'))),
        MelFid(b'RNAM','conditionalFaction'),
        MelUInt32(b'FNAM', 'fnam'),
    )

#------------------------------------------------------------------------------
class MreAmef(MelRecord):
    """Ammo Effect."""
    rec_sig = b'AMEF'

    melSet = MelSet(
        MelEdid(),
        MelFull(),
        MelStruct(b'DATA', [u'2I', u'f'],'type','operation','value'),
    )

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
        MelSoundPickupDrop(),
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

#------------------------------------------------------------------------------
class MreCdck(MelRecord):
    """Caravan Deck."""
    rec_sig = b'CDCK'

    melSet = MelSet(
        MelEdid(),
        MelFull(),
        MelSorted(MelFids('cards', MelFid(b'CARD'))),
        MelUInt32(b'DATA', 'count'), # 'Count (broken)' in xEdit - unused?
    )

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
        MelSoundPickupDrop(),
    )

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
        MelSoundPickupDrop(),
        MelUInt32(b'DATA', 'absoluteValue'),
    )

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

#------------------------------------------------------------------------------
class MreDehy(MelRecord):
    """Dehydration Stage."""
    rec_sig = b'DEHY'

    melSet = MelSet(
        MelEdid(),
        MelStruct(b'DATA', [u'2I'],'trigerThreshold',(FID,'actorEffect')),
    )

#------------------------------------------------------------------------------
class MreDial(MelRecord):
    """Dialogue."""
    rec_sig = b'DIAL'

    _DialFlags = Flags.from_names('rumors', 'toplevel')

    @classmethod
    def nested_records_sigs(cls):
        return {b'INFO'}

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
        MelSorted(MelFids('removed_quests', MelFid(b'QSTR'))),
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

#------------------------------------------------------------------------------
class MreHung(MelRecord):
    """Hunger Stage."""
    rec_sig = b'HUNG'

    melSet = MelSet(
        MelEdid(),
        MelStruct(b'DATA', [u'2I'],'trigerThreshold',(FID,'actorEffect')),
    )

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
        MelSoundPickupDrop(),
        MelValueWeight(),
    )

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

#------------------------------------------------------------------------------
class MreMset(MelRecord):
    """Media Set."""
    rec_sig = b'MSET'

    _flags = Flags.from_names(
        ( 0,'dayOuter'),
        ( 1,'dayMiddle'),
        ( 2,'dayInner'),
        ( 3,'nightOuter'),
        ( 4,'nightMiddle'),
        ( 5,'nightInner'),
    )

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

#------------------------------------------------------------------------------
class MreRcct(MelRecord):
    """Recipe Category."""
    rec_sig = b'RCCT'

    melSet = MelSet(
        MelEdid(),
        MelFull(),
        MelUInt8(b'DATA', 'flags'),
    )

#------------------------------------------------------------------------------
class MreRcpe(MelRecord):
    """Recipe."""
    rec_sig = b'RCPE'

    melSet = MelSet(
        MelEdid(),
        MelFull(),
        MelConditionsFo3(),
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

#------------------------------------------------------------------------------
class MreSlpd(MelRecord):
    """Sleep Deprivation Stage."""
    rec_sig = b'SLPD'

    melSet = MelSet(
        MelEdid(),
        MelStruct(b'DATA', [u'2I'],'trigerThreshold',(FID,'actorEffect')),
    )
