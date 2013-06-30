# -*- coding: utf-8 -*-
#
# bait/view/impl/filter_registry_test.py
#
# GPL License and Copyright Notice ============================================
#  This file is part of Wrye Bash.
#
#  Wrye Bash is free software: you can redistribute it and/or modify
#  it under the terms of the GNU General Public License as published by
#  the Free Software Foundation, either version 3 of the License, or
#  (at your option) any later version.
#
#  Wrye Bash is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
#
#  You should have received a copy of the GNU General Public License
#  along with Wrye Bash.  If not, see <http://www.gnu.org/licenses/>.
#
#  Wrye Bash Copyright (C) 2011 Myk Taylor
#
# =============================================================================

from ... import presenter
from . import filter_registry


class _DummyParent:
    def Layout(self): pass
    def Fit(self): pass
class _DummyToggleButton:
    def __init__(self):
        self.label = None
        self.minsize = (10, 10)
        self.bestsize = (20, 20)
        self.size = (30, 30)
        self.value = None
        self.parent = _DummyParent()
    def SetLabel(self, label): self.label = label
    def SetMinSize(self, minsize): self.minsize = minsize
    def SetValue(self, value): self.value = value
    def GetBestSize(self): return self.bestsize
    def GetSize(self): return self.size
    def GetParent(self): return self.parent


def filter_registry_test():
    fr = filter_registry.FilterRegistry()

    instButton = _DummyToggleButton()
    uninstButton = _DummyToggleButton()
    hiddenButton = _DummyToggleButton()

    filterMask = presenter.FilterIds.PACKAGES_INSTALLED

    fr.init_filter_states({})
    fr.init_filter_states(filterMask)
    fr.add_filter(presenter.FilterIds.PACKAGES_INSTALLED, "Installed", None)
    fr.add_filter(presenter.FilterIds.PACKAGES_INSTALLED, "Installed", instButton)
    fr.add_filter(presenter.FilterIds.PACKAGES_NOT_INSTALLED,
                  "Not Installed", uninstButton)
    fr.add_filter(presenter.FilterIds.PACKAGES_HIDDEN, "Hidden", hiddenButton)

    assert instButton.value is None
    assert uninstButton.value is None
    assert hiddenButton.value is None
    fr.init_filter_states(filterMask)
    assert instButton.value is True
    assert uninstButton.value is False
    assert hiddenButton.value is False

    fr.set_filter_stats(presenter.FilterIds.PACKAGES_INSTALLED, 10, 20, False)
    assert instButton.label == "Installed (10/20)"
    assert instButton.minsize == (20, 30)

    fr.set_filter_stats(presenter.FilterIds.PACKAGES_NOT_INSTALLED, 0, 0)
    assert uninstButton.label == "Not Installed (0)"
    assert uninstButton.minsize == (20, 30)

    fr.set_filter_stats(presenter.FilterIds.PACKAGES_HIDDEN, 10, 10)
    assert hiddenButton.label == "Hidden (10)"
    assert hiddenButton.minsize == (20, 30)
