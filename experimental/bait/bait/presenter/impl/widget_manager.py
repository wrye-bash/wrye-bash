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

from . import data_fetcher, diff_engine
from .. import model
from ...util import enum, monitored_thread, process_monitor


_STATE_CHANGE_TYPE_IDX = 0
_STATE_CHANGE_FILTER_MASK_IDX = 1
_STATE_CHANGE_SEARCH_STRING_IDX = 1

_logger = logging.getLogger(__name__)


class _StateChange(enum.Enum):
    __enumerables__ = ('UNKNOWN', 'FILTER', 'SEARCH')
    FILTER = None
    SEARCH = None

class _WidgetManagerBase:
    def __init__(self, name, dataFetcher):
        self._name = name
        self._dataFetcher = dataFetcher
        self._started = False
        self._isShutdown = False
        self._stateChangeQueue = Queue.Queue(maxsize=100)
        self._processingThread = monitored_thread.MonitoredThread(
            target=self._process_state_changes, name=name+"WidgetManager")

    def start(self):
        if self._started:
            raise RuntimeError("WidgetManager already started")
        _logger.debug("starting %sWidgetManager", self._name)
        self._processingThread.start()
        self._started = True
        process_monitor.register_statistics_callback(self._dump_stats)

    def shutdown(self):
        """assumes that the data fetcher has been shut down by this point and that nothing
        else can be enqueued into the stateChangeQueue"""
        if self._started:
            process_monitor.unregister_statistics_callback(self._dump_stats)
            _logger.debug("shutting %sWidgetManager down", self._name)
            self._isShutdown = True
            self._stateChangeQueue.put(None)
            self._processingThread.join()
            self._started = False

    def handle_model_update(self, modelUpdateNotification):
        if not self._is_in_scope(modelUpdateNotification):
            _logger.debug("%s not in scope for %sWidgetManager",
                          modelUpdateNotification, self._name)
            return False
        if self._want_update(modelUpdateNotification):
            _logger.debug("%sWidgetManager interested in update %s",
                          self._name, modelUpdateNotification)
            self._dataFetcher.async_fetch(
                modelUpdateNotification[model.UPDATE_NODE_TUPLE_IDX_NODE_ID],
                modelUpdateNotification[model.UPDATE_TUPLE_IDX_TYPE],
                self._stateChangeQueue)
        return True

    def _dump_stats(self, logFn):
        logFn("%s stateChangeQueue length: %d",
              self.__class__.__name__, self._stateChangeQueue.qsize())

    def _is_in_scope(self, modelUpdateNotification):
        """returns whether the subclass handles this type of update"""
        _logger.error("_is_in_scope not overridden by subclass as required")
        raise NotImplementedError("subclass must implement")

    def _want_update(self, modelUpdateNotification):
        """may be overridden by subclass to return whether the proposed update should be
        persued further.  the default result is True."""
        return True

    def _process_state_changes(self):
        """applies state changes to data objects"""
        while True:
            stateChange = self._stateChangeQueue.get()
            if stateChange is None:
                break
            if self._isShutdown:
                self._stateChangeQueue.task_done()
                continue
            try:
                self._process_state_change(stateChange)
            except:
                _logger.warn("caught exception processing state changes:", exc_info=True)
            self._stateChangeQueue.task_done()

    def _process_state_change(self, stateChange):
        _logger.error("_process_state_change not overridden by subclass as required")
        raise NotImplementedError("subclass must implement")


