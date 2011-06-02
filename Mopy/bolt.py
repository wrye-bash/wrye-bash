# GPL License and Copyright Notice ============================================
#  This file is part of Wrye Bolt.
#
#  Wrye Bolt is free software; you can redistribute it and/or
#  modify it under the terms of the GNU General Public License
#  as published by the Free Software Foundation; either version 2
#  of the License, or (at your option) any later version.
#
#  Wrye Bolt is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
#
#  You should have received a copy of the GNU General Public License
#  along with Wrye Bolt; if not, write to the Free Software Foundation,
#  Inc., 59 Temple Place - Suite 330, Boston, MA  02111-1307, USA.
#
#  Wrye Bolt copyright (C) 2005, 2006, 2007, 2008, 2009 Wrye
#
# =============================================================================

# Imports ----------------------------------------------------------------------
#-- Use the 'with' statement for Python 2.5
from __future__ import with_statement
#--Standard
import cPickle
import copy
import locale
import os
import re
import shutil
import struct
import sys
import time
import subprocess
import collections
from subprocess import Popen, PIPE
import types
from binascii import crc32
import ConfigParser
#-- To make commands executed with Popen hidden
if os.name == 'nt':
    startupinfo = subprocess.STARTUPINFO()
    try: startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
    except:
        import _subprocess
        startupinfo.dwFlags |= _subprocess.STARTF_USESHOWWINDOW


# Unicode Strings -------------------------------------------------------------
# See Python's "aliases.py" for a list of possible encodings
UnicodeEncodings = (
    # Encodings we'll try for conversion to unicode
    'UTF8',     # Standard encoding
    'U16',      # Some files use UTF-16 though
    'cp1252',   # Western Europe
    'cp500',    # Western Europe
    'cp932',    # Japanese SJIS-win 
    'mbcs',     # Multi-byte character set (depends on the Windows locale)
    )
NumEncodings = len(UnicodeEncodings)

def Unicode(name):
    if not bUseUnicode: return name #don't change if not unicode mode.
    if isinstance(name,unicode): return name
    if isinstance(name,str):
        for i in range(NumEncodings):
            try:
                return unicode(name,UnicodeEncodings[i])
            except UnicodeDecodeError:
                if i == NumEncodings - 1:
                    raise
    return name

def Encode(name,tryFirstEncoding=False):
    if not bUseUnicode: return name #don't change if not unicode mode.
    if isinstance(name,str): return name
    if isinstance(name,unicode):
        if tryFirstEncoding:
            try:
                return name.encode(tryFirstEncoding)
            except UnicodeEncodeError: 
                deprint("Unable to encode '%s' in %s" % (name, tryFirstEncoding))
                pass
        for i in range(NumEncodings):
            try:
                return name.encode(UnicodeEncodings[i])
            except UnicodeEncodeError:
                if i == NumEncodings - 1:
                    raise
    return name

# Localization ----------------------------------------------------------------
#used instead of bosh.inisettings['EnableUnicode'] to avoid circular imports
#has to be set by bolt before any Path's are instantiated
#ini gets read twice, but that's a minor hit at startup
bUseUnicode = False
if os.path.exists('bash.ini'):
    bashIni = ConfigParser.ConfigParser()
    bashIni.read('bash.ini')
    for section in bashIni.sections():
        options = bashIni.items(section)
        for key,value in options:
            if key == 'benableunicode':
                bUseUnicode = bashIni.getboolean(section,key)
                break

reTrans = re.compile(r'^([ :=\.]*)(.+?)([ :=\.]*$)')
def compileTranslator(txtPath,pklPath):
    """Compiles specified txtFile into pklFile."""
    reSource = re.compile(r'^=== ')
    reValue = re.compile(r'^>>>>\s*$')
    reNewLine = re.compile(r'\\n')
    #--Scan text file
    translator = {}
    def addTranslation(key,value):
        key,value   = key[:-1],value[:-1]
        if key and value:
            key = reTrans.match(key).group(2)
            value = reTrans.match(value).group(2)
            translator[key] = value
    key,value,mode = '','',0
    textFile = file(txtPath)
    for line in textFile:
        #--Begin key input?
        if reSource.match(line):
            addTranslation(key,value)
            key,value,mode = '','',1
        #--Begin value input?
        elif reValue.match(line):
            mode = 2
        elif mode == 1:
            key += line
        elif mode == 2:
            value += line
    addTranslation(key,value) #--In case missed last pair
    textFile.close()
    #--Write translator to pickle
    filePath = pklPath
    tempPath = filePath+'.tmp'
    cPickle.dump(translator,open(tempPath,'w'))
    if os.path.exists(filePath): os.remove(filePath)
    os.rename(tempPath,filePath)

#--Do translator test and set
if locale.getlocale() == (None,None):
    locale.setlocale(locale.LC_ALL,'')
language = locale.getlocale()[0].split('_',1)[0]
if language.lower() == 'german': language = 'de' #--Hack for German speakers who aren't 'DE'.
languagePkl, languageTxt = (os.path.join('data',language+ext) for ext in ('.pkl','.txt'))
#--Recompile pkl file?
if os.path.exists(languageTxt) and (
    not os.path.exists(languagePkl) or (
        os.path.getmtime(languageTxt) > os.path.getmtime(languagePkl)
        )
    ):
    compileTranslator(languageTxt,languagePkl)
#--Use dictionary from pickle as translator
if os.path.exists(languagePkl):
    pklFile = open(languagePkl)
    reEscQuote = re.compile(r"\\'")
    _translator = cPickle.load(pklFile)
    pklFile.close()
    def _(text,encode=True):
        text = Encode(text,'mbcs')
        if encode: text = reEscQuote.sub("'",text.encode('string_escape'))
        head,core,tail = reTrans.match(text).groups()
        if core and core in _translator:
            text = head+_translator[core]+tail
        if encode: text = text.decode('string_escape')
        if bUseUnicode: text = unicode(text,'mbcs')
        return text
else:
    def _(text,encode=True): return text

# Errors ----------------------------------------------------------------------
class BoltError(Exception):
    """Generic error with a string message."""
    def __init__(self,message):
        self.message = message
    def __str__(self):
        return self.message

#------------------------------------------------------------------------------
class AbstractError(BoltError):
    """Coding Error: Abstract code section called."""
    def __init__(self,message=_('Abstract section called.')):
        BoltError.__init__(self,message)

#------------------------------------------------------------------------------
class ArgumentError(BoltError):
    """Coding Error: Argument out of allowed range of values."""
    def __init__(self,message=_('Argument is out of allowed ranged of values.')):
        BoltError.__init__(self,message)

#------------------------------------------------------------------------------
class StateError(BoltError):
    """Error: Object is corrupted."""
    def __init__(self,message=_('Object is in a bad state.')):
        BoltError.__init__(self,message)

#------------------------------------------------------------------------------
class UncodedError(BoltError):
    """Coding Error: Call to section of code that hasn't been written."""
    def __init__(self,message=_('Section is not coded yet.')):
        BoltError.__init__(self,message)

#------------------------------------------------------------------------------
class CancelError(BoltError):
    """User pressed 'Cancel' on the progress meter."""
    def __init__(self,message=_('Action aborted by user.')):
        BoltError.__init__(self, message)

class SkipError(BoltError):
    """User pressed 'Skip' on the progress meter."""
    def __init__(self,message=_('Action skipped by user.')):
        BoltError.__init__(self,message)

#------------------------------------------------------------------------------
class PermissionError(BoltError):
    """Wrye Bash doesn't have permission to access the specified file/directory."""
    def __init__(self,message=None):
        message = message or _('Access is denied.')
        BoltError.__init__(self,message)

# LowStrings ------------------------------------------------------------------
class LString(object):
    """Strings that compare as lower case strings."""
    __slots__ = ('_s','_cs')

    def __init__(self,s):
        if isinstance(s,LString): s = s._s
        self._s = s
        self._cs = s.lower()

    def __getstate__(self):
        """Used by pickler. _cs is redundant,so don't include."""
        return self._s

    def __setstate__(self,s):
        """Used by unpickler. Reconstruct _cs."""
        self._s = s
        self._cs = s.lower()

    def __len__(self):
        return len(self._s)

    def __str__(self):
        return self._s

    def __repr__(self):
        return "bolt.LString("+repr(self._s)+")"

    def __add__(self,other):
        return LString(self._s + other)

    #--Hash/Compare
    def __hash__(self):
        return hash(self._cs)
    def __cmp__(self, other):
        if isinstance(other,LString): return cmp(self._cs, other._cs)
        else: return cmp(self._cs, other.lower())

# Paths -----------------------------------------------------------------------
#------------------------------------------------------------------------------
_gpaths = {}
Path = None
def GPath(name):
    """Returns common path object for specified name/path."""
    if name is None: return None
    elif not name: norm = name
    elif isinstance(name,Path): norm = name._s
    else: norm = os.path.normpath(name)
    path = _gpaths.get(norm)
    if path != None: return path
    else: return _gpaths.setdefault(norm,Path(norm))

