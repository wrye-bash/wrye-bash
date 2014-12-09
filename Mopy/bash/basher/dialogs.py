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

import re
import string
from types import IntType, LongType
import wx
from .. import balt, bosh, bolt, bush
from ..balt import Dialog, Links, button, hSizer, ItemLink, Link, colors, \
    roTextCtrl, vSizer, spacer, checkBox, staticText, Image, spinCtrl, \
    hsbSizer, bell, textCtrl, tooltip
from . import Resources, bEnableWizard
from .constants import colorInfo, tabInfo, settingDefaults, JPEG, PNG

modList = None # TODO(ut): Balo - bin, also from basher
gInstallers = None

class _CheckList_SelectAll(ItemLink):
    """Menu item used in ListBoxes."""
    def __init__(self,select=True):
        super(_CheckList_SelectAll, self).__init__()
        self.select = select
        self.text = _(u'Select All') if select else _(u'Select None')

    def Execute(self,event):
        for i in xrange(self.window.GetCount()):
            self.window.Check(i,self.select)

class ListBoxes(Dialog):
    """A window with 1 or more lists."""
    # TODO(ut): attributes below must go - askContinue method ?
    ID_OK = wx.ID_OK
    ID_CANCEL = wx.ID_CANCEL

    def __init__(self,parent,title,message,lists,liststyle='check',style=0,changedlabels={},Cancel=True):
        """lists is in this format:
        if liststyle == 'check' or 'list'
        [title,tooltip,item1,item2,itemn],
        [title,tooltip,....],
        elif liststyle == 'tree'
        [title,tooltip,{item1:[subitem1,subitemn],item2:[subitem1,subitemn],itemn:[subitem1,subitemn]}],
        [title,tooltip,....],
        """
        super(ListBoxes, self).__init__(parent, title=title, style=style,
                                        resize=False)  # TODO(ut): resize = True and drop resize parameter
        self.itemMenu = Links()
        self.itemMenu.append(_CheckList_SelectAll())
        self.itemMenu.append(_CheckList_SelectAll(False))
        self.SetIcons(Resources.bashBlue)
        minWidth = self.GetTextExtent(title)[0]*1.2+64
        sizer = wx.FlexGridSizer(len(lists)+1,1)
        self.ids = {}
        labels = {wx.ID_CANCEL:_(u'Cancel'),wx.ID_OK:_(u'OK')}
        labels.update(changedlabels)
        self.SetSize(wx.Size(self.GetTextExtent(title)[0]*1.2+64,-1))
        for i,group in enumerate(lists):
            title = group[0]
            tip = group[1]
            try: items = [x.s for x in group[2:]]
            except: items = [x for x in group[2:]]
            if len(items) == 0: continue
            box = wx.StaticBox(self,wx.ID_ANY,title)
            subsizer = wx.StaticBoxSizer(box, wx.HORIZONTAL)
            if liststyle == 'check':
                checks = wx.CheckListBox(self,wx.ID_ANY,choices=items,style=wx.LB_SINGLE|wx.LB_HSCROLL)
                checks.Bind(wx.EVT_KEY_UP,self.OnKeyUp)
                checks.Bind(wx.EVT_CONTEXT_MENU,self.OnContext)
                for i in xrange(len(items)):
                    checks.Check(i,True)
            elif liststyle == 'list':
                checks = wx.ListBox(self,wx.ID_ANY,choices=items,style=wx.LB_SINGLE|wx.LB_HSCROLL)
            else:
                checks = wx.TreeCtrl(self,wx.ID_ANY,size=(150,200),style=wx.TR_DEFAULT_STYLE|wx.TR_FULL_ROW_HIGHLIGHT|wx.TR_HIDE_ROOT)
                root = checks.AddRoot(title)
                for item in group[2]:
                    child = checks.AppendItem(root,item.s)
                    for subitem in group[2][item]:
                        sub = checks.AppendItem(child,subitem.s)
            self.ids[title] = checks.GetId()
            checks.SetToolTip(balt.tooltip(tip))
            subsizer.Add(checks,1,wx.EXPAND|wx.ALL,2)
            sizer.Add(subsizer,0,wx.EXPAND|wx.ALL,5)
            sizer.AddGrowableRow(i)
        okButton = button(self,id=wx.ID_OK,label=labels[wx.ID_OK])
        okButton.SetDefault()
        buttonSizer = hSizer(balt.spacer,
                             (okButton,0,wx.ALIGN_RIGHT),
                             )
        for id,label in labels.iteritems():
            if id in (wx.ID_OK,wx.ID_CANCEL):
                continue
            but = button(self,id=id,label=label)
            but.Bind(wx.EVT_BUTTON,self.OnClick)
            buttonSizer.Add(but,0,wx.ALIGN_RIGHT|wx.LEFT,2)
        if Cancel:
            buttonSizer.Add(button(self,id=wx.ID_CANCEL,label=labels[wx.ID_CANCEL]),0,wx.ALIGN_RIGHT|wx.LEFT,2)
        sizer.Add(buttonSizer,1,wx.EXPAND|wx.BOTTOM|wx.LEFT|wx.RIGHT,5)
        sizer.AddGrowableCol(0)
        sizer.SetSizeHints(self)
        self.SetSizer(sizer)
        #make sure that minimum size is at least the size of title
        if self.GetSize()[0] < minWidth:
            self.SetSize(wx.Size(minWidth,-1))

    def OnKeyUp(self,event):
        """Char events"""
        ##Ctrl-A - check all
        obj = event.GetEventObject()
        if event.CmdDown() and event.GetKeyCode() == ord('A'):
            check = not event.ShiftDown()
            for i in xrange(len(obj.GetStrings())):
                    obj.Check(i,check)
        else:
            event.Skip()

    def OnContext(self,event):
        """Context Menu"""
        self.itemMenu.PopupMenu(event.GetEventObject(), Link.Frame,
                                event.GetEventObject().GetSelections())
        event.Skip()

    def OnClick(self,event):
        id = event.GetId()
        if id not in (wx.ID_OK,wx.ID_CANCEL):
            self.EndModal(id)
        else:
            event.Skip()

