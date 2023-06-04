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
"""Tmp module, hence the underscore, to rip save classes out of bosh -
Oblivion only . We need this split into cosaves and proper saves module and
coded for rest of the games."""
# TODO: Oblivion only - we need to support rest of games - help needed
import array
from collections import Counter, defaultdict
from io import BytesIO
from itertools import repeat, starmap

from .save_headers import OblivionSaveHeader
from .. import bolt, bush
from ..bolt import Flags, SubProgress, deprint, dict_sort, encode, flag, \
    pack_byte, pack_int, pack_short, sig_to_str, struct_unpack, \
    structs_cache, unpack_int, unpack_many, unpack_short, unpack_str8
from ..brec import FormId, ModReader, MreRecord, RecordType, \
    ShortFidWriteContext, int_unpacker, unpack_header
from ..exception import ModError, StateError
from ..mod_files import LoadFactory, ModFile
from ..wbtemp import TempFile

#------------------------------------------------------------------------------
# Save I/O --------------------------------------------------------------------
#------------------------------------------------------------------------------

# Save Change Records ---------------------------------------------------------
class SreNPC(object):
    """NPC change record."""
    __slots__ = ('form', 'health', 'unused2', 'attributes', 'acbs', 'spells',
                 'factions', 'full', 'ai', 'skills', 'modifiers')

    class sre_flags(Flags):
        form: bool
        health: bool = flag(2)
        attributes: bool
        acbs: bool
        spells: bool
        factions: bool
        full: bool
        ai: bool
        skills: bool
        modifiers: bool = flag(28)

    class ACBS(object):
        __slots__ = ('flags', 'baseSpell', 'fatigue', 'barterGold',
                     'level_offset', 'calcMin', 'calcMax')

        def __init__(self, ins=None, *, __deflts=(0, 0, 0, 0, 1, 0, 0)):
            if ins is not None:
                __deflts = struct_unpack('=I3Hh2H', ins.read(16))
            for a, d in zip(self.__slots__, __deflts):
                setattr(self, a, d)
            self.flags = RecordType.sig_to_class[b'NPC_'].NpcFlags(self.flags)

        def __str__(self):
            return '\n'.join(
                f'  {a} {getattr(self, a)}' for a in self.__slots__)

    def __init__(self, sre_flags=0, data_=None):
        for att in self.__slots__:
            setattr(self, att, None)
        if data_: self._load_acbs(sre_flags, data_)

    def _load_acbs(self, sr_flags, data_):
        """Loads variables from data."""
        ins = BytesIO(data_)
        def _unpack(fmt, fmt_siz):
            return struct_unpack(fmt, ins.read(fmt_siz))
        sr_flags = SreNPC.sre_flags(sr_flags)
        if sr_flags.form:
            self.form = unpack_int(ins)
        if sr_flags.attributes:
            self.attributes = list(_unpack('8B', 8))
        if sr_flags.acbs:
            self.acbs = SreNPC.ACBS(ins)
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
        out = BytesIO()
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
            for fa in self.factions:
                _pack(u'=Ib', *fa)
        #--Spells
        if self.spells is not None:
            num = len(self.spells)
            pack_short(out, num)
            _pack(f'{num}I', *self.spells)
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

    def getTuple(self, version):
        """Returns record as a change record tuple."""
        return 35, self.getFlags(), version, self.getData()

    def dumpText(self,saveFile):
        """Returns informal string representation of data."""
        buff = []
        fids = saveFile.fids
        if self.form is not None:
            buff.append(f'Form:\n  {self.form:d}')
        if self.attributes is not None:
            buff.append('Attributes\n  strength %3d\n  intelligence %3d\n  '
                'willpower %3d\n  agility %3d\n  speed %3d\n  endurance '
                '%3d\n  personality %3d\n  luck %3d' % tuple(self.attributes))
        if self.acbs is not None:
            buff.append('ACBS:')
            buff.append(f'{self.acbs}')
        if self.factions is not None:
            buff.append('Factions:')
            for fa in self.factions:
                buff.append(f'  {fids[fa[0]]:8X} {fa[1]:2X}')
        if self.spells is not None:
            buff.append('Spells:')
            for spell in self.spells:
                buff.append(f'  {fids[spell]:8X}')
        if self.ai is not None:
            buff.append(_(u'AI') + f':\n  {self.ai}')
        if self.health is not None:
            buff.append(f'Health\n  {self.health}')
            buff.append(f'Unused2\n  {self.unused2}')
        if self.modifiers is not None:
            buff.append('Modifiers:')
            for modifier in self.modifiers:
                buff.append(f'  {modifier}')
        if self.full is not None:
            buff.append(f'Full:\n  {self.full}')
        if self.skills is not None:
            buff.append(
                u'Skills:\n  armorer %3d\n  athletics %3d\n  blade %3d\n '
                u' block %3d\n  blunt %3d\n  handToHand %3d\n  '
                u'heavyArmor %3d\n  alchemy %3d\n  alteration %3d\n  '
                u'conjuration %3d\n  destruction %3d\n  illusion %3d\n  '
                u'mysticism %3d\n  restoration %3d\n  acrobatics %3d\n  '
                u'lightArmor %3d\n  marksman %3d\n  mercantile %3d\n  '
                u'security %3d\n  sneak %3d\n  speechcraft  %3d' % tuple(
                    self.skills))
        buff.append('') # final newline
        return '\n'.join(buff)

