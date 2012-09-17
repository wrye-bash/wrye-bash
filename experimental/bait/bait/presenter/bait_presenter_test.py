# -*- coding: utf-8 -*-
#
# bait/presenter/bait_presneter_test.py
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

from .. import presenter
from . import bait_presenter


class _DummyModel:
    def __init__(self):
        self.updateNotificationQueue = Queue.Queue()
    def start(self):
        pass
    def pause(self):
        pass
    def resume(self):
        pass
    def shutdown(self):
        self.updateNotificationQueue.put(None)
    def get_node_attributes(self, nodeId):
        return None
    def get_node_children(self, nodeId):
        return None
    def get_node_details(self, nodeId):
        return None

class _ThrowOnShutdown:
    def __init__(self, obj, throwOnShutdownInput=True, throwOnShutdown=True,
                 throwOnShutdownOutput=True):
        self._obj = obj
        self._throwOnShutdownInput = throwOnShutdownInput
        self._throwOnShutdown = throwOnShutdown
        self._throwOnShutdownOutput = throwOnShutdownOutput
    def shutdown_input(self):
        self._obj.shutdown_input()
        if self._throwOnShutdownInput: self._throw()
    def shutdown(self):
        self._obj.shutdown()
        if self._throwOnShutdown: self._throw()
    def shutdown_output(self):
        self._obj.shutdown_output()
        if self._throwOnShutdownOutput: self._throw()
    def _throw(self):
        raise RuntimeError("dummy error")


def presenter_lifecycle_test():
    viewCommandQueue = Queue.Queue()

    # normal
    p = bait_presenter.BaitPresenter(_DummyModel(), viewCommandQueue)
    p.start(presenter.DetailsTabIds.GENERAL, presenter.FilterIds.NONE)
    p.shutdown()

    # double-start, double-shutdown (failed start calls shutdown the first time)
    p = bait_presenter.BaitPresenter(_DummyModel(), viewCommandQueue)
    p.start(presenter.DetailsTabIds.GENERAL, presenter.FilterIds.NONE)
    try:
        p.start(presenter.DetailsTabIds.GENERAL, presenter.FilterIds.NONE)
        assert False
    except RuntimeError:
        pass
    p.shutdown()

    # pause-resume cycle
    p = bait_presenter.BaitPresenter(_DummyModel(), viewCommandQueue)
    p.start(presenter.DetailsTabIds.GENERAL, presenter.FilterIds.NONE)
    p.pause()
    p.resume()
    p.pause()
    p.pause()
    p.resume()
    p.resume()
    p.shutdown()

    # test shutdown errors
    for failTuple in [("_updateDispatcher", True),
                      ("_dataFetcher", True),
                      ("_packagesTreeManager", True),
                      ("_model", True),
                      ("_updateDispatcher", False)]:
        p = bait_presenter.BaitPresenter(_DummyModel(), viewCommandQueue)
        p.start(presenter.DetailsTabIds.GENERAL, presenter.FilterIds.NONE)
        # call the shutdown ourselves to make sure we don't get any leftover threads
        throwObj = _ThrowOnShutdown(getattr(p, failTuple[0]),
                                    throwOnShutdownOutput=failTuple[1])
        setattr(p, failTuple[0], throwObj)
        p.shutdown()
