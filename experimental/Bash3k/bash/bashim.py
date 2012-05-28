# -*- coding: utf-8 -*-

"""bashim is an intermediary layer between all components.
   Only bashim communicates to the GUI, and the GUI only communicates to bashim."""

#.games/__init__.py controls which game actually gets imported
import bash.games.manager
from bash.messages import *

from queue import Empty as QueueEmpty
from time import time, sleep
from imp import reload
import heapq
import os
import subprocess
import locale

##print(dir())
##print()

class BashIntermediary:
    """bashim process: Intermediary layer"""
    def __init__(self, top_working_dir, to_parent_queue, to_gui_queue, to_bashim_queue):
        self.to_parent_queue = to_parent_queue
        self.to_bashim_queue = to_bashim_queue
        self.to_gui_queue = to_gui_queue
        self._command_table = {}
        self.afters = []
        self.game_manager = bash.games.manager.ResourceManager(top_working_dir)
        #Before the connection is used, bind all messages that might be received
        self.bind_message(GET_RESOURCE, self.get_resource)
        self.bind_message(SET_RESOURCE, self.set_resource)
        self.bind_message(GET_SETTING, self.get_setting)
        self.bind_message(TOGGLE_SETTING, self.toggle_setting)
        self.bind_message(REQUEST_VOLATILE_UPDATE, self.get_volatile)
        self.bind_message(LAUNCH_PROGRAM, self.launch_program)
        self.is_alive()
        #Delay any initial messages until the other connection is ready
        self.bind_message(CONNECTION_READY, self.initialize)
        self.to_gui_queue.put((CONNECTION_READY, None, None))

    def initialize(self, args):
        #Rebind CONNECTION_READY to signal that this side is ready without re-initializing
        self.bind_message(CONNECTION_READY, lambda args: self.to_gui_queue.put((CONNECTION_READY, None, None)))
        self.to_gui_queue.put((IS_ALIVE_REQ, (self.last_is_alive_sent,), None))

    def mainLoop(self):
        """bashim process: Handle all the incoming messages"""
        command_table = self._command_table
        to_bashim_queue_get = self.to_bashim_queue.get
        _timeout = 0.2
        heappop = heapq.heappop
        heappush = heapq.heappush
        afters = self.afters
        while True:
            try:
                command, args, response_to = to_bashim_queue_get(timeout=_timeout) #Blocking
            except QueueEmpty:
                if self.afters:
                    sched_time, func = heappop(afters)
                    while time() - sched_time >= 0:
                        func()
                        if not afters: break
                        sched_time, func = heapq.heappop(afters)
                    _timeout = time() - sched_time
                    heappush(afters, (sched_time, func))
                else:
                    _timeout = 5.0
                sleep(0.1)
                continue
##            print('bashim - ',command, args, response_to)
            if command == CLOSE_PROCESS: return args[0]
            command_table[command](args)
        print("bashim stopping - Exception occurred?")
        return False

    def bind_message(self, command_id, command_func):
        self._command_table[command_id] = command_func

    def unbind_message(self, command_id):
        if command_id in self._command_table:
            del self._command_table[command_id]

    def get_resource(self, args):
        resource_name = args[0]
        resource = self.game_manager.get_resource(resource_name, None)
        self.to_gui_queue.put((SET_RESOURCE, (resource_name, resource), (GET_RESOURCE, args)))

    def set_resource(self, args):
        resource_name, resource_value = args
        return_message = self.game_manager.set_resource(resource_name, resource_value)
        if return_message:
            self.to_gui_queue.put((return_message, (SET_RESOURCE, args)))

    def get_setting(self, args):
        setting_name = args[0]
        setting_value = self.game_manager.get_setting(setting_name, None)
        self.to_gui_queue.put((SET_SETTING, (setting_name, setting_value), (GET_SETTING, args)))

    def get_volatile(self, args):
        resource_name = args[0]
        resource = self.game_manager.get_resource(resource_name, None)
        self.to_gui_queue.put((UPDATE_VOLATILE, (resource_name, resource), (REQUEST_VOLATILE_UPDATE, args)))

    def toggle_setting(self, args):
        resource_name = args[0]
        self.game_manager.toggle_setting(resource_name)

    def after_idle(self, delay, func):
        """Sets a function callback after a minimum delay in seconds when no messages are being processed"""
        heapq.heappush(self.afters, (time() + delay, func))

    def launch_program(self, args):
        program_path, program_name, program_icon, program_args, program_working_dir = args
        if program_path.endswith('.lnk') or os.path.isdir(program_path):
            os.startfile(program_path)
        else:
            cwd = os.getcwd()
            if not program_working_dir:
                program_working_dir = os.path.split(program_path)[0]
            os.chdir(program_working_dir)
            if program_args:
                subprocess.Popen([program_path, program_args], close_fds=True)
            else:
                subprocess.Popen(program_path, close_fds=True)
            os.chdir(cwd)

    def is_alive(self):
        """Periodically polls to_gui_queue to make sure there's a listener."""
        self.last_is_alive_sent = 0
        self.last_is_alive_received = 0
        self.is_not_alive_count = 0
        def got_ack(args):
            self.last_is_alive_received = args[0]
        def got_req(args):
            send_ack(args)
        def send_req():
            last_is_alive_sent = self.last_is_alive_sent
            if self.last_is_alive_sent != self.last_is_alive_received:
                self.is_not_alive_count += 1
                if self.is_not_alive_count > 1:
                    self.to_parent_queue.put((SHUTDOWN, (SYSTEM_ERROR,), None))
                    raise EnvironmentError('The Bash backend is unable to communicate with the rest of Bash. A support process may have crashed or been terminated by the user.')
            last_is_alive_sent += 1
            if last_is_alive_sent > 60:
                last_is_alive_sent = 0
            self.to_gui_queue.put((IS_ALIVE_REQ, (last_is_alive_sent,), None))
            self.last_is_alive_sent = last_is_alive_sent
            self.after_idle(5.0, send_req)
        def send_ack(args):
            self.to_gui_queue.put((IS_ALIVE_ACK, args, None))
        self.bind_message(IS_ALIVE_ACK, got_ack)
        self.bind_message(IS_ALIVE_REQ, got_req)
