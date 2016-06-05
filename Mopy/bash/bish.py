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
import StringIO
import sys
import types
from subprocess import Popen, PIPE
from operator import attrgetter,itemgetter

import bass
import bosh.faces
import parsers
from record_groups import MobCell, MobWorld
from game.oblivion import MreNpc, MreRace, MreScpt, MreBook, MreGmst, \
    MreWeap, MreSkil, MreInfo, MreDial, MreRegn

#--Local
import bolt
bolt.CBash = [os.path.join(os.getcwdu(),u'bash',u'compiled'),os.path.join(os.getcwdu(),u'compiled')]
import bush
ret = bush.setGame(u'')
if ret != False: # False == success
    if len(ret) != 1:
        # Python mode, use Tkinter here, since we don't know for sure if wx is present
        import Tkinter
        root = Tkinter.Tk()
        frame = Tkinter.Frame(root)
        frame.pack()

        class onQuit(object):
            def __init__(self):
                self.canceled = False

            def on_click(self):
                self.canceled = True
                root.destroy()
        quit = onQuit()

        button = Tkinter.Button(frame,text=u'Quit',fg=u'red',command=quit.on_click,pady=15,borderwidth=5,relief=Tkinter.GROOVE)
        button.pack(fill=Tkinter.BOTH,expand=1,side=Tkinter.BOTTOM)
        class OnClick(object):
            def __init__(self,gameName):
                self.gameName = gameName

            def on_click(self):
                bush.setGame(self.gameName)
                root.destroy()
        for gameName in ret:
            text = gameName[0].upper() + gameName[1:]
            command = OnClick(gameName).on_click
            button = Tkinter.Button(frame,text=text,command=command,pady=15,borderwidth=5,relief=Tkinter.GROOVE)
            button.pack(fill=Tkinter.BOTH,expand=1,side=Tkinter.BOTTOM)
        w = Tkinter.Text(frame)
        w.insert(Tkinter.END, _(u"Wrye Bash could not determine which game to manage.  The following games have been detected, please select one to manage.")
                 + u'\n\n'+
                 _(u"To prevent this message in the future, use the -g command line argument to specify the game"))
        w.config(state=Tkinter.DISABLED)
        w.pack()
        root.mainloop()
        #if quit.canceled:
            #return
        del Tkinter # Unload TKinter, it's not needed anymore
    else:
        bush.setGame(ret[0])
import bosh
from bolt import GPath, Path, mainfunc

indent = 0
longest = 0
stringBuffer = StringIO.StringIO

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
    bosh.initBosh()
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
    if isinstance(record, MobCell):
        melSet = ['cell','persistent','distant','temp','land','pgrd']
    elif isinstance(record, MobWorld):
        melSet = ['cellBlocks','world','road','worldCellBlock']
    elif hasattr(record, 'melSet'):
        melSet = record.melSet.getSlotsUsed()
        if record.recType == 'DIAL':
            melSet += ['infoStamp','infoStamp2','infos']
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
            if sum(struct.unpack(`len(item)`+'b',item)) == 0:
                print report, 'Null'
            else:
                print report, struct.unpack(`len(item)`+'b',item)
        elif isinstance(item, basestring):
            if len(item.splitlines()) > 1:
                item = item.splitlines()
                print report
                for line in item:
                    readRecord(line,[attr],1)
            else:
                if sum(struct.unpack(`len(item)`+'b',item)) == 0:
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
    raceFaces = bosh.faces.PCFaces.mod_getRaceFaces(raceInfo)
    fromRace = raceFaces.get(fromEid, bosh.faces.PCFaces.PCFace())
    toRace   = raceFaces.get(toEid,   bosh.faces.PCFaces.PCFace())
    #--Mod Face
    modInfo = bosh.modInfos[GPath(fileName)]
    face = bosh.faces.PCFaces.mod_getFaces(modInfo)[eid]
    face.convertRace(fromRace,toRace)
    #--Save back over original face
    loadFactory = parsers.LoadFactory(True, MreNpc)
    modFile = parsers.ModFile(modInfo, loadFactory)
    modFile.load(True)
    npc = modFile.NPC_.getRecordByEid(eid)
    bolt.copyattrs(face,npc,('fggs_p','fgga_p','fgts_p'))
    npc.setChanged()
    modFile.safeSave()

