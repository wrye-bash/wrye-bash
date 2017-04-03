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

# Imports ---------------------------------------------------------------------
#--Standard
import StringIO
import cPickle
import codecs
import copy
import csv
import datetime
import gettext
import locale
import os
import pkgutil
import re
import shutil
import stat
import struct
import subprocess
import sys
import tempfile
import time
import traceback

close_fds = True
import types
from binascii import crc32
import bass
import chardet
#-- To make commands executed with Popen hidden
startupinfo = None
if os.name == u'nt':
    startupinfo = subprocess.STARTUPINFO()
    startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW

# Unicode ---------------------------------------------------------------------
#--decode unicode strings
#  This is only useful when reading fields from mods, as the encoding is not
#  known.  For normal filesystem interaction, these functions are not needed
encodingOrder = (
    'ascii',    # Plain old ASCII (0-127)
    'gbk',      # GBK (simplified Chinese + some)
    'cp932',    # Japanese
    'cp949',    # Korean
    'cp1252',   # English (extended ASCII)
    'utf8',
    'cp500',
    'UTF-16LE',
    'mbcs',
    )

_encodingSwap = {
    # The encoding detector reports back some encodings that
    # are subsets of others.  Use the better encoding when
    # given the option
    # 'reported encoding':'actual encoding to use',
    'GB2312': 'gbk',        # Simplified Chinese
    'SHIFT_JIS': 'cp932',   # Japanese
    'windows-1252': 'cp1252',
    'windows-1251': 'cp1251',
    'utf-8': 'utf8',
    }

# Preferred encoding to use when decoding/encoding strings in plugin files
# None = auto
# setting it tries the specified encoding first
pluginEncoding = None

def _getbestencoding(bitstream):
    """Tries to detect the encoding a bitstream was saved in.  Uses Mozilla's
       detection library to find the best match (heuristics)"""
    result = chardet.detect(bitstream)
    encoding_,confidence = result['encoding'],result['confidence']
    encoding_ = _encodingSwap.get(encoding_,encoding_)
    ## Debug: uncomment the following to output stats on encoding detection
    #print
    #print '%s: %s (%s)' % (repr(bitstream),encoding,confidence)
    return encoding_,confidence

def decode(byte_str, encoding=None, avoidEncodings=()):
    if isinstance(byte_str, unicode) or byte_str is None: return byte_str
    # Try the user specified encoding first
    if encoding:
        try: return unicode(byte_str, encoding)
        except UnicodeDecodeError: pass
    # Try to detect the encoding next
    encoding,confidence = _getbestencoding(byte_str)
    if encoding and confidence >= 0.55 and (encoding not in avoidEncodings or confidence == 1.0):
        try: return unicode(byte_str, encoding)
        except UnicodeDecodeError: pass
    # If even that fails, fall back to the old method, trial and error
    for encoding in encodingOrder:
        try: return unicode(byte_str, encoding)
        except UnicodeDecodeError: pass
    raise UnicodeDecodeError(u'Text could not be decoded using any method')

def encode(text_str, encodings=encodingOrder, firstEncoding=None,
           returnEncoding=False):
    if isinstance(text_str, str) or text_str is None:
        if returnEncoding: return text_str, None
        else: return text_str
    # Try user specified encoding
    if firstEncoding:
        try:
            text_str = text_str.encode(firstEncoding)
            if returnEncoding: return text_str, firstEncoding
            else: return text_str
        except UnicodeEncodeError:
            pass
    goodEncoding = None
    # Try the list of encodings in order
    for encoding in encodings:
        try:
            temp = text_str.encode(encoding)
            detectedEncoding = _getbestencoding(temp)
            if detectedEncoding[0] == encoding:
                # This encoding also happens to be detected
                # By the encoding detector as the same thing,
                # which means use it!
                if returnEncoding: return temp,encoding
                else: return temp
            # The encoding detector didn't detect it, but
            # it works, so save it for later
            if not goodEncoding: goodEncoding = (temp,encoding)
        except UnicodeEncodeError:
            pass
    # Non of the encodings also where detectable via the
    # detector, so use the first one that encoded without error
    if goodEncoding:
        if returnEncoding: return goodEncoding
        else: return goodEncoding[0]
    raise UnicodeEncodeError(u'Text could not be encoded using any of the following encodings: %s' % encodings)

def formatInteger(value):
    """Convert integer to string formatted to locale."""
    return decode(locale.format('%d', int(value), True),
                  locale.getpreferredencoding())

def formatDate(value):
    """Convert time to string formatted to to locale's default date/time."""
    return decode(time.strftime('%c', time.localtime(value)),
                  locale.getpreferredencoding())

def unformatDate(date, formatStr):
    """Basically a wrapper around time.strptime. Exists to get around bug in
    strptime for Japanese locale."""
    try:
        return time.strptime(date, '%c')
    except ValueError:
        if formatStr == '%c' and u'Japanese' in locale.getlocale()[0]:
            date = re.sub(u'^([0-9]{4})/([1-9])', r'\1/0\2', date, flags=re.U)
            return time.strptime(date, '%c')
        else:
            raise

def timestamp(): return datetime.datetime.now().strftime(u'%Y-%m-%d %H.%M.%S')

def round_size(siz):
    """Round non zero sizes to 1 KB."""
    return formatInteger(0 if siz == 0 else max(siz, 1024) / 1024) + u' KB'

# Helpers ---------------------------------------------------------------------
def sortFiles(files, __split=os.path.split):
    """Utility function. Sorts files by directory, then file name."""
    sort_keys_dict = dict((x, __split(x.lower())) for x in files)
    return sorted(files, key=sort_keys_dict.__getitem__)

# Localization ----------------------------------------------------------------
# noinspection PyDefaultArgument
def _findAllBashModules(files=[], bashPath=None, cwd=None,
                        exts=('.py', '.pyw'), exclude=(u'chardet',),
                        _firstRun=False):
    """Return a list of all Bash files as relative paths to the Mopy
    directory.

    :param files: files list cache - populated in first run. In the form: [
    u'Wrye Bash Launcher.pyw', u'bash\\balt.py', ..., u'bash\\__init__.py',
    u'bash\\basher\\app_buttons.py', ...]
    :param bashPath: the relative path from Mopy
    :param cwd: initially C:\...\Mopy - but not at the time def is executed !
    :param exts: extensions to keep in listdir()
    :param exclude: tuple of excluded packages
    :param _firstRun: internal use
    """
    if not _firstRun and files:
        return files # cache, not likely to change during execution
    cwd = cwd or os.getcwdu()
    files.extend([(bashPath or Path(u'')).join(m).s for m in
                  os.listdir(cwd) if m.lower().endswith(exts)])
    # find subpackages -- p=(module_loader, name, ispkg)
    for p in pkgutil.iter_modules([cwd]):
        if not p[2] or p[1] in exclude: continue
        _findAllBashModules(
            files, bashPath.join(p[1]) if bashPath else GPath(u'bash'),
            cwd=os.path.join(cwd, p[1]), _firstRun=True)
    return files