#------------------------------------------------------------------------------
class Path(object):
    """A file path. May be just a directory, filename or full path."""
    """Paths are immutable objects that represent file directory paths."""

    #--Class Vars/Methods -------------------------------------------
    norm_path = {} #--Dictionary of paths
    mtimeResets = [] #--Used by getmtime
    ascii = '[\x00-\x7F]'
    japanese_hankana = '[\xA1-\xDF]'
    japanese_zenkaku ='[\x81-\x9F\xE0-\xFC][\x40-\x7E\x80-\xFC]'
    reChar = re.compile('('+ascii+'|'+japanese_hankana+'|'+japanese_zenkaku+')', re.M)

    @staticmethod
    def get(name):
        """Returns path object for specified name/path."""
        if isinstance(name,Path): norm = name._s
        else: norm = os.path.normpath(name)
        return Path.norm_path.setdefault(norm,Path(norm))

    @staticmethod
    def getNorm(name):
        """Return the normpath for specified name/path object."""
        if not name: return name
        elif isinstance(name,Path): return name._s
        else: return os.path.normpath(name)

    @staticmethod
    def getCase(name):
        """Return the normpath+normcase for specified name/path object."""
        if not name: return name
        if isinstance(name,Path): return name._cs
        else: return os.path.normcase(os.path.normpath(name))

    @staticmethod
    def getcwd():
        return Path(os.getcwd())

    def setcwd(self):
        """Set cwd. Works as either instance or class method."""
        if isinstance(self,Path): dir = self._s
        else: dir = self
        os.chdir(dir)

    @staticmethod
    def mbSplit(path):
        """Split path to consider multibyte character boundary."""
        # Should also add Chinese fantizi and zhengtizi, Korean Hangul, etc.
        match = Path.reChar.split(path)
        result = []
        curResult = ''
        resultAppend = result.append
        for c in match:
            if c == '\\':
                resultAppend(curResult)
                curResult = ''
            else:
                curResult += c
        resultAppend(curResult)
        return result

    #--Instance stuff --------------------------------------------------
    #--Slots: _s is normalized path. All other slots are just pre-calced
    #  variations of it.
    __slots__ = ('_s','_cs','_csroot','_sroot','_shead','_stail','_ext','_cext','_sbody','_csbody')

    def __init__(self, name):
        """Initialize."""
        if bUseUnicode:
            if isinstance(name,Path):
                self.__setstate__(unicode(name._s,'UTF8'))
            elif isinstance(name,unicode):
                self.__setstate__(name)
            else:
                self.__setstate__(Unicode(name))
                ##try:
                ##    self.__setstate__(unicode(str(name),'UTF8'))
                ##except UnicodeDecodeError:
                ##    try:
                ##        # A fair number of file names require UTF16 instead...
                ##        self.__setstate__(unicode(str(name),'U16'))
                ##    except UnicodeDecodeError:
                ##        try:
                ##            self.__setstate__(unicode(str(name),'cp1252'))
                ##        except UnicodeDecodeError:
                ##            # and one really really odd one (in SOVVM mesh bundle) requires cp500 (well at least that works unlike UTF8,16,32,32BE (the others I tried first))!
                ##            self.__setstate__(unicode(str(name),'cp500'))
        else:
            if isinstance(name,Path):
                self.__setstate__(name._s)
            elif isinstance(name,unicode):
                self.__setstate__(name)
            else:
                self.__setstate__(str(name))

    def __getstate__(self):
        """Used by pickler. _cs is redundant,so don't include."""
        return self._s

    def __setstate__(self,norm):
        """Used by unpickler. Reconstruct _cs."""
        self._s = norm
        self._cs = os.path.normcase(self._s)
        self._sroot,self._ext = os.path.splitext(self._s)
        if bUseUnicode:
            self._shead,self._stail = os.path.split(self._s)
        else:
            pathParts = Path.mbSplit(self._s)
            if len(pathParts) == 1:
                self._shead = ''
                self._stail = pathParts[0]
            else:
                self._shead = '\\'.join(pathParts[0:-1])
                self._stail = pathParts[-1]
        self._cext = os.path.normcase(self._ext)
        self._csroot = os.path.normcase(self._sroot)
        self._sbody = os.path.basename(os.path.splitext(self._s)[0])
        self._csbody = os.path.normcase(self._sbody)

    def __len__(self):
        return len(self._s)

    def __repr__(self):
        return "bolt.Path("+repr(self._s)+")"

    def __str__(self):
        return self._s
    #--Properties--------------------------------------------------------
    #--String/unicode versions.
    @property
    def s(self):
        "Path as string."
        return self._s
    @property
    def cs(self):
        "Path as string in normalized case."
        return self._cs
    @property
    def csroot(self):
        "Root as string."
        return self._csroot
    @property
    def sroot(self):
        "Root as string."
        return self._sroot
    @property
    def shead(self):
        "Head as string."
        return self._shead
    @property
    def stail(self):
        "Tail as string."
        return self._stail
    @property
    def sbody(self):
        "For alpha\beta.gamma returns beta as string."
        return self._sbody
    @property
    def csbody(self):
        "For alpha\beta.gamma returns beta as string in normalized case."
        return self._csbody

    #--Head, tail
    @property
    def headTail(self):
        "For alpha\beta.gamma returns (alpha,beta.gamma)"
        return map(GPath,(self._shead,self._stail))
    @property
    def head(self):
        "For alpha\beta.gamma, returns alpha."
        return GPath(self._shead)
    @property
    def tail(self):
        "For alpha\beta.gamma, returns beta.gamma."
        return GPath(self._stail)
    @property
    def body(self):
        "For alpha\beta.gamma, returns beta."
        return GPath(self._sbody)

    #--Root, ext
    @property
    def rootExt(self):
        return (GPath(self._sroot),self._ext)
    @property
    def root(self):
        "For alpha\beta.gamma returns alpha\beta"
        return GPath(self._sroot)
    @property
    def ext(self):
        "Extension (including leading period, e.g. '.txt')."
        return self._ext
    @property
    def cext(self):
        "Extension in normalized case."
        return self._cext
    @property
    def temp(self):
        "Temp file path.."
        return self+'.tmp'
    @property
    def backup(self):
        "Backup file path."
        return self+'.bak'

    #--size, atim, ctime
    @property
    def size(self):
        "Size of file or directory."
        if self.isdir():
            join = os.path.join
            getSize = os.path.getsize
            try:
                return sum([sum(map(getSize,map(lambda z: join(x,z),files))) for x,y,files in os.walk(self._s)])
            except ValueError:
                return 0
        else:
            return os.path.getsize(self._s)
    @property
    def atime(self):
        return os.path.getatime(self._s)
    @property
    def ctime(self):
        return os.path.getctime(self._s)

    #--Mtime
    def getmtime(self,maxMTime=False):
        """Returns mtime for path. But if mtime is outside of epoch, then resets
        mtime to an in-epoch date and uses that."""
        if self.isdir() and maxMTime:
            #fastest implementation I could make
            c = []
            cExtend = c.extend
            join = os.path.join
            getM = os.path.getmtime
            [cExtend([getM(join(root,dir)) for dir in dirs] + [getM(join(root,file)) for file in files]) for root,dirs,files in os.walk(self._s)]
            try:
                return max(c)
            except ValueError:
                return 0
        mtime = int(os.path.getmtime(self._s))
        #--Y2038 bug? (os.path.getmtime() can't handle years over unix epoch)
        if mtime <= 0:
            import random
            #--Kludge mtime to a random time within 10 days of 1/1/2037
            mtime = time.mktime((2037,1,1,0,0,0,3,1,0))
            mtime += random.randint(0,10*24*60*60) #--10 days in seconds
            self.mtime = mtime
            Path.mtimeResets.append(self)
        return mtime
    def setmtime(self,mtime):
        os.utime(self._s,(self.atime,int(mtime)))
    mtime = property(getmtime,setmtime,doc="Time file was last modified.")

    #--crc
    @property
    def crc(self):
        """Calculates and returns crc value for self."""
        size = self.size
        crc = 0L
        ins = self.open('rb')
        insRead = ins.read
        while ins.tell() < size:
            crc = crc32(insRead(512),crc)
        ins.close()
        return crc & 0xffffffff

    #--crc with progress bar
    def crcProgress(self, progress):
        """Calculates and returns crc value for self, updating progress as it goes."""
        size = self.size
        progress.setFull(max(size,1))
        crc = 0L
        with self.open('rb') as ins:
            insRead = ins.read
            while ins.tell() < size:
                crc = crc32(insRead(2097152),crc) # 2MB at a time, probably ok
                progress(ins.tell())
        return crc & 0xFFFFFFFF

    #--Path stuff -------------------------------------------------------
    #--New Paths, subpaths
    def __add__(self,other):
        return GPath(self._s + Path.getNorm(other))
    def join(*args):
        norms = [Path.getNorm(x) for x in args]
        return GPath(os.path.join(*norms))
    def list(self):
        """For directory: Returns list of files."""
        if not os.path.exists(self._s): return []
        return [GPath(x) for x in os.listdir(self._s)]
    def walk(self,topdown=True,onerror=None,relative=False):
        """Like os.walk."""
        if relative:
            start = len(self._s)
            return ((GPath(x[start:]),[GPath(u) for u in y],[GPath(u) for u in z])
                for x,y,z in os.walk(self._s,topdown,onerror))
        else:
            return ((GPath(x),[GPath(u) for u in y],[GPath(u) for u in z])
                for x,y,z in os.walk(self._s,topdown,onerror))
    def split(self):
        """Splits the path into each of it's sub parts.  IE: C:\Program Files\Bethesda Softworks
           would return ['C:','Program Files','Bethesda Softworks']"""
        dirs = []
        drive, path = os.path.splitdrive(self.s)
        path = path.strip(os.path.sep)
        l,r = os.path.split(path)
        while l != '':
            dirs.append(r)
            l,r = os.path.split(l)
        dirs.append(r)
        if drive != '':
            dirs.append(drive)
        dirs.reverse()
        return dirs
    def relpath(self,path):
        try:
            return GPath(os.path.relpath(self._s,Path.getNorm(path)))
        except:
            # Python 2.5 doesn't have os.path.relpath, so we'll have to implement our own
            path = GPath(path)
            if path.isfile(): path = path.head
            splitSelf = self.split()
            splitOther = path.split()
            relPath = []
            while len(splitSelf) > 0 and len(splitOther) > 0 and splitSelf[0] == splitOther[0]:
                splitSelf.pop(0)
                splitOther.pop(0)
            while len(splitOther) > 0:
                splitOther.pop(0)
                relPath.append('..')
            relPath.extend(splitSelf)
            return GPath(os.path.join(*relPath))

    #--File system info
    #--THESE REALLY OUGHT TO BE PROPERTIES.
    def exists(self):
        return os.path.exists(self._s)
    def isdir(self):
        return os.path.isdir(self._s)
    def isfile(self):
        return os.path.isfile(self._s)
    def isabs(self):
        return os.path.isabs(self._s)

    #--File system manipulation
    def open(self,*args):
        if self._shead and not os.path.exists(self._shead):
            os.makedirs(self._shead)
        return open(self._s,*args)
    def makedirs(self):
        if not self.exists(): os.makedirs(self._s)
    def remove(self):
        if self.exists(): os.remove(self._s)
    def removedirs(self):
        if self.exists(): os.removedirs(self._s)
    def rmtree(self,safety='PART OF DIRECTORY NAME'):
        """Removes directory tree. As a safety factor, a part of the directory name must be supplied."""
        if self.isdir() and safety and safety.lower() in self._cs:
            # Clear ReadOnly flag if set
            cmd = r'attrib -R "%s\*" /S /D' % (self._s)
            cmd = Encode(cmd,'mbcs')
            ins, err = Popen(cmd, stdout=PIPE, startupinfo=startupinfo).communicate()
            shutil.rmtree(self._s)

    #--start, move, copy, touch, untemp
    def start(self, exeArgs=None):
        """Starts file as if it had been doubleclicked in file explorer."""
        if self._cext == '.exe':
            if not exeArgs:
                subprocess.Popen([self.s], close_fds=True)
            else:
                subprocess.Popen(exeArgs, executable=self.s, close_fds=True)
        else:
            os.startfile(self._s)
    def copyTo(self,destName):
        destName = GPath(destName)
        if self.isdir():
            shutil.copytree(self._s,destName._s)
        else:
            if destName._shead and not os.path.exists(destName._shead):
                os.makedirs(destName._shead)
            shutil.copyfile(self._s,destName._s)
            destName.mtime = self.mtime
    def moveTo(self,destName):
        if not self.exists():
            raise StateError(self._s + _(" cannot be moved because it does not exist."))
        destPath = GPath(destName)
        if destPath._cs == self._cs: return
        if destPath._shead and not os.path.exists(destPath._shead):
            os.makedirs(destPath._shead)
        elif destPath.exists():
            os.remove(destPath._s)
        shutil.move(self._s,destPath._s)
    def touch(self):
        """Like unix 'touch' command. Creates a file with current date/time."""
        if self.exists():
            self.mtime = time.time()
        else:
            self.temp.open('w').close()
            self.untemp()
    def untemp(self,doBackup=False):
        """Replaces file with temp version, optionally making backup of file first."""
        if self.temp.exists():
            if self.exists():
                if doBackup:
                    self.backup.remove()
                    shutil.move(self._s, self.backup._s)
                else:
                    os.remove(self._s)
            shutil.move(self.temp._s, self._s)

    #--Hash/Compare
    def __hash__(self):
        return hash(self._cs)
    def __cmp__(self, other):
        if isinstance(other,Path):
            try:
                return cmp(self._cs, other._cs)
            except UnicodeDecodeError:
                try:
                    return cmp(Encode(self._cs), Encode(other._cs))
                except UnicodeError:
                    deprint("Wrye Bash Unicode mode is currently %s" % (['off.','on.'][bUseUnicode]))
                    deprint("unrecovered Unicode error when dealing with %s - presuming non equal." % (self._cs))
                    return False
        else:
            try:
                return cmp(self._cs, Path.getCase(other))
            except UnicodeDecodeError:
                try:
                    return cmp(Encode(self._cs), Encode(Path.getCase(other)))
                except UnicodeError:
                    deprint("Wrye Bash Unicode mode is currently %s." % (['off','on'][bUseUnicode]))
                    deprint("unrecovered Unicode error when dealing with %s - presuming non equal.'" % (self._cs))
                    return False

