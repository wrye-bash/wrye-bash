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
#  Wrye Bash copyright (C) 2005-2009 Wrye, 2010-2023 Wrye Bash Team
#  https://github.com/wrye-bash
#
# =============================================================================

import io
import lzma
import re
import subprocess

from .. import archives, bass, bolt, env
from ..bolt import Path, decoder, encode, pack_byte, pack_byte_signed, \
    pack_int_signed, popen_common, startupinfo, unpack_byte, \
    unpack_int64_signed, unpack_int_signed, unpack_short, GPath_no_norm
from ..exception import StateError
from ..wbtemp import TempDir, TempFile

def _readNetString(open_file):
    """Read a .net string. THIS CODE IS DUBIOUS!"""
    pos = open_file.tell()
    strLen = unpack_byte(open_file)
    if strLen >= 128:
        open_file.seek(pos)
        strLen = unpack_short(open_file)
        strLen = strLen & 0x7f | (strLen >> 1) & 0xff80
        if strLen > 0x7FFF:
            raise NotImplementedError('String too long to convert.')
    return open_file.read(strLen)

def _writeNetString(open_file, string):
    """Write string as a .net string. THIS CODE IS DUBIOUS!"""
    strLen = len(string)
    if strLen < 128:
        pack_byte_signed(open_file, strLen)
    elif strLen > 0x7FFF: #--Actually probably fails earlier.
        raise NotImplementedError('String too long to convert.')
    else:
        strLen =  0x80 | strLen & 0x7f | (strLen & 0xff80) << 1
        pack_byte_signed(open_file, strLen)
    open_file.write(string)

failedOmods = set()

