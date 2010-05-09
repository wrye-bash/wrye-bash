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
#  Wrye Bash copyright (C) 2005, 2006, 2007, 2008, 2009 Wrye
#
# =============================================================================

"""This module provides a command line interface for working with Oblivion files
and environment. Functions are defined here and added to the callables
singleton. Callables.main() is then used to parse command line arguments.

Practice:
    While in theory this module is usable by anybody, no one but Wrye and
    Waruddar have made use of it, so it's become our own miscellaneous toolbin
    and testing environment. As a result, its contents tend to shift depending
    on what we're currently working on. However, the functions (init, dumpData)
    and classes (Callables) at the top are fairly reliably present and
    unchanging.

Rational Names:
    Rational names is a mod that "Rationalizes" names of many objects in the
    Oblivion world. Many of those names were generated here by functions working
    on the basis of the eid or pre-existing name. Naturally these tend to be
    use-once functions, but they also tended to be modified and then used again.
"""

# Imports ----------------------------------------------------------------------
#--Standard
import os
import re
import string
import struct
import cStringIO
import sys
import types
from operator import attrgetter,itemgetter

#--Local
import bosh
import bush
import bolt
from bolt import _, GPath, mainfunc

indent = 0
longest = 0

# Basics ----------------------------------------------------------------------
#------------------------------------------------------------------------------
def init(initLevel):
    """Initializes bosh environment to specified level. I.e., it initializes
    certain data arrays which can then be accessed by the function. It's typical
    to init to level 3, which gives access to all basic data arrays (plugins,
    modInfos and saveInfos.)

    initLevels:
        0: Settings
        1: plugins
        2: modInfos
        3: saveInfos"""
    #--Settings
    bosh.initDirs()
    bosh.initSettings(readOnly=True)
    bosh.oblivionIni = bosh.OblivionIni()
    #--MwIniFile (initLevel >= 1)
    if initLevel < 1: return
    bosh.oblivionIni = bosh.OblivionIni()
    #--ModInfos (initLevel >= 2)
    if initLevel < 2: return
    bosh.modInfos = bosh.ModInfos()
    bosh.modInfos.refresh()
    #--SaveInfos (initLevel >= 3)
    if initLevel < 3: return
    bosh.saveInfos = bosh.SaveInfos()
    bosh.saveInfos.refresh()
    #--Misc.
    if initLevel < 4: return
    bosh.screensData = bosh.ScreensData()
    bosh.screensData.refresh()

def readRecord(record, melSet=0, skipLabel=0):
    global longest
    global indent
    indent += 2
    if isinstance(record, bosh.MobCell):
        melSet = ['cell','persistent','distant','temp','land','pgrd']
    elif isinstance(record, bosh.MobWorld):
        melSet = ['cellBlocks','world','road','worldCellBlock']
    elif hasattr(record, 'melSet'):
        melSet = record.melSet.getSlotsUsed()
        if record.recType == 'DIAL':
            melSet += ['infoStamp','infos']
    elif hasattr(record, '__slots__'):
        melSet = getattr(record, '__slots__')
    elif hasattr(record, '__dict__'):
        melSet = getattr(record, '__dict__').keys()
    if hasattr(record,'setChanged'):
        record.setChanged()
    if hasattr(record, 'getHeader'):
        if 6 > longest: longest = 6
        attr = 'flags'
        print ' '*indent + attr.ljust(longest) + ' :', record.flags1.hex(), record.flags1.getTrueAttrs()
        attr = 'formID'
        print ' '*indent + attr.ljust(longest) + ' : ' + bosh.strFid(record.fid)
        attr = 'unk'
        print ' '*indent + attr.ljust(longest) + ' : %08X' % record.flags2
    for attr in melSet:
        if len(attr) > longest: longest = len(attr)
    for attr in melSet:
        if hasattr(record,attr):
            item = getattr(record, attr)
        else:
            item = record
        if attr == 'references':
            if isinstance(item, tuple):
                if item[0] is True:
                    attr = 'scro'
                    item = item[1]
                else:
                    attr = 'scrv'
                    item = item[1]
        if skipLabel == 0:
            report = ' '*indent + attr.ljust(longest) + ' :'
        else:
            report = ' '*indent + ' '.rjust(longest)
        if item == None:
            print report, 'None'
        elif isinstance(item, list) or isinstance(item,tuple):
            itemList = item
            if len(itemList) == 0:
                print report, 'Empty'
                continue
            print report
            for item in itemList:
                readRecord(item,[attr])
        elif isinstance(item, bolt.Flags):
            print report, item.hex(), item.getTrueAttrs()
        elif attr[-2:] == '_p' or attr == 'pgrd':
            print report, 'Packed Data'
        elif attr[-2:] == 'Id':
            print report, bosh.strFid(item)
        elif attr[:6] == 'unused': pass
        elif attr == 'scro':
            print report, '%08X' % int(item)
        elif attr in ['param1', 'param2']:
            if record.form12[int(attr[-1])-1] == 'I':
                print bosh.strFid(item)
            else:
                print report, item
        elif attr == 'land':
            print "land ", item
            print type(item)
            print dir(item)
##            sys.exit()
        elif isinstance(item,int):
            print report, item
        elif isinstance(item,long):
            print report, item
        elif isinstance(item,float):
            print report, round(item,6)
        elif attr in ['unk1','unk2','unk3','unk4','unk5','unk6']:
            if sum(struct.unpack(str(len(item)) + 'b',item)) == 0:
                print report, 'Null'
            else:
                print report, struct.unpack(str(len(item)) + 'b',item)
        elif isinstance(item, basestring):
            if len(item.splitlines()) > 1:
                item = item.splitlines()
                print report
                for line in item:
                    readRecord(line,[attr],1)
            else:
                if sum(struct.unpack(str(len(item)) + 'b',item)) == 0:
                    print report, ''
                else:
                    print report, item
        else:
            print report
            readRecord(item)
    indent -= 2
    if indent == 0:
        longest = 0
        print ''

