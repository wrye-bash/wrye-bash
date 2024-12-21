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
#  Wrye Bash copyright (C) 2005-2009 Wrye, 2010-2024 Wrye Bash Team
#  https://github.com/wrye-bash
#
# =============================================================================

import os
import re
import string
from collections import OrderedDict

from .. import balt, bass, bolt, bosh, bush, load_order, wrye_text
from ..balt import Link, Resources
from ..bolt import FName, FNDict
from ..bosh import empty_path, mods_metadata, omods
from ..env import canonize_ci_path
from ..exception import StateError, CancelError
from ..gui import Button, CancelButton, CheckBox, DocumentViewer, DropDown, \
    FileOpen, FileSave, GridLayout, HLayout, Label, LayoutOptions, ListBox, \
    SaveButton, SearchBar, Spacer, Splitter, Stretch, TextArea, TextField, \
    VerticalLine, VLayout, WindowFrame, bell, copy_text_to_clipboard, \
    web_viewer_available, showWarning

class DocBrowser(WindowFrame):
    """Doc Browser frame."""
    _key_prefix = 'bash.modDocs'
    _def_size = (900, 500)

    def __init__(self, mod_infos_singl):
        # Data
        self._mod_infos_singl = mod_infos_singl # for modInfo doc/docEdit props
        self._doc_is_wtxt = False
        self._doc_dir = mod_infos_singl.store_dir.join('Docs')
        # Singleton
        Link.Frame.docBrowser = self
        # Window
        super().__init__(Link.Frame, title=_('Doc Browser'),
            icon_bundle=Resources.bashBlue, sizes_dict=bass.settings)
        # Base UI components
        root_window = Splitter(self)
        mod_list_window, main_window = root_window.make_panes(250,
                                                              vertically=True)
        self._plugin_search = SearchBar(mod_list_window,
            hint=_('Search Plugins'))
        self._plugin_search.on_text_changed.subscribe(self._search_plugins)
        self._plugin_dropdown = DropDown(mod_list_window, value='',
            choices=[''])
        self._plugin_dropdown.on_combo_select.subscribe(self._do_select_free)
        # Get mods that have a doc attribute set
        self._mod_list = ListBox(mod_list_window, isSort=True,
                                 onSelect=self._do_select_existing)
        # Buttons
        self._set_btn = Button(main_window, _('Set Doc…'),
                               btn_tooltip=_('Associates this plugin file '
                                             'with a document.'))
        self._set_btn.on_clicked.subscribe(self._do_set)
        self._forget_btn = Button(main_window, _('Forget Doc'),
                                  btn_tooltip=_('Removes the link between '
                                                'this plugin file and the '
                                                'matching document.'))
        self._forget_btn.on_clicked.subscribe(self._do_forget)
        self._rename_btn = Button(main_window, _('Rename Doc…'),
                                  btn_tooltip=_('Renames the document.'))
        self._rename_btn.on_clicked.subscribe(self._do_rename)
        self._edit_box = CheckBox(main_window, _('Allow Editing'),
                                  chkbx_tooltip=_('Enables or disables '
                                                  'editing in the text field '
                                                  'below.'))
        self._edit_box.on_checked.subscribe(self._do_edit)
        self._open_btn = Button(main_window, _('Open Doc…'),
                                btn_tooltip=_('Opens the document in your '
                                              'default viewer/editor.'))
        self._open_btn.on_clicked.subscribe(self._do_open)
        self._doc_name_box = TextField(main_window, editable=False)
        self._doc_ctrl = DocumentViewer(main_window, balt.get_dv_bitmaps())
        self._prev_btn, self._next_btn, self._reload_btn = \
            self._doc_ctrl.get_buttons()
        self._buttons = [self._edit_box, self._set_btn, self._forget_btn,
                         self._rename_btn, self._open_btn, self._prev_btn,
                         self._next_btn, self._reload_btn]
        # Search bar and dropdown caches also used in checking for changes
        self._full_lo = {}
        self._dropdown_index = {}
        #--Mod list
        VLayout(spacing=4, item_expand=True, items=[
            self._plugin_search,
            self._plugin_dropdown,
            (self._mod_list, LayoutOptions(weight=1)),
        ]).apply_to(mod_list_window)
        #--Text field and buttons
        VLayout(spacing=4, item_expand=True, items=[
            HLayout(item_expand=True, items=[
                self._edit_box,
                Spacer(6), VerticalLine(main_window), Spacer(6),
                self._set_btn, self._forget_btn, self._rename_btn,
                self._open_btn,
                Spacer(6), VerticalLine(main_window), Spacer(6),
                self._prev_btn, self._next_btn, self._reload_btn,
            ]),
            self._doc_name_box, (self._doc_ctrl, LayoutOptions(weight=3)),
        ]).apply_to(main_window)
        VLayout(item_expand=1, item_border=4, item_weight=1, items=[
            root_window,
        ]).apply_to(self)
        for btn in self._buttons:
            btn.enabled = False
        self.on_activate.subscribe(self._on_activation)

    def _on_activation(self, evt_active):
        """Update the list of mods every time the frame is shown."""
        if evt_active: self._init_controls()

    def _init_controls(self):
        """Init the docs list and plugin dropdown - check for changes in mods
        on init and activation."""
        items = FNDict((('', ''),)) # '' == no plugin selected
        items.update((k, k.lower()) for k in sorted(self._mod_infos_singl))
        if self._full_lo != items:
            self._full_lo = items
            self._search_plugins(self._plugin_search.text_content, # empty on __init__
                                 set_mod=False)
        self._update_docs_list()

    def _update_docs_list(self):
        sel = self._mod_list.lb_get_selected_strings()
        sel = sel[0] if sel else None # one selection right?
        mods = [*map(FName, self._mod_list.lb_get_str_items())]
        documented = {mod_name for mod_name, mod_inf in
            self._mod_infos_singl.items() if mod_inf.get_table_prop('doc')}
        if del_mods := (set_mods := {*mods}) - documented:
            for mod_dex, mod in enumerate(reversed(mods)):
                if mod in del_mods: # deleted or docs removed
                    self._mod_list.lb_delete_at_index(len(mods) - mod_dex - 1)
                    if sel == mod: # deselect previous plugin
                        self.SetMod('') # needed
        for mod in documented - set_mods:
            self._mod_list.lb_append(mod)

    def _get_doc_prop(self, def_=None, mod_name=None, *, prop='doc'):
        if mod_name is None: mod_name = self._dropdown_item()
        if not mod_name: return def_ # nothing selected in _plugin_dropdown
        return self._mod_infos_singl[mod_name].get_table_prop(prop, def_)

    def _set_doc_prop(self, doc_path, *, prop='doc'):
        self._mod_infos_singl[self._dropdown_item()].set_table_prop(prop,
                                                                    doc_path)

    def _dropdown_item(self) -> FName:
        """Return the currently selected plugin in the dropdown."""
        return FName(self._plugin_dropdown.get_value())

    @staticmethod
    def _get_is_wtxt(doc_path, *, __rx=re.compile(r'^=.+=#\s*$')):
        """Determines whether specified path is a wtxt file."""
        try:
            with doc_path.open(u'r', encoding=u'utf-8-sig') as text_file:
                match_text = __rx.match(text_file.readline())
            return match_text is not None
        except (OSError, UnicodeDecodeError):
            return False

    def _search_plugins(self, search_str, *, set_mod=True):
        """Called when text is entered into the search bar. Narrows the results
        in the dropdown. Empty search_str populates the dropdown with the
        modlist which must be up to date!"""
        # set_choices can change self._dropdown_item - we need the previous
        # value so we can restore it after searching
        prev_doc_plugin = self._dropdown_item()
        search_lower = search_str.strip().lower()
        filtered_plugins = [k for k, v in self._full_lo.items()
                            if search_lower in v]
        self._dropdown_index = {pl: i for i, pl in enumerate(filtered_plugins)}
        with self._plugin_dropdown.pause_drawing():
            self._plugin_dropdown.set_choices(filtered_plugins)
            # Check if the previous plugin can be restored now, otherwise
            # select the first plugin
            try:
                new_doc_choice = self._dropdown_index[prev_doc_plugin]
            except KeyError:
                new_doc_choice = 0
            self._plugin_dropdown.set_selection(new_doc_choice)
            if set_mod: # else we are called directly from _init_controls
                # Update the doc viewer to match the new selection
                self.SetMod(self._dropdown_item())

    def _do_open(self):
        """Handle "Open Doc" button."""
        doc_path = self._get_doc_prop()
        if not doc_path:
            return bell()
        if not doc_path.is_file():
            showWarning(self, _('The assigned document is not present:') +
                        f'\n  {doc_path}')
        else:
            doc_path.start()

    def _do_edit(self, is_editing):
        """Handle "Edit Doc" button click."""
        self.DoSave()
        self._set_doc_prop(is_editing, prop='docEdit')
        self._doc_ctrl.set_text_editable(is_editing)
        self._load_data(doc_path=(self._get_doc_prop()), editing=is_editing)

    def _do_forget(self):
        """Handle "Forget Doc" button click. Drops the associated help document
        for the current plugin."""
        if self._get_doc_prop() is None:  ##: can it happen?
            return
        self._set_doc_prop(None)
        p_index = self._mod_list.lb_index_for_str_item(self._dropdown_item())
        if p_index is None: return
        self._mod_list.lb_delete_at_index(p_index)
        remaining_plugins = self._mod_list.lb_get_str_items()
        # If there are plugins remaining, switch to the one right before
        # the one that was removed
        if remaining_plugins:
            self.SetMod(remaining_plugins[max(p_index - 1, 0)])
        else:
            self._clear_doc()

    def _do_select_free(self, selection_label):
        """Called when a plugin is selected from the dropdown."""
        self.SetMod(selection_label)

    def _do_select_existing(self, _lb_selection_dex, lb_selection_str):
        """Called when a plugin is selected in the left-hand list."""
        self.SetMod(lb_selection_str)

    def _do_set(self):
        """Handle "Set Doc" button click."""
        #--Already have mod data?
        if doc_ := self._get_doc_prop():
            (docs_dir, file_name) = doc_.headTail
        else:
            docs_dir = bass.settings[u'bash.modDocs.dir'] or bass.dirs[u'mods']
            file_name = ''
        msg = _('Select document for %(target_file_name)s:') % {
                    'target_file_name': self._dropdown_item()}
        doc_path = FileOpen.display_dialog(self, msg, docs_dir, file_name,
                                           '*.*', allow_create_file=True)
        if not doc_path: return
        bass.settings[u'bash.modDocs.dir'] = doc_path.head
        if not doc_:
            self._mod_list.lb_append(self._dropdown_item())
        self._set_doc_prop(doc_path)
        self.SetMod(self._dropdown_item())

    def _do_rename(self):
        """Handle "Rename Doc" button click."""
        old_path = self._get_doc_prop()
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
        self._set_doc_prop(dest_path)
        self._doc_name_box.text_content = dest_path.stail

    def _clear_doc(self):
        """Clears the contents of the doc browser's text boxes, doc viewer,
        etc."""
        self.DoSave()
        for btn in self._buttons:
            btn.enabled = False
        self._doc_name_box.text_content = ''
        self._mod_list.lb_select_none()
        self._plugin_dropdown.set_selection(0)
        self._load_data(uni_str='')

    def DoSave(self):
        """Saves doc, if necessary."""
        doc_path = self._get_doc_prop()
        if not doc_path: return  # nothing to save if no file is loaded
        if not self._doc_ctrl.is_text_modified(): return
        self._doc_ctrl.set_text_modified(False)
        with doc_path.open(u'w', encoding=u'utf-8-sig') as out:
            out.write(self._doc_ctrl.fallback_text)
        if self._doc_is_wtxt:
            wrye_text.genHtml(doc_path, None, self._doc_dir)

    def _load_data(self, doc_path=None, uni_str=None, editing=False,
                   __html_extensions=frozenset((u'.htm', u'.html', u'.mht'))):
        if doc_path and doc_path.cext in __html_extensions and not editing:
            self._doc_ctrl.try_load_html(doc_path)
        elif doc_path and doc_path.cext == '.pdf' and not editing:
            self._doc_ctrl.try_load_pdf(doc_path)
        else:
            if uni_str is None and doc_path:
                self._doc_ctrl.try_load_text(doc_path)
            else:
                self._doc_ctrl.load_text(uni_str)

    def SetMod(self, mod_name):
        """Sets the mod to show docs for."""
        # defaults
        self._edit_box.is_checked = False
        self._doc_ctrl.set_text_editable(False)
        if not mod_name:
            self._clear_doc()
            return
        # update _search_plugins caches as we may be called for new mods
        self._init_controls()
        self.DoSave()
        # If we ended up selecting something outside the search clear the
        # search which triggers the subscribed _search_plugins and waits until
        # it's done - the latter might update _dropdown_index
        self._plugin_search.clear_search_bar(mod_name)
        self._plugin_dropdown.set_selection(
            self._dropdown_index[FName(mod_name)])
        self._set_btn.enabled = True
        self._mod_list.lb_select_index(
            self._mod_list.lb_index_for_str_item(mod_name))
        # Doc path
        doc_path = self._get_doc_prop(empty_path, mod_name)
        self._doc_name_box.text_content = doc_path.stail
        for btn in (self._forget_btn, self._rename_btn, self._edit_box,
                    self._open_btn):
            btn.enabled = bool(doc_path)
        # Set empty and uneditable if there's no doc path:
        if not doc_path:
            self._load_data(uni_str=u'')
            return
        # Handle case where the file doesn't exist - this is tricky
        elif not doc_path.is_file():
            if not doc_path.is_absolute():
                # This path probably came from another operating system. If it
                # came from the Data folder, we may be able to find it
                doc_parents = doc_path.head
                wip_doc = doc_path.stail
                data_lower = bush.game.mods_dir.lower()
                while doc_parents:
                    wip_doc = os.path.join(doc_parents.sbody, wip_doc)
                    dp_head = doc_parents.head
                    if dp_head.stail.lower() == data_lower:
                        break
                    doc_parents = dp_head
                else:
                    # Could not find a parent Data folder, this may have been
                    # some random doc path outside the Data folder. Best we can
                    # do is ignore it
                    self._load_data(uni_str='')
                    return
                ported_path = canonize_ci_path(
                    bass.dirs['mods'].join(wip_doc))
                if ported_path and ported_path.is_file():
                    doc_path = ported_path
                    self._set_doc_prop(ported_path)
                else:
                    # We reconstructed, but the path doesn't seem to exist.
                    # Again, best we can do is ignore it
                    self._load_data(uni_str='')
                    return
            else:
                for template_file in (self._doc_dir.join(
                        f'{s} Readme Template') for s in ('My', 'Bash')):
                    if template_file.exists():
                        with template_file.open(u'rb') as ins:
                            template = bolt.decoder(ins.read())
                        break
                else:
                    template = (f'= $modName {u"=" * (74 - len(mod_name))}#\n'
                                f'{doc_path}')
                self._load_data(uni_str=string.Template(template).substitute(
                    modName=mod_name))
                # Start edit mode
                self._edit_box.is_checked = True
                self._doc_ctrl.set_text_editable(True)
                self._doc_ctrl.set_text_modified(True)
                # Save the new file
                self.DoSave()
                return
        # Either the path existed from the start or we ported it over
        editing = self._get_doc_prop(False, mod_name, prop='docEdit')
        if editing:
            self._edit_box.is_checked = True
            self._doc_ctrl.set_text_editable(True)
        else:
            is_wtxt = self._get_is_wtxt(doc_path)
            if is_wtxt:  # Update generated html
                html_path = doc_path.root + '.html'
                if not html_path.is_file() or doc_path.mtime > html_path.mtime:
                    wrye_text.genHtml(doc_path, None, self._doc_dir)
        self._load_data(doc_path=doc_path, editing=editing)

    def on_closing(self, destroy=True):
        """Handle window close event.
        Remember window size, position, etc."""
        self.DoSave()
        Link.Frame.docBrowser = None
        super(DocBrowser, self).on_closing(destroy)