# Util Constants --------------------------------------------------------------
#--Unix new lines
reUnixNewLine = re.compile(r'(?<!\r)\n')

# Util Classes ----------------------------------------------------------------
#------------------------------------------------------------------------------
class CsvReader:
    """For reading csv files. Handles both command tab separated (excel) formats."""
    def __init__(self,path):
        import csv
        self.ins = path.open('rb')
        format = ('excel','excel-tab')['\t' in self.ins.readline()]
        self.ins.seek(0)
        self.reader = csv.reader(self.ins,format)

    def __iter__(self):
        return self

    def next(self):
        return self.reader.next()

    def close(self):
        self.reader = None
        self.ins.close()

#------------------------------------------------------------------------------
class Flags(object):
    """Represents a flag field."""
    __slots__ = ['_names','_field']

    @staticmethod
    def getNames(*names):
        """Returns dictionary mapping names to indices.
        Names are either strings or (index,name) tuples.
        E.g., Flags.getNames('isQuest','isHidden',None,(4,'isDark'),(7,'hasWater'))"""
        namesDict = {}
        for index,name in enumerate(names):
            if isinstance(name,tuple):
                namesDict[name[1]] = name[0]
            elif name: #--skip if "name" is 0 or None
                namesDict[name] = index
        return namesDict

    #--Generation
    def __init__(self,value=0,names=None):
        """Initialize. Attrs, if present, is mapping of attribute names to indices. See getAttrs()"""
        object.__setattr__(self,'_field',int(value) | 0L)
        object.__setattr__(self,'_names',names or {})

    def __call__(self,newValue=None):
        """Retuns a clone of self, optionally with new value."""
        if newValue is not None:
            return Flags(int(newValue) | 0L,self._names)
        else:
            return Flags(self._field,self._names)

    def __deepcopy__(self,memo={}):
        newFlags=Flags(self._field,self._names)
        memo[id(self)] = newFlags
        return newFlags

    #--As hex string
    def hex(self):
        """Returns hex string of value."""
        return '%08X' % (self._field,)
    def dump(self):
        """Returns value for packing"""
        return self._field

    #--As int
    def __int__(self):
        """Return as integer value for saving."""
        return self._field
    def __getstate__(self):
        """Return values for pickling."""
        return self._field, self._names
    def __setstate__(self,fields):
        """Used by unpickler."""
        self._field = fields[0]
        self._names = fields[1]

    #--As list
    def __getitem__(self, index):
        """Get value by index. E.g., flags[3]"""
        return bool((self._field >> index) & 1)

    def __setitem__(self,index,value):
        """Set value by index. E.g., flags[3] = True"""
        value = ((value or 0L) and 1L) << index
        mask = 1L << index
        self._field = ((self._field & ~mask) | value)

    #--As class
    def __getattr__(self,name):
        """Get value by flag name. E.g. flags.isQuestItem"""
        try:
            names = object.__getattribute__(self,'_names')
            index = names[name]
            return (object.__getattribute__(self,'_field') >> index) & 1 == 1
        except KeyError:
            raise AttributeError(name)

    def __setattr__(self,name,value):
        """Set value by flag name. E.g., flags.isQuestItem = False"""
        if name in ('_field','_names'):
            object.__setattr__(self,name,value)
        else:
            self.__setitem__(self._names[name],value)

    #--Native operations
    def __eq__( self, other):
        """Logical equals."""
        if isinstance(other,Flags):
            return self._field == other._field
        else:
            return self._field == other

    def __ne__( self, other):
        """Logical not equals."""
        if isinstance(other,Flags):
            return self._field != other._field
        else:
            return self._field != other

    def __and__(self,other):
        """Bitwise and."""
        if isinstance(other,Flags): other = other._field
        return self(self._field & other)

    def __invert__(self):
        """Bitwise inversion."""
        return self(~self._field)

    def __or__(self,other):
        """Bitwise or."""
        if isinstance(other,Flags): other = other._field
        return self(self._field | other)

    def __xor__(self,other):
        """Bitwise exclusive or."""
        if isinstance(other,Flags): other = other._field
        return self(self._field ^ other)

    def getTrueAttrs(self):
        """Returns attributes that are true."""
        trueNames = [name for name in self._names if getattr(self,name)]
        trueNames.sort(key = lambda xxx: self._names[xxx])
        return tuple(trueNames)