# Common ----------------------------------------------------------------------
#------------------------------------------------------------------------------
@mainfunc
def convertFace(fileName,eid,fromEid,toEid):
    """Converts faces from one race to another."""
    init(3)
    #--Race faces
    raceInfo = bosh.modInfos[GPath('Oblivion.esm')]
    raceFaces = bosh.PCFaces.mod_getRaceFaces(raceInfo)
    fromRace = raceFaces.get(fromEid, bosh.PCFaces.PCFace())
    toRace   = raceFaces.get(toEid,   bosh.PCFaces.PCFace())
    #--Mod Face
    modInfo = bosh.modInfos[GPath(fileName)]
    face = bosh.PCFaces.mod_getFaces(modInfo)[eid]
    face.convertRace(fromRace,toRace)
    #--Save back over original face
    loadFactory = bosh.LoadFactory(True,bosh.MreNpc)
    modFile = bosh.ModFile(modInfo,loadFactory)
    modFile.load(True)
    npc = modFile.NPC_.getRecordByEid(eid)
    bosh.copyattrs(face,npc,('fggs_p','fgga_p','fgts_p'))
    npc.setChanged()
    modFile.safeSave()

#------------------------------------------------------------------------------
@mainfunc
def importRacialEyesHair(srcMod,srcRaceEid,dstMod,dstRaceEid):
    """Copies eyes and hair from one race to another."""
    init(3)
    if dstMod.lower() == 'oblivion.esm':
        raise "You don't REALLY want to overwrite Oblvion.esm, do you?"
    srcFactory = bosh.LoadFactory(False,bosh.MreRace)
    dstFactory = bosh.LoadFactory(True,bosh.MreRace)
    srcInfo = bosh.modInfos[GPath(srcMod)]
    dstInfo = bosh.modInfos[GPath(dstMod)]
    srcFile = bosh.ModFile(srcInfo,srcFactory)
    dstFile = bosh.ModFile(dstInfo,dstFactory)
    srcFile.load(True)
    dstFile.load(True)
    #--Get source and dest race records
    srcRace = dstRace = None
    for record in srcFile.RACE.records:
        if record.eid == srcRaceEid:
            srcRace = record
            break
    for record in dstFile.RACE.records:
        if record.eid == dstRaceEid:
            dstRace = record
            break
    if not srcRace: raise "Didn't find race (eid) %s in %s." % (srcRaceEid,srcMod)
    if not dstRace: raise "Didn't find race (eid) %s in %s." % (dstRaceEid,dstMod)
    #--Get mapper
    srcMasters = srcFile.tes4.masters[:] + [GPath(srcMod)]
    dstMasters = dstFile.tes4.masters[:] + [GPath(dstMod)]
    mapper = bosh.MasterMap(srcMasters,dstMasters)
    #print mapper.map
    #--XFer eyes, hair
    dstRace.defaultHairColor = srcRace.defaultHairColor
    dstRace.defaultHairMale = mapper(srcRace.defaultHairMale)
    dstRace.defaultHairFemale = mapper(srcRace.defaultHairFemale)
    dstRace.eyes = []
    cntEyes,cntHair = 0,0
    for srcid in srcRace.eyes:
        dstid = mapper(srcid)
        if dstid not in dstRace.eyes:
            dstRace.eyes.append(dstid)
            cntEyes += 1
    dstRace.hairs = []
    for srcid in srcRace.hairs:
        dstid = mapper(srcid)
        if dstid not in dstRace.hairs:
            dstRace.hairs.append(dstid)
            cntHair += 1
    dstRace.setChanged()
    #--Save Changes
    dstFile.safeSave()
    print "  Added %d eyes, %d hair" % (cntEyes,cntHair)

#------------------------------------------------------------------------------
@mainfunc
def diffScripts(oldFile,newFile):
    """Compares scripts between old and new files and prints scripts which differ
    from old to new to to two text files which can then be diffed by a diff utility."""
    init(3)
    oldScripts, newScripts = {},{}
    for scripts,fileName in ((oldScripts,oldFile),(newScripts,newFile)):
        loadFactory = bosh.LoadFactory(False,bosh.MreScpt)
        modInfo = bosh.modInfos[GPath(fileName)]
        modFile = bosh.ModFile(modInfo,loadFactory)
        modFile.load(True)
        scripts.update(dict((record.eid, record.scriptText) for record in modFile.SCPT.records))
    oldDump,newDump = ((GPath(fileName)+'.mws').open('w') for fileName in (oldFile,newFile))
    for eid in sorted(oldScripts):
        if eid in newScripts and oldScripts[eid] != newScripts[eid]:
            print 'Modified:',eid
            oldDump.write(';;;OLD %s %s\n' %( eid,'='*40))
            newDump.write(';;;NEW %s %s\n' %( eid,'='*40))
            oldDump.write(oldScripts[eid]+'\n\n')
            newDump.write(newScripts[eid]+'\n\n')
    oldDump.close()
    newDump.close()
    newScriptKeys = set(newScripts) - set(oldScripts)
#------------------------------------------------------------------------------
@mainfunc
def diffScripts2(oldFile,newFile):
    """As diffScripts, however returns lists of changes between the old version and new.
    Creates two text files in ..\Mopy\ - "oldFile" to "newFile" - Modified/Added.txt"""
    init(3)
    oldScripts, newScripts = {},{}
    for scripts,fileName in ((oldScripts,oldFile),(newScripts,newFile)):
        loadFactory = bosh.LoadFactory(False,bosh.MreScpt)
        modInfo = bosh.modInfos[GPath(fileName)]
        modFile = bosh.ModFile(modInfo,loadFactory)
        modFile.load(True)
        scripts.update(dict((record.eid, record.scriptText) for record in modFile.SCPT.records))
    modDump = (GPath(oldFile)+' to '+GPath(newFile)+' - Modified Scripts'+'.txt').open('w')
    addDump = (GPath(oldFile)+' to '+GPath(newFile)+' - Added Scripts'+'.txt').open('w')
    for eid in sorted(newScripts):
        if eid in oldScripts and newScripts[eid] != oldScripts[eid]:
            modDump.write('%s\n' %( eid))
        elif not (eid in oldScripts):
            addDump.write('%s\n' %( eid))
    modDump.close()
    addDump.close()
    newScriptKeys = set(newScripts) - set(oldScripts)

