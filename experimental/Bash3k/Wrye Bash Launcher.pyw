# -*- coding: utf-8 -*-

"""This module starts the Wrye Bash application (both GUI and backend processes)."""

import multiprocessing

from bash.messages import bashim_process_id, basher_process_id

class _BashProcess(multiprocessing.Process):
    """Base class for Bash's processes"""
    def __init__(self, process_id, to_parent_queue, to_gui_queue, to_bashim_queue):
        multiprocessing.Process.__init__(self)
        self.process_id = process_id
        self.to_parent_queue = to_parent_queue
        self.to_bashim_queue = to_bashim_queue
        self.to_gui_queue = to_gui_queue

    def _BashProcess__run(self, func, *args):
##        print(self.process_id, " starting")
        import bash.messages
        try:
            closed_reason = func(*args) #Blocking
        except KeyboardInterrupt:
            print("Keyboard interrupted")
            closed_reason = bash.messages.SYSTEM_ERROR
        except Exception as e:
            print("Exception interrupted")
            import traceback
            closed_reason = bash.messages.SYSTEM_ERROR
            traceback.print_exc()
            print(e)
        finally:
            if closed_reason == bash.messages.SYSTEM_REQUEST:
                return
            if closed_reason == bash.messages.SYSTEM_ERROR:
                if self.is_parent_alive():
                    self.to_parent_queue.put((bash.messages.SHUTDOWN, (bash.messages.SYSTEM_REQUEST,), None))
                else:
                    self.to_bashim_queue.put((bash.messages.CLOSE_PROCESS, (bash.messages.SYSTEM_REQUEST,), None))
                raise EnvironmentError('Unable to communicate with the parent process. It may have crashed or been terminated by the user.')

##        print(self.process_id, "ending")

    def is_parent_alive(self):
        """Base class for Bash's processes"""
        import bash.messages
        self.to_parent_queue.put((bash.messages.IS_ALIVE_REQ, (self.process_id,), None))
        size = self.to_parent_queue.qsize()
        from time import time, sleep
        start_time = time()
        time_out = 5.0
        parent_alive = False
        message_was_found = False

        from queue import Empty as QueueEmpty
        while time() - start_time < time_out:
            if size > self.to_parent_queue.qsize():
                return True
            size = self.to_parent_queue.qsize()

            parent_queue = []
            while True:
                try:
                    parent_queue.append(self.to_parent_queue.get_nowait()) #Non-blocking
                except QueueEmpty:
                    break
            message_found = False
            for message in parent_queue:
                self.to_parent_queue.put(message)
                if message == (bash.messages.IS_ALIVE_REQ, (self.process_id,), None):
                    message_found = True
                    message_was_found = True

            if message_was_found and not message_found:
                return True
            sleep(0.1)
        return parent_alive

class _BashIntermediaryProcess(_BashProcess):
    """bashim process: Starts Intermediary layer"""

    def run(self):
        import bash.bashim
        import locale
        locale.setlocale(locale.LC_ALL, '')
        import os
        cwd = os.getcwd()
        del os
        app = bash.bashim.BashIntermediary(cwd, self.to_parent_queue, self.to_gui_queue, self.to_bashim_queue)
        self._BashProcess__run(app.mainLoop)

class _BashGUIProcess(_BashProcess):
    """basher process: Starts GUI"""
    def run(self):
        import bash.gui.basher
        import locale
        locale.setlocale(locale.LC_ALL, '')
        import os
        cwd = os.getcwd()
        del os
        self._BashProcess__run(bash.gui.basher.main, cwd, self.to_parent_queue, self.to_gui_queue, self.to_bashim_queue)

def mainLoop(bashim_process, basher_process, to_parent_queue, to_gui_queue, to_bashim_queue):
    """Parent process: Handle all the incoming messages"""
    to_parent_queue_get = to_parent_queue.get
    import bash.messages
    SHUTDOWN = bash.messages.SHUTDOWN
    CLOSE_PROCESS = bash.messages.CLOSE_PROCESS
    RESTART = bash.messages.RESTART
    SYSTEM_REQUEST = bash.messages.SYSTEM_REQUEST
    USER_REQUEST = bash.messages.USER_REQUEST
    from queue import Empty as QueueEmpty
    from imp import reload
##    from time import sleep
    print(basher_process.pid)
    print(bashim_process.pid)
    try:
        while True:
##            sleep(0.5) #simulate an unresponsive parent
##            continue
            try:
                command, args, response_to = to_parent_queue_get(timeout=1.0) #Blocking
            except QueueEmpty:
                if not basher_process.is_alive():
                    raise EnvironmentError('The Bash parent process is unable to communicate with the GUI. A support process may have crashed or been terminated by the user.')
                if not bashim_process.is_alive():
                    raise EnvironmentError('The Bash parent process is unable to communicate with the backend. A support process may have crashed or been terminated by the user.')
                continue

            print('parent - ', command, args, response_to)
            if command == SHUTDOWN:
                break
            elif command == RESTART:
                if args[0] == 'ALL':
    ##                    print("restarting all processes")
                    if basher_process.is_alive():
                        to_gui_queue.put((CLOSE_PROCESS, (SYSTEM_REQUEST,), None))
                    if bashim_process.is_alive():
                        to_bashim_queue.put((CLOSE_PROCESS, (SYSTEM_REQUEST,), None))
                    bashim_process.join()
                    basher_process.join()

                    to_parent_queue = multiprocessing.Queue()
                    to_gui_queue = multiprocessing.Queue()
                    to_bashim_queue = multiprocessing.Queue()
                    to_parent_queue_get = to_parent_queue.get

                    bashim_process = _BashIntermediaryProcess(bashim_process_id, to_parent_queue, to_gui_queue, to_bashim_queue)
                    bashim_process.start() #non-blocking

                    basher_process = _BashGUIProcess(basher_process_id, to_parent_queue, to_gui_queue, to_bashim_queue)
                    basher_process.start() #non-blocking
                elif args[0] == basher_process_id:
    ##                    print("restarting gui process")
                    basher_process.join(0.1)
                    if basher_process.is_alive():
                        to_gui_queue.put((CLOSE_PROCESS, (SYSTEM_REQUEST,), None))
                    basher_process.join()

                    basher_process = _BashGUIProcess(basher_process_id, to_parent_queue, to_gui_queue, to_bashim_queue)
                    basher_process.start() #non-blocking
                elif args[0] == bashim_process_id:
    ##                    print("restarting bashim process")
                    bashim_process.join(0.1)
                    if bashim_process.is_alive():
                        to_bashim_queue.put((CLOSE_PROCESS, (SYSTEM_REQUEST,), None))
                    bashim_process.join()

                    bashim_process = _BashIntermediaryProcess(bashim_process_id, to_parent_queue, to_gui_queue, to_bashim_queue)
                    bashim_process.start() #non-blocking
                reload(bash.messages)
                SHUTDOWN = bash.messages.SHUTDOWN
                CLOSE_PROCESS = bash.messages.CLOSE_PROCESS
                RESTART = bash.messages.RESTART
                SYSTEM_REQUEST = bash.messages.SYSTEM_REQUEST
                USER_REQUEST = bash.messages.USER_REQUEST
    finally:
##        print("stopping all processes")
        to_gui_queue.put((CLOSE_PROCESS, (SYSTEM_REQUEST,), None))
        to_bashim_queue.put((CLOSE_PROCESS, (SYSTEM_REQUEST,), None))
        bashim_process.join()
        basher_process.join()

if __name__ == '__main__':
    """Parent process: Start the GUI and bashim processes."""
    multiprocessing.freeze_support()
    to_parent_queue = multiprocessing.Queue()
    to_gui_queue = multiprocessing.Queue()
    to_bashim_queue = multiprocessing.Queue()
    err = None
    try:
        bashim_process = _BashIntermediaryProcess(bashim_process_id, to_parent_queue, to_gui_queue, to_bashim_queue)
        bashim_process.start() #non-blocking

        basher_process = _BashGUIProcess(basher_process_id, to_parent_queue, to_gui_queue, to_bashim_queue)
        basher_process.start() #non-blocking
    except:
##        print("stopping all processes")
        import bash.messages
        to_gui_queue.put((bash.messages.CLOSE_PROCESS, (bash.messages.SYSTEM_REQUEST,), None))
        to_bashim_queue.put((bash.messages.CLOSE_PROCESS, (bash.messages.SYSTEM_REQUEST,), None))
        bashim_process.join()
        basher_process.join()
        raise
##        print("parent stopped")
    else:
        err = mainLoop(bashim_process, basher_process, to_parent_queue, to_gui_queue, to_bashim_queue)
