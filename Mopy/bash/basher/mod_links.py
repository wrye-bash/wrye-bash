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
from .. import bosh, bolt, balt, bush
import StringIO
import os
import wx
from ..balt import _Link, Link, textCtrl, toggleButton, vSizer, staticText, \
    spacer, hSizer, button
from ..bolt import deprint, GPath, SubProgress, AbstractError
from . import bashBlue, EnabledLink, ListBoxes, ID_GROUPS, Mod_BaloGroups_Edit, \
    CheckLink, refreshData
from ..bosh import formatDate, formatInteger
from ..cint import ObCollection, CBash # TODO(ut): CBash...should be in bosh

modList = None
# Mod Links -------------------------------------------------------------------
#------------------------------------------------------------------------------

class _Mod_Export_Link(EnabledLink):

    def _enable(self): return bool(self.data)

    def Execute(self, event):
        fileName = GPath(self.data[0])
        fileInfo = bosh.modInfos[fileName] # TODO(ut): UNUSED
        textName = fileName.root + self.__class__.csvFile
        textDir = bosh.dirs['patches']
        textDir.makedirs()
        #--File dialog
        textPath = balt.askSave(self.window, self.__class__.askTitle, textDir,
                                textName, u'*' + self.__class__.csvFile)
        if not textPath: return
        (textDir, textName) = textPath.headTail
        #--Export
        with balt.Progress(self.__class__.progressTitle) as progress:
            parser = self._parser()
            readProgress = SubProgress(progress, 0.1, 0.8)
            readProgress.setFull(len(self.data))
            for index, fileName in enumerate(map(GPath, self.data)):
                fileInfo = bosh.modInfos[fileName]
                readProgress(index, _(u'Reading') + u' ' + fileName.s + u'.')
                parser.readFromMod(fileInfo)
            progress(0.8, _(u'Exporting to') + u' ' + textName.s + u'.')
            parser.writeToText(textPath)
            progress(1.0, _(u'Done.'))

    def _parser(self): raise AbstractError # TODO(ut): class attribute ? initialised once...

class _Mod_Import_Link(EnabledLink):

    def _enable(self): return len(self.data) == 1

#------------------------------------------------------------------------------
from ..patcher.utilities import ActorLevels, CBash_ActorLevels

class Mod_ActorLevels_Export(_Mod_Export_Link):
    """Export actor levels from mod to text file."""
    text = _(u'NPC Levels...')
    help = _(u"Export NPC level info from mod to text file.")

    def _parser(self): return CBash_ActorLevels() if CBash else  ActorLevels()

    def Execute(self,event): # overrides _Mod_Export_Link
        message = (_(u'This command will export the level info for NPCs whose level is offset with respect to the PC.  The exported file can be edited with most spreadsheet programs and then reimported.')
                   + u'\n\n' +
                   _(u'See the Bash help file for more info.'))
        if not balt.askContinue(self.window,message,
                'bash.actorLevels.export.continue',
                _(u'Export NPC Levels')):
            return
        fileName = GPath(self.data[0])
        fileInfo = bosh.modInfos[fileName]
        textName = fileName.root+u'_NPC_Levels.csv'
        textDir = bosh.dirs['patches']
        textDir.makedirs()
        #--File dialog
        textPath = balt.askSave(self.window,_(u'Export NPC levels to:'),textDir,
                                textName, u'*_NPC_Levels.csv')
        if not textPath: return
        (textDir,textName) = textPath.headTail
        #--Export
        with balt.Progress(_(u'Export NPC levels')) as progress:
            actorLevels = self._parser()
            readProgress = SubProgress(progress,0.1,0.8)
            readProgress.setFull(len(self.data))
            for index,fileName in enumerate(map(GPath,self.data)):
                fileInfo = bosh.modInfos[fileName]
                readProgress(index,_(u'Reading')+u' '+fileName.s)
                actorLevels.readFromMod(fileInfo)
            progress(0.8,_(u'Exporting to')+u' '+textName.s+u'.')
            actorLevels.writeToText(textPath)
            progress(1.0,_(u'Done.'))

#------------------------------------------------------------------------------
class Mod_ActorLevels_Import(_Mod_Import_Link):
    """Imports actor levels from text file to mod."""
    text = _(u'NPC Levels...')
    help = _(u"Import NPC level info from text file to mod")

    def _parser(self): return CBash_ActorLevels() if CBash else  ActorLevels()

    def Execute(self,event):
        message = (_(u'This command will import NPC level info from a previously exported file.')
                   + u'\n\n' +
                   _(u'See the Bash help file for more info.'))
        if not balt.askContinue(self.window,message,
                'bash.actorLevels.import.continue',
                _(u'Import NPC Levels')):
            return
        fileName = GPath(self.data[0])
        fileInfo = bosh.modInfos[fileName]
        textName = fileName.root+u'_NPC_Levels.csv'
        textDir = bosh.dirs['patches']
        #--File dialog
        textPath = balt.askOpen(self.window,_(u'Import NPC levels from:'),
            textDir,textName,u'*_NPC_Levels.csv',mustExist=True)
        if not textPath: return
        (textDir,textName) = textPath.headTail
        #--Extension error check
        ext = textName.cext
        if ext != u'.csv':
            balt.showError(self.window,_(u'Source file must be a _NPC_Levels.csv file.'))
            return
        #--Export
        changed = None
        with balt.Progress(_(u'Import NPC Levels')) as progress:
            actorLevels = self._parser()
            progress(0.1,_(u'Reading')+u' '+textName.s+u'.')
            actorLevels.readFromText(textPath)
            progress(0.2,_(u'Applying to')+u' '+fileName.s+u'.')
            changed = actorLevels.writeToMod(fileInfo)
            progress(1.0,_(u'Done.'))
        #--Log
        if not changed:
            balt.showOk(self.window,_(u'No relevant NPC levels to import.'),
                        _(u'Import NPC Levels'))
        else:
            buff = StringIO.StringIO()
            buff.write(u'* %03d  %s\n' % (changed, fileName.s))
            balt.showLog(self.window,buff.getvalue(),_(u'Import NPC Levels'),
                         icons=bashBlue)

#------------------------------------------------------------------------------
class MasterList_AddMasters(_Link):
    """Adds a master."""
    text = _(u'Add Masters...')
    help = _(u'Adds specified master to list of masters')

    def Execute(self,event):
        message = _(u"WARNING!  For advanced modders only!  Adds specified master to list of masters, thus ceding ownership of new content of this mod to the new master.  Useful for splitting mods into esm/esp pairs.")
        if not balt.askContinue(self.window,message,'bash.addMaster.continue',_(u'Add Masters')):
            return
        modInfo = self.window.fileInfo
        wildcard = bush.game.displayName+u' '+_(u'Masters')+u' (*.esm;*.esp)|*.esm;*.esp'
        masterPaths = balt.askOpenMulti(self.window,_(u'Add masters:'),
                        modInfo.dir, u'', wildcard)
        if not masterPaths: return
        names = []
        for masterPath in masterPaths:
            (dir,name) = masterPath.headTail
            if dir != modInfo.dir:
                return balt.showError(self.window,
                    _(u"File must be selected from %s Data Files directory.")
                    % bush.game.fsName)
            if name in modInfo.header.masters:
                return balt.showError(self.window,
                    name.s+u' '+_(u"is already a master."))
            names.append(name)
        for masterName in bosh.modInfos.getOrdered(names, asTuple=False):
            if masterName in bosh.modInfos:
                masterName = bosh.modInfos[masterName].name
            modInfo.header.masters.append(masterName)
        modInfo.header.changed = True
        self.window.SetFileInfo(modInfo)
        self.window.InitEdit()

#------------------------------------------------------------------------------
class MasterList_CleanMasters(_Link):
    """Remove unneeded masters."""
    text, help = _(u'Clean Masters...'), _(u'Remove unneeded masters')

    def AppendToMenu(self,menu,window,data):
        if not bosh.settings['bash.CBashEnabled']: return
        _Link.AppendToMenu(self,menu,window,data)

    def Execute(self,event):
        message = _(u"WARNING!  For advanced modders only!  Removes masters that are not referenced in any records.")
        if not balt.askContinue(self.window,message,'bash.cleanMaster.continue',
                                _(u'Clean Masters')):
            return
        modInfo = self.window.fileInfo
        path = modInfo.getPath()

        with ObCollection(ModsPath=bosh.dirs['mods'].s) as Current:
            modFile = Current.addMod(path.stail)
            Current.load()
            oldMasters = modFile.TES4.masters
            cleaned = modFile.CleanMasters()

            if cleaned:
                newMasters = modFile.TES4.masters
                removed = [GPath(x) for x in oldMasters if x not in newMasters]
                removeKey = _(u'Masters')
                group = [removeKey,
                              _(u'These master files are not referenced within the mod, and can safely be removed.'),
                              ]
                group.extend(removed)
                checklists = [group]
                from . import bashFrame # FIXME
                dialog = ListBoxes(bashFrame,_(u'Remove these masters?'),
                                        _(u'The following master files can be safely removed.'),
                                        checklists)
                if dialog.ShowModal() == ListBoxes.ID_CANCEL:
                    dialog.Destroy()
                    return
                id = dialog.ids[removeKey]
                checks = dialog.FindWindowById(id)
                if checks:
                    for i,mod in enumerate(removed):
                        if not checks.IsChecked(i):
                            newMasters.append(mod)

                modFile.TES4.masters = newMasters
                modFile.save()
                dialog.Destroy()
                deprint(u'to remove:', removed)
            else:
                balt.showOk(self.window,_(u'No Masters to clean.'),
                            _(u'Clean Masters'))

