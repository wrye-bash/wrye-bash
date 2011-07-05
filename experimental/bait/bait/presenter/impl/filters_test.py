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

from . import filters
from ... import model
from ... import presenter
from ...model import node_attributes


def _assert_stats_update(viewUpdateQueue, filterId, current, total):
    assert not viewUpdateQueue.empty()
    setFilterStatsUpdate = viewUpdateQueue.get()
    assert filterId == setFilterStatsUpdate.filterId
    assert current == setFilterStatsUpdate.current
    assert total == setFilterStatsUpdate.total
    assert viewUpdateQueue.empty()

def _assert_stats_updates(viewUpdateQueue, updates):
    """updates is a dict of filterId -> (current, total)"""
    for updateNum in xrange(len(updates)):
        assert not viewUpdateQueue.empty()
        setFilterStatsUpdate = viewUpdateQueue.get()
        current, total = updates[setFilterStatsUpdate.filterId]
        assert current == setFilterStatsUpdate.current
        assert total == setFilterStatsUpdate.total
    assert viewUpdateQueue.empty()


def incomplete_subclasses_test():
    # this is just to get some lines out of the "Missing" list of the coverage tool
    viewUpdateQueue = Queue.Queue()
    class BadFilter(filters._Filter):
        def __init__(self):
            filters._Filter.__init__(self, None)
    f = BadFilter()
    try:
        f.process_and_get_visibility(0, None)
        assert False
    except NotImplementedError: pass
    try:
        f.get_visible_node_ids(None)
        assert False
    except NotImplementedError: pass
    try:
        f.remove(None)
        assert False
    except NotImplementedError: pass
    try:
        f.refresh_view(None)
        assert False
    except NotImplementedError: pass
    try:
        f.update_view(None, None)
        assert False
    except NotImplementedError: pass

    class BadFilterButton(filters._FilterButton):
        def __init__(self):
            filters._FilterButton.__init__(self, None, None)
    f = BadFilterButton()
    try:
        f._match(None, None)
        assert False
    except NotImplementedError: False

    try:
        f = filters._AggregateFilter([filters._DirtyAddFilter(viewUpdateQueue)])
        assert False
    except RuntimeError: pass


def package_contents_tree_filter_test():
    viewUpdateQueue = Queue.Queue()
    f = filters.PackageContentsTreeFilter(viewUpdateQueue)

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
    assert len(f.visibleNodeIds) == 0
    assert viewUpdateQueue.empty()

    # test setting active filter mask with no data
    assert not f.set_active_mask(presenter.FilterIds.NONE)
    assert not f.set_active_mask(presenter.FilterIds.PACKAGES_HIDDEN)
    assert f.set_active_mask(presenter.FilterIds.FILES_RESOURCES)
    assert len(f.visibleNodeIds) == 0
    assert viewUpdateQueue.empty()

    # test adding data
    assert not f.process_and_get_visibility(0, data[0])
    assert len(f.visibleNodeIds) == 0
    _assert_stats_update(viewUpdateQueue, presenter.FilterIds.FILES_PLUGINS, 1, 1)

    assert f.process_and_get_visibility(1, data[1])
    assert len(f.visibleNodeIds) == 1
    assert 1 in f.visibleNodeIds
    _assert_stats_update(viewUpdateQueue, presenter.FilterIds.FILES_RESOURCES, 1, 1)

    assert not f.process_and_get_visibility(2, data[2])
    _assert_stats_update(viewUpdateQueue, presenter.FilterIds.FILES_OTHER, 1, 1)

    assert not f.process_and_get_visibility(3, data[3])
    assert viewUpdateQueue.empty()

    assert not f.process_and_get_visibility(4, data[4])
    assert len(f.visibleNodeIds) == 1
    assert 1 in f.visibleNodeIds
    _assert_stats_update(viewUpdateQueue, presenter.FilterIds.FILES_OTHER, 2, 2)

    # test adjusting active filters while we have data
    assert(f.set_active_mask(
        presenter.FilterIds.FILES_OTHER|presenter.FilterIds.PACKAGES_HIDDEN))
    assert viewUpdateQueue.empty()
    assert len(f.visibleNodeIds) == 3
    assert 2 in f.visibleNodeIds
    assert 3 in f.visibleNodeIds
    assert 4 in f.visibleNodeIds

    # test removals
    f.remove([2])
    _assert_stats_update(viewUpdateQueue, presenter.FilterIds.FILES_OTHER, 1, 1)
    assert len(f.visibleNodeIds) == 2
    assert 3 in f.visibleNodeIds
    assert 4 in f.visibleNodeIds
    f.remove([3, 4])
    _assert_stats_update(viewUpdateQueue, presenter.FilterIds.FILES_OTHER, 0, 0)
    assert len(f.visibleNodeIds) == 0
    assert f.set_active_mask(presenter.FilterIds.FILES_PLUGINS)
    assert len(f.visibleNodeIds) == 1
    assert 0 in f.visibleNodeIds
    f.remove([0, 1])
    _assert_stats_updates(viewUpdateQueue, {presenter.FilterIds.FILES_RESOURCES:(0,0),
                                            presenter.FilterIds.FILES_PLUGINS:(0,0)})
    assert len(f.visibleNodeIds) == 0


