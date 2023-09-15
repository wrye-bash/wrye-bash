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
import webbrowser
from dataclasses import dataclass

from .. import balt, bass, bolt, bosh, bush, env, exception, load_order
from ..balt import DecoratedTreeDict, ImageList, ImageWrapper, colors
from ..bolt import CIstr, FName, GPath_no_norm, text_wrap, top_level_dirs, \
    reverse_dict
from ..bosh import ModInfo, faces
from ..fomod_schema import default_moduleconfig
from ..gui import BOTTOM, CENTER, RIGHT, CancelButton, CheckBox, \
    CheckListBox, DeselectAllButton, DialogWindow, DropDown, EventResult, \
    GridLayout, HBoxedLayout, HLayout, Label, LayoutOptions, ListBox, \
    OkButton, Picture, SearchBar, SelectAllButton, Spacer, Stretch, \
    TextAlignment, TextField, VBoxedLayout, VLayout, bell, AMultiListEditor, \
    MLEList, DocumentViewer, RadioButton, showOk, showError, WrappingLabel, \
    MaybeModalDialogWindow, Tree, HorizontalLine, TreeNode, ImageButton, \
    FileOpen
from ..parsers import CsvParser
from ..update_checker import LatestVersion
from ..wbtemp import TempDir, cleanup_temp_file, new_temp_file

class ImportFaceDialog(DialogWindow):
    """Dialog for importing faces."""
    _min_size = (550, 300)

    def __init__(self, parent, title, fileInfo, faces):
        #--Data
        self.fileInfo = fileInfo
        if faces and not isinstance(next(iter(faces)), str):
            # Keys are FormIDs, convert them to human-readable strings
            self.fdata = {f'{key_fid} {val_face.pcName}': val_face for
                          key_fid, val_face in faces.items()}
        else:
            # Keys are EditorIDs, good to go
            self.fdata = faces
        self.list_items = sorted(self.fdata, key=str.lower)
        #--GUI
        super(ImportFaceDialog, self).__init__(parent, title=title,
                                               sizes_dict=balt.sizes)
        #--List Box
        self.listBox = ListBox(self, choices=self.list_items,
                               onSelect=self.EvtListBox)
        self.listBox.set_min_size(175, 150)
        #--Name,Race,Gender Checkboxes
        fi_flgs = bosh.faces.PCFaces.pcf_flags(
            bass.settings.get('bash.faceImport.flags', 0x4))
        self.nameCheck = CheckBox(self, _('Name'), checked=fi_flgs.pcf_name)
        self.raceCheck = CheckBox(self, _('Race'), checked=fi_flgs.pcf_race)
        self.genderCheck = CheckBox(self, _('Gender'),
            checked=fi_flgs.pcf_gender)
        self.statsCheck = CheckBox(self, _('Stats'), checked=fi_flgs.pcf_stats)
        self.classCheck = CheckBox(self, _('Class'),
            checked=fi_flgs.pcf_class)
        #--Name, Race, Gender Text
        self.nameText = Label(self, '-----------------------------')
        self.raceText = Label(self, '')
        self.genderText = Label(self, '')
        self.statsText = Label(self, '')
        self.classText = Label(self, '')
        #--Other
        importButton = OkButton(self, btn_label=_('Import'))
        importButton.on_clicked.subscribe(self.DoImport)
        self.picture = Picture(self, 350, 210, scaling=2) ##: unused
        GridLayout(border=4, stretch_cols=[0, 1], stretch_rows=[0], items=[
            # Row 1
            ((self.listBox, LayoutOptions(row_span=2, expand=True)),
             (self.picture, LayoutOptions(col_span=2, expand=True))),
            # Row 2
            (None,  # note the row_span in the prev row
             GridLayout(h_spacing=4, v_spacing=2, stretch_cols=[1], items=[
                 (self.nameCheck, self.nameText),
                 (self.raceCheck, self.raceText),
                 (self.genderCheck, self.genderText),
                 (self.statsCheck, self.statsText),
                 (self.classCheck, self.classText)]),
             (VLayout(spacing=4, items=[importButton, CancelButton(self)]),
              LayoutOptions(h_align=RIGHT, v_align=BOTTOM)))
        ]).apply_to(self)

    def EvtListBox(self, lb_selection_dex, lb_selection_str):
        """Responds to listbox selection."""
        item = self.list_items[lb_selection_dex]
        face = self.fdata[item]
        self.nameText.label_text = face.pcName
        self.raceText.label_text = face.getRaceName()
        self.genderText.label_text = face.getGenderName()
        self.statsText.label_text = _('Health') + f' {face.health}'
        itemImagePath = bass.dirs['mods'].join('Docs', 'Images', f'{item}.jpg')
        # TODO(ut): any way to get the picture ? see mod_links.Mod_Face_Import
        self.picture.set_bitmap(itemImagePath)
        self.listBox.lb_select_index(lb_selection_dex)

    def DoImport(self):
        """Imports selected face into save file."""
        selections = self.listBox.lb_get_selections()
        if not selections:
            bell()
            return
        itemDex = selections[0]
        item = self.list_items[itemDex]
        #--Do import
        pc_flags = bosh.faces.PCFaces.pcf_flags() # make a copy of PCFaces flags
        pc_flags.pcf_hair = pc_flags.pcf_eye = True
        pc_flags.pcf_name = self.nameCheck.is_checked
        pc_flags.pcf_race = self.raceCheck.is_checked
        pc_flags.pcf_gender = self.genderCheck.is_checked
        pc_flags.pcf_stats = self.statsCheck.is_checked
        pc_flags.pcf_iclass = self.classCheck.is_checked
        #deprint(flags.getTrueAttrs())
        bass.settings[u'bash.faceImport.flags'] = int(pc_flags)
        bosh.faces.PCFaces.save_setFace(self.fileInfo, self.fdata[item],
                                        pc_flags)
        showOk(self, _('Face imported.'), self.fileInfo.fn_key)
        self.accept_modal()