class OmodFile(object):
    """Class for extracting data from OMODs."""
    def __init__(self, omod_path):
        self.omod_path = omod_path
        # FOMOD format is slightly different - doesn't need to have a config,
        # for example
        self._is_fomod = omod_path.cext == u'.fomod'

    def readConfig(self, conf_path):
        """Read info about the omod from the 'config' file"""
        with open(conf_path, u'rb') as omod_config:
            self.version = unpack_byte(omod_config) # OMOD version
            self.modName = decoder(_readNetString(omod_config)) # Mod name
            # TODO(ut) original code unpacked signed int, maybe that's why "weird numbers" ?
            self.major = unpack_int_signed(omod_config) # Mod major version - getting weird numbers here though
            self.minor = unpack_int_signed(omod_config) # Mod minor version
            self.omod_author = decoder(_readNetString(omod_config)) # om_author
            self.email = decoder(_readNetString(omod_config)) # email
            self.website = decoder(_readNetString(omod_config)) # website
            self.desc = decoder(_readNetString(omod_config)) # description
            if self.version >= 2:
                self.ftime = unpack_int64_signed(omod_config) # creation time
            else:
                self.ftime = decoder(_readNetString(omod_config))
            self.compType = unpack_byte(omod_config) # Compression type. 0 = lzma, 1 = zip
            if self.version >= 1:
                self.build = unpack_int_signed(omod_config)
            else:
                self.build = -1

    def writeInfo(self, dest_path, filename, readme, scr_exists):
        with dest_path.open(u'wb') as out:
            out.write(encode(filename))
            out.write(b'\n\n[basic info]\n')
            out.write(b'Name: ')
            out.write(encode(filename[:-5]))
            out.write(b'\nAuthor: ')
            out.write(encode(self.omod_author))
            out.write(b'\nVersion:') ##: add version?
            out.write(b'\nContact: ')
            out.write(encode(self.email))
            out.write(b'\nWebsite: ')
            out.write(encode(self.website))
            out.write(b'\n\n')
            out.write(encode(self.desc))
            out.write(b'\n\n')
            #fTime = time.gmtime(self.ftime) #-error
            #file.write(b'Date this omod was compiled: %s-%s-%s %s:%s:%s\n' % (fTime.tm_mon, fTime.tm_mday, fTime.tm_year, fTime.tm_hour, fTime.tm_min, fTime.tm_sec))
            out.write(b'Contains readme: %s\n' % (b'yes' if readme else b'no'))
            out.write(b'Contains script: %s\n' % (b'yes' if scr_exists else b'no'))
            # Skip the reset that OBMM puts in

    def getOmodContents(self):
        """Return a list of the files and their uncompressed sizes, and the total uncompressed size of an archive"""
        # Get contents of archive
        filesizes = {}
        reFileSize = re.compile(r'[0-9]{4}-[0-9]{2}-[0-9]{2}\s+'
                                r'[0-9]{2}:[0-9]{2}:[0-9]{2}.{6}\s+'
                                r'([0-9]+)\s+[0-9]*\s+(.+?)$')
        cmd7z = [archives.exe7z, u'l', u'-r', u'-sccUTF-8', self.omod_path.s]
        with popen_common(cmd7z, encoding='utf-8').stdout as ins:
            for line in ins:
                maFileSize = reFileSize.match(line)
                if maFileSize:  #also matches the last line with total sizes
                    name_ = maFileSize.group(2).strip().strip(u'\r')
                    filesizes[name_] = int(maFileSize.group(1))
        # drop the last line entry
        del filesizes[list(filesizes)[-1]]
        return filesizes, sum(filesizes.values())

    def extractToProject(self, outDir: Path, progress, ask_confirm):
        """Extract the contents of the OMOD to a project, with OMOD conversion
        data."""
        progress = progress if progress else bolt.Progress()
        with TempDir() as ed_temp, TempDir() as stage_base_dir:
            extract_dir = GPath_no_norm(ed_temp)
            stage_dir = GPath_no_norm(stage_base_dir).join(outDir.stail)
            try:
                stail_fmt = f'{self.omod_path.stail}\n'
                progress(0, f"{stail_fmt}{_('Extracting...')}")
                if self._is_fomod:
                    self._extract_fomod(extract_dir, stage_dir)
                else:
                    self._extract_omod(progress, extract_dir, stage_dir)
                progress(1, f"{stail_fmt}{_('Extracted')}")
                # Move files to final directory
                env.shellMove({stage_dir: outDir}, ask_confirm=ask_confirm,
                    allow_undo=True, auto_rename=True)
            except Exception:
                # Error occurred, see if final output dir needs deleting
                env.shellDeletePass(outDir, parent=progress.getParent())
                raise

    def _extract_omod(self, progress, extractDir, stageDir):
        """Extracts a .omod file into stageDir. They have configs that we need
        to create OMOD conversion data from and package their files into
        'plugins' and 'data' files along with CRC files."""
        # Get contents of archive
        sizes_,total = self.getOmodContents()
        # Extract the files
        reExtracting = re.compile(u'- (.+)', re.U)
        subprogress = bolt.SubProgress(progress, 0, 0.4)
        omod_tail = self.omod_path.stail
        current = 0
        cmd7z = [archives.exe7z, u'e', u'-r', u'-sccUTF-8', self.omod_path.s,
                 f'-o{extractDir}', u'-bb1']
        with popen_common(cmd7z, encoding='utf-8').stdout as ins:
            for line in ins:
                maExtracting = reExtracting.match(line)
                if maExtracting:
                    name_ = maExtracting.group(1).strip().strip(u'\r')
                    subprogress(float(current) / total, omod_tail + u'\n' + _(u'Extracting...') + u'\n' + name_)
                    current += sizes_[name_]
        # Get compression type
        progress(0.4, omod_tail + u'\n' + _(u'Reading config'))
        self.readConfig(extractDir.join(u'config'))
        # Collect OMOD conversion data
        ocdDir = stageDir.join(u'omod conversion data')
        prog_pref = omod_tail + u'\n' + _(u'Creating omod conversion data')
        progress(0.46, prog_pref + u'\ninfo.txt')
        scr_path = extractDir.join(u'script')
        readme_path = extractDir.join(u'readme')
        readme_exists = readme_path.exists()
        scr_exists = scr_path.exists()
        self.writeInfo(ocdDir.join(u'info.txt'), omod_tail,
                       readme_exists, scr_exists)
        progress(0.47, prog_pref + u'\nscript')
        if scr_exists:
            with scr_path.open(u'rb') as ins:
                with ocdDir.join(u'script.txt').open(u'wb') as output:
                    output.write(_readNetString(ins))
        progress(0.48, prog_pref + u'\nreadme.rtf')
        if readme_exists:
            with readme_path.open(u'rb') as ins:
                with ocdDir.join(u'readme.rtf').open(u'wb') as output:
                    output.write(_readNetString(ins))
        progress(0.49, prog_pref + u'\nscreenshot')
        try: extractDir.join(u'image').moveTo(ocdDir.join(u'screenshot'))
        except StateError: pass # image file does not exist
        progress(0.5, prog_pref + u'\nconfig')
        extractDir.join(u'config').moveTo(ocdDir.join(u'config'))
        # Extract the files
        if self.compType == 0:
            extract = self.extractFiles7z
        else:
            extract = self.extractFilesZip
        pluginSize = sizes_.get(u'plugins',0)
        dataSize = sizes_.get(u'data',0)
        subprogress = bolt.SubProgress(progress, 0.5, 1)
        if extractDir.join(u'plugins.crc').exists() and extractDir.join(u'plugins').exists():
            pluginProgress = bolt.SubProgress(subprogress, 0, float(pluginSize) / (pluginSize + dataSize))
            extract(extractDir.join(u'plugins.crc'), extractDir.join(u'plugins'), stageDir, pluginProgress)
        if extractDir.join(u'data.crc').exists() and extractDir.join(u'data').exists():
            dataProgress = bolt.SubProgress(subprogress, subprogress.state, 1)
            extract(extractDir.join(u'data.crc'), extractDir.join(u'data'), stageDir, dataProgress)

    def _extract_fomod(self, extractDir, stageDir):
        """Extracts a .fomod file into stageDir. Unlike .omod files, these are
        pretty much just renamed .7z files. They don't pack files into binary
        blobs, they just contain a folder-and-files structure like any other
        archive."""
        archives.extract7z(self.omod_path, extractDir)
        env.shellMove({extractDir: stageDir})

    def extractFilesZip(self, crcPath, dataPath, outPath, progress):
        fileNames, crcs, sizes_ = self.getFile_CrcSizes(crcPath)
        if len(fileNames) == 0: return
        # Extracted data stream is saved as a file named 'a'
        base_msg = (self.omod_path.stail + u'\n' +
                    _(u'Unpacking %s') % dataPath.stail)
        progress(0, base_msg)
        cmd = [archives.exe7z, u'e', u'-r', u'-sccUTF-8', dataPath.s,
               f'-o{outPath}']
        subprocess.call(cmd, startupinfo=startupinfo)
        # Split the uncompress stream into files
        progress(0.7)
        stream_path = outPath.join(u'a')
        s_prog = bolt.SubProgress(progress, 0.7, 1.0, len(fileNames))
        with stream_path.open('rb') as ins:
            self.splitStream(ins, outPath, fileNames, sizes_, s_prog,
                             base_msg)
        progress(1)
        # Clean up
        outPath.join(u'a').remove()

    def splitStream(self, in_stream, outDir, fileNames, sizes_, progress,
            base_progress_msg):
        progress.setFull(len(fileNames))
        progress(0, base_progress_msg)
        # Split the uncompressed stream into files
        for i, fname in enumerate(fileNames):
            fn_str = fname.decode('utf-8')
            progress(i, base_progress_msg + f'\n{fn_str}')
            outFile = outDir.join(fn_str)
            with outFile.open(u'wb') as out:
                out.write(in_stream.read(sizes_[i]))
        progress(len(fileNames))

    def extractFiles7z(self, crcPath, dataPath, outPath, progress):
        fileNames, crcs, sizes_ = self.getFile_CrcSizes(crcPath)
        if len(fileNames) == 0: return
        totalSize = sum(sizes_)
        base_msg = (self.omod_path.stail + u'\n' +
                    _(u'Unpacking %s') % dataPath.stail)
        # Extract data stream to an uncompressed stream
        dpath_size = dataPath.psize
        out = io.BytesIO()
        with dataPath.open(u'rb') as ins:
            # Decoder properties
            out.write(ins.read(5))
            # Next 8 bytes are the size of the data stream
            for i in range(8):
                pack_byte(out, totalSize >> (i * 8) & 0xFF)
            # Now copy the data stream
            while ins.tell() < dpath_size:
                out.write(ins.read(2097152)) # 2MB at a time
        # Now decompress
        uncompressed = io.BytesIO(lzma.decompress(out.getvalue()))
        # Split the uncompressed stream into files
        self.splitStream(uncompressed, outPath, fileNames, sizes_, progress,
            base_msg)

    @staticmethod
    def getFile_CrcSizes(crc_file_path):
        fileNames = []
        crcs = []
        sizes_ = []
        crc_file_size = crc_file_path.psize
        with open(crc_file_path, u'rb') as crc_file:
            while crc_file.tell() < crc_file_size:
                fileNames.append(_readNetString(crc_file))
                crcs.append(unpack_int_signed(crc_file))
                sizes_.append(unpack_int64_signed(crc_file))
        return fileNames, crcs, sizes_

