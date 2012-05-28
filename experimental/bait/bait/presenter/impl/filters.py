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

from ... import model, presenter


_logger = logging.getLogger(__name__)

_CONFLICT_LOCAL_NODE_ATTRIBUTES_IDX = 0
_CONFLICT_OTHER_NODE_ATTRIBUTES_IDX = 1
_CONFLICT_LOCAL_PACKAGE_ORDINAL_IDX = 2
_CONFLICT_OTHER_PACKAGE_ORDINAL_IDX = 3


class _Filter:
    """This class and all subclasses are intended only for single-threaded access"""
    def __init__(self, idMask):
        assert(idMask != presenter.FilterIds.NONE)
        self.idMask = idMask
        self._activeMask = presenter.FilterIds.NONE
        self.visibleNodeIds = None
    def set_active_mask(self, idMask):
        """returns the bitwise xor between the relevant bits of the old mask and the new
        one"""
        activeMask = self.idMask & idMask
        diff = self._activeMask ^ activeMask
        _logger.debug("changing activemask for %s(%s) from %s to %s (diff: %s)",
                      self.__class__.__name__, self.idMask,
                      self._activeMask, activeMask, diff)
        self._activeMask = activeMask
        return diff
    def get_active_mask(self):
        return self._activeMask
    def is_active(self):
        return self._activeMask != 0
    def process_and_get_visibility(self, nodeId, nodeAttributes):
        """adds node to appropriate sets and returns true if this node is visible at this
        filter level (although it may not be visible at the top level)"""
        raise NotImplementedError("subclass must implement")
    def get_visible_node_ids(self, filterMask):
        # returns set of nodes that are visible when filterMask is the active filter mask
        raise NotImplementedError("subclass must implement")
    def remove(self, nodeIds):
        """remove nodes from state"""
        raise NotImplementedError("subclass must implement")
    def refresh_view(self, getHypotheticalVisibleNodeIdsFn):
        """sync node counts to the filter button labels in the view"""
        raise NotImplementedError("subclass must implement")
    def update_view(self, nodeId, getHypotheticalVisibilityFn):
        """incrementally update the view"""
        raise NotImplementedError("subclass must implement")

class _FilterButton(_Filter):
    def __init__(self, filterId, viewUpdateQueue):
        _Filter.__init__(self, filterId)
        self._viewUpdateQueue = viewUpdateQueue
        self._matchedNodeIds = set()
        # only includes nodes that count in the label statistics
        self._hypotheticallyVisibleNodeIds = set()
        self._prevNumCurrentNodes = 0
        self._prevTotalNodes = 0
    def set_active_mask(self, idMask):
        diff = _Filter.set_active_mask(self, idMask)
        if self.is_active():
            self.visibleNodeIds = self._matchedNodeIds
        else:
            self.visibleNodeIds = None
        return diff
    def process_and_get_visibility(self, nodeId, nodeAttributes):
        if not self._match(nodeId, nodeAttributes):
            self._discard_node_id(nodeId)
            return False
        self._matchedNodeIds.add(nodeId)
        _logger.debug("filter %s matched node %s", self.idMask, nodeId)
        return self.is_active()
    def get_visible_node_ids(self, filterId):
        if filterId & self.idMask != 0:
            _logger.debug("contributing %d nodes from filter %s",
                          len(self._matchedNodeIds), self.idMask)
            return self._matchedNodeIds
        return None
    def remove(self, nodeIds):
        _logger.debug("removing nodes %s from filter %s", nodeIds, self.idMask)
        self._discard_node_ids(nodeIds)
    def refresh_view(self, getHypotheticalVisibleNodeIdsFn):
        visibleNodeIds = getHypotheticalVisibleNodeIdsFn(self.idMask)
        matchedNodeIds = self._get_matched_node_ids_for_stats()
        self._hypotheticallyVisibleNodeIds = matchedNodeIds.intersection(visibleNodeIds)
        self._sync_to_view(matchedNodeIds)
    def update_view(self, nodeId, getHypotheticalVisibilityFn):
        matchedNodeIds = self._get_matched_node_ids_for_stats()
        if nodeId in matchedNodeIds and \
           getHypotheticalVisibilityFn(nodeId, self.idMask) and \
           nodeId not in self._hypotheticallyVisibleNodeIds:
            _logger.debug("adding node %s to filter %s's hypothetically visible list",
                          nodeId, self.idMask)
            self._hypotheticallyVisibleNodeIds.add(nodeId)
        elif nodeId in self._hypotheticallyVisibleNodeIds:
            _logger.debug("removing node %s from filter %s's hypothetically visible list",
                          nodeId, self.idMask)
            self._hypotheticallyVisibleNodeIds.discard(nodeId)
        self._sync_to_view(matchedNodeIds)
    def _sync_to_view(self, matchedNodeIds):
        # TODO: don't send more than one update per time quantum to avoid flooding the UI,
        # TODO:   but make sure the most recent update doesn't get dropped
        numCurrentNodes = len(self._hypotheticallyVisibleNodeIds)
        totalNodes = len(matchedNodeIds)
        if numCurrentNodes != self._prevNumCurrentNodes or \
           totalNodes != self._prevTotalNodes:
            _logger.debug("syncing state to view: filter %s: %d/%d",
                          self.idMask, numCurrentNodes, totalNodes)
            self._viewUpdateQueue.put(presenter.SetFilterStatsCommand(
                self.idMask, numCurrentNodes, totalNodes))
            self._prevNumCurrentNodes = numCurrentNodes
            self._prevTotalNodes = totalNodes
        else:
            _logger.debug("not syncing identical state to view: %s: %d/%d",
              self.idMask, numCurrentNodes, totalNodes)
    def _discard_node_id(self, nodeId):
        self._matchedNodeIds.discard(nodeId)
    def _discard_node_ids(self, nodeIds):
        self._matchedNodeIds.difference_update(nodeIds)
        self._hypotheticallyVisibleNodeIds.difference_update(nodeIds)
    def _get_matched_node_ids_for_stats(self):
        return self._matchedNodeIds
    def _match(self, nodeId, nodeAttributes):
        """returns whether the filter matches the given node, regardless of whether it is
        active"""
        raise NotImplementedError("subclass must implement")

