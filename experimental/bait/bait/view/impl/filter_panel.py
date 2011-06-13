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


class FilterPanel(wx.Panel):
    '''Provides a panel of toggle filter buttons'''
    def __init__(self, parent, filterIds, filterLabelFormatPatterns, presenter_, backgroundColor=None, filterFont=None, setFilterButtonLabelFn=None):
        wx.Panel.__init__(self, parent)
        if not setFilterButtonLabelFn is None:
            self._set_filter_button_label = setFilterButtonLabelFn
        if backgroundColor is None:
            backgroundColor = parent.GetBackgroundColour()
        self.SetBackgroundColour(backgroundColor)
        if filterFont is None:
            # reduce size of toggle filter labels by 2, but no smaller than 6
            # TODO: is there a better way to do this?
            parentFont = parent.GetFont()
            filterFont = wx.Font(
                max((6, parentFont.GetPointSize()-2)),
                parentFont.GetFamily(), parentFont.GetStyle(),
                wx.FONTWEIGHT_NORMAL, False, parentFont.GetFaceName())
        self.SetFont(filterFont)
        dc = wx.WindowDC(self)
        dc.SetFont(filterFont)
        label = wx.StaticText(self, label=" Show:")
        sizer = wx.BoxSizer(wx.HORIZONTAL)
        sizer.Add(label, 0, wx.ALIGN_CENTER_VERTICAL)
        self._filters = {}
        self._wxIdToFilterId = {}
        for filterId, filterLabelFormatPattern in zip(filterIds, filterLabelFormatPatterns):
            # calculate reduced button size dimensions and create buttons
            filterButton = wx.ToggleButton(self)
            self._set_filter_button_label(filterButton, filterLabelFormatPattern, 0, 0)
            curWidth, curHeight = filterButton.GetBestSize()
            filterButton.SetMinSize((curWidth, curHeight-6))
            sizer.Add(filterButton, 0, wx.ALIGN_CENTER_VERTICAL)
            self._filters[filterId] = (filterButton, filterLabelFormatPattern)
            self._wxIdToFilterId[filterButton.GetId()] = filterId
        # no need to set size hints -- this panel doesn't determine any sizer limits
        self.SetSizer(sizer)
        self.Fit()
        self._presenter = presenter_
        self.Bind(wx.EVT_TOGGLEBUTTON, self._on_toggle_filter)

    def start(self, filterStateMap):
        # set initial filter states (presenter is notified in bait_view.start(), so no need to do it here)
        filters = self._filters
        for filterId in filters:
            filters[filterId][0].SetValue(filterStateMap[filterId])

    def set_filter_stats(self, filterId, current, total):
        filterButton, filterLabelFormatPattern = self._filters[filterId]
        _logger.debug("updating filter %s label with stats: current=%d; total=%d",
                      filterId, current, total)
        self._set_filter_button_label(
            filterButton, filterLabelFormatPattern, current, total)
        # resize button width to fit the new label
        curHeight = filterButton.GetSize()[1]
        filterButton.SetMinSize((filterButton.GetBestSize()[0], curHeight))
        self.Layout()
        self.Fit()

    def _set_filter_button_label(self, filterButton, filterLabelFormatPattern,
                                 current, total):
        """may be overridden in the constructor"""
        filterButton.SetLabel(filterLabelFormatPattern % total)

    def _on_toggle_filter(self, event):
        _logger.debug("handling toggle filter event")
        filterId = self._wxIdToFilterId[event.GetId()]
        self._presenter.set_filter_state(filterId, event.IsChecked())
        event.Skip()
