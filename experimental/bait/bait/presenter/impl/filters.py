# -*- coding: utf-8 -*-
#
# bait/presenter/impl/filters.py
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

from ... import model
from ... import presenter
from ...presenter import view_commands


_logger = logging.getLogger(__name__)


# elegant design, but does not meet all requirements
class _Filter:
    """Base class for filters"""
    def __init__(self, viewUpdateQueue, idMask):
        self.dirty = False
        self._viewUpdateQueue = viewUpdateQueue
        self._idMask = idMask
        self._activeMask = 0
        self._matchedNodeIds = set()
    def set_active_mask(self, idMask):
        """returns the bitwise xor between the relevant bits of the old mask and the new
        one"""
        activeMask = self._idMask & idMask
        diff = self._activeMask ^ activeMask
        _logger.debug("changing activemask from 0x%x to 0x%x (diff: 0x%x)",
                      self._activeMask, activeMask, diff)
        if self._activeMask is not activeMask:
            self._activeMask = activeMask
            self.dirty = True
        return diff
    def add(self, nodeId, nodeAttributes):
        """filters given node; returns whether node was successfully added (i.e. it
        matched this filter)"""
        if self._matches(nodeId, nodeAttributes):
            if nodeId not in self._matchedNodeIds:
                self._matchedNodeIds.add(nodeId)
                self.dirty = True
            return True
        else:
            self.remove(nodeId)
            return False
    def remove(self, nodeId):
        """removes given node from state"""
        if nodeId in self._matchedNodeIds:
            self._matchedNodeIds.discard(nodeId)
            self.dirty = True
    def update_view(self):
        self._update_view(len(self._matchedNodeIds))
    def reset(self):
        if len(self._matchedNodeIds) is 0:
            _logger.debug("state already reset")
        else:
            _logger.debug("resetting state")
            self._matchedNodeIds.clear()
            self.dirty = True
    def _matches(self, nodeId, nodeAttributes):
        """returns whether the specified node matches the filter, regardless of whether
        the filter is active"""
        raise NotImplementedError("subclass must override this method")
    def _update_view(self, numVisibleNodes):
        if not self.dirty:
            _logger.debug("view already up to date")
        else:
            numMatchedNodes = len(self._matchedNodeIds)
            _logger.debug("syncing state to view: filter 0x%x: %d/%d",
                          self._idMask, numVisibleNodes, numMatchedNodes)
            self._viewUpdateQueue.put(view_commands.SetFilterStats(
                self._idMask, numVisibleNodes, numMatchedNodes))
            self.dirty = False

class _AggregateFilter(_Filter):
    """Combines a collection of subfilters to form a boolean chain.  The matchedNodeIds
    set in AggregateFilter subclasses contains only nodeIds that match /active/
    subfilters"""
    def __init__(self, filters):
        _Filter.__init__(self, None, self._get_aggregate_id(filters))
        if len(filters) < 2:
            raise RuntimeError("Cannot aggregate less than 2 subfilters")
        self._filters = filters
        for filter in filters:
            # attach a set used for tracking nodes that are visible if the filter is
            # active, given the state of other filters in the aggregation
            filter._visibleNodeIds = set()
    def set_active_mask(self, idMask):
        for filter in self._filters:
            filter.set_active_mask(idMask)
        changedIdMask = _Filter.set_active_mask(self, idMask)
        self._refresh(changedIdMask)
        return changedIdMask
    def update_view(self):
        if self.dirty:
            for filter in self._filters:
                filter._update_view(len(filter._visibleNodeIds))
            self.dirty = False
    def remove(self, nodeId):
        for filter in self._filters:
            filter.remove(nodeId)
            if filter._dirty:
                self.dirty = True
        _Filter.remove(self, nodeId)
    def reset(self):
        for filter in self._filters:
            filter.reset()
            if filter._dirty:
                self.dirty = True
        _Filter.reset(self)
    def _get_aggregate_id(self, filters):
        """ORs together the IDs of all aggregated filters"""
        id = 0
        for filter in filters:
            id = id | filter._idMask
        return id
    def _refresh(self, changedIdMask):
        """updates the aggregate filter's matchedNodeIds set"""
        raise NotImplementedError("subclass must override this method")