def dumpTranslator(outPath,language,*files):
    """Dumps all translatable strings in python source files to a new text file.
       as this requires the source files, it will not work in WBSA mode, unless
       the source files are also installed"""
    outTxt = u'%sNEW.txt' % language
    fullTxt = os.path.join(outPath,outTxt)
    tmpTxt = os.path.join(outPath,u'%sNEW.tmp' % language)
    oldTxt = os.path.join(outPath,u'%s.txt' % language)
    if not files: files = _findAllBashModules()
    args = [u'p',u'-a',u'-o',fullTxt]
    args.extend(files)
    if hasattr(sys,'frozen'):
        import pygettext
        old_argv = sys.argv[:]
        sys.argv = args
        pygettext.main()
        sys.argv = old_argv
    else:
        p = os.path.join(sys.prefix,u'Tools',u'i18n',u'pygettext.py')
        args[0] = p
        subprocess.call(args,shell=True)
    # Fill in any already translated stuff...?
    try:
        reMsgIdsStart = re.compile('#:')
        reEncoding = re.compile(r'"Content-Type:\s*text/plain;\s*charset=(.*?)\\n"$',re.I)
        reNonEscapedQuote = re.compile(r'([^\\])"')
        def subQuote(match): return match.group(1)+'\\"'
        encoding = None
        with open(tmpTxt,'w') as out:
            outWrite = out.write
            #--Copy old translation file header, and get encoding for strings
            with open(oldTxt,'r') as ins:
                for line in ins:
                    if not encoding:
                        match = reEncoding.match(line.strip('\r\n'))
                        if match:
                            encoding = match.group(1)
                    match = reMsgIdsStart.match(line)
                    if match: break
                    outWrite(line)
            #--Read through the new translation file, fill in any already
            #  translated strings
            with open(fullTxt,'r') as ins:
                header = False
                msgIds = False
                for line in ins:
                    if not header:
                        match = reMsgIdsStart.match(line)
                        if match:
                            header = True
                            outWrite(line)
                        continue
                    elif line[0:7] == 'msgid "':
                        stripped = line.strip('\r\n')[7:-1]
                        # Replace escape sequences
                        stripped = stripped.replace('\\"','"')      # Quote
                        stripped = stripped.replace('\\t','\t')     # Tab
                        stripped = stripped.replace('\\\\', '\\')   # Backslash
                        translated = _(stripped)
                        if stripped != translated:
                            # Already translated
                            outWrite(line)
                            outWrite('msgstr "')
                            translated = translated.encode(encoding)
                            # Re-escape the escape sequences
                            translated = translated.replace('\\','\\\\')
                            translated = translated.replace('\t','\\t')
                            translated = reNonEscapedQuote.sub(subQuote,translated)
                            outWrite(translated)
                            outWrite('"\n')
                        else:
                            # Not translated
                            outWrite(line)
                            outWrite('msgstr ""\n')
                    elif line[0:8] == 'msgstr "':
                        continue
                    else:
                        outWrite(line)
    except:
        try: os.remove(tmpTxt)
        except: pass
    else:
        try:
            os.remove(fullTxt)
            os.rename(tmpTxt,fullTxt)
        except:
            if os.path.exists(fullTxt):
                try: os.remove(tmpTxt)
                except: pass
    return outTxt

def initTranslator(language=None,path=None):
    if not language:
        try:
            language = locale.getlocale()[0].split('_',1)[0]
            language = decode(language)
        except UnicodeError:
            deprint(u'Still unicode problems detecting locale:', repr(locale.getlocale()),traceback=True)
            # Default to English
            language = u'English'
    path = path or os.path.join(u'bash',u'l10n')
    if language.lower() == u'german': language = u'de'
    txt,po,mo = (os.path.join(path,language+ext)
                 for ext in (u'.txt',u'.po',u'.mo'))
    if not os.path.exists(txt) and not os.path.exists(mo):
        if language.lower() != u'english':
            print u'No translation file for language:', language
        trans = gettext.NullTranslations()
    else:
        try:
            if not os.path.exists(mo) or (os.path.getmtime(txt) > os.path.getmtime(mo)):
                # Compile
                shutil.copy(txt,po)
                args = [u'm',u'-o',mo,po]
                if hasattr(sys,'frozen'):
                    import msgfmt
                    old_argv = sys.argv[:]
                    sys.argv = args
                    msgfmt.main()
                    sys.argv = old_argv
                else:
                    m = os.path.join(sys.prefix,u'Tools',u'i18n',u'msgfmt.py')
                    subprocess.call([m,u'-o',mo,po],shell=True)
                os.remove(po)
            # install translator
            with open(mo,'rb') as file:
                trans = gettext.GNUTranslations(file)
        except:
            print 'Error loading translation file:'
            traceback.print_exc()
            trans = gettext.NullTranslations()
    trans.install(unicode=True)

#--Do translator test and set
if locale.getlocale() == (None,None):
    locale.setlocale(locale.LC_ALL,u'')
initTranslator(bass.language)

CBash = 0
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
    def __init__(self,message=u'Abstract section called.'):
        BoltError.__init__(self,message)

#------------------------------------------------------------------------------
class ArgumentError(BoltError):
    """Coding Error: Argument out of allowed range of values."""
    def __init__(self,message=u'Argument is out of allowed ranged of values.'):
        BoltError.__init__(self,message)

#------------------------------------------------------------------------------
class StateError(BoltError):
    """Error: Object is corrupted."""
    def __init__(self,message=u'Object is in a bad state.'):
        BoltError.__init__(self,message)

#------------------------------------------------------------------------------
class UncodedError(BoltError):
    """Coding Error: Call to section of code that hasn't been written."""
    def __init__(self,message=u'Section is not coded yet.'):
        BoltError.__init__(self,message)

#------------------------------------------------------------------------------
class CancelError(BoltError):
    """User pressed 'Cancel' on the progress meter."""
    def __init__(self,message=u'Action aborted by user.'):
        BoltError.__init__(self, message)

class SkipError(CancelError):
    """User pressed Skipped n operations."""
    def __init__(self):
        CancelError.__init__(self, u'Action skipped by user.')

#------------------------------------------------------------------------------
class PermissionError(BoltError):
    """Wrye Bash doesn't have permission to access the specified file/directory."""
    def __init__(self,message=u'Access is denied.'):
        BoltError.__init__(self,message)

#------------------------------------------------------------------------------
class FileError(BoltError):
    """TES4/Tes4SaveFile Error: File is corrupted."""
    def __init__(self,inName,message):
        BoltError.__init__(self,message)
        self.inName = inName

    def __str__(self):
        if self.inName: # Path or basestring
            return (u'%s: ' % self.inName) + self.message
        return u'Unknown File: ' + self.message

#------------------------------------------------------------------------------
class FileEditError(BoltError):
    """Unable to edit a file"""
    def __init__(self,filePath,message=None):
        message = message or u"Unable to edit file %s." % filePath.s
        BoltError.__init__(self,message)
        self.filePath = filePath

# LowStrings ------------------------------------------------------------------
class LString(object):
    """Strings that compare as lower case strings."""
    __slots__ = ('_s','_cs')

    def __init__(self,s):
        if isinstance(s,LString):
            self._s = s._s
            self._cs = s._cs
        else:
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
        return u'bolt.LString('+repr(self._s)+u')'

    def __add__(self,other):
        return LString(self._s + other)

    #--Hash/Compare
    def __hash__(self):
        return hash(self._cs)
    def __cmp__(self, other):
        if isinstance(other,LString): return cmp(self._cs, other._cs)
        else: return cmp(self._cs, other.lower())

# sio - StringIO wrapper so it uses the 'with' statement, so they can be used
#  in the same functions that accept files as input/output as well.  Really,
#  StringIO objects don't need to 'close' ever, since the data is unallocated
#  once the object is destroyed.
#------------------------------------------------------------------------------
class sio(StringIO.StringIO):
    def __enter__(self): return self
    def __exit__(self, exc_type, exc_value, exc_traceback): self.close()

# Paths -----------------------------------------------------------------------
#------------------------------------------------------------------------------
_gpaths = {}

def GPath(name):
    """Path factory and cache.
    :rtype: Path
    """
    if name is None: return None
    elif isinstance(name,Path): norm = name._s
    elif not name: norm = name # empty string - bin this if ?
    elif isinstance(name,unicode): norm = os.path.normpath(name)
    else: norm = os.path.normpath(decode(name))
    path = _gpaths.get(norm)
    if path is not None: return path
    else: return _gpaths.setdefault(norm,Path(norm))