#------------------------------------------------------------------------------
class DataDict:
    """Mixin class that handles dictionary emulation, assuming that dictionary is is 'data' attribute."""

    def __contains__(self,key):
        return key in self.data
    def __getitem__(self,key):
        if self.data.has_key(key):
            return self.data[key]
        else:
            if isinstance(key, Path):
                return self.data[Path('Oblivion.esm')]
    def __setitem__(self,key,value):
        self.data[key] = value
    def __delitem__(self,key):
        del self.data[key]
    def __len__(self):
        return len(self.data)
    def setdefault(self,key,default):
        return self.data.setdefault(key,value)
    def keys(self):
        return self.data.keys()
    def values(self):
        return self.data.values()
    def items(self):
        return self.data.items()
    def has_key(self,key):
        return self.data.has_key(key)
    def get(self,key,default=None):
        return self.data.get(key,default)
    def pop(self,key,default=None):
        return self.data.pop(key,default)
    def iteritems(self):
        return self.data.iteritems()
    def iterkeys(self):
        return self.data.iterkeys()
    def itervalues(self):
        return self.data.itervalues()

#------------------------------------------------------------------------------
try:
    from collections import MutableSet
except:
    # Python 2.5 compatability
    class MutableSet:
        def __le__(self,other):
            if not isinstance(other, MutableSet):
                return NotImplemented
            if len(self) > len(other):
                return False
            for elem in self:
                if elem not in other:
                    return False
            return True
        def __lt__(self,other):
            if not isinstance(other, MutableSet):
                return NotImplemented
            return len(self) < len(other) and self <= other
        def __gt__(self,other): return other < self
        def __ge__(self,other): return other <= self

        def __eq__(self,other):
            if not isintance(other, MutableSet):
                return NotImplemented
            return len(self) == len(other) and self <= other
        def __ne__(self,other): return not (self == other)

        @classmethod
        def _from_iterable(cls, it):
            return cls(it)

        def __and__(self,other):
            return self._from_iterable(elem for elem in other if elem in self)

        def isdisjoint(self,other):
            for elem in other:
                if elem in self:
                    return False
            return True

        def __or__(self,other):
            chain = (e for s in (self,other) for e in s)
            return self._from_iterable(chain)
        def __sub__(self,other):
            return self._from_iterable(elem for elem in self if elem not in other)
        def __xor__(self,other):
            return (self - other) | (other - self)

        def add(self, value): raise NotImplementedError
        def discard(self, value): raise NotImplementedError

        def remove(self, elem):
            if elem not in self:
                raise KeyError(elem)
            self.discard(elem)

        def pop(self):
            it = iter(self)
            try:
                value = next(it)
            except StopIteration:
                raise KeyError
            self.discard(value)
            return value

        def clear(self):
            try:
                while True:
                    self.pop()
            except KeyError:
                pass

        def __ior__(self, it):
            for value in it:
                self.add(value)
            return self

        def __iand__(self, it):
            for value in (self - it):
                self.discard(value)
            return self

        def __ixor(self, it):
            if it is self:
                self.clear()
            else:
                for value in it:
                    if value in self:
                        self.discard(value)
                    else:
                        self.add(value)
            return self

        def __isub__(self, it):
            if it is self:
                self.clear()
            else:
                for value in it:
                    self.discard(value)
            return self

#------------------------------------------------------------------------------
class OrderedSet(list, MutableSet):
    """A set like object, that remembers the order items were added to it.
       Since it has order, a few list functions were added as well:
        - index(value)
        - __getitem__(index)
        - __call__ -> to enable 'enumerate'
       If an item is dicarded, then later readded, it will be added
       to the end of the set.
    """
    def update(self, *args, **kwdargs):
        if kwdargs: raise TypeError("update() takes no keyword arguments")
        for s in args:
            for e in s:
                self.add(e)

    def add(self, elem):
        if elem not in self:
            self.append(elem)
    def discard(self, elem): self.pop(self.index(elem),None)
    def __or__(self,other):
        left = OrderedSet(self)
        left.update(other)
        return left
    def __repr__(self): return 'OrderedSet%s' % str(list(self))[1:-1]
    def __str__(self): return '{%s}' % str(list(self))[1:-1]

#------------------------------------------------------------------------------
class MemorySet(object):
    """Specialization of the OrderedSet, where it remembers the order of items
       event if they're removed.  Also, combining and comparing to other MemorySet's
       takes this into account:
        a|b -> returns union of a and b, but keeps the ordering of b where possible.
               if an item in a was also in b, but deleted, it will be added to the
               deleted location.
        a&b -> same as a|b, but only items 'not-deleted' in both a and b are marked
               as 'not-deleted'
        a^b -> same as a|b, but only items 'not-deleted' in a but not b, or b but not
               a are marked as 'not-deleted'
        a-b -> same as a|b, but any 'not-deleted' items in b are marked as deleted
    """
    def __init__(self, *args, **kwdargs):
        self.items = OrderedSet(*args, **kwdargs)
        self.mask = [True for i in range(len(self.items))]

    def add(self,elem):
        if elem in self.items: self.mask[self.items.index(elem)] = True
        else:
            self.items.add(elem)
            self.mask.append(True)
    def discard(self,elem):
        if elem in self.items: self.mask[self.items.index(elem)] = False
    discarded = property(lambda self: OrderedSet([x for i,x in enumerate(self.items) if not self.mask[i]]))

    def __len__(self): return sum(self.mask)
    def __iter__(self):
        for i,elem in enumerate(self.items):
            if self.mask[i]: yield self.items[i]
    def __str__(self): return '{%s}' % (','.join(map(repr,self._items())))
    def __repr__(self): return 'MemorySet([%s])' % (','.join(map(repr,self._items())))
    def forget(self, elem):
        # Permanently remove an item from the list.  Don't remember its order
        if elem in self.items:
            idex = self.items.index(elem)
            self.items.discard(elem)
            del self.mask[idex]

    def _items(self): return OrderedSet([x for x in self])

    def __or__(self,other):
        """Return items in self or in other"""
        discards = (self.discarded-other._items())|(other.discarded-self._items())
        right = list(other.items)
        left = list(self.items)

        for idex,elem in enumerate(left):
            # elem is already in the other one, skip
            if elem in right: continue

            # Figure out best place to put it
            if idex == 0:
                # put it in front
                right.insert(0,elem)
            elif idex == len(left)-1:
                # put in in back
                right.append(elem)
            else:
                # Find out what item it comes after
                afterIdex = idex-1
                while afterIdex > 0 and left[afterIdex] not in right:
                    afterIdex -= 1
                insertIdex = right.index(left[afterIdex])+1
                right.insert(insertIdex,elem)
        ret = MemorySet(right)
        ret.mask = [x not in discards for x in right]
        return ret
    def __and__(self,other):
        items = self.items & other.items
        discards = self.discarded | other.discarded
        ret = MemorySet(items)
        ret.mask = [x not in discards for x in items]
        return ret
    def __sub__(self,other):
        discards = self.discarded | other._items()
        ret = MemorySet(self.items)
        ret.mask = [x not in discards for x in self.items]
        return ret
    def __xor__(self,other):
        items = (self|other).items
        discards = items - (self._items()^other._items())
        ret = MemorySet(items)
        ret.mask = [x not in discards for x in items]
        return ret

#------------------------------------------------------------------------------
class MainFunctions:
    """Encapsulates a set of functions and/or object instances so that they can
    be called from the command line with normal command line syntax.

    Functions are called with their arguments. Object instances are called
    with their method and method arguments. E.g.:
    * bish bar arg1 arg2 arg3
    * bish foo.bar arg1 arg2 arg3"""

    def __init__(self):
        """Initialization."""
        self.funcs = {}

    def add(self,func,key=None):
        """Add a callable object.
        func - A function or class instance.
        key - Command line invocation for object (defaults to name of func).
        """
        key = key or func.__name__
        self.funcs[key] = func
        return func

    def main(self):
        """Main function. Call this in __main__ handler."""
        #--Get func
        args = sys.argv[1:]
        attrs = args.pop(0).split('.')
        key = attrs.pop(0)
        func = self.funcs.get(key)
        if not func:
            print "Unknown function/object:", key
            return
        for attr in attrs:
            func = getattr(func,attr)
        #--Separate out keywords args
        keywords = {}
        argDex = 0
        reKeyArg  = re.compile(r'^\-(\D\w+)')
        reKeyBool = re.compile(r'^\+(\D\w+)')
        while argDex < len(args):
            arg = args[argDex]
            if reKeyArg.match(arg):
                keyword = reKeyArg.match(arg).group(1)
                value   = args[argDex+1]
                keywords[keyword] = value
                del args[argDex:argDex+2]
            elif reKeyBool.match(arg):
                keyword = reKeyBool.match(arg).group(1)
                keywords[keyword] = True
                del args[argDex]
            else:
                argDex = argDex + 1
        #--Apply
        apply(func,args,keywords)

#--Commands Singleton
_mainFunctions = MainFunctions()
def mainfunc(func):
    """A function for adding funcs to _mainFunctions.
    Used as a function decorator ("@mainfunc")."""
    _mainFunctions.add(func)
    return func

