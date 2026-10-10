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
#  Wrye Bash copyright (C) 2005-2009 Wrye, 2010-2026 Wrye Bash Team
#  https://github.com/wrye-bash
#
# =============================================================================
import os

from ...bosh.bain import InstallerProject, _remove_empty_dirs
from ...wbtemp import TempDir

def test__remove_empty_dirs():
    with TempDir() as tempdir:
        os.mkdir(tex := os.path.join(tempdir, 'textures'))
        os.mkdir(cl := os.path.join(tex, 'clothes'))
        os.mkdir(os.path.join(cl, 'farmclothes02'))
        _remove_empty_dirs(tex)
        assert not os.path.exists(cl)


class _Package(InstallerProject):
    """A project whose files we need not create - we set its file list and
    only care for the structure that is detected from that."""
    def __init__(self, package_files, install_to_game_root):
        self._set_defaults()  # skip the init, that needs the directories
        self.fileSizeCrcs = [(os.path.join(*f.split('/')), 0, 0) for f in
                             package_files]
        self.install_to_game_root = install_to_game_root
        self._reset_cache()

    def _stat_tuple(self, cached_stat=None): return ()
    def _fs_refresh(self, progress, stat_tuple, **kwargs): pass
    def refreshDataSizeCrc(self, *args, **kwargs): return {}


def _structure(package_files, install_to_game_root):
    """Return the wrapper directory, the BAIN type and the sub-packages
    detected for a package containing package_files."""
    package = _Package(package_files, install_to_game_root)
    return (package.extras_dict.get('root_path', '').rstrip(os.sep),
            package.bain_type, package.subNames[1:])


def test_data_package_structure():
    """Installing to the game root must not change how the packages that
    are laid out for the Data folder are detected."""
    simple = ['Plugin.esp', 'Docs/Readme.txt']
    complex_ = ['00 Core/Plugin.esp', '01 Extra/Docs/Readme.txt']
    wrapped = ['Some Mod 1.0/Plugin.esp', 'Some Mod 1.0/Docs/Readme.txt']
    for game_root in (False, True):
        assert _structure(simple, game_root) == ('', 1, [])
        assert _structure(complex_, game_root) == (
            '', 2, ['00 Core', '01 Extra'])
        assert _structure(wrapped, game_root) == ('Some Mod 1.0', 1, [])


def test_game_root_package_structure():
    # A top level binary - not recognized, unless we install to the game root
    flat = ['d3d11.dll', 'enbseries/effect.fx']
    assert _structure(flat, False) == ('', 0, [])
    assert _structure(flat, True) == ('', 1, [])
    # A wrapper directory is dropped
    wrapped = ['Some Preset/d3d11.dll', 'Some Preset/enbseries/effect.fx']
    assert _structure(wrapped, False) == ('Some Preset', 0, [])
    assert _structure(wrapped, True) == ('Some Preset', 1, [])
    # ...but the directories we expect in the game folder are not wrappers
    for game_dir in ('enbseries', 'reshade-shaders', 'Data'):
        assert _structure([f'{game_dir}/Sub/effect.fx'], True) == ('', 1, [])
        nested = [f'Some Preset/{game_dir}/Sub/effect.fx']
        assert _structure(nested, True) == ('Some Preset', 1, [])
    # ...nor are they sub-packages
    mixed = ['Data/Textures/a.dds', 'Other/effect.fx']
    assert _structure(mixed, True) == ('', 1, [])
    # Sub-packages are detected by what they contain - binaries
    binaries = ['Version A/d3d11.dll', 'Version B/Injector.exe']
    assert _structure(binaries, False) == ('', 0, [])
    assert _structure(binaries, True) == ('', 2, ['Version A', 'Version B'])
    # ...or the directories we expect in the game folder
    options = ['00 Main/enbseries/effect.fx', '01 Extra/Data/Textures/a.dds',
               'Extras/Nested/enbseries/effect.fx']
    assert _structure(options, False) == ('', 0, [])
    assert _structure(options, True) == ('', 2, ['00 Main', '01 Extra'])
