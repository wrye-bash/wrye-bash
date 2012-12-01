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

"""This module parses the command line that was used to start Wrye Bash."""

import optparse
import sys

def parse():
    parser = optparse.OptionParser()
    parser.add_option('-g', '--game',
                        action='store',
                        type='string',
                        default='',
                        dest='gameName',
                        help='Specifies the game Wrye Bash should try to manage.  Use this argument if more than one game Wrye Bash supports is installed.')
    pathGroup = optparse.OptionGroup(parser, "Path Arguments",
                         r"All path arguments must be absolute paths and use either forward slashes (/) or two backward slashes (\\). All of these can also be set in the ini (where  you can also use relative paths) and if set in both cmd line takes precedence.")
    pathGroup.add_option('-o', '--oblivionPath',
                        action='store',
                        type='string',
                        default='',
                        dest='oblivionPath',
                        help='Specifies the game directory (the one containing game\'s exe). Use this argument if Bash is located outside of the game directory, and the --game argument failed to find it.')
    userPathGroup = optparse.OptionGroup(parser, "'User Directory Arguments",
                        'These arguments allow you to specify your user directories in several ways.'
                        ' These are only useful if the regular procedure for getting the user directory fails.'
                        ' And even in that case, the user is probably better off installing win32com.')
    userPathGroup.add_option('-p', '--personalPath',
                        action='store',
                        type='string',
                        default='',
                        dest='personalPath',
                        help='Specify the user\'s personal directory. (Like "C:\\\\Documents and Settings\\\\Wrye\\\\My Documents\") '
                             'If you need to set this then you probably need to set -l too')
    userPathGroup.add_option('-u', '--userPath',
                        action='store',
                        type='string',
                        default='',
                        dest='userPath',
                        help='Specify the user profile path. May help if HOMEDRIVE and/or HOMEPATH'
                             ' are missing from the user\'s environment')
    userPathGroup.add_option('-l', '--localAppDataPath',
                        action='store',
                        type='string',
                        default='',
                        dest='localAppDataPath',
                        help='Specify the user\'s local application data directory.'
                             'If you need to set this then you probably need to set -p too.')
    backupGroup = optparse.OptionGroup(parser, "'Backup and Restore Arguments",
                        'These arguments allow you to do backup and restore settings operations.')
    backupGroup.add_option('-b', '--backup',
                        action='store_true',
                        default=False,
                        dest='backup',
                        help='Backup all Bash settings to an archive file before the app launches. Either specify the filepath with  the -f/--filename options or Wrye Bash will prompt the user for the backup file path.')
    backupGroup.add_option('-r', '--restore',
                        action='store_true',
                        default=False,
                        dest='restore',
                        help='Backup all Bash settings to an archive file before the app launches. Either specify the filepath with  the -f/--filename options or Wrye Bash will prompt the user for the backup file path.')
    backupGroup.add_option('-f', '--filename',
                        action='store',
                        default='',
                        dest='filename',
                        help='The file to use with the -r or -b options. Must end in \'.7z\' and be a valid path and for -r exist and for -b not already exist.')
    backupGroup.add_option('-q', '--quiet-quit',
                        action='store_true',
                        default=False,
                        dest='quietquit',
                        help='Close Bash after creating or restoring backup and do not display any prompts or message dialogs.')
    parser.set_defaults(backup_images=0)
    backupGroup.add_option('-i', '--include-changed-images',
                        action='store_const',
                        const=1,
                        dest='backup_images',
                        help='Include changed images from mopy/bash/images in the backup. Include any image(s) from backup file in restore.')
    backupGroup.add_option('-I', '--include-all-images',
                        action='store_const',
                        const=2,
                        dest='backup_images',
                        help='Include all images from mopy/bash/images in the backup/restore (if present in backup file).')
    parser.add_option('-d', '--debug',
                        action='store_true',
                        default=False,
                        dest='debug',
                        help='Useful if bash is crashing on startup or if you want to print a lot of '
                             'information (e.g. while developing or debugging).')
    parser.add_option('--no-psyco',
                        action='store_false',
                        default=True,
                        dest='Psyco',
                        help='Disables import of Psyco')
    parser.set_defaults(mode=0)
    parser.add_option('-C', '--Cbash-mode',
                        action='store_const',
                        const=2,
                        dest='mode',
                        help='enables CBash and uses CBash to build bashed patch.')
    parser.add_option('-P', '--Python-mode',
                        action='store_const',
                        const=1,
                        dest='mode',
                        help='disables CBash and uses python code to build bashed patch.')
    parser.add_option('--restarting',
                        action='store_true',
                        default=False,
                        dest='restarting',
                        help=optparse.SUPPRESS_HELP)
    parser.add_option('--no-uac',
                        action='store_true',
                        default=False,
                        dest='noUac',
                        help='suppress the prompt to restart in admin mode when UAC is detected.')
    parser.add_option('--uac',
                        action='store_true',
                        default=False,
                        dest='uac',
                        help='always start in admin mode if UAC protection is detected.')
    parser.add_option('--bashmon',
                        action='store_true',
                        help=optparse.SUPPRESS_HELP)
    parser.add_option('--genHtml',
                        default=None,
                        help=optparse.SUPPRESS_HELP)
    parser.add_option('-L', '--Language',
                        action='store',
                        type='string',
                        default='',
                        dest='language',
                        help='Specify the user language overriding the system language settings.')

    parser.add_option_group(pathGroup)
    parser.add_option_group(userPathGroup)
    parser.add_option_group(backupGroup)

    opts,extra = parser.parse_args()
    if len(extra) > 0:
        parser.print_help()
    return opts, extra