def GPathPurge():
    """Cleans out the _gpaths dictionary of any unused bolt.Path objects.
       We cannot use a weakref.WeakValueDictionary in this case for 2 reasons:
        1) bolt.Path, due to its class structure, cannot be made into weak
           references
        2) the objects would be deleted as soon as the last reference goes
           out of scope (not the behavior we want).  We want the object to
           stay alive as long as we will possibly be needing it, IE: as long
           as we're still on the same tab.
       So instead, we'll manually call our flushing function a few times:
        1) When switching tabs
        2) Prior to building a bashed patch
        3) Prior to saving settings files
    """
    for key in _gpaths.keys():
        # Using .keys() allows use to modify the dictionary while iterating
        if sys.getrefcount(_gpaths[key]) == 2:
            # 1 for the reference in the _gpaths dictionary,
            # 1 for the temp reference passed to sys.getrefcount
            # meanin the object is not reference anywhere else
            del _gpaths[key]

#------------------------------------------------------------------------------
class Path(object):
    """Paths are immutable objects that represent file directory paths.
     May be just a directory, filename or full path."""

    #--Class Vars/Methods -------------------------------------------
    sys_fs_enc = sys.getfilesystemencoding() or 'mbcs'
    invalid_chars_re = re.compile(ur'(.*)([/\\:*?"<>|]+)(.*)', re.I | re.U)

    @staticmethod
    def getNorm(name):
        """Return the normpath for specified name/path object."""
        if isinstance(name,Path): return name._s
        elif not name: return name
        elif isinstance(name,str): name = decode(name)
        return os.path.normpath(name)

    @staticmethod
    def __getCase(name):
        """Return the normpath+normcase for specified name/path object."""
        if not name: return name
        if isinstance(name, str): name = decode(name)
        return os.path.normcase(os.path.normpath(name))

    @staticmethod
    def getcwd():
        return Path(os.getcwdu())

    def setcwd(self):
        """Set cwd."""
        os.chdir(self._s)

    @staticmethod
    def has_invalid_chars(string):
        match = Path.invalid_chars_re.match(string)
        if not match: return None
        return match.groups()[1]

    #--Instance stuff --------------------------------------------------
    #--Slots: _s is normalized path. All other slots are just pre-calced
    #  variations of it.
    __slots__ = ('_s', '_cs', '_sroot', '_shead', '_stail', '_ext',
                 '_cext', '_sbody')

    def __init__(self, name):
        """Initialize."""
        if isinstance(name,Path):
            self.__setstate__(name._s)
        else:
            self.__setstate__(name)

    def __getstate__(self):
        """Used by pickler. _cs is redundant,so don't include."""
        return self._s

    def __setstate__(self,norm):
        """Used by unpickler. Reconstruct _cs."""
        # Older pickle files stored filename in str, not unicode
        if not isinstance(norm,unicode): norm = decode(norm)
        self._s = norm
        self._cs = os.path.normcase(self._s)
        self._shead,self._stail = os.path.split(self._s)

    def __len__(self):
        return len(self._s)

    def __repr__(self):
        return u"bolt.Path("+repr(self._s)+u")"

    def __unicode__(self):
        return self._s

    #--Properties--------------------------------------------------------
    #--String/unicode versions.
    @property
    def s(self):
        """Path as string."""
        return self._s
    @property
    def cs(self):
        """Path as string in normalized case."""
        return self._cs
    @property
    def sroot(self):
        """Root as string."""
        try:
            return self._sroot
        except AttributeError:
            self._sroot, self._ext = os.path.splitext(self._s)
            return self._sroot
    @property
    def shead(self):
        """Head as string."""
        return self._shead
    @property
    def stail(self):
        """Tail as string."""
        return self._stail
    @property
    def sbody(self):
        """For alpha\beta.gamma returns beta as string."""
        try:
            return self._sbody
        except AttributeError:
            self._sbody = os.path.basename(self.sroot)
            return self._sbody
    @property
    def csbody(self):
        """For alpha\beta.gamma returns beta as string in normalized case."""
        return os.path.normcase(self.sbody)

    #--Head, tail
    @property
    def headTail(self):
        """For alpha\beta.gamma returns (alpha,beta.gamma)"""
        return map(GPath,(self._shead,self._stail))
    @property
    def head(self):
        """For alpha\beta.gamma, returns alpha."""
        return GPath(self._shead)
    @property
    def tail(self):
        """For alpha\beta.gamma, returns beta.gamma."""
        return GPath(self._stail)
    @property
    def body(self):
        """For alpha\beta.gamma, returns beta."""
        return GPath(self.sbody)

    #--Root, ext
    @property
    def root(self):
        """For alpha\beta.gamma returns alpha\beta"""
        return GPath(self.sroot)
    @property
    def ext(self):
        """Extension (including leading period, e.g. '.txt')."""
        try:
            return self._ext
        except AttributeError:
            self._sroot, self._ext = os.path.splitext(self._s)
            return self._ext
    @property
    def cext(self):
        """Extension in normalized case."""
        try:
            return self._cext
        except AttributeError:
            self._cext = os.path.normcase(self.ext)
            return self._cext
    @property
    def temp(self,unicodeSafe=True):
        """Temp file path.  If unicodeSafe is True, the returned
        temp file will be a fileName that can be passes through Popen
        (Popen automatically tries to encode the name)"""
        baseDir = GPath(unicode(tempfile.gettempdir(), Path.sys_fs_enc)).join(u'WryeBash_temp')
        baseDir.makedirs()
        dirJoin = baseDir.join
        if unicodeSafe:
            try:
                self._s.encode('ascii')
                return dirJoin(self.tail+u'.tmp')
            except UnicodeEncodeError:
                ret = unicode(self._s.encode('ascii','xmlcharrefreplace'),'ascii')+u'_unicode_safe.tmp'
                return dirJoin(ret)
        else:
            return dirJoin(self.tail+u'.tmp')

    @staticmethod
    def tempDir(prefix=u'WryeBash_'):
        try: # workaround for http://bugs.python.org/issue1681974 see there
            return GPath(tempfile.mkdtemp(prefix=prefix))
        except UnicodeDecodeError:
            try:
                traceback.print_exc()
                print 'Trying to pass temp dir in...'
                tempdir = unicode(tempfile.gettempdir(), Path.sys_fs_enc)
                return GPath(tempfile.mkdtemp(prefix=prefix, dir=tempdir))
            except UnicodeDecodeError:
                try:
                    traceback.print_exc()
                    print 'Trying to encode temp dir prefix...'
                    return GPath(tempfile.mkdtemp(
                        prefix=prefix.encode(Path.sys_fs_enc)).decode(
                        Path.sys_fs_enc))
                except:
                    traceback.print_exc()
                    print 'Failed to create tmp dir, Bash will not function ' \
                          'correctly.'

    @staticmethod
    def baseTempDir():
        return GPath(unicode(tempfile.gettempdir(), Path.sys_fs_enc))

    @property
    def backup(self):
        """Backup file path."""
        return self+u'.bak'

    #--size, atime, ctime
    @property
    def size(self):
        """Size of file or directory."""
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
    def _getmtime(self):
        """Return mtime for path."""
        return int(os.path.getmtime(self._s))
    def _setmtime(self, mtime):
        os.utime(self._s, (self.atime, int(mtime)))
    mtime = property(_getmtime, _setmtime, doc="Time file was last modified.")

    def size_mtime(self):
        lstat = os.lstat(self._s)
        return lstat.st_size, int(lstat.st_mtime)

    def size_mtime_ctime(self):
        lstat = os.lstat(self._s)
        return lstat.st_size, int(lstat.st_mtime), lstat.st_ctime

    @property
    def stat(self):
        """File stats"""
        return os.stat(self._s)

    @property
    def version(self):
        """File version (exe/dll) embedded in the file properties
        (windows only)."""
        try:
            import win32api
            info = win32api.GetFileVersionInfo(self._s,u'\\')
            ms = info['FileVersionMS']
            ls = info['FileVersionLS']
            version = (win32api.HIWORD(ms),win32api.LOWORD(ms),win32api.HIWORD(ls),win32api.LOWORD(ls))
        except:
            version = (0,0,0,0)
        return version

    @property
    def strippedVersion(self):
        """.version with leading and trailing zeros stripped."""
        version = list(self.version)
        while len(version) > 1 and version[0] == 0:
            version.pop(0)
        while len(version) > 1 and version[-1] == 0:
            version.pop()
        return tuple(version)

    #--crc
    @property
    def crc(self):
        """Calculates and returns crc value for self."""
        size = self.size
        crc = 0L
        with self.open('rb') as ins:
            insRead = ins.read
            insTell = ins.tell
            while insTell() < size:
                crc = crc32(insRead(512),crc)
        return crc & 0xffffffff

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
            for root_dir,dirs,files in os.walk(self._s,topdown,onerror):
                yield (GPath(root_dir[start:]),[GPath(x) for x in dirs],[GPath(x) for x in files])
        else:
            for root_dir,dirs,files in os.walk(self._s,topdown,onerror):
                yield (GPath(root_dir),[GPath(x) for x in dirs],[GPath(x) for x in files])

    def split(self):
        """Splits the path into each of it's sub parts.  IE: C:\Program Files\Bethesda Softworks
           would return ['C:','Program Files','Bethesda Softworks']"""
        dirs = []
        drive, path = os.path.splitdrive(self.s)
        path = path.strip(os.path.sep)
        l,r = os.path.split(path)
        while l != u'':
            dirs.append(r)
            l,r = os.path.split(l)
        dirs.append(r)
        if drive != u'':
            dirs.append(drive)
        dirs.reverse()
        return dirs
    def relpath(self,path):
        return GPath(os.path.relpath(self._s,Path.getNorm(path)))

    def drive(self):
        """Returns the drive part of the path string."""
        return GPath(os.path.splitdrive(self._s)[0])

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
    @staticmethod
    def _onerror(func,path,exc_info):
        """shutil error handler: remove RO flag"""
        if not os.access(path,os.W_OK):
            os.chmod(path,stat.S_IWUSR|stat.S_IWOTH)
            func(path)
        else:
            raise

    def clearRO(self):
        """Clears RO flag on self"""
        if not self.isdir():
            os.chmod(self._s,stat.S_IWUSR|stat.S_IWOTH)
        else:
            try:
                clearReadOnly(self)
            except UnicodeError:
                flags = stat.S_IWUSR|stat.S_IWOTH
                chmod = os.chmod
                for root_dir,dirs,files in os.walk(self._s):
                    rootJoin = root_dir.join
                    for directory in dirs:
                        try: chmod(rootJoin(directory),flags)
                        except: pass
                    for filename in files:
                        try: chmod(rootJoin(filename),flags)
                        except: pass

    def open(self,*args,**kwdargs):
        if self._shead and not os.path.exists(self._shead):
            os.makedirs(self._shead)
        if 'encoding' in kwdargs:
            return codecs.open(self._s,*args,**kwdargs)
        else:
            return open(self._s,*args,**kwdargs)
    def makedirs(self):
        if not self.exists(): os.makedirs(self._s)
    def remove(self):
        try:
            if self.exists(): os.remove(self._s)
        except OSError:
            # Clear RO flag
            os.chmod(self._s,stat.S_IWUSR|stat.S_IWOTH)
            os.remove(self._s)
    def removedirs(self):
        try:
            if self.exists(): os.removedirs(self._s)
        except OSError:
            self.clearRO()
            os.removedirs(self._s)
    def rmtree(self,safety='PART OF DIRECTORY NAME'):
        """Removes directory tree. As a safety factor, a part of the directory name must be supplied."""
        if self.isdir() and safety and safety.lower() in self._cs:
            shutil.rmtree(self._s,onerror=Path._onerror)

    #--start, move, copy, touch, untemp
    def start(self, exeArgs=None):
        """Starts file as if it had been doubleclicked in file explorer."""
        if self.cext == u'.exe':
            if not exeArgs:
                subprocess.Popen([self.s], close_fds=close_fds)
            else:
                subprocess.Popen(exeArgs, executable=self.s, close_fds=close_fds)
        else:
            os.startfile(self._s)
    def copyTo(self,destName):
        """Copy self to destName, make dirs if necessary and preserve mtime."""
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
            raise StateError(self._s + u' cannot be moved because it does not exist.')
        destPath = GPath(destName)
        if destPath._cs == self._cs: return
        if destPath._shead and not os.path.exists(destPath._shead):
            os.makedirs(destPath._shead)
        elif destPath.exists():
            destPath.remove()
        try:
            shutil.move(self._s,destPath._s)
        except OSError:
            self.clearRO()
            shutil.move(self._s,destPath._s)

    def tempMoveTo(self,destName):
        """Temporarily rename/move an object.  Use with the 'with' statement"""
        class temp(object):
            def __init__(self,oldPath,newPath):
                self.newPath = GPath(newPath)
                self.oldPath = GPath(oldPath)

            def __enter__(self): return self.newPath
            def __exit__(self, exc_type, exc_value, exc_traceback): self.newPath.moveTo(self.oldPath)
        self.moveTo(destName)
        return temp(self,destName)

    def unicodeSafe(self):
        """Temporarily rename (only if necessary) the file to a unicode safe name.
           Use with the 'with' statement."""
        try:
            self._s.encode('ascii')
            class temp(object):
                def __init__(self,path):
                    self.path = path
                def __enter__(self): return self.path
                def __exit__(self, exc_type, exc_value, exc_traceback): pass
            return temp(self)
        except UnicodeEncodeError:
            return self.tempMoveTo(self.temp)

    def touch(self):
        """Like unix 'touch' command. Creates a file with current date/time."""
        if self.exists():
            self.mtime = time.time()
        else:
            with self.temp.open('w'):
                pass
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
    def editable(self):
        """Safely check whether a file is editable."""
        delete = not os.path.exists(self._s)
        try:
            with open(self._s,'ab') as f:
                return True
        except:
            return False
        finally:
            # If the file didn't exist before, remove the created version
            if delete:
                try:
                    os.remove(self._s)
                except:
                    pass

    #--Hash/Compare, based on the _cs attribute so case insensitive. NB: Paths
    # directly compare to basestring and Path and will blow for anything else
    def __hash__(self):
        return hash(self._cs)
    def __eq__(self, other):
        if isinstance(other, Path):
            return self._cs == other._cs
        else:
            return self._cs == Path.__getCase(other)
    def __ne__(self, other):
        if isinstance(other, Path):
            return self._cs != other._cs
        else:
            return self._cs != Path.__getCase(other)
    def __lt__(self, other):
        if isinstance(other, Path):
            return self._cs < other._cs
        else:
            return self._cs < Path.__getCase(other)
    def __ge__(self, other):
        if isinstance(other, Path):
            return self._cs >= other._cs
        else:
            return self._cs >= Path.__getCase(other)
    def __gt__(self, other):
        if isinstance(other, Path):
            return self._cs > other._cs
        else:
            return self._cs > Path.__getCase(other)
    def __le__(self, other):
        if isinstance(other, Path):
            return self._cs <= other._cs
        else:
            return self._cs <= Path.__getCase(other)

