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
#  Wrye Bash copyright (C) 2005-2009 Wrye, 2010-2015 Wrye Bash Team
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
from __future__ import print_function

import glob
import subprocess
import os
import shutil
import sys
import argparse
import binascii
import textwrap
import traceback
import time

class NON_REPO(object):
    __slots__= []

    # 'Enum' for options for non-repo files
    MOVE = 'MOVE'
    COPY = 'COPY'
    NONE = 'NONE'

# environment detection
try:
    #--Needed for the Installer version to find NSIS
    import _winreg
except ImportError:
    _winreg = False

try:
    #--Needed for the StandAlone version
    import py2exe
except:
    py2exe = False

try:
    #--Needed to ensure non-repo file don't get packaged
    import git
    have_git = True
except:
    have_git = False


# ensure we are in the correct directory so relative paths will work properly
scriptDir = os.path.dirname(unicode(sys.argv[0], sys.getfilesystemencoding()))
if scriptDir:
    os.chdir(scriptDir)
os.chdir(u'..')


# Setup some global paths that all functions will use
root = os.getcwdu()
scripts = os.path.join(root, u'scripts')
mopy = os.path.join(root, u'Mopy')
apps = os.path.join(mopy, u'Apps')
if sys.platform.lower().startswith('linux'):
    exe7z = u'7z'
else:
    exe7z = os.path.join(mopy, u'bash', u'compiled', u'7z.exe')
dest = os.path.join(scripts, u'dist')

# global pipe file for log output
pipe = None


def GetVersionInfo(version, padding=4):
    """Gets generates version strings from the passed parameter.
       Returns the a string used for the 'File Version' property
       of the built WBSA.
       For example, a
       version of 291 would with default padding would return:
       ('291','0.2.9.1')"""
    v = version.split(u'.')
    if len(v) == 2:
        if len(v[1]) == 12 and float(v[1]) >= 201603171733L: # 2016/03/17 17:33
            v, v1 = v[:1], v[1]
            v.extend((v1[:4], v1[4:8], v1[8:]))
    # If version is too short, pad it with 0's
    abspad = abs(padding)
    delta = abspad - len(v)
    if delta > 0:
        pad = ['0'] * delta
        if padding > 0:
            v.extend(pad)
        else:
            v = pad + v
    # If version is too long, warn and truncate
    if delta < 0:
        lprint('WARNING: The version specified ({version}) has too many'
               ' version pieces.  The extra pieces will be truncated.'
               ''.format(version=version))
        v = v[:abspad]
    # Verify version pieces are actually integers, as non-integer values will
    # cause much of the 'Details' section of the built exe to be non-existant
    newv = []
    error = False
    for x in v:
        try:
            int(x)
            newv.append(x)
        except ValueError:
            error = True
            newv.append(u'0')
    if error:
        lprint('WARNING: The version specified ({version}) does not convert '
               'to integer values.'.format(version=version))
    file_version = u'.'.join(newv)
    lprint('Using file version:', file_version)
    return file_version


def rm(node):
    """Removes a file or directory if it exists"""
    if os.path.isfile(node): os.remove(node)
    elif os.path.isdir(node): shutil.rmtree(node)


def mv(node, dst):
    """Moves a file or directory if it exists"""
    if os.path.exists(node):
        shutil.move(node, dst)


def cpy(src, dst):
    """Moves a file to a destination, creating the target
       directory as needed."""
    if os.path.isdir(src):
        if not os.path.exists(dst):
            os.makedirs(dst)
    else:
        # file
        dstdir = os.path.dirname(dst)
        if not os.path.exists(dstdir):
            os.makedirs(dstdir)
        shutil.copy2(src, dst)


def lprint(*args, **kwdargs):
    """Helper function to print to both the build log file and the console.
       Needs the print function to work properly."""
    print(*args, **kwdargs)
    if pipe:
        kwdargs['file'] = pipe
        print('[package_for_release]:', *args, **kwdargs)
        pipe.flush()


