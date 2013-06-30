# -*- coding: utf-8 -*-
#
# bait/util/process_monitor_test.py
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

import time
import random

from . import process_monitor, monitored_thread


def _active_thread_proc(seconds):
    dummyDict = {}
    for x in xrange(int(seconds)):
        for y in xrange(10000):
            time.sleep(0.0001)
            dummyDict[y] = random.expovariate(y+1)


def process_monitor_test():
    monitored_thread.tag_current_thread()
    st = monitored_thread.MonitoredThread(name="SleepyThread",
                                          target=time.sleep, args=(4,))
    st.start()
    at1 = monitored_thread.MonitoredThread(name="ActiveThread1",
                                          target=_active_thread_proc, args=(3,))
    at1.start()
    at2 = monitored_thread.MonitoredThread(name="ActiveThread2",
                                          target=_active_thread_proc, args=(4,))
    at2.start()
    process_monitor.set_interval_seconds(1)

    # check log to verify functionality
    time.sleep(10)

    st.join()
    at1.join()
    at2.join()
