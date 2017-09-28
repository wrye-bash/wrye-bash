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
#  Wrye Bash copyright (C) 2005-2009 Wrye, 2010-2015 Wrye Bash Team
#  https://github.com/wrye-bash
#
# =============================================================================

import re
import string
import wx
from .. import bass, balt, bosh, bolt, load_order
from ..balt import TextCtrl, StaticText, vSizer, hSizer, hspacer, Button, \
    RoTextCtrl, bell, Link, toggleButton, SaveButton, CancelButton, hspace, \
    vspace, BaltFrame, Resources, HtmlCtrl
from ..bolt import GPath
from ..bosh import omods
from ..exception import BoltError

class DocBrowser(BaltFrame):
    """Doc Browser frame."""
    _frame_settings_key = 'bash.modDocs'
    _def_size = (300, 400)

    def __init__(self, modName=None):
        """Initialize.
        modName -- current modname (or None)."""
        #--Data
        self.modName = GPath(modName or u'')
        self.docs = bosh.modInfos.table.getColumn('doc')
        self.docEdit = bosh.modInfos.table.getColumn('docEdit')
        self.docType = None
        self.docIsWtxt = False
        #--Clean data
        for key,doc in self.docs.items():
            if not isinstance(doc,bolt.Path):
                self.docs[key] = GPath(doc)
        #--Singleton
        Link.Frame.docBrowser = self
        #--Window
        super(DocBrowser, self).__init__(Link.Frame, title=_(u'Doc Browser'))
        #--Mod Name
        self.modNameBox = RoTextCtrl(self, multiline=False)
        self.modNameList = balt.listBox(self,
            choices=sorted(x.s for x in self.docs.keys()), isSort=True,
            onSelect=self.DoSelectMod)
        #--Set Doc
        self.setButton = Button(self, _(u'Set Doc...'), onButClick=self.DoSet)
        #--Forget Doc
        self.forgetButton = Button(self, _(u'Forget Doc...'),
                                   onButClick=self.DoForget)
        #--Rename Doc
        self.renameButton = Button(self, _(u'Rename Doc...'),
                                   onButClick=self.DoRename)
        #--Edit Doc
        self.editButton = toggleButton(self, label=_(u'Edit Doc...'),
                                       onClickToggle=self.DoEdit)
        self.openButton = Button(self, _(u'Open Doc...'),
                                 onButClick=self.DoOpen,
                                 button_tip=_(u'Open doc in external editor.'))
        #--Doc Name
        self.docNameBox = RoTextCtrl(self, multiline=False)
        #--Doc display
        self.plainText = RoTextCtrl(self, special=True, autotooltip=False)
        if HtmlCtrl.html_lib_available():
            html_ctrl = HtmlCtrl(self)
            self.htmlText = html_ctrl.text_ctrl
            self.prevButton = html_ctrl.prevButton
            self.nextButton = html_ctrl.nextButton
        else:
            self.htmlText = None
            self.prevButton = None
            self.nextButton = None
        #--Layout
        self.mainSizer = vSizer(
            (hSizer( #--Buttons
                (self.setButton,0,wx.GROW),
                (self.forgetButton,0,wx.GROW),
                (self.renameButton,0,wx.GROW),
                (self.editButton,0,wx.GROW),
                (self.openButton,0,wx.GROW),
                (self.prevButton,0,wx.GROW),
                (self.nextButton,0,wx.GROW),
                ),0,wx.GROW|wx.ALL^wx.BOTTOM,4),
            (hSizer( #--Mod name, doc name
                #(self.modNameBox,2,wx.GROW|wx.RIGHT,4),
                (self.docNameBox,2,wx.GROW),
                ),0,wx.GROW|wx.TOP|wx.BOTTOM,4),
            (self.plainText,3,wx.GROW),
            (self.htmlText,3,wx.GROW),
            )
        sizer = hSizer(
            (vSizer(
                (self.modNameBox,0,wx.GROW),
                vspace(), (self.modNameList,1,wx.GROW),
                ),0,wx.GROW|wx.TOP|wx.RIGHT,4),
            (self.mainSizer,1,wx.GROW),
            )
        #--Set
        self.SetSizer(sizer)
        self.SetMod(modName)
        self.SetDocType('txt')

    @staticmethod
    def _resources(): return Resources.bashDocBrowser

    def GetIsWtxt(self,docPath=None):
        """Determines whether specified path is a wtxt file."""
        docPath = docPath or GPath(self.docs.get(self.modName,u''))
        if not docPath.exists():
            return False
        try:
            with docPath.open('r',encoding='utf-8-sig') as textFile:
                maText = re.match(ur'^=.+=#\s*$',textFile.readline(),re.U)
            return maText is not None
        except UnicodeDecodeError:
            return False

    def DoOpen(self):
        """Handle "Open Doc" button."""
        docPath = self.docs.get(self.modName)
        if not docPath:
            return bell()
        if not docPath.isfile():
            balt.showWarning(self, _(u'The assigned document is not present:')
                             + '\n  ' + docPath.s)
        else:
            docPath.start()

    def DoEdit(self):
        """Handle "Edit Doc" button click."""
        self.DoSave()
        editing = self.editButton.GetValue()
        self.docEdit[self.modName] = editing
        self.docIsWtxt = self.GetIsWtxt()
        if self.docIsWtxt:
            self.SetMod(self.modName)
        else:
            self.plainText.SetEditable(editing)

    def DoForget(self):
        """Handle "Forget Doc" button click.
        Sets help document for current mod name to None."""
        #--Already have mod data?
        modName = self.modName
        if modName not in self.docs:
            return
        index = self.modNameList.FindString(modName.s)
        if index != wx.NOT_FOUND:
            self.modNameList.Delete(index)
        del self.docs[modName]
        self.SetMod(modName)

    def DoSelectMod(self,event):
        """Handle mod name combobox selection."""
        self.SetMod(event.GetString())

    def DoSet(self):
        """Handle "Set Doc" button click."""
        #--Already have mod data?
        modName = self.modName
        if modName in self.docs:
            (docsDir,fileName) = self.docs[modName].headTail
        else:
            docsDir = bass.settings['bash.modDocs.dir'] or bass.dirs['mods']
            fileName = GPath(u'')
        #--Dialog
        doc_path = balt.askOpen(self,_(u'Select doc for %s:') % modName.s,
            docsDir,fileName, u'*.*',mustExist=True)
        if not doc_path: return
        bass.settings['bash.modDocs.dir'] = doc_path.head
        if modName not in self.docs:
            self.modNameList.Append(modName.s)
        self.docs[modName] = doc_path
        self.SetMod(modName)

    def DoRename(self):
        """Handle "Rename Doc" button click."""
        modName = self.modName
        oldPath = self.docs[modName]
        (workDir,fileName) = oldPath.headTail
        #--Dialog
        dest_path = balt.askSave(self, _(u'Rename file to:'), workDir,
                                 fileName, u'*.*')
        if not dest_path or dest_path == oldPath: return
        #--OS renaming
        dest_path.remove()
        oldPath.moveTo(dest_path)
        if self.docIsWtxt:
            oldHtml, newHtml = (x.root+u'.html' for x in (oldPath,dest_path))
            if oldHtml.exists(): oldHtml.moveTo(newHtml)
            else: newHtml.remove()
        #--Remember change
        self.docs[modName] = dest_path
        self.SetMod(modName)

    def DoSave(self):
        """Saves doc, if necessary."""
        if not self.plainText.IsModified(): return
        docPath = self.docs.get(self.modName)
        self.plainText.DiscardEdits()
        if not docPath:
            raise BoltError(_(u'Filename not defined.'))
        with docPath.open('w',encoding='utf-8-sig') as out:
            out.write(self.plainText.GetValue())
        if self.docIsWtxt:
            docsDir = bosh.modInfos.store_dir.join(u'Docs')
            bolt.WryeText.genHtml(docPath, None, docsDir)

    def SetMod(self,modName=None):
        """Sets the mod to show docs for."""
        #--Save Current Edits
        self.DoSave()
        #--New modName
        self.modName = modName = GPath(modName or u'')
        #--ModName
        if modName:
            self.modNameBox.SetValue(modName.s)
            index = self.modNameList.FindString(modName.s)
            self.modNameList.SetSelection(index)
            self.setButton.Enable(True)
        else:
            self.modNameBox.SetValue(u'')
            self.modNameList.SetSelection(wx.NOT_FOUND)
            self.setButton.Enable(False)
        #--Doc Data
        docPath = self.docs.get(modName) or GPath(u'')
        docExt = docPath.cext
        self.docNameBox.SetValue(docPath.stail)
        self.forgetButton.Enable(docPath != u'')
        self.renameButton.Enable(docPath != u'')
        #--Edit defaults to false.
        self.editButton.SetValue(False)
        self.editButton.Enable(False)
        self.openButton.Enable(False)
        self.plainText.SetEditable(False)
        self.docIsWtxt = False
        #--View/edit doc.
        if not docPath:
            self.plainText.SetValue(u'')
            self.SetDocType('txt')
        elif not docPath.exists():
            myTemplate = bosh.modInfos.store_dir.join(u'Docs',
                                                u'My Readme Template.txt')
            bashTemplate = bosh.modInfos.store_dir.join(u'Docs',
                                                  u'Bash Readme Template.txt')
            if myTemplate.exists():
                template = u''.join(myTemplate.open().readlines())
            elif bashTemplate.exists():
                template = u''.join(bashTemplate.open().readlines())
            else:
                template = u'= $modName ' + (
                    u'=' * (74 - len(modName))) + u'#\n' + docPath.s
            defaultText = string.Template(template).substitute(
                modName=modName.s)
            self.plainText.SetValue(defaultText)
            self.SetDocType('txt')
            if docExt in (u'.txt',u'.etxt'):
                self.editButton.Enable(True)
                self.openButton.Enable(True)
                editing = self.docEdit.get(modName,True)
                self.editButton.SetValue(editing)
                self.plainText.SetEditable(editing)
            self.docIsWtxt = (docExt == u'.txt')
        elif docExt in (u'.htm',u'.html',u'.mht') and self.htmlText:
            self.htmlText.Navigate(docPath.s,0x2) #--0x2: Clear History
            self.SetDocType('html')
        else:
            self.editButton.Enable(True)
            self.openButton.Enable(True)
            editing = self.docEdit.get(modName,False)
            self.editButton.SetValue(editing)
            self.plainText.SetEditable(editing)
            self.docIsWtxt = self.GetIsWtxt(docPath)
            htmlPath = self.docIsWtxt and docPath.root + u'.html'
            if htmlPath and (
                not htmlPath.exists() or (docPath.mtime > htmlPath.mtime)):
                docsDir = bosh.modInfos.store_dir.join(u'Docs')
                bolt.WryeText.genHtml(docPath,None,docsDir)
            if not editing and htmlPath and htmlPath.exists() \
                    and self.htmlText:
                self.htmlText.Navigate(htmlPath.s,0x2) #--0x2: Clear History
                self.SetDocType('html')
            else:
                # Oddly, wxPython's LoadFile function doesn't read unicode
                # correctly, even in unicode builds
                try:
                    with docPath.open('r',encoding='utf-8-sig') as ins:
                        data = ins.read()
                except UnicodeDecodeError:
                    with docPath.open('r') as ins:
                        data = ins.read()
                self.plainText.SetValue(data)
                self.SetDocType('txt')

    #--Set Doc Type
    def SetDocType(self,docType):
        """Shows the plainText or htmlText view depending on document type (
        i.e. file name extension)."""
        if docType == self.docType:
            return
        sizer = self.mainSizer
        html_doc = docType == 'html'
        # show plain text if it's not an html doc or the html control is None
        sizer.Show(self.plainText, not html_doc or not self.htmlText)
        if self.htmlText: #if the html control is not None show it for html doc
            sizer.Show(self.htmlText, html_doc)
            self.prevButton.Enable(html_doc)
            self.nextButton.Enable(html_doc)
        self.Layout()

    #--Window Closing
    def OnCloseWindow(self):
        """Handle window close event.
        Remember window size, position, etc."""
        self.DoSave()
        bass.settings['bash.modDocs.show'] = False
        Link.Frame.docBrowser = None
        super(DocBrowser, self).OnCloseWindow()

