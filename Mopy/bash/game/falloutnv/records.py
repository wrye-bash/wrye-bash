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
#  Wrye Bash copyright (C) 2005-2009 Wrye, 2010-2024 Wrye Bash Team
#  https://github.com/wrye-bash
#
# =============================================================================
"""This module contains the falloutnv record classes."""
# Make sure to import the FO3 MelRecord, since it's redefined to include the
# quest_item header flag
from ..fallout3.records import MelDestructible, MelModel, MelRecord
from ...bolt import Flags, flag
from ...brec import FID, AMreHeader, MelBase, MelBounds, MelConditionsFo3, \
    MelDescription, MelEdid, MelFid, MelFloat, MelFull, MelGroups, \
    MelIco2, MelIcon, MelIcons, MelNull, MelScript, MelSet, \
    MelSimpleArray, MelSInt32, MelSorted, MelSoundPickupDrop, MelString, \
    MelStruct, MelTruncatedStruct, MelUInt8, MelUInt8Flags, MelUInt32, \
    MelValueWeight, MelSimpleGroups

#------------------------------------------------------------------------------
# FalloutNV Records -----------------------------------------------------------
#------------------------------------------------------------------------------
class MreTes4(AMreHeader):
    """TES4 Record.  File header."""
    rec_sig = b'TES4'
    _post_masters_sigs = {b'ONAM', b'SCRN'}
    next_object_default = 0x800

    melSet = MelSet(
        MelStruct(b'HEDR', ['f', '2I'], ('version', 1.34), 'numRecords',
                  ('nextObject', next_object_default), is_required=True),
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
        MelSorted(MelSimpleGroups('neutralSets', MelFid(b'HNAM'))),
        MelSorted(MelSimpleGroups('allySets', MelFid(b'ZNAM'))),
        MelSorted(MelSimpleGroups('friendSets', MelFid(b'XNAM'))),
        MelSorted(MelSimpleGroups('enemySets', MelFid(b'YNAM'))),
        MelSorted(MelSimpleGroups('locationSets', MelFid(b'LNAM'))),
        MelSorted(MelSimpleGroups('battleSets', MelFid(b'GNAM'))),
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
        MelStruct(b'DATA', ['2I', 'f'], 'type', 'operation', 'value'),
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
        b'INTV': ('card_suit', {
            b'INTV': 'card_value',
        }),
    })

#------------------------------------------------------------------------------
class MreCdck(MelRecord):
    """Caravan Deck."""
    rec_sig = b'CDCK'

    melSet = MelSet(
        MelEdid(),
        MelFull(),
        MelSorted(MelSimpleGroups('cards', MelFid(b'CARD'))),
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
        MelStruct(b'DATA', ['4I', '2s', '2s', '4s'], 'type', 'threshold',
                  'flags', 'interval', 'dependOnType1', 'dependOnType2',
                  'dependOnType3'),
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
        MelStruct(b'DATA', ['2f', '9I', '2I', 'I'],
            'decksPercentBeforeShuffle', 'BlackjackPayoutRatio', 'slotReel0',
            'slotReel1', 'slotReel2', 'slotReel3', 'slotReel4', 'slotReel5',
            'slotReel6', 'numberOfDecks', 'maxWinnings', (FID, 'currency'),
            (FID, 'casinoWinningQuest'), 'flags'),
        MelGroups('chipModels',
            MelString(b'MODL','model')
        ),
        MelString(b'MOD2','slotMachineModel'),
        MelString(b'MOD3','blackjackTableModel'),
        MelString(b'MODT','extraBlackjackTableModel'),
        MelString(b'MOD4','rouletteTableModel'),
        MelGroups('slotReelTextures',
            MelIcon('texture'),
        ),
        MelGroups('blackjackDecks',
            MelIco2('texture'),
        ),
    )

#------------------------------------------------------------------------------
class MreDehy(MelRecord):
    """Dehydration Stage."""
    rec_sig = b'DEHY'

    melSet = MelSet(
        MelEdid(),
        MelStruct(b'DATA', ['2I'], 'trigerThreshold', (FID, 'actorEffect')),
    )

#------------------------------------------------------------------------------
class MreDial(MelRecord):
    """Dialogue."""
    rec_sig = b'DIAL'

    class _DialFlags(Flags):
        rumors: bool
        toplevel: bool

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
        MelSorted(MelSimpleGroups('removed_quests', MelFid(b'QSTR'))),
        MelFull(),
        MelFloat(b'PNAM', 'priority'),
        MelString(b'TDUM', 'dumb_response'),
        MelTruncatedStruct(b'DATA', ['2B'], 'dialType',
                           (_DialFlags, 'dialFlags'), old_versions={'B'}),
    ).with_distributor({
        b'INFC': 'broken_infc',
        b'INFX': 'broken_infx',
        b'QSTI': {
            b'INFC|INFX': 'added_quests',
        },
    })

#------------------------------------------------------------------------------
class MreHung(MelRecord):
    """Hunger Stage."""
    rec_sig = b'HUNG'

    melSet = MelSet(
        MelEdid(),
        MelStruct(b'DATA', ['2I'], 'trigerThreshold', (FID, 'actorEffect')),
    )

#------------------------------------------------------------------------------
class MreImod(MelRecord):
    """Item Mod."""
    rec_sig = b'IMOD'

    class HeaderFlags(MelRecord.HeaderFlags):
        quest_item: bool = flag(10)

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
        MelStruct(b'DATA',
            ['5I', 'f', 'I', '3f', 'I', '20s', 'I', '3f', '4s', 'I'],
            'type', 'data1X', 'data1Y', 'data1Width', 'data1Height',
            'data1Orientation', 'data1Font', 'data1ColorR', 'data1ColorG',
            'data1ColorB', 'data1Align', 'unknown1', 'data2Font',
            'data2ColorR', 'data2ColorG', 'data2ColorB', 'unknown2', 'stats'),
    )

#------------------------------------------------------------------------------
class MreMset(MelRecord):
    """Media Set."""
    rec_sig = b'MSET'

    class _flags(Flags):
        dayOuter: bool = flag(0)
        dayMiddle: bool = flag(1)
        dayInner: bool = flag(2)
        nightOuter: bool = flag(3)
        nightMiddle: bool = flag(4)
        nightInner: bool = flag(5)

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
        MelUInt8Flags(b'PNAM', 'enableFlags', _flags),
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
        MelStruct(b'DATA', ['4I'], 'recipe_skill', 'recipe_level',
            (FID, 'recipe_category'), (FID, 'recipe_subcategory')),
        MelGroups('recipe_ingredients',
            MelFid(b'RCIL', 'r_ingr_item'),
            MelUInt32(b'RCQY', 'r_ingr_quantity'),
        ),
        MelGroups('recipe_outputs',
            MelFid(b'RCOD', 'r_ingr_item'),
            MelUInt32(b'RCQY', 'r_ingr_quantity'),
        ),
    ).with_distributor({
        b'RCIL': {
            b'RCQY': 'recipe_ingredients',
        },
        b'RCOD': {
            b'RCQY': 'recipe_outputs',
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
        MelStruct(b'DATA', ['2I'], 'trigerThreshold', (FID, 'actorEffect')),
    )
