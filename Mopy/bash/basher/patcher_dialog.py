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

"""Patch dialog"""
import StringIO
import copy
import errno
import re
import time
import wx
from datetime import timedelta
from . import SetUAC, BashFrame
from .. import bass, bosh, bolt, balt, env, load_order
from ..bass import Resources
from ..balt import StaticText, vSizer, hSizer, hspacer, Link, OkButton, \
    SelectAllButton, CancelButton, SaveAsButton, OpenButton, \
    RevertToSavedButton, RevertButton, hspace, vspace
from ..bolt import SubProgress, GPath, CancelError, BoltError, SkipError, Path
from ..patcher import configIsCBash, exportConfig
from ..patcher.patch_files import PatchFile, CBash_PatchFile
from ..patcher.base import AListPatcher

# Final lists of gui patcher classes instances, initialized in
# gui_patchers.InitPatchers() based on game. These must be copied as needed.
PBash_gui_patchers = [] #--All gui patchers classes for this game
CBash_gui_patchers = [] #--All gui patchers classes for this game (CBash mode)

class PatchDialog(balt.Dialog):
    """Bash Patch update dialog.

    :type patchers: list[basher.gui_patchers._PatcherPanel]
    """

    def __init__(self,parent,patchInfo,doCBash=None,importConfig=True):
        self.parent = parent
        if (doCBash or doCBash is None) and bass.settings['bash.CBashEnabled']:
            doCBash = True
        else:
            doCBash = False
        self.doCBash = doCBash
        title = _(u'Update ') + patchInfo.name.s + [u'', u' (CBash)'][doCBash]
        size = balt.sizes.get(self.__class__.__name__, (500,600))
        super(PatchDialog, self).__init__(parent, title=title, size=size)
        self.SetSizeHints(400,300)
        #--Data
        AListPatcher.list_patches_dir()
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
        self.patchers = [copy.deepcopy(p) for p in (
            CBash_gui_patchers if doCBash else PBash_gui_patchers)]
        self.patchers.sort(key=lambda a: a.__class__.name)
        self.patchers.sort(key=lambda a: groupOrder[a.__class__.group])
        for patcher in self.patchers:
            patcher.getConfig(patchConfigs) #--Will set patcher.isEnabled
            patcher.SetIsFirstLoad(isFirstLoad)
        self.currentPatcher = None
        patcherNames = [patcher.getName() for patcher in self.patchers]
        #--GUI elements
        self.gExecute = OkButton(self, label=_(u'Build Patch'),
                                 onButClick=self.PatchExecute)
        SetUAC(self.gExecute)
        self.gSelectAll = SelectAllButton(self, label=_(u'Select All'),
                                          onButClick=self.SelectAll)
        self.gDeselectAll = SelectAllButton(self, label=_(u'Deselect All'),
                                            onButClick=self.DeselectAll)
        cancelButton = CancelButton(self)
        self.gPatchers = balt.listBox(self, choices=patcherNames,
                                      isSingle=True, kind='checklist',
                                      onSelect=self.OnSelect,
                                      onCheck=self.OnCheck)
        self.gExportConfig = SaveAsButton(self, label=_(u'Export'),
                                          onButClick=self.ExportConfig)
        self.gImportConfig = OpenButton(self, label=_(u'Import'),
                                        onButClick=self.ImportConfig)
        self.gRevertConfig = RevertToSavedButton(
            self, label=_(u'Revert To Saved'), onButClick=self.RevertConfig)
        self.gRevertToDefault = RevertButton(
            self, label=_(u'Revert To Default'), onButClick=self.DefaultConfig)
        for index,patcher in enumerate(self.patchers):
            self.gPatchers.Check(index,patcher.isEnabled)
        self.defaultTipText = _(u'Items that are new since the last time this patch was built are displayed in bold')
        self.gTipText = StaticText(self,self.defaultTipText)
        #--Events
        self.Bind(wx.EVT_SIZE,self.OnSize) # save dialog size
        self.gPatchers.Bind(wx.EVT_MOTION,self.OnMouse)
        self.gPatchers.Bind(wx.EVT_LEAVE_WINDOW,self.OnMouse)
        self.gPatchers.Bind(wx.EVT_CHAR,self.OnChar)
        self.mouse_dex = -1
        #--Layout
        self.gConfigSizer = gConfigSizer = vSizer()
        sizer = vSizer(
            (hSizer(
                (self.gPatchers,0,wx.EXPAND), hspace(),
                (self.gConfigSizer,1,wx.EXPAND),
                ),1,wx.EXPAND|wx.ALL,4),
            (self.gTipText,0,wx.EXPAND|wx.ALL^wx.TOP,4),
            (wx.StaticLine(self),0,wx.EXPAND), vspace(),
            (hSizer(hspacer,
                hspace(), self.gExportConfig,
                hspace(), self.gImportConfig,
                hspace(), self.gRevertConfig,
                hspace(), self.gRevertToDefault,
                ),0,wx.EXPAND|wx.ALL^wx.TOP,4),
            (hSizer(hspacer,
                self.gExecute,
                hspace(), self.gSelectAll,
                hspace(), self.gDeselectAll,
                hspace(), cancelButton,
                ),0,wx.EXPAND|wx.ALL^wx.TOP,4)
            )
        self.SetSizer(sizer)
        self.SetIcons(Resources.bashMonkey)
        #--Patcher panels
        for patcher in self.patchers:
            gConfigPanel = patcher.GetConfigPanel(self,gConfigSizer,self.gTipText)
            gConfigSizer.Show(gConfigPanel,False)
        initial_select = min(len(self.patchers)-1,1)
        if initial_select >= 0:
            self.gPatchers.SetSelection(initial_select) # callback not fired
            self.ShowPatcher(self.patchers[initial_select]) # so this is needed
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

    @balt.conversation
    def PatchExecute(self): # TODO(ut): needs more work to reduce P/C differences to an absolute minimum
        """Do the patch."""
        self.EndModalOK()
        patchFile = progress = None
        try:
            patch_name = self.patchInfo.name
            progress = balt.Progress(patch_name.s,(u' '*60+u'\n'), abort=True)
            timer1 = time.clock()
            #--Save configs
            self._saveConfig(patch_name)
            #--Do it
            log = bolt.LogFile(StringIO.StringIO())
            patchers = [patcher for patcher in self.patchers if patcher.isEnabled]
            patchFile = CBash_PatchFile(patch_name, patchers) if self.doCBash \
                   else PatchFile(self.patchInfo, patchers)
            patchFile.init_patchers_data(SubProgress(progress, 0, 0.1)) #try to speed this up!
            if self.doCBash:
                #try to speed this up!
                patchFile.buildPatch(SubProgress(progress,0.1,0.9))
                #no speeding needed/really possible (less than 1/4 second even with large LO)
                patchFile.buildPatchLog(log, SubProgress(progress, 0.95, 0.99))
                #--Save
                progress.setCancel(False)
                progress(1.0,patch_name.s+u'\n'+_(u'Saving...'))
                self._save_cbash(patchFile, patch_name)
            else:
                patchFile.initFactories(SubProgress(progress,0.1,0.2)) #no speeding needed/really possible (less than 1/4 second even with large LO)
                patchFile.scanLoadMods(SubProgress(progress,0.2,0.8)) #try to speed this up!
                patchFile.buildPatch(log,SubProgress(progress,0.8,0.9))#no speeding needed/really possible (less than 1/4 second even with large LO)
                #--Save
                progress.setCancel(False)
                progress(0.9,patch_name.s+u'\n'+_(u'Saving...'))
                self._save_pbash(patchFile, patch_name)
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
            readme = bosh.modInfos.store_dir.join(u'Docs', patch_name.sroot + u'.txt')
            docsDir = bass.settings.get('balt.WryeLog.cssDir', GPath(u''))
            if self.doCBash: ##: eliminate this if/else
                with readme.open('w',encoding='utf-8') as file:
                    file.write(logValue)
                #--Convert log/readme to wtxt and show log
                bolt.WryeText.genHtml(readme,None,docsDir)
            else:
                tempReadmeDir = Path.tempDir().join(u'Docs')
                tempReadme = tempReadmeDir.join(patch_name.sroot+u'.txt')
                #--Write log/readme to temp dir first
                with tempReadme.open('w',encoding='utf-8-sig') as file:
                    file.write(logValue)
                #--Convert log/readmeto wtxt
                bolt.WryeText.genHtml(tempReadme,None,docsDir)
                #--Try moving temp log/readme to Docs dir
                try:
                    env.shellMove(tempReadmeDir, bass.dirs['mods'],
                                  parent=self)
                except (CancelError,SkipError):
                    # User didn't allow UAC, move to My Games directory instead
                    env.shellMove([tempReadme, tempReadme.root + u'.html'],
                                  bass.dirs['saveBase'], parent=self)
                    readme = bass.dirs['saveBase'].join(readme.tail)
                #finally:
                #    tempReadmeDir.head.rmtree(safety=tempReadmeDir.head.stail)
            bosh.modInfos.table.setItem(patch_name,'doc',readme)
            balt.playSound(self.parent, bass.inisettings['SoundSuccess'].s)
            balt.showWryeLog(self.parent,readme.root+u'.html',patch_name.s,icons=Resources.bashBlue)
            #--Select?
            count, message = 0, _(u'Activate %s?') % patch_name.s
            if load_order.cached_is_active(patch_name) or (
                        bass.inisettings['PromptActivateBashedPatch'] and
                        balt.askYes(self.parent, message, patch_name.s)):
                try:
                    changedFiles = bosh.modInfos.lo_activate(patch_name,
                                                             doSave=True)
                    count = len(changedFiles)
                    if count > 1: Link.Frame.SetStatusInfo(
                            _(u'Masters Activated: ') + unicode(count - 1))
                except bosh.PluginsFullError:
                    balt.showError(self, _(
                        u'Unable to add mod %s because load list is full.')
                                   % patch_name.s)
            bosh.modInfos.refreshFile(patch_name)
            BashFrame.modList.RefreshUI(refreshSaves=bool(count))
        except bolt.FileEditError as error:
            balt.playSound(self.parent, bass.inisettings['SoundError'].s)
            balt.showError(self,u'%s'%error,_(u'File Edit Error'))
        except CancelError:
            pass
        except BoltError as error:
            balt.playSound(self.parent, bass.inisettings['SoundError'].s)
            balt.showError(self,u'%s'%error,_(u'Processing Error'))
        except:
            balt.playSound(self.parent, bass.inisettings['SoundError'].s)
            raise
        finally:
            if self.doCBash:
                try: patchFile.Current.Close()
                except: pass
            if progress: progress.Destroy()

    def _save_pbash(self, patchFile, patch_name):
        while True:
            try:
                # FIXME will keep displaying a bogus UAC prompt if file is
                # locked - aborting bogus UAC dialog raises SkipError() in
                # shellMove, not sure if ever a Windows or Cancel are raised
                patchFile.safeSave()
                return
            except (CancelError, SkipError, OSError) as werr:
                if isinstance(werr, OSError) and werr.errno != errno.EACCES:
                    raise
                if self._pretry(patch_name):
                    continue
                raise # will raise the SkipError which is correctly processed

    def _save_cbash(self, patchFile, patch_name):
        patchFile.save()
        patchTime = self.patchInfo.mtime
        while True:
            try:
                patch_name.untemp()
                patch_name.mtime = patchTime
                return
            except OSError as werr:
                if werr.errno == errno.EACCES:
                    if not self._cretry(patch_name):
                        raise SkipError() # caught - Processing error displayed
                    continue
                raise

    def _pretry(self, patch_name):
        return balt.askYes(self, (
            _(u'Bash encountered and error when saving %(patch_name)s.') +
            u'\n\n' + _(u'Either Bash needs Administrator Privileges to '
            u'save the file, or the file is in use by another process '
            u'such as TES4Edit.') + u'\n' + _(u'Please close any program '
            u'that is accessing %(patch_name)s, and provide Administrator '
            u'Privileges if prompted to do so.') + u'\n\n' +
            _(u'Try again?')) % {'patch_name': patch_name.s},
                           _(u'Bash Patch - Save Error'))

    def _cretry(self, patch_name):
        return balt.askYes(self, (
            _(u'Bash encountered an error when renaming %s to %s.') + u'\n\n' +
            _(u'The file is in use by another process such as TES4Edit.') +
            u'\n' + _(u'Please close the other program that is accessing %s.')
            + u'\n\n' + _(u'Try again?')) % (
                               patch_name.temp.s, patch_name.s, patch_name.s),
                           _(u'Bash Patch - Save Error'))

    def __config(self):
        config = {'ImportedMods': set()}
        for patcher in self.patchers: patcher.saveConfig(config)
        return config

    def _saveConfig(self, patch_name):
        """Save the configuration"""
        config = self.__config()
        bosh.modInfos.table.setItem(patch_name, 'bash.patch.configs', config)

    def ExportConfig(self):
        """Export the configuration to a user selected dat file."""
        config = self.__config()
        exportConfig(patch_name=self.patchInfo.name, config=config,
                     isCBash=self.doCBash, win=self.parent,
                     outDir=bass.dirs['patches'])

    __old_key = GPath(u'Saved Bashed Patch Configuration')
    __new_key = u'Saved Bashed Patch Configuration (%s)'
    def ImportConfig(self):
        """Import the configuration from a user selected dat file."""
        config_dat = self.patchInfo.name + _(u'_Configuration.dat')
        textDir = bass.dirs['patches']
        textDir.makedirs()
        #--File dialog
        textPath = balt.askOpen(self.parent,
                                _(u'Import Bashed Patch configuration from:'),
                                textDir, config_dat, u'*.dat', mustExist=True)
        if not textPath: return
        table = bolt.Table(bolt.PickleDict(textPath))
        # try the current Bashed Patch mode.
        patchConfigs = table.getItem(
            GPath(self.__new_key % ([u'Python', u'CBash'][self.doCBash])),
            'bash.patch.configs', {})
        convert = False
        if not patchConfigs: # try the non-current Bashed Patch mode
            patchConfigs = table.getItem(
                GPath(self.__new_key % ([u'CBash', u'Python'][self.doCBash])),
                'bash.patch.configs', {})
            convert = bool(patchConfigs)
        if not patchConfigs: # try the old format
            patchConfigs = table.getItem(self.__old_key, 'bash.patch.configs',
                                         {})
            convert = configIsCBash(patchConfigs) != self.doCBash
        if not patchConfigs:
            balt.showWarning(_(u'No patch config data found in %s') % textPath,
                             _(u'Import Config'))
            return
        if convert:
            patchConfigs = self.UpdateConfig(patchConfigs)
            if patchConfigs is None: return
        self._load_config(patchConfigs)

    def _load_config(self, patchConfigs, set_first_load=False, default=False):
        for index, patcher in enumerate(self.patchers):
            patcher.import_config(patchConfigs, set_first_load=set_first_load,
                                  default=default)
            self.gPatchers.Check(index, patcher.isEnabled)
        self.SetOkEnable()

    def UpdateConfig(self, patchConfigs):
        if not balt.askYes(self.parent, _(
            u"Wrye Bash detects that the selected file was saved in Bash's "
            u"%s mode, do you want Wrye Bash to attempt to adjust the "
            u"configuration on import to work with %s mode (Good chance "
            u"there will be a few mistakes)? (Otherwise this import will "
            u"have no effect.)") % ([u'CBash', u'Python'][self.doCBash],
                                    [u'Python', u'CBash'][self.doCBash])):
            return
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

    def RevertConfig(self):
        """Revert configuration back to saved"""
        patchConfigs = bosh.modInfos.table.getItem(self.patchInfo.name,
                                                   'bash.patch.configs', {})
        if configIsCBash(patchConfigs) and not self.doCBash:
            patchConfigs = self.ConvertConfig(patchConfigs)
        self._load_config(patchConfigs)

    def DefaultConfig(self):
        """Revert configuration back to default"""
        self._load_config({}, set_first_load=True, default=True)

    def SelectAll(self):
        """Select all patchers and entries in patchers with child entries."""
        for index,patcher in enumerate(self.patchers):
            self.gPatchers.Check(index,True)
            patcher.mass_select()
        self.gExecute.Enable(True)

    def DeselectAll(self):
        """Deselect all patchers and entries in patchers with child entries."""
        for index,patcher in enumerate(self.patchers):
            self.gPatchers.Check(index,False)
            patcher.mass_select(select=False)
        self.gExecute.Enable(False)

    #--GUI --------------------------------
    def OnSize(self,event):
        balt.sizes[self.__class__.__name__] = tuple(self.GetSize())
        event.Skip()

    def OnSelect(self,event):
        """Responds to patchers list selection."""
        itemDex = event.GetSelection()
        self.ShowPatcher(self.patchers[itemDex])
        self.gPatchers.SetSelection(itemDex)

    def CheckPatcher(self, patcher):
        """Enable a patcher - Called from a patcher's OnCheck method."""
        index = self.patchers.index(patcher)
        self.gPatchers.Check(index)
        self.SetOkEnable()

    def BoldPatcher(self, patcher):
        """Set the patcher label to bold font.  Called from a patcher when
        it realizes it has something new in its list"""
        index = self.patchers.index(patcher)
        get_font = self.gPatchers.GetFont()
        self.gPatchers.SetItemFont(index, balt.Font.Style(get_font, bold=True))

    def OnCheck(self,event):
        """Toggle patcher activity state."""
        index = event.GetSelection()
        patcher = self.patchers[index]
        patcher.isEnabled = self.gPatchers.IsChecked(index)
        self.gPatchers.SetSelection(index)
        self.ShowPatcher(patcher) # SetSelection does not fire the callback
        self.SetOkEnable()

    def OnMouse(self,event):
        """Show tip text when changing item."""
        mouseItem = -1
        if event.Moving():
            mouseItem = self.gPatchers.HitTest(event.GetPosition())
            if mouseItem != self.mouse_dex:
                self.mouse_dex = mouseItem
        elif event.Leaving():
            pass # will be set to defaultTipText
        if 0 <= mouseItem < len(self.patchers):
            patcherClass = self.patchers[mouseItem].__class__
            tip = patcherClass.tip or re.sub(ur'\..*', u'.',
                            patcherClass.text.split(u'\n')[0], flags=re.U)
            self.gTipText.SetLabel(tip)
        else:
            self.gTipText.SetLabel(self.defaultTipText)
        event.Skip()

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