#------------------------------------------------------------------------------
class ModChecker(BaltFrame):
    """Mod Checker frame."""
    _frame_settings_key = 'bash.modChecker'
    _def_size = (475, 500)

    def __init__(self):
        #--Singleton
        Link.Frame.modChecker = self
        #--Window
        super(ModChecker, self).__init__(Link.Frame, title=_(u'Mod Checker'))
        #--Data
        self.orderedActive = None
        self.merged = None
        self.imported = None
        #--Text
        self._html_ctrl = HtmlCtrl(self)
        self.gTextCtrl = self._html_ctrl.text_ctrl
        gBackButton = self._html_ctrl.prevButton # may be None
        gForwardButton = self._html_ctrl.nextButton # may be None
        gUpdateButton = Button(self, _(u'Update'), onButClick=self.CheckMods)
        def _toggle_button(caption):
            return toggleButton(self, caption, onClickToggle=self.CheckMods)
        self.gShowModList = _toggle_button( _(u'Mod List'))
        self.gShowRuleSets = _toggle_button(_(u'Rule Sets'))
        self.gShowNotes = _toggle_button(_(u'Notes'))
        self.gShowConfig = _toggle_button(_(u'Configuration'))
        self.gShowSuggest = _toggle_button(_(u'Suggestions'))
        self.gShowCRC = _toggle_button(_(u'CRCs'))
        self.gShowVersion = _toggle_button(_(u'Version Numbers'))
        if bass.settings['bash.CBashEnabled']:
            self.gScanDirty = _toggle_button(_(u'Scan for Dirty Edits'))
        else:
            self.gScanDirty = _toggle_button(_(u"Scan for UDR's"))
        self.gCopyText = Button(self, _(u'Copy Text'),
                                onButClick=self.OnCopyText)
        self.gShowModList.SetValue(
            bass.settings.get('bash.modChecker.showModList', False))
        self.gShowNotes.SetValue(
            bass.settings.get('bash.modChecker.showNotes', True))
        self.gShowConfig.SetValue(
            bass.settings.get('bash.modChecker.showConfig', True))
        self.gShowSuggest.SetValue(
            bass.settings.get('bash.modChecker.showSuggest', True))
        self.gShowCRC.SetValue(
            bass.settings.get('bash.modChecker.showCRC', False))
        self.gShowVersion.SetValue(
            bass.settings.get('bash.modChecker.showVersion', True))
        #--Events
        self.Bind(wx.EVT_ACTIVATE, self.OnActivate)
        #--Layout
        self.SetSizer(
            vSizer(
                (self.gTextCtrl,1,wx.EXPAND|wx.ALL^wx.BOTTOM,2),
                (hSizer(
                    gBackButton,
                    gForwardButton,
                    hspace(), self.gShowModList,
                    hspace(), self.gShowRuleSets,
                    hspace(), self.gShowNotes,
                    hspace(), self.gShowConfig,
                    hspace(), self.gShowSuggest,
                    ),0,wx.ALL|wx.EXPAND,4),
                (hSizer(
                    hspace(), self.gShowVersion,
                    hspace(), self.gShowCRC,
                    hspace(), self.gScanDirty,
                    hspace(), self.gCopyText,
                    hspacer,
                    gUpdateButton,
                    ),0,wx.ALL|wx.EXPAND,4),
                )
            )
        self.CheckMods()

    def OnCopyText(self):
        """Copies text of report to clipboard."""
        text_ = u'[spoiler]\n' + self.check_mods_text + u'[/spoiler]'
        text_ = re.sub(ur'\[\[.+?\|\s*(.+?)\]\]', ur'\1', text_, re.U)
        text_ = re.sub(u'(__|\*\*|~~)', u'', text_, re.U)
        text_ = re.sub(u'&bull; &bull;', u'**', text_, re.U)
        text_ = re.sub(u'<[^>]+>', '', text_, re.U)
        balt.copyToClipboard(text_)

    def CheckMods(self):
        """Do mod check."""
        bass.settings[
            'bash.modChecker.showModList'] = self.gShowModList.GetValue()
        bass.settings[
            'bash.modChecker.showRuleSets'] = self.gShowRuleSets.GetValue()
        if not bass.settings['bash.modChecker.showRuleSets']:
            self.gShowNotes.SetValue(False)
            self.gShowConfig.SetValue(False)
            self.gShowSuggest.SetValue(False)
        bass.settings['bash.modChecker.showNotes'] = self.gShowNotes.GetValue()
        bass.settings[
            'bash.modChecker.showConfig'] = self.gShowConfig.GetValue()
        bass.settings[
            'bash.modChecker.showSuggest'] = self.gShowSuggest.GetValue()
        bass.settings['bash.modChecker.showCRC'] = self.gShowCRC.GetValue()
        bass.settings[
            'bash.modChecker.showVersion'] = self.gShowVersion.GetValue()
        #--Cache info from modinfos to support auto-update.
        self.orderedActive = load_order.cached_active_tuple()
        self.merged = bosh.modInfos.merged.copy()
        self.imported = bosh.modInfos.imported.copy()
        #--Do it
        self.check_mods_text = bosh.configHelpers.checkMods(
            bass.settings['bash.modChecker.showModList'],
            bass.settings['bash.modChecker.showRuleSets'],
            bass.settings['bash.modChecker.showNotes'],
            bass.settings['bash.modChecker.showConfig'],
            bass.settings['bash.modChecker.showSuggest'],
            bass.settings['bash.modChecker.showCRC'],
            bass.settings['bash.modChecker.showVersion'],
            mod_checker=(None, self)[self.gScanDirty.GetValue()]
            )
        if HtmlCtrl.html_lib_available():
            logPath = bass.dirs['saveBase'].join(u'ModChecker.html')
            balt.convert_wtext_to_html(logPath, self.check_mods_text)
            self.gTextCtrl.Navigate(logPath.s,0x2) #--0x2: Clear History
        else:
            self.gTextCtrl.SetValue(self.check_mods_text)

    def OnActivate(self,event):
        """Handle window activate/deactivate. Use for auto-updating list."""
        if (event.GetActive() and (
            self.orderedActive != load_order.cached_active_tuple() or
            self.merged != bosh.modInfos.merged or
            self.imported != bosh.modInfos.imported)
            ):
            self.CheckMods()

