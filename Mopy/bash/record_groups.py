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
#  Wrye Bash copyright (C) 2005-2009 Wrye, 2010-2019 Wrye Bash Team
#  https://github.com/wrye-bash
#
# =============================================================================

"""Classes that group records."""
# Python imports
from operator import itemgetter
# Wrye Bash imports
from brec import ModReader, RecordHeader
from bolt import sio, struct_pack, struct_unpack
import bosh # for modInfos
import bush # for fallout3/nv fsName
from exception import AbstractError, ArgumentError, ModError

# Tes3 Group/Top Types --------------------------------------------------------
groupTypes = [
    _(u'Top (Type)'),
    _(u'World Children'),
    _(u'Int Cell Block'),
    _(u'Int Cell Sub-Block'),
    _(u'Ext Cell Block'),
    _(u'Ext Cell Sub-Block'),
    _(u'Cell Children'),
    _(u'Topic Children'),
    _(u'Cell Persistent Children'),
    _(u'Cell Temporary Children'),
    _(u'Cell Visible Distant Children'),
]

class MobBase(object):
    """Group of records and/or subgroups. This basic implementation does not
    support unpacking, but can report its number of records and be written."""

    __slots__ = ['header','size','label','groupType','stamp','debug','data',
                 'changed','numRecords','loadFactory','inName']

    def __init__(self, header, loadFactory, ins=None, do_unpack=False):
        """Initialize."""
        self.header = header
        if header.recType == 'GRUP':
            self.size,self.label,self.groupType,self.stamp = (
                header.size,header.label,header.groupType,header.stamp)
        else:
            # Yes it's weird, but this is how it needs to work
            self.size,self.label,self.groupType,self.stamp = (
                header.size,header.flags1,header.fid,header.flags2)
        self.debug = False
        self.data = None
        self.changed = False
        self.numRecords = -1
        self.loadFactory = loadFactory
        self.inName = ins and ins.inName
        if ins: self.load(ins, do_unpack)

    def load(self, ins=None, do_unpack=False):
        """Load data from ins stream or internal data buffer."""
        if self.debug: print u'GRUP load:',self.label
        #--Read, but don't analyze.
        if not do_unpack:
            self.data = ins.read(self.size - self.header.__class__.rec_header_size, type(self))
        #--Analyze ins.
        elif ins is not None:
            self.loadData(ins,
                          ins.tell() + self.size - self.header.__class__.rec_header_size)
        #--Analyze internal buffer.
        else:
            with self.getReader() as reader:
                self.loadData(reader,reader.size)
        #--Discard raw data?
        if do_unpack:
            self.data = None
            self.setChanged()

    def loadData(self,ins,endPos):
        """Loads data from input stream. Called by load()."""
        raise AbstractError

    def setChanged(self,value=True):
        """Sets changed attribute to value. [Default = True.]"""
        self.changed = value

    def getSize(self):
        """Returns size (including size of any group headers)."""
        if self.changed: raise AbstractError
        return self.size

    def getNumRecords(self,includeGroups=True):
        """Returns number of records, including self (if plusSelf), unless
        there's no subrecords, in which case, it returns 0."""
        if self.changed:
            raise AbstractError
        elif self.numRecords > -1: #--Cached value.
            return self.numRecords
        elif not self.data: #--No data >> no records, not even self.
            self.numRecords = 0
            return self.numRecords
        else:
            numSubRecords = 0
            reader = self.getReader()
            errLabel = groupTypes[self.groupType]
            readerAtEnd = reader.atEnd
            readerRecHeader = reader.unpackRecHeader
            readerSeek = reader.seek
            while not readerAtEnd(reader.size,errLabel):
                header = readerRecHeader()
                recType,size = header.recType,header.size
                if recType == 'GRUP': size = 0
                readerSeek(size,1)
                numSubRecords += 1
            self.numRecords = numSubRecords + includeGroups
            return self.numRecords

    def dump(self,out):
        """Dumps record header and data into output file stream."""
        if self.changed:
            raise AbstractError
        if self.numRecords == -1:
            self.getNumRecords()
        if self.numRecords > 0:
            self.header.size = self.size
            out.write(self.header.pack())
            out.write(self.data)

    def getReader(self):
        """Returns a ModReader wrapped around self.data."""
        return ModReader(self.inName,sio(self.data))

    def convertFids(self,mapper,toLong):
        """Converts fids between formats according to mapper.
        toLong should be True if converting to long format or False if
        converting to short format."""
        raise AbstractError

    def updateRecords(self,block,mapper,toLong):
        """Looks through all of the records in 'block', and updates any
        records in self that exist with the data in 'block'."""
        raise AbstractError