#------------------------------------------------------------------------------
class Mod_FullLoad(EnabledLink):
    """Tests all record definitions against a specific mod"""
    text = _(u'Test Full Record Definitions...')

    def _enable(self): return len(self.data) == 1

    def Execute(self,event):
        fileName = GPath(self.data[0])
        with balt.Progress(_(u'Loading:')+u'\n%s'%fileName.stail) as progress:
            print bosh.MreRecord.type_class
            readClasses = bosh.MreRecord.type_class
            print readClasses.values()
            loadFactory = bosh.LoadFactory(False, *readClasses.values())
            modFile = bosh.ModFile(bosh.modInfos[fileName],loadFactory)
            try:
                modFile.load(True,progress)
            except:
                deprint('exception:\n', traceback=True)

#------------------------------------------------------------------------------
class Mod_AddMaster(EnabledLink):
    """Adds master."""
    text = _(u'Add Master...')

    def _enable(self): return len(self.data) == 1

    def Execute(self,event):
        message = _(u"WARNING! For advanced modders only! Adds specified master to list of masters, thus ceding ownership of new content of this mod to the new master. Useful for splitting mods into esm/esp pairs.")
        if not balt.askContinue(self.window,message,'bash.addMaster.continue',_(u'Add Master')):
            return
        fileName = GPath(self.data[0])
        fileInfo = self.window.data[fileName]
        wildcard = _(u'%s Masters')%bush.game.displayName+u' (*.esm;*.esp)|*.esm;*.esp'
        masterPaths = balt.askOpenMulti(self.window,_(u'Add master:'),fileInfo.dir, u'', wildcard)
        if not masterPaths: return
        names = []
        for masterPath in masterPaths:
            (dir,name) = masterPath.headTail
            if dir != fileInfo.dir:
                return balt.showError(self.window,
                    _(u"File must be selected from %s Data Files directory.") % bush.game.fsName)
            if name in fileInfo.header.masters:
                return balt.showError(self.window,_(u"%s is already a master!") % name.s)
            names.append(name)
        # actually do the modification
        for masterName in bosh.modInfos.getOrdered(names, asTuple=False):
            if masterName in bosh.modInfos:
                #--Avoid capitalization errors by getting the actual name from modinfos.
                masterName = bosh.modInfos[masterName].name
            fileInfo.header.masters.append(masterName)
        fileInfo.header.changed = True
        fileInfo.writeHeader()
        bosh.modInfos.refreshFile(fileInfo.name)
        self.window.RefreshUI()

#------------------------------------------------------------------------------
class Mod_BaloGroups:
    """Select Balo group to use."""
    def __init__(self):
        """Initialize."""
        self.id_group = {}
        self.idList = ID_GROUPS

    def GetItems(self):
        items = self.labels[:]
        items.sort(key=lambda a: a.lower())
        return items

    def AppendToMenu(self,menu,window,data):
        """Append label list to menu."""
        if not bosh.settings.get('bash.balo.full'): return
        self.window = window
        self.data = data
        id_group = self.id_group
        menu.Append(self.idList.EDIT,_(u'Edit...'))
        setableMods = [GPath(x) for x in self.data if GPath(x) not in bosh.modInfos.autoHeaders]
        if setableMods:
            menu.AppendSeparator()
            ids = iter(self.idList)
            if len(setableMods) == 1:
                modGroup = bosh.modInfos.table.getItem(setableMods[0],'group')
            else:
                modGroup = None
            for group,lower,upper in bosh.modInfos.getBaloGroups():
                if lower == upper:
                    id = ids.next()
                    id_group[id] = group
                    menu.AppendCheckItem(id,group)
                    menu.Check(id,group == modGroup)
                else:
                    subMenu = wx.Menu()
                    for x in range(lower,upper+1):
                        offGroup = bosh.joinModGroup(group,x)
                        id = ids.next()
                        id_group[id] = offGroup
                        subMenu.AppendCheckItem(id,offGroup)
                        subMenu.Check(id,offGroup == modGroup)
                    menu.AppendMenu(-1,group,subMenu)
        #--Events
        from . import bashFrame # FIXME
        wx.EVT_MENU(bashFrame,self.idList.EDIT,self.DoEdit)
        wx.EVT_MENU_RANGE(bashFrame,self.idList.BASE,self.idList.MAX,self.DoList)

    def DoList(self,event):
        """Handle selection of label."""
        label = self.id_group[event.GetId()]
        mod_group = bosh.modInfos.table.getColumn('group')
        for mod in self.data:
            if mod not in bosh.modInfos.autoHeaders:
                mod_group[mod] = label
        if bosh.modInfos.refresh(doInfos=False):
            modList.SortItems()
        self.window.RefreshUI()

    def DoEdit(self,event):
        """Show label editing dialog."""
        dialog = Mod_BaloGroups_Edit(self.window)
        dialog.ShowModal()
        dialog.Destroy()

#------------------------------------------------------------------------------
class Mod_AllowAllGhosting(_Link):
    text, help = _(u"Allow Ghosting"), u''

    def Execute(self,event):
        files = []
        for fileName in self.data:
            fileInfo = bosh.modInfos[fileName]
            allowGhosting = True
            bosh.modInfos.table.setItem(fileName,'allowGhosting',allowGhosting)
            toGhost = fileName not in bosh.modInfos.ordered
            oldGhost = fileInfo.isGhost
            if fileInfo.setGhost(toGhost) != oldGhost:
                files.append(fileName)
        self.window.RefreshUI(files)

#------------------------------------------------------------------------------
class Mod_CreateBOSSReport(EnabledLink):
    """Copies appropriate information for making a report in the BOSS thread."""
    text = _(u"Create BOSS Report...")

    def _enable(self):
        return len(self.data) != 1 or (
            not bosh.reOblivion.match(self.data[0].s))

    def Execute(self,event):
        text = u''
        if len(self.data) > 5:
            spoiler = True
            text += u'[spoiler]\n'
        else:
            spoiler = False
        # Scan for ITM and UDR's
        modInfos = [bosh.modInfos[x] for x in self.data]
        try:
            with balt.Progress(_(u"Dirty Edits"),u'\n'+u' '*60,abort=True) as progress:
                udr_itm_fog = bosh.ModCleaner.scan_Many(modInfos,progress=progress)
        except bolt.CancelError:
            return
        # Create the report
        for i,fileName in enumerate(self.data):
            if fileName == u'Oblivion.esm': continue
            fileInfo = bosh.modInfos[fileName]
            #-- Name of file, plus a link if we can figure it out
            installer = bosh.modInfos.table.getItem(fileName,'installer',u'')
            if not installer:
                text += fileName.s
            else:
                # Try to get the url of the file
                # Order of priority will be:
                #  TESNexus
                #  TESAlliance
                url = None
                ma = bosh.reTesNexus.search(installer)
                if ma and ma.group(2):
                    url = bush.game.nexusUrl+u'downloads/file.php?id='+ma.group(2)
                if not url:
                    ma = bosh.reTESA.search(installer)
                    if ma and ma.group(2):
                        url = u'http://tesalliance.org/forums/index.php?app=downloads&showfile='+ma.group(2)
                if url:
                    text += u'[url='+url+u']'+fileName.s+u'[/url]'
                else:
                    text += fileName.s
            #-- Version, if it exists
            version = bosh.modInfos.getVersion(fileName)
            if version:
                text += u'\n'+_(u'Version')+u': %s' % version
            #-- CRC
            text += u'\n'+_(u'CRC')+u': %08X' % fileInfo.cachedCrc()
            #-- Dirty edits
            if udr_itm_fog:
                udrs,itms,fogs = udr_itm_fog[i]
                if udrs or itms:
                    if bosh.settings['bash.CBashEnabled']:
                        text += (u'\nUDR: %i, ITM: %i '+_(u'(via Wrye Bash)')) % (len(udrs),len(itms))
                    else:
                        text += (u'\nUDR: %i, ITM not scanned '+_(u'(via Wrye Bash)')) % len(udrs)
            text += u'\n\n'
        if spoiler: text += u'[/spoiler]'

        # Show results + copy to clipboard
        balt.copyToClipboard(text)
        balt.showLog(self.window,text,_(u'BOSS Report'),asDialog=False,fixedFont=False,icons=bashBlue)