class _TreeFilterButton(_FilterButton):
    def __init__(self, filterId, viewUpdateQueue):
        _FilterButton.__init__(self, filterId, viewUpdateQueue)
        self._matchedLeafNodeIds = set()
    def _discard_node_id(self, nodeId):
        _FilterButton._discard_node_id(self, nodeId)
        self._matchedLeafNodeIds.discard(nodeId)
    def _discard_node_ids(self, nodeIds):
        _FilterButton._discard_node_ids(self, nodeIds)
        self._matchedLeafNodeIds.difference_update(nodeIds)
    def _get_matched_node_ids_for_stats(self):
        return self._matchedLeafNodeIds

class _AggregateFilter(_Filter):
    """Combines a collection of subfilters to form a boolean chain."""
    def __init__(self, filters):
        _Filter.__init__(self, self._get_aggregate_id(filters))
        if len(filters) < 2:
            raise RuntimeError("Cannot aggregate less than 2 subfilters")
        self._filters = filters
        self.visibleNodeIds = set()
    def set_active_mask(self, idMask):
        diff = _Filter.set_active_mask(self, idMask)
        if diff != 0:
            for f in self._filters:
                f.set_active_mask(idMask)
        return diff
    def process_and_get_visibility(self, nodeId, nodeAttributes):
        if self._process_and_get_visibility(nodeId, nodeAttributes):
            self.visibleNodeIds.add(nodeId)
            return True
        else:
            self.visibleNodeIds.discard(nodeId)
        return False
    def remove(self, nodeIds):
        self.visibleNodeIds.difference_update(nodeIds)
        for f in self._filters:
            f.remove(nodeIds)
    def refresh_view(self, getHypotheticalVisibleNodeIdsFn):
        for f in self._filters:
            f.refresh_view(getHypotheticalVisibleNodeIdsFn)
    def update_view(self, nodeId, getHypotheticalVisibilityFn):
        for f in self._filters:
            f.update_view(nodeId, getHypotheticalVisibilityFn)
    def _get_aggregate_id(self, filters):
        """ORs together the IDs of all aggregated filters"""
        filterId = presenter.FilterIds.NONE
        for f in filters:
            filterId |= f.idMask
        return filterId

