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
from collections import namedtuple
from .. import balt, bolt, bass

PatcherInfo = namedtuple('PatcherInfo', ['clazz', 'twinPatcher'])

def configIsCBash(patchConfigs): ##: belongs to basher but used also in bosh
    for key in patchConfigs:
        if 'CBash' in key:
            return True
    return False

def exportConfig(patch_name, config, isCBash, win, outDir):
    outFile = patch_name + u'_Configuration.dat'
    outDir.makedirs()
    #--File dialog
    outPath = balt.askSave(win,
        title=_(u'Export Bashed Patch configuration to:'),
        defaultDir=outDir, defaultFile=outFile,
        wildcard=u'*_Configuration.dat')
    if outPath:
        table = bolt.Table(bolt.PickleDict(outPath))
        table.setItem(bolt.GPath(u'Saved Bashed Patch Configuration (%s)' % (
            [u'Python', u'CBash'][isCBash])), 'bash.patch.configs', config)
        table.save()

def getPatchesPath(fileName):
    """Choose the correct Bash Patches path for the file."""
    if bass.dirs['patches'].join(fileName).isfile():
        return bass.dirs['patches'].join(fileName)
    else:
        return bass.dirs['defaultPatches'].join(fileName)

def getPatchesList():
    """Get a basic list of potential Bash Patches."""
    return set(bass.dirs['patches'].list()) | set(
        bass.dirs['defaultPatches'].list())
