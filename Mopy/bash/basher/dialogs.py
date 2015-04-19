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
#  Wrye Bash copyright (C) 2005-2009 Wrye, 2010-2014 Wrye Bash Team
#  https://github.com/wrye-bash
#
# =============================================================================

import string
from types import IntType, LongType
import wx
from . import bEnableWizard, tabInfo, BashFrame
from .constants import colorInfo, settingDefaults, JPEG, PNG
from .. import balt, bosh, bolt, bush
from ..bass import Resources
from ..balt import button, hSizer, Link, colors, roTextCtrl, vSizer, spacer, \
    checkBox, staticText, Image, bell, textCtrl, tooltip, OkButton, \
    CancelButton

class ColorDialog(balt.Dialog):
    """Color configuration dialog"""
    title = _(u'Color Configuration')

    def __init__(self):
        super(ColorDialog, self).__init__(parent=Link.Frame, resize=False)
        self.changes = dict()
        #--ComboBox
        keys = [x for x in colors]
        keys.sort()
        choices = [colorInfo[x][0] for x in keys]
        choice = choices[0]
        self.text_key = dict()
        for key in keys:
            text = colorInfo[key][0]
            self.text_key[text] = key
        choiceKey = self.text_key[choice]
        self.comboBox = balt.comboBox(self, value=choice, choices=choices)
        #--Color Picker
        self.picker = wx.ColourPickerCtrl(self)
        self.picker.SetColour(colors[choiceKey])
        #--Description
        help = colorInfo[choiceKey][1]
        self.textCtrl = roTextCtrl(self, help)
        #--Buttons
        self.default = button(self,_(u'Default'),onClick=self.OnDefault)
        self.defaultAll = button(self,_(u'All Defaults'),onClick=self.OnDefaultAll)
        self.apply = button(self,id=wx.ID_APPLY,onClick=self.OnApply)
        self.applyAll = button(self,_(u'Apply All'),onClick=self.OnApplyAll)
        self.exportConfig = button(self,_(u'Export...'),onClick=self.OnExport)
        self.importConfig = button(self,_(u'Import...'),onClick=self.OnImport)
        self.ok = OkButton(self, onClick=self.OnApplyAll, default=True)
        #--Events
        self.comboBox.Bind(wx.EVT_COMBOBOX,self.OnComboBox)
        self.picker.Bind(wx.EVT_COLOURPICKER_CHANGED,self.OnColorPicker)
        #--Layout
        sizer = vSizer(
            (hSizer(
                (self.comboBox,1,wx.EXPAND|wx.RIGHT,5), self.picker,
                ),0,wx.EXPAND|wx.ALL,5),
            (self.textCtrl,1,wx.EXPAND|wx.ALL,5),
            (hSizer(
                (self.defaultAll,0,wx.RIGHT,5),
                (self.applyAll,0,wx.RIGHT,5), self.exportConfig,
                ),0,wx.EXPAND|wx.ALL,5),
            (hSizer(
                (self.default,0,wx.RIGHT,5),
                (self.apply,0,wx.RIGHT,5), self.importConfig, spacer, self.ok,
                ),0,wx.EXPAND|wx.ALL,5),
            )
        self.comboBox.SetFocus()
        self.SetSizer(sizer)
        self.SetIcons(Resources.bashBlue)
        self.UpdateUIButtons()

    def GetChoice(self):
        return self.text_key[self.comboBox.GetValue()]

    def UpdateUIColors(self):
        """Update the Bash Frame with the new colors"""
        nb = Link.Frame.notebook
        with balt.BusyCursor():
            for (className,title,panel) in tabInfo.itervalues():
                if panel is not None:
                    panel.RefreshUIColors()

    def UpdateUIButtons(self):
        # Apply All and Default All
        for key in self.changes.keys():
            if self.changes[key] == colors[key]:
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
        choice = self.GetChoice()
        changed = bool(choice in self.changes)
        if changed:
            color = self.changes[choice]
        else:
            color = colors[choice]
        default = bool(color == settingDefaults['bash.colors'][choice])
        # Update the Buttons, ComboBox, and ColorPicker
        self.apply.Enable(changed)
        self.applyAll.Enable(anyChanged)
        self.default.Enable(not default)
        self.defaultAll.Enable(not allDefault)
        self.picker.SetColour(color)
        self.comboBox.SetFocusFromKbd()

    def OnDefault(self,event):
        event.Skip()
        choice = self.GetChoice()
        newColor = settingDefaults['bash.colors'][choice]
        self.changes[choice] = newColor
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
        choice = self.GetChoice()
        newColor = self.changes[choice]
        #--Update settings and colors
        bosh.settings['bash.colors'][choice] = newColor
        bosh.settings.setChanged('bash.colors')
        colors[choice] = newColor
        self.UpdateUIButtons()
        self.UpdateUIColors()

    def OnApplyAll(self,event):
        event.Skip()
        for key,newColor in self.changes.iteritems():
            bosh.settings['bash.colors'][key] = newColor
            colors[key] = newColor
        bosh.settings.setChanged('bash.colors')
        self.UpdateUIButtons()
        self.UpdateUIColors()

    def OnExport(self,event):
        event.Skip()
        outDir = bosh.dirs['patches']
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
        except Exception,e:
            balt.showError(self,_(u'An error occurred writing to ')+outPath.stail+u':\n\n%s'%e)

    def OnImport(self,event):
        event.Skip()
        inDir = bosh.dirs['patches']
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
        except Exception, e:
            balt.showError(Link.Frame, _(
                u'An error occurred reading from ') + inPath.stail +
                           u':\n\n%s' % e)
        self.UpdateUIButtons()

    def OnComboBox(self,event):
        event.Skip()
        self.UpdateUIButtons()
        choice = self.GetChoice()
        help = colorInfo[choice][1]
        self.textCtrl.SetValue(help)

    def OnColorPicker(self,event):
        event.Skip()
        choice = self.GetChoice()
        newColor = self.picker.GetColour()
        self.changes[choice] = newColor
        self.UpdateUIButtons()

