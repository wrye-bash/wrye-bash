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
#  Wrye Bash copyright (C) 2005, 2006, 2007, 2008, 2009 Wrye
#
# =============================================================================

#===================================================
# Specific parser for Wrye Bash
#===================================================
import ScriptParser         # generic parser class
from ScriptParser import error
import wx
import wx.wizard as wiz     # wxPython wizard class
import bosh, balt, bolt, basher, bush
import struct, string
import win32api
import StringIO
import traceback
#---------------------------------------------------

#Translateable strings
EXTRA_ARGS =   _(u"Extra arguments to '%s'.")
MISSING_ARGS = _(u"Missing arguments to '%s'.")
UNEXPECTED =   _(u"Unexpected '%s'.")

class WizardReturn(object):
    __slots__ = ('Canceled', 'SelectEspms', 'RenameEspms', 'SelectSubPackages', 'Install',
                 'IniEdits', 'PageSize', 'Pos',
                 )
    # Canceled: Set to true if the user canceled the wizard, or if an error occurred
    # SelectEspms: List of ESP's/ESM's to 'select' for install
    # RenameEspms: Dictionary of renames for ESP/M's.  In the format of:
    #   'original name':'new name'
    # SelectSubPackages: List of Subpackages to 'select' for install
    # IniEdits: Dictionary of INI edits to apply/create.  In the format of:
    #   'ini file': {
    #      'section': {
    #         'key': value
    #         }
    #      }
    #    For BatchScript type ini's, the 'section' will either be 'set' or 'setGS'
    # Install: Set to True if after configuring this package, it should also be installed.
    # PageSize: Tuple/wxSize of the saved size of the Wizard
    # Pos: Tuple/wxPoint of the saved position of the Wizard

    def __init__(self):
        self.Canceled = False
        self.SelectEspms = []
        self.RenameEspms = {}
        self.SelectSubPackages = []
        self.IniEdits = {}
        self.Install = False
        self.PageSize = wx.DefaultSize
        self.Pos = wx.DefaultPosition

# InstallerWizard ----------------------------------
#  Class used by Wrye Bash, creates a wx Wizard that
#  dynamically creates pages based on a script
#---------------------------------------------------
class InstallerWizard(wiz.Wizard):
    def __init__(self, link, subs, pageSize, pos):
        wiz.Wizard.__init__(self, link.gTank, wx.ID_ANY, _(u'Installer Wizard'),
                            pos=pos,
                            style=wx.DEFAULT_DIALOG_STYLE|wx.RESIZE_BORDER|wx.MAXIMIZE_BOX)

        #'dummy' page tricks the wizard into always showing the "Next" button,
        #'next' will be set by the parser
        self.dummy = wiz.PyWizardPage(self)
        self.next = None

        #True prevents actually moving to the 'next' page.  We use this after the "Next"
        #button is pressed, while the parser is running to return the _actual_ next page
        #'finishing' is to allow the "Next" button to be used when it's name is changed to
        #'Finish' on the last page of the wizard
        self.blockChange = True
        self.finishing = False

        #parser that will spit out the pages
        path = link.selected[0]
        installer = link.data[path]
        bArchive = link.isSingleArchive()
        if bArchive:
            with balt.Progress(_(u'Extracting wizard files...'),u'\n'+u' '*60,abort=True) as progress:
                # Extract the wizard, and any images as well
                installer.unpackToTemp(path, [installer.hasWizard,
                    u'*.bmp',            # BMP's
                    u'*.jpg', u'*.jpeg', # JPEG's
                    u'*.png',            # PNG's
                    u'*.gif',            # GIF's
                    u'*.pcx',            # PCX's
                    u'*.pnm',            # PNM's
                    u'*.tif', u'*.tiff', # TIFF's
                    u'*.tga',            # TGA's
                    u'*.iff',            # IFF's
                    u'*.xpm',            # XPM's
                    u'*.ico',            # ICO's
                    u'*.cur',            # CUR's
                    u'*.ani',            # ANI's
                    ], bosh.SubProgress(progress,0,0.9), recurse=True)
            self.wizard_file = installer.tempDir.join(installer.hasWizard)
        else:
            self.wizard_file = link.data.dir.join(path.s, installer.hasWizard)
        self.parser = WryeParser(self, installer, subs, bArchive, path, link.bAuto)

        #Intercept the changing event so we can implement 'blockChange'
        self.Bind(wiz.EVT_WIZARD_PAGE_CHANGING, self.OnChange)
        self.ret = WizardReturn()
        self.ret.PageSize = pageSize

        # So we can save window size
        self.Bind(wx.EVT_SIZE, self.OnSize)
        self.Bind(wx.EVT_CLOSE, self.OnClose)
        self.Bind(wiz.EVT_WIZARD_CANCEL, self.OnClose)
        self.Bind(wiz.EVT_WIZARD_FINISHED, self.OnClose)

        #Set the minimum size for pages, and setup OnSize to resize the
        #First page to the saved size
        self.SetPageSize((600,500))
        self.firstPage = True

    def OnClose(self, event):
        if not self.IsMaximized():
            # Only save the current size if the page isn't maximized
            self.ret.PageSize = self.GetSize()
            self.ret.Pos = self.GetPosition()
        event.Skip()

    def OnSize(self, event):
        if self.firstPage:
            # On the first page, resize it to the saved size
            self.firstPage = False
            self.SetSize(self.ret.PageSize)
        else:
            # Otherwise, regular resize, save the size if we're not
            # maximized
            if not self.IsMaximized():
                self.ret.PageSize = self.GetSize()
                self.Pos = self.GetPosition()
            event.Skip()

    def OnChange(self, event):
        if event.GetDirection():
            if not self.finishing:
                # Next, continue script execution
                if self.blockChange:
                    #Tell the current page that next was pressed,
                    #So the parser can continue parsing,
                    #Then show the page that the parser returns,
                    #rather than the dummy page
                    event.GetPage().OnNext()
                    event.Veto()
                    self.next = self.parser.Continue()
                    self.blockChange = False
                    self.ShowPage(self.next)
                else:
                    self.blockChange = True
        else:
            # Previous, pop back to the last state,
            # and resume execution
            self.finishing = False
            event.Veto()
            self.next = self.parser.Back()
            self.blockChange = False
            self.ShowPage(self.next)

    def Run(self):
        page = self.parser.Begin(self.wizard_file)
        if page:
            self.ret.Canceled = not self.RunWizard(page)
        # Clean up temp files
        if self.parser.bArchive:
            try:
                self.parser.installer.tempDir.rmtree(safety='Temp')
            except:
                pass
        return self.ret
#End of Installer Wizard

# PageInstaller ----------------------------------------------
#  base class for all the parser wizard pages, just to handle
#  a couple simple things here
#-------------------------------------------------------------
class PageInstaller(wiz.PyWizardPage):
    def __init__(self, parent):
        wiz.PyWizardPage.__init__(self, parent)
        self.parent = parent
        parent.FindWindowById(wx.ID_FORWARD).Enable(True)

    def GetNext(self): return self.parent.dummy
    def GetPrev(self):
        if self.parent.parser.choiceIdex > 0:
            return self.parent.dummy
        return None
    def OnNext(self):
        #This is what needs to be implemented by sub-classes,
        #this is where flow control objects etc should be
        #created
        pass
# End PageInstaller ------------------------------------------

# PageError --------------------------------------------------
#  Page that shows an error message, hase only a "Cancel"
#  button enabled, and cancels any changes made
#-------------------------------------------------------------
class PageError(PageInstaller):
    def __init__(self, parent, title, errorMsg):
        PageInstaller.__init__(self, parent)

        #Disable the "Finish"/"Next" button
        self.parent.FindWindowById(wx.ID_FORWARD).Enable(False)

        #Layout stuff
        sizerMain = wx.FlexGridSizer(2, 1, 5, 5)
        textError = wx.TextCtrl(self, wx.ID_ANY, errorMsg, style=wx.TE_READONLY|wx.TE_MULTILINE)
        sizerMain.Add(wx.StaticText(self, wx.ID_ANY, title))
        sizerMain.Add(textError, 0, wx.ALL|wx.CENTER|wx.EXPAND)
        sizerMain.AddGrowableCol(0)
        sizerMain.AddGrowableRow(1)
        self.SetSizer(sizerMain)
        self.Layout()

    def GetNext(self): return None
    def GetPrev(self): return None
# End PageError ----------------------------------------------