def clearReadOnly(dirPath):
    """Recursively (/S) clear ReadOnly flag if set - include folders (/D)."""
    cmd = ur'attrib -R "%s\*" /S /D' % dirPath.s
    subprocess.call(cmd, startupinfo=startupinfo)

# Util Constants --------------------------------------------------------------
#--Unix new lines
reUnixNewLine = re.compile(ur'(?<!\r)\n',re.U)

# Util Classes ----------------------------------------------------------------
#------------------------------------------------------------------------------
class CsvReader:
    """For reading csv files. Handles comma, semicolon and tab separated (excel) formats.
       CSV files must be encoded in UTF-8"""
    @staticmethod
    def utf_8_encoder(unicode_csv_data):
        for line in unicode_csv_data:
            yield line.encode('utf8')

    def __init__(self,path):
        self.ins = path.open('rb',encoding='utf-8-sig')
        format = ('excel','excel-tab')[u'\t' in self.ins.readline()]
        if format == 'excel':
            delimiter = (',',';')[u';' in self.ins.readline()]
            self.ins.seek(0)
            self.reader = csv.reader(CsvReader.utf_8_encoder(self.ins),format,delimiter=delimiter)
        else:
            self.ins.seek(0)
            self.reader = csv.reader(CsvReader.utf_8_encoder(self.ins),format)

    def __enter__(self): return self
    def __exit__(self, exc_type, exc_value, exc_traceback): self.ins.close()

    def __iter__(self):
        for iter in self.reader:
            yield [unicode(x,'utf8') for x in iter]

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
        """Returns a clone of self, optionally with new value."""
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
        return u'%08X' % (self._field,)
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
class DataDict(object):
    """Mixin class that handles dictionary emulation, assuming that
    dictionary is its 'data' attribute."""

    def __contains__(self,key):
        return key in self.data
    def __getitem__(self,key):
        """Return value for key or raise KeyError if not present."""
        return self.data[key]
    def __setitem__(self,key,value):
        self.data[key] = value
    def __delitem__(self,key):
        del self.data[key]
    def __len__(self):
        return len(self.data)
    def setdefault(self,key,default):
        return self.data.setdefault(key,default)
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
from collections import MutableSet
class OrderedSet(list, MutableSet):
    """A set like object, that remembers the order items were added to it.
       Since it has order, a few list functions were added as well:
        - index(value)
        - __getitem__(index)
        - __call__ -> to enable 'enumerate'
       If an item is discarded, then later readded, it will be added
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
    def __repr__(self): return u'OrderedSet%s' % unicode(list(self))[1:-1]
    def __unicode__(self): return u'{%s}' % unicode(list(self))[1:-1]

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

        a==b -> compares the 'not-deleted' items of the MemorySets.  If both are the same,
                and in the same order, then they are equal.
        a!=b -> oposite of a==b
    """
    def __init__(self, *args, **kwdargs):
        self.items = OrderedSet(*args, **kwdargs)
        self.mask = [True] * len(self.items)

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
    def __str__(self): return u'{%s}' % (','.join(map(repr,self._items())))
    def __repr__(self): return u'MemorySet([%s])' % (','.join(map(repr,self._items())))
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

    def __eq__(self,other): return list(self) == list(other)
    def __ne__(self,other): return list(self) != list(other)

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
        attrs = args.pop(0).split(u'.')
        key = attrs.pop(0)
        func = self.funcs.get(key)
        if not func:
            msg = _(u"Unknown function/object: %s") % key
            try: print msg
            except UnicodeError: print msg.encode('mbcs')
            return
        for attr in attrs:
            func = getattr(func,attr)
        #--Separate out keywords args
        keywords = {}
        argDex = 0
        reKeyArg  = re.compile(ur'^-(\D\w+)',re.U)
        reKeyBool = re.compile(ur'^\+(\D\w+)',re.U)
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
                argDex += 1
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

    class Mold(Exception):
        def __init__(self, moldedFile):
            msg = (u'Your settings in %s come from an ancient Bash version. '
                   u'Please load them in 306 so they are converted '
                   u'to the newer format' % moldedFile)
            super(PickleDict.Mold, self).__init__(msg)

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
        cor = cor_name =  None
        for path in (self.path,self.backup):
            if cor is not None:
                cor.moveTo(cor_name)
                cor = None
            if path.exists():
                try:
                    with path.open('rb') as ins:
                        try:
                            firstPickle = cPickle.load(ins)
                        except ValueError:
                            cor = path
                            cor_name = GPath(path.s + u' (%s)' % timestamp() +
                                    u'.corrupted')
                            deprint(u'Unable to load %s (moved to "%s")' % (
                                path, cor_name.tail), traceback=True)
                            continue # file corrupt - try next file
                        if firstPickle == 'VDATA2':
                            self.vdata.update(cPickle.load(ins))
                            self.data.update(cPickle.load(ins))
                        else:
                            raise PickleDict.Mold(path)
                    return 1 + (path == self.backup)
                except (EOFError, ValueError):
                    pass
        #--No files and/or files are corrupt
        return 0

    def save(self):
        """Save to pickle file.

        Three objects are writen - a version string and the vdata and data
        dictionaries, in this order. Current version string is VDATA2.
        """
        if self.readOnly: return False
        #--Pickle it
        self.vdata['boltPaths'] = True # needed so pre 307 versions don't blow
        with self.path.temp.open('wb') as out:
            for data in ('VDATA2',self.vdata,self.data):
                cPickle.dump(data,out,-1)
        self.path.untemp(doBackup=True)
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

    def __init__(self, dictFile):
        """Initialize. Read settings from dictFile."""
        self.dictFile = dictFile
        self.cleanSave = False
        if self.dictFile:
            res = dictFile.load()
            self.cleanSave = res == 0 # no data read - do not attempt to read on save
            self.vdata = dictFile.vdata.copy()
            self.data = dictFile.data.copy()
        else:
            self.vdata = {}
            self.data = {}
        self.defaults = {}
        self.changed = set()
        self.deleted = set()

    def loadDefaults(self,defaults):
        """Add default settings to dictionary. Will not replace values that are already set."""
        self.defaults = defaults
        for key in defaults.keys():
            if key not in self.data:
                self.data[key] = copy.deepcopy(defaults[key])

    def save(self):
        """Save to pickle file. Only key/values marked as changed are saved."""
        dictFile = self.dictFile
        if not dictFile or dictFile.readOnly: return
        # on a clean save ignore BashSettings.dat.bak possibly corrupt
        if not self.cleanSave: dictFile.load()
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
            raise ArgumentError(u'No settings data for '+key)
        self.changed.add(key)

    def getChanged(self,key,default=None):
        """Gets and marks as changed."""
        if default is not None and key not in self.data:
            self.data[key] = default
        self.setChanged(key)
        return self.data.get(key)

    #--Dictionary Emulation
    def __setitem__(self,key,value):
        """Dictionary emulation. Marks key as changed."""
        if key in self.deleted: self.deleted.remove(key)
        self.changed.add(key)
        self.data[key] = value

    def __delitem__(self,key):
        """Dictionary emulation. Marks key as deleted."""
        if key in self.changed: self.changed.remove(key)
        self.deleted.add(key)
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
        self.deleted.add(key)
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
                raise UncodedError(u'String too long to convert.')
        return self.read(strLen)

    def writeNetString(self,str):
        """Write string as a .net string. THIS CODE IS DUBIOUS!"""
        strLen = len(str)
        if strLen < 128:
            self.pack('b',strLen)
        elif strLen > 0x7FFF: #--Actually probably fails earlier.
            raise UncodedError(u'String too long to convert.')
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
            if args[1] == 'r': new_args[1] = 'rb'
            elif args[1] == 'w': new_args[1] = 'wb'
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
        return [(key,tableData[key][column]) for key in self]
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
        """Initialize and read data from dictFile, if available."""
        self.dictFile = dictFile
        dictFile.load()
        self.vdata = dictFile.vdata
        self.data = dictFile.data
        self.hasChanged = False ##: move to PickleDict

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
        return self.data.setdefault(key,default)
    def pop(self,key,default=None):
        self.hasChanged = True
        return self.data.pop(key,default)

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
    csvFormat = u''
    for char in format:
        if char in u'bBhHiIlLqQ': csvFormat += u',%d'
        elif char in u'fd': csvFormat += u',%f'
        elif char in u's': csvFormat += u',"%s"'
    return csvFormat[1:] #--Chop leading comma

