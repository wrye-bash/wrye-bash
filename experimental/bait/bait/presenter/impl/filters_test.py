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

def _add_nodes(f, data):
    for nodeId in xrange(len(data)):
        node = data[nodeId]
        _logger.debug("filtering node %d: %s", nodeId, str(node))
        f.filter(nodeId, node, True)

def package_tree_filter_test():
    viewCommandQueue = Queue.Queue()

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

    #hpf = filters._HiddenPackagesFilter(viewCommandQueue)

    #_logger.debug("ensuring valid initial state for hidden packages filter")
    #assert(hpf._idMask == presenter.FILTER_ID_PACKAGES_HIDDEN)
    #assert(len(hpf._matchedNodeIds) is 0)
    #assert(not hpf.dirty)

    #_logger.debug("ensuring correct nodes are matched by hidden packages filter")
    #_add_nodes(hpf, data)
    #assert(hpf._matchedNodeIds == set([4]))
    #assert(hpf.dirty)
    #_logger.debug("updating view")
    #hpf.update_view()
    #_drain_queue(viewCommandQueue)


    ptf = filters.PackageTreeFilter(viewCommandQueue)

    _logger.debug("adding nodes")
    _add_nodes(ptf, data)

    #_logger.debug("checking visible nodes")
    #assert(len(ptf.visibleNodeIds) is 0)

    _logger.debug("updating view")
    ptf.update_view()
    _drain_queue(viewCommandQueue)

    _logger.debug("turning on some filters")
    ptf.set_active_mask(
        presenter.FilterIds.PACKAGES_HIDDEN|presenter.FilterIds.PACKAGES_INSTALLED)
    _logger.debug("updating view")
    ptf.update_view()
    _drain_queue(viewCommandQueue)

    _logger.debug("applying search")
    ptf.apply_search(set([0, 2]))
    _logger.debug("updating view")
    ptf.update_view()
    _drain_queue(viewCommandQueue)

    _logger.debug("removing node 0")
    ptf.remove(0)
    _logger.debug("updating view")
    ptf.update_view()
    _drain_queue(viewCommandQueue)

    _logger.debug("removing and re-adding node 4")
    ptf.remove(4)
    ptf.filter(4, data[4], False)
    _logger.debug("updating view")
    ptf.update_view()
    _drain_queue(viewCommandQueue)

    _logger.debug("cancelling search")
    ptf.apply_search(None)
    _logger.debug("updating view")
    ptf.update_view()
    _drain_queue(viewCommandQueue)

    _logger.debug("adding node 0 back in")
    ptf.filter(0, data[0], True)
    _logger.debug("updating view")
    ptf.update_view()
    _drain_queue(viewCommandQueue)

    _logger.debug("updating node 4 from hidden to installed")
    package3.hidden = False
    package3.installed = True
    ptf.filter(4, data[4], True)
    _logger.debug("updating view")
    ptf.update_view()
    _drain_queue(viewCommandQueue)

    _logger.debug("updating node 4 from installed to hidden")
    package3.hidden = True
    package3.installed = False
    ptf.filter(4, data[4], True)
    _logger.debug("updating view")
    ptf.update_view()
    _drain_queue(viewCommandQueue)
