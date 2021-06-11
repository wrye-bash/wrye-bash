# -*- coding: utf-8 -*-
#
# GPL License and Copyright Notice ============================================
#  This file is part of Wrye Bash.
#
#  Wrye Bash is free software: you can redistribute it and/or
#  modify it under the terms of the GNU General Public License
#  as published by the Free Software Foundation, either version 3
#  of the License, or (at your option) any later version.
#
#  Wrye Bash is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
#
#  You should have received a copy of the GNU General Public License
#  along with Wrye Bash.  If not, see <https://www.gnu.org/licenses/>.
#
#  Wrye Bash copyright (C) 2005-2009 Wrye, 2010-2021 Wrye Bash Team
#  https://github.com/wrye-bash
#
# =============================================================================
"""Patch dialog"""
import copy
import io
import re
import time
from datetime import timedelta
from . import BashFrame, configIsCBash  ##: drop this - decouple !
from .. import balt, bass, bolt, bosh, bush, env, load_order
from ..balt import Link, Resources
from ..bolt import SubProgress, GPath, Path
from ..exception import BoltError, CancelError, FileEditError, \
    PluginsFullError, SkipError, BPConfigError
from ..gui import CancelButton, DeselectAllButton, HLayout, Label, \
    LayoutOptions, OkButton, OpenButton, RevertButton, RevertToSavedButton, \
    SaveAsButton, SelectAllButton, Stretch, VLayout, DialogWindow, \
    CheckListBox, HorizontalLine, EventResult, FileOpen
from ..patcher import exportConfig, list_patches_dir
from ..patcher.patch_files import PatchFile

# Final lists of gui patcher classes instances, initialized in
# gui_patchers.InitPatchers() based on game. These must be copied as needed.
all_gui_patchers = [] #--All gui patchers classes for this game

