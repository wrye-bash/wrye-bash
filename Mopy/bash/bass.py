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
#  Wrye Bash copyright (C) 2005-2009 Wrye, 2010-2015 Wrye Bash Team
#  https://github.com/wrye-bash
#
# =============================================================================

"""This module just stores some data that all modules have to be able to access
without worrying about circular imports. Currently used to expose layout
and environment issues - do not modify or imitate (ut)."""
import ConfigParser as _cp
import os as _os

language = None
AppVersion = u"307.201804150204" # must represent a valid float
__bashIni = None

#--Null strings (for default empty byte arrays)
null1 = '\x00'
null2 = null1*2
null3 = null1*3
null4 = null1*4

def GetBashIni(iniPath=None, reload_=False): ##: needs work
    iniPath = iniPath or u'bash.ini'
    global __bashIni
    if reload_ or __bashIni is None:
        if _os.path.exists(iniPath):
            __bashIni = _cp.ConfigParser()
            __bashIni.read(iniPath)
    return __bashIni

#--Global dictionaries - do _not_ reassign !
# Bash's directories - values are absolute Paths - populated in initDirs()
dirs = {}
# settings read from the Mopy/bash.ini file in initDefaultSettings()
inisettings = {}
# dirs where various apps may be located - populated in initDefaultTools()
tooldirs = {}

# settings dictionary - belongs to a dedicated settings module below bolt - WIP !
settings = None # bolt.Settings !

# restarting info
is_restarting = False # set to true so Bash is restarted via the exit hook
sys_argv = [] # set to the sys.argv used to start bash - modify when restarting

def update_sys_argv(arg):
    """Replace existing option with new one, option must be in *long* format"""
    if len(arg) == 2:
        try:
            option_index = sys_argv.index(arg[0])
            sys_argv[option_index + 1] = arg[1]
        except ValueError:
            sys_argv.extend(arg)
    else: # boolean switches like '--uac'
        if not arg[0] in sys_argv:
            sys_argv.append(arg[0])

#--Temp Files/Dirs - originally in Installer, probably belong to a new module
################################## DO NOT USE #################################
_tempDir = None # type: bolt.Path | None

def getTempDir():
    """Return current Temp Dir, generating one if needed."""
    return _tempDir if _tempDir is not None else newTempDir()

def rmTempDir():
    """Remove the current temporary directory, and set the current Temp Dir to
       None - meaning a new one will be generated on getTempDir()"""
    global _tempDir
    if _tempDir is None:
        return
    try:
        _tempDir.rmtree(safety=_tempDir.stail)
    except OSError:
        from bolt import deprint
        deprint(u'Failed to remove %s' % _tempDir, traceback=True)
    _tempDir = None

def newTempDir():
    """Generate a new temporary directory name, set it as the current Temp
    Dir."""
    global _tempDir
    from bolt import Path
    _tempDir = Path.tempDir()
    return _tempDir
