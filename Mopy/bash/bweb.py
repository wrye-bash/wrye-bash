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
   parsing a TESNexus page for files available."""

import re
import urllib
import urllib2

#--TESNexus stuff -------------------------------------------------------------
urlFiles = u'http://www.tesnexus.com/downloads/file/files.php?id=%i'
reFileGroupStart = re.compile(
    u'.*?<h3>\s*(.+?)\s*</h3>\s*<ol\s+class\s*=\s*"files-tab-files-list"\s*>(.*)',
    re.I|re.U)
reFileStart = re.compile(u'.*?<li>(.*)', re.I|re.U)
reFileEnd = re.compile(u'.*?</li>(.*)', re.I|re.U)
reFileName = re.compile(
    u'.*?<span\s+class\s*=\s*"name"\s*>.*?>(.+?)</a></span>(.*)', re.I|re.U)
reFileVersion = re.compile(
    u'.*?<span\s+class\s*=\s*"version"\s*>\s*version\s+(.+?)\s*</span>(.*)',
    re.I|re.U)

def getTESNexusFiles(fileId, groups=None):
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

    url = urlFiles % fileId
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
            currentFile = maFileName.group(1)
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
                    versions.setdefault(group,[]).append((currentFile,currentVersion))
    return versions