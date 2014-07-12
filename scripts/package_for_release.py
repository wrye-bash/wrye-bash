#!/usr/bin/env python2.7-32
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
#  Wrye Bash copyright (C) 2005-2009 Wrye, 2010-2014 Wrye Bash Team
#  https://github.com/wrye-bash
#
# =============================================================================

"""Python script to package up the various Wrye Bash files into archives for
   release.  More detailed help can be found by passing the --help or -h
   command line arguments.

   It is assumed that if you have multiple version of Python installed on your
   computer, then you also have Python Launcher for Windows installed.  This
   will ensure that this script will be launched with the correct version of
   Python, via shebang lines.  Python Launcher for Windows comes with Python
   3.3+, but will need to be installed manually otherwise."""


# Imports ---------------------------------------------------------------------
import subprocess
import os
import shutil
import re
import sys
import argparse
import binascii
import textwrap
import traceback

# environment detection
try:
    #--Needed for the Installer version to find NSIS
    import _winreg
    have_winreg = True
except ImportError:
    have_winreg = False

try:
    #--Needed for the StandAlone version
    import py2exe
    have_py2exe = True
except:
    have_py2exe = False


# ensure we are in the correct directory so relative paths will work properly
scriptDir = os.path.dirname(unicode(sys.argv[0], sys.getfilesystemencoding()))
if scriptDir:
    os.chdir(scriptDir)
os.chdir(u'..')


# Setup some global paths that all functions will use
root = os.getcwdu()
scripts = os.path.join(root, u'scripts')
mopy = os.path.join(root, u'Mopy')
if sys.platform.lower().startswith('linux'):
    exe7z = u'7z'
else:
    exe7z = os.path.join(mopy, u'bash', u'compiled', u'7za.exe')
dest = os.path.join(scripts, u'dist')


def GetVersionInfo(version, padding=4):
    '''Gets generates version strings from the passed parameter.
       Returns the a string used for the 'File Version' property
       of the built WBSA.
       For example, a
       version of 291 would with default padding would return:
       ('291','0.2.9.1')'''
    file_version = (u'0.' * abs(padding))[:-1]

    v = version
    v = v.replace(u'.', u'')
    if padding < 0:
        file_version = u'.'.join(c for c in v.ljust(-padding, u'0'))
    else:
        file_version = u'.'.join(c for c in v.rjust(padding, u'0'))

    return file_version


def rm(file):
    """Removes a file if it exitsts"""
    if os.path.isfile(file): os.remove(file)


def mv(file, dest):
    """Moves a file if it exists"""
    if os.path.exists(file): shutil.move(file, dest)


def VerifyPy2Exe():
    """Checks for presense of the modified zipextimporter.py, which is required
       for building the WBSA"""
    path = os.path.join(sys.prefix, u'Lib', u'site-packages',
                        u'zipextimporter.py')
    with open(os.path.join(scripts, u'zipextimporter.py'), 'r') as ins:
        # 'r' vice 'rb', so line endings don't interfere
        crcGood = binascii.crc32(ins.read())
        crcGood &= 0xFFFFFFFFL
    with open(path, 'r') as ins:
        crcTest = binascii.crc32(ins.read())
        crcTest &= 0xFFFFFFFFL
    return crcGood == crcTest


def BuildManualVersion(version, pipe=None):
    """Creates the standard python manual install version"""
    archive = os.path.join(dest, 'Wrye Bash %s - Python Source.7z' % version)
    cmd_7z = [exe7z, 'a', '-mx9',
              # Skip repo management files
              '-xr!.svn', '-xr!.git*',
              # Skip compiled Python files
              '-xr!*.pyc', '-xr!*.pyo',
              # Skip other files that may get sucked in
              '-xr!bash.ini', '-xr!*.log', '-xr!desktop.ini', '-xr!thumbs.db',
              archive, 'Mopy']
    subprocess.call(cmd_7z, stdout=pipe, stderr=pipe)


def BuildStandaloneVersion(version, file_version, pipe=None):
    """Builds the standalone exe, packages into the standalone manual install
       version, then cleans up the extra files created."""
    if CreateStandaloneExe(version, file_version, pipe):
        PackStandaloneVersion(version, pipe)
        CleanupStandaloneFiles()


def CleanupStandaloneFiles():
    """Removes standalone exe files that are not needed after packaging"""
    rm(os.path.join(mopy, u'Wrye Bash.exe'))
    rm(os.path.join(mopy, u'w9xpopen.exe'))


