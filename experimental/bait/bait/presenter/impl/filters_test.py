# -*- coding: utf-8 -*-
#
# bait/presenter/impl/filters_test.py
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

import Queue
import logging

from . import filters
from ... import model
from ... import presenter
from ...model import node_attributes


_logger = logging.getLogger(__name__)


def _drain_queue(viewCommandQueue):
    while viewCommandQueue.qsize() > 0:
        viewCommand = viewCommandQueue.get()
        _logger.debug("received viewCommand: %s", str(viewCommand))


def package_tree_filter_test():
    viewCommandQueue = Queue.Queue()
    ptf = filters.PackageTreeFilter(viewCommandQueue)

    _logger.debug("ensuring valid initial state")
    assert(len(ptf.get_matched_node_ids()) is 0)
    assert(ptf.id == presenter.FILTER_ID_PACKAGES_HIDDEN|\
           presenter.FILTER_ID_PACKAGES_INSTALLED|\
           presenter.FILTER_ID_PACKAGES_NOT_INSTALLED)

    data = {}
    package1 = node_attributes.PackageNodeAttributes()
    package1.installed = True
    data[0] = package1
    group1 = node_attributes.GroupNodeAttributes()
    group1.hasNotInstalled = True
    group1.hasHidden = True
    data[1] = group1
    package2 = node_attributes.PackageNodeAttributes()
    data[2] = package2
    group2 = node_attributes.GroupNodeAttributes()
    group2.hasHidden = True
    data[3] = group2
    package3 = node_attributes.PackageNodeAttributes()
    package3.hidden = True
    data[4] = package3

    _logger.debug("adding nodes")
    for idx in xrange(5):
        ptf.passes(idx, data[idx])
