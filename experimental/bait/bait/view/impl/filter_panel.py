# -*- coding: utf-8 -*-
#
# bait/view/impl/filter_panel.py
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


class FilterPanel:
    '''Provides a panel of toggle filter buttons'''
    def __init__(self, wxParent, sizer, filterIds, filterLabels, presenter_,
                 filterRegistry):
        self._wxIdToFilterId = {}
        self._presenter = presenter_
        panel = wx.Panel(wxParent)
        panel.SetBackgroundColour(wxParent.GetBackgroundColour())
        # TODO: can we reduce the font size without making the labels look horrible?
        label = wx.StaticText(panel, label=" Show:")
        panelSizer = wx.BoxSizer(wx.HORIZONTAL)
        panelSizer.Add(label, 0, wx.ALIGN_CENTER_VERTICAL)
        for filterId, filterLabel in zip(filterIds, filterLabels):
            # calculate smallest button size dimensions and create buttons
            filterButton = wx.ToggleButton(panel)
            filterRegistry.add_filter(filterId, filterLabel, filterButton)
            filterRegistry.set_filter_stats(filterId, 0, 0, False)
            # reduce height
            curWidth, curHeight = filterButton.GetBestSize()
            filterButton.SetMinSize((curWidth, curHeight-6))
            panelSizer.Add(filterButton, 0, wx.ALIGN_CENTER_VERTICAL)
            self._wxIdToFilterId[filterButton.GetId()] = filterId
        # no need to set size hints -- this panel doesn't determine any sizer limits
        panel.SetSizer(panelSizer)
        panel.Fit()
        sizer.Add(panel, 0, wx.EXPAND)
        panel.Bind(wx.EVT_TOGGLEBUTTON, self._on_toggle_filter)

    def _on_toggle_filter(self, event):
        _logger.debug("handling toggle filter event")
        filterId = self._wxIdToFilterId[event.GetId()]
        self._presenter.set_filter_state(filterId, event.IsChecked())
        event.Skip()