deprintOn = False

class tempDebugMode(object):
    __slots__= '_old'
    def __init__(self):
        global deprintOn
        self._old = deprintOn
        deprintOn = True

    def __enter__(self): return self
    def __exit__(self, exc_type, exc_value, exc_traceback):
        global deprintOn
        deprintOn = self._old

import inspect
def deprint(*args,**keyargs):
    """Prints message along with file and line location."""
    if not deprintOn and not keyargs.get('on'): return

    if keyargs.get('trace', True):
        stack = inspect.stack()
        file_, line, function = stack[1][1:4]
        msg = u'%s %4d %s: ' % (GPath(file_).tail.s, line, function)
    else:
        msg = u''

    try:
        msg += u' '.join([u'%s'%x for x in args]) # OK, even with unicode args
    except UnicodeError:
        # If the args failed to convert to unicode for some reason
        # we still want the message displayed any way we can
        for x in args:
            try:
                msg += u' %s' % x
            except UnicodeError:
                msg += u' %s' % repr(x)

    if keyargs.get('traceback',False):
        o = StringIO.StringIO()
        traceback.print_exc(file=o)
        value = o.getvalue()
        try:
            msg += u'\n%s' % unicode(value, 'utf-8')
        except UnicodeError:
            traceback.print_exc()
            msg += u'\n%s' % repr(value)
        o.close()
    try:
        # Should work if stdout/stderr is going to wxPython output
        print msg
    except UnicodeError:
        # Nope, it's going somewhere else
        print msg.encode(Path.sys_fs_enc)

