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

import re
import string
from collections import OrderedDict

import wx
from .. import bass, balt, bosh, bolt, load_order
from ..balt import bell, Link, BaltFrame, Resources, HtmlCtrl, set_event_hook
from ..bolt import GPath
from ..bosh import omods
from ..gui import Button, CancelButton, CENTER, CheckBox, GridLayout, \
    HLayout, Label, LayoutOptions, SaveButton, Spacer, Stretch, TextArea, \
    TextField, ToggleButton, VLayout

class DocBrowser(BaltFrame):
    """Doc Browser frame."""
    _frame_settings_key = 'bash.modDocs'
    _def_size = (300, 400)

    def __init__(self):
        # Data
        self._mod_name = GPath(u'')
        self._db_doc_paths = bosh.modInfos.table.getColumn('doc')
        self._db_is_editing = bosh.modInfos.table.getColumn('docEdit')
        self._doc_is_wtxt = False
        # Clean data
        for mod_name, doc in self._db_doc_paths.items():
            if not isinstance(doc, bolt.Path):
                self._db_doc_paths[mod_name] = GPath(doc)
        # Singleton
        Link.Frame.docBrowser = self
        # Window
        super(DocBrowser, self).__init__(Link.Frame, title=_(u'Doc Browser'))
        # Base UI components
        root_window = balt.Splitter(self)
        mod_list_window = wx.Panel(root_window)
        main_window = wx.Panel(root_window)
        # Mod Name
        self._mod_name_box = TextField(mod_list_window, editable=False)
        self._mod_list = balt.listBox(mod_list_window,
                                      choices=sorted(x.s for x in self._db_doc_paths.keys()),
                                      isSort=True,
                                      onSelect=self._do_select_mod)
        # Buttons
        self._set_btn = Button(main_window, _(u'Set Doc...'))
        self._set_btn.on_clicked.subscribe(self._do_set)
        self._forget_btn = Button(main_window, _(u'Forget Doc...'))
        self._forget_btn.on_clicked.subscribe(self._do_forget)
        self._rename_btn = Button(main_window, _(u'Rename Doc...'))
        self._rename_btn.on_clicked.subscribe(self._do_rename)
        self._edit_btn = ToggleButton(main_window, _(u'Edit Doc...'),
                                      on_toggle=self._do_edit)
        self._open_btn = Button(main_window, _(u'Open Doc...'),
                                tooltip=_(u'Open doc in external editor.'))
        self._open_btn.on_clicked.subscribe(self._do_open)
        self._doc_name_box = TextField(main_window, editable=False)
        self._doc_ctrl = HtmlCtrl(main_window)
        self._prev_btn, self._next_btn = self._doc_ctrl.get_buttons()
        self._buttons = [self._set_btn, self._forget_btn, self._rename_btn,
                         self._edit_btn, self._open_btn,
                         self._prev_btn, self._next_btn]
        #--Mod list
        VLayout(spacing=4, default_fill=True, items=[
            self._mod_name_box, (self._mod_list, LayoutOptions(weight=1))
        ]).apply_to(mod_list_window)
        #--Text field and buttons
        VLayout(spacing=4, default_fill=True, items=[
            HLayout(default_fill=True, items=self._buttons),
            self._doc_name_box,
            (self._doc_ctrl.web_viewer, LayoutOptions(weight=3))
        ]).apply_to(main_window)
        root_window.SplitVertically(mod_list_window, main_window, 250)
        VLayout(default_fill=1, default_border=4, default_weight=1,
                items=[root_window])
        for btn in self._buttons:
            # TODO(inf) de-wx! Wrap bitmapButton and drop this check
            if isinstance(btn, Button) or isinstance(btn, ToggleButton):
                btn.enabled = False
            else:
                btn.Disable()

    @staticmethod
    def _resources(): return Resources.bashDocBrowser

    @staticmethod
    def _get_is_wtxt(path=None, data=None):
        """Determines whether specified path is a wtxt file."""
        rx = re.compile(u'' r'^=.+=#\s*$', re.U)
        if path is not None:
            try:
                with path.open('r', encoding='utf-8-sig') as text_file:
                    match_text = rx.match(text_file.readline())
                return match_text is not None
            except (OSError, UnicodeDecodeError):
                return False
        else:
            return rx.match(data) is not None

    def _do_open(self):
        """Handle "Open Doc" button."""
        doc_path = self._db_doc_paths.get(self._mod_name)
        if not doc_path:
            return bell()
        if not doc_path.isfile():
            balt.showWarning(self, _(u'The assigned document is not present:')
                             + '\n  ' + doc_path.s)
        else:
            doc_path.start()

    def _do_edit(self, is_editing):
        """Handle "Edit Doc" button click."""
        self.DoSave()
        self._db_is_editing[self._mod_name] = is_editing
        self._doc_ctrl.set_text_editable(is_editing)
        self._load_data(path=self._db_doc_paths.get(self._mod_name),
                        editing=is_editing)

    def _do_forget(self):
        """Handle "Forget Doc" button click.
        Sets help document for current mod name to None."""
        if self._mod_name not in self._db_doc_paths:
            return
        index = self._mod_list.FindString(self._mod_name.s)
        if index != balt.notFound:
            self._mod_list.Delete(index)
        del self._db_doc_paths[self._mod_name]
        self.DoSave()
        for btn in (self._edit_btn, self._forget_btn, self._rename_btn,
                    self._open_btn):
            btn.enabled = False
        self._doc_name_box.text_content = u''
        self._load_data(data=u'')

    def _do_select_mod(self, event):
        """Handle mod name combobox selection."""
        self.SetMod(event.GetString())

    def _do_set(self):
        """Handle "Set Doc" button click."""
        #--Already have mod data?
        mod_name = self._mod_name
        if mod_name in self._db_doc_paths:
            (docs_dir, file_name) = self._db_doc_paths[mod_name].headTail
        else:
            docs_dir = bass.settings['bash.modDocs.dir'] or bass.dirs['mods']
            file_name = GPath(u'')
        doc_path = balt.askOpen(self ,_(u'Select doc for %s:') % mod_name.s,
                                docs_dir, file_name, u'*.*')
        if not doc_path: return
        bass.settings['bash.modDocs.dir'] = doc_path.head
        if mod_name not in self._db_doc_paths:
            self._mod_list.Append(mod_name.s)
        self._db_doc_paths[mod_name] = doc_path
        self.SetMod(mod_name)

    def _do_rename(self):
        """Handle "Rename Doc" button click."""
        old_path = self._db_doc_paths[self._mod_name]
        (work_dir,file_name) = old_path.headTail
        #--Dialog
        dest_path = balt.askSave(self, _(u'Rename file to:'), work_dir,
                                 file_name, u'*.*')
        if not dest_path or dest_path == old_path: return
        #--OS renaming
        dest_path.remove()
        old_path.moveTo(dest_path)
        if self._doc_is_wtxt:
            old_html, new_html = (x.root+u'.html' for x in (old_path,dest_path))
            if old_html.exists(): old_html.moveTo(new_html)
            else: new_html.remove()
        #--Remember change
        self._db_doc_paths[self._mod_name] = dest_path
        self._doc_name_box.text_content = dest_path.stail

    def DoSave(self):
        """Saves doc, if necessary."""
        if not self._doc_ctrl.is_text_modified(): return
        doc_path = self._db_doc_paths.get(self._mod_name)
        if not doc_path: return  # nothing to save if no file is loaded
        self._doc_ctrl.set_text_modified(False)
        with doc_path.open('w', encoding='utf-8-sig') as out:
            out.write(self._doc_ctrl.fallback_text)
        if self._doc_is_wtxt:
            bolt.WryeText.genHtml(doc_path, None,
                                  bosh.modInfos.store_dir.join(u'Docs'))

    def _load_data(self, path=None, data=None, editing=False):
        if path and path.cext in (u'.htm',u'.html',u'.mht') and not editing \
                and self._doc_ctrl.html_lib_available():
            self._doc_ctrl.try_load_html(path)
        else:
            # Oddly, wxPython's LoadFile function doesn't read unicode
            # correctly, even in unicode builds
            if data is None:
                try:
                    with path.open('r',encoding='utf-8-sig') as ins:
                        data = ins.read()
                except UnicodeDecodeError:
                    with path.open('r') as ins:
                        data = ins.read()
            self._doc_ctrl.load_text(data)

    def SetMod(self, mod_name):
        """Sets the mod to show docs for."""
        self.DoSave()
        # defaults
        self._edit_btn.toggled = False
        self._doc_ctrl.set_text_editable(False)
        mod_name = GPath(mod_name)
        self._mod_name = mod_name
        self._mod_name_box.text_content = mod_name.s
        if not mod_name:
            self._load_data(data=u'')
            for btn in self._buttons:
                btn.enabled = False
            return
        self._set_btn.enabled = True
        self._mod_list.SetSelection(self._mod_list.FindString(mod_name.s))
        # Doc path
        doc_path = self._db_doc_paths.get(mod_name, GPath(u''))
        self._doc_name_box.text_content = doc_path.stail
        for btn in (self._forget_btn, self._rename_btn, self._edit_btn,
                    self._open_btn):
            btn.enabled = bool(doc_path)
        # Set empty and uneditable if there's no doc path:
        if not doc_path:
            self._load_data(data=u'')
        # Create new file if none exists
        elif not doc_path.exists():
            for template_file in (bosh.modInfos.store_dir.join(
                    u'Docs', u'{} Readme Template'.format(fname))
                                  for fname in (u'My', u'Bash')):
                if template_file.exists():
                    template = u''.join(template_file.open().readlines())
                    break
            else:
                template = u'= $modName {}#\n{}'.format(u'=' * (74-len(mod_name)),
                                                        doc_path.s)
            self._load_data(data=string.Template(template)
                                            .substitute(modName=mod_name.s))
            # Start edit mode
            self._edit_btn.toggled = True
            self._doc_ctrl.set_text_editable(True)
            self._doc_ctrl.set_text_modified(True)
            # Save the new file
            self.DoSave()
        else:  # Otherwise it exists
            editing = self._db_is_editing.get(mod_name, False)
            if editing:
                self._edit_btn.toggled = True
                self._doc_ctrl.set_text_editable(True)
            else:
                is_wtxt = self._get_is_wtxt(doc_path)
                if is_wtxt:  # Update generated html
                    html_path = doc_path.root + u'.html'
                    if not html_path.exists() or (doc_path.mtime > html_path.mtime):
                        bolt.WryeText.genHtml(doc_path, None,
                                              bosh.modInfos.store_dir.join(u'Docs'))
            self._load_data(path=doc_path, editing=editing)

    def OnCloseWindow(self):
        """Handle window close event.
        Remember window size, position, etc."""
        self.DoSave()
        bass.settings['bash.modDocs.show'] = False
        Link.Frame.docBrowser = None
        super(DocBrowser, self).OnCloseWindow()

