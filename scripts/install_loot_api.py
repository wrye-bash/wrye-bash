#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import subprocess
import sys
import tempfile
import urllib
import _winreg

try:
    sys.path.append('Mopy')
    import loot_api
except ImportError:
    pass

def isMSVCRedistInstalled(majorVersion, minorVersion, buildVersion):
    subKey = 'SOFTWARE\\Microsoft\\VisualStudio\\14.0\\VC\\Runtimes\\x86'

    try:
        keyHandle = _winreg.OpenKey(_winreg.HKEY_LOCAL_MACHINE, subKey)

        runtimeInstalled = _winreg.QueryValueEx(keyHandle, 'Installed')[0]
        installedMajorVersion = _winreg.QueryValueEx(keyHandle, 'Major')[0]
        installedMinorVersion = _winreg.QueryValueEx(keyHandle, 'Minor')[0]
        installedBuildVersion = _winreg.QueryValueEx(keyHandle, 'Bld')[0]

        if runtimeInstalled != 0:
            print 'Found MSVC 2015 redistributable version {0}.{1}.{2}'.format(installedMajorVersion, installedMinorVersion, installedBuildVersion)

        return (runtimeInstalled != 0
            and installedMajorVersion >= majorVersion
            and installedMinorVersion >= minorVersion
            and installedBuildVersion >= buildVersion)
    except:
        return False

def installMSVCRedist():
    url = 'https://download.microsoft.com/download/6/A/A/6AA4EDFF-645B-48C5-81CC-ED5963AEAD48/vc_redist.x86.exe'
    downloadedFile = os.path.join(tempfile.gettempdir(), 'vc_redist.x86.exe')

    print 'Downloading the MSVC 2015 redistributable...'
    urllib.urlretrieve(url, downloadedFile)

    print 'Installing the MSVC 2015 redistributable...'
    subprocess.call([downloadedFile, '/quiet'])

    os.remove(downloadedFile)

def isLootApiInstalled(version, revision):
    return ('loot_api' in sys.modules
        and loot_api.WrapperVersion.string() == version
        and loot_api.WrapperVersion.revision == revision)

def installLootApi(version, revision, destinationPath):
    url = 'https://github.com/loot/loot-api-python/releases/download/{0}/loot_api_python-{0}-0-g{1}_master-win32.7z'.format(version, revision)
    archivePath = os.path.join(tempfile.gettempdir(), 'archive.7z')
    sevenZipPath = os.path.join('Mopy', 'bash', 'compiled', '7z.exe')

    print 'Downloading LOOT API Python wrapper from "' + url + '"...'
    urllib.urlretrieve(url, archivePath)

    print 'Extracting LOOT API Python wrapper to ' + destinationPath

    if os.path.exists(os.path.join(destinationPath, 'loot_api.dll')):
        os.remove(os.path.join(destinationPath, 'loot_api.dll'))

    if os.path.exists(os.path.join(destinationPath, 'loot_api.pyd')):
        os.remove(os.path.join(destinationPath, 'loot_api.pyd'))

    subprocess.call([sevenZipPath, 'e', archivePath, '-y', '-o' + destinationPath, '*/loot_api.dll', '*/loot_api.pyd'])

    os.remove(archivePath)

if isMSVCRedistInstalled(14, 0, 24215):
    print 'MSVC 2015 Redistributable is already installed'
else:
    installMSVCRedist()

lootApiWrapperVersion = '1.2.0'
lootApiWrapperRevision ='70371b7'
lootApiUrl = ''
if isLootApiInstalled(lootApiWrapperVersion, lootApiWrapperRevision):
    print 'LOOT API wrapper revision {} is already installed'.format(lootApiWrapperRevision)
else:
    installLootApi(lootApiWrapperVersion, lootApiWrapperRevision, 'Mopy')
