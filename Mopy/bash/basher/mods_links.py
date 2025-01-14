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
"""Menu items for the _main_ menu of the mods tab - their window attribute
points to ModList singleton."""
from .dialogs import CreateNewPlugin
from .frames import PluginChecker
from .. import bush # for _Mods_ActivePluginsData, Mods_ActivePlugins
from .. import balt, bass, bosh, exception, load_order
from ..balt import AppendableLink, BoolLink, CheckLink, EnabledLink, \
    ItemLink, Link, MenuLink, MultiLink, SeparatorLink
from ..bolt import FName, decoder, deprint, dict_sort, fast_cached_property
from ..gui import BusyCursor, copy_text_to_clipboard, get_ctrl_down, \
    get_shift_down, showError
from ..parsers import CsvParser

__all__ = ['Mods_MastersFirst', 'Mods_ActivePlugins', 'Mods_ActiveFirst',
           'Mods_OblivionEsmMenu', 'Mods_CreateBlankBashedPatch',
           u'Mods_CreateBlank', u'Mods_ListMods', u'Mods_ListBashTags',
           u'Mods_CleanDummyMasters', u'Mods_AutoGhost', u'Mods_LockLoadOrder',
           u'Mods_ScanDirty', u'Mods_CrcRefresh', u'Mods_AutoESLFlagBP',
           u'Mods_LockActivePlugins', u'Mods_PluginChecker',
           u'Mods_ExportBashTags', u'Mods_ImportBashTags',
           'Mods_ClearManualBashTags', 'Mods_OpenLOFileMenu', 'Mods_LOUndo',
           'Mods_LORedo', 'Mods_IgnoreDirtyVanillaFiles', 'Mods_LOExport',
           'Mods_LOImport', 'Mods_LOImportFromOBMM']

# "Active Plugins" submenu ----------------------------------------------------
class _Mods_ActivePluginsData(balt.ListEditorData):
    """Data capsule for load list editing dialog."""
    def __init__(self, parent, loadListsDict):
        self.loadListDict = loadListsDict
        #--GUI
        balt.ListEditorData.__init__(self,parent)
        self.showRename = True
        self.showRemove = True

    def getItemList(self):
        """Returns load list keys in alpha order."""
        return sorted(self.loadListDict, key=lambda a: a.lower())

    def rename(self,oldName,newName):
        """Renames oldName to newName."""
        #--Right length?
        if len(newName) == 0 or len(newName) > 64:
            showError(self.parent, _('Name must be between 1 and 64 '
                                     'characters long.'))
            return False
        #--Rename
        self.loadListDict[newName] = self.loadListDict[oldName]
        del self.loadListDict[oldName]
        return newName

    def remove(self,item):
        """Removes load list."""
        del self.loadListDict[item]
        return True

# Basic Active Plugins links - mass activate/deactivate
class _AMods_ActivePlugins(ItemLink):
    """Base class for Active Plugins links."""

    def _select_exact(self, mods):
        lo_msg, lordata = bosh.modInfos.lo_activate_exact(mods, doSave=True)
        self.window.propagate_refresh(lordata)
        if lo_msg:
            self._showWarning(lo_msg, title=self._text)

class _Mods_ActivateAll(_AMods_ActivePlugins):
    _text = _('Activate All')
    _help = _("Activate all plugins, except ones tagged with 'Deactivate'.")
    _activate_mergeable = True

    def Execute(self):
        """Select all mods."""
        try:
            bosh.modInfos.lo_activate_all(doSave=True,
                activate_mergeable=self._activate_mergeable)
        except exception.PluginsFullError:
            self._showError(_('Plugin list is full, so some plugins '
                              'were skipped.'),
                title=_('Too Many Plugins'))
        except exception.SkippedMergeablePluginsError:
            # This isn't actually a problem, so don't show it as an error
            self._showInfo(_('There is not enough space in the plugin list to '
                             'activate all mergeable plugins, so some were '
                             'skipped.'),
                title=_('Too Many Plugins'))
        except (exception.BoltError, NotImplementedError) as e:
            deprint('Error while activating plugins', traceback=True)
            self._showError(f'{e}')
        self.window.propagate_refresh(True)

