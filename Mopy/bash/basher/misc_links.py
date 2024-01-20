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
import re
from collections import defaultdict

from . import SaveDetails
from .settings_dialog import SettingsDialog
from .. import balt, bass, bosh, bush
from ..balt import AppendableLink, CheckLink, ChoiceMenuLink, EnabledLink, \
    ItemLink, Link, OneItemLink, RadioLink, SeparatorLink
from ..bolt import GPath, FName
from ..gui import AutoSize, BusyCursor, ImgFromPath

__all__ = [u'ColumnsMenu', u'Master_ChangeTo', u'Master_Disable',
           u'Screens_NextScreenShot', u'Screens_JpgQuality',
           'Screens_JpgQualityCustom', 'Screen_ConvertTo',
           u'Master_AllowEdit', u'Master_ClearRenames', u'SortByMenu',
           'Misc_SettingsDialog', 'Master_JumpTo', 'Misc_SaveData']

# Screen Links ----------------------------------------------------------------
#------------------------------------------------------------------------------
class Screens_NextScreenShot(EnabledLink):
    """Sets screenshot base name and number."""
    _text = _('Next Shot...')
    _help = _('Sets screenshot base name and number.')
    rePattern = re.compile(r'^(.+?)(\d*)$', re.I | re.U)

    def _enable(self):
        return (not bosh.oblivionIni.isCorrupted
                and bosh.oblivionIni.abs_path.exists())

    @property
    def link_help(self):
        if not self._enable():
            return self._help + ' ' + _('%(game_ini_name)s must exist.') % {
                'game_ini_name': bush.game.Ini.dropdown_inis[0]}
        else: return self._help

    def Execute(self):
        base_key = bush.game.Ini.screenshot_base_key
        index_key = bush.game.Ini.screenshot_index_key
        enabled_key = bush.game.Ini.screenshot_enabled_key
        base = bosh.oblivionIni.getSetting(*base_key)
        index = bosh.oblivionIni.getSetting(*index_key)
        pattern = self._askText(
            _('Screenshot base name, optionally with next screenshot number '
              '(e.g. %(ini_example1)s, %(ini_example2)s or '
              '%(ini_example3)s).') % {
                'ini_example1': 'ScreenShot', 'ini_example2': 'ScreenShot_101',
                'ini_example3': r'Subdir\ScreenShot_201'},
            default=base + index)
        if not pattern: return
        new_base, new_index = self.__class__.rePattern.match(pattern).groups()
        settings_screens = defaultdict(dict)
        settings_screens[base_key[0]][base_key[1]] = new_base
        settings_screens[index_key[0]][index_key[1]] = (new_index or index)
        settings_screens[enabled_key[0]][enabled_key[1]] = enabled_key[2]
        screens_dir = GPath(new_base).head
        if screens_dir:
            if not screens_dir.is_absolute():
                screens_dir = bass.dirs[u'app'].join(screens_dir)
            screens_dir.makedirs()
        bosh.oblivionIni.saveSettings(settings_screens)
        bosh.screen_infos.refresh()
        self.window.RefreshUI()

#------------------------------------------------------------------------------
class Screen_ConvertTo(EnabledLink):
    """Converts selected images to another type."""
    _help = _('Converts selected images to another format.')

    def __init__(self, ext):
        super().__init__()
        self._ext = ext
        self._text = _('Convert to %(img_ext)s') % {'img_ext': ext}

    def _enable(self):
        self.convertable = [s for s in self.selected if s.fn_ext != self._ext]
        return bool(self.convertable)

    def Execute(self):
        try:
            msg = _('Converting to %(img_ext)s') % {'img_ext': self._ext[1:]}
            with balt.Progress(msg) as progress:
                progress.setFull(len(self.convertable))
                for index, fileName in enumerate(self.convertable):
                    progress(index, fileName)
                    srcPath = bosh.screen_infos[fileName].abs_path
                    destPath = srcPath.root + self._ext
                    if srcPath == destPath or destPath.exists(): continue
                    bmp = ImgFromPath.from_path(srcPath.s,
                        quality=bass.settings['bash.screens.jpgQuality'])
                    result = bmp.save_bmp(destPath.s, self._ext)
                    if not result: continue
                    srcPath.remove()
        finally:
            bosh.screen_infos.refresh()
            self.window.RefreshUI()

#------------------------------------------------------------------------------
class Screens_JpgQuality(RadioLink):
    """Sets JPG quality for saving."""
    _help = _('Sets JPG quality for saving.')

    def __init__(self, quality):
        super().__init__()
        self.quality = quality
        self._text = f'{self.quality:d}'

    def _check(self):
        return self.quality == bass.settings[u'bash.screens.jpgQuality']

    def Execute(self):
        bass.settings[u'bash.screens.jpgQuality'] = self.quality

