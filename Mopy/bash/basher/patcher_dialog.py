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
#  Wrye Bash copyright (C) 2005-2009 Wrye, 2010-2023 Wrye Bash Team
#  https://github.com/wrye-bash
#
# =============================================================================
"""Patch dialog"""
import copy
import io
import re
import time
from datetime import timedelta

from .. import balt, bass, bolt, bosh, bush, env, load_order
from ..balt import Link, Resources
from ..bolt import GPath_no_norm, SubProgress
from ..exception import BoltError, BPConfigError, CancelError, FileEditError, \
    PluginsFullError, SkipError
from ..gui import BusyCursor, CancelButton, CheckListBox, DeselectAllButton, \
    DialogWindow, EventResult, FileOpen, HLayout, HorizontalLine, Label, \
    LayoutOptions, OkButton, OpenButton, RevertButton, RevertToSavedButton, \
    SaveAsButton, SelectAllButton, Stretch, VLayout, showError, askYes, \
    showWarning
from ..patcher import exportConfig
from ..wbtemp import TempDir

# Final lists of gui patcher classes instances, initialized in
# gui_patchers.InitPatchers() based on game. These must be copied as needed.
all_gui_patchers = [] #--All gui patchers classes for this game

class PatchDialog(DialogWindow):
    """Bash Patch update dialog.

    :type _gui_patchers: list[basher.gui_patchers._PatcherPanel]
    """
    _def_size = (600, 600)
    _min_size = (400, 300)

    def __init__(self, parent, bashed_patch, mods_to_reselect, patchConfigs):
        self.mods_to_reselect = mods_to_reselect
        self.parent = parent
        self.bashed_patch = bashed_patch
        self.patchInfo = bashed_patch.fileInfo
        title = _('Update ') + f'{self.patchInfo}'
        super().__init__(parent, title=title, icon_bundle=Resources.bashBlue,
            sizes_dict=bass.settings)
        #--Data
        self._gui_patchers = [copy.deepcopy(p) for p in all_gui_patchers]
        for g in self._gui_patchers: g._bp = bashed_patch
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
        # load the config
        self.patchConfigs = patchConfigs
        isFirstLoad = 0 == len(patchConfigs)
        self._load_config(patchConfigs, isFirstLoad, _decouple=True) ##: _decouple == True to short circuit _import_config
        with BusyCursor(): # Constructs all the patcher panels, so takes a bit
            for patcher in self._gui_patchers:
                patcher.GetConfigPanel(self, self.config_layout,
                    self.gTipText).visible = False
        initial_select = min(len(self._gui_patchers) - 1, 1)
        if initial_select >= 0:
            self.gPatchers.lb_select_index(initial_select) # callback not fired
            self.ShowPatcher(self._gui_patchers[initial_select]) # so this is needed

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
            patch_name = self.patchInfo.fn_key
            patch_size = self.patchInfo.fsize
            progress = balt.Progress(patch_name, abort=True)
            timer1 = time.time_ns()
            #--Save configs
            config = self.__config()
            self.patchInfo.set_table_prop(u'bash.patch.configs', config)
            #--Do it
            log = bolt.LogFile(io.StringIO())
            patchFile = self.bashed_patch
            enabled_patchers = [p.get_patcher_instance(patchFile) for p in
                                self._gui_patchers if p.isEnabled] ##: what happens if empty
            patchFile.init_patchers_data(enabled_patchers, SubProgress(progress, 0, 0.1)) #try to speed this up!
            patchFile.initFactories(SubProgress(progress,0.1,0.2)) #no speeding needed/really possible (less than 1/4 second even with large LO)
            patchFile.scanLoadMods(SubProgress(progress,0.2,0.8)) #try to speed this up!
            patchFile.buildPatch(log,SubProgress(progress,0.8,0.9))#no speeding needed/really possible (less than 1/4 second even with large LO)
            if patchFile.tes4.num_masters > bush.game.Esp.master_limit:
                showError(self, _(
                    'The resulting Bashed Patch contains too many masters '
                    '(%(curr_num_masters)d, limit is %(max_num_masters)d). '
                    'You can try to disable some patchers, create a second '
                    'Bashed Patch and rebuild that one with only the patchers '
                    'you disabled in this one active.') % {
                    'curr_num_masters': patchFile.tes4.num_masters,
                    'max_num_masters': bush.game.Esp.master_limit})
                return # Abort, we'll just blow up on saving it
            #--Save
            progress.setCancel(False, f'{patch_name}\n' + _(u'Saving...'))
            progress(0.9)
            self._save_pbash(patchFile, patch_name)
            #--Done
            progress.Destroy()
            progress = None
            timer2 = time.time_ns()
            #--Readme and log
            log.setHeader(None)
            log(u'{{CSS:wtxt_sand_small.css}}')
            logValue = log.out.getvalue()
            # Determine the elapsed nanoseconds, convert to seconds and round
            # to 3 decimal digits
            delta_seconds = round((timer2 - timer1) / 1_000_000_000, 3)
            timerString = str(timedelta(seconds=delta_seconds)).rstrip('0')
            logValue = re.sub(u'TIMEPLACEHOLDER', timerString, logValue, 1)
            data_docs_dir = bosh.modInfos.store_dir.join('Docs')
            readme = data_docs_dir.join(patch_name.fn_body + '.txt')
            docsDir = bass.dirs[u'mopy'].join(u'Docs')
            with TempDir(temp_prefix='Docs') as trd:
                temp_readme_dir = GPath_no_norm(trd)
                temp_readme = temp_readme_dir.join(patch_name.fn_body + '.txt')
                #--Write log/readme to temp dir first
                with temp_readme.open(u'w', encoding=u'utf-8-sig') as file:
                    file.write(logValue)
                #--Convert log/readme to wtxt
                bolt.WryeText.genHtml(temp_readme, None, docsDir)
                #--Try moving temp log/readme to Docs dir
                try:
                    env.shellMove({temp_readme_dir: data_docs_dir},
                        parent=self)
                except (CancelError, SkipError):
                    # User didn't allow UAC, move to My Games directory instead
                    temp_readme_html = temp_readme.root + '.html'
                    readme_moves = {
                        temp_readme: bass.dirs['saveBase'].join(
                            temp_readme.stail),
                        temp_readme_html: bass.dirs['saveBase'].join(
                            temp_readme_html.stail)
                    }
                    env.shellMove(readme_moves, parent=self)
                    readme = bass.dirs['saveBase'].join(readme.stail)
            readme = readme.root + u'.html'
            self.patchInfo.set_table_prop(u'doc', readme)
            balt.playSound(self.parent, bass.inisettings[u'SoundSuccess'])
            balt.WryeLog(self.parent, readme, patch_name,
                         log_icons=Resources.bashBlue)
            # We have to parse the new info first, since the masters may
            # differ. Most people probably don't keep BAIN packages of BPs, but
            # *I* do, so...
            info = bosh.modInfos.new_info(patch_name, notify_bain=True)
            #--Select?
            if self.mods_to_reselect:
                for mod in self.mods_to_reselect:
                    bosh.modInfos.lo_activate(mod, doSave=False)
                self.mods_to_reselect.clear()
                bosh.modInfos.cached_lo_save_active() ##: also done below duh
            message = _('Activate %(bp_name)s?') % {'bp_name': patch_name}
            count = 0
            if load_order.cached_is_active(patch_name) or (
                    bass.inisettings['PromptActivateBashedPatch'] and
                    askYes(self.parent, message, patch_name)):
                try:
                    count = len(bosh.modInfos.lo_activate(patch_name,
                        doSave=True))
                    if count > 1:
                        Link.Frame.set_status_info(
                            _('Masters Activated: %(num_activated)d') % {
                                'num_activated': count - 1})
                except PluginsFullError:
                    showError(self, _(
                        'Unable to activate plugin %(bp_name)s because the '
                        'load order is full.') % {'bp_name': patch_name})
            if info.fsize == patch_size:
                # Needed if size remains the same - mtime is set in
                # ModFile.safeSave which can't use setmtime(crc_changed), as no
                # info is there. In this case _reset_cache > calculate_crc()
                # would not detect the crc change. That's a general problem
                # with crc cache - API limits
                info.calculate_crc(recalculate=True)
            self.parent.RefreshUI(refreshSaves=bool(count))
        except CancelError:
            pass
        except BPConfigError as e: # User configured BP incorrectly
            self._error(_(u'The configuration of the Bashed Patch is '
                          u'incorrect.') + f'\n\n{e}')
        except (BoltError, FileEditError, NotImplementedError) as e:
            # Nonfatal error
            self._error(f'{e}')
        except Exception as e: # Fatal error
            self._error(f'{e}')
            raise
        finally:
            if progress: progress.Destroy()

    def _error(self, e_msg):
        balt.playSound(self.parent, bass.inisettings[u'SoundError'])
        bolt.deprint('Exception during Bashed Patch building:', traceback=True)
        showError(self, e_msg, _('Bashed Patch Error'))

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
                m = _('Bash encountered an error when saving %(patch_name)s.')
                m += '\n\n' + _('Either Bash needs Administrator Privileges '
                    'to save the file, or the file is in use by another '
                    'process such as %(xedit_name)s.')
                m += '\n' + _('Please close any program that is accessing '
                    '%(patch_name)s, and provide Administrator Privileges if '
                    'prompted to do so.') + '\n\n' + _('Try again?')
                m %= {'patch_name': patch_name,
                      'xedit_name': bush.game.Xe.full_name}
                if askYes(self, m, _('Bashed Patch - Save Error')):
                    continue
                raise # will raise the SkipError which is correctly processed

    def __config(self):
        config = {u'ImportedMods': set()}
        for p in self._gui_patchers: p.saveConfig(config)
        return config

    def ExportConfig(self):
        """Export the configuration to a user selected dat file."""
        config = self.__config()
        exportConfig(patch_name=self.patchInfo.fn_key, config=config,
                     win=self.parent, outDir=bass.dirs[u'patches'])

    __old_key = u'Saved Bashed Patch Configuration'
    __new_key = u'Saved Bashed Patch Configuration (%s)'
    def ImportConfig(self):
        """Import the configuration from a user selected dat file."""
        config_dat = f'{self.patchInfo.fn_key}_Configuration.dat'
        textDir = bass.dirs[u'patches']
        textDir.makedirs()
        #--File dialog
        textPath = FileOpen.display_dialog(self.parent, _(
            u'Import Bashed Patch configuration from:'), textDir, config_dat,
            u'*.dat')
        if not textPath: return
        pickle_dict = bolt.PickleDict(textPath, load_pickle=True).pickled_data
        table_get = lambda x: (conf := pickle_dict.get(GPath_no_norm(x))) and (
            conf.get('bash.patch.configs', {}))
        # try the current Bashed Patch mode.
        patchConfigs = table_get(self.__new_key % 'Python')
        if not patchConfigs: # try the non-current Bashed Patch mode
            patchConfigs = table_get(self.__new_key % 'CBash')
            if not patchConfigs: # try the old format
                patchConfigs = table_get(self.__old_key)
            if not patchConfigs:
                msg = _('No patch config data found in %(bp_config_path)s') % {
                    'bp_config_path': textPath}
                showWarning(self, msg, title=_('Import Config'))
                return
            msg = _('The patch config data in %(bp_config_path)s is too old '
                'for this version of Wrye Bash to handle or was created with '
                'CBash. Please use Wrye Bash 307 to import the config, then '
                'rebuild the patch using PBash to convert it and finally '
                'export the config again to get one that will work in this '
                'version.') % {'bp_config_path': textPath}
            showError(self, msg, title=_('Config Too Old'))
            return
        self._load_config(patchConfigs)

    def _load_config(self, patchConfigs, set_first_load=False, default=False,
                     _decouple=False): ##: hacky param due to SetItems/GetConfigPanel overlap
        for index, patcher in enumerate(self._gui_patchers):
            patcher.import_config(patchConfigs, set_first_load=set_first_load,
                                  default=default, _decouple=_decouple)
            self.gPatchers.lb_check_at_index(index, patcher.isEnabled)
        self._update_ok_btn()

    def RevertConfig(self):
        """Revert configuration back to saved"""
        self._load_config(self.patchConfigs)

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

    def style_patcher(self, patcher, bold=False, italics=False):
        """Set the patcher label to bold and/or italicized font. Called from a
        patcher when it's new or detects that it has something new in its
        list."""
        self.gPatchers.lb_style_font_at_index(
            self._gui_patchers.index(patcher), bold=bold, italics=italics)

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
        # Ctrl+A - select all items of the current patchers (or deselect them
        # if Shift is also held)
        if wrapped_evt.is_cmd_down and wrapped_evt.key_code == ord(u'A'):
            patcher = self.currentPatcher
            if patcher is not None:
                patcher.mass_select(select=not wrapped_evt.is_shift_down)
                # Otherwise will select 'Alias Plugin Names' ('A' key is
                # pressed!)
                return EventResult.FINISH
