# -*- coding: utf-8 -*-
#
# GPL License and Copyright Notice ============================================
#  This file is part of Wrye Bash.
#
#  Wrye Bash is free software; you can redistribute it and/or
#  modify it under the terms of the GNU General Public License
#  as published by the Free Software Foundation; either version 2
#  of the License, or (at your option) any later version.
#
#  Wrye Bash is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
#
#  You should have received a copy of the GNU General Public License
#  along with Wrye Bash; if not, write to the Free Software Foundation,
#  Inc., 59 Temple Place - Suite 330, Boston, MA  02111-1307, USA.
#
#  Wrye Bash copyright (C) 2005, 2006, 2007, 2008, 2009 Wrye
#
# =============================================================================

"""This module has functions for interacting with webpages.  Specifically,
   parsing a TESNexus page for files available.  Since items here will be used
   with the multiprocessing module, it needs to not have any dependancies on
   the rest of Wrye Bash's files."""

import os
import shutil
import re
import urllib
import urllib2
import subprocess

#-- To make commands executed with Popen hidden
startupinfo = None
if os.name == u'nt':
    startupinfo = subprocess.STARTUPINFO()
    try: startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
    except:
        import _subprocess
        startupinfo.dwFlags |= _subprocess.STARTF_USESHOWWINDOW


class Nexus:
    #--Regex's for parsing Nexus site URLs
    reFileGroupStart = re.compile(
        u'.*?<h3>\s*(.+?)\s*</h3>\s*<ol\s+class\s*=\s*"files-tab-files-list"\s*>(.*)',
        re.I|re.U)
    reFileStart = re.compile(u'.*?<li>(.*)', re.I|re.U)
    reFileEnd = re.compile(u'.*?</li>(.*)', re.I|re.U)
    reFileName = re.compile(
        u'.*?<span\s+class\s*=\s*"name"\s*>\s*<\s*a\s+href\s*=\"(.*?)\".*?>(.+?)</a></span>(.*)', re.I|re.U)
    reFileVersion = re.compile(
        u'.*?<span\s+class\s*=\s*"version"\s*>\|\s*version\s+(.+?)\s*</span>(.*)',
        re.I|re.U)

    # Class for interacting with TES/Skyrim Nexus
    def __init__(self,nexusSite='tesnexus',fileId=None):
        self.urlBase = 'http://www.'+nexusSite+'.com'
        self.fileId = fileId

    def getFiles(groups=None,fileId=None,nexusSite=None):
        if fileId is None: fileId = self.fileId
        if not fileId: raise ValueError('fileId')
        if nexusSites is None: urlBase = self.urlBase
        else: urlBase = 'http://www.'+nexusSite+'.com'
        urlFiles = urlBase + '/downloads/file/files.php?id=%i' % fileId
        reFileGroupStart = self.reFileGroupStart
        reFileStart = self.reFileStart
        reFileEnd = self.reFileEnd
        reFileVersion = self.reFileVersion

        inGroup = {}
        versions = {}
        if groups:
            for group in groups:
                inType[group.lower()] = False
                versions[group.lower()] = []
            onlySpecificGroups = True
        else:
            onlySpecificGroups = False

        inAnyGroup = False
        inFile = False
        currentFile = None
        currentVersion = None
        currentUrl = None

        url = urllib2.urlopen(url)
        for line in url:
            maFileGroupStart = reFileGroupStart.match(line)
            if maFileGroupStart:
                group = maFileGroupStart.group(1).lower()
                line = maFileGroupStart.group(2)
                for key in inGroup:
                    inGroup[key] = bool(key == group)
                inAnyGroup = bool(group in inGroup) or not onlySpecificGroups
            if not inAnyGroup: continue
            if not inFile:
                maFileStart = reFileStart.match(line)
                if maFileStart:
                    line = maFileStart.group(1)
                    inFile = True
                    currentFile = None
                    currentVersion = None
            if not inFile: continue
            maFileName = reFileName.match(line)
            if maFileName:
                currentUrl = urlBase + maFileName.group(1)
                currentFile = maFileName.group(2)
                currentVersion = (1,0)
                line = maFileName.group(2)
            maFileVersion = reFileVersion.match(line)
            if maFileVersion:
                currentVersion = maFileVersion.group(1)
                line = maFileVersion.group(2)
                try:
                    currentVersion = tuple([int(x) for x in currentVersion.split(u'.')])
                except:
                    currentVersion = None
            maFileEnd = reFileEnd.match(line)
            if maFileEnd:
                inFile = False
                if inAnyGroup:
                    if currentVersion is not None and currentFile is not None:
                        versions.setdefault(group,[]).append((currentFile,currentVersion,currentUrl))
        return versions

