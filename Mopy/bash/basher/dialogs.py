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
#  Wrye Bash copyright (C) 2005-2009 Wrye, 2010-2019 Wrye Bash Team
#  https://github.com/wrye-bash
#
# =============================================================================

import wx
import string
from . import bEnableWizard, tabInfo, BashFrame
from .constants import colorInfo, settingDefaults, installercons
from .. import bass, balt, bosh, bolt, bush, env
from ..balt import Link, colors, Image, bell, Resources, set_event_hook, \
    Events, ColorPicker
from ..bosh import faces
from ..gui import ApplyButton, BOTTOM, Button, CancelButton, CENTER, \
    CheckBox, GridLayout, HLayout, Label, LayoutOptions, OkButton, RIGHT, \
    Stretch, TextArea, TextField, VLayout

class ColorDialog(balt.Dialog):
    """Color configuration dialog"""
    title = _(u'Color Configuration')

    _keys_to_tabs = {
        'mods': _(u'[Mods] '),
        'screens': _(u'[Saves, Screens] '),
        'installers': _(u'[Installers] '),
        'ini': _(u'[INI Edits] '),
        'tweak': _(u'[INI Edits] '),
        'default': _(u'[All] '),
    }

    def __init__(self):
        super(ColorDialog, self).__init__(parent=Link.Frame, resize=False)
        self.changes = dict()
        #--ComboBox
        def _display_text(k):
            return _(self._keys_to_tabs[k.split('.')[0]]) + colorInfo[k][0]
        self.text_key = dict((_display_text(x), x) for x in colors)
        colored = self.text_key.keys()
        colored.sort(key=unicode.lower)
        combo_text = colored[0]
        choiceKey = self.text_key[combo_text]
        self.comboBox = balt.ComboBox(self, value=combo_text, choices=colored)
        #--Color Picker
        self.picker = ColorPicker(self, colors[choiceKey])
        #--Description
        help_ = colorInfo[choiceKey][1]
        self.textCtrl = TextArea(self, text=help_, editable=False)
        #--Buttons
        self.default = Button(self, _(u'Default'),
                              onButClickEventful=self.OnDefault)
        self.defaultAll = Button(self, _(u'All Defaults'),
                                 onButClickEventful=self.OnDefaultAll)
        self.apply = ApplyButton(self, onButClickEventful=self.OnApply)
        self.applyAll = Button(self, _(u'Apply All'),
                               onButClickEventful=self.OnApplyAll)
        self.export_config = Button(self, _(u'Export...'),
                                    onButClickEventful=self.OnExport)
        self.importConfig = Button(self, _(u'Import...'),
                                   onButClickEventful=self.OnImport)
        self.ok = OkButton(self, onButClickEventful=self.OnOK,
                           default=True)
        #--Events
        set_event_hook(self.comboBox, Events.COMBOBOX_CHOICE, self.OnComboBox)
        set_event_hook(self.picker, Events.COLORPICKER_CHANGED,
                       self.OnColorPicker)
        #--Layout
        VLayout(border=5, default_fill=True, spacing=5, items=[
            HLayout(items=[
                (self.comboBox, LayoutOptions(fill=True, weight=1)),
                self.picker]),
            (self.textCtrl, LayoutOptions(weight=1)),
            GridLayout(h_spacing=5, v_spacing=5, default_fill=True,
                       stretch_cols=[3], items=[
                (self.defaultAll, self.applyAll, self.export_config),
                (self.default, self.apply, self.importConfig, None, self.ok)
            ])
        ]).apply_to(self)
        self.comboBox.SetFocus()
        self.SetIcons(Resources.bashBlue)
        self.UpdateUIButtons()

    def GetColorKey(self):
        """Return balt.colors dict key for current combobox selection."""
        return self.text_key[self.comboBox.GetValue()]

    @staticmethod
    def UpdateUIColors():
        """Update the Bash Frame with the new colors"""
        with balt.BusyCursor():
            for (className,title,panel) in tabInfo.itervalues():
                if panel is not None:
                    panel.RefreshUIColors()

    def UpdateUIButtons(self):
        # Apply All and Default All
        for key, val in self.changes.items():
            if val == colors[key]:
                del self.changes[key]
        anyChanged = bool(self.changes)
        allDefault = True
        for key in colors:
            if key in self.changes:
                color = self.changes[key]
            else:
                color = colors[key]
            default = bool(color == settingDefaults['bash.colors'][key])
            if not default:
                allDefault = False
                break
        # Apply and Default
        color_key = self.GetColorKey()
        changed = bool(color_key in self.changes)
        if changed:
            color = self.changes[color_key]
        else:
            color = colors[color_key]
        default = bool(color == settingDefaults['bash.colors'][color_key])
        # Update the Buttons, ComboBox, and ColorPicker
        self.apply.enabled = changed
        self.applyAll.enabled = anyChanged
        self.default.enabled = not default
        self.defaultAll.enabled = not allDefault
        self.picker.set_color(color)
        self.comboBox.SetFocusFromKbd()

    def _unbind_combobox(self):
        # TODO(inf) de-wx!, needed for wx3, check if needed in Phoenix
        self.comboBox.Unbind(wx.EVT_SIZE)

    def OnDefault(self,event):
        # TODO(nycz): un-event this ok
        event.Skip()
        color_key = self.GetColorKey()
        newColor = settingDefaults['bash.colors'][color_key]
        self.changes[color_key] = newColor
        self.UpdateUIButtons()

    def OnDefaultAll(self,event):
        event.Skip()
        for key in colors:
            default = settingDefaults['bash.colors'][key]
            if colors[key] != default:
                self.changes[key] = default
        self.UpdateUIButtons()

    def OnApply(self,event):
        event.Skip()
        color_key = self.GetColorKey()
        newColor = self.changes[color_key]
        #--Update settings and colors
        bass.settings['bash.colors'][color_key] = newColor
        bass.settings.setChanged('bash.colors')
        colors[color_key] = newColor
        self.UpdateUIButtons()
        self.UpdateUIColors()

    def OnApplyAll(self,event):
        event.Skip()
        for key,newColor in self.changes.iteritems():
            bass.settings['bash.colors'][key] = newColor
            colors[key] = newColor
        bass.settings.setChanged('bash.colors')
        self.UpdateUIButtons()
        self.UpdateUIColors()

    def OnOK(self, event):
        self._unbind_combobox()
        self.OnApplyAll(event)

    def OnExport(self,event):
        event.Skip()
        outDir = bass.dirs['patches']
        outDir.makedirs()
        #--File dialog
        outPath = balt.askSave(self,_(u'Export color configuration to:'), outDir, _(u'Colors.txt'), u'*.txt')
        if not outPath: return
        try:
            with outPath.open('w') as file:
                for key in colors:
                    if key in self.changes:
                        color = self.changes[key]
                    else:
                        color = colors[key]
                    file.write(key+u': '+color+u'\n')
        except Exception as e:
            balt.showError(self,_(u'An error occurred writing to ')+outPath.stail+u':\n\n%s'%e)

    def OnImport(self,event):
        event.Skip()
        inDir = bass.dirs['patches']
        inDir.makedirs()
        #--File dialog
        inPath = balt.askOpen(self,_(u'Import color configuration from:'), inDir, _(u'Colors.txt'), u'*.txt', mustExist=True)
        if not inPath: return
        try:
            with inPath.open('r') as file:
                for line in file:
                    # Format validation
                    if u':' not in line:
                        continue
                    split = line.split(u':')
                    if len(split) != 2:
                        continue
                    key = split[0]
                    # Verify color exists
                    if key not in colors:
                        continue
                    # Color format verification
                    color = eval(split[1])
                    if not isinstance(color, tuple) or len(color) not in (3,4):
                        continue
                    ok = True
                    for value in color:
                        if not isinstance(value,int):
                            ok = False
                            break
                        if value < 0x00 or value > 0xFF:
                            ok = False
                            break
                    if not ok:
                        continue
                    # Save it
                    if color == colors[key]: continue
                    self.changes[key] = color
        except Exception as e:
            balt.showError(Link.Frame, _(
                u'An error occurred reading from ') + inPath.stail +
                           u':\n\n%s' % e)
        self.UpdateUIButtons()

    def OnComboBox(self,event):
        event.Skip()
        self.UpdateUIButtons()
        color_key = self.GetColorKey()
        description = colorInfo[color_key][1]
        self.textCtrl.text_content = description

    def OnColorPicker(self,event):
        event.Skip()
        color_key = self.GetColorKey()
        newColor = self.picker.get_color()
        self.changes[color_key] = newColor
        self.UpdateUIButtons()

    def OnCloseWindow(self, event):
        self._unbind_combobox()
        super(ColorDialog, self).OnCloseWindow(event)