def VerifyPy2Exe():
    """Checks for presense of the modified zipextimporter.py.  We no longer want
       the modified version, and need the original."""
    # CRCs of the correct version, from both 'r', and 'rb' mode
    crcGood = [0xA56E66A6, 0x57925DA8]
    path = os.path.join(sys.prefix, u'Lib', u'site-packages',
                        u'zipextimporter.py')
    # First we'll test using 'r' mode, this way if the line endings differ,
    # but the contents are the same, the crc will still be equal
    with open(os.path.join(scripts, u'zipextimporter.py'), 'r') as ins:
        crcBad = binascii.crc32(ins.read())
    crcBad &= 0xFFFFFFFFL
    with open(path, 'r') as ins:
        crcTest = binascii.crc32(ins.read())
    crcTest &= 0xFFFFFFFFL
    if crcTest == crcBad:
        # Definitely using the old modified version, need to reinstall
        return False
    if crcTest in crcGood:
        # Definitely using the un-modified version, good to go
        return True
    # Now check if the current file's crc in 'rb' mode matches a known "good"
    # crc.
    with open(path, 'rb') as ins:
        crcTest = binascii.crc32(ins.read())
    crcTest &= 0xFFFFFFFFL
    if crcTest in crcGood:
        # Definitely using the un-modified version
        return True
    # Last test: see if the modified lines are present
    with open(path, 'r') as ins:
        return 'filename = fullname.replace(".","\\")' in ins.read()


def PackManualVersion(args, all_files):
    """Creates the standard python manual install version"""
    version = args.version
    archive = os.path.join(dest, u'Wrye Bash %s - Python Source.7z' % version)
    listFile = os.path.join(dest, u'manual_list.txt')
    # We want every file for the manual version
    _pack7z(all_files, archive, listFile)


def _pack7z(all_files, archive, listFile):
    with open(listFile, 'wb') as out:
        for node in sorted(all_files, key=unicode.lower):
            out.write(node)
            out.write('\n')
    cmd_7z = [exe7z, 'a', '-mx9', archive, '@%s' % listFile]
    subprocess.call(cmd_7z, stdout=pipe, stderr=pipe)
    rm(listFile)


def CleanupStandaloneFiles():
    """Removes standalone exe files that are not needed after packaging"""
    rm(os.path.join(mopy, u'Wrye Bash.exe'))


def CreateStandaloneExe(args, file_version):
    """Builds the standalone exe"""
    # Check for build requirements
    if not py2exe:
        lprint(" Could not find python module 'py2exe', aborting standalone "
               "creation.")
        return False
    if not VerifyPy2Exe():
        lprint(" You have the replacement zipextimporter.py installed.  The "
               "replacement is not longer used.  Please re-install py2exe to"
               " get the original file back.")
        return False
    # Some paths we'll use
    wbsa = os.path.join(scripts, u'build', u'standalone')
    reshacker = os.path.join(wbsa, u'Reshacker.exe')
    upx = os.path.join(wbsa, u'upx.exe')
    icon = os.path.join(wbsa, u'bash.ico')
    manifest = os.path.join(wbsa, u'manifest.template')
    script = os.path.join(wbsa, u'setup.template')
    exe = os.path.join(mopy, u'Wrye Bash.exe')
    setup = os.path.join(mopy, u'setup.py')
    #--For l10n
    msgfmt = os.path.join(sys.prefix, u'Tools', u'i18n', u'msgfmt.py')
    pygettext = os.path.join(sys.prefix, u'Tools', u'i18n', u'pygettext.py')
    msgfmtTo = os.path.join(mopy, u'bash', u'msgfmt.py')
    pygettextTo = os.path.join(mopy, u'bash', u'pygettext.py')
    #--Output folders/files
    dist = os.path.join(mopy, u'dist')

    if not os.path.isfile(script):
        lprint(" Could not find 'setup.template', aborting standalone "
               "creation.")
    if not os.path.isfile(manifest):
        lprint(" Could not find 'manifest.template', aborting standalone "
               "creation.")
        return False

    # Read in the manifest file
    with open(manifest, 'r') as man:
        manifest = '"""\n' + man.read() + '\n"""'

    # Include the game package and subpackages (because py2exe wont
    # automatically detect these)
    packages = "'bash.game'" # notice the double quotes

    try:
        # Ensure comtypes is generated, so the required files for wx.lib.iewin
        # will get pulled in by py2exe
        lprint(' Generating comtypes...')
        try:
            import wx
            import wx.lib.iewin
        except ImportError:
            lprint(' ERROR: Could not import comtypes.  Aborting Standalone '
                   'creation.')
            return False
        # Write the setup script
        with open(script, 'r') as ins:
            script = ins.read()
        script = script % dict(version=args.version, file_version=file_version,
                               manifest=manifest, upx=None,
                               upx_compression='-9', packages=packages,
                               )
        with open(setup, 'w') as out:
            out.write(script)

        # Copy the l10n files over
        shutil.copy(msgfmt, msgfmtTo)
        shutil.copy(pygettext, pygettextTo)

        # Call the setup script
        os.chdir(mopy)
        lprint(' Calling py2exe...')
        subprocess.call([setup, 'py2exe', '-q'], shell=True, stdout=pipe,
                        stderr=pipe)
        os.chdir(root)

        # Copy the exe's to the Mopy folder
        mv(os.path.join(dist, u'Wrye Bash Launcher.exe'), exe)

        # Insert the icon
        lprint(' Adding icon...')
        subprocess.call([reshacker, '-addoverwrite', exe+',', exe+',',
                         icon+',', 'ICONGROUP,', 'MAINICON,', '0'], stdout=pipe,
                        stderr=pipe)
        # Also copy contents of ResHacker.log to the pipe file
        if pipe is not None:
            try:
                with open(os.path.join(wbsa, u'Reshacker.log'), 'r') as ins:
                    for line in ins:
                        print(line, file=pipe)
            except:
                # Don't care why it failed
                pass

        # Compress with UPX
        lprint(' Compressing with UPX...')
        subprocess.call([upx, '-9', exe], stdout=pipe, stderr=pipe)
    except:
        # On error, don't keep the built exe's
        rm(exe)
        raise
    finally:
        # Clean up left over files
        rm(msgfmtTo)
        rm(pygettextTo)
        rm(dist)
        rm(os.path.join(mopy, u'build'))
        rm(os.path.join(wbsa, u'ResHacker.ini'))
        rm(os.path.join(wbsa, u'ResHacker.log'))
        rm(setup)
        rm(os.path.join(mopy, u'Wrye Bash.upx'))

    return True