#------------------------------------------------------------------------------
@mainfunc
def importRacialEyesHair(srcMod,srcRaceEid,dstMod,dstRaceEid):
    """Copies eyes and hair from one race to another."""
    init(3)
    if dstMod.lower() == 'oblivion.esm':
        raise bolt.BoltError(u"You don't REALLY want to overwrite Oblivion.esm, do you?")
    srcFactory = parsers.LoadFactory(False, MreRace)
    dstFactory = parsers.LoadFactory(True, MreRace)
    srcInfo = bosh.modInfos[GPath(srcMod)]
    dstInfo = bosh.modInfos[GPath(dstMod)]
    srcFile = parsers.ModFile(srcInfo, srcFactory)
    dstFile = parsers.ModFile(dstInfo, dstFactory)
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
    if not srcRace: raise bosh.ModError(srcMod,u"Didn't find race (eid) %s." % srcRaceEid)
    if not dstRace: raise bosh.ModError(dstMod,u"Didn't find race (eid) %s." % dstRaceEid)
    #--Get mapper
    srcMasters = srcFile.tes4.masters[:] + [GPath(srcMod)]
    dstMasters = dstFile.tes4.masters[:] + [GPath(dstMod)]
    mapper = parsers.MasterMap(srcMasters, dstMasters)
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
    print _(u"  Added %d eyes, %d hair") % (cntEyes,cntHair)

#------------------------------------------------------------------------------
@mainfunc
def diffScripts(oldFile,newFile):
    """Compares scripts between old and new files and prints scripts which differ
    from old to new to to two text files which can then be diffed by a diff utility."""
    init(3)
    oldScripts, newScripts = {},{}
    for scripts,fileName in ((oldScripts,oldFile),(newScripts,newFile)):
        loadFactory = parsers.LoadFactory(False, MreScpt)
        modInfo = bosh.modInfos[GPath(fileName)]
        modFile = parsers.ModFile(modInfo, loadFactory)
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
        loadFactory = parsers.LoadFactory(False, MreScpt)
        modInfo = bosh.modInfos[GPath(fileName)]
        modFile = parsers.ModFile(modInfo, loadFactory)
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
    loadFactory = parsers.LoadFactory(False, MreScpt)
    modInfo = bosh.modInfos[GPath(fileName)]
    modFile = parsers.ModFile(modInfo, loadFactory)
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
    loadFactory= parsers.LoadFactory(doImport, MreBook)
    modFile = parsers.ModFile(modInfo, loadFactory)
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
                if eid and buffer: imported[eid] = bolt.winNewLines(buffer.getvalue())
                eid = maHeader.group(1)
                buffer = stringBuffer()
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
            imported[eid] = bolt.winNewLines(buffer.getvalue())
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
    loadFactory= parsers.LoadFactory(True, MreBook)
    modFile = parsers.ModFile(modInfo, loadFactory)
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
    init(3)
    test = 0.0
    total = 0.0
    from timeit import Timer
    for testClasses in ['bosh.MreClmt','bosh.MreCsty','bosh.MreIdle','bosh.MreLtex','MreRegn','bosh.MreSbsp']:
        test = Timer('testClasses = (%s,);loadFactory = bosh.LoadFactory(False,*testClasses);modInfo = bosh.modInfos[GPath("Oblivion.esm")];modFile = bosh.ModFile(modInfo,loadFactory);modFile.load(True)' % testClasses, "import bosh;from bolt import GPath").timeit(1)
        print testClasses, ":", test
        total += test
    print "total:", total
    sys.exit()
    test = 0.0
    total = 0.0
    for testClasses in ['bosh.MreAchr,bosh.MreCell,bosh.MreWrld','bosh.MreAcre,bosh.MreCell,bosh.MreWrld','bosh.MreActi','bosh.MreAlch','bosh.MreAmmo','bosh.MreAnio','bosh.MreAppa','bosh.MreArmo','MreBook','bosh.MreBsgn','bosh.MreCell,bosh.MreWrld','bosh.MreClas','bosh.MreClot','bosh.MreCont','bosh.MreCrea','MreDial,MreInfo','bosh.MreDoor','bosh.MreEfsh','bosh.MreEnch','bosh.MreEyes','bosh.MreFact','bosh.MreFlor','bosh.MreFurn','bosh.MreGlob','MreGmst','bosh.MreGras','bosh.MreHair','bosh.MreIngr','bosh.MreKeym','bosh.MreLigh','bosh.MreLscr','bosh.MreLvlc','bosh.MreLvli','bosh.MreLvsp','bosh.MreMgef','bosh.MreMisc','MreNpc','bosh.MrePack','bosh.MreQust','MreRace','bosh.MreRefr,bosh.MreCell,bosh.MreWrld','bosh.MreRoad,bosh.MreCell,bosh.MreWrld','MreScpt','bosh.MreSgst','MreSkil','bosh.MreSlgm','bosh.MreSoun','bosh.MreSpel','bosh.MreStat','bosh.MreTes4','bosh.MreTree','bosh.MreWatr','MreWeap','bosh.MreWthr']:#,'"LAND"', '"PGRD"']:
        test = Timer('testClasses = (%s,);loadFactory = bosh.LoadFactory(False,*testClasses);modInfo = bosh.modInfos[GPath("Oblivion.esm")];modFile = bosh.ModFile(modInfo,loadFactory);modFile.load(True)' % testClasses, "import bosh;from bolt import GPath").timeit(1)
        print testClasses, ":", test
        total += test
    print "total:", total
    ##print Timer('testClasses = (bosh.MreAchr,bosh.MreAcre,bosh.MreActi,bosh.MreAlch,bosh.MreAmmo,bosh.MreAnio,bosh.MreAppa,bosh.MreArmo,MreBook,bosh.MreBsgn,bosh.MreCell,bosh.MreClas,bosh.MreClmt,bosh.MreClot,bosh.MreCont,bosh.MreCrea,bosh.MreCsty,MreDial,bosh.MreDoor,bosh.MreEfsh,bosh.MreEnch,bosh.MreEyes,bosh.MreFact,bosh.MreFlor,bosh.MreFurn,bosh.MreGlob,MreGmst,bosh.MreGras,bosh.MreHair,bosh.MreIdle,MreInfo,bosh.MreIngr,bosh.MreKeym,bosh.MreLigh,bosh.MreLscr,bosh.MreLtex,bosh.MreLvlc,bosh.MreLvli,bosh.MreLvsp,bosh.MreMgef,bosh.MreMisc,MreNpc ,bosh.MrePack,bosh.MreQust,MreRace,bosh.MreRefr,MreRegn,bosh.MreRoad,bosh.MreSbsp,MreScpt,bosh.MreSgst,MreSkil,bosh.MreSlgm,bosh.MreSoun,bosh.MreSpel,bosh.MreStat,bosh.MreTes4,bosh.MreTree,bosh.MreWatr,MreWeap,bosh.MreWrld,bosh.MreWthr,"LAND", "PGRD");loadFactory = bosh.LoadFactory(False,*testClasses);modInfo = bosh.modInfos[GPath("Oblivion.esm")];modFile = bosh.ModFile(modInfo,loadFactory);modFile.load(True)', "import bosh;from bolt import GPath").timeit(1)
    sys.exit()

