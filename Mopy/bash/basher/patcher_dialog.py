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
#  Wrye Bash copyright (C) 2005-2009 Wrye, 2010-2026 Wrye Bash Team
#  https://github.com/wrye-bash
#
# =============================================================================
"""Patch dialog"""
from .dialogs import DeleteBPPartsEditor
from .. import balt, bass, bolt, bush, env
from ..balt import Resources
from ..bolt import GPath_no_norm
from ..exception import BoltError, BPConfigError, CancelError, SkipError, \
    BPTooManyMastersError, BPSplitError
from ..gui import BusyCursor, CancelButton, CheckListBox, DeselectAllButton, \
    DialogWindow, EventResult, FileOpen, HLayout, HorizontalLine, Label, \
    LayoutOptions, OkButton, OpenButton, RevertButton, RevertToSavedButton, \
    SaveAsButton, SelectAllButton, Stretch, VLayout, showError, askYes, \
    showWarning, FileSave
from ..patcher.config_patchers import PatchBuilder
from ..patcher.patch_files import PatchFile

# Final list of gui patcher classes, populated in InitPatchers based on game
gpatcher_types = [] #--All gui patchers classes for this game

class PatchDialog(DialogWindow, PatchBuilder):
    """Bash Patch update dialog.

    :type _config_patchers: list[basher.gui_patchers._PatcherPanel]
    """
    _def_size = (600, 600)
    _min_size = (400, 300)

    def __init__(self, parent, bashed_patch: PatchFile, bashed_patches_out,
                 patchConfigs, bp_rdata):
        self._bp_rdata = bp_rdata
        self._bps = bashed_patches_out
        self.parent = parent
        title = _('Update %(bp_name)s') % {
            'bp_name': f'{bashed_patch.fileInfo}'}
        super().__init__(parent, title=title, icon_bundle=Resources.bashBlue,
            sizes_dict=bass.settings)
        patcherNames = [patcher.patcher_name for patcher in gpatcher_types]
        #--GUI elements
        self.gExecute = OkButton(self, btn_label=_('Build Patch'),
                                 on_click=self.PatchExecute)
        # TODO(nycz): somehow move setUAC further into env?
        # Note: for this to work correctly, it needs to be run BEFORE
        # appending a menu item to a menu (and so, needs to be enabled/
        # disabled prior to that as well.
        # TODO(nycz): DEWX - Button.GetHandle
        env.setUAC(self.gExecute._native_widget.GetHandle(), True)
        self.gSelectAll = SelectAllButton(self, on_click=
            lambda: self._mass_select_recursive(True))
        self.gDeselectAll = DeselectAllButton(self, on_click=
            lambda: self._mass_select_recursive(False))
        self.gPatchers = CheckListBox(self, choices=patcherNames,
                                      isSingle=True, onSelect=self.OnSelect)
        self.gPatchers.on_box_checked.subscribe(self.OnCheck)
        conf_buttons = [
            SaveAsButton(self, btn_label=_('Export'),
                         on_click=self._export_conf),
            OpenButton(self, btn_label=_('Import'),
                       on_click=self._import_conf),
            RevertToSavedButton(self, on_click=self._revert_conf),
            RevertButton(self, btn_label=_('Revert To Default'),
                         on_click=self._reset_conf)]
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
            HLayout(spacing=4, items=[Stretch(), *conf_buttons]),
            HLayout(spacing=4, items=[
                Stretch(), self.gExecute, self.gSelectAll, self.gDeselectAll,
                CancelButton(self),
            ]),
        ]).apply_to(self)
        #--Patcher panels
        self._patch_configs = patchConfigs
        with BusyCursor(): # Constructs all the patcher panels, so takes a bit
            self.bashed_patch = bashed_patch
            self._config_patchers = [ptype(bashed_patch, parent_dialog=self)
                                     for ptype in gpatcher_types]
            self._load_patcher_configs(patchConfigs)
        self.currentPatcher = None
        initial_select = min(len(self._config_patchers) - 1, 1)
        if initial_select >= 0:
            # lb_select_index does not fire the callback, so show it ourselves
            self.gPatchers.lb_select_index(initial_select)
            self.ShowPatcher(self._config_patchers[initial_select])

    #--Core -------------------------------
    def _update_ok_btn(self):
        """Enable Build Patch button if at least one patcher is enabled."""
        self.gExecute.enabled = any(p.isEnabled for p in self._config_patchers)

    def ShowPatcher(self,patcher):
        """Show patcher panel."""
        if patcher == self.currentPatcher: return
        if self.currentPatcher is not None:
            self.currentPatcher.visible = False
        patcher.visible = True
        self.update_layout()
        patcher.update_layout()
        self.currentPatcher = patcher

    @balt.conversation
    def PatchExecute(self):
        """Do the patch."""
        self.accept_modal()
        try:
            self.build_patch()
        except CancelError:
            pass
        except BPConfigError as e: # User configured BP incorrectly
            self._error(_(u'The configuration of the Bashed Patch is '
                          u'incorrect.') + f'\n\n{e}')
        except (BoltError, NotImplementedError) as e:
            # Nonfatal error
            self._error(f'{e}')
        except Exception as e: # Fatal error
            self._error(f'{e}')
            raise

    def _error(self, e_msg):
        balt.playSound(self.parent, bass.inisettings['SoundError'])
        bolt.deprint('Exception during Bashed Patch building:', traceback=True)
        showError(self, e_msg, _('Bashed Patch Error'))

    # PatchBuilder overrides - these are the steps that talk to the user ------
    def _get_target_patch(self):
        return self.bashed_patch # set up with its panels in __init__

    def _get_progress(self):
        return balt.Progress(self._bp_name, abort=True)

    def _prepare_patch_files(self):
        try:
            return super()._prepare_patch_files()
        except BPTooManyMastersError as e:
            showError(self, f'{e}',
                title=_('Achievement Unlocked: Modaholic!'))
        except BPSplitError as e:
            showError(self, f'{e}')
        raise CancelError # we reported the error, just abort the build

    def _handle_unneeded_parts(self, parts_to_del):
        """Let the user choose which obsolete parts to delete."""
        ed_ok, ed_parts = DeleteBPPartsEditor.display_dialog(
            self, unneeded_parts=parts_to_del)
        if ed_ok and ed_parts:
            self._bp_rdata |= self.bashed_patch.p_file_minfos.delete_op(
                ed_parts)

    def _start_saving(self, prog):
        prog.setCancel(False, f"{self._bp_name}\n{_('Saving…')}")
        prog(0.9)

    def _save_patch_file(self, patch_file):
        while True:
            try:
                # FIXME will keep displaying a bogus UAC prompt if file is
                # locked - aborting bogus UAC dialog raises SkipError() in
                # shellMove, not sure if ever a Windows or Cancel are raised
                patch_file.safeSave()
                return
            except (CancelError, SkipError, PermissionError):
                ##: Ugly warts below (see also FIXME above)
                m = [_('Wrye Bash encountered an error when saving '
                       '%(patch_name)s.'),
                     '', '',
                     _('Either Wrye Bash needs Administrator Privileges to '
                       'save the file, or the file is in use by another '
                       'process such as %(xedit_name)s.'),
                     '',
                     _('Please close any program that is accessing '
                       '%(patch_name)s, and provide Administrator Privileges '
                       'if prompted to do so.'),
                     '', '',
                     _('Try again?')]
                msg = '\n'.join(m) % {'patch_name': self._bp_name,
                                      'xedit_name': bush.game.Xe.full_name}
                if askYes(self, msg, _('Bashed Patch - Save Error')):
                    continue
                raise # will raise the SkipError which is correctly processed

    def _move_readme(self, temp_readme_dir, temp_readme, readme):
        #--Try moving temp log/readme to Docs dir
        try:
            env.shellMove({temp_readme_dir: readme.head}, parent=self)
        except (CancelError, SkipError):
            # User didn't allow UAC, move to My Games directory instead
            temp_readme_html = temp_readme.root + '.html'
            readme_moves = {
                temp_readme: bass.dirs['saveBase'].join(temp_readme.stail),
                temp_readme_html: bass.dirs['saveBase'].join(
                    temp_readme_html.stail)
            }
            env.shellMove(readme_moves, parent=self)
            readme = bass.dirs['saveBase'].join(readme.stail)
        return readme

    def _show_readme(self, readme):
        shown_log = (readme.root + '.html') if balt.web_viewer_available(
            ) else readme
        balt.playSound(self.parent, bass.inisettings['SoundSuccess'])
        balt.show_log(self.parent, shown_log, self._bp_name, wrye_log=True,
                      asDialog=True)

    def _patch_built(self, patch_names, refreshed):
        self._bps.extend(patch_names)
        # We have to parse the new infos first since the masters may differ
        # note this won't activate the new masters, the caller has to do it
        self._bp_rdata |= refreshed

    # Config Phase overrides and import/export/revert config callbacks
    def _load_patcher_configs(self, patch_configs):
        """Load patchConfigs into the patcher panels - used for the initial
        load and whenever the user imports or reverts the config."""
        super()._load_patcher_configs(patch_configs)
        for index, patcher in enumerate(self._config_patchers):
            self.gPatchers.lb_check_at_index(index, patcher.isEnabled)
        self._update_ok_btn()

    def _export_conf(self):
        """Export the configuration to a user selected dat file."""
        config = self._save_patcher_configs()
        out_dir = bass.dirs['patches']
        outFile = f'{self._bp_name}_Configuration.dat'
        out_dir.makedirs()
        #--File dialog
        outPath = FileSave.display_dialog(self.parent,
            title=_('Export Bashed Patch configuration to:'),
            defaultDir=out_dir, defaultFile=outFile,
            wildcard='*_Configuration.dat')
        if outPath:
            pd = bolt.PickleDict(outPath)
            gkey = GPath_no_norm('Saved Bashed Patch Configuration (Python)')
            pd.pickled_data[gkey] = {'bash.patch.configs': config}
            pd.save()

    __old_key = u'Saved Bashed Patch Configuration'
    __new_key = u'Saved Bashed Patch Configuration (%s)'
    def _import_conf(self):
        """Import the configuration from a user selected dat file."""
        config_dat = f'{self._bp_name}_Configuration.dat'
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
        self._load_patcher_configs(patchConfigs)

    def _revert_conf(self):
        """Revert configuration back to saved"""
        self._load_patcher_configs(self._patch_configs)

    def _reset_conf(self):
        """Revert configuration back to default"""
        self._load_patcher_configs({})

    def _mass_select_recursive(self, select=True):
        """Select or deselect all patchers and entries in patchers with child
        entries."""
        self.gPatchers.set_all_checkmarks(checked=select)
        for patcher in self._config_patchers:
            patcher.mass_select(select=select)
        self._update_ok_btn()

    #--GUI --------------------------------
    def OnSelect(self, lb_selection_dex, _lb_selection_str):
        """Responds to patchers list selection."""
        self.ShowPatcher(self._config_patchers[lb_selection_dex])
        self.gPatchers.lb_select_index(lb_selection_dex)

    def check_patcher(self, patcher, enable_patcher=True):
        """Enable or disable a patcher."""
        self.gPatchers.lb_check_at_index(
            self._config_patchers.index(patcher), enable_patcher)
        self._update_ok_btn()

    def style_patcher(self, patcher, bold=False, italics=False):
        """Set the patcher label to bold and/or italicized font. Called from a
        patcher when it's new or detects that it has something new in its
        list."""
        self.gPatchers.lb_style_font_at_index(
            self._config_patchers.index(patcher), bold=bold, italics=italics)

    def OnCheck(self, lb_selection_dex):
        """Toggle patcher activity state."""
        patcher = self._config_patchers[lb_selection_dex]
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
        if 0 <= mouseItem < len(self._config_patchers):
            gui_patcher = self._config_patchers[mouseItem]
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