#------------------------------------------------------------------------------
@mainfunc
def scriptVars(fileName=None,printAll=None):
    """Print variables for scripts for specified mod file."""
    init(3)
    loadFactory = bosh.LoadFactory(False,bosh.MreScpt)
    modInfo = bosh.modInfos[GPath(fileName)]
    modFile = bosh.ModFile(modInfo,loadFactory)
    modFile.load(True)
    for record in sorted(modFile.SCPT.records,key=lambda a: a.eid):
        indices = [var.index for var in record.vars]
        if printAll or (indices != range(1,len(indices)+1)):
            print '%s:  NRefs: %d Last: %d' % (record.eid, record.numRefs, record.lastIndex)
            refVars = set(record.references)
            for var in record.vars:
                print ' ',var.index,var.name,('','[REF]')[var.index in refVars]

# Book Mangling ---------------------------------------------------------------
@mainfunc
def bookExport(fileName=None):
    """Export data from book to text file(s)."""
    fileName = GPath(fileName)
    init(3)
    #--Data from mod
    doImport = True
    modInfo = bosh.modInfos[fileName]
    loadFactory= bosh.LoadFactory(doImport,bosh.MreBook)
    modFile = bosh.ModFile(modInfo,loadFactory)
    modFile.load(True)
    data = {}
    texts = {}
    imported = {}
    #--Import Book texts
    if doImport:
        eid = None
        buffer = None
        reAt = re.compile('^@',re.M)
        reHeader = re.compile('== ?\[(\w+)\]')
        ins = GPath(fileName.root()+'.txt').open('r')
        reEndLine = re.compile('\n')
        for line in ins:
            maHeader = reHeader.match(line)
            if maHeader:
                if eid and buffer: imported[eid] = bosh.winNewLines(buffer.getvalue())
                eid = maHeader.group(1)
                buffer = cStringIO.StringIO()
                addTags = True
                wasBlank = True
                firstLine = True
                blanks = ''
            elif buffer:
                if firstLine:
                    firstLine = False
                    addTags = ('<' not in line)
                    if addTags:
                        line = '<font face=1><div align="center">'+line
                isBlank = not bool(line.strip())
                if addTags:
                    line = reAt.sub('<div align="left">',line)
                    line = reEndLine.sub('<br>\n',line)
                if isBlank:
                    blanks += line
                else:
                    buffer.write(blanks)
                    buffer.write(line)
                    blanks = ''
        ins.close()
        if eid and buffer:
            imported[eid] = bosh.winNewLines(buffer.getvalue())
    #--Books from mod
    changed = False
    for book in modFile.BOOK.records:
        if doImport:
            newText = imported.get(book.eid)
            if newText and newText != book.text:
                print 'Updating',book.eid
                book.text = newText
                book.setChanged()
                changed = True
        data[book.eid] = (book.eid,book.full,book.value,len(book.text))
        texts[book.eid] = book.text
    #--Save import?
    if doImport and changed:
        modFile.askSave(True)
    #--Dump book info
    if False:
        textPath = GPath(fileName.root()+'.csv')
        out = textPath.open('w')
        #out.write('"Edit Id"\t"Name"\t"Value"\t"Text Len"\n')
        for eid in sorted(data):
            out.write('"%s"\t"%s"\t"%d"\t"%d"\n' % data[eid])
        out.close()
    #--Dump Texts
    if True:
        reNewLine = re.compile('\r\n')
        out = GPath(fileName.root()+'.txt').open('w')
        for eid in sorted(data):
            text = reNewLine.sub('\n',texts[eid])
            out.write('== [%s]  %s\n' % data[eid][:2])
            out.write(text)
            out.write('\n\n')
        out.close()

@mainfunc
def bookImport(fileName=None):
    """Import data from text file into book."""
    fileName = GPath(fileName)
    init(3)
    data = {}
    #--Import from book
    textPath = GPath(fileName.root()+'.csv')
    ins = textPath.open()
    ins.readline() #--Skip first line
    for line in ins:
        line = line.strip()
        if not line or '\t' not in line: return
        (eid,full,value) = line.split('\t')[:3]
        eid = eid[1:-1]
        full = full[1:-1]
        value = int(value)
        #print eid,full,value
        data[eid] = value
    ins.close()
    #--Export to book
    modInfo = bosh.modInfos[fileName]
    loadFactory= bosh.LoadFactory(True,bosh.MreBook)
    modFile = bosh.ModFile(modInfo,loadFactory)
    modFile.load(True)
    for book in modFile.BOOK.records:
        if book.eid in data:
            print '%-35s %3d %3d' % (book.eid,book.value,data[book.eid])
            book.value = data[book.eid]
            book.setChanged()
        else:
            print book.eid,'NOT----------'
    modFile.safeSave()