class _AndFilter(_AggregateFilter):
    """ANDs a collection of subfilters.  Does not short-circuit boolean expression to
    ensure all subfilters have accurate statistics"""
    def __init__(self, filters):
        _AggregateFilter.__init__(self, filters)
    def _matches(self, nodeId, nodeAttributes):
        """returns true iff all subfilters return true"""
        retVal = True
        for filter in self._filters:
            if not filter.passes(nodeId, nodeAttributes):
                retVal = False
        return retVal
    def _refresh(self, changedIdMask):
        """resyncs to the intersection of the subfilters"""
        matchedNodeIds = None
        copyPending = True
        for filter in self._filters:
            if filter._activeMask is not 0:
                if matchedNodeIds is None:
                    matchedNodeIds = filter._matchedNodeIds
                else:
                    matchedNodeIds = matchedNodeIds.intersection(filter._matchedNodeIds)
                    copyPending = False
        if matchedNodeIds is None:
            self._matchedNodeIds = set()
        elif copyPending:
            self._matchedNodeIds = set(matchedNodeIds)
        else:
            self._matchedNodeIds = matchedNodeIds

class _OrFilter(_AggregateFilter):
    """ORs a collection of subfilters.  Does not short-circuit boolean expression to
    ensure all subfilters have accurate statistics"""
    def __init__(self, filters):
        _AggregateFilter.__init__(self, filters)
        self._isDisjoint = True
        self._containsAggregateFilters = False
        for filter in self._filters:
            if isinstance(filter, _AggregateFilter):
                self._containsAggregateFilters = True
    def remove(self, nodeId):
        _AggregateFilter.remove(self, nodeId)
        if len(self._matchedNodeIds) is 0:
            self._isDisjoint = True
    def reset(self):
        _AggregateFilter.reset(self)
        self._isDisjoint = True
    def _matches(self, nodeId, nodeAttributes):
        """returns true iff at least on subfilter returns true"""
        retVal = False
        for filter in self._filters:
            if filter.passes(nodeId, nodeAttributes):
                if retVal:
                    self._isDisjoint = False
                retVal = True
        return retVal
    def _refresh_fast(self, changedIdMask):
        # if the subfilters are disjoint, we can refresh faster by just addressing the
        # changed subfilter(s).  if the subfilters are aggregate filters, the entire
        # aggregate filter must be switched on or off for this to make sense
        if not self._isDisjoint:
            return False
        # ensure that this optimization is applicable
        remainingChangedIdMask = changedIdMask
        for filter in self._filters:
            if filter._id & remainingChangedIdMask is filter._id:
                remainingChangedIdMask = remainingChangedIdMask ^ filter._id
        if remainingChangedIdMask is not 0:
            return False
        # we're good
        remainingChangedIdMask = changedIdMask
        for filter in self._filters:
            if remainingChangedIdMask is 0:
                break
            if filter._id & remainingChangedIdMask is filter._id:
                remainingChangedIdMask = remainingChangedIdMask ^ filter._id
                if 0 == filter._activeMask:
                    # remove nodeIds from set
                    self._matchedNodeIds = self._matchedNodeIds.symmetric_difference(
                        filter._matchedNodeIds)
                else:
                    # add nodeIds to set
                    self._matchedNodeIds = self._matchedNodeIds.union(
                        filter._matchedNodeIds)
        return True

    def _refresh(self, changedIdMask):
        """resyncs to the union of the subfilters"""
        if self._refresh_fast(changedIdMask):
            return
        # otherwise, do it the slow way
        matchedNodeIds = None
        copyPending = True
        for filter in self._filters:
            if filter._activeMask is not 0:
                if matchedNodeIds is None:
                    matchedNodeIds = filter._matchedNodeIds
                else:
                    if self._isDisjoint and self._containsAggregateFilters:
                        # ensure sets are still disjoint
                        numDups = len(matchedNodeIds.intersection(filter._matchedNodeIds))
                        self._isDisjoint = numDups is 0
                    matchedNodeIds = matchedNodeIds.union(filter._matchedNodeIds)
                    copyPending = False
        if matchedNodeIds is None:
            self._matchedNodeIds = set()
        elif copyPending:
            self._matchedNodeIds = set(matchedNodeIds)
        else:
            self._matchedNodeIds = matchedNodeIds

