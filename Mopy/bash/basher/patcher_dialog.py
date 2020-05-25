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

"""Patch dialog"""
import StringIO
import copy
import errno
import re
import time
from datetime import timedelta
from . import BashFrame ##: drop this - decouple !
from .. import balt, bass, bolt, bosh, bush, env, load_order
from ..balt import Link, Resources
from ..bolt import SubProgress, GPath, Path
from ..exception import BoltError, CancelError, FileEditError, \
    PluginsFullError, SkipError
from ..gui import CancelButton, DeselectAllButton, HLayout, Label, \
    LayoutOptions, OkButton, OpenButton, RevertButton, RevertToSavedButton, \
    SaveAsButton, SelectAllButton, Stretch, VLayout, DialogWindow, \
    CheckListBox, HorizontalLine
from ..patcher import configIsCBash, exportConfig, list_patches_dir
from ..patcher.patch_files import PatchFile, CBash_PatchFile

# Final lists of gui patcher classes instances, initialized in
# gui_patchers.InitPatchers() based on game. These must be copied as needed.
PBash_gui_patchers = [] #--All gui patchers classes for this game
CBash_gui_patchers = [] #--All gui patchers classes for this game (CBash mode)

class PatchDialog(DialogWindow):
    """Bash Patch update dialog.

    :type _gui_patchers: list[basher.gui_patchers._PatcherPanel]
    """
    _min_size = (400, 300)

    def __init__(self, parent, patchInfo, doCBash, importConfig,
                 mods_to_reselect):
        self.mods_to_reselect = mods_to_reselect
        self.parent = parent
        if (doCBash or doCBash is None) and bass.settings['bash.CBashEnabled']:
            doCBash = True
        else:
            doCBash = False
        self.doCBash = doCBash
        title = _(u'Update ') + patchInfo.name.s + [u'', u' (CBash)'][doCBash]
        size = balt.sizes.get(self.__class__.__name__, (500,600))
        super(PatchDialog, self).__init__(parent, title=title,
            icon_bundle=Resources.bashMonkey, sizes_dict=balt.sizes, size=size)
        #--Data
        list_patches_dir() # refresh cached dir
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
        self._gui_patchers = [copy.deepcopy(p) for p in (
            CBash_gui_patchers if doCBash else PBash_gui_patchers)]
        self._gui_patchers.sort(key=lambda a: a.__class__.patcher_name)
        self._gui_patchers.sort(key=lambda a: groupOrder[a.patcher_type.group]) ##: what does this ordering do??
        for patcher in self._gui_patchers:
            patcher.getConfig(patchConfigs) #--Will set patcher.isEnabled
            patcher.SetIsFirstLoad(isFirstLoad)
        self.currentPatcher = None
        patcherNames = [patcher.patcher_name for patcher in self._gui_patchers]
        #--GUI elements
        self.gExecute = OkButton(self, btn_label=_(u'Build Patch'))
        self.gExecute.on_clicked.subscribe(self.PatchExecute)
        # TODO(nycz): somehow move setUAC further into env?
        # Note: for this to work correctly, it needs to be run BEFORE
        # appending a menu item to a menu (and so, needs to be enabled/
        # disabled prior to that as well.
        # TODO(nycz): DEWX - Button.GetHandle
        env.setUAC(self.gExecute._native_widget.GetHandle(), True)
        self.gSelectAll = SelectAllButton(self)
        self.gSelectAll.on_clicked.subscribe(
            lambda: self.mass_select_recursive(True))
        self.gDeselectAll = DeselectAllButton(self)
        self.gDeselectAll.on_clicked.subscribe(
            lambda: self.mass_select_recursive(False))
        cancelButton = CancelButton(self)
        self.gPatchers = CheckListBox(self, choices=patcherNames,
                                      isSingle=True, onSelect=self.OnSelect,
                                      onCheck=self.OnCheck)
        self.gExportConfig = SaveAsButton(self, btn_label=_(u'Export'))
        self.gExportConfig.on_clicked.subscribe(self.ExportConfig)
        self.gImportConfig = OpenButton(self, btn_label=_(u'Import'))
        self.gImportConfig.on_clicked.subscribe(self.ImportConfig)
        self.gRevertConfig = RevertToSavedButton(self)
        self.gRevertConfig.on_clicked.subscribe(self.RevertConfig)
        self.gRevertToDefault = RevertButton(self,
                                             btn_label=_(u'Revert To Default'))
        self.gRevertToDefault.on_clicked.subscribe(self.DefaultConfig)
        for index,patcher in enumerate(self._gui_patchers):
            self.gPatchers.lb_check_at_index(index, patcher.isEnabled)
        self.defaultTipText = _(u'Items that are new since the last time this patch was built are displayed in bold')
        self.gTipText = Label(self,self.defaultTipText)
        #--Events
        self.gPatchers.on_mouse_leaving.subscribe(self._mouse_leaving)
        self.gPatchers.on_mouse_motion.subscribe(self.handle_mouse_motion)
        self.gPatchers.on_key_pressed.subscribe(self._on_char)
        self.mouse_dex = -1
        #--Layout
        self.config_layout = VLayout(item_expand=True, item_weight=1)
        VLayout(border=4, spacing=4, item_expand=True, items=[
            (HLayout(spacing=8, item_expand=True, items=[
                self.gPatchers,
                (self.config_layout, LayoutOptions(weight=1))
             ]), LayoutOptions(weight=1)),
            self.gTipText,
            HorizontalLine(self),
            HLayout(spacing=4, items=[
                Stretch(), self.gExportConfig, self.gImportConfig,
                self.gRevertConfig, self.gRevertToDefault]),
            HLayout(spacing=4, items=[
                Stretch(), self.gExecute, self.gSelectAll, self.gDeselectAll,
                cancelButton])
        ]).apply_to(self)
        #--Patcher panels
        for patcher in self._gui_patchers:
            patcher.GetConfigPanel(self, self.config_layout,
                                   self.gTipText).pnl_hide()
        initial_select = min(len(self._gui_patchers) - 1, 1)
        if initial_select >= 0:
            self.gPatchers.lb_select_index(initial_select) # callback not fired
            self.ShowPatcher(self._gui_patchers[initial_select]) # so this is needed
        self.SetOkEnable()

    #--Core -------------------------------
    def SetOkEnable(self):
        """Enable Build Patch button if at least one patcher is enabled."""
        self.gExecute.enabled = any(p.isEnabled for p in self._gui_patchers)

    def ShowPatcher(self,patcher):
        """Show patcher panel."""
        if patcher == self.currentPatcher: return
        if self.currentPatcher is not None:
            self.currentPatcher.gConfigPanel.pnl_hide()
        patcher.GetConfigPanel(self, self.config_layout, self.gTipText).visible = True
        self._native_widget.Layout()
        patcher.Layout()
        self.currentPatcher = patcher

    @balt.conversation
    def PatchExecute(self): # TODO(ut): needs more work to reduce P/C differences to an absolute minimum
        """Do the patch."""
        self.accept_modal()
        patchFile = progress = None
        try:
            patch_name = self.patchInfo.name
            patch_size = self.patchInfo.size
            progress = balt.Progress(patch_name.s,(u' '*60+u'\n'), abort=True)
            timer1 = time.clock()
            #--Save configs
            self._saveConfig(patch_name)
            #--Do it
            log = bolt.LogFile(StringIO.StringIO())
            patchFile = CBash_PatchFile(patch_name) if self.doCBash else \
                PatchFile(self.patchInfo)
            enabled_patchers = [p.get_patcher_instance(patchFile) for p in
                                self._gui_patchers if p.isEnabled] ##: what happens if empty
            patchFile.init_patchers_data(enabled_patchers, SubProgress(progress, 0, 0.1)) #try to speed this up!
            if self.doCBash:
                #try to speed this up!
                patchFile.buildPatch(SubProgress(progress,0.1,0.9))
                #no speeding needed/really possible (less than 1/4 second even with large LO)
                patchFile.buildPatchLog(log, SubProgress(progress, 0.95, 0.99))
                #--Save
                progress.setCancel(False, patch_name.s+u'\n'+_(u'Saving...'))
                progress(0.99)
                self._save_cbash(patchFile, patch_name)
            else:
                patchFile.initFactories(SubProgress(progress,0.1,0.2)) #no speeding needed/really possible (less than 1/4 second even with large LO)
                patchFile.scanLoadMods(SubProgress(progress,0.2,0.8)) #try to speed this up!
                patchFile.buildPatch(log,SubProgress(progress,0.8,0.9))#no speeding needed/really possible (less than 1/4 second even with large LO)
                #--Save
                progress.setCancel(False, patch_name.s+u'\n'+_(u'Saving...'))
                progress(0.9)
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
                                  parent=self._native_widget)
                except (CancelError,SkipError):
                    # User didn't allow UAC, move to My Games directory instead
                    env.shellMove([tempReadme, tempReadme.root + u'.html'],
                                  bass.dirs['saveBase'], parent=self)
                    readme = bass.dirs['saveBase'].join(readme.tail)
                #finally:
                #    tempReadmeDir.head.rmtree(safety=tempReadmeDir.head.stail)
            readme = readme.root + u'.html'
            bosh.modInfos.table.setItem(patch_name, 'doc', readme)
            balt.playSound(self.parent, bass.inisettings['SoundSuccess'].s)
            balt.WryeLog(self.parent, readme, patch_name.s,
                         log_icons=Resources.bashBlue)
            #--Select?
            if self.mods_to_reselect:
                for mod in self.mods_to_reselect:
                    bosh.modInfos.lo_activate(mod, doSave=False)
                self.mods_to_reselect.clear()
                bosh.modInfos.cached_lo_save_active() ##: also done below duh
            count, message = 0, _(u'Activate %s?') % patch_name.s
            if load_order.cached_is_active(patch_name) or (
                        bass.inisettings['PromptActivateBashedPatch'] and
                        balt.askYes(self.parent, message, patch_name.s)):
                try:
                    changedFiles = bosh.modInfos.lo_activate(patch_name,
                                                             doSave=True)
                    count = len(changedFiles)
                    if count > 1: Link.Frame.set_status_info(
                            _(u'Masters Activated: ') + unicode(count - 1))
                except PluginsFullError:
                    balt.showError(self, _(
                        u'Unable to add mod %s because load list is full.')
                                   % patch_name.s)
            # although improbable user has package with bashed patches...
            info = bosh.modInfos.new_info(patch_name, notify_bain=True)
            if info.size == patch_size:
                # needed if size remains the same - mtime is set in
                # parsers.ModFile#safeSave (or save for CBash...) which can't
                # use setmtime(crc_changed), as no info is there. In this case
                # _reset_cache > calculate_crc() would not detect the crc
                # change. That's a general problem with crc cache - API limits
                info.calculate_crc(recalculate=True)
            BashFrame.modList.RefreshUI(refreshSaves=bool(count))
        except CancelError:
            pass
        except FileEditError as error:
            balt.playSound(self.parent, bass.inisettings['SoundError'].s)
            balt.showError(self,u'%s'%error,_(u'File Edit Error'))
            bolt.deprint(u'Exception during Bashed Patch building:',
                traceback=True)
        except BoltError as error:
            balt.playSound(self.parent, bass.inisettings['SoundError'].s)
            balt.showError(self,u'%s'%error,_(u'Processing Error'))
            bolt.deprint(u'Exception during Bashed Patch building:',
                traceback=True)
        except:
            balt.playSound(self.parent, bass.inisettings['SoundError'].s)
            bolt.deprint(u'Exception during Bashed Patch building:',
                traceback=True)
            raise
        finally:
            if self.doCBash:
                try: patchFile.Current.Close()
                except:
                    bolt.deprint(u'Failed to close CBash collection',
                                 traceback=True)
            if progress: progress.Destroy()

    def _save_pbash(self, patchFile, patch_name):
        while True:
            try:
                # FIXME will keep displaying a bogus UAC prompt if file is
                # locked - aborting bogus UAC dialog raises SkipError() in
                # shellMove, not sure if ever a Windows or Cancel are raised
                patchFile.safeSave()
                return
            except (CancelError, SkipError, OSError, IOError) as werr:
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
        return balt.askYes(
            self, _(u'Bash encountered an error when saving %(patch_name)s.'
                    u'\n\nEither Bash needs Administrator Privileges to save '
                    u'the file, or the file is in use by another process such '
                    u'as %(xedit_name)s.\nPlease close any program that is '
                    u'accessing %(patch_name)s, and provide Administrator '
                    u'Privileges if prompted to do so.\n\nTry again?') % {
                u'patch_name': patch_name.s,
                u'xedit_name': bush.game.Xe.full_name},
            _(u'Bashed Patch - Save Error'))

    def _cretry(self, patch_name):
        return balt.askYes(
            self, _(u'Bash encountered an error when renaming '
                    u'%(temp_patch)s to %(patch_name)s.\n\nThe file is in use '
                    u'by another process such as %(xedit_name)s.\nPlease '
                    u'close the other program that is accessing %s.\n\nTry '
                    u'again?') % {
                u'temp_patch': patch_name.temp.s, u'patch_name': patch_name.s,
                u'xedit_name': bush.game.Xe.full_name},
            _(u'Bashed Patch - Save Error'))

    def __config(self):
        config = {'ImportedMods': set()}
        for p in self._gui_patchers: p.saveConfig(config)
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
        table = bolt.DataTable(bolt.PickleDict(textPath))
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
        for index, patcher in enumerate(self._gui_patchers):
            patcher.import_config(patchConfigs, set_first_load=set_first_load,
                                  default=default)
            self.gPatchers.lb_check_at_index(index, patcher.isEnabled)
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

    def mass_select_recursive(self, select=True):
        """Select or deselect all patchers and entries in patchers with child
        entries."""
        self.gPatchers.set_all_checkmarks(checked=select)
        for patcher in self._gui_patchers:
            patcher.mass_select(select=select)
        self.gExecute.enabled = select

    #--GUI --------------------------------
    def OnSelect(self, lb_selection_dex, lb_selection_str):
        """Responds to patchers list selection."""
        self.ShowPatcher(self._gui_patchers[lb_selection_dex])
        self.gPatchers.lb_select_index(lb_selection_dex)

    def CheckPatcher(self, patcher):
        """Enable a patcher - Called from a patcher's OnCheck method."""
        index = self._gui_patchers.index(patcher)
        self.gPatchers.lb_check_at_index(index, True)
        self.SetOkEnable()

    def BoldPatcher(self, patcher):
        """Set the patcher label to bold font.  Called from a patcher when
        it realizes it has something new in its list"""
        index = self._gui_patchers.index(patcher)
        self.gPatchers.lb_bold_font_at_index(index)

    def OnCheck(self, lb_selection_dex):
        """Toggle patcher activity state."""
        patcher = self._gui_patchers[lb_selection_dex]
        patcher.isEnabled = self.gPatchers.lb_is_checked_at_index(lb_selection_dex)
        self.gPatchers.lb_select_index(lb_selection_dex)
        self.ShowPatcher(patcher) # SetSelection does not fire the callback
        self.SetOkEnable()

    def _mouse_leaving(self): self._set_tip_text(-1)

    def handle_mouse_motion(self, wrapped_evt, lb_dex):
        """Show tip text when changing item."""
        if wrapped_evt.is_moving:
            if lb_dex != self.mouse_dex:
                self.mouse_dex = lb_dex
        self._set_tip_text(lb_dex)

    def _set_tip_text(self, mouseItem):
        if 0 <= mouseItem < len(self._gui_patchers):
            gui_patcher = self._gui_patchers[mouseItem]
            self.gTipText.label_text = gui_patcher.patcher_tip
        else:
            self.gTipText.label_text = self.defaultTipText

    def _on_char(self, wrapped_evt):
        """Keyboard input to the patchers list box"""
        if wrapped_evt.key_code == 1 and wrapped_evt.is_cmd_down: # Ctrl+'A'
            patcher = self.currentPatcher
            if patcher is not None:
                patcher.mass_select(select=not wrapped_evt.is_shift_down)
                return

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
