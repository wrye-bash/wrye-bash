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
from collections import defaultdict
from types import SimpleNamespace

from ... import bass, bush
from ...bolt import DataDict, FName, LowerDict
from ...bosh.bain import Installer, InstallerProject, InstallersData, \
    _remove_empty_dirs
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


def _init_bain(monkeypatch):
    """All BAIN settings off, except for showing lower conflicts, and the
    directories of the game's Data folder known."""
    monkeypatch.setattr(bass, 'settings', defaultdict(
        bool, {'bash.installers.conflictsReport.showLower': True}))
    monkeypatch.setattr(Installer, 'dataDirsPlus',
                        Installer.dataDirsPlus | bush.game.Bain.data_dirs)
    Installer.init_attributes_process()


def _package(package_files, install_to_game_root, order=0, sub_actives=None):
    """Return an active package with its destinations - package_files maps
    the paths of the files in the package to their CRCs."""
    package = _Package(package_files, install_to_game_root)
    package.fileSizeCrcs = [(os.path.join(*f.split('/')), 1, crc) for f, crc
                            in package_files.items()]
    package.fn_key = FName(f'Package {order}')
    package.order = order
    if sub_actives is not None:
        package.subActives = [True, *sub_actives]
    package.is_active = True
    package.refresh_dest_srcs()
    return package


def _paths(*files):
    return {os.path.join(*f.split('/')).lower() for f in files}


def _lower(paths):
    return {p.lower() for p in paths}


def test_game_root_package_destinations(monkeypatch):
    """The files in the Data folder of a package that installs to the game
    root go through the same rules as the files of any other package,
    relative to the Data folder - the rest go to the game folder the way
    they are laid out in the package."""
    _init_bain(monkeypatch)
    vanilla_master = min(f for f in bush.game.bethDataFiles if
                         f.endswith('.esm'))
    package = _package(dict.fromkeys([
        'binary.dll', 'Plugin.esp', 'enbseries/effect.fx', 'wizard.txt',
        'Data/Plugin.esp', 'Data/Textures/a.dds', f'Data/{vanilla_master}',
        'Data/Unknown/b.nif'], 0), True)
    # the vanilla master and the unknown directory are skipped
    assert _lower(package.ci_dest_sizeCrc) == _paths('Plugin.esp',
                                                    'Textures/a.dds')
    # a file outside the Data folder may have the same path as one in it -
    # and the wizard is not installed
    assert _lower(package.ci_root_sizeCrc) == _paths(
        'binary.dll', 'Plugin.esp', 'enbseries/effect.fx')
    assert package.hasWizard
    # both are mapped to their path in the package for installing them
    dest_src, root_dest_src = package.refresh_dest_srcs()
    assert dest_src['Plugin.esp'] == os.path.join('Data', 'Plugin.esp')
    assert root_dest_src['Plugin.esp'] == 'Plugin.esp'
    # shown relative to the game folder
    assert _lower(package.to_install_root(
        package.ci_dest_sizeCrc, package.ci_root_sizeCrc)) == _paths(
        'binary.dll', 'Plugin.esp', 'enbseries/effect.fx', 'Data/Plugin.esp',
        'Data/Textures/a.dds')
    # the Data folder of a sub-package
    package = _package(dict.fromkeys([
        '00 Core/binary.dll', '00 Core/Data/Plugin.esp',
        '01 Extra/enbseries/effect.fx', '01 Extra/Data/Textures/a.dds'], 0),
        True, sub_actives=[True, False])
    assert _lower(package.ci_dest_sizeCrc) == _paths('Plugin.esp')
    assert _lower(package.ci_root_sizeCrc) == _paths('binary.dll')
    # a package that installs to Data has no files for the game folder
    package = _package(dict.fromkeys(['Plugin.esp', 'Data/a.dds'], 0), False)
    assert _lower(package.ci_dest_sizeCrc) == _paths('Plugin.esp')
    assert not package.ci_root_sizeCrc


