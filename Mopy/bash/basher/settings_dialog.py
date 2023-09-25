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
#  Wrye Bash copyright (C) 2005-2009 Wrye, 2010-2023 Wrye Bash Team
#  https://github.com/wrye-bash
#
# =============================================================================
import io
import os
import subprocess
import webbrowser
from collections import defaultdict

from . import BashStatusBar, tabInfo
from .constants import colorInfo, settingDefaults
from .dialogs import UpdateNotification
from .. import balt, barb, bass, bolt, bosh, bush, env, exception
from ..balt import Link, Resources, colors
from ..bolt import deprint, dict_sort, os_name, readme_url, LooseVersion, \
    reverse_dict
from ..gui import ApplyButton, ATreeMixin, BusyCursor, Button, CancelButton, \
    CheckBox, CheckListBox, ClickableImage, Color, ColorPicker, DialogWindow, \
    DirOpen, DoubleListBox, DropDown, FileOpen, FileSave, HBoxedLayout, \
    HLayout, HorizontalLine, Label, LayoutOptions, ListBox, OkButton, \
    OpenButton, PanelWin, RevertButton, SaveAsButton, SaveButton, \
    ScrollableWindow, Spacer, Stretch, TextArea, TextField, TreePanel, \
    VBoxedLayout, VLayout, WrappingLabel, CENTER, VerticalLine, Spinner, \
    showOk, askYes, askText, showError, askWarning, showInfo, ImageButton
from ..localize import dump_translator
from ..update_checker import UpdateChecker, can_check_updates
from ..wbtemp import default_global_temp_dir

class SettingsDialog(DialogWindow):
    """A dialog for configuring settings, split into multiple pages."""
    title = _(u'Settings')
    _def_size = (700, 450)
    _min_size = (500, 300)

    def __init__(self, initial_page=u''):
        """Creates a new settings dialog with the specified initial page.

        :param initial_page: If set to a truthy string, will switch to that
                             page before showing the dialog to the user."""
        super(SettingsDialog, self).__init__(Link.Frame,
            icon_bundle=Resources.bashBlue, sizes_dict=balt.sizes)
        # Used to keep track of the pages that have changed settings
        self._changed_state = {}
        # Used to keep track of a potential scheduled restart of Wrye Bash in
        # order to apply certain settings
        self._requesting_restart = set()
        self._restart_params = []
        # GUI/Layout Definition
        self._tab_tree = TreePanel(self, _settings_pages, _page_descriptions)
        for leaf_page in self._tab_tree.get_leaf_pages():
            self._changed_state[leaf_page] = False
            leaf_page._mark_changed = self._exec_mark_changed
            leaf_page._request_restart = self._exec_request_restart
        ##: Unused right now, will come in handy once we move all tab-specific
        # settings into this dialog as well
        if initial_page:
            self._tab_tree.select_page(initial_page)
##: Not yet ready, will need much more refactoring (#178). We'd need a way to
# have each page and each setting as an object, so that we can pass the search
# term along to each page. Plus TreeCtrl refactoring is needed to easily hide
# non-matching items, etc. Making this work is a very long-term goal.
#        self._search_bar = SearchBar(self)
#        self._search_bar.on_text_changed.subscribe(self._handle_search)
        help_btn = ClickableImage(self, balt.images[u'help.24'].get_bitmap(),
            btn_tooltip=_(u'View the readme section for the currently active '
                          u'settings page.'))
        help_btn.on_clicked.subscribe(self._open_readme)
        ok_btn = OkButton(self)
        ok_btn.on_clicked.subscribe(self._send_apply)
        self._apply_btn = ApplyButton(self)
        self._apply_btn.enabled = False
        self._apply_btn.on_clicked.subscribe(self._send_apply)
        VLayout(border=4, spacing=4, item_expand=True, items=[
#            self._search_bar,
            (self._tab_tree, LayoutOptions(weight=1)),
            HorizontalLine(self),
            HLayout(spacing=5, items=[
                help_btn, Stretch(), ok_btn, CancelButton(self),
                self._apply_btn,
            ]),
        ]).apply_to(self)
        # We have to wait until now and pass this size along because we can't
        # get a size from the panels (they're all sized '20x20' internally and
        # querying their best size breaks because that depends on the size of
        # the text - which is exactly what we're trying to adjust...)
        self._tab_tree.wrap_page_descriptions(self.component_size[0])

    def _exec_mark_changed(self, requesting_page, is_changed):
        """Marks or unmarks the requesting page as changed, and enables or
        disables the Apply button accordingly."""
        self._changed_state[requesting_page] = is_changed
        self._apply_btn.enabled = any(self._changed_state.values())

    def _exec_request_restart(self, requesting_setting, restart_params=()):
        """Schedules a restart request from the specified setting."""
        self._requesting_restart.add(requesting_setting)
        self._restart_params.extend(restart_params)

    def _open_readme(self):
        """Handles a click on the help button by opening the readme."""
        ##: skip_local because webbrowser.open eats anchors on Windows
        advanced_radme = readme_url(mopy=bass.dirs[u'mopy'], advanced=True,
                                    skip_local=True)
        help_anchor = _page_anchors[self._tab_tree.get_selected_page_path()]
        webbrowser.open(advanced_radme + u'#' + help_anchor)

    def _send_apply(self):
        """Propagates an Apply button click to all child pages."""
        for leaf_page in self._tab_tree.get_leaf_pages():
            leaf_page.on_apply()
        if self._requesting_restart:
            # A restart has been requested, ask the user whether to do it now
            m = [_('The following settings require Wrye Bash to be restarted '
                   'before they take effect:'), '\n'.join(f' - {r}' for r in
                        sorted(self._requesting_restart)),
                 _('Do you want to restart now?')]
            if askYes(self, '\n\n'.join(m), title=_('Restart Wrye Bash')):
                Link.Frame.Restart(*self._restart_params)
            else:
                # User denied the restart, don't bother them again
                self._requesting_restart.clear()
                del self._restart_params[:]

class _ASettingsPage(ATreeMixin):
    """Abstract class for all settings pages."""
    # A set of all setting IDs in this page. This is optional, see
    # _mark_setting_changed below
    # PY3: Consider an enum here for stricter typing + no chance of typos
    _setting_ids = set()

    def __init__(self, parent, page_desc):
        super().__init__(parent)
        self._page_desc_label = WrappingLabel(self, page_desc)
        # Callback to a method that takes the settings page and a boolean,
        # marking the settings in the specified page as changed or not. Used
        # to automatically enable or disable the Apply button.
        self._mark_changed = None
        # Callback to a method that will ask the user to restart Wrye Bash
        # after the settings from all tabs have been applied. It takes two
        # parameters, a user-readable name for the setting that requires the
        # restart and a list of options to pass to the newly started process.
        # Note that the user can deny the restart, so you can't rely on the
        # next start definitely having these parameters passed to it
        ##: The restart parameters here are a smell, see usage in LanguagePage
        self._request_restart = None
        # Used to keep track of each setting's 'changed' state
        self._setting_states = {k: False for k in self._setting_ids}

    def _is_changed(self, setting_id):
        """Checks if the setting with the specified ID has been changed. See
        _mark_setting_changed below."""
        if setting_id not in self._setting_ids:
            raise SyntaxError(f"Setting ID ({setting_id}) missing from "
                              f"_setting_ids for page '{self!r}'")
        return self._setting_states[setting_id]

    def _mark_setting_changed(self, setting_id, is_changed):
        """Marks the setting with the specified ID as changed or unchanged.

        This method is intended to provide a convenient way to manage a page
        with several independent settings. It's just a wrapper around
        _mark_changed, you do not have to use it.

        If you do want to use it, _setting_ids needs to be populated with all
        setting IDs that you're going to pass to this method, or else a
        SyntaxError will be raised."""
        if setting_id not in self._setting_ids:
            raise SyntaxError(u'Setting ID (%s) missing from _setting_ids for '
                              u"page '%r'" % (setting_id, self))
        self._setting_states[setting_id] = is_changed
        self._mark_changed(self, any(self._setting_states.values()))

    def on_apply(self):
        """Called when the OK or Apply button on the settings dialog is
        clicked. Should apply whatever changes have been made on this page."""
        for setting_key in self._setting_states:
            self._setting_states[setting_key] = False
        self._mark_changed(self, False)

    def _rename_op(self, chosen_file, parent_dir, msg_title, msg):
        new_fstr = askText(self, msg, title=msg_title, default_txt=chosen_file)
        if not new_fstr or new_fstr == chosen_file:
            return False # user canceled or entered identical name
        new_fpath = parent_dir.join(new_fstr)
        old_fpath = parent_dir.join(chosen_file)
        if new_fpath.is_file():
            fstr = _('The chosen filename (%s) already exists. Do you want '
                     'to replace the file?') % new_fstr
            if not askYes(self, fstr, title=_('Name Conflict')):
                return False # don't want to replace it, so cancel
        try:
            env.shellMove({old_fpath: new_fpath}, parent=self)
            return True
        except (exception.CancelError, exception.SkipError):
            return False # user canceled

class _AScrollablePage(_ASettingsPage, ScrollableWindow): pass
class _AFixedPage(_ASettingsPage, PanelWin): pass

