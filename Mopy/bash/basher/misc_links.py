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
#  Wrye Bash copyright (C) 2005-2009 Wrye, 2010-2014 Wrye Bash Team
#  https://github.com/wrye-bash
#
# =============================================================================

import re
import time
from ..balt import EnabledLink, AppendableLink, ItemLink, Link, RadioLink, \
    ChoiceLink, MenuLink, CheckLink, Image
from .. import balt, bosh, bush
from .import People_Link
from .constants import ID_GROUPS, settingDefaults
from ..bolt import GPath, LString

__all__ = ['List_Columns', 'Master_ChangeTo', 'Master_Disable',
           'Screens_NextScreenShot', 'Screen_JpgQuality',
           'Screen_JpgQualityCustom', 'Screen_Rename', 'Screen_ConvertTo',
           'Messages_Archive_Import', 'Message_Delete', 'People_AddNew',
           'People_Import', 'People_Karma', 'People_Export']

# Screen Links ----------------------------------------------------------------
#------------------------------------------------------------------------------
class Screens_NextScreenShot(ItemLink):
    """Sets screenshot base name and number."""
    text = _(u'Next Shot...')
    help = _(u'Set screenshot base name and number')

    def Execute(self,event):
        oblivionIni = bosh.oblivionIni
        base = oblivionIni.getSetting(u'Display', u'sScreenShotBaseName',
                                      u'ScreenShot')
        next_ = oblivionIni.getSetting(u'Display',u'iScreenShotIndex',u'0')
        rePattern = re.compile(ur'^(.+?)(\d*)$',re.I|re.U)
        pattern = balt.askText(self.window,(
            _(u"Screenshot base name, optionally with next screenshot number.")
            + u'\n' +
            _(u"E.g. ScreenShot or ScreenShot_101 or Subdir\\ScreenShot_201.")
            ),_(u"Next Shot..."),base+next_)
        if not pattern: return
        maPattern = rePattern.match(pattern)
        newBase,newNext = maPattern.groups()
        settings = {LString(u'Display'):{
            LString(u'SScreenShotBaseName'): newBase,
            LString(u'iScreenShotIndex'): (newNext or next_),
            LString(u'bAllowScreenShot'): u'1',
            }}
        screensDir = GPath(newBase).head
        if screensDir:
            if not screensDir.isabs(): screensDir = bosh.dirs['app'].join(
                screensDir)
            screensDir.makedirs()
        oblivionIni.saveSettings(settings)
        bosh.screensData.refresh()
        self.window.RefreshUI()

#------------------------------------------------------------------------------
class Screen_ConvertTo(EnabledLink):
    """Converts selected images to another type."""
    help = _(u'Convert selected images to another format')

    def __init__(self,ext,imageType):
        super(Screen_ConvertTo, self).__init__()
        self.ext = ext.lower()
        self.imageType = imageType
        self.text = _(u'Convert to %s') % self.ext

    def _enable(self):
        convertable = [name_ for name_ in self.selected if
                       GPath(name_).cext != u'.' + self.ext]
        return len(convertable) > 0

    def Execute(self,event):
        srcDir = bosh.screensData.dir
        try:
            with balt.Progress(_(u"Converting to %s") % self.ext) as progress:
                progress.setFull(len(self.selected))
                for index,fileName in enumerate(self.selected):
                    progress(index,fileName.s)
                    srcPath = srcDir.join(fileName)
                    destPath = srcPath.root+u'.'+self.ext
                    if srcPath == destPath or destPath.exists(): continue
                    bitmap = Image.Load(srcPath, quality=bosh.settings[
                        'bash.screens.jpgQuality'])
                    result = bitmap.SaveFile(destPath.s,self.imageType)
                    if not result: continue
                    srcPath.remove()
        finally:
            self.window.data.refresh()
            self.window.RefreshUI()

#------------------------------------------------------------------------------
class Screen_JpgQuality(RadioLink):
    """Sets JPEG quality for saving."""
    help = _(u'Sets JPEG quality for saving')

    def __init__(self, quality):
        super(Screen_JpgQuality, self).__init__()
        self.quality = quality
        self.text = u'%i' % self.quality

    def _check(self):
        return self.quality == bosh.settings['bash.screens.jpgQuality']

    def Execute(self,event):
        bosh.settings['bash.screens.jpgQuality'] = self.quality