class _OrFilter(_AggregateFilter):
    def __init__(self, filters):
        _AggregateFilter.__init__(self, filters)
    def set_active_mask(self, idMask):
        diff = _AggregateFilter.set_active_mask(self, idMask)
        if diff != 0:
            visibleNodeIdSets = [f.visibleNodeIds for f in self._filters if f.is_active()]
            if len(visibleNodeIdSets) == 0:
                self.visibleNodeIds = set()
            else:
                self.visibleNodeIds = set.union(*visibleNodeIdSets)
        return diff
    def get_visible_node_ids(self, filterId):
        if filterId in self.idMask:
            visibleNodeIdSets = [f.get_visible_node_ids(filterId) for f in self._filters]
            return set.union(*[v for v in visibleNodeIdSets if v is not None])
        return None
    def _process_and_get_visibility(self, nodeId, nodeAttributes):
        """returns false iff all subfilters return false"""
        retVal = False
        for f in self._filters:
            # don't break early -- newly mismatched nodes might need to be removed
            if f.process_and_get_visibility(nodeId, nodeAttributes):
                retVal = True
        return retVal

class _AndFilter(_AggregateFilter):
    def __init__(self, filters):
        _AggregateFilter.__init__(self, filters)
    def set_active_mask(self, idMask):
        diff = _AggregateFilter.set_active_mask(self, idMask)
        if diff != 0:
            visibleNodeIdSets = [f.visibleNodeIds for f in self._filters if f.is_active()]
            if len(visibleNodeIdSets) == 0:
                self.visibleNodeIds = set()
            else:
                self.visibleNodeIds = set.intersection(*visibleNodeIdSets)
        return diff
    def get_visible_node_ids(self, filterId):
        if filterId in self.idMask:
            visibleNodeIdSets = [f.get_visible_node_ids(filterId) for f in self._filters]
            return set.intersection(*[v for v in visibleNodeIdSets if v is not None])
        return None
    def _process_and_get_visibility(self, nodeId, nodeAttributes):
        """returns true iff all subfilters return true"""
        retVal = True
        for f in self._filters:
            # don't break early -- newly mismatched nodes might need to be removed
            if not f.process_and_get_visibility(nodeId, nodeAttributes):
                retVal = False
        return retVal

class _FilterGroup:
    def __init__(self, wrappedFilter):
        self.idMask = wrappedFilter.idMask
        self._filter = wrappedFilter
        self.visibleNodeIds = self._get_visible_node_ids()
        self._automatic_updates_enabled = True
    def set_active_mask(self, idMask):
        """sets active filters and returns whether state has changed"""
        _logger.debug("modifying active mask for %s: %s", self.__class__.__name__, idMask)
        # apply mask to filters so they can update their visible nodes
        if self._filter.set_active_mask(idMask) == 0:
            _logger.debug("no relevant changes to activeMask")
            return False
        # set top level visibleNodeIds
        self.visibleNodeIds = self._get_visible_node_ids()
        if self._automatic_updates_enabled:
            # update view button labels
            self._filter.refresh_view(self._get_hypothetical_visible_node_ids)
        _logger.debug("%s visibleNodeIds now: %s",
                      self.__class__.__name__, self.visibleNodeIds)
        return True
    def enable_automatic_updates(self, enabled):
        self._automatic_updates_enabled = enabled
        if enabled:
            _logger.debug("automatic updates enabled")
            self._filter.refresh_view(self._get_hypothetical_visible_node_ids)
        else:
            _logger.debug("automatic updates disabled")
    def process_and_get_visibility(self, nodeId, nodeAttributes):
        """adds/updates node and returns whether the node should be visible"""
        return self._process_and_get_visibility(nodeId, nodeAttributes, None)
    def remove(self, nodeIds):
        _logger.debug("removing nodes for %s: %s", self.__class__.__name__, nodeIds)
        # remove references to nodes from all data structures
        self._filter.remove(nodeIds)
        self._update_visible_node_ids(nodeIds, False, None)
        if self._automatic_updates_enabled:
            # update view button labels
            self._filter.refresh_view(self._get_hypothetical_visible_node_ids)
    def _process_and_get_visibility(self, nodeId, nodeAttributes, arg):
        """adds/updates node and returns whether the node should be visible"""
        _logger.debug("processing node for %s: %s", self.__class__.__name__, nodeId)
        # process and incrementally update state
        retVal = self._filter.process_and_get_visibility(nodeId, nodeAttributes)
        self._update_visible_node_ids(nodeId, retVal, arg)
        if self._automatic_updates_enabled:
            # update view button labels
            self._filter.update_view(nodeId, self._get_hypothetical_visibility)
        return retVal
    def _get_visible_node_ids(self):
        """subclass may override; default implementation returns a reference to the
        wrapped filter's visibleNodeIds set"""
        return self._filter.visibleNodeIds
    def _update_visible_node_ids(self, nodeIds, isVisible, arg):
        """subclass may override; default implementation assumes set has already been
        updated"""
        pass
    def _get_hypothetical_visible_node_ids(self, filterId):
        # returns set of nodes that would be visible if filterId were enabled
        activeMask = self._filter.get_active_mask()
        if filterId in activeMask:
            return self.visibleNodeIds
        return self._filter.get_visible_node_ids(activeMask|filterId)
    def _get_hypothetical_visibility(self, nodeId, filterId):
        # returns if the given node would be visible if filterId were enabled
        activeMask = self._filter.get_active_mask()
        if filterId in activeMask:
            return nodeId in self.visibleNodeIds
        visibleNodeIds = self._filter.get_visible_node_ids(activeMask|filterId)
        return visibleNodeIds is not None and nodeId in visibleNodeIds

