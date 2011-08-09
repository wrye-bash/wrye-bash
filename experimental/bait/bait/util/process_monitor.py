# -*- coding: utf-8 -*-
#
# bait/util/process_monitor.py
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
import operator
import os
import threading

from . import monitored_thread


_logger = logging.getLogger(__name__)

_isPsutilLoaded = False
try:
    # import inside of a try block since psutil may not be installed
    import psutil
    _isPsutilLoaded = True
except ImportError:
    pass


class ProcessMonitor:
    def __init__(self, intervalSecs):
        # start a daemon thread that periodically outputs process statistics
        # process memory usage (cur/peak/max before crash)
        # CPU utilization of each thread
        # presenter cache size?
        # view latency stats?
        # model dataset size?
        # operation counters?
        self._intervalSecs = intervalSecs
        if not _isPsutilLoaded:
            _logger.info("unable to load psutil; not starting process monitor")
        else:
            # ensure our own monitoring thread is included in the report
            monitorThread = monitored_thread.MonitoredThread(name="Monitor",
                                                             target=self._run)
            monitorThread.setDaemon(True)
            monitorThread.start()

    def _get_process_time(self, curProcess):
        processTimes = curProcess.get_cpu_times()
        return processTimes.user + processTimes.system

    def _run(self):
        try:
            intervalSecs = self._intervalSecs
            curProcess = psutil.Process(os.getpid())

            # initialize times
            prevProcessTime = self._get_process_time(curProcess)
            prevThreadTimes = {times.id:times.user_time+times.system_time
                               for times in curProcess.get_threads()}

            while True:
                processCpuPercent = curProcess.get_cpu_percent(intervalSecs)

                # for mapping thread IDs to python thread names
                threadNames = {hasattr(t, "tid") and t.tid or t.ident:t.name \
                               for t in threading.enumerate()}

                cumulativeProcessTime = self._get_process_time(curProcess)
                recentProcessTime = cumulativeProcessTime - prevProcessTime
                prevProcessTime = cumulativeProcessTime

                # calculate percentage of times each thread is contributing
                cumulativeThreadTimes = {}
                threadContributions = {}
                for threadTimes in curProcess.get_threads():
                    threadTime = threadTimes.user_time + threadTimes.system_time
                    cumulativeThreadTimes[threadTimes.id] = threadTime
                    recentThreadTime = threadTime - prevThreadTimes.get(threadTimes.id, 0)
                    if 0 >= recentProcessTime or 0 >= recentThreadTime:
                        contribution = 0
                    else:
                        contribution = int(recentThreadTime*100/recentProcessTime)
                    threadName = threadNames.get(threadTimes.id, threadTimes.id)
                    threadContributions[threadName] = contribution
                prevThreadTimes = cumulativeThreadTimes

                # sort the threads by contribution
                sortedThreadContributions = sorted(threadContributions.iteritems(),
                                                   key=operator.itemgetter(1),
                                                   reverse=True)

                _logger.info("CPU utilization: %d%%; threadContributions: %s",
                             processCpuPercent, sortedThreadContributions)
        except:
            _logger.warn("process monitoring thread exiting with exception:", exc_info=1)