def PackStandaloneVersion(args, all_files):
    """Packages the standalone manual install version"""
    version = args.version
    archive = os.path.join(
                  dest,
                  u'Wrye Bash %s - Standalone Executable.7z' % version
                  )
    # We do not want any python files with the standalone
    # version, and we need to include the built EXEs
    all_files = [x for x in all_files
                 if os.path.splitext(x)[1].lower() not in (u'.py',
                                                           u'.pyw',
                                                           u'.pyd',
                                                           u'.bat',
                                                           u'.template')
                 ]
    all_files.append(u'Mopy\\Wrye Bash.exe')
    listFile = os.path.join(dest, u'standalone_list.txt')
    _pack7z(all_files, archive, listFile)


def RelocateNonRepoFiles(non_repo):
    """Moves any non-repository files/directories to scripts/temp"""
    tmpDir = os.path.join(u'scripts', u'temp')
    rm(tmpDir)
    os.makedirs(tmpDir)

    if non_repo:
        lprint(" Relocating non-repository files:")
    for path in non_repo:
        lprint(" ", path)
        src = os.path.join(mopy, path)
        dst = os.path.join(tmpDir, path)
        if os.path.isdir(src):
            shutil.move(src, dst)
        elif os.path.isfile(src):
            dirname = os.path.dirname(dst)
            if not os.path.exists(dirname):
                os.makedirs(dirname)
            shutil.move(src, dst)


def WarnNonRepoFiles(args, all_files):
    """Prints a warning if non-repository files are detected."""
    non_repo = GetNonRepoFiles(all_files)
    if non_repo:
        lprint(" WARNING: Non-repository files are present in your source "
               "directory.")
        if args.non_repo == NON_REPO.MOVE:
            lprint("          You have chosen to move the non-repository "
                   "files out of the source directory temporarily.")
        elif args.non_repo == NON_REPO.COPY:
            lprint("          You have chosen to make a temporary clean copy "
                   "of the repository to build with.")
        else:
            lprint("          You have chosen to not relocate them.  "
                   "These files will be included in the installer!")
            for file in non_repo:
                lprint(" ", file)
    return non_repo