# Misc. Utils -----------------------------------------------------------------
@mainfunc
def perfTest():
    import psyco
    psyco.full()
    init(3)
    test = 0.0
    total = 0.0
    from timeit import Timer
    for testClasses in ['bosh.MreClmt','bosh.MreCsty','bosh.MreIdle','bosh.MreLtex','bosh.MreRegn','bosh.MreSbsp']:
        test = Timer('testClasses = (%s,);loadFactory = bosh.LoadFactory(False,*testClasses);modInfo = bosh.modInfos[GPath("Oblivion.esm")];modFile = bosh.ModFile(modInfo,loadFactory);modFile.load(True)' % testClasses, "import bosh;from bolt import GPath").timeit(1)
        print testClasses, ":", test
        total += test
    print "total:", total
    sys.exit()
    test = 0.0
    total = 0.0
    for testClasses in ['bosh.MreAchr,bosh.MreCell,bosh.MreWrld','bosh.MreAcre,bosh.MreCell,bosh.MreWrld','bosh.MreActi','bosh.MreAlch','bosh.MreAmmo','bosh.MreAnio','bosh.MreAppa','bosh.MreArmo','bosh.MreBook','bosh.MreBsgn','bosh.MreCell,bosh.MreWrld','bosh.MreClas','bosh.MreClot','bosh.MreCont','bosh.MreCrea','bosh.MreDial,bosh.MreInfo','bosh.MreDoor','bosh.MreEfsh','bosh.MreEnch','bosh.MreEyes','bosh.MreFact','bosh.MreFlor','bosh.MreFurn','bosh.MreGlob','bosh.MreGmst','bosh.MreGras','bosh.MreHair','bosh.MreIngr','bosh.MreKeym','bosh.MreLigh','bosh.MreLscr','bosh.MreLvlc','bosh.MreLvli','bosh.MreLvsp','bosh.MreMgef','bosh.MreMisc','bosh.MreNpc','bosh.MrePack','bosh.MreQust','bosh.MreRace','bosh.MreRefr,bosh.MreCell,bosh.MreWrld','bosh.MreRoad,bosh.MreCell,bosh.MreWrld','bosh.MreScpt','bosh.MreSgst','bosh.MreSkil','bosh.MreSlgm','bosh.MreSoun','bosh.MreSpel','bosh.MreStat','bosh.MreTes4','bosh.MreTree','bosh.MreWatr','bosh.MreWeap','bosh.MreWthr']:#,'"LAND"', '"PGRD"']:
        test = Timer('testClasses = (%s,);loadFactory = bosh.LoadFactory(False,*testClasses);modInfo = bosh.modInfos[GPath("Oblivion.esm")];modFile = bosh.ModFile(modInfo,loadFactory);modFile.load(True)' % testClasses, "import bosh;from bolt import GPath").timeit(1)
        print testClasses, ":", test
        total += test
    print "total:", total
    ##print Timer('testClasses = (bosh.MreAchr,bosh.MreAcre,bosh.MreActi,bosh.MreAlch,bosh.MreAmmo,bosh.MreAnio,bosh.MreAppa,bosh.MreArmo,bosh.MreBook,bosh.MreBsgn,bosh.MreCell,bosh.MreClas,bosh.MreClmt,bosh.MreClot,bosh.MreCont,bosh.MreCrea,bosh.MreCsty,bosh.MreDial,bosh.MreDoor,bosh.MreEfsh,bosh.MreEnch,bosh.MreEyes,bosh.MreFact,bosh.MreFlor,bosh.MreFurn,bosh.MreGlob,bosh.MreGmst,bosh.MreGras,bosh.MreHair,bosh.MreIdle,bosh.MreInfo,bosh.MreIngr,bosh.MreKeym,bosh.MreLigh,bosh.MreLscr,bosh.MreLtex,bosh.MreLvlc,bosh.MreLvli,bosh.MreLvsp,bosh.MreMgef,bosh.MreMisc,bosh.MreNpc ,bosh.MrePack,bosh.MreQust,bosh.MreRace,bosh.MreRefr,bosh.MreRegn,bosh.MreRoad,bosh.MreSbsp,bosh.MreScpt,bosh.MreSgst,bosh.MreSkil,bosh.MreSlgm,bosh.MreSoun,bosh.MreSpel,bosh.MreStat,bosh.MreTes4,bosh.MreTree,bosh.MreWatr,bosh.MreWeap,bosh.MreWrld,bosh.MreWthr,"LAND", "PGRD");loadFactory = bosh.LoadFactory(False,*testClasses);modInfo = bosh.modInfos[GPath("Oblivion.esm")];modFile = bosh.ModFile(modInfo,loadFactory);modFile.load(True)', "import bosh;from bolt import GPath").timeit(1)
    sys.exit()

#------------------------------------------------------------------------------
@mainfunc
def bsaReport(fileName,printAll='False'):
    printAll = eval(printAll)
    init(2)
    bsaFile = bosh.BsaFile(GPath(fileName))
    bsaFile.scan()
    bsaFile.report(printAll)

#------------------------------------------------------------------------------
@mainfunc
def csType(newType,fileName="CS Functions.txt"):
    """Generates various function tables for CS Wiki from a raw CSFunctions.csv file."""
    #--Get list
    path = GPath("CS Types.txt")
    funcs = set([x.strip() for x in path.open()])
    changed = set()
    #--Edit
    records = []
    functions = set()
    path = GPath(fileName)
    ins = path.open()
    out = path.temp.open('w')
    for line in ins:
        line = re.sub('#.*','',line.strip())
        fields = line.split(';')
        fields = map(string.strip,fields)
        if fields and fields[0] and fields[0] != 'Function':
            while len(fields) < 4: fields.append('')
            func,source,type,text = fields
            if func and func in funcs and newType not in type:
                if type: type += ', '+newType
                else: type = newType
                changed.add(func)
            out.write(';'.join((func,source,type,text))+'\n')
    ins.close()
    out.close()
    path.untemp(True)
    print '\n'.join(sorted(changed))