# Colors ----------------------------------------------------------------------
class ColorsPage(_AFixedPage): ##: _AScrollablePage breaks the color picker??
    """Color configuration page."""
    _keys_to_tabs = {
        u'mods': _(u'[Mods] %s'),
        u'screens': _(u'[Saves, Screens] %s'),
        u'installers': _(u'[Installers] %s'),
        u'ini': _(u'[INI Edits] %s'),
        u'tweak': _(u'[INI Edits] %s'),
        u'default': _(u'[All] %s'),
    }

    def __init__(self, parent, page_desc):
        super(ColorsPage, self).__init__(parent, page_desc)
        self.changes = {}
        #--DropDown
        def _display_text(k):
            return self._keys_to_tabs[k.split(u'.')[0]] % colorInfo[k][0]
        # Note the 'in colorInfo' to filter out colors that this game doesn't
        # actually use
        self._txt_key = {_display_text(x): x for x in colors if x in colorInfo}
        colored = sorted(self._txt_key, key=str.lower)
        combo_text = colored[0]
        choiceKey = self._txt_key[combo_text]
        self.comboBox = DropDown(self, value=combo_text, choices=colored)
        self.comboBox.on_combo_select.subscribe(lambda _sel: self.OnComboBox())
        #--Color Picker
        self.picker = ColorPicker(self, colors[choiceKey])
        #--Description
        help_ = colorInfo[choiceKey][1]
        self.textCtrl = TextArea(self, init_text=help_, editable=False)
        #--Buttons
        self.default = Button(self, _(u'Reset Color'))
        self.default.on_clicked.subscribe(self.OnDefault)
        self.defaultAll = RevertButton(self, _(u'Reset All Colors'))
        self.defaultAll.on_clicked.subscribe(self.OnDefaultAll)
        self.export_config = SaveAsButton(self, _(u'Export Colors...'))
        self.export_config.on_clicked.subscribe(self.OnExport)
        self.importConfig = OpenButton(self, _(u'Import Colors...'))
        self.importConfig.on_clicked.subscribe(self.OnImport)
        #--Events
        self.picker.on_color_picker_evt.subscribe(self.OnColorPicker)
        #--Layout
        VLayout(border=6, spacing=4, item_expand=True, items=[
            self._page_desc_label,
            HorizontalLine(self),
            HLayout(items=[
                (self.comboBox, LayoutOptions(expand=True, weight=1)),
                self.picker]),
            (self.textCtrl, LayoutOptions(weight=1)),
            HLayout(spacing=5, item_expand=True, items=[
                Stretch(), self.default, self.defaultAll, self.export_config,
                self.importConfig,
            ]),
        ]).apply_to(self)
        self.comboBox.set_focus()
        self.UpdateUIButtons()

    def GetColorKey(self):
        """Return balt.colors dict key for current combobox selection."""
        return self._txt_key[self.comboBox.get_value()]

    @staticmethod
    def UpdateUIColors():
        """Update the Bash Frame with the new colors"""
        with BusyCursor():
            for (className,title,panel) in tabInfo.values():
                if panel is not None:
                    panel.RefreshUIColors()

    def UpdateUIButtons(self):
        # Apply All and Default All
        for col_key, changed_color in list(self.changes.items()):
            if changed_color == colors[col_key]:
                del self.changes[col_key]
        anyChanged = bool(self.changes)
        allDefault = True
        for col_key, col_value in colors.items():
            if col_key in self.changes:
                color = self.changes[col_key]
            else:
                color = col_value
            default = color == Color(*settingDefaults[u'bash.colors'][col_key])
            if not default:
                allDefault = False
                break
        # Apply and Default
        col_key = self.GetColorKey()
        if col_key in self.changes:
            color = self.changes[col_key]
        else:
            color = colors[col_key]
        default = color == Color(*settingDefaults[u'bash.colors'][col_key])
        # Update the Buttons, DropDown, and ColorPicker
        if self._mark_changed:
            # If _mark_changed is None, then we're still in the construction
            # phase. The apply button is never going to be on without user
            # input, so this is fine
            self._mark_changed(self, is_changed=anyChanged)
        self.default.enabled = not default
        self.defaultAll.enabled = not allDefault
        self.picker.set_color(color)
        self.comboBox.set_focus_from_kb()

    def OnDefault(self):
        color_key = self.GetColorKey()
        newColor = Color(*settingDefaults[u'bash.colors'][color_key])
        self.changes[color_key] = newColor
        self.UpdateUIButtons()

    def OnDefaultAll(self):
        for col_key, col_value in colors.items():
            default = Color(*settingDefaults['bash.colors'][col_key])
            if col_value != default:
                self.changes[col_key] = default
        self.UpdateUIButtons()

    def on_apply(self):
        if self.changes:
            for key,newColor in self.changes.items():
                bass.settings[u'bash.colors'][key] = newColor.to_rgb_tuple()
                colors[key] = newColor
            self.UpdateUIButtons()
            self.UpdateUIColors()

    def OnExport(self):
        outDir = bass.dirs[u'patches']
        outDir.makedirs()
        #--File dialog
        outPath = FileSave.display_dialog(
            self, _(u'Export color configuration to:'), outDir,
            _(u'Colors.txt'), u'*.txt')
        if not outPath: return
        try:
            with outPath.open(u'w', encoding=u'utf-8') as out:
                for col_key, col_value in dict_sort(colors):
                    if col_key in self.changes:
                        color = self.changes[col_key]
                    else:
                        color = col_value
                    out.write(f'{col_key}: {color.to_rgb_tuple()}\n')
        except Exception as e:
            msg = _('An error occurred writing to %s:') % outPath.stail
            showError(self, msg + f'\n\n{e}')

    def OnImport(self):
        inDir = bass.dirs[u'patches']
        inDir.makedirs()
        #--File dialog
        inPath = FileOpen.display_dialog(self,
            _(u'Import color configuration from:'), inDir, _(u'Colors.txt'),
            u'*.txt')
        if not inPath: return
        try:
            with inPath.open(u'r', encoding=u'utf-8') as ins:
                for line in ins:
                    # Format validation
                    if u':' not in line:
                        continue
                    split = line.split(u':')
                    if len(split) != 2:
                        continue
                    color_key = split[0]
                    # Verify color exists
                    if color_key not in colors:
                        continue
                    # Parse the color, verify that it's actually valid
                    color_tup = tuple([int(c.strip()) for c
                                       in split[1].strip()[1:-1].split(u',')])
                    if len(color_tup) not in (3, 4):
                        continue
                    for value in color_tup:
                        if value < 0 or value > 255:
                            break
                    else:
                        # All checks passed, save it
                        if (color_key not in self.changes and (
                            color := Color(*color_tup)) == colors[color_key]):
                            continue # skip, identical to our current state
                        self.changes[color_key] = color
        except Exception as e:
            msg = _('An error occurred reading from %s:') % inPath.stail
            showError(self, msg + f'\n\n{e}')
        self.UpdateUIButtons()

    def OnComboBox(self):
        self.UpdateUIButtons()
        color_key = self.GetColorKey()
        self.textCtrl.text_content = colorInfo[color_key][1]

    def OnColorPicker(self):
        color_key = self.GetColorKey()
        newColor = self.picker.get_color()
        self.changes[color_key] = newColor
        self.UpdateUIButtons()

# Languages -------------------------------------------------------------------
class ConfigureEditorDialog(DialogWindow):
    """A dialog for configuring a localization file editor."""
    _min_size = _def_size = (400, 240)

    def __init__(self, parent):
        super(ConfigureEditorDialog, self).__init__(parent,
            title=_(u'Configure Editor'), icon_bundle=Resources.bashBlue,
            sizes_dict=balt.sizes)
        self._editor_location = TextField(self,
            init_text=bass.settings[u'bash.l10n.editor.path'])
        browse_editor_btn = ImageButton(self,
            balt.images['folder.16'].get_bitmap(),
            btn_tooltip=_('Open a file dialog to interactively choose the '
                          'editor binary.'))
        browse_editor_btn.on_clicked.subscribe(self._handle_browse)
        self._params_field = TextField(self,
            init_text=bass.settings[u'bash.l10n.editor.param_fmt'])
        ok_btn = OkButton(self)
        ok_btn.on_clicked.subscribe(self._handle_ok)
        VLayout(border=6, spacing=4, item_expand=True, items=[
            HBoxedLayout(self, title=_(u'Editor'), spacing=4, items=[
                (self._editor_location, LayoutOptions(expand=True, weight=1)),
                browse_editor_btn,
            ]),
            Spacer(12),
            VBoxedLayout(self, title=_(u'Parameters'), spacing=4, items=[
                (self._params_field, LayoutOptions(expand=True, weight=1)),
                Label(self, _(u"Note: '%s' will be replaced by the path "
                              u'to the localization file.')),
            ]),
            Stretch(), HLayout(spacing=5, items=[
                Stretch(), ok_btn, CancelButton(self),
            ]),
        ]).apply_to(self)

    def _handle_browse(self):
        """Opens a file dialog to choose the editor."""
        # Don't use mustExist, we want to show an error message for that below
        chosen_editor = FileOpen.display_dialog(self,
            title=_(u'Choose Editor'),
            defaultDir=os.environ.get(u'ProgramFiles', u''),
            wildcard=u'*.exe')
        if chosen_editor:
            self._editor_location.text_content = chosen_editor.s

    def _handle_ok(self):
        """Stores all changes that have been made."""
        bass.settings[u'bash.l10n.editor.path'] = \
            self._editor_location.text_content
        bass.settings[u'bash.l10n.editor.param_fmt'] = \
            self._params_field.text_content

##: Quite a bit of duplicate code with the Backups page here
class _LangDict(dict):
    __slots__ = ()
    def __missing__(self, key):
        return self.setdefault(key, key)
