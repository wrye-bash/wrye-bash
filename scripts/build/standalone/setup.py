#!/usr/bin/env python2

# setup.py used to compile the executable with py2exe

from __future__ import absolute_import
import argparse
import os
import shutil
import sys
from contextlib import contextmanager
from distutils.core import setup

import py2exe.mf as modulefinder
import win32com

def real_sys_prefix():
    if hasattr(sys, u'real_prefix'):  # running in virtualenv
        return sys.real_prefix
    elif hasattr(sys, u'base_prefix'):  # running in venv
        return sys.base_prefix
    else:
        return sys.prefix

# this will be run in the mopy folder
MOPY_FOLDER = os.path.dirname(os.path.abspath(__file__))
BASH_FOLDER = os.path.join(MOPY_FOLDER, u'bash')
WBSA_FOLDER = os.path.join(MOPY_FOLDER, u'..', u'scripts', u'build', u'standalone')
TOOL_FOLDER = os.path.join(real_sys_prefix(), u'Tools', u'i18n')
MANIFEST_FILE = os.path.join(WBSA_FOLDER, u'manifest.xml')
ICON_FILE = os.path.join(WBSA_FOLDER, u'bash.ico')
I18N_FILES = [
    os.path.join(TOOL_FOLDER, u'msgfmt.py'),
    os.path.join(TOOL_FOLDER, u'pygettext.py'),
]

@contextmanager
def move_to_bash(*files):
    file_map = {}  # avoid recalculating file paths
    for filepath in files:
        target = os.path.join(BASH_FOLDER, os.path.basename(filepath))
        shutil.copy2(filepath, target)
        file_map[filepath] = target
    try:
        yield
    finally:
        for target in file_map.values():
            os.remove(target)

# https://stackoverflow.com/a/18940379
argparser = argparse.ArgumentParser(add_help=False)
argparser.add_argument(u'--version', required=True)
args, unknown = argparser.parse_known_args()
sys.argv = [sys.argv[0]] + unknown

# ModuleFinder can't handle runtime changes to __path__, but win32com uses them
for p in win32com.__path__[1:]:
    modulefinder.AddPackagePath(u'win32com', p)

# Read in the manifest file
with open(MANIFEST_FILE, u'r') as man:
    manifest = man.read()

target = {
    u'name': u'Wrye Bash',
    u'description': u'Wrye Bash',
    u'version': args.version,
    u'icon_resources': [(1, ICON_FILE)],
    u'author': u'Wrye Bash development team',
    u'url': u'https://www.nexusmods.com/oblivion/mods/22368',
    u'download_url': u'https://www.nexusmods.com/oblivion/mods/22368',
    u'script': u'Wrye Bash Launcher.pyw',
    u'other_resources': [(24, 1, manifest)],
}