#------------------------------------------------------------------------------
class Screens_JpgQualityCustom(Screens_JpgQuality):
    """Sets a custom JPG quality."""
    def __init__(self):
        super().__init__(bass.settings['bash.screens.jpgCustomQuality'])
        self._text = _('Custom [%(custom_quality)d]') % {
            'custom_quality': self.quality}

    def Execute(self):
        quality = self._askNumber(_('JPG Quality'), initial_num=self.quality,
                                  min_num=0, max_num=100)
        if quality is None: return
        self.quality = quality
        bass.settings['bash.screens.jpgCustomQuality'] = self.quality
        self._text = _('Custom [%(custom_quality)d]') % {
            'custom_quality': self.quality}
        super().Execute()

# Masters Links ---------------------------------------------------------------
#------------------------------------------------------------------------------
class Master_AllowEdit(CheckLink, EnabledLink):
    _text, _help = _(u'Allow Editing'), _(u'Allow editing the masters list.')

    def _enable(self): return self.window.panel.detailsPanel.allowDetailsEdit
    def _check(self): return self.window.allowEdit
    def Execute(self): self.window.allowEdit ^= True

class Master_ClearRenames(ItemLink):
    _text = _('Clear Renames')
    _help = _('Clear the renames dictionary, causing Wrye Bash to no longer '
              'automatically apply previously executed renames.')

    def Execute(self):
        bass.settings[u'bash.mods.renames'].clear()
        self.window.RefreshUI()

class _Master_EditList(OneItemLink): # one item cause _singleSelect = True

    def _enable(self): return self.window.allowEdit

    @property
    def link_help(self):
        full_help = self.__class__._help
        if not self._enable():
            full_help += u' ' + _(u'You must first allow editing from the '
                                  u'column menu.')
        return full_help

class Master_ChangeTo(_Master_EditList):
    """Rename/replace master through file dialog."""
    _text = _('Change To...')
    _help = _(u'Rename or replace the selected master through a file dialog.')

    @balt.conversation
    def Execute(self):
        masterInfo = self._selected_info
        master_name = masterInfo.curr_name
        #--File Dialog
        wildcard = bosh.modInfos.plugin_wildcard()
        newPath = self._askOpen(title=_('Change master name to:'),
                                defaultDir=bosh.modInfos.store_dir,
                                defaultFile=master_name, wildcard=wildcard)
        if not newPath: return
        newDir, newName = newPath.headTail
        #--Valid directory?
        if newDir != bosh.modInfos.store_dir:
            self._showError(_('File must be selected from %(data_folder)s '
                              'folder.') % {'data_folder': bush.game.mods_dir})
            return
        # Handle ghosts: simply chop off the extension
        if newName.cext == '.ghost':
            newName = newName.root
        if (new_fname := FName(newName.s)) == master_name:
            return
        curr_master_names = {m.curr_name for m in
                             self.window.data_store.values()}
        parent_mi = masterInfo.parent_mod_info
        # If the user is trying to fix a plugin with circular masters, allow
        # any kind of reassignment - otherwise, run some sanity checks
        if not parent_mi.has_circular_masters():
            # Don't allow duplicate masters
            if new_fname in curr_master_names:
                self._showError(_('This plugin already has %(master_name)s as '
                                  'a master.') % {'master_name': new_fname})
                return
            # Don't allow adding a master that makes the masters circular
            altered_masters = [new_fname if m == master_name else m
                               for m in parent_mi.masterNames]
            if parent_mi.has_circular_masters(fake_masters=altered_masters):
                self._showError(_('Having %(problem_master)s as a master '
                                  'would cause this plugin to have circular '
                                  'masters, i.e. depend on itself.') % {
                    'problem_master': new_fname})
                return
        #--Save Name
        if masterInfo.rename_if_present(new_fname):
            ##: should be True but needs extra validation -> cycles?
            bass.settings['bash.mods.renames'][
                master_name] = masterInfo.curr_name
            self.window.SetMasterlistEdited(repopulate=True)

#------------------------------------------------------------------------------
class Master_Disable(AppendableLink, _Master_EditList):
    """Disable an ESM master."""
    _text = _(u'Disable')
    _help = _(u'Renames the selected ESM to a non-existent ESP so it will get '
              u'removed when you next load and save the game.')

    def _append(self, window):
        # Only allow doing this for saves and only for games where removing a
        # master from an existing save is safe
        return bush.game.Ess.can_safely_remove_masters and isinstance(
            window.detailsPanel, SaveDetails)

    def _enable(self):
        if not super(Master_Disable, self)._enable(): return False
        # Only allow for .esm files, pointless on anything else
        return self._selected_info.curr_name.fn_ext == u'.esm'

    def Execute(self):
        self._selected_info.disable_master()
        self.window.SetMasterlistEdited(repopulate=True)