def getMatch(reMatch,group=0):
    """Returns the match or an empty string."""
    if reMatch: return reMatch.group(group)
    else: return u''

def intArg(arg,default=None):
    """Returns argument as an integer. If argument is a string, then it converts it using int(arg,0)."""
    if arg is None: return default
    elif isinstance(arg,types.StringTypes): return int(arg,0)
    else: return int(arg)

def winNewLines(inString):
    """Converts unix newlines to windows newlines."""
    return reUnixNewLine.sub(u'\r\n',inString)

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
            self.prevHeader += u'x'
        self.doFooter = doFooter
        if writeNow: self()

    def __call__(self,message=None,appendNewline=True):
        """Callable. Writes message, and if necessary, header and footer."""
        if self.header != self.prevHeader:
            if self.prevHeader and self.doFooter:
                self.writeFooter()
            if self.header:
                self.writeLogHeader(self.header)
            self.prevHeader = self.header
        if message: self.writeMessage(message,appendNewline)

    #--Abstract/null writing functions...
    def writeLogHeader(self, header):
        """Write header. Abstract/null version."""
        pass
    def writeFooter(self):
        """Write mess. Abstract/null version."""
        pass
    def writeMessage(self,message,appendNewline):
        """Write message to log. Abstract/null version."""
        pass

#------------------------------------------------------------------------------
class LogFile(Log):
    """Log that writes messages to file."""
    def __init__(self,out):
        self.out = out
        Log.__init__(self)

    def writeLogHeader(self, header):
        self.out.write(header+u'\n')

    def writeFooter(self):
        self.out.write(u'\n')

    def writeMessage(self,message,appendNewline):
        self.out.write(message)
        if appendNewline: self.out.write(u'\n')

#------------------------------------------------------------------------------
class Progress:
    """Progress Callable: Shows progress when called."""
    def __init__(self,full=1.0):
        if (1.0*full) == 0: raise ArgumentError(u'Full must be non-zero!')
        self.message = u''
        self.full = 1.0 * full
        self.state = 0
        self.debug = False

    def getParent(self):
        return None

    def setFull(self,full):
        """Set's full and for convenience, returns self."""
        if (1.0*full) == 0: raise ArgumentError(u'Full must be non-zero!')
        self.full = 1.0 * full
        return self

    def plus(self,increment=1):
        """Increments progress by 1."""
        self.__call__(self.state+increment)

    def __call__(self,state,message=''):
        """Update progress with current state. Progress is state/full."""
        if (1.0*self.full) == 0: raise ArgumentError(u'Full must be non-zero!')
        if message: self.message = message
        if self.debug: deprint(u'%0.3f %s' % (1.0*state/self.full, self.message))
        self._do_progress(1.0 * state / self.full, self.message)
        self.state = state

    def _do_progress(self, state, message):
        """Default _do_progress does nothing."""

    # __enter__ and __exit__ for use with the 'with' statement
    def __enter__(self): return self
    def __exit__(self, exc_type, exc_value, exc_traceback): pass

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
        if baseFrom < 0 or baseFrom >= baseTo:
            raise ArgumentError(u'BaseFrom must be >= 0 and BaseTo must be > BaseFrom')
        self.parent = parent
        self.baseFrom = baseFrom
        self.scale = 1.0*(baseTo-baseFrom)
        self.silent = silent

    def __call__(self,state,message=u''):
        """Update progress with current state. Progress is state/full."""
        if self.silent: message = u''
        self.parent(self.baseFrom+self.scale*state/self.full,message)
        self.state = state

#------------------------------------------------------------------------------
class ProgressFile(Progress): # CRUFT
    """Prints progress to file (stdout by default)."""
    def __init__(self,full=1.0,out=None):
        Progress.__init__(self,full)
        self.out = out or sys.stdout

    def _do_progress(self, progress, message):
        msg = u'%0.2f %s\n' % (progress,message)
        try: self.out.write(msg)
        except UnicodeError: self.out.write(msg.encode('mbcs'))

#------------------------------------------------------------------------------
class StringTable(dict):
    """For reading .STRINGS, .DLSTRINGS, .ILSTRINGS files."""
    encodings = {
        # Encoding to fall back to if UTF-8 fails, based on language
        # Default is 1252 (Western European), so only list languages
        # different than that
        u'russian': 'cp1251',
        }

    def load(self,modFilePath,language=u'English',progress=Progress()):
        baseName = modFilePath.tail.body
        baseDir = modFilePath.head.join(u'Strings')
        files = (baseName+u'_'+language+x for x in (u'.STRINGS',u'.DLSTRINGS',
                                                   u'.ILSTRINGS'))
        files = (baseDir.join(file) for file in files)
        self.clear()
        progress.setFull(3)
        for i,file in enumerate(files):
            progress(i)
            self.loadFile(file,SubProgress(progress,i,i+1))

    def loadFile(self,path,progress,language=u'english'):
        if path.cext == u'.strings': format = 0
        else: format = 1
        language = language.lower()
        backupEncoding = self.encodings.get(language,'cp1252')
        try:
            with BinaryFile(path.s) as ins:
                insSeek = ins.seek
                insTell = ins.tell
                insUnpack = ins.unpack
                insReadCString = ins.readCString
                insRead = ins.read

                insSeek(0,os.SEEK_END)
                eof = insTell()
                insSeek(0)
                if eof < 8:
                    deprint(u"Warning: Strings file '%s' file size (%d) is less than 8 bytes.  8 bytes are the minimum required by the expected format, assuming the Strings file is empty."
                            % (path, eof))
                    return

                numIds,dataSize = insUnpack('=2I',8)
                progress.setFull(max(numIds,1))
                stringsStart = 8 + (numIds*8)
                if stringsStart != eof-dataSize:
                    deprint(u"Warning: Strings file '%s' dataSize element (%d) results in a string start location of %d, but the expected location is %d"
                            % (path, dataSize, eof-dataSize, stringsStart))

                id_ = -1
                offset = -1
                for x in xrange(numIds):
                    try:
                        progress(x)
                        id_,offset = insUnpack('=2I',8)
                        pos = insTell()
                        insSeek(stringsStart+offset)
                        if format:
                            strLen, = insUnpack('I',4)
                            value = insRead(strLen)
                        else:
                            value = insReadCString()
                        value = cstrip(value)
                        try:
                            value = unicode(value,'utf-8')
                        except UnicodeDecodeError:
                            value = unicode(value,backupEncoding)
                        insSeek(pos)
                        self[id_] = value
                    except:
                        deprint(u'Error reading string file:')
                        deprint(u'id:', id_)
                        deprint(u'offset:', offset)
                        deprint(u'filePos:',  insTell())
                        raise
        except:
            deprint(u'Error loading string file:', path.stail, traceback=True)
            return

