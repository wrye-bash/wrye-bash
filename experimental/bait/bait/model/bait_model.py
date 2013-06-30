# -*- coding: utf-8 -*-
#
# bait/model/bait_model.py
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


_logger = logging.getLogger(__name__)


class BaitModel:
    def __init__(self, updateNotificationQueue, stateManager=None, ioProxy=None):
        self.updateNotificationQueue = updateNotificationQueue

    def start(self):
        _logger.debug("model starting")

    def pause(self):
        _logger.debug("model pausing")

    def resume(self):
        _logger.debug("model resuming")

    def shutdown(self):
        _logger.debug("model shutting down")
        self.updateNotificationQueue.put(None)

    def get_node_attributes(self, nodeId):
        _logger.debug("retrieving attributes for node %d", nodeId)
        return None

    def get_node_children(self, nodeId):
        _logger.debug("retrieving children for node %d", nodeId)
        return None

    def get_node_details(self, nodeId):
        _logger.debug("retrieving details for node %d", nodeId)
        return None

    # TODO: functions to implement menu commands (e.g. "anneal")