#------------------------------------------------------------------------------
class CreateNewProject(DialogWindow):
    title = _(u'New Project')
    def __init__(self, parent):
        self._parent = parent
        super(CreateNewProject, self).__init__(parent)
        # Build a list of existing directories. The text control will use this
        # to change background color when name collisions occur.
        self.existingProjects = {x for x in  ##: use idata?
                                 top_level_dirs(bass.dirs[u'installers'])}
        #--Attributes
        self._project_name = TextField(self, _('Project Name Goes Here'))
        self._project_name.on_text_changed.subscribe(
            self.OnCheckProjectsColorTextCtrl)
        self._check_esp = CheckBox(self, _('Blank.esp'), checked=True,
            chkbx_tooltip=_('Include a blank plugin file with only '
                            '%(game_master)s as a master in the project.') % {
                'game_master': bush.game.master_file})
        self._check_esp_masterless = CheckBox(self, _('Blank Masterless.esp'),
            chkbx_tooltip=_('Include a blank plugin file without any masters '
                            'in the project.'))
        self._check_wizard = CheckBox(self, _('Blank wizard.txt'),
            chkbx_tooltip=_('Include a blank BAIN wizard in the project.'))
        self._check_fomod = CheckBox(self, _('Blank ModuleConfig.xml'),
            chkbx_tooltip=_('Include a blank FOMOD config in the project.'))
        self._check_wizard_images = CheckBox(self,
            _('Wizard Images Directory'), chkbx_tooltip=_(
                'Include an empty Wizard Images directory in the project.'))
        self._check_docs = CheckBox(self, _('Docs Directory'),
            chkbx_tooltip=_('Include an empty Docs directory in the project.'))
        for checkbox in (self._check_esp, self._check_esp_masterless,
                         self._check_wizard):
            checkbox.on_checked.subscribe(self.OnCheckBoxChange)
        # Panel Layout
        self.ok_button = OkButton(self)
        self.ok_button.on_clicked.subscribe(self.OnClose)
        VLayout(border=5, spacing=5, items=[
            (VBoxedLayout(self,
                title=_(u'What do you want to name the new project?'),
                item_expand=True, item_weight=1, items=[
                    self._project_name,
                ]), LayoutOptions(expand=True)),
            VBoxedLayout(self, spacing=5,
                title=_('What do you want to add to the new project?'),
                items=[
                    self._check_esp, self._check_esp_masterless,
                    self._check_wizard, self._check_fomod,
                    self._check_wizard_images, self._check_docs,
                ]),
            Stretch(),
            (HLayout(spacing=5, items=[self.ok_button, CancelButton(self)]),
             LayoutOptions(h_align=CENTER))
        ]).apply_to(self, fit=True)
        # Dialog Icon Handlers
        self.set_icon(ImageWrapper(bass.dirs['images'].join(
            'diamond_red_off.png')).GetIcon())
        self.OnCheckBoxChange()
        self.OnCheckProjectsColorTextCtrl(self._project_name.text_content)

    def OnCheckProjectsColorTextCtrl(self, new_text):
        projectName = FName(new_text)
        if existing := projectName in self.existingProjects:
            self._project_name.set_background_color(colors['default.warn'])
            self._project_name.tooltip = _('There is already a project with '
                                           'that name!')
        else:
            self._project_name.reset_background_color()
            self._project_name.tooltip = None
        self.ok_button.enabled = not existing

    def OnCheckBoxChange(self, _is_checked=None):
        """Change the DialogWindow icon to represent what the project status
        will be when created. """
        if self._check_esp.is_checked or self._check_esp_masterless.is_checked:
            img_fname = ('diamond_red_off' +
                         ('_wiz' if self._check_wizard.is_checked else ''))
        else:
            img_fname = 'diamond_grey_off'
        self.set_icon(ImageWrapper(bass.dirs['images'].join(
            img_fname + '.png')).GetIcon())

    def OnClose(self):
        """ Create the New Project and add user specified extras. """
        projectName = self._project_name.text_content.strip()
        # Destination project directory in installers dir
        projectDir = bass.dirs[u'installers'].join(projectName)
        if projectDir.exists():
            showError(self, _(
                'There is already a project with that name!') + '\n' + _(
                'Pick a different name for the project and try again.'))
            return
        # Create project in temp directory, so we can move it via
        # Shell commands (UAC workaround) ##: TODO(ut) needed?
        with TempDir() as tmp_dir:
            tmp_project = GPath_no_norm(tmp_dir).join(projectName)
            # Create the directory first, otherwise some of the file creation
            # calls below may race and cause undebuggable issues otherwise
            tmp_project.makedirs()
            blank_esp_name = f'Blank, {bush.game.display_name}.esp'
            if self._check_esp.is_checked:
                bosh.modInfos.create_new_mod(blank_esp_name,
                    dir_path=tmp_project)
            blank_ml_name = f'Blank, {bush.game.display_name} (masterless).esp'
            if self._check_esp_masterless.is_checked:
                bosh.modInfos.create_new_mod(blank_ml_name,
                    dir_path=tmp_project, wanted_masters=[])
            if self._check_wizard.is_checked:
                wizardPath = tmp_project.join('wizard.txt')
                with wizardPath.open('w', encoding='utf-8') as out:
                    out.write(f'; {projectName} BAIN Wizard Installation '
                              f'Script\n')
                    out.write(f'; Created by Wrye Bash v{bass.AppVersion}\n')
                    # Put an example SelectPlugin statement in if possible
                    if self._check_esp.is_checked:
                        out.write(f'SelectPlugin "{blank_esp_name}"\n')
                    if self._check_esp_masterless.is_checked:
                        out.write(f'SelectPlugin "{blank_ml_name}"\n')
            if self._check_fomod.is_checked:
                fomod_path = tmp_project.join('fomod')
                fomod_path.makedirs()
                module_config_path = fomod_path.join('ModuleConfig.xml')
                with module_config_path.open('w', encoding='utf-8') as out:
                    out.write(default_moduleconfig % {
                        'fomod_proj': projectName, 'wb_ver': bass.AppVersion,
                    })
            if self._check_wizard_images.is_checked:
                tmp_project.join('Wizard Images').makedirs()
            if self._check_docs.is_checked:
                tmp_project.join('Docs').makedirs()
            # HACK: shellMove fails unless it has at least one file - means
            # creating an empty project fails silently unless we make one
            # TODO(lo): See if this is still necessary with IFileOperation
            has_files = bool([*tmp_project.ilist()])
            if not has_files:
                tmp_project.join('temp_hack').makedirs()
            # Move into the target location
            env.shellMove({tmp_project: projectDir}, parent=self)
        if not has_files:
            projectDir.join('temp_hack').rmtree(safety='temp_hack')
        fn_result_proj = FName(projectDir.stail)
        new_installer_order = 0
        sel_installers = self._parent.GetSelectedInfos()
        if sel_installers:
            new_installer_order = sel_installers[-1].order + 1
        ##: This is mostly copy-pasted from InstallerArchive_Unpack
        with balt.Progress(_('Creating Project...')) as prog:
            self._parent.data_store.new_info(fn_result_proj, progress=prog,
                install_order=new_installer_order)
        self._parent.RefreshUI(detail_item=fn_result_proj)
        self._parent.SelectItemsNoCallback([fn_result_proj])

