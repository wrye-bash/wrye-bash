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
from . import bEnableWizard, BashFrame
from .constants import installercons
from .. import bass, balt, bosh, bolt, bush, env
from ..balt import colors, bell
from ..bosh import faces
from ..gui import BOTTOM, Button, CancelButton, CENTER, CheckBox, GridLayout, \
    HLayout, Label, LayoutOptions, OkButton, RIGHT, Stretch, TextField, \
    VLayout, DialogWindow, ListBox, Picture

class ImportFaceDialog(DialogWindow):
    """Dialog for importing faces."""
    _min_size = (550, 300)

    def __init__(self, parent, title, fileInfo, faces):
        #--Data
        self.fileInfo = fileInfo
        if faces and isinstance(faces.keys()[0], int):
            self.data = dict((u'%08X %s' % (key,face.pcName),face) for key,face in faces.items())
        else:
            self.data = faces
        self.list_items = sorted(self.data.keys(),key=unicode.lower)
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
        self.nameCheck = CheckBox(self, _(u'Name'), checked=fi_flgs.name)
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
        importButton = Button(self, btn_label=_(u'Import'), default=True)
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
        face = self.data[item]
        self.nameText.label_text = face.pcName
        self.raceText.label_text = face.getRaceName()
        self.genderText.label_text = face.getGenderName()
        self.statsText.label_text = _(u'Health ') + unicode(face.health)
        itemImagePath = bass.dirs['mods'].join(u'Docs', u'Images', '%s.jpg' % item)
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
        pc_flags.name = self.nameCheck.is_checked
        pc_flags.race = self.raceCheck.is_checked
        pc_flags.gender = self.genderCheck.is_checked
        pc_flags.stats = self.statsCheck.is_checked
        pc_flags.iclass = self.classCheck.is_checked
        #deprint(flags.getTrueAttrs())
        bass.settings['bash.faceImport.flags'] = int(pc_flags)
        bosh.faces.PCFaces.save_setFace(self.fileInfo,self.data[item],pc_flags)
        balt.showOk(self, _(u'Face imported.'), self.fileInfo.name.s)
        self.accept_modal()

#------------------------------------------------------------------------------
class CreateNewProject(DialogWindow):
    title = _(u'New Project')
    def __init__(self,parent=None):
        super(CreateNewProject, self).__init__(parent)
        #--Build a list of existing directories
        #  The text control will use this to change background color when name collisions occur
        self.existingProjects = set(x for x in bass.dirs['installers'].list()
                                    if bass.dirs['installers'].join(x).isdir())
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
        self.set_icon(installercons.get_image('off.white.dir').GetIcon())
        self.OnCheckBoxChange()
        self.OnCheckProjectsColorTextCtrl(self.textName.text_content)

    def OnCheckProjectsColorTextCtrl(self, new_text):
        projectName = bolt.GPath(new_text)
        if projectName in self.existingProjects: #Fill this in. Compare this with the self.existingprojects list
            # PY3: See note in basher/constants.py
            self.textName.set_background_color(colors.RED)
            self.textName.tooltip = _(u'There is already a project with that name!')
            self.ok_button.enabled = False
        else:
            self.textName.set_background_color(colors.WHITE)
            self.textName.tooltip = None
            self.ok_button.enabled = True

    def OnCheckBoxChange(self, is_checked=None):
        """Change the DialogWindow icon to represent what the project status
        will be when created. """
        if self.checkEsp.is_checked or self.checkEspMasterless.is_checked:
            if self.checkWizard.is_checked:
                self.set_icon(
                    installercons.get_image('off.white.dir.wiz').GetIcon())
            else:
                self.set_icon(
                    installercons.get_image('off.white.dir').GetIcon())
        else:
            self.set_icon(installercons.get_image('off.grey.dir').GetIcon())

    def OnClose(self):
        """ Create the New Project and add user specified extras. """
        projectName = bolt.GPath(self.textName.text_content.strip())
        projectDir = bass.dirs['installers'].join(projectName)

        if projectDir.exists():
            balt.showError(self, _(
                u'There is already a project with that name!') + u'\n' + _(
                u'Pick a different name for the project and try again.'))
            return

        # Create project in temp directory, so we can move it via
        # Shell commands (UAC workaround)
        tmpDir = bolt.Path.tempDir()
        tempProject = tmpDir.join(projectName)
        if self.checkEsp.is_checked:
            fileName = u'Blank, %s.esp' % bush.game.fsName
            bosh.modInfos.create_new_mod(fileName, directory=tempProject)
        if self.checkEspMasterless.is_checked:
            fileName = u'Blank, %s (masterless).esp' % bush.game.fsName
            bosh.modInfos.create_new_mod(fileName, directory=tempProject,
                                         masterless=True)
        if self.checkWizard.is_checked:
            # Create empty wizard.txt
            wizardPath = tempProject.join(u'wizard.txt')
            with wizardPath.open('w',encoding='utf-8') as out:
                out.write(u'; %s BAIN Wizard Installation Script\n' % projectName)
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