#------------------------------------------------------------------------------
class ImportFaceDialog(balt.Dialog):
    """Dialog for importing faces."""
    def __init__(self, parent, title, fileInfo, faces):
        #--Data
        self.fileInfo = fileInfo
        if faces and isinstance(faces.keys()[0],(IntType,LongType)):
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
        flags = bosh.PCFaces.flags(bosh.settings.get('bash.faceImport.flags', 0x4))
        self.nameCheck = checkBox(self, _(u'Name'), checked=flags.name)
        self.raceCheck = checkBox(self, _(u'Race'), checked=flags.race)
        self.genderCheck = checkBox(self, _(u'Gender'), checked=flags.gender)
        self.statsCheck = checkBox(self, _(u'Stats'), checked=flags.stats)
        self.classCheck = checkBox(self, _(u'Class'), checked=flags.iclass)
        #--Name,Race,Gender Text
        self.nameText  = staticText(self,u'-----------------------------')
        self.raceText  = staticText(self,u'')
        self.genderText  = staticText(self,u'')
        self.statsText  = staticText(self,u'')
        self.classText  = staticText(self,u'')
        #--Other
        importButton = button(self, label=_(u'Import'), onClick=self.DoImport,
                              default=True)
        self.picture = balt.Picture(self,350,210,scaling=2)
        #--Layout
        fgSizer = wx.FlexGridSizer(3,2,2,4)
        fgSizer.AddGrowableCol(1,1)
        fgSizer.AddMany([
            self.nameCheck,
            self.nameText,
            self.raceCheck,
            self.raceText,
            self.genderCheck,
            self.genderText,
            self.statsCheck,
            self.statsText,
            self.classCheck,
            self.classText,
            ])
        sizer = hSizer(
            (self.listBox,1,wx.EXPAND|wx.TOP,4),
            (vSizer(
                self.picture,
                (hSizer(
                    (fgSizer,1),
                    (vSizer(
                        (importButton,0,wx.ALIGN_RIGHT),
                        (CancelButton(self),0,wx.TOP,4),
                        )),
                    ),0,wx.EXPAND|wx.TOP,4),
                ),0,wx.EXPAND|wx.ALL,4),
            )
        #--Done
        if 'ImportFaceDialog' in balt.sizes:
            self.SetSizer(sizer)
            self.SetSize(balt.sizes['ImportFaceDialog'])
        else:
            self.SetSizerAndFit(sizer)

    def EvtListBox(self,event):
        """Responds to listbox selection."""
        itemDex = event.GetSelection()
        item = self.list_items[itemDex]
        face = self.data[item]
        self.nameText.SetLabel(face.pcName)
        self.raceText.SetLabel(face.getRaceName())
        self.genderText.SetLabel(face.getGenderName())
        self.statsText.SetLabel(_(u'Health ')+unicode(face.health))
        itemImagePath = bosh.dirs['mods'].join(u'Docs',u'Images','%s.jpg' % item)
        # TODO(ut): any way to get the picture ? see mod_links.Mod_Face_Import
        bitmap = (itemImagePath.exists() and
                  Image(itemImagePath.s, imageType=JPEG).GetBitmap()) or None
        self.picture.SetBitmap(bitmap)

    def DoImport(self,event):
        """Imports selected face into save file."""
        selections = self.listBox.GetSelections()
        if not selections:
            bell()
            return
        itemDex = selections[0]
        item = self.list_items[itemDex]
        #--Do import
        flags = bosh.PCFaces.flags()
        flags.hair = flags.eye = True
        flags.name = self.nameCheck.GetValue()
        flags.race = self.raceCheck.GetValue()
        flags.gender = self.genderCheck.GetValue()
        flags.stats = self.statsCheck.GetValue()
        flags.iclass = self.classCheck.GetValue()
        #deprint(flags.getTrueAttrs())
        bosh.settings['bash.faceImport.flags'] = int(flags)
        bosh.PCFaces.save_setFace(self.fileInfo,self.data[item],flags)
        balt.showOk(self,_(u'Face imported.'),self.fileInfo.name.s)
        self.EndModalOK()