#------------------------------------------------------------------------------
class CreateNewPlugin(DialogWindow):
    """Dialog for creating a new plugin, allowing the user to select extension,
    name and flags."""
    title = _(u'New Plugin')
    _def_size = (400, 500)

    def __init__(self, parent):
        super(CreateNewPlugin, self).__init__(parent,
            icon_bundle=balt.Resources.bashBlue, sizes_dict=balt.sizes)
        self._parent_window = parent
        self._plugin_ext = DropDown(self, value='.esp',
            choices=sorted(bush.game.espm_extensions), dd_tooltip=_(
                'Select which extension the plugin will have.'))
        self._plugin_ext.on_combo_select.subscribe(self._handle_plugin_ext)
        self._plugin_name = TextField(self, _(u'New Plugin'),
            alignment=TextAlignment.RIGHT)
        # Start with the plugin field focused (so that a simple Enter press
        # will complete the process immediately) and all text selected (so that
        # the user can immediately start typing the plugin name they actually
        # want)
        self._plugin_name.set_focus()
        self._plugin_name.select_all_text()
        self._esm_flag = CheckBox(self, _(u'ESM Flag'),
            chkbx_tooltip=_(u'Whether or not the the resulting plugin will be '
                            u'a master, i.e. have the ESM flag.'))
        # Completely hide the ESL checkbox for non-ESL games, but check it by
        # default for ESL games, since one of the most common use cases for
        # this command on those games is to create BSA-loading dummies.
        self._esl_flag = CheckBox(self, _(u'ESL Flag'),
            chkbx_tooltip=_(u'Whether or not the resulting plugin will be '
                            u'light, i.e have the ESL flag.'),
            checked=bush.game.has_esl)
        self._esl_flag.visible = bush.game.has_esl
        self._master_search = SearchBar(self, hint=_('Search Masters'))
        self._master_search.on_text_changed.subscribe(self._handle_search)
        self._masters_box = CheckListBox(self)
        # Initially populate the masters list, checking only the game master
        self._masters_dict = {m: m == bush.game.master_file for m in
                              load_order.cached_lo_tuple()}
        self._masters_box.set_all_items(self._masters_dict)
        # Only once that's done do we subscribe - avoid all the initial events
        self._masters_box.on_box_checked.subscribe(self._handle_master_checked)
        select_all_btn = SelectAllButton(self,
            btn_tooltip=_(u'Select all plugins that are visible with the '
                          u'current search term.'))
        select_all_btn.on_clicked.subscribe(
            lambda: self._handle_mass_select(mark_active=True))
        deselect_all_btn = DeselectAllButton(self,
            btn_tooltip=_(u'Deselect all plugins that are visible with the '
                          u'current search term.'))
        deselect_all_btn.on_clicked.subscribe(
            lambda: self._handle_mass_select(mark_active=False))
        self._ok_btn = OkButton(self)
        self._ok_btn.on_clicked.subscribe(self._handle_ok)
        self._too_many_masters = Label(self, u'')
        self._too_many_masters.set_foreground_color(colors[u'default.warn'])
        self._too_many_masters.visible = False
        VLayout(border=6, spacing=6, item_expand=True, items=[
            HLayout(spacing=4, items=[
                (self._plugin_name, LayoutOptions(weight=1)),
                self._plugin_ext,
            ]),
            VBoxedLayout(self, title=_(u'Flags'), spacing=4, items=[
                self._esm_flag, self._esl_flag,
            ]),
            (HBoxedLayout(self, title=_(u'Masters'), spacing=4,
                item_expand=True, items=[
                    (VLayout(item_expand=True, spacing=4, items=[
                        self._master_search,
                        (self._masters_box, LayoutOptions(weight=1)),
                    ]), LayoutOptions(weight=1)),
                    VLayout(spacing=4, items=[
                        select_all_btn, deselect_all_btn,
                    ]),
            ]), LayoutOptions(weight=1)),
            VLayout(item_expand=True, items=[
                self._too_many_masters,
                HLayout(spacing=5, item_expand=True, items=[
                    Stretch(), self._ok_btn, CancelButton(self)
                ]),
            ]),
        ]).apply_to(self)

    @property
    def _chosen_masters(self):
        """Returns a generator yielding all checked masters."""
        return (k for k, v in self._masters_dict.items() if v)

    def _check_master_limit(self):
        """Checks if the current selection of masters exceeds the game's master
        limit and, if so, disables the OK button and shows a warning
        message."""
        count_checked = len(list(self._chosen_masters))
        count_limit = bush.game.Esp.master_limit
        limit_exceeded = count_checked > count_limit
        self._ok_btn.enabled = not limit_exceeded
        self._too_many_masters.visible = limit_exceeded
        if limit_exceeded:
            # Only update if limit exceeded to avoid the wx update/redraw cost
            self._too_many_masters.label_text = _(
                'Too many masters: %(count_checked)d checked, but only '
                '%(count_limit)d are allowed by the game.') % {
                'count_checked': count_checked, 'count_limit': count_limit}
        self.update_layout()

    def _handle_plugin_ext(self, new_p_ext):
        """Internal callback to handle a change in extension."""
        # Enable the flags by default, but don't mess with their checked state
        p_is_esl = new_p_ext == '.esl'
        p_is_master = p_is_esl or new_p_ext == '.esm'
        # For .esm and .esl files, force-check the ESM flag
        if p_is_master:
            self._esm_flag.is_checked = True
        self._esm_flag.enabled = not p_is_master
        # For .esl files, force-check the ESL flag
        if p_is_esl:
            self._esl_flag.is_checked = True
        self._esl_flag.enabled = not p_is_esl

    def _handle_mass_select(self, mark_active):
        """Internal callback to handle the Select/Deselect All buttons."""
        self._masters_box.set_all_checkmarks(checked=mark_active)
        for m in self._masters_box.lb_get_str_items():
            # Update only visible items!
            self._masters_dict[FName(m)] = mark_active
        self._check_master_limit()

    def _handle_master_checked(self, master_index):
        """Internal callback to update the dict we use to track state,
        independent of the contents of the masters box."""
        mast_name = self._masters_box.lb_get_str_item_at_index(master_index)
        mast_checked = self._masters_box.lb_is_checked_at_index(master_index)
        self._masters_dict[FName(mast_name)] = mast_checked
        self._check_master_limit()

    def _handle_search(self, search_str):
        """Internal callback used to repopulate the masters box whenever the
        text in the search bar changes."""
        lower_search_str = search_str.strip().lower()
        # Case-insensitively filter based on the keys, then update the box
        new_m_items = {k: v for k, v in self._masters_dict.items() if
                       lower_search_str in k.lower()}
        self._masters_box.set_all_items(new_m_items)

    def _handle_ok(self):
        """Internal callback to handle the OK button."""
        pw = self._parent_window
        pl_name = self._plugin_name.text_content + self._plugin_ext.get_value()
        newName, root = ModInfo.validate_filename_str(pl_name)
        if root is None:
            showError(self, newName)
            self._plugin_name.set_focus()
            self._plugin_name.select_all_text()
            return EventResult.FINISH # leave the dialog open
        chosen_name = ModInfo.unique_name(newName)
        windowSelected = pw.GetSelected()
        pw.data_store.create_new_mod(chosen_name, windowSelected,
            with_esm_flag=self._esm_flag.is_checked,
            with_esl_flag=self._esl_flag.is_checked,
            wanted_masters=[*map(FName, self._chosen_masters)])
        if windowSelected:  # assign it the group of the first selected mod
            mod_group = pw.data_store.table.getColumn(u'group')
            mod_group[chosen_name] = mod_group.get(windowSelected[0], u'')
        pw.ClearSelected(clear_details=True)
        pw.RefreshUI(redraw=[chosen_name], refreshSaves=False)