def packages_tree_filter_test():
    viewUpdateQueue = Queue.Queue()
    f = filters.PackagesTreeFilter(viewUpdateQueue)

    # define data structure
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
    assert len(f.visibleNodeIds) == 0
    assert viewUpdateQueue.empty()

    # set active filters and add some data without an active search
    f.set_active_mask(
        presenter.FilterIds.PACKAGES_INSTALLED|presenter.FilterIds.PACKAGES_NOT_INSTALLED)
    assert f.process_and_get_visibility(0, data[0], True)
    assert len(f.visibleNodeIds) == 1
    assert 0 in f.visibleNodeIds
    assert viewUpdateQueue.empty()

    assert not f.process_and_get_visibility(1, data[1], True)
    assert len(f.visibleNodeIds) == 1
    assert 0 in f.visibleNodeIds
    assert viewUpdateQueue.empty()

    assert not f.process_and_get_visibility(2, data[2], True)
    _assert_stats_update(viewUpdateQueue, presenter.FilterIds.PACKAGES_HIDDEN, 1, 1)

    # apply the search "notIns"
    f.apply_search([])
    assert len(f.visibleNodeIds) == 0
    _assert_stats_update(viewUpdateQueue, presenter.FilterIds.PACKAGES_HIDDEN, 0, 1)

    # add some more data, one that doesn't match the search and one that does
    # both match the active filters
    assert not f.process_and_get_visibility(3, data[3], False)
    assert len(f.visibleNodeIds) == 0
    _assert_stats_update(viewUpdateQueue, presenter.FilterIds.PACKAGES_INSTALLED, 0, 1)

    assert f.process_and_get_visibility(0, data[0], True)
    assert f.process_and_get_visibility(4, data[4], True)
    assert len(f.visibleNodeIds) == 2
    assert 0 in f.visibleNodeIds
    assert 4 in f.visibleNodeIds
    _assert_stats_update(viewUpdateQueue, presenter.FilterIds.PACKAGES_NOT_INSTALLED, 1, 1)

    # change the active mask to hidden
    f.set_active_mask(presenter.FilterIds.PACKAGES_HIDDEN)
    assert len(f.visibleNodeIds) == 1
    assert 0 in f.visibleNodeIds
    # reapply search
    f.apply_search([])
    assert len(f.visibleNodeIds) == 0
    _assert_stats_update(viewUpdateQueue, presenter.FilterIds.PACKAGES_NOT_INSTALLED, 0, 1)

    # change the active mask to everything
    f.set_active_mask(presenter.FilterIds.PACKAGES_HIDDEN | \
                        presenter.FilterIds.PACKAGES_INSTALLED | \
                        presenter.FilterIds.PACKAGES_NOT_INSTALLED)
    assert len(f.visibleNodeIds) == 0
    # change the search string to "installed"
    f.apply_search([0, 3, 4])
    assert len(f.visibleNodeIds) == 3
    assert 0 in f.visibleNodeIds
    assert 3 in f.visibleNodeIds
    assert 4 in f.visibleNodeIds
    _assert_stats_updates(viewUpdateQueue,
                          {presenter.FilterIds.PACKAGES_INSTALLED:(1,1),
                           presenter.FilterIds.PACKAGES_NOT_INSTALLED:(1,1)})

    # remove some data, including the installed package
    f.remove([1, 2, 3])
    assert len(f.visibleNodeIds) == 2
    assert 0 in f.visibleNodeIds
    assert 4 in f.visibleNodeIds
    _assert_stats_updates(viewUpdateQueue,
                          {presenter.FilterIds.PACKAGES_INSTALLED:(0,0),
                           presenter.FilterIds.PACKAGES_HIDDEN:(0,0)})

    # update the not installed package so that it is now installed
    assert f.process_and_get_visibility(4, data[3], True)
    assert len(f.visibleNodeIds) == 2
    assert 0 in f.visibleNodeIds
    assert 4 in f.visibleNodeIds
    _assert_stats_updates(viewUpdateQueue,
                          {presenter.FilterIds.PACKAGES_INSTALLED:(1,1),
                           presenter.FilterIds.PACKAGES_NOT_INSTALLED:(0,0)})

    # remove the search restriction; check that nothing changes
    f.apply_search(None)
    assert len(f.visibleNodeIds) == 2
    assert 0 in f.visibleNodeIds
    assert 4 in f.visibleNodeIds
    assert viewUpdateQueue.empty()


