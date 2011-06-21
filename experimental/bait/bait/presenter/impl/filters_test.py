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


def assert_stats_update(viewUpdateQueue, filterId, current, total):
    assert(not viewUpdateQueue.empty())
    setFilterStatsUpdate = viewUpdateQueue.get()
    assert(filterId == setFilterStatsUpdate.filterId)
    assert(current == setFilterStatsUpdate.current)
    assert(total == setFilterStatsUpdate.total)


def package_contents_tree_filter_test():
    viewUpdateQueue = Queue.Queue()
    pctf = filters.PackageContentsTreeFilter(viewUpdateQueue)

    # define initial data structure
    data = {}
    fileAttributes1 = node_attributes.FileNodeAttributes()
    fileAttributes1.label = "plugin1.esp"
    fileAttributes1.isPlugin = True
    data[0] = fileAttributes1
    fileAttributes2 = node_attributes.FileNodeAttributes()
    fileAttributes2.label = "resource.nif"
    fileAttributes2.isResource = True
    data[1] = fileAttributes2
    fileAttributes3 = node_attributes.FileNodeAttributes()
    fileAttributes3.label = "document.txt"
    fileAttributes3.isOther = True
    data[2] = fileAttributes3
    dirAttributes1 = node_attributes.DirectoryNodeAttributes()
    dirAttributes1.label = "screenshotsDir"
    dirAttributes1.isOther = True
    data[3] = dirAttributes1
    fileAttributes4 = node_attributes.FileNodeAttributes()
    fileAttributes4.label = "screenie.jpg"
    fileAttributes4.isOther = True
    data[4] = fileAttributes4

    # test initial conditions
    assert(len(pctf.visibleNodeIds) == 0)
    assert(viewUpdateQueue.empty())

    # test setting active filter mask with no data
    assert(not pctf.set_active_mask(presenter.FilterIds.NONE))
    assert(not pctf.set_active_mask(presenter.FilterIds.PACKAGES_HIDDEN))
    assert(pctf.set_active_mask(presenter.FilterIds.FILES_RESOURCES))
    assert(len(pctf.visibleNodeIds) == 0)
    assert(viewUpdateQueue.empty())

    # test adding data
    assert(not pctf.process_and_get_visibility(0, data[0]))
    assert(len(pctf.visibleNodeIds) == 0)
    assert_stats_update(viewUpdateQueue, presenter.FilterIds.FILES_PLUGINS, 1, 1)
    assert(viewUpdateQueue.empty())

    assert(pctf.process_and_get_visibility(1, data[1]))
    assert(len(pctf.visibleNodeIds) == 1)
    assert(1 in pctf.visibleNodeIds)
    assert_stats_update(viewUpdateQueue, presenter.FilterIds.FILES_RESOURCES, 1, 1)
    assert(viewUpdateQueue.empty())

    assert(not pctf.process_and_get_visibility(2, data[2]))
    assert_stats_update(viewUpdateQueue, presenter.FilterIds.FILES_OTHER, 1, 1)
    assert(viewUpdateQueue.empty())

    assert(not pctf.process_and_get_visibility(3, data[3]))
    assert(viewUpdateQueue.empty())

    assert(not pctf.process_and_get_visibility(4, data[4]))
    assert(len(pctf.visibleNodeIds) == 1)
    assert(1 in pctf.visibleNodeIds)
    assert_stats_update(viewUpdateQueue, presenter.FilterIds.FILES_OTHER, 2, 2)
    assert(viewUpdateQueue.empty())

    # test adjusting active filters while we have data
    assert(pctf.set_active_mask(
        presenter.FilterIds.FILES_OTHER|presenter.FilterIds.PACKAGES_HIDDEN))
    assert(viewUpdateQueue.empty())
    assert(len(pctf.visibleNodeIds) == 3)
    assert(2 in pctf.visibleNodeIds)
    assert(3 in pctf.visibleNodeIds)
    assert(4 in pctf.visibleNodeIds)

    # test removals
    pctf.remove([2])
    assert_stats_update(viewUpdateQueue, presenter.FilterIds.FILES_OTHER, 1, 1)
    assert(viewUpdateQueue.empty())
    assert(len(pctf.visibleNodeIds) == 2)
    assert(3 in pctf.visibleNodeIds)
    assert(4 in pctf.visibleNodeIds)
    pctf.remove([3, 4])
    assert_stats_update(viewUpdateQueue, presenter.FilterIds.FILES_OTHER, 0, 0)
    assert(viewUpdateQueue.empty())
    assert(len(pctf.visibleNodeIds) == 0)
    assert(pctf.set_active_mask(presenter.FilterIds.FILES_PLUGINS))
    assert(viewUpdateQueue.empty())
    assert(len(pctf.visibleNodeIds) == 1)
    assert(0 in pctf.visibleNodeIds)
    pctf.remove([0, 1])
    # order of following two lines is not set in stone
    assert_stats_update(viewUpdateQueue, presenter.FilterIds.FILES_RESOURCES, 0, 0)
    assert_stats_update(viewUpdateQueue, presenter.FilterIds.FILES_PLUGINS, 0, 0)
    assert(viewUpdateQueue.empty())
    assert(len(pctf.visibleNodeIds) == 0)


