#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# GPL License and Copyright Notice ============================================
#  This file is part of Wrye Bash.
#
#  Wrye Bash is free software: you can redistribute it and/or
#  modify it under the terms of the GNU General Public License
#  as published by the Free Software Foundation, either version 3
#  of the License, or (at your option) any later version.
#
#  Wrye Bash is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
#
#  You should have received a copy of the GNU General Public License
#  along with Wrye Bash.  If not, see <https://www.gnu.org/licenses/>.
#
#  Wrye Bash copyright (C) 2005-2009 Wrye, 2010-2026 Wrye Bash Team
#  https://github.com/wrye-bash
#
# =============================================================================

"""This module starts the Wrye Bash application in GUI mode. It checks the
Python version and shows the errors of importing bash, so it must only use
the standard library - and syntax that old Pythons can parse."""
import sys

# The links the boot error messages point to - bash.main gets them passed
_help_urls = {
 'thread_url': 'https://afkmods.com/index.php?/topic/4966-wrye-bash-all-games',
 'discord_url': 'https://discord.gg/NwWvAFR',
 'ms_docs_url': 'https://support.microsoft.com/en-us/office/back-up-your-documents-pictures-and-desktop-folders-with-onedrive-d61a7930-a6fb-4b95-b28a-6552e77c3057',
}
# accepted Python versions - importing bash needs 3.11 (bolt imports Self)
_MIN_PYTHON, _MAX_PYTHON = (3, 11), (4,)

def _boot_failed(msg):
    """Show msg in a popup, then exit - for the errors that bash could not
    show with wx, or importing bash itself."""
    if sys.platform == 'win32': # the standalone does not bundle tkinter
        from ctypes import windll # 0x50010: error icon, foreground, topmost
        windll.user32.MessageBoxW(None, msg, 'Wrye Bash Error', 0x50010)
        sys.exit(1)
    # tkinter may not be installed (python3-tk) and needs a display - not
    # stderr, which also writes to the BashBugDump, uncensored
    sys.__stderr__.write(msg + '\n')
    import tkinter
    root = tkinter.Tk() ##: on macos this crashes
    root.title('Wrye Bash Error')
    text = tkinter.Text(root)
    text.insert(tkinter.END, msg)
    text.config(state=tkinter.DISABLED)
    text.pack(fill=tkinter.BOTH, expand=1)
    tkinter.Button(root, text='QUIT', fg='red', command=root.destroy).pack(
        fill=tkinter.X)
    root.mainloop()
    sys.exit(1)

if __name__ == '__main__':
    # check the Python version on a Python install - the standalone bundles
    # one we support
    if not hasattr(sys, 'frozen') and not (
            _MIN_PYTHON <= sys.version_info[:3] < _MAX_PYTHON):
        _boot_failed("Only Python %s and newer up to %s is supported (%s "
            "detected). If you know what you're doing, edit this warning "
            "out. Wrye Bash will now exit." % tuple('.'.join(map(str, v)) for
            v in (_MIN_PYTHON, _MAX_PYTHON, sys.version_info[:3])))
    try:
        from bash import barg, bash
        bash.main(barg.parse(), _help_urls)
    except SystemExit as e: # bash exits with the error it could not show
        if isinstance(e.code, str): _boot_failed(e.code)
        raise
    except Exception: # importing bash failed, or main before its try
        import traceback
        _boot_failed('Wrye Bash failed to start - please make sure it is '
            'installed correctly. Should the error persist, please post the '
            'information below to the official thread at %(thread_url)s or '
            'to the Wrye Bash Discord at %(discord_url)s' % _help_urls +
            '\n\n' + traceback.format_exc())