def RestoreNonRepoFiles():
    """Returns non-repository files scripts/temp to their proper locations"""
    tmpDir = os.path.join(u'scripts', u'temp')
    if not os.path.exists(tmpDir):
        return
    failed = []
    if os.listdir(tmpDir):
        lprint(" Restoring non-repository files")
    for top, dirs, files in os.walk(tmpDir):
        for dir_ in dirs:
            src = os.path.join(top, dir_)
            dst = os.path.join(mopy, src[13:])
            if not os.path.isdir(dst):
                try:
                    os.makedirs(dst)
                except:
                    failed.append(src)
        for file_ in files:
            src = os.path.join(top, file_)
            dst = os.path.join(mopy, src[13:])
            try:
                shutil.move(src, dst)
            except:
                failed.append(src)
    if failed:
        lprint(" Failed to restore the following moved files:")
        for file_ in sorted(failed):
            lprint(" ", file_)
    else:
        try:
            rm(tmpDir)
        except:
            pass


def MakeTempRepoCopy(all_files):
    """Create a temporary copy of the necessary repository files to
       have a clean repository for building."""
    temp_root = os.path.join(scripts, u'build_temp')
    temp_scripts = os.path.join(temp_root, u'scripts')
    temp_nsis = os.path.join(temp_scripts, u'build', u'installer')
    nsis = os.path.join(scripts, u'build', u'installer')
    lprint(" Copying repository files to temporary location...")
    # Clean the destination
    if os.path.exists(temp_root):
        shutil.rmtree(temp_root)
    os.makedirs(temp_root)
    # Copy the NSIS scripts to the correct location
    shutil.copytree(nsis, temp_nsis)
    # Copy the repository files + WBSA files
    wbsa_files = [u'Mopy\\Wrye Bash.exe']
    for fname in all_files + wbsa_files:
        dst = os.path.join(temp_root, fname)
        src = os.path.join(root, fname)
        cpy(src, dst)
    return temp_root


def RemoveTempRepoCopy():
    """Deletes the temporary repository copy if present."""
    temp_root = os.path.join(scripts, u'build_temp')
    if os.path.exists(temp_root):
        shutil.rmtree(temp_root)


def BuildInstallerVersion(args, all_files, file_version):
    """Compiles the NSIS script, creating the installer version"""
    nsis = args.nsis
    if not _winreg and nsis is None:
        lprint(" Could not find python module '_winreg', aborting installer "
               "creation.")
        return

    rel_script = os.path.join(u'build', u'installer', u'main.nsi')
    script = os.path.join(scripts, rel_script)
    if not os.path.exists(script):
        lprint(" Could not find nsis script '%s', aborting installer "
               "creation." % script)
        return

    try:
        if nsis is None:
            # Need NSIS version 3.0+, so we can use the Inetc plugin
            # Older versions of NSIS 2.x key was located here:
            nsis = _winreg.QueryValue(_winreg.HKEY_LOCAL_MACHINE,
                                      r'Software\NSIS')
        inetc = os.path.join(nsis, u'Plugins', u'x86-unicode', u'inetc.dll')
        nsis = os.path.join(nsis, u'makensis.exe')
        if not os.path.isfile(nsis):
            lprint(" Could not find 'makensis.exe', aborting installer "
                   "creation.")
            return
        if not os.path.isfile(inetc):
            lprint(" Could not find NSIS Inetc plugin, aborting installer "
                   "creation.")
            return

        try:
            non_repo = WarnNonRepoFiles(args, all_files)
            clean_mopy_dir = mopy
            if non_repo:
                if args.non_repo == NON_REPO.MOVE:
                    RelocateNonRepoFiles(non_repo)
                elif args.non_repo == NON_REPO.COPY:
                    temp_root = MakeTempRepoCopy(all_files)
                    script = os.path.join(temp_root, u'scripts', rel_script)
                    clean_mopy_dir = os.path.join(temp_root, u'Mopy')
            clean_mopy_dir = os.path.relpath(clean_mopy_dir, os.getcwd())

            # Build the installer
            lprint(" Calling makensis.exe...")
            ret = subprocess.call([nsis, '/NOCD',
                                   '/DWB_NAME=Wrye Bash %s' % args.version,
                                   '/DWB_FILEVERSION=%s' % file_version,
                                   # pass the correct mopy dir for the script
                                   # to copy the right files in the installer
                                   '/DWB_CLEAN_MOPY=%s' % clean_mopy_dir,
                                   script],
                                  shell=True, stdout=pipe, stderr=pipe)
            if ret != 0:
                lprint(' makensis exited with error code %s.  Check the output'
                       ' log for errors in the NSIS script.' % ret)
        finally:
            if args.non_repo == NON_REPO.MOVE:
                RestoreNonRepoFiles()
            elif args.non_repo == NON_REPO.COPY:
                RemoveTempRepoCopy()
    except KeyboardInterrupt:
        raise
    except Exception as e:
        lprint(" Error calling creating installer, aborting creation.")
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
        wrapper.fill('This is the packaging script for Wrye Bash. It can be '
                     'used to build all versions of Wrye Bash that are '
                     'released:'),
        list.fill('''Manual install (archive) of the Python version'''),
        list.fill('''Manual install (archive) of the Standalone version'''),
        list.fill('''Automated Installer'''),
        '',
        wrapper.fill('In addition to the default requirements to run Wrye Bash'
                     ' in Python mode, you will need five additional things:'),
        list.fill('NSIS: Used to create the Automated Installer. The latest '
                  '3.x release is recommended, as the instructions below for '
                  'Inetc are based on 3.0.'''),
        list.fill('Inetc: An NSIS plugin for downloading files, this is needed'
                  ' due to the Python website using redirects that the built '
                  'in NSISdl plugin can not handle.  Get it from:'),
        '',
        '   http://nsis.sourceforge.net/Inetc_plug-in',
        '',
        listExt.fill('And install by copying the provided unicode dll into '
                     'your NSIS/Plugins/x86-unicode directory.'),
        list.fill('''py2exe: Used to create the Standalone EXE.'''),
        list.fill('Modified zipextimporter.py:  Copy the modified version from'
                  " this directory into your Python's Lib\\site-packages "
                  'directory.  This is needed for custom zipextimporter '
                  'functionality that the Wrye Bash Standalone uses.'),
        list.fill('GitPython: This is used to parse the repository information'
                  ' to ensure non-repo files are not included in the built'
                  ' packages.  Get version 0.2.0 or newer. In addition, this '
                  'script needs to be able to locate your git executable.  Do '
                  'this by either adding its directory to the PATH environment'
                  ' variable, or passing the directory via the --git command '
                  'line argument.'),
        '',
        '   https://pypi.python.org/pypi/GitPython/',
        ''
        ]
    print(*lines, sep='\n')


