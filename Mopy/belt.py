#===================================================
# Specific parser for Wrye Bash
#===================================================
import ScriptParser         # generic parser class
import wx
import wx.wizard as wiz     # wxPython wizard class
import bosh, balt
from bolt import _
import struct, string
import win32api
#---------------------------------------------------
gDialogSize = (600,440)
#---------------------------------------------------

def replaceShader(sdpFileName, shaderName, shaderFileName):
    temp = bosh.dirs['mods'].join('Shaders', sdpFileName+'.bak')
    sdp = bosh.dirs['mods'].join('Shaders', sdpFileName)
    sNew = bosh.dirs['mods'].join('Shaders', shaderFileName)
    sBak = bosh.dirs['app'].join('Mopy', 'Data', 'Shaders Backup', sdpFileName, shaderName)

    if not sdp.exists() and not sdp.isfile(): return
    if not sNew.exists() and not sNew.isfile(): return
    if sBak.exists() and sBak.isfile():
        sBak.remove()

    sdp.moveTo(temp.s)        
    
    shaderFile = sNew.open('rb')
    newData = shaderFile.read()
    shaderFile.close()
    
    backupFile = sBak.open('wb')

    editShader(sdp, temp, shaderName, newData, backupFile)
    
def restoreShader(sdpFileName, shaderName):
    temp = bosh.dirs['mods'].join('Shaders', sdpFileName+'.bak')
    sdp = bosh.dirs['mods'].join('Shaders', sdpFileName)
    dBackup = bosh.dirs['app'].join('Mopy', 'Data', 'Shaders Backup', sdpFileName)
    sNew = dBackup.join(shaderName)

    if not sdp.exists() and not sdp.isfile(): return
    if not sNew.exists() and not sNew.isfile(): return

    sdp.moveTo(temp.s)
    shaderFile = sNew.open('rb')
    newData = shaderFile.read()
    shaderFile.close()

    editShader(sdp, temp, shaderName, newData, None)
    sNew.remove()
    #Clean up dirs
    for path, dirs, files in dbackup.walk():
        if len(dirs) == 0 and len(files) == 0:
            path.removedirs()
        
def editShader(sdp, temp, shaderName, newData, backupFile):
    mtime = temp.getmtime()
    newSDP = sdp.open('wb')
    oldSDP = temp.open('rb')

    #Read some bytes
    newSDP.write(oldSDP.read(4))

    #Read the number of shaders
    numstr = oldSDP.read(4)
    (num,) = struct.unpack('l', numstr)
    newSDP.write(numstr)

    #Save position of the 'size' bytes
    sizeoffset = oldSDP.tell()
    newSDP.write(oldSDP.read(4))

    #Go through each shader
    bFound = False
    for i in range(num):
        name = oldSDP.read(0x100)
        newSDP.write(name)
        sizestr = oldSDP.read(4)
        (size,) = struct.unpack('l', sizestr)
        data = oldSDP.read(size)

        #See if it's the right one
        if not bFound:
            #shader names are stored as 256 character null-terminated strings,
            #python strings aren't null-terminated so...
            sname = string.lower(name[:string.find(name, '\0')])

            if sname == string.lower(shaderName):
                newSDP.write(struct.pack('l', len(newData)))
                newSDP.write(newData)
                bFound = True

                if backupFile:            
                    backupFile.write(data)
                    backupFile.close()
                continue
        newSDP.write(sizestr)
        newSDP.write(data)
    # Now update the size value at the beginning of the file
    newSDP.seek(sizeoffset)
    size = sdp.size - 12
    newSDP.write(struct.pack('l', size))

    newSDP.close()
    oldSDP.close()
    temp.remove()    

    # Finally update the time stamps
    sdp.setmtime(mtime)
    
class WizardReturn(object):
    __slots__ = ('Canceled', 'SelectEspms', 'SelectSubPackages', 'Install')

    def __init__(self):
        self.Canceled = False
        self.SelectEspms = []
        self.SelectSubPackages = []
        self.Install = False