class LanguagePage(_AScrollablePage):
    """Change the language that the GUI is displayed in."""
    _internal_to_localized = _LangDict({
        u'zh_CN': _(u'Chinese (Simplified)') + u' (简体中文)',
        u'zh_TW': _(u'Chinese (Traditional)') + u' (繁体中文)',
        u'de_DE': _(u'German') + u' (Deutsch)',
        'pt_BR': _('Brazilian Portuguese') + ' (português brasileiro)',
        u'it_IT': _(u'Italian') + u' (italiano)',
        u'ja_JP': _(u'Japanese') + u' (日本語)',
        u'ru_RU': _(u'Russian') + u' (ру́сский язы́к)',
        u'en_US': _('American English') + ' (American English)',
    })
    _localized_to_internal = _LangDict(reverse_dict(_internal_to_localized))

    def __init__(self, parent, page_desc):
        super(LanguagePage, self).__init__(parent, page_desc)
        # Gather all localizations in the l10n directory
        all_langs = [f'{b}' for f in bass.dirs['l10n'].ilist()
                     if f.fn_ext == '.po'
                     and (b := f.fn_body)[-3:].lower() != 'new']
        # Insert English since there's no localization file for that
        if u'en_US' not in all_langs:
            all_langs.append(u'en_US')
        localized_langs = [self._internal_to_localized[l] for l in all_langs]
        # If the user has an unknown language active
        active_lang = self._internal_to_localized[u'en_US']
        for internal_name, localized_name in sorted(zip(
                all_langs, localized_langs), key=lambda x: x[1]):
            if self._is_active_lang(internal_name):
                active_lang = localized_name
                break
        # We can't compare the internal names to mark us as (un)changed since
        # we may be using a fallback language, so just store this for later
        # comparisons
        self._initial_lang = active_lang
        self._lang_dropdown = DropDown(self, value=active_lang,
            choices=localized_langs, dd_tooltip=_(
                'Changes the language that Wrye Bash will be displayed in.'))
        self._lang_dropdown.on_combo_select.subscribe(self._handle_lang_select)
        self._l10n_list = ListBox(self, isSort=True, isHScroll=True,
            onSelect=self._handle_select_l10n)
        configure_editor_btn = Button(self, _(u'Configure Editor...'),
            btn_tooltip=_(u'Choose the editor to use for editing '
                          u'localizations.'))
        configure_editor_btn.on_clicked.subscribe(self._handle_editor_cfg_btn)
        is_standalone_warning = Label(self,
            _(u'Note: You are using the standalone version and will not able '
              u'to dump localizations.'))
        is_standalone_warning.set_foreground_color(colors[u'default.warn'])
        is_standalone_warning.visible = bass.is_standalone
        dump_localization_btn = Button(self, _(u'Dump Localization...'),
            btn_tooltip=_(u'Generates an up-to-date version of the '
                          u'localization file for the currently active '
                          u'language (%s).') % active_lang.split(u' ')[0])
        dump_localization_btn.enabled = not bass.is_standalone
        dump_localization_btn.on_clicked.subscribe(self._dump_localization)
        self._edit_l10n_btn = OpenButton(self, _(u'Edit...'),
            btn_tooltip=_(u'Opens the selected localization in an editor. You '
                          u'can configure which editor to use via the '
                          u"'Configure Editor...' button."))
        self._edit_l10n_btn.on_clicked.subscribe(self._edit_l10n)
        self._rename_l10n_btn = Button(self, _(u'Rename...'),
            btn_tooltip=_(u'Rename the selected localization.'))
        self._rename_l10n_btn.on_clicked.subscribe(self._rename_l10n)
        # Populate the list and disable the context buttons by default
        self._populate_l10n_list()
        self._set_context_buttons(btns_enabled=False)
        VLayout(border=6, spacing=4, item_expand=True, items=[
            self._page_desc_label,
            HorizontalLine(self),
            HBoxedLayout(self, title=_(u'Change Language'),
                items=[self._lang_dropdown]),
            (VBoxedLayout(self, title=_(u'Manage Localizations'),
                spacing=4, item_expand=True, items=[
                    is_standalone_warning,
                    (HLayout(spacing=4, item_expand=True, items=[
                        (self._l10n_list, LayoutOptions(weight=1)),
                        VLayout(spacing=4, item_expand=True, items=[
                            configure_editor_btn, dump_localization_btn,
                            HorizontalLine(self), self._edit_l10n_btn,
                            self._rename_l10n_btn,
                        ]),
                    ]), LayoutOptions(weight=1)),
                ]), LayoutOptions(weight=1)),
        ]).apply_to(self)

    @property
    def _chosen_l10n(self):
        """Returns the localization file that the user has selected. Note that
        this will raise an error if no hidden icon has been selected, so it is
        only safe to call if that has already been checked."""
        return self._l10n_list.lb_get_selected_strings()[0]

    def _dump_localization(self):
        """Dumps out an up-to-date version of the current l10n file."""
        message = _(u'Generate Bash program translator file?') + u'\n\n' + _(
            u'This function is for translating Bash itself (NOT mods) into '
            u'non-English languages. For more info, '
            u'see the Internationalization section of the Advanced Readme.')
        if not balt.askContinue(self, message,
                u'bash.dump_translator.continue', _(u'Dump Localization')):
            return
        outPath = bass.dirs[u'l10n']
        with BusyCursor():
            outFile = dump_translator(outPath, bass.active_locale)
        showOk(self, _('Translation keys written to %s') % outFile,
               _('Dump Localization: %s') % outPath.stail)
        # Make the new localization show up in the list
        self._populate_l10n_list()
        # wx unselects here, so disable the context buttons
        self._set_context_buttons(btns_enabled=False)

    def _edit_l10n(self):
        """Opens the selected localization file in an editor."""
        chosen_editor = bass.settings[u'bash.l10n.editor.path']
        # First, verify that the chosen editor is valid
        if not chosen_editor:
            msg = _("No localization editor has been chosen. Please click "
                    "on 'Configure Editor' to set one up.")
            showError(self, msg, title=_('Invalid Editor'))
            return
        elif not os.path.isfile(chosen_editor):
            msg = _('The chosen editor (%(chosen_editor)s) does not exist or '
                    'is not a file.') % {'chosen_editor': chosen_editor}
            showError(self, msg, title=_('Invalid Editor'))
            return
        # Now we can move on to actually opening the editor
        selected_l10n = bass.dirs[u'l10n'].join(self._chosen_l10n)
        # Construct the final command and pass it to subprocess
        editor_arg_fmt = bass.settings[u'bash.l10n.editor.param_fmt']
        subprocess.Popen(
            [chosen_editor, *((a % selected_l10n if '%s' in a else a)
            for a in editor_arg_fmt.split(u' '))], close_fds=True)

    @staticmethod
    def _gather_l10n():
        """Returns a list of all localization files in the l10n directory."""
        return [f'{f}' for f in bass.dirs['l10n'].ilist() if f.fn_ext == '.po']

    def _handle_editor_cfg_btn(self):
        """Internal callback, called when the 'Configure Editor...' button has
        been clicked. Shows a dialog for configuring the editor."""
        ConfigureEditorDialog.display_dialog(self)

    def _handle_lang_select(self, selected_lang):
        """Internal callback, called when a new language has been selected.
        Marks this page as changed or not."""
        self._mark_changed(self, selected_lang != self._initial_lang)

    def _handle_select_l10n(self, _lb_dex, _item_text):
        """Internal callback, enables the context buttons once a localization
        has been selected."""
        self._set_context_buttons(btns_enabled=True)

    @staticmethod
    def _is_active_lang(internal_name):
        """Returns True if the specified language is currently active."""
        return bass.active_locale == internal_name

    @property
    def _l10n_dir(self):
        """Returns the directory in which localizations are stored."""
        return bass.dirs[u'l10n']

    def on_apply(self):
        super(LanguagePage, self).on_apply()
        selected_lang = self._lang_dropdown.get_value()
        if selected_lang != self._initial_lang:
            internal_name = self._localized_to_internal[selected_lang]
            ##: #26, our oldest open issue; This should be a
            # parameterless restart request, with us having saved the
            # new language to some 'early boot' info file
            self._request_restart(_(u'Language: %s') % selected_lang,
                [(u'--Language', internal_name)])

    def _populate_l10n_list(self):
        """Clears and repopulates the localization list."""
        self._l10n_list.lb_set_items(self._gather_l10n())

    def _rename_l10n(self):
        """Renames the currently selected localization file."""
        if not self._rename_op(
            self._chosen_l10n, self._l10n_dir, _(u'Rename Localization'),
            _(u'Please enter the new name for this localization file.')):
            return
        self._populate_l10n_list()
        # This is equivalent to removing the selected entry and adding a new
        # one, so we need to disable localization-specific buttons
        self._set_context_buttons(btns_enabled=False)

    def _set_context_buttons(self, btns_enabled):
        """Enables or disables all l10n-specific buttons."""
        for ctx_btn in (self._edit_l10n_btn, self._rename_l10n_btn):
            ctx_btn.enabled = btns_enabled

# Misc Appearance -------------------------------------------------------------
class MiscAppearancePage(_AFixedPage):
    """Appearance settings that don't fix anywhere else yet."""
    _setting_ids = {'alt_name_on', 'rev_icons_on'}

    def __init__(self, parent, page_desc):
        super().__init__(parent, page_desc)
        self._alt_name_checkbox = CheckBox(self,
            _('Use Alternate Wrye Bash Name'),
            chkbx_tooltip=_('Use an alternate display name for Wrye Bash '
                            'based on the game it is managing.'),
            checked=bass.settings['bash.useAltName'])
        self._alt_name_checkbox.on_checked.subscribe(self._on_alt_name)
        self._reverse_icons_checkbox = CheckBox(self, _('Reverse Icon Colors'),
            chkbx_tooltip=_('Replace black icons used by Wrye Bash with white '
                            'ones. Useful if you are using an OS theme that '
                            'makes those icons hard to see.'),
            checked=bass.settings['bash.use_reverse_icons'])
        self._reverse_icons_checkbox.on_checked.subscribe(self._on_rev_icons)
        VLayout(border=6, spacing=4, item_expand=True, items=[
            self._page_desc_label,
            HorizontalLine(self),
            self._alt_name_checkbox,
            self._reverse_icons_checkbox,
        ]).apply_to(self)

    def _on_alt_name(self, checked):
        self._mark_setting_changed('alt_name_on',
            checked != bass.settings['bash.useAltName'])

    def _on_rev_icons(self, checked):
        self._mark_setting_changed('rev_icons_on',
            checked != bass.settings['bash.use_reverse_icons'])

    def on_apply(self):
        # Use Alternate Wrye Bash Name
        if self._is_changed('alt_name_on'):
            new_alt_name = self._alt_name_checkbox.is_checked
            bass.settings['bash.useAltName'] = new_alt_name
            Link.Frame.set_bash_frame_title()
        # Reverse Icon Colors
        if self._is_changed('rev_icons_on'):
            new_rev_icons = self._reverse_icons_checkbox.is_checked
            bass.settings['bash.use_reverse_icons'] = new_rev_icons
            self._request_restart(_('Reverse Icon Colors'))
        super().on_apply()

