# -*- mode: python -*-

import fnmatch
import os
import sys

# PyInstaller *insists* on including Tk/Tcl. Workaround taken from here:
# https://github.com/pyinstaller/pyinstaller/wiki/Recipe-remove-tkinter-tcl
sys.modules['FixTk'] = None

def real_sys_prefix():
    if hasattr(sys, 'real_prefix'):  # running in virtualenv
        return sys.real_prefix
    elif hasattr(sys, 'base_prefix'):  # running in venv
        return sys.base_prefix
    else:
        return sys.prefix

TOOL_PATH = os.path.join(real_sys_prefix(), 'Tools', 'i18n')
WBSA_PATH = SPECPATH  # pyinstaller-defined global
ROOT_PATH = os.path.join(WBSA_PATH, '..', '..', '..')
MOPY_PATH = os.path.join(ROOT_PATH, 'Mopy')
GAME_PATH = os.path.join(MOPY_PATH, 'bash', 'game')

block_cipher = None
entry_point = os.path.join(MOPY_PATH, 'Wrye Bash Launcher.pyw')
icon_path = os.path.join(WBSA_PATH, 'bash.ico')
manifest_path = os.path.join(WBSA_PATH, 'manifest.xml')
hiddenimports = ['pygettext', 'msgfmt']

for root, _, filenames in os.walk(GAME_PATH):
    for filename in fnmatch.filter(filenames, '*.py'):
        path = os.path.join(root, filename)
        path = path[:-3]  # remove '.py'
        import_path = os.path.relpath(path, start=MOPY_PATH)
        hiddenimports.append(import_path.replace(os.sep, '.'))

# See sys.modules hack above - we don't need Tkinter, just bloats the EXE
excluded_modules = [
    '_tkinter',
    'FixTk',
    'tcl',
    'tk',
    'tkinter',
    'Tkinter',
]
# These showed up all of a sudden after a PyInstaller upgrade :/
excluded_modules += [
    'IPython',
    'matplotlib',
    'numpy',
]

a = Analysis([entry_point],
             pathex=[TOOL_PATH, ROOT_PATH],
             binaries=[],
             datas=[],
             hiddenimports=hiddenimports,
             hookspath=[],
             runtime_hooks=[],
             excludes=excluded_modules,
             win_no_prefer_redirects=False,
             win_private_assemblies=False,
             cipher=block_cipher,
             noarchive=False)

# Remove binaries we don't want to include
excluded_binaries = {
    'MSVCP140.dll',
    'VCRUNTIME140.dll',
    'api-ms-win-core-console-l1-1-0.dll',
    'api-ms-win-core-datetime-l1-1-0.dll',
    'api-ms-win-core-debug-l1-1-0.dll',
    'api-ms-win-core-errorhandling-l1-1-0.dll',
    'api-ms-win-core-file-l1-1-0.dll',
    'api-ms-win-core-file-l1-2-0.dll',
    'api-ms-win-core-file-l2-1-0.dll',
    'api-ms-win-core-handle-l1-1-0.dll',
    'api-ms-win-core-heap-l1-1-0.dll',
    'api-ms-win-core-interlocked-l1-1-0.dll',
    'api-ms-win-core-libraryloader-l1-1-0.dll',
    'api-ms-win-core-localization-l1-2-0.dll',
    'api-ms-win-core-memory-l1-1-0.dll',
    'api-ms-win-core-namedpipe-l1-1-0.dll',
    'api-ms-win-core-processenvironment-l1-1-0.dll',
    'api-ms-win-core-processthreads-l1-1-0.dll',
    'api-ms-win-core-processthreads-l1-1-1.dll',
    'api-ms-win-core-profile-l1-1-0.dll',
    'api-ms-win-core-rtlsupport-l1-1-0.dll',
    'api-ms-win-core-string-l1-1-0.dll',
    'api-ms-win-core-synch-l1-1-0.dll',
    'api-ms-win-core-synch-l1-2-0.dll',
    'api-ms-win-core-sysinfo-l1-1-0.dll',
    'api-ms-win-core-timezone-l1-1-0.dll',
    'api-ms-win-core-util-l1-1-0.dll',
    'api-ms-win-crt-conio-l1-1-0.dll',
    'api-ms-win-crt-convert-l1-1-0.dll',
    'api-ms-win-crt-environment-l1-1-0.dll',
    'api-ms-win-crt-filesystem-l1-1-0.dll',
    'api-ms-win-crt-heap-l1-1-0.dll',
    'api-ms-win-crt-locale-l1-1-0.dll',
    'api-ms-win-crt-math-l1-1-0.dll',
    'api-ms-win-crt-multibyte-l1-1-0.dll',
    'api-ms-win-crt-process-l1-1-0.dll',
    'api-ms-win-crt-runtime-l1-1-0.dll',
    'api-ms-win-crt-stdio-l1-1-0.dll',
    'api-ms-win-crt-string-l1-1-0.dll',
    'api-ms-win-crt-time-l1-1-0.dll',
    'api-ms-win-crt-utility-l1-1-0.dll',
    'mfc140u.dll',
    'tcl86t.dll',
    'tk86t.dll',
    'ucrtbase.dll',
}
a.binaries = TOC([x for x in a.binaries if x[0] not in excluded_binaries])

pyz = PYZ(a.pure, a.zipped_data,
          cipher=block_cipher)

exe = EXE(pyz,
          a.scripts,
          a.binaries,
          a.zipfiles,
          a.datas,
          [],
          name='Wrye Bash',
          debug=False,
          bootloader_ignore_signals=False,
          strip=False,
          upx=True,
          runtime_tmpdir=None,
          console=False,
          icon=icon_path,
          manifest=manifest_path)
