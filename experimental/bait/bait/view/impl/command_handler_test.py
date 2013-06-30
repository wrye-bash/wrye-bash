# -*- coding: utf-8 -*-
#
# bait/view/impl/command_handler_test.py
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
import time

from ... import presenter
from . import command_handler, filter_registry


_expectException = False
_expectCall = True

def _call_after(fn, arg):
    global _expectCall
    global _expectException

    assert _expectCall
    # just execute it in the calling thread
    gotException = False
    try:
        fn(arg)
    except:
        gotException = True
        if not _expectException:
            raise
    assert gotException == _expectException

def _wait_until_empty(queue):
    while 0 < queue.unfinished_tasks:
        # for some reason, sleep(0) here just spins indefinitely
        time.sleep(0.01)

def _do_command(commandHandler, command):
    # halt the test if the command handler thread dies
    if not commandHandler._commandThread.is_alive():
        raise RuntimeError("command thread died")
    queue = commandHandler._inCommandQueue
    queue.put(command)
    _wait_until_empty(queue)


class _DummyFilterRegistry:
    def add_filter(self, *args): pass
    def set_filter_stats(self, *args): pass
class _DummyGlobalSettingsButton:
    def set_settings(self, *args): pass
class _DummyStatusPanel:
    def set_ok(self, *args): pass
    def set_loading(self, *args): pass
    def set_dirty(self, *args): pass
    def set_doing_io(self, *args): pass
class _DummyTree:
    def add_node(self, *args): pass
    def update_node(self, *args): pass
    def remove_node(self, *args): pass
    def clear(self): pass
class _DummyPackagesTree(_DummyTree):
    def __init__(self):
        self.nodeIdToLabelMap = {}
    def set_checkbox_images(self, *args): pass
class _DummyPackageContentsTree(_DummyTree):
    pass
class _DummyPackageContentsPanel:
    def __init__(self):
        self.packageContentsTree = _DummyPackageContentsTree()
    def reset(self, *args): pass
    def set_general_tab_info(self, *args): pass
    def set_general_tab_image(self, *args): pass
    def set_dirty_tab_info(self, *args): pass
    def set_conflicts_tab_info(self, *args): pass
    def set_selected_tab_info(self, *args): pass
    def set_unselected_tab_info(self, *args): pass
    def set_skipped_tab_info(self, *args): pass
class _DummyInstallerTab:
    def __init__(self):
        self.globalSettingsButton = _DummyGlobalSettingsButton()
        self.statusPanel = _DummyStatusPanel()
        self.packagesTree = _DummyPackagesTree()
        self.packageContentsPanel = _DummyPackageContentsPanel()
    def display_error(self, *args): pass
    def ask_confirmation(self, *args): pass
class _DummyImageLoader:
    def load_image(self, *args): pass
class _DummyMesssageManager:
    def get_error_message(self, *args): return ""
    def get_confirmation_message(self, *args): return ""


def command_thread_failure_test():
    commandQueue = Queue.Queue()

    global _expectCall
    _expectCall = False

    ch = command_handler.CommandHandler(commandQueue, None, None, None,
                                        messageManager=None, callAfterFn=_call_after)
    ch.start()

    try:
        _do_command(ch, presenter.SetGlobalSettingsCommand(True))
    finally:
        commandQueue.put(None)
        ch.shutdown()


def command_thread_test():
    commandQueue = Queue.Queue()
    filterRegistry = _DummyFilterRegistry()
    installerTab = _DummyInstallerTab()
    imageLoader = _DummyImageLoader()
    messageManager = _DummyMesssageManager()

    global _expectCall
    global _expectException

    _expectCall = False
    ch = command_handler.CommandHandler(commandQueue, filterRegistry, installerTab,
                                        imageLoader, messageManager=messageManager,
                                        callAfterFn=_call_after)
    ch.start()

    try:
        style1 = presenter.Style()
        style2 = presenter.Style(presenter.FontStyleIds.BOLD,
                                 presenter.ForegroundColorIds.HAS_SUBPACKAGES,
                                 presenter.HighlightColorIds.MISSING_DEPENDENCY,
                                 True, presenter.IconIds.INSTALLER_EMPTY)

        _expectCall = True
        _expectException = False
        _do_command(ch, presenter.SetGlobalSettingsCommand(True))
        _do_command(ch, presenter.SetPackageContentsInfoCommand("", True))
        _do_command(ch, presenter.SetStatusOkCommand(0, 0, 0, 0, 0, 0))
        _do_command(ch, presenter.SetStatusDirtyCommand([]))
        _do_command(ch, presenter.SetStatusLoadingCommand(500, 1000))
        _do_command(ch, presenter.SetStatusIOCommand([]))
        _do_command(ch, presenter.SetStyleMapsCommand({}, {}, {}, {}))
        _do_command(ch, presenter.UpdateNodeCommand(presenter.NodeTreeIds.PACKAGES, 0, "",
                                                    True, style1))
        _do_command(ch, presenter.AddNodeCommand(presenter.NodeTreeIds.CONTENTS, 1, "",
                                                 False, style2, 0, None,
                                                 presenter.ContextMenuIds.BSAFILE))
        _do_command(ch, presenter.RemoveNodeCommand(presenter.NodeTreeIds.PACKAGES, 0))
        _do_command(ch, presenter.ClearTreeCommand(presenter.NodeTreeIds.CONTENTS))
        _do_command(ch, presenter.SetFilterStatsCommand(presenter.FilterIds.DIRTY_ADD,
                                                        10, 20))
        _do_command(ch, presenter.SetGeneralTabInfoCommand(True, False, True, 0, 0, "",
                                                           *[0]*20))
        _do_command(ch, presenter.SetDirtyTabInfoCommand([]))
        _do_command(ch, presenter.SetConflictsTabInfoCommand([]))
        _do_command(ch, presenter.SetFileListTabInfoCommand(
            presenter.DetailsTabIds.SELECTED, []))
        _do_command(ch, presenter.SetFileListTabInfoCommand(
            presenter.DetailsTabIds.UNSELECTED, []))
        _do_command(ch, presenter.SetFileListTabInfoCommand(
            presenter.DetailsTabIds.SKIPPED, []))
        _do_command(ch, presenter.DisplayErrorCommand(presenter.ErrorCodes.DISK_FULL, ""))
        _do_command(ch, presenter.AskConfirmationCommand(
            presenter.ConfirmationQuestionIds.DELETE, ""))
        _do_command(ch, presenter.ExtendedCommand())

        _expectException = True
        _do_command(ch, presenter.ClearTreeCommand(-1))
        _do_command(ch, presenter.SetFileListTabInfoCommand(
            presenter.DetailsTabIds.CONFLICTS, []))

        _expectCall = False
        _do_command(ch, 'notacommand')
        badCommand = presenter.ExtendedCommand()
        badCommand.commandId = -1
        _do_command(ch, badCommand)
        ch.set_ignore_updates()
        _do_command(ch, presenter.ExtendedCommand())
    finally:
        commandQueue.put(None)
        ch.shutdown()