class SourceForge(object):
    __slots__ = ('wbVersion','project')

    #--Regex's for parsing SourceForge's URLs
    reFileStart = re.compile(
        u'.*?<\s*tr\s+title\s*=\s*(.*?)\s+class\s*=\s*"file warn"\s*>(.*)',
        re.I|re.U)
    reFolderStart = re.compile(
        u'.*?<\s*tr\s+title\s*=\s*(.*?)\s+class\s*=\s*"folder warn"\s*>(.*)',
        re.I|re.U)
    reFileUrl = re.compile(
        u'.*?href\s*=\s*(.*?)\s+(.*)',
        re.U|re.I)
    reFileEnd = re.compile(
        u'.*?<\s*/\s*tr\s*>(.*?)',
        re.U|re.I)
    reDateVersion = re.compile(
        ur'(.*?)(\d+)-(\d+)-(\d+)(-rev\d+|).*?',
        re.U|re.I)
    reWryeBashVersion = re.compile(
        ur'Wrye Bash (\d[\d\.]*)\s*(.*?)',
        re.U|re.I)
    baseUrl = 'https://sourceforge.net/projects/%s/'

    def __init__(self,wbVersion=None,project='oblivionworks'):
        self.wbVersion = wbVersion
        self.project = project

    @property
    def filesUrl(self):
        return (self.baseUrl % self.project) + 'files/'

    def getAllUpdates(self,wbVersion=None):
        if not wbVersion: wbVersion = self.wbVersion
        if not wbVersion: raise ValueError('wbVersion')

        updates = {}
        results = self.getWryeBashFiles(wbVersion)
        for result in results:
            updates.setdefault(result[0],{})['name'] = result[3]
            updates[result[0]]['url'] = result[2]
        for version in updates:
            progs,defs,langs = self.getUpdates(version)
            updates[version]['definitions'] = defs
            updates[version]['languages'] = langs
            updates[version]['programs'] = progs
        progs,defs,langs = self.getUpdates(wbVersion)
        updates[wbVersion] = {
            'name': 'Wrye Bash %s' % wbVersion,
            'url': '',
            'definitions': defs,
            'languages': langs,
            'programs': [],
            }
        return updates

    def getWryeBashFiles(self,wbVersion=None):
        if not wbVersion: wbVersion = self.wbVersion
        if not wbVersion: wbVersion = '0.0'

        reFolder = self.reFolderStart
        reFolderUrl = self.reFileUrl
        reEnd = self.reFileEnd
        reWryeBashVersion = self.reWryeBashVersion
        results = []
        currentFolder = None

        url = self.filesUrl + '/Wrye%20Bash/'
        ins = urllib2.urlopen(url)
        for line in ins:
            if not currentFolder:
                maFolder = reFolder.match(line)
                if maFolder:
                    currentFolder = maFolder.group(1)[1:-1]
                    result = None
                    maWB = reWryeBashVersion.match(currentFolder)
                    if maWB:
                        result = list(maWB.groups())
                        if result[0] <= wbVersion:
                            result = None
                        else:
                            result = result + ['',currentFolder]
                    line = maFolder.group(2)
            if currentFolder:
                if result and result[2] == '':
                    maUrl = reFolderUrl.match(line)
                    if maUrl:
                        result[2] = 'http://sourceforge.net'+maUrl.group(1)[1:-1]
                        line = maUrl.group(2)
                maEnd = reEnd.match(line)
                if maEnd:
                    currentFolder = None
                    if result:
                        results.append(result)
        results.sort(reverse=True)
        return results

    def getUpdates(self,wbVersion=None):
        if not wbVersion: wbVersion = self.wbVersion
        if not wbVersion: raise ValueError('wbVersion')

        reFileStart = self.reFileStart
        reFileUrl = self.reFileUrl
        reFileEnd = self.reFileEnd
        reDateVersion = self.reDateVersion
        url=self.filesUrl + '/Wrye%20Bash/Wrye%20Bash%20'+wbVersion+u'/'
        currentFile = None
        currentUrl = None
        definitions = []
        languages = []
        programs = []
        ins = urllib2.urlopen(url)
        for line in ins:
            if not currentFile:
                maFileStart = reFileStart.match(line)
                if maFileStart:
                    currentFile = maFileStart.group(1)[1:-1]
                    line = maFileStart.group(2)
            if currentFile and not currentUrl:
                maFileUrl = reFileUrl.match(line)
                if maFileUrl:
                    currentUrl = maFileUrl.group(1)[1:-1]
                    line = maFileUrl.group(2)
            if currentFile:
                maFileEnd = reFileEnd.match(line)
                if maFileEnd and currentUrl:
                    match = reDateVersion.match(currentFile)
                    if match:
                        date_rev = match.group(4),match.group(2),match.group(3),match.group(5)
                    else:
                        date_rev = (0,0,0,currentFile)
                    currentLower = currentFile.lower()
                    if 'game definitions' in currentLower:
                        definitions.append((currentFile,date_rev,currentUrl))
                    elif 'language' in currentLower or 'translation' in currentLower:
                        languages.append((currentFile,date_rev,currentUrl))
                    elif 'wrye bash' in currentLower:
                        programs.append((currentFile,date_rev,currentUrl))
                    currentFile = None
                    currentUrl = None
                    line = maFileEnd.group(1)
        definitions.sort(key=lambda a: a[1],reverse=True)
        languages.sort(key=lambda a: a[1],reverse=True)
        return programs,definitions,languages

    def downloadLatestGameDefinition(self,outDir=u'.',callback=None,wbVersion=None):
        programs,defs,langs = self.getUpdates(wbVersion)
        if not defs: return None
        return self.downloadUpdate(defs[-1],outDir,callback)

    def downloadLatestLanguagePack(self,outDir=u'.',callback=None,wbVersion=None):
        programs,defs,langs = self.getUpdates(wbVersion)
        if not langs: return None
        return self.downloadUpdate(langs[-1],outDir,callback)

    def downloadUpdate(self,update,outDir=u'.',callback=None):
        name,version,url = update
        if not os.path.isabs(outDir):
            outDir = os.path.join(os.getcwdu(),outDir)
            outDir = os.path.normpath(outDir)
        name = os.path.join(outDir,name)
        urllib.urlretrieve(url,name,callback)
        return name

    def downloadUpdates(self,updates,outDir='.',callback=None):
        return [self.downloadUpdate(update,outDir,callback) for update in updates]