def GetGitFiles(gitDir, version):
    """Using git.exe, parses the repository information to get a list of all
       files that belong in the repository.  Returns a dict of files with paths
       relative to the Mopy directory, which can be used to ensure no non-repo
       files get included in the installers.  This function will also print a
       warning if there are non-committed changes.

       The dictionary format is: ##: not a bad idea but for now a list
       { case_insensitive_file_name: real_file_name}
       :return: a list of all paths that git tracks plus Mopy/Apps (
       preserves case)
    """
    # First, ensure GitPython will be able to call git.  On windows, this means
    # ensuring that the Git/bin directory is in the PATH variable.
    if not have_git:
        lprint("ERROR: Could not locate GitPython.")
        return False

    try:
        if sys.platform == 'win32':
            # Windows, check all the PATH options first
            for path in os.environ['PATH'].split(u';'):
                if os.path.isfile(os.path.join(path, u'git.exe')):
                    # Found, no changes necessary
                    break
            else:
                # Not found in PATH, try user supplied directory, as well as
                # common install paths
                pfiles = os.path.join(os.path.expandvars(u'%PROGRAMFILES%'),
                                      u'Git', u'bin')
                if u'(x86)' in pfiles:
                    # On a 64-bit system, running 32-bit Python, there is
                    # no environment variable that expands to the 64-bit
                    # program files location, so do a hacky workaround
                    pfilesx64 = pfiles.replace(u'Program Files (x86)',
                                               u'Program Files')
                else:
                    pfilesx64 = None
                for path in (gitDir, pfiles, pfilesx64):
                    if path is None:
                        continue
                    if os.path.isfile(os.path.join(path, u'git.exe')):
                        # Found it, put the path into PATH
                        os.environ['PATH'] += ';' + path
                        break
        # Test out if git can be launched now
        try:
            with open(os.devnull, 'wb') as devnull:
                subprocess.Popen('git', stdout=devnull, stderr=devnull)
        except:
            lprint('ERROR: Could not locate git.  Try adding the path to your'
                   ' git directory to the PATH environment variable.')
            return False

        # Git is working good, now use it
        repo = git.Repo()
        if repo.is_dirty():
            lprint('WARNING: Your wrye-bash repository is dirty (you have '
                   'uncommitted changes).')
        branchName = repo.active_branch.name.lower()
        if (not branchName.startswith('rel-') or
            not branchName.startswith('release-') or
            not version in branchName):
            lprint('WARNING: You are building off branch "%s", which does not'
                   ' appear to be a release branch for %s.'
                   % (branchName, version))
        else:
            lprint('Building from branch "%s".' % branchName)
        files = [unicode(os.path.normpath(x.path))
                 for x in repo.tree().traverse()
                 if x.path.lower().startswith(u'mopy')
                    and os.path.isfile(x.path)
                 ]
        # Special case: we want the Apps folder to be included, even though
        # it's not in the repository
        files.append(os.path.join(u'Mopy', u'Apps'))
        return files
    except:
        lprint('An error occurred while attempting to interface with '
               'git.')
        traceback.print_exc(file=pipe)
        return False


