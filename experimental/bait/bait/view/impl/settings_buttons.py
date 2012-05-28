# -*- coding: utf-8 -*-
#
# bait/view/impl/settings_buttons.py
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


_logger = logging.getLogger(__name__)


class GlobalSettingsButton:
    def __init__(self, wxParent, sizer):
        settingsIcon = wx.ArtProvider.GetBitmap(wx.ART_REMOVABLE, client=wx.ART_BUTTON)
        button = self._button = wx.BitmapButton(wxParent, bitmap=settingsIcon,
                                                style=wx.NO_BORDER)
        button.SetToolTipString("Global Settings")
        sizer.Add(button, 0, wx.ALIGN_CENTER_VERTICAL|wx.LEFT|wx.RIGHT, 3)
        button.Bind(wx.EVT_BUTTON, self._on_global_settings_menu)

    def set_enabled(self, enabled):
        self._button.Enable(enabled)

    def set_settings(self, rememberTreeExpansionState, skipDistantLod, skipLodMeshes,
                     skipLodNormals, skipLodTextures, skipVoices): pass

    def _on_global_settings_menu(self, event):
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
        self._button.PopupMenu(menu)
        menu.Destroy()

class PackageSettingsButton:
    def __init__(self, wxParent, sizer):
        settingsIcon = wx.ArtProvider.GetBitmap(wx.ART_REMOVABLE, client=wx.ART_BUTTON)
        button = self._button = wx.BitmapButton(wxParent, bitmap=settingsIcon,
                                                style=wx.NO_BORDER)
        button.SetToolTipString("Package Settings")
        sizer.Add(button, 0, wx.ALIGN_CENTER_VERTICAL|wx.LEFT|wx.RIGHT, 3)
        button.Bind(wx.EVT_BUTTON, self._on_package_settings_menu)

    def set_enabled(self, enabled):
        self._button.Enable(enabled)

    def set_settings(self, skipDistantLod, skipLodMeshes, skipLodNormals,
                     skipLodTextures, skipVoices): pass

    def _on_package_settings_menu(self, event):
        _logger.debug("showing package settings menu")
        # TODO: use a PopupWindow with a listbox instead of PopupMenu() to avoid stalling
        # the GUI event loop thread
        menu = wx.Menu()
        menu.Append(-1, "Skip DistantLOD", kind=wx.ITEM_CHECK)
        menu.Append(-1, "Skip LOD meshes", kind=wx.ITEM_CHECK)
        menu.Append(-1, "Skip LOD textures", kind=wx.ITEM_CHECK)
        menu.Append(-1, "Skip LOD normals", kind=wx.ITEM_CHECK)
        menu.Append(-1, "Skip all voices", kind=wx.ITEM_CHECK)
        self._button.PopupMenu(menu)
        menu.Destroy()
