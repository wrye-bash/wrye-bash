# Simple Python scrip to package up the the various Wrye Bash
# Files into archives for release.
#
# command line options:
#  none             -> Build all versions
#  -m OR -manual    -> Build the Manual (archive) version
#  -w OR -wbsa      -> Build the Standalone version
#  -i or -installer -> Build the Installer version
import subprocess
import os
import shutil
import re
import sys
import _winreg

def GetWryeBashVersion():
    readme = r'.\Mopy\Wrye Bash.txt'
    if os.path.exists(readme):
        file = open(readme, 'r')
        reVersion = re.compile('^=== ([\.\d]+) \[')
        for line in file:
            maVersion = reVersion.match(line)
            if maVersion:
                return maVersion.group(1)
    return 'SVN'

# Archives to make
WB = GetWryeBashVersion()
archive =   'Wrye Bash %s -- Archive Version.7z'    % WB
installer = 'Wrye Bash %s -- Installer Version.exe' % WB
WBSA =      'Wrye Bash %s -- Standalone Version.7z' % WB

def BuildManualVersion():
    # Create the standard manual install version
    cmd_7z = [r'.\Mopy\7z.exe', 'a', '-mx9', '-xr!.svn', archive, 'Mopy', 'Data']
    rmv(archive)
    subprocess.call(cmd_7z)

def BuildStandaloneVersion():
    # Create the standalone version
    dir = os.getcwd()
    os.chdir(r'experimental\standalone')
    subprocess.call('build.py', shell=True)
    shutil.move('Wrye Bash Standalone.7z', os.path.join(dir, WBSA))
    os.chdir(dir)

def BuildInstallerVersion():
    # Edit the NSIS script to change the version
    script = 'Wrye Bash.nsi'
    if not os.path.exists(script): return
    
    file = open(script, 'rb')
    lines = file.readlines()
    file.close()

    reVersion = re.compile('(\s+\!define\s+WB_NAME\s+)"(.+)"(.+)')
    for i,line in enumerate(lines):
        # Make sure we're actually overwriting what we want
        maVersion = reVersion.match(line)
        if maVersion:
            newline = maVersion.group(1) + ('"Wrye Bash %s"' % WB) + maVersion.group(3) + '\n'
            if line == newline:
                break
            lines[i] = newline
            file = open(script, 'wb')
            file.writelines(lines)
            file.close()
            break

    # Now compile the NSIS script
    try:
        nsis = _winreg.QueryValue(_winreg.HKEY_LOCAL_MACHINE, r'Software\NSIS')
        nsis = os.path.join(nsis, 'makensis.exe')
        subprocess.call([nsis, 'Wrye Bash.nsi'], shell=True)
    except:
        pass

def rmv(path):
    """Helper function to remove if a file/directory exists"""
    if os.path.exists(path):
        if os.path.isdir(path):
            shutil.rmtree(path)
        else:
            os.remove(path)

if __name__ == '__main__':
    if len(sys.argv) == 1:
        BuildManualVersion()
        BuildStandaloneVersion()
        BuildInstallerVersion()
    else:
        if '-m' in sys.argv or '-manual' in sys.argv:
            BuildManualVersion()
        if '-w' in sys.argv or '-wbsa' in sys.argv:
            BuildStandaloneVersion()
        if '-i' in sys.argv or '-installer' in sys.argv:
            BuildInstallerVersion()