#------------------------------------------------------------------------------
class Master_JumpTo(OneItemLink):
    """Jump to the selected master."""
    _text = _(u'Jump to Master')
    _help = _(u'Jumps to the currently selected master. You can double-click '
              u'on the master to the same effect.')

    def _enable(self):
        if not super(Master_JumpTo, self)._enable(): return False
        self._sel_master = self._selected_info.curr_name
        return self._sel_master in bosh.modInfos

    def Execute(self):
        balt.Link.Frame.notebook.SelectPage(u'Mods', self._sel_master)

#------------------------------------------------------------------------------
class _Column(CheckLink, EnabledLink):

    def __init__(self, _text='COLKEY'):
        """:param _text: not the link _text in this case, the key to the text
        """
        super(_Column, self).__init__()
        self.colName = _text
        self._text = bass.settings[u'bash.colNames'][_text]
        self._help = _(u"Show/Hide '%(colname)s' column.") % {
            u'colname': self._text}

    def _enable(self):
        return self.colName not in self.window.persistent_columns

    def _check(self): return self.colName in self.window.cols

    def Execute(self):
        window_cols = self.window.cols
        if self.colName in window_cols:
            window_cols.remove(self.colName)
        else:
            #--Ensure the same order each time
            cols_set = set(window_cols)
            window_cols[:] = [x for x in self.window.allCols if
                              x in cols_set or x == self.colName]
        self.window.PopulateColumns()
        self.window.RefreshUI()

class _AAutoWidthLink(RadioLink):
    """Base class for links that change the automatic column width sizing."""
    _auto_type: int

    def _check(self):
        return self._auto_type == self.window.auto_col_widths

    def Execute(self):
        self.window.auto_col_widths = self._auto_type
        self.window.autosizeColumns()

class _FitManual(_AAutoWidthLink):
    _text = _('Manual')
    _help = _('Allow manual resizing of the columns.')
    _auto_type = AutoSize.FIT_MANUAL

class _FitContents(_AAutoWidthLink):
    _text = _('Fit Contents')
    _help = _('Fit columns to their content.')
    _keyboard_hint = 'Ctrl+Num +'
    _auto_type = AutoSize.FIT_CONTENTS

class _FitHeader(_AAutoWidthLink):
    _text = _('Fit Header')
    _help = _('Fit columns to their content, keep header always visible.')
    _auto_type = AutoSize.FIT_HEADER

class ColumnsMenu(ChoiceMenuLink):
    """Customize visible columns."""
    _text = _('Columns..')
    choiceLinkType = _Column
    extraItems = [_FitManual(), _FitContents(), _FitHeader(), SeparatorLink()]

    @property
    def _choices(self): return self.window.all_allowed_cols

#------------------------------------------------------------------------------
class _SortBy(RadioLink):
    """Sort files by specified key (sortCol)."""
    def __init__(self, _text: str):
        super(_SortBy, self).__init__()
        self.sortCol = _text
        self._text = bass.settings['bash.colNames'][_text]
        self._help = _("Sort by the '%(column_name)s' column.") % {
            'column_name': self._text}

    def _check(self): return self.window.sort_column == self.sortCol

    def Execute(self): self.window.SortItems(self.sortCol, u'INVERT')

class SortByMenu(ChoiceMenuLink):
    """Link-based interface to decide what to sort the list by."""
    _text = _('Sort By..')
    choiceLinkType = _SortBy

    def __init__(self, sort_options: list[Link] | None = None):
        """Creates a new 'sort by' menu, optionally prepending the specified
        sort options before the choices. A separator is automatically inserted
        if any sort options are specified."""
        super(SortByMenu, self).__init__()
        if sort_options:
            self.extraItems = sort_options + [SeparatorLink()]

    @property
    def _choices(self): return self.window.allowed_cols

#------------------------------------------------------------------------------
class Misc_SettingsDialog(ItemLink):
    _text = _(u'Global Settings...')
    _help = _(u'Allows you to configure various settings that apply to the '
              u'entirety of Wrye Bash, not just one tab.')

    def Execute(self):
        SettingsDialog.display_dialog()

#------------------------------------------------------------------------------
class Misc_SaveData(ItemLink):
    """Saves WB settings and data."""
    _text = _('Save Data')
    _help = _("Saves Wrye Bash's settings and data.")
    _keyboard_hint = 'Ctrl+S'

    def Execute(self):
        with BusyCursor():
            Link.Frame.SaveSettings()