def packages_tree_filter_test():
    viewUpdateQueue = Queue.Queue()
    ptf = filters.PackagesTreeFilter(viewUpdateQueue)

    # define initial data structure
    data = {}
    groupAttributes1 = node_attributes.GroupNodeAttributes()
    groupAttributes1.label = "groupAll"
    groupAttributes1.isHidden = True
    groupAttributes1.isInstalled = True
    groupAttributes1.isNotInstalled = True
    data[0] = groupAttributes1
    groupAttributes2 = node_attributes.GroupNodeAttributes()
    groupAttributes2.label = "groupHidden"
    groupAttributes2.isHidden = True
    data[1] = groupAttributes2
    packageAttributes1 = node_attributes.PackageNodeAttributes()
    packageAttributes1.label = "hiddenPackage"
    packageAttributes1.isHidden = True
    data[2] = packageAttributes1
    packageAttributes2 = node_attributes.PackageNodeAttributes()
    packageAttributes2.label = "installedPackage"
    packageAttributes2.isInstalled = True
    data[3] = packageAttributes2
    packageAttributes3 = node_attributes.PackageNodeAttributes()
    packageAttributes3.label = "notInstalledPackage"
    packageAttributes3.isNotInstalled = True
    data[4] = packageAttributes3

    # test initial conditions
    assert(len(ptf.visibleNodeIds) == 0)
    assert(viewUpdateQueue.empty())

    # set active filters and add some data without an active search
    ptf.set_active_mask(
        presenter.FilterIds.PACKAGES_INSTALLED|presenter.FilterIds.PACKAGES_NOT_INSTALLED)
    assert(ptf.process_and_get_visibility(0, data[0], True))
    assert(len(ptf.visibleNodeIds) == 1)
    assert(0 in ptf.visibleNodeIds)
    assert(viewUpdateQueue.empty())

    assert(not ptf.process_and_get_visibility(1, data[1], True))
    assert(len(ptf.visibleNodeIds) == 1)
    assert(0 in ptf.visibleNodeIds)
    assert(viewUpdateQueue.empty())

    assert(not ptf.process_and_get_visibility(2, data[2], True))
    assert_stats_update(viewUpdateQueue, presenter.FilterIds.PACKAGES_HIDDEN, 1, 1)
    assert(viewUpdateQueue.empty())

    # apply the search "notIns"
    ptf.apply_search([])
    assert(len(ptf.visibleNodeIds) == 0)
    assert_stats_update(viewUpdateQueue, presenter.FilterIds.PACKAGES_HIDDEN, 0, 1)
    assert(viewUpdateQueue.empty())

    # add some more data, one that doesn't match the search and one that does
    # both match the active filters
    assert(not ptf.process_and_get_visibility(3, data[3], False))
    assert(len(ptf.visibleNodeIds) == 0)
    assert_stats_update(viewUpdateQueue, presenter.FilterIds.PACKAGES_INSTALLED, 0, 1)
    assert(viewUpdateQueue.empty())

    assert(ptf.process_and_get_visibility(0, data[0], True))
    assert(ptf.process_and_get_visibility(4, data[4], True))
    assert(len(ptf.visibleNodeIds) == 2)
    assert(0 in ptf.visibleNodeIds)
    assert(4 in ptf.visibleNodeIds)
    assert_stats_update(viewUpdateQueue, presenter.FilterIds.PACKAGES_NOT_INSTALLED, 1, 1)
    assert(viewUpdateQueue.empty())

    # change the active mask to hidden
    ptf.set_active_mask(presenter.FilterIds.PACKAGES_HIDDEN)
    assert(len(ptf.visibleNodeIds) == 1)
    assert(0 in ptf.visibleNodeIds)
    # reapply search
    ptf.apply_search([])
    assert(len(ptf.visibleNodeIds) == 0)
    assert_stats_update(viewUpdateQueue, presenter.FilterIds.PACKAGES_NOT_INSTALLED, 0, 1)
    assert(viewUpdateQueue.empty())

    # change the active mask to everything
    ptf.set_active_mask(presenter.FilterIds.PACKAGES_HIDDEN | \
                        presenter.FilterIds.PACKAGES_INSTALLED | \
                        presenter.FilterIds.PACKAGES_NOT_INSTALLED)
    assert(len(ptf.visibleNodeIds) == 0)
    # change the search string to "installed"
    ptf.apply_search([0, 3, 4])
    assert(len(ptf.visibleNodeIds) == 3)
    assert(0 in ptf.visibleNodeIds)
    assert(3 in ptf.visibleNodeIds)
    assert(4 in ptf.visibleNodeIds)
    assert_stats_update(viewUpdateQueue, presenter.FilterIds.PACKAGES_INSTALLED, 1, 1)
    assert_stats_update(viewUpdateQueue, presenter.FilterIds.PACKAGES_NOT_INSTALLED, 1, 1)
    assert(viewUpdateQueue.empty())

    # remove some data, including the installed package
    ptf.remove([1, 2, 3])
    assert(len(ptf.visibleNodeIds) == 2)
    assert(0 in ptf.visibleNodeIds)
    assert(4 in ptf.visibleNodeIds)
    assert_stats_update(viewUpdateQueue, presenter.FilterIds.PACKAGES_INSTALLED, 0, 0)
    assert_stats_update(viewUpdateQueue, presenter.FilterIds.PACKAGES_HIDDEN, 0, 0)
    assert(viewUpdateQueue.empty())

    # update the not installed package so that it is now installed
    assert(ptf.process_and_get_visibility(4, data[3], True))
    assert(len(ptf.visibleNodeIds) == 2)
    assert(0 in ptf.visibleNodeIds)
    assert(4 in ptf.visibleNodeIds)
    assert_stats_update(viewUpdateQueue, presenter.FilterIds.PACKAGES_INSTALLED, 1, 1)
    assert_stats_update(viewUpdateQueue, presenter.FilterIds.PACKAGES_NOT_INSTALLED, 0, 0)
    assert(viewUpdateQueue.empty())

    # remove the search restriction; check that nothing changes
    ptf.apply_search(None)
    assert(len(ptf.visibleNodeIds) == 2)
    assert(0 in ptf.visibleNodeIds)
    assert(4 in ptf.visibleNodeIds)
    assert(viewUpdateQueue.empty())
