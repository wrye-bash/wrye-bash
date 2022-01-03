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

import re
import string
from collections import OrderedDict

from .. import bass, balt, bosh, bolt, load_order
from ..balt import Link, Resources
from ..bolt import GPath
from ..bosh import mods_metadata
from ..bosh import omods
from ..exception import StateError
from ..gui import Button, CancelButton, CheckBox, GridLayout, HLayout, Label, \
    LayoutOptions, SaveButton, Spacer, Stretch, TextArea, TextField, VLayout, \
    web_viewer_available, Splitter, WindowFrame, ListBox, DocumentViewer, \
    pdf_viewer_available, bell, copy_text_to_clipboard, FileOpen, FileSave

class DocBrowser(WindowFrame):
    """Doc Browser frame."""
    _frame_settings_key = u'bash.modDocs'
    _def_size = (300, 400)

    def __init__(self):
        # Data
        self._mod_name = GPath(u'')
        self._db_doc_paths = bosh.modInfos.table.getColumn(u'doc')
        self._db_is_editing = bosh.modInfos.table.getColumn(u'docEdit')
        self._doc_is_wtxt = False
        # Clean data
        for mod_name, doc in list(self._db_doc_paths.items()):
            if not isinstance(doc, bolt.Path):
                self._db_doc_paths[mod_name] = GPath(doc)
        # Singleton
        Link.Frame.docBrowser = self
        # Window
        super(DocBrowser, self).__init__(Link.Frame, title=_(u'Doc Browser'),
                                         icon_bundle=Resources.bashBlue,
                                         sizes_dict=bass.settings)
        # Base UI components
        root_window = Splitter(self)
        mod_list_window, main_window = root_window.make_panes(250,
                                                              vertically=True)
        # Mod Name
        self._mod_name_box = TextField(mod_list_window, editable=False)
        self._mod_list = ListBox(mod_list_window,
             choices=sorted(x.s for x in self._db_doc_paths),
             isSort=True, onSelect=self._do_select_mod)
        # Buttons
        self._set_btn = Button(main_window, _(u'Set Doc...'),
                               btn_tooltip=u'Associates this plugin file with '
                                           u'a document.')
        self._set_btn.on_clicked.subscribe(self._do_set)
        self._forget_btn = Button(main_window, _(u'Forget Doc'),
                                  btn_tooltip=_(u'Removes the link between '
                                                u'this plugin file and the '
                                                u'matching document.'))
        self._forget_btn.on_clicked.subscribe(self._do_forget)
        self._rename_btn = Button(main_window, _(u'Rename Doc...'),
                                  btn_tooltip=_(u'Renames the document.'))
        self._rename_btn.on_clicked.subscribe(self._do_rename)
        self._edit_box = CheckBox(main_window, _(u'Allow Editing'),
                                  chkbx_tooltip=_(u'Enables or disables '
                                                  u'editing in the text field '
                                                  u'below.'))
        self._edit_box.on_checked.subscribe(self._do_edit)
        self._open_btn = Button(main_window, _(u'Open Doc...'),
                                btn_tooltip=_(u'Opens the document in your '
                                              u'default viewer/editor.'))
        self._open_btn.on_clicked.subscribe(self._do_open)
        self._doc_name_box = TextField(main_window, editable=False)
        self._doc_ctrl = DocumentViewer(main_window)
        self._prev_btn, self._next_btn, self._reload_btn = \
            self._doc_ctrl.get_buttons()
        self._buttons = [self._edit_box, self._set_btn, self._forget_btn,
                         self._rename_btn, self._open_btn, self._prev_btn,
                         self._next_btn, self._reload_btn]
        #--Mod list
        VLayout(spacing=4, item_expand=True, items=[
            self._mod_name_box, (self._mod_list, LayoutOptions(weight=1)),
        ]).apply_to(mod_list_window)
        #--Text field and buttons
        VLayout(spacing=4, item_expand=True, items=[
            HLayout(item_expand=True, items=self._buttons),
            self._doc_name_box, (self._doc_ctrl, LayoutOptions(weight=3)),
        ]).apply_to(main_window)
        VLayout(item_expand=1, item_border=4, item_weight=1, items=[
            root_window,
        ]).apply_to(self)
        for btn in self._buttons:
            btn.enabled = False

    @staticmethod
    def _get_is_wtxt(doc_path):
        """Determines whether specified path is a wtxt file."""
        rx = re.compile(r'^=.+=#\s*$', re.U)
        try:
            with doc_path.open(u'r', encoding=u'utf-8-sig') as text_file:
                match_text = rx.match(text_file.readline())
            return match_text is not None
        except (OSError, UnicodeDecodeError):
            return False

    def _do_open(self):
        """Handle "Open Doc" button."""
        doc_path = self._db_doc_paths.get(self._mod_name)
        if not doc_path:
            return bell()
        if not doc_path.is_file():
            balt.showWarning(self, _('The assigned document is not '
                                     'present:') + f'\n  {doc_path}')
        else:
            doc_path.start()

    def _do_edit(self, is_editing):
        """Handle "Edit Doc" button click."""
        self.DoSave()
        self._db_is_editing[self._mod_name] = is_editing
        self._doc_ctrl.set_text_editable(is_editing)
        self._load_data(doc_path=self._db_doc_paths.get(self._mod_name),
                        editing=is_editing)

    def _do_forget(self):
        """Handle "Forget Doc" button click.
        Sets help document for current mod name to None."""
        if self._mod_name not in self._db_doc_paths:
            return
        index = self._mod_list.lb_index_for_str_item(self._mod_name.s)
        if index is not None:
            self._mod_list.lb_delete_at_index(index)
        del self._db_doc_paths[self._mod_name]
        self.DoSave()
        for btn in (self._edit_box, self._forget_btn, self._rename_btn,
                    self._open_btn):
            btn.enabled = False
        self._doc_name_box.text_content = u''
        self._load_data(uni_str=u'')

    def _do_select_mod(self, _lb_selection_dex, lb_selection_str):
        """Handle mod name combobox selection."""
        self.SetMod(lb_selection_str)

    def _do_set(self):
        """Handle "Set Doc" button click."""
        #--Already have mod data?
        mod_name = self._mod_name
        if mod_name in self._db_doc_paths:
            (docs_dir, file_name) = self._db_doc_paths[mod_name].headTail
        else:
            docs_dir = bass.settings[u'bash.modDocs.dir'] or bass.dirs[u'mods']
            file_name = GPath(u'')
        doc_path = FileOpen.display_dialog(self,
            _(u'Select doc for %s:') % mod_name, docs_dir, file_name, u'*.*',
            allow_create=True)
        if not doc_path: return
        bass.settings[u'bash.modDocs.dir'] = doc_path.head
        if mod_name not in self._db_doc_paths:
            self._mod_list.lb_append(mod_name.s)
        self._db_doc_paths[mod_name] = doc_path
        self.SetMod(mod_name)

    def _do_rename(self):
        """Handle "Rename Doc" button click."""
        old_path = self._db_doc_paths[self._mod_name]
        (work_dir,file_name) = old_path.headTail
        #--Dialog
        dest_path = FileSave.display_dialog(self, _(u'Rename file to:'),
                                            work_dir, file_name, u'*.*')
        if not dest_path or dest_path == old_path: return
        #--OS renaming
        dest_path.remove()
        old_path.moveTo(dest_path)
        if self._doc_is_wtxt:
            old_html, new_html = (x.root+u'.html' for x in (old_path,dest_path))
            try: old_html.moveTo(new_html)
            except StateError: new_html.remove()
        #--Remember change
        self._db_doc_paths[self._mod_name] = dest_path
        self._doc_name_box.text_content = dest_path.stail

    def DoSave(self):
        """Saves doc, if necessary."""
        doc_path = self._db_doc_paths.get(self._mod_name)
        if not doc_path: return  # nothing to save if no file is loaded
        if not self._doc_ctrl.is_text_modified(): return
        self._doc_ctrl.set_text_modified(False)
        with doc_path.open(u'w', encoding=u'utf-8-sig') as out:
            out.write(self._doc_ctrl.fallback_text)
        if self._doc_is_wtxt:
            bolt.WryeText.genHtml(doc_path, None,
                                  bosh.modInfos.store_dir.join(u'Docs'))

    def _load_data(self, doc_path=None, uni_str=None, editing=False,
                   __html_extensions=frozenset((u'.htm', u'.html', u'.mht'))):
        if doc_path and doc_path.cext in __html_extensions and not editing \
                and web_viewer_available():
            self._doc_ctrl.try_load_html(doc_path)
        elif doc_path and doc_path.cext == u'.pdf' and not editing \
                and pdf_viewer_available():
            self._doc_ctrl.try_load_pdf(doc_path)
        else:
            if uni_str is None and doc_path:
                self._doc_ctrl.try_load_text(doc_path)
            else:
                self._doc_ctrl.load_text(uni_str)

    def SetMod(self, mod_name):
        """Sets the mod to show docs for."""
        self.DoSave()
        # defaults
        self._edit_box.is_checked = False
        self._doc_ctrl.set_text_editable(False)
        mod_name = GPath(mod_name)
        self._mod_name = mod_name
        self._mod_name_box.text_content = mod_name.s
        if not mod_name:
            self._load_data(uni_str=u'')
            for btn in self._buttons:
                btn.enabled = False
            return
        self._set_btn.enabled = True
        self._mod_list.lb_select_index(self._mod_list.lb_index_for_str_item(mod_name.s))
        # Doc path
        doc_path = self._db_doc_paths.get(mod_name, GPath(u''))
        self._doc_name_box.text_content = doc_path.stail
        for btn in (self._forget_btn, self._rename_btn, self._edit_box,
                    self._open_btn):
            btn.enabled = bool(doc_path)
        # Set empty and uneditable if there's no doc path:
        if not doc_path:
            self._load_data(uni_str=u'')
        # Create new file if none exists
        elif not doc_path.exists():
            for template_file in (bosh.modInfos.store_dir.join(
                    u'Docs', u'{} Readme Template'.format(fname))
                                  for fname in (u'My', u'Bash')):
                if template_file.exists():
                    with template_file.open(u'rb') as ins:
                        template = bolt.decoder(ins.read())
                    break
            else:
                template = f'= $modName {u"=" * (74 - len(mod_name))}#\n' \
                           f'{doc_path}'
            self._load_data(uni_str=string.Template(template).substitute(
                modName=mod_name.s))
            # Start edit mode
            self._edit_box.is_checked = True
            self._doc_ctrl.set_text_editable(True)
            self._doc_ctrl.set_text_modified(True)
            # Save the new file
            self.DoSave()
        else:  # Otherwise it exists
            editing = self._db_is_editing.get(mod_name, False)
            if editing:
                self._edit_box.is_checked = True
                self._doc_ctrl.set_text_editable(True)
            else:
                is_wtxt = self._get_is_wtxt(doc_path)
                if is_wtxt:  # Update generated html
                    html_path = doc_path.root + u'.html'
                    if not html_path.exists() or (doc_path.mtime > html_path.mtime):
                        bolt.WryeText.genHtml(doc_path, None,
                                              bosh.modInfos.store_dir.join(u'Docs'))
            self._load_data(doc_path=doc_path, editing=editing)

    def on_closing(self, destroy=True):
        """Handle window close event.
        Remember window size, position, etc."""
        self.DoSave()
        bass.settings[u'bash.modDocs.show'] = False
        Link.Frame.docBrowser = None
        super(DocBrowser, self).on_closing(destroy)