# Save File -------------------------------------------------------------------
class SaveFile(object):
    """Represents a Tes4 Save file."""

    class recordFlags(Flags):
        form: bool
        baseid: bool
        moved: bool
        havokMoved: bool
        scale: bool
        allExtra: bool
        lock: bool
        owner: bool
        mapMarkerFlags: bool = flag(10)
        hadHavokMoveFlag: bool
        emptyFlag: bool = flag(16)
        droppedItem: bool
        doorDefaultSate: bool
        doorState: bool
        teleport: bool
        extraMagic: bool
        furnMarkers: bool
        oblivionFlag: bool
        movementExtra: bool
        animation: bool
        script: bool
        inventory: bool
        created: bool
        enabled: bool = flag(30)

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
        self.created = {}
        self.preGlobals = None #--Pre-records, pre-globals
        self.preCreated = None #--Pre-records, pre-created
        self.preRecords = None #--Pre-records, pre
        #--Records, temp effects, fids, worldspaces
        # rec_id: (rec_kind, flags, version, data)
        # rec_kind is an int, rec_id the short formid of the record in the save
        self.fid_recNum = {}
        self.tempEffects = None
        self.fids = None
        self.irefs = {}  #--iref = self.irefs[fid]
        self.worldSpaces = None

    def load(self,progress=None):
        """Extract info from save file."""
        # TODO: This is Oblivion only code.  Needs to be refactored
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
            self.globals = [unpack_many(ins, 'If') for _n in range(globalsNum)]
            #--Pre-Created (Class, processes, spectator, sky)
            buff = BytesIO()
            for x in range(4):
                siz = unpack_short(ins)
                insCopy(buff, siz, 2)
            #--Supposedly part of created info, but sticking it here since
            # I don't decode it.
            insCopy(buff, 4)
            self.preCreated = buff.getvalue()
            #--Created (ALCH,SPEL,ENCH,WEAP,CLOTH,ARMO, etc.?)
            createdNum = unpack_int(ins)
            with ModReader(self.fileInfo.fn_key, ins) as modReader:
                for count in range(createdNum):
                    progress(ins.tell(), _('Reading created...'))
                    record = MreRecord(unpack_header(modReader), modReader)
                    self.created[record.fid] = record
                #--Pre-records: Quickkeys, reticule, interface, regions
                buff = BytesIO()
                for x in range(4):
                    siz = unpack_short(ins)
                    insCopy(buff, siz, 2)
                self.preRecords = buff.getvalue()
                #--Records
                for count in range(recordsNum):
                    progress(ins.tell(), _('Reading records...'))
                    rec_id, *atts, siz = unpack_many(ins, '=IBIBH')
                    self.fid_recNum[rec_id] = (*atts, ins.read(siz))
                #--Temp Effects, fids, worldids
                progress(ins.tell(), _('Reading fids, worldids...'))
                tmp_effects_size = unpack_int(ins)
                self.tempEffects = ins.read(tmp_effects_size)
                #--Fids
                num = unpack_int(ins)
                self.fids = array.array('I')
                self.fids.fromfile(ins, num)
                for iref, int_fid in enumerate(self.fids):
                    self.irefs[int_fid] = iref
                #--WorldSpaces
                num = unpack_int(ins)
                self.worldSpaces = array.array('I')
                self.worldSpaces.fromfile(ins, num)
        #--Done
        progress(progress.full,_(u'Finished reading.'))

    def save(self,outPath=None,progress=None):
        """Save data to file.
        outPath -- Path of the output file to write to. Defaults to original file path."""
        if not self.canSave:
            raise StateError('Insufficient data to write file.')
        outPath = outPath or self.fileInfo.abs_path
        with ShortFidWriteContext(outPath) as out:
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
            _pack('I', len(self.fid_recNum))
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
            _pack('I', len(self.created))
            for record in self.created.values():
                record.dump(out)
            #--Pre-records
            out.write(self.preRecords)
            #--Records, temp effects, fids, worldspaces
            progress(0.2,_(u'Writing records.'))
            for rec_id, (*atts, rdata) in self.fid_recNum.items():
                _pack('=IBIBH', rec_id, *atts, len(rdata))
                out.write(rdata)
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
        with TempFile() as tmp_path:
            self.save(tmp_path, progress)
            filePath.replace_with_temp(tmp_path)
        self.fileInfo.setmtime()

    def addMaster(self, master):
        """Adds master to masters list."""
        if master not in self._masters:
            self._masters.append(master)

    def getFid(self, iref, iref_default=None):
        """Returns fid corresponding to iref."""
        if not iref: return iref_default
        if iref >> 24 == 0xFF: return iref
        if iref >= len(self.fids):
            raise ModError(self.fileInfo.fn_key, 'IRef from Mars.')
        return self.fids[iref]

    def getIref(self,fid):
        """Returns iref corresponding to fid, creating it if necessary."""
        iref = self.irefs.get(fid,-1)
        if iref < 0:
            self.fids.append(fid)
            iref = self.irefs[fid] = len(self.fids) - 1
        return iref

    #--------------------------------------------------------------------------
    def logStats(self,log=None, *, __unpacker=int_unpacker):
        """Print stats to log."""
        log = log or bolt.Log()
        doLostChanges = False
        doUnknownTypes = False
        def getMaster(modIndex):
            if modIndex < len(self._masters):
                return self._masters[modIndex]
            elif modIndex == 0xFF:
                return self.fileInfo.fn_key
            else:
                return _(u'Missing Master ')+hex(modIndex)
        #--ABomb
        (tesClassSize,abombCounter,abombFloat) = self.getAbomb()
        log.setHeader(_(u'Abomb Counter'))
        log(_(u'  Integer:\t0x%08X') % abombCounter)
        log(_(u'  Float:\t%.2f') % abombFloat)
        #--FBomb
        log.setHeader(_(u'Fbomb Counter'))
        log(_('  Next in-game object: %08X') % __unpacker(self.preGlobals[:4]))
        #--Array Sizes
        log.setHeader(u'Array Sizes')
        log(f'  {len(self.created)}\t{_("Created Items")}')
        log(f'  {len(self.fid_recNum)}\t{_("Records")}')
        log(f'  {len(self.fids)}\t{_("Fids")}')
        #--Created Types
        log.setHeader(_(u'Created Items'))
        created_sizes = defaultdict(int)
        created_counts = Counter()
        for citem in self.created.values():
            created_sizes[citem._rec_sig] += citem.header.blob_size
            created_counts[citem._rec_sig] += 1
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
        for rec_id, (rec_kind, rec_flgs, _version, rdata) in \
                self.fid_recNum.items():
            if rec_id ==0xFEFFFFFF: continue #--Ignore intentional(?) extra fid added by patch.
            mod = rec_id >> 24
            typeModHisto[rec_kind][mod] += 1
            changeHisto[mod] += 1
            #--Lost Change?
            if doLostChanges and mod == 255 and not (48 <= rec_kind <= 51) and rec_id not in self.created:
                lostChanges[rec_id] = rec_kind
            #--Unknown type?
            if doUnknownTypes and rec_kind not in knownTypes:
                if mod < 255:
                    print(rec_kind, hex(rec_id), f'{getMaster(mod)}')
                    knownTypes.add(rec_kind)
                elif rec_id in self.created:
                    print(rec_kind, hex(rec_id), self.created[rec_id]._rec_sig)
                    knownTypes.add(rec_kind)
            #--Obj ref parents
            if rec_kind == 49 and mod == 255 and (rec_flgs & 2):
                iref = __unpacker(rdata[4:8])[0]
                count,cumSize = objRefBases.get(iref,(0,0))
                count += 1
                cumSize += len(rdata) + 12
                objRefBases[iref] = (count,cumSize)
                if iref >> 24 != 255 and fids[iref] == 0:
                    objRefNullBases += 1
        rec_type_map = bush.game.save_rec_types
        #--Fids log
        log.setHeader(_(u'Fids'))
        log('  Refed\tChanged\tMI    Mod Name')
        log(f'  {lostRefs:d}\t\t     Lost Refs (Fid == 0)')
        for modIndex, (irefed, changes) in enumerate(zip(idHist, changeHisto)):
            if irefed or changes:
                log(f'  {irefed:d}\t{changes:d}\t{modIndex:02X}   '
                    f'{getMaster(modIndex)}')
        #--Lost Changes
        if lostChanges:
            log.setHeader(_(u'LostChanges'))
            for rec_id, rec_kind in dict_sort(lostChanges):
                log(hex(rec_id) + rec_type_map.get(rec_kind, f'{rec_kind}'))
        for rec_kind, modHisto in dict_sort(typeModHisto):
            log.setHeader(f'{rec_kind:d} '
                          f'{rec_type_map.get(rec_kind, _("Unknown"))}')
            for modIndex,count in dict_sort(modHisto):
                log(f'  {count:d}\t{getMaster(modIndex)}')
            log(f'  {sum(modHisto.values()):d}\tTotal')
        objRefBases = {k: v for k, v in objRefBases.items() if v[0] > 100}
        log.setHeader(_(u'New ObjectRef Bases'))
        if objRefNullBases:
            log(f' Null Bases: {objRefNullBases}')
        if objRefBases:
            log(_(u' Count IRef     BaseId'))
            for iref, (count, cumSize) in dict_sort(objRefBases):
                if iref >> 24 == 255:
                    parentid = iref
                else:
                    parentid = self.fids[iref]
                log(f'{count:6d} {iref:08X} {parentid:08X} '
                    f'{cumSize // 1024:6d} kb')

    def findBloating(self,progress=None):
        """Analyzes file for bloating. Returns (createdCounts,nullRefCount)."""
        nullRefCount = 0
        createdCounts = Counter()
        progress = progress or bolt.Progress()
        progress.setFull(len(self.created) + len(self.fid_recNum))
        #--Created objects
        progress(0,_(u'Scanning created objects'))
        for citem in self.created.values():
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
        for rec_id, (rec_kind, rec_flgs, _version, rdata) in \
                self.fid_recNum.items():
            if rec_kind == 49 and rec_id >> 24 == 0xFF and (rec_flgs & 2):
                iref, = struct_unpack(u'I', rdata[4:8])
                if iref >> 24 != 0xFF and fids[iref] == 0:
                    nullRefCount += 1
            progress.plus()
        return createdCounts,nullRefCount

    def removeBloating(self,uncreateKeys,removeNullRefs=True,progress=None):
        """Removes duplicated created items and null refs."""
        numUncreated = numUnCreChanged = numUnNulled = 0
        progress = progress or bolt.Progress()
        progress.setFull(
            (len(uncreateKeys) and len(self.created)) + len(self.fid_recNum))
        uncreated = set()
        #--Uncreate
        if uncreateKeys:
            progress(0,_(u'Scanning created objects'))
            kept = {}
            for rfid, citem in self.created.items():
                if u'full' in citem.__class__.__slots__:
                    full = citem.full
                else:
                    full = citem.getSubString(b'FULL')
                if full and (citem._rec_sig, full) in uncreateKeys:
                    uncreated.add(rfid)
                    numUncreated += 1
                else:
                    kept[rfid] = citem
                progress.plus()
            self.created = kept
        #--Change records
        progress(progress.state,_(u'Scanning change records.'))
        fids = self.fids
        kept = {}
        for rec_id, record in self.fid_recNum.items():
            rec_kind, rec_flgs, version, rdata = record
            if rec_id in uncreated:
                numUnCreChanged += 1
            elif removeNullRefs and rec_kind == 49 and rec_id >> 24 == 0xFF and (rec_flgs & 2):
                iref, = struct_unpack(u'I', rdata[4:8])
                if iref >> 24 != 0xFF and fids[iref] == 0:
                    numUnNulled += 1
                else:
                    kept[rec_id] = record
            else:
                kept[rec_id] = record
            progress.plus()
        self.fid_recNum = kept
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
        buff = BytesIO()
        buff.write(data)
        buff.seek(2 + tesClassSize - 4)
        pack_int(buff, value)
        self.preCreated = buff.getvalue()

    def get_npc(self, pc_fid=7):
        """Get NPC with specified fid - if no fid is passed get Player record.
        """
        try:
            rec_kind, recFlags, version, data = self.fid_recNum.get(pc_fid)
        except ValueError: # Unpacking None
            return None
        npc = SreNPC(recFlags, data)
        return npc, version