#------------------------------------------------------------------------------
_BACK, _FORWARD, _MOD_LIST, _RULE_SETS, _NOTES, _CONFIG, _SUGGEST, \
_CRC, _VERSION, _SCAN_DIRTY, _COPY_TEXT, _UPDATE = range(12)

def _get_mod_checker_setting(key, default=None):
    return bass.settings.get('bash.modChecker.show{}'.format(key), default)

def _set_mod_checker_setting(key, value):
    bass.settings['bash.modChecker.show{}'.format(key)] = value

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
        self.__merged = None
        self.__imported = None
        #--Text
        self.check_mods_text = None
        self._html_ctrl = HtmlCtrl(self)
        back_button, forward_button = self._html_ctrl.get_buttons()
        self._buttons = OrderedDict()
        self._setting_names = {}
        def _f(key, type_, caption, setting_key=None, setting_value=None,
               callback=self.CheckMods):
            if type_ == 'toggle':
                btn = ToggleButton(self, caption, on_toggle=callback)
            elif type_ == 'check':
                btn = CheckBox(self, caption, on_toggle=callback)
            else: # type_ == 'click'
                btn = Button(self, caption)
                btn.on_clicked.subscribe(callback)
            if setting_key is not None:
                new_value = bass.settings.get(
                    'bash.modChecker.show{}'.format(setting_key), setting_value)
                if type_ == 'toggle':
                    btn.toggled = new_value
                elif type_ == 'check':
                    btn.checked = new_value
                self._setting_names[key] = setting_key
            self._buttons[key] = btn
        _f(_MOD_LIST,   'toggle', _(u'Mod List'), 'ModList', False)
        _f(_VERSION,    'check',  _(u'Version Numbers'), 'Version', True)
        _f(_CRC,        'check',  _(u'CRCs'),            'CRC', False)
        _f(_RULE_SETS,  'toggle', _(u'Rule Sets'),       'RuleSets', False)
        _f(_NOTES,      'check',  _(u'Notes'),           'Notes', True)
        _f(_CONFIG,     'check',  _(u'Configuration'),   'Config', True)
        _f(_SUGGEST,    'check',  _(u'Suggestions'),     'Suggest', True)
        _f(_SCAN_DIRTY, 'toggle', (_(u'Scan for Dirty Edits')
                                   if bass.settings['bash.CBashEnabled']
                                   else _(u"Scan for UDR's")))
        _f(_COPY_TEXT,  'click',  _(u'Copy Text'), callback=self.OnCopyText)
        _f(_UPDATE,     'click',  _(u'Update'))
        #--Events
        set_event_hook(self, balt.Events.ACTIVATE, self.OnActivate)
        VLayout(border=4, spacing=4, default_fill=True, items=[
            (self._html_ctrl.web_viewer, LayoutOptions(weight=1)),
            HLayout(spacing=4, items=[
                self._buttons[_MOD_LIST], self._buttons[_CRC],
                self._buttons[_VERSION]
            ]),
            HLayout(spacing=4, items=[
                self._buttons[_RULE_SETS], self._buttons[_NOTES],
                self._buttons[_CONFIG], self._buttons[_SUGGEST]
            ]),
            HLayout(spacing=4, items=[
                self._buttons[_SCAN_DIRTY], Stretch(), self._buttons[_UPDATE],
                self._buttons[_COPY_TEXT], back_button, forward_button
            ])
        ]).apply_to(self)
        self.CheckMods()

    def OnCopyText(self):
        """Copies text of report to clipboard."""
        text_ = u'[spoiler]\n' + self.check_mods_text + u'[/spoiler]'
        text_ = re.sub(u'' r'\[\[.+?\|\s*(.+?)\]\]', u'' r'\1', text_, re.U)
        text_ = re.sub(u'(__|\*\*|~~)', u'', text_, re.U)
        text_ = re.sub(u'&bull; &bull;', u'**', text_, re.U)
        text_ = re.sub(u'<[^>]+>', u'', text_, re.U)
        balt.copyToClipboard(text_)

    def CheckMods(self, _new_value=None):
        """Do mod check."""
        for btn_id in [_MOD_LIST, _RULE_SETS]:
            _set_mod_checker_setting(self._setting_names[btn_id],
                                     self._buttons[btn_id].checked)
        # Enable or disable the children of ModList and RuleSets buttons
        for parent, btn_ids in [(_MOD_LIST, (_CRC, _VERSION)),
                                (_RULE_SETS, (_NOTES, _CONFIG, _SUGGEST))]:
            key = self._setting_names[parent]
            for btn_id in btn_ids:
                self._buttons[btn_id].Enable(_get_mod_checker_setting(key))
        # Set settings from all the buttons' values
        for btn_id in [_NOTES, _CONFIG, _SUGGEST, _CRC, _VERSION]:
            _set_mod_checker_setting(self._setting_names[btn_id],
                                     self._buttons[btn_id].checked)
        #--Cache info from modinfos to support auto-update.
        self.orderedActive = load_order.cached_active_tuple()
        self.__merged = bosh.modInfos.merged.copy()
        self.__imported = bosh.modInfos.imported.copy()
        #--Do it
        self.check_mods_text = bosh.configHelpers.checkMods(
            *[_get_mod_checker_setting(self._setting_names[key])
              for key in [_MOD_LIST, _RULE_SETS, _NOTES, _CONFIG, _SUGGEST,
                          _CRC, _VERSION]],
            mod_checker=(None, self)[self._buttons[_SCAN_DIRTY].checked])
        if HtmlCtrl.html_lib_available():
            log_path = bass.dirs['saveBase'].join(u'ModChecker.html')
            balt.convert_wtext_to_html(log_path, self.check_mods_text)
            self._html_ctrl.try_load_html(log_path)
        else:
            self._html_ctrl.load_text(self.check_mods_text)

    def OnActivate(self,event):
        """Handle window activate/deactivate. Use for auto-updating list."""
        if (event.GetActive() and (
                self.orderedActive != load_order.cached_active_tuple() or
                self.__merged != bosh.modInfos.merged or
                self.__imported != bosh.modInfos.imported)
            ):
            self.CheckMods()

    def OnCloseWindow(self):
        # Need to unset Link.Frame.modChecker here to avoid accessing a deleted
        # object when clicking the mod checker button again.
        Link.Frame.modChecker = None
        super(ModChecker, self).OnCloseWindow()

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
        self.gName = TextField(self, text=config.name, max_length=100)
        self.gVersion = TextField(self, u'{:d}.{:02d}'.format(
            config.vMajor, config.vMinor), max_length=32)
        self.gWebsite = TextField(self, config.website, max_length=512)
        self.gAuthor = TextField(self, config.author, max_length=512)
        self.gEmail = TextField(self, text=config.email, max_length=512)
        self.gAbstract = TextArea(self, text=config.abstract,
                                  max_length=4 * 1024)
        #--Layout
        def _no_fill_text(txt):
            return Label(self, txt), LayoutOptions(fill=False)
        save_button = SaveButton(self, default=True)
        save_button.on_clicked.subscribe(self.DoSave)
        cancel_button = CancelButton(self)
        cancel_button.on_clicked.subscribe(self.OnCloseWindow)
        VLayout(default_fill=True, spacing=4, border=4, items=[
            GridLayout(h_spacing=4, v_spacing=4, default_v_align=CENTER,
                       stretch_cols=[1], default_fill=True, items=[
                (_no_fill_text(_(u'Name:')), self.gName),
                (_no_fill_text(_(u'Version:')), self.gVersion),
                (_no_fill_text(_(u'Website:')), self.gWebsite),
                (_no_fill_text(_(u'Author:')), self.gAuthor),
                (_no_fill_text(_(u'Email:')), self.gEmail)]),
            Spacer(10),
            _no_fill_text(_(u'Abstract')),
            (self.gAbstract, LayoutOptions(weight=1)),
            HLayout(spacing=4, items=[save_button, cancel_button])
        ]).apply_to(self)
        self.SetSize((350,400))

    def DoSave(self):
        """Handle save button."""
        config = self.config
        #--Text fields
        config.name = self.gName.text_content.strip()
        config.website = self.gWebsite.text_content.strip()
        config.author = self.gAuthor.text_content.strip()
        config.email = self.gEmail.text_content.strip()
        config.abstract = self.gAbstract.text_content.strip()
        #--Version
        maVersion = re.match(u'' r'(\d+)\.(\d+)',
                             self.gVersion.text_content.strip(), flags=re.U)
        if maVersion:
            config.vMajor,config.vMinor = map(int,maVersion.groups())
        else:
            config.vMajor,config.vMinor = (0,0)
        #--Done
        omods.OmodConfig.writeOmodConfig(self.project, self.config)
        self.OnCloseWindow()
