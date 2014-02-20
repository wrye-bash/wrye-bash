#!/usr/bin/env python
# -*- coding: utf-8 -*-

# Python script to package up the the various Wrye Bash
# files into archives for release.
import subprocess
import os
import shutil
import re
import sys
import optparse
import binascii

sys.path.append( '../Mopy/bash' ) #Bad general practice, don't do this in a production app. We're fudging here for expediency.
import bass

# ensure we are in the correct directory so relative paths will work properly
scriptDir = os.path.dirname(unicode(sys.argv[0], sys.getfilesystemencoding()))
if scriptDir:
    os.chdir(scriptDir)
os.chdir("..")


# Some paths
root = os.getcwd()
scripts = os.path.join(root, 'scripts')
mopy = os.path.join(root, 'Mopy')
if sys.platform.lower().startswith("linux"):
    exe7z = '7z'
else:
    exe7z = os.path.join(mopy, 'bash', 'compiled', '7z.exe')
dest = os.path.join(scripts, 'dist')


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


#--GetVersionInfo: Gets version information about Wrye Bash
def GetVersionInfo(padding=4):
    '''Gets version information from Mopy\bash\bass.py, returns
       a tuple: (version, file_version).  For example, a
       version of 291 would with default padding would return:
       ('291','0.2.9.1')'''

    version = bass.AppVersion
    file_version = ('0.'*abs(padding))[:-1]

    v = version
    v = v.replace('.','')
    if padding < 0:
        file_version = '.'.join(c for c in v.ljust(-padding,'0'))
    else:
        file_version = '.'.join(c for c in v.rjust(padding,'0'))

    return version,file_version

#--rm: Removes a file if it exists
def rm(file):
    if os.path.exists(file): os.remove(file)

#--mv: Moves a file if it exists
def mv(file, dest):
    if os.path.exists(file): shutil.move(file, dest)

#--Check for presense of modified zipextimporter.py, required for WBSA
def VerifyPy2Exe():
    pythonPath = sys.executable
    pythonRoot,pythonExe = os.path.split(pythonPath)
    path = os.path.join(pythonRoot,u'Lib',u'site-packages',u'zipextimporter.py')
    with open(os.path.join(scripts,u'zipextimporter.py'),'r') as ins:
        # 'r' vice 'rb', so line endings don't interfere
        crcGood = binascii.crc32(ins.read())
        crcGood &= 0xFFFFFFFFL
    with open(path,'r') as ins:
        crcTest = binascii.crc32(ins.read())
        crcTest &= 0xFFFFFFFFL
    return crcGood == crcTest

#--Create the standard manual installer version
def BuildManualVersion(version, pipe=None):
    archive = os.path.join(dest, 'Wrye Bash %s - Python Source.7z' % version)
    cmd_7z = [exe7z, 'a', '-mx9', '-xr!.svn', '-xr!Microsoft.VC80.CRT', '-xr!*.pyc', '-xr!*.pyo', archive,'Mopy']
    subprocess.call(cmd_7z, stdout=pipe, stderr=pipe)

#--Create the StandAlone version
def BuildStandaloneVersion(version, file_version, pipe=None):
    if CreateStandaloneExe(version, file_version, pipe):
        PackStandaloneVersion(version, pipe)
        CleanupStandaloneFiles()

def CleanupStandaloneFiles():
    rm(os.path.join(mopy, 'Wrye Bash.exe'))
    rm(os.path.join(mopy, 'w9xpopen.exe'))

