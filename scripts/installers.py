# -*- coding: utf-8 -*-
#
#==============================================================================
# This script reproduces minimal code from Wrye Bash's 'bash\bolt' and
# 'bash\bosh' modules, to read the InstallersData pickle file 'Installers.dat'.
# This allows recovery of information in the event that the actual installer
# were deleted, but the .dat file is still intact.  It will retrieve the
# Install Order, install status, and configuration of each package, allowing
# for reconstructing the setup to before the files were deleted (granted the
# missing files can be downloaded of course).
#
# Usage:
#   dumpdata.py [input_file]
#
#   input_file: defaults to 'Installers.dat'
#
# bash\bolt and bash\bosh modules, to read the InstallersData pickle
# file, in order to recover information from it in the even that the
# actual files themselves got deleted.  This information can then be
# used to re-download the mods, arrange them properly, configure them as before
#==============================================================================
import sys
import cPickle
import re
import traceback
import codecs
import os

#--Utility functions ----------------------------------------------------------
def _unicode(s):
    # Older Installer.dat files had file names stored as string objects.
    # Newer versions are unicode now, this converts the string to unicode
    # if present.
    if isinstance(s,unicode): return s
    try: return unicode(s,sys.getfilesystemencoding())
    except UnicodeError: return unicode(s,'mbcs')

# Regex's used to trick cPickle into using this module's classes, instead of
# the Wrye Bash modules (which aren't present anyway).
reTransSubOld = re.compile(u'^(bolt|bosh)$',re.U).sub
reTransSubNew = re.compile(u'^bash\.(bolt|bosh)$',re.U).sub

# Wrapper around the input file to cPickle, uses one of the above regex's
# to pass the tricked out information on to cPickle.
class Translator:
    def __init__(self,fp,reSub):
        self.fp = fp
        self.reSub = reSub
    def read(self,*args,**kwdargs):
        return self._translate(self.fp.read(*args,**kwdargs))
    def readline(self,*args,**kwdargs):
        return self._translate(self.fp.readline())
    def _translate(self,s):
        return self.reSub(r'__main__',s)


#--Fake Wrye Bash classes -----------------------------------------------------

class Installer(object):
    # Need to reproduce 'persistent' since it's used to read and write the
    # attributes during pickling/unpickling
    persistent = ('archive','order','group','modified','size','crc',
        'fileSizeCrcs','type','isActive','subNames','subActives',
        'dirty_sizeCrc','comments','readMe','packageDoc','packagePic',
        'src_sizeCrcDate','hasExtraData','skipVoices','espmNots','isSolid',
        'blockSize','overrideSkips','remaps','skipRefresh')

    def __setstate__(self,values):
        map(self.__setattr__,self.persistent,values)
class InstallerMarker(Installer): pass
class InstallerProject(Installer): pass
class InstallerArchive(Installer): pass


class Path(object):
    def __setstate__(self,s):
        s = _unicode(s)
        self.s = s
        self.cs = os.path.normcase(s)
    @property
    def stail(self):
        return os.path.split(self.s)[1]
    def __cmp__(self,other):
        if isinstance(other,Path): return cmp(self.cs,other.cs)
        else: return cmp(self.cs,other)
    def __hash__(self): return hash(self.s)
    def __repr__(self): return u"Path('%s')" % self.s


#--Loads the pickle file ------------------------------------------------------
def load(fileName):
    vdata = {}
    data = {}
    try:
        with open(fileName,'rb') as ins:
            transOld = Translator(ins,reTransSubOld)
            transNew = Translator(ins,reTransSubNew)
            try:
                header = cPickle.load(ins)
            except ValueError as e:
                print 'Error reading header:', e
                return vdata,data
            if header == 'VDATA2':
                vdata.update(cPickle.load(transNew))
                data.update(cPickle.load(transNew))
            elif header == 'VDATA':
                vdata.update(cPickle.load(transOld))
                data.update(cPickle.load(transOld))
    except Exception:
        traceback.print_exc()
    return vdata,data

#--Output ---------------------------------------------------------------------
def format_output(data,out):
    outWrite = out.write
    outWrite(u'# File encoding: UTF-8\r\n\r\n')
    outWrite(u'Install Order, Sub-Packages, and status:\r\n\r\n')

    installers = data['installers']
    for installer in sorted(installers.keys(),key=lambda x: installers[x].order):
        item = installers[installer]
        active = False if isinstance(item,InstallerMarker) else item.isActive
        outWrite(u'%s %02X %s\r\n' % (u'X' if active else u' ',
                                    item.order,installer.stail))
        if isinstance(item,InstallerMarker):
            continue
        espmNots = item.espmNots
        if espmNots:
            outWrite(u'      De-selected Esp/ms:\r\n')
            for espm in sorted(espmNots):
                outWrite(u'        %s\r\n' % espm.stail)
        remaps = item.remaps
        if remaps:
            outWrite(u'      Renamed Esp/ms:\r\n')
            for espm in sorted(remaps.keys(),key=lambda x: os.path.normcase(x)):
                outWrite(u'        %s -> %s\r\n' % (espm,remaps[espm]))
        subs = [_unicode(x) for x in item.subNames]
        lenSubs = len(subs)
        if u'' in subs and lenSubs < 3:
            continue
        elif lenSubs < 2:
            continue
        outWrite(u'      Sub-Packages:\r\n')
        for sub,active in zip(subs,item.subActives):
            if sub == u'': continue
            outWrite(u'       %s %s\r\n' % (u'X' if active else u' ',sub))
    print 'Output writen to file'

def main(file='Installers.dat',*args):
    print 'Loading', file
    vdata,data = load(file)
    if not data: return
    with codecs.open(file+'.dump.txt','w','utf-8') as out:
        format_output(data,out)


if __name__ == '__main__':
    main(*(sys.argv[1:]))