# inelegant design, but meets requirements
class _SimpleFilter:
    def __init__(self, viewUpdateQueue, filterId):
        _logger.debug("initializing filter %s", filterId)
        self._viewUpdateQueue = viewUpdateQueue
        self.filterId = filterId
        self.active = False
        self.matchedNodeIds = set()
        self.visibleNodeIds = set()
    def set_active_mask(self, idMask):
        self.active = self.filterId & idMask is self.filterId
        if self.active: _logger.debug("activating filter %s", self.filterId)
        else: _logger.debug("deactivating filter %s", self.filterId)
    def update_view(self):
        numMatchedNodes = len(self.matchedNodeIds)
        numVisibleNodes = len(self.visibleNodeIds)
        _logger.debug("syncing state to view: filter %s: %d/%d",
                      self.filterId, numVisibleNodes, numMatchedNodes)
        self._viewUpdateQueue.put(view_commands.SetFilterStats(
            self.filterId, numVisibleNodes, numMatchedNodes))
    def matches(self, nodeId, nodeAttributes):
        """returns whether the specified node matches the filter, regardless of whether
        the filter is active"""
        raise NotImplementedError("subclass must override this method")

class _HiddenPackagesFilter(_SimpleFilter):
    """Controls display of hidden packages in the packages tree"""
    def __init__(self, viewUpdateQueue):
        _SimpleFilter.__init__(self, viewUpdateQueue, presenter.FilterIds.PACKAGES_HIDDEN)
    def matches(self, nodeId, nodeAttributes):
        """returns true iff it is a package node and is hidden."""
        return nodeAttributes.nodeType is model.NodeTypes.PACKAGE and \
               nodeAttributes.isHidden

class _InstalledPackagesFilter(_SimpleFilter):
    """Controls display of installed packages in the packages tree"""
    def __init__(self, viewUpdateQueue):
        _SimpleFilter.__init__(self, viewUpdateQueue,
                               presenter.FilterIds.PACKAGES_INSTALLED)
    def matches(self, nodeId, nodeAttributes):
        """returns true iff it is a package node and it is marked for install"""
        return nodeAttributes.nodeType is model.NodeTypes.PACKAGE and \
               nodeAttributes.isInstalled

class _NotInstalledPackagesFilter(_SimpleFilter):
    """Controls display of non-installed packages in the packages tree"""
    def __init__(self, viewUpdateQueue):
        _SimpleFilter.__init__(self, viewUpdateQueue,
                               presenter.FilterIds.PACKAGES_NOT_INSTALLED)
    def matches(self, nodeId, nodeAttributes):
        """returns true iff it is a package node and is is marked neither as hidden or
        for install"""
        return nodeAttributes.nodeType is model.NodeTypes.PACKAGE and \
               not nodeAttributes.isInstalled and not nodeAttributes.isHidden