#------------------------------------------------------------------------------
class ExportScriptsDialog(DialogWindow):
    """Dialog for exporting script sources from a plugin."""
    title = _('Export Scripts Options')

    def __init__(self, parent):
        super().__init__(parent)
        self._skip_prefix = TextField(self)
        self._skip_prefix.text_content = bass.settings[
            'bash.mods.export.skip']
        self._remove_prefix = TextField(self)
        self._remove_prefix.text_content = bass.settings[
            'bash.mods.export.deprefix']
        self._skip_comments = CheckBox(self, _('Filter Out Comments'),
          chkbx_tooltip=_('Whether or to include comments in the exported '
                          'scripts.'))
        self._skip_comments.is_checked = bass.settings[
            'bash.mods.export.skipcomments']
        msg = _('Removes a prefix from the exported file names, e.g. enter '
                'cob to save script cobDenockInit as DenockInit.txt rather '
                'than as cobDenockInit.txt (case-insensitive, leave blank to '
                'not remove any prefix):')
        ok_button = OkButton(self)
        ok_button.on_clicked.subscribe(self._on_ok)
        VLayout(border=6, spacing=4, items=[
            Label(self, _('Skip prefix (leave blank to not skip any), '
                          'case-insensitive):')),
            (self._skip_prefix, LayoutOptions(expand=True)),
            Spacer(10),
            Label(self, text_wrap(msg, 80)),
            (self._remove_prefix, LayoutOptions(expand=True)),
            Spacer(10),
            self._skip_comments, Stretch(),
            (HLayout(spacing=4, items=[
                ok_button,
                CancelButton(self),
            ]), LayoutOptions(h_align=RIGHT)),
        ]).apply_to(self, fit=True)

    def _on_ok(self):
        pfx_skip = self._skip_prefix.text_content.strip()
        bass.settings['bash.mods.export.skip'] = pfx_skip
        pfx_remove = self._remove_prefix.text_content.strip()
        bass.settings['bash.mods.export.deprefix'] = pfx_remove
        cmt_skip = self._skip_comments.is_checked
        bass.settings['bash.mods.export.skipcomments'] = cmt_skip

#------------------------------------------------------------------------------
class _AWBMLE(AMultiListEditor):
    """Base class for multi-list editors, passing required parameters that
    depend on balt automatically."""
    def __init__(self, parent, *, data_desc: str, list_data: list[MLEList],
            **kwargs):
        cu_bitmaps = tuple(balt.images[x].get_bitmap() for x in (
            'square_check.16', 'square_empty.16'))
        super().__init__(parent, data_desc=data_desc, list_data=list_data,
            check_uncheck_bitmaps=cu_bitmaps, sizes_dict=balt.sizes,
            icon_bundle=balt.Resources.bashBlue, **kwargs)