def dirty_list_filter_test():
    viewUpdateQueue = Queue.Queue()
    f = filters.DirtyFilter(viewUpdateQueue)

    # define data structure
    data = {}
    fileAttributes1 = node_attributes.FileNodeAttributes()
    fileAttributes1.label = "cleanFile"
    data[0] = fileAttributes1
    fileAttributes2 = node_attributes.FileNodeAttributes()
    fileAttributes2.label = "newFile"
    fileAttributes2.isDirty = True
    fileAttributes2.pendingOperation = model.Operations.COPY
    data[1] = fileAttributes2
    fileAttributes3 = node_attributes.FileNodeAttributes()
    fileAttributes3.label = "updatedFile"
    fileAttributes3.isDirty = True
    fileAttributes3.pendingOperation = model.Operations.OVERWRITE
    data[2] = fileAttributes3
    dirAttributes1 = node_attributes.DirectoryNodeAttributes()
    dirAttributes1.label = "aDir"
    dirAttributes1.isDirty = True
    data[3] = dirAttributes1
    fileAttributes4 = node_attributes.FileNodeAttributes()
    fileAttributes4.isDirty = True
    fileAttributes4.label = "oldFile"
    fileAttributes4.pendingOperation = model.Operations.DELETE
    data[4] = fileAttributes4

    # test initial conditions
    assert len(f.visibleNodeIds) == 0
    assert viewUpdateQueue.empty()

    # add some data with no active filters
    assert not f.process_and_get_visibility(0, data[0])
    assert len(f.visibleNodeIds) == 0
    assert viewUpdateQueue.empty()

    assert not f.process_and_get_visibility(1, data[1])
    assert len(f.visibleNodeIds) == 0
    _assert_stats_update(viewUpdateQueue, presenter.FilterIds.DIRTY_ADD, 1, 1)

    # set the filter
    assert f.set_active_mask(
        presenter.FilterIds.DIRTY_ADD|presenter.FilterIds.DIRTY_DELETE)
    assert len(f.visibleNodeIds) == 1
    assert 1 in f.visibleNodeIds

    assert not f.process_and_get_visibility(2, data[2])
    assert len(f.visibleNodeIds) == 1
    assert 1 in f.visibleNodeIds
    _assert_stats_update(viewUpdateQueue, presenter.FilterIds.DIRTY_UPDATE, 1, 1)

    assert not f.process_and_get_visibility(3, data[3])
    assert len(f.visibleNodeIds) == 1
    assert 1 in f.visibleNodeIds
    assert viewUpdateQueue.empty()

    assert f.process_and_get_visibility(4, data[4])
    assert len(f.visibleNodeIds) == 2
    assert 1 in f.visibleNodeIds
    assert 4 in f.visibleNodeIds
    _assert_stats_update(viewUpdateQueue, presenter.FilterIds.DIRTY_DELETE, 1, 1)

    # try removing the DIRTY_ADD node
    f.remove([1])
    assert len(f.visibleNodeIds) == 1
    assert 4 in f.visibleNodeIds
    _assert_stats_update(viewUpdateQueue, presenter.FilterIds.DIRTY_ADD, 0, 0)


