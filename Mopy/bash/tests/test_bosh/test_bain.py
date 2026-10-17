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

from ... import bass, bolt, bush
from ...bolt import DataDict, FName, LowerDict
from ...bosh import bain
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
    """A project whose files we need not create - we set its file list."""
    def __init__(self, name, order, package_files):
        self._set_defaults() # skip the init, that needs the directories
        self.fileSizeCrcs = [(os.path.join(*f.split('/')), 1, 0) for f in
                             package_files]
        self._reset_cache() # detect the structure
        self.fn_key = FName(name)
        self.order = order
        self.is_active = True

    def _stat_tuple(self, cached_stat=None): return ()
    def _fs_refresh(self, progress, stat_tuple, **kwargs): pass
    def refreshDataSizeCrc(self, *args, **kwargs): return {}


def test_uninstall_all(monkeypatch):
    """Uninstall All (bain_uninstall(None)) uninstalls every package - it
    used to compare the packages with their names and raise (#761)."""
    monkeypatch.setattr(bass, 'settings', defaultdict(bool))
    monkeypatch.setattr(Installer, 'dataDirsPlus',
                        Installer.dataDirsPlus | bush.game.Bain.data_dirs)
    monkeypatch.setattr(bain, 'data_tracking_stores', lambda: [])
    packages = [_Package(f'Package {i}', i, ['Textures/a.dds'])
                for i in range(2)]
    idata = InstallersData.__new__(InstallersData) # skip the init
    DataDict.__init__(idata, {p.fn_key: p for p in packages})
    idata.data_sizeCrcDate = LowerDict()
    idata.refreshTracked = idata.refresh_ns = lambda *args: None
    idata.bain_uninstall(None, progress=bolt.Progress(), rui_data={})
    assert not any(p.is_active for p in packages)
