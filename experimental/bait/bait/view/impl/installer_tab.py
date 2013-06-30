# -*- coding: utf-8 -*-
#
# bait/view/impl/installer_tab.py
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
import wx.gizmos

from ... import presenter
from . import settings_buttons, status_panel, filtered_tree, package_contents_panel


_logger = logging.getLogger(__name__)


class InstallerTab:
    def __init__(self, wxParentNotebook, presenter_, filterRegistry, viewIoGateway):
        topSizer = wx.BoxSizer(wx.VERTICAL)
        topPanel = self._topPanel = wx.Panel(wxParentNotebook)

        # work around color weirdness on windows
        backgroundColor = topPanel.GetBackgroundColour()
        wxParentNotebook.SetBackgroundColour(backgroundColor)

        # assemble widget hierarchy
        # top-level splitter between left and right panels
        splitterStyle = wx.NO_BORDER|wx.SP_LIVE_UPDATE|wx.FULL_REPAINT_ON_RESIZE
        topSplitter = wx.gizmos.ThinSplitterWindow(topPanel, style=splitterStyle)
        topSizer.Add(topSplitter, 1, wx.EXPAND)

        # main section
        mainSizer = wx.BoxSizer(wx.VERTICAL)
        mainPanel = wx.Panel(topSplitter)

        # global settings button and search bar
        searchSizer = wx.BoxSizer(wx.HORIZONTAL)
        self.globalSettingsButton = settings_buttons.GlobalSettingsButton(
            mainPanel, searchSizer)
        search = wx.SearchCtrl(mainPanel)
        searchSizer.Add(search, 1, wx.ALIGN_CENTER_VERTICAL)
        mainSizer.Add(searchSizer, 0, wx.EXPAND)

        # status panel
        self.statusPanel = status_panel.StatusPanel(mainPanel, mainSizer, presenter_)

        # packages tree
        self.packagesTree = filtered_tree.PackagesTree(mainPanel, mainSizer,
                (presenter.FilterIds.PACKAGES_HIDDEN,
                 presenter.FilterIds.PACKAGES_INSTALLED,
                 presenter.FilterIds.PACKAGES_NOT_INSTALLED),
                ("Hidden", "Installed", "Not Installed"),
                presenter_, filterRegistry)

        # details section
        commentsSplitter = wx.gizmos.ThinSplitterWindow(topSplitter, style=splitterStyle)
        detailsSplitter = wx.gizmos.ThinSplitterWindow(
            commentsSplitter, style=splitterStyle)
        fileTreeSplitter = wx.gizmos.ThinSplitterWindow(
            detailsSplitter, style=splitterStyle)
        self._splitters = {"fileTree":fileTreeSplitter,
                           "details":detailsSplitter,
                           "comments":commentsSplitter,
                           "top":topSplitter}

        self.packageContentsPanel = package_contents_panel.PackageContentsPanel(
            self._splitters, search.GetSize()[1], presenter_, filterRegistry)

        # customize search controls
        # see http://groups.google.com/group/wxpython-users/browse_thread/thread/6e999b3013e383f6
        # for how to fix text color bug
        search.SetDescriptiveText("Search...")
        search.ShowCancelButton(True)

        # configure splitter
        topSplitter.SetMinimumPaneSize(200)
        topSplitter.SplitVertically(mainPanel, commentsSplitter)
        topSplitter.SetSashGravity(1.0) # only resize mainPanel

        # configure layout
        mainPanel.SetMinSize(mainSizer.GetMinSize())
        mainPanel.SetSizer(mainSizer)
        topPanel.SetMinSize(topSizer.GetMinSize())
        topPanel.SetSizer(topSizer)

        # add page to parent notebook
        wxParentNotebook.AddPage(topPanel, "Installers")

        # set up state
        self._presenter = presenter_
        self._filterRegistry = filterRegistry
        self._viewIoGateway = viewIoGateway

        # event bindings
        search.Bind(wx.EVT_TEXT, self._on_search_text)


    def load(self, filterStateMap):
        self._filterRegistry.init_filter_states(filterStateMap)
        # TODO: load and apply saved gui state
        # if no saved state, use defaults
        self._splitters["comments"].SetSashPosition(-1) # one line
        size = self._topPanel.GetSize()
        self._splitters["top"].SetSashPosition(size[0]*0.42)
        self._splitters["details"].SetSashPosition(size[1]*0.22)
        self._splitters["fileTree"].SetSashPosition(size[0]*0.32)

    def display_error(self, *args): pass
    def ask_confirmation(self, *args): pass

    def save_state(self):
        if self._viewIoGateway is None:
            return
        # TODO: save gui state
        for splitterName, splitterCtrl in self._splitters.iteritems():
            sashPos = splitterCtrl.GetSashPosition()
            if splitterName is "comments":
                # save distance from the bottom so it will still be meaningful if the pane
                # gets resized
                sashPos -= splitterCtrl.GetSize()[1]
            _logger.debug("saving splitter %s sash position: %d", splitterName, sashPos)

    def _on_search_text(self, event):
        text = event.GetEventObject().GetValue()
        _logger.debug("search string changing to: '%s'", text)
        self._presenter.set_search_string(text)
