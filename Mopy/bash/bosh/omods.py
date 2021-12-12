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

import collections
import re
import subprocess
from .. import env, bolt, bass, archives
from ..bolt import decoder, encode, Path, startupinfo, unpack_int_signed, \
    unpack_byte, unpack_short, unpack_int64_signed, pack_byte_signed, \
    pack_byte, pack_int_signed, popen_common

def _readNetString(open_file):
    """Read a .net string. THIS CODE IS DUBIOUS!"""
    pos = open_file.tell()
    strLen = unpack_byte(open_file)
    if strLen >= 128:
        open_file.seek(pos)
        strLen = unpack_short(open_file)
        strLen = strLen & 0x7f | (strLen >> 1) & 0xff80
        if strLen > 0x7FFF:
            raise NotImplementedError(u'String too long to convert.')
    return open_file.read(strLen)

def _writeNetString(open_file, string):
    """Write string as a .net string. THIS CODE IS DUBIOUS!"""
    strLen = len(string)
    if strLen < 128:
        pack_byte_signed(open_file, strLen)
    elif strLen > 0x7FFF: #--Actually probably fails earlier.
        raise NotImplementedError(u'String too long to convert.')
    else:
        strLen =  0x80 | strLen & 0x7f | (strLen & 0xff80) << 1
        pack_byte_signed(open_file, strLen)
    open_file.write(string)

failedOmods = set()

def extractOmodsNeeded(installers_paths=()):
    """Return true if .omod files are present, requiring extraction."""
    for inst_path in installers_paths:
        if (inst_path.cext in archives.omod_exts and
                inst_path not in failedOmods):
            return True
    return False

