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
"""Script extender cosave files. They are composed of a header and script
extender plugin chunks which, in turn are composed of chunks. We need to
read them to log stats and write them to remap espm masters. We only handle
renaming of the masters of the xSE plugin chunk itself and of the Pluggy chunk.
"""

from ..bolt import sio, GPath, decode, encode, unpack_string, unpack_int, \
    unpack_short, unpack_4s, unpack_byte, unpack_str16, struct_pack, \
    struct_unpack
from ..exception import FileError

class CoSaveHeader(object):
    __slots__ = ('signature', 'formatVersion', 'obseVersion',
                 'obseMinorVersion', 'oblivionVersion', 'numPlugins')
    # numPlugins: the xSE plugins the cosave knows about - including xSE itself
    def __init__(self, ins, cosave_path, signature):
        self.signature = unpack_string(ins, len(signature))
        if self.signature != signature:
            raise FileError(cosave_path, u'Signature wrong: %r (expected %r)' %
                (self.signature, signature))
        self.formatVersion = unpack_int(ins)
        self.obseVersion = unpack_short(ins)
        self.obseMinorVersion = unpack_short(ins)
        self.oblivionVersion = unpack_int(ins)
        self.numPlugins = unpack_int(ins)

class _Chunk(object):
    __slots__ = ('chunkType', 'chunkVersion', 'chunkLength', 'chunkData')
    _esm_encoding = 'cp1252' # TODO ask!

    def __init__(self, ins):
        self.chunkType = unpack_4s(ins)
        self.chunkVersion = unpack_int(ins)
        self.chunkLength = unpack_int(ins) # the length of the chunk data block
        self.chunkData = ins.read(self.chunkLength)

    def log_chunk(self, log, ins, save_masters, espmMap):
        """
        :param save_masters: the espm masters of the save, used in xSE chunks
        :param espmMap: a dict populated in pluggy chunks
        :type log: bolt.Log
        """

    def chunk_map_master(self, master_renames_dict, plugin_chunk):
        """Rename the espm masters - for xSE and Pluggy chunks.

        :param master_renames_dict: mapping of old to new espm names
        :param plugin_chunk: the plugin_chunk this chunk belongs to
        """

class _SEChunk(_Chunk):
    _espm_chunk_type = {'SDOM'}

    def log_chunk(self, log, ins, save_masters, espmMap):
        chunkType = self.chunkType
        def _unpack(fmt, fmt_siz):
            return struct_unpack(fmt, ins.read(fmt_siz))
        if chunkType == 'RVTS':
            #--OBSE String
            modIndex, stringID, stringLength, = _unpack('=BIH', 7)
            stringData = decode(ins.read(stringLength))
            log(u'    ' + _(u'Mod :') + u'  %02X (%s)' % (
                modIndex, save_masters[modIndex].s))
            log(u'    ' + _(u'ID  :') + u'  %u' % stringID)
            log(u'    ' + _(u'Data:') + u'  %s' % stringData)
        elif chunkType == 'RVRA':
            #--OBSE Array
            modIndex, arrayID, keyType, isPacked, = _unpack('=BIBB', 7)
            if modIndex == 255:
                log(_(u'    Mod :  %02X (Save File)') % modIndex)
            else:
                log(_(u'    Mod :  %02X (%s)') % (
                    modIndex, save_masters[modIndex].s))
            log(_(u'    ID  :  %u') % arrayID)
            if keyType == 1: #Numeric
                if isPacked:
                    log(_(u'    Type:  Array'))
                else:
                    log(_(u'    Type:  Map'))
            elif keyType == 3:
                log(_(u'    Type:  StringMap'))
            else:
                log(_(u'    Type:  Unknown'))
            if self.chunkVersion >= 1:
                numRefs, = _unpack('=I', 4)
                if numRefs > 0:
                    log(u'    Refs:')
                    for x in range(numRefs):
                        refModID, = _unpack('=B', 1)
                        if refModID == 255:
                            log(_(u'      %02X (Save File)') % refModID)
                        else:
                            log(u'      %02X (%s)' % (
                                refModID, save_masters[refModID].s))
            numElements, = _unpack('=I', 4)
            log(_(u'    Size:  %u') % numElements)
            for i in range(numElements):
                if keyType == 1:
                    key, = _unpack('=d', 8)
                    keyStr = u'%f' % key
                elif keyType == 3:
                    keyLen, = _unpack('=H', 2)
                    key = ins.read(keyLen)
                    keyStr = decode(key)
                else:
                    keyStr = 'BAD'
                dataType, = _unpack('=B', 1)
                if dataType == 1:
                    data, = _unpack('=d', 8)
                    dataStr = u'%f' % data
                elif dataType == 2:
                    data, = _unpack('=I', 4)
                    dataStr = u'%08X' % data
                elif dataType == 3:
                    dataLen, = _unpack('=H', 2)
                    data = ins.read(dataLen)
                    dataStr = decode(data)
                elif dataType == 4:
                    data, = _unpack('=I', 4)
                    dataStr = u'%u' % data
                log(u'    [%s]:%s = %s' % (keyStr, (
                u'BAD', u'NUM', u'REF', u'STR', u'ARR')[dataType],
                                           dataStr))

    def chunk_map_master(self, master_renames_dict, plugin_chunk):
        if self.chunkType not in self._espm_chunk_type:
            return
        with sio(self.chunkData) as ins:
            num_of_masters = unpack_byte(ins) # this won't change
            with sio() as out:
                def _pack(fmt, *args): out.write(struct_pack(fmt, *args))
                _pack('B', num_of_masters)
                while ins.tell() < len(self.chunkData):
                    modName = GPath(unpack_str16(ins))
                    modName = master_renames_dict.get(modName, modName)
                    modname_str = encode(modName.s,
                                         firstEncoding=self._esm_encoding)
                    _pack('=H', len(modname_str))
                    out.write(modname_str)
                self.chunkData = out.getvalue()
        old_chunk_length = self.chunkLength
        self.chunkLength = len(self.chunkData)
        plugin_chunk.plugin_data_size += self.chunkLength - old_chunk_length # Todo Test