class _ABainMLE(_AWBMLE):
    """Base class for BAIN-related multi-list editors. Automatically converts
    results back to CIstrs."""
    def show_modal(self):
        # Add the CIstrs we removed in __init__ (see map(str)'s below) back in
        result = super().show_modal()
        final_lists = [list(map(CIstr, l)) for l in result[1:]]
        return result[0], *final_lists

#------------------------------------------------------------------------------
class SyncFromDataEditor(_ABainMLE):
    """Template for a multi-list editor for Sync From Data."""
    title = _('Sync From Data - Preview')
    _def_size = (450, 600)

    def __init__(self, parent, *, pkg_missing: list[CIstr],
            pkg_mismatched: list[CIstr], pkg_name: str):
        # Note the map(str) usages to get rid of CIstr for gui/wx, which we
        # later have to recreate in show_modal
        del_data = MLEList(
            mlel_title=_('Files To Delete (%(missing_count)d):') % {
                'missing_count': len(pkg_missing)},
            mlel_desc=_('Uncheck files to keep them in the package.'),
            mlel_items=list(map(str, pkg_missing)))
        upd_data = MLEList(
            mlel_title=_('Files To Update (%(mismatched_count)d):') % {
                'mismatched_count': len(pkg_mismatched)},
            mlel_desc=_('Uncheck files to keep them unchanged in the '
                        'package.'),
            mlel_items=list(map(str, pkg_mismatched)))
        sync_desc = _('Update %(target_package)s according to '
                      '%(data_folder)s directory?') % {
            'target_package': pkg_name, 'data_folder': bush.game.mods_dir}
        sync_desc += '\n' + _('Uncheck any files you want to keep unchanged.')
        super().__init__(parent, data_desc=sync_desc,
            list_data=[del_data, upd_data], ok_label=_('Update'))

#------------------------------------------------------------------------------
class CleanDataEditor(_ABainMLE):
    """Template for a multi-list editor for Clean Data."""
    title = _('Clean Data - Preview')
    _def_size = (450, 500)

    def __init__(self, parent, *, unknown_files: list[CIstr]):
        mdir_fmt = {'data_folder': bush.game.mods_dir}
        to_move_data = MLEList(
            mlel_title=_('Files To Move (%(to_move_count)d):') % {
                'to_move_count': len(unknown_files)},
            mlel_desc=_('Uncheck any files you want to keep in the '
                        '%(data_folder)s folder.') % mdir_fmt,
            mlel_items=list(map(str, unknown_files)))
        super().__init__(parent, list_data=[to_move_data],
            data_desc=_('Move the following files out of the %(data_folder)s '
                        'folder?') % mdir_fmt, ok_label=_('Move'))

#------------------------------------------------------------------------------
class MonitorExternalInstallationEditor(_ABainMLE):
    """Template for a multi-list editor for Monitor External Installation."""
    title = _('Monitor External Installation - Result')
    _def_size = (450, 600)

    def __init__(self, parent, *, new_files: list[CIstr],
            changed_files: list[CIstr], touched_files: list[CIstr],
            deleted_files: list[CIstr]):
        mdir_fmt = {'data_folder': bush.game.mods_dir}
        newf_data = MLEList(
            mlel_title=_('New Files (%(new_file_cnt)d):') % {
                'new_file_cnt': len(new_files)},
            mlel_desc=_('These files are newly added to the %(data_folder)s '
                        'folder. Uncheck any that you want to '
                        'skip.') % mdir_fmt,
            mlel_items=list(map(str, new_files)))
        changedf_data = MLEList(
            mlel_title=_('Changed Files (%(chg_file_cnt)d):') % {
                'chg_file_cnt': len(changed_files)},
            mlel_desc=_('These files were modified. Uncheck any that you want '
                        'to skip.'),
            mlel_items=list(map(str, changed_files)))
        touchedf_data = MLEList(
            mlel_title=_('Touched Files (%(tch_file_cnt)d):') % {
                'tch_file_cnt': len(touched_files)},
            mlel_desc=_('These files were not changed, but had their '
                        'modification time altered. These files were most '
                        'likely included in the external installation, but '
                        'were identical to the ones that already existed in '
                        'the %(data_folder)s folder.') % mdir_fmt,
            mlel_items=list(map(str, touched_files)))
        deletedf_data = MLEList(
            mlel_title=_('Deleted Files (%(del_file_cnt)d):') % {
                'del_file_cnt': len(deleted_files)},
            mlel_desc=_("These files were deleted. BAIN does not have the "
                        "capability to remove files when installing, so these "
                        "deletions cannot be packaged into a BAIN project. "
                        "You may want to use 'Sync From Data...' to remove "
                        "them from their origin packages."),
            mlel_items=list(map(str, deleted_files)))
        mei_desc = _('The following changes were detected in the '
                     '%(data_folder)s folder. Do you want to create a project '
                     'from them?') % mdir_fmt
        # Only show an OK button if we only have deleted files
        any_non_deleted = bool(new_files or changed_files or touched_files)
        ok_btn_label = _('Create Project') if any_non_deleted else _('OK')
        cancel_btn_label = _('Cancel') if any_non_deleted else None
        super().__init__(parent, data_desc=mei_desc,
            list_data=[newf_data, changedf_data, touchedf_data, deletedf_data],
            ok_label=ok_btn_label, cancel_label=cancel_btn_label)