# Status Bar ------------------------------------------------------------------
class StatusBarPage(_AScrollablePage):
    """Settings related to the status bar."""
    _setting_ids = {u'app_ver', u'icon_size', u'hidden_icons'}

    def __init__(self, parent, page_desc):
        super(StatusBarPage, self).__init__(parent, page_desc)
        # Used to retrieve the Link object for hiding/unhiding a button
        self._tip_to_links = {}
        # GUI/Layout definition
        self._show_app_ver_chk = CheckBox(self, _(u'Show App Version'),
            chkbx_tooltip=_(u'Show/hide version numbers for buttons on the '
                            u'status bar.'),
            checked=bass.settings[u'bash.statusbar.showversion'])
        self._show_app_ver_chk.on_checked.subscribe(self._handle_app_ver)
        self._icon_size_dropdown = DropDown(self,
            value=str(bass.settings[u'bash.statusbar.iconSize']),
            choices=['16', '24', '32'], dd_tooltip=_(
                'Sets the status bar icons to the selected size in pixels.'))
        self._icon_size_dropdown.on_combo_select.subscribe(
            self._handle_icon_size)
        ##: Create a variant of DoubleListBox that can actually show the icons
        self._icon_lists = DoubleListBox(self,
            left_label=_(u'Visible Buttons'), right_label=_(u'Hidden Buttons'),
            left_btn_tooltip=_(u'Make the selected button visible again.'),
            right_btn_tooltip=_(u'Hide the selected button.'))
        self._icon_lists.move_btn_callback = self._on_move_btn
        self._populate_icon_lists()
        VLayout(border=6, spacing=4, item_expand=True, items=[
            self._page_desc_label,
            HorizontalLine(self),
            VBoxedLayout(self, title=_(u'General'), item_border=3, spacing=6,
                items=[
                    self._show_app_ver_chk,
                    HLayout(spacing=6, items=[
                        Label(self, _(u'Icon Size:')),
                        self._icon_size_dropdown,
                    ]),
            ]),
            (HBoxedLayout(self, item_expand=True,
                title=_(u'Manage Hidden Buttons'), items=[self._icon_lists]),
             LayoutOptions(weight=1)),
        ]).apply_to(self)

    def _get_chosen_hidden_icons(self):
        """Returns a set of UIDs that have been chosen for hiding by the
        user."""
        return {self._tip_to_links[x].uid
                for x in self._icon_lists.right_items}

    def _handle_app_ver(self, checked):
        """Internal callback, called when the version checkbox is changed."""
        self._mark_setting_changed(u'app_ver',
            checked != bass.settings[u'bash.statusbar.showversion'])

    def _handle_icon_size(self, new_selection):
        """Internal callback, called when the icon size dropdown is changed."""
        self._mark_setting_changed(u'icon_size',
            int(new_selection) != bass.settings[u'bash.statusbar.iconSize'])

    def _link_by_uid(self, link_uid):
        """Returns the status bar Link with the specified UID."""
        for link_candidate in self._tip_to_links.values():
            if link_candidate.uid == link_uid:
                return link_candidate
        return None

    def on_apply(self):
        # Note we skip_refresh all status bar changes in order to do them all
        # at once at the end
        # Show App Version
        if self._is_changed(u'app_ver'):
            bass.settings[u'bash.statusbar.showversion'] ^= True
            for button in BashStatusBar.all_sb_links.values():
                button.set_sb_button_tooltip()
            if BashStatusBar.obseButton.button_state:
                BashStatusBar.obseButton.UpdateToolTips()
            # Will change tooltips, so need to repopulate these
            self._populate_icon_lists()
        # Icon Size
        icon_size_changed = self._is_changed(u'icon_size')
        if icon_size_changed:
            bass.settings[u'bash.statusbar.iconSize'] = \
                int(self._icon_size_dropdown.get_value())
            Link.Frame.statusBar.UpdateIconSizes(skip_refresh=True)
        # Hidden Icons
        hidden_icons_changed = self._is_changed(u'hidden_icons')
        if hidden_icons_changed:
            # Compare old and new hidden, then hide the newly hidden buttons
            # and unhide the newly visible ones
            old_hidden = bass.settings[u'bash.statusbar.hide']
            new_hidden = self._get_chosen_hidden_icons()
            hidden_added = new_hidden - old_hidden
            hidden_removed = old_hidden - new_hidden
            for to_hide in hidden_added:
                Link.Frame.statusBar.HideButton(
                    self._link_by_uid(to_hide).gButton, skip_refresh=True)
            for to_unhide in hidden_removed:
                Link.Frame.statusBar.UnhideButton(self._link_by_uid(to_unhide),
                    skip_refresh=True)
        # Perform a single update of the status bar if needed
        if hidden_icons_changed or icon_size_changed:
            Link.Frame.statusBar.refresh_status_bar(
                refresh_icon_size=icon_size_changed)
        super(StatusBarPage, self).on_apply()

    def _on_move_btn(self):
        """Mark our setting as changed if the hidden icons list no longer
        matches the list of icons that are currently hidden."""
        self._mark_setting_changed(u'hidden_icons',
             self._get_chosen_hidden_icons() != bass.settings[
                 u'bash.statusbar.hide'])

    def _populate_icon_lists(self):
        """Clears and repopulates the two icon lists."""
        ##: Here be dragons, of the tooltip-related kind
        self._tip_to_links.clear()
        hide = bass.settings[u'bash.statusbar.hide']
        hidden = []
        visible = []
        for link_uid, link in BashStatusBar.all_sb_links.items():
            if not link.IsPresent() or not link.canHide: continue
            button = link.gButton
            # Get a title for the hidden button
            if button:
                # If the wx.Button object exists (it was hidden this
                # session), use the tooltip from it
                tip_ = button.tooltip
            else:
                # If the link is an _App_Button, it will have a
                # 'sb_button_tip' attribute
                tip_ = getattr(link, u'sb_button_tip', None) # YAK YAK YAK
            if tip_ is None:
                # No good, use its uid as a last resort
                tip_ = link_uid
            target_link_list = hidden if link_uid in hide else visible
            target_link_list.append(tip_)
            self._tip_to_links[tip_] = link
        self._icon_lists.left_items = visible
        self._icon_lists.right_items = hidden

