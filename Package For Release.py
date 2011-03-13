import subprocess
import os
import shutil
import re

# Archives to make
WB = 'SVN'
readme = r'.\Mopy\Wrye Bash.txt'
if os.path.exists(readme):
    file = open(readme)
    reVersion = re.compile('^=== ([\.\d]+) \[')
    for line in file:
        maVersion = reVersion.match(line)
        if maVersion:
            WB = maVersion.group(1)
            break
    file.close()
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
    # Create the installer version
    # TODO: DO THIS!
    pass

def rmv(path):
    """Helper function to remove if a file/directory exists"""
    if os.path.exists(path):
        if os.path.isdir(path):
            shutil.rmtree(path)
        else:
            os.remove(path)

BuildManualVersion()
BuildStandaloneVersion()
BuildInstallerVersion()
