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

from cStringIO import StringIO
import logging
import os, os.path
import sys
import threading
import traceback

from . import monitored_thread


_logger = logging.getLogger(__name__)
_statsLogger = logging.getLogger("STATISTICS")

_isPsutilLoaded = False
try:
    # import inside of a try block since psutil may not be installed
    import psutil
    _isPsutilLoaded = True
except ImportError:
    pass

# TODO: will this still match when we're running from a py2exe standalone executable?
_includeStackStr = os.path.sep + 'bait' + os.path.sep
_excludeStackStr = 'monitored_thread.py'
_bytesPerMegabyte = 1024*1024


class _ProcessMonitor:
    def __init__(self):
        self._intervalSecs = 60
        self._dumpStatsCallbacksLock = threading.Lock()
        self._dumpStatsCallbacks = set()
        if not _isPsutilLoaded:
            _logger.info("unable to load psutil; not starting process monitor")
        else:
            # ensure our own monitoring thread is included in the report
            monitorThread = monitored_thread.MonitoredThread(name="ProcessMonitor",
                                                             target=self._run)
            monitorThread.setDaemon(True)
            monitorThread.start()

    def set_interval_seconds(self, seconds):
        self._intervalSecs = seconds

    def register_statistics_callback(self, cb):
        with self._dumpStatsCallbacksLock:
            self._dumpStatsCallbacks.add(cb)

    def unregister_statistics_callback(self, cb):
        with self._dumpStatsCallbacksLock:
            self._dumpStatsCallbacks.discard(cb)

    def _get_host_time(self):
        hostTimes = psutil.cpu_times()
        return hostTimes.user + hostTimes.system

    def _get_process_time(self, curProcess):
        processTimes = curProcess.get_cpu_times()
        return processTimes.user + processTimes.system

    def _dump_stats(self, curProcess, prevHostTime, prevProcessTime, prevThreadTimes):
        # factor this out into a function to ensure we don't accidentally keep any frame
        # references around
        hostCpuPercent = psutil.cpu_percent(self._intervalSecs)

        cumulativeHostTime = self._get_host_time()
        recentHostTime = cumulativeHostTime - prevHostTime

        cumulativeProcessTime = self._get_process_time(curProcess)
        recentProcessTime = cumulativeProcessTime - prevProcessTime

        processCpuPercent = recentHostTime <= 0 and 0 or \
                          (recentProcessTime*100)/recentHostTime

        # record memory usage
        physUsed = psutil.used_phymem()
        physAvail = psutil.avail_phymem()
        physBufs = psutil.cached_phymem() + psutil.phymem_buffers()
        _statsLogger.info("system memory: total: %dM; used: %dM; avail: %dM",
                          (physUsed + physAvail)/_bytesPerMegabyte,
                          (physUsed - physBufs)/_bytesPerMegabyte,
                          (physAvail + physBufs)/_bytesPerMegabyte)
        _statsLogger.info("system swap: total: %dM; used: %dM; avail: %dM",
                          psutil.total_virtmem()/_bytesPerMegabyte,
                          psutil.used_virtmem()/_bytesPerMegabyte,
                          psutil.avail_virtmem()/_bytesPerMegabyte)
        procMem = curProcess.get_memory_info()
        _statsLogger.info("process memory: RSS: %dM (%.2f%%); VMS: %dM",
                          procMem[0]/_bytesPerMegabyte,
                          curProcess.get_memory_percent(),
                          procMem[1]/_bytesPerMegabyte)

        # associate thread info
        frames = sys._current_frames()
        tidToThreadInfo = {hasattr(t, "tid") and t.tid or t.ident:\
                           (t.name,frames.get(t.ident)) \
                           for t in threading.enumerate()}

        # calculate percentage of times each thread is contributing
        cumulativeThreadTimes = {}
        threadContributions = []
        for threadTimes in curProcess.get_threads():
            threadTime = threadTimes.user_time + threadTimes.system_time
            cumulativeThreadTimes[threadTimes.id] = threadTime
            recentThreadTime = threadTime - prevThreadTimes.get(threadTimes.id, 0)
            if 0 >= recentProcessTime or 0 >= recentThreadTime:
                contribution = 0
            else:
                contribution = int(recentThreadTime*100/recentProcessTime)
            threadName, stack = tidToThreadInfo.get(threadTimes.id,
                                                    (threadTimes.id, None))
            threadContributions.append((contribution, threadName, stack))

        # sort the threads by contribution
        sortedThreadContributions = sorted(threadContributions, reverse=True)
        isFirst = True
        threadCpuStr = StringIO()
        for threadInfo in sortedThreadContributions:
            if isFirst:
                threadCpuStr.write("[")
                isFirst = False
            else:
                threadCpuStr.write("; ")
            threadCpuStr.write(str(threadInfo[1]))
            threadCpuStr.write(": %d%%" % threadInfo[0])
        threadCpuStr.write("]")

        _statsLogger.info("CPU utilization: host: %d%% -> proc: %d%% -> threads: %s",
                     hostCpuPercent, processCpuPercent, threadCpuStr.getvalue())

        _statsLogger.info("thread stacks:")
        for threadInfo in sortedThreadContributions:
            threadName = threadInfo[1]
            if threadName == threading.currentThread().getName():
                # no need to clutter the log with stack traces from this thread
                continue
            _statsLogger.info("  %s:", threadName)
            matched = False
            stack = threadInfo[2]
            if stack is None:
                _statsLogger.info("    stack trace not available")
                continue
            for filename, lineno, name, line in traceback.extract_stack(stack):
                if _includeStackStr in filename and \
                   (matched or _excludeStackStr not in filename):
                    matched = True
                    _statsLogger.info("    %s:%d(%s): %s", os.path.basename(filename),
                                 lineno, name, line.strip())
            if not matched:
                # system thread -- just dump the whole stack trace
                for filename, lineno, name, line in \
                    traceback.extract_stack(stack):
                    _statsLogger.info("    %s:%d(%s): %s", os.path.basename(filename),
                                 lineno, name, line.strip())

        with self._dumpStatsCallbacksLock:
            try:
                for cb in self._dumpStatsCallbacks:
                    cb(_statsLogger.info)
            except:
                _logger.warn("caught exception from stats callback:", exc_info=True)

        return cumulativeHostTime, cumulativeProcessTime, cumulativeThreadTimes

    def _run(self):
        try:
            curProcess = psutil.Process(os.getpid())

            # ignore resource usage burst from program startup
            curProcess.get_cpu_percent(5)

            # initialize times
            prevHostTime = self._get_host_time()
            prevProcessTime = self._get_process_time(curProcess)
            prevThreadTimes = {times.id:times.user_time+times.system_time
                               for times in curProcess.get_threads()}

            # this is a daemon thread -- we run until program termination
            while True:
                prevHostTime, prevProcessTime, prevThreadTimes = self._dump_stats(
                    curProcess, prevHostTime, prevProcessTime, prevThreadTimes)

        except:
            _logger.warn("process monitoring thread exiting with exception:", exc_info=1)
            _statsLogger.warn("process monitoring thread exiting with exception:",
                              exc_info=1)


# singleton instance
_processMonitor = _ProcessMonitor()

def set_interval_seconds(seconds):
    """will take effect on next iteration"""
    _processMonitor.set_interval_seconds(seconds)

# TODO:
# presenter cache size?
# view latency stats?
# model dataset size?
# operation counters?
def register_statistics_callback(cb):
    """callbacks are called with a single argument: the log function of the target logger.
    Call it to log statistics.  For example:
      def _dump_stats(self, logFn):
          logFn("Fooclass queue length: %s", self._internalQueue.qsize())
    To avoid a deadlock, do not attempt to register or unregister callbacks from within
    the callback."""
    _processMonitor.register_statistics_callback(cb)

def unregister_statistics_callback(cb):
    _processMonitor.unregister_statistics_callback(cb)

#def register_low_memory_callback(cb):
#    pass "pressure" rating so callbacks know how much to free?