#--These are plain functions, for use with multiprocessing module, since you
#  can't instansiate an object, then use one of its member function in a
#  different process, since the object data would have to be sent as well.
def downloadUpdate(update,outDir=u'.',callback=None):
    sf = SourceForge()
    return sf.downloadUpdate(update,outDir,callback)

def downloadUpdates(updates,outDir=u'.',callback=None):
    sf = SourceForge()
    return sf.downloadUpdates(updates,outDir,callback)

def downloadLatestGameDefinition(wbVersion,outDir=u'.',callback=None):
    sf = SourceForge(wbVersion)
    return sf.downloadLatestGameDefinition(outDir,callback)

def downloadLatestLanguagePack(wbVersion,outDir=u'.',callback=None):
    sf = SourceForge(wbVersion)
    return sf.downloadLatestLanguagePack(outDir,callback)

def getAllUpdates(wbVersion):
    sf = SourceForge(wbVersion)
    return sf.getAllUpdates()

def createBackup(outFile,exe7z,cmd7zTemplate):
    cwd = os.getcwdu()
    outFile = os.path.relpath(outFile,cwd)
    exe7z = os.path.relpath(exe7z,cwd)
    if os.path.exists(outFile):
        os.remove(outFile)

    # Compress backup
    cmd7z = cmd7zTemplate % (exe7z,outFile)
    ins = subprocess.Popen(cmd7z,stdout=subprocess.PIPE,startupinfo=startupinfo).stdout
    reCompressing = re.compile(ur'^Compressing\s+(.+)',re.U)
    reError = re.compile(ur'^Error:(.*?)',re.U)
    allErrorLines = []
    errorLines = []
    for line in ins:
        if reError.match(line):
            errorLines.append(line)
        elif reCompressing.match(line):
            allErrorLines.extend(errorLines)
            errorLines = []
        elif errorLines:
            errorLines.append(line)
    allErrorLines.extend(errorLines)
    ins.close()
    return allErrorLines

def extractUpdates(fileNames,exe7z,cmd7zTemplate,outDir):
    failed = []
    reExtracting = re.compile(ur'^Extracting\s+(.+)',re.U)
    reError = re.compile(ur'^Error:(.*?)',re.U)
    cwd = os.getcwdu()
    # Use relative paths to cwd, to minimize change of passing
    # unicode filenames on the command line
    fileNames = [os.path.relpath(x,cwd) for x in fileNames]
    exe7z = os.path.relpath(exe7z,cwd)
    outDir = os.path.relpath(outDir,cwd)
    errorLines = []

    for fileName in fileNames:
        cmd7z = cmd7zTemplate % (exe7z,fileName,outDir)
        ins = subprocess.Popen(cmd7z,stdout=subprocess.PIPE,startupinfo=startupinfo).stdout
        try:
            for line in ins:
                if reError.match(line):
                    errorLines.append(line)
                elif reExtracting.match(line):
                    if errorLines:
                        failed.append((fileName,errorLines))
                        errorLines = []
                elif errorLines:
                    errorLines.append(line)
        except:
            failed.append((fileName,errorLines))
            try: ins.close()
            except: pass
            continue
        try:
            if ins.close():
                failed.append((fileName,errorLines))
        except:
            failed.append((fileName,errorLines))
    return failed