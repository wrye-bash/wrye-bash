# Python script to package up the the various Wrye Bash
# files into archives for release.
import subprocess
import os
import shutil
import re
import sys
import optparse

# Some paths
root = os.getcwd()
mopy = os.path.join(root,'Mopy')
exe7z = os.path.join(mopy,'bash','compiled','7z.exe')
readme = os.path.join(mopy,'Wrye Bash.txt')

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
def GetVersionInfo(readme=readme, padding=4):
    '''Gets version information from Wrye Bash.txt, returns
       a tuple: (version, file_version).  For example, a
       version of 291 would with default padding would return:
       ('291','0.2.9.1')

       padding: number of digits to padd the file_version to,
          using zeroes.  If padding is less than 0, the padding
          will be added to the end, otherwise it will be added
          to the front
    '''
    version = 'SVN'
    file_version = ('0.'*abs(padding))[:-1]

    if os.path.exists(readme):
        file = open(readme, 'r')
        reVersion = re.compile('^=== ([\.\d]+) \[')
        for line in file:
            maVersion = reVersion.match(line)
            if maVersion:
                version = maVersion.group(1)
                if padding < 0:
                    file_version = '.'.join(c for c in version.ljust(-padding,'0'))
                else:
                    file_version = '.'.join(c for c in version.rjust(padding,'0'))
                break
    return version,file_version

#--rm: Removes a file if it exists
def rm(file):
    if os.path.exists(file): os.remove(file)

#--mv: Moves a file if it exists
def mv(file, dest):
    if os.path.exists(file): shutil.move(file, dest)


#--Create the standard manual installer version
def BuildManualVersion(version, pipe=None):
    archive = 'Wrye Bash %s -- Archive Version.7z' % version
    cmd_7z = [exe7z, 'a', '-mx9', '-xr!.svn', archive, 'Mopy', 'Data']
    rm(archive)
    subprocess.call(cmd_7z, stdout=pipe, stderr=pipe)

#--Create the StandAlone version
def BuildStandaloneVersion(version, file_version, pipe=None):
    if CreateStandaloneExe(version, file_version, pipe):
        PackStandaloneVersion(version, pipe)
        CleanupStandaloneFiles()

def CleanupStandaloneFiles():
    rm(os.path.join(mopy, 'Wrye Bash.exe'))
    rm(os.path.join(mopy, 'w9xpopen.exe'))

#--Creat just the exe(s) for the StandAlone veresion
def CreateStandaloneExe(version, file_version, pipe=None):
    if not have_py2exe:
        print " Could not find python module 'py2exe', aborting StandAlone creation."
        return False
    wbsa = os.path.join(root, 'experimental', 'standalone')
    reshacker = os.path.join(wbsa, 'Reshacker.exe')
    upx = os.path.join(wbsa, 'upx.exe')
    icon = os.path.join(wbsa, 'bash.ico')
    manifest = os.path.join(wbsa, 'manifest.template')
    script = os.path.join(wbsa, 'setup.template')
    exe = os.path.join(mopy, 'Wrye Bash.exe')

    if not os.path.exists(script):
        print " Could not find 'setup.template', aborting StandAlone creation."
        return False

    if os.path.exists(manifest):
        file = open(manifest, 'r')
        manifest = '"""\n' + file.read() + '\n"""'
        file.close()
    else:
        print " Could not find 'manifest.template', the StandAlone will look OLD (Windows 9x style)."
        manifest = None
    
    # Write the setup script
    file = open(script, 'r')
    script = file.read()
    script = script % dict(version=version, file_version=file_version,
                           manifest=manifest, upx=None, upx_compression='-9'
                           )
    file.close()
    file = open(os.path.join(mopy, 'setup.py'), 'w')
    file.write(script)
    file.close()
    
    # Call the setup script
    os.chdir(mopy)
    subprocess.call([os.path.join(mopy, 'setup.py'), 'py2exe', '-q'], shell=True, stdout=pipe, stderr=pipe)
    os.chdir(root)

    # Copy the exe's to the Mopy folder
    mv(os.path.join(mopy, 'dist', 'Wrye Bash Launcher.exe'), exe)
    mv(os.path.join(mopy, 'dist', 'w9xpopen.exe'),
       os.path.join(mopy, 'w9xpopen.exe'))
    
    # Clean up the py2exe directories
    shutil.rmtree(os.path.join(mopy, 'dist'))
    shutil.rmtree(os.path.join(mopy, 'build'))
    
    # Insert the icon
    subprocess.call([reshacker, '-addoverwrite', exe+',', exe+',',
                     icon+',', 'icon,', '101,', '0'], stdout=pipe, stderr=pipe)

    # Compress with UPX
    subprocess.call([upx, '-9', exe])
    subprocess.call([upx, '-9', os.path.join(mopy, 'w9xpopen.exe')])
    
    # Clean up left over files
    rm(os.path.join(wbsa, 'ResHacker.ini'))
    rm(os.path.join(wbsa, 'ResHacker.log'))
    rm(os.path.join(mopy, 'setup.py'))
    rm(os.path.join(mopy, 'Wrye Bash.upx'))
    return True