#------------------------------------------------------------------------------
class Mod_CopyModInfo(_Link):
    """Copies the basic info about selected mod(s)."""
    text = _(u'Copy Mod Info...')
    help = _(u'Copies the basic info about selected mod(s)')

    def Execute(self,event):
        text = u''
        if len(self.data) > 5:
            spoiler = True
            text += u'[spoiler]'
        else:
            spoiler = False
        # Create the report
        isFirst = True
        for i,fileName in enumerate(self.data):
            # add a blank line in between mods
            if isFirst: isFirst = False
            else: text += u'\n\n'
            fileInfo = bosh.modInfos[fileName]
            #-- Name of file, plus a link if we can figure it out
            installer = bosh.modInfos.table.getItem(fileName,'installer',u'')
            if not installer:
                text += fileName.s
            else:
                # Try to get the url of the file
                # Order of priority will be:
                #  TESNexus
                #  TESAlliance
                url = None
                ma = bosh.reTesNexus.search(installer)
                if ma and ma.group(2):
                    url = bush.game.nexusUrl+u'downloads/file.php?id='+ma.group(2)
                if not url:
                    ma = bosh.reTESA.search(installer)
                    if ma and ma.group(2):
                        url = u'http://tesalliance.org/forums/index.php?app=downloads&showfile='+ma.group(2)
                if url:
                    text += u'[url=%s]%s[/url]' % (url, fileName.s)
                else:
                    text += fileName.s
            for col in bosh.settings['bash.mods.cols']:
                if col == 'File': continue
                elif col == 'Rating':
                    value = bosh.modInfos.table.getItem(fileName,'rating',u'')
                elif col == 'Group':
                    value = bosh.modInfos.table.getItem(fileName,'group',u'')
                elif col == 'Installer':
                    value = bosh.modInfos.table.getItem(fileName,'installer', u'')
                elif col == 'Modified':
                    value = formatDate(fileInfo.mtime)
                elif col == 'Size':
                    value = formatInteger(max(fileInfo.size,1024)/1024 if fileInfo.size else 0)+u' KB'
                elif col == 'Author' and fileInfo.header:
                    value = fileInfo.header.author
                elif col == 'Load Order':
                    ordered = bosh.modInfos.ordered
                    if fileName in ordered:
                        value = u'%02X' % list(ordered).index(fileName)
                    else:
                        value = u''
                elif col == 'CRC':
                    value = u'%08X' % fileInfo.cachedCrc()
                elif col == 'Mod Status':
                    value = fileInfo.txt_status()
                text += u'\n%s: %s' % (col, value)
            #-- Version, if it exists
            version = bosh.modInfos.getVersion(fileName)
            if version:
                text += u'\n'+_(u'Version')+u': %s' % version
        if spoiler: text += u'[/spoiler]'
        # Show results + copy to clipboard
        balt.copyToClipboard(text)
        balt.showLog(self.window,text,_(u'Mod Info Report'),asDialog=False,
                     fixedFont=False,icons=bashBlue)

#------------------------------------------------------------------------------
class Mod_ListBashTags(_Link):
    """Copies list of bash tags to clipboard."""
    text = _(u"List Bash Tags...")
    help = _(u'Copies list of bash tags to clipboard')

    def Execute(self,event):
        #--Get masters list
        files = []
        for fileName in self.data:
            files.append(bosh.modInfos[fileName])
        text = bosh.modInfos.getTagList(files)
        balt.copyToClipboard(text)
        balt.showLog(self.window,text,_(u"Bash Tags"),asDialog=False,fixedFont=False,icons=bashBlue)

#------------------------------------------------------------------------------
class Mod_AllowNoGhosting(_Link):
    text = _(u'Disallow Ghosting')
    help = _(u'Disallow Ghosting for selected mod(s)')

    def Execute(self,event):
        files = []
        for fileName in self.data:
            fileInfo = bosh.modInfos[fileName]
            allowGhosting = False
            bosh.modInfos.table.setItem(fileName,'allowGhosting',allowGhosting)
            toGhost = False
            oldGhost = fileInfo.isGhost
            if fileInfo.setGhost(toGhost) != oldGhost:
                files.append(fileName)
        self.window.RefreshUI(files)

#------------------------------------------------------------------------------
class Mod_Ghost(EnabledLink):

    def _initData(self, window, data):
        _Link._initData(self, window, data)
        if len(data) == 1:
            self.help = _(u"Ghost/Unghost selected mod.  Active mods can't be ghosted")
            self.path = data[0]
            self.fileInfo = bosh.modInfos[self.path]
            self.isGhost = self.fileInfo.isGhost
            self.text = _(u"Ghost") if not self.isGhost else _(u"Unghost")
        else:
            self.help = _(u"Ghost selected mods.  Active mods can't be ghosted")
            self.text = _(u"Ghost")

    def _enable(self):
        # only enable ghosting for one item if not active
        if len(self.data) == 1 and not self.isGhost:
            return self.path not in bosh.modInfos.ordered
        return True

    def AppendToMenu(self,menu,window,data):
        # if not len(data) == 1: return
        return EnabledLink.AppendToMenu(self,menu,window,data)

    def Execute(self,event):
        files = []
        if len(self.data) == 1:
            # toggle
            if not self.isGhost: # ghosting - override allowGhosting with True
                bosh.modInfos.table.setItem(self.path,'allowGhosting',True)
            self.fileInfo.setGhost(not self.isGhost)
            files.append(self.path)
        else:
            for fileName in self.data:
                fileInfo = bosh.modInfos[fileName]
                allowGhosting = True
                bosh.modInfos.table.setItem(fileName,'allowGhosting',allowGhosting)
                toGhost = fileName not in bosh.modInfos.ordered
                oldGhost = fileInfo.isGhost
                if fileInfo.setGhost(toGhost) != oldGhost:
                    files.append(fileName)
        self.window.RefreshUI(files)

#------------------------------------------------------------------------------
class Mod_AllowInvertGhosting(_Link):
    text = _(u'Invert Ghosting')
    help = _(u'Invert Ghosting for selected mod(s)')

    def Execute(self,event):
        files = []
        for fileName in self.data:
            fileInfo = bosh.modInfos[fileName]
            allowGhosting = bosh.modInfos.table.getItem(fileName,'allowGhosting',True) ^ True
            bosh.modInfos.table.setItem(fileName,'allowGhosting',allowGhosting)
            toGhost = allowGhosting and fileName not in bosh.modInfos.ordered
            oldGhost = fileInfo.isGhost
            if fileInfo.setGhost(toGhost) != oldGhost:
                files.append(fileName)
        self.window.RefreshUI(files)

#------------------------------------------------------------------------------

class Mod_AllowGhosting(Link):
    """Toggles Ghostability."""

    def AppendToMenu(self,menu,window,data):
        Link._initData(self, window, data)
        if len(data) == 1:
            _self = self
            class _CheckLink(CheckLink):
                text = _(u"Disallow Ghosting")
                help = _(u"Toggle Ghostability")

                def Execute(self, event):
                    _self.Execute(event)

            cl = _CheckLink()
            menuItem = cl.AppendToMenu(menu,window,data)
            self.allowGhosting = bosh.modInfos.table.getItem(data[0],'allowGhosting',True)
            menuItem.Check(not self.allowGhosting)
        else:
            subMenu = balt.MenuLink(_(u"Ghosting"))
            subMenu.links.append(Mod_AllowAllGhosting())
            subMenu.links.append(Mod_AllowNoGhosting())
            subMenu.links.append(Mod_AllowInvertGhosting())
            menuItem = subMenu.AppendToMenu(menu,window,data)
        return menuItem

    def Execute(self,event):
        fileName = self.data[0]
        fileInfo = bosh.modInfos[fileName]
        allowGhosting = self.allowGhosting ^ True
        bosh.modInfos.table.setItem(fileName,'allowGhosting',allowGhosting)
        toGhost = allowGhosting and fileName not in bosh.modInfos.ordered
        oldGhost = fileInfo.isGhost
        if fileInfo.setGhost(toGhost) != oldGhost:
            self.window.RefreshUI(fileName)

#------------------------------------------------------------------------------
class Mod_SkipDirtyCheckAll(CheckLink):
    help = _(u"Set whether to check or not the selected mod(s) against LOOT's "
             u"dirty mod list")

    def __init__(self, bSkip):
        CheckLink.__init__(self)
        self.skip = bSkip
        self.text = _(
            u"Don't check against LOOT's dirty mod list") if self.skip else _(
            u"Check against LOOT's dirty mod list")

    def _check(self):
        for fileName in self.data:
            if bosh.modInfos.table.getItem(fileName,'ignoreDirty',self.skip) != self.skip:
                return False
        return True

    def Execute(self,event):
        for fileName in self.data:
            fileInfo = bosh.modInfos[fileName] # TODO(ut): unused
            bosh.modInfos.table.setItem(fileName,'ignoreDirty',self.skip)
        self.window.RefreshUI(self.data)

