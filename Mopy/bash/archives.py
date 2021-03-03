# -*- coding: utf-8 -*-
#
# GPL License and Copyright Notice ============================================
#  This file is part of Wrye Bash.
#
#  Wrye Bash is free software: you can redistribute it and/or
#  modify it under the terms of the GNU General Public License
#  as published by the Free Software Foundation, either version 3
#  of the License, or (at your option) any later version.
#
#  Wrye Bash is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
#
#  You should have received a copy of the GNU General Public License
#  along with Wrye Bash.  If not, see <https://www.gnu.org/licenses/>.
#
#  Wrye Bash copyright (C) 2005-2009 Wrye, 2010-2021 Wrye Bash Team
#  https://github.com/wrye-bash
#
# =============================================================================
import os
import re
import subprocess

from . import bass
from .bolt import startupinfo, GPath, deprint, walkdir
from .exception import StateError

exe7z = u'7z.exe' if os.name == u'nt' else u'7z'
# TODO(inf) stuck it here for now - should probably go somewhere else
pngcrush = u'pngcrush.exe' if os.name == u'nt' else u'pngcrush'
defaultExt = u'.7z'
writeExts = {u'.7z': u'7z', u'.zip': u'zip'}
readExts = {u'.rar', u'.7z.001', u'.001'}
readExts.update(writeExts)
noSolidExts = {u'.zip'}
reSolid = re.compile(u'' r'[-/]ms=[^\s]+', re.IGNORECASE)
regCompressMatch = re.compile(u'' r'Compressing\s+(.+)', re.U).match
regExtractMatch = re.compile(u'- (.+)', re.U).match
regErrMatch = re.compile(u'^(Error:.+|.+ {5}Data Error?|Sub items Errors:.+)',
    re.U).match
reListArchive = re.compile(
    u'(Solid|Path|Size|CRC|Attributes|Method) = (.*?)(?:\r\n|\n)')

def compress7z(command, full_dest, rel_dest, srcDir, progress=None):
    if progress is not None: #--Used solely for the progress bar
        length = sum([len(files) for x, y, files in walkdir(srcDir.s)])
        progress(0, u'%s\n' % rel_dest + _(u'Compressing files...'))
        progress.setFull(1 + length)
    #--Pack the files
    proc = subprocess.Popen(command, stdout=subprocess.PIPE, bufsize=1,
                            stdin=subprocess.PIPE, # needed for some commands
                            startupinfo=startupinfo)
    #--Error checking and progress feedback
    index, errorLine = 0, u''
    with proc.stdout as out:
        for line in iter(out.readline, b''):
            line = unicode(line, u'utf8') # utf-8 is ok, see compressCommand
            if regErrMatch(line):
                errorLine = line + u''.join(out)
                break
            if progress is None: continue
            maCompressing = regCompressMatch(line)
            if maCompressing:
                progress(index, u'%s\n' % rel_dest + _(
                    u'Compressing files...') + u'\n' + maCompressing.group(
                    1).strip())
                index += 1
    returncode = proc.wait()
    if returncode or errorLine:
        full_dest.temp.remove()
        raise StateError(u'%s: Compression failed:\n7z.exe return value: '
                         u'%d\n%s' % (rel_dest, returncode, errorLine))
    #--Finalize the file, and cleanup
    full_dest.untemp()

def extract7z(src_archive, extract_dir, progress=None, readExtensions=None,
              recursive=False, filelist_to_extract=None):
    command = _extract_command(src_archive, extract_dir, recursive,
                               filelist_to_extract)
    proc = subprocess.Popen(command, stdout=subprocess.PIPE, bufsize=1,
                            stdin=subprocess.PIPE, startupinfo=startupinfo)
    # Error checking, progress feedback and subArchives for recursive unpacking
    index, errorLine, subArchives = 0, u'', []
    with proc.stdout as out:
        for line in iter(out.readline, b''):
            line = unicode(line, u'utf8')
            if regErrMatch(line):
                errorLine = line + u''.join(out)
                break
            maExtracting = regExtractMatch(line)
            if maExtracting:
                extracted = GPath(maExtracting.group(1).strip())
                if readExtensions and extracted.cext in readExtensions:
                    subArchives.append(extracted)
                if not progress: continue
                progress(index, u'%s\n' % src_archive.tail + _(
                    u'Extracting files...') + u'\n%s' % extracted)
                index += 1
    returncode = proc.wait()
    if returncode or errorLine:
        raise StateError(
            u'%s: Extraction failed:\n7z.exe return value: %d\n%s' % (
                src_archive.tail, returncode, errorLine))
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
    userArgs = bass.inisettings[u'7zExtraCompressionArguments']
    if userArgs:
        if reSolid.search(userArgs):
            if not solid: # zip, will blow if ms=XXX is passed in
                old = userArgs
                userArgs = reSolid.sub(u'', userArgs).strip()
                if old != userArgs: deprint(
                    u'%s: 7zExtraCompressionArguments ini option "%s" -> '
                    u'"%s"' % (archive_path, old, userArgs))
            solid = userArgs
        else:
            solid += userArgs
    return archive_path, archiveType, solid

def compressCommand(destArchive, destDir, srcFolder, solid=u'-ms=on',
                    archiveType=u'7z'): # WIP - note solid on by default (7z)
    return [exe7z, u'a', destArchive.temp.s,
            u'-t%s' % archiveType] + solid.split() + [
            u'-y', u'-r', # quiet, recursive
            u'-o"%s"' % destDir,
            u'-scsUTF-8', u'-sccUTF-8', # encode output in unicode
            srcFolder.join(u'*').s] # add a wildcard at the end of the path

def _extract_command(archivePath, outDirPath, recursive, filelist_to_extract):
    command = u'"%s" x "%s" -y -bb1 -o"%s" -scsUTF-8 -sccUTF-8' % (
        exe7z, archivePath, outDirPath)
    if recursive: command += u' -r'
    if filelist_to_extract: command += (u' @"%s"' % filelist_to_extract)
    return command

def list_archive(archive_path, parse_archive_line, __reList=reListArchive):
    """Client is responsible for closing the file ! See uses for
    _parse_archive_line examples."""
    command = u'"%s" l -slt -sccUTF-8 "%s"' % (exe7z, archive_path)
    ins, err = subprocess.Popen(command, stdout=subprocess.PIPE,
                                stderr=subprocess.STDOUT,
                                stdin=subprocess.PIPE,
                                startupinfo=startupinfo).communicate()
    for line in ins.splitlines(True): # keepends=True
        maList = __reList.match(line)
        if maList:
            parse_archive_line(*(maList.groups()))
