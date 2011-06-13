# -*- coding: utf-8 -*-
#
# bait/presenter/impl/colors_and_icons.py
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

from ... import presenter
from .. import view_commands


_logger = logging.getLogger(__name__)
_foregroundColorMap = {
        view_commands.ForegroundColorIds.DISABLED:(142,139,138),
        view_commands.ForegroundColorIds.HAS_INACTIVE_OVERRIDDE:(255,165,0)
    }
_highlightColorMap = {
        view_commands.HighlightColorIds.ERROR:(193,205,205),
        view_commands.HighlightColorIds.MISSING_DEPENDENCY:(255,0,0),
        view_commands.HighlightColorIds.DIRTY:(255,215,0),
        view_commands.HighlightColorIds.LOADING:(255,255,0),
        view_commands.HighlightColorIds.OK:(0,255,0)
    }
_checkedIconMap = {
        view_commands.IconIds.PROJECT_MATCHES:"images/diamond_green_inc.png",
        view_commands.IconIds.PROJECT_MATCHES_WIZ:"images/diamond_green_inc_wiz.png",
        view_commands.IconIds.PROJECT_MISMATCHED:"images/diamond_orange_inc.png",
        view_commands.IconIds.PROJECT_MISMATCHED_WIZ:"images/diamond_orange_inc_wiz.png",
        view_commands.IconIds.PROJECT_MISSING:"images/diamond_red_inc.png",
        view_commands.IconIds.PROJECT_MISSING_WIZ:"images/diamond_red_inc_wiz.png",
        view_commands.IconIds.PROJECT_EMPTY:"images/diamond_white_off.png",
        view_commands.IconIds.PROJECT_EMPTY_WIZ:"images/diamond_white_off_wiz.png",
        view_commands.IconIds.PROJECT_UNINSTALLABLE:"images/diamond_grey_off.png",
        view_commands.IconIds.INSTALLER_MATCHES:"images/checkbox_green_inc.png",
        view_commands.IconIds.INSTALLER_MATCHES_WIZ:"images/checkbox_green_inc_wiz.png",
        view_commands.IconIds.INSTALLER_MISMATCHED:"images/checkbox_orange_inc.png",
        view_commands.IconIds.INSTALLER_MISMATCHED_WIZ:"images/checkbox_orange_inc_wiz.png",
        view_commands.IconIds.INSTALLER_MISSING:"images/checkbox_red_inc.png",
        view_commands.IconIds.INSTALLER_MISSING_WIZ:"images/checkbox_red_inc_wiz.png",
        view_commands.IconIds.INSTALLER_EMPTY:"images/checkbox_white_off.png",
        view_commands.IconIds.INSTALLER_EMPTY_WIZ:"images/checkbox_white_off_wiz.png",
        view_commands.IconIds.INSTALLER_UNINSTALLABLE:"images/checkbox_grey_off.png"
    }
_uncheckedIconMap = {
        view_commands.IconIds.PROJECT_MATCHES:"images/diamond_green_off.png",
        view_commands.IconIds.PROJECT_MATCHES_WIZ:"images/diamond_green_off_wiz.png",
        view_commands.IconIds.PROJECT_MISMATCHED:"images/diamond_orange_off.png",
        view_commands.IconIds.PROJECT_MISMATCHED_WIZ:"images/diamond_orange_off_wiz.png",
        view_commands.IconIds.PROJECT_MISSING:"images/diamond_red_off.png",
        view_commands.IconIds.PROJECT_MISSING_WIZ:"images/diamond_red_off_wiz.png",
        view_commands.IconIds.PROJECT_EMPTY:"images/diamond_white_off.png",
        view_commands.IconIds.PROJECT_EMPTY_WIZ:"images/diamond_white_off_wiz.png",
        view_commands.IconIds.PROJECT_UNINSTALLABLE:"images/diamond_grey_off.png",
        view_commands.IconIds.INSTALLER_MATCHES:"images/checkbox_green_off.png",
        view_commands.IconIds.INSTALLER_MATCHES_WIZ:"images/checkbox_green_off_wiz.png",
        view_commands.IconIds.INSTALLER_MISMATCHED:"images/checkbox_orange_off.png",
        view_commands.IconIds.INSTALLER_MISMATCHED_WIZ:"images/checkbox_orange_off_wiz.png",
        view_commands.IconIds.INSTALLER_MISSING:"images/checkbox_red_off.png",
        view_commands.IconIds.INSTALLER_MISSING_WIZ:"images/checkbox_red_off_wiz.png",
        view_commands.IconIds.INSTALLER_EMPTY:"images/checkbox_white_off.png",
        view_commands.IconIds.INSTALLER_EMPTY_WIZ:"images/checkbox_white_off_wiz.png",
        view_commands.IconIds.INSTALLER_UNINSTALLABLE:"images/checkbox_grey_off.png"
    }


class ColorsAndIcons:
    def __init__(self, stateManager=None):
        self._stateManager = stateManager
        # TODO: restore any custom colors

    def get_set_style_maps_command(self):
        return view_commands.SetStyleMaps(_foregroundColorMap, _highlightColorMap,
                                          _checkedIconMap, _uncheckedIconMap)