#------------------------------------------------------------------------------
class PickleDict:
    """Dictionary saved in a pickle file.
    Note: self.vdata and self.data are not reassigned! (Useful for some clients.)"""
    def __init__(self,path,readOnly=False):
        """Initialize."""
        self.path = path
        self.backup = path.backup
        self.readOnly = readOnly
        self.vdata = {}
        self.data = {}

    def exists(self):
        return self.path.exists() or self.backup.exists()

    def load(self):
        """Loads vdata and data from file or backup file.

        If file does not exist, or is corrupt, then reads from backup file. If
        backup file also does not exist or is corrupt, then no data is read. If
        no data is read, then self.data is cleared.

        If file exists and has a vdata header, then that will be recorded in
        self.vdata. Otherwise, self.vdata will be empty.

        Returns:
          0: No data read (files don't exist and/or are corrupt)
          1: Data read from file
          2: Data read from backup file
        """
        self.vdata.clear()
        self.data.clear()
        for path in (self.path,self.backup):
            if path.exists():
                ins = None
                try:
                    ins = path.open('rb')
                    try:
                        header = cPickle.load(ins)
                    except ValueError:
                        os.remove(path)
                        continue # file corrupt - try next file
                    if header == 'VDATA':
                        self.vdata.update(cPickle.load(ins))
                        self.data.update(cPickle.load(ins))
                    else:
                        self.data.update(header)
                    ins.close()
                    return 1 + (path == self.backup)
                except EOFError:
                    if ins: ins.close()
        #--No files and/or files are corrupt
        return 0

    def save(self):
        """Save to pickle file."""
        if self.readOnly: return False
        #--Pickle it
        out = self.path.temp.open('wb')
        for data in ('VDATA',self.vdata,self.data):
            cPickle.dump(data,out,-1)
        out.close()
        self.path.untemp(True)
        return True

#------------------------------------------------------------------------------
class Settings(DataDict):
    """Settings/configuration dictionary with persistent storage.

    Default setting for configurations are either set in bulk (by the
    loadDefaults function) or are set as needed in the code (e.g., various
    auto-continue settings for bash. Only settings that have been changed from
    the default values are saved in persistent storage.

    Directly setting a value in the dictionary will mark it as changed (and thus
    to be archived). However, an indirect change (e.g., to a value that is a
    list) must be manually marked as changed by using the setChanged method."""

    def __init__(self,dictFile):
        """Initialize. Read settings from dictFile."""
        self.dictFile = dictFile
        if self.dictFile:
            dictFile.load()
            self.vdata = dictFile.vdata.copy()
            self.data = dictFile.data.copy()
        else:
            self.vdata = {}
            self.data = {}
        self.defaults = {}
        self.changed = []
        self.deleted = []

    def loadDefaults(self,defaults):
        """Add default settings to dictionary. Will not replace values that are already set."""
        self.defaults = defaults
        for key in defaults.keys():
            if key not in self.data:
                self.data[key] = copy.deepcopy(defaults[key])

    def setDefault(self,key,default):
        """Sets a single value to a default value if it has not yet been set."""

    def save(self):
        """Save to pickle file. Only key/values marked as changed are saved."""
        dictFile = self.dictFile
        if not dictFile or dictFile.readOnly: return
        dictFile.load()
        dictFile.vdata = self.vdata.copy()
        for key in self.deleted:
            dictFile.data.pop(key,None)
        for key in self.changed:
            if self.data[key] == self.defaults.get(key,None):
                dictFile.data.pop(key,None)
            else:
                dictFile.data[key] = self.data[key]
        dictFile.save()

    def setChanged(self,key):
        """Marks given key as having been changed. Use if value is a dictionary, list or other object."""
        if key not in self.data:
            raise ArgumentError("No settings data for "+key)
        if key not in self.changed:
            self.changed.append(key)

    def getChanged(self,key,default=None):
        """Gets and marks as changed."""
        if default != None and key not in self.data:
            self.data[key] = default
        self.setChanged(key)
        return self.data.get(key)

    #--Dictionary Emulation
    def __setitem__(self,key,value):
        """Dictionary emulation. Marks key as changed."""
        if key in self.deleted: self.deleted.remove(key)
        if key not in self.changed: self.changed.append(key)
        self.data[key] = value

    def __delitem__(self,key):
        """Dictionary emulation. Marks key as deleted."""
        if key in self.changed: self.changed.remove(key)
        if key not in self.deleted: self.deleted.append(key)
        del self.data[key]

    def setdefault(self,key,value):
        """Dictionary emulation. Will not mark as changed."""
        if key in self.data:
            return self.data[key]
        if key in self.deleted: self.deleted.remove(key)
        self.data[key] = value
        return value

    def pop(self,key,default=None):
        """Dictionary emulation: extract value and delete from dictionary."""
        if key in self.changed: self.changed.remove(key)
        if key not in self.deleted: self.deleted.append(key)
        return self.data.pop(key,default)

#------------------------------------------------------------------------------
class StructFile(file):
    """File reader/writer with extra functions for handling structured data."""
    def unpack(self,format,size):
        """Reads and unpacks according to format."""
        return struct.unpack(format,self.read(size))

    def pack(self,format,*data):
        """Packs data according to format."""
        self.write(struct.pack(format,*data))

    def readNetString(self):
        """Read a .net string. THIS CODE IS DUBIOUS!"""
        pos = self.tell()
        strLen, = self.unpack('B',1)
        if strLen >= 128:
            self.seek(pos)
            strLen, = self.unpack('H',2)
            strLen = strLen & 0x7f | (strLen >> 1) & 0xff80
            if strLen > 0x7FFF:
                raise UncodedError(_('String too long to convert.'))
        return self.read(strLen)

    def writeNetString(self,str):
        """Write string as a .net string. THIS CODE IS DUBIOUS!"""
        strLen = len(str)
        if strLen < 128:
            self.pack('b',strLen)
        elif strLen > 0x7FFF: #--Actually probably fails earlier.
            raise UncodedError(_('String too long to convert.'))
        else:
            strLen =  0x80 | strLen & 0x7f | (strLen & 0xff80) << 1
            self.pack('H',strLen)
        self.write(str)

#------------------------------------------------------------------------------
class BinaryFile(StructFile):
    """File reader/writer easier to read specific number of bytes."""
    def __init__(self,*args,**kwdargs):
        # Ensure we're reading/writing in binary mode
        if len(args) < 2:
            mode = kwdargs.get('mode',None)
            if mode =='r': mode = 'rb'
            elif mode == 'w': mode = 'wb'
            elif mode == 'rb' or mode == 'wb':
                pass
            else: mode = 'rb'
            kwdargs['mode'] = mode
        else:
            new_args = list(args)
            if args[1] == 'r': new_args[1] == 'rb'
            elif args[1] == 'w': new_args[1] == 'wb'
            elif args[1] == 'rb' or args[1] == 'wb':
                pass
            else: new_args[1] = 'rb'
            args = tuple(new_args)
        types.FileType.__init__(self,*args,**kwdargs)

    def readPascalString(self): return self.read(self.readByte())
    def readCString(self):
        pos = self.tell()
        while self.readByte() != 0:
            pass
        end = self.tell()
        self.seek(pos)
        return self.read(end-pos+1)
    # readNetString defined in StructFile
    def readByte(self): return struct.unpack('B',self.read(1))[0]
    def readBytes(self, numBytes): return list(struct.unpack('b'*numBytes,self.read(numBytes)))
    def readInt16(self): return struct.unpack('h',self.read(2))[0]
    def readInt32(self): return struct.unpack('i',self.read(4))[0]
    def readInt64(self): return struct.unpack('q',self.read(8))[0]

    def writeString(self, text):
        self.writeByte(len(text))
        self.write(text)
    def writeByte(self, byte): self.write(struct.pack('B',byte))
    def writeBytes(self, bytes): self.write(struct.pack('b'*len(bytes),*bytes))
    def writeInt16(self, int16): self.write(struct.pack('h',int16))
    def writeInt32(self, int32): self.write(struct.pack('i',int32))
    def writeInt64(self, int64): self.write(struct.pack('q',int64))

#------------------------------------------------------------------------------
class TableColumn:
    """Table accessor that presents table column as a dictionary."""
    def __init__(self,table,column):
        self.table = table
        self.column = column
    #--Dictionary Emulation
    def __iter__(self):
        """Dictionary emulation."""
        tableData = self.table.data
        column = self.column
        return (key for key in tableData.keys() if (column in tableData[key]))
    def keys(self):
        return list(self.__iter__())
    def items(self):
        """Dictionary emulation."""
        tableData = self.table.data
        column = self.column
        return [(key,tableData[key][column]) for key in tableData.keys()
            if (column in tableData[key])]
    def has_key(self,key):
        """Dictionary emulation."""
        return self.__contains__(key)
    def clear(self):
        """Dictionary emulation."""
        self.table.delColumn(self.column)
    def get(self,key,default=None):
        """Dictionary emulation."""
        return self.table.getItem(key,self.column,default)
    #--Overloaded
    def __contains__(self,key):
        """Dictionary emulation."""
        tableData = self.table.data
        return tableData.has_key(key) and tableData[key].has_key(self.column)
    def __getitem__(self,key):
        """Dictionary emulation."""
        return self.table.data[key][self.column]
    def __setitem__(self,key,value):
        """Dictionary emulation. Marks key as changed."""
        self.table.setItem(key,self.column,value)
    def __delitem__(self,key):
        """Dictionary emulation. Marks key as deleted."""
        self.table.delItem(key,self.column)