#------------------------------------------------------------------------------
class MobObjects(MobBase):
    """Represents a top level group consisting of one type of record only. I.e.
    all top groups except CELL, WRLD and DIAL."""

    def __init__(self, header, loadFactory, ins=None, do_unpack=False):
        """Initialize."""
        self.records = []
        self.id_records = {}
        MobBase.__init__(self, header, loadFactory, ins, do_unpack)

    def loadData(self,ins,endPos):
        """Loads data from input stream. Called by load()."""
        expType = self.label
        recClass = self.loadFactory.getRecClass(expType)
        errLabel = expType + u' Top Block'
        records = self.records
        insAtEnd = ins.atEnd
        insRecHeader = ins.unpackRecHeader
        recordsAppend = records.append
        while not insAtEnd(endPos,errLabel):
            #--Get record info and handle it
            header = insRecHeader()
            recType = header.recType
            if recType != expType:
                raise ModError(ins.inName,u'Unexpected %s record in %s group.'
                               % (recType,expType))
            record = recClass(header,ins,True)
            recordsAppend(record)
        self.setChanged()

    def getActiveRecords(self):
        """Returns non-ignored records."""
        return [record for record in self.records if not record.flags1.ignored]

    def getNumRecords(self,includeGroups=True):
        """Returns number of records, including self."""
        numRecords = len(self.records)
        if numRecords: numRecords += includeGroups #--Count self
        self.numRecords = numRecords
        return numRecords

    def getSize(self):
        """Returns size (including size of any group headers)."""
        if not self.changed:
            return self.size
        else:
            hsize = RecordHeader.rec_header_size
            return hsize + sum(
                (hsize + record.getSize()) for record in self.records)

    def dump(self,out):
        """Dumps group header and then records."""
        if not self.changed:
            out.write(RecordHeader('GRUP',self.size, self.label, 0,
                                   self.stamp).pack())
            out.write(self.data)
        else:
            size = self.getSize()
            if size == RecordHeader.rec_header_size: return
            out.write(
                RecordHeader('GRUP', size, self.label, 0, self.stamp).pack())
            for record in self.records:
                record.dump(out)

    def updateMasters(self,masters):
        """Updates set of master names according to masters actually used."""
        for record in self.records:
            record.updateMasters(masters)

    def convertFids(self,mapper,toLong):
        """Converts fids between formats according to mapper.
        toLong should be True if converting to long format or False if
        converting to short format."""
        for record in self.records:
            record.convertFids(mapper,toLong)
        self.id_records.clear()

    def indexRecords(self):
        """Indexes records by fid."""
        self.id_records.clear()
        for record in self.records:
            self.id_records[record.fid] = record

    def getRecord(self,fid,default=None):
        """Gets record with corresponding id.
        If record doesn't exist, returns None."""
        if not self.records: return default
        if not self.id_records: self.indexRecords()
        return self.id_records.get(fid,default)

    def getRecordByEid(self,eid,default=None):
        """Gets record by eid, or returns default."""
        if not self.records: return default
        for record in self.records:
            if record.eid == eid:
                return record
        else:
            return default

    def setRecord(self,record):
        """Adds record to record list and indexed."""
        if self.records and not self.id_records:
            self.indexRecords()
        record_id = record.fid
        if record.isKeyedByEid:
            if record_id == (bosh.modInfos.masterName, 0):
                record_id = record.eid
        if record_id in self.id_records:
            oldRecord = self.id_records[record_id]
            index = self.records.index(oldRecord)
            self.records[index] = record
        else:
            self.records.append(record)
        self.id_records[record_id] = record

    def keepRecords(self,keepIds):
        """Keeps records with fid in set keepIds. Discards the rest."""
        self.records = [record for record in self.records if (record.fid == (
            record.isKeyedByEid and bosh.modInfos.masterName,
            0) and record.eid in keepIds) or record.fid in keepIds]
        self.id_records.clear()
        self.setChanged()

    def updateRecords(self,srcBlock,mapper,mergeIds):
        """Looks through all of the records in 'srcBlock', and updates any
        records in self that exist within the data in 'block'."""
        fids = set([record.fid for record in self.records])
        for record in srcBlock.getActiveRecords():
            if mapper(record.fid) in fids:
                record = record.getTypeCopy(mapper)
                self.setRecord(record)
                mergeIds.discard(record.fid)

#------------------------------------------------------------------------------
class MobDials(MobObjects):
    """DIAL top block of mod file."""

    def loadData(self,ins,endPos):
        """Loads data from input stream. Called by load()."""
        expType = self.label
        recClass = self.loadFactory.getRecClass(expType)
        errLabel = expType + u' Top Block'
        records = self.records
        insAtEnd = ins.atEnd
        insRecHeader = ins.unpackRecHeader
        recordsAppend = records.append
        loadGetRecClass = self.loadFactory.getRecClass
        record = None
        recordLoadInfos = None
        while not insAtEnd(endPos,errLabel):
            #--Get record info and handle it
            header = insRecHeader()
            recType = header.recType
            if recType == expType:
                record = recClass(header,ins,True)
                recordLoadInfos = record.loadInfos
                recordsAppend(record)
            elif recType == 'GRUP':
                (size, groupType, stamp) = (header.size, header.groupType,
                                            header.stamp)
                if groupType == 7:
                    try: # record/recordLoadInfos should be initialized in 'if'
                        record.infoStamp = stamp
                        infoClass = loadGetRecClass('INFO')
                        if infoClass:
                            recordLoadInfos(ins, ins.tell() + size -
                                            header.__class__.rec_header_size,
                                            infoClass)
                        else:
                            ins.seek(ins.tell() + size - header.__class__.rec_header_size)
                    except AttributeError:
                        ModError(self.inName, u'Malformed Plugin: Exterior '
                                 u'CELL subblock before worldspace GRUP')
                else:
                    raise ModError(self.inName,
                                   u'Unexpected subgroup %d in DIAL group.'
                                   % groupType)
            else:
                raise ModError(self.inName,
                               u'Unexpected %s record in %s group.'
                               % (recType,expType))
        self.setChanged()

    def getSize(self):
        """Returns size of records plus group and record headers."""
        if not self.changed:
            return self.size
        hsize = RecordHeader.rec_header_size
        size = hsize
        for record in self.records:
            size += hsize + record.getSize()
            if record.infos:
                size += hsize + sum(
                    hsize + info.getSize() for info in record.infos)
        return size

    def getNumRecords(self,includeGroups=1):
        """Returns number of records, including self plus info records."""
        self.numRecords = (
            len(self.records) + includeGroups * bool(self.records) +
            sum((includeGroups + len(x.infos)) for x in self.records if
                x.infos)
        )
        return self.numRecords

