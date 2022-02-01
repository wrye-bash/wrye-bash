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
#  Wrye Bash copyright (C) 2005-2009 Wrye, 2010-2022 Wrye Bash Team
#  https://github.com/wrye-bash
#
# =============================================================================
import os
import re

from . import bass
from .bolt import GPath, deprint, popen_common, os_name
from .exception import StateError

exe7z = u'7z.exe' if os_name == u'nt' else u'7z'
defaultExt = u'.7z'
writeExts = {defaultExt: u'7z', u'.zip': u'zip'}
readExts = {u'.rar', u'.001'}
readExts.update(writeExts)
omod_exts = {u'.omod', u'.fomod'}
noSolidExts = {u'.zip'}
reSolid = re.compile(r'[-/]ms=[^\s]+', re.IGNORECASE)
regCompressMatch = re.compile(r'Compressing\s+(.+)', re.U).match
regExtractMatch = re.compile(u'- (.+)', re.U).match
reListArchive = re.compile(
    r'(Solid|Path|Size|CRC|Attributes|Method) = (.*?)(?:\r\n|\n)')

def compress7z(full_dest, rel_dest, srcDir, progress=None, *,
               is_solid=None, temp_list=None, blockSize=None):
    if is_solid is None:
        solid, archiveType = '-ms=on', '7z'
    else:
        new_rel_dest, archiveType, solid = _compressionSettings(
            rel_dest, blockSize, is_solid)
        if new_rel_dest != rel_dest:
            # We changed the extension, need to fix up full_dest too
            rel_dest = new_rel_dest
            full_dest = full_dest.root.join(new_rel_dest)
    join_star = srcDir.join(u'*').s # add a wildcard at the end of the path
    out_args = [join_star] if temp_list is None else [f'-i!{join_star}',
                                                      f'-x@{temp_list}']
    command = [exe7z, u'a', full_dest.temp.s, f'-t{archiveType}',
        *solid.split(), u'-y', u'-r', # quiet, recursive
        *out_args, u'-scsUTF-8', u'-sccUTF-8']  # encode output in UTF-8
    if progress is not None: #--Used solely for the progress bar
        length = sum(map(len, (files for x, y, files in os.walk(srcDir))))
        progress(0, f'{rel_dest}\n' + _(u'Compressing files...'))
        progress.setFull(1 + length)
    #--Pack the files
    proc = popen_common(command, bufsize=1, encoding='utf-8')
    #--Error checking and progress feedback
    index, lines = 0, []
    with proc.stdout as out:
        for line in out.readlines():
            lines.append(line)
            if progress is None: continue
            maCompressing = regCompressMatch(line)
            if maCompressing:
                progress(index, '\n'.join(
                    [f'{rel_dest}', _(u'Compressing files...'),
                     maCompressing.group(1).strip()]))
                index += 1
    returncode = proc.wait()
    if returncode:
        full_dest.temp.remove()
        raise StateError(
            f'{rel_dest}: Compression failed:\n7z.exe return value: '
            f'{returncode:d}\n{"".join(lines)}')
    #--Finalize the file, and cleanup
    full_dest.untemp()

def extract7z(src_archive, extract_dir, progress=None, readExtensions=None,
              recursive=False, filelist_to_extract=None):
    command = [exe7z, 'x', src_archive.s, '-y', '-bb1', f'-o{extract_dir}',
               '-scsUTF-8', '-sccUTF-8']
    if recursive: command.append('-r')
    if filelist_to_extract: command.append(f'@{filelist_to_extract}')
    proc = popen_common(command, bufsize=1, encoding='utf-8')
    # Error checking, progress feedback and subArchives for recursive unpacking
    index, lines, subArchives = 0, [], []
    with proc.stdout as out:
        for line in out.readlines():
            maExtracting = regExtractMatch(line)
            if maExtracting:
                extracted = GPath(maExtracting.group(1).strip())
                if readExtensions and extracted.cext in readExtensions:
                    subArchives.append(extracted)
                if not progress: continue
                progress(index, f'{src_archive.tail}\n' + _(
                    u'Extracting files...') + f'\n{extracted}')
                index += 1
    returncode = proc.wait()
    if returncode:
        raise StateError(f'{src_archive.tail}: Extraction failed:\n'
            f'7z.exe return value: {returncode:d}\n{"".join(lines)}')
    return subArchives

def wrapPopenOut(fullPath, wrapper, errorMsg):
    command = [exe7z, 'x', f'{fullPath}', 'BCF.dat', '-y', '-so', '-sccUTF-8']
    # No encoding, this is *supposed* to return bytes!
    proc = popen_common(command, bufsize=-1)
    out, unused_err = proc.communicate()
    wrapper(out)
    returncode = proc.returncode
    if returncode:
        raise StateError(f'{errorMsg}\nPopen return value: {returncode:d}')

#  WIP: http://sevenzip.osdn.jp/chm/cmdline/switches/method.htm
def _compressionSettings(fn_archive, blockSize, isSolid):
    archiveType = writeExts.get(fn_archive.cext)
    if not archiveType:
        #--Always fall back to using the defaultExt
        fn_archive = GPath(fn_archive.sbody + defaultExt).tail
        archiveType = writeExts[defaultExt]
    if fn_archive.cext in noSolidExts: # zip
        solid = u''
    else:
        if isSolid:
            if blockSize:
                solid = f'-ms=on -ms={blockSize:d}m'
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
                    f'{fn_archive}: 7zExtraCompressionArguments ini option '
                    f'"{old}" -> "{userArgs}"')
            solid = userArgs
        else:
            solid += userArgs
    return fn_archive, archiveType, solid

def list_archive(archive_path, parse_archive_line, __reList=reListArchive):
    """Client is responsible for closing the file ! See uses for
    _parse_archive_line examples."""
    command = [exe7z, 'l', '-slt', '-sccUTF-8', f'{archive_path}']
    proc = popen_common(command, encoding='utf-8')
    ins, _err = proc.communicate()
    for line in ins.splitlines(True): # keepends=True
        maList = __reList.match(line)
        if maList:
            parse_archive_line(*(maList.groups()))