# InstallerWizard ----------------------------------
#  Class used by Wrye Bash, creates a wx Wizard that
#  dynamically creates pages based on a script
#---------------------------------------------------
class InstallerWizard(wiz.Wizard):
    def __init__(self, link, subs):
        wiz.Wizard.__init__(self, link.gTank, -1, 'Installer Wizard')
        #Hide the "Previous" button, we wont use it
        self.FindWindowById(wx.ID_BACKWARD).Hide()

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
            installer.unpackToTemp(path, ['wizard.txt'])
            self.wizard_file = installer.tempDir.join('wizard.txt')
        else:
            self.wizard_file = link.data.dir.join(path.s, 'wizard.txt')
        self.parser = WryeParser(self, installer, subs, bArchive, path, link.bAuto)

        #Intercept the changing event so we can implement 'blockChange'        
        self.Bind(wiz.EVT_WIZARD_PAGE_CHANGING, self.OnChange)
        self.ret = WizardReturn()

        #Set the size for the wizard to use
        self.SetPageSize(gDialogSize)

    def HasPrevPage(self): return False

    def OnChange(self, event):
        if not self.finishing:
            if event.GetDirection():
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
                event.Veto()

    def Run(self):
        page = self.parser.Begin(self.wizard_file)
        if page:
            self.ret.Canceled = not self.RunWizard(page)
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

    def GetNext(self): return self.parent.dummy
    def GetPrev(self): return None
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
        textError = wx.TextCtrl(self, -1, errorMsg, style=wx.TE_READONLY|wx.TE_MULTILINE)
        sizerMain.Add(wx.StaticText(self, -1, title))
        sizerMain.Add(textError, 0, wx.ALL|wx.CENTER|wx.EXPAND)
        sizerMain.AddGrowableCol(0)
        sizerMain.AddGrowableRow(1)
        self.SetSizer(sizerMain)
        self.Layout()

    def GetNext(self): return None        
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

        sizerMain = wx.FlexGridSizer(4, 1, 5, 0)

        sizerTitle = wx.StaticBoxSizer(wx.StaticBox(self, -1, ''))
        self.TitleDesc = wx.StaticText(self, -1, desc)
        sizerTitle.Add(self.TitleDesc, 0, wx.ALIGN_CENTER|wx.ALL)
        sizerMain.Add(sizerTitle, 0, wx.EXPAND)

        sizerBoxes = wx.FlexGridSizer(2, 2, 5, 5)
        sizerBoxes.Add(wx.StaticText(self, -1, 'Options:'))
        sizerBoxes.AddStretchSpacer()
        self.textItem = wx.TextCtrl(self, -1, '', style=wx.TE_READONLY|wx.TE_MULTILINE)        
        self.bmpItem = wx.StaticBitmap(self, -1, wx.NullBitmap, size=(200, 200))
        if bMany:
            self.listOptions = wx.CheckListBox(self, 643, choices=listItems)
            for index, default in enumerate(defaultMap):
                self.listOptions.Check(index, default)
        else:
            self.listOptions = wx.ListBox(self, 643, choices=listItems)
            for index, default in enumerate(defaultMap):
                if default:
                    self.listOptions.Select(index)
                    self.Selection(index)
                    break
        sizerBoxes.Add(self.listOptions, 0, wx.ALL|wx.EXPAND)
        sizerBoxes.Add(self.bmpItem, 0, wx.ALL|wx.EXPAND)
        sizerBoxes.AddGrowableRow(1)
        sizerBoxes.AddGrowableCol(0)
        sizerBoxes.AddGrowableCol(1)
        sizerMain.Add(sizerBoxes, -1, wx.EXPAND)

        sizerMain.Add(wx.StaticText(self, -1, 'Description:'))
        sizerMain.Add(self.textItem, -1, wx.EXPAND|wx.ALL)

        self.SetSizer(sizerMain)
        sizerMain.AddGrowableRow(3)
        sizerMain.AddGrowableCol(0)
        self.Layout()

        wx.EVT_LISTBOX(self, 643, self.OnSelect)

    def OnSelect(self, event):
        index = event.GetSelection()
        self.Selection(index)

    def Selection(self, index):
        self.textItem.SetLabel(self.descs[index])
        file = self.images[index]
        if file.exists() and not file.isdir():
            image = wx.Image( file.s )
            factor = 400.0 / max(image.GetHeight(), image.GetWidth())
            newHeight = round(image.GetHeight() * factor)
            newWidth = round(image.GetWidth() * factor)
            image.Rescale(newWidth, newHeight)
            self.bmp = wx.BitmapFromImage(image)
            self.bmpItem.SetBitmap(self.bmp)
        else:
            self.bmpItem.SetBitmap(wx.NullBitmap)
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
        self.parent.parser.AddFlowControl('Select', False, ['SelectOne', 'SelectMany', 'Case', 'Default', 'EndSelect'], values=temp, hitCase=False)
