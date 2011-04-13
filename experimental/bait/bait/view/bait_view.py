# -*- coding: utf-8 -*-
#
# bait/view/bait_view.py
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

from .. import presenter
from .impl import command_thread, filtered_tree, package_info, status_panel


_logger = logging.getLogger(__name__)


class BaitView(wx.Panel):
    def __init__(self, parent, presenter_, stateManager=None):
        '''Creates and configures bait widget hierarchies'''
        _logger.debug("initializing bait view")
        wx.Panel.__init__(self, parent)

        # assemble widget hierarchy
        # top-level splitter between left and right panels
        splitterStyle = wx.NO_BORDER|wx.SP_LIVE_UPDATE|wx.FULL_REPAINT_ON_RESIZE
        topSplitter = wx.gizmos.ThinSplitterWindow(self, style=splitterStyle)

        # main section
        mainPanel = wx.Panel(topSplitter)
        settingsIcon = wx.ArtProvider.GetBitmap(wx.ART_REMOVABLE, client=wx.ART_BUTTON)
        globalSettingsButton = wx.BitmapButton(mainPanel, bitmap=settingsIcon, style=wx.NO_BORDER)
        search = wx.SearchCtrl(mainPanel)
        statusPanel = status_panel.StatusPanel(mainPanel, presenter_)
        packageTree = self._packageTree = filtered_tree.PackagesTree(mainPanel,
                (presenter.FILTER_ID_PACKAGES_HIDDEN, presenter.FILTER_ID_PACKAGES_INSTALLED, presenter.FILTER_ID_PACKAGES_NOT_INSTALLED),
                ("Hidden (%d/%d)", "Installed (%d/%d)", "Not Installed (%d/%d)"), presenter_)

        # details section
        infoStyle = wx.TE_READONLY|wx.TE_MULTILINE
        commentsSplitter = wx.gizmos.ThinSplitterWindow(topSplitter, style=splitterStyle)
        detailsSplitter = wx.gizmos.ThinSplitterWindow(commentsSplitter, style=splitterStyle)
        packageInfoPanel = self._packageInfoPanel = package_info.PackageInfoPanel(detailsSplitter, presenter_)
        fileTreeSplitter = wx.gizmos.ThinSplitterWindow(detailsSplitter, style=splitterStyle)
        fileTreePanel = wx.Panel(fileTreeSplitter)
        projectSettingsButton = wx.BitmapButton(fileTreePanel, bitmap=settingsIcon, style=wx.NO_BORDER)
        fileTreeLabel = wx.StaticText(fileTreePanel, label="Package contents")
        self._fileTree = filtered_tree.FilesTree(fileTreePanel,
                (presenter.FILTER_ID_FILES_PLUGINS, presenter.FILTER_ID_FILES_RESOURCES, presenter.FILTER_ID_FILES_OTHER),
                ("Plugins (%d)", "Resources (%d)", "Other (%d)"), presenter_)
        fileInfoPanel = wx.Panel(fileTreeSplitter)
        fileInfoLabel = wx.StaticText(fileInfoPanel, label="File details")
        fileInfo = wx.TextCtrl(fileInfoPanel, style=infoStyle)
        commentsPanel = wx.Panel(commentsSplitter)
        commentsLabel = wx.StaticText(commentsPanel, label="Comments")
        oneLineHeight = search.GetSize()[1]
        commentsText = wx.SearchCtrl(commentsPanel, size=(-1, oneLineHeight), style=wx.TE_MULTILINE)

        # customize widgets
        globalSettingsButton.SetToolTipString("Settings")

        # read-only text controls should have same background color as parent
        bgColor = mainPanel.GetBackgroundColour()
        statusPanel.SetBackgroundColour(bgColor)
        fileInfo.SetBackgroundColour(bgColor)

        # customize search controls
        # see http://groups.google.com/group/wxpython-users/browse_thread/thread/6e999b3013e383f6
        # for how to fix text color bug
        search.SetDescriptiveText("Search...")
        search.ShowCancelButton(True)
        commentsText.SetDescriptiveText("Enter comments for this project here")
        commentsText.ShowSearchButton(False)

        # set up splitters
        fileTreeSplitter.SetMinimumPaneSize(50)
        fileTreeSplitter.SplitVertically(fileTreePanel, fileInfoPanel)
        fileTreeSplitter.SetSashGravity(0.5) # resize both panels equally
        detailsSplitter.SetMinimumPaneSize(100)
        detailsSplitter.SplitHorizontally(packageInfoPanel, fileTreeSplitter)
        detailsSplitter.SetSashGravity(0.5) # resize both panels equally
        commentsSplitter.SetMinimumPaneSize(oneLineHeight)
        commentsSplitter.SplitHorizontally(detailsSplitter, commentsPanel)
        commentsSplitter.SetSashGravity(1.0) # only resize details
        topSplitter.SetMinimumPaneSize(200)
        topSplitter.SplitVertically(mainPanel, commentsSplitter)
        topSplitter.SetSashGravity(1.0) # only resize mainPanel

        # configure layout
        searchSizer = wx.BoxSizer(wx.HORIZONTAL)
        searchSizer.Add(globalSettingsButton, 0, wx.ALIGN_CENTER_VERTICAL|wx.LEFT|wx.RIGHT, 3)
        searchSizer.Add(search, 1, wx.ALIGN_CENTER_VERTICAL)

        mainSizer = wx.BoxSizer(wx.VERTICAL)
        mainSizer.Add(searchSizer, 0, wx.EXPAND)
        mainSizer.Add(statusPanel, 0, wx.EXPAND|wx.TOP|wx.BOTTOM, 3)
        mainSizer.Add(packageTree, 1, wx.EXPAND)
        mainPanel.SetMinSize(mainSizer.GetMinSize())
        mainPanel.SetSizer(mainSizer)

        fileTreeHeaderSizer = wx.BoxSizer(wx.HORIZONTAL)
        fileTreeHeaderSizer.Add(projectSettingsButton, 0, wx.ALIGN_CENTER_VERTICAL|wx.LEFT|wx.RIGHT, 3)
        fileTreeHeaderSizer.Add(fileTreeLabel, 1, wx.ALIGN_CENTER_VERTICAL|wx.TOP|wx.BOTTOM, 3)
        fileTreeSizer = wx.BoxSizer(wx.VERTICAL)
        fileTreeSizer.Add(fileTreeHeaderSizer, 0, wx.EXPAND)
        fileTreeSizer.Add(self._fileTree, 1, wx.EXPAND)
        fileTreePanel.SetMinSize(fileTreeSizer.GetMinSize())
        fileTreePanel.SetSizer(fileTreeSizer)

        fileInfoSizer = wx.BoxSizer(wx.VERTICAL)
        fileInfoSizer.Add(fileInfoLabel, 0, wx.EXPAND|wx.TOP|wx.BOTTOM, 3)
        fileInfoSizer.Add(fileInfo, 1, wx.EXPAND)
        fileInfoPanel.SetMinSize(fileInfoSizer.GetMinSize())
        fileInfoPanel.SetSizer(fileInfoSizer)

        commentsSizer = wx.BoxSizer(wx.VERTICAL)
        commentsSizer.Add(commentsLabel, 0, wx.EXPAND|wx.TOP|wx.BOTTOM, 3)
        commentsSizer.Add(commentsText, 1, wx.EXPAND)
        commentsPanel.SetMinSize(commentsSizer.GetMinSize())
        commentsPanel.SetSizer(commentsSizer)

        topSizer = wx.BoxSizer(wx.VERTICAL)
        topSizer.Add(topSplitter, 1, wx.EXPAND)
        self.SetMinSize(topSizer.GetMinSize())
        self.SetSizer(topSizer)
        
        # set up state
        self._splitters = {"fileTree":fileTreeSplitter, "details":detailsSplitter, "comments":commentsSplitter, "top":topSplitter}
        self._presenter = presenter_
        self._stateManager = stateManager
        self._commandThread = command_thread.CommandThread(presenter_.viewCommandQueue, statusPanel=statusPanel, packageTree=packageTree, fileTree=self._fileTree, packageInfoPanel=packageInfoPanel, fileInfo=fileInfo)
        self._shuttingDown = False

        # event bindings
        globalSettingsButton.Bind(wx.EVT_BUTTON, self._on_global_settings_menu)
        projectSettingsButton.Bind(wx.EVT_BUTTON, self._on_project_settings_menu)
        search.Bind(wx.EVT_TEXT, self._on_search_text)


    def start(self):
        '''Loads saved state, starts threads and subcomponents (including presenter)'''
        # TODO: load and apply saved gui state
        # if no saved state, use defaults
        self._splitters["comments"].SetSashPosition(-1) # one line
        paneWidth = self.GetSize()[0]
        self._splitters["top"].SetSashPosition(paneWidth*0.38)
        self._splitters["details"].SetSashPosition(paneWidth*0.22)
        self._splitters["fileTree"].SetSashPosition(paneWidth*0.32)
        filterStateMap = {
            presenter.FILTER_ID_PACKAGES_HIDDEN:False,
            presenter.FILTER_ID_PACKAGES_INSTALLED:True,
            presenter.FILTER_ID_PACKAGES_NOT_INSTALLED:True,
            presenter.FILTER_ID_FILES_PLUGINS:True,
            presenter.FILTER_ID_FILES_RESOURCES:False,
            presenter.FILTER_ID_FILES_OTHER:False,
            presenter.FILTER_ID_DIRTY_ADD:True,
            presenter.FILTER_ID_DIRTY_UPDATE:True,
            presenter.FILTER_ID_DIRTY_DELETE:True,
            presenter.FILTER_ID_CONFLICTS_SELECTED:True,
            presenter.FILTER_ID_CONFLICTS_UNSELECTED:False,
            presenter.FILTER_ID_CONFLICTS_ACTIVE:True,
            presenter.FILTER_ID_CONFLICTS_INACTIVE:False,
            presenter.FILTER_ID_CONFLICTS_HIGHER:True,
            presenter.FILTER_ID_CONFLICTS_LOWER:False,
            presenter.FILTER_ID_SELECTED_MATCHED:True,
            presenter.FILTER_ID_SELECTED_MISMATCHED:True,
            presenter.FILTER_ID_SELECTED_OVERRIDDEN:True,
            presenter.FILTER_ID_SELECTED_MISSING:True,
            presenter.FILTER_ID_UNSELECTED_MATCHED:True,
            presenter.FILTER_ID_UNSELECTED_MISMATCHED:True,
            presenter.FILTER_ID_UNSELECTED_OVERRIDDEN:True,
            presenter.FILTER_ID_UNSELECTED_MISSING:False,
            presenter.FILTER_ID_SKIPPED_NONGAME:True,
            presenter.FILTER_ID_SKIPPED_MASKED:False}
        self._packageTree.start(filterStateMap)
        self._fileTree.start(filterStateMap)
        self._packageInfoPanel.start(filterStateMap)
        _logger.debug("starting command processing thread")
        self._commandThread.start()
        _logger.debug("starting presenter")
        self._presenter.start(presenter.DETAILS_TAB_ID_GENERAL, filterStateMap)
        _logger.debug("view successfully started")

    def shutdown(self):
        '''Saves any dirty state, shuts down threads and subcomponents'''
        self._shuttingDown = True
        _logger.debug("discarding further output from presenter")
        self._commandThread.set_ignore_updates(True)
        self._save_state()
        _logger.debug("shutting down presenter")
        self._presenter.shutdown()
        _logger.debug("joining command preprocessing thread")
        self._commandThread.join()
        _logger.debug("view successfully shut down")

    def pause(self):
        '''Suggests that bait suspend operations; may not take effect immediately'''
        _logger.debug("pause requested")
        self._presenter.pause()

    def resume(self):
        '''Resumes from a pause'''
        _logger.debug("resume requested")
        self._presenter.resume()
        
    def _save_state(self):
        if self._stateManager is None:
            return
        # TODO: save gui state
        for splitterName, splitterCtrl in self._splitters.iteritems():
            sashPos = splitterCtrl.GetSashPosition()
            if splitterName is "status" or splitterName is "comments":
                # save these as distances from the bottom so they will still be meaningful if the pane gets resized
                sashPos -= splitterCtrl.GetSize()[1]
            _logger.debug("saving splitter %s sash position: %d", splitterName, sashPos)

    def _on_global_settings_menu(self, event):
        if self._shuttingDown: return
        _logger.debug("showing global settings menu")
        # TODO: use a PopupWindow with a listbox instead of PopupMenu() to avoid stalling the GUI event loop thread
        menu = wx.Menu()
        menu.Append(-1, "Anneal all")
        menu.Append(-1, "Refresh installed data")
        menu.Append(-1, "Refresh packages")
        filterMenu = wx.Menu()
        filterMenu.Append(-1, "Allow OBSE plugins", kind=wx.ITEM_CHECK)
        filterMenu.Append(-1, "Skip DistantLOD", kind=wx.ITEM_CHECK)
        filterMenu.Append(-1, "Skip LOD meshes", kind=wx.ITEM_CHECK)
        filterMenu.Append(-1, "Skip LOD textures", kind=wx.ITEM_CHECK)
        filterMenu.Append(-1, "Skip LOD normals", kind=wx.ITEM_CHECK)
        filterMenu.Append(-1, "Skip all voices", kind=wx.ITEM_CHECK)
        filterMenu.Append(-1, "Skip silent voices", kind=wx.ITEM_CHECK)
        menu.AppendMenu(-1, "Install filters", filterMenu)
        stateMenu = wx.Menu()
        stateMenu.Append(-1, "Force state save")
        stateMenu.Append(-1, "Reset state...")
        stateMenu.Append(-1, "Export state...")
        stateMenu.Append(-1, "Import state...")
        stateMenu.Append(-1, "Derive state from contents of Data directory")
        menu.AppendMenu(-1, "Manage state", stateMenu)
        self.PopupMenu(menu)
        menu.Destroy()

    def _on_project_settings_menu(self, event):
        if self._shuttingDown: return
        _logger.debug("showing project settings menu")
        # TODO: use a PopupWindow with a listbox instead of PopupMenu() to avoid stalling the GUI event loop thread
        # TODO: make these tristates, falls through to global settings
        menu = wx.Menu()
        menu.Append(-1, "Has non-standard directories", kind=wx.ITEM_CHECK)
        menu.Append(-1, "Allow OBSE plugins", kind=wx.ITEM_CHECK)
        menu.Append(-1, "Skip DistantLOD", kind=wx.ITEM_CHECK)
        menu.Append(-1, "Skip LOD meshes", kind=wx.ITEM_CHECK)
        menu.Append(-1, "Skip LOD textures", kind=wx.ITEM_CHECK)
        menu.Append(-1, "Skip LOD normals", kind=wx.ITEM_CHECK)
        menu.Append(-1, "Skip all voices", kind=wx.ITEM_CHECK)
        menu.Append(-1, "Skip silent voices", kind=wx.ITEM_CHECK)
        self.PopupMenu(menu)
        menu.Destroy()
        
    def _on_search_text(self, event):
        text = event.GetEventObject().GetValue()
        _logger.debug("search string changing to: '%s'", text)
        self._presenter.set_search_string(text)
