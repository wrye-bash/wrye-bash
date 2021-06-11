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
"""This module contains the skyrim SE record classes. The great majority are
imported from skyrim."""
from ...bolt import Flags
from ...brec import MelRecord, MelGroups, MelStruct, MelString, MelSet, \
    MelFloat, MelUInt32, MelCounter, MelEdid

#------------------------------------------------------------------------------
# Added in SSE ----------------------------------------------------------------
#------------------------------------------------------------------------------
class MreLens(MelRecord):
    """Lens Flare."""
    rec_sig = b'LENS'

    LensFlareFlags = Flags(0,Flags.getNames(
            (0, 'rotates'),
            (1, 'shrinksWhenOccluded'),
        ))

    melSet = MelSet(
        MelEdid(),
        MelFloat(b'CNAM', 'colorInfluence'),
        MelFloat(b'DNAM', 'fadeDistanceRadiusScale'),
        MelCounter(MelUInt32(b'LFSP', 'sprite_count'),
                   counts='lensFlareSprites'),
        MelGroups('lensFlareSprites',
            MelString(b'DNAM','spriteID'),
            MelString(b'FNAM','texture'),
            MelStruct(b'LFSD', [u'f', u'8I'], 'tintRed', 'tintGreen', 'tintBlue',
                'width', 'height', 'position', 'angularFade', 'opacity',
                (LensFlareFlags, u'lensFlags'), ),
        )
    ).with_distributor({
        b'DNAM': u'fadeDistanceRadiusScale',
        b'LFSP': {
            b'DNAM': u'lensFlareSprites',
        },
    })
    __slots__ = melSet.getSlotsUsed()

#------------------------------------------------------------------------------
class MreVoli(MelRecord):
    """Volumetric Lighting."""
    rec_sig = b'VOLI'

    melSet = MelSet(
        MelEdid(),
        MelFloat(b'CNAM', 'intensity'),
        MelFloat(b'DNAM', 'customColorContribution'),
        MelFloat(b'ENAM', 'red'),
        MelFloat(b'FNAM', 'green'),
        MelFloat(b'GNAM', 'blue'),
        MelFloat(b'HNAM', 'densityContribution'),
        MelFloat(b'INAM', 'densitySize'),
        MelFloat(b'JNAM', 'densityWindSpeed'),
        MelFloat(b'KNAM', 'densityFallingSpeed'),
        MelFloat(b'LNAM', 'phaseFunctionContribution'),
        MelFloat(b'MNAM', 'phaseFunctionScattering'),
        MelFloat(b'NNAM', 'samplingRepartitionRangeFactor'),
    )
    __slots__ = melSet.getSlotsUsed()
