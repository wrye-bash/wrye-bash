# -*- coding: utf-8 -*-
#
# bait/presenter/impl/widget_manager_test.py
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

from . import widget_manager, diff_engine
from ... import model, presenter


class _DummyDataFetcher:
    def __init__(self):
        self.stateChangeQueue = None
    def async_fetch(self, nodeId, updateTypeMask, stateChangeQueue):
        self.stateChangeQueue = stateChangeQueue

# TODO: use mock
class _DummyDiffEngine(diff_engine.PackagesTreeDiffEngine):
    def __init__(self):
        diff_engine.PackagesTreeDiffEngine.__init__(self, None, None, None)
    def could_use_update(self, updateType, nodeId, version):
        return True
    def set_pending_filter_mask(self, filterMask):
        pass
    def set_pending_search_string(self, searchString):
        pass
    def set_node_expansion(self, nodeId, isExpanded):
        pass
    def set_selected_nodes(self, nodeIds):
        pass
    def update_attributes(self, nodeId, nodeAttributes):
        pass
    def update_children(self, nodeId, nodeChildren):
        pass
    def update_filter(self, filterMask):
        pass
    def update_search_string(self, searchString):
        pass


def widget_manager_lifecycle_test():
    dummyDataFetcher = _DummyDataFetcher()
    wm = widget_manager._WidgetManagerBase("Dummy", dummyDataFetcher)

    # test lifecycle
    wm.start()
    try:
        try:
            wm.start()
            assert False
        except RuntimeError:
            pass
    finally:
        # 2nd shutdown is a noop
        wm.shutdown()
        wm.shutdown()


def widget_manager_base_test():
    dummyDataFetcher = _DummyDataFetcher()
    wm = widget_manager._WidgetManagerBase("Dummy", dummyDataFetcher)

    def truth(modelUpdateNotification):
        return True
    def lies(modelUpdateNotification):
        return False

    # (updateType, nodeType, nodeId, version)
    modelUpdate = (model.UpdateTypes.ATTRIBUTES,
                   model.NodeTypes.ROOT, model.ROOT_NODE_ID, 0)

    wm.start()
    try:
        try:
            wm.handle_model_update(modelUpdate)
            assert False
        except RuntimeError:
            pass

        wm._is_in_scope = truth
        assert wm.handle_model_update(modelUpdate)

        wm._is_in_scope = lies
        assert not wm.handle_model_update(modelUpdate)

        # (updateType, nodeId, nodeData)
        stateChange = (model.UpdateTypes.ATTRIBUTES, model.ROOT_NODE_ID, None)
        dummyDataFetcher.stateChangeQueue.put(stateChange)
        # wait for the widget manager to process it
        while 0 < dummyDataFetcher.stateChangeQueue.unfinished_tasks:
            time.sleep(0)

        # enqueue and immediately shut down
        for x in xrange(100):
            dummyDataFetcher.stateChangeQueue.put(stateChange)
    finally:
        wm.shutdown()

def widget_manager_packages_tree_test():
    dummyDataFetcher = _DummyDataFetcher()
    dummyDiffEngine = _DummyDiffEngine()
    wm = widget_manager.PackagesTreeWidgetManager(dummyDataFetcher, dummyDiffEngine)

    wm.start()
    try:
        wm.handle_expansion_update(1, True)
        wm.handle_filter_update(presenter.FilterIds.PACKAGES_INSTALLED)
        wm.handle_model_update((model.UpdateTypes.ATTRIBUTES,
                                model.NodeTypes.ROOT, model.ROOT_NODE_ID, 0))
        wm.handle_model_update((model.UpdateTypes.CHILDREN,
                                model.NodeTypes.ROOT, model.ROOT_NODE_ID, 0))
        wm.handle_search_update("wasssup")
        wm.handle_selection_update([2,5,7])

        dummyDataFetcher.stateChangeQueue.put(("garbage"))
        dummyDataFetcher.stateChangeQueue.put((model.UpdateTypes.ATTRIBUTES, 1, None))
        dummyDataFetcher.stateChangeQueue.put((model.UpdateTypes.CHILDREN, 0, []))
        # wait for the widget manager to process it
        while 0 < dummyDataFetcher.stateChangeQueue.unfinished_tasks:
            time.sleep(0)
    finally:
        wm.shutdown()