#------------------------------------------------------------------------------
class DeactivateBeforePatchEditor(_AWBMLE):
    """Template for a multi-list editor for pre-BP deactivation of plugins."""
    title = _('Deactivate Prior to Patching')
    _def_size = (450, 600)

    def __init__(self, parent, *, plugins_mergeable: list[FName],
            plugins_nomerge: list[FName], plugins_deactivate: list[FName]):
        pm_data = MLEList(
            mlel_title=_('Mergeable (%(plgn_cnt)d):') % {
                'plgn_cnt': len(plugins_mergeable)},
            mlel_desc=_('These plugins are mergeable. It is suggested that '
                        'they be deactivated and merged into the patch. This '
                        'helps avoid the maximum plugin limit.'),
            mlel_items=list(map(str, plugins_mergeable)))
        pn_data = MLEList(
            mlel_title=_("Mergeable, but Tagged 'NoMerge' (%(plgn_cnt)d):") % {
                'plgn_cnt': len(plugins_nomerge)},
            mlel_desc=_("These plugins are mergeable, but have been tagged "
                        "with 'NoMerge'. They should be deactivated before "
                        "building the patch, imported into it and reactivated "
                        "afterwards."),
            mlel_items=list(map(str, plugins_nomerge)))
        pd_data = MLEList(
            mlel_title=_("Tagged 'Deactivate' (%(plgn_cnt)d):") % {
                'plgn_cnt': len(plugins_deactivate)},
            mlel_desc=_("These mods have been tagged with 'Deactivate'. They "
                        "should be deactivated and merged or imported into "
                        "the Bashed Patch."),
            mlel_items=list(map(str, plugins_deactivate)))
        dbp_desc = _('The following plugins should be deactivated prior to '
                     'building the Bashed Patch.')
        super().__init__(parent, data_desc=dbp_desc,
            list_data=[pm_data, pn_data, pd_data], cancel_label=_('Skip'))

    def show_modal(self):
        # Add the FNames we removed in __init__ (see map(str)'s above) back in
        result = super().show_modal()
        final_lists = [list(map(FName, l)) for l in result[1:]]
        return result[0], *final_lists

#------------------------------------------------------------------------------
_uc_css = """body {
    max-width: 650px;
    line-height: 1.5;
    font-size: 16px;
    color: #444;
}
h1, h2, h3 { line-height: 1.2 }
a:link { text-decoration: none; }
a:hover { text-decoration: underline; }
"""

class UpdateNotification(DialogWindow):
    """A notification dialog showing the user information about a new version
    of Wrye Bash."""
    title = _('New Version Available!')
    _min_size = (400, 400)
    _def_size = (500, 500)

    def __init__(self, parent, new_version: LatestVersion):
        super().__init__(parent, icon_bundle=balt.Resources.bashBlue,
            sizes_dict=balt.sizes)
        self._do_quit = False
        new_ver_msg = _('A new version of Wrye Bash, version %(new_wb_ver)s, '
                        'is available! You are currently using version '
                        '%(curr_wb_ver)s.') % {
            'new_wb_ver': new_version.wb_version,
            'curr_wb_ver': bass.AppVersion,
        }
        # Write the changelog into a temp file, we'll clean it up when we close
        # the notification
        self._temp_html = new_temp_file(temp_prefix='wb_changes',
            temp_suffix='.html')
        with open(self._temp_html, 'w', encoding='utf-8') as out:
            out.write(bolt.html_start % (self.title, _uc_css))
            out.write(new_version.wb_changes)
            out.write(bolt.html_end)
        self._changes_viewer = DocumentViewer(self, balt.get_dv_bitmaps())
        self._changes_viewer.try_load_html(self._temp_html)
        back_btn, forward_btn, reload_btn = self._changes_viewer.get_buttons()
        # Generate the download location radio buttons
        self._download_url = ''
        self._dl_btn_to_url = {}
        self._url_buttons = []
        for i, download_info in enumerate(new_version.wb_downloads):
            if not download_info.should_show_download():
                # The download isn't compatible with this system, skip it
                continue
            dl_name = download_info.download_name
            dl_url = download_info.download_url
            if i == 0:
                # The first one is the default
                self._download_url = dl_url
                rbtn = RadioButton(self, dl_name, is_group=True)
                rbtn.is_checked = True
            else:
                rbtn = RadioButton(self, dl_name)
            rbtn.tooltip = _('Download from %(dl_name)s (%(dl_url)s).') % {
                'dl_name': dl_name, 'dl_url': dl_url}
            rbtn.on_checked.subscribe(self._on_download_opt_changed)
            self._url_buttons.append(rbtn)
            self._dl_btn_to_url[rbtn] = dl_url
        # Ensure the downloads list is never empty, which would break the
        # entire update notification popup
        if not self._url_buttons:
            raise RuntimeError('No download is available on this system. '
                               'latest.json has been misconfigured, please '
                               'report this to the Wrye Bash maintainers.')
        quit_btn = OkButton(self, _('Quit and Download'),
            btn_tooltip=_('Close Wrye Bash and open the selected download '
                          'option in your default web browser.'))
        quit_btn.on_clicked.subscribe(self._on_quit_and_download)
        VLayout(border=4, spacing=6, item_expand=True, items=[
            ##: Make this a WrappingLabel, depends on inf-190-bye-listboxes
            (Label(self, new_ver_msg), LayoutOptions(h_align=CENTER)),
            (HBoxedLayout(self, title=_('Release Notes'), item_expand=True,
                items=[(self._changes_viewer, LayoutOptions(weight=1))]),
             LayoutOptions(weight=1)),
            HBoxedLayout(self, title=_('Download Options'), spacing=6,
                items=self._url_buttons),
            HLayout(spacing=6, item_expand=True, items=[
                back_btn, forward_btn, reload_btn, Stretch(), quit_btn,
                CancelButton(self, _('Ignore')),
            ]),
        ]).apply_to(self)

    def _on_download_opt_changed(self, _checked):
        """Internal callback, called when one of the radio buttons for the
        download locations is changed."""
        for url_btn in self._url_buttons:
            if url_btn.is_checked:
                self._download_url = self._dl_btn_to_url[url_btn]
                break

    def _on_quit_and_download(self):
        """Internal callback, called when the Quit and Download button is
        pressed."""
        webbrowser.open(self._download_url)
        self._do_quit = True

    def show_modal(self):
        super().show_modal()
        # Clean up the temp file we used to store the HTML and quit WB if the
        # Quit and Download button was pressed
        cleanup_temp_file(self._temp_html)
        if self._do_quit:
            balt.Link.Frame.exit_wb()