class _Mods_ActivateNonMergeable(AppendableLink, _Mods_ActivateAll):
    _text = _('Activate Non-Mergeable')
    _help = _("Activate all plugins, except mergeable ones and ones tagged "
              "with 'Deactivate'.")
    _activate_mergeable = False

    def _append(self, window):
        return bush.game.Esp.canBash and 'NoMerge' in bush.game.allTags

class _Mods_DeactivateAll(_AMods_ActivePlugins):
    _text = _('Deactivate All')
    _help = _('Deactivate all plugins.')

    def Execute(self):
        self._select_exact([])

class _Mods_ActivateOnlySelected(_AMods_ActivePlugins):
    _text = _('Activate Only Selected')
    _help = _('Activate only the currently selected plugins.')

    def Execute(self):
        self._select_exact(self.window.GetSelected())

# List-based Active Plugins links - save or edit lists
class _AMods_ActivePluginsContext(_AMods_ActivePlugins):
    """Base class for Active Plugins links that need the parent link for
    context."""
    def __init__(self, ap_parent_link):
        super().__init__()
        self._ap_parent_link = ap_parent_link

class _Mods_EditActivePluginsLists(_AMods_ActivePluginsContext):
    _text = _('Edit Active Plugins Lists…')
    _help = _('Display a dialog to rename/remove active plugins '
              'lists.')

    def Execute(self):
        ap_editor_data = _Mods_ActivePluginsData(self.window,
            self._ap_parent_link.load_lists)
        balt.ListEditor.display_dialog(self.window, _('Active Plugins Lists'),
            ap_editor_data)

class _Mods_SaveActivePluginsList(EnabledLink, _AMods_ActivePluginsContext):
    _text = _('Save Active Plugins List…')
    _help = _('Save the currently active plugins to a new active '
              'plugins list.')

    def _enable(self):
        return bool(load_order.cached_active_tuple())

    def Execute(self):
        new_actives_name = self._askText(_('Save currently active plugins '
                                           'list as:'))
        if not new_actives_name: return
        if len(new_actives_name) > 64:
            return self._showError(_('Active plugins list name must be '
                                     'between 1 and 64 characters long.'))
        self._ap_parent_link.load_lists[new_actives_name] = list(
            load_order.cached_active_tuple())

class _Mods_ActivateApList(_AMods_ActivePluginsContext):
    """Activate one specific saved active plugins list."""
    def __init__(self, ap_parent_link, lo_list_name):
        super().__init__(ap_parent_link)
        self._text = lo_list_name

    def Execute(self):
        wanted_aps = set(self._ap_parent_link.load_lists[self._text])
        self._select_exact([p for p in self._data_store if p in wanted_aps])

    @property
    def link_help(self):
        return _('Activate plugins in the %(list_name)s list.') % {
            'list_name': self._text}

class _Mods_ApLists(MultiLink, _AMods_ActivePluginsContext):
    """MultiLink that resolves to a number of _Mods_ActivateApList instances.
    Necessary because we have to delay instantiating them until after
    __load_pickled_load_orders has run."""
    def _links(self):
        sorted_lists = sorted(self._ap_parent_link.load_lists,
            key=lambda a: a.lower())
        return [_Mods_ActivateApList(self._ap_parent_link, l)
                for l in sorted_lists]

class Mods_ActivePlugins(MenuLink):
    """The Active Plugins submenu."""
    _text = _('Active Plugins..')

    def __init__(self):
        super().__init__()
        self.append(_Mods_ActivateAll())
        self.append(_Mods_ActivateNonMergeable())
        self.append(_Mods_ActivateOnlySelected())
        self.append(_Mods_DeactivateAll())
        self.append(SeparatorLink())
        self.append(_Mods_SaveActivePluginsList(self))
        self.append(_Mods_EditActivePluginsLists(self))
        self.append(SeparatorLink())
        self.append(_Mods_ApLists(self))

    @fast_cached_property
    def load_lists(self):
        """Get the load lists, since those come from BashLoadOrders.dat we must
        wait for this being initialized in ModInfos.__init__."""
        active_lists = load_order.get_active_mods_lists()
        vanilla_list = (FName(x) for x in bush.game.bethDataFiles)
        # Note the 'and' - avoids activating modding esms for Oblivion
        active_lists['Vanilla'] = [x for x in vanilla_list if
                                   x.fn_ext == '.esm' and
                                   x not in bush.game.modding_esm_size]
        return active_lists

