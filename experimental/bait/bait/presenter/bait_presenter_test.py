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


def presenter_lifecycle_test():
    viewCommandQueue = Queue.Queue()
    p = bait_presenter.BaitPresenter(_DummyModel(), viewCommandQueue)

    p.start(presenter.DetailsTabIds.GENERAL, presenter.FilterIds.NONE)
    p.shutdown()