#------------------------------------------------------------------------------
_BACK, _FORWARD, _MOD_LIST, _CRC, _VERSION, _LOAD_PLUGINS, _COPY_TEXT, \
_UPDATE = range(8)

def _get_mod_checker_setting(key, default=None):
    return bass.settings.get(u'bash.modChecker.show%s' % key, default)

def _set_mod_checker_setting(key, value):
    bass.settings[u'bash.modChecker.show%s' % key] = value

class PluginChecker(WindowFrame):
    """Plugin Checker frame."""
    _frame_settings_key = u'bash.modChecker'
    _def_size = (475, 500)

    def __init__(self):
        #--Singleton
        Link.Frame.plugin_checker = self
        #--Window
        super(PluginChecker, self).__init__(
            Link.Frame, title=_(u'Plugin Checker'), sizes_dict=bass.settings,
            icon_bundle=Resources.bashBlue)
        #--Data
        self.orderedActive = None
        self.__merged = None
        self.__imported = None
        #--Text
        self.check_mods_text = None
        self._html_ctrl = DocumentViewer(self)
        back_btn, forward_btn, reload_btn = self._html_ctrl.get_buttons()
        self._controls = OrderedDict()
        self._setting_names = {}
        def _f(key, make_checkbox, caption_, setting_key=None,
               setting_value=None, callback=self.CheckMods, setting_tip=u''):
            if make_checkbox:
                btn = CheckBox(self, caption_)
                btn.on_checked.subscribe(callback)
            else:
                btn = Button(self, caption_)
                btn.on_clicked.subscribe(callback)
            btn.tooltip = setting_tip
            if make_checkbox and setting_key is not None:
                new_value = bass.settings.get(
                    u'bash.modChecker.show%s' % setting_key, setting_value)
                btn.is_checked = new_value
                self._setting_names[key] = setting_key
            self._controls[key] = btn
        _f(_MOD_LIST,     True,  _(u'Plugin List'),     u'ModList', False,
           setting_tip=_(u'Show a list of all installed plugins as well.'))
        _f(_VERSION,      True,  _(u'Version Numbers'), u'Version', True,
           setting_tip=_(u'Show verion numbers alongside the plugin list.'))
        _f(_CRC,          True,  _(u'CRCs'),            u'CRC',     False,
           setting_tip=_(u'Show CRCs alongside the plugin list.'))
        _f(_LOAD_PLUGINS, True,  _(u'Load Plugins'),    u'Plugins', True,
           setting_tip=_(u'Detect more types of problems that require loading '
                         u'every plugin.'))
        _f(_COPY_TEXT,    False, _(u'Copy Text'), callback=self.OnCopyText,
           setting_tip=_(u'Copy a text version of the report to the '
                         u'clipboard.'))
        _f(_UPDATE,       False, _(u'Update'),
           setting_tip=_(u'Regenerate the report from scratch.'))
        #--Events
        self.on_activate.subscribe(self.on_activation)
        VLayout(border=4, spacing=4, item_expand=True, items=[
            (self._html_ctrl, LayoutOptions(weight=1)),
            HLayout(spacing=4, items=[
                self._controls[_MOD_LIST], self._controls[_CRC],
                self._controls[_VERSION]
            ]),
            HLayout(spacing=4, items=[
                self._controls[_LOAD_PLUGINS], Stretch(), self._controls[_UPDATE],
                self._controls[_COPY_TEXT], back_btn, forward_btn, reload_btn
            ])
        ]).apply_to(self)
        self.CheckMods()

    def OnCopyText(self):
        """Copies text of report to clipboard."""
        text_ = u'[spoiler]\n' + self.check_mods_text + u'[/spoiler]'
        text_ = re.sub(r'\[\[.+?\|\s*(.+?)\]\]', r'\1', text_, re.U)
        text_ = re.sub(u'(__|\*\*|~~)', u'', text_, re.U)
        text_ = re.sub(u'&bull; &bull;', u'**', text_, re.U)
        text_ = re.sub(u'<[^>]+>', u'', text_, re.U)
        copy_text_to_clipboard(text_)

    def CheckMods(self, _new_value=None):
        """Do mod check."""
        # Enable or disable the children of the Mod List button
        _set_mod_checker_setting(self._setting_names[_MOD_LIST],
                                 self._controls[_MOD_LIST].is_checked)
        setting_val = _get_mod_checker_setting(self._setting_names[_MOD_LIST])
        for ctrl_id in (_CRC, _VERSION):
            self._controls[ctrl_id].enabled = setting_val
        # Set settings from all the buttons' values
        for ctrl_id in (_CRC, _VERSION, _LOAD_PLUGINS):
            _set_mod_checker_setting(self._setting_names[ctrl_id],
                                     self._controls[ctrl_id].is_checked)
        #--Cache info from modinfos to support auto-update.
        self.orderedActive = load_order.cached_active_tuple()
        self.__merged = bosh.modInfos.merged.copy()
        self.__imported = bosh.modInfos.imported.copy()
        #--Do it
        self.check_mods_text = mods_metadata.checkMods(self, bosh.modInfos,
            *[_get_mod_checker_setting(self._setting_names[setting_key])
            for setting_key in (_MOD_LIST, _CRC, _VERSION, _LOAD_PLUGINS)])
        if web_viewer_available():
            log_path = bass.dirs[u'saveBase'].join(u'ModChecker.html')
            css_dir = bass.dirs[u'mopy'].join(u'Docs')
            bolt.convert_wtext_to_html(log_path, self.check_mods_text, css_dir)
            self._html_ctrl.try_load_html(log_path)
        else:
            self._html_ctrl.load_text(self.check_mods_text)

    def on_activation(self, evt_active):
        """Handle window activate/deactivate. Use for auto-updating list."""
        if (evt_active and (
                self.orderedActive != load_order.cached_active_tuple() or
                self.__merged != bosh.modInfos.merged or
                self.__imported != bosh.modInfos.imported)
            ):
            self.CheckMods()

    def on_closing(self, destroy=True):
        # Need to unset Link.Frame.plugin_checker here to avoid accessing a
        # deleted object when clicking the plugin checker button again.
        Link.Frame.plugin_checker = None
        super(PluginChecker, self).on_closing(destroy)

    @classmethod
    def create_or_raise(cls):
        """Creates and shows the plugin checker if it doesn't already exist,
        otherwise just raises the existing one."""
        if not Link.Frame.plugin_checker:
            cls().show_frame()
        Link.Frame.plugin_checker.raise_frame()