#------------------------------------------------------------------------------
@mainfunc
def makeOOO_NoGuildOwnership():
    bosh.initBosh()
    import cint
    with cint.ObCollection(ModsPath=bass.dirs['mods'].s) as Current:
        modFile = Current.addMod("Oscuro's_Oblivion_Overhaul.esp")
        destFile = Current.addMod("OOO-No_Guild_Ownership.esp", CreateIfNotExist=True)
        Current.load()
        guildCells = set([0x0002C178,0x00003AAC,0x00030534,0x0000A2BC,0x00027D58,
                          0x0003E0E4,0x00086588,0x0002C179,0x000855AD,0x0002CA2F,
                          0x0002FF4F,0x0002CDBD,0x00030535,0x0002D155,0x00000885,
                          0x0003E0E5,0x0002C17A,0x0004F8C8,0x00032F02,0x000235DE,
                          0x00000ADE,0x00000D9A,0x00006917,0x000855A5,0x00003AAF,
                          0x000260CD,0x000855A6,0x0002D068,0x0001C92A,0x00051B8E,
                          0x0002C172,0x0002D626,0x0003ABDD,0x00051B8F,0x0001C93F,
                          0x0002E545,0x0003ABDE,0x000855A8,0x000097B4,0x00051B90,
                          0x00033370,0x0002C174,0x0000691B,0x000855A9,0x000097B5,
                          0x0000A2B9,0x000302ED,0x0002C175,0x0008440C,0x00049CF8,
                          0x000097B6,0x0004EA5A,0x0002C176,0x0008440D,0x00049CF9,
                          0x00027D57,0x000308CB,0x00030425,0x0002CFD7,0x0003E0E3,
                          0x0002C177])
        guildFactions = set([0x00022296,0x0002228F])
        changed = {}

        for record in modFile.CELL:
            if record.fid in guildCells:
                print record.eid
                for refr in record.REFR:
                    if refr.owner in guildFactions:
                        base = Current.LookupRecords(refr.base)
                        try:
                            base = base[0]
                        except:
                            continue
                        if base._Type in bosh.pickupables:
                            if base._Type == 'LIGH':
                                if not base.IsCanTake: continue
                            if base._Type == 'BOOK':
                                if base.IsFixed: continue
                            if destFile.HasRecord(record.fid) is None:
                                #Copy the winning version of the parent over if it isn't in the patch
                                record.CopyAsOverride(destFile)
                            override = refr.CopyAsOverride(destFile)
                            if override:
                                override.owner = None
                                override.rank = None
                                override.globalVariable = None
                                changed[base._Type] = changed.get(base._Type,0) + 1
        print changed
        if sum(changed.values()): destFile.save()

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
    def getRecordReader(self,ins,flags,size):
        """Decompress record data as needed."""
        if not bosh.MreRecord.flags1(flags).compressed:
            return (ins,ins.tell()+size)
        else:
            import zlib
            sizeCheck, = struct.unpack('I',ins.read(4))
            decomp = zlib.decompress(ins.read(size-4))
            if len(decomp) != sizeCheck:
                raise bosh.ModError(self.inName,
                    u'Mis-sized compressed data. Expected %d, got %d.' % (size,len(decomp)))
            reader = bosh.ModReader(fileName,stringBuffer(decomp))
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
                # header[1]-24,1 20 for Oblivion, 24 for others.
                # There needs to be a global for this.
                # ins.seek(size-header.__class__.size,1)
                # ModReader.recHeader.size
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
                # header[1]-24,1 20 for Oblivion, 24 for others.
                # There needs to be a global for this.
                # ins.seek(size-header.__class__.size,1)
                # ModReader.recHeader.size
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
    """Updates map of GMST eids to fids in bash\db\Oblivion_ids.pkl, based either
    on a list of new eids or the gmsts in the specified mod file. Updated pkl file
    is dropped in Mopy directory."""
    #--Data base
    import cPickle
    fids = cPickle.load(GPath(bush.game.pklfile).open('r'))['GMST']
    maxId = max(fids.values())
    maxId = max(maxId,0xf12345)
    maxOld = maxId
    print 'maxId',hex(maxId)
    #--Eid list? - if the GMST has a 00000000 eid when looking at it in the cs with nothing
    # but oblivion.esm loaded you need to add the gmst to this list, rebuild the pickle and overwrite the old one.
    for eid in bush.game.gmstEids:
        if eid not in fids:
            maxId += 1
            fids[eid] = maxId
            print '%08X  %08X %s' % (0,maxId,eid)
            #--Source file
    if fileName:
        init(3)
        sorter = lambda a: a.eid
        loadFactory = parsers.LoadFactory(False, MreGmst)
        modInfo = bosh.modInfos[GPath(fileName)]
        modFile = parsers.ModFile(modInfo, loadFactory)
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
        cPickle.dump(outData,GPath(bush.game.pklfile).open('w'))
        print _(u"%d new gmst ids written to "+bush.game.pklfile) % ((maxId - maxOld),)