#------------------------------------------------------------------------------
class Screen_JpgQualityCustom(Screen_JpgQuality):
    """Sets a custom JPG quality."""
    def __init__(self):
        super(Screen_JpgQualityCustom, self).__init__(
            bosh.settings['bash.screens.jpgCustomQuality'])
        self.text = _(u'Custom [%i]') % self.quality

    def Execute(self,event):
        quality = balt.askNumber(self.window, _(u'JPEG Quality'),
                                 value=self.quality, min=0, max=100)
        if quality is None: return
        self.quality = quality
        bosh.settings['bash.screens.jpgCustomQuality'] = self.quality
        self.text = _(u'Custom [%i]') % quality
        Screen_JpgQuality.Execute(self,event)

#------------------------------------------------------------------------------
class Screen_Rename(EnabledLink):
    """Renames files by pattern."""
    text = _(u'Rename...')
    help = _(u'Renames files by pattern')

    def _enable(self): return len(self.selected) > 0

    def Execute(self,event): self.window.Rename(selected=self.selected)

# Messages Links --------------------------------------------------------------
#------------------------------------------------------------------------------
class Messages_Archive_Import(ItemLink):
    """Import messages from html message archive."""
    text = _(u'Import Archives...')
    help = _(u'Import messages from html message archive')

    def Execute(self,event):
        textDir = bosh.settings.get('bash.workDir',bosh.dirs['app'])
        #--File dialog
        paths = balt.askOpenMulti(self.window,_(u'Import message archive(s):'),
                                  textDir, u'', u'*.html')
        if not paths: return
        bosh.settings['bash.workDir'] = paths[0].head
        for path in paths:
            bosh.messages.importArchive(path)
        self.window.RefreshUI()

#------------------------------------------------------------------------------
class Message_Delete(ItemLink):
    """Delete the file and all backups."""
    text = _(u'Delete')
    help = _(u'Permanently delete messages')

    def Execute(self,event):
        message = _(u'Delete these %d message(s)? This operation cannot'
                    u' be undone.') % len(self.selected)
        if not balt.askYes(self.window,message,_(u'Delete Messages')):
            return
        #--Do it
        for message in self.selected:
            self.window.data.delete(message)
        #--Refresh stuff
        self.window.RefreshUI()

# People Links ----------------------------------------------------------------
#------------------------------------------------------------------------------
class People_AddNew(People_Link):
    """Add a new record."""
    dialogTitle = _(u'Add New Person')
    text = _(u'Add...')
    help = _(u'Add a new record')

    def Execute(self,event):
        name = balt.askText(self.gTank,_(u"Add new person:"),self.dialogTitle)
        if not name: return
        if name in self.pdata:
            return balt.showInfo(self.gTank, name + _(u" already exists."),
                                 self.dialogTitle)
        self.pdata[name] = (time.time(),0,u'')
        self.gTank.RefreshUI(details=name) ##: select it !
        self.gTank.gList.EnsureVisible(self.gTank.GetIndex(name))
        self.pdata.setChanged()

#------------------------------------------------------------------------------
class People_Export(People_Link):
    """Export people to text archive."""
    dialogTitle = _(u"Export People")
    text = _(u'Export...')
    help = _(u'Export people to text archive')

    def Execute(self,event):
        textDir = bosh.settings.get('bash.workDir',bosh.dirs['app'])
        #--File dialog
        path = balt.askSave(self.gTank, _(u'Export people to text file:'),
                            textDir, u'People.txt', u'*.txt')
        if not path: return
        bosh.settings['bash.workDir'] = path.head
        self.pdata.dumpText(path,self.selected)
        balt.showInfo(self.gTank,
                      _(u'Records exported: %d.') % len(self.selected),
                      self.dialogTitle)

#------------------------------------------------------------------------------
class People_Import(People_Link):
    """Import people from text archive."""
    dialogTitle = _(u"Import People")
    text = _(u'Import...')
    help = _(u'Import people from text archive')

    def Execute(self,event):
        textDir = bosh.settings.get('bash.workDir',bosh.dirs['app'])
        #--File dialog
        path = balt.askOpen(self.gTank, _(u'Import people from text file:'),
                            textDir, u'', u'*.txt', mustExist=True)
        if not path: return
        bosh.settings['bash.workDir'] = path.head
        newNames = self.pdata.loadText(path)
        balt.showInfo(self.gTank, _(u"People imported: %d") % len(newNames),
                      self.dialogTitle)
        self.gTank.RefreshUI()