class OmodFile(object):
    """Class for extracting data from OMODs."""
    def __init__(self, omod_path):
        self.omod_path = omod_path
        # FOMOD format is slightly different - doesn't need to have a config,
        # for example
        self._is_fomod = omod_path.cext == u'.fomod'

    def readConfig(self, conf_path):
        """Read info about the omod from the 'config' file"""
        with open(conf_path.s, u'rb') as omod_config:
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
        filesizes = collections.OrderedDict()
        reFileSize = re.compile(r'[0-9]{4}-[0-9]{2}-[0-9]{2}\s+[0-9]{2}:[0-9]{2}:[0-9]{2}.{6}\s+([0-9]+)\s+[0-9]*\s+(.+?)$', re.U)
        with self.omod_path.unicodeSafe() as tempOmod:
            cmd7z = [archives.exe7z, u'l', u'-r', u'-sccUTF-8', tempOmod.s]
            with popen_common(cmd7z, encoding='utf-8').stdout as ins:
                for line in ins:
                    maFileSize = reFileSize.match(line)
                    if maFileSize: #also matches the last line with total sizes
                        name_ = maFileSize.group(2).strip().strip(u'\r')
                        filesizes[name_] = int(maFileSize.group(1))
        # drop the last line entry
        del filesizes[list(filesizes)[-1]]
        return filesizes, sum(filesizes.values())

    def extractToProject(self,outDir,progress=None):
        """Extract the contents of the omod to a project, with omod conversion data"""
        progress = progress if progress else bolt.Progress()
        extractDir = stageBaseDir = Path.tempDir()
        stageDir = stageBaseDir.join(outDir.tail)
        try:
            progress(0, self.omod_path.stail + u'\n' + _(u'Extracting...'))
            if self._is_fomod:
                self._extract_fomod(extractDir, stageDir)
            else:
                self._extract_omod(progress, extractDir, stageDir)
            progress(1, self.omod_path.stail + u'\n' + _(u'Extracted'))
            # Move files to final directory
            env.shellMove(stageDir, outDir.head, parent=None,
                          askOverwrite=True, allowUndo=True, autoRename=True)
        except Exception:
            # Error occurred, see if final output dir needs deleting
            env.shellDeletePass(outDir, parent=progress.getParent())
            raise
        finally:
            # Clean up temp directories
            extractDir.rmtree(safety=extractDir.stail)
            stageBaseDir.rmtree(safety=stageBaseDir.stail)

    def _extract_omod(self, progress, extractDir, stageDir):
        """Extracts a .omod file into stageDir. They have configs that we need
        to create OMOD conversion data from and package their files into
        'plugins' and 'data' files along with CRC files."""
        # Get contents of archive
        sizes_,total = self.getOmodContents()
        # Extract the files
        reExtracting = re.compile(u'- (.+)', re.U)
        subprogress = bolt.SubProgress(progress, 0, 0.4)
        current = 0
        with self.omod_path.unicodeSafe() as tempOmod:
            cmd7z = [archives.exe7z, u'e', u'-r', u'-sccUTF-8', tempOmod.s, u'-o%s' % extractDir, u'-bb1']
            with popen_common(cmd7z, encoding='utf-8').stdout as ins:
                for line in ins:
                    maExtracting = reExtracting.match(line)
                    if maExtracting:
                        name_ = maExtracting.group(1).strip().strip(u'\r')
                        subprogress(float(current) / total, self.omod_path.stail + u'\n' + _(u'Extracting...') + u'\n' + name_)
                        current += sizes_[name_]
        # Get compression type
        progress(0.4, self.omod_path.stail + u'\n' + _(u'Reading config'))
        self.readConfig(extractDir.join(u'config'))
        # Collect OMOD conversion data
        ocdDir = stageDir.join(u'omod conversion data')
        progress(0.46, self.omod_path.stail + u'\n' + _(u'Creating omod conversion data') + u'\ninfo.txt')
        scr_path = extractDir.join(u'script')
        readme_path = extractDir.join(u'readme')
        readme_exists = readme_path.exists()
        scr_exists = scr_path.exists()
        self.writeInfo(ocdDir.join(u'info.txt'), self.omod_path.stail,
                       readme_exists, scr_exists)
        progress(0.47, self.omod_path.stail + u'\n' + _(u'Creating omod conversion data') + u'\nscript')
        if scr_exists:
            with scr_path.open(u'rb') as ins:
                with ocdDir.join(u'script.txt').open(u'wb') as output:
                    output.write(_readNetString(ins))
        progress(0.48, self.omod_path.stail + u'\n' + _(u'Creating omod conversion data') + u'\nreadme.rtf')
        if readme_exists:
            with readme_path.open(u'rb') as ins:
                with ocdDir.join(u'readme.rtf').open(u'wb') as output:
                    output.write(_readNetString(ins))
        progress(0.49, self.omod_path.stail + u'\n' + _(u'Creating omod conversion data') + u'\nscreenshot')
        if extractDir.join(u'image').exists():
            extractDir.join(u'image').moveTo(ocdDir.join(u'screenshot'))
        progress(0.5, self.omod_path.stail + u'\n' + _(u'Creating omod conversion data') + u'\nconfig')
        extractDir.join(u'config').moveTo(ocdDir.join(u'config'))
        # Extract the files
        if self.compType == 0:
            extract = self.extractFiles7z
        else:
            extract = self.extractFilesZip
        pluginSize = sizes_.get(u'plugins',0)
        dataSize = sizes_.get(u'data',0)
        subprogress = bolt.SubProgress(progress, 0.5, 1)
        with stageDir.unicodeSafe() as tempOut:
            if extractDir.join(u'plugins.crc').exists() and extractDir.join(u'plugins').exists():
                pluginProgress = bolt.SubProgress(subprogress, 0, float(pluginSize)/(pluginSize+dataSize))
                extract(extractDir.join(u'plugins.crc'),extractDir.join(u'plugins'),tempOut,pluginProgress)
            if extractDir.join(u'data.crc').exists() and extractDir.join(u'data').exists():
                dataProgress = bolt.SubProgress(subprogress, subprogress.state, 1)
                extract(extractDir.join(u'data.crc'),extractDir.join(u'data'),tempOut,dataProgress)

    def _extract_fomod(self, extractDir, stageDir):
        """Extracts a .fomod file into stageDir. Unlike .omod files, these are
        pretty much just renamed .7z files. They don't pack files into binary
        blobs, they just contain a folder-and-files structure like any other
        archive."""
        # Needed since stageDir is a subdir of extractDir. We can't move a
        # parent dir into its subdir (duh), so just make a small temp subdir
        temp_extract = extractDir.join(u'out')
        with self.omod_path.unicodeSafe() as tempOmod:
            archives.extract7z(tempOmod, temp_extract)
        env.shellMove(temp_extract, stageDir, parent=None)

    def extractFilesZip(self, crcPath, dataPath, outPath, progress):
        fileNames, crcs, sizes_ = self.getFile_CrcSizes(crcPath)
        if len(fileNames) == 0: return

        # Extracted data stream is saved as a file named 'a'
        progress(0, self.omod_path.tail + u'\n' + _(u'Unpacking %s') % dataPath.stail)
        cmd = [archives.exe7z, u'e', u'-r', u'-sccUTF-8', dataPath.s, u'-o%s' % outPath]
        subprocess.call(cmd, startupinfo=startupinfo)

        # Split the uncompress stream into files
        progress(0.7, self.omod_path.stail + u'\n' + _(u'Unpacking %s') % dataPath.stail)
        self.splitStream(outPath.join(u'a'), outPath, fileNames, sizes_,
                         bolt.SubProgress(progress,0.7,1.0,len(fileNames))
                         )
        progress(1)

        # Clean up
        outPath.join(u'a').remove()

    def splitStream(self, streamPath, outDir, fileNames, sizes_, progress):
        # Split the uncompressed stream into files
        progress(0, self.omod_path.stail + u'\n' + _(u'Unpacking %s') % streamPath.stail)
        with streamPath.open(u'rb') as bin_out:
            for i,fname in enumerate(fileNames):
                progress(i, self.omod_path.stail + u'\n' + _(u'Unpacking %s') % streamPath.stail + u'\n' + fname)
                outFile = outDir.join(fname)
                with outFile.open(u'wb') as output:
                    output.write(bin_out.read(sizes_[i]))
        progress(len(fileNames))

    def extractFiles7z(self, crcPath, dataPath, outPath, progress):
        fileNames, crcs, sizes_ = self.getFile_CrcSizes(crcPath)
        if len(fileNames) == 0: return
        totalSize = sum(sizes_)

        # Extract data stream to an uncompressed stream
        subprogress = bolt.SubProgress(progress, 0, 0.3, full=dataPath.psize)
        subprogress(0, self.omod_path.stail + u'\n' + _(u'Unpacking %s') % dataPath.stail)
        with dataPath.open(u'rb') as ins:
            done = 0
            with open(outPath.join(dataPath.sbody+u'.tmp').s, u'wb') as output:
                # Decoder properties
                output.write(ins.read(5))
                done += 5
                subprogress(5)

                # Next 8 bytes are the size of the data stream
                for i in range(8):
                    out = totalSize >> (i*8)
                    pack_byte(output, out & 0xFF)
                    done += 1
                    subprogress(done)

                # Now copy the data stream
                while ins.tell() < dataPath.psize:
                    output.write(ins.read(512))
                    done += 512
                    subprogress(done)

        # Now decompress
        progress(0.3)
        cmd = [bass.dirs[u'compiled'].join(u'lzma').s,u'd',outPath.join(dataPath.sbody+u'.tmp').s, outPath.join(dataPath.sbody+u'.uncomp').s]
        subprocess.call(cmd, startupinfo=startupinfo)
        progress(0.8)

        # Split the uncompressed stream into files
        self.splitStream(outPath.join(dataPath.sbody+u'.uncomp'), outPath, fileNames, sizes_,
                         bolt.SubProgress(progress,0.8,1.0,full=len(fileNames))
                         )
        progress(1)

        # Clean up temp files
        outPath.join(dataPath.sbody+u'.uncomp').remove()
        outPath.join(dataPath.sbody+u'.tmp').remove()

    @staticmethod
    def getFile_CrcSizes(crc_file_path):
        fileNames = list()
        crcs = list()
        sizes_ = list()
        with open(crc_file_path.s, u'rb') as crc_file:
            while crc_file.tell() < crc_file_path.psize:
                fileNames.append(_readNetString(crc_file))
                crcs.append(unpack_int_signed(crc_file))
                sizes_.append(unpack_int64_signed(crc_file))
        return fileNames,crcs,sizes_

class OmodConfig(object):
    """Tiny little omod config class."""
    def __init__(self, omod_proj):
        self.omod_proj = omod_proj.s
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
            with open(configPath.s,u'rb') as ins:
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
        with open(configPath.temp.s,u'wb') as out:
            pack_byte(out, 4)
            _writeNetString(out, self.omod_proj.encode(u'utf8'))
            pack_int_signed(out, self.vMajor)
            pack_int_signed(out, self.vMinor)
            for attr in (u'omod_author', u'email', u'website', u'abstract'):
                # OBMM reads it fine if in UTF-8, so we'll do that.
                _writeNetString(out, getattr(self, attr).encode(u'utf-8'))
            out.write(b'\x74\x1a\x74\x67\xf2\x7a\xca\x88') #--Random date time
            pack_byte_signed(out, 0) #--zip compression (will be ignored)
            out.write(b'\xFF\xFF\xFF\xFF')
        configPath.untemp()