class _PluggyChunk(_Chunk):

    def log_chunk(self, log, ins, save_masters, espMap):
        chunkVersion = self.chunkVersion
        chunkBuff = self.chunkData
        chunkTypeNum, = struct_unpack('=I', self.chunkType)
        def _unpack(fmt, fmt_siz):
            return struct_unpack(fmt, ins.read(fmt_siz))
        if chunkTypeNum == 1:
            #--Pluggy TypeESP
            log(_(u'    Pluggy ESPs'))
            log(_(u'    EID   ID    Name'))
            while ins.tell() < len(chunkBuff):
                if chunkVersion == 2:
                    espId, modId, = _unpack('=BB', 2)
                    log(u'    %02X    %02X' % (espId, modId))
                    espMap[modId] = espId
                else:  #elif chunkVersion == 1"
                    espId, modId, modNameLen, = _unpack('=BBI', 6)
                    modName = ins.read(modNameLen)
                    log(u'    %02X    %02X    %s' % (espId, modId, modName))
                    espMap[modId] = modName  # was [espId]
        elif chunkTypeNum == 2:
            #--Pluggy TypeSTR
            log(_(u'    Pluggy String'))
            strId, modId, strFlags, = _unpack('=IBB', 6)
            strData = ins.read(len(chunkBuff) - ins.tell())
            log(u'      ' + _(u'StrID :') + u' %u' % strId)
            log(u'      ' + _(u'ModID :') + u' %02X %s' % (
                modId, espMap[modId] if modId in espMap else u'ERROR',))
            log(u'      ' + _(u'Flags :') + u' %u' % strFlags)
            log(u'      ' + _(u'Data  :') + u' %s' % strData)
        elif chunkTypeNum == 3:
            #--Pluggy TypeArray
            log(_(u'    Pluggy Array'))
            arrId, modId, arrFlags, arrSize, = _unpack('=IBBI', 10)
            log(_(u'      ArrID : %u') % (arrId,))
            log(_(u'      ModID : %02X %s') % (
                modId, espMap[modId] if modId in espMap else u'ERROR',))
            log(_(u'      Flags : %u') % (arrFlags,))
            log(_(u'      Size  : %u') % (arrSize,))
            while ins.tell() < len(chunkBuff):
                elemIdx, elemType, = _unpack('=IB', 5)
                elemStr = ins.read(4)
                if elemType == 0:  #--Integer
                    elem, = struct_unpack('=i', elemStr)
                    log(u'        [%u]  INT  %d' % (elemIdx, elem,))
                elif elemType == 1:  #--Ref
                    elem, = struct_unpack('=I', elemStr)
                    log(u'        [%u]  REF  %08X' % (elemIdx, elem,))
                elif elemType == 2:  #--Float
                    elem, = struct_unpack('=f', elemStr)
                    log(u'        [%u]  FLT  %08X' % (elemIdx, elem,))
        elif chunkTypeNum == 4:
            #--Pluggy TypeName
            log(_(u'    Pluggy Name'))
            refId, = _unpack('=I', 4)
            refName = ins.read(len(chunkBuff) - ins.tell())
            newName = u''
            for c in refName:
                ch = c if (c >= chr(0x20)) and (c < chr(0x80)) else '.'
                newName = newName + ch
            log(_(u'      RefID : %08X') % refId)
            log(_(u'      Name  : %s') % decode(newName))
        elif chunkTypeNum == 5:
            #--Pluggy TypeScr
            log(_(u'    Pluggy ScreenSize'))
            #UNTESTED - uncomment following line to skip this record type
            #continue
            scrW, scrH, = _unpack('=II', 8)
            log(_(u'      Width  : %u') % scrW)
            log(_(u'      Height : %u') % scrH)
        elif chunkTypeNum == 6:
            #--Pluggy TypeHudS
            log(u'    ' + _(u'Pluggy HudS'))
            #UNTESTED - uncomment following line to skip this record type
            #continue
            hudSid, modId, hudFlags, hudRootID, hudShow, hudPosX, hudPosY, \
            hudDepth, hudScaleX, hudScaleY, hudAlpha, hudAlignment, \
            hudAutoScale, = _unpack('=IBBBBffhffBBB', 29)
            hudFileName = decode(ins.read(len(chunkBuff) - ins.tell()))
            log(u'      ' + _(u'HudSID :') + u' %u' % hudSid)
            log(u'      ' + _(u'ModID  :') + u' %02X %s' % (
                modId, espMap[modId] if modId in espMap else u'ERROR',))
            log(u'      ' + _(u'Flags  :') + u' %02X' % hudFlags)
            log(u'      ' + _(u'RootID :') + u' %u' % hudRootID)
            log(u'      ' + _(u'Show   :') + u' %02X' % hudShow)
            log(u'      ' + _(u'Pos    :') + u' %f,%f' % (hudPosX, hudPosY,))
            log(u'      ' + _(u'Depth  :') + u' %u' % hudDepth)
            log(u'      ' + _(u'Scale  :') + u' %f,%f' % (
                hudScaleX, hudScaleY,))
            log(u'      ' + _(u'Alpha  :') + u' %02X' % hudAlpha)
            log(u'      ' + _(u'Align  :') + u' %02X' % hudAlignment)
            log(u'      ' + _(u'AutoSc :') + u' %02X' % hudAutoScale)
            log(u'      ' + _(u'File   :') + u' %s' % hudFileName)
        elif chunkTypeNum == 7:
            #--Pluggy TypeHudT
            log(_(u'    Pluggy HudT'))
            #UNTESTED - uncomment following line to skip this record type
            #continue
            hudTid, modId, hudFlags, hudShow, hudPosX, hudPosY, hudDepth, \
                = _unpack('=IBBBffh', 17)
            hudScaleX, hudScaleY, hudAlpha, hudAlignment, hudAutoScale, \
            hudWidth, hudHeight, hudFormat, = _unpack('=ffBBBIIB', 20)
            hudFontNameLen, = _unpack('=I', 4)
            hudFontName = decode(ins.read(hudFontNameLen))
            hudFontHeight, hudFontWidth, hudWeight, hudItalic, hudFontR, \
            hudFontG, hudFontB, = _unpack('=IIhBBBB', 14)
            hudText = decode(ins.read(len(chunkBuff) - ins.tell()))
            log(u'      ' + _(u'HudTID :') + u' %u' % hudTid)
            log(u'      ' + _(u'ModID  :') + u' %02X %s' % (
                modId, espMap[modId] if modId in espMap else u'ERROR',))
            log(u'      ' + _(u'Flags  :') + u' %02X' % hudFlags)
            log(u'      ' + _(u'Show   :') + u' %02X' % hudShow)
            log(u'      ' + _(u'Pos    :') + u' %f,%f' % (hudPosX, hudPosY,))
            log(u'      ' + _(u'Depth  :') + u' %u' % hudDepth)
            log(u'      ' + _(u'Scale  :') + u' %f,%f' % (
                hudScaleX, hudScaleY,))
            log(u'      ' + _(u'Alpha  :') + u' %02X' % hudAlpha)
            log(u'      ' + _(u'Align  :') + u' %02X' % hudAlignment)
            log(u'      ' + _(u'AutoSc :') + u' %02X' % hudAutoScale)
            log(u'      ' + _(u'Width  :') + u' %u' % hudWidth)
            log(u'      ' + _(u'Height :') + u' %u' % hudHeight)
            log(u'      ' + _(u'Format :') + u' %u' % hudFormat)
            log(u'      ' + _(u'FName  :') + u' %s' % hudFontName)
            log(u'      ' + _(u'FHght  :') + u' %u' % hudFontHeight)
            log(u'      ' + _(u'FWdth  :') + u' %u' % hudFontWidth)
            log(u'      ' + _(u'FWeigh :') + u' %u' % hudWeight)
            log(u'      ' + _(u'FItal  :') + u' %u' % hudItalic)
            log(u'      ' + _(u'FRGB   :') + u' %u,%u,%u' % (
                hudFontR, hudFontG, hudFontB,))
            log(u'      ' + _(u'FText  :') + u' %s' % hudText)

    def chunk_map_master(self, master_renames_dict, plugin_chunk):
        chunkTypeNum, = struct_unpack('=I', self.chunkType)
        if chunkTypeNum != 1:
            return # TODO confirm this is the espm chunk for Pluggy
        with sio(self.chunkData) as ins:
            with sio() as out:
                def _unpack(fmt, fmt_siz):
                    return struct_unpack(fmt, ins.read(fmt_siz))
                def _pack(fmt, *args):
                    out.write(struct_pack(fmt, *args))
                while ins.tell() < len(self.chunkData):
                    espId, modId, modNameLen, = _unpack('=BBI', 6)
                    modName = GPath(ins.read(modNameLen))
                    modName = master_renames_dict.get(modName, modName)
                    _pack('=BBI', espId, modId, len(modName.s))
                    out.write(encode(modName.cs, ##: why LowerCase ??
                                     firstEncoding=self._esm_encoding))
                self.chunkData = out.getvalue()
        old_chunk_length = self.chunkLength
        self.chunkLength = len(self.chunkData)
        plugin_chunk.plugin_data_size += self.chunkLength - old_chunk_length # Todo Test

