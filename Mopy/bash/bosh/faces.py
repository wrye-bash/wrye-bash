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

import io
import re
from . import SaveInfo
from ._saves import SreNPC, SaveFile
from .. import bush, bolt
from ..bolt import Flags, encode, Path, struct_pack, struct_unpack, \
    pack_int, pack_byte
from ..brec import getModIndex, MreRecord, genFid, RecHeader, null2
from ..exception import SaveFileError, StateError
from ..mod_files import LoadFactory, MasterMap, ModFile

class PCFaces(object):
    """Package: Objects and functions for working with face data."""
    pcf_flags = Flags(0, Flags.getNames(u'pcf_name', u'race', u'gender',
                                        u'hair', u'eye', u'iclass', u'stats',
                                        u'factions', u'modifiers', u'spells'))

    class PCFace(object):
        """Represents a face."""
        __slots__ = (
            u'face_masters', u'eid', u'pcName', u'race', u'gender', u'eye',
            u'hair', u'hairLength', u'hairRed', u'hairBlue', u'hairGreen',
            u'unused3', u'fggs_p', u'fgga_p', u'fgts_p', u'level_offset',
            u'attributes', u'skills', u'health', u'unused2', u'baseSpell',
            u'fatigue', u'iclass', u'factions', u'modifiers', u'spells')

        def __init__(self):
            self.face_masters = []
            self.eid = self.pcName = u'generic'
            self.fggs_p = self.fgts_p = b'\x00'*4*50
            self.fgga_p = b'\x00'*4*30
            self.unused2 = null2
            self.health = self.unused3 = self.baseSpell = self.fatigue = 0
            self.level_offset = 0
            self.skills = self.attributes = self.iclass = None
            self.factions = []
            self.modifiers = []
            self.spells = []

        def getGenderName(self):
            return self.gender and u'Female' or u'Male'

        def getRaceName(self):
            return bush.game.raceNames.get(self.race,_(u'Unknown'))

        def convertRace(self,fromRace,toRace):
            """Converts face from one race to another while preserving structure, etc."""
            for a, f in ((u'fggs_p', u'50f'), (u'fgga_p', u'30f'),
                         (u'fgts_p', u'50f')):
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
            raise SaveFileError(saveName,u'Failed to find pcName in PC ACHR record.')
        namePos2 = data.find(pcName,namePos+1)
        if namePos2 != -1:
            raise SaveFileError(saveName,
                u'Uncertain about position of face data, probably because '
                u'player character name is too short. Try renaming player '
                u'character in save game.')
        return namePos

    # Save Get ----------------------------------------------------------------
    @staticmethod
    def save_getFaces(saveFile):
        """Returns player and created faces from a save file or saveInfo."""
        if isinstance(saveFile,SaveInfo):
            saveInfo = saveFile
            saveFile = SaveFile(saveInfo)
            saveFile.load()
        faces = PCFaces.save_getCreatedFaces(saveFile)
        playerFace = PCFaces.save_getPlayerFace(saveFile)
        faces[7] = playerFace
        return faces

    @staticmethod
    def save_getCreatedFace(saveFile,targetid):
        """Gets a particular created face."""
        return PCFaces.save_getCreatedFaces(saveFile,targetid).get(targetid)

    @staticmethod
    def save_getCreatedFaces(saveFile,targetid=None):
        """Returns created faces from savefile. If fid is supplied, will only
        return created face with that fid.
        Note: Created NPCs do NOT use irefs!"""
        targetid = bolt.intArg(targetid)
        if isinstance(saveFile,SaveInfo):
            saveInfo = saveFile
            saveFile = SaveFile(saveInfo)
            saveFile.load()
        faces = {}
        for record in saveFile.created:
            if record._rec_sig != b'NPC_': continue
            #--Created NPC record
            if targetid and record.fid != targetid: continue
            npc = record.getTypeCopy()
            face = faces[npc.fid] = PCFaces.PCFace()
            face.face_masters = saveFile._masters
            for a in (u'eid', u'race', u'eye', u'hair', u'hairLength',
                      u'hairRed', u'hairBlue', u'hairGreen', u'unused3',
                      u'fggs_p', u'fgga_p', u'fgts_p', u'level_offset',
                      u'skills', u'health', u'unused2', u'baseSpell',
                      u'fatigue', u'attributes', u'iclass'):
                setattr(face, a, getattr(npc, a))
            face.gender = (0,1)[npc.flags.female]
            face.pcName = npc.full
            #--Changed NPC Record
            PCFaces.save_getChangedNpc(saveFile,record.fid,face)
        return faces

    @staticmethod
    def save_getChangedNpc(saveFile,fid,face=None):
        """Update face with data from npc change record."""
        face = face or PCFaces.PCFace()
        changeRecord = saveFile.getRecord(fid)
        if not changeRecord:
            return face
        fid,_recType,recFlags,version,data = changeRecord
        npc = SreNPC(recFlags,data)
        if npc.acbs:
            face.gender = npc.acbs.flags.female
            face.level_offset = npc.acbs.level_offset
            face.baseSpell = npc.acbs.baseSpell
            face.fatigue = npc.acbs.fatigue
        for a in (u'attributes', u'skills', u'health', u'unused2'):
            npc_val = getattr(npc, a)
            if npc_val is not None:
                setattr(face, a, npc_val)
        #--Iref >> fid
        getFid = saveFile.getFid
        face.spells = [getFid(x) for x in (npc.spells or [])]
        face.factions = [(getFid(x),y) for x,y in (npc.factions or [])]
        face.modifiers = (npc.modifiers or [])[:]
        #delist('npc.spells:',[strFid(x) for x in face.spells])
        #delist('npc.factions:',face.factions)
        #delist('npc.modifiers:',face.modifiers)
        return face

    @staticmethod
    def save_getPlayerFace(saveFile):
        """Extract player face from save file."""
        if isinstance(saveFile,SaveInfo):
            saveInfo = saveFile
            saveFile = SaveFile(saveInfo)
            saveFile.load()
        face = PCFaces.PCFace()
        face.pcName = saveFile.header.pcName
        face.face_masters = saveFile._masters
        #--Player ACHR
        record = saveFile.getRecord(0x14)
        data = record[-1]
        namePos = PCFaces.save_getNamePos(saveFile.fileInfo.ci_key, data,
                                          encode(saveFile.header.pcName))
        (face.fggs_p, face.fgga_p, face.fgts_p, face.race, face.hair, face.eye,
            face.hairLength, face.hairRed, face.hairBlue, face.hairGreen, face.unused3, face.gender) = struct_unpack(
            u'=200s120s200s3If3BsB',data[namePos-542:namePos-1])
        classPos = namePos + len(saveFile.header.pcName) + 1
        face.iclass, = struct_unpack(u'I', data[classPos:classPos+4])
        #--Iref >> fid
        getFid = saveFile.getFid
        face.race = getFid(face.race)
        face.hair = getFid(face.hair)
        face.eye = getFid(face.eye)
        face.iclass = getFid(face.iclass)
        #--Changed NPC Record
        PCFaces.save_getChangedNpc(saveFile,7,face)
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
    def save_setCreatedFace(saveFile,targetid,face):
        """Sets created face in savefile to specified face.
        Note: Created NPCs do NOT use irefs!"""
        targetid = bolt.intArg(targetid)
        #--Find record
        for index,record in enumerate(saveFile.created):
            if record.fid == targetid:
                if record._rec_sig != b'NPC_':
                    raise StateError(u'Record %08X in %s is not an NPC.' % (
                        targetid, saveFile.fileInfo))
                npc = record.getTypeCopy()
                saveFile.created[index] = npc
                break
        else:
            raise StateError(u'Record %08X not found in %s.' % (
                targetid, saveFile.fileInfo))
        #--Update masters
        for fid in (face.race, face.eye, face.hair):
            if not fid: continue
            maxMaster = len(face.face_masters) - 1
            mod = getModIndex(fid)
            master = face.face_masters[min(mod, maxMaster)]
            if master not in saveFile._masters:
                saveFile._masters.append(master)
        masterMap = MasterMap(face.face_masters, saveFile._masters)
        #--Set face
        npc.full = face.pcName
        npc.flags.female = (face.gender & 0x1)
        npc.setRace(masterMap(face.race,0x00907)) #--Default to Imperial
        npc.eye = masterMap(face.eye,None)
        npc.hair = masterMap(face.hair,None)
        npc.hairLength = face.hairLength
        npc.hairRed = face.hairRed
        npc.hairBlue = face.hairBlue
        npc.hairGreen = face.hairGreen
        npc.unused3 = face.unused3
        npc.fggs_p = face.fggs_p
        npc.fgga_p = face.fgga_p
        npc.fgts_p = face.fgts_p
        #--Stats: Skip Level, baseSpell, fatigue and factions since they're discarded by game engine.
        if face.skills: npc.skills = face.skills
        if face.health:
            npc.health = face.health
            npc.unused2 = face.unused2
        if face.attributes: npc.attributes = face.attributes
        if face.iclass: npc.iclass = face.iclass
        npc.setChanged()
        npc.getSize()

        #--Change record?
        changeRecord = saveFile.getRecord(npc.fid)
        if changeRecord is None: return
        fid,_recType,recFlags,version,data = changeRecord
        npc = SreNPC(recFlags,data)
        if not npc.acbs: npc.acbs = npc.getDefault(u'acbs')
        npc.acbs.flags.female = face.gender
        npc.acbs.level_offset = face.level_offset
        npc.acbs.baseSpell = face.baseSpell
        npc.acbs.fatigue = face.fatigue
        npc.modifiers = face.modifiers[:]
        #--Fid conversion
        getIref = saveFile.getIref
        npc.spells = [getIref(x) for x in face.spells]
        npc.factions = [(getIref(x),y) for x,y in face.factions]

        #--Done
        saveFile.setRecord(npc.getTuple(fid,version))

    @staticmethod
    def save_setPlayerFace(saveFile, face, pcf_flags=0, morphFacts=None):
        """Write a pcFace to a save file."""
        pcf_flags = PCFaces.pcf_flags(pcf_flags)
        #--Update masters
        for fid in (face.race, face.eye, face.hair, face.iclass):
            if not fid: continue
            maxMaster = len(face.face_masters) - 1
            mod = getModIndex(fid)
            master = face.face_masters[min(mod, maxMaster)]
            if master not in saveFile._masters:
                saveFile._masters.append(master)
        masterMap = MasterMap(face.face_masters, saveFile._masters)

        #--Player ACHR
        #--Buffer for modified record data
        buff = io.BytesIO()
        def buffPack(*args):
            buff.write(struct_pack(*args))
        def buffPackRef(oldFid,doPack=True):
            newFid = oldFid and masterMap(oldFid,None)
            if newFid and doPack:
                newRef = saveFile.getIref(newFid)
                pack_int(buff, newRef)
            else:
                buff.seek(4,1)
        oldRecord = saveFile.getRecord(0x14)
        oldData = oldRecord[-1]
        namePos = PCFaces.save_getNamePos(saveFile.fileInfo.ci_key, oldData,
                                          encode(saveFile.header.pcName))
        buff.write(oldData)
        #--Modify buffer with face data.
        buff.seek(namePos-542)
        buffPack(u'=200s120s200s',face.fggs_p, face.fgga_p, face.fgts_p)
        #--Race?
        buffPackRef(face.race, pcf_flags.race)
        #--Hair, Eyes?
        buffPackRef(face.hair, pcf_flags.hair)
        buffPackRef(face.eye, pcf_flags.eye)
        if pcf_flags.hair:
            buffPack(u'=f3Bs',face.hairLength,face.hairRed,face.hairBlue,face.hairGreen,face.unused3)
        else:
            buff.seek(8,1)
        #--Gender?
        if pcf_flags.gender:
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
        if pcf_flags.iclass and face.iclass:
            pos = buff.tell()
            newClass = masterMap(face.iclass)
            oldClass = saveFile.fids[struct_unpack(u'I', buff.read(4))[0]]
            customClass = saveFile.getIref(0x22843)
            if customClass not in (newClass,oldClass):
                buff.seek(pos)
                buffPackRef(newClass)

        newData = buff.getvalue()
        saveFile.setRecord(oldRecord[:-1]+(newData,))

        #--Player NPC
        (fid,_recType,recFlags,version,data) = saveFile.getRecord(7)
        npc = SreNPC(recFlags,data)
        #--Gender
        if pcf_flags.gender and npc.acbs:
            npc.acbs.flags.female = face.gender
        #--Stats
        if pcf_flags.stats and npc.acbs:
            npc.acbs.level_offset = face.level_offset
            npc.acbs.baseSpell = face.baseSpell
            npc.acbs.fatigue = face.fatigue
            npc.attributes = face.attributes
            npc.skills = face.skills
            npc.health = face.health
            npc.unused2 = face.unused2
        #--Factions: Faction assignment doesn't work. (Probably stored in achr.)
        #--Modifiers, Spells, Name
        if pcf_flags.modifiers: npc.modifiers = face.modifiers[:]
        if pcf_flags.spells:
            #delist('Set PC Spells:',face.spells)
            npc.spells = [saveFile.getIref(x) for x in face.spells]
        npc.full = None
        #--Save
        saveFile.setRecord(npc.getTuple(fid,version))

    # Save Misc ----------------------------------------------------------------
    @staticmethod
    def save_repairHair(saveInfo):
        """Repairs hair if it has been zeroed. (Which happens if hair came from a
        cosmetic mod that has since been removed.) Returns True if repaired, False
        if no repair was necessary."""
        saveFile = SaveFile(saveInfo)
        saveFile.load()
        record = saveFile.getRecord(0x14)
        data = record[-1]
        namePos = PCFaces.save_getNamePos(saveInfo.ci_key, data,
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
        saveFile.setRecord(record[:-1]+(data,))
        saveFile.safeSave()
        return True

    # MODS --------------------------------------------------------------------
    @staticmethod
    def _mod_load_fact(modInfo, keepAll=False, by_sig=None):
        loadFactory = LoadFactory(keepAll=keepAll, by_sig=by_sig)
        modFile = ModFile(modInfo,loadFactory)
        if (not keepAll) or modInfo.getPath().exists(): # read -> keepAll=False
            modFile.load(True)
        return modFile

    @staticmethod
    def mod_getFaces(modInfo):
        """Returns an array of PCFaces from a mod file."""
        #--Mod File
        modFile = PCFaces._mod_load_fact(modInfo, by_sig=[b'NPC_'])
        short_mapper = modFile.getShortMapper()
        faces = {}
        for npc in modFile.tops[b'NPC_'].getActiveRecords():
            face = PCFaces.PCFace()
            face.face_masters = modFile.augmented_masters()
            for a in (u'eid', u'race', u'eye', u'hair', u'hairLength',
                      u'hairRed', u'hairBlue', u'hairGreen', u'unused3',
                      u'fggs_p', u'fgga_p', u'fgts_p', u'level_offset',
                      u'skills', u'health', u'unused2', u'baseSpell',
                      u'fatigue', u'attributes', u'iclass'):
                npc_val = getattr(npc, a)
                if isinstance(npc_val, tuple): # Hacky check for FormIDs
                    npc_val = short_mapper(npc_val)
                setattr(face, a, npc_val)
            face.gender = npc.flags.female
            face.pcName = npc.full
            faces[face.eid] = face
            #print face.pcName, face.race, face.hair, face.eye, face.hairLength, face.hairRed, face.hairBlue, face.hairGreen, face.unused3
        return faces

    @staticmethod
    def mod_getRaceFaces(modInfo):
        """Returns an array of Race Faces from a mod file."""
        modFile = PCFaces._mod_load_fact(modInfo, by_sig=[b'RACE'])
        faces = {}
        for race in modFile.tops[b'RACE'].getActiveRecords():
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
        from . import modInfos ##: put it here so I know it's initialized...
        if modInfos.masterName not in tes4.masters:
            tes4.masters.append(modInfos.masterName)
        masterMap = MasterMap(face.face_masters, modFile.augmented_masters())
        #--Eid
        npcEids = {record.eid for record in modFile.tops[b'NPC_'].records}
        eidForm = u''.join(('sg', bush.game.raceShortNames.get(face.race, 'Unk'),
            (face.gender and 'a' or 'u'), re.sub(r'\W', '', face.pcName), '%02d'))
        count,eid = 0, eidForm % 0
        while eid in npcEids:
            count += 1
            eid = eidForm % count
        #--NPC
        npcid = genFid(tes4.num_masters, tes4.getNextObject())
        npc = MreRecord.type_class[b'NPC_'](
            RecHeader(b'NPC_', 0, 0x40000, npcid, 0))
        npc.eid = eid
        npc.full = face.pcName
        npc.flags.female = face.gender
        npc.iclass = masterMap(face.iclass,0x237a8) #--Default to Acrobat
        npc.setRace(masterMap(face.race,0x00907)) #--Default to Imperial
        npc.eye = masterMap(face.eye,None)
        npc.hair = masterMap(face.hair,None)
        npc.hairLength = face.hairLength
        npc.hairRed = face.hairRed
        npc.hairBlue = face.hairBlue
        npc.hairGreen = face.hairGreen
        npc.unused3 = face.unused3
        npc.fggs_p = face.fggs_p
        npc.fgga_p = face.fgga_p
        npc.fgts_p = face.fgts_p
        #--Stats
        npc.level_offset = face.level_offset
        npc.baseSpell = face.baseSpell
        npc.fatigue = face.fatigue
        if face.skills: npc.skills = face.skills
        if face.health:
            npc.health = face.health
            npc.unused2 = face.unused2
        if face.attributes: npc.attributes = face.attributes
        npc.setChanged()
        modFile.tops[b'NPC_'].records.append(npc)
        #--Save
        modFile.safeSave()
        return npc
