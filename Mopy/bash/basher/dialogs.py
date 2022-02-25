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
#  Wrye Bash copyright (C) 2005-2009 Wrye, 2010-2022 Wrye Bash Team
#  https://github.com/wrye-bash
#
# =============================================================================
from . import bEnableWizard, BashFrame
from .constants import installercons
from .. import bass, balt, bosh, bolt, bush, env, load_order
from ..balt import colors
from ..bolt import GPath_no_norm, top_level_dirs
from ..bosh import faces, ModInfo
from ..gui import BOTTOM, CancelButton, CENTER, CheckBox, GridLayout, \
    HLayout, Label, LayoutOptions, OkButton, RIGHT, Stretch, TextField, \
    VLayout, DialogWindow, ListBox, Picture, DropDown, CheckListBox, \
    HBoxedLayout, SelectAllButton, DeselectAllButton, VBoxedLayout, \
    TextAlignment, SearchBar, bell, EventResult

class ImportFaceDialog(DialogWindow):
    """Dialog for importing faces."""
    _min_size = (550, 300)

    def __init__(self, parent, title, fileInfo, faces):
        #--Data
        self.fileInfo = fileInfo
        if faces and isinstance(next(iter(faces)), int):
            self.fdata = {u'%08X %s' % (key, face.pcName): face for key, face
                          in faces.items()}
        else:
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
            bass.settings.get(u'bash.faceImport.flags', 0x4))
        self.nameCheck = CheckBox(self, _(u'Name'), checked=fi_flgs.pcf_name)
        self.raceCheck = CheckBox(self, _(u'Race'), checked=fi_flgs.race)
        self.genderCheck = CheckBox(self, _(u'Gender'), checked=fi_flgs.gender)
        self.statsCheck = CheckBox(self, _(u'Stats'), checked=fi_flgs.stats)
        self.classCheck = CheckBox(self, _(u'Class'), checked=fi_flgs.iclass)
        #--Name,Race,Gender Text
        self.nameText  = Label(self,u'-----------------------------')
        self.raceText  = Label(self,u'')
        self.genderText  = Label(self,u'')
        self.statsText  = Label(self,u'')
        self.classText  = Label(self,u'')
        #--Other
        importButton = OkButton(self, btn_label=_(u'Import'))
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
        self.statsText.label_text = _(u'Health ') + str(face.health)
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
        pc_flags.hair = pc_flags.eye = True
        pc_flags.pcf_name = self.nameCheck.is_checked
        pc_flags.race = self.raceCheck.is_checked
        pc_flags.gender = self.genderCheck.is_checked
        pc_flags.stats = self.statsCheck.is_checked
        pc_flags.iclass = self.classCheck.is_checked
        #deprint(flags.getTrueAttrs())
        bass.settings[u'bash.faceImport.flags'] = int(pc_flags)
        bosh.faces.PCFaces.save_setFace(self.fileInfo, self.fdata[item],
                                        pc_flags)
        balt.showOk(self, _(u'Face imported.'), self.fileInfo.ci_key)
        self.accept_modal()

