#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import subprocess
import sys
import tempfile
import urllib
import _winreg

lootApiWrapperVersion = '3.0.0'
lootApiWrapperRevision ='1275a11'

try:
    sys.path.append('Mopy')
    import loot_api
except ImportError:
    print 'Importing the loot api failed'
    loot_api = None

dowload_dir = tempfile.gettempdir()
#dowload_dir = '.'

def isMSVCRedistInstalled(majorVersion, minorVersion, buildVersion):
    subKey = 'SOFTWARE\\Microsoft\\VisualStudio\\14.0\\VC\\Runtimes\\x86'
    try:
        keyHandle = _winreg.OpenKey(_winreg.HKEY_LOCAL_MACHINE, subKey)
        runtimeInstalled = _winreg.QueryValueEx(keyHandle, 'Installed')[0]
        installedMajorVersion = _winreg.QueryValueEx(keyHandle, 'Major')[0]
        installedMinorVersion = _winreg.QueryValueEx(keyHandle, 'Minor')[0]
        installedBuildVersion = _winreg.QueryValueEx(keyHandle, 'Bld')[0]
        if runtimeInstalled != 0:
            print 'Found MSVC 2015 redistributable version {0}.{1}.{2}'.format(
                installedMajorVersion, installedMinorVersion,
                installedBuildVersion)
        return (runtimeInstalled != 0
            and installedMajorVersion >= majorVersion
            and installedMinorVersion >= minorVersion
            and installedBuildVersion >= buildVersion)
    except:
        return False

def installMSVCRedist():
    url = 'https://download.microsoft.com/download/6/A/A/6AA4EDFF-645B-48C5-81CC-ED5963AEAD48/vc_redist.x86.exe'
    downloadedFile = os.path.join(dowload_dir, 'vc_redist.x86.exe')
    print 'Downloading the MSVC 2015 redistributable...'
    urllib.urlretrieve(url, downloadedFile)
    print 'Installing the MSVC 2015 redistributable...'
    subprocess.call([downloadedFile, '/quiet'])
    os.remove(downloadedFile)

def isLootApiInstalled(version, revision):
    return (loot_api is not None
        and loot_api.WrapperVersion.string() == version
        and loot_api.WrapperVersion.revision == revision)

def installLootApi(version, revision, destination_path):
    url = 'https://github.com/loot/loot-api-python/releases/download/{0}/loot_api_python-{0}-0-g{1}_master-win32.7z'.format(version, revision)
    archive_path = os.path.join(dowload_dir, 'archive.7z')
    seven_zip_folder = os.path.join('..', 'Mopy', 'bash', 'compiled')
    seven_zip_path = os.path.join(seven_zip_folder, '7z.exe')
    if (os.path.exists(os.path.join(destination_path, 'loot_api.dll'))
       or os.path.exists(os.path.join(destination_path, 'loot_api.pyd'))):
       raise RuntimeError('Please delete the existing LOOT API binaries first.')
    print 'Downloading LOOT API Python wrapper from "' + url + '"...'
    urllib.urlretrieve(url, archive_path)
    print 'Extracting LOOT API Python wrapper to ' + destination_path
    subprocess.call([seven_zip_path, 'e', archive_path, '-y', '-o' + destination_path, '*/loot_api.dll', '*/loot_api.pyd'])
    os.remove(archive_path)

if isMSVCRedistInstalled(14, 0, 24215):
    print 'MSVC 2015 Redistributable is already installed'
else:
    installMSVCRedist()

if isLootApiInstalled(lootApiWrapperVersion, lootApiWrapperRevision):
    print 'LOOT API wrapper revision {} is already installed'.format(
        lootApiWrapperRevision)
else:
    destination_folder = os.path.join('..', 'Mopy')
    installLootApi(lootApiWrapperVersion, lootApiWrapperRevision, destination_folder)

raw_input('> Done')