#------------------------------------------------------------------------------
@dataclass(slots=True, kw_only=True)
class _ChangeData:
    """Records a change to some items in a UIList."""
    # An optional description for this change
    change_desc: str | None
    # The ImageList used by the parent UIList that hosts the items that this
    # change happened to
    uil_image_list: ImageList
    # A decorated tree dict storing the items that the change happened to
    changed_items: DecoratedTreeDict
    # The internal key for the parent tab in tabInfo. E.g. 'Mods'
    parent_tab_key: str

def _mk_node_class(node_tab_key: str):
    """Helper for creating a dynamic node class that jumps to an item on the
    tab with the specified key."""
    class _TabTreeNode(TreeNode):
        """A node depicting an item on a certain tab."""
        def on_activated(self):
            try:
                balt.Link.Frame.notebook.SelectPage(node_tab_key,
                    self._node_text)
            except KeyError:
                balt.showError(self._parent_tree,
                    _('%(target_item)s could not be found.') % {
                        'target_item': self._node_text},
                    title=_('Cannot Jump to Item'))
            except exception.BoltError:
                pass ##: BSAs tab, ignore for now
            return EventResult.FINISH # Don't collapse/expand nodes
    return _TabTreeNode

class _AChangeHighlightDialog(MaybeModalDialogWindow):
    """Base class for dialogs that highlights certain changes having been
    made to UIList items."""
    _def_size = (350, 400)
    _min_size = (250, 300)

    def __init__(self, parent, *, highlight_changes: list[_ChangeData],
            add_cancel_btn=False):
        super().__init__(parent, stay_over_parent=True, sizes_dict=balt.sizes,
            icon_bundle=balt.Resources.bashBlue)
        ch_layout = VLayout(border=4, spacing=6, item_expand=True)
        labels_to_wrap = []
        for change_data in highlight_changes:
            # First add the description for the change, if any
            if change_data.change_desc:
                desc_label = WrappingLabel(self, change_data.change_desc)
                ch_layout.add(desc_label)
                labels_to_wrap.append(desc_label)
            node_type = _mk_node_class(change_data.parent_tab_key)
            # Then create the actual tree listing the changes, which will take
            # up most of the space
            new_tree = Tree(self, change_data.uil_image_list)
            temp_root = new_tree.root_node
            affected_items = change_data.changed_items
            for hp, (hp_tf, hp_children) in affected_items.items():
                hp_node = temp_root.append_child(hp,
                    child_node_type=node_type)
                hp_node.decorate_node(hp_tf)
                if hp_children:
                    for hpc, hpc_tf in hp_children:
                        hpc_node = hp_node.append_child(hpc,
                            child_node_type=node_type)
                        hpc_node.decorate_node(hpc_tf)
            new_tree.expand_everything()
            ch_layout.add((new_tree, LayoutOptions(weight=1)))
            # Separator between trees and also between the last tree and the OK
            # button
            ch_layout.add(HorizontalLine(self))
        ch_layout.add(HLayout(spacing=6, item_expand=True, items=[
            Stretch(),
            OkButton(self),
            CancelButton(self) if add_cancel_btn else None,
        ]))
        ch_layout.apply_to(self)
        for wl in labels_to_wrap:
            wl.auto_wrap()
        self.update_layout()

class _AModsChangeHighlightDialog(_AChangeHighlightDialog):
    """Version of _AChangeHighlightDialog for the Mods tab."""
    @staticmethod
    def make_change_entry(*, mods_list_images: ImageList,
            mods_change_desc: str, decorated_plugins: DecoratedTreeDict):
        """Helper for creating a _ChangeData object for load order
        sanitizations."""
        return _ChangeData(uil_image_list=mods_list_images,
            change_desc=mods_change_desc, changed_items=decorated_plugins,
            parent_tab_key='Mods')

# Note: we sometimes use 'unnecessary' subclasses here for the separate
# balt.sizes key provided by the unique class name
#------------------------------------------------------------------------------
class _ALORippleHighlightDialog(_AChangeHighlightDialog):
    """Base class for dialogs highlighting when a load order change had a
    'ripple' effect, e.g. deactivating a certain master caused its dependents
    to be deactivated too."""
    _change_title: str
    _change_desc: str

    def __init__(self, parent, *, mods_list_images: ImageList,
            decorated_plugins: DecoratedTreeDict):
        # Only count the additional masters/dependents
        total_affected = sum(len(v[1]) for v in decorated_plugins.values())
        super().__init__(parent, highlight_changes=[_ChangeData(
            uil_image_list=mods_list_images,
            change_desc=self._change_desc % {'num_affected': total_affected},
            changed_items=decorated_plugins, parent_tab_key='Mods')])

class MastersAffectedDialog(_ALORippleHighlightDialog):
    """Dialog shown when a plugin was activated and thus its masters got
    activated too."""
    title = _('Masters Affected')
    _change_desc = _('Wrye Bash automatically activates the masters of '
                     'activated plugins. Activating the following plugins '
                     'thus caused %(num_affected)d master(s) to be activated '
                     'as well.')

class DependentsAffectedDialog(_ALORippleHighlightDialog):
    """Dialog shown when a plugin was deactivated and thus its dependent
    plugins got deactivated too."""
    title = _('Dependents Affected')
    _change_desc = _('Wrye Bash automatically deactivates the dependent '
                     'plugins of deactivated plugins. Deactivating the '
                     'following plugins thus caused %(num_affected)d '
                     'dependent(s) to be deactivated as well.')

#------------------------------------------------------------------------------
class LoadOrderSanitizedDialog(_AModsChangeHighlightDialog):
    """Dialog shown when certain load order problems have been fixed."""
    title = _('Warning: Load Order Sanitized')

