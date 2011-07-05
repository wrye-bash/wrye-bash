# -*- coding: utf-8 -*-
#
# bait/util/debug_utils.py
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

from cStringIO import StringIO


class Dumpable:
    """Derive classes from this to allow the str() method to dump their public values"""
    def __str__(self):
        outStr = StringIO()
        outStr.write(self.__class__.__name__)
        outStr.write("[")
        isFirst = True
        for varName in self.__dict__:
            if not varName.startswith("_"):
                if not isFirst:
                    outStr.write("; ")
                outStr.write(varName)
                outStr.write("=")
                varVal = self.__dict__[varName]
                if isinstance(varVal, (str, unicode)):
                    outStr.write("'")
                    outStr.write(varVal)
                    outStr.write("'")
                else:
                    outStr.write(str(varVal))
                isFirst = False
        outStr.write("]")
        return outStr.getvalue()