#--Create just the exe for the StandAlone veresion
def CreateStandaloneExe(version, file_version, pipe=None):
    if not have_py2exe:
        print " Could not find python module 'py2exe', aborting StandAlone creation."
        print >> pipe, " Could not find python module 'py2exe', aborting StandAlone creation."
        return False
    if not VerifyPy2Exe():
        print " You have not installed the replacement zipextimporter.py file.  Place it in <Python Path>\\Lib\\site-packages."
        print >> pipe, " You have not installed the replacement zipextimporter.py file.  Place it in <Python Path>\\Lib\\site-packages."
        return False
    wbsa = os.path.join(scripts, 'build', 'standalone')
    reshacker = os.path.join(wbsa, 'Reshacker.exe')
    upx = os.path.join(wbsa, 'upx.exe')
    icon = os.path.join(wbsa, 'bash.ico')
    manifest = os.path.join(wbsa, 'manifest.template')
    script = os.path.join(wbsa, 'setup.template')
    exe = os.path.join(mopy, 'Wrye Bash.exe')
    w9xexe = os.path.join(mopy, 'w9xpopen.exe')
    setup = os.path.join(mopy, 'setup.py')
    #--For l10n
    msgfmt = os.path.join(sys.prefix,'Tools','i18n','msgfmt.py')
    pygettext = os.path.join(sys.prefix,'Tools','i18n','pygettext.py')
    msgfmtTo = os.path.join(mopy,'bash','msgfmt.py')
    pygettextTo = os.path.join(mopy,'bash','pygettext.py')

    if not os.path.exists(script):
        print " Could not find 'setup.template', aborting StandAlone creation."
        print >> pipe, " Could not find 'setup.template', aborting StandAlone creation."
        return False

    if os.path.exists(manifest):
        file = open(manifest, 'r')
        manifest = '"""\n' + file.read() + '\n"""'
        file.close()
    else:
        print " Could not find 'manifest.template', the StandAlone will look OLD (Windows 9x style)."
        print >> pipe, " Could not find 'manifest.template', the StandAlone will look OLD (Windows 9x style)."
        manifest = None

    # Determine the extra includes needed (because py2exe wont automatically detect these)
    includes = []
    for file in os.listdir(os.path.join(mopy,'bash','game')):
        if file.lower()[-3:] == '.py':
            if file.lower() != '__init__.py':
                includes.append("'bash.game.%s'" % file[:-3])
    includes = ','.join(includes)

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
    shutil.copy(msgfmt,msgfmtTo)
    shutil.copy(pygettext,pygettextTo)
    
    # Call the setup script
    os.chdir(mopy)
    subprocess.call([setup, 'py2exe', '-q'], shell=True, stdout=pipe, stderr=pipe)
    os.chdir(root)

    # Clean up the l10n files
    rm(msgfmtTo)
    rm(pygettextTo)

    # Copy the exe's to the Mopy folder
    dist = os.path.join(mopy, 'dist')
    mv(os.path.join(dist, 'Wrye Bash Launcher.exe'), exe)
    mv(os.path.join(dist, 'w9xpopen.exe'), w9xexe)
    
    # Clean up the py2exe directories
    shutil.rmtree(dist)
    shutil.rmtree(os.path.join(mopy, 'build'))
    
    # Insert the icon
    subprocess.call([reshacker, '-addoverwrite', exe+',', exe+',',
                     icon+',', 'icon,', '101,', '0'], stdout=pipe, stderr=pipe)

    # Compress with UPX
    subprocess.call([upx, '-9', exe], stdout=pipe, stderr=pipe)
    subprocess.call([upx, '-9', w9xexe], stdout=pipe, stderr=pipe)
    
    # Clean up left over files
    rm(os.path.join(wbsa, 'ResHacker.ini'))
    rm(os.path.join(wbsa, 'ResHacker.log'))
    rm(setup)
    rm(os.path.join(mopy, 'Wrye Bash.upx'))

    return True


#--Package up all the files for the StandAlone version    
def PackStandaloneVersion(version, pipe=None):
    archive = os.path.join(dest, 'Wrye Bash %s - Standalone Executable.7z' % version)
    cmd_7z = [exe7z, 'a', '-mx9',
              '-xr!.svn',   # Skip '.svn' dirs
              '-xr!Microsoft.VC80.CRT', # Skip MSVC runtime for the manual archive install
              '-xr!*.py', '-xr!*.pyc', '-xr!*.pyw', '-xr!*.bat', # Skip python source
              archive,
              'Mopy',
              ]
    subprocess.call(cmd_7z, stdout=pipe, stderr=pipe)

