# -*- coding: utf-8 -*-
#
# bait/util/monitored_thread.py
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

import ctypes
import logging
import os
import sys
import threading


_logger = logging.getLogger(__name__)

_nativeBait = None
try:
    # do all this in a try block -- if it fails we can fall back to just not monitoring
    if sys.platform.lower().startswith("linux"):
        import struct;
        _bitSize = 8 * struct.calcsize("P")
        _nativeBaitPath = os.path.join("native", "bait%d.so"%_bitSize)
        if not os.path.exists(_nativeBaitPath):
            _logger.info("native library not found: '%s' (manual build may be required)",
                         _nativeBaitPath)
        else:
            _logger.debug("loading: '%s'", _nativeBaitPath)
            _nativeBaitTmp = ctypes.CDLL(_nativeBaitPath)
            _logger.debug("successfully loaded native library")
            if hasattr(_nativeBaitTmp, "get_thread_id"):
                _nativeBait = _nativeBaitTmp
            else:
                _logger.warn("cannot call get_thread_id function in %s", _nativeBaitPath)
except:
    _logger.info("could not load native library:", exc_info=True)


def _tag_thread(thread):
    if _nativeBait is not None:
        thread.tid = _nativeBait.get_thread_id()
    else:
        thread.tid = thread.ident

def tag_current_thread():
    _tag_thread(threading.current_thread())


class MonitoredThread(threading.Thread):
    def __init__(self, group=None, target=None, name=None,
                 args=(), kwargs=None, verbose=None):
        threading.Thread.__init__(self, group, self.__run, name, args, kwargs, verbose)
        self.__target = target
        self.tid = None

    def __run(self, *args, **kwargs):
        _tag_thread(self)
        self.__target(*args, **kwargs)