#------------------------------------------------------------------------------
@mainfunc
def createTagList(inPath='masterlist.txt',outPath='taglist.txt'):
    tags, lootDirtyMods = {}, {}
    reFcomSwitch = re.compile('^[<>]')
    reComment = re.compile(r'^\\.*')
    reMod = re.compile(r'(^[_[(\w!].*?\.es[pm]$)',re.I)
    reBashTags = re.compile(r'(%\s+{{BASH:|TAG\s+{{BASH:)([^}]+)(}})(.*remove \[)?([^\]]+)?(\])?')
    reDirty = re.compile(r'.*?IF\s*\(\s*([a-fA-F0-9]*)\s*\|\s*[\"\'](.*?)[\'\"]\s*\).*?DIRTY:\s*(.*?)\s*$')
    ins = GPath(inPath).open('r')
    mod = None
    for line in ins:
        line = reFcomSwitch.sub('',line)
        line = reComment.sub('',line)
        maMod = reMod.match(line)
        maBashTags = reBashTags.match(line)
        maDirty = reDirty.match(line)
        if maMod:
            mod = maMod.group(1)
        elif maBashTags and mod:
            if maBashTags.group(4):
                modTags = ''.join(maBashTags.groups())
            else:
                modTags = ''.join(maBashTags.groups()[0:3])
            tags[mod] = modTags
        elif maDirty:
            dirty = ''.join(maDirty.groups())
            if mod in tags:
                tags[mod] += '\n' + dirty
            else:
                tags[mod] = dirty
        elif "http://cs.elderscrolls.com/constwiki/index.php/TES4Edit_Cleaning_Guide" in line:
            if mod in tags:
                tags[mod] += '\n' + line[:-1]
            else:
                tags[mod] = line[:-1]
        elif line.startswith(r"? Masterlist Information: $Revision: "):
            revision = int(line[37:42])
    ins.close()
    tagList = '\ Taglist for Wrye Bash; derived from LOOT Masterlist revision %i.\n' % (revision) + '\% A Bashed Patch suggestion for the mod above.\n\n'
    for mod in sorted(tags,key=str.lower):
        tagList += mod + '\n'
        tagList += tags[mod] + '\n'
        if mod in lootDirtyMods:
            tagList += lootDirtyMods[mod] + '\n'
    out = GPath(outPath).open('w')
    out.write(tagList[:-1])
    out.close()