def conflict_list_filter_test():
    viewUpdateQueue = Queue.Queue()
    f = filters.ConflictsFilter(viewUpdateQueue, 1)

    # define data structure
    data = {}
    fileAttributes1 = node_attributes.FileNodeAttributes()
    fileAttributes1.label = "file1"
    fileAttributes1.packageNodeId = 100
    fileAttributes1.crc = 0x11111111
    fileAttributes1.isInstalled = True
    data[0] = fileAttributes1
    fileAttributes2 = node_attributes.FileNodeAttributes()
    fileAttributes2.label = "file1"
    fileAttributes2.packageNodeId = 101
    fileAttributes2.crc = 0x22222222
    fileAttributes2.isInstalled = True
    data[1] = fileAttributes2
    fileAttributes3 = node_attributes.FileNodeAttributes()
    fileAttributes3.label = "file1"
    fileAttributes3.packageNodeId = 102
    fileAttributes3.crc = 0x11111111
    fileAttributes3.isInstalled = False
    data[2] = fileAttributes3

    # test initial conditions
    assert len(f.visibleNodeIds) == 0
    assert viewUpdateQueue.empty()

    # set active filters
    f.set_active_mask(presenter.FilterIds.CONFLICTS_SELECTED| \
                      presenter.FilterIds.CONFLICTS_ACTIVE| \
                      presenter.FilterIds.CONFLICTS_HIGHER| \
                      presenter.FilterIds.CONFLICTS_MISMATCHED)

    # add data
    assert f.process_and_get_visibility(0, data[0], data[1], 2)
    assert len(f.visibleNodeIds) == 1
    assert (101, 0) in f.visibleNodeIds
    _assert_stats_updates(viewUpdateQueue,
                          {presenter.FilterIds.CONFLICTS_SELECTED:(1,1),
                           presenter.FilterIds.CONFLICTS_ACTIVE:(1,1),
                           presenter.FilterIds.CONFLICTS_HIGHER:(1,1),
                           presenter.FilterIds.CONFLICTS_MISMATCHED:(1,1)})

    assert not f.process_and_get_visibility(0, data[0], data[2], 3)
    _assert_stats_updates(viewUpdateQueue,
                          {presenter.FilterIds.CONFLICTS_SELECTED:(1,2),
                           presenter.FilterIds.CONFLICTS_INACTIVE:(0,1),
                           presenter.FilterIds.CONFLICTS_HIGHER:(1,2),
                           presenter.FilterIds.CONFLICTS_MATCHED:(0,1)})


