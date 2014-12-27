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
#  Wrye Bash copyright (C) 2005-2009 Wrye, 2010-2014 Wrye Bash Team
#  https://github.com/wrye-bash
#
# =============================================================================

"""This module has functions for interacting with webpages.  Specifically,
   parsing a TESNexus page for files available.  Since items here will be used
   with the multiprocessing module, it needs to not have any dependancies on
   the rest of Wrye Bash's files."""
# CRUFT, unused - use or bin

import os
import re
import urllib2
import subprocess

#-- To make commands executed with Popen hidden
startupinfo = None
if os.name == u'nt':
    startupinfo = subprocess.STARTUPINFO()
    startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW

class Nexus:
    #--Regex's for parsing Nexus site URLs
    # http://www.nexusmods.com/skyrim/mods/25859/?tab=2&navtag=http%3A%2F%2Fwww.nexusmods.com%2Fskyrim%2Fajax%2Fmodfiles%2F%3Fid%3D25859&pUp=1
    # http://www.nexusmods.com/oblivion/mods/22368/?tab=2&navtag=http%3A%2F%2Fwww.nexusmods.com%2Foblivion%2Fajax%2Fmodfiles%2F%3Fid%3D22368&pUp=1
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
    # http://www.nexusmods.com/skyrim/mods/25859/?
    # http://www.nexusmods.com/oblivion/mods/22368/?
    # http://www.nexusmods.com/oblivion/?
    # http://www.nexusmods.com/skyrim/?
    def __init__(self,nexusSite='tesnexus',fileId=None):
        self.urlBase = 'http://'+nexusSite+'nexusmods.com'
        self.fileId = fileId

    def getFiles(self,groups=None,fileId=None,nexusSite=None):
        if fileId is None: fileId = self.fileId
        if not fileId: raise ValueError('fileId')
        if nexusSite is None: urlBase = self.urlBase
        else: urlBase = 'http://'+nexusSite+'nexusmods.com'
        urlFiles = urlBase + '/mods/%i' % fileId
        reFileGroupStart = self.reFileGroupStart
        reFileStart = self.reFileStart
        reFileEnd = self.reFileEnd
        reFileName = self.reFileName
        reFileVersion = self.reFileVersion

        inGroup = {}
        versions = {}
        if groups:
            for group in groups:
                inGroup[group.lower()] = False
                versions[group.lower()] = []
            onlySpecificGroups = True
        else:
            onlySpecificGroups = False

        inAnyGroup = False
        inFile = False
        currentFile = None
        currentVersion = None
        currentUrl = None

        url = urllib2.urlopen(urlFiles)
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