#------------------------------------------------------------------------------
@mainfunc
def modCheck(fileName=None):
    """Reports on various problems with mods."""
    reBadVarName = re.compile('^[_0-9]')
    init(3)
    loadFactory = parsers.LoadFactory(False, MreWeap)
    for modInfo in bosh.modInfos.values():
        print '\n',modInfo.name
        modFile = parsers.ModFile(modInfo, loadFactory)
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
    testClasses = (MreSkil,)
    loadFactory = parsers.LoadFactory(False, *testClasses)
    #--Src file
    srcInfo = bosh.modInfos[GPath(srcName)]
    srcFile = parsers.ModFile(srcInfo, loadFactory)
    srcFile.load(True)
    #return
    #--Dst file
    loadFactory = parsers.LoadFactory(True, *testClasses)
    dstInfo = bosh.modInfos[GPath(dstName)]
    dstFile = parsers.ModFile(dstInfo, loadFactory)
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
    testClasses = (MreDial,MreInfo)
    loadFactory = parsers.LoadFactory(False, *testClasses)
    #--Src file
    srcInfo = bosh.modInfos[GPath(srcName)]
    srcFile = parsers.ModFile(srcInfo, loadFactory)
    srcFile.load(True)
    #return
    #--Dst file
    loadFactory = parsers.LoadFactory(True, *testClasses)
    dstInfo = bosh.modInfos[GPath(dstName)]
    dstFile = parsers.ModFile(dstInfo, loadFactory)
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
    testClasses = [MreRegn,]
##    testClasses = [bosh.MreRefr,bosh.MreCell,bosh.MreWrld]
    loadFactory = parsers.LoadFactory(False, *testClasses)
    modInfo = bosh.modInfos[GPath(fileName)]
    modFile = parsers.ModFile(modInfo, loadFactory)
    modFile.load(True)
    class disablePrint:
        def write(self,text):
            pass
    if skipPrint == True:
        oOut = sys.stdout
        sys.stdout = disablePrint()
    for typed in bush.game.modFile.topTypes:
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
    modFile.fileInfo.readHeader()
    modFile.fileInfo.setType('esp')

@mainfunc
def dumpLSCR(fileName=u'Oblivion.esm'):
    def strFid(longFid):
        return u'%s: %06X' % (longFid[0].stail, longFid[1])
    bosh.initBosh()
    fileName = GPath(fileName)
    #--Load up in CBash
    import cint
    with cint.ObCollection(ModsPath=bass.dirs['mods'].s) as Current:
        modFile = Current.addMod(fileName.stail)
        Current.load()
        #--Dump the info
        outFile = GPath(fileName.root+u'.csv')
        with outFile.open('w') as file:
            count = 0
            file.write(u'"FormId"\t"EditorID"\t"ICON"\t"DESC"\n')
            for lscr in modFile.LSCR:
                file.write(u'"%s"\t"%s"\t"%s"\t"%s"\n' % (strFid(lscr.fid),lscr.eid,lscr.iconPath,lscr.text))
                count += 1
            print u'Dumped %i records from "%s" to "%s".' % (count, fileName.stail, outFile.s)

