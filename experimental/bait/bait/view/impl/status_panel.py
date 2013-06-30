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
        presenter.AnnealOperationIds.COPY:"Adding",
        presenter.AnnealOperationIds.DELETE:"Deleting",
        presenter.AnnealOperationIds.OVERWRITE:"Updating"
    }


def _node_label_generator(nodeIds, nodeIdToLabelMap):
    for nodeId in nodeIds:
        yield nodeIdToLabelMap[nodeId]

def _make_str(strings, separator):
    outStr = StringIO()
    isFirst = True
    for string in strings:
        if not isFirst: outStr.write(separator)
        outStr.write(string)
        isFirst = False
    return outStr.getvalue()

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


class StatusPanel:
    def __init__(self, wxParent, sizer, presenter_,):
        # MinSize not set for any panel since this panel should not restrict sizing
        basePanel = wx.Panel(wxParent, style=wx.SUNKEN_BORDER)
        self._wxParent = wxParent

        # "ok" panel
        okPanel = self._okPanel = wx.Panel(basePanel)
        dataStats = self._dataStats = wx.StaticText(okPanel)
        okSizer = wx.BoxSizer(wx.HORIZONTAL)
        okSizer.Add(dataStats, 0, wx.ALIGN_CENTER_VERTICAL)
        okPanel.SetSizer(okSizer)

        # "dirty" panel
        dirtyPanel = self._dirtyPanel = wx.Panel(basePanel)
        annealAllButton = wx.Button(dirtyPanel, label="Anneal all now")
        # TODO: attach anneal all action to button
        dirtyText = self._dirtyText = wx.StaticText(dirtyPanel)
        dirtySizer = wx.BoxSizer(wx.HORIZONTAL)
        dirtySizer.Add(annealAllButton, 0, wx.ALIGN_CENTER_VERTICAL)
        dirtySizer.Add(dirtyText, 0, wx.ALIGN_CENTER_VERTICAL)
        dirtyPanel.SetSizer(dirtySizer)

        # "loading" panel
        loadingPanel = self._loadingPanel = wx.Panel(basePanel)
        loadingText = wx.StaticText(loadingPanel, label="Loading packages: ")
        loadingPercent = self._loadingPercent = wx.Gauge(loadingPanel)
        loadingSizer = wx.BoxSizer(wx.HORIZONTAL)
        loadingSizer.Add(loadingText, 0, wx.ALIGN_CENTER_VERTICAL)
        loadingSizer.Add(loadingPercent, 0, wx.ALIGN_CENTER_VERTICAL)
        loadingPanel.SetSizer(loadingSizer)

        # "doing I/O" panel
        ioPanel = self._ioPanel = wx.Panel(basePanel)
        iopsText = self._iopsText = wx.StaticText(ioPanel)
        ioSizer = wx.BoxSizer(wx.HORIZONTAL)
        ioSizer.Add(iopsText, 0, wx.ALIGN_CENTER_VERTICAL)
        ioPanel.SetSizer(ioSizer)

        statusSizer = wx.BoxSizer(wx.HORIZONTAL)
        statusSizer.Add(okPanel, 1, wx.ALIGN_CENTER_VERTICAL)
        statusSizer.Add(dirtyPanel, 1, wx.ALIGN_CENTER_VERTICAL)
        statusSizer.Add(loadingPanel, 1, wx.ALIGN_CENTER_VERTICAL)
        statusSizer.Add(ioPanel, 1, wx.ALIGN_CENTER_VERTICAL)
        basePanel.SetSizer(statusSizer)
        sizer.Add(basePanel, 0, wx.EXPAND|wx.TOP|wx.BOTTOM, 3)

        okPanel.Hide()
        loadingPanel.Hide()
        dirtyPanel.Hide()
        # needed on Windows to ensure the panel doesn't disappear
        basePanel.SetMinSize((0, basePanel.GetBestSize()[1]))
        ioPanel.Hide()

        self._curPanel = self._okPanel
        self._presenter = presenter_

        self.set_ok(None, *[0]*6)


    def set_ok(self, highlightColor, numInstalledFiles, numLibraryFiles, installedMb,
               libraryMb, freeInstalledMb, freeLibraryMb):
        if freeInstalledMb == freeLibraryMb:
            label = "Library: %d (%d MB), Installed: %d (%d MB), Free: %d MB" % \
                  (numLibraryFiles, libraryMb,
                   numInstalledFiles, installedMb, freeLibraryMb)
            tooltip = "%d files (%d MB) in packages managed by Wrye Bash, " \
                    "%d files (%d MB) installed, %d MB free on hard drive" % \
                    (numLibraryFiles, libraryMb,
                     numInstalledFiles, installedMb, freeLibraryMb)
        else:
            label = "Library: %d (%d MB, %d Free), Installed: %d (%d MB, %d Free)" % \
                  (numLibraryFiles, libraryMb, freeLibraryMb,
                   numInstalledFiles, installedMb, freeInstalledMb)
            tooltip = "%d files (%d MB) in packages managed by Wrye Bash, " \
                    "%d MB free in package directory, " \
                    "%d files (%d MB) installed, %d MB free in Data directory" % \
                    (numLibraryFiles, libraryMb, freeLibraryMb,
                     numInstalledFiles, installedMb, freeInstalledMb)
        _logger.debug("showing 'ok' panel; data stats: '%s'", label)
        self._dataStats.SetLabel(label)
        self._okPanel.SetToolTipString(tooltip)
        self._switch_to_panel(self._okPanel, highlightColor)

    def set_dirty(self, highlightColor, dirtyPackageNodeIds, nodeIdToLabelMap):
        _logger.debug("showing 'dirty' panel; dirty packages: %s", dirtyPackageNodeIds)
        self._dirtyText.SetLabel(_make_str(
            _node_label_generator(dirtyPackageNodeIds, nodeIdToLabelMap), ', '))
        self._dirtyPanel.SetToolTipString(
            "Please see the highlighted packages below for details on what needs"
            "annealing, or click the 'Anneal all now' button to autofix.\n" +
            _make_str(_node_label_generator(dirtyPackageNodeIds, nodeIdToLabelMap), '\n'))
        self._switch_to_panel(self._dirtyPanel, highlightColor)

    def set_loading(self, highlightColor, complete, total):
        _logger.debug("showing 'loading' panel; num complete: %d/%d", complete, total)
        self._loadingPercent.SetRange(total)
        self._loadingPercent.SetValue(complete)
        self._switch_to_panel(self._loadingPanel, highlightColor)

    def set_doing_io(self, highlightColor, ioOperations):
        _logger.debug("showing 'io' panel; operations: %s", ioOperations)
        self._iopsText.SetLabel(_make_iops_str(ioOperations, ", "))
        self._ioPanel.SetToolTipString(_make_iops_str(ioOperations, "\n"))
        self._switch_to_panel(self._ioPanel, highlightColor)

    def _switch_to_panel(self, targetPanel, highlightColor):
        targetPanel.SetBackgroundColour(highlightColor)
        if self._curPanel != targetPanel:
            self._curPanel.Hide()
            targetPanel.Show()
            self._curPanel = targetPanel
            # ensure panel is properly sized
            self._wxParent.Layout()