#------------------------------------------------------------------------------
class Mod_SkipDirtyCheckInvert(_Link):
    text = _(u"Invert checking against LOOT's dirty mod list")
    help = _(
        u"Invert checking against LOOT's dirty mod list for selected mod(s)")

    def Execute(self,event):
        for fileName in self.data:
            fileInfo = bosh.modInfos[fileName] # TODO(ut): unused
            ignoreDiry = bosh.modInfos.table.getItem(fileName,'ignoreDirty',False) ^ True
            bosh.modInfos.table.setItem(fileName,'ignoreDirty',ignoreDiry)
        self.window.RefreshUI(self.data)

#------------------------------------------------------------------------------
class Mod_SkipDirtyCheck(Link):
    """Toggles scanning for dirty mods on a per-mod basis."""

    def AppendToMenu(self,menu,window,data):
        Link._initData(self, window, data)
        if len(data) == 1:
            _self = self
            class _CheckLink(CheckLink):
                text = _(u"Don't check against LOOT's dirty mod list")
                help = _(u"Toggles scanning for dirty mods on a per-mod basis")

                def Execute(self, event):
                    _self.Execute(event)

            cl = _CheckLink()
            menuItem = cl.AppendToMenu(menu,window,data)
            self.ignoreDirty = bosh.modInfos.table.getItem(data[0],'ignoreDirty',False)
            menuItem.Check(self.ignoreDirty)
        else:
            subMenu = balt.MenuLink(_(u"Dirty edit scanning"))
            subMenu.links.append(Mod_SkipDirtyCheckAll(True))
            subMenu.links.append(Mod_SkipDirtyCheckAll(False))
            subMenu.links.append(Mod_SkipDirtyCheckInvert())
            menuItem = subMenu.AppendToMenu(menu,window,data)
        return menuItem

    def Execute(self,event):
        fileName = self.data[0]
        fileInfo = bosh.modInfos[fileName]
        self.ignoreDirty ^= True
        bosh.modInfos.table.setItem(fileName,'ignoreDirty',self.ignoreDirty)
        self.window.RefreshUI(fileName)

#------------------------------------------------------------------------------
class Mod_CleanMod(EnabledLink):
    """Fix fog on selected cells."""
    text = _(u'Nvidia Fog Fix')
    help = _(u'Modify fog values in interior cells to avoid the Nvidia black '
             u'screen bug')

    def _enable(self): return bool(self.data)

    def Execute(self,event):
        message = _(u'Apply Nvidia fog fix.  This modify fog values in interior cells to avoid the Nvidia black screen bug.')
        if not balt.askContinue(self.window,message,'bash.cleanMod.continue',
            _(u'Nvidia Fog Fix')):
            return
        with balt.Progress(_(u'Nvidia Fog Fix')) as progress:
            progress.setFull(len(self.data))
            fixed = []
            for index,fileName in enumerate(map(GPath,self.data)):
                if fileName.cs in bush.game.masterFiles: continue
                progress(index,_(u'Scanning')+fileName.s)
                fileInfo = bosh.modInfos[fileName]
                cleanMod = bosh.CleanMod(fileInfo)
                cleanMod.clean(SubProgress(progress,index,index+1))
                if cleanMod.fixedCells:
                    fixed.append(u'* %4d %s' % (len(cleanMod.fixedCells),fileName.s))
        if fixed:
            message = u'==='+_(u'Cells Fixed')+u':\n'+u'\n'.join(fixed)
            balt.showWryeLog(self.window,message,_(u'Nvidia Fog Fix'),
                             icons=bashBlue)
        else:
            message = _(u'No changes required.')
            balt.showOk(self.window,message,_(u'Nvidia Fog Fix'))

#------------------------------------------------------------------------------
class Mod_CreateBlankBashedPatch(_Link):
    """Create a new bashed patch."""
    text, help = _(u'New Bashed Patch...'), _(u'Create a new bashed patch')

    def Execute(self,event):
        newPatchName = bosh.PatchFile.generateNextBashedPatch(self.window)
        if newPatchName is not None:
            self.window.RefreshUI(detail=newPatchName)

#------------------------------------------------------------------------------
class Mod_CreateBlank(_Link):
    """Create a new blank mod."""
    text, help = _(u'New Mod...'), _(u'Create a new blank mod')

    def Execute(self,event):
        data = self.window.GetSelected()
        fileInfos = self.window.data
        count = 0
        newName = GPath(u'New Mod.esp')
        while newName in fileInfos:
            count += 1
            newName = GPath(u'New Mod %d.esp' % count)
        newInfo = fileInfos.factory(fileInfos.dir,newName)
        if data:
            newTime = max(fileInfos[x].mtime for x in data)
        else:
            newTime = max(fileInfos[x].mtime for x in fileInfos.data)
        newInfo.mtime = fileInfos.getFreeTime(newTime,newTime)
        newFile = bosh.ModFile(newInfo,bosh.LoadFactory(True))
        newFile.tes4.masters = [GPath(bush.game.masterFiles[0])]
        newFile.safeSave()
        mod_group = fileInfos.table.getColumn('group')
        mod_group[newName] = mod_group.get(newName,u'')
        bosh.modInfos.refresh()
        self.window.RefreshUI(detail=newName)

#------------------------------------------------------------------------------
class Mod_CreateDummyMasters(EnabledLink):
    """TES4Edit tool, makes dummy plugins for each missing master, for use if looking at a 'Filter' patch."""
    text = _(u'Create Dummy Masters...')
    help = _(u"TES4Edit tool, makes dummy plugins for each missing master of"
             u" the selected mod, for use if looking at a 'Filter' patch")

    def _enable(self):
        return len(self.data) == 1 and bosh.modInfos[self.data[
            0]].getStatus() == 30  # Missing masters

    def Execute(self,event):
        """Handle execution."""
        if not balt.askYes(self.window,
                           _(u"This is an advanced feature for editing 'Filter' patches in TES4Edit.  It will create dummy plugins for each missing master.  Are you sure you want to continue?")
                           + u'\n\n' +
                           _(u"To remove these files later, use 'Clean Dummy Masters...'"),
                           _(u'Create Files')):
            return
        doCBash = False #settings['bash.CBashEnabled'] - something odd's going on, can't rename temp names
        modInfo = bosh.modInfos[self.data[0]]
        lastTime = modInfo.mtime - 1
        if doCBash:
            newFiles = []
        refresh = []
        for master in modInfo.header.masters:
            if master in bosh.modInfos:
                lastTime = bosh.modInfos[master].mtime
                continue
            # Missing master, create a dummy plugin for it
            newInfo = bosh.ModInfo(modInfo.dir,master)
            newTime = lastTime
            newInfo.mtime = bosh.modInfos.getFreeTime(newTime,newTime)
            refresh.append(master)
            if doCBash:
                # TODO: CBash doesn't handle unicode.  Make this make temp unicode safe
                # files, then rename them to the correct unicode name later
                newFiles.append(newInfo.getPath().stail)
            else:
                newFile = bosh.ModFile(newInfo,bosh.LoadFactory(True))
                newFile.tes4.author = u'BASHED DUMMY'
                newFile.safeSave()
        if doCBash:
            with ObCollection(ModsPath=bosh.dirs['mods'].s) as Current:
                tempname = u'_DummyMaster.esp.tmp'
                modFile = Current.addMod(tempname, CreateNew=True)
                Current.load()
                modFile.TES4.author = u'BASHED DUMMY'
                for newFile in newFiles:
                    modFile.save(CloseCollection=False,DestinationName=newFile)
        refreshData()
        self.window.RefreshUI()

class Mods_CleanDummyMasters(EnabledLink):
    """Clean up after using a 'Create Dummy Masters...' command."""
    text = _(u'Remove Dummy Masters...')
    help = _(u"Clean up after using a 'Create Dummy Masters...' command")

    def _enable(self):
        for fileName in bosh.modInfos.data:
            fileInfo = bosh.modInfos[fileName]
            if fileInfo.header.author == u'BASHED DUMMY':
                return True
        return False

    def Execute(self,event):
        """Handle execution."""
        remove = []
        for fileName in bosh.modInfos.data:
            fileInfo = bosh.modInfos[fileName]
            if fileInfo.header.author == u'BASHED DUMMY':
                remove.append(fileName)
        remove = bosh.modInfos.getOrdered(remove)
        message = [u'',_(u'Uncheck items to skip deleting them if desired.')]
        message.extend(remove)
        from . import bashFrame # FIXME
        dialog = ListBoxes(bashFrame,_(u'Delete Dummy Masters'),
                     _(u'Delete these items? This operation cannot be undone.'),
                     [message])
        if dialog.ShowModal() == ListBoxes.ID_CANCEL:
            dialog.Destroy()
            return
        id = dialog.ids[u'']
        checks = dialog.FindWindowById(id)
        if checks:
            for i,mod in enumerate(remove):
                if checks.IsChecked(i):
                    self.window.data.delete(mod)
        dialog.Destroy()
        bashFrame.RefreshData()
        self.window.RefreshUI()

