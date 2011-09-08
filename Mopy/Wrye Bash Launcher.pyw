# -*- coding: utf-8 -*-
#
# GPL License and Copyright Notice ============================================
#  This file is part of Wrye Bash.
#
#  Wrye Bash is free software; you can redistribute it and/or
#  modify it under the terms of the GNU General Public License
#  as published by the Free Software Foundation; either version 2
#  of the License, or (at your option) any later version.
#
#  Wrye Bash is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
#
#  You should have received a copy of the GNU General Public License
#  along with Wrye Bash; if not, write to the Free Software Foundation,
#  Inc., 59 Temple Place - Suite 330, Boston, MA  02111-1307, USA.
#
#  Wrye Bash copyright (C) 2005, 2006, 2007, 2008, 2009 Wrye
#
# =============================================================================

"""This module starts the Wrye Bash application in GUI mode."""

import linecache
import locale
import os
import sys
import traceback

_instCounter = 0
def instruction_tracer(frame, event, arg):
    if event == "line":
        name = frame.f_globals.get("__name__", "unknown")
        if name.startswith("bash."):
            filename = frame.f_globals.get("__file__", "unknown")
            if (filename.endswith(".pyc") or filename.endswith(".pyo")):
                filename = filename[:-1]
            lineno = frame.f_lineno
            line = linecache.getline(filename, lineno)
            global _targetCounter
            global _instCounter
            _instCounter += 1
            # print the last 100 instructions before the forced exit
            if _targetCounter <= _instCounter+10:
                print "%s/%s %s:%s: %s" % (_instCounter, _targetCounter, name, lineno, line.rstrip())
            if _targetCounter == _instCounter:
                traceback.print_stack()
                os._exit(1)
    return instruction_tracer

if __name__ == '__main__':
    print "Wrye Bash starting"
    print "Python version: %d.%d.%d" % (sys.version_info.major, sys.version_info.minor, sys.version_info.micro)
    try:
        import wx
        print "wxPython version: %s" % wx.version()
    except ImportError:
        print "wxPython not found"
    print "input encoding: %s; output encoding: %s; locale: %s" % (sys.stdin.encoding, sys.stdout.encoding, locale.getdefaultlocale())

    global _targetCounter
    # get instruction to stop at from last arg of commandline
    _targetCounter = len(sys.argv) > 1 and int(sys.argv.pop()) or 0
    if _targetCounter:
        sys.settrace(instruction_tracer)

    # only import bash-related modules after the tracer is set
    from bash import bash

    bash.main()