class _PackageTreeFilter:
    """Filters contents of the packages tree"""
    def __init__(self, viewUpdateQueue):
        self.visibleNodeIds = set()
        self._filters = [_HiddenPackagesFilter(viewUpdateQueue),
                         _InstalledPackagesFilter(viewUpdateQueue),
                         _NotInstalledPackagesFilter(viewUpdateQueue)]
    def set_active_mask(self, idMask):
        """adjusts state to reflect new filter configuration."""
        # if any filters have changed state, recalculate top-level visibleNodes
        visibleNodeIds = set()
        for f in self._filters:
            f.set_active_mask(idMask)
            if f.active:
                _logger.debug("adding %d visible nodes from filter %s",
                              len(f.visibleNodeIds), f.filterId)
                visibleNodeIds.update(f.visibleNodeIds)
        self.visibleNodeIds = visibleNodeIds
        _logger.debug("PackagesTreeFilter visible nodes: %s", self.visibleNodeIds)

    def apply_search(self, matchesSearchNodeIds):
        """adjusts state to reflect new search overlay.  returns True if state has
        changed"""
        # intersect set with each child's matchedNodes set to form the child's visibleNode
        # set; set dirty flags only if state has changed
        _logger.debug("applying search; matched nodes: %s", matchesSearchNodeIds)
        visibleNodeIds = set()
        for f in self._filters:
            if matchesSearchNodeIds is None:
                f.visibleNodeIds = set(f.matchedNodeIds)
            else:
                f.visibleNodeIds = f.matchedNodeIds.intersection(matchesSearchNodeIds)
            if f.active:
                visibleNodeIds.update(f.visibleNodeIds)
        self.visibleNodeIds = visibleNodeIds
        _logger.debug("PackagesTreeFilter visible nodes: %s", self.visibleNodeIds)

    def filter(self, nodeId, nodeAttributes, matchesSearch):
        """adds or updates a node; adjusts state accordingly.  returns True if state has
        changed"""
        # for each child
        #   if the node matches, add to matched set
        #   if matchesSearch is True, add to child's visibleNodes
        #   if the child is additionally active, add to top-level visibleNodes set

        # ensure we don't remove a node that we just added to the visible set when a node
        # is updated
        addedVisibleNodeIds = set()
        for f in self._filters:
            if f.matches(nodeId, nodeAttributes):
                _logger.debug("match: node %d in filter %s", nodeId, f.filterId)
                f.matchedNodeIds.add(nodeId)
                if matchesSearch:
                    _logger.debug("visible: node %d in filter %s", nodeId, f.filterId)
                    f.visibleNodeIds.add(nodeId)
                    if f.active:
                        _logger.debug("visible: node %d", nodeId)
                        self.visibleNodeIds.add(nodeId)
                        addedVisibleNodeIds.add(nodeId)
                else:
                    _logger.debug("not visible: node %d in filter %s",
                                  nodeId, f.filterId)
                    f.visibleNodeIds.discard(nodeId)
            else:
                _logger.debug("not matched: node %d in filter %s", nodeId, f.filterId)
                if nodeId in f.matchedNodeIds:
                    _logger.debug("removing node %d from filter %s", nodeId, f.filterId)
                    f.matchedNodeIds.remove(nodeId)
                    f.visibleNodeIds.discard(nodeId)
                    if nodeId not in addedVisibleNodeIds:
                        _logger.debug("removing node %d from visible set", nodeId)
                        self.visibleNodeIds.discard(nodeId)
        _logger.debug("PackagesTreeFilter visible nodes: %s", self.visibleNodeIds)

    def remove(self, nodeId):
        """removes a node; adjusts state accordingly.  returns True if state has
        changed"""
        # remove from visibleNodes and all children's matched and visible sets
        _logger.debug("removing node %d", nodeId)
        for f in self._filters:
            f.matchedNodeIds.discard(nodeId)
            f.visibleNodeIds.discard(nodeId)
        self.visibleNodeIds.discard(nodeId)
        _logger.debug("PackagesTreeFilter visible nodes: %s", self.visibleNodeIds)

    def update_view(self):
        """if there are changes to sync, syncs filter state and statistics to view"""
        for f in self._filters:
            f.update_view()