# Backups ---------------------------------------------------------------------
class BackupsPage(_AFixedPage):
    """Create, manage and restore backups."""
    def __init__(self, parent, page_desc):
        super(BackupsPage, self).__init__(parent, page_desc)
        self._backup_list = ListBox(self, isSort=True, isHScroll=True,
            onSelect=self._handle_backup_selected)
        save_settings_btn = SaveButton(self, _(u'Save Data'),
            btn_tooltip=_(u"Save all of Wrye Bash's settings/data now."))
        save_settings_btn.on_clicked.subscribe(self._save_settings)
        new_backup_btn = Button(self, _(u'New Backup...'),
            btn_tooltip=_(u"Backup all of Wrye Bash's settings/data to an "
                          u'archive file.'))
        new_backup_btn.on_clicked.subscribe(self._new_backup)
        set_backups_dir_btn = Button(self, _('Set Backups Directory...'),
            btn_tooltip=_('Select the directory containing your backups.'))
        set_backups_dir_btn.on_clicked.subscribe(self._set_backup_dir)
        self.restore_backup_btn = Button(self, _(u'Restore...'),
            btn_tooltip=_(u"Restore all of Wrye Bash's settings/data from the "
                          u'selected backup.'))
        self.restore_backup_btn.on_clicked.subscribe(self._restore_backup)
        self.rename_backup_btn = Button(self, _(u'Rename...'),
            btn_tooltip=_(u'Rename the selected backup archive.'))
        self.rename_backup_btn.on_clicked.subscribe(self._rename_backup)
        self.delete_backup_btn = Button(self, _(u'Delete...'),
            btn_tooltip=_(u'Delete the selected backup archive.'))
        self.delete_backup_btn.on_clicked.subscribe(self._delete_backup)
        # These start out disabled, because nothing is selected by default
        self._set_context_buttons(btns_enabled=False)
        self._populate_backup_list()
        VLayout(border=6, spacing=4, item_expand=True, items=[
            self._page_desc_label,
            HorizontalLine(self),
            (HLayout(spacing=4, item_expand=True, items=[
                (self._backup_list, LayoutOptions(weight=1)),
                VLayout(item_expand=True, spacing=4, items=[save_settings_btn,
                    new_backup_btn, set_backups_dir_btn, HorizontalLine(self),
                    self.restore_backup_btn, self.rename_backup_btn,
                    self.delete_backup_btn,
                ]),
            ]), LayoutOptions(weight=1)),
        ]).apply_to(self)

    @property
    def _backup_dir(self):
        """Returns the directory into which backups will be saved."""
        return bass.settings[u'bash.backupPath'] or bass.dirs[u'modsBash']

    @property
    def _chosen_backup(self):
        """Returns the name of the backup that is currently selected by the
        user. Note that this will raise an error if no backup has been selected
        yet, so it is only safe to call if that has already been checked."""
        return self._backup_list.lb_get_selected_strings()[0]

    def _delete_backup(self):
        """Deletes the currently selected backup."""
        settings_file = self._backup_dir.join(self._chosen_backup)
        try:
            env.shellDelete([settings_file], parent=self, ask_confirm=True,
                recycle=True)
        except (exception.CancelError, exception.SkipError): pass
        finally:
            self._populate_backup_list()
            self._set_context_buttons(btns_enabled=False)

    def _handle_backup_selected(self, _lb_dex, _item_text):
        """Internal callback, enables the backup-specific buttons as soon as a
        backup has been selected. There is no way to unselect besides removing
        the selected entry, which is handled in _delete_backup and
        _populate_backup_list."""
        self._set_context_buttons(btns_enabled=True)

    @balt.conversation
    def _set_backup_dir(self):
        backups_dir = DirOpen.display_dialog(self,
            title=_('Set Backups Directory'), defaultPath=self._backup_dir)
        if not backups_dir: return
        bass.settings[u'bash.backupPath'] = backups_dir
        self._populate_backup_list()

    @balt.conversation
    def _new_backup(self):
        """Saves the current settings and data to create a new backup."""
        with BusyCursor(): Link.Frame.SaveSettings()
        settings_file = FileSave.display_dialog(self,
            title=_(u'Backup Bash Settings'), defaultDir=self._backup_dir,
            wildcard=u'*.7z', defaultFile=barb.BackupSettings.backup_filename(
                bush.game.bak_game_name))
        if not settings_file: return
        with BusyCursor():
            backup = barb.BackupSettings(
                settings_file, bush.game.bak_game_name,
                bush.game.my_games_name, bush.game.bash_root_prefix,
                bush.game.mods_dir)
        try:
            with BusyCursor(): backup.backup_settings(balt)
        except exception.StateError:
            deprint(u'Backup settings failed', traceback=True)
            backup.warn_message(balt)
        finally:
            self._populate_backup_list()

    def _populate_backup_list(self):
        """Clears and repopulates the backups list."""
        all_backups = [x for x in self._backup_dir.ilist() if barb.is_backup(x)]
        self._backup_list.lb_set_items(all_backups)
        if not all_backups:
            # If there are no more backups left, we need to disable all
            # backup-specific buttons again
            self._set_context_buttons(btns_enabled=False)

    def _rename_backup(self):
        """Renames the currently selected backup."""
        if not self._rename_op(
            self._chosen_backup, self._backup_dir, _(u'Rename Backup'),
            _(u'Please enter the new name for this backup.')):
            return
        self._populate_backup_list()
        # This is equivalent to removing the selected entry and adding a new
        # one, so we need to disable backup-specific buttons
        self._set_context_buttons(btns_enabled=False)

    @balt.conversation
    def _restore_backup(self):
        """Restores the currently selected backup."""
        if not askYes(self, '\n\n'.join([
            _("Are you sure you want to restore your Bash settings from '%s'?"
              ) % self._chosen_backup,
            _(u'This will force a restart of Wrye Bash once your settings are '
              u'restored.')]), _(u'Restore Bash Settings?')):
            return
        # former may be None
        settings_file = self._backup_dir.join(self._chosen_backup)
        with BusyCursor():
            restore_ = barb.RestoreSettings(settings_file)
        backup_dir = None
        restarting = False
        try:
            with BusyCursor():
                backup_dir = restore_.extract_backup()
            error_msg, error_title = restore_.incompatible_backup_error(
                bush.game.bak_game_name)
            if error_msg:
                showError(self, error_msg, error_title)
                return
            error_msg, error_title = restore_.incompatible_backup_warn()
            if error_msg and not askWarning(self, error_msg, error_title):
                return
            restarting = True
            m = [_('Your Bash settings have been successfully extracted.'), _(
                'Backup Path: ') + settings_file.s, '', _('Before the '
                'settings can take effect, Wrye Bash must restart.'),
                _('Click OK to restart now.')]
            showInfo(self, '\n'.join(m), _('Bash Settings Extracted'))
            try: # we currently disallow backup and restore on the same boot
                bass.sys_argv.remove(u'--backup')
            except ValueError:
                pass
            Link.Frame.Restart([u'--restore'], [u'--filename', backup_dir.s])
        except (exception.BoltError, NotImplementedError) as e:
            deprint(u'Restore settings failed:', traceback=True)
            restore_.warn_message(balt, e.message)
        finally:
            if not restarting and backup_dir is not None:
                barb.RestoreSettings.remove_extract_dir(backup_dir)

    @staticmethod
    def _save_settings():
        """Saves all settings and data right now."""
        with BusyCursor():
            Link.Frame.SaveSettings()
        showOk(Link.Frame,
               _('Wrye Bash settings files were successfully saved.'),
               _('Save Settings'))

    def _set_context_buttons(self, btns_enabled):
        """Enables or disables all backup-specific buttons."""
        for ctx_btn in (self.restore_backup_btn, self.rename_backup_btn,
                        self.delete_backup_btn):
            ctx_btn.enabled = btns_enabled

