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
#  Wrye Bash copyright (C) 2005-2009 Wrye, 2010-2020 Wrye Bash Team
#  https://github.com/wrye-bash
#
# =============================================================================
from .. import balt, bolt, bass

class PatcherInfo(object): ##: clazz is unused?
    __slots__ = (u'clazz', u'twin_patcher', u'cls_vars', u'cls_csv_key')

    def __init__(self, clazz, twin_patcher, cls_vars, cls_csv_key=u''):
        self.clazz = clazz
        self.twin_patcher = twin_patcher
        self.cls_vars = cls_vars
        self.cls_csv_key = cls_csv_key

def configIsCBash(patchConfigs): ##: belongs to basher but used also in bosh
    for config_key in patchConfigs:
        if 'CBash' in config_key:
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
        table = bolt.DataTable(bolt.PickleDict(outPath))
        table.setItem(bolt.GPath(u'Saved Bashed Patch Configuration (%s)' % (
            [u'Python', u'CBash'][isCBash])), 'bash.patch.configs', config)
        table.save()

def getPatchesPath(fileName):
    """Choose the correct Bash Patches path for the file."""
    if bass.dirs[u'patches'].join(fileName).isfile():
        return bass.dirs[u'patches'].join(fileName)
    else:
        return bass.dirs[u'defaultPatches'].join(fileName)

def getPatchesList():
    """Get a basic list of potential Bash Patches."""
    return set(bass.dirs[u'patches'].list()) | set(
        bass.dirs[u'defaultPatches'].list())

# this is set once and stays the same for the patch execution session
_patches_set = None

def list_patches_dir():
    global _patches_set
    _patches_set = getPatchesList()

def patches_set():
    if _patches_set is None: list_patches_dir()
    return _patches_set
