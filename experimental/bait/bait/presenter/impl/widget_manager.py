# -*- coding: utf-8 -*-
#
# bait/presenter/impl/widget_manager.py
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
import threading

from .. import model


_logger = logging.getLogger(__name__)


class _StateChange(enum.Enum):
    __enumerables__ = ('UNKNOWN', 'FILTER', 'SEARCH')
    FILTER = None
    SEARCH = None

class _WidgetManagerBase:
    def __init__(self, name, dataFetcher, diffEngine):
        self._name = name
        self._dataFetcher = dataFetcher
        self._diffEngine = diffEngine
        self._stateChangeQueue = Queue.Queue()
        self._processingThread = threading.Thread(
            target=self._process_updates, name=name+"WidgetManager")

    def start(self):
        _logger.debug("starting %sWidgetManager", self._name)
        self._processingThread.start()

    def shutdown(self):
        """assumes that the data fetcher has been shut down by this point and that nothing
        else can be enqueued into the stateChangeQueue"""
        _logger.debug("shutting %sWidgetManager down", self._name)
        self._stateChangeQueue.put(None)
        self._processingThread.join()

    def handle_update(self, modelUpdateNotification):
        if not self._is_in_scope(modelUpdateNotification):
            _logger.debug("%s not in scope for %sWidgetManager",
                          str(modelUpdateNotification), self._name)
            return False
        if self._is_relevant(modelUpdateNotification):
            _logger.debug("%sWidgetManager interested in update %s",
                          self._name, str(modelUpdateNotification))
            self._dataFetcher.async_fetch(
                modelUpdateNotification[model.UPDATE_NODE_TUPLE_IDX_NODE_ID],
                modelUpdateNotification[model.UPDATE_NODE_TUPLE_IDX_NODE_TYPE],
                self._stateChangeQueue)
        return True

    def _is_in_scope(self, modelUpdateNotification):
        """returns whether the subclass handles this type of update"""
        raise NotImplementedError("subclass must implement")

    def _is_relevant(self, modelUpdateNotification):
        """may be overridden by subclass to return whether the proposed update should be
        persued further"""
        return True

    def _process_updates(self):
        """sends loaded data to the diff engine"""
        while True:
            updatedData = self._stateChangeQueue.get()
            if updatedData is None:
                break
            self._diffEngine.apply_update(updatedData)

class PackagesTreeWidgetManager(_WidgetManagerBase):
    def __init__(self):
        pass

    def apply_update(self, update):
        # handles the following types of updates:
        # (model.UpdateType, nodeType, nodeId, nodeData)
        # (StateChange.FILTER, filterMask)
        # (StateChange.SEARCH, searchString)
        updateType = update[0]
        if updateType is model.UpdateTypes.ATTRIBUTES:
            nodeType = update[1]
            nodeId = update[2]
            nodeAttributes = update[3]
            assert nodeType == nodeAttributes.nodeType
            if nodeType is model.NodeTypes.PACKAGE:
                _logger.debug("updating attributes for package node %d (%s)",
                              nodeId, nodeAttributes.label)
                self._update_package_attributes(nodeId, nodeAttributes)
            elif nodeType is model.NodeTypes.GROUP:
                _logger.debug("updating attributes for group node %d (%s)",
                              nodeId, nodeAttributes.label)
                self._update_group_attributes(nodeId, nodeAttributes)
            else:
                _logger.error("unexpected diff engine update: %s", str(updateType))
                assert False
        elif updateType is model.UpdateTypes.CHILDREN:
            nodeType = update[1]
            nodeId = update[2]
            nodeChildren = update[3]
            if nodeType is model.NodeTypes.ROOT:
                _logger.debug("updating children for root node")
                self._update_root_children(nodeChildren)
            elif nodeType is model.NodeTypes.GROUP:
                _logger.debug("updating children for group node %d", nodeId)
                self._update_group_children(nodeId, nodeChildren)
            else:
                _logger.error("unexpected diff engine update: %s", str(updateType))
                assert False
        elif updateType is StateChange.FILTER:
            filterMask = update[1]
            _logger.debug("updating filter mask to %s", filterMask)
            self._update_filter_mask(filterMask)
        elif updateType is StateChange.SEARCH:
            searchString = update[1]
            _logger.debug("updating search string to %s", searchString)
            self._update_search_string(searchString)
        else:
            _logger.error("unexpected diff engine update: %s", str(updateType))
            assert False
