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

"""Patch dialog"""
import StringIO
import copy
import re
import time
import wx
from datetime import timedelta
from . import SetUAC, BashFrame
from .. import bosh, bolt, balt
from ..bass import Resources
from ..balt import staticText, vSizer, hSizer, spacer, Link, OkButton, \
    SelectAllButton, CancelButton, SaveAsButton, OpenButton, \
    RevertToSavedButton, RevertButton
from ..bolt import UncodedError, SubProgress, GPath, CancelError, BoltError, \
    SkipError, deprint, Path
from ..patcher import configIsCBash
from ..patcher.patch_files import PatchFile, CBash_PatchFile

# Final lists of gui patcher classes instances, initialized in
# gui_patchers.InitPatchers() based on game. These must be copied as needed.
gui_patchers = []       #--All patchers.
CBash_gui_patchers = [] #--All patchers (CBash mode).

class PatchDialog(balt.Dialog):
    """Bash Patch update dialog."""

    def __init__(self,parent,patchInfo,doCBash=None,importConfig=True):
        self.parent = parent
        if (doCBash or doCBash is None) and bosh.settings['bash.CBashEnabled']:
            doCBash = True
        else:
            doCBash = False
        self.doCBash = doCBash
        title = _(u'Update ') + patchInfo.name.s + [u'', u' (CBash)'][doCBash]
        size = balt.sizes.get(self.__class__.__name__, (500,600))
        super(PatchDialog, self).__init__(parent, title=title, size=size)
        self.SetSizeHints(400,300)
        #--Data
        groupOrder = dict([(group,index) for index,group in
            enumerate((_(u'General'),_(u'Importers'),_(u'Tweakers'),_(u'Special')))])
        patchConfigs = bosh.modInfos.table.getItem(patchInfo.name,'bash.patch.configs',{})
        # If the patch config isn't from the same mode (CBash/Python), try converting
        # it over to the current mode
        if configIsCBash(patchConfigs) != self.doCBash:
            if importConfig:
                patchConfigs = self.ConvertConfig(patchConfigs)
            else:
                patchConfigs = {}
        isFirstLoad = 0 == len(patchConfigs)
        self.patchInfo = patchInfo
        self.patchers = [copy.deepcopy(p) for p in
                         (CBash_gui_patchers if doCBash else gui_patchers)]
        self.patchers.sort(key=lambda a: a.__class__.name)
        self.patchers.sort(key=lambda a: groupOrder[a.__class__.group])
        for patcher in self.patchers:
            patcher.getConfig(patchConfigs) #--Will set patcher.isEnabled
            if u'UNDEFINED' in (patcher.__class__.group, patcher.__class__.group):
                raise UncodedError(u'Name or group not defined for: %s' % patcher.__class__.__name__)
            patcher.SetCallbackFns(self._CheckPatcher, self._BoldPatcher)
            patcher.SetIsFirstLoad(isFirstLoad)
        self.currentPatcher = None
        patcherNames = [patcher.getName() for patcher in self.patchers]
        #--GUI elements
        self.gExecute = OkButton(self, label=_(u'Build Patch'),onClick=self.Execute)
        SetUAC(self.gExecute)
        self.gSelectAll = SelectAllButton(self,label=_(u'Select All'),onClick=self.SelectAll)
        self.gDeselectAll = SelectAllButton(self,label=_(u'Deselect All'),onClick=self.DeselectAll)
        cancelButton = CancelButton(self)
        self.gPatchers = balt.listBox(self, choices=patcherNames,
                                      isSingle=True, kind='checklist')
        self.gExportConfig = SaveAsButton(self,label=_(u'Export'),onClick=self.ExportConfig)
        self.gImportConfig = OpenButton(self,label=_(u'Import'),onClick=self.ImportConfig)
        self.gRevertConfig = RevertToSavedButton(self,label=_(u'Revert To Saved'),onClick=self.RevertConfig)
        self.gRevertToDefault = RevertButton(self,label=_(u'Revert To Default'),onClick=self.DefaultConfig)
        for index,patcher in enumerate(self.patchers):
            self.gPatchers.Check(index,patcher.isEnabled)
        self.defaultTipText = _(u'Items that are new since the last time this patch was built are displayed in bold')
        self.gTipText = staticText(self,self.defaultTipText)
        #--Events
        self.Bind(wx.EVT_SIZE,self.OnSize)
        self.gPatchers.Bind(wx.EVT_LISTBOX, self.OnSelect)
        self.gPatchers.Bind(wx.EVT_CHECKLISTBOX, self.OnCheck)
        self.gPatchers.Bind(wx.EVT_MOTION,self.OnMouse)
        self.gPatchers.Bind(wx.EVT_LEAVE_WINDOW,self.OnMouse)
        self.gPatchers.Bind(wx.EVT_CHAR,self.OnChar)
        self.mouseItem = -1
        #--Layout
        self.gConfigSizer = gConfigSizer = vSizer()
        sizer = vSizer(
            (hSizer(
                (self.gPatchers,0,wx.EXPAND),
                (self.gConfigSizer,1,wx.EXPAND|wx.LEFT,4),
                ),1,wx.EXPAND|wx.ALL,4),
            (self.gTipText,0,wx.EXPAND|wx.ALL^wx.TOP,4),
            (wx.StaticLine(self),0,wx.EXPAND|wx.BOTTOM,4),
            (hSizer(
                spacer,
                (self.gExportConfig,0,wx.LEFT,4),
                (self.gImportConfig,0,wx.LEFT,4),
                (self.gRevertConfig,0,wx.LEFT,4),
                (self.gRevertToDefault,0,wx.LEFT,4),
                ),0,wx.EXPAND|wx.LEFT|wx.RIGHT|wx.BOTTOM,4),
            (hSizer(
                spacer,
                self.gExecute,
                (self.gSelectAll,0,wx.LEFT,4),
                (self.gDeselectAll,0,wx.LEFT,4),
                (cancelButton,0,wx.LEFT,4),
                ),0,wx.EXPAND|wx.LEFT|wx.RIGHT|wx.BOTTOM,4)
            )
        self.SetSizer(sizer)
        self.SetIcons(Resources.bashMonkey)
        #--Patcher panels
        for patcher in self.patchers:
            gConfigPanel = patcher.GetConfigPanel(self,gConfigSizer,self.gTipText)
            gConfigSizer.Show(gConfigPanel,False)
        self.gPatchers.Select(1)
        self.ShowPatcher(self.patchers[1])
        self.SetOkEnable()

    #--Core -------------------------------
    def SetOkEnable(self):
        """Sets enable state for Ok button."""
        for patcher in self.patchers:
            if patcher.isEnabled:
                return self.gExecute.Enable(True)
        self.gExecute.Enable(False)

    def ShowPatcher(self,patcher):
        """Show patcher panel."""
        gConfigSizer = self.gConfigSizer
        if patcher == self.currentPatcher: return
        if self.currentPatcher is not None:
            gConfigSizer.Show(self.currentPatcher.gConfigPanel,False)
        gConfigPanel = patcher.GetConfigPanel(self,gConfigSizer,self.gTipText)
        gConfigSizer.Show(gConfigPanel,True)
        self.Layout()
        patcher.Layout()
        self.currentPatcher = patcher

    def Execute(self,event=None): # TODO(ut): needs more work to reduce P/C differences to an absolute minimum
        """Do the patch."""
        Link.Frame.isPatching = True ##: hack - prevent
        # mod_links._Mod_Patch_Update from binding activation event
        # we really need a lock
        self.EndModalOK()
        patchFile = progress = None
        try:
            Link.Frame.BindRefresh(bind=False)
            patchName = self.patchInfo.name
            progress = balt.Progress(patchName.s,(u' '*60+u'\n'), abort=True)
            timer1 = time.clock()
            #--Save configs
            patchConfigs = {'ImportedMods':set()}
            for patcher in self.patchers:
                patcher.saveConfig(patchConfigs)
            bosh.modInfos.table.setItem(patchName,'bash.patch.configs',patchConfigs)
            #--Do it
            log = bolt.LogFile(StringIO.StringIO())
            patchers = [patcher for patcher in self.patchers if patcher.isEnabled]
            patchFile = CBash_PatchFile(patchName, patchers) if self.doCBash \
                   else PatchFile(self.patchInfo, patchers)
            patchFile.initData(SubProgress(progress,0,0.1)) #try to speed this up!
            if self.doCBash:
                #try to speed this up!
                patchFile.buildPatch(SubProgress(progress,0.1,0.9))
                #no speeding needed/really possible (less than 1/4 second even with large LO)
                patchFile.buildPatchLog(patchName,log,SubProgress(progress,0.95,0.99))
                #--Save
                progress.setCancel(False)
                progress(1.0,patchName.s+u'\n'+_(u'Saving...'))
                patchFile.save()
                fullName = self.patchInfo.getPath().tail
                patchTime = fullName.mtime
                try:
                    patchName.untemp()
                except WindowsError, werr:
                    while werr.winerror == 32 and self._retry(patchName.temp.s,
                                                              patchName.s):
                        try:
                            patchName.untemp()
                        except WindowsError, werr:
                            continue
                        break
                    else:
                        raise
                patchName.mtime = patchTime
            else:
                patchFile.initFactories(SubProgress(progress,0.1,0.2)) #no speeding needed/really possible (less than 1/4 second even with large LO)
                patchFile.scanLoadMods(SubProgress(progress,0.2,0.8)) #try to speed this up!
                patchFile.buildPatch(log,SubProgress(progress,0.8,0.9))#no speeding needed/really possible (less than 1/4 second even with large LO)
                #--Save
                progress.setCancel(False)
                progress(0.9,patchName.s+u'\n'+_(u'Saving...'))
                message = (_(u'Bash encountered and error when saving %(patchName)s.')
                           + u'\n\n' +
                           _(u'Either Bash needs Administrator Privileges to save the file, or the file is in use by another process such as TES4Edit.')
                           + u'\n' +
                           _(u'Please close any program that is accessing %(patchName)s, and provide Administrator Privileges if prompted to do so.')
                           + u'\n\n' +
                           _(u'Try again?')) % {'patchName':patchName.s}
                while True:
                    try:
                        patchFile.safeSave()
                    except (CancelError,SkipError,WindowsError) as error:
                        if isinstance(error,WindowsError) and error.winerror != 32:
                            raise
                        if balt.askYes(self,message,_(u'Bash Patch - Save Error')):
                            continue
                        raise
                    break
            #--Cleanup
            self.patchInfo.refresh()
            #--Done
            progress.Destroy(); progress = None
            timer2 = time.clock()
            #--Readme and log
            log.setHeader(None)
            log(u'{{CSS:wtxt_sand_small.css}}')
            logValue = log.out.getvalue()
            log.out.close()
            timerString = unicode(timedelta(seconds=round(timer2 - timer1, 3))).rstrip(u'0')
            logValue = re.sub(u'TIMEPLACEHOLDER', timerString, logValue, 1)
            readme = bosh.modInfos.dir.join(u'Docs',patchName.sroot+u'.txt')
            docsDir = bosh.settings.get('balt.WryeLog.cssDir', GPath(u''))
            if self.doCBash: ##: eliminate this if/else
                with readme.open('w',encoding='utf-8') as file:
                    file.write(logValue)
                #--Convert log/readme to wtxt and show log
                bolt.WryeText.genHtml(readme,None,docsDir)
            else:
                tempReadmeDir = Path.tempDir().join(u'Docs')
                tempReadme = tempReadmeDir.join(patchName.sroot+u'.txt')
                #--Write log/readme to temp dir first
                with tempReadme.open('w',encoding='utf-8-sig') as file:
                    file.write(logValue)
                #--Convert log/readmeto wtxt
                bolt.WryeText.genHtml(tempReadme,None,docsDir)
                #--Try moving temp log/readme to Docs dir
                try:
                    balt.shellMove(tempReadmeDir, bosh.dirs['mods'],
                                   parent=self)
                except (CancelError,SkipError):
                    # User didn't allow UAC, move to My Games directory instead
                    balt.shellMove([tempReadme, tempReadme.root + u'.html'],
                                   bosh.dirs['saveBase'], parent=self)
                    readme = bosh.dirs['saveBase'].join(readme.tail)
                #finally:
                #    tempReadmeDir.head.rmtree(safety=tempReadmeDir.head.stail)
            bosh.modInfos.table.setItem(patchName,'doc',readme)
            balt.playSound(self.parent,bosh.inisettings['SoundSuccess'].s)
            balt.showWryeLog(self.parent,readme.root+u'.html',patchName.s,icons=Resources.bashBlue)
            #--Select?
            count, message = 0, _(u'Activate %s?') % patchName.s
            if bosh.modInfos.isSelected(patchName) or (
                        bosh.inisettings['PromptActivateBashedPatch'] and
                        balt.askYes(self.parent, message, patchName.s)):
                try:
                    oldFiles = bosh.modInfos.ordered[:]
                    bosh.modInfos.select(patchName)
                    changedFiles = bolt.listSubtract(bosh.modInfos.ordered,oldFiles)
                    count = len(changedFiles)
                    if count > 1: Link.Frame.SetStatusInfo(
                            _(u'Masters Activated: ') + unicode(count - 1))
                    # bosh.modInfos.refreshInfoLists() # covered in refreshFile
                except bosh.PluginsFullError:
                    balt.showError(self, _(
                        u'Unable to add mod %s because load list is full.')
                                   % patchName.s)
            bosh.modInfos.refreshFile(patchName) # (ut) not sure if needed
            BashFrame.modList.RefreshUI(refreshSaves=bool(count))
        except bolt.FileEditError, error:
            balt.playSound(self.parent,bosh.inisettings['SoundError'].s)
            balt.showError(self,u'%s'%error,_(u'File Edit Error'))
        except CancelError:
            pass
        except BoltError, error:
            balt.playSound(self.parent,bosh.inisettings['SoundError'].s)
            balt.showError(self,u'%s'%error,_(u'Processing Error'))
        except:
            balt.playSound(self.parent,bosh.inisettings['SoundError'].s)
            raise
        finally:
            Link.Frame.isPatching = False
            Link.Frame.BindRefresh(bind=True)
            if self.doCBash:
                try: patchFile.Current.Close()
                except: pass
            if progress: progress.Destroy()

    def _retry(self, old, new):
        return balt.askYes(self,
            _(u'Bash encountered an error when renaming %s to %s.') + u'\n\n' +
            _(u'The file is in use by another process such as TES4Edit.') +
            u'\n' + _(u'Please close the other program that is accessing %s.')
            + u'\n\n' + _(u'Try again?') % (old.s, new.s, new.s),
             _(u'Bash Patch - Save Error'))

    def SaveConfig(self,event=None):
        """Save the configuration"""
        patchName = self.patchInfo.name
        patchConfigs = {'ImportedMods':set()}
        for patcher in self.patchers:
            patcher.saveConfig(patchConfigs)
        bosh.modInfos.table.setItem(patchName,'bash.patch.configs',patchConfigs)

    def ExportConfig(self,event=None):
        """Export the configuration to a user selected dat file."""
        patchName = self.patchInfo.name + _(u'_Configuration.dat')
        textDir = bosh.dirs['patches']
        textDir.makedirs()
        #--File dialog
        textPath = balt.askSave(self.parent,_(u'Export Bashed Patch configuration to:'),
                                textDir,patchName, u'*Configuration.dat')
        if not textPath: return
        pklPath = textPath+u'.pkl'
        table = bolt.Table(bosh.PickleDict(textPath, pklPath))
        patchConfigs = {'ImportedMods':set()}
        for patcher in self.patchers:
            patcher.saveConfig(patchConfigs)
        table.setItem(GPath(u'Saved Bashed Patch Configuration (%s)' % ([u'Python',u'CBash'][self.doCBash])),'bash.patch.configs',patchConfigs)
        table.save()

    def ImportConfig(self,event=None):
        """Import the configuration to a user selected dat file."""
        patchName = self.patchInfo.name + _(u'_Configuration.dat')
        textDir = bosh.dirs['patches']
        textDir.makedirs()
        #--File dialog
        textPath = balt.askOpen(self.parent,_(u'Import Bashed Patch configuration from:'),textDir,patchName, u'*.dat',mustExist=True)
        if not textPath: return
        pklPath = textPath+u'.pkl'
        table = bolt.Table(bosh.PickleDict(
            textPath, pklPath))
        #try the current Bashed Patch mode.
        patchConfigs = table.getItem(GPath(u'Saved Bashed Patch Configuration (%s)' % ([u'Python',u'CBash'][self.doCBash])),'bash.patch.configs',{})
        if not patchConfigs: #try the old format:
            patchConfigs = table.getItem(GPath(u'Saved Bashed Patch Configuration'),'bash.patch.configs',{})
            if patchConfigs:
                if configIsCBash(patchConfigs) != self.doCBash:
                    patchConfigs = self.UpdateConfig(patchConfigs)
            else:   #try the non-current Bashed Patch mode:
                patchConfigs = table.getItem(GPath(u'Saved Bashed Patch Configuration (%s)' % ([u'CBash',u'Python'][self.doCBash])),'bash.patch.configs',{})
                if patchConfigs:
                    patchConfigs = self.UpdateConfig(patchConfigs)
        if patchConfigs is None:
            patchConfigs = {}
        for index,patcher in enumerate(self.patchers):
            patcher.SetIsFirstLoad(False)
            patcher.getConfig(patchConfigs)
            self.gPatchers.Check(index,patcher.isEnabled)
            if hasattr(patcher, 'gList'):
                if patcher.getName() == 'Leveled Lists': continue #not handled yet!
                for index, item in enumerate(patcher.items):
                    try:
                        patcher.gList.Check(index,patcher.configChecks[item])
                    except KeyError: pass#deprint(_(u'item %s not in saved configs') % (item))
            if hasattr(patcher, 'gTweakList'):
                for index, item in enumerate(patcher.tweaks):
                    try:
                        patcher.gTweakList.Check(index,item.isEnabled)
                        patcher.gTweakList.SetString(index,item.getListLabel())
                    except: deprint(_(u'item %s not in saved configs') % item)
        self.SetOkEnable()

    def UpdateConfig(self,patchConfigs,event=None):
        if not balt.askYes(self.parent,
            _(u"Wrye Bash detects that the selected file was saved in Bash's %s mode, do you want Wrye Bash to attempt to adjust the configuration on import to work with %s mode (Good chance there will be a few mistakes)? (Otherwise this import will have no effect.)")
                % ([u'CBash',u'Python'][self.doCBash],
                   [u'Python',u'CBash'][self.doCBash])):
            return
        if self.doCBash:
            PatchFile.patchTime = CBash_PatchFile.patchTime
            PatchFile.patchName = CBash_PatchFile.patchName
        else:
            CBash_PatchFile.patchTime = PatchFile.patchTime
            CBash_PatchFile.patchName = PatchFile.patchName
        return self.ConvertConfig(patchConfigs)

    @staticmethod
    def ConvertConfig(patchConfigs):
        newConfig = {}
        for key in patchConfigs:
            if key in otherPatcherDict:
                newConfig[otherPatcherDict[key]] = patchConfigs[key]
            else:
                newConfig[key] = patchConfigs[key]
        return newConfig

    def RevertConfig(self,event=None):
        """Revert configuration back to saved"""
        patchConfigs = bosh.modInfos.table.getItem(self.patchInfo.name,'bash.patch.configs',{})
        if configIsCBash(patchConfigs) and not self.doCBash:
            patchConfigs = self.ConvertConfig(patchConfigs)
        for index,patcher in enumerate(self.patchers):
            patcher.SetIsFirstLoad(False)
            patcher.getConfig(patchConfigs)
            self.gPatchers.Check(index,patcher.isEnabled)
            if hasattr(patcher, 'gList'):
                if patcher.getName() == 'Leveled Lists': continue #not handled yet!
                for index, item in enumerate(patcher.items):
                    try: patcher.gList.Check(index,patcher.configChecks[item])
                    except Exception, err: deprint(_(u'Error reverting Bashed patch configuration (error is: %s). Item %s skipped.') % (err,item))
            if hasattr(patcher, 'gTweakList'):
                for index, item in enumerate(patcher.tweaks):
                    try:
                        patcher.gTweakList.Check(index,item.isEnabled)
                        patcher.gTweakList.SetString(index,item.getListLabel())
                    except Exception, err: deprint(_(u'Error reverting Bashed patch configuration (error is: %s). Item %s skipped.') % (err,item))
        self.SetOkEnable()

    def DefaultConfig(self,event=None):
        """Revert configuration back to default"""
        patchConfigs = {}
        for index,patcher in enumerate(self.patchers):
            patcher.SetIsFirstLoad(True)
            patcher.getConfig(patchConfigs)
            self.gPatchers.Check(index,patcher.isEnabled)
            if hasattr(patcher, 'gList'):
                patcher.SetItems(patcher.getAutoItems())
            if hasattr(patcher, 'gTweakList'):
                for index, item in enumerate(patcher.tweaks):
                    try:
                        patcher.gTweakList.Check(index,item.isEnabled)
                        patcher.gTweakList.SetString(index,item.getListLabel())
                    except Exception, err: deprint(_(u'Error reverting Bashed patch configuration (error is: %s). Item %s skipped.') % (err,item))
        self.SetOkEnable()

    def SelectAll(self,event=None):
        """Select all patchers and entries in patchers with child entries."""
        for index,patcher in enumerate(self.patchers):
            self.gPatchers.Check(index,True)
            patcher.isEnabled = True
            if hasattr(patcher, 'gList'):
                if patcher.getName() == 'Leveled Lists': continue
                for index, item in enumerate(patcher.items):
                    patcher.gList.Check(index,True)
                    patcher.configChecks[item] = True
            if hasattr(patcher, 'gTweakList'):
                for index, item in enumerate(patcher.tweaks):
                    patcher.gTweakList.Check(index,True)
                    item.isEnabled = True
            self.gExecute.Enable(True)

    def DeselectAll(self,event=None):
        """Deselect all patchers and entries in patchers with child entries."""
        for index,patcher in enumerate(self.patchers):
            self.gPatchers.Check(index,False)
            patcher.isEnabled = False
            if patcher.getName() in [_(u'Leveled Lists'),_(u"Alias Mod Names")]: continue # special case that one.
            if hasattr(patcher, 'gList'):
                patcher.gList.SetChecked([])
                patcher.OnListCheck()
            if hasattr(patcher, 'gTweakList'):
                patcher.gTweakList.SetChecked([])
        self.gExecute.Enable(False)

    #--GUI --------------------------------
    def OnSize(self,event): ##: needed ? event.Skip() ??
        balt.sizes[self.__class__.__name__] = self.GetSizeTuple()
        self.Layout()
        self.currentPatcher.Layout()

    def OnSelect(self,event):
        """Responds to patchers list selection."""
        itemDex = event.GetSelection()
        self.ShowPatcher(self.patchers[itemDex])

    def _CheckPatcher(self,patcher):
        """Remotely enables a patcher.  Called from a particular patcher's OnCheck method."""
        index = self.patchers.index(patcher)
        self.gPatchers.Check(index)
        patcher.isEnabled = True
        self.SetOkEnable()

    def _BoldPatcher(self,patcher):
        """Set the patcher label to bold font.  Called from a patcher when it realizes it has something new in its list"""
        index = self.patchers.index(patcher)
        font = self.gPatchers.GetFont()
        font.SetWeight(wx.FONTWEIGHT_BOLD)
        self.gPatchers.SetItemFont(index, font)

    def OnCheck(self,event):
        """Toggle patcher activity state."""
        index = event.GetSelection()
        patcher = self.patchers[index]
        patcher.isEnabled = self.gPatchers.IsChecked(index)
        self.gPatchers.SetSelection(index)
        self.ShowPatcher(patcher)
        self.SetOkEnable()

    def OnMouse(self,event):
        """Check mouse motion to detect right click event."""
        if event.Moving():
            mouseItem = (event.m_y/self.gPatchers.GetItemHeight() +
                self.gPatchers.GetScrollPos(wx.VERTICAL))
            if mouseItem != self.mouseItem:
                self.mouseItem = mouseItem
                self.MouseEnteredItem(mouseItem)
        elif event.Leaving():
            self.gTipText.SetLabel(self.defaultTipText)
            self.mouseItem = -1
        event.Skip()

    def MouseEnteredItem(self,item):
        """Show tip text when changing item."""
        #--Following isn't displaying correctly.
        if item < len(self.patchers):
            patcherClass = self.patchers[item].__class__
            tip = patcherClass.tip or re.sub(ur'\..*',u'.',patcherClass.text.split(u'\n')[0],flags=re.U)
            self.gTipText.SetLabel(tip)
        else:
            self.gTipText.SetLabel(self.defaultTipText)

    def OnChar(self,event):
        """Keyboard input to the patchers list box"""
        if event.GetKeyCode() == 1 and event.CmdDown(): # Ctrl+'A'
            patcher = self.currentPatcher
            if patcher is not None:
                if event.ShiftDown():
                    patcher.DeselectAll()
                else:
                    patcher.SelectAll()
                return
        event.Skip()