def CreateStandaloneExe(version, file_version, pipe=None):
    """Builds the standalone exe"""
    # Check for build requirements
    if not have_py2exe:
        msg = " Could not find python module 'py2exe', aborting standalone creation."
        print msg
        print >> pipe, msg
        return False
    if not VerifyPy2Exe():
        msg = " You have not installed the replacement zipextimporter.py file.  Place it in <Python Path>\\Lib\\site-packages.  Aborting standalone creation."
        print msg
        print >> pipe, msg
        return False
    # Some paths we'll use
    wbsa = os.path.join(scripts, u'build', u'standalone')
    reshacker = os.path.join(wbsa, u'Reshacker.exe')
    upx = os.path.join(wbsa, u'upx.exe')
    icon = os.path.join(wbsa, u'bash.ico')
    manifest = os.path.join(wbsa, u'manifest.template')
    script = os.path.join(wbsa, u'setup.template')
    exe = os.path.join(mopy, u'Wrye Bash.exe')
    w9xexe = os.path.join(mopy, u'w9xpopen.exe')
    setup = os.path.join(mopy, u'setup.py')
    #--For l10n
    msgfmt = os.path.join(sys.prefix, u'Tools', u'i18n', u'msgfmt.py')
    pygettext = os.path.join(sys.prefix, u'Tools', u'i18n', u'pygettext.py')
    msgfmtTo = os.path.join(mopy, u'bash', u'msgfmt.py')
    pygettextTo = os.path.join(mopy, u'bash', u'pygettext.py')

    if not os.path.isfile(script):
        msg = " Could not find 'setup.template', aborting standalone creation."
        print msg
        print >> pipe, msg
        return False
    if not os.path.isfile(manifest):
        msg = " Could not find 'manifest.template', aborting standalone creation."
        print msg
        print >> pipe, msg
        return False

    # Read in the manifest file
    file = open(manifest, 'r')
    manifest = '"""\n' + file.read() + '\n"""'
    file.close()

    # Determine the extra includes needed (because py2exe wont automatically detect these)
    includes = []
    for file in os.listdir(os.path.join(mopy, u'bash', u'game')):
        if file.lower()[-3:] == u'.py':
            if file.lower() != u'__init__.py':
                includes.append("'bash.game.%s'" % file[:-3])
    includes = u','.join(includes)

    # Write the setup script
    file = open(script, 'r')
    script = file.read()
    script = script % dict(version=version, file_version=file_version,
                           manifest=manifest, upx=None, upx_compression='-9',
                           includes=includes,
                           )
    file.close()
    file = open(setup, 'w')
    file.write(script)
    file.close()

    # Copy the files needed for l10n
    shutil.copy(msgfmt, msgfmtTo)
    shutil.copy(pygettext, pygettextTo)

    # Call the setup script
    os.chdir(mopy)
    subprocess.call([setup, 'py2exe', '-q'], shell=True, stdout=pipe, stderr=pipe)
    os.chdir(root)

    # Clean up the l10n files
    rm(msgfmtTo)
    rm(pygettextTo)

    # Copy the exe's to the Mopy folder
    dist = os.path.join(mopy, u'dist')
    mv(os.path.join(dist, u'Wrye Bash Launcher.exe'), exe)
    mv(os.path.join(dist, u'w9xpopen.exe'), w9xexe)

    # Clean up the py2exe directories
    shutil.rmtree(dist)
    shutil.rmtree(os.path.join(mopy, u'build'))

    # Insert the icon
    subprocess.call([reshacker, '-addoverwrite', exe+',', exe+',',
                     icon+',', 'icon,', '101,', '0'], stdout=pipe, stderr=pipe)

    # Compress with UPX
    subprocess.call([upx, '-9', exe], stdout=pipe, stderr=pipe)
    subprocess.call([upx, '-9', w9xexe], stdout=pipe, stderr=pipe)

    # Clean up left over files
    rm(os.path.join(wbsa, u'ResHacker.ini'))
    rm(os.path.join(wbsa, u'ResHacker.log'))
    rm(setup)
    rm(os.path.join(mopy, u'Wrye Bash.upx'))

    return True