# PageSelect -------------------------------------------------
#  A Page that shows a message up top, with a selection box on
#  the left (multi- or single- selection), with an optional
#  associated image and description for each option, shown when
#  that item is selected
#-------------------------------------------------------------
class PageSelect(PageInstaller):
    def __init__(self, parent, bMany, title, desc, listItems, listDescs, listImages, defaultMap):
        PageInstaller.__init__(self, parent)
        self.items = listItems
        self.images = listImages
        self.descs = listDescs
        self.bMany = bMany
        self.bmp = wx.EmptyBitmap(1, 1)
        self.index = None

        sizerMain = wx.FlexGridSizer(5, 1, 5, 0)

        sizerTitle = wx.StaticBoxSizer(wx.StaticBox(self, wx.ID_ANY, u''))
        self.TitleDesc = wx.StaticText(self, wx.ID_ANY, desc)
        self.TitleDesc.Wrap(parent.GetPageSize()[0]-10)
        sizerTitle.Add(self.TitleDesc, 1, wx.ALIGN_CENTER|wx.ALL)
        sizerMain.Add(sizerTitle, 0, wx.EXPAND)
        sizerMain.Add(wx.StaticText(self, wx.ID_ANY, _(u'Options:')))

        sizerBoxes = wx.GridSizer(1, 2, 5, 5)
        self.textItem = wx.TextCtrl(self, wx.ID_ANY, u'', style=wx.TE_READONLY|wx.TE_MULTILINE)
        self.bmpItem = balt.Picture(self,0,0,background=None)
        if parent.parser.choiceIdex < len(parent.parser.choices):
            oldChoices = parent.parser.choices[parent.parser.choiceIdex]
            defaultMap = [choice in oldChoices for choice in listItems]
        if bMany:
            self.listOptions = wx.CheckListBox(self, wx.ID_ANY, choices=listItems, style=wx.LB_HSCROLL)
            for index, default in enumerate(defaultMap):
                self.listOptions.Check(index, default)
        else:
            self.listOptions = wx.ListBox(self, wx.ID_ANY, choices=listItems, style=wx.LB_HSCROLL)
            self.parent.FindWindowById(wx.ID_FORWARD).Enable(False)
            for index, default in enumerate(defaultMap):
                if default:
                    self.listOptions.Select(index)
                    self.Selection(index)
                    break
        sizerBoxes.Add(self.listOptions, 1, wx.ALL|wx.EXPAND)
        sizerBoxes.Add(self.bmpItem, 1, wx.ALL|wx.EXPAND)
        sizerMain.Add(sizerBoxes, wx.ID_ANY, wx.EXPAND)

        sizerMain.Add(wx.StaticText(self, wx.ID_ANY, _(u'Description:')))
        sizerMain.Add(self.textItem, wx.ID_ANY, wx.EXPAND|wx.ALL)

        self.SetSizer(sizerMain)
        sizerMain.AddGrowableRow(2)
        sizerMain.AddGrowableRow(4)
        sizerMain.AddGrowableCol(0)
        self.Layout()

        self.listOptions.Bind(wx.EVT_LISTBOX, self.OnSelect)
        self.bmpItem.Bind(wx.EVT_LEFT_DCLICK, self.OnDoubleClick)
        self.bmpItem.Bind(wx.EVT_MIDDLE_UP, self.OnDoubleClick)

    def OnSelect(self, event):
        index = event.GetSelection()
        self.Selection(index)

    def OnDoubleClick(self, event):
        try:
            file = self.images[self.index]
            if file.exists() and not file.isdir():
                file.start()
        except:
            pass


    def Selection(self, index):
        self.parent.FindWindowById(wx.ID_FORWARD).Enable(True)
        self.index = index
        self.textItem.SetValue(self.descs[index])
        # Don't want the bitmap to resize until we call self.Layout()
        self.bmpItem.Freeze()
        file = self.images[index]
        if file.exists() and not file.isdir():
            image = wx.Bitmap(file.s)
            self.bmpItem.SetBitmap(image)
            self.bmpItem.SetCursor(wx.StockCursor(wx.CURSOR_MAGNIFIER))
        else:
            self.bmpItem.SetBitmap(None)
            self.bmpItem.SetCursor(wx.StockCursor(wx.CURSOR_ARROW))
        self.bmpItem.Thaw()
        self.Layout()

    def OnNext(self):
        temp = []
        if self.bMany:
            index = -1
            for item in self.items:
                index += 1
                if self.listOptions.IsChecked(index):
                    temp.append(item)
        else:
            for i in self.listOptions.GetSelections():
                temp.append(self.items[i])
        if self.parent.parser.choiceIdex < len(self.parent.parser.choices):
            oldChoices = self.parent.parser.choices[self.parent.parser.choiceIdex]
            if temp == oldChoices:
                pass
            else:
                self.parent.parser.choices = self.parent.parser.choices[0:self.parent.parser.choiceIdex]
                self.parent.parser.choices.append(temp)
        else:
            self.parent.parser.choices.append(temp)
        self.parent.parser.PushFlow('Select', False, ['SelectOne', 'SelectMany', 'Case', 'Default', 'EndSelect'], values=temp, hitCase=False)
# End PageSelect -----------------------------------------

def generateTweakLines(wizardEdits, target):
    lines = []
    lines.append(_(u'; Generated by Wrye Bash %s for \'%s\' via wizard') % (basher.settings['bash.version'], target.s))
    for realSection in wizardEdits:
        if realSection == u']set[':
            modFormat = wizardEdits[realSection][0]+u' %(setting)s to %(value)s%(comment)s'
            delFormat = u';-'+wizardEdits[realSection][0]+u' %(setting)s to DELETED'
        elif realSection == u']setgs[':
            modFormat = wizardEdits[realSection][0]+u' %(setting)s %(value)s%(comment)s'
            delFormat = u';-'+wizardEdits[realSection][0]+u' %(setting)s DELETED'
        elif not realSection:
            continue
        else:
            lines.append(u'')
            lines.append(u'[%s]' % wizardEdits[realSection][0])
            modFormat = u'%(setting)s=%(value)s%(comment)s'
            delFormat = u';-%(setting)s'
        for realSetting in wizardEdits[realSection][1]:
            setting,value,comment,deleted = wizardEdits[realSection][1][realSetting]
            if deleted: format = delFormat
            else: format = modFormat
            lines.append(format % (dict(setting=setting,
                                        value=value,
                                        comment=comment,)))
    return lines