# "Sort by" submenu -----------------------------------------------------------
class Mods_MastersFirst(CheckLink, EnabledLink):
    """Sort masters to the top."""
    _text = _('Masters First')
    _help = _('Sort masters by type. Always on if current sort is Load Order.')

    def _enable(self): return not self.window.masters_first_required
    def _check(self): return self.window.masters_first

    def Execute(self):
        self.window.masters_first = not self.window.masters_first
        self.window.SortItems()

class Mods_ActiveFirst(CheckLink):
    """Sort loaded mods to the top."""
    _text = _('Active First')
    _help = _('Sort active plugins to the top, followed by merged plugins, '
              'imported plugins and inactive plugins.')

    def _check(self): return self.window.selectedFirst

    def Execute(self):
        self.window.selectedFirst = not self.window.selectedFirst
        self.window.SortItems()

# "Oblivion.esm" submenu ------------------------------------------------------
class _Mods_SetOblivionVersion(CheckLink, EnabledLink):
    """Single link for setting an Oblivion.esm version."""
    _version_key: str # must not be None!

    def __init__(self, version_key, setProfile=False):
        super().__init__()
        self._version_key = self._text = version_key
        self.setProfile = setProfile

    @property
    def link_help(self):
        return _('Set Oblivion.esm version to %(ob_ver)s.') % {
            'ob_ver': self._text}

    def _check(self): return bosh.modInfos.voCurrent == self._version_key

    def _enable(self):
        return bosh.modInfos.try_set_version(self._version_key)

    def Execute(self):
        # we will repeat the checks here - should not be needed but won't harm
        bosh.modInfos.try_set_version(self._version_key, do_swap=self._askYes)
        # We refresh saves although should only ever depend on Oblivion.esm,
        # not any of the modding ESMs
        self.window.propagate_refresh(True)
        if self.setProfile:
            bosh.saveInfos.set_profile_attr(bosh.saveInfos.localSave,
                                            'vOblivion', self._version_key)
        Link.Frame.set_bash_frame_title()

class _Mods_OblivionVersionMenu(MenuLink):
    """The actual Oblivion.esm switching menu."""
    _text = 'Oblivion.esm..'

    def __init__(self, set_profile):
        super().__init__()
        for esm_version in bush.game.size_esm_version.values():
            self.append(_Mods_SetOblivionVersion(esm_version, set_profile))

class Mods_OblivionEsmMenu(AppendableLink, MultiLink):
    """MultiLink that adds a SeparatorLink and the Oblivion.esm switching menu
    if the current game is Oblivion."""
    def __init__(self, *, set_profile=False):
        super().__init__()
        self._set_profile = set_profile

    def _append(self, window):
        return bush.game.fsName == 'Oblivion'

    def _links(self):
        return [SeparatorLink(), _Mods_OblivionVersionMenu(self._set_profile)]

# "File" submenu --------------------------------------------------------------
class Mods_CreateBlankBashedPatch(ItemLink):
    """Create a new bashed patch."""
    _text = _(u'New Bashed Patch')
    _help = _(u'Create a new Bashed Patch.')
    _keyboard_hint = 'Ctrl+Shift+N'

    def Execute(self):
        self.window.new_bashed_patch()

class Mods_CreateBlank(ItemLink):
    """Create a new blank mod."""
    _text = _('New Plugin…')
    _help = _(u'Create a new blank plugin.')
    _keyboard_hint = 'Ctrl+N'

    def Execute(self):
        CreateNewPlugin.display_dialog(self.window)