def PackStandaloneVersion(version, pipe=None):
    """Packages the standalone manual install version"""
    archive = os.path.join(dest, u'Wrye Bash %s - Standalone Executable.7z' % version)
    cmd_7z = [exe7z, 'a', '-mx9',
              # Skip repo management files
              '-xr!.svn', '-xr!.git*',
              # Skip compiled Python files
              '-xr!*.pyc', '-xr!*.pyo',
              # Skip other files that may get sucked in
              '-xr!bash.ini', '-xr!*.log', '-xr!desktop.ini', '-xr!thumbs.db',
              # WBSA: skip all Python files and batch files
              '-xr!*.py', '-xr!*.pyw', '-xr!*.bat',
              archive,
              'Mopy',
              ]
    subprocess.call(cmd_7z, stdout=pipe, stderr=pipe)


def BuildInstallerVersion(version, file_version, nsis=None, pipe=None):
    """Compiles the NSIS script, creating the installer version"""
    if not have_winreg and nsis is None:
        msg = " Could not find python module '_winreg', aborting installer creation."
        print msg
        print >> pipe, msg
        return

    script = os.path.join(scripts, u'build', u'installer', u'main.nsi')
    if not os.path.exists(script):
        msg = " Could not find nsis script '%s', aborting installer creation." % script
        print msg
        print >> pipe, msg
        return

    try:
        if nsis is None:
            # Need NSIS version 3.0+, so we can use the Inetc plugin
            # Older versions of NSIS 2.x key was located here:
            nsis = _winreg.QueryValue(_winreg.HKEY_LOCAL_MACHINE, r'Software\NSIS')
        inetc = os.path.join(nsis, u'Plugins', u'x86-unicode', u'inetc.dll')
        nsis = os.path.join(nsis, u'makensis.exe')
        if not os.path.isfile(nsis):
            msg = " Could not find 'makensis.exe', aborting installer creation."
            print msg
            print >> pipe, msg
            return
        if not os.path.isfile(inetc):
            msg = " Could not find NSIS Inetc plugin, aborting installer creation."
            print msg
            print >> pipe, msg
            return
        subprocess.call([nsis, '/NOCD',
                         '/DWB_NAME=Wrye Bash %s' % version,
                         '/DWB_FILEVERSION=%s' % file_version, script],
                        shell=True, stdout=pipe, stderr=pipe)
    except KeyboardInterrupt:
        raise
    except Exception as e:
        msg = " Error calling 'makensis.exe', aborting installer creation."
        print msg
        print >> pipe, msg
        traceback.print_exc(file=pipe)


def ShowTutorial():
    """Prints some additional information that may be needed to run this script
       that would be too much to fit into the default --help page."""
    wrapper = textwrap.TextWrapper()
    list = textwrap.TextWrapper(initial_indent=' * ',
                                subsequent_indent='   ',
                                replace_whitespace=False)
    listExt = textwrap.TextWrapper(initial_indent='   ',
                                   subsequent_indent='   ',
                                   replace_whitespace=False)
    lines = [
        '',
        wrapper.fill('''This is the packaging script for Wrye Bash. It can be used to build all versions of Wrye Bash that are released:'''),
        list.fill('''Manual install (archive) of the Python version'''),
        list.fill('''Manual install (archive) of the Standalone version'''),
        list.fill('''Automated Installer'''),
        '',
        wrapper.fill('''In addition to the default requirements to run Wrye Bash in Python mode, you will need four additional things:'''),
        list.fill('''NSIS: Used to create the Automated Installer. The latest 3.x release is recommended, as the instructions below for Inetc are based on 3.0.'''),
        list.fill('''Inetc: An NSIS plugin for downloading files, this is needed due to the Python website using redirects that the built in NSISdl plugin can not handle.  Get it from:'''),
        '',
        '   http://nsis.sourceforge.net/Inetc_plugin-in',
        '',
        listExt.fill('''And install by copying the provided unicode dll into your NSIS/Plugins/x86-unicode directory.'''),
        list.fill('''py2exe: Used to create the Standalone EXE.'''),
        list.fill('''Modified zipextimporter.py:  Copy the modified version from this directory into your Python's Lib\\site-packages directory.  This is needed for custom zipextimporter functionality that the Wrye Bash Standalone uses.'''),
        ]
    print '\n'.join(lines)