class _HiddenPackagesFilter(_TreeFilterButton):
    """Controls display of hidden packages in the packages tree"""
    def __init__(self, viewUpdateQueue):
        _TreeFilterButton.__init__(self, presenter.FilterIds.PACKAGES_HIDDEN,
                                   viewUpdateQueue)
    def _match(self, nodeId, nodeAttributes):
        if nodeAttributes.nodeType is model.NodeTypes.PACKAGE and nodeAttributes.isHidden:
            self._matchedLeafNodeIds.add(nodeId)
            return True
        return False

class _InstalledPackagesFilter(_TreeFilterButton):
    """Controls display of installed packages in the packages tree"""
    def __init__(self, viewUpdateQueue):
        _TreeFilterButton.__init__(self, presenter.FilterIds.PACKAGES_INSTALLED,
                                   viewUpdateQueue)
    def _match(self, nodeId, nodeAttributes):
        if nodeAttributes.nodeType is model.NodeTypes.PACKAGE and \
           nodeAttributes.isInstalled:
            self._matchedLeafNodeIds.add(nodeId)
            return True
        return False

class _NotInstalledPackagesFilter(_TreeFilterButton):
    """Controls display of non-installed packages in the packages tree"""
    def __init__(self, viewUpdateQueue):
        _TreeFilterButton.__init__(self, presenter.FilterIds.PACKAGES_NOT_INSTALLED,
                                   viewUpdateQueue)
    def _match(self, nodeId, nodeAttributes):
        if nodeAttributes.nodeType is model.NodeTypes.PACKAGE and \
           nodeAttributes.isNotInstalled:
            self._matchedLeafNodeIds.add(nodeId)
            return True
        return False

class _AlwaysVisiblePackagesFilter(_TreeFilterButton):
    """Ensures marked packages are always visible"""
    def __init__(self, viewUpdateQueue):
        _TreeFilterButton.__init__(self, presenter.FilterIds.PACKAGES_ALWAYS_VISIBLE,
                                   viewUpdateQueue)
    def _match(self, nodeId, nodeAttributes):
        if nodeAttributes.nodeType is model.NodeTypes.PACKAGE and \
           nodeAttributes.alwaysVisible:
            self._matchedLeafNodeIds.add(nodeId)
            return True
        return False
    # override
    def _sync_to_view(self, matchedNodeIds):
        # no GUI counterpart, so no need to update
        pass

class _ResourceFilesFilter(_TreeFilterButton):
    """Controls display of resource files in the package contents tree"""
    def __init__(self, viewUpdateQueue):
        _TreeFilterButton.__init__(self, presenter.FilterIds.FILES_RESOURCES,
                                   viewUpdateQueue)
    def _match(self, nodeId, nodeAttributes):
        if nodeAttributes.nodeType is model.NodeTypes.FILE and nodeAttributes.isResource:
            self._matchedLeafNodeIds.add(nodeId)
            return True
        return False

class _PluginFilesFilter(_TreeFilterButton):
    """Controls display of plugin files in the package contents tree"""
    def __init__(self, viewUpdateQueue):
        _TreeFilterButton.__init__(self, presenter.FilterIds.FILES_PLUGINS,
                                   viewUpdateQueue)
    def _match(self, nodeId, nodeAttributes):
        if nodeAttributes.nodeType is model.NodeTypes.FILE and nodeAttributes.isPlugin:
            self._matchedLeafNodeIds.add(nodeId)
            return True
        return False

class _OtherFilesFilter(_TreeFilterButton):
    """Controls display of cruft files in the package contents tree"""
    def __init__(self, viewUpdateQueue):
        _TreeFilterButton.__init__(self, presenter.FilterIds.FILES_OTHER, viewUpdateQueue)
    def _match(self, nodeId, nodeAttributes):
        if nodeAttributes.nodeType is model.NodeTypes.FILE and nodeAttributes.isOther:
            self._matchedLeafNodeIds.add(nodeId)
            return True
        return False