#------------------------------------------------------------------------------
class _SaveData:
    """Encapsulate common SaveFile manipulations."""
    def __init__(self, saveInfo):
        self.saveInfo = saveInfo
        self.saveFile = None

    def _load_save(self, progress=None):
        self.saveFile = SaveFile(self.saveInfo)
        self.saveFile.load(progress)

    def load_data(self, progress=None): raise NotImplementedError

class SaveSpells(_SaveData):
    """Player spells of a savegame."""

    def __init__(self, saveInfo):
        super().__init__(saveInfo)
        #--spells[(modName,objectIndex)] = (name,type)
        self.allSpells: dict[FormId, (str, int)] = {}

    def load_data(self, progress, modInfos):
        """Load savegame and extract created spells from it and its masters."""
        progress = progress or bolt.Progress()
        self._load_save(SubProgress(progress, 0, 0.4))
        progress = SubProgress(progress, 0.4, 1.0, len(self.saveFile._masters) + 1)
        #--Extract spells from masters
        for index,master in enumerate(self.saveFile._masters):
            progress(index, master)
            if master in modInfos:
                self.importMod(modInfos[master])
        #--Extract created spells
        allSpells = self.allSpells
        saveName = self.saveInfo.fn_key
        progress(progress.full - 1, saveName)
        for rfid, record in self.saveFile.created.items():
            if record._rec_sig == b'SPEL':
                save_fid = FormId.from_tuple((saveName, rfid.object_dex))
                allSpells[save_fid] = record.getTypeCopy()

    def importMod(self,modInfo):
        """Imports spell info from specified mod."""
        #--Spell list already extracted?
        if 'bash.spellList' in modInfo.extras:
            self.allSpells.update((FormId.from_tuple(k), v) for k, v in
                                  modInfo.extras['bash.spellList'].items())
            return
        #--Else extract spell list
        spell_lf = LoadFactory(False, by_sig=[b'SPEL'])
        modFile = ModFile(modInfo, spell_lf)
        try: modFile.load_plugin(catch_errors=False)
        except ModError as err:
            deprint(f'skipped mod due to read error ({err})')
            return
        spells = {rid: record for rid, record in
                  modFile.tops[b'SPEL'].iter_present_records()}
        modInfo.extras['bash.spellList'] = {k.long_fid: v for k, v in
                                            spells.items()}
        self.allSpells.update(spells)

    def getPlayerSpells(self): ##: could be refactored to use FormId machinery
        """Returns players spell list from savegame. (Returns ONLY spells. I.e., not abilities, etc.)"""
        saveFile = self.saveFile
        npc, _version = saveFile.get_npc()
        pcSpells = {} #--pcSpells[spellName] = iref
        #--NPC doesn't have any spells?
        if not npc.spells:
            return pcSpells
        #--Get masters and npc spell fids
        masters_copy = saveFile._masters[:]
        maxMasters = len(masters_copy) - 1
        #--Get spell names to match fids
        for iref in npc.spells:
            if (iref >> 24) == 255:
                fid = iref
            else:
                fid = saveFile.fids[iref]
            modIndex, objectIndex = fid >> 24, fid & 0x00FFFFFF
            if modIndex == 255:
                master = self.saveInfo.fn_key
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
        pc_fid = 7
        npc, version = self.saveFile.get_npc()
        if npc.spells and spellsToRemove:
            #--Remove spells and save
            npc.spells = [iref for iref in npc.spells if iref not in spellsToRemove]
            self.saveFile.fid_recNum[pc_fid] = npc.getTuple(version)
            self.saveFile.safeSave()