def test_game_root_package_fomod_dir(monkeypatch):
    """The fomod folder of a package that installs to the game root is not
    installed to the game folder."""
    _init_bain(monkeypatch)
    package = _package(dict.fromkeys([
        'binary.dll', 'fomod/info.xml', 'fomod/images/a.png',
        'fomod/ModuleConfig.xml'], 0), True)
    assert _lower(package.ci_root_sizeCrc) == _paths('binary.dll')
    # the same in a sub-package
    package = _package(dict.fromkeys([
        '00 Core/binary.dll', '00 Core/fomod/info.xml',
        '01 Extra/enbseries/effect.fx'], 0), True, sub_actives=[True, False])
    assert _lower(package.ci_root_sizeCrc) == _paths('binary.dll')


def test_game_root_package_conflicts(monkeypatch):
    """The files in the Data folder of packages that install to the game
    root conflict with the files of any other package, the files in the game
    folder only with the ones other packages install there."""
    _init_bain(monkeypatch)
    low = _package({'enbseries/a.fx': 1, 'Data/Scripts/a.pex': 1}, True, 0)
    src = _package({'enbseries/a.fx': 2, 'Data/Scripts/a.pex': 2,
                    'Scripts/c.pex': 2, 'binary.dll': 2}, True, 1)
    high = _package({'Scripts/a.pex': 3, 'Scripts/c.pex': 3}, False, 2)
    monkeypatch.setattr(Installer, 'instData', SimpleNamespace(
        sorted_values=lambda: [low, src, high]))
    lower, higher, *_bsas = src._InstallerPackage__find_conflicts(True, None)
    assert [(i, _lower(c)) for i, c in lower] == [
        (low, _paths('enbseries/a.fx', 'Data/Scripts/a.pex'))]
    # Scripts/c.pex of src goes to the game folder, not to Data
    assert [(i, _lower(c)) for i, c in higher] == [
        (high, _paths('Data/Scripts/a.pex'))]
    # the other way round
    lower, higher, *_bsas = high._InstallerPackage__find_conflicts(True, None)
    assert [(i, _lower(c)) for i, c in lower] == [
        (low, _paths('Scripts/a.pex')), (src, _paths('Scripts/a.pex'))]
    assert not higher


def test_game_root_package_uninstall(monkeypatch):
    """Uninstalling a package that installs to the game root removes its
    files from the game folder and from Data - and restores the ones lower
    packages install."""
    _init_bain(monkeypatch)
    low = _package({'enbseries/a.fx': 1, 'Data/Scripts/a.pex': 1}, True, 0)
    src = _package({'enbseries/a.fx': 2, 'Data/Scripts/a.pex': 2,
                    'Data/Scripts/b.pex': 2, 'binary.dll': 2}, True, 1)
    high = _package({'Scripts/b.pex': 3}, False, 2)
    idata = InstallersData.__new__(InstallersData) # skip the init
    DataDict.__init__(idata, {p.fn_key: p for p in (low, src, high)})
    # what is on disk - src overwrote the files of low, high those of src
    idata.data_sizeCrcDate = LowerDict({
        os.path.join('Scripts', 'a.pex'): (1, 2, 0),
        os.path.join('Scripts', 'b.pex'): (1, 3, 0)})
    idata.game_root_sizeCrcDate = LowerDict({
        os.path.join('enbseries', 'a.fx'): (1, 2, 0),
        'binary.dll': (1, 2, 0)})
    removed_restored = []
    monkeypatch.setattr(idata, '_remove_restore',
                        lambda *args, **kwargs: removed_restored.extend(args))
    InstallersData.bain_uninstall.__wrapped__(
        idata, [src.fn_key], cede_ownership=defaultdict(set))
    (removes, root_removes), (restores, root_restores) = removed_restored[:2]
    assert not src.is_active
    # Scripts/a.pex is restored from low, Scripts/b.pex belongs to high
    assert not removes
    assert _lower(root_removes) == _paths('binary.dll')
    assert {k.lower(): v for k, v in restores.items()} == {
        os.path.join('scripts', 'a.pex'): low.fn_key}
    assert {k.lower(): v for k, v in root_restores.items()} == {
        os.path.join('enbseries', 'a.fx'): low.fn_key}