#------------------------------------------------------------------------------
class Mods_ListMods(ItemLink):
    """Copies list of mod files to clipboard."""
    _text = _('List Plugins…')
    _help = _('Copies list of active plugins to clipboard.')

    def Execute(self):
        #--Get masters list
        list_txt = bosh.modInfos.getModList(showCRC=get_shift_down(),
                                            showVersion=not get_ctrl_down())
        copy_text_to_clipboard(list_txt)
        self._showLog(list_txt, title=_('Active Plugins'))

#------------------------------------------------------------------------------
# Basically just a convenient 'whole LO' version of Mod_ListBashTags
class Mods_ListBashTags(ItemLink):
    """Copies list of bash tags to clipboard."""
    _text = _('List Bash Tags…')
    _help = _(u'Copies list of bash tags to clipboard.')

    def Execute(self):
        tags_text = bosh.modInfos.getTagList()
        copy_text_to_clipboard(tags_text)
        self._showLog(tags_text, title=_('Bash Tags'))

#------------------------------------------------------------------------------
class Mods_CleanDummyMasters(EnabledLink):
    """Clean up after using a 'Create Dummy Masters…' command."""
    _text = _('Remove Dummy Masters…')
    _help = _("Clean up after using a 'Create Dummy Masters…' command")

    def _enable(self):
        for fileInfo in bosh.modInfos.values():
            if fileInfo.header.author == u'BASHED DUMMY':
                return True
        return False

    def Execute(self):
        to_remove = []
        for fileName, fileInfo in bosh.modInfos.items():
            if fileInfo.header.author == u'BASHED DUMMY':
                to_remove.append(fileName)
        to_remove = load_order.get_ordered(to_remove)
        self.window.DeleteItems(items=to_remove, order=False,
                                dialogTitle=_(u'Delete Dummy Masters'))

#------------------------------------------------------------------------------
class Mods_AutoGhost(BoolLink):
    """Toggle Auto-ghosting."""
    _text, _bl_key = _(u'Auto-Ghost'), u'bash.mods.autoGhost'
    _help = _(u'Toggles whether or not to automatically ghost all disabled '
              u'mods.')

    def Execute(self):
        super(Mods_AutoGhost, self).Execute()
        flipped = []
        toGhost = bass.settings['bash.mods.autoGhost']
        for mod, modInfo in bosh.modInfos.items():
            modGhost = toGhost and not load_order.cached_is_active(
                mod) and modInfo.get_table_prop('allowGhosting', True)
            if modInfo.setGhost(modGhost):
                flipped.append(mod)
        self.refresh_sel(flipped)

class Mods_AutoESLFlagBP(BoolLink):
    """Automatically flags built Bashed Patches as ESLs. This is safe, since
    BPs can never contain new records, only overrides."""
    _text = _(u'ESL-Flag Bashed Patches')
    _help = _(u'Automatically flags any built Bashed Patches as ESLs, freeing '
              u'up a load order slot.')
    _bl_key = u'bash.mods.auto_flag_esl'

class _AMods_DirtyUpdateLink(BoolLink):
    """Base class for links that have to refresh UI to account for changes in
    dirty plugin highlighting."""

    def Execute(self):
        super().Execute()
        # Update static help text & underlined plugins
        self.window.RefreshUI()

class Mods_ScanDirty(_AMods_DirtyUpdateLink):
    """Read mod CRC's to check for dirty mods."""
    _text = _("Check Against LOOT's Dirty Plugin List")
    _help = _('Display a tooltip if a plugin is dirty and underline dirty '
              'plugins.')
    _bl_key = u'bash.mods.scanDirty'

class Mods_IgnoreDirtyVanillaFiles(_AMods_DirtyUpdateLink):
    """Ignore dirty vanilla files on the Mods tab and in the Plugin Checker."""
    _text = _('Ignore Dirty Vanilla Files')
    _help = _("When checking plugins against LOOT's dirty plugin list, skip "
              "vanilla plugins (e.g. DLCs).")
    _bl_key = 'bash.mods.ignore_dirty_vanilla_files'

