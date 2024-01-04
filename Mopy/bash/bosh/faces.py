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
import re

from . import SaveInfo
from ._saves import SaveFile, SreNPC
from .. import bush
from ..bolt import Flags, Path, encode, pack_byte, pack_int, struct_pack, \
    struct_unpack, structs_cache
from ..brec import FormId, int_unpacker, null2, RecordType
from ..exception import SaveFileError, StateError
from ..mod_files import LoadFactory, MasterMap, ModFile

##: Last use of from_object_id, can we get rid of it?
_player_fid = FormId.from_object_id(0, 0x7)

class PCFaces(object):
    """Package: Objects and functions for working with face data."""
    class pcf_flags(Flags):
        pcf_name: bool
        pcf_race: bool
        pcf_gender: bool
        pcf_hair: bool
        pcf_eye: bool
        pcf_class: bool
        pcf_stats: bool
        pcf_factions: bool
        pcf_modifiers: bool
        pcf_spells: bool

    class PCFace(object):
        """Represents a face."""
        __slots__ = (
            'face_masters', 'eid', 'pcName', 'race', 'gender', 'eye',
            'hair', 'hairLength', 'hairRed', 'hairBlue', 'hairGreen',
            'unused3', 'fggs_p', 'fgga_p', 'fgts_p', 'level_offset',
            'attributes', 'skills', 'health', 'unused2', 'base_spell',
            'fatigue', 'npc_class', 'factions', 'modifiers', 'spells')

        def __init__(self):
            self.face_masters = []
            self.eid = self.pcName = 'generic'
            self.fggs_p = self.fgts_p = b'\x00'*4*50
            self.fgga_p = b'\x00'*4*30
            self.unused2 = null2
            self.health = self.unused3 = self.base_spell = self.fatigue = 0
            self.level_offset = 0
            self.skills = self.attributes = self.npc_class = None
            self.factions = []
            self.modifiers = []
            self.spells = []

        def getGenderName(self):
            return _('Female') if self.gender else _('Male')

        def getRaceName(self):
            return bush.game.raceNames.get(self.race, _('Unknown'))

        def convertRace(self,fromRace,toRace):
            """Converts face from one race to another while preserving
            structure, etc."""
            for a, f in (('fggs_p', '50f'), ('fgga_p', '30f'),
                         ('fgts_p', '50f')):
                sValues = list(struct_unpack(f, getattr(self, a)))
                fValues = list(struct_unpack(f, getattr(fromRace, a)))
                tValues = list(struct_unpack(f, getattr(toRace, a)))
                for index, (sValue, fValue, tValue) in list(enumerate(zip(
                        sValues, fValues, tValues))):
                    sValues[index] = sValue + fValue - tValue
                setattr(self, a, struct_pack(f, *sValues))

    # SAVES -------------------------------------------------------------------
    @staticmethod
    def save_getNamePos(saveName,data,pcName):
        """Safely finds position of name within save ACHR data."""
        namePos = data.find(pcName)
        if namePos == -1:
            raise SaveFileError(saveName,
                                'Failed to find pcName in PC ACHR record.')
        namePos2 = data.find(pcName,namePos+1)
        if namePos2 != -1:
            raise SaveFileError(saveName,
                'Uncertain about position of face data, probably because '
                'player character name is too short. Try renaming player '
                'character in save game.')
        return namePos

    # Save Get ----------------------------------------------------------------
    @staticmethod
    def save_getFaces(saveFile):
        """Returns player and created faces from a save file or saveInfo."""
        faces = PCFaces._save_getCreatedFaces(saveFile)
        playerFace = PCFaces.save_getPlayerFace(saveFile)
        faces[_player_fid] = playerFace
        return faces

    @staticmethod
    def _save_getCreatedFaces(saveFile):
        """Returns created faces from savefile. If fid is supplied, will only
        return created face with that fid.
        Note: Created NPCs do NOT use irefs!"""
        faces = {}
        for rfid, record in saveFile.created.items():
            if record._rec_sig != b'NPC_': continue
            #--Created NPC record
            npc = record.getTypeCopy()
            face = faces[npc.fid] = PCFaces.PCFace()
            face.face_masters = saveFile._masters
            for a in ('eid', 'race', 'eye', 'hair', 'hairLength', 'hairRed',
                      'hairBlue', 'hairGreen', 'unused3', 'fggs_p', 'fgga_p',
                      'fgts_p', 'level_offset', 'skills', 'health', 'unused2',
                      'base_spell', 'fatigue', 'attributes', 'npc_class'):
                setattr(face, a, getattr(npc, a))
            face.gender = (0,1)[npc.npc_flags.npc_female]
            face.pcName = npc.full
            #--Changed NPC Record
            PCFaces.save_getChangedNpc(saveFile, rfid, face)
        return faces

    @staticmethod
    def save_getChangedNpc(saveFile, npc_fid, face=None):
        """Update face with data from npc change record."""
        face = face or PCFaces.PCFace()
        changeRecord = saveFile.get_npc(npc_fid)
        if changeRecord is None:
            return face
        npc, _version = changeRecord
        if npc.acbs:
            face.gender = npc.acbs.npc_flags.npc_female
            face.level_offset = npc.acbs.level_offset
            face.base_spell = npc.acbs.base_spell
            face.fatigue = npc.acbs.fatigue
        for att in ('attributes', 'skills', 'health', 'unused2'):
            npc_val = getattr(npc, att)
            if npc_val is not None:
                setattr(face, att, npc_val)
        #--Iref >> fid
        getFid = saveFile.getFid
        face.spells = [getFid(x) for x in (npc.spells or [])]
        face.factions = [(getFid(x),y) for x,y in (npc.factions or [])]
        face.modifiers = (npc.modifiers or [])[:]
        return face

    @staticmethod
    def save_getPlayerFace(saveFile, *, __unpacker=int_unpacker,
            __faceunpack=structs_cache['=200s120s200s3If3BsB'].unpack):
        """Extract player face from save file."""
        if isinstance(saveFile,SaveInfo):
            saveInfo = saveFile
            saveFile = SaveFile(saveInfo)
            saveFile.load()
        face = PCFaces.PCFace()
        face.pcName = saveFile.header.pcName
        face.face_masters = saveFile._masters
        #--Player ACHR
        record = saveFile.fid_recNum.get(0x14)
        data = record[-1]
        namePos = PCFaces.save_getNamePos(saveFile.fileInfo.fn_key, data,
                                          encode(saveFile.header.pcName))
        (face.fggs_p, face.fgga_p, face.fgts_p, face.race, face.hair,
         face.eye, face.hairLength, face.hairRed, face.hairBlue,
         face.hairGreen, face.unused3, face.gender) = __faceunpack(
            data[namePos - 542:namePos - 1])
        classPos = namePos + len(saveFile.header.pcName) + 1
        face.npc_class, = __unpacker(data[classPos:classPos+4])
        #--Iref >> fid
        getFid = saveFile.getFid
        face.race = getFid(face.race)
        face.hair = getFid(face.hair)
        face.eye = getFid(face.eye)
        face.npc_class = getFid(face.npc_class)
        #--Changed NPC Record
        PCFaces.save_getChangedNpc(saveFile, _player_fid, face)
        #--Done
        return face

    # Save Set ----------------------------------------------------------------
    @staticmethod
    def save_setFace(saveInfo, face, pcf_flags=0):
        """DEPRECATED. Write a pcFace to a save file."""
        saveFile = SaveFile(saveInfo)
        saveFile.load()
        PCFaces.save_setPlayerFace(saveFile, face, pcf_flags)
        saveFile.safeSave()

    @staticmethod
    def save_setCreatedFace(saveFile, targetid: int, face): ##: UNUSED!
        """Sets created face in savefile to specified face.
        Note: Created NPCs do NOT use irefs!"""
        #--Find record
        for rfid, record in saveFile.created.items():
            if rfid == targetid:
                if record._rec_sig != b'NPC_':
                    raise StateError(f'Record {targetid:08X} in '
                                     f'{saveFile.fileInfo} is not an NPC.')
                npc = record.getTypeCopy()
                saveFile.created[rfid] = npc
                break
        else:
            raise StateError(f'Record {targetid:08X} not found in '
                             f'{saveFile.fileInfo}.')
        #--Update masters
        for save_rec_fid in (face.race, face.eye, face.hair):
            if not save_rec_fid: continue
            maxMaster = len(face.face_masters) - 1
            mod = save_rec_fid >> 24
            master = face.face_masters[min(mod, maxMaster)]
            saveFile.addMaster(master) # won't add it if it's there
        masterMap = MasterMap(face.face_masters, saveFile._masters)
        #--Set face
        npc.npc_flags.npc_female = (face.gender & 0x1)
        PCFaces._set_npc_attrs(npc, face, masterMap)
        #--Stats: Skip Level, base_spell, fatigue and factions since they're discarded by game engine.
        if face.skills: npc.skills = face.skills
        if face.health:
            npc.health = face.health
            npc.unused2 = face.unused2
        if face.attributes: npc.attributes = face.attributes
        if face.npc_class: npc.npc_class = face.npc_class
        npc.setChanged()
        npc.getSize()
        #--Change record?
        changeRecord = saveFile.get_npc(npc_int_fid := npc.fid)
        if changeRecord is None: return
        npc, version = changeRecord
        if not npc.acbs: npc.acbs = SreNPC.ACBS()
        npc.acbs.npc_flags.npc_female = face.gender
        npc.acbs.level_offset = face.level_offset
        npc.acbs.base_spell = face.base_spell
        npc.acbs.fatigue = face.fatigue
        npc.modifiers = face.modifiers[:]
        #--Fid conversion
        getIref = saveFile.getIref
        npc.spells = [getIref(x) for x in face.spells]
        npc.factions = [(getIref(x),y) for x,y in face.factions]
        #--Done
        saveFile.fid_recNum[npc_int_fid] = npc.getTuple(version)

    @staticmethod
    def save_setPlayerFace(saveFile, face, pcf_flags=0):
        """Write a pcFace to a save file."""
        pcf_flags = PCFaces.pcf_flags(pcf_flags)
        #--Update masters
        maxMaster = len(face.face_masters) - 1
        for fid in (face.race, face.eye, face.hair, face.npc_class):
            if not fid: continue
            master = face.face_masters[min(fid >> 24, maxMaster)]
            saveFile.addMaster(master) # won't add it if it's there
        masterMap = MasterMap(face.face_masters, saveFile._masters)
        #--Player ACHR
        #--Buffer for modified record data
        buff = io.BytesIO()
        def buffPack(*args):
            buff.write(struct_pack(*args))
        def buffPackRef(oldFid,doPack=True):
            newFid = oldFid and masterMap(oldFid, None)
            if newFid and doPack:
                newRef = saveFile.getIref(newFid.short_fid)
                pack_int(buff, newRef)
            else:
                buff.seek(4,1)
        oldRecord = saveFile.fid_recNum.get(0x14)
        oldData = oldRecord[-1]
        namePos = PCFaces.save_getNamePos(saveFile.fileInfo.fn_key, oldData,
                                          encode(saveFile.header.pcName))
        buff.write(oldData)
        #--Modify buffer with face data.
        buff.seek(namePos-542)
        buffPack(u'=200s120s200s',face.fggs_p, face.fgga_p, face.fgts_p)
        #--Race?
        buffPackRef(face.race, pcf_flags.pcf_race)
        #--Hair, Eyes?
        buffPackRef(face.hair, pcf_flags.pcf_hair)
        buffPackRef(face.eye, pcf_flags.pcf_eye)
        if pcf_flags.pcf_hair:
            buffPack(u'=f3Bs',face.hairLength,face.hairRed,face.hairBlue,face.hairGreen,face.unused3)
        else:
            buff.seek(8,1)
        #--Gender?
        if pcf_flags.pcf_gender:
            pack_byte(buff, face.gender)
        else:
            buff.seek(1,1)
        #--Name?
        if pcf_flags.pcf_name:
            postName = buff.getvalue()[buff.tell() +
                                       len(saveFile.header.pcName) + 2:]
            pack_byte(buff,len(face.pcName)+1)
            buff.write(encode(face.pcName, firstEncoding=Path.sys_fs_enc))
            buff.write(b'\x00')
            buff.write(postName)
            buff.seek(-len(postName),1)
            saveFile.header.pcName = face.pcName
        else:
            buff.seek(len(saveFile.header.pcName) + 2, 1)
        #--Class?
        if pcf_flags.pcf_class and face.npc_class:
            pos = buff.tell()
            newClass = masterMap(face.npc_class)
            oldClass = saveFile.fids[struct_unpack(u'I', buff.read(4))[0]]
            customClass = saveFile.getIref(0x22843)
            if customClass not in (newClass.short_fid, oldClass):
                buff.seek(pos)
                buffPackRef(newClass)
        newData = buff.getvalue()
        saveFile.fid_recNum[0x14] = (*oldRecord[:-1], newData)
        #--Player NPC
        npc, version = saveFile.get_npc()
        #--Gender
        if pcf_flags.pcf_gender and npc.acbs:
            npc.acbs.npc_flags.npc_female = face.gender
        #--Stats
        if pcf_flags.pcf_stats and npc.acbs:
            npc.acbs.level_offset = face.level_offset
            npc.acbs.base_spell = face.base_spell
            npc.acbs.fatigue = face.fatigue
            npc.attributes = face.attributes
            npc.skills = face.skills
            npc.health = face.health
            npc.unused2 = face.unused2
        #--Factions: Faction assignment doesn't work. (Probably stored in achr.)
        #--Modifiers, Spells, Name
        if pcf_flags.pcf_modifiers:
            npc.modifiers = face.modifiers[:]
        if pcf_flags.pcf_spells:
            npc.spells = [saveFile.getIref(x) for x in face.spells]
        npc.full = None
        #--Save
        saveFile.fid_recNum[_player_fid] = npc.getTuple(version)

    # Save Misc ----------------------------------------------------------------
    @staticmethod
    def save_repairHair(saveInfo):
        """Repairs hair if it has been zeroed. (Which happens if hair came from a
        cosmetic mod that has since been removed.) Returns True if repaired, False
        if no repair was necessary."""
        saveFile = SaveFile(saveInfo)
        saveFile.load()
        record = saveFile.fid_recNum.get(0x14)
        data = record[-1]
        namePos = PCFaces.save_getNamePos(saveInfo.fn_key, data,
                                          encode(saveFile.header.pcName))
        raceRef,hairRef = struct_unpack(u'2I', data[namePos-22:namePos-14])
        if hairRef != 0: return False
        raceForm = raceRef and saveFile.fids[raceRef]
        gender, = struct_unpack(u'B', data[namePos-2])
        if gender:
            hairForm = bush.game.raceHairFemale.get(raceForm,0x1da83)
        else:
            hairForm = bush.game.raceHairMale.get(raceForm,0x90475)
        hairRef = saveFile.getIref(hairForm)
        data = data[:namePos-18]+struct_pack(u'I', hairRef)+data[namePos-14:]
        saveFile.fid_recNum[0x14] = (*record[:-1], data)
        saveFile.safeSave()
        return True
    # MODS --------------------------------------------------------------------
    @staticmethod
    def _mod_load_fact(modInfo, keepAll=False, by_sig=None):
        lf = LoadFactory(keepAll=keepAll, by_sig=by_sig)
        modFile = ModFile(modInfo, lf)
        if (not keepAll) or modInfo.getPath().exists(): # read -> keepAll=False
            modFile.load_plugin()
        return modFile

    @staticmethod
    def mod_getFaces(modInfo):
        """Returns an array of PCFaces from a mod file."""
        #--Mod File
        modFile = PCFaces._mod_load_fact(modInfo, by_sig=[b'NPC_'])
        faces = {}
        for _rid, npc in modFile.tops[b'NPC_'].iter_present_records():
            face = PCFaces.PCFace()
            face.face_masters = modFile.augmented_masters()
            for att in ('eid', 'race', 'eye', 'hair', 'hairLength', 'hairRed',
                        'hairBlue', 'hairGreen', 'unused3', 'fggs_p', 'fgga_p',
                        'fgts_p', 'level_offset', 'skills', 'health',
                        'npc_class', 'unused2', 'base_spell', 'fatigue',
                        'attributes'):
                npc_val = getattr(npc, att)
                if isinstance(npc_val, FormId):
                    npc_val = npc_val.short_fid # saves code uses the ints...
                setattr(face, att, npc_val)
            face.gender = npc.npc_flags.npc_female
            face.pcName = npc.full
            faces[face.eid] = face
        return faces

    @staticmethod
    def mod_getRaceFaces(modInfo):
        """Returns an array of Race Faces from a mod file."""
        modFile = PCFaces._mod_load_fact(modInfo, by_sig=[b'RACE'])
        faces = {}
        for _rid, race in modFile.tops[b'RACE'].iter_present_records():
            face = PCFaces.PCFace()
            face.face_masters = []
            for field in (u'eid',u'fggs_p',u'fgga_p',u'fgts_p'):
                setattr(face,field,getattr(race,field))
            faces[face.eid] = face
        return faces

    @staticmethod
    def mod_addFace(modInfo,face):
        """Writes a pcFace to a mod file."""
        #--Mod File
        modFile = PCFaces._mod_load_fact(modInfo, keepAll=True,
                                         by_sig=[b'NPC_'])
        #--Tes4
        tes4 = modFile.tes4
        if not tes4.author:
            tes4.author = u'[wb]'
        if not tes4.description:
            tes4.description = _(u'Face dump from save game.')
        if bush.game.master_file not in tes4.masters:
            tes4.masters.append(bush.game.master_file)
        masterMap = MasterMap(face.face_masters, modFile.augmented_masters())
        #--Eid
        npcEids = {r.eid for r in modFile.tops[b'NPC_'].iter_records(skip_flagged=False)}
        eidForm = u''.join(('sg', bush.game.raceShortNames.get(face.race, 'Unk'),
            (face.gender and 'a' or 'u'), re.sub(r'\W', '', face.pcName), '%02d'))
        count,eid = 0, eidForm % 0
        while eid in npcEids:
            count += 1
            eid = eidForm % count
        #--NPC
        npc = modFile.create_record(b'NPC_', head_flags=0x40000)
        npc.eid = eid
        npc.npc_flags = RecordType.sig_to_class[b'NPC_'].NpcFlags() ##: setDefault - drop this!
        npc.npc_flags.npc_female = face.gender
        npc.npc_class = masterMap(face.npc_class,0x237a8) #--Default to Acrobat
        PCFaces._set_npc_attrs(npc, face, masterMap)
        #--Stats
        npc.level_offset = face.level_offset
        npc.base_spell = face.base_spell
        npc.fatigue = face.fatigue
        if face.skills: npc.skills = face.skills
        if face.health:
            npc.health = face.health
            npc.unused2 = face.unused2
        else:
            # Still have to set the defaults or we blow up in MelLists
            npc.health = 0
            npc.unused2 = b'\x00\x00'
        if face.attributes: npc.attributes = face.attributes
        #--Save
        modFile.safeSave()
        return npc

    @staticmethod
    def _set_npc_attrs(npc, face, masterMap):
        npc.full = face.pcName
        npc.setRace(masterMap(face.race, 0x00907))  #--Default to Imperial
        npc.eye = masterMap(face.eye, None)
        npc.hair = masterMap(face.hair, None)
        npc.hairLength = face.hairLength
        npc.hairRed = face.hairRed
        npc.hairBlue = face.hairBlue
        npc.hairGreen = face.hairGreen
        npc.unused3 = face.unused3
        npc.fggs_p = face.fggs_p
        npc.fgga_p = face.fgga_p
        npc.fgts_p = face.fgts_p