def GetNonRepoFiles(repo_files):
    """Return a list of all files in the Mopy folder that should not be
       included in the installer.  This list can be used to temporarily
       remove these files prior to running the NSIS scripts.
    """
    non_repo = []
    # Get a list of every directory and file actually present
    mopy_files = []
    mopy_dirs = []
    for root, dirs, files in os.walk(u'Mopy'):
        mopy_files.extend((os.path.join(root, x) for x in files))
        mopy_dirs.extend((os.path.join(root, x) for x in dirs))
    mopy_files = (os.path.normpath(x) for x in mopy_files)
    # We can ignore .pyc and .pyo files, since the NSIS scripts skip those
    mopy_files = (x for x in mopy_files
                 if os.path.splitext(x)[1].lower() not in (u'.pyc', u'.pyo'))
    # We can also ignore Wrye Bash.exe, for the same reason
    mopy_files = (x for x in mopy_files
                 if os.path.basename(x).lower() != u'wrye bash.exe')
    mopy_dirs = (os.path.normpath(x) for x in mopy_dirs)
    # Pick out every file that doesn't belong
    non_repo.extend((x for x in mopy_files if x not in set(repo_files)))
    # Pick out every directory that doesn't contain repo files
    non_repo_dirs = []
    for mopy_dir in mopy_dirs:
        for tracked_file in repo_files:
            if tracked_file.lower().startswith(mopy_dir.lower()):
                # It's good to keep
                break
        else:
            # It's not good to keep
            # Insert these at the beginning so they get handled first when
            # relocating
            non_repo_dirs.append(mopy_dir)
    if non_repo_dirs:
        non_repo_dirs.sort(key=unicode.lower)
        parent_dir = non_repo_dirs[0][5:]
        parent_dirs, parent_dir = [parent_dir], parent_dir.lower()
        for skip_dir in non_repo_dirs[1:]:
            new_parent = skip_dir[5:]
            if new_parent.lower().startswith(parent_dir):
                if new_parent[len(parent_dir)] == os.sep:
                    continue # subdir keep only the top level dir
            parent_dirs.append(new_parent)
            parent_dir = new_parent.lower()
    else: parent_dirs = []
    # Lop off the "mopy/" part
    non_repo = (x[5:] for x in non_repo)
    tuple_parent_dirs = tuple(d.lower() + os.sep for d in parent_dirs)
    non_repo = [x for x in non_repo if not x.lower().startswith(tuple_parent_dirs)]
    # Insert parent_dirs at the beginning so they get handled first when relocating
    non_repo = parent_dirs + non_repo
    return non_repo


