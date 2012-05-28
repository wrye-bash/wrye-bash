# -*- coding: utf-8 -*-
#
# bait/util/proxy_tools.py
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
import types

from . import monitored_thread


_logger = logging.getLogger(__name__)


# structure based on code found at:
#   http://code.activestate.com/recipes/366254-generic-proxy-object-with-beforeafter-method-hooks/
class _ProxyMethodWrapper:
    def __init__(self, fnName, fn, callQueue):
        self._fnName = fnName
        self._fn = fn
        self._callQueue = callQueue

    def __call__(self, *args, **kwargs):
        self._callQueue.put((self._fnName, self._fn, args, kwargs))


class AsyncProxy:
    """Wraps an object so that calls to the object's methods are marshalled through a
    queue and executed in a daemon thread.  Does not support methods with return
    values."""
    def __init__(self, name, obj):
        self._obj = obj
        self._callQueue = Queue.Queue()
        workerThread = monitored_thread.MonitoredThread(name=name+"AsyncProxy",
                                                        target=self._run)
        workerThread.setDaemon(True)
        workerThread.start()

    def __getattr__(self, attrName):
        """wraps methods with proxy objects"""
        if attrName.startswith('_'):
            raise NotImplementedError("cannot get non-public attributes")
        else:
            attr = getattr(self._obj, attrName)
            if type(attr) is types.MethodType:
                return _ProxyMethodWrapper(attrName, attr, self._callQueue)
            else:
                return attr

    def _run(self):
        callQueue = self._callQueue
        while True:
            try:
                fnName, fn, args, kwargs = callQueue.get()
                fn(*args, **kwargs)
            except:
                _logger.warn("caught exception in async call to %s.%s",
                             self._name, fnName, exc_info=1)