#------------------------------------------------------------------------------
class People_Karma(People_Link, ChoiceLink):
    """Add Karma setting links."""
    text = _(u'Karma')
    idList = ID_GROUPS
    labels = [u'%+d' % x for x in xrange(5, -6, -1)]

    @property
    def items(self): return self.__class__.labels

    def DoList(self,event):
        """Handle selection of label."""
        idList = ID_GROUPS
        karma = range(5,-6,-1)[event.GetId()-idList.BASE]
        for item in self.selected:
            text = self.pdata[item][2]
            self.pdata[item] = (time.time(),karma,text)
        self.gTank.RefreshUI()
        self.pdata.setChanged()

# Masters Links ---------------------------------------------------------------
#------------------------------------------------------------------------------
class Master_ChangeTo(EnabledLink):
    """Rename/replace master through file dialog."""
    text = _(u"Change to...")
    help = _(u"Rename/replace master through file dialog")

    def _enable(self): return self.window.edited

    def Execute(self,event):
        itemId = self.selected[0]
        masterInfo = self.window.data[itemId]
        masterName = masterInfo.name
        #--File Dialog
        wildcard = _(u'%s Mod Files') % bush.game.displayName \
                   + u' (*.esp;*.esm)|*.esp;*.esm'
        newPath = balt.askOpen(self.window,_(u'Change master name to:'),
            bosh.modInfos.dir, masterName, wildcard,mustExist=True)
        if not newPath: return
        (newDir,newName) = newPath.headTail
        #--Valid directory?
        if newDir != bosh.modInfos.dir:
            balt.showError(self.window,
               _(u"File must be selected from Oblivion Data Files directory."))
            return
        elif newName == masterName:
            return
        #--Save Name
        masterInfo.setName(newName)
        self.window.ReList()
        self.window.PopulateItems()
        bosh.settings.getChanged('bash.mods.renames')[masterName] = newName

#------------------------------------------------------------------------------
class Master_Disable(AppendableLink, EnabledLink):
    """Rename/replace master through file dialog."""
    text = _(u"Disable")
    help = _(u"Disable master")

    def _append(self, window): return not window.fileInfo.isMod() #--Saves only

    def _enable(self): return self.window.edited

    def Execute(self,event):
        itemId = self.selected[0]
        masterInfo = self.window.data[itemId]
        masterName = masterInfo.name
        newName = GPath(re.sub(u'[mM]$','p',u'XX'+masterName.s))
        #--Save Name
        masterInfo.setName(newName)
        self.window.ReList()
        self.window.PopulateItems()

# Column menu -----------------------------------------------------------------
#------------------------------------------------------------------------------
class List_Columns(MenuLink):
    """Customize visible columns."""
    text = _(u"Columns")

    def __init__(self, columnsKey, allColumnsKey, persistentColumns):
        super(List_Columns, self).__init__(self.__class__.text)
        self.columnsKey = columnsKey
        self.allColumnsKey = allColumnsKey
        for col in settingDefaults[self.allColumnsKey]:
            enable = col not in persistentColumns
            self.links.append(
                List_Column(self.columnsKey, self.allColumnsKey, col, enable))

class List_Column(CheckLink, EnabledLink):

    def __init__(self,columnsKey,allColumnsKey,colName,enable=True):
        super(List_Column, self).__init__()
        self.colName = colName
        self.columnsKey = columnsKey
        self.allColumnsKey = allColumnsKey
        self.enable = enable
        self.text = bosh.settings['bash.colNames'][self.colName]
        self.help = _(u"Show/Hide '%s' column.") % self.text

    def _enable(self): return self.enable

    def _check(self): return self.colName in bosh.settings[self.columnsKey]

    def Execute(self,event):
        if self.colName in bosh.settings[self.columnsKey]:
            bosh.settings[self.columnsKey].remove(self.colName)
            bosh.settings.setChanged(self.columnsKey)
        else:
            #--Ensure the same order each time
            bosh.settings[self.columnsKey] = [
                x for x in settingDefaults[self.allColumnsKey]
                if x in bosh.settings[self.columnsKey] or x == self.colName]
        self.window.PopulateColumns()
        self.window.RefreshUI()