#------------------------------------------------------------------------------
class CreateNewProject(DialogWindow):
    title = _(u'New Project')
    def __init__(self,parent=None):
        super(CreateNewProject, self).__init__(parent)
        # Build a list of existing directories. The text control will use this
        # to change background color when name collisions occur.
        self.existingProjects = {GPath_no_norm(x) for x in ##: use idata?
                                 top_level_dirs(bass.dirs[u'installers'])}
        #--Attributes
        self.textName = TextField(self, _(u'New Project Name-#####'))
        self.textName.on_text_changed.subscribe(
            self.OnCheckProjectsColorTextCtrl)
        self.checkEsp = CheckBox(self, _(u'Blank.esp'), checked=True)
        self.checkEspMasterless = CheckBox(self, _(u'Blank Masterless.esp'))
        self.checkWizard = CheckBox(self, _(u'Blank wizard.txt'))
        self.checkWizardImages = CheckBox(self, _(u'Wizard Images Directory'))
        for checkbox in (self.checkEsp, self.checkEspMasterless,
                         self.checkWizard):
            checkbox.on_checked.subscribe(self.OnCheckBoxChange)
        if not bEnableWizard:
            # pywin32 not installed
            self.checkWizard.enabled = False
            self.checkWizardImages.enabled = False
        self.checkDocs = CheckBox(self, _(u'Docs Directory'))
        # Panel Layout
        self.ok_button = OkButton(self)
        self.ok_button.on_clicked.subscribe(self.OnClose)
        VLayout(border=5, spacing=5, items=[
            Label(self, _(u'What do you want to name the new project?')),
            (self.textName, LayoutOptions(expand=True)),
            Label(self, _(u'What do you want to add to the new project?')),
            self.checkEsp, self.checkEspMasterless, self.checkWizard,
            self.checkWizardImages, self.checkDocs, Stretch(),
            (HLayout(spacing=5, items=[self.ok_button, CancelButton(self)]),
             LayoutOptions(h_align=CENTER))
        ]).apply_to(self, fit=True)
        # Dialog Icon Handlers
        self.set_icon(installercons.get_icon(u'off.white.dir'))
        self.OnCheckBoxChange()
        self.OnCheckProjectsColorTextCtrl(self.textName.text_content)

    def OnCheckProjectsColorTextCtrl(self, new_text):
        projectName = bolt.GPath(new_text)
        if projectName in self.existingProjects: #Fill this in. Compare this with the self.existingprojects list
            self.textName.set_background_color(colors[u'default.warn'])
            self.textName.tooltip = _(u'There is already a project with that name!')
            self.ok_button.enabled = False
        else:
            self.textName.reset_background_color()
            self.textName.tooltip = None
            self.ok_button.enabled = True

    def OnCheckBoxChange(self, is_checked=None):
        """Change the DialogWindow icon to represent what the project status
        will be when created. """
        if self.checkEsp.is_checked or self.checkEspMasterless.is_checked:
            img_key = f'off.white.dir' \
                      f'{self.checkWizard.is_checked and ".wiz" or ""}'
        else:
            img_key = 'off.grey.dir'
        self.set_icon(installercons.get_icon(img_key))

    def OnClose(self):
        """ Create the New Project and add user specified extras. """
        projectName = self.textName.text_content.strip()
        # Destination project directory in installers dir
        projectDir = bass.dirs[u'installers'].join(projectName)
        if projectDir.exists():
            balt.showError(self, _(
                u'There is already a project with that name!') + u'\n' + _(
                u'Pick a different name for the project and try again.'))
            return
        # Create project in temp directory, so we can move it via
        # Shell commands (UAC workaround) ##: TODO(ut) needed?
        tmpDir = bolt.Path.tempDir()
        tempProject = tmpDir.join(projectName)
        if (masterless := self.checkEspMasterless.is_checked) or \
                self.checkEsp.is_checked:
            file_body, wanted_masters = f'Blank, {bush.game.displayName}', None
            if masterless:
                file_body = f'{file_body} (masterless)'
                wanted_masters = []
            bosh.modInfos.create_new_mod(f'{file_body}.esp',
                dir_path=tempProject, wanted_masters=wanted_masters)
        if self.checkWizard.is_checked:
            # Create empty wizard.txt
            wizardPath = tempProject.join(u'wizard.txt')
            with wizardPath.open(u'w', encoding=u'utf-8') as out:
                out.write(f'; {projectName} BAIN Wizard Installation Script\n')
        if self.checkWizardImages.is_checked:
            # Create 'Wizard Images' directory
            tempProject.join(u'Wizard Images').makedirs()
        if self.checkDocs.is_checked:
            #Create the 'Docs' Directory
            tempProject.join(u'Docs').makedirs()
        # HACK: shellMove fails unless it has at least one file - means
        # creating an empty project fails silently unless we make one
        has_files = bool(tempProject.list())
        if not has_files: tempProject.join(u'temp_hack').makedirs()
        # Move into the target location
        # TODO(inf) de-wx! Investigate further
        env.shellMove(tempProject, projectDir, parent=self._native_widget)
        BashFrame.iPanel.ShowPanel(canCancel=False, scan_data_dir=True)
        tmpDir.rmtree(tmpDir.s)
        if not has_files:
            projectDir.join(u'temp_hack').rmtree(safety=u'temp_hack')