# PageFinish ---------------------------------------------
#  Page displayed at the end of a wizard, showing which
#  sub-packages and which esps and espms will be
#  selected.  Also displays some notes for the user
#---------------------------------------------------------
class PageFinish(PageInstaller):
    def __init__(self, parent, subsList, espmsList, espmRenames, bAuto, notes, iniedits):
        PageInstaller.__init__(self, parent)

        subs = subsList.keys()
        subs.sort(lambda l,r: cmp(l, r))
        subs = [x.replace(u'&',u'&&') for x in subs]
        espms = espmsList.keys()
        espms.sort(lambda l,r: cmp(l, r))

        #--make the list that will be displayed
        espmShow = []
        for x in espms:
            if x in espmRenames:
                espmShow.append(x + u' -> ' + espmRenames[x])
            else:
                espmShow.append(x)
        espmShow = [x.replace(u'&',u'&&') for x in espmShow]

        sizerMain = wx.FlexGridSizer(5, 1, 5, 0)

        parent.parser.choiceIdex += 1

        #--Heading
        sizerTitle = wx.StaticBoxSizer(wx.StaticBox(self, wx.ID_ANY, u''))
        textTitle = wx.StaticText(self, wx.ID_ANY, _(u"The installer script has finished, and will apply the following settings:"))
        textTitle.Wrap(parent.GetPageSize()[0]-10)
        sizerTitle.Add(textTitle, 0, wx.ALIGN_CENTER|wx.ALL)
        sizerMain.Add(sizerTitle, 0, wx.EXPAND)

        #--Subpackages and Espms
        sizerLists = wx.FlexGridSizer(2, 2, 5, 5)
        sizerLists.Add(wx.StaticText(self, wx.ID_ANY, _(u'Sub-Packages')))
        sizerLists.Add(wx.StaticText(self, wx.ID_ANY, _(u'Esp/ms')))
        self.listSubs = wx.CheckListBox(self, wx.ID_ANY, choices=subs)
        self.listSubs.Bind(wx.EVT_CHECKLISTBOX, self.OnSelectSubs)
        for index,key in enumerate(subs):
            key = key.replace(u'&&',u'&')
            if subsList[key]:
                self.listSubs.Check(index, True)
                self.parent.ret.SelectSubPackages.append(key)
        self.listEspms = wx.CheckListBox(self, wx.ID_ANY, choices=espmShow)
        self.listEspms.Bind(wx.EVT_CHECKLISTBOX, self.OnSelectEspms)
        for index,key in enumerate(espms):
            if espmsList[key]:
                self.listEspms.Check(index, True)
                self.parent.ret.SelectEspms.append(key)
        self.parent.ret.RenameEspms = espmRenames
        sizerLists.Add(self.listSubs, 0, wx.ALL|wx.EXPAND)
        sizerLists.Add(self.listEspms, 0, wx.ALL|wx.EXPAND)
        sizerLists.AddGrowableRow(1)
        sizerLists.AddGrowableCol(0)
        sizerLists.AddGrowableCol(1)
        sizerMain.Add(sizerLists, 1, wx.EXPAND)

        #--Ini tweaks
        sizerInis = wx.FlexGridSizer(2, 2, 5, 5)
        sizerInis.Add(wx.StaticText(self, wx.ID_ANY, _(u'Ini Tweaks:')))
        sizerInis.Add(wx.StaticText(self, wx.ID_ANY, u''))
        self.listInis = wx.ListBox(self, wx.ID_ANY, style=wx.LB_SINGLE, choices=[x.s for x in iniedits.keys()])
        self.listInis.Bind(wx.EVT_LISTBOX, self.OnSelectIni)
        self.listTweaks = wx.ListBox(self, wx.ID_ANY, style=wx.LB_SINGLE)
        sizerInis.Add(self.listInis, 0, wx.ALL|wx.EXPAND)
        sizerInis.Add(self.listTweaks, 0, wx.ALL|wx.EXPAND)
        sizerInis.AddGrowableRow(1)
        sizerInis.AddGrowableCol(0)
        sizerInis.AddGrowableCol(1)
        sizerMain.Add(sizerInis, 1, wx.EXPAND)
        self.parent.ret.IniEdits = iniedits

        #--Notes
        sizerNotes = wx.FlexGridSizer(2, 1, 5, 0)
        sizerNotes.Add(wx.StaticText(self, wx.ID_ANY, _(u'Notes:')))
        sizerNotes.Add(wx.TextCtrl(self, wx.ID_ANY, u''.join(notes), style=wx.TE_READONLY|wx.TE_MULTILINE), 1, wx.EXPAND)
        sizerNotes.AddGrowableCol(0)
        sizerNotes.AddGrowableRow(1)
        sizerMain.Add(sizerNotes, 2, wx.TOP|wx.EXPAND)

        sizerChecks = wx.FlexGridSizer(2, 2, 5, 0)
        # Apply the selections
        self.checkApply = wx.CheckBox(self, wx.ID_ANY, _(u'Apply these selections'))
        self.checkApply.SetValue(bAuto)
        self.checkApply.Bind(wx.EVT_CHECKBOX, self.OnCheckApply)
        sizerChecks.AddStretchSpacer()
        sizerChecks.Add(self.checkApply)
        # Also install/anneal the package
        self.checkInstall = wx.CheckBox(self, wx.ID_ANY, _(u'Install this package'))
        self.checkInstall.SetValue(basher.settings['bash.installers.autoWizard'])
        self.checkInstall.Bind(wx.EVT_CHECKBOX, self.OnCheckInstall)
        self.parent.ret.Install = basher.settings['bash.installers.autoWizard']
        sizerChecks.AddStretchSpacer()
        sizerChecks.Add(self.checkInstall)
        sizerChecks.AddGrowableRow(0)
        sizerChecks.AddGrowableRow(1)
        sizerChecks.AddGrowableCol(0)
        sizerMain.Add(sizerChecks, 3, wx.EXPAND|wx.TOP)

        self.parent.FindWindowById(wx.ID_FORWARD).Enable(bAuto)
        self.parent.finishing = True

        sizerMain.AddGrowableCol(0)
        sizerMain.AddGrowableRow(1)
        sizerMain.AddGrowableRow(2)
        sizerMain.AddGrowableRow(3)
        sizerMain.SetSizeHints(self)
        self.SetSizer(sizerMain)
        self.Layout()

    def OnCheckApply(self, event):
        self.parent.FindWindowById(wx.ID_FORWARD).Enable(self.checkApply.IsChecked())

    def OnCheckInstall(self, event):
        self.parent.ret.Install = self.checkInstall.IsChecked()

    def GetNext(self): return None

    # Undo selecting/deselection of items for UI consistency
    def OnSelectSubs(self, event):
        index = event.GetSelection()
        self.listSubs.Check(index, not self.listSubs.IsChecked(index))
    def OnSelectEspms(self, event):
        index = event.GetSelection()
        self.listEspms.Check(index, not self.listEspms.IsChecked(index))

    def OnSelectIni(self, event):
        index = event.GetSelection()
        path = bolt.GPath(self.listInis.GetString(index))
        lines = generateTweakLines(self.parent.ret.IniEdits[path],path)
        self.listTweaks.Set(lines)
# End PageFinish -------------------------------------


# PageVersions ---------------------------------------
#  Page for displaying what versions an installer
#  requires/recommends and what you have installed
#  for Game, *SE, *GE, and Wrye Bash
#-----------------------------------------------------
class PageVersions(PageInstaller):
    def __init__(self, parent, bGameOk, gameHave, gameNeed, bSEOk, seHave,
                 seNeed, bGEOk, geHave, geNeed, bWBOk, wbHave, wbNeed):
        PageInstaller.__init__(self, parent)

        bmp = [wx.Bitmap(bosh.dirs['images'].join(u'x.png').s),
               wx.Bitmap(bosh.dirs['images'].join(u'check.png').s)
               ]

        sizerMain = wx.FlexGridSizer(5, 1, 0, 0)

        self.textWarning = wx.StaticText(self, wx.ID_ANY, _(u'WARNING: The following version requirements are not met for using this installer.'))
        self.textWarning.Wrap(parent.GetPageSize()[0]-20)
        sizerMain.Add(self.textWarning, 0, wx.ALL|wx.ALIGN_CENTER, 5)

        sizerVersionsTop = wx.StaticBoxSizer(wx.StaticBox(self, wx.ID_ANY, _(u'Version Requirements')))
        sizerVersions = wx.FlexGridSizer(5, 4, 5, 5)
        sizerVersionsTop.Add(sizerVersions, 1, wx.EXPAND, 0)

        sizerVersions.AddStretchSpacer()
        sizerVersions.Add(wx.StaticText(self, wx.ID_ANY, _(u'Need')))
        sizerVersions.Add(wx.StaticText(self, wx.ID_ANY, _(u'Have')))
        sizerVersions.AddStretchSpacer()

        # Game
        if bush.game.patchURL != u'':
            linkGame = wx.HyperlinkCtrl(self, wx.ID_ANY, bush.game.name, bush.game.patchURL)
            linkGame.SetVisitedColour(linkGame.GetNormalColour())
        else:
            linkGame = wx.StaticText(self, wx.ID_ANY, bush.game.name)
        linkGame.SetToolTip(wx.ToolTip(bush.game.patchTip))
        sizerVersions.Add(linkGame)
        sizerVersions.Add(wx.StaticText(self, wx.ID_ANY, gameNeed))
        sizerVersions.Add(wx.StaticText(self, wx.ID_ANY, gameHave))
        sizerVersions.Add(wx.StaticBitmap(self, wx.ID_ANY, bmp[bGameOk]))

        # Script Extender
        if bush.game.se.shortName != u'':
            linkSE = wx.HyperlinkCtrl(self, wx.ID_ANY, bush.game.se.longName, bush.game.se.url)
            linkSE.SetVisitedColour(linkSE.GetNormalColour())
            linkSE.SetToolTip(wx.ToolTip(bush.game.se.urlTip))
            sizerVersions.Add(linkSE)
            sizerVersions.Add(wx.StaticText(self, wx.ID_ANY, seNeed))
            sizerVersions.Add(wx.StaticText(self, wx.ID_ANY, seHave))
            sizerVersions.Add(wx.StaticBitmap(self, wx.ID_ANY, bmp[bSEOk]))

        # Graphics extender
        if bush.game.ge.shortName != u'':
            linkGE = wx.HyperlinkCtrl(self, wx.ID_ANY, bush.game.ge.longName, bush.game.ge.url)
            linkGE.SetVisitedColour(linkGE.GetNormalColour())
            linkGE.SetToolTip(wx.ToolTip(bush.game.ge.urlTip))
            sizerVersions.Add(linkGE)
            sizerVersions.Add(wx.StaticText(self, wx.ID_ANY, geNeed))
            sizerVersions.Add(wx.StaticText(self, wx.ID_ANY, geHave))
            sizerVersions.Add(wx.StaticBitmap(self, wx.ID_ANY, bmp[bGEOk]))

        linkWB = wx.HyperlinkCtrl(self, wx.ID_ANY, u'Wrye Bash', u'http://oblivion.nexusmods.com/mods/22368')
        linkWB.SetVisitedColour(linkWB.GetNormalColour())
        linkWB.SetToolTip(wx.ToolTip(u'http://oblivion.nexusmods.com/'))
        sizerVersions.Add(linkWB)
        sizerVersions.Add(wx.StaticText(self, wx.ID_ANY, wbNeed))
        sizerVersions.Add(wx.StaticText(self, wx.ID_ANY, wbHave))
        sizerVersions.Add(wx.StaticBitmap(self, wx.ID_ANY, bmp[bWBOk]))

        sizerVersions.AddGrowableCol(0)
        sizerVersions.AddGrowableCol(1)
        sizerVersions.AddGrowableCol(2)
        sizerVersions.AddGrowableCol(3)
        sizerMain.Add(sizerVersionsTop, 2, wx.ALL|wx.EXPAND, 5)

        sizerMain.AddStretchSpacer()

        sizerCheck = wx.FlexGridSizer(1, 2, 5, 5)
        self.checkOk = wx.CheckBox(self, wx.ID_ANY, _(u'Install anyway.'))
        self.checkOk.Bind(wx.EVT_CHECKBOX, self.OnCheck)
        self.parent.FindWindowById(wx.ID_FORWARD).Enable(False)
        sizerCheck.AddStretchSpacer()
        sizerCheck.Add(self.checkOk)
        sizerCheck.AddGrowableRow(0)
        sizerCheck.AddGrowableCol(0)
        sizerMain.Add(sizerCheck, 3, wx.EXPAND)

        self.SetSizer(sizerMain)
        sizerMain.AddGrowableRow(0)
        sizerMain.AddGrowableRow(2)
        sizerMain.AddGrowableCol(0)
        self.Layout()

    def OnCheck(self, event):
        self.parent.FindWindowById(wx.ID_FORWARD).Enable(self.checkOk.IsChecked())
