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
import os as _os
import ConfigParser as _cp

language = None
AppVersion = u"307"
bashIni = None

#--Null strings (for default empty byte arrays)
null1 = '\x00'
null2 = null1*2
null3 = null1*3
null4 = null1*4

def GetBashIni(iniPath=None, reload_=False): ##: needs work
    iniPath = iniPath or u'bash.ini'
    global bashIni
    if reload_ or bashIni is None:
        if _os.path.exists(iniPath):
            bashIni = _cp.ConfigParser()
            bashIni.read(iniPath)
    return bashIni

class Resources: # this belongs to basher but leads to cyclic imports, so...
    fonts = None
    #--Icon Bundles
    bashRed = None
    bashBlue = None
    bashDocBrowser = None
    bashMonkey = None
