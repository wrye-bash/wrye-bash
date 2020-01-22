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
"""This module contains the skyrim SE record classes. The great majority are
imported from skyrim."""
from ...bolt import Flags
from ...brec import MelRecord, MelGroups, MelStruct, MelString, MelSet, \
    MelFloat, MelUInt32, MelCounter, MelEdid
# Those are unused here, but need be in this file as are accessed via it
from ..skyrim.records import MreTes4, MreGmst

#------------------------------------------------------------------------------
# Added in SSE ----------------------------------------------------------------
#------------------------------------------------------------------------------
class MreVoli(MelRecord):
    """Volumetric Lighting."""
    classType = 'VOLI'

    melSet = MelSet(
        MelEdid(),
        MelFloat('CNAM', 'intensity'),
        MelFloat('DNAM', 'customColorContribution'),
        MelFloat('ENAM', 'red'),
        MelFloat('FNAM', 'green'),
        MelFloat('GNAM', 'blue'),
        MelFloat('HNAM', 'densityContribution'),
        MelFloat('INAM', 'densitySize'),
        MelFloat('JNAM', 'densityWindSpeed'),
        MelFloat('KNAM', 'densityFallingSpeed'),
        MelFloat('LNAM', 'phaseFunctionContribution'),
        MelFloat('MNAM', 'phaseFunctionScattering'),
        MelFloat('NNAM', 'samplingRepartitionRangeFactor'),
    )
    __slots__ = melSet.getSlotsUsed()

#------------------------------------------------------------------------------
class MreLens(MelRecord):
    """Lens Flare."""
    classType = 'LENS'

    LensFlareFlags = Flags(0,Flags.getNames(
            (0, 'rotates'),
            (1, 'shrinksWhenOccluded'),
        ))

    melSet = MelSet(
        MelEdid(),
        MelFloat('CNAM', 'colorInfluence'),
        MelFloat('DNAM', 'fadeDistanceRadiusScale'),
        MelCounter(MelUInt32('LFSP', 'sprite_count'),
                   counts='lensFlareSprites'),
        MelGroups('lensFlareSprites',
            MelString('DNAM','spriteID'),
            MelString('FNAM','texture'),
            MelStruct('LFSD', 'f8I', 'tintRed', 'tintGreen', 'tintBlue',
                'width', 'height', 'position', 'angularFade', 'opacity',
                (LensFlareFlags, 'lensFlags', 0), ),
        )
    ).with_distributor({
        'DNAM': 'fadeDistanceRadiusScale',
        'LFSP': {
            'DNAM': 'lensFlareSprites',
        },
    })
    __slots__ = melSet.getSlotsUsed()