#------------------------------------------------------------------------------
@mainfunc
def csFunctions(fileName="CS Functions.txt"):
    """Generates various function tables for CS Wiki from a raw CSFunctions.csv file."""
    records = []
    functions = set()
    source_icol = {'Function':0,'Source':1,'Type':2,'Description':3}
    ins = GPath(fileName).open()
    for line in ins:
        line = re.sub('#.*','',line.strip())
        fields = line.split(';')
        fields = map(string.strip,fields)
        if fields and fields[0] and fields[0] != 'Function':
            while len(fields) < 4: fields.append('')
            if not fields[1]: print "  No source for",fields[0]
            if fields[0] in functions:
                print "  Repeated function",fields[0]
            functions.add(fields[0])
            records.append(fields)
    ins.close()
    print 'Read',fileName
    #--Page writer
    def groupLink(group):
        group = re.sub('OBSE','[[:Category:Oblivion_Script_Extender|OBSE]]',group)
        group = re.sub('Pluggy','[[:Category:Pluggy|]]',group)
        group = re.sub('TSFC','[[:Category:TSFC|]]',group)
        return group
    def dumpPage(fileName,records,source=None,header=None):
        doLinks = source != 'TSFC'
        #--Filter?
        if source:
            records = [x for x in records if re.match(source,x[1])]
        out = GPath(fileName).open('w')
        #--Header
        if header: out.write(header+'\n\n')
        out.write("'''Editors:''' Do not edit entries on this page. See [[Raw Function List]] for more info.\n\n")
        if doLinks: out.write('{{CompactTOC4}}\n')
        #--Sort
        records.sort(key=lambda x: x[0].lower())
        current = ''
        links = (""," - [[#A|A]][[#B|B]][[#C|C]][[#D|D]][[#E|E]][[#F|F]][[#G|G]][[#H|H]][[#I|I]][[#J|J]][[#K|K]][[#L|L]][[#M|M]][[#N|N]][[#O|O]][[#P|P]][[#Q|Q]][[#R|R]][[#S|S]][[#T|T]][[#U|U]][[#V|V]][[#W|W]][[#X|X]][[#Y|Y]][[#Z|Z]]")[doLinks]
        if source == 'TSFC': links = ''
        for func,src,type,text in records:
            #--Alpha header
            if func[0].upper() != current:
                if current: out.write('|}\n\n')
                current = func[0].upper()
                if doLinks: out.write('===%s===\n' % current)
                out.write('{| width=100% class=functionTable\n|-\n')
                out.write('!align=left width=10%|Source\n')
                #out.write('!align=left width=10%|Type\n')
                out.write('!align=left width=35%|Function\n')
                #out.write('!align=left|Description ([[#top|Top]])\n')
                out.write('!align=left|Description'+links+'\n')
            #--Entry
            fields = (groupLink(src),'[['+func+']]',text)
            out.write('|-\n|'+(' || '.join(fields))+'\n')
        if current: out.write('|}\n')
        out.write('\n[[Category:Scripting]]\n')
        out.close()
        print 'Wrote', fileName
    #--Dump pages
    dumpPage('CS All.txt',records,None,
        "[[Category:Scripting]]\nThis page lists all scripting functions including OBSE and OBSE plugin functions.")
    dumpPage('CS CS.txt',records,'CS',
        "[[Category:Scripting]]\nThis page lists all native CS scripting functions. For a more comprehensive list (including OBSE and OBSE plugin functions), see [[List of Functions]].")
    dumpPage('CS OBSE.txt',records,'OBSE',
        "[[Category:Scripting]][[Category:Oblivion Script Extender]]\nThis page lists all functions for [[:Category:Oblivion_Script_Extender|]]. For a more comprehensive list (including native CS and OBSE plugin functions), see [[List of Functions]].")
    dumpPage('CS Pluggy.txt',records,'Pluggy',
        "[[Category:Scripting]][[Category:Pluggy]]\nThis page lists all functions for [[:Category:Pluggy|]]. For a more comprehesive list of functions (including native CS and other OBSE related functions), see [[List of Functions]].")
    dumpPage('CS TSFC.txt',records,'TSFC',
        "[[Category:Scripting]][[Category:TSFC]]\nThis page lists all functions for [[:Category:TSFC|]]. For a more comprehesive list of functions (including native CS and other OBSE related functions), see [[List of Functions]].")

#------------------------------------------------------------------------------
@mainfunc
def getIds(fileName=None):
    """Gets fids and returns as a set. Primarily for analysis of Oblivion.esm.
    NOTE: Does a low level read and hence can read fids of ALL records in all
    groups. Including CELLs WRLDs, etc."""
    def getRecordReader(ins,flags,size):
        """Decompress record data as needed."""
        if not bosh.MreRecord.flags1(flags).compressed:
            return (ins,ins.tell()+size)
        else:
            import zlib
            sizeCheck, = struct.unpack('I',ins.read(4))
            decomp = zlib.decompress(ins.read(size-4))
            if len(decomp) != sizeCheck:
                raise ModError(self.inName,
                    _('Mis-sized compressed data. Expected %d, got %d.') % (size,len(decomp)))
            reader = bosh.ModReader(fileName,cStringIO.StringIO(decomp))
            return (reader,sizeCheck)
    init(2)
    modInfo = bosh.modInfos[GPath(fileName)]
    ins = bosh.ModReader(fileName,modInfo.getPath().open('rb'))
    group_records = {}
    records = group_records['TES4'] = []
    while not ins.atEnd():
        (type,size,str0,fid,uint2) = ins.unpackRecHeader()
        print '>>',type,size,fid
        if type == 'GRUP':
            records = group_records.setdefault(str0,[])
            if str0 in ('CELL','WRLD'):
                ins.seek(size-20,1)
        elif type != 'GRUP':
            eid = ''
            nextRecord = ins.tell() + size
            recs,endRecs = getRecordReader(ins,str0,size)
            while recs.tell() < endRecs:
                (type,size) = recs.unpackSubHeader()
                if type == 'EDID':
                    eid = recs.readString(size)
                    break
                ins.seek(size,1)
            records.append((fid,eid))
            ins.seek(nextRecord)
    ins.close()
    #--Report
    del group_records['TES4']
    for group in sorted(group_records):
        #print
        print group
        for fid,eid in sorted(group_records[group],key = lambda a: a[1].lower()):
            print ' ',bosh.strFid(fid),eid

#------------------------------------------------------------------------------
@mainfunc
def gmstIds(fileName=None):
    """Updates map of GMST eids to fids in Data\Oblivion_ids.pkl, based either
    on a list of new eids or the gmsts in the specified mod file. Updated pkl file
    is dropped in Mopy directory."""
    #--Data base
    import cPickle
    fids = cPickle.load(GPath(r'Data\Oblivion_ids.pkl').open('r'))['GMST']
    maxId = max(fids.values())
    maxId = max(maxId,0xf12345)
    maxOld = maxId
    print 'maxId',hex(maxId)
    #--Eid list? - if the GMST has a 00000000 eid when looking at it in the cs with nothing 
	# but oblivion.esm loaded you need to add the gmst to this list, rebuild the pickle and overwrite the old one.
    for eid in ['iTrainingSkills','fRepairCostMult','fCrimeGoldSteal','iAllowAlchemyDuringCombat','iNumberActorsAllowedToFollowPlayer','iAllowRepairDuringCombat','iMaxPlayerSummonedCreatures','iAICombatMaxAllySummonCount','iAINumberActorsComplexScene','fHostileActorExteriorDistance','fHostileActorInteriorDistance']:
        if eid not in fids:
            maxId += 1
            fids[eid] = maxId
            print '%08X  %08X %s' % (0,maxId,eid)
			#--Source file
    if fileName:
        init(3)
        sorter = lambda a: a.eid
        loadFactory = bosh.LoadFactory(False,bosh.MreGmst)
        modInfo = bosh.modInfos[GPath(fileName)]
        modFile = bosh.ModFile(modInfo,loadFactory)
        modFile.load(True)
        for gmst in sorted(modFile.GMST.records,key=sorter):
            print gmst.eid, gmst.value
            if gmst.eid not in fids:
                maxId += 1
                fids[gmst.eid] = maxId
                print '%08X  %08X %s' % (gmst.fid,maxId,gmst.eid)
    #--Changes?
    if maxId > maxOld:
        outData = {'GMST':fids}
        cPickle.dump(outData,GPath(r'Oblivion_ids.pkl').open('w'))
        print "%d news gmst ids written to Oblivion_ids.pkl" % ((maxId - maxOld),)