#------------------------------------------------------------------------------
class Table(DataDict):
    """Simple data table of rows and columns, saved in a pickle file. It is
    currently used by modInfos to represent properties associated with modfiles,
    where each modfile is a row, and each property (e.g. modified date or
    'mtime') is a column.

    The "table" is actually a dictionary of dictionaries. E.g.
        propValue = table['fileName']['propName']
    Rows are the first index ('fileName') and columns are the second index
    ('propName')."""

    def __init__(self,dictFile):
        """Intialize and read data from dictFile, if available."""
        self.dictFile = dictFile
        dictFile.load()
        self.vdata = dictFile.vdata
        self.data = dictFile.data
        self.hasChanged = False

    def save(self):
        """Saves to pickle file."""
        dictFile = self.dictFile
        if self.hasChanged and not dictFile.readOnly:
            self.hasChanged = not dictFile.save()

    def getItem(self,row,column,default=None):
        """Get item from row, column. Return default if row,column doesn't exist."""
        data = self.data
        if row in data and column in data[row]:
            return data[row][column]
        else:
            return default

    def getColumn(self,column):
        """Returns a data accessor for column."""
        return TableColumn(self,column)

    def setItem(self,row,column,value):
        """Set value for row, column."""
        data = self.data
        if row not in data:
            data[row] = {}
        data[row][column] = value
        self.hasChanged = True

    def setItemDefault(self,row,column,value):
        """Set value for row, column."""
        data = self.data
        if row not in data:
            data[row] = {}
        self.hasChanged = True
        return data[row].setdefault(column,value)

    def delItem(self,row,column):
        """Deletes item in row, column."""
        data = self.data
        if row in data and column in data[row]:
            del data[row][column]
            self.hasChanged = True

    def delRow(self,row):
        """Deletes row."""
        data = self.data
        if row in data:
            del data[row]
            self.hasChanged = True

    def delColumn(self,column):
        """Deletes column of data."""
        data = self.data
        for rowData in data.values():
            if column in rowData:
                del rowData[column]
                self.hasChanged = True

    def moveRow(self,oldRow,newRow):
        """Renames a row of data."""
        data = self.data
        if oldRow in data:
            data[newRow] = data[oldRow]
            del data[oldRow]
            self.hasChanged = True

    def copyRow(self,oldRow,newRow):
        """Copies a row of data."""
        data = self.data
        if oldRow in data:
            data[newRow] = data[oldRow].copy()
            self.hasChanged = True

    #--Dictionary emulation
    def __setitem__(self,key,value):
        self.data[key] = value
        self.hasChanged = True
    def __delitem__(self,key):
        del self.data[key]
        self.hasChanged = True
    def setdefault(self,key,default):
        if key not in self.data: self.hasChanged = True
        return self.data.setdefault(key,value)
    def pop(self,key,default=None):
        self.hasChanged = True
        return self.data.pop(key,default)

#------------------------------------------------------------------------------
class TankData:
    """Data source for a Tank table."""

    def __init__(self,params):
        """Initialize."""
        self.tankParams = params
        #--Default settings. Subclasses should define these.
        self.tankKey = self.__class__.__name__
        self.tankColumns = [] #--Full possible set of columns.
        self.title = self.__class__.__name__
        self.hasChanged = False

    #--Parameter access
    def getParam(self,key,default=None):
        """Get a GUI parameter.
        Typical Parameters:
        * columns: list of current columns.
        * colNames: column_name dict
        * colWidths: column_width dict
        * colAligns: column_align dict
        * colReverse: column_reverse dict (colReverse[column] = True/False)
        * colSort: current column being sorted on
        """
        return self.tankParams.get(self.tankKey+'.'+key,default)

    def defaultParam(self,key,value):
        """Works like setdefault for dictionaries."""
        return self.tankParams.setdefault(self.tankKey+'.'+key,value)

    def updateParam(self,key,default=None):
        """Get a param, but also mark it as changed.
        Used for deep params like lists and dictionaries."""
        return self.tankParams.getChanged(self.tankKey+'.'+key,default)

    def setParam(self,key,value):
        """Set a GUI parameter."""
        self.tankParams[self.tankKey+'.'+key] = value

    #--Collection
    def setChanged(self,hasChanged=True):
        """Mark as having changed."""
        pass

    def refresh(self):
        """Refreshes underlying data as needed."""
        pass

    def getRefreshReport(self):
        """Returns a (string) report on the refresh operation."""
        return None

    def getSorted(self,column,reverse):
        """Returns items sorted according to column and reverse."""
        raise AbstractError

    #--Item Info
    def getColumns(self,item=None):
        """Returns text labels for item or for row header if item == None."""
        columns = self.getParam('columns',self.tankColumns)
        if item == None: return columns[:]
        raise AbstractError

    def getName(self,item):
        """Returns a string name of item for use in dialogs, etc."""
        return item

    def getGuiKeys(self,item):
        """Returns keys for icon and text and background colors."""
        iconKey = textKey = backKey = None
        return (iconKey,textKey,backKey)

# Util Functions --------------------------------------------------------------
#------------------------------------------------------------------------------
def copyattrs(source,dest,attrs):
    """Copies specified attrbutes from source object to dest object."""
    for attr in attrs:
        setattr(dest,attr,getattr(source,attr))

def cstrip(inString):
    """Convert c-string (null-terminated string) to python string."""
    zeroDex = inString.find('\x00')
    if zeroDex == -1:
        return inString
    else:
        return inString[:zeroDex]

def csvFormat(format):
    """Returns csv format for specified structure format."""
    csvFormat = ''
    for char in format:
        if char in 'bBhHiIlLqQ': csvFormat += ',%d'
        elif char in 'fd': csvFormat += ',%f'
        elif char in 's': csvFormat += ',"%s"'
    return csvFormat[1:] #--Chop leading comma

deprintOn = False
def deprint(*args,**keyargs):
    """Prints message along with file and line location."""
    if not deprintOn and not keyargs.get('on'): return

    import inspect
    stack = inspect.stack()
    file,line,function = stack[1][1:4]
    msg = '%s %4d %s: %s' % (GPath(file).tail.s,line,function,' '.join(map(str,args)))

    if keyargs.get('traceback',False):
        import traceback, cStringIO
        o = cStringIO.StringIO()
        o.write(msg+'\n')
        traceback.print_exc(file=o)
        msg = o.getvalue()
        o.close()
    print msg

def delist(header,items,on=False):
    """Prints list as header plus items."""
    if not deprintOn and not on: return
    import inspect
    stack = inspect.stack()
    file,line,function = stack[1][1:4]
    print '%s %4d %s: %s' % (GPath(file).tail.s,line,function,str(header))
    if items == None:
        print '> None'
    else:
        for indexItem in enumerate(items): print '>%2d: %s' % indexItem

def dictFromLines(lines,sep=None):
    """Generate a dictionary from a string with lines, stripping comments and skipping empty strings."""
    temp = [reComment.sub('',x).strip() for x in lines.split('\n')]
    if sep == None or type(sep) == type(''):
        temp = dict([x.split(sep,1) for x in temp if x])
    else: #--Assume re object.
        temp = dict([sep.split(x,1) for x in temp if x])
    return temp

def getMatch(reMatch,group=0):
    """Returns the match or an empty string."""
    if reMatch: return reMatch.group(group)
    else: return ''

def intArg(arg,default=None):
    """Returns argument as an integer. If argument is a string, then it converts it using int(arg,0)."""
    if arg == None: return default
    elif isinstance(arg,StringType): return int(arg,0)
    else: return int(arg)

def invertDict(indict):
    """Invert a dictionary."""
    return dict((y,x) for x,y in indict.iteritems())

def listFromLines(lines):
    """Generate a list from a string with lines, stripping comments and skipping empty strings."""
    temp = [reComment.sub('',x).strip() for x in lines.split('\n')]
    temp = [x for x in temp if x]
    return temp

def listSubtract(alist,blist):
    """Return a copy of first list minus items in second list."""
    result = []
    for item in alist:
        if item not in blist:
            result.append(item)
    return result

def listJoin(*inLists):
    """Joins multiple lists into a single list."""
    outList = []
    for inList in inLists:
        outList.extend(inList)
    return outList

def listGroup(items):
    """Joins items into a list for use in a regular expression.
    E.g., a list of ('alpha','beta') becomes '(alpha|beta)'"""
    return '('+('|'.join(items))+')'

def rgbString(red,green,blue):
    """Converts red, green blue ints to rgb string."""
    return chr(red)+chr(green)+chr(blue)

def rgbTuple(rgb):
    """Converts red, green, blue string to tuple."""
    return struct.unpack('BBB',rgb)

def unQuote(inString):
    """Removes surrounding quotes from string."""
    if len(inString) >= 2 and inString[0] == '"' and inString[-1] == '"':
        return inString[1:-1]
    else:
        return inString

def winNewLines(inString):
    """Converts unix newlines to windows newlines."""
    return reUnixNewLine.sub('\r\n',inString)

# Log/Progress ----------------------------------------------------------------
#------------------------------------------------------------------------------
class Log:
    """Log Callable. This is the abstract/null version. Useful version should
    override write functions.

    Log is divided into sections with headers. Header text is assigned (through
    setHeader), but isn't written until a message is written under it. I.e.,
    if no message are written under a given header, then the header itself is
    never written."""

    def __init__(self):
        """Initialize."""
        self.header = None
        self.prevHeader = None

    def setHeader(self,header,writeNow=False,doFooter=True):
        """Sets the header."""
        self.header = header
        if self.prevHeader:
            self.prevHeader += 'x'
        self.doFooter = doFooter
        if writeNow: self()

    def __call__(self,message=None):
        """Callable. Writes message, and if necessary, header and footer."""
        if self.header != self.prevHeader:
            if self.prevHeader and self.doFooter:
                self.writeFooter()
            if self.header:
                self.writeHeader(self.header)
            self.prevHeader = self.header
        if message: self.writeMessage(message)

    #--Abstract/null writing functions...
    def writeHeader(self,header):
        """Write header. Abstract/null version."""
        pass
    def writeFooter(self):
        """Write mess. Abstract/null version."""
        pass
    def writeMessage(self,message):
        """Write message to log. Abstract/null version."""
        pass