#--Package up all the files for the StandAlone version    
def PackStandaloneVersion(version, pipe=None):
    archive = 'Wrye Bash %s -- Standalone Version.7z' % version

    cmd_7z = [exe7z, 'a', '-mx9',
              '-xr!.svn',   # Skip '.svn' dirs
              '-xr!*.py', '-xr!*.pyc', '-xr!*.pyw', # Skip python files
              archive,
              'Data',
              'Mopy',
              ]
    rm(archive)
    subprocess.call(cmd_7z, stdout=pipe, stderr=pipe)

#--Compile the NSIS script
def BuildInstallerVersion(version, file_version, nsis=None, pipe=None):
    if not have_winreg and nsis is None:
        print " Could not find python module '_winreg', aborting Installer creation."
        return

    script = 'Wrye Bash.nsi'
    if not os.path.exists(script):
        print " Could not find nsis script '%s', aborting Installer creation." % script
        return

    try:
        if nsis is None:
            nsis = _winreg.QueryValue(_winreg.HKEY_LOCAL_MACHINE, r'Software\NSIS')
        nsis = os.path.join(nsis, 'makensis.exe')
        subprocess.call([nsis, '/DWB_NAME=Wrye Bash %s' % version, '/DWB_FILEVERSION=%s' % file_version, script], shell=True, stdout=pipe, stderr=pipe)
    except:
        print " Could not find 'makensis.exe', aborting Installer creation."


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
                        help='Specify the path to the NSIS root directory.  Use this is pywin32 is not installed.'
                        )
    parser.add_option('-q', '--quiet',
                        default=False,
                        action='store_true',
                        dest='quiet',
                        help='Quiet mode, supress output from 7z, py2exe, etc'
                        )
    try:
        args,extra = parser.parse_args()
    except:
        parser.print_help()
    else:
        if len(extra) > 0:
            parser.print_help()
        else:
            if not args.wbsa and not args.manual and not args.installer and not args.exe:
                # No arguments specified, build them all
                args.wbsa = True
                args.manual = True
                args.installer = True

            version, file_version = GetVersionInfo()

            if args.quiet:
                pipe = open('log.tmp', 'w')
            else:
                pipe = None

            if args.manual:
                print 'Creating Manual version...'
                BuildManualVersion(version, pipe)

            exe_made = False
            if args.exe or args.wbsa or args.installer:
                print 'Creating StandAlone exe...'
                exe_made = CreateStandaloneExe(version, file_version, pipe)

            if args.wbsa and exe_made:
                print 'Creating StandAlone version...'
                PackStandaloneVersion(version, pipe)

            if args.installer and exe_made:
                print 'Creating Installer version...'
                BuildInstallerVersion(version, file_version, args.nsis, pipe)

            if not args.exe:
                # Clean up the WBSA exe's if necessary
                CleanupStandaloneFiles()

            if args.quiet:
                pipe.close()
                rm('log.tmp')