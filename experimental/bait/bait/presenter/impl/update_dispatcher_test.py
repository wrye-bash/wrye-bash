# -*- coding: utf-8 -*-
#
# bait/presenter/impl/update_dispatcher_test.py
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
import time

from . import update_dispatcher
from ... import model


_logger = logging.getLogger(__name__)


class _DummyWidgetManager:
    def __init__(self, name, nodeType):
        self._name = name
        self._nodeType = nodeType
    def handle(self, updateType, nodeType, nodeId, version):
        _logger.debug("DummyWidgetManager%s received update: %d %d %d %d",
                      self._name, updateType, nodeType, nodeId, version)
        if nodeType is self._nodeType:
            _logger.debug("DummyWidgetManager%s handling update", self._name)
            return True
        else:
            _logger.debug("DummyWidgetManager%s not handling update", self._name)
            return False


def _view_command_queue_reader(viewCommandQueue):
    while True:
        viewCommand = viewCommandQueue.get()
        if viewCommand is None:
            _logger.debug(
                "received sentinel value; view command reader thread exiting")
            break
        _logger.debug("received view command: %s", str(viewCommand))

def update_dispatcher_test():
    modelUpdateQueue = Queue.Queue()
    viewCommandQueue = Queue.Queue()
    widgetManagers = [_DummyWidgetManager("1", model.NODE_TYPE_ROOT),
                      _DummyWidgetManager("2", model.NODE_TYPE_PACKAGE)]
    viewCommandQueueReaderThread = threading.Thread(name="ViewCommandReader",
                                                    target=_view_command_queue_reader,
                                                    args=(viewCommandQueue,))
    viewCommandQueueReaderThread.start()
    ud = update_dispatcher.UpdateDispatcher(modelUpdateQueue, viewCommandQueue,
                                            widgetManagers)

    _logger.debug("starting UpdateDispatcher")
    ud.start()
    try:
        _logger.debug("starting UpdateDispatcher again; should throw")
        ud.start()
        _logger.warn("should not get here")
    except RuntimeError as e:
        _logger.debug("correctly threw: %s", e)

    update = (model.UPDATE_TYPE_ATTRIBUTES, model.NODE_TYPE_ROOT, 100, 1)
    _logger.debug("should be handled by DummyWidgetManager1: %s", str(update))
    modelUpdateQueue.put(update)

    update = (model.UPDATE_TYPE_CHILDREN, model.NODE_TYPE_PACKAGE, 110, 1)
    _logger.debug("should be handled by DummyWidgetManager2: %s", str(update))
    modelUpdateQueue.put(update)

    update = (model.UPDATE_TYPE_DETAILS, model.NODE_TYPE_FILE, 120, 1)
    _logger.debug("should not be handled by any DummyWidgetManager")
    modelUpdateQueue.put(update)

    update = (model.UPDATE_TYPE_ERROR, model.ERROR_DISK_FULL, "filename.esp")
    _logger.debug("should be sent to the view command queue: %s", str(update))
    modelUpdateQueue.put(update)

    update = (0, "garbage")
    _logger.debug("should be detected as garbage: %s", str(update))
    modelUpdateQueue.put(update)

    _logger.debug("waiting for updates to be processed")
    while not modelUpdateQueue.empty():
        time.sleep(0)

    _logger.debug("shutting down UpdateDispatcher output")
    ud.shutdown_output()

    update = (model.UPDATE_TYPE_ATTRIBUTES, model.NODE_TYPE_ROOT, 100, 1)
    _logger.debug("should be skipped: %s", str(update))
    modelUpdateQueue.put(update)

    _logger.debug("shutting down UpdateDispatcher input")
    modelUpdateQueue.put(None)
    ud.shutdown_input()

    _logger.debug("shutting down viewCommand reader thread")
    viewCommandQueue.put(None)
    viewCommandQueueReaderThread.join()