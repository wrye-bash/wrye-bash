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
#  Wrye Bash copyright (C) 2005-2009 Wrye, 2010-2020 Wrye Bash Team
#  https://github.com/wrye-bash
#
# =============================================================================
from . import tabInfo
from .constants import colorInfo, settingDefaults
from .. import balt, barb, bass, bush, env, exception
from ..balt import colors, Link, Resources
from ..bolt import deprint
from ..gui import ApplyButton, BusyCursor, Button, CancelButton, Color, \
    ColorPicker, DialogWindow, DropDown, HLayout, HorizontalLine, \
    LayoutOptions, OkButton, PanelWin, Stretch, TextArea, TreePanel, VLayout, \
    WrappingTextMixin, ListBox

class SettingsDialog(DialogWindow):
    """A dialog for configuring settings, split into multiple pages."""
    title = _(u'Settings')
    _def_size = (600, 400)

    def __init__(self):
        super(SettingsDialog, self).__init__(Link.Frame,
            icon_bundle=Resources.bashBlue, sizes_dict=balt.sizes)
        self._tab_tree = TreePanel(self, _settings_pages, _page_descriptions)
        self._changed_state = {}
        for leaf_page in self._tab_tree.get_leaf_pages():
            self._changed_state[leaf_page] = False
            leaf_page._mark_changed = self._exec_mark_changed
##: Not yet ready, will need much more refactoring (#178). We'd need a way to
# have each page and each setting as an object, so that we can pass the search
# term along to each page. Plus TreeCtrl refactoring is needed to easily hide
# non-matching items, etc. Making this work is a very long-term goal.
#        self._search_bar = SearchBar(self)
#        self._search_bar.on_text_changed.subscribe(self._handle_search)
        self.ok_btn = OkButton(self)
        self.ok_btn.on_clicked.subscribe(self._send_ok)
        self.cancel_btn = CancelButton(self)
        # This will automatically be picked up for the top-right close button
        # by wxPython, due to us using CancelButton
        self.cancel_btn.on_clicked.subscribe(self._send_cancel)
        self.apply_btn = ApplyButton(self)
        self.apply_btn.enabled = False
        self.apply_btn.on_clicked.subscribe(self._send_apply)
        VLayout(border=4, spacing=4, item_expand=True, items=[
#            self._search_bar,
            (self._tab_tree, LayoutOptions(weight=1)),
            HorizontalLine(self),
            HLayout(spacing=5, items=[
                Stretch(), self.ok_btn, self.cancel_btn, self.apply_btn,
            ]),
        ]).apply_to(self)

    def _exec_mark_changed(self, requesting_page, is_changed):
        """Marks or unmarks the requesting page as changed, and enables or
        disables the Apply button accordingly."""
        self._changed_state[requesting_page] = is_changed
        self.apply_btn.enabled = any(self._changed_state.itervalues())

    def _send_apply(self):
        """Propagates an Apply button click to all child pages."""
        for leaf_page in self._tab_tree.get_leaf_pages():
            leaf_page.on_apply()

    def _send_cancel(self):
        """Propagates a Cancel button click to all child pages."""
        for leaf_page in self._tab_tree.get_leaf_pages():
            leaf_page.on_cancel()
            leaf_page.on_closing()

    def _send_ok(self):
        """Propagates an OK button click to all child pages."""
        for leaf_page in self._tab_tree.get_leaf_pages():
            leaf_page.on_apply()
            leaf_page.on_closing()

class _ASettingsPanel(WrappingTextMixin, PanelWin):
    """Abstract class for all settings panels."""
    def __init__(self, parent, page_desc):
        super(_ASettingsPanel, self).__init__(page_desc, parent)
        # Callback to a method that takes the settings panel and a boolean,
        # marking the settings in the specified panel as changed or not. Used
        # to automatically enable or disable the Apply button.
        self._mark_changed = None

    def on_apply(self):
        """Called when the OK or Apply button on the settings dialog is
        clicked. Should apply whatever changes have been made on this panel."""

    def on_cancel(self): # FIXME(inf) See if we'll actually need this
        """Called when the settings dialog is closed via the top-right X or
        when the Cancel button has been clicked. Only has to be overriden if
        some changes made on this panel require special actions in order to be
        discarded."""

    def on_closing(self):
        """Called when the settings dialog is about to be closed."""

