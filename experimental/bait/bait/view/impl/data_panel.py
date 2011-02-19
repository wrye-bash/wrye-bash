# -*- coding: utf-8 -*-
#
# bait/view/impl/data_panel.py
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

import logging
import wx
import wx.lib.platebtn


_logger = logging.getLogger(__name__)


class DataPanel(wx.Panel):
    def __init__(self, parent, presenter_,):
        wx.Panel.__init__(self, parent, style=wx.SUNKEN_BORDER)
        self._presenter = presenter_

        dataLabel = wx.StaticText(self, label=" Installed Data")
        dataSyncButton = wx.lib.platebtn.PlateButton(self, bmp=wx.ArtProvider.GetBitmap(wx.ART_HELP_SIDE_PANEL, client=wx.ART_BUTTON))
        self._dataStats = wx.StaticText(self)
        self.set_stats(0, 0, 0, 0)

        dataSyncButton.SetToolTipString("Anneal all")

        dataSizer = wx.BoxSizer(wx.HORIZONTAL)
        dataSizer.Add(dataLabel, 0, wx.ALIGN_CENTER_VERTICAL)
        dataSizer.Add(dataSyncButton, 0, wx.ALIGN_CENTER_VERTICAL)
        dataSizer.Add(self._dataStats, 0, wx.ALIGN_CENTER_VERTICAL)
        self.SetMinSize(dataSizer.GetMinSize())
        self.SetSizer(dataSizer)


    def set_stats(self, activePlugins, totalPlugins, knownFiles, totalFiles):
        label = "Plugins: %d/%d, Files: %d/%d" % (activePlugins, totalPlugins, knownFiles, totalFiles)
        _logger.debug("data label changing to: '%s'", label)
        self._dataStats.SetLabel(label)
        tooltip = "%d of %d plugins active, %d of %d installed files managed by Wrye Bash" % (activePlugins, totalPlugins, knownFiles, totalFiles)
        self._dataStats.SetToolTipString(tooltip)