# Confirmations ---------------------------------------------------------------
class ConfirmationsPage(_AFixedPage):
    """Manage the consent you gave to 'Don't show this again' checkboxes."""
    # Actions to take when dropping files onto the Installers tab
    _action_to_label = {
        None:    _(u'Ask every time'),
        u'COPY': _(u'Copy'),
        u'MOVE': _(u'Move'),
    }
    _label_to_action = reverse_dict(_action_to_label)
    ##: Maybe hide some of these per game? E.g. Nvidia Fog will never be
    # relevant outside of Oblivion/Nehrim, while Add/Remove ESL Flag makes no
    # sense for non-SSE/FO4 games
    ##: We should also enforce that a key is in here before allowing
    # askContinue to proceed, so that we won't ever forget to add one here (or
    # come up with a better way to store these)
    _confirmations = {
        _(u'[INI Edits] Applying an INI tweak'):
            u'bash.iniTweaks.continue',
        _(u'[Installers, Screenshots] Opening a lot of items'):
            u'bash.maxItemsOpen.continue',
        _('[Installers] Exporting package order'):
            'bash.installers.export_order.continue',
        _('[Installers] Installing unconfigured complex packages'):
            'bash.installers.nothing_installed.continue',
        _("[Installers] Opening a mod's page at the %(target_nexus_name)s") % {
            'target_nexus_name': bush.game.nexusName}:
            bush.game.nexusKey,
        _(u"[Installers] Opening a mod's page at TES Alliance"):
            u'bash.installers.openTESA.continue',
        _('[Installers] Overwriting a package via drag and drop'):
            'bash.installers.onDropFiles.overwrite_pkg.continue',
        _('[Installers] Overwriting a BCF via drag and drop'):
            'bash.installers.onDropFiles.overwrite_conv.continue',
        _(u'[Installers] Searching for a mod on Google'):
            u'bash.installers.opensearch.continue',
        _(u'[Installers] Trying to reorder installers, but Install Order '
          u'column not selected'):
            u'bash.installers.dnd.column.continue',
        _(u'[Masters] Editing or updating a master list'):
            u'bash.masters.update.continue',
        _(u'[Mods] Adding or removing the ESL flag from a plugin'):
            u'bash.flipToEslp.continue',
        _(u'[Mods] Adding or removing the ESM flag from a plugin'):
            u'bash.flipToEsmp.continue',
        _(u"[Mods] Adding or removing the ESM flag from a plugin's masters"):
            u'bash.flipMasters.continue',
        _(u'[Mods] Applying the Nvidia Fog Fix'):
            u'bash.cleanMod.continue',
        _(u"[Mods] Changing a plugin's version to 0.8"):
            u'bash.setModVersion.continue',
        _(u'[Mods] Exporting NPC levels to a text file'):
            u'bash.actorLevels.export.continue',
        _(u'[Mods] Importing groups from a text file'):
            u'bash.groups.import.continue',
        _(u'[Mods] Locking or unlocking the load order'):
            u'bash.load_order.lock.continue',
        _(u'[Mods] Removing world orphans'):
            u'bash.removeWorldOrphans.continue',
        _("[Mods] Renaming a plugin to something that %(game_name)s can't "
          'load') % {'game_name': bush.game.display_name}:
            'bash.rename.isBadFileName.continue',
        _(u'[Mods] Reordering plugins by name'):
            u'bash.sortMods.continue',
        _(u"[Mods] Replacing a plugin's FormIDs based on a text file"):
            u'bash.formIds.replace.continue',
        _(u'[Mods] Resetting groups to default ones'):
            u'bash.groups.reset.continue',
        _(u'[Mods] Synchronizing groups to currently active ones'):
            u'bash.groups.sync.continue',
        _(u"[Mods] Trying to activate plugins that can't be activated"):
            u'bash.mods.dnd.illegal_activation.continue',
        _(u"[Mods] Trying to deactivate plugins that can't be deactivated"):
            u'bash.mods.dnd.illegal_deactivation.continue',
        _(u'[Mods] Trying to reorder plugins, but Load Order column not '
          u'selected'):
            u'bash.mods.dnd.column.continue',
        _(u"[Mods] Trying to reorder plugins that can't be reordered"):
            u'bash.mods.dnd.pinned.continue',
        _(u"[Mods] Using Decompile All to undo a 'Recompile All'"):
            u'bash.decompileAll.continue',
        _(u'[Saves] Disabling a save'):
            u'bash.saves.askDisable.continue',
        _(u'[Saves] Updating NPC levels in a save based on current plugins'):
            u'bash.updateNpcLevels.continue',
        _(u'[Settings] Dumping a new translation file'):
            u'bash.dump_translator.continue',
        _(u'[Settings] Switching the currently managed game'):
            u'bash.switch_games_warning.continue',
    }
    # The Import links are highly formulaic, so we just generate these here
    for k, v in {_(u'Editor IDs'):   u'editorIds',
                 _(u'Ingredients'):  u'Ingredient',
                 _(u'Names'):        u'fullNames',
                 _(u'NPC Levels'):   u'actorLevels',
                 _(u'Prices'):       u'prices',
                 _(u'Relations'):    u'factionRelations',
                 _(u'Scripts'):      u'scripts',
                 _(u'Sigil Stones'): u'SigilStone',
                 _(u'Spells'):       u'SpellRecords',
                 _(u'Stats'):        u'stats'}.items():
        _confirmations[_(u'[Mods] Importing %s from a text '
                         u'file') % k] = u'bash.%s.import.continue' % v
    # Detect parentheses in the confirmation names, which will cause problems
    # when we go to strip out the internal keys
    for conf_key in _confirmations:
        if '(' in conf_key or ')' in conf_key:
            raise SyntaxError(f'_confirmations keys may not contain '
                              f'parentheses (offending key: {conf_key!r}')
    _setting_ids = {u'confirmed_prompts', u'drop_action', u'internal_keys'}

    def __init__(self, parent, page_desc):
        super(ConfirmationsPage, self).__init__(parent, page_desc)
        self._show_keys_checkbox = CheckBox(self, _(u'Show Internal Keys'),
            chkbx_tooltip=_(u'If checked, show the internal key Wrye Bash '
                            u'uses to store these settings as well.'),
            checked=bass.settings[u'bash.show_internal_keys'])
        self._show_keys_checkbox.on_checked.subscribe(self._on_show_keys)
        self._confirmation_list = CheckListBox(self, isSort=True,
            isHScroll=True)
        self._confirmation_list.on_box_checked.subscribe(self._on_check_conf)
        self._file_drop_dropdown = DropDown(self, value=self._saved_action,
            choices=sorted(self._label_to_action), dd_tooltip=_(
                'Choose what to do with files that are dropped onto the '
                'Installers tab.'))
        self._file_drop_dropdown.on_combo_select.subscribe(self._on_file_drop)
        self._populate_confirmations()
        VLayout(border=6, spacing=4, item_expand=True, items=[
            self._page_desc_label,
            HorizontalLine(self),
            HLayout(spacing=6, items=[
                Label(self, _(u'Drop Action:')), self._file_drop_dropdown,
            ]),
            HLayout(items=[
                Label(self, _(u'Unchecking an entry below will reenable that '
                              u'prompt and vice versa.')),
                Stretch(), self._show_keys_checkbox,
            ]),
            (self._confirmation_list, LayoutOptions(weight=1)),
        ]).apply_to(self)

    def _on_check_conf(self, _lb_selection_dex):
        self._mark_setting_changed(u'confirmed_prompts',
            self._selected_confirmations != self._saved_confirmations)

    def _on_file_drop(self, selected_action):
        self._mark_setting_changed(u'drop_action',
            selected_action != self._saved_action)

    def _on_show_keys(self, checked):
        def mark_internal_keys(ik_checked):
            self._mark_setting_changed(u'internal_keys',
                ik_checked != bass.settings[u'bash.show_internal_keys'])
        # Make sure we don't throw away changes the user made
        msg = _('Activating this setting will discard all changes you have '
                'made below. Are you sure you want to proceed?')
        if self._is_changed('confirmed_prompts') and not askYes(
                self, msg, title=_('Warning: Unapplied Changes')):
            # User chose to cancel, reset the checkbox for visual consistency
            self._show_keys_checkbox.is_checked = not checked
            mark_internal_keys(not checked)
            return
        mark_internal_keys(checked)
        # Repopulating the list obviously means we'll have no user changes left
        # anymore, so mark this False
        self._mark_setting_changed(u'confirmed_prompts', False)
        self._populate_confirmations()

    def _populate_confirmations(self):
        """Repopulates the list of confirmations and ticks them according to
        bass.settings."""
        sorted_confs = sorted(self._confirmations.items(),
                              key=lambda x: x[0])
        if self._show_keys_checkbox.is_checked:
            conf_names = [f'{m} ({k})' for m, k in sorted_confs]
        else:
            conf_names = [c[0] for c in sorted_confs]
        self._confirmation_list.lb_set_items(conf_names)
        for i, conf_key in enumerate([c[1] for c in sorted_confs]):
            self._confirmation_list.lb_check_at_index(i, bass.settings.get(
                conf_key, False))

    @property
    def _saved_action(self):
        """Returns the label for the drop action saved in bass.settings."""
        return self._action_to_label[bass.settings[
            u'bash.installers.onDropFiles.action']]

    @property
    def _saved_confirmations(self):
        """Returns a dict mapping confirmation descriptions to booleans
        indicating whether or not that entry is active in bass.settings."""
        return {conf_name: bass.settings.get(conf_key, False)
                for conf_name, conf_key in self._confirmations.items()}

    @property
    def _selected_confirmations(self):
        """Returns a dict mapping confirmation descriptions to booleans
        indicating whether or not the user checked that entry."""
        # Cut off the internal key extension that may be present
        clist = self._confirmation_list
        return {clist.lb_get_str_item_at_index(i).split('(')[0].strip():
                    clist.lb_is_checked_at_index(i)
                for i in range(clist.lb_get_items_count())}

    def on_apply(self):
        if self._is_changed(u'confirmed_prompts'):
            conf_states = {self._confirmations[conf_name]: conf_checked
                           for conf_name, conf_checked
                           in self._selected_confirmations.items()}
            for conf_key in self._confirmations.values():
                if bass.settings.get(conf_key, False) != conf_states[conf_key]:
                    bass.settings[conf_key] = conf_states[conf_key]
        if self._is_changed(u'drop_action'):
            new_drop_act = self._label_to_action[
                self._file_drop_dropdown.get_value()]
            bass.settings[u'bash.installers.onDropFiles.action'] = new_drop_act
        if self._is_changed(u'internal_keys'):
            new_internal_keys = self._show_keys_checkbox.is_checked
            bass.settings[u'bash.show_internal_keys'] = new_internal_keys
        super(ConfirmationsPage, self).on_apply()