#------------------------------------------------------------------------------
@mainfunc
def modCheck(fileName=None):
    """Reports on various problems with mods."""
    reBadVarName = re.compile('^[_0-9]')
    init(3)
    loadFactory = bosh.LoadFactory(False,bosh.MreWeap)
    for modInfo in bosh.modInfos.data.values():
        print '\n',modInfo.name
        modFile = bosh.ModFile(modInfo,loadFactory)
        modFile.load(True)
        #--Bows with reach == 0 error? (Causes CTD if NPC tries to equip.)
        for record in modFile.WEAP.records:
            if record.weaponType == 5 and record.reach <= 0:
                print ' ',record.eid
        #--Records with poor variable names? (Names likely to cause errors.)
        for record in modFile.SCPT.records:
            badVarNames = []
            for var in record.vars:
                if reBadVarName.match(var.name): badVarNames.append(var.name)
            if badVarNames:
                print ' ',record.eid,badVarNames

#------------------------------------------------------------------------------
@mainfunc
def findSaveRecord(srcName,fid):
    """Finds specified record in save file."""
    init(3)
    srcInfo = bosh.saveInfos[GPath(srcName)]
    srcFile = bosh.SaveFile(srcInfo)
    srcFile.load()
    #--Get src npc data
    fid = int(fid,16)
    print srcFile.getRecord(fid)

#------------------------------------------------------------------------------
@mainfunc
def renameArchives(root=r'C:\Program Files\Bethesda Softworks\Oblivion\Downloads'):
    """Renames TesSource archive files to sort a little better.
    E.g., change 12345-2.23-My Wicked Mod-TESSource.zip to My Wicked Mod 2.23.zip."""
    reTesSource = re.compile(r'^\d{4}-(\d[^-]*)-(.+)-TESSource.(zip|rar|7z|ace|exe)$',re.I)
    reTesSourceNV = re.compile(r'^\d{4}-(.+)-TESSource.(zip|rar|7z|ace|exe)$',re.I)
    reTesSource3 = re.compile(r'^(.+)-\d+-TESSource.(zip|rar|7z|ace|exe|esp)$',re.I)
    reBracketNum = re.compile(r'\[1\]')
    for (dirPath,dirNames,fileNames) in os.walk(root):
        dirPath = GPath(dirPath)
        for name in fileNames:
            path = dirPath.join(name)
            maTesSource = reTesSource.match(name.s)
            maTesSource3 = reTesSource3.match(name.s)
            maTesSourceNV = reTesSourceNV.match(name.s)
            if maTesSource:
                newName = '%s %s.%s' % maTesSource.group(2,1,3)
            elif maTesSourceNV:
                newName = '%s.%s' % maTesSourceNV.group(1,2)
            elif maTesSource3:
                newName = '%s.%s' % maTesSource3.group(1,2)
            else:
                newName = name
            newName = reBracketNum.sub('',newName)
            if newName != name:
                newPath = os.path.join(dirPath,newName)
                print newName.s
                path.moveTo(newPath)

#------------------------------------------------------------------------------
@mainfunc
def uncontinue():
    """Clears continue settings from settings."""
    init(0)
    settings = bosh.settings
    for key in settings.keys():
        if re.search(r'\.continue$',key):
            print key
            del settings[key]
    settings.save()

@mainfunc
def parseTest(srcName=None,dstName='Wrye Test.esp'):
    init(3)
    testClasses = (bosh.MreSkil,)
    loadFactory = bosh.LoadFactory(False,*testClasses)
    #--Src file
    srcInfo = bosh.modInfos[GPath(srcName)]
    srcFile = bosh.ModFile(srcInfo,loadFactory)
    srcFile.load(True)
    #return
    #--Dst file
    loadFactory = bosh.LoadFactory(True,*testClasses)
    dstInfo = bosh.modInfos[GPath(dstName)]
    dstFile = bosh.ModFile(dstInfo,loadFactory)
    dstFile.convertToLongFids()
    srcFile.convertToLongFids()
    #--Save to test file
    for testClass in testClasses:
        type = testClass.classType
        print type
        srcBlock = getattr(srcFile,type)
        dstBlock = getattr(dstFile,type)
        for record in srcBlock.records:
            dstBlock.setRecord(record.getTypeCopy())
    #--Convert and save
    dstFile.tes4.masters = dstFile.getMastersUsed()
    dstFile.convertToShortFids()
    dstFile.askSave(True)

@mainfunc
def parseDials(srcName=None,dstName='Wrye Test.esp'):
    init(3)
    testClasses = (bosh.MreDial,bosh.MreInfo)
    loadFactory = bosh.LoadFactory(False,*testClasses)
    #--Src file
    srcInfo = bosh.modInfos[GPath(srcName)]
    srcFile = bosh.ModFile(srcInfo,loadFactory)
    srcFile.load(True)
    #return
    #--Dst file
    loadFactory = bosh.LoadFactory(True,*testClasses)
    dstInfo = bosh.modInfos[GPath(dstName)]
    dstFile = bosh.ModFile(dstInfo,loadFactory)
    dstFile.convertToLongFids()
    srcFile.convertToLongFids()
    #--Save to test file
    srcBlock = getattr(srcFile,'DIAL')
    dstBlock = getattr(dstFile,'DIAL')
    for index,record in enumerate(srcBlock.records):
        record = record.getTypeCopy()
        dstBlock.setRecord(record)
    #--Convert and save
    dstFile.tes4.masters = dstFile.getMastersUsed()
    dstFile.convertToShortFids()
    dstFile.askSave(True)

