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
import wx
from ..balt import EnabledLink, AppendableLink, _Link, Link, RadioLink, \
    ChoiceLink, MenuLink, CheckLink
from .. import balt, bosh, bush
from .constants import ID_GROUPS, settingDefaults, tabInfo
from ..bolt import GPath, LString

# Screen Links ----------------------------------------------------------------
#------------------------------------------------------------------------------
class Screens_NextScreenShot(_Link):
    """Sets screenshot base name and number."""
    text = _(u'Next Shot...')
    help = _(u'Set screenshot base name and number')

    def Execute(self,event):
        oblivionIni = bosh.oblivionIni
        base = oblivionIni.getSetting(u'Display',u'sScreenShotBaseName',u'ScreenShot')
        next = oblivionIni.getSetting(u'Display',u'iScreenShotIndex',u'0')
        rePattern = re.compile(ur'^(.+?)(\d*)$',re.I|re.U)
        pattern = balt.askText(self.window,(_(u"Screenshot base name, optionally with next screenshot number.")
                                            + u'\n' +
                                            _(u"E.g. ScreenShot or ScreenShot_101 or Subdir\\ScreenShot_201.")
                                            ),_(u"Next Shot..."),base+next)
        if not pattern: return
        maPattern = rePattern.match(pattern)
        newBase,newNext = maPattern.groups()
        settings = {LString(u'Display'):{
            LString(u'SScreenShotBaseName'): newBase,
            LString(u'iScreenShotIndex'): (newNext or next),
            LString(u'bAllowScreenShot'): u'1',
            }}
        screensDir = GPath(newBase).head
        if screensDir:
            if not screensDir.isabs(): screensDir = bosh.dirs['app'].join(screensDir)
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
        convertable = [name_ for name_ in self.data if
                       GPath(name_).cext != u'.' + self.ext]
        return len(convertable) > 0

    def Execute(self,event):
        srcDir = bosh.screensData.dir
        try:
            with balt.Progress(_(u"Converting to %s") % self.ext) as progress:
                progress.setFull(len(self.data))
                for index,fileName in enumerate(self.data):
                    progress(index,fileName.s)
                    srcPath = srcDir.join(fileName)
                    destPath = srcPath.root+u'.'+self.ext
                    if srcPath == destPath or destPath.exists(): continue
                    bitmap = wx.Image(srcPath.s)
                    # This only has an effect on jpegs, so it's ok to do it on every kind
                    bitmap.SetOptionInt(wx.IMAGE_OPTION_QUALITY,bosh.settings['bash.screens.jpgQuality'])
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

    def __init__(self,quality):
        Link.__init__(self)
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
        Screen_JpgQuality.__init__(self,bosh.settings['bash.screens.jpgCustomQuality'])
        self.text = _(u'Custom [%i]') % self.quality

    def Execute(self,event):
        quality = balt.askNumber(self.window,_(u'JPEG Quality'),value=self.quality,min=0,max=100)
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

    def _enable(self): return len(self.data) > 0

    def Execute(self,event):
        if len(self.data) > 0:
            index = self.window.list.FindItem(0,self.data[0].s)
            if index != -1:
                self.window.list.EditLabel(index)

# Messages Links --------------------------------------------------------------
#------------------------------------------------------------------------------
class Messages_Archive_Import(_Link):
    """Import messages from html message archive."""
    text = _(u'Import Archives...')
    help = _(u'Import messages from html message archive')

    def Execute(self,event):
        textDir = bosh.settings.get('bash.workDir',bosh.dirs['app'])
        #--File dialog
        paths = balt.askOpenMulti(self.window,_(u'Import message archive(s):'),textDir,
            u'', u'*.html')
        if not paths: return
        bosh.settings['bash.workDir'] = paths[0].head
        for path in paths:
            bosh.messages.importArchive(path)
        self.window.RefreshUI()

#------------------------------------------------------------------------------
class Message_Delete(_Link):
    """Delete the file and all backups."""
    text = _(u'Delete')
    help = _(u'Permanently delete messages')

    def Execute(self,event):
        message = _(u'Delete these %d message(s)? This operation cannot be undone.') % len(self.data)
        if not balt.askYes(self.window,message,_(u'Delete Messages')):
            return
        #--Do it
        for message in self.data:
            self.window.data.delete(message)
        #--Refresh stuff
        self.window.RefreshUI()

# People Links ----------------------------------------------------------------
#------------------------------------------------------------------------------
class People_AddNew(_Link):
    """Add a new record."""
    dialogTitle = _(u'Add New Person')
    text = _(u'Add...')
    help = _(u'Add a new record')

    def Execute(self,event):
        name = balt.askText(self.gTank,_(u"Add new person:"),self.dialogTitle)
        if not name: return
        if name in self.data:
            return balt.showInfo(self.gTank,name+_(u" already exists."),self.dialogTitle)
        self.data[name] = (time.time(),0,u'')
        self.gTank.RefreshUI(details=name)
        self.gTank.gList.EnsureVisible(self.gTank.GetIndex(name))
        self.data.setChanged()

