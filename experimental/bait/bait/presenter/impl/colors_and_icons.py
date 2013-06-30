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


_logger = logging.getLogger(__name__)
_foregroundColorMap = {
        presenter.ForegroundColorIds.DISABLED:(142,139,138),
        presenter.ForegroundColorIds.HAS_INACTIVE_OVERRIDDE:(255,165,0),
        presenter.ForegroundColorIds.HAS_SUBPACKAGES:(0,0,255)
    }
_highlightColorMap = {
        presenter.HighlightColorIds.ERROR:(193,205,205),
        presenter.HighlightColorIds.MISSING_DEPENDENCY:(255,0,0),
        presenter.HighlightColorIds.DIRTY:(255,215,0),
        presenter.HighlightColorIds.LOADING:(255,255,0),
        presenter.HighlightColorIds.OK:(0,255,0)
    }
_checkedIconMap = {
        presenter.IconIds.PROJECT_MATCHES:"images/diamond_green_inc.png",
        presenter.IconIds.PROJECT_MATCHES_WIZ:"images/diamond_green_inc_wiz.png",
        presenter.IconIds.PROJECT_MISMATCHED:"images/diamond_orange_inc.png",
        presenter.IconIds.PROJECT_MISMATCHED_WIZ:"images/diamond_orange_inc_wiz.png",
        presenter.IconIds.PROJECT_MISSING:"images/diamond_red_inc.png",
        presenter.IconIds.PROJECT_MISSING_WIZ:"images/diamond_red_inc_wiz.png",
        presenter.IconIds.PROJECT_EMPTY:"images/diamond_white_off.png",
        presenter.IconIds.PROJECT_EMPTY_WIZ:"images/diamond_white_off_wiz.png",
        presenter.IconIds.PROJECT_UNINSTALLABLE:"images/diamond_grey_off.png",
        presenter.IconIds.INSTALLER_MATCHES:"images/checkbox_green_inc.png",
        presenter.IconIds.INSTALLER_MATCHES_WIZ:"images/checkbox_green_inc_wiz.png",
        presenter.IconIds.INSTALLER_MISMATCHED:"images/checkbox_orange_inc.png",
        presenter.IconIds.INSTALLER_MISMATCHED_WIZ:"images/checkbox_orange_inc_wiz.png",
        presenter.IconIds.INSTALLER_MISSING:"images/checkbox_red_inc.png",
        presenter.IconIds.INSTALLER_MISSING_WIZ:"images/checkbox_red_inc_wiz.png",
        presenter.IconIds.INSTALLER_EMPTY:"images/checkbox_white_off.png",
        presenter.IconIds.INSTALLER_EMPTY_WIZ:"images/checkbox_white_off_wiz.png",
        presenter.IconIds.INSTALLER_UNINSTALLABLE:"images/checkbox_grey_off.png"
    }
_uncheckedIconMap = {
        presenter.IconIds.PROJECT_MATCHES:"images/diamond_green_off.png",
        presenter.IconIds.PROJECT_MATCHES_WIZ:"images/diamond_green_off_wiz.png",
        presenter.IconIds.PROJECT_MISMATCHED:"images/diamond_orange_off.png",
        presenter.IconIds.PROJECT_MISMATCHED_WIZ:"images/diamond_orange_off_wiz.png",
        presenter.IconIds.PROJECT_MISSING:"images/diamond_red_off.png",
        presenter.IconIds.PROJECT_MISSING_WIZ:"images/diamond_red_off_wiz.png",
        presenter.IconIds.PROJECT_EMPTY:"images/diamond_white_off.png",
        presenter.IconIds.PROJECT_EMPTY_WIZ:"images/diamond_white_off_wiz.png",
        presenter.IconIds.PROJECT_UNINSTALLABLE:"images/diamond_grey_off.png",
        presenter.IconIds.INSTALLER_MATCHES:"images/checkbox_green_off.png",
        presenter.IconIds.INSTALLER_MATCHES_WIZ:"images/checkbox_green_off_wiz.png",
        presenter.IconIds.INSTALLER_MISMATCHED:"images/checkbox_orange_off.png",
        presenter.IconIds.INSTALLER_MISMATCHED_WIZ:"images/checkbox_orange_off_wiz.png",
        presenter.IconIds.INSTALLER_MISSING:"images/checkbox_red_off.png",
        presenter.IconIds.INSTALLER_MISSING_WIZ:"images/checkbox_red_off_wiz.png",
        presenter.IconIds.INSTALLER_EMPTY:"images/checkbox_white_off.png",
        presenter.IconIds.INSTALLER_EMPTY_WIZ:"images/checkbox_white_off_wiz.png",
        presenter.IconIds.INSTALLER_UNINSTALLABLE:"images/checkbox_grey_off.png"
    }


class ColorsAndIcons:
    def __init__(self, presenterIoGateway):
        self._presenterIoGateway = presenterIoGateway
        # TODO: restore any custom colors

    def get_set_style_maps_command(self):
        return presenter.SetStyleMapsCommand(_foregroundColorMap, _highlightColorMap,
                                             _checkedIconMap, _uncheckedIconMap)
