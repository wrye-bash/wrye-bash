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
#  Wrye Bash copyright (C) 2005-2009 Wrye, 2010-2021 Wrye Bash Team
#  https://github.com/wrye-bash
#
# =============================================================================
"""Module providing a Mixin class to set some common defaults for Windows Store
   games.  Cannot handle modifying an attribute based on a parent class
   attribute."""
from . import GameInfo

class classproperty(object):
    # This is a more general tool, maybe stick it in...bolt?
    def __init__(self, fget):
        self.fget = fget
    def __get__(self, obj, owner):
        return self.fget(owner)

class WindowsStoreMixin(object):
    regInstallKeys = ()
    game_detect_excludes = []
    # We'd also like to set `game_detect_includes` but to do so we need the
    # parent class's attribute value:
    @classproperty
    def game_detect_includes(cls):
        return super(WindowsStoreMixin,
            cls).game_detect_includes + [u'appxmanifest.xml']

    # Disable any tools that require hooking into the game's executable. Even
    # if the user manually installs these, they will not work, with no workable
    # solution found by the tool devs.
    class Se(GameInfo.Se):
        pass
    class Sd(GameInfo.Sd):
        pass
    class Laa(GameInfo.Laa):
        pass