#------------------------------------------------------------------------------
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
        self.comboBox = balt.comboBox(self,wx.ID_ANY,choice,choices=choices,style=wx.CB_READONLY)
        #--Color Picker
        self.picker = wx.ColourPickerCtrl(self,wx.ID_ANY)
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
        self.ok = button(self,id=wx.ID_OK,onClick=self.OnApplyAll) # OK applies all changes
        self.ok.SetDefault()
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
        """Update the bashFrame with the new colors"""
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
        self.items = sorted(self.data.keys(),key=string.lower)
        #--GUI
        super(ImportFaceDialog, self).__init__(parent, tile=title)
        self.SetSizeHints(550,300)
        #--List Box
        self.list = wx.ListBox(self,wx.ID_OK,choices=self.items,style=wx.LB_SINGLE)
        self.list.SetSizeHints(175,150)
        wx.EVT_LISTBOX(self,wx.ID_OK,self.EvtListBox)
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
        importButton = button(self,_(u'Import'),onClick=self.DoImport)
        importButton.SetDefault()
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
            (self.list,1,wx.EXPAND|wx.TOP,4),
            (vSizer(
                self.picture,
                (hSizer(
                    (fgSizer,1),
                    (vSizer(
                        (importButton,0,wx.ALIGN_RIGHT),
                        (button(self,id=wx.ID_CANCEL),0,wx.TOP,4),
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
        item = self.items[itemDex]
        face = self.data[item]
        self.nameText.SetLabel(face.pcName)
        self.raceText.SetLabel(face.getRaceName())
        self.genderText.SetLabel(face.getGenderName())
        self.statsText.SetLabel(_(u'Health ')+unicode(face.health))
        itemImagePath = bosh.dirs['mods'].join(u'Docs',u'Images','%s.jpg' % item)
        bitmap = (itemImagePath.exists() and
                  Image(itemImagePath.s, imageType=JPEG).GetBitmap()) or None
        self.picture.SetBitmap(bitmap)

    def DoImport(self,event):
        """Imports selected face into save file."""
        selections = self.list.GetSelections()
        if not selections:
            bell()
            return
        itemDex = selections[0]
        item = self.items[itemDex]
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
class Mod_BaloGroups_Edit(balt.Dialog):
    """Dialog for editing Balo groups."""
    title = _(u"Balo Groups")

    def __init__(self,parent):
        #--Data
        self.parent = parent
        self.groups = [list(x) for x in bosh.modInfos.getBaloGroups(True)]
        self.removed = set()
        #--GUI
        super(Mod_BaloGroups_Edit, self).__init__(parent, caption=True)
        #--List
        self.gList = wx.ListBox(self,wx.ID_ANY,choices=self.GetItems(),style=wx.LB_SINGLE)
        self.gList.SetSizeHints(125,150)
        self.gList.Bind(wx.EVT_LISTBOX,self.DoSelect)
        #--Bounds
        self.gLowerBounds = spinCtrl(self,u'-10',size=(15,15),min=-10,max=0,onSpin=self.OnSpin)
        self.gUpperBounds = spinCtrl(self,u'10',size=(15,15),min=0,max=10, onSpin=self.OnSpin)
        self.gLowerBounds.SetSizeHints(35,-1)
        self.gUpperBounds.SetSizeHints(35,-1)
        #--Buttons
        self.gAdd = button(self,_(u'Add'),onClick=self.DoAdd)
        self.gRename = button(self,_(u'Rename'),onClick=self.DoRename)
        self.gRemove = button(self,_(u'Remove'),onClick=self.DoRemove)
        self.gMoveEarlier = button(self,_(u'Move Up'),onClick=self.DoMoveEarlier)
        self.gMoveLater = button(self,_(u'Move Down'),onClick=self.DoMoveLater)
        #--Layout
        topLeftCenter= wx.ALIGN_CENTER|wx.LEFT|wx.TOP
        sizer = hSizer(
            (self.gList,1,wx.EXPAND|wx.TOP,4),
            (vSizer(
                (self.gAdd,0,topLeftCenter,4),
                (self.gRename,0,topLeftCenter,4),
                (self.gRemove,0,topLeftCenter,4),
                (self.gMoveEarlier,0,topLeftCenter,4),
                (self.gMoveLater,0,topLeftCenter,4),
                (hsbSizer((self,wx.ID_ANY,_(u'Offsets')),
                    (self.gLowerBounds,1,wx.EXPAND|wx.LEFT|wx.TOP,4),
                    (self.gUpperBounds,1,wx.EXPAND|wx.TOP,4),
                    ),0,wx.LEFT|wx.TOP,4),
                    spacer,
                    (button(self,id=wx.ID_SAVE,onClick=self.DoSave),0,topLeftCenter,4),
                    (button(self,id=wx.ID_CANCEL,onClick=self.DoCancel),0,topLeftCenter|wx.BOTTOM,4),
                ),0,wx.EXPAND|wx.RIGHT,4),
            )
        #--Done
        self.SetSizeHints(200,300)
        className = self.__class__.__name__
        if className in balt.sizes:
            self.SetSizer(sizer)
            self.SetSize(balt.sizes[className])
        else:
            self.SetSizerAndFit(sizer)
        self.Refresh(0)

    #--Support
    def AskNewName(self,message,title):
        """Ask user for new/copy name."""
        newName = (balt.askText(self,message,title) or u'').strip()
        if not newName: return None
        maValid = re.match(u'([a-zA-Z][ _a-zA-Z]+)',newName,flags=re.U)
        if not maValid or maValid.group(1) != newName:
            balt.showWarning(self,
                _(u"Group name must be letters, spaces, underscores only!"),title)
            return None
        elif newName in self.GetItems():
            balt.showWarning(self,_(u"group %s already exists.") % newName,title)
            return None
        elif len(newName) >= 40:
            balt.showWarning(self,_(u"Group names must be less than forty characters."),title)
            return None
        else:
            return newName

    def GetItems(self):
        """Return a list of item strings."""
        return [x[5] for x in self.groups]

    def GetItemLabel(self,index):
        info = self.groups[index]
        lower,upper,group = info[1],info[2],info[5]
        if lower == upper:
            return group
        else:
            return u'%s  %d : %d' % (group,lower,upper)

    def Refresh(self,index):
        """Refresh items in list."""
        labels = [self.GetItemLabel(x) for x in range(len(self.groups))]
        self.gList.Set(labels)
        self.gList.SetSelection(index)
        self.RefreshButtons()

    def RefreshBounds(self,index):
        """Refresh bounds info."""
        if index < 0 or index >= len(self.groups):
            lower,upper = 0,0
        else:
            lower,upper,usedStart,usedStop = self.groups[index][1:5]
        self.gLowerBounds.SetRange(-10,usedStart)
        self.gUpperBounds.SetRange(usedStop-1,10)
        self.gLowerBounds.SetValue(lower)
        self.gUpperBounds.SetValue(upper)

    def RefreshButtons(self,index=None):
        """Updates buttons."""
        if index is None:
            index = (self.gList.GetSelections() or (0,))[0]
        self.RefreshBounds(index)
        usedStart,usedStop = self.groups[index][3:5]
        mutable = index <= len(self.groups) - 3
        self.gAdd.Enable(mutable)
        self.gRename.Enable(mutable)
        self.gRemove.Enable(mutable and usedStart == usedStop)
        self.gMoveEarlier.Enable(mutable and index > 0)
        self.gMoveLater.Enable(mutable and index <= len(self.groups) - 4)
        self.gLowerBounds.Enable(index != len(self.groups) - 2)
        self.gUpperBounds.Enable(index != len(self.groups) - 2)

    #--Event Handling
    def DoAdd(self,event):
        """Adds a new item."""
        title = _(u"Add Balo Group")
        index = (self.gList.GetSelections() or (0,))[0]
        if index < 0 or index >= len(self.groups) - 2: return bell()
        #--Ask for and then check new name
        oldName = self.groups[index][0]
        message = _(u"Name of new group (spaces and letters only):")
        newName = self.AskNewName(message,title)
        if newName:
            self.groups.insert(index+1,[u'',0,0,0,0,newName])
            self.Refresh(index+1)

    def DoMoveEarlier(self,event):
        """Moves selected group up (earlier) in order.)"""
        index = (self.gList.GetSelections() or (0,))[0]
        if index < 1 or index >= (len(self.groups)-2): return bell()
        swapped = [self.groups[index],self.groups[index-1]]
        self.groups[index-1:index+1] = swapped
        self.Refresh(index-1)

    def DoMoveLater(self,event):
        """Moves selected group down (later) in order.)"""
        index = (self.gList.GetSelections() or (0,))[0]
        if index < 0 or index >= (len(self.groups) - 3): return bell()
        swapped = [self.groups[index+1],self.groups[index]]
        self.groups[index:index+2] = swapped
        self.Refresh(index+1)

    def DoRename(self,event):
        """Renames selected item."""
        title = _(u"Rename Balo Group")
        index = (self.gList.GetSelections() or (0,))[0]
        if index < 0 or index >= len(self.groups): return bell()
        #--Ask for and then check new name
        oldName = self.groups[index][5]
        message = _(u"Rename %s to (spaces, letters and underscores only):") % oldName
        newName = self.AskNewName(message,title)
        if newName:
            self.groups[index][5] = newName
            self.gList.SetString(index,self.GetItemLabel(index))

    def DoRemove(self,event):
        """Removes selected item."""
        index = (self.gList.GetSelections() or (0,))[0]
        if index < 0 or index >= len(self.groups): return bell()
        name = self.groups[index][0]
        if name: self.removed.add(name)
        del self.groups[index]
        self.gList.Delete(index)
        self.Refresh(index)

    def DoSelect(self,event):
        """Handle select event."""
        self.Refresh(event.GetSelection())
        self.gList.SetFocus()

    def OnSpin(self,event):
        """Show label editing dialog."""
        index = (self.gList.GetSelections() or (0,))[0]
        self.groups[index][1] = self.gLowerBounds.GetValue()
        self.groups[index][2] = self.gUpperBounds.GetValue()
        self.gList.SetString(index,self.GetItemLabel(index))
        event.Skip()

    #--Save/Cancel
    def DoSave(self,event):
        """Handle save button."""
        balt.sizes[self.__class__.__name__] = self.GetSizeTuple()
        bosh.settings['bash.balo.full'] = True
        bosh.modInfos.setBaloGroups(self.groups,self.removed)
        bosh.modInfos.updateAutoGroups()
        bosh.modInfos.refresh()
        modList.RefreshUI()
        self.EndModalOK()

    def DoCancel(self,event):
        """Handle save button."""
        balt.sizes[self.__class__.__name__] = self.GetSizeTuple()
        self.EndModal(wx.ID_CANCEL)

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
        okButton = wx.Button(self,wx.ID_OK)
        cancelButton = wx.Button(self,wx.ID_CANCEL)
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
        okButton.Bind(wx.EVT_BUTTON,self.OnClose)
        cancelButton.Bind(wx.EVT_BUTTON,self.OnClose)
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
            balt.showError(self,_(u'There is already a project with that name!')
                                + u'\n' +
                                _(u'Pick a different name for the project and try again.'))
            return
        event.Skip()

        # Create project in temp directory, so we can move it via
        # Shell commands (UAC workaround)
        tempDir = bolt.Path.tempDir(u'WryeBash_')
        tempProject = tempDir.join(projectName)
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
            balt.shellMove(tempProject,projectDir,self,False,False,False)
        except:
            pass
        finally:
            tempDir.rmtree(tempDir.s)

        # Move successful
        self.fullRefresh = False
        gInstallers.refreshed = False
        gInstallers.fullRefresh = self.fullRefresh
        gInstallers.OnShow()

#------------------------------------------------------------------------------