# WryeText --------------------------------------------------------------------
codebox = None
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
    htmlHead = u"""<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.0 Strict//EN"
    "http://www.w3.org/TR/xhtml1/DTD/xhtml1-strict.dtd">
    <html xmlns="http://www.w3.org/1999/xhtml" xml:lang="en" lang="en">
    <head>
    <meta http-equiv="Content-Type" content="text/html;charset=utf-8" />
    <title>%s</title>
    <style type="text/css">%s</style>
    </head>
    <body>
    """
    defaultCss = u"""
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
    .code-n { background-color: #FDF5E6; font-family: "Lucide Console", monospace; font-size: 10pt; white-space: pre; }
    pre { border: 1px solid; overflow: auto; width: 750px; word-wrap: break-word; background: #FDF5E6; padding: 0.5em; margin-top: 0in; margin-bottom: 0in; margin-left: 0.25in}
    code { background-color: #FDF5E6; font-family: "Lucida Console", monospace; font-size: 10pt; }
    td.code { background-color: #FDF5E6; font-family: "Lucida Console", monospace; font-size: 10pt; border: 1px solid #000000; padding:5px; width:50%;}
    body { background-color: #ffffcc; }
    """

    # Conversion ---------------------------------------------------------------
    @staticmethod
    def genHtml(ins,out=None,*cssDirs):
        """Reads a wtxt input stream and writes an html output stream."""
        import string, urllib
        # Path or Stream? -----------------------------------------------
        if isinstance(ins,(Path,str,unicode)):
            srcPath = GPath(ins)
            outPath = GPath(out) or srcPath.root+u'.html'
            cssDirs = (srcPath.head,) + cssDirs
            ins = srcPath.open(encoding='utf-8-sig')
            out = outPath.open('w',encoding='utf-8-sig')
        else:
            srcPath = outPath = None
        # Setup
        outWrite = out.write

        cssDirs = map(GPath,cssDirs)
        # Setup ---------------------------------------------------------
        #--Headers
        reHead = re.compile(ur'(=+) *(.+)',re.U)
        headFormat = u"<h%d><a id='%s'>%s</a></h%d>\n"
        headFormatNA = u"<h%d>%s</h%d>\n"
        #--List
        reWryeList = re.compile(ur'( *)([-x!?.+*o])(.*)',re.U)
        #--Code
        reCode = re.compile(ur'\[code\](.*?)\[/code\]',re.I|re.U)
        reCodeStart = re.compile(ur'(.*?)\[code\](.*?)$',re.I|re.U)
        reCodeEnd = re.compile(ur'(.*?)\[/code\](.*?)$',re.I|re.U)
        reCodeBoxStart = re.compile(ur'\s*\[codebox\](.*?)',re.I|re.U)
        reCodeBoxEnd = re.compile(ur'(.*?)\[/codebox\]\s*',re.I|re.U)
        reCodeBox = re.compile(ur'\s*\[codebox\](.*?)\[/codebox\]\s*',re.I|re.U)
        codeLines = None
        codeboxLines = None
        def subCode(match):
            try:
                return u' '.join(codebox([match.group(1)],False,False))
            except:
                return match(1)
        #--Misc. text
        reHr = re.compile(u'^------+$',re.U)
        reEmpty = re.compile(ur'\s+$',re.U)
        reMDash = re.compile(ur' -- ',re.U)
        rePreBegin = re.compile(u'<pre',re.I|re.U)
        rePreEnd = re.compile(u'</pre>',re.I|re.U)
        anchorlist = [] #to make sure that each anchor is unique.
        def subAnchor(match):
            text = match.group(1)
            # This one's weird.  Encode the url to utf-8, then allow urllib to do it's magic.
            # urllib will automatically take any unicode characters and escape them, so to
            # convert back to unicode for purposes of storing the string, everything will
            # be in cp1252, due to the escapings.
            anchor = unicode(urllib.quote(reWd.sub(u'',text).encode('utf8')),'cp1252')
            count = 0
            if re.match(ur'\d', anchor):
                anchor = u'_' + anchor
            while anchor in anchorlist and count < 10:
                count += 1
                if count == 1:
                    anchor += unicode(count)
                else:
                    anchor = anchor[:-1] + unicode(count)
            anchorlist.append(anchor)
            return u"<a id='%s'>%s</a>" % (anchor,text)
        #--Bold, Italic, BoldItalic
        reBold = re.compile(ur'__',re.U)
        reItalic = re.compile(ur'~~',re.U)
        reBoldItalic = re.compile(ur'\*\*',re.U)
        states = {'bold':False,'italic':False,'boldItalic':False,'code':0}
        def subBold(match):
            state = states['bold'] = not states['bold']
            return u'<b>' if state else u'</b>'
        def subItalic(match):
            state = states['italic'] = not states['italic']
            return u'<i>' if state else u'</i>'
        def subBoldItalic(match):
            state = states['boldItalic'] = not states['boldItalic']
            return u'<i><b>' if state else u'</b></i>'
        #--Preformatting
        #--Links
        reLink = re.compile(ur'\[\[(.*?)\]\]',re.U)
        reHttp = re.compile(ur' (http://[_~a-zA-Z0-9./%-]+)',re.U)
        reWww = re.compile(ur' (www\.[_~a-zA-Z0-9./%-]+)',re.U)
        reWd = re.compile(ur'(<[^>]+>|\[\[[^\]]+\]\]|\s+|[%s]+)' % re.escape(string.punctuation.replace(u'_',u'')),re.U)
        rePar = re.compile(ur'^(\s*[a-zA-Z(;]|\*\*|~~|__|\s*<i|\s*<a)',re.U)
        reFullLink = re.compile(ur'(:|#|\.[a-zA-Z0-9]{2,4}$)',re.U)
        reColor = re.compile(ur'\[\s*color\s*=[\s\"\']*(.+?)[\s\"\']*\](.*?)\[\s*/\s*color\s*\]',re.I|re.U)
        reBGColor = re.compile(ur'\[\s*bg\s*=[\s\"\']*(.+?)[\s\"\']*\](.*?)\[\s*/\s*bg\s*\]',re.I|re.U)
        def subColor(match):
            return u'<span style="color:%s;">%s</span>' % (match.group(1),match.group(2))
        def subBGColor(match):
            return u'<span style="background-color:%s;">%s</span>' % (match.group(1),match.group(2))
        def subLink(match):
            address = text = match.group(1).strip()
            if u'|' in text:
                (address,text) = [chunk.strip() for chunk in text.split(u'|',1)]
                if address == u'#': address += unicode(urllib.quote(reWd.sub(u'',text).encode('utf8')),'cp1252')
            if address.startswith(u'!'):
                newWindow = u' target="_blank"'
                address = address[1:]
            else:
                newWindow = u''
            if not reFullLink.search(address):
                address += u'.html'
            return u'<a href="%s"%s>%s</a>' % (address,newWindow,text)
        #--Tags
        reAnchorTag = re.compile(u'{{A:(.+?)}}',re.U)
        reContentsTag = re.compile(ur'\s*{{CONTENTS=?(\d+)}}\s*$',re.U)
        reAnchorHeadersTag = re.compile(ur'\s*{{ANCHORHEADERS=(\d+)}}\s*$',re.U)
        reCssTag = re.compile(u'\s*{{CSS:(.+?)}}\s*$',re.U)
        #--Defaults ----------------------------------------------------------
        title = u''
        level = 1
        spaces = u''
        cssName = None
        #--Init
        outLines = []
        contents = []
        outLinesAppend = outLines.append
        outLinesExtend = outLines.extend
        addContents = 0
        inPre = False
        anchorHeaders = True
        #--Read source file --------------------------------------------------
        for line in ins:
            line = line.replace('\r\n','\n')
            #--Codebox -----------------------------------
            if codebox:
                if codeboxLines is not None:
                    maCodeBoxEnd = reCodeBoxEnd.match(line)
                    if maCodeBoxEnd:
                        codeboxLines.append(maCodeBoxEnd.group(1))
                        outLinesAppend(u'<pre style="width:850px;">')
                        try:
                            codeboxLines = codebox(codeboxLines)
                        except:
                            pass
                        outLinesExtend(codeboxLines)
                        outLinesAppend(u'</pre>\n')
                        codeboxLines = None
                        continue
                    else:
                        codeboxLines.append(line)
                        continue
                maCodeBox = reCodeBox.match(line)
                if maCodeBox:
                    outLines.append(u'<pre style="width:850px;">')
                    try:
                        outLinesExtend(codebox([maCodeBox.group(1)]))
                    except:
                        outLinesAppend(maCodeBox.group(1))
                    outLinesAppend(u'</pre>\n')
                    continue
                maCodeBoxStart = reCodeBoxStart.match(line)
                if maCodeBoxStart:
                    codeboxLines = [maCodeBoxStart.group(1)]
                    continue
            #--Code --------------------------------------
                if codeLines is not None:
                    maCodeEnd = reCodeEnd.match(line)
                    if maCodeEnd:
                        codeLines.append(maCodeEnd.group(1))
                        try:
                            codeLines = codebox(codeLines,False)
                        except:
                            pass
                        outLinesExtend(codeLines)
                        codeLines = None
                        line = maCodeEnd.group(2)
                    else:
                        codeLines.append(line)
                        continue
                line = reCode.sub(subCode,line)
                maCodeStart = reCodeStart.match(line)
                if maCodeStart:
                    line = maCodeStart.group(1)
                    codeLines = [maCodeStart.group(2)]
            #--Preformatted? -----------------------------
            maPreBegin = rePreBegin.search(line)
            maPreEnd = rePreEnd.search(line)
            if inPre or maPreBegin or maPreEnd:
                inPre = maPreBegin or (inPre and not maPreEnd)
                outLinesAppend(line)
                continue
            #--Font/Background Color
            line = reColor.sub(subColor,line)
            line = reBGColor.sub(subBGColor,line)
            #--Re Matches -------------------------------
            maContents = reContentsTag.match(line)
            maAnchorHeaders = reAnchorHeadersTag.match(line)
            maCss = reCssTag.match(line)
            maHead = reHead.match(line)
            maList  = reWryeList.match(line)
            maPar   = rePar.match(line)
            maEmpty = reEmpty.match(line)
            #--Contents
            if maContents:
                if maContents.group(1):
                    addContents = int(maContents.group(1))
                else:
                    addContents = 100
                inPar = False
            elif maAnchorHeaders:
                anchorHeaders = maAnchorHeaders.group(1) != u'0'
                continue
            #--CSS
            elif maCss:
                #--Directory spec is not allowed, so use tail.
                cssName = GPath(maCss.group(1).strip()).tail
                continue
            #--Headers
            elif maHead:
                lead,text = maHead.group(1,2)
                text = re.sub(u' *=*#?$','',text.strip())
                anchor = unicode(urllib.quote(reWd.sub(u'',text).encode('utf8')),'cp1252')
                level = len(lead)
                if anchorHeaders:
                    if re.match(ur'\d', anchor):
                        anchor = u'_' + anchor
                    count = 0
                    while anchor in anchorlist and count < 10:
                        count += 1
                        if count == 1:
                            anchor += unicode(count)
                        else:
                            anchor = anchor[:-1] + unicode(count)
                    anchorlist.append(anchor)
                    line = (headFormatNA,headFormat)[anchorHeaders] % (level,anchor,text,level)
                    if addContents: contents.append((level,anchor,text))
                else:
                    line = headFormatNA % (level,text,level)
                #--Title?
                if not title and level <= 2: title = text
            #--Paragraph
            elif maPar and not states['code']:
                line = u'<p>'+line+u'</p>\n'
            #--List item
            elif maList:
                spaces = maList.group(1)
                bullet = maList.group(2)
                text = maList.group(3)
                if bullet == u'.': bullet = u'&nbsp;'
                elif bullet == u'*': bullet = u'&bull;'
                level = len(spaces)/2 + 1
                line = spaces+u'<p class="list-%i">'%level+bullet+u'&nbsp; '
                line = line + text + u'</p>\n'
            #--Empty line
            elif maEmpty:
                line = spaces+u'<p class="empty">&nbsp;</p>\n'
            #--Misc. Text changes --------------------
            line = reHr.sub(u'<hr>',line)
            line = reMDash.sub(u' &#150; ',line)
            #--Bold/Italic subs
            line = reBold.sub(subBold,line)
            line = reItalic.sub(subItalic,line)
            line = reBoldItalic.sub(subBoldItalic,line)
            #--Wtxt Tags
            line = reAnchorTag.sub(subAnchor,line)
            #--Hyperlinks
            line = reLink.sub(subLink,line)
            line = reHttp.sub(ur' <a href="\1">\1</a>',line)
            line = reWww.sub(ur' <a href="http://\1">\1</a>',line)
            #--Save line ------------------
            #print line,
            outLines.append(line)
        #--Get Css -----------------------------------------------------------
        if not cssName:
            css = WryeText.defaultCss
        else:
            if cssName.ext != u'.css':
                raise BoltError(u'Invalid Css file: '+cssName.s)
            for css_dir in cssDirs:
                cssPath = GPath(css_dir).join(cssName)
                if cssPath.exists(): break
            else:
                raise BoltError(u'Css file not found: '+cssName.s)
            with cssPath.open('r',encoding='utf-8-sig') as cssIns:
                css = u''.join(cssIns.readlines())
            if u'<' in css:
                raise BoltError(u'Non css tag in '+cssPath.s)
        #--Write Output ------------------------------------------------------
        outWrite(WryeText.htmlHead % (title,css))
        didContents = False
        for line in outLines:
            if reContentsTag.match(line):
                if contents and not didContents:
                    baseLevel = min([level for (level,name,text) in contents])
                    for (level,name,text) in contents:
                        level = level - baseLevel + 1
                        if level <= addContents:
                            outWrite(u'<p class="list-%d">&bull;&nbsp; <a href="#%s">%s</a></p>\n' % (level,name,text))
                    didContents = True
            else:
                outWrite(line)
        outWrite(u'</body>\n</html>\n')
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
            args = [u"..\Wrye Bash.txt"]
        WryeText.genHtml(*args,**keywords)

    #--Command Handler --------------------------------------------------------
    _mainFunctions.main()