class _DirtyAddFilter(_FilterButton):
    """Controls display of pending additions in the dirty list"""
    def __init__(self, viewUpdateQueue):
        _FilterButton.__init__(self, presenter.FilterIds.DIRTY_ADD, viewUpdateQueue)
    def _match(self, nodeId, nodeAttributes):
        return nodeAttributes.nodeType is model.NodeTypes.FILE and \
               nodeAttributes.pendingOperation == model.AnnealOperationIds.COPY

class _DirtyUpdateFilter(_FilterButton):
    """Controls display of pending overwrites in the dirty list"""
    def __init__(self, viewUpdateQueue):
        _FilterButton.__init__(self, presenter.FilterIds.DIRTY_UPDATE, viewUpdateQueue)
    def _match(self, nodeId, nodeAttributes):
        return nodeAttributes.nodeType is model.NodeTypes.FILE and \
               nodeAttributes.pendingOperation == model.AnnealOperationIds.OVERWRITE

class _DirtyDeleteFilter(_FilterButton):
    """Controls display of pending deletes in the dirty list"""
    def __init__(self, viewUpdateQueue):
        _FilterButton.__init__(self, presenter.FilterIds.DIRTY_DELETE, viewUpdateQueue)
    def _match(self, nodeId, nodeAttributes):
        return nodeAttributes.nodeType is model.NodeTypes.FILE and \
               nodeAttributes.pendingOperation == model.AnnealOperationIds.DELETE

class _ConflictsSelectedFilter(_FilterButton):
    """Controls display of local selected files in the conflicts list"""
    def __init__(self, viewUpdateQueue):
        _FilterButton.__init__(self, presenter.FilterIds.CONFLICTS_SELECTED,
                               viewUpdateQueue)
    def _match(self, nodeId, nodeAttributes):
        # it is assumed that this is a file
        return nodeAttributes[_CONFLICT_LOCAL_NODE_ATTRIBUTES_IDX].isInstalled

class _ConflictsUnselectedFilter(_FilterButton):
    """Controls display of local unselected files in the conflicts list"""
    def __init__(self, viewUpdateQueue):
        _FilterButton.__init__(self, presenter.FilterIds.CONFLICTS_UNSELECTED,
                               viewUpdateQueue)
    def _match(self, nodeId, nodeAttributes):
        # it is assumed that this is a file
        return not nodeAttributes[_CONFLICT_LOCAL_NODE_ATTRIBUTES_IDX].isInstalled

class _ConflictsActiveFilter(_FilterButton):
    """Controls display of foreign selected files in the conflicts list"""
    def __init__(self, viewUpdateQueue):
        _FilterButton.__init__(self, presenter.FilterIds.CONFLICTS_ACTIVE,
                               viewUpdateQueue)
    def _match(self, nodeId, nodeAttributes):
        # it is assumed that this is a file
        return nodeAttributes[_CONFLICT_OTHER_NODE_ATTRIBUTES_IDX].isInstalled

class _ConflictsInactiveFilter(_FilterButton):
    """Controls display of foreign unselected files in the conflicts list"""
    def __init__(self, viewUpdateQueue):
        _FilterButton.__init__(self, presenter.FilterIds.CONFLICTS_INACTIVE,
                               viewUpdateQueue)
    def _match(self, nodeId, nodeAttributes):
        # it is assumed that this is a file
        return not nodeAttributes[_CONFLICT_OTHER_NODE_ATTRIBUTES_IDX].isInstalled

class _ConflictsHigherFilter(_FilterButton):
    """Controls display of files in higher-priority packages in the conflicts list"""
    def __init__(self, viewUpdateQueue):
        _FilterButton.__init__(self, presenter.FilterIds.CONFLICTS_HIGHER,
                               viewUpdateQueue)
    def _match(self, nodeId, nodeAttributes):
        # it is assumed that this is a file
        return nodeAttributes[_CONFLICT_LOCAL_PACKAGE_ORDINAL_IDX] < \
               nodeAttributes[_CONFLICT_OTHER_PACKAGE_ORDINAL_IDX]

class _ConflictsLowerFilter(_FilterButton):
    """Controls display of files in lower-priority packages in the conflicts list"""
    def __init__(self, viewUpdateQueue):
        _FilterButton.__init__(self, presenter.FilterIds.CONFLICTS_LOWER,
                               viewUpdateQueue)
    def _match(self, nodeId, nodeAttributes):
        # it is assumed that this is a file
        return nodeAttributes[_CONFLICT_LOCAL_PACKAGE_ORDINAL_IDX] > \
               nodeAttributes[_CONFLICT_OTHER_PACKAGE_ORDINAL_IDX]

