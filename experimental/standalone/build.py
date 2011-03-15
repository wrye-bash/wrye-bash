#= Wrye Bash Standalone Creator ===============================
#
# This script does the work of creating a standalone version
# of Wrye Bash.  You can run it from one of two places:
#
# 1) The folder up from 'Mopy' (for example, C:\Games\Oblivion)
# 2) The default location in the SVN
#
# The script uses py2exe to package the required files all
# into an exe, then runs UPX on that exe, then packages
# all the files into a 7z archive.
import os
import shutil
import subprocess
import re

# Some quick reference paths
root = build = os.getcwd()
reshacker = os.path.join(root, 'ResHacker.exe')
icon = os.path.join(root, 'bash.ico')
upx = os.path.join(root, 'upx.exe')
archive = os.path.join(root, 'Wrye Bash Standalone.7z')

# Now we'll see if build.py is located in the 'experimental/standalone'
# folder of the svn, or just up from the 'Mopy' folder
mopy = os.path.join(root, 'Mopy')
if os.path.exists(mopy):
    # We're just up one
    pass
else:
    # We're probably in the 'experimental/standalone' folder
    os.chdir('..\..')
    root = os.getcwd()
    mopy = os.path.join(root, 'Mopy')

if not os.path.exists(mopy):
    raise "Could not locate the Mopy folder."


# Delete/Move if exists helper functions
def rmv(file):
    if os.path.exists(file):
        os.remove(file)
def mv(file,dest):
    if os.path.exists(file):
        shutil.move(file,dest)

def GetWryeBashVersion():
    readme = os.path.join(mopy,'Wrye Bash.txt')
    if os.path.exists(readme):
        file = open(readme, 'r')
        reVersion = re.compile('^=== ([\.\d]+) \[')
        for line in file:
            maVersion = reVersion.match(line)
            if maVersion:
                return maVersion.group(1)
    return 'SVN'

# First execute the py2exe script
# I'm doing it this was because 'exec' and 'execfile' don't
# quite work the way I want - the py2exe creation doesn't
# collect the right source files.
setup_script = """
# A setup script for Wrye Bash
#
# This will create a standalone EXE for Wrye Bash,
# gathering all the required files into the 'dist'
# folder.

from distutils.core import setup
import py2exe
import sys

# If run without args, build executables, in quiet mode.
if len(sys.argv) == 1:
    sys.argv.append("py2exe")
    sys.argv.append("-q")

# Info for the executable
class Target:
    def __init__(self, **kw):
        self.__dict__.update(kw)
        # for the versioninfo resources
        self.version = "%(version)s"
        self.name = "Wrye Bash"
        self.author = "Wrye and the Wrye Bash Team"
        self.url= "http://tesnexus.com/downloads/file.php?id=22368"
        self.download_url = self.url

################################################################
# A program using wxPython

# The manifest will be inserted as resource into test_wx.exe.  This
# gives the controls the Windows XP appearance (if run on XP ;-)
#
# Another option would be to store it in a file named
# Wrye Bash.exe.manifest, and copy it with the data_files option into
# the dist-dir.
#
manifest_template = '''
<assembly xmlns="urn:schemas-microsoft-com:asm.v1" manifestVersion="1.0">
  <trustInfo xmlns="urn:schemas-microsoft-com:asm.v3">
    <security>
      <requestedPrivileges>
        <requestedExecutionLevel
          level="asInvoker"
          uiAccess="false"
        />
      </requestedPrivileges>
    </security>
  </trustInfo>
  <dependency>
    <dependentAssembly>
      <assemblyIdentity
        type="win32"
        name="Microsoft.VC90.CRT"
        version="9.0.21022.8"
        processorArchitecture="x86"
        publicKeyToken="1fc8b3b9a1e18e3b"
      />
    </dependentAssembly>
  </dependency>
  <dependency>
    <dependentAssembly>
      <assemblyIdentity
          type="win32"
          name="Microsoft.Windows.Common-Controls"
          version="6.0.0.0"
          processorArchitecture="X86"
          publicKeyToken="6595b64144ccf1df"
          language="*"
      />
    </dependentAssembly>
  </dependency>
</assembly>
'''
RT_MANIFEST = 24

default_target = Target(
    description = "Wrye Bash",
    script = "Wrye Bash Launcher.pyw",
    other_resources = [(RT_MANIFEST, 1, manifest_template)],
    )

# Make the executable
setup(
    windows = [default_target],
    options = {
        'py2exe': {
            'dll_excludes': [
                'MSVCP90.dll',
                # For win32api (py2exe included these when built
                # on Vista/7, when it shouldn't
                'mswsock.dll',
                'powrprof.dll',
                ],
            'excludes': [
                # From the py2exe tutorial
                '_ssl',
                'doctest',
                'pdb',
                'unittest',
                'difflib',
                'inspect',
                # From the wx sample in py2exe
                'pywin',
                'pywin.debugger',
                'pywin.debugger.dbgcon',
                'pywin.dialogs',
                'pywin.dialogs.list',
                ],
            'bundle_files': 1,
            'optimize': 2,
            'compressed':True,
            }
        },
    zipfile = None,
    )
""" % dict(version=GetWryeBashVersion())
# Write the script file
file = open('Mopy\setup.py', 'w')
file.write(setup_script)
file.close()

# Now run the script
os.chdir(mopy)
subprocess.call('setup.py', shell=True)
os.chdir(root)

# Now copy 'Wrye Bash Launcher.exe' to the Mopy folder as 'Wrye Bash.exe'
# and copy 'w9xpopen' for those Win98 users (are there any?)
mv(r'Mopy\dist\Wrye Bash Launcher.exe', r'Mopy\Wrye Bash.exe')
mv(r'Mopy\dist\w9xpopen.exe', r'Mopy\w9xpopen.exe')

# Now cleanup unneeded files, and make the list of files for 7z
cmd_7z = [r'.\Mopy\7z.exe', 'a', '-mx9', '-xr!.svn', archive]
for file in os.listdir(mopy):
    path = os.path.join(mopy, file)
    if os.path.isdir(path):
        # Directories.  Get rid of the 'build', 'dist'
        if file.lower() in ['dist','build']:
            shutil.rmtree(path)
        elif file.lower() == '.svn':
            continue
        else:
            cmd_7z.append('Mopy\\'+file)
cmd_7z.extend([r'Mopy\*.exe', r'Mopy\*.dll', r'Mopy\*.ini', r'Mopy\*.html', r'Mopy\*.txt'])
cmd_7z.append('Data')

# Fixup the exe with ResHacker (py2exe doesn't set the icon right, so
# we'll use ResHacker instead)
subprocess.call([reshacker, '-addoverwrite', r'Mopy\Wrye Bash.exe,', r'Mopy\Wrye Bash.exe,',
                 icon+',', 'icon,', '101,', '0'])

# Compress with UPX
subprocess.call([upx, '-9', r'.\Mopy\Wrye Bash.exe'])

# Make the 7z archive, delete any old ones first
rmv(archive)
subprocess.call(cmd_7z)

# Cleanup files
rmv(r'Mopy\setup.py')
rmv(r'Mopy\Wrye Bash.exe')
rmv(r'Mopy\w9xpopen.exe')
os.chdir(build)     # Make sure we're in the dir that ResHacker is located
rmv('ResHacker.ini')
rmv('ResHacker.log')