# End PageSelect -----------------------------------------

# PageFinish ---------------------------------------------
#  Page displayed at the end of a wizard, showing which
#  sub-packages and which esps and espms will be
#  selected.  Also displays some notes for the user
#---------------------------------------------------------
class PageFinish(PageInstaller):
    def __init__(self, parent, subsList, espmsList, bAuto, notes):
        PageInstaller.__init__(self, parent)

        subs = subsList.keys()
        subs.sort(lambda l,r: cmp(l, r))
        espms = espmsList.keys()
        espms.sort(lambda l,r: cmp(l, r))

        sizerMain = wx.FlexGridSizer(4, 1, 5, 0)

        sizerTitle = wx.StaticBoxSizer(wx.StaticBox(self, -1, ''))
        textTitle = wx.StaticText(self, -1, "The installer script has finished, and selected the following sub-packages, esps, and esms to be installed.")
        textTitle.Wrap(gDialogSize[0]-10)
        sizerTitle.Add(textTitle, 0, wx.ALIGN_CENTER|wx.ALL)
        sizerMain.Add(sizerTitle, 0, wx.EXPAND)

        sizerLists = wx.FlexGridSizer(2, 2, 5, 5)
        sizerLists.Add(wx.StaticText(self, -1, 'Sub-Packages'))
        sizerLists.Add(wx.StaticText(self, -1, 'Esp/ms'))
        self.listSubs = wx.CheckListBox(self, -1, choices=subs)
        #self.listSubs.Enable(False)
        #TODO: Figure way to still allow scrolling packages, but not checking the checkbox
        #      I've 'enabled' the subpackage and esp/m list boxes, so that if there are
        #      a lot of items, the scrollbar works, but this gives the illusion that the user
        #      can select and deselect subpackages and esp/m's...which you can't from here
        index = -1
        for key in subs:
            index += 1
            if subsList[key]:
                self.listSubs.Check(index, True)
                self.parent.ret.SelectSubPackages.append(key)
        self.listEspms = wx.CheckListBox(self, -1, choices=espms)
        #self.listEspms.Enable(False)
        index = -1
        for key in espms:
            index += 1
            if espmsList[key]:
                self.listEspms.Check(index, True)
                self.parent.ret.SelectEspms.append(key)
        sizerLists.Add(self.listSubs, 0, wx.ALL|wx.EXPAND)
        sizerLists.Add(self.listEspms, 0, wx.ALL|wx.EXPAND)
        sizerLists.AddGrowableRow(1)
        sizerLists.AddGrowableCol(0)
        sizerLists.AddGrowableCol(1)
        sizerMain.Add(sizerLists, 1, wx.EXPAND)

        sizerNotes = wx.FlexGridSizer(2, 1, 5, 0)
        sizerNotes.Add(wx.StaticText(self, -1, 'Notes:'))
        sizerNotes.Add(wx.TextCtrl(self, -1, ''.join(notes), style=wx.TE_READONLY|wx.TE_MULTILINE), 1, wx.EXPAND)
        sizerNotes.AddGrowableCol(0)
        sizerNotes.AddGrowableRow(1)
        sizerMain.Add(sizerNotes, 2, wx.TOP|wx.EXPAND)

        sizerChecks = wx.FlexGridSizer(1, 2, 5, 0)
        self.checkApply = wx.CheckBox(self, 111, "Apply these selections")
        self.checkApply.SetValue(bAuto)
        wx.EVT_CHECKBOX(self, 111, self.OnCheckApply)
        sizerChecks.AddStretchSpacer()
        sizerChecks.Add(self.checkApply)
        sizerChecks.AddGrowableRow(0)
        sizerChecks.AddGrowableCol(0)
        sizerMain.Add(sizerChecks, 3, wx.EXPAND|wx.TOP)

        self.parent.FindWindowById(wx.ID_FORWARD).Enable(bAuto)
        self.parent.finishing = True

        sizerMain.AddGrowableCol(0)
        sizerMain.AddGrowableRow(1)
        sizerMain.AddGrowableRow(2)
        self.SetSizer(sizerMain)
        self.Layout()

    def OnCheckApply(self, event):
        self.parent.FindWindowById(wx.ID_FORWARD).Enable(self.checkApply.IsChecked())

    def GetNext(self): return None
# End PageFinish -------------------------------------