class OmodConfig(object):
    """Tiny little omod config class."""
    def __init__(self, omod_proj):
        self.omod_proj = omod_proj
        self.vMajor = 0
        self.vMinor = 1
        self.vBuild = 0
        self.omod_author = u''
        self.email = u''
        self.website = u''
        self.abstract = u''

    @staticmethod
    def getOmodConfig(omod_proj):
        """Get obmm config file for project."""
        config = OmodConfig(omod_proj)
        configPath = bass.dirs[u'installers'].join(omod_proj,
            u'omod conversion data', u'config')
        if configPath.exists():
            with open(configPath,u'rb') as ins:
                ins.read(1) #--Skip first four bytes
                # OBMM can support UTF-8, so try that first, then fail back to
                config.omod_proj = decoder(_readNetString(ins),
                                           encoding=u'utf-8')
                config.vMajor = unpack_int_signed(ins)
                config.vMinor = unpack_int_signed(ins)
                for attr in (u'omod_author',u'email',u'website',u'abstract'):
                    setattr(config, attr,
                            decoder(_readNetString(ins), encoding=u'utf-8'))
                ins.read(8) #--Skip date-time
                ins.read(1) #--Skip zip-compression
                #config['vBuild'], = ins.unpack('I',4)
        return config

    def writeOmodConfig(self):
        """Write obmm config file for project."""
        configPath = bass.dirs[u'installers'].join(self.omod_proj,
            u'omod conversion data', u'config')
        configPath.head.makedirs()
        with TempFile() as tmp_config:
            with open(tmp_config, 'wb') as out:
                pack_byte(out, 4)
                _writeNetString(out, self.omod_proj.encode('utf-8'))
                pack_int_signed(out, self.vMajor)
                pack_int_signed(out, self.vMinor)
                for attr in ('omod_author', 'email', 'website', 'abstract'):
                    # OBMM reads it fine if in UTF-8, so we'll do that.
                    _writeNetString(out, getattr(self, attr).encode('utf-8'))
                # Some random date and time
                out.write(b'\x74\x1a\x74\x67\xf2\x7a\xca\x88')
                pack_byte_signed(out, 0) #--zip compression (will be ignored)
                out.write(b'\xFF\xFF\xFF\xFF')
            configPath.replace_with_temp(tmp_config)