#------------------------------------------------------------------------------
class ImportFaceDialog(balt.Dialog):
    """Dialog for importing faces."""
    def __init__(self, parent, title, fileInfo, faces):
        #--Data
        self.fileInfo = fileInfo
        if faces and isinstance(faces.keys()[0], int):
            self.data = dict((u'%08X %s' % (key,face.pcName),face) for key,face in faces.items())
        else:
            self.data = faces
        self.list_items = sorted(self.data.keys(),key=string.lower)
        #--GUI
        super(ImportFaceDialog, self).__init__(parent, title=title)
        self.SetSizeHints(550,300)
        #--List Box
        self.listBox = balt.listBox(self, choices=self.list_items,
                                    onSelect=self.EvtListBox)
        self.listBox.SetSizeHints(175,150)
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
        importButton = Button(self, label=_(u'Import'),
                              on_click=self.DoImport, default=True)
        self.picture = balt.Picture(self,350,210,scaling=2)
        GridLayout(border=4, stretch_cols=[0, 1], stretch_rows=[0], items=[
            # Row 1
            ((self.listBox, LayoutOptions(row_span=2, fill=True)),
             (self.picture, LayoutOptions(col_span=2, fill=True))),
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

    def EvtListBox(self,event):
        """Responds to listbox selection."""
        itemDex = event.GetSelection()
        item = self.list_items[itemDex]
        face = self.data[item]
        self.nameText.label_text = face.pcName
        self.raceText.label_text = face.getRaceName()
        self.genderText.label_text = face.getGenderName()
        self.statsText.label_text = _(u'Health ') + unicode(face.health)
        itemImagePath = bass.dirs['mods'].join(u'Docs', u'Images', '%s.jpg' % item)
        # TODO(ut): any way to get the picture ? see mod_links.Mod_Face_Import
        bitmap = itemImagePath.exists() and Image(
            itemImagePath.s).GetBitmap() or None
        self.picture.SetBitmap(bitmap)
        self.listBox.SetSelection(itemDex)

    def DoImport(self):
        """Imports selected face into save file."""
        selections = self.listBox.GetSelections()
        if not selections:
            bell()
            return
        itemDex = selections[0]
        item = self.list_items[itemDex]
        #--Do import
        pc_flags = bosh.faces.PCFaces.pcf_flags() # make a copy of PCFaces flags
        pc_flags.hair = pc_flags.eye = True
        pc_flags.name = self.nameCheck.checked
        pc_flags.race = self.raceCheck.checked
        pc_flags.gender = self.genderCheck.checked
        pc_flags.stats = self.statsCheck.checked
        pc_flags.iclass = self.classCheck.checked
        #deprint(flags.getTrueAttrs())
        bass.settings['bash.faceImport.flags'] = int(pc_flags)
        bosh.faces.PCFaces.save_setFace(self.fileInfo,self.data[item],pc_flags)
        balt.showOk(self,_(u'Face imported.'),self.fileInfo.name.s)
        self.EndModalOK()

#------------------------------------------------------------------------------
class CreateNewProject(balt.Dialog):
    title = _(u'Create New Project')
    def __init__(self,parent=None):
        super(CreateNewProject, self).__init__(parent, resize=False)
        #--Build a list of existing directories
        #  The text control will use this to change background color when name collisions occur
        self.existingProjects = [x for x in bass.dirs['installers'].list() if bass.dirs['installers'].join(x).isdir()]

        #--Attributes
        self.textName = TextField(self, _(u'New Project Name-#####'),
                                  on_text_change=self.OnCheckProjectsColorTextCtrl)
        self.checkEsp = CheckBox(self, _(u'Blank.esp'),
                                 on_toggle=self.OnCheckBoxChange, checked=True)
        self.checkEspMasterless = CheckBox(self, _(u'Blank Masterless.esp'),
                                   on_toggle=self.OnCheckBoxChange, checked=False)
        self.checkWizard = CheckBox(self, _(u'Blank wizard.txt'),
                                    on_toggle=self.OnCheckBoxChange)
        self.checkWizardImages = CheckBox(self, _(u'Wizard Images Directory'))
        if not bEnableWizard:
            # pywin32 not installed
            self.checkWizard.enabled = False
            self.checkWizardImages.enabled = False
        self.checkDocs = CheckBox(self, _(u'Docs Directory'))
        # Panel Layout
        VLayout(border=5, spacing=5, items=[
            Label(self, _(u'What do you want to name the New Project?')),
            (self.textName, LayoutOptions(fill=True)),
            Label(self,_(u'What do you want to add to the New Project?')),
            self.checkEsp, self.checkEspMasterless, self.checkWizard,
            self.checkWizardImages, self.checkDocs,
            Stretch(),
            (HLayout(spacing=5, items=[
                OkButton(self, onButClickEventful=self.OnClose),
                CancelButton(self, onButClickEventful=self.OnCancel)]),
             LayoutOptions(h_align=CENTER))
        ]).apply_to(self)
        self.SetInitialSize()
        # Event Handlers
        set_event_hook(self.textName, Events.TEXT_CHANGED,
                       self.OnCheckProjectsColorTextCtrl)
        # Dialog Icon Handlers
        self.SetIcon(installercons.get_image('off.white.dir').GetIcon())
        self.OnCheckBoxChange()

    def OnCheckProjectsColorTextCtrl(self,event):
        projectName = bolt.GPath(self.textName.text_content)
        if projectName in self.existingProjects: #Fill this in. Compare this with the self.existingprojects list
            self.textName.background_color = '#FF0000'
            self.textName.tooltip = _(u'There is already a project with that name!')
        else:
            self.textName.background_color = '#FFFFFF'
            self.textName.tooltip = None
        event.Skip()

    def OnCheckBoxChange(self, is_checked=None):
        """ Change the Dialog Icon to represent what the project status will
        be when created. """
        if self.checkEsp.checked:
            if self.checkWizard.checked:
                self.SetIcon(
                    installercons.get_image('off.white.dir.wiz').GetIcon())
            else:
                self.SetIcon(
                    installercons.get_image('off.white.dir').GetIcon())
        else:
            self.SetIcon(installercons.get_image('off.grey.dir').GetIcon())

    @staticmethod
    def OnCancel(event): event.Skip()

    def OnClose(self, event):
        """ Create the New Project and add user specified extras. """
        projectName = bolt.GPath(self.textName.text_content.strip())
        projectDir = bass.dirs['installers'].join(projectName)

        if projectDir.exists():
            balt.showError(self, _(
                u'There is already a project with that name!') + u'\n' + _(
                u'Pick a different name for the project and try again.'))
            return
        event.Skip()

        # Create project in temp directory, so we can move it via
        # Shell commands (UAC workaround)
        tmpDir = bolt.Path.tempDir()
        tempProject = tmpDir.join(projectName)
        if self.checkEsp.checked:
            fileName = u'Blank, %s.esp' % bush.game.fsName
            bosh.modInfos.create_new_mod(fileName, directory=tempProject)
        if self.checkEspMasterless.checked:
            fileName = u'Blank, %s (masterless).esp' % bush.game.fsName
            bosh.modInfos.create_new_mod(fileName, directory=tempProject,
                                         masterless=True)
        if self.checkWizard.checked:
            # Create empty wizard.txt
            wizardPath = tempProject.join(u'wizard.txt')
            with wizardPath.open('w',encoding='utf-8') as out:
                out.write(u'; %s BAIN Wizard Installation Script\n' % projectName)
        if self.checkWizardImages.checked:
            # Create 'Wizard Images' directory
            tempProject.join(u'Wizard Images').makedirs()
        if self.checkDocs.checked:
            #Create the 'Docs' Directory
            tempProject.join(u'Docs').makedirs()
        # if self.checkScreenshot.IsChecked():
        #     #Copy the dummy default 'Screenshot' into the New Project
        #     extrasDir.join(u'Screenshot').copyTo(tempProject.join(u'Screenshot'))

        # Move into the target location
        try:
            env.shellMove(tempProject, projectDir, parent=self)
            # Move successful
            BashFrame.iPanel.ShowPanel(canCancel=False, scan_data_dir=True)
        except:
            pass
        finally:
            tmpDir.rmtree(tmpDir.s)