#------------------------------------------------------------------------------
class CreateNewProject(balt.Dialog):
    title = _(u'Create New Project')
    def __init__(self,parent=None):
        super(CreateNewProject, self).__init__(parent, resize=False)
        #--Build a list of existing directories
        #  The text control will use this to change background color when name collisions occur
        self.existingProjects = [x for x in bosh.dirs['installers'].list() if bosh.dirs['installers'].join(x).isdir()]

        #--Attributes
        self.textName = textCtrl(self, _(u'New Project Name-#####'),
                                 onText=self.OnCheckProjectsColorTextCtrl)
        self.checkEsp = checkBox(self, _(u'Blank.esp'),
                                 onCheck=self.OnCheckBoxChange, checked=True)
        self.checkWizard = checkBox(self, _(u'Blank wizard.txt'), onCheck=self.OnCheckBoxChange)
        self.checkWizardImages = checkBox(self, _(u'Wizard Images Directory'))
        if not bEnableWizard:
            # pywin32 not installed
            self.checkWizard.Disable()
            self.checkWizardImages.Disable()
        self.checkDocs = checkBox(self,_(u'Docs Directory'))
        # self.checkScreenshot = checkBox(self,_(u'Preview Screenshot(No.ext)(re-enable for BAIT)'))
        # self.checkScreenshot.Disable() #Remove this when BAIT gets preview stuff done
        okButton = OkButton(self, onClick=self.OnClose)
        cancelButton = CancelButton(self, onClick=self.OnClose)
        # Panel Layout
        hsizer = wx.BoxSizer(wx.HORIZONTAL)
        hsizer.Add(okButton,0,wx.ALL|wx.ALIGN_CENTER,10)
        hsizer.Add(cancelButton,0,wx.ALL|wx.ALIGN_CENTER,10)
        vsizer = wx.BoxSizer(wx.VERTICAL)
        vsizer.Add(staticText(self,_(u'What do you want to name the New Project?'),style=wx.TE_RICH2),0,wx.ALL|wx.ALIGN_CENTER,10)
        vsizer.Add(self.textName,0,wx.ALL|wx.ALIGN_CENTER|wx.EXPAND,2)
        vsizer.Add(staticText(self,_(u'What do you want to add to the New Project?')),0,wx.ALL|wx.ALIGN_CENTER,10)
        vsizer.Add(self.checkEsp,0,wx.ALL|wx.ALIGN_TOP,5)
        vsizer.Add(self.checkWizard,0,wx.ALL|wx.ALIGN_TOP,5)
        vsizer.Add(self.checkWizardImages,0,wx.ALL|wx.ALIGN_TOP,5)
        vsizer.Add(self.checkDocs,0,wx.ALL|wx.ALIGN_TOP,5)
        # vsizer.Add(self.checkScreenshot,0,wx.ALL|wx.ALIGN_TOP,5)
        vsizer.Add(wx.StaticLine(self,wx.ID_ANY))
        vsizer.AddStretchSpacer()
        vsizer.Add(hsizer,0,wx.ALIGN_CENTER)
        vsizer.AddStretchSpacer()
        self.SetSizer(vsizer)
        self.SetInitialSize()
        # Event Handlers
        self.textName.Bind(wx.EVT_TEXT,self.OnCheckProjectsColorTextCtrl)
        # Dialog Icon Handlers
        self.SetIcon(wx.Icon(bosh.dirs['images'].join(u'diamond_white_off.png').s,PNG))
        self.OnCheckBoxChange(self)

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

    def OnCheckBoxChange(self, event):
        """ Change the Dialog Icon to represent what the project status will
        be when created. """
        if self.checkEsp.IsChecked():
            if self.checkWizard.IsChecked():
                self.SetIcon(wx.Icon(bosh.dirs['images'].join(u'diamond_white_off_wiz.png').s,PNG))
            else:
                self.SetIcon(wx.Icon(bosh.dirs['images'].join(u'diamond_white_off.png').s,PNG))
        else:
            self.SetIcon(wx.Icon(bosh.dirs['images'].join(u'diamond_grey_off.png').s,PNG))

    def OnClose(self,event):
        """ Create the New Project and add user specified extras. """
        if event.GetId() == wx.ID_CANCEL:
            event.Skip()
            return

        projectName = bolt.GPath(self.textName.GetValue())
        projectDir = bosh.dirs['installers'].join(projectName)

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
        extrasDir = bosh.dirs['templates'].join(bush.game.fsName)
        if self.checkEsp.IsChecked():
            # Copy blank esp into project
            fileName = u'Blank, %s.esp' % bush.game.fsName
            extrasDir.join(fileName).copyTo(tempProject.join(fileName))
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
            balt.shellMove(tempProject, projectDir, parent=self)
        except:
            pass
        finally:
            tmpDir.rmtree(tmpDir.s)

        # Move successful
        self.fullRefresh = False
        BashFrame.iPanel.refreshed = False
        BashFrame.iPanel.fullRefresh = self.fullRefresh
        BashFrame.iPanel.ShowPanel()
