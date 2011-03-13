# A setup script for Wrye Bash
#
# This will create a standalone EXE for Wrye Bash,
# gathering all the required files into the 'dist'
# folder.

from distutils.core import setup
import py2exe
import os
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
        self.version = "291"
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

# Generate list of data files needed by Wrye Bash
WBDataFiles = []
base_files = [] # files that go in the root directory
for file in os.listdir(os.getcwd()):
    if os.path.isdir(file):
        # directories should be 'Data', 'Extras', 'Images', and 'Wizard Images'
        if file.lower() in ['build','dist','.svn']:
            # Skip py2exe, SVN directories
            continue
        files = [os.path.join(file, x) for x in os.listdir(file)]
        WBDataFiles.append((file,files))
    elif file.lower().endswith(('.html','.ini','.dll','.exe')):
        base_files.append(file)
base_files.append('gpl.txt')
WBDataFiles.append(('',base_files))

default_target = Target(
    description = "Wrye Bash",
    script = "Wrye Bash Launcher.pyw",
    other_resources = [(RT_MANIFEST, 1, manifest_template)],
    icon_resources = [(101,'bash.ico')],
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
    data_files = WBDataFiles,
    zipfile = None,
    )