#------------------------------------------------------------------------------
class SaveEnchantments(_SaveData):
    """Player enchantments of a savegame."""

    def __init__(self, saveInfo):
        super().__init__(saveInfo)
        self.createdEnchantments = []

    def load_data(self, progress=None):
        """Loads savegame and and extracts created enchantments from it."""
        progress = progress or bolt.Progress()
        self._load_save(SubProgress(progress,0,0.4))
        #--Extract created enchantments
        progress(progress.full - 1, self.saveInfo.fn_key)
        for rfid, record in self.saveFile.created.items():
            if record._rec_sig == b'ENCH':
                record = record.getTypeCopy()
                record.getSize() #--Since type copy makes it changed.
                self.saveFile.created[rfid] = record
                self.createdEnchantments.append(record)

    def setCastWhenUsedEnchantmentNumberOfUses(self,uses):
        """Sets Cast When Used Enchantment number of uses (via editing the
        enchant cost)."""
        count = 0
        for record in self.createdEnchantments:
            if record.item_type in (1, 2):
                charge_over_uses = 0 if uses == 0 else max(
                    record.charge_amount // uses, 1)
                if record.enchantment_cost == charge_over_uses: continue
                record.enchantment_cost = charge_over_uses
                record.setChanged()
                record.getSize()
                count += 1
        self.saveFile.safeSave()

#------------------------------------------------------------------------------
class Save_NPCEdits(_SaveData):
    """General editing of NPCs/player in savegame."""

    def renamePlayer(self,newName):
        """rename the player in  a save file."""
        self.saveInfo.header.pcName = newName
        self._load_save()
        pc_fid = 7
        npc, version = self.saveFile.get_npc()
        npc.full = encode(newName)
        self.saveFile.header.pcName = newName
        self.saveFile.fid_recNum[pc_fid] = npc.getTuple(version)
        self.saveFile.safeSave()
