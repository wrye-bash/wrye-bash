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
#  Wrye Bash copyright (C) 2005-2009 Wrye, 2010-2020 Wrye Bash Team
#  https://github.com/wrye-bash
#
# =============================================================================
"""Houses the parts of brec that didn't fit anywhere else or were needed by
almost all other parts of brec."""

from __future__ import division, print_function
import struct

from ..bolt import decode, struct_pack, struct_unpack
# no local imports, imported everywhere in brec

# Random stuff ----------------------------------------------------------------
def _coerce(value, newtype, base=None, AllowNone=False):
    try:
        if newtype is float:
            #--Force standard precision
            return round(struct_unpack('f', struct_pack('f', float(value)))[0], 6)
        elif newtype is bool:
            if isinstance(value,basestring):
                retValue = value.strip().lower()
                if AllowNone and retValue == u'none': return None
                return retValue not in (u'',u'none',u'false',u'no',u'0',u'0.0')
            else: return bool(value)
        elif base: retValue = newtype(value, base)
        elif newtype is unicode: retValue = decode(value)
        else: retValue = newtype(value)
        if (AllowNone and
            (isinstance(retValue,str) and retValue.lower() == 'none') or
            (isinstance(retValue,unicode) and retValue.lower() == u'none')
            ):
            return None
        return retValue
    except (ValueError,TypeError):
        if newtype is int: return 0
        return None

_int_unpacker = struct.Struct(u'I').unpack

# Reference (fid) -------------------------------------------------------------
def strFid(form_id):
    """Return a string representation of the fid."""
    if isinstance(form_id, tuple):
        return u'(%s, %06X)' % (form_id[0].s, form_id[1])
    else:
        return u'%08X' % form_id

def genFid(modIndex,objectIndex):
    """Generates a fid from modIndex and ObjectIndex."""
    return int(objectIndex) | (int(modIndex) << 24)

def getModIndex(form_id):
    """Returns the modIndex portion of a fid."""
    return int(form_id >> 24)

def getObjectIndex(form_id):
    """Returns the objectIndex portion of a fid."""
    return int(form_id & 0x00FFFFFF)

def getFormIndices(form_id):
    """Returns tuple of modIndex and ObjectIndex of fid."""
    return int(form_id >> 24), int(form_id & 0x00FFFFFF)

# Constants -------------------------------------------------------------------
# Used by MelStruct classes to indicate fid elements.
FID = 'FID'

# Null strings (for default empty byte arrays)
null1 = '\x00'
null2 = null1 * 2
null3 = null1 * 3
null4 = null1 * 4

# Hack for allowing record imports from parent games - set per game
MelModel = None # type: type
