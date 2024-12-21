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
from ....patcher.patchers.preservers import APreserver

class ImportWeaponModificationsPatcher(APreserver):
    """Merge changes to weapon modifications for FalloutNV."""
    patcher_name = _(u'Import Weapon Modifications')
    patcher_desc = _(u'Merges changes to weapon modifications.')
    patcher_tags = {'WeaponMods'}
    _config_key = u'WeaponModsPatcher'
    patcher_order = 27 ##: This seems unneeded + no reason given
    rec_attrs = {b'WEAP': (
        'modelWithMods', 'firstPersonModelWithMods', 'weaponMods',
        'effectMod1', 'effectMod2', 'effectMod3', 'valueAMod1', 'valueAMod2',
        'valueAMod3', 'valueBMod1', 'valueBMod2', 'valueBMod3',
        'reloadAnimationMod', 'vats_mod_required', 'dnamFlags2.scopeFromMod')}
    _fid_rec_attrs = {b'WEAP': ('sound_mod1_shoot_3d', 'sound_mod1_shoot_dist',
                                'sound_mod1_shoot_2d')}

    @classmethod
    def gui_cls_vars(cls):
        """Class variables for gui patcher classes created dynamically."""
        return {u'patcher_type': cls, u'patcher_desc': cls.patcher_desc,
            'patcher_name': cls.patcher_name, '_config_key': cls._config_key}
