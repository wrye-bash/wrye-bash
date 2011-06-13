# -*- coding: utf-8 -*-
#
# bait/view/impl/status_panel.py
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
from cStringIO import StringIO

from ... import presenter


_logger = logging.getLogger(__name__)
_operationNames = {
        presenter.AnnealOperations.COPY:"Copying",
        presenter.AnnealOperations.DELETE:"Deleting",
        presenter.AnnealOperations.RENAME:"Renaming"
    }

def _make_iops_str(ioOperations, separator):
    outStr = StringIO()
    isFirst = True
    for ioOperation in ioOperations:
        if not isFirst: outStr.write(separator)
        outStr.write(_operationNames[ioOperation.type])
        outStr.write(": '")
        outStr.write(ioOperation.target)
        outStr.write("'")
        isFirst = False
    return outStr.getvalue()


class StatusPanel(wx.Panel):
    def __init__(self, parent, presenter_,):
        wx.Panel.__init__(self, parent, style=wx.SUNKEN_BORDER)
        self._presenter = presenter_

        # "ok" panel
        # Show "ok", installed statistics
        okPanel = self._okPanel = wx.Panel(self)
        dataStats = self._dataStats = wx.StaticText(okPanel)
        okSizer = wx.BoxSizer(wx.HORIZONTAL)
        okSizer.Add(dataStats, 0, wx.ALIGN_CENTER_VERTICAL)
        okPanel.SetSizer(okSizer)

        # "loading" panel
        loadingPanel = self._loadingPanel = wx.Panel(self)
        loadingText = wx.StaticText(loadingPanel, label="Loading packages: ")
        loadingPercent = self._loadingPercent = wx.Gauge(loadingPanel)
        loadingSizer = wx.BoxSizer(wx.HORIZONTAL)
        loadingSizer.Add(loadingText, 0, wx.ALIGN_CENTER_VERTICAL)
        loadingSizer.Add(loadingPercent, 0, wx.ALIGN_CENTER_VERTICAL)
        loadingPanel.SetSizer(loadingSizer)

        # "needs annealing" panel
        dirtyPanel = self._dirtyPanel = wx.Panel(self)
        annealAllButton = wx.Button(dirtyPanel, label="Anneal all now")
        dirtyText = wx.StaticText(dirtyPanel, label="Data needs annealing")
        dirtyPanel.SetToolTipString("Please see the highlighted packages below for details on what needs annealing, or click the button to anneal all.")
        dirtySizer = wx.BoxSizer(wx.HORIZONTAL)
        dirtySizer.Add(annealAllButton, 0, wx.ALIGN_CENTER_VERTICAL)
        dirtySizer.Add(dirtyText, 0, wx.ALIGN_CENTER_VERTICAL)
        dirtyPanel.SetSizer(dirtySizer)

        # "doing IO" panel
        # show cancel button, comma separated list of actions that trail off the right side of the panel
        ioPanel = self._ioPanel = wx.Panel(self)
        iopsText = self._iopsText = wx.StaticText(ioPanel)
        ioSizer = wx.BoxSizer(wx.HORIZONTAL)
        ioSizer.Add(iopsText, 0, wx.ALIGN_CENTER_VERTICAL)
        ioPanel.SetSizer(ioSizer)

        statusSizer = wx.BoxSizer(wx.HORIZONTAL)
        statusSizer.Add(okPanel, 1, wx.ALIGN_CENTER_VERTICAL)
        statusSizer.Add(loadingPanel, 1, wx.ALIGN_CENTER_VERTICAL)
        statusSizer.Add(dirtyPanel, 1, wx.ALIGN_CENTER_VERTICAL)
        statusSizer.Add(ioPanel, 1, wx.ALIGN_CENTER_VERTICAL)
        self.SetSizer(statusSizer)

        okPanel.Hide()
        loadingPanel.Hide()
        dirtyPanel.Hide()
        ioPanel.Hide()

        self._curPanel = self._okPanel


    def set_ok_status(self, hilightColor, activePlugins, totalPlugins, knownFiles, totalFiles):
        label = "Plugins: %d/%d, Files: %d/%d" % (activePlugins, totalPlugins, knownFiles, totalFiles)
        _logger.debug("showing 'ok' panel; data stats: '%s'", label)
        self._dataStats.SetLabel(label)
        tooltip = "%d of %d plugins active, %d of %d installed files managed by Wrye Bash" % (activePlugins, totalPlugins, knownFiles, totalFiles)
        self._okPanel.SetToolTipString(tooltip)
        self._okPanel.SetBackgroundColour(hilightColor)
        self._curPanel.Hide()
        self._okPanel.Show()
        self._curPanel = self._okPanel

    def set_loading_status(self, hilightColor, current, total):
        _logger.debug("showing 'loading' panel; num complete: %d/%d", current, total)
        self._loadingPercent.SetRange(total)
        self._loadingPercent.SetValue(current)
        self._loadingPanel.SetBackgroundColour(hilightColor)
        self._curPanel.Hide()
        self._loadingPanel.Show()
        self._curPanel = self._loadingPanel

    def set_dirty_status(self, hilightColor):
        _logger.debug("showing 'dirty' panel")
        self._dirtyPanel.SetBackgroundColour(hilightColor)
        self._curPanel.Hide()
        self._dirtyPanel.Show()
        self._curPanel = self._dirtyPanel

    def set_io_status(self, hilightColor, ioOperations):
        _logger.debug("showing 'io' panel; %d operations", len(ioOperations))
        self._iopsText.SetLabel(_make_iops_str(ioOperations, ", "))
        self._ioPanel.SetToolTipString(_make_iops_str(ioOperations, "\n"))
        self._ioPanel.SetBackgroundColour(hilightColor)
        self._curPanel.Hide()
        self._ioPanel.Show()
        self._curPanel = self._ioPanel