#------------------------------------------------------------------------------
class MobCell(MobBase):
    """Represents cell block structure -- including the cell and all
    subrecords."""

    __slots__ = MobBase.__slots__ + ['cell','persistent','distant','temp',
                                     'land','pgrd']

    def __init__(self, header, loadFactory, cell, ins=None, do_unpack=False):
        """Initialize."""
        self.cell = cell
        self.persistent = []
        self.distant = []
        self.temp = []
        self.land = None
        self.pgrd = None
        MobBase.__init__(self, header, loadFactory, ins, do_unpack)

    def loadData(self,ins,endPos):
        """Loads data from input stream. Called by load()."""
        cellType_class = self.loadFactory.getCellTypeClass()
        persistent,temp,distant = self.persistent,self.temp,self.distant
        insAtEnd = ins.atEnd
        insRecHeader = ins.unpackRecHeader
        cellGet = cellType_class.get
        persistentAppend = persistent.append
        tempAppend = temp.append
        distantAppend = distant.append
        insSeek = ins.seek
        while not insAtEnd(endPos,'Cell Block'):
            subgroupLoaded = [False,False,False]
            header = insRecHeader()
            recType = header.recType
            recClass = cellGet(recType)
            if recType == 'GRUP':
                groupType = header.groupType
                if groupType not in (8, 9, 10):
                    raise ModError(self.inName,
                                   u'Unexpected subgroup %d in cell children '
                                   u'group.' % groupType)
                if subgroupLoaded[groupType - 8]:
                    raise ModError(self.inName,
                                   u'Extra subgroup %d in cell children '
                                   u'group.' % groupType)
                else:
                    subgroupLoaded[groupType - 8] = True
            elif recType not in cellType_class:
                raise ModError(self.inName,
                               u'Unexpected %s record in cell children '
                               u'group.' % recType)
            elif not recClass:
                insSeek(header.size,1)
            elif recType in ('REFR','ACHR','ACRE'):
                record = recClass(header,ins,True)
                if   groupType ==  8: persistentAppend(record)
                elif groupType ==  9: tempAppend(record)
                elif groupType == 10: distantAppend(record)
            elif recType == 'LAND':
                self.land = recClass(header,ins,False)
            elif recType == 'PGRD':
                self.pgrd = recClass(header,ins,False)
        self.setChanged()

    def getSize(self):
        """Returns size (including size of any group headers)."""
        return RecordHeader.rec_header_size + self.cell.getSize() + \
               self.getChildrenSize()

    def getChildrenSize(self):
        """Returns size of all children, including the group header.  This
        does not include the cell itself."""
        size = self.getPersistentSize() + self.getTempSize() + \
               self.getDistantSize()
        return size + RecordHeader.rec_header_size * bool(size)

    def getPersistentSize(self):
        """Returns size of all persistent children, including the persistent
        children group."""
        hsize = RecordHeader.rec_header_size
        size = sum(hsize + x.getSize() for x in self.persistent)
        return size + hsize * bool(size)

    def getTempSize(self):
        """Returns size of all temporary children, including the temporary
        children group."""
        hsize = RecordHeader.rec_header_size
        size = sum(hsize + x.getSize() for x in self.temp)
        if self.pgrd: size += hsize + self.pgrd.getSize()
        if self.land: size += hsize + self.land.getSize()
        return size + hsize * bool(size)

    def getDistantSize(self):
        """Returns size of all distant children, including the distant
        children group."""
        hsize = RecordHeader.rec_header_size
        size = sum(hsize + x.getSize() for x in self.distant)
        return size + hsize * bool(size)

    def getNumRecords(self,includeGroups=True):
        """Returns number of records, including self and all children."""
        count = 1 + includeGroups # Cell GRUP and CELL record
        if self.persistent:
            count += len(self.persistent) + includeGroups
        if self.temp or self.pgrd or self.land:
            count += len(self.temp) + includeGroups
            count += bool(self.pgrd) + bool(self.land)
        if self.distant:
            count += len(self.distant) + includeGroups
        return count

    def getBsb(self):
        """Returns tesfile block and sub-block indices for cells in this group.
        For interior cell, bsb is (blockNum,subBlockNum). For exterior cell,
        bsb is ((blockY,blockX),(subblockY,subblockX))."""
        cell = self.cell
        #--Interior cell
        if cell.flags.isInterior:
            baseFid = cell.fid & 0x00FFFFFF
            return baseFid%10, baseFid%100//10
        #--Exterior cell
        else:
            x,y = cell.posY,cell.posX
            if x is None: x = 0
            if y is None: y = 0
            return (x//32, y//32), (x//8, y//8)

    def dump(self,out):
        """Dumps group header and then records."""
        self.cell.getSize()
        self.cell.dump(out)
        childrenSize = self.getChildrenSize()
        if not childrenSize: return
        out.writeGroup(childrenSize,self.cell.fid,6,self.stamp)
        if self.persistent:
            out.writeGroup(self.getPersistentSize(),self.cell.fid,8,self.stamp)
            for record in self.persistent:
                record.dump(out)
        if self.temp or self.pgrd or self.land:
            out.writeGroup(self.getTempSize(),self.cell.fid,9,self.stamp)
            if self.pgrd:
                self.pgrd.dump(out)
            if self.land:
                self.land.dump(out)
            for record in self.temp:
                record.dump(out)
        if self.distant:
            out.writeGroup(self.getDistantSize(),self.cell.fid,10,self.stamp)
            for record in self.distant:
                record.dump(out)

    #--Fid manipulation, record filtering ----------------------------------
    def convertFids(self,mapper,toLong):
        """Converts fids between formats according to mapper.
        toLong should be True if converting to long format or False if
        converting to short format."""
        self.cell.convertFids(mapper,toLong)
        for record in self.temp:
            record.convertFids(mapper,toLong)
        for record in self.persistent:
            record.convertFids(mapper,toLong)
        for record in self.distant:
            record.convertFids(mapper,toLong)
        if self.land:
            self.land.convertFids(mapper,toLong)
        if self.pgrd:
            self.pgrd.convertFids(mapper,toLong)

    def updateMasters(self,masters):
        """Updates set of master names according to masters actually used."""
        self.cell.updateMasters(masters)
        for record in self.persistent:
            record.updateMasters(masters)
        for record in self.distant:
            record.updateMasters(masters)
        for record in self.temp:
            record.updateMasters(masters)
        if self.land:
            self.land.updateMasters(masters)
        if self.pgrd:
            self.pgrd.updateMasters(masters)

    def updateRecords(self,srcBlock,mapper,mergeIds):
        """Updates any records in 'self' that exist in 'srcBlock'."""
        mergeDiscard = mergeIds.discard
        selfGetter = self.__getattribute__
        srcGetter = srcBlock.__getattribute__
        selfSetter = self.__setattr__
        for attr in ('cell','pgrd','land'):
            myRecord = selfGetter(attr)
            record = srcGetter(attr)
            if myRecord and record:
                if myRecord.fid != mapper(record.fid):
                    raise ArgumentError(u"Fids don't match! %08x, %08x" % (
                        myRecord.fid,record.fid))
                if not record.flags1.ignored:
                    record = record.getTypeCopy(mapper)
                    selfSetter(attr,record)
                    mergeDiscard(record.fid)
        for attr in ('persistent','temp','distant'):
            recordList = selfGetter(attr)
            fids = dict(
                (record.fid,index) for index,record in enumerate(recordList))
            for record in srcGetter(attr):
                if not record.flags1.ignored and mapper(record.fid) in fids:
                    record = record.getTypeCopy(mapper)
                    recordList[fids[record.fid]] = record
                    mergeDiscard(record.fid)

    def keepRecords(self,keepIds):
        """Keeps records with fid in set keepIds. Discards the rest."""
        if self.pgrd and self.pgrd.fid not in keepIds:
            self.pgrd = None
        if self.land and self.land.fid not in keepIds:
            self.land = None
        self.temp       = [x for x in self.temp if x.fid in keepIds]
        self.persistent = [x for x in self.persistent if x.fid in keepIds]
        self.distant    = [x for x in self.distant if x.fid in keepIds]
        if self.pgrd or self.land or self.persistent or self.temp or \
                self.distant:
            keepIds.add(self.cell.fid)
        self.setChanged()

#------------------------------------------------------------------------------
class MobCells(MobBase):
    """A block containing cells. Subclassed by MobWorld and MobICells.

    Note that "blocks" here only roughly match the file block structure.

    "Bsb" is a tuple of the file (block,subblock) labels. For interior
    cells, bsbs are tuples of two numbers, while for exterior cells, bsb labels
    are tuples of grid tuples."""

    def __init__(self, header, loadFactory, ins=None, do_unpack=False):
        """Initialize."""
        self.cellBlocks = [] #--Each cellBlock is a cell and its related
        # records.
        self.id_cellBlock = {}
        MobBase.__init__(self, header, loadFactory, ins, do_unpack)

    def indexRecords(self):
        """Indexes records by fid."""
        self.id_cellBlock = dict((x.cell.fid,x) for x in self.cellBlocks)

    def setCell(self,cell):
        """Adds record to record list and indexed."""
        if self.cellBlocks and not self.id_cellBlock:
            self.indexRecords()
        fid = cell.fid
        if fid in self.id_cellBlock:
            self.id_cellBlock[fid].cell = cell
        else:
            cellBlock = MobCell(RecordHeader('GRUP', 0, 0, 6, self.stamp),
                                self.loadFactory, cell)
            cellBlock.setChanged()
            self.cellBlocks.append(cellBlock)
            self.id_cellBlock[fid] = cellBlock

    def getUsedBlocks(self):
        """Returns a set of blocks that exist in this group."""
        return set(x.getBsb()[0] for x in self.cellBlocks)

    def getUsedSubblocks(self):
        """Returns a set of block/sub-blocks that exist in this group."""
        return set(x.getBsb() for x in self.cellBlocks)

    def getBsbSizes(self):
        """Returns the total size of the block, but also returns a
        dictionary containing the sizes of the individual block,subblocks."""
        bsbCellBlocks = [(x.getBsb(),x) for x in self.cellBlocks]
        bsbCellBlocks.sort(key = lambda y: y[1].cell.fid)
        bsbCellBlocks.sort(key = itemgetter(0))
        bsb_size = {}
        hsize = RecordHeader.rec_header_size
        totalSize = hsize
        bsb_setDefault = bsb_size.setdefault
        for bsb,cellBlock in bsbCellBlocks:
            cellBlockSize = cellBlock.getSize()
            totalSize += cellBlockSize
            bsb0 = (bsb[0],None) #--Block group
            bsb_setDefault(bsb0,hsize)
            if bsb_setDefault(bsb, hsize) == hsize:
                bsb_size[bsb0] += hsize
            bsb_size[bsb] += cellBlockSize
            bsb_size[bsb0] += cellBlockSize
        totalSize += hsize * len(bsb_size)
        return totalSize,bsb_size,bsbCellBlocks

    def dumpBlocks(self,out,bsbCellBlocks,bsb_size,blockGroupType,
                   subBlockGroupType):
        """Dumps the cell blocks and their block and sub-block groups to
        out."""
        curBlock = None
        curSubblock = None
        stamp = self.stamp
        outWrite = out.write
        for bsb,cellBlock in bsbCellBlocks:
            (block,subblock) = bsb
            bsb0 = (block,None)
            if block != curBlock:
                curBlock,curSubblock = bsb0
                outWrite(RecordHeader('GRUP',bsb_size[bsb0],block,
                                      blockGroupType,stamp).pack())
            if subblock != curSubblock:
                curSubblock = subblock
                outWrite(RecordHeader('GRUP',bsb_size[bsb],subblock,
                                      subBlockGroupType,stamp).pack())
            cellBlock.dump(out)

    def getNumRecords(self,includeGroups=1):
        """Returns number of records, including self and all children."""
        count = sum(x.getNumRecords(includeGroups) for x in self.cellBlocks)
        if count and includeGroups:
            count += 1 + len(self.getUsedBlocks()) + len(
                self.getUsedSubblocks())
        return count

    #--Fid manipulation, record filtering ----------------------------------
    def keepRecords(self,keepIds):
        """Keeps records with fid in set keepIds. Discards the rest."""
        #--Note: this call will add the cell to keepIds if any of its
        # related records are kept.
        for cellBlock in self.cellBlocks: cellBlock.keepRecords(keepIds)
        self.cellBlocks = [x for x in self.cellBlocks if x.cell.fid in keepIds]
        self.id_cellBlock.clear()
        self.setChanged()

    def convertFids(self,mapper,toLong):
        """Converts fids between formats according to mapper.
        toLong should be True if converting to long format or False if
        converting to short format."""
        for cellBlock in self.cellBlocks:
            cellBlock.convertFids(mapper,toLong)

    def updateRecords(self,srcBlock,mapper,mergeIds):
        """Updates any records in 'self' that exist in 'srcBlock'."""
        if self.cellBlocks and not self.id_cellBlock:
            self.indexRecords()
        id_cellBlock = self.id_cellBlock
        id_Get = id_cellBlock.get
        for srcCellBlock in srcBlock.cellBlocks:
            fid = mapper(srcCellBlock.cell.fid)
            cellBlock = id_Get(fid)
            if cellBlock:
                cellBlock.updateRecords(srcCellBlock,mapper,mergeIds)

    def updateMasters(self,masters):
        """Updates set of master names according to masters actually used."""
        for cellBlock in self.cellBlocks:
            cellBlock.updateMasters(masters)

#------------------------------------------------------------------------------
class MobICells(MobCells):
    """Tes4 top block for interior cell records."""

    def loadData(self,ins,endPos):
        """Loads data from input stream. Called by load()."""
        expType = self.label
        recCellClass = self.loadFactory.getRecClass(expType)
        errLabel = expType + u' Top Block'
        cellBlocks = self.cellBlocks
        cell = None
        endBlockPos = endSubblockPos = 0
        unpackCellBlocks = self.loadFactory.getUnpackCellBlocks('CELL')
        insAtEnd = ins.atEnd
        insRecHeader = ins.unpackRecHeader
        cellBlocksAppend = cellBlocks.append
        selfLoadFactory = self.loadFactory
        insTell = ins.tell
        insSeek = ins.seek
        while not insAtEnd(endPos,errLabel):
            header = insRecHeader()
            recType = header.recType
            if recType == expType:
                if cell:
                    cellBlock = MobCell(header,selfLoadFactory,cell)
                    cellBlocksAppend(cellBlock)
                cell = recCellClass(header,ins,True)
                if insTell() > endBlockPos or insTell() > endSubblockPos:
                    raise ModError(self.inName,
                                   u'Interior cell <%X> %s outside of block '
                                   u'or subblock.' % (
                                       cell.fid,cell.eid))
            elif recType == 'GRUP':
                size,groupFid,groupType = header.size,header.label, \
                                          header.groupType
                delta = size - header.__class__.rec_header_size
                if groupType == 2: # Block number
                    endBlockPos = insTell() + delta
                elif groupType == 3: # Sub-block number
                    endSubblockPos = insTell() + delta
                elif groupType == 6: # Cell Children
                    if cell:
                        if groupFid != cell.fid:
                            raise ModError(self.inName,
                                           u'Cell subgroup (%X) does not '
                                           u'match CELL <%X> %s.' %
                                           (groupFid,cell.fid,cell.eid))
                        if unpackCellBlocks:
                            cellBlock = MobCell(header,selfLoadFactory,cell,
                                                ins,True)
                        else:
                            cellBlock = MobCell(header,selfLoadFactory,cell)
                            insSeek(delta,1)
                        cellBlocksAppend(cellBlock)
                        cell = None
                    else:
                        raise ModError(self.inName,
                                       u'Extra subgroup %d in CELL group.' %
                                       groupType)
                else:
                    raise ModError(self.inName,
                                   u'Unexpected subgroup %d in CELL group.'
                                   % groupType)
            else:
                raise ModError(self.inName,
                               u'Unexpected %s record in %s group.' % (
                                   recType,expType))
        self.setChanged()

    def dump(self,out):
        """Dumps group header and then records."""
        if not self.changed:
            out.write(self.header.pack())
            out.write(self.data)
        elif self.cellBlocks:
            (totalSize, bsb_size, blocks) = self.getBsbSizes()
            self.header.size = totalSize
            out.write(self.header.pack())
            self.dumpBlocks(out,blocks,bsb_size,2,3)

#------------------------------------------------------------------------------
class MobWorld(MobCells):
    def __init__(self, header, loadFactory, world, ins=None, do_unpack=False):
        """Initialize."""
        self.world = world
        self.worldCellBlock = None
        self.road = None
        MobCells.__init__(self, header, loadFactory, ins, do_unpack)

    def loadData(self,ins,endPos):
        """Loads data from input stream. Called by load()."""
        cellType_class = self.loadFactory.getCellTypeClass()
        errLabel = u'World Block'
        cell = None
        block = None
        # subblock = None # unused var
        endBlockPos = endSubblockPos = 0
        cellBlocks = self.cellBlocks
        unpackCellBlocks = self.loadFactory.getUnpackCellBlocks('WRLD')
        insAtEnd = ins.atEnd
        insRecHeader = ins.unpackRecHeader
        cellGet = cellType_class.get
        insSeek = ins.seek
        insTell = ins.tell
        selfLoadFactory = self.loadFactory
        cellBlocksAppend = cellBlocks.append
        isFallout = bush.game.fsName != u'Oblivion'
        cells = {}
        while not insAtEnd(endPos,errLabel):
            curPos = insTell()
            if curPos >= endBlockPos:
                block = None
            if curPos >= endSubblockPos:
                pass # subblock = None # unused var
            #--Get record info and handle it
            header = insRecHeader()
            recType,size = header.recType,header.size
            delta = size - header.__class__.rec_header_size
            recClass = cellGet(recType)
            if recType == 'ROAD':
                if not recClass: insSeek(size,1)
                else: self.road = recClass(header,ins,True)
            elif recType == 'CELL':
                if cell:
                    cellBlock = MobCell(header,selfLoadFactory,cell)
                    if block:
                        cellBlocksAppend(cellBlock)
                    else:
                        if self.worldCellBlock:
                            raise ModError(self.inName,
                                           u'Extra exterior cell <%s> %s '
                                           u'before block group.' % (
                                               hex(cell.fid),cell.eid))
                        self.worldCellBlock = cellBlock
                cell = recClass(header,ins,True)
                if isFallout: cells[cell.fid] = cell
                if block:
                    if cell:
                        cellBlock = MobCell(header, selfLoadFactory, cell)
                        if block:
                            cellBlocksAppend(cellBlock)
                        else:
                            if self.worldCellBlock:
                                raise ModError(self.inName,
                                               u'Extra exterior cell <%s> %s '
                                               u'before block group.' % (
                                                   hex(cell.fid), cell.eid))
                            self.worldCellBlock = cellBlock
                    elif insTell() > endBlockPos or insTell() > endSubblockPos:
                        raise ModError(self.inName,
                                       u'Exterior cell <%s> %s after block or'
                                       u' subblock.' % (
                                           hex(cell.fid),cell.eid))
            elif recType == 'GRUP':
                groupFid,groupType = header.label,header.groupType
                if groupType == 4: # Exterior Cell Block
                    block = struct_unpack('2h', struct_pack('I', groupFid))
                    block = (block[1],block[0])
                    endBlockPos = insTell() + delta
                elif groupType == 5: # Exterior Cell Sub-Block
                    # we don't actually care what the sub-block is, since
                    # we never use that information here. So below was unused:
                    # subblock = structUnpack('2h',structPack('I',groupFid))
                    # subblock = (subblock[1],subblock[0]) # unused var
                    endSubblockPos = insTell() + delta
                elif groupType == 6: # Cell Children
                    if isFallout: cell = cells.get(groupFid,None)
                    if cell:
                        if groupFid != cell.fid:
                            raise ModError(self.inName,
                                           u'Cell subgroup (%s) does not '
                                           u'match CELL <%s> %s.' %
                                           (hex(groupFid),hex(cell.fid),
                                            cell.eid))
                        if unpackCellBlocks:
                            cellBlock = MobCell(header,selfLoadFactory,cell,
                                                ins,True)
                        else:
                            cellBlock = MobCell(header,selfLoadFactory,cell)
                            insSeek(delta,1)
                        if block:
                            cellBlocksAppend(cellBlock)
                        else:
                            if self.worldCellBlock:
                                raise ModError(self.inName,
                                               u'Extra exterior cell <%s> %s '
                                               u'before block group.' % (
                                                   hex(cell.fid),cell.eid))
                            self.worldCellBlock = cellBlock
                        cell = None
                    else:
                        raise ModError(self.inName,
                                       u'Extra cell children subgroup in '
                                       u'world children group.')
                else:
                    raise ModError(self.inName,
                                   u'Unexpected subgroup %d in world '
                                   u'children group.' % groupType)
            else:
                raise ModError(self.inName,
                               u'Unexpected %s record in world children '
                               u'group.' % recType)
        self.setChanged()

    def getNumRecords(self,includeGroups=True):
        """Returns number of records, including self and all children."""
        if not self.changed:
            return MobBase.getNumRecords(self)
        count = 1 + includeGroups #--world record & group
        count += bool(self.road)
        if self.worldCellBlock:
            count += self.worldCellBlock.getNumRecords(includeGroups)
        count += MobCells.getNumRecords(self,includeGroups)
        return count

    def dump(self,out):
        """Dumps group header and then records.  Returns the total size of
        the world block."""
        hsize = RecordHeader.rec_header_size
        worldSize = self.world.getSize() + hsize
        self.world.dump(out)
        if not self.changed:
            out.write(self.header.pack())
            out.write(self.data)
            return self.size + worldSize
        elif self.cellBlocks or self.road or self.worldCellBlock:
            (totalSize, bsb_size, blocks) = self.getBsbSizes()
            if self.road:
                totalSize += self.road.getSize() + hsize
            if self.worldCellBlock:
                totalSize += self.worldCellBlock.getSize()
            self.header.size = totalSize
            self.header.label = self.world.fid
            self.header.groupType = 1
            out.write(self.header.pack())
            if self.road:
                self.road.dump(out)
            if self.worldCellBlock:
                self.worldCellBlock.dump(out)
            self.dumpBlocks(out,blocks,bsb_size,4,5)
            return totalSize + worldSize
        else:
            return worldSize

    #--Fid manipulation, record filtering ----------------------------------
    def convertFids(self,mapper,toLong):
        """Converts fids between formats according to mapper.
        toLong should be True if converting to long format or False if
        converting to short format."""
        self.world.convertFids(mapper,toLong)
        if self.road:
            self.road.convertFids(mapper,toLong)
        if self.worldCellBlock:
            self.worldCellBlock.convertFids(mapper,toLong)
        MobCells.convertFids(self,mapper,toLong)

    def updateMasters(self,masters):
        """Updates set of master names according to masters actually used."""
        self.world.updateMasters(masters)
        if self.road:
            self.road.updateMasters(masters)
        if self.worldCellBlock:
            self.worldCellBlock.updateMasters(masters)
        MobCells.updateMasters(self,masters)

    def updateRecords(self,srcBlock,mapper,mergeIds):
        """Updates any records in 'self' that exist in 'srcBlock'."""
        selfGetter = self.__getattribute__
        srcGetter = srcBlock.__getattribute__
        selfSetter = self.__setattr__
        mergeDiscard = mergeIds.discard
        for attr in ('world','road'):
            myRecord = selfGetter(attr)
            record = srcGetter(attr)
            if myRecord and record:
                if myRecord.fid != mapper(record.fid):
                    raise ArgumentError(u"Fids don't match! %08x, %08x" % (
                        myRecord.fid,record.fid))
                if not record.flags1.ignored:
                    record = record.getTypeCopy(mapper)
                    selfSetter(attr,record)
                    mergeDiscard(record.fid)
        if self.worldCellBlock and srcBlock.worldCellBlock:
            self.worldCellBlock.updateRecords(srcBlock.worldCellBlock,mapper,
                                              mergeIds)
        MobCells.updateRecords(self,srcBlock,mapper,mergeIds)

    def keepRecords(self,keepIds):
        """Keeps records with fid in set keepIds. Discards the rest."""
        if self.road and self.road.fid not in keepIds:
            self.road = None
        if self.worldCellBlock:
            self.worldCellBlock.keepRecords(keepIds)
            if self.worldCellBlock.cell.fid not in keepIds:
                self.worldCellBlock = None
        MobCells.keepRecords(self,keepIds)
        if self.road or self.worldCellBlock or self.cellBlocks:
            keepIds.add(self.world.fid)

#------------------------------------------------------------------------------
class MobWorlds(MobBase):
    """Tes4 top block for world records and related roads and cells. Consists
    of world blocks."""

    def __init__(self, header, loadFactory, ins=None, do_unpack=False):
        """Initialize."""
        self.worldBlocks = []
        self.id_worldBlocks = {}
        self.orphansSkipped = 0
        MobBase.__init__(self, header, loadFactory, ins, do_unpack)

    def loadData(self,ins,endPos):
        """Loads data from input stream. Called by load()."""
        expType = self.label
        recWrldClass = self.loadFactory.getRecClass(expType)
        errLabel = expType + u' Top Block'
        worldBlocks = self.worldBlocks
        world = None
        insAtEnd = ins.atEnd
        insRecHeader = ins.unpackRecHeader
        insSeek = ins.seek
        selfLoadFactory = self.loadFactory
        worldBlocksAppend = worldBlocks.append
        isFallout = bush.game.fsName != u'Oblivion'
        worlds = {}
        while not insAtEnd(endPos,errLabel):
            #--Get record info and handle it
            header = insRecHeader()
            recType = header.recType
            if recType == expType:
                world = recWrldClass(header,ins,True)
                if isFallout: worlds[world.fid] = world
            elif recType == 'GRUP':
                groupFid,groupType = header.label,header.groupType
                if groupType != 1:
                    raise ModError(ins.inName,
                                   u'Unexpected subgroup %d in CELL group.'
                                   % groupType)
                if isFallout: world = worlds.get(groupFid,None)
                if not world:
                    #raise ModError(ins.inName,'Extra subgroup %d in WRLD
                    # group.' % groupType)
                    #--Orphaned world records. Skip over.
                    insSeek(header.size - header.__class__.rec_header_size,1)
                    self.orphansSkipped += 1
                    continue
                if groupFid != world.fid:
                    raise ModError(ins.inName,
                                   u'WRLD subgroup (%s) does not match WRLD '
                                   u'<%s> %s.' % (
                                   hex(groupFid),hex(world.fid),world.eid))
                worldBlock = MobWorld(header,selfLoadFactory,world,ins,True)
                worldBlocksAppend(worldBlock)
                world = None
            else:
                raise ModError(ins.inName,
                               u'Unexpected %s record in %s group.' % (
                                   recType,expType))

    def getSize(self):
        """Returns size (including size of any group headers)."""
        return RecordHeader.rec_header_size + sum(
            x.getSize() for x in self.worldBlocks)

    def dump(self,out):
        """Dumps group header and then records."""
        if not self.changed:
            out.write(self.header.pack())
            out.write(self.data)
        else:
            if not self.worldBlocks: return
            worldHeaderPos = out.tell()
            header = RecordHeader('GRUP', 0, self.label, 0, self.stamp)
            out.write(header.pack())
            totalSize = header.__class__.rec_header_size + sum(
                x.dump(out) for x in self.worldBlocks)
            out.seek(worldHeaderPos + 4)
            out.pack('I', totalSize)
            out.seek(worldHeaderPos + totalSize)

    def getNumRecords(self,includeGroups=True):
        """Returns number of records, including self and all children."""
        count = sum(x.getNumRecords(includeGroups) for x in self.worldBlocks)
        return count + includeGroups * bool(count)

    def convertFids(self,mapper,toLong):
        """Converts fids between formats according to mapper.
        toLong should be True if converting to long format or False if
        converting to short format."""
        for worldBlock in self.worldBlocks:
            worldBlock.convertFids(mapper,toLong)

    def indexRecords(self):
        """Indexes records by fid."""
        self.id_worldBlocks = dict((x.world.fid,x) for x in self.worldBlocks)

    def updateMasters(self,masters):
        """Updates set of master names according to masters actually used."""
        for worldBlock in self.worldBlocks:
            worldBlock.updateMasters(masters)

    def updateRecords(self,srcBlock,mapper,mergeIds):
        """Updates any records in 'self' that exist in 'srcBlock'."""
        if self.worldBlocks and not self.id_worldBlocks:
            self.indexRecords()
        id_worldBlocks = self.id_worldBlocks
        idGet = id_worldBlocks.get
        for srcWorldBlock in srcBlock.worldBlocks:
            worldBlock = idGet(mapper(srcWorldBlock.world.fid))
            if worldBlock:
                worldBlock.updateRecords(srcWorldBlock,mapper,mergeIds)

    def setWorld(self, world, worldcellblock=None):
        """Adds record to record list and indexed."""
        if self.worldBlocks and not self.id_worldBlocks:
            self.indexRecords()
        fid = world.fid
        if fid in self.id_worldBlocks:
            self.id_worldBlocks[fid].world = world
            self.id_worldBlocks[fid].worldCellBlock = worldcellblock
        else:
            worldBlock = MobWorld(RecordHeader('GRUP',0,0,1,self.stamp),
                                  self.loadFactory,world)
            worldBlock.setChanged()
            self.worldBlocks.append(worldBlock)
            self.id_worldBlocks[fid] = worldBlock

    def keepRecords(self,keepIds):
        """Keeps records with fid in set keepIds. Discards the rest."""
        for worldBlock in self.worldBlocks: worldBlock.keepRecords(keepIds)
        self.worldBlocks = [x for x in self.worldBlocks if
                            x.world.fid in keepIds]
        self.id_worldBlocks.clear()
        self.setChanged()
