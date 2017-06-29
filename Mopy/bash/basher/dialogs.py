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

import string
import wx
from . import bEnableWizard, tabInfo, BashFrame
from .constants import colorInfo, settingDefaults, installercons
from .. import bass, balt, bosh, bolt, bush, env
from ..balt import Button, Link, colors, RoTextCtrl, checkBox, StaticText, \
    Image, bell, TextCtrl, tooltip, OkButton, CancelButton, ApplyButton, \
    Resources, VLayout, HLayout, GridLayout, LayoutOptions, set_event_hook, \
    Events, Stretch
from ..bosh import faces

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
        self.picker = wx.ColourPickerCtrl(self)
        self.picker.SetColour(colors[choiceKey])
        #--Description
        help_ = colorInfo[choiceKey][1]
        self.textCtrl = RoTextCtrl(self, help_)
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
        self.apply.Enable(changed)
        self.applyAll.Enable(anyChanged)
        self.default.Enable(not default)
        self.defaultAll.Enable(not allDefault)
        self.picker.SetColour(color)
        self.comboBox.SetFocusFromKbd()

    def _unbind_combobox(self):
        # TODO(inf) de-wx!, needed for wx3, check if needed in Phoenix
        self.comboBox.Unbind(wx.EVT_SIZE)

    def OnDefault(self,event):
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
        help = colorInfo[color_key][1]
        self.textCtrl.SetValue(help)

    def OnColorPicker(self,event):
        event.Skip()
        color_key = self.GetColorKey()
        newColor = self.picker.GetColour()
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
        self.nameCheck = checkBox(self, _(u'Name'), checked=fi_flgs.name)
        self.raceCheck = checkBox(self, _(u'Race'), checked=fi_flgs.race)
        self.genderCheck = checkBox(self, _(u'Gender'), checked=fi_flgs.gender)
        self.statsCheck = checkBox(self, _(u'Stats'), checked=fi_flgs.stats)
        self.classCheck = checkBox(self, _(u'Class'), checked=fi_flgs.iclass)
        #--Name,Race,Gender Text
        self.nameText  = StaticText(self,u'-----------------------------')
        self.raceText  = StaticText(self,u'')
        self.genderText  = StaticText(self,u'')
        self.statsText  = StaticText(self,u'')
        self.classText  = StaticText(self,u'')
        #--Other
        importButton = Button(self, label=_(u'Import'),
                              onButClick=self.DoImport, default=True)
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
              LayoutOptions(h_align=balt.RIGHT, v_align=balt.BOTTOM)))
        ]).apply_to(self)

    def EvtListBox(self,event):
        """Responds to listbox selection."""
        itemDex = event.GetSelection()
        item = self.list_items[itemDex]
        face = self.data[item]
        self.nameText.SetLabel(face.pcName)
        self.raceText.SetLabel(face.getRaceName())
        self.genderText.SetLabel(face.getGenderName())
        self.statsText.SetLabel(_(u'Health ')+unicode(face.health))
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
        pc_flags.name = self.nameCheck.GetValue()
        pc_flags.race = self.raceCheck.GetValue()
        pc_flags.gender = self.genderCheck.GetValue()
        pc_flags.stats = self.statsCheck.GetValue()
        pc_flags.iclass = self.classCheck.GetValue()
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
        self.textName = TextCtrl(self, _(u'New Project Name-#####'),
                                 onText=self.OnCheckProjectsColorTextCtrl)
        self.checkEsp = checkBox(self, _(u'Blank.esp'),
                                 onCheck=self.OnCheckBoxChange, checked=True)
        self.checkEspMasterless = checkBox(self, _(u'Blank Masterless.esp'),
                                   onCheck=self.OnCheckBoxChange, checked=False)
        self.checkWizard = checkBox(self, _(u'Blank wizard.txt'),
                                    onCheck=self.OnCheckBoxChange)
        self.checkWizardImages = checkBox(self, _(u'Wizard Images Directory'))
        if not bEnableWizard:
            # pywin32 not installed
            self.checkWizard.Disable()
            self.checkWizardImages.Disable()
        self.checkDocs = checkBox(self,_(u'Docs Directory'))
        # Panel Layout
        VLayout(border=5, spacing=5, items=[
            StaticText(self, _(u'What do you want to name the New Project?')),
            (self.textName, LayoutOptions(fill=True)),
            StaticText(self,_(u'What do you want to add to the New Project?')),
            self.checkEsp, self.checkEspMasterless, self.checkWizard,
            self.checkWizardImages, self.checkDocs,
            Stretch(),
            (HLayout(spacing=5, items=[
                OkButton(self, onButClickEventful=self.OnClose),
                CancelButton(self, onButClickEventful=self.OnCancel)]),
             LayoutOptions(h_align=balt.CENTER))
        ]).apply_to(self)
        self.SetInitialSize()
        # Event Handlers
        set_event_hook(self.textName, Events.TEXT_CHANGED,
                       self.OnCheckProjectsColorTextCtrl)
        # Dialog Icon Handlers
        self.SetIcon(installercons.get_image('off.white.dir').GetIcon())
        self.OnCheckBoxChange()

    def OnCheckProjectsColorTextCtrl(self,event):
        projectName = bolt.GPath(self.textName.GetValue())
        if projectName in self.existingProjects: #Fill this in. Compare this with the self.existingprojects list
            self.textName.SetBackgroundColour('#FF0000')
            self.textName.SetToolTip(tooltip(_(u'There is already a project with that name!')))
        else:
            self.textName.SetBackgroundColour('#FFFFFF')
            self.textName.SetToolTip(None)
        self.textName.Refresh()
        event.Skip()

    def OnCheckBoxChange(self):
        """ Change the Dialog Icon to represent what the project status will
        be when created. """
        if self.checkEsp.IsChecked():
            if self.checkWizard.IsChecked():
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
        projectName = bolt.GPath(self.textName.GetValue().strip())
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
        if self.checkEsp.IsChecked():
            fileName = u'Blank, %s.esp' % bush.game.fsName
            bosh.modInfos.create_new_mod(fileName, directory=tempProject)
        if self.checkEspMasterless.IsChecked():
            fileName = u'Blank, %s (masterless).esp' % bush.game.fsName
            bosh.modInfos.create_new_mod(fileName, directory=tempProject,
                                         masterless=True)
        if self.checkWizard.IsChecked():
            # Create empty wizard.txt
            wizardPath = tempProject.join(u'wizard.txt')
            with wizardPath.open('w',encoding='utf-8') as out:
                out.write(u'; %s BAIN Wizard Installation Script\n' % projectName)
        if self.checkWizardImages.IsChecked():
            # Create 'Wizard Images' directory
            tempProject.join(u'Wizard Images').makedirs()
        if self.checkDocs.IsChecked():
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