class _ConflictsMatchedFilter(_FilterButton):
    """Controls display of matching files in other packages in the conflicts list"""
    def __init__(self, viewUpdateQueue):
        _FilterButton.__init__(self, presenter.FilterIds.CONFLICTS_MATCHED,
                               viewUpdateQueue)
    def _match(self, nodeId, nodeAttributes):
        # it is assumed that this is a file
        return nodeAttributes[_CONFLICT_LOCAL_NODE_ATTRIBUTES_IDX].crc == \
               nodeAttributes[_CONFLICT_OTHER_NODE_ATTRIBUTES_IDX].crc

class _ConflictsMismatchedFilter(_FilterButton):
    """Controls display of non-matching files in other packages in the conflicts list"""
    def __init__(self, viewUpdateQueue):
        _FilterButton.__init__(self, presenter.FilterIds.CONFLICTS_MISMATCHED,
                               viewUpdateQueue)
    def _match(self, nodeId, nodeAttributes):
        # it is assumed that this is a file
        return nodeAttributes[_CONFLICT_LOCAL_NODE_ATTRIBUTES_IDX].crc != \
               nodeAttributes[_CONFLICT_OTHER_NODE_ATTRIBUTES_IDX].crc

class _SelectedMatchedFilter(_FilterButton):
    """Controls display of selected, matched files in the selected list"""
    def __init__(self, viewUpdateQueue):
        _FilterButton.__init__(self, presenter.FilterIds.SELECTED_MATCHED,
                               viewUpdateQueue)
    def _match(self, nodeId, nodeAttributes):
        return nodeAttributes.isInstalled and nodeAttributes.isMatched

class _SelectedMismatchedFilter(_FilterButton):
    """Controls display of selected, mismatched files in the selected list"""
    def __init__(self, viewUpdateQueue):
        _FilterButton.__init__(self, presenter.FilterIds.SELECTED_MISMATCHED,
                               viewUpdateQueue)
    def _match(self, nodeId, nodeAttributes):
        return nodeAttributes.isInstalled and nodeAttributes.isMismatched

class _SelectedMissingFilter(_FilterButton):
    """Controls display of selected, missing files in the selected list"""
    def __init__(self, viewUpdateQueue):
        _FilterButton.__init__(self, presenter.FilterIds.SELECTED_MISSING,
                               viewUpdateQueue)
    def _match(self, nodeId, nodeAttributes):
        return nodeAttributes.isInstalled and nodeAttributes.isMissing

class _SelectedHasConflictsFilter(_FilterButton):
    """Controls display of selected, conflicting files in the selected list"""
    def __init__(self, viewUpdateQueue):
        _FilterButton.__init__(self, presenter.FilterIds.SELECTED_HAS_CONFLICTS,
                               viewUpdateQueue)
    def _match(self, nodeId, nodeAttributes):
        return nodeAttributes.isInstalled and nodeAttributes.hasConflicts

class _SelectedNoConflictsFilter(_FilterButton):
    """Controls display of selected, unique files in the selected list"""
    def __init__(self, viewUpdateQueue):
        _FilterButton.__init__(self, presenter.FilterIds.SELECTED_NO_CONFLICTS,
                               viewUpdateQueue)
    def _match(self, nodeId, nodeAttributes):
        return nodeAttributes.isInstalled and not nodeAttributes.hasConflicts

class _UnselectedMatchedFilter(_FilterButton):
    """Controls display of unselected, matched files in the unselected list"""
    def __init__(self, viewUpdateQueue):
        _FilterButton.__init__(self, presenter.FilterIds.UNSELECTED_MATCHED,
                               viewUpdateQueue)
    def _match(self, nodeId, nodeAttributes):
        return nodeAttributes.isNotInstalled and nodeAttributes.isMatched

class _UnselectedMismatchedFilter(_FilterButton):
    """Controls display of unselected, mismatched files in the unselected list"""
    def __init__(self, viewUpdateQueue):
        _FilterButton.__init__(self, presenter.FilterIds.UNSELECTED_MISMATCHED,
                               viewUpdateQueue)
    def _match(self, nodeId, nodeAttributes):
        return nodeAttributes.isNotInstalled and nodeAttributes.isMismatched

