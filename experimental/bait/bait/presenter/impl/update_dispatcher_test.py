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
import time

from . import update_dispatcher
from ... import model


class _DummyWidgetManager:
    def __init__(self, name, nodeType):
        self._name = name
        self._nodeType = nodeType
    def handle_model_update(self, modelUpdateNotification):
        return modelUpdateNotification[model.UPDATE_NODE_TUPLE_IDX_NODE_TYPE] is \
               self._nodeType


def _assert_view_command(viewCommandQueue, errorCode, resourceName):
    assert not viewCommandQueue.empty()
    displayErrorUpdate = viewCommandQueue.get()
    assert errorCode == displayErrorUpdate.errorCode
    assert resourceName == displayErrorUpdate.resourceName


def update_dispatcher_test():
    modelUpdateQueue = Queue.Queue()
    viewCommandQueue = Queue.Queue()

    dwm1 = _DummyWidgetManager("1", model.NodeTypes.ROOT)
    dwm2 = _DummyWidgetManager("2", model.NodeTypes.PACKAGE)

    widgetManagers = [dwm1, dwm2]
    ud = update_dispatcher.UpdateDispatcher(
        modelUpdateQueue, viewCommandQueue, widgetManagers)

    ud.start()
    try:
        try:
            ud.start()
            assert False
        except RuntimeError as e:
            pass

        # handled by dwm1
        modelUpdateQueue.put((model.UpdateTypes.ATTRIBUTES, model.NodeTypes.ROOT, 100, 1))

        # handled by dwm2
        modelUpdateQueue.put((model.UpdateTypes.CHILDREN, model.NodeTypes.PACKAGE, 110, 1))

        # not handled by any DummyWidgetManager
        modelUpdateQueue.put((model.UpdateTypes.DETAILS, model.NodeTypes.FILE, 120, 1))

        # sent to the view command queue (can't check until the ud processes it, though)
        modelUpdateQueue.put(
            (model.UpdateTypes.ERROR, model.Errors.DISK_FULL, "filename.esp"))

        # should be detected as garbage
        modelUpdateQueue.put((0, "garbage"))
        modelUpdateQueue.put(())

        # wait for updates to be processed
        while 0 < modelUpdateQueue.unfinished_tasks:
            time.sleep(0)
        _assert_view_command(viewCommandQueue, model.Errors.DISK_FULL, "filename.esp")

    finally:
        # shut down UpdateDispatcher output
        ud.shutdown_output()

        # should be skipped
        modelUpdateQueue.put((model.UpdateTypes.ATTRIBUTES, model.NodeTypes.ROOT, 100, 1))

        # shut down UpdateDispatcher input
        modelUpdateQueue.put(None)
        ud.shutdown_input()

    assert modelUpdateQueue.empty()
    assert viewCommandQueue.empty()