#------------------------------------------------------------------------------
class LogFile(Log):
    """Log that writes messages to file."""
    def __init__(self,out):
        self.out = out
        Log.__init__(self)

    def writeHeader(self,header):
        self.out.write(header+'\n')

    def writeFooter(self):
        self.out.write('\n')

    def writeMessage(self,message):
        self.out.write(message+'\n')

#------------------------------------------------------------------------------
class Progress:
    """Progress Callable: Shows progress when called."""
    def __init__(self,full=1.0):
        if (1.0*full) == 0: raise ArgumentError('Full must be non-zero!')
        self.message = ''
        self.full = full
        self.state = 0
        self.debug = False

    def setFull(self,full):
        """Set's full and for convenience, returns self."""
        if (1.0*full) == 0: raise ArgumentError('Full must be non-zero!')
        self.full = full
        return self

    def plus(self,increment=1):
        """Increments progress by 1."""
        self.__call__(self.state+increment)

    def __call__(self,state,message=''):
        """Update progress with current state. Progress is state/full."""
        if (1.0*self.full) == 0: raise ArgumentError('Full must be non-zero!')
        if message: self.message = message
        if self.debug: deprint('%0.3f %s' % (1.0*state/self.full, self.message))
        self.doProgress(1.0*state/self.full, self.message)
        self.state = state

    def doProgress(self,progress,message):
        """Default doProgress does nothing."""
        pass

#------------------------------------------------------------------------------
class SubProgress(Progress):
    """Sub progress goes from base to ceiling."""
    def __init__(self,parent,baseFrom=0.0,baseTo='+1',full=1.0,silent=False):
        """For creating a subprogress of another progress meter.
        progress: parent (base) progress meter
        baseFrom: Base progress when this progress == 0.
        baseTo: Base progress when this progress == full
          Usually a number. But string '+1' sets it to baseFrom + 1
        full: Full meter by this progress' scale."""
        Progress.__init__(self,full)
        if baseTo == '+1': baseTo = baseFrom + 1
        if (baseFrom < 0 or baseFrom >= baseTo):
            raise ArgumentError('BaseFrom must be >= 0 and BaseTo must be > BaseFrom')
        self.parent = parent
        self.baseFrom = baseFrom
        self.scale = 1.0*(baseTo-baseFrom)
        self.silent = silent

    def __call__(self,state,message=''):
        """Update progress with current state. Progress is state/full."""
        if self.silent: message = ''
        self.parent(self.baseFrom+self.scale*state/self.full,message)
        self.state = state

#------------------------------------------------------------------------------
class ProgressFile(Progress):
    """Prints progress to file (stdout by default)."""
    def __init__(self,full=1.0,out=None):
        Progress.__init__(self,full)
        self.out = out or sys.stdout

    def doProgress(self,progress,message):
        self.out.write('%0.2f %s\n' % (progress,message))

