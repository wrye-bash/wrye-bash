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
#  Wrye Bash copyright (C) 2005-2009 Wrye, 2010-2019 Wrye Bash Team
#  https://github.com/wrye-bash
#
# =============================================================================
import os
import re
import subprocess

import bass
from bolt import startupinfo, GPath, deprint, walkdir
from exception import StateError

exe7z = u'7z.exe' if os.name == u'nt' else u'7z'
defaultExt = u'.7z'
writeExts = {u'.7z': u'7z', u'.zip': u'zip'}
readExts = {u'.rar', u'.7z.001', u'.001'}
readExts.update(set(writeExts))
noSolidExts = {u'.zip'}
reSolid = re.compile(ur'[-/]ms=[^\s]+', re.IGNORECASE)
regCompressMatch = re.compile(ur'Compressing\s+(.+)', re.U).match
regExtractMatch = re.compile(ur'- (.+)', re.U).match
regErrMatch = re.compile(u'^(Error:.+|.+     Data Error?|Sub items Errors:.+)',
    re.U).match
reListArchive = re.compile(
    u'(Solid|Path|Size|CRC|Attributes|Method) = (.*?)(?:\r\n|\n)')

def compress7z(command, outDir, destArchive, srcDir, progress=None):
    outFile = outDir.join(destArchive)
    if progress is not None: #--Used solely for the progress bar
        length = sum([len(files) for x, y, files in walkdir(srcDir.s)])
        progress(0, destArchive.s + u'\n' + _(u'Compressing files...'))
        progress.setFull(1 + length)
    #--Pack the files
    proc = subprocess.Popen(command, stdout=subprocess.PIPE, bufsize=1,
                            stdin=subprocess.PIPE, # needed for some commands
                            startupinfo=startupinfo)
    #--Error checking and progress feedback
    index, errorLine = 0, u''
    with proc.stdout as out:
        for line in iter(out.readline, b''):
            line = unicode(line, 'utf8') # utf-8 is ok see bosh.compressCommand
            if regErrMatch(line):
                errorLine = line + u''.join(out)
                break
            if progress is None: continue
            maCompressing = regCompressMatch(line)
            if maCompressing:
                progress(index, destArchive.s + u'\n' + _(
                    u'Compressing files...') + u'\n' + maCompressing.group(
                    1).strip())
                index += 1
    returncode = proc.wait()
    if returncode or errorLine:
        outFile.temp.remove()
        raise StateError(destArchive.s + u': Compression failed:\n' +
                u'7z.exe return value: ' + str(returncode) + u'\n' + errorLine)
    #--Finalize the file, and cleanup
    outFile.untemp()

def extract7z(src_archive, extract_dir, progress=None, readExtensions=None,
              recursive=False, filelist_to_extract=None):
    command = _extract_command(src_archive, extract_dir, recursive,
                               filelist_to_extract)
    proc = subprocess.Popen(command, stdout=subprocess.PIPE, bufsize=1,
                            stdin=subprocess.PIPE, startupinfo=startupinfo)
    # Error checking, progress feedback and subArchives for recursive unpacking
    index, errorLine, subArchives = 0, u'', []
    source_archive = src_archive.tail.s
    with proc.stdout as out:
        for line in iter(out.readline, b''):
            line = unicode(line, 'utf8')
            if regErrMatch(line):
                errorLine = line + u''.join(out)
                break
            maExtracting = regExtractMatch(line)
            if maExtracting:
                extracted = GPath(maExtracting.group(1).strip())
                if readExtensions and extracted.cext in readExtensions:
                    subArchives.append(extracted)
                if not progress: continue
                progress(index, source_archive + u'\n' + _(
                    u'Extracting files...') + u'\n' + extracted.s)
                index += 1
    returncode = proc.wait()
    if returncode or errorLine:
        raise StateError(u'%s: Extraction failed:\n7z.exe return value: %s\n%s'
                         % (source_archive, str(returncode), errorLine))
    return subArchives

def wrapPopenOut(command, wrapper, errorMsg):
    proc = subprocess.Popen(command, stdout=subprocess.PIPE, bufsize=-1,
                            stdin=subprocess.PIPE, startupinfo=startupinfo)
    out, unused_err = proc.communicate()
    wrapper(out)
    returncode = proc.returncode
    if returncode:
        raise StateError(errorMsg + u'\nPopen return value: %d' + returncode)

#  WIP: http://sevenzip.osdn.jp/chm/cmdline/switches/method.htm
def compressionSettings(archive_path, blockSize, isSolid):
    archiveType = writeExts.get(archive_path.cext)
    if not archiveType:
        #--Always fall back to using the defaultExt
        archive_path = GPath(archive_path.sbody + defaultExt).tail
        archiveType = writeExts.get(archive_path.cext)
    if archive_path.cext in noSolidExts: # zip
        solid = u''
    else:
        if isSolid:
            if blockSize:
                solid = u'-ms=on -ms=%dm' % blockSize
            else:
                solid = u'-ms=on'
        else:
            solid = u'-ms=off'
    userArgs = bass.inisettings['7zExtraCompressionArguments']
    if userArgs:
        if reSolid.search(userArgs):
            if not solid: # zip, will blow if ms=XXX is passed in
                old = userArgs
                userArgs = reSolid.sub(u'', userArgs).strip()
                if old != userArgs: deprint(archive_path.s +
                    u': 7zExtraCompressionArguments ini option "' + old +
                    u'" -> "' + userArgs + u'"')
            solid = userArgs
        else:
            solid += userArgs
    return archive_path, archiveType, solid

def compressCommand(destArchive, destDir, srcFolder, solid=u'-ms=on',
                    archiveType=u'7z'): # WIP - note solid on by default (7z)
    return [exe7z, u'a', destDir.join(destArchive).temp.s,
            u'-t%s' % archiveType] + solid.split() + [
            u'-y', u'-r', # quiet, recursive
            u'-o"%s"' % destDir.s,
            u'-scsUTF-8', u'-sccUTF-8', # encode output in unicode
            srcFolder.join(u'*').s] # add a wildcard at the end of the path

def _extract_command(archivePath, outDirPath, recursive, filelist_to_extract):
    command = u'"%s" x "%s" -y -bb1 -o"%s" -scsUTF-8 -sccUTF-8' % (
        exe7z, archivePath.s, outDirPath.s)
    if recursive: command += u' -r'
    if filelist_to_extract: command += (u' @"%s"' % filelist_to_extract)
    return command

def list_archive(archive_path, parse_archive_line, __reList=reListArchive):
    """Client is responsible for closing the file ! See uses for
    _parse_archive_line examples."""
    command = ur'"%s" l -slt -sccUTF-8 "%s"' % (exe7z, archive_path.s)
    ins, err = subprocess.Popen(command, stdout=subprocess.PIPE,
                                stderr=subprocess.STDOUT,
                                stdin=subprocess.PIPE,
                                startupinfo=startupinfo).communicate()
    for line in ins.splitlines(True): # keepends=True
        maList = __reList.match(line)
        if maList:
            parse_archive_line(*(maList.groups()))