@mainfunc
def createLSCR(*args):
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('modName',
                        type=Path,
                        help='Name of the ESP to create.',
                        )
    parser.add_argument('-textures',
                        action='store',
                        type=Path,
                        default=GPath('textures'),
                        dest='ddsPath',
                        help="Path to the 'Textures' folder containing the DDS textures for the Loading Screens.  Default: 'textures'",
                        )
    parser.add_argument('-formids',
                        action='store',
                        type=Path,
                        default=GPath('formids.txt'),
                        dest='formidPath',
                        help="Path to the text file containing FormIDs of records to overwrite.  Default: 'formids.txt'",
                        )
    parser.add_argument('-descs',
                        action='store',
                        type=Path,
                        default=GPath('descs.txt'),
                        dest='descPath',
                        help="Path to the text file containing strings to be used as DESC subrecords.  Default: 'descs.txt'",
                        )
    parser.add_argument('-lnams',
                        action='store',
                        type=Path,
                        default=GPath('lnams.txt'),
                        dest='lnamPath',
                        help="Path to the text file containing FormIDs to be added to each Loading Screen as a Direct LNAM subrecord.  Default: 'lnams.txt'",
                        )
    parser.add_argument('-noreuse',
                        action='store_false',
                        default=True,
                        dest='reuse',
                        help='If specified, when more LSCR records need to be created, but available textures or DESC strings have run out, these field will be left blank.',
                        )
    parser.add_argument('-clearlnam',
                        action='store_true',
                        default=False,
                        dest='clearLNAM',
                        help='If specified, when override records are created, their LNAM subrecords will be cleared out.',
                        )
    parser.add_argument('-removedesc',
                        action='store_true',
                        default=False,
                        dest='removeDESC',
                        help='If specified, override records will always have their DESC subrecord overwritten, even if no DESC subrecords are available to use.  In otherwords, the DESC subrecord will be blanked.',
                        )
    parser.add_argument('-keepemptylnam',
                        action='store_true',
                        default=False,
                        dest='keepEmptyLnam',
                        help='If specified, when override records are created, if the original record had no LNAM data, then no new LNAM data will be added.',
                        )
    opts = parser.parse_args(list(args))

    import cint
    import random

    class LSCRData(object):
        def __init__(self,ddsDirectory,formIDFileName,descFileName,lnamFileName,reuse,clearLNAM):
            # Defaults
            self.DDS = []
            self.DESC = []
            self.LNAM = []
            self.fids_eids = []
            self.masters = set()
            self.missingMasters = set()
            self.reuse = reuse

            self.usedDDS = []
            self.usedDESC = []
            self.allDDS = False # True when all DDS files have been used at least once
            self.allDESC = False # Same as above

            bosh.initBosh()
            # Collection DDS Files
            self.loadDDS(ddsDirectory)
            # Read Fids file
            self.loadFIDS(formIDFileName)
            # Read DESC file
            self.loadDESCS(descFileName)
            # Read LNAM file
            self.loadLNAMS(lnamFileName,clearLNAM)

            self.updateMasters()

        def _getNext(self,notUsed,used,all):
            if not notUsed:
                setattr(self,all,True)
                if self.reuse and used:
                    notUsed = used[:]
                    used = []
                    random.shuffle(notUsed)
                else:
                    return None
            ret = notUsed.pop()
            used.append(ret)
            return ret

        def getNextDDS(self): return self._getNext(self.DDS,self.usedDDS,'allDDS')
        def getNextDESC(self): return self._getNext(self.DESC,self.usedDESC,'allDESC')

        def loadDDS(self,textureDir):
            ddsDir = GPath(os.getcwd()).join(textureDir,'menus','loading')
            self.DDS = [GPath('Menus').join('Loading',x) for x in ddsDir.list() if x.cext == '.dds']
            random.shuffle(self.DDS)

        def loadFIDS(self,fidFile):
            fidFile = GPath(fidFile)
            if not fidFile.exists():
                print "WARNING: FormID text file '%s' could not be found.  All LSCR records will be new records." % (fidFile.s)
            #--Parse the FormID file
            self.fids_eids = []
            try:
                with fidFile.open('r') as file:
                    for line in file:
                        # Format is:
                        # modname: hexformid [optional editor id]
                        if ':' not in line: continue
                        parts = line.split(':')
                        if len(parts) != 2: continue
                        masterName = parts[0].strip()
                        parts = parts[1].split()
                        if len(parts) not in [1,2]:  continue
                        if len(parts) == 2:
                            eid = parts[1].strip()
                        else:
                            eid = None
                        try:
                            recordId = long(parts[0],16)
                            if recordId < 0 or recordId > 0xFFFFFF:
                                continue
                        except:
                            continue
                        masterName = bass.dirs['mods'].join(masterName)
                        self.fids_eids.append((cint.FormID(masterName.tail,recordId),eid))
            except Exception as e:
                print "WARNING: An error occurred while reading FormID text file '%s':\n%s\n" % (fidFile.s,e)

        def loadDESCS(self,descFile):
            descFile = GPath(descFile)
            if not descFile.exists():
                print "WARNING: DESC text file '%s' could not be found.  All LSCR records will need to be modified by hand to have a DESC subrecord." % (descFile.s)
            #--Parse DESC file
            self.DESC = []
            try:
                with descFile.open('r') as file:
                    for line in file:
                        #--Optional line has 'DESC' at the beginning
                        if line.startswith('DESC'): continue
                        line = line.strip()
                        if len(line) > 0:
                            self.DESC.append(line)
            except Exception as e:
                print "WARNING: An error occurred while reading DESC text file '%s':\n%s\n" % (descFile.s,e)
            random.shuffle(self.DESC)

        def loadLNAMS(self,lnamFile,clearLNAM):
            lnamFile = GPath(lnamFile)
            if not lnamFile.exists():
                if clearLNAM:
                    print "WARNING: LNAM text file '%s' could not be found, and this tool is currently set to clear all LNAM subrecords from override records.  No LSCR records will have LNAM data." % (lnamFile.s)
                else:
                    print "WARNING: LNAM text file '%s' could not be found.  All new LSCR records will have no LNAM data." % (lnamFile.s)
                return
            self.LNAM = []
            try:
                with lnamFile.open('r') as file:
                    for line in file:
                        if ':' not in line: continue
                        parts = line.split(':')
                        if len(parts) != 2: continue
                        masterName = parts[0].strip()
                        parts = parts[1].split()
                        try:
                            recordId = long(parts[0],16)
                            if recordId < 0 or recordId > 0xFFFFFF:
                                continue
                        except:
                            continue
                        masterName = bass.dirs['mods'].join(masterName)
                        self.LNAM.append(cint.FormID(masterName.tail,recordId))
            except Exception as e:
                print "WARNING: An error occurred while reading LNAM text file '%s':\n%s\n" % (lnamFile.s,e)

        def updateMasters(self):
            self.masters = set()
            self.missingMasters = set()
            for fid,eid in self.fids_eids:
                master = bass.dirs['mods'].join(fid[0])
                if master.exists():
                    self.masters.add(fid[0])
                else:
                    self.missingMasters.add(fid[0])
            for lnam in self.LNAM:
                master = bass.dirs['mods'].join(lnam[0])
                if master.exists():
                    self.masters.add(fid[0])
                else:
                    self.missingMasters.add(fid[0])

    bosh.initBosh()
    modName = bass.dirs['mods'].join(opts.modName)
    #--Parse data
    data = LSCRData(opts.ddsPath,opts.formidPath,opts.descPath,opts.lnamPath,opts.reuse,opts.clearLNAM)
    if not data.DESC and not data.DDS and not data.fids_eids:
        print "WARNING: No DESC subrecords, no textures, and no record overrides were found.  Quiting operation."
        return
    #--Check for existing mods
    if modName.exists():
        print "WARNING: Plugin '%s' already exists, creating backup: '%s'" % (modName.stail,modName.backup)
        modName.moveTo(modName.backup)
    #--Check for loaded data
    if not data.DESC:
        print "WARNING: No DESC subrecords were loaded."
    else:
        print 'Loaded %i DESC subrecords.' % (len(data.DESC))
    if not data.DDS:
        print "WARNING: No textures were found."
    else:
        print 'Loaded %i textures.' % (len(data.DDS))
    if not data.LNAM:
        if opts.clearLNAM:
            print "WARNING: No LNAM subrecords were loaded.  No records will have LNAM data."
        else:
            print "WARNING: No LNAM subrecords were loaded.  No new records will have LNAM data."
    else:
        print 'Loaded %i LNAM subrecords.' % (len(data.LNAM))
    #--Check for missing masters
    for master in data.missingMasters:
        print "WARNING: Expected master file '%s' is not present.  Applicable data from those records cannot be verified and/or copied." % (master.stail)
    #--Now do the mod creation
    with cint.ObCollection(ModsPath=bass.dirs['mods'].s) as Current:
        for master in data.masters:
            Current.addMod(master.stail)
        modFile = Current.addMod(modName.stail,CreateNew=True)
        Current.load()
        # Create overrides for each fid
        extraDDS = set()
        extraDESC = set()
        for fid,eid in data.fids_eids:
            if fid[0] not in data.masters:
                print "WARNING: LSCR record '%s' master is missing.  Data from the original record cannot be copied." % (fid[0].s)
                # Missing master, so "create new" record instead
                record = modFile.create_LSCR(fid)
                #--EditorID
                if eid is not None:
                    record.eid = eid
                #--Texture
                icon = data.getNextDDS()
                if icon:
                    record.iconPath = icon.s
                #--Description
                text = data.getNextDESC()
                if text:
                    record.text = text
                #--LNAM
                for lnam in data.LNAM:
                    loc = record.create_location()
                    loc.direct = lnam
                #--Did this record have reused DESC/DDS's?
                if data.allDDS: extraDDS.add(fid)
                if data.allDESC: extraDESC.add(fid)
            else:
                # Master is present, so create by override
                masterFile = Current.LookupModFile(fid[0].stail)
                record = masterFile.LookupRecord(fid)
                if not record:
                    print "WARNING: Could not locate record %s in master file '%s'." % (fid,fid[0].stail)
                    continue
                if record._Type != 'LSCR':
                    print 'WARNING: Record %s is not a Loading Screen, skipping!' % (fid)
                    continue
                override = record.CopyAsOverride(modFile)
                if not override:
                    print 'WARNING: Error copying record %s into the mod.' % (fid)
                    continue
                #--EditorID
                if eid is not None:
                    override.eid = eid
                #--Texture
                icon = data.getNextDDS()
                if icon:
                    override.iconPath = icon.s
                #--Description
                text = data.getNextDESC()
                if text:
                    override.text = text
                elif opts.removeDESC:
                    override.text = ' '
                #--LNAM
                if opts.keepEmptyLnam and len(override.locations_list) == 0:
                    pass
                else:
                    if opts.clearLNAM:
                        override.locations = None
                    for lnam in data.LNAM:
                        loc = override.create_location()
                        loc.direct = lnam
                if data.allDDS: extraDDS.add(fid)
                if data.allDESC: extraDESC.add(fid)
        # Use any left over DDS's as new records
        if not data.allDDS:
            for dds in data.DDS:
                record = modFile.create_LSCR()
                #--Texture
                record.iconPath = dds.s
                #--Description
                text = data.getNextDESC()
                if text:
                    record.text = text
                #--LNAM
                for lnam in data.LNAM:
                    loc = record.create_location()
                    loc.direct = lnam
                if data.allDESC: extraDESC.add(record.fid)
        modFile.save()
        print
        print 'Operation complete.'
        if len(data.fids_eids) > 0:
            for master in data.masters:
                fids = [x for x in data.fids_eids if x[0][0] == master]
                num = len(fids)
                print "Created %i override records for '%s'." % (num, master.s)
        if len(data.DDS) + len(data.usedDDS) > len(data.fids_eids):
            print 'Created %i new records.' % (len(data.DDS) + len(data.usedDDS) - len(data.fids_eids))
        if extraDESC:
            if data.reuse:
                print "More records were made than DESC subrecords were available.  %i records reused another record's DESC." % (len(extraDESC))
            else:
                print "WARNING: More records were made than DESC subrecords were available.  %i records have no DESC subrecord." % (len(extraDESC))
        if extraDDS:
            if data.reuse:
                print "More records were made than textures were available.  %i records reused another record's texture." % (len(extraDDS))
            else:
                print "WARNING: More records were made than textures were available.  %i records have no texture." % (len(extraDDS))

