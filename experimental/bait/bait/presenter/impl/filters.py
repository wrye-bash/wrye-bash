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


_logger = logging.getLogger(__name__)


class _Filter:
    """Base class for filters"""
    def __init__(self, viewUpdateQueue, id):
        self.id = id
        self._viewUpdateQueue = viewUpdateQueue
        self._activeMask = 0
        self._matchedNodeIds = set()
        self._dirty = False
    def set_active_mask(self, idMask):
        """returns the bitwise xor between the relevant bits of the old mask and the new
        one"""
        activeMask = self.id & idMask
        diff = self._activeMask ^ activeMask
        if self._activeMask is not activeMask:
            self._activeMask = activeMask
            self._dirty = True
        return diff
    def update_view(self):
        if self._dirty:
            self._update_view()
            self._dirty = False
    def _update_view(self):
        """sends ViewUpdateCommands to sync state to view"""
        raise NotImplementedError("subclass must override this method")
    def remove(self, nodeId):
        if nodeId in self._matchedNodeIds:
            self._matchedNodeIds.discard(nodeId)
            self._dirty = True
    def passes(self, nodeId, nodeAttributes):
        """updates internal statistics returns whether the specified node passes the
        filter"""
        if self._matches(nodeId, nodeAttributes):
            if nodeId not in self._matchedNodeIds:
                self._matchedNodeIds.add(nodeId)
                self._dirty = True
            return self._activeMask
        else:
            self.remove(nodeId)
            return False
    def _matches(self, nodeId, nodeAttributes):
        """returns whether the specified node matches the filter, regardless of whether
        the filter is active"""
        raise NotImplementedError("subclass must override this method")
    def reset(self):
        if len(self._matchedNodeIds) is not 0:
            self._matchedNodeIds.clear()
            self._dirty = True
    def get_matched_node_ids(self):
        """returns the set of node ids that pass this filter"""
        return self._matchedNodeIds

class _AggregateFilter(_Filter):
    """Combines a collection of subfilters to form a boolean chain.  The matchedNodeIds
    set in AggregateFilter subclasses contains only nodeIds that match /and/ pass the
    subfilters"""
    def __init__(self, filters):
        _Filter.__init__(self, None, self._get_aggregate_id(filters))
        self._filters = filters
        if len(filters) < 2:
            raise RuntimeError("Cannot aggregate less than 2 subfilters")
    def set_active_mask(self, idMask):
        for filter in self._filters:
            filter.set_active_mask(idMask)
        changedIdMask = _Filter.set_active_mask(self, idMask)
        self._refresh(changedIdMask)
        return changedIdMask
    def update_view(self):
        if self._dirty:
            for filter in self._filters:
                filter.update_view()
            self._dirty = False
    def remove(self, nodeId):
        for filter in self._filters:
            filter.remove(nodeId)
            if filter._dirty:
                self._dirty = True
        _Filter.remove(self, nodeId)
    def reset(self):
        for filter in self._filters:
            filter.reset()
            if filter._dirty:
                self._dirty = True
        _Filter.reset(self)
    def _get_aggregate_id(self, filters):
        """ORs together the IDs of all aggregated filters"""
        id = 0
        for filter in filters:
            id = id | filter.id
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

class _HiddenPackagesFilter(_Filter):
    """Controls display of hidden packages in the packages tree"""
    def __init__(self, viewUpdateQueue):
        _Filter.__init__(self, viewUpdateQueue, presenter.FILTER_ID_PACKAGES_HIDDEN)
    def _matches(self, nodeId, nodeAttributes):
        """If it is a package node, returns True if the package is hidden.  If it is a
        group node, returns True if the group contains any hidden packages.  Otherwise,
        returns False."""
        isHiddenPackage = nodeAttributes.nodeType is model.NODE_TYPE_PACKAGE and \
                        nodeAttributes.hidden
        isHiddenGroup = nodeAttributes.nodeType is model.NODE_TYPE_GROUP and \
                        nodeAttributes.hasHidden
        return isHiddenPackage or isHiddenGroup

class _InstalledPackagesFilter(_Filter):
    """Controls display of installed packages in the packages tree"""
    def __init__(self, viewUpdateQueue):
        _Filter.__init__(self, viewUpdateQueue, presenter.FILTER_ID_PACKAGES_INSTALLED)
    def _matches(self, nodeId, nodeAttributes):
        """If it is a package node, returns True if the package is marked for install.  If
        it is a group node, returns True if the group contains any installed packages.
        Otherwise, returns False."""
        isInstalledPackage = nodeAttributes.nodeType is model.NODE_TYPE_PACKAGE and \
                        nodeAttributes.installed
        isInstalledGroup = nodeAttributes.nodeType is model.NODE_TYPE_GROUP and \
                        nodeAttributes.hasInstalled
        return isInstalledPackage or isInstalledGroup

class _NotInstalledPackagesFilter(_Filter):
    """Controls display of non-installed packages in the packages tree"""
    def __init__(self, viewUpdateQueue):
        _Filter.__init__(self, viewUpdateQueue,
                         presenter.FILTER_ID_PACKAGES_NOT_INSTALLED)
    def _matches(self, nodeId, nodeAttributes):
        """If it is a package node, returns True if the package is not hidden, but not
        marked for install.  If it is a group node, returns True if the group contains any
        non-hidden, non-installed packages.  Otherwise, returns False."""
        isNotInstalledPackage = nodeAttributes.nodeType is model.NODE_TYPE_PACKAGE and \
                        not nodeAttributes.installed and not nodeAttributes.hidden
        isNotInstalledGroup = nodeAttributes.nodeType is model.NODE_TYPE_GROUP and \
                        nodeAttributes.hasNotInstalled
        return isNotInstalledPackage or isNotInstalledGroup

class PackageTreeFilter(_OrFilter):
    """Filters contents of the packages tree"""
    def __init__(self, viewUpdateQueue):
        _OrFilter.__init__(self,
                           (_HiddenPackagesFilter(viewUpdateQueue),
                            _InstalledPackagesFilter(viewUpdateQueue),
                            _NotInstalledPackagesFilter(viewUpdateQueue)))