#--Compile the NSIS script
def BuildInstallerVersion(version, file_version, nsis=None, pipe=None):
    if not have_winreg and nsis is None:
        print " Could not find python module '_winreg', aborting Installer creation."
        print >> pipe, " Could not find python module '_winreg', aborting Installer creation."
        return

    script = os.path.join(scripts, 'build', 'Wrye Bash.nsi')
    if not os.path.exists(script):
        print " Could not find nsis script '%s', aborting Installer creation." % script
        print >> pipe, " Could not find nsis script '%s', aborting Installer creation." % script
        return

    try:
        if nsis is None:
            nsis = _winreg.QueryValue(_winreg.HKEY_LOCAL_MACHINE, r'Software\NSIS\Unicode')
        nsis = os.path.join(nsis, 'makensis.exe')
        subprocess.call([nsis, '/NOCD', '/DWB_NAME=Wrye Bash %s' % version, '/DWB_FILEVERSION=%s' % file_version, script], shell=True, stdout=pipe, stderr=pipe)
    except:
        print " Could not find 'makensis.exe', aborting Installer creation."
        print >> pipe, " Could not find 'makensis.exe', aborting Installer creation."


if __name__ == '__main__':
    parser = optparse.OptionParser()
    parser.add_option('-w', '--wbsa',
                        action='store_true',
                        default=False,
                        dest='wbsa',
                        help='Build and package the standalone version of Wrye Bash'
                        )
    parser.add_option('-e', '--exe',
                        action='store_true',
                        default=False,
                        dest='exe',
                        help="Create the WBSA exe, but don't package it into an archive."
                        )
    parser.add_option('-m', '--manual',
                        action='store_true',
                        default=False,
                        dest='manual',
                        help='Package the manual version of Wrye Bash'
                        )
    parser.add_option('-i', '--installer',
                        action='store_true',
                        default=False,
                        dest='installer',
                        help='Build the installer version of Wrye Bash'
                        )
    parser.add_option('-n', '--nsis',
                        default=None,
                        dest='nsis',
                        help='Specify the path to the NSIS root directory.  Use this if pywin32 is not installed.'
                        )
    parser.add_option('-v', '--verbose',
                        default=False,
                        action='store_true',
                        dest='verbose',
                        help='verbose mode, direct output from 7z, py2exe, etc. to the console instead of the build log'
                        )
    try:
        args, extra = parser.parse_args()
    except:
        parser.print_help()
        exit(1)

    if len(extra) > 0:
        parser.print_help()
        exit(1)

    if not args.wbsa and not args.manual and not args.installer and not args.exe:
        # No arguments specified, build them all
        args.wbsa = True
        args.manual = True
        args.installer = True

    version, file_version = GetVersionInfo()

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
        print 'Creating archive distributable...'
        print >> pipe, 'Creating archive distributable...'
        BuildManualVersion(version, pipe)

    exe_made = False
    if args.exe or args.wbsa or args.installer:
        print 'Building standalone exe...'
        print >> pipe, 'Building standalone exe...'
        exe_made = CreateStandaloneExe(version, file_version, pipe)

    if args.wbsa and exe_made:
        print 'Creating standalone distributable...'
        print >> pipe, 'Creating standalone distributable...'
        PackStandaloneVersion(version, pipe)

    if args.installer and exe_made:
        print 'Creating installer distributable...'
        print >> pipe, 'Creating installer distributable...'
        BuildInstallerVersion(version, file_version, args.nsis, pipe)

    if not args.exe:
        # Clean up the WBSA exe's if necessary
        CleanupStandaloneFiles()

    if not args.verbose:
        pipe.close()
