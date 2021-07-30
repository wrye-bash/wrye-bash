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
"""Tmp module, hence the underscore, to rip save classes out of bosh -
Oblivion only . We need this split into cosaves and proper saves module and
coded for rest of the games."""
# TODO: Oblivion only - we need to support rest of games - help needed
import io
from collections import Counter, defaultdict
from itertools import starmap, repeat

from .save_headers import OblivionSaveHeader
from .. import bolt, bush
from ..bolt import Flags, deprint, encode, SubProgress, unpack_many, \
    unpack_int, unpack_short, struct_unpack, pack_int, pack_short, pack_byte, \
    structs_cache, unpack_str8, dict_sort, sig_to_str
from ..brec import ModReader, MreRecord, getObjectIndex, getFormIndices, \
    unpack_header
from ..exception import ModError, StateError
from ..mod_files import ModFile, LoadFactory

#------------------------------------------------------------------------------
# Save I/O --------------------------------------------------------------------
#------------------------------------------------------------------------------

# Save Change Records ---------------------------------------------------------
class SreNPC(object):
    """NPC change record."""
    __slots__ = (u'form', u'health', u'unused2', u'attributes', u'acbs',
                 u'spells', u'factions', u'full', u'ai', u'skills',
                 u'modifiers')
    sre_flags = Flags.from_names(
        (0,u'form'),
        (2,u'health'),
        (3,u'attributes'),
        (4,u'acbs'),
        (5,u'spells'),
        (6,u'factions'),
        (7,u'full'),
        (8,u'ai'),
        (9,u'skills'),
        (28,u'modifiers'),
    )

    class ACBS(object):
        __slots__ = (u'flags', u'baseSpell', u'fatigue', u'barterGold',
                     u'level_offset', u'calcMin', u'calcMax')

    def __init__(self, sre_flags=0, data_=None):
        for attr in self.__slots__:
            setattr(self, attr, None)
        if data_: self.load(sre_flags, data_)

    def getDefault(self,attr):
        """Returns a default version. Only supports acbs."""
        assert attr == u'acbs'
        acbs = SreNPC.ACBS()
        (acbs.flags, acbs.baseSpell, acbs.fatigue, acbs.barterGold,
         acbs.level_offset, acbs.calcMin, acbs.calcMax) = (0,0,0,0,1,0,0)
        acbs.flags = MreRecord.type_class[b'NPC_']._flags(acbs.flags)
        return acbs

    def load(self, sr_flags, data_):
        """Loads variables from data."""
        ins = io.BytesIO(data_)
        def _unpack(fmt, fmt_siz):
            return struct_unpack(fmt, ins.read(fmt_siz))
        sr_flags = SreNPC.sre_flags(sr_flags)
        if sr_flags.form:
            self.form = unpack_int(ins)
        if sr_flags.attributes:
            self.attributes = list(_unpack(u'8B', 8))
        if sr_flags.acbs:
            acbs = self.acbs = SreNPC.ACBS()
            (acbs.flags, acbs.baseSpell, acbs.fatigue, acbs.barterGold,
             acbs.level_offset, acbs.calcMin,
             acbs.calcMax) = _unpack(u'=I3Hh2H', 16)
            acbs.flags = MreRecord.type_class[b'NPC_']._flags(acbs.flags)
        if sr_flags.factions:
            num = unpack_short(ins)
            self.factions = list(starmap(_unpack, repeat((u'=Ib', 5), num)))
        if sr_flags.spells:
            num = unpack_short(ins)
            self.spells = list(_unpack(u'%dI' % num, 4 * num))
        if sr_flags.ai:
            self.ai = ins.read(4)
        if sr_flags.health:
            self.health, self.unused2 = _unpack(u'H2s', 4)
        if sr_flags.modifiers:
            num = unpack_short(ins)
            self.modifiers = list(starmap(_unpack, repeat((u'=Bf', 5), num)))
        if sr_flags.full:
            self.full = unpack_str8(ins)
        if sr_flags.skills:
            self.skills = list(_unpack(u'21B', 21))

    def getFlags(self):
        """Returns current flags set."""
        sr_flags = SreNPC.sre_flags()
        for attr in SreNPC.__slots__:
            if attr != u'unused2':
                setattr(sr_flags, attr, getattr(self, attr) is not None)
        return sr_flags.dump()

    def getData(self):
        """Returns self.data."""
        out = io.BytesIO()
        def _pack(fmt, *args):
            out.write(structs_cache[fmt].pack(*args))
        #--Form
        if self.form is not None:
            pack_int(out, self.form)
        #--Attributes
        if self.attributes is not None:
            _pack(u'8B', *self.attributes)
        #--Acbs
        if self.acbs is not None:
            acbs = self.acbs
            _pack(u'=I3Hh2H', acbs.flags.dump(), acbs.baseSpell, acbs.fatigue,
                  acbs.barterGold, acbs.level_offset, acbs.calcMin,
                  acbs.calcMax)
        #--Factions
        if self.factions is not None:
            pack_short(out, len(self.factions))
            for faction in self.factions:
                _pack(u'=Ib', *faction)
        #--Spells
        if self.spells is not None:
            num = len(self.spells)
            pack_short(out, num)
            _pack(u'%dI' % num, *self.spells)
        #--AI Data
        if self.ai is not None:
            out.write(self.ai)
        #--Health
        if self.health is not None:
            _pack(u'H2s', self.health, self.unused2)
        #--Modifiers
        if self.modifiers is not None:
            pack_short(out, len(self.modifiers))
            for modifier in self.modifiers:
                _pack(u'=Bf', *modifier)
        #--Full
        if self.full is not None:
            pack_byte(out, len(self.full))
            out.write(self.full)
        #--Skills
        if self.skills is not None:
            _pack(u'21B', *self.skills)
        #--Done
        return out.getvalue()

    def getTuple(self,rec_id,version):
        """Returns record as a change record tuple."""
        return rec_id,35,self.getFlags(),version,self.getData()

    def dumpText(self,saveFile):
        """Returns informal string representation of data."""
        buff = io.StringIO()
        fids = saveFile.fids
        if self.form is not None:
            buff.write(u'Form:\n  %d' % self.form)
        if self.attributes is not None:
            buff.write(
                u'Attributes\n  strength %3d\n  intelligence %3d\n  '
                u'willpower %3d\n  agility %3d\n  speed %3d\n  endurance '
                u'%3d\n  personality %3d\n  luck %3d\n' % tuple(
                    self.attributes))
        if self.acbs is not None:
            buff.write(u'ACBS:\n')
            for attr in SreNPC.ACBS.__slots__:
                buff.write(u'  %s %s\n' % (attr, getattr(self.acbs, attr)))
        if self.factions is not None:
            buff.write(u'Factions:\n')
            for faction in self.factions:
                buff.write(u'  %8X %2X\n' % (fids[faction[0]], faction[1]))
        if self.spells is not None:
            buff.write(u'Spells:\n')
            for spell in self.spells:
                buff.write(u'  %8X\n' % fids[spell])
        if self.ai is not None:
            buff.write(_(u'AI')+u':\n  ' + self.ai + u'\n')
        if self.health is not None:
            buff.write(u'Health\n  %s\n' % self.health)
            buff.write(u'Unused2\n  %s\n' % self.unused2)
        if self.modifiers is not None:
            buff.write(u'Modifiers:\n')
            for modifier in self.modifiers:
                buff.write(u'  %s\n' % modifier)
        if self.full is not None:
            buff.write(u'Full:\n  %s\n' % self.full)
        if self.skills is not None:
            buff.write(
                u'Skills:\n  armorer %3d\n  athletics %3d\n  blade %3d\n '
                u' block %3d\n  blunt %3d\n  handToHand %3d\n  '
                u'heavyArmor %3d\n  alchemy %3d\n  alteration %3d\n  '
                u'conjuration %3d\n  destruction %3d\n  illusion %3d\n  '
                u'mysticism %3d\n  restoration %3d\n  acrobatics %3d\n  '
                u'lightArmor %3d\n  marksman %3d\n  mercantile %3d\n  '
                u'security %3d\n  sneak %3d\n  speechcraft  %3d\n' % tuple(
                    self.skills))
        return buff.getvalue()

