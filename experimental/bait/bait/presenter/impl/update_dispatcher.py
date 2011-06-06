# -*- coding: utf-8 -*-
#
# bait/presenter/impl/update_dispatcher.py
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
import threading

from ... import model
from .. import view_commands


_logger = logging.getLogger(__name__)


class UpdateDispatcher:
    def __init__(self, modelUpdateQueue, viewCommandQueue, widgetManagers):
        self._modelUpdateQueue = modelUpdateQueue
        self._viewCommandQueue = viewCommandQueue
        self._widgetManagers = widgetManagers
        self._monitorThread = None
        self._shutdownLock = threading.Lock()
        self._shutdown = False

    def start(self):
        if self._monitorThread is not None:
            raise RuntimeError("UpdateDispatcher instance already started")
        self._monitorThread = threading.Thread(name="UpdateDispatcher", target=self._run)
        self._monitorThread.start()

    def shutdown_output(self):
        # acquire lock to ensure that we will never call a widget manager after this
        # function completes
        with self._shutdownLock:
            self._shutdown = True;

    def shutdown_input(self):
        # wait for None to be sent from the model
        self._monitorThread.join()
        self._monitorThread = None

    def _run(self):
        _logger.debug("model update dispatcher thread starting")
        while True:
            updateInfo = self._modelUpdateQueue.get()
            # quit on None
            if updateInfo is None:
                _logger.debug(
                    "received sentinel value; update dispatcher thread exiting")
                break
            with self._shutdownLock:
                # if we are shutting down, eat all updates
                if self._shutdown:
                    continue
                try:
                    _logger.debug("received update: %s", str(updateInfo))
                    updateType = updateInfo[model.UPDATE_TUPLE_IDX_TYPE]
                    if updateType is model.UPDATE_TYPE_ERROR:
                        # propagate errors to view
                        self._viewCommandQueue.put(
                            view_commands.DisplayError(
                                updateInfo[model.UPDATE_ERROR_TUPLE_IDX_CODE],
                                updateInfo[model.UPDATE_ERROR_TUPLE_IDX_RESOURCE_NAME]))
                    else:
                        handled = False
                        # send to each widget manager in turn until one handles it
                        # TODO: would it be more efficient to use a map?
                        for widgetManager in self._widgetManagers:
                            if widgetManager.handle(updateType,
                                        updateInfo[model.UPDATE_NODE_TUPLE_IDX_NODE_TYPE],
                                        updateInfo[model.UPDATE_NODE_TUPLE_IDX_NODE_ID],
                                        updateInfo[model.UPDATE_NODE_TUPLE_IDX_VERSION]):
                                handled = True
                                break
                        if not handled:
                            _logger.warn("unhandled update: %s", str(updateInfo))
                except Exception as e:
                    _logger.warn("invalid model update: %s: %s", str(updateInfo), e)