#------------------------------------------------------------------------------
class People_Export(_Link):
    """Export people to text archive."""
    dialogTitle = _(u"Export People")
    text = _(u'Export...')
    help = _(u'Export people to text archive')

    def Execute(self,event):
        textDir = bosh.settings.get('bash.workDir',bosh.dirs['app'])
        #--File dialog
        path = balt.askSave(self.gTank,_(u'Export people to text file:'),textDir,
            u'People.txt', u'*.txt')
        if not path: return
        bosh.settings['bash.workDir'] = path.head
        self.data.dumpText(path,self.selected)
        balt.showInfo(self.gTank,_(u'Records exported: %d.') % len(self.selected),self.dialogTitle)

#------------------------------------------------------------------------------
class People_Import(_Link):
    """Import people from text archive."""
    dialogTitle = _(u"Import People")
    text = _(u'Import...')
    help = _(u'Import people from text archive')

    def Execute(self,event):
        textDir = bosh.settings.get('bash.workDir',bosh.dirs['app'])
        #--File dialog
        path = balt.askOpen(self.gTank,_(u'Import people from text file:'),textDir,
            u'', u'*.txt',mustExist=True)
        if not path: return
        bosh.settings['bash.workDir'] = path.head
        newNames = self.data.loadText(path)
        balt.showInfo(self.gTank,_(u"People imported: %d") % len(newNames),self.dialogTitle)
        self.gTank.RefreshUI()

#------------------------------------------------------------------------------
class People_Karma(ChoiceLink):
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
            text = self.data[item][2]
            self.data[item] = (time.time(),karma,text)
        self.gTank.RefreshUI()
        self.data.setChanged()

# Masters Links ---------------------------------------------------------------
#------------------------------------------------------------------------------
class Master_ChangeTo(EnabledLink):
    """Rename/replace master through file dialog."""
    text = _(u"Change to...")
    help = _(u"Rename/replace master through file dialog")

    def _enable(self): return self.window.edited

    def Execute(self,event):
        itemId = self.data[0]
        masterInfo = self.window.data[itemId]
        masterName = masterInfo.name
        #--File Dialog
        wildcard = _(u'%s Mod Files')%bush.game.displayName+u' (*.esp;*.esm)|*.esp;*.esm'
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
        itemId = self.data[0]
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

    def __init__(self,columnsKey,allColumnsKey,persistantColumns=()):
        super(List_Columns, self).__init__(self.__class__.text)
        self.columnsKey = columnsKey
        self.allColumnsKey = allColumnsKey
        self.persistant = persistantColumns
        for col in settingDefaults[self.allColumnsKey]:
            enable = col not in self.persistant
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

# Tabs menu -------------------------------------------------------------------
#------------------------------------------------------------------------------
class Tab_Link(AppendableLink, CheckLink, EnabledLink):
    """Handle hiding/unhiding tabs."""
    def __init__(self,tabKey,canDisable=True):
        super(Tab_Link, self).__init__()
        self.tabKey = tabKey
        self.enabled = canDisable
        className, self.text, item = tabInfo.get(self.tabKey,[None,None,None])
        self.help = _(u"Show/Hide the %(tabtitle)s Tab.") % (
            {'tabtitle': self.text})

    def _append(self, window): return self.text is not None

    def _enable(self): return self.enabled

    def _check(self): return bosh.settings['bash.tabs'][self.tabKey]

    def Execute(self,event):
        if bosh.settings['bash.tabs'][self.tabKey]:
            # It was enabled, disable it.
            iMods = None
            iInstallers = None
            iDelete = None
            for i in range(Link.Frame.notebook.GetPageCount()):
                pageTitle = Link.Frame.notebook.GetPageText(i)
                if pageTitle == tabInfo['Mods'][1]:
                    iMods = i
                elif pageTitle == tabInfo['Installers'][1]:
                    iInstallers = i
                if pageTitle == tabInfo[self.tabKey][1]:
                    iDelete = i
            if iDelete == Link.Frame.notebook.GetSelection():
                # We're deleting the current page...
                if ((iDelete == 0 and iInstallers == 1) or
                        (iDelete - 1 == iInstallers)):
                    # The auto-page change will change to
                    # the 'Installers' tab.  Change to the
                    # 'Mods' tab instead.
                    Link.Frame.notebook.SetSelection(iMods)
            page = Link.Frame.notebook.GetPage(iDelete)
            Link.Frame.notebook.RemovePage(iDelete)
            page.Show(False)
        else:
            # It was disabled, enable it
            insertAt = 0
            for i,key in enumerate(bosh.settings['bash.tabs.order']):
                if key == self.tabKey: break
                if bosh.settings['bash.tabs'][key]:
                    insertAt = i+1
            className,title,panel = tabInfo[self.tabKey]
            if not panel:
                # FIXME(ut): ugly as hell - use tabInfo somehow
                from . import BSAPanel, INIPanel, InstallersPanel, \
                    MessagePanel, PeoplePanel, SavePanel, ScreensPanel
                panel = locals()[className](Link.Frame.notebook)
                tabInfo[self.tabKey][2] = panel
            if insertAt > Link.Frame.notebook.GetPageCount():
                Link.Frame.notebook.AddPage(panel,title)
            else:
                Link.Frame.notebook.InsertPage(insertAt,panel,title)
        bosh.settings['bash.tabs'][self.tabKey] ^= True
        bosh.settings.setChanged('bash.tabs')