# Save File -------------------------------------------------------------------
class SaveFile(object):
    """Represents a Tes4 Save file."""
    recordFlags = Flags.from_names(u'form', u'baseid', u'moved',
        u'havocMoved', u'scale', u'allExtra', u'lock', u'owner', u'unk8',
        u'unk9', u'mapMarkerFlags', u'hadHavokMoveFlag', u'unk12', u'unk13',
        u'unk14', u'unk15', u'emptyFlag', u'droppedItem', u'doorDefaultState',
        u'doorState', u'teleport', u'extraMagic', u'furnMarkers',
        u'oblivionFlag', u'movementExtra', u'animation', u'script',
        u'inventory', u'created', u'unk29', u'enabled')

    def __init__(self,saveInfo=None,canSave=True):
        self.fileInfo = saveInfo
        self.canSave = canSave
        #--File Header, Save Game Header
        self.header = None # type: OblivionSaveHeader| None
        self.gameHeader = None
        #--Masters
        self._masters = []
        #--Global
        self.globals = []
        self.created = []
        self.fid_createdNum = None
        self.preGlobals = None #--Pre-records, pre-globals
        self.preCreated = None #--Pre-records, pre-created
        self.preRecords = None #--Pre-records, pre
        #--Records, temp effects, fids, worldspaces
        # (rec_id, rec_kind, flags, version, data)
        # rec_kind is an int, rec_id the short formid of the record in the save
        self.records = []
        self.fid_recNum = None
        self.tempEffects = None
        self.fids = None
        self.irefs = {}  #--iref = self.irefs[fid]
        self.worldSpaces = None

    def load(self,progress=None):
        """Extract info from save file."""
        # TODO: This is Oblivion only code.  Needs to be refactored
        import array
        with self.fileInfo.abs_path.open(u'rb') as ins:
            #--Progress
            progress = progress or bolt.Progress()
            progress.setFull(self.fileInfo.fsize)
            #--Header
            progress(0,_(u'Reading Header.'))
            self.header = OblivionSaveHeader(self.fileInfo.abs_path,
                                             load_image=True, ins=ins)
            self._masters = self.header.masters
            #--Pre-Records copy buffer
            def insCopy(buff, siz, backSize=0):
                if backSize: ins.seek(-backSize,1)
                buff.write(ins.read(siz + backSize))
            #--"Globals" block
            fidsPointer,recordsNum = unpack_many(ins, u'2I')
            #--Pre-globals
            self.preGlobals = ins.read(8*4)
            #--Globals
            globalsNum = unpack_short(ins)
            self.globals = [unpack_many(ins, u'If')
                            for _n in range(globalsNum)]
            #--Pre-Created (Class, processes, spectator, sky)
            buff = io.BytesIO()
            for x in range(4):
                siz = unpack_short(ins)
                insCopy(buff, siz, 2)
            #--Supposedly part of created info, but sticking it here since
            # I don't decode it.
            insCopy(buff, 4)
            self.preCreated = buff.getvalue()
            #--Created (ALCH,SPEL,ENCH,WEAP,CLOTH,ARMO, etc.?)
            modReader = ModReader(self.fileInfo.ci_key, ins)
            createdNum = unpack_int(ins)
            for count in range(createdNum):
                progress(ins.tell(),_(u'Reading created...'))
                self.created.append(MreRecord(unpack_header(modReader), modReader))
            #--Pre-records: Quickkeys, reticule, interface, regions
            buff = io.BytesIO()
            for x in range(4):
                siz = unpack_short(ins)
                insCopy(buff, siz, 2)
            self.preRecords = buff.getvalue()
            #--Records
            for count in range(recordsNum):
                progress(ins.tell(),_(u'Reading records...'))
                (rec_id, rec_kind, flags, version, siz) = unpack_many(ins,u'=IBIBH')
                data = ins.read(siz)
                self.records.append((rec_id,rec_kind,flags,version,data))
            #--Temp Effects, fids, worldids
            progress(ins.tell(),_(u'Reading fids, worldids...'))
            tmp_effects_size = unpack_int(ins)
            self.tempEffects = ins.read(tmp_effects_size)
            #--Fids
            num = unpack_int(ins)
            self.fids = array.array(u'I')
            self.fids.fromfile(ins, num)
            for iref,fid in enumerate(self.fids):
                self.irefs[fid] = iref
            #--WorldSpaces
            num = unpack_int(ins)
            self.worldSpaces = array.array(u'I')
            self.worldSpaces.fromfile(ins, num)
        #--Done
        progress(progress.full,_(u'Finished reading.'))

    def save(self,outPath=None,progress=None):
        """Save data to file.
        outPath -- Path of the output file to write to. Defaults to original file path."""
        if not self.canSave: raise StateError(u'Insufficient data to write file.')
        outPath = outPath or self.fileInfo.getPath()
        with outPath.open(u'wb') as out:
            def _pack(fmt, *args):
                out.write(structs_cache[fmt].pack(*args))
            #--Progress
            progress = progress or bolt.Progress()
            progress.setFull(self.fileInfo.fsize)
            #--Header
            progress(0,_(u'Writing Header.'))
            self.header.dump_header(out)
            #--Fids Pointer, num records
            fidsPointerPos = out.tell()
            _pack(u'I',0) #--Temp. Will write real value later.
            _pack(u'I',len(self.records))
            #--Pre-Globals
            out.write(self.preGlobals)
            #--Globals
            _pack(u'H',len(self.globals))
            for iref,value in self.globals:
                _pack(u'If',iref,value)
            #--Pre-Created
            out.write(self.preCreated)
            #--Created
            progress(0.1,_(u'Writing created.'))
            _pack(u'I',len(self.created))
            for record in self.created:
                record.dump(out)
            #--Pre-records
            out.write(self.preRecords)
            #--Records, temp effects, fids, worldspaces
            progress(0.2,_(u'Writing records.'))
            for rec_id,rec_kind,flags,version,data in self.records:
                _pack(u'=IBIBH',rec_id,rec_kind,flags,version,len(data))
                out.write(data)
            #--Temp Effects, fids, worldids
            _pack(u'I',len(self.tempEffects))
            out.write(self.tempEffects)
            #--Fids
            progress(0.9,_(u'Writing fids, worldids.'))
            fidsPos = out.tell()
            out.seek(fidsPointerPos)
            _pack(u'I',fidsPos)
            out.seek(fidsPos)
            _pack(u'I',len(self.fids))
            self.fids.tofile(out)
            #--Worldspaces
            _pack(u'I',len(self.worldSpaces))
            self.worldSpaces.tofile(out)
            #--Done
            progress(1.0,_(u'Writing complete.'))

    def safeSave(self,progress=None):
        """Save data to file safely."""
        self.fileInfo.makeBackup()
        filePath = self.fileInfo.getPath()
        self.save(filePath.temp,progress)
        filePath.untemp()
        self.fileInfo.setmtime()

    def addMaster(self, master):
        """Adds master to masters list."""
        if master not in self._masters:
            self._masters.append(master)

    def indexCreated(self):
        """Fills out self.fid_recNum."""
        self.fid_createdNum = {x.fid: i for i, x in enumerate(self.created)}

    def removeCreated(self,fid):
        """Removes created if it exists. Returns True if record existed, false if not."""
        if self.fid_createdNum is None: self.indexCreated()
        recNum = self.fid_createdNum.get(fid)
        if recNum is None:
            return False
        else:
            del self.created[recNum]
            del self.fid_createdNum[fid]
            return True

    def indexRecords(self):
        """Fills out self.fid_recNum."""
        self.fid_recNum = {r[0]: i for i, r in enumerate(self.records)}

    def getRecord(self, rec_fid):
        """Returns recNum and record with corresponding fid."""
        if self.fid_recNum is None: self.indexRecords()
        recNum = self.fid_recNum.get(rec_fid)
        if recNum is None:
            return None
        return self.records[recNum]

    def setRecord(self,record):
        """Sets records where record = (rec_id,rec_kind,flags,version,data)."""
        if self.fid_recNum is None: self.indexRecords()
        rec_id = record[0]
        recNum = self.fid_recNum.get(rec_id,-1)
        if recNum == -1:
            self.records.append(record)
            self.fid_recNum[rec_id] = len(self.records)-1
        else:
            self.records[recNum] = record

    def removeRecord(self,fid):
        """Removes record if it exists. Returns True if record existed, false if not."""
        if self.fid_recNum is None: self.indexRecords()
        recNum = self.fid_recNum.get(fid)
        if recNum is None:
            return False
        else:
            del self.records[recNum]
            del self.fid_recNum[fid]
            return True

    def getFid(self,iref,default=None):
        """Returns fid corresponding to iref."""
        if not iref: return default
        if iref >> 24 == 0xFF: return iref
        if iref >= len(self.fids): raise ModError(self.fileInfo.ci_key,
                                                  u'IRef from Mars.')
        return self.fids[iref]

    def getIref(self,fid):
        """Returns iref corresponding to fid, creating it if necessary."""
        iref = self.irefs.get(fid,-1)
        if iref < 0:
            self.fids.append(fid)
            iref = self.irefs[fid] = len(self.fids) - 1
        return iref

    #--------------------------------------------------------------------------
    def logStats(self,log=None):
        """Print stats to log."""
        log = log or bolt.Log()
        doLostChanges = False
        doUnknownTypes = False
        def getMaster(modIndex):
            if modIndex < len(self._masters):
                return self._masters[modIndex]
            elif modIndex == 0xFF:
                return self.fileInfo.name
            else:
                return _(u'Missing Master ')+hex(modIndex)
        #--ABomb
        (tesClassSize,abombCounter,abombFloat) = self.getAbomb()
        log.setHeader(_(u'Abomb Counter'))
        log(_(u'  Integer:\t0x%08X') % abombCounter)
        log(_(u'  Float:\t%.2f') % abombFloat)
        #--FBomb
        log.setHeader(_(u'Fbomb Counter'))
        log(_(u'  Next in-game object: %08X') % struct_unpack(u'I', self.preGlobals[:4]))
        #--Array Sizes
        log.setHeader(u'Array Sizes')
        log(u'  %d\t%s' % (len(self.created),_(u'Created Items')))
        log(u'  %d\t%s' % (len(self.records),_(u'Records')))
        log(u'  %d\t%s' % (len(self.fids),_(u'Fids')))
        #--Created Types
        log.setHeader(_(u'Created Items'))
        created_sizes = defaultdict(int)
        created_counts = Counter()
        id_created = {}
        for citem in self.created:
            created_sizes[citem._rec_sig] += citem.size
            created_counts[citem._rec_sig] += 1
            id_created[citem.fid] = citem
        for rsig, csize in dict_sort(created_sizes):
            log(f'  {created_counts[rsig]}\t{csize // 1024} kb\t'
                f'{sig_to_str(rsig)}')
        #--Fids
        lostRefs = 0
        idHist = [0]*256
        for rec_id in self.fids:
            if rec_id == 0:
                lostRefs += 1
            else:
                idHist[rec_id >> 24] += 1
        #--Change Records
        changeHisto = [0]*256
        typeModHisto = defaultdict(Counter)
        knownTypes = set(bush.game.save_rec_types)
        lostChanges = {}
        objRefBases = {}
        objRefNullBases = 0
        fids = self.fids
        for record in self.records:
            rec_id,rec_kind,rec_flgs,version,data = record
            if rec_id ==0xFEFFFFFF: continue #--Ignore intentional(?) extra fid added by patch.
            mod = rec_id >> 24
            typeModHisto[rec_kind][mod] += 1
            changeHisto[mod] += 1
            #--Lost Change?
            if doLostChanges and mod == 255 and not (48 <= rec_kind <= 51) and rec_id not in id_created:
                lostChanges[rec_id] = rec_kind
            #--Unknown type?
            if doUnknownTypes and rec_kind not in knownTypes:
                if mod < 255:
                    print(rec_kind,hex(rec_id), u'%s' % getMaster(mod))
                    knownTypes.add(rec_kind)
                elif rec_id in id_created:
                    print(rec_kind, hex(rec_id), id_created[rec_id]._rec_sig)
                    knownTypes.add(rec_kind)
            #--Obj ref parents
            if rec_kind == 49 and mod == 255 and (rec_flgs & 2):
                iref, = struct_unpack(u'I', data[4:8])
                count,cumSize = objRefBases.get(iref,(0,0))
                count += 1
                cumSize += len(data) + 12
                objRefBases[iref] = (count,cumSize)
                if iref >> 24 != 255 and fids[iref] == 0:
                    objRefNullBases += 1
        rec_type_map = bush.game.save_rec_types
        #--Fids log
        log.setHeader(_(u'Fids'))
        log(u'  Refed\tChanged\tMI    Mod Name')
        log(u'  %d\t\t     Lost Refs (Fid == 0)' % lostRefs)
        for modIndex, (irefed,changed) in enumerate(zip(idHist, changeHisto)):
            if irefed or changed:
                log(u'  %d\t%d\t%02X   %s' % (irefed,changed,modIndex,getMaster(modIndex)))
        #--Lost Changes
        if lostChanges:
            log.setHeader(_(u'LostChanges'))
            for rec_id, rec_kind in dict_sort(lostChanges):
                log(hex(rec_id) + rec_type_map.get(rec_kind, u'%s' % rec_kind))
        for rec_kind, modHisto in dict_sort(typeModHisto):
            log.setHeader(u'%d %s' % (
                rec_kind, rec_type_map.get(rec_kind, _(u'Unknown'))))
            for modIndex,count in dict_sort(modHisto):
                log(u'  %d\t%s' % (count,getMaster(modIndex)))
            log(u'  %d\tTotal' % sum(modHisto.values()))
        objRefBases = {k: v for k, v in objRefBases.items() if v[0] > 100}
        log.setHeader(_(u'New ObjectRef Bases'))
        if objRefNullBases:
            log(u' Null Bases: %s' % objRefNullBases)
        if objRefBases:
            log(_(u' Count IRef     BaseId'))
            for iref, (count, cumSize) in dict_sort(objRefBases):
                if iref >> 24 == 255:
                    parentid = iref
                else:
                    parentid = self.fids[iref]
                log(u'%6d %08X %08X %6d kb' % (count,iref,parentid,cumSize//1024))

    def findBloating(self,progress=None):
        """Analyzes file for bloating. Returns (createdCounts,nullRefCount)."""
        nullRefCount = 0
        createdCounts = Counter()
        progress = progress or bolt.Progress()
        progress.setFull(len(self.created)+len(self.records))
        #--Created objects
        progress(0,_(u'Scanning created objects'))
        for citem in self.created:
            if u'full' in citem.__class__.__slots__:
                full = citem.full
            else:
                full = citem.getSubString(b'FULL')
            if full:
                createdCounts[(citem._rec_sig, full)] += 1
            progress.plus()
        for k in list(createdCounts):
            minCount = (50,100)[k[0] == b'ALCH']
            if createdCounts[k] < minCount:
                del createdCounts[k]
        #--Change records
        progress(len(self.created),_(u'Scanning change records.'))
        fids = self.fids
        for record in self.records:
            rec_id,rec_kind,rec_flgs,version,data = record
            if rec_kind == 49 and rec_id >> 24 == 0xFF and (rec_flgs & 2):
                iref, = struct_unpack(u'I', data[4:8])
                if iref >> 24 != 0xFF and fids[iref] == 0:
                    nullRefCount += 1
            progress.plus()
        return createdCounts,nullRefCount

    def removeBloating(self,uncreateKeys,removeNullRefs=True,progress=None):
        """Removes duplicated created items and null refs."""
        numUncreated = numUnCreChanged = numUnNulled = 0
        progress = progress or bolt.Progress()
        progress.setFull((len(uncreateKeys) and len(self.created))+len(self.records))
        uncreated = set()
        #--Uncreate
        if uncreateKeys:
            progress(0,_(u'Scanning created objects'))
            kept = []
            for citem in self.created:
                if u'full' in citem.__class__.__slots__:
                    full = citem.full
                else:
                    full = citem.getSubString(b'FULL')
                if full and (citem._rec_sig, full) in uncreateKeys:
                    uncreated.add(citem.fid)
                    numUncreated += 1
                else:
                    kept.append(citem)
                progress.plus()
            self.created = kept
        #--Change records
        progress(progress.state,_(u'Scanning change records.'))
        fids = self.fids
        kept = []
        for record in self.records:
            rec_id,rec_kind,rec_flgs,version,data = record
            if rec_id in uncreated:
                numUnCreChanged += 1
            elif removeNullRefs and rec_kind == 49 and rec_id >> 24 == 0xFF and (rec_flgs & 2):
                iref, = struct_unpack(u'I', data[4:8])
                if iref >> 24 != 0xFF and fids[iref] == 0:
                    numUnNulled += 1
                else:
                    kept.append(record)
            else:
                kept.append(record)
            progress.plus()
        self.records = kept
        return numUncreated,numUnCreChanged,numUnNulled

    def getAbomb(self):
        """Gets animation slowing counter(?) value."""
        data = self.preCreated
        tesClassSize, = struct_unpack(u'H', data[:2])
        abombBytes = data[2+tesClassSize-4:2+tesClassSize]
        abombCounter, = struct_unpack(u'I', abombBytes)
        abombFloat, = struct_unpack(u'f', abombBytes)
        return tesClassSize,abombCounter,abombFloat

    def setAbomb(self,value=0x41000000):
        """Resets abomb counter to specified value."""
        data = self.preCreated
        tesClassSize, = struct_unpack(u'H', data[:2])
        if tesClassSize < 4: return
        buff = io.BytesIO()
        buff.write(data)
        buff.seek(2 + tesClassSize - 4)
        pack_int(buff, value)
        self.preCreated = buff.getvalue()

#------------------------------------------------------------------------------
class SaveSpells(object):
    """Player spells of a savegame."""

    def __init__(self,saveInfo):
        self.saveInfo = saveInfo
        self.saveFile = None
        self.allSpells = {} #--spells[(modName,objectIndex)] = (name,type)

    def load(self, modInfos, progress=None):
        """Load savegame and extract created spells from it and its masters."""
        progress = progress or bolt.Progress()
        saveFile = self.saveFile = SaveFile(self.saveInfo)
        saveFile.load(SubProgress(progress,0,0.4))
        progress = SubProgress(progress, 0.4, 1.0, len(saveFile._masters) + 1)
        #--Extract spells from masters
        for index,master in enumerate(saveFile._masters):
            progress(index,master.s)
            if master in modInfos:
                self.importMod(modInfos[master])
        #--Extract created spells
        allSpells = self.allSpells
        saveName = self.saveInfo.ci_key
        progress(progress.full-1,saveName.s)
        for record in saveFile.created:
            if record._rec_sig == b'SPEL':
                allSpells[(saveName,getObjectIndex(record.fid))] = record.getTypeCopy()

    def importMod(self,modInfo):
        """Imports spell info from specified mod."""
        #--Spell list already extracted?
        if u'bash.spellList' in modInfo.extras:
            self.allSpells.update(modInfo.extras[u'bash.spellList'])
            return
        #--Else extract spell list
        loadFactory = LoadFactory(False, by_sig=[b'SPEL'])
        modFile = ModFile(modInfo, loadFactory)
        try: modFile.load(True)
        except ModError as err:
            deprint(u'skipped mod due to read error (%s)' % err)
            return
        spells = modInfo.extras[u'bash.spellList'] = {
            record.fid: record for record in modFile.tops[b'SPEL'].getActiveRecords()}
        self.allSpells.update(spells)

    def getPlayerSpells(self):
        """Returns players spell list from savegame. (Returns ONLY spells. I.e., not abilities, etc.)"""
        saveFile = self.saveFile
        #--Get masters and npc spell fids
        masters_copy = saveFile._masters[:]
        maxMasters = len(masters_copy) - 1
        (rec_id,rec_kind,recFlags,version,data) = saveFile.getRecord(7)
        npc = SreNPC(recFlags,data)
        pcSpells = {} #--pcSpells[spellName] = iref
        #--NPC doesn't have any spells?
        if not npc.spells:
            return pcSpells
        #--Get spell names to match fids
        for iref in npc.spells:
            if (iref >> 24) == 255:
                fid = iref
            else:
                fid = saveFile.fids[iref]
            modIndex,objectIndex = getFormIndices(fid)
            if modIndex == 255:
                master = self.saveInfo.ci_key
            elif modIndex <= maxMasters:
                master = masters_copy[modIndex]
            else: #--Bad fid?
                continue
            #--Get spell data
            record = self.allSpells.get((master,objectIndex),None)
            if record and record.full and record.spellType == 0 and fid != 0x136:
                pcSpells[record.full] = (iref,record)
        return pcSpells

    def removePlayerSpells(self,spellsToRemove):
        """Removes specified spells from players spell list."""
        (rec_id,rec_kind,recFlags,version,data) = self.saveFile.getRecord(7)
        npc = SreNPC(recFlags,data)
        if npc.spells and spellsToRemove:
            #--Remove spells and save
            npc.spells = [iref for iref in npc.spells if iref not in spellsToRemove]
            self.saveFile.setRecord(npc.getTuple(rec_id,version))
            self.saveFile.safeSave()

#------------------------------------------------------------------------------
class SaveEnchantments(object):
    """Player enchantments of a savegame."""

    def __init__(self,saveInfo):
        self.saveInfo = saveInfo
        self.saveFile = None
        self.createdEnchantments = []

    def load(self,progress=None):
        """Loads savegame and and extracts created enchantments from it."""
        progress = progress or bolt.Progress()
        saveFile = self.saveFile = SaveFile(self.saveInfo)
        saveFile.load(SubProgress(progress,0,0.4))
        #--Extract created enchantments
        saveName = self.saveInfo.ci_key
        progress(progress.full-1,saveName.s)
        for index,record in enumerate(saveFile.created):
            if record._rec_sig == b'ENCH':
                record = record.getTypeCopy()
                record.getSize() #--Since type copy makes it changed.
                saveFile.created[index] = record
                self.createdEnchantments.append((index,record))

    def setCastWhenUsedEnchantmentNumberOfUses(self,uses):
        """Sets Cast When Used Enchantment number of uses (via editing the enchat cost)."""
        count = 0
        for (index, record) in self.createdEnchantments:
            if record.itemType in [1,2]:
                if uses == 0:
                    if record.enchantCost == 0: continue
                    record.enchantCost = 0
                else:
                    if record.enchantCost == max(record.chargeAmount//uses,1): continue
                    record.enchantCost = max(record.chargeAmount//uses,1)
                record.setChanged()
                record.getSize()
                count += 1
        self.saveFile.safeSave()

#------------------------------------------------------------------------------
class Save_NPCEdits(object):
    """General editing of NPCs/player in savegame."""

    def __init__(self,saveInfo):
        self.saveInfo = saveInfo
        self.saveFile = SaveFile(saveInfo)

    def renamePlayer(self,newName):
        """rename the player in  a save file."""
        self.saveInfo.header.pcName = newName
        saveFile = self.saveFile
        saveFile.load()
        (rec_id,rec_kind,recFlags,version,data) = saveFile.getRecord(7)
        npc = SreNPC(recFlags,data)
        npc.full = encode(newName)
        saveFile.header.pcName = newName
        saveFile.setRecord(npc.getTuple(rec_id,version))
        saveFile.safeSave()