# General ---------------------------------------------------------------------
class GeneralPage(_AScrollablePage):
    """Houses settings that didn't fit anywhere else."""
    _all_encodings = {
        _(u'Automatic'): None,
        _(u'Chinese (Simplified)'): u'gbk',
        _(u'Chinese (Traditional)'): u'big5',
        _(u'Russian'): u'cp1251',
        _(u'Japanese (Shift_JIS)'): u'cp932',
        _(u'UTF-8'): u'utf-8',
        _(u'Western European (English, French, German, etc)'): u'cp1252',
    }
    _encodings_reverse = reverse_dict(_all_encodings)
    _global_menu_options = {
        _('Both'): 0,
        _('Global Menu Only'): 1,
        _('Column Menu Only'): 2,
    }
    _gm_reverse = reverse_dict(_global_menu_options)
    _setting_ids = {'global_menu_state', 'res_scroll_on', 'managed_game',
                    'plugin_encoding', 'update_check_enabled',
                    'update_check_cooldown', 'uac_restart', 'wb_temp_dir'}

    def __init__(self, parent, page_desc):
        super(GeneralPage, self).__init__(parent, page_desc)
        self._managed_game = DropDown(self,
            value=bush.game.unique_display_name,
            choices=sorted(bush.foundGames), dd_tooltip=_(
                'Changes which game Wrye Bash is managing.'))
        self._managed_game.on_combo_select.subscribe(self._on_managed_game)
        self._plugin_encoding = DropDown(self, value=self._current_encoding,
            choices=sorted(self._all_encodings), dd_tooltip=_(
                'Changes the encoding Wrye Bash will use to read and write '
                'plugins.'))
        self._plugin_encoding.on_combo_select.subscribe(self._on_plugin_enc)
        # Update checking-related things begin here
        ##: Change to WrappingLabel after inf-190-bye-listboxes?
        uc_error_label = Label(self, _("'requests' not installed, update "
                                       "checking disabled."))
        uc_error_label.set_foreground_color(balt.colors['default.warn'])
        uc_error_label.visible = not can_check_updates
        update_check_on = bass.settings['bash.update_check.enabled']
        self._update_check_enable = CheckBox(self, _('Check on Startup'),
            chkbx_tooltip=_('Whether or not Wrye Bash should check to see if '
                            'a newer version is available when it is '
                            'launched.'), checked=update_check_on)
        self._update_check_enable.on_checked.subscribe(self._on_update_checked)
        self._update_check_enable.enabled = can_check_updates
        self._update_check_cooldown = Spinner(self,
            spin_tip=_('Do not check for updates again until this many hours '
                       'have elapsed since the last check. Set to 0 to '
                       'check on every startup.'),
            max_num=24 * 7 * 4, # Four weeks as maximum, high values break wx
            initial_num=bass.settings['bash.update_check.cooldown'])
        self._update_check_cooldown.on_spun.subscribe(self._on_update_cooldown)
        self._uc_cooldown_label = Label(self, _('Cooldown (hours):'))
        # Disable both of these immediately if update checking is disabled
        uc_cooldown_enable = can_check_updates and update_check_on
        self._update_check_cooldown.enabled = uc_cooldown_enable
        self._uc_cooldown_label.enabled = uc_cooldown_enable
        check_now_btn = Button(self, _('Check for Updates'),
            btn_tooltip=_('Check for Wrye Bash updates right now.'))
        check_now_btn.on_clicked.subscribe(self._on_check_now)
        check_now_btn.enabled = can_check_updates
        self._global_menu_dropdown = DropDown(self,
            value=self._gm_reverse[bass.settings['bash.global_menu']],
            choices=sorted(self._global_menu_options),
            dd_tooltip=_('Choose whether only the global menu, only the '
                         'column header menus, or both should be enabled.'))
        self._global_menu_dropdown.on_combo_select.subscribe(
            self._on_global_menu)
        global_menu_label = Label(self, _('Global or Column Menu:'))
        # Hide the whole section on Linux - see refresh_global_menu_visibility
        if os_name != 'nt':
            global_menu_label.visible = False
            self._global_menu_dropdown.visible = False
        self._restore_scroll_checkbox = CheckBox(
            self, _(u'Restore Scroll Positions on Start'),
            chkbx_tooltip=_("Remember where you left off last time and "
                            "scroll back down to that plugin/save/etc. on "
                            "startup. May cause a moderate slowdown in "
                            "Wrye Bash's boot process if you have a very "
                            "large number of plugins/saves/etc."),
            checked=bass.settings[u'bash.restore_scroll_positions'])
        self._restore_scroll_checkbox.on_checked.subscribe(self._on_res_scroll)
        ##: Doesn't really belong here, but couldn't think of a better place
        self._uac_restart_checkbox = CheckBox(self, _(u'Administrator Mode'),
            chkbx_tooltip=_(u'Restart Wrye Bash with administrator '
                            u'privileges.'))
        self._uac_restart_checkbox.on_checked.subscribe(self._on_uac_restart)
        self._uac_restart_checkbox.visible = env.is_uac()
        ##: This should be on its own page for configuring all kinds of paths,
        # see #572
        self._temp_folder_path = TextField(self,
            init_text=bass.settings['bash.temp_dir'])
        self._temp_folder_path.on_text_changed.subscribe(
            self._on_temp_folder_change)
        browse_temp_folder_btn = ImageButton(self,
            balt.images['folder.16'].get_bitmap(),
            btn_tooltip=_('Open a file dialog to interactively choose the '
                          'path at which Wrye Bash will store temporary '
                          'files.'))
        browse_temp_folder_btn.on_clicked.subscribe(
            self._on_temp_folder_browse)
        reset_temp_folder_btn = ImageButton(self,
            balt.images['reset.16'].get_bitmap(),
            btn_tooltip=_('Reset the path at which Wrye Bash will store '
                          'temporary files back to its default value.'))
        reset_temp_folder_btn.on_clicked.subscribe(self._on_temp_folder_reset)
        VLayout(border=6, spacing=4, item_expand=True, items=[
            self._page_desc_label,
            HorizontalLine(self),
            VBoxedLayout(self, title=_(u'Game'), spacing=6, items=[
                HLayout(spacing=6, items=[
                    Label(self, _(u'Managed Game:')), self._managed_game,
                ]),
                HLayout(spacing=6, items=[
                    Label(self, _(u'Plugin Encoding:')), self._plugin_encoding,
                ]),
            ]),
            VBoxedLayout(self, title=_('Updates'), spacing=6, items=[
                uc_error_label,
                HLayout(spacing=6, item_v_align=CENTER, items=[
                    self._update_check_enable,
                    (VerticalLine(self), LayoutOptions(expand=True)),
                    self._uc_cooldown_label, self._update_check_cooldown,
                ]),
                check_now_btn,
            ]),
            HBoxedLayout(self, _('Temporary Folder'), spacing=4,
                item_expand=True, items=[
                    (self._temp_folder_path, LayoutOptions(weight=1)),
                    browse_temp_folder_btn,
                    reset_temp_folder_btn,
            ]),
            VBoxedLayout(self, title=_(u'Miscellaneous'), spacing=6, items=[
                HLayout(spacing=6, items=[
                    global_menu_label,
                    self._global_menu_dropdown,
                ]),
                self._restore_scroll_checkbox,
                self._uac_restart_checkbox,
            ]),
        ]).apply_to(self)

    @property
    def _current_encoding(self):
        return self._encodings_reverse[bass.settings[u'bash.pluginEncoding']]

    def _on_global_menu(self, menu_label: str):
        new_gm_state = self._global_menu_options[menu_label]
        self._mark_setting_changed('global_menu_state',
            new_gm_state != bass.settings['bash.global_menu'])

    def _on_res_scroll(self, checked: bool):
        self._mark_setting_changed('res_scroll_on',
            checked != bass.settings['bash.restore_scroll_positions'])

    def _on_managed_game(self, new_game: str):
        self._mark_setting_changed(u'managed_game',
            new_game != bush.game.unique_display_name)

    def _on_plugin_enc(self, new_enc: str):
        self._mark_setting_changed(u'plugin_encoding',
            new_enc != self._current_encoding)

    def _on_update_checked(self, checked: bool):
        self._mark_setting_changed('update_check_enabled',
            checked != bass.settings['bash.update_check.enabled'])
        # Also disable the cooldown info if the update check is disabled
        self._update_check_cooldown.enabled = checked
        self._uc_cooldown_label.enabled = checked

    def _on_update_cooldown(self, new_cooldown: int):
        self._mark_setting_changed('update_check_cooldown',
            new_cooldown != bass.settings['bash.update_check.cooldown'])

    def _on_check_now(self):
        with BusyCursor():
            newer_version = UpdateChecker().check_for_updates(force_check=True)
        if newer_version is not None:
            if newer_version.wb_version > LooseVersion(bass.AppVersion):
                UpdateNotification.display_dialog(self, newer_version)
            else:
                showInfo(self, _('You are already using the newest version of '
                                 'Wrye Bash, version %(wb_version)s.') % {
                    'wb_version': bass.AppVersion},
                    title=_('No Newer Version Available'))
        else:
            showError(self, _('Failed to contact GitHub for update checking. '
                              'Check your Internet connection.'),
                title=_('Failed To Check for Updates'))

    def _on_temp_folder_change(self, new_temp_dir: str):
        self._mark_setting_changed('wb_temp_dir',
            new_temp_dir != bass.settings['bash.temp_dir'])

    def _on_temp_folder_browse(self):
        chosen_temp_dir = DirOpen.display_dialog(self,
            title=_('Choose Temporary Folder'),
            defaultPath=bass.settings['bash.temp_dir'],
            create_dir=True)
        if chosen_temp_dir:
            self._temp_folder_path.text_content = chosen_temp_dir.s

    def _on_temp_folder_reset(self):
        self._temp_folder_path.text_content = default_global_temp_dir()

    def _on_uac_restart(self, checked: bool):
        self._mark_setting_changed(u'uac_restart', checked)

    def on_apply(self):
        # Managed Game
        if self._is_changed(u'managed_game') and balt.askContinue(self,
                    _(u'Switching games this way will simply relaunch this '
                      u'Wrye Bash installation with the -o command line '
                      u'switch.') + u'\n\n' +
                    _(u'That means manually added application launchers in '
                      u'the status bar will not change after switching.'),
                    u'bash.switch_games_warning.continue'):
            chosen_game = self._managed_game.get_value()
            ##: The [0] here is ugly, doesn't allow changing WS variations
            self._request_restart(
                _(u'Managed Game: %s') % chosen_game,
                [(u'--oblivionPath', bush.game_path(chosen_game)[0].s)])
        # Plugin Encoding
        if self._is_changed(u'plugin_encoding'):
            chosen_encoding = self._plugin_encoding.get_value()
            internal_encoding = self._all_encodings[chosen_encoding]
            bass.settings[u'bash.pluginEncoding'] = internal_encoding
            bolt.pluginEncoding = internal_encoding
            # Request a restart so that alrady loaded plugins can be reparsed
            self._request_restart(_(u'Plugin Encoding: %s') % chosen_encoding)
        # Check on Startup
        if self._is_changed('update_check_enabled'):
            new_uc_on = self._update_check_enable.is_checked
            bass.settings['bash.update_check.enabled'] = new_uc_on
        # Cooldown (hours)
        if self._is_changed('update_check_cooldown'):
            new_cooldown = self._update_check_cooldown.spinner_value
            bass.settings['bash.update_check.cooldown'] = new_cooldown
        # Temporary Folder
        if self._is_changed('wb_temp_dir'):
            new_temp_dir = self._temp_folder_path.text_content
            bass.settings['bash.temp_dir'] = new_temp_dir
            self._request_restart(_('Temporary Folder'))
        # Show Global Menu
        if self._is_changed('global_menu_state'):
            new_gm_state = self._global_menu_options[
                self._global_menu_dropdown.get_value()]
            bass.settings['bash.global_menu'] = new_gm_state
            Link.Frame.refresh_global_menu_visibility()
        # Restore Scroll Positions on Start
        if self._is_changed(u'res_scroll_on'):
            new_res_scroll = self._restore_scroll_checkbox.is_checked
            bass.settings[u'bash.restore_scroll_positions'] = new_res_scroll
        # Administrator Mode
        if self._is_changed(u'uac_restart'):
            self._request_restart(_(u'Administrator Mode'), [u'--uac'])
        super(GeneralPage, self).on_apply()