#------------------------------------------------------------------------------
_BACK, _FORWARD, _MOD_LIST, _CRC, _VERSION, _LOAD_PLUGINS, _COPY_TEXT, \
_UPDATE = range(8)

def _get_mod_checker_setting(key, default=None):
    return bass.settings.get(f'bash.modChecker.show{key}', default)

def _set_mod_checker_setting(key, value):
    bass.settings[f'bash.modChecker.show{key}'] = value

class PluginChecker(WindowFrame):
    """Plugin Checker frame."""
    _key_prefix = 'bash.modChecker'
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
        self._html_ctrl = DocumentViewer(self, balt.get_dv_bitmaps())
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
                new_value = _get_mod_checker_setting(setting_key,
                    setting_value)
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
        # If we can't load plugins, don't even show the option
        if not bush.game.Esp.canBash:
            self._controls[_LOAD_PLUGINS].visible = False
        #--Events
        self.on_activate.subscribe(self.on_activation)
        VLayout(border=4, spacing=4, item_expand=True, items=[
            (self._html_ctrl, LayoutOptions(weight=1)),
            HLayout(spacing=4, items=[
                self._controls[_MOD_LIST], self._controls[_CRC],
                self._controls[_VERSION]
            ]),
            HLayout(spacing=4, items=[
                self._controls[_LOAD_PLUGINS], Stretch(),
                self._controls[_UPDATE], self._controls[_COPY_TEXT],
                back_btn, forward_btn, reload_btn
            ])
        ]).apply_to(self)
        self.CheckMods()

    def OnCopyText(self):
        """Copies text of report to clipboard."""
        mods_txt = f'[spoiler]\n{self.check_mods_text}[/spoiler]'
        mods_txt = re.sub(r'\[\[.+?\|\s*(.+?)\]\]', r'\1', mods_txt)
        mods_txt = re.sub(r'(__|\*\*|~~)', '', mods_txt)
        mods_txt = re.sub('&bull; &bull;', '**', mods_txt)
        mods_txt = re.sub('<[^>]+>', '', mods_txt)
        copy_text_to_clipboard(mods_txt)

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
        with balt.Progress(_('Checking Plugins…'), parent=self,
                           abort=True) as prog:
            try:
                args = prog, bosh.modInfos, *(
                    _get_mod_checker_setting(self._setting_names[setting_key])
                for setting_key in (_MOD_LIST, _CRC, _VERSION, _LOAD_PLUGINS))
                self.check_mods_text = mods_metadata.checkMods(*args)
            except CancelError:
                return # user pressed cancel early
        log_path = bass.dirs[u'saveBase'].join(u'ModChecker.html')
        css_dir = bass.dirs[u'mopy'].join(u'Docs')
        wrye_text.convert_wtext_to_html(log_path, self.check_mods_text, css_dir)
        if web_viewer_available():
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
            title=f"{_('OMOD Config')}: {project}",
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
                             self.gVersion.text_content.strip())
        if maVersion:
            config.vMajor, config.vMinor = map(int, maVersion.groups())
        else:
            config.vMajor,config.vMinor = (0,0)
        #--Done
        self.config.writeOmodConfig()
        self.on_closing()
