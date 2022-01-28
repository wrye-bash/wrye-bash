# -*- coding: utf-8 -*-
#
# GPL License and Copyright Notice ============================================
#  This file is part of Wrye Bash.
#
#  Wrye Bash is free software: you can redistribute it and/or
#  modify it under the terms of the GNU General Public License
#  as published by the Free Software Foundation, either version 3
#  of the License, or (at your option) any later version.
#
#  Wrye Bash is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
#
#  You should have received a copy of the GNU General Public License
#  along with Wrye Bash.  If not, see <https://www.gnu.org/licenses/>.
#
#  Wrye Bash copyright (C) 2005-2009 Wrye, 2010-2022 Wrye Bash Team
#  https://github.com/wrye-bash
#
# =============================================================================

"""This module parses the command line that was used to start Wrye Bash."""

import argparse

def parse():
    """Helper function to define commandline arguments"""
    parser = argparse.ArgumentParser()

    #### Groups ####
    def arg(group, dashed, descr, dest, action=u'store', default=None):
        group.add_argument(dashed, descr, dest=dest, action=action,
                           default=u'' if default is None else default,
                           help=h) # so we can wrap help but not too much

    ### Path Group ###
    pathGroup = parser.add_argument_group(u'Path Arguments',
        u'All path arguments must be absolute paths and use either forward '
        r'slashes (/) or two backward slashes (\\). All of these can also '
        u'be set in the ini (where you can also use relative paths) and if '
        u'set in both cmd line takes precedence.')
    # oblivionPath #
    h = (u"Specifies the game directory (the one containing the game's exe). "
         u'Use this argument if Bash is located outside of the game '
         u'directory, and automatic detection failed to find it.')
    arg(pathGroup, u'-o', u'--oblivionPath', dest=u'oblivionPath')

    ### User Path Group ###
    userPathGroup = parser.add_argument_group(u'User Directory Arguments',
        u'These arguments allow you to specify your user directories in '
        u'several ways. These are only useful if the regular procedure for '
        u'getting the user directory fails. And even in that case, the user '
        u'is probably better off installing win32com.')
    # personalPath #
    h = (u"Specify the user's personal directory. (Like \"C:\\Documents and "
         u'Settings\\Wrye\\My Documents") If you need to set this then you '
         u'probably need to set -l too.')
    arg(userPathGroup, u'-p', u'--personalPath', dest=u'personalPath')
    # userPath #
    h = (u'Specify the user profile path. May help if HOMEDRIVE and/or '
         u"HOMEPATH are missing from the user's environment.")
    arg(userPathGroup, u'-u', u'--userPath', dest=u'userPath')
    # localAppDataPath #
    h = (u"Specify the user's local application data directory. If you need "
         u'to set this then you probably need to set -p too.')
    arg(userPathGroup, u'-l', u'--localAppDataPath', dest=u'localAppDataPath')

    ### Backup Group ###
    backupGroup = parser.add_argument_group(u'Backup and Restore Arguments',
        u'These arguments allow you to do backup and restore settings '
        u'operations.')
    # backup #
    h = (u'Backup all Bash settings to an archive file before the app '
         u'launches. You have to specify the filepath with the -f/--filename '
         u'option. If also -r is specified Bash will not start.')
    arg(backupGroup, u'-b', u'--backup', dest=u'backup', action=u'store_true',
        default=False)
    # restore #
    h = (u'Restore all Bash settings from an archive file before the app '
         u'launches. You have to specify the filepath with the -f/--filename '
         u'option. If also -b is specified Bash will not start.')
    arg(backupGroup, u'-r', u'--restore', dest=u'restore', action=u'store_true',
        default=False)
    # filename #
    h = (u"The file to use with the -r or -b options. For -r must be a '.7z' "
         u'backup file or a dir where such a file was extracted. For -b must '
         u"be a valid path to a '.7z' file that will be overwritten if it "
         u"exists.")
    arg(backupGroup, u'-f', u'--filename', dest=u'filename')
    # quietquit #
    h = (u'Close Bash after creating or restoring backup and do not display '
         u'any prompts or message dialogs.')
    arg(backupGroup, u'-q', u'--quiet-quit', dest=u'quietquit',
        action=u'store_true', default=False)

    #### Individual Arguments ####
    parser.add_argument(u'-d', u'--debug',
                        action=u'store_true',
                        dest=u'debug',
                        help=u'Useful if bash is crashing on startup or if '
                             u'you want to print a lot of information'
                             u' (e.g. while developing or debugging).')
    parser.add_argument(u'--no-uac',
                        action=u'store_true',
                        dest=u'noUac',
                        help=u'suppress the prompt to restart in admin mode '
                             u'when UAC is detected.')
    parser.add_argument(u'--uac',
                        action=u'store_true',
                        dest=u'uac',
                        help=u'always start in admin mode if UAC protection is '
                             u'detected.')
    parser.add_argument(u'--genHtml', default=None, help=argparse.SUPPRESS)
    parser.add_argument(u'-L', u'--Language',
                        action=u'store',
                        default=u'',
                        dest=u'language',
                        help=u'Specify the user language overriding the '
                             u'system language settings.')
    parser.add_argument(u'-n', u'--unix',
                        action=u'store_true',
                        help=u'Allow bash to run on unix systems ['
                             u'EXPERIMENTTAL].')
    # parse and error check backup options
    args = parser.parse_args()
    if args.backup and args.restore:
        parser.error(u'You specified both backup and restore')
    elif (args.backup or args.restore) and not args.filename:
        parser.error(u'You must specify a filename for use with '
                     u'backup/restore')
    return args

_short_to_long = {
    u'-b': u'--backup',
    u'-d': u'--debug',
    u'-f': u'--filename',
    u'-L': u'--Language',
    u'-l': u'--localAppDataPath',
    u'-n': u'--unix',
    u'-o': u'--oblivionPath',
    u'-p': u'--personalPath',
    u'-q': u'--quiet-quit',
    u'-r': u'--restore',
    u'-u': u'--userPath',
}

def convert_to_long_options(sys_argv):
    sys_argv = list(sys_argv)
    for j, arg in enumerate(sys_argv):
        if arg in _short_to_long:
            sys_argv[j] = _short_to_long[arg]
    return sys_argv