#------------------------------------------------------------------------------
from ..patcher.utilities import FactionRelations, CBash_FactionRelations

class Mod_FactionRelations_Export(_Mod_Export_Link):
    """Export faction relations from mod to text file."""
    askTitle = _(u'Export faction relations to:')
    csvFile = u'_Relations.csv'
    progressTitle = _(u'Export Relations')
    text = _(u'Relations...')
    help = _(u'Export faction relations from mod to text file')

    def _parser(self):
        return CBash_FactionRelations() if CBash else FactionRelations()

#------------------------------------------------------------------------------
class Mod_FactionRelations_Import(_Mod_Import_Link):
    """Imports faction relations from text file to mod."""
    text = _(u'Relations...')
    help = _(u'Import faction relations from text file to mod')

    def _parser(self):
        return CBash_FactionRelations() if CBash else FactionRelations()

    def Execute(self,event):
        message = (_(u"This command will import faction relation info from a previously exported file.")
                   + u'\n\n' +
                   _(u"See the Bash help file for more info."))
        if not balt.askContinue(self.window,message,
                'bash.factionRelations.import.continue',_(u'Import Relations')):
            return
        fileName = GPath(self.data[0])
        fileInfo = bosh.modInfos[fileName]
        textName = fileName.root+u'_Relations.csv'
        textDir = bosh.dirs['patches']
        #--File dialog
        textPath = balt.askOpen(self.window,_(u'Import faction relations from:'),
            textDir, textName, u'*_Relations.csv',mustExist=True)
        if not textPath: return
        (textDir,textName) = textPath.headTail
        #--Extension error check
        ext = textName.cext
        if ext != u'.csv':
            balt.showError(self.window,_(u'Source file must be a _Relations.csv file.'))
            return
        #--Export
        changed = None
        with balt.Progress(_(u'Import Relations')) as progress:
            factionRelations =  self._parser()
            progress(0.1,_(u'Reading')+u' '+textName.s+u'.')
            factionRelations.readFromText(textPath)
            progress(0.2,_(u'Applying to')+u' '+fileName.s+u'.')
            changed = factionRelations.writeToMod(fileInfo)
            progress(1.0,_(u'Done.'))
        #--Log
        if not changed:
            balt.showOk(self.window,
                _(u'No relevant faction relations to import.'),
                _(u'Import Relations'))
        else:
            buff = StringIO.StringIO()
            buff.write(u'* %03d  %s\n' % (changed, fileName.s))
            text = buff.getvalue()
            buff.close()
            balt.showLog(self.window,text,_(u'Import Relations'),icons=bashBlue)

#------------------------------------------------------------------------------
from ..patcher.utilities import ActorFactions, CBash_ActorFactions

class Mod_Factions_Export(_Mod_Export_Link):
    """Export factions from mod to text file."""
    askTitle = _(u'Export factions to:')
    csvFile = u'_Factions.csv'
    progressTitle = _(u'Export Factions')
    text = _(u'Factions...')
    help = _(u'Export factions from mod to text file')

    def _parser(self):
        return CBash_ActorFactions() if CBash else ActorFactions()

#------------------------------------------------------------------------------
class Mod_Factions_Import(_Mod_Import_Link):
    """Imports factions from text file to mod."""
    text = _(u'Factions...')
    help = _(u'Import factions from text file to mod')

    def _parser(self):
        return CBash_ActorFactions() if CBash else ActorFactions()

    def Execute(self,event):
        message = (_(u"This command will import faction ranks from a previously exported file.")
                   + u'\n\n' +
                   _(u'See the Bash help file for more info.'))
        if not balt.askContinue(self.window,message,
                'bash.factionRanks.import.continue',_(u'Import Factions')):
            return
        fileName = GPath(self.data[0])
        fileInfo = bosh.modInfos[fileName]
        textName = fileName.root+u'_Factions.csv'
        textDir = bosh.dirs['patches']
        #--File dialog
        textPath = balt.askOpen(self.window,_(u'Import Factions from:'),
            textDir, textName, u'*_Factions.csv',mustExist=True)
        if not textPath: return
        (textDir,textName) = textPath.headTail
        #--Extension error check
        ext = textName.cext
        if ext != u'.csv':
            balt.showError(self.window,
                _(u'Source file must be a _Factions.csv file.'))
            return
        #--Export
        changed = None
        with balt.Progress(_(u'Import Factions')) as progress:
            actorFactions = self._parser()
            progress(0.1,_(u'Reading')+u' '+textName.s+u'.')
            actorFactions.readFromText(textPath)
            progress(0.2,_(u'Applying to')+u' '+fileName.s+u'.')
            changed = actorFactions.writeToMod(fileInfo)
            progress(1.0,_(u'Done.'))
        #--Log
        if not changed:
            balt.showOk(self.window,_(u'No relevant faction ranks to import.'),
                        _(u'Import Factions'))
        else:
            buff = StringIO.StringIO()
            for groupName in sorted(changed):
                buff.write(u'* %s : %03d  %s\n' % (groupName,changed[groupName],fileName.s))
            text = buff.getvalue()
            buff.close()
            balt.showLog(self.window,text,_(u'Import Factions'),icons=bashBlue)

#------------------------------------------------------------------------------
class Mod_MarkLevelers(EnabledLink):
    """Marks (tags) selected mods as Delevs and/or Relevs according to Leveled Lists.csv."""
    text = _(u'Mark Levelers...')

    def _enable(self): return bool(self.data)

    def Execute(self,event):
        message = _(u'Obsolete. Mods are now automatically tagged when possible.')
        balt.showInfo(self.window,message,_(u'Mark Levelers'))

#------------------------------------------------------------------------------
class Mod_MarkMergeable(EnabledLink):
    """Returns true if can act as patch mod."""
    def __init__(self,doCBash):
        Link.__init__(self)
        self.doCBash = doCBash
        self.text = _(u'Mark Mergeable (CBash)...') if doCBash else _(u'Mark Mergeable...')

    def _enable(self): return bool(self.data)

    def Execute(self,event):
        yes,no = [],[]
        mod_mergeInfo = bosh.modInfos.table.getColumn('mergeInfo')
        for fileName in map(GPath,self.data):
            if not self.doCBash and bosh.reOblivion.match(fileName.s): continue
            fileInfo = bosh.modInfos[fileName]
            if self.doCBash:
                if fileName == u"Oscuro's_Oblivion_Overhaul.esp":
                    reason = u'\n.    '+_(u'Marked non-mergeable at request of mod author.')
                else:
                    reason = bosh.CBash_PatchFile.modIsMergeable(fileInfo,True)
            else:
                reason = bosh.PatchFile.modIsMergeable(fileInfo,True)

            if reason == True:
                mod_mergeInfo[fileName] = (fileInfo.size,True)
                yes.append(fileName)
            else:
                if (u'\n.    '+_(u"Has 'NoMerge' tag.")) in reason:
                    mod_mergeInfo[fileName] = (fileInfo.size,True)
                else:
                    mod_mergeInfo[fileName] = (fileInfo.size,False)
                no.append(u"%s:%s" % (fileName.s,reason))
        message = u'== %s ' % ([u'Python',u'CBash'][self.doCBash])+_(u'Mergeability')+u'\n\n'
        if yes:
            message += u'=== '+_(u'Mergeable')+u'\n* '+u'\n\n* '.join(x.s for x in yes)
        if yes and no:
            message += u'\n\n'
        if no:
            message += u'=== '+_(u'Not Mergeable')+u'\n* '+'\n\n* '.join(no)
        self.window.RefreshUI(yes)
        self.window.RefreshUI(no)
        if message != u'':
            balt.showWryeLog(self.window,message,_(u'Mark Mergeable'),icons=bashBlue)
#------------------------------------------------------------------------------
from ..patcher.utilities import ScriptText, CBash_ScriptText