# Colors ----------------------------------------------------------------------
class ColorsPanel(_ASettingsPanel):
    """Color configuration panel."""
    _keys_to_tabs = {
        u'mods': _(u'[Mods] '),
        u'screens': _(u'[Saves, Screens] '),
        u'installers': _(u'[Installers] '),
        u'ini': _(u'[INI Edits] '),
        u'tweak': _(u'[INI Edits] '),
        u'default': _(u'[All] '),
    }

    def __init__(self, parent, page_desc):
        super(ColorsPanel, self).__init__(parent, page_desc)
        self.changes = dict()
        #--DropDown
        def _display_text(k):
            return _(self._keys_to_tabs[k.split(u'.')[0]]) + colorInfo[k][0]
        self.text_key = dict((_display_text(x), x) for x in colors)
        colored = self.text_key.keys()
        colored.sort(key=unicode.lower)
        combo_text = colored[0]
        choiceKey = self.text_key[combo_text]
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
        self.defaultAll = Button(self, _(u'Reset All Colors'))
        self.defaultAll.on_clicked.subscribe(self.OnDefaultAll)
        self.export_config = Button(self, _(u'Export Colors...'))
        self.export_config.on_clicked.subscribe(self.OnExport)
        self.importConfig = Button(self, _(u'Import Colors...'))
        self.importConfig.on_clicked.subscribe(self.OnImport)
        #--Events
        self.picker.on_color_picker_evt.subscribe(self.OnColorPicker)
        #--Layout
        VLayout(border=6, item_expand=True, spacing=5, items=[
            self._panel_text,
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
        return self.text_key[self.comboBox.get_value()]

    @staticmethod
    def UpdateUIColors():
        """Update the Bash Frame with the new colors"""
        with BusyCursor():
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
            default = color == Color(*settingDefaults[u'bash.colors'][key])
            if not default:
                allDefault = False
                break
        # Apply and Default
        color_key = self.GetColorKey()
        if color_key in self.changes:
            color = self.changes[color_key]
        else:
            color = colors[color_key]
        default = color == Color(*settingDefaults[u'bash.colors'][color_key])
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
        for key in colors:
            default = Color(*settingDefaults[u'bash.colors'][key])
            if colors[key] != default:
                self.changes[key] = default
        self.UpdateUIButtons()

    def on_apply(self):
        for key,newColor in self.changes.iteritems():
            bass.settings[u'bash.colors'][key] = newColor.to_rgb_tuple()
            colors[key] = newColor
        bass.settings.setChanged(u'bash.colors')
        self.UpdateUIButtons()
        self.UpdateUIColors()

    def OnExport(self):
        outDir = bass.dirs[u'patches']
        outDir.makedirs()
        #--File dialog
        outPath = balt.askSave(self, _(u'Export color configuration to:'),
                               outDir, _(u'Colors.txt'), u'*.txt')
        if not outPath: return
        try:
            with outPath.open(u'w') as out:
                for key in sorted(colors):
                    if key in self.changes:
                        color = self.changes[key]
                    else:
                        color = colors[key]
                    out.write(u'%s: %s\n' % (key, color.to_rgb_tuple()))
        except Exception as e:
            balt.showError(self, _(u'An error occurred writing to ') +
                           outPath.stail + u':\n\n%s' % e)

    def OnImport(self):
        inDir = bass.dirs[u'patches']
        inDir.makedirs()
        #--File dialog
        inPath = balt.askOpen(self, _(u'Import color configuration from:'),
                              inDir, _(u'Colors.txt'), u'*.txt',
                              mustExist=True)
        if not inPath: return
        try:
            with inPath.open(u'r') as ins:
                for line in ins:
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
                        color = Color(*color_tup)
                        if color == colors[key] and key not in self.changes:
                            continue # skip, identical to our current state
                        self.changes[key] = color
        except Exception as e:
            balt.showError(self,
                _(u'An error occurred reading from ') + inPath.stail +
                u':\n\n%s' % e)
        self.UpdateUIButtons()

    def OnComboBox(self):
        self.UpdateUIButtons()
        color_key = self.GetColorKey()
        description = colorInfo[color_key][1]
        self.textCtrl.text_content = description

    def OnColorPicker(self):
        color_key = self.GetColorKey()
        newColor = self.picker.get_color()
        self.changes[color_key] = newColor
        self.UpdateUIButtons()

    def on_closing(self):
        self.comboBox.unsubscribe_handler_()

# Backups ---------------------------------------------------------------------
class BackupsPanel(_ASettingsPanel):
    """Create, manage and restore backups."""
    def __init__(self, parent, page_desc):
        super(BackupsPanel, self).__init__(parent, page_desc)
        self._backup_list = ListBox(self, isSort=True, isHScroll=True,
            onSelect=self._handle_backup_selected)
        save_settings_btn = Button(self, _(u'Save Data'),
            btn_tooltip=_(u"Save all of Wrye Bash's settings/data now."))
        save_settings_btn.on_clicked.subscribe(self._save_settings)
        new_backup_btn = Button(self, _(u'New Backup...'),
            btn_tooltip=_(u"Backup all of Wrye Bash's settings/data to an "
                          u'archive file.'))
        new_backup_btn.on_clicked.subscribe(self._new_backup)
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
        VLayout(border=6, spacing=3, item_expand=True, items=[
            self._panel_text,
            (HLayout(spacing=4, item_expand=True, items=[
                (self._backup_list, LayoutOptions(weight=1)),
                VLayout(item_expand=True, spacing=4, items=[
                    save_settings_btn, new_backup_btn, HorizontalLine(self),
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
        return self._backup_list.lb_get_str_item_at_index(
            self._backup_list.lb_get_selections()[0])

    def _delete_backup(self):
        """Deletes the currently selected backup."""
        settings_file = self._backup_dir.join(self._chosen_backup)
        try:
            env.shellDelete(settings_file, parent=self._native_widget,
                confirm=True, recycle=True)
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
    def _new_backup(self):
        """Saves the current settings and data to create a new backup."""
        with BusyCursor(): Link.Frame.SaveSettings()
        settings_file = balt.askSave(self,
            title=_(u'Backup Bash Settings'), defaultDir=self._backup_dir,
            wildcard=u'*.7z', defaultFile=barb.BackupSettings.backup_filename(
                bush.game.fsName))
        if not settings_file: return
        with BusyCursor():
            backup = barb.BackupSettings(settings_file, bush.game.fsName,
                bush.game.bash_root_prefix, bush.game.mods_dir)
        try:
            with BusyCursor(): backup.backup_settings(balt)
        except exception.StateError:
            deprint(u'Backup settings failed', traceback=True)
            backup.warn_message(balt)
        finally:
            self._populate_backup_list()

    def _populate_backup_list(self):
        """Clears and repopulates the backups list."""
        all_backups = [x.s for x in self._backup_dir.list()
                       if barb.BackupSettings.is_backup(x)]
        self._backup_list.lb_set_items(all_backups)
        if not all_backups:
            # If there are no more backups left, we need to disable all
            # backup-specific buttons again
            self._set_context_buttons(btns_enabled=False)

    def _rename_backup(self):
        """Renames the currently selected backup."""
        new_backup_name = balt.askText(self,
            _(u'Please enter the new name for this backup.'),
            title=_(u'Rename Backup'), default=self._chosen_backup)
        if not new_backup_name or new_backup_name == self._chosen_backup:
            return # user canceled or entered identical name
        new_backup = self._backup_dir.join(new_backup_name)
        old_backup = self._backup_dir.join(self._chosen_backup)
        if new_backup.isfile():
            if not balt.askYes(self, _(u'The chosen filename (%s) already '
                                       u'exists. Do you want to replace the '
                                       u'file?') % new_backup_name,
                    title=_(u'Name Conflict')):
                return # don't want to replace it, so cancel
        try:
            env.shellMove(old_backup, new_backup, parent=self._native_widget)
        except (exception.CancelError, exception.SkipError):
            return # user canceled
        self._populate_backup_list()
        # This is equivalent to removing the selected entry and adding a new
        # one, so we need to disable backup-specific buttons
        self._set_context_buttons(btns_enabled=False)

    @balt.conversation
    def _restore_backup(self):
        """Restores the currently selected backup."""
        if not balt.askYes(self, u'\n\n'.join([
            _(u"Are you sure you want to restore your Bash settings from "
              u"'%s'?") % self._chosen_backup,
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
                bush.game.fsName)
            if error_msg:
                balt.showError(self, error_msg, error_title)
                return
            error_msg, error_title = restore_.incompatible_backup_warn()
            if error_msg and not balt.askWarning(self, error_msg, error_title):
                return
            restarting = True
            balt.showInfo(self, '\n'.join([
                _(u'Your Bash settings have been successfully extracted.'),
                _(u'Backup Path: ') + settings_file.s, u'', _(u'Before the '
                  u'settings can take effect, Wrye Bash must restart.'), _(
                u'Click OK to restart now.')]), _(u'Bash Settings Extracted'))
            try: # we currently disallow backup and restore on the same boot
                bass.sys_argv.remove(u'--backup')
            except ValueError:
                pass
            Link.Frame.Restart([u'--restore'], [u'--filename', backup_dir.s])
        except exception.BoltError as e:
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

    def _set_context_buttons(self, btns_enabled):
        """Enables or disables all backup-specific buttons."""
        for ctx_btn in (self.restore_backup_btn, self.rename_backup_btn,
                        self.delete_backup_btn):
            ctx_btn.enabled = btns_enabled

# Page Definitions ------------------------------------------------------------
_settings_pages = {
    _(u'Appearance'): {
        _(u'Colors'): ColorsPanel,
    },
    _(u'Backups'): BackupsPanel,
}

_page_descriptions = {
    _(u'Appearance'):    _(u'Personalize various aspects of how Wrye Bash '
                           u'looks, including colors and some GUI options.'),
    _(u'Backups'):       _(u'Create, manage and restore backups of Wrye Bash '
                           u'settings and other data. Click on a backup to '
                           u'manage it.'),
    _(u'Colors'):        _(u'Change colors of various GUI components.'),
    _(u'Confirmations'): _(u"Enable or disable popups with a 'Don't show this "
                           u"in the future' option.")
}