def main():
    parser = argparse.ArgumentParser(
        description='''
        Packaging script for Wrye Bash, used to create the release modules.

        If you need more detailed help beyond what is listed below, use the
        --tutorial or -t switch.

        You must use at least Python 2.7.12.
        ''',
        )
    parser.add_argument(
        '-r', '--release',
        default=None,
        action='store',
        type=str,
        dest='version',
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
        '-g', '--git',
        default=None,
        dest='git',
        help='''Specify the path to the git bin directory.  Use this if the
                script cannot locate git automatically.''',
        )
    parser.add_argument(
        '--non-repo',
        default=NON_REPO.MOVE,
        action='store',
        choices=[NON_REPO.MOVE, NON_REPO.COPY, NON_REPO.NONE],
        help='''If non-repository files are detected during packaging the
        *installer* version, the packaging script will deal with them in the
        following way: {MOVE} - move the non-repository files out of the
        source directory, then restore them after (recommended).  {COPY} -
        make a copy of the repository files into a temporary directory,
        then build from there (slower).  {NONE} - do nothing, causing those
        files to be included in the installer(HIGHLY DISCOURAGED).'''.format(
            COPY=NON_REPO.COPY, MOVE=NON_REPO.MOVE, NONE=NON_REPO.NONE),
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
        '-l', '--view-logfile',
        default=False,
        action='store_true',
        dest='view_log',
        help='''If specified, and verbose mode is not enabled, opens the log
                file for viewing after completion of the packaging script.''',
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
    except SystemExit as e:
        if e.code: parser.print_help()
        return
    if len(extra) > 0:
        parser.print_help()
        return
    if args.tutorial:
        ShowTutorial()
        return
    if sys.version_info[0:3] < (2, 7, 12):
        lprint('You must run at least Python 2.7.12 to use this script.')
        lprint('Your Python:', sys.version)
        return
    if not args.version:
        print('No release version specified, please enter it now.')
        args.version = raw_input('>')

    print (sys.version)

    # See if Mopy/Apps is already present, if it is, we won't
    # remove it at the end
    appsPresent = os.path.isdir(apps)

    global pipe
    try:
        # Setup output log
        if args.verbose:
            pipe = None
        else:
            logFile = os.path.join(scripts, 'build.log')
            pipe = open(logFile, 'w')

        # If no build arguments passed, it's the same as --all
        if (not args.wbsa and not args.manual
            and not args.installer and not args.exe) or args.all:
            # Build everything
            args.wbsa = True
            args.manual = True
            args.installer = True

        # Create the Mopy/Apps folder if it's not present
        if appsPresent:
            apps_temp = os.path.join(scripts, u'apps_temp')
            rm(apps_temp)
            os.makedirs(apps_temp)
            lprint('Moving your Apps folder to %s' % apps_temp)
            shutil.move(apps, apps_temp)
        os.makedirs(apps)

        # Get repository files
        all_files = GetGitFiles(args.git, args.version)
        if all_files is False:
            lprint('GitPython is not set up correctly, aborting.')
            return

        # Add the LOOT API binaries to all_files
        all_files.append(os.path.join(u'Mopy', u'loot_api.dll'))
        all_files.append(os.path.join(u'Mopy', u'loot_api.pyd'))

        file_version = GetVersionInfo(args.version)

        # clean and create distributable directory
        if os.path.exists(dest):
            shutil.rmtree(dest)
        try:
            # Sometimes in Windows, if the dist directory was open in Windows
            # Explorer, this will cause an OSError: Accessed Denied, while
            # Explorer is renavigating as a result of the deletion.  So just
            # wait a second and try again.
            os.makedirs(dest)
        except OSError:
            time.sleep(1)
            os.makedirs(dest)

        if args.manual:
            lprint('Creating Python archive distributable...')
            PackManualVersion(args, all_files)

        exe_made = False

        if args.exe or args.wbsa or args.installer:
            lprint('Building standalone exe...')
            exe_made = CreateStandaloneExe(args, file_version)

        if args.wbsa and exe_made:
            lprint('Creating standalone distributable...')
            PackStandaloneVersion(args, all_files)

        if args.installer:
            lprint('Creating installer distributable...')
            if exe_made:
                BuildInstallerVersion(args, all_files, file_version)
            else:
                lprint(' Standalone exe not found, aborting installer '
                       'creation.')

    except KeyboardInterrupt:
        lprint('Build aborted by user.')
    except Exception as e:
        print('Error:', e)
        traceback.print_exc()
    finally:
        # Clean up Mopy/Apps if it was not present to begin with
        if appsPresent:
            backapps = os.path.join(apps_temp, u'Apps')
            for lnk in glob.glob(backapps + os.sep + u'*'):
                shutil.copy(lnk, os.path.join(mopy, u'Apps'))
            # shutil.move(backapps, mopy)
            rm(apps_temp)
        else: rm(apps)
        if not args.exe:
            # Clean up the WBSA exe's if necessary
            CleanupStandaloneFiles()

        if not args.verbose:
            if pipe:
                pipe.close()
                if args.view_log:
                    os.startfile(logFile)


if __name__=='__main__':
    main()