class Mod_Scripts_Export(_Mod_Export_Link):
    """Export scripts from mod to text file."""
    text = _(u'Scripts...')
    help = _(u'Export scripts from mod to text file')

    def Execute(self,event): # overrides _Mod_Export_Link
        fileName = GPath(self.data[0])
        fileInfo = bosh.modInfos[fileName]
        defaultPath = bosh.dirs['patches'].join(fileName.s+u' Exported Scripts')
        def OnOk(event):
            dialog.EndModal(1)
            bosh.settings['bash.mods.export.deprefix'] = gdeprefix.GetValue().strip()
            bosh.settings['bash.mods.export.skip'] = gskip.GetValue().strip()
            bosh.settings['bash.mods.export.skipcomments'] = gskipcomments.GetValue()
        from . import bashFrame # FIXME
        dialog = wx.Dialog(bashFrame,wx.ID_ANY,_(u'Export Scripts Options'),
                           size=(400,180),style=wx.DEFAULT_DIALOG_STYLE)
        gskip = textCtrl(dialog)
        gdeprefix = textCtrl(dialog)
        gskipcomments = toggleButton(dialog,_(u'Filter Out Comments'),
            tip=_(u"If active doesn't export comments in the scripts"))
        gskip.SetValue(bosh.settings['bash.mods.export.skip'])
        gdeprefix.SetValue(bosh.settings['bash.mods.export.deprefix'])
        gskipcomments.SetValue(bosh.settings['bash.mods.export.skipcomments'])
        sizer = vSizer(
            staticText(dialog,_(u"Skip prefix (leave blank to not skip any), non-case sensitive):"),style=wx.ST_NO_AUTORESIZE),
            gskip,
            spacer,
            staticText(dialog,(_(u'Remove prefix from file names i.e. enter cob to save script cobDenockInit')
                               + u'\n' +
                               _(u'as DenockInit.ext rather than as cobDenockInit.ext')
                               + u'\n' +
                               _(u'(Leave blank to not cut any prefix, non-case sensitive):')
                               ),style=wx.ST_NO_AUTORESIZE),
            gdeprefix,
            spacer,
            gskipcomments,
            (hSizer(
                spacer,
                button(dialog,id=wx.ID_OK,onClick=OnOk),
                (button(dialog,id=wx.ID_CANCEL),0,wx.LEFT,4),
                ),0,wx.EXPAND|wx.LEFT|wx.RIGHT|wx.BOTTOM,6),
            )
        dialog.SetSizer(sizer)
        questions = dialog.ShowModal()
        if questions != 1: return #because for some reason cancel/close dialogue is returning 5101!
        if not defaultPath.exists():
            defaultPath.makedirs()
        textDir = balt.askDirectory(self.window,
            _(u'Choose directory to export scripts to'),defaultPath)
        if textDir != defaultPath:
            for asDir,sDirs,sFiles in os.walk(defaultPath.s):
                if not (sDirs or sFiles):
                    defaultPath.removedirs()
        if not textDir: return
        #--Export
        #try:
        if CBash:
            scriptText = CBash_ScriptText()
        else:
            scriptText = ScriptText()
        scriptText.readFromMod(fileInfo,fileName.s)
        exportedScripts = scriptText.writeToText(fileInfo,bosh.settings['bash.mods.export.skip'],textDir,bosh.settings['bash.mods.export.deprefix'],fileName.s,bosh.settings['bash.mods.export.skipcomments'])
        #finally:
        balt.showLog(self.window,exportedScripts,_(u'Export Scripts'),
                     icons=bashBlue)

#------------------------------------------------------------------------------
class Mod_Scripts_Import(_Mod_Import_Link):
    """Import scripts from text file or other mod."""
    text = _(u'Scripts...')
    help = _(u'Import scripts from text file or other mod')

    def Execute(self,event):
        message = (_(u"Import script from a text file.  This will replace existing scripts and is not reversible (except by restoring from backup)!"))
        if not balt.askContinue(self.window,message,'bash.scripts.import.continue',
            _(u'Import Scripts')):
            return
        fileName = GPath(self.data[0])
        fileInfo = bosh.modInfos[fileName]
        defaultPath = bosh.dirs['patches'].join(fileName.s+u' Exported Scripts')
        if not defaultPath.exists():
            defaultPath = bosh.dirs['patches']
        textDir = balt.askDirectory(self.window,
            _(u'Choose directory to import scripts from'),defaultPath)
        if textDir is None:
            return
        message = (_(u"Import scripts that don't exist in the esp as new scripts?")
                   + u'\n' +
                   _(u'(If not they will just be skipped).')
                   )
        makeNew = balt.askYes(self.window,message,_(u'Import Scripts'),icon=wx.ICON_QUESTION)
        if CBash:
            scriptText = CBash_ScriptText()
        else:
            scriptText = ScriptText()
        scriptText.readFromText(textDir.s,fileInfo)
        changed, added = scriptText.writeToMod(fileInfo,makeNew)
    #--Log
        if not (len(changed) or len(added)):
            balt.showOk(self.window,_(u"No changed or new scripts to import."),
                        _(u"Import Scripts"))
        else:
            if changed:
                changedScripts = (_(u'Imported %d changed scripts from %s:')
                                  + u'\n%s') % (len(changed),textDir.s,u'*'+u'\n*'.join(sorted(changed)))
            else:
                changedScripts = u''
            if added:
                addedScripts = (_(u'Imported %d new scripts from %s:')
                                + u'\n%s') % (len(added),textDir.s,u'*'+u'\n*'.join(sorted(added)))
            else:
                addedScripts = u''
            if changed and added:
                report = changedScripts + u'\n\n' + addedScripts
            elif changed:
                report = changedScripts
            elif added:
                report = addedScripts
            balt.showLog(self.window,report,_(u'Import Scripts'),icons=bashBlue)

#------------------------------------------------------------------------------
from ..patcher.utilities import ItemStats, CBash_ItemStats

class Mod_Stats_Export(_Mod_Export_Link):
    """Export armor and weapon stats from mod to text file.""" # TODO: armor and weapon ??
    askTitle = _(u'Export stats to:')
    csvFile = u'_Stats.csv'
    progressTitle = _(u"Export Stats")
    text = _(u'Stats...')
    help = _(u'Export stats from mod to text file')

    def _parser(self):
        return CBash_ItemStats() if CBash else ItemStats()

#------------------------------------------------------------------------------
class Mod_Stats_Import(_Mod_Import_Link):
    """Import stats from text file or other mod."""
    text = _(u'Stats...')
    help = _(u'Import stats from text file or other mod')

    def Execute(self,event):
        message = (_(u"Import item stats from a text file. This will replace existing stats and is not reversible!"))
        if not balt.askContinue(self.window,message,'bash.stats.import.continue',
            _(u'Import Stats')):
            return
        fileName = GPath(self.data[0])
        fileInfo = bosh.modInfos[fileName]
        textName = fileName.root+u'_Stats.csv'
        textDir = bosh.dirs['patches']
        #--File dialog
        textPath = balt.askOpen(self.window,_(u'Import stats from:'),
            textDir, textName, u'*_Stats.csv',mustExist=True)
        if not textPath: return
        (textDir,textName) = textPath.headTail
        #--Extension error check
        ext = textName.cext
        if ext != u'.csv':
            balt.showError(self.window,_(u'Source file must be a Stats.csv file.'))
            return
        #--Export
        changed = None
        with balt.Progress(_(u"Import Stats")) as progress:
            if CBash:
                itemStats = CBash_ItemStats()
            else:
                itemStats = ItemStats()
            progress(0.1,_(u"Reading %s.") % textName.s)
            itemStats.readFromText(textPath)
            progress(0.2,_(u"Applying to %s.") % fileName.s)
            changed = itemStats.writeToMod(fileInfo)
            progress(1.0,_(u"Done."))
        #--Log
        if not changed:
            balt.showOk(self.window,_(u"No relevant stats to import."),_(u"Import Stats"))
        else:
            if not len(changed):
                balt.showOk(self.window,_(u"No changed stats to import."),_(u"Import Stats"))
            else:
                buff = StringIO.StringIO()
                for modName in sorted(changed):
                    buff.write(u'* %03d  %s\n' % (changed[modName], modName.s))
                balt.showLog(self.window,buff.getvalue(),_(u'Import Stats'),icons=bashBlue)
                buff.close()

#------------------------------------------------------------------------------
from ..patcher.utilities import CompleteItemData, CBash_CompleteItemData

class Mod_ItemData_Export(_Mod_Export_Link): # TODO: unused !!
    """Export pretty much complete item data from mod to text file."""
    askTitle = _(u'Export item data to:')
    csvFile = u'_ItemData.csv'
    progressTitle = _(u"Export Item Data")
    text = _(u'Item Data...')
    help = _(u'Export pretty much complete item data from mod to text file')

    def _parser(self):
        return CBash_CompleteItemData() if CBash else CompleteItemData()

