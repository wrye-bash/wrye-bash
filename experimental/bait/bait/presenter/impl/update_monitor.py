# -*- coding: utf-8 -*-
#
# bait/presenter/impl/update_monitor.py
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


_logger = logging.getLogger(__name__)


class UpdateMonitor(threading.Thread):
    def __init__(self, updateQueue):
        threading.Thread.__init__(self, name="PresenterUpdate")
        self._updateQueue = updateQueue
        self._handlers = {}
        self._handlers[model.UPDATE_TYPE_ATTRIBUTES] = self._update_attributes
        self._handlers[model.UPDATE_TYPE_CHILDREN] = self._update_children
        self._handlers[model.UPDATE_TYPE_DETAILS] = self._update_details
        self._handlers[model.UPDATE_TYPE_STATUS] = self._update_status
        self._handlers[model.UPDATE_TYPE_ERROR] = self._update_error

    def run(self):
        _logger.debug("presenter update monitor thread starting")
        # cache constant variables to avoid repetitive lookups
        updateQueue = self._updateQueue
        handlerMap = self._handlers

        while True:
            updateInfo = updateQueue.get()
            if updateInfo is None:
                _logger.debug(
                    "received sentinel value; presenter update monitor thread exiting")
                break
            _logger.debug("received %s update" % updateInfo.__class__)
            handler = handlerMap.get(updateInfo.typeId)
            if handler is None:
                _logger.warn("unhandled %s update: %s",
                             updateInfo.__class__, dir(updateInfo))
                continue
            handler(updateInfo)

    def _update_attributes(self, attributeUpdateNotification):
        _logger.debug("attributes for node %d have been updated",
                      attributeUpdateNotification.nodeId)
        # TODO: check visibleNodeSet to see if we care about this

    def _update_children(self, childrenUpdateNotification):
        _logger.debug("children for node %d have been updated",
                      childrenUpdateNotification.nodeId)
        # TODO: check visibleNodeSet to see if we care about this

    def _update_details(self, detailsUpdateNotification):
        _logger.debug("details for node %d have been updated",
                      detailsUpdateNotification.nodeId)
        # TODO: check visibleNodeSet to see if we care about this

    def _update_status(self, statusUpdateNotification):
        _logger.debug("model status has been updated")
        # TODO: ascertain model status and send view commands

    def _update_error(self, errorUpdateNotification):
        _logger.debug("model encountered an error")
        # TODO: send view commands
