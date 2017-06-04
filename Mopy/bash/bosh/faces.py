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
import struct
from .. import bass, bush, bolt
from ..bolt import Flags, encode, sio, Path
from ..exception import SaveFileError, StateError
from . import SaveInfo
from ._saves import SreNPC, SaveFile
from ..parsers import LoadFactory, ModFile, MasterMap
from ..brec import getModIndex, MreRecord, genFid, ModReader

class PCFaces:
    """Package: Objects and functions for working with face data."""
    flags = Flags(0L,Flags.getNames('name','race','gender','hair','eye','iclass','stats','factions','modifiers','spells'))

    class PCFace(object):
        """Represents a face."""
        __slots__ = ('masters','eid','pcName','race','gender','eye','hair',
            'hairLength','hairRed','hairBlue','hairGreen','unused3','fggs_p','fgga_p','fgts_p','level','attributes',
            'skills','health','unused2','baseSpell','fatigue','iclass','factions','modifiers','spells')
        def __init__(self):
            self.masters = []
            self.eid = self.pcName = u'generic'
            self.fggs_p = self.fgts_p = '\x00'*4*50
            self.fgga_p = '\x00'*4*30
            self.unused2 = bass.null2
            self.health = self.unused3 = self.baseSpell = self.fatigue = self.level = 0
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
            for attr,num in (('fggs_p',50),('fgga_p',30),('fgts_p',50)):
                format = unicode(num)+u'f'
                sValues = list(struct.unpack(format,getattr(self,attr)))
                fValues = list(struct.unpack(format,getattr(fromRace,attr)))
                tValues = list(struct.unpack(format,getattr(toRace,attr)))
                for index,(sValue,fValue,tValue) in enumerate(zip(sValues,fValues,tValues)):
                    sValues[index] = sValue + fValue - tValue
                setattr(self,attr,struct.pack(format,*sValues))

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
            if record.recType != 'NPC_': continue
            #--Created NPC record
            if targetid and record.fid != targetid: continue
            npc = record.getTypeCopy()
            face = faces[npc.fid] = PCFaces.PCFace()
            face.masters = saveFile.masters
            for attr in ('eid','race','eye','hair','hairLength',
                         'hairRed','hairBlue','hairGreen','unused3',
                         'fggs_p','fgga_p','fgts_p','level','skills',
                         'health','unused2','baseSpell', 'fatigue',
                         'attributes','iclass'):
                setattr(face,attr,getattr(npc,attr))
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
        fid,recType,recFlags,version,data = changeRecord
        npc = SreNPC(recFlags,data)
        if npc.acbs:
            face.gender = npc.acbs.flags.female
            face.level = npc.acbs.level
            face.baseSpell = npc.acbs.baseSpell
            face.fatigue = npc.acbs.fatigue
        for attr in ('attributes','skills','health','unused2'):
            value = getattr(npc,attr)
            if value is not None:
                setattr(face,attr,value)
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
        face.pcName = saveFile.pcName
        face.masters = saveFile.masters
        #--Player ACHR
        record = saveFile.getRecord(0x14)
        data = record[-1]
        namePos = PCFaces.save_getNamePos(saveFile.fileInfo.name,data,encode(saveFile.pcName))
        (face.fggs_p, face.fgga_p, face.fgts_p, face.race, face.hair, face.eye,
            face.hairLength, face.hairRed, face.hairBlue, face.hairGreen, face.unused3, face.gender) = struct.unpack(
            '=200s120s200s3If3BsB',data[namePos-542:namePos-1])
        classPos = namePos+len(saveFile.pcName)+1
        face.iclass, = struct.unpack('I',data[classPos:classPos+4])
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
    def save_setFace(saveInfo,face,flags=0L):
        """DEPRECATED. Write a pcFace to a save file."""
        saveFile = SaveFile(saveInfo)
        saveFile.load()
        PCFaces.save_setPlayerFace(saveFile,face,flags)
        saveFile.safeSave()

    @staticmethod
    def save_setCreatedFace(saveFile,targetid,face):
        """Sets created face in savefile to specified face.
        Note: Created NPCs do NOT use irefs!"""
        targetid = bolt.intArg(targetid)
        #--Find record
        for index,record in enumerate(saveFile.created):
            if record.fid == targetid:
                npc = record.getTypeCopy()
                saveFile.created[index] = npc
                break
        else:
            raise StateError(u"Record %08X not found in %s." % (targetid,saveFile.fileInfo.name.s))
        if npc.recType != 'NPC_':
            raise StateError(u"Record %08X in %s is not an NPC." % (targetid,saveFile.fileInfo.name.s))
        #--Update masters
        for fid in (face.race, face.eye, face.hair):
            if not fid: continue
            maxMaster = len(face.masters)-1
            mod = getModIndex(fid)
            master = face.masters[min(mod,maxMaster)]
            if master not in saveFile.masters:
                saveFile.masters.append(master)
        masterMap = MasterMap(face.masters,saveFile.masters)
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
        fid,recType,recFlags,version,data = changeRecord
        npc = SreNPC(recFlags,data)
        if not npc.acbs: npc.acbs = npc.getDefault('acbs')
        npc.acbs.flags.female = face.gender
        npc.acbs.level = face.level
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
    def save_setPlayerFace(saveFile,face,flags=0L,morphFacts=None):
        """Write a pcFace to a save file."""
        flags = PCFaces.flags(flags)
        #--Update masters
        for fid in (face.race, face.eye, face.hair, face.iclass):
            if not fid: continue
            maxMaster = len(face.masters)-1
            mod = getModIndex(fid)
            master = face.masters[min(mod,maxMaster)]
            if master not in saveFile.masters:
                saveFile.masters.append(master)
        masterMap = MasterMap(face.masters,saveFile.masters)

        #--Player ACHR
        #--Buffer for modified record data
        buff = sio()
        def buffPack(format,*args):
            buff.write(struct.pack(format,*args))
        def buffPackRef(oldFid,doPack=True):
            newFid = oldFid and masterMap(oldFid,None)
            if newFid and doPack:
                newRef = saveFile.getIref(newFid)
                buff.write(struct.pack('I',newRef))
            else:
                buff.seek(4,1)
        oldRecord = saveFile.getRecord(0x14)
        oldData = oldRecord[-1]
        namePos = PCFaces.save_getNamePos(saveFile.fileInfo.name,oldData,encode(saveFile.pcName))
        buff.write(oldData)
        #--Modify buffer with face data.
        buff.seek(namePos-542)
        buffPack('=200s120s200s',face.fggs_p, face.fgga_p, face.fgts_p)
        #--Race?
        buffPackRef(face.race,flags.race)
        #--Hair, Eyes?
        buffPackRef(face.hair,flags.hair)
        buffPackRef(face.eye,flags.eye)
        if flags.hair:
            buffPack('=f3Bs',face.hairLength,face.hairRed,face.hairBlue,face.hairGreen,face.unused3)
        else:
            buff.seek(8,1)
        #--Gender?
        if flags.gender:
            buffPack('B',face.gender)
        else:
            buff.seek(1,1)
        #--Name?
        if flags.name:
            postName = buff.getvalue()[buff.tell()+len(saveFile.pcName)+2:]
            buffPack('B',len(face.pcName)+1)
            buff.write(
                encode(face.pcName, firstEncoding=Path.sys_fs_enc) + '\x00')
            buff.write(postName)
            buff.seek(-len(postName),1)
            saveFile.pcName = face.pcName
        else:
            buff.seek(len(saveFile.pcName)+2,1)
        #--Class?
        if flags.iclass and face.iclass:
            pos = buff.tell()
            newClass = masterMap(face.iclass)
            oldClass = saveFile.fids[struct.unpack('I',buff.read(4))[0]]
            customClass = saveFile.getIref(0x22843)
            if customClass not in (newClass,oldClass):
                buff.seek(pos)
                buffPackRef(newClass)

        newData = buff.getvalue()
        saveFile.setRecord(oldRecord[:-1]+(newData,))

        #--Player NPC
        (fid,recType,recFlags,version,data) = saveFile.getRecord(7)
        npc = SreNPC(recFlags,data)
        #--Gender
        if flags.gender and npc.acbs:
            npc.acbs.flags.female = face.gender
        #--Stats
        if flags.stats and npc.acbs:
            npc.acbs.level = face.level
            npc.acbs.baseSpell = face.baseSpell
            npc.acbs.fatigue = face.fatigue
            npc.attributes = face.attributes
            npc.skills = face.skills
            npc.health = face.health
            npc.unused2 = face.unused2
        #--Factions: Faction assignment doesn't work. (Probably stored in achr.)
        #--Modifiers, Spells, Name
        if flags.modifiers: npc.modifiers = face.modifiers[:]
        if flags.spells:
            #delist('Set PC Spells:',face.spells)
            npc.spells = [saveFile.getIref(x) for x in face.spells]
        npc.full = None
        saveFile.setRecord(npc.getTuple(fid,version))
        #--Save
        buff.close()

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
        namePos = PCFaces.save_getNamePos(saveInfo.name,data,encode(saveFile.pcName))
        raceRef,hairRef = struct.unpack('2I',data[namePos-22:namePos-14])
        if hairRef != 0: return False
        raceForm = raceRef and saveFile.fids[raceRef]
        gender, = struct.unpack('B',data[namePos-2])
        if gender:
            hairForm = bush.game.raceHairFemale.get(raceForm,0x1da83)
        else:
            hairForm = bush.game.raceHairMale.get(raceForm,0x90475)
        hairRef = saveFile.getIref(hairForm)
        data = data[:namePos-18]+struct.pack('I',hairRef)+data[namePos-14:]
        saveFile.setRecord(record[:-1]+(data,))
        saveFile.safeSave()
        return True

    # MODS --------------------------------------------------------------------
    @staticmethod
    def mod_getFaces(modInfo):
        """Returns an array of PCFaces from a mod file."""
        #--Mod File
        loadFactory = LoadFactory(False,MreRecord.type_class['NPC_'])
        modFile = ModFile(modInfo,loadFactory)
        modFile.load(True)
        faces = {}
        for npc in modFile.NPC_.getActiveRecords():
            face = PCFaces.PCFace()
            face.masters = modFile.tes4.masters + [modInfo.name]
            for field in ('eid','race','eye','hair','hairLength',
                          'hairRed','hairBlue','hairGreen','unused3',
                          'fggs_p','fgga_p','fgts_p','level','skills',
                          'health','unused2','baseSpell',
                          'fatigue','attributes','iclass'):
                setattr(face,field,getattr(npc,field))
            face.gender = npc.flags.female
            face.pcName = npc.full
            faces[face.eid] = face
            #print face.pcName, face.race, face.hair, face.eye, face.hairLength, face.hairRed, face.hairBlue, face.hairGreen, face.unused3
        return faces

    @staticmethod
    def mod_getRaceFaces(modInfo):
        """Returns an array of Race Faces from a mod file."""
        loadFactory = LoadFactory(False,MreRecord.type_class['RACE'])
        modFile = ModFile(modInfo,loadFactory)
        modFile.load(True)
        faces = {}
        for race in modFile.RACE.getActiveRecords():
            face = PCFaces.PCFace()
            face.masters = []
            for field in ('eid','fggs_p','fgga_p','fgts_p'):
                setattr(face,field,getattr(race,field))
            faces[face.eid] = face
        return faces

    @staticmethod
    def mod_addFace(modInfo,face):
        """Writes a pcFace to a mod file."""
        #--Mod File
        loadFactory = LoadFactory(True,MreRecord.type_class['NPC_'])
        modFile = ModFile(modInfo,loadFactory)
        if modInfo.getPath().exists():
            modFile.load(True)
        #--Tes4
        tes4 = modFile.tes4
        if not tes4.author:
            tes4.author = u'[wb]'
        if not tes4.description:
            tes4.description = _(u'Face dump from save game.')
        from . import modInfos ##: put it here so I know it's initialized...
        if modInfos.masterName not in tes4.masters:
            tes4.masters.append(modInfos.masterName)
        masterMap = MasterMap(face.masters,tes4.masters+[modInfo.name])
        #--Eid
        npcEids = set([record.eid for record in modFile.NPC_.records])
        eidForm = u''.join((u"sg", bush.game.raceShortNames.get(face.race,u'Unk'),
            (face.gender and u'a' or u'u'), re.sub(ur'\W',u'',face.pcName),u'%02d'))
        count,eid = 0, eidForm % 0
        while eid in npcEids:
            count += 1
            eid = eidForm % count
        #--NPC
        npcid = genFid(len(tes4.masters),tes4.getNextObject())
        npc = MreRecord.type_class['NPC_'](ModReader.recHeader('NPC_',0,0x40000,npcid,0))
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
        npc.level = face.level
        npc.baseSpell = face.baseSpell
        npc.fatigue = face.fatigue
        if face.skills: npc.skills = face.skills
        if face.health:
            npc.health = face.health
            npc.unused2 = face.unused2
        if face.attributes: npc.attributes = face.attributes
        npc.setChanged()
        modFile.NPC_.records.append(npc)
        #--Save
        modFile.safeSave()
        return npc
