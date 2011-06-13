# -*- coding: utf-8 -*-
#
# bait/test/mock_model.py
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

from .. import model
from ..model import bait_model, node_attributes, node_children, node_details
from mock_presenter_data import *


_logger = logging.getLogger(__name__)


class MockModel(bait_model.BaitModel):
    def __init__(self):
        bait_model.BaitModel.__init__(self, Queue.Queue())

    def start(self):
        _logger.debug("mock model starting")

    def pause(self):
        _logger.debug("mock model pausing")

    def resume(self):
        _logger.debug("mock model resuming")

    def shutdown(self):
        _logger.debug("mock model shutting down")
        self.updateQueue.put(None)

    def get_status(self):
        # TODO: if there are writes going on, return IO
        # TODO: else if there are dirty files, return DIRTY
        # TODO: else if we are loading data, return LOADING
        # TODO: else return OK
        pass

    def get_loaded_percent(self):
        """returns completion percentage of initial data load"""
        return 0

    def _load_data_async(self):
        for x in xrange(5):
            time.sleep(1)
