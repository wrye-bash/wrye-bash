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
# library for handling command line arguments

import sys
import os
import getopt

# ----------------------------------------------------------------------------------
def ParseArgs():
    #--Parse arguments
    optlist,args = getopt.getopt(sys.argv[1:],'o:u:p:l:b:r:qd',('restarting'))
    opts = dict(optlist)

    #strip options from sys.argv that should not be reinvoked on app restart
    for opt,argc in (('-b',1),('-r',1),('-q',0),('--restarting',0)):
        if opt in opts:
            i = sys.argv.index(opt)
            del sys.argv[i:i+argc+1]

    return (opts, args)

# ----------------------------------------------------------------------------------
def SetHomePath(homePath):
    drive,path = os.path.splitdrive(homePath)
    os.environ['HOMEDRIVE'] = drive
    os.environ['HOMEPATH'] = path

# ----------------------------------------------------------------------------------
def GetBashIni(iniPath):
    import ConfigParser
    bashIni = None
    if os.path.exists(iniPath):
        bashIni = ConfigParser.ConfigParser()
        bashIni.read(iniPath)
    return bashIni

# ----------------------------------------------------------------------------------
def SetUserPath(iniPath, uArg=None):
#if uArg is None, then get the UserPath from the ini file
    if uArg:
        SetHomePath(uArg)
    elif os.path.exists(iniPath):
        bashIni = GetBashIni(iniPath)
        if bashIni and bashIni.has_option('General', 'sUserPath') and not bashIni.get('General', 'sUserPath') == '.':
            SetHomePath(bashIni.get('General', 'sUserPath'))

# Main ------------------------------------------------------------------------
if __name__ == '__main__':
    print _('Compiled')
