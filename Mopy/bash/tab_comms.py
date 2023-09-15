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
#  Wrye Bash copyright (C) 2005-2009 Wrye, 2010-2023 Wrye Bash Team
#  https://github.com/wrye-bash
#
# =============================================================================
"""Provides constants and tools for inter-tab communication."""
from collections import defaultdict

# Key Constants ---------------------------------------------------------------
KEY_BSAS        = 'bsa_store'
KEY_INIS        = 'ini_store'
KEY_INSTALLERS  = 'installer_store'
KEY_MODS        = 'mod_store'
KEY_SAVES       = 'save_store'
KEY_SCREENSHOTS = 'screenshot_store'

# Shorthands ------------------------------------------------------------------
def _gen_shorthand(store_key):
    return defaultdict(bool, {store_key: True})
BSAS        = _gen_shorthand(KEY_BSAS)
INIS        = _gen_shorthand(KEY_INIS)
INSTALLERS  = _gen_shorthand(KEY_INSTALLERS)
MODS        = _gen_shorthand(KEY_MODS)
SAVES       = _gen_shorthand(KEY_SAVES)
SCREENSHOTS = _gen_shorthand(KEY_SCREENSHOTS)

def _gen_cond_shorthand(store_key):
    return lambda c: (_gen_shorthand(store_key) if c else defaultdict(bool))
BSAS_IF        =_gen_cond_shorthand(KEY_BSAS)
INIS_IF        =_gen_cond_shorthand(KEY_INIS)
INSTALLERS_IF  =_gen_cond_shorthand(KEY_INSTALLERS)
MODS_IF        =_gen_cond_shorthand(KEY_MODS)
SAVES_IF       =_gen_cond_shorthand(KEY_SAVES)
SCREENSHOTS_IF =_gen_cond_shorthand(KEY_SCREENSHOTS)