# Temp ------------------------------------------------------------------------
"""Very temporary functions."""
#--Temp
@mainfunc
def balancer(fileName=None):
    """Generates part of the balancing scripts for Cobl Races Balanced."""
    init(3)
    loadFactory = parsers.LoadFactory(False, MreRace)
    modInfo = bosh.modInfos[GPath('Cobl Races.esp')]
    balInfo = bosh.modInfos[GPath('Cobl Races - Balanced.esp')]
    modFile = parsers.ModFile(modInfo, loadFactory)
    balFile = parsers.ModFile(balInfo, loadFactory)
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

# Zip/Installer Stuff --------------------------------------------------------------------
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
        reListArchive = re.compile('(Path|Size|CRC|Attributes) = (.+)')
        path = size = isDir = 0

        cmd = '"%s" l "%s"' % (bolt.exe7z, self.path.s)
        cmd = cmd.encode('mbcs')
        proc = Popen(cmd, stdout=PIPE, stdin=PIPE)
        out = proc.stdout
        for line in out:
            print line,
            maList = reListArchive.match(line)
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
                    path = size = 0
        out.close()
        returncode = proc.wait()
        print 'result', returncode

    def extract(self):
        """Extracts specified files from archive."""
        command = '"%s" x "%s" -y -oDumpster @listfile.txt -scsWIN' % (
            bolt.exe7z, self.path.s)
        command = command.encode('mbcs')
        out = Popen(command, stdout=PIPE, stdin=PIPE).stdout
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

@mainfunc
def create_sample_project(read_file=None,dest_path=None):
    """create a sample project for BAIN testing from a text file list of paths - ie as exported by 'list structure'"""
    if not read_file:
        print _(u"read file must be specified")
        return
    if not dest_path:
        dest_path = GPath(os.getcwd()).join("Test BAIN Project")
    try:
        ins = GPath(read_file).open("r")
    except:
        read_file = GPath(os.getcwd()).join(read_file)
        ins = GPath(read_file).open("r")
    for path in ins:
        if path[0] in [";","#"]: continue #comment lines
        dest_file = dest_path.join(path[:-1])
        try:
            file = dest_file.open("w")
        except:
            dest_dir = dest_path.shead()
            os.makedirs(dest_dir.s)
            file = dest_file.open("w")
        file.write("test file")
        file.close()
    ins.close()

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