class _PluginChunk(object):
    """Info on a xSE plugin in the save - composed of _Chunk units"""
    __slots__ = ('plugin_signature', 'num_plugin_chunks', 'plugin_data_size',
                 'plugin_chunks')

    def __init__(self, ins, xse_signature, pluggy_signature):
        self.plugin_signature = unpack_int(ins) # aka opcodeBase on pre papyrus
        self.num_plugin_chunks = unpack_int(ins)
        self.plugin_data_size = unpack_int(ins) # update it if you edit chunks
        self.plugin_chunks = []
        chunk_type = self._get_plugin_chunk_type(xse_signature,
                                                 pluggy_signature)
        for x in xrange(self.num_plugin_chunks):
            self.plugin_chunks.append(chunk_type(ins))

    def _get_plugin_chunk_type(self, xse_signature, pluggy_signature):
        if self.plugin_signature == xse_signature: return _SEChunk
        if self.plugin_signature == pluggy_signature: return _PluggyChunk
        return _Chunk

class ACoSaveFile(object):
    signature = 'OVERRIDE' # the cosave file signature, OBSE, SKSE etc
    _xse_signature = 0x1400 # signature (aka opcodeBase) of xSE plugin itself
    _pluggy_signature = None # signature (aka opcodeBase) of Pluggy plugin
    __slots__ = ('cosave_path', 'cosave_header', 'plugin_chunks')

    def __init__(self, cosave_path):
        # super(ACoSaveFile, self).__init__(cosave_path)
        self.cosave_path = cosave_path
        with open(u'%s' % cosave_path, 'rb') as ins:
            self.cosave_header = CoSaveHeader(ins, cosave_path, self.signature)
            self.plugin_chunks = []
            for x in xrange(self.cosave_header.numPlugins):
                self.plugin_chunks.append(_PluginChunk(
                    ins, self._xse_signature, self._pluggy_signature))

    def map_masters(self, master_renames_dict):
        for plugin_chunk in self.plugin_chunks:
            for chunk in plugin_chunk.plugin_chunks: # TODO avoid scanning all chunks
                chunk.chunk_map_master(master_renames_dict, plugin_chunk)

    def logStatObse(self, log, save_masters):
        """Print stats to log."""
        #--Header
        log.setHeader(_(u'Header'))
        log(u'=' * 80)
        log(_(u'  Format version:   %08X') % (self.cosave_header.formatVersion,))
        log(_(u'  OBSE version:     %u.%u') % (self.cosave_header.obseVersion,self.cosave_header.obseMinorVersion,))
        log(_(u'  Oblivion version: %08X') % (self.cosave_header.oblivionVersion,))
        #--Plugins
        for plugin_ch in self.plugin_chunks: # type: _PluginChunk
            plugin_sig = plugin_ch.plugin_signature
            log.setHeader(_(u'Plugin opcode=%08X chunkNum=%u') % (
                plugin_sig, plugin_ch.num_plugin_chunks,))
            log(u'=' * 80)
            log(_(u'  Type  Ver   Size'))
            log(u'-' * 80)
            espMap = {}
            for ch in plugin_ch.plugin_chunks: # type: _Chunk
                chunkTypeNum, = struct_unpack('=I',ch.chunkType)
                if ch.chunkType[0] >= ' ' and ch.chunkType[3] >= ' ': # HUH ?
                    log(u'  %4s  %-4u  %08X' % (
                        ch.chunkType, ch.chunkVersion, ch.chunkLength))
                else:
                    log(u'  %04X  %-4u  %08X' % (
                        chunkTypeNum, ch.chunkVersion, ch.chunkLength))
                with sio(ch.chunkData) as ins:
                    ch.log_chunk(log, ins, save_masters, espMap)

    def write_cosave(self, out_path):
        mtime = self.cosave_path.mtime # must exist !
        with sio() as buff:
            def _pack(fmt, *args): buff.write(struct_pack(fmt, *args))
            buff.write(self.__class__.signature)
            _pack('=I', self.cosave_header.formatVersion)
            _pack('=H', self.cosave_header.obseVersion)
            _pack('=H', self.cosave_header.obseMinorVersion)
            _pack('=I', self.cosave_header.oblivionVersion)
            #--Plugins
            _pack('=I', len(self.plugin_chunks))
            for plugin_ch in self.plugin_chunks: # type: _PluginChunk
                _pack('=I', plugin_ch.plugin_signature)
                _pack('=I', plugin_ch.num_plugin_chunks)
                _pack('=I', plugin_ch.plugin_data_size)
                for chunk in plugin_ch.plugin_chunks: # type: _Chunk
                    buff.write(chunk.chunkType)
                    _pack('=2I', chunk.chunkVersion, chunk.chunkLength)
                    buff.write(chunk.chunkData)
            text = buff.getvalue()
        with out_path.open('wb') as out:
            out.write(text)
        out_path.mtime = mtime

    def write_cosave_safe(self):
        """Write to a tmp file first so if that fails we won't delete the
        cosave."""
        self.write_cosave(self.cosave_path.temp)
        self.cosave_path.untemp()

class ObseCosave(ACoSaveFile):
    signature = 'OBSE'
    _pluggy_signature = 0x2330

class SkseCosave(ACoSaveFile):
    signature = 'SKSE'
    _xse_signature = 0x0

class F4seCosave(SkseCosave):
    signature = 'F4SE' # TODO eslS !!!

# Factory
def get_cosave_type(game_fsName):
    """:rtype: type"""
    if game_fsName == u'Oblivion':
        return ObseCosave
    elif game_fsName in {u'Skyrim', u'Skyrim Special Edition'}:
        return SkseCosave
    elif game_fsName == u'Fallout4':
        return F4seCosave
    return None