class _UnselectedMissingFilter(_FilterButton):
    """Controls display of unselected, missing files in the unselected list"""
    def __init__(self, viewUpdateQueue):
        _FilterButton.__init__(self, presenter.FilterIds.UNSELECTED_MISSING,
                               viewUpdateQueue)
    def _match(self, nodeId, nodeAttributes):
        return nodeAttributes.isNotInstalled and nodeAttributes.isMissing

class _UnselectedHasConflictsFilter(_FilterButton):
    """Controls display of unselected, conflicting files in the unselected list"""
    def __init__(self, viewUpdateQueue):
        _FilterButton.__init__(self, presenter.FilterIds.UNSELECTED_HAS_CONFLICTS,
                               viewUpdateQueue)
    def _match(self, nodeId, nodeAttributes):
        return nodeAttributes.isNotInstalled and nodeAttributes.hasConflicts

class _UnselectedNoConflictsFilter(_FilterButton):
    """Controls display of unselected, unique files in the unselected list"""
    def __init__(self, viewUpdateQueue):
        _FilterButton.__init__(self, presenter.FilterIds.UNSELECTED_NO_CONFLICTS,
                               viewUpdateQueue)
    def _match(self, nodeId, nodeAttributes):
        return nodeAttributes.isNotInstalled and not nodeAttributes.hasConflicts

class _SkippedMaskedFilter(_FilterButton):
    """Controls display of masked files in the skipped list"""
    def __init__(self, viewUpdateQueue):
        _FilterButton.__init__(self, presenter.FilterIds.SKIPPED_MASKED,
                               viewUpdateQueue)
    def _match(self, nodeId, nodeAttributes):
        return nodeAttributes.isMasked

class _SkippedNonGameFilter(_FilterButton):
    """Controls display of non-game files in the skipped list"""
    def __init__(self, viewUpdateQueue):
        _FilterButton.__init__(self, presenter.FilterIds.SKIPPED_NONGAME,
                               viewUpdateQueue)
    def _match(self, nodeId, nodeAttributes):
        return nodeAttributes.isCruft


class PackagesTreeFilter(_FilterGroup):
    """Filters contents of the packages tree"""
    def __init__(self, viewUpdateQueue):
        self._matchesSearchNodeIds = None
        _FilterGroup.__init__(self,
                              _OrFilter([_InstalledPackagesFilter(viewUpdateQueue),
                                         _HiddenPackagesFilter(viewUpdateQueue),
                                         _NotInstalledPackagesFilter(viewUpdateQueue),
                                         _AlwaysVisiblePackagesFilter(viewUpdateQueue)]))
    # override
    def set_active_mask(self, idMask):
        """sets active filters and returns whether state has changed"""
        # ensure the ALWAYS_VISIBLE filter is always active
        return _FilterGroup.set_active_mask(
            self, idMask|presenter.FilterIds.PACKAGES_ALWAYS_VISIBLE)
    def apply_search(self, matchesSearchNodeIds):
        _logger.debug("applying search; matched nodes: %s", matchesSearchNodeIds)
        if matchesSearchNodeIds is None:
            self._matchesSearchNodeIds = None
        else:
            self._matchesSearchNodeIds = set(matchesSearchNodeIds)
        self.visibleNodeIds = self._get_visible_node_ids()
        _logger.debug("%s visibleNodeIds now: %s",
                      self.__class__.__name__, self.visibleNodeIds)
        if self._automatic_updates_enabled:
            self._filter.refresh_view(self._get_hypothetical_visible_node_ids)
    def process_and_get_visibility(self, nodeId, nodeAttributes, matchesSearch):
        if self._matchesSearchNodeIds is not None:
            if matchesSearch:
                self._matchesSearchNodeIds.add(nodeId)
            else:
                self._matchesSearchNodeIds.discard(nodeId)
        return self._process_and_get_visibility(nodeId, nodeAttributes, matchesSearch) \
               and matchesSearch
    def _get_visible_node_ids(self):
        """and the search match nodes with the wrapped filter's visibleNodeIds set"""
        if self._matchesSearchNodeIds is None:
            return set(self._filter.visibleNodeIds)
        return self._matchesSearchNodeIds.intersection(self._filter.visibleNodeIds)
    def _update_visible_node_ids(self, nodeIds, isVisible, matchesSearch):
        if isVisible and matchesSearch:
            self.visibleNodeIds.add(nodeIds)
        else:
            if hasattr(nodeIds, "__iter__"):
                self.visibleNodeIds.difference_update(nodeIds)
            else:
                self.visibleNodeIds.discard(nodeIds)
    def _get_hypothetical_visible_node_ids(self, filterId):
        visibleNodeIds = _FilterGroup._get_hypothetical_visible_node_ids(self, filterId)
        if self._matchesSearchNodeIds is None:
            return visibleNodeIds
        return self._matchesSearchNodeIds.intersection(visibleNodeIds)
    def _get_hypothetical_visibility(self, nodeId, filterId):
        if self._matchesSearchNodeIds is not None and \
           nodeId not in self._matchesSearchNodeIds:
            return False
        return _FilterGroup._get_hypothetical_visibility(self, nodeId, filterId)