def selected_list_filter_test():
    viewUpdateQueue = Queue.Queue()
    f = filters.SelectedFilter(viewUpdateQueue)

    # define data structure
    data = {}
    fileAttributes1 = node_attributes.FileNodeAttributes()
    fileAttributes1.label = "matchedFile"
    fileAttributes1.isMatched = True
    data[0] = fileAttributes1
    fileAttributes2 = node_attributes.FileNodeAttributes()
    fileAttributes2.label = "mismatchedFile"
    fileAttributes2.isInstalled = True
    fileAttributes2.isMismatched = True
    data[1] = fileAttributes2
    fileAttributes3 = node_attributes.FileNodeAttributes()
    fileAttributes3.label = "missingFile"
    fileAttributes3.isInstalled = True
    fileAttributes3.isMissing = True
    data[2] = fileAttributes3
    fileAttributes4 = node_attributes.FileNodeAttributes()
    fileAttributes4.label = "conflictingFile"
    fileAttributes4.isInstalled = True
    fileAttributes4.hasConflicts = True
    fileAttributes4.isMatched = True
    data[3] = fileAttributes4

    # add data
    assert not f.process_and_get_visibility(0, data[0])
    assert len(f.visibleNodeIds) == 0
    assert viewUpdateQueue.empty()
    assert not f.process_and_get_visibility(1, data[1])
    assert len(f.visibleNodeIds) == 0
    _assert_stats_updates(viewUpdateQueue,
                          {presenter.FilterIds.SELECTED_MISMATCHED:(1,1),
                           presenter.FilterIds.SELECTED_NO_CONFLICTS:(1,1)})
    assert not f.process_and_get_visibility(2, data[2])
    assert len(f.visibleNodeIds) == 0
    _assert_stats_updates(viewUpdateQueue,
                          {presenter.FilterIds.SELECTED_MISSING:(1,1),
                           presenter.FilterIds.SELECTED_NO_CONFLICTS:(2,2)})
    assert not f.process_and_get_visibility(3, data[3])
    assert len(f.visibleNodeIds) == 0
    _assert_stats_updates(viewUpdateQueue,
                          {presenter.FilterIds.SELECTED_MATCHED:(1,1),
                           presenter.FilterIds.SELECTED_HAS_CONFLICTS:(1,1)})


def unselected_list_filter_test():
    viewUpdateQueue = Queue.Queue()
    f = filters.UnselectedFilter(viewUpdateQueue)

    # define data structure
    data = {}
    fileAttributes1 = node_attributes.FileNodeAttributes()
    fileAttributes1.label = "matchedFile"
    fileAttributes1.isInstalled = True
    fileAttributes1.isMatched = True
    data[0] = fileAttributes1
    fileAttributes2 = node_attributes.FileNodeAttributes()
    fileAttributes2.label = "mismatchedFile"
    fileAttributes2.isNotInstalled = True
    fileAttributes2.isMismatched = True
    data[1] = fileAttributes2
    fileAttributes3 = node_attributes.FileNodeAttributes()
    fileAttributes3.label = "missingFile"
    fileAttributes3.isNotInstalled = True
    fileAttributes3.isMissing = True
    data[2] = fileAttributes3
    fileAttributes4 = node_attributes.FileNodeAttributes()
    fileAttributes4.label = "conflictingFile"
    fileAttributes4.isNotInstalled = True
    fileAttributes4.hasConflicts = True
    fileAttributes4.isMatched = True
    data[3] = fileAttributes4

    # add data
    assert not f.process_and_get_visibility(0, data[0])
    assert len(f.visibleNodeIds) == 0
    assert viewUpdateQueue.empty()
    assert not f.process_and_get_visibility(1, data[1])
    assert len(f.visibleNodeIds) == 0
    _assert_stats_updates(viewUpdateQueue,
                          {presenter.FilterIds.UNSELECTED_MISMATCHED:(1,1),
                           presenter.FilterIds.UNSELECTED_NO_CONFLICTS:(1,1)})
    assert not f.process_and_get_visibility(2, data[2])
    assert len(f.visibleNodeIds) == 0
    _assert_stats_updates(viewUpdateQueue,
                          {presenter.FilterIds.UNSELECTED_MISSING:(1,1),
                           presenter.FilterIds.UNSELECTED_NO_CONFLICTS:(2,2)})
    assert not f.process_and_get_visibility(3, data[3])
    assert len(f.visibleNodeIds) == 0
    _assert_stats_updates(viewUpdateQueue,
                          {presenter.FilterIds.UNSELECTED_MATCHED:(1,1),
                           presenter.FilterIds.UNSELECTED_HAS_CONFLICTS:(1,1)})