#------------------------------------------------------------------------------
class InstallerProject_OmodConfigDialog(WindowFrame):
    """Dialog for editing omod configuration data."""
    _size_hints = (300, 300)

    def __init__(self, parent, project):
        #--Data
        self.config = config = omods.OmodConfig.getOmodConfig(project)
        #--GUI
        super(InstallerProject_OmodConfigDialog, self).__init__(parent,
            title=_(u'Omod Config: ') + project.s,
            icon_bundle=Resources.bashBlue, sizes_dict=bass.settings,
            caption=True, clip_children=True, tab_traversal=True)
        #--Fields
        self.gName = TextField(self, init_text=config.omod_proj,max_length=100)
        self.gVersion = TextField(self, f'{config.vMajor:d}.'
                                        f'{config.vMinor:02d}', max_length=32)
        self.gWebsite = TextField(self, config.website, max_length=512)
        self.gAuthor = TextField(self, config.omod_author, max_length=512)
        self.gEmail = TextField(self, init_text=config.email, max_length=512)
        self.gAbstract = TextArea(self, init_text=config.abstract,
                                  max_length=4 * 1024)
        #--Layout
        def _no_fill_text(txt):
            return Label(self, txt), LayoutOptions(expand=False)
        save_button = SaveButton(self, default=True)
        save_button.on_clicked.subscribe(self.DoSave)
        cancel_button = CancelButton(self)
        cancel_button.on_clicked.subscribe(self.on_closing)
        VLayout(item_expand=True, spacing=4, border=4, items=[
            GridLayout(h_spacing=4, v_spacing=4, stretch_cols=[1],
                       item_expand=True, items=[
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
        self.component_size = (350, 400)

    def DoSave(self):
        """Handle save button."""
        config = self.config
        #--Text fields
        config.omod_proj = self.gName.text_content.strip()
        config.website = self.gWebsite.text_content.strip()
        config.omod_author = self.gAuthor.text_content.strip()
        config.email = self.gEmail.text_content.strip()
        config.abstract = self.gAbstract.text_content.strip()
        #--Version
        maVersion = re.match(r'(\d+)\.(\d+)',
                             self.gVersion.text_content.strip(), flags=re.U)
        if maVersion:
            config.vMajor,config.vMinor = (int(g) for g in maVersion.groups())
        else:
            config.vMajor,config.vMinor = (0,0)
        #--Done
        self.config.writeOmodConfig()
        self.on_closing()