class PackageContentsTreeFilter(_FilterGroup):
    """Filters contents of the package contents tree"""
    def __init__(self, viewUpdateQueue):
        _FilterGroup.__init__(self,
                              _OrFilter([_ResourceFilesFilter(viewUpdateQueue),
                                         _PluginFilesFilter(viewUpdateQueue),
                                         _OtherFilesFilter(viewUpdateQueue)]))

class DirtyFilter(_FilterGroup):
    """Filters contents of the dirty files list"""
    def __init__(self, viewUpdateQueue):
        _FilterGroup.__init__(self,
                              _OrFilter([_DirtyAddFilter(viewUpdateQueue),
                                         _DirtyUpdateFilter(viewUpdateQueue),
                                         _DirtyDeleteFilter(viewUpdateQueue)]))

class ConflictsFilter(_FilterGroup):
    """Filters contents of the conflicts list.  visibleNodeIds will be a set of tuples of
    the form: (conflictingPackageNodeId, nodeId)"""
    def __init__(self, viewUpdateQueue, referencePackageIdx):
        _FilterGroup.__init__(self,
                              _AndFilter([
                                  _OrFilter([_ConflictsSelectedFilter(viewUpdateQueue),
                                             _ConflictsUnselectedFilter(
                                                 viewUpdateQueue)]),
                                  _OrFilter([_ConflictsActiveFilter(viewUpdateQueue),
                                             _ConflictsInactiveFilter(viewUpdateQueue)]),
                                  _OrFilter([_ConflictsHigherFilter(viewUpdateQueue),
                                             _ConflictsLowerFilter(viewUpdateQueue)]),
                                  _OrFilter([_ConflictsMismatchedFilter(viewUpdateQueue),
                                             _ConflictsMatchedFilter(viewUpdateQueue)])]))
        self._referencePackageIdx = referencePackageIdx
    def process_and_get_visibility(self, nodeId, nodeAttributes,
                                   conflictNodeAttributes, conflictNodePackageIdx):
        """It is assumed only file nodes with conflicts will be passed in here"""
        return _FilterGroup.process_and_get_visibility(
            self, (conflictNodeAttributes.packageNodeId, nodeId),
            (nodeAttributes, conflictNodeAttributes,
             self._referencePackageIdx, conflictNodePackageIdx))

class SelectedFilter(_FilterGroup):
    """Filters contents of the selected list"""
    def __init__(self, viewUpdateQueue):
        _FilterGroup.__init__(self,
                              _AndFilter([
                                  _OrFilter([_SelectedMatchedFilter(viewUpdateQueue),
                                             _SelectedMismatchedFilter(viewUpdateQueue),
                                             _SelectedMissingFilter(viewUpdateQueue)]),
                                  _OrFilter([
                                      _SelectedHasConflictsFilter(viewUpdateQueue),
                                      _SelectedNoConflictsFilter(viewUpdateQueue)])]))

class UnselectedFilter(_FilterGroup):
    """Filters contents of the unselected list"""
    def __init__(self, viewUpdateQueue):
        _FilterGroup.__init__(self,
                              _AndFilter([
                                  _OrFilter([_UnselectedMatchedFilter(viewUpdateQueue),
                                             _UnselectedMismatchedFilter(viewUpdateQueue),
                                             _UnselectedMissingFilter(viewUpdateQueue)]),
                                  _OrFilter([
                                      _UnselectedHasConflictsFilter(viewUpdateQueue),
                                      _UnselectedNoConflictsFilter(viewUpdateQueue)])]))

class SkippedFilter(_FilterGroup):
    """Filters contents of the dirty list"""
    def __init__(self, viewUpdateQueue):
        _FilterGroup.__init__(self,
                              _OrFilter([_SkippedMaskedFilter(viewUpdateQueue),
                                         _SkippedNonGameFilter(viewUpdateQueue)]))