#------------------------------------------------------------------------------
class InstallerProject_OmodConfigDialog(BaltFrame):
    """Dialog for editing omod configuration data."""
    _size_hints = (300, 300)

    def __init__(self,parent,data,project):
        #--Data
        self.data = data
        self.project = project
        self.config = config = omods.OmodConfig.getOmodConfig(project)
        #--GUI
        super(InstallerProject_OmodConfigDialog, self).__init__(parent,
            title=_(u'Omod Config: ') + project.s,
            style=wx.RESIZE_BORDER | wx.CAPTION | wx.CLIP_CHILDREN |
                  wx.TAB_TRAVERSAL)
        #--Fields
        self.gName = TextCtrl(self, config.name, maxChars=100)
        self.gVersion = TextCtrl(self, u'%d.%02d' % (
            config.vMajor, config.vMinor), maxChars=32)
        self.gWebsite = TextCtrl(self, config.website, maxChars=512)
        self.gAuthor = TextCtrl(self, config.author, maxChars=512)
        self.gEmail = TextCtrl(self, config.email, maxChars=512)
        self.gAbstract = TextCtrl(self, config.abstract, multiline=True,
                                  maxChars=4 * 1024)
        #--Layout
        fgSizer = wx.FlexGridSizer(0,2,4,4)
        fgSizer.AddGrowableCol(1,1)
        fgSizer.AddMany([
            StaticText(self,_(u"Name:")), (self.gName,1,wx.EXPAND),
            StaticText(self,_(u"Version:")),(self.gVersion,1,wx.EXPAND),
            StaticText(self,_(u"Website:")),(self.gWebsite,1,wx.EXPAND),
            StaticText(self,_(u"Author:")),(self.gAuthor,1,wx.EXPAND),
            StaticText(self,_(u"Email:")),(self.gEmail,1,wx.EXPAND),
            ])
        sizer = vSizer(
            (fgSizer,0,wx.EXPAND|wx.ALL^wx.BOTTOM,4),
            (StaticText(self,_(u"Abstract")),0,wx.LEFT|wx.RIGHT,4),
            (self.gAbstract,1,wx.EXPAND|wx.ALL^wx.BOTTOM,4),
            (hSizer(
                hspacer, SaveButton(self, onButClick=self.DoSave,
                                    default=True),
                hspace(), CancelButton(self, onButClick=self.OnCloseWindow),
                ),0,wx.EXPAND|wx.ALL,4),
            )
        #--Done
        self.SetSizerAndFit(sizer)
        self.SetSizer(sizer)
        self.SetSize((350,400))

    def DoSave(self):
        """Handle save button."""
        config = self.config
        #--Text fields
        config.name = self.gName.GetValue().strip()
        config.website = self.gWebsite.GetValue().strip()
        config.author = self.gAuthor.GetValue().strip()
        config.email = self.gEmail.GetValue().strip()
        config.abstract = self.gAbstract.GetValue().strip()
        #--Version
        maVersion = re.match(ur'(\d+)\.(\d+)',
                             self.gVersion.GetValue().strip(), flags=re.U)
        if maVersion:
            config.vMajor,config.vMinor = map(int,maVersion.groups())
        else:
            config.vMajor,config.vMinor = (0,0)
        #--Done
        omods.OmodConfig.writeOmodConfig(self.project, self.config)
        self.OnCloseWindow()
