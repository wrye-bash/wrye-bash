# -*- coding: utf-8 -*-
#
# bait/view/impl/filter_registry.py
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


class FilterRegistry:
    def __init__(self):
        self._filters = {}

    def init_filter_states(self, filterMask):
        # set initial filter states (presenter is notified in BaitView.start(), so no need
        # to do it here)
        filters = self._filters
        for filterId in filters:
            value = filterId in filterMask
            _logger.debug("initializing filter %s to %s", filterId, value)
            filters[filterId][1].SetValue(value)

    def add_filter(self, filterId, label, filterButton):
        if self._filters.has_key(filterId):
            _logger.warn("adding duplicate key to filter registry: %s", filterId)
        self._filters[filterId] = (label, filterButton)

    def set_filter_stats(self, filterId, current, total, autofit=True):
        label, filterButton = self._filters[filterId]
        _logger.debug("updating filter %s label with stats: current=%d; total=%d",
                      filterId, current, total)
        if current == total:
            filterButton.SetLabel("%s (%d)" % (label, total))
        else:
            filterButton.SetLabel("%s (%d/%d)" % (label, current, total))
        # resize button width to fit the new label
        curHeight = filterButton.GetSize()[1]
        filterButton.SetMinSize((filterButton.GetBestSize()[0], curHeight))
        if autofit:
            parent = filterButton.GetParent()
            parent.Layout()
            parent.Fit()