# Used in ConvertConfig to convert between C and P *gui* patchers config - so
# it belongs with gui_patchers (and not with patchers/ package). Still a hack
otherPatcherDict = {
    'AliasesPatcher' : 'CBash_AliasesPatcher',
    'AssortedTweaker' : 'CBash_AssortedTweaker',
    'PatchMerger' : 'CBash_PatchMerger',
    'KFFZPatcher' : 'CBash_KFFZPatcher',
    'ActorImporter' : 'CBash_ActorImporter',
    'DeathItemPatcher' : 'CBash_DeathItemPatcher',
    'NPCAIPackagePatcher' : 'CBash_NPCAIPackagePatcher',
    'UpdateReferences' : 'CBash_UpdateReferences',
    'CellImporter' : 'CBash_CellImporter',
    'ClothesTweaker' : 'CBash_ClothesTweaker',
    'GmstTweaker' : 'CBash_GmstTweaker',
    'GraphicsPatcher' : 'CBash_GraphicsPatcher',
    'ImportFactions' : 'CBash_ImportFactions',
    'ImportInventory' : 'CBash_ImportInventory',
    'SpellsPatcher' : 'CBash_SpellsPatcher',
    'TweakActors' : 'CBash_TweakActors',
    'ImportRelations' : 'CBash_ImportRelations',
    'ImportScripts' : 'CBash_ImportScripts',
    'ImportActorsSpells' : 'CBash_ImportActorsSpells',
    'ListsMerger' : 'CBash_ListsMerger',
    'NamesPatcher' : 'CBash_NamesPatcher',
    'NamesTweaker' : 'CBash_NamesTweaker',
    'NpcFacePatcher' : 'CBash_NpcFacePatcher',
    'RacePatcher' : 'CBash_RacePatcher',
    'RoadImporter' : 'CBash_RoadImporter',
    'SoundPatcher' : 'CBash_SoundPatcher',
    'StatsPatcher' : 'CBash_StatsPatcher',
    'ContentsChecker' : 'CBash_ContentsChecker',
    'CBash_AliasesPatcher' : 'AliasesPatcher',
    'CBash_AssortedTweaker' : 'AssortedTweaker',
    'CBash_PatchMerger' : 'PatchMerger',
    'CBash_KFFZPatcher' : 'KFFZPatcher',
    'CBash_ActorImporter' : 'ActorImporter',
    'CBash_DeathItemPatcher' : 'DeathItemPatcher',
    'CBash_NPCAIPackagePatcher' : 'NPCAIPackagePatcher',
    'CBash_UpdateReferences' : 'UpdateReferences',
    'CBash_CellImporter' : 'CellImporter',
    'CBash_ClothesTweaker' : 'ClothesTweaker',
    'CBash_GmstTweaker' : 'GmstTweaker',
    'CBash_GraphicsPatcher' : 'GraphicsPatcher',
    'CBash_ImportFactions' : 'ImportFactions',
    'CBash_ImportInventory' : 'ImportInventory',
    'CBash_SpellsPatcher' : 'SpellsPatcher',
    'CBash_TweakActors' : 'TweakActors',
    'CBash_ImportRelations' : 'ImportRelations',
    'CBash_ImportScripts' : 'ImportScripts',
    'CBash_ImportActorsSpells' : 'ImportActorsSpells',
    'CBash_ListsMerger' : 'ListsMerger',
    'CBash_NamesPatcher' : 'NamesPatcher',
    'CBash_NamesTweaker' : 'NamesTweaker',
    'CBash_NpcFacePatcher' : 'NpcFacePatcher',
    'CBash_RacePatcher' : 'RacePatcher',
    'CBash_RoadImporter' : 'RoadImporter',
    'CBash_SoundPatcher' : 'SoundPatcher',
    'CBash_StatsPatcher' : 'StatsPatcher',
    'CBash_ContentsChecker' : 'ContentsChecker',
    }
