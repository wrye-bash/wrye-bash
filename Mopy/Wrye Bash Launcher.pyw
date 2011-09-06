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
import os
import sys
import traceback

# get instruction to stop at from commandline
targetCounter = len(sys.argv) > 1 and int(sys.argv.pop()) or 0
instCounter = 0
def instruction_tracer(frame, event, arg):
    if event == "line":
        name = frame.f_globals.get("__name__", "unknown")
        if name.startswith("bash."):
            filename = frame.f_globals.get("__file__", "unknown")
            if (filename.endswith(".pyc") or filename.endswith(".pyo")):
                filename = filename[:-1]
            lineno = frame.f_lineno
            line = linecache.getline(filename, lineno)
            global targetCounter
            global instCounter
            instCounter += 1
            print "%s/%s %s:%s: %s" % (instCounter, targetCounter, name, lineno, line.rstrip())
            if targetCounter == instCounter:
                traceback.print_stack()
                os._exit(1)
    return instruction_tracer

if targetCounter:
    sys.settrace(instruction_tracer)

from bash import bash, bolt

if __name__ == '__main__':
    bash.main()