@mainfunc
def parseRecords(fileName='Oblivion.esm'):
    import psyco
    psyco.full()
    init(3)
    skipPrint = False
    tempDict = dict()
    diffDict = dict()
    skipPrint = True
##    #All complex records
##    testClasses = [bosh.MreRecord.type_class[x] for x in (set(bosh.MreRecord.type_class) - bosh.MreRecord.simpleTypes)] ##'LAND', 'PGRD'
##    #All simple records
##    testClasses = [bosh.MreRecord.type_class[x] for x in bosh.MreRecord.simpleTypes]
    #All Records
##    testClasses = bosh.MreRecord.type_class.values() + ['LAND','PGRD']
    testClasses = [bosh.MreRegn,]
##    testClasses = [bosh.MreRefr,bosh.MreCell,bosh.MreWrld]
    loadFactory = bosh.LoadFactory(False,*testClasses)
    modInfo = bosh.modInfos[GPath(fileName)]
    modFile = bosh.ModFile(modInfo,loadFactory)
    modFile.load(True)
    class disablePrint:
        def write(self,text):
            pass
    if skipPrint == True:
        oOut = sys.stdout
        sys.stdout = disablePrint()
    for typed in bush.topTypes:
        if typed not in loadFactory.recTypes or typed not in modFile.tops: continue
        print typed
        if hasattr(getattr(modFile,typed), 'melSet'): readRecord(getattr(modFile,typed))
        elif typed == 'CELL':
            for cb in getattr(modFile,typed).cellBlocks: readRecord(cb)
        elif typed == 'WRLD':
            for wb in getattr(modFile,typed).worldBlocks: readRecord(wb)
        elif hasattr(getattr(modFile,typed), 'records'):
            for record in getattr(modFile,typed).records:
                if hasattr(record, 'melSet'): readRecord(record)
                else:
                    print record
                    print dir(record)
                    for item in dir(record):
                        print item
                    print "Blergh", typed
                    sys.exit()
                    return
        else:
            print typed
            return
    if skipPrint == True:
        sys.stdout = oOut
    modFile.tes4.masters.append(modInfo.name)
    modFile.tes4.setChanged()
    outInfo = bosh.ModInfo(modInfo.dir,GPath(modFile.fileInfo.name.s[:-4] + " Dump.esp"))
    modFile.fileInfo = outInfo
    loadFactory.keepAll = True
    modFile.safeSave()
    print modFile.fileInfo.name.s,'saved.'
    modFile.fileInfo.getHeader()
    modFile.fileInfo.setType('esp')
    
# Temp ------------------------------------------------------------------------
"""Very temporary functions."""
#--Temp
@mainfunc
def temp(fileName=None):
    import psyco
    psyco.full()
    init(3)
    testClasses = (bosh.MreWrld,bosh.MreCell,bosh.MreAcre,bosh.MreAchr,bosh.MreRefr)
    loadFactory = bosh.LoadFactory(False,*testClasses)
    modInfo = bosh.modInfos[GPath(fileName)]
    modFile = bosh.ModFile(modInfo,loadFactory)
    modFile.load(True)
    strf = bosh.strFid
    for cb in modFile.CELL.cellBlocks:
        print cb.cell.full,strf(cb.cell.fid)
        cb.cell.setChanged()
        for attr in ('persistent','temp','distant'):
            #print ' ',attr
            for record in getattr(cb,attr):
                #print '   ',strf(record.fid)
                record.setChanged()
    for wb in modFile.WRLD.worldBlocks:
        print wb.world.full,strf(wb.world.fid)
        for cb in wb.cellBlocks:
            print '.',cb.cell.full,strf(cb.cell.fid)
            cb.cell.setChanged()
            for attr in ('persistent','temp','distant'):
                #print ' ',attr
                for record in getattr(cb,attr):
                    #print '   ',strf(record.fid)
                    record.setChanged()
    modFile.tes4.masters.append(modInfo.name)
    modFile.tes4.setChanged()
    outInfo = bosh.ModInfo(modInfo.dir,GPath("Wrye Dump.esp"))
    modFile.fileInfo = outInfo
    loadFactory.keepAll = True
    modFile.askSave()
    return
    for record in modFile.SCPT.getActiveRecords():
        print record.eid
        out = GPath(record.eid+'.mws').open('w')
        out.write(record.scriptText)
        out.close()
    return
    #--Save to test file
    for testClass in testClasses:
        print testClass.classType
        for record in getattr(modFile,testClass.classType).records:
            #print record.eid
            if reBarExt.match(record.model.modPath):
                record.model.modPath = reBarExt.sub(r'Architecture\\BarabusCrypt',record.model.modPath)
                print record.eid, record.model.modPath
                record.setChanged()
    modFile.askSave(True)

