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
#  Wrye Bash copyright (C) 2005-2009 Wrye, 2010-2026 Wrye Bash Team
#  https://github.com/wrye-bash
#
# =============================================================================
"""Tests for the game packages."""
from ..bolt import FName
from ..game.starfield import SteamStarfieldGameInfo

def test_sf_strings_bsas():
    """BlueprintShips-X.esm may keep its strings in the BA2s of X."""
    av_bsas = {FName(b): b for b in ('SFBGS050 - Main.ba2',
        'SFBGS050 - Textures.ba2', 'sfta03 - main.ba2',
        'BlueprintShips-Starfield - Localization.ba2',
        'Starfield - Localization.ba2', 'Other - Main.ba2')}
    def _str_bsas(plugin):
        return SteamStarfieldGameInfo.Bsa.attached_bsas(av_bsas,
            FName(plugin), for_strings=True)
    sfbgs050_bsas = ['SFBGS050 - Main.ba2', 'SFBGS050 - Textures.ba2']
    assert _str_bsas('BlueprintShips-SFBGS050.esm') == sfbgs050_bsas
    assert _str_bsas('blueprintships-sfta03.esm') == ['sfta03 - main.ba2']
    # Their own BA2s come first
    assert _str_bsas('BlueprintShips-Starfield.esm') == [
        'BlueprintShips-Starfield - Localization.ba2',
        'Starfield - Localization.ba2']
    # Any other plugin only gets its own
    assert _str_bsas('SFBGS050.esm') == sfbgs050_bsas
    assert _str_bsas('Other.esp') == ['Other - Main.ba2']
    assert _str_bsas('Unrelated.esm') == []
    # The BA2s the game attaches to them are their own only
    assert SteamStarfieldGameInfo.Bsa.attached_bsas(av_bsas,
        FName('BlueprintShips-SFBGS050.esm')) == []