class PatchDialog(DialogWindow):
    """Bash Patch update dialog.

    :type _gui_patchers: list[basher.gui_patchers._PatcherPanel]
    """
    _min_size = (400, 300)

    def __init__(self, parent, patchInfo, mods_to_reselect):
        self.mods_to_reselect = mods_to_reselect
        self.parent = parent
        title = _(u'Update ') + u'%s' % patchInfo
        super(PatchDialog, self).__init__(parent, title=title,
            icon_bundle=Resources.bashBlue, sizes_dict=balt.sizes,
            size=balt.sizes.get(self.__class__.__name__, (500, 600)))
        #--Data
        list_patches_dir() # refresh cached dir
        patchConfigs = patchInfo.get_table_prop(u'bash.patch.configs', {})
        if configIsCBash(patchConfigs):
            patchConfigs = {}
        isFirstLoad = 0 == len(patchConfigs)
        self.patchInfo = patchInfo
        self._gui_patchers = [copy.deepcopy(p) for p in all_gui_patchers]
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
            lambda: self._mass_select_recursive(True))
        self.gDeselectAll = DeselectAllButton(self)
        self.gDeselectAll.on_clicked.subscribe(
            lambda: self._mass_select_recursive(False))
        self.gPatchers = CheckListBox(self, choices=patcherNames,
                                      isSingle=True, onSelect=self.OnSelect)
        self.gPatchers.on_box_checked.subscribe(self.OnCheck)
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
        self.defaultTipText = _(u'Items that are new since the last time this '
                                u'patch was built are displayed in bold.')
        self.gTipText = Label(self,self.defaultTipText)
        #--Events
        self.gPatchers.on_mouse_leaving.subscribe(self._mouse_leaving)
        self.gPatchers.on_mouse_motion.subscribe(self.handle_mouse_motion)
        self.gPatchers.on_key_down.subscribe(self._on_char)
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
                self.gRevertConfig, self.gRevertToDefault,
            ]),
            HLayout(spacing=4, items=[
                Stretch(), self.gExecute, self.gSelectAll, self.gDeselectAll,
                CancelButton(self),
            ]),
        ]).apply_to(self)
        #--Patcher panels
        for patcher in self._gui_patchers:
            patcher.GetConfigPanel(self, self.config_layout,
                self.gTipText).visible = False
        initial_select = min(len(self._gui_patchers) - 1, 1)
        if initial_select >= 0:
            self.gPatchers.lb_select_index(initial_select) # callback not fired
            self.ShowPatcher(self._gui_patchers[initial_select]) # so this is needed
        self._update_ok_btn()

    #--Core -------------------------------
    def _update_ok_btn(self):
        """Enable Build Patch button if at least one patcher is enabled."""
        self.gExecute.enabled = any(p.isEnabled for p in self._gui_patchers)

    def ShowPatcher(self,patcher):
        """Show patcher panel."""
        if patcher == self.currentPatcher: return
        if self.currentPatcher is not None:
            self.currentPatcher.gConfigPanel.visible = False
        patcher.GetConfigPanel(self, self.config_layout,
            self.gTipText).visible = True
        self.update_layout()
        patcher.Layout()
        self.currentPatcher = patcher

    @balt.conversation
    def PatchExecute(self):
        """Do the patch."""
        self.accept_modal()
        progress = None
        try:
            patch_name = self.patchInfo.ci_key
            patch_size = self.patchInfo.fsize
            progress = balt.Progress(patch_name.s,(u' '*60+u'\n'), abort=True)
            timer1 = time.process_time()
            #--Save configs
            config = self.__config()
            self.patchInfo.set_table_prop(u'bash.patch.configs', config)
            #--Do it
            log = bolt.LogFile(io.StringIO())
            patchFile = PatchFile(self.patchInfo, bosh.modInfos)
            enabled_patchers = [p.get_patcher_instance(patchFile) for p in
                                self._gui_patchers if p.isEnabled] ##: what happens if empty
            patchFile.init_patchers_data(enabled_patchers, SubProgress(progress, 0, 0.1)) #try to speed this up!
            patchFile.initFactories(SubProgress(progress,0.1,0.2)) #no speeding needed/really possible (less than 1/4 second even with large LO)
            patchFile.scanLoadMods(SubProgress(progress,0.2,0.8)) #try to speed this up!
            patchFile.buildPatch(log,SubProgress(progress,0.8,0.9))#no speeding needed/really possible (less than 1/4 second even with large LO)
            if patchFile.tes4.num_masters > bush.game.Esp.master_limit:
                balt.showError(self,
                    _(u'The resulting Bashed Patch contains too many '
                      u'masters (>%u). You can try to disable some '
                      u'patchers, create a second Bashed Patch and '
                      u'rebuild that one with only the patchers you '
                      u'disabled in this one active.')
                    % bush.game.Esp.master_limit)
                return # Abort, we'll just blow up on saving it
            #--Save
            progress.setCancel(False, u'%s\n' % patch_name + _(u'Saving...'))
            progress(0.9)
            self._save_pbash(patchFile, patch_name)
            #--Done
            progress.Destroy(); progress = None
            timer2 = time.process_time()
            #--Readme and log
            log.setHeader(None)
            log(u'{{CSS:wtxt_sand_small.css}}')
            logValue = log.out.getvalue()
            timerString = str(timedelta(seconds=round(timer2 - timer1, 3))).rstrip(u'0')
            logValue = re.sub(u'TIMEPLACEHOLDER', timerString, logValue, 1)
            readme = bosh.modInfos.store_dir.join(u'Docs', patch_name.sroot + u'.txt')
            docsDir = bass.dirs[u'mopy'].join(u'Docs')
            tempReadmeDir = Path.tempDir().join(u'Docs')
            tempReadme = tempReadmeDir.join(patch_name.sroot + u'.txt')
            #--Write log/readme to temp dir first
            with tempReadme.open(u'w', encoding=u'utf-8-sig') as file:
                file.write(logValue)
            #--Convert log/readmeto wtxt
            bolt.WryeText.genHtml(tempReadme,None,docsDir)
            #--Try moving temp log/readme to Docs dir
            try:
                env.shellMove(tempReadmeDir, bass.dirs[u'mods'],
                              parent=self._native_widget)
            except (CancelError,SkipError):
                # User didn't allow UAC, move to My Games directory instead
                env.shellMove([tempReadme, tempReadme.root + u'.html'],
                              bass.dirs[u'saveBase'], parent=self)
                readme = bass.dirs[u'saveBase'].join(readme.tail)
            #finally:
            #    tempReadmeDir.head.rmtree(safety=tempReadmeDir.head.stail)
            readme = readme.root + u'.html'
            self.patchInfo.set_table_prop(u'doc', readme)
            balt.playSound(self.parent, bass.inisettings[u'SoundSuccess'])
            balt.WryeLog(self.parent, readme, patch_name,
                         log_icons=Resources.bashBlue)
            #--Select?
            if self.mods_to_reselect:
                for mod in self.mods_to_reselect:
                    bosh.modInfos.lo_activate(mod, doSave=False)
                self.mods_to_reselect.clear()
                bosh.modInfos.cached_lo_save_active() ##: also done below duh
            count, message = 0, _(u'Activate %s?') % patch_name
            if load_order.cached_is_active(patch_name) or (
                        bass.inisettings[u'PromptActivateBashedPatch'] and
                        balt.askYes(self.parent, message, patch_name.s)):
                try:
                    changedFiles = bosh.modInfos.lo_activate(patch_name,
                                                             doSave=True)
                    count = len(changedFiles)
                    if count > 1: Link.Frame.set_status_info(
                            _(u'Masters Activated: ') + str(count - 1))
                except PluginsFullError:
                    balt.showError(self, _(
                        u'Unable to add mod %s because load list is full.')
                                   % patch_name)
            # although improbable user has package with bashed patches...
            info = bosh.modInfos.new_info(patch_name, notify_bain=True)
            if info.fsize == patch_size:
                # needed if size remains the same - mtime is set in
                # parsers.ModFile#safeSave which can't use
                # setmtime(crc_changed), as no info is there. In this case
                # _reset_cache > calculate_crc() would not detect the crc
                # change. That's a general problem with crc cache - API limits
                info.calculate_crc(recalculate=True)
            BashFrame.modList.RefreshUI(refreshSaves=bool(count))
        except CancelError:
            pass
        except BPConfigError as e: # User configured BP incorrectly
            self._error(_(u'The configuration of the Bashed Patch is '
                          u'incorrect.') + u'\n' + e.message)
        except (BoltError, FileEditError) as e: # Nonfatal error
            self._error(u'%s' % e)
        except Exception as e: # Fatal error
            self._error(u'%s' % e)
            raise
        finally:
            if progress: progress.Destroy()

    def _error(self, e_msg):
        balt.playSound(self.parent, bass.inisettings[u'SoundError'])
        balt.showError(self, e_msg, _(u'Bashed Patch Error'))
        bolt.deprint(u'Exception during Bashed Patch building:',
                     traceback=True)

    def _save_pbash(self, patchFile, patch_name):
        while True:
            try:
                # FIXME will keep displaying a bogus UAC prompt if file is
                # locked - aborting bogus UAC dialog raises SkipError() in
                # shellMove, not sure if ever a Windows or Cancel are raised
                patchFile.safeSave()
                return
            except (CancelError, SkipError, PermissionError):
                ##: Ugly warts below (see also FIXME above)
                if balt.askYes(self,
                    (_(u'Bash encountered an error when saving '
                       u'%(patch_name)s.') + u'\n\n' + _(
                        u'Either Bash needs Administrator Privileges to save '
                        u'the file, or the file is in use by another process '
                        u'such as %(xedit_name)s.') + u'\n' + _(
                        u'Please close any program that is accessing '
                        u'%(patch_name)s, and provide Administrator '
                        u'Privileges if prompted to do so.') + u'\n\n' + _(
                        u'Try again?')) % {u'patch_name': patch_name,
                        u'xedit_name': bush.game.Xe.full_name},
                        _(u'Bashed Patch - Save Error')):
                    continue
                raise # will raise the SkipError which is correctly processed

    def __config(self):
        config = {u'ImportedMods': set()}
        for p in self._gui_patchers: p.saveConfig(config)
        return config

    def ExportConfig(self):
        """Export the configuration to a user selected dat file."""
        config = self.__config()
        exportConfig(patch_name=self.patchInfo.ci_key, config=config,
                     win=self.parent, outDir=bass.dirs[u'patches'])

    __old_key = GPath(u'Saved Bashed Patch Configuration')
    __new_key = u'Saved Bashed Patch Configuration (%s)'
    def ImportConfig(self):
        """Import the configuration from a user selected dat file."""
        config_dat = self.patchInfo.ci_key + u'_Configuration.dat'
        textDir = bass.dirs[u'patches']
        textDir.makedirs()
        #--File dialog
        textPath = FileOpen.display_dialog(self.parent, _(
            u'Import Bashed Patch configuration from:'), textDir, config_dat,
            u'*.dat')
        if not textPath: return
        table = bolt.DataTable(bolt.PickleDict(textPath))
        # try the current Bashed Patch mode.
        patchConfigs = table.getItem(GPath(self.__new_key % u'Python'),
            u'bash.patch.configs', {})
        convert = False
        if not patchConfigs: # try the non-current Bashed Patch mode
            patchConfigs = table.getItem(GPath(self.__new_key % u'CBash'),
                u'bash.patch.configs', {})
            convert = bool(patchConfigs)
        if not patchConfigs: # try the old format
            patchConfigs = table.getItem(self.__old_key, u'bash.patch.configs',
                {})
            convert = bool(patchConfigs)
        if not patchConfigs:
            balt.showWarning(self,
                _(u'No patch config data found in %s') % textPath,
                title=_(u'Import Config'))
            return
        if convert:
            balt.showError(self,
                _(u'The patch config data in %s is too old for this version '
                  u'of Wrye Bash to handle or was created with CBash. Please '
                  u'use Wrye Bash 307 to import the config, then rebuild the '
                  u'patch using PBash to convert it and finally export the '
                  u'config again to get one that will work in this '
                  u'version.') % textPath, title=_(u'Config Too Old'))
            return
        self._load_config(patchConfigs)

    def _load_config(self, patchConfigs, set_first_load=False, default=False):
        for index, patcher in enumerate(self._gui_patchers):
            patcher.import_config(patchConfigs, set_first_load=set_first_load,
                                  default=default)
            self.gPatchers.lb_check_at_index(index, patcher.isEnabled)
        self._update_ok_btn()

    def RevertConfig(self):
        """Revert configuration back to saved"""
        patchConfigs = self.patchInfo.get_table_prop(u'bash.patch.configs', {})
        self._load_config(patchConfigs)

    def DefaultConfig(self):
        """Revert configuration back to default"""
        self._load_config({}, set_first_load=True, default=True)

    def _mass_select_recursive(self, select=True):
        """Select or deselect all patchers and entries in patchers with child
        entries."""
        self.gPatchers.set_all_checkmarks(checked=select)
        for patcher in self._gui_patchers:
            patcher.mass_select(select=select)
        self._update_ok_btn()

    #--GUI --------------------------------
    def OnSelect(self, lb_selection_dex, _lb_selection_str):
        """Responds to patchers list selection."""
        self.ShowPatcher(self._gui_patchers[lb_selection_dex])
        self.gPatchers.lb_select_index(lb_selection_dex)

    def check_patcher(self, patcher, enable_patcher=True):
        """Enable or disable a patcher."""
        self.gPatchers.lb_check_at_index(
            self._gui_patchers.index(patcher), enable_patcher)
        self._update_ok_btn()

    def style_patcher(self, patcher, bold=False, slant=False):
        """Set the patcher label to bold and/or italicized font. Called from a
        patcher when it's new or detects that it has something new in its
        list."""
        self.gPatchers.lb_style_font_at_index(
            self._gui_patchers.index(patcher), bold=bold, slant=slant)

    def OnCheck(self, lb_selection_dex):
        """Toggle patcher activity state."""
        patcher = self._gui_patchers[lb_selection_dex]
        patcher.isEnabled = self.gPatchers.lb_is_checked_at_index(lb_selection_dex)
        self.gPatchers.lb_select_index(lb_selection_dex)
        self.ShowPatcher(patcher) # SetSelection does not fire the callback
        self._update_ok_btn()

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
        # Ctrl+'A' - select all items of the current patchers (or deselect them
        # if Shift is also held)
        if wrapped_evt.is_cmd_down and wrapped_evt.key_code == ord(u'A'):
            patcher = self.currentPatcher
            if patcher is not None:
                patcher.mass_select(select=not wrapped_evt.is_shift_down)
                # Otherwise will select 'Alias Mod Names' ('A' key is pressed!)
                return EventResult.FINISH