#------------------------------------------------------------------------------
class MultiWarningDialog(_AChangeHighlightDialog):
    """Dialog shown when Wrye Bash detected certain problems with a user's
    setup."""
    title = _('Warnings')

    @staticmethod
    def make_change_entry(*, uil_images: ImageList, warn_change_desc: str,
            decorated_items: DecoratedTreeDict, origin_tab_key: str):
        """Helper for creating a _ChangeData object for multi-warning
        dialogs."""
        return _ChangeData(uil_image_list=uil_images,
            change_desc=warn_change_desc, changed_items=decorated_items,
            parent_tab_key=origin_tab_key)

#------------------------------------------------------------------------------
class MasterErrorsDialog(_AModsChangeHighlightDialog):
    """Dialog shown when Wrye Bash detected master errors before building a
    BP."""
    title = _('Master Errors')

#------------------------------------------------------------------------------
class AImportOrderParser(CsvParser):
    """Base class for export/import package order-related classes."""
    _csv_header = _('Package'), (_('Installed? (%(inst_y)s/%(inst_n)s)')
                                 % {'inst_y': 'Y', 'inst_n': 'N'})

class ImportOrderDialog(DialogWindow, AImportOrderParser):
    """Dialog shown when importing package order."""
    title = _('Import Order')
    _key_to_import = {
        'imp_all':       _('Order and Installed Status'),
        'imp_order':     _('Order Only'),
        'imp_installed': _('Installed Status Only'),
    }
    _import_to_key = reverse_dict(_key_to_import)

    def __init__(self, parent):
        super().__init__(parent, icon_bundle=balt.Resources.bashBlue)
        self._bain_parent = parent
        self._import_target_field = TextField(self, hint=_('CSV to import'))
        browse_file_btn = ImageButton(self,
            balt.images['folder.16'].get_bitmap(),
            btn_tooltip=_('Open a file dialog to interactively choose the '
                          'saved package order to import.'))
        browse_file_btn.on_clicked.subscribe(self._handle_browse)
        self._import_what = DropDown(self,
            value=self._key_to_import[
                bass.settings['bash.installers.import_order.what']],
            choices=sorted(self._key_to_import.values()),
            dd_tooltip=_('Select what will be imported.'))
        self._import_what.on_combo_select.subscribe(self._save_import_what)
        self._create_markers = CheckBox(self, checked=bass.settings[
            'bash.installers.import_order.create_markers'],
            chkbx_tooltip=_("If checked, markers (i.e. entries beginning and "
                            "ending with '==') that don't exist will be "
                            "created upon import."))
        ok_btn = OkButton(self)
        ok_btn.on_clicked.subscribe(self._handle_ok)
        VLayout(border=6, spacing=4, item_expand=True, items=[
            HBoxedLayout(self, title=_('File'), spacing=4, items=[
                (self._import_target_field,
                 LayoutOptions(expand=True, weight=1)),
                browse_file_btn,
            ]),
            VBoxedLayout(self, title=_('Options'), spacing=4, item_expand=True,
                items=[
                    HLayout(spacing=4, items=[
                        Label(self, _('Import What?')),
                        (self._import_what,
                         LayoutOptions(expand=True, weight=1)),
                    ]),
                    HLayout(spacing=4, items=[
                        Label(self, _('Create Missing Markers')),
                        self._create_markers,
                    ]),
            ]),
            Stretch(),
            HorizontalLine(self),
            HLayout(spacing=4, item_expand=True, items=[
                Stretch(), ok_btn, CancelButton(self),
            ]),
        ]).apply_to(self, fit=True)

    def _handle_browse(self):
        """Internal callback, opens a file dialog to choose the order file."""
        chosen_order_file = FileOpen.display_dialog(self,
            title=_('Import Order - Choose File'),
            defaultFile='PackageOrder.csv', defaultDir=bass.dirs['patches'],
            wildcard='*.csv')
        if chosen_order_file:
            self._import_target_field.text_content = chosen_order_file.s

    def _save_import_what(self, sel_import_what: str):
        """Internal callback, saves the Import what? value when it's changed so
        that future Import Order dialogs have a fitting default."""
        bass.settings['bash.installers.import_order.what'] = \
            self._import_to_key[sel_import_what]

    def _handle_ok(self):
        """Internal callback, performs the actual reordering etc."""
        imp_path = self._import_target_field.text_content
        if not imp_path: return
        self.first_line = True
        self._partial_package_order = []
        try:
            self.read_csv(imp_path)
        except (exception.BoltError, NotImplementedError):
            balt.showError(self, _('The selected file is not a valid package '
                                   'order CSV export.'),
                title=_('Import Order - Invalid CSV'))
            return
        bain_idata = self._bain_parent.data_store
        reorder_err = bain_idata.reorder_packages(self._partial_package_order)
        bain_idata.refresh_ns()
        self._bain_parent.RefreshUI()
        if reorder_err:
            balt.showError(self, reorder_err, title=_('Import Order - Error'))
        else:
            balt.showInfo(self, _('Imported order and installation status for '
                                  '%(total_imported)d package(s).') % {
                'total_imported': len(self._partial_package_order)},
                title=_('Import Order - Done'))

    def _parse_line(self, csv_fields):
        if self.first_line: # header validation
            self.first_line = False
            if len(csv_fields) != 2:
                raise exception.BoltError(f'Header error: {csv_fields}')
            return
        pkg_fstr, pkg_installed_yn = csv_fields
        bain_idata = self._bain_parent.data_store
        pkg_fname = bolt.FName(pkg_fstr)
        pkg_present = pkg_fname in bain_idata
        pkg_is_marker = pkg_fstr.startswith('==') and pkg_fstr.endswith('==')
        if (self._create_markers.is_checked and pkg_is_marker and
                not pkg_present):
            bain_idata.new_info(pkg_fname, is_mark=True)
            pkg_present = True
        if pkg_present:
            # If we import something other than purely order (and this isn't a
            # marker, which can't be enabled anyways)
            order_only = self._key_to_import['imp_order']
            if (not pkg_is_marker and
                    self._import_what.get_value() != order_only):
                bain_idata[pkg_fname].is_active = pkg_installed_yn == 'Y'
            self._partial_package_order.append(pkg_fname)