class PackagesTreeWidgetManager(_WidgetManagerBase):
    def __init__(self, dataFetcher, diffEngine):
        _WidgetManagerBase.__init__(self, "PackagesTree", dataFetcher)
        self._diffEngine = diffEngine
        self._feedbackThread = monitored_thread.MonitoredThread(
            target=self._handle_pending_load_requests, name="PackagesTreeFeedback")
        # TODO: make this thread non-daemonic so we don't get errors on interpreter
        # shutdown
        self._feedbackThread.setDaemon(True)

    # override
    def start(self):
        _WidgetManagerBase.start(self)
        self._feedbackThread.start()

    def handle_filter_update(self, filterMask):
        _logger.debug("setting pending filterMask and enqueuing state change: %s",
                      filterMask)
        self._diffEngine.set_pending_filter_mask(filterMask)
        self._stateChangeQueue.put((_StateChange.FILTER, filterMask))

    def handle_search_update(self, searchString):
        _logger.debug("setting pending search string and enqueuing state change: '%s'",
                      searchString)
        self._diffEngine.set_pending_search_string(searchString)
        self._stateChangeQueue.put((_StateChange.SEARCH, searchString))

    def handle_expansion_update(self, nodeId, isExpanded):
        _logger.debug("notifying diff engine that node %d now has expansion state: %s",
                      nodeId, isExpanded)
        self._diffEngine.set_node_expansion(nodeId, isExpanded)

    def handle_selection_update(self, nodeIds):
        _logger.debug("notifying diff engine the following nodes are now selected: %s",
                      nodeIds)
        self._diffEngine.set_selected_nodes(nodeIds)

    # override
    def _dump_stats(self, logFn):
        _WidgetManagerBase._dump_stats(self, logFn)
        logFn("%s loadRequestQueue length: %d",
              self.__class__.__name__, self._diffEngine.loadRequestQueue.qsize())

    # override
    def _is_in_scope(self, modelUpdateNotification):
        return self._diffEngine.is_in_scope(
            modelUpdateNotification[model.UPDATE_TUPLE_IDX_TYPE],
            modelUpdateNotification[model.UPDATE_NODE_TUPLE_IDX_NODE_TYPE])

    # override
    def _want_update(self, modelUpdateNotification):
        return self._diffEngine.could_use_update(
            modelUpdateNotification[model.UPDATE_TUPLE_IDX_TYPE],
            modelUpdateNotification[model.UPDATE_NODE_TUPLE_IDX_NODE_ID],
            modelUpdateNotification[model.UPDATE_NODE_TUPLE_IDX_VERSION])

    def _handle_pending_load_requests(self):
        loadRequestQueue = self._diffEngine.loadRequestQueue
        stateChangeQueue = self._stateChangeQueue
        while True:
            loadRequest = loadRequestQueue.get()
            self._dataFetcher.async_fetch(
                loadRequest[diff_engine.NODE_ID_IDX],
                loadRequest[diff_engine.UPDATE_TYPE_MASK_IDX], stateChangeQueue)
            loadRequestQueue.task_done()

    # override
    def _process_state_change(self, stateChange):
        stateChangeType = stateChange[_STATE_CHANGE_TYPE_IDX]
        if stateChangeType is model.UpdateTypes.ATTRIBUTES:
            nodeId = stateChange[data_fetcher.NODE_ID_IDX]
            _logger.debug("updating attributes for node %d", nodeId)
            self._diffEngine.update_attributes(nodeId, stateChange[data_fetcher.DATA_IDX])
        elif stateChangeType is model.UpdateTypes.CHILDREN:
            nodeId = stateChange[data_fetcher.NODE_ID_IDX]
            _logger.debug("updating children for node %d", nodeId)
            self._diffEngine.update_children(nodeId, stateChange[data_fetcher.DATA_IDX])
        elif stateChangeType is _StateChange.FILTER:
            filterMask = stateChange[_STATE_CHANGE_FILTER_MASK_IDX]
            _logger.debug("updating filter mask to %s", filterMask)
            self._diffEngine.update_filter(filterMask)
        elif stateChangeType is _StateChange.SEARCH:
            searchString = stateChange[_STATE_CHANGE_SEARCH_STRING_IDX]
            _logger.debug("updating search string to '%s'", searchString)
            self._diffEngine.update_search_string(searchString)
        else:
            raise RuntimeError("unexpected state change: %s", stateChange)


class PackageContentsTreeWidgetManager(_WidgetManagerBase):
    def __init__(self):
        self.targetPackage = None
        self.isMultiple = False
    def set_target_package(self, nodeId, isMultiple):
        self.targetPackage = nodeId
        self.isMultiple = isMultiple


class GeneralTabWidgetManager(_WidgetManagerBase):
    def __init__(self):
        self.targetPackage = None
        self.isMultiple = False
    def set_target_package(self, nodeId, isMultiple):
        self.targetPackage = nodeId
        self.isMultiple = isMultiple
