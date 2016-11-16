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
#  Wrye Bash copyright (C) 2005-2009 Wrye, 2010-2015 Wrye Bash Team
#  https://github.com/wrye-bash
#
# =============================================================================
import re
import subprocess
from subprocess import PIPE
from .. import env, bolt, bass, archives
from ..bolt import decode, encode, Path, startupinfo

failedOmods = set()

def extractOmodsNeeded(installers_paths=()):
    """Return true if .omod files are present, requiring extraction."""
    for inst_path in installers_paths:
        if inst_path.cext == u'.omod' and inst_path not in failedOmods:
            return True
    return False

class OmodFile:
    """Class for extracting data from OMODs."""
    def __init__(self, omod_path):
        self.omod_path = omod_path

    def readConfig(self, conf_path):
        """Read info about the omod from the 'config' file"""
        with bolt.BinaryFile(conf_path.s) as omod_config:
            self.version = omod_config.readByte() # OMOD version
            self.modName = decode(omod_config.readNetString()) # Mod name
            self.major = omod_config.readInt32() # Mod major version - getting weird numbers here though
            self.minor = omod_config.readInt32() # Mod minor version
            self.author = decode(omod_config.readNetString()) # author
            self.email = decode(omod_config.readNetString()) # email
            self.website = decode(omod_config.readNetString()) # website
            self.desc = decode(omod_config.readNetString()) # description
            if self.version >= 2:
                self.ftime = omod_config.readInt64() # creation time
            else:
                self.ftime = decode(omod_config.readNetString())
            self.compType = omod_config.readByte() # Compression type. 0 = lzma, 1 = zip
            if self.version >= 1:
                self.build = omod_config.readInt32()
            else:
                self.build = -1

    def writeInfo(self, dest_path, filename, readme, script):
        with dest_path.open('w') as file:
            file.write(encode(filename))
            file.write('\n\n[basic info]\n')
            file.write('Name: ')
            file.write(encode(filename[:-5]))
            file.write('\nAuthor: ')
            file.write(encode(self.author))
            file.write('\nVersion:') # TODO, fix this?
            file.write('\nContact: ')
            file.write(encode(self.email))
            file.write('\nWebsite: ')
            file.write(encode(self.website))
            file.write('\n\n')
            file.write(encode(self.desc))
            file.write('\n\n')
            #fTime = time.gmtime(self.ftime) #-error
            #file.write('Date this omod was compiled: %s-%s-%s %s:%s:%s\n' % (fTime.tm_mon, fTime.tm_mday, fTime.tm_year, fTime.tm_hour, fTime.tm_min, fTime.tm_sec))
            file.write('Contains readme: %s\n' % ('yes' if readme else 'no'))
            file.write('Contains script: %s\n' % ('yes' if readme else 'no'))
            # Skip the reset that OBMM puts in

    def getOmodContents(self):
        """Return a list of the files and their uncompressed sizes, and the total uncompressed size of an archive"""
        # Get contents of archive
        filesizes = dict()
        totalSize = 0
        reFileSize = re.compile(ur'[0-9]{4}-[0-9]{2}-[0-9]{2}\s+[0-9]{2}:[0-9]{2}:[0-9]{2}.{6}\s+([0-9]+)\s+[0-9]+\s+(.+?)$',re.U)
        reFinalLine = re.compile(ur'\s+([0-9]+)\s+[0-9]+\s+[0-9]+\s+files.*',re.U)

        with self.omod_path.unicodeSafe() as tempOmod:
            cmd7z = [archives.exe7z, u'l', u'-r', u'-sccUTF-8', tempOmod.s]
            with subprocess.Popen(cmd7z, stdout=PIPE, stdin=PIPE, startupinfo=startupinfo).stdout as ins:
                for line in ins:
                    line = unicode(line,'utf8')
                    maFinalLine = reFinalLine.match(line)
                    if maFinalLine:
                        totalSize = int(maFinalLine.group(1))
                        break
                    maFileSize = reFileSize.match(line)
                    if maFileSize:
                        size = int(maFileSize.group(1))
                        name = maFileSize.group(2).strip().strip(u'\r')
                        filesizes[name] = size
        return filesizes,totalSize

    def extractToProject(self,outDir,progress=None):
        """Extract the contents of the omod to a project, with omod conversion data"""
        progress = progress if progress else bolt.Progress()
        extractDir = stageBaseDir = Path.tempDir()
        stageDir = stageBaseDir.join(outDir.tail)

        try:
            # Get contents of archive
            sizes,total = self.getOmodContents()

            # Extract the files
            reExtracting = re.compile(ur'Extracting\s+(.+)',re.U)
            progress(0, self.omod_path.stail + u'\n' + _(u'Extracting...'))

            subprogress = bolt.SubProgress(progress, 0, 0.4)
            current = 0
            with self.omod_path.unicodeSafe() as tempOmod:
                cmd7z = [archives.exe7z, u'e', u'-r', u'-sccUTF-8', tempOmod.s, u'-o%s' % extractDir.s]
                with subprocess.Popen(cmd7z, stdout=PIPE, stdin=PIPE, startupinfo=startupinfo).stdout as ins:
                    for line in ins:
                        line = unicode(line,'utf8')
                        maExtracting = reExtracting.match(line)
                        if maExtracting:
                            name = maExtracting.group(1).strip().strip(u'\r')
                            size = sizes[name]
                            subprogress(float(current) / total, self.omod_path.stail + u'\n' + _(u'Extracting...') + u'\n' + name)
                            current += size

            # Get compression type
            progress(0.4, self.omod_path.stail + u'\n' + _(u'Reading config'))
            self.readConfig(extractDir.join(u'config'))

            # Collect OMOD conversion data
            ocdDir = stageDir.join(u'omod conversion data')
            progress(0.46, self.omod_path.stail + u'\n' + _(u'Creating omod conversion data') + u'\ninfo.txt')
            self.writeInfo(ocdDir.join(u'info.txt'), self.omod_path.stail, extractDir.join(u'readme').exists(), extractDir.join(u'script').exists())
            progress(0.47, self.omod_path.stail + u'\n' + _(u'Creating omod conversion data') + u'\nscript')
            if extractDir.join(u'script').exists():
                with bolt.BinaryFile(extractDir.join(u'script').s) as input:
                    with ocdDir.join(u'script.txt').open('w') as output:
                        output.write(input.readNetString())
            progress(0.48, self.omod_path.stail + u'\n' + _(u'Creating omod conversion data') + u'\nreadme.rtf')
            if extractDir.join(u'readme').exists():
                with bolt.BinaryFile(extractDir.join(u'readme').s) as input:
                    with ocdDir.join(u'readme.rtf').open('w') as output:
                        output.write(input.readNetString())
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

            pluginSize = sizes.get('plugins',0)
            dataSize = sizes.get('data',0)
            subprogress = bolt.SubProgress(progress, 0.5, 1)
            with stageDir.unicodeSafe() as tempOut:
                if extractDir.join(u'plugins.crc').exists() and extractDir.join(u'plugins').exists():
                    pluginProgress = bolt.SubProgress(subprogress, 0, float(pluginSize)/(pluginSize+dataSize))
                    extract(extractDir.join(u'plugins.crc'),extractDir.join(u'plugins'),tempOut,pluginProgress)
                if extractDir.join(u'data.crc').exists() and extractDir.join(u'data').exists():
                    dataProgress = bolt.SubProgress(subprogress, subprogress.state, 1)
                    extract(extractDir.join(u'data.crc'),extractDir.join(u'data'),tempOut,dataProgress)
                progress(1, self.omod_path.stail + u'\n' + _(u'Extracted'))

            # Move files to final directory
            env.shellMove(stageDir, outDir.head, parent=None,
                          askOverwrite=True, allowUndo=True, autoRename=True)
        except Exception as e:
            # Error occurred, see if final output dir needs deleting
            env.shellDeletePass(outDir, parent=progress.getParent())
            raise
        finally:
            # Clean up temp directories
            extractDir.rmtree(safety=extractDir.stail)
            stageBaseDir.rmtree(safety=stageBaseDir.stail)

    def extractFilesZip(self, crcPath, dataPath, outPath, progress):
        fileNames, crcs, sizes = self.getFile_CrcSizes(crcPath)
        if len(fileNames) == 0: return

        # Extracted data stream is saved as a file named 'a'
        progress(0, self.omod_path.tail + u'\n' + _(u'Unpacking %s') % dataPath.stail)
        cmd = [archives.exe7z, u'e', u'-r', u'-sccUTF-8', dataPath.s, u'-o%s' % outPath.s]
        subprocess.call(cmd, startupinfo=startupinfo)

        # Split the uncompress stream into files
        progress(0.7, self.omod_path.stail + u'\n' + _(u'Unpacking %s') % dataPath.stail)
        self.splitStream(outPath.join(u'a'), outPath, fileNames, sizes,
                         bolt.SubProgress(progress,0.7,1.0,len(fileNames))
                         )
        progress(1)

        # Clean up
        outPath.join(u'a').remove()

    def splitStream(self, streamPath, outDir, fileNames, sizes, progress):
        # Split the uncompressed stream into files
        progress(0, self.omod_path.stail + u'\n' + _(u'Unpacking %s') % streamPath.stail)
        with streamPath.open('rb') as file:
            for i,name in enumerate(fileNames):
                progress(i, self.omod_path.stail + u'\n' + _(u'Unpacking %s') % streamPath.stail + u'\n' + name)
                outFile = outDir.join(name)
                with outFile.open('wb') as output:
                    output.write(file.read(sizes[i]))
        progress(len(fileNames))

    def extractFiles7z(self, crcPath, dataPath, outPath, progress):
        fileNames, crcs, sizes = self.getFile_CrcSizes(crcPath)
        if len(fileNames) == 0: return
        totalSize = sum(sizes)

        # Extract data stream to an uncompressed stream
        subprogress = bolt.SubProgress(progress,0,0.3,full=dataPath.size)
        subprogress(0, self.omod_path.stail + u'\n' + _(u'Unpacking %s') % dataPath.stail)
        with dataPath.open('rb') as file:
            done = 0
            with bolt.BinaryFile(outPath.join(dataPath.sbody+u'.tmp').s,'wb') as output:
                # Decoder properties
                output.write(file.read(5))
                done += 5
                subprogress(5)

                # Next 8 bytes are the size of the data stream
                for i in range(8):
                    out = totalSize >> (i*8)
                    output.writeByte(out & 0xFF)
                    done += 1
                    subprogress(done)

                # Now copy the data stream
                while file.tell() < dataPath.size:
                    output.write(file.read(512))
                    done += 512
                    subprogress(done)

        # Now decompress
        progress(0.3)
        cmd = [bass.dirs['compiled'].join(u'lzma').s,u'd',outPath.join(dataPath.sbody+u'.tmp').s, outPath.join(dataPath.sbody+u'.uncomp').s]
        subprocess.call(cmd,startupinfo=startupinfo)
        progress(0.8)

        # Split the uncompressed stream into files
        self.splitStream(outPath.join(dataPath.sbody+u'.uncomp'), outPath, fileNames, sizes,
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
        sizes = list()
        with bolt.BinaryFile(crc_file_path.s) as crc_file:
            while crc_file.tell() < crc_file_path.size:
                fileNames.append(crc_file.readNetString())
                crcs.append(crc_file.readInt32())
                sizes.append(crc_file.readInt64())
        return fileNames,crcs,sizes

class OmodConfig:
    """Tiny little omod config class."""
    def __init__(self,name):
        self.name = name.s
        self.vMajor = 0
        self.vMinor = 1
        self.vBuild = 0
        self.author = u''
        self.email = u''
        self.website = u''
        self.abstract = u''

    @staticmethod
    def getOmodConfig(name):
        """Get obmm config file for project."""
        config = OmodConfig(name)
        configPath = bass.dirs['installers'].join(name,u'omod conversion data',u'config')
        if configPath.exists():
            with bolt.StructFile(configPath.s,'rb') as ins:
                ins.read(1) #--Skip first four bytes
                # OBMM can support UTF-8, so try that first, then fail back to
                config.name = decode(ins.readNetString(),encoding='utf-8')
                config.vMajor, = ins.unpack('i',4)
                config.vMinor, = ins.unpack('i',4)
                for attr in ('author','email','website','abstract'):
                    setattr(config,attr,decode(ins.readNetString(),encoding='utf-8'))
                ins.read(8) #--Skip date-time
                ins.read(1) #--Skip zip-compression
                #config['vBuild'], = ins.unpack('I',4)
        return config

    @staticmethod
    def writeOmodConfig(name, config):
        """Write obmm config file for project."""
        configPath = bass.dirs['installers'].join(name,u'omod conversion data',u'config')
        configPath.head.makedirs()
        with bolt.StructFile(configPath.temp.s,'wb') as out:
            out.pack('B',4)
            out.writeNetString(config.name.encode('utf8'))
            out.pack('i',config.vMajor)
            out.pack('i',config.vMinor)
            for attr in ('author','email','website','abstract'):
                # OBMM reads it fine if in UTF-8, so we'll do that.
                out.writeNetString(getattr(config,attr).encode('utf-8'))
            out.write('\x74\x1a\x74\x67\xf2\x7a\xca\x88') #--Random date time
            out.pack('b',0) #--zip compression (will be ignored)
            out.write('\xFF\xFF\xFF\xFF')
        configPath.untemp()