def skipped_list_filter_test():
    viewUpdateQueue = Queue.Queue()
    f = filters.SkippedFilter(viewUpdateQueue)

    # define data structure
    data = {}
    fileAttributes1 = node_attributes.FileNodeAttributes()
    fileAttributes1.label = "regularFile"
    data[0] = fileAttributes1
    fileAttributes2 = node_attributes.FileNodeAttributes()
    fileAttributes2.label = "maskedFile"
    fileAttributes2.isMasked= True
    data[1] = fileAttributes2
    fileAttributes3 = node_attributes.FileNodeAttributes()
    fileAttributes3.label = "cruftFile"
    fileAttributes3.isCruft = True
    data[2] = fileAttributes3

    # add data
    assert not f.process_and_get_visibility(0, data[0])
    assert len(f.visibleNodeIds) == 0
    assert viewUpdateQueue.empty()
    assert not f.process_and_get_visibility(1, data[1])
    assert len(f.visibleNodeIds) == 0
    _assert_stats_update(viewUpdateQueue, presenter.FilterIds.SKIPPED_MASKED, 1, 1)
    assert not f.process_and_get_visibility(2, data[2])
    assert len(f.visibleNodeIds) == 0
    _assert_stats_update(viewUpdateQueue, presenter.FilterIds.SKIPPED_NONGAME, 1, 1)


def last_bits_test():
    class DummyFilter(filters._FilterGroup):
        def __init__(self, viewUpdateQueue):
            filters._FilterGroup.__init__(
                self,
                filters._OrFilter([
                    filters._AndFilter([filters._SkippedMaskedFilter(viewUpdateQueue),
                                        filters._SkippedNonGameFilter(viewUpdateQueue)]),
                    filters._AndFilter([filters._DirtyAddFilter(viewUpdateQueue),
                                        filters._DirtyDeleteFilter(viewUpdateQueue)])]))
    class DummyFilter2(filters._FilterGroup):
        def __init__(self, viewUpdateQueue):
            filters._FilterGroup.__init__(
                self,
                filters._AndFilter([
                    filters._OrFilter([filters._SkippedMaskedFilter(viewUpdateQueue),
                                       filters._SkippedNonGameFilter(viewUpdateQueue)]),
                    filters._OrFilter([filters._DirtyAddFilter(viewUpdateQueue),
                                       filters._DirtyDeleteFilter(viewUpdateQueue)])]))

    viewUpdateQueue = Queue.Queue()
    f = DummyFilter(viewUpdateQueue)
    f2 = DummyFilter2(viewUpdateQueue)

    data = {}
    fileAttributes1 = node_attributes.FileNodeAttributes()
    fileAttributes1.label = "testFile"
    fileAttributes1.isMasked = True
    fileAttributes1.pendingOperation = model.Operations.COPY
    data[0] = fileAttributes1
    fileAttributes2 = node_attributes.FileNodeAttributes()
    fileAttributes2.label = "testFile2"
    fileAttributes2.isMasked = True
    fileAttributes2.isCruft = True
    data[1] = fileAttributes2

    assert not f.process_and_get_visibility(0, data[0])
    assert not f2.process_and_get_visibility(1, data[1])

    f.set_active_mask(presenter.FilterIds.SKIPPED_MASKED|\
                      presenter.FilterIds.SKIPPED_NONGAME)
    f2.set_active_mask(presenter.FilterIds.SKIPPED_MASKED|\
                       presenter.FilterIds.SKIPPED_NONGAME)
    assert f.process_and_get_visibility(1, data[1])
    f.set_active_mask(presenter.FilterIds.DIRTY_ADD|\
                      presenter.FilterIds.DIRTY_DELETE)
    f2.set_active_mask(presenter.FilterIds.DIRTY_ADD|\
                       presenter.FilterIds.DIRTY_DELETE)