def main():
    parser = argparse.ArgumentParser(
        description='''
        Packaging script for Wrye Bash, used to create the release modules.

        If you need more detailed help beyond what is listed below, use the
        --tutorial or -t switch.

        This script requires at least Python 2.7.8 to run, due to improvements
        made to py2exe executables in regards to MSVC redistributable packages.
        ''',
        )
    parser.add_argument(
        '-r', '--release',
        default=None,
        action='store',
        type=str,
        dest='release',
        help='''Specifies the release number for Wrye Bash that you are
                packaging.''',
        )
    wbsa_group = parser.add_mutually_exclusive_group()
    wbsa_group.add_argument(
        '-w', '--wbsa',
        action='store_true',
        default=False,
        dest='wbsa',
        help='''Build and package the standalone version of Wrye Bash''',
        )
    wbsa_group.add_argument(
        '-e', '--exe',
        action='store_true',
        default=False,
        dest='exe',
        help='''Create the WBSA exe.  This option does not package it into the
                standalone archive.''',
        )
    parser.add_argument(
        '-m', '--manual',
        action='store_true',
        default=False,
        dest='manual',
        help='''Package the manual install Python version of Wrye Bash''',
        )
    parser.add_argument(
        '-i', '--installer',
        action='store_true',
        default=False,
        dest='installer',
        help='''Build the installer version of Wrye Bash.''',
        )
    parser.add_argument(
        '-a', '--all',
        action='store_true',
        default=False,
        dest='all',
        help='''Build and package all version of Wrye Bash. This is equivalent
                to -w -i -m''',
        )
    parser.add_argument(
        '-n', '--nsis',
        default=None,
        dest='nsis',
        help='''Specify the path to the NSIS root directory.  Use this if the
                script cannot locate NSIS automatically.''',
        )
    parser.add_argument(
        '-v', '--verbose',
        default=False,
        action='store_true',
        dest='verbose',
        help='''Verbose mode.  Directs output from 7z, py2exe, etc. to the
                console instead of the build log''',
        )
    parser.add_argument(
        '-t', '--tutorial',
        default=False,
        action='store_true',
        dest='tutorial',
        help='''Prints a more detailed description of requirements and things
                you need to know before building a release.''',
        )
    # Parse command line, show help if invalid arguments are present
    try:
        args, extra = parser.parse_known_args()
    except Exception as e:
        parser.print_help()
        return
    if len(extra) > 0:
        parser.print_help()
        return
    if args.tutorial:
        ShowTutorial()
        return
    if sys.version_info[0:3] < (2,7,8):
        print 'You must run at least Python 2.7.8 to use this script.'
        print 'Your Python:', sys.version
        return
    if not args.release:
        print 'No release version specified, please enter it now.'
        args.release = raw_input('>')

    print (sys.version)

    try:
        # If no build arguments passed, it's the same as --all
        if (not args.wbsa and not args.manual
            and not args.installer and not args.exe) or args.all:
            # Build everything
            args.wbsa = True
            args.manual = True
            args.installer = True

        file_version = GetVersionInfo(args.release)

        if args.verbose:
            pipe = None
        else:
            logFile = os.path.join(scripts, 'build.log')
            pipe = open(logFile, 'w')

        # clean and create distributable directory
        if os.path.exists(dest):
            shutil.rmtree(dest)
        os.makedirs(dest)

        if args.manual:
            msg = 'Creating Python archive distributable...'
            print msg
            print >> pipe, msg
            BuildManualVersion(args.release, pipe)

        exe_made = False
        if args.exe or args.wbsa or args.installer:
            msg = 'Building standalone exe...'
            print msg
            print >> pipe, msg
            exe_made = CreateStandaloneExe(args.release, file_version, pipe)

        if args.wbsa and exe_made:
            msg = 'Creating standalone distributable...'
            print msg
            print >> pipe, msg
            PackStandaloneVersion(args.release, pipe)

        if args.installer:
            msg = 'Creating installer distributable...'
            print msg
            print >> pipe, msg
            if exe_made:
                BuildInstallerVersion(args.release, file_version, args.nsis, pipe)
            else:
                msg = ' Standalone exe not found, aborting installer creation.'
                print msg
                print >> pipe, msg

        if not args.exe:
            # Clean up the WBSA exe's if necessary
            CleanupStandaloneFiles()
    except KeyboardInterrupt:
        msg = 'Build aborted by user.'
        print msg
        print >> pipe, msg

    if not args.verbose:
        pipe.close()


if __name__=='__main__':
    main()
