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
    if hasattr(sys, "real_prefix"):  # running in virtualenv
        return sys.real_prefix
    elif hasattr(sys, "base_prefix"):  # running in venv
        return sys.base_prefix
    else:
        return sys.prefix


# this will be run in the mopy folder
MOPY_FOLDER = os.path.dirname(os.path.abspath(__file__))
BASH_FOLDER = os.path.join(MOPY_FOLDER, u"bash")
WBSA_FOLDER = os.path.join(MOPY_FOLDER, u"..", u"scripts", u"build", u"standalone")
TOOL_FOLDER = os.path.join(real_sys_prefix(), u"Tools", u"i18n")
MANIFEST_FILE = os.path.join(WBSA_FOLDER, u"manifest.xml")
ICON_FILE = os.path.join(WBSA_FOLDER, u"bash.ico")
I18N_FILES = [
    os.path.join(TOOL_FOLDER, u"msgfmt.py"),
    os.path.join(TOOL_FOLDER, u"pygettext.py"),
]


@contextmanager
def move_to_bash(*files):
    file_map = {}  # avoid recalculating file paths
    for path in files:
        target = os.path.join(BASH_FOLDER, os.path.basename(path))
        shutil.copy2(path, target)
        file_map[path] = target
    try:
        yield
    finally:
        for target in file_map.values():
            os.remove(target)


# https://stackoverflow.com/a/18940379
argparser = argparse.ArgumentParser(add_help=False)
argparser.add_argument("--version", required=True)
args, unknown = argparser.parse_known_args()
sys.argv = [sys.argv[0]] + unknown

# ModuleFinder can't handle runtime changes to __path__, but win32com uses them
for p in win32com.__path__[1:]:
    modulefinder.AddPackagePath("win32com", p)

# Read in the manifest file
with open(MANIFEST_FILE, "r") as man:
    manifest = man.read()

target = {
    "name": "Wrye Bash",
    "description": "Wrye Bash",
    "version": args.version,
    "icon_resources": [(1, ICON_FILE)],
    "author": "Wrye Bash development team",
    "url": "https://www.nexusmods.com/oblivion/mods/22368",
    "download_url": "https://www.nexusmods.com/oblivion/mods/22368",
    "script": "Wrye Bash Launcher.pyw",
    "other_resources": [(24, 1, manifest)],
}

dll_excludes = [
    # Make sure the MSVC 2008 Redist doesn't get included.
    "MSVCP90.dll",
    "MSVCR90.dll",
    "MSVCM90.dll",
    "mswsock.dll",  # Prevent x64 versions (for win32api)
    "powrprof.dll",  # Prevent x64 versions (for win32api)
    "api-ms-win-crt-heap-l1-1-0.dll",
    "api-ms-win-crt-string-l1-1-0.dll",
    "api-ms-win-crt-runtime-l1-1-0.dll",
    "api-ms-win-crt-convert-l1-1-0.dll",
    "api-ms-win-crt-locale-l1-1-0.dll",
    "api-ms-win-crt-filesystem-l1-1-0.dll",
    "api-ms-win-crt-math-l1-1-0.dll",
    "api-ms-win-crt-utility-l1-1-0.dll",
    "api-ms-win-crt-environment-l1-1-0.dll",
    "api-ms-win-crt-stdio-l1-1-0.dll",
    "api-ms-win-crt-time-l1-1-0.dll",
    "MSVCP140.dll",
    "VCRUNTIME140.dll",
]

package_excludes = [
    "_ssl",  # Suggested in the py2exe tutorial
    "doctest",  # Suggested in the py2exe tutorial
    "pdb",  # Suggested in the py2exe tutorial
    "unittest",  # Suggested in the py2exe tutorial
    "difflib",  # Suggested in the py2exe tutorial
    "pywin",  # Suggested in the wxPython example
    "pywin.debugger",  # Suggested in the wxPython example
    "pywin.debugger.dbgcon",  # Suggested in the wxPython example
    "pywin.dialogs",  # Suggested in the wxPython example
    "pywin.dialogs.list",  # Suggested in the wxPython example
    # Don't need Tkinter in the standalone, since wxPython is present for sure
    "Tkinter",
    "Tkconstants",
    "tcl",
]

with move_to_bash(*I18N_FILES):
    setup(
        windows=[target],
        options={
            "py2exe": {
                "dll_excludes": dll_excludes,
                "packages": ["bash.game"],
                "excludes": package_excludes,
                "ignores": ["psyco"],
                "bundle_files": 1,  # 1 = bundle in the exe
                "optimize": 2,  # 2 = full code optimization
                "compressed": True,  # Compress the data files
            }
        },
        zipfile=None,  # Don't include data files in a zip along side
    )