# stub classes for now until I figure out the above mess
class _StubFilter:
    def __init__(self, viewUpdateQueue, filterIds):
        self.visibleNodeIds = set()
        self._matchedNodeIds = set()
        self._matchedLeafNodeIds = set()
        self._viewUpdateQueue = viewUpdateQueue
        self._filterIds = filterIds
    def set_active_mask(self, idMask):
        _logger.debug("modifying active mask for %s: %s", self.__class__.__name__, idMask)
    def filter(self, nodeId, nodeAttributes, matchesSearch=True):
        _logger.debug("filtering node for %s: %d", self.__class__.__name__, nodeId)
        self._matchedNodeIds.add(nodeId)
        if matchesSearch:
            self.visibleNodeIds.add(nodeId)
    def remove(self, nodeId):
        _logger.debug("removing node for %s: %d", self.__class__.__name__, nodeId)
        self._matchedNodeIds.discard(nodeId)
        self.visibleNodeIds.discard(nodeId)
    def update_view(self):
        _logger.debug("updating view for %s", self.__class__.__name__)
        for filterId in self._filterIds:
            self._viewUpdateQueue.put(view_commands.SetFilterStats(
                filterId, len(self.visibleNodeIds), len(self._matchedNodeIds)))

class PackageTreeFilter(_StubFilter):
    """Filters contents of the packages tree"""
    def __init__(self, viewUpdateQueue):
        _StubFilter.__init__(self, viewUpdateQueue,
                             [presenter.FilterIds.PACKAGES_HIDDEN,
                              presenter.FilterIds.PACKAGES_INSTALLED,
                              presenter.FilterIds.PACKAGES_NOT_INSTALLED])
    def apply_search(self, matchesSearchNodeIds):
        _logger.debug("applying search; matched nodes: %s", matchesSearchNodeIds)
        if matchesSearchNodeIds is None:
            self.visibleNodeIds = set(self._matchedNodeIds)
        else:
            self._visibleNodeIds = self._matchedNodeIds.intersection(matchesSearchNodeIds)

class FileTreeFilter(_StubFilter):
    """Filters contents of the files tree"""
    def __init__(self, viewUpdateQueue):
        _StubFilter.__init__(self, viewUpdateQueue,
                             [presenter.FilterIds.FILES_PLUGINS,
                              presenter.FilterIds.FILES_RESOURCES,
                              presenter.FilterIds.FILES_OTHER])

class DirtyFilter(_StubFilter):
    """Filters contents of the dirty list"""
    def __init__(self, viewUpdateQueue):
        _StubFilter.__init__(self, viewUpdateQueue,
                             [presenter.FilterIds.DIRTY_ADD,
                              presenter.FilterIds.DIRTY_UPDATE,
                              presenter.FilterIds.DIRTY_DELETE])

class ConflictsFilter(_StubFilter):
    """Filters contents of the conflicts list"""
    def __init__(self, viewUpdateQueue):
        _StubFilter.__init__(self, viewUpdateQueue,
                             [presenter.FilterIds.CONFLICTS_ACTIVE,
                              presenter.FilterIds.CONFLICTS_HIGHER,
                              presenter.FilterIds.CONFLICTS_INACTIVE,
                              presenter.FilterIds.CONFLICTS_LOWER,
                              presenter.FilterIds.CONFLICTS_SELECTED,
                              presenter.FilterIds.CONFLICTS_UNSELECTED])

class SelectedFilter(_StubFilter):
    """Filters contents of the selected list"""
    def __init__(self, viewUpdateQueue):
        _StubFilter.__init__(self, viewUpdateQueue,
                             [presenter.FilterIds.SELECTED_MATCHED,
                              presenter.FilterIds.SELECTED_MISMATCHED,
                              presenter.FilterIds.SELECTED_MISSING,
                              presenter.FilterIds.SELECTED_OVERRIDDEN])

class UnselectedFilter(_StubFilter):
    """Filters contents of the unselected list"""
    def __init__(self, viewUpdateQueue):
        _StubFilter.__init__(self, viewUpdateQueue,
                             [presenter.FilterIds.UNSELECTED_MATCHED,
                              presenter.FilterIds.UNSELECTED_MISMATCHED,
                              presenter.FilterIds.UNSELECTED_MISSING,
                              presenter.FilterIds.UNSELECTED_OVERRIDDEN])

class SkippedFilter(_StubFilter):
    """Filters contents of the dirty list"""
    def __init__(self, viewUpdateQueue):
        _StubFilter.__init__(self, viewUpdateQueue,
                             [presenter.FilterIds.SKIPPED_MASKED,
                              presenter.FilterIds.SKIPPED_NONGAME])
