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

"""This module starts the Wrye Bash application. Basically, it runs some
initialization functions, and then starts the main application loop.

bash [-u userPath] [-p personalPath] [-l localAppDataPath] [0]
User directory arguments (-u, -p and -l).
These arguments allow you to specify your user directory in several ways. These
are only useful if the regular procedure for getting the user directory fails.
And even in that case, the user is probably bettr off installing win32com.
However, the arguments are:

-u userPath: Specify the user profile path. May help if HOMEDRIVE and/or HOMEPATH
are missing from the user's environgment. Example: -u "C:\Documents and Settings\Wrye"

-p personalPath: Specify the user's personal directory. Must be used in
conjunction with -l option.
Example: -p "c:\documents and settings\Wrye\My Documents"

-l localAppDataPath: Specify the user's local application data directory. Must be used in
conjunction with -l option.
Example: -p "c:\documents and settings\Wrye\Local Settings\Application Data"

Debug argument:
-d Send debug text to the console rather than to a newly created debug window.
Useful if bash is crashing on startup or if you want to print a lot of
information (e.g. while developing or debugging).
"""

# Imports ---------------------------------------------------------------------
import getopt
import os
import sys
if sys.version[:3] == '2.4':
    import wxversion
    wxversion.select("2.5.3.1")
import bosh, basher
import bolt

# Main ------------------------------------------------------------------------
def main():
    #import warnings
    #warnings.filterwarnings('error')
    #--Parse arguments
    optlist,args = getopt.getopt(sys.argv[1:],'u:p:l:d')
    #--Initialize Directories
    opts = dict(optlist)
    if '-u' in opts:
        drive,path = os.path.splitdrive(opts['-u'])
        os.environ['HOMEDRIVE'] = drive
        os.environ['HOMEPATH'] = path
    personal = opts.get('-p')
    localAppData = opts.get('-l')
    bosh.initDirs(personal,localAppData)
    #--More Initialization
    basher.InitSettings()
    basher.InitLinks()
    basher.InitImages()
    #--Start application
    if '-d' in opts or (args and args[0] == '0'):
        app = basher.BashApp(False)
        bolt.deprintOn = True
    else:
        app = basher.BashApp()
    app.MainLoop()

if __name__ == '__main__':
    try:
        args = sys.argv[1:]
        if '-d' not in args and '0' not in args:
            import psyco
            psyco.full()
    except:
        pass
    main()
