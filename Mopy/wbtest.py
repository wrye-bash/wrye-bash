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

# number of instructions until we know the problem happens
knownGoodInst = 0
knownBadInst = 1000000

# show slider that ranges from knownGoodInst to knownBadInst

# set slider halfway between knowns

# on "go" button click, run Wrye Bash Launcher.pyw with the slider value as the only argument

# run Oblivion.exe

# ask if Oblivion crashed
# print slider value and response to log

# if it crashed, reduce knownBadInst to current slider value
# if it did not crash, raise knownGoodInst to current slider value

# show slider and repeat until knownGoodInst == knownBadInst - 1