# Trusted Binaries ------------------------------------------------------------
class TrustedBinariesPage(_AFixedPage):
    """Change which binaries are trusted and which aren't."""
    def __init__(self, parent, page_desc):
        super(TrustedBinariesPage, self).__init__(parent, page_desc)
        self._binaries_list = DoubleListBox(self,
            left_label=_(u'Trusted Binaries'),
            right_label=_(u'Untrusted Binaries'),
            left_btn_tooltip=_(u'Mark the selected binary as trusted.'),
            right_btn_tooltip=_(u'Mark the selected binary as untrusted.'))
        self._binaries_list.move_btn_callback = self._check_changed
        import_btn = OpenButton(self, _(u'Import...'),
            btn_tooltip=_(u'Import list of allowed/disallowed binaries from a '
                          u'.txt file. This also allows more fine-grained '
                          u'control over trusted binary versions.'))
        import_btn.on_clicked.subscribe(self._import_lists)
        export_btn = SaveAsButton(self, _(u'Export...'),
            btn_tooltip=_(u'Export list of allowed/disallowed binaries to a '
                          u'.txt file. This also allows more fine-grained '
                          u'control over trusted binary versions.'))
        export_btn.on_clicked.subscribe(self._export_lists)
        self._populate_binaries()
        VLayout(border=6, spacing=4, item_expand=True, items=[
            self._page_desc_label,
            HorizontalLine(self),
            (self._binaries_list, LayoutOptions(weight=1)),
            HLayout(spacing=4, items=[Stretch(), import_btn, export_btn]),
        ]).apply_to(self)

    def _check_changed(self):
        good_changed = self._binaries_list.left_items != list(bass.settings[
            u'bash.installers.goodDlls'])
        bad_changed = self._binaries_list.right_items != list(bass.settings[
            u'bash.installers.badDlls'])
        self._mark_changed(self, good_changed or bad_changed)
        self.update_layout()

    ##: Here be (some) dragons, especially in the import method
    def _export_lists(self):
        textDir = bass.dirs[u'patches']
        textDir.makedirs()
        #--File dialog
        title = _(u'Export list of allowed/disallowed plugin DLLs to:')
        file_ = bush.game.Se.se_abbrev + u' ' + _(u'DLL permissions') + u'.txt'
        textPath = FileSave.display_dialog(self, title=title,
            defaultDir=textDir, defaultFile=file_, wildcard=u'*.txt')
        if not textPath: return
        with textPath.open(u'w', encoding=u'utf-8') as out:
            # Stick a header in there and include the version. Should always be
            # a comment anyways, but to be sure, put a '#' in front of it
            out.write(u'# %s\n' % (_(u'Exported by Wrye Bash v%s')
                                   % bass.AppVersion))
            out.write(u'goodDlls # %s\n' % _(u'Binaries whose installation '
                                             u'you have allowed'))
            self._dump_dlls(bass.settings['bash.installers.goodDlls'], out)
            out.write('\n')
            out.write(u'badDlls # %s\n' % _(u'Binaries whose installation you '
                                            u'have forbidden'))
            self._dump_dlls(bass.settings['bash.installers.badDlls'], out)

    @staticmethod
    def _dump_dlls(dll_dict, out):
        if not dll_dict:
            out.write(f'# {_("None")}\n') # Treated as a comment
            return
        for dll, versions in dll_dict.items():
            out.write(f'dll: {dll}:\n')
            for i, version in enumerate(versions):
                v_name, v_size, v_crc = version
                out.write(f"version {i:02d}: ['{v_name}', {v_size:d}, "
                          f"{v_crc:d}]\n")

    def _import_lists(self):
        textDir = bass.dirs[u'patches']
        textDir.makedirs()
        #--File dialog
        defFile = f'{bush.game.Se.se_abbrev} {_("dll permissions")}.txt'
        title = _(u'Import list of allowed/disallowed plugin DLLs from:')
        textPath = FileOpen.display_dialog(self,title=title,
            defaultDir=textDir, defaultFile=defFile, wildcard=u'*.txt')
        if not textPath: return
        msg = _('Merge permissions from file with current dll permissions?')
        msg += '\n' + _("('No' Replaces current permissions instead.)")
        replace = not askYes(Link.Frame, msg, _('Merge permissions?'))
        def parse_path(s):
            """s was generated by a repr - so get rid of the u-prefix if it's
            there, drop the quotes and deal with path separators."""
            if s.startswith(u'u'):
                s = s[1:]
            return s[1:-1].replace(u'/', os.sep).replace(u'\\', os.sep)
        def parse_int(i):
            """i was generated by a repr - so get rid of the L-suffix if it's
            there and convert to int."""
            if i.endswith(u'L'):
                i = i[:-1]
            return int(i)
        try:
            with textPath.open(u'rb') as ins:
                contents = ins.read()
            # WB versions before 309 wrote a BOM into these files
            if contents.startswith(b'\xef\xbb\xbf'):
                contents = contents[3:]
            with io.StringIO(contents.decode(u'utf-8')) as ins:
                Dlls = {u'goodDlls':{}, u'badDlls':{}}
                current, dll = None, None
                for line in ins:
                    line = line.strip()
                    if line.startswith(u'goodDlls'):
                        current = Dlls[u'goodDlls']
                    elif line.startswith(u'badDlls'):
                        current = Dlls[u'badDlls']
                    elif line.startswith(u'dll:'):
                        if current is None:
                            raise SyntaxError(u'Missing "goodDlls" or '
                                              u'"badDlls" statement before '
                                              u'"dll" statement')
                        dll = line.split(u':',1)[1].strip().rstrip(u':')
                        if dll not in current: current[dll] = []
                    elif line.startswith(u'version'):
                        if dll is None:
                            raise SyntaxError(u'Missing "dll" statement '
                                              u'before "version" statement')
                        ver = line.split(u':',1)[1]
                        # Strip off leading '[' and trailing ']' before split
                        ver_components = ver[1:-1].split(u',')
                        if len(ver_components) != 3:
                            raise SyntaxError(u'Invalid format: expected '
                                              u'"version: [name, size, crc]"')
                        # Strip any spacing due to the repr used when exporting
                        ver_components = [c.strip() for c in ver_components]
                        inst_name, inst_size, inst_crc = ver_components
                        current[dll].append((
                            parse_path(inst_name), parse_int(inst_size),
                            parse_int(inst_crc)))
            if not replace:
                self._binaries_list.left_items = sorted(
                    set(self._binaries_list.left_items) |
                    set(Dlls[u'goodDlls']))
                self._binaries_list.right_items = sorted(
                    set(self._binaries_list.right_items) |
                    set(Dlls[u'badDlls']))
            else:
                self._binaries_list.left_items = sorted(Dlls[u'goodDlls'])
                self._binaries_list.right_items = sorted(Dlls[u'badDlls'])
        except UnicodeError:
            msg = _('Wrye Bash could not load %s, because it is not saved in '
                    'UTF-8 format.  Please resave it in UTF-8 format and try '
                    'again.') % textPath
            showError(self, msg)
        except SyntaxError:
            deprint(f'Error reading {textPath}', traceback=True)
            msg = _('Wrye Bash could not load %s, because there was an error '
                    'in the format of the file.') % textPath
            showError(self, msg)
        finally:
            self._check_changed()

    def on_apply(self):
        def merge_versions(dll_source, target_dict, source_dict):
            """Helper function to merge versions for each DLL in dll_source
            from source_dict into target_dict. Can't just use sets for this
            since lists aren't hashable."""
            for d in dll_source:
                # Merge the new good versions with the old ones, if any
                prev_vers = target_dict.get(d, [])
                new_vers = [x for x in source_dict[d] if x not in prev_vers]
                target_dict[d] = prev_vers + new_vers
                # Finally, remove the entry from the dict it was previously in
                del source_dict[d]
        bad_dlls_dict = bass.settings[u'bash.installers.badDlls']
        good_dlls_dict = bass.settings[u'bash.installers.goodDlls']
        # Determine which have been moved to/from the bad DLLs list
        old_bad = set(bad_dlls_dict)
        new_bad = set(self._binaries_list.right_items)
        bad_added = new_bad - old_bad
        bad_removed = old_bad - new_bad
        merge_versions(dll_source=bad_added, target_dict=bad_dlls_dict,
            source_dict=good_dlls_dict)
        merge_versions(dll_source=bad_removed, target_dict=good_dlls_dict,
            source_dict=bad_dlls_dict)
        # Force BAIN to update its good/bad caches
        bosh.bain.Installer.badDlls(force_recalc=True)
        bosh.bain.Installer.goodDlls(force_recalc=True)
        self._mark_changed(self, False)

    def _populate_binaries(self):
        self._binaries_list.left_items = list(bass.settings[
            u'bash.installers.goodDlls'])
        self._binaries_list.right_items = list(bass.settings[
            u'bash.installers.badDlls'])

    @staticmethod
    def should_appear():
        # Currently we only allow a few special types of binaries
        return bool(bush.game.Sd.sd_abbrev or
                    bush.game.Se.se_abbrev or
                    bush.game.Sp.sp_abbrev)

# Page Definitions ------------------------------------------------------------
_settings_pages = {
    _(u'Appearance'): {
        _(u'Colors'): ColorsPage,
        _(u'Language'): LanguagePage,
        _('Miscellaneous'): MiscAppearancePage,
        _(u'Status Bar'): StatusBarPage,
    },
    _(u'Backups'): BackupsPage,
    _(u'Confirmations'): ConfirmationsPage,
    _(u'General'): GeneralPage,
    _(u'Trusted Binaries'): TrustedBinariesPage,
}

_page_descriptions = {
    _(u'Appearance'):
        _(u'Personalize various aspects of how Wrye Bash looks, including '
          u'colors and some GUI options.'),
    _(u'Appearance') + u'/' + _(u'Colors'):
        _(u'Change colors of various GUI components.'),
    _(u'Appearance') + u'/' + _(u'Language'):
        _(u'Change the language that Wrye Bash is displayed in and manage '
          u'localizations.'),
    _('Appearance') + '/' + _('Miscellaneous'):
        _('Change various miscellaneous appearance settings.'),
    _(u'Appearance') + u'/' + _(u'Status Bar'):
        _(u'Change settings related to the status bar at the bottom and '
          u'manage hidden buttons.'),
    _(u'Backups'):
        _(u'Create, manage and restore backups of Wrye Bash settings and '
          u'other data. Click on a backup to manage it.'),
    _(u'Confirmations'):
        _(u"Enable or disable popups with a 'Don't show this in the future' "
          u'option.'),
    _(u'General'):
        _(u'Change various general settings.'),
    _(u'Trusted Binaries'):
        _(u'Change which binaries (DLLs, EXEs, etc.) you trust. Untrusted '
          u'binaries will be skipped by BAIN when installing packages.')
}

# Anchor refs into the WB Advanced Readme
_page_anchors = defaultdict(lambda: u'settings', {
    _(u'Appearance') + u'/' + _(u'Colors'): u'settings-appearance-colors',
    _(u'Appearance') + u'/' + _(u'Language'): u'settings-appearance-language',
    _('Appearance') + '/' + _('Miscellaneous'): 'settings-appearance-misc',
    _(u'Appearance') + u'/' + _(u'Status Bar'):
        u'settings-appearance-status-bar',
    _(u'Backups'): u'settings-backups',
    _(u'Confirmations'): u'settings-confirmations',
    _(u'General'): u'settings-general',
    _(u'Trusted Binaries'): u'settings-trusted-binaries',
})