# END PageVersions -----------------------------------------------

# WryeParser -----------------------------------------------------
#  a derived class of Parser, for handling BAIN install
#  wizards
#-----------------------------------------------------------------
class WryeParser(ScriptParser.Parser):
    codeboxRemaps = {
        'Link': {
            # These are links that have different names than their text
            u'SelectOne':u'SelectOne1',
            u'SelectMany':u'SelectMany1',
            u'=':u'Assignment',
            u'+=':u'CompountAssignmentetc',
            u'-=':u'CompountAssignmentetc',
            u'*=':u'CompountAssignmentetc',
            u'/=':u'CompountAssignmentetc',
            u'^=':u'CompountAssignmentetc',
            u'+':u'Addition',
            u'-':u'Subtraction',
            u'*':u'Multiplication',
            u'/':u'Division',
            u'^':u'Exponentiation',
            u'and':u'Andampand',
            u'&':u'Andampand',
            u'or':u'Oror',
            u'|':u'Oror',
            u'not':u'Notnot',
            u'!':u'Notnot',
            u'in':u'Inin',
            u'in:':u'CaseInsensitiveInin',
            u'==':u'Equal',
            u'==:':u'CaseinsensitiveEqual',
            u'!=':u'NotEqual',
            u'!=:':u'CaseinsensitiveNotEqual',
            u'>=':u'GreaterThanorEqualgt',
            u'>=:':u'CaseInsensitiveGreaterThanorEqualgt',
            u'>':u'GreaterThangt',
            u'>:':u'CaseInsensitiveGreaterThangt',
            u'<=':u'LessThanorEquallt',
            u'<=:':u'CaseInsensitiveLessThanorEquallt',
            u'<':u'LessThanlt',
            u'<:':u'CaseInsensitiveLessThanlt',
            u'.':u'DotOperator',
            u'SubPackages':u'ForContinueBreakEndFor',
            },
        'Text': {
            # These are symbols that need to be replaced to be xhtml compliant
            u'&':u'&amp;',
            u'<':u'&lt;',
            u'<:':u'&lt;:',
            u'<=':u'&lt;=',
            u'<=:':u'&lt;=:',
            u'>':u'&gt;',
            u'>:':u'&gt;:',
            u'>=':u'&gt;=',
            u'>=:':u'&gt;=:',
            },
        'Color': {
            # These are items that we want colored differently
            u'in':u'blue',
            u'in:':u'blue',
            u'and':u'blue',
            u'or':u'blue',
            u'not':u'blue',
            },
        }
    @staticmethod
    def codebox(lines,pre=True,br=True):
        self = WryeParser(None,None,None,None,None,None,True)
        def colorize(text,color=u'black',link=True):
            href = text
            text = WryeParser.codeboxRemaps['Text'].get(text,text)
            if color != u'black' or link:
                color = WryeParser.codeboxRemaps['Color'].get(text,color)
                text = u'<span style="color:%s;">%s</span>' % (color,text)
            if link:
                href = WryeParser.codeboxRemaps['Link'].get(href,href)
                text = u'<a href="#%s">%s</a>' % (href,text)
            return text

        self.cLine = 0
        outLines = []
        lastBlank = 0
        while self.cLine < len(lines):
            line = lines[self.cLine]
            self.cLine += 1
            self.tokens = []
            self.TokenizeLine(line)
            tokens = self.tokens
            line = line.strip(u'\r\n')

            lastEnd = 0
            dotCount = 0
            outLine = u''
            for i in tokens:
                start,stop = i.pos
                if start is not None and stop is not None:
                    # Not an inserted token from the parser
                    if i.type == ScriptParser.STRING:
                        start -= 1
                        stop  += 1
                    # Padding
                    padding = line[lastEnd:start]
                    outLine += padding
                    lastEnd = stop
                    # The token
                    text = line[start:stop]
                    # Check for ellipses
                    if i.text == u'.':
                        dotCount += 1
                        if dotCount == 3:
                            dotCount = 0
                            outLine += u'...'
                        continue
                    else:
                        while dotCount > 0:
                            outLine += colorize(u'.')
                            dotCount -= 1
                    if i.type == ScriptParser.KEYWORD:
                        outLine += colorize(text,u'blue')
                    elif i.type == ScriptParser.FUNCTION:
                        outLine += colorize(text,u'purple')
                    elif i.type in (ScriptParser.INTEGER, ScriptParser.DECIMAL):
                        outLine += colorize(text,u'cyan',False)
                    elif i.type == ScriptParser.STRING:
                        outLine += colorize(text,u'brown',False)
                    elif i.type == ScriptParser.OPERATOR:
                        outLine += colorize(i.text)
                    elif i.type == ScriptParser.CONSTANT:
                        outLine += colorize(text,u'cyan')
                    elif i.type == ScriptParser.NAME:
                        outLine += u'<i>%s</i>' % text
                    else:
                        outLine += text
            if self.runon:
                outLine += u' \\'
            if lastEnd < len(line):
                comments = line[lastEnd:]
                if u';' in comments:
                    outLine += colorize(comments,u'green',False)
            if outLine == u'':
                if len(outLines) != 0:
                    lastBlank = len(outLines)
                else:
                    continue
            else:
                lastBlank = 0
            if pre:
                outLine = u'<span class="code-n" style="display: inline;">%s</span>\n' % outLine
            else:
                if br:
                    outLine = u'<span class="code-n">%s</span><br />\n' % outLine
                else:
                    outLine = u'<span class="code-n">%s</span>' % outLine
            outLines.append(outLine)
        if lastBlank:
            outLines = outLines[:lastBlank]
        return outLines

    def __init__(self, parent, installer, subs, bArchive, path, bAuto, codebox=False):
        ScriptParser.Parser.__init__(self)

        if not codebox:
            self.parent = parent
            self.installer = installer
            self.bArchive = bArchive
            self.path = path
            self.bAuto = bAuto
            self.page = None

            self.choices = []
            self.choiceIdex = -1
            self.sublist = {}
            self.espmlist = {}
            for i in installer.espmMap.keys():
                for j in installer.espmMap[i]:
                    if j not in self.espmlist:
                        self.espmlist[j] = False
                if i == u'': continue
                self.sublist[i] = False

        #--Constants
        self.SetConstant(u'SubPackages',u'SubPackages')
        #--Operators
        #Assignment
        self.SetOperator(u'=' , self.Ass, ScriptParser.OP.ASS, ScriptParser.RIGHT)
        self.SetOperator(u'+=', self.AssAdd, ScriptParser.OP.ASS, ScriptParser.RIGHT)
        self.SetOperator(u'-=', self.AssMin, ScriptParser.OP.ASS, ScriptParser.RIGHT)
        self.SetOperator(u'*=', self.AssMul, ScriptParser.OP.ASS, ScriptParser.RIGHT)
        self.SetOperator(u'/=', self.AssDiv, ScriptParser.OP.ASS, ScriptParser.RIGHT)
        #self.SetOperator(u'%=', self.AssMod, ScriptParser.OP.ASS, ScriptParser.RIGHT)
        self.SetOperator(u'^=', self.AssExp, ScriptParser.OP.ASS, ScriptParser.RIGHT)
        #Comparison
        self.SetOperator(u'==', self.opE, ScriptParser.OP.CO2)
        self.SetOperator(u'!=', self.opNE, ScriptParser.OP.CO2)
        self.SetOperator(u'>=', self.opGE, ScriptParser.OP.CO1)
        self.SetOperator(u'>' , self.opG, ScriptParser.OP.CO1)
        self.SetOperator(u'<=', self.opLE, ScriptParser.OP.CO1)
        self.SetOperator(u'<' , self.opL, ScriptParser.OP.CO1)
        self.SetOperator(u'==:', self.opEc, ScriptParser.OP.CO2, passTokens=False)  # Case insensitive ==
        self.SetOperator(u'!=:', self.opNEc, ScriptParser.OP.CO2, passTokens=False) # Case insensitive !=
        self.SetOperator(u'>=:', self.opGEc, ScriptParser.OP.CO1, passTokens=False) # Case insensitive >=
        self.SetOperator(u'>:', self.opGc, ScriptParser.OP.CO1, passTokens=False)   # Case insensitive >
        self.SetOperator(u'<=:', self.opLEc, ScriptParser.OP.CO1, passTokens=False) # Case insensitive <=
        self.SetOperator(u'<:', self.opLc, ScriptParser.OP.CO1, passTokens=False)   # Case insensitive <
        #Membership operators
        self.SetOperator(u'in', self.opIn, ScriptParser.OP.MEM, passTokens=False)
        self.SetOperator(u'in:', self.opInCase, ScriptParser.OP.MEM, passTokens=False) # Case insensitive in
        #Boolean
        self.SetOperator(u'&' , self.opAnd, ScriptParser.OP.AND)
        self.SetOperator(u'and', self.opAnd, ScriptParser.OP.AND)
        self.SetOperator(u'|', self.opOr, ScriptParser.OP.OR)
        self.SetOperator(u'or', self.opOr, ScriptParser.OP.OR)
        self.SetOperator(u'!', self.opNot, ScriptParser.OP.NOT, ScriptParser.RIGHT)
        self.SetOperator(u'not', self.opNot, ScriptParser.OP.NOT, ScriptParser.RIGHT)
        #Post-fix increment/decrement
        self.SetOperator(u'++', self.opInc, ScriptParser.OP.UNA)
        self.SetOperator(u'--', self.opDec, ScriptParser.OP.UNA)
        #Math
        self.SetOperator(u'+', self.opAdd, ScriptParser.OP.ADD)
        self.SetOperator(u'-', self.opMin, ScriptParser.OP.ADD)
        self.SetOperator(u'*', self.opMul, ScriptParser.OP.MUL)
        self.SetOperator(u'/', self.opDiv, ScriptParser.OP.MUL)
        #self.SetOperator(u'%', self.opMod, ScriptParser.OP.MUL)
        self.SetOperator(u'^', self.opExp, ScriptParser.OP.EXP, ScriptParser.RIGHT)

        #--Functions
        self.SetFunction(u'CompareObVersion', self.fnCompareGameVersion, 1)      # Retained for compatibility
        self.SetFunction(u'CompareGameVersion', self.fnCompareGameVersion, 1)
        self.SetFunction(u'CompareOBSEVersion', self.fnCompareSEVersion, 1)      # Retained for compatibility
        self.SetFunction(u'CompareSEVersion', self.fnCompareSEVersion, 1)
        self.SetFunction(u'CompareOBGEVersion', self.fnCompareGEVersion, 1)      # Retained for compatibility
        self.SetFunction(u'CompareGEVersion', self.fnCompareGEVersion, 1)
        self.SetFunction(u'CompareWBVersion', self.fnCompareWBVersion, 1)
        self.SetFunction(u'DataFileExists', self.fnDataFileExists, 1, ScriptParser.KEY.NO_MAX)
        self.SetFunction(u'GetEspmStatus', self.fnGetEspmStatus, 1)
        self.SetFunction(u'EditINI', self.fnEditINI, 4, 5)
        self.SetFunction(u'DisableINILine',self.fnDisableINILine, 3)
        self.SetFunction(u'Exec', self.fnExec, 1)
        self.SetFunction(u'EndExec', self.fnEndExec, 1)
        self.SetFunction(u'str', self.fnStr, 1)
        self.SetFunction(u'int', self.fnInt, 1)
        self.SetFunction(u'float', self.fnFloat, 1)
        #--String functions
        self.SetFunction(u'len', self.fnLen, 1, dotFunction=True)
        self.SetFunction(u'endswith', self.fnEndsWith, 2, ScriptParser.KEY.NO_MAX, dotFunction=True)
        self.SetFunction(u'startswith', self.fnStartsWith, 2, ScriptParser.KEY.NO_MAX, dotFunction=True)
        self.SetFunction(u'lower', self.fnLower, 1, dotFunction=True)
        self.SetFunction(u'find', self.fnFind, 2, 4, dotFunction=True)
        self.SetFunction(u'rfind', self.fnRFind, 2, 4, dotFunction=True)
        #--String pathname functions
        self.SetFunction(u'GetFilename', self.fnGetFilename, 1)
        self.SetFunction(u'GetFolder', self.fnGetFolder, 1)
        #--Keywords
        self.SetKeyword(u'SelectSubPackage', self.kwdSelectSubPackage, 1)
        self.SetKeyword(u'DeSelectSubPackage', self.kwdDeSelectSubPackage, 1)
        self.SetKeyword(u'SelectEspm', self.kwdSelectEspm, 1)
        self.SetKeyword(u'DeSelectEspm', self.kwdDeSelectEspm, 1)
        self.SetKeyword(u'SelectAll', self.kwdSelectAll)
        self.SetKeyword(u'DeSelectAll', self.kwdDeSelectAll)
        self.SetKeyword(u'SelectAllEspms', self.kwdSelectAllEspms)
        self.SetKeyword(u'DeSelectAllEspms', self.kwdDeSelectAllEspms)
        self.SetKeyword(u'RenameEspm', self.kwdRenameEspm, 2)
        self.SetKeyword(u'ResetEspmName', self.kwdResetEspmName, 1)
        self.SetKeyword(u'ResetAllEspmNames', self.kwdResetAllEspmNames)
        self.SetKeyword(u'Note', self.kwdNote, 1)
        self.SetKeyword(u'If', self.kwdIf, 1 )
        self.SetKeyword(u'Elif', self.kwdElif, 1)
        self.SetKeyword(u'Else', self.kwdElse)
        self.SetKeyword(u'EndIf', self.kwdEndIf)
        self.SetKeyword(u'While', self.kwdWhile, 1)
        self.SetKeyword(u'Continue', self.kwdContinue)
        self.SetKeyword(u'EndWhile', self.kwdEndWhile)
        self.SetKeyword(u'For', self.kwdFor, 3, ScriptParser.KEY.NO_MAX, passTokens=True, splitCommas=False)
        self.SetKeyword(u'from', self.kwdDummy)
        self.SetKeyword(u'to', self.kwdDummy)
        self.SetKeyword(u'by', self.kwdDummy)
        self.SetKeyword(u'EndFor', self.kwdEndFor)
        self.SetKeyword(u'SelectOne', self.kwdSelectOne, 7, ScriptParser.KEY.NO_MAX)
        self.SetKeyword(u'SelectMany', self.kwdSelectMany, 4, ScriptParser.KEY.NO_MAX)
        self.SetKeyword(u'Case', self.kwdCase, 1)
        self.SetKeyword(u'Default', self.kwdDefault)
        self.SetKeyword(u'Break', self.kwdBreak)
        self.SetKeyword(u'EndSelect', self.kwdEndSelect)
        self.SetKeyword(u'Return', self.kwdReturn)
        self.SetKeyword(u'Cancel', self.kwdCancel, 0, 1)
        self.SetKeyword(u'RequireVersions', self.kwdRequireVersions, 1, 4)


    def Begin(self, file):
        self.variables.clear()
        self.Flow = []
        self.notes = []
        self.espmrenames = {}
        self.iniedits = {}
        self.cLine = 0
        self.reversing = 0
        self.ExecCount = 0

        if file.exists() and file.isfile():
            try:
                with file.open(encoding='utf-8-sig') as script:
                    # Ensure \n line endings for the script parser
                    self.lines = [x.replace(u'\r\n',u'\n') for x in script.readlines()]
                return self.Continue()
            except UnicodeError:
                balt.showWarning(self.parent,_(u'Could not read the wizard file.  Please ensure it is encoded in UTF-8 format.'))
                return
        balt.showWarning(self.parent, _(u'Could not open wizard file'))
        return None

    def Continue(self):
        self.page = None
        while self.cLine < len(self.lines):
            newline = self.lines[self.cLine]
            try:
                self.RunLine(newline)
            except ScriptParser.ParserError, e:
                return PageError(self.parent, _(u'Installer Wizard'),
                                 _(u'An error occurred in the wizard script')
                                 +u':\n '+
                                 _(u'Line')
                                 +u':\t%s\n'+newline.strip(u'\n')+u' '+
                                 _(u'Error')
                                 +u':\t%s' % e)
            except Exception:
                o = StringIO.StringIO()
                o.write(_(u'An unhandled error occurred while parsing the wizard')
                        +u' :\n '+
                        _(u'Line')
                        +u'(%s):\t%s\n\n' % (self.cLine, newline.strip(u'\n')))
                traceback.print_exc(file=o)
                msg = o.getvalue()
                o.close()
                return PageError(self.parent, _(u'Installer Wizard'), msg)
            if self.page:
                return self.page
        self.cLine += 1
        self.cLineStart = self.cLine
        return PageFinish(self.parent, self.sublist, self.espmlist, self.espmrenames, self.bAuto, self.notes, self.iniedits)

    def Back(self):
        if self.choiceIdex == 0:
            return

        # Rebegin
        self.variables.clear()
        self.Flow = []
        self.notes = []
        self.espmrenames = {}
        self.iniedits = {}

        i = 0
        while self.ExecCount > 0 and i < len(self.lines):
            line = self.lines[i]
            i += 1
            if line.startswith(u'EndExec('):
                numLines = int(line[8:-1])
                del self.lines[i-numLines:i]
                i -= numLines
                self.ExecCount -= 1

        for i in self.sublist:
            self.sublist[i] = False
        for i in self.espmlist:
            self.espmlist[i] = False

        self.cLine = 0
        self.reversing = self.choiceIdex-1
        self.choiceIdex = -1
        return self.Continue()

    def EspmIsInPackage(self, espm, package):
        package = package.lower()
        espm = espm.lower()
        for i in self.installer.espmMap:
            if package == i.lower():
                for j in self.installer.espmMap[i]:
                    if espm == j.lower():
                        return True
        return False
    def EspmList(self, package):
        pack = self.GetPackage(package)
        if pack in self.installer.espmMap:
            return self.installer.espmMap[pack]
        return []
    def PackageList(self, espm):
        ret = []
        for i in self.sublist:
            if self.EspmIsInPackage(espm, i):
                ret.append(i)
        return ret
    def EspmHasActivePackage(self, espm):
        for i in self.sublist:
            if self.EspmIsInPackage(espm, i):
                if self.sublist[i]:
                    return True
        return False
    def GetPackage(self, package):
        package = package.lower()
        for i in self.sublist:
            if package == i.lower():
                return i
        return None
    def GetEspm(self, espm):
        espm = espm.lower()
        for i in self.espmlist:
            if espm == i.lower():
                return i
        return None

    # Assignment operators
    def Ass(self, l, r):
        if l.type not in [ScriptParser.VARIABLE,ScriptParser.NAME]:
            error(_(u'Cannot assign a value to %s, type is %s.') % (l.text, ScriptParser.Types[l.type]))
        self.variables[l.text] = r.data
        return r.data
    def AssAdd(self, l, r): return self.Ass(l, l+r)
    def AssMin(self, l, r): return self.Ass(l, l-r)
    def AssMul(self, l, r): return self.Ass(l, l*r)
    def AssDiv(self, l, r): return self.Ass(l, l/r)
    def AssMod(self, l, r): return self.Ass(l, l%r)
    def AssExp(self, l, r): return self.Ass(l, l**r)
    # Comparison operators
    def opE(self, l, r): return l == r
    def opEc(self, l, r):
        try:
            return l.lower() == r.lower()
        except:
            return l == r
    def opNE(self, l, r): return l != r
    def opNEc(self, l, r):
        try:
            return l.lower() != r.lower()
        except:
            return l != r
    def opGE(self, l, r): return l >= r
    def opGEc(self, l, r):
        try:
            return l.lower() >= r.lower()
        except:
            return l >= r
    def opG(self, l, r): return l > r
    def opGc(self, l, r):
        try:
            return l.lower() > r.lower()
        except:
            return l > r
    def opLE(self, l, r): return l <= r
    def opLEc(self, l, r):
        try:
            return l.lower() <= r.lower()
        except:
            return l <= r
    def opL(self, l, r): return l < r
    def opLc(self, l, r):
        try:
            return l.lower() < r.lower()
        except:
            return l < r
    # Membership tests
    def opIn(self, l, r): return l in r
    def opInCase(self, l, r):
        try:
            l.lower() in r.lower()
        except:
            return l in r
    # Boolean operators
    def opAnd(self, l, r): return l and r
    def opOr(self, l, r): return l or r
    def opNot(self, l): return not l
    # Postfix inc/dec
    def opInc(self, l):
        if l.type not in [ScriptParser.VARIABLE,ScriptParser.NAME]:
            error(_(u'Cannot increment %s, type is %s.') % (l.text, ScriptParser.Types[l.type]))
        self.variables[l.text] = l.data+1
        return l.data
    def opDec(self, l):
        if l.type not in [ScriptParser.VARIABLE,ScriptParser.NAME]:
            error(_(u'Cannot decrement %s, type is %s.') % (l.text, ScriptParser.Types[l.type]))
        self.variables[l.text] = l.data-1
        return l.data
    # Math operators
    def opAdd(self, l, r): return l + r
    def opMin(self, l, r): return l - r
    def opMul(self, l, r): return l * r
    def opDiv(self, l, r): return l / r
    def opMod(self, l, r): return l % r
    def opExp(self, l, r): return l ** r

    # Functions...
    def fnCompareGameVersion(self, obWant):
        ret = self._TestVersion(self._TestVersion_Want(obWant), bosh.dirs['app'].join(bush.game.exe))
        return ret[0]
    def fnCompareSEVersion(self, seWant):
        if bush.game.se.shortName != u'':
            if bosh.inisettings['SteamInstall']:
                se = bush.game.se.steamExe   # User may not have obse_loader.exe, since it's only required for the CS
            else:
                se = bush.game.se.exe
            ret = self._TestVersion(self._TestVersion_Want(seWant), bosh.dirs['app'].join(se))
            return ret[0]
        else:
            # No script extender available for this game
            return 1
    def fnCompareGEVersion(self, geWant):
        if bush.game.ge.shortName != u'':
            ret = self._TestVersion_OBGE(self._TestVersion_Want(geWant))
            return ret[0]
        else:
            # No graphics extender available for this game
            return 1
    def fnCompareWBVersion(self, wbWant):
        wbHave = basher.settings['bash.version']
        return cmp(float(wbHave), float(wbWant))
    def fnDataFileExists(self, *filenames):
        for filename in filenames:
            if not bosh.dirs['mods'].join(filename).exists():
                # Check for ghosted mods
                if bolt.GPath(filename) in bosh.modInfos:
                    return True # It's a ghosted mod
                return False
        return True
    def fnGetEspmStatus(self, filename):
        file = bolt.GPath(filename)
        if file in bosh.modInfos.merged: return 3   # Merged
        if file in bosh.modInfos.ordered: return 2  # Active
        if file in bosh.modInfos.imported: return 1 # Imported (not active/merged)
        if file in bosh.modInfos: return 0          # Inactive
        return -1                                   # Not found
    def fnEditINI(self, iniName, section, setting, value, comment=None):
        iniPath = bolt.GPath(iniName)
        #--Section
        if section.strip().lower() == u'set':
            realSection = bolt.LString(u']set[')
        elif section.strip().lower() == u'setgs':
            realSection = bolt.LString(u']setgs[')
        else:
            realSection = bolt.LString(section.strip())
        #--Setting
        realSetting = bolt.LString(setting.strip())
        #--Comment
        if comment:
            if comment.strip().startswith(u';'):
                pass
            else:
                comment = u';'+comment
        else: comment = u''
        self.iniedits.setdefault(iniPath,{}).setdefault(realSection,[section,{}])
        self.iniedits[iniPath][realSection][0] = section
        self.iniedits[iniPath][realSection][1][realSetting] = (setting,value,comment,False)

    def fnDisableINILine(self, iniName, section, setting):
        iniPath = bolt.GPath(iniName)
        #--Section:
        section = section.strip()
        realSection = section.lower()
        if realSection == u'set':
            realSection = bolt.LString(u']set[')
        elif realSection == u'setgs':
            realSection = bolt.LString(u']setgs[')
        else:
            realSection = bolt.LString(section)
        #--Setting
        setting = setting.strip()
        realSetting = bolt.LString(setting)
        self.iniedits.setdefault(iniPath,{}).setdefault(realSection,[section,{}])
        self.iniedits[iniPath][realSection][0] = section
        self.iniedits[iniPath][realSection][1][realSetting] = (setting,u'',u'',True)

    def fnExec(self, strLines):
        lines = strLines.split(u'\n')
        lines.append(u'EndExec(%i)' % (len(lines)+1))
        self.lines[self.cLine:self.cLine] = lines
        self.ExecCount += 1
    def fnEndExec(self, numLines):
        if self.ExecCount == 0:
            error(UNEXPECTED % u'EndExec')
        del self.lines[self.cLine-numLines:self.cLine]
        self.cLine -= numLines
        self.ExecCount -= 1

    def fnStr(self, data): return unicode(data)
    def fnInt(self, data):
        try:
            return int(data)
        except:
            return 0
    def fnFloat(self, data):
        try:
            return float(data)
        except:
            return 0.0
    def fnLen(self, data):
        try:
            return len(data)
        except:
            return 0
    def fnEndsWith(self, String, *args):
        if not isinstance(String, basestring):
            error(_(u"Function 'endswith' only operates on string types."))
        try:
            return String.endswith(args)
        except:
            return False
    def fnStartsWith(self, String, *args):
        if not isinstance(String, basestring):
            error(_(u"Function 'startswith' only operates on string types."))
        try:
            return String.startswith(args)
        except:
            return False
    def fnLower(self, String):
        if not isinstance(String, basestring):
            error(_(u"Function 'lower' only operates on string types."))
        return String.lower()
    def fnFind(self, String, sub, start=0, end=-1):
        if not isinstance(String, basestring):
            error(_(u"Function 'find' only operates on string types."))
        if end < 0: end += len(String) + 1
        return String.find(sub, start, end)
    def fnRFind(self, String, sub, start=0, end=-1):
        if not isinstance(String, basestring):
            error(_(u"Function 'rfind' only operates on string types."))
        if end < 0: end += len(String) + 1
        return String.rfind(sub, start, end)
    def fnGetFilename(self, String):
        try:
            path = bolt.Path(String)
            return path.stail
        except:
            return u''
    def fnGetFolder(self, String):
        try:
            path = bolt.Path(String)
            return path.shead
        except:
            return u''

    # Dummy keyword, for reserving a keyword, but handled by other keywords (like from, to, and by)
    def kwdDummy(self):
        pass

    # Keywords, mostly for flow control (If, Select, etc)
    def kwdIf(self, bActive):
        if self.LenFlow() > 0 and self.PeekFlow().type == u'If' and not self.PeekFlow().active:
            #Inactive portion of an If-Elif-Else-EndIf statement, but we hit an If, so we need
            #To not count the next 'EndIf' towards THIS one
            self.PushFlow(u'If', False, [u'If', u'EndIf'])
            return
        self.PushFlow(u'If', bActive, [u'If', u'Else', u'Elif', u'EndIf'], ifTrue=bActive, hitElse=False)
    def kwdElif(self, bActive):
        if self.LenFlow() == 0 or self.PeekFlow().type != u'If' or self.PeekFlow().hitElse:
            error(UNEXPECTED % u'Elif')
        if self.PeekFlow().ifTrue:
            self.PeekFlow().active = False
        else:
            self.PeekFlow().active = bActive
            self.PeekFlow().ifTrue = self.PeekFlow().active or self.PeekFlow().ifTrue
    def kwdElse(self):
        if self.LenFlow() == 0 or self.PeekFlow().type != u'If' or self.PeekFlow().hitElse:
            error(UNEXPECTED % u'Else')
        if self.PeekFlow().ifTrue:
            self.PeekFlow().active = False
            self.PeekFlow().hitElse = True
        else:
            self.PeekFlow().active = True
            self.PeekFlow().hitElse = True
    def kwdEndIf(self):
        if self.LenFlow() == 0 or self.PeekFlow().type != u'If':
            error(UNEXPECTED % u'EndIf')
        self.PopFlow()

    def kwdWhile(self, bActive):
        if self.LenFlow() > 0 and self.PeekFlow().type == u'While' and not self.PeekFlow().active:
            #Within an un-true while statement, but we hit a new While, so we need to ignore the
            #next 'EndWhile' towards THIS one
            self.PushFlow('While', False, [u'While', u'EndWhile'])
            return
        self.PushFlow(u'While', bActive, [u'While', u'EndWhile'], cLine=self.cLine-1)
    def kwdContinue(self):
        #Find the next up While or For statement to continue from
        index = self.LenFlow()-1
        iType = None
        while index >= 0:
            iType = self.PeekFlow(index).type
            if iType in [u'While',u'For']:
                break
            index -= 1
        if index < 0:
            # No while statement was found
            error(UNEXPECTED % u'Continue')
        #Discard any flow control statments that happened after
        #the While/For, since we're resetting either back to the
        #the While/For', or the EndWhile/EndFor
        while self.LenFlow() > index+1:
            self.PopFlow()
        flow = self.PeekFlow()
        if iType == u'While':
            # Continue a While loop
            self.cLine = flow.cLine
            self.PopFlow()
        else:
            # Continue a For loop
            if flow.ForType == 0:
                # Numeric loop
                if self.variables[flow.varname] == flow.end:
                    # For loop is done
                    self.PeekFlow().active = False
                else:
                    # keep going
                    self.cLine = flow.cLine
                self.variables[flow.varname] += flow.by
            elif flow.ForType == 1:
                # Iterator type
                flow.index += 1
                if flow.index == len(flow.List):
                    # Loop is done
                    self.PeekFlow().active = False
                else:
                    # Re-loop
                    self.cLine = flow.cLine
                    self.variables[flow.varname] = flow.List[flow.index]
    def kwdEndWhile(self):
        if self.LenFlow() == 0 or self.PeekFlow().type != u'While':
            error(UNEXPECTED % u'EndWhile')
        #Re-evaluate the while loop's expression, if needed
        flow = self.PopFlow()
        if flow.active:
            self.cLine = flow.cLine

    def kwdFor(self, *args):
        if self.LenFlow() > 0 and self.PeekFlow().type == u'For' and not self.PeekFlow().active:
            #Within an ending For statement, but we hit a new For, so we need to ignore the
            #next 'EndFor' towards THIS one
            self.PushFlow(u'For', False, [u'For', u'EndFor'])
            return
        varname = args[0]
        if varname.type not in [ScriptParser.VARIABLE,ScriptParser.NAME]:
            error(_(u"Invalid syntax for 'For' statement.  Expected format:")
                    +u'\n For var_name from value_start to value_end [by value_increment]\n For var_name in SubPackages\n For var_name in subpackage_name'
                  )
        if args[1].text == 'from':
            #For varname from value_start to value_end [by value_increment]
            if (len(args) not in [5,7]) or (args[3].text != u'to') or (len(args)==7 and args[5].text != u'by'):
                error(_(u"Invalid syntax for 'For' statement.  Expected format:")
                      +u'\n For var_name from value_start to value_end\n For var_name from value_start to value_end by value_increment'
                      )
            start = self.ExecuteTokens([args[2]])
            end = self.ExecuteTokens([args[4]])
            if len(args) == 7:
                by = self.ExecuteTokens([args[6]])
            elif start > end:
                by = -1
            else:
                by = 1
            self.variables[varname.text] = start
            self.PushFlow(u'For', True, [u'For', u'EndFor'], ForType=0, cLine=self.cLine, varname=varname.text, end=end, by=by)
        elif args[1].text == u'in':
            # For name in SubPackages / For name in SubPackage
            if args[2].text == u'SubPackages':
                if len(args) > 4:
                    error(_(u"Invalid syntax for 'For' statement.  Expected format:")
                          +u'\n For var_name in Subpackages\n For var_name in subpackage_name'
                          )
                List = sorted(self.sublist.keys())
            else:
                name = self.ExecuteTokens(args[2:])
                try:
                    subpackage = self.GetPackage(name)
                except:
                    error(_(u"Subpackage '%s' does not exist.") % name)
                if subpackage is None:
                    error(_(u"SubPackage '%s' does not exist.") % name)
                List = []
                if isinstance(self.installer,bosh.InstallerProject):
                    dir = bosh.dirs['installers'].join(self.path,subpackage)
                    for root,dirs,files in dir.walk():
                        for file in files:
                            rel = root.join(file).relpath(dir)
                            List.append(rel.s)
                else:
                    # Archive
                    for file in self.installer.fileSizeCrcs:
                        rel = bolt.Path(file[0]).relpath(subpackage)
                        if not rel.s.startswith(u'..'):
                            List.append(rel.s)
                List.sort()
            if len(List) == 0:
                self.variables[varname.text] = u''
                self.PushFlow(u'For', False, [u'For',u'EndFor'])
            else:
                self.variables[varname.text] = List[0]
                self.PushFlow(u'For', True, [u'For',u'EndFor'], ForType=1, cLine=self.cLine, varname=varname.text, List=List, index=0)
        else:
            error(_(u"Invalid syntax for 'For' statement.  Expected format:")
                  +u'\n For var_name from value_start to value_end [by value_increment]\n For var_name in SubPackages\n For var_name in subpackage_name'
                  )
    def kwdEndFor(self):
        if self.LenFlow() == 0 or self.PeekFlow().type != u'For':
            error(UNEXPECTED % u'EndFor')
        #Increment the variable, then test to see if we should end or keep going
        flow = self.PeekFlow()
        if flow.active:
            if flow.ForType == 0:
                # Numerical loop
                if self.variables[flow.varname] == flow.end:
                    #For loop is done
                    self.PopFlow()
                else:
                    #Need to keep going
                    self.cLine = flow.cLine
                    self.variables[flow.varname] += flow.by
            elif flow.ForType == 1:
                # Iterator type
                flow.index += 1
                if flow.index == len(flow.List):
                    self.PopFlow()
                else:
                    self.cLine = flow.cLine
                    self.variables[flow.varname] = flow.List[flow.index]
        else:
            self.PopFlow()

    def kwdSelectOne(self, *args): self._KeywordSelect(False, u'SelectOne', *args)
    def kwdSelectMany(self, *args): self._KeywordSelect(True, u'SelectMany', *args)
    def _KeywordSelect(self, bMany, name, *args):
        args = list(args)
        if self.LenFlow() > 0 and self.PeekFlow().type == u'Select' and not self.PeekFlow().active:
            #We're inside an invalid Case for a Select already, so just add a blank FlowControl for
            #this select
            self.PushFlow(u'Select', False, [u'SelectOne', u'SelectMany', u'EndSelect'])
            return
        main_desc = args.pop(0)
        if len(args) % 3:
            error(MISSING_ARGS % name)
        images = []
        titles = []
        descs = []
        defaultMap = []
        image_paths = []
        while len(args):
            title = args.pop(0)
            if title[0] == u'|':
                defaultMap.append(True)
                titles.append(title[1:])
            else:
                defaultMap.append(False)
                titles.append(title)
            descs.append(args.pop(0))
            images.append(args.pop(0))
        if self.bAuto:
            #If there are no defaults specified, show the dialog anyway
            default = False
            for i in defaultMap:
                if defaultMap[i]:
                    temp = []
                    for index in range(len(titles)):
                        if defaultMap[index]:
                            temp.append(titles[index])
                            if not bMany:
                                break
                    self.PushFlow(u'Select', False, [u'SelectOne', u'SelectMany', u'Case', u'Default', u'EndSelect'], values=temp, hitCase=False)
                    return
        self.choiceIdex += 1
        if self.reversing:
            # We're using the 'Back' button
            self.reversing -= 1
            self.PushFlow(u'Select', False, [u'SelectOne', u'SelectMany', u'Case', u'Default', u'EndSelect'], values = self.choices[self.choiceIdex], hitCase=False)
            return
        # If not an auto-wizard, or an auto-wizard with no default option
        if self.bArchive:
            imageJoin = self.installer.tempDir.join
        else:
            imageJoin = bosh.dirs['installers'].join(self.path).join
        for i in images:
            path = imageJoin(i)
            if not path.exists() and bosh.dirs['mopy'].join(i).exists():
                path = bosh.dirs['mopy'].join(i)
            image_paths.append(path)
        self.page = PageSelect(self.parent, bMany, _(u'Installer Wizard'), main_desc, titles, descs, image_paths, defaultMap)
    def kwdCase(self, value):
        if self.LenFlow() == 0 or self.PeekFlow().type != u'Select':
            error(UNEXPECTED % u'Case')
        if value in self.PeekFlow().values or unicode(value) in self.PeekFlow().values:
            self.PeekFlow().hitCase = True
            self.PeekFlow().active = True
    def kwdDefault(self):
        if self.LenFlow() == 0 or self.PeekFlow().type != u'Select':
            error(UNEXPECTED % u'Default')
        if self.PeekFlow().hitCase:
            return
        self.PeekFlow().active = True
        self.PeekFlow().hitCase = True
    def kwdBreak(self):
        if self.LenFlow() > 0 and self.PeekFlow().type == u'Select':
            # Break for SelectOne/SelectMany
            self.PeekFlow().active = False
        else:
            # Test for a While/For statement earlier
            index = self.LenFlow()-1
            iType = None
            while index >=0:
                iType = self.PeekFlow(index).type
                if iType in [u'While',u'For']:
                    break
                index -= 1
            if index < 0:
                # No while or for statements found
                error(UNEXPECTED % u'Break')
            self.PeekFlow(index).active = False

            #We're going to jump to the EndWhile/EndFor, so discard
            #any flow control structs on top of the While/For one
            while self.LenFlow() > index+1:
                flow = self.PopFlow()
            flow.active = False
    def kwdEndSelect(self):
        if self.LenFlow() == 0 or self.PeekFlow().type != u'Select':
            error(UNEXPECTED % u'EndSelect')
        self.PopFlow()

    # Package selection functions
    def kwdSelectSubPackage(self, subpackage): self._SelectSubPackage(True, subpackage)
    def kwdDeSelectSubPackage(self, subpackage): self._SelectSubPackage(False, subpackage)
    def _SelectSubPackage(self, bSelect, subpackage):
        package = self.GetPackage(subpackage)
        if package:
            self.sublist[package] = bSelect
            for i in self.EspmList(package):
                if bSelect:
                    self._SelectEspm(True, i)
                else:
                    if not self.EspmHasActivePackage(i):
                        self._SelectEspm(False, i)
        else:
            error(_(u"Sub-package '%s' is not a part of the installer.") % subpackage)
    def kwdSelectAll(self): self._SelectAll(True)
    def kwdDeSelectAll(self): self._SelectAll(False)
    def _SelectAll(self, bSelect):
        for i in self.sublist.keys():
            self.sublist[i] = bSelect
        for i in self.espmlist.keys():
            self.espmlist[i] = bSelect
    def kwdSelectEspm(self, espm): self._SelectEspm(True, espm)
    def kwdDeSelectEspm(self, espm): self._SelectEspm(False, espm)
    def _SelectEspm(self, bSelect, name):
        espm = self.GetEspm(name)
        if espm:
            self.espmlist[espm] = bSelect
        else:
            error(_(u"Espm '%s' is not a part of the installer.") % name)
    def kwdSelectAllEspms(self): self._SelectAllEspms(True)
    def kwdDeSelectAllEspms(self): self._SelectAllEspms(False)
    def _SelectAllEspms(self, bSelect):
        for i in self.espmlist.keys():
            self.espmlist[i] = bSelect

    def kwdRenameEspm(self, espm, newName):
        espm = self.GetEspm(espm)
        if espm:
            # Keep same extension
            if espm.lower()[-4:] != newName.lower()[-4:]:
                raise ScriptParser.ParserError(_(u'Cannot rename %s to %s: the extensions must match.') % (espm, newName))
            self.espmrenames[espm] = newName
    def kwdResetEspmName(self, espm):
        espm = self.GetEspm(espm)
        if espm and espm in self.espmrenames:
            del self.espmrenames[espm]
    def kwdResetAllEspmNames(self):
        self.espmrenames = dict()

    def kwdNote(self, note):
        self.notes.append(u'- %s\n' % note)

    def kwdRequireVersions(self, game, se=u'None', ge=u'None', wbWant=u'0.0'):
        if self.bAuto: return

        gameWant = self._TestVersion_Want(game)
        if gameWant == u'None': game = u'None'
        seWant = self._TestVersion_Want(se)
        if seWant == u'None': se = u'None'
        geWant = self._TestVersion_Want(ge)
        if geWant == u'None': ge = u'None'
        if not wbWant: wbWant = u'0.0'
        wbHave = basher.settings['bash.version']

        ret = self._TestVersion(gameWant, bosh.dirs['app'].join(bush.game.exe))
        bGameOk = ret[0] >= 0
        gameHave = ret[1]
        if bush.game.se.shortName != u'':
            if bosh.inisettings['SteamInstall']:
                seName = bush.game.se.steamExe
            else:
                seName = bush.game.se.exe
            ret = self._TestVersion(seWant, bosh.dirs['app'].join(seName))
            bSEOk = ret[0] >= 0
            seHave = ret[1]
        else:
            bSEOk = True
            seHave = u'None'
        if bush.game.ge.shortName != u'':
            ret = self._TestVersion_GE(geWant)
            bGEOk = ret[0] >= 0
            geHave = ret[1]
        else:
            bGEOk = True
            geHave = u'None'
        try:
            bWBOk = float(wbHave) >= float(wbWant)
        except:
            # Error converting to float, just assume it's OK
            bWBOk = True

        if not bGameOk or not bSEOk or not bGEOk or not bWBOk:
            self.page = PageVersions(self.parent, bGameOk, gameHave, game, bSEOk, seHave, se, bGEOk, geHave, ge, bWBOk, wbHave, wbWant)
    def _TestVersion_GE(self, want):
        if isinstance(bush.game.ge.exe,str):
            files = [bosh.dirs['mods'].join(bush.game.ge.exe)]
        else:
            files = [bosh.dirs['mods'].join(*x) for x in bush.game.ge.exe]
        for file in reversed(files):
            ret = self._TestVersion(want, file)
            if ret[1] != u'None':
                return ret
        return ret
    def _TestVersion_Want(self, want):
        try:
            need = [int(i) for i in want.split(u'.')]
        except:
            need = u'None'
        return need
    def _TestVersion(self, need, file):
        if file.exists():
            info = win32api.GetFileVersionInfo(file.s, u'\\')
            ms = info['FileVersionMS']
            ls = info['FileVersionLS']
            have = win32api.HIWORD(ms), win32api.LOWORD(ms), win32api.HIWORD(ls), win32api.LOWORD(ls)
            ver = u'.'.join([unicode(i) for i in have])
            if need == u'None':
                return [1, ver]
            if len(need) != 4:
                error(_(u"Version '%s' expected in format 'x.x.x.x'") % need)
                return [-1, ver]
            if have[0] > need[0]: return [1, ver]
            if have[0] < need[0]: return [-1, ver]
            if have[1] > need[1]: return [1, ver]
            if have[1] < need[1]: return [-1, ver]
            if have[2] > need[2]: return [1, ver]
            if have[2] < need[2]: return [-1, ver]
            if have[3] > need[3]: return [1, ver]
            if have[3] < need[3]: return [-1, ver]
            return [0, ver]
        elif need == u'None':
            return [0, u'None']
        return [-1, u'None']
    def kwdReturn(self):
        self.page = PageFinish(self.parent, self.sublist, self.espmlist, self.espmrenames, self.bAuto, self.notes, self.iniedits)
    def kwdCancel(self, msg=_(u"No reason given")):
        self.page = PageError(self.parent, _(u'The installer wizard was canceled:'), msg)
# END --------------------------------------------------------------------------------------------------
bolt.codebox = WryeParser.codebox