# PageVersions ---------------------------------------
#  Page for displaying what versions an installer
#  requires/recommends and what you have installed
#  for Oblivion, OBSE, and OBGE
#-----------------------------------------------------
class PageVersions(PageInstaller):
    def __init__(self, parent, bObOk, obHave, obNeed, bOBSEOk, obseHave, obseNeed, bOBGEOk, obgeHave, obgeNeed):
        PageInstaller.__init__(self, parent)

        bmpGood = wx.Bitmap(bosh.dirs['app'].join('Mopy', 'images', 'check.png').s)
        bmpBad = wx.Bitmap(bosh.dirs['app'].join('Mopy', 'images', 'x.png').s)
        
        sizerMain = wx.FlexGridSizer(5, 1, 0, 0)

        self.textWarning = wx.StaticText(self, 124, 'WARNING: The following version requirements are not met for using this installer.')
        self.textWarning.Wrap(gDialogSize[0]-20)
        sizerMain.Add(self.textWarning, 0, wx.ALL|wx.ALIGN_CENTER, 5)

        sizerVersionsTop = wx.StaticBoxSizer(wx.StaticBox(self, -1, 'Version Requirements'))
        sizerVersions = wx.FlexGridSizer(4, 4, 5, 5)
        sizerVersionsTop.Add(sizerVersions, 1, wx.EXPAND, 0)

        sizerVersions.AddStretchSpacer()
        sizerVersions.Add(wx.StaticText(self, -1, 'Need'))
        sizerVersions.Add(wx.StaticText(self, -1, 'Have'))
        sizerVersions.AddStretchSpacer()

        linkOb = wx.HyperlinkCtrl(self, -1, 'Oblivion', 'http://www.elderscrolls.com/downloads/updates_patches.htm')
        linkOb.SetVisitedColour(linkOb.GetNormalColour())
        linkOb.SetToolTip(wx.ToolTip('http://www.elderscrolls.com/'))
        sizerVersions.Add(linkOb)
        sizerVersions.Add(wx.StaticText(self, -1, obNeed))
        sizerVersions.Add(wx.StaticText(self, -1, obHave))
        if bObOk:
            sizerVersions.Add(wx.StaticBitmap(self, -1, bmpGood))
        else:
            sizerVersions.Add(wx.StaticBitmap(self, -1, bmpBad))

        linkOBSE = wx.HyperlinkCtrl(self, -1, 'Oblivion Script Extender', 'http://obse.silverlock.org/')
        linkOBSE.SetVisitedColour(linkOBSE.GetNormalColour())
        linkOBSE.SetToolTip(wx.ToolTip('http://obse.silverlock.org/'))
        sizerVersions.Add(linkOBSE)
        sizerVersions.Add(wx.StaticText(self, -1, obseNeed))
        sizerVersions.Add(wx.StaticText(self, -1, obseHave))
        if bOBSEOk:
            sizerVersions.Add(wx.StaticBitmap(self, -1, bmpGood))
        else:
            sizerVersions.Add(wx.StaticBitmap(self, -1, bmpBad))

        linkOBGE = wx.HyperlinkCtrl(self, -1, 'Oblivion Graphics Extender', 'http://timeslip.chorrol.com/obge.html')
        linkOBGE.SetVisitedColour(linkOBGE.GetNormalColour())
        linkOBGE.SetToolTip(wx.ToolTip('http://timeslip.chorrol.com/'))
        sizerVersions.Add(linkOBGE)
        sizerVersions.Add(wx.StaticText(self, -1, obgeNeed))
        sizerVersions.Add(wx.StaticText(self, -1, obgeHave))
        if bOBGEOk:
            sizerVersions.Add(wx.StaticBitmap(self, -1, bmpGood))
        else:
            sizerVersions.Add(wx.StaticBitmap(self, -1, bmpBad))

        sizerVersions.AddGrowableCol(0)
        sizerVersions.AddGrowableCol(1)
        sizerVersions.AddGrowableCol(2)
        sizerVersions.AddGrowableCol(3)
        sizerMain.Add(sizerVersionsTop, 2, wx.ALL|wx.EXPAND, 5)
        
        sizerMain.AddStretchSpacer()
        
        sizerCheck = wx.FlexGridSizer(1, 2, 5, 5)
        self.checkOk = wx.CheckBox(self, 123, 'Install anyway.')
        wx.EVT_CHECKBOX(self, 123, self.OnCheck)
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
    def __init__(self, parent, installer, subs, bArchive, path, bAuto):
        ScriptParser.Parser.__init__(self)
        self.parent = parent
        self.installer = installer
        self.bArchive = bArchive
        self.path = path
        self.bAuto = bAuto
        self.notes = []
        self.page = None

        self.sublist = {}
        self.espmlist = {}
        for i in installer.espmMap.keys():
            for j in installer.espmMap[i]:
                if j not in self.espmlist:
                    self.espmlist[j] = False
            if i == '': continue
            self.sublist[i] = False                
            
        self.AddAssignmentOperator('+=', self.AssignPlus)
        self.AddAssignmentOperator('-=', self.AssignMin)
        self.AddAssignmentOperator('*=', self.AssignMult)
        self.AddAssignmentOperator('/=', self.AssignDiv)
        self.AddAssignmentOperator('%=', self.AssignMod)
        self.AddAssignmentOperator('^=', self.AssignPow)
        self.AddBooleanOperator('==', self.CompE)
        self.AddBooleanOperator('!=', self.CompNE)
        self.AddBooleanOperator('>=', self.CompGE)
        self.AddBooleanOperator('>', self.CompG)
        self.AddBooleanOperator('<=', self.CompLE)
        self.AddBooleanOperator('<', self.CompL)
        self.AddBooleanOperator('|', self.Or)
        self.AddBooleanOperator('&', self.And)
        self.AddFunction('!', self.Not)
        self.AddFunction('CompareOblivionVersion', self.FunctionCompareOblivionVersion)
        self.AddFunction('CompareOBSEVersion', self.FunctionCompareOBSEVersion)
        self.AddFunction('CompareOBGEVersion', self.FunctionCompareOBGEVersion)
        self.AddFunction('DataFileExists', self.FunctionDataFileExists)
        self.AddKeyword('SelectSubPackage', self.KeywordSelectSubPackage)
        self.AddKeyword('DeSelectSubPackage', self.KeywordDeSelectSubPackage)
        self.AddKeyword('SelectEspm', self.KeywordSelectEspm)
        self.AddKeyword('DeSelectEspm', self.KeywordDeSelectEspm)
        self.AddKeyword('SelectAll', self.KeywordSelectAll)
        self.AddKeyword('DeSelectAll', self.KeywordDeSelectAll)
        self.AddKeyword('SelectAllEspms', self.KeywordSelectAllEspms)
        self.AddKeyword('DeSelectAllEspms', self.KeywordDeSelectAllEspms)
        self.AddKeyword('Note', self.KeywordNote)
        self.AddKeyword('If', self.KeywordIf)
        self.AddKeyword('Elif', self.KeywordElif)
        self.AddKeyword('Else', self.KeywordElse)
        self.AddKeyword('EndIf', self.KeywordEndIf)
        self.AddKeyword('SelectOne', self.KeywordSelectOne)
        self.AddKeyword('SelectMany', self.KeywordSelectMany)
        self.AddKeyword('Case', self.KeywordCase)
        self.AddKeyword('Default', self.KeywordDefault)
        self.AddKeyword('Break', self.KeywordBreak)
        self.AddKeyword('EndSelect', self.KeywordEndSelect)
        self.AddKeyword('Return', self.KeywordReturn)
        self.AddKeyword('Cancel', self.KeywordCancel)
        self.AddKeyword('RequireVersions', self.KeywordRequireVersions)
        self.AddConstant('True', True)
        self.AddConstant('False', False)

    def Begin(self, file):
        self.vars = {}
        self.Flow = []
        self.cLine = 0

        if file.exists() and file.isfile():
            script = file.open()
            self.lines = script.readlines()
            script.close()
            return self.Continue()
        balt.showWarning(self.parent, _('Could not open wizard file'))
        return None

    def Continue(self):
        self.page = None
        while len(self.lines) > 0:
            newline = self.lines.pop(0)
            self.cLine += 1
            try:
                self.RunLine(newline)
            except ScriptParser.ParserError, e:
                return PageError(self.parent, "An error occured in the wizard script:", "Line " + str(self.cLine) + ": '" + newline.strip('\n') + "'\nError:  " + str(e))
            if self.page:
                return self.page
        return PageFinish(self.parent, self.sublist, self.espmlist, self.bAuto, self.notes)

    def EspmIsInPackage(self, esmp, package):
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
    def EspmHasActivePackage(self, esmp):
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
    def AssignPlus(parser, var, value): parser.vars[var] += value
    def AssignMin(parser, var, value): parser.vars[var] -= value
    def AssignMult(parser, var, value): parser.vars[var] *= value
    def AssignDiv(parser, var, value): parser.vars[var] /= value
    def AssignMod(parser, var, value): parser.vars[var] %= value
    def AssignPow(parser, var, value): parser.vars[var] **= value

    # Comparison boolean operators
    def CompE(parser, lval, rval): return lval == rval
    def CompNE(parser, lval, rval): return lval != rval
    def CompGE(parser, lval, rval): return lval >= rval
    def CompG(parser, lval, rval): return lval > rval
    def CompLE(parser, lval, rval): return lval <= rval
    def CompL(parser, lval, rval): return lval < rval

    # and, or, not boolean operators
    def And(parser, lval, rval): return lval and rval
    def Or(parser, lval, rval): return lval or rval
    def Not(self, params):
        if len(params) > 1:
            self.error('Extra arguments to NOT operator (!)')
        if len(params) < 1:
            self.error('Missing argument to NOT operator (!)')
        return not params[0]

    # Functions...
    def FunctionCompareOblivionVersion(self, params):
        if len(params) > 1:
            self.error("Extra arguments to function 'CompareOblivionVersion'")
        if len(params) < 1:
            self.error("Missing argument to function 'CompareOblivionVersion'")
        ret = self._TestVersion(self._TestVersion_Want(params[0]), bosh.dirs['app'].join('oblivion.exe'))
        return ret[0]
    def FunctionCompareOBSEVersion(self, params):
        if len(params) > 1:
            self.error("Extra arguments to function 'CompareOBSEVersion'")
        if len(params) < 1:
            self.error("Missing argument to function 'CompareOBSEVersion'")
        ret = self._TestVersion(self._TestVersion_Want(params[0]), bosh.dirs['app'].join('obse_loader.exe'))
        return ret[0]
    def FunctionCompareOBGEVersion(self, params):
        if len(params) > 1:
            self.error("Extra arguments to function 'CompareOBGEVersion'")
        if len(params) < 1:
            self.error("Missing argument to function 'CompareOBGEVersion'")
        ret = self._TestVersion(self._TestVersion_Want(params[0]), bosh.dirs['mods'].join('obse', 'plugins', 'obge.dll'))
        return ret[0]
    def FunctionDataFileExists(self, params):
        if len(params) > 1:
            self.error("Extra arguments to function 'DataFileExists'")
        if len(params) < 1:
            self.error("Missing argument to function 'DataFileExists'")
        return bosh.dirs['mods'].join(params[0]).exists()

    # Keywords, mostly for flow control (If, Select, etc)
    def KeywordIf(self, line):
        if self.LenFlowControl() > 0 and self.GetFlowControl(-1).type == 'If' and not self.GetFlowControl(-1).active:
            #Inactive portion of an If-Elif-Else-EndIf statement, but we hit an If, so we need
            #To not count the next 'EndIf' towards THIS one
            self.AddFlowControl('If', False, ['If', 'EndIf'])
            return
        if len(line) == 0:
            self.error("Missing arguements to 'If'.")
        bActive = self.Eval(line)
        self.AddFlowControl('If', bActive, ['If', 'Else', 'Elif', 'EndIf'], ifTrue=bActive, hitElse=False)
    def KeywordElif(parser, line):
        if parser.LenFlowControl() == 0 or parser.GetFlowControl(-1).type != 'If' or parser.GetFlowControl(-1).hitElse:
            parser.error("Unexpected 'Elif'")
        if parser.GetFlowControl(-1).ifTrue:
            parser.GetFlowControl(-1).active = False
        elif len(line) == 0:
            parser.error("Missing arguments to 'Elif'")
        else:
            parser.GetFlowControl(-1).active = parser.Eval(line)
            parser.GetFlowControl(-1).ifTrue = parser.GetFlowControl(-1).active or parser.GetFlowControl(-1).ifTrue
    def KeywordElse(parser, line):
        if len(line) > 1:
            parser.error("Extra arguments to 'Else'")
        if parser.LenFlowControl() == 0 or parser.GetFlowControl(-1).type != 'If' or parser.GetFlowControl(-1).hitElse:
            parser.error("Unexpected 'Else'")
        if parser.GetFlowControl(-1).ifTrue:
            parser.GetFlowControl(-1).active = False
            parser.GetFlowControl(-1).hitElse = True
        else:
            parser.GetFlowControl(-1).active = True
            parser.GetFlowControl(-1).hitElse = True
    def KeywordEndIf(parser, line):
        if parser.LenFlowControl() == 0 or parser.GetFlowControl(-1).type != 'If':
            parser.error("Unexpected 'EndIf'")
        parser.PopFlowControl()

    def KeywordSelectOne(self, line): self._KeywordSelect(line, False, 'SelectOne')
    def KeywordSelectMany(self, line): self._KeywordSelect(line, True, 'SelectMany')
    def _KeywordSelect(self, line, bMany, name):
        if self.LenFlowControl() > 0 and self.GetFlowControl(-1).type == 'Select' and not self.GetFlowControl(-1).active:
            #We're inside an invalid Case for a Select alread, so just add a blank FlowControl for
            #this select
            self.AddFlowControl('Select', False, ['SelectOne', 'SelectMany', 'EndSelect'])
            return
        if (not bMany and len(line) < 7) or (bMany and len(line) < 4):
            self.error("Missing arguments to '" + name + "'")
        main_desc = line.pop(0)
        if len(line) % 3:
            self.error("Missing arguments to '" + name + "'")
        images = []
        titles = []
        descs = []
        defaultMap = []
        image_paths = []
        while len(line):
            title = line.pop(0)
            if title[0] == '|':
                defaultMap.append(True)
                titles.append(title[1:])
            else:
                defaultMap.append(False)
                titles.append(title)
            descs.append(line.pop(0))
            images.append(line.pop(0))
        if self.bAuto:
            temp = []
            for index in range(len(titles)):
                if defaultMap[index]:
                    temp.append(titles[index])
                    if not bMany:
                        break
            self.AddFlowControl('Select', False, ['SelectOne', 'SelectMany', 'Case', 'Default', 'EndSelect'], values=temp, hitCase=False)
            return
        if self.bArchive:
            temp = []
            for i in images:
                if i == '': continue
                temp.append(i)
            if len(temp):
                self.installer.unpackToTemp(self.path, temp)
            for i in images:
                image_paths.append(self.installer.tempDir.join(i))
        else:
            for i in images:
                image_paths.append(bosh.dirs['installers'].join(self.path.s, i))
        self.page = PageSelect(self.parent, bMany, 'Installer Wizard', main_desc, titles, descs, image_paths, defaultMap)
    def KeywordCase(parser, line):
        if parser.LenFlowControl() == 0 or parser.GetFlowControl(-1).type != 'Select':
            parser.error("Unexpected 'Case'")
        if len(line) == 0:
            parser.error("Missing arguments to 'Case'")
        case = ' '.join(line)
        parser.GetFlowControl(-1).hitCase = True
        if case in parser.GetFlowControl(-1).values:
            parser.GetFlowControl(-1).active = True
    def KeywordDefault(parser, line):
        if parser.LenFlowControl() == 0 or parser.GetFlowControl(-1).type != 'Select':
            parser.error("Unexpected 'Default'")
        if parser.GetFlowControl(-1).hitCase:
            return
        if len(line) != 1:
            parser.error("Extra arguments to 'Default'")
        parser.GetFlowControl(-1).active = True
        parser.GetFlowControl(-1).hitCase = True
    def KeywordBreak(parser, line):
        if parser.LenFlowControl() == 0 or parser.GetFlowControl(-1).type != 'Select':
            parser.error("Unexpected 'Break'")
        parser.GetFlowControl(-1).active = False
    def KeywordEndSelect(parser, line):
        if parser.LenFlowControl() == 0 or parser.GetFlowControl(-1).type != 'Select':
            parser.error("Unexpected 'EndSelect'")
        parser.PopFlowControl()

    # Package selection functions
    def KeywordSelectSubPackage(self, line): self._SelectSubPackage(line, True, 'SelectSubPackage')
    def KeywordDeSelectSubPackage(self, line): self._SelectSubPackage(line, False, 'DeSelectSubPackage')
    def _SelectSubPackage(self, line, bSelect, name):
        if len(line) < 1:
            self.error("Missing arguments to '" + name + "'")
        if len(line) > 1:
            self.error("Extra arguments to '" + name + "'")
        package = self.GetPackage(line[0])
        if package:
            self.sublist[package] = bSelect
            for i in self.EspmList(package):
                if bSelect:
                    self._SelectEspm([i], True, 'SelectEspm')
                else:
                    if not self.EspmHasActivePackage(i):
                        self._SelectEspm([i], False, 'DeSelectEspm')
        else:
            self.error("Sub-package '" + line[0] + "' is not a part of the installer.")
    def KeywordSelectAll(self, line): self._SelectAll(line, True, 'SelectAll')
    def KeywordDeSelectAll(self, line): self._SelectAll(line, False, 'DeSelectAll')
    def _SelectAll(self, line, bSelect, name):
        if len(line) > 0:
            self.error("Extra arguments to '" + name + "'")
        for i in self.sublist.keys():
            self.sublist[i] = bSelect
        for i in self.espmlist.keys():
            self.espmlist[i] = bSelect
    def KeywordSelectEspm(self, line): self._SelectEspm(line, True, 'SelectEspm')
    def KeywordDeSelectEspm(self, line): self._SelectEspm(line, False, 'DeSelectEspm')
    def _SelectEspm(self, line, bSelect, name):
        if len(line) < 1:
            self.error("Missing arguments to '" + name + "'")
        if len(line) > 1:
            self.error("Extra arguments to '" + name + "'")
        espm = self.GetEspm(line[0])
        if espm:
            self.espmlist[espm] = bSelect
        else:
            self.error("Espm '" + line[0] + "' is not part of the installer.")
    def KeywordSelectAllEspms(self, line): self._SelectAllEspms(line, True, 'SelectAllEspms')
    def KeywordDeSelectAllEspms(self, line): self._SelectAllEspms(line, False, 'DeSelectAllEspms')
    def _SelectAllEspms(self, line, bSelect, name):
        if len(line) > 0:
            self.error("Extra arguments to '" + name + "'")
        for i in self.espmlist.keys():
            self.espmlist[i] = bSelect
            
    def KeywordNote(self, line):
        if len(line) > 0:
            self.notes.append('- ' + ' '.join(line) + '\n')
    def KeywordRequireVersions(self, line):
        if self.bAuto: return
        if len(line) < 1:
            self.error("Missing arguements to 'RequireVersions'")
        if len(line) > 3:
            self.error("Extra arguments to 'RequireVersions'")
        if len(line) < 2:
            line.append('None')
        if len(line) < 3:
            line.append('None')
        obWant = self._TestVersion_Want(line[0])
        if obWant == 'None':
            line[0] = 'None'
        obseWant = self._TestVersion_Want(line[1])
        if obseWant == 'None':
            line[1] = 'None'
        obgeWant = self._TestVersion_Want(line[2])
        if obgeWant == 'None':
            line[2] = 'None'
        ret = self._TestVersion(obWant, bosh.dirs['app'].join('oblivion.exe'))
        bObOk = ret[0] >= 0
        obHave = ret[1]
        ret = self._TestVersion(obseWant, bosh.dirs['app'].join('obse_loader.exe'))
        bOBSEOk = ret[0] >= 0
        obseHave = ret[1]
        ret = self._TestVersion(obgeWant, bosh.dirs['mods'].join('obse', 'plugins', 'obge.dll'))
        bOBGEOk = ret[0] >= 0
        obgeHave = ret[1]
        if not bObOk or not bOBSEOk or not bOBGEOk:
            self.page = PageVersions(self.parent, bObOk, obHave, line[0], bOBSEOk, obseHave, line[1], bOBGEOk, obgeHave, line[2])
    def _TestVersion_Want(self, want):
        try:
            need = [int(i) for i in want.split('.')]
        except:
            need = 'None'
        return need
    def _TestVersion(self, need, file):
        if file.exists():
            info = win32api.GetFileVersionInfo(file.s, '\\')
            ms = info['FileVersionMS']
            ls = info['FileVersionLS']
            have = win32api.HIWORD(ms), win32api.LOWORD(ms), win32api.HIWORD(ls), win32api.LOWORD(ls)
            ver = '.'.join([str(i) for i in have])
            if need == 'None':
                return [1, ver]
            if len(need) != 4:
                self.error("Version '" + want + "' expected in format 'x.x.x.x'")
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
        elif need == 'None':
            return [0, 'None']
        return [-1, 'None']
    def KeywordReturn(self, line):
        self.page = PageFinish(self.parent, self.sublist, self.espmlist, self.bAuto, self.notes)
    def KeywordCancel(self, line):
        if len(line) < 1:
            msg = "No reason given"
        else:
            msg = ' '.join(line)
        self.page = PageError(self.parent, 'The installer wizard was canceled:', msg)
# END --------------------------------------------------------------------------------------------------