#------------------------------------------------------------------------------
class CreateNewPlugin(DialogWindow):
    """Dialog for creating a new plugin, allowing the user to select extension,
    name and flags."""
    title = _(u'New Plugin')
    _def_size = (400, 500)

    def __init__(self, parent):
        super(CreateNewPlugin, self).__init__(parent, sizes_dict=balt.sizes)
        self._parent_window = parent
        default_ext = u'.esp'
        self._plugin_ext = DropDown(self, value=default_ext,
            choices=sorted(bush.game.espm_extensions), auto_tooltip=False)
        self._plugin_ext.tooltip = _(u'Select which extension the plugin will '
                                     u'have.')
        self._plugin_ext.on_combo_select.subscribe(self._handle_plugin_ext)
        self._plugin_name = TextField(self, _(u'New Plugin'),
            alignment=TextAlignment.RIGHT)
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
        self._masters_dict = {m.s: m == bush.game.master_file for m in
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
        self._too_many_masters.label_text = _(
            u'Too many masters: %u checked, but only %u are allowed by the '
            u'game.') % (count_checked, count_limit)
        self._too_many_masters.visible = limit_exceeded
        self.update_layout()

    def _handle_plugin_ext(self, new_p_ext):
        """Internal callback to handle a change in extension."""
        # Enable the flags by default, but don't mess with their checked state
        self._esm_flag.enabled = True
        if (isesl := new_p_ext == u'.esl') or new_p_ext == u'.esm':
            # For .esm and .esl files, force-check the ESM flag
            self._esm_flag.enabled = False
            self._esm_flag.is_checked = True
        # For .esl files, force-check the ESL flag
        if isesl: self._esl_flag.is_checked = True
        self._esl_flag.enabled = not isesl

    def _handle_mass_select(self, mark_active):
        """Internal callback to handle the Select/Deselect All buttons."""
        self._masters_box.set_all_checkmarks(checked=mark_active)
        for m in self._masters_box.lb_get_str_items():
            self._masters_dict[m] = mark_active # update only visible items!
        self._check_master_limit()

    def _handle_master_checked(self, master_index):
        """Internal callback to update the dict we use to track state,
        independent of the contents of the masters box."""
        mast_name = self._masters_box.lb_get_str_item_at_index(master_index)
        mast_checked = self._masters_box.lb_is_checked_at_index(master_index)
        self._masters_dict[mast_name] = mast_checked
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
            balt.showError(self, newName)
            self._plugin_name.set_focus()
            self._plugin_name.select_all_text()
            return EventResult.FINISH # leave the dialog open
        chosen_name = ModInfo.unique_name(newName)
        windowSelected = pw.GetSelected()
        pw.data_store.create_new_mod(chosen_name, windowSelected,
            esm_flag=self._esm_flag.is_checked,
            esl_flag=self._esl_flag.is_checked,
            wanted_masters=[bolt.GPath(m) for m in self._chosen_masters])
        if windowSelected:  # assign it the group of the first selected mod
            mod_group = pw.data_store.table.getColumn(u'group')
            mod_group[chosen_name] = mod_group.get(windowSelected[0], u'')
        pw.ClearSelected(clear_details=True)
        pw.RefreshUI(redraw=[chosen_name], refreshSaves=False)