class Mods_LockLoadOrder(CheckLink):
    """Turn on Lock Load Order feature."""
    _text = _(u'Lock Load Order')
    _help = _(u'Will reset mod Load Order to whatever Wrye Bash has saved for'
             u' them whenever Wrye Bash refreshes data/starts up.')

    def _check(self): return load_order.locked

    def Execute(self):
        def _show_lo_lock_warning():
            message = _('Lock Load Order is a feature which resets load '
                        'order to a previously memorized state. While this '
                        'feature is good for maintaining your load order, it '
                        'will also undo any load order changes that you have '
                        'made outside Wrye Bash.')
            return self._askContinue(message, 'bash.load_order.lock.continue',
                                     title=_('Lock Load Order'))
        load_order.toggle_lock_load_order(_show_lo_lock_warning)

class Mods_LockActivePlugins(BoolLink, EnabledLink):
    """Turn on Lock Active Plugins, needs Lock Load Order to be on first."""
    _text = _('Lock Active Plugins')
    _help = _("Enhances 'Lock Load Order' to also detect when mods are "
              'enabled or disabled and to undo those changes too.')
    _bl_key = 'bash.load_order.lock_active_plugins'

    def _enable(self): return load_order.locked # needs Lock LO to be on

#------------------------------------------------------------------------------
class Mods_CrcRefresh(ItemLink):
    """Recalculate crcs for all mods"""
    _text = _(u'Recalculate CRCs')
    _help = _(u'Clean stale CRCs from cache')

    @balt.conversation
    def Execute(self):
        message = f"== {_('Mismatched CRCs')}\n\n"
        with BusyCursor(): pairs = bosh.modInfos.refresh_crcs()
        mismatched = {k: v for k, v in pairs.items() if v[0] != v[1]}
        if mismatched:
            trans_msg = _('%(mismatched_plugin)s: cached is '
                          '%(cached_crc_val)s, real is %(real_crc_val)s.')
            message += '  * ' + '\n  * '.join(
                [trans_msg % {'mismatched_plugin': k,
                              # Keep the hex formatting out of the translations
                              'cached_crc_val': f'{v[1]:08X}',
                              'real_crc_val': f'{v[0]:08X}'}
                 for k, v in mismatched.items()])
            self.refresh_sel(mismatched)
        else: message += _('No stale cached CRC values detected.')
        self._showWryeLog(message)

#------------------------------------------------------------------------------
class Mods_PluginChecker(ItemLink):
    """Launches the Plugin Checker. More discoverable alternative to the teensy
    icon at the bottom."""
    _text = _('Plugin Checker…')
    _help = _(u'Checks your loaded plugins for various problems and shows a '
              u'configurable report.')

    def Execute(self):
        PluginChecker.create_or_raise()

#------------------------------------------------------------------------------
class _AMods_BashTags(ItemLink, CsvParser):
    """Base class for export/import bash tags links."""
    _csv_header = _('Plugin'), _('Bash Tags')

class Mods_ExportBashTags(_AMods_BashTags):
    """Writes all currently applied bash tags to a CSV file."""
    _text = _('Export Bash Tags…')
    _help = _(u'Exports all currently applied bash tags to a CSV file.')

    def Execute(self):
        exp_path = self._askSave(defaultDir=bass.dirs['patches'],
            title=_('Export Bash Tags - Choose Destination'),
            defaultFile='SavedTags.csv', wildcard='*.csv')
        if not exp_path: return
        self.plugins_exported = 0
        self.write_text_file(exp_path)
        self._showInfo(_('Exported tags for %(exp_num)d plugins to '
                         '%(exp_path)s.') % {'exp_num': self.plugins_exported,
                                             'exp_path': exp_path},
            title=_('Export Bash Tags - Done'))

    def _write_rows(self, out):
        for pl_name, p in dict_sort(bosh.modInfos):
            curr_tags = p.getBashTags()
            if curr_tags:
                out.write(f'"{pl_name}","{u", ".join(sorted(curr_tags))}"\n')
                self.plugins_exported += 1

