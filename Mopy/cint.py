from ctypes import *
import struct
from os.path import exists
if(exists(".\\bolt.py")):
    from bolt import GPath

if(exists(".\\CBash.dll")):
    CBash = CDLL("CBash.dll")
else:
    CBash = None

class PrintFormID(object):
    def __init__(self, formID):
        self._FormID = formID
    def __repr__(self):
        if(self._FormID): return "%08X" % self._FormID
        return "None"
    def __str__(self):
        if(self._FormID): return "%08X" % self._FormID
        return "None"


class BaseRecord(object):
    def __init__(self, CollectionIndex, ModName, recordID):
        self._CollectionIndex = CollectionIndex
        self._ModName = ModName
        self._recordID = recordID
    def LoadRecord(self):
        CBash.LoadRecord(self._CollectionIndex, self._ModName, self._recordID)
        return
    def UnloadRecord(self):
        CBash.UnloadRecord(self._CollectionIndex, self._ModName, self._recordID)
        return
    def DeleteRecord(self):
        CBash.DeleteRecord(self._CollectionIndex, self._ModName, self._recordID, 0)
        return

    def UpdateReferences(self, origFid, newFid):
        if not isinstance(origFid, int): return 0
        if not isinstance(newFid, int): return 0
        return CBash.UpdateReferences(self._CollectionIndex, self._ModName, self._recordID, origFid, newFid)
    def get_longFid(self):
        fid = self.fid
        if(fid == None): return (None,None)
        masterIndex = int(fid >> 24)
        object = int(fid & 0xFFFFFFL)
        master = CBash.GetModName(self._CollectionIndex, masterIndex)
        if(exists(".\\bolt.py")):
            return (GPath(master),object)
        return (master,object)
    def set_longFid(self, nValue):
        if not isinstance(nValue,tuple): return
        fid = CBash.GetCorrectedFID(self._CollectionIndex, nValue[0].s, nValue[1])
        if(fid == 0): return
        self.fid = fid
    longFid = property(get_longFid, set_longFid)
    def CopyAsOverride(self, targetMod):
        CBash.CopyFIDRecord(self._CollectionIndex, self._ModName, self._recordID, targetMod._ModName, c_bool(True))
        return
    def CopyAsNew(self, targetMod):
        CBash.CopyFIDRecord(self._CollectionIndex, self._ModName, self._recordID, targetMod._ModName, c_bool(False))
        return
    def get_flags1(self):
        CBash.ReadFIDField.restype = POINTER(c_int)
        retValue = CBash.ReadFIDField(self._CollectionIndex, self._ModName, self._recordID, 2)
        if(retValue): return retValue.contents.value
        return None
    def set_flags1(self, nValue):
        CBash.SetFIDFieldUI(self._CollectionIndex, self._ModName, self._recordID, 2, nValue)
    flags1 = property(get_flags1, set_flags1)
    def get_fid(self):
        CBash.ReadFIDField.restype = POINTER(c_int)
        retValue = CBash.ReadFIDField(self._CollectionIndex, self._ModName, self._recordID, 3)
        if(retValue): return retValue.contents.value
        return None
    def set_fid(self, nValue):
        nValue = CBash.SetRecordFormID(self._CollectionIndex, self._ModName, self._recordID, nValue)
        if(nValue != 0):
            self._recordID = nValue
    fid = property(get_fid, set_fid)
    def get_flags2(self):
        CBash.ReadFIDField.restype = POINTER(c_int)
        retValue = CBash.ReadFIDField(self._CollectionIndex, self._ModName, self._recordID, 4)
        if(retValue): return retValue.contents.value
        return None
    def set_flags2(self, nValue):
        CBash.SetFIDFieldUI(self._CollectionIndex, self._ModName, self._recordID, 4, nValue)
    flags2 = property(get_flags2, set_flags2)
    def get_eid(self):
        CBash.ReadFIDField.restype = c_char_p
        return CBash.ReadFIDField(self._CollectionIndex, self._ModName, self._recordID, 5)
    def set_eid(self, nValue):
        CBash.SetFIDFieldStr(self._CollectionIndex, self._ModName, self._recordID, 5, nValue)
    eid = property(get_eid, set_eid)
    def get_IsDeleted(self):
        return (self.flags1 & 0x00000020) != 0
    def set_IsDeleted(self, nValue):
        if (nValue == True): self.flags1 |= 0x00000020
        else: self.flags1 &= ~0x00000020
    IsDeleted = property(get_IsDeleted, set_IsDeleted)
    def get_IsBorderRegion(self):
        return (self.flags1 & 0x00000040) != 0
    def set_IsBorderRegion(self, nValue):
        if (nValue == True): self.flags1 |= 0x00000040
        else: self.flags1 &= ~0x00000040
    IsBorderRegion = property(get_IsBorderRegion, set_IsBorderRegion)
    def get_IsTurnOffFire(self):
        return (self.flags1 & 0x00000080) != 0
    def set_IsTurnOffFire(self, nValue):
        if (nValue == True): self.flags1 |= 0x00000080
        else: self.flags1 &= ~0x00000080
    IsTurnOffFire = property(get_IsTurnOffFire, set_IsTurnOffFire)
    def get_IsCastsShadows(self):
        return (self.flags1 & 0x00000200) != 0
    def set_IsCastsShadows(self, nValue):
        if (nValue == True): self.flags1 |= 0x00000200
        else: self.flags1 &= ~0x00000200
    IsCastsShadows = property(get_IsCastsShadows, set_IsCastsShadows)
    def get_IsQuestOrPersistent(self):
        return (self.flags1 & 0x00000400) != 0
    def set_IsQuestOrPersistent(self, nValue):
        if (nValue == True): self.flags1 |= 0x00000400
        else: self.flags1 &= ~0x00000400
    IsPersistent = IsQuest = IsQuestOrPersistent = property(get_IsQuestOrPersistent, set_IsQuestOrPersistent)
    def get_IsInitiallyDisabled(self):
        return (self.flags1 & 0x00000800) != 0
    def set_IsInitiallyDisabled(self, nValue):
        if (nValue == True): self.flags1 |= 0x00000800
        else: self.flags1 &= ~0x00000800
    IsInitiallyDisabled = property(get_IsInitiallyDisabled, set_IsInitiallyDisabled)
    def get_IsIgnored(self):
        return (self.flags1 & 0x00001000) != 0
    def set_IsIgnored(self, nValue):
        if (nValue == True): self.flags1 |= 0x00001000
        else: self.flags1 &= ~0x00001000
    IsIgnored = property(get_IsIgnored, set_IsIgnored)
    def get_IsVisibleWhenDistant(self):
        return (self.flags1 & 0x00008000) != 0
    def set_IsVisibleWhenDistant(self, nValue):
        if (nValue == True): self.flags1 |= 0x00008000
        else: self.flags1 &= ~0x00008000
    IsVWD = IsVisibleWhenDistant = property(get_IsVisibleWhenDistant, set_IsVisibleWhenDistant)
    def get_IsDangerousOrOffLimits(self):
        return (self.flags1 & 0x00020000) != 0
    def set_IsDangerousOrOffLimits(self, nValue):
        if (nValue == True): self.flags1 |= 0x00020000
        else: self.flags1 &= ~0x00020000
    IsDangerousOrOffLimits = property(get_IsDangerousOrOffLimits, set_IsDangerousOrOffLimits)
    def get_IsCompressed(self):
        return (self.flags1 & 0x00040000) != 0
    def set_IsCompressed(self, nValue):
        if (nValue == True): self.flags1 |= 0x00040000
        else: self.flags1 &= ~0x00040000
    IsCompressed = property(get_IsCompressed, set_IsCompressed)
    def get_IsCantWait(self):
        return (self.flags1 & 0x00080000) != 0
    def set_IsCantWait(self, nValue):
        if (nValue == True): self.flags1 |= 0x00080000
        else: self.flags1 &= ~0x00080000
    IsCantWait = property(get_IsCantWait, set_IsCantWait)
    baseattrs = ['flags1', 'flags2', 'eid']

class TES4Record(object):
    def __init__(self, CollectionIndex, ModName):
        self._CollectionIndex = CollectionIndex
        self._ModName = ModName
    def get_flags1(self):
        CBash.ReadTES4Field.restype = POINTER(c_uint)
        retValue = CBash.ReadTES4Field(self._CollectionIndex, self._ModName, 2)
        if(retValue): return retValue.contents.value
        return None
    def set_flags1(self, nValue):
        CBash.SetTES4FieldUI(self._CollectionIndex, self._ModName, 2, nValue)
    flags1 = property(get_flags1, set_flags1)
    def get_flags2(self):
        CBash.ReadTES4Field.restype = POINTER(c_uint)
        retValue = CBash.ReadTES4Field(self._CollectionIndex, self._ModName, 4)
        if(retValue): return retValue.contents.value
        return None
    def set_flags2(self, nValue):
        CBash.SetTES4FieldUI(self._CollectionIndex, self._ModName, 4, nValue)
    flags2 = property(get_flags2, set_flags2)
    def get_version(self):
        CBash.ReadTES4Field.restype = POINTER(c_float)
        retValue = CBash.ReadTES4Field(self._CollectionIndex, self._ModName, 6)
        if(retValue): return retValue.contents.value
        return None
    def set_version(self, nValue):
        CBash.SetTES4FieldF(self._CollectionIndex, self._ModName, 6, c_float(nValue))
    version = property(get_version, set_version)
    def get_numRecords(self):
        CBash.ReadTES4Field.restype = POINTER(c_uint)
        retValue = CBash.ReadTES4Field(self._CollectionIndex, self._ModName, 7)
        if(retValue): return retValue.contents.value
        return None
    def set_numRecords(self, nValue):
        CBash.SetTES4FieldUI(self._CollectionIndex, self._ModName, 7, nValue)
    numRecords = property(get_numRecords, set_numRecords)
    def get_nextObject(self):
        CBash.ReadTES4Field.restype = POINTER(c_uint)
        retValue = CBash.ReadTES4Field(self._CollectionIndex, self._ModName, 8)
        if(retValue): return retValue.contents.value
        return None
    def set_nextObject(self, nValue):
        CBash.SetTES4FieldUI(self._CollectionIndex, self._ModName, 8, nValue)
    nextObject = property(get_nextObject, set_nextObject)
    def get_ofst_p(self):
        numRecords = CBash.GetTES4FieldArraySize(self._CollectionIndex, self._ModName, 9)
        if(numRecords > 0):
            cRecords = POINTER(c_ubyte * numRecords)()
            CBash.GetTES4FieldArray(self._CollectionIndex, self._ModName, 9, byref(cRecords))
            return [cRecords.contents[x] for x in range(0, numRecords)]
        return []
    def set_ofst_p(self, nValue):
        length = len(nValue)
        CBash.SetTES4FieldR(self._CollectionIndex, self._ModName, 9, struct.pack('B' * length, *nValue), length)
    ofst_p = property(get_ofst_p, set_ofst_p)
    def get_dele_p(self):
        numRecords = CBash.GetTES4FieldArraySize(self._CollectionIndex, self._ModName, 10)
        if(numRecords > 0):
            cRecords = POINTER(c_ubyte * numRecords)()
            CBash.GetTES4FieldArray(self._CollectionIndex, self._ModName, 10, byref(cRecords))
            return [cRecords.contents[x] for x in range(0, numRecords)]
        return []
    def set_dele_p(self, nValue):
        length = len(nValue)
        CBash.SetTES4FieldR(self._CollectionIndex, self._ModName, 10, struct.pack('B' * length, *nValue), length)
    dele_p = property(get_dele_p, set_dele_p)
    def get_author(self):
        CBash.ReadTES4Field.restype = c_char_p
        return CBash.ReadTES4Field(self._CollectionIndex, self._ModName, 11)
    def set_author(self, nValue):
        CBash.SetTES4FieldStr(self._CollectionIndex, self._ModName, 11, nValue)
    author = property(get_author, set_author)
    def get_description(self):
        CBash.ReadTES4Field.restype = c_char_p
        return CBash.ReadTES4Field(self._CollectionIndex, self._ModName, 12)
    def set_description(self, nValue):
        CBash.SetTES4FieldStr(self._CollectionIndex, self._ModName, 12, nValue)
    description = property(get_description, set_description)
    def get_masters(self):
        numRecords = CBash.GetTES4FieldArraySize(self._CollectionIndex, self._ModName, 13)
        if(numRecords > 0):
            cRecords = (POINTER(c_char_p) * numRecords)()
            CBash.GetTES4FieldArray(self._CollectionIndex, self._ModName, 13, cRecords)
            return [string_at(cRecords[x]) for x in range(0, numRecords)]
        return []
    def set_masters(self, nValue):
        length = len(nValue)
        cRecords = (c_char_p * length)(*nValue)
        CBash.SetTES4FieldStrA(self._CollectionIndex, self._ModName, 13, byref(cRecords), length)
    masters = property(get_masters, set_masters)
    @property
    def DATA(self):
        return 0
    def get_IsESM(self):
        return (self.flags1 & 0x00000001) != 0
    def set_IsESM(self, nValue):
        if (nValue == True): self.flags1 |= 0x00000001
        else: self.flags1 &= ~0x00000001
    IsESM = property(get_IsESM, set_IsESM)
    attrs = ['flags1', 'flags2', 'version', 'numRecords', 'nextObject', 'author', 'description', 'masters']
    
class GMSTRecord(object):
    def __init__(self, CollectionIndex, ModName, recordID):
        self._CollectionIndex = CollectionIndex
        self._ModName = ModName
        self._recordID = recordID
    def DeleteRecord(self):
        CBash.DeleteGMSTRecord(self._CollectionIndex, self._ModName, self._recordID)
        return
    def UpdateReferences(self, origFid, newFid):
        return 0
    def get_longFid(self):
        fid = self.fid
        if(fid == None): return (None,None)
        masterIndex = int(fid >> 24)
        object = int(fid & 0xFFFFFFL)
        master = CBash.GetModName(self._CollectionIndex, masterIndex)
        if(exists(".\\bolt.py")):
            return (GPath(master),object)
        return (master,object)
    def set_longFid(self, nValue):
        if not isinstance(nValue,tuple): return
        fid = CBash.GetCorrectedFID(self._CollectionIndex, nValue[0].s, nValue[1])
        if(fid == 0): return
        self.fid = fid
    longFid = property(get_longFid, set_longFid)
    def CopyAsOverride(self, targetMod):
        recID = CBash.CopyGMSTRecord(self._CollectionIndex, self._ModName, self._recordID, targetMod._ModName)
        if(recID): return GMSTRecord(self._CollectionIndex, targetMod._ModName, self._recordID)
        return None

    def get_flags1(self):
        CBash.ReadGMSTField.restype = POINTER(c_int)
        retValue = CBash.ReadGMSTField(self._CollectionIndex, self._ModName, self._recordID, 2)
        if(retValue): return retValue.contents.value
        return None
    def set_flags1(self, nValue):
        CBash.SetGMSTFieldUI(self._CollectionIndex, self._ModName, self._recordID, 2, nValue)
    flags1 = property(get_flags1, set_flags1)
    def get_fid(self):
        CBash.ReadGMSTField.restype = POINTER(c_int)
        retValue = CBash.ReadGMSTField(self._CollectionIndex, self._ModName, self._recordID, 3)
        if(retValue): return retValue.contents.value
        return None
    def set_fid(self, nValue):
        nValue = CBash.SetRecordFormID(self._CollectionIndex, self._ModName, self._recordID, nValue)
        if(nValue != 0):
            self._recordID = nValue
    fid = property(get_fid, set_fid)
    def get_flags2(self):
        CBash.ReadGMSTField.restype = POINTER(c_int)
        retValue = CBash.ReadGMSTField(self._CollectionIndex, self._ModName, self._recordID, 4)
        if(retValue): return retValue.contents.value
        return None
    def set_flags2(self, nValue):
        CBash.SetGMSTFieldUI(self._CollectionIndex, self._ModName, self._recordID, 4, nValue)
    flags2 = property(get_flags2, set_flags2)
    @property
    def eid(self):
        #eid, unsettable due to conflicts with GMST_ModFile_Record. Will be fixed.
        CBash.ReadGMSTField.restype = c_char_p
        return CBash.ReadGMSTField(self._CollectionIndex, self._ModName, self._recordID, 5)
    def get_value(self):
        rFormat = CBash.GetGMSTFieldType(self._CollectionIndex, self._ModName, self._recordID, 6)
        if(rFormat == -1):
            return None
        elif(rFormat == 1):
            CBash.ReadGMSTField.restype = POINTER(c_int)
        elif(rFormat == 2):
            CBash.ReadGMSTField.restype = POINTER(c_float)
        elif(rFormat == 3):
            CBash.ReadGMSTField.restype = c_char_p
            return CBash.ReadGMSTField(self._CollectionIndex, self._ModName, self._recordID, 6)
        retValue = CBash.ReadGMSTField(self._CollectionIndex, self._ModName, self._recordID, 6)
        if(retValue): return retValue.contents.value
        return None
    def set_value(self, nValue):
        rFormat = CBash.GetGMSTFieldType(self._CollectionIndex, self._ModName, self._recordID, 6)
        if(rFormat == 1 and type(nValue) is int):
            CBash.SetGMSTFieldI(self._CollectionIndex, self._ModName, self._recordID, 6, nValue)
        elif(rFormat == 2 and type(nValue) is float):
            CBash.SetGMSTFieldF(self._CollectionIndex, self._ModName, self._recordID, 6, c_float(nValue))
        elif(rFormat == 3 and type(nValue) is str):
            CBash.SetGMSTFieldStr(self._CollectionIndex, self._ModName, self._recordID, 6, nValue)
    value = property(get_value, set_value)
    attrs = ['flags1', 'flags2', 'eid', 'value']

class GLOBRecord(BaseRecord):
    def CopyAsOverride(self, targetMod):
        FID = CBash.CopyGLOBRecord(self._CollectionIndex, self._ModName, self._recordID, targetMod._ModName, c_bool(True))
        if(FID): return GLOBRecord(self._CollectionIndex, targetMod._ModName, FID)
        return None
    def CopyAsNew(self, targetMod):
        FID = CBash.CopyGLOBRecord(self._CollectionIndex, self._ModName, self._recordID, targetMod._ModName, c_bool(False))
        if(FID): return GLOBRecord(self._CollectionIndex, targetMod._ModName, FID)
        return None
    def get_format(self):
        CBash.ReadFIDField.restype = POINTER(c_char)
        retValue = CBash.ReadFIDField(self._CollectionIndex, self._ModName, self._recordID, 6)
        if(retValue): return retValue.contents.value
        return None
    def set_format(self, nValue):
        CBash.SetFIDFieldC(self._CollectionIndex, self._ModName, self._recordID, 6, c_char(nValue))
    format = property(get_format, set_format)
    def get_value(self):
        CBash.ReadFIDField.restype = POINTER(c_float)
        retValue = CBash.ReadFIDField(self._CollectionIndex, self._ModName, self._recordID, 7)
        if(retValue): return retValue.contents.value
        return None
    def set_value(self, nValue):
        CBash.SetFIDFieldF(self._CollectionIndex, self._ModName, self._recordID, 7, c_float(nValue))
    value = property(get_value, set_value)
    attrs = BaseRecord.baseattrs + ['format', 'value']
    
class CLASRecord(BaseRecord):
    def CopyAsOverride(self, targetMod):
        FID = CBash.CopyCLASRecord(self._CollectionIndex, self._ModName, self._recordID, targetMod._ModName, c_bool(True))
        if(FID): return CLASRecord(self._CollectionIndex, targetMod._ModName, FID)
        return None
    def CopyAsNew(self, targetMod):
        FID = CBash.CopyCLASRecord(self._CollectionIndex, self._ModName, self._recordID, targetMod._ModName, c_bool(False))
        if(FID): return CLASRecord(self._CollectionIndex, targetMod._ModName, FID)
        return None
    def get_full(self):
        CBash.ReadFIDField.restype = c_char_p
        return CBash.ReadFIDField(self._CollectionIndex, self._ModName, self._recordID, 6)
    def set_full(self, nValue):
        CBash.SetFIDFieldStr(self._CollectionIndex, self._ModName, self._recordID, 6, nValue)
    full = property(get_full, set_full)
    def get_description(self):
        CBash.ReadFIDField.restype = c_char_p
        return CBash.ReadFIDField(self._CollectionIndex, self._ModName, self._recordID, 7)
    def set_description(self, nValue):
        CBash.SetFIDFieldStr(self._CollectionIndex, self._ModName, self._recordID, 7, nValue)
    description = property(get_description, set_description)
    def get_iconPath(self):
        CBash.ReadFIDField.restype = c_char_p
        return CBash.ReadFIDField(self._CollectionIndex, self._ModName, self._recordID, 8)
    def set_iconPath(self, nValue):
        CBash.SetFIDFieldStr(self._CollectionIndex, self._ModName, self._recordID, 8, nValue)
    iconPath = property(get_iconPath, set_iconPath)
    def get_primary1(self):
        CBash.ReadFIDField.restype = POINTER(c_int)
        retValue = CBash.ReadFIDField(self._CollectionIndex, self._ModName, self._recordID, 9)
        if(retValue): return retValue.contents.value
        return None
    def set_primary1(self, nValue):
        CBash.SetFIDFieldI(self._CollectionIndex, self._ModName, self._recordID, 9, nValue)
    primary1 = property(get_primary1, set_primary1)
    def get_primary2(self):
        CBash.ReadFIDField.restype = POINTER(c_int)
        retValue = CBash.ReadFIDField(self._CollectionIndex, self._ModName, self._recordID, 10)
        if(retValue): return retValue.contents.value
        return None
    def set_primary2(self, nValue):
        CBash.SetFIDFieldI(self._CollectionIndex, self._ModName, self._recordID, 10, nValue)
        
    primary2 = property(get_primary2, set_primary2)
    def get_specialization(self):
        CBash.ReadFIDField.restype = POINTER(c_uint)
        retValue = CBash.ReadFIDField(self._CollectionIndex, self._ModName, self._recordID, 11)
        if(retValue): return retValue.contents.value
        return None
    def set_specialization(self, nValue):
        CBash.SetFIDFieldUI(self._CollectionIndex, self._ModName, self._recordID, 11, nValue)
        
    specialization = property(get_specialization, set_specialization)
    def get_major1(self):
        CBash.ReadFIDField.restype = POINTER(c_int)
        retValue = CBash.ReadFIDField(self._CollectionIndex, self._ModName, self._recordID, 12)
        if(retValue): return retValue.contents.value
        return None
    def set_major1(self, nValue):
        CBash.SetFIDFieldI(self._CollectionIndex, self._ModName, self._recordID, 12, nValue)
        
    major1 = property(get_major1, set_major1)
    def get_major2(self):
        CBash.ReadFIDField.restype = POINTER(c_int)
        retValue = CBash.ReadFIDField(self._CollectionIndex, self._ModName, self._recordID, 13)
        if(retValue): return retValue.contents.value
        return None
    def set_major2(self, nValue):
        CBash.SetFIDFieldI(self._CollectionIndex, self._ModName, self._recordID, 13, nValue)
        
    major2 = property(get_major2, set_major2)
    def get_major3(self):
        CBash.ReadFIDField.restype = POINTER(c_int)
        retValue = CBash.ReadFIDField(self._CollectionIndex, self._ModName, self._recordID, 14)
        if(retValue): return retValue.contents.value
        return None
    def set_major3(self, nValue):
        CBash.SetFIDFieldI(self._CollectionIndex, self._ModName, self._recordID, 14, nValue)
        
    major3 = property(get_major3, set_major3)
    def get_major4(self):
        CBash.ReadFIDField.restype = POINTER(c_int)
        retValue = CBash.ReadFIDField(self._CollectionIndex, self._ModName, self._recordID, 15)
        if(retValue): return retValue.contents.value
        return None
    def set_major4(self, nValue):
        CBash.SetFIDFieldI(self._CollectionIndex, self._ModName, self._recordID, 15, nValue)
        
    major4 = property(get_major4, set_major4)
    def get_major5(self):
        CBash.ReadFIDField.restype = POINTER(c_int)
        retValue = CBash.ReadFIDField(self._CollectionIndex, self._ModName, self._recordID, 16)
        if(retValue): return retValue.contents.value
        return None
    def set_major5(self, nValue):
        CBash.SetFIDFieldI(self._CollectionIndex, self._ModName, self._recordID, 16, nValue)
        
    major5 = property(get_major5, set_major5)
    def get_major6(self):
        CBash.ReadFIDField.restype = POINTER(c_int)
        retValue = CBash.ReadFIDField(self._CollectionIndex, self._ModName, self._recordID, 17)
        if(retValue): return retValue.contents.value
        return None
    def set_major6(self, nValue):
        CBash.SetFIDFieldI(self._CollectionIndex, self._ModName, self._recordID, 17, nValue)
        
    major6 = property(get_major6, set_major6)
    def get_major7(self):
        CBash.ReadFIDField.restype = POINTER(c_int)
        retValue = CBash.ReadFIDField(self._CollectionIndex, self._ModName, self._recordID, 18)
        if(retValue): return retValue.contents.value
        return None
    def set_major7(self, nValue):
        CBash.SetFIDFieldI(self._CollectionIndex, self._ModName, self._recordID, 18, nValue)
        
    major7 = property(get_major7, set_major7)
    def get_flags(self):
        CBash.ReadFIDField.restype = POINTER(c_uint)
        retValue = CBash.ReadFIDField(self._CollectionIndex, self._ModName, self._recordID, 19)
        if(retValue): return retValue.contents.value
        return None
    def set_flags(self, nValue):
        CBash.SetFIDFieldUI(self._CollectionIndex, self._ModName, self._recordID, 19, nValue)
        
    flags = property(get_flags, set_flags)
    def get_services(self):
        CBash.ReadFIDField.restype = POINTER(c_uint)
        retValue = CBash.ReadFIDField(self._CollectionIndex, self._ModName, self._recordID, 20)
        if(retValue): return retValue.contents.value
        return None
    def set_services(self, nValue):
        CBash.SetFIDFieldUI(self._CollectionIndex, self._ModName, self._recordID, 20, nValue)
    services = property(get_services, set_services)
    def get_trainSkill(self):
        CBash.ReadFIDField.restype = POINTER(c_byte)
        retValue = CBash.ReadFIDField(self._CollectionIndex, self._ModName, self._recordID, 21)
        if(retValue): return retValue.contents.value
        return None
    def set_trainSkill(self, nValue):
        CBash.SetFIDFieldC(self._CollectionIndex, self._ModName, self._recordID, 21, c_byte(nValue))
    trainSkill = property(get_trainSkill, set_trainSkill)
    def get_trainLevel(self):
        CBash.ReadFIDField.restype = POINTER(c_ubyte)
        retValue = CBash.ReadFIDField(self._CollectionIndex, self._ModName, self._recordID, 22)
        if(retValue): return retValue.contents.value
        return None
    def set_trainLevel(self, nValue):
        CBash.SetFIDFieldUC(self._CollectionIndex, self._ModName, self._recordID, 22, c_ubyte(nValue))
    trainLevel = property(get_trainLevel, set_trainLevel)
    def get_unused1(self):
        numRecords = CBash.GetFIDFieldArraySize(self._CollectionIndex, self._ModName, self._recordID, 23)
        if(numRecords > 0):
            cRecords = POINTER(c_ubyte * numRecords)()
            CBash.GetFIDFieldArray(self._CollectionIndex, self._ModName, self._recordID, 23, byref(cRecords))
            return [cRecords.contents[x] for x in range(0, numRecords)]
        return []
    def set_unused1(self, nValue):
        CBash.SetFIDFieldR(self._CollectionIndex, self._ModName, self._recordID, 23, struct.pack('2B', *nValue), 2)
    unused1 = property(get_unused1, set_unused1)
    def get_IsPlayable(self):
        return (self.flags & 0x00000001) != 0
    def set_IsPlayable(self, nValue):
        if (nValue == True): self.flags |= 0x00000001
        else: self.flags &= ~0x00000001
    IsPlayable = property(get_IsPlayable, set_IsPlayable)
    def get_IsGuard(self):
        return (self.flags & 0x00000002) != 0
    def set_IsGuard(self, nValue):
        if (nValue == True): self.flags |= 0x00000002
        else: self.flags &= ~0x00000002
    IsGuard = property(get_IsGuard, set_IsGuard)
    def get_IsServicesWeapons(self):
        return (self.services & 0x00000001) != 0
    def set_IsServicesWeapons(self, nValue):
        if (nValue == True): self.services |= 0x00000001
        else: self.services &= ~0x00000001
    IsServicesWeapons = property(get_IsServicesWeapons, set_IsServicesWeapons)
    def get_IsServicesArmor(self):
        return (self.services & 0x00000002) != 0
    def set_IsServicesArmor(self, nValue):
        if (nValue == True): self.services |= 0x00000002
        else: self.services &= ~0x00000002
    IsServicesArmor = property(get_IsServicesArmor, set_IsServicesArmor)
    def get_IsServicesClothing(self):
        return (self.services & 0x00000004) != 0
    def set_IsServicesClothing(self, nValue):
        if (nValue == True): self.services |= 0x00000004
        else: self.services &= ~0x00000004
    IsServicesClothing = property(get_IsServicesClothing, set_IsServicesClothing)
    def get_IsServicesBooks(self):
        return (self.services & 0x00000008) != 0
    def set_IsServicesBooks(self, nValue):
        if (nValue == True): self.services |= 0x00000008
        else: self.services &= ~0x00000008
    IsServicesBooks = property(get_IsServicesBooks, set_IsServicesBooks)
    def get_IsServicesIngredients(self):
        return (self.services & 0x00000010) != 0
    def set_IsServicesIngredients(self, nValue):
        if (nValue == True): self.services |= 0x00000010
        else: self.services &= ~0x00000010
    IsServicesIngredients = property(get_IsServicesIngredients, set_IsServicesIngredients)
    def get_IsServicesLights(self):
        return (self.services & 0x00000080) != 0
    def set_IsServicesLights(self, nValue):
        if (nValue == True): self.services |= 0x00000080
        else: self.services &= ~0x00000080
    IsServicesLights = property(get_IsServicesLights, set_IsServicesLights)
    def get_IsServicesApparatus(self):
        return (self.services & 0x00000100) != 0
    def set_IsServicesApparatus(self, nValue):
        if (nValue == True): self.services |= 0x00000100
        else: self.services &= ~0x00000100
    IsServicesApparatus = property(get_IsServicesApparatus, set_IsServicesApparatus)
    def get_IsServicesMiscItems(self):
        return (self.services & 0x00000400) != 0
    def set_IsServicesMiscItems(self, nValue):
        if (nValue == True): self.services |= 0x00000400
        else: self.services &= ~0x00000400
    IsServicesMiscItems = property(get_IsServicesMiscItems, set_IsServicesMiscItems)
    def get_IsServicesSpells(self):
        return (self.services & 0x00000800) != 0
    def set_IsServicesSpells(self, nValue):
        if (nValue == True): self.services |= 0x00000800
        else: self.services &= ~0x00000800
    IsServicesSpells = property(get_IsServicesSpells, set_IsServicesSpells)
    def get_IsServicesMagicItems(self):
        return (self.services & 0x00001000) != 0
    def set_IsServicesMagicItems(self, nValue):
        if (nValue == True): self.services |= 0x00001000
        else: self.services &= ~0x00001000
    IsServicesMagicItems = property(get_IsServicesMagicItems, set_IsServicesMagicItems)
    def get_IsServicesPotions(self):
        return (self.services & 0x00002000) != 0
    def set_IsServicesPotions(self, nValue):
        if (nValue == True): self.services |= 0x00002000
        else: self.services &= ~0x00002000
    IsServicesPotions = property(get_IsServicesPotions, set_IsServicesPotions)
    def get_IsServicesTraining(self):
        return (self.services & 0x00004000) != 0
    def set_IsServicesTraining(self, nValue):
        if (nValue == True): self.services |= 0x00004000
        else: self.services &= ~0x00004000
    IsServicesTraining = property(get_IsServicesTraining, set_IsServicesTraining)
    def get_IsServicesRecharge(self):
        return (self.services & 0x00010000) != 0
    def set_IsServicesRecharge(self, nValue):
        if (nValue == True): self.services |= 0x00010000
        else: self.services &= ~0x00010000
    IsServicesRecharge = property(get_IsServicesRecharge, set_IsServicesRecharge)
    def get_IsServicesRepair(self):
        return (self.services & 0x00020000) != 0
    def set_IsServicesRepair(self, nValue):
        if (nValue == True): self.services |= 0x00020000
        else: self.services &= ~0x00020000
    IsServicesRepair = property(get_IsServicesRepair, set_IsServicesRepair)
    attrs = BaseRecord.baseattrs + ['full', 'description', 'iconPath', 'primary1', 'primary2', 'specialization',
                         'major1', 'major2', 'major3', 'major4', 'major5', 'major6', 'major7',
                         'flags', 'services', 'trainSkill', 'trainLevel']

class FACTRecord(BaseRecord):
    def CopyAsOverride(self, targetMod):
        FID = CBash.CopyFACTRecord(self._CollectionIndex, self._ModName, self._recordID, targetMod._ModName, c_bool(True))
        if(FID): return FACTRecord(self._CollectionIndex, targetMod._ModName, FID)
        return None
    def CopyAsNew(self, targetMod):
        FID = CBash.CopyFACTRecord(self._CollectionIndex, self._ModName, self._recordID, targetMod._ModName, c_bool(False))
        if(FID): return FACTRecord(self._CollectionIndex, targetMod._ModName, FID)
        return None
    class Relation(object):
        def __init__(self, CollectionIndex, ModName, recordID, listIndex):
            self._CollectionIndex = CollectionIndex
            self._ModName = ModName
            self._recordID = recordID
            self._listIndex = listIndex
        def get_faction(self):
            CBash.ReadFIDListField.restype = POINTER(c_uint)
            retValue = CBash.ReadFIDListField(self._CollectionIndex, self._ModName, self._recordID, 7, self._listIndex, 1)
            if(retValue): return retValue.contents.value
            return None
        def set_faction(self, nValue):
            CBash.SetFIDListFieldUI(self._CollectionIndex, self._ModName, self._recordID, 7, self._listIndex, 1, nValue)
        faction = property(get_faction, set_faction)
        def get_mod(self):
            CBash.ReadFIDListField.restype = POINTER(c_int)
            retValue = CBash.ReadFIDListField(self._CollectionIndex, self._ModName, self._recordID, 7, self._listIndex, 2)
            if(retValue): return retValue.contents.value
            return None
        def set_mod(self, nValue):
            CBash.SetFIDListFieldI(self._CollectionIndex, self._ModName, self._recordID, 7, self._listIndex, 2, nValue)
        mod = property(get_mod, set_mod)

    class Rank(object):
        def __init__(self, CollectionIndex, ModName, recordID, listIndex):
            self._CollectionIndex = CollectionIndex
            self._ModName = ModName
            self._recordID = recordID
            self._listIndex = listIndex
        def get_rank(self):
            CBash.ReadFIDListField.restype = POINTER(c_int)
            retValue = CBash.ReadFIDListField(self._CollectionIndex, self._ModName, self._recordID, 10, self._listIndex, 1)
            if(retValue): return retValue.contents.value
            return None
        def set_rank(self, nValue):
            CBash.SetFIDListFieldI(self._CollectionIndex, self._ModName, self._recordID, 10, self._listIndex, 1, nValue)
        rank = property(get_rank, set_rank)
        def get_male(self):
            CBash.ReadFIDListField.restype = c_char_p
            return CBash.ReadFIDListField(self._CollectionIndex, self._ModName, self._recordID, 10, self._listIndex, 2)
        def set_male(self, nValue):
            CBash.SetFIDListFieldStr(self._CollectionIndex, self._ModName, self._recordID, 10, self._listIndex, 2, nValue)
        male = property(get_male, set_male)
        def get_female(self):
            CBash.ReadFIDListField.restype = c_char_p
            return CBash.ReadFIDListField(self._CollectionIndex, self._ModName, self._recordID, 10, self._listIndex, 3)
        def set_female(self, nValue):
            CBash.SetFIDListFieldStr(self._CollectionIndex, self._ModName, self._recordID, 10, self._listIndex, 3, nValue)
        female = property(get_female, set_female)
        def get_insigniaPath(self):
            CBash.ReadFIDListField.restype = c_char_p
            return CBash.ReadFIDListField(self._CollectionIndex, self._ModName, self._recordID, 10, self._listIndex, 4)
        def set_insigniaPath(self, nValue):
            CBash.SetFIDListFieldStr(self._CollectionIndex, self._ModName, self._recordID, 10, self._listIndex, 4, nValue)
        insigniaPath = property(get_insigniaPath, set_insigniaPath)

    def newRelationsElement(self):
        listIndex = CBash.CreateFIDListElement(self._CollectionIndex, self._ModName, self._recordID, 7)
        if(listIndex == -1): return None
        return self.Relation(self._CollectionIndex, self._ModName, self._recordID, listIndex)

    def newRanksElement(self):
        listIndex = CBash.CreateFIDListElement(self._CollectionIndex, self._ModName, self._recordID, 10)
        if(listIndex == -1): return None
        return self.Rank(self._CollectionIndex, self._ModName, self._recordID, listIndex)
    
    def get_full(self):
        CBash.ReadFIDField.restype = c_char_p
        return CBash.ReadFIDField(self._CollectionIndex, self._ModName, self._recordID, 6)
    def set_full(self, nValue):
        CBash.SetFIDFieldStr(self._CollectionIndex, self._ModName, self._recordID, 6, nValue)

    full = property(get_full, set_full)
    def get_relations(self):
        numRecords = CBash.GetFIDListSize(self._CollectionIndex, self._ModName, self._recordID, 7)
        if(numRecords > 0): return [self.Relation(self._CollectionIndex, self._ModName, self._recordID, x) for x in range(0, numRecords)]
        return []
    def set_relations(self, nRelations):
        diffLength = len(nRelations) - CBash.GetFIDListSize(self._CollectionIndex, self._ModName, self._recordID, 7)
        nValues = [(relation.faction,relation.mod) for relation in nRelations]
        while(diffLength < 0):
            CBash.DeleteFIDListElement(self._CollectionIndex, self._ModName, self._recordID, 7)
            diffLength += 1
        while(diffLength > 0):
            CBash.CreateFIDListElement(self._CollectionIndex, self._ModName, self._recordID, 7)
            diffLength -= 1
        for oRelation, nValue in zip(self.relations, nValues):
            oRelation.faction, oRelation.mod = nValue
    relations = property(get_relations, set_relations)
    def get_flags(self):
        CBash.ReadFIDField.restype = POINTER(c_ubyte)
        retValue = CBash.ReadFIDField(self._CollectionIndex, self._ModName, self._recordID, 8)
        if(retValue): return retValue.contents.value
        return None
    def set_flags(self, nValue):
        CBash.SetFIDFieldUC(self._CollectionIndex, self._ModName, self._recordID, 8, c_ubyte(nValue))
    flags = property(get_flags, set_flags)
    def get_crimeGoldMultiplier(self):
        CBash.ReadFIDField.restype = POINTER(c_float)
        retValue = CBash.ReadFIDField(self._CollectionIndex, self._ModName, self._recordID, 9)
        if(retValue): return retValue.contents.value
        return None
    def set_crimeGoldMultiplier(self, nValue):
        CBash.SetFIDFieldF(self._CollectionIndex, self._ModName, self._recordID, 9, c_float(nValue))       
    crimeGoldMultiplier = property(get_crimeGoldMultiplier, set_crimeGoldMultiplier)
    def get_ranks(self):
        numRecords = CBash.GetFIDListSize(self._CollectionIndex, self._ModName, self._recordID, 10)
        if(numRecords > 0): return [self.Rank(self._CollectionIndex, self._ModName, self._recordID, x) for x in range(0, numRecords)]
        return []
    def set_ranks(self, nRanks):
        diffLength = len(nRanks) - CBash.GetFIDListSize(self._CollectionIndex, self._ModName, self._recordID, 10)
        nValues = [(nRank.rank, nRank.male, nRank.female, nRank.insigniaPath) for nRank in nRanks]
        while(diffLength < 0):
            CBash.DeleteFIDListElement(self._CollectionIndex, self._ModName, self._recordID, 10)
            diffLength += 1
        while(diffLength > 0):
            CBash.CreateFIDListElement(self._CollectionIndex, self._ModName, self._recordID, 10)
            diffLength -= 1
        for oRank, nValue in zip(self.ranks, nValues):
            oRank.rank, oRank.male, oRank.female, oRank.insigniaPath = nValue
    ranks = property(get_ranks, set_ranks)
    def get_IsHiddenFromPC(self):
        return (self.flags & 0x00000001) != 0
    def set_IsHiddenFromPC(self, nValue):
        if (nValue == True): self.flags |= 0x00000001
        else: self.flags &= ~0x00000001
    IsHiddenFromPC = property(get_IsHiddenFromPC, set_IsHiddenFromPC)
    def get_IsEvil(self):
        return (self.flags & 0x00000002) != 0
    def set_IsEvil(self, nValue):
        if (nValue == True): self.flags |= 0x00000002
        else: self.flags &= ~0x00000002
    IsEvil = property(get_IsEvil, set_IsEvil)
    def get_IsSpecialCombat(self):
        return (self.flags & 0x00000004) != 0
    def set_IsSpecialCombat(self, nValue):
        if (nValue == True): self.flags |= 0x00000004
        else: self.flags &= ~0x00000004
    IsSpecialCombat = property(get_IsSpecialCombat, set_IsSpecialCombat)
    attrs = BaseRecord.baseattrs + ['full', 'relations', 'flags', 'crimeGoldMultiplier', 'ranks']
    
class HAIRRecord(BaseRecord):
    def CopyAsOverride(self, targetMod):
        FID = CBash.CopyHAIRRecord(self._CollectionIndex, self._ModName, self._recordID, targetMod._ModName, c_bool(True))
        if(FID): return HAIRRecord(self._CollectionIndex, targetMod._ModName, FID)
        return None
    def CopyAsNew(self, targetMod):
        FID = CBash.CopyHAIRRecord(self._CollectionIndex, self._ModName, self._recordID, targetMod._ModName, c_bool(False))
        if(FID): return HAIRRecord(self._CollectionIndex, targetMod._ModName, FID)
        return None
    def get_full(self):
        CBash.ReadFIDField.restype = c_char_p
        return CBash.ReadFIDField(self._CollectionIndex, self._ModName, self._recordID, 6)
    def set_full(self, nValue):
        CBash.SetFIDFieldStr(self._CollectionIndex, self._ModName, self._recordID, 6, nValue)
    full = property(get_full, set_full)
    def get_modPath(self):
        CBash.ReadFIDField.restype = c_char_p
        return CBash.ReadFIDField(self._CollectionIndex, self._ModName, self._recordID, 7)
    def set_modPath(self, nValue):
        CBash.SetFIDFieldStr(self._CollectionIndex, self._ModName, self._recordID, 7, nValue)
    modPath = property(get_modPath, set_modPath)
    def get_modb(self):
        CBash.ReadFIDField.restype = POINTER(c_float)
        retValue = CBash.ReadFIDField(self._CollectionIndex, self._ModName, self._recordID, 8)
        if(retValue): return retValue.contents.value
        return None
    def set_modb(self, nValue):
        CBash.SetFIDFieldF(self._CollectionIndex, self._ModName, self._recordID, 8, c_float(nValue))
    modb = property(get_modb, set_modb)
    def get_modt_p(self):
        numRecords = CBash.GetFIDFieldArraySize(self._CollectionIndex, self._ModName, self._recordID, 9)
        if(numRecords > 0):
            cRecords = POINTER(c_ubyte * numRecords)()
            CBash.GetFIDFieldArray(self._CollectionIndex, self._ModName, self._recordID, 9, byref(cRecords))
            return [cRecords.contents[x] for x in range(0, numRecords)]
        return []
    def set_modt_p(self, nValue):
        length = len(nValue)
        CBash.SetFIDFieldR(self._CollectionIndex, self._ModName, self._recordID, 9, struct.pack('B' * length, *nValue), length)
    modt_p = property(get_modt_p, set_modt_p)
    def get_iconPath(self):
        CBash.ReadFIDField.restype = c_char_p
        return CBash.ReadFIDField(self._CollectionIndex, self._ModName, self._recordID, 10)
    def set_iconPath(self, nValue):
        CBash.SetFIDFieldStr(self._CollectionIndex, self._ModName, self._recordID, 10, nValue)
    iconPath = property(get_iconPath, set_iconPath)
    def get_flags(self):
        CBash.ReadFIDField.restype = POINTER(c_ubyte)
        retValue = CBash.ReadFIDField(self._CollectionIndex, self._ModName, self._recordID, 11)
        if(retValue): return retValue.contents.value
        return None
    def set_flags(self, nValue):
        CBash.SetFIDFieldUC(self._CollectionIndex, self._ModName, self._recordID, 11, c_ubyte(nValue))
    flags = property(get_flags, set_flags)
    def get_IsPlayable(self):
        return (self.flags & 0x00000001) != 0
    def set_IsPlayable(self, nValue):
        if (nValue == True): self.flags |= 0x00000001
        else: self.flags &= ~0x00000001
    IsPlayable = property(get_IsPlayable, set_IsPlayable)
    def get_IsNotMale(self):
        return (self.flags & 0x00000002) != 0
    def set_IsNotMale(self, nValue):
        if (nValue == True): self.flags |= 0x00000002
        else: self.flags &= ~0x00000002
    IsNotMale = property(get_IsNotMale, set_IsNotMale)
    def get_IsMale(self):
        return not self.get_IsNotMale()
    def set_IsMale(self, nValue):
        set_IsNotMale(not nValue)
    IsMale = property(get_IsMale, set_IsMale)
    def get_IsNotFemale(self):
        return (self.flags & 0x00000004) != 0
    def set_IsNotFemale(self, nValue):
        if (nValue == True): self.flags |= 0x00000004
        else: self.flags &= ~0x00000004
    IsNotFemale = property(get_IsNotFemale, set_IsNotFemale)
    def get_IsFemale(self):
        return not self.get_IsNotFemale()
    def set_IsFemale(self, nValue):
        set_IsNotFemale(not nValue)
    IsFemale = property(get_IsFemale, set_IsFemale)
    def get_IsFixedColor(self):
        return (self.flags & 0x00000008) != 0
    def set_IsFixedColor(self, nValue):
        if (nValue == True): self.flags |= 0x00000008
        else: self.flags &= ~0x00000008
    IsFixedColor = property(get_IsFixedColor, set_IsFixedColor)
    attrs = BaseRecord.baseattrs + ['full', 'modPath', 'modb', 'modt_p', 'iconPath', 'flags']
    
class EYESRecord(BaseRecord):
    def CopyAsOverride(self, targetMod):
        FID = CBash.CopyEYESRecord(self._CollectionIndex, self._ModName, self._recordID, targetMod._ModName, c_bool(True))
        if(FID): return EYESRecord(self._CollectionIndex, targetMod._ModName, FID)
        return None
    def CopyAsNew(self, targetMod):
        FID = CBash.CopyEYESRecord(self._CollectionIndex, self._ModName, self._recordID, targetMod._ModName, c_bool(False))
        if(FID): return EYESRecord(self._CollectionIndex, targetMod._ModName, FID)
        return None
    def get_full(self):
        CBash.ReadFIDField.restype = c_char_p
        return CBash.ReadFIDField(self._CollectionIndex, self._ModName, self._recordID, 6)
    def set_full(self, nValue):
        CBash.SetFIDFieldStr(self._CollectionIndex, self._ModName, self._recordID, 6, nValue)
    full = property(get_full, set_full)
    def get_iconPath(self):
        CBash.ReadFIDField.restype = c_char_p
        return CBash.ReadFIDField(self._CollectionIndex, self._ModName, self._recordID, 7)
    def set_iconPath(self, nValue):
        CBash.SetFIDFieldStr(self._CollectionIndex, self._ModName, self._recordID, 7, nValue)
    iconPath = property(get_iconPath, set_iconPath)
    def get_flags(self):
        CBash.ReadFIDField.restype = POINTER(c_ubyte)
        retValue = CBash.ReadFIDField(self._CollectionIndex, self._ModName, self._recordID, 8)
        if(retValue): return retValue.contents.value
        return None
    def set_flags(self, nValue):
        CBash.SetFIDFieldUC(self._CollectionIndex, self._ModName, self._recordID, 8, c_ubyte(nValue))
    flags = property(get_flags, set_flags)
    def get_IsPlayable(self):
        return (self.flags & 0x00000001) != 0
    def set_IsPlayable(self, nValue):
        if (nValue == True): self.flags |= 0x00000001
        else: self.flags &= ~0x00000001
    IsPlayable = property(get_IsPlayable, set_IsPlayable)
    attrs = BaseRecord.baseattrs + ['full', 'iconPath', 'flags']

class RACERecord(BaseRecord):
    def CopyAsOverride(self, targetMod):
        FID = CBash.CopyRACERecord(self._CollectionIndex, self._ModName, self._recordID, targetMod._ModName, c_bool(True))
        if(FID): return RACERecord(self._CollectionIndex, targetMod._ModName, FID)
        return None
    def CopyAsNew(self, targetMod):
        FID = CBash.CopyRACERecord(self._CollectionIndex, self._ModName, self._recordID, targetMod._ModName, c_bool(False))
        if(FID): return RACERecord(self._CollectionIndex, targetMod._ModName, FID)
        return None
    class Relation(object):
        def __init__(self, CollectionIndex, ModName, recordID, listIndex):
            self._CollectionIndex = CollectionIndex
            self._ModName = ModName
            self._recordID = recordID
            self._listIndex = listIndex
        def get_faction(self):
            CBash.ReadFIDListField.restype = POINTER(c_uint)
            retValue = CBash.ReadFIDListField(self._CollectionIndex, self._ModName, self._recordID, 9, self._listIndex, 1)
            if(retValue): return retValue.contents.value
            return None
        def set_faction(self, nValue):
            CBash.SetFIDListFieldUI(self._CollectionIndex, self._ModName, self._recordID, 9, self._listIndex, 1, nValue)
        faction = property(get_faction, set_faction)
        def get_mod(self):
            CBash.ReadFIDListField.restype = POINTER(c_int)
            retValue = CBash.ReadFIDListField(self._CollectionIndex, self._ModName, self._recordID, 9, self._listIndex, 2)
            if(retValue): return retValue.contents.value
            return None
        def set_mod(self, nValue):
            CBash.SetFIDListFieldI(self._CollectionIndex, self._ModName, self._recordID, 9, self._listIndex, 2, nValue)
        mod = property(get_mod, set_mod)

    class RaceModel(object):
        def __init__(self, CollectionIndex, ModName, recordID, listIndex):
            self._CollectionIndex = CollectionIndex
            self._ModName = ModName
            self._recordID = recordID
            self._listIndex = listIndex
        def get_modPath(self):
            CBash.ReadFIDField.restype = c_char_p
            return CBash.ReadFIDField(self._CollectionIndex, self._ModName, self._recordID, self._listIndex)
        def set_modPath(self, nValue):
            CBash.SetFIDFieldStr(self._CollectionIndex, self._ModName, self._recordID, self._listIndex, nValue)
        modPath = property(get_modPath, set_modPath)
        def get_modb(self):
            CBash.ReadFIDField.restype = POINTER(c_float)
            retValue = CBash.ReadFIDField(self._CollectionIndex, self._ModName, self._recordID, self._listIndex + 1)
            if(retValue): return retValue.contents.value
            return None
        def set_modb(self, nValue):
            CBash.SetFIDFieldF(self._CollectionIndex, self._ModName, self._recordID, self._listIndex + 1, c_float(nValue))
        modb = property(get_modb, set_modb)
        def get_iconPath(self):
            CBash.ReadFIDField.restype = c_char_p
            return CBash.ReadFIDField(self._CollectionIndex, self._ModName, self._recordID, self._listIndex + 2)
        def set_iconPath(self, nValue):
            CBash.SetFIDFieldStr(self._CollectionIndex, self._ModName, self._recordID, self._listIndex + 2, nValue)
        iconPath = property(get_iconPath, set_iconPath)
        def get_modt_p(self):
            numRecords = CBash.GetFIDFieldArraySize(self._CollectionIndex, self._ModName, self._recordID, self._listIndex + 3)
            if(numRecords > 0):
                cRecords = POINTER(c_ubyte * numRecords)()
                CBash.GetFIDFieldArray(self._CollectionIndex, self._ModName, self._recordID, self._listIndex + 3, byref(cRecords))
                return [cRecords.contents[x] for x in range(0, numRecords)]
            return []
        def set_modt_p(self, nValue):
            length = len(nValue)
            CBash.SetFIDFieldR(self._CollectionIndex, self._ModName, self._recordID, self._listIndex + 3, struct.pack('B' * length, *nValue), length)
        modt_p = property(get_modt_p, set_modt_p)
       
    class Model(object):
        def __init__(self, CollectionIndex, ModName, recordID, listIndex):
            self._CollectionIndex = CollectionIndex
            self._ModName = ModName
            self._recordID = recordID
            self._listIndex = listIndex
        def get_modPath(self):
            CBash.ReadFIDField.restype = c_char_p
            return CBash.ReadFIDField(self._CollectionIndex, self._ModName, self._recordID, self._listIndex)
        def set_modPath(self, nValue):
            CBash.SetFIDFieldStr(self._CollectionIndex, self._ModName, self._recordID, self._listIndex, nValue)
        modPath = property(get_modPath, set_modPath)
        def get_modb(self):
            CBash.ReadFIDField.restype = POINTER(c_float)
            retValue = CBash.ReadFIDField(self._CollectionIndex, self._ModName, self._recordID, self._listIndex + 1)
            if(retValue): return retValue.contents.value
            return None
        def set_modb(self, nValue):
            CBash.SetFIDFieldF(self._CollectionIndex, self._ModName, self._recordID, self._listIndex + 1, c_float(nValue))
        modb = property(get_modb, set_modb)
        def get_modt_p(self):
            numRecords = CBash.GetFIDFieldArraySize(self._CollectionIndex, self._ModName, self._recordID, self._listIndex + 2)
            if(numRecords > 0):
                cRecords = POINTER(c_ubyte * numRecords)()
                CBash.GetFIDFieldArray(self._CollectionIndex, self._ModName, self._recordID, self._listIndex + 2, byref(cRecords))
                return [cRecords.contents[x] for x in range(0, numRecords)]
            return []
        def set_modt_p(self, nValue):
            length = len(nValue)
            CBash.SetFIDFieldR(self._CollectionIndex, self._ModName, self._recordID, self._listIndex + 2, struct.pack('B' * length, *nValue), length)
        modt_p = property(get_modt_p, set_modt_p)    
    def newRelationsElement(self):
        listIndex = CBash.CreateFIDListElement(self._CollectionIndex, self._ModName, self._recordID, 9)
        if(listIndex == -1): return None
        return self.Relation(self._CollectionIndex, self._ModName, self._recordID, listIndex)
    def get_full(self):
        CBash.ReadFIDField.restype = c_char_p
        return CBash.ReadFIDField(self._CollectionIndex, self._ModName, self._recordID, 6)
    def set_full(self, nValue):
        CBash.SetFIDFieldStr(self._CollectionIndex, self._ModName, self._recordID, 6, nValue)
    full = property(get_full, set_full)
    def get_text(self):
        CBash.ReadFIDField.restype = c_char_p
        return CBash.ReadFIDField(self._CollectionIndex, self._ModName, self._recordID, 7)
    def set_text(self, nValue):
        CBash.SetFIDFieldStr(self._CollectionIndex, self._ModName, self._recordID, 7, nValue)
    text = property(get_text, set_text)
    def get_spells(self):
        numRecords = CBash.GetFIDFieldArraySize(self._CollectionIndex, self._ModName, self._recordID, 8)
        if(numRecords > 0):
            cRecords = (POINTER(c_uint) * numRecords)()
            CBash.GetFIDFieldArray(self._CollectionIndex, self._ModName, self._recordID, 8, byref(cRecords))
            return [cRecords[x].contents.value for x in range(0, numRecords)]
        return []
    def set_spells(self, nValue):
        length = len(nValue)
        cRecords = (c_uint * length)(*nValue)
        CBash.SetFIDFieldUIA(self._CollectionIndex, self._ModName, self._recordID, 8, cRecords, length)
    spells = property(get_spells, set_spells)
    def get_relations(self):
        numRecords = CBash.GetFIDListSize(self._CollectionIndex, self._ModName, self._recordID, 9)
        if(numRecords > 0): return [self.Relation(self._CollectionIndex, self._ModName, self._recordID, x) for x in range(0, numRecords)]
        return []
    def set_relations(self, nRelations):
        diffLength = len(nRelations) - len(self.relations)
        nValues = [(relation.faction,relation.mod) for relation in nRelations]
        while(diffLength < 0):
            CBash.DeleteFIDListElement(self._CollectionIndex, self._ModName, self._recordID, 9)
            diffLength += 1
        while(diffLength > 0):
            CBash.CreateFIDListElement(self._CollectionIndex, self._ModName, self._recordID, 9)
            diffLength -= 1
        for oRelation, nValue in zip(self.relations, nValues):
            oRelation.faction, oRelation.mod = nValue
    relations = property(get_relations, set_relations)
    def get_skill1(self):
        CBash.ReadFIDField.restype = POINTER(c_byte)
        retValue = CBash.ReadFIDField(self._CollectionIndex, self._ModName, self._recordID, 10)
        if(retValue): return retValue.contents.value
        return None
    def set_skill1(self, nValue):
        CBash.SetFIDFieldC(self._CollectionIndex, self._ModName, self._recordID, 10, c_byte(nValue))
    skill1 = property(get_skill1, set_skill1)
    def get_skill1Boost(self):
        CBash.ReadFIDField.restype = POINTER(c_byte)
        retValue = CBash.ReadFIDField(self._CollectionIndex, self._ModName, self._recordID, 11)
        if(retValue): return retValue.contents.value
        return None
    def set_skill1Boost(self, nValue):
        CBash.SetFIDFieldC(self._CollectionIndex, self._ModName, self._recordID, 11, c_byte(nValue))
    skill1Boost = property(get_skill1Boost, set_skill1Boost)
    def get_skill2(self):
        CBash.ReadFIDField.restype = POINTER(c_byte)
        retValue = CBash.ReadFIDField(self._CollectionIndex, self._ModName, self._recordID, 12)
        if(retValue): return retValue.contents.value
        return None
    def set_skill2(self, nValue):
        CBash.SetFIDFieldC(self._CollectionIndex, self._ModName, self._recordID, 12, c_byte(nValue))
    skill2 = property(get_skill2, set_skill2)
    def get_skill2Boost(self):
        CBash.ReadFIDField.restype = POINTER(c_byte)
        retValue = CBash.ReadFIDField(self._CollectionIndex, self._ModName, self._recordID, 13)
        if(retValue): return retValue.contents.value
        return None
    def set_skill2Boost(self, nValue):
        CBash.SetFIDFieldC(self._CollectionIndex, self._ModName, self._recordID, 13, c_byte(nValue))
    skill2Boost = property(get_skill2Boost, set_skill2Boost)
    def get_skill3(self):
        CBash.ReadFIDField.restype = POINTER(c_byte)
        retValue = CBash.ReadFIDField(self._CollectionIndex, self._ModName, self._recordID, 14)
        if(retValue): return retValue.contents.value
        return None
    def set_skill3(self, nValue):
        CBash.SetFIDFieldC(self._CollectionIndex, self._ModName, self._recordID, 14, c_byte(nValue))
    skill3 = property(get_skill3, set_skill3)
    def get_skill3Boost(self):
        CBash.ReadFIDField.restype = POINTER(c_byte)
        retValue = CBash.ReadFIDField(self._CollectionIndex, self._ModName, self._recordID, 15)
        if(retValue): return retValue.contents.value
        return None
    def set_skill3Boost(self, nValue):
        CBash.SetFIDFieldC(self._CollectionIndex, self._ModName, self._recordID, 15, c_byte(nValue))
    skill3Boost = property(get_skill3Boost, set_skill3Boost)
    def get_skill4(self):
        CBash.ReadFIDField.restype = POINTER(c_byte)
        retValue = CBash.ReadFIDField(self._CollectionIndex, self._ModName, self._recordID, 16)
        if(retValue): return retValue.contents.value
        return None
    def set_skill4(self, nValue):
        CBash.SetFIDFieldC(self._CollectionIndex, self._ModName, self._recordID, 16, c_byte(nValue))
    skill4 = property(get_skill4, set_skill4)
    def get_skill4Boost(self):
        CBash.ReadFIDField.restype = POINTER(c_byte)
        retValue = CBash.ReadFIDField(self._CollectionIndex, self._ModName, self._recordID, 17)
        if(retValue): return retValue.contents.value
        return None
    def set_skill4Boost(self, nValue):
        CBash.SetFIDFieldC(self._CollectionIndex, self._ModName, self._recordID, 17, c_byte(nValue))
    skill4Boost = property(get_skill4Boost, set_skill4Boost)
    def get_skill5(self):
        CBash.ReadFIDField.restype = POINTER(c_byte)
        retValue = CBash.ReadFIDField(self._CollectionIndex, self._ModName, self._recordID, 18)
        if(retValue): return retValue.contents.value
        return None
    def set_skill5(self, nValue):
        CBash.SetFIDFieldC(self._CollectionIndex, self._ModName, self._recordID, 18, c_byte(nValue))
    skill5 = property(get_skill5, set_skill5)
    def get_skill5Boost(self):
        CBash.ReadFIDField.restype = POINTER(c_byte)
        retValue = CBash.ReadFIDField(self._CollectionIndex, self._ModName, self._recordID, 19)
        if(retValue): return retValue.contents.value
        return None
    def set_skill5Boost(self, nValue):
        CBash.SetFIDFieldC(self._CollectionIndex, self._ModName, self._recordID, 19, c_byte(nValue))
    skill5Boost = property(get_skill5Boost, set_skill5Boost)
    def get_skill6(self):
        CBash.ReadFIDField.restype = POINTER(c_byte)
        retValue = CBash.ReadFIDField(self._CollectionIndex, self._ModName, self._recordID, 20)
        if(retValue): return retValue.contents.value
        return None
    def set_skill6(self, nValue):
        CBash.SetFIDFieldC(self._CollectionIndex, self._ModName, self._recordID, 20, c_byte(nValue))
    skill6 = property(get_skill6, set_skill6)
    def get_skill6Boost(self):
        CBash.ReadFIDField.restype = POINTER(c_byte)
        retValue = CBash.ReadFIDField(self._CollectionIndex, self._ModName, self._recordID, 21)
        if(retValue): return retValue.contents.value
        return None
    def set_skill6Boost(self, nValue):
        CBash.SetFIDFieldC(self._CollectionIndex, self._ModName, self._recordID, 21, c_byte(nValue))
    skill6Boost = property(get_skill6Boost, set_skill6Boost)
    def get_skill7(self):
        CBash.ReadFIDField.restype = POINTER(c_byte)
        retValue = CBash.ReadFIDField(self._CollectionIndex, self._ModName, self._recordID, 22)
        if(retValue): return retValue.contents.value
        return None
    def set_skill7(self, nValue):
        CBash.SetFIDFieldC(self._CollectionIndex, self._ModName, self._recordID, 22, c_byte(nValue))
    skill7 = property(get_skill7, set_skill7)
    def get_skill7Boost(self):
        CBash.ReadFIDField.restype = POINTER(c_byte)
        retValue = CBash.ReadFIDField(self._CollectionIndex, self._ModName, self._recordID, 23)
        if(retValue): return retValue.contents.value
        return None
    def set_skill7Boost(self, nValue):
        CBash.SetFIDFieldC(self._CollectionIndex, self._ModName, self._recordID, 23, c_byte(nValue))
    skill7Boost = property(get_skill7Boost, set_skill7Boost)
    def get_unused1(self):
        numRecords = CBash.GetFIDFieldArraySize(self._CollectionIndex, self._ModName, self._recordID, 24)
        if(numRecords > 0):
            cRecords = POINTER(c_ubyte * numRecords)()
            CBash.GetFIDFieldArray(self._CollectionIndex, self._ModName, self._recordID, 24, byref(cRecords))
            return [cRecords.contents[x] for x in range(0, numRecords)]
        return []
    def set_unused1(self, nValue):
        CBash.SetFIDFieldR(self._CollectionIndex, self._ModName, self._recordID, 24, struct.pack('2B', *nValue), 2)
    unused1 = property(get_unused1, set_unused1)
    def get_maleHeight(self):
        CBash.ReadFIDField.restype = POINTER(c_float)
        retValue = CBash.ReadFIDField(self._CollectionIndex, self._ModName, self._recordID, 25)
        if(retValue): return retValue.contents.value
        return None
    def set_maleHeight(self, nValue):
        CBash.SetFIDFieldF(self._CollectionIndex, self._ModName, self._recordID, 25, c_float(nValue))
    maleHeight = property(get_maleHeight, set_maleHeight)
    def get_femaleHeight(self):
        CBash.ReadFIDField.restype = POINTER(c_float)
        retValue = CBash.ReadFIDField(self._CollectionIndex, self._ModName, self._recordID, 26)
        if(retValue): return retValue.contents.value
        return None
    def set_femaleHeight(self, nValue):
        CBash.SetFIDFieldF(self._CollectionIndex, self._ModName, self._recordID, 26, c_float(nValue))   
    femaleHeight = property(get_femaleHeight, set_femaleHeight)
    def get_maleWeight(self):
        CBash.ReadFIDField.restype = POINTER(c_float)
        retValue = CBash.ReadFIDField(self._CollectionIndex, self._ModName, self._recordID, 27)
        if(retValue): return retValue.contents.value
        return None
    def set_maleWeight(self, nValue):
        CBash.SetFIDFieldF(self._CollectionIndex, self._ModName, self._recordID, 27, c_float(nValue))   
    maleWeight = property(get_maleWeight, set_maleWeight)
    def get_femaleWeight(self):
        CBash.ReadFIDField.restype = POINTER(c_float)
        retValue = CBash.ReadFIDField(self._CollectionIndex, self._ModName, self._recordID, 28)
        if(retValue): return retValue.contents.value
        return None
    def set_femaleWeight(self, nValue):
        CBash.SetFIDFieldF(self._CollectionIndex, self._ModName, self._recordID, 28, c_float(nValue))          
    femaleWeight = property(get_femaleWeight, set_femaleWeight)
    def get_flags(self):
        CBash.ReadFIDField.restype = POINTER(c_uint)
        retValue = CBash.ReadFIDField(self._CollectionIndex, self._ModName, self._recordID, 29)
        if(retValue): return retValue.contents.value
        return None
    def set_flags(self, nValue):
        CBash.SetFIDFieldUI(self._CollectionIndex, self._ModName, self._recordID, 29, c_uint(nValue))
    flags = property(get_flags, set_flags)
    def get_maleVoice(self):
        CBash.ReadFIDField.restype = POINTER(c_uint)
        retValue = CBash.ReadFIDField(self._CollectionIndex, self._ModName, self._recordID, 30)
        if(retValue): return retValue.contents.value
        return None
    def set_maleVoice(self, nValue):
        CBash.SetFIDFieldUI(self._CollectionIndex, self._ModName, self._recordID, 30, c_uint(nValue))
    maleVoice = property(get_maleVoice, set_maleVoice)
    def get_femaleVoice(self):
        CBash.ReadFIDField.restype = POINTER(c_uint)
        retValue = CBash.ReadFIDField(self._CollectionIndex, self._ModName, self._recordID, 31)
        if(retValue): return retValue.contents.value
        return None
    def set_femaleVoice(self, nValue):
        CBash.SetFIDFieldUI(self._CollectionIndex, self._ModName, self._recordID, 31, c_uint(nValue))
    femaleVoice = property(get_femaleVoice, set_femaleVoice)
    def get_defaultHairMale(self):
        CBash.ReadFIDField.restype = POINTER(c_uint)
        retValue = CBash.ReadFIDField(self._CollectionIndex, self._ModName, self._recordID, 32)
        if(retValue): return retValue.contents.value
        return None
    def set_defaultHairMale(self, nValue):
        CBash.SetFIDFieldUI(self._CollectionIndex, self._ModName, self._recordID, 32, c_uint(nValue))
    defaultHairMale = property(get_defaultHairMale, set_defaultHairMale)
    def get_defaultHairFemale(self):
        CBash.ReadFIDField.restype = POINTER(c_uint)
        retValue = CBash.ReadFIDField(self._CollectionIndex, self._ModName, self._recordID, 33)
        if(retValue): return retValue.contents.value
        return None
    def set_defaultHairFemale(self, nValue):
        CBash.SetFIDFieldUI(self._CollectionIndex, self._ModName, self._recordID, 33, c_uint(nValue))
    defaultHairFemale = property(get_defaultHairFemale, set_defaultHairFemale)
    def get_defaultHairColor(self):
        CBash.ReadFIDField.restype = POINTER(c_ubyte)
        retValue = CBash.ReadFIDField(self._CollectionIndex, self._ModName, self._recordID, 34)
        if(retValue): return retValue.contents.value
        return None
    def set_defaultHairColor(self, nValue):
        CBash.SetFIDFieldUC(self._CollectionIndex, self._ModName, self._recordID, 34, c_ubyte(nValue))
    defaultHairColor = property(get_defaultHairColor, set_defaultHairColor)
    def get_mainClamp(self):
        CBash.ReadFIDField.restype = POINTER(c_float)
        retValue = CBash.ReadFIDField(self._CollectionIndex, self._ModName, self._recordID, 35)
        if(retValue): return retValue.contents.value
        return None
    def set_mainClamp(self, nValue):
        CBash.SetFIDFieldF(self._CollectionIndex, self._ModName, self._recordID, 35, c_float(nValue))
    mainClamp = property(get_mainClamp, set_mainClamp)
    def get_faceClamp(self):
        CBash.ReadFIDField.restype = POINTER(c_float)
        retValue = CBash.ReadFIDField(self._CollectionIndex, self._ModName, self._recordID, 36)
        if(retValue): return retValue.contents.value
        return None
    def set_faceClamp(self, nValue):
        CBash.SetFIDFieldF(self._CollectionIndex, self._ModName, self._recordID, 36, c_float(nValue))
    faceClamp = property(get_faceClamp, set_faceClamp)
    def get_maleStrength(self):
        CBash.ReadFIDField.restype = POINTER(c_ubyte)
        retValue = CBash.ReadFIDField(self._CollectionIndex, self._ModName, self._recordID, 37)
        if(retValue): return retValue.contents.value
        return None
    def set_maleStrength(self, nValue):
        CBash.SetFIDFieldUC(self._CollectionIndex, self._ModName, self._recordID, 37, c_ubyte(nValue))
    maleStrength = property(get_maleStrength, set_maleStrength)
    def get_maleIntelligence(self):
        CBash.ReadFIDField.restype = POINTER(c_ubyte)
        retValue = CBash.ReadFIDField(self._CollectionIndex, self._ModName, self._recordID, 38)
        if(retValue): return retValue.contents.value
        return None
    def set_maleIntelligence(self, nValue):
        CBash.SetFIDFieldUC(self._CollectionIndex, self._ModName, self._recordID, 38, c_ubyte(nValue))
    maleIntelligence = property(get_maleIntelligence, set_maleIntelligence)
    def get_maleWillpower(self):
        CBash.ReadFIDField.restype = POINTER(c_ubyte)
        retValue = CBash.ReadFIDField(self._CollectionIndex, self._ModName, self._recordID, 39)
        if(retValue): return retValue.contents.value
        return None
    def set_maleWillpower(self, nValue):
        CBash.SetFIDFieldUC(self._CollectionIndex, self._ModName, self._recordID, 39, c_ubyte(nValue))
    maleWillpower = property(get_maleWillpower, set_maleWillpower)
    def get_maleAgility(self):
        CBash.ReadFIDField.restype = POINTER(c_ubyte)
        retValue = CBash.ReadFIDField(self._CollectionIndex, self._ModName, self._recordID, 40)
        if(retValue): return retValue.contents.value
        return None
    def set_maleAgility(self, nValue):
        CBash.SetFIDFieldUC(self._CollectionIndex, self._ModName, self._recordID, 40, c_ubyte(nValue))
    maleAgility = property(get_maleAgility, set_maleAgility)
    def get_maleSpeed(self):
        CBash.ReadFIDField.restype = POINTER(c_ubyte)
        retValue = CBash.ReadFIDField(self._CollectionIndex, self._ModName, self._recordID, 41)
        if(retValue): return retValue.contents.value
        return None
    def set_maleSpeed(self, nValue):
        CBash.SetFIDFieldUC(self._CollectionIndex, self._ModName, self._recordID, 41, c_ubyte(nValue))
    maleSpeed = property(get_maleSpeed, set_maleSpeed)
    def get_maleEndurance(self):
        CBash.ReadFIDField.restype = POINTER(c_ubyte)
        retValue = CBash.ReadFIDField(self._CollectionIndex, self._ModName, self._recordID, 42)
        if(retValue): return retValue.contents.value
        return None
    def set_maleEndurance(self, nValue):
        CBash.SetFIDFieldUC(self._CollectionIndex, self._ModName, self._recordID, 42, c_ubyte(nValue))
    maleEndurance = property(get_maleEndurance, set_maleEndurance)
    def get_malePersonality(self):
        CBash.ReadFIDField.restype = POINTER(c_ubyte)
        retValue = CBash.ReadFIDField(self._CollectionIndex, self._ModName, self._recordID, 43)
        if(retValue): return retValue.contents.value
        return None
    def set_malePersonality(self, nValue):
        CBash.SetFIDFieldUC(self._CollectionIndex, self._ModName, self._recordID, 43, c_ubyte(nValue))
    malePersonality = property(get_malePersonality, set_malePersonality)
    def get_maleLuck(self):
        CBash.ReadFIDField.restype = POINTER(c_ubyte)
        retValue = CBash.ReadFIDField(self._CollectionIndex, self._ModName, self._recordID, 44)
        if(retValue): return retValue.contents.value
        return None
    def set_maleLuck(self, nValue):
        CBash.SetFIDFieldUC(self._CollectionIndex, self._ModName, self._recordID, 44, c_ubyte(nValue))
    maleLuck = property(get_maleLuck, set_maleLuck)
    def get_femaleStrength(self):
        CBash.ReadFIDField.restype = POINTER(c_ubyte)
        retValue = CBash.ReadFIDField(self._CollectionIndex, self._ModName, self._recordID, 45)
        if(retValue): return retValue.contents.value
        return None
    def set_femaleStrength(self, nValue):
        CBash.SetFIDFieldUC(self._CollectionIndex, self._ModName, self._recordID, 45, c_ubyte(nValue))
    femaleStrength = property(get_femaleStrength, set_femaleStrength)
    def get_femaleIntelligence(self):
        CBash.ReadFIDField.restype = POINTER(c_ubyte)
        retValue = CBash.ReadFIDField(self._CollectionIndex, self._ModName, self._recordID, 46)
        if(retValue): return retValue.contents.value
        return None
    def set_femaleIntelligence(self, nValue):
        CBash.SetFIDFieldUC(self._CollectionIndex, self._ModName, self._recordID, 46, c_ubyte(nValue))
    femaleIntelligence = property(get_femaleIntelligence, set_femaleIntelligence)
    def get_femaleWillpower(self):
        CBash.ReadFIDField.restype = POINTER(c_ubyte)
        retValue = CBash.ReadFIDField(self._CollectionIndex, self._ModName, self._recordID, 47)
        if(retValue): return retValue.contents.value
        return None
    def set_femaleWillpower(self, nValue):
        CBash.SetFIDFieldUC(self._CollectionIndex, self._ModName, self._recordID, 47, c_ubyte(nValue))
    femaleWillpower = property(get_femaleWillpower, set_femaleWillpower)
    def get_femaleAgility(self):
        CBash.ReadFIDField.restype = POINTER(c_ubyte)
        retValue = CBash.ReadFIDField(self._CollectionIndex, self._ModName, self._recordID, 48)
        if(retValue): return retValue.contents.value
        return None
    def set_femaleAgility(self, nValue):
        CBash.SetFIDFieldUC(self._CollectionIndex, self._ModName, self._recordID, 48, c_ubyte(nValue))
    femaleAgility = property(get_femaleAgility, set_femaleAgility)
    def get_femaleSpeed(self):
        CBash.ReadFIDField.restype = POINTER(c_ubyte)
        retValue = CBash.ReadFIDField(self._CollectionIndex, self._ModName, self._recordID, 49)
        if(retValue): return retValue.contents.value
        return None
    def set_femaleSpeed(self, nValue):
        CBash.SetFIDFieldUC(self._CollectionIndex, self._ModName, self._recordID, 49, c_ubyte(nValue))
    femaleSpeed = property(get_femaleSpeed, set_femaleSpeed)
    def get_femaleEndurance(self):
        CBash.ReadFIDField.restype = POINTER(c_ubyte)
        retValue = CBash.ReadFIDField(self._CollectionIndex, self._ModName, self._recordID, 50)
        if(retValue): return retValue.contents.value
        return None
    def set_femaleEndurance(self, nValue):
        CBash.SetFIDFieldUC(self._CollectionIndex, self._ModName, self._recordID, 50, c_ubyte(nValue))
    femaleEndurance = property(get_femaleEndurance, set_femaleEndurance)
    def get_femalePersonality(self):
        CBash.ReadFIDField.restype = POINTER(c_ubyte)
        retValue = CBash.ReadFIDField(self._CollectionIndex, self._ModName, self._recordID, 51)
        if(retValue): return retValue.contents.value
        return None
    def set_femalePersonality(self, nValue):
        CBash.SetFIDFieldUC(self._CollectionIndex, self._ModName, self._recordID, 51, c_ubyte(nValue))
    femalePersonality = property(get_femalePersonality, set_femalePersonality)
    def get_femaleLuck(self):
        CBash.ReadFIDField.restype = POINTER(c_ubyte)
        retValue = CBash.ReadFIDField(self._CollectionIndex, self._ModName, self._recordID, 52)
        if(retValue): return retValue.contents.value
        return None
    def set_femaleLuck(self, nValue):
        CBash.SetFIDFieldUC(self._CollectionIndex, self._ModName, self._recordID, 52, c_ubyte(nValue))
    femaleLuck = property(get_femaleLuck, set_femaleLuck)
    def get_head(self):
        return self.RaceModel(self._CollectionIndex, self._ModName, self._recordID, 53)
    def set_head(self, nValue):
        if not isinstance(nValue, self.RaceModel): return
        thisModel = self.head
        thisModel.modPath = nValue.modPath
        thisModel.modb = nValue.modb
        thisModel.iconPath = nValue.iconPath
        thisModel.modt_p = nValue.modt_p
    head = property(get_head, set_head)
    def get_maleEars(self):
        return self.RaceModel(self._CollectionIndex, self._ModName, self._recordID, 57)
    def set_maleEars(self, nValue):
        if not isinstance(nValue, self.RaceModel): return
        thisModel = self.maleEars
        thisModel.modPath = nValue.modPath
        thisModel.modb = nValue.modb
        thisModel.iconPath = nValue.iconPath
        thisModel.modt_p = nValue.modt_p
    maleEars = property(get_maleEars, set_maleEars)
    def get_femaleEars(self):
        return self.RaceModel(self._CollectionIndex, self._ModName, self._recordID, 61)
    def set_femaleEars(self, nValue):
        if not isinstance(nValue, self.RaceModel): return
        thisModel = self.femaleEars
        thisModel.modPath = nValue.modPath
        thisModel.modb = nValue.modb
        thisModel.iconPath = nValue.iconPath
        thisModel.modt_p = nValue.modt_p
    femaleEars = property(get_femaleEars, set_femaleEars)
    def get_mouth(self):
        return self.RaceModel(self._CollectionIndex, self._ModName, self._recordID, 65)
    def set_mouth(self, nValue):
        if not isinstance(nValue, self.RaceModel): return
        thisModel = self.mouth
        thisModel.modPath = nValue.modPath
        thisModel.modb = nValue.modb
        thisModel.iconPath = nValue.iconPath
        thisModel.modt_p = nValue.modt_p
    mouth = property(get_mouth, set_mouth)
    def get_teethLower(self):
        return self.RaceModel(self._CollectionIndex, self._ModName, self._recordID, 69)
    def set_teethLower(self, nValue):
        if not isinstance(nValue, self.RaceModel): return
        thisModel = self.teethLower
        thisModel.modPath = nValue.modPath
        thisModel.modb = nValue.modb
        thisModel.iconPath = nValue.iconPath
        thisModel.modt_p = nValue.modt_p
    teethLower = property(get_teethLower, set_teethLower)
    def get_teethUpper(self):
        return self.RaceModel(self._CollectionIndex, self._ModName, self._recordID, 73)
    def set_teethUpper(self, nValue):
        if not isinstance(nValue, self.RaceModel): return
        thisModel = self.teethUpper
        thisModel.modPath = nValue.modPath
        thisModel.modb = nValue.modb
        thisModel.iconPath = nValue.iconPath
        thisModel.modt_p = nValue.modt_p
    teethUpper = property(get_teethUpper, set_teethUpper)
    def get_tongue(self):
        return self.RaceModel(self._CollectionIndex, self._ModName, self._recordID, 77)
    def set_tongue(self, nValue):
        if not isinstance(nValue, self.RaceModel): return
        thisModel = self.tongue
        thisModel.modPath = nValue.modPath
        thisModel.modb = nValue.modb
        thisModel.iconPath = nValue.iconPath
        thisModel.modt_p = nValue.modt_p
    tongue = property(get_tongue, set_tongue)
    def get_leftEye(self):
        return self.RaceModel(self._CollectionIndex, self._ModName, self._recordID, 81)
    def set_leftEye(self, nValue):
        if not isinstance(nValue, self.RaceModel): return
        thisModel = self.leftEye
        thisModel.modPath = nValue.modPath
        thisModel.modb = nValue.modb
        thisModel.iconPath = nValue.iconPath
        thisModel.modt_p = nValue.modt_p
    leftEye = property(get_leftEye, set_leftEye)
    def get_rightEye(self):
        return self.RaceModel(self._CollectionIndex, self._ModName, self._recordID, 85)
    def set_rightEye(self, nValue):
        if not isinstance(nValue, self.RaceModel): return
        thisModel = self.rightEye
        thisModel.modPath = nValue.modPath
        thisModel.modb = nValue.modb
        thisModel.iconPath = nValue.iconPath
        thisModel.modt_p = nValue.modt_p
    rightEye = property(get_rightEye, set_rightEye)
    def get_maleTailModel(self):
        return self.Model(self._CollectionIndex, self._ModName, self._recordID, 89)
    def set_maleTailModel(self, nValue):
        if not isinstance(nValue, self.Model): return
        thisModel = self.maleTailModel
        thisModel.modPath = nValue.modPath
        thisModel.modb = nValue.modb
        thisModel.modt_p = nValue.modt_p
    maleTailModel = property(get_maleTailModel, set_maleTailModel)
    def get_maleUpperBodyPath(self):
        CBash.ReadFIDField.restype = c_char_p
        return CBash.ReadFIDField(self._CollectionIndex, self._ModName, self._recordID, 92)
    def set_maleUpperBodyPath(self, nValue):
        CBash.SetFIDFieldStr(self._CollectionIndex, self._ModName, self._recordID, 92, nValue)
    maleUpperBodyPath = property(get_maleUpperBodyPath, set_maleUpperBodyPath)
    def get_maleLowerBodyPath(self):
        CBash.ReadFIDField.restype = c_char_p
        return CBash.ReadFIDField(self._CollectionIndex, self._ModName, self._recordID, 93)
    def set_maleLowerBodyPath(self, nValue):
        CBash.SetFIDFieldStr(self._CollectionIndex, self._ModName, self._recordID, 93, nValue)
    maleLowerBodyPath = property(get_maleLowerBodyPath, set_maleLowerBodyPath)
    def get_maleHandPath(self):
        CBash.ReadFIDField.restype = c_char_p
        return CBash.ReadFIDField(self._CollectionIndex, self._ModName, self._recordID, 94)
    def set_maleHandPath(self, nValue):
        CBash.SetFIDFieldStr(self._CollectionIndex, self._ModName, self._recordID, 94, nValue)
    maleHandPath = property(get_maleHandPath, set_maleHandPath)
    def get_maleFootPath(self):
        CBash.ReadFIDField.restype = c_char_p
        return CBash.ReadFIDField(self._CollectionIndex, self._ModName, self._recordID, 95)
    def set_maleFootPath(self, nValue):
        CBash.SetFIDFieldStr(self._CollectionIndex, self._ModName, self._recordID, 95, nValue)
    maleFootPath = property(get_maleFootPath, set_maleFootPath)
    def get_maleTailPath(self):
        CBash.ReadFIDField.restype = c_char_p
        return CBash.ReadFIDField(self._CollectionIndex, self._ModName, self._recordID, 96)
    def set_maleTailPath(self, nValue):
        CBash.SetFIDFieldStr(self._CollectionIndex, self._ModName, self._recordID, 96, nValue)
    maleTailPath = property(get_maleTailPath, set_maleTailPath)
    def get_femaleTailModel(self):
        return self.Model(self._CollectionIndex, self._ModName, self._recordID, 97)
    def set_femaleTailModel(self, nValue):
        if not isinstance(nValue, self.Model): return
        thisModel = self.femaleTailModel
        thisModel.modPath = nValue.modPath
        thisModel.modb = nValue.modb
        thisModel.modt_p = nValue.modt_p
    femaleTailModel = property(get_femaleTailModel, set_femaleTailModel)
    def get_femaleUpperBodyPath(self):
        CBash.ReadFIDField.restype = c_char_p
        return CBash.ReadFIDField(self._CollectionIndex, self._ModName, self._recordID, 100)
    def set_femaleUpperBodyPath(self, nValue):
        CBash.SetFIDFieldStr(self._CollectionIndex, self._ModName, self._recordID, 100, nValue)
    femaleUpperBodyPath = property(get_femaleUpperBodyPath, set_femaleUpperBodyPath)
    def get_femaleLowerBodyPath(self):
        CBash.ReadFIDField.restype = c_char_p
        return CBash.ReadFIDField(self._CollectionIndex, self._ModName, self._recordID, 101)
    def set_femaleLowerBodyPath(self, nValue):
        CBash.SetFIDFieldStr(self._CollectionIndex, self._ModName, self._recordID, 101, nValue)
    femaleLowerBodyPath = property(get_femaleLowerBodyPath, set_femaleLowerBodyPath)
    def get_femaleHandPath(self):
        CBash.ReadFIDField.restype = c_char_p
        return CBash.ReadFIDField(self._CollectionIndex, self._ModName, self._recordID, 102)
    def set_femaleHandPath(self, nValue):
        CBash.SetFIDFieldStr(self._CollectionIndex, self._ModName, self._recordID, 102, nValue)
    femaleHandPath = property(get_femaleHandPath, set_femaleHandPath)
    def get_femaleFootPath(self):
        CBash.ReadFIDField.restype = c_char_p
        return CBash.ReadFIDField(self._CollectionIndex, self._ModName, self._recordID, 103)
    def set_femaleFootPath(self, nValue):
        CBash.SetFIDFieldStr(self._CollectionIndex, self._ModName, self._recordID, 103, nValue)
    femaleFootPath = property(get_femaleFootPath, set_femaleFootPath)
    def get_femaleTailPath(self):
        CBash.ReadFIDField.restype = c_char_p
        return CBash.ReadFIDField(self._CollectionIndex, self._ModName, self._recordID, 104)
    def set_femaleTailPath(self, nValue):
        CBash.SetFIDFieldStr(self._CollectionIndex, self._ModName, self._recordID, 104, nValue)
    femaleTailPath = property(get_femaleTailPath, set_femaleTailPath)
    def get_hairs(self):
        numRecords = CBash.GetFIDFieldArraySize(self._CollectionIndex, self._ModName, self._recordID, 105)
        if(numRecords > 0):
            cRecords = (POINTER(c_uint) * numRecords)()
            CBash.GetFIDFieldArray(self._CollectionIndex, self._ModName, self._recordID, 105, byref(cRecords))
            return [cRecords[x].contents.value for x in range(0, numRecords)]
        return []
    def set_hairs(self, nValue):
        length = len(nValue)
        cRecords = (c_uint * length)(*nValue)
        CBash.SetFIDFieldUIA(self._CollectionIndex, self._ModName, self._recordID, 105, cRecords, length)
    hairs = property(get_hairs, set_hairs)
    def get_eyes(self):
        numRecords = CBash.GetFIDFieldArraySize(self._CollectionIndex, self._ModName, self._recordID, 106)
        if(numRecords > 0):
            cRecords = (POINTER(c_uint) * numRecords)()
            CBash.GetFIDFieldArray(self._CollectionIndex, self._ModName, self._recordID, 106, byref(cRecords))
            return [cRecords[x].contents.value for x in range(0, numRecords)]
        return []
    def set_eyes(self, nValue):
        length = len(nValue)
        cRecords = (c_uint * length)(*nValue)
        CBash.SetFIDFieldUIA(self._CollectionIndex, self._ModName, self._recordID, 106, cRecords, length)
    eyes = property(get_eyes, set_eyes)
    def get_fggs_p(self):
        numRecords = CBash.GetFIDFieldArraySize(self._CollectionIndex, self._ModName, self._recordID, 107)
        if(numRecords > 0):
            cRecords = POINTER(c_ubyte * numRecords)()
            CBash.GetFIDFieldArray(self._CollectionIndex, self._ModName, self._recordID, 107, byref(cRecords))
            return [cRecords.contents[x] for x in range(0, numRecords)]
        return []
    def set_fggs_p(self, nValue):
        length = len(nValue)
        CBash.SetFIDFieldR(self._CollectionIndex, self._ModName, self._recordID, 107, struct.pack('B' * length, *nValue), length)
    fggs_p = property(get_fggs_p, set_fggs_p)
    def get_fgga_p(self):
        numRecords = CBash.GetFIDFieldArraySize(self._CollectionIndex, self._ModName, self._recordID, 108)
        if(numRecords > 0):
            cRecords = POINTER(c_ubyte * numRecords)()
            CBash.GetFIDFieldArray(self._CollectionIndex, self._ModName, self._recordID, 108, byref(cRecords))
            return [cRecords.contents[x] for x in range(0, numRecords)]
        return []
    def set_fgga_p(self, nValue):
        length = len(nValue)
        CBash.SetFIDFieldR(self._CollectionIndex, self._ModName, self._recordID, 108, struct.pack('B' * length, *nValue), length)
    fgga_p = property(get_fgga_p, set_fgga_p)
    def get_fgts_p(self):
        numRecords = CBash.GetFIDFieldArraySize(self._CollectionIndex, self._ModName, self._recordID, 109)
        if(numRecords > 0):
            cRecords = POINTER(c_ubyte * numRecords)()
            CBash.GetFIDFieldArray(self._CollectionIndex, self._ModName, self._recordID, 109, byref(cRecords))
            return [cRecords.contents[x] for x in range(0, numRecords)]
        return []
    def set_fgts_p(self, nValue):
        length = len(nValue)
        CBash.SetFIDFieldR(self._CollectionIndex, self._ModName, self._recordID, 109, struct.pack('B' * length, *nValue), length)
    fgts_p = property(get_fgts_p, set_fgts_p)
    def get_snam(self):
        numRecords = CBash.GetFIDFieldArraySize(self._CollectionIndex, self._ModName, self._recordID, 110)
        if(numRecords > 0):
            cRecords = POINTER(c_ubyte * numRecords)()
            CBash.GetFIDFieldArray(self._CollectionIndex, self._ModName, self._recordID, 110, byref(cRecords))
            return [cRecords.contents[x] for x in range(0, numRecords)]
        return []
    def set_snam(self, nValue):
        length = len(nValue)
        CBash.SetFIDFieldR(self._CollectionIndex, self._ModName, self._recordID, 110, struct.pack('B' * length, *nValue), length)
    snam = property(get_snam, set_snam)
    def get_IsPlayable(self):
        return (self.flags & 0x00000001) != 0
    def set_IsPlayable(self, nValue):
        if (nValue == True): self.flags |= 0x00000001
        else: self.flags &= ~0x00000001
    IsPlayable = property(get_IsPlayable, set_IsPlayable)
    attrs = BaseRecord.baseattrs + ['full', 'text', 'spells', 'relations', 
                         'skill1', 'skill1Boost', 'skill2', 'skill2Boost',
                         'skill3', 'skill3Boost', 'skill4', 'skill4Boost',
                         'skill5', 'skill5Boost', 'skill6', 'skill6Boost',
                         'skill7', 'skill7Boost', 'maleHeight', 'femaleHeight',
                         'maleWeight', 'femaleWeight', 'flags', 'maleVoice',
                         'femaleVoice', 'defaultHairMale', 'defaultHairFemale',
                         'defaultHairColor', 'mainClamp', 'faceClamp', 'maleStrength',
                         'maleIntelligence', 'maleAgility', 'maleSpeed',
                         'maleEndurance', 'malePersonality', 'maleLuck',
                         'femaleStrength', 'femaleIntelligence', 'femaleWillpower',
                         'femaleAgility', 'femaleSpeed', 'femaleEndurance',
                         'femalePersonality', 'femaleLuck', 'head', 'maleEars',
                         'femaleEars', 'mouth', 'teethLower', 'teethUpper',
                         'tongue', 'leftEye', 'rightEye', 'maleTailModel',
                         'maleUpperBodyPath', 'maleLowerBodyPath', 'maleHandPath',
                         'maleFootPath', 'maleTailPath', 'femaleTailModel',
                         'femaleUpperBodyPath', 'femaleLowerBodyPath',
                         'femaleHandPath', 'femaleFootPath', 'femaleTailPath',
                         'hairs', 'eyes', 'fggs_p', 'fgga_p', 'fgts_p', 'snam']

class SOUNRecord(BaseRecord):
    def CopyAsOverride(self, targetMod):
        FID = CBash.CopySOUNRecord(self._CollectionIndex, self._ModName, self._recordID, targetMod._ModName, c_bool(True))
        if(FID): return SOUNRecord(self._CollectionIndex, targetMod._ModName, FID)
        return None
    def CopyAsNew(self, targetMod):
        FID = CBash.CopySOUNRecord(self._CollectionIndex, self._ModName, self._recordID, targetMod._ModName, c_bool(False))
        if(FID): return SOUNRecord(self._CollectionIndex, targetMod._ModName, FID)
        return None
    def get_soundFile(self):
        CBash.ReadFIDField.restype = c_char_p
        return CBash.ReadFIDField(self._CollectionIndex, self._ModName, self._recordID, 6)
    def set_soundFile(self, nValue):
        CBash.SetFIDFieldStr(self._CollectionIndex, self._ModName, self._recordID, 6, nValue)
    soundFile = property(get_soundFile, set_soundFile)
    def get_minDistance(self):
        CBash.ReadFIDField.restype = POINTER(c_ubyte)
        retValue = CBash.ReadFIDField(self._CollectionIndex, self._ModName, self._recordID, 7)
        if(retValue): return retValue.contents.value
        return None
    def set_minDistance(self, nValue):
        CBash.SetFIDFieldUC(self._CollectionIndex, self._ModName, self._recordID, 7, c_ubyte(nValue))
    minDistance = property(get_minDistance, set_minDistance)
    def get_maxDistance(self):
        CBash.ReadFIDField.restype = POINTER(c_ubyte)
        retValue = CBash.ReadFIDField(self._CollectionIndex, self._ModName, self._recordID, 8)
        if(retValue): return retValue.contents.value
        return None
    def set_maxDistance(self, nValue):
        CBash.SetFIDFieldUC(self._CollectionIndex, self._ModName, self._recordID, 8, c_ubyte(nValue))        
    maxDistance = property(get_maxDistance, set_maxDistance)
    def get_freqAdjustment(self):
        CBash.ReadFIDField.restype = POINTER(c_byte)
        retValue = CBash.ReadFIDField(self._CollectionIndex, self._ModName, self._recordID, 9)
        if(retValue): return retValue.contents.value
        return None
    def set_freqAdjustment(self, nValue):
        CBash.SetFIDFieldC(self._CollectionIndex, self._ModName, self._recordID, 9, c_byte(nValue))        
    freqAdjustment = property(get_freqAdjustment, set_freqAdjustment)
    def get_unused1(self):
        CBash.ReadFIDField.restype = POINTER(c_ubyte)
        retValue = CBash.ReadFIDField(self._CollectionIndex, self._ModName, self._recordID, 10)
        if(retValue): return retValue.contents.value
        return None
    def set_unused1(self, nValue):
        CBash.SetFIDFieldUC(self._CollectionIndex, self._ModName, self._recordID, 10, c_ubyte(nValue))        
    unused1 = property(get_unused1, set_unused1)
    def get_flags(self):
        CBash.ReadFIDField.restype = POINTER(c_ushort)
        retValue = CBash.ReadFIDField(self._CollectionIndex, self._ModName, self._recordID, 11)
        if(retValue): return retValue.contents.value
        return None
    def set_flags(self, nValue):
        CBash.SetFIDFieldUS(self._CollectionIndex, self._ModName, self._recordID, 11, c_ushort(nValue))
    flags = property(get_flags, set_flags)
    def get_unused2(self):
        numRecords = CBash.GetFIDFieldArraySize(self._CollectionIndex, self._ModName, self._recordID, 12)
        if(numRecords > 0):
            cRecords = POINTER(c_ubyte * numRecords)()
            CBash.GetFIDFieldArray(self._CollectionIndex, self._ModName, self._recordID, 12, byref(cRecords))
            return [cRecords.contents[x] for x in range(0, numRecords)]
        return []
    def set_unused2(self, nValue):
        CBash.SetFIDFieldR(self._CollectionIndex, self._ModName, self._recordID, 12, struct.pack('2B', *nValue), 2)
    unused2 = property(get_unused2, set_unused2)
    def get_staticAtten(self):
        CBash.ReadFIDField.restype = POINTER(c_short)
        retValue = CBash.ReadFIDField(self._CollectionIndex, self._ModName, self._recordID, 13)
        if(retValue): return retValue.contents.value
        return None
    def set_staticAtten(self, nValue):
        CBash.SetFIDFieldS(self._CollectionIndex, self._ModName, self._recordID, 13, c_short(nValue))
    staticAtten = property(get_staticAtten, set_staticAtten)
    def get_stopTime(self):
        CBash.ReadFIDField.restype = POINTER(c_ubyte)
        retValue = CBash.ReadFIDField(self._CollectionIndex, self._ModName, self._recordID, 14)
        if(retValue): return retValue.contents.value
        return None
    def set_stopTime(self, nValue):
        CBash.SetFIDFieldUC(self._CollectionIndex, self._ModName, self._recordID, 14, c_ubyte(nValue))
    stopTime = property(get_stopTime, set_stopTime)
    def get_startTime(self):
        CBash.ReadFIDField.restype = POINTER(c_ubyte)
        retValue = CBash.ReadFIDField(self._CollectionIndex, self._ModName, self._recordID, 15)
        if(retValue): return retValue.contents.value
        return None
    def set_startTime(self, nValue):
        CBash.SetFIDFieldUC(self._CollectionIndex, self._ModName, self._recordID, 15, c_ubyte(nValue))
    startTime = property(get_startTime, set_startTime)
    def get_IsRandomFrequencyShift(self):
        return (self.flags & 0x00000001) != 0
    def set_IsRandomFrequencyShift(self, nValue):
        if (nValue == True): self.flags |= 0x00000001
        else: self.flags &= ~0x00000001
    IsRandomFrequencyShift = property(get_IsRandomFrequencyShift, set_IsRandomFrequencyShift)
    def get_IsPlayAtRandom(self):
        return (self.flags & 0x00000002) != 0
    def set_IsPlayAtRandom(self, nValue):
        if (nValue == True): self.flags |= 0x00000002
        else: self.flags &= ~0x00000002
    IsPlayAtRandom = property(get_IsPlayAtRandom, set_IsPlayAtRandom)
    def get_IsEnvironmentIgnored(self):
        return (self.flags & 0x00000004) != 0
    def set_IsEnvironmentIgnored(self, nValue):
        if (nValue == True): self.flags |= 0x00000004
        else: self.flags &= ~0x00000004
    IsEnvironmentIgnored = property(get_IsEnvironmentIgnored, set_IsEnvironmentIgnored)
    def get_IsRandomLocation(self):
        return (self.flags & 0x00000008) != 0
    def set_IsRandomLocation(self, nValue):
        if (nValue == True): self.flags |= 0x00000008
        else: self.flags &= ~0x00000008
    IsRandomLocation = property(get_IsRandomLocation, set_IsRandomLocation)
    def get_IsLoop(self):
        return (self.flags & 0x00000010) != 0
    def set_IsLoop(self, nValue):
        if (nValue == True): self.flags |= 0x00000010
        else: self.flags &= ~0x00000010
    IsLoop = property(get_IsLoop, set_IsLoop)
    def get_IsMenuSound(self):
        return (self.flags & 0x00000020) != 0
    def set_IsMenuSound(self, nValue):
        if (nValue == True): self.flags |= 0x00000020
        else: self.flags &= ~0x00000020
    IsMenuSound = property(get_IsMenuSound, set_IsMenuSound)
    def get_Is2D(self):
        return (self.flags & 0x00000040) != 0
    def set_Is2D(self, nValue):
        if (nValue == True): self.flags |= 0x00000040
        else: self.flags &= ~0x00000040
    Is2D = property(get_Is2D, set_Is2D)
    def get_Is360LFE(self):
        return (self.flags & 0x00000080) != 0
    def set_Is360LFE(self, nValue):
        if (nValue == True): self.flags |= 0x00000080
        else: self.flags &= ~0x00000080
    Is360LFE = property(get_Is360LFE, set_Is360LFE)
    
class SKILRecord(BaseRecord):
    def CopyAsOverride(self, targetMod):
        FID = CBash.CopySKILRecord(self._CollectionIndex, self._ModName, self._recordID, targetMod._ModName, c_bool(True))
        if(FID): return SKILRecord(self._CollectionIndex, targetMod._ModName, FID)
        return None
    def CopyAsNew(self, targetMod):
        FID = CBash.CopySKILRecord(self._CollectionIndex, self._ModName, self._recordID, targetMod._ModName, c_bool(False))
        if(FID): return SKILRecord(self._CollectionIndex, targetMod._ModName, FID)
        return None
    def get_skill(self):
        CBash.ReadFIDField.restype = POINTER(c_int)
        retValue = CBash.ReadFIDField(self._CollectionIndex, self._ModName, self._recordID, 6)
        if(retValue): return retValue.contents.value
        return None
    def set_skill(self, nValue):
        CBash.SetFIDFieldI(self._CollectionIndex, self._ModName, self._recordID, 6, nValue)
    skill = property(get_skill, set_skill)
    def get_description(self):
        CBash.ReadFIDField.restype = c_char_p
        return CBash.ReadFIDField(self._CollectionIndex, self._ModName, self._recordID, 7)
    def set_description(self, nValue):
        CBash.SetFIDFieldStr(self._CollectionIndex, self._ModName, self._recordID, 7, nValue)
    description = property(get_description, set_description)
    def get_iconPath(self):
        CBash.ReadFIDField.restype = c_char_p
        return CBash.ReadFIDField(self._CollectionIndex, self._ModName, self._recordID, 8)
    def set_iconPath(self, nValue):
        CBash.SetFIDFieldStr(self._CollectionIndex, self._ModName, self._recordID, 8, nValue)
    iconPath = property(get_iconPath, set_iconPath)
    def get_action(self):
        CBash.ReadFIDField.restype = POINTER(c_int)
        retValue = CBash.ReadFIDField(self._CollectionIndex, self._ModName, self._recordID, 9)
        if(retValue): return retValue.contents.value
        return None
    def set_action(self, nValue):
        CBash.SetFIDFieldI(self._CollectionIndex, self._ModName, self._recordID, 9, nValue)
    action = property(get_action, set_action)
    def get_attribute(self):
        CBash.ReadFIDField.restype = POINTER(c_int)
        retValue = CBash.ReadFIDField(self._CollectionIndex, self._ModName, self._recordID, 10)
        if(retValue): return retValue.contents.value
        return None
    def set_attribute(self, nValue):
        CBash.SetFIDFieldI(self._CollectionIndex, self._ModName, self._recordID, 10, nValue)
    attribute = property(get_attribute, set_attribute)
    def get_specialization(self):
        CBash.ReadFIDField.restype = POINTER(c_uint)
        retValue = CBash.ReadFIDField(self._CollectionIndex, self._ModName, self._recordID, 11)
        if(retValue): return retValue.contents.value
        return None
    def set_specialization(self, nValue):
        CBash.SetFIDFieldUI(self._CollectionIndex, self._ModName, self._recordID, 11, c_uint(nValue))
    specialization = property(get_specialization, set_specialization)
    def get_use0(self):
        CBash.ReadFIDField.restype = POINTER(c_float)
        retValue = CBash.ReadFIDField(self._CollectionIndex, self._ModName, self._recordID, 12)
        if(retValue): return retValue.contents.value
        return None
    def set_use0(self, nValue):
        CBash.SetFIDFieldF(self._CollectionIndex, self._ModName, self._recordID, 12, c_float(nValue))
    use0 = property(get_use0, set_use0)
    def get_use1(self):
        CBash.ReadFIDField.restype = POINTER(c_float)
        retValue = CBash.ReadFIDField(self._CollectionIndex, self._ModName, self._recordID, 13)
        if(retValue): return retValue.contents.value
        return None
    def set_use1(self, nValue):
        CBash.SetFIDFieldF(self._CollectionIndex, self._ModName, self._recordID, 13, c_float(nValue))
    use1 = property(get_use1, set_use1)
    def get_apprentice(self):
        CBash.ReadFIDField.restype = c_char_p
        return CBash.ReadFIDField(self._CollectionIndex, self._ModName, self._recordID, 14)
    def set_apprentice(self, nValue):
        CBash.SetFIDFieldStr(self._CollectionIndex, self._ModName, self._recordID, 14, nValue)
    apprentice = property(get_apprentice, set_apprentice)
    def get_journeyman(self):
        CBash.ReadFIDField.restype = c_char_p
        return CBash.ReadFIDField(self._CollectionIndex, self._ModName, self._recordID, 15)
    def set_journeyman(self, nValue):
        CBash.SetFIDFieldStr(self._CollectionIndex, self._ModName, self._recordID, 15, nValue)
    journeyman = property(get_journeyman, set_journeyman)
    def get_expert(self):
        CBash.ReadFIDField.restype = c_char_p
        return CBash.ReadFIDField(self._CollectionIndex, self._ModName, self._recordID, 16)
    def set_expert(self, nValue):
        CBash.SetFIDFieldStr(self._CollectionIndex, self._ModName, self._recordID, 16, nValue)
    expert = property(get_expert, set_expert)
    def get_master(self):
        CBash.ReadFIDField.restype = c_char_p
        return CBash.ReadFIDField(self._CollectionIndex, self._ModName, self._recordID, 17)
    def set_master(self, nValue):
        CBash.SetFIDFieldStr(self._CollectionIndex, self._ModName, self._recordID, 17, nValue)
    master = property(get_master, set_master)
class MGEFRecord(BaseRecord):
    def CopyAsOverride(self, targetMod):
        FID = CBash.CopyMGEFRecord(self._CollectionIndex, self._ModName, self._recordID, targetMod._ModName, c_bool(True))
        if(FID): return MGEFRecord(self._CollectionIndex, targetMod._ModName, FID)
        return None
    def CopyAsNew(self, targetMod):
        FID = CBash.CopyMGEFRecord(self._CollectionIndex, self._ModName, self._recordID, targetMod._ModName, c_bool(False))
        if(FID): return MGEFRecord(self._CollectionIndex, targetMod._ModName, FID)
        return None
    def get_full(self):
        CBash.ReadFIDField.restype = c_char_p
        return CBash.ReadFIDField(self._CollectionIndex, self._ModName, self._recordID, 6)
    def set_full(self, nValue):
        CBash.SetFIDFieldStr(self._CollectionIndex, self._ModName, self._recordID, 6, nValue)
    full = property(get_full, set_full)
    def get_text(self):
        CBash.ReadFIDField.restype = c_char_p
        return CBash.ReadFIDField(self._CollectionIndex, self._ModName, self._recordID, 7)
    def set_text(self, nValue):
        CBash.SetFIDFieldStr(self._CollectionIndex, self._ModName, self._recordID, 7, nValue)
    text = property(get_text, set_text)
    def get_iconPath(self):
        CBash.ReadFIDField.restype = c_char_p
        return CBash.ReadFIDField(self._CollectionIndex, self._ModName, self._recordID, 8)
    def set_iconPath(self, nValue):
        CBash.SetFIDFieldStr(self._CollectionIndex, self._ModName, self._recordID, 8, nValue)
    iconPath = property(get_iconPath, set_iconPath)
    def get_modPath(self):
        CBash.ReadFIDField.restype = c_char_p
        return CBash.ReadFIDField(self._CollectionIndex, self._ModName, self._recordID, 9)
    def set_modPath(self, nValue):
        CBash.SetFIDFieldStr(self._CollectionIndex, self._ModName, self._recordID, 9, nValue)
    modPath = property(get_modPath, set_modPath)
    def get_modb(self):
        CBash.ReadFIDField.restype = POINTER(c_float)
        retValue = CBash.ReadFIDField(self._CollectionIndex, self._ModName, self._recordID, 10)
        if(retValue): return retValue.contents.value
        return None
    def set_modb(self, nValue):
        CBash.SetFIDFieldF(self._CollectionIndex, self._ModName, self._recordID, 10, c_float(nValue))
    modb = property(get_modb, set_modb)
    def get_modt_p(self):
        numRecords = CBash.GetFIDFieldArraySize(self._CollectionIndex, self._ModName, self._recordID, 11)
        if(numRecords > 0):
            cRecords = POINTER(c_ubyte * numRecords)()
            CBash.GetFIDFieldArray(self._CollectionIndex, self._ModName, self._recordID, 11, byref(cRecords))
            return [cRecords.contents[x] for x in range(0, numRecords)]
        return []
    def set_modt_p(self, nValue):
        length = len(nValue)
        CBash.SetFIDFieldR(self._CollectionIndex, self._ModName, self._recordID, 11, struct.pack('B' * length, *nValue), length)
    modt_p = property(get_modt_p, set_modt_p)
    def get_flags(self):
        CBash.ReadFIDField.restype = POINTER(c_uint)
        retValue = CBash.ReadFIDField(self._CollectionIndex, self._ModName, self._recordID, 12)
        if(retValue): return retValue.contents.value
        return None
    def set_flags(self, nValue):
        CBash.SetFIDFieldUI(self._CollectionIndex, self._ModName, self._recordID, 12, c_uint(nValue))
    flags = property(get_flags, set_flags)
    def get_baseCost(self):
        CBash.ReadFIDField.restype = POINTER(c_float)
        retValue = CBash.ReadFIDField(self._CollectionIndex, self._ModName, self._recordID, 13)
        if(retValue): return retValue.contents.value
        return None
    def set_baseCost(self, nValue):
        CBash.SetFIDFieldF(self._CollectionIndex, self._ModName, self._recordID, 13, c_float(nValue))
    baseCost = property(get_baseCost, set_baseCost)
    def get_associated(self):
        CBash.ReadFIDField.restype = POINTER(c_uint)
        retValue = CBash.ReadFIDField(self._CollectionIndex, self._ModName, self._recordID, 14)
        if(retValue): return retValue.contents.value
        return None
    def set_associated(self, nValue):
        CBash.SetFIDFieldUI(self._CollectionIndex, self._ModName, self._recordID, 14, c_uint(nValue))
    associated = property(get_associated, set_associated)
    def get_school(self):
        CBash.ReadFIDField.restype = POINTER(c_uint)
        retValue = CBash.ReadFIDField(self._CollectionIndex, self._ModName, self._recordID, 15)
        if(retValue): return retValue.contents.value
        return None
    def set_school(self, nValue):
        CBash.SetFIDFieldI(self._CollectionIndex, self._ModName, self._recordID, 15, nValue)
    school = property(get_school, set_school)
    def get_resistValue(self):
        CBash.ReadFIDField.restype = POINTER(c_int)
        retValue = CBash.ReadFIDField(self._CollectionIndex, self._ModName, self._recordID, 16)
        if(retValue): return retValue.contents.value
        return None
    def set_resistValue(self, nValue):
        CBash.SetFIDFieldI(self._CollectionIndex, self._ModName, self._recordID, 16, nValue)
    resistValue = property(get_resistValue, set_resistValue)
    def get_unk1(self):
        CBash.ReadFIDField.restype = POINTER(c_ushort)
        retValue = CBash.ReadFIDField(self._CollectionIndex, self._ModName, self._recordID, 17)
        if(retValue): return retValue.contents.value
        return None
    def set_unk1(self, nValue):
        CBash.SetFIDFieldUS(self._CollectionIndex, self._ModName, self._recordID, 17, c_ushort(nValue))
    unk1 = property(get_unk1, set_unk1)
    def get_unused1(self):
        numRecords = CBash.GetFIDFieldArraySize(self._CollectionIndex, self._ModName, self._recordID, 18)
        if(numRecords > 0):
            cRecords = POINTER(c_ubyte * numRecords)()
            CBash.GetFIDFieldArray(self._CollectionIndex, self._ModName, self._recordID, 18, byref(cRecords))
            return [cRecords.contents[x] for x in range(0, numRecords)]
        return []
    def set_unused1(self, nValue):
        CBash.SetFIDFieldR(self._CollectionIndex, self._ModName, self._recordID, 18, struct.pack('2B', *nValue), 2)
    unused1 = property(get_unused1, set_unused1)
    def get_light(self):
        CBash.ReadFIDField.restype = POINTER(c_uint)
        retValue = CBash.ReadFIDField(self._CollectionIndex, self._ModName, self._recordID, 19)
        if(retValue): return retValue.contents.value
        return None
    def set_light(self, nValue):
        CBash.SetFIDFieldUI(self._CollectionIndex, self._ModName, self._recordID, 19, c_uint(nValue))
    light = property(get_light, set_light)
    def get_projectileSpeed(self):
        CBash.ReadFIDField.restype = POINTER(c_float)
        retValue = CBash.ReadFIDField(self._CollectionIndex, self._ModName, self._recordID, 20)
        if(retValue): return retValue.contents.value
        return None
    def set_projectileSpeed(self, nValue):
        CBash.SetFIDFieldF(self._CollectionIndex, self._ModName, self._recordID, 20, c_float(nValue))
    projectileSpeed = property(get_projectileSpeed, set_projectileSpeed)
    def get_effectShader(self):
        CBash.ReadFIDField.restype = POINTER(c_uint)
        retValue = CBash.ReadFIDField(self._CollectionIndex, self._ModName, self._recordID, 21)
        if(retValue): return retValue.contents.value
        return None
    def set_effectShader(self, nValue):
        CBash.SetFIDFieldUI(self._CollectionIndex, self._ModName, self._recordID, 21, c_uint(nValue))
    effectShader = property(get_effectShader, set_effectShader)
    def get_enchantEffect(self):
        CBash.ReadFIDField.restype = POINTER(c_uint)
        retValue = CBash.ReadFIDField(self._CollectionIndex, self._ModName, self._recordID, 22)
        if(retValue): return retValue.contents.value
        return None
    def set_enchantEffect(self, nValue):
        CBash.SetFIDFieldUI(self._CollectionIndex, self._ModName, self._recordID, 22, c_uint(nValue))
    enchantEffect = property(get_enchantEffect, set_enchantEffect)
    def get_castingSound(self):
        CBash.ReadFIDField.restype = POINTER(c_uint)
        retValue = CBash.ReadFIDField(self._CollectionIndex, self._ModName, self._recordID, 23)
        if(retValue): return retValue.contents.value
        return None
    def set_castingSound(self, nValue):
        CBash.SetFIDFieldUI(self._CollectionIndex, self._ModName, self._recordID, 23, c_uint(nValue))
    castingSound = property(get_castingSound, set_castingSound)
    def get_boltSound(self):
        CBash.ReadFIDField.restype = POINTER(c_uint)
        retValue = CBash.ReadFIDField(self._CollectionIndex, self._ModName, self._recordID, 24)
        if(retValue): return retValue.contents.value
        return None
    def set_boltSound(self, nValue):
        CBash.SetFIDFieldUI(self._CollectionIndex, self._ModName, self._recordID, 24, c_uint(nValue))
    boltSound = property(get_boltSound, set_boltSound)
    def get_hitSound(self):
        CBash.ReadFIDField.restype = POINTER(c_uint)
        retValue = CBash.ReadFIDField(self._CollectionIndex, self._ModName, self._recordID, 25)
        if(retValue): return retValue.contents.value
        return None
    def set_hitSound(self, nValue):
        CBash.SetFIDFieldUI(self._CollectionIndex, self._ModName, self._recordID, 25, c_uint(nValue))
    hitSound = property(get_hitSound, set_hitSound)
    def get_areaSound(self):
        CBash.ReadFIDField.restype = POINTER(c_uint)
        retValue = CBash.ReadFIDField(self._CollectionIndex, self._ModName, self._recordID, 26)
        if(retValue): return retValue.contents.value
        return None
    def set_areaSound(self, nValue):
        CBash.SetFIDFieldUI(self._CollectionIndex, self._ModName, self._recordID, 26, c_uint(nValue))
    areaSound = property(get_areaSound, set_areaSound)
    def get_cefEnchantment(self):
        CBash.ReadFIDField.restype = POINTER(c_float)
        retValue = CBash.ReadFIDField(self._CollectionIndex, self._ModName, self._recordID, 27)
        if(retValue): return retValue.contents.value
        return None
    def set_cefEnchantment(self, nValue):
        CBash.SetFIDFieldF(self._CollectionIndex, self._ModName, self._recordID, 27, c_float(nValue))
    cefEnchantment = property(get_cefEnchantment, set_cefEnchantment)
    def get_cefBarter(self):
        CBash.ReadFIDField.restype = POINTER(c_float)
        retValue = CBash.ReadFIDField(self._CollectionIndex, self._ModName, self._recordID, 28)
        if(retValue): return retValue.contents.value
        return None
    def set_cefBarter(self, nValue):
        CBash.SetFIDFieldF(self._CollectionIndex, self._ModName, self._recordID, 28, c_float(nValue))
    cefBarter = property(get_cefBarter, set_cefBarter)
    def get_counterEffects(self):
        numRecords = CBash.GetFIDFieldArraySize(self._CollectionIndex, self._ModName, self._recordID, 29)
        if(numRecords > 0):
            cRecords = POINTER(c_uint * numRecords)()
            CBash.GetFIDFieldArray(self._CollectionIndex, self._ModName, self._recordID, 29, byref(cRecords))
            return [cRecords.contents[x] for x in range(0, numRecords)]
        return []
    def set_counterEffects(self, nValue):
        CBash.SetFIDFieldUIA(self._CollectionIndex, self._ModName, self._recordID, 29, struct.pack('I' * len(nValue), *nValue), len(nValue))
    counterEffects = property(get_counterEffects, set_counterEffects)
    def get_IsHostile(self):
        return (self.flags & 0x00000001) != 0
    def set_IsHostile(self, nValue):
        if (nValue == True): self.flags |= 0x00000001
        else: self.flags &= ~0x00000001
    IsHostile = property(get_IsHostile, set_IsHostile)
    def get_IsRecover(self):
        return (self.flags & 0x00000002) != 0
    def set_IsRecover(self, nValue):
        if (nValue == True): self.flags |= 0x00000002
        else: self.flags &= ~0x00000002
    IsRecover = property(get_IsRecover, set_IsRecover)
    def get_IsDetrimental(self):
        return (self.flags & 0x00000004) != 0
    def set_IsDetrimental(self, nValue):
        if (nValue == True): self.flags |= 0x00000004
        else: self.flags &= ~0x00000004
    IsDetrimental = property(get_IsDetrimental, set_IsDetrimental)
    def get_IsMagnitude(self):
        return (self.flags & 0x00000008) != 0
    def set_IsMagnitude(self, nValue):
        if (nValue == True): self.flags |= 0x00000008
        else: self.flags &= ~0x00000008
    IsMagnitude = property(get_IsMagnitude, set_IsMagnitude)
    def get_IsSelf(self):
        return (self.flags & 0x00000010) != 0
    def set_IsSelf(self, nValue):
        if (nValue == True): self.flags |= 0x00000010
        else: self.flags &= ~0x00000010
    IsSelf = property(get_IsSelf, set_IsSelf)
    def get_IsTouch(self):
        return (self.flags & 0x00000020) != 0
    def set_IsTouch(self, nValue):
        if (nValue == True): self.flags |= 0x00000020
        else: self.flags &= ~0x00000020
    IsTouch = property(get_IsTouch, set_IsTouch)
    def get_IsTarget(self):
        return (self.flags & 0x00000040) != 0
    def set_IsTarget(self, nValue):
        if (nValue == True): self.flags |= 0x00000040
        else: self.flags &= ~0x00000040
    IsTarget = property(get_IsTarget, set_IsTarget)
    def get_IsNoDuration(self):
        return (self.flags & 0x00000080) != 0
    def set_IsNoDuration(self, nValue):
        if (nValue == True): self.flags |= 0x00000080
        else: self.flags &= ~0x00000080
    IsNoDuration = property(get_IsNoDuration, set_IsNoDuration)
    def get_IsNoMagnitude(self):
        return (self.flags & 0x00000100) != 0
    def set_IsNoMagnitude(self, nValue):
        if (nValue == True): self.flags |= 0x00000100
        else: self.flags &= ~0x00000100
    IsNoMagnitude = property(get_IsNoMagnitude, set_IsNoMagnitude)
    def get_IsNoArea(self):
        return (self.flags & 0x00000200) != 0
    def set_IsNoArea(self, nValue):
        if (nValue == True): self.flags |= 0x00000200
        else: self.flags &= ~0x00000200
    IsNoArea = property(get_IsNoArea, set_IsNoArea)
    def get_IsFXPersist(self):
        return (self.flags & 0x00000400) != 0
    def set_IsFXPersist(self, nValue):
        if (nValue == True): self.flags |= 0x00000400
        else: self.flags &= ~0x00000400
    IsFXPersist = property(get_IsFXPersist, set_IsFXPersist)
    def get_IsSpellmaking(self):
        return (self.flags & 0x00000800) != 0
    def set_IsSpellmaking(self, nValue):
        if (nValue == True): self.flags |= 0x00000800
        else: self.flags &= ~0x00000800
    IsSpellmaking = property(get_IsSpellmaking, set_IsSpellmaking)
    def get_IsEnchanting(self):
        return (self.flags & 0x00001000) != 0
    def set_IsEnchanting(self, nValue):
        if (nValue == True): self.flags |= 0x00001000
        else: self.flags &= ~0x00001000
    IsEnchanting = property(get_IsEnchanting, set_IsEnchanting)
    def get_IsNoIngredient(self):
        return (self.flags & 0x00002000) != 0
    def set_IsNoIngredient(self, nValue):
        if (nValue == True): self.flags |= 0x00002000
        else: self.flags &= ~0x00002000
    IsNoIngredient = property(get_IsNoIngredient, set_IsNoIngredient)
    def get_IsUseWeapon(self):
        return (self.flags & 0x00010000) != 0
    def set_IsUseWeapon(self, nValue):
        if (nValue == True): self.flags |= 0x00010000
        else: self.flags &= ~0x00010000
    IsUseWeapon = property(get_IsUseWeapon, set_IsUseWeapon)
    def get_IsUseArmor(self):
        return (self.flags & 0x00020000) != 0
    def set_IsUseArmor(self, nValue):
        if (nValue == True): self.flags |= 0x00020000
        else: self.flags &= ~0x00020000
    IsUseArmor = property(get_IsUseArmor, set_IsUseArmor)
    def get_IsUseCreature(self):
        return (self.flags & 0x00040000) != 0
    def set_IsUseCreature(self, nValue):
        if (nValue == True): self.flags |= 0x00040000
        else: self.flags &= ~0x00040000
    IsUseCreature = property(get_IsUseCreature, set_IsUseCreature)
    def get_IsUseSkill(self):
        return (self.flags & 0x00080000) != 0
    def set_IsUseSkill(self, nValue):
        if (nValue == True): self.flags |= 0x00080000
        else: self.flags &= ~0x00080000
    IsUseSkill = property(get_IsUseSkill, set_IsUseSkill)
    def get_IsUseAttr(self):
        return (self.flags & 0x00100000) != 0
    def set_IsUseAttr(self, nValue):
        if (nValue == True): self.flags |= 0x00100000
        else: self.flags &= ~0x00100000
    IsUseAttr = IsUseAttribute = property(get_IsUseAttr, set_IsUseAttr)
    def get_IsUseAV(self):
        return (self.flags & 0x01000000) != 0
    def set_IsUseAV(self, nValue):
        if (nValue == True): self.flags |= 0x01000000
        else: self.flags &= ~0x01000000
    IsUseAV = IsUseActorValue = property(get_IsUseAV, set_IsUseAV)
    def get_IsSprayType(self):
        return (self.flags & 0x02000000) != 0 and (self.flags & 0x04000000) == 0
    def set_IsSprayType(self, nValue):
        if (nValue == True):
            self.flags &= ~0x06000000
            self.flags |= 0x02000000
        elif self.get_IsSprayType():
            self.IsBallType = True
    IsSprayType = property(get_IsSprayType, set_IsSprayType)
    def get_IsBoltType(self):
        return (self.flags & 0x04000000) != 0 and (self.flags & 0x02000000) == 0
    def set_IsBoltType(self, nValue):
        if (nValue == True):
            self.flags &= ~0x06000000
            self.flags |= 0x04000000
        elif self.get_IsBoltType():
            self.IsBallType = True
    IsBoltType = property(get_IsBoltType, set_IsBoltType)
    def get_IsFogType(self):
        return (self.flags & 0x06000000) == 0x06000000
    def set_IsFogType(self, nValue):
        if (nValue == True):
            self.flags |= 0x06000000
        elif self.get_IsFogType():
            self.IsBallType = True
    IsFogType = property(get_IsFogType, set_IsFogType)
    def get_IsBallType(self):
        return (self.flags & 0x06000000) == 0
    def set_IsBallType(self, nValue):
        if (nValue == True):
            self.flags &= ~0x06000000
        elif self.get_IsBallType():
            self.IsBoltType = True
    IsBallType = property(get_IsBallType, set_IsBallType)
    def get_IsNoHitEffect(self):
        return (self.flags & 0x08000000) != 0
    def set_IsNoHitEffect(self, nValue):
        if (nValue == True): self.flags |= 0x08000000
        else: self.flags &= ~0x08000000
    IsNoHitEffect = property(get_IsNoHitEffect, set_IsNoHitEffect)

class SCPTRecord(BaseRecord):
    def CopyAsOverride(self, targetMod):
        FID = CBash.CopySCPTRecord(self._CollectionIndex, self._ModName, self._recordID, targetMod._ModName, c_bool(True))
        if(FID): return SCPTRecord(self._CollectionIndex, targetMod._ModName, FID)
        return None
    def CopyAsNew(self, targetMod):
        FID = CBash.CopySCPTRecord(self._CollectionIndex, self._ModName, self._recordID, targetMod._ModName, c_bool(False))
        if(FID): return SCPTRecord(self._CollectionIndex, targetMod._ModName, FID)
        return None
    class Var(object):
        def __init__(self, CollectionIndex, ModName, recordID, listIndex):
            self._CollectionIndex = CollectionIndex
            self._ModName = ModName
            self._recordID = recordID
            self._listIndex = listIndex
        def get_listIndex(self):
            CBash.ReadFIDListField.restype = POINTER(c_uint)
            retValue = CBash.ReadFIDListField(self._CollectionIndex, self._ModName, self._recordID, 13, self._listIndex, 1)
            if(retValue): return retValue.contents.value
            return None
        def set_listIndex(self, nValue):
            CBash.SetFIDListFieldUI(self._CollectionIndex, self._ModName, self._recordID, 13, self._listIndex, 1, nValue)
        index = property(get_listIndex, set_listIndex)
        def get_unused1(self):
            numRecords = CBash.GetFIDListArraySize(self._CollectionIndex, self._ModName, self._recordID, 13, self._listIndex, 2)
            if(numRecords > 0):
                cRecords = POINTER(c_ubyte * numRecords)()
                CBash.GetFIDListArray(self._CollectionIndex, self._ModName, self._recordID, 13, self._listIndex, 2, byref(cRecords))
                return [cRecords.contents[x] for x in range(0, numRecords)]
            return []
        def set_unused1(self, nValue):
            CBash.SetFIDListFieldR(self._CollectionIndex, self._ModName, self._recordID, 13, self._listIndex, 2, struct.pack('12B', *nValue), 12)
        unused1 = property(get_unused1, set_unused1)
        def get_flags(self):
            CBash.ReadFIDListField.restype = POINTER(c_ubyte)
            retValue = CBash.ReadFIDListField(self._CollectionIndex, self._ModName, self._recordID, 13, self._listIndex, 3)
            if(retValue): return retValue.contents.value
            return None
        def set_flags(self, nValue):
            CBash.SetFIDListFieldUC(self._CollectionIndex, self._ModName, self._recordID, 13, self._listIndex, 3, c_ubyte(nValue))
        flags = property(get_flags, set_flags)
        def get_unused2(self):
            numRecords = CBash.GetFIDListArraySize(self._CollectionIndex, self._ModName, self._recordID, 13, self._listIndex, 4)
            if(numRecords > 0):
                cRecords = POINTER(c_ubyte * numRecords)()
                CBash.GetFIDListArray(self._CollectionIndex, self._ModName, self._recordID, 13, self._listIndex, 4, byref(cRecords))
                return [cRecords.contents[x] for x in range(0, numRecords)]
            return []
        def set_unused2(self, nValue):
            CBash.SetFIDListFieldR(self._CollectionIndex, self._ModName, self._recordID, 13, self._listIndex, 4, struct.pack('7B', *nValue), 7)
        unused2 = property(get_unused2, set_unused2)
        def get_name(self):
            CBash.ReadFIDListField.restype = c_char_p
            return CBash.ReadFIDListField(self._CollectionIndex, self._ModName, self._recordID, 13, self._listIndex, 5)
        def set_name(self, nValue):
            CBash.SetFIDListFieldStr(self._CollectionIndex, self._ModName, self._recordID, 13, self._listIndex, 5, nValue)
        name = property(get_name, set_name)
        def get_IsLongOrShort(self):
            return (self.flags & 0x00000001) != 0
        def set_IsLongOrShort(self, nValue):
            if (nValue == True): self.flags |= 0x00000001
            else: self.flags &= ~0x00000001
        IsLongOrShort = property(get_IsLongOrShort, set_IsLongOrShort)
    class Reference(object):
        def __init__(self, CollectionIndex, ModName, recordID, listIndex):
            self._CollectionIndex = CollectionIndex
            self._ModName = ModName
            self._recordID = recordID
            self._listIndex = listIndex
        def get_reference(self):
            CBash.ReadFIDListField.restype = POINTER(c_uint)
            retValue = CBash.ReadFIDListField(self._CollectionIndex, self._ModName, self._recordID, 14, self._listIndex, 1)
            if(retValue): return retValue.contents.value
            return None
        def set_reference(self, nValue):
            CBash.SetFIDListFieldUI(self._CollectionIndex, self._ModName, self._recordID, 14, self._listIndex, 1, nValue)
        reference = property(get_reference, set_reference)
        def get_IsSCRO(self):
            CBash.ReadFIDListField.restype = POINTER(c_bool)
            retValue = CBash.ReadFIDListField(self._CollectionIndex, self._ModName, self._recordID, 14, self._listIndex, 2)
            if(retValue): return retValue.contents.value
            return None
        def set_IsSCRO(self, nValue):
            if isinstance(nValue, bool):
                if(nValue): CBash.SetFIDListFieldUI(self._CollectionIndex, self._ModName, self._recordID, 14, self._listIndex, 2, 1)
                else: CBash.SetFIDListFieldUI(self._CollectionIndex, self._ModName, self._recordID, 14, self._listIndex, 2, 0)
            else: CBash.SetFIDListFieldUI(self._CollectionIndex, self._ModName, self._recordID, 14, self._listIndex, 2, nValue)
        IsSCRO = property(get_IsSCRO, set_IsSCRO)
    def newVarsElement(self):
        listIndex = CBash.CreateFIDListElement(self._CollectionIndex, self._ModName, self._recordID, 13)
        if(listIndex == -1): return None
        return self.Var(self._CollectionIndex, self._ModName, self._recordID, listIndex)    
    def newReferencesElement(self):
        listIndex = CBash.CreateFIDListElement(self._CollectionIndex, self._ModName, self._recordID, 14)
        if(listIndex == -1): return None
        return self.Reference(self._CollectionIndex, self._ModName, self._recordID, listIndex)    
    def get_unused1(self):
        numRecords = CBash.GetFIDFieldArraySize(self._CollectionIndex, self._ModName, self._recordID, 6)
        if(numRecords > 0):
            cRecords = POINTER(c_ubyte * numRecords)()
            CBash.GetFIDFieldArray(self._CollectionIndex, self._ModName, self._recordID, 6, byref(cRecords))
            return [cRecords.contents[x] for x in range(0, numRecords)]
        return []
    def set_unused1(self, nValue):
        CBash.SetFIDFieldR(self._CollectionIndex, self._ModName, self._recordID, 6, struct.pack('2B', *nValue), 2)
    unused1 = property(get_unused1, set_unused1)
    def get_numRefs(self):
        CBash.ReadFIDField.restype = POINTER(c_uint)
        retValue = CBash.ReadFIDField(self._CollectionIndex, self._ModName, self._recordID, 7)
        if(retValue): return retValue.contents.value
        return None
    def set_numRefs(self, nValue):
        CBash.SetFIDFieldUI(self._CollectionIndex, self._ModName, self._recordID, 7, c_uint(nValue))
    numRefs = property(get_numRefs, set_numRefs)
    def get_compiledSize(self):
        CBash.ReadFIDField.restype = POINTER(c_uint)
        retValue = CBash.ReadFIDField(self._CollectionIndex, self._ModName, self._recordID, 8)
        if(retValue): return retValue.contents.value
        return None
    def set_compiledSize(self, nValue):
        CBash.SetFIDFieldUI(self._CollectionIndex, self._ModName, self._recordID, 8, c_uint(nValue))
    compiledSize = property(get_compiledSize, set_compiledSize)
    def get_lastIndex(self):
        CBash.ReadFIDField.restype = POINTER(c_uint)
        retValue = CBash.ReadFIDField(self._CollectionIndex, self._ModName, self._recordID, 9)
        if(retValue): return retValue.contents.value
        return None
    def set_lastIndex(self, nValue):
        CBash.SetFIDFieldUI(self._CollectionIndex, self._ModName, self._recordID, 9, c_uint(nValue))
    lastIndex = property(get_lastIndex, set_lastIndex)
    def get_scriptType(self):
        CBash.ReadFIDField.restype = POINTER(c_uint)
        retValue = CBash.ReadFIDField(self._CollectionIndex, self._ModName, self._recordID, 10)
        if(retValue): return retValue.contents.value
        return None
    def set_scriptType(self, nValue):
        CBash.SetFIDFieldUI(self._CollectionIndex, self._ModName, self._recordID, 10, c_uint(nValue))
    scriptType = property(get_scriptType, set_scriptType)
    def get_compiled_p(self):
        numRecords = CBash.GetFIDFieldArraySize(self._CollectionIndex, self._ModName, self._recordID, 11)
        if(numRecords > 0):
            cRecords = POINTER(c_ubyte * numRecords)()
            CBash.GetFIDFieldArray(self._CollectionIndex, self._ModName, self._recordID, 11, byref(cRecords))
            return [cRecords.contents[x] for x in range(0, numRecords)]
        return []
    def set_compiled_p(self, nValue):
        CBash.SetFIDFieldR(self._CollectionIndex, self._ModName, self._recordID, 11, struct.pack('B' * len(nValue), *nValue), len(nValue))
    compiled_p = property(get_compiled_p, set_compiled_p)
    def get_scriptText(self):
        CBash.ReadFIDField.restype = c_char_p
        return CBash.ReadFIDField(self._CollectionIndex, self._ModName, self._recordID, 12)
    def set_scriptText(self, nValue):
        CBash.SetFIDFieldStr(self._CollectionIndex, self._ModName, self._recordID, 12, nValue)
    scriptText = property(get_scriptText, set_scriptText)
    def get_vars(self):
        numRecords = CBash.GetFIDListSize(self._CollectionIndex, self._ModName, self._recordID, 13)
        if(numRecords > 0): return [self.Var(self._CollectionIndex, self._ModName, self._recordID, x) for x in range(0, numRecords)]
        return []
    def set_vars(self, nVars):
        diffLength = len(nVars) - CBash.GetFIDListSize(self._CollectionIndex, self._ModName, self._recordID, 13)
        nValues = [(nVar.index, nVar.unused1, nVar.flags, nVar.unused2, nVar.name) for nVar in nVars]
        while(diffLength < 0):
            CBash.DeleteFIDListElement(self._CollectionIndex, self._ModName, self._recordID, 13)
            diffLength += 1
        while(diffLength > 0):
            CBash.CreateFIDListElement(self._CollectionIndex, self._ModName, self._recordID, 13)
            diffLength -= 1
        for oVar, nValue in zip(self.vars, nValues):
            oVar.index, oVar.unused1, oVar.flags, oVar.unused2, oVar.name = nValue
    vars = property(get_vars, set_vars)
    def get_references(self):
        numRecords = CBash.GetFIDListSize(self._CollectionIndex, self._ModName, self._recordID, 14)
        if(numRecords > 0): return [self.Reference(self._CollectionIndex, self._ModName, self._recordID, x) for x in range(0, numRecords)]
        return []
    def set_references(self, nReferences):
        diffLength = len(nReferences) - CBash.GetFIDListSize(self._CollectionIndex, self._ModName, self._recordID, 14)
        nValues = [(nReference.reference,nReference.IsSCRO) for nReference in nReferences]
        while(diffLength < 0):
            CBash.DeleteFIDListElement(self._CollectionIndex, self._ModName, self._recordID, 14)
            diffLength += 1
        while(diffLength > 0):
            CBash.CreateFIDListElement(self._CollectionIndex, self._ModName, self._recordID, 14)
            diffLength -= 1
        for oReference, nValue in zip(self.references, nValues):
            oReference.reference, oReference.IsSCRO = nValue  
    references = property(get_references, set_references)
    
class LTEXRecord(BaseRecord):
    def CopyAsOverride(self, targetMod):
        FID = CBash.CopyLTEXRecord(self._CollectionIndex, self._ModName, self._recordID, targetMod._ModName, c_bool(True))
        if(FID): return LTEXRecord(self._CollectionIndex, targetMod._ModName, FID)
        return None
    def CopyAsNew(self, targetMod):
        FID = CBash.CopyLTEXRecord(self._CollectionIndex, self._ModName, self._recordID, targetMod._ModName, c_bool(False))
        if(FID): return LTEXRecord(self._CollectionIndex, targetMod._ModName, FID)
        return None
    def get_iconPath(self):
        CBash.ReadFIDField.restype = c_char_p
        return CBash.ReadFIDField(self._CollectionIndex, self._ModName, self._recordID, 6)
    def set_iconPath(self, nValue):
        CBash.SetFIDFieldStr(self._CollectionIndex, self._ModName, self._recordID, 6, nValue)
    iconPath = property(get_iconPath, set_iconPath)
    def get_flags(self):
        CBash.ReadFIDField.restype = POINTER(c_ubyte)
        retValue = CBash.ReadFIDField(self._CollectionIndex, self._ModName, self._recordID, 7)
        if(retValue): return retValue.contents.value
        return None
    def set_flags(self, nValue):
        CBash.SetFIDFieldUC(self._CollectionIndex, self._ModName, self._recordID, 7, c_ubyte(nValue))
    flags = property(get_flags, set_flags)
    def get_friction(self):
        CBash.ReadFIDField.restype = POINTER(c_ubyte)
        retValue = CBash.ReadFIDField(self._CollectionIndex, self._ModName, self._recordID, 8)
        if(retValue): return retValue.contents.value
        return None
    def set_friction(self, nValue):
        CBash.SetFIDFieldUC(self._CollectionIndex, self._ModName, self._recordID, 8, c_ubyte(nValue))
    friction = property(get_friction, set_friction)
    def get_restitution(self):
        CBash.ReadFIDField.restype = POINTER(c_ubyte)
        retValue = CBash.ReadFIDField(self._CollectionIndex, self._ModName, self._recordID, 9)
        if(retValue): return retValue.contents.value
        return None
    def set_restitution(self, nValue):
        CBash.SetFIDFieldUC(self._CollectionIndex, self._ModName, self._recordID, 9, c_ubyte(nValue))
    restitution = property(get_restitution, set_restitution)
    def get_specular(self):
        CBash.ReadFIDField.restype = POINTER(c_ubyte)
        retValue = CBash.ReadFIDField(self._CollectionIndex, self._ModName, self._recordID, 10)
        if(retValue): return retValue.contents.value
        return None
    def set_specular(self, nValue):
        CBash.SetFIDFieldUC(self._CollectionIndex, self._ModName, self._recordID, 10, c_ubyte(nValue))
    specular = property(get_specular, set_specular)
    def get_grass(self):
        numRecords = CBash.GetFIDFieldArraySize(self._CollectionIndex, self._ModName, self._recordID, 11)
        if(numRecords > 0):
            cRecords = (POINTER(c_uint) * numRecords)()
            CBash.GetFIDFieldArray(self._CollectionIndex, self._ModName, self._recordID, 11, byref(cRecords))
            return [cRecords[x].contents.value for x in range(0, numRecords)]
        return []
    def set_grass(self, nValue):
        length = len(nValue)
        cRecords = (c_uint * length)(*nValue)
        CBash.SetFIDFieldUIA(self._CollectionIndex, self._ModName, self._recordID, 11, cRecords, length)
    grass = property(get_grass, set_grass)
    def get_IsStone(self):
        return (self.flags & 0x00000001) != 0
    def set_IsStone(self, nValue):
        if (nValue == True): self.flags |= 0x00000001
        else: self.flags &= ~0x00000001
    IsStone = property(get_IsStone, set_IsStone)
    def get_IsCloth(self):
        return (self.flags & 0x00000002) != 0
    def set_IsCloth(self, nValue):
        if (nValue == True): self.flags |= 0x00000002
        else: self.flags &= ~0x00000002
    IsCloth = property(get_IsCloth, set_IsCloth)
    def get_IsDirt(self):
        return (self.flags & 0x00000004) != 0
    def set_IsDirt(self, nValue):
        if (nValue == True): self.flags |= 0x00000004
        else: self.flags &= ~0x00000004
    IsDirt = property(get_IsDirt, set_IsDirt)
    def get_IsGlass(self):
        return (self.flags & 0x00000008) != 0
    def set_IsGlass(self, nValue):
        if (nValue == True): self.flags |= 0x00000008
        else: self.flags &= ~0x00000008
    IsGlass = property(get_IsGlass, set_IsGlass)
    def get_IsGrass(self):
        return (self.flags & 0x00000010) != 0
    def set_IsGrass(self, nValue):
        if (nValue == True): self.flags |= 0x00000010
        else: self.flags &= ~0x00000010
    IsGrass = property(get_IsGrass, set_IsGrass)
    def get_IsMetal(self):
        return (self.flags & 0x00000020) != 0
    def set_IsMetal(self, nValue):
        if (nValue == True): self.flags |= 0x00000020
        else: self.flags &= ~0x00000020
    IsMetal = property(get_IsMetal, set_IsMetal)
    def get_IsOrganic(self):
        return (self.flags & 0x00000040) != 0
    def set_IsOrganic(self, nValue):
        if (nValue == True): self.flags |= 0x00000040
        else: self.flags &= ~0x00000040
    IsOrganic = property(get_IsOrganic, set_IsOrganic)
    def get_IsSkin(self):
        return (self.flags & 0x00000080) != 0
    def set_IsSkin(self, nValue):
        if (nValue == True): self.flags |= 0x00000080
        else: self.flags &= ~0x00000080
    IsSkin = property(get_IsSkin, set_IsSkin)
    def get_IsWater(self):
        return (self.flags & 0x00000100) != 0
    def set_IsWater(self, nValue):
        if (nValue == True): self.flags |= 0x00000100
        else: self.flags &= ~0x00000100
    IsWater = property(get_IsWater, set_IsWater)
    def get_IsWood(self):
        return (self.flags & 0x00000200) != 0
    def set_IsWood(self, nValue):
        if (nValue == True): self.flags |= 0x00000200
        else: self.flags &= ~0x00000200
    IsWood = property(get_IsWood, set_IsWood)
    def get_IsHeavyStone(self):
        return (self.flags & 0x00000400) != 0
    def set_IsHeavyStone(self, nValue):
        if (nValue == True): self.flags |= 0x00000400
        else: self.flags &= ~0x00000400
    IsHeavyStone = property(get_IsHeavyStone, set_IsHeavyStone)
    def get_IsHeavyMetal(self):
        return (self.flags & 0x00000800) != 0
    def set_IsHeavyMetal(self, nValue):
        if (nValue == True): self.flags |= 0x00000800
        else: self.flags &= ~0x00000800
    IsHeavyMetal = property(get_IsHeavyMetal, set_IsHeavyMetal)
    def get_IsHeavyWood(self):
        return (self.flags & 0x00001000) != 0
    def set_IsHeavyWood(self, nValue):
        if (nValue == True): self.flags |= 0x00001000
        else: self.flags &= ~0x00001000
    IsHeavyWood = property(get_IsHeavyWood, set_IsHeavyWood)
    def get_IsChain(self):
        return (self.flags & 0x00002000) != 0
    def set_IsChain(self, nValue):
        if (nValue == True): self.flags |= 0x00002000
        else: self.flags &= ~0x00002000
    IsChain = property(get_IsChain, set_IsChain)
    def get_IsSnow(self):
        return (self.flags & 0x00004000) != 0
    def set_IsSnow(self, nValue):
        if (nValue == True): self.flags |= 0x00004000
        else: self.flags &= ~0x00004000
    IsSnow = property(get_IsSnow, set_IsSnow)

class ENCHRecord(BaseRecord):
    def CopyAsOverride(self, targetMod):
        FID = CBash.CopyENCHRecord(self._CollectionIndex, self._ModName, self._recordID, targetMod._ModName, c_bool(True))
        if(FID): return ENCHRecord(self._CollectionIndex, targetMod._ModName, FID)
        return None
    def CopyAsNew(self, targetMod):
        FID = CBash.CopyENCHRecord(self._CollectionIndex, self._ModName, self._recordID, targetMod._ModName, c_bool(False))
        if(FID): return ENCHRecord(self._CollectionIndex, targetMod._ModName, FID)
        return None
    class Effect(object):
        def __init__(self, CollectionIndex, ModName, recordID, subField, listIndex):
            self._CollectionIndex = CollectionIndex
            self._ModName = ModName
            self._recordID = recordID
            self._subField = subField
            self._listIndex = listIndex
        ##name0 and name are both are always the same value, so setting one will set both. They're basically aliases
        def get_name0(self):
            CBash.ReadFIDListField.restype = POINTER(c_uint)
            retValue = CBash.ReadFIDListField(self._CollectionIndex, self._ModName, self._recordID, self._subField, self._listIndex, 1)
            if(retValue): return retValue.contents.value
            return None
        def set_name0(self, nValue):
            CBash.SetFIDListFieldUI(self._CollectionIndex, self._ModName, self._recordID, self._subField, self._listIndex, 1, nValue)
        name0 = property(get_name0, set_name0)
        def get_name(self):
            CBash.ReadFIDListField.restype = POINTER(c_uint)
            retValue = CBash.ReadFIDListField(self._CollectionIndex, self._ModName, self._recordID, self._subField, self._listIndex, 2)
            if(retValue): return retValue.contents.value
            return None
        def set_name(self, nValue):
            CBash.SetFIDListFieldUI(self._CollectionIndex, self._ModName, self._recordID, self._subField, self._listIndex, 2, nValue)
        name = property(get_name, set_name)
        def get_magnitude(self):
            CBash.ReadFIDListField.restype = POINTER(c_uint)
            retValue = CBash.ReadFIDListField(self._CollectionIndex, self._ModName, self._recordID, self._subField, self._listIndex, 3)
            if(retValue): return retValue.contents.value
            return None
        def set_magnitude(self, nValue):
            CBash.SetFIDListFieldUI(self._CollectionIndex, self._ModName, self._recordID, self._subField, self._listIndex, 3, nValue)
        magnitude = property(get_magnitude, set_magnitude)
        def get_area(self):
            CBash.ReadFIDListField.restype = POINTER(c_uint)
            retValue = CBash.ReadFIDListField(self._CollectionIndex, self._ModName, self._recordID, self._subField, self._listIndex, 4)
            if(retValue): return retValue.contents.value
            return None
        def set_area(self, nValue):
            CBash.SetFIDListFieldUI(self._CollectionIndex, self._ModName, self._recordID, self._subField, self._listIndex, 4, nValue)
        area = property(get_area, set_area)
        def get_duration(self):
            CBash.ReadFIDListField.restype = POINTER(c_uint)
            retValue = CBash.ReadFIDListField(self._CollectionIndex, self._ModName, self._recordID, self._subField, self._listIndex, 5)
            if(retValue): return retValue.contents.value
            return None
        def set_duration(self, nValue):
            CBash.SetFIDListFieldUI(self._CollectionIndex, self._ModName, self._recordID, self._subField, self._listIndex, 5, nValue)
        duration = property(get_duration, set_duration)
        def get_recipient(self):
            CBash.ReadFIDListField.restype = POINTER(c_uint)
            retValue = CBash.ReadFIDListField(self._CollectionIndex, self._ModName, self._recordID, self._subField, self._listIndex, 6)
            if(retValue): return retValue.contents.value
            return None
        def set_recipient(self, nValue):
            CBash.SetFIDListFieldUI(self._CollectionIndex, self._ModName, self._recordID, self._subField, self._listIndex, 6, nValue)
        recipient = property(get_recipient, set_recipient)
        def get_actorValue(self):
            CBash.ReadFIDListField.restype = POINTER(c_int)
            retValue = CBash.ReadFIDListField(self._CollectionIndex, self._ModName, self._recordID, self._subField, self._listIndex, 7)
            if(retValue): return retValue.contents.value
            return None
        def set_actorValue(self, nValue):
            CBash.SetFIDListFieldI(self._CollectionIndex, self._ModName, self._recordID, self._subField, self._listIndex, 7, nValue)
        actorValue = property(get_actorValue, set_actorValue)
        def get_script(self):
            CBash.ReadFIDListField.restype = POINTER(c_uint)
            retValue = CBash.ReadFIDListField(self._CollectionIndex, self._ModName, self._recordID, self._subField, self._listIndex, 8)
            if(retValue): return retValue.contents.value
            return None
        def set_script(self, nValue):
            CBash.SetFIDListFieldUI(self._CollectionIndex, self._ModName, self._recordID, self._subField, self._listIndex, 8, nValue)
        script = property(get_script, set_script)
        def get_school(self):
            CBash.ReadFIDListField.restype = POINTER(c_uint)
            retValue = CBash.ReadFIDListField(self._CollectionIndex, self._ModName, self._recordID, self._subField, self._listIndex, 9)
            if(retValue): return retValue.contents.value
            return None
        def set_school(self, nValue):
            CBash.SetFIDListFieldUI(self._CollectionIndex, self._ModName, self._recordID, self._subField, self._listIndex, 9, nValue)
        school = property(get_school, set_school)
        def get_visual(self):
            CBash.ReadFIDListField.restype = POINTER(c_uint)
            retValue = CBash.ReadFIDListField(self._CollectionIndex, self._ModName, self._recordID, self._subField, self._listIndex, 10)
            if(retValue): return retValue.contents.value
            return None
        def set_visual(self, nValue):
            CBash.SetFIDListFieldUI(self._CollectionIndex, self._ModName, self._recordID, self._subField, self._listIndex, 10, nValue)
        visual = property(get_visual, set_visual)
        def get_flags(self):
            CBash.ReadFIDListField.restype = POINTER(c_ubyte)
            retValue = CBash.ReadFIDListField(self._CollectionIndex, self._ModName, self._recordID, self._subField, self._listIndex, 11)
            if(retValue): return retValue.contents.value
            return None
        def set_flags(self, nValue):
            CBash.SetFIDListFieldUC(self._CollectionIndex, self._ModName, self._recordID, self._subField, self._listIndex, 11, c_ubyte(nValue))
        flags = property(get_flags, set_flags)
        def get_unused1(self):
            numRecords = CBash.GetFIDListArraySize(self._CollectionIndex, self._ModName, self._recordID, self._subField, self._listIndex, 12)
            if(numRecords > 0):
                cRecords = POINTER(c_ubyte * numRecords)()
                CBash.GetFIDListArray(self._CollectionIndex, self._ModName, self._recordID, self._subField, self._listIndex, 12, byref(cRecords))
                return [cRecords.contents[x] for x in range(0, numRecords)]
            return []
        def set_unused1(self, nValue):
            CBash.SetFIDListFieldR(self._CollectionIndex, self._ModName, self._recordID, self._subField, self._listIndex, 12, struct.pack('3B', *nValue), 3)
        unused1 = property(get_unused1, set_unused1)
        def get_full(self):
            CBash.ReadFIDListField.restype = c_char_p
            return CBash.ReadFIDListField(self._CollectionIndex, self._ModName, self._recordID, self._subField, self._listIndex, 13)
        def set_full(self, nValue):
            CBash.SetFIDListFieldStr(self._CollectionIndex, self._ModName, self._recordID, self._subField, self._listIndex, 13, nValue)
        full = property(get_full, set_full)
        def get_IsHostile(self):
            return (self.flags & 0x00000001) != 0
        def set_IsHostile(self, nValue):
            if (nValue == True): self.flags |= 0x00000001
            else: self.flags &= ~0x00000001
        IsHostile = property(get_IsHostile, set_IsHostile)

    def newEffectsElement(self):
        listIndex = CBash.CreateFIDListElement(self._CollectionIndex, self._ModName, self._recordID, 12)
        if(listIndex == -1): return None
        return self.Effect(self._CollectionIndex, self._ModName, self._recordID, 12, listIndex)
    
    def get_full(self):
        CBash.ReadFIDField.restype = c_char_p
        return CBash.ReadFIDField(self._CollectionIndex, self._ModName, self._recordID, 6)
    def set_full(self, nValue):
        CBash.SetFIDFieldStr(self._CollectionIndex, self._ModName, self._recordID, 6, nValue)
    full = property(get_full, set_full)
    def get_itemType(self):
        CBash.ReadFIDField.restype = POINTER(c_uint)
        retValue = CBash.ReadFIDField(self._CollectionIndex, self._ModName, self._recordID, 7)
        if(retValue): return retValue.contents.value
        return None
    def set_itemType(self, nValue):
        CBash.SetFIDFieldUI(self._CollectionIndex, self._ModName, self._recordID, 7, c_uint(nValue))
    itemType = property(get_itemType, set_itemType)
    def get_chargeAmount(self):
        CBash.ReadFIDField.restype = POINTER(c_uint)
        retValue = CBash.ReadFIDField(self._CollectionIndex, self._ModName, self._recordID, 8)
        if(retValue): return retValue.contents.value
        return None
    def set_chargeAmount(self, nValue):
        CBash.SetFIDFieldUI(self._CollectionIndex, self._ModName, self._recordID, 8, c_uint(nValue))
    chargeAmount = property(get_chargeAmount, set_chargeAmount)
    def get_enchantCost(self):
        CBash.ReadFIDField.restype = POINTER(c_uint)
        retValue = CBash.ReadFIDField(self._CollectionIndex, self._ModName, self._recordID, 9)
        if(retValue): return retValue.contents.value
        return None
    def set_enchantCost(self, nValue):
        CBash.SetFIDFieldUI(self._CollectionIndex, self._ModName, self._recordID, 9, c_uint(nValue))
    enchantCost = property(get_enchantCost, set_enchantCost)
    def get_flags(self):
        CBash.ReadFIDField.restype = POINTER(c_ubyte)
        retValue = CBash.ReadFIDField(self._CollectionIndex, self._ModName, self._recordID, 10)
        if(retValue): return retValue.contents.value
        return None
    def set_flags(self, nValue):
        CBash.SetFIDFieldUC(self._CollectionIndex, self._ModName, self._recordID, 10, c_ubyte(nValue))
    flags = property(get_flags, set_flags)
    def get_unused1(self):
        numRecords = CBash.GetFIDFieldArraySize(self._CollectionIndex, self._ModName, self._recordID, 11)
        if(numRecords > 0):
            cRecords = POINTER(c_ubyte * numRecords)()
            CBash.GetFIDFieldArray(self._CollectionIndex, self._ModName, self._recordID, 11, byref(cRecords))
            return [cRecords.contents[x] for x in range(0, numRecords)]
        return []
    def set_unused1(self, nValue):
        CBash.SetFIDFieldR(self._CollectionIndex, self._ModName, self._recordID, 11, struct.pack('3B', *nValue), 3)
    unused1 = property(get_unused1, set_unused1)
    def get_effects(self):
        numRecords = CBash.GetFIDListSize(self._CollectionIndex, self._ModName, self._recordID, 12)
        if(numRecords > 0): return [self.Effect(self._CollectionIndex, self._ModName, self._recordID, 12, x) for x in range(0, numRecords)]
        return []
    def set_effects(self, nEffects):
        diffLength = len(nEffects) - CBash.GetFIDListSize(self._CollectionIndex, self._ModName, self._recordID, 12)
        nValues = [(nVar.name0, nVar.name, nVar.magnitude, nVar.area, nVar.duration, nVar.recipient, nVar.actorValue, nVar.script, nVar.school, nVar.visual, nVar.flags, nVar.unused1, nVar.full) for nVar in nVars]
        while(diffLength < 0):
            CBash.DeleteFIDListElement(self._CollectionIndex, self._ModName, self._recordID, 12)
            diffLength += 1
        while(diffLength > 0):
            CBash.CreateFIDListElement(self._CollectionIndex, self._ModName, self._recordID, 12)
            diffLength -= 1
        for oEffect, nValue in zip(self.effects, nValues):
            oEffect.index, oEffect.unused1, oEffect.flags, oEffect.unused2, oEffect.name = nValue
    effects = property(get_effects, set_effects)
    def get_IsNoAutoCalc(self):
        return (self.flags & 0x00000001) != 0
    def set_IsNoAutoCalc(self, nValue):
        if (nValue == True): self.flags |= 0x00000001
        else: self.flags &= ~0x00000001
    IsNoAutoCalc = property(get_IsNoAutoCalc, set_IsNoAutoCalc)
    def get_IsScroll(self):
        return (self.itemType == 0)
    def set_IsScroll(self, nValue):
        if (nValue == True): self.itemType = 0
        else: self.IsStaff = True
    IsScroll = property(get_IsScroll, set_IsScroll)
    def get_IsStaff(self):
        return (self.itemType == 1)
    def set_IsStaff(self, nValue):
        if (nValue == True): self.itemType = 1
        else: self.IsScroll = True
    IsStaff = property(get_IsStaff, set_IsStaff)
    def get_IsWeapon(self):
        return (self.itemType == 2)
    def set_IsWeapon(self, nValue):
        if (nValue == True): self.itemType = 2
        else: self.IsScroll = True
    IsWeapon = property(get_IsWeapon, set_IsWeapon)
    def get_IsApparel(self):
        return (self.itemType == 3)
    def set_IsApparel(self, nValue):
        if (nValue == True): self.itemType = 3
        else: self.IsScroll = True
    IsApparel = property(get_IsApparel, set_IsApparel)
    
class SPELRecord(BaseRecord):
    def CopyAsOverride(self, targetMod):
        FID = CBash.CopySPELRecord(self._CollectionIndex, self._ModName, self._recordID, targetMod._ModName, c_bool(True))
        if(FID): return SPELRecord(self._CollectionIndex, targetMod._ModName, FID)
        return None
    def CopyAsNew(self, targetMod):
        FID = CBash.CopySPELRecord(self._CollectionIndex, self._ModName, self._recordID, targetMod._ModName, c_bool(False))
        if(FID): return SPELRecord(self._CollectionIndex, targetMod._ModName, FID)
        return None
    class Effect(object):
        def __init__(self, CollectionIndex, ModName, recordID, subField, listIndex):
            self._CollectionIndex = CollectionIndex
            self._ModName = ModName
            self._recordID = recordID
            self._subField = subField
            self._listIndex = listIndex
        ##name0 and name are both are always the same value, so setting one will set both. They're basically aliases
        def get_name0(self):
            CBash.ReadFIDListField.restype = POINTER(c_uint)
            retValue = CBash.ReadFIDListField(self._CollectionIndex, self._ModName, self._recordID, self._subField, self._listIndex, 1)
            if(retValue): return retValue.contents.value
            return None
        def set_name0(self, nValue):
            CBash.SetFIDListFieldUI(self._CollectionIndex, self._ModName, self._recordID, self._subField, self._listIndex, 1, nValue)
        name0 = property(get_name0, set_name0)
        def get_name(self):
            CBash.ReadFIDListField.restype = POINTER(c_uint)
            retValue = CBash.ReadFIDListField(self._CollectionIndex, self._ModName, self._recordID, self._subField, self._listIndex, 2)
            if(retValue): return retValue.contents.value
            return None
        def set_name(self, nValue):
            CBash.SetFIDListFieldUI(self._CollectionIndex, self._ModName, self._recordID, self._subField, self._listIndex, 2, nValue)
        name = property(get_name, set_name)
        def get_magnitude(self):
            CBash.ReadFIDListField.restype = POINTER(c_uint)
            retValue = CBash.ReadFIDListField(self._CollectionIndex, self._ModName, self._recordID, self._subField, self._listIndex, 3)
            if(retValue): return retValue.contents.value
            return None
        def set_magnitude(self, nValue):
            CBash.SetFIDListFieldUI(self._CollectionIndex, self._ModName, self._recordID, self._subField, self._listIndex, 3, nValue)
        magnitude = property(get_magnitude, set_magnitude)
        def get_area(self):
            CBash.ReadFIDListField.restype = POINTER(c_uint)
            retValue = CBash.ReadFIDListField(self._CollectionIndex, self._ModName, self._recordID, self._subField, self._listIndex, 4)
            if(retValue): return retValue.contents.value
            return None
        def set_area(self, nValue):
            CBash.SetFIDListFieldUI(self._CollectionIndex, self._ModName, self._recordID, self._subField, self._listIndex, 4, nValue)
        area = property(get_area, set_area)
        def get_duration(self):
            CBash.ReadFIDListField.restype = POINTER(c_uint)
            retValue = CBash.ReadFIDListField(self._CollectionIndex, self._ModName, self._recordID, self._subField, self._listIndex, 5)
            if(retValue): return retValue.contents.value
            return None
        def set_duration(self, nValue):
            CBash.SetFIDListFieldUI(self._CollectionIndex, self._ModName, self._recordID, self._subField, self._listIndex, 5, nValue)
        duration = property(get_duration, set_duration)
        def get_recipient(self):
            CBash.ReadFIDListField.restype = POINTER(c_uint)
            retValue = CBash.ReadFIDListField(self._CollectionIndex, self._ModName, self._recordID, self._subField, self._listIndex, 6)
            if(retValue): return retValue.contents.value
            return None
        def set_recipient(self, nValue):
            CBash.SetFIDListFieldUI(self._CollectionIndex, self._ModName, self._recordID, self._subField, self._listIndex, 6, nValue)
        recipient = property(get_recipient, set_recipient)
        def get_actorValue(self):
            CBash.ReadFIDListField.restype = POINTER(c_int)
            retValue = CBash.ReadFIDListField(self._CollectionIndex, self._ModName, self._recordID, self._subField, self._listIndex, 7)
            if(retValue): return retValue.contents.value
            return None
        def set_actorValue(self, nValue):
            CBash.SetFIDListFieldI(self._CollectionIndex, self._ModName, self._recordID, self._subField, self._listIndex, 7, nValue)
        actorValue = property(get_actorValue, set_actorValue)
        def get_script(self):
            CBash.ReadFIDListField.restype = POINTER(c_uint)
            retValue = CBash.ReadFIDListField(self._CollectionIndex, self._ModName, self._recordID, self._subField, self._listIndex, 8)
            if(retValue): return retValue.contents.value
            return None
        def set_script(self, nValue):
            CBash.SetFIDListFieldUI(self._CollectionIndex, self._ModName, self._recordID, self._subField, self._listIndex, 8, nValue)
        script = property(get_script, set_script)
        def get_school(self):
            CBash.ReadFIDListField.restype = POINTER(c_uint)
            retValue = CBash.ReadFIDListField(self._CollectionIndex, self._ModName, self._recordID, self._subField, self._listIndex, 9)
            if(retValue): return retValue.contents.value
            return None
        def set_school(self, nValue):
            CBash.SetFIDListFieldUI(self._CollectionIndex, self._ModName, self._recordID, self._subField, self._listIndex, 9, nValue)
        school = property(get_school, set_school)
        def get_visual(self):
            CBash.ReadFIDListField.restype = POINTER(c_uint)
            retValue = CBash.ReadFIDListField(self._CollectionIndex, self._ModName, self._recordID, self._subField, self._listIndex, 10)
            if(retValue): return retValue.contents.value
            return None
        def set_visual(self, nValue):
            CBash.SetFIDListFieldUI(self._CollectionIndex, self._ModName, self._recordID, self._subField, self._listIndex, 10, nValue)
        visual = property(get_visual, set_visual)
        def get_flags(self):
            CBash.ReadFIDListField.restype = POINTER(c_ubyte)
            retValue = CBash.ReadFIDListField(self._CollectionIndex, self._ModName, self._recordID, self._subField, self._listIndex, 11)
            if(retValue): return retValue.contents.value
            return None
        def set_flags(self, nValue):
            CBash.SetFIDListFieldUC(self._CollectionIndex, self._ModName, self._recordID, self._subField, self._listIndex, 11, c_ubyte(nValue))
        flags = property(get_flags, set_flags)
        def get_unused1(self):
            numRecords = CBash.GetFIDListArraySize(self._CollectionIndex, self._ModName, self._recordID, self._subField, self._listIndex, 12)
            if(numRecords > 0):
                cRecords = POINTER(c_ubyte * numRecords)()
                CBash.GetFIDListArray(self._CollectionIndex, self._ModName, self._recordID, self._subField, self._listIndex, 12, byref(cRecords))
                return [cRecords.contents[x] for x in range(0, numRecords)]
            return []
        def set_unused1(self, nValue):
            CBash.SetFIDListFieldR(self._CollectionIndex, self._ModName, self._recordID, self._subField, self._listIndex, 12, struct.pack('3B', *nValue), 3)
        unused1 = property(get_unused1, set_unused1)
        def get_full(self):
            CBash.ReadFIDListField.restype = c_char_p
            return CBash.ReadFIDListField(self._CollectionIndex, self._ModName, self._recordID, self._subField, self._listIndex, 13)
        def set_full(self, nValue):
            CBash.SetFIDListFieldStr(self._CollectionIndex, self._ModName, self._recordID, self._subField, self._listIndex, 13, nValue)
        full = property(get_full, set_full)
        def get_IsHostile(self):
            return (self.flags & 0x00000001) != 0
        def set_IsHostile(self, nValue):
            if (nValue == True): self.flags |= 0x00000001
            else: self.flags &= ~0x00000001
        IsHostile = property(get_IsHostile, set_IsHostile)
    def newEffectsElement(self):
        listIndex = CBash.CreateFIDListElement(self._CollectionIndex, self._ModName, self._recordID, 12)
        if(listIndex == -1): return None
        return self.Effect(self._CollectionIndex, self._ModName, self._recordID, 12, listIndex)
    
    def get_full(self):
        CBash.ReadFIDField.restype = c_char_p
        return CBash.ReadFIDField(self._CollectionIndex, self._ModName, self._recordID, 6)
    def set_full(self, nValue):
        CBash.SetFIDFieldStr(self._CollectionIndex, self._ModName, self._recordID, 6, nValue)
    full = property(get_full, set_full)
    def get_spellType(self):
        CBash.ReadFIDField.restype = POINTER(c_uint)
        retValue = CBash.ReadFIDField(self._CollectionIndex, self._ModName, self._recordID, 7)
        if(retValue): return retValue.contents.value
        return None
    def set_spellType(self, nValue):
        CBash.SetFIDFieldUI(self._CollectionIndex, self._ModName, self._recordID, 7, c_uint(nValue))
    spellType = property(get_spellType, set_spellType)
    def get_cost(self):
        CBash.ReadFIDField.restype = POINTER(c_uint)
        retValue = CBash.ReadFIDField(self._CollectionIndex, self._ModName, self._recordID, 8)
        if(retValue): return retValue.contents.value
        return None
    def set_cost(self, nValue):
        CBash.SetFIDFieldUI(self._CollectionIndex, self._ModName, self._recordID, 8, c_uint(nValue))
    cost = property(get_cost, set_cost)
    def get_level(self):
        CBash.ReadFIDField.restype = POINTER(c_uint)
        retValue = CBash.ReadFIDField(self._CollectionIndex, self._ModName, self._recordID, 9)
        if(retValue): return retValue.contents.value
        return None
    def set_level(self, nValue):
        CBash.SetFIDFieldUI(self._CollectionIndex, self._ModName, self._recordID, 9, c_uint(nValue))
    level = property(get_level, set_level)
    def get_flags(self):
        CBash.ReadFIDField.restype = POINTER(c_ubyte)
        retValue = CBash.ReadFIDField(self._CollectionIndex, self._ModName, self._recordID, 10)
        if(retValue): return retValue.contents.value
        return None
    def set_flags(self, nValue):
        CBash.SetFIDFieldUC(self._CollectionIndex, self._ModName, self._recordID, 10, c_ubyte(nValue))
    flags = property(get_flags, set_flags)
    def get_unused1(self):
        numRecords = CBash.GetFIDFieldArraySize(self._CollectionIndex, self._ModName, self._recordID, 11)
        if(numRecords > 0):
            cRecords = POINTER(c_ubyte * numRecords)()
            CBash.GetFIDFieldArray(self._CollectionIndex, self._ModName, self._recordID, 11, byref(cRecords))
            return [cRecords.contents[x] for x in range(0, numRecords)]
        return []
    def set_unused1(self, nValue):
        CBash.SetFIDFieldR(self._CollectionIndex, self._ModName, self._recordID, 11, struct.pack('3B', *nValue), 3)
    unused1 = property(get_unused1, set_unused1)
    def get_effects(self):
        numRecords = CBash.GetFIDListSize(self._CollectionIndex, self._ModName, self._recordID, 12)
        if(numRecords > 0): return [self.Effect(self._CollectionIndex, self._ModName, self._recordID, 12, x) for x in range(0, numRecords)]
        return []
    def set_effects(self, nEffects):
        diffLength = len(nEffects) - CBash.GetFIDListSize(self._CollectionIndex, self._ModName, self._recordID, 12)
        nValues = [(nVar.name0, nVar.name, nVar.magnitude, nVar.area, nVar.duration, nVar.recipient, nVar.actorValue, nVar.script, nVar.school, nVar.visual, nVar.flags, nVar.unused1, nVar.full) for nVar in nVars]
        while(diffLength < 0):
            CBash.DeleteFIDListElement(self._CollectionIndex, self._ModName, self._recordID, 12)
            diffLength += 1
        while(diffLength > 0):
            CBash.CreateFIDListElement(self._CollectionIndex, self._ModName, self._recordID, 12)
            diffLength -= 1
        for oEffect, nValue in zip(self.effects, nValues):
            oEffect.index, oEffect.unused1, oEffect.flags, oEffect.unused2, oEffect.name = nValue
    effects = property(get_effects, set_effects)
    def get_IsManualCost(self):
        return (self.flags & 0x00000001) != 0
    def set_IsManualCost(self, nValue):
        if (nValue == True): self.flags |= 0x00000001
        else: self.flags &= ~0x00000001
    IsManualCost = property(get_IsManualCost, set_IsManualCost)
    def get_IsStartSpell(self):
        return (self.flags & 0x00000004) != 0
    def set_IsStartSpell(self, nValue):
        if (nValue == True): self.flags |= 0x00000004
        else: self.flags &= ~0x00000004
    IsStartSpell = property(get_IsStartSpell, set_IsStartSpell)
    def get_IsSilenceImmune(self):
        return (self.flags & 0x0000000A) != 0
    def set_IsSilenceImmune(self, nValue):
        if (nValue == True): self.flags |= 0x0000000A
        else: self.flags &= ~0x0000000A
    IsSilenceImmune = property(get_IsSilenceImmune, set_IsSilenceImmune)
    def get_IsAreaEffectIgnoresLOS(self):
        return (self.flags & 0x00000010) != 0
    def set_IsAreaEffectIgnoresLOS(self, nValue):
        if (nValue == True): self.flags |= 0x00000010
        else: self.flags &= ~0x00000010
    IsAEIgnoresLOS = IsAreaEffectIgnoresLOS = property(get_IsAreaEffectIgnoresLOS, set_IsAreaEffectIgnoresLOS)
    def get_IsScriptAlwaysApplies(self):
        return (self.flags & 0x00000020) != 0
    def set_IsScriptAlwaysApplies(self, nValue):
        if (nValue == True): self.flags |= 0x00000020
        else: self.flags &= ~0x00000020
    IsScriptAlwaysApplies = property(get_IsScriptAlwaysApplies, set_IsScriptAlwaysApplies)
    def get_IsDisallowAbsorbReflect(self):
        return (self.flags & 0x00000040) != 0
    def set_IsDisallowAbsorbReflect(self, nValue):
        if (nValue == True): self.flags |= 0x00000040
        else: self.flags &= ~0x00000040
    IsDisallowAbsorb = IsDisallowReflect = IsDisallowAbsorbReflect = property(get_IsDisallowAbsorbReflect, set_IsDisallowAbsorbReflect)
    def get_IsTouchExplodesWOTarget(self):
        return (self.flags & 0x00000080) != 0
    def set_IsTouchExplodesWOTarget(self, nValue):
        if (nValue == True): self.flags |= 0x00000080
        else: self.flags &= ~0x00000080
    IsTouchExplodes = IsTouchExplodesWOTarget = property(get_IsTouchExplodesWOTarget, set_IsTouchExplodesWOTarget)
    def get_IsSpell(self):
        return (self.spellType == 0)
    def set_IsSpell(self, nValue):
        if (nValue == True): self.spellType = 0
        else: self.IsDisease = True
    IsSpell = property(get_IsSpell, set_IsSpell)
    def get_IsDisease(self):
        return (self.spellType == 1)
    def set_IsDisease(self, nValue):
        if (nValue == True): self.spellType = 1
        else: self.IsSpell = True
    IsDisease = property(get_IsDisease, set_IsDisease)
    def get_IsPower(self):
        return (self.spellType == 2)
    def set_IsPower(self, nValue):
        if (nValue == True): self.spellType = 2
        else: self.IsSpell = True
    IsPower = property(get_IsPower, set_IsPower)
    def get_IsLesserPower(self):
        return (self.spellType == 3)
    def set_IsLesserPower(self, nValue):
        if (nValue == True): self.spellType = 3
        else: self.IsSpell = True
    IsLesserPower = property(get_IsLesserPower, set_IsLesserPower)
    def get_IsAbility(self):
        return (self.spellType == 4)
    def set_IsAbility(self, nValue):
        if (nValue == True): self.spellType = 4
        else: self.IsSpell = True
    IsAbility = property(get_IsAbility, set_IsAbility)
    def get_IsPoison(self):
        return (self.spellType == 5)
    def set_IsPoison(self, nValue):
        if (nValue == True): self.spellType = 5
        else: self.IsSpell = True
    IsPoison = property(get_IsPoison, set_IsPoison)
    def get_IsNovice(self):
        return (self.level == 0)
    def set_IsNovice(self, nValue):
        if (nValue == True): self.level = 0
        else: self.IsApprentice = True
    IsNovice = property(get_IsNovice, set_IsNovice)
    def get_IsApprentice(self):
        return (self.level == 1)
    def set_IsApprentice(self, nValue):
        if (nValue == True): self.level = 1
        else: self.IsNovice = True
    IsApprentice = property(get_IsApprentice, set_IsApprentice)
    def get_IsJourneyman(self):
        return (self.level == 2)
    def set_IsJourneyman(self, nValue):
        if (nValue == True): self.level = 2
        else: self.IsNovice = True
    IsJourneyman = property(get_IsJourneyman, set_IsJourneyman)
    def get_IsExpert(self):
        return (self.level == 3)
    def set_IsExpert(self, nValue):
        if (nValue == True): self.level = 3
        else: self.IsNovice = True
    IsExpert = property(get_IsExpert, set_IsExpert)
    def get_IsMaster(self):
        return (self.level == 4)
    def set_IsMaster(self, nValue):
        if (nValue == True): self.level = 4
        else: self.IsNovice = True
    IsMaster = property(get_IsMaster, set_IsMaster)
    
class BSGNRecord(BaseRecord):
    def CopyAsOverride(self, targetMod):
        FID = CBash.CopyBSGNRecord(self._CollectionIndex, self._ModName, self._recordID, targetMod._ModName, c_bool(True))
        if(FID): return BSGNRecord(self._CollectionIndex, targetMod._ModName, FID)
        return None
    def CopyAsNew(self, targetMod):
        FID = CBash.CopyBSGNRecord(self._CollectionIndex, self._ModName, self._recordID, targetMod._ModName, c_bool(False))
        if(FID): return BSGNRecord(self._CollectionIndex, targetMod._ModName, FID)
        return None
    def get_full(self):
        CBash.ReadFIDField.restype = c_char_p
        return CBash.ReadFIDField(self._CollectionIndex, self._ModName, self._recordID, 6)
    def set_full(self, nValue):
        CBash.SetFIDFieldStr(self._CollectionIndex, self._ModName, self._recordID, 6, nValue)
    full = property(get_full, set_full)
    def get_iconPath(self):
        CBash.ReadFIDField.restype = c_char_p
        return CBash.ReadFIDField(self._CollectionIndex, self._ModName, self._recordID, 7)
    def set_iconPath(self, nValue):
        CBash.SetFIDFieldStr(self._CollectionIndex, self._ModName, self._recordID, 7, nValue)
    iconPath = property(get_iconPath, set_iconPath)
    def get_text(self):
        CBash.ReadFIDField.restype = c_char_p
        return CBash.ReadFIDField(self._CollectionIndex, self._ModName, self._recordID, 8)
    def set_text(self, nValue):
        CBash.SetFIDFieldStr(self._CollectionIndex, self._ModName, self._recordID, 8, nValue)
    text = property(get_text, set_text)
    def get_spells(self):
        numRecords = CBash.GetFIDFieldArraySize(self._CollectionIndex, self._ModName, self._recordID, 9)
        if(numRecords > 0):
            cRecords = (POINTER(c_uint) * numRecords)()
            CBash.GetFIDFieldArray(self._CollectionIndex, self._ModName, self._recordID, 9, byref(cRecords))
            return [cRecords[x].contents.value for x in range(0, numRecords)]
        return []
    def set_spells(self, nValue):
        length = len(nValue)
        cRecords = (c_uint * length)(*nValue)
        CBash.SetFIDFieldUIA(self._CollectionIndex, self._ModName, self._recordID, 9, cRecords, length)
    spells = property(get_spells, set_spells)

class ACTIRecord(BaseRecord):
    def CopyAsOverride(self, targetMod):
        FID = CBash.CopyACTIRecord(self._CollectionIndex, self._ModName, self._recordID, targetMod._ModName, c_bool(True))
        if(FID): return ACTIRecord(self._CollectionIndex, targetMod._ModName, FID)
        return None
    def CopyAsNew(self, targetMod):
        FID = CBash.CopyACTIRecord(self._CollectionIndex, self._ModName, self._recordID, targetMod._ModName, c_bool(False))
        if(FID): return ACTIRecord(self._CollectionIndex, targetMod._ModName, FID)
        return None
    def get_full(self):
        CBash.ReadFIDField.restype = c_char_p
        return CBash.ReadFIDField(self._CollectionIndex, self._ModName, self._recordID, 6)
    def set_full(self, nValue):
        CBash.SetFIDFieldStr(self._CollectionIndex, self._ModName, self._recordID, 6, nValue)
    full = property(get_full, set_full)
    def get_modPath(self):
        CBash.ReadFIDField.restype = c_char_p
        return CBash.ReadFIDField(self._CollectionIndex, self._ModName, self._recordID, 7)
    def set_modPath(self, nValue):
        CBash.SetFIDFieldStr(self._CollectionIndex, self._ModName, self._recordID, 7, nValue)
    modPath = property(get_modPath, set_modPath)
    def get_modb(self):
        CBash.ReadFIDField.restype = POINTER(c_float)
        retValue = CBash.ReadFIDField(self._CollectionIndex, self._ModName, self._recordID, 8)
        if(retValue): return retValue.contents.value
        return None
    def set_modb(self, nValue):
        CBash.SetFIDFieldF(self._CollectionIndex, self._ModName, self._recordID, 8, c_float(nValue))
    modb = property(get_modb, set_modb)
    def get_modt_p(self):
        numRecords = CBash.GetFIDFieldArraySize(self._CollectionIndex, self._ModName, self._recordID, 9)
        if(numRecords > 0):
            cRecords = POINTER(c_ubyte * numRecords)()
            CBash.GetFIDFieldArray(self._CollectionIndex, self._ModName, self._recordID, 9, byref(cRecords))
            return [cRecords.contents[x] for x in range(0, numRecords)]
        return []
    def set_modt_p(self, nValue):
        length = len(nValue)
        CBash.SetFIDFieldR(self._CollectionIndex, self._ModName, self._recordID, 9, struct.pack('B' * length, *nValue), length)
    modt_p = property(get_modt_p, set_modt_p)
    def get_script(self):
        CBash.ReadFIDField.restype = POINTER(c_uint)
        retValue = CBash.ReadFIDField(self._CollectionIndex, self._ModName, self._recordID, 10)
        if(retValue): return retValue.contents.value
        return None
    def set_script(self, nValue):
        CBash.SetFIDFieldUI(self._CollectionIndex, self._ModName, self._recordID, 10, c_uint(nValue))
    script = property(get_script, set_script)
    def get_sound(self):
        CBash.ReadFIDField.restype = POINTER(c_uint)
        retValue = CBash.ReadFIDField(self._CollectionIndex, self._ModName, self._recordID, 11)
        if(retValue): return retValue.contents.value
        return None
    def set_sound(self, nValue):
        CBash.SetFIDFieldUI(self._CollectionIndex, self._ModName, self._recordID, 11, c_uint(nValue))
    sound = property(get_sound, set_sound)

class APPARecord(BaseRecord):
    def CopyAsOverride(self, targetMod):
        FID = CBash.CopyAPPARecord(self._CollectionIndex, self._ModName, self._recordID, targetMod._ModName, c_bool(True))
        if(FID): return APPARecord(self._CollectionIndex, targetMod._ModName, FID)
        return None
    def CopyAsNew(self, targetMod):
        FID = CBash.CopyAPPARecord(self._CollectionIndex, self._ModName, self._recordID, targetMod._ModName, c_bool(False))
        if(FID): return APPARecord(self._CollectionIndex, targetMod._ModName, FID)
        return None
    def get_full(self):
        CBash.ReadFIDField.restype = c_char_p
        return CBash.ReadFIDField(self._CollectionIndex, self._ModName, self._recordID, 6)
    def set_full(self, nValue):
        CBash.SetFIDFieldStr(self._CollectionIndex, self._ModName, self._recordID, 6, nValue)
    full = property(get_full, set_full)
    def get_modPath(self):
        CBash.ReadFIDField.restype = c_char_p
        return CBash.ReadFIDField(self._CollectionIndex, self._ModName, self._recordID, 7)
    def set_modPath(self, nValue):
        CBash.SetFIDFieldStr(self._CollectionIndex, self._ModName, self._recordID, 7, nValue)
    modPath = property(get_modPath, set_modPath)
    def get_modb(self):
        CBash.ReadFIDField.restype = POINTER(c_float)
        retValue = CBash.ReadFIDField(self._CollectionIndex, self._ModName, self._recordID, 8)
        if(retValue): return retValue.contents.value
        return None
    def set_modb(self, nValue):
        CBash.SetFIDFieldF(self._CollectionIndex, self._ModName, self._recordID, 8, c_float(nValue))
    modb = property(get_modb, set_modb)
    def get_modt_p(self):
        numRecords = CBash.GetFIDFieldArraySize(self._CollectionIndex, self._ModName, self._recordID, 9)
        if(numRecords > 0):
            cRecords = POINTER(c_ubyte * numRecords)()
            CBash.GetFIDFieldArray(self._CollectionIndex, self._ModName, self._recordID, 9, byref(cRecords))
            return [cRecords.contents[x] for x in range(0, numRecords)]
        return []
    def set_modt_p(self, nValue):
        length = len(nValue)
        CBash.SetFIDFieldR(self._CollectionIndex, self._ModName, self._recordID, 9, struct.pack('B' * length, *nValue), length)
    modt_p = property(get_modt_p, set_modt_p)
    def get_iconPath(self):
        CBash.ReadFIDField.restype = c_char_p
        return CBash.ReadFIDField(self._CollectionIndex, self._ModName, self._recordID, 10)
    def set_iconPath(self, nValue):
        CBash.SetFIDFieldStr(self._CollectionIndex, self._ModName, self._recordID, 10, nValue)
    iconPath = property(get_iconPath, set_iconPath)
    def get_script(self):
        CBash.ReadFIDField.restype = POINTER(c_uint)
        retValue = CBash.ReadFIDField(self._CollectionIndex, self._ModName, self._recordID, 11)
        if(retValue): return retValue.contents.value
        return None
    def set_script(self, nValue):
        CBash.SetFIDFieldUI(self._CollectionIndex, self._ModName, self._recordID, 11, c_uint(nValue))
    script = property(get_script, set_script)
    def get_apparatus(self):
        CBash.ReadFIDField.restype = POINTER(c_ubyte)
        retValue = CBash.ReadFIDField(self._CollectionIndex, self._ModName, self._recordID, 12)
        if(retValue): return retValue.contents.value
        return None
    def set_apparatus(self, nValue):
        CBash.SetFIDFieldUC(self._CollectionIndex, self._ModName, self._recordID, 12, c_ubyte(nValue))
    apparatus = property(get_apparatus, set_apparatus)
    def get_value(self):
        CBash.ReadFIDField.restype = POINTER(c_uint)
        retValue = CBash.ReadFIDField(self._CollectionIndex, self._ModName, self._recordID, 13)
        if(retValue): return retValue.contents.value
        return None
    def set_value(self, nValue):
        CBash.SetFIDFieldUI(self._CollectionIndex, self._ModName, self._recordID, 13, c_uint(nValue))
    value = property(get_value, set_value)
    def get_weight(self):
        CBash.ReadFIDField.restype = POINTER(c_float)
        retValue = CBash.ReadFIDField(self._CollectionIndex, self._ModName, self._recordID, 14)
        if(retValue): return retValue.contents.value
        return None
    def set_weight(self, nValue):
        CBash.SetFIDFieldF(self._CollectionIndex, self._ModName, self._recordID, 14, c_float(nValue))
    weight = property(get_weight, set_weight)
    def get_quality(self):
        CBash.ReadFIDField.restype = POINTER(c_float)
        retValue = CBash.ReadFIDField(self._CollectionIndex, self._ModName, self._recordID, 15)
        if(retValue): return retValue.contents.value
        return None
    def set_quality(self, nValue):
        CBash.SetFIDFieldF(self._CollectionIndex, self._ModName, self._recordID, 15, c_float(nValue))
    quality = property(get_quality, set_quality)
    def get_IsMortarPestle(self):
        return (self.apparatus == 0)
    def set_IsMortarPestle(self, nValue):
        if (nValue == True): self.apparatus = 0
        else: self.IsAlembic = True
    IsMortarPestle = property(get_IsMortarPestle, set_IsMortarPestle)
    def get_IsAlembic(self):
        return (self.apparatus == 1)
    def set_IsAlembic(self, nValue):
        if (nValue == True): self.apparatus = 1
        else: self.IsMortarPestle = True
    IsAlembic = property(get_IsAlembic, set_IsAlembic)
    def get_IsCalcinator(self):
        return (self.apparatus == 2)
    def set_IsCalcinator(self, nValue):
        if (nValue == True): self.apparatus = 2
        else: self.IsMortarPestle = True
    IsCalcinator = property(get_IsCalcinator, set_IsCalcinator)
    def get_IsRetort(self):
        return (self.apparatus == 3)
    def set_IsRetort(self, nValue):
        if (nValue == True): self.apparatus = 3
        else: self.IsMortarPestle = True
    IsRetort = property(get_IsRetort, set_IsRetort)

class ARMORecord(BaseRecord):
    def CopyAsOverride(self, targetMod):
        FID = CBash.CopyARMORecord(self._CollectionIndex, self._ModName, self._recordID, targetMod._ModName, c_bool(True))
        if(FID): return ARMORecord(self._CollectionIndex, targetMod._ModName, FID)
        return None
    def CopyAsNew(self, targetMod):
        FID = CBash.CopyARMORecord(self._CollectionIndex, self._ModName, self._recordID, targetMod._ModName, c_bool(False))
        if(FID): return ARMORecord(self._CollectionIndex, targetMod._ModName, FID)
        return None
    class Model(object):
        def __init__(self, CollectionIndex, ModName, recordID, listIndex):
            self._CollectionIndex = CollectionIndex
            self._ModName = ModName
            self._recordID = recordID
            self._listIndex = listIndex
        def get_modPath(self):
            CBash.ReadFIDField.restype = c_char_p
            return CBash.ReadFIDField(self._CollectionIndex, self._ModName, self._recordID, self._listIndex)
        def set_modPath(self, nValue):
            CBash.SetFIDFieldStr(self._CollectionIndex, self._ModName, self._recordID, self._listIndex, nValue)
        modPath = property(get_modPath, set_modPath)
        def get_modb(self):
            CBash.ReadFIDField.restype = POINTER(c_float)
            retValue = CBash.ReadFIDField(self._CollectionIndex, self._ModName, self._recordID, self._listIndex + 1)
            if(retValue): return retValue.contents.value
            return None
        def set_modb(self, nValue):
            CBash.SetFIDFieldF(self._CollectionIndex, self._ModName, self._recordID, self._listIndex + 1, c_float(nValue))
        modb = property(get_modb, set_modb)
        def get_modt_p(self):
            numRecords = CBash.GetFIDFieldArraySize(self._CollectionIndex, self._ModName, self._recordID, self._listIndex + 2)
            if(numRecords > 0):
                cRecords = POINTER(c_ubyte * numRecords)()
                CBash.GetFIDFieldArray(self._CollectionIndex, self._ModName, self._recordID, self._listIndex + 2, byref(cRecords))
                return [cRecords.contents[x] for x in range(0, numRecords)]
            return []
        def set_modt_p(self, nValue):
            length = len(nValue)
            CBash.SetFIDFieldR(self._CollectionIndex, self._ModName, self._recordID, self._listIndex + 2, struct.pack('B' * length, *nValue), length)
        modt_p = property(get_modt_p, set_modt_p)   
    def get_full(self):
        CBash.ReadFIDField.restype = c_char_p
        return CBash.ReadFIDField(self._CollectionIndex, self._ModName, self._recordID, 6)
    def set_full(self, nValue):
        CBash.SetFIDFieldStr(self._CollectionIndex, self._ModName, self._recordID, 6, nValue)
    full = property(get_full, set_full)
    def get_script(self):
        CBash.ReadFIDField.restype = POINTER(c_uint)
        retValue = CBash.ReadFIDField(self._CollectionIndex, self._ModName, self._recordID, 7)
        if(retValue): return retValue.contents.value
        return None
    def set_script(self, nValue):
        CBash.SetFIDFieldUI(self._CollectionIndex, self._ModName, self._recordID, 7, c_uint(nValue))
    script = property(get_script, set_script)
    def get_enchantment(self):
        CBash.ReadFIDField.restype = POINTER(c_uint)
        retValue = CBash.ReadFIDField(self._CollectionIndex, self._ModName, self._recordID, 8)
        if(retValue): return retValue.contents.value
        return None
    def set_enchantment(self, nValue):
        CBash.SetFIDFieldUI(self._CollectionIndex, self._ModName, self._recordID, 8, c_uint(nValue))
    enchantment = property(get_enchantment, set_enchantment)
    def get_enchantPoints(self):
        CBash.ReadFIDField.restype = POINTER(c_ushort)
        retValue = CBash.ReadFIDField(self._CollectionIndex, self._ModName, self._recordID, 9)
        if(retValue): return retValue.contents.value
        return None
    def set_enchantPoints(self, nValue):
        CBash.SetFIDFieldUS(self._CollectionIndex, self._ModName, self._recordID, 9, c_ushort(nValue))
    enchantPoints = property(get_enchantPoints, set_enchantPoints)
    def get_flags(self):
        CBash.ReadFIDField.restype = POINTER(c_uint)
        retValue = CBash.ReadFIDField(self._CollectionIndex, self._ModName, self._recordID, 10)
        if(retValue): return retValue.contents.value
        return None
    def set_flags(self, nValue):
        CBash.SetFIDFieldUI(self._CollectionIndex, self._ModName, self._recordID, 10, c_uint(nValue))
    flags = property(get_flags, set_flags)
    @property
    def maleBody(self):
        return self.Model(self._CollectionIndex, self._ModName, self._recordID, 11)
    @property
    def maleWorld(self):
        return self.Model(self._CollectionIndex, self._ModName, self._recordID, 14)
    def get_maleIconPath(self):
        CBash.ReadFIDField.restype = c_char_p
        return CBash.ReadFIDField(self._CollectionIndex, self._ModName, self._recordID, 17)
    def set_maleIconPath(self, nValue):
        CBash.SetFIDFieldStr(self._CollectionIndex, self._ModName, self._recordID, 17, nValue)
    maleIconPath = property(get_maleIconPath, set_maleIconPath)
    @property
    def femaleBody(self):
        return self.Model(self._CollectionIndex, self._ModName, self._recordID, 18)
    @property
    def femaleWorld(self):
        return self.Model(self._CollectionIndex, self._ModName, self._recordID, 21)
    def get_femaleIconPath(self):
        CBash.ReadFIDField.restype = c_char_p
        return CBash.ReadFIDField(self._CollectionIndex, self._ModName, self._recordID, 24)
    def set_femaleIconPath(self, nValue):
        CBash.SetFIDFieldStr(self._CollectionIndex, self._ModName, self._recordID, 24, nValue)
    femaleIconPath = property(get_femaleIconPath, set_femaleIconPath)
    def get_strength(self):
        CBash.ReadFIDField.restype = POINTER(c_ushort)
        retValue = CBash.ReadFIDField(self._CollectionIndex, self._ModName, self._recordID, 25)
        if(retValue): return retValue.contents.value
        return None
    def set_strength(self, nValue):
        CBash.SetFIDFieldUS(self._CollectionIndex, self._ModName, self._recordID, 25, c_ushort(nValue))
    strength = property(get_strength, set_strength)
    def get_value(self):
        CBash.ReadFIDField.restype = POINTER(c_uint)
        retValue = CBash.ReadFIDField(self._CollectionIndex, self._ModName, self._recordID, 26)
        if(retValue): return retValue.contents.value
        return None
    def set_value(self, nValue):
        CBash.SetFIDFieldUI(self._CollectionIndex, self._ModName, self._recordID, 26, c_uint(nValue))
    value = property(get_value, set_value)
    def get_health(self):
        CBash.ReadFIDField.restype = POINTER(c_uint)
        retValue = CBash.ReadFIDField(self._CollectionIndex, self._ModName, self._recordID, 27)
        if(retValue): return retValue.contents.value
        return None
    def set_health(self, nValue):
        CBash.SetFIDFieldUI(self._CollectionIndex, self._ModName, self._recordID, 27, c_uint(nValue))
    health = property(get_health, set_health)
    def get_weight(self):
        CBash.ReadFIDField.restype = POINTER(c_float)
        retValue = CBash.ReadFIDField(self._CollectionIndex, self._ModName, self._recordID, 28)
        if(retValue): return retValue.contents.value
        return None
    def set_weight(self, nValue):
        CBash.SetFIDFieldF(self._CollectionIndex, self._ModName, self._recordID, 28, c_float(nValue))
    weight = property(get_weight, set_weight)
    def get_IsHead(self):
        return (self.flags & 0x00000001) != 0
    def set_IsHead(self, nValue):
        if (nValue == True): self.flags |= 0x00000001
        else: self.flags &= ~0x00000001
    IsHead = property(get_IsHead, set_IsHead)
    def get_IsHair(self):
        return (self.flags & 0x00000002) != 0
    def set_IsHair(self, nValue):
        if (nValue == True): self.flags |= 0x00000002
        else: self.flags &= ~0x00000002
    IsHair = property(get_IsHair, set_IsHair)
    def get_IsUpperBody(self):
        return (self.flags & 0x00000004) != 0
    def set_IsUpperBody(self, nValue):
        if (nValue == True): self.flags |= 0x00000004
        else: self.flags &= ~0x00000004
    IsUpperBody = property(get_IsUpperBody, set_IsUpperBody)
    def get_IsLowerBody(self):
        return (self.flags & 0x00000008) != 0
    def set_IsLowerBody(self, nValue):
        if (nValue == True): self.flags |= 0x00000008
        else: self.flags &= ~0x00000008
    IsLowerBody = property(get_IsLowerBody, set_IsLowerBody)
    def get_IsHand(self):
        return (self.flags & 0x00000010) != 0
    def set_IsHand(self, nValue):
        if (nValue == True): self.flags |= 0x00000010
        else: self.flags &= ~0x00000010
    IsHand = property(get_IsHand, set_IsHand)
    def get_IsFoot(self):
        return (self.flags & 0x00000020) != 0
    def set_IsFoot(self, nValue):
        if (nValue == True): self.flags |= 0x00000020
        else: self.flags &= ~0x00000020
    IsFoot = property(get_IsFoot, set_IsFoot)
    def get_IsRightRing(self):
        return (self.flags & 0x00000040) != 0
    def set_IsRightRing(self, nValue):
        if (nValue == True): self.flags |= 0x00000040
        else: self.flags &= ~0x00000040
    IsRightRing = property(get_IsRightRing, set_IsRightRing)
    def get_IsLeftRing(self):
        return (self.flags & 0x00000080) != 0
    def set_IsLeftRing(self, nValue):
        if (nValue == True): self.flags |= 0x00000080
        else: self.flags &= ~0x00000080
    IsLeftRing = property(get_IsLeftRing, set_IsLeftRing)
    def get_IsAmulet(self):
        return (self.flags & 0x00000100) != 0
    def set_IsAmulet(self, nValue):
        if (nValue == True): self.flags |= 0x00000100
        else: self.flags &= ~0x00000100
    IsAmulet = property(get_IsAmulet, set_IsAmulet)
    def get_IsWeapon(self):
        return (self.flags & 0x00000200) != 0
    def set_IsWeapon(self, nValue):
        if (nValue == True): self.flags |= 0x00000200
        else: self.flags &= ~0x00000200
    IsWeapon = property(get_IsWeapon, set_IsWeapon)
    def get_IsBackWeapon(self):
        return (self.flags & 0x00000400) != 0
    def set_IsBackWeapon(self, nValue):
        if (nValue == True): self.flags |= 0x00000400
        else: self.flags &= ~0x00000400
    IsBackWeapon = property(get_IsBackWeapon, set_IsBackWeapon)
    def get_IsSideWeapon(self):
        return (self.flags & 0x00000800) != 0
    def set_IsSideWeapon(self, nValue):
        if (nValue == True): self.flags |= 0x00000800
        else: self.flags &= ~0x00000800
    IsSideWeapon = property(get_IsSideWeapon, set_IsSideWeapon)
    def get_IsQuiver(self):
        return (self.flags & 0x00001000) != 0
    def set_IsQuiver(self, nValue):
        if (nValue == True): self.flags |= 0x00001000
        else: self.flags &= ~0x00001000
    IsQuiver = property(get_IsQuiver, set_IsQuiver)
    def get_IsShield(self):
        return (self.flags & 0x00002000) != 0
    def set_IsShield(self, nValue):
        if (nValue == True): self.flags |= 0x00002000
        else: self.flags &= ~0x00002000
    IsShield = property(get_IsShield, set_IsShield)
    def get_IsTorch(self):
        return (self.flags & 0x00004000) != 0
    def set_IsTorch(self, nValue):
        if (nValue == True): self.flags |= 0x00004000
        else: self.flags &= ~0x00004000
    IsTorch = property(get_IsTorch, set_IsTorch)
    def get_IsTail(self):
        return (self.flags & 0x00008000) != 0
    def set_IsTail(self, nValue):
        if (nValue == True): self.flags |= 0x00008000
        else: self.flags &= ~0x00008000
    IsTail = property(get_IsTail, set_IsTail)
    def get_IsHideRings(self):
        return (self.flags & 0x00010000) != 0
    def set_IsHideRings(self, nValue):
        if (nValue == True): self.flags |= 0x00010000
        else: self.flags &= ~0x00010000
    IsHideRings = property(get_IsHideRings, set_IsHideRings)
    def get_IsHideAmulets(self):
        return (self.flags & 0x00020000) != 0
    def set_IsHideAmulets(self, nValue):
        if (nValue == True): self.flags |= 0x00020000
        else: self.flags &= ~0x00020000
    IsHideAmulets = property(get_IsHideAmulets, set_IsHideAmulets)
    def get_IsNonPlayable(self):
        return (self.flags & 0x00040000) != 0
    def set_IsNonPlayable(self, nValue):
        if (nValue == True): self.flags |= 0x00040000
        else: self.flags &= ~0x00040000
    IsNonPlayable = property(get_IsNonPlayable, set_IsNonPlayable)
    def get_IsHeavyArmor(self):
        return (self.flags & 0x00080000) != 0
    def set_IsHeavyArmor(self, nValue):
        if (nValue == True): self.flags |= 0x00080000
        else: self.flags &= ~0x00080000
    IsHeavyArmor = property(get_IsHeavyArmor, set_IsHeavyArmor)

class BOOKRecord(BaseRecord):
    def CopyAsOverride(self, targetMod):
        FID = CBash.CopyBOOKRecord(self._CollectionIndex, self._ModName, self._recordID, targetMod._ModName, c_bool(True))
        if(FID): return BOOKRecord(self._CollectionIndex, targetMod._ModName, FID)
        return None
    def CopyAsNew(self, targetMod):
        FID = CBash.CopyBOOKRecord(self._CollectionIndex, self._ModName, self._recordID, targetMod._ModName, c_bool(False))
        if(FID): return BOOKRecord(self._CollectionIndex, targetMod._ModName, FID)
        return None
    def get_full(self):
        CBash.ReadFIDField.restype = c_char_p
        return CBash.ReadFIDField(self._CollectionIndex, self._ModName, self._recordID, 6)
    def set_full(self, nValue):
        CBash.SetFIDFieldStr(self._CollectionIndex, self._ModName, self._recordID, 6, nValue)
    full = property(get_full, set_full)
    def get_modPath(self):
        CBash.ReadFIDField.restype = c_char_p
        return CBash.ReadFIDField(self._CollectionIndex, self._ModName, self._recordID, 7)
    def set_modPath(self, nValue):
        CBash.SetFIDFieldStr(self._CollectionIndex, self._ModName, self._recordID, 7, nValue)
    modPath = property(get_modPath, set_modPath)
    def get_modb(self):
        CBash.ReadFIDField.restype = POINTER(c_float)
        retValue = CBash.ReadFIDField(self._CollectionIndex, self._ModName, self._recordID, 8)
        if(retValue): return retValue.contents.value
        return None
    def set_modb(self, nValue):
        CBash.SetFIDFieldF(self._CollectionIndex, self._ModName, self._recordID, 8, c_float(nValue))
    modb = property(get_modb, set_modb)
    def get_modt_p(self):
        numRecords = CBash.GetFIDFieldArraySize(self._CollectionIndex, self._ModName, self._recordID, 9)
        if(numRecords > 0):
            cRecords = POINTER(c_ubyte * numRecords)()
            CBash.GetFIDFieldArray(self._CollectionIndex, self._ModName, self._recordID, 9, byref(cRecords))
            return [cRecords.contents[x] for x in range(0, numRecords)]
        return []
    def set_modt_p(self, nValue):
        length = len(nValue)
        CBash.SetFIDFieldR(self._CollectionIndex, self._ModName, self._recordID, 9, struct.pack('B' * length, *nValue), length)
    modt_p = property(get_modt_p, set_modt_p)
    def get_iconPath(self):
        CBash.ReadFIDField.restype = c_char_p
        return CBash.ReadFIDField(self._CollectionIndex, self._ModName, self._recordID, 10)
    def set_iconPath(self, nValue):
        CBash.SetFIDFieldStr(self._CollectionIndex, self._ModName, self._recordID, 10, nValue)
    iconPath = property(get_iconPath, set_iconPath)
    def get_text(self):
        CBash.ReadFIDField.restype = c_char_p
        return CBash.ReadFIDField(self._CollectionIndex, self._ModName, self._recordID, 11)
    def set_text(self, nValue):
        CBash.SetFIDFieldStr(self._CollectionIndex, self._ModName, self._recordID, 11, nValue)
    text = property(get_text, set_text)
    def get_script(self):
        CBash.ReadFIDField.restype = POINTER(c_uint)
        retValue = CBash.ReadFIDField(self._CollectionIndex, self._ModName, self._recordID, 12)
        if(retValue): return retValue.contents.value
        return None
    def set_script(self, nValue):
        CBash.SetFIDFieldUI(self._CollectionIndex, self._ModName, self._recordID, 12, c_uint(nValue))
    script = property(get_script, set_script)
    def get_enchantment(self):
        CBash.ReadFIDField.restype = POINTER(c_uint)
        retValue = CBash.ReadFIDField(self._CollectionIndex, self._ModName, self._recordID, 13)
        if(retValue): return retValue.contents.value
        return None
    def set_enchantment(self, nValue):
        CBash.SetFIDFieldUI(self._CollectionIndex, self._ModName, self._recordID, 13, c_uint(nValue))
    enchantment = property(get_enchantment, set_enchantment)
    def get_enchantPoints(self):
        CBash.ReadFIDField.restype = POINTER(c_ushort)
        retValue = CBash.ReadFIDField(self._CollectionIndex, self._ModName, self._recordID, 14)
        if(retValue): return retValue.contents.value
        return None
    def set_enchantPoints(self, nValue):
        CBash.SetFIDFieldUS(self._CollectionIndex, self._ModName, self._recordID, 14, c_ushort(nValue))
    enchantPoints = property(get_enchantPoints, set_enchantPoints)
    def get_flags(self):
        CBash.ReadFIDField.restype = POINTER(c_ubyte)
        retValue = CBash.ReadFIDField(self._CollectionIndex, self._ModName, self._recordID, 15)
        if(retValue): return retValue.contents.value
        return None
    def set_flags(self, nValue):
        CBash.SetFIDFieldUC(self._CollectionIndex, self._ModName, self._recordID, 15, c_ubyte(nValue))
    flags = property(get_flags, set_flags)
    def get_teaches(self):
        CBash.ReadFIDField.restype = POINTER(c_byte)
        retValue = CBash.ReadFIDField(self._CollectionIndex, self._ModName, self._recordID, 16)
        if(retValue): return retValue.contents.value
        return None
    def set_teaches(self, nValue):
        CBash.SetFIDFieldUC(self._CollectionIndex, self._ModName, self._recordID, 16, c_byte(nValue))
    teaches = property(get_teaches, set_teaches)
    def get_value(self):
        CBash.ReadFIDField.restype = POINTER(c_uint)
        retValue = CBash.ReadFIDField(self._CollectionIndex, self._ModName, self._recordID, 17)
        if(retValue): return retValue.contents.value
        return None
    def set_value(self, nValue):
        CBash.SetFIDFieldUI(self._CollectionIndex, self._ModName, self._recordID, 17, c_uint(nValue))
    value = property(get_value, set_value)
    def get_weight(self):
        CBash.ReadFIDField.restype = POINTER(c_float)
        retValue = CBash.ReadFIDField(self._CollectionIndex, self._ModName, self._recordID, 18)
        if(retValue): return retValue.contents.value
        return None
    def set_weight(self, nValue):
        CBash.SetFIDFieldF(self._CollectionIndex, self._ModName, self._recordID, 18, c_float(nValue))
    weight = property(get_weight, set_weight)
    def get_IsScroll(self):
        return (self.flags & 0x00000001) != 0
    def set_IsScroll(self, nValue):
        if (nValue == True): self.flags |= 0x00000001
        else: self.flags &= ~0x00000001
    IsScroll = property(get_IsScroll, set_IsScroll)
    def get_IsFixed(self):
        return (self.flags & 0x00000002) != 0
    def set_IsFixed(self, nValue):
        if (nValue == True): self.flags |= 0x00000002
        else: self.flags &= ~0x00000002
    IsFixed = property(get_IsFixed, set_IsFixed)

class CLOTRecord(BaseRecord):
    def CopyAsOverride(self, targetMod):
        FID = CBash.CopyCLOTRecord(self._CollectionIndex, self._ModName, self._recordID, targetMod._ModName, c_bool(True))
        if(FID): return CLOTRecord(self._CollectionIndex, targetMod._ModName, FID)
        return None
    def CopyAsNew(self, targetMod):
        FID = CBash.CopyCLOTRecord(self._CollectionIndex, self._ModName, self._recordID, targetMod._ModName, c_bool(False))
        if(FID): return CLOTRecord(self._CollectionIndex, targetMod._ModName, FID)
        return None
    class Model(object):
        def __init__(self, CollectionIndex, ModName, recordID, listIndex):
            self._CollectionIndex = CollectionIndex
            self._ModName = ModName
            self._recordID = recordID
            self._listIndex = listIndex
        def get_modPath(self):
            CBash.ReadFIDField.restype = c_char_p
            return CBash.ReadFIDField(self._CollectionIndex, self._ModName, self._recordID, self._listIndex)
        def set_modPath(self, nValue):
            CBash.SetFIDFieldStr(self._CollectionIndex, self._ModName, self._recordID, self._listIndex, nValue)
        modPath = property(get_modPath, set_modPath)
        def get_modb(self):
            CBash.ReadFIDField.restype = POINTER(c_float)
            retValue = CBash.ReadFIDField(self._CollectionIndex, self._ModName, self._recordID, self._listIndex + 1)
            if(retValue): return retValue.contents.value
            return None
        def set_modb(self, nValue):
            CBash.SetFIDFieldF(self._CollectionIndex, self._ModName, self._recordID, self._listIndex + 1, c_float(nValue))
        modb = property(get_modb, set_modb)
        def get_modt_p(self):
            numRecords = CBash.GetFIDFieldArraySize(self._CollectionIndex, self._ModName, self._recordID, self._listIndex + 2)
            if(numRecords > 0):
                cRecords = POINTER(c_ubyte * numRecords)()
                CBash.GetFIDFieldArray(self._CollectionIndex, self._ModName, self._recordID, self._listIndex + 2, byref(cRecords))
                return [cRecords.contents[x] for x in range(0, numRecords)]
            return []
        def set_modt_p(self, nValue):
            length = len(nValue)
            CBash.SetFIDFieldR(self._CollectionIndex, self._ModName, self._recordID, self._listIndex + 2, struct.pack('B' * length, *nValue), length)
        modt_p = property(get_modt_p, set_modt_p)   
    def get_full(self):
        CBash.ReadFIDField.restype = c_char_p
        return CBash.ReadFIDField(self._CollectionIndex, self._ModName, self._recordID, 6)
    def set_full(self, nValue):
        CBash.SetFIDFieldStr(self._CollectionIndex, self._ModName, self._recordID, 6, nValue)
    full = property(get_full, set_full)
    def get_script(self):
        CBash.ReadFIDField.restype = POINTER(c_uint)
        retValue = CBash.ReadFIDField(self._CollectionIndex, self._ModName, self._recordID, 7)
        if(retValue): return retValue.contents.value
        return None
    def set_script(self, nValue):
        CBash.SetFIDFieldUI(self._CollectionIndex, self._ModName, self._recordID, 7, c_uint(nValue))
    script = property(get_script, set_script)
    def get_enchantment(self):
        CBash.ReadFIDField.restype = POINTER(c_uint)
        retValue = CBash.ReadFIDField(self._CollectionIndex, self._ModName, self._recordID, 8)
        if(retValue): return retValue.contents.value
        return None
    def set_enchantment(self, nValue):
        CBash.SetFIDFieldUI(self._CollectionIndex, self._ModName, self._recordID, 8, c_uint(nValue))
    enchantment = property(get_enchantment, set_enchantment)
    def get_enchantPoints(self):
        CBash.ReadFIDField.restype = POINTER(c_ushort)
        retValue = CBash.ReadFIDField(self._CollectionIndex, self._ModName, self._recordID, 9)
        if(retValue): return retValue.contents.value
        return None
    def set_enchantPoints(self, nValue):
        CBash.SetFIDFieldUS(self._CollectionIndex, self._ModName, self._recordID, 9, c_ushort(nValue))
    enchantPoints = property(get_enchantPoints, set_enchantPoints)
    def get_flags(self):
        CBash.ReadFIDField.restype = POINTER(c_uint)
        retValue = CBash.ReadFIDField(self._CollectionIndex, self._ModName, self._recordID, 10)
        if(retValue): return retValue.contents.value
        return None
    def set_flags(self, nValue):
        CBash.SetFIDFieldUI(self._CollectionIndex, self._ModName, self._recordID, 10, c_uint(nValue))
    flags = property(get_flags, set_flags)
    @property
    def maleBody(self):
        return self.Model(self._CollectionIndex, self._ModName, self._recordID, 11)
    @property
    def maleWorld(self):
        return self.Model(self._CollectionIndex, self._ModName, self._recordID, 14)
    def get_maleIconPath(self):
        CBash.ReadFIDField.restype = c_char_p
        return CBash.ReadFIDField(self._CollectionIndex, self._ModName, self._recordID, 17)
    def set_maleIconPath(self, nValue):
        CBash.SetFIDFieldStr(self._CollectionIndex, self._ModName, self._recordID, 17, nValue)
    maleIconPath = property(get_maleIconPath, set_maleIconPath)
    @property
    def femaleBody(self):
        return self.Model(self._CollectionIndex, self._ModName, self._recordID, 18)
    @property
    def femaleWorld(self):
        return self.Model(self._CollectionIndex, self._ModName, self._recordID, 21)
    def get_femaleIconPath(self):
        CBash.ReadFIDField.restype = c_char_p
        return CBash.ReadFIDField(self._CollectionIndex, self._ModName, self._recordID, 24)
    def set_femaleIconPath(self, nValue):
        CBash.SetFIDFieldStr(self._CollectionIndex, self._ModName, self._recordID, 24, nValue)
    femaleIconPath = property(get_femaleIconPath, set_femaleIconPath)
    def get_value(self):
        CBash.ReadFIDField.restype = POINTER(c_uint)
        retValue = CBash.ReadFIDField(self._CollectionIndex, self._ModName, self._recordID, 25)
        if(retValue): return retValue.contents.value
        return None
    def set_value(self, nValue):
        CBash.SetFIDFieldUI(self._CollectionIndex, self._ModName, self._recordID, 25, c_uint(nValue))
    value = property(get_value, set_value)
    def get_weight(self):
        CBash.ReadFIDField.restype = POINTER(c_float)
        retValue = CBash.ReadFIDField(self._CollectionIndex, self._ModName, self._recordID, 26)
        if(retValue): return retValue.contents.value
        return None
    def set_weight(self, nValue):
        CBash.SetFIDFieldF(self._CollectionIndex, self._ModName, self._recordID, 26, c_float(nValue))
    weight = property(get_weight, set_weight)
    def get_IsHead(self):
        return (self.flags & 0x00000001) != 0
    def set_IsHead(self, nValue):
        if (nValue == True): self.flags |= 0x00000001
        else: self.flags &= ~0x00000001
    IsHead = property(get_IsHead, set_IsHead)
    def get_IsHair(self):
        return (self.flags & 0x00000002) != 0
    def set_IsHair(self, nValue):
        if (nValue == True): self.flags |= 0x00000002
        else: self.flags &= ~0x00000002
    IsHair = property(get_IsHair, set_IsHair)
    def get_IsUpperBody(self):
        return (self.flags & 0x00000004) != 0
    def set_IsUpperBody(self, nValue):
        if (nValue == True): self.flags |= 0x00000004
        else: self.flags &= ~0x00000004
    IsUpperBody = property(get_IsUpperBody, set_IsUpperBody)
    def get_IsLowerBody(self):
        return (self.flags & 0x00000008) != 0
    def set_IsLowerBody(self, nValue):
        if (nValue == True): self.flags |= 0x00000008
        else: self.flags &= ~0x00000008
    IsLowerBody = property(get_IsLowerBody, set_IsLowerBody)
    def get_IsHand(self):
        return (self.flags & 0x00000010) != 0
    def set_IsHand(self, nValue):
        if (nValue == True): self.flags |= 0x00000010
        else: self.flags &= ~0x00000010
    IsHand = property(get_IsHand, set_IsHand)
    def get_IsFoot(self):
        return (self.flags & 0x00000020) != 0
    def set_IsFoot(self, nValue):
        if (nValue == True): self.flags |= 0x00000020
        else: self.flags &= ~0x00000020
    IsFoot = property(get_IsFoot, set_IsFoot)
    def get_IsRightRing(self):
        return (self.flags & 0x00000040) != 0
    def set_IsRightRing(self, nValue):
        if (nValue == True): self.flags |= 0x00000040
        else: self.flags &= ~0x00000040
    IsRightRing = property(get_IsRightRing, set_IsRightRing)
    def get_IsLeftRing(self):
        return (self.flags & 0x00000080) != 0
    def set_IsLeftRing(self, nValue):
        if (nValue == True): self.flags |= 0x00000080
        else: self.flags &= ~0x00000080
    IsLeftRing = property(get_IsLeftRing, set_IsLeftRing)
    def get_IsAmulet(self):
        return (self.flags & 0x00000100) != 0
    def set_IsAmulet(self, nValue):
        if (nValue == True): self.flags |= 0x00000100
        else: self.flags &= ~0x00000100
    IsAmulet = property(get_IsAmulet, set_IsAmulet)
    def get_IsWeapon(self):
        return (self.flags & 0x00000200) != 0
    def set_IsWeapon(self, nValue):
        if (nValue == True): self.flags |= 0x00000200
        else: self.flags &= ~0x00000200
    IsWeapon = property(get_IsWeapon, set_IsWeapon)
    def get_IsBackWeapon(self):
        return (self.flags & 0x00000400) != 0
    def set_IsBackWeapon(self, nValue):
        if (nValue == True): self.flags |= 0x00000400
        else: self.flags &= ~0x00000400
    IsBackWeapon = property(get_IsBackWeapon, set_IsBackWeapon)
    def get_IsSideWeapon(self):
        return (self.flags & 0x00000800) != 0
    def set_IsSideWeapon(self, nValue):
        if (nValue == True): self.flags |= 0x00000800
        else: self.flags &= ~0x00000800
    IsSideWeapon = property(get_IsSideWeapon, set_IsSideWeapon)
    def get_IsQuiver(self):
        return (self.flags & 0x00001000) != 0
    def set_IsQuiver(self, nValue):
        if (nValue == True): self.flags |= 0x00001000
        else: self.flags &= ~0x00001000
    IsQuiver = property(get_IsQuiver, set_IsQuiver)
    def get_IsShield(self):
        return (self.flags & 0x00002000) != 0
    def set_IsShield(self, nValue):
        if (nValue == True): self.flags |= 0x00002000
        else: self.flags &= ~0x00002000
    IsShield = property(get_IsShield, set_IsShield)
    def get_IsTorch(self):
        return (self.flags & 0x00004000) != 0
    def set_IsTorch(self, nValue):
        if (nValue == True): self.flags |= 0x00004000
        else: self.flags &= ~0x00004000
    IsTorch = property(get_IsTorch, set_IsTorch)
    def get_IsTail(self):
        return (self.flags & 0x00008000) != 0
    def set_IsTail(self, nValue):
        if (nValue == True): self.flags |= 0x00008000
        else: self.flags &= ~0x00008000
    IsTail = property(get_IsTail, set_IsTail)
    def get_IsHideRings(self):
        return (self.flags & 0x00010000) != 0
    def set_IsHideRings(self, nValue):
        if (nValue == True): self.flags |= 0x00010000
        else: self.flags &= ~0x00010000
    IsHideRings = property(get_IsHideRings, set_IsHideRings)
    def get_IsHideAmulets(self):
        return (self.flags & 0x00020000) != 0
    def set_IsHideAmulets(self, nValue):
        if (nValue == True): self.flags |= 0x00020000
        else: self.flags &= ~0x00020000
    IsHideAmulets = property(get_IsHideAmulets, set_IsHideAmulets)
    def get_IsNonPlayable(self):
        return (self.flags & 0x00040000) != 0
    def set_IsNonPlayable(self, nValue):
        if (nValue == True): self.flags |= 0x00040000
        else: self.flags &= ~0x00040000
    IsNonPlayable = property(get_IsNonPlayable, set_IsNonPlayable)

class CONTRecord(BaseRecord):
    def CopyAsOverride(self, targetMod):
        FID = CBash.CopyCONTRecord(self._CollectionIndex, self._ModName, self._recordID, targetMod._ModName, c_bool(True))
        if(FID): return CONTRecord(self._CollectionIndex, targetMod._ModName, FID)
        return None
    def CopyAsNew(self, targetMod):
        FID = CBash.CopyCONTRecord(self._CollectionIndex, self._ModName, self._recordID, targetMod._ModName, c_bool(False))
        if(FID): return CONTRecord(self._CollectionIndex, targetMod._ModName, FID)
        return None
    class Item(object):
        def __init__(self, CollectionIndex, ModName, recordID, subField, listIndex):
            self._CollectionIndex = CollectionIndex
            self._ModName = ModName
            self._recordID = recordID
            self._subField = subField
            self._listIndex = listIndex
        def get_item(self):
            CBash.ReadFIDListField.restype = POINTER(c_uint)
            retValue = CBash.ReadFIDListField(self._CollectionIndex, self._ModName, self._recordID, self._subField, self._listIndex, 1)
            if(retValue): return retValue.contents.value
            return None
        def set_item(self, nValue):
            CBash.SetFIDListFieldUI(self._CollectionIndex, self._ModName, self._recordID, self._subField, self._listIndex, 1, nValue)
        item = property(get_item, set_item)
        def get_count(self):
            CBash.ReadFIDListField.restype = POINTER(c_int)
            retValue = CBash.ReadFIDListField(self._CollectionIndex, self._ModName, self._recordID, self._subField, self._listIndex, 2)
            if(retValue): return retValue.contents.value
            return None
        def set_count(self, nValue):
            CBash.SetFIDListFieldI(self._CollectionIndex, self._ModName, self._recordID, self._subField, self._listIndex, 2, nValue)
        count = property(get_count, set_count)
    def newItemsElement(self):
        listIndex = CBash.CreateFIDListElement(self._CollectionIndex, self._ModName, self._recordID, 11)
        if(listIndex == -1): return None
        return self.Item(self._CollectionIndex, self._ModName, self._recordID, 11, listIndex)
    def get_full(self):
        CBash.ReadFIDField.restype = c_char_p
        return CBash.ReadFIDField(self._CollectionIndex, self._ModName, self._recordID, 6)
    def set_full(self, nValue):
        CBash.SetFIDFieldStr(self._CollectionIndex, self._ModName, self._recordID, 6, nValue)
    full = property(get_full, set_full)
    def get_modPath(self):
        CBash.ReadFIDField.restype = c_char_p
        return CBash.ReadFIDField(self._CollectionIndex, self._ModName, self._recordID, 7)
    def set_modPath(self, nValue):
        CBash.SetFIDFieldStr(self._CollectionIndex, self._ModName, self._recordID, 7, nValue)
    modPath = property(get_modPath, set_modPath)
    def get_modb(self):
        CBash.ReadFIDField.restype = POINTER(c_float)
        retValue = CBash.ReadFIDField(self._CollectionIndex, self._ModName, self._recordID, 8)
        if(retValue): return retValue.contents.value
        return None
    def set_modb(self, nValue):
        CBash.SetFIDFieldF(self._CollectionIndex, self._ModName, self._recordID, 8, c_float(nValue))
    modb = property(get_modb, set_modb)
    def get_modt_p(self):
        numRecords = CBash.GetFIDFieldArraySize(self._CollectionIndex, self._ModName, self._recordID, 9)
        if(numRecords > 0):
            cRecords = POINTER(c_ubyte * numRecords)()
            CBash.GetFIDFieldArray(self._CollectionIndex, self._ModName, self._recordID, 9, byref(cRecords))
            return [cRecords.contents[x] for x in range(0, numRecords)]
        return []
    def set_modt_p(self, nValue):
        length = len(nValue)
        CBash.SetFIDFieldR(self._CollectionIndex, self._ModName, self._recordID, 9, struct.pack('B' * length, *nValue), length)
    modt_p = property(get_modt_p, set_modt_p)
    def get_script(self):
        CBash.ReadFIDField.restype = POINTER(c_uint)
        retValue = CBash.ReadFIDField(self._CollectionIndex, self._ModName, self._recordID, 10)
        if(retValue): return retValue.contents.value
        return None
    def set_script(self, nValue):
        CBash.SetFIDFieldUI(self._CollectionIndex, self._ModName, self._recordID, 10, c_uint(nValue))
    script = property(get_script, set_script)
    def get_items(self):
        numRecords = CBash.GetFIDListSize(self._CollectionIndex, self._ModName, self._recordID, 11)
        if(numRecords > 0): return [self.Item(self._CollectionIndex, self._ModName, self._recordID, 11, x) for x in range(0, numRecords)]
        return []
    def set_items(self, nItems):
        diffLength = len(nItems) - CBash.GetFIDListSize(self._CollectionIndex, self._ModName, self._recordID, 11)
        nValues = [(item.item, item.count) for item in nItems]
        while(diffLength < 0):
            CBash.DeleteFIDListElement(self._CollectionIndex, self._ModName, self._recordID, 11)
            diffLength += 1
        while(diffLength > 0):
            CBash.CreateFIDListElement(self._CollectionIndex, self._ModName, self._recordID, 11)
            diffLength -= 1
        for oItem, nValue in zip(self.items, nValues):
            oItem.item, oItem.count = nValue
    items = property(get_items, set_items)
    def get_flags(self):
        CBash.ReadFIDField.restype = POINTER(c_ubyte)
        retValue = CBash.ReadFIDField(self._CollectionIndex, self._ModName, self._recordID, 12)
        if(retValue): return retValue.contents.value
        return None
    def set_flags(self, nValue):
        CBash.SetFIDFieldUC(self._CollectionIndex, self._ModName, self._recordID, 12, c_ubyte(nValue))
    flags = property(get_flags, set_flags)
    def get_weight(self):
        CBash.ReadFIDField.restype = POINTER(c_float)
        retValue = CBash.ReadFIDField(self._CollectionIndex, self._ModName, self._recordID, 13)
        if(retValue): return retValue.contents.value
        return None
    def set_weight(self, nValue):
        CBash.SetFIDFieldF(self._CollectionIndex, self._ModName, self._recordID, 13, c_float(nValue))
    weight = property(get_weight, set_weight)
    def get_soundOpen(self):
        CBash.ReadFIDField.restype = POINTER(c_uint)
        retValue = CBash.ReadFIDField(self._CollectionIndex, self._ModName, self._recordID, 14)
        if(retValue): return retValue.contents.value
        return None
    def set_soundOpen(self, nValue):
        CBash.SetFIDFieldUI(self._CollectionIndex, self._ModName, self._recordID, 14, c_uint(nValue))
    soundOpen = property(get_soundOpen, set_soundOpen)
    def get_soundClose(self):
        CBash.ReadFIDField.restype = POINTER(c_uint)
        retValue = CBash.ReadFIDField(self._CollectionIndex, self._ModName, self._recordID, 15)
        if(retValue): return retValue.contents.value
        return None
    def set_soundClose(self, nValue):
        CBash.SetFIDFieldUI(self._CollectionIndex, self._ModName, self._recordID, 15, c_uint(nValue))
    soundClose = property(get_soundClose, set_soundClose)
    def get_IsRespawn(self):
        return (self.flags & 0x00000001) != 0
    def set_IsRespawn(self, nValue):
        if (nValue == True): self.flags |= 0x00000001
        else: self.flags &= ~0x00000001
    IsRespawn = property(get_IsRespawn, set_IsRespawn)
    
class DOORRecord(BaseRecord):
    def CopyAsOverride(self, targetMod):
        FID = CBash.CopyDOORRecord(self._CollectionIndex, self._ModName, self._recordID, targetMod._ModName, c_bool(True))
        if(FID): return DOORRecord(self._CollectionIndex, targetMod._ModName, FID)
        return None
    def CopyAsNew(self, targetMod):
        FID = CBash.CopyDOORRecord(self._CollectionIndex, self._ModName, self._recordID, targetMod._ModName, c_bool(False))
        if(FID): return DOORRecord(self._CollectionIndex, targetMod._ModName, FID)
        return None
    def get_full(self):
        CBash.ReadFIDField.restype = c_char_p
        return CBash.ReadFIDField(self._CollectionIndex, self._ModName, self._recordID, 6)
    def set_full(self, nValue):
        CBash.SetFIDFieldStr(self._CollectionIndex, self._ModName, self._recordID, 6, nValue)
    full = property(get_full, set_full)
    def get_modPath(self):
        CBash.ReadFIDField.restype = c_char_p
        return CBash.ReadFIDField(self._CollectionIndex, self._ModName, self._recordID, 7)
    def set_modPath(self, nValue):
        CBash.SetFIDFieldStr(self._CollectionIndex, self._ModName, self._recordID, 7, nValue)
    modPath = property(get_modPath, set_modPath)
    def get_modb(self):
        CBash.ReadFIDField.restype = POINTER(c_float)
        retValue = CBash.ReadFIDField(self._CollectionIndex, self._ModName, self._recordID, 8)
        if(retValue): return retValue.contents.value
        return None
    def set_modb(self, nValue):
        CBash.SetFIDFieldF(self._CollectionIndex, self._ModName, self._recordID, 8, c_float(nValue))
    modb = property(get_modb, set_modb)
    def get_modt_p(self):
        numRecords = CBash.GetFIDFieldArraySize(self._CollectionIndex, self._ModName, self._recordID, 9)
        if(numRecords > 0):
            cRecords = POINTER(c_ubyte * numRecords)()
            CBash.GetFIDFieldArray(self._CollectionIndex, self._ModName, self._recordID, 9, byref(cRecords))
            return [cRecords.contents[x] for x in range(0, numRecords)]
        return []
    def set_modt_p(self, nValue):
        length = len(nValue)
        CBash.SetFIDFieldR(self._CollectionIndex, self._ModName, self._recordID, 9, struct.pack('B' * length, *nValue), length)
    modt_p = property(get_modt_p, set_modt_p)
    def get_script(self):
        CBash.ReadFIDField.restype = POINTER(c_uint)
        retValue = CBash.ReadFIDField(self._CollectionIndex, self._ModName, self._recordID, 10)
        if(retValue): return retValue.contents.value
        return None
    def set_script(self, nValue):
        CBash.SetFIDFieldUI(self._CollectionIndex, self._ModName, self._recordID, 10, c_uint(nValue))
    script = property(get_script, set_script)
    def get_soundOpen(self):
        CBash.ReadFIDField.restype = POINTER(c_uint)
        retValue = CBash.ReadFIDField(self._CollectionIndex, self._ModName, self._recordID, 11)
        if(retValue): return retValue.contents.value
        return None
    def set_soundOpen(self, nValue):
        CBash.SetFIDFieldUI(self._CollectionIndex, self._ModName, self._recordID, 11, c_uint(nValue))
    soundOpen = property(get_soundOpen, set_soundOpen)
    def get_soundClose(self):
        CBash.ReadFIDField.restype = POINTER(c_uint)
        retValue = CBash.ReadFIDField(self._CollectionIndex, self._ModName, self._recordID, 12)
        if(retValue): return retValue.contents.value
        return None
    def set_soundClose(self, nValue):
        CBash.SetFIDFieldUI(self._CollectionIndex, self._ModName, self._recordID, 12, c_uint(nValue))
    soundClose = property(get_soundClose, set_soundClose)
    def get_soundLoop(self):
        CBash.ReadFIDField.restype = POINTER(c_uint)
        retValue = CBash.ReadFIDField(self._CollectionIndex, self._ModName, self._recordID, 13)
        if(retValue): return retValue.contents.value
        return None
    def set_soundLoop(self, nValue):
        CBash.SetFIDFieldUI(self._CollectionIndex, self._ModName, self._recordID, 13, c_uint(nValue))
    soundLoop = property(get_soundLoop, set_soundLoop)
    def get_flags(self):
        CBash.ReadFIDField.restype = POINTER(c_ubyte)
        retValue = CBash.ReadFIDField(self._CollectionIndex, self._ModName, self._recordID, 14)
        if(retValue): return retValue.contents.value
        return None
    def set_flags(self, nValue):
        CBash.SetFIDFieldUC(self._CollectionIndex, self._ModName, self._recordID, 14, c_ubyte(nValue))
    flags = property(get_flags, set_flags)
    def get_destinations(self):
        numRecords = CBash.GetFIDFieldArraySize(self._CollectionIndex, self._ModName, self._recordID, 15)
        if(numRecords > 0):
            cRecords = (POINTER(c_uint) * numRecords)()
            CBash.GetFIDFieldArray(self._CollectionIndex, self._ModName, self._recordID, 15, byref(cRecords))
            return [cRecords[x].contents.value for x in range(0, numRecords)]
        return []
    def set_destinations(self, nValue):
        length = len(nValue)
        cRecords = (c_uint * length)(*nValue)
        CBash.SetFIDFieldUIA(self._CollectionIndex, self._ModName, self._recordID, 15, cRecords, length)
    destinations = property(get_destinations, set_destinations)
    def get_IsOblivionGate(self):
        return (self.flags & 0x00000001) != 0
    def set_IsOblivionGate(self, nValue):
        if (nValue == True): self.flags |= 0x00000001
        else: self.flags &= ~0x00000001
    IsOblivionGate = property(get_IsOblivionGate, set_IsOblivionGate)
    def get_IsAutomatic(self):
        return (self.flags & 0x00000002) != 0
    def set_IsAutomatic(self, nValue):
        if (nValue == True): self.flags |= 0x00000002
        else: self.flags &= ~0x00000002
    IsAutomatic = property(get_IsAutomatic, set_IsAutomatic)
    def get_IsHidden(self):
        return (self.flags & 0x00000004) != 0
    def set_IsHidden(self, nValue):
        if (nValue == True): self.flags |= 0x00000004
        else: self.flags &= ~0x00000004
    IsHidden = property(get_IsHidden, set_IsHidden)
    def get_IsMinimalUse(self):
        return (self.flags & 0x00000008) != 0
    def set_IsMinimalUse(self, nValue):
        if (nValue == True): self.flags |= 0x00000008
        else: self.flags &= ~0x00000008
    IsMinimalUse = property(get_IsMinimalUse, set_IsMinimalUse)
    
class INGRRecord(BaseRecord):
    def CopyAsOverride(self, targetMod):
        FID = CBash.CopyINGRRecord(self._CollectionIndex, self._ModName, self._recordID, targetMod._ModName, c_bool(True))
        if(FID): return INGRRecord(self._CollectionIndex, targetMod._ModName, FID)
        return None
    def CopyAsNew(self, targetMod):
        FID = CBash.CopyINGRRecord(self._CollectionIndex, self._ModName, self._recordID, targetMod._ModName, c_bool(False))
        if(FID): return INGRRecord(self._CollectionIndex, targetMod._ModName, FID)
        return None
    class Effect(object):
        def __init__(self, CollectionIndex, ModName, recordID, subField, listIndex):
            self._CollectionIndex = CollectionIndex
            self._ModName = ModName
            self._recordID = recordID
            self._subField = subField
            self._listIndex = listIndex
        ##name0 and name are both are always the same value, so setting one will set both. They're basically aliases
        def get_name0(self):
            CBash.ReadFIDListField.restype = POINTER(c_uint)
            retValue = CBash.ReadFIDListField(self._CollectionIndex, self._ModName, self._recordID, self._subField, self._listIndex, 1)
            if(retValue): return retValue.contents.value
            return None
        def set_name0(self, nValue):
            CBash.SetFIDListFieldUI(self._CollectionIndex, self._ModName, self._recordID, self._subField, self._listIndex, 1, nValue)
        name0 = property(get_name0, set_name0)
        def get_name(self):
            CBash.ReadFIDListField.restype = POINTER(c_uint)
            retValue = CBash.ReadFIDListField(self._CollectionIndex, self._ModName, self._recordID, self._subField, self._listIndex, 2)
            if(retValue): return retValue.contents.value
            return None
        def set_name(self, nValue):
            CBash.SetFIDListFieldUI(self._CollectionIndex, self._ModName, self._recordID, self._subField, self._listIndex, 2, nValue)
        name = property(get_name, set_name)
        def get_magnitude(self):
            CBash.ReadFIDListField.restype = POINTER(c_uint)
            retValue = CBash.ReadFIDListField(self._CollectionIndex, self._ModName, self._recordID, self._subField, self._listIndex, 3)
            if(retValue): return retValue.contents.value
            return None
        def set_magnitude(self, nValue):
            CBash.SetFIDListFieldUI(self._CollectionIndex, self._ModName, self._recordID, self._subField, self._listIndex, 3, nValue)
        magnitude = property(get_magnitude, set_magnitude)
        def get_area(self):
            CBash.ReadFIDListField.restype = POINTER(c_uint)
            retValue = CBash.ReadFIDListField(self._CollectionIndex, self._ModName, self._recordID, self._subField, self._listIndex, 4)
            if(retValue): return retValue.contents.value
            return None
        def set_area(self, nValue):
            CBash.SetFIDListFieldUI(self._CollectionIndex, self._ModName, self._recordID, self._subField, self._listIndex, 4, nValue)
        area = property(get_area, set_area)
        def get_duration(self):
            CBash.ReadFIDListField.restype = POINTER(c_uint)
            retValue = CBash.ReadFIDListField(self._CollectionIndex, self._ModName, self._recordID, self._subField, self._listIndex, 5)
            if(retValue): return retValue.contents.value
            return None
        def set_duration(self, nValue):
            CBash.SetFIDListFieldUI(self._CollectionIndex, self._ModName, self._recordID, self._subField, self._listIndex, 5, nValue)
        duration = property(get_duration, set_duration)
        def get_recipient(self):
            CBash.ReadFIDListField.restype = POINTER(c_uint)
            retValue = CBash.ReadFIDListField(self._CollectionIndex, self._ModName, self._recordID, self._subField, self._listIndex, 6)
            if(retValue): return retValue.contents.value
            return None
        def set_recipient(self, nValue):
            CBash.SetFIDListFieldUI(self._CollectionIndex, self._ModName, self._recordID, self._subField, self._listIndex, 6, nValue)
        recipient = property(get_recipient, set_recipient)
        def get_actorValue(self):
            CBash.ReadFIDListField.restype = POINTER(c_int)
            retValue = CBash.ReadFIDListField(self._CollectionIndex, self._ModName, self._recordID, self._subField, self._listIndex, 7)
            if(retValue): return retValue.contents.value
            return None
        def set_actorValue(self, nValue):
            CBash.SetFIDListFieldI(self._CollectionIndex, self._ModName, self._recordID, self._subField, self._listIndex, 7, nValue)
        actorValue = property(get_actorValue, set_actorValue)
        def get_script(self):
            CBash.ReadFIDListField.restype = POINTER(c_uint)
            retValue = CBash.ReadFIDListField(self._CollectionIndex, self._ModName, self._recordID, self._subField, self._listIndex, 8)
            if(retValue): return retValue.contents.value
            return None
        def set_script(self, nValue):
            CBash.SetFIDListFieldUI(self._CollectionIndex, self._ModName, self._recordID, self._subField, self._listIndex, 8, nValue)
        script = property(get_script, set_script)
        def get_school(self):
            CBash.ReadFIDListField.restype = POINTER(c_uint)
            retValue = CBash.ReadFIDListField(self._CollectionIndex, self._ModName, self._recordID, self._subField, self._listIndex, 9)
            if(retValue): return retValue.contents.value
            return None
        def set_school(self, nValue):
            CBash.SetFIDListFieldUI(self._CollectionIndex, self._ModName, self._recordID, self._subField, self._listIndex, 9, nValue)
        school = property(get_school, set_school)
        def get_visual(self):
            CBash.ReadFIDListField.restype = POINTER(c_uint)
            retValue = CBash.ReadFIDListField(self._CollectionIndex, self._ModName, self._recordID, self._subField, self._listIndex, 10)
            if(retValue): return retValue.contents.value
            return None
        def set_visual(self, nValue):
            CBash.SetFIDListFieldUI(self._CollectionIndex, self._ModName, self._recordID, self._subField, self._listIndex, 10, nValue)
        visual = property(get_visual, set_visual)
        def get_flags(self):
            CBash.ReadFIDListField.restype = POINTER(c_ubyte)
            retValue = CBash.ReadFIDListField(self._CollectionIndex, self._ModName, self._recordID, self._subField, self._listIndex, 11)
            if(retValue): return retValue.contents.value
            return None
        def set_flags(self, nValue):
            CBash.SetFIDListFieldUC(self._CollectionIndex, self._ModName, self._recordID, self._subField, self._listIndex, 11, c_ubyte(nValue))
        flags = property(get_flags, set_flags)
        def get_unused1(self):
            numRecords = CBash.GetFIDListArraySize(self._CollectionIndex, self._ModName, self._recordID, self._subField, self._listIndex, 12)
            if(numRecords > 0):
                cRecords = POINTER(c_ubyte * numRecords)()
                CBash.GetFIDListArray(self._CollectionIndex, self._ModName, self._recordID, self._subField, self._listIndex, 12, byref(cRecords))
                return [cRecords.contents[x] for x in range(0, numRecords)]
            return []
        def set_unused1(self, nValue):
            CBash.SetFIDListFieldR(self._CollectionIndex, self._ModName, self._recordID, self._subField, self._listIndex, 12, struct.pack('3B', *nValue), 3)
        unused1 = property(get_unused1, set_unused1)
        def get_full(self):
            CBash.ReadFIDListField.restype = c_char_p
            return CBash.ReadFIDListField(self._CollectionIndex, self._ModName, self._recordID, self._subField, self._listIndex, 13)
        def set_full(self, nValue):
            CBash.SetFIDListFieldStr(self._CollectionIndex, self._ModName, self._recordID, self._subField, self._listIndex, 13, nValue)
        full = property(get_full, set_full)
        def get_IsHostile(self):
            return (self.flags & 0x00000001) != 0
        def set_IsHostile(self, nValue):
            if (nValue == True): self.flags |= 0x00000001
            else: self.flags &= ~0x00000001
        IsHostile = property(get_IsHostile, set_IsHostile)
    def newEffectsElement(self):
        listIndex = CBash.CreateFIDListElement(self._CollectionIndex, self._ModName, self._recordID, 16)
        if(listIndex == -1): return None
        return self.Effect(self._CollectionIndex, self._ModName, self._recordID, 16, listIndex)
    def get_full(self):
        CBash.ReadFIDField.restype = c_char_p
        return CBash.ReadFIDField(self._CollectionIndex, self._ModName, self._recordID, 6)
    def set_full(self, nValue):
        CBash.SetFIDFieldStr(self._CollectionIndex, self._ModName, self._recordID, 6, nValue)
    full = property(get_full, set_full)
    def get_modPath(self):
        CBash.ReadFIDField.restype = c_char_p
        return CBash.ReadFIDField(self._CollectionIndex, self._ModName, self._recordID, 7)
    def set_modPath(self, nValue):
        CBash.SetFIDFieldStr(self._CollectionIndex, self._ModName, self._recordID, 7, nValue)
    modPath = property(get_modPath, set_modPath)
    def get_modb(self):
        CBash.ReadFIDField.restype = POINTER(c_float)
        retValue = CBash.ReadFIDField(self._CollectionIndex, self._ModName, self._recordID, 8)
        if(retValue): return retValue.contents.value
        return None
    def set_modb(self, nValue):
        CBash.SetFIDFieldF(self._CollectionIndex, self._ModName, self._recordID, 8, c_float(nValue))
    modb = property(get_modb, set_modb)
    def get_modt_p(self):
        numRecords = CBash.GetFIDFieldArraySize(self._CollectionIndex, self._ModName, self._recordID, 9)
        if(numRecords > 0):
            cRecords = POINTER(c_ubyte * numRecords)()
            CBash.GetFIDFieldArray(self._CollectionIndex, self._ModName, self._recordID, 9, byref(cRecords))
            return [cRecords.contents[x] for x in range(0, numRecords)]
        return []
    def set_modt_p(self, nValue):
        length = len(nValue)
        CBash.SetFIDFieldR(self._CollectionIndex, self._ModName, self._recordID, 9, struct.pack('B' * length, *nValue), length)
    modt_p = property(get_modt_p, set_modt_p)
    def get_iconPath(self):
        CBash.ReadFIDField.restype = c_char_p
        return CBash.ReadFIDField(self._CollectionIndex, self._ModName, self._recordID, 10)
    def set_iconPath(self, nValue):
        CBash.SetFIDFieldStr(self._CollectionIndex, self._ModName, self._recordID, 10, nValue)
    iconPath = property(get_iconPath, set_iconPath)
    def get_script(self):
        CBash.ReadFIDField.restype = POINTER(c_uint)
        retValue = CBash.ReadFIDField(self._CollectionIndex, self._ModName, self._recordID, 11)
        if(retValue): return retValue.contents.value
        return None
    def set_script(self, nValue):
        CBash.SetFIDFieldUI(self._CollectionIndex, self._ModName, self._recordID, 11, c_uint(nValue))
    script = property(get_script, set_script)
    def get_weight(self):
        CBash.ReadFIDField.restype = POINTER(c_float)
        retValue = CBash.ReadFIDField(self._CollectionIndex, self._ModName, self._recordID, 12)
        if(retValue): return retValue.contents.value
        return None
    def set_weight(self, nValue):
        CBash.SetFIDFieldF(self._CollectionIndex, self._ModName, self._recordID, 12, c_float(nValue))
    weight = property(get_weight, set_weight)
    def get_value(self):
        CBash.ReadFIDField.restype = POINTER(c_int)
        retValue = CBash.ReadFIDField(self._CollectionIndex, self._ModName, self._recordID, 13)
        if(retValue): return retValue.contents.value
        return None
    def set_value(self, nValue):
        CBash.SetFIDFieldI(self._CollectionIndex, self._ModName, self._recordID, 13, c_int(nValue))
    value = property(get_value, set_value)
    def get_flags(self):
        CBash.ReadFIDField.restype = POINTER(c_ubyte)
        retValue = CBash.ReadFIDField(self._CollectionIndex, self._ModName, self._recordID, 14)
        if(retValue): return retValue.contents.value
        return None
    def set_flags(self, nValue):
        CBash.SetFIDFieldUC(self._CollectionIndex, self._ModName, self._recordID, 14, c_ubyte(nValue))
    flags = property(get_flags, set_flags)
    def get_unused1(self):
        numRecords = CBash.GetFIDFieldArraySize(self._CollectionIndex, self._ModName, self._recordID, 15)
        if(numRecords > 0):
            cRecords = POINTER(c_ubyte * numRecords)()
            CBash.GetFIDFieldArray(self._CollectionIndex, self._ModName, self._recordID, 15, byref(cRecords))
            return [cRecords.contents[x] for x in range(0, numRecords)]
        return []
    def set_unused1(self, nValue):
        CBash.SetFIDFieldR(self._CollectionIndex, self._ModName, self._recordID, 15, struct.pack('3B', *nValue), 3)
    unused1 = property(get_unused1, set_unused1)
    def get_effects(self):
        numRecords = CBash.GetFIDListSize(self._CollectionIndex, self._ModName, self._recordID, 16)
        if(numRecords > 0): return [self.Effect(self._CollectionIndex, self._ModName, self._recordID, 16, x) for x in range(0, numRecords)]
        return []
    def set_effects(self, nEffects):
        diffLength = len(nEffects) - CBash.GetFIDListSize(self._CollectionIndex, self._ModName, self._recordID, 16)
        nValues = [(nEffect.name0, nEffect.name, nEffect.magnitude, nEffect.area, nEffect.duration, nEffect.recipient, nEffect.actorValue, nEffect.script, nEffect.school, nEffect.visual, nEffect.flags, nEffect.unused1, nEffect.full) for nEffect in nEffects]
        while(diffLength < 0):
            CBash.DeleteFIDListElement(self._CollectionIndex, self._ModName, self._recordID, 16)
            diffLength += 1
        while(diffLength > 0):
            CBash.CreateFIDListElement(self._CollectionIndex, self._ModName, self._recordID, 16)
            diffLength -= 1
        for oEffect, nValue in zip(self.effects, nValues):
            oEffect.name0, oEffect.name, oEffect.magnitude, oEffect.area, oEffect.duration, oEffect.recipient, oEffect.actorValue, oEffect.script, oEffect.school, oEffect.visual, oEffect.flags, oEffect.unused1, oEffect.full = nValue
    effects = property(get_effects, set_effects)
    def get_IsNoAutoCalc(self):
        return (self.flags & 0x00000001) != 0
    def set_IsNoAutoCalc(self, nValue):
        if (nValue == True): self.flags |= 0x00000001
        else: self.flags &= ~0x00000001
    IsNoAutoCalc = property(get_IsNoAutoCalc, set_IsNoAutoCalc)
    def get_IsFood(self):
        return (self.flags & 0x00000002) != 0
    def set_IsFood(self, nValue):
        if (nValue == True): self.flags |= 0x00000002
        else: self.flags &= ~0x00000002
    IsFood = property(get_IsFood, set_IsFood)

class LIGHRecord(BaseRecord):
    def CopyAsOverride(self, targetMod):
        FID = CBash.CopyLIGHRecord(self._CollectionIndex, self._ModName, self._recordID, targetMod._ModName, c_bool(True))
        if(FID): return LIGHRecord(self._CollectionIndex, targetMod._ModName, FID)
        return None
    def CopyAsNew(self, targetMod):
        FID = CBash.CopyLIGHRecord(self._CollectionIndex, self._ModName, self._recordID, targetMod._ModName, c_bool(False))
        if(FID): return LIGHRecord(self._CollectionIndex, targetMod._ModName, FID)
        return None
    def get_modPath(self):
        CBash.ReadFIDField.restype = c_char_p
        return CBash.ReadFIDField(self._CollectionIndex, self._ModName, self._recordID, 6)
    def set_modPath(self, nValue):
        CBash.SetFIDFieldStr(self._CollectionIndex, self._ModName, self._recordID, 6, nValue)
    modPath = property(get_modPath, set_modPath)
    def get_modb(self):
        CBash.ReadFIDField.restype = POINTER(c_float)
        retValue = CBash.ReadFIDField(self._CollectionIndex, self._ModName, self._recordID, 7)
        if(retValue): return retValue.contents.value
        return None
    def set_modb(self, nValue):
        CBash.SetFIDFieldF(self._CollectionIndex, self._ModName, self._recordID, 7, c_float(nValue))
    modb = property(get_modb, set_modb)
    def get_modt_p(self):
        numRecords = CBash.GetFIDFieldArraySize(self._CollectionIndex, self._ModName, self._recordID, 8)
        if(numRecords > 0):
            cRecords = POINTER(c_ubyte * numRecords)()
            CBash.GetFIDFieldArray(self._CollectionIndex, self._ModName, self._recordID, 8, byref(cRecords))
            return [cRecords.contents[x] for x in range(0, numRecords)]
        return []
    def set_modt_p(self, nValue):
        length = len(nValue)
        CBash.SetFIDFieldR(self._CollectionIndex, self._ModName, self._recordID, 8, struct.pack('B' * length, *nValue), length)
    modt_p = property(get_modt_p, set_modt_p)
    def get_script(self):
        CBash.ReadFIDField.restype = POINTER(c_uint)
        retValue = CBash.ReadFIDField(self._CollectionIndex, self._ModName, self._recordID, 9)
        if(retValue): return retValue.contents.value
        return None
    def set_script(self, nValue):
        CBash.SetFIDFieldUI(self._CollectionIndex, self._ModName, self._recordID, 9, c_uint(nValue))
    script = property(get_script, set_script)
    def get_full(self):
        CBash.ReadFIDField.restype = c_char_p
        return CBash.ReadFIDField(self._CollectionIndex, self._ModName, self._recordID, 10)
    def set_full(self, nValue):
        CBash.SetFIDFieldStr(self._CollectionIndex, self._ModName, self._recordID, 10, nValue)
    full = property(get_full, set_full)
    def get_iconPath(self):
        CBash.ReadFIDField.restype = c_char_p
        return CBash.ReadFIDField(self._CollectionIndex, self._ModName, self._recordID, 11)
    def set_iconPath(self, nValue):
        CBash.SetFIDFieldStr(self._CollectionIndex, self._ModName, self._recordID, 11, nValue)
    iconPath = property(get_iconPath, set_iconPath)
    def get_duration(self):
        CBash.ReadFIDField.restype = POINTER(c_int)
        retValue = CBash.ReadFIDField(self._CollectionIndex, self._ModName, self._recordID, 12)
        if(retValue): return retValue.contents.value
        return None
    def set_duration(self, nValue):
        CBash.SetFIDFieldI(self._CollectionIndex, self._ModName, self._recordID, 12, c_int(nValue))
    duration = property(get_duration, set_duration)
    def get_radius(self):
        CBash.ReadFIDField.restype = POINTER(c_uint)
        retValue = CBash.ReadFIDField(self._CollectionIndex, self._ModName, self._recordID, 13)
        if(retValue): return retValue.contents.value
        return None
    def set_radius(self, nValue):
        CBash.SetFIDFieldUI(self._CollectionIndex, self._ModName, self._recordID, 13, c_uint(nValue))
    radius = property(get_radius, set_radius)
    def get_red(self):
        CBash.ReadFIDField.restype = POINTER(c_ubyte)
        retValue = CBash.ReadFIDField(self._CollectionIndex, self._ModName, self._recordID, 14)
        if(retValue): return retValue.contents.value
        return None
    def set_red(self, nValue):
        CBash.SetFIDFieldUC(self._CollectionIndex, self._ModName, self._recordID, 14, c_ubyte(nValue))
    red = property(get_red, set_red)
    def get_green(self):
        CBash.ReadFIDField.restype = POINTER(c_ubyte)
        retValue = CBash.ReadFIDField(self._CollectionIndex, self._ModName, self._recordID, 15)
        if(retValue): return retValue.contents.value
        return None
    def set_green(self, nValue):
        CBash.SetFIDFieldUC(self._CollectionIndex, self._ModName, self._recordID, 15, c_ubyte(nValue))
    green = property(get_green, set_green)
    def get_blue(self):
        CBash.ReadFIDField.restype = POINTER(c_ubyte)
        retValue = CBash.ReadFIDField(self._CollectionIndex, self._ModName, self._recordID, 16)
        if(retValue): return retValue.contents.value
        return None
    def set_blue(self, nValue):
        CBash.SetFIDFieldUC(self._CollectionIndex, self._ModName, self._recordID, 16, c_ubyte(nValue))
    blue = property(get_blue, set_blue)
    def get_unused1(self):
        numRecords = CBash.GetFIDFieldArraySize(self._CollectionIndex, self._ModName, self._recordID, 17)
        if(numRecords > 0):
            cRecords = POINTER(c_ubyte * numRecords)()
            CBash.GetFIDFieldArray(self._CollectionIndex, self._ModName, self._recordID, 17, byref(cRecords))
            return [cRecords.contents[x] for x in range(0, numRecords)]
        return []
    def set_unused1(self, nValue):
        CBash.SetFIDFieldR(self._CollectionIndex, self._ModName, self._recordID, 17, struct.pack('B', *nValue), 1)
    unused1 = property(get_unused1, set_unused1)
    def get_flags(self):
        CBash.ReadFIDField.restype = POINTER(c_uint)
        retValue = CBash.ReadFIDField(self._CollectionIndex, self._ModName, self._recordID, 18)
        if(retValue): return retValue.contents.value
        return None
    def set_flags(self, nValue):
        CBash.SetFIDFieldUI(self._CollectionIndex, self._ModName, self._recordID, 18, c_uint(nValue))
    flags = property(get_flags, set_flags)
    def get_falloff(self):
        CBash.ReadFIDField.restype = POINTER(c_float)
        retValue = CBash.ReadFIDField(self._CollectionIndex, self._ModName, self._recordID, 19)
        if(retValue): return retValue.contents.value
        return None
    def set_falloff(self, nValue):
        CBash.SetFIDFieldF(self._CollectionIndex, self._ModName, self._recordID, 19, c_float(nValue))
    falloff = property(get_falloff, set_falloff)
    def get_fov(self):
        CBash.ReadFIDField.restype = POINTER(c_float)
        retValue = CBash.ReadFIDField(self._CollectionIndex, self._ModName, self._recordID, 20)
        if(retValue): return retValue.contents.value
        return None
    def set_fov(self, nValue):
        CBash.SetFIDFieldF(self._CollectionIndex, self._ModName, self._recordID, 20, c_float(nValue))
    fov = property(get_fov, set_fov)
    def get_value(self):
        CBash.ReadFIDField.restype = POINTER(c_uint)
        retValue = CBash.ReadFIDField(self._CollectionIndex, self._ModName, self._recordID, 21)
        if(retValue): return retValue.contents.value
        return None
    def set_value(self, nValue):
        CBash.SetFIDFieldUI(self._CollectionIndex, self._ModName, self._recordID, 21, c_uint(nValue))
    value = property(get_value, set_value)
    def get_weight(self):
        CBash.ReadFIDField.restype = POINTER(c_float)
        retValue = CBash.ReadFIDField(self._CollectionIndex, self._ModName, self._recordID, 22)
        if(retValue): return retValue.contents.value
        return None
    def set_weight(self, nValue):
        CBash.SetFIDFieldF(self._CollectionIndex, self._ModName, self._recordID, 22, c_float(nValue))
    weight = property(get_weight, set_weight)
    def get_fade(self):
        CBash.ReadFIDField.restype = POINTER(c_float)
        retValue = CBash.ReadFIDField(self._CollectionIndex, self._ModName, self._recordID, 23)
        if(retValue): return retValue.contents.value
        return None
    def set_fade(self, nValue):
        CBash.SetFIDFieldF(self._CollectionIndex, self._ModName, self._recordID, 23, c_float(nValue))
    fade = property(get_fade, set_fade)
    def get_sound(self):
        CBash.ReadFIDField.restype = POINTER(c_uint)
        retValue = CBash.ReadFIDField(self._CollectionIndex, self._ModName, self._recordID, 24)
        if(retValue): return retValue.contents.value
        return None
    def set_sound(self, nValue):
        CBash.SetFIDFieldUI(self._CollectionIndex, self._ModName, self._recordID, 24, c_uint(nValue))
    sound = property(get_sound, set_sound)
    def get_IsDynamic(self):
        return (self.flags & 0x00000001) != 0
    def set_IsDynamic(self, nValue):
        if (nValue == True): self.flags |= 0x00000001
        else: self.flags &= ~0x00000001
    IsDynamic = property(get_IsDynamic, set_IsDynamic)
    def get_IsCanTake(self):
        return (self.flags & 0x00000002) != 0
    def set_IsCanTake(self, nValue):
        if (nValue == True): self.flags |= 0x00000002
        else: self.flags &= ~0x00000002
    IsCanTake = property(get_IsCanTake, set_IsCanTake)
    def get_IsNegative(self):
        return (self.flags & 0x00000004) != 0
    def set_IsNegative(self, nValue):
        if (nValue == True): self.flags |= 0x00000004
        else: self.flags &= ~0x00000004
    IsNegative = property(get_IsNegative, set_IsNegative)
    def get_IsFlickers(self):
        return (self.flags & 0x00000008) != 0
    def set_IsFlickers(self, nValue):
        if (nValue == True): self.flags |= 0x00000008
        else: self.flags &= ~0x00000008
    IsFlickers = property(get_IsFlickers, set_IsFlickers)
    def get_IsOffByDefault(self):
        return (self.flags & 0x00000020) != 0
    def set_IsOffByDefault(self, nValue):
        if (nValue == True): self.flags |= 0x00000020
        else: self.flags &= ~0x00000020
    IsOffByDefault = property(get_IsOffByDefault, set_IsOffByDefault)
    def get_IsFlickerSlow(self):
        return (self.flags & 0x00000040) != 0
    def set_IsFlickerSlow(self, nValue):
        if (nValue == True): self.flags |= 0x00000040
        else: self.flags &= ~0x00000040
    IsFlickerSlow = property(get_IsFlickerSlow, set_IsFlickerSlow)
    def get_IsPulse(self):
        return (self.flags & 0x00000080) != 0
    def set_IsPulse(self, nValue):
        if (nValue == True): self.flags |= 0x00000080
        else: self.flags &= ~0x00000080
    IsPulse = property(get_IsPulse, set_IsPulse)
    def get_IsPulseSlow(self):
        return (self.flags & 0x00000100) != 0
    def set_IsPulseSlow(self, nValue):
        if (nValue == True): self.flags |= 0x00000100
        else: self.flags &= ~0x00000100
    IsPulseSlow = property(get_IsPulseSlow, set_IsPulseSlow)
    def get_IsSpotLight(self):
        return (self.flags & 0x00000200) != 0
    def set_IsSpotLight(self, nValue):
        if (nValue == True): self.flags |= 0x00000200
        else: self.flags &= ~0x00000200
    IsSpotLight = property(get_IsSpotLight, set_IsSpotLight)
    def get_IsSpotShadow(self):
        return (self.flags & 0x00000400) != 0
    def set_IsSpotShadow(self, nValue):
        if (nValue == True): self.flags |= 0x00000400
        else: self.flags &= ~0x00000400
    IsSpotShadow = property(get_IsSpotShadow, set_IsSpotShadow)

class MISCRecord(BaseRecord):
    def CopyAsOverride(self, targetMod):
        FID = CBash.CopyMISCRecord(self._CollectionIndex, self._ModName, self._recordID, targetMod._ModName, c_bool(True))
        if(FID): return MISCRecord(self._CollectionIndex, targetMod._ModName, FID)
        return None
    def CopyAsNew(self, targetMod):
        FID = CBash.CopyMISCRecord(self._CollectionIndex, self._ModName, self._recordID, targetMod._ModName, c_bool(False))
        if(FID): return MISCRecord(self._CollectionIndex, targetMod._ModName, FID)
        return None
    def get_full(self):
        CBash.ReadFIDField.restype = c_char_p
        return CBash.ReadFIDField(self._CollectionIndex, self._ModName, self._recordID, 6)
    def set_full(self, nValue):
        CBash.SetFIDFieldStr(self._CollectionIndex, self._ModName, self._recordID, 6, nValue)
    full = property(get_full, set_full)
    def get_modPath(self):
        CBash.ReadFIDField.restype = c_char_p
        return CBash.ReadFIDField(self._CollectionIndex, self._ModName, self._recordID, 7)
    def set_modPath(self, nValue):
        CBash.SetFIDFieldStr(self._CollectionIndex, self._ModName, self._recordID, 7, nValue)
    modPath = property(get_modPath, set_modPath)
    def get_modb(self):
        CBash.ReadFIDField.restype = POINTER(c_float)
        retValue = CBash.ReadFIDField(self._CollectionIndex, self._ModName, self._recordID, 8)
        if(retValue): return retValue.contents.value
        return None
    def set_modb(self, nValue):
        CBash.SetFIDFieldF(self._CollectionIndex, self._ModName, self._recordID, 8, c_float(nValue))
    modb = property(get_modb, set_modb)
    def get_modt_p(self):
        numRecords = CBash.GetFIDFieldArraySize(self._CollectionIndex, self._ModName, self._recordID, 9)
        if(numRecords > 0):
            cRecords = POINTER(c_ubyte * numRecords)()
            CBash.GetFIDFieldArray(self._CollectionIndex, self._ModName, self._recordID, 9, byref(cRecords))
            return [cRecords.contents[x] for x in range(0, numRecords)]
        return []
    def set_modt_p(self, nValue):
        length = len(nValue)
        CBash.SetFIDFieldR(self._CollectionIndex, self._ModName, self._recordID, 9, struct.pack('B' * length, *nValue), length)
    modt_p = property(get_modt_p, set_modt_p)
    def get_iconPath(self):
        CBash.ReadFIDField.restype = c_char_p
        return CBash.ReadFIDField(self._CollectionIndex, self._ModName, self._recordID, 10)
    def set_iconPath(self, nValue):
        CBash.SetFIDFieldStr(self._CollectionIndex, self._ModName, self._recordID, 10, nValue)
    iconPath = property(get_iconPath, set_iconPath)
    def get_script(self):
        CBash.ReadFIDField.restype = POINTER(c_uint)
        retValue = CBash.ReadFIDField(self._CollectionIndex, self._ModName, self._recordID, 11)
        if(retValue): return retValue.contents.value
        return None
    def set_script(self, nValue):
        CBash.SetFIDFieldUI(self._CollectionIndex, self._ModName, self._recordID, 11, c_uint(nValue))
    script = property(get_script, set_script)
    def get_value(self):
        CBash.ReadFIDField.restype = POINTER(c_uint)
        retValue = CBash.ReadFIDField(self._CollectionIndex, self._ModName, self._recordID, 12)
        if(retValue): return retValue.contents.value
        return None
    def set_value(self, nValue):
        CBash.SetFIDFieldUI(self._CollectionIndex, self._ModName, self._recordID, 12, c_uint(nValue))
    value = property(get_value, set_value)
    def get_weight(self):
        CBash.ReadFIDField.restype = POINTER(c_float)
        retValue = CBash.ReadFIDField(self._CollectionIndex, self._ModName, self._recordID, 13)
        if(retValue): return retValue.contents.value
        return None
    def set_weight(self, nValue):
        CBash.SetFIDFieldF(self._CollectionIndex, self._ModName, self._recordID, 13, c_float(nValue))
    weight = property(get_weight, set_weight)

class STATRecord(BaseRecord):
    def CopyAsOverride(self, targetMod):
        FID = CBash.CopySTATRecord(self._CollectionIndex, self._ModName, self._recordID, targetMod._ModName, c_bool(True))
        if(FID): return STATRecord(self._CollectionIndex, targetMod._ModName, FID)
        return None
    def CopyAsNew(self, targetMod):
        FID = CBash.CopySTATRecord(self._CollectionIndex, self._ModName, self._recordID, targetMod._ModName, c_bool(False))
        if(FID): return STATRecord(self._CollectionIndex, targetMod._ModName, FID)
        return None
    def get_modPath(self):
        CBash.ReadFIDField.restype = c_char_p
        return CBash.ReadFIDField(self._CollectionIndex, self._ModName, self._recordID, 6)
    def set_modPath(self, nValue):
        CBash.SetFIDFieldStr(self._CollectionIndex, self._ModName, self._recordID, 6, nValue)
    modPath = property(get_modPath, set_modPath)
    def get_modb(self):
        CBash.ReadFIDField.restype = POINTER(c_float)
        retValue = CBash.ReadFIDField(self._CollectionIndex, self._ModName, self._recordID, 7)
        if(retValue): return retValue.contents.value
        return None
    def set_modb(self, nValue):
        CBash.SetFIDFieldF(self._CollectionIndex, self._ModName, self._recordID, 7, c_float(nValue))
    modb = property(get_modb, set_modb)
    def get_modt_p(self):
        numRecords = CBash.GetFIDFieldArraySize(self._CollectionIndex, self._ModName, self._recordID, 8)
        if(numRecords > 0):
            cRecords = POINTER(c_ubyte * numRecords)()
            CBash.GetFIDFieldArray(self._CollectionIndex, self._ModName, self._recordID, 8, byref(cRecords))
            return [cRecords.contents[x] for x in range(0, numRecords)]
        return []
    def set_modt_p(self, nValue):
        length = len(nValue)
        CBash.SetFIDFieldR(self._CollectionIndex, self._ModName, self._recordID, 8, struct.pack('B' * length, *nValue), length)
    modt_p = property(get_modt_p, set_modt_p)
class GRASRecord(BaseRecord):
    def CopyAsOverride(self, targetMod):
        FID = CBash.CopyGRASRecord(self._CollectionIndex, self._ModName, self._recordID, targetMod._ModName, c_bool(True))
        if(FID): return GRASRecord(self._CollectionIndex, targetMod._ModName, FID)
        return None
    def CopyAsNew(self, targetMod):
        FID = CBash.CopyGRASRecord(self._CollectionIndex, self._ModName, self._recordID, targetMod._ModName, c_bool(False))
        if(FID): return GRASRecord(self._CollectionIndex, targetMod._ModName, FID)
        return None
    def get_modPath(self):
        CBash.ReadFIDField.restype = c_char_p
        return CBash.ReadFIDField(self._CollectionIndex, self._ModName, self._recordID, 6)
    def set_modPath(self, nValue):
        CBash.SetFIDFieldStr(self._CollectionIndex, self._ModName, self._recordID, 6, nValue)
    modPath = property(get_modPath, set_modPath)
    def get_modb(self):
        CBash.ReadFIDField.restype = POINTER(c_float)
        retValue = CBash.ReadFIDField(self._CollectionIndex, self._ModName, self._recordID, 7)
        if(retValue): return retValue.contents.value
        return None
    def set_modb(self, nValue):
        CBash.SetFIDFieldF(self._CollectionIndex, self._ModName, self._recordID, 7, c_float(nValue))
    modb = property(get_modb, set_modb)
    def get_modt_p(self):
        numRecords = CBash.GetFIDFieldArraySize(self._CollectionIndex, self._ModName, self._recordID, 8)
        if(numRecords > 0):
            cRecords = POINTER(c_ubyte * numRecords)()
            CBash.GetFIDFieldArray(self._CollectionIndex, self._ModName, self._recordID, 8, byref(cRecords))
            return [cRecords.contents[x] for x in range(0, numRecords)]
        return []
    def set_modt_p(self, nValue):
        length = len(nValue)
        CBash.SetFIDFieldR(self._CollectionIndex, self._ModName, self._recordID, 8, struct.pack('B' * length, *nValue), length)
    modt_p = property(get_modt_p, set_modt_p)
    def get_density(self):
        CBash.ReadFIDField.restype = POINTER(c_ubyte)
        retValue = CBash.ReadFIDField(self._CollectionIndex, self._ModName, self._recordID, 9)
        if(retValue): return retValue.contents.value
        return None
    def set_density(self, nValue):
        CBash.SetFIDFieldUC(self._CollectionIndex, self._ModName, self._recordID, 9, c_ubyte(nValue))
    density = property(get_density, set_density)
    def get_minSlope(self):
        CBash.ReadFIDField.restype = POINTER(c_ubyte)
        retValue = CBash.ReadFIDField(self._CollectionIndex, self._ModName, self._recordID, 10)
        if(retValue): return retValue.contents.value
        return None
    def set_minSlope(self, nValue):
        CBash.SetFIDFieldUC(self._CollectionIndex, self._ModName, self._recordID, 10, c_ubyte(nValue))
    minSlope = property(get_minSlope, set_minSlope)
    def get_maxSlope(self):
        CBash.ReadFIDField.restype = POINTER(c_ubyte)
        retValue = CBash.ReadFIDField(self._CollectionIndex, self._ModName, self._recordID, 11)
        if(retValue): return retValue.contents.value
        return None
    def set_maxSlope(self, nValue):
        CBash.SetFIDFieldUC(self._CollectionIndex, self._ModName, self._recordID, 11, c_ubyte(nValue))
    maxSlope = property(get_maxSlope, set_maxSlope)
    def get_unused1(self):
        numRecords = CBash.GetFIDFieldArraySize(self._CollectionIndex, self._ModName, self._recordID, 12)
        if(numRecords > 0):
            cRecords = POINTER(c_ubyte * numRecords)()
            CBash.GetFIDFieldArray(self._CollectionIndex, self._ModName, self._recordID, 12, byref(cRecords))
            return [cRecords.contents[x] for x in range(0, numRecords)]
        return []
    def set_unused1(self, nValue):
        CBash.SetFIDFieldR(self._CollectionIndex, self._ModName, self._recordID, 12, struct.pack('B', *nValue), 1)
    unused1 = property(get_unused1, set_unused1)
    def get_waterDistance(self):
        CBash.ReadFIDField.restype = POINTER(c_ushort)
        retValue = CBash.ReadFIDField(self._CollectionIndex, self._ModName, self._recordID, 13)
        if(retValue): return retValue.contents.value
        return None
    def set_waterDistance(self, nValue):
        CBash.SetFIDFieldUS(self._CollectionIndex, self._ModName, self._recordID, 13, c_ushort(nValue))
    waterDistance = property(get_waterDistance, set_waterDistance)
    def get_unused2(self):
        numRecords = CBash.GetFIDFieldArraySize(self._CollectionIndex, self._ModName, self._recordID, 14)
        if(numRecords > 0):
            cRecords = POINTER(c_ubyte * numRecords)()
            CBash.GetFIDFieldArray(self._CollectionIndex, self._ModName, self._recordID, 14, byref(cRecords))
            return [cRecords.contents[x] for x in range(0, numRecords)]
        return []
    def set_unused2(self, nValue):
        CBash.SetFIDFieldR(self._CollectionIndex, self._ModName, self._recordID, 14, struct.pack('2B', *nValue), 2)
    unused2 = property(get_unused2, set_unused2)
    def get_waterOp(self):
        CBash.ReadFIDField.restype = POINTER(c_uint)
        retValue = CBash.ReadFIDField(self._CollectionIndex, self._ModName, self._recordID, 15)
        if(retValue): return retValue.contents.value
        return None
    def set_waterOp(self, nValue):
        CBash.SetFIDFieldUI(self._CollectionIndex, self._ModName, self._recordID, 15, nValue)
    waterOp = property(get_waterOp, set_waterOp)
    def get_posRange(self):
        CBash.ReadFIDField.restype = POINTER(c_float)
        retValue = CBash.ReadFIDField(self._CollectionIndex, self._ModName, self._recordID, 16)
        if(retValue): return retValue.contents.value
        return None
    def set_posRange(self, nValue):
        CBash.SetFIDFieldF(self._CollectionIndex, self._ModName, self._recordID, 16, c_float(nValue))
    posRange = property(get_posRange, set_posRange)
    def get_heightRange(self):
        CBash.ReadFIDField.restype = POINTER(c_float)
        retValue = CBash.ReadFIDField(self._CollectionIndex, self._ModName, self._recordID, 17)
        if(retValue): return retValue.contents.value
        return None
    def set_heightRange(self, nValue):
        CBash.SetFIDFieldF(self._CollectionIndex, self._ModName, self._recordID, 17, c_float(nValue))
    heightRange = property(get_heightRange, set_heightRange)
    def get_colorRange(self):
        CBash.ReadFIDField.restype = POINTER(c_float)
        retValue = CBash.ReadFIDField(self._CollectionIndex, self._ModName, self._recordID, 18)
        if(retValue): return retValue.contents.value
        return None
    def set_colorRange(self, nValue):
        CBash.SetFIDFieldF(self._CollectionIndex, self._ModName, self._recordID, 18, c_float(nValue))
    colorRange = property(get_colorRange, set_colorRange)
    def get_wavePeriod(self):
        CBash.ReadFIDField.restype = POINTER(c_float)
        retValue = CBash.ReadFIDField(self._CollectionIndex, self._ModName, self._recordID, 19)
        if(retValue): return retValue.contents.value
        return None
    def set_wavePeriod(self, nValue):
        CBash.SetFIDFieldF(self._CollectionIndex, self._ModName, self._recordID, 19, c_float(nValue))
    wavePeriod = property(get_wavePeriod, set_wavePeriod)
    def get_flags(self):
        CBash.ReadFIDField.restype = POINTER(c_ubyte)
        retValue = CBash.ReadFIDField(self._CollectionIndex, self._ModName, self._recordID, 20)
        if(retValue): return retValue.contents.value
        return None
    def set_flags(self, nValue):
        CBash.SetFIDFieldUC(self._CollectionIndex, self._ModName, self._recordID, 20, c_ubyte(nValue))
    flags = property(get_flags, set_flags)
    def get_unused3(self):
        numRecords = CBash.GetFIDFieldArraySize(self._CollectionIndex, self._ModName, self._recordID, 21)
        if(numRecords > 0):
            cRecords = POINTER(c_ubyte * numRecords)()
            CBash.GetFIDFieldArray(self._CollectionIndex, self._ModName, self._recordID, 21, byref(cRecords))
            return [cRecords.contents[x] for x in range(0, numRecords)]
        return []
    def set_unused3(self, nValue):
        CBash.SetFIDFieldR(self._CollectionIndex, self._ModName, self._recordID, 21, struct.pack('3B', *nValue), 3)
    unused3 = property(get_unused3, set_unused3)
    def get_IsVLighting(self):
        return (self.flags & 0x00000001) != 0
    def set_IsVLighting(self, nValue):
        if (nValue == True): self.flags |= 0x00000001
        else: self.flags &= ~0x00000001
    IsVLighting = property(get_IsVLighting, set_IsVLighting)
    def get_IsUScaling(self):
        return (self.flags & 0x00000002) != 0
    def set_IsUScaling(self, nValue):
        if (nValue == True): self.flags |= 0x00000002
        else: self.flags &= ~0x00000002
    IsUScaling = property(get_IsUScaling, set_IsUScaling)
    def get_IsFitSlope(self):
        return (self.flags & 0x00000004) != 0
    def set_IsFitSlope(self, nValue):
        if (nValue == True): self.flags |= 0x00000004
        else: self.flags &= ~0x00000004
    IsFitSlope = property(get_IsFitSlope, set_IsFitSlope)

class TREERecord(BaseRecord):
    def CopyAsOverride(self, targetMod):
        FID = CBash.CopyTREERecord(self._CollectionIndex, self._ModName, self._recordID, targetMod._ModName, c_bool(True))
        if(FID): return TREERecord(self._CollectionIndex, targetMod._ModName, FID)
        return None
    def CopyAsNew(self, targetMod):
        FID = CBash.CopyTREERecord(self._CollectionIndex, self._ModName, self._recordID, targetMod._ModName, c_bool(False))
        if(FID): return TREERecord(self._CollectionIndex, targetMod._ModName, FID)
        return None
    def get_modPath(self):
        CBash.ReadFIDField.restype = c_char_p
        return CBash.ReadFIDField(self._CollectionIndex, self._ModName, self._recordID, 6)
    def set_modPath(self, nValue):
        CBash.SetFIDFieldStr(self._CollectionIndex, self._ModName, self._recordID, 6, nValue)
    modPath = property(get_modPath, set_modPath)
    def get_modb(self):
        CBash.ReadFIDField.restype = POINTER(c_float)
        retValue = CBash.ReadFIDField(self._CollectionIndex, self._ModName, self._recordID, 7)
        if(retValue): return retValue.contents.value
        return None
    def set_modb(self, nValue):
        CBash.SetFIDFieldF(self._CollectionIndex, self._ModName, self._recordID, 7, c_float(nValue))
    modb = property(get_modb, set_modb)
    def get_modt_p(self):
        numRecords = CBash.GetFIDFieldArraySize(self._CollectionIndex, self._ModName, self._recordID, 8)
        if(numRecords > 0):
            cRecords = POINTER(c_ubyte * numRecords)()
            CBash.GetFIDFieldArray(self._CollectionIndex, self._ModName, self._recordID, 8, byref(cRecords))
            return [cRecords.contents[x] for x in range(0, numRecords)]
        return []
    def set_modt_p(self, nValue):
        length = len(nValue)
        CBash.SetFIDFieldR(self._CollectionIndex, self._ModName, self._recordID, 8, struct.pack('B' * length, *nValue), length)
    modt_p = property(get_modt_p, set_modt_p)
    def get_iconPath(self):
        CBash.ReadFIDField.restype = c_char_p
        return CBash.ReadFIDField(self._CollectionIndex, self._ModName, self._recordID, 9)
    def set_iconPath(self, nValue):
        CBash.SetFIDFieldStr(self._CollectionIndex, self._ModName, self._recordID, 9, nValue)
    iconPath = property(get_iconPath, set_iconPath)
    def get_speedTree(self):
        numRecords = CBash.GetFIDFieldArraySize(self._CollectionIndex, self._ModName, self._recordID, 10)
        if(numRecords > 0):
            cRecords = POINTER(c_uint * numRecords)()
            CBash.GetFIDFieldArray(self._CollectionIndex, self._ModName, self._recordID, 10, byref(cRecords))
            return [cRecords.contents[x] for x in range(0, numRecords)]
        return []
    def set_speedTree(self, nValue):
        CBash.SetFIDFieldUIA(self._CollectionIndex, self._ModName, self._recordID, 10, struct.pack('I' * len(nValue), *nValue), len(nValue))
    speedTree = property(get_speedTree, set_speedTree)
    def get_curvature(self):
        CBash.ReadFIDField.restype = POINTER(c_float)
        retValue = CBash.ReadFIDField(self._CollectionIndex, self._ModName, self._recordID, 11)
        if(retValue): return retValue.contents.value
        return None
    def set_curvature(self, nValue):
        CBash.SetFIDFieldF(self._CollectionIndex, self._ModName, self._recordID, 11, c_float(nValue))
    curvature = property(get_curvature, set_curvature)
    def get_minAngle(self):
        CBash.ReadFIDField.restype = POINTER(c_float)
        retValue = CBash.ReadFIDField(self._CollectionIndex, self._ModName, self._recordID, 12)
        if(retValue): return retValue.contents.value
        return None
    def set_minAngle(self, nValue):
        CBash.SetFIDFieldF(self._CollectionIndex, self._ModName, self._recordID, 12, c_float(nValue))
    minAngle = property(get_minAngle, set_minAngle)
    def get_maxAngle(self):
        CBash.ReadFIDField.restype = POINTER(c_float)
        retValue = CBash.ReadFIDField(self._CollectionIndex, self._ModName, self._recordID, 13)
        if(retValue): return retValue.contents.value
        return None
    def set_maxAngle(self, nValue):
        CBash.SetFIDFieldF(self._CollectionIndex, self._ModName, self._recordID, 13, c_float(nValue))
    maxAngle = property(get_maxAngle, set_maxAngle)
    def get_branchDim(self):
        CBash.ReadFIDField.restype = POINTER(c_float)
        retValue = CBash.ReadFIDField(self._CollectionIndex, self._ModName, self._recordID, 14)
        if(retValue): return retValue.contents.value
        return None
    def set_branchDim(self, nValue):
        CBash.SetFIDFieldF(self._CollectionIndex, self._ModName, self._recordID, 14, c_float(nValue))
    branchDim = property(get_branchDim, set_branchDim)
    def get_leafDim(self):
        CBash.ReadFIDField.restype = POINTER(c_float)
        retValue = CBash.ReadFIDField(self._CollectionIndex, self._ModName, self._recordID, 15)
        if(retValue): return retValue.contents.value
        return None
    def set_leafDim(self, nValue):
        CBash.SetFIDFieldF(self._CollectionIndex, self._ModName, self._recordID, 15, c_float(nValue))
    leafDim = property(get_leafDim, set_leafDim)
    def get_shadowRadius(self):
        CBash.ReadFIDField.restype = POINTER(c_int)
        retValue = CBash.ReadFIDField(self._CollectionIndex, self._ModName, self._recordID, 16)
        if(retValue): return retValue.contents.value
        return None
    def set_shadowRadius(self, nValue):
        CBash.SetFIDFieldI(self._CollectionIndex, self._ModName, self._recordID, 16, nValue)
    shadowRadius = property(get_shadowRadius, set_shadowRadius)
    def get_rockSpeed         (self):
        CBash.ReadFIDField.restype = POINTER(c_float)
        retValue = CBash.ReadFIDField(self._CollectionIndex, self._ModName, self._recordID, 17)
        if(retValue): return retValue.contents.value
        return None
    def set_rockSpeed         (self, nValue):
        CBash.SetFIDFieldF(self._CollectionIndex, self._ModName, self._recordID, 17, c_float(nValue))
    rockSpeed          = property(get_rockSpeed         , set_rockSpeed         )
    def get_rustleSpeed  (self):
        CBash.ReadFIDField.restype = POINTER(c_float)
        retValue = CBash.ReadFIDField(self._CollectionIndex, self._ModName, self._recordID, 18)
        if(retValue): return retValue.contents.value
        return None
    def set_rustleSpeed  (self, nValue):
        CBash.SetFIDFieldF(self._CollectionIndex, self._ModName, self._recordID, 18, c_float(nValue))
    rustleSpeed   = property(get_rustleSpeed  , set_rustleSpeed  )
    def get_widthBill(self):
        CBash.ReadFIDField.restype = POINTER(c_float)
        retValue = CBash.ReadFIDField(self._CollectionIndex, self._ModName, self._recordID, 19)
        if(retValue): return retValue.contents.value
        return None
    def set_widthBill(self, nValue):
        CBash.SetFIDFieldF(self._CollectionIndex, self._ModName, self._recordID, 19, c_float(nValue))
    widthBill = property(get_widthBill, set_widthBill)
    def get_heightBill(self):
        CBash.ReadFIDField.restype = POINTER(c_float)
        retValue = CBash.ReadFIDField(self._CollectionIndex, self._ModName, self._recordID, 20)
        if(retValue): return retValue.contents.value
        return None
    def set_heightBill(self, nValue):
        CBash.SetFIDFieldF(self._CollectionIndex, self._ModName, self._recordID, 20, c_float(nValue))
    heightBill = property(get_heightBill, set_heightBill)
class FLORRecord(BaseRecord):
    def CopyAsOverride(self, targetMod):
        FID = CBash.CopyFLORRecord(self._CollectionIndex, self._ModName, self._recordID, targetMod._ModName, c_bool(True))
        if(FID): return FLORRecord(self._CollectionIndex, targetMod._ModName, FID)
        return None
    def CopyAsNew(self, targetMod):
        FID = CBash.CopyFLORRecord(self._CollectionIndex, self._ModName, self._recordID, targetMod._ModName, c_bool(False))
        if(FID): return FLORRecord(self._CollectionIndex, targetMod._ModName, FID)
        return None
    def get_full(self):
        CBash.ReadFIDField.restype = c_char_p
        return CBash.ReadFIDField(self._CollectionIndex, self._ModName, self._recordID, 6)
    def set_full(self, nValue):
        CBash.SetFIDFieldStr(self._CollectionIndex, self._ModName, self._recordID, 6, nValue)
    full = property(get_full, set_full)
    def get_modPath(self):
        CBash.ReadFIDField.restype = c_char_p
        return CBash.ReadFIDField(self._CollectionIndex, self._ModName, self._recordID, 7)
    def set_modPath(self, nValue):
        CBash.SetFIDFieldStr(self._CollectionIndex, self._ModName, self._recordID, 7, nValue)
    modPath = property(get_modPath, set_modPath)
    def get_modb(self):
        CBash.ReadFIDField.restype = POINTER(c_float)
        retValue = CBash.ReadFIDField(self._CollectionIndex, self._ModName, self._recordID, 8)
        if(retValue): return retValue.contents.value
        return None
    def set_modb(self, nValue):
        CBash.SetFIDFieldF(self._CollectionIndex, self._ModName, self._recordID, 8, c_float(nValue))
    modb = property(get_modb, set_modb)
    def get_modt_p(self):
        numRecords = CBash.GetFIDFieldArraySize(self._CollectionIndex, self._ModName, self._recordID, 9)
        if(numRecords > 0):
            cRecords = POINTER(c_ubyte * numRecords)()
            CBash.GetFIDFieldArray(self._CollectionIndex, self._ModName, self._recordID, 9, byref(cRecords))
            return [cRecords.contents[x] for x in range(0, numRecords)]
        return []
    def set_modt_p(self, nValue):
        length = len(nValue)
        CBash.SetFIDFieldR(self._CollectionIndex, self._ModName, self._recordID, 9, struct.pack('B' * length, *nValue), length)
    modt_p = property(get_modt_p, set_modt_p)
    def get_script(self):
        CBash.ReadFIDField.restype = POINTER(c_uint)
        retValue = CBash.ReadFIDField(self._CollectionIndex, self._ModName, self._recordID, 10)
        if(retValue): return retValue.contents.value
        return None
    def set_script(self, nValue):
        CBash.SetFIDFieldUI(self._CollectionIndex, self._ModName, self._recordID, 10, nValue)
    script = property(get_script, set_script)
    def get_ingredient(self):
        CBash.ReadFIDField.restype = POINTER(c_uint)
        retValue = CBash.ReadFIDField(self._CollectionIndex, self._ModName, self._recordID, 11)
        if(retValue): return retValue.contents.value
        return None
    def set_ingredient(self, nValue):
        CBash.SetFIDFieldUI(self._CollectionIndex, self._ModName, self._recordID, 11, nValue)
    ingredient = property(get_ingredient, set_ingredient)
    def get_spring(self):
        CBash.ReadFIDField.restype = POINTER(c_ubyte)
        retValue = CBash.ReadFIDField(self._CollectionIndex, self._ModName, self._recordID, 12)
        if(retValue): return retValue.contents.value
        return None
    def set_spring(self, nValue):
        CBash.SetFIDFieldUC(self._CollectionIndex, self._ModName, self._recordID, 12, c_ubyte(nValue))
    spring = property(get_spring, set_spring)
    def get_summer(self):
        CBash.ReadFIDField.restype = POINTER(c_ubyte)
        retValue = CBash.ReadFIDField(self._CollectionIndex, self._ModName, self._recordID, 13)
        if(retValue): return retValue.contents.value
        return None
    def set_summer(self, nValue):
        CBash.SetFIDFieldUC(self._CollectionIndex, self._ModName, self._recordID, 13, c_ubyte(nValue))
    summer = property(get_summer, set_summer)
    def get_fall(self):
        CBash.ReadFIDField.restype = POINTER(c_ubyte)
        retValue = CBash.ReadFIDField(self._CollectionIndex, self._ModName, self._recordID, 14)
        if(retValue): return retValue.contents.value
        return None
    def set_fall(self, nValue):
        CBash.SetFIDFieldUC(self._CollectionIndex, self._ModName, self._recordID, 14, c_ubyte(nValue))
    fall = property(get_fall, set_fall)
    def get_winter(self):
        CBash.ReadFIDField.restype = POINTER(c_ubyte)
        retValue = CBash.ReadFIDField(self._CollectionIndex, self._ModName, self._recordID, 15)
        if(retValue): return retValue.contents.value
        return None
    def set_winter(self, nValue):
        CBash.SetFIDFieldUC(self._CollectionIndex, self._ModName, self._recordID, 15, c_ubyte(nValue))
    winter = property(get_winter, set_winter)
class FURNRecord(BaseRecord):
    def CopyAsOverride(self, targetMod):
        FID = CBash.CopyFURNRecord(self._CollectionIndex, self._ModName, self._recordID, targetMod._ModName, c_bool(True))
        if(FID): return FURNRecord(self._CollectionIndex, targetMod._ModName, FID)
        return None
    def CopyAsNew(self, targetMod):
        FID = CBash.CopyFURNRecord(self._CollectionIndex, self._ModName, self._recordID, targetMod._ModName, c_bool(False))
        if(FID): return FURNRecord(self._CollectionIndex, targetMod._ModName, FID)
        return None
    def get_full(self):
        CBash.ReadFIDField.restype = c_char_p
        return CBash.ReadFIDField(self._CollectionIndex, self._ModName, self._recordID, 6)
    def set_full(self, nValue):
        CBash.SetFIDFieldStr(self._CollectionIndex, self._ModName, self._recordID, 6, nValue)
    full = property(get_full, set_full)
    def get_modPath(self):
        CBash.ReadFIDField.restype = c_char_p
        return CBash.ReadFIDField(self._CollectionIndex, self._ModName, self._recordID, 7)
    def set_modPath(self, nValue):
        CBash.SetFIDFieldStr(self._CollectionIndex, self._ModName, self._recordID, 7, nValue)
    modPath = property(get_modPath, set_modPath)
    def get_modb(self):
        CBash.ReadFIDField.restype = POINTER(c_float)
        retValue = CBash.ReadFIDField(self._CollectionIndex, self._ModName, self._recordID, 8)
        if(retValue): return retValue.contents.value
        return None
    def set_modb(self, nValue):
        CBash.SetFIDFieldF(self._CollectionIndex, self._ModName, self._recordID, 8, c_float(nValue))
    modb = property(get_modb, set_modb)
    def get_modt_p(self):
        numRecords = CBash.GetFIDFieldArraySize(self._CollectionIndex, self._ModName, self._recordID, 9)
        if(numRecords > 0):
            cRecords = POINTER(c_ubyte * numRecords)()
            CBash.GetFIDFieldArray(self._CollectionIndex, self._ModName, self._recordID, 9, byref(cRecords))
            return [cRecords.contents[x] for x in range(0, numRecords)]
        return []
    def set_modt_p(self, nValue):
        length = len(nValue)
        CBash.SetFIDFieldR(self._CollectionIndex, self._ModName, self._recordID, 9, struct.pack('B' * length, *nValue), length)
    modt_p = property(get_modt_p, set_modt_p)
    def get_script(self):
        CBash.ReadFIDField.restype = POINTER(c_uint)
        retValue = CBash.ReadFIDField(self._CollectionIndex, self._ModName, self._recordID, 10)
        if(retValue): return retValue.contents.value
        return None
    def set_script(self, nValue):
        CBash.SetFIDFieldUI(self._CollectionIndex, self._ModName, self._recordID, 10, c_uint(nValue))
    script = property(get_script, set_script)
    def get_flags(self):
        CBash.ReadFIDField.restype = POINTER(c_uint)
        retValue = CBash.ReadFIDField(self._CollectionIndex, self._ModName, self._recordID, 11)
        if(retValue): return retValue.contents.value
        return None
    def set_flags(self, nValue):
        CBash.SetFIDFieldUI(self._CollectionIndex, self._ModName, self._recordID, 11, nValue)
    flags = property(get_flags, set_flags)
    def get_IsAnim01(self):
        return (self.flags & 0x00000001) != 0
    def set_IsAnim01(self, nValue):
        if (nValue == True): self.flags |= 0x00000001
        else: self.flags &= ~0x00000001
    IsAnim01 = property(get_IsAnim01, set_IsAnim01)
    def get_IsAnim02(self):
        return (self.flags & 0x00000002) != 0
    def set_IsAnim02(self, nValue):
        if (nValue == True): self.flags |= 0x00000002
        else: self.flags &= ~0x00000002
    IsAnim02 = property(get_IsAnim02, set_IsAnim02)
    def get_IsAnim03(self):
        return (self.flags & 0x00000004) != 0
    def set_IsAnim03(self, nValue):
        if (nValue == True): self.flags |= 0x00000004
        else: self.flags &= ~0x00000004
    IsAnim03 = property(get_IsAnim03, set_IsAnim03)
    def get_IsAnim04(self):
        return (self.flags & 0x00000008) != 0
    def set_IsAnim04(self, nValue):
        if (nValue == True): self.flags |= 0x00000008
        else: self.flags &= ~0x00000008
    IsAnim04 = property(get_IsAnim04, set_IsAnim04)
    def get_IsAnim05(self):
        return (self.flags & 0x00000010) != 0
    def set_IsAnim05(self, nValue):
        if (nValue == True): self.flags |= 0x00000010
        else: self.flags &= ~0x00000010
    IsAnim05 = property(get_IsAnim05, set_IsAnim05)
    def get_IsAnim06(self):
        return (self.flags & 0x00000020) != 0
    def set_IsAnim06(self, nValue):
        if (nValue == True): self.flags |= 0x00000020
        else: self.flags &= ~0x00000020
    IsAnim06 = property(get_IsAnim06, set_IsAnim06)
    def get_IsAnim07(self):
        return (self.flags & 0x00000040) != 0
    def set_IsAnim07(self, nValue):
        if (nValue == True): self.flags |= 0x00000040
        else: self.flags &= ~0x00000040
    IsAnim07 = property(get_IsAnim07, set_IsAnim07)
    def get_IsAnim08(self):
        return (self.flags & 0x00000080) != 0
    def set_IsAnim08(self, nValue):
        if (nValue == True): self.flags |= 0x00000080
        else: self.flags &= ~0x00000080
    IsAnim08 = property(get_IsAnim08, set_IsAnim08)
    def get_IsAnim09(self):
        return (self.flags & 0x00000100) != 0
    def set_IsAnim09(self, nValue):
        if (nValue == True): self.flags |= 0x00000100
        else: self.flags &= ~0x00000100
    IsAnim09 = property(get_IsAnim09, set_IsAnim09)
    def get_IsAnim10(self):
        return (self.flags & 0x00000200) != 0
    def set_IsAnim10(self, nValue):
        if (nValue == True): self.flags |= 0x00000200
        else: self.flags &= ~0x00000200
    IsAnim10 = property(get_IsAnim10, set_IsAnim10)
    def get_IsAnim11(self):
        return (self.flags & 0x00000400) != 0
    def set_IsAnim11(self, nValue):
        if (nValue == True): self.flags |= 0x00000400
        else: self.flags &= ~0x00000400
    IsAnim11 = property(get_IsAnim11, set_IsAnim11)
    def get_IsAnim12(self):
        return (self.flags & 0x00000800) != 0
    def set_IsAnim12(self, nValue):
        if (nValue == True): self.flags |= 0x00000800
        else: self.flags &= ~0x00000800
    IsAnim12 = property(get_IsAnim12, set_IsAnim12)
    def get_IsAnim13(self):
        return (self.flags & 0x00001000) != 0
    def set_IsAnim13(self, nValue):
        if (nValue == True): self.flags |= 0x00001000
        else: self.flags &= ~0x00001000
    IsAnim13 = property(get_IsAnim13, set_IsAnim13)
    def get_IsAnim14(self):
        return (self.flags & 0x00002000) != 0
    def set_IsAnim14(self, nValue):
        if (nValue == True): self.flags |= 0x00002000
        else: self.flags &= ~0x00002000
    IsAnim14 = property(get_IsAnim14, set_IsAnim14)
    def get_IsAnim15(self):
        return (self.flags & 0x00004000) != 0
    def set_IsAnim15(self, nValue):
        if (nValue == True): self.flags |= 0x00004000
        else: self.flags &= ~0x00004000
    IsAnim15 = property(get_IsAnim15, set_IsAnim15)
    def get_IsAnim16(self):
        return (self.flags & 0x00008000) != 0
    def set_IsAnim16(self, nValue):
        if (nValue == True): self.flags |= 0x00008000
        else: self.flags &= ~0x00008000
    IsAnim16 = property(get_IsAnim16, set_IsAnim16)
    def get_IsAnim17(self):
        return (self.flags & 0x00010000) != 0
    def set_IsAnim17(self, nValue):
        if (nValue == True): self.flags |= 0x00010000
        else: self.flags &= ~0x00010000
    IsAnim17 = property(get_IsAnim17, set_IsAnim17)
    def get_IsAnim18(self):
        return (self.flags & 0x00020000) != 0
    def set_IsAnim18(self, nValue):
        if (nValue == True): self.flags |= 0x00020000
        else: self.flags &= ~0x00020000
    IsAnim18 = property(get_IsAnim18, set_IsAnim18)
    def get_IsAnim19(self):
        return (self.flags & 0x00040000) != 0
    def set_IsAnim19(self, nValue):
        if (nValue == True): self.flags |= 0x00040000
        else: self.flags &= ~0x00040000
    IsAnim19 = property(get_IsAnim19, set_IsAnim19)
    def get_IsAnim20(self):
        return (self.flags & 0x00080000) != 0
    def set_IsAnim20(self, nValue):
        if (nValue == True): self.flags |= 0x00080000
        else: self.flags &= ~0x00080000
    IsAnim20 = property(get_IsAnim20, set_IsAnim20)
    def get_IsAnim21(self):
        return (self.flags & 0x00100000) != 0
    def set_IsAnim21(self, nValue):
        if (nValue == True): self.flags |= 0x00100000
        else: self.flags &= ~0x00100000
    IsAnim21 = property(get_IsAnim21, set_IsAnim21)
    def get_IsAnim22(self):
        return (self.flags & 0x00200000) != 0
    def set_IsAnim22(self, nValue):
        if (nValue == True): self.flags |= 0x00200000
        else: self.flags &= ~0x00200000
    IsAnim22 = property(get_IsAnim22, set_IsAnim22)
    def get_IsAnim23(self):
        return (self.flags & 0x00400000) != 0
    def set_IsAnim23(self, nValue):
        if (nValue == True): self.flags |= 0x00400000
        else: self.flags &= ~0x00400000
    IsAnim23 = property(get_IsAnim23, set_IsAnim23)
    def get_IsAnim24(self):
        return (self.flags & 0x00800000) != 0
    def set_IsAnim24(self, nValue):
        if (nValue == True): self.flags |= 0x00800000
        else: self.flags &= ~0x00800000
    IsAnim24 = property(get_IsAnim24, set_IsAnim24)
    def get_IsAnim25(self):
        return (self.flags & 0x01000000) != 0
    def set_IsAnim25(self, nValue):
        if (nValue == True): self.flags |= 0x01000000
        else: self.flags &= ~0x01000000
    IsAnim25 = property(get_IsAnim25, set_IsAnim25)
    def get_IsAnim26(self):
        return (self.flags & 0x02000000) != 0
    def set_IsAnim26(self, nValue):
        if (nValue == True): self.flags |= 0x02000000
        else: self.flags &= ~0x02000000
    IsAnim26 = property(get_IsAnim26, set_IsAnim26)
    def get_IsAnim27(self):
        return (self.flags & 0x04000000) != 0
    def set_IsAnim27(self, nValue):
        if (nValue == True): self.flags |= 0x04000000
        else: self.flags &= ~0x04000000
    IsAnim27 = property(get_IsAnim27, set_IsAnim27)
    def get_IsAnim28(self):
        return (self.flags & 0x08000000) != 0
    def set_IsAnim28(self, nValue):
        if (nValue == True): self.flags |= 0x08000000
        else: self.flags &= ~0x08000000
    IsAnim28 = property(get_IsAnim28, set_IsAnim28)
    def get_IsAnim29(self):
        return (self.flags & 0x10000000) != 0
    def set_IsAnim29(self, nValue):
        if (nValue == True): self.flags |= 0x10000000
        else: self.flags &= ~0x10000000
    IsAnim29 = property(get_IsAnim29, set_IsAnim29)
    def get_IsAnim30(self):
        return (self.flags & 0x20000000) != 0
    def set_IsAnim30(self, nValue):
        if (nValue == True): self.flags |= 0x20000000
        else: self.flags &= ~0x20000000
    IsAnim30 = property(get_IsAnim30, set_IsAnim30)
    def get_IsSitAnim(self):
        return (self.flags & 0x40000000) != 0
    def set_IsSitAnim(self, nValue):
        if (nValue == True):
            self.flags |= 0x40000000
            self.flags &= ~0x80000000
        else:
            self.flags &= ~0x40000000
            self.flags |= 0x80000000
    IsSitAnim = property(get_IsSitAnim, set_IsSitAnim)
    def get_IsSleepAnim(self):
        return (self.flags & 0x80000000) != 0
    def set_IsSleepAnim(self, nValue):
        if (nValue == True):
            self.flags &= ~0x40000000
            self.flags |= 0x80000000
        else:
            self.flags |= 0x40000000
            self.flags &= ~0x80000000
    IsSleepAnim = property(get_IsSleepAnim, set_IsSleepAnim)
    
class WEAPRecord(BaseRecord):
    def CopyAsOverride(self, targetMod):
        FID = CBash.CopyWEAPRecord(self._CollectionIndex, self._ModName, self._recordID, targetMod._ModName, c_bool(True))
        if(FID): return WEAPRecord(self._CollectionIndex, targetMod._ModName, FID)
        return None
    def CopyAsNew(self, targetMod):
        FID = CBash.CopyWEAPRecord(self._CollectionIndex, self._ModName, self._recordID, targetMod._ModName, c_bool(False))
        if(FID): return WEAPRecord(self._CollectionIndex, targetMod._ModName, FID)
        return None
    def get_full(self):
        CBash.ReadFIDField.restype = c_char_p
        return CBash.ReadFIDField(self._CollectionIndex, self._ModName, self._recordID, 6)
    def set_full(self, nValue):
        CBash.SetFIDFieldStr(self._CollectionIndex, self._ModName, self._recordID, 6, nValue)
    full = property(get_full, set_full)
    def get_modPath(self):
        CBash.ReadFIDField.restype = c_char_p
        return CBash.ReadFIDField(self._CollectionIndex, self._ModName, self._recordID, 7)
    def set_modPath(self, nValue):
        CBash.SetFIDFieldStr(self._CollectionIndex, self._ModName, self._recordID, 7, nValue)
    modPath = property(get_modPath, set_modPath)
    def get_modb(self):
        CBash.ReadFIDField.restype = POINTER(c_float)
        retValue = CBash.ReadFIDField(self._CollectionIndex, self._ModName, self._recordID, 8)
        if(retValue): return retValue.contents.value
        return None
    def set_modb(self, nValue):
        CBash.SetFIDFieldF(self._CollectionIndex, self._ModName, self._recordID, 8, c_float(nValue))
    modb = property(get_modb, set_modb)
    def get_modt_p(self):
        numRecords = CBash.GetFIDFieldArraySize(self._CollectionIndex, self._ModName, self._recordID, 9)
        if(numRecords > 0):
            cRecords = POINTER(c_ubyte * numRecords)()
            CBash.GetFIDFieldArray(self._CollectionIndex, self._ModName, self._recordID, 9, byref(cRecords))
            return [cRecords.contents[x] for x in range(0, numRecords)]
        return []
    def set_modt_p(self, nValue):
        length = len(nValue)
        CBash.SetFIDFieldR(self._CollectionIndex, self._ModName, self._recordID, 9, struct.pack('B' * length, *nValue), length)
    modt_p = property(get_modt_p, set_modt_p)
    def get_iconPath(self):
        CBash.ReadFIDField.restype = c_char_p
        return CBash.ReadFIDField(self._CollectionIndex, self._ModName, self._recordID, 10)
    def set_iconPath(self, nValue):
        CBash.SetFIDFieldStr(self._CollectionIndex, self._ModName, self._recordID, 10, nValue)
    iconPath = property(get_iconPath, set_iconPath)
    def get_script(self):
        CBash.ReadFIDField.restype = POINTER(c_uint)
        retValue = CBash.ReadFIDField(self._CollectionIndex, self._ModName, self._recordID, 11)
        if(retValue): return retValue.contents.value
        return None
    def set_script(self, nValue):
        CBash.SetFIDFieldUI(self._CollectionIndex, self._ModName, self._recordID, 11, c_uint(nValue))
    script = property(get_script, set_script)
    def get_enchantment(self):
        CBash.ReadFIDField.restype = POINTER(c_uint)
        retValue = CBash.ReadFIDField(self._CollectionIndex, self._ModName, self._recordID, 12)
        if(retValue): return retValue.contents.value
        return None
    def set_enchantment(self, nValue):
        CBash.SetFIDFieldUI(self._CollectionIndex, self._ModName, self._recordID, 12, nValue)
    enchantment = property(get_enchantment, set_enchantment)
    def get_enchantPoints(self):
        CBash.ReadFIDField.restype = POINTER(c_ushort)
        retValue = CBash.ReadFIDField(self._CollectionIndex, self._ModName, self._recordID, 13)
        if(retValue): return retValue.contents.value
        return None
    def set_enchantPoints(self, nValue):
        CBash.SetFIDFieldUS(self._CollectionIndex, self._ModName, self._recordID, 13, c_ushort(nValue))
    enchantPoints = property(get_enchantPoints, set_enchantPoints)                    
    def get_weaponType(self):
        CBash.ReadFIDField.restype = POINTER(c_uint)
        retValue = CBash.ReadFIDField(self._CollectionIndex, self._ModName, self._recordID, 14)
        if(retValue): return retValue.contents.value
        return None
    def set_weaponType(self, nValue):
        CBash.SetFIDFieldUI(self._CollectionIndex, self._ModName, self._recordID, 14, nValue)
    weaponType = property(get_weaponType, set_weaponType)
    def get_speed(self):
        CBash.ReadFIDField.restype = POINTER(c_float)
        retValue = CBash.ReadFIDField(self._CollectionIndex, self._ModName, self._recordID, 15)
        if(retValue): return retValue.contents.value
        return None
    def set_speed(self, nValue):
        CBash.SetFIDFieldF(self._CollectionIndex, self._ModName, self._recordID, 15, c_float(nValue))
    speed = property(get_speed, set_speed)
    def get_reach(self):
        CBash.ReadFIDField.restype = POINTER(c_float)
        retValue = CBash.ReadFIDField(self._CollectionIndex, self._ModName, self._recordID, 16)
        if(retValue): return retValue.contents.value
        return None
    def set_reach(self, nValue):
        CBash.SetFIDFieldF(self._CollectionIndex, self._ModName, self._recordID, 16, c_float(nValue))
    reach = property(get_reach, set_reach)
    def get_flags(self):
        CBash.ReadFIDField.restype = POINTER(c_uint)
        retValue = CBash.ReadFIDField(self._CollectionIndex, self._ModName, self._recordID, 17)
        if(retValue): return retValue.contents.value
        return None
    def set_flags(self, nValue):
        CBash.SetFIDFieldUI(self._CollectionIndex, self._ModName, self._recordID, 17, nValue)
    flags = property(get_flags, set_flags)
    def get_value(self):
        CBash.ReadFIDField.restype = POINTER(c_uint)
        retValue = CBash.ReadFIDField(self._CollectionIndex, self._ModName, self._recordID, 18)
        if(retValue): return retValue.contents.value
        return None
    def set_value(self, nValue):
        CBash.SetFIDFieldUI(self._CollectionIndex, self._ModName, self._recordID, 18, nValue)
    value = property(get_value, set_value)
    def get_health(self):
        CBash.ReadFIDField.restype = POINTER(c_uint)
        retValue = CBash.ReadFIDField(self._CollectionIndex, self._ModName, self._recordID, 19)
        if(retValue): return retValue.contents.value
        return None
    def set_health(self, nValue):
        CBash.SetFIDFieldUI(self._CollectionIndex, self._ModName, self._recordID, 19, nValue)
    health = property(get_health, set_health)
    def get_weight(self):
        CBash.ReadFIDField.restype = POINTER(c_float)
        retValue = CBash.ReadFIDField(self._CollectionIndex, self._ModName, self._recordID, 20)
        if(retValue): return retValue.contents.value
        return None
    def set_weight(self, nValue):
        CBash.SetFIDFieldF(self._CollectionIndex, self._ModName, self._recordID, 20, c_float(nValue))
    weight = property(get_weight, set_weight)
    def get_damage(self):
        CBash.ReadFIDField.restype = POINTER(c_ushort)
        retValue = CBash.ReadFIDField(self._CollectionIndex, self._ModName, self._recordID, 21)
        if(retValue): return retValue.contents.value
        return None
    def set_damage(self, nValue):
        CBash.SetFIDFieldUS(self._CollectionIndex, self._ModName, self._recordID, 21, c_ushort(nValue))
    damage = property(get_damage, set_damage)
    def get_IsNotNormalWeapon(self):
        return (self.flags & 0x00000001) != 0
    def set_IsNotNormalWeapon(self, nValue):
        if (nValue == True): self.flags |= 0x00000001
        else: self.flags &= ~0x00000001
    IsNotNormal = IsNotNormalWeapon = property(get_IsNotNormalWeapon, set_IsNotNormalWeapon)
    def get_IsNormalWeapon(self):
        return (self.flags & 0x00000001) == 0
    def set_IsNormalWeapon(self, nValue):
        if (nValue == True): self.flags &= ~0x00000001
        else: self.flags |= 0x00000001
    IsNormal = IsNormalWeapon = property(get_IsNormalWeapon, set_IsNormalWeapon)
    def get_IsBlade1Hand(self):
        return (self.weaponType == 0)
    def set_IsBlade1Hand(self, nValue):
        if (nValue == True): self.weaponType = 0
        else: self.IsBlade2Hand = True
    IsBlade1Hand = property(get_IsBlade1Hand, set_IsBlade1Hand)
    def get_IsBlade2Hand(self):
        return (self.weaponType == 1)
    def set_IsBlade2Hand(self, nValue):
        if (nValue == True): self.weaponType = 1
        else: self.IsBlade1Hand = True
    IsBlade2Hand = property(get_IsBlade2Hand, set_IsBlade2Hand)
    def get_IsBlunt1Hand(self):
        return (self.weaponType == 2)
    def set_IsBlunt1Hand(self, nValue):
        if (nValue == True): self.weaponType = 2
        else: self.IsBlade1Hand = True
    IsBlunt1Hand = property(get_IsBlunt1Hand, set_IsBlunt1Hand)
    def get_IsBlunt2Hand(self):
        return (self.weaponType == 3)
    def set_IsBlunt2Hand(self, nValue):
        if (nValue == True): self.weaponType = 3
        else: self.IsBlade1Hand = True
    IsBlunt2Hand = property(get_IsBlunt2Hand, set_IsBlunt2Hand)
    def get_IsStaff(self):
        return (self.weaponType == 4)
    def set_IsStaff(self, nValue):
        if (nValue == True): self.weaponType = 4
        else: self.IsBlade1Hand = True
    IsStaff = property(get_IsStaff, set_IsStaff)
    def get_IsBow(self):
        return (self.weaponType == 5)
    def set_IsBow(self, nValue):
        if (nValue == True): self.weaponType = 5
        else: self.IsBlade1Hand = True
    IsBow = property(get_IsBow, set_IsBow)
    
class AMMORecord(BaseRecord):
    def CopyAsOverride(self, targetMod):
        FID = CBash.CopyAMMORecord(self._CollectionIndex, self._ModName, self._recordID, targetMod._ModName, c_bool(True))
        if(FID): return AMMORecord(self._CollectionIndex, targetMod._ModName, FID)
        return None
    def CopyAsNew(self, targetMod):
        FID = CBash.CopyAMMORecord(self._CollectionIndex, self._ModName, self._recordID, targetMod._ModName, c_bool(False))
        if(FID): return AMMORecord(self._CollectionIndex, targetMod._ModName, FID)
        return None
    def get_full(self):
        CBash.ReadFIDField.restype = c_char_p
        return CBash.ReadFIDField(self._CollectionIndex, self._ModName, self._recordID, 6)
    def set_full(self, nValue):
        CBash.SetFIDFieldStr(self._CollectionIndex, self._ModName, self._recordID, 6, nValue)
    full = property(get_full, set_full)
    def get_modPath(self):
        CBash.ReadFIDField.restype = c_char_p
        return CBash.ReadFIDField(self._CollectionIndex, self._ModName, self._recordID, 7)
    def set_modPath(self, nValue):
        CBash.SetFIDFieldStr(self._CollectionIndex, self._ModName, self._recordID, 7, nValue)
    modPath = property(get_modPath, set_modPath)
    def get_modb(self):
        CBash.ReadFIDField.restype = POINTER(c_float)
        retValue = CBash.ReadFIDField(self._CollectionIndex, self._ModName, self._recordID, 8)
        if(retValue): return retValue.contents.value
        return None
    def set_modb(self, nValue):
        CBash.SetFIDFieldF(self._CollectionIndex, self._ModName, self._recordID, 8, c_float(nValue))
    modb = property(get_modb, set_modb)
    def get_modt_p(self):
        numRecords = CBash.GetFIDFieldArraySize(self._CollectionIndex, self._ModName, self._recordID, 9)
        if(numRecords > 0):
            cRecords = POINTER(c_ubyte * numRecords)()
            CBash.GetFIDFieldArray(self._CollectionIndex, self._ModName, self._recordID, 9, byref(cRecords))
            return [cRecords.contents[x] for x in range(0, numRecords)]
        return []
    def set_modt_p(self, nValue):
        length = len(nValue)
        CBash.SetFIDFieldR(self._CollectionIndex, self._ModName, self._recordID, 9, struct.pack('B' * length, *nValue), length)
    modt_p = property(get_modt_p, set_modt_p)
    def get_iconPath(self):
        CBash.ReadFIDField.restype = c_char_p
        return CBash.ReadFIDField(self._CollectionIndex, self._ModName, self._recordID, 10)
    def set_iconPath(self, nValue):
        CBash.SetFIDFieldStr(self._CollectionIndex, self._ModName, self._recordID, 10, nValue)
    iconPath = property(get_iconPath, set_iconPath)
    def get_enchantment(self):
        CBash.ReadFIDField.restype = POINTER(c_uint)
        retValue = CBash.ReadFIDField(self._CollectionIndex, self._ModName, self._recordID, 11)
        if(retValue): return retValue.contents.value
        return None
    def set_enchantment(self, nValue):
        CBash.SetFIDFieldUI(self._CollectionIndex, self._ModName, self._recordID, 11, nValue)
    enchantment = property(get_enchantment, set_enchantment)
    def get_enchantPoints(self):
        CBash.ReadFIDField.restype = POINTER(c_ushort)
        retValue = CBash.ReadFIDField(self._CollectionIndex, self._ModName, self._recordID, 12)
        if(retValue): return retValue.contents.value
        return None
    def set_enchantPoints(self, nValue):
        CBash.SetFIDFieldUS(self._CollectionIndex, self._ModName, self._recordID, 12, c_ushort(nValue))
    enchantPoints = property(get_enchantPoints, set_enchantPoints)     
    def get_speed(self):
        CBash.ReadFIDField.restype = POINTER(c_float)
        retValue = CBash.ReadFIDField(self._CollectionIndex, self._ModName, self._recordID, 13)
        if(retValue): return retValue.contents.value
        return None
    def set_speed(self, nValue):
        CBash.SetFIDFieldF(self._CollectionIndex, self._ModName, self._recordID, 13, c_float(nValue))
    speed = property(get_speed, set_speed)  
    def get_flags(self):
        CBash.ReadFIDField.restype = POINTER(c_uint)
        retValue = CBash.ReadFIDField(self._CollectionIndex, self._ModName, self._recordID, 14)
        if(retValue): return retValue.contents.value
        return None
    def set_flags(self, nValue):
        CBash.SetFIDFieldUI(self._CollectionIndex, self._ModName, self._recordID, 14, nValue)
    flags = property(get_flags, set_flags)
    def get_unused1(self):
        numRecords = CBash.GetFIDFieldArraySize(self._CollectionIndex, self._ModName, self._recordID, 15)
        if(numRecords > 0):
            cRecords = POINTER(c_ubyte * numRecords)()
            CBash.GetFIDFieldArray(self._CollectionIndex, self._ModName, self._recordID, 15, byref(cRecords))
            return [cRecords.contents[x] for x in range(0, numRecords)]
        return []
    def set_unused1(self, nValue):
        CBash.SetFIDFieldR(self._CollectionIndex, self._ModName, self._recordID, 15, struct.pack('3B', *nValue), 3)
    unused1 = property(get_unused1, set_unused1)
    def get_value(self):
        CBash.ReadFIDField.restype = POINTER(c_uint)
        retValue = CBash.ReadFIDField(self._CollectionIndex, self._ModName, self._recordID, 16)
        if(retValue): return retValue.contents.value
        return None
    def set_value(self, nValue):
        CBash.SetFIDFieldUI(self._CollectionIndex, self._ModName, self._recordID, 16, nValue)
    value = property(get_value, set_value)
    def get_weight(self):
        CBash.ReadFIDField.restype = POINTER(c_float)
        retValue = CBash.ReadFIDField(self._CollectionIndex, self._ModName, self._recordID, 17)
        if(retValue): return retValue.contents.value
        return None
    def set_weight(self, nValue):
        CBash.SetFIDFieldF(self._CollectionIndex, self._ModName, self._recordID, 17, c_float(nValue))
    weight = property(get_weight, set_weight)
    def get_damage(self):
        CBash.ReadFIDField.restype = POINTER(c_ushort)
        retValue = CBash.ReadFIDField(self._CollectionIndex, self._ModName, self._recordID, 18)
        if(retValue): return retValue.contents.value
        return None
    def set_damage(self, nValue):
        CBash.SetFIDFieldUS(self._CollectionIndex, self._ModName, self._recordID, 18, c_ushort(nValue))
    damage = property(get_damage, set_damage)
    def get_IsNotNormalWeapon(self):
        return (self.flags & 0x00000001) != 0
    def set_IsNotNormalWeapon(self, nValue):
        if (nValue == True): self.flags |= 0x00000001
        else: self.flags &= ~0x00000001
    IsNotNormal = IsNotNormalWeapon = property(get_IsNotNormalWeapon, set_IsNotNormalWeapon)
    def get_IsNormalWeapon(self):
        return (self.flags & 0x00000001) == 0
    def set_IsNormalWeapon(self, nValue):
        if (nValue == True): self.flags &= ~0x00000001
        else: self.flags |= 0x00000001
    IsNormal = IsNormalWeapon = property(get_IsNormalWeapon, set_IsNormalWeapon)
    
class NPC_Record(BaseRecord):
    def CopyAsOverride(self, targetMod):
        FID = CBash.CopyNPC_Record(self._CollectionIndex, self._ModName, self._recordID, targetMod._ModName, c_bool(True))
        if(FID): return NPC_Record(self._CollectionIndex, targetMod._ModName, FID)
        return None
    def CopyAsNew(self, targetMod):
        FID = CBash.CopyNPC_Record(self._CollectionIndex, self._ModName, self._recordID, targetMod._ModName, c_bool(False))
        if(FID): return NPC_Record(self._CollectionIndex, targetMod._ModName, FID)
        return None
    class Faction(object):
        def __init__(self, CollectionIndex, ModName, recordID, subField, listIndex):
            self._CollectionIndex = CollectionIndex
            self._ModName = ModName
            self._recordID = recordID
            self._subField = subField
            self._listIndex = listIndex
        def get_faction(self):
            CBash.ReadFIDListField.restype = POINTER(c_uint)
            retValue = CBash.ReadFIDListField(self._CollectionIndex, self._ModName, self._recordID, self._subField, self._listIndex, 1)
            if(retValue): return retValue.contents.value
            return None
        def set_faction(self, nValue):
            CBash.SetFIDListFieldUI(self._CollectionIndex, self._ModName, self._recordID, self._subField, self._listIndex, 1, nValue)
        faction = property(get_faction, set_faction)
        def get_rank(self):
            CBash.ReadFIDListField.restype = POINTER(c_ubyte)
            retValue = CBash.ReadFIDListField(self._CollectionIndex, self._ModName, self._recordID, self._subField, self._listIndex, 2)
            if(retValue): return retValue.contents.value
            return None
        def set_rank(self, nValue):
            CBash.SetFIDListFieldUC(self._CollectionIndex, self._ModName, self._recordID, self._subField, self._listIndex, 2, c_ubyte(nValue))
        rank = property(get_rank, set_rank)
        def get_unused1(self):
            numRecords = CBash.GetFIDListArraySize(self._CollectionIndex, self._ModName, self._recordID, self._subField, self._listIndex, 3)
            if(numRecords > 0):
                cRecords = POINTER(c_ubyte * numRecords)()
                CBash.GetFIDListArray(self._CollectionIndex, self._ModName, self._recordID, self._subField, self._listIndex, 3, byref(cRecords))
                return [cRecords.contents[x] for x in range(0, numRecords)]
            return []
        def set_unused1(self, nValue):
            CBash.SetFIDListFieldR(self._CollectionIndex, self._ModName, self._recordID, self._subField, self._listIndex, 3, struct.pack('3B', *nValue), 3)
        unused1 = property(get_unused1, set_unused1)
    class Item(object):
        def __init__(self, CollectionIndex, ModName, recordID, subField, listIndex):
            self._CollectionIndex = CollectionIndex
            self._ModName = ModName
            self._recordID = recordID
            self._subField = subField
            self._listIndex = listIndex
        def get_item(self):
            CBash.ReadFIDListField.restype = POINTER(c_uint)
            retValue = CBash.ReadFIDListField(self._CollectionIndex, self._ModName, self._recordID, self._subField, self._listIndex, 1)
            if(retValue): return retValue.contents.value
            return None
        def set_item(self, nValue):
            CBash.SetFIDListFieldUI(self._CollectionIndex, self._ModName, self._recordID, self._subField, self._listIndex, 1, nValue)
        item = property(get_item, set_item)
        def get_count(self):
            CBash.ReadFIDListField.restype = POINTER(c_int)
            retValue = CBash.ReadFIDListField(self._CollectionIndex, self._ModName, self._recordID, self._subField, self._listIndex, 2)
            if(retValue): return retValue.contents.value
            return None
        def set_count(self, nValue):
            CBash.SetFIDListFieldI(self._CollectionIndex, self._ModName, self._recordID, self._subField, self._listIndex, 2, nValue)
        count = property(get_count, set_count)
        
    def newFactionsElement(self):
        listIndex = CBash.CreateFIDListElement(self._CollectionIndex, self._ModName, self._recordID, 17)
        if(listIndex == -1): return None
        return self.Faction(self._CollectionIndex, self._ModName, self._recordID, 17, listIndex)
    def newItemsElement(self):
        listIndex = CBash.CreateFIDListElement(self._CollectionIndex, self._ModName, self._recordID, 22)
        if(listIndex == -1): return None
        return self.Item(self._CollectionIndex, self._ModName, self._recordID, 22, listIndex)
    def get_full(self):
        CBash.ReadFIDField.restype = c_char_p
        return CBash.ReadFIDField(self._CollectionIndex, self._ModName, self._recordID, 6)
    def set_full(self, nValue):
        CBash.SetFIDFieldStr(self._CollectionIndex, self._ModName, self._recordID, 6, nValue)
    full = property(get_full, set_full)
    def get_modPath(self):
        CBash.ReadFIDField.restype = c_char_p
        return CBash.ReadFIDField(self._CollectionIndex, self._ModName, self._recordID, 7)
    def set_modPath(self, nValue):
        CBash.SetFIDFieldStr(self._CollectionIndex, self._ModName, self._recordID, 7, nValue)
    modPath = property(get_modPath, set_modPath)
    def get_modb(self):
        CBash.ReadFIDField.restype = POINTER(c_float)
        retValue = CBash.ReadFIDField(self._CollectionIndex, self._ModName, self._recordID, 8)
        if(retValue): return retValue.contents.value
        return None
    def set_modb(self, nValue):
        CBash.SetFIDFieldF(self._CollectionIndex, self._ModName, self._recordID, 8, c_float(nValue))
    modb = property(get_modb, set_modb)
    def get_modt_p(self):
        numRecords = CBash.GetFIDFieldArraySize(self._CollectionIndex, self._ModName, self._recordID, 9)
        if(numRecords > 0):
            cRecords = POINTER(c_ubyte * numRecords)()
            CBash.GetFIDFieldArray(self._CollectionIndex, self._ModName, self._recordID, 9, byref(cRecords))
            return [cRecords.contents[x] for x in range(0, numRecords)]
        return []
    def set_modt_p(self, nValue):
        length = len(nValue)
        CBash.SetFIDFieldR(self._CollectionIndex, self._ModName, self._recordID, 9, struct.pack('B' * length, *nValue), length)
    modt_p = property(get_modt_p, set_modt_p)
    def get_flags(self):
        CBash.ReadFIDField.restype = POINTER(c_uint)
        retValue = CBash.ReadFIDField(self._CollectionIndex, self._ModName, self._recordID, 10)
        if(retValue): return retValue.contents.value
        return None
    def set_flags(self, nValue):
        CBash.SetFIDFieldUI(self._CollectionIndex, self._ModName, self._recordID, 10, nValue)
    flags = property(get_flags, set_flags)
    def get_baseSpell(self):
        CBash.ReadFIDField.restype = POINTER(c_ushort)
        retValue = CBash.ReadFIDField(self._CollectionIndex, self._ModName, self._recordID, 11)
        if(retValue): return retValue.contents.value
        return None
    def set_baseSpell(self, nValue):
        CBash.SetFIDFieldUS(self._CollectionIndex, self._ModName, self._recordID, 11, c_ushort(nValue))
    baseSpell = property(get_baseSpell, set_baseSpell)
    def get_fatigue(self):
        CBash.ReadFIDField.restype = POINTER(c_ushort)
        retValue = CBash.ReadFIDField(self._CollectionIndex, self._ModName, self._recordID, 12)
        if(retValue): return retValue.contents.value
        return None
    def set_fatigue(self, nValue):
        CBash.SetFIDFieldUS(self._CollectionIndex, self._ModName, self._recordID, 12, c_ushort(nValue))
    fatigue = property(get_fatigue, set_fatigue)
    def get_barterGold(self):
        CBash.ReadFIDField.restype = POINTER(c_ushort)
        retValue = CBash.ReadFIDField(self._CollectionIndex, self._ModName, self._recordID, 13)
        if(retValue): return retValue.contents.value
        return None
    def set_barterGold(self, nValue):
        CBash.SetFIDFieldUS(self._CollectionIndex, self._ModName, self._recordID, 13, c_ushort(nValue))
    barterGold = property(get_barterGold, set_barterGold)
    def get_level(self):
        CBash.ReadFIDField.restype = POINTER(c_short)
        retValue = CBash.ReadFIDField(self._CollectionIndex, self._ModName, self._recordID, 14)
        if(retValue): return retValue.contents.value
        return None
    def set_level(self, nValue):
        CBash.SetFIDFieldS(self._CollectionIndex, self._ModName, self._recordID, 14, c_short(nValue))
    level = property(get_level, set_level)
    def get_calcMin(self):
        CBash.ReadFIDField.restype = POINTER(c_ushort)
        retValue = CBash.ReadFIDField(self._CollectionIndex, self._ModName, self._recordID, 15)
        if(retValue): return retValue.contents.value
        return None
    def set_calcMin(self, nValue):
        CBash.SetFIDFieldUS(self._CollectionIndex, self._ModName, self._recordID, 15, c_ushort(nValue))
    calcMin = property(get_calcMin, set_calcMin)
    def get_calcMax(self):
        CBash.ReadFIDField.restype = POINTER(c_ushort)
        retValue = CBash.ReadFIDField(self._CollectionIndex, self._ModName, self._recordID, 16)
        if(retValue): return retValue.contents.value
        return None
    def set_calcMax(self, nValue):
        CBash.SetFIDFieldUS(self._CollectionIndex, self._ModName, self._recordID, 16, c_ushort(nValue))
    calcMax = property(get_calcMax, set_calcMax)
    def get_factions(self):
        numRecords = CBash.GetFIDListSize(self._CollectionIndex, self._ModName, self._recordID, 17)
        if(numRecords > 0): return [self.Faction(self._CollectionIndex, self._ModName, self._recordID, 17, x) for x in range(0, numRecords)]
        return []
    def set_factions(self, nFactions):
        diffLength = len(nFactions) - CBash.GetFIDListSize(self._CollectionIndex, self._ModName, self._recordID, 17)
        nValues = [(faction.faction,faction.rank,faction.unused1) for faction in nFactions]
        while(diffLength < 0):
            CBash.DeleteFIDListElement(self._CollectionIndex, self._ModName, self._recordID, 17)
            diffLength += 1
        while(diffLength > 0):
            CBash.CreateFIDListElement(self._CollectionIndex, self._ModName, self._recordID, 17)
            diffLength -= 1
        for oFaction, nValue in zip(self.factions, nValues):
            oFaction.faction, oFaction.rank, oFaction.unused1 = nValue
    factions = property(get_factions, set_factions)
    def get_deathItem(self):
        CBash.ReadFIDField.restype = POINTER(c_uint)
        retValue = CBash.ReadFIDField(self._CollectionIndex, self._ModName, self._recordID, 18)
        if(retValue): return retValue.contents.value
        return None
    def set_deathItem(self, nValue):
        CBash.SetFIDFieldUI(self._CollectionIndex, self._ModName, self._recordID, 18, nValue)
    deathItem = property(get_deathItem, set_deathItem)
    def get_race(self):
        CBash.ReadFIDField.restype = POINTER(c_uint)
        retValue = CBash.ReadFIDField(self._CollectionIndex, self._ModName, self._recordID, 19)
        if(retValue): return retValue.contents.value
        return None
    def set_race(self, nValue):
        CBash.SetFIDFieldUI(self._CollectionIndex, self._ModName, self._recordID, 19, nValue)
    race = property(get_race, set_race)
    def get_spells(self):
        numRecords = CBash.GetFIDFieldArraySize(self._CollectionIndex, self._ModName, self._recordID, 20)
        if(numRecords > 0):
            cRecords = POINTER(c_uint * numRecords)()
            CBash.GetFIDFieldArray(self._CollectionIndex, self._ModName, self._recordID, 20, byref(cRecords))
            return [cRecords.contents[x] for x in range(0, numRecords)]
        return []
    def set_spells(self, nValue):
        CBash.SetFIDFieldUIA(self._CollectionIndex, self._ModName, self._recordID, 20, struct.pack('I' * len(nValue), *nValue), len(nValue))
    spells = property(get_spells, set_spells)
    def get_script(self):
        CBash.ReadFIDField.restype = POINTER(c_uint)
        retValue = CBash.ReadFIDField(self._CollectionIndex, self._ModName, self._recordID, 21)
        if(retValue): return retValue.contents.value
        return None
    def set_script(self, nValue):
        CBash.SetFIDFieldUI(self._CollectionIndex, self._ModName, self._recordID, 21, nValue)
    script = property(get_script, set_script)
    def get_items(self):
        numRecords = CBash.GetFIDListSize(self._CollectionIndex, self._ModName, self._recordID, 22)
        if(numRecords > 0): return [self.Item(self._CollectionIndex, self._ModName, self._recordID, 22, x) for x in range(0, numRecords)]
        return []
    def set_items(self, nItems):
        diffLength = len(nItems) - CBash.GetFIDListSize(self._CollectionIndex, self._ModName, self._recordID, 22)
        nValues = [(item.item, item.count) for item in nItems]
        while(diffLength < 0):
            CBash.DeleteFIDListElement(self._CollectionIndex, self._ModName, self._recordID, 22)
            diffLength += 1
        while(diffLength > 0):
            CBash.CreateFIDListElement(self._CollectionIndex, self._ModName, self._recordID, 22)
            diffLength -= 1
        for oItem, nValue in zip(self.items, nValues):
            oItem.item, oItem.count = nValue
    items = property(get_items, set_items)
    def get_aggression(self):
        CBash.ReadFIDField.restype = POINTER(c_ubyte)
        retValue = CBash.ReadFIDField(self._CollectionIndex, self._ModName, self._recordID, 23)
        if(retValue): return retValue.contents.value
        return None
    def set_aggression(self, nValue):
        CBash.SetFIDFieldUC(self._CollectionIndex, self._ModName, self._recordID, 23, c_ubyte(nValue))
    aggression = property(get_aggression, set_aggression)
    def get_confidence(self):
        CBash.ReadFIDField.restype = POINTER(c_ubyte)
        retValue = CBash.ReadFIDField(self._CollectionIndex, self._ModName, self._recordID, 24)
        if(retValue): return retValue.contents.value
        return None
    def set_confidence(self, nValue):
        CBash.SetFIDFieldUC(self._CollectionIndex, self._ModName, self._recordID, 24, c_ubyte(nValue))
    confidence = property(get_confidence, set_confidence)
    def get_energyLevel(self):
        CBash.ReadFIDField.restype = POINTER(c_ubyte)
        retValue = CBash.ReadFIDField(self._CollectionIndex, self._ModName, self._recordID, 25)
        if(retValue): return retValue.contents.value
        return None
    def set_energyLevel(self, nValue):
        CBash.SetFIDFieldUC(self._CollectionIndex, self._ModName, self._recordID, 25, c_ubyte(nValue))
    energyLevel = property(get_energyLevel, set_energyLevel)
    def get_responsibility(self):
        CBash.ReadFIDField.restype = POINTER(c_ubyte)
        retValue = CBash.ReadFIDField(self._CollectionIndex, self._ModName, self._recordID, 26)
        if(retValue): return retValue.contents.value
        return None
    def set_responsibility(self, nValue):
        CBash.SetFIDFieldUC(self._CollectionIndex, self._ModName, self._recordID, 26, c_ubyte(nValue))
    responsibility = property(get_responsibility, set_responsibility)
    def get_services(self):
        CBash.ReadFIDField.restype = POINTER(c_uint)
        retValue = CBash.ReadFIDField(self._CollectionIndex, self._ModName, self._recordID, 27)
        if(retValue): return retValue.contents.value
        return None
    def set_services(self, nValue):
        CBash.SetFIDFieldUI(self._CollectionIndex, self._ModName, self._recordID, 27, nValue)
    services = property(get_services, set_services)
    def get_trainSkill(self):
        CBash.ReadFIDField.restype = POINTER(c_byte)
        retValue = CBash.ReadFIDField(self._CollectionIndex, self._ModName, self._recordID, 28)
        if(retValue): return retValue.contents.value
        return None
    def set_trainSkill(self, nValue):
        CBash.SetFIDFieldC(self._CollectionIndex, self._ModName, self._recordID, 28, c_byte(nValue))
    trainSkill = property(get_trainSkill, set_trainSkill)
    def get_trainLevel(self):
        CBash.ReadFIDField.restype = POINTER(c_ubyte)
        retValue = CBash.ReadFIDField(self._CollectionIndex, self._ModName, self._recordID, 29)
        if(retValue): return retValue.contents.value
        return None
    def set_trainLevel(self, nValue):
        CBash.SetFIDFieldUC(self._CollectionIndex, self._ModName, self._recordID, 29, c_ubyte(nValue))
    trainLevel = property(get_trainLevel, set_trainLevel)
    def get_unused1(self):
        numRecords = CBash.GetFIDFieldArraySize(self._CollectionIndex, self._ModName, self._recordID, 30)
        if(numRecords > 0):
            cRecords = POINTER(c_ubyte * numRecords)()
            CBash.GetFIDFieldArray(self._CollectionIndex, self._ModName, self._recordID, 30, byref(cRecords))
            return [cRecords.contents[x] for x in range(0, numRecords)]
        return []
    def set_unused1(self, nValue):
        CBash.SetFIDFieldR(self._CollectionIndex, self._ModName, self._recordID, 30, struct.pack('2B', *nValue), 2)
    unused1 = property(get_unused1, set_unused1)
    def get_aiPackages(self):
        numRecords = CBash.GetFIDFieldArraySize(self._CollectionIndex, self._ModName, self._recordID, 31)
        if(numRecords > 0):
            cRecords = POINTER(c_uint * numRecords)()
            CBash.GetFIDFieldArray(self._CollectionIndex, self._ModName, self._recordID, 31, byref(cRecords))
            return [cRecords.contents[x] for x in range(0, numRecords)]
        return []
    def set_aiPackages(self, nValue):
        CBash.SetFIDFieldUIA(self._CollectionIndex, self._ModName, self._recordID, 31, struct.pack('I' * len(nValue), *nValue), len(nValue))
    aiPackages = property(get_aiPackages, set_aiPackages)
    def get_animations(self):
        numRecords = CBash.GetFIDFieldArraySize(self._CollectionIndex, self._ModName, self._recordID, 32)
        if(numRecords > 0):
            cRecords = (POINTER(c_char_p) * numRecords)()
            CBash.GetFIDFieldArray(self._CollectionIndex, self._ModName, self._recordID, 32, byref(cRecords))
            return [string_at(cRecords[x]) for x in range(0, numRecords)]
        return []
    def set_animations(self, nValue):
        length = len(nValue)
        cRecords = (c_char_p * length)(*nValue)
        CBash.SetFIDFieldStrA(self._CollectionIndex, self._ModName, self._recordID, 32, byref(cRecords), length)
    animations = property(get_animations, set_animations)
    def get_iclass(self):
        CBash.ReadFIDField.restype = POINTER(c_uint)
        retValue = CBash.ReadFIDField(self._CollectionIndex, self._ModName, self._recordID, 33)
        if(retValue): return retValue.contents.value
        return None
    def set_iclass(self, nValue):
        CBash.SetFIDFieldUI(self._CollectionIndex, self._ModName, self._recordID, 33, nValue)
    iclass = property(get_iclass, set_iclass)
    def get_armorer(self):
        CBash.ReadFIDField.restype = POINTER(c_ubyte)
        retValue = CBash.ReadFIDField(self._CollectionIndex, self._ModName, self._recordID, 34)
        if(retValue): return retValue.contents.value
        return None
    def set_armorer(self, nValue):
        CBash.SetFIDFieldUC(self._CollectionIndex, self._ModName, self._recordID, 34, c_ubyte(nValue))
    armorer = property(get_armorer, set_armorer)
    def get_athletics(self):
        CBash.ReadFIDField.restype = POINTER(c_ubyte)
        retValue = CBash.ReadFIDField(self._CollectionIndex, self._ModName, self._recordID, 35)
        if(retValue): return retValue.contents.value
        return None
    def set_athletics(self, nValue):
        CBash.SetFIDFieldUC(self._CollectionIndex, self._ModName, self._recordID, 35, c_ubyte(nValue))
    athletics = property(get_athletics, set_athletics)
    def get_blade(self):
        CBash.ReadFIDField.restype = POINTER(c_ubyte)
        retValue = CBash.ReadFIDField(self._CollectionIndex, self._ModName, self._recordID, 36)
        if(retValue): return retValue.contents.value
        return None
    def set_blade(self, nValue):
        CBash.SetFIDFieldUC(self._CollectionIndex, self._ModName, self._recordID, 36, c_ubyte(nValue))
    blade = property(get_blade, set_blade)
    def get_block(self):
        CBash.ReadFIDField.restype = POINTER(c_ubyte)
        retValue = CBash.ReadFIDField(self._CollectionIndex, self._ModName, self._recordID, 37)
        if(retValue): return retValue.contents.value
        return None
    def set_block(self, nValue):
        CBash.SetFIDFieldUC(self._CollectionIndex, self._ModName, self._recordID, 37, c_ubyte(nValue))
    block = property(get_block, set_block)
    def get_blunt(self):
        CBash.ReadFIDField.restype = POINTER(c_ubyte)
        retValue = CBash.ReadFIDField(self._CollectionIndex, self._ModName, self._recordID, 38)
        if(retValue): return retValue.contents.value
        return None
    def set_blunt(self, nValue):
        CBash.SetFIDFieldUC(self._CollectionIndex, self._ModName, self._recordID, 38, c_ubyte(nValue))
    blunt = property(get_blunt, set_blunt)
    def get_h2h(self):
        CBash.ReadFIDField.restype = POINTER(c_ubyte)
        retValue = CBash.ReadFIDField(self._CollectionIndex, self._ModName, self._recordID, 39)
        if(retValue): return retValue.contents.value
        return None
    def set_h2h(self, nValue):
        CBash.SetFIDFieldUC(self._CollectionIndex, self._ModName, self._recordID, 39, c_ubyte(nValue))
    h2h = property(get_h2h, set_h2h)
    def get_heavyArmor(self):
        CBash.ReadFIDField.restype = POINTER(c_ubyte)
        retValue = CBash.ReadFIDField(self._CollectionIndex, self._ModName, self._recordID, 40)
        if(retValue): return retValue.contents.value
        return None
    def set_heavyArmor(self, nValue):
        CBash.SetFIDFieldUC(self._CollectionIndex, self._ModName, self._recordID, 40, c_ubyte(nValue))
    heavyArmor = property(get_heavyArmor, set_heavyArmor)
    def get_alchemy(self):
        CBash.ReadFIDField.restype = POINTER(c_ubyte)
        retValue = CBash.ReadFIDField(self._CollectionIndex, self._ModName, self._recordID, 41)
        if(retValue): return retValue.contents.value
        return None
    def set_alchemy(self, nValue):
        CBash.SetFIDFieldUC(self._CollectionIndex, self._ModName, self._recordID, 41, c_ubyte(nValue))
    alchemy = property(get_alchemy, set_alchemy)
    def get_alteration(self):
        CBash.ReadFIDField.restype = POINTER(c_ubyte)
        retValue = CBash.ReadFIDField(self._CollectionIndex, self._ModName, self._recordID, 42)
        if(retValue): return retValue.contents.value
        return None
    def set_alteration(self, nValue):
        CBash.SetFIDFieldUC(self._CollectionIndex, self._ModName, self._recordID, 42, c_ubyte(nValue))
    alteration = property(get_alteration, set_alteration)
    def get_conjuration(self):
        CBash.ReadFIDField.restype = POINTER(c_ubyte)
        retValue = CBash.ReadFIDField(self._CollectionIndex, self._ModName, self._recordID, 43)
        if(retValue): return retValue.contents.value
        return None
    def set_conjuration(self, nValue):
        CBash.SetFIDFieldUC(self._CollectionIndex, self._ModName, self._recordID, 43, c_ubyte(nValue))
    conjuration = property(get_conjuration, set_conjuration)
    def get_destruction(self):
        CBash.ReadFIDField.restype = POINTER(c_ubyte)
        retValue = CBash.ReadFIDField(self._CollectionIndex, self._ModName, self._recordID, 44)
        if(retValue): return retValue.contents.value
        return None
    def set_destruction(self, nValue):
        CBash.SetFIDFieldUC(self._CollectionIndex, self._ModName, self._recordID, 44, c_ubyte(nValue))
    destruction = property(get_destruction, set_destruction)
    def get_illusion(self):
        CBash.ReadFIDField.restype = POINTER(c_ubyte)
        retValue = CBash.ReadFIDField(self._CollectionIndex, self._ModName, self._recordID, 45)
        if(retValue): return retValue.contents.value
        return None
    def set_illusion(self, nValue):
        CBash.SetFIDFieldUC(self._CollectionIndex, self._ModName, self._recordID, 45, c_ubyte(nValue))
    illusion = property(get_illusion, set_illusion)
    def get_mysticism(self):
        CBash.ReadFIDField.restype = POINTER(c_ubyte)
        retValue = CBash.ReadFIDField(self._CollectionIndex, self._ModName, self._recordID, 46)
        if(retValue): return retValue.contents.value
        return None
    def set_mysticism(self, nValue):
        CBash.SetFIDFieldUC(self._CollectionIndex, self._ModName, self._recordID, 46, c_ubyte(nValue))
    mysticism = property(get_mysticism, set_mysticism)
    def get_restoration(self):
        CBash.ReadFIDField.restype = POINTER(c_ubyte)
        retValue = CBash.ReadFIDField(self._CollectionIndex, self._ModName, self._recordID, 47)
        if(retValue): return retValue.contents.value
        return None
    def set_restoration(self, nValue):
        CBash.SetFIDFieldUC(self._CollectionIndex, self._ModName, self._recordID, 47, c_ubyte(nValue))
    restoration = property(get_restoration, set_restoration)
    def get_acrobatics(self):
        CBash.ReadFIDField.restype = POINTER(c_ubyte)
        retValue = CBash.ReadFIDField(self._CollectionIndex, self._ModName, self._recordID, 48)
        if(retValue): return retValue.contents.value
        return None
    def set_acrobatics(self, nValue):
        CBash.SetFIDFieldUC(self._CollectionIndex, self._ModName, self._recordID, 48, c_ubyte(nValue))
    acrobatics = property(get_acrobatics, set_acrobatics)
    def get_lightArmor(self):
        CBash.ReadFIDField.restype = POINTER(c_ubyte)
        retValue = CBash.ReadFIDField(self._CollectionIndex, self._ModName, self._recordID, 49)
        if(retValue): return retValue.contents.value
        return None
    def set_lightArmor(self, nValue):
        CBash.SetFIDFieldUC(self._CollectionIndex, self._ModName, self._recordID, 49, c_ubyte(nValue))
    lightArmor = property(get_lightArmor, set_lightArmor)
    def get_marksman(self):
        CBash.ReadFIDField.restype = POINTER(c_ubyte)
        retValue = CBash.ReadFIDField(self._CollectionIndex, self._ModName, self._recordID, 50)
        if(retValue): return retValue.contents.value
        return None
    def set_marksman(self, nValue):
        CBash.SetFIDFieldUC(self._CollectionIndex, self._ModName, self._recordID, 50, c_ubyte(nValue))
    marksman = property(get_marksman, set_marksman)
    def get_mercantile(self):
        CBash.ReadFIDField.restype = POINTER(c_ubyte)
        retValue = CBash.ReadFIDField(self._CollectionIndex, self._ModName, self._recordID, 51)
        if(retValue): return retValue.contents.value
        return None
    def set_mercantile(self, nValue):
        CBash.SetFIDFieldUC(self._CollectionIndex, self._ModName, self._recordID, 51, c_ubyte(nValue))
    mercantile = property(get_mercantile, set_mercantile)
    def get_security(self):
        CBash.ReadFIDField.restype = POINTER(c_ubyte)
        retValue = CBash.ReadFIDField(self._CollectionIndex, self._ModName, self._recordID, 52)
        if(retValue): return retValue.contents.value
        return None
    def set_security(self, nValue):
        CBash.SetFIDFieldUC(self._CollectionIndex, self._ModName, self._recordID, 52, c_ubyte(nValue))
    security = property(get_security, set_security)
    def get_sneak(self):
        CBash.ReadFIDField.restype = POINTER(c_ubyte)
        retValue = CBash.ReadFIDField(self._CollectionIndex, self._ModName, self._recordID, 53)
        if(retValue): return retValue.contents.value
        return None
    def set_sneak(self, nValue):
        CBash.SetFIDFieldUC(self._CollectionIndex, self._ModName, self._recordID, 53, c_ubyte(nValue))
    sneak = property(get_sneak, set_sneak)
    def get_speechcraft(self):
        CBash.ReadFIDField.restype = POINTER(c_ubyte)
        retValue = CBash.ReadFIDField(self._CollectionIndex, self._ModName, self._recordID, 54)
        if(retValue): return retValue.contents.value
        return None
    def set_speechcraft(self, nValue):
        CBash.SetFIDFieldUC(self._CollectionIndex, self._ModName, self._recordID, 54, c_ubyte(nValue))
    speechcraft = property(get_speechcraft, set_speechcraft)
    def get_health(self):
        CBash.ReadFIDField.restype = POINTER(c_ushort)
        retValue = CBash.ReadFIDField(self._CollectionIndex, self._ModName, self._recordID, 55)
        if(retValue): return retValue.contents.value
        return None
    def set_health(self, nValue):
        CBash.SetFIDFieldUS(self._CollectionIndex, self._ModName, self._recordID, 55, c_ushort(nValue))
    health = property(get_health, set_health)
    def get_unused2(self):
        numRecords = CBash.GetFIDFieldArraySize(self._CollectionIndex, self._ModName, self._recordID, 56)
        if(numRecords > 0):
            cRecords = POINTER(c_ubyte * numRecords)()
            CBash.GetFIDFieldArray(self._CollectionIndex, self._ModName, self._recordID, 56, byref(cRecords))
            return [cRecords.contents[x] for x in range(0, numRecords)]
        return []
    def set_unused2(self, nValue):
        CBash.SetFIDFieldR(self._CollectionIndex, self._ModName, self._recordID, 56, struct.pack('2B', *nValue), 2)
    unused2 = property(get_unused2, set_unused2)
    def get_strength(self):
        CBash.ReadFIDField.restype = POINTER(c_ubyte)
        retValue = CBash.ReadFIDField(self._CollectionIndex, self._ModName, self._recordID, 57)
        if(retValue): return retValue.contents.value
        return None
    def set_strength(self, nValue):
        CBash.SetFIDFieldUC(self._CollectionIndex, self._ModName, self._recordID, 57, c_ubyte(nValue))
    strength = property(get_strength, set_strength)
    def get_intelligence(self):
        CBash.ReadFIDField.restype = POINTER(c_ubyte)
        retValue = CBash.ReadFIDField(self._CollectionIndex, self._ModName, self._recordID, 58)
        if(retValue): return retValue.contents.value
        return None
    def set_intelligence(self, nValue):
        CBash.SetFIDFieldUC(self._CollectionIndex, self._ModName, self._recordID, 58, c_ubyte(nValue))
    intelligence = property(get_intelligence, set_intelligence)
    def get_willpower(self):
        CBash.ReadFIDField.restype = POINTER(c_ubyte)
        retValue = CBash.ReadFIDField(self._CollectionIndex, self._ModName, self._recordID, 59)
        if(retValue): return retValue.contents.value
        return None
    def set_willpower(self, nValue):
        CBash.SetFIDFieldUC(self._CollectionIndex, self._ModName, self._recordID, 59, c_ubyte(nValue))
    willpower = property(get_willpower, set_willpower)
    def get_agility(self):
        CBash.ReadFIDField.restype = POINTER(c_ubyte)
        retValue = CBash.ReadFIDField(self._CollectionIndex, self._ModName, self._recordID, 60)
        if(retValue): return retValue.contents.value
        return None
    def set_agility(self, nValue):
        CBash.SetFIDFieldUC(self._CollectionIndex, self._ModName, self._recordID, 60, c_ubyte(nValue))
    agility = property(get_agility, set_agility)
    def get_speed(self):
        CBash.ReadFIDField.restype = POINTER(c_ubyte)
        retValue = CBash.ReadFIDField(self._CollectionIndex, self._ModName, self._recordID, 61)
        if(retValue): return retValue.contents.value
        return None
    def set_speed(self, nValue):
        CBash.SetFIDFieldUC(self._CollectionIndex, self._ModName, self._recordID, 61, c_ubyte(nValue))
    speed = property(get_speed, set_speed)
    def get_endurance(self):
        CBash.ReadFIDField.restype = POINTER(c_ubyte)
        retValue = CBash.ReadFIDField(self._CollectionIndex, self._ModName, self._recordID, 62)
        if(retValue): return retValue.contents.value
        return None
    def set_endurance(self, nValue):
        CBash.SetFIDFieldUC(self._CollectionIndex, self._ModName, self._recordID, 62, c_ubyte(nValue))
    endurance = property(get_endurance, set_endurance)
    def get_personality(self):
        CBash.ReadFIDField.restype = POINTER(c_ubyte)
        retValue = CBash.ReadFIDField(self._CollectionIndex, self._ModName, self._recordID, 63)
        if(retValue): return retValue.contents.value
        return None
    def set_personality(self, nValue):
        CBash.SetFIDFieldUC(self._CollectionIndex, self._ModName, self._recordID, 63, c_ubyte(nValue))
    personality = property(get_personality, set_personality)
    def get_luck(self):
        CBash.ReadFIDField.restype = POINTER(c_ubyte)
        retValue = CBash.ReadFIDField(self._CollectionIndex, self._ModName, self._recordID, 64)
        if(retValue): return retValue.contents.value
        return None
    def set_luck(self, nValue):
        CBash.SetFIDFieldUC(self._CollectionIndex, self._ModName, self._recordID, 64, c_ubyte(nValue))
    luck = property(get_luck, set_luck)
    def get_hair(self):
        CBash.ReadFIDField.restype = POINTER(c_uint)
        retValue = CBash.ReadFIDField(self._CollectionIndex, self._ModName, self._recordID, 65)
        if(retValue): return retValue.contents.value
        return None
    def set_hair(self, nValue):
        CBash.SetFIDFieldUI(self._CollectionIndex, self._ModName, self._recordID, 65, nValue)
    hair = property(get_hair, set_hair)
    def get_hairLength(self):
        CBash.ReadFIDField.restype = POINTER(c_float)
        retValue = CBash.ReadFIDField(self._CollectionIndex, self._ModName, self._recordID, 66)
        if(retValue): return retValue.contents.value
        return None
    def set_hairLength(self, nValue):
        CBash.SetFIDFieldF(self._CollectionIndex, self._ModName, self._recordID, 66, c_float(nValue))
    hairLength = property(get_hairLength, set_hairLength)
    def get_eye(self):
        CBash.ReadFIDField.restype = POINTER(c_uint)
        retValue = CBash.ReadFIDField(self._CollectionIndex, self._ModName, self._recordID, 67)
        if(retValue): return retValue.contents.value
        return None
    def set_eye(self, nValue):
        CBash.SetFIDFieldUI(self._CollectionIndex, self._ModName, self._recordID, 67, nValue)
    eye = property(get_eye, set_eye)
    def get_hairRed(self):
        CBash.ReadFIDField.restype = POINTER(c_ubyte)
        retValue = CBash.ReadFIDField(self._CollectionIndex, self._ModName, self._recordID, 68)
        if(retValue): return retValue.contents.value
        return None
    def set_hairRed(self, nValue):
        CBash.SetFIDFieldUC(self._CollectionIndex, self._ModName, self._recordID, 68, c_ubyte(nValue))
    hairRed = property(get_hairRed, set_hairRed)
    def get_hairGreen(self):
        CBash.ReadFIDField.restype = POINTER(c_ubyte)
        retValue = CBash.ReadFIDField(self._CollectionIndex, self._ModName, self._recordID, 69)
        if(retValue): return retValue.contents.value
        return None
    def set_hairGreen(self, nValue):
        CBash.SetFIDFieldUC(self._CollectionIndex, self._ModName, self._recordID, 69, c_ubyte(nValue))
    hairGreen = property(get_hairGreen, set_hairGreen)
    def get_hairBlue(self):
        CBash.ReadFIDField.restype = POINTER(c_ubyte)
        retValue = CBash.ReadFIDField(self._CollectionIndex, self._ModName, self._recordID, 70)
        if(retValue): return retValue.contents.value
        return None
    def set_hairBlue(self, nValue):
        CBash.SetFIDFieldUC(self._CollectionIndex, self._ModName, self._recordID, 70, c_ubyte(nValue))
    hairBlue = property(get_hairBlue, set_hairBlue)
    def get_unused3(self):
        numRecords = CBash.GetFIDFieldArraySize(self._CollectionIndex, self._ModName, self._recordID, 71)
        if(numRecords > 0):
            cRecords = POINTER(c_ubyte * numRecords)()
            CBash.GetFIDFieldArray(self._CollectionIndex, self._ModName, self._recordID, 71, byref(cRecords))
            return [cRecords.contents[x] for x in range(0, numRecords)]
        return []
    def set_unused3(self, nValue):
        CBash.SetFIDFieldR(self._CollectionIndex, self._ModName, self._recordID, 71, struct.pack('B', *nValue), 1)
    unused3 = property(get_unused3, set_unused3)
    def get_combatStyle(self):
        CBash.ReadFIDField.restype = POINTER(c_uint)
        retValue = CBash.ReadFIDField(self._CollectionIndex, self._ModName, self._recordID, 72)
        if(retValue): return retValue.contents.value
        return None
    def set_combatStyle(self, nValue):
        CBash.SetFIDFieldUI(self._CollectionIndex, self._ModName, self._recordID, 72, nValue)
    combatStyle = property(get_combatStyle, set_combatStyle)
    def get_fggs_p(self):
        numRecords = CBash.GetFIDFieldArraySize(self._CollectionIndex, self._ModName, self._recordID, 73)
        if(numRecords > 0):
            cRecords = POINTER(c_ubyte * numRecords)()
            CBash.GetFIDFieldArray(self._CollectionIndex, self._ModName, self._recordID, 73, byref(cRecords))
            return [cRecords.contents[x] for x in range(0, numRecords)]
        return []
    def set_fggs_p(self, nValue):
        CBash.SetFIDFieldR(self._CollectionIndex, self._ModName, self._recordID, 73, struct.pack('200B', *nValue), 200)
    fggs_p = property(get_fggs_p, set_fggs_p)
    def get_fgga_p(self):
        numRecords = CBash.GetFIDFieldArraySize(self._CollectionIndex, self._ModName, self._recordID, 74)
        if(numRecords > 0):
            cRecords = POINTER(c_ubyte * numRecords)()
            CBash.GetFIDFieldArray(self._CollectionIndex, self._ModName, self._recordID, 74, byref(cRecords))
            return [cRecords.contents[x] for x in range(0, numRecords)]
        return []
    def set_fgga_p(self, nValue):
        CBash.SetFIDFieldR(self._CollectionIndex, self._ModName, self._recordID, 74, struct.pack('120B', *nValue), 120)
    fgga_p = property(get_fgga_p, set_fgga_p)
    def get_fgts_p(self):
        numRecords = CBash.GetFIDFieldArraySize(self._CollectionIndex, self._ModName, self._recordID, 75)
        if(numRecords > 0):
            cRecords = POINTER(c_ubyte * numRecords)()
            CBash.GetFIDFieldArray(self._CollectionIndex, self._ModName, self._recordID, 75, byref(cRecords))
            return [cRecords.contents[x] for x in range(0, numRecords)]
        return []
    def set_fgts_p(self, nValue):
        CBash.SetFIDFieldR(self._CollectionIndex, self._ModName, self._recordID, 75, struct.pack('200B', *nValue), 200)
    fgts_p = property(get_fgts_p, set_fgts_p)
    def get_fnam(self):
        CBash.ReadFIDField.restype = POINTER(c_ushort)
        retValue = CBash.ReadFIDField(self._CollectionIndex, self._ModName, self._recordID, 76)
        if(retValue): return retValue.contents.value
        return None
    def set_fnam(self, nValue):
        CBash.SetFIDFieldUS(self._CollectionIndex, self._ModName, self._recordID, 76, c_ushort(nValue))
    fnam = property(get_fnam, set_fnam)
    def get_IsFemale(self):
        return (self.flags & 0x00000001) != 0
    def set_IsFemale(self, nValue):
        if (nValue == True): self.flags |= 0x00000001
        else: self.flags &= ~0x00000001
    IsFemale = property(get_IsFemale, set_IsFemale)
    def get_IsMale(self):
        return not self.get_IsFemale()
    def set_IsMale(self, nValue):
        if (nValue == True): self.flags &= ~0x00000001
        else: self.flags |= 0x00000001
    IsMale = property(get_IsMale, set_IsMale)
    def get_IsEssential(self):
        return (self.flags & 0x00000002) != 0
    def set_IsEssential(self, nValue):
        if (nValue == True): self.flags |= 0x00000002
        else: self.flags &= ~0x00000002
    IsEssential = property(get_IsEssential, set_IsEssential)
    def get_IsRespawn(self):
        return (self.flags & 0x00000008) != 0
    def set_IsRespawn(self, nValue):
        if (nValue == True): self.flags |= 0x00000008
        else: self.flags &= ~0x00000008
    IsRespawn = property(get_IsRespawn, set_IsRespawn)
    def get_IsAutoCalc(self):
        return (self.flags & 0x00000010) != 0
    def set_IsAutoCalc(self, nValue):
        if (nValue == True): self.flags |= 0x00000010
        else: self.flags &= ~0x00000010
    IsAutoCalc = property(get_IsAutoCalc, set_IsAutoCalc)
    def get_IsPCLevelOffset(self):
        return (self.flags & 0x00000080) != 0
    def set_IsPCLevelOffset(self, nValue):
        if (nValue == True): self.flags |= 0x00000080
        else: self.flags &= ~0x00000080
    IsPCLevelOffset = property(get_IsPCLevelOffset, set_IsPCLevelOffset)
    def get_IsNoLowLevel(self):
        return (self.flags & 0x00000200) != 0
    def set_IsNoLowLevel(self, nValue):
        if (nValue == True): self.flags |= 0x00000200
        else: self.flags &= ~0x00000200
    IsNoLowLevel = property(get_IsNoLowLevel, set_IsNoLowLevel)
    def get_IsLowLevel(self):
        return not self.get_IsNoLowLevel()
    def set_IsLowLevel(self, nValue):
        if (nValue == True): self.flags &= ~0x00000200
        else: self.flags |= 0x00000200
    IsLowLevel = property(get_IsLowLevel, set_IsLowLevel)
    def get_IsNoRumors(self):
        return (self.flags & 0x00002000) != 0
    def set_IsNoRumors(self, nValue):
        if (nValue == True): self.flags |= 0x00002000
        else: self.flags &= ~0x00002000
    IsNoRumors = property(get_IsNoRumors, set_IsNoRumors)
    def get_IsRumors(self):
        return not self.get_IsNoRumors()
    def set_IsRumors(self, nValue):
        if (nValue == True): self.flags &= ~0x00002000
        else: self.flags |= 0x00002000
    IsRumors = property(get_IsRumors, set_IsRumors)
    def get_IsSummonable(self):
        return (self.flags & 0x00004000) != 0
    def set_IsSummonable(self, nValue):
        if (nValue == True): self.flags |= 0x00004000
        else: self.flags &= ~0x00004000
    IsSummonable = property(get_IsSummonable, set_IsSummonable)
    def get_IsNoPersuasion(self):
        return (self.flags & 0x00008000) != 0
    def set_IsNoPersuasion(self, nValue):
        if (nValue == True): self.flags |= 0x00008000
        else: self.flags &= ~0x00008000
    IsNoPersuasion = property(get_IsNoPersuasion, set_IsNoPersuasion)
    def get_IsPersuasion(self):
        return not self.get_IsNoPersuasion()
    def set_IsPersuasion(self, nValue):
        if (nValue == True): self.flags &= ~0x00008000
        else: self.flags |= 0x00008000
    IsPersuasion = property(get_IsPersuasion, set_IsPersuasion)
    def get_IsCanCorpseCheck(self):
        return (self.flags & 0x00100000) != 0
    def set_IsCanCorpseCheck(self, nValue):
        if (nValue == True): self.flags |= 0x00100000
        else: self.flags &= ~0x00100000
    IsCanCorpseCheck = property(get_IsCanCorpseCheck, set_IsCanCorpseCheck)
    def get_IsServicesWeapons(self):
        return (self.services & 0x00000001) != 0
    def set_IsServicesWeapons(self, nValue):
        if (nValue == True): self.services |= 0x00000001
        else: self.services &= ~0x00000001
    IsServicesWeapons = property(get_IsServicesWeapons, set_IsServicesWeapons)
    def get_IsServicesArmor(self):
        return (self.services & 0x00000002) != 0
    def set_IsServicesArmor(self, nValue):
        if (nValue == True): self.services |= 0x00000002
        else: self.services &= ~0x00000002
    IsServicesArmor = property(get_IsServicesArmor, set_IsServicesArmor)
    def get_IsServicesClothing(self):
        return (self.services & 0x00000004) != 0
    def set_IsServicesClothing(self, nValue):
        if (nValue == True): self.services |= 0x00000004
        else: self.services &= ~0x00000004
    IsServicesClothing = property(get_IsServicesClothing, set_IsServicesClothing)
    def get_IsServicesBooks(self):
        return (self.services & 0x00000008) != 0
    def set_IsServicesBooks(self, nValue):
        if (nValue == True): self.services |= 0x00000008
        else: self.services &= ~0x00000008
    IsServicesBooks = property(get_IsServicesBooks, set_IsServicesBooks)
    def get_IsServicesIngredients(self):
        return (self.services & 0x00000010) != 0
    def set_IsServicesIngredients(self, nValue):
        if (nValue == True): self.services |= 0x00000010
        else: self.services &= ~0x00000010
    IsServicesIngredients = property(get_IsServicesIngredients, set_IsServicesIngredients)
    def get_IsServicesLights(self):
        return (self.services & 0x00000080) != 0
    def set_IsServicesLights(self, nValue):
        if (nValue == True): self.services |= 0x00000080
        else: self.services &= ~0x00000080
    IsServicesLights = property(get_IsServicesLights, set_IsServicesLights)
    def get_IsServicesApparatus(self):
        return (self.services & 0x00000100) != 0
    def set_IsServicesApparatus(self, nValue):
        if (nValue == True): self.services |= 0x00000100
        else: self.services &= ~0x00000100
    IsServicesApparatus = property(get_IsServicesApparatus, set_IsServicesApparatus)
    def get_IsServicesMiscItems(self):
        return (self.services & 0x00000400) != 0
    def set_IsServicesMiscItems(self, nValue):
        if (nValue == True): self.services |= 0x00000400
        else: self.services &= ~0x00000400
    IsServicesMiscItems = property(get_IsServicesMiscItems, set_IsServicesMiscItems)
    def get_IsServicesSpells(self):
        return (self.services & 0x00000800) != 0
    def set_IsServicesSpells(self, nValue):
        if (nValue == True): self.services |= 0x00000800
        else: self.services &= ~0x00000800
    IsServicesSpells = property(get_IsServicesSpells, set_IsServicesSpells)
    def get_IsServicesMagicItems(self):
        return (self.services & 0x00001000) != 0
    def set_IsServicesMagicItems(self, nValue):
        if (nValue == True): self.services |= 0x00001000
        else: self.services &= ~0x00001000
    IsServicesMagicItems = property(get_IsServicesMagicItems, set_IsServicesMagicItems)
    def get_IsServicesPotions(self):
        return (self.services & 0x00002000) != 0
    def set_IsServicesPotions(self, nValue):
        if (nValue == True): self.services |= 0x00002000
        else: self.services &= ~0x00002000
    IsServicesPotions = property(get_IsServicesPotions, set_IsServicesPotions)
    def get_IsServicesTraining(self):
        return (self.services & 0x00004000) != 0
    def set_IsServicesTraining(self, nValue):
        if (nValue == True): self.services |= 0x00004000
        else: self.services &= ~0x00004000
    IsServicesTraining = property(get_IsServicesTraining, set_IsServicesTraining)
    def get_IsServicesRecharge(self):
        return (self.services & 0x00010000) != 0
    def set_IsServicesRecharge(self, nValue):
        if (nValue == True): self.services |= 0x00010000
        else: self.services &= ~0x00010000
    IsServicesRecharge = property(get_IsServicesRecharge, set_IsServicesRecharge)
    def get_IsServicesRepair(self):
        return (self.services & 0x00020000) != 0
    def set_IsServicesRepair(self, nValue):
        if (nValue == True): self.services |= 0x00020000
        else: self.services &= ~0x00020000
    IsServicesRepair = property(get_IsServicesRepair, set_IsServicesRepair)
    
class CREARecord(BaseRecord):
    def CopyAsOverride(self, targetMod):
        FID = CBash.CopyCREARecord(self._CollectionIndex, self._ModName, self._recordID, targetMod._ModName, c_bool(True))
        if(FID): return CREARecord(self._CollectionIndex, targetMod._ModName, FID)
        return None
    def CopyAsNew(self, targetMod):
        FID = CBash.CopyCREARecord(self._CollectionIndex, self._ModName, self._recordID, targetMod._ModName, c_bool(False))
        if(FID): return CREARecord(self._CollectionIndex, targetMod._ModName, FID)
        return None
    class Faction(object):
        def __init__(self, CollectionIndex, ModName, recordID, subField, listIndex):
            self._CollectionIndex = CollectionIndex
            self._ModName = ModName
            self._recordID = recordID
            self._subField = subField
            self._listIndex = listIndex
        def get_faction(self):
            CBash.ReadFIDListField.restype = POINTER(c_uint)
            retValue = CBash.ReadFIDListField(self._CollectionIndex, self._ModName, self._recordID, self._subField, self._listIndex, 1)
            if(retValue): return retValue.contents.value
            return None
        def set_faction(self, nValue):
            CBash.SetFIDListFieldUI(self._CollectionIndex, self._ModName, self._recordID, self._subField, self._listIndex, 1, nValue)
        faction = property(get_faction, set_faction)
        def get_rank(self):
            CBash.ReadFIDListField.restype = POINTER(c_ubyte)
            retValue = CBash.ReadFIDListField(self._CollectionIndex, self._ModName, self._recordID, self._subField, self._listIndex, 2)
            if(retValue): return retValue.contents.value
            return None
        def set_rank(self, nValue):
            CBash.SetFIDListFieldUC(self._CollectionIndex, self._ModName, self._recordID, self._subField, self._listIndex, 2, c_ubyte(nValue))
        rank = property(get_rank, set_rank)
        def get_unused1(self):
            numRecords = CBash.GetFIDListArraySize(self._CollectionIndex, self._ModName, self._recordID, self._subField, self._listIndex, 3)
            if(numRecords > 0):
                cRecords = POINTER(c_ubyte * numRecords)()
                CBash.GetFIDListArray(self._CollectionIndex, self._ModName, self._recordID, self._subField, self._listIndex, 3, byref(cRecords))
                return [cRecords.contents[x] for x in range(0, numRecords)]
            return []
        def set_unused1(self, nValue):
            CBash.SetFIDListFieldR(self._CollectionIndex, self._ModName, self._recordID, self._subField, self._listIndex, 3, struct.pack('3B', *nValue), 3)
        unused1 = property(get_unused1, set_unused1)
    class Item(object):
        def __init__(self, CollectionIndex, ModName, recordID, subField, listIndex):
            self._CollectionIndex = CollectionIndex
            self._ModName = ModName
            self._recordID = recordID
            self._subField = subField
            self._listIndex = listIndex
        def get_item(self):
            CBash.ReadFIDListField.restype = POINTER(c_uint)
            retValue = CBash.ReadFIDListField(self._CollectionIndex, self._ModName, self._recordID, self._subField, self._listIndex, 1)
            if(retValue): return retValue.contents.value
            return None
        def set_item(self, nValue):
            CBash.SetFIDListFieldUI(self._CollectionIndex, self._ModName, self._recordID, self._subField, self._listIndex, 1, nValue)
        item = property(get_item, set_item)
        def get_count(self):
            CBash.ReadFIDListField.restype = POINTER(c_int)
            retValue = CBash.ReadFIDListField(self._CollectionIndex, self._ModName, self._recordID, self._subField, self._listIndex, 2)
            if(retValue): return retValue.contents.value
            return None
        def set_count(self, nValue):
            CBash.SetFIDListFieldI(self._CollectionIndex, self._ModName, self._recordID, self._subField, self._listIndex, 2, nValue)
        count = property(get_count, set_count)
    class Sound(object):
        def __init__(self, CollectionIndex, ModName, recordID, subField, listIndex):
            self._CollectionIndex = CollectionIndex
            self._ModName = ModName
            self._recordID = recordID
            self._subField = subField
            self._listIndex = listIndex
        def get_type(self):
            CBash.ReadFIDListField.restype = POINTER(c_uint)
            retValue = CBash.ReadFIDListField(self._CollectionIndex, self._ModName, self._recordID, self._subField, self._listIndex, 1)
            if(retValue): return retValue.contents.value
            return None
        def set_type(self, nValue):
            CBash.SetFIDListFieldUI(self._CollectionIndex, self._ModName, self._recordID, self._subField, self._listIndex, 1, nValue)
        type = property(get_type, set_type)
        def get_sound(self):
            CBash.ReadFIDListField.restype = POINTER(c_uint)
            retValue = CBash.ReadFIDListField(self._CollectionIndex, self._ModName, self._recordID, self._subField, self._listIndex, 2)
            if(retValue): return retValue.contents.value
            return None
        def set_sound(self, nValue):
            CBash.SetFIDListFieldUI(self._CollectionIndex, self._ModName, self._recordID, self._subField, self._listIndex, 2, nValue)
        sound = property(get_sound, set_sound)
        def get_chance(self):
            CBash.ReadFIDListField.restype = POINTER(c_ubyte)
            retValue = CBash.ReadFIDListField(self._CollectionIndex, self._ModName, self._recordID, self._subField, self._listIndex, 3)
            if(retValue): return retValue.contents.value
            return None
        def set_chance(self, nValue):
            CBash.SetFIDListFieldUC(self._CollectionIndex, self._ModName, self._recordID, self._subField, self._listIndex, 3, c_ubyte(nValue))
        chance = property(get_chance, set_chance)
    def newFactionsElement(self):
        listIndex = CBash.CreateFIDListElement(self._CollectionIndex, self._ModName, self._recordID, 20)
        if(listIndex == -1): return None
        return self.Faction(self._CollectionIndex, self._ModName, self._recordID, 20, listIndex)
    def newItemsElement(self):
        listIndex = CBash.CreateFIDListElement(self._CollectionIndex, self._ModName, self._recordID, 23)
        if(listIndex == -1): return None
        return self.Item(self._CollectionIndex, self._ModName, self._recordID, 23, listIndex)
    def newSoundsElement(self):
        listIndex = CBash.CreateFIDListElement(self._CollectionIndex, self._ModName, self._recordID, 59)
        if(listIndex == -1): return None
        return self.Sound(self._CollectionIndex, self._ModName, self._recordID, 59, listIndex)
    def get_full(self):
        CBash.ReadFIDField.restype = c_char_p
        return CBash.ReadFIDField(self._CollectionIndex, self._ModName, self._recordID, 6)
    def set_full(self, nValue):
        CBash.SetFIDFieldStr(self._CollectionIndex, self._ModName, self._recordID, 6, nValue)
    full = property(get_full, set_full)
    def get_modPath(self):
        CBash.ReadFIDField.restype = c_char_p
        return CBash.ReadFIDField(self._CollectionIndex, self._ModName, self._recordID, 7)
    def set_modPath(self, nValue):
        CBash.SetFIDFieldStr(self._CollectionIndex, self._ModName, self._recordID, 7, nValue)
    modPath = property(get_modPath, set_modPath)
    def get_modb(self):
        CBash.ReadFIDField.restype = POINTER(c_float)
        retValue = CBash.ReadFIDField(self._CollectionIndex, self._ModName, self._recordID, 8)
        if(retValue): return retValue.contents.value
        return None
    def set_modb(self, nValue):
        CBash.SetFIDFieldF(self._CollectionIndex, self._ModName, self._recordID, 8, c_float(nValue))
    modb = property(get_modb, set_modb)
    def get_modt_p(self):
        numRecords = CBash.GetFIDFieldArraySize(self._CollectionIndex, self._ModName, self._recordID, 9)
        if(numRecords > 0):
            cRecords = POINTER(c_ubyte * numRecords)()
            CBash.GetFIDFieldArray(self._CollectionIndex, self._ModName, self._recordID, 9, byref(cRecords))
            return [cRecords.contents[x] for x in range(0, numRecords)]
        return []
    def set_modt_p(self, nValue):
        length = len(nValue)
        CBash.SetFIDFieldR(self._CollectionIndex, self._ModName, self._recordID, 9, struct.pack('B' * length, *nValue), length)
    modt_p = property(get_modt_p, set_modt_p)
    def get_spells(self):
        numRecords = CBash.GetFIDFieldArraySize(self._CollectionIndex, self._ModName, self._recordID, 10)
        if(numRecords > 0):
            cRecords = (POINTER(c_uint) * numRecords)()
            CBash.GetFIDFieldArray(self._CollectionIndex, self._ModName, self._recordID, 10, byref(cRecords))
            return [cRecords[x].contents.value for x in range(0, numRecords)]
        return []
    def set_spells(self, nValue):
        CBash.SetFIDFieldUIA(self._CollectionIndex, self._ModName, self._recordID, 10, struct.pack('I' * len(nValue), *nValue), len(nValue))
    spells = property(get_spells, set_spells)
    def get_bodyParts(self):
        numRecords = CBash.GetFIDFieldArraySize(self._CollectionIndex, self._ModName, self._recordID, 11)
        if(numRecords > 0):
            cRecords = cRecords = (POINTER(c_char_p) * numRecords)()
            CBash.GetFIDFieldArray(self._CollectionIndex, self._ModName, self._recordID, 11, byref(cRecords))
            return [string_at(cRecords[x]) for x in range(0, numRecords)]
        return []
    def set_bodyParts(self, nValue):
        length = len(nValue)
        cRecords = (c_char_p * length)(*nValue)
        CBash.SetFIDFieldStrA(self._CollectionIndex, self._ModName, self._recordID, 11, byref(cRecords), length)
    bodyParts = property(get_bodyParts, set_bodyParts)
    def get_nift_p(self):
        numRecords = CBash.GetFIDFieldArraySize(self._CollectionIndex, self._ModName, self._recordID, 12)
        if(numRecords > 0):
            cRecords = POINTER(c_ubyte * numRecords)()
            CBash.GetFIDFieldArray(self._CollectionIndex, self._ModName, self._recordID, 12, byref(cRecords))
            return [cRecords.contents[x] for x in range(0, numRecords)]
        return []
    def set_nift_p(self, nValue):
        length = len(nValue)
        CBash.SetFIDFieldR(self._CollectionIndex, self._ModName, self._recordID, 12, struct.pack('B' * length, *nValue), length)
    nift_p = property(get_nift_p, set_nift_p)
    def get_flags(self):
        CBash.ReadFIDField.restype = POINTER(c_uint)
        retValue = CBash.ReadFIDField(self._CollectionIndex, self._ModName, self._recordID, 13)
        if(retValue): return retValue.contents.value
        return None
    def set_flags(self, nValue):
        CBash.SetFIDFieldUI(self._CollectionIndex, self._ModName, self._recordID, 13, nValue)
    flags = property(get_flags, set_flags)
    def get_baseSpell(self):
        CBash.ReadFIDField.restype = POINTER(c_ushort)
        retValue = CBash.ReadFIDField(self._CollectionIndex, self._ModName, self._recordID, 14)
        if(retValue): return retValue.contents.value
        return None
    def set_baseSpell(self, nValue):
        CBash.SetFIDFieldUS(self._CollectionIndex, self._ModName, self._recordID, 14, c_ushort(nValue))
    baseSpell = property(get_baseSpell, set_baseSpell)
    def get_fatigue(self):
        CBash.ReadFIDField.restype = POINTER(c_ushort)
        retValue = CBash.ReadFIDField(self._CollectionIndex, self._ModName, self._recordID, 15)
        if(retValue): return retValue.contents.value
        return None
    def set_fatigue(self, nValue):
        CBash.SetFIDFieldUS(self._CollectionIndex, self._ModName, self._recordID, 15, c_ushort(nValue))
    fatigue = property(get_fatigue, set_fatigue)
    def get_barterGold(self):
        CBash.ReadFIDField.restype = POINTER(c_ushort)
        retValue = CBash.ReadFIDField(self._CollectionIndex, self._ModName, self._recordID, 16)
        if(retValue): return retValue.contents.value
        return None
    def set_barterGold(self, nValue):
        CBash.SetFIDFieldUS(self._CollectionIndex, self._ModName, self._recordID, 16, c_ushort(nValue))
    barterGold = property(get_barterGold, set_barterGold)
    def get_level(self):
        CBash.ReadFIDField.restype = POINTER(c_short)
        retValue = CBash.ReadFIDField(self._CollectionIndex, self._ModName, self._recordID, 17)
        if(retValue): return retValue.contents.value
        return None
    def set_level(self, nValue):
        CBash.SetFIDFieldS(self._CollectionIndex, self._ModName, self._recordID, 17, c_short(nValue))
    level = property(get_level, set_level)
    def get_calcMin(self):
        CBash.ReadFIDField.restype = POINTER(c_ushort)
        retValue = CBash.ReadFIDField(self._CollectionIndex, self._ModName, self._recordID, 18)
        if(retValue): return retValue.contents.value
        return None
    def set_calcMin(self, nValue):
        CBash.SetFIDFieldUS(self._CollectionIndex, self._ModName, self._recordID, 18, c_ushort(nValue))
    calcMin = property(get_calcMin, set_calcMin)
    def get_calcMax(self):
        CBash.ReadFIDField.restype = POINTER(c_ushort)
        retValue = CBash.ReadFIDField(self._CollectionIndex, self._ModName, self._recordID, 19)
        if(retValue): return retValue.contents.value
        return None
    def set_calcMax(self, nValue):
        CBash.SetFIDFieldUS(self._CollectionIndex, self._ModName, self._recordID, 19, c_ushort(nValue))
    calcMax = property(get_calcMax, set_calcMax)
    def get_factions(self):
        numRecords = CBash.GetFIDListSize(self._CollectionIndex, self._ModName, self._recordID, 20)
        if(numRecords > 0): return [self.Faction(self._CollectionIndex, self._ModName, self._recordID, 20, x) for x in range(0, numRecords)]
        return []
    def set_factions(self, nFactions):
        diffLength = len(nFactions) - CBash.GetFIDListSize(self._CollectionIndex, self._ModName, self._recordID, 20)
        nValues = [(faction.faction,faction.rank,faction.unused1) for faction in nFactions]
        while(diffLength < 0):
            CBash.DeleteFIDListElement(self._CollectionIndex, self._ModName, self._recordID, 20)
            diffLength += 1
        while(diffLength > 0):
            CBash.CreateFIDListElement(self._CollectionIndex, self._ModName, self._recordID, 20)
            diffLength -= 1
        for oFaction, nValue in zip(self.factions, nValues):
            oFaction.faction, oFaction.rank, oFaction.unused1 = nValue
    factions = property(get_factions, set_factions)
    def get_deathItem(self):
        CBash.ReadFIDField.restype = POINTER(c_uint)
        retValue = CBash.ReadFIDField(self._CollectionIndex, self._ModName, self._recordID, 21)
        if(retValue): return retValue.contents.value
        return None
    def set_deathItem(self, nValue):
        CBash.SetFIDFieldUI(self._CollectionIndex, self._ModName, self._recordID, 21, nValue)
    deathItem = property(get_deathItem, set_deathItem)
    def get_script(self):
        CBash.ReadFIDField.restype = POINTER(c_uint)
        retValue = CBash.ReadFIDField(self._CollectionIndex, self._ModName, self._recordID, 22)
        if(retValue): return retValue.contents.value
        return None
    def set_script(self, nValue):
        CBash.SetFIDFieldUI(self._CollectionIndex, self._ModName, self._recordID, 22, nValue)
    script = property(get_script, set_script)
    def get_items(self):
        numRecords = CBash.GetFIDListSize(self._CollectionIndex, self._ModName, self._recordID, 23)
        if(numRecords > 0): return [self.Item(self._CollectionIndex, self._ModName, self._recordID, 23, x) for x in range(0, numRecords)]
        return []
    def set_items(self, nItems):
        diffLength = len(nItems) - CBash.GetFIDListSize(self._CollectionIndex, self._ModName, self._recordID, 23)
        nValues = [(item.item, item.count) for item in nItems]
        while(diffLength < 0):
            CBash.DeleteFIDListElement(self._CollectionIndex, self._ModName, self._recordID, 23)
            diffLength += 1
        while(diffLength > 0):
            CBash.CreateFIDListElement(self._CollectionIndex, self._ModName, self._recordID, 23)
            diffLength -= 1
        for oItem, nValue in zip(self.items, nValues):
            oItem.item, oItem.count = nValue
    items = property(get_items, set_items)
    def get_aggression(self):
        CBash.ReadFIDField.restype = POINTER(c_ubyte)
        retValue = CBash.ReadFIDField(self._CollectionIndex, self._ModName, self._recordID, 24)
        if(retValue): return retValue.contents.value
        return None
    def set_aggression(self, nValue):
        CBash.SetFIDFieldUC(self._CollectionIndex, self._ModName, self._recordID, 24, c_ubyte(nValue))
    aggression = property(get_aggression, set_aggression)
    def get_confidence(self):
        CBash.ReadFIDField.restype = POINTER(c_ubyte)
        retValue = CBash.ReadFIDField(self._CollectionIndex, self._ModName, self._recordID, 25)
        if(retValue): return retValue.contents.value
        return None
    def set_confidence(self, nValue):
        CBash.SetFIDFieldUC(self._CollectionIndex, self._ModName, self._recordID, 25, c_ubyte(nValue))
    confidence = property(get_confidence, set_confidence)
    def get_energyLevel(self):
        CBash.ReadFIDField.restype = POINTER(c_ubyte)
        retValue = CBash.ReadFIDField(self._CollectionIndex, self._ModName, self._recordID, 26)
        if(retValue): return retValue.contents.value
        return None
    def set_energyLevel(self, nValue):
        CBash.SetFIDFieldUC(self._CollectionIndex, self._ModName, self._recordID, 26, c_ubyte(nValue))
    energyLevel = property(get_energyLevel, set_energyLevel)
    def get_responsibility(self):
        CBash.ReadFIDField.restype = POINTER(c_ubyte)
        retValue = CBash.ReadFIDField(self._CollectionIndex, self._ModName, self._recordID, 27)
        if(retValue): return retValue.contents.value
        return None
    def set_responsibility(self, nValue):
        CBash.SetFIDFieldUC(self._CollectionIndex, self._ModName, self._recordID, 27, c_ubyte(nValue))
    responsibility = property(get_responsibility, set_responsibility)
    def get_services(self):
        CBash.ReadFIDField.restype = POINTER(c_uint)
        retValue = CBash.ReadFIDField(self._CollectionIndex, self._ModName, self._recordID, 28)
        if(retValue): return retValue.contents.value
        return None
    def set_services(self, nValue):
        CBash.SetFIDFieldUI(self._CollectionIndex, self._ModName, self._recordID, 28, nValue)
    services = property(get_services, set_services)
    def get_trainSkill(self):
        CBash.ReadFIDField.restype = POINTER(c_byte)
        retValue = CBash.ReadFIDField(self._CollectionIndex, self._ModName, self._recordID, 29)
        if(retValue): return retValue.contents.value
        return None
    def set_trainSkill(self, nValue):
        CBash.SetFIDFieldC(self._CollectionIndex, self._ModName, self._recordID, 29, c_byte(nValue))
    trainSkill = property(get_trainSkill, set_trainSkill)
    def get_trainLevel(self):
        CBash.ReadFIDField.restype = POINTER(c_ubyte)
        retValue = CBash.ReadFIDField(self._CollectionIndex, self._ModName, self._recordID, 30)
        if(retValue): return retValue.contents.value
        return None
    def set_trainLevel(self, nValue):
        CBash.SetFIDFieldUC(self._CollectionIndex, self._ModName, self._recordID, 30, c_ubyte(nValue))
    trainLevel = property(get_trainLevel, set_trainLevel)
    def get_unused1(self):
        numRecords = CBash.GetFIDFieldArraySize(self._CollectionIndex, self._ModName, self._recordID, 31)
        if(numRecords > 0):
            cRecords = POINTER(c_ubyte * numRecords)()
            CBash.GetFIDFieldArray(self._CollectionIndex, self._ModName, self._recordID, 31, byref(cRecords))
            return [cRecords.contents[x] for x in range(0, numRecords)]
        return []
    def set_unused1(self, nValue):
        CBash.SetFIDFieldR(self._CollectionIndex, self._ModName, self._recordID, 31, struct.pack('2B', *nValue), 2)
    unused1 = property(get_unused1, set_unused1)
    def get_aiPackages(self):
        numRecords = CBash.GetFIDFieldArraySize(self._CollectionIndex, self._ModName, self._recordID, 32)
        if(numRecords > 0):
            cRecords = (POINTER(c_uint) * numRecords)()
            CBash.GetFIDFieldArray(self._CollectionIndex, self._ModName, self._recordID, 32, byref(cRecords))
            return [cRecords[x].contents.value for x in range(0, numRecords)]
        return []
    def set_aiPackages(self, nValue):
        CBash.SetFIDFieldUIA(self._CollectionIndex, self._ModName, self._recordID, 32, struct.pack('I' * len(nValue), *nValue), len(nValue))
    aiPackages = property(get_aiPackages, set_aiPackages)
    def get_animations(self):
        numRecords = CBash.GetFIDFieldArraySize(self._CollectionIndex, self._ModName, self._recordID, 33)
        if(numRecords > 0):
            cRecords = cRecords = (POINTER(c_char_p) * numRecords)()
            CBash.GetFIDFieldArray(self._CollectionIndex, self._ModName, self._recordID, 33, byref(cRecords))
            return [string_at(cRecords[x]) for x in range(0, numRecords)]
        return []
    def set_animations(self, nValue):
        length = len(nValue)
        cRecords = (c_char_p * length)(*nValue)
        CBash.SetFIDFieldStrA(self._CollectionIndex, self._ModName, self._recordID, 33, byref(cRecords), length)
    animations = property(get_animations, set_animations)
    def get_creatureType(self):
        CBash.ReadFIDField.restype = POINTER(c_ubyte)
        retValue = CBash.ReadFIDField(self._CollectionIndex, self._ModName, self._recordID, 34)
        if(retValue): return retValue.contents.value
        return None
    def set_creatureType(self, nValue):
        CBash.SetFIDFieldUC(self._CollectionIndex, self._ModName, self._recordID, 34, c_ubyte(nValue))
    creatureType = property(get_creatureType, set_creatureType)
    def get_combat(self):
        CBash.ReadFIDField.restype = POINTER(c_ubyte)
        retValue = CBash.ReadFIDField(self._CollectionIndex, self._ModName, self._recordID, 35)
        if(retValue): return retValue.contents.value
        return None
    def set_combat(self, nValue):
        CBash.SetFIDFieldUC(self._CollectionIndex, self._ModName, self._recordID, 35, c_ubyte(nValue))
    combat = property(get_combat, set_combat)
    def get_magic(self):
        CBash.ReadFIDField.restype = POINTER(c_ubyte)
        retValue = CBash.ReadFIDField(self._CollectionIndex, self._ModName, self._recordID, 36)
        if(retValue): return retValue.contents.value
        return None
    def set_magic(self, nValue):
        CBash.SetFIDFieldUC(self._CollectionIndex, self._ModName, self._recordID, 36, c_ubyte(nValue))
    magic = property(get_magic, set_magic)
    def get_stealth(self):
        CBash.ReadFIDField.restype = POINTER(c_ubyte)
        retValue = CBash.ReadFIDField(self._CollectionIndex, self._ModName, self._recordID, 37)
        if(retValue): return retValue.contents.value
        return None
    def set_stealth(self, nValue):
        CBash.SetFIDFieldUC(self._CollectionIndex, self._ModName, self._recordID, 37, c_ubyte(nValue))
    stealth = property(get_stealth, set_stealth)
    def get_soul(self):
        CBash.ReadFIDField.restype = POINTER(c_ubyte)
        retValue = CBash.ReadFIDField(self._CollectionIndex, self._ModName, self._recordID, 38)
        if(retValue): return retValue.contents.value
        return None
    def set_soul(self, nValue):
        CBash.SetFIDFieldUC(self._CollectionIndex, self._ModName, self._recordID, 38, c_ubyte(nValue))
    soul = property(get_soul, set_soul)
    def get_unused2(self):
        numRecords = CBash.GetFIDFieldArraySize(self._CollectionIndex, self._ModName, self._recordID, 39)
        if(numRecords > 0):
            cRecords = POINTER(c_ubyte * numRecords)()
            CBash.GetFIDFieldArray(self._CollectionIndex, self._ModName, self._recordID, 39, byref(cRecords))
            return [cRecords.contents[x] for x in range(0, numRecords)]
        return []
    def set_unused2(self, nValue):
        CBash.SetFIDFieldR(self._CollectionIndex, self._ModName, self._recordID, 39, struct.pack('B', *nValue), 1)
    unused2 = property(get_unused2, set_unused2)
    def get_health(self):
        CBash.ReadFIDField.restype = POINTER(c_ushort)
        retValue = CBash.ReadFIDField(self._CollectionIndex, self._ModName, self._recordID, 40)
        if(retValue): return retValue.contents.value
        return None
    def set_health(self, nValue):
        CBash.SetFIDFieldUS(self._CollectionIndex, self._ModName, self._recordID, 40, c_ushort(nValue))
    health = property(get_health, set_health)
    def get_unused3(self):
        numRecords = CBash.GetFIDFieldArraySize(self._CollectionIndex, self._ModName, self._recordID, 41)
        if(numRecords > 0):
            cRecords = POINTER(c_ubyte * numRecords)()
            CBash.GetFIDFieldArray(self._CollectionIndex, self._ModName, self._recordID, 41, byref(cRecords))
            return [cRecords.contents[x] for x in range(0, numRecords)]
        return []
    def set_unused3(self, nValue):
        CBash.SetFIDFieldR(self._CollectionIndex, self._ModName, self._recordID, 41, struct.pack('2B', *nValue), 2)
    unused3 = property(get_unused3, set_unused3)
    def get_attackDamage(self):
        CBash.ReadFIDField.restype = POINTER(c_ushort)
        retValue = CBash.ReadFIDField(self._CollectionIndex, self._ModName, self._recordID, 42)
        if(retValue): return retValue.contents.value
        return None
    def set_attackDamage(self, nValue):
        CBash.SetFIDFieldUS(self._CollectionIndex, self._ModName, self._recordID, 42, c_ushort(nValue))
    attackDamage = property(get_attackDamage, set_attackDamage)
    def get_strength(self):
        CBash.ReadFIDField.restype = POINTER(c_ubyte)
        retValue = CBash.ReadFIDField(self._CollectionIndex, self._ModName, self._recordID, 43)
        if(retValue): return retValue.contents.value
        return None
    def set_strength(self, nValue):
        CBash.SetFIDFieldUC(self._CollectionIndex, self._ModName, self._recordID, 43, c_ubyte(nValue))
    strength = property(get_strength, set_strength)
    def get_intelligence(self):
        CBash.ReadFIDField.restype = POINTER(c_ubyte)
        retValue = CBash.ReadFIDField(self._CollectionIndex, self._ModName, self._recordID, 44)
        if(retValue): return retValue.contents.value
        return None
    def set_intelligence(self, nValue):
        CBash.SetFIDFieldUC(self._CollectionIndex, self._ModName, self._recordID, 44, c_ubyte(nValue))
    intelligence = property(get_intelligence, set_intelligence)
    def get_willpower(self):
        CBash.ReadFIDField.restype = POINTER(c_ubyte)
        retValue = CBash.ReadFIDField(self._CollectionIndex, self._ModName, self._recordID, 45)
        if(retValue): return retValue.contents.value
        return None
    def set_willpower(self, nValue):
        CBash.SetFIDFieldUC(self._CollectionIndex, self._ModName, self._recordID, 45, c_ubyte(nValue))
    willpower = property(get_willpower, set_willpower)
    def get_agility(self):
        CBash.ReadFIDField.restype = POINTER(c_ubyte)
        retValue = CBash.ReadFIDField(self._CollectionIndex, self._ModName, self._recordID, 46)
        if(retValue): return retValue.contents.value
        return None
    def set_agility(self, nValue):
        CBash.SetFIDFieldUC(self._CollectionIndex, self._ModName, self._recordID, 46, c_ubyte(nValue))
    agility = property(get_agility, set_agility)
    def get_speed(self):
        CBash.ReadFIDField.restype = POINTER(c_ubyte)
        retValue = CBash.ReadFIDField(self._CollectionIndex, self._ModName, self._recordID, 47)
        if(retValue): return retValue.contents.value
        return None
    def set_speed(self, nValue):
        CBash.SetFIDFieldUC(self._CollectionIndex, self._ModName, self._recordID, 47, c_ubyte(nValue))
    speed = property(get_speed, set_speed)
    def get_endurance(self):
        CBash.ReadFIDField.restype = POINTER(c_ubyte)
        retValue = CBash.ReadFIDField(self._CollectionIndex, self._ModName, self._recordID, 48)
        if(retValue): return retValue.contents.value
        return None
    def set_endurance(self, nValue):
        CBash.SetFIDFieldUC(self._CollectionIndex, self._ModName, self._recordID, 48, c_ubyte(nValue))
    endurance = property(get_endurance, set_endurance)
    def get_personality(self):
        CBash.ReadFIDField.restype = POINTER(c_ubyte)
        retValue = CBash.ReadFIDField(self._CollectionIndex, self._ModName, self._recordID, 49)
        if(retValue): return retValue.contents.value
        return None
    def set_personality(self, nValue):
        CBash.SetFIDFieldUC(self._CollectionIndex, self._ModName, self._recordID, 49, c_ubyte(nValue))
    personality = property(get_personality, set_personality)
    def get_luck(self):
        CBash.ReadFIDField.restype = POINTER(c_ubyte)
        retValue = CBash.ReadFIDField(self._CollectionIndex, self._ModName, self._recordID, 50)
        if(retValue): return retValue.contents.value
        return None
    def set_luck(self, nValue):
        CBash.SetFIDFieldUC(self._CollectionIndex, self._ModName, self._recordID, 50, c_ubyte(nValue))
    luck = property(get_luck, set_luck)
    def get_attackReach(self):
        CBash.ReadFIDField.restype = POINTER(c_ubyte)
        retValue = CBash.ReadFIDField(self._CollectionIndex, self._ModName, self._recordID, 51)
        if(retValue): return retValue.contents.value
        return None
    def set_attackReach(self, nValue):
        CBash.SetFIDFieldUC(self._CollectionIndex, self._ModName, self._recordID, 51, c_ubyte(nValue))
    attackReach = property(get_attackReach, set_attackReach)
    def get_combatStyle(self):
        CBash.ReadFIDField.restype = POINTER(c_uint)
        retValue = CBash.ReadFIDField(self._CollectionIndex, self._ModName, self._recordID, 52)
        if(retValue): return retValue.contents.value
        return None
    def set_combatStyle(self, nValue):
        CBash.SetFIDFieldUI(self._CollectionIndex, self._ModName, self._recordID, 52, nValue)
    combatStyle = property(get_combatStyle, set_combatStyle)
    def get_turningSpeed(self):
        CBash.ReadFIDField.restype = POINTER(c_float)
        retValue = CBash.ReadFIDField(self._CollectionIndex, self._ModName, self._recordID, 53)
        if(retValue): return retValue.contents.value
        return None
    def set_turningSpeed(self, nValue):
        CBash.SetFIDFieldF(self._CollectionIndex, self._ModName, self._recordID, 53, c_float(nValue))
    turningSpeed = property(get_turningSpeed, set_turningSpeed)
    def get_baseScale(self):
        CBash.ReadFIDField.restype = POINTER(c_float)
        retValue = CBash.ReadFIDField(self._CollectionIndex, self._ModName, self._recordID, 54)
        if(retValue): return retValue.contents.value
        return None
    def set_baseScale(self, nValue):
        CBash.SetFIDFieldF(self._CollectionIndex, self._ModName, self._recordID, 54, c_float(nValue))
    baseScale = property(get_baseScale, set_baseScale)
    def get_footWeight(self):
        CBash.ReadFIDField.restype = POINTER(c_float)
        retValue = CBash.ReadFIDField(self._CollectionIndex, self._ModName, self._recordID, 55)
        if(retValue): return retValue.contents.value
        return None
    def set_footWeight(self, nValue):
        CBash.SetFIDFieldF(self._CollectionIndex, self._ModName, self._recordID, 55, c_float(nValue))
    footWeight = property(get_footWeight, set_footWeight)
    def get_inheritsSoundsFrom(self):
        CBash.ReadFIDField.restype = POINTER(c_uint)
        retValue = CBash.ReadFIDField(self._CollectionIndex, self._ModName, self._recordID, 56)
        if(retValue): return retValue.contents.value
        return None
    def set_inheritsSoundsFrom(self, nValue):
        CBash.SetFIDFieldUI(self._CollectionIndex, self._ModName, self._recordID, 56, nValue)
    inheritsSoundsFrom = property(get_inheritsSoundsFrom, set_inheritsSoundsFrom)
    def get_bloodSprayPath(self):
        CBash.ReadFIDField.restype = c_char_p
        return CBash.ReadFIDField(self._CollectionIndex, self._ModName, self._recordID, 57)
    def set_bloodSprayPath(self, nValue):
        CBash.SetFIDFieldStr(self._CollectionIndex, self._ModName, self._recordID, 57, nValue)
    bloodSprayPath = property(get_bloodSprayPath, set_bloodSprayPath)
    def get_bloodDecalPath(self):
        CBash.ReadFIDField.restype = c_char_p
        return CBash.ReadFIDField(self._CollectionIndex, self._ModName, self._recordID, 58)
    def set_bloodDecalPath(self, nValue):
        CBash.SetFIDFieldStr(self._CollectionIndex, self._ModName, self._recordID, 58, nValue)
    bloodDecalPath = property(get_bloodDecalPath, set_bloodDecalPath)
    def get_sounds(self):
        numRecords = CBash.GetFIDListSize(self._CollectionIndex, self._ModName, self._recordID, 59)
        if(numRecords > 0): return [self.Sound(self._CollectionIndex, self._ModName, self._recordID, 59, x) for x in range(0, numRecords)]
        return []
    def set_sounds(self, nSounds):
        diffLength = len(nSounds) - CBash.GetFIDListSize(self._CollectionIndex, self._ModName, self._recordID, 59)
        nValues = [(nSound.type, nSound.sound, nSound.chance) for nSound in nSounds]
        while(diffLength < 0):
            CBash.DeleteFIDListElement(self._CollectionIndex, self._ModName, self._recordID, 59)
            diffLength += 1
        while(diffLength > 0):
            CBash.CreateFIDListElement(self._CollectionIndex, self._ModName, self._recordID, 59)
            diffLength -= 1
        for oSound, nValue in zip(self.sounds, nValues):
            oSound.type, oSound.sound, oSound.chance = nValue
    sounds = property(get_sounds, set_sounds)
    def get_IsBiped(self):
        return (self.flags & 0x00000001) != 0
    def set_IsBiped(self, nValue):
        if (nValue == True): self.flags |= 0x00000001
        else: self.flags &= ~0x00000001
    IsBiped = property(get_IsBiped, set_IsBiped)
    def get_IsEssential(self):
        return (self.flags & 0x00000002) != 0
    def set_IsEssential(self, nValue):
        if (nValue == True): self.flags |= 0x00000002
        else: self.flags &= ~0x00000002
    IsEssential = property(get_IsEssential, set_IsEssential)
    def get_IsWeaponAndShield(self):
        return (self.flags & 0x00000004) != 0
    def set_IsWeaponAndShield(self, nValue):
        if (nValue == True): self.flags |= 0x00000004
        else: self.flags &= ~0x00000004
    IsWeaponAndShield = property(get_IsWeaponAndShield, set_IsWeaponAndShield)
    def get_IsRespawn(self):
        return (self.flags & 0x00000008) != 0
    def set_IsRespawn(self, nValue):
        if (nValue == True): self.flags |= 0x00000008
        else: self.flags &= ~0x00000008
    IsRespawn = property(get_IsRespawn, set_IsRespawn)
    def get_IsSwims(self):
        return (self.flags & 0x00000010) != 0
    def set_IsSwims(self, nValue):
        if (nValue == True): self.flags |= 0x00000010
        else: self.flags &= ~0x00000010
    IsSwims = property(get_IsSwims, set_IsSwims)
    def get_IsFlies(self):
        return (self.flags & 0x00000020) != 0
    def set_IsFlies(self, nValue):
        if (nValue == True): self.flags |= 0x00000020
        else: self.flags &= ~0x00000020
    IsFlies = property(get_IsFlies, set_IsFlies)
    def get_IsWalks(self):
        return (self.flags & 0x00000040) != 0
    def set_IsWalks(self, nValue):
        if (nValue == True): self.flags |= 0x00000040
        else: self.flags &= ~0x00000040
    IsWalks = property(get_IsWalks, set_IsWalks)
    def get_IsPCLevelOffset(self):
        return (self.flags & 0x00000080) != 0
    def set_IsPCLevelOffset(self, nValue):
        if (nValue == True): self.flags |= 0x00000080
        else: self.flags &= ~0x00000080
    IsPCLevelOffset = property(get_IsPCLevelOffset, set_IsPCLevelOffset)
    def get_IsNoLowLevel(self):
        return (self.flags & 0x00000200) != 0
    def set_IsNoLowLevel(self, nValue):
        if (nValue == True): self.flags |= 0x00000200
        else: self.flags &= ~0x00000200
    IsNoLowLevel = property(get_IsNoLowLevel, set_IsNoLowLevel)
    def get_IsLowLevel(self):
        return not self.get_IsNoLowLevel()
    def set_IsLowLevel(self, nValue):
        if (nValue == True): self.flags &= ~0x00000200
        else: self.flags |= 0x00000200
    IsLowLevel = property(get_IsLowLevel, set_IsLowLevel)
    def get_IsNoBloodSpray(self):
        return (self.flags & 0x00000800) != 0
    def set_IsNoBloodSpray(self, nValue):
        if (nValue == True): self.flags |= 0x00000800
        else: self.flags &= ~0x00000800
    IsNoBloodSpray = property(get_IsNoBloodSpray, set_IsNoBloodSpray)
    def get_IsBloodSpray(self):
        return not self.get_IsNoBloodSpray()
    def set_IsBloodSpray(self, nValue):
        if (nValue == True): self.flags &= ~0x00000800
        else: self.flags |= 0x00000800
    IsBloodSpray = property(get_IsBloodSpray, set_IsBloodSpray)
    def get_IsNoBloodDecal(self):
        return (self.flags & 0x00001000) != 0
    def set_IsNoBloodDecal(self, nValue):
        if (nValue == True): self.flags |= 0x00001000
        else: self.flags &= ~0x00001000
    IsNoBloodDecal = property(get_IsNoBloodDecal, set_IsNoBloodDecal)
    def get_IsBloodDecal(self):
        return not self.get_IsNoBloodDecal()
    def set_IsBloodDecal(self, nValue):
        if (nValue == True): self.flags &= ~0x00001000
        else: self.flags |= 0x00001000
    IsBloodDecal = property(get_IsBloodDecal, set_IsBloodDecal)
    def get_IsNoHead(self):
        return (self.flags & 0x00008000) != 0
    def set_IsNoHead(self, nValue):
        if (nValue == True): self.flags |= 0x00008000
        else: self.flags &= ~0x00008000
    IsNoHead = property(get_IsNoHead, set_IsNoHead)
    def get_IsHead(self):
        return not self.get_IsNoHead()
    def set_IsHead(self, nValue):
        if (nValue == True): self.flags &= ~0x00008000
        else: self.flags |= 0x00008000
    IsHead = property(get_IsHead, set_IsHead)
    def get_IsNoRightArm(self):
        return (self.flags & 0x00010000) != 0
    def set_IsNoRightArm(self, nValue):
        if (nValue == True): self.flags |= 0x00010000
        else: self.flags &= ~0x00010000
    IsNoRightArm = property(get_IsNoRightArm, set_IsNoRightArm)
    def get_IsRightArm(self):
        return not self.get_IsNoRightArm()
    def set_IsRightArm(self, nValue):
        if (nValue == True): self.flags &= ~0x00010000
        else: self.flags |= 0x00010000
    IsRightArm = property(get_IsRightArm, set_IsRightArm)
    def get_IsNoLeftArm(self):
        return (self.flags & 0x00020000) != 0
    def set_IsNoLeftArm(self, nValue):
        if (nValue == True): self.flags |= 0x00020000
        else: self.flags &= ~0x00020000
    IsNoLeftArm = property(get_IsNoLeftArm, set_IsNoLeftArm)
    def get_IsLeftArm(self):
        return not self.get_IsNoLeftArm()
    def set_IsLeftArm(self, nValue):
        if (nValue == True): self.flags &= ~0x00020000
        else: self.flags |= 0x00020000
    IsLeftArm = property(get_IsLeftArm, set_IsLeftArm)
    def get_IsNoCombatInWater(self):
        return (self.flags & 0x00040000) != 0
    def set_IsNoCombatInWater(self, nValue):
        if (nValue == True): self.flags |= 0x00040000
        else: self.flags &= ~0x00040000
    IsNoCombatInWater = property(get_IsNoCombatInWater, set_IsNoCombatInWater)
    def get_IsCombatInWater(self):
        return not self.get_IsNoCombatInWater()
    def set_IsCombatInWater(self, nValue):
        if (nValue == True): self.flags &= ~0x00040000
        else: self.flags |= 0x00040000
    IsCombatInWater = property(get_IsCombatInWater, set_IsCombatInWater)
    def get_IsNoShadow(self):
        return (self.flags & 0x00080000) != 0
    def set_IsNoShadow(self, nValue):
        if (nValue == True): self.flags |= 0x00080000
        else: self.flags &= ~0x00080000
    IsNoShadow = property(get_IsNoShadow, set_IsNoShadow)
    def get_IsShadow(self):
        return not self.get_IsNoShadow()
    def set_IsShadow(self, nValue):
        if (nValue == True): self.flags &= ~0x00080000
        else: self.flags |= 0x00080000
    IsShadow = property(get_IsShadow, set_IsShadow)
    def get_IsNoCorpseCheck(self):
        return (self.flags & 0x00100000) != 0
    def set_IsNoCorpseCheck(self, nValue):
        if (nValue == True): self.flags |= 0x00100000
        else: self.flags &= ~0x00100000
    IsNoCorpseCheck = property(get_IsNoCorpseCheck, set_IsNoCorpseCheck)
    def get_IsCorpseCheck(self):
        return not self.get_IsNoCorpseCheck()
    def set_IsCorpseCheck(self, nValue):
        if (nValue == True): self.flags &= ~0x00100000
        else: self.flags |= 0x00100000
    IsCorpseCheck = property(get_IsCorpseCheck, set_IsCorpseCheck)
    def get_IsServicesWeapons(self):
        return (self.services & 0x00000001) != 0
    def set_IsServicesWeapons(self, nValue):
        if (nValue == True): self.services |= 0x00000001
        else: self.services &= ~0x00000001
    IsServicesWeapons = property(get_IsServicesWeapons, set_IsServicesWeapons)
    def get_IsServicesArmor(self):
        return (self.services & 0x00000002) != 0
    def set_IsServicesArmor(self, nValue):
        if (nValue == True): self.services |= 0x00000002
        else: self.services &= ~0x00000002
    IsServicesArmor = property(get_IsServicesArmor, set_IsServicesArmor)
    def get_IsServicesClothing(self):
        return (self.services & 0x00000004) != 0
    def set_IsServicesClothing(self, nValue):
        if (nValue == True): self.services |= 0x00000004
        else: self.services &= ~0x00000004
    IsServicesClothing = property(get_IsServicesClothing, set_IsServicesClothing)
    def get_IsServicesBooks(self):
        return (self.services & 0x00000008) != 0
    def set_IsServicesBooks(self, nValue):
        if (nValue == True): self.services |= 0x00000008
        else: self.services &= ~0x00000008
    IsServicesBooks = property(get_IsServicesBooks, set_IsServicesBooks)
    def get_IsServicesIngredients(self):
        return (self.services & 0x00000010) != 0
    def set_IsServicesIngredients(self, nValue):
        if (nValue == True): self.services |= 0x00000010
        else: self.services &= ~0x00000010
    IsServicesIngredients = property(get_IsServicesIngredients, set_IsServicesIngredients)
    def get_IsServicesLights(self):
        return (self.services & 0x00000080) != 0
    def set_IsServicesLights(self, nValue):
        if (nValue == True): self.services |= 0x00000080
        else: self.services &= ~0x00000080
    IsServicesLights = property(get_IsServicesLights, set_IsServicesLights)
    def get_IsServicesApparatus(self):
        return (self.services & 0x00000100) != 0
    def set_IsServicesApparatus(self, nValue):
        if (nValue == True): self.services |= 0x00000100
        else: self.services &= ~0x00000100
    IsServicesApparatus = property(get_IsServicesApparatus, set_IsServicesApparatus)
    def get_IsServicesMiscItems(self):
        return (self.services & 0x00000400) != 0
    def set_IsServicesMiscItems(self, nValue):
        if (nValue == True): self.services |= 0x00000400
        else: self.services &= ~0x00000400
    IsServicesMiscItems = property(get_IsServicesMiscItems, set_IsServicesMiscItems)
    def get_IsServicesSpells(self):
        return (self.services & 0x00000800) != 0
    def set_IsServicesSpells(self, nValue):
        if (nValue == True): self.services |= 0x00000800
        else: self.services &= ~0x00000800
    IsServicesSpells = property(get_IsServicesSpells, set_IsServicesSpells)
    def get_IsServicesMagicItems(self):
        return (self.services & 0x00001000) != 0
    def set_IsServicesMagicItems(self, nValue):
        if (nValue == True): self.services |= 0x00001000
        else: self.services &= ~0x00001000
    IsServicesMagicItems = property(get_IsServicesMagicItems, set_IsServicesMagicItems)
    def get_IsServicesPotions(self):
        return (self.services & 0x00002000) != 0
    def set_IsServicesPotions(self, nValue):
        if (nValue == True): self.services |= 0x00002000
        else: self.services &= ~0x00002000
    IsServicesPotions = property(get_IsServicesPotions, set_IsServicesPotions)
    def get_IsServicesTraining(self):
        return (self.services & 0x00004000) != 0
    def set_IsServicesTraining(self, nValue):
        if (nValue == True): self.services |= 0x00004000
        else: self.services &= ~0x00004000
    IsServicesTraining = property(get_IsServicesTraining, set_IsServicesTraining)
    def get_IsServicesRecharge(self):
        return (self.services & 0x00010000) != 0
    def set_IsServicesRecharge(self, nValue):
        if (nValue == True): self.services |= 0x00010000
        else: self.services &= ~0x00010000
    IsServicesRecharge = property(get_IsServicesRecharge, set_IsServicesRecharge)
    def get_IsServicesRepair(self):
        return (self.services & 0x00020000) != 0
    def set_IsServicesRepair(self, nValue):
        if (nValue == True): self.services |= 0x00020000
        else: self.services &= ~0x00020000
    IsServicesRepair = property(get_IsServicesRepair, set_IsServicesRepair)
    def get_IsCreature(self):
        return (self.creatureType == 0)
    def set_IsCreature(self, nValue):
        if (nValue == True): self.creatureType = 0
        elif(self.get_IsCreature()): self.IsDaedra = True
    IsCreature = property(get_IsCreature, set_IsCreature)
    def get_IsDaedra(self):
        return (self.creatureType == 1)
    def set_IsDaedra(self, nValue):
        if (nValue == True): self.creatureType = 1
        elif(self.get_IsDaedra()): self.IsCreature = True
    IsDaedra = property(get_IsDaedra, set_IsDaedra)
    def get_IsUndead(self):
        return (self.creatureType == 2)
    def set_IsUndead(self, nValue):
        if (nValue == True): self.creatureType = 2
        elif(self.get_IsUndead()): self.IsCreature = True
    IsUndead = property(get_IsUndead, set_IsUndead)
    def get_IsHumanoid(self):
        return (self.creatureType == 3)
    def set_IsHumanoid(self, nValue):
        if (nValue == True): self.creatureType = 3
        elif(self.get_IsHumanoid()): self.IsCreature = True
    IsHumanoid = property(get_IsHumanoid, set_IsHumanoid)
    def get_IsHorse(self):
        return (self.creatureType == 4)
    def set_IsHorse(self, nValue):
        if (nValue == True): self.creatureType = 4
        elif(self.get_IsHorse()): self.IsCreature = True
    IsHorse = property(get_IsHorse, set_IsHorse)
    def get_IsGiant(self):
        return (self.creatureType == 5)
    def set_IsGiant(self, nValue):
        if (nValue == True): self.creatureType = 5
        elif(self.get_IsGiant()): self.IsCreature = True
    IsGiant = property(get_IsGiant, set_IsGiant)
    def get_IsNoSoul(self):
        return (self.soul == 0)
    def set_IsNoSoul(self, nValue):
        if (nValue == True): self.soul = 0
        elif(self.get_IsNoSoul()): self.IsPettySoul = True
    IsNoSoul = property(get_IsNoSoul, set_IsNoSoul)
    def get_IsPettySoul(self):
        return (self.soul == 1)
    def set_IsPettySoul(self, nValue):
        if (nValue == True): self.soul = 1
        elif(self.get_IsPettySoul()): self.IsNoSoul = True
    IsPettySoul = property(get_IsPettySoul, set_IsPettySoul)
    def get_IsLesserSoul(self):
        return (self.soul == 2)
    def set_IsLesserSoul(self, nValue):
        if (nValue == True): self.soul = 2
        elif(self.get_IsLesserSoul()): self.IsNoSoul = True
    IsLesserSoul = property(get_IsLesserSoul, set_IsLesserSoul)
    def get_IsCommonSoul(self):
        return (self.soul == 3)
    def set_IsCommonSoul(self, nValue):
        if (nValue == True): self.soul = 3
        elif(self.get_IsCommonSoul()): self.IsNoSoul = True
    IsCommonSoul = property(get_IsCommonSoul, set_IsCommonSoul)
    def get_IsGreaterSoul(self):
        return (self.soul == 4)
    def set_IsGreaterSoul(self, nValue):
        if (nValue == True): self.soul = 4
        elif(self.get_IsGreaterSoul()): self.IsNoSoul = True
    IsGreaterSoul = property(get_IsGreaterSoul, set_IsGreaterSoul)
    def get_IsGrandSoul(self):
        return (self.soul == 5)
    def set_IsGrandSoul(self, nValue):
        if (nValue == True): self.soul = 5
        elif(self.get_IsGrandSoul()): self.IsNoSoul = True
    IsGrandSoul = property(get_IsGrandSoul, set_IsGrandSoul)

class LVLRecord(BaseRecord):
    def CopyAsOverride(self, targetMod):
        FID = CBash.CopyLVLRecord(self._CollectionIndex, self._ModName, self._recordID, targetMod._ModName, c_bool(True))
        if(FID): return LVLRecord(self._CollectionIndex, targetMod._ModName, FID)
        return None
    def CopyAsNew(self, targetMod):
        FID = CBash.CopyLVLRecord(self._CollectionIndex, self._ModName, self._recordID, targetMod._ModName, c_bool(False))
        if(FID): return LVLRecord(self._CollectionIndex, targetMod._ModName, FID)
        return None
    class Entry(object):
        def __init__(self, CollectionIndex, ModName, recordID, subField, listIndex):
            self._CollectionIndex = CollectionIndex
            self._ModName = ModName
            self._recordID = recordID
            self._subField = subField
            self._listIndex = listIndex
        def get_level(self):
            CBash.ReadFIDListField.restype = POINTER(c_short)
            retValue = CBash.ReadFIDListField(self._CollectionIndex, self._ModName, self._recordID, self._subField, self._listIndex, 1)
            if(retValue): return retValue.contents.value
            return None
        def set_level(self, nValue):
            CBash.SetFIDListFieldS(self._CollectionIndex, self._ModName, self._recordID, self._subField, self._listIndex, 1, c_short(nValue))
        level = property(get_level, set_level)
        def get_unused1(self):
            numRecords = CBash.GetFIDListArraySize(self._CollectionIndex, self._ModName, self._recordID, self._subField, self._listIndex, 2)
            if(numRecords > 0):
                cRecords = POINTER(c_ubyte * numRecords)()
                CBash.GetFIDListArray(self._CollectionIndex, self._ModName, self._recordID, self._subField, self._listIndex, 2, byref(cRecords))
                return [cRecords.contents[x] for x in range(0, numRecords)]
            return []
        def set_unused1(self, nValue):
            CBash.SetFIDListFieldR(self._CollectionIndex, self._ModName, self._recordID, self._subField, self._listIndex, 2, struct.pack('2B', *nValue), 2)
        unused1 = property(get_unused1, set_unused1)
        def get_listId(self):
            CBash.ReadFIDListField.restype = POINTER(c_uint)
            retValue = CBash.ReadFIDListField(self._CollectionIndex, self._ModName, self._recordID, self._subField, self._listIndex, 3)
            if(retValue): return retValue.contents.value
            return None
        def set_listId(self, nValue):
            CBash.SetFIDListFieldUI(self._CollectionIndex, self._ModName, self._recordID, self._subField, self._listIndex, 3, nValue)
        listId = property(get_listId, set_listId)
        def get_count(self):
            CBash.ReadFIDListField.restype = POINTER(c_short)
            retValue = CBash.ReadFIDListField(self._CollectionIndex, self._ModName, self._recordID, self._subField, self._listIndex, 4)
            if(retValue): return retValue.contents.value
            return None
        def set_count(self, nValue):
            CBash.SetFIDListFieldS(self._CollectionIndex, self._ModName, self._recordID, self._subField, self._listIndex, 4, c_short(nValue))
        count = property(get_count, set_count)
        def get_unused2(self):
            numRecords = CBash.GetFIDListArraySize(self._CollectionIndex, self._ModName, self._recordID, self._subField, self._listIndex, 5)
            if(numRecords > 0):
                cRecords = POINTER(c_ubyte * numRecords)()
                CBash.GetFIDListArray(self._CollectionIndex, self._ModName, self._recordID, self._subField, self._listIndex, 5, byref(cRecords))
                return [cRecords.contents[x] for x in range(0, numRecords)]
            return []
        def set_unused2(self, nValue):
            CBash.SetFIDListFieldR(self._CollectionIndex, self._ModName, self._recordID, self._subField, self._listIndex, 5, struct.pack('2B', *nValue), 2)
        unused2 = property(get_unused2, set_unused2)
    def newEntriesElement(self):
        listIndex = CBash.CreateFIDListElement(self._CollectionIndex, self._ModName, self._recordID, 10)
        if(listIndex == -1): return None
        return self.Entry(self._CollectionIndex, self._ModName, self._recordID, 10, listIndex)
    def get_chanceNone(self):
        CBash.ReadFIDField.restype = POINTER(c_ubyte)
        retValue = CBash.ReadFIDField(self._CollectionIndex, self._ModName, self._recordID, 6)
        if(retValue): return retValue.contents.value
        return None
    def set_chanceNone(self, nValue):
        CBash.SetFIDFieldUC(self._CollectionIndex, self._ModName, self._recordID, 6, c_ubyte(nValue))
    chanceNone = property(get_chanceNone, set_chanceNone)
    def get_flags(self):
        CBash.ReadFIDField.restype = POINTER(c_ubyte)
        retValue = CBash.ReadFIDField(self._CollectionIndex, self._ModName, self._recordID, 7)
        if(retValue): return retValue.contents.value
        return None
    def set_flags(self, nValue):
        CBash.SetFIDFieldUC(self._CollectionIndex, self._ModName, self._recordID, 7, c_ubyte(nValue))
    flags = property(get_flags, set_flags)
    def get_entries(self):
        numRecords = CBash.GetFIDListSize(self._CollectionIndex, self._ModName, self._recordID, 10)
        if(numRecords > 0): return [self.Entry(self._CollectionIndex, self._ModName, self._recordID, 10, x) for x in range(0, numRecords)]
        return []
    def set_entries(self, nEntries):
        diffLength = len(nEntries) - CBash.GetFIDListSize(self._CollectionIndex, self._ModName, self._recordID, 10)
        nValues = [(nEntry.level, nEntry.unused1, nEntry.listId, nEntry.count, nEntry.unused2) for nEntry in nEntries]
        while(diffLength < 0):
            CBash.DeleteFIDListElement(self._CollectionIndex, self._ModName, self._recordID, 10)
            diffLength += 1
        while(diffLength > 0):
            CBash.CreateFIDListElement(self._CollectionIndex, self._ModName, self._recordID, 10)
            diffLength -= 1
        for oEntry, nValue in zip(self.entries, nValues):
            oEntry.level, oEntry.unused1, oEntry.listId, oEntry.count, oEntry.unused2 = nValue
    entries = property(get_entries, set_entries)
    def get_IsCalcFromAllLevels(self):
        return (self.flags & 0x00000001) != 0 or (chanceNone & 0x00000080) != 0
    def set_IsCalcFromAllLevels(self, nValue):
        if (nValue == True):
            chanceNone &= ~0x00000080
            flags |= 0x00000001
        else:
            chanceNone &= ~0x00000080
            flags &= ~0x00000001
    IsCalcFromAllLevels = property(get_IsCalcFromAllLevels, set_IsCalcFromAllLevels)
    def get_IsCalcForEachItem(self):
        return (self.flags & 0x00000002) != 0
    def set_IsCalcForEachItem(self, nValue):
        if (nValue == True): self.flags |= 0x00000002
        else: self.flags &= ~0x00000002
    IsCalcForEachItem = property(get_IsCalcForEachItem, set_IsCalcForEachItem)
    def get_IsUseAllSpells(self):
        return (self.flags & 0x00000004) != 0
    def set_IsUseAllSpells(self, nValue):
        if (nValue == True): self.flags |= 0x00000004
        else: self.flags &= ~0x00000004
    IsUseAllSpells = property(get_IsUseAllSpells, set_IsUseAllSpells)

class LVLCRecord(LVLRecord):
    def CopyAsOverride(self, targetMod):
        FID = CBash.CopyLVLCRecord(self._CollectionIndex, self._ModName, self._recordID, targetMod._ModName, c_bool(True))
        if(FID): return LVLCRecord(self._CollectionIndex, targetMod._ModName, FID)
        return None
    def CopyAsNew(self, targetMod):
        FID = CBash.CopyLVLCRecord(self._CollectionIndex, self._ModName, self._recordID, targetMod._ModName, c_bool(False))
        if(FID): return LVLCRecord(self._CollectionIndex, targetMod._ModName, FID)
        return None
    def get_script(self):
        CBash.ReadFIDField.restype = POINTER(c_uint)
        retValue = CBash.ReadFIDField(self._CollectionIndex, self._ModName, self._recordID, 8)
        if(retValue): return retValue.contents.value
        return None
    def set_script(self, nValue):
        CBash.SetFIDFieldUI(self._CollectionIndex, self._ModName, self._recordID, 8, nValue)
    script = property(get_script, set_script)
    def get_template(self):
        CBash.ReadFIDField.restype = POINTER(c_uint)
        retValue = CBash.ReadFIDField(self._CollectionIndex, self._ModName, self._recordID, 9)
        if(retValue): return retValue.contents.value
        return None
    def set_template(self, nValue):
        CBash.SetFIDFieldUI(self._CollectionIndex, self._ModName, self._recordID, 9, nValue)
    template = property(get_template, set_template)
class SLGMRecord(BaseRecord):
    def CopyAsOverride(self, targetMod):
        FID = CBash.CopySLGMRecord(self._CollectionIndex, self._ModName, self._recordID, targetMod._ModName, c_bool(True))
        if(FID): return SLGMRecord(self._CollectionIndex, targetMod._ModName, FID)
        return None
    def CopyAsNew(self, targetMod):
        FID = CBash.CopySLGMRecord(self._CollectionIndex, self._ModName, self._recordID, targetMod._ModName, c_bool(False))
        if(FID): return SLGMRecord(self._CollectionIndex, targetMod._ModName, FID)
        return None
    def get_full(self):
        CBash.ReadFIDField.restype = c_char_p
        return CBash.ReadFIDField(self._CollectionIndex, self._ModName, self._recordID, 6)
    def set_full(self, nValue):
        CBash.SetFIDFieldStr(self._CollectionIndex, self._ModName, self._recordID, 6, nValue)
    full = property(get_full, set_full)
    def get_modPath(self):
        CBash.ReadFIDField.restype = c_char_p
        return CBash.ReadFIDField(self._CollectionIndex, self._ModName, self._recordID, 7)
    def set_modPath(self, nValue):
        CBash.SetFIDFieldStr(self._CollectionIndex, self._ModName, self._recordID, 7, nValue)
    modPath = property(get_modPath, set_modPath)
    def get_modb(self):
        CBash.ReadFIDField.restype = POINTER(c_float)
        retValue = CBash.ReadFIDField(self._CollectionIndex, self._ModName, self._recordID, 8)
        if(retValue): return retValue.contents.value
        return None
    def set_modb(self, nValue):
        CBash.SetFIDFieldF(self._CollectionIndex, self._ModName, self._recordID, 8, c_float(nValue))
    modb = property(get_modb, set_modb)
    def get_modt_p(self):
        numRecords = CBash.GetFIDFieldArraySize(self._CollectionIndex, self._ModName, self._recordID, 9)
        if(numRecords > 0):
            cRecords = POINTER(c_ubyte * numRecords)()
            CBash.GetFIDFieldArray(self._CollectionIndex, self._ModName, self._recordID, 9, byref(cRecords))
            return [cRecords.contents[x] for x in range(0, numRecords)]
        return []
    def set_modt_p(self, nValue):
        length = len(nValue)
        CBash.SetFIDFieldR(self._CollectionIndex, self._ModName, self._recordID, 9, struct.pack('B' * length, *nValue), length)
    modt_p = property(get_modt_p, set_modt_p)
    def get_iconPath(self):
        CBash.ReadFIDField.restype = c_char_p
        return CBash.ReadFIDField(self._CollectionIndex, self._ModName, self._recordID, 10)
    def set_iconPath(self, nValue):
        CBash.SetFIDFieldStr(self._CollectionIndex, self._ModName, self._recordID, 10, nValue)
    iconPath = property(get_iconPath, set_iconPath)
    def get_script(self):
        CBash.ReadFIDField.restype = POINTER(c_uint)
        retValue = CBash.ReadFIDField(self._CollectionIndex, self._ModName, self._recordID, 11)
        if(retValue): return retValue.contents.value
        return None
    def set_script(self, nValue):
        CBash.SetFIDFieldUI(self._CollectionIndex, self._ModName, self._recordID, 11, c_uint(nValue))
    script = property(get_script, set_script)
    def get_value(self):
        CBash.ReadFIDField.restype = POINTER(c_uint)
        retValue = CBash.ReadFIDField(self._CollectionIndex, self._ModName, self._recordID, 12)
        if(retValue): return retValue.contents.value
        return None
    def set_value(self, nValue):
        CBash.SetFIDFieldUI(self._CollectionIndex, self._ModName, self._recordID, 12, c_uint(nValue))
    value = property(get_value, set_value)
    def get_weight(self):
        CBash.ReadFIDField.restype = POINTER(c_float)
        retValue = CBash.ReadFIDField(self._CollectionIndex, self._ModName, self._recordID, 13)
        if(retValue): return retValue.contents.value
        return None
    def set_weight(self, nValue):
        CBash.SetFIDFieldF(self._CollectionIndex, self._ModName, self._recordID, 13, c_float(nValue))
    weight = property(get_weight, set_weight)
    def get_soul(self):
        CBash.ReadFIDField.restype = POINTER(c_ubyte)
        retValue = CBash.ReadFIDField(self._CollectionIndex, self._ModName, self._recordID, 14)
        if(retValue): return retValue.contents.value
        return None
    def set_soul(self, nValue):
        CBash.SetFIDFieldUC(self._CollectionIndex, self._ModName, self._recordID, 14, c_ubyte(nValue))
    soul = property(get_soul, set_soul)
    def get_capacity(self):
        CBash.ReadFIDField.restype = POINTER(c_ubyte)
        retValue = CBash.ReadFIDField(self._CollectionIndex, self._ModName, self._recordID, 15)
        if(retValue): return retValue.contents.value
        return None
    def set_capacity(self, nValue):
        CBash.SetFIDFieldUC(self._CollectionIndex, self._ModName, self._recordID, 15, c_ubyte(nValue))
    capacity = property(get_capacity, set_capacity)
    def get_IsNoSoul(self):
        return (self.soul == 0)
    def set_IsNoSoul(self, nValue):
        if (nValue == True): self.soul = 0
        elif(self.get_IsNoSoul()): self.IsPettySoul = True
    IsNoSoul = property(get_IsNoSoul, set_IsNoSoul)
    def get_IsPettySoul(self):
        return (self.soul == 1)
    def set_IsPettySoul(self, nValue):
        if (nValue == True): self.soul = 1
        elif(self.get_IsPettySoul()): self.IsNoSoul = True
    IsPettySoul = property(get_IsPettySoul, set_IsPettySoul)
    def get_IsLesserSoul(self):
        return (self.soul == 2)
    def set_IsLesserSoul(self, nValue):
        if (nValue == True): self.soul = 2
        elif(self.get_IsLesserSoul()): self.IsNoSoul = True
    IsLesserSoul = property(get_IsLesserSoul, set_IsLesserSoul)
    def get_IsCommonSoul(self):
        return (self.soul == 3)
    def set_IsCommonSoul(self, nValue):
        if (nValue == True): self.soul = 3
        elif(self.get_IsCommonSoul()): self.IsNoSoul = True
    IsCommonSoul = property(get_IsCommonSoul, set_IsCommonSoul)
    def get_IsGreaterSoul(self):
        return (self.soul == 4)
    def set_IsGreaterSoul(self, nValue):
        if (nValue == True): self.soul = 4
        elif(self.get_IsGreaterSoul()): self.IsNoSoul = True
    IsGreaterSoul = property(get_IsGreaterSoul, set_IsGreaterSoul)
    def get_IsGrandSoul(self):
        return (self.soul == 5)
    def set_IsGrandSoul(self, nValue):
        if (nValue == True): self.soul = 5
        elif(self.get_IsGrandSoul()): self.IsNoSoul = True
    IsGrandSoul = property(get_IsGrandSoul, set_IsGrandSoul)
    def get_IsNoCapacity(self):
        return (self.capacity == 0)
    def set_IsNoCapacity(self, nValue):
        if (nValue == True): self.capacity = 0
        elif(self.get_IsNoCapacity()): self.IsPettyCapacity = True
    IsNoCapacity = property(get_IsNoCapacity, set_IsNoCapacity)
    def get_IsPettyCapacity(self):
        return (self.capacity == 1)
    def set_IsPettyCapacity(self, nValue):
        if (nValue == True): self.capacity = 1
        elif(self.get_IsPettyCapacity()): self.IsNoCapacity = True
    IsPettyCapacity = property(get_IsPettyCapacity, set_IsPettyCapacity)
    def get_IsLesserCapacity(self):
        return (self.capacity == 2)
    def set_IsLesserCapacity(self, nValue):
        if (nValue == True): self.capacity = 2
        elif(self.get_IsLesserCapacity()): self.IsNoCapacity = True
    IsLesserCapacity = property(get_IsLesserCapacity, set_IsLesserCapacity)
    def get_IsCommonCapacity(self):
        return (self.capacity == 3)
    def set_IsCommonCapacity(self, nValue):
        if (nValue == True): self.capacity = 3
        elif(self.get_IsCommonCapacity()): self.IsNoCapacity = True
    IsCommonCapacity = property(get_IsCommonCapacity, set_IsCommonCapacity)
    def get_IsGreaterCapacity(self):
        return (self.capacity == 4)
    def set_IsGreaterCapacity(self, nValue):
        if (nValue == True): self.capacity = 4
        elif(self.get_IsGreaterCapacity()): self.IsNoCapacity = True
    IsGreaterCapacity = property(get_IsGreaterCapacity, set_IsGreaterCapacity)
    def get_IsGrandCapacity(self):
        return (self.capacity == 5)
    def set_IsGrandCapacity(self, nValue):
        if (nValue == True): self.capacity = 5
        elif(self.get_IsGrandCapacity()): self.IsNoCapacity = True
    IsGrandCapacity = property(get_IsGrandCapacity, set_IsGrandCapacity)
    
class KEYMRecord(BaseRecord):
    def CopyAsOverride(self, targetMod):
        FID = CBash.CopyKEYMRecord(self._CollectionIndex, self._ModName, self._recordID, targetMod._ModName, c_bool(True))
        if(FID): return KEYMRecord(self._CollectionIndex, targetMod._ModName, FID)
        return None
    def CopyAsNew(self, targetMod):
        FID = CBash.CopyKEYMRecord(self._CollectionIndex, self._ModName, self._recordID, targetMod._ModName, c_bool(False))
        if(FID): return KEYMRecord(self._CollectionIndex, targetMod._ModName, FID)
        return None
    def get_full(self):
        CBash.ReadFIDField.restype = c_char_p
        return CBash.ReadFIDField(self._CollectionIndex, self._ModName, self._recordID, 6)
    def set_full(self, nValue):
        CBash.SetFIDFieldStr(self._CollectionIndex, self._ModName, self._recordID, 6, nValue)
    full = property(get_full, set_full)
    def get_modPath(self):
        CBash.ReadFIDField.restype = c_char_p
        return CBash.ReadFIDField(self._CollectionIndex, self._ModName, self._recordID, 7)
    def set_modPath(self, nValue):
        CBash.SetFIDFieldStr(self._CollectionIndex, self._ModName, self._recordID, 7, nValue)
    modPath = property(get_modPath, set_modPath)
    def get_modb(self):
        CBash.ReadFIDField.restype = POINTER(c_float)
        retValue = CBash.ReadFIDField(self._CollectionIndex, self._ModName, self._recordID, 8)
        if(retValue): return retValue.contents.value
        return None
    def set_modb(self, nValue):
        CBash.SetFIDFieldF(self._CollectionIndex, self._ModName, self._recordID, 8, c_float(nValue))
    modb = property(get_modb, set_modb)
    def get_modt_p(self):
        numRecords = CBash.GetFIDFieldArraySize(self._CollectionIndex, self._ModName, self._recordID, 9)
        if(numRecords > 0):
            cRecords = POINTER(c_ubyte * numRecords)()
            CBash.GetFIDFieldArray(self._CollectionIndex, self._ModName, self._recordID, 9, byref(cRecords))
            return [cRecords.contents[x] for x in range(0, numRecords)]
        return []
    def set_modt_p(self, nValue):
        length = len(nValue)
        CBash.SetFIDFieldR(self._CollectionIndex, self._ModName, self._recordID, 9, struct.pack('B' * length, *nValue), length)
    modt_p = property(get_modt_p, set_modt_p)
    def get_iconPath(self):
        CBash.ReadFIDField.restype = c_char_p
        return CBash.ReadFIDField(self._CollectionIndex, self._ModName, self._recordID, 10)
    def set_iconPath(self, nValue):
        CBash.SetFIDFieldStr(self._CollectionIndex, self._ModName, self._recordID, 10, nValue)
    iconPath = property(get_iconPath, set_iconPath)
    def get_script(self):
        CBash.ReadFIDField.restype = POINTER(c_uint)
        retValue = CBash.ReadFIDField(self._CollectionIndex, self._ModName, self._recordID, 11)
        if(retValue): return retValue.contents.value
        return None
    def set_script(self, nValue):
        CBash.SetFIDFieldUI(self._CollectionIndex, self._ModName, self._recordID, 11, c_uint(nValue))
    script = property(get_script, set_script)
    def get_value(self):
        CBash.ReadFIDField.restype = POINTER(c_uint)
        retValue = CBash.ReadFIDField(self._CollectionIndex, self._ModName, self._recordID, 12)
        if(retValue): return retValue.contents.value
        return None
    def set_value(self, nValue):
        CBash.SetFIDFieldUI(self._CollectionIndex, self._ModName, self._recordID, 12, c_uint(nValue))
    value = property(get_value, set_value)
    def get_weight(self):
        CBash.ReadFIDField.restype = POINTER(c_float)
        retValue = CBash.ReadFIDField(self._CollectionIndex, self._ModName, self._recordID, 13)
        if(retValue): return retValue.contents.value
        return None
    def set_weight(self, nValue):
        CBash.SetFIDFieldF(self._CollectionIndex, self._ModName, self._recordID, 13, c_float(nValue))
    weight = property(get_weight, set_weight)
class ALCHRecord(BaseRecord):
    def CopyAsOverride(self, targetMod):
        FID = CBash.CopyALCHRecord(self._CollectionIndex, self._ModName, self._recordID, targetMod._ModName, c_bool(True))
        if(FID): return ALCHRecord(self._CollectionIndex, targetMod._ModName, FID)
        return None
    def CopyAsNew(self, targetMod):
        FID = CBash.CopyALCHRecord(self._CollectionIndex, self._ModName, self._recordID, targetMod._ModName, c_bool(False))
        if(FID): return ALCHRecord(self._CollectionIndex, targetMod._ModName, FID)
        return None
    class Effect(object):
        def __init__(self, CollectionIndex, ModName, recordID, subField, listIndex):
            self._CollectionIndex = CollectionIndex
            self._ModName = ModName
            self._recordID = recordID
            self._subField = subField
            self._listIndex = listIndex
        ##name0 and name are both are always the same value, so setting one will set both. They're basically aliases
        def get_name0(self):
            CBash.ReadFIDListField.restype = POINTER(c_uint)
            retValue = CBash.ReadFIDListField(self._CollectionIndex, self._ModName, self._recordID, self._subField, self._listIndex, 1)
            if(retValue): return retValue.contents.value
            return None
        def set_name0(self, nValue):
            CBash.SetFIDListFieldUI(self._CollectionIndex, self._ModName, self._recordID, self._subField, self._listIndex, 1, nValue)
        name0 = property(get_name0, set_name0)
        def get_name(self):
            CBash.ReadFIDListField.restype = POINTER(c_uint)
            retValue = CBash.ReadFIDListField(self._CollectionIndex, self._ModName, self._recordID, self._subField, self._listIndex, 2)
            if(retValue): return retValue.contents.value
            return None
        def set_name(self, nValue):
            CBash.SetFIDListFieldUI(self._CollectionIndex, self._ModName, self._recordID, self._subField, self._listIndex, 2, nValue)
        name = property(get_name, set_name)
        def get_magnitude(self):
            CBash.ReadFIDListField.restype = POINTER(c_uint)
            retValue = CBash.ReadFIDListField(self._CollectionIndex, self._ModName, self._recordID, self._subField, self._listIndex, 3)
            if(retValue): return retValue.contents.value
            return None
        def set_magnitude(self, nValue):
            CBash.SetFIDListFieldUI(self._CollectionIndex, self._ModName, self._recordID, self._subField, self._listIndex, 3, nValue)
        magnitude = property(get_magnitude, set_magnitude)
        def get_area(self):
            CBash.ReadFIDListField.restype = POINTER(c_uint)
            retValue = CBash.ReadFIDListField(self._CollectionIndex, self._ModName, self._recordID, self._subField, self._listIndex, 4)
            if(retValue): return retValue.contents.value
            return None
        def set_area(self, nValue):
            CBash.SetFIDListFieldUI(self._CollectionIndex, self._ModName, self._recordID, self._subField, self._listIndex, 4, nValue)
        area = property(get_area, set_area)
        def get_duration(self):
            CBash.ReadFIDListField.restype = POINTER(c_uint)
            retValue = CBash.ReadFIDListField(self._CollectionIndex, self._ModName, self._recordID, self._subField, self._listIndex, 5)
            if(retValue): return retValue.contents.value
            return None
        def set_duration(self, nValue):
            CBash.SetFIDListFieldUI(self._CollectionIndex, self._ModName, self._recordID, self._subField, self._listIndex, 5, nValue)
        duration = property(get_duration, set_duration)
        def get_recipient(self):
            CBash.ReadFIDListField.restype = POINTER(c_uint)
            retValue = CBash.ReadFIDListField(self._CollectionIndex, self._ModName, self._recordID, self._subField, self._listIndex, 6)
            if(retValue): return retValue.contents.value
            return None
        def set_recipient(self, nValue):
            CBash.SetFIDListFieldUI(self._CollectionIndex, self._ModName, self._recordID, self._subField, self._listIndex, 6, nValue)
        recipient = property(get_recipient, set_recipient)
        def get_actorValue(self):
            CBash.ReadFIDListField.restype = POINTER(c_int)
            retValue = CBash.ReadFIDListField(self._CollectionIndex, self._ModName, self._recordID, self._subField, self._listIndex, 7)
            if(retValue): return retValue.contents.value
            return None
        def set_actorValue(self, nValue):
            CBash.SetFIDListFieldI(self._CollectionIndex, self._ModName, self._recordID, self._subField, self._listIndex, 7, nValue)
        actorValue = property(get_actorValue, set_actorValue)
        def get_script(self):
            CBash.ReadFIDListField.restype = POINTER(c_uint)
            retValue = CBash.ReadFIDListField(self._CollectionIndex, self._ModName, self._recordID, self._subField, self._listIndex, 8)
            if(retValue): return retValue.contents.value
            return None
        def set_script(self, nValue):
            CBash.SetFIDListFieldUI(self._CollectionIndex, self._ModName, self._recordID, self._subField, self._listIndex, 8, nValue)
        script = property(get_script, set_script)
        def get_school(self):
            CBash.ReadFIDListField.restype = POINTER(c_uint)
            retValue = CBash.ReadFIDListField(self._CollectionIndex, self._ModName, self._recordID, self._subField, self._listIndex, 9)
            if(retValue): return retValue.contents.value
            return None
        def set_school(self, nValue):
            CBash.SetFIDListFieldUI(self._CollectionIndex, self._ModName, self._recordID, self._subField, self._listIndex, 9, nValue)
        school = property(get_school, set_school)
        def get_visual(self):
            CBash.ReadFIDListField.restype = POINTER(c_uint)
            retValue = CBash.ReadFIDListField(self._CollectionIndex, self._ModName, self._recordID, self._subField, self._listIndex, 10)
            if(retValue): return retValue.contents.value
            return None
        def set_visual(self, nValue):
            CBash.SetFIDListFieldUI(self._CollectionIndex, self._ModName, self._recordID, self._subField, self._listIndex, 10, nValue)
        visual = property(get_visual, set_visual)
        def get_flags(self):
            CBash.ReadFIDListField.restype = POINTER(c_ubyte)
            retValue = CBash.ReadFIDListField(self._CollectionIndex, self._ModName, self._recordID, self._subField, self._listIndex, 11)
            if(retValue): return retValue.contents.value
            return None
        def set_flags(self, nValue):
            CBash.SetFIDListFieldUC(self._CollectionIndex, self._ModName, self._recordID, self._subField, self._listIndex, 11, c_ubyte(nValue))
        flags = property(get_flags, set_flags)
        def get_unused1(self):
            numRecords = CBash.GetFIDListArraySize(self._CollectionIndex, self._ModName, self._recordID, self._subField, self._listIndex, 12)
            if(numRecords > 0):
                cRecords = POINTER(c_ubyte * numRecords)()
                CBash.GetFIDListArray(self._CollectionIndex, self._ModName, self._recordID, self._subField, self._listIndex, 12, byref(cRecords))
                return [cRecords.contents[x] for x in range(0, numRecords)]
            return []
        def set_unused1(self, nValue):
            CBash.SetFIDListFieldR(self._CollectionIndex, self._ModName, self._recordID, self._subField, self._listIndex, 12, struct.pack('3B', *nValue), 3)
        unused1 = property(get_unused1, set_unused1)
        def get_full(self):
            CBash.ReadFIDListField.restype = c_char_p
            return CBash.ReadFIDListField(self._CollectionIndex, self._ModName, self._recordID, self._subField, self._listIndex, 13)
        def set_full(self, nValue):
            CBash.SetFIDListFieldStr(self._CollectionIndex, self._ModName, self._recordID, self._subField, self._listIndex, 13, nValue)
        full = property(get_full, set_full)
        def get_IsHostile(self):
            return (self.flags & 0x00000001) != 0
        def set_IsHostile(self, nValue):
            if (nValue == True): self.flags |= 0x00000001
            else: self.flags &= ~0x00000001
        IsHostile = property(get_IsHostile, set_IsHostile)
    def newEffectsElement(self):
        listIndex = CBash.CreateFIDListElement(self._CollectionIndex, self._ModName, self._recordID, 16)
        if(listIndex == -1): return None
        return self.Effect(self._CollectionIndex, self._ModName, self._recordID, 16, listIndex)
    def get_full(self):
        CBash.ReadFIDField.restype = c_char_p
        return CBash.ReadFIDField(self._CollectionIndex, self._ModName, self._recordID, 6)
    def set_full(self, nValue):
        CBash.SetFIDFieldStr(self._CollectionIndex, self._ModName, self._recordID, 6, nValue)
    full = property(get_full, set_full)
    def get_modPath(self):
        CBash.ReadFIDField.restype = c_char_p
        return CBash.ReadFIDField(self._CollectionIndex, self._ModName, self._recordID, 7)
    def set_modPath(self, nValue):
        CBash.SetFIDFieldStr(self._CollectionIndex, self._ModName, self._recordID, 7, nValue)
    modPath = property(get_modPath, set_modPath)
    def get_modb(self):
        CBash.ReadFIDField.restype = POINTER(c_float)
        retValue = CBash.ReadFIDField(self._CollectionIndex, self._ModName, self._recordID, 8)
        if(retValue): return retValue.contents.value
        return None
    def set_modb(self, nValue):
        CBash.SetFIDFieldF(self._CollectionIndex, self._ModName, self._recordID, 8, c_float(nValue))
    modb = property(get_modb, set_modb)
    def get_modt_p(self):
        numRecords = CBash.GetFIDFieldArraySize(self._CollectionIndex, self._ModName, self._recordID, 9)
        if(numRecords > 0):
            cRecords = POINTER(c_ubyte * numRecords)()
            CBash.GetFIDFieldArray(self._CollectionIndex, self._ModName, self._recordID, 9, byref(cRecords))
            return [cRecords.contents[x] for x in range(0, numRecords)]
        return []
    def set_modt_p(self, nValue):
        length = len(nValue)
        CBash.SetFIDFieldR(self._CollectionIndex, self._ModName, self._recordID, 9, struct.pack('B' * length, *nValue), length)
    modt_p = property(get_modt_p, set_modt_p)
    def get_iconPath(self):
        CBash.ReadFIDField.restype = c_char_p
        return CBash.ReadFIDField(self._CollectionIndex, self._ModName, self._recordID, 10)
    def set_iconPath(self, nValue):
        CBash.SetFIDFieldStr(self._CollectionIndex, self._ModName, self._recordID, 10, nValue)
    iconPath = property(get_iconPath, set_iconPath)
    def get_script(self):
        CBash.ReadFIDField.restype = POINTER(c_uint)
        retValue = CBash.ReadFIDField(self._CollectionIndex, self._ModName, self._recordID, 11)
        if(retValue): return retValue.contents.value
        return None
    def set_script(self, nValue):
        CBash.SetFIDFieldUI(self._CollectionIndex, self._ModName, self._recordID, 11, c_uint(nValue))
    script = property(get_script, set_script)
    def get_weight(self):
        CBash.ReadFIDField.restype = POINTER(c_float)
        retValue = CBash.ReadFIDField(self._CollectionIndex, self._ModName, self._recordID, 12)
        if(retValue): return retValue.contents.value
        return None
    def set_weight(self, nValue):
        CBash.SetFIDFieldF(self._CollectionIndex, self._ModName, self._recordID, 12, c_float(nValue))
    weight = property(get_weight, set_weight)
    def get_value(self):
        CBash.ReadFIDField.restype = POINTER(c_int)
        retValue = CBash.ReadFIDField(self._CollectionIndex, self._ModName, self._recordID, 13)
        if(retValue): return retValue.contents.value
        return None
    def set_value(self, nValue):
        CBash.SetFIDFieldI(self._CollectionIndex, self._ModName, self._recordID, 13, c_int(nValue))
    value = property(get_value, set_value)
    def get_flags(self):
        CBash.ReadFIDField.restype = POINTER(c_ubyte)
        retValue = CBash.ReadFIDField(self._CollectionIndex, self._ModName, self._recordID, 14)
        if(retValue): return retValue.contents.value
        return None
    def set_flags(self, nValue):
        CBash.SetFIDFieldUC(self._CollectionIndex, self._ModName, self._recordID, 14, c_ubyte(nValue))
    flags = property(get_flags, set_flags)
    def get_unused1(self):
        numRecords = CBash.GetFIDFieldArraySize(self._CollectionIndex, self._ModName, self._recordID, 15)
        if(numRecords > 0):
            cRecords = POINTER(c_ubyte * numRecords)()
            CBash.GetFIDFieldArray(self._CollectionIndex, self._ModName, self._recordID, 15, byref(cRecords))
            return [cRecords.contents[x] for x in range(0, numRecords)]
        return []
    def set_unused1(self, nValue):
        CBash.SetFIDFieldR(self._CollectionIndex, self._ModName, self._recordID, 15, struct.pack('3B', *nValue), 3)
    unused1 = property(get_unused1, set_unused1)
    def get_effects(self):
        numRecords = CBash.GetFIDListSize(self._CollectionIndex, self._ModName, self._recordID, 16)
        if(numRecords > 0): return [self.Effect(self._CollectionIndex, self._ModName, self._recordID, 16, x) for x in range(0, numRecords)]
        return []
    def set_effects(self, nEffects):
        diffLength = len(nEffects) - CBash.GetFIDListSize(self._CollectionIndex, self._ModName, self._recordID, 16)
        nValues = [(nEffect.name0, nEffect.name, nEffect.magnitude, nEffect.area, nEffect.duration, nEffect.recipient, nEffect.actorValue, nEffect.script, nEffect.school, nEffect.visual, nEffect.flags, nEffect.unused1, nEffect.full) for nEffect in nEffects]
        while(diffLength < 0):
            CBash.DeleteFIDListElement(self._CollectionIndex, self._ModName, self._recordID, 16)
            diffLength += 1
        while(diffLength > 0):
            CBash.CreateFIDListElement(self._CollectionIndex, self._ModName, self._recordID, 16)
            diffLength -= 1
        for oEffect, nValue in zip(self.effects, nValues):
            oEffect.name0, oEffect.name, oEffect.magnitude, oEffect.area, oEffect.duration, oEffect.recipient, oEffect.actorValue, oEffect.script, oEffect.school, oEffect.visual, oEffect.flags, oEffect.unused1, oEffect.full = nValue
    effects = property(get_effects, set_effects)
    def get_IsNoAutoCalc(self):
        return (self.flags & 0x00000001) != 0
    def set_IsNoAutoCalc(self, nValue):
        if (nValue == True): self.flags |= 0x00000001
        else: self.flags &= ~0x00000001
    IsNoAutoCalc = property(get_IsNoAutoCalc, set_IsNoAutoCalc)
    def get_IsFood(self):
        return (self.flags & 0x00000002) != 0
    def set_IsFood(self, nValue):
        if (nValue == True): self.flags |= 0x00000002
        else: self.flags &= ~0x00000002
    IsFood = property(get_IsFood, set_IsFood)
    
class SBSPRecord(BaseRecord):
    def CopyAsOverride(self, targetMod):
        FID = CBash.CopySBSPRecord(self._CollectionIndex, self._ModName, self._recordID, targetMod._ModName, c_bool(True))
        if(FID): return SBSPRecord(self._CollectionIndex, targetMod._ModName, FID)
        return None
    def CopyAsNew(self, targetMod):
        FID = CBash.CopySBSPRecord(self._CollectionIndex, self._ModName, self._recordID, targetMod._ModName, c_bool(False))
        if(FID): return SBSPRecord(self._CollectionIndex, targetMod._ModName, FID)
        return None
    def get_sizeX(self):
        CBash.ReadFIDField.restype = POINTER(c_float)
        retValue = CBash.ReadFIDField(self._CollectionIndex, self._ModName, self._recordID, 6)
        if(retValue): return retValue.contents.value
        return None
    def set_sizeX(self, nValue):
        CBash.SetFIDFieldF(self._CollectionIndex, self._ModName, self._recordID, 6, c_float(nValue))
    sizeX = property(get_sizeX, set_sizeX)
    def get_sizeY(self):
        CBash.ReadFIDField.restype = POINTER(c_float)
        retValue = CBash.ReadFIDField(self._CollectionIndex, self._ModName, self._recordID, 7)
        if(retValue): return retValue.contents.value
        return None
    def set_sizeY(self, nValue):
        CBash.SetFIDFieldF(self._CollectionIndex, self._ModName, self._recordID, 7, c_float(nValue))
    sizeY = property(get_sizeY, set_sizeY)
    def get_sizeZ(self):
        CBash.ReadFIDField.restype = POINTER(c_float)
        retValue = CBash.ReadFIDField(self._CollectionIndex, self._ModName, self._recordID, 8)
        if(retValue): return retValue.contents.value
        return None
    def set_sizeZ(self, nValue):
        CBash.SetFIDFieldF(self._CollectionIndex, self._ModName, self._recordID, 8, c_float(nValue))
    sizeZ = property(get_sizeZ, set_sizeZ)
class SGSTRecord(BaseRecord):
    def CopyAsOverride(self, targetMod):
        FID = CBash.CopySGSTRecord(self._CollectionIndex, self._ModName, self._recordID, targetMod._ModName, c_bool(True))
        if(FID): return SGSTRecord(self._CollectionIndex, targetMod._ModName, FID)
        return None
    def CopyAsNew(self, targetMod):
        FID = CBash.CopySGSTRecord(self._CollectionIndex, self._ModName, self._recordID, targetMod._ModName, c_bool(False))
        if(FID): return SGSTRecord(self._CollectionIndex, targetMod._ModName, FID)
        return None
    class Effect(object):
        def __init__(self, CollectionIndex, ModName, recordID, subField, listIndex):
            self._CollectionIndex = CollectionIndex
            self._ModName = ModName
            self._recordID = recordID
            self._subField = subField
            self._listIndex = listIndex
        ##name0 and name are both are always the same value, so setting one will set both. They're basically aliases
        def get_name0(self):
            CBash.ReadFIDListField.restype = POINTER(c_uint)
            retValue = CBash.ReadFIDListField(self._CollectionIndex, self._ModName, self._recordID, self._subField, self._listIndex, 1)
            if(retValue): return retValue.contents.value
            return None
        def set_name0(self, nValue):
            CBash.SetFIDListFieldUI(self._CollectionIndex, self._ModName, self._recordID, self._subField, self._listIndex, 1, nValue)
        name0 = property(get_name0, set_name0)
        def get_name(self):
            CBash.ReadFIDListField.restype = POINTER(c_uint)
            retValue = CBash.ReadFIDListField(self._CollectionIndex, self._ModName, self._recordID, self._subField, self._listIndex, 2)
            if(retValue): return retValue.contents.value
            return None
        def set_name(self, nValue):
            CBash.SetFIDListFieldUI(self._CollectionIndex, self._ModName, self._recordID, self._subField, self._listIndex, 2, nValue)
        name = property(get_name, set_name)
        def get_magnitude(self):
            CBash.ReadFIDListField.restype = POINTER(c_uint)
            retValue = CBash.ReadFIDListField(self._CollectionIndex, self._ModName, self._recordID, self._subField, self._listIndex, 3)
            if(retValue): return retValue.contents.value
            return None
        def set_magnitude(self, nValue):
            CBash.SetFIDListFieldUI(self._CollectionIndex, self._ModName, self._recordID, self._subField, self._listIndex, 3, nValue)
        magnitude = property(get_magnitude, set_magnitude)
        def get_area(self):
            CBash.ReadFIDListField.restype = POINTER(c_uint)
            retValue = CBash.ReadFIDListField(self._CollectionIndex, self._ModName, self._recordID, self._subField, self._listIndex, 4)
            if(retValue): return retValue.contents.value
            return None
        def set_area(self, nValue):
            CBash.SetFIDListFieldUI(self._CollectionIndex, self._ModName, self._recordID, self._subField, self._listIndex, 4, nValue)
        area = property(get_area, set_area)
        def get_duration(self):
            CBash.ReadFIDListField.restype = POINTER(c_uint)
            retValue = CBash.ReadFIDListField(self._CollectionIndex, self._ModName, self._recordID, self._subField, self._listIndex, 5)
            if(retValue): return retValue.contents.value
            return None
        def set_duration(self, nValue):
            CBash.SetFIDListFieldUI(self._CollectionIndex, self._ModName, self._recordID, self._subField, self._listIndex, 5, nValue)
        duration = property(get_duration, set_duration)
        def get_recipient(self):
            CBash.ReadFIDListField.restype = POINTER(c_uint)
            retValue = CBash.ReadFIDListField(self._CollectionIndex, self._ModName, self._recordID, self._subField, self._listIndex, 6)
            if(retValue): return retValue.contents.value
            return None
        def set_recipient(self, nValue):
            CBash.SetFIDListFieldUI(self._CollectionIndex, self._ModName, self._recordID, self._subField, self._listIndex, 6, nValue)
        recipient = property(get_recipient, set_recipient)
        def get_actorValue(self):
            CBash.ReadFIDListField.restype = POINTER(c_int)
            retValue = CBash.ReadFIDListField(self._CollectionIndex, self._ModName, self._recordID, self._subField, self._listIndex, 7)
            if(retValue): return retValue.contents.value
            return None
        def set_actorValue(self, nValue):
            CBash.SetFIDListFieldI(self._CollectionIndex, self._ModName, self._recordID, self._subField, self._listIndex, 7, nValue)
        actorValue = property(get_actorValue, set_actorValue)
        def get_script(self):
            CBash.ReadFIDListField.restype = POINTER(c_uint)
            retValue = CBash.ReadFIDListField(self._CollectionIndex, self._ModName, self._recordID, self._subField, self._listIndex, 8)
            if(retValue): return retValue.contents.value
            return None
        def set_script(self, nValue):
            CBash.SetFIDListFieldUI(self._CollectionIndex, self._ModName, self._recordID, self._subField, self._listIndex, 8, nValue)
        script = property(get_script, set_script)
        def get_school(self):
            CBash.ReadFIDListField.restype = POINTER(c_uint)
            retValue = CBash.ReadFIDListField(self._CollectionIndex, self._ModName, self._recordID, self._subField, self._listIndex, 9)
            if(retValue): return retValue.contents.value
            return None
        def set_school(self, nValue):
            CBash.SetFIDListFieldUI(self._CollectionIndex, self._ModName, self._recordID, self._subField, self._listIndex, 9, nValue)
        school = property(get_school, set_school)
        def get_visual(self):
            CBash.ReadFIDListField.restype = POINTER(c_uint)
            retValue = CBash.ReadFIDListField(self._CollectionIndex, self._ModName, self._recordID, self._subField, self._listIndex, 10)
            if(retValue): return retValue.contents.value
            return None
        def set_visual(self, nValue):
            CBash.SetFIDListFieldUI(self._CollectionIndex, self._ModName, self._recordID, self._subField, self._listIndex, 10, nValue)
        visual = property(get_visual, set_visual)
        def get_flags(self):
            CBash.ReadFIDListField.restype = POINTER(c_ubyte)
            retValue = CBash.ReadFIDListField(self._CollectionIndex, self._ModName, self._recordID, self._subField, self._listIndex, 11)
            if(retValue): return retValue.contents.value
            return None
        def set_flags(self, nValue):
            CBash.SetFIDListFieldUC(self._CollectionIndex, self._ModName, self._recordID, self._subField, self._listIndex, 11, c_ubyte(nValue))
        flags = property(get_flags, set_flags)
        def get_unused1(self):
            numRecords = CBash.GetFIDListArraySize(self._CollectionIndex, self._ModName, self._recordID, self._subField, self._listIndex, 12)
            if(numRecords > 0):
                cRecords = POINTER(c_ubyte * numRecords)()
                CBash.GetFIDListArray(self._CollectionIndex, self._ModName, self._recordID, self._subField, self._listIndex, 12, byref(cRecords))
                return [cRecords.contents[x] for x in range(0, numRecords)]
            return []
        def set_unused1(self, nValue):
            CBash.SetFIDListFieldR(self._CollectionIndex, self._ModName, self._recordID, self._subField, self._listIndex, 12, struct.pack('3B', *nValue), 3)
        unused1 = property(get_unused1, set_unused1)
        def get_full(self):
            CBash.ReadFIDListField.restype = c_char_p
            return CBash.ReadFIDListField(self._CollectionIndex, self._ModName, self._recordID, self._subField, self._listIndex, 13)
        def set_full(self, nValue):
            CBash.SetFIDListFieldStr(self._CollectionIndex, self._ModName, self._recordID, self._subField, self._listIndex, 13, nValue)
        full = property(get_full, set_full)
        def get_IsHostile(self):
            return (self.flags & 0x00000001) != 0
        def set_IsHostile(self, nValue):
            if (nValue == True): self.flags |= 0x00000001
            else: self.flags &= ~0x00000001
        IsHostile = property(get_IsHostile, set_IsHostile)
    def newEffectsElement(self):
        listIndex = CBash.CreateFIDListElement(self._CollectionIndex, self._ModName, self._recordID, 12)
        if(listIndex == -1): return None
        return self.Effect(self._CollectionIndex, self._ModName, self._recordID, 12, listIndex)
    def get_full(self):
        CBash.ReadFIDField.restype = c_char_p
        return CBash.ReadFIDField(self._CollectionIndex, self._ModName, self._recordID, 6)
    def set_full(self, nValue):
        CBash.SetFIDFieldStr(self._CollectionIndex, self._ModName, self._recordID, 6, nValue)
    full = property(get_full, set_full)
    def get_modPath(self):
        CBash.ReadFIDField.restype = c_char_p
        return CBash.ReadFIDField(self._CollectionIndex, self._ModName, self._recordID, 7)
    def set_modPath(self, nValue):
        CBash.SetFIDFieldStr(self._CollectionIndex, self._ModName, self._recordID, 7, nValue)
    modPath = property(get_modPath, set_modPath)
    def get_modb(self):
        CBash.ReadFIDField.restype = POINTER(c_float)
        retValue = CBash.ReadFIDField(self._CollectionIndex, self._ModName, self._recordID, 8)
        if(retValue): return retValue.contents.value
        return None
    def set_modb(self, nValue):
        CBash.SetFIDFieldF(self._CollectionIndex, self._ModName, self._recordID, 8, c_float(nValue))
    modb = property(get_modb, set_modb)
    def get_modt_p(self):
        numRecords = CBash.GetFIDFieldArraySize(self._CollectionIndex, self._ModName, self._recordID, 9)
        if(numRecords > 0):
            cRecords = POINTER(c_ubyte * numRecords)()
            CBash.GetFIDFieldArray(self._CollectionIndex, self._ModName, self._recordID, 9, byref(cRecords))
            return [cRecords.contents[x] for x in range(0, numRecords)]
        return []
    def set_modt_p(self, nValue):
        length = len(nValue)
        CBash.SetFIDFieldR(self._CollectionIndex, self._ModName, self._recordID, 9, struct.pack('B' * length, *nValue), length)
    modt_p = property(get_modt_p, set_modt_p)
    def get_iconPath(self):
        CBash.ReadFIDField.restype = c_char_p
        return CBash.ReadFIDField(self._CollectionIndex, self._ModName, self._recordID, 10)
    def set_iconPath(self, nValue):
        CBash.SetFIDFieldStr(self._CollectionIndex, self._ModName, self._recordID, 10, nValue)
    iconPath = property(get_iconPath, set_iconPath)
    def get_script(self):
        CBash.ReadFIDField.restype = POINTER(c_uint)
        retValue = CBash.ReadFIDField(self._CollectionIndex, self._ModName, self._recordID, 11)
        if(retValue): return retValue.contents.value
        return None
    def set_script(self, nValue):
        CBash.SetFIDFieldUI(self._CollectionIndex, self._ModName, self._recordID, 11, c_uint(nValue))
    script = property(get_script, set_script)
    def get_effects(self):
        numRecords = CBash.GetFIDListSize(self._CollectionIndex, self._ModName, self._recordID, 12)
        if(numRecords > 0): return [self.Effect(self._CollectionIndex, self._ModName, self._recordID, 12, x) for x in range(0, numRecords)]
        return []
    def set_effects(self, nEffects):
        diffLength = len(nEffects) - CBash.GetFIDListSize(self._CollectionIndex, self._ModName, self._recordID, 12)
        nValues = [(nEffect.name0, nEffect.name, nEffect.magnitude, nEffect.area, nEffect.duration, nEffect.recipient, nEffect.actorValue, nEffect.script, nEffect.school, nEffect.visual, nEffect.flags, nEffect.unused1, nEffect.full) for nEffect in nEffects]
        while(diffLength < 0):
            CBash.DeleteFIDListElement(self._CollectionIndex, self._ModName, self._recordID, 12)
            diffLength += 1
        while(diffLength > 0):
            CBash.CreateFIDListElement(self._CollectionIndex, self._ModName, self._recordID, 12)
            diffLength -= 1
        for oEffect, nValue in zip(self.effects, nValues):
            oEffect.name0, oEffect.name, oEffect.magnitude, oEffect.area, oEffect.duration, oEffect.recipient, oEffect.actorValue, oEffect.script, oEffect.school, oEffect.visual, oEffect.flags, oEffect.unused1, oEffect.full = nValue
    effects = property(get_effects, set_effects)
    def get_uses(self):
        CBash.ReadFIDField.restype = POINTER(c_ubyte)
        retValue = CBash.ReadFIDField(self._CollectionIndex, self._ModName, self._recordID, 13)
        if(retValue): return retValue.contents.value
        return None
    def set_uses(self, nValue):
        CBash.SetFIDFieldUC(self._CollectionIndex, self._ModName, self._recordID, 13, c_ubyte(nValue))
    uses = property(get_uses, set_uses)
    def get_value(self):
        CBash.ReadFIDField.restype = POINTER(c_int)
        retValue = CBash.ReadFIDField(self._CollectionIndex, self._ModName, self._recordID, 14)
        if(retValue): return retValue.contents.value
        return None
    def set_value(self, nValue):
        CBash.SetFIDFieldI(self._CollectionIndex, self._ModName, self._recordID, 14, nValue)
    value = property(get_value, set_value)
    def get_weight(self):
        CBash.ReadFIDField.restype = POINTER(c_float)
        retValue = CBash.ReadFIDField(self._CollectionIndex, self._ModName, self._recordID, 15)
        if(retValue): return retValue.contents.value
        return None
    def set_weight(self, nValue):
        CBash.SetFIDFieldF(self._CollectionIndex, self._ModName, self._recordID, 15, c_float(nValue))
    weight = property(get_weight, set_weight)
class LVLIRecord(LVLRecord):
    def CopyAsOverride(self, targetMod):
        FID = CBash.CopyLVLIRecord(self._CollectionIndex, self._ModName, self._recordID, targetMod._ModName, c_bool(True))
        if(FID): return LVLIRecord(self._CollectionIndex, targetMod._ModName, FID)
        return None
    def CopyAsNew(self, targetMod):
        FID = CBash.CopyLVLIRecord(self._CollectionIndex, self._ModName, self._recordID, targetMod._ModName, c_bool(False))
        if(FID): return LVLIRecord(self._CollectionIndex, targetMod._ModName, FID)
        return None

class WTHRRecord(BaseRecord):
    def CopyAsOverride(self, targetMod):
        FID = CBash.CopyWTHRRecord(self._CollectionIndex, self._ModName, self._recordID, targetMod._ModName, c_bool(True))
        if(FID): return WTHRRecord(self._CollectionIndex, targetMod._ModName, FID)
        return None
    def CopyAsNew(self, targetMod):
        FID = CBash.CopyWTHRRecord(self._CollectionIndex, self._ModName, self._recordID, targetMod._ModName, c_bool(False))
        if(FID): return WTHRRecord(self._CollectionIndex, targetMod._ModName, FID)
        return None
    class WTHRColor(object):
        def __init__(self, CollectionIndex, ModName, recordID, listIndex):
            self._CollectionIndex = CollectionIndex
            self._ModName = ModName
            self._recordID = recordID
            self._listIndex = listIndex
        def get_riseRed(self):
            CBash.ReadFIDField.restype = POINTER(c_ubyte)
            retValue = CBash.ReadFIDField(self._CollectionIndex, self._ModName, self._recordID, self._listIndex)
            if(retValue): return retValue.contents.value
            return None
        def set_riseRed(self, nValue):
            CBash.SetFIDFieldUC(self._CollectionIndex, self._ModName, self._recordID, self._listIndex, c_ubyte(nValue))
        riseRed = property(get_riseRed, set_riseRed)
        def get_riseGreen(self):
            CBash.ReadFIDField.restype = POINTER(c_ubyte)
            retValue = CBash.ReadFIDField(self._CollectionIndex, self._ModName, self._recordID, self._listIndex + 1)
            if(retValue): return retValue.contents.value
            return None
        def set_riseGreen(self, nValue):
            CBash.SetFIDFieldUC(self._CollectionIndex, self._ModName, self._recordID, self._listIndex + 1, c_ubyte(nValue))
        riseGreen = property(get_riseGreen, set_riseGreen)
        def get_riseBlue(self):
            CBash.ReadFIDField.restype = POINTER(c_ubyte)
            retValue = CBash.ReadFIDField(self._CollectionIndex, self._ModName, self._recordID, self._listIndex + 2)
            if(retValue): return retValue.contents.value
            return None
        def set_riseBlue(self, nValue):
            CBash.SetFIDFieldUC(self._CollectionIndex, self._ModName, self._recordID, self._listIndex + 2, c_ubyte(nValue))
        riseBlue = property(get_riseBlue, set_riseBlue)
        def get_unused1(self):
            numRecords = CBash.GetFIDFieldArraySize(self._CollectionIndex, self._ModName, self._recordID, self._listIndex + 3)
            if(numRecords > 0):
                cRecords = POINTER(c_ubyte * numRecords)()
                CBash.GetFIDFieldArray(self._CollectionIndex, self._ModName, self._recordID, self._listIndex + 3, byref(cRecords))
                return [cRecords.contents[x] for x in range(0, numRecords)]
            return []
        def set_unused1(self, nValue):
            CBash.SetFIDFieldR(self._CollectionIndex, self._ModName, self._recordID, self._listIndex + 3, struct.pack('B', *nValue), 1)
        unused1 = property(get_unused1, set_unused1)
        def get_dayRed(self):
            CBash.ReadFIDField.restype = POINTER(c_ubyte)
            retValue = CBash.ReadFIDField(self._CollectionIndex, self._ModName, self._recordID, self._listIndex + 4)
            if(retValue): return retValue.contents.value
            return None
        def set_dayRed(self, nValue):
            CBash.SetFIDFieldUC(self._CollectionIndex, self._ModName, self._recordID, self._listIndex + 4, c_ubyte(nValue))
        dayRed = property(get_dayRed, set_dayRed)
        def get_dayGreen(self):
            CBash.ReadFIDField.restype = POINTER(c_ubyte)
            retValue = CBash.ReadFIDField(self._CollectionIndex, self._ModName, self._recordID, self._listIndex + 5)
            if(retValue): return retValue.contents.value
            return None
        def set_dayGreen(self, nValue):
            CBash.SetFIDFieldUC(self._CollectionIndex, self._ModName, self._recordID, self._listIndex + 5, c_ubyte(nValue))
        dayGreen = property(get_dayGreen, set_dayGreen)
        def get_dayBlue(self):
            CBash.ReadFIDField.restype = POINTER(c_ubyte)
            retValue = CBash.ReadFIDField(self._CollectionIndex, self._ModName, self._recordID, self._listIndex + 6)
            if(retValue): return retValue.contents.value
            return None
        def set_dayBlue(self, nValue):
            CBash.SetFIDFieldUC(self._CollectionIndex, self._ModName, self._recordID, self._listIndex + 6, c_ubyte(nValue))
        dayBlue = property(get_dayBlue, set_dayBlue)
        def get_unused2(self):
            numRecords = CBash.GetFIDFieldArraySize(self._CollectionIndex, self._ModName, self._recordID, self._listIndex + 7)
            if(numRecords > 0):
                cRecords = POINTER(c_ubyte * numRecords)()
                CBash.GetFIDFieldArray(self._CollectionIndex, self._ModName, self._recordID, self._listIndex + 7, byref(cRecords))
                return [cRecords.contents[x] for x in range(0, numRecords)]
            return []
        def set_unused2(self, nValue):
            CBash.SetFIDFieldR(self._CollectionIndex, self._ModName, self._recordID, self._listIndex + 7, struct.pack('B', *nValue), 1)
        unused2 = property(get_unused2, set_unused2)
        def get_setRed(self):
            CBash.ReadFIDField.restype = POINTER(c_ubyte)
            retValue = CBash.ReadFIDField(self._CollectionIndex, self._ModName, self._recordID, self._listIndex + 8)
            if(retValue): return retValue.contents.value
            return None
        def set_setRed(self, nValue):
            CBash.SetFIDFieldUC(self._CollectionIndex, self._ModName, self._recordID, self._listIndex + 8, c_ubyte(nValue))
        setRed = property(get_setRed, set_setRed)
        def get_setGreen(self):
            CBash.ReadFIDField.restype = POINTER(c_ubyte)
            retValue = CBash.ReadFIDField(self._CollectionIndex, self._ModName, self._recordID, self._listIndex + 9)
            if(retValue): return retValue.contents.value
            return None
        def set_setGreen(self, nValue):
            CBash.SetFIDFieldUC(self._CollectionIndex, self._ModName, self._recordID, self._listIndex + 9, c_ubyte(nValue))
        setGreen = property(get_setGreen, set_setGreen)
        def get_setBlue(self):
            CBash.ReadFIDField.restype = POINTER(c_ubyte)
            retValue = CBash.ReadFIDField(self._CollectionIndex, self._ModName, self._recordID, self._listIndex + 10)
            if(retValue): return retValue.contents.value
            return None
        def set_setBlue(self, nValue):
            CBash.SetFIDFieldUC(self._CollectionIndex, self._ModName, self._recordID, self._listIndex + 10, c_ubyte(nValue))
        setBlue = property(get_setBlue, set_setBlue)
        def get_unused3(self):
            numRecords = CBash.GetFIDFieldArraySize(self._CollectionIndex, self._ModName, self._recordID, self._listIndex + 11)
            if(numRecords > 0):
                cRecords = POINTER(c_ubyte * numRecords)()
                CBash.GetFIDFieldArray(self._CollectionIndex, self._ModName, self._recordID, self._listIndex + 11, byref(cRecords))
                return [cRecords.contents[x] for x in range(0, numRecords)]
            return []
        def set_unused3(self, nValue):
            CBash.SetFIDFieldR(self._CollectionIndex, self._ModName, self._recordID, self._listIndex + 11, struct.pack('B', *nValue), 1)
        unused3 = property(get_unused3, set_unused3)
        def get_nightRed(self):
            CBash.ReadFIDField.restype = POINTER(c_ubyte)
            retValue = CBash.ReadFIDField(self._CollectionIndex, self._ModName, self._recordID, self._listIndex + 12)
            if(retValue): return retValue.contents.value
            return None
        def set_nightRed(self, nValue):
            CBash.SetFIDFieldUC(self._CollectionIndex, self._ModName, self._recordID, self._listIndex + 12, c_ubyte(nValue))
        nightRed = property(get_nightRed, set_nightRed)
        def get_nightGreen(self):
            CBash.ReadFIDField.restype = POINTER(c_ubyte)
            retValue = CBash.ReadFIDField(self._CollectionIndex, self._ModName, self._recordID, self._listIndex + 13)
            if(retValue): return retValue.contents.value
            return None
        def set_nightGreen(self, nValue):
            CBash.SetFIDFieldUC(self._CollectionIndex, self._ModName, self._recordID, self._listIndex + 13, c_ubyte(nValue))
        nightGreen = property(get_nightGreen, set_nightGreen)
        def get_nightBlue(self):
            CBash.ReadFIDField.restype = POINTER(c_ubyte)
            retValue = CBash.ReadFIDField(self._CollectionIndex, self._ModName, self._recordID, self._listIndex + 14)
            if(retValue): return retValue.contents.value
            return None
        def set_nightBlue(self, nValue):
            CBash.SetFIDFieldUC(self._CollectionIndex, self._ModName, self._recordID, self._listIndex + 14, c_ubyte(nValue))
        nightBlue = property(get_nightBlue, set_nightBlue)
        def get_unused4(self):
            numRecords = CBash.GetFIDFieldArraySize(self._CollectionIndex, self._ModName, self._recordID, self._listIndex + 15)
            if(numRecords > 0):
                cRecords = POINTER(c_ubyte * numRecords)()
                CBash.GetFIDFieldArray(self._CollectionIndex, self._ModName, self._recordID, self._listIndex + 15, byref(cRecords))
                return [cRecords.contents[x] for x in range(0, numRecords)]
            return []
        def set_unused4(self, nValue):
            CBash.SetFIDFieldR(self._CollectionIndex, self._ModName, self._recordID, self._listIndex + 15, struct.pack('B', *nValue), 1)
        unused4 = property(get_unused4, set_unused4)  
    class Sound(object):
        def __init__(self, CollectionIndex, ModName, recordID, listIndex):
            self._CollectionIndex = CollectionIndex
            self._ModName = ModName
            self._recordID = recordID
            self._listIndex = listIndex
        def get_sound(self):
            CBash.ReadFIDListField.restype = POINTER(c_uint)
            retValue = CBash.ReadFIDListField(self._CollectionIndex, self._ModName, self._recordID, 204, self._listIndex, 1)
            if(retValue): return retValue.contents.value
            return None
        def set_sound(self, nValue):
            CBash.SetFIDListFieldUI(self._CollectionIndex, self._ModName, self._recordID, 204, self._listIndex, 1, nValue)
        sound = property(get_sound, set_sound)
        def get_type(self):
            CBash.ReadFIDListField.restype = POINTER(c_uint)
            retValue = CBash.ReadFIDListField(self._CollectionIndex, self._ModName, self._recordID, 204, self._listIndex, 2)
            if(retValue): return retValue.contents.value
            return None
        def set_type(self, nValue):
            CBash.SetFIDListFieldUI(self._CollectionIndex, self._ModName, self._recordID, 204, self._listIndex, 2, nValue)
        type = property(get_type, set_type)
        def get_IsDefault(self):
            return (self.type == 0)
        def set_IsDefault(self, nValue):
            if (nValue == True): self.type = 0
            elif(self.get_IsDefault()): self.IsPrecip = True
        IsDefault = property(get_IsDefault, set_IsDefault)
        def get_IsPrecipitation(self):
            return (self.type == 1)
        def set_IsPrecipitation(self, nValue):
            if (nValue == True): self.type = 1
            elif(self.get_IsPrecipitation()): self.IsDefault = True
        IsPrecip = IsPrecipitation = property(get_IsPrecipitation, set_IsPrecipitation)
        def get_IsWind(self):
            return (self.type == 2)
        def set_IsWind(self, nValue):
            if (nValue == True): self.type = 2
            elif(self.get_IsWind()): self.IsDefault = True
        IsWind = property(get_IsWind, set_IsWind)
        def get_IsThunder(self):
            return (self.type == 3)
        def set_IsThunder(self, nValue):
            if (nValue == True): self.type = 3
            elif(self.get_IsThunder()): self.IsDefault = True
        IsThunder = property(get_IsThunder, set_IsThunder)
    def newSoundsElement(self):
        listIndex = CBash.CreateFIDListElement(self._CollectionIndex, self._ModName, self._recordID, 204)
        if(listIndex == -1): return None
        return self.Sound(self._CollectionIndex, self._ModName, self._recordID, listIndex)
    def get_lowerLayer(self):
        CBash.ReadFIDField.restype = c_char_p
        return CBash.ReadFIDField(self._CollectionIndex, self._ModName, self._recordID, 6)
    def set_lowerLayer(self, nValue):
        CBash.SetFIDFieldStr(self._CollectionIndex, self._ModName, self._recordID, 6, nValue)
    lowerLayer = property(get_lowerLayer, set_lowerLayer)
    def get_upperLayer(self):
        CBash.ReadFIDField.restype = c_char_p
        return CBash.ReadFIDField(self._CollectionIndex, self._ModName, self._recordID, 7)
    def set_upperLayer(self, nValue):
        CBash.SetFIDFieldStr(self._CollectionIndex, self._ModName, self._recordID, 7, nValue)
    upperLayer = property(get_upperLayer, set_upperLayer)
    def get_modPath(self):
        CBash.ReadFIDField.restype = c_char_p
        return CBash.ReadFIDField(self._CollectionIndex, self._ModName, self._recordID, 8)
    def set_modPath(self, nValue):
        CBash.SetFIDFieldStr(self._CollectionIndex, self._ModName, self._recordID, 8, nValue)
    modPath = property(get_modPath, set_modPath)
    def get_modb(self):
        CBash.ReadFIDField.restype = POINTER(c_float)
        retValue = CBash.ReadFIDField(self._CollectionIndex, self._ModName, self._recordID, 9)
        if(retValue): return retValue.contents.value
        return None
    def set_modb(self, nValue):
        CBash.SetFIDFieldF(self._CollectionIndex, self._ModName, self._recordID, 9, c_float(nValue))
    modb = property(get_modb, set_modb)
    def get_modt_p(self):
        numRecords = CBash.GetFIDFieldArraySize(self._CollectionIndex, self._ModName, self._recordID, 10)
        if(numRecords > 0):
            cRecords = POINTER(c_ubyte * numRecords)()
            CBash.GetFIDFieldArray(self._CollectionIndex, self._ModName, self._recordID, 10, byref(cRecords))
            return [cRecords.contents[x] for x in range(0, numRecords)]
        return []
    def set_modt_p(self, nValue):
        length = len(nValue)
        CBash.SetFIDFieldR(self._CollectionIndex, self._ModName, self._recordID, 10, struct.pack('B' * length, *nValue), length)
    modt_p = property(get_modt_p, set_modt_p)
    @property
    def upperSky(self):
        return self.WTHRColor(self._CollectionIndex, self._ModName, self._recordID, 11)
    @property
    def fog(self):
        return self.WTHRColor(self._CollectionIndex, self._ModName, self._recordID, 27)
    @property
    def lowerClouds(self):
        return self.WTHRColor(self._CollectionIndex, self._ModName, self._recordID, 43)
    @property
    def ambient(self):
        return self.WTHRColor(self._CollectionIndex, self._ModName, self._recordID, 59)
    @property
    def sunlight(self):
        return self.WTHRColor(self._CollectionIndex, self._ModName, self._recordID, 75)
    @property
    def sun(self):
        return self.WTHRColor(self._CollectionIndex, self._ModName, self._recordID, 91)
    @property
    def stars(self):
        return self.WTHRColor(self._CollectionIndex, self._ModName, self._recordID, 107)
    @property
    def lowerSky(self):
        return self.WTHRColor(self._CollectionIndex, self._ModName, self._recordID, 123)
    @property
    def horizon(self):
        return self.WTHRColor(self._CollectionIndex, self._ModName, self._recordID, 139)
    @property
    def upperClouds(self):
        return self.WTHRColor(self._CollectionIndex, self._ModName, self._recordID, 155)
    def get_fogDayNear(self):
        CBash.ReadFIDField.restype = POINTER(c_float)
        retValue = CBash.ReadFIDField(self._CollectionIndex, self._ModName, self._recordID, 171)
        if(retValue): return retValue.contents.value
        return None
    def set_fogDayNear(self, nValue):
        CBash.SetFIDFieldF(self._CollectionIndex, self._ModName, self._recordID, 171, c_float(nValue))
    fogDayNear = property(get_fogDayNear, set_fogDayNear)
    def get_fogDayFar(self):
        CBash.ReadFIDField.restype = POINTER(c_float)
        retValue = CBash.ReadFIDField(self._CollectionIndex, self._ModName, self._recordID, 172)
        if(retValue): return retValue.contents.value
        return None
    def set_fogDayFar(self, nValue):
        CBash.SetFIDFieldF(self._CollectionIndex, self._ModName, self._recordID, 172, c_float(nValue))
    fogDayFar = property(get_fogDayFar, set_fogDayFar)
    def get_fogNightNear(self):
        CBash.ReadFIDField.restype = POINTER(c_float)
        retValue = CBash.ReadFIDField(self._CollectionIndex, self._ModName, self._recordID, 173)
        if(retValue): return retValue.contents.value
        return None
    def set_fogNightNear(self, nValue):
        CBash.SetFIDFieldF(self._CollectionIndex, self._ModName, self._recordID, 173, c_float(nValue))
    fogNightNear = property(get_fogNightNear, set_fogNightNear)
    def get_fogNightFar(self):
        CBash.ReadFIDField.restype = POINTER(c_float)
        retValue = CBash.ReadFIDField(self._CollectionIndex, self._ModName, self._recordID, 174)
        if(retValue): return retValue.contents.value
        return None
    def set_fogNightFar(self, nValue):
        CBash.SetFIDFieldF(self._CollectionIndex, self._ModName, self._recordID, 174, c_float(nValue))
    fogNightFar = property(get_fogNightFar, set_fogNightFar)
    def get_eyeAdaptSpeed(self):
        CBash.ReadFIDField.restype = POINTER(c_float)
        retValue = CBash.ReadFIDField(self._CollectionIndex, self._ModName, self._recordID, 175)
        if(retValue): return retValue.contents.value
        return None
    def set_eyeAdaptSpeed(self, nValue):
        CBash.SetFIDFieldF(self._CollectionIndex, self._ModName, self._recordID, 175, c_float(nValue))
    eyeAdaptSpeed = property(get_eyeAdaptSpeed, set_eyeAdaptSpeed)
    def get_blurRadius(self):
        CBash.ReadFIDField.restype = POINTER(c_float)
        retValue = CBash.ReadFIDField(self._CollectionIndex, self._ModName, self._recordID, 176)
        if(retValue): return retValue.contents.value
        return None
    def set_blurRadius(self, nValue):
        CBash.SetFIDFieldF(self._CollectionIndex, self._ModName, self._recordID, 176, c_float(nValue))
    blurRadius = property(get_blurRadius, set_blurRadius)
    def get_blurPasses(self):
        CBash.ReadFIDField.restype = POINTER(c_float)
        retValue = CBash.ReadFIDField(self._CollectionIndex, self._ModName, self._recordID, 177)
        if(retValue): return retValue.contents.value
        return None
    def set_blurPasses(self, nValue):
        CBash.SetFIDFieldF(self._CollectionIndex, self._ModName, self._recordID, 177, c_float(nValue))
    blurPasses = property(get_blurPasses, set_blurPasses)
    def get_emissiveMult(self):
        CBash.ReadFIDField.restype = POINTER(c_float)
        retValue = CBash.ReadFIDField(self._CollectionIndex, self._ModName, self._recordID, 178)
        if(retValue): return retValue.contents.value
        return None
    def set_emissiveMult(self, nValue):
        CBash.SetFIDFieldF(self._CollectionIndex, self._ModName, self._recordID, 178, c_float(nValue))
    emissiveMult = property(get_emissiveMult, set_emissiveMult)
    def get_targetLum(self):
        CBash.ReadFIDField.restype = POINTER(c_float)
        retValue = CBash.ReadFIDField(self._CollectionIndex, self._ModName, self._recordID, 179)
        if(retValue): return retValue.contents.value
        return None
    def set_targetLum(self, nValue):
        CBash.SetFIDFieldF(self._CollectionIndex, self._ModName, self._recordID, 179, c_float(nValue))
    targetLum = property(get_targetLum, set_targetLum)
    def get_upperLumClamp(self):
        CBash.ReadFIDField.restype = POINTER(c_float)
        retValue = CBash.ReadFIDField(self._CollectionIndex, self._ModName, self._recordID, 180)
        if(retValue): return retValue.contents.value
        return None
    def set_upperLumClamp(self, nValue):
        CBash.SetFIDFieldF(self._CollectionIndex, self._ModName, self._recordID, 180, c_float(nValue))
    upperLumClamp = property(get_upperLumClamp, set_upperLumClamp)
    def get_brightScale(self):
        CBash.ReadFIDField.restype = POINTER(c_float)
        retValue = CBash.ReadFIDField(self._CollectionIndex, self._ModName, self._recordID, 181)
        if(retValue): return retValue.contents.value
        return None
    def set_brightScale(self, nValue):
        CBash.SetFIDFieldF(self._CollectionIndex, self._ModName, self._recordID, 181, c_float(nValue))
    brightScale = property(get_brightScale, set_brightScale)
    def get_brightClamp(self):
        CBash.ReadFIDField.restype = POINTER(c_float)
        retValue = CBash.ReadFIDField(self._CollectionIndex, self._ModName, self._recordID, 182)
        if(retValue): return retValue.contents.value
        return None
    def set_brightClamp(self, nValue):
        CBash.SetFIDFieldF(self._CollectionIndex, self._ModName, self._recordID, 182, c_float(nValue))
    brightClamp = property(get_brightClamp, set_brightClamp)
    def get_lumRampNoTex(self):
        CBash.ReadFIDField.restype = POINTER(c_float)
        retValue = CBash.ReadFIDField(self._CollectionIndex, self._ModName, self._recordID, 183)
        if(retValue): return retValue.contents.value
        return None
    def set_lumRampNoTex(self, nValue):
        CBash.SetFIDFieldF(self._CollectionIndex, self._ModName, self._recordID, 183, c_float(nValue))
    lumRampNoTex = property(get_lumRampNoTex, set_lumRampNoTex)
    def get_lumRampMin(self):
        CBash.ReadFIDField.restype = POINTER(c_float)
        retValue = CBash.ReadFIDField(self._CollectionIndex, self._ModName, self._recordID, 184)
        if(retValue): return retValue.contents.value
        return None
    def set_lumRampMin(self, nValue):
        CBash.SetFIDFieldF(self._CollectionIndex, self._ModName, self._recordID, 184, c_float(nValue))
    lumRampMin = property(get_lumRampMin, set_lumRampMin)
    def get_lumRampMax(self):
        CBash.ReadFIDField.restype = POINTER(c_float)
        retValue = CBash.ReadFIDField(self._CollectionIndex, self._ModName, self._recordID, 185)
        if(retValue): return retValue.contents.value
        return None
    def set_lumRampMax(self, nValue):
        CBash.SetFIDFieldF(self._CollectionIndex, self._ModName, self._recordID, 185, c_float(nValue))
    lumRampMax = property(get_lumRampMax, set_lumRampMax)
    def get_sunlightDimmer(self):
        CBash.ReadFIDField.restype = POINTER(c_float)
        retValue = CBash.ReadFIDField(self._CollectionIndex, self._ModName, self._recordID, 186)
        if(retValue): return retValue.contents.value
        return None
    def set_sunlightDimmer(self, nValue):
        CBash.SetFIDFieldF(self._CollectionIndex, self._ModName, self._recordID, 186, c_float(nValue))
    sunlightDimmer = property(get_sunlightDimmer, set_sunlightDimmer)
    def get_grassDimmer(self):
        CBash.ReadFIDField.restype = POINTER(c_float)
        retValue = CBash.ReadFIDField(self._CollectionIndex, self._ModName, self._recordID, 187)
        if(retValue): return retValue.contents.value
        return None
    def set_grassDimmer(self, nValue):
        CBash.SetFIDFieldF(self._CollectionIndex, self._ModName, self._recordID, 187, c_float(nValue))
    grassDimmer = property(get_grassDimmer, set_grassDimmer)
    def get_treeDimmer(self):
        CBash.ReadFIDField.restype = POINTER(c_float)
        retValue = CBash.ReadFIDField(self._CollectionIndex, self._ModName, self._recordID, 188)
        if(retValue): return retValue.contents.value
        return None
    def set_treeDimmer(self, nValue):
        CBash.SetFIDFieldF(self._CollectionIndex, self._ModName, self._recordID, 188, c_float(nValue))
    treeDimmer = property(get_treeDimmer, set_treeDimmer)
    def get_windSpeed(self):
        CBash.ReadFIDField.restype = POINTER(c_ubyte)
        retValue = CBash.ReadFIDField(self._CollectionIndex, self._ModName, self._recordID, 189)
        if(retValue): return retValue.contents.value
        return None
    def set_windSpeed(self, nValue):
        CBash.SetFIDFieldUC(self._CollectionIndex, self._ModName, self._recordID, 189, c_ubyte(nValue))
    windSpeed = property(get_windSpeed, set_windSpeed)
    def get_lowerCloudSpeed(self):
        CBash.ReadFIDField.restype = POINTER(c_ubyte)
        retValue = CBash.ReadFIDField(self._CollectionIndex, self._ModName, self._recordID, 190)
        if(retValue): return retValue.contents.value
        return None
    def set_lowerCloudSpeed(self, nValue):
        CBash.SetFIDFieldUC(self._CollectionIndex, self._ModName, self._recordID, 190, c_ubyte(nValue))
    lowerCloudSpeed = property(get_lowerCloudSpeed, set_lowerCloudSpeed)
    def get_upperCloudSpeed(self):
        CBash.ReadFIDField.restype = POINTER(c_ubyte)
        retValue = CBash.ReadFIDField(self._CollectionIndex, self._ModName, self._recordID, 191)
        if(retValue): return retValue.contents.value
        return None
    def set_upperCloudSpeed(self, nValue):
        CBash.SetFIDFieldUC(self._CollectionIndex, self._ModName, self._recordID, 191, c_ubyte(nValue))
    upperCloudSpeed = property(get_upperCloudSpeed, set_upperCloudSpeed)
    def get_transDelta(self):
        CBash.ReadFIDField.restype = POINTER(c_ubyte)
        retValue = CBash.ReadFIDField(self._CollectionIndex, self._ModName, self._recordID, 192)
        if(retValue): return retValue.contents.value
        return None
    def set_transDelta(self, nValue):
        CBash.SetFIDFieldUC(self._CollectionIndex, self._ModName, self._recordID, 192, c_ubyte(nValue))
    transDelta = property(get_transDelta, set_transDelta)
    def get_sunGlare(self):
        CBash.ReadFIDField.restype = POINTER(c_ubyte)
        retValue = CBash.ReadFIDField(self._CollectionIndex, self._ModName, self._recordID, 193)
        if(retValue): return retValue.contents.value
        return None
    def set_sunGlare(self, nValue):
        CBash.SetFIDFieldUC(self._CollectionIndex, self._ModName, self._recordID, 193, c_ubyte(nValue))
    sunGlare = property(get_sunGlare, set_sunGlare)
    def get_sunDamage(self):
        CBash.ReadFIDField.restype = POINTER(c_ubyte)
        retValue = CBash.ReadFIDField(self._CollectionIndex, self._ModName, self._recordID, 194)
        if(retValue): return retValue.contents.value
        return None
    def set_sunDamage(self, nValue):
        CBash.SetFIDFieldUC(self._CollectionIndex, self._ModName, self._recordID, 194, c_ubyte(nValue))
    sunDamage = property(get_sunDamage, set_sunDamage)
    def get_rainFadeIn(self):
        CBash.ReadFIDField.restype = POINTER(c_ubyte)
        retValue = CBash.ReadFIDField(self._CollectionIndex, self._ModName, self._recordID, 195)
        if(retValue): return retValue.contents.value
        return None
    def set_rainFadeIn(self, nValue):
        CBash.SetFIDFieldUC(self._CollectionIndex, self._ModName, self._recordID, 195, c_ubyte(nValue))
    rainFadeIn = property(get_rainFadeIn, set_rainFadeIn)
    def get_rainFadeOut(self):
        CBash.ReadFIDField.restype = POINTER(c_ubyte)
        retValue = CBash.ReadFIDField(self._CollectionIndex, self._ModName, self._recordID, 196)
        if(retValue): return retValue.contents.value
        return None
    def set_rainFadeOut(self, nValue):
        CBash.SetFIDFieldUC(self._CollectionIndex, self._ModName, self._recordID, 196, c_ubyte(nValue))
    rainFadeOut = property(get_rainFadeOut, set_rainFadeOut)
    def get_boltFadeIn(self):
        CBash.ReadFIDField.restype = POINTER(c_ubyte)
        retValue = CBash.ReadFIDField(self._CollectionIndex, self._ModName, self._recordID, 197)
        if(retValue): return retValue.contents.value
        return None
    def set_boltFadeIn(self, nValue):
        CBash.SetFIDFieldUC(self._CollectionIndex, self._ModName, self._recordID, 197, c_ubyte(nValue))
    boltFadeIn = property(get_boltFadeIn, set_boltFadeIn)
    def get_boltFadeOut(self):
        CBash.ReadFIDField.restype = POINTER(c_ubyte)
        retValue = CBash.ReadFIDField(self._CollectionIndex, self._ModName, self._recordID, 198)
        if(retValue): return retValue.contents.value
        return None
    def set_boltFadeOut(self, nValue):
        CBash.SetFIDFieldUC(self._CollectionIndex, self._ModName, self._recordID, 198, c_ubyte(nValue))
    boltFadeOut = property(get_boltFadeOut, set_boltFadeOut)
    def get_boltFrequency(self):
        CBash.ReadFIDField.restype = POINTER(c_ubyte)
        retValue = CBash.ReadFIDField(self._CollectionIndex, self._ModName, self._recordID, 199)
        if(retValue): return retValue.contents.value
        return None
    def set_boltFrequency(self, nValue):
        CBash.SetFIDFieldUC(self._CollectionIndex, self._ModName, self._recordID, 199, c_ubyte(nValue))
    boltFrequency = property(get_boltFrequency, set_boltFrequency)
    def get_weatherType(self):
        CBash.ReadFIDField.restype = POINTER(c_ubyte)
        retValue = CBash.ReadFIDField(self._CollectionIndex, self._ModName, self._recordID, 200)
        if(retValue): return retValue.contents.value
        return None
    def set_weatherType(self, nValue):
        CBash.SetFIDFieldUC(self._CollectionIndex, self._ModName, self._recordID, 200, c_ubyte(nValue))
    weatherType = property(get_weatherType, set_weatherType)
    def get_boltRed(self):
        CBash.ReadFIDField.restype = POINTER(c_ubyte)
        retValue = CBash.ReadFIDField(self._CollectionIndex, self._ModName, self._recordID, 201)
        if(retValue): return retValue.contents.value
        return None
    def set_boltRed(self, nValue):
        CBash.SetFIDFieldUC(self._CollectionIndex, self._ModName, self._recordID, 201, c_ubyte(nValue))
    boltRed = property(get_boltRed, set_boltRed)
    def get_boltGreen(self):
        CBash.ReadFIDField.restype = POINTER(c_ubyte)
        retValue = CBash.ReadFIDField(self._CollectionIndex, self._ModName, self._recordID, 202)
        if(retValue): return retValue.contents.value
        return None
    def set_boltGreen(self, nValue):
        CBash.SetFIDFieldUC(self._CollectionIndex, self._ModName, self._recordID, 202, c_ubyte(nValue))
    boltGreen = property(get_boltGreen, set_boltGreen)
    def get_boltBlue(self):
        CBash.ReadFIDField.restype = POINTER(c_ubyte)
        retValue = CBash.ReadFIDField(self._CollectionIndex, self._ModName, self._recordID, 203)
        if(retValue): return retValue.contents.value
        return None
    def set_boltBlue(self, nValue):
        CBash.SetFIDFieldUC(self._CollectionIndex, self._ModName, self._recordID, 203, c_ubyte(nValue))
    boltBlue = property(get_boltBlue, set_boltBlue)
    def get_sounds(self):
        numRecords = CBash.GetFIDListSize(self._CollectionIndex, self._ModName, self._recordID, 204)
        if(numRecords > 0): return [self.Sound(self._CollectionIndex, self._ModName, self._recordID, x) for x in range(0, numRecords)]
        return []
    def set_sounds(self, nSounds):
        diffLength = len(nSounds) - CBash.GetFIDListSize(self._CollectionIndex, self._ModName, self._recordID, 204)
        nValues = [(nSound.sound, nSound.type) for nSound in nSounds]
        while(diffLength < 0):
            CBash.DeleteFIDListElement(self._CollectionIndex, self._ModName, self._recordID, 204)
            diffLength += 1
        while(diffLength > 0):
            CBash.CreateFIDListElement(self._CollectionIndex, self._ModName, self._recordID, 204)
            diffLength -= 1
        for oSound, nValue in zip(self.sounds, nValues):
            oSound.sound, oSound.type = nValue
    sounds = property(get_sounds, set_sounds)
    def get_IsNone(self):
        return self.IsPleasant == False and self.IsCloudy == False and self.IsRainy == False and self.IsSnow == False
    def set_IsNone(self, nValue):
        if (nValue == True):
            self.weatherType &= ~0x00000001
            self.weatherType &= ~0x00000002
            self.weatherType &= ~0x00000004
            self.weatherType &= ~0x00000008
        elif(self.get_IsNone()):
            self.weatherType |= 0x00000001
            self.weatherType &= ~0x00000002
            self.weatherType &= ~0x00000004
            self.weatherType &= ~0x00000008
    IsNone = property(get_IsNone, set_IsNone)
    def get_IsPleasant(self):
        return (self.weatherType & 0x00000001) != 0
    def set_IsPleasant(self, nValue):
        if (nValue == True):
            self.weatherType |= 0x00000001
            self.weatherType &= ~0x00000002
            self.weatherType &= ~0x00000004
            self.weatherType &= ~0x00000008
        elif(self.get_IsPleasant()):
            self.weatherType &= ~0x00000001
            self.weatherType &= ~0x00000002
            self.weatherType &= ~0x00000004
            self.weatherType &= ~0x00000008
    IsPleasant = property(get_IsPleasant, set_IsPleasant)
    def get_IsCloudy(self):
        return (self.weatherType & 0x00000002) != 0
    def set_IsCloudy(self, nValue):
        if (nValue == True):
            self.weatherType &= ~0x00000001
            self.weatherType |= 0x00000002
            self.weatherType &= ~0x00000004
            self.weatherType &= ~0x00000008
        elif(self.get_IsCloudy()):
            self.weatherType &= ~0x00000001
            self.weatherType &= ~0x00000002
            self.weatherType &= ~0x00000004
            self.weatherType &= ~0x00000008
    IsCloudy = property(get_IsCloudy, set_IsCloudy)
    def get_IsRainy(self):
        return (self.weatherType & 0x00000004) != 0
    def set_IsRainy(self, nValue):
        if (nValue == True):
            self.weatherType &= ~0x00000001
            self.weatherType &= ~0x00000002
            self.weatherType |= 0x00000004
            self.weatherType &= ~0x00000008
        elif(self.get_IsRainy()):
            self.weatherType &= ~0x00000001
            self.weatherType &= ~0x00000002
            self.weatherType &= ~0x00000004
            self.weatherType &= ~0x00000008
    IsRainy = property(get_IsRainy, set_IsRainy)
    def get_IsSnow(self):
        return (self.weatherType & 0x00000008) != 0
    def set_IsSnow(self, nValue):
        if (nValue == True):
            self.weatherType &= ~0x00000001
            self.weatherType &= ~0x00000002
            self.weatherType &= ~0x00000004
            self.weatherType |= 0x00000008
        elif(self.get_IsSnow()):
            self.weatherType &= ~0x00000001
            self.weatherType &= ~0x00000002
            self.weatherType &= ~0x00000004
            self.weatherType &= ~0x00000008
    IsSnow = property(get_IsSnow, set_IsSnow)
    def get_IsUnk1(self):
        return (self.weatherType & 0x01000000) != 0
    def set_IsUnk1(self, nValue):
        if (nValue == True): self.weatherType |= 0x01000000
        else: self.weatherType &= ~0x01000000
    IsUnk1 = property(get_IsUnk1, set_IsUnk1)
    def get_IsUnk2(self):
        return (self.weatherType & 0x10000000) != 0
    def set_IsUnk2(self, nValue):
        if (nValue == True): self.weatherType |= 0x10000000
        else: self.weatherType &= ~0x10000000
    IsUnk2 = property(get_IsUnk2, set_IsUnk2)
    
class CLMTRecord(BaseRecord):
    def CopyAsOverride(self, targetMod):
        FID = CBash.CopyCLMTRecord(self._CollectionIndex, self._ModName, self._recordID, targetMod._ModName, c_bool(True))
        if(FID): return CLMTRecord(self._CollectionIndex, targetMod._ModName, FID)
        return None
    def CopyAsNew(self, targetMod):
        FID = CBash.CopyCLMTRecord(self._CollectionIndex, self._ModName, self._recordID, targetMod._ModName, c_bool(False))
        if(FID): return CLMTRecord(self._CollectionIndex, targetMod._ModName, FID)
        return None
    class Weather(object):
        def __init__(self, CollectionIndex, ModName, recordID, listIndex):
            self._CollectionIndex = CollectionIndex
            self._ModName = ModName
            self._recordID = recordID
            self._listIndex = listIndex
        def get_weather(self):
            CBash.ReadFIDListField.restype = POINTER(c_uint)
            retValue = CBash.ReadFIDListField(self._CollectionIndex, self._ModName, self._recordID, 6, self._listIndex, 1)
            if(retValue): return retValue.contents.value
            return None
        def set_weather(self, nValue):
            CBash.SetFIDListFieldUI(self._CollectionIndex, self._ModName, self._recordID, 6, self._listIndex, 1, nValue)
        weather = property(get_weather, set_weather)
        def get_chance(self):
            CBash.ReadFIDListField.restype = POINTER(c_int)
            retValue = CBash.ReadFIDListField(self._CollectionIndex, self._ModName, self._recordID, 6, self._listIndex, 2)
            if(retValue): return retValue.contents.value
            return None
        def set_chance(self, nValue):
            CBash.SetFIDListFieldI(self._CollectionIndex, self._ModName, self._recordID, 6, self._listIndex, 2, nValue)
        chance = property(get_chance, set_chance)
    def newWeathersElement(self):
        listIndex = CBash.CreateFIDListElement(self._CollectionIndex, self._ModName, self._recordID, 6)
        if(listIndex == -1): return None
        return self.Weather(self._CollectionIndex, self._ModName, self._recordID, listIndex)

    def get_weathers(self):
        numRecords = CBash.GetFIDListSize(self._CollectionIndex, self._ModName, self._recordID, 6)
        if(numRecords > 0): return [self.Weather(self._CollectionIndex, self._ModName, self._recordID, x) for x in range(0, numRecords)]
        return []
    def set_weathers(self, nWeathers):
        diffLength = len(nWeathers) - CBash.GetFIDListSize(self._CollectionIndex, self._ModName, self._recordID, 6)
        nValues = [(nWeather.weather, nWeather.chance) for nWeather in nWeathers]
        while(diffLength < 0):
            CBash.DeleteFIDListElement(self._CollectionIndex, self._ModName, self._recordID, 6)
            diffLength += 1
        while(diffLength > 0):
            CBash.CreateFIDListElement(self._CollectionIndex, self._ModName, self._recordID, 6)
            diffLength -= 1
        for oWeather, nValue in zip(self.weathers, nValues):
            oWeather.weather, oWeather.chance = nValue
    weathers = property(get_weathers, set_weathers)
    def get_sunPath(self):
        CBash.ReadFIDField.restype = c_char_p
        return CBash.ReadFIDField(self._CollectionIndex, self._ModName, self._recordID, 7)
    def set_sunPath(self, nValue):
        CBash.SetFIDFieldStr(self._CollectionIndex, self._ModName, self._recordID, 7, nValue)
    sunPath = property(get_sunPath, set_sunPath)
    def get_glarePath(self):
        CBash.ReadFIDField.restype = c_char_p
        return CBash.ReadFIDField(self._CollectionIndex, self._ModName, self._recordID, 8)
    def set_glarePath(self, nValue):
        CBash.SetFIDFieldStr(self._CollectionIndex, self._ModName, self._recordID, 8, nValue)
    glarePath = property(get_glarePath, set_glarePath)
    def get_modPath(self):
        CBash.ReadFIDField.restype = c_char_p
        return CBash.ReadFIDField(self._CollectionIndex, self._ModName, self._recordID, 9)
    def set_modPath(self, nValue):
        CBash.SetFIDFieldStr(self._CollectionIndex, self._ModName, self._recordID, 9, nValue)
    modPath = property(get_modPath, set_modPath)
    def get_modb(self):
        CBash.ReadFIDField.restype = POINTER(c_float)
        retValue = CBash.ReadFIDField(self._CollectionIndex, self._ModName, self._recordID, 10)
        if(retValue): return retValue.contents.value
        return None
    def set_modb(self, nValue):
        CBash.SetFIDFieldF(self._CollectionIndex, self._ModName, self._recordID, 10, c_float(nValue))
    modb = property(get_modb, set_modb)
    def get_modt_p(self):
        numRecords = CBash.GetFIDFieldArraySize(self._CollectionIndex, self._ModName, self._recordID, 11)
        if(numRecords > 0):
            cRecords = POINTER(c_ubyte * numRecords)()
            CBash.GetFIDFieldArray(self._CollectionIndex, self._ModName, self._recordID, 11, byref(cRecords))
            return [cRecords.contents[x] for x in range(0, numRecords)]
        return []
    def set_modt_p(self, nValue):
        length = len(nValue)
        CBash.SetFIDFieldR(self._CollectionIndex, self._ModName, self._recordID, 11, struct.pack('B' * length, *nValue), length)
    modt_p = property(get_modt_p, set_modt_p)
    def get_riseBegin(self):
        CBash.ReadFIDField.restype = POINTER(c_ubyte)
        retValue = CBash.ReadFIDField(self._CollectionIndex, self._ModName, self._recordID, 12)
        if(retValue): return retValue.contents.value
        return None
    def set_riseBegin(self, nValue):
        CBash.SetFIDFieldUC(self._CollectionIndex, self._ModName, self._recordID, 12, c_ubyte(nValue))
    riseBegin = property(get_riseBegin, set_riseBegin)
    def get_riseEnd(self):
        CBash.ReadFIDField.restype = POINTER(c_ubyte)
        retValue = CBash.ReadFIDField(self._CollectionIndex, self._ModName, self._recordID, 13)
        if(retValue): return retValue.contents.value
        return None
    def set_riseEnd(self, nValue):
        CBash.SetFIDFieldUC(self._CollectionIndex, self._ModName, self._recordID, 13, c_ubyte(nValue))
    riseEnd = property(get_riseEnd, set_riseEnd)
    def get_setBegin(self):
        CBash.ReadFIDField.restype = POINTER(c_ubyte)
        retValue = CBash.ReadFIDField(self._CollectionIndex, self._ModName, self._recordID, 14)
        if(retValue): return retValue.contents.value
        return None
    def set_setBegin(self, nValue):
        CBash.SetFIDFieldUC(self._CollectionIndex, self._ModName, self._recordID, 14, c_ubyte(nValue))
    setBegin = property(get_setBegin, set_setBegin)
    def get_setEnd(self):
        CBash.ReadFIDField.restype = POINTER(c_ubyte)
        retValue = CBash.ReadFIDField(self._CollectionIndex, self._ModName, self._recordID, 15)
        if(retValue): return retValue.contents.value
        return None
    def set_setEnd(self, nValue):
        CBash.SetFIDFieldUC(self._CollectionIndex, self._ModName, self._recordID, 15, c_ubyte(nValue))
    setEnd = property(get_setEnd, set_setEnd)
    def get_volatility(self):
        CBash.ReadFIDField.restype = POINTER(c_ubyte)
        retValue = CBash.ReadFIDField(self._CollectionIndex, self._ModName, self._recordID, 16)
        if(retValue): return retValue.contents.value
        return None
    def set_volatility(self, nValue):
        CBash.SetFIDFieldUC(self._CollectionIndex, self._ModName, self._recordID, 16, c_ubyte(nValue))
    volatility = property(get_volatility, set_volatility)
    def get_phaseLength(self):
        CBash.ReadFIDField.restype = POINTER(c_ubyte)
        retValue = CBash.ReadFIDField(self._CollectionIndex, self._ModName, self._recordID, 17)
        if(retValue): return retValue.contents.value
        return None
    def set_phaseLength(self, nValue):
        CBash.SetFIDFieldUC(self._CollectionIndex, self._ModName, self._recordID, 17, c_ubyte(nValue))
    phaseLength = property(get_phaseLength, set_phaseLength)
    
class REGNRecord(BaseRecord):
    def CopyAsOverride(self, targetMod):
        FID = CBash.CopyREGNRecord(self._CollectionIndex, self._ModName, self._recordID, targetMod._ModName, c_bool(True))
        if(FID): return REGNRecord(self._CollectionIndex, targetMod._ModName, FID)
        return None
    def CopyAsNew(self, targetMod):
        FID = CBash.CopyREGNRecord(self._CollectionIndex, self._ModName, self._recordID, targetMod._ModName, c_bool(False))
        if(FID): return REGNRecord(self._CollectionIndex, targetMod._ModName, FID)
        return None
    class Area(object):
        class Points(object):
            def __init__(self, CollectionIndex, ModName, recordID, listIndex, listX2Index):
                self._CollectionIndex = CollectionIndex
                self._ModName = ModName
                self._recordID = recordID
                self._listIndex = listIndex
                self._listX2Index = listX2Index
            def get_posX(self):
                CBash.ReadFIDListX2Field.restype = POINTER(c_float)
                retValue = CBash.ReadFIDListX2Field(self._CollectionIndex, self._ModName, self._recordID, 12, self._listIndex, 2, self._listX2Index, 1)
                if(retValue): return retValue.contents.value
                return None
            def set_posX(self, nValue):
                CBash.SetFIDListX2FieldF(self._CollectionIndex, self._ModName, self._recordID, 12, self._listIndex, 2, self._listX2Index, 1, c_float(nValue))
            posX = property(get_posX, set_posX)
            def get_posY(self):
                CBash.ReadFIDListX2Field.restype = POINTER(c_float)
                retValue = CBash.ReadFIDListX2Field(self._CollectionIndex, self._ModName, self._recordID, 12, self._listIndex, 2, self._listX2Index, 2)
                if(retValue): return retValue.contents.value
                return None
            def set_posY(self, nValue):
                CBash.SetFIDListX2FieldF(self._CollectionIndex, self._ModName, self._recordID, 12, self._listIndex, 2, self._listX2Index, 2, c_float(nValue))
            posY = property(get_posY, set_posY)
            
        def __init__(self, CollectionIndex, ModName, recordID, listIndex):
            self._CollectionIndex = CollectionIndex
            self._ModName = ModName
            self._recordID = recordID
            self._listIndex = listIndex
        def newPointsElement(self):
            listX2Index = CBash.CreateFIDListX2Element(self._CollectionIndex, self._ModName, self._recordID, 12, self._listIndex, 2)
            if(listX2Index == -1): return None
            return self.Points(self._CollectionIndex, self._ModName, self._recordID, self._listIndex, listX2Index)
        def get_edgeFalloff(self):
            CBash.ReadFIDListField.restype = POINTER(c_uint)
            retValue = CBash.ReadFIDListField(self._CollectionIndex, self._ModName, self._recordID, 12, self._listIndex, 1)
            if(retValue): return retValue.contents.value
            return None
        def set_edgeFalloff(self, nValue):
            CBash.SetFIDListFieldUI(self._CollectionIndex, self._ModName, self._recordID, 12, self._listIndex, 1, nValue)
        edgeFalloff = property(get_edgeFalloff, set_edgeFalloff)
        def get_points(self):
            numRecords = CBash.GetFIDListX2Size(self._CollectionIndex, self._ModName, self._recordID, 12, self._listIndex, 2)
            if(numRecords > 0): return [self.Points(self._CollectionIndex, self._ModName, self._recordID, self._listIndex, x) for x in range(0, numRecords)]
            return []
        def set_points(self, nPoints):
            diffLength = len(nPoints) - CBash.GetFIDListX2Size(self._CollectionIndex, self._ModName, self._recordID, 12, self._listIndex, 2)
            nValues = [(nPoint.posX, nPoint.posY) for nPoint in nPoints]
            while(diffLength < 0):
                CBash.DeleteFIDListX2Element(self._CollectionIndex, self._ModName, self._recordID, 12, self._listIndex, 2)
                diffLength += 1
            while(diffLength > 0):
                CBash.CreateFIDListX2Element(self._CollectionIndex, self._ModName, self._recordID, 12, self._listIndex, 2)
                diffLength -= 1
            for oPoint, nValue in zip(self.points, nValues):
                oPoint.posX, oPoint.posY = nValue
        points = property(get_points, set_points)
    class Entry(object):
        class Object(object):
            def __init__(self, CollectionIndex, ModName, recordID, listIndex, listX2Index):
                self._CollectionIndex = CollectionIndex
                self._ModName = ModName
                self._recordID = recordID
                self._listIndex = listIndex
                self._listX2Index = listX2Index
            def get_objectId(self):
                CBash.ReadFIDListX2Field.restype = POINTER(c_uint)
                retValue = CBash.ReadFIDListX2Field(self._CollectionIndex, self._ModName, self._recordID, 13, self._listIndex, 5, self._listX2Index, 1)
                if(retValue): return retValue.contents.value
                return None
            def set_objectId(self, nValue):
                CBash.SetFIDListX2FieldUI(self._CollectionIndex, self._ModName, self._recordID, 13, self._listIndex, 5, self._listX2Index, 1, nValue)
            objectId = property(get_objectId, set_objectId)
            def get_parentIndex(self):
                CBash.ReadFIDListX2Field.restype = POINTER(c_ushort)
                retValue = CBash.ReadFIDListX2Field(self._CollectionIndex, self._ModName, self._recordID, 13, self._listIndex, 5, self._listX2Index, 2)
                if(retValue): return retValue.contents.value
                return None
            def set_parentIndex(self, nValue):
                CBash.SetFIDListX2FieldUS(self._CollectionIndex, self._ModName, self._recordID, 13, self._listIndex, 5, self._listX2Index, 2, c_ushort(nValue))
            parentIndex = property(get_parentIndex, set_parentIndex)
            def get_unused1(self):
                numRecords = CBash.GetFIDListX2ArraySize(self._CollectionIndex, self._ModName, self._recordID, 13, self._listIndex, 5, self._listX2Index, 3)
                if(numRecords > 0):
                    cRecords = POINTER(c_ubyte * numRecords)()
                    CBash.GetFIDListX2Array(self._CollectionIndex, self._ModName, self._recordID, 13, self._listIndex, 5, self._listX2Index, 3, byref(cRecords))
                    return [cRecords.contents[x] for x in range(0, numRecords)]
                return []
            def set_unused1(self, nValue):
                CBash.SetFIDListX2FieldR(self._CollectionIndex, self._ModName, self._recordID, 13, self._listIndex, 5, self._listX2Index, 3, struct.pack('2B', *nValue), 2)
            unused1 = property(get_unused1, set_unused1)
            def get_density(self):
                CBash.ReadFIDListX2Field.restype = POINTER(c_float)
                retValue = CBash.ReadFIDListX2Field(self._CollectionIndex, self._ModName, self._recordID, 13, self._listIndex, 5, self._listX2Index, 4)
                if(retValue): return retValue.contents.value
                return None
            def set_density(self, nValue):
                CBash.SetFIDListX2FieldF(self._CollectionIndex, self._ModName, self._recordID, 13, self._listIndex, 5, self._listX2Index, 4, c_float(nValue))
            density = property(get_density, set_density)
            def get_clustering(self):
                CBash.ReadFIDListX2Field.restype = POINTER(c_ubyte)
                retValue = CBash.ReadFIDListX2Field(self._CollectionIndex, self._ModName, self._recordID, 13, self._listIndex, 5, self._listX2Index, 5)
                if(retValue): return retValue.contents.value
                return None
            def set_clustering(self, nValue):
                CBash.SetFIDListX2FieldUC(self._CollectionIndex, self._ModName, self._recordID, 13, self._listIndex, 5, self._listX2Index, 5, c_ubyte(nValue))
            clustering = property(get_clustering, set_clustering)
            def get_minSlope(self):
                CBash.ReadFIDListX2Field.restype = POINTER(c_ubyte)
                retValue = CBash.ReadFIDListX2Field(self._CollectionIndex, self._ModName, self._recordID, 13, self._listIndex, 5, self._listX2Index, 6)
                if(retValue): return retValue.contents.value
                return None
            def set_minSlope(self, nValue):
                CBash.SetFIDListX2FieldUC(self._CollectionIndex, self._ModName, self._recordID, 13, self._listIndex, 5, self._listX2Index, 6, c_ubyte(nValue))
            minSlope = property(get_minSlope, set_minSlope)
            def get_maxSlope(self):
                CBash.ReadFIDListX2Field.restype = POINTER(c_ubyte)
                retValue = CBash.ReadFIDListX2Field(self._CollectionIndex, self._ModName, self._recordID, 13, self._listIndex, 5, self._listX2Index, 7)
                if(retValue): return retValue.contents.value
                return None
            def set_maxSlope(self, nValue):
                CBash.SetFIDListX2FieldUC(self._CollectionIndex, self._ModName, self._recordID, 13, self._listIndex, 5, self._listX2Index, 7, c_ubyte(nValue))
            maxSlope = property(get_maxSlope, set_maxSlope)
            def get_flags(self):
                CBash.ReadFIDListX2Field.restype = POINTER(c_ubyte)
                retValue = CBash.ReadFIDListX2Field(self._CollectionIndex, self._ModName, self._recordID, 13, self._listIndex, 5, self._listX2Index, 8)
                if(retValue): return retValue.contents.value
                return None
            def set_flags(self, nValue):
                CBash.SetFIDListX2FieldUC(self._CollectionIndex, self._ModName, self._recordID, 13, self._listIndex, 5, self._listX2Index, 8, c_ubyte(nValue))
            flags = property(get_flags, set_flags)
            def get_radiusWRTParent(self):
                CBash.ReadFIDListX2Field.restype = POINTER(c_ushort)
                retValue = CBash.ReadFIDListX2Field(self._CollectionIndex, self._ModName, self._recordID, 13, self._listIndex, 5, self._listX2Index, 9)
                if(retValue): return retValue.contents.value
                return None
            def set_radiusWRTParent(self, nValue):
                CBash.SetFIDListX2FieldUS(self._CollectionIndex, self._ModName, self._recordID, 13, self._listIndex, 5, self._listX2Index, 9, c_ushort(nValue))
            radiusWRTParent = property(get_radiusWRTParent, set_radiusWRTParent)
            def get_radius(self):
                CBash.ReadFIDListX2Field.restype = POINTER(c_ushort)
                retValue = CBash.ReadFIDListX2Field(self._CollectionIndex, self._ModName, self._recordID, 13, self._listIndex, 5, self._listX2Index, 10)
                if(retValue): return retValue.contents.value
                return None
            def set_radius(self, nValue):
                CBash.SetFIDListX2FieldUS(self._CollectionIndex, self._ModName, self._recordID, 13, self._listIndex, 5, self._listX2Index, 10, c_ushort(nValue))
            radius = property(get_radius, set_radius)
            def get_unk1(self):
                numRecords = CBash.GetFIDListX2ArraySize(self._CollectionIndex, self._ModName, self._recordID, 13, self._listIndex, 5, self._listX2Index, 11)
                if(numRecords > 0):
                    cRecords = POINTER(c_ubyte * numRecords)()
                    CBash.GetFIDListX2Array(self._CollectionIndex, self._ModName, self._recordID, 13, self._listIndex, 5, self._listX2Index, 11, byref(cRecords))
                    return [cRecords.contents[x] for x in range(0, numRecords)]
                return []
            def set_unk1(self, nValue):
                CBash.SetFIDListX2FieldR(self._CollectionIndex, self._ModName, self._recordID, 13, self._listIndex, 5, self._listX2Index, 11, struct.pack('4B', *nValue), 4)
            unk1 = property(get_unk1, set_unk1)
            def get_maxHeight(self):
                CBash.ReadFIDListX2Field.restype = POINTER(c_float)
                retValue = CBash.ReadFIDListX2Field(self._CollectionIndex, self._ModName, self._recordID, 13, self._listIndex, 5, self._listX2Index, 12)
                if(retValue): return retValue.contents.value
                return None
            def set_maxHeight(self, nValue):
                CBash.SetFIDListX2FieldF(self._CollectionIndex, self._ModName, self._recordID, 13, self._listIndex, 5, self._listX2Index, 12, c_float(nValue))
            maxHeight = property(get_maxHeight, set_maxHeight)
            def get_sink(self):
                CBash.ReadFIDListX2Field.restype = POINTER(c_float)
                retValue = CBash.ReadFIDListX2Field(self._CollectionIndex, self._ModName, self._recordID, 13, self._listIndex, 5, self._listX2Index, 13)
                if(retValue): return retValue.contents.value
                return None
            def set_sink(self, nValue):
                CBash.SetFIDListX2FieldF(self._CollectionIndex, self._ModName, self._recordID, 13, self._listIndex, 5, self._listX2Index, 13, c_float(nValue))
            sink = property(get_sink, set_sink)
            def get_sinkVar(self):
                CBash.ReadFIDListX2Field.restype = POINTER(c_float)
                retValue = CBash.ReadFIDListX2Field(self._CollectionIndex, self._ModName, self._recordID, 13, self._listIndex, 5, self._listX2Index, 14)
                if(retValue): return retValue.contents.value
                return None
            def set_sinkVar(self, nValue):
                CBash.SetFIDListX2FieldF(self._CollectionIndex, self._ModName, self._recordID, 13, self._listIndex, 5, self._listX2Index, 14, c_float(nValue))
            sinkVar = property(get_sinkVar, set_sinkVar)
            def get_sizeVar(self):
                CBash.ReadFIDListX2Field.restype = POINTER(c_float)
                retValue = CBash.ReadFIDListX2Field(self._CollectionIndex, self._ModName, self._recordID, 13, self._listIndex, 5, self._listX2Index, 15)
                if(retValue): return retValue.contents.value
                return None
            def set_sizeVar(self, nValue):
                CBash.SetFIDListX2FieldF(self._CollectionIndex, self._ModName, self._recordID, 13, self._listIndex, 5, self._listX2Index, 15, c_float(nValue))
            sizeVar = property(get_sizeVar, set_sizeVar)
            def get_angleVarX(self):
                CBash.ReadFIDListX2Field.restype = POINTER(c_ushort)
                retValue = CBash.ReadFIDListX2Field(self._CollectionIndex, self._ModName, self._recordID, 13, self._listIndex, 5, self._listX2Index, 16)
                if(retValue): return retValue.contents.value
                return None
            def set_angleVarX(self, nValue):
                CBash.SetFIDListX2FieldUS(self._CollectionIndex, self._ModName, self._recordID, 13, self._listIndex, 5, self._listX2Index, 16, c_ushort(nValue))
            angleVarX = property(get_angleVarX, set_angleVarX)
            def get_angleVarY(self):
                CBash.ReadFIDListX2Field.restype = POINTER(c_ushort)
                retValue = CBash.ReadFIDListX2Field(self._CollectionIndex, self._ModName, self._recordID, 13, self._listIndex, 5, self._listX2Index, 17)
                if(retValue): return retValue.contents.value
                return None
            def set_angleVarY(self, nValue):
                CBash.SetFIDListX2FieldUS(self._CollectionIndex, self._ModName, self._recordID, 13, self._listIndex, 5, self._listX2Index, 17, c_ushort(nValue))
            angleVarY = property(get_angleVarY, set_angleVarY)
            def get_angleVarZ(self):
                CBash.ReadFIDListX2Field.restype = POINTER(c_ushort)
                retValue = CBash.ReadFIDListX2Field(self._CollectionIndex, self._ModName, self._recordID, 13, self._listIndex, 5, self._listX2Index, 18)
                if(retValue): return retValue.contents.value
                return None
            def set_angleVarZ(self, nValue):
                CBash.SetFIDListX2FieldUS(self._CollectionIndex, self._ModName, self._recordID, 13, self._listIndex, 5, self._listX2Index, 18, c_ushort(nValue))
            angleVarZ = property(get_angleVarZ, set_angleVarZ)
            def get_unused2(self):
                numRecords = CBash.GetFIDListX2ArraySize(self._CollectionIndex, self._ModName, self._recordID, 13, self._listIndex, 5, self._listX2Index, 19)
                if(numRecords > 0):
                    cRecords = POINTER(c_ubyte * numRecords)()
                    CBash.GetFIDListX2Array(self._CollectionIndex, self._ModName, self._recordID, 13, self._listIndex, 5, self._listX2Index, 19, byref(cRecords))
                    return [cRecords.contents[x] for x in range(0, numRecords)]
                return []
            def set_unused2(self, nValue):
                CBash.SetFIDListX2FieldR(self._CollectionIndex, self._ModName, self._recordID, 13, self._listIndex, 5, self._listX2Index, 19, struct.pack('2B', *nValue), 2)
            unused2 = property(get_unused2, set_unused2)
            def get_unk2(self):
                numRecords = CBash.GetFIDListX2ArraySize(self._CollectionIndex, self._ModName, self._recordID, 13, self._listIndex, 5, self._listX2Index, 20)
                if(numRecords > 0):
                    cRecords = POINTER(c_ubyte * numRecords)()
                    CBash.GetFIDListX2Array(self._CollectionIndex, self._ModName, self._recordID, 13, self._listIndex, 5, self._listX2Index, 20, byref(cRecords))
                    return [cRecords.contents[x] for x in range(0, numRecords)]
                return []
            def set_unk2(self, nValue):
                CBash.SetFIDListX2FieldR(self._CollectionIndex, self._ModName, self._recordID, 13, self._listIndex, 5, self._listX2Index, 20, struct.pack('4B', *nValue), 4)
            unk2 = property(get_unk2, set_unk2)
            def get_IsConformToSlope(self):
                return (self.flags & 0x00000001) != 0
            def set_IsConformToSlope(self, nValue):
                if (nValue == True): self.flags |= 0x00000001
                else: self.flags &= ~0x00000001
            IsConformToSlope = property(get_IsConformToSlope, set_IsConformToSlope)
            def get_IsPaintVertices(self):
                return (self.flags & 0x00000002) != 0
            def set_IsPaintVertices(self, nValue):
                if (nValue == True): self.flags |= 0x00000002
                else: self.flags &= ~0x00000002
            IsPaintVertices = property(get_IsPaintVertices, set_IsPaintVertices)
            def get_IsSizeVariance(self):
                return (self.flags & 0x00000004) != 0
            def set_IsSizeVariance(self, nValue):
                if (nValue == True): self.flags |= 0x00000004
                else: self.flags &= ~0x00000004
            IsSizeVariance = property(get_IsSizeVariance, set_IsSizeVariance)
            def get_IsXVariance(self):
                return (self.flags & 0x00000008) != 0
            def set_IsXVariance(self, nValue):
                if (nValue == True): self.flags |= 0x00000008
                else: self.flags &= ~0x00000008
            IsXVariance = property(get_IsXVariance, set_IsXVariance)
            def get_IsYVariance(self):
                return (self.flags & 0x00000010) != 0
            def set_IsYVariance(self, nValue):
                if (nValue == True): self.flags |= 0x00000010
                else: self.flags &= ~0x00000010
            IsYVariance = property(get_IsYVariance, set_IsYVariance)
            def get_IsZVariance(self):
                return (self.flags & 0x00000020) != 0
            def set_IsZVariance(self, nValue):
                if (nValue == True): self.flags |= 0x00000020
                else: self.flags &= ~0x00000020
            IsZVariance = property(get_IsZVariance, set_IsZVariance)
            def get_IsTree(self):
                return (self.flags & 0x00000040) != 0
            def set_IsTree(self, nValue):
                if (nValue == True): self.flags |= 0x00000040
                else: self.flags &= ~0x00000040
            IsTree = property(get_IsTree, set_IsTree)
            def get_IsHugeRock(self):
                return (self.flags & 0x00000080) != 0
            def set_IsHugeRock(self, nValue):
                if (nValue == True): self.flags |= 0x00000080
                else: self.flags &= ~0x00000080
            IsHugeRock = property(get_IsHugeRock, set_IsHugeRock)
            
        class Grass(object):
            def __init__(self, CollectionIndex, ModName, recordID, listIndex, listX2Index):
                self._CollectionIndex = CollectionIndex
                self._ModName = ModName
                self._recordID = recordID
                self._listIndex = listIndex
                self._listX2Index = listX2Index
            def get_grass(self):
                CBash.ReadFIDListX2Field.restype = POINTER(c_uint)
                retValue = CBash.ReadFIDListX2Field(self._CollectionIndex, self._ModName, self._recordID, 13, self._listIndex, 8, self._listX2Index, 1)
                if(retValue): return retValue.contents.value
                return None
            def set_grass(self, nValue):
                CBash.SetFIDListX2FieldUI(self._CollectionIndex, self._ModName, self._recordID, 13, self._listIndex, 8, self._listX2Index, 1, nValue)
            grass = property(get_grass, set_grass)
            def get_unk1(self):
                numRecords = CBash.GetFIDListX2ArraySize(self._CollectionIndex, self._ModName, self._recordID, 13, self._listIndex, 8, self._listX2Index, 2)
                if(numRecords > 0):
                    cRecords = POINTER(c_ubyte * numRecords)()
                    CBash.GetFIDListX2Array(self._CollectionIndex, self._ModName, self._recordID, 13, self._listIndex, 8, self._listX2Index, 2, byref(cRecords))
                    return [cRecords.contents[x] for x in range(0, numRecords)]
                return []
            def set_unk1(self, nValue):
                CBash.SetFIDListX2FieldR(self._CollectionIndex, self._ModName, self._recordID, 13, self._listIndex, 8, self._listX2Index, 2, struct.pack('4B', *nValue), 4)
            unk1 = property(get_unk1, set_unk1)
        class Sound(object):
            def __init__(self, CollectionIndex, ModName, recordID, listIndex, listX2Index):
                self._CollectionIndex = CollectionIndex
                self._ModName = ModName
                self._recordID = recordID
                self._listIndex = listIndex
                self._listX2Index = listX2Index
            def get_sound(self):
                CBash.ReadFIDListX2Field.restype = POINTER(c_uint)
                retValue = CBash.ReadFIDListX2Field(self._CollectionIndex, self._ModName, self._recordID, 13, self._listIndex, 10, self._listX2Index, 1)
                if(retValue): return retValue.contents.value
                return None
            def set_sound(self, nValue):
                CBash.SetFIDListX2FieldUI(self._CollectionIndex, self._ModName, self._recordID, 13, self._listIndex, 10, self._listX2Index, 1, nValue)
            sound = property(get_sound, set_sound)
            def get_flags(self):
                CBash.ReadFIDListX2Field.restype = POINTER(c_uint)
                retValue = CBash.ReadFIDListX2Field(self._CollectionIndex, self._ModName, self._recordID, 13, self._listIndex, 10, self._listX2Index, 2)
                if(retValue): return retValue.contents.value
                return None
            def set_flags(self, nValue):
                CBash.SetFIDListX2FieldUI(self._CollectionIndex, self._ModName, self._recordID, 13, self._listIndex, 10, self._listX2Index, 2, nValue)
            flags = property(get_flags, set_flags)
            def get_chance(self):
                CBash.ReadFIDListX2Field.restype = POINTER(c_uint)
                retValue = CBash.ReadFIDListX2Field(self._CollectionIndex, self._ModName, self._recordID, 13, self._listIndex, 10, self._listX2Index, 3)
                if(retValue): return retValue.contents.value
                return None
            def set_chance(self, nValue):
                CBash.SetFIDListX2FieldUI(self._CollectionIndex, self._ModName, self._recordID, 13, self._listIndex, 10, self._listX2Index, 3, nValue)
            chance = property(get_chance, set_chance)

            def get_IsPleasant(self):
                return (self.flags & 0x00000001) != 0
            def set_IsPleasant(self, nValue):
                if (nValue == True): self.flags |= 0x00000001
                else: self.flags &= ~0x00000001
            IsPleasant = property(get_IsPleasant, set_IsPleasant)
            def get_IsCloudy(self):
                return (self.flags & 0x00000002) != 0
            def set_IsCloudy(self, nValue):
                if (nValue == True): self.flags |= 0x00000002
                else: self.flags &= ~0x00000002
            IsCloudy = property(get_IsCloudy, set_IsCloudy)
            def get_IsRainy(self):
                return (self.flags & 0x00000004) != 0
            def set_IsRainy(self, nValue):
                if (nValue == True): self.flags |= 0x00000004
                else: self.flags &= ~0x00000004
            IsRainy = property(get_IsRainy, set_IsRainy)
            def get_IsSnowy(self):
                return (self.flags & 0x00000008) != 0
            def set_IsSnowy(self, nValue):
                if (nValue == True): self.flags |= 0x00000008
                else: self.flags &= ~0x00000008
            IsSnowy = property(get_IsSnowy, set_IsSnowy)
        class Weather(object):
            def __init__(self, CollectionIndex, ModName, recordID, listIndex, listX2Index):
                self._CollectionIndex = CollectionIndex
                self._ModName = ModName
                self._recordID = recordID
                self._listIndex = listIndex
                self._listX2Index = listX2Index
            def get_weather(self):
                CBash.ReadFIDListX2Field.restype = POINTER(c_uint)
                retValue = CBash.ReadFIDListX2Field(self._CollectionIndex, self._ModName, self._recordID, 13, self._listIndex, 11, self._listX2Index, 1)
                if(retValue): return retValue.contents.value
                return None
            def set_weather(self, nValue):
                CBash.SetFIDListX2FieldUI(self._CollectionIndex, self._ModName, self._recordID, 13, self._listIndex, 11, self._listX2Index, 1, nValue)
            weather = property(get_weather, set_weather)
            def get_chance(self):
                CBash.ReadFIDListX2Field.restype = POINTER(c_uint)
                retValue = CBash.ReadFIDListX2Field(self._CollectionIndex, self._ModName, self._recordID, 13, self._listIndex, 11, self._listX2Index, 2)
                if(retValue): return retValue.contents.value
                return None
            def set_chance(self, nValue):
                CBash.SetFIDListX2FieldUI(self._CollectionIndex, self._ModName, self._recordID, 13, self._listIndex, 11, self._listX2Index, 2, nValue)
            chance = property(get_chance, set_chance)

        def __init__(self, CollectionIndex, ModName, recordID, listIndex):
            self._CollectionIndex = CollectionIndex
            self._ModName = ModName
            self._recordID = recordID
            self._listIndex = listIndex
        def newObjectsElement(self):
            listX2Index = CBash.CreateFIDListX2Element(self._CollectionIndex, self._ModName, self._recordID, 13, self._listIndex, 5)
            if(listX2Index == -1): return None
            return self.Object(self._CollectionIndex, self._ModName, self._recordID, self._listIndex, listX2Index)
        def newGrassesElement(self):
            listX2Index = CBash.CreateFIDListX2Element(self._CollectionIndex, self._ModName, self._recordID, 13, self._listIndex, 8)
            if(listX2Index == -1): return None
            return self.Grass(self._CollectionIndex, self._ModName, self._recordID, self._listIndex, listX2Index)
        def newSoundsElement(self):
            listX2Index = CBash.CreateFIDListX2Element(self._CollectionIndex, self._ModName, self._recordID, 13, self._listIndex, 10)
            if(listX2Index == -1): return None
            return self.Sound(self._CollectionIndex, self._ModName, self._recordID, self._listIndex, listX2Index)
        def newWeathersElement(self):
            listX2Index = CBash.CreateFIDListX2Element(self._CollectionIndex, self._ModName, self._recordID, 13, self._listIndex, 11)
            if(listX2Index == -1): return None
            return self.Weather(self._CollectionIndex, self._ModName, self._recordID, self._listIndex, listX2Index)

        def get_entryType(self):
            CBash.ReadFIDListField.restype = POINTER(c_uint)
            retValue = CBash.ReadFIDListField(self._CollectionIndex, self._ModName, self._recordID, 13, self._listIndex, 1)
            if(retValue): return retValue.contents.value
            return None
        def set_entryType(self, nValue):
            CBash.SetFIDListFieldUI(self._CollectionIndex, self._ModName, self._recordID, 13, self._listIndex, 1, nValue)
        entryType = property(get_entryType, set_entryType)
        def get_flags(self):
            CBash.ReadFIDListField.restype = POINTER(c_ubyte)
            retValue = CBash.ReadFIDListField(self._CollectionIndex, self._ModName, self._recordID, 13, self._listIndex, 2)
            if(retValue): return retValue.contents.value
            return None
        def set_flags(self, nValue):
            CBash.SetFIDListFieldUC(self._CollectionIndex, self._ModName, self._recordID, 13, self._listIndex, 2, c_ubyte(nValue))
        flags = property(get_flags, set_flags)
        def get_priority(self):
            CBash.ReadFIDListField.restype = POINTER(c_ubyte)
            retValue = CBash.ReadFIDListField(self._CollectionIndex, self._ModName, self._recordID, 13, self._listIndex, 3)
            if(retValue): return retValue.contents.value
            return None
        def set_priority(self, nValue):
            CBash.SetFIDListFieldUC(self._CollectionIndex, self._ModName, self._recordID, 13, self._listIndex, 3, c_ubyte(nValue))
        priority = property(get_priority, set_priority)
        def get_unused1(self):
            numRecords = CBash.GetFIDListArraySize(self._CollectionIndex, self._ModName, self._recordID, 13, self._listIndex, 4)
            if(numRecords > 0):
                cRecords = POINTER(c_ubyte * numRecords)()
                CBash.GetFIDListArray(self._CollectionIndex, self._ModName, self._recordID, 13, self._listIndex, 4, byref(cRecords))
                return [cRecords.contents[x] for x in range(0, numRecords)]
            return []
        def set_unused1(self, nValue):
            CBash.SetFIDListFieldR(self._CollectionIndex, self._ModName, self._recordID, 13, self._listIndex, 4, struct.pack('2B', *nValue), 2)
        unused1 = property(get_unused1, set_unused1)
        def get_objects(self):
            numRecords = CBash.GetFIDListX2Size(self._CollectionIndex, self._ModName, self._recordID, 13, self._listIndex, 5)
            if(numRecords > 0): return [self.Object(self._CollectionIndex, self._ModName, self._recordID, self._listIndex, x) for x in range(0, numRecords)]
            return []
        def set_objects(self, nObjects):
            diffLength = len(nObjects) - CBash.GetFIDListX2Size(self._CollectionIndex, self._ModName, self._recordID, 13, self._listIndex, 5)
            nValues = [(nObject.objectId, nObject.parentIndex, nObject.unused1, nObject.density, nObject.clustering, 
                        nObject.minSlope, nObject.maxSlope, nObject.flags, nObject.radiusWRTParent, nObject.radius, 
                        nObject.unk1, nObject.maxHeight, nObject.sink, nObject.sinkVar, nObject.sizeVar, 
                        nObject.angleVarX, nObject.angleVarY, nObject.angleVarZ, nObject.unused2, nObject.unk2) for nObject in nObjects]
            while(diffLength < 0):
                CBash.DeleteFIDListX2Element(self._CollectionIndex, self._ModName, self._recordID, 13, self._listIndex, 5)
                diffLength += 1
            while(diffLength > 0):
                CBash.CreateFIDListX2Element(self._CollectionIndex, self._ModName, self._recordID, 13, self._listIndex, 5)
                diffLength -= 1
            for oObject, nValue in zip(self.objects, nValues):
                oObject.objectId, oObject.parentIndex, oObject.unused1, oObject.density, oObject.clustering, oObject.minSlope, oObject.maxSlope, oObject.flags, oObject.radiusWRTParent, oObject.radius, oObject.unk1, oObject.maxHeight, oObject.sink, oObject.sinkVar, oObject.sizeVar,oObject.angleVarX, oObject.angleVarY, oObject.angleVarZ, oObject.unused2, oObject.unk2 = nValue
        objects = property(get_objects, set_objects)
        def get_mapName(self):
            CBash.ReadFIDListField.restype = c_char_p
            return CBash.ReadFIDListField(self._CollectionIndex, self._ModName, self._recordID, 13, self._listIndex, 6)
        def set_mapName(self, nValue):
            CBash.SetFIDListFieldStr(self._CollectionIndex, self._ModName, self._recordID, 13, self._listIndex, 6, nValue)
        mapName = property(get_mapName, set_mapName)
        def get_iconPath(self):
            CBash.ReadFIDListField.restype = c_char_p
            return CBash.ReadFIDListField(self._CollectionIndex, self._ModName, self._recordID, 13, self._listIndex, 7)
        def set_iconPath(self, nValue):
            CBash.SetFIDListFieldStr(self._CollectionIndex, self._ModName, self._recordID, 13, self._listIndex, 7, nValue)
        iconPath = property(get_iconPath, set_iconPath)
        def get_grasses(self):
            numRecords = CBash.GetFIDListX2Size(self._CollectionIndex, self._ModName, self._recordID, 13, self._listIndex, 8)
            if(numRecords > 0): return [self.Grass(self._CollectionIndex, self._ModName, self._recordID, self._listIndex, x) for x in range(0, numRecords)]
            return []
        def set_grasses(self, nGrasses):
            diffLength = len(nGrasses) - CBash.GetFIDListX2Size(self._CollectionIndex, self._ModName, self._recordID, 13, self._listIndex, 8)
            nValues = [(nGrass.grass, nGrass.unk1) for nGrass in nGrasses]
            while(diffLength < 0):
                CBash.DeleteFIDListX2Element(self._CollectionIndex, self._ModName, self._recordID, 13, self._listIndex, 8)
                diffLength += 1
            while(diffLength > 0):
                CBash.CreateFIDListX2Element(self._CollectionIndex, self._ModName, self._recordID, 13, self._listIndex, 8)
                diffLength -= 1
            for oGrass, nValue in zip(self.grasses, nValues):
                oGrass.grass, oGrass.unk1 = nValue
        grasses = property(get_grasses, set_grasses)
        def get_musicType(self):
            CBash.ReadFIDListField.restype = POINTER(c_uint)
            retValue = CBash.ReadFIDListField(self._CollectionIndex, self._ModName, self._recordID, 13, self._listIndex, 9)
            if(retValue): return retValue.contents.value
            return None
        def set_musicType(self, nValue):
            CBash.SetFIDListFieldUI(self._CollectionIndex, self._ModName, self._recordID, 13, self._listIndex, 9, nValue)
        musicType = property(get_musicType, set_musicType)
        def get_sounds(self):
            numRecords = CBash.GetFIDListX2Size(self._CollectionIndex, self._ModName, self._recordID, 13, self._listIndex, 10)
            if(numRecords > 0): return [self.Sound(self._CollectionIndex, self._ModName, self._recordID, self._listIndex, x) for x in range(0, numRecords)]
            return []
        def set_sounds(self, nSounds):
            diffLength = len(nSounds) - CBash.GetFIDListX2Size(self._CollectionIndex, self._ModName, self._recordID, 13, self._listIndex, 10)
            nValues = [(nSound.sound, nSound.flags, nSound.chance) for nSound in nSounds]
            while(diffLength < 0):
                CBash.DeleteFIDListX2Element(self._CollectionIndex, self._ModName, self._recordID, 13, self._listIndex, 10)
                diffLength += 1
            while(diffLength > 0):
                CBash.CreateFIDListX2Element(self._CollectionIndex, self._ModName, self._recordID, 13, self._listIndex, 10)
                diffLength -= 1
            for oSound, nValue in zip(self.sounds, nValues):
                oSound.sound, oSound.flags, oSound.chance = nValue
        sounds = property(get_sounds, set_sounds)
        def get_weathers(self):
            numRecords = CBash.GetFIDListX2Size(self._CollectionIndex, self._ModName, self._recordID, 13, self._listIndex, 11)
            if(numRecords > 0): return [self.Weather(self._CollectionIndex, self._ModName, self._recordID, self._listIndex, x) for x in range(0, numRecords)]
            return []
        def set_weathers(self, nWeathers):
            diffLength = len(nWeathers) - CBash.GetFIDListX2Size(self._CollectionIndex, self._ModName, self._recordID, 13, self._listIndex, 11)
            nValues = [(nWeather.weather, nWeather.chance) for nWeather in nWeathers]
            while(diffLength < 0):
                CBash.DeleteFIDListX2Element(self._CollectionIndex, self._ModName, self._recordID, 13, self._listIndex, 11)
                diffLength += 1
            while(diffLength > 0):
                CBash.CreateFIDListX2Element(self._CollectionIndex, self._ModName, self._recordID, 13, self._listIndex, 11)
                diffLength -= 1
            for oWeather, nValue in zip(self.weathers, nValues):
                oWeather.weather, oWeather.chance = nValue
        weathers = property(get_weathers, set_weathers)
        def get_IsOverride(self):
            return (self.flags & 0x00000001) != 0
        def set_IsOverride(self, nValue):
            if (nValue == True): self.flags |= 0x00000001
            else: self.flags &= ~0x00000001
        IsOverride = property(get_IsOverride, set_IsOverride)
        def get_IsObject(self):
            return (self.entryType == 2)
        def set_IsObject(self, nValue):
            if (nValue == True): self.entryType = 2
            elif(self.get_IsObject()): self.IsWeather = True
        IsObject = property(get_IsObject, set_IsObject)
        def get_IsWeather(self):
            return (self.entryType == 3)
        def set_IsWeather(self, nValue):
            if (nValue == True): self.entryType = 3
            elif(self.get_IsWeather()): self.IsObject = True
        IsWeather = property(get_IsWeather, set_IsWeather)
        def get_IsMap(self):
            return (self.entryType == 4)
        def set_IsMap(self, nValue):
            if (nValue == True): self.entryType = 4
            elif(self.get_IsMap()): self.IsObject = True
        IsMap = property(get_IsMap, set_IsMap)
        def get_IsIcon(self):
            return (self.entryType == 5)
        def set_IsIcon(self, nValue):
            if (nValue == True): self.entryType = 5
            elif(self.get_IsUnkIcon()): self.IsObject = True
        IsIcon = property(get_IsIcon, set_IsIcon)
        def get_IsGrass(self):
            return (self.entryType == 6)
        def set_IsGrass(self, nValue):
            if (nValue == True): self.entryType = 6
            elif(self.get_IsGrass()): self.IsObject = True
        IsGrass = property(get_IsGrass, set_IsGrass)
        def get_IsSound(self):
            return (self.entryType == 7)
        def set_IsSound(self, nValue):
            if (nValue == True): self.entryType = 7
            elif(self.get_IsSound()): self.IsObject = True
        IsSound = property(get_IsSound, set_IsSound)
        def get_IsDefault(self):
            return (self.musicType == 0)
        def set_IsDefault(self, nValue):
            if (nValue == True): self.musicType = 0
            elif(self.get_IsDefault()): self.IsPublic = True
        IsDefault = property(get_IsDefault, set_IsDefault)
        def get_IsPublic(self):
            return (self.musicType == 1)
        def set_IsPublic(self, nValue):
            if (nValue == True): self.musicType = 1
            elif(self.get_IsPublic()): self.IsDefault = True
        IsPublic = property(get_IsPublic, set_IsPublic)
        def get_IsDungeon(self):
            return (self.musicType == 2)
        def set_IsDungeon(self, nValue):
            if (nValue == True): self.musicType = 2
            elif(self.get_IsDungeon()): self.IsDefault = True
        IsDungeon = property(get_IsDungeon, set_IsDungeon)
    def newAreasElement(self):
        listIndex = CBash.CreateFIDListElement(self._CollectionIndex, self._ModName, self._recordID, 12)
        if(listIndex == -1): return None
        return self.Area(self._CollectionIndex, self._ModName, self._recordID, listIndex)
    def newEntriesElement(self):
        listIndex = CBash.CreateFIDListElement(self._CollectionIndex, self._ModName, self._recordID, 13)
        if(listIndex == -1): return None
        return self.Entry(self._CollectionIndex, self._ModName, self._recordID, listIndex)

    def get_iconPath(self):
        CBash.ReadFIDField.restype = c_char_p
        return CBash.ReadFIDField(self._CollectionIndex, self._ModName, self._recordID, 6)
    def set_iconPath(self, nValue):
        CBash.SetFIDFieldStr(self._CollectionIndex, self._ModName, self._recordID, 6, nValue)
    iconPath = property(get_iconPath, set_iconPath)
    def get_mapRed(self):
        CBash.ReadFIDField.restype = POINTER(c_ubyte)
        retValue = CBash.ReadFIDField(self._CollectionIndex, self._ModName, self._recordID, 7)
        if(retValue): return retValue.contents.value
        return None
    def set_mapRed(self, nValue):
        CBash.SetFIDFieldUC(self._CollectionIndex, self._ModName, self._recordID, 7, c_ubyte(nValue))
    mapRed = property(get_mapRed, set_mapRed)
    def get_mapGreen(self):
        CBash.ReadFIDField.restype = POINTER(c_ubyte)
        retValue = CBash.ReadFIDField(self._CollectionIndex, self._ModName, self._recordID, 8)
        if(retValue): return retValue.contents.value
        return None
    def set_mapGreen(self, nValue):
        CBash.SetFIDFieldUC(self._CollectionIndex, self._ModName, self._recordID, 8, c_ubyte(nValue))
    mapGreen = property(get_mapGreen, set_mapGreen)
    def get_mapBlue(self):
        CBash.ReadFIDField.restype = POINTER(c_ubyte)
        retValue = CBash.ReadFIDField(self._CollectionIndex, self._ModName, self._recordID, 9)
        if(retValue): return retValue.contents.value
        return None
    def set_mapBlue(self, nValue):
        CBash.SetFIDFieldUC(self._CollectionIndex, self._ModName, self._recordID, 9, c_ubyte(nValue))
    mapBlue = property(get_mapBlue, set_mapBlue)
    def get_unused1(self):
        numRecords = CBash.GetFIDFieldArraySize(self._CollectionIndex, self._ModName, self._recordID, 10)
        if(numRecords > 0):
            cRecords = POINTER(c_ubyte * numRecords)()
            CBash.GetFIDFieldArray(self._CollectionIndex, self._ModName, self._recordID, 10, byref(cRecords))
            return [cRecords.contents[x] for x in range(0, numRecords)]
        return []
    def set_unused1(self, nValue):
        CBash.SetFIDFieldR(self._CollectionIndex, self._ModName, self._recordID, 10, struct.pack('B', *nValue), 1)
    unused1 = property(get_unused1, set_unused1)
    def get_worldspace(self):
        CBash.ReadFIDField.restype = POINTER(c_uint)
        retValue = CBash.ReadFIDField(self._CollectionIndex, self._ModName, self._recordID, 11)
        if(retValue): return retValue.contents.value
        return None
    def set_worldspace(self, nValue):
        CBash.SetFIDFieldUI(self._CollectionIndex, self._ModName, self._recordID, 11, nValue)
    worldspace = property(get_worldspace, set_worldspace)
    def get_areas(self):
        numRecords = CBash.GetFIDListSize(self._CollectionIndex, self._ModName, self._recordID, 12)
        if(numRecords > 0): return [self.Area(self._CollectionIndex, self._ModName, self._recordID, x) for x in range(0, numRecords)]
        return []
    def set_areas(self, nAreas):
        diffLength = len(nAreas) - CBash.GetFIDListSize(self._CollectionIndex, self._ModName, self._recordID, 12)
        nValues = [(nArea.edgeFalloff, [(nPoint.posX, nPoint.posY) for nPoint in nArea.points]) for nArea in nAreas]
        while(diffLength < 0):
            CBash.DeleteFIDListElement(self._CollectionIndex, self._ModName, self._recordID, 12)
            diffLength += 1
        while(diffLength > 0):
            CBash.CreateFIDListElement(self._CollectionIndex, self._ModName, self._recordID, 12)
            diffLength -= 1
        for oArea, nValue in zip(self.areas, nValues):
            oArea.edgeFalloff = nValue[0]
            diffLength = len(nValue[1]) - CBash.GetFIDListX2Size(self._CollectionIndex, self._ModName, self._recordID, 12, oArea._listIndex, 2)
            while(diffLength < 0):
                CBash.DeleteFIDListX2Element(self._CollectionIndex, self._ModName, self._recordID, 12, oArea._listIndex, 2)
                diffLength += 1
            while(diffLength > 0):
                CBash.CreateFIDListX2Element(self._CollectionIndex, self._ModName, self._recordID, 12, oArea._listIndex, 2)
                diffLength -= 1
            for oPoint, posValue in zip(oArea.points, nValue[1]):
                oPoint.posX, oPoint.posY = posValue
    areas = property(get_areas, set_areas)
    def get_entries(self):
        numRecords = CBash.GetFIDListSize(self._CollectionIndex, self._ModName, self._recordID, 13)
        if(numRecords > 0): return [self.Entry(self._CollectionIndex, self._ModName, self._recordID, x) for x in range(0, numRecords)]
        return []
    def set_entries(self, nEntries):
        diffLength = len(nEntries) - CBash.GetFIDListSize(self._CollectionIndex, self._ModName, self._recordID, 13)
        nValues = [(nEntry.entryType, nEntry.flags, nEntry.priority, nEntry.unused1,
                    [(nObject.objectId, nObject.subField, nObject.unused1, nObject.density, 
                      nObject.clustering, nObject.minSlope, nObject.maxSlope, nObject.flags, 
                      nObject.radiusWRTParent, nObject.radius, nObject.unk1, nObject.maxHeight,  
                      nObject.sink, nObject.sinkVar, nObject.sizeVar, nObject.angleVarX, 
                      nObject.angleVarY, nObject.angleVarZ, nObject.unused2, nObject.unk2) for nObject in nEntry.objects],
                    nEntry.mapName, nEntry.iconPath,
                    [(nGrass.grass, nGrass.unk1) for nGrass in nEntry.grasses],
                    nEntry.musicType,
                    [(nSound.sound, nSound.flags, nSound.chance) for nSound in nEntry.sounds],
                    [(nWeather.weather, nWeather.chance) for nWeather in nEntry.weathers]) for nEntry in nEntries]
        while(diffLength < 0):
            CBash.DeleteFIDListElement(self._CollectionIndex, self._ModName, self._recordID, 13)
            diffLength += 1
        while(diffLength > 0):
            CBash.CreateFIDListElement(self._CollectionIndex, self._ModName, self._recordID, 13)
            diffLength -= 1
        for oEntry, nValue in zip(self.entries, nValues):
            nEntry.entryType = nValue[0]
            nEntry.flags = nValue[1]
            nEntry.priority = nValue[2]
            nEntry.unused1 = nValue[3]
            diffLength = len(nValue[4]) - CBash.GetFIDListX2Size(self._CollectionIndex, self._ModName, self._recordID, 13, oEntry._listIndex, 5)
            while(diffLength < 0):
                CBash.DeleteFIDListX2Element(self._CollectionIndex, self._ModName, self._recordID, 13, oEntry._listIndex, 5)
                diffLength += 1
            while(diffLength > 0):
                CBash.CreateFIDListX2Element(self._CollectionIndex, self._ModName, self._recordID, 13, oEntry._listIndex, 5)
                diffLength -= 1
            for oObject, objValue in zip(oEntry.objects, nValue[4]):
                oObject.objectId, oObject.subField, oObject.unused1, oObject.density, 
                oObject.clustering, oObject.minSlope, oObject.maxSlope, oObject.flags, 
                oObject.radiusWRTParent, oObject.radius, oObject.unk1, oObject.maxHeight,  
                oObject.sink, oObject.sinkVar, oObject.sizeVar, oObject.angleVarX, 
                oObject.angleVarY, oObject.angleVarZ, oObject.unused2, oObject.unk2 = objValue
            nEntry.mapName = nValue[5]
            nEntry.iconPath = nValue[6]
            diffLength = len(nValue[7]) - CBash.GetFIDListX2Size(self._CollectionIndex, self._ModName, self._recordID, 13, oEntry._listIndex, 8)
            while(diffLength < 0):
                CBash.DeleteFIDListX2Element(self._CollectionIndex, self._ModName, self._recordID, 13, oEntry._listIndex, 8)
                diffLength += 1
            while(diffLength > 0):
                CBash.CreateFIDListX2Element(self._CollectionIndex, self._ModName, self._recordID, 13, oEntry._listIndex, 8)
                diffLength -= 1
            for oGrass, grassValue in zip(oEntry.grasses, nValue[7]):
                oGrass.grass, oGrass.unk1 = grassValue
            nEntry.musicType = nValue[8]
            diffLength = len(nValue[9]) - CBash.GetFIDListX2Size(self._CollectionIndex, self._ModName, self._recordID, 13, oEntry._listIndex, 10)
            while(diffLength < 0):
                CBash.DeleteFIDListX2Element(self._CollectionIndex, self._ModName, self._recordID, 13, oEntry._listIndex, 10)
                diffLength += 1
            while(diffLength > 0):
                CBash.CreateFIDListX2Element(self._CollectionIndex, self._ModName, self._recordID, 13, oEntry._listIndex, 10)
                diffLength -= 1
            for oSound, soundValue in zip(oEntry.sounds, nValue[9]):
                oSound.sound, oSound.flags, oSound.chance = soundValue
            diffLength = len(nValue[10]) - CBash.GetFIDListX2Size(self._CollectionIndex, self._ModName, self._recordID, 13, oEntry._listIndex, 11)
            while(diffLength < 0):
                CBash.DeleteFIDListX2Element(self._CollectionIndex, self._ModName, self._recordID, 13, oEntry._listIndex, 11)
                diffLength += 1
            while(diffLength > 0):
                CBash.CreateFIDListX2Element(self._CollectionIndex, self._ModName, self._recordID, 13, oEntry._listIndex, 11)
                diffLength -= 1
            for oWeather, weatherValue in zip(oEntry.weathers, nValue[10]):
                oWeather.weather, oWeather.chance = weatherValue                  
    entries = property(get_entries, set_entries)
    
class CELLRecord(BaseRecord):
    def CopyAsOverride(self, target, isWorldCell=False):
        if isinstance(target, ModFile):
            FID = CBash.CopyCELLRecord(self._CollectionIndex, self._ModName, self._recordID, target._ModName, 0, c_bool(True), c_bool(False))
        else:
            FID = CBash.CopyCELLRecord(self._CollectionIndex, self._ModName, self._recordID, target._ModName, target._recordID, c_bool(True), c_bool(isWorldCell))
        if(FID): return CELLRecord(self._CollectionIndex, target._ModName, FID)
        return None
    def CopyAsNew(self, target, isWorldCell=False):
        if isinstance(target, ModFile):
            FID = CBash.CopyCELLRecord(self._CollectionIndex, self._ModName, self._recordID, target._ModName, 0, c_bool(False), c_bool(False))
        else:
            FID = CBash.CopyCELLRecord(self._CollectionIndex, self._ModName, self._recordID, target._ModName, target._recordID, c_bool(False), c_bool(isWorldCell))
        if(FID): return CELLRecord(self._CollectionIndex, target._ModName, FID)
        return None
    def DeleteRecord(self, parent=None):
        if(parent == None):
            CBash.DeleteRecord(self._CollectionIndex, self._ModName, self._recordID, 0)
        else:
            CBash.DeleteRecord(self._CollectionIndex, self._ModName, self._recordID, parent._recordID)
        return
    def createACHRRecord(self):
        FID = CBash.CreateACHRRecord(self._CollectionIndex, self._ModName, self._recordID)
        if(FID): return ACHRRecord(self._CollectionIndex, self._ModName, FID)
        return None
    def createACRERecord(self):
        FID = CBash.CreateACRERecord(self._CollectionIndex, self._ModName, self._recordID)
        if(FID): return ACRERecord(self._CollectionIndex, self._ModName, FID)
        return None
    def createREFRRecord(self):
        FID = CBash.CreateREFRRecord(self._CollectionIndex, self._ModName, self._recordID)
        if(FID): return REFRRecord(self._CollectionIndex, self._ModName, FID)
        return None
    def createPGRDRecord(self):
        FID = CBash.CreatePGRDRecord(self._CollectionIndex, self._ModName, self._recordID)
        if(FID): return PGRDRecord(self._CollectionIndex, self._ModName, FID)
        return None
    def createLANDRecord(self):
        FID = CBash.CreateLANDRecord(self._CollectionIndex, self._ModName, self._recordID)
        if(FID): return LANDRecord(self._CollectionIndex, self._ModName, FID, self._recordID)
        return None
    def get_full(self):
        CBash.ReadFIDField.restype = c_char_p
        return CBash.ReadFIDField(self._CollectionIndex, self._ModName, self._recordID, 6)
    def set_full(self, nValue):
        CBash.SetFIDFieldStr(self._CollectionIndex, self._ModName, self._recordID, 6, nValue)
    full = property(get_full, set_full)
    def get_flags(self):
        CBash.ReadFIDField.restype = POINTER(c_ubyte)
        retValue = CBash.ReadFIDField(self._CollectionIndex, self._ModName, self._recordID, 7)
        if(retValue): return retValue.contents.value
        return None
    def set_flags(self, nValue):
        CBash.SetFIDFieldUC(self._CollectionIndex, self._ModName, self._recordID, 7, c_ubyte(nValue))
    flags = property(get_flags, set_flags)
    def get_ambientRed(self):
        CBash.ReadFIDField.restype = POINTER(c_ubyte)
        retValue = CBash.ReadFIDField(self._CollectionIndex, self._ModName, self._recordID, 8)
        if(retValue): return retValue.contents.value
        return None
    def set_ambientRed(self, nValue):
        CBash.SetFIDFieldUC(self._CollectionIndex, self._ModName, self._recordID, 8, c_ubyte(nValue))
    ambientRed = property(get_ambientRed, set_ambientRed)
    def get_ambientGreen(self):
        CBash.ReadFIDField.restype = POINTER(c_ubyte)
        retValue = CBash.ReadFIDField(self._CollectionIndex, self._ModName, self._recordID, 9)
        if(retValue): return retValue.contents.value
        return None
    def set_ambientGreen(self, nValue):
        CBash.SetFIDFieldUC(self._CollectionIndex, self._ModName, self._recordID, 9, c_ubyte(nValue))
    ambientGreen = property(get_ambientGreen, set_ambientGreen)
    def get_ambientBlue(self):
        CBash.ReadFIDField.restype = POINTER(c_ubyte)
        retValue = CBash.ReadFIDField(self._CollectionIndex, self._ModName, self._recordID, 10)
        if(retValue): return retValue.contents.value
        return None
    def set_ambientBlue(self, nValue):
        CBash.SetFIDFieldUC(self._CollectionIndex, self._ModName, self._recordID, 10, c_ubyte(nValue))
    ambientBlue = property(get_ambientBlue, set_ambientBlue)
    def get_unused1(self):
        numRecords = CBash.GetFIDFieldArraySize(self._CollectionIndex, self._ModName, self._recordID, 11)
        if(numRecords > 0):
            cRecords = POINTER(c_ubyte * numRecords)()
            CBash.GetFIDFieldArray(self._CollectionIndex, self._ModName, self._recordID, 11, byref(cRecords))
            return [cRecords.contents[x] for x in range(0, numRecords)]
        return []
    def set_unused1(self, nValue):
        CBash.SetFIDFieldR(self._CollectionIndex, self._ModName, self._recordID, 11, struct.pack('B', *nValue), 1)
    unused1 = property(get_unused1, set_unused1)
    def get_directionalRed(self):
        CBash.ReadFIDField.restype = POINTER(c_ubyte)
        retValue = CBash.ReadFIDField(self._CollectionIndex, self._ModName, self._recordID, 12)
        if(retValue): return retValue.contents.value
        return None
    def set_directionalRed(self, nValue):
        CBash.SetFIDFieldUC(self._CollectionIndex, self._ModName, self._recordID, 12, c_ubyte(nValue))
    directionalRed = property(get_directionalRed, set_directionalRed)
    def get_directionalGreen(self):
        CBash.ReadFIDField.restype = POINTER(c_ubyte)
        retValue = CBash.ReadFIDField(self._CollectionIndex, self._ModName, self._recordID, 13)
        if(retValue): return retValue.contents.value
        return None
    def set_directionalGreen(self, nValue):
        CBash.SetFIDFieldUC(self._CollectionIndex, self._ModName, self._recordID, 13, c_ubyte(nValue))
    directionalGreen = property(get_directionalGreen, set_directionalGreen)
    def get_directionalBlue(self):
        CBash.ReadFIDField.restype = POINTER(c_ubyte)
        retValue = CBash.ReadFIDField(self._CollectionIndex, self._ModName, self._recordID, 14)
        if(retValue): return retValue.contents.value
        return None
    def set_directionalBlue(self, nValue):
        CBash.SetFIDFieldUC(self._CollectionIndex, self._ModName, self._recordID, 14, c_ubyte(nValue))
    directionalBlue = property(get_directionalBlue, set_directionalBlue)
    def get_unused2(self):
        numRecords = CBash.GetFIDFieldArraySize(self._CollectionIndex, self._ModName, self._recordID, 15)
        if(numRecords > 0):
            cRecords = POINTER(c_ubyte * numRecords)()
            CBash.GetFIDFieldArray(self._CollectionIndex, self._ModName, self._recordID, 15, byref(cRecords))
            return [cRecords.contents[x] for x in range(0, numRecords)]
        return []
    def set_unused2(self, nValue):
        CBash.SetFIDFieldR(self._CollectionIndex, self._ModName, self._recordID, 15, struct.pack('B', *nValue), 1)
    unused2 = property(get_unused2, set_unused2)
    def get_fogRed(self):
        CBash.ReadFIDField.restype = POINTER(c_ubyte)
        retValue = CBash.ReadFIDField(self._CollectionIndex, self._ModName, self._recordID, 16)
        if(retValue): return retValue.contents.value
        return None
    def set_fogRed(self, nValue):
        CBash.SetFIDFieldUC(self._CollectionIndex, self._ModName, self._recordID, 16, c_ubyte(nValue))
    fogRed = property(get_fogRed, set_fogRed)
    def get_fogGreen(self):
        CBash.ReadFIDField.restype = POINTER(c_ubyte)
        retValue = CBash.ReadFIDField(self._CollectionIndex, self._ModName, self._recordID, 17)
        if(retValue): return retValue.contents.value
        return None
    def set_fogGreen(self, nValue):
        CBash.SetFIDFieldUC(self._CollectionIndex, self._ModName, self._recordID, 17, c_ubyte(nValue))
    fogGreen = property(get_fogGreen, set_fogGreen)
    def get_fogBlue(self):
        CBash.ReadFIDField.restype = POINTER(c_ubyte)
        retValue = CBash.ReadFIDField(self._CollectionIndex, self._ModName, self._recordID, 18)
        if(retValue): return retValue.contents.value
        return None
    def set_fogBlue(self, nValue):
        CBash.SetFIDFieldUC(self._CollectionIndex, self._ModName, self._recordID, 18, c_ubyte(nValue))
    fogBlue = property(get_fogBlue, set_fogBlue)
    def get_unused3(self):
        numRecords = CBash.GetFIDFieldArraySize(self._CollectionIndex, self._ModName, self._recordID, 19)
        if(numRecords > 0):
            cRecords = POINTER(c_ubyte * numRecords)()
            CBash.GetFIDFieldArray(self._CollectionIndex, self._ModName, self._recordID, 19, byref(cRecords))
            return [cRecords.contents[x] for x in range(0, numRecords)]
        return []
    def set_unused3(self, nValue):
        CBash.SetFIDFieldR(self._CollectionIndex, self._ModName, self._recordID, 19, struct.pack('B', *nValue), 1)
    unused3 = property(get_unused3, set_unused3)
    def get_fogNear(self):
        CBash.ReadFIDField.restype = POINTER(c_float)
        retValue = CBash.ReadFIDField(self._CollectionIndex, self._ModName, self._recordID, 20)
        if(retValue): return retValue.contents.value
        return None
    def set_fogNear(self, nValue):
        CBash.SetFIDFieldF(self._CollectionIndex, self._ModName, self._recordID, 20, c_float(nValue))
    fogNear = property(get_fogNear, set_fogNear)
    def get_fogFar(self):
        CBash.ReadFIDField.restype = POINTER(c_float)
        retValue = CBash.ReadFIDField(self._CollectionIndex, self._ModName, self._recordID, 21)
        if(retValue): return retValue.contents.value
        return None
    def set_fogFar(self, nValue):
        CBash.SetFIDFieldF(self._CollectionIndex, self._ModName, self._recordID, 21, c_float(nValue))
    fogFar = property(get_fogFar, set_fogFar)
    def get_directionalXY(self):
        CBash.ReadFIDField.restype = POINTER(c_int)
        retValue = CBash.ReadFIDField(self._CollectionIndex, self._ModName, self._recordID, 22)
        if(retValue): return retValue.contents.value
        return None
    def set_directionalXY(self, nValue):
        CBash.SetFIDFieldI(self._CollectionIndex, self._ModName, self._recordID, 22, nValue)
    directionalXY = property(get_directionalXY, set_directionalXY)
    def get_directionalZ(self):
        CBash.ReadFIDField.restype = POINTER(c_int)
        retValue = CBash.ReadFIDField(self._CollectionIndex, self._ModName, self._recordID, 23)
        if(retValue): return retValue.contents.value
        return None
    def set_directionalZ(self, nValue):
        CBash.SetFIDFieldI(self._CollectionIndex, self._ModName, self._recordID, 23, nValue)
    directionalZ = property(get_directionalZ, set_directionalZ)
    def get_directionalFade(self):
        CBash.ReadFIDField.restype = POINTER(c_float)
        retValue = CBash.ReadFIDField(self._CollectionIndex, self._ModName, self._recordID, 24)
        if(retValue): return retValue.contents.value
        return None
    def set_directionalFade(self, nValue):
        CBash.SetFIDFieldF(self._CollectionIndex, self._ModName, self._recordID, 24, c_float(nValue))
    directionalFade = property(get_directionalFade, set_directionalFade)
    def get_fogClip(self):
        CBash.ReadFIDField.restype = POINTER(c_float)
        retValue = CBash.ReadFIDField(self._CollectionIndex, self._ModName, self._recordID, 25)
        if(retValue): return retValue.contents.value
        return None
    def set_fogClip(self, nValue):
        CBash.SetFIDFieldF(self._CollectionIndex, self._ModName, self._recordID, 25, c_float(nValue))
    fogClip = property(get_fogClip, set_fogClip)
    def get_music(self):
        CBash.ReadFIDField.restype = POINTER(c_ubyte)
        retValue = CBash.ReadFIDField(self._CollectionIndex, self._ModName, self._recordID, 26)
        if(retValue): return retValue.contents.value
        return None
    def set_music(self, nValue):
        CBash.SetFIDFieldUC(self._CollectionIndex, self._ModName, self._recordID, 26, c_ubyte(nValue))
    music = property(get_music, set_music)
    def get_owner(self):
        CBash.ReadFIDField.restype = POINTER(c_uint)
        retValue = CBash.ReadFIDField(self._CollectionIndex, self._ModName, self._recordID, 27)
        if(retValue): return retValue.contents.value
        return None
    def set_owner(self, nValue):
        CBash.SetFIDFieldUI(self._CollectionIndex, self._ModName, self._recordID, 27, nValue)
    owner = property(get_owner, set_owner)
    def get_rank(self):
        CBash.ReadFIDField.restype = POINTER(c_int)
        retValue = CBash.ReadFIDField(self._CollectionIndex, self._ModName, self._recordID, 28)
        if(retValue): return retValue.contents.value
        return None
    def set_rank(self, nValue):
        CBash.SetFIDFieldI(self._CollectionIndex, self._ModName, self._recordID, 28, nValue)
    rank = property(get_rank, set_rank)
    def get_globalVariable(self):
        CBash.ReadFIDField.restype = POINTER(c_uint)
        retValue = CBash.ReadFIDField(self._CollectionIndex, self._ModName, self._recordID, 29)
        if(retValue): return retValue.contents.value
        return None
    def set_globalVariable(self, nValue):
        CBash.SetFIDFieldUI(self._CollectionIndex, self._ModName, self._recordID, 29, nValue)
    globalVariable = property(get_globalVariable, set_globalVariable)
    def get_climate(self):
        CBash.ReadFIDField.restype = POINTER(c_uint)
        retValue = CBash.ReadFIDField(self._CollectionIndex, self._ModName, self._recordID, 30)
        if(retValue): return retValue.contents.value
        return None
    def set_climate(self, nValue):
        CBash.SetFIDFieldUI(self._CollectionIndex, self._ModName, self._recordID, 30, nValue)
    climate = property(get_climate, set_climate)
    def get_waterHeight(self):
        CBash.ReadFIDField.restype = POINTER(c_float)
        retValue = CBash.ReadFIDField(self._CollectionIndex, self._ModName, self._recordID, 31)
        if(retValue): return retValue.contents.value
        return None
    def set_waterHeight(self, nValue):
        CBash.SetFIDFieldF(self._CollectionIndex, self._ModName, self._recordID, 31, c_float(nValue))
    waterHeight = property(get_waterHeight, set_waterHeight)
    def get_regions(self):
        numRecords = CBash.GetFIDFieldArraySize(self._CollectionIndex, self._ModName, self._recordID, 32)
        if(numRecords > 0):
            cRecords = (POINTER(c_uint) * numRecords)()
            CBash.GetFIDFieldArray(self._CollectionIndex, self._ModName, self._recordID, 32, byref(cRecords))
            return [cRecords[x].contents.value for x in range(0, numRecords)]
        return []
    def set_regions(self, nValue):
        CBash.SetFIDFieldUIA(self._CollectionIndex, self._ModName, self._recordID, 32, struct.pack('I' * len(nValue), *nValue), len(nValue))
    regions = property(get_regions, set_regions)
    def get_posX(self):
        CBash.ReadFIDField.restype = POINTER(c_int)
        retValue = CBash.ReadFIDField(self._CollectionIndex, self._ModName, self._recordID, 33)
        if(retValue): return retValue.contents.value
        return None
    def set_posX(self, nValue):
        CBash.SetFIDFieldI(self._CollectionIndex, self._ModName, self._recordID, 33, nValue)
    posX = property(get_posX, set_posX)
    def get_posY(self):
        CBash.ReadFIDField.restype = POINTER(c_int)
        retValue = CBash.ReadFIDField(self._CollectionIndex, self._ModName, self._recordID, 34)
        if(retValue): return retValue.contents.value
        return None
    def set_posY(self, nValue):
        CBash.SetFIDFieldI(self._CollectionIndex, self._ModName, self._recordID, 34, nValue)
    posY = property(get_posY, set_posY)
    def get_water(self):
        CBash.ReadFIDField.restype = POINTER(c_uint)
        retValue = CBash.ReadFIDField(self._CollectionIndex, self._ModName, self._recordID, 35)
        if(retValue): return retValue.contents.value
        return None
    def set_water(self, nValue):
        CBash.SetFIDFieldUI(self._CollectionIndex, self._ModName, self._recordID, 35, nValue)
    water = property(get_water, set_water)
    @property
    def ACHR(self):
        numSubRecords = CBash.GetFIDFieldArraySize(self._CollectionIndex, self._ModName, self._recordID, 36)
        if(numSubRecords > 0):
            cRecords = (POINTER(c_uint) * numSubRecords)()
            CBash.GetFIDFieldArray(self._CollectionIndex, self._ModName, self._recordID, 36, byref(cRecords))
            return [ACHRRecord(self._CollectionIndex, self._ModName, x.contents.value) for x in cRecords]
        return []
    @property
    def ACRE(self):
        numSubRecords = CBash.GetFIDFieldArraySize(self._CollectionIndex, self._ModName, self._recordID, 37)
        if(numSubRecords > 0):
            cRecords = (POINTER(c_uint) * numSubRecords)()
            CBash.GetFIDFieldArray(self._CollectionIndex, self._ModName, self._recordID, 37, byref(cRecords))
            return [ACRERecord(self._CollectionIndex, self._ModName, x.contents.value) for x in cRecords]
        return []
    @property
    def REFR(self):
        numSubRecords = CBash.GetFIDFieldArraySize(self._CollectionIndex, self._ModName, self._recordID, 38)
        if(numSubRecords > 0):
            cRecords = (POINTER(c_uint) * numSubRecords)()
            CBash.GetFIDFieldArray(self._CollectionIndex, self._ModName, self._recordID, 38, byref(cRecords))
            return [REFRRecord(self._CollectionIndex, self._ModName, x.contents.value) for x in cRecords]
        return []
    def get_PGRD(self):
        CBash.ReadFIDField.restype = POINTER(c_uint)
        retValue = CBash.ReadFIDField(self._CollectionIndex, self._ModName, self._recordID, 39)
        if(retValue): return PGRDRecord(self._CollectionIndex, self._ModName, retValue.contents.value)
        return None
    def set_PGRD(self, nPGRD):
        if(nPGRD == None and self.PGRD != None):
            self.PGRD.DeleteRecord()
            return
        curPGRD = self.PGRD
        if(curPGRD == None):
            curPGRD = self.createPGRDRecord()
        curPGRD.count = nPGRD.count
        curPGRD.PGRP = nPGRD.PGRP
        curPGRD.PGAG = nPGRD.PGAG
        curPGRD.PGRR = nPGRD.PGRR
        curPGRD.PGRI = nPGRD.PGRI
        curPGRD.PGRL = nPGRD.PGRL
    PGRD = property(get_PGRD, set_PGRD)
    def get_LAND(self):
        CBash.ReadFIDField.restype = POINTER(c_uint)
        retValue = CBash.ReadFIDField(self._CollectionIndex, self._ModName, self._recordID, 40)
        if(retValue): return LANDRecord(self._CollectionIndex, self._ModName, retValue.contents.value)
        return None
    def set_LAND(self, nLAND):
        if(nLAND == None and self.LAND != None):
            self.LAND.DeleteRecord()
            return
        curLAND = self.LAND
        if(curLAND == None):
            curLAND = self.createLANDRecord()
        curLAND.data = nLAND.data
        curLAND.normals = nLAND.normals
        curLAND.heights = nLAND.heights
        curLAND.heightOffset = nLAND.heightOffset
        curLAND.unused1 = nLAND.unused1
        curLAND.colors = nLAND.colors
        curLAND.baseTextures = nLAND.baseTextures
        curLAND.alphaLayers = nLAND.alphaLayers
        curLAND.vertexTextures = nLAND.vertexTextures
    LAND = property(get_LAND, set_LAND)
    def get_IsInterior(self):
        return (self.flags & 0x00000001) != 0
    def set_IsInterior(self, nValue):
        if (nValue == True): self.flags |= 0x00000001
        else: self.flags &= ~0x00000001
    IsInterior = property(get_IsInterior, set_IsInterior)
    def get_HasWater(self):
        return (self.flags & 0x00000002) != 0
    def set_HasWater(self, nValue):
        if (nValue == True): self.flags |= 0x00000002
        else: self.flags &= ~0x00000002
    HasWater = property(get_HasWater, set_HasWater)
    def get_InvertFastTravel(self):
        return (self.flags & 0x00000004) != 0
    def set_InvertFastTravel(self, nValue):
        if (nValue == True): self.flags |= 0x00000004
        else: self.flags &= ~0x00000004
    InvertFastTravel = property(get_InvertFastTravel, set_InvertFastTravel)
    def get_ForceHideLand(self):
        return (self.flags & 0x00000008) != 0
    def set_ForceHideLand(self, nValue):
        if (nValue == True): self.flags |= 0x00000008
        else: self.flags &= ~0x00000008
    ForceHideLand = property(get_ForceHideLand, set_ForceHideLand)
    def get_PublicPlace(self):
        return (self.flags & 0x00000020) != 0
    def set_PublicPlace(self, nValue):
        if (nValue == True): self.flags |= 0x00000020
        else: self.flags &= ~0x00000020
    PublicPlace = property(get_PublicPlace, set_PublicPlace)
    def get_HandChanged(self):
        return (self.flags & 0x00000040) != 0
    def set_HandChanged(self, nValue):
        if (nValue == True): self.flags |= 0x00000040
        else: self.flags &= ~0x00000040
    HandChanged = property(get_HandChanged, set_HandChanged)
    def get_BehaveLikeExterior(self):
        return (self.flags & 0x00000080) != 0
    def set_BehaveLikeExterior(self, nValue):
        if (nValue == True): self.flags |= 0x00000080
        else: self.flags &= ~0x00000080
    BehaveLikeExterior = property(get_BehaveLikeExterior, set_BehaveLikeExterior)
    def get_IsDefault(self):
        return (self.music == 0)
    def set_IsDefault(self, nValue):
        if (nValue == True): self.music = 0
        elif(self.get_IsDefault()): self.IsPublic = True
    IsDefault = property(get_IsDefault, set_IsDefault)
    def get_IsPublic(self):
        return (self.music == 1)
    def set_IsPublic(self, nValue):
        if (nValue == True): self.music = 1
        elif(self.get_IsPublic()): self.IsDefault = True
    IsPublic = property(get_IsPublic, set_IsPublic)
    def get_IsDungeon(self):
        return (self.music == 2)
    def set_IsDungeon(self, nValue):
        if (nValue == True): self.music = 2
        elif(self.get_IsDungeon()): self.IsDefault = True
    IsDungeon = property(get_IsDungeon, set_IsDungeon)
    
class ACHRRecord(BaseRecord):
    def CopyAsOverride(self, targetCELL):
        FID = CBash.CopyACHRRecord(self._CollectionIndex, self._ModName, self._recordID, targetCELL._ModName, targetCELL._recordID, c_bool(True))
        if(FID): return ACHRRecord(self._CollectionIndex, targetCELL._ModName, FID)
        return None
    def CopyAsNew(self, targetCELL):
        FID = CBash.CopyACHRRecord(self._CollectionIndex, self._ModName, self._recordID, targetCELL._ModName, targetCELL._recordID, c_bool(False))
        if(FID): return ACHRRecord(self._CollectionIndex, targetCELL._ModName, FID)
        return None
    def DeleteRecord(self, parent):
        CBash.DeleteRecord(self._CollectionIndex, self._ModName, self._recordID, parent._recordID)
        return
    def get_base(self):
        CBash.ReadFIDField.restype = POINTER(c_uint)
        retValue = CBash.ReadFIDField(self._CollectionIndex, self._ModName, self._recordID, 6)
        if(retValue): return retValue.contents.value
        return None
    def set_base(self, nValue):
        CBash.SetFIDFieldUI(self._CollectionIndex, self._ModName, self._recordID, 6, nValue)
    base = property(get_base, set_base)
    def get_unknownXPCIFormID(self):
        CBash.ReadFIDField.restype = POINTER(c_uint)
        retValue = CBash.ReadFIDField(self._CollectionIndex, self._ModName, self._recordID, 7)
        if(retValue): return retValue.contents.value
        return None
    def set_unknownXPCIFormID(self, nValue):
        CBash.SetFIDFieldUI(self._CollectionIndex, self._ModName, self._recordID, 7, nValue)
    unknownXPCIFormID = property(get_unknownXPCIFormID, set_unknownXPCIFormID)
    def get_unknownXPCIString(self):
        CBash.ReadFIDField.restype = c_char_p
        return CBash.ReadFIDField(self._CollectionIndex, self._ModName, self._recordID, 8)
    def set_unknownXPCIString(self, nValue):
        CBash.SetFIDFieldStr(self._CollectionIndex, self._ModName, self._recordID, 8, nValue)
    unknownXPCIString = property(get_unknownXPCIString, set_unknownXPCIString)
    def get_lod1(self):
        CBash.ReadFIDField.restype = POINTER(c_float)
        retValue = CBash.ReadFIDField(self._CollectionIndex, self._ModName, self._recordID, 9)
        if(retValue): return retValue.contents.value
        return None
    def set_lod1(self, nValue):
        CBash.SetFIDFieldF(self._CollectionIndex, self._ModName, self._recordID, 9, c_float(nValue))
    lod1 = property(get_lod1, set_lod1)
    def get_lod2(self):
        CBash.ReadFIDField.restype = POINTER(c_float)
        retValue = CBash.ReadFIDField(self._CollectionIndex, self._ModName, self._recordID, 10)
        if(retValue): return retValue.contents.value
        return None
    def set_lod2(self, nValue):
        CBash.SetFIDFieldF(self._CollectionIndex, self._ModName, self._recordID, 10, c_float(nValue))
    lod2 = property(get_lod2, set_lod2)
    def get_lod3(self):
        CBash.ReadFIDField.restype = POINTER(c_float)
        retValue = CBash.ReadFIDField(self._CollectionIndex, self._ModName, self._recordID, 11)
        if(retValue): return retValue.contents.value
        return None
    def set_lod3(self, nValue):
        CBash.SetFIDFieldF(self._CollectionIndex, self._ModName, self._recordID, 11, c_float(nValue))
    lod3 = property(get_lod3, set_lod3)
    def get_parent(self):
        CBash.ReadFIDField.restype = POINTER(c_uint)
        retValue = CBash.ReadFIDField(self._CollectionIndex, self._ModName, self._recordID, 12)
        if(retValue): return retValue.contents.value
        return None
    def set_parent(self, nValue):
        CBash.SetFIDFieldUI(self._CollectionIndex, self._ModName, self._recordID, 12, nValue)
    parent = property(get_parent, set_parent)
    def get_parentFlags(self):
        CBash.ReadFIDField.restype = POINTER(c_ubyte)
        retValue = CBash.ReadFIDField(self._CollectionIndex, self._ModName, self._recordID, 13)
        if(retValue): return retValue.contents.value
        return None
    def set_parentFlags(self, nValue):
        CBash.SetFIDFieldUC(self._CollectionIndex, self._ModName, self._recordID, 13, c_ubyte(nValue))
    parentFlags = property(get_parentFlags, set_parentFlags)
    def get_unused1(self):
        numRecords = CBash.GetFIDFieldArraySize(self._CollectionIndex, self._ModName, self._recordID, 14)
        if(numRecords > 0):
            cRecords = POINTER(c_ubyte * numRecords)()
            CBash.GetFIDFieldArray(self._CollectionIndex, self._ModName, self._recordID, 14, byref(cRecords))
            return [cRecords.contents[x] for x in range(0, numRecords)]
        return []
    def set_unused1(self, nValue):
        CBash.SetFIDFieldR(self._CollectionIndex, self._ModName, self._recordID, 14, struct.pack('3B', *nValue), 3)
    unused1 = property(get_unused1, set_unused1)
    def get_merchantContainer(self):
        CBash.ReadFIDField.restype = POINTER(c_uint)
        retValue = CBash.ReadFIDField(self._CollectionIndex, self._ModName, self._recordID, 15)
        if(retValue): return retValue.contents.value
        return None
    def set_merchantContainer(self, nValue):
        CBash.SetFIDFieldUI(self._CollectionIndex, self._ModName, self._recordID, 15, nValue)
    merchantContainer = property(get_merchantContainer, set_merchantContainer)
    def get_horse(self):
        CBash.ReadFIDField.restype = POINTER(c_uint)
        retValue = CBash.ReadFIDField(self._CollectionIndex, self._ModName, self._recordID, 16)
        if(retValue): return retValue.contents.value
        return None
    def set_horse(self, nValue):
        CBash.SetFIDFieldUI(self._CollectionIndex, self._ModName, self._recordID, 16, nValue)
    horse = property(get_horse, set_horse)
    def get_xrgd_p(self):
        numRecords = CBash.GetFIDFieldArraySize(self._CollectionIndex, self._ModName, self._recordID, 17)
        if(numRecords > 0):
            cRecords = POINTER(c_ubyte * numRecords)()
            CBash.GetFIDFieldArray(self._CollectionIndex, self._ModName, self._recordID, 17, byref(cRecords))
            return [cRecords.contents[x] for x in range(0, numRecords)]
        return []
    def set_xrgd_p(self, nValue):
        length = len(nValue)
        CBash.SetFIDFieldR(self._CollectionIndex, self._ModName, self._recordID, 17, struct.pack('B' * length, *nValue), length)
    xrgd_p = property(get_xrgd_p, set_xrgd_p)
    def get_scale(self):
        CBash.ReadFIDField.restype = POINTER(c_float)
        retValue = CBash.ReadFIDField(self._CollectionIndex, self._ModName, self._recordID, 18)
        if(retValue): return retValue.contents.value
        return None
    def set_scale(self, nValue):
        CBash.SetFIDFieldF(self._CollectionIndex, self._ModName, self._recordID, 18, c_float(nValue))
    scale = property(get_scale, set_scale)
    def get_posX(self):
        CBash.ReadFIDField.restype = POINTER(c_float)
        retValue = CBash.ReadFIDField(self._CollectionIndex, self._ModName, self._recordID, 19)
        if(retValue): return retValue.contents.value
        return None
    def set_posX(self, nValue):
        CBash.SetFIDFieldF(self._CollectionIndex, self._ModName, self._recordID, 19, c_float(nValue))
    posX = property(get_posX, set_posX)
    def get_posY(self):
        CBash.ReadFIDField.restype = POINTER(c_float)
        retValue = CBash.ReadFIDField(self._CollectionIndex, self._ModName, self._recordID, 20)
        if(retValue): return retValue.contents.value
        return None
    def set_posY(self, nValue):
        CBash.SetFIDFieldF(self._CollectionIndex, self._ModName, self._recordID, 20, c_float(nValue))
    posY = property(get_posY, set_posY)
    def get_posZ(self):
        CBash.ReadFIDField.restype = POINTER(c_float)
        retValue = CBash.ReadFIDField(self._CollectionIndex, self._ModName, self._recordID, 21)
        if(retValue): return retValue.contents.value
        return None
    def set_posZ(self, nValue):
        CBash.SetFIDFieldF(self._CollectionIndex, self._ModName, self._recordID, 21, c_float(nValue))
    posZ = property(get_posZ, set_posZ)
    def get_rotX(self):
        CBash.ReadFIDField.restype = POINTER(c_float)
        retValue = CBash.ReadFIDField(self._CollectionIndex, self._ModName, self._recordID, 22)
        if(retValue): return retValue.contents.value
        return None
    def set_rotX(self, nValue):
        CBash.SetFIDFieldF(self._CollectionIndex, self._ModName, self._recordID, 22, c_float(nValue))
    rotX = property(get_rotX, set_rotX)
    def get_rotY(self):
        CBash.ReadFIDField.restype = POINTER(c_float)
        retValue = CBash.ReadFIDField(self._CollectionIndex, self._ModName, self._recordID, 23)
        if(retValue): return retValue.contents.value
        return None
    def set_rotY(self, nValue):
        CBash.SetFIDFieldF(self._CollectionIndex, self._ModName, self._recordID, 23, c_float(nValue))
    rotY = property(get_rotY, set_rotY)
    def get_rotZ(self):
        CBash.ReadFIDField.restype = POINTER(c_float)
        retValue = CBash.ReadFIDField(self._CollectionIndex, self._ModName, self._recordID, 24)
        if(retValue): return retValue.contents.value
        return None
    def set_rotZ(self, nValue):
        CBash.SetFIDFieldF(self._CollectionIndex, self._ModName, self._recordID, 24, c_float(nValue))
    rotZ = property(get_rotZ, set_rotZ)
    def get_IsOppositeParent(self):
        return (self.parentFlags & 0x00000001) != 0
    def set_IsOppositeParent(self, nValue):
        if (nValue == True): self.parentFlags |= 0x00000001
        else: self.parentFlags &= ~0x00000001
    IsOppositeParent = property(get_IsOppositeParent, set_IsOppositeParent)
    
class ACRERecord(BaseRecord):
    def CopyAsOverride(self, targetCELL):
        FID = CBash.CopyACRERecord(self._CollectionIndex, self._ModName, self._recordID, targetCELL._ModName, targetCELL._recordID, c_bool(True))
        if(FID): return ACRERecord(self._CollectionIndex, targetCELL._ModName, FID)
        return None
    def CopyAsNew(self, targetCELL):
        FID = CBash.CopyACRERecord(self._CollectionIndex, self._ModName, self._recordID, targetCELL._ModName, targetCELL._recordID, c_bool(False))
        if(FID): return ACRERecord(self._CollectionIndex, targetCELL._ModName, FID)
        return None
    def DeleteRecord(self, parent):
        CBash.DeleteRecord(self._CollectionIndex, self._ModName, self._recordID, parent._recordID)
        return
    def get_base(self):
        CBash.ReadFIDField.restype = POINTER(c_uint)
        retValue = CBash.ReadFIDField(self._CollectionIndex, self._ModName, self._recordID, 6)
        if(retValue): return retValue.contents.value
        return None
    def set_base(self, nValue):
        CBash.SetFIDFieldUI(self._CollectionIndex, self._ModName, self._recordID, 6, nValue)
    base = property(get_base, set_base)
    def get_owner(self):
        CBash.ReadFIDField.restype = POINTER(c_uint)
        retValue = CBash.ReadFIDField(self._CollectionIndex, self._ModName, self._recordID, 7)
        if(retValue): return retValue.contents.value
        return None
    def set_owner(self, nValue):
        CBash.SetFIDFieldUI(self._CollectionIndex, self._ModName, self._recordID, 7, nValue)
    owner = property(get_owner, set_owner)
    def get_rank(self):
        CBash.ReadFIDField.restype = POINTER(c_int)
        retValue = CBash.ReadFIDField(self._CollectionIndex, self._ModName, self._recordID, 8)
        if(retValue): return retValue.contents.value
        return None
    def set_rank(self, nValue):
        CBash.SetFIDFieldI(self._CollectionIndex, self._ModName, self._recordID, 8, nValue)
    rank = property(get_rank, set_rank)
    def get_globalVariable(self):
        CBash.ReadFIDField.restype = POINTER(c_uint)
        retValue = CBash.ReadFIDField(self._CollectionIndex, self._ModName, self._recordID, 9)
        if(retValue): return retValue.contents.value
        return None
    def set_globalVariable(self, nValue):
        CBash.SetFIDFieldUI(self._CollectionIndex, self._ModName, self._recordID, 9, nValue)
    globalVariable = property(get_globalVariable, set_globalVariable)
    def get_parent(self):
        CBash.ReadFIDField.restype = POINTER(c_uint)
        retValue = CBash.ReadFIDField(self._CollectionIndex, self._ModName, self._recordID, 10)
        if(retValue): return retValue.contents.value
        return None
    def set_parent(self, nValue):
        CBash.SetFIDFieldUI(self._CollectionIndex, self._ModName, self._recordID, 10, nValue)
    parent = property(get_parent, set_parent)
    def get_parentFlags(self):
        CBash.ReadFIDField.restype = POINTER(c_ubyte)
        retValue = CBash.ReadFIDField(self._CollectionIndex, self._ModName, self._recordID, 11)
        if(retValue): return retValue.contents.value
        return None
    def set_parentFlags(self, nValue):
        CBash.SetFIDFieldUC(self._CollectionIndex, self._ModName, self._recordID, 11, c_ubyte(nValue))
    parentFlags = property(get_parentFlags, set_parentFlags)
    def get_unused1(self):
        numRecords = CBash.GetFIDFieldArraySize(self._CollectionIndex, self._ModName, self._recordID, 12)
        if(numRecords > 0):
            cRecords = POINTER(c_ubyte * numRecords)()
            CBash.GetFIDFieldArray(self._CollectionIndex, self._ModName, self._recordID, 12, byref(cRecords))
            return [cRecords.contents[x] for x in range(0, numRecords)]
        return []
    def set_unused1(self, nValue):
        CBash.SetFIDFieldR(self._CollectionIndex, self._ModName, self._recordID, 12, struct.pack('3B', *nValue), 3)
    unused1 = property(get_unused1, set_unused1)
    def get_xrgd_p(self):
        numRecords = CBash.GetFIDFieldArraySize(self._CollectionIndex, self._ModName, self._recordID, 13)
        if(numRecords > 0):
            cRecords = POINTER(c_ubyte * numRecords)()
            CBash.GetFIDFieldArray(self._CollectionIndex, self._ModName, self._recordID, 13, byref(cRecords))
            return [cRecords.contents[x] for x in range(0, numRecords)]
        return []
    def set_xrgd_p(self, nValue):
        length = len(nValue)
        CBash.SetFIDFieldR(self._CollectionIndex, self._ModName, self._recordID, 13, struct.pack('B' * length, *nValue), length)
    xrgd_p = property(get_xrgd_p, set_xrgd_p)
    def get_scale(self):
        CBash.ReadFIDField.restype = POINTER(c_float)
        retValue = CBash.ReadFIDField(self._CollectionIndex, self._ModName, self._recordID, 14)
        if(retValue): return retValue.contents.value
        return None
    def set_scale(self, nValue):
        CBash.SetFIDFieldF(self._CollectionIndex, self._ModName, self._recordID, 14, c_float(nValue))
    scale = property(get_scale, set_scale)
    def get_posX(self):
        CBash.ReadFIDField.restype = POINTER(c_float)
        retValue = CBash.ReadFIDField(self._CollectionIndex, self._ModName, self._recordID, 15)
        if(retValue): return retValue.contents.value
        return None
    def set_posX(self, nValue):
        CBash.SetFIDFieldF(self._CollectionIndex, self._ModName, self._recordID, 15, c_float(nValue))
    posX = property(get_posX, set_posX)
    def get_posY(self):
        CBash.ReadFIDField.restype = POINTER(c_float)
        retValue = CBash.ReadFIDField(self._CollectionIndex, self._ModName, self._recordID, 16)
        if(retValue): return retValue.contents.value
        return None
    def set_posY(self, nValue):
        CBash.SetFIDFieldF(self._CollectionIndex, self._ModName, self._recordID, 16, c_float(nValue))
    posY = property(get_posY, set_posY)
    def get_posZ(self):
        CBash.ReadFIDField.restype = POINTER(c_float)
        retValue = CBash.ReadFIDField(self._CollectionIndex, self._ModName, self._recordID, 17)
        if(retValue): return retValue.contents.value
        return None
    def set_posZ(self, nValue):
        CBash.SetFIDFieldF(self._CollectionIndex, self._ModName, self._recordID, 17, c_float(nValue))
    posZ = property(get_posZ, set_posZ)
    def get_rotX(self):
        CBash.ReadFIDField.restype = POINTER(c_float)
        retValue = CBash.ReadFIDField(self._CollectionIndex, self._ModName, self._recordID, 18)
        if(retValue): return retValue.contents.value
        return None
    def set_rotX(self, nValue):
        CBash.SetFIDFieldF(self._CollectionIndex, self._ModName, self._recordID, 18, c_float(nValue))
    rotX = property(get_rotX, set_rotX)
    def get_rotY(self):
        CBash.ReadFIDField.restype = POINTER(c_float)
        retValue = CBash.ReadFIDField(self._CollectionIndex, self._ModName, self._recordID, 19)
        if(retValue): return retValue.contents.value
        return None
    def set_rotY(self, nValue):
        CBash.SetFIDFieldF(self._CollectionIndex, self._ModName, self._recordID, 19, c_float(nValue))
    rotY = property(get_rotY, set_rotY)
    def get_rotZ(self):
        CBash.ReadFIDField.restype = POINTER(c_float)
        retValue = CBash.ReadFIDField(self._CollectionIndex, self._ModName, self._recordID, 20)
        if(retValue): return retValue.contents.value
        return None
    def set_rotZ(self, nValue):
        CBash.SetFIDFieldF(self._CollectionIndex, self._ModName, self._recordID, 20, c_float(nValue))
    rotZ = property(get_rotZ, set_rotZ)
    def get_IsOppositeParent(self):
        return (self.parentFlags & 0x00000001) != 0
    def set_IsOppositeParent(self, nValue):
        if (nValue == True): self.parentFlags |= 0x00000001
        else: self.parentFlags &= ~0x00000001
    IsOppositeParent = property(get_IsOppositeParent, set_IsOppositeParent)
    
class REFRRecord(BaseRecord):
    def CopyAsOverride(self, targetCELL):
        FID = CBash.CopyREFRRecord(self._CollectionIndex, self._ModName, self._recordID, targetCELL._ModName, targetCELL._recordID, c_bool(True))
        if(FID): return REFRRecord(self._CollectionIndex, targetCELL._ModName, FID)
        return None
    def CopyAsNew(self, targetCELL):
        FID = CBash.CopyREFRRecord(self._CollectionIndex, self._ModName, self._recordID, targetCELL._ModName, targetCELL._recordID, c_bool(False))
        if(FID): return REFRRecord(self._CollectionIndex, targetCELL._ModName, FID)
        return None
    def DeleteRecord(self, parent):
        CBash.DeleteRecord(self._CollectionIndex, self._ModName, self._recordID, parent._recordID)
        return
    def get_base(self):
        CBash.ReadFIDField.restype = POINTER(c_uint)
        retValue = CBash.ReadFIDField(self._CollectionIndex, self._ModName, self._recordID, 6)
        if(retValue): return retValue.contents.value
        return None
    def set_base(self, nValue):
        CBash.SetFIDFieldUI(self._CollectionIndex, self._ModName, self._recordID, 6, nValue)
    base = property(get_base, set_base)
    def get_destinationFormID(self):
        CBash.ReadFIDField.restype = POINTER(c_uint)
        retValue = CBash.ReadFIDField(self._CollectionIndex, self._ModName, self._recordID, 7)
        if(retValue): return retValue.contents.value
        return None
    def set_destinationFormID(self, nValue):
        CBash.SetFIDFieldUI(self._CollectionIndex, self._ModName, self._recordID, 7, nValue)
    destinationFormID = property(get_destinationFormID, set_destinationFormID)
    def get_destinationPosX(self):
        CBash.ReadFIDField.restype = POINTER(c_float)
        retValue = CBash.ReadFIDField(self._CollectionIndex, self._ModName, self._recordID, 8)
        if(retValue): return retValue.contents.value
        return None
    def set_destinationPosX(self, nValue):
        CBash.SetFIDFieldF(self._CollectionIndex, self._ModName, self._recordID, 8, c_float(nValue))
    destinationPosX = property(get_destinationPosX, set_destinationPosX)
    def get_destinationPosY(self):
        CBash.ReadFIDField.restype = POINTER(c_float)
        retValue = CBash.ReadFIDField(self._CollectionIndex, self._ModName, self._recordID, 9)
        if(retValue): return retValue.contents.value
        return None
    def set_destinationPosY(self, nValue):
        CBash.SetFIDFieldF(self._CollectionIndex, self._ModName, self._recordID, 9, c_float(nValue))
    destinationPosY = property(get_destinationPosY, set_destinationPosY)
    def get_destinationPosZ(self):
        CBash.ReadFIDField.restype = POINTER(c_float)
        retValue = CBash.ReadFIDField(self._CollectionIndex, self._ModName, self._recordID, 10)
        if(retValue): return retValue.contents.value
        return None
    def set_destinationPosZ(self, nValue):
        CBash.SetFIDFieldF(self._CollectionIndex, self._ModName, self._recordID, 10, c_float(nValue))
    destinationPosZ = property(get_destinationPosZ, set_destinationPosZ)
    def get_destinationRotX(self):
        CBash.ReadFIDField.restype = POINTER(c_float)
        retValue = CBash.ReadFIDField(self._CollectionIndex, self._ModName, self._recordID, 11)
        if(retValue): return retValue.contents.value
        return None
    def set_destinationRotX(self, nValue):
        CBash.SetFIDFieldF(self._CollectionIndex, self._ModName, self._recordID, 11, c_float(nValue))
    destinationRotX = property(get_destinationRotX, set_destinationRotX)
    def get_destinationRotY(self):
        CBash.ReadFIDField.restype = POINTER(c_float)
        retValue = CBash.ReadFIDField(self._CollectionIndex, self._ModName, self._recordID, 12)
        if(retValue): return retValue.contents.value
        return None
    def set_destinationRotY(self, nValue):
        CBash.SetFIDFieldF(self._CollectionIndex, self._ModName, self._recordID, 12, c_float(nValue))
    destinationRotY = property(get_destinationRotY, set_destinationRotY)
    def get_destinationRotZ(self):
        CBash.ReadFIDField.restype = POINTER(c_float)
        retValue = CBash.ReadFIDField(self._CollectionIndex, self._ModName, self._recordID, 13)
        if(retValue): return retValue.contents.value
        return None
    def set_destinationRotZ(self, nValue):
        CBash.SetFIDFieldF(self._CollectionIndex, self._ModName, self._recordID, 13, c_float(nValue))
    destinationRotZ = property(get_destinationRotZ, set_destinationRotZ)
    def get_lockLevel(self):
        CBash.ReadFIDField.restype = POINTER(c_ubyte)
        retValue = CBash.ReadFIDField(self._CollectionIndex, self._ModName, self._recordID, 14)
        if(retValue): return retValue.contents.value
        return None
    def set_lockLevel(self, nValue):
        CBash.SetFIDFieldUC(self._CollectionIndex, self._ModName, self._recordID, 14, c_ubyte(nValue))
    lockLevel = property(get_lockLevel, set_lockLevel)
    def get_unused1(self):
        numRecords = CBash.GetFIDFieldArraySize(self._CollectionIndex, self._ModName, self._recordID, 15)
        if(numRecords > 0):
            cRecords = POINTER(c_ubyte * numRecords)()
            CBash.GetFIDFieldArray(self._CollectionIndex, self._ModName, self._recordID, 15, byref(cRecords))
            return [cRecords.contents[x] for x in range(0, numRecords)]
        return []
    def set_unused1(self, nValue):
        CBash.SetFIDFieldR(self._CollectionIndex, self._ModName, self._recordID, 15, struct.pack('3B', *nValue), 3)
    unused1 = property(get_unused1, set_unused1)
    def get_lockKey(self):
        CBash.ReadFIDField.restype = POINTER(c_uint)
        retValue = CBash.ReadFIDField(self._CollectionIndex, self._ModName, self._recordID, 16)
        if(retValue): return retValue.contents.value
        return None
    def set_lockKey(self, nValue):
        CBash.SetFIDFieldUI(self._CollectionIndex, self._ModName, self._recordID, 16, nValue)
    lockKey = property(get_lockKey, set_lockKey)
    def get_unused2(self):
        numRecords = CBash.GetFIDFieldArraySize(self._CollectionIndex, self._ModName, self._recordID, 17)
        if(numRecords > 0):
            cRecords = POINTER(c_ubyte * numRecords)()
            CBash.GetFIDFieldArray(self._CollectionIndex, self._ModName, self._recordID, 17, byref(cRecords))
            return [cRecords.contents[x] for x in range(0, numRecords)]
        return []
    def set_unused2(self, nValue):
        CBash.SetFIDFieldR(self._CollectionIndex, self._ModName, self._recordID, 17, struct.pack('4B', *nValue), 4)
    unused2 = property(get_unused2, set_unused2)
    def get_lockFlags(self):
        CBash.ReadFIDField.restype = POINTER(c_ubyte)
        retValue = CBash.ReadFIDField(self._CollectionIndex, self._ModName, self._recordID, 18)
        if(retValue): return retValue.contents.value
        return None
    def set_lockFlags(self, nValue):
        CBash.SetFIDFieldUC(self._CollectionIndex, self._ModName, self._recordID, 18, c_ubyte(nValue))
    lockFlags = property(get_lockFlags, set_lockFlags)
    def get_unused3(self):
        numRecords = CBash.GetFIDFieldArraySize(self._CollectionIndex, self._ModName, self._recordID, 19)
        if(numRecords > 0):
            cRecords = POINTER(c_ubyte * numRecords)()
            CBash.GetFIDFieldArray(self._CollectionIndex, self._ModName, self._recordID, 19, byref(cRecords))
            return [cRecords.contents[x] for x in range(0, numRecords)]
        return []
    def set_unused3(self, nValue):
        CBash.SetFIDFieldR(self._CollectionIndex, self._ModName, self._recordID, 19, struct.pack('3B', *nValue), 3)
    unused3 = property(get_unused3, set_unused3)
    def get_owner(self):
        CBash.ReadFIDField.restype = POINTER(c_uint)
        retValue = CBash.ReadFIDField(self._CollectionIndex, self._ModName, self._recordID, 20)
        if(retValue): return retValue.contents.value
        return None
    def set_owner(self, nValue):
        CBash.SetFIDFieldUI(self._CollectionIndex, self._ModName, self._recordID, 20, nValue)
    owner = property(get_owner, set_owner)
    def get_rank(self):
        CBash.ReadFIDField.restype = POINTER(c_int)
        retValue = CBash.ReadFIDField(self._CollectionIndex, self._ModName, self._recordID, 21)
        if(retValue): return retValue.contents.value
        return None
    def set_rank(self, nValue):
        CBash.SetFIDFieldI(self._CollectionIndex, self._ModName, self._recordID, 21, nValue)
    rank = property(get_rank, set_rank)
    def get_globalVariable(self):
        CBash.ReadFIDField.restype = POINTER(c_uint)
        retValue = CBash.ReadFIDField(self._CollectionIndex, self._ModName, self._recordID, 22)
        if(retValue): return retValue.contents.value
        return None
    def set_globalVariable(self, nValue):
        CBash.SetFIDFieldUI(self._CollectionIndex, self._ModName, self._recordID, 22, nValue)
    globalVariable = property(get_globalVariable, set_globalVariable)
    def get_parent(self):
        CBash.ReadFIDField.restype = POINTER(c_uint)
        retValue = CBash.ReadFIDField(self._CollectionIndex, self._ModName, self._recordID, 23)
        if(retValue): return retValue.contents.value
        return None
    def set_parent(self, nValue):
        CBash.SetFIDFieldUI(self._CollectionIndex, self._ModName, self._recordID, 23, nValue)
    parent = property(get_parent, set_parent)
    def get_parentFlags(self):
        CBash.ReadFIDField.restype = POINTER(c_ubyte)
        retValue = CBash.ReadFIDField(self._CollectionIndex, self._ModName, self._recordID, 24)
        if(retValue): return retValue.contents.value
        return None
    def set_parentFlags(self, nValue):
        CBash.SetFIDFieldUC(self._CollectionIndex, self._ModName, self._recordID, 24, c_ubyte(nValue))
    parentFlags = property(get_parentFlags, set_parentFlags)
    def get_unused4(self):
        numRecords = CBash.GetFIDFieldArraySize(self._CollectionIndex, self._ModName, self._recordID, 25)
        if(numRecords > 0):
            cRecords = POINTER(c_ubyte * numRecords)()
            CBash.GetFIDFieldArray(self._CollectionIndex, self._ModName, self._recordID, 25, byref(cRecords))
            return [cRecords.contents[x] for x in range(0, numRecords)]
        return []
    def set_unused4(self, nValue):
        CBash.SetFIDFieldR(self._CollectionIndex, self._ModName, self._recordID, 25, struct.pack('3B', *nValue), 3)
    unused4 = property(get_unused4, set_unused4)
    def get_targetFormID(self):
        CBash.ReadFIDField.restype = POINTER(c_uint)
        retValue = CBash.ReadFIDField(self._CollectionIndex, self._ModName, self._recordID, 26)
        if(retValue): return retValue.contents.value
        return None
    def set_targetFormID(self, nValue):
        CBash.SetFIDFieldUI(self._CollectionIndex, self._ModName, self._recordID, 26, nValue)
    targetFormID = property(get_targetFormID, set_targetFormID)
    def get_seed(self):
        CBash.ReadFIDField.restype = POINTER(c_uint)
        retValue = CBash.ReadFIDField(self._CollectionIndex, self._ModName, self._recordID, 27)
        if(retValue): return retValue.contents.value
        return None
    def set_seed(self, nValue):
        CBash.SetFIDFieldUI(self._CollectionIndex, self._ModName, self._recordID, 27, nValue)
    seed = property(get_seed, set_seed)
    def get_seedOffset(self):
        CBash.ReadFIDField.restype = POINTER(c_ubyte)
        retValue = CBash.ReadFIDField(self._CollectionIndex, self._ModName, self._recordID, 27)
        if(retValue): return retValue.contents.value
        return None
    def set_seedOffset(self, nValue):
        CBash.SetFIDFieldUC(self._CollectionIndex, self._ModName, self._recordID, 27, c_ubyte(nValue))
    seedOffset = property(get_seedOffset, set_seedOffset)
    def get_lod1(self):
        CBash.ReadFIDField.restype = POINTER(c_float)
        retValue = CBash.ReadFIDField(self._CollectionIndex, self._ModName, self._recordID, 28)
        if(retValue): return retValue.contents.value
        return None
    def set_lod1(self, nValue):
        CBash.SetFIDFieldF(self._CollectionIndex, self._ModName, self._recordID, 28, c_float(nValue))
    lod1 = property(get_lod1, set_lod1)
    def get_lod2(self):
        CBash.ReadFIDField.restype = POINTER(c_float)
        retValue = CBash.ReadFIDField(self._CollectionIndex, self._ModName, self._recordID, 29)
        if(retValue): return retValue.contents.value
        return None
    def set_lod2(self, nValue):
        CBash.SetFIDFieldF(self._CollectionIndex, self._ModName, self._recordID, 29, c_float(nValue))
    lod2 = property(get_lod2, set_lod2)
    def get_lod3(self):
        CBash.ReadFIDField.restype = POINTER(c_float)
        retValue = CBash.ReadFIDField(self._CollectionIndex, self._ModName, self._recordID, 30)
        if(retValue): return retValue.contents.value
        return None
    def set_lod3(self, nValue):
        CBash.SetFIDFieldF(self._CollectionIndex, self._ModName, self._recordID, 30, c_float(nValue))
    lod3 = property(get_lod3, set_lod3)
    def get_charge(self):
        CBash.ReadFIDField.restype = POINTER(c_float)
        retValue = CBash.ReadFIDField(self._CollectionIndex, self._ModName, self._recordID, 31)
        if(retValue): return retValue.contents.value
        return None
    def set_charge(self, nValue):
        CBash.SetFIDFieldF(self._CollectionIndex, self._ModName, self._recordID, 31, c_float(nValue))
    charge = property(get_charge, set_charge)
    def get_health(self):
        CBash.ReadFIDField.restype = POINTER(c_int)
        retValue = CBash.ReadFIDField(self._CollectionIndex, self._ModName, self._recordID, 32)
        if(retValue): return retValue.contents.value
        return None
    def set_health(self, nValue):
        CBash.SetFIDFieldI(self._CollectionIndex, self._ModName, self._recordID, 32, nValue)
    health = property(get_health, set_health)
    def get_unknownXPCIFormID(self):
        CBash.ReadFIDField.restype = POINTER(c_uint)
        retValue = CBash.ReadFIDField(self._CollectionIndex, self._ModName, self._recordID, 33)
        if(retValue): return retValue.contents.value
        return None
    def set_unknownXPCIFormID(self, nValue):
        CBash.SetFIDFieldUI(self._CollectionIndex, self._ModName, self._recordID, 33, nValue)
    unknownXPCIFormID = property(get_unknownXPCIFormID, set_unknownXPCIFormID)
    def get_unknownXPCIString(self):
        CBash.ReadFIDField.restype = c_char_p
        return CBash.ReadFIDField(self._CollectionIndex, self._ModName, self._recordID, 34)
    def set_unknownXPCIString(self, nValue):
        CBash.SetFIDFieldStr(self._CollectionIndex, self._ModName, self._recordID, 34, nValue)
    unknownXPCIString = property(get_unknownXPCIString, set_unknownXPCIString)
    def get_levelMod(self):
        CBash.ReadFIDField.restype = POINTER(c_int)
        retValue = CBash.ReadFIDField(self._CollectionIndex, self._ModName, self._recordID, 35)
        if(retValue): return retValue.contents.value
        return None
    def set_levelMod(self, nValue):
        CBash.SetFIDFieldI(self._CollectionIndex, self._ModName, self._recordID, 35, nValue)
    levelMod = property(get_levelMod, set_levelMod)
    def get_unknownXRTMFormID(self):
        CBash.ReadFIDField.restype = POINTER(c_uint)
        retValue = CBash.ReadFIDField(self._CollectionIndex, self._ModName, self._recordID, 36)
        if(retValue): return retValue.contents.value
        return None
    def set_unknownXRTMFormID(self, nValue):
        CBash.SetFIDFieldUI(self._CollectionIndex, self._ModName, self._recordID, 36, nValue)
    unknownXRTMFormID = property(get_unknownXRTMFormID, set_unknownXRTMFormID)
    def get_actionFlags(self):
        CBash.ReadFIDField.restype = POINTER(c_uint)
        retValue = CBash.ReadFIDField(self._CollectionIndex, self._ModName, self._recordID, 37)
        if(retValue): return retValue.contents.value
        return None
    def set_actionFlags(self, nValue):
        CBash.SetFIDFieldUI(self._CollectionIndex, self._ModName, self._recordID, 37, nValue)
    actionFlags = property(get_actionFlags, set_actionFlags)
    def get_count(self):
        CBash.ReadFIDField.restype = POINTER(c_int)
        retValue = CBash.ReadFIDField(self._CollectionIndex, self._ModName, self._recordID, 38)
        if(retValue): return retValue.contents.value
        return None
    def set_count(self, nValue):
        CBash.SetFIDFieldI(self._CollectionIndex, self._ModName, self._recordID, 38, nValue)
    count = property(get_count, set_count)
    def get_markerFlags(self):
        CBash.ReadFIDField.restype = POINTER(c_ubyte)
        retValue = CBash.ReadFIDField(self._CollectionIndex, self._ModName, self._recordID, 39)
        if(retValue): return retValue.contents.value
        return None
    def set_markerFlags(self, nValue):
        CBash.SetFIDFieldUC(self._CollectionIndex, self._ModName, self._recordID, 39, c_ubyte(nValue))
    markerFlags = property(get_markerFlags, set_markerFlags)
    def get_markerName(self):
        CBash.ReadFIDField.restype = c_char_p
        return CBash.ReadFIDField(self._CollectionIndex, self._ModName, self._recordID, 40)
    def set_markerName(self, nValue):
        CBash.SetFIDFieldStr(self._CollectionIndex, self._ModName, self._recordID, 40, nValue)
    markerName = property(get_markerName, set_markerName)
    def get_markerType(self):
        CBash.ReadFIDField.restype = POINTER(c_ubyte)
        retValue = CBash.ReadFIDField(self._CollectionIndex, self._ModName, self._recordID, 41)
        if(retValue): return retValue.contents.value
        return None
    def set_markerType(self, nValue):
        CBash.SetFIDFieldUC(self._CollectionIndex, self._ModName, self._recordID, 41, c_ubyte(nValue))
    markerType = property(get_markerType, set_markerType)
    def get_markerUnused(self):
        numRecords = CBash.GetFIDFieldArraySize(self._CollectionIndex, self._ModName, self._recordID, 42)
        if(numRecords > 0):
            cRecords = POINTER(c_ubyte * numRecords)()
            CBash.GetFIDFieldArray(self._CollectionIndex, self._ModName, self._recordID, 42, byref(cRecords))
            return [cRecords.contents[x] for x in range(0, numRecords)]
        return []
    def set_markerUnused(self, nValue):
        CBash.SetFIDFieldR(self._CollectionIndex, self._ModName, self._recordID, 42, struct.pack('B', *nValue), 1)
    markerUnused = property(get_markerUnused, set_markerUnused)
    def get_scale(self):
        CBash.ReadFIDField.restype = POINTER(c_float)
        retValue = CBash.ReadFIDField(self._CollectionIndex, self._ModName, self._recordID, 43)
        if(retValue): return retValue.contents.value
        return None
    def set_scale(self, nValue):
        CBash.SetFIDFieldF(self._CollectionIndex, self._ModName, self._recordID, 43, c_float(nValue))
    scale = property(get_scale, set_scale)
    def get_soul(self):
        CBash.ReadFIDField.restype = POINTER(c_ubyte)
        retValue = CBash.ReadFIDField(self._CollectionIndex, self._ModName, self._recordID, 44)
        if(retValue): return retValue.contents.value
        return None
    def set_soul(self, nValue):
        CBash.SetFIDFieldUC(self._CollectionIndex, self._ModName, self._recordID, 44, c_ubyte(nValue))
    soul = property(get_soul, set_soul)
    def get_posX(self):
        CBash.ReadFIDField.restype = POINTER(c_float)
        retValue = CBash.ReadFIDField(self._CollectionIndex, self._ModName, self._recordID, 45)
        if(retValue): return retValue.contents.value
        return None
    def set_posX(self, nValue):
        CBash.SetFIDFieldF(self._CollectionIndex, self._ModName, self._recordID, 45, c_float(nValue))
    posX = property(get_posX, set_posX)
    def get_posY(self):
        CBash.ReadFIDField.restype = POINTER(c_float)
        retValue = CBash.ReadFIDField(self._CollectionIndex, self._ModName, self._recordID, 46)
        if(retValue): return retValue.contents.value
        return None
    def set_posY(self, nValue):
        CBash.SetFIDFieldF(self._CollectionIndex, self._ModName, self._recordID, 46, c_float(nValue))
    posY = property(get_posY, set_posY)
    def get_posZ(self):
        CBash.ReadFIDField.restype = POINTER(c_float)
        retValue = CBash.ReadFIDField(self._CollectionIndex, self._ModName, self._recordID, 47)
        if(retValue): return retValue.contents.value
        return None
    def set_posZ(self, nValue):
        CBash.SetFIDFieldF(self._CollectionIndex, self._ModName, self._recordID, 47, c_float(nValue))
    posZ = property(get_posZ, set_posZ)
    def get_rotX(self):
        CBash.ReadFIDField.restype = POINTER(c_float)
        retValue = CBash.ReadFIDField(self._CollectionIndex, self._ModName, self._recordID, 48)
        if(retValue): return retValue.contents.value
        return None
    def set_rotX(self, nValue):
        CBash.SetFIDFieldF(self._CollectionIndex, self._ModName, self._recordID, 48, c_float(nValue))
    rotX = property(get_rotX, set_rotX)
    def get_rotY(self):
        CBash.ReadFIDField.restype = POINTER(c_float)
        retValue = CBash.ReadFIDField(self._CollectionIndex, self._ModName, self._recordID, 49)
        if(retValue): return retValue.contents.value
        return None
    def set_rotY(self, nValue):
        CBash.SetFIDFieldF(self._CollectionIndex, self._ModName, self._recordID, 49, c_float(nValue))
    rotY = property(get_rotY, set_rotY)
    def get_rotZ(self):
        CBash.ReadFIDField.restype = POINTER(c_float)
        retValue = CBash.ReadFIDField(self._CollectionIndex, self._ModName, self._recordID, 50)
        if(retValue): return retValue.contents.value
        return None
    def set_rotZ(self, nValue):
        CBash.SetFIDFieldF(self._CollectionIndex, self._ModName, self._recordID, 50, c_float(nValue))
    rotZ = property(get_rotZ, set_rotZ)
    def get_IsOppositeParent(self):
        return (self.parentFlags & 0x00000001) != 0
    def set_IsOppositeParent(self, nValue):
        if (nValue == True): self.parentFlags |= 0x00000001
        else: self.parentFlags &= ~0x00000001
    IsOppositeParent = property(get_IsOppositeParent, set_IsOppositeParent)
    def get_IsVisible(self):
        return (self.markerFlags & 0x00000001) != 0
    def set_IsVisible(self, nValue):
        if (nValue == True): self.markerFlags |= 0x00000001
        else: self.markerFlags &= ~0x00000001
    IsVisible = property(get_IsVisible, set_IsVisible)
    def get_IsCanTravelTo(self):
        return (self.markerFlags & 0x00000002) != 0
    def set_IsCanTravelTo(self, nValue):
        if (nValue == True): self.markerFlags |= 0x00000002
        else: self.markerFlags &= ~0x00000002
    IsCanTravelTo = property(get_IsCanTravelTo, set_IsCanTravelTo)
    def get_IsUseDefault(self):
        return (self.actionFlags & 0x00000001) != 0
    def set_IsUseDefault(self, nValue):
        if (nValue == True): self.actionFlags |= 0x00000001
        else: self.actionFlags &= ~0x00000001
    IsUseDefault = property(get_IsUseDefault, set_IsUseDefault)
    def get_IsActivate(self):
        return (self.actionFlags & 0x00000002) != 0
    def set_IsActivate(self, nValue):
        if (nValue == True): self.actionFlags |= 0x00000002
        else: self.actionFlags &= ~0x00000002
    IsActivate = property(get_IsActivate, set_IsActivate)
    def get_IsOpen(self):
        return (self.actionFlags & 0x00000004) != 0
    def set_IsOpen(self, nValue):
        if (nValue == True): self.actionFlags |= 0x00000004
        else: self.actionFlags &= ~0x00000004
    IsOpen = property(get_IsOpen, set_IsOpen)
    def get_IsOpenByDefault(self):
        return (self.actionFlags & 0x00000008) != 0
    def set_IsOpenByDefault(self, nValue):
        if (nValue == True): self.actionFlags |= 0x00000008
        else: self.actionFlags &= ~0x00000008
    IsOpenByDefault = property(get_IsOpenByDefault, set_IsOpenByDefault)
    def get_IsLeveledLock(self):
        return (self.lockFlags & 0x00000004) != 0
    def set_IsLeveledLock(self, nValue):
        if (nValue == True): self.lockFlags |= 0x00000004
        else: self.lockFlags &= ~0x00000004
    IsLeveledLock = property(get_IsLeveledLock, set_IsLeveledLock)
    def get_IsMarkerNone(self):
        if(self.markerType == None): return True
        return (self.markerType == 0x00000000)
    def set_IsMarkerNone(self, nValue):
        if (nValue == True): self.markerType = 0x00000000
        elif(self.get_MarkerNone()): IsCamp = True
    IsMarkerNone = property(get_IsMarkerNone, set_IsMarkerNone)
    def get_IsCamp(self):
        if(self.markerType == None): return False
        return (self.markerType == 0x00000001)
    def set_IsCamp(self, nValue):
        if (nValue == True): self.markerType = 0x00000001
        elif(self.get_Camp()): self.markerType = 0
    IsCamp = property(get_IsCamp, set_IsCamp)
    def get_IsCave(self):
        if(self.markerType == None): return False
        return (self.markerType == 0x00000002)
    def set_IsCave(self, nValue):
        if (nValue == True): self.markerType = 0x00000002
        elif(self.get_Cave()): self.markerType = 0
    IsCave = property(get_IsCave, set_IsCave)
    def get_IsCity(self):
        if(self.markerType == None): return False
        return (self.markerType == 0x00000003)
    def set_IsCity(self, nValue):
        if (nValue == True): self.markerType = 0x00000003
        elif(self.get_City()): self.markerType = 0
    IsCity = property(get_IsCity, set_IsCity)
    def get_IsElvenRuin(self):
        if(self.markerType == None): return False
        return (self.markerType == 0x00000004)
    def set_IsElvenRuin(self, nValue):
        if (nValue == True): self.markerType = 0x00000004
        elif(self.get_ElvenRuin()): self.markerType = 0
    IsElvenRuin = property(get_IsElvenRuin, set_IsElvenRuin)
    def get_IsFortRuin(self):
        if(self.markerType == None): return False
        return (self.markerType == 0x00000005)
    def set_IsFortRuin(self, nValue):
        if (nValue == True): self.markerType = 0x00000005
        elif(self.get_FortRuin()): self.markerType = 0
    IsFortRuin = property(get_IsFortRuin, set_IsFortRuin)
    def get_IsMine(self):
        if(self.markerType == None): return False
        return (self.markerType == 0x00000006)
    def set_IsMine(self, nValue):
        if (nValue == True): self.markerType = 0x00000006
        elif(self.get_Mine()): self.markerType = 0
    IsMine = property(get_IsMine, set_IsMine)
    def get_IsLandmark(self):
        if(self.markerType == None): return False
        return (self.markerType == 0x00000007)
    def set_IsLandmark(self, nValue):
        if (nValue == True): self.markerType = 0x00000007
        elif(self.get_Landmark()): self.markerType = 0
    IsLandmark = property(get_IsLandmark, set_IsLandmark)
    def get_IsTavern(self):
        if(self.markerType == None): return False
        return (self.markerType == 0x00000008)
    def set_IsTavern(self, nValue):
        if (nValue == True): self.markerType = 0x00000008
        elif(self.get_Tavern()): self.markerType = 0
    IsTavern = property(get_IsTavern, set_IsTavern)
    def get_IsSettlement(self):
        if(self.markerType == None): return False
        return (self.markerType == 0x00000009)
    def set_IsSettlement(self, nValue):
        if (nValue == True): self.markerType = 0x00000009
        elif(self.get_Settlement()): self.markerType = 0
    IsSettlement = property(get_IsSettlement, set_IsSettlement)
    def get_IsDaedricShrine(self):
        if(self.markerType == None): return False
        return (self.markerType == 0x0000000A)
    def set_IsDaedricShrine(self, nValue):
        if (nValue == True): self.markerType = 0x0000000A
        elif(self.get_DaedricShrine()): self.markerType = 0
    IsDaedricShrine = property(get_IsDaedricShrine, set_IsDaedricShrine)
    def get_IsOblivionGate(self):
        if(self.markerType == None): return False
        return (self.markerType == 0x0000000B)
    def set_IsOblivionGate(self, nValue):
        if (nValue == True): self.markerType = 0x0000000B
        elif(self.get_OblivionGate()): self.markerType = 0
    IsOblivionGate = property(get_IsOblivionGate, set_IsOblivionGate)
    def get_IsUnknownDoorIcon(self):
        if(self.markerType == None): return False
        return (self.markerType == 0x0000000C)
    def set_IsUnknownDoorIcon(self, nValue):
        if (nValue == True): self.markerType = 0x0000000C
        elif(self.get_UnknownDoorIcon()): self.markerType = 0
    IsUnknownDoorIcon = property(get_IsUnknownDoorIcon, set_IsUnknownDoorIcon)
    def get_IsNoSoul(self):
        return (self.soul == 0)
    def set_IsNoSoul(self, nValue):
        if (nValue == True): self.soul = 0
        elif(self.get_IsNoSoul()): IsPettySoul = True
    IsNoSoul = property(get_IsNoSoul, set_IsNoSoul)
    def get_IsPettySoul(self):
        return (self.soul == 1)
    def set_IsPettySoul(self, nValue):
        if (nValue == True): self.soul = 1
        elif(self.get_IsPettySoul()): IsNoSoul = True
    IsPettySoul = property(get_IsPettySoul, set_IsPettySoul)
    def get_IsLesserSoul(self):
        return (self.soul == 2)
    def set_IsLesserSoul(self, nValue):
        if (nValue == True): self.soul = 2
        elif(self.get_IsLesserSoul()): IsNoSoul = True
    IsLesserSoul = property(get_IsLesserSoul, set_IsLesserSoul)
    def get_IsCommonSoul(self):
        return (self.soul == 3)
    def set_IsCommonSoul(self, nValue):
        if (nValue == True): self.soul = 3
        elif(self.get_IsCommonSoul()): IsNoSoul = True
    IsCommonSoul = property(get_IsCommonSoul, set_IsCommonSoul)
    def get_IsGreaterSoul(self):
        return (self.soul == 4)
    def set_IsGreaterSoul(self, nValue):
        if (nValue == True): self.soul = 4
        elif(self.get_IsGreaterSoul()): IsNoSoul = True
    IsGreaterSoul = property(get_IsGreaterSoul, set_IsGreaterSoul)
    def get_IsGrandSoul(self):
        return (self.soul == 5)
    def set_IsGrandSoul(self, nValue):
        if (nValue == True): self.soul = 5
        elif(self.get_IsGrandSoul()): IsNoSoul = True
    IsGrandSoul = property(get_IsGrandSoul, set_IsGrandSoul)
    
class PGRDRecord(BaseRecord):
    def CopyAsOverride(self, targetCELL):
        FID = CBash.CopyPGRDRecord(self._CollectionIndex, self._ModName, self._recordID, targetCELL._ModName, targetCELL._recordID, c_bool(True))
        if(FID): return PGRDRecord(self._CollectionIndex, targetCELL._ModName, FID)
        return None
    def CopyAsNew(self, targetCELL):
        FID = CBash.CopyPGRDRecord(self._CollectionIndex, self._ModName, self._recordID, targetCELL._ModName, targetCELL._recordID, c_bool(False))
        if(FID): return PGRDRecord(self._CollectionIndex, targetCELL._ModName, FID)
        return None
    def DeleteRecord(self, parent):
        CBash.DeleteRecord(self._CollectionIndex, self._ModName, self._recordID, parent._recordID)
        return
    class PGRPRecord(object):
        def __init__(self, CollectionIndex, ModName, recordID, listIndex):
            self._CollectionIndex = CollectionIndex
            self._ModName = ModName
            self._recordID = recordID
            self._listIndex = listIndex
        def get_x(self):
            CBash.ReadFIDListField.restype = POINTER(c_float)
            retValue = CBash.ReadFIDListField(self._CollectionIndex, self._ModName, self._recordID, 7, self._listIndex, 1)
            if(retValue): return retValue.contents.value
            return None
        def set_x(self, nValue):
            CBash.SetFIDListFieldF(self._CollectionIndex, self._ModName, self._recordID, 7, self._listIndex, 1, c_float(nValue))
        x = property(get_x, set_x)
        def get_y(self):
            CBash.ReadFIDListField.restype = POINTER(c_float)
            retValue = CBash.ReadFIDListField(self._CollectionIndex, self._ModName, self._recordID, 7, self._listIndex, 2)
            if(retValue): return retValue.contents.value
            return None
        def set_y(self, nValue):
            CBash.SetFIDListFieldF(self._CollectionIndex, self._ModName, self._recordID, 7, self._listIndex, 2, c_float(nValue))
        y = property(get_y, set_y)
        def get_z(self):
            CBash.ReadFIDListField.restype = POINTER(c_float)
            retValue = CBash.ReadFIDListField(self._CollectionIndex, self._ModName, self._recordID, 7, self._listIndex, 3)
            if(retValue): return retValue.contents.value
            return None
        def set_z(self, nValue):
            CBash.SetFIDListFieldF(self._CollectionIndex, self._ModName, self._recordID, 7, self._listIndex, 3, c_float(nValue))
        z = property(get_z, set_z)
        def get_connections(self):
            CBash.ReadFIDListField.restype = POINTER(c_ubyte)
            retValue = CBash.ReadFIDListField(self._CollectionIndex, self._ModName, self._recordID, 7, self._listIndex, 4)
            if(retValue): return retValue.contents.value
            return None
        def set_connections(self, nValue):
            CBash.SetFIDListFieldUC(self._CollectionIndex, self._ModName, self._recordID, 7, self._listIndex, 4, c_ubyte(nValue))
        connections = property(get_connections, set_connections)
        def get_unused1(self):
            numRecords = CBash.GetFIDListArraySize(self._CollectionIndex, self._ModName, self._recordID, 7, self._listIndex, 5)
            if(numRecords > 0):
                cRecords = POINTER(c_ubyte * numRecords)()
                CBash.GetFIDListArray(self._CollectionIndex, self._ModName, self._recordID, 7, self._listIndex, 5, byref(cRecords))
                return [cRecords.contents[x] for x in range(0, numRecords)]
            return []
        def set_unused1(self, nValue):
            CBash.SetFIDListFieldR(self._CollectionIndex, self._ModName, self._recordID, 7, self._listIndex, 5, struct.pack('3B', *nValue), 3)
        unused1 = property(get_unused1, set_unused1)
    class PGRIRecord(object):
        def __init__(self, CollectionIndex, ModName, recordID, listIndex):
            self._CollectionIndex = CollectionIndex
            self._ModName = ModName
            self._recordID = recordID
            self._listIndex = listIndex
        def get_point(self):
            CBash.ReadFIDListField.restype = POINTER(c_ushort)
            retValue = CBash.ReadFIDListField(self._CollectionIndex, self._ModName, self._recordID, 10, self._listIndex, 1)
            if(retValue): return retValue.contents.value
            return None
        def set_point(self, nValue):
            CBash.SetFIDListFieldUS(self._CollectionIndex, self._ModName, self._recordID, 10, self._listIndex, 1, c_ushort(nValue))
        point = property(get_point, set_point)
        def get_unused1(self):
            numRecords = CBash.GetFIDListArraySize(self._CollectionIndex, self._ModName, self._recordID, 10, self._listIndex, 2)
            if(numRecords > 0):
                cRecords = POINTER(c_ubyte * numRecords)()
                CBash.GetFIDListArray(self._CollectionIndex, self._ModName, self._recordID, 10, self._listIndex, 2, byref(cRecords))
                return [cRecords.contents[x] for x in range(0, numRecords)]
            return []
        def set_unused1(self, nValue):
            CBash.SetFIDListFieldR(self._CollectionIndex, self._ModName, self._recordID, 10, self._listIndex, 2, struct.pack('2B', *nValue), 2)
        unused1 = property(get_unused1, set_unused1)
        def get_x(self):
            CBash.ReadFIDListField.restype = POINTER(c_float)
            retValue = CBash.ReadFIDListField(self._CollectionIndex, self._ModName, self._recordID, 10, self._listIndex, 3)
            if(retValue): return retValue.contents.value
            return None
        def set_x(self, nValue):
            CBash.SetFIDListFieldF(self._CollectionIndex, self._ModName, self._recordID, 10, self._listIndex, 3, c_float(nValue))
        x = property(get_x, set_x)
        def get_y(self):
            CBash.ReadFIDListField.restype = POINTER(c_float)
            retValue = CBash.ReadFIDListField(self._CollectionIndex, self._ModName, self._recordID, 10, self._listIndex, 4)
            if(retValue): return retValue.contents.value
            return None
        def set_y(self, nValue):
            CBash.SetFIDListFieldF(self._CollectionIndex, self._ModName, self._recordID, 10, self._listIndex, 4, c_float(nValue))
        y = property(get_y, set_y)
        def get_z(self):
            CBash.ReadFIDListField.restype = POINTER(c_float)
            retValue = CBash.ReadFIDListField(self._CollectionIndex, self._ModName, self._recordID, 10, self._listIndex, 5)
            if(retValue): return retValue.contents.value
            return None
        def set_z(self, nValue):
            CBash.SetFIDListFieldF(self._CollectionIndex, self._ModName, self._recordID, 10, self._listIndex, 5, c_float(nValue))
        z = property(get_z, set_z)
    class PGRLRecord(object):
        def __init__(self, CollectionIndex, ModName, recordID, listIndex):
            self._CollectionIndex = CollectionIndex
            self._ModName = ModName
            self._recordID = recordID
            self._listIndex = listIndex
        def get_reference(self):
            CBash.ReadFIDListField.restype = POINTER(c_uint)
            retValue = CBash.ReadFIDListField(self._CollectionIndex, self._ModName, self._recordID, 11, self._listIndex, 1)
            if(retValue): return retValue.contents.value
            return None
        def set_reference(self, nValue):
            CBash.SetFIDListFieldUI(self._CollectionIndex, self._ModName, self._recordID, 11, self._listIndex, 1, nValue)
        reference = property(get_reference, set_reference)
        def get_points(self):
            numRecords = CBash.GetFIDListArraySize(self._CollectionIndex, self._ModName, self._recordID, 11, self._listIndex, 2)
            if(numRecords > 0):                
                cRecords = POINTER(c_uint * numRecords)()
                CBash.GetFIDListArray(self._CollectionIndex, self._ModName, self._recordID, 11, self._listIndex, 2, byref(cRecords))
                return [cRecords.contents[x] for x in range(0, numRecords)]
            return []
        def set_points(self, nValues):
            CBash.SetFIDListFieldUIA(self._CollectionIndex, self._ModName, self._recordID, 11, self._listIndex, 2, struct.pack('I' * len(nValues), *nValues), len(nValues))
        points = property(get_points, set_points)
    def newPGRPElement(self):
        listIndex = CBash.CreateFIDListElement(self._CollectionIndex, self._ModName, self._recordID, 7)
        if(listIndex == -1): return None
        return self.PGRPRecord(self._CollectionIndex, self._ModName, self._recordID, listIndex)

    def newPGRIElement(self):
        listIndex = CBash.CreateFIDListElement(self._CollectionIndex, self._ModName, self._recordID, 10)
        if(listIndex == -1): return None
        return self.PGRIRecord(self._CollectionIndex, self._ModName, self._recordID, listIndex)

    def newPGRLElement(self):
        listIndex = CBash.CreateFIDListElement(self._CollectionIndex, self._ModName, self._recordID, 11)
        if(listIndex == -1): return None
        return self.PGRLRecord(self._CollectionIndex, self._ModName, self._recordID, listIndex)
    
    def get_count(self):
        CBash.ReadFIDField.restype = POINTER(c_ushort)
        retValue = CBash.ReadFIDField(self._CollectionIndex, self._ModName, self._recordID, 6)
        if(retValue): return retValue.contents.value
        return None
    def set_count(self, nValue):
        CBash.SetFIDFieldUS(self._CollectionIndex, self._ModName, self._recordID, 6, c_ushort(nValue))
    count = property(get_count, set_count)    
    def get_PGRP(self):
        numRecords = CBash.GetFIDListSize(self._CollectionIndex, self._ModName, self._recordID, 7)
        if(numRecords > 0): return [self.PGRPRecord(self._CollectionIndex, self._ModName, self._recordID, x) for x in range(0, numRecords)]
        return []
    def set_PGRP(self, nPGRP):
        diffLength = len(nPGRP) - CBash.GetFIDListSize(self._CollectionIndex, self._ModName, self._recordID, 7)
        nValues = [(nPGRPRecord.x, nPGRPRecord.y, nPGRPRecord.z, nPGRPRecord.connections, nPGRPRecord.unused1) for nPGRPRecord in nPGRP]
        while(diffLength < 0):
            CBash.DeleteFIDListElement(self._CollectionIndex, self._ModName, self._recordID, 7)
            diffLength += 1
        while(diffLength > 0):
            CBash.CreateFIDListElement(self._CollectionIndex, self._ModName, self._recordID, 7)
            diffLength -= 1
        for oPGRPRecord, nValue in zip(self.PGRP, nValues):
            oPGRPRecord.x, oPGRPRecord.y, oPGRPRecord.z, oPGRPRecord.connections, oPGRPRecord.unused1 = nValue
    PGRP = property(get_PGRP, set_PGRP)    
    def get_PGAG(self):
        numRecords = CBash.GetFIDFieldArraySize(self._CollectionIndex, self._ModName, self._recordID, 8)
        if(numRecords > 0):
            cRecords = POINTER(c_ubyte * numRecords)()
            CBash.GetFIDFieldArray(self._CollectionIndex, self._ModName, self._recordID, 8, byref(cRecords))
            return [cRecords.contents[x] for x in range(0, numRecords)]
        return []
    def set_PGAG(self, nValue):
        length = len(nValue)
        CBash.SetFIDFieldR(self._CollectionIndex, self._ModName, self._recordID, 8, struct.pack('B' * length, *nValue), length)
    PGAG = property(get_PGAG, set_PGAG)
    def get_PGRR(self):
        numRecords = CBash.GetFIDFieldArraySize(self._CollectionIndex, self._ModName, self._recordID, 9)
        if(numRecords > 0):
            cRecords = POINTER(c_ubyte * numRecords)()
            CBash.GetFIDFieldArray(self._CollectionIndex, self._ModName, self._recordID, 9, byref(cRecords))
            return [cRecords.contents[x] for x in range(0, numRecords)]
        return []
    def set_PGRR(self, nValue):
        length = len(nValue)
        CBash.SetFIDFieldR(self._CollectionIndex, self._ModName, self._recordID, 9, struct.pack('B' * length, *nValue), length)
    PGRR = property(get_PGRR, set_PGRR)
    def get_PGRI(self):
        numRecords = CBash.GetFIDListSize(self._CollectionIndex, self._ModName, self._recordID, 10)
        if(numRecords > 0): return [self.PGRIRecord(self._CollectionIndex, self._ModName, self._recordID, x) for x in range(0, numRecords)]
        return []
    def set_PGRI(self, nPGRI):
        diffLength = len(nPGRI) - CBash.GetFIDListSize(self._CollectionIndex, self._ModName, self._recordID, 10)
        nValues = [(nPGRIRecord.point, nPGRIRecord.unused1, nPGRIRecord.x, nPGRIRecord.y, nPGRIRecord.z) for nPGRIRecord in nPGRI]
        while(diffLength < 0):
            CBash.DeleteFIDListElement(self._CollectionIndex, self._ModName, self._recordID, 10)
            diffLength += 1
        while(diffLength > 0):
            CBash.CreateFIDListElement(self._CollectionIndex, self._ModName, self._recordID, 10)
            diffLength -= 1
        for oPGRIRecord, nValue in zip(self.PGRI, nValues):
            oPGRIRecord.point, oPGRIRecord.unused1, oPGRIRecord.x, oPGRIRecord.y, oPGRIRecord.z = nValue
    PGRI = property(get_PGRI, set_PGRI) 
    def get_PGRL(self):
        numRecords = CBash.GetFIDListSize(self._CollectionIndex, self._ModName, self._recordID, 11)
        if(numRecords > 0): return [self.PGRLRecord(self._CollectionIndex, self._ModName, self._recordID, x) for x in range(0, numRecords)]
        return []
    def set_PGRL(self, nPGRL):
        diffLength = len(nPGRL) - CBash.GetFIDListSize(self._CollectionIndex, self._ModName, self._recordID, 11)
        nValues = [(nPGRLRecord.reference, nPGRLRecord.points) for nPGRLRecord in nPGRL]
        while(diffLength < 0):
            CBash.DeleteFIDListElement(self._CollectionIndex, self._ModName, self._recordID, 11)
            diffLength += 1
        while(diffLength > 0):
            CBash.CreateFIDListElement(self._CollectionIndex, self._ModName, self._recordID, 11)
            diffLength -= 1
        for oPGRLRecord, nValue in zip(self.PGRL, nValues):
            oPGRLRecord.reference, oPGRLRecord.points = nValue
    PGRL = property(get_PGRL, set_PGRL)

class WRLDRecord(BaseRecord):
    def CopyAsOverride(self, targetMod):
        FID = CBash.CopyWRLDRecord(self._CollectionIndex, self._ModName, self._recordID, targetMod._ModName, c_bool(True))
        if(FID): return WRLDRecord(self._CollectionIndex, targetMod._ModName, FID)
        return None
    def CopyAsNew(self, targetMod):
        FID = CBash.CopyWRLDRecord(self._CollectionIndex, self._ModName, self._recordID, targetMod._ModName, c_bool(False))
        if(FID): return WRLDRecord(self._CollectionIndex, targetMod._ModName, FID)
        return None
    def createWorldCELLRecord(self):
        FID = CBash.CreateCELLRecord(self._CollectionIndex, self._ModName, self._recordID, c_bool(True))
        if(FID): return CELLRecord(self._CollectionIndex, self._ModName, FID)
        return None
    def createCELLRecord(self):
        FID = CBash.CreateCELLRecord(self._CollectionIndex, self._ModName, self._recordID, c_bool(False))
        if(FID): return CELLRecord(self._CollectionIndex, self._ModName, FID)
        return None
    def createROADRecord(self):
        FID = CBash.CreateROADRecord(self._CollectionIndex, self._ModName, self._recordID)
        if(FID): return ROADRecord(self._CollectionIndex, self._ModName, FID)
        return None
    def get_full(self):
        CBash.ReadFIDField.restype = c_char_p
        return CBash.ReadFIDField(self._CollectionIndex, self._ModName, self._recordID, 6)
    def set_full(self, nValue):
        CBash.SetFIDFieldStr(self._CollectionIndex, self._ModName, self._recordID, 6, nValue)
    full = property(get_full, set_full)
    def get_parent(self):
        CBash.ReadFIDField.restype = POINTER(c_uint)
        retValue = CBash.ReadFIDField(self._CollectionIndex, self._ModName, self._recordID, 7)
        if(retValue): return retValue.contents.value
        return None
    def set_parent(self, nValue):
        CBash.SetFIDFieldUI(self._CollectionIndex, self._ModName, self._recordID, 7, nValue)
    parent = property(get_parent, set_parent)
    def get_climate(self):
        CBash.ReadFIDField.restype = POINTER(c_uint)
        retValue = CBash.ReadFIDField(self._CollectionIndex, self._ModName, self._recordID, 8)
        if(retValue): return retValue.contents.value
        return None
    def set_climate(self, nValue):
        CBash.SetFIDFieldUI(self._CollectionIndex, self._ModName, self._recordID, 8, nValue)
    climate = property(get_climate, set_climate)
    def get_water(self):
        CBash.ReadFIDField.restype = POINTER(c_uint)
        retValue = CBash.ReadFIDField(self._CollectionIndex, self._ModName, self._recordID, 9)
        if(retValue): return retValue.contents.value
        return None
    def set_water(self, nValue):
        CBash.SetFIDFieldUI(self._CollectionIndex, self._ModName, self._recordID, 9, nValue)
    water = property(get_water, set_water)
    def get_mapPath(self):
        CBash.ReadFIDField.restype = c_char_p
        return CBash.ReadFIDField(self._CollectionIndex, self._ModName, self._recordID, 10)
    def set_mapPath(self, nValue):
        CBash.SetFIDFieldStr(self._CollectionIndex, self._ModName, self._recordID, 10, nValue)
    mapPath = property(get_mapPath, set_mapPath)
    def get_dimX(self):
        CBash.ReadFIDField.restype = POINTER(c_int)
        retValue = CBash.ReadFIDField(self._CollectionIndex, self._ModName, self._recordID, 11)
        if(retValue): return retValue.contents.value
        return None
    def set_dimX(self, nValue):
        CBash.SetFIDFieldI(self._CollectionIndex, self._ModName, self._recordID, 11, nValue)
    dimX = property(get_dimX, set_dimX)
    def get_dimY(self):
        CBash.ReadFIDField.restype = POINTER(c_int)
        retValue = CBash.ReadFIDField(self._CollectionIndex, self._ModName, self._recordID, 12)
        if(retValue): return retValue.contents.value
        return None
    def set_dimY(self, nValue):
        CBash.SetFIDFieldI(self._CollectionIndex, self._ModName, self._recordID, 12, nValue)
    dimY = property(get_dimY, set_dimY)
    def get_NWCellX(self):
        CBash.ReadFIDField.restype = POINTER(c_short)
        retValue = CBash.ReadFIDField(self._CollectionIndex, self._ModName, self._recordID, 13)
        if(retValue): return retValue.contents.value
        return None
    def set_NWCellX(self, nValue):
        CBash.SetFIDFieldS(self._CollectionIndex, self._ModName, self._recordID, 13, c_short(nValue))
    NWCellX = property(get_NWCellX, set_NWCellX)
    def get_NWCellY(self):
        CBash.ReadFIDField.restype = POINTER(c_short)
        retValue = CBash.ReadFIDField(self._CollectionIndex, self._ModName, self._recordID, 14)
        if(retValue): return retValue.contents.value
        return None
    def set_NWCellY(self, nValue):
        CBash.SetFIDFieldS(self._CollectionIndex, self._ModName, self._recordID, 14, c_short(nValue))
    NWCellY = property(get_NWCellY, set_NWCellY)
    def get_SECellX(self):
        CBash.ReadFIDField.restype = POINTER(c_short)
        retValue = CBash.ReadFIDField(self._CollectionIndex, self._ModName, self._recordID, 15)
        if(retValue): return retValue.contents.value
        return None
    def set_SECellX(self, nValue):
        CBash.SetFIDFieldS(self._CollectionIndex, self._ModName, self._recordID, 15, c_short(nValue))
    SECellX = property(get_SECellX, set_SECellX)
    def get_SECellY(self):
        CBash.ReadFIDField.restype = POINTER(c_short)
        retValue = CBash.ReadFIDField(self._CollectionIndex, self._ModName, self._recordID, 16)
        if(retValue): return retValue.contents.value
        return None
    def set_SECellY(self, nValue):
        CBash.SetFIDFieldS(self._CollectionIndex, self._ModName, self._recordID, 16, c_short(nValue))
    SECellY = property(get_SECellY, set_SECellY)
    def get_flags(self):
        CBash.ReadFIDField.restype = POINTER(c_ubyte)
        retValue = CBash.ReadFIDField(self._CollectionIndex, self._ModName, self._recordID, 17)
        if(retValue): return retValue.contents.value
        return None
    def set_flags(self, nValue):
        CBash.SetFIDFieldUC(self._CollectionIndex, self._ModName, self._recordID, 17, c_ubyte(nValue))
    flags = property(get_flags, set_flags)
    def get_unknown00(self):
        CBash.ReadFIDField.restype = POINTER(c_float)
        retValue = CBash.ReadFIDField(self._CollectionIndex, self._ModName, self._recordID, 18)
        if(retValue): return retValue.contents.value
        return None
    def set_unknown00(self, nValue):
        CBash.SetFIDFieldF(self._CollectionIndex, self._ModName, self._recordID, 18, c_float(nValue))
    unknown00 = property(get_unknown00, set_unknown00)
    def get_unknown01(self):
        CBash.ReadFIDField.restype = POINTER(c_float)
        retValue = CBash.ReadFIDField(self._CollectionIndex, self._ModName, self._recordID, 19)
        if(retValue): return retValue.contents.value
        return None
    def set_unknown01(self, nValue):
        CBash.SetFIDFieldF(self._CollectionIndex, self._ModName, self._recordID, 19, c_float(nValue))
    unknown01 = property(get_unknown01, set_unknown01)
    def get_unknown90(self):
        CBash.ReadFIDField.restype = POINTER(c_float)
        retValue = CBash.ReadFIDField(self._CollectionIndex, self._ModName, self._recordID, 20)
        if(retValue): return retValue.contents.value
        return None
    def set_unknown90(self, nValue):
        CBash.SetFIDFieldF(self._CollectionIndex, self._ModName, self._recordID, 20, c_float(nValue))
    unknown90 = property(get_unknown90, set_unknown90)
    def get_unknown91(self):
        CBash.ReadFIDField.restype = POINTER(c_float)
        retValue = CBash.ReadFIDField(self._CollectionIndex, self._ModName, self._recordID, 21)
        if(retValue): return retValue.contents.value
        return None
    def set_unknown91(self, nValue):
        CBash.SetFIDFieldF(self._CollectionIndex, self._ModName, self._recordID, 21, c_float(nValue))
    unknown91 = property(get_unknown91, set_unknown91)
    def get_sound(self):
        CBash.ReadFIDField.restype = POINTER(c_uint)
        retValue = CBash.ReadFIDField(self._CollectionIndex, self._ModName, self._recordID, 22)
        if(retValue): return retValue.contents.value
        return None
    def set_sound(self, nValue):
        CBash.SetFIDFieldUI(self._CollectionIndex, self._ModName, self._recordID, 22, nValue)
    sound = property(get_sound, set_sound)
    def get_ofst_p(self):
        numRecords = CBash.GetFIDFieldArraySize(self._CollectionIndex, self._ModName, self._recordID, 23)
        if(numRecords > 0):
            cRecords = POINTER(c_ubyte * numRecords)()
            CBash.GetFIDFieldArray(self._CollectionIndex, self._ModName, self._recordID, 23, byref(cRecords))
            return [cRecords.contents[x] for x in range(0, numRecords)]
        return []
    def set_ofst_p(self, nValue):
        length = len(nValue)
        CBash.SetFIDFieldR(self._CollectionIndex, self._ModName, self._recordID, 23, struct.pack('B' * length, *nValue), length)
    ofst_p = property(get_ofst_p, set_ofst_p)
    def get_ROAD(self):
        CBash.ReadFIDField.restype = POINTER(c_uint)
        retValue = CBash.ReadFIDField(self._CollectionIndex, self._ModName, self._recordID, 24)
        if(retValue): return ROADRecord(self._CollectionIndex, self._ModName, retValue.contents.value)
        return None
    def set_ROAD(self, nROAD):
        if(nCELL == None and self.ROAD != None):
            self.ROAD.DeleteRecord()
            return
        curROAD = self.ROAD
        if(curROAD == None):
            curROAD = self.createROADRecord()
        curROAD.PGRP = nROAD.PGRP
        curROAD.PGRR = nROAD.PGRR
    ROAD = property(get_ROAD, set_ROAD)
    def get_CELL(self):
        CBash.ReadFIDField.restype = POINTER(c_uint)
        retValue = CBash.ReadFIDField(self._CollectionIndex, self._ModName, self._recordID, 25)
        if(retValue): return CELLRecord(self._CollectionIndex, self._ModName, retValue.contents.value)
        return None
    def set_CELL(self, nCELL):
        if(nCELL == None and self.CELL != None):
            self.CELL.DeleteRecord()
            return
        curCELL = self.CELL
        if(curCELL == None):
            curCELL = self.createWorldCELLRecord()

        curCELL.flags1 = nCELL.flags1
        curCELL.flags2 = nCELL.flags2
        curCELL.eid = nCELL.eid

        curCELL.full = nCELL.full
        curCELL.flags = nCELL.flags
        curCELL.ambientRed = nCELL.ambientRed
        curCELL.ambientGreen = nCELL.ambientGreen
        curCELL.ambientBlue = nCELL.ambientBlue
        curCELL.unused1 = nCELL.unused1
        curCELL.directionalRed = nCELL.directionalRed
        curCELL.directionalGreen = nCELL.directionalGreen
        curCELL.directionalBlue = nCELL.directionalBlue
        curCELL.unused2 = nCELL.unused2
        curCELL.fogRed = nCELL.fogRed
        curCELL.fogGreen = nCELL.fogGreen
        curCELL.fogBlue = nCELL.fogBlue
        curCELL.unused3 = nCELL.unused3
        curCELL.fogNear = nCELL.fogNear
        curCELL.fogFar = nCELL.fogFar
        curCELL.directionalXY = nCELL.directionalXY
        curCELL.directionalZ = nCELL.directionalZ
        curCELL.directionalFade = nCELL.directionalFade
        curCELL.fogClip = nCELL.fogClip
        curCELL.music = nCELL.music
        curCELL.owner = nCELL.owner
        curCELL.rank = nCELL.rank
        curCELL.globalVariable = nCELL.globalVariable
        curCELL.climate = nCELL.climate
        curCELL.waterHeight = nCELL.waterHeight
        curCELL.regions = nCELL.regions
        curCELL.posX = nCELL.posX
        curCELL.posY = nCELL.posY
        curCELL.water = nCELL.water
    CELL = property(get_CELL, set_CELL)
    @property
    def CELLS(self):
        numSubRecords = CBash.GetFIDFieldArraySize(self._CollectionIndex, self._ModName, self._recordID, 26)
        if(numSubRecords > 0):
            cRecords = (POINTER(c_uint) * numSubRecords)()
            CBash.GetFIDFieldArray(self._CollectionIndex, self._ModName, self._recordID, 26, byref(cRecords))
            return [CELLRecord(self._CollectionIndex, self._ModName, x.contents.value) for x in cRecords]
        return []

    def get_IsSmallWorld(self):
        return (self.flags & 0x00000001) != 0
    def set_IsSmallWorld(self, nValue):
        if (nValue == True): self.flags |= 0x00000001
        else: self.flags &= ~0x00000001
    IsSmallWorld = property(get_IsSmallWorld, set_IsSmallWorld)
    def get_IsNoFastTravel(self):
        return (self.flags & 0x00000002) != 0
    def set_IsNoFastTravel(self, nValue):
        if (nValue == True): self.flags |= 0x00000002
        else: self.flags &= ~0x00000002
    IsNoFastTravel = property(get_IsNoFastTravel, set_IsNoFastTravel)
    def get_IsFastTravel(self):
        return not self.get_IsNoFastTravel()
    def set_IsFastTravel(self, nValue):
        if (nValue == True): self.flags &= ~0x00000002
        else: self.flags |= 0x00000002
    IsFastTravel = property(get_IsFastTravel, set_IsFastTravel)
    def get_IsOblivionWorldspace(self):
        return (self.flags & 0x00000004) != 0
    def set_IsOblivionWorldspace(self, nValue):
        if (nValue == True): self.flags |= 0x00000004
        else: self.flags &= ~0x00000004
    IsOblivionWorldspace = property(get_IsOblivionWorldspace, set_IsOblivionWorldspace)
    def get_IsNoLODWater(self):
        return (self.flags & 0x00000010) != 0
    def set_IsNoLODWater(self, nValue):
        if (nValue == True): self.flags |= 0x00000010
        else: self.flags &= ~0x00000010
    IsNoLODWater = property(get_IsNoLODWater, set_IsNoLODWater)
    def get_IsLODWater(self):
        return not self.get_IsNoLODWater()
    def set_IsLODWater(self, nValue):
        if (nValue == True): self.flags &= ~0x00000010
        else: self.flags |= 0x00000010
    IsLODWater = property(get_IsLODWater, set_IsLODWater)
    def get_IsDefault(self):
        return (self.sound == 0)
    def set_IsDefault(self, nValue):
        if (nValue == True): self.sound = 0
        elif(self.get_IsDefault()): self.IsPublic = True
    IsDefault = property(get_IsDefault, set_IsDefault)
    def get_IsPublic(self):
        return (self.sound == 1)
    def set_IsPublic(self, nValue):
        if (nValue == True): self.sound = 1
        elif(self.get_IsPublic()): self.IsDefault = True
    IsPublic = property(get_IsPublic, set_IsPublic)
    def get_IsDungeon(self):
        return (self.sound == 2)
    def set_IsDungeon(self, nValue):
        if (nValue == True): self.sound = 2
        elif(self.get_IsDungeon()): self.IsDefault = True
    IsDungeon = property(get_IsDungeon, set_IsDungeon)
    
class ROADRecord(BaseRecord):
    def CopyAsOverride(self, targetWRLD):
        FID = CBash.CopyROADRecord(self._CollectionIndex, self._ModName, self._recordID, targetWRLD._ModName, targetWRLD._recordID, c_bool(True))
        if(FID): return ROADRecord(self._CollectionIndex, targetWRLD._ModName, FID)
        return None
    def CopyAsNew(self, targetWRLD):
        FID = CBash.CopyROADRecord(self._CollectionIndex, self._ModName, self._recordID, targetWRLD._ModName, targetWRLD._recordID, c_bool(False))
        if(FID): return ROADRecord(self._CollectionIndex, targetWRLD._ModName, FID)
        return None
    def DeleteRecord(self, parent):
        CBash.DeleteRecord(self._CollectionIndex, self._ModName, self._recordID, parent._recordID)
        return
    class PGRPRecord(object):
        def __init__(self, CollectionIndex, ModName, recordID, listIndex):
            self._CollectionIndex = CollectionIndex
            self._ModName = ModName
            self._recordID = recordID
            self._listIndex = listIndex
        def get_x(self):
            CBash.ReadFIDListField.restype = POINTER(c_float)
            retValue = CBash.ReadFIDListField(self._CollectionIndex, self._ModName, self._recordID, 6, self._listIndex, 1)
            if(retValue): return retValue.contents.value
            return None
        def set_x(self, nValue):
            CBash.SetFIDListFieldF(self._CollectionIndex, self._ModName, self._recordID, 6, self._listIndex, 1, c_float(nValue))
        x = property(get_x, set_x)
        def get_y(self):
            CBash.ReadFIDListField.restype = POINTER(c_float)
            retValue = CBash.ReadFIDListField(self._CollectionIndex, self._ModName, self._recordID, 6, self._listIndex, 2)
            if(retValue): return retValue.contents.value
            return None
        def set_y(self, nValue):
            CBash.SetFIDListFieldF(self._CollectionIndex, self._ModName, self._recordID, 6, self._listIndex, 2, c_float(nValue))
        y = property(get_y, set_y)
        def get_z(self):
            CBash.ReadFIDListField.restype = POINTER(c_float)
            retValue = CBash.ReadFIDListField(self._CollectionIndex, self._ModName, self._recordID, 6, self._listIndex, 3)
            if(retValue): return retValue.contents.value
            return None
        def set_z(self, nValue):
            CBash.SetFIDListFieldF(self._CollectionIndex, self._ModName, self._recordID, 6, self._listIndex, 3, c_float(nValue))
        z = property(get_z, set_z)
        def get_connections(self):
            CBash.ReadFIDListField.restype = POINTER(c_ubyte)
            retValue = CBash.ReadFIDListField(self._CollectionIndex, self._ModName, self._recordID, 6, self._listIndex, 4)
            if(retValue): return retValue.contents.value
            return None
        def set_connections(self, nValue):
            CBash.SetFIDListFieldUC(self._CollectionIndex, self._ModName, self._recordID, 6, self._listIndex, 4, c_ubyte(nValue))
        connections = property(get_connections, set_connections)
        def get_unused1(self):
            numRecords = CBash.GetFIDListArraySize(self._CollectionIndex, self._ModName, self._recordID, 6, self._listIndex, 5)
            if(numRecords > 0):
                cRecords = POINTER(c_ubyte * numRecords)()
                CBash.GetFIDListArray(self._CollectionIndex, self._ModName, self._recordID, 6, self._listIndex, 5, byref(cRecords))
                return [cRecords.contents[x] for x in range(0, numRecords)]
            return []
        def set_unused1(self, nValue):
            CBash.SetFIDListFieldR(self._CollectionIndex, self._ModName, self._recordID, 6, self._listIndex, 5, struct.pack('3B', *nValue), 3)
        unused1 = property(get_unused1, set_unused1)
    class PGRRRecord(object):
        def __init__(self, CollectionIndex, ModName, recordID, listIndex):
            self._CollectionIndex = CollectionIndex
            self._ModName = ModName
            self._recordID = recordID
            self._listIndex = listIndex
        def get_x(self):
            CBash.ReadFIDListField.restype = POINTER(c_float)
            retValue = CBash.ReadFIDListField(self._CollectionIndex, self._ModName, self._recordID, 7, self._listIndex, 1)
            if(retValue): return retValue.contents.value
            return None
        def set_x(self, nValue):
            CBash.SetFIDListFieldF(self._CollectionIndex, self._ModName, self._recordID, 7, self._listIndex, 1, c_float(nValue))
        x = property(get_x, set_x)
        def get_y(self):
            CBash.ReadFIDListField.restype = POINTER(c_float)
            retValue = CBash.ReadFIDListField(self._CollectionIndex, self._ModName, self._recordID, 7, self._listIndex, 2)
            if(retValue): return retValue.contents.value
            return None
        def set_y(self, nValue):
            CBash.SetFIDListFieldF(self._CollectionIndex, self._ModName, self._recordID, 7, self._listIndex, 2, c_float(nValue))
        y = property(get_y, set_y)
        def get_z(self):
            CBash.ReadFIDListField.restype = POINTER(c_float)
            retValue = CBash.ReadFIDListField(self._CollectionIndex, self._ModName, self._recordID, 7, self._listIndex, 3)
            if(retValue): return retValue.contents.value
            return None
        def set_z(self, nValue):
            CBash.SetFIDListFieldF(self._CollectionIndex, self._ModName, self._recordID, 7, self._listIndex, 3, c_float(nValue))
        z = property(get_z, set_z)
    def newPGRPElement(self):
        listIndex = CBash.CreateFIDListElement(self._CollectionIndex, self._ModName, self._recordID, 6)
        if(listIndex == -1): return None
        return self.PGRPRecord(self._CollectionIndex, self._ModName, self._recordID, listIndex)
    def newPGRRElement(self):
        listIndex = CBash.CreateFIDListElement(self._CollectionIndex, self._ModName, self._recordID, 7)
        if(listIndex == -1): return None
        return self.PGRRRecord(self._CollectionIndex, self._ModName, self._recordID, listIndex)
    def get_PGRP(self):
        numRecords = CBash.GetFIDListSize(self._CollectionIndex, self._ModName, self._recordID, 6)
        if(numRecords > 0): return [self.PGRPRecord(self._CollectionIndex, self._ModName, self._recordID, x) for x in range(0, numRecords)]
        return []
    def set_PGRP(self, nPGRP):
        diffLength = len(nPGRP) - CBash.GetFIDListSize(self._CollectionIndex, self._ModName, self._recordID, 6)
        nValues = [(nPGRPRecord.x, nPGRPRecord.y, nPGRPRecord.z, nPGRPRecord.connections, nPGRPRecord.unused1) for nPGRPRecord in nPGRP]
        while(diffLength < 0):
            CBash.DeleteFIDListElement(self._CollectionIndex, self._ModName, self._recordID, 6)
            diffLength += 1
        while(diffLength > 0):
            CBash.CreateFIDListElement(self._CollectionIndex, self._ModName, self._recordID, 6)
            diffLength -= 1
        for oPGRPRecord, nValue in zip(self.PGRP, nValues):
            oPGRPRecord.x, oPGRPRecord.y, oPGRPRecord.z, oPGRPRecord.connections, oPGRPRecord.unused1 = nValue
    PGRP = property(get_PGRP, set_PGRP)
    def get_PGRR(self):
        numRecords = CBash.GetFIDListSize(self._CollectionIndex, self._ModName, self._recordID, 7)
        if(numRecords > 0): return [self.PGRRRecord(self._CollectionIndex, self._ModName, self._recordID, x) for x in range(0, numRecords)]
        return []
    def set_PGRR(self, nPGRR):
        diffLength = len(nPGRR) - CBash.GetFIDListSize(self._CollectionIndex, self._ModName, self._recordID, 7)
        nValues = [(nPGRRRecord.x, nPGRRRecord.y, nPGRRRecord.z) for nPGRRRecord in nPGRR]
        while(diffLength < 0):
            CBash.DeleteFIDListElement(self._CollectionIndex, self._ModName, self._recordID, 7)
            diffLength += 1
        while(diffLength > 0):
            CBash.CreateFIDListElement(self._CollectionIndex, self._ModName, self._recordID, 7)
            diffLength -= 1
        for oPGRRRecord, nValue in zip(self.PGRR, nValues):
            oPGRRRecord.x, oPGRRRecord.y, oPGRRRecord.z = nValue
    PGRR = property(get_PGRR, set_PGRR)

class LANDRecord(BaseRecord):
    def CopyAsOverride(self, targetCELL):
        FID = CBash.CopyLANDRecord(self._CollectionIndex, self._ModName, self._recordID, targetCELL._ModName, targetCELL._recordID, c_bool(True))
        if(FID): return LANDRecord(self._CollectionIndex, targetCELL._ModName, FID)
        return None
    def CopyAsNew(self, targetCELL):
        FID = CBash.CopyLANDRecord(self._CollectionIndex, self._ModName, self._recordID, targetCELL._ModName, targetCELL._recordID, c_bool(False))
        if(FID): return LANDRecord(self._CollectionIndex, targetCELL._ModName, FID)
        return None
    def DeleteRecord(self, parent):
        CBash.DeleteRecord(self._CollectionIndex, self._ModName, self._recordID, parent._recordID)
        return
    class Normal(object):
        def __init__(self, CollectionIndex, ModName, recordID, listIndex, listX2Index):
            self._CollectionIndex = CollectionIndex
            self._ModName = ModName
            self._recordID = recordID
            self._listIndex = listIndex
            self._listX2Index = listX2Index
        def get_x(self):
            CBash.ReadFIDListX2Field.restype = POINTER(c_ubyte)
            retValue = CBash.ReadFIDListX2Field(self._CollectionIndex, self._ModName, self._recordID, 7, self._listIndex, 0, self._listX2Index, 1)
            if(retValue): return retValue.contents.value
            return None
        def set_x(self, nValue):
            CBash.SetFIDListX2FieldUC(self._CollectionIndex, self._ModName, self._recordID, 7, self._listIndex, 0, self._listX2Index, 1, c_ubyte(nValue))
        x = property(get_x, set_x)
        def get_y(self):
            CBash.ReadFIDListX2Field.restype = POINTER(c_ubyte)
            retValue = CBash.ReadFIDListX2Field(self._CollectionIndex, self._ModName, self._recordID, 7, self._listIndex, 0, self._listX2Index, 2)
            if(retValue): return retValue.contents.value
            return None
        def set_y(self, nValue):
            CBash.SetFIDListX2FieldUC(self._CollectionIndex, self._ModName, self._recordID, 7, self._listIndex, 0, self._listX2Index, 2, c_ubyte(nValue))
        y = property(get_y, set_y)
        def get_z(self):
            CBash.ReadFIDListX2Field.restype = POINTER(c_ubyte)
            retValue = CBash.ReadFIDListX2Field(self._CollectionIndex, self._ModName, self._recordID, 7, self._listIndex, 0, self._listX2Index, 3)
            if(retValue): return retValue.contents.value
            return None
        def set_z(self, nValue):
            CBash.SetFIDListX2FieldUC(self._CollectionIndex, self._ModName, self._recordID, 7, self._listIndex, 0, self._listX2Index, 3, c_ubyte(nValue))
        z = property(get_z, set_z)
    class Height(object):
        def __init__(self, CollectionIndex, ModName, recordID, listIndex, listX2Index):
            self._CollectionIndex = CollectionIndex
            self._ModName = ModName
            self._recordID = recordID
            self._listIndex = listIndex
            self._listX2Index = listX2Index
        def get_height(self):
            CBash.ReadFIDListX2Field.restype = POINTER(c_byte)
            retValue = CBash.ReadFIDListX2Field(self._CollectionIndex, self._ModName, self._recordID, 9, self._listIndex, 0, self._listX2Index, 1)
            if(retValue): return retValue.contents.value
            return None
        def set_height(self, nValue):
            CBash.SetFIDListX2FieldC(self._CollectionIndex, self._ModName, self._recordID, 9, self._listIndex, 0, self._listX2Index, 1, c_ubyte(nValue))
        height = property(get_height, set_height)
    class Color(object):
        def __init__(self, CollectionIndex, ModName, recordID, listIndex, listX2Index):
            self._CollectionIndex = CollectionIndex
            self._ModName = ModName
            self._recordID = recordID
            self._listIndex = listIndex
            self._listX2Index = listX2Index
        def get_red(self):
            CBash.ReadFIDListX2Field.restype = POINTER(c_ubyte)
            retValue = CBash.ReadFIDListX2Field(self._CollectionIndex, self._ModName, self._recordID, 11, self._listIndex, 0, self._listX2Index, 1)
            if(retValue): return retValue.contents.value
            return None
        def set_red(self, nValue):
            CBash.SetFIDListX2FieldUC(self._CollectionIndex, self._ModName, self._recordID, 11, self._listIndex, 0, self._listX2Index, 1, c_ubyte(nValue))
        red = property(get_red, set_red)
        def get_green(self):
            CBash.ReadFIDListX2Field.restype = POINTER(c_ubyte)
            retValue = CBash.ReadFIDListX2Field(self._CollectionIndex, self._ModName, self._recordID, 11, self._listIndex, 0, self._listX2Index, 2)
            if(retValue): return retValue.contents.value
            return None
        def set_green(self, nValue):
            CBash.SetFIDListX2FieldUC(self._CollectionIndex, self._ModName, self._recordID, 11, self._listIndex, 0, self._listX2Index, 2, c_ubyte(nValue))
        green = property(get_green, set_green)
        def get_blue(self):
            CBash.ReadFIDListX2Field.restype = POINTER(c_ubyte)
            retValue = CBash.ReadFIDListX2Field(self._CollectionIndex, self._ModName, self._recordID, 11, self._listIndex, 0, self._listX2Index, 3)
            if(retValue): return retValue.contents.value
            return None
        def set_blue(self, nValue):
            CBash.SetFIDListX2FieldUC(self._CollectionIndex, self._ModName, self._recordID, 11, self._listIndex, 0, self._listX2Index, 3, c_ubyte(nValue))
        blue = property(get_blue, set_blue)
    class BaseTexture(object):
        def __init__(self, CollectionIndex, ModName, recordID, subField, listIndex):
            self._CollectionIndex = CollectionIndex
            self._ModName = ModName
            self._recordID = recordID
            self._subField = subField
            self._listIndex = listIndex
        def get_texture(self):
            CBash.ReadFIDListField.restype = POINTER(c_uint)
            retValue = CBash.ReadFIDListField(self._CollectionIndex, self._ModName, self._recordID, self._subField, self._listIndex, 1)
            if(retValue): return retValue.contents.value
            return None
        def set_texture(self, nValue):
            CBash.SetFIDListFieldUI(self._CollectionIndex, self._ModName, self._recordID, self._subField, self._listIndex, 1, nValue)
        texture = property(get_texture, set_texture)
        def get_quadrant(self):
            CBash.ReadFIDListField.restype = POINTER(c_byte)
            retValue = CBash.ReadFIDListField(self._CollectionIndex, self._ModName, self._recordID, self._subField, self._listIndex, 2)
            if(retValue): return retValue.contents.value
            return None
        def set_quadrant(self, nValue):
            CBash.SetFIDListFieldUC(self._CollectionIndex, self._ModName, self._recordID, self._subField, self._listIndex, 2, c_byte(nValue))
        quadrant = property(get_quadrant, set_quadrant)
        def get_unused1(self):
            numRecords = CBash.GetFIDListArraySize(self._CollectionIndex, self._ModName, self._recordID, self._subField, self._listIndex, 3)
            if(numRecords > 0):
                cRecords = POINTER(c_ubyte * numRecords)()
                CBash.GetFIDListArray(self._CollectionIndex, self._ModName, self._recordID, self._subField, self._listIndex, 3, byref(cRecords))
                return [cRecords.contents[x] for x in range(0, numRecords)]
            return []
        def set_unused1(self, nValue):
            CBash.SetFIDListFieldR(self._CollectionIndex, self._ModName, self._recordID, self._subField, self._listIndex, 3, struct.pack('B', *nValue), 1)
        unused1 = property(get_unused1, set_unused1)
        def get_layer(self):
            CBash.ReadFIDListField.restype = POINTER(c_short)
            retValue = CBash.ReadFIDListField(self._CollectionIndex, self._ModName, self._recordID, self._subField, self._listIndex, 4)
            if(retValue): return retValue.contents.value
            return None
        def set_layer(self, nValue):
            CBash.SetFIDListFieldS(self._CollectionIndex, self._ModName, self._recordID, self._subField, self._listIndex, 4, c_short(nValue))
        layer = property(get_layer, set_layer)
    class AlphaLayer(object):
        class Opacity(object):
            def __init__(self, CollectionIndex, ModName, recordID, listIndex, listX2Index):
                self._CollectionIndex = CollectionIndex
                self._ModName = ModName
                self._recordID = recordID
                self._listIndex = listIndex
                self._listX2Index = listX2Index
            def get_position(self):
                CBash.ReadFIDListX2Field.restype = POINTER(c_ushort)
                retValue = CBash.ReadFIDListX2Field(self._CollectionIndex, self._ModName, self._recordID, 13, self._listIndex, 5, self._listX2Index, 1)
                if(retValue): return retValue.contents.value
                return None
            def set_position(self, nValue):
                CBash.SetFIDListX2FieldUS(self._CollectionIndex, self._ModName, self._recordID, 13, self._listIndex, 5, self._listX2Index, 1, c_ushort(nValue))
            position = property(get_position, set_position)
            def get_unused1(self):
                numRecords = CBash.GetFIDListX2ArraySize(self._CollectionIndex, self._ModName, self._recordID, 13, self._listIndex, 5, self._listX2Index, 2)
                if(numRecords > 0):
                    cRecords = POINTER(c_ubyte * numRecords)()
                    CBash.GetFIDListX2Array(self._CollectionIndex, self._ModName, self._recordID, 13, self._listIndex, 5, self._listX2Index, 2, byref(cRecords))
                    return [cRecords.contents[x] for x in range(0, numRecords)]
                return []
            def set_unused1(self, nValue):
                CBash.SetFIDListX2FieldR(self._CollectionIndex, self._ModName, self._recordID, 13, self._listIndex, 5, self._listX2Index, 2, struct.pack('2B', *nValue), 2)
            unused1 = property(get_unused1, set_unused1)
            def get_opacity(self):
                CBash.ReadFIDListX2Field.restype = POINTER(c_float)
                retValue = CBash.ReadFIDListX2Field(self._CollectionIndex, self._ModName, self._recordID, 13, self._listIndex, 5, self._listX2Index, 3)
                if(retValue): return retValue.contents.value
                return None
            def set_opacity(self, nValue):
                CBash.SetFIDListX2FieldF(self._CollectionIndex, self._ModName, self._recordID, 13, self._listIndex, 5, self._listX2Index, 3, c_float(nValue))
            opacity = property(get_opacity, set_opacity)
        def __init__(self, CollectionIndex, ModName, recordID, subField, listIndex):
            self._CollectionIndex = CollectionIndex
            self._ModName = ModName
            self._recordID = recordID
            self._subField = subField
            self._listIndex = listIndex
        def newOpacitiesElement(self):
            listX2Index = CBash.CreateFIDListX2Element(self._CollectionIndex, self._ModName, self._recordID, self._subField, self._listIndex, 5)
            if(listX2Index == -1): return None
            return self.Opacity(self._CollectionIndex, self._ModName, self._recordID, self._listIndex, listX2Index)
        def get_texture(self):
            CBash.ReadFIDListField.restype = POINTER(c_uint)
            retValue = CBash.ReadFIDListField(self._CollectionIndex, self._ModName, self._recordID, self._subField, self._listIndex, 1)
            if(retValue): return retValue.contents.value
            return None
        def set_texture(self, nValue):
            CBash.SetFIDListFieldUI(self._CollectionIndex, self._ModName, self._recordID, self._subField, self._listIndex, 1, nValue)
        texture = property(get_texture, set_texture)
        def get_quadrant(self):
            CBash.ReadFIDListField.restype = POINTER(c_byte)
            retValue = CBash.ReadFIDListField(self._CollectionIndex, self._ModName, self._recordID, self._subField, self._listIndex, 2)
            if(retValue): return retValue.contents.value
            return None
        def set_quadrant(self, nValue):
            CBash.SetFIDListFieldUC(self._CollectionIndex, self._ModName, self._recordID, self._subField, self._listIndex, 2, c_byte(nValue))
        quadrant = property(get_quadrant, set_quadrant)
        def get_unused1(self):
            numRecords = CBash.GetFIDListArraySize(self._CollectionIndex, self._ModName, self._recordID, self._subField, self._listIndex, 3)
            if(numRecords > 0):
                cRecords = POINTER(c_ubyte * numRecords)()
                CBash.GetFIDListArray(self._CollectionIndex, self._ModName, self._recordID, self._subField, self._listIndex, 3, byref(cRecords))
                return [cRecords.contents[x] for x in range(0, numRecords)]
            return []
        def set_unused1(self, nValue):
            CBash.SetFIDListFieldR(self._CollectionIndex, self._ModName, self._recordID, self._subField, self._listIndex, 3, struct.pack('B', *nValue), 1)
        unused1 = property(get_unused1, set_unused1)
        def get_layer(self):
            CBash.ReadFIDListField.restype = POINTER(c_short)
            retValue = CBash.ReadFIDListField(self._CollectionIndex, self._ModName, self._recordID, self._subField, self._listIndex, 4)
            if(retValue): return retValue.contents.value
            return None
        def set_layer(self, nValue):
            CBash.SetFIDListFieldS(self._CollectionIndex, self._ModName, self._recordID, self._subField, self._listIndex, 4, c_short(nValue))
        layer = property(get_layer, set_layer)
        def get_opacities(self):
            numRecords = CBash.GetFIDListX2Size(self._CollectionIndex, self._ModName, self._recordID, self._subField, self._listIndex, 5)
            if(numRecords > 0): return [self.Opacity(self._CollectionIndex, self._ModName, self._recordID, self._listIndex, x) for x in range(0, numRecords)]
            return []
        def set_opacities(self, nOpacities):
            diffLength = len(nOpacities) - CBash.GetFIDListX2Size(self._CollectionIndex, self._ModName, self._recordID, self._subField, self._listIndex, 5)
            nValues = [(nOpacity.position, nOpacity.unused1, nOpacity.opacity) for nOpacity in nOpacities]
            while(diffLength < 0):
                CBash.DeleteFIDListX2Element(self._CollectionIndex, self._ModName, self._recordID, self._subField, self._listIndex, 5)
                diffLength += 1
            while(diffLength > 0):
                CBash.CreateFIDListX2Element(self._CollectionIndex, self._ModName, self._recordID, self._subField, self._listIndex, 5)
                diffLength -= 1
            for oOpacity, nValue in zip(self.opacities, nValues):
                oOpacity.position, oOpacity.unused1, oOpacity.opacity = nValue
        opacities = property(get_opacities, set_opacities)
    class VertexTexture(object):
        def __init__(self, CollectionIndex, ModName, recordID, subField, listIndex):
            self._CollectionIndex = CollectionIndex
            self._ModName = ModName
            self._recordID = recordID
            self._subField = subField
            self._listIndex = listIndex
        def get_texture(self):
            CBash.ReadFIDListField.restype = POINTER(c_uint)
            retValue = CBash.ReadFIDListField(self._CollectionIndex, self._ModName, self._recordID, self._subField, self._listIndex, 1)
            if(retValue): return retValue.contents.value
            return None
        def set_texture(self, nValue):
            CBash.SetFIDListFieldUI(self._CollectionIndex, self._ModName, self._recordID, self._subField, self._listIndex, 1, nValue)
        texture = property(get_texture, set_texture)
    class Positions(object):
        def __init__(self, CollectionIndex, ModName, recordID, listIndex, listX2Index):
            self._CollectionIndex = CollectionIndex
            self._ModName = ModName
            self._recordID = recordID
            self._listIndex = listIndex
            self._listX2Index = listX2Index
        def get_height(self):
            CBash.ReadFIDListX2Field.restype = POINTER(c_float)
            retValue = CBash.ReadFIDListX2Field(self._CollectionIndex, self._ModName, self._recordID, 15, self._listIndex, 0, self._listX2Index, 1)
            if(retValue): return retValue.contents.value
            return None
        def set_height(self, nValue):
            CBash.SetFIDListX2FieldF(self._CollectionIndex, self._ModName, self._recordID, 15, self._listIndex, 0, self._listX2Index, 1, c_float(nValue))
        height = property(get_height, set_height)
        def get_normalX(self):
            CBash.ReadFIDListX2Field.restype = POINTER(c_ubyte)
            retValue = CBash.ReadFIDListX2Field(self._CollectionIndex, self._ModName, self._recordID, 15, self._listIndex, 0, self._listX2Index, 2)
            if(retValue): return retValue.contents.value
            return None
        def set_normalX(self, nValue):
            CBash.SetFIDListX2FieldUC(self._CollectionIndex, self._ModName, self._recordID, 15, self._listIndex, 0, self._listX2Index, 2, c_ubyte(nValue))
        normalX = property(get_normalX, set_normalX)
        def get_normalY(self):
            CBash.ReadFIDListX2Field.restype = POINTER(c_ubyte)
            retValue = CBash.ReadFIDListX2Field(self._CollectionIndex, self._ModName, self._recordID, 15, self._listIndex, 0, self._listX2Index, 3)
            if(retValue): return retValue.contents.value
            return None
        def set_normalY(self, nValue):
            CBash.SetFIDListX2FieldUC(self._CollectionIndex, self._ModName, self._recordID, 15, self._listIndex, 0, self._listX2Index, 3, c_ubyte(nValue))
        normalY = property(get_normalY, set_normalY)
        def get_normalZ(self):
            CBash.ReadFIDListX2Field.restype = POINTER(c_ubyte)
            retValue = CBash.ReadFIDListX2Field(self._CollectionIndex, self._ModName, self._recordID, 15, self._listIndex, 0, self._listX2Index, 4)
            if(retValue): return retValue.contents.value
            return None
        def set_normalZ(self, nValue):
            CBash.SetFIDListX2FieldUC(self._CollectionIndex, self._ModName, self._recordID, 15, self._listIndex, 0, self._listX2Index, 4, c_ubyte(nValue))
        normalZ = property(get_normalZ, set_normalZ)
        def get_red(self):
            CBash.ReadFIDListX2Field.restype = POINTER(c_ubyte)
            retValue = CBash.ReadFIDListX2Field(self._CollectionIndex, self._ModName, self._recordID, 15, self._listIndex, 0, self._listX2Index, 5)
            if(retValue): return retValue.contents.value
            return None
        def set_red(self, nValue):
            CBash.SetFIDListX2FieldUC(self._CollectionIndex, self._ModName, self._recordID, 15, self._listIndex, 0, self._listX2Index, 5, c_ubyte(nValue))
        red = property(get_red, set_red)
        def get_green(self):
            CBash.ReadFIDListX2Field.restype = POINTER(c_ubyte)
            retValue = CBash.ReadFIDListX2Field(self._CollectionIndex, self._ModName, self._recordID, 15, self._listIndex, 0, self._listX2Index, 6)
            if(retValue): return retValue.contents.value
            return None
        def set_green(self, nValue):
            CBash.SetFIDListX2FieldUC(self._CollectionIndex, self._ModName, self._recordID, 15, self._listIndex, 0, self._listX2Index, 6, c_ubyte(nValue))
        green = property(get_green, set_green)
        def get_blue(self):
            CBash.ReadFIDListX2Field.restype = POINTER(c_ubyte)
            retValue = CBash.ReadFIDListX2Field(self._CollectionIndex, self._ModName, self._recordID, 15, self._listIndex, 0, self._listX2Index, 7)
            if(retValue): return retValue.contents.value
            return None
        def set_blue(self, nValue):
            CBash.SetFIDListX2FieldUC(self._CollectionIndex, self._ModName, self._recordID, 15, self._listIndex, 0, self._listX2Index, 7, c_ubyte(nValue))
        blue = property(get_blue, set_blue)
        def get_baseTexture(self):
            CBash.ReadFIDListX2Field.restype = POINTER(c_uint)
            retValue = CBash.ReadFIDListX2Field(self._CollectionIndex, self._ModName, self._recordID, 15, self._listIndex, 0, self._listX2Index, 8)
            if(retValue): return retValue.contents.value
            return None
        def set_baseTexture(self, nValue):
            CBash.SetFIDListX2FieldUI(self._CollectionIndex, self._ModName, self._recordID, 15, self._listIndex, 0, self._listX2Index, 8, nValue)
        baseTexture = property(get_baseTexture, set_baseTexture)
        def get_layer1Texture(self):
            CBash.ReadFIDListX2Field.restype = POINTER(c_uint)
            retValue = CBash.ReadFIDListX2Field(self._CollectionIndex, self._ModName, self._recordID, 15, self._listIndex, 0, self._listX2Index, 9)
            if(retValue): return retValue.contents.value
            return None
        def set_layer1Texture(self, nValue):
            CBash.SetFIDListX2FieldUI(self._CollectionIndex, self._ModName, self._recordID, 15, self._listIndex, 0, self._listX2Index, 9, nValue)
        layer1Texture = property(get_layer1Texture, set_layer1Texture)
        def get_layer1Opacity(self):
            CBash.ReadFIDListX2Field.restype = POINTER(c_float)
            retValue = CBash.ReadFIDListX2Field(self._CollectionIndex, self._ModName, self._recordID, 15, self._listIndex, 0, self._listX2Index, 10)
            if(retValue): return retValue.contents.value
            return None
        def set_layer1Opacity(self, nValue):
            CBash.SetFIDListX2FieldF(self._CollectionIndex, self._ModName, self._recordID, 15, self._listIndex, 0, self._listX2Index, 10, c_float(nValue))
        layer1Opacity = property(get_layer1Opacity, set_layer1Opacity)
        def get_layer2Texture(self):
            CBash.ReadFIDListX2Field.restype = POINTER(c_uint)
            retValue = CBash.ReadFIDListX2Field(self._CollectionIndex, self._ModName, self._recordID, 15, self._listIndex, 0, self._listX2Index, 11)
            if(retValue): return retValue.contents.value
            return None
        def set_layer2Texture(self, nValue):
            CBash.SetFIDListX2FieldUI(self._CollectionIndex, self._ModName, self._recordID, 15, self._listIndex, 0, self._listX2Index, 11, nValue)
        layer2Texture = property(get_layer2Texture, set_layer2Texture)
        def get_layer2Opacity(self):
            CBash.ReadFIDListX2Field.restype = POINTER(c_float)
            retValue = CBash.ReadFIDListX2Field(self._CollectionIndex, self._ModName, self._recordID, 15, self._listIndex, 0, self._listX2Index, 12)
            if(retValue): return retValue.contents.value
            return None
        def set_layer2Opacity(self, nValue):
            CBash.SetFIDListX2FieldF(self._CollectionIndex, self._ModName, self._recordID, 15, self._listIndex, 0, self._listX2Index, 12, c_float(nValue))
        layer2Opacity = property(get_layer2Opacity, set_layer2Opacity)
        def get_layer3Texture(self):
            CBash.ReadFIDListX2Field.restype = POINTER(c_uint)
            retValue = CBash.ReadFIDListX2Field(self._CollectionIndex, self._ModName, self._recordID, 15, self._listIndex, 0, self._listX2Index, 13)
            if(retValue): return retValue.contents.value
            return None
        def set_layer3Texture(self, nValue):
            CBash.SetFIDListX2FieldUI(self._CollectionIndex, self._ModName, self._recordID, 15, self._listIndex, 0, self._listX2Index, 13, nValue)
        layer3Texture = property(get_layer3Texture, set_layer3Texture)
        def get_layer3Opacity(self):
            CBash.ReadFIDListX2Field.restype = POINTER(c_float)
            retValue = CBash.ReadFIDListX2Field(self._CollectionIndex, self._ModName, self._recordID, 15, self._listIndex, 0, self._listX2Index, 14)
            if(retValue): return retValue.contents.value
            return None
        def set_layer3Opacity(self, nValue):
            CBash.SetFIDListX2FieldF(self._CollectionIndex, self._ModName, self._recordID, 15, self._listIndex, 0, self._listX2Index, 14, c_float(nValue))
        layer3Opacity = property(get_layer3Opacity, set_layer3Opacity)
        def get_layer4Texture(self):
            CBash.ReadFIDListX2Field.restype = POINTER(c_uint)
            retValue = CBash.ReadFIDListX2Field(self._CollectionIndex, self._ModName, self._recordID, 15, self._listIndex, 0, self._listX2Index, 15)
            if(retValue): return retValue.contents.value
            return None
        def set_layer4Texture(self, nValue):
            CBash.SetFIDListX2FieldUI(self._CollectionIndex, self._ModName, self._recordID, 15, self._listIndex, 0, self._listX2Index, 15, nValue)
        layer4Texture = property(get_layer4Texture, set_layer4Texture)
        def get_layer4Opacity(self):
            CBash.ReadFIDListX2Field.restype = POINTER(c_float)
            retValue = CBash.ReadFIDListX2Field(self._CollectionIndex, self._ModName, self._recordID, 15, self._listIndex, 0, self._listX2Index, 16)
            if(retValue): return retValue.contents.value
            return None
        def set_layer4Opacity(self, nValue):
            CBash.SetFIDListX2FieldF(self._CollectionIndex, self._ModName, self._recordID, 15, self._listIndex, 0, self._listX2Index, 16, c_float(nValue))
        layer4Opacity = property(get_layer4Opacity, set_layer4Opacity)
        def get_layer5Texture(self):
            CBash.ReadFIDListX2Field.restype = POINTER(c_uint)
            retValue = CBash.ReadFIDListX2Field(self._CollectionIndex, self._ModName, self._recordID, 15, self._listIndex, 0, self._listX2Index, 17)
            if(retValue): return retValue.contents.value
            return None
        def set_layer5Texture(self, nValue):
            CBash.SetFIDListX2FieldUI(self._CollectionIndex, self._ModName, self._recordID, 15, self._listIndex, 0, self._listX2Index, 17, nValue)
        layer5Texture = property(get_layer5Texture, set_layer5Texture)
        def get_layer5Opacity(self):
            CBash.ReadFIDListX2Field.restype = POINTER(c_float)
            retValue = CBash.ReadFIDListX2Field(self._CollectionIndex, self._ModName, self._recordID, 15, self._listIndex, 0, self._listX2Index, 18)
            if(retValue): return retValue.contents.value
            return None
        def set_layer5Opacity(self, nValue):
            CBash.SetFIDListX2FieldF(self._CollectionIndex, self._ModName, self._recordID, 15, self._listIndex, 0, self._listX2Index, 18, c_float(nValue))
        layer5Opacity = property(get_layer5Opacity, set_layer5Opacity)
        def get_layer6Texture(self):
            CBash.ReadFIDListX2Field.restype = POINTER(c_uint)
            retValue = CBash.ReadFIDListX2Field(self._CollectionIndex, self._ModName, self._recordID, 15, self._listIndex, 0, self._listX2Index, 19)
            if(retValue): return retValue.contents.value
            return None
        def set_layer6Texture(self, nValue):
            CBash.SetFIDListX2FieldUI(self._CollectionIndex, self._ModName, self._recordID, 15, self._listIndex, 0, self._listX2Index, 19, nValue)
        layer6Texture = property(get_layer6Texture, set_layer6Texture)
        def get_layer6Opacity(self):
            CBash.ReadFIDListX2Field.restype = POINTER(c_float)
            retValue = CBash.ReadFIDListX2Field(self._CollectionIndex, self._ModName, self._recordID, 15, self._listIndex, 0, self._listX2Index, 20)
            if(retValue): return retValue.contents.value
            return None
        def set_layer6Opacity(self, nValue):
            CBash.SetFIDListX2FieldF(self._CollectionIndex, self._ModName, self._recordID, 15, self._listIndex, 0, self._listX2Index, 20, c_float(nValue))
        layer6Opacity = property(get_layer6Opacity, set_layer6Opacity)
        def get_layer7Texture(self):
            CBash.ReadFIDListX2Field.restype = POINTER(c_uint)
            retValue = CBash.ReadFIDListX2Field(self._CollectionIndex, self._ModName, self._recordID, 15, self._listIndex, 0, self._listX2Index, 21)
            if(retValue): return retValue.contents.value
            return None
        def set_layer7Texture(self, nValue):
            CBash.SetFIDListX2FieldUI(self._CollectionIndex, self._ModName, self._recordID, 15, self._listIndex, 0, self._listX2Index, 21, nValue)
        layer7Texture = property(get_layer7Texture, set_layer7Texture)
        def get_layer7Opacity(self):
            CBash.ReadFIDListX2Field.restype = POINTER(c_float)
            retValue = CBash.ReadFIDListX2Field(self._CollectionIndex, self._ModName, self._recordID, 15, self._listIndex, 0, self._listX2Index, 22)
            if(retValue): return retValue.contents.value
            return None
        def set_layer7Opacity(self, nValue):
            CBash.SetFIDListX2FieldF(self._CollectionIndex, self._ModName, self._recordID, 15, self._listIndex, 0, self._listX2Index, 22, c_float(nValue))
        layer7Opacity = property(get_layer7Opacity, set_layer7Opacity)
        def get_layer8Texture(self):
            CBash.ReadFIDListX2Field.restype = POINTER(c_uint)
            retValue = CBash.ReadFIDListX2Field(self._CollectionIndex, self._ModName, self._recordID, 15, self._listIndex, 0, self._listX2Index, 23)
            if(retValue): return retValue.contents.value
            return None
        def set_layer8Texture(self, nValue):
            CBash.SetFIDListX2FieldUI(self._CollectionIndex, self._ModName, self._recordID, 15, self._listIndex, 0, self._listX2Index, 23, nValue)
        layer8Texture = property(get_layer8Texture, set_layer8Texture)
        def get_layer8Opacity(self):
            CBash.ReadFIDListX2Field.restype = POINTER(c_float)
            retValue = CBash.ReadFIDListX2Field(self._CollectionIndex, self._ModName, self._recordID, 15, self._listIndex, 0, self._listX2Index, 24)
            if(retValue): return retValue.contents.value
            return None
        def set_layer8Opacity(self, nValue):
            CBash.SetFIDListX2FieldF(self._CollectionIndex, self._ModName, self._recordID, 15, self._listIndex, 0, self._listX2Index, 24, c_float(nValue))
        layer8Opacity = property(get_layer8Opacity, set_layer8Opacity)

    def newBaseTexturesElement(self):
        listIndex = CBash.CreateFIDListElement(self._CollectionIndex, self._ModName, self._recordID, 12)
        if(listIndex == -1): return None
        return self.BaseTexture(self._CollectionIndex, self._ModName, self._recordID, 12, listIndex)
    def newAlphaLayersElement(self):
        listIndex = CBash.CreateFIDListElement(self._CollectionIndex, self._ModName, self._recordID, 13)
        if(listIndex == -1): return None
        return self.AlphaLayer(self._CollectionIndex, self._ModName, self._recordID, 13, listIndex)
    def newVertexTexturesElement(self):
        listIndex = CBash.CreateFIDListElement(self._CollectionIndex, self._ModName, self._recordID, 14)
        if(listIndex == -1): return None
        return self.VertexTexture(self._CollectionIndex, self._ModName, self._recordID, 14, listIndex)
    def get_data(self):
        numRecords = CBash.GetFIDFieldArraySize(self._CollectionIndex, self._ModName, self._recordID, 6)
        if(numRecords > 0):
            cRecords = POINTER(c_ubyte * numRecords)()
            CBash.GetFIDFieldArray(self._CollectionIndex, self._ModName, self._recordID, 6, byref(cRecords))
            return [cRecords.contents[x] for x in range(0, numRecords)]
        return []
    def set_data(self, nValue):
        length = len(nValue)
        CBash.SetFIDFieldR(self._CollectionIndex, self._ModName, self._recordID, 6, struct.pack('B' * length, *nValue), length)
    data = property(get_data, set_data)
    def get_normals(self):
        return [[self.Normal(self._CollectionIndex, self._ModName, self._recordID, x, y) for y in range(0,33)] for x in range(0,33)]
    def set_normals(self, nNormals):
        if(len(nNormals) != 33):
            return
        nValues = [(nNormal.x, nNormal.y, nNormal.z) for nNormal in nNormals]
        for oNormal, nValue in zip(self.normals, nValues):
            oNormal.x, oNormal.y, oNormal.z = nValue
    normals = property(get_normals, set_normals)
    def get_heights(self):
        return [[self.Height(self._CollectionIndex, self._ModName, self._recordID, x, y) for y in range(0,33)] for x in range(0,33)]
    def set_heights(self, nHeights):
        if(len(nNormals) != 33):
            return
        nValues = [nHeight.height for nHeight in nHeights]
        for oHeight, nValue in zip(self.heights, nValues):
            oHeight.height = nValue
    heights = property(get_heights, set_heights)
    def get_heightOffset(self):
        CBash.ReadFIDField.restype = POINTER(c_float)
        retValue = CBash.ReadFIDField(self._CollectionIndex, self._ModName, self._recordID, 8)
        if(retValue): return retValue.contents.value
        return None
    def set_heightOffset(self, nValue):
        CBash.SetFIDFieldF(self._CollectionIndex, self._ModName, self._recordID, 8, c_float(nValue))
    heightOffset = property(get_heightOffset, set_heightOffset)
    def get_unused1(self):
        numRecords = CBash.GetFIDFieldArraySize(self._CollectionIndex, self._ModName, self._recordID, 10)
        if(numRecords > 0):
            cRecords = POINTER(c_ubyte * numRecords)()
            CBash.GetFIDFieldArray(self._CollectionIndex, self._ModName, self._recordID, 10, byref(cRecords))
            return [cRecords.contents[x] for x in range(0, numRecords)]
        return []
    def set_unused1(self, nValue):
        CBash.SetFIDFieldR(self._CollectionIndex, self._ModName, self._recordID, 10, struct.pack('3B', *nValue), 3)
    unused1 = property(get_unused1, set_unused1)
    def get_colors(self):
        return [[self.Color(self._CollectionIndex, self._ModName, self._recordID, x, y)for y in range(0,33)]for x in range(0,33)]
    def set_colors(self, nColors):
        if(len(nColors) != 33):
            return
        nValues = [(nColor.red, nColor.green, nColor.blue) for nColor in nColors]
        for oColor, nValue in zip(self.colors, nValues):
            oColor.red, oColor.green, oColor.blue = nValue
    colors = property(get_colors, set_colors)
    def get_baseTextures(self):
        numRecords = CBash.GetFIDListSize(self._CollectionIndex, self._ModName, self._recordID, 12)
        if(numRecords > 0): return [self.BaseTexture(self._CollectionIndex, self._ModName, self._recordID, 12, x) for x in range(0, numRecords)]
        return []
    def set_baseTextures(self, nBaseTextures):
        diffLength = len(nBaseTextures) - CBash.GetFIDListSize(self._CollectionIndex, self._ModName, self._recordID, 12)
        nValues = [(nBaseTexture.texture, nBaseTexture.quadrant, nBaseTexture.unused1, nBaseTexture.layer) for nBaseTexture in nBaseTextures]
        while(diffLength < 0):
            CBash.DeleteFIDListElement(self._CollectionIndex, self._ModName, self._recordID, 12)
            diffLength += 1
        while(diffLength > 0):
            CBash.CreateFIDListElement(self._CollectionIndex, self._ModName, self._recordID, 12)
            diffLength -= 1
        for oBaseTexture, nValue in zip(self.baseTextures, nValues):
            oBaseTexture.texture, oBaseTexture.quadrant, oBaseTexture.unused1, oBaseTexture.layer = nValue
    baseTextures = property(get_baseTextures, set_baseTextures)
    def get_alphaLayers(self):
        numRecords = CBash.GetFIDListSize(self._CollectionIndex, self._ModName, self._recordID, 13)
        if(numRecords > 0): return [self.AlphaLayer(self._CollectionIndex, self._ModName, self._recordID, 13, x) for x in range(0, numRecords)]
        return []
    def set_alphaLayers(self, nAlphaLayers):
        diffLength = len(nAlphaLayers) - CBash.GetFIDListSize(self._CollectionIndex, self._ModName, self._recordID, 13)
        nValues = [(nAlphaLayer.texture, nAlphaLayer.quadrant, nAlphaLayer.unused1, nAlphaLayer.layer,
                  [(nOpacity.position, nOpacity.unused1, nOpacity.opacity) for nOpacity in nAlphaLayer.opacities]) for nAlphaLayer in nAlphaLayers]
        while(diffLength < 0):
            CBash.DeleteFIDListElement(self._CollectionIndex, self._ModName, self._recordID, 13)
            diffLength += 1
        while(diffLength > 0):
            CBash.CreateFIDListElement(self._CollectionIndex, self._ModName, self._recordID, 13)
            diffLength -= 1
        for oAlphaLayer, nValue in zip(self.alphaLayers, nValues):
            oAlphaLayer.texture = nValue[0]
            oAlphaLayer.quadrant = nValue[1]
            oAlphaLayer.unused1 = nValue[2]
            oAlphaLayer.layer = nValue[3]
            diffLength = len(nValue[4]) - CBash.GetFIDListX2Size(self._CollectionIndex, self._ModName, self._recordID, 13, oTarget._listIndex, 5)
            while(diffLength < 0):
                CBash.DeleteFIDListX2Element(self._CollectionIndex, self._ModName, self._recordID, 13, oTarget._listIndex, 5)
                diffLength += 1
            while(diffLength > 0):
                CBash.CreateFIDListX2Element(self._CollectionIndex, self._ModName, self._recordID, 13, oTarget._listIndex, 5)
                diffLength -= 1
            for oOpacity, eValue in zip(oAlphaLayer.opacities, nValue[4]):
                oOpacity.position, oOpacity.unused1, oOpacity.opacity = eValue
    alphaLayers = property(get_alphaLayers, set_alphaLayers)
    def get_vertexTextures(self):
        numRecords = CBash.GetFIDListSize(self._CollectionIndex, self._ModName, self._recordID, 14)
        if(numRecords > 0): return [self.BaseTexture(self._CollectionIndex, self._ModName, self._recordID, 14, x) for x in range(0, numRecords)]
        return []
    def set_vertexTextures(self, nVertexTextures):
        diffLength = len(nVertexTextures) - CBash.GetFIDListSize(self._CollectionIndex, self._ModName, self._recordID, 14)
        nValues = [nVertexTexture.texture for nVertexTexture in nVertexTextures]
        while(diffLength < 0):
            CBash.DeleteFIDListElement(self._CollectionIndex, self._ModName, self._recordID, 14)
            diffLength += 1
        while(diffLength > 0):
            CBash.CreateFIDListElement(self._CollectionIndex, self._ModName, self._recordID, 14)
            diffLength -= 1
        for oVertexTexture, nValue in zip(self.vertexTextures, nValues):
            oVertexTexture.texture = nValue
    vertexTextures = property(get_vertexTextures, set_vertexTextures)
    def get_positions(self):
        return [[self.Positions(self._CollectionIndex, self._ModName, self._recordID, row, column) for column in range(0,33)] for row in range(0,33)]
    def set_positions(self, nPositions):
        if(len(nPositions) != 33):
            return
        nValues = [(nPosition.height, nPosition.normalX, nPosition.normalY, nPosition.normalZ, nPosition.red, nPosition.green,
                    nPosition.blue, nPosition.baseTexture, nPosition.layer1Texture, nPosition.layer1Opacity, nPosition.layer2Texture, nPosition.layer2Opacity,
                    nPosition.layer3Texture, nPosition.layer3Opacity, nPosition.layer4Texture, nPosition.layer4Opacity, nPosition.layer5Texture, nPosition.layer5Opacity,
                    nPosition.layer6Texture, nPosition.layer6Opacity, nPosition.layer7Texture, nPosition.layer7Opacity, nPosition.layer8Texture, nPosition.layer8Opacity) for nPosition in nPositions]
        for oPosition, nValue in zip(self.Position, nValues):
            oPosition.height, oPosition.normalX, oPosition.normalY, oPosition.normalZ, oPosition.red, oPosition.green,
            oPosition.blue, oPosition.baseTexture, oPosition.layer1Texture, oPosition.layer1Opacity, oPosition.layer2Texture, oPosition.layer2Opacity,
            oPosition.layer3Texture, oPosition.layer3Opacity, oPosition.layer4Texture, oPosition.layer4Opacity, oPosition.layer5Texture, oPosition.layer5Opacity,
            oPosition.layer6Texture, oPosition.layer6Opacity, oPosition.layer7Texture, oPosition.layer7Opacity, oPosition.layer8Texture, oPosition.layer8Opacity = nValue
    Position = property(get_positions, set_positions)

class DIALRecord(BaseRecord):
    def CopyAsOverride(self, targetMod):
        FID = CBash.CopyDIALRecord(self._CollectionIndex, self._ModName, self._recordID, targetMod._ModName, c_bool(True))
        if(FID): return DIALRecord(self._CollectionIndex, targetMod._ModName, FID)
        return None
    def CopyAsNew(self, targetMod):
        FID = CBash.CopyDIALRecord(self._CollectionIndex, self._ModName, self._recordID, targetMod._ModName, c_bool(False))
        if(FID): return DIALRecord(self._CollectionIndex, targetMod._ModName, FID)
        return None
    def createINFORecord(self):
        FID = CBash.CreateINFORecord(self._CollectionIndex, self._ModName, self._recordID)
        if(FID): return INFORecord(self._CollectionIndex, self._ModName, FID)
        return None
    def get_quests(self):
        numRecords = CBash.GetFIDFieldArraySize(self._CollectionIndex, self._ModName, self._recordID, 6)
        if(numRecords > 0):
            cRecords = (POINTER(c_uint) * numRecords)()
            CBash.GetFIDFieldArray(self._CollectionIndex, self._ModName, self._recordID, 6, byref(cRecords))
            return [cRecords[x].contents.value for x in range(0, numRecords)]
        return []
    def set_quests(self, nValue):
        CBash.SetFIDFieldUIA(self._CollectionIndex, self._ModName, self._recordID, 6, struct.pack('I' * len(nValue), *nValue), len(nValue))
    quests = property(get_quests, set_quests)
    def get_full(self):
        CBash.ReadFIDField.restype = c_char_p
        return CBash.ReadFIDField(self._CollectionIndex, self._ModName, self._recordID, 7)
    def set_full(self, nValue):
        CBash.SetFIDFieldStr(self._CollectionIndex, self._ModName, self._recordID, 7, nValue)
    full = property(get_full, set_full)
    def get_dialType(self):
        CBash.ReadFIDField.restype = POINTER(c_ubyte)
        retValue = CBash.ReadFIDField(self._CollectionIndex, self._ModName, self._recordID, 8)
        if(retValue): return retValue.contents.value
        return None
    def set_dialType(self, nValue):
        CBash.SetFIDFieldUC(self._CollectionIndex, self._ModName, self._recordID, 8, c_ubyte(nValue))
    dialType = property(get_dialType, set_dialType)
    @property
    def INFO(self):
        numSubRecords = CBash.GetFIDFieldArraySize(self._CollectionIndex, self._ModName, self._recordID, 9)
        if(numSubRecords > 0):
            cRecords = (POINTER(c_uint) * numSubRecords)()
            CBash.GetFIDFieldArray(self._CollectionIndex, self._ModName, self._recordID, 9, byref(cRecords))
            return [INFORecord(self._CollectionIndex, self._ModName, x.contents.value) for x in cRecords]
        return []
    def get_IsTopic(self):
        return (self.dialType == 0)
    def set_IsTopic(self, nValue):
        if (nValue == True): self.dialType = 0
        elif(self.get_IsTopic()): self.IsConversation = True
    IsTopic = property(get_IsTopic, set_IsTopic)
    def get_IsConversation(self):
        return (self.dialType == 1)
    def set_IsConversation(self, nValue):
        if (nValue == True): self.dialType = 1
        elif(self.get_IsConversation()): self.IsTopic = True
    IsConversation = property(get_IsConversation, set_IsConversation)
    def get_IsCombat(self):
        return (self.dialType == 2)
    def set_IsCombat(self, nValue):
        if (nValue == True): self.dialType = 2
        elif(self.get_IsCombat()): self.IsTopic = True
    IsCombat = property(get_IsCombat, set_IsCombat)
    def get_IsPersuasion(self):
        return (self.dialType == 3)
    def set_IsPersuasion(self, nValue):
        if (nValue == True): self.dialType = 3
        elif(self.get_IsPersuasion()): self.IsTopic = True
    IsPersuasion = property(get_IsPersuasion, set_IsPersuasion)
    def get_IsDetection(self):
        return (self.dialType == 4)
    def set_IsDetection(self, nValue):
        if (nValue == True): self.dialType = 4
        elif(self.get_IsDetection()): self.IsTopic = True
    IsDetection = property(get_IsDetection, set_IsDetection)
    def get_IsService(self):
        return (self.dialType == 5)
    def set_IsService(self, nValue):
        if (nValue == True): self.dialType = 5
        elif(self.get_IsService()): self.IsTopic = True
    IsService = property(get_IsService, set_IsService)
    def get_IsMisc(self):
        return (self.dialType == 6)
    def set_IsMisc(self, nValue):
        if (nValue == True): self.dialType = 6
        elif(self.get_IsMisc()): self.IsTopic = True
    IsMisc = property(get_IsMisc, set_IsMisc)
    
class INFORecord(BaseRecord):
    def CopyAsOverride(self, targetDIAL):
        FID = CBash.CopyINFORecord(self._CollectionIndex, self._ModName, self._recordID, targetDIAL._ModName, targetDIAL._recordID, c_bool(True))
        if(FID): return INFORecord(self._CollectionIndex, targetDIAL._ModName, FID)
        return None
    def CopyAsNew(self, targetDIAL):
        FID = CBash.CopyINFORecord(self._CollectionIndex, self._ModName, self._recordID, targetDIAL._ModName, targetDIAL._recordID, c_bool(False))
        if(FID): return INFORecord(self._CollectionIndex, targetDIAL._ModName, FID)
        return None
    def DeleteRecord(self, parent):
        CBash.DeleteRecord(self._CollectionIndex, self._ModName, self._recordID, parent._recordID)
        return
    class Response(object):
        def __init__(self, CollectionIndex, ModName, recordID, listIndex):
            self._CollectionIndex = CollectionIndex
            self._ModName = ModName
            self._recordID = recordID
            self._listIndex = listIndex
        def get_emotionType(self):
            CBash.ReadFIDListField.restype = POINTER(c_uint)
            retValue = CBash.ReadFIDListField(self._CollectionIndex, self._ModName, self._recordID, 13, self._listIndex, 1)
            if(retValue): return retValue.contents.value
            return None
        def set_emotionType(self, nValue):
            CBash.SetFIDListFieldUI(self._CollectionIndex, self._ModName, self._recordID, 13, self._listIndex, 1, nValue)
        emotionType = property(get_emotionType, set_emotionType)
        def get_emotionValue(self):
            CBash.ReadFIDListField.restype = POINTER(c_int)
            retValue = CBash.ReadFIDListField(self._CollectionIndex, self._ModName, self._recordID, 13, self._listIndex, 2)
            if(retValue): return retValue.contents.value
            return None
        def set_emotionValue(self, nValue):
            CBash.SetFIDListFieldI(self._CollectionIndex, self._ModName, self._recordID, 13, self._listIndex, 2, nValue)
        emotionValue = property(get_emotionValue, set_emotionValue)
        def get_unused1(self):
            numRecords = CBash.GetFIDListArraySize(self._CollectionIndex, self._ModName, self._recordID, 13, self._listIndex, 3)
            if(numRecords > 0):
                cRecords = POINTER(c_ubyte * numRecords)()
                CBash.GetFIDListArray(self._CollectionIndex, self._ModName, self._recordID, 13, self._listIndex, 3, byref(cRecords))
                return [cRecords.contents[x] for x in range(0, numRecords)]
            return []
        def set_unused1(self, nValue):
            CBash.SetFIDListFieldR(self._CollectionIndex, self._ModName, self._recordID, 13, self._listIndex, 3, struct.pack('4B', *nValue), 4)
        unused1 = property(get_unused1, set_unused1)
        def get_responseNum(self):
            CBash.ReadFIDListField.restype = POINTER(c_ubyte)
            retValue = CBash.ReadFIDListField(self._CollectionIndex, self._ModName, self._recordID, 13, self._listIndex, 4)
            if(retValue): return retValue.contents.value
            return None
        def set_responseNum(self, nValue):
            CBash.SetFIDListFieldUC(self._CollectionIndex, self._ModName, self._recordID, 13, self._listIndex, 4, c_ubyte(nValue))
        responseNum = property(get_responseNum, set_responseNum)
        def get_unused2(self):
            numRecords = CBash.GetFIDListArraySize(self._CollectionIndex, self._ModName, self._recordID, 13, self._listIndex, 5)
            if(numRecords > 0):
                cRecords = POINTER(c_ubyte * numRecords)()
                CBash.GetFIDListArray(self._CollectionIndex, self._ModName, self._recordID, 13, self._listIndex, 5, byref(cRecords))
                return [cRecords.contents[x] for x in range(0, numRecords)]
            return []
        def set_unused2(self, nValue):
            CBash.SetFIDListFieldR(self._CollectionIndex, self._ModName, self._recordID, 13, self._listIndex, 5, struct.pack('3B', *nValue), 3)
        unused2 = property(get_unused2, set_unused2)
        def get_responseText(self):
            CBash.ReadFIDListField.restype = c_char_p
            return CBash.ReadFIDListField(self._CollectionIndex, self._ModName, self._recordID, 13, self._listIndex, 6)
        def set_responseText(self, nValue):
            CBash.SetFIDListFieldStr(self._CollectionIndex, self._ModName, self._recordID, 13, self._listIndex, 6, nValue)
        responseText = property(get_responseText, set_responseText)
        def get_actorNotes(self):
            CBash.ReadFIDListField.restype = c_char_p
            return CBash.ReadFIDListField(self._CollectionIndex, self._ModName, self._recordID, 13, self._listIndex, 7)
        def set_actorNotes(self, nValue):
            CBash.SetFIDListFieldStr(self._CollectionIndex, self._ModName, self._recordID, 13, self._listIndex, 7, nValue)
        actorNotes = property(get_actorNotes, set_actorNotes)
        def get_IsNeutral(self):
            return (self.emotionType == 0)
        def set_IsNeutral(self, nValue):
            if (nValue == True): self.emotionType = 0
            elif(self.get_IsNeutral()): self.IsAnger = True
        IsNeutral = property(get_IsNeutral, set_IsNeutral)
        def get_IsAnger(self):
            return (self.emotionType == 1)
        def set_IsAnger(self, nValue):
            if (nValue == True): self.emotionType = 1
            elif(self.get_IsAnger()): self.IsNeutral = True
        IsAnger = property(get_IsAnger, set_IsAnger)
        def get_IsDisgust(self):
            return (self.emotionType == 2)
        def set_IsDisgust(self, nValue):
            if (nValue == True): self.emotionType = 2
            elif(self.get_IsDisgust()): self.IsNeutral = True
        IsDisgust = property(get_IsDisgust, set_IsDisgust)
        def get_IsFear(self):
            return (self.emotionType == 3)
        def set_IsFear(self, nValue):
            if (nValue == True): self.emotionType = 3
            elif(self.get_IsFear()): self.IsNeutral = True
        IsFear = property(get_IsFear, set_IsFear)
        def get_IsSad(self):
            return (self.emotionType == 4)
        def set_IsSad(self, nValue):
            if (nValue == True): self.emotionType = 4
            elif(self.get_IsSad()): self.IsNeutral = True
        IsSad = property(get_IsSad, set_IsSad)
        def get_IsHappy(self):
            return (self.emotionType == 5)
        def set_IsHappy(self, nValue):
            if (nValue == True): self.emotionType = 5
            elif(self.get_IsHappy()): self.IsNeutral = True
        IsHappy = property(get_IsHappy, set_IsHappy)
        def get_IsSurprise(self):
            return (self.emotionType == 6)
        def set_IsSurprise(self, nValue):
            if (nValue == True): self.emotionType = 6
            elif(self.get_IsSurprise()): self.IsNeutral = True
        IsSurprise = property(get_IsSurprise, set_IsSurprise)
    class Condition(object):
        def __init__(self, CollectionIndex, ModName, recordID, subField, listIndex):
            self._CollectionIndex = CollectionIndex
            self._ModName = ModName
            self._recordID = recordID
            self._subField = subField
            self._listIndex = listIndex
        def get_operType(self):
            CBash.ReadFIDListField.restype = POINTER(c_ubyte)
            retValue = CBash.ReadFIDListField(self._CollectionIndex, self._ModName, self._recordID, self._subField, self._listIndex, 1)
            if(retValue): return retValue.contents.value
            return None
        def set_operType(self, nValue):
            CBash.SetFIDListFieldUC(self._CollectionIndex, self._ModName, self._recordID, self._subField, self._listIndex, 1, c_ubyte(nValue))
        operType = property(get_operType, set_operType)
        def get_unused1(self):
            numRecords = CBash.GetFIDListArraySize(self._CollectionIndex, self._ModName, self._recordID, self._subField, self._listIndex, 2)
            if(numRecords > 0):
                cRecords = POINTER(c_ubyte * numRecords)()
                CBash.GetFIDListArray(self._CollectionIndex, self._ModName, self._recordID, self._subField, self._listIndex, 2, byref(cRecords))
                return [cRecords.contents[x] for x in range(0, numRecords)]
            return []
        def set_unused1(self, nValue):
            CBash.SetFIDListFieldR(self._CollectionIndex, self._ModName, self._recordID, self._subField, self._listIndex, 2, struct.pack('3B', *nValue), 3)
        unused1 = property(get_unused1, set_unused1)
        def get_compValue(self):
            CBash.ReadFIDListField.restype = POINTER(c_float)
            retValue = CBash.ReadFIDListField(self._CollectionIndex, self._ModName, self._recordID, self._subField, self._listIndex, 3)
            if(retValue): return retValue.contents.value
            return None
        def set_compValue(self, nValue):
            CBash.SetFIDListFieldF(self._CollectionIndex, self._ModName, self._recordID, self._subField, self._listIndex, 3, c_float(nValue))
        compValue = property(get_compValue, set_compValue)
        def get_ifunc(self):
            CBash.ReadFIDListField.restype = POINTER(c_uint)
            retValue = CBash.ReadFIDListField(self._CollectionIndex, self._ModName, self._recordID, self._subField, self._listIndex, 4)
            if(retValue): return retValue.contents.value
            return None
        def set_ifunc(self, nValue):
            CBash.SetFIDListFieldUI(self._CollectionIndex, self._ModName, self._recordID, self._subField, self._listIndex, 4, nValue)
        ifunc = property(get_ifunc, set_ifunc)
        def get_param1(self):
            CBash.ReadFIDListField.restype = POINTER(c_uint)
            retValue = CBash.ReadFIDListField(self._CollectionIndex, self._ModName, self._recordID, self._subField, self._listIndex, 5)
            if(retValue): return retValue.contents.value
            return None
        def set_param1(self, nValue):
            CBash.SetFIDListFieldUI(self._CollectionIndex, self._ModName, self._recordID, self._subField, self._listIndex, 5, nValue)
        param1 = property(get_param1, set_param1)
        def get_param2(self):
            CBash.ReadFIDListField.restype = POINTER(c_uint)
            retValue = CBash.ReadFIDListField(self._CollectionIndex, self._ModName, self._recordID, self._subField, self._listIndex, 6)
            if(retValue): return retValue.contents.value
            return None
        def set_param2(self, nValue):
            CBash.SetFIDListFieldUI(self._CollectionIndex, self._ModName, self._recordID, self._subField, self._listIndex, 6, nValue)
        param2 = property(get_param2, set_param2)
        def get_unused2(self):
            numRecords = CBash.GetFIDListArraySize(self._CollectionIndex, self._ModName, self._recordID, self._subField, self._listIndex, 7)
            if(numRecords > 0):
                cRecords = POINTER(c_ubyte * numRecords)()
                CBash.GetFIDListArray(self._CollectionIndex, self._ModName, self._recordID, self._subField, self._listIndex, 7, byref(cRecords))
                return [cRecords.contents[x] for x in range(0, numRecords)]
            return []
        def set_unused2(self, nValue):
            CBash.SetFIDListFieldR(self._CollectionIndex, self._ModName, self._recordID, self._subField, self._listIndex, 7, struct.pack('4B', *nValue), 4)
        unused2 = property(get_unused2, set_unused2)
        def get_IsEqual(self):
            return ((self.operType & 0xF0) == 0x00000000)
        def set_IsEqual(self, nValue):
            if (nValue == True):
                self.operType &= 0x0F
                self.operType |= 0x00000000
            elif(self.get_IsEqual()): self.IsNotEqual = True
        IsEqual = property(get_IsEqual, set_IsEqual)
        def get_IsNotEqual(self):
            return ((self.operType & 0xF0) == 0x00000020)
        def set_IsNotEqual(self, nValue):
            if (nValue == True):
                self.operType &= 0x0F
                self.operType |= 0x00000020
            elif(self.get_IsNotEqual()): self.IsEqual = True
        IsNotEqual = property(get_IsNotEqual, set_IsNotEqual)
        def get_IsGreater(self):
            return ((self.operType & 0xF0) == 0x00000040)
        def set_IsGreater(self, nValue):
            if (nValue == True):
                self.operType &= 0x0F
                self.operType |= 0x00000040
            elif(self.get_IsGreater()): self.IsEqual = True
        IsGreater = property(get_IsGreater, set_IsGreater)
        def get_IsGreaterOrEqual(self):
            return ((self.operType & 0xF0) == 0x00000060)
        def set_IsGreaterOrEqual(self, nValue):
            if (nValue == True):
                self.operType &= 0x0F
                self.operType |= 0x00000060
            elif(self.get_IsGreaterOrEqual()): self.IsEqual = True
        IsGreaterOrEqual = property(get_IsGreaterOrEqual, set_IsGreaterOrEqual)
        def get_IsLess(self):
            return ((self.operType & 0xF0) == 0x00000080)
        def set_IsLess(self, nValue):
            if (nValue == True):
                self.operType &= 0x0F
                self.operType |= 0x00000080
            elif(self.get_IsLess()): self.IsEqual = True
        IsLess = property(get_IsLess, set_IsLess)
        def get_IsLessOrEqual(self):
            return ((self.operType & 0xF0) == 0x000000A0)
        def set_IsLessOrEqual(self, nValue):
            if (nValue == True):
                self.operType &= 0x0F
                self.operType |= 0x000000A0
            elif(self.get_IsLessOrEqual()): self.IsEqual = True
        IsLessOrEqual = property(get_IsLessOrEqual, set_IsLessOrEqual)        
        def IsType(self, nValue):
            return ((self.operType & 0xF0) == (nValue & 0xF0))
        def SetType(self, nValue):
            nValue &= 0xF0
            self.operType &= 0x0F
            self.operType |= nValue
        def get_IsNone(self):
            return ((self.operType & 0x0F) == 0x00000000)
        def set_IsNone(self, nValue):
            if (nValue == True): self.operType &= 0xF0
        IsNone = property(get_IsNone, set_IsNone)
        def get_IsOr(self):
            return ((self.operType & 0x0F) == 0x00000001)
        def set_IsOr(self, nValue):
            if (nValue == True): self.operType |= 0x00000001
            else: self.operType &= ~0x00000001
        IsOr = property(get_IsOr, set_IsOr)
        def get_IsRunOnTarget(self):
            return ((self.operType & 0x0F) == 0x00000002)
        def set_IsRunOnTarget(self, nValue):
            if (nValue == True): self.operType |= 0x00000002
            else: self.operType &= ~0x00000002
        IsRunOnTarget = property(get_IsRunOnTarget, set_IsRunOnTarget)
        def get_IsUseGlobal(self):
            return ((self.operType & 0x0F) == 0x00000004)
        def set_IsUseGlobal(self, nValue):
            if (nValue == True): self.operType |= 0x00000004
            else: self.operType &= ~0x00000004
        IsUseGlobal = property(get_IsUseGlobal, set_IsUseGlobal)
        def IsFlagMask(self, nValue, Exact=False):
            if(Exact): return ((self.operType & 0x0F) & (nValue & 0x0F)) == nValue
            return ((self.operType & 0x0F) & (nValue & 0x0F)) != 0
        def SetFlagMask(self, nValue):
            nValue &= 0x0F
            self.operType &= 0xF0
            self.operType |= nValue
        
    class Reference(object):
        def __init__(self, CollectionIndex, ModName, recordID, listIndex):
            self._CollectionIndex = CollectionIndex
            self._ModName = ModName
            self._recordID = recordID
            self._listIndex = listIndex
        def get_reference(self):
            CBash.ReadFIDListField.restype = POINTER(c_uint)
            retValue = CBash.ReadFIDListField(self._CollectionIndex, self._ModName, self._recordID, 24, self._listIndex, 1)
            if(retValue): return retValue.contents.value
            return None
        def set_reference(self, nValue):
            CBash.SetFIDListFieldUI(self._CollectionIndex, self._ModName, self._recordID, 24, self._listIndex, 1, nValue)
        reference = property(get_reference, set_reference)
        def get_IsSCRO(self):
            CBash.ReadFIDListField.restype = POINTER(c_bool)
            retValue = CBash.ReadFIDListField(self._CollectionIndex, self._ModName, self._recordID, 24, self._listIndex, 2)
            if(retValue): return retValue.contents.value
            return None
        def set_IsSCRO(self, nValue):
            if isinstance(nValue, bool):
                if(nValue): CBash.SetFIDListFieldUI(self._CollectionIndex, self._ModName, self._recordID, 24, self._listIndex, 2, 1)
                else: CBash.SetFIDListFieldUI(self._CollectionIndex, self._ModName, self._recordID, 24, self._listIndex, 2, 0)
            else: CBash.SetFIDListFieldUI(self._CollectionIndex, self._ModName, self._recordID, 24, self._listIndex, 2, nValue)
        IsSCRO = property(get_IsSCRO, set_IsSCRO)
    def newResponsesElement(self):
        listIndex = CBash.CreateFIDListElement(self._CollectionIndex, self._ModName, self._recordID, 13)
        if(listIndex == -1): return None
        return self.Response(self._CollectionIndex, self._ModName, self._recordID, listIndex)
    def newConditionsElement(self):
        listIndex = CBash.CreateFIDListElement(self._CollectionIndex, self._ModName, self._recordID, 14)
        if(listIndex == -1): return None
        return self.Condition(self._CollectionIndex, self._ModName, self._recordID, 14, listIndex)
    def newReferencesElement(self):
        listIndex = CBash.CreateFIDListElement(self._CollectionIndex, self._ModName, self._recordID, 24)
        if(listIndex == -1): return None
        return self.Reference(self._CollectionIndex, self._ModName, self._recordID, listIndex) 
    def get_dialType(self):
        CBash.ReadFIDField.restype = POINTER(c_ubyte)
        retValue = CBash.ReadFIDField(self._CollectionIndex, self._ModName, self._recordID, 6)
        if(retValue): return retValue.contents.value
        return None
    def set_dialType(self, nValue):
        CBash.SetFIDFieldUC(self._CollectionIndex, self._ModName, self._recordID, 6, c_ubyte(nValue))
    dialType = property(get_dialType, set_dialType)
    def get_flags(self):
        CBash.ReadFIDField.restype = POINTER(c_ubyte)
        retValue = CBash.ReadFIDField(self._CollectionIndex, self._ModName, self._recordID, 7)
        if(retValue): return retValue.contents.value
        return None
    def set_flags(self, nValue):
        CBash.SetFIDFieldUC(self._CollectionIndex, self._ModName, self._recordID, 7, c_ubyte(nValue))
    flags = property(get_flags, set_flags)
    def get_unused1(self):
        numRecords = CBash.GetFIDFieldArraySize(self._CollectionIndex, self._ModName, self._recordID, 8)
        if(numRecords > 0):
            cRecords = POINTER(c_ubyte * numRecords)()
            CBash.GetFIDFieldArray(self._CollectionIndex, self._ModName, self._recordID, 8, byref(cRecords))
            return [cRecords.contents[x] for x in range(0, numRecords)]
        return []
    def set_unused1(self, nValue):
        CBash.SetFIDFieldR(self._CollectionIndex, self._ModName, self._recordID, 8, struct.pack('B', *nValue), 1)
    unused1 = property(get_unused1, set_unused1)
    def get_quest(self):
        CBash.ReadFIDField.restype = POINTER(c_uint)
        retValue = CBash.ReadFIDField(self._CollectionIndex, self._ModName, self._recordID, 9)
        if(retValue): return retValue.contents.value
        return None
    def set_quest(self, nValue):
        CBash.SetFIDFieldUI(self._CollectionIndex, self._ModName, self._recordID, 9, nValue)
    quest = property(get_quest, set_quest)
    def get_topic(self):
        CBash.ReadFIDField.restype = POINTER(c_uint)
        retValue = CBash.ReadFIDField(self._CollectionIndex, self._ModName, self._recordID, 10)
        if(retValue): return retValue.contents.value
        return None
    def set_topic(self, nValue):
        CBash.SetFIDFieldUI(self._CollectionIndex, self._ModName, self._recordID, 10, nValue)
    topic = property(get_topic, set_topic)
    def get_prevInfo(self):
        CBash.ReadFIDField.restype = POINTER(c_uint)
        retValue = CBash.ReadFIDField(self._CollectionIndex, self._ModName, self._recordID, 11)
        if(retValue): return retValue.contents.value
        return None
    def set_prevInfo(self, nValue):
        CBash.SetFIDFieldUI(self._CollectionIndex, self._ModName, self._recordID, 11, nValue)
    prevInfo = property(get_prevInfo, set_prevInfo)
    def get_addTopics(self):
        numRecords = CBash.GetFIDFieldArraySize(self._CollectionIndex, self._ModName, self._recordID, 12)
        if(numRecords > 0):
            cRecords = (POINTER(c_uint) * numRecords)()
            CBash.GetFIDFieldArray(self._CollectionIndex, self._ModName, self._recordID, 12, byref(cRecords))
            return [cRecords[x].contents.value for x in range(0, numRecords)]
        return []
    def set_addTopics(self, nValue):
        CBash.SetFIDFieldUIA(self._CollectionIndex, self._ModName, self._recordID, 12, struct.pack('I' * len(nValue), *nValue), len(nValue))
    addTopics = property(get_addTopics, set_addTopics)
    def get_responses(self):
        numRecords = CBash.GetFIDListSize(self._CollectionIndex, self._ModName, self._recordID, 13)
        if(numRecords > 0): return [self.Response(self._CollectionIndex, self._ModName, self._recordID, x) for x in range(0, numRecords)]
        return []
    def set_responses(self, nResponses):
        diffLength = len(nResponses) - CBash.GetFIDListSize(self._CollectionIndex, self._ModName, self._recordID, 13)
        nValues = [(nResponse.emotionType, nResponse.emotionValue, nResponse.unused1, nResponse.responseNum, nResponse.unused2, nResponse.responseText, nResponse.actorNotes) for nResponse in nResponses]
        while(diffLength < 0):
            CBash.DeleteFIDListElement(self._CollectionIndex, self._ModName, self._recordID, 13)
            diffLength += 1
        while(diffLength > 0):
            CBash.CreateFIDListElement(self._CollectionIndex, self._ModName, self._recordID, 13)
            diffLength -= 1
        for oResponse, nValue in zip(self.responses, nValues):
            oResponse.emotionType, oResponse.emotionValue, oResponse.unused1, oResponse.responseNum, oResponse.unused2, oResponse.responseText, oResponse.actorNotes = nValue
    responses = property(get_responses, set_responses)    
    def get_conditions(self):
        numRecords = CBash.GetFIDListSize(self._CollectionIndex, self._ModName, self._recordID, 14)
        if(numRecords > 0): return [self.Condition(self._CollectionIndex, self._ModName, self._recordID, 14, x) for x in range(0, numRecords)]
        return []
    def set_conditions(self, nConditions):
        diffLength = len(nConditions) - CBash.GetFIDListSize(self._CollectionIndex, self._ModName, self._recordID, 14)
        nValues = [(nCondition.operType, nCondition.unused1, nCondition.compValue, nCondition.ifunc, nCondition.param1, nCondition.param2, nCondition.unused2) for nCondition in nConditions]
        while(diffLength < 0):
            CBash.DeleteFIDListElement(self._CollectionIndex, self._ModName, self._recordID, 14)
            diffLength += 1
        while(diffLength > 0):
            CBash.CreateFIDListElement(self._CollectionIndex, self._ModName, self._recordID, 14)
            diffLength -= 1
        for oCondition, nValue in zip(self.conditions, nValues):
            oCondition.operType, oCondition.unused1, oCondition.compValue, oCondition.ifunc, oCondition.param1, oCondition.param2, oCondition.unused2 = nValue
    conditions = property(get_conditions, set_conditions)
    def get_choices(self):
        numRecords = CBash.GetFIDFieldArraySize(self._CollectionIndex, self._ModName, self._recordID, 15)
        if(numRecords > 0):
            cRecords = (POINTER(c_uint) * numRecords)()
            CBash.GetFIDFieldArray(self._CollectionIndex, self._ModName, self._recordID, 15, byref(cRecords))
            return [cRecords[x].contents.value for x in range(0, numRecords)]
        return []
    def set_choices(self, nValue):
        CBash.SetFIDFieldUIA(self._CollectionIndex, self._ModName, self._recordID, 15, struct.pack('I' * len(nValue), *nValue), len(nValue))
    choices = property(get_choices, set_choices)
    def get_linksFrom(self):
        numRecords = CBash.GetFIDFieldArraySize(self._CollectionIndex, self._ModName, self._recordID, 16)
        if(numRecords > 0):
            cRecords = (POINTER(c_uint) * numRecords)()
            CBash.GetFIDFieldArray(self._CollectionIndex, self._ModName, self._recordID, 16, byref(cRecords))
            return [cRecords[x].contents.value for x in range(0, numRecords)]
        return []
    def set_linksFrom(self, nValue):
        CBash.SetFIDFieldUIA(self._CollectionIndex, self._ModName, self._recordID, 16, struct.pack('I' * len(nValue), *nValue), len(nValue))
    linksFrom = property(get_linksFrom, set_linksFrom)
    def get_unused2(self):
        numRecords = CBash.GetFIDFieldArraySize(self._CollectionIndex, self._ModName, self._recordID, 17)
        if(numRecords > 0):
            cRecords = POINTER(c_ubyte * numRecords)()
            CBash.GetFIDFieldArray(self._CollectionIndex, self._ModName, self._recordID, 17, byref(cRecords))
            return [cRecords.contents[x] for x in range(0, numRecords)]
        return []
    def set_unused2(self, nValue):
        CBash.SetFIDFieldR(self._CollectionIndex, self._ModName, self._recordID, 17, struct.pack('4B', *nValue), 4)
    unused2 = property(get_unused2, set_unused2)
    def get_numRefs(self):
        CBash.ReadFIDField.restype = POINTER(c_uint)
        retValue = CBash.ReadFIDField(self._CollectionIndex, self._ModName, self._recordID, 18)
        if(retValue): return retValue.contents.value
        return None
    def set_numRefs(self, nValue):
        CBash.SetFIDFieldUI(self._CollectionIndex, self._ModName, self._recordID, 18, nValue)
    numRefs = property(get_numRefs, set_numRefs)
    def get_compiledSize(self):
        CBash.ReadFIDField.restype = POINTER(c_uint)
        retValue = CBash.ReadFIDField(self._CollectionIndex, self._ModName, self._recordID, 19)
        if(retValue): return retValue.contents.value
        return None
    def set_compiledSize(self, nValue):
        CBash.SetFIDFieldUI(self._CollectionIndex, self._ModName, self._recordID, 19, nValue)
    compiledSize = property(get_compiledSize, set_compiledSize)
    def get_lastIndex(self):
        CBash.ReadFIDField.restype = POINTER(c_uint)
        retValue = CBash.ReadFIDField(self._CollectionIndex, self._ModName, self._recordID, 20)
        if(retValue): return retValue.contents.value
        return None
    def set_lastIndex(self, nValue):
        CBash.SetFIDFieldUI(self._CollectionIndex, self._ModName, self._recordID, 20, nValue)
    lastIndex = property(get_lastIndex, set_lastIndex)
    def get_scriptType(self):
        CBash.ReadFIDField.restype = POINTER(c_uint)
        retValue = CBash.ReadFIDField(self._CollectionIndex, self._ModName, self._recordID, 21)
        if(retValue): return retValue.contents.value
        return None
    def set_scriptType(self, nValue):
        CBash.SetFIDFieldUI(self._CollectionIndex, self._ModName, self._recordID, 21, nValue)
    scriptType = property(get_scriptType, set_scriptType)
    def get_compiled_p(self):
        numRecords = CBash.GetFIDFieldArraySize(self._CollectionIndex, self._ModName, self._recordID, 22)
        if(numRecords > 0):
            cRecords = POINTER(c_ubyte * numRecords)()
            CBash.GetFIDFieldArray(self._CollectionIndex, self._ModName, self._recordID, 22, byref(cRecords))
            return [cRecords.contents[x] for x in range(0, numRecords)]
        return []
    def set_compiled_p(self, nValue):
        length = len(nValue)
        CBash.SetFIDFieldR(self._CollectionIndex, self._ModName, self._recordID, 22, struct.pack('B' * length, *nValue), length)
    compiled_p = property(get_compiled_p, set_compiled_p)
    def get_scriptText(self):
        CBash.ReadFIDField.restype = c_char_p
        return CBash.ReadFIDField(self._CollectionIndex, self._ModName, self._recordID, 23)
    def set_scriptText(self, nValue):
        CBash.SetFIDFieldStr(self._CollectionIndex, self._ModName, self._recordID, 23, nValue)
    scriptText = property(get_scriptText, set_scriptText)
    def get_references(self):
        numRecords = CBash.GetFIDListSize(self._CollectionIndex, self._ModName, self._recordID, 24)
        if(numRecords > 0): return [self.Reference(self._CollectionIndex, self._ModName, self._recordID, x) for x in range(0, numRecords)]
        return []
    def set_references(self, nReferences):
        diffLength = len(nReferences) - CBash.GetFIDListSize(self._CollectionIndex, self._ModName, self._recordID, 24)
        nValues = [(nReference.reference,nReference.IsSCRO) for nReference in nReferences]
        while(diffLength < 0):
            CBash.DeleteFIDListElement(self._CollectionIndex, self._ModName, self._recordID, 24)
            diffLength += 1
        while(diffLength > 0):
            CBash.CreateFIDListElement(self._CollectionIndex, self._ModName, self._recordID, 24)
            diffLength -= 1
        for oReference, nValue in zip(self.references, nValues):
            oReference.reference, oReference.IsSCRO = nValue  
    references = property(get_references, set_references)
    def get_IsTopic(self):
        return (self.dialType == 0)
    def set_IsTopic(self, nValue):
        if (nValue == True): self.dialType = 0
        elif(self.get_IsTopic()): self.IsConversation = True
    IsTopic = property(get_IsTopic, set_IsTopic)
    def get_IsConversation(self):
        return (self.dialType == 1)
    def set_IsConversation(self, nValue):
        if (nValue == True): self.dialType = 1
        elif(self.get_IsConversation()): self.IsTopic = True
    IsConversation = property(get_IsConversation, set_IsConversation)
    def get_IsCombat(self):
        return (self.dialType == 2)
    def set_IsCombat(self, nValue):
        if (nValue == True): self.dialType = 2
        elif(self.get_IsCombat()): self.IsTopic = True
    IsCombat = property(get_IsCombat, set_IsCombat)
    def get_IsPersuasion(self):
        return (self.dialType == 3)
    def set_IsPersuasion(self, nValue):
        if (nValue == True): self.dialType = 3
        elif(self.get_IsPersuasion()): self.IsTopic = True
    IsPersuasion = property(get_IsPersuasion, set_IsPersuasion)
    def get_IsDetection(self):
        return (self.dialType == 4)
    def set_IsDetection(self, nValue):
        if (nValue == True): self.dialType = 4
        elif(self.get_IsDetection()): self.IsTopic = True
    IsDetection = property(get_IsDetection, set_IsDetection)
    def get_IsService(self):
        return (self.dialType == 5)
    def set_IsService(self, nValue):
        if (nValue == True): self.dialType = 5
        elif(self.get_IsService()): self.IsTopic = True
    IsService = property(get_IsService, set_IsService)
    def get_IsMisc(self):
        return (self.dialType == 6)
    def set_IsMisc(self, nValue):
        if (nValue == True): self.dialType = 6
        elif(self.get_IsMisc()): self.IsTopic = True
    IsMisc = property(get_IsMisc, set_IsMisc)
    def get_IsGoodbye(self):
        return (self.flags & 0x00000001) != 0
    def set_IsGoodbye(self, nValue):
        if (nValue == True): self.flags |= 0x00000001
        else: self.flags &= ~0x00000001
    IsGoodbye = property(get_IsGoodbye, set_IsGoodbye)
    def get_IsRandom(self):
        return (self.flags & 0x00000002) != 0
    def set_IsRandom(self, nValue):
        if (nValue == True): self.flags |= 0x00000002
        else: self.flags &= ~0x00000002
    IsRandom = property(get_IsRandom, set_IsRandom)
    def get_IsSayOnce(self):
        return (self.flags & 0x00000004) != 0
    def set_IsSayOnce(self, nValue):
        if (nValue == True): self.flags |= 0x00000004
        else: self.flags &= ~0x00000004
    IsSayOnce = property(get_IsSayOnce, set_IsSayOnce)
    def get_IsInfoRefusal(self):
        return (self.flags & 0x00000010) != 0
    def set_IsInfoRefusal(self, nValue):
        if (nValue == True): self.flags |= 0x00000010
        else: self.flags &= ~0x00000010
    IsInfoRefusal = property(get_IsInfoRefusal, set_IsInfoRefusal)
    def get_IsRandomEnd(self):
        return (self.flags & 0x00000020) != 0
    def set_IsRandomEnd(self, nValue):
        if (nValue == True): self.flags |= 0x00000020
        else: self.flags &= ~0x00000020
    IsRandomEnd = property(get_IsRandomEnd, set_IsRandomEnd)
    def get_IsRunForRumors(self):
        return (self.flags & 0x00000040) != 0
    def set_IsRunForRumors(self, nValue):
        if (nValue == True): self.flags |= 0x00000040
        else: self.flags &= ~0x00000040
    IsRunForRumors = property(get_IsRunForRumors, set_IsRunForRumors)
    
class QUSTRecord(BaseRecord):
    def CopyAsOverride(self, targetMod):
        FID = CBash.CopyQUSTRecord(self._CollectionIndex, self._ModName, self._recordID, targetMod._ModName, c_bool(True))
        if(FID): return QUSTRecord(self._CollectionIndex, targetMod._ModName, FID)
        return None
    def CopyAsNew(self, targetMod):
        FID = CBash.CopyQUSTRecord(self._CollectionIndex, self._ModName, self._recordID, targetMod._ModName, c_bool(False))
        if(FID): return QUSTRecord(self._CollectionIndex, targetMod._ModName, FID)
        return None
    class Condition(object):
        def __init__(self, CollectionIndex, ModName, recordID, subField, listIndex):
            self._CollectionIndex = CollectionIndex
            self._ModName = ModName
            self._recordID = recordID
            self._subField = subField
            self._listIndex = listIndex
        def get_operType(self):
            CBash.ReadFIDListField.restype = POINTER(c_ubyte)
            retValue = CBash.ReadFIDListField(self._CollectionIndex, self._ModName, self._recordID, self._subField, self._listIndex, 1)
            if(retValue): return retValue.contents.value
            return None
        def set_operType(self, nValue):
            CBash.SetFIDListFieldUC(self._CollectionIndex, self._ModName, self._recordID, self._subField, self._listIndex, 1, c_ubyte(nValue))
        operType = property(get_operType, set_operType)
        def get_unused1(self):
            numRecords = CBash.GetFIDListArraySize(self._CollectionIndex, self._ModName, self._recordID, self._subField, self._listIndex, 2)
            if(numRecords > 0):
                cRecords = POINTER(c_ubyte * numRecords)()
                CBash.GetFIDListArray(self._CollectionIndex, self._ModName, self._recordID, self._subField, self._listIndex, 2, byref(cRecords))
                return [cRecords.contents[x] for x in range(0, numRecords)]
            return []
        def set_unused1(self, nValue):
            CBash.SetFIDListFieldR(self._CollectionIndex, self._ModName, self._recordID, self._subField, self._listIndex, 2, struct.pack('3B', *nValue), 3)
        unused1 = property(get_unused1, set_unused1)
        def get_compValue(self):
            CBash.ReadFIDListField.restype = POINTER(c_float)
            retValue = CBash.ReadFIDListField(self._CollectionIndex, self._ModName, self._recordID, self._subField, self._listIndex, 3)
            if(retValue): return retValue.contents.value
            return None
        def set_compValue(self, nValue):
            CBash.SetFIDListFieldF(self._CollectionIndex, self._ModName, self._recordID, self._subField, self._listIndex, 3, c_float(nValue))
        compValue = property(get_compValue, set_compValue)
        def get_ifunc(self):
            CBash.ReadFIDListField.restype = POINTER(c_uint)
            retValue = CBash.ReadFIDListField(self._CollectionIndex, self._ModName, self._recordID, self._subField, self._listIndex, 4)
            if(retValue): return retValue.contents.value
            return None
        def set_ifunc(self, nValue):
            CBash.SetFIDListFieldUI(self._CollectionIndex, self._ModName, self._recordID, self._subField, self._listIndex, 4, nValue)
        ifunc = property(get_ifunc, set_ifunc)
        def get_param1(self):
            CBash.ReadFIDListField.restype = POINTER(c_uint)
            retValue = CBash.ReadFIDListField(self._CollectionIndex, self._ModName, self._recordID, self._subField, self._listIndex, 5)
            if(retValue): return retValue.contents.value
            return None
        def set_param1(self, nValue):
            CBash.SetFIDListFieldUI(self._CollectionIndex, self._ModName, self._recordID, self._subField, self._listIndex, 5, nValue)
        param1 = property(get_param1, set_param1)
        def get_param2(self):
            CBash.ReadFIDListField.restype = POINTER(c_uint)
            retValue = CBash.ReadFIDListField(self._CollectionIndex, self._ModName, self._recordID, self._subField, self._listIndex, 6)
            if(retValue): return retValue.contents.value
            return None
        def set_param2(self, nValue):
            CBash.SetFIDListFieldUI(self._CollectionIndex, self._ModName, self._recordID, self._subField, self._listIndex, 6, nValue)
        param2 = property(get_param2, set_param2)
        def get_unused2(self):
            numRecords = CBash.GetFIDListArraySize(self._CollectionIndex, self._ModName, self._recordID, self._subField, self._listIndex, 7)
            if(numRecords > 0):
                cRecords = POINTER(c_ubyte * numRecords)()
                CBash.GetFIDListArray(self._CollectionIndex, self._ModName, self._recordID, self._subField, self._listIndex, 7, byref(cRecords))
                return [cRecords.contents[x] for x in range(0, numRecords)]
            return []
        def set_unused2(self, nValue):
            CBash.SetFIDListFieldR(self._CollectionIndex, self._ModName, self._recordID, self._subField, self._listIndex, 7, struct.pack('4B', *nValue), 4)
        unused2 = property(get_unused2, set_unused2)
        def get_IsEqual(self):
            return ((self.operType & 0xF0) == 0x00000000)
        def set_IsEqual(self, nValue):
            if (nValue == True):
                self.operType &= 0x0F
                self.operType |= 0x00000000
            elif(self.get_IsEqual()): self.IsNotEqual = True
        IsEqual = property(get_IsEqual, set_IsEqual)
        def get_IsNotEqual(self):
            return ((self.operType & 0xF0) == 0x00000020)
        def set_IsNotEqual(self, nValue):
            if (nValue == True):
                self.operType &= 0x0F
                self.operType |= 0x00000020
            elif(self.get_IsNotEqual()): self.IsEqual = True
        IsNotEqual = property(get_IsNotEqual, set_IsNotEqual)
        def get_IsGreater(self):
            return ((self.operType & 0xF0) == 0x00000040)
        def set_IsGreater(self, nValue):
            if (nValue == True):
                self.operType &= 0x0F
                self.operType |= 0x00000040
            elif(self.get_IsGreater()): self.IsEqual = True
        IsGreater = property(get_IsGreater, set_IsGreater)
        def get_IsGreaterOrEqual(self):
            return ((self.operType & 0xF0) == 0x00000060)
        def set_IsGreaterOrEqual(self, nValue):
            if (nValue == True):
                self.operType &= 0x0F
                self.operType |= 0x00000060
            elif(self.get_IsGreaterOrEqual()): self.IsEqual = True
        IsGreaterOrEqual = property(get_IsGreaterOrEqual, set_IsGreaterOrEqual)
        def get_IsLess(self):
            return ((self.operType & 0xF0) == 0x00000080)
        def set_IsLess(self, nValue):
            if (nValue == True):
                self.operType &= 0x0F
                self.operType |= 0x00000080
            elif(self.get_IsLess()): self.IsEqual = True
        IsLess = property(get_IsLess, set_IsLess)
        def get_IsLessOrEqual(self):
            return ((self.operType & 0xF0) == 0x000000A0)
        def set_IsLessOrEqual(self, nValue):
            if (nValue == True):
                self.operType &= 0x0F
                self.operType |= 0x000000A0
            elif(self.get_IsLessOrEqual()): self.IsEqual = True
        IsLessOrEqual = property(get_IsLessOrEqual, set_IsLessOrEqual)        
        def IsType(self, nValue):
            return ((self.operType & 0xF0) == (nValue & 0xF0))
        def SetType(self, nValue):
            nValue &= 0xF0
            self.operType &= 0x0F
            self.operType |= nValue
        def get_IsNone(self):
            return ((self.operType & 0x0F) == 0x00000000)
        def set_IsNone(self, nValue):
            if (nValue == True): self.operType &= 0xF0
        IsNone = property(get_IsNone, set_IsNone)
        def get_IsOr(self):
            return ((self.operType & 0x0F) == 0x00000001)
        def set_IsOr(self, nValue):
            if (nValue == True): self.operType |= 0x00000001
            else: self.operType &= ~0x00000001
        IsOr = property(get_IsOr, set_IsOr)
        def get_IsRunOnTarget(self):
            return ((self.operType & 0x0F) == 0x00000002)
        def set_IsRunOnTarget(self, nValue):
            if (nValue == True): self.operType |= 0x00000002
            else: self.operType &= ~0x00000002
        IsRunOnTarget = property(get_IsRunOnTarget, set_IsRunOnTarget)
        def get_IsUseGlobal(self):
            return ((self.operType & 0x0F) == 0x00000004)
        def set_IsUseGlobal(self, nValue):
            if (nValue == True): self.operType |= 0x00000004
            else: self.operType &= ~0x00000004
        IsUseGlobal = property(get_IsUseGlobal, set_IsUseGlobal)
        def IsFlagMask(self, nValue, Exact=False):
            if(Exact): return ((self.operType & 0x0F) & (nValue & 0x0F)) == nValue
            return ((self.operType & 0x0F) & (nValue & 0x0F)) != 0
        def SetFlagMask(self, nValue):
            nValue &= 0x0F
            self.operType &= 0xF0
            self.operType |= nValue
    class Stage(object):
        class Entry(object):
            class Condition(object):
                def __init__(self, CollectionIndex, ModName, recordID, listIndex, listX2Index, listX3Index):
                    self._CollectionIndex = CollectionIndex
                    self._ModName = ModName
                    self._recordID = recordID
                    self._listIndex = listIndex
                    self._listX2Index = listX2Index
                    self._listX3Index = listX3Index
                def get_operType(self):
                    CBash.ReadFIDListX3Field.restype = POINTER(c_ubyte)
                    retValue = CBash.ReadFIDListX3Field(self._CollectionIndex, self._ModName, self._recordID, 12, self._listIndex, 2, self._listX2Index, 2, self._listX3Index, 1)
                    if(retValue): return retValue.contents.value
                    return None
                def set_operType(self, nValue):
                    CBash.SetFIDListX3FieldUC(self._CollectionIndex, self._ModName, self._recordID, 12, self._listIndex, 2, self._listX2Index, 2, self._listX3Index, 1, c_ubyte(nValue))
                operType = property(get_operType, set_operType)
                def get_unused1(self):
                    numRecords = CBash.GetFIDListX3ArraySize(self._CollectionIndex, self._ModName, self._recordID, 12, self._listIndex, 2, self._listX2Index, 2, self._listX3Index, 2)
                    if(numRecords > 0):
                        cRecords = POINTER(c_ubyte * numRecords)()
                        CBash.GetFIDListX3Array(self._CollectionIndex, self._ModName, self._recordID, 12, self._listIndex, 2, self._listX2Index, 2, self._listX3Index, 2, byref(cRecords))
                        return [cRecords.contents[x] for x in range(0, numRecords)]
                    else:
                        return []
                def set_unused1(self, nValue):
                    CBash.SetFIDListX3FieldR(self._CollectionIndex, self._ModName, self._recordID, 12, self._listIndex, 2, self._listX2Index, 2, self._listX3Index, 2, struct.pack('3B', *nValue), 3)
                unused1 = property(get_unused1, set_unused1)
                def get_compValue(self):
                    CBash.ReadFIDListX3Field.restype = POINTER(c_float)
                    retValue = CBash.ReadFIDListX3Field(self._CollectionIndex, self._ModName, self._recordID, 12, self._listIndex, 2, self._listX2Index, 2, self._listX3Index, 3)
                    if(retValue): return retValue.contents.value
                    return None
                def set_compValue(self, nValue):
                    CBash.SetFIDListX3FieldF(self._CollectionIndex, self._ModName, self._recordID, 12, self._listIndex, 2, self._listX2Index, 2, self._listX3Index, 3, c_float(nValue))
                compValue = property(get_compValue, set_compValue)
                def get_ifunc(self):
                    CBash.ReadFIDListX3Field.restype = POINTER(c_uint)
                    retValue = CBash.ReadFIDListX3Field(self._CollectionIndex, self._ModName, self._recordID, 12, self._listIndex, 2, self._listX2Index, 2, self._listX3Index, 4)
                    if(retValue): return retValue.contents.value
                    return None
                def set_ifunc(self, nValue):
                    CBash.SetFIDListX3FieldUI(self._CollectionIndex, self._ModName, self._recordID, 12, self._listIndex, 2, self._listX2Index, 2, self._listX3Index, 4, nValue)
                ifunc = property(get_ifunc, set_ifunc)
                def get_param1(self):
                    CBash.ReadFIDListX3Field.restype = POINTER(c_uint)
                    retValue = CBash.ReadFIDListX3Field(self._CollectionIndex, self._ModName, self._recordID, 12, self._listIndex, 2, self._listX2Index, 2, self._listX3Index, 5)
                    if(retValue): return retValue.contents.value
                    return None
                def set_param1(self, nValue):
                    CBash.SetFIDListX3FieldUI(self._CollectionIndex, self._ModName, self._recordID, 12, self._listIndex, 2, self._listX2Index, 2, self._listX3Index, 5, nValue)
                param1 = property(get_param1, set_param1)
                def get_param2(self):
                    CBash.ReadFIDListX3Field.restype = POINTER(c_uint)
                    retValue = CBash.ReadFIDListX3Field(self._CollectionIndex, self._ModName, self._recordID, 12, self._listIndex, 2, self._listX2Index, 2, self._listX3Index, 6)
                    if(retValue): return retValue.contents.value
                    return None
                def set_param2(self, nValue):
                    CBash.SetFIDListX3FieldUI(self._CollectionIndex, self._ModName, self._recordID, 12, self._listIndex, 2, self._listX2Index, 2, self._listX3Index, 6, nValue)
                param2 = property(get_param2, set_param2)
                def get_unused2(self):
                    numRecords = CBash.GetFIDListX3ArraySize(self._CollectionIndex, self._ModName, self._recordID, 12, self._listIndex, 2, self._listX2Index, 2, self._listX3Index, 7)
                    if(numRecords > 0):
                        cRecords = POINTER(c_ubyte * numRecords)()
                        CBash.GetFIDListX3Array(self._CollectionIndex, self._ModName, self._recordID, 12, self._listIndex, 2, self._listX2Index, 2, self._listX3Index, 7, byref(cRecords))
                        return [cRecords.contents[x] for x in range(0, numRecords)]
                    else:
                        return []
                def set_unused2(self, nValue):
                    CBash.SetFIDListX3FieldR(self._CollectionIndex, self._ModName, self._recordID, 12, self._listIndex, 2, self._listX2Index, 2, self._listX3Index, 7, struct.pack('4B', *nValue), 4)
                unused2 = property(get_unused2, set_unused2)
                def get_IsEqual(self):
                    return ((self.operType & 0xF0) == 0x00000000)
                def set_IsEqual(self, nValue):
                    if (nValue == True):
                        self.operType &= 0x0F
                        self.operType |= 0x00000000
                    elif(self.get_IsEqual()): self.IsNotEqual = True
                IsEqual = property(get_IsEqual, set_IsEqual)
                def get_IsNotEqual(self):
                    return ((self.operType & 0xF0) == 0x00000020)
                def set_IsNotEqual(self, nValue):
                    if (nValue == True):
                        self.operType &= 0x0F
                        self.operType |= 0x00000020
                    elif(self.get_IsNotEqual()): self.IsEqual = True
                IsNotEqual = property(get_IsNotEqual, set_IsNotEqual)
                def get_IsGreater(self):
                    return ((self.operType & 0xF0) == 0x00000040)
                def set_IsGreater(self, nValue):
                    if (nValue == True):
                        self.operType &= 0x0F
                        self.operType |= 0x00000040
                    elif(self.get_IsGreater()): self.IsEqual = True
                IsGreater = property(get_IsGreater, set_IsGreater)
                def get_IsGreaterOrEqual(self):
                    return ((self.operType & 0xF0) == 0x00000060)
                def set_IsGreaterOrEqual(self, nValue):
                    if (nValue == True):
                        self.operType &= 0x0F
                        self.operType |= 0x00000060
                    elif(self.get_IsGreaterOrEqual()): self.IsEqual = True
                IsGreaterOrEqual = property(get_IsGreaterOrEqual, set_IsGreaterOrEqual)
                def get_IsLess(self):
                    return ((self.operType & 0xF0) == 0x00000080)
                def set_IsLess(self, nValue):
                    if (nValue == True):
                        self.operType &= 0x0F
                        self.operType |= 0x00000080
                    elif(self.get_IsLess()): self.IsEqual = True
                IsLess = property(get_IsLess, set_IsLess)
                def get_IsLessOrEqual(self):
                    return ((self.operType & 0xF0) == 0x000000A0)
                def set_IsLessOrEqual(self, nValue):
                    if (nValue == True):
                        self.operType &= 0x0F
                        self.operType |= 0x000000A0
                    elif(self.get_IsLessOrEqual()): self.IsEqual = True
                IsLessOrEqual = property(get_IsLessOrEqual, set_IsLessOrEqual)        
                def IsType(self, nValue):
                    return ((self.operType & 0xF0) == (nValue & 0xF0))
                def SetType(self, nValue):
                    nValue &= 0xF0
                    self.operType &= 0x0F
                    self.operType |= nValue
                def get_IsNone(self):
                    return ((self.operType & 0x0F) == 0x00000000)
                def set_IsNone(self, nValue):
                    if (nValue == True): self.operType &= 0xF0
                IsNone = property(get_IsNone, set_IsNone)
                def get_IsOr(self):
                    return ((self.operType & 0x0F) == 0x00000001)
                def set_IsOr(self, nValue):
                    if (nValue == True): self.operType |= 0x00000001
                    else: self.operType &= ~0x00000001
                IsOr = property(get_IsOr, set_IsOr)
                def get_IsRunOnTarget(self):
                    return ((self.operType & 0x0F) == 0x00000002)
                def set_IsRunOnTarget(self, nValue):
                    if (nValue == True): self.operType |= 0x00000002
                    else: self.operType &= ~0x00000002
                IsRunOnTarget = property(get_IsRunOnTarget, set_IsRunOnTarget)
                def get_IsUseGlobal(self):
                    return ((self.operType & 0x0F) == 0x00000004)
                def set_IsUseGlobal(self, nValue):
                    if (nValue == True): self.operType |= 0x00000004
                    else: self.operType &= ~0x00000004
                IsUseGlobal = property(get_IsUseGlobal, set_IsUseGlobal)
                def IsFlagMask(self, nValue, Exact=False):
                    if(Exact): return ((self.operType & 0x0F) & (nValue & 0x0F)) == nValue
                    return ((self.operType & 0x0F) & (nValue & 0x0F)) != 0
                def SetFlagMask(self, nValue):
                    nValue &= 0x0F
                    self.operType &= 0xF0
                    self.operType |= nValue

            class Reference(object):
                def __init__(self, CollectionIndex, ModName, recordID, listIndex, listX2Index, listX3Index):
                    self._CollectionIndex = CollectionIndex
                    self._ModName = ModName
                    self._recordID = recordID
                    self._listIndex = listIndex
                    self._listX2Index = listX2Index
                    self._listX3Index = listX3Index
                def get_reference(self):
                    CBash.ReadFIDListX3Field.restype = POINTER(c_uint)
                    retValue = CBash.ReadFIDListX3Field(self._CollectionIndex, self._ModName, self._recordID, 12, self._listIndex, 2, self._listX2Index, 11, self._listX3Index, 1)
                    if(retValue): return retValue.contents.value
                    return None
                def set_reference(self, nValue):
                    CBash.SetFIDListX3FieldUI(self._CollectionIndex, self._ModName, self._recordID, 12, self._listIndex, 2, self._listX2Index, 11, self._listX3Index, 1, nValue)
                reference = property(get_reference, set_reference)
                def get_IsSCRO(self):
                    CBash.ReadFIDListX3Field.restype = POINTER(c_bool)
                    retValue = CBash.ReadFIDListX3Field(self._CollectionIndex, self._ModName, self._recordID, 12, self._listIndex, 2, self._listX2Index, 11, self._listX3Index, 2)
                    if(retValue): return retValue.contents.value
                    return None
                def set_IsSCRO(self, nValue):
                    if isinstance(nValue, bool):
                        if(nValue):
                            CBash.SetFIDListX3FieldUI(self._CollectionIndex, self._ModName, self._recordID, 12, self._listIndex, 2, self._listX2Index, 11, self._listX3Index, 2, 1)
                        else:
                            CBash.SetFIDListX3FieldUI(self._CollectionIndex, self._ModName, self._recordID, 12, self._listIndex, 2, self._listX2Index, 11, self._listX3Index, 2, 0)
                    else:
                        CBash.SetFIDListX3FieldUI(self._CollectionIndex, self._ModName, self._recordID, 12, self._listIndex, 2, self._listX2Index, 11, self._listX3Index, 2, nValue)
                IsSCRO = property(get_IsSCRO, set_IsSCRO)
            def __init__(self, CollectionIndex, ModName, recordID, listIndex, listX2Index):
                self._CollectionIndex = CollectionIndex
                self._ModName = ModName
                self._recordID = recordID
                self._listIndex = listIndex
                self._listX2Index = listX2Index
            def newConditionsElement(self):
                listX3Index = CBash.CreateFIDListX3Element(self._CollectionIndex, self._ModName, self._recordID, 12, self._listIndex, 2, self._listX2Index, 2)
                if(listX3Index == -1):
                    return None
                return self.Condition(self._CollectionIndex, self._ModName, self._recordID, self._listIndex, self._listX2Index, listX3Index)
            def newReferencesElement(self):
                listX3Index = CBash.CreateFIDListX3Element(self._CollectionIndex, self._ModName, self._recordID, 12, self._listIndex, 2, self._listX2Index, 11)
                if(listX3Index == -1):
                    return None
                return self.Reference(self._CollectionIndex, self._ModName, self._recordID, self._listIndex, self._listX2Index, listX3Index)
                
            def get_flags(self):
                CBash.ReadFIDListX2Field.restype = POINTER(c_ubyte)
                retValue = CBash.ReadFIDListX2Field(self._CollectionIndex, self._ModName, self._recordID, 12, self._listIndex, 2, self._listX2Index, 1)
                if(retValue): return retValue.contents.value
                return None
            def set_flags(self, nValue):
                CBash.SetFIDListX2FieldUC(self._CollectionIndex, self._ModName, self._recordID, 12, self._listIndex, 2, self._listX2Index, 1, c_ubyte(nValue))
            flags = property(get_flags, set_flags)
            def get_conditions(self):
                numRecords = CBash.GetFIDListX3Size(self._CollectionIndex, self._ModName, self._recordID, 12, self._listIndex, 2, self._listX2Index, 2)
                if(numRecords > 0):
                    return [self.Condition(self._CollectionIndex, self._ModName, self._recordID, self._listIndex, self._listX2Index, x) for x in range(0, numRecords)]
                return []
            def set_conditions(self, nConditions):
                diffLength = len(nConditions) - CBash.GetFIDListX3Size(self._CollectionIndex, self._ModName, self._recordID, 12, self._listIndex, 2, self._listX2Index, 2)
                nValues = [(nCondition.operType, nCondition.unused1, nCondition.compValue, nCondition.ifunc, nCondition.param1, nCondition.param2, nCondition.unused2) for nCondition in nConditions]
                while(diffLength < 0):
                    CBash.DeleteFIDListX3Element(self._CollectionIndex, self._ModName, self._recordID, 12, self._listIndex, 2, self._listX2Index, 2)
                    diffLength += 1
                while(diffLength > 0):
                    CBash.CreateFIDListX3Element(self._CollectionIndex, self._ModName, self._recordID, 12, self._listIndex, 2, self._listX2Index, 2)
                    diffLength -= 1
                for oCondition, nValue in zip(self.conditions, nValues):
                    oCondition.operType, oCondition.unused1, oCondition.compValue, oCondition.ifunc, oCondition.param1, oCondition.param2, oCondition.unused2 = nValue
            conditions = property(get_conditions, set_conditions)
            def get_text(self):
                CBash.ReadFIDListX2Field.restype = c_char_p
                return CBash.ReadFIDListX2Field(self._CollectionIndex, self._ModName, self._recordID, 12, self._listIndex, 2, self._listX2Index, 3)
            def set_text(self, nValue):
                CBash.SetFIDListX2FieldStr(self._CollectionIndex, self._ModName, self._recordID, 12, self._listIndex, 2, self._listX2Index, 3, nValue)
            text = property(get_text, set_text)
            def get_unused1(self):
                numRecords = CBash.GetFIDListX2ArraySize(self._CollectionIndex, self._ModName, self._recordID, 12, self._listIndex, 2, self._listX2Index, 4)
                if(numRecords > 0):
                    cRecords = POINTER(c_ubyte * numRecords)()
                    CBash.GetFIDListX2Array(self._CollectionIndex, self._ModName, self._recordID, 12, self._listIndex, 2, self._listX2Index, 4, byref(cRecords))
                    return [cRecords.contents[x] for x in range(0, numRecords)]
                return []
            def set_unused1(self, nValue):
                CBash.SetFIDListX2FieldR(self._CollectionIndex, self._ModName, self._recordID, 12, self._listIndex, 2, self._listX2Index, 4, struct.pack('4B', *nValue), 4)
            unused1 = property(get_unused1, set_unused1)
            def get_numRefs(self):
                CBash.ReadFIDListX2Field.restype = POINTER(c_uint)
                retValue = CBash.ReadFIDListX2Field(self._CollectionIndex, self._ModName, self._recordID, 12, self._listIndex, 2, self._listX2Index, 5)
                if(retValue): return retValue.contents.value
                return None
            def set_numRefs(self, nValue):
                CBash.SetFIDListX2FieldUI(self._CollectionIndex, self._ModName, self._recordID, 12, self._listIndex, 2, self._listX2Index, 5, nValue)
            numRefs = property(get_numRefs, set_numRefs)
            def get_compiledSize(self):
                CBash.ReadFIDListX2Field.restype = POINTER(c_uint)
                retValue = CBash.ReadFIDListX2Field(self._CollectionIndex, self._ModName, self._recordID, 12, self._listIndex, 2, self._listX2Index, 6)
                if(retValue): return retValue.contents.value
                return None
            def set_compiledSize(self, nValue):
                CBash.SetFIDListX2FieldUI(self._CollectionIndex, self._ModName, self._recordID, 12, self._listIndex, 2, self._listX2Index, 6, nValue)
            compiledSize = property(get_compiledSize, set_compiledSize)
            def get_lastIndex(self):
                CBash.ReadFIDListX2Field.restype = POINTER(c_uint)
                retValue = CBash.ReadFIDListX2Field(self._CollectionIndex, self._ModName, self._recordID, 12, self._listIndex, 2, self._listX2Index, 7)
                if(retValue): return retValue.contents.value
                return None
            def set_lastIndex(self, nValue):
                CBash.SetFIDListX2FieldUI(self._CollectionIndex, self._ModName, self._recordID, 12, self._listIndex, 2, self._listX2Index, 7, nValue)
            lastIndex = property(get_lastIndex, set_lastIndex)
            def get_scriptType(self):
                CBash.ReadFIDListX2Field.restype = POINTER(c_uint)
                retValue = CBash.ReadFIDListX2Field(self._CollectionIndex, self._ModName, self._recordID, 12, self._listIndex, 2, self._listX2Index, 8)
                if(retValue): return retValue.contents.value
                return None
            def set_scriptType(self, nValue):
                CBash.SetFIDListX2FieldUI(self._CollectionIndex, self._ModName, self._recordID, 12, self._listIndex, 2, self._listX2Index, 8, nValue)
            scriptType = property(get_scriptType, set_scriptType)
            def get_compiled_p(self):
                numRecords = CBash.GetFIDListX2ArraySize(self._CollectionIndex, self._ModName, self._recordID, 12, self._listIndex, 2, self._listX2Index, 9)
                if(numRecords > 0):
                    cRecords = POINTER(c_ubyte * numRecords)()
                    CBash.GetFIDListX2Array(self._CollectionIndex, self._ModName, self._recordID, 12, self._listIndex, 2, self._listX2Index, 9, byref(cRecords))
                    return [cRecords.contents[x] for x in range(0, numRecords)]
                return []
            def set_compiled_p(self, nValue):
                length = len(nValue)
                CBash.SetFIDListX2FieldR(self._CollectionIndex, self._ModName, self._recordID, 12, self._listIndex, 2, self._listX2Index, 9, struct.pack('B' * length, *nValue), length)
            compiled_p = property(get_compiled_p, set_compiled_p)
            def get_scriptText(self):
                CBash.ReadFIDListX2Field.restype = c_char_p
                return CBash.ReadFIDListX2Field(self._CollectionIndex, self._ModName, self._recordID, 12, self._listIndex, 2, self._listX2Index, 10)
            def set_scriptText(self, nValue):
                CBash.SetFIDListX2FieldStr(self._CollectionIndex, self._ModName, self._recordID, 12, self._listIndex, 2, self._listX2Index, 10, nValue)
            scriptText = property(get_scriptText, set_scriptText)
            def get_references(self):
                numRecords = CBash.GetFIDListX3Size(self._CollectionIndex, self._ModName, self._recordID, 12, self._listIndex, 2, self._listX2Index, 11)
                if(numRecords > 0):
                    return [self.Reference(self._CollectionIndex, self._ModName, self._recordID, self._listIndex, self._listX2Index, x) for x in range(0, numRecords)]
                return []
            def set_references(self, nReferences):
                diffLength = len(nReferences) - CBash.GetFIDListX3Size(self._CollectionIndex, self._ModName, self._recordID, 12, self._listIndex, 2, self._listX2Index, 11)
                nValues = [(nReference.reference,nReference.IsSCRO) for nReference in nReferences]
                while(diffLength < 0):
                    CBash.DeleteFIDListX3Element(self._CollectionIndex, self._ModName, self._recordID, 12, self._listIndex, 2, self._listX2Index, 11)
                    diffLength += 1
                while(diffLength > 0):
                    CBash.CreateFIDListX3Element(self._CollectionIndex, self._ModName, self._recordID, 12, self._listIndex, 2, self._listX2Index, 11)
                    diffLength -= 1
                for oReference, nValue in zip(self.references, nValues):
                    oReference.reference, oReference.IsSCRO = nValue  
            references = property(get_references, set_references)
            def get_IsCompletes(self):
                return (self.flags & 0x00000001) != 0
            def set_IsCompletes(self, nValue):
                if (nValue == True): self.flags |= 0x00000001
                else: self.flags &= ~0x00000001
            IsCompletes = property(get_IsCompletes, set_IsCompletes)
        def __init__(self, CollectionIndex, ModName, recordID, listIndex):
            self._CollectionIndex = CollectionIndex
            self._ModName = ModName
            self._recordID = recordID
            self._listIndex = listIndex
        def newEntriesElement(self):
            listX2Index = CBash.CreateFIDListX2Element(self._CollectionIndex, self._ModName, self._recordID, 12, self._listIndex, 2)
            if(listX2Index == -1): return None
            return self.Entry(self._CollectionIndex, self._ModName, self._recordID, self._listIndex, listX2Index)
        def get_stage(self):
            CBash.ReadFIDListField.restype = POINTER(c_ushort)
            retValue = CBash.ReadFIDListField(self._CollectionIndex, self._ModName, self._recordID, 12, self._listIndex, 1)
            if(retValue): return retValue.contents.value
            return None
        def set_stage(self, nValue):
            CBash.SetFIDListFieldUS(self._CollectionIndex, self._ModName, self._recordID, 12, self._listIndex, 1, c_ushort(nValue))
        stage = property(get_stage, set_stage)
        def get_entries(self):
            numRecords = CBash.GetFIDListX2Size(self._CollectionIndex, self._ModName, self._recordID, 12, self._listIndex, 2)
            if(numRecords > 0): return [self.Entry(self._CollectionIndex, self._ModName, self._recordID, self._listIndex, x) for x in range(0, numRecords)]
            return []
        def set_entries(self, nEntries):
            diffLength = len(nEntries) - CBash.GetFIDListX2Size(self._CollectionIndex, self._ModName, self._recordID, 12, self._listIndex, 2)
            nValues = [(nEntry.flags,
                        [(nCondition.operType, nCondition.unused1, nCondition.compValue, nCondition.ifunc, 
                          nCondition.param1, nCondition.param2, nCondition.unused2) for nCondition in nEntry.conditions],
                        nEntry.text, nEntry.unused1, nEntry.numRefs, nEntry.compiledSize, nEntry.lastIndex, nEntry.scriptType, nEntry.compiled_p, nEntry.scriptText,
                        [(nReference.reference, nReference.IsSCRO) for nReference in nEntry.references]) for nEntry in nEntries]
            while(diffLength < 0):
                CBash.DeleteFIDListX2Element(self._CollectionIndex, self._ModName, self._recordID, 12, self._listIndex, 2)
                diffLength += 1
            while(diffLength > 0):
                CBash.CreateFIDListX2Element(self._CollectionIndex, self._ModName, self._recordID, 12, self._listIndex, 2)
                diffLength -= 1
            for oEntry, nValue in zip(self.entries, nValues):
                nEntry.flags = nValue[0]
                diffLength = len(nValue[1]) - CBash.GetFIDListX3Size(self._CollectionIndex, self._ModName, self._recordID, 12, oEntry._listIndex, 2, oEntry._listX2Index, 2)
                while(diffLength < 0):
                    CBash.DeleteFIDListX3Element(self._CollectionIndex, self._ModName, self._recordID, 12, oEntry._listIndex, 2, oEntry.listX2Index, 2)
                    diffLength += 1
                while(diffLength > 0):
                    CBash.CreateFIDListX3Element(self._CollectionIndex, self._ModName, self._recordID, 12, oEntry._listIndex, 2, oEntry.listX2Index, 2)
                    diffLength -= 1
                for oCondition, condValue in zip(oEntry.conditions, nValue[1]):
                    oCondition.operType, oCondition.unused1, oCondition.compValue, oCondition.ifunc, oCondition.param1, oCondition.param2, oCondition.unused2 = condValue
                nEntry.text = nValue[2]
                nEntry.unused1 = nValue[3]
                nEntry.numRefs = nValue[4]
                nEntry.compiledSize = nValue[5]
                nEntry.lastIndex = nValue[6]
                nEntry.scriptType = nValue[7]
                nEntry.compiled_p = nValue[8]
                nEntry.scriptText = nValue[9]
                diffLength = len(nValue[10]) - CBash.GetFIDListX3Size(self._CollectionIndex, self._ModName, self._recordID, 12, oEntry._listIndex, 2, oEntry._listX2Index, 11)
                while(diffLength < 0):
                    CBash.DeleteFIDListX3Element(self._CollectionIndex, self._ModName, self._recordID, 12, oEntry._listIndex, 2, oEntry.listX2Index, 11)
                    diffLength += 1
                while(diffLength > 0):
                    CBash.CreateFIDListX3Element(self._CollectionIndex, self._ModName, self._recordID, 12, oEntry._listIndex, 2, oEntry.listX2Index, 11)
                    diffLength -= 1
                for oReference, refValue in zip(oEntry.references, nValue[10]):
                    oReference.reference, oReference.IsSCRO = refValue   
        entries = property(get_entries, set_entries)
    class Target(object):
        class Condition(object):
            def __init__(self, CollectionIndex, ModName, recordID, listIndex, listX2Index):
                self._CollectionIndex = CollectionIndex
                self._ModName = ModName
                self._recordID = recordID
                self._listIndex = listIndex
                self._listX2Index = listX2Index
            def get_operType(self):
                CBash.ReadFIDListX2Field.restype = POINTER(c_ubyte)
                retValue = CBash.ReadFIDListX2Field(self._CollectionIndex, self._ModName, self._recordID, 13, self._listIndex, 4, self._listX2Index, 1)
                if(retValue): return retValue.contents.value
                return None
            def set_operType(self, nValue):
                CBash.SetFIDListX2FieldUC(self._CollectionIndex, self._ModName, self._recordID, 13, self._listIndex, 4, self._listX2Index, 1, c_ubyte(nValue))
            operType = property(get_operType, set_operType)
            def get_unused1(self):
                numRecords = CBash.GetFIDListX2ArraySize(self._CollectionIndex, self._ModName, self._recordID, 13, self._listIndex, 4, self._listX2Index, 2)
                if(numRecords > 0):
                    cRecords = POINTER(c_ubyte * numRecords)()
                    CBash.GetFIDListX2Array(self._CollectionIndex, self._ModName, self._recordID, 13, self._listIndex, 4, self._listX2Index, 2, byref(cRecords))
                    return [cRecords.contents[x] for x in range(0, numRecords)]
                return []
            def set_unused1(self, nValue):
                CBash.SetFIDListX2FieldR(self._CollectionIndex, self._ModName, self._recordID, 13, self._listIndex, 4, self._listX2Index, 2, struct.pack('3B', *nValue), 3)
            unused1 = property(get_unused1, set_unused1)
            def get_compValue(self):
                CBash.ReadFIDListX2Field.restype = POINTER(c_float)
                retValue = CBash.ReadFIDListX2Field(self._CollectionIndex, self._ModName, self._recordID, 13, self._listIndex, 4, self._listX2Index, 3)
                if(retValue): return retValue.contents.value
                return None
            def set_compValue(self, nValue):
                CBash.SetFIDListX2FieldF(self._CollectionIndex, self._ModName, self._recordID, 13, self._listIndex, 4, self._listX2Index, 3, c_float(nValue))
            compValue = property(get_compValue, set_compValue)
            def get_ifunc(self):
                CBash.ReadFIDListX2Field.restype = POINTER(c_uint)
                retValue = CBash.ReadFIDListX2Field(self._CollectionIndex, self._ModName, self._recordID, 13, self._listIndex, 4, self._listX2Index, 4)
                if(retValue): return retValue.contents.value
                return None
            def set_ifunc(self, nValue):
                CBash.SetFIDListX2FieldUI(self._CollectionIndex, self._ModName, self._recordID, 13, self._listIndex, 4, self._listX2Index, 4, nValue)
            ifunc = property(get_ifunc, set_ifunc)
            def get_param1(self):
                CBash.ReadFIDListX2Field.restype = POINTER(c_uint)
                retValue = CBash.ReadFIDListX2Field(self._CollectionIndex, self._ModName, self._recordID, 13, self._listIndex, 4, self._listX2Index, 5)
                if(retValue): return retValue.contents.value
                return None
            def set_param1(self, nValue):
                CBash.SetFIDListX2FieldUI(self._CollectionIndex, self._ModName, self._recordID, 13, self._listIndex, 4, self._listX2Index, 5, nValue)
            param1 = property(get_param1, set_param1)
            def get_param2(self):
                CBash.ReadFIDListX2Field.restype = POINTER(c_uint)
                retValue = CBash.ReadFIDListX2Field(self._CollectionIndex, self._ModName, self._recordID, 13, self._listIndex, 4, self._listX2Index, 6)
                if(retValue): return retValue.contents.value
                return None
            def set_param2(self, nValue):
                CBash.SetFIDListX2FieldUI(self._CollectionIndex, self._ModName, self._recordID, 13, self._listIndex, 4, self._listX2Index, 6, nValue)
            param2 = property(get_param2, set_param2)
            def get_unused2(self):
                numRecords = CBash.GetFIDListX2ArraySize(self._CollectionIndex, self._ModName, self._recordID, 13, self._listIndex, 4, self._listX2Index, 7)
                if(numRecords > 0):
                    cRecords = POINTER(c_ubyte * numRecords)()
                    CBash.GetFIDListX2Array(self._CollectionIndex, self._ModName, self._recordID, 13, self._listIndex, 4, self._listX2Index, 7, byref(cRecords))
                    return [cRecords.contents[x] for x in range(0, numRecords)]
                return []
            def set_unused2(self, nValue):
                CBash.SetFIDListX2FieldR(self._CollectionIndex, self._ModName, self._recordID, 13, self._listIndex, 4, self._listX2Index, 7, struct.pack('4B', *nValue), 4)
            unused2 = property(get_unused2, set_unused2)
            def get_IsEqual(self):
                return ((self.operType & 0xF0) == 0x00000000)
            def set_IsEqual(self, nValue):
                if (nValue == True):
                    self.operType &= 0x0F
                    self.operType |= 0x00000000
                elif(self.get_IsEqual()): self.IsNotEqual = True
            IsEqual = property(get_IsEqual, set_IsEqual)
            def get_IsNotEqual(self):
                return ((self.operType & 0xF0) == 0x00000020)
            def set_IsNotEqual(self, nValue):
                if (nValue == True):
                    self.operType &= 0x0F
                    self.operType |= 0x00000020
                elif(self.get_IsNotEqual()): self.IsEqual = True
            IsNotEqual = property(get_IsNotEqual, set_IsNotEqual)
            def get_IsGreater(self):
                return ((self.operType & 0xF0) == 0x00000040)
            def set_IsGreater(self, nValue):
                if (nValue == True):
                    self.operType &= 0x0F
                    self.operType |= 0x00000040
                elif(self.get_IsGreater()): self.IsEqual = True
            IsGreater = property(get_IsGreater, set_IsGreater)
            def get_IsGreaterOrEqual(self):
                return ((self.operType & 0xF0) == 0x00000060)
            def set_IsGreaterOrEqual(self, nValue):
                if (nValue == True):
                    self.operType &= 0x0F
                    self.operType |= 0x00000060
                elif(self.get_IsGreaterOrEqual()): self.IsEqual = True
            IsGreaterOrEqual = property(get_IsGreaterOrEqual, set_IsGreaterOrEqual)
            def get_IsLess(self):
                return ((self.operType & 0xF0) == 0x00000080)
            def set_IsLess(self, nValue):
                if (nValue == True):
                    self.operType &= 0x0F
                    self.operType |= 0x00000080
                elif(self.get_IsLess()): self.IsEqual = True
            IsLess = property(get_IsLess, set_IsLess)
            def get_IsLessOrEqual(self):
                return ((self.operType & 0xF0) == 0x000000A0)
            def set_IsLessOrEqual(self, nValue):
                if (nValue == True):
                    self.operType &= 0x0F
                    self.operType |= 0x000000A0
                elif(self.get_IsLessOrEqual()): self.IsEqual = True
            IsLessOrEqual = property(get_IsLessOrEqual, set_IsLessOrEqual)        
            def IsType(self, nValue):
                return ((self.operType & 0xF0) == (nValue & 0xF0))
            def SetType(self, nValue):
                nValue &= 0xF0
                self.operType &= 0x0F
                self.operType |= nValue
            def get_IsNone(self):
                return ((self.operType & 0x0F) == 0x00000000)
            def set_IsNone(self, nValue):
                if (nValue == True): self.operType &= 0xF0
            IsNone = property(get_IsNone, set_IsNone)
            def get_IsOr(self):
                return ((self.operType & 0x0F) == 0x00000001)
            def set_IsOr(self, nValue):
                if (nValue == True): self.operType |= 0x00000001
                else: self.operType &= ~0x00000001
            IsOr = property(get_IsOr, set_IsOr)
            def get_IsRunOnTarget(self):
                return ((self.operType & 0x0F) == 0x00000002)
            def set_IsRunOnTarget(self, nValue):
                if (nValue == True): self.operType |= 0x00000002
                else: self.operType &= ~0x00000002
            IsRunOnTarget = property(get_IsRunOnTarget, set_IsRunOnTarget)
            def get_IsUseGlobal(self):
                return ((self.operType & 0x0F) == 0x00000004)
            def set_IsUseGlobal(self, nValue):
                if (nValue == True): self.operType |= 0x00000004
                else: self.operType &= ~0x00000004
            IsUseGlobal = property(get_IsUseGlobal, set_IsUseGlobal)
            def IsFlagMask(self, nValue, Exact=False):
                if(Exact): return ((self.operType & 0x0F) & (nValue & 0x0F)) == nValue
                return ((self.operType & 0x0F) & (nValue & 0x0F)) != 0
            def SetFlagMask(self, nValue):
                nValue &= 0x0F
                self.operType &= 0xF0
                self.operType |= nValue
        def __init__(self, CollectionIndex, ModName, recordID, listIndex):
            self._CollectionIndex = CollectionIndex
            self._ModName = ModName
            self._recordID = recordID
            self._listIndex = listIndex
        def newConditionsElement(self):
            listX2Index = CBash.CreateFIDListX2Element(self._CollectionIndex, self._ModName, self._recordID, 13, self._listIndex, 4)
            if(listX2Index == -1): return None
            return self.Condition(self._CollectionIndex, self._ModName, self._recordID, self._listIndex, listX2Index)
        def get_targetId(self):
            CBash.ReadFIDListField.restype = POINTER(c_uint)
            retValue = CBash.ReadFIDListField(self._CollectionIndex, self._ModName, self._recordID, 13, self._listIndex, 1)
            if(retValue): return retValue.contents.value
            return None
        def set_targetId(self, nValue):
            CBash.SetFIDListFieldUI(self._CollectionIndex, self._ModName, self._recordID, 13, self._listIndex, 1, nValue)
        targetId = property(get_targetId, set_targetId)
        def get_flags(self):
            CBash.ReadFIDListField.restype = POINTER(c_ubyte)
            retValue = CBash.ReadFIDListField(self._CollectionIndex, self._ModName, self._recordID, 13, self._listIndex, 2)
            if(retValue): return retValue.contents.value
            return None
        def set_flags(self, nValue):
            CBash.SetFIDListFieldUC(self._CollectionIndex, self._ModName, self._recordID, 13, self._listIndex, 2, c_ubyte(nValue))
        flags = property(get_flags, set_flags)
        def get_unused1(self):
            numRecords = CBash.GetFIDListArraySize(self._CollectionIndex, self._ModName, self._recordID, 13, self._listIndex, 3)
            if(numRecords > 0):
                cRecords = POINTER(c_ubyte * numRecords)()
                CBash.GetFIDListArray(self._CollectionIndex, self._ModName, self._recordID, 13, self._listIndex, 3, byref(cRecords))
                return [cRecords.contents[x] for x in range(0, numRecords)]
            return []
        def set_unused1(self, nValue):
            CBash.SetFIDListFieldR(self._CollectionIndex, self._ModName, self._recordID, 13, self._listIndex, 3, struct.pack('3B', *nValue), 3)
        unused1 = property(get_unused1, set_unused1)
        def get_conditions(self):
            numRecords = CBash.GetFIDListX2Size(self._CollectionIndex, self._ModName, self._recordID, 13, self._listIndex, 4)
            if(numRecords > 0): return [self.Condition(self._CollectionIndex, self._ModName, self._recordID, self._listIndex, x) for x in range(0, numRecords)]
            return []
        def set_conditions(self, nConditions):
            diffLength = len(nConditions) - CBash.GetFIDListX2Size(self._CollectionIndex, self._ModName, self._recordID, 13, self._listIndex, 4)
            nValues = [(nCondition.operType, nCondition.unused1, nCondition.compValue, nCondition.ifunc, nCondition.param1, nCondition.param2, nCondition.unused2) for nCondition in nConditions]
            while(diffLength < 0):
                CBash.DeleteFIDListX2Element(self._CollectionIndex, self._ModName, self._recordID, 13, self._listIndex, 4)
                diffLength += 1
            while(diffLength > 0):
                CBash.CreateFIDListX2Element(self._CollectionIndex, self._ModName, self._recordID, 13, self._listIndex, 4)
                diffLength -= 1
            for oCondition, nValue in zip(self.conditions, nValues):
                oCondition.operType, oCondition.unused1, oCondition.compValue, oCondition.ifunc, oCondition.param1, oCondition.param2, oCondition.unused2 = nValue
        conditions = property(get_conditions, set_conditions)
        def get_IsIgnoresLocks(self):
            return (self.flags & 0x00000001) != 0
        def set_IsIgnoresLocks(self, nValue):
            if (nValue == True): self.flags |= 0x00000001
            else: self.flags &= ~0x00000001
        IsIgnoresLocks = property(get_IsIgnoresLocks, set_IsIgnoresLocks)
    def newConditionsElement(self):
        listIndex = CBash.CreateFIDListElement(self._CollectionIndex, self._ModName, self._recordID, 11)
        if(listIndex == -1): return None
        return self.Condition(self._CollectionIndex, self._ModName, self._recordID, 11, listIndex)
    def newStagesElement(self):
        listIndex = CBash.CreateFIDListElement(self._CollectionIndex, self._ModName, self._recordID, 12)
        if(listIndex == -1): return None
        return self.Stage(self._CollectionIndex, self._ModName, self._recordID, listIndex)
    def newTargetsElement(self):
        listIndex = CBash.CreateFIDListElement(self._CollectionIndex, self._ModName, self._recordID, 13)
        if(listIndex == -1): return None
        return self.Target(self._CollectionIndex, self._ModName, self._recordID, listIndex)

    def get_script(self):
        CBash.ReadFIDField.restype = POINTER(c_uint)
        retValue = CBash.ReadFIDField(self._CollectionIndex, self._ModName, self._recordID, 6)
        if(retValue): return retValue.contents.value
        return None
    def set_script(self, nValue):
        CBash.SetFIDFieldUI(self._CollectionIndex, self._ModName, self._recordID, 6, nValue)
    script = property(get_script, set_script)
    def get_full(self):
        CBash.ReadFIDField.restype = c_char_p
        return CBash.ReadFIDField(self._CollectionIndex, self._ModName, self._recordID, 7)
    def set_full(self, nValue):
        CBash.SetFIDFieldStr(self._CollectionIndex, self._ModName, self._recordID, 7, nValue)
    full = property(get_full, set_full)
    def get_iconPath(self):
        CBash.ReadFIDField.restype = c_char_p
        return CBash.ReadFIDField(self._CollectionIndex, self._ModName, self._recordID, 8)
    def set_iconPath(self, nValue):
        CBash.SetFIDFieldStr(self._CollectionIndex, self._ModName, self._recordID, 8, nValue)
    iconPath = property(get_iconPath, set_iconPath)
    def get_flags(self):
        CBash.ReadFIDField.restype = POINTER(c_ubyte)
        retValue = CBash.ReadFIDField(self._CollectionIndex, self._ModName, self._recordID, 9)
        if(retValue): return retValue.contents.value
        return None
    def set_flags(self, nValue):
        CBash.SetFIDFieldUC(self._CollectionIndex, self._ModName, self._recordID, 9, c_ubyte(nValue))
    flags = property(get_flags, set_flags)
    def get_priority(self):
        CBash.ReadFIDField.restype = POINTER(c_ubyte)
        retValue = CBash.ReadFIDField(self._CollectionIndex, self._ModName, self._recordID, 10)
        if(retValue): return retValue.contents.value
        return None
    def set_priority(self, nValue):
        CBash.SetFIDFieldUC(self._CollectionIndex, self._ModName, self._recordID, 10, c_ubyte(nValue))
    priority = property(get_priority, set_priority)
    def get_conditions(self):
        numRecords = CBash.GetFIDListSize(self._CollectionIndex, self._ModName, self._recordID, 11)
        if(numRecords > 0): return [self.Condition(self._CollectionIndex, self._ModName, self._recordID, 11, x) for x in range(0, numRecords)]
        return []
    def set_conditions(self, nConditions):
        diffLength = len(nConditions) - CBash.GetFIDListSize(self._CollectionIndex, self._ModName, self._recordID, 11)
        nValues = [(nCondition.operType, nCondition.unused1, nCondition.compValue, nCondition.ifunc, nCondition.param1, nCondition.param2, nCondition.unused2) for nCondition in nConditions]
        while(diffLength < 0):
            CBash.DeleteFIDListElement(self._CollectionIndex, self._ModName, self._recordID, 11)
            diffLength += 1
        while(diffLength > 0):
            CBash.CreateFIDListElement(self._CollectionIndex, self._ModName, self._recordID, 11)
            diffLength -= 1
        for oCondition, nValue in zip(self.conditions, nValues):
            oCondition.operType, oCondition.unused1, oCondition.compValue, oCondition.ifunc, oCondition.param1, oCondition.param2, oCondition.unused2 = nValue
    conditions = property(get_conditions, set_conditions)
    def get_stages(self):
        numRecords = CBash.GetFIDListSize(self._CollectionIndex, self._ModName, self._recordID, 12)
        if(numRecords > 0): return [self.Stage(self._CollectionIndex, self._ModName, self._recordID, x) for x in range(0, numRecords)]
        return []
    def set_stages(self, nStages):
        diffLength = len(nStages) - CBash.GetFIDListSize(self._CollectionIndex, self._ModName, self._recordID, 12)
        nValues = [(nStage.stage,
                  [(nEntry.flags,
                  [(nCondition.operType, nCondition.unused1, nCondition.compValue, nCondition.ifunc, 
                  nCondition.param1, nCondition.param2, nCondition.unused2) for nCondition in nEntry.conditions],
                  nEntry.text, nEntry.unused1, nEntry.numRefs, nEntry.compiledSize, nEntry.lastIndex, nEntry.scriptType, nEntry.compiled_p, nEntry.scriptText,
                  [(nReference.reference, nReference.IsSCRO) for nReference in nEntry.references]) for nEntry in nStage.entries]) for nStage in nStages]
        while(diffLength < 0):
            CBash.DeleteFIDListElement(self._CollectionIndex, self._ModName, self._recordID, 12)
            diffLength += 1
        while(diffLength > 0):
            CBash.CreateFIDListElement(self._CollectionIndex, self._ModName, self._recordID, 12)
            diffLength -= 1
        for oStage, nValue in zip(self.stages, nValues):
            oStage.stage = nValue[0]
            for oEntry, eValue in zip(oStage.entries, nValue[1]):
                nEntry.flags = eValue[0]
                diffLength = len(eValue[1]) - CBash.GetFIDListX3Size(self._CollectionIndex, self._ModName, self._recordID, 12, oEntry._listIndex, 2, oEntry._listX2Index, 2)
                while(diffLength < 0):
                    CBash.DeleteFIDListX3Element(self._CollectionIndex, self._ModName, self._recordID, 12, oEntry._listIndex, 2, oEntry._listX2Index, 2)
                    diffLength += 1
                while(diffLength > 0):
                    CBash.CreateFIDListX3Element(self._CollectionIndex, self._ModName, self._recordID, 12, oEntry._listIndex, 2, oEntry._listX2Index, 2)
                    diffLength -= 1
                for oCondition, condValue in zip(oEntry.conditions, eValue[1]):
                    oCondition.operType, oCondition.unused1, oCondition.compValue, oCondition.ifunc, oCondition.param1, oCondition.param2, oCondition.unused2 = condValue
                nEntry.text = eValue[2]
                nEntry.unused1 = eValue[3]
                nEntry.numRefs = eValue[4]
                nEntry.compiledSize = eValue[5]
                nEntry.lastIndex = eValue[6]
                nEntry.scriptType = eValue[7]
                nEntry.compiled_p = eValue[8]
                nEntry.scriptText = eValue[9]
                diffLength = len(eValue[10]) - CBash.GetFIDListX3Size(self._CollectionIndex, self._ModName, self._recordID, 12, oEntry._listIndex, 2, oEntry._listX2Index, 11)
                while(diffLength < 0):
                    CBash.DeleteFIDListX3Element(self._CollectionIndex, self._ModName, self._recordID, 12, oEntry._listIndex, 2, oEntry._listX2Index, 11)
                    diffLength += 1
                while(diffLength > 0):
                    CBash.CreateFIDListX3Element(self._CollectionIndex, self._ModName, self._recordID, 12, oEntry._listIndex, 2, oEntry._listX2Index, 11)
                    diffLength -= 1
                for oReference, refValue in zip(oEntry.references, eValue[10]):
                    oReference.reference, oReference.IsSCRO = refValue  
    stages = property(get_stages, set_stages)
    def get_targets(self):
        numRecords = CBash.GetFIDListSize(self._CollectionIndex, self._ModName, self._recordID, 13)
        if(numRecords > 0): return [self.Target(self._CollectionIndex, self._ModName, self._recordID, x) for x in range(0, numRecords)]
        return []
    def set_targets(self, nTargets):
        diffLength = len(nTargets) - CBash.GetFIDListSize(self._CollectionIndex, self._ModName, self._recordID, 13)
        nValues = [(nTarget.targetId, nTarget.flags, nTarget.unused1,
                  [(nCondition.operType, nCondition.unused1, nCondition.compValue, nCondition.ifunc, nCondition.param1, nCondition.param2, nCondition.unused2) for nCondition in nTarget.conditions]) for nTarget in nTargets]
        while(diffLength < 0):
            CBash.DeleteFIDListElement(self._CollectionIndex, self._ModName, self._recordID, 13)
            diffLength += 1
        while(diffLength > 0):
            CBash.CreateFIDListElement(self._CollectionIndex, self._ModName, self._recordID, 13)
            diffLength -= 1
        for oTarget, nValue in zip(self.targets, nValues):
            oTarget.targetId = nValue[0]
            oTarget.flags = nValue[1]
            oTarget.unused1 = nValue[2]
            diffLength = len(nValue[3]) - CBash.GetFIDListX2Size(self._CollectionIndex, self._ModName, self._recordID, 13, oTarget._listIndex, 4)
            while(diffLength < 0):
                CBash.DeleteFIDListX2Element(self._CollectionIndex, self._ModName, self._recordID, 13, oTarget._listIndex, 4)
                diffLength += 1
            while(diffLength > 0):
                CBash.CreateFIDListX2Element(self._CollectionIndex, self._ModName, self._recordID, 13, oTarget._listIndex, 4)
                diffLength -= 1
            for oCondition, eValue in zip(oTarget.conditions, nValue[3]):
                oCondition.operType, oCondition.unused1, oCondition.compValue, oCondition.ifunc, oCondition.param1, oCondition.param2, oCondition.unused2 = eValue
    targets = property(get_targets, set_targets)
    def get_IsStartEnabled(self):
        return (self.flags & 0x00000001) != 0
    def set_IsStartEnabled(self, nValue):
        if (nValue == True): self.flags |= 0x00000001
        else: self.flags &= ~0x00000001
    IsStartEnabled = property(get_IsStartEnabled, set_IsStartEnabled)
    def get_IsRepeatedTopics(self):
        return (self.flags & 0x00000004) != 0
    def set_IsRepeatedTopics(self, nValue):
        if (nValue == True): self.flags |= 0x00000004
        else: self.flags &= ~0x00000004
    IsRepeatedTopics = property(get_IsRepeatedTopics, set_IsRepeatedTopics)
    def get_IsRepeatedStages(self):
        return (self.flags & 0x00000008) != 0
    def set_IsRepeatedStages(self, nValue):
        if (nValue == True): self.flags |= 0x00000008
        else: self.flags &= ~0x00000008
    IsRepeatedStages = property(get_IsRepeatedStages, set_IsRepeatedStages)
    
class IDLERecord(BaseRecord):
    def CopyAsOverride(self, targetMod):
        FID = CBash.CopyIDLERecord(self._CollectionIndex, self._ModName, self._recordID, targetMod._ModName, c_bool(True))
        if(FID): return IDLERecord(self._CollectionIndex, targetMod._ModName, FID)
        return None
    def CopyAsNew(self, targetMod):
        FID = CBash.CopyIDLERecord(self._CollectionIndex, self._ModName, self._recordID, targetMod._ModName, c_bool(False))
        if(FID): return IDLERecord(self._CollectionIndex, targetMod._ModName, FID)
        return None
    class Condition(object):
        def __init__(self, CollectionIndex, ModName, recordID, subField, listIndex):
            self._CollectionIndex = CollectionIndex
            self._ModName = ModName
            self._recordID = recordID
            self._subField = subField
            self._listIndex = listIndex
        def get_operType(self):
            CBash.ReadFIDListField.restype = POINTER(c_ubyte)
            retValue = CBash.ReadFIDListField(self._CollectionIndex, self._ModName, self._recordID, self._subField, self._listIndex, 1)
            if(retValue): return retValue.contents.value
            return None
        def set_operType(self, nValue):
            CBash.SetFIDListFieldUC(self._CollectionIndex, self._ModName, self._recordID, self._subField, self._listIndex, 1, c_ubyte(nValue))
        operType = property(get_operType, set_operType)
        def get_unused1(self):
            numRecords = CBash.GetFIDListArraySize(self._CollectionIndex, self._ModName, self._recordID, self._subField, self._listIndex, 2)
            if(numRecords > 0):
                cRecords = POINTER(c_ubyte * numRecords)()
                CBash.GetFIDListArray(self._CollectionIndex, self._ModName, self._recordID, self._subField, self._listIndex, 2, byref(cRecords))
                return [cRecords.contents[x] for x in range(0, numRecords)]
            return []
        def set_unused1(self, nValue):
            CBash.SetFIDListFieldR(self._CollectionIndex, self._ModName, self._recordID, self._subField, self._listIndex, 2, struct.pack('3B', *nValue), 3)
        unused1 = property(get_unused1, set_unused1)
        def get_compValue(self):
            CBash.ReadFIDListField.restype = POINTER(c_float)
            retValue = CBash.ReadFIDListField(self._CollectionIndex, self._ModName, self._recordID, self._subField, self._listIndex, 3)
            if(retValue): return retValue.contents.value
            return None
        def set_compValue(self, nValue):
            CBash.SetFIDListFieldF(self._CollectionIndex, self._ModName, self._recordID, self._subField, self._listIndex, 3, c_float(nValue))
        compValue = property(get_compValue, set_compValue)
        def get_ifunc(self):
            CBash.ReadFIDListField.restype = POINTER(c_uint)
            retValue = CBash.ReadFIDListField(self._CollectionIndex, self._ModName, self._recordID, self._subField, self._listIndex, 4)
            if(retValue): return retValue.contents.value
            return None
        def set_ifunc(self, nValue):
            CBash.SetFIDListFieldUI(self._CollectionIndex, self._ModName, self._recordID, self._subField, self._listIndex, 4, nValue)
        ifunc = property(get_ifunc, set_ifunc)
        def get_param1(self):
            CBash.ReadFIDListField.restype = POINTER(c_uint)
            retValue = CBash.ReadFIDListField(self._CollectionIndex, self._ModName, self._recordID, self._subField, self._listIndex, 5)
            if(retValue): return retValue.contents.value
            return None
        def set_param1(self, nValue):
            CBash.SetFIDListFieldUI(self._CollectionIndex, self._ModName, self._recordID, self._subField, self._listIndex, 5, nValue)
        param1 = property(get_param1, set_param1)
        def get_param2(self):
            CBash.ReadFIDListField.restype = POINTER(c_uint)
            retValue = CBash.ReadFIDListField(self._CollectionIndex, self._ModName, self._recordID, self._subField, self._listIndex, 6)
            if(retValue): return retValue.contents.value
            return None
        def set_param2(self, nValue):
            CBash.SetFIDListFieldUI(self._CollectionIndex, self._ModName, self._recordID, self._subField, self._listIndex, 6, nValue)
        param2 = property(get_param2, set_param2)
        def get_unused2(self):
            numRecords = CBash.GetFIDListArraySize(self._CollectionIndex, self._ModName, self._recordID, self._subField, self._listIndex, 7)
            if(numRecords > 0):
                cRecords = POINTER(c_ubyte * numRecords)()
                CBash.GetFIDListArray(self._CollectionIndex, self._ModName, self._recordID, self._subField, self._listIndex, 7, byref(cRecords))
                return [cRecords.contents[x] for x in range(0, numRecords)]
            return []
        def set_unused2(self, nValue):
            CBash.SetFIDListFieldR(self._CollectionIndex, self._ModName, self._recordID, self._subField, self._listIndex, 7, struct.pack('4B', *nValue), 4)
        unused2 = property(get_unused2, set_unused2)
        def get_IsEqual(self):
            return ((self.operType & 0xF0) == 0x00000000)
        def set_IsEqual(self, nValue):
            if (nValue == True):
                self.operType &= 0x0F
                self.operType |= 0x00000000
            elif(self.get_IsEqual()): self.IsNotEqual = True
        IsEqual = property(get_IsEqual, set_IsEqual)
        def get_IsNotEqual(self):
            return ((self.operType & 0xF0) == 0x00000020)
        def set_IsNotEqual(self, nValue):
            if (nValue == True):
                self.operType &= 0x0F
                self.operType |= 0x00000020
            elif(self.get_IsNotEqual()): self.IsEqual = True
        IsNotEqual = property(get_IsNotEqual, set_IsNotEqual)
        def get_IsGreater(self):
            return ((self.operType & 0xF0) == 0x00000040)
        def set_IsGreater(self, nValue):
            if (nValue == True):
                self.operType &= 0x0F
                self.operType |= 0x00000040
            elif(self.get_IsGreater()): self.IsEqual = True
        IsGreater = property(get_IsGreater, set_IsGreater)
        def get_IsGreaterOrEqual(self):
            return ((self.operType & 0xF0) == 0x00000060)
        def set_IsGreaterOrEqual(self, nValue):
            if (nValue == True):
                self.operType &= 0x0F
                self.operType |= 0x00000060
            elif(self.get_IsGreaterOrEqual()): self.IsEqual = True
        IsGreaterOrEqual = property(get_IsGreaterOrEqual, set_IsGreaterOrEqual)
        def get_IsLess(self):
            return ((self.operType & 0xF0) == 0x00000080)
        def set_IsLess(self, nValue):
            if (nValue == True):
                self.operType &= 0x0F
                self.operType |= 0x00000080
            elif(self.get_IsLess()): self.IsEqual = True
        IsLess = property(get_IsLess, set_IsLess)
        def get_IsLessOrEqual(self):
            return ((self.operType & 0xF0) == 0x000000A0)
        def set_IsLessOrEqual(self, nValue):
            if (nValue == True):
                self.operType &= 0x0F
                self.operType |= 0x000000A0
            elif(self.get_IsLessOrEqual()): self.IsEqual = True
        IsLessOrEqual = property(get_IsLessOrEqual, set_IsLessOrEqual)        
        def IsType(self, nValue):
            return ((self.operType & 0xF0) == (nValue & 0xF0))
        def SetType(self, nValue):
            nValue &= 0xF0
            self.operType &= 0x0F
            self.operType |= nValue
        def get_IsNone(self):
            return ((self.operType & 0x0F) == 0x00000000)
        def set_IsNone(self, nValue):
            if (nValue == True): self.operType &= 0xF0
        IsNone = property(get_IsNone, set_IsNone)
        def get_IsOr(self):
            return ((self.operType & 0x0F) == 0x00000001)
        def set_IsOr(self, nValue):
            if (nValue == True): self.operType |= 0x00000001
            else: self.operType &= ~0x00000001
        IsOr = property(get_IsOr, set_IsOr)
        def get_IsRunOnTarget(self):
            return ((self.operType & 0x0F) == 0x00000002)
        def set_IsRunOnTarget(self, nValue):
            if (nValue == True): self.operType |= 0x00000002
            else: self.operType &= ~0x00000002
        IsRunOnTarget = property(get_IsRunOnTarget, set_IsRunOnTarget)
        def get_IsUseGlobal(self):
            return ((self.operType & 0x0F) == 0x00000004)
        def set_IsUseGlobal(self, nValue):
            if (nValue == True): self.operType |= 0x00000004
            else: self.operType &= ~0x00000004
        IsUseGlobal = property(get_IsUseGlobal, set_IsUseGlobal)
        def IsFlagMask(self, nValue, Exact=False):
            if(Exact): return ((self.operType & 0x0F) & (nValue & 0x0F)) == nValue
            return ((self.operType & 0x0F) & (nValue & 0x0F)) != 0
        def SetFlagMask(self, nValue):
            nValue &= 0x0F
            self.operType &= 0xF0
            self.operType |= nValue
    def newConditionsElement(self):
        listIndex = CBash.CreateFIDListElement(self._CollectionIndex, self._ModName, self._recordID, 9)
        if(listIndex == -1): return None
        return self.Condition(self._CollectionIndex, self._ModName, self._recordID, 9, listIndex)

    def get_modPath(self):
        CBash.ReadFIDField.restype = c_char_p
        return CBash.ReadFIDField(self._CollectionIndex, self._ModName, self._recordID, 6)
    def set_modPath(self, nValue):
        CBash.SetFIDFieldStr(self._CollectionIndex, self._ModName, self._recordID, 6, nValue)
    modPath = property(get_modPath, set_modPath)
    def get_modb(self):
        CBash.ReadFIDField.restype = POINTER(c_float)
        retValue = CBash.ReadFIDField(self._CollectionIndex, self._ModName, self._recordID, 7)
        if(retValue): return retValue.contents.value
        return None
    def set_modb(self, nValue):
        CBash.SetFIDFieldF(self._CollectionIndex, self._ModName, self._recordID, 7, c_float(nValue))
    modb = property(get_modb, set_modb)
    def get_modt_p(self):
        numRecords = CBash.GetFIDFieldArraySize(self._CollectionIndex, self._ModName, self._recordID, 8)
        if(numRecords > 0):
            cRecords = POINTER(c_ubyte * numRecords)()
            CBash.GetFIDFieldArray(self._CollectionIndex, self._ModName, self._recordID, 8, byref(cRecords))
            return [cRecords.contents[x] for x in range(0, numRecords)]
        return []
    def set_modt_p(self, nValue):
        length = len(nValue)
        CBash.SetFIDFieldR(self._CollectionIndex, self._ModName, self._recordID, 8, struct.pack('B' * length, *nValue), length)
    modt_p = property(get_modt_p, set_modt_p)
    def get_conditions(self):
        numRecords = CBash.GetFIDListSize(self._CollectionIndex, self._ModName, self._recordID, 9)
        if(numRecords > 0): return [self.Condition(self._CollectionIndex, self._ModName, self._recordID, 9, x) for x in range(0, numRecords)]
        return []
    def set_conditions(self, nConditions):
        diffLength = len(nConditions) - CBash.GetFIDListSize(self._CollectionIndex, self._ModName, self._recordID, 9)
        nValues = [(nCondition.operType, nCondition.unused1, nCondition.compValue, nCondition.ifunc, nCondition.param1, nCondition.param2, nCondition.unused2) for nCondition in nConditions]
        while(diffLength < 0):
            CBash.DeleteFIDListElement(self._CollectionIndex, self._ModName, self._recordID, 9)
            diffLength += 1
        while(diffLength > 0):
            CBash.CreateFIDListElement(self._CollectionIndex, self._ModName, self._recordID, 9)
            diffLength -= 1
        for oCondition, nValue in zip(self.conditions, nValues):
            oCondition.operType, oCondition.unused1, oCondition.compValue, oCondition.ifunc, oCondition.param1, oCondition.param2, oCondition.unused2 = nValue
    conditions = property(get_conditions, set_conditions)
    def get_group(self):
        CBash.ReadFIDField.restype = POINTER(c_ubyte)
        retValue = CBash.ReadFIDField(self._CollectionIndex, self._ModName, self._recordID, 10)
        if(retValue): return retValue.contents.value
        return None
    def set_group(self, nValue):
        CBash.SetFIDFieldUC(self._CollectionIndex, self._ModName, self._recordID, 10, c_ubyte(nValue))
    group = property(get_group, set_group)
    def get_parent(self):
        CBash.ReadFIDField.restype = POINTER(c_uint)
        retValue = CBash.ReadFIDField(self._CollectionIndex, self._ModName, self._recordID, 11)
        if(retValue): return retValue.contents.value
        return None
    def set_parent(self, nValue):
        CBash.SetFIDFieldUI(self._CollectionIndex, self._ModName, self._recordID, 11, nValue)
    parent = property(get_parent, set_parent)
    def get_prevId(self):
        CBash.ReadFIDField.restype = POINTER(c_uint)
        retValue = CBash.ReadFIDField(self._CollectionIndex, self._ModName, self._recordID, 12)
        if(retValue): return retValue.contents.value
        return None
    def set_prevId(self, nValue):
        CBash.SetFIDFieldUI(self._CollectionIndex, self._ModName, self._recordID, 12, nValue)
    prevId = property(get_prevId, set_prevId)
    def get_IsLowerBody(self):
        return ((self.group & 0x0F) == 0x00000000)
    def set_IsLowerBody(self, nValue):
        if (nValue == True):
            self.group &= 0xF0
            self.group |= 0x00000000
        elif(self.get_IsLowerBody()): self.IsLeftArm = True
    IsLowerBody = property(get_IsLowerBody, set_IsLowerBody)
    def get_IsLeftArm(self):
        return ((self.group & 0x0F) == 0x00000001)
    def set_IsLeftArm(self, nValue):
        if (nValue == True):
            self.group &= 0xF0
            self.group |= 0x00000001
        elif(self.get_IsLeftArm()): self.IsLowerBody = True
    IsLeftArm = property(get_IsLeftArm, set_IsLeftArm)
    def get_IsLeftHand(self):
        return ((self.group & 0x0F) == 0x00000002)
    def set_IsLeftHand(self, nValue):
        if (nValue == True):
            self.group &= 0xF0
            self.group |= 0x00000002
        elif(self.get_IsLeftHand()): self.IsLowerBody = True
    IsLeftHand = property(get_IsLeftHand, set_IsLeftHand)
    def get_IsRightArm(self):
        return ((self.group & 0x0F) == 0x00000003)
    def set_IsRightArm(self, nValue):
        if (nValue == True):
            self.group &= 0xF0
            self.group |= 0x00000003
        elif(self.get_IsRightArm()): self.IsLowerBody = True
    IsRightArm = property(get_IsRightArm, set_IsRightArm)
    def get_IsSpecialIdle(self):
        return ((self.group & 0x0F) == 0x00000004)
    def set_IsSpecialIdle(self, nValue):
        if (nValue == True):
            self.group &= 0xF0
            self.group |= 0x00000004
        elif(self.get_IsSpecialIdle()): self.IsLowerBody = True
    IsSpecialIdle = property(get_IsSpecialIdle, set_IsSpecialIdle)
    def get_IsWholeBody(self):
        return ((self.group & 0x0F) == 0x00000005)
    def set_IsWholeBody(self, nValue):
        if (nValue == True):
            self.group &= 0xF0
            self.group |= 0x00000005
        elif(self.get_IsWholeBody()): self.IsLowerBody = True
    IsWholeBody = property(get_IsWholeBody, set_IsWholeBody)
    def get_IsUpperBody(self):
        return ((self.group & 0x0F) == 0x00000006)
    def set_IsUpperBody(self, nValue):
        if (nValue == True):
            self.group &= 0xF0
            self.group |= 0x00000006
        elif(self.get_IsUpperBody()): self.IsLowerBody = True
    IsUpperBody = property(get_IsUpperBody, set_IsUpperBody)
    def IsType(self, nValue):
        return ((self.group & 0x0F) == (nValue & 0x0F))
    def SetType(self, nValue):
        nValue &= 0x0F
        self.group &= 0xF0
        self.group |= nValue
    def get_IsNotReturnFile(self):
        return (self.group & 0x00000080) != 0
    def set_IsNotReturnFile(self, nValue):
        if (nValue == True): self.group |= 0x00000080
        else: self.group &= ~0x00000080
    IsNotReturnFile = property(get_IsNotReturnFile, set_IsNotReturnFile)
    def get_IsReturnFile(self):
        return not self.get_IsNotReturnFile()
    def set_IsReturnFile(self, nValue):
        if (nValue == True): self.group &= ~0x00000080
        else: self.group |= 0x00000080
    IsReturnFile = property(get_IsReturnFile, set_IsReturnFile)
    def IsFlagMask(self, nValue, Exact=False):
        if(Exact): return ((self.group & 0xF0) & (nValue & 0xF0)) == nValue
        return ((self.group & 0xF0) & (nValue & 0xF0)) != 0
    def SetFlagMask(self, nValue):
        nValue &= 0xF0
        self.group &= 0x0F
        self.group |= nValue
        
class PACKRecord(BaseRecord):
    def CopyAsOverride(self, targetMod):
        FID = CBash.CopyPACKRecord(self._CollectionIndex, self._ModName, self._recordID, targetMod._ModName, c_bool(True))
        if(FID): return PACKRecord(self._CollectionIndex, targetMod._ModName, FID)
        return None
    def CopyAsNew(self, targetMod):
        FID = CBash.CopyPACKRecord(self._CollectionIndex, self._ModName, self._recordID, targetMod._ModName, c_bool(False))
        if(FID): return PACKRecord(self._CollectionIndex, targetMod._ModName, FID)
        return None
    class Condition(object):
        def __init__(self, CollectionIndex, ModName, recordID, subField, listIndex):
            self._CollectionIndex = CollectionIndex
            self._ModName = ModName
            self._recordID = recordID
            self._subField = subField
            self._listIndex = listIndex
        def get_operType(self):
            CBash.ReadFIDListField.restype = POINTER(c_ubyte)
            retValue = CBash.ReadFIDListField(self._CollectionIndex, self._ModName, self._recordID, self._subField, self._listIndex, 1)
            if(retValue): return retValue.contents.value
            return None
        def set_operType(self, nValue):
            CBash.SetFIDListFieldUC(self._CollectionIndex, self._ModName, self._recordID, self._subField, self._listIndex, 1, c_ubyte(nValue))
        operType = property(get_operType, set_operType)
        def get_unused1(self):
            numRecords = CBash.GetFIDListArraySize(self._CollectionIndex, self._ModName, self._recordID, self._subField, self._listIndex, 2)
            if(numRecords > 0):
                cRecords = POINTER(c_ubyte * numRecords)()
                CBash.GetFIDListArray(self._CollectionIndex, self._ModName, self._recordID, self._subField, self._listIndex, 2, byref(cRecords))
                return [cRecords.contents[x] for x in range(0, numRecords)]
            return []
        def set_unused1(self, nValue):
            CBash.SetFIDListFieldR(self._CollectionIndex, self._ModName, self._recordID, self._subField, self._listIndex, 2, struct.pack('3B', *nValue), 3)
        unused1 = property(get_unused1, set_unused1)
        def get_compValue(self):
            CBash.ReadFIDListField.restype = POINTER(c_float)
            retValue = CBash.ReadFIDListField(self._CollectionIndex, self._ModName, self._recordID, self._subField, self._listIndex, 3)
            if(retValue): return retValue.contents.value
            return None
        def set_compValue(self, nValue):
            CBash.SetFIDListFieldF(self._CollectionIndex, self._ModName, self._recordID, self._subField, self._listIndex, 3, c_float(nValue))
        compValue = property(get_compValue, set_compValue)
        def get_ifunc(self):
            CBash.ReadFIDListField.restype = POINTER(c_uint)
            retValue = CBash.ReadFIDListField(self._CollectionIndex, self._ModName, self._recordID, self._subField, self._listIndex, 4)
            if(retValue): return retValue.contents.value
            return None
        def set_ifunc(self, nValue):
            CBash.SetFIDListFieldUI(self._CollectionIndex, self._ModName, self._recordID, self._subField, self._listIndex, 4, nValue)
        ifunc = property(get_ifunc, set_ifunc)
        def get_param1(self):
            CBash.ReadFIDListField.restype = POINTER(c_uint)
            retValue = CBash.ReadFIDListField(self._CollectionIndex, self._ModName, self._recordID, self._subField, self._listIndex, 5)
            if(retValue): return retValue.contents.value
            return None
        def set_param1(self, nValue):
            CBash.SetFIDListFieldUI(self._CollectionIndex, self._ModName, self._recordID, self._subField, self._listIndex, 5, nValue)
        param1 = property(get_param1, set_param1)
        def get_param2(self):
            CBash.ReadFIDListField.restype = POINTER(c_uint)
            retValue = CBash.ReadFIDListField(self._CollectionIndex, self._ModName, self._recordID, self._subField, self._listIndex, 6)
            if(retValue): return retValue.contents.value
            return None
        def set_param2(self, nValue):
            CBash.SetFIDListFieldUI(self._CollectionIndex, self._ModName, self._recordID, self._subField, self._listIndex, 6, nValue)
        param2 = property(get_param2, set_param2)
        def get_unused2(self):
            numRecords = CBash.GetFIDListArraySize(self._CollectionIndex, self._ModName, self._recordID, self._subField, self._listIndex, 7)
            if(numRecords > 0):
                cRecords = POINTER(c_ubyte * numRecords)()
                CBash.GetFIDListArray(self._CollectionIndex, self._ModName, self._recordID, self._subField, self._listIndex, 7, byref(cRecords))
                return [cRecords.contents[x] for x in range(0, numRecords)]
            return []
        def set_unused2(self, nValue):
            CBash.SetFIDListFieldR(self._CollectionIndex, self._ModName, self._recordID, self._subField, self._listIndex, 7, struct.pack('4B', *nValue), 4)
        unused2 = property(get_unused2, set_unused2)
        def get_IsEqual(self):
            return ((self.operType & 0xF0) == 0x00000000)
        def set_IsEqual(self, nValue):
            if (nValue == True):
                self.operType &= 0x0F
                self.operType |= 0x00000000
            elif(self.get_IsEqual()): self.IsNotEqual = True
        IsEqual = property(get_IsEqual, set_IsEqual)
        def get_IsNotEqual(self):
            return ((self.operType & 0xF0) == 0x00000020)
        def set_IsNotEqual(self, nValue):
            if (nValue == True):
                self.operType &= 0x0F
                self.operType |= 0x00000020
            elif(self.get_IsNotEqual()): self.IsEqual = True
        IsNotEqual = property(get_IsNotEqual, set_IsNotEqual)
        def get_IsGreater(self):
            return ((self.operType & 0xF0) == 0x00000040)
        def set_IsGreater(self, nValue):
            if (nValue == True):
                self.operType &= 0x0F
                self.operType |= 0x00000040
            elif(self.get_IsGreater()): self.IsEqual = True
        IsGreater = property(get_IsGreater, set_IsGreater)
        def get_IsGreaterOrEqual(self):
            return ((self.operType & 0xF0) == 0x00000060)
        def set_IsGreaterOrEqual(self, nValue):
            if (nValue == True):
                self.operType &= 0x0F
                self.operType |= 0x00000060
            elif(self.get_IsGreaterOrEqual()): self.IsEqual = True
        IsGreaterOrEqual = property(get_IsGreaterOrEqual, set_IsGreaterOrEqual)
        def get_IsLess(self):
            return ((self.operType & 0xF0) == 0x00000080)
        def set_IsLess(self, nValue):
            if (nValue == True):
                self.operType &= 0x0F
                self.operType |= 0x00000080
            elif(self.get_IsLess()): self.IsEqual = True
        IsLess = property(get_IsLess, set_IsLess)
        def get_IsLessOrEqual(self):
            return ((self.operType & 0xF0) == 0x000000A0)
        def set_IsLessOrEqual(self, nValue):
            if (nValue == True):
                self.operType &= 0x0F
                self.operType |= 0x000000A0
            elif(self.get_IsLessOrEqual()): self.IsEqual = True
        IsLessOrEqual = property(get_IsLessOrEqual, set_IsLessOrEqual)        
        def IsType(self, nValue):
            return ((self.operType & 0xF0) == (nValue & 0xF0))
        def SetType(self, nValue):
            nValue &= 0xF0
            self.operType &= 0x0F
            self.operType |= nValue
        def get_IsNone(self):
            return ((self.operType & 0x0F) == 0x00000000)
        def set_IsNone(self, nValue):
            if (nValue == True): self.operType &= 0xF0
        IsNone = property(get_IsNone, set_IsNone)
        def get_IsOr(self):
            return ((self.operType & 0x0F) == 0x00000001)
        def set_IsOr(self, nValue):
            if (nValue == True): self.operType |= 0x00000001
            else: self.operType &= ~0x00000001
        IsOr = property(get_IsOr, set_IsOr)
        def get_IsRunOnTarget(self):
            return ((self.operType & 0x0F) == 0x00000002)
        def set_IsRunOnTarget(self, nValue):
            if (nValue == True): self.operType |= 0x00000002
            else: self.operType &= ~0x00000002
        IsRunOnTarget = property(get_IsRunOnTarget, set_IsRunOnTarget)
        def get_IsUseGlobal(self):
            return ((self.operType & 0x0F) == 0x00000004)
        def set_IsUseGlobal(self, nValue):
            if (nValue == True): self.operType |= 0x00000004
            else: self.operType &= ~0x00000004
        IsUseGlobal = property(get_IsUseGlobal, set_IsUseGlobal)
        def IsFlagMask(self, nValue, Exact=False):
            if(Exact): return ((self.operType & 0x0F) & (nValue & 0x0F)) == nValue
            return ((self.operType & 0x0F) & (nValue & 0x0F)) != 0
        def SetFlagMask(self, nValue):
            nValue &= 0x0F
            self.operType &= 0xF0
            self.operType |= nValue
    def newConditionsElement(self):
        listIndex = CBash.CreateFIDListElement(self._CollectionIndex, self._ModName, self._recordID, 20)
        if(listIndex == -1): return None
        return self.Condition(self._CollectionIndex, self._ModName, self._recordID, 20, listIndex)
    def get_flags(self):
        CBash.ReadFIDField.restype = POINTER(c_uint)
        retValue = CBash.ReadFIDField(self._CollectionIndex, self._ModName, self._recordID, 6)
        if(retValue): return retValue.contents.value
        return None
    def set_flags(self, nValue):
        CBash.SetFIDFieldUI(self._CollectionIndex, self._ModName, self._recordID, 6, nValue)
    flags = property(get_flags, set_flags)
    def get_aiType(self):
        CBash.ReadFIDField.restype = POINTER(c_ubyte)
        retValue = CBash.ReadFIDField(self._CollectionIndex, self._ModName, self._recordID, 7)
        if(retValue): return retValue.contents.value
        return None
    def set_aiType(self, nValue):
        CBash.SetFIDFieldUC(self._CollectionIndex, self._ModName, self._recordID, 7, c_ubyte(nValue))
    aiType = property(get_aiType, set_aiType)
    def get_unused1(self):
        numRecords = CBash.GetFIDFieldArraySize(self._CollectionIndex, self._ModName, self._recordID, 8)
        if(numRecords > 0):
            cRecords = POINTER(c_ubyte * numRecords)()
            CBash.GetFIDFieldArray(self._CollectionIndex, self._ModName, self._recordID, 8, byref(cRecords))
            return [cRecords.contents[x] for x in range(0, numRecords)]
        return []
    def set_unused1(self, nValue):
        CBash.SetFIDFieldR(self._CollectionIndex, self._ModName, self._recordID, 8, struct.pack('3B', *nValue), 3)
    unused1 = property(get_unused1, set_unused1)
    def get_locType(self):
        CBash.ReadFIDField.restype = POINTER(c_int)
        retValue = CBash.ReadFIDField(self._CollectionIndex, self._ModName, self._recordID, 9)
        if(retValue): return retValue.contents.value
        return None
    def set_locType(self, nValue):
        CBash.SetFIDFieldI(self._CollectionIndex, self._ModName, self._recordID, 9, nValue)
    locType = property(get_locType, set_locType)
    def get_locId(self):
        CBash.ReadFIDField.restype = POINTER(c_uint)
        retValue = CBash.ReadFIDField(self._CollectionIndex, self._ModName, self._recordID, 10)
        if(retValue): return retValue.contents.value
        return None
    def set_locId(self, nValue):
        CBash.SetFIDFieldUI(self._CollectionIndex, self._ModName, self._recordID, 10, nValue)
    locId = property(get_locId, set_locId)
    def get_locRadius(self):
        CBash.ReadFIDField.restype = POINTER(c_int)
        retValue = CBash.ReadFIDField(self._CollectionIndex, self._ModName, self._recordID, 11)
        if(retValue): return retValue.contents.value
        return None
    def set_locRadius(self, nValue):
        CBash.SetFIDFieldI(self._CollectionIndex, self._ModName, self._recordID, 11, nValue)
    locRadius = property(get_locRadius, set_locRadius)
    def get_month(self):
        CBash.ReadFIDField.restype = POINTER(c_byte)
        retValue = CBash.ReadFIDField(self._CollectionIndex, self._ModName, self._recordID, 12)
        if(retValue): return retValue.contents.value
        return None
    def set_month(self, nValue):
        CBash.SetFIDFieldC(self._CollectionIndex, self._ModName, self._recordID, 12, c_byte(nValue))
    month = property(get_month, set_month)
    def get_day(self):
        CBash.ReadFIDField.restype = POINTER(c_byte)
        retValue = CBash.ReadFIDField(self._CollectionIndex, self._ModName, self._recordID, 13)
        if(retValue): return retValue.contents.value
        return None
    def set_day(self, nValue):
        CBash.SetFIDFieldC(self._CollectionIndex, self._ModName, self._recordID, 13, c_byte(nValue))
    day = property(get_day, set_day)
    def get_date(self):
        CBash.ReadFIDField.restype = POINTER(c_ubyte)
        retValue = CBash.ReadFIDField(self._CollectionIndex, self._ModName, self._recordID, 14)
        if(retValue): return retValue.contents.value
        return None
    def set_date(self, nValue):
        CBash.SetFIDFieldUC(self._CollectionIndex, self._ModName, self._recordID, 14, c_ubyte(nValue))
    date = property(get_date, set_date)
    def get_time(self):
        CBash.ReadFIDField.restype = POINTER(c_byte)
        retValue = CBash.ReadFIDField(self._CollectionIndex, self._ModName, self._recordID, 15)
        if(retValue): return retValue.contents.value
        return None
    def set_time(self, nValue):
        CBash.SetFIDFieldC(self._CollectionIndex, self._ModName, self._recordID, 15, c_byte(nValue))
    time = property(get_time, set_time)
    def get_duration(self):
        CBash.ReadFIDField.restype = POINTER(c_int)
        retValue = CBash.ReadFIDField(self._CollectionIndex, self._ModName, self._recordID, 16)
        if(retValue): return retValue.contents.value
        return None
    def set_duration(self, nValue):
        CBash.SetFIDFieldI(self._CollectionIndex, self._ModName, self._recordID, 16, nValue)
    duration = property(get_duration, set_duration)
    def get_targetType(self):
        CBash.ReadFIDField.restype = POINTER(c_int)
        retValue = CBash.ReadFIDField(self._CollectionIndex, self._ModName, self._recordID, 17)
        if(retValue): return retValue.contents.value
        return None
    def set_targetType(self, nValue):
        CBash.SetFIDFieldI(self._CollectionIndex, self._ModName, self._recordID, 17, nValue)
    targetType = property(get_targetType, set_targetType)
    def get_targetId(self):
        CBash.ReadFIDField.restype = POINTER(c_uint)
        retValue = CBash.ReadFIDField(self._CollectionIndex, self._ModName, self._recordID, 18)
        if(retValue): return retValue.contents.value
        return None
    def set_targetId(self, nValue):
        CBash.SetFIDFieldUI(self._CollectionIndex, self._ModName, self._recordID, 18, nValue)
    targetId = property(get_targetId, set_targetId)
    def get_targetCount(self):
        CBash.ReadFIDField.restype = POINTER(c_int)
        retValue = CBash.ReadFIDField(self._CollectionIndex, self._ModName, self._recordID, 19)
        if(retValue): return retValue.contents.value
        return None
    def set_targetCount(self, nValue):
        CBash.SetFIDFieldI(self._CollectionIndex, self._ModName, self._recordID, 19, nValue)
    targetCount = property(get_targetCount, set_targetCount)
    def get_conditions(self):
        numRecords = CBash.GetFIDListSize(self._CollectionIndex, self._ModName, self._recordID, 20)
        if(numRecords > 0): return [self.Condition(self._CollectionIndex, self._ModName, self._recordID, 20, x) for x in range(0, numRecords)]
        return []
    def set_conditions(self, nConditions):
        diffLength = len(nConditions) - CBash.GetFIDListSize(self._CollectionIndex, self._ModName, self._recordID, 20)
        nValues = [(nCondition.operType, nCondition.unused1, nCondition.compValue, nCondition.ifunc, nCondition.param1, nCondition.param2, nCondition.unused2) for nCondition in nConditions]
        while(diffLength < 0):
            CBash.DeleteFIDListElement(self._CollectionIndex, self._ModName, self._recordID, 20)
            diffLength += 1
        while(diffLength > 0):
            CBash.CreateFIDListElement(self._CollectionIndex, self._ModName, self._recordID, 20)
            diffLength -= 1
        for oCondition, nValue in zip(self.conditions, nValues):
            oCondition.operType, oCondition.unused1, oCondition.compValue, oCondition.ifunc, oCondition.param1, oCondition.param2, oCondition.unused2 = nValue
    conditions = property(get_conditions, set_conditions)
    def get_IsOffersServices(self):
        return (self.flags & 0x00000001) != 0
    def set_IsOffersServices(self, nValue):
        if (nValue == True): self.flags |= 0x00000001
        else: self.flags &= ~0x00000001
    IsOffersServices = property(get_IsOffersServices, set_IsOffersServices)
    def get_IsMustReachLocation(self):
        return (self.flags & 0x00000002) != 0
    def set_IsMustReachLocation(self, nValue):
        if (nValue == True): self.flags |= 0x00000002
        else: self.flags &= ~0x00000002
    IsMustReachLocation = property(get_IsMustReachLocation, set_IsMustReachLocation)
    def get_IsMustComplete(self):
        return (self.flags & 0x00000004) != 0
    def set_IsMustComplete(self, nValue):
        if (nValue == True): self.flags |= 0x00000004
        else: self.flags &= ~0x00000004
    IsMustComplete = property(get_IsMustComplete, set_IsMustComplete)
    def get_IsLockAtStart(self):
        return (self.flags & 0x00000008) != 0
    def set_IsLockAtStart(self, nValue):
        if (nValue == True): self.flags |= 0x00000008
        else: self.flags &= ~0x00000008
    IsLockAtStart = property(get_IsLockAtStart, set_IsLockAtStart)
    def get_IsLockAtEnd(self):
        return (self.flags & 0x00000010) != 0
    def set_IsLockAtEnd(self, nValue):
        if (nValue == True): self.flags |= 0x00000010
        else: self.flags &= ~0x00000010
    IsLockAtEnd = property(get_IsLockAtEnd, set_IsLockAtEnd)
    def get_IsLockAtLocation(self):
        return (self.flags & 0x00000020) != 0
    def set_IsLockAtLocation(self, nValue):
        if (nValue == True): self.flags |= 0x00000020
        else: self.flags &= ~0x00000020
    IsLockAtLocation = property(get_IsLockAtLocation, set_IsLockAtLocation)
    def get_IsUnlockAtStart(self):
        return (self.flags & 0x00000040) != 0
    def set_IsUnlockAtStart(self, nValue):
        if (nValue == True): self.flags |= 0x00000040
        else: self.flags &= ~0x00000040
    IsUnlockAtStart = property(get_IsUnlockAtStart, set_IsUnlockAtStart)
    def get_IsUnlockAtEnd(self):
        return (self.flags & 0x00000080) != 0
    def set_IsUnlockAtEnd(self, nValue):
        if (nValue == True): self.flags |= 0x00000080
        else: self.flags &= ~0x00000080
    IsUnlockAtEnd = property(get_IsUnlockAtEnd, set_IsUnlockAtEnd)
    def get_IsUnlockAtLocation(self):
        return (self.flags & 0x00000100) != 0
    def set_IsUnlockAtLocation(self, nValue):
        if (nValue == True): self.flags |= 0x00000100
        else: self.flags &= ~0x00000100
    IsUnlockAtLocation = property(get_IsUnlockAtLocation, set_IsUnlockAtLocation)
    def get_IsContinueIfPcNear(self):
        return (self.flags & 0x00000200) != 0
    def set_IsContinueIfPcNear(self, nValue):
        if (nValue == True): self.flags |= 0x00000200
        else: self.flags &= ~0x00000200
    IsContinueIfPcNear = property(get_IsContinueIfPcNear, set_IsContinueIfPcNear)
    def get_IsOncePerDay(self):
        return (self.flags & 0x00000400) != 0
    def set_IsOncePerDay(self, nValue):
        if (nValue == True): self.flags |= 0x00000400
        else: self.flags &= ~0x00000400
    IsOncePerDay = property(get_IsOncePerDay, set_IsOncePerDay)
    def get_IsSkipFallout(self):
        return (self.flags & 0x00001000) != 0
    def set_IsSkipFallout(self, nValue):
        if (nValue == True): self.flags |= 0x00001000
        else: self.flags &= ~0x00001000
    IsSkipFallout = property(get_IsSkipFallout, set_IsSkipFallout)
    def get_IsAlwaysRun(self):
        return (self.flags & 0x00002000) != 0
    def set_IsAlwaysRun(self, nValue):
        if (nValue == True): self.flags |= 0x00002000
        else: self.flags &= ~0x00002000
    IsAlwaysRun = property(get_IsAlwaysRun, set_IsAlwaysRun)
    def get_IsAlwaysSneak(self):
        return (self.flags & 0x00020000) != 0
    def set_IsAlwaysSneak(self, nValue):
        if (nValue == True): self.flags |= 0x00020000
        else: self.flags &= ~0x00020000
    IsAlwaysSneak = property(get_IsAlwaysSneak, set_IsAlwaysSneak)
    def get_IsAllowSwimming(self):
        return (self.flags & 0x00040000) != 0
    def set_IsAllowSwimming(self, nValue):
        if (nValue == True): self.flags |= 0x00040000
        else: self.flags &= ~0x00040000
    IsAllowSwimming = property(get_IsAllowSwimming, set_IsAllowSwimming)
    def get_IsAllowFalls(self):
        return (self.flags & 0x00080000) != 0
    def set_IsAllowFalls(self, nValue):
        if (nValue == True): self.flags |= 0x00080000
        else: self.flags &= ~0x00080000
    IsAllowFalls = property(get_IsAllowFalls, set_IsAllowFalls)
    def get_IsUnequipArmor(self):
        return (self.flags & 0x00100000) != 0
    def set_IsUnequipArmor(self, nValue):
        if (nValue == True): self.flags |= 0x00100000
        else: self.flags &= ~0x00100000
    IsUnequipArmor = property(get_IsUnequipArmor, set_IsUnequipArmor)
    def get_IsUnequipWeapons(self):
        return (self.flags & 0x00200000) != 0
    def set_IsUnequipWeapons(self, nValue):
        if (nValue == True): self.flags |= 0x00200000
        else: self.flags &= ~0x00200000
    IsUnequipWeapons = property(get_IsUnequipWeapons, set_IsUnequipWeapons)
    def get_IsDefensiveCombat(self):
        return (self.flags & 0x00400000) != 0
    def set_IsDefensiveCombat(self, nValue):
        if (nValue == True): self.flags |= 0x00400000
        else: self.flags &= ~0x00400000
    IsDefensiveCombat = property(get_IsDefensiveCombat, set_IsDefensiveCombat)
    def get_IsUseHorse(self):
        return (self.flags & 0x00800000) != 0
    def set_IsUseHorse(self, nValue):
        if (nValue == True): self.flags |= 0x00800000
        else: self.flags &= ~0x00800000
    IsUseHorse = property(get_IsUseHorse, set_IsUseHorse)
    def get_IsNoIdleAnims(self):
        return (self.flags & 0x01000000) != 0
    def set_IsNoIdleAnims(self, nValue):
        if (nValue == True): self.flags |= 0x01000000
        else: self.flags &= ~0x01000000
    IsNoIdleAnims = property(get_IsNoIdleAnims, set_IsNoIdleAnims)
    def get_IsAIFind(self):
        return (self.aiType == 0)
    def set_IsAIFind(self, nValue):
        if (nValue == True): self.aiType = 0
        elif(self.get_IsAIFind()): self.IsAIFollow = True
    IsAIFind = property(get_IsAIFind, set_IsAIFind)
    def get_IsAIFollow(self):
        return (self.aiType == 1)
    def set_IsAIFollow(self, nValue):
        if (nValue == True): self.aiType = 1
        elif(self.get_IsAIFollow()): self.IsAIFind = True
    IsAIFollow = property(get_IsAIFollow, set_IsAIFollow)
    def get_IsAIEscort(self):
        return (self.aiType == 2)
    def set_IsAIEscort(self, nValue):
        if (nValue == True): self.aiType = 2
        elif(self.get_IsAIEscort()): self.IsAIFind = True
    IsAIEscort = property(get_IsAIEscort, set_IsAIEscort)
    def get_IsAIEat(self):
        return (self.aiType == 3)
    def set_IsAIEat(self, nValue):
        if (nValue == True): self.aiType = 3
        elif(self.get_IsAIEat()): self.IsAIFind = True
    IsAIEat = property(get_IsAIEat, set_IsAIEat)
    def get_IsAISleep(self):
        return (self.aiType == 4)
    def set_IsAISleep(self, nValue):
        if (nValue == True): self.aiType = 4
        elif(self.get_IsAISleep()): self.IsAIFind = True
    IsAISleep = property(get_IsAISleep, set_IsAISleep)
    def get_IsAIWander(self):
        return (self.aiType == 5)
    def set_IsAIWander(self, nValue):
        if (nValue == True): self.aiType = 5
        elif(self.get_IsAIWander()): self.IsAIFind = True
    IsAIWander = property(get_IsAIWander, set_IsAIWander)
    def get_IsAITravel(self):
        return (self.aiType == 6)
    def set_IsAITravel(self, nValue):
        if (nValue == True): self.aiType = 6
        elif(self.get_IsAITravel()): self.IsAIFind = True
    IsAITravel = property(get_IsAITravel, set_IsAITravel)
    def get_IsAIAccompany(self):
        return (self.aiType == 7)
    def set_IsAIAccompany(self, nValue):
        if (nValue == True): self.aiType = 7
        elif(self.get_IsAIAccompany()): self.IsAIFind = True
    IsAIAccompany = property(get_IsAIAccompany, set_IsAIAccompany)
    def get_IsAIUseItemAt(self):
        return (self.aiType == 8)
    def set_IsAIUseItemAt(self, nValue):
        if (nValue == True): self.aiType = 8
        elif(self.get_IsAIUseItemAt()): self.IsAIFind = True
    IsAIUseItemAt = property(get_IsAIUseItemAt, set_IsAIUseItemAt)
    def get_IsAIAmbush(self):
        return (self.aiType == 9)
    def set_IsAIAmbush(self, nValue):
        if (nValue == True): self.aiType = 9
        elif(self.get_IsAIAmbush()): self.IsAIFind = True
    IsAIAmbush = property(get_IsAIAmbush, set_IsAIAmbush)
    def get_IsAIFleeNotCombat(self):
        return (self.aiType == 10)
    def set_IsAIFleeNotCombat(self, nValue):
        if (nValue == True): self.aiType = 10
        elif(self.get_IsAIFleeNotCombat()): self.IsAIFind = True
    IsAIFleeNotCombat = property(get_IsAIFleeNotCombat, set_IsAIFleeNotCombat)
    def get_IsAICastMagic(self):
        return (self.aiType == 11)
    def set_IsAICastMagic(self, nValue):
        if (nValue == True): self.aiType = 11
        elif(self.get_IsAICastMagic()): self.IsAIFind = True
    IsAICastMagic = property(get_IsAICastMagic, set_IsAICastMagic)
    def get_IsLocNearReference(self):
        if(self.locType == None): return False
        return (self.locType == 0)
    def set_IsLocNearReference(self, nValue):
        if (nValue == True): self.locType = 0
        elif(self.get_LocNearReference()): self.locType = 1
    IsLocNearReference = property(get_IsLocNearReference, set_IsLocNearReference)
    def get_IsLocInCell(self):
        if(self.locType == None): return False
        return (self.locType == 1)
    def set_IsLocInCell(self, nValue):
        if (nValue == True): self.locType = 1
        elif(self.get_LocInCell()): self.locType = 0
    IsLocInCell = property(get_IsLocInCell, set_IsLocInCell)
    def get_IsLocNearCurrentLocation(self):
        if(self.locType == None): return False
        return (self.locType == 2)
    def set_IsLocNearCurrentLocation(self, nValue):
        if (nValue == True): self.locType = 2
        elif(self.get_LocNearCurrentLocation()): self.locType = 0
    IsLocNearCurrentLocation = property(get_IsLocNearCurrentLocation, set_IsLocNearCurrentLocation)
    def get_IsLocNearEditorLocation(self):
        if(self.locType == None): return False
        return (self.locType == 3)
    def set_IsLocNearEditorLocation(self, nValue):
        if (nValue == True): self.locType = 3
        elif(self.get_LocNearEditorLocation()): self.locType = 0
    IsLocNearEditorLocation = property(get_IsLocNearEditorLocation, set_IsLocNearEditorLocation)
    def get_IsLocObjectID(self):
        if(self.locType == None): return False
        return (self.locType == 4)
    def set_IsLocObjectID(self, nValue):
        if (nValue == True): self.locType = 4
        elif(self.get_LocObjectID()): self.locType = 0
    IsLocObjectID = property(get_IsLocObjectID, set_IsLocObjectID)
    def get_IsLocObjectType(self):
        if(self.locType == None): return False
        return (self.locType == 5)
    def set_IsLocObjectType(self, nValue):
        if (nValue == True): self.locType = 5
        elif(self.get_LocObjectType()): self.locType = 0
    IsLocObjectType = property(get_IsLocObjectType, set_IsLocObjectType)
    def get_IsTargetReference(self):
        if(self.targetType == None): return False
        return (self.targetType == 0)
    def set_IsTargetReference(self, nValue):
        if (nValue == True): self.targetType = 0
        elif(self.get_TargetReference()): self.targetType = 1
    IsTargetReference = property(get_IsTargetReference, set_IsTargetReference)
    def get_IsTargetObjectID(self):
        if(self.targetType == None): return False
        return (self.targetType == 1)
    def set_IsTargetObjectID(self, nValue):
        if (nValue == True): self.targetType = 1
        elif(self.get_TargetObjectID()): self.targetType = 0
    IsTargetObjectID = property(get_IsTargetObjectID, set_IsTargetObjectID)
    def get_IsTargetObjectType(self):
        if(self.targetType == None): return False
        return (self.targetType == 2)
    def set_IsTargetObjectType(self, nValue):
        if (nValue == True): self.targetType = 2
        elif(self.get_TargetObjectType()): self.targetType = 0
    IsTargetObjectType = property(get_IsTargetObjectType, set_IsTargetObjectType)
    
class CSTYRecord(BaseRecord):
    def CopyAsOverride(self, targetMod):
        FID = CBash.CopyCSTYRecord(self._CollectionIndex, self._ModName, self._recordID, targetMod._ModName, c_bool(True))
        if(FID): return CSTYRecord(self._CollectionIndex, targetMod._ModName, FID)
        return None
    def CopyAsNew(self, targetMod):
        FID = CBash.CopyCSTYRecord(self._CollectionIndex, self._ModName, self._recordID, targetMod._ModName, c_bool(False))
        if(FID): return CSTYRecord(self._CollectionIndex, targetMod._ModName, FID)
        return None
    def get_dodgeChance(self):
        CBash.ReadFIDField.restype = POINTER(c_ubyte)
        retValue = CBash.ReadFIDField(self._CollectionIndex, self._ModName, self._recordID, 6)
        if(retValue): return retValue.contents.value
        return None
    def set_dodgeChance(self, nValue):
        CBash.SetFIDFieldUC(self._CollectionIndex, self._ModName, self._recordID, 6, c_ubyte(nValue))
    dodgeChance = property(get_dodgeChance, set_dodgeChance)
    def get_lrChance(self):
        CBash.ReadFIDField.restype = POINTER(c_ubyte)
        retValue = CBash.ReadFIDField(self._CollectionIndex, self._ModName, self._recordID, 7)
        if(retValue): return retValue.contents.value
        return None
    def set_lrChance(self, nValue):
        CBash.SetFIDFieldUC(self._CollectionIndex, self._ModName, self._recordID, 7, c_ubyte(nValue))
    lrChance = property(get_lrChance, set_lrChance)
    def get_unused1(self):
        numRecords = CBash.GetFIDFieldArraySize(self._CollectionIndex, self._ModName, self._recordID, 8)
        if(numRecords > 0):
            cRecords = POINTER(c_ubyte * numRecords)()
            CBash.GetFIDFieldArray(self._CollectionIndex, self._ModName, self._recordID, 8, byref(cRecords))
            return [cRecords.contents[x] for x in range(0, numRecords)]
        return []
    def set_unused1(self, nValue):
        CBash.SetFIDFieldR(self._CollectionIndex, self._ModName, self._recordID, 8, struct.pack('2B', *nValue), 2)
    unused1 = property(get_unused1, set_unused1)
    def get_lrTimerMin(self):
        CBash.ReadFIDField.restype = POINTER(c_float)
        retValue = CBash.ReadFIDField(self._CollectionIndex, self._ModName, self._recordID, 9)
        if(retValue): return retValue.contents.value
        return None
    def set_lrTimerMin(self, nValue):
        CBash.SetFIDFieldF(self._CollectionIndex, self._ModName, self._recordID, 9, c_float(nValue))
    lrTimerMin = property(get_lrTimerMin, set_lrTimerMin)
    def get_lrTimerMax(self):
        CBash.ReadFIDField.restype = POINTER(c_float)
        retValue = CBash.ReadFIDField(self._CollectionIndex, self._ModName, self._recordID, 10)
        if(retValue): return retValue.contents.value
        return None
    def set_lrTimerMax(self, nValue):
        CBash.SetFIDFieldF(self._CollectionIndex, self._ModName, self._recordID, 10, c_float(nValue))
    lrTimerMax = property(get_lrTimerMax, set_lrTimerMax)
    def get_forTimerMin(self):
        CBash.ReadFIDField.restype = POINTER(c_float)
        retValue = CBash.ReadFIDField(self._CollectionIndex, self._ModName, self._recordID, 11)
        if(retValue): return retValue.contents.value
        return None
    def set_forTimerMin(self, nValue):
        CBash.SetFIDFieldF(self._CollectionIndex, self._ModName, self._recordID, 11, c_float(nValue))
    forTimerMin = property(get_forTimerMin, set_forTimerMin)
    def get_forTimerMax(self):
        CBash.ReadFIDField.restype = POINTER(c_float)
        retValue = CBash.ReadFIDField(self._CollectionIndex, self._ModName, self._recordID, 12)
        if(retValue): return retValue.contents.value
        return None
    def set_forTimerMax(self, nValue):
        CBash.SetFIDFieldF(self._CollectionIndex, self._ModName, self._recordID, 12, c_float(nValue))
    forTimerMax = property(get_forTimerMax, set_forTimerMax)
    def get_backTimerMin(self):
        CBash.ReadFIDField.restype = POINTER(c_float)
        retValue = CBash.ReadFIDField(self._CollectionIndex, self._ModName, self._recordID, 13)
        if(retValue): return retValue.contents.value
        return None
    def set_backTimerMin(self, nValue):
        CBash.SetFIDFieldF(self._CollectionIndex, self._ModName, self._recordID, 13, c_float(nValue))
    backTimerMin = property(get_backTimerMin, set_backTimerMin)
    def get_backTimerMax(self):
        CBash.ReadFIDField.restype = POINTER(c_float)
        retValue = CBash.ReadFIDField(self._CollectionIndex, self._ModName, self._recordID, 14)
        if(retValue): return retValue.contents.value
        return None
    def set_backTimerMax(self, nValue):
        CBash.SetFIDFieldF(self._CollectionIndex, self._ModName, self._recordID, 14, c_float(nValue))
    backTimerMax = property(get_backTimerMax, set_backTimerMax)
    def get_idleTimerMin(self):
        CBash.ReadFIDField.restype = POINTER(c_float)
        retValue = CBash.ReadFIDField(self._CollectionIndex, self._ModName, self._recordID, 15)
        if(retValue): return retValue.contents.value
        return None
    def set_idleTimerMin(self, nValue):
        CBash.SetFIDFieldF(self._CollectionIndex, self._ModName, self._recordID, 15, c_float(nValue))
    idleTimerMin = property(get_idleTimerMin, set_idleTimerMin)
    def get_idleTimerMax(self):
        CBash.ReadFIDField.restype = POINTER(c_float)
        retValue = CBash.ReadFIDField(self._CollectionIndex, self._ModName, self._recordID, 16)
        if(retValue): return retValue.contents.value
        return None
    def set_idleTimerMax(self, nValue):
        CBash.SetFIDFieldF(self._CollectionIndex, self._ModName, self._recordID, 16, c_float(nValue))
    idleTimerMax = property(get_idleTimerMax, set_idleTimerMax)
    def get_blkChance(self):
        CBash.ReadFIDField.restype = POINTER(c_ubyte)
        retValue = CBash.ReadFIDField(self._CollectionIndex, self._ModName, self._recordID, 17)
        if(retValue): return retValue.contents.value
        return None
    def set_blkChance(self, nValue):
        CBash.SetFIDFieldUC(self._CollectionIndex, self._ModName, self._recordID, 17, c_ubyte(nValue))
    blkChance = property(get_blkChance, set_blkChance)
    def get_atkChance(self):
        CBash.ReadFIDField.restype = POINTER(c_ubyte)
        retValue = CBash.ReadFIDField(self._CollectionIndex, self._ModName, self._recordID, 18)
        if(retValue): return retValue.contents.value
        return None
    def set_atkChance(self, nValue):
        CBash.SetFIDFieldUC(self._CollectionIndex, self._ModName, self._recordID, 18, c_ubyte(nValue))
    atkChance = property(get_atkChance, set_atkChance)
    def get_unused2(self):
        numRecords = CBash.GetFIDFieldArraySize(self._CollectionIndex, self._ModName, self._recordID, 19)
        if(numRecords > 0):
            cRecords = POINTER(c_ubyte * numRecords)()
            CBash.GetFIDFieldArray(self._CollectionIndex, self._ModName, self._recordID, 19, byref(cRecords))
            return [cRecords.contents[x] for x in range(0, numRecords)]
        return []
    def set_unused2(self, nValue):
        CBash.SetFIDFieldR(self._CollectionIndex, self._ModName, self._recordID, 19, struct.pack('2B', *nValue), 2)
    unused2 = property(get_unused2, set_unused2)
    def get_atkBRecoil(self):
        CBash.ReadFIDField.restype = POINTER(c_float)
        retValue = CBash.ReadFIDField(self._CollectionIndex, self._ModName, self._recordID, 20)
        if(retValue): return retValue.contents.value
        return None
    def set_atkBRecoil(self, nValue):
        CBash.SetFIDFieldF(self._CollectionIndex, self._ModName, self._recordID, 20, c_float(nValue))
    atkBRecoil = property(get_atkBRecoil, set_atkBRecoil)
    def get_atkBUnc(self):
        CBash.ReadFIDField.restype = POINTER(c_float)
        retValue = CBash.ReadFIDField(self._CollectionIndex, self._ModName, self._recordID, 21)
        if(retValue): return retValue.contents.value
        return None
    def set_atkBUnc(self, nValue):
        CBash.SetFIDFieldF(self._CollectionIndex, self._ModName, self._recordID, 21, c_float(nValue))
    atkBUnc = property(get_atkBUnc, set_atkBUnc)
    def get_atkBh2h(self):
        CBash.ReadFIDField.restype = POINTER(c_float)
        retValue = CBash.ReadFIDField(self._CollectionIndex, self._ModName, self._recordID, 22)
        if(retValue): return retValue.contents.value
        return None
    def set_atkBh2h(self, nValue):
        CBash.SetFIDFieldF(self._CollectionIndex, self._ModName, self._recordID, 22, c_float(nValue))
    atkBh2h = property(get_atkBh2h, set_atkBh2h)
    def get_pAtkChance(self):
        CBash.ReadFIDField.restype = POINTER(c_ubyte)
        retValue = CBash.ReadFIDField(self._CollectionIndex, self._ModName, self._recordID, 23)
        if(retValue): return retValue.contents.value
        return None
    def set_pAtkChance(self, nValue):
        CBash.SetFIDFieldUC(self._CollectionIndex, self._ModName, self._recordID, 23, c_ubyte(nValue))
    pAtkChance = property(get_pAtkChance, set_pAtkChance)
    def get_unused3(self):
        numRecords = CBash.GetFIDFieldArraySize(self._CollectionIndex, self._ModName, self._recordID, 24)
        if(numRecords > 0):
            cRecords = POINTER(c_ubyte * numRecords)()
            CBash.GetFIDFieldArray(self._CollectionIndex, self._ModName, self._recordID, 24, byref(cRecords))
            return [cRecords.contents[x] for x in range(0, numRecords)]
        return []
    def set_unused3(self, nValue):
        CBash.SetFIDFieldR(self._CollectionIndex, self._ModName, self._recordID, 24, struct.pack('3B', *nValue), 3)
    unused3 = property(get_unused3, set_unused3)
    def get_pAtkBRecoil(self):
        CBash.ReadFIDField.restype = POINTER(c_float)
        retValue = CBash.ReadFIDField(self._CollectionIndex, self._ModName, self._recordID, 25)
        if(retValue): return retValue.contents.value
        return None
    def set_pAtkBRecoil(self, nValue):
        CBash.SetFIDFieldF(self._CollectionIndex, self._ModName, self._recordID, 25, c_float(nValue))
    pAtkBRecoil = property(get_pAtkBRecoil, set_pAtkBRecoil)
    def get_pAtkBUnc(self):
        CBash.ReadFIDField.restype = POINTER(c_float)
        retValue = CBash.ReadFIDField(self._CollectionIndex, self._ModName, self._recordID, 26)
        if(retValue): return retValue.contents.value
        return None
    def set_pAtkBUnc(self, nValue):
        CBash.SetFIDFieldF(self._CollectionIndex, self._ModName, self._recordID, 26, c_float(nValue))
    pAtkBUnc = property(get_pAtkBUnc, set_pAtkBUnc)
    def get_pAtkNormal(self):
        CBash.ReadFIDField.restype = POINTER(c_ubyte)
        retValue = CBash.ReadFIDField(self._CollectionIndex, self._ModName, self._recordID, 27)
        if(retValue): return retValue.contents.value
        return None
    def set_pAtkNormal(self, nValue):
        CBash.SetFIDFieldUC(self._CollectionIndex, self._ModName, self._recordID, 27, c_ubyte(nValue))
    pAtkNormal = property(get_pAtkNormal, set_pAtkNormal)
    def get_pAtkFor(self):
        CBash.ReadFIDField.restype = POINTER(c_ubyte)
        retValue = CBash.ReadFIDField(self._CollectionIndex, self._ModName, self._recordID, 28)
        if(retValue): return retValue.contents.value
        return None
    def set_pAtkFor(self, nValue):
        CBash.SetFIDFieldUC(self._CollectionIndex, self._ModName, self._recordID, 28, c_ubyte(nValue))
    pAtkFor = property(get_pAtkFor, set_pAtkFor)
    def get_pAtkBack(self):
        CBash.ReadFIDField.restype = POINTER(c_ubyte)
        retValue = CBash.ReadFIDField(self._CollectionIndex, self._ModName, self._recordID, 29)
        if(retValue): return retValue.contents.value
        return None
    def set_pAtkBack(self, nValue):
        CBash.SetFIDFieldUC(self._CollectionIndex, self._ModName, self._recordID, 29, c_ubyte(nValue))
    pAtkBack = property(get_pAtkBack, set_pAtkBack)
    def get_pAtkL(self):
        CBash.ReadFIDField.restype = POINTER(c_ubyte)
        retValue = CBash.ReadFIDField(self._CollectionIndex, self._ModName, self._recordID, 30)
        if(retValue): return retValue.contents.value
        return None
    def set_pAtkL(self, nValue):
        CBash.SetFIDFieldUC(self._CollectionIndex, self._ModName, self._recordID, 30, c_ubyte(nValue))
    pAtkL = property(get_pAtkL, set_pAtkL)
    def get_pAtkR(self):
        CBash.ReadFIDField.restype = POINTER(c_ubyte)
        retValue = CBash.ReadFIDField(self._CollectionIndex, self._ModName, self._recordID, 31)
        if(retValue): return retValue.contents.value
        return None
    def set_pAtkR(self, nValue):
        CBash.SetFIDFieldUC(self._CollectionIndex, self._ModName, self._recordID, 31, c_ubyte(nValue))
    pAtkR = property(get_pAtkR, set_pAtkR)
    def get_unused4(self):
        numRecords = CBash.GetFIDFieldArraySize(self._CollectionIndex, self._ModName, self._recordID, 32)
        if(numRecords > 0):
            cRecords = POINTER(c_ubyte * numRecords)()
            CBash.GetFIDFieldArray(self._CollectionIndex, self._ModName, self._recordID, 32, byref(cRecords))
            return [cRecords.contents[x] for x in range(0, numRecords)]
        return []
    def set_unused4(self, nValue):
        CBash.SetFIDFieldR(self._CollectionIndex, self._ModName, self._recordID, 32, struct.pack('3B', *nValue), 3)
    unused4 = property(get_unused4, set_unused4)                    
    def get_holdTimerMin(self):
        CBash.ReadFIDField.restype = POINTER(c_float)
        retValue = CBash.ReadFIDField(self._CollectionIndex, self._ModName, self._recordID, 33)
        if(retValue): return retValue.contents.value
        return None
    def set_holdTimerMin(self, nValue):
        CBash.SetFIDFieldF(self._CollectionIndex, self._ModName, self._recordID, 33, c_float(nValue))
    holdTimerMin = property(get_holdTimerMin, set_holdTimerMin)
    def get_holdTimerMax(self):
        CBash.ReadFIDField.restype = POINTER(c_float)
        retValue = CBash.ReadFIDField(self._CollectionIndex, self._ModName, self._recordID, 34)
        if(retValue): return retValue.contents.value
        return None
    def set_holdTimerMax(self, nValue):
        CBash.SetFIDFieldF(self._CollectionIndex, self._ModName, self._recordID, 34, c_float(nValue))
    holdTimerMax = property(get_holdTimerMax, set_holdTimerMax)
    def get_flagsA(self):
        CBash.ReadFIDField.restype = POINTER(c_ubyte)
        retValue = CBash.ReadFIDField(self._CollectionIndex, self._ModName, self._recordID, 35)
        if(retValue): return retValue.contents.value
        return None
    def set_flagsA(self, nValue):
        CBash.SetFIDFieldUC(self._CollectionIndex, self._ModName, self._recordID, 35, c_ubyte(nValue))
    flagsA = property(get_flagsA, set_flagsA)
    def get_acroDodge(self):
        CBash.ReadFIDField.restype = POINTER(c_ubyte)
        retValue = CBash.ReadFIDField(self._CollectionIndex, self._ModName, self._recordID, 36)
        if(retValue): return retValue.contents.value
        return None
    def set_acroDodge(self, nValue):
        CBash.SetFIDFieldUC(self._CollectionIndex, self._ModName, self._recordID, 36, c_ubyte(nValue))
    acroDodge = property(get_acroDodge, set_acroDodge)
    def get_unused5(self):
        numRecords = CBash.GetFIDFieldArraySize(self._CollectionIndex, self._ModName, self._recordID, 37)
        if(numRecords > 0):
            cRecords = POINTER(c_ubyte * numRecords)()
            CBash.GetFIDFieldArray(self._CollectionIndex, self._ModName, self._recordID, 37, byref(cRecords))
            return [cRecords.contents[x] for x in range(0, numRecords)]
        return []
    def set_unused5(self, nValue):
        CBash.SetFIDFieldR(self._CollectionIndex, self._ModName, self._recordID, 37, struct.pack('2B', *nValue), 2)
    unused5 = property(get_unused5, set_unused5)
    def get_rMultOpt(self):
        CBash.ReadFIDField.restype = POINTER(c_float)
        retValue = CBash.ReadFIDField(self._CollectionIndex, self._ModName, self._recordID, 38)
        if(retValue): return retValue.contents.value
        return None
    def set_rMultOpt(self, nValue):
        CBash.SetFIDFieldF(self._CollectionIndex, self._ModName, self._recordID, 38, c_float(nValue))
    rMultOpt = property(get_rMultOpt, set_rMultOpt)
    def get_rMultMax(self):
        CBash.ReadFIDField.restype = POINTER(c_float)
        retValue = CBash.ReadFIDField(self._CollectionIndex, self._ModName, self._recordID, 39)
        if(retValue): return retValue.contents.value
        return None
    def set_rMultMax(self, nValue):
        CBash.SetFIDFieldF(self._CollectionIndex, self._ModName, self._recordID, 39, c_float(nValue))
    rMultMax = property(get_rMultMax, set_rMultMax)
    def get_mDistance(self):
        CBash.ReadFIDField.restype = POINTER(c_float)
        retValue = CBash.ReadFIDField(self._CollectionIndex, self._ModName, self._recordID, 40)
        if(retValue): return retValue.contents.value
        return None
    def set_mDistance(self, nValue):
        CBash.SetFIDFieldF(self._CollectionIndex, self._ModName, self._recordID, 40, c_float(nValue))
    mDistance = property(get_mDistance, set_mDistance)
    def get_rDistance(self):
        CBash.ReadFIDField.restype = POINTER(c_float)
        retValue = CBash.ReadFIDField(self._CollectionIndex, self._ModName, self._recordID, 41)
        if(retValue): return retValue.contents.value
        return None
    def set_rDistance(self, nValue):
        CBash.SetFIDFieldF(self._CollectionIndex, self._ModName, self._recordID, 41, c_float(nValue))
    rDistance = property(get_rDistance, set_rDistance)
    def get_buffStand(self):
        CBash.ReadFIDField.restype = POINTER(c_float)
        retValue = CBash.ReadFIDField(self._CollectionIndex, self._ModName, self._recordID, 42)
        if(retValue): return retValue.contents.value
        return None
    def set_buffStand(self, nValue):
        CBash.SetFIDFieldF(self._CollectionIndex, self._ModName, self._recordID, 42, c_float(nValue))
    buffStand = property(get_buffStand, set_buffStand)
    def get_rStand(self):
        CBash.ReadFIDField.restype = POINTER(c_float)
        retValue = CBash.ReadFIDField(self._CollectionIndex, self._ModName, self._recordID, 43)
        if(retValue): return retValue.contents.value
        return None
    def set_rStand(self, nValue):
        CBash.SetFIDFieldF(self._CollectionIndex, self._ModName, self._recordID, 43, c_float(nValue))
    rStand = property(get_rStand, set_rStand)
    def get_groupStand(self):
        CBash.ReadFIDField.restype = POINTER(c_float)
        retValue = CBash.ReadFIDField(self._CollectionIndex, self._ModName, self._recordID, 44)
        if(retValue): return retValue.contents.value
        return None
    def set_groupStand(self, nValue):
        CBash.SetFIDFieldF(self._CollectionIndex, self._ModName, self._recordID, 44, c_float(nValue))
    groupStand = property(get_groupStand, set_groupStand)
    def get_rushChance(self):
        CBash.ReadFIDField.restype = POINTER(c_ubyte)
        retValue = CBash.ReadFIDField(self._CollectionIndex, self._ModName, self._recordID, 45)
        if(retValue): return retValue.contents.value
        return None
    def set_rushChance(self, nValue):
        CBash.SetFIDFieldUC(self._CollectionIndex, self._ModName, self._recordID, 45, c_ubyte(nValue))
    rushChance = property(get_rushChance, set_rushChance)
    def get_unused6(self):
        numRecords = CBash.GetFIDFieldArraySize(self._CollectionIndex, self._ModName, self._recordID, 46)
        if(numRecords > 0):
            cRecords = POINTER(c_ubyte * numRecords)()
            CBash.GetFIDFieldArray(self._CollectionIndex, self._ModName, self._recordID, 46, byref(cRecords))
            return [cRecords.contents[x] for x in range(0, numRecords)]
        return []
    def set_unused6(self, nValue):
        CBash.SetFIDFieldR(self._CollectionIndex, self._ModName, self._recordID, 46, struct.pack('3B', *nValue), 3)
    unused6 = property(get_unused6, set_unused6)
    def get_rushMult(self):
        CBash.ReadFIDField.restype = POINTER(c_float)
        retValue = CBash.ReadFIDField(self._CollectionIndex, self._ModName, self._recordID, 47)
        if(retValue): return retValue.contents.value
        return None
    def set_rushMult(self, nValue):
        CBash.SetFIDFieldF(self._CollectionIndex, self._ModName, self._recordID, 47, c_float(nValue))
    rushMult = property(get_rushMult, set_rushMult)
    def get_flagsB(self):
        CBash.ReadFIDField.restype = POINTER(c_uint)
        retValue = CBash.ReadFIDField(self._CollectionIndex, self._ModName, self._recordID, 48)
        if(retValue): return retValue.contents.value
        return None
    def set_flagsB(self, nValue):
        CBash.SetFIDFieldUI(self._CollectionIndex, self._ModName, self._recordID, 48, nValue)
    flagsB = property(get_flagsB, set_flagsB)
    def get_dodgeFMult(self):
        CBash.ReadFIDField.restype = POINTER(c_float)
        retValue = CBash.ReadFIDField(self._CollectionIndex, self._ModName, self._recordID, 49)
        if(retValue): return retValue.contents.value
        return None
    def set_dodgeFMult(self, nValue):
        CBash.SetFIDFieldF(self._CollectionIndex, self._ModName, self._recordID, 49, c_float(nValue))
    dodgeFMult = property(get_dodgeFMult, set_dodgeFMult)
    def get_dodgeFBase(self):
        CBash.ReadFIDField.restype = POINTER(c_float)
        retValue = CBash.ReadFIDField(self._CollectionIndex, self._ModName, self._recordID, 50)
        if(retValue): return retValue.contents.value
        return None
    def set_dodgeFBase(self, nValue):
        CBash.SetFIDFieldF(self._CollectionIndex, self._ModName, self._recordID, 50, c_float(nValue))
    dodgeFBase = property(get_dodgeFBase, set_dodgeFBase)
    def get_encSBase(self):
        CBash.ReadFIDField.restype = POINTER(c_float)
        retValue = CBash.ReadFIDField(self._CollectionIndex, self._ModName, self._recordID, 51)
        if(retValue): return retValue.contents.value
        return None
    def set_encSBase(self, nValue):
        CBash.SetFIDFieldF(self._CollectionIndex, self._ModName, self._recordID, 51, c_float(nValue))
    encSBase = property(get_encSBase, set_encSBase)
    def get_encSMult(self):
        CBash.ReadFIDField.restype = POINTER(c_float)
        retValue = CBash.ReadFIDField(self._CollectionIndex, self._ModName, self._recordID, 52)
        if(retValue): return retValue.contents.value
        return None
    def set_encSMult(self, nValue):
        CBash.SetFIDFieldF(self._CollectionIndex, self._ModName, self._recordID, 52, c_float(nValue))
    encSMult = property(get_encSMult, set_encSMult)
    def get_dodgeAtkMult(self):
        CBash.ReadFIDField.restype = POINTER(c_float)
        retValue = CBash.ReadFIDField(self._CollectionIndex, self._ModName, self._recordID, 53)
        if(retValue): return retValue.contents.value
        return None
    def set_dodgeAtkMult(self, nValue):
        CBash.SetFIDFieldF(self._CollectionIndex, self._ModName, self._recordID, 53, c_float(nValue))
    dodgeAtkMult = property(get_dodgeAtkMult, set_dodgeAtkMult)
    def get_dodgeNAtkMult(self):
        CBash.ReadFIDField.restype = POINTER(c_float)
        retValue = CBash.ReadFIDField(self._CollectionIndex, self._ModName, self._recordID, 54)
        if(retValue): return retValue.contents.value
        return None
    def set_dodgeNAtkMult(self, nValue):
        CBash.SetFIDFieldF(self._CollectionIndex, self._ModName, self._recordID, 54, c_float(nValue))
    dodgeNAtkMult = property(get_dodgeNAtkMult, set_dodgeNAtkMult)
    def get_dodgeBAtkMult(self):
        CBash.ReadFIDField.restype = POINTER(c_float)
        retValue = CBash.ReadFIDField(self._CollectionIndex, self._ModName, self._recordID, 55)
        if(retValue): return retValue.contents.value
        return None
    def set_dodgeBAtkMult(self, nValue):
        CBash.SetFIDFieldF(self._CollectionIndex, self._ModName, self._recordID, 55, c_float(nValue))
    dodgeBAtkMult = property(get_dodgeBAtkMult, set_dodgeBAtkMult)
    def get_dodgeBNAtkMult(self):
        CBash.ReadFIDField.restype = POINTER(c_float)
        retValue = CBash.ReadFIDField(self._CollectionIndex, self._ModName, self._recordID, 56)
        if(retValue): return retValue.contents.value
        return None
    def set_dodgeBNAtkMult(self, nValue):
        CBash.SetFIDFieldF(self._CollectionIndex, self._ModName, self._recordID, 56, c_float(nValue))
    dodgeBNAtkMult = property(get_dodgeBNAtkMult, set_dodgeBNAtkMult)
    def get_dodgeFAtkMult(self):
        CBash.ReadFIDField.restype = POINTER(c_float)
        retValue = CBash.ReadFIDField(self._CollectionIndex, self._ModName, self._recordID, 57)
        if(retValue): return retValue.contents.value
        return None
    def set_dodgeFAtkMult(self, nValue):
        CBash.SetFIDFieldF(self._CollectionIndex, self._ModName, self._recordID, 57, c_float(nValue))
    dodgeFAtkMult = property(get_dodgeFAtkMult, set_dodgeFAtkMult)
    def get_dodgeFNAtkMult(self):
        CBash.ReadFIDField.restype = POINTER(c_float)
        retValue = CBash.ReadFIDField(self._CollectionIndex, self._ModName, self._recordID, 58)
        if(retValue): return retValue.contents.value
        return None
    def set_dodgeFNAtkMult(self, nValue):
        CBash.SetFIDFieldF(self._CollectionIndex, self._ModName, self._recordID, 58, c_float(nValue))
    dodgeFNAtkMult = property(get_dodgeFNAtkMult, set_dodgeFNAtkMult)
    def get_blockMult(self):
        CBash.ReadFIDField.restype = POINTER(c_float)
        retValue = CBash.ReadFIDField(self._CollectionIndex, self._ModName, self._recordID, 59)
        if(retValue): return retValue.contents.value
        return None
    def set_blockMult(self, nValue):
        CBash.SetFIDFieldF(self._CollectionIndex, self._ModName, self._recordID, 59, c_float(nValue))
    blockMult = property(get_blockMult, set_blockMult)
    def get_blockBase(self):
        CBash.ReadFIDField.restype = POINTER(c_float)
        retValue = CBash.ReadFIDField(self._CollectionIndex, self._ModName, self._recordID, 60)
        if(retValue): return retValue.contents.value
        return None
    def set_blockBase(self, nValue):
        CBash.SetFIDFieldF(self._CollectionIndex, self._ModName, self._recordID, 60, c_float(nValue))
    blockBase = property(get_blockBase, set_blockBase)
    def get_blockAtkMult(self):
        CBash.ReadFIDField.restype = POINTER(c_float)
        retValue = CBash.ReadFIDField(self._CollectionIndex, self._ModName, self._recordID, 61)
        if(retValue): return retValue.contents.value
        return None
    def set_blockAtkMult(self, nValue):
        CBash.SetFIDFieldF(self._CollectionIndex, self._ModName, self._recordID, 61, c_float(nValue))
    blockAtkMult = property(get_blockAtkMult, set_blockAtkMult)
    def get_blockNAtkMult(self):
        CBash.ReadFIDField.restype = POINTER(c_float)
        retValue = CBash.ReadFIDField(self._CollectionIndex, self._ModName, self._recordID, 62)
        if(retValue): return retValue.contents.value
        return None
    def set_blockNAtkMult(self, nValue):
        CBash.SetFIDFieldF(self._CollectionIndex, self._ModName, self._recordID, 62, c_float(nValue))
    blockNAtkMult = property(get_blockNAtkMult, set_blockNAtkMult)
    def get_atkMult(self):
        CBash.ReadFIDField.restype = POINTER(c_float)
        retValue = CBash.ReadFIDField(self._CollectionIndex, self._ModName, self._recordID, 63)
        if(retValue): return retValue.contents.value
        return None
    def set_atkMult(self, nValue):
        CBash.SetFIDFieldF(self._CollectionIndex, self._ModName, self._recordID, 63, c_float(nValue))
    atkMult = property(get_atkMult, set_atkMult)
    def get_atkBase(self):
        CBash.ReadFIDField.restype = POINTER(c_float)
        retValue = CBash.ReadFIDField(self._CollectionIndex, self._ModName, self._recordID, 64)
        if(retValue): return retValue.contents.value
        return None
    def set_atkBase(self, nValue):
        CBash.SetFIDFieldF(self._CollectionIndex, self._ModName, self._recordID, 64, c_float(nValue))
    atkBase = property(get_atkBase, set_atkBase)
    def get_atkAtkMult(self):
        CBash.ReadFIDField.restype = POINTER(c_float)
        retValue = CBash.ReadFIDField(self._CollectionIndex, self._ModName, self._recordID, 65)
        if(retValue): return retValue.contents.value
        return None
    def set_atkAtkMult(self, nValue):
        CBash.SetFIDFieldF(self._CollectionIndex, self._ModName, self._recordID, 65, c_float(nValue))
    atkAtkMult = property(get_atkAtkMult, set_atkAtkMult)
    def get_atkNAtkMult(self):
        CBash.ReadFIDField.restype = POINTER(c_float)
        retValue = CBash.ReadFIDField(self._CollectionIndex, self._ModName, self._recordID, 66)
        if(retValue): return retValue.contents.value
        return None
    def set_atkNAtkMult(self, nValue):
        CBash.SetFIDFieldF(self._CollectionIndex, self._ModName, self._recordID, 66, c_float(nValue))
    atkNAtkMult = property(get_atkNAtkMult, set_atkNAtkMult)
    def get_atkBlockMult(self):
        CBash.ReadFIDField.restype = POINTER(c_float)
        retValue = CBash.ReadFIDField(self._CollectionIndex, self._ModName, self._recordID, 67)
        if(retValue): return retValue.contents.value
        return None
    def set_atkBlockMult(self, nValue):
        CBash.SetFIDFieldF(self._CollectionIndex, self._ModName, self._recordID, 67, c_float(nValue))
    atkBlockMult = property(get_atkBlockMult, set_atkBlockMult)
    def get_pAtkFBase(self):
        CBash.ReadFIDField.restype = POINTER(c_float)
        retValue = CBash.ReadFIDField(self._CollectionIndex, self._ModName, self._recordID, 68)
        if(retValue): return retValue.contents.value
        return None
    def set_pAtkFBase(self, nValue):
        CBash.SetFIDFieldF(self._CollectionIndex, self._ModName, self._recordID, 68, c_float(nValue))
    pAtkFBase = property(get_pAtkFBase, set_pAtkFBase)
    def get_pAtkFMult(self):
        CBash.ReadFIDField.restype = POINTER(c_float)
        retValue = CBash.ReadFIDField(self._CollectionIndex, self._ModName, self._recordID, 69)
        if(retValue): return retValue.contents.value
        return None
    def set_pAtkFMult(self, nValue):
        CBash.SetFIDFieldF(self._CollectionIndex, self._ModName, self._recordID, 69, c_float(nValue))
    pAtkFMult = property(get_pAtkFMult, set_pAtkFMult)
    def get_IsUseAdvanced(self):
        return (self.flagsA & 0x00000001) != 0
    def set_IsUseAdvanced(self, nValue):
        if (nValue == True): self.flagsA |= 0x00000001
        else: self.flagsA &= ~0x00000001
    IsUseAdvanced = property(get_IsUseAdvanced, set_IsUseAdvanced)
    def get_IsUseChanceForAttack(self):
        return (self.flagsA & 0x00000002) != 0
    def set_IsUseChanceForAttack(self, nValue):
        if (nValue == True): self.flagsA |= 0x00000002
        else: self.flagsA &= ~0x00000002
    IsUseChanceForAttack = property(get_IsUseChanceForAttack, set_IsUseChanceForAttack)
    def get_IsIgnoreAllies(self):
        return (self.flagsA & 0x00000004) != 0
    def set_IsIgnoreAllies(self, nValue):
        if (nValue == True): self.flagsA |= 0x00000004
        else: self.flagsA &= ~0x00000004
    IsIgnoreAllies = property(get_IsIgnoreAllies, set_IsIgnoreAllies)
    def get_IsWillYield(self):
        return (self.flagsA & 0x00000008) != 0
    def set_IsWillYield(self, nValue):
        if (nValue == True): self.flagsA |= 0x00000008
        else: self.flagsA &= ~0x00000008
    IsWillYield = property(get_IsWillYield, set_IsWillYield)
    def get_IsRejectsYields(self):
        return (self.flagsA & 0x00000010) != 0
    def set_IsRejectsYields(self, nValue):
        if (nValue == True): self.flagsA |= 0x00000010
        else: self.flagsA &= ~0x00000010
    IsRejectsYields = property(get_IsRejectsYields, set_IsRejectsYields)
    def get_IsFleeingDisabled(self):
        return (self.flagsA & 0x00000020) != 0
    def set_IsFleeingDisabled(self, nValue):
        if (nValue == True): self.flagsA |= 0x00000020
        else: self.flagsA &= ~0x00000020
    IsFleeingDisabled = property(get_IsFleeingDisabled, set_IsFleeingDisabled)
    def get_IsPrefersRanged(self):
        return (self.flagsA & 0x00000040) != 0
    def set_IsPrefersRanged(self, nValue):
        if (nValue == True): self.flagsA |= 0x00000040
        else: self.flagsA &= ~0x00000040
    IsPrefersRanged = property(get_IsPrefersRanged, set_IsPrefersRanged)
    def get_IsMeleeAlertOK(self):
        return (self.flagsA & 0x00000080) != 0
    def set_IsMeleeAlertOK(self, nValue):
        if (nValue == True): self.flagsA |= 0x00000080
        else: self.flagsA &= ~0x00000080
    IsMeleeAlertOK = property(get_IsMeleeAlertOK, set_IsMeleeAlertOK)
    def get_IsDoNotAcquire(self):
        return (self.flagsB & 0x00000001) != 0
    def set_IsDoNotAcquire(self, nValue):
        if (nValue == True): self.flagsB |= 0x00000001
        else: self.flagsB &= ~0x00000001
    IsDoNotAcquire = property(get_IsDoNotAcquire, set_IsDoNotAcquire)
    
class LSCRRecord(BaseRecord):
    def CopyAsOverride(self, targetMod):
        FID = CBash.CopyLSCRRecord(self._CollectionIndex, self._ModName, self._recordID, targetMod._ModName, c_bool(True))
        if(FID): return LSCRRecord(self._CollectionIndex, targetMod._ModName, FID)
        return None
    def CopyAsNew(self, targetMod):
        FID = CBash.CopyLSCRRecord(self._CollectionIndex, self._ModName, self._recordID, targetMod._ModName, c_bool(False))
        if(FID): return LSCRRecord(self._CollectionIndex, targetMod._ModName, FID)
        return None
    class Location(object):
        def __init__(self, CollectionIndex, ModName, recordID, listIndex):
            self._CollectionIndex = CollectionIndex
            self._ModName = ModName
            self._recordID = recordID
            self._listIndex = listIndex
        def get_direct(self):
            CBash.ReadFIDListField.restype = POINTER(c_uint)
            retValue = CBash.ReadFIDListField(self._CollectionIndex, self._ModName, self._recordID, 8, self._listIndex, 1)
            if(retValue): return retValue.contents.value
            return None
        def set_direct(self, nValue):
            CBash.SetFIDListFieldUI(self._CollectionIndex, self._ModName, self._recordID, 8, self._listIndex, 1, nValue)
        direct = property(get_direct, set_direct)
        def get_indirect(self):
            CBash.ReadFIDListField.restype = POINTER(c_uint)
            retValue = CBash.ReadFIDListField(self._CollectionIndex, self._ModName, self._recordID, 8, self._listIndex, 2)
            if(retValue): return retValue.contents.value
            return None
        def set_indirect(self, nValue):
            CBash.SetFIDListFieldUI(self._CollectionIndex, self._ModName, self._recordID, 8, self._listIndex, 2, nValue)
        indirect = property(get_indirect, set_indirect)
        def get_gridY(self):
            CBash.ReadFIDListField.restype = POINTER(c_short)
            retValue = CBash.ReadFIDListField(self._CollectionIndex, self._ModName, self._recordID, 8, self._listIndex, 3)
            if(retValue): return retValue.contents.value
            return None
        def set_gridY(self, nValue):
            CBash.SetFIDListFieldS(self._CollectionIndex, self._ModName, self._recordID, 8, self._listIndex, 3, c_short(nValue))
        gridY = property(get_gridY, set_gridY)
        def get_gridX(self):
            CBash.ReadFIDListField.restype = POINTER(c_short)
            retValue = CBash.ReadFIDListField(self._CollectionIndex, self._ModName, self._recordID, 8, self._listIndex, 4)
            if(retValue): return retValue.contents.value
            return None
        def set_gridX(self, nValue):
            CBash.SetFIDListFieldS(self._CollectionIndex, self._ModName, self._recordID, 8, self._listIndex, 4, c_short(nValue))
        gridX = property(get_gridX, set_gridX)
    def newLocationsElement(self):
        listIndex = CBash.CreateFIDListElement(self._CollectionIndex, self._ModName, self._recordID, 8)
        if(listIndex == -1): return None
        return self.Location(self._CollectionIndex, self._ModName, self._recordID, listIndex)
    def get_iconPath(self):
        CBash.ReadFIDField.restype = c_char_p
        return CBash.ReadFIDField(self._CollectionIndex, self._ModName, self._recordID, 6)
    def set_iconPath(self, nValue):
        CBash.SetFIDFieldStr(self._CollectionIndex, self._ModName, self._recordID, 6, nValue)
    iconPath = property(get_iconPath, set_iconPath)
    def get_text(self):
        CBash.ReadFIDField.restype = c_char_p
        return CBash.ReadFIDField(self._CollectionIndex, self._ModName, self._recordID, 7)
    def set_text(self, nValue):
        CBash.SetFIDFieldStr(self._CollectionIndex, self._ModName, self._recordID, 7, nValue)
    text = property(get_text, set_text)
    def get_locations(self):
        numRecords = CBash.GetFIDListSize(self._CollectionIndex, self._ModName, self._recordID, 8)
        if(numRecords > 0): return [self.Location(self._CollectionIndex, self._ModName, self._recordID, x) for x in range(0, numRecords)]
        return []
    def set_locations(self, nLocations):
        diffLength = len(nLocations) - CBash.GetFIDListSize(self._CollectionIndex, self._ModName, self._recordID, 8)
        nValues = [(nLocation.direct, nLocation.indirect, nLocation.gridY, nLocation.gridX) for nLocation in nLocations]
        while(diffLength < 0):
            CBash.DeleteFIDListElement(self._CollectionIndex, self._ModName, self._recordID, 8)
            diffLength += 1
        while(diffLength > 0):
            CBash.CreateFIDListElement(self._CollectionIndex, self._ModName, self._recordID, 8)
            diffLength -= 1
        for oLocation, nValue in zip(self.locations, nValues):
            oLocation.direct, oLocation.indirect, oLocation.gridY, oLocation.gridX = nValue
    locations = property(get_locations, set_locations)

class LVSPRecord(LVLRecord):
    def CopyAsOverride(self, targetMod):
        FID = CBash.CopyLVSPRecord(self._CollectionIndex, self._ModName, self._recordID, targetMod._ModName, c_bool(True))
        if(FID): return LVSPRecord(self._CollectionIndex, targetMod._ModName, FID)
        return None
    def CopyAsNew(self, targetMod):
        FID = CBash.CopyLVSPRecord(self._CollectionIndex, self._ModName, self._recordID, targetMod._ModName, c_bool(False))
        if(FID): return LVSPRecord(self._CollectionIndex, targetMod._ModName, FID)
        return None

class ANIORecord(BaseRecord):
    def CopyAsOverride(self, targetMod):
        FID = CBash.CopyANIORecord(self._CollectionIndex, self._ModName, self._recordID, targetMod._ModName, c_bool(True))
        if(FID): return ANIORecord(self._CollectionIndex, targetMod._ModName, FID)
        return None
    def CopyAsNew(self, targetMod):
        FID = CBash.CopyANIORecord(self._CollectionIndex, self._ModName, self._recordID, targetMod._ModName, c_bool(False))
        if(FID): return ANIORecord(self._CollectionIndex, targetMod._ModName, FID)
        return None
    def get_modPath(self):
        CBash.ReadFIDField.restype = c_char_p
        return CBash.ReadFIDField(self._CollectionIndex, self._ModName, self._recordID, 6)
    def set_modPath(self, nValue):
        CBash.SetFIDFieldStr(self._CollectionIndex, self._ModName, self._recordID, 6, nValue)
    modPath = property(get_modPath, set_modPath)
    def get_modb(self):
        CBash.ReadFIDField.restype = POINTER(c_float)
        retValue = CBash.ReadFIDField(self._CollectionIndex, self._ModName, self._recordID, 7)
        if(retValue): return retValue.contents.value
        return None
    def set_modb(self, nValue):
        CBash.SetFIDFieldF(self._CollectionIndex, self._ModName, self._recordID, 7, c_float(nValue))
    modb = property(get_modb, set_modb)
    def get_modt_p(self):
        numRecords = CBash.GetFIDFieldArraySize(self._CollectionIndex, self._ModName, self._recordID, 8)
        if(numRecords > 0):
            cRecords = POINTER(c_ubyte * numRecords)()
            CBash.GetFIDFieldArray(self._CollectionIndex, self._ModName, self._recordID, 8, byref(cRecords))
            return [cRecords.contents[x] for x in range(0, numRecords)]
        return []
    def set_modt_p(self, nValue):
        length = len(nValue)
        CBash.SetFIDFieldR(self._CollectionIndex, self._ModName, self._recordID, 8, struct.pack('B' * length, *nValue), length)
    modt_p = property(get_modt_p, set_modt_p)
    def get_animationId(self):
        CBash.ReadFIDField.restype = POINTER(c_uint)
        retValue = CBash.ReadFIDField(self._CollectionIndex, self._ModName, self._recordID, 9)
        if(retValue): return retValue.contents.value
        return None
    def set_animationId(self, nValue):
        CBash.SetFIDFieldUI(self._CollectionIndex, self._ModName, self._recordID, 9, nValue)
    animationId = property(get_animationId, set_animationId)
class WATRRecord(BaseRecord):
    def CopyAsOverride(self, targetMod):
        FID = CBash.CopyWATRRecord(self._CollectionIndex, self._ModName, self._recordID, targetMod._ModName, c_bool(True))
        if(FID): return WATRRecord(self._CollectionIndex, targetMod._ModName, FID)
        return None
    def CopyAsNew(self, targetMod):
        FID = CBash.CopyWATRRecord(self._CollectionIndex, self._ModName, self._recordID, targetMod._ModName, c_bool(False))
        if(FID): return WATRRecord(self._CollectionIndex, targetMod._ModName, FID)
        return None
    def get_texture(self):
        CBash.ReadFIDField.restype = c_char_p
        return CBash.ReadFIDField(self._CollectionIndex, self._ModName, self._recordID, 6)
    def set_texture(self, nValue):
        CBash.SetFIDFieldStr(self._CollectionIndex, self._ModName, self._recordID, 6, nValue)
    texture = property(get_texture, set_texture)
    def get_opacity(self):
        CBash.ReadFIDField.restype = POINTER(c_ubyte)
        retValue = CBash.ReadFIDField(self._CollectionIndex, self._ModName, self._recordID, 7)
        if(retValue): return retValue.contents.value
        return None
    def set_opacity(self, nValue):
        CBash.SetFIDFieldUC(self._CollectionIndex, self._ModName, self._recordID, 7, c_ubyte(nValue))
    opacity = property(get_opacity, set_opacity)
    def get_flags(self):
        CBash.ReadFIDField.restype = POINTER(c_ubyte)
        retValue = CBash.ReadFIDField(self._CollectionIndex, self._ModName, self._recordID, 8)
        if(retValue): return retValue.contents.value
        return None
    def set_flags(self, nValue):
        CBash.SetFIDFieldUC(self._CollectionIndex, self._ModName, self._recordID, 8, c_ubyte(nValue))
    flags = property(get_flags, set_flags)                    
    def get_material(self):
        CBash.ReadFIDField.restype = c_char_p
        return CBash.ReadFIDField(self._CollectionIndex, self._ModName, self._recordID, 9)
    def set_material(self, nValue):
        CBash.SetFIDFieldStr(self._CollectionIndex, self._ModName, self._recordID, 9, nValue)
    material = property(get_material, set_material)                    
    def get_sound(self):
        CBash.ReadFIDField.restype = POINTER(c_uint)
        retValue = CBash.ReadFIDField(self._CollectionIndex, self._ModName, self._recordID, 10)
        if(retValue): return retValue.contents.value
        return None
    def set_sound(self, nValue):
        CBash.SetFIDFieldUI(self._CollectionIndex, self._ModName, self._recordID, 10, nValue)
    sound = property(get_sound, set_sound)                    
    def get_windVelocity(self):
        CBash.ReadFIDField.restype = POINTER(c_float)
        retValue = CBash.ReadFIDField(self._CollectionIndex, self._ModName, self._recordID, 11)
        if(retValue): return retValue.contents.value
        return None
    def set_windVelocity(self, nValue):
        CBash.SetFIDFieldF(self._CollectionIndex, self._ModName, self._recordID, 11, c_float(nValue))
    windVelocity = property(get_windVelocity, set_windVelocity)
    def get_windDirection(self):
        CBash.ReadFIDField.restype = POINTER(c_float)
        retValue = CBash.ReadFIDField(self._CollectionIndex, self._ModName, self._recordID, 12)
        if(retValue): return retValue.contents.value
        return None
    def set_windDirection(self, nValue):
        CBash.SetFIDFieldF(self._CollectionIndex, self._ModName, self._recordID, 12, c_float(nValue))
    windDirection = property(get_windDirection, set_windDirection)
    def get_waveAmp(self):
        CBash.ReadFIDField.restype = POINTER(c_float)
        retValue = CBash.ReadFIDField(self._CollectionIndex, self._ModName, self._recordID, 13)
        if(retValue): return retValue.contents.value
        return None
    def set_waveAmp(self, nValue):
        CBash.SetFIDFieldF(self._CollectionIndex, self._ModName, self._recordID, 13, c_float(nValue))
    waveAmp = property(get_waveAmp, set_waveAmp)
    def get_waveFreq(self):
        CBash.ReadFIDField.restype = POINTER(c_float)
        retValue = CBash.ReadFIDField(self._CollectionIndex, self._ModName, self._recordID, 14)
        if(retValue): return retValue.contents.value
        return None
    def set_waveFreq(self, nValue):
        CBash.SetFIDFieldF(self._CollectionIndex, self._ModName, self._recordID, 14, c_float(nValue))
    waveFreq = property(get_waveFreq, set_waveFreq)
    def get_sunPower(self):
        CBash.ReadFIDField.restype = POINTER(c_float)
        retValue = CBash.ReadFIDField(self._CollectionIndex, self._ModName, self._recordID, 15)
        if(retValue): return retValue.contents.value
        return None
    def set_sunPower(self, nValue):
        CBash.SetFIDFieldF(self._CollectionIndex, self._ModName, self._recordID, 15, c_float(nValue))
    sunPower = property(get_sunPower, set_sunPower)
    def get_reflectAmt(self):
        CBash.ReadFIDField.restype = POINTER(c_float)
        retValue = CBash.ReadFIDField(self._CollectionIndex, self._ModName, self._recordID, 16)
        if(retValue): return retValue.contents.value
        return None
    def set_reflectAmt(self, nValue):
        CBash.SetFIDFieldF(self._CollectionIndex, self._ModName, self._recordID, 16, c_float(nValue))
    reflectAmt = property(get_reflectAmt, set_reflectAmt)
    def get_fresnelAmt(self):
        CBash.ReadFIDField.restype = POINTER(c_float)
        retValue = CBash.ReadFIDField(self._CollectionIndex, self._ModName, self._recordID, 17)
        if(retValue): return retValue.contents.value
        return None
    def set_fresnelAmt(self, nValue):
        CBash.SetFIDFieldF(self._CollectionIndex, self._ModName, self._recordID, 17, c_float(nValue))
    fresnelAmt = property(get_fresnelAmt, set_fresnelAmt)
    def get_xSpeed(self):
        CBash.ReadFIDField.restype = POINTER(c_float)
        retValue = CBash.ReadFIDField(self._CollectionIndex, self._ModName, self._recordID, 18)
        if(retValue): return retValue.contents.value
        return None
    def set_xSpeed(self, nValue):
        CBash.SetFIDFieldF(self._CollectionIndex, self._ModName, self._recordID, 18, c_float(nValue))
    xSpeed = property(get_xSpeed, set_xSpeed)
    def get_ySpeed(self):
        CBash.ReadFIDField.restype = POINTER(c_float)
        retValue = CBash.ReadFIDField(self._CollectionIndex, self._ModName, self._recordID, 19)
        if(retValue): return retValue.contents.value
        return None
    def set_ySpeed(self, nValue):
        CBash.SetFIDFieldF(self._CollectionIndex, self._ModName, self._recordID, 19, c_float(nValue))
    ySpeed = property(get_ySpeed, set_ySpeed)
    def get_fogNear(self):
        CBash.ReadFIDField.restype = POINTER(c_float)
        retValue = CBash.ReadFIDField(self._CollectionIndex, self._ModName, self._recordID, 20)
        if(retValue): return retValue.contents.value
        return None
    def set_fogNear(self, nValue):
        CBash.SetFIDFieldF(self._CollectionIndex, self._ModName, self._recordID, 20, c_float(nValue))
    fogNear = property(get_fogNear, set_fogNear)
    def get_fogFar(self):
        CBash.ReadFIDField.restype = POINTER(c_float)
        retValue = CBash.ReadFIDField(self._CollectionIndex, self._ModName, self._recordID, 21)
        if(retValue): return retValue.contents.value
        return None
    def set_fogFar(self, nValue):
        CBash.SetFIDFieldF(self._CollectionIndex, self._ModName, self._recordID, 21, c_float(nValue))
    fogFar = property(get_fogFar, set_fogFar)
    def get_shallowRed(self):
        CBash.ReadFIDField.restype = POINTER(c_ubyte)
        retValue = CBash.ReadFIDField(self._CollectionIndex, self._ModName, self._recordID, 22)
        if(retValue): return retValue.contents.value
        return None
    def set_shallowRed(self, nValue):
        CBash.SetFIDFieldUC(self._CollectionIndex, self._ModName, self._recordID, 22, c_ubyte(nValue))
    shallowRed = property(get_shallowRed, set_shallowRed)
    def get_shallowGreen(self):
        CBash.ReadFIDField.restype = POINTER(c_ubyte)
        retValue = CBash.ReadFIDField(self._CollectionIndex, self._ModName, self._recordID, 23)
        if(retValue): return retValue.contents.value
        return None
    def set_shallowGreen(self, nValue):
        CBash.SetFIDFieldUC(self._CollectionIndex, self._ModName, self._recordID, 23, c_ubyte(nValue))
    shallowGreen = property(get_shallowGreen, set_shallowGreen)
    def get_shallowBlue(self):
        CBash.ReadFIDField.restype = POINTER(c_ubyte)
        retValue = CBash.ReadFIDField(self._CollectionIndex, self._ModName, self._recordID, 24)
        if(retValue): return retValue.contents.value
        return None
    def set_shallowBlue(self, nValue):
        CBash.SetFIDFieldUC(self._CollectionIndex, self._ModName, self._recordID, 24, c_ubyte(nValue))
    shallowBlue = property(get_shallowBlue, set_shallowBlue)
    def get_unused1(self):
        numRecords = CBash.GetFIDFieldArraySize(self._CollectionIndex, self._ModName, self._recordID, 25)
        if(numRecords > 0):
            cRecords = POINTER(c_ubyte * numRecords)()
            CBash.GetFIDFieldArray(self._CollectionIndex, self._ModName, self._recordID, 25, byref(cRecords))
            return [cRecords.contents[x] for x in range(0, numRecords)]
        return []
    def set_unused1(self, nValue):
        CBash.SetFIDFieldR(self._CollectionIndex, self._ModName, self._recordID, 25, struct.pack('B', *nValue), 1)
    unused1 = property(get_unused1, set_unused1)
    def get_deepRed(self):
        CBash.ReadFIDField.restype = POINTER(c_ubyte)
        retValue = CBash.ReadFIDField(self._CollectionIndex, self._ModName, self._recordID, 26)
        if(retValue): return retValue.contents.value
        return None
    def set_deepRed(self, nValue):
        CBash.SetFIDFieldUC(self._CollectionIndex, self._ModName, self._recordID, 26, c_ubyte(nValue))
    deepRed = property(get_deepRed, set_deepRed)
    def get_deepGreen(self):
        CBash.ReadFIDField.restype = POINTER(c_ubyte)
        retValue = CBash.ReadFIDField(self._CollectionIndex, self._ModName, self._recordID, 27)
        if(retValue): return retValue.contents.value
        return None
    def set_deepGreen(self, nValue):
        CBash.SetFIDFieldUC(self._CollectionIndex, self._ModName, self._recordID, 27, c_ubyte(nValue))
    deepGreen = property(get_deepGreen, set_deepGreen)
    def get_deepBlue(self):
        CBash.ReadFIDField.restype = POINTER(c_ubyte)
        retValue = CBash.ReadFIDField(self._CollectionIndex, self._ModName, self._recordID, 28)
        if(retValue): return retValue.contents.value
        return None
    def set_deepBlue(self, nValue):
        CBash.SetFIDFieldUC(self._CollectionIndex, self._ModName, self._recordID, 28, c_ubyte(nValue))
    deepBlue = property(get_deepBlue, set_deepBlue)
    def get_unused2(self):
        numRecords = CBash.GetFIDFieldArraySize(self._CollectionIndex, self._ModName, self._recordID, 29)
        if(numRecords > 0):
            cRecords = POINTER(c_ubyte * numRecords)()
            CBash.GetFIDFieldArray(self._CollectionIndex, self._ModName, self._recordID, 29, byref(cRecords))
            return [cRecords.contents[x] for x in range(0, numRecords)]
        return []
    def set_unused2(self, nValue):
        CBash.SetFIDFieldR(self._CollectionIndex, self._ModName, self._recordID, 29, struct.pack('B', *nValue), 1)
    unused2 = property(get_unused2, set_unused2)
    def get_reflRed(self):
        CBash.ReadFIDField.restype = POINTER(c_ubyte)
        retValue = CBash.ReadFIDField(self._CollectionIndex, self._ModName, self._recordID, 30)
        if(retValue): return retValue.contents.value
        return None
    def set_reflRed(self, nValue):
        CBash.SetFIDFieldUC(self._CollectionIndex, self._ModName, self._recordID, 30, c_ubyte(nValue))
    reflRed = property(get_reflRed, set_reflRed)
    def get_reflGreen(self):
        CBash.ReadFIDField.restype = POINTER(c_ubyte)
        retValue = CBash.ReadFIDField(self._CollectionIndex, self._ModName, self._recordID, 31)
        if(retValue): return retValue.contents.value
        return None
    def set_reflGreen(self, nValue):
        CBash.SetFIDFieldUC(self._CollectionIndex, self._ModName, self._recordID, 31, c_ubyte(nValue))
    reflGreen = property(get_reflGreen, set_reflGreen)
    def get_reflBlue(self):
        CBash.ReadFIDField.restype = POINTER(c_ubyte)
        retValue = CBash.ReadFIDField(self._CollectionIndex, self._ModName, self._recordID, 32)
        if(retValue): return retValue.contents.value
        return None
    def set_reflBlue(self, nValue):
        CBash.SetFIDFieldUC(self._CollectionIndex, self._ModName, self._recordID, 32, c_ubyte(nValue))
    reflBlue = property(get_reflBlue, set_reflBlue)                    
    def get_unused3(self):
        numRecords = CBash.GetFIDFieldArraySize(self._CollectionIndex, self._ModName, self._recordID, 33)
        if(numRecords > 0):
            cRecords = POINTER(c_ubyte * numRecords)()
            CBash.GetFIDFieldArray(self._CollectionIndex, self._ModName, self._recordID, 33, byref(cRecords))
            return [cRecords.contents[x] for x in range(0, numRecords)]
        return []
    def set_unused3(self, nValue):
        CBash.SetFIDFieldR(self._CollectionIndex, self._ModName, self._recordID, 33, struct.pack('B', *nValue), 1)
    unused3 = property(get_unused3, set_unused3)
    def get_blend(self):
        CBash.ReadFIDField.restype = POINTER(c_ubyte)
        retValue = CBash.ReadFIDField(self._CollectionIndex, self._ModName, self._recordID, 34)
        if(retValue): return retValue.contents.value
        return None
    def set_blend(self, nValue):
        CBash.SetFIDFieldUC(self._CollectionIndex, self._ModName, self._recordID, 34, c_ubyte(nValue))
    blend = property(get_blend, set_blend)
    def get_unused4(self):
        numRecords = CBash.GetFIDFieldArraySize(self._CollectionIndex, self._ModName, self._recordID, 35)
        if(numRecords > 0):
            cRecords = POINTER(c_ubyte * numRecords)()
            CBash.GetFIDFieldArray(self._CollectionIndex, self._ModName, self._recordID, 35, byref(cRecords))
            return [cRecords.contents[x] for x in range(0, numRecords)]
        return []
    def set_unused4(self, nValue):
        CBash.SetFIDFieldR(self._CollectionIndex, self._ModName, self._recordID, 35, struct.pack('3B', *nValue), 3)
    unused4 = property(get_unused4, set_unused4)
    def get_rainForce(self):
        CBash.ReadFIDField.restype = POINTER(c_float)
        retValue = CBash.ReadFIDField(self._CollectionIndex, self._ModName, self._recordID, 36)
        if(retValue): return retValue.contents.value
        return None
    def set_rainForce(self, nValue):
        CBash.SetFIDFieldF(self._CollectionIndex, self._ModName, self._recordID, 36, c_float(nValue))
    rainForce = property(get_rainForce, set_rainForce)
    def get_rainVelocity(self):
        CBash.ReadFIDField.restype = POINTER(c_float)
        retValue = CBash.ReadFIDField(self._CollectionIndex, self._ModName, self._recordID, 37)
        if(retValue): return retValue.contents.value
        return None
    def set_rainVelocity(self, nValue):
        CBash.SetFIDFieldF(self._CollectionIndex, self._ModName, self._recordID, 37, c_float(nValue))
    rainVelocity = property(get_rainVelocity, set_rainVelocity)
    def get_rainFalloff(self):
        CBash.ReadFIDField.restype = POINTER(c_float)
        retValue = CBash.ReadFIDField(self._CollectionIndex, self._ModName, self._recordID, 38)
        if(retValue): return retValue.contents.value
        return None
    def set_rainFalloff(self, nValue):
        CBash.SetFIDFieldF(self._CollectionIndex, self._ModName, self._recordID, 38, c_float(nValue))
    rainFalloff = property(get_rainFalloff, set_rainFalloff)
    def get_rainDampner(self):
        CBash.ReadFIDField.restype = POINTER(c_float)
        retValue = CBash.ReadFIDField(self._CollectionIndex, self._ModName, self._recordID, 39)
        if(retValue): return retValue.contents.value
        return None
    def set_rainDampner(self, nValue):
        CBash.SetFIDFieldF(self._CollectionIndex, self._ModName, self._recordID, 39, c_float(nValue))
    rainDampner = property(get_rainDampner, set_rainDampner)
    def get_rainSize(self):
        CBash.ReadFIDField.restype = POINTER(c_float)
        retValue = CBash.ReadFIDField(self._CollectionIndex, self._ModName, self._recordID, 40)
        if(retValue): return retValue.contents.value
        return None
    def set_rainSize(self, nValue):
        CBash.SetFIDFieldF(self._CollectionIndex, self._ModName, self._recordID, 40, c_float(nValue))
    rainSize = property(get_rainSize, set_rainSize)
    def get_dispForce(self):
        CBash.ReadFIDField.restype = POINTER(c_float)
        retValue = CBash.ReadFIDField(self._CollectionIndex, self._ModName, self._recordID, 41)
        if(retValue): return retValue.contents.value
        return None
    def set_dispForce(self, nValue):
        CBash.SetFIDFieldF(self._CollectionIndex, self._ModName, self._recordID, 41, c_float(nValue))
    dispForce = property(get_dispForce, set_dispForce)
    def get_dispVelocity(self):
        CBash.ReadFIDField.restype = POINTER(c_float)
        retValue = CBash.ReadFIDField(self._CollectionIndex, self._ModName, self._recordID, 42)
        if(retValue): return retValue.contents.value
        return None
    def set_dispVelocity(self, nValue):
        CBash.SetFIDFieldF(self._CollectionIndex, self._ModName, self._recordID, 42, c_float(nValue))
    dispVelocity = property(get_dispVelocity, set_dispVelocity)
    def get_dispFalloff(self):
        CBash.ReadFIDField.restype = POINTER(c_float)
        retValue = CBash.ReadFIDField(self._CollectionIndex, self._ModName, self._recordID, 43)
        if(retValue): return retValue.contents.value
        return None
    def set_dispFalloff(self, nValue):
        CBash.SetFIDFieldF(self._CollectionIndex, self._ModName, self._recordID, 43, c_float(nValue))
    dispFalloff = property(get_dispFalloff, set_dispFalloff)
    def get_dispDampner(self):
        CBash.ReadFIDField.restype = POINTER(c_float)
        retValue = CBash.ReadFIDField(self._CollectionIndex, self._ModName, self._recordID, 44)
        if(retValue): return retValue.contents.value
        return None
    def set_dispDampner(self, nValue):
        CBash.SetFIDFieldF(self._CollectionIndex, self._ModName, self._recordID, 44, c_float(nValue))
    dispDampner = property(get_dispDampner, set_dispDampner)
    def get_dispSize(self):
        CBash.ReadFIDField.restype = POINTER(c_float)
        retValue = CBash.ReadFIDField(self._CollectionIndex, self._ModName, self._recordID, 45)
        if(retValue): return retValue.contents.value
        return None
    def set_dispSize(self, nValue):
        CBash.SetFIDFieldF(self._CollectionIndex, self._ModName, self._recordID, 45, c_float(nValue))
    dispSize = property(get_dispSize, set_dispSize)
    def get_damage(self):
        CBash.ReadFIDField.restype = POINTER(c_ushort)
        retValue = CBash.ReadFIDField(self._CollectionIndex, self._ModName, self._recordID, 46)
        if(retValue): return retValue.contents.value
        return None
    def set_damage(self, nValue):
        CBash.SetFIDFieldUS(self._CollectionIndex, self._ModName, self._recordID, 46, c_ushort(nValue))
    damage = property(get_damage, set_damage)                    
    def get_dayWater(self):
        CBash.ReadFIDField.restype = POINTER(c_uint)
        retValue = CBash.ReadFIDField(self._CollectionIndex, self._ModName, self._recordID, 47)
        if(retValue): return retValue.contents.value
        return None
    def set_dayWater(self, nValue):
        CBash.SetFIDFieldUI(self._CollectionIndex, self._ModName, self._recordID, 47, nValue)
    dayWater = property(get_dayWater, set_dayWater)
    def get_nightWater(self):
        CBash.ReadFIDField.restype = POINTER(c_uint)
        retValue = CBash.ReadFIDField(self._CollectionIndex, self._ModName, self._recordID, 48)
        if(retValue): return retValue.contents.value
        return None
    def set_nightWater(self, nValue):
        CBash.SetFIDFieldUI(self._CollectionIndex, self._ModName, self._recordID, 48, nValue)
    nightWater = property(get_nightWater, set_nightWater)
    def get_underWater(self):
        CBash.ReadFIDField.restype = POINTER(c_uint)
        retValue = CBash.ReadFIDField(self._CollectionIndex, self._ModName, self._recordID, 49)
        if(retValue): return retValue.contents.value
        return None
    def set_underWater(self, nValue):
        CBash.SetFIDFieldUI(self._CollectionIndex, self._ModName, self._recordID, 49, nValue)
    underWater = property(get_underWater, set_underWater)   
    def get_IsCausesDamage(self):
        return (self.flags & 0x00000001) != 0
    def set_IsCausesDamage(self, nValue):
        if (nValue == True): self.flags |= 0x00000001
        else: self.flags &= ~0x00000001
    IsCausesDmg = IsCausesDamage = property(get_IsCausesDamage, set_IsCausesDamage)
    def get_IsReflective(self):
        return (self.flags & 0x00000002) != 0
    def set_IsReflective(self, nValue):
        if (nValue == True): self.flags |= 0x00000002
        else: self.flags &= ~0x00000002
    IsReflective = property(get_IsReflective, set_IsReflective)
    
class EFSHRecord(BaseRecord):
    def CopyAsOverride(self, targetMod):
        FID = CBash.CopyEFSHRecord(self._CollectionIndex, self._ModName, self._recordID, targetMod._ModName, c_bool(True))
        if(FID): return EFSHRecord(self._CollectionIndex, targetMod._ModName, FID)
        return None
    def CopyAsNew(self, targetMod):
        FID = CBash.CopyEFSHRecord(self._CollectionIndex, self._ModName, self._recordID, targetMod._ModName, c_bool(False))
        if(FID): return EFSHRecord(self._CollectionIndex, targetMod._ModName, FID)
        return None
    def get_fillTexture(self):
        CBash.ReadFIDField.restype = c_char_p
        return CBash.ReadFIDField(self._CollectionIndex, self._ModName, self._recordID, 6)
    def set_fillTexture(self, nValue):
        CBash.SetFIDFieldStr(self._CollectionIndex, self._ModName, self._recordID, 6, nValue)
    fillTexture = property(get_fillTexture, set_fillTexture)
    def get_particleTexture(self):
        CBash.ReadFIDField.restype = c_char_p
        return CBash.ReadFIDField(self._CollectionIndex, self._ModName, self._recordID, 7)
    def set_particleTexture(self, nValue):
        CBash.SetFIDFieldStr(self._CollectionIndex, self._ModName, self._recordID, 7, nValue)
    particleTexture = property(get_particleTexture, set_particleTexture)
    def get_flags(self):
        CBash.ReadFIDField.restype = POINTER(c_ubyte)
        retValue = CBash.ReadFIDField(self._CollectionIndex, self._ModName, self._recordID, 8)
        if(retValue): return retValue.contents.value
        return None
    def set_flags(self, nValue):
        CBash.SetFIDFieldUC(self._CollectionIndex, self._ModName, self._recordID, 8, c_ubyte(nValue))
    flags = property(get_flags, set_flags)
    def get_unused1(self):
        numRecords = CBash.GetFIDFieldArraySize(self._CollectionIndex, self._ModName, self._recordID, 9)
        if(numRecords > 0):
            cRecords = POINTER(c_ubyte * numRecords)()
            CBash.GetFIDFieldArray(self._CollectionIndex, self._ModName, self._recordID, 9, byref(cRecords))
            return [cRecords.contents[x] for x in range(0, numRecords)]
        return []
    def set_unused1(self, nValue):
        CBash.SetFIDFieldR(self._CollectionIndex, self._ModName, self._recordID, 9, struct.pack('3B', *nValue), 3)
    unused1 = property(get_unused1, set_unused1)
    def get_memSBlend(self):
        CBash.ReadFIDField.restype = POINTER(c_uint)
        retValue = CBash.ReadFIDField(self._CollectionIndex, self._ModName, self._recordID, 10)
        if(retValue): return retValue.contents.value
        return None
    def set_memSBlend(self, nValue):
        CBash.SetFIDFieldUI(self._CollectionIndex, self._ModName, self._recordID, 10, nValue)
    memSBlend = property(get_memSBlend, set_memSBlend)
    def get_memBlendOp(self):
        CBash.ReadFIDField.restype = POINTER(c_uint)
        retValue = CBash.ReadFIDField(self._CollectionIndex, self._ModName, self._recordID, 11)
        if(retValue): return retValue.contents.value
        return None
    def set_memBlendOp(self, nValue):
        CBash.SetFIDFieldUI(self._CollectionIndex, self._ModName, self._recordID, 11, nValue)
    memBlendOp = property(get_memBlendOp, set_memBlendOp)
    def get_memZFunc(self):
        CBash.ReadFIDField.restype = POINTER(c_uint)
        retValue = CBash.ReadFIDField(self._CollectionIndex, self._ModName, self._recordID, 12)
        if(retValue): return retValue.contents.value
        return None
    def set_memZFunc(self, nValue):
        CBash.SetFIDFieldUI(self._CollectionIndex, self._ModName, self._recordID, 12, nValue)
    memZFunc = property(get_memZFunc, set_memZFunc)
    def get_fillRed(self):
        CBash.ReadFIDField.restype = POINTER(c_ubyte)
        retValue = CBash.ReadFIDField(self._CollectionIndex, self._ModName, self._recordID, 13)
        if(retValue): return retValue.contents.value
        return None
    def set_fillRed(self, nValue):
        CBash.SetFIDFieldUC(self._CollectionIndex, self._ModName, self._recordID, 13, c_ubyte(nValue))
    fillRed = property(get_fillRed, set_fillRed)
    def get_fillGreen(self):
        CBash.ReadFIDField.restype = POINTER(c_ubyte)
        retValue = CBash.ReadFIDField(self._CollectionIndex, self._ModName, self._recordID, 14)
        if(retValue): return retValue.contents.value
        return None
    def set_fillGreen(self, nValue):
        CBash.SetFIDFieldUC(self._CollectionIndex, self._ModName, self._recordID, 14, c_ubyte(nValue))
    fillGreen = property(get_fillGreen, set_fillGreen)
    def get_fillBlue(self):
        CBash.ReadFIDField.restype = POINTER(c_ubyte)
        retValue = CBash.ReadFIDField(self._CollectionIndex, self._ModName, self._recordID, 15)
        if(retValue): return retValue.contents.value
        return None
    def set_fillBlue(self, nValue):
        CBash.SetFIDFieldUC(self._CollectionIndex, self._ModName, self._recordID, 15, c_ubyte(nValue))
    fillBlue = property(get_fillBlue, set_fillBlue)
    def get_unused2(self):
        numRecords = CBash.GetFIDFieldArraySize(self._CollectionIndex, self._ModName, self._recordID, 16)
        if(numRecords > 0):
            cRecords = POINTER(c_ubyte * numRecords)()
            CBash.GetFIDFieldArray(self._CollectionIndex, self._ModName, self._recordID, 16, byref(cRecords))
            return [cRecords.contents[x] for x in range(0, numRecords)]
        return []
    def set_unused2(self, nValue):
        CBash.SetFIDFieldR(self._CollectionIndex, self._ModName, self._recordID, 16, struct.pack('B', *nValue), 1)
    unused2 = property(get_unused2, set_unused2)
    def get_fillAIn(self):
        CBash.ReadFIDField.restype = POINTER(c_float)
        retValue = CBash.ReadFIDField(self._CollectionIndex, self._ModName, self._recordID, 17)
        if(retValue): return retValue.contents.value
        return None
    def set_fillAIn(self, nValue):
        CBash.SetFIDFieldF(self._CollectionIndex, self._ModName, self._recordID, 17, c_float(nValue))
    fillAIn = property(get_fillAIn, set_fillAIn)
    def get_fillAFull(self):
        CBash.ReadFIDField.restype = POINTER(c_float)
        retValue = CBash.ReadFIDField(self._CollectionIndex, self._ModName, self._recordID, 18)
        if(retValue): return retValue.contents.value
        return None
    def set_fillAFull(self, nValue):
        CBash.SetFIDFieldF(self._CollectionIndex, self._ModName, self._recordID, 18, c_float(nValue))
    fillAFull = property(get_fillAFull, set_fillAFull)
    def get_fillAOut(self):
        CBash.ReadFIDField.restype = POINTER(c_float)
        retValue = CBash.ReadFIDField(self._CollectionIndex, self._ModName, self._recordID, 19)
        if(retValue): return retValue.contents.value
        return None
    def set_fillAOut(self, nValue):
        CBash.SetFIDFieldF(self._CollectionIndex, self._ModName, self._recordID, 19, c_float(nValue))
    fillAOut = property(get_fillAOut, set_fillAOut)
    def get_fillAPRatio(self):
        CBash.ReadFIDField.restype = POINTER(c_float)
        retValue = CBash.ReadFIDField(self._CollectionIndex, self._ModName, self._recordID, 20)
        if(retValue): return retValue.contents.value
        return None
    def set_fillAPRatio(self, nValue):
        CBash.SetFIDFieldF(self._CollectionIndex, self._ModName, self._recordID, 20, c_float(nValue))
    fillAPRatio = property(get_fillAPRatio, set_fillAPRatio)
    def get_fillAAmp(self):
        CBash.ReadFIDField.restype = POINTER(c_float)
        retValue = CBash.ReadFIDField(self._CollectionIndex, self._ModName, self._recordID, 21)
        if(retValue): return retValue.contents.value
        return None
    def set_fillAAmp(self, nValue):
        CBash.SetFIDFieldF(self._CollectionIndex, self._ModName, self._recordID, 21, c_float(nValue))
    fillAAmp = property(get_fillAAmp, set_fillAAmp)
    def get_fillAFreq(self):
        CBash.ReadFIDField.restype = POINTER(c_float)
        retValue = CBash.ReadFIDField(self._CollectionIndex, self._ModName, self._recordID, 22)
        if(retValue): return retValue.contents.value
        return None
    def set_fillAFreq(self, nValue):
        CBash.SetFIDFieldF(self._CollectionIndex, self._ModName, self._recordID, 22, c_float(nValue))
    fillAFreq = property(get_fillAFreq, set_fillAFreq)
    def get_fillAnimSpdU(self):
        CBash.ReadFIDField.restype = POINTER(c_float)
        retValue = CBash.ReadFIDField(self._CollectionIndex, self._ModName, self._recordID, 23)
        if(retValue): return retValue.contents.value
        return None
    def set_fillAnimSpdU(self, nValue):
        CBash.SetFIDFieldF(self._CollectionIndex, self._ModName, self._recordID, 23, c_float(nValue))
    fillAnimSpdU = property(get_fillAnimSpdU, set_fillAnimSpdU)
    def get_fillAnimSpdV(self):
        CBash.ReadFIDField.restype = POINTER(c_float)
        retValue = CBash.ReadFIDField(self._CollectionIndex, self._ModName, self._recordID, 24)
        if(retValue): return retValue.contents.value
        return None
    def set_fillAnimSpdV(self, nValue):
        CBash.SetFIDFieldF(self._CollectionIndex, self._ModName, self._recordID, 24, c_float(nValue))
    fillAnimSpdV = property(get_fillAnimSpdV, set_fillAnimSpdV)
    def get_edgeOff(self):
        CBash.ReadFIDField.restype = POINTER(c_float)
        retValue = CBash.ReadFIDField(self._CollectionIndex, self._ModName, self._recordID, 25)
        if(retValue): return retValue.contents.value
        return None
    def set_edgeOff(self, nValue):
        CBash.SetFIDFieldF(self._CollectionIndex, self._ModName, self._recordID, 25, c_float(nValue))
    edgeOff = property(get_edgeOff, set_edgeOff)
    def get_edgeRed(self):
        CBash.ReadFIDField.restype = POINTER(c_ubyte)
        retValue = CBash.ReadFIDField(self._CollectionIndex, self._ModName, self._recordID, 26)
        if(retValue): return retValue.contents.value
        return None
    def set_edgeRed(self, nValue):
        CBash.SetFIDFieldUC(self._CollectionIndex, self._ModName, self._recordID, 26, c_ubyte(nValue))
    edgeRed = property(get_edgeRed, set_edgeRed)
    def get_edgeGreen(self):
        CBash.ReadFIDField.restype = POINTER(c_ubyte)
        retValue = CBash.ReadFIDField(self._CollectionIndex, self._ModName, self._recordID, 27)
        if(retValue): return retValue.contents.value
        return None
    def set_edgeGreen(self, nValue):
        CBash.SetFIDFieldUC(self._CollectionIndex, self._ModName, self._recordID, 27, c_ubyte(nValue))
    edgeGreen = property(get_edgeGreen, set_edgeGreen)
    def get_edgeBlue(self):
        CBash.ReadFIDField.restype = POINTER(c_ubyte)
        retValue = CBash.ReadFIDField(self._CollectionIndex, self._ModName, self._recordID, 28)
        if(retValue): return retValue.contents.value
        return None
    def set_edgeBlue(self, nValue):
        CBash.SetFIDFieldUC(self._CollectionIndex, self._ModName, self._recordID, 28, c_ubyte(nValue))
    edgeBlue = property(get_edgeBlue, set_edgeBlue)
    def get_unused3(self):
        numRecords = CBash.GetFIDFieldArraySize(self._CollectionIndex, self._ModName, self._recordID, 29)
        if(numRecords > 0):
            cRecords = POINTER(c_ubyte * numRecords)()
            CBash.GetFIDFieldArray(self._CollectionIndex, self._ModName, self._recordID, 29, byref(cRecords))
            return [cRecords.contents[x] for x in range(0, numRecords)]
        return []
    def set_unused3(self, nValue):
        CBash.SetFIDFieldR(self._CollectionIndex, self._ModName, self._recordID, 29, struct.pack('B', *nValue), 1)
    unused3 = property(get_unused3, set_unused3)
    def get_edgeAIn(self):
        CBash.ReadFIDField.restype = POINTER(c_float)
        retValue = CBash.ReadFIDField(self._CollectionIndex, self._ModName, self._recordID, 30)
        if(retValue): return retValue.contents.value
        return None
    def set_edgeAIn(self, nValue):
        CBash.SetFIDFieldF(self._CollectionIndex, self._ModName, self._recordID, 30, c_float(nValue))
    edgeAIn = property(get_edgeAIn, set_edgeAIn)
    def get_edgeAFull(self):
        CBash.ReadFIDField.restype = POINTER(c_float)
        retValue = CBash.ReadFIDField(self._CollectionIndex, self._ModName, self._recordID, 31)
        if(retValue): return retValue.contents.value
        return None
    def set_edgeAFull(self, nValue):
        CBash.SetFIDFieldF(self._CollectionIndex, self._ModName, self._recordID, 31, c_float(nValue))
    edgeAFull = property(get_edgeAFull, set_edgeAFull)
    def get_edgeAOut(self):
        CBash.ReadFIDField.restype = POINTER(c_float)
        retValue = CBash.ReadFIDField(self._CollectionIndex, self._ModName, self._recordID, 32)
        if(retValue): return retValue.contents.value
        return None
    def set_edgeAOut(self, nValue):
        CBash.SetFIDFieldF(self._CollectionIndex, self._ModName, self._recordID, 32, c_float(nValue))
    edgeAOut = property(get_edgeAOut, set_edgeAOut)
    def get_edgeAPRatio(self):
        CBash.ReadFIDField.restype = POINTER(c_float)
        retValue = CBash.ReadFIDField(self._CollectionIndex, self._ModName, self._recordID, 33)
        if(retValue): return retValue.contents.value
        return None
    def set_edgeAPRatio(self, nValue):
        CBash.SetFIDFieldF(self._CollectionIndex, self._ModName, self._recordID, 33, c_float(nValue))
    edgeAPRatio = property(get_edgeAPRatio, set_edgeAPRatio)
    def get_edgeAAmp(self):
        CBash.ReadFIDField.restype = POINTER(c_float)
        retValue = CBash.ReadFIDField(self._CollectionIndex, self._ModName, self._recordID, 34)
        if(retValue): return retValue.contents.value
        return None
    def set_edgeAAmp(self, nValue):
        CBash.SetFIDFieldF(self._CollectionIndex, self._ModName, self._recordID, 34, c_float(nValue))
    edgeAAmp = property(get_edgeAAmp, set_edgeAAmp)
    def get_edgeAFreq(self):
        CBash.ReadFIDField.restype = POINTER(c_float)
        retValue = CBash.ReadFIDField(self._CollectionIndex, self._ModName, self._recordID, 35)
        if(retValue): return retValue.contents.value
        return None
    def set_edgeAFreq(self, nValue):
        CBash.SetFIDFieldF(self._CollectionIndex, self._ModName, self._recordID, 35, c_float(nValue))
    edgeAFreq = property(get_edgeAFreq, set_edgeAFreq)
    def get_fillAFRatio(self):
        CBash.ReadFIDField.restype = POINTER(c_float)
        retValue = CBash.ReadFIDField(self._CollectionIndex, self._ModName, self._recordID, 36)
        if(retValue): return retValue.contents.value
        return None
    def set_fillAFRatio(self, nValue):
        CBash.SetFIDFieldF(self._CollectionIndex, self._ModName, self._recordID, 36, c_float(nValue))
    fillAFRatio = property(get_fillAFRatio, set_fillAFRatio)
    def get_edgeAFRatio(self):
        CBash.ReadFIDField.restype = POINTER(c_float)
        retValue = CBash.ReadFIDField(self._CollectionIndex, self._ModName, self._recordID, 37)
        if(retValue): return retValue.contents.value
        return None
    def set_edgeAFRatio(self, nValue):
        CBash.SetFIDFieldF(self._CollectionIndex, self._ModName, self._recordID, 37, c_float(nValue))
    edgeAFRatio = property(get_edgeAFRatio, set_edgeAFRatio)
    def get_memDBlend(self):
        CBash.ReadFIDField.restype = POINTER(c_ubyte)
        retValue = CBash.ReadFIDField(self._CollectionIndex, self._ModName, self._recordID, 38)
        if(retValue): return retValue.contents.value
        return None
    def set_memDBlend(self, nValue):
        CBash.SetFIDFieldUC(self._CollectionIndex, self._ModName, self._recordID, 38, c_ubyte(nValue))
    memDBlend = property(get_memDBlend, set_memDBlend)
    def get_partSBlend(self):
        CBash.ReadFIDField.restype = POINTER(c_ubyte)
        retValue = CBash.ReadFIDField(self._CollectionIndex, self._ModName, self._recordID, 39)
        if(retValue): return retValue.contents.value
        return None
    def set_partSBlend(self, nValue):
        CBash.SetFIDFieldUC(self._CollectionIndex, self._ModName, self._recordID, 39, c_ubyte(nValue))
    partSBlend = property(get_partSBlend, set_partSBlend)
    def get_partBlendOp(self):
        CBash.ReadFIDField.restype = POINTER(c_ubyte)
        retValue = CBash.ReadFIDField(self._CollectionIndex, self._ModName, self._recordID, 40)
        if(retValue): return retValue.contents.value
        return None
    def set_partBlendOp(self, nValue):
        CBash.SetFIDFieldUC(self._CollectionIndex, self._ModName, self._recordID, 40, c_ubyte(nValue))
    partBlendOp = property(get_partBlendOp, set_partBlendOp)
    def get_partZFunc(self):
        CBash.ReadFIDField.restype = POINTER(c_ubyte)
        retValue = CBash.ReadFIDField(self._CollectionIndex, self._ModName, self._recordID, 41)
        if(retValue): return retValue.contents.value
        return None
    def set_partZFunc(self, nValue):
        CBash.SetFIDFieldUC(self._CollectionIndex, self._ModName, self._recordID, 41, c_ubyte(nValue))
    partZFunc = property(get_partZFunc, set_partZFunc)
    def get_partDBlend(self):
        CBash.ReadFIDField.restype = POINTER(c_ubyte)
        retValue = CBash.ReadFIDField(self._CollectionIndex, self._ModName, self._recordID, 42)
        if(retValue): return retValue.contents.value
        return None
    def set_partDBlend(self, nValue):
        CBash.SetFIDFieldUC(self._CollectionIndex, self._ModName, self._recordID, 42, c_ubyte(nValue))
    partDBlend = property(get_partDBlend, set_partDBlend)
    def get_partBUp(self):
        CBash.ReadFIDField.restype = POINTER(c_float)
        retValue = CBash.ReadFIDField(self._CollectionIndex, self._ModName, self._recordID, 43)
        if(retValue): return retValue.contents.value
        return None
    def set_partBUp(self, nValue):
        CBash.SetFIDFieldF(self._CollectionIndex, self._ModName, self._recordID, 43, c_float(nValue))
    partBUp = property(get_partBUp, set_partBUp)
    def get_partBFull(self):
        CBash.ReadFIDField.restype = POINTER(c_float)
        retValue = CBash.ReadFIDField(self._CollectionIndex, self._ModName, self._recordID, 44)
        if(retValue): return retValue.contents.value
        return None
    def set_partBFull(self, nValue):
        CBash.SetFIDFieldF(self._CollectionIndex, self._ModName, self._recordID, 44, c_float(nValue))
    partBFull = property(get_partBFull, set_partBFull)
    def get_partBDown(self):
        CBash.ReadFIDField.restype = POINTER(c_float)
        retValue = CBash.ReadFIDField(self._CollectionIndex, self._ModName, self._recordID, 45)
        if(retValue): return retValue.contents.value
        return None
    def set_partBDown(self, nValue):
        CBash.SetFIDFieldF(self._CollectionIndex, self._ModName, self._recordID, 45, c_float(nValue))
    partBDown = property(get_partBDown, set_partBDown)
    def get_partBFRatio(self):
        CBash.ReadFIDField.restype = POINTER(c_float)
        retValue = CBash.ReadFIDField(self._CollectionIndex, self._ModName, self._recordID, 46)
        if(retValue): return retValue.contents.value
        return None
    def set_partBFRatio(self, nValue):
        CBash.SetFIDFieldF(self._CollectionIndex, self._ModName, self._recordID, 46, c_float(nValue))
    partBFRatio = property(get_partBFRatio, set_partBFRatio)
    def get_partBPRatio(self):
        CBash.ReadFIDField.restype = POINTER(c_float)
        retValue = CBash.ReadFIDField(self._CollectionIndex, self._ModName, self._recordID, 47)
        if(retValue): return retValue.contents.value
        return None
    def set_partBPRatio(self, nValue):
        CBash.SetFIDFieldF(self._CollectionIndex, self._ModName, self._recordID, 47, c_float(nValue))
    partBPRatio = property(get_partBPRatio, set_partBPRatio)
    def get_partLTime(self):
        CBash.ReadFIDField.restype = POINTER(c_float)
        retValue = CBash.ReadFIDField(self._CollectionIndex, self._ModName, self._recordID, 48)
        if(retValue): return retValue.contents.value
        return None
    def set_partLTime(self, nValue):
        CBash.SetFIDFieldF(self._CollectionIndex, self._ModName, self._recordID, 48, c_float(nValue))
    partLTime = property(get_partLTime, set_partLTime)
    def get_partLDelta(self):
        CBash.ReadFIDField.restype = POINTER(c_float)
        retValue = CBash.ReadFIDField(self._CollectionIndex, self._ModName, self._recordID, 49)
        if(retValue): return retValue.contents.value
        return None
    def set_partLDelta(self, nValue):
        CBash.SetFIDFieldF(self._CollectionIndex, self._ModName, self._recordID, 49, c_float(nValue))
    partLDelta = property(get_partLDelta, set_partLDelta)
    def get_partNSpd(self):
        CBash.ReadFIDField.restype = POINTER(c_float)
        retValue = CBash.ReadFIDField(self._CollectionIndex, self._ModName, self._recordID, 50)
        if(retValue): return retValue.contents.value
        return None
    def set_partNSpd(self, nValue):
        CBash.SetFIDFieldF(self._CollectionIndex, self._ModName, self._recordID, 50, c_float(nValue))
    partNSpd = property(get_partNSpd, set_partNSpd)
    def get_partNAcc(self):
        CBash.ReadFIDField.restype = POINTER(c_float)
        retValue = CBash.ReadFIDField(self._CollectionIndex, self._ModName, self._recordID, 51)
        if(retValue): return retValue.contents.value
        return None
    def set_partNAcc(self, nValue):
        CBash.SetFIDFieldF(self._CollectionIndex, self._ModName, self._recordID, 51, c_float(nValue))
    partNAcc = property(get_partNAcc, set_partNAcc)
    def get_partVel1(self):
        CBash.ReadFIDField.restype = POINTER(c_float)
        retValue = CBash.ReadFIDField(self._CollectionIndex, self._ModName, self._recordID, 52)
        if(retValue): return retValue.contents.value
        return None
    def set_partVel1(self, nValue):
        CBash.SetFIDFieldF(self._CollectionIndex, self._ModName, self._recordID, 52, c_float(nValue))
    partVel1 = property(get_partVel1, set_partVel1)
    def get_partVel2(self):
        CBash.ReadFIDField.restype = POINTER(c_float)
        retValue = CBash.ReadFIDField(self._CollectionIndex, self._ModName, self._recordID, 53)
        if(retValue): return retValue.contents.value
        return None
    def set_partVel2(self, nValue):
        CBash.SetFIDFieldF(self._CollectionIndex, self._ModName, self._recordID, 53, c_float(nValue))
    partVel2 = property(get_partVel2, set_partVel2)
    def get_partVel3(self):
        CBash.ReadFIDField.restype = POINTER(c_float)
        retValue = CBash.ReadFIDField(self._CollectionIndex, self._ModName, self._recordID, 54)
        if(retValue): return retValue.contents.value
        return None
    def set_partVel3(self, nValue):
        CBash.SetFIDFieldF(self._CollectionIndex, self._ModName, self._recordID, 54, c_float(nValue))
    partVel3 = property(get_partVel3, set_partVel3)
    def get_partAcc1(self):
        CBash.ReadFIDField.restype = POINTER(c_float)
        retValue = CBash.ReadFIDField(self._CollectionIndex, self._ModName, self._recordID, 55)
        if(retValue): return retValue.contents.value
        return None
    def set_partAcc1(self, nValue):
        CBash.SetFIDFieldF(self._CollectionIndex, self._ModName, self._recordID, 55, c_float(nValue))
    partAcc1 = property(get_partAcc1, set_partAcc1)
    def get_partAcc2(self):
        CBash.ReadFIDField.restype = POINTER(c_float)
        retValue = CBash.ReadFIDField(self._CollectionIndex, self._ModName, self._recordID, 56)
        if(retValue): return retValue.contents.value
        return None
    def set_partAcc2(self, nValue):
        CBash.SetFIDFieldF(self._CollectionIndex, self._ModName, self._recordID, 56, c_float(nValue))
    partAcc2 = property(get_partAcc2, set_partAcc2)
    def get_partAcc3(self):
        CBash.ReadFIDField.restype = POINTER(c_float)
        retValue = CBash.ReadFIDField(self._CollectionIndex, self._ModName, self._recordID, 57)
        if(retValue): return retValue.contents.value
        return None
    def set_partAcc3(self, nValue):
        CBash.SetFIDFieldF(self._CollectionIndex, self._ModName, self._recordID, 57, c_float(nValue))
    partAcc3 = property(get_partAcc3, set_partAcc3)
    def get_partKey1(self):
        CBash.ReadFIDField.restype = POINTER(c_float)
        retValue = CBash.ReadFIDField(self._CollectionIndex, self._ModName, self._recordID, 58)
        if(retValue): return retValue.contents.value
        return None
    def set_partKey1(self, nValue):
        CBash.SetFIDFieldF(self._CollectionIndex, self._ModName, self._recordID, 58, c_float(nValue))
    partKey1 = property(get_partKey1, set_partKey1)
    def get_partKey2(self):
        CBash.ReadFIDField.restype = POINTER(c_float)
        retValue = CBash.ReadFIDField(self._CollectionIndex, self._ModName, self._recordID, 59)
        if(retValue): return retValue.contents.value
        return None
    def set_partKey2(self, nValue):
        CBash.SetFIDFieldF(self._CollectionIndex, self._ModName, self._recordID, 59, c_float(nValue))
    partKey2 = property(get_partKey2, set_partKey2)
    def get_partKey1Time(self):
        CBash.ReadFIDField.restype = POINTER(c_float)
        retValue = CBash.ReadFIDField(self._CollectionIndex, self._ModName, self._recordID, 60)
        if(retValue): return retValue.contents.value
        return None
    def set_partKey1Time(self, nValue):
        CBash.SetFIDFieldF(self._CollectionIndex, self._ModName, self._recordID, 60, c_float(nValue))
    partKey1Time = property(get_partKey1Time, set_partKey1Time)
    def get_partKey2Time(self):
        CBash.ReadFIDField.restype = POINTER(c_float)
        retValue = CBash.ReadFIDField(self._CollectionIndex, self._ModName, self._recordID, 61)
        if(retValue): return retValue.contents.value
        return None
    def set_partKey2Time(self, nValue):
        CBash.SetFIDFieldF(self._CollectionIndex, self._ModName, self._recordID, 61, c_float(nValue))
    partKey2Time = property(get_partKey2Time, set_partKey2Time)
    def get_key1Red(self):
        CBash.ReadFIDField.restype = POINTER(c_ubyte)
        retValue = CBash.ReadFIDField(self._CollectionIndex, self._ModName, self._recordID, 62)
        if(retValue): return retValue.contents.value
        return None
    def set_key1Red(self, nValue):
        CBash.SetFIDFieldUC(self._CollectionIndex, self._ModName, self._recordID, 62, c_ubyte(nValue))
    key1Red = property(get_key1Red, set_key1Red)
    def get_key1Green(self):
        CBash.ReadFIDField.restype = POINTER(c_ubyte)
        retValue = CBash.ReadFIDField(self._CollectionIndex, self._ModName, self._recordID, 63)
        if(retValue): return retValue.contents.value
        return None
    def set_key1Green(self, nValue):
        CBash.SetFIDFieldUC(self._CollectionIndex, self._ModName, self._recordID, 63, c_ubyte(nValue))
    key1Green = property(get_key1Green, set_key1Green)
    def get_key1Blue(self):
        CBash.ReadFIDField.restype = POINTER(c_ubyte)
        retValue = CBash.ReadFIDField(self._CollectionIndex, self._ModName, self._recordID, 64)
        if(retValue): return retValue.contents.value
        return None
    def set_key1Blue(self, nValue):
        CBash.SetFIDFieldUC(self._CollectionIndex, self._ModName, self._recordID, 64, c_ubyte(nValue))
    key1Blue = property(get_key1Blue, set_key1Blue)
    def get_unused4(self):
        numRecords = CBash.GetFIDFieldArraySize(self._CollectionIndex, self._ModName, self._recordID, 65)
        if(numRecords > 0):
            cRecords = POINTER(c_ubyte * numRecords)()
            CBash.GetFIDFieldArray(self._CollectionIndex, self._ModName, self._recordID, 65, byref(cRecords))
            return [cRecords.contents[x] for x in range(0, numRecords)]
        return []
    def set_unused4(self, nValue):
        CBash.SetFIDFieldR(self._CollectionIndex, self._ModName, self._recordID, 65, struct.pack('B', *nValue), 1)
    unused4 = property(get_unused4, set_unused4)
    def get_key2Red(self):
        CBash.ReadFIDField.restype = POINTER(c_ubyte)
        retValue = CBash.ReadFIDField(self._CollectionIndex, self._ModName, self._recordID, 66)
        if(retValue): return retValue.contents.value
        return None
    def set_key2Red(self, nValue):
        CBash.SetFIDFieldUC(self._CollectionIndex, self._ModName, self._recordID, 66, c_ubyte(nValue))
    key2Red = property(get_key2Red, set_key2Red)
    def get_key2Green(self):
        CBash.ReadFIDField.restype = POINTER(c_ubyte)
        retValue = CBash.ReadFIDField(self._CollectionIndex, self._ModName, self._recordID, 67)
        if(retValue): return retValue.contents.value
        return None
    def set_key2Green(self, nValue):
        CBash.SetFIDFieldUC(self._CollectionIndex, self._ModName, self._recordID, 67, c_ubyte(nValue))
    key2Green = property(get_key2Green, set_key2Green)
    def get_key2Blue(self):
        CBash.ReadFIDField.restype = POINTER(c_ubyte)
        retValue = CBash.ReadFIDField(self._CollectionIndex, self._ModName, self._recordID, 68)
        if(retValue): return retValue.contents.value
        return None
    def set_key2Blue(self, nValue):
        CBash.SetFIDFieldUC(self._CollectionIndex, self._ModName, self._recordID, 68, c_ubyte(nValue))
    key2Blue = property(get_key2Blue, set_key2Blue)
    def get_unused5(self):
        numRecords = CBash.GetFIDFieldArraySize(self._CollectionIndex, self._ModName, self._recordID, 69)
        if(numRecords > 0):
            cRecords = POINTER(c_ubyte * numRecords)()
            CBash.GetFIDFieldArray(self._CollectionIndex, self._ModName, self._recordID, 69, byref(cRecords))
            return [cRecords.contents[x] for x in range(0, numRecords)]
        return []
    def set_unused5(self, nValue):
        CBash.SetFIDFieldR(self._CollectionIndex, self._ModName, self._recordID, 69, struct.pack('B', *nValue), 1)
    unused5 = property(get_unused5, set_unused5)
    def get_key3Red(self):
        CBash.ReadFIDField.restype = POINTER(c_ubyte)
        retValue = CBash.ReadFIDField(self._CollectionIndex, self._ModName, self._recordID, 70)
        if(retValue): return retValue.contents.value
        return None
    def set_key3Red(self, nValue):
        CBash.SetFIDFieldUC(self._CollectionIndex, self._ModName, self._recordID, 70, c_ubyte(nValue))
    key3Red = property(get_key3Red, set_key3Red)
    def get_key3Green(self):
        CBash.ReadFIDField.restype = POINTER(c_ubyte)
        retValue = CBash.ReadFIDField(self._CollectionIndex, self._ModName, self._recordID, 71)
        if(retValue): return retValue.contents.value
        return None
    def set_key3Green(self, nValue):
        CBash.SetFIDFieldUC(self._CollectionIndex, self._ModName, self._recordID, 71, c_ubyte(nValue))
    key3Green = property(get_key3Green, set_key3Green)
    def get_key3Blue(self):
        CBash.ReadFIDField.restype = POINTER(c_ubyte)
        retValue = CBash.ReadFIDField(self._CollectionIndex, self._ModName, self._recordID, 72)
        if(retValue): return retValue.contents.value
        return None
    def set_key3Blue(self, nValue):
        CBash.SetFIDFieldUC(self._CollectionIndex, self._ModName, self._recordID, 72, c_ubyte(nValue))
    key3Blue = property(get_key3Blue, set_key3Blue)
    def get_unused6(self):
        numRecords = CBash.GetFIDFieldArraySize(self._CollectionIndex, self._ModName, self._recordID, 73)
        if(numRecords > 0):
            cRecords = POINTER(c_ubyte * numRecords)()
            CBash.GetFIDFieldArray(self._CollectionIndex, self._ModName, self._recordID, 73, byref(cRecords))
            return [cRecords.contents[x] for x in range(0, numRecords)]
        return []
    def set_unused6(self, nValue):
        CBash.SetFIDFieldR(self._CollectionIndex, self._ModName, self._recordID, 73, struct.pack('B', *nValue), 1)
    unused6 = property(get_unused6, set_unused6)
    def get_key1A(self):
        CBash.ReadFIDField.restype = POINTER(c_float)
        retValue = CBash.ReadFIDField(self._CollectionIndex, self._ModName, self._recordID, 74)
        if(retValue): return retValue.contents.value
        return None
    def set_key1A(self, nValue):
        CBash.SetFIDFieldF(self._CollectionIndex, self._ModName, self._recordID, 74, c_float(nValue))
    key1A = property(get_key1A, set_key1A)
    def get_key2A(self):
        CBash.ReadFIDField.restype = POINTER(c_float)
        retValue = CBash.ReadFIDField(self._CollectionIndex, self._ModName, self._recordID, 75)
        if(retValue): return retValue.contents.value
        return None
    def set_key2A(self, nValue):
        CBash.SetFIDFieldF(self._CollectionIndex, self._ModName, self._recordID, 75, c_float(nValue))
    key2A = property(get_key2A, set_key2A)
    def get_key3A(self):
        CBash.ReadFIDField.restype = POINTER(c_float)
        retValue = CBash.ReadFIDField(self._CollectionIndex, self._ModName, self._recordID, 76)
        if(retValue): return retValue.contents.value
        return None
    def set_key3A(self, nValue):
        CBash.SetFIDFieldF(self._CollectionIndex, self._ModName, self._recordID, 76, c_float(nValue))
    key3A = property(get_key3A, set_key3A)
    def get_key1Time(self):
        CBash.ReadFIDField.restype = POINTER(c_float)
        retValue = CBash.ReadFIDField(self._CollectionIndex, self._ModName, self._recordID, 77)
        if(retValue): return retValue.contents.value
        return None
    def set_key1Time(self, nValue):
        CBash.SetFIDFieldF(self._CollectionIndex, self._ModName, self._recordID, 77, c_float(nValue))
    key1Time = property(get_key1Time, set_key1Time)
    def get_key2Time(self):
        CBash.ReadFIDField.restype = POINTER(c_float)
        retValue = CBash.ReadFIDField(self._CollectionIndex, self._ModName, self._recordID, 78)
        if(retValue): return retValue.contents.value
        return None
    def set_key2Time(self, nValue):
        CBash.SetFIDFieldF(self._CollectionIndex, self._ModName, self._recordID, 78, c_float(nValue))
    key2Time = property(get_key2Time, set_key2Time)
    def get_key3Time(self):
        CBash.ReadFIDField.restype = POINTER(c_float)
        retValue = CBash.ReadFIDField(self._CollectionIndex, self._ModName, self._recordID, 79)
        if(retValue): return retValue.contents.value
        return None
    def set_key3Time(self, nValue):
        CBash.SetFIDFieldF(self._CollectionIndex, self._ModName, self._recordID, 79, c_float(nValue))
    key3Time = property(get_key3Time, set_key3Time)
    def get_IsNoMembraneShader(self):
        return (self.flags & 0x00000001) != 0
    def set_IsNoMembraneShader(self, nValue):
        if (nValue == True): self.flags |= 0x00000001
        else: self.flags &= ~0x00000001
    IsNoMemShader = IsNoMembraneShader = property(get_IsNoMembraneShader, set_IsNoMembraneShader)
    def get_IsNoParticleShader(self):
        return (self.flags & 0x00000008) != 0
    def set_IsNoParticleShader(self, nValue):
        if (nValue == True): self.flags |= 0x00000008
        else: self.flags &= ~0x00000008
    IsNoPartShader = IsNoParticleShader = property(get_IsNoParticleShader, set_IsNoParticleShader)
    def get_IsEdgeEffectInverse(self):
        return (self.flags & 0x00000010) != 0
    def set_IsEdgeEffectInverse(self, nValue):
        if (nValue == True): self.flags |= 0x00000010
        else: self.flags &= ~0x00000010
    IsEdgeInverse = IsEdgeEffectInverse = property(get_IsEdgeEffectInverse, set_IsEdgeEffectInverse)
    def get_IsMembraneShaderSkinOnly(self):
        return (self.flags & 0x00000020) != 0
    def set_IsMembraneShaderSkinOnly(self, nValue):
        if (nValue == True): self.flags |= 0x00000020
        else: self.flags &= ~0x00000020
    IsMemSkinOnly = IsMembraneShaderSkinOnly= property(get_IsMembraneShaderSkinOnly, set_IsMembraneShaderSkinOnly)

class ModFile(object):
    def __init__(self, CollectionIndex, ModName=None):
        self._CollectionIndex = CollectionIndex
        self._ModName = ModName
        self.type_class = {}
    def MakeLongFid(self, fid):
        if(fid == None): return (None,None)
        masterIndex = int(fid >> 24)
        object = int(fid & 0xFFFFFFL)
        master = CBash.GetModName(self._CollectionIndex, masterIndex)
        if(exists(".\\bolt.py")):
            return (GPath(master),object)
        return (master,object)
    def MakeShortFid(self, longFid):
        if not isinstance(longFid, tuple): return longFid
        fid = CBash.GetCorrectedFID(self._CollectionIndex, nValue[0].s, nValue[1])
        if(fid == 0): return None
        return fid
    def UpdateReferences(self, origFid, newFid):
        if not isinstance(origFid, int): return 0
        if not isinstance(newFid, int): return 0
        return CBash.UpdateAllReferences(self._CollectionIndex, self._ModName, origFid, newFid)
    def CleanMasters(self):
        return CBash.CleanMasters(self._CollectionIndex, self._ModName)
    def createGMSTRecord(self, recordID):
        if(CBash.CreateGMSTRecord(self._CollectionIndex, self._ModName, recordID)):
            return GMSTRecord(self._CollectionIndex, self._ModName, recordID)
        return None
    def createGLOBRecord(self):
        FID = CBash.CreateGLOBRecord(self._CollectionIndex, self._ModName)
        if(FID): return GLOBRecord(self._CollectionIndex, self._ModName, FID)
        return None
    def createCLASRecord(self):
        FID = CBash.CreateCLASRecord(self._CollectionIndex, self._ModName)
        if(FID): return CLASRecord(self._CollectionIndex, self._ModName, FID)
        return None
    def createFACTRecord(self):
        FID = CBash.CreateFACTRecord(self._CollectionIndex, self._ModName)
        if(FID): return FACTRecord(self._CollectionIndex, self._ModName, FID)
        return None
    def createHAIRRecord(self):
        FID = CBash.CreateHAIRRecord(self._CollectionIndex, self._ModName)
        if(FID): return HAIRRecord(self._CollectionIndex, self._ModName, FID)
        return None
    def createEYESRecord(self):
        FID = CBash.CreateEYESRecord(self._CollectionIndex, self._ModName)
        if(FID): return EYESRecord(self._CollectionIndex, self._ModName, FID)
        return None
    def createRACERecord(self):
        FID = CBash.CreateRACERecord(self._CollectionIndex, self._ModName)
        if(FID): return RACERecord(self._CollectionIndex, self._ModName, FID)
        return None
    def createSOUNRecord(self):
        FID = CBash.CreateSOUNRecord(self._CollectionIndex, self._ModName)
        if(FID): return SOUNRecord(self._CollectionIndex, self._ModName, FID)
        return None
    def createSKILRecord(self):
        FID = CBash.CreateSKILRecord(self._CollectionIndex, self._ModName)
        if(FID): return SKILRecord(self._CollectionIndex, self._ModName, FID)
        return None
    def createMGEFRecord(self):
        FID = CBash.CreateMGEFRecord(self._CollectionIndex, self._ModName)
        if(FID): return MGEFRecord(self._CollectionIndex, self._ModName, FID)
        return None
    def createSCPTRecord(self):
        FID = CBash.CreateSCPTRecord(self._CollectionIndex, self._ModName)
        if(FID): return SCPTRecord(self._CollectionIndex, self._ModName, FID)
        return None
    def createLTEXRecord(self):
        FID = CBash.CreateLTEXRecord(self._CollectionIndex, self._ModName)
        if(FID): return LTEXRecord(self._CollectionIndex, self._ModName, FID)
        return None
    def createENCHRecord(self):
        FID = CBash.CreateENCHRecord(self._CollectionIndex, self._ModName)
        if(FID): return ENCHRecord(self._CollectionIndex, self._ModName, FID)
        return None
    def createSPELRecord(self):
        FID = CBash.CreateSPELRecord(self._CollectionIndex, self._ModName)
        if(FID): return SPELRecord(self._CollectionIndex, self._ModName, FID)
        return None
    def createBSGNRecord(self):
        FID = CBash.CreateBSGNRecord(self._CollectionIndex, self._ModName)
        if(FID): return BSGNRecord(self._CollectionIndex, self._ModName, FID)
        return None
    def createACTIRecord(self):
        FID = CBash.CreateACTIRecord(self._CollectionIndex, self._ModName)
        if(FID): return ACTIRecord(self._CollectionIndex, self._ModName, FID)
        return None
    def createAPPARecord(self):
        FID = CBash.CreateAPPARecord(self._CollectionIndex, self._ModName)
        if(FID): return APPARecord(self._CollectionIndex, self._ModName, FID)
        return None
    def createARMORecord(self):
        FID = CBash.CreateARMORecord(self._CollectionIndex, self._ModName)
        if(FID): return ARMORecord(self._CollectionIndex, self._ModName, FID)
        return None
    def createBOOKRecord(self):
        FID = CBash.CreateBOOKRecord(self._CollectionIndex, self._ModName)
        if(FID): return BOOKRecord(self._CollectionIndex, self._ModName, FID)
        return None
    def createCLOTRecord(self):
        FID = CBash.CreateCLOTRecord(self._CollectionIndex, self._ModName)
        if(FID): return CLOTRecord(self._CollectionIndex, self._ModName, FID)
        return None
    def createCONTRecord(self):
        FID = CBash.CreateCONTRecord(self._CollectionIndex, self._ModName)
        if(FID): return CONTRecord(self._CollectionIndex, self._ModName, FID)
        return None
    def createDOORRecord(self):
        FID = CBash.CreateDOORRecord(self._CollectionIndex, self._ModName)
        if(FID): return DOORRecord(self._CollectionIndex, self._ModName, FID)
        return None
    def createINGRRecord(self):
        FID = CBash.CreateINGRRecord(self._CollectionIndex, self._ModName)
        if(FID): return INGRRecord(self._CollectionIndex, self._ModName, FID)
        return None
    def createLIGHRecord(self):
        FID = CBash.CreateLIGHRecord(self._CollectionIndex, self._ModName)
        if(FID): return LIGHRecord(self._CollectionIndex, self._ModName, FID)
        return None
    def createMISCRecord(self):
        FID = CBash.CreateMISCRecord(self._CollectionIndex, self._ModName)
        if(FID): return MISCRecord(self._CollectionIndex, self._ModName, FID)
        return None
    def createSTATRecord(self):
        FID = CBash.CreateSTATRecord(self._CollectionIndex, self._ModName)
        if(FID): return STATRecord(self._CollectionIndex, self._ModName, FID)
        return None
    def createGRASRecord(self):
        FID = CBash.CreateGRASRecord(self._CollectionIndex, self._ModName)
        if(FID): return GRASRecord(self._CollectionIndex, self._ModName, FID)
        return None
    def createTREERecord(self):
        FID = CBash.CreateTREERecord(self._CollectionIndex, self._ModName)
        if(FID): return TREERecord(self._CollectionIndex, self._ModName, FID)
        return None
    def createFLORRecord(self):
        FID = CBash.CreateFLORRecord(self._CollectionIndex, self._ModName)
        if(FID): return FLORRecord(self._CollectionIndex, self._ModName, FID)
        return None
    def createFURNRecord(self):
        FID = CBash.CreateFURNRecord(self._CollectionIndex, self._ModName)
        if(FID): return FURNRecord(self._CollectionIndex, self._ModName, FID)
        return None
    def createWEAPRecord(self):
        FID = CBash.CreateWEAPRecord(self._CollectionIndex, self._ModName)
        if(FID): return WEAPRecord(self._CollectionIndex, self._ModName, FID)
        return None
    def createAMMORecord(self):
        FID = CBash.CreateAMMORecord(self._CollectionIndex, self._ModName)
        if(FID): return AMMORecord(self._CollectionIndex, self._ModName, FID)
        return None
    def createNPC_Record(self):
        FID = CBash.CreateNPC_Record(self._CollectionIndex, self._ModName)
        if(FID): return NPC_Record(self._CollectionIndex, self._ModName, FID)
        return None
    def createCREARecord(self):
        FID = CBash.CreateCREARecord(self._CollectionIndex, self._ModName)
        if(FID): return CREARecord(self._CollectionIndex, self._ModName, FID)
        return None
    def createLVLCRecord(self):
        FID = CBash.CreateLVLCRecord(self._CollectionIndex, self._ModName)
        if(FID): return LVLCRecord(self._CollectionIndex, self._ModName, FID)
        return None
    def createSLGMRecord(self):
        FID = CBash.CreateSLGMRecord(self._CollectionIndex, self._ModName)
        if(FID): return SLGMRecord(self._CollectionIndex, self._ModName, FID)
        return None
    def createKEYMRecord(self):
        FID = CBash.CreateKEYMRecord(self._CollectionIndex, self._ModName)
        if(FID): return KEYMRecord(self._CollectionIndex, self._ModName, FID)
        return None
    def createALCHRecord(self):
        FID = CBash.CreateALCHRecord(self._CollectionIndex, self._ModName)
        if(FID): return ALCHRecord(self._CollectionIndex, self._ModName, FID)
        return None
    def createSBSPRecord(self):
        FID = CBash.CreateSBSPRecord(self._CollectionIndex, self._ModName)
        if(FID): return SBSPRecord(self._CollectionIndex, self._ModName, FID)
        return None
    def createSGSTRecord(self):
        FID = CBash.CreateSGSTRecord(self._CollectionIndex, self._ModName)
        if(FID): return SGSTRecord(self._CollectionIndex, self._ModName, FID)
        return None
    def createLVLIRecord(self):
        FID = CBash.CreateLVLIRecord(self._CollectionIndex, self._ModName)
        if(FID): return LVLIRecord(self._CollectionIndex, self._ModName, FID)
        return None
    def createWTHRRecord(self):
        FID = CBash.CreateWTHRRecord(self._CollectionIndex, self._ModName)
        if(FID): return WTHRRecord(self._CollectionIndex, self._ModName, FID)
        return None
    def createCLMTRecord(self):
        FID = CBash.CreateCLMTRecord(self._CollectionIndex, self._ModName)
        if(FID): return CLMTRecord(self._CollectionIndex, self._ModName, FID)
        return None
    def createREGNRecord(self):
        FID = CBash.CreateREGNRecord(self._CollectionIndex, self._ModName)
        if(FID): return REGNRecord(self._CollectionIndex, self._ModName, FID)
        return None
    def createCELLRecord(self):
        FID = CBash.CreateCELLRecord(self._CollectionIndex, self._ModName, 0, c_bool(False))
        if(FID): return CELLRecord(self._CollectionIndex, self._ModName, FID)
        return None
    def createWRLDRecord(self):
        FID = CBash.CreateWRLDRecord(self._CollectionIndex, self._ModName)
        if(FID): return WRLDRecord(self._CollectionIndex, self._ModName, FID)
        return None
    def createDIALRecord(self):
        FID = CBash.CreateDIALRecord(self._CollectionIndex, self._ModName)
        if(FID): return DIALRecord(self._CollectionIndex, self._ModName, FID)
        return None
    def createQUSTRecord(self):
        FID = CBash.CreateQUSTRecord(self._CollectionIndex, self._ModName)
        if(FID): return QUSTRecord(self._CollectionIndex, self._ModName, FID)
        return None
    def createIDLERecord(self):
        FID = CBash.CreateIDLERecord(self._CollectionIndex, self._ModName)
        if(FID): return IDLERecord(self._CollectionIndex, self._ModName, FID)
        return None
    def createPACKRecord(self):
        FID = CBash.CreatePACKRecord(self._CollectionIndex, self._ModName)
        if(FID): return PACKRecord(self._CollectionIndex, self._ModName, FID)
        return None
    def createCSTYRecord(self):
        FID = CBash.CreateCSTYRecord(self._CollectionIndex, self._ModName)
        if(FID): return CSTYRecord(self._CollectionIndex, self._ModName, FID)
        return None
    def createLSCRRecord(self):
        FID = CBash.CreateLSCRRecord(self._CollectionIndex, self._ModName)
        if(FID): return LSCRRecord(self._CollectionIndex, self._ModName, FID)
        return None
    def createLVSPRecord(self):
        FID = CBash.CreateLVSPRecord(self._CollectionIndex, self._ModName)
        if(FID): return LVSPRecord(self._CollectionIndex, self._ModName, FID)
        return None
    def createANIORecord(self):
        FID = CBash.CreateANIORecord(self._CollectionIndex, self._ModName)
        if(FID): return ANIORecord(self._CollectionIndex, self._ModName, FID)
        return None
    def createWATRRecord(self):
        FID = CBash.CreateWATRRecord(self._CollectionIndex, self._ModName)
        if(FID): return WATRRecord(self._CollectionIndex, self._ModName, FID)
        return None
    def createEFSHRecord(self):
        FID = CBash.CreateEFSHRecord(self._CollectionIndex, self._ModName)
        if(FID): return EFSHRecord(self._CollectionIndex, self._ModName, FID)
        return None

    def safeSave(self):
        return CBash.SafeSaveMod(self._CollectionIndex, self._ModName, c_bool(False))
    def safeCloseSave(self):
        return CBash.SafeSaveMod(self._CollectionIndex, self._ModName, c_bool(True))
    @property
    def TES4(self):
        return TES4Record(self._CollectionIndex, self._ModName)

    @property
    def GMST(self):
        numRecords = CBash.GetNumGMSTRecords(self._CollectionIndex, self._ModName)
        if(numRecords > 0):
            cRecords = (POINTER(c_char_p) * numRecords)()
            CBash.GetGMSTRecords(self._CollectionIndex, self._ModName, cRecords)
            return [GMSTRecord(self._CollectionIndex, self._ModName, string_at(cRecords[x])) for x in range(0, numRecords)]
        return []
    @property
    def GLOB(self):
        numRecords = CBash.GetNumGLOBRecords(self._CollectionIndex, self._ModName)
        if(numRecords > 0):
            cRecords = (POINTER(c_uint) * numRecords)()
            CBash.GetGLOBRecords(self._CollectionIndex, self._ModName, cRecords)
            return [GLOBRecord(self._CollectionIndex, self._ModName, x.contents.value) for x in cRecords]
        return []
    @property
    def CLAS(self):
        numRecords = CBash.GetNumCLASRecords(self._CollectionIndex, self._ModName)
        if(numRecords > 0):
            cRecords = (POINTER(c_uint) * numRecords)()
            CBash.GetCLASRecords(self._CollectionIndex, self._ModName, cRecords)
            return [CLASRecord(self._CollectionIndex, self._ModName, x.contents.value) for x in cRecords]
        return []
    @property
    def FACT(self):
        numRecords = CBash.GetNumFACTRecords(self._CollectionIndex, self._ModName)
        if(numRecords > 0):
            cRecords = (POINTER(c_uint) * numRecords)()
            CBash.GetFACTRecords(self._CollectionIndex, self._ModName, cRecords)
            return [FACTRecord(self._CollectionIndex, self._ModName, x.contents.value) for x in cRecords]
        return []
    @property
    def HAIR(self):
        numRecords = CBash.GetNumHAIRRecords(self._CollectionIndex, self._ModName)
        if(numRecords > 0):
            cRecords = (POINTER(c_uint) * numRecords)()
            CBash.GetHAIRRecords(self._CollectionIndex, self._ModName, cRecords)
            return [HAIRRecord(self._CollectionIndex, self._ModName, x.contents.value) for x in cRecords]
        return []
    @property
    def EYES(self):
        numRecords = CBash.GetNumEYESRecords(self._CollectionIndex, self._ModName)
        if(numRecords > 0):
            cRecords = (POINTER(c_uint) * numRecords)()
            CBash.GetEYESRecords(self._CollectionIndex, self._ModName, cRecords)
            return [EYESRecord(self._CollectionIndex, self._ModName, x.contents.value) for x in cRecords]
        return []
    @property
    def RACE(self):
        numRecords = CBash.GetNumRACERecords(self._CollectionIndex, self._ModName)
        if(numRecords > 0):
            cRecords = (POINTER(c_uint) * numRecords)()
            CBash.GetRACERecords(self._CollectionIndex, self._ModName, cRecords)
            return [RACERecord(self._CollectionIndex, self._ModName, x.contents.value) for x in cRecords]
        return []
    @property
    def SOUN(self):
        numRecords = CBash.GetNumSOUNRecords(self._CollectionIndex, self._ModName)
        if(numRecords > 0):
            cRecords = (POINTER(c_uint) * numRecords)()
            CBash.GetSOUNRecords(self._CollectionIndex, self._ModName, cRecords)
            return [SOUNRecord(self._CollectionIndex, self._ModName, x.contents.value) for x in cRecords]
        return []
    @property
    def SKIL(self):
        numRecords = CBash.GetNumSKILRecords(self._CollectionIndex, self._ModName)
        if(numRecords > 0):
            cRecords = (POINTER(c_uint) * numRecords)()
            CBash.GetSKILRecords(self._CollectionIndex, self._ModName, cRecords)
            return [SKILRecord(self._CollectionIndex, self._ModName, x.contents.value) for x in cRecords]
        return []
    @property
    def MGEF(self):
        numRecords = CBash.GetNumMGEFRecords(self._CollectionIndex, self._ModName)
        if(numRecords > 0):
            cRecords = (POINTER(c_uint) * numRecords)()
            CBash.GetMGEFRecords(self._CollectionIndex, self._ModName, cRecords)
            return [MGEFRecord(self._CollectionIndex, self._ModName, x.contents.value) for x in cRecords]
        return []
    @property
    def SCPT(self):
        numRecords = CBash.GetNumSCPTRecords(self._CollectionIndex, self._ModName)
        if(numRecords > 0):
            cRecords = (POINTER(c_uint) * numRecords)()
            CBash.GetSCPTRecords(self._CollectionIndex, self._ModName, cRecords)
            return [SCPTRecord(self._CollectionIndex, self._ModName, x.contents.value) for x in cRecords]
        return []
    @property
    def LTEX(self):
        numRecords = CBash.GetNumLTEXRecords(self._CollectionIndex, self._ModName)
        if(numRecords > 0):
            cRecords = (POINTER(c_uint) * numRecords)()
            CBash.GetLTEXRecords(self._CollectionIndex, self._ModName, cRecords)
            return [LTEXRecord(self._CollectionIndex, self._ModName, x.contents.value) for x in cRecords]
        return []
    @property
    def ENCH(self):
        numRecords = CBash.GetNumENCHRecords(self._CollectionIndex, self._ModName)
        if(numRecords > 0):
            cRecords = (POINTER(c_uint) * numRecords)()
            CBash.GetENCHRecords(self._CollectionIndex, self._ModName, cRecords)
            return [ENCHRecord(self._CollectionIndex, self._ModName, x.contents.value) for x in cRecords]
        return []
    @property
    def SPEL(self):
        numRecords = CBash.GetNumSPELRecords(self._CollectionIndex, self._ModName)
        if(numRecords > 0):
            cRecords = (POINTER(c_uint) * numRecords)()
            CBash.GetSPELRecords(self._CollectionIndex, self._ModName, cRecords)
            return [SPELRecord(self._CollectionIndex, self._ModName, x.contents.value) for x in cRecords]
        return []
    @property
    def BSGN(self):
        numRecords = CBash.GetNumBSGNRecords(self._CollectionIndex, self._ModName)
        if(numRecords > 0):
            cRecords = (POINTER(c_uint) * numRecords)()
            CBash.GetBSGNRecords(self._CollectionIndex, self._ModName, cRecords)
            return [BSGNRecord(self._CollectionIndex, self._ModName, x.contents.value) for x in cRecords]
        return []
    @property
    def ACTI(self):
        numRecords = CBash.GetNumACTIRecords(self._CollectionIndex, self._ModName)
        if(numRecords > 0):
            cRecords = (POINTER(c_uint) * numRecords)()
            CBash.GetACTIRecords(self._CollectionIndex, self._ModName, cRecords)
            return [ACTIRecord(self._CollectionIndex, self._ModName, x.contents.value) for x in cRecords]
        return []
    @property
    def APPA(self):
        numRecords = CBash.GetNumAPPARecords(self._CollectionIndex, self._ModName)
        if(numRecords > 0):
            cRecords = (POINTER(c_uint) * numRecords)()
            CBash.GetAPPARecords(self._CollectionIndex, self._ModName, cRecords)
            return [APPARecord(self._CollectionIndex, self._ModName, x.contents.value) for x in cRecords]
        return []
    @property
    def ARMO(self):
        numRecords = CBash.GetNumARMORecords(self._CollectionIndex, self._ModName)
        if(numRecords > 0):
            cRecords = (POINTER(c_uint) * numRecords)()
            CBash.GetARMORecords(self._CollectionIndex, self._ModName, cRecords)
            return [ARMORecord(self._CollectionIndex, self._ModName, x.contents.value) for x in cRecords]
        return []
    @property
    def BOOK(self):
        numRecords = CBash.GetNumBOOKRecords(self._CollectionIndex, self._ModName)
        if(numRecords > 0):
            cRecords = (POINTER(c_uint) * numRecords)()
            CBash.GetBOOKRecords(self._CollectionIndex, self._ModName, cRecords)
            return [BOOKRecord(self._CollectionIndex, self._ModName, x.contents.value) for x in cRecords]
        return []
    @property
    def CLOT(self):
        numRecords = CBash.GetNumCLOTRecords(self._CollectionIndex, self._ModName)
        if(numRecords > 0):
            cRecords = (POINTER(c_uint) * numRecords)()
            CBash.GetCLOTRecords(self._CollectionIndex, self._ModName, cRecords)
            return [CLOTRecord(self._CollectionIndex, self._ModName, x.contents.value) for x in cRecords]
        return []
    @property
    def CONT(self):
        numRecords = CBash.GetNumCONTRecords(self._CollectionIndex, self._ModName)
        if(numRecords > 0):
            cRecords = (POINTER(c_uint) * numRecords)()
            CBash.GetCONTRecords(self._CollectionIndex, self._ModName, cRecords)
            return [CONTRecord(self._CollectionIndex, self._ModName, x.contents.value) for x in cRecords]
        return []
    @property
    def DOOR(self):
        numRecords = CBash.GetNumDOORRecords(self._CollectionIndex, self._ModName)
        if(numRecords > 0):
            cRecords = (POINTER(c_uint) * numRecords)()
            CBash.GetDOORRecords(self._CollectionIndex, self._ModName, cRecords)
            return [DOORRecord(self._CollectionIndex, self._ModName, x.contents.value) for x in cRecords]
        return []
    @property
    def INGR(self):
        numRecords = CBash.GetNumINGRRecords(self._CollectionIndex, self._ModName)
        if(numRecords > 0):
            cRecords = (POINTER(c_uint) * numRecords)()
            CBash.GetINGRRecords(self._CollectionIndex, self._ModName, cRecords)
            return [INGRRecord(self._CollectionIndex, self._ModName, x.contents.value) for x in cRecords]
        return []
    @property
    def LIGH(self):
        numRecords = CBash.GetNumLIGHRecords(self._CollectionIndex, self._ModName)
        if(numRecords > 0):
            cRecords = (POINTER(c_uint) * numRecords)()
            CBash.GetLIGHRecords(self._CollectionIndex, self._ModName, cRecords)
            return [LIGHRecord(self._CollectionIndex, self._ModName, x.contents.value) for x in cRecords]
        return []
    @property
    def MISC(self):
        numRecords = CBash.GetNumMISCRecords(self._CollectionIndex, self._ModName)
        if(numRecords > 0):
            cRecords = (POINTER(c_uint) * numRecords)()
            CBash.GetMISCRecords(self._CollectionIndex, self._ModName, cRecords)
            return [MISCRecord(self._CollectionIndex, self._ModName, x.contents.value) for x in cRecords]
        return []
    @property
    def STAT(self):
        numRecords = CBash.GetNumSTATRecords(self._CollectionIndex, self._ModName)
        if(numRecords > 0):
            cRecords = (POINTER(c_uint) * numRecords)()
            CBash.GetSTATRecords(self._CollectionIndex, self._ModName, cRecords)
            return [STATRecord(self._CollectionIndex, self._ModName, x.contents.value) for x in cRecords]
        return []
    @property
    def GRAS(self):
        numRecords = CBash.GetNumGRASRecords(self._CollectionIndex, self._ModName)
        if(numRecords > 0):
            cRecords = (POINTER(c_uint) * numRecords)()
            CBash.GetGRASRecords(self._CollectionIndex, self._ModName, cRecords)
            return [GRASRecord(self._CollectionIndex, self._ModName, x.contents.value) for x in cRecords]
        return []
    @property
    def TREE(self):
        numRecords = CBash.GetNumTREERecords(self._CollectionIndex, self._ModName)
        if(numRecords > 0):
            cRecords = (POINTER(c_uint) * numRecords)()
            CBash.GetTREERecords(self._CollectionIndex, self._ModName, cRecords)
            return [TREERecord(self._CollectionIndex, self._ModName, x.contents.value) for x in cRecords]
        return []
    @property
    def FLOR(self):
        numRecords = CBash.GetNumFLORRecords(self._CollectionIndex, self._ModName)
        if(numRecords > 0):
            cRecords = (POINTER(c_uint) * numRecords)()
            CBash.GetFLORRecords(self._CollectionIndex, self._ModName, cRecords)
            return [FLORRecord(self._CollectionIndex, self._ModName, x.contents.value) for x in cRecords]
        return []
    @property
    def FURN(self):
        numRecords = CBash.GetNumFURNRecords(self._CollectionIndex, self._ModName)
        if(numRecords > 0):
            cRecords = (POINTER(c_uint) * numRecords)()
            CBash.GetFURNRecords(self._CollectionIndex, self._ModName, cRecords)
            return [FURNRecord(self._CollectionIndex, self._ModName, x.contents.value) for x in cRecords]
        return []
    @property
    def WEAP(self):
        numRecords = CBash.GetNumWEAPRecords(self._CollectionIndex, self._ModName)
        if(numRecords > 0):
            cRecords = (POINTER(c_uint) * numRecords)()
            CBash.GetWEAPRecords(self._CollectionIndex, self._ModName, cRecords)
            return [WEAPRecord(self._CollectionIndex, self._ModName, x.contents.value) for x in cRecords]
        return []
    @property
    def AMMO(self):
        numRecords = CBash.GetNumAMMORecords(self._CollectionIndex, self._ModName)
        if(numRecords > 0):
            cRecords = (POINTER(c_uint) * numRecords)()
            CBash.GetAMMORecords(self._CollectionIndex, self._ModName, cRecords)
            return [AMMORecord(self._CollectionIndex, self._ModName, x.contents.value) for x in cRecords]
        return []
    @property
    def NPC_(self):
        numRecords = CBash.GetNumNPC_Records(self._CollectionIndex, self._ModName)
        if(numRecords > 0):
            cRecords = (POINTER(c_uint) * numRecords)()
            CBash.GetNPC_Records(self._CollectionIndex, self._ModName, cRecords)
            return [NPC_Record(self._CollectionIndex, self._ModName, x.contents.value) for x in cRecords]
        return []
    @property
    def CREA(self):
        numRecords = CBash.GetNumCREARecords(self._CollectionIndex, self._ModName)
        if(numRecords > 0):
            cRecords = (POINTER(c_uint) * numRecords)()
            CBash.GetCREARecords(self._CollectionIndex, self._ModName, cRecords)
            return [CREARecord(self._CollectionIndex, self._ModName, x.contents.value) for x in cRecords]
        return []
    @property
    def LVLC(self):
        numRecords = CBash.GetNumLVLCRecords(self._CollectionIndex, self._ModName)
        if(numRecords > 0):
            cRecords = (POINTER(c_uint) * numRecords)()
            CBash.GetLVLCRecords(self._CollectionIndex, self._ModName, cRecords)
            return [LVLCRecord(self._CollectionIndex, self._ModName, x.contents.value) for x in cRecords]
        return []
    @property
    def SLGM(self):
        numRecords = CBash.GetNumSLGMRecords(self._CollectionIndex, self._ModName)
        if(numRecords > 0):
            cRecords = (POINTER(c_uint) * numRecords)()
            CBash.GetSLGMRecords(self._CollectionIndex, self._ModName, cRecords)
            return [SLGMRecord(self._CollectionIndex, self._ModName, x.contents.value) for x in cRecords]
        return []
    @property
    def KEYM(self):
        numRecords = CBash.GetNumKEYMRecords(self._CollectionIndex, self._ModName)
        if(numRecords > 0):
            cRecords = (POINTER(c_uint) * numRecords)()
            CBash.GetKEYMRecords(self._CollectionIndex, self._ModName, cRecords)
            return [KEYMRecord(self._CollectionIndex, self._ModName, x.contents.value) for x in cRecords]
        return []
    @property
    def ALCH(self):
        numRecords = CBash.GetNumALCHRecords(self._CollectionIndex, self._ModName)
        if(numRecords > 0):
            cRecords = (POINTER(c_uint) * numRecords)()
            CBash.GetALCHRecords(self._CollectionIndex, self._ModName, cRecords)
            return [ALCHRecord(self._CollectionIndex, self._ModName, x.contents.value) for x in cRecords]
        return []
    @property
    def SBSP(self):
        numRecords = CBash.GetNumSBSPRecords(self._CollectionIndex, self._ModName)
        if(numRecords > 0):
            cRecords = (POINTER(c_uint) * numRecords)()
            CBash.GetSBSPRecords(self._CollectionIndex, self._ModName, cRecords)
            return [SBSPRecord(self._CollectionIndex, self._ModName, x.contents.value) for x in cRecords]
        return []
    @property
    def SGST(self):
        numRecords = CBash.GetNumSGSTRecords(self._CollectionIndex, self._ModName)
        if(numRecords > 0):
            cRecords = (POINTER(c_uint) * numRecords)()
            CBash.GetSGSTRecords(self._CollectionIndex, self._ModName, cRecords)
            return [SGSTRecord(self._CollectionIndex, self._ModName, x.contents.value) for x in cRecords]
        return []
    @property
    def LVLI(self):
        numRecords = CBash.GetNumLVLIRecords(self._CollectionIndex, self._ModName)
        if(numRecords > 0):
            cRecords = (POINTER(c_uint) * numRecords)()
            CBash.GetLVLIRecords(self._CollectionIndex, self._ModName, cRecords)
            return [LVLIRecord(self._CollectionIndex, self._ModName, x.contents.value) for x in cRecords]
        return []
    @property
    def WTHR(self):
        numRecords = CBash.GetNumWTHRRecords(self._CollectionIndex, self._ModName)
        if(numRecords > 0):
            cRecords = (POINTER(c_uint) * numRecords)()
            CBash.GetWTHRRecords(self._CollectionIndex, self._ModName, cRecords)
            return [WTHRRecord(self._CollectionIndex, self._ModName, x.contents.value) for x in cRecords]
        return []
    @property
    def CLMT(self):
        numRecords = CBash.GetNumCLMTRecords(self._CollectionIndex, self._ModName)
        if(numRecords > 0):
            cRecords = (POINTER(c_uint) * numRecords)()
            CBash.GetCLMTRecords(self._CollectionIndex, self._ModName, cRecords)
            return [CLMTRecord(self._CollectionIndex, self._ModName, x.contents.value) for x in cRecords]
        return []
    @property
    def REGN(self):
        numRecords = CBash.GetNumREGNRecords(self._CollectionIndex, self._ModName)
        if(numRecords > 0):
            cRecords = (POINTER(c_uint) * numRecords)()
            CBash.GetREGNRecords(self._CollectionIndex, self._ModName, cRecords)
            return [REGNRecord(self._CollectionIndex, self._ModName, x.contents.value) for x in cRecords]
        return []
    @property
    def CELL(self):
        numRecords = CBash.GetNumCELLRecords(self._CollectionIndex, self._ModName)
        if(numRecords > 0):
            cRecords = (POINTER(c_uint) * numRecords)()
            CBash.GetCELLRecords(self._CollectionIndex, self._ModName, cRecords)
            return [CELLRecord(self._CollectionIndex, self._ModName, x.contents.value) for x in cRecords]
        return []
    @property
    def WRLD(self):
        numRecords = CBash.GetNumWRLDRecords(self._CollectionIndex, self._ModName)
        if(numRecords > 0):
            cRecords = (POINTER(c_uint) * numRecords)()
            CBash.GetWRLDRecords(self._CollectionIndex, self._ModName, cRecords)
            return [WRLDRecord(self._CollectionIndex, self._ModName, x.contents.value) for x in cRecords]
        return []
    @property
    def DIAL(self):
        numRecords = CBash.GetNumDIALRecords(self._CollectionIndex, self._ModName)
        if(numRecords > 0):
            cRecords = (POINTER(c_uint) * numRecords)()
            CBash.GetDIALRecords(self._CollectionIndex, self._ModName, cRecords)
            return [DIALRecord(self._CollectionIndex, self._ModName, x.contents.value) for x in cRecords]
        return []
    @property
    def QUST(self):
        numRecords = CBash.GetNumQUSTRecords(self._CollectionIndex, self._ModName)
        if(numRecords > 0):
            cRecords = (POINTER(c_uint) * numRecords)()
            CBash.GetQUSTRecords(self._CollectionIndex, self._ModName, cRecords)
            return [QUSTRecord(self._CollectionIndex, self._ModName, x.contents.value) for x in cRecords]
        return []
    @property
    def IDLE(self):
        numRecords = CBash.GetNumIDLERecords(self._CollectionIndex, self._ModName)
        if(numRecords > 0):
            cRecords = (POINTER(c_uint) * numRecords)()
            CBash.GetIDLERecords(self._CollectionIndex, self._ModName, cRecords)
            return [IDLERecord(self._CollectionIndex, self._ModName, x.contents.value) for x in cRecords]
        return []
    @property
    def PACK(self):
        numRecords = CBash.GetNumPACKRecords(self._CollectionIndex, self._ModName)
        if(numRecords > 0):
            cRecords = (POINTER(c_uint) * numRecords)()
            CBash.GetPACKRecords(self._CollectionIndex, self._ModName, cRecords)
            return [PACKRecord(self._CollectionIndex, self._ModName, x.contents.value) for x in cRecords]
        return []
    @property
    def CSTY(self):
        numRecords = CBash.GetNumCSTYRecords(self._CollectionIndex, self._ModName)
        if(numRecords > 0):
            cRecords = (POINTER(c_uint) * numRecords)()
            CBash.GetCSTYRecords(self._CollectionIndex, self._ModName, cRecords)
            return [CSTYRecord(self._CollectionIndex, self._ModName, x.contents.value) for x in cRecords]
        return []
    @property
    def LSCR(self):
        numRecords = CBash.GetNumLSCRRecords(self._CollectionIndex, self._ModName)
        if(numRecords > 0):
            cRecords = (POINTER(c_uint) * numRecords)()
            CBash.GetLSCRRecords(self._CollectionIndex, self._ModName, cRecords)
            return [LSCRRecord(self._CollectionIndex, self._ModName, x.contents.value) for x in cRecords]
        return []
    @property
    def LVSP(self):
        numRecords = CBash.GetNumLVSPRecords(self._CollectionIndex, self._ModName)
        if(numRecords > 0):
            cRecords = (POINTER(c_uint) * numRecords)()
            CBash.GetLVSPRecords(self._CollectionIndex, self._ModName, cRecords)
            return [LVSPRecord(self._CollectionIndex, self._ModName, x.contents.value) for x in cRecords]
        return []
    @property
    def ANIO(self):
        numRecords = CBash.GetNumANIORecords(self._CollectionIndex, self._ModName)
        if(numRecords > 0):
            cRecords = (POINTER(c_uint) * numRecords)()
            CBash.GetANIORecords(self._CollectionIndex, self._ModName, cRecords)
            return [ANIORecord(self._CollectionIndex, self._ModName, x.contents.value) for x in cRecords]
        return []
    @property
    def WATR(self):
        numRecords = CBash.GetNumWATRRecords(self._CollectionIndex, self._ModName)
        if(numRecords > 0):
            cRecords = (POINTER(c_uint) * numRecords)()
            CBash.GetWATRRecords(self._CollectionIndex, self._ModName, cRecords)
            return [WATRRecord(self._CollectionIndex, self._ModName, x.contents.value) for x in cRecords]
        return []
    @property
    def EFSH(self):
        numRecords = CBash.GetNumEFSHRecords(self._CollectionIndex, self._ModName)
        if(numRecords > 0):
            cRecords = (POINTER(c_uint) * numRecords)()
            CBash.GetEFSHRecords(self._CollectionIndex, self._ModName, cRecords)
            return [EFSHRecord(self._CollectionIndex, self._ModName, x.contents.value) for x in cRecords]
        return []
    ##Aggregate properties. Useful for reading, and basic editting, but not so much for copying since it doesn't keep track of parenting
    @property
    def CELLS(self):
        cells = self.CELL
        for world in self.WRLD:
            cell = world.CELL
            if(cell): cells = cells + [cell]
            cells = cells + world.CELLS
        return cells
    @property
    def INFOS(self):
        infos = []
        for dial in self.DIAL:
            infos = infos + dial.INFO
        return infos
    @property
    def ACHRS(self):
        achrs = []
        for cell in self.CELL:
            achrs = achrs + cell.ACHR
        for world in self.WRLD:
            cell = world.CELL
            if(cell): achrs = achrs + cell.ACHR
            for cell in world.CELLS:
                achrs = achrs + cell.ACHR
        return achrs
    @property
    def ACRES(self):
        acres = []
        for cell in self.CELL:
            acres = acres + cell.ACRE
        for world in self.WRLD:
            cell = world.CELL
            if(cell): acres = acres + cell.ACRE
            for cell in world.CELLS:
                acres = acres + cell.ACRE
        return acres
    @property
    def REFRS(self):
        refrs = []
        for cell in self.CELL:
            refrs = refrs + cell.REFR
        for world in self.WRLD:
            cell = world.CELL
            if(cell): refrs = refrs + cell.REFR
            for cell in world.CELLS:
                refrs = refrs + cell.REFR
        return refrs
    @property
    def PGRDS(self):
        pgrds = []
        for cell in self.CELL:
            pgrd = cell.PGRD
            if(pgrd): pgrds = pgrds + [pgrd]
        for world in self.WRLD:
            cell = world.CELL
            if(cell):
                pgrd = cell.PGRD
                if(pgrd): pgrds = pgrds + [pgrd]
            for cell in world.CELLS:
                pgrd = cell.PGRD
                if(pgrd): pgrds = pgrds + [pgrd]
        return pgrds
    @property
    def LANDS(self):
        lands = []
        for cell in self.CELL:
            land = cell.LAND
            if(land): lands = lands + [land]
        for world in self.WRLD:
            cell = world.CELL
            if(cell):
                land = cell.LAND
                if(land): lands = lands + [land]
            for cell in world.CELLS:
                land = cell.LAND
                if(land): lands = lands + [land]
        return lands
    @property
    def ROADS(self):
        roads = []
        for world in self.WRLD:
            road = world.ROAD
            if(road): roads = roads + [road]
        return roads
    @property
    def tops(self):
        return dict((("GMST", self.GMST),("GLOB", self.GLOB),("CLAS", self.CLAS),("FACT", self.FACT),
                     ("HAIR", self.HAIR),("EYES", self.EYES),("RACE", self.RACE),("SOUN", self.SOUN),
                     ("SKIL", self.SKIL),("MGEF", self.MGEF),("SCPT", self.SCPT),("LTEX", self.LTEX),
                     ("ENCH", self.ENCH),("SPEL", self.SPEL),("BSGN", self.BSGN),("ACTI", self.ACTI),
                     ("APPA", self.APPA),("ARMO", self.ARMO),("BOOK", self.BOOK),("CLOT", self.CLOT),
                     ("CONT", self.CONT),("DOOR", self.DOOR),("INGR", self.INGR),("LIGH", self.LIGH),
                     ("MISC", self.MISC),("STAT", self.STAT),("GRAS", self.GRAS),("TREE", self.TREE),
                     ("FLOR", self.FLOR),("FURN", self.FURN),("WEAP", self.WEAP),("AMMO", self.AMMO),
                     ("NPC_", self.NPC_),("CREA", self.CREA),("LVLC", self.LVLC),("SLGM", self.SLGM),
                     ("KEYM", self.KEYM),("ALCH", self.ALCH),("SBSP", self.SBSP),("SGST", self.SGST),
                     ("LVLI", self.LVLI),("WTHR", self.WTHR),("CLMT", self.CLMT),("REGN", self.REGN),
                     ("CELL", self.CELL),("WRLD", self.WRLD),("DIAL", self.DIAL),("QUST", self.QUST),
                     ("IDLE", self.IDLE),("PACK", self.PACK),("CSTY", self.CSTY),("LSCR", self.LSCR),
                     ("LVSP", self.LVSP),("ANIO", self.ANIO),("WATR", self.WATR),("EFSH", self.EFSH)))
    @property
    def aggregates(self):
        return dict((("GMST", self.GMST),("GLOB", self.GLOB),("CLAS", self.CLAS),("FACT", self.FACT),
                     ("HAIR", self.HAIR),("EYES", self.EYES),("RACE", self.RACE),("SOUN", self.SOUN),
                     ("SKIL", self.SKIL),("MGEF", self.MGEF),("SCPT", self.SCPT),("LTEX", self.LTEX),
                     ("ENCH", self.ENCH),("SPEL", self.SPEL),("BSGN", self.BSGN),("ACTI", self.ACTI),
                     ("APPA", self.APPA),("ARMO", self.ARMO),("BOOK", self.BOOK),("CLOT", self.CLOT),
                     ("CONT", self.CONT),("DOOR", self.DOOR),("INGR", self.INGR),("LIGH", self.LIGH),
                     ("MISC", self.MISC),("STAT", self.STAT),("GRAS", self.GRAS),("TREE", self.TREE),
                     ("FLOR", self.FLOR),("FURN", self.FURN),("WEAP", self.WEAP),("AMMO", self.AMMO),
                     ("NPC_", self.NPC_),("CREA", self.CREA),("LVLC", self.LVLC),("SLGM", self.SLGM),
                     ("KEYM", self.KEYM),("ALCH", self.ALCH),("SBSP", self.SBSP),("SGST", self.SGST),
                     ("LVLI", self.LVLI),("WTHR", self.WTHR),("CLMT", self.CLMT),("REGN", self.REGN),
                     ("CELL", self.CELLS),("ACHR", self.ACHRS),("ACRE", self.ACRES),("REFR", self.REFRS),
                     ("PGRD", self.PGRDS),("LAND", self.LANDS),("WRLD", self.WRLD),("ROAD", self.ROADS),
                     ("DIAL", self.DIAL),("INFO", self.INFOS),("QUST", self.QUST),("IDLE", self.IDLE),
                     ("PACK", self.PACK),("CSTY", self.CSTY),("LSCR", self.LSCR),("LVSP", self.LVSP),
                     ("ANIO", self.ANIO),("WATR", self.WATR),("EFSH", self.EFSH)))


 
class Collection:
    """Collection of esm/esp's."""

    def __init__(self, recordID=None, ModsPath="."):
        if recordID:
            self._CollectionIndex = recordID
        else:
            self._CollectionIndex = CBash.NewCollection(ModsPath)
        self._ModIndex = -1
        CBash.GetModName.restype = c_char_p

    def addMod(self, ModName, CreateIfNotExist=False):
        if(CBash.AddMod(self._CollectionIndex, ModName, CreateIfNotExist) != -1):
            return ModFile(self._CollectionIndex, ModName)
        return None

    def minimalLoad(self, LoadMasters=False):
        CBash.MinimalLoad(self._CollectionIndex, LoadMasters)
        
    def fullLoad(self, LoadMasters=False):
        CBash.FullLoad(self._CollectionIndex, LoadMasters)

    def UpdateReferences(self, origFid, newFid):
        if not isinstance(origFid, int): return 0
        if not isinstance(newFid, int): return 0
        count = 0
        for modFile in self:
            count = count + modFile.UpdateReferences(origFid, newFid)
        return count
    def close(self):
        CBash.Close(self._CollectionIndex)

    def __del__(self):
        CBash.DeleteCollection(self._CollectionIndex)

    def __iter__(self):
        self._ModIndex = -1
        return self

    def __len__(self):
        return CBash.GetNumMods(self._CollectionIndex)

    def next(self):
        self._ModIndex = self._ModIndex + 1
        if self._ModIndex >= CBash.GetNumMods(self._CollectionIndex):
            raise StopIteration
        return ModFile(self._CollectionIndex, CBash.GetModName(self._CollectionIndex, self._ModIndex))

    def __getitem__(self, ModIndex):
        if(ModIndex < 0 or ModIndex >= CBash.GetNumMods(self._CollectionIndex)):
            raise IndexError
        else:
            return ModFile(self._CollectionIndex, CBash.GetModName(self._CollectionIndex, ModIndex))

    def getChangedMods(self):
        return CBash.GetChangedMods(self._CollectionIndex)

    def safeSaveMod(self, ModName):
        return CBash.SafeSaveMod(self._CollectionIndex, ModName)

    def safeSaveAllChangedMods(self):
        return CBash.SafeSaveAllChangedMods(self._recordID)    