#------------------------------------------------------------------------------
class Mod_ItemData_Import(_Mod_Import_Link): # TODO: unused !!
    """Import stats from text file or other mod."""
    text = _(u'Item Data...')
    help = _(u'Import pretty much complete item data from text file or other'
             u' mod')

    def Execute(self,event):
        message = (_(u"Import pretty much complete item data from a text file.  This will replace existing data and is not reversible!"))
        if not balt.askContinue(self.window,message,'bash.itemdata.import.continue',
            _(u'Import Item Data')):
            return
        fileName = GPath(self.data[0])
        fileInfo = bosh.modInfos[fileName]
        textName = fileName.root+u'_ItemData.csv'
        textDir = bosh.dirs['patches']
        #--File dialog
        textPath = balt.askOpen(self.window,_(u'Import item data from:'),
            textDir, textName, u'*_ItemData.csv',mustExist=True)
        if not textPath: return
        (textDir,textName) = textPath.headTail
        #--Extension error check
        ext = textName.cext
        if ext != '.csv':
            balt.showError(self.window,_(u'Source file must be a ItemData.csv file.'))
            return
        #--Export
        changed = None
        with balt.Progress(_(u'Import Item Data')) as progress:
            itemStats = CompleteItemData() # FIXME - why not if CBash: ?
            progress(0.1,_(u'Reading')+u' '+textName.s+u'.')
            if ext == u'.csv':
                itemStats.readFromText(textPath)
            else:
                srcInfo = bosh.ModInfo(textDir,textName)
                itemStats.readFromMod(srcInfo)
            progress(0.2,_(u'Applying to')+u' '+fileName.s+u'.')
            changed = itemStats.writeToMod(fileInfo)
            progress(1.0,_(u'Done.'))
        #--Log
        if not changed:
            balt.showOk(self.window,_(u'No relevant data to import.'),
                        _(u'Import Item Data'))
        else:
            buff = StringIO.StringIO()
            for modName in sorted(changed):
                buff.write(_(u'Imported Item Data:')
                           + u'\n* %03d  %s:\n' % (changed[modName], modName.s))
            balt.showLog(self.window,buff.getvalue(),_(u'Import Item Data'),icons=bashBlue)
            buff.close()

#------------------------------------------------------------------------------
from ..patcher.utilities import ItemPrices, CBash_ItemPrices

class Mod_Prices_Export(_Mod_Export_Link):
    """Export item prices from mod to text file."""
    askTitle = _(u'Export prices to:')
    csvFile = u'_Prices.csv'
    progressTitle = _(u'Export Prices')
    text = _(u'Prices...')
    help = _(u'Export item prices from mod to text file')

    def _parser(self):
        return CBash_ItemPrices() if CBash else ItemPrices()

#------------------------------------------------------------------------------
class Mod_Prices_Import(_Mod_Import_Link):
    """Import prices from text file."""
    text = _(u'Prices...')
    help = _(u'Import item prices from text file')

    def Execute(self,event):
        message = (_(u"Import item prices from a text file.  This will replace existing prices and is not reversible!"))
        if not balt.askContinue(self.window,message,
            'bash.prices.import.continue',_(u'Import prices')):
            return
        fileName = GPath(self.data[0])
        fileInfo = bosh.modInfos[fileName]
        textName = fileName.root+u'_Prices.csv'
        textDir = bosh.dirs['patches']
        #--File dialog
        textPath = balt.askOpen(self.window,_(u'Import prices from:'),
            textDir, textName, u'*_Prices.csv',mustExist=True)
        if not textPath: return
        (textDir,textName) = textPath.headTail
        #--Extension error check
        ext = textName.cext
        if ext not in [u'.csv',u'.ghost',u'.esm',u'.esp']:
            balt.showError(self.window,_(u'Source file must be a Prices.csv file or esp/m.'))
            return
        #--Export
        changed = None
        with balt.Progress(_(u'Import Prices')) as progress:
            if CBash:
                itemPrices = CBash_ItemPrices()
            else:
                itemPrices = ItemPrices()
            progress(0.1,_(u'Reading')+u' '+textName.s+u'.')
            if ext == u'.csv':
                itemPrices.readFromText(textPath)
            else:
                srcInfo = bosh.ModInfo(textDir,textName)
                itemPrices.readFromMod(srcInfo)
            progress(0.2,_(u'Applying to')+u' '+fileName.s+u'.')
            changed = itemPrices.writeToMod(fileInfo)
            progress(1.0,_(u'Done.'))
        #--Log
        if not changed:
            balt.showOk(self.window,_(u'No relevant prices to import.'),
                        _(u'Import Prices'))
        else:
            buff = StringIO.StringIO()
            for modName in sorted(changed):
                buff.write(_(u'Imported Prices:')
                           + u'\n* %s: %d\n' % (modName.s,changed[modName]))
            balt.showLog(self.window,buff.getvalue(),_(u'Import Prices'),
                         icons=bashBlue)
            buff.close()

#------------------------------------------------------------------------------
from ..patcher.utilities import CBash_MapMarkers

class _Mod_Export_Link_CBash(_Mod_Export_Link):
    def _enable(self): return bool(self.data) and bool(CBash)

class _Mod_Import_Link_CBash(_Mod_Import_Link):
    def _enable(self): return len(self.data) == 1 and bool(CBash)

class CBash_Mod_MapMarkers_Export(_Mod_Export_Link_CBash):
    """Export map marker stats from mod to text file."""
    askTitle = _(u'Export Map Markers to:')
    csvFile = u'_MapMarkers.csv'
    progressTitle = _(u'Export Map Markers')
    text = _(u'Map Markers...')
    help = _(u'Export map marker stats from mod to text file')

    def _parser(self): return CBash_MapMarkers()

#------------------------------------------------------------------------------
class CBash_Mod_MapMarkers_Import(_Mod_Import_Link_CBash):
    """Import MapMarkers from text file."""
    text = _(u'Map Markers...')
    help = _(u'Import MapMarkers from text file')

    def Execute(self,event):
        message = (_(u"Import Map Markers data from a text file.  This will replace existing the data on map markers with the same editor ids and is not reversible!"))
        if not balt.askContinue(self.window,message,
            'bash.MapMarkers.import.continue',_(u'Import Map Markers')):
            return
        fileName = GPath(self.data[0])
        fileInfo = bosh.modInfos[fileName]
        textName = fileName.root+u'_MapMarkers.csv'
        textDir = bosh.dirs['patches']
        #--File dialog
        textPath = balt.askOpen(self.window,_(u'Import Map Markers from:'),
            textDir, textName, u'*_MapMarkers.csv',mustExist=True)
        if not textPath: return
        (textDir,textName) = textPath.headTail
        #--Extension error check
        ext = textName.cext
        if ext != u'.csv':
            balt.showError(self.window,_(u'Source file must be a MapMarkers.csv file'))
            return
        #--Export
        changed = None
        with balt.Progress(_(u'Import Map Markers')) as progress:
            MapMarkers = CBash_MapMarkers()
            progress(0.1,_(u'Reading')+u' '+textName.s)
            MapMarkers.readFromText(textPath)
            progress(0.2,_(u'Applying to')+u' '+fileName.s)
            changed = MapMarkers.writeToMod(fileInfo)
            progress(1.0,_(u'Done.'))
        #--Log
        if not changed:
            balt.showOk(self.window,_(u'No relevant Map Markers to import.'),
                        _(u'Import Map Markers'))
        else:
            buff = StringIO.StringIO()
            buff.write((_(u'Imported Map Markers to mod %s:')
                        + u'\n') % (fileName.s,))
            for eid in sorted(changed):
                buff.write(u'* %s\n' % eid)
            balt.showLog(self.window,buff.getvalue(),_(u'Import Map Markers'),
                         icons=bashBlue)
            buff.close()

#------------------------------------------------------------------------------
from ..patcher.utilities import CBash_CellBlockInfo

class CBash_Mod_CellBlockInfo_Export(_Mod_Export_Link_CBash):
    """Export Cell Block Info to text file
    (in the form of Cell, block, subblock)."""
    askTitle = _(u'Export Cell Block Info to:')
    csvFile = u'_CellBlockInfo.csv'
    progressTitle = _(u"Export Cell Block Info")
    text = _(u'Cell Block Info...')
    help = _(u'Export Cell Block Info to text file (in the form of Cell,'
             u' block, subblock)')

    def _parser(self): return CBash_CellBlockInfo()

#------------------------------------------------------------------------------
from ..patcher.utilities import SigilStoneDetails, CBash_SigilStoneDetails

class Mod_SigilStoneDetails_Export(_Mod_Export_Link):
    """Export Sigil Stone details from mod to text file."""
    askTitle = _(u'Export Sigil Stone details to:')
    csvFile = u'_SigilStones.csv'
    progressTitle = _(u'Export Sigil Stone details')
    text = _(u'Sigil Stones...')
    help = _(u'Export Sigil Stone details from mod to text file')

    def _parser(self):
        return CBash_SigilStoneDetails() if CBash else SigilStoneDetails()

