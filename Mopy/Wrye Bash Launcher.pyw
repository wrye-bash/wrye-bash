#!/usr/bin/env python2
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
#  Wrye Bash copyright (C) 2005, 2006, 2007, 2008, 2009 Wrye
#
# =============================================================================

"""This module starts the Wrye Bash application in GUI mode."""
import multiprocessing

# Hacky workarounds so import still work, even when Bash is installed to a
# directory that has non encodable (MBCS) characters in the name.  This is
# a problem with Python that doesn't work with these
import imp, os, sys

class UnicodeImporter(object):
    def find_module(self,fullname,path=None):
        if isinstance(fullname,unicode):
            fullname = fullname.replace(u'.',u'\\')
            exts = (u'.pyc',u'.pyo',u'.py')
        else:
            fullname = fullname.replace('.','\\')
            exts = ('.pyc','.pyo','.py')
        if os.path.exists(fullname) and os.path.isdir(fullname):
            return self
        for ext in exts:
            if os.path.exists(fullname+ext):
                return self

    def load_module(self,fullname):
        if fullname in sys.modules:
            return sys.modules[fullname]
        else:
            sys.modules[fullname] = imp.new_module(fullname)
        if isinstance(fullname,unicode):
            filename = fullname.replace(u'.',u'\\')
            ext = u'.py'
            initfile = u'__init__'
        else:
            filename = fullname.replace('.','\\')
            ext = '.py'
            initfile = '__init__'
        if os.path.exists(filename+ext):
            try:
                with open(filename+ext,'U') as fp:
                    mod = imp.load_source(fullname,filename+ext,fp)
                    sys.modules[fullname] = mod
                    mod.__loader__ = self
                    return mod
            except:
                print 'fail', filename+ext
                raise
        mod = sys.modules[fullname]
        mod.__loader__ = self
        mod.__file__ = os.path.join(os.getcwd(),filename)
        mod.__path__ = [filename]
        #init file
        initfile = os.path.join(filename,initfile+ext)
        if os.path.exists(initfile):
            with open(initfile,'U') as fp:
                code = fp.read()
            exec code in mod.__dict__
        return mod

if not hasattr(sys,'frozen'):
    sys.meta_path = [UnicodeImporter()]

if __name__ == '__main__':
    # Need to call freeze_support before importing bash,
    # so the arg parsing doesn't complain about how
    # freeze_support does multiprocessing
    multiprocessing.freeze_support()
    from bash import bash
    bash.main()