@mainfunc
def balancer(fileName=None):
    """Generates part of the balancing scripts for Cobl Races Balanced."""
    init(3)
    loadFactory = bosh.LoadFactory(False,bosh.MreRace)
    modInfo = bosh.modInfos[GPath('Cobl Races.esp')]
    balInfo = bosh.modInfos[GPath('Cobl Races - Balanced.esp')]
    modFile = bosh.ModFile(modInfo,loadFactory)
    balFile = bosh.ModFile(balInfo,loadFactory)
    modFile.load(True)
    balFile.load(True)
    skillNames = bush.actorValues[12:33]
    for race in sorted(modFile.RACE.getActiveRecords(),key=attrgetter('eid')):
        balRace = balFile.RACE.getRecord(race.fid)
        if not balRace: continue
        print 'if',race.eid
        #--Attributes
        print '\tif getPcIsSex male'
        if race.maleStrength != balRace.maleStrength:
            print '\t\tset mod%s to %d' % (bush.actorValues[0],balRace.maleStrength-race.maleStrength)
        if race.maleIntelligence != balRace.maleIntelligence:
            print '\t\tset mod%s to %d' % (bush.actorValues[1],balRace.maleIntelligence-race.maleIntelligence)
        if race.maleWillpower != balRace.maleWillpower:
            print '\t\tset mod%s to %d' % (bush.actorValues[2],balRace.maleWillpower-race.maleWillpower)
        if race.maleAgility != balRace.maleAgility:
            print '\t\tset mod%s to %d' % (bush.actorValues[3],balRace.maleAgility-race.maleAgility)
        if race.maleSpeed != balRace.maleSpeed:
            print '\t\tset mod%s to %d' % (bush.actorValues[4],balRace.maleSpeed-race.maleSpeed)
        if race.maleEndurance != balRace.maleEndurance:
            print '\t\tset mod%s to %d' % (bush.actorValues[5],balRace.maleEndurance-race.maleEndurance)
        if race.malePersonality != balRace.malePersonality:
            print '\t\tset mod%s to %d' % (bush.actorValues[6],balRace.malePersonality-race.malePersonality)
        if race.maleLuck != balRace.maleLuck:
            print '\t\tset mod%s to %d' % (bush.actorValues[7],balRace.maleLuck-race.maleLuck)
        print '\telse'
        if race.femaleStrength != balRace.femaleStrength:
            print '\t\tset mod%s to %d' % (bush.actorValues[0],balRace.femaleStrength-race.femaleStrength)
        if race.femaleIntelligence != balRace.femaleIntelligence:
            print '\t\tset mod%s to %d' % (bush.actorValues[1],balRace.femaleIntelligence-race.femaleIntelligence)
        if race.femaleWillpower != balRace.femaleWillpower:
            print '\t\tset mod%s to %d' % (bush.actorValues[2],balRace.femaleWillpower-race.femaleWillpower)
        if race.femaleAgility != balRace.femaleAgility:
            print '\t\tset mod%s to %d' % (bush.actorValues[3],balRace.femaleAgility-race.femaleAgility)
        if race.femaleSpeed != balRace.femaleSpeed:
            print '\t\tset mod%s to %d' % (bush.actorValues[4],balRace.femaleSpeed-race.femaleSpeed)
        if race.femaleEndurance != balRace.femaleEndurance:
            print '\t\tset mod%s to %d' % (bush.actorValues[5],balRace.femaleEndurance-race.femaleEndurance)
        if race.femalePersonality != balRace.femalePersonality:
            print '\t\tset mod%s to %d' % (bush.actorValues[6],balRace.femalePersonality-race.femalePersonality)
        if race.femaleLuck != balRace.femaleLuck:
            print '\t\tset mod%s to %d' % (bush.actorValues[7],balRace.femaleLuck-race.femaleLuck)
        print '\tendif'

        #--Skills
        boosts = [0 for x in skillNames]
        if race.skill1 != 255: boosts[race.skill1-12] = race.skill1Boost
        if race.skill2 != 255: boosts[race.skill2-12] = race.skill2Boost
        if race.skill3 != 255: boosts[race.skill3-12] = race.skill3Boost
        if race.skill4 != 255: boosts[race.skill4-12] = race.skill4Boost
        if race.skill5 != 255: boosts[race.skill5-12] = race.skill5Boost
        if race.skill6 != 255: boosts[race.skill6-12] = race.skill6Boost
        if race.skill7 != 255: boosts[race.skill7-12] = race.skill7Boost

        balBoosts = [0 for x in skillNames]
        if balRace.skill1 != 255: balBoosts[balRace.skill1-12] = balRace.skill1Boost
        if balRace.skill2 != 255: balBoosts[balRace.skill2-12] = balRace.skill2Boost
        if balRace.skill3 != 255: balBoosts[balRace.skill3-12] = balRace.skill3Boost
        if balRace.skill4 != 255: balBoosts[balRace.skill4-12] = balRace.skill4Boost
        if balRace.skill5 != 255: balBoosts[balRace.skill5-12] = balRace.skill5Boost
        if balRace.skill6 != 255: balBoosts[balRace.skill6-12] = balRace.skill6Boost
        if balRace.skill7 != 255: balBoosts[balRace.skill7-12] = balRace.skill7Boost

        #--Attributes
        for index,boost,balBoost in zip(range(21),boosts,balBoosts):
            if boost != balBoost:
                print '\tset mod%s to %d' % (skillNames[index],balBoost-boost)

@mainfunc
def temp1(fileName):
    init(3)
    #bolt.deprintOn = True
    #saveInfo = bosh.SaveInfo(bosh.saveInfos.dir,GPath(fileName))
    #saveFile = bosh.SaveFile(saveInfo)
    #saveFile.load()
    #saveFile.weather = ''
    #saveFile.safeSave()


# Zip Stuff --------------------------------------------------------------------
class Archive:
    """Installer Archive. Represents a 7z or zip archive in a certain format.
    Can install/uninstall."""

    def __init__(self,path):
        """Initialize."""
        self.path = GPath(path)
        self.files = [] #--

    def refresh(self):
        """Refreshes file list from archive."""
        files = {}
        reList = re.compile('(Path|Size|CRC|Attributes) = (.+)')
        path = size = crc = isDir = 0
        out = os.popen('7z.exe l "'+self.path.s+'"','rt')
        for line in out:
            print line,
            maList = reList.match(line)
            if maList:
                key,value = maList.groups()
                if key == 'Path':
                    path = GPath(value)
                elif key == 'Size':
                    size = int(value)
                elif key == 'Attributes':
                    isDir = (value[0] == 'D')
                    if isDir: print path,'isDir'
                elif key == 'CRC':
                    crc = int(value,16)
                    if path and not isDir:
                        files[path] = (size,crc)
                        #print '%8d %8X %s' % (size,crc,path.s)
                    path = size = crc = 0
        result = out.close()
        print 'result',result

    def extract(self):
        """Extracts specified files from archive."""
        out = os.popen('7z.exe x "'+self.path.s+'" -y -oDumpster @listfile.txt -scsWIN','r')
        reExtracting = re.compile('Extracting\s+(.+)')
        for line in out:
            maExtracting = reExtracting.match(line)
            if maExtracting:
                print maExtracting.group(1)
        print 'result',out.close()

@mainfunc
def test(file):
    x = Archive(file)
    x.refresh()


# Main -------------------------------------------------------------------------
if __name__ == '__main__':
    #--No profile
    if True:
        bolt._mainFunctions.main()
    #--Profile
    else:
        import profile,pstats
        profile.run('bolt.commands.main()','bishProfile')
        stats = pstats.Stats('bishProfile')
        stats.strip_dirs().sort_stats('time').print_stats('bish')