#------------------------------------------------------------------------------
class Mod_SigilStoneDetails_Import(_Mod_Import_Link):
    """Import Sigil Stone details from text file."""
    text = _(u'Sigil Stones...')
    help = _(u'Import Sigil Stone details from text file')

    def _parser(self):
        return CBash_SigilStoneDetails() if CBash else SigilStoneDetails()

    def Execute(self,event):
        message = (_(u"Import Sigil Stone details from a text file.  This will replace existing the data on sigil stones with the same form ids and is not reversible!"))
        if not balt.askContinue(self.window,message,
            'bash.SigilStone.import.continue',
            _(u'Import Sigil Stones details')):
            return
        fileName = GPath(self.data[0])
        fileInfo = bosh.modInfos[fileName]
        textName = fileName.root+u'_SigilStones.csv'
        textDir = bosh.dirs['patches']
        #--File dialog
        textPath = balt.askOpen(self.window,
            _(u'Import Sigil Stone details from:'),
            textDir, textName, u'*_SigilStones.csv',mustExist=True)
        if not textPath: return
        (textDir,textName) = textPath.headTail
        #--Extension error check
        ext = textName.cext
        if ext != u'.csv':
            balt.showError(self.window,_(u'Source file must be a _SigilStones.csv file'))
            return
        #--Export
        changed = None
        with balt.Progress(_(u'Import Sigil Stone details')) as progress:
            sigilStones = self._parser()
            progress(0.1,_(u'Reading')+u' '+textName.s+u'.')
            sigilStones.readFromText(textPath)
            progress(0.2,_(u'Applying to')+u' '+fileName.s+u'.')
            changed = sigilStones.writeToMod(fileInfo)
            progress(1.0,_(u'Done.'))
        #--Log
        if not changed:
            balt.showOk(self.window,
                _(u'No relevant Sigil Stone details to import.'),
                _(u'Import Sigil Stone details'))
        else:
            buff = StringIO.StringIO()
            buff.write((_(u'Imported Sigil Stone details to mod %s:')
                        +u'\n') % fileName.s)
            for eid in sorted(changed):
                buff.write(u'* %s\n' % eid)
            balt.showLog(self.window,buff.getvalue(),
                         _(u'Import Sigil Stone details'),icons=bashBlue)
            buff.close()

#------------------------------------------------------------------------------
from ..patcher.utilities import SpellRecords, CBash_SpellRecords

class Mod_SpellRecords_Export(_Mod_Export_Link):
    """Export Spell details from mod to text file."""
    text = _(u'Spells...')
    help = _(u'Export Spell details from mod to text file')

    def Execute(self,event): # overrides _Mod_Export_Link
        fileName = GPath(self.data[0])
        fileInfo = bosh.modInfos[fileName]
        textName = fileName.root+u'_Spells.csv'
        textDir = bosh.dirs['patches']
        textDir.makedirs()
        #--File dialog
        textPath = balt.askSave(self.window,_(u'Export Spell details to:'),textDir,textName, u'*_Spells.csv')
        if not textPath: return
        message = (_(u'Export flags and effects?')
                   + u'\n' +
                   _(u'(If not they will just be skipped).')
                   )
        doDetailed = balt.askYes(self.window,message,_(u'Export Spells'),icon=wx.ICON_QUESTION)
        (textDir,textName) = textPath.headTail
        #--Export
        with balt.Progress(_(u'Export Spell details')) as progress:
            if CBash:
                spellRecords = CBash_SpellRecords(detailed=doDetailed)
            else:
                spellRecords = SpellRecords(detailed=doDetailed)
            readProgress = SubProgress(progress,0.1,0.8)
            readProgress.setFull(len(self.data))
            for index,fileName in enumerate(map(GPath,self.data)):
                fileInfo = bosh.modInfos[fileName]
                readProgress(index,_(u'Reading')+u' '+fileName.s+u'.')
                spellRecords.readFromMod(fileInfo)
            progress(0.8,_(u'Exporting to')+u' '+textName.s+u'.')
            spellRecords.writeToText(textPath)
            progress(1.0,_(u'Done.'))

#------------------------------------------------------------------------------
class Mod_SpellRecords_Import(_Mod_Import_Link):
    """Import Spell details from text file."""
    text = _(u'Spells...')
    help = _(u'Import Spell details from text file')

    def Execute(self,event):
        message = (_(u"Import Spell details from a text file.  This will replace existing the data on spells with the same form ids and is not reversible!"))
        if not balt.askContinue(self.window,message,
            'bash.SpellRecords.import.continue',
            _(u'Import Spell details')):
            return
        fileName = GPath(self.data[0])
        fileInfo = bosh.modInfos[fileName]
        textName = fileName.root+u'_Spells.csv'
        textDir = bosh.dirs['patches']
        #--File dialog
        textPath = balt.askOpen(self.window,_(u'Import Spell details from:'),
            textDir, textName, u'*_Spells.csv',mustExist=True)
        if not textPath: return
        message = (_(u'Import flags and effects?')
                   + u'\n' +
                   _(u'(If not they will just be skipped).')
                   )
        doDetailed = balt.askYes(self.window,message,_(u'Import Spell details'),
                                 icon=wx.ICON_QUESTION)
        (textDir,textName) = textPath.headTail
        #--Extension error check
        ext = textName.cext
        if ext != u'.csv':
            balt.showError(self.window,_(u'Source file must be a _Spells.csv file'))
            return
        #--Export
        changed = None
        with balt.Progress(_(u'Import Spell details')) as progress:
            if CBash:
                spellRecords = CBash_SpellRecords(detailed=doDetailed)
            else:
                spellRecords = SpellRecords(detailed=doDetailed)
            progress(0.1,_(u'Reading')+u' '+textName.s+u'.')
            spellRecords.readFromText(textPath)
            progress(0.2,_(u'Applying to')+u' '+fileName.s+u'.')
            changed = spellRecords.writeToMod(fileInfo)
            progress(1.0,_(u'Done.'))
        #--Log
        if not changed:
            balt.showOk(self.window,_(u'No relevant Spell details to import.'),
                        _(u'Import Spell details'))
        else:
            buff = StringIO.StringIO()
            buff.write((_(u'Imported Spell details to mod %s:')
                        +u'\n') % fileName.s)
            for eid in sorted(changed):
                buff.write(u'* %s\n' % eid)
            balt.showLog(self.window,buff.getvalue(),_(u'Import Spell details'),

                         icons=bashBlue)
            buff.close()

#------------------------------------------------------------------------------
from ..patcher.utilities import IngredientDetails, CBash_IngredientDetails

class Mod_IngredientDetails_Export(_Mod_Export_Link):
    """Export Ingredient details from mod to text file."""
    askTitle = _(u'Export Ingredient details to:')
    csvFile = u'_Ingredients.csv'
    progressTitle = _(u'Export Ingredient details')
    text = _(u'Ingredients...')
    help = _(u'Export Ingredient details from mod to text file')

    def _parser(self):
        return CBash_IngredientDetails() if CBash else IngredientDetails()

class Mod_IngredientDetails_Import(_Mod_Import_Link):
    """Import Ingredient details from text file."""
    text = _(u'Ingredients...')
    help = _(u'Import Ingredient details from text file')

    def Execute(self,event):
        message = (_(u"Import Ingredient details from a text file.  This will replace existing the data on Ingredients with the same form ids and is not reversible!"))
        if not balt.askContinue(self.window,message,
            'bash.Ingredient.import.continue',
            _(u'Import Ingredients details')):
            return
        fileName = GPath(self.data[0])
        fileInfo = bosh.modInfos[fileName]
        textName = fileName.root+u'_Ingredients.csv'
        textDir = bosh.dirs['patches']
        #--File dialog
        textPath = balt.askOpen(self.window,_(u'Import Ingredient details from:'),
            textDir,textName,u'*_Ingredients.csv',mustExist=True)
        if not textPath: return
        (textDir,textName) = textPath.headTail
        #--Extension error check
        ext = textName.cext
        if ext != u'.csv':
            balt.showError(self.window,_(u'Source file must be a _Ingredients.csv file'))
            return
        #--Export
        changed = None
        with balt.Progress(_(u'Import Ingredient details')) as progress:
            if CBash:
                Ingredients = CBash_IngredientDetails()
            else:
                Ingredients = IngredientDetails()
            progress(0.1,_(u'Reading %s.') % textName.s)
            Ingredients.readFromText(textPath)
            progress(0.2,_(u'Applying to %s.') % fileName.s)
            changed = Ingredients.writeToMod(fileInfo)
            progress(1.0,_(u'Done.'))
        #--Log
        if not changed:
            balt.showOk(self.window,
                _(u'No relevant Ingredient details to import.'),
                _(u'Import Ingredient details'))
        else:
            buff = StringIO.StringIO()
            buff.write((_(u'Imported Ingredient details to mod %s:')
                        + u'\n') % fileName.s)
            for eid in sorted(changed):
                buff.write(u'* %s\n' % eid)
            balt.showLog(self.window,buff.getvalue(),
                _(u'Import Ingredient details'),icons=bashBlue)
            buff.close()

#------------------------------------------------------------------------------