dll_excludes = [
    # Make sure the MSVC 2008 Redist doesn't get included.
    u'MSVCP90.dll',
    u'MSVCR90.dll',
    u'MSVCM90.dll',
    u'api-ms-win-core-atoms-l1-1-0.dll',
    u'api-ms-win-core-com-midlproxystub-l1-1-0.dll',
    u'api-ms-win-core-debug-l1-1-0.dll',
    u'api-ms-win-core-delayload-l1-1-0.dll',
    u'api-ms-win-core-delayload-l1-1-1.dll',
    u'api-ms-win-core-errorhandling-l1-1-0.dll',
    u'api-ms-win-core-file-l1-1-0.dll',
    u'api-ms-win-core-handle-l1-1-0.dll',
    u'api-ms-win-core-heap-l1-1-0.dll',
    u'api-ms-win-core-heap-l2-1-0.dll',
    u'api-ms-win-core-heap-obsolete-l1-1-0.dll',
    u'api-ms-win-core-interlocked-l1-1-0.dll',
    u'api-ms-win-core-kernel32-legacy-l1-1-0.dll',
    u'api-ms-win-core-libraryloader-l1-2-0.dll',
    u'api-ms-win-core-libraryloader-l1-2-1.dll',
    u'api-ms-win-core-localization-l1-2-0.dll',
    u'api-ms-win-core-localization-obsolete-l1-2-0.dll',
    u'api-ms-win-core-memory-l1-1-0.dll',
    u'api-ms-win-core-processenvironment-l1-1-0.dll',
    u'api-ms-win-core-processthreads-l1-1-0.dll',
    u'api-ms-win-core-processthreads-l1-1-1.dll',
    u'api-ms-win-core-profile-l1-1-0.dll',
    u'api-ms-win-core-psapi-l1-1-0.dll',
    u'api-ms-win-core-registry-l1-1-0.dll',
    u'api-ms-win-core-rtlsupport-l1-1-0.dll',
    u'api-ms-win-core-shlwapi-obsolete-l1-1-0.dll',
    u'api-ms-win-core-sidebyside-l1-1-0.dll',
    u'api-ms-win-core-string-l1-1-0.dll',
    u'api-ms-win-core-string-l2-1-0.dll',
    u'api-ms-win-core-string-obsolete-l1-1-0.dll',
    u'api-ms-win-core-synch-l1-1-0.dll',
    u'api-ms-win-core-synch-l1-2-0.dll',
    u'api-ms-win-core-sysinfo-l1-1-0.dll',
    u'api-ms-win-core-threadpool-l1-2-0.dll',
    u'api-ms-win-core-threadpool-legacy-l1-1-0.dll',
    u'api-ms-win-core-timezone-l1-1-0.dll',
    u'api-ms-win-core-util-l1-1-0.dll',
    u'api-ms-win-core-winrt-error-l1-1-0.dll',
    u'api-ms-win-crt-convert-l1-1-0.dll',
    u'api-ms-win-crt-environment-l1-1-0.dll',
    u'api-ms-win-crt-filesystem-l1-1-0.dll',
    u'api-ms-win-crt-heap-l1-1-0.dll',
    u'api-ms-win-crt-locale-l1-1-0.dll',
    u'api-ms-win-crt-math-l1-1-0.dll',
    u'api-ms-win-crt-private-l1-1-0.dll',
    u'api-ms-win-crt-runtime-l1-1-0.dll',
    u'api-ms-win-crt-stdio-l1-1-0.dll',
    u'api-ms-win-crt-string-l1-1-0.dll',
    u'api-ms-win-crt-time-l1-1-0.dll',
    u'api-ms-win-crt-utility-l1-1-0.dll',
    u'api-ms-win-security-base-l1-1-0.dll',
    u'libopenblas.TXA6YQSD3GCQQC22GEQ54J2UDCXDXHWN.gfortran-win_amd64.dll',
    u'MSVCP140.dll',
    u'VCRUNTIME140.dll',
    u'mfc90.dll',
    u'MSIMG32.dll',
    u'MSVCR100.dll',
    u'MPR.dll',
    u'OLEACC.dll',
    u'UxTheme.dll',
]

package_excludes = [
    u'_ssl',  # Suggested in the py2exe tutorial
    u'doctest',  # Suggested in the py2exe tutorial
    u'pdb',  # Suggested in the py2exe tutorial
    u'unittest',  # Suggested in the py2exe tutorial
    u'difflib',  # Suggested in the py2exe tutorial
    u'pywin',  # Suggested in the wxPython example
    u'pywin.debugger',  # Suggested in the wxPython example
    u'pywin.debugger.dbgcon',  # Suggested in the wxPython example
    u'pywin.dialogs',  # Suggested in the wxPython example
    u'pywin.dialogs.list',  # Suggested in the wxPython example
    # Don't need Tkinter in the standalone, since wxPython is present for sure
    u'Tkinter',
    u'Tkconstants',
    u'tcl',
]

with move_to_bash(*I18N_FILES):
    setup(
        windows=[target],
        options={
            u'py2exe': {
                u'dll_excludes': dll_excludes,
                u'packages': [u'bash.game'],
                u'excludes': package_excludes,
                u'ignores': [u'psyco'],
                u'bundle_files': 1,  # 1 = bundle in the exe
                u'optimize': 2,  # 2 = full code optimization
                u'compressed': True,  # Compress the data files
            }
        },
        zipfile=None,  # Don't include data files in a zip along side
    )