#------------------------------------------------------------------------------
class Mods_ImportBashTags(_AMods_BashTags):
    """Reads bash tags from a CSV file and applies them to the current plugins
    (as far as possible)."""
    _text = _('Import Bash Tags…')
    _help = _(u'Imports applied bash tags from a CSV file.')

    def Execute(self):
        if not self._askWarning(
            _(u'This will permanently replace applied bash tags with ones '
              u'from a previously exported CSV file. Plugins that are not '
              u'listed in the CSV file will not be touched.') + u'\n\n' +
            _(u'Are you sure you want to proceed?'),
                title=_('Import Bash Tags - Warning')):
            return
        imp_path = self._askOpen(title=_('Import Bash Tags - Choose Source'),
            defaultDir=bass.dirs['patches'], defaultFile='SavedTags.csv',
            wildcard='*.csv')
        if not imp_path: return
        self.first_line = True
        self.plugins_imported = []
        try:
            self.read_csv(imp_path)
        except (exception.BoltError, NotImplementedError):
            self._showError(_('The selected file is not a valid '
                              'bash tags CSV export.'),
                title=_('Import Bash Tags - Invalid CSV'))
            return
        self.refresh_sel(self.plugins_imported)
        self._showInfo(_('Imported tags for %(total_imported)d plugins.') % {
            'total_imported': len(self.plugins_imported)},
            title=_('Import Bash Tags - Done'))

    def _parse_line(self, csv_fields):
        if self.first_line: # header validation
            self.first_line = False
            if len(csv_fields) != 2:
                raise exception.BoltError(f'Header error: {csv_fields}')
            return
        pl_name, curr_tags = csv_fields
        if (pl_name := FName(pl_name)) in bosh.modInfos:
            target_tags = {t.strip() for t in curr_tags.split(u',')}
            target_pl = bosh.modInfos[pl_name]
            # Only import if doing this would actually change anything and mark
            # as non-automatic (otherwise they'll just get deleted immediately)
            if target_pl.getBashTags() != target_tags:
                self.plugins_imported.append(pl_name)
                target_pl.setBashTags(target_tags)
                target_pl.set_auto_tagged(False)

#------------------------------------------------------------------------------
class Mods_ClearManualBashTags(ItemLink):
    """Removes all manually applied tags."""
    _text = _(u'Clear Manual Bash Tags')
    _help = _(u'Removes all manually applied bash tags.')

    def Execute(self):
        if not self._askWarning(
                _(u'This will permanently and irreversibly remove all '
                  u'manually applied bash tags from all plugins. Tags from '
                  u'plugin descriptions, the LOOT masterlist/userlist and '
                  u'BashTags files will be left alone.') + u'\n\n' +
                _('Are you sure you want to proceed?'),
                title=_('Clear Manual Bash Tags - Warning')):
            return
        pl_reset = []
        for pl_name, p in bosh.modInfos.items():
            if not p.is_auto_tagged():
                pl_reset.append(pl_name)
                p.set_auto_tagged(True)
                p.reloadBashTags()
        self.refresh_sel(pl_reset)
        self._showInfo(_('Cleared tags from %(total_cleared)d plugins.') % {
            'total_cleared': len(pl_reset)},
            title=_('Clear Manual Bash Tags - Done'))

#------------------------------------------------------------------------------
class _Mods_OpenLOFile(ItemLink):
    """Opens a load order file in the system's default text editor."""
    def __init__(self, lo_file_path):
        super().__init__()
        self._lo_file_path = lo_file_path
        lo_file_fmt = {'lo_file_name': lo_file_path.stail}
        self._text = _('Open %(lo_file_name)s') % lo_file_fmt
        self._help = _("Opens the load order management file "
                       "'%(lo_file_name)s' in a text editor.") % lo_file_fmt

    def Execute(self):
        self._lo_file_path.start()

class Mods_OpenLOFileMenu(MultiLink):
    """Shows one or more links for opening LO management files."""
    def _links(self):
        return [_Mods_OpenLOFile(lo_f) for lo_f
                in sorted(load_order.get_lo_files())]

#------------------------------------------------------------------------------
class Mods_LOUndo(ItemLink):
    """Undoes a load order or active plugins change."""
    _text = _('Undo')
    _help = _('Undoes a load order or active plugins change.')
    _keyboard_hint = 'Ctrl+Z'

    def Execute(self):
        self.window.lo_undo()

#------------------------------------------------------------------------------
class Mods_LORedo(ItemLink):
    """Redoes a load order or active plugins change."""
    _text = _('Redo')
    _help = _('Redoes a load order or active plugins change.')
    _keyboard_hint = 'Ctrl+Y'

    def Execute(self):
        self.window.lo_redo()

#------------------------------------------------------------------------------
class Mods_LOExport(ItemLink):
    """Export the current load order to a text file (format inspired by the
    Asterisk games' plugins.txt)."""
    _text = _('Export…')
    _help = _('Exports the current load order (and active plugins) to a text '
              'file.')

    def Execute(self):
        if bush.game.has_obmm:
            if not self._askContinue(_(
                    'Note that the resulting export is not compatible with '
                    'OBMM. Its main purpose is to be imported by Wrye Bash '
                    'again.'), 'bash.load_order.no_obmm_export.continue',
                    title=_('Export Load Order - OBMM Interoperability '
                            'Warning')):
                return
        export_path = self._askSave(title=_('Export Load Order - Destination'),
            defaultDir=bass.dirs['patches'],
            defaultFile=f"{_('Exported Load Order')}.txt",
            wildcard='*.txt')
        if not export_path:
            return
        self._export_lo(export_path)
        self._showInfo(_('Successfully exported the current load order to '
                         '%(target_path)s.') % {
            'target_path': export_path,
        }, title=_('Export Load Order - Success'))

    @staticmethod
    def _export_lo(export_path):
        """Export the current load order to the specified path."""
        current_lo = load_order.cached_lo_tuple()
        current_acti_set = set(load_order.cached_active_tuple())
        header_comment = _("Load order exported by Wrye Bash v%(wb_ver)s for "
                           "%(game_name)s") % {
            'wb_ver': bass.AppVersion,
            'game_name': bush.game.display_name,
        }
        # See specification in the technical readme - skip plugins with
        # asterisks (illegal on Windows anyways, so very unlikely we'd ever get
        # such a plugin)
        formatted_lo = [f'{"*" if p in current_acti_set else ""}{p}'
                        for p in current_lo if '*' not in p]
        with open(export_path, 'w', encoding='utf-8') as out:
            out.write(f'# {header_comment}\n')
            out.write('\n'.join(formatted_lo) + '\n')

#------------------------------------------------------------------------------
def _get_import_err_msg(offending_line: str) -> str:
    return (_('Failed to import the given load order. The file is malformed. '
              'The following line is causing a problem:') + '\n\n' +
            offending_line)

class _AImportLOBaseLink(ItemLink):
    """Base class for deduplicating logic from the two LO imports."""
    _success_title: str
    _warning_title: str

    def _apply_lo(self, import_path, imp_lo, imp_acti):
        msg_lo = bosh.modInfos.lo_reorder(imp_lo, save_lo=False)
        msg_acti = bosh.modInfos.lo_activate_exact(imp_acti)
        # Don't show the exact same message twice
        for msg in dict.fromkeys([msg_lo, msg_acti]):
            if msg: self._showWarning(msg, title=self._warning_title)
        ldiff = bosh.modInfos.cached_lo_save_all()
        self.window.propagate_refresh(ldiff.to_rdata())
        self._showInfo(_('Successfully imported a load order from '
                         '%(source_path)s.') % {'source_path': import_path},
                       title=self._success_title)

class Mods_LOImport(_AImportLOBaseLink):
    """Import a previously exported load order from a text file (format
    inspired by the Asterisk games' plugins.txt)."""
    _text = _('Import…')
    _help = _('Imports a previously exported load order (and active plugins) '
              'from a text file.')
    _success_title = _('Import Load Order - Success')
    _warning_title = _('Import Load Order - Warning')

    def Execute(self):
        if bush.game.has_obmm:
            if not self._askContinue(_(
                    "Note that this command is not compatible with exports "
                    "made in OBMM. They will not cause an error, but the "
                    "result will be wrong. Use the dedicated 'Import From "
                    "OBMM…' command to handle such exports."),
                    'bash.load_order.use_obmm_import.continue',
                    title=_('Import Load Order - OBMM Interoperability '
                            'Warning')):
                return
        import_path = self._askOpen(title=_('Import Load Order - Source'),
            defaultDir=bass.dirs['patches'],
            defaultFile=f"{_('Exported Load Order')}.txt",
            wildcard='*.txt')
        if not import_path:
            return
        imp_first, imp_second = self._import_lo(import_path)
        if imp_first is None:
            self._showError(imp_second, title=_('Import Load Order - Error'))
            return
        # If imp_first is not None, the import worked and the first value is
        # the load order, while the second value is the actives
        self._apply_lo(import_path, imp_first, imp_second)

    @staticmethod
    def _import_lo(import_path) -> (tuple[list[FName], set[FName]] |
                                    tuple[None, str]):
        """Import a previous LO export from the specified path.

        :return: Either a tuple containing None and a line that caused the
            import to fail, or a tuple containing a list of FNames and a set of
            FNames, the former representing the load order and the latter the
            active plugins."""
        with open(import_path, 'r', encoding='utf-8') as ins:
            exported_lines = ins.read().splitlines()
        imported_lo = []
        imported_acti = set()
        for ex_line in exported_lines:
            stripped_line = (ex_line[:ex_line.index('#')]
                             if '#' in ex_line else ex_line)
            if not stripped_line or stripped_line.isspace():
                continue
            is_line_active = stripped_line.startswith('*')
            # rstrip instead of strip because leading spaces are fine, see
            # specification in technical readme
            trimmed_plugin = FName((stripped_line[1:] if is_line_active else
                                    stripped_line).rstrip())
            if trimmed_plugin.fn_ext not in bush.game.espm_extensions:
                return None, _get_import_err_msg(ex_line)
            imported_lo.append(trimmed_plugin)
            if is_line_active:
                imported_acti.add(trimmed_plugin)
        return imported_lo, imported_acti

#------------------------------------------------------------------------------
class Mods_LOImportFromOBMM(AppendableLink, _AImportLOBaseLink):
    """Import active plugins from a text file exported by OBMM."""
    _text = _('Import From OBMM…')
    _help = _('Imports active plugins from a text file exported by OBMM.')
    _success_title = _('Import From OBMM - Success')
    _warning_title = _('Import From OBMM - Warning')

    def _append(self, window):
        return bush.game.has_obmm

    def Execute(self):
        if not self._askContinue(_(
                'Note that this command is always going to result in '
                'imperfect imports, because OBMM does not export the order '
                'of inactive plugins. Wrye Bash will do its best, but you '
                'should check the result manually.'),
                'bash.load_order.flawed_obmm_import.continue',
                title=_('Import From OBMM - Warning')):
            return
        import_path = self._askOpen(title=_('Import From OBMM - Source'),
            defaultDir=bass.dirs['patches'],
            defaultFile=f"{_('OBMM Export')}.txt",
            wildcard='*.txt')
        if not import_path:
            return
        imp_result = self._import_lo(import_path)
        if isinstance(imp_result, str):
            self._showError(imp_result, title=_('Import From OBMM - Error'))
            return
        # If imp_result is not a string, the import worked and we've got a load
        # order
        self._apply_lo(import_path, imp_result, imp_result)

    @staticmethod
    def _import_lo(import_path) -> list[FName] | str:
        """Import a previous LO export from the specified path.

        :return: Either a tuple containing None and an error message, or a list
            of FNames representing the load order and active plugins."""
        with open(import_path, 'rb') as ins:
            obmm_data = ins.read()
        try:
            exported_lines = decoder(obmm_data).splitlines()
        except UnicodeDecodeError:
            return _('Could not determine encoding.')
        imported_lo = []
        for ex_line in exported_lines:
            parsed_plugin = FName(ex_line)
            if parsed_plugin.fn_ext not in bush.game.espm_extensions:
                return _get_import_err_msg(ex_line)
            imported_lo.append(parsed_plugin)
        return imported_lo