# WryeText --------------------------------------------------------------------
class WryeText:
    """This class provides a function for converting wtxt text files to html
    files.

    Headings:
    = XXXX >> H1 "XXX"
    == XXXX >> H2 "XXX"
    === XXXX >> H3 "XXX"
    ==== XXXX >> H4 "XXX"
    Notes:
    * These must start at first character of line.
    * The XXX text is compressed to form an anchor. E.g == Foo Bar gets anchored as" FooBar".
    * If the line has trailing ='s, they are discarded. This is useful for making
      text version of level 1 and 2 headings more readable.

    Bullet Lists:
    * Level 1
      * Level 2
        * Level 3
    Notes:
    * These must start at first character of line.
    * Recognized bullet characters are: - ! ? . + * o The dot (.) produces an invisible
      bullet, and the * produces a bullet character.

    Styles:
      __Text__
      ~~Italic~~
      **BoldItalic**
    Notes:
    * These can be anywhere on line, and effects can continue across lines.

    Links:
     [[file]] produces <a href=file>file</a>
     [[file|text]] produces <a href=file>text</a>
     [[!file]] produces <a href=file target="_blank">file</a>
     [[!file|text]] produces <a href=file target="_blank">text</a>

    Contents
    {{CONTENTS=NN}} Where NN is the desired depth of contents (1 for single level,
    2 for two levels, etc.).
    """

    # Data ------------------------------------------------------------------------
    htmlHead = """<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.0 Strict//EN"
    "http://www.w3.org/TR/xhtml1/DTD/xhtml1-strict.dtd">
    <html xmlns="http://www.w3.org/1999/xhtml" xml:lang="en" lang="en">
    <head>
    <meta http-equiv="Content-Type" content="text/html;charset=utf-8" />
    <title>%s</title>
    <style type="text/css">%s</style>
    </head>
    <body>
    """
    defaultCss = """
    h1 { margin-top: 0in; margin-bottom: 0in; border-top: 1px solid #000000; border-bottom: 1px solid #000000; border-left: none; border-right: none; padding: 0.02in 0in; background: #c6c63c; font-family: "Arial", serif; font-size: 12pt; page-break-before: auto; page-break-after: auto }
    h2 { margin-top: 0in; margin-bottom: 0in; border-top: 1px solid #000000; border-bottom: 1px solid #000000; border-left: none; border-right: none; padding: 0.02in 0in; background: #e6e64c; font-family: "Arial", serif; font-size: 10pt; page-break-before: auto; page-break-after: auto }
    h3 { margin-top: 0in; margin-bottom: 0in; font-family: "Arial", serif; font-size: 10pt; font-style: normal; page-break-before: auto; page-break-after: auto }
    h4 { margin-top: 0in; margin-bottom: 0in; font-family: "Arial", serif; font-style: italic; page-break-before: auto; page-break-after: auto }
    a:link { text-decoration:none; }
    a:hover { text-decoration:underline; }
    p { margin-top: 0.01in; margin-bottom: 0.01in; font-family: "Arial", serif; font-size: 10pt; page-break-before: auto; page-break-after: auto }
    p.empty {}
    p.list-1 { margin-left: 0.15in; text-indent: -0.15in }
    p.list-2 { margin-left: 0.3in; text-indent: -0.15in }
    p.list-3 { margin-left: 0.45in; text-indent: -0.15in }
    p.list-4 { margin-left: 0.6in; text-indent: -0.15in }
    p.list-5 { margin-left: 0.75in; text-indent: -0.15in }
    p.list-6 { margin-left: 1.00in; text-indent: -0.15in }
    .code-0 { background-color: #FDF5E6; font-family: "Lucida Console", monospace; font-size: 10pt; }
    .code-1 { background-color: #FDF5E6; font-family: "Lucida Console", monospace; font-size: 10pt; text-indent: 1em; }
    .code-2 { background-color: #FDF5E6; font-family: "Lucida Console", monospace; font-size: 10pt; text-indent: 2em; }
    .code-3 { background-color: #FDF5E6; font-family: "Lucida Console", monospace; font-size: 10pt; text-indent: 3em; }
    .code-4 { background-color: #FDF5E6; font-family: "Lucida Console", monospace; font-size: 10pt; text-indent: 4em; }
    .code-5 { background-color: #FDF5E6; font-family: "Lucida Console", monospace; font-size: 10pt; text-indent: 5em; }
    pre { border: 1px solid; overflow: auto; width: 750px; word-wrap: break-word; background: #FDF5E6; padding: 0.5em; margin-top: 0in; margin-bottom: 0in; margin-left: 0.25in}
    code { background-color: #FDF5E6; font-family: "Lucida Console", monospace; font-size: 10pt; }
    td.code { background-color: #FDF5E6; font-family: "Lucida Console", monospace; font-size: 10pt; border: 1px solid #000000; padding:5px; width:50%;}
    body { background-color: #ffffcc; }
    """

    # Conversion ------------------------------------------------------------------
    @staticmethod
    def genHtml(ins,out=None,*cssDirs):
        """Reads a wtxt input stream and writes an html output stream."""
        # Path or Stream? -----------------------------------------------
        if isinstance(ins,(Path,str,unicode)):
            srcPath = GPath(ins)
            outPath = GPath(out) or srcPath.root+'.html'
            cssDirs = (srcPath.head,) + cssDirs
            ins = srcPath.open()
            out = outPath.open('w')
        else:
            srcPath = outPath = None
        cssDirs = map(GPath,cssDirs)
        # Setup ---------------------------------------------------------
        #--Headers
        reHead = re.compile(r'(=+) *(.+)')
        headFormat = "<h%d><a id='%s'>%s</a></h%d>\n"
        headFormatNA = "<h%d>%s</h%d>\n"
        #--List
        reList = re.compile(r'( *)([-x!?\.\+\*o])(.*)')
        #--Code
        reCode = re.compile(r'\[code\](.*?)\[/code\]',re.I)
        reCodeStart = re.compile(r'\[code\](\s*)(.*?)',re.I)
        reCodeLine = re.compile(r'(\s*)(.*)')
        reCodeEnd = re.compile(r'(\s*)(.*?)\[/code\]',re.I)
        def subCode(match):
            if len(match.group(1)) > 0:
                return '<p class="code-0">%s</p>' % match.group(1)
            else:
                return ''
        def subCodeStart(match):
            states['code'] = True
            indent = min(len(match.group(1))/2, 5)
            if len(match.group(2)) > 0:
                return '<p class="code-%i">%s</p>' % (indent, match.group(2))
            else:
                return ''
        def subCodeLine(match):
            if states['code']:
                indent = min(len(match.group(1))/2, 5)
                if len(match.group(2)) > 0:
                    return '<p class="code-%i">%s</p>' % (indent,match.group(2))
                else:
                    return ''
            else:
                return match.group(0)
        def subCodeEnd(match):
            if states['code']:
                states['code'] = False
                indent = min(len(match.group(1))/2, 5)
                return '<p class="code-%i">%s</p>' % (indent,match.group(2))
            else:
                return '%s%s' % (match.group(1), match.group(2))
        #--Misc. text
        reHr = re.compile('^------+$')
        reEmpty = re.compile(r'\s+$')
        reMDash = re.compile(r' -- ')
        rePreBegin = re.compile('<pre',re.I)
        rePreEnd = re.compile('</pre>',re.I)
        anchorlist = [] #to make sure that each anchor is unique.
        def subAnchor(match):
            text = match.group(1)
            anchor = reWd.sub('',text)
            count = 0
            if re.match(r'\d', anchor):
                anchor = '_' + anchor
            while anchor in anchorlist and count < 10:
                count += 1
                if count == 1:
                    anchor = anchor + str(count)
                else:
                    anchor = anchor[:-1] + str(count)
            anchorlist.append(anchor)
            return "<a id='%s'>%s</a>" % (anchor,text)
        #--Bold, Italic, BoldItalic
        reBold = re.compile(r'__')
        reItalic = re.compile(r'~~')
        reBoldItalic = re.compile(r'\*\*')
        states = {'bold':False,'italic':False,'boldItalic':False,'code':0}
        def subBold(match):
            state = states['bold'] = not states['bold']
            return ('</b>','<b>')[state]
        def subItalic(match):
            state = states['italic'] = not states['italic']
            return ('</i>','<i>')[state]
        def subBoldItalic(match):
            state = states['boldItalic'] = not states['boldItalic']
            return ('</b></i>','<i><b>')[state]
        #--Preformatting
        #--Links
        reLink = re.compile(r'\[\[(.*?)\]\]')
        reHttp = re.compile(r' (http://[_~a-zA-Z0-9\./%-]+)')
        reWww = re.compile(r' (www\.[_~a-zA-Z0-9\./%-]+)')
        reWd = re.compile(r'(<[^>]+>|\[[^\]]+\]|\W+)')
        rePar = re.compile(r'^(\s*[a-zA-Z(;]|\*\*|~~|__|\s*<i|\s*<a)')
        reFullLink = re.compile(r'(:|#|\.[a-zA-Z0-9]{2,4}$)')
        reColor = re.compile(r'\[\s*color\s*=[\s\"\']*(.+?)[\s\"\']*\](.*?)\[\s*/\s*color\s*\]',re.I)
        reBGColor = re.compile(r'\[\s*bg\s*=[\s\"\']*(.+?)[\s\"\']*\](.*?)\[\s*/\s*bg\s*\]',re.I)
        def subColor(match):
            return '<span style="color:%s;">%s</span>' % (match.group(1),match.group(2))
        def subBGColor(match):
            return '<span style="background-color:%s;">%s</span>' % (match.group(1),match.group(2))
        def subLink(match):
            address = text = match.group(1).strip()
            if '|' in text:
                (address,text) = [chunk.strip() for chunk in text.split('|',1)]
                if address == '#': address += reWd.sub('',text)
            if address.startswith('!'):
                newWindow = ' target="_blank"'
                address = address[1:]
            else:
                newWindow = ''
            if not reFullLink.search(address):
                address = address+'.html'
            return '<a href="%s"%s>%s</a>' % (address,newWindow,text)
        #--Tags
        reAnchorTag = re.compile('{{A:(.+?)}}')
        reContentsTag = re.compile(r'\s*{{CONTENTS=?(\d+)}}\s*$')
        reAnchorHeadersTag = re.compile(r'\s*{{ANCHORHEADERS=(\d+)}}\s*$')
        reCssTag = re.compile('\s*{{CSS:(.+?)}}\s*$')
        #--Defaults ----------------------------------------------------------
        title = ''
        level = 1
        spaces = ''
        cssName = None
        #--Init
        outLines = []
        contents = []
        addContents = 0
        inPre = False
        anchorHeaders = True
        #--Read source file --------------------------------------------------
        for line in ins:
            #--Preformatted? -----------------------------
            maPreBegin = rePreBegin.search(line)
            maPreEnd = rePreEnd.search(line)
            if inPre or maPreBegin or maPreEnd:
                inPre = maPreBegin or (inPre and not maPreEnd)
                outLines.append(line)
                continue
            #--Font/Background Color
            line = reColor.sub(subColor,line)
            line = reBGColor.sub(subBGColor,line)
            #--Re Matches -------------------------------
            maContents = reContentsTag.match(line)
            maAnchorHeaders = reAnchorHeadersTag.match(line)
            maCss = reCssTag.match(line)
            maHead = reHead.match(line)
            maList  = reList.match(line)
            maPar   = rePar.match(line)
            maEmpty = reEmpty.match(line)
            #--Code --------------------------------------
            line = reCode.sub(subCode,line)
            maCodeStart = reCodeStart.search(line)
            maCodeEnd = reCodeEnd.search(line)
            #--Contents
            if maCodeStart:
                line = reCodeStart.sub(subCodeStart, line)
            elif maCodeEnd:
                line = reCodeEnd.sub(subCodeEnd, line)
            else:
                line = reCodeLine.sub(subCodeLine,line)
            if maContents:
                if maContents.group(1):
                    addContents = int(maContents.group(1))
                else:
                    addContents = 100
                inPar = False
            elif maAnchorHeaders:
                anchorHeaders = maAnchorHeaders.group(1) != '0'
                continue
            #--CSS
            elif maCss:
                #--Directory spec is not allowed, so use tail.
                cssName = GPath(maCss.group(1).strip()).tail
                continue
            #--Headers
            elif maHead:
                lead,text = maHead.group(1,2)
                text = re.sub(' *=*#?$','',text.strip())
                anchor = reWd.sub('',text)
                level = len(lead)
                if anchorHeaders:
                    if re.match(r'\d', anchor):
                        anchor = '_' + anchor
                    count = 0
                    while anchor in anchorlist and count < 10:
                        count += 1
                        if count == 1:
                            anchor = anchor + str(count)
                        else:
                            anchor = anchor[:-1] + str(count)
                    anchorlist.append(anchor)
                    line = (headFormatNA,headFormat)[anchorHeaders] % (level,anchor,text,level)
                    if addContents: contents.append((level,anchor,text))
                else:
                    line = headFormatNA % (level,text,level)
                #--Title?
                if not title and level <= 2: title = text
            #--Paragraph
            elif maPar and not states['code']:
                line = '<p>'+line+'</p>\n'
            #--List item
            elif maList:
                spaces = maList.group(1)
                bullet = maList.group(2)
                text = maList.group(3)
                if bullet == '.': bullet = '&nbsp;'
                elif bullet == '*': bullet = '&bull;'
                level = len(spaces)/2 + 1
                line = spaces+'<p class="list-'+`level`+'">'+bullet+'&nbsp; '
                line = line + text + '</p>\n'
            #--Empty line
            elif maEmpty:
                line = spaces+'<p class="empty">&nbsp;</p>\n'
            #--Misc. Text changes --------------------
            line = reHr.sub('<hr>',line)
            line = reMDash.sub(' &#150; ',line)
            #--Bold/Italic subs
            line = reBold.sub(subBold,line)
            line = reItalic.sub(subItalic,line)
            line = reBoldItalic.sub(subBoldItalic,line)
            #--Wtxt Tags
            line = reAnchorTag.sub(subAnchor,line)
            #--Hyperlinks
            line = reLink.sub(subLink,line)
            line = reHttp.sub(r' <a href="\1">\1</a>',line)
            line = reWww.sub(r' <a href="http://\1">\1</a>',line)
            #--Save line ------------------
            #print line,
            outLines.append(line)
        #--Get Css -----------------------------------------------------------
        if not cssName:
            css = WryeText.defaultCss
        else:
            if cssName.ext != '.css':
                raise "Invalid Css file: "+cssName.s
            for dir in cssDirs:
                cssPath = GPath(dir).join(cssName)
                if cssPath.exists(): break
            else:
                raise 'Css file not found: '+cssName.s
            css = ''.join(cssPath.open().readlines())
            if '<' in css:
                raise "Non css tag in "+cssPath.s
        #--Write Output ------------------------------------------------------
        out.write(WryeText.htmlHead % (title,css))
        didContents = False
        for line in outLines:
            if reContentsTag.match(line):
                if contents and not didContents:
                    baseLevel = min([level for (level,name,text) in contents])
                    for (level,name,text) in contents:
                        level = level - baseLevel + 1
                        if level <= addContents:
                            out.write('<p class="list-%d">&bull;&nbsp; <a href="#%s">%s</a></p>\n' % (level,name,text))
                    didContents = True
            else:
                out.write(line)
        out.write('</body>\n</html>\n')
        #--Close files?
        if srcPath:
            ins.close()
            out.close()

# Main -------------------------------------------------------------------------
if __name__ == '__main__' and len(sys.argv) > 1:
    #--Commands----------------------------------------------------------------
    @mainfunc
    def genHtml(*args,**keywords):
        """Wtxt to html. Just pass through to WryeText.genHtml."""
        if not len(args):
            args = ["Wrye Bash.txt"]
        WryeText.genHtml(*args,**keywords)

    #--Command Handler --------------------------------------------------------
    _mainFunctions.main()
