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
"""Menu items for the _item_ menu of the mods tab - their window attribute
points to ModList singleton."""

import copy
import io
import re
import traceback
from collections import defaultdict
from itertools import chain

from .constants import settingDefaults
from .dialogs import DeactivateBeforePatchEditor, ExportScriptsDialog, \
    ListDependentDialog, MasterErrorsDialog
from .files_links import File_Duplicate, File_Redate
from .frames import DocBrowser
from .patcher_dialog import PatchDialog, all_gui_patchers
from .. import balt, bass, bolt, bosh, bush, load_order
from ..balt import AppendableLink, CheckLink, ChoiceLink, EnabledLink, \
    ItemLink, Link, MenuLink, OneItemLink, SeparatorLink, TransLink
from ..bass import Store
from ..bolt import FName, SubProgress, dict_sort, sig_to_str, FNDict, \
    GPath_no_norm, RefrIn
from ..brec import RecordType
from ..exception import BoltError, CancelError, PluginsFullError
from ..gui import BmpFromStream, BusyCursor, copy_text_to_clipboard, askText, \
    showError
from ..localize import format_date
from ..mod_files import LoadFactory, ModFile, ModHeaderReader
from ..parsers import ActorFactions, ActorLevels, CsvParser, EditorIds, \
    FactionRelations, FidReplacer, FullNames, IngredientDetails, ItemPrices, \
    ItemStats, ScriptText, SigilStoneDetails, SpellRecords, _AParser
from ..patcher.patch_files import PatchFile
from ..plugin_types import MergeabilityCheck, PluginFlag
from ..wbtemp import TempFile

__all__ = [u'Mod_FullLoad', u'Mod_CreateDummyMasters', u'Mod_OrderByName',
           u'Mod_Groups', u'Mod_Ratings', u'Mod_Details', u'Mod_ShowReadme',
           u'Mod_ListBashTags', u'Mod_CreateLOOTReport', u'Mod_CopyModInfo',
           'Mod_AllowGhosting', 'Mod_GhostUnghost', 'Mod_CheckQualifications',
           'Mod_RebuildPatch', 'Mod_ListPatchConfig', 'Mod_EditorIds_Export',
           u'Mod_FullNames_Export', u'Mod_Prices_Export', u'Mod_Stats_Export',
           u'Mod_Factions_Export', u'Mod_ActorLevels_Export', u'Mod_Redate',
           u'Mod_FactionRelations_Export', u'Mod_IngredientDetails_Export',
           u'Mod_Scripts_Export', u'Mod_SigilStoneDetails_Export',
           u'Mod_SpellRecords_Export', u'Mod_EditorIds_Import',
           u'Mod_FullNames_Import', u'Mod_Prices_Import', u'Mod_Stats_Import',
           u'Mod_Factions_Import', u'Mod_ActorLevels_Import',
           u'Mod_FactionRelations_Import', u'Mod_IngredientDetails_Import',
           u'Mod_Scripts_Import', u'Mod_SigilStoneDetails_Import',
           u'Mod_SpellRecords_Import', u'Mod_Face_Import', u'Mod_Fids_Replace',
           u'Mod_SkipDirtyCheck', u'Mod_ScanDirty', u'Mod_RemoveWorldOrphans',
           u'Mod_FogFixer', u'Mod_CopyToMenu', u'Mod_DecompileAll',
           'Mod_FlipMasters', 'Mod_SetVersion', 'Mod_ListDependent',
           'Mod_Move', 'Mod_RecalcRecordCounts', 'Mod_Duplicate',
           'Mod_DumpSubrecords', 'Mod_DumpRecordTypeNames', 'Mod_Snapshot',
           'Mod_RevertToSnapshot', 'AFlipFlagLink']

def _configIsCBash(patchConfigs):
    return any('CBash' in config_key for config_key in patchConfigs)

#------------------------------------------------------------------------------
# Mod Links -------------------------------------------------------------------
#------------------------------------------------------------------------------
class _LoadLink(ItemLink):
    _load_sigs = ()

    def _load_fact(self, keepAll=True):
        return LoadFactory(keepAll, by_sig=self._load_sigs)

    def _load_mod(self, mod_info, keepAll=True, load_fact=None, **kwargs):
        lf = load_fact or self._load_fact(keepAll=keepAll)
        modFile = ModFile(mod_info, lf)
        modFile.load_plugin(**kwargs)
        return modFile

# Dev tools, no need to translate strings here
class Mod_FullLoad(_LoadLink):
    """Tests all record definitions against a specific mod"""
    _text = 'Test Record Definitions…'
    _help = ('Tests the current record definitions for this game against the '
             'selected plugins.')
    _load_sigs = tuple(RecordType.sig_to_class) # all available (decoded) records

    @balt.conversation
    def Execute(self):
        bolt.deprint(RecordType.sig_to_class)
        dbg_infos = list(self.iselected_infos())
        with balt.Progress() as progress:
            progress.setFull(len(dbg_infos))
            for i, dbg_inf in enumerate(dbg_infos):
                try:
                    self._load_mod(dbg_inf, keepAll=False,
                        progress=SubProgress(progress, i, i + 1),
                        catch_errors=False)
                except:
                    failed_msg = f'{dbg_inf.fn_key} failed to verify using ' \
                        f'current record definitions. The original ' \
                        f'traceback is available in the BashBugDump.\n\n' \
                        f'{traceback.format_exc()}'
                    self._showError(failed_msg, title='Verification Failed')
                    bolt.deprint(f'Exception loading {dbg_inf.fn_key}:',
                                 traceback=True)
                    return
        self._showOk('All selected files fully verified using current '
                     'record definitions.', title='Verification Succeeded')

class Mod_RecalcRecordCounts(OneItemLink, _LoadLink):
    """Useful for debugging if any get_num_headers implementations are broken.
    Simply copy-paste the loop from below into ModFile.save to get output on BP
    save, then compare it to the MobBase-based output from this link."""
    _text = 'Recalculate Record Counts'
    _help = ('Recalculates the group record counts for the selected plugin '
             'and writes them to the BashBugDump.')

    def Execute(self):
        modFile = self._load_mod(self._selected_info, do_map_fids=False)
        for top_grup_sig, block in dict_sort(modFile.tops):
            bolt.deprint(f'{sig_to_str(top_grup_sig)} GRUP has '
                         f'{block.get_num_headers()} records and groups')

class Mod_DumpSubrecords(_LoadLink):
    """Useful for figuring out the *order* of subrecords inside certain
    records, to make sure the order you're programming into WB matches the one
    the CK actually puts out."""
    _text = 'Dump Subrecords'
    _help = ('Write information on the FourCC and order of all subrecords in '
             'all records in the selected plugins to the BashBugDump.')

    def Execute(self):
        for ds_p in self.iselected_infos():
            ds_data = ModHeaderReader.read_all_subrecords(ds_p)
            bolt.deprint(f'=== Dumping records and subrecords for {ds_p} ===')
            for ds_sig, ds_all_recs in ds_data.items():
                bolt.deprint(f'- {sig_to_str(ds_sig)}:')
                for ds_rec_head, ds_subrecs in ds_all_recs:
                    bolt.deprint(f' - {ds_rec_head.fid.short_fid:08X}:')
                    for ds_sub in ds_subrecs:
                        bolt.deprint(f'  - {sig_to_str(ds_sub.mel_sig)}, '
                                     f'{len(ds_sub.mel_data)} bytes')
            bolt.deprint(f'=== Finished dump for {ds_p} ===')

class Mod_DumpRecordTypeNames(ItemLink):
    """Useful for updating the mk_html_list script (in record_work_utils). Also
    highlights record types where you forgot to add a docstring."""
    _text = 'Dump Record Type Names'
    _help = ('Write a mapping of record type signatures to record type names '
             'to the BashBugDump.')

    def Execute(self):
        rt_mapping = dict_sort({
            s: (c.__doc__.rstrip('.') if c.__doc__ else '<Missing Docstring>')
            for s, c in RecordType.sig_to_class.items()
            if c.__name__ != 'MreRecord' # Skip annoying generic docstring
        })
        bolt.deprint(dict(rt_mapping))
        self._showOk('Done, see BashBugDump for results.')

# File submenu ----------------------------------------------------------------
# the rest of the File submenu links come from file_links.py
class Mod_CreateDummyMasters(OneItemLink):
    """xEdit tool, makes dummy plugins for each missing master, for use if
    looking at a 'Filter' patch."""
    _text = _('Create Dummy Masters…')
    _help = _('Creates empty plugins for each missing master of the selected '
              'plugin, allowing it to be loaded by tools like %(xedit_name)s '
              'or the %(ck_name)s.') % {
        'xedit_name': bush.game.Xe.full_name,
        'ck_name': bush.game.Ck.long_name,
    }

    def _enable(self): # enable if there are missing masters
        return super()._enable() and self._selected_info.getStatus() == 30

    def Execute(self):
        """Create Dummy Masters"""
        msg = '\n\n'.join([
            _("This is an advanced feature, originally intended for viewing "
              "and editing 'Filter' patches in %(xedit_name)s. It will create "
              "empty plugins for each missing master. Are you sure you want "
              "to continue?") % {'xedit_name': bush.game.Xe.full_name},
            _("To remove these files later, use 'Remove Dummy Masters…'.")])
        if not self._askYes(msg, title=self._text): return
        mod_previous = FNDict() # previous master for each master
        # creates esp files - so place them correctly after the last esm
        previous_master = bosh.modInfos.cached_lo_last_esm()
        for master in self._selected_info.masterNames:
            if master in bosh.modInfos:
                if not bush.game.master_flag.cached_type(bosh.modInfos[master]):
                    # if previous master is an esp put this one after it
                    previous_master = master
                continue
            # Missing master, create a dummy plugin for it --------------------
            # Add the appropriate flags based on extension. This is obviously
            # just a guess - you can have a .esm file without an ESM flag in
            # Skyrim LE - but these are also just dummy masters.
            force_flags = bush.game.plugin_flags.guess_flags(
                master.fn_ext, bush.game)
            bosh.modInfos.create_new_mod(master, author_str='BASHED DUMMY',
                flags_dict=force_flags,
                wanted_masters=[], # previous behavior - correct?
                # pass dir_path explicitly so refresh is skipped
                dir_path=self._data_store.store_dir)
            mod_previous[master] = previous_master
            previous_master = master
        bosh.modInfos.refresh(RefrIn.from_added(mod_previous),
                              insert_after=mod_previous)
        self.window.propagate_refresh(Store.SAVES.DO(), detail_item=next(
            reversed(mod_previous)))
        self.window.SelectItemsNoCallback(mod_previous)

#------------------------------------------------------------------------------
class Mod_OrderByName(EnabledLink):
    """Sort the selected files."""
    _text = _('Order by Name')
    _help = _(u'Reorder the selected plugins to be in alphabetical order. '
              u'Only works if the selected plugins may be reordered.')

    def _enable(self):
        # Can't be used if at least one of the selected mods is pinned
        return len(self.selected) > 1 and not load_order.filter_pinned(
            self.selected, fixed_order=True)

    @balt.conversation
    def Execute(self):
        message = _('Reorder selected plugins in alphabetical order starting '
            'at the lowest ordered?') if bush.game.using_txt_file else _(
            'Reorder selected plugins in alphabetical order? The first plugin '
            'will be given the date/time of the current earliest plugin in '
            'the group, with consecutive files following at 1 minute '
            'increments.')
        message = '\n\n'.join((message, _(
            'Note that some plugins need to be in a specific order to work '
            'correctly, and this sort operation may break that order.')))
        if not self._askContinue(message, 'bash.sortMods.continue',
                                 title=self._text): return
        #--Do it
        self.selected.sort(key=lambda m: ( # sort masters first
            *bush.game.master_flags.sort_masters_key(bosh.modInfos[m]), m))
        lowest = load_order.get_ordered(self.selected)[0]
        bosh.modInfos.cached_lo_insert_at(lowest, self.selected)
        # Reorder the actives too to avoid bogus LO warnings
        bosh.modInfos.cached_lo_save_all()
        self.window.propagate_refresh(Store.SAVES.DO())

#------------------------------------------------------------------------------
class Mod_Move(EnabledLink):
    """Moves selected mod(s) to a different LO position."""
    _text = _('Move To…')
    _help = _('Move the selected plugins to a position of your choice. '
              'Only works if the selected plugins may be reordered.')

    def _enable(self):
        # Can't be used if at least one of the selected mods is pinned
        return not load_order.filter_pinned(self.selected, fixed_order=True)

    def Execute(self):
        entered_text = u''
        # Default to the index of the first selected active plugin, or 0
        for p in self.selected:  ##: order in load order?
            if default_index := load_order.cached_active_index_str(p): break
        else: default_index = f'{0:02X}'
        try:
            # Only accept hexadecimal numbers, trying to guess what they are
            # will just lead to sadness
            entered_text = self._askText(
                _('Please enter the plugin index to which the selected '
                  'plugins should be moved.') + '\n' +
                _('Note that it must be a hexadecimal number, as shown on '
                  'the Mods tab.'), default=default_index)
            if not entered_text: return # Abort if canceled or empty string
            target_index = int(entered_text, base=16)
        except (TypeError, ValueError):
            self._showError(_("'%(not_hexadecimal)s' is not a valid "
                              "hexadecimal number.") % {
                'not_hexadecimal': entered_text})
            return
        # We can obviously only target active plugins, since inactive
        # plugins do not have a *user-exposed* index
        active_plugins = load_order.cached_active_tuple()
        # Clamp between 0 and max plugin index
        target_index = max(0, min(target_index, len(active_plugins) - 1))
        bosh.modInfos.cached_lo_insert_at(active_plugins[target_index],
                                          self.selected)
        # Reorder the actives too to avoid bogus LO warnings
        ldiff = bosh.modInfos.cached_lo_save_all()
        self.window.propagate_refresh(Store.SAVES.DO(), rdata=ldiff.to_rdata(),
                                      detail_item=self.selected[0])

#------------------------------------------------------------------------------
class Mod_Redate(File_Redate):
    """Mods tab version of the Redate command."""
    def _infos_to_redate(self):
        return [self._data_store[to_redate] for to_redate
                in load_order.get_ordered(self.selected)]

# Group/Rating submenus -------------------------------------------------------
#--Common ---------------------------------------------------------------------
class _Mod_LabelsData(balt.ListEditorData):
    """Data capsule for label editing dialog."""

    def __init__(self, parent, modLabels):
        #--Strings
        self.column = modLabels.column
        self.setKey = modLabels.setKey
        self.addPrompt = modLabels.addPrompt
        #--Key/type
        self.mod_labels = bass.settings[self.setKey]
        #--GUI
        balt.ListEditorData.__init__(self,parent)
        self.showAdd = True
        self.showRename = True
        self.showRemove = True

    def getItemList(self):
        """Returns load list keys in alpha order."""
        return sorted(self.mod_labels, key=lambda a: a.lower())

    def add(self):
        """Adds a new group."""
        #--Name Dialog
        newName = askText(self.parent, self.addPrompt)
        if newName is None: return
        if newName in self.mod_labels:
            showError(self.parent, _('Name must be unique.'))
            return False
        elif len(newName) == 0 or len(newName) > 64:
            showError(self.parent, _('Name must be between 1 and 64 '
                                     'characters long.'))
            return False
        self.mod_labels.append(newName)
        self.mod_labels.sort()
        return newName

    def rename(self,oldName,newName):
        """Renames oldName to newName."""
        #--Right length?
        if len(newName) == 0 or len(newName) > 64:
            showError(self.parent, _('Name must be between 1 and 64 '
                                     'characters long.'))
            return False
        #--Rename
        self.mod_labels.remove(oldName)
        self.mod_labels.append(newName)
        self.mod_labels.sort()
        #--Edit table entries.
        renamed = []
        for fn, mod_inf in bosh.modInfos.items():
            if mod_inf.get_table_prop(self.column) == oldName:
                mod_inf.set_table_prop(self.column, newName)
                renamed.append(fn)
        Link.refresh_sel(self.parent, renamed)
        #--Done
        return newName

    def remove(self,item):
        """Removes group."""
        self.mod_labels.remove(item)
        #--Edit table entries.
        deletd = []
        for fn, mod_inf in bosh.modInfos.items():
            if mod_inf.get_table_prop(self.column) == item:
                mod_inf.set_table_prop(self.column, None)
                deletd.append(fn)
        Link.refresh_sel(self.parent, deletd)
        #--Done
        return True

    def setTo(self, items):
        """Set the bosh.settings[self.setKey] list to the items given - do
        not update mod List for removals (i.e. if a group/rating is removed
        there may be mods still assigned to it or rated) - it's a feature.
        """
        items.sort(key=lambda a: a.lower())
        if self.mod_labels == items: return False
        # do not reassign self.mod_labels! points to settings[self.setKey]
        self.mod_labels[:] = items
        return True

class _Mod_Labels(ChoiceLink):
    """Add mod label links."""
    extraButtons = {} # extra actions for the edit dialog
    # override in subclasses
    edit_menu_text = _('Edit Groups…')
    edit_window_title = _(u'Groups')
    column     = u'group'
    setKey     = u'bash.mods.groups'
    addPrompt  = _(u'Add group:')

    def __init__(self):
        super(_Mod_Labels, self).__init__()
        self.mod_labels = bass.settings[self.setKey]
        #-- Links
        _self = self
        class _Edit(ItemLink):
            _text = _help = _self.edit_menu_text
            def Execute(self):
                """Show label editing dialog."""
                lid = _Mod_LabelsData(self.window, _self)  # ListEditorData
                with balt.ListEditor(self.window, _self.edit_window_title, lid,
                                     _self.extraButtons) as _self.listEditor:
                    _self.listEditor.show_modal()  ##: consider only refreshing
                    # the mod list if this returns true
                ##: used by the buttons code - should be encapsulated
                del _self.listEditor
        class _None(CheckLink):
            _text = _('None')
            _help = _('Remove all labels from the selected plugins.')
            def Execute(self):
                """Handle selection of None."""
                for finf in self.iselected_infos():
                    finf.set_table_prop(_self.column, None)
                _self.refresh_sel()
            def _check(self):
                return _self._none_checked
        self.extraItems = [_Edit(), SeparatorLink(), _None()]

    def _initData(self, window, selection):
        super(_Mod_Labels, self)._initData(window, selection)
        _self = self
        selection_set = set(selection)
        assigned_labels = {p for k, v in bosh.modInfos.items() if
            k in selection_set and (p := v.get_table_prop(self.column))}
        self._none_checked = not assigned_labels
        class _LabelLink(CheckLink):
            def Execute(self):
                for fileInfo in self.iselected_infos():
                    fileInfo.set_table_prop(_self.column, self._text)
                _self.refresh_sel()
            @property
            def link_help(self):
                return _("Applies the label '%(target_label)s' to the "
                         "selected plugins.") % {'target_label': self._text}
            def _check(self):
                """Check the link if any of the selected plugins have labels
                matching this one."""
                return self._text in assigned_labels
        self.__class__.choiceLinkType = _LabelLink

    @property
    def _choices(self): return sorted(self.mod_labels, key=lambda a: a.lower())

#--Groups ---------------------------------------------------------------------
class _ModGroups(CsvParser):
    """Groups for mods with functions for importing/exporting from/to text
    file."""
    _csv_header = _(u'Mod'), _(u'Group')

    def __init__(self):
        self.mod_group = {}

    def readFromModInfos(self, mods):
        """Read groups for specified mods from modInfos."""
        self.mod_group.update((x, g) for x in mods if (
            g := bosh.modInfos[x].get_table_prop('group')))

    @staticmethod
    def assignedGroups():
        """Return all groups that are currently assigned to mods."""
        return {g for x in bosh.modInfos.values() if
                (g := x.get_table_prop('group'))}

    def writeToModInfos(self, mods):
        """Exports mod groups to modInfos."""
        mod_group = self.mod_group
        changed = set()
        for x in mods:
            if x in mod_group and (g := mod_group[x]) != (
                    (inf := bosh.modInfos[x]).get_table_prop('group')):
                inf.set_table_prop('group', g)
                changed.add(x)
        return changed

    def _parse_line(self, csv_fields):
        """Imports mod groups from specified text file."""
        if len(csv_fields) >= 2 and bosh.ModInfos.rightFileType(csv_fields[0]):
            mod, mod_grp = csv_fields[:2]
            self.mod_group[FName(mod)] = mod_grp

    def _write_rows(self, out):
        """Exports eids to specified text file."""
        for mod, mod_grp in dict_sort(self.mod_group):
            out.write(f'"{mod}","{mod_grp}"\n')

class _CsvExport_Link(ItemLink):
    """Mixin for links exporting in a csv file."""

    def _csv_out(self, textName):
        textDir = bass.dirs[u'patches']
        textDir.makedirs()
        #--File dialog
        textPath = self._askSave(title=self.__class__.askTitle,
                                 defaultDir=textDir, defaultFile=textName,
                                 wildcard=u'*' + self.__class__.csvFile)
        return textPath

class _Mod_Groups_Export(_CsvExport_Link):
    """Export mod groups to text file."""
    askTitle = _(u'Export groups to:')
    csvFile = u'_Groups.csv'
    _text = _('Export Groups…')
    _help = _('Exports the groups of all selected plugins to a .csv file.')

    def Execute(self):
        textName = _('My %(csv_file)s') % {'csv_file': self.__class__.csvFile}
        textPath = self._csv_out(textName)
        if not textPath: return
        #--Export
        modGroups = _ModGroups()
        modGroups.readFromModInfos(self.selected)
        modGroups.write_text_file(textPath)
        self._showOk(_('Exported %(num_groups_exported)d groups.') % {
            'num_groups_exported': len(modGroups.mod_group)})

class _Mod_Groups_Import(ItemLink):
    """Import mod groups from text file."""
    _text = _('Import Groups…')
    _help = _("Imports all groups from a CSV file (filename must end in "
              "'_Groups.csv') and applies them to the selected plugins.")

    def Execute(self):
        message = _('Import groups from a CSV file? This will assign the '
                    'group each selected plugin is assigned in the CSV file, '
                    'if any.')
        if not self._askContinue(message, 'bash.groups.import.continue',
                title=_('Import Groups')):
            return
        textDir = bass.dirs[u'patches']
        #--File dialog
        textPath = self._askOpen(_('Import names from:'), textDir, '',
                                 '*_Groups.csv')
        if not textPath: return
        #--Extension error check
        if textPath.cext != '.csv':
            self._showError(_('Source file must be a CSV file.'))
            return
        #--Import
        modGroups = _ModGroups()
        modGroups.read_csv(textPath)
        changed = modGroups.writeToModInfos(self.selected)
        self.refresh_sel(changed)
        self._showOk(_('Imported %(num_imported_groups)d groups '
                       '(%(num_changed_groups)d changed).') % {
            'num_imported_groups': len(modGroups.mod_group),
            'num_changed_groups': len(changed)}, title=_('Import Groups'))

class Mod_Groups(_Mod_Labels):
    """Add mod group links."""

    def __init__(self):
        self.extraButtons = {_('Refresh'): self._doRefresh,
            _('Sync'): self._doSync, _('Reset'): self._doReset}
        super(Mod_Groups, self).__init__()
        self.extraItems = [_Mod_Groups_Export(),
                           _Mod_Groups_Import()] + self.extraItems

    def _doRefresh(self):
        """Add to the list of groups currently assigned to mods."""
        self.SetItemsTo(list(set(
            bass.settings['bash.mods.groups']) | _ModGroups.assignedGroups()))

    def _doSync(self):
        """Set the list of groups to groups currently assigned to mods."""
        msg = _('This will set the list of available groups to the groups '
                'currently assigned to plugins. Continue?')
        if not balt.askContinue(self.listEditor, msg,
                                'bash.groups.sync.continue',
                                _('Sync Groups')): return
        self.SetItemsTo(list(_ModGroups.assignedGroups()))

    def _doReset(self):
        """Set the list of groups to the default groups list.

        Won't clear user set groups from the modlist - most probably not
        what the user wants.
        """
        msg = _("This will reset the list of available groups to the default "
                "group list. However, it won't remove non-default groups from "
                "plugins that are already tagged with them. Continue?")
        if not balt.askContinue(self.listEditor, msg,
                                'bash.groups.reset.continue',
                                _('Reset Groups')): return
        self.SetItemsTo(list(settingDefaults['bash.mods.groups']))

    def SetItemsTo(self, items):
        led = self.listEditor._listEditorData
        if led.setTo(items):
            self._list_items = led.getItemList()
            self.listEditor.listBox.lb_set_items(self._list_items)

#--Ratings --------------------------------------------------------------------
class Mod_Ratings(_Mod_Labels):
    """Add mod rating links."""
    edit_menu_text = _('Edit Ratings…')
    edit_window_title = _(u'Ratings')
    column     = u'rating'
    setKey     = u'bash.mods.ratings'
    addPrompt  = _(u'Add rating:')

# Mod info menus --------------------------------------------------------------
#------------------------------------------------------------------------------
class Mod_Details(OneItemLink):
    """Show Mod Details"""
    _text = _('Details…')
    _help = _(u'Show Mod Details')

    def Execute(self):
        with balt.Progress(_(u'Details')) as progress:
            sel_info_data = ModHeaderReader.extract_mod_data(
                self._selected_info, SubProgress(progress, 0.1, 0.7))
            buff = []
            complex_groups = bush.game.complex_groups
            progress(0.7, _('Sorting records.'))
            for group, group_records in dict_sort(sel_info_data):
                buff.append(sig_to_str(group))
                if group in complex_groups:
                    buff.append('  %s\n' % _('(Details not provided for this '
                                             'record type.)'))
                    continue
                recs = sorted(group_records, key=lambda r: r[1].lower())
                for h, e in recs:
                    buff.append(f'  {h.fid} {e}')
                buff.append('') # an empty line
            self._showLog('\n'.join(buff), title=self._selected_item)

class Mod_ShowReadme(OneItemLink):
    """Open the readme."""
    _text = _('Readme…')
    _help = _(u'Open the readme')

    def Execute(self):
        if not Link.Frame.docBrowser:
            DocBrowser(self.window.data_store).show_frame()
        Link.Frame.docBrowser.SetMod(self._selected_item)
        Link.Frame.docBrowser.raise_frame()

class Mod_ListBashTags(ItemLink):
    """Copies list of bash tags to clipboard."""
    _text = _('List Bash Tags…')
    _help = _(u'Copies list of bash tags to clipboard')

    def Execute(self):
        #--Get masters list
        tags_text = bosh.modInfos.getTagList(list(self.iselected_infos()))
        copy_text_to_clipboard(tags_text)
        self._showLog(tags_text, title=_('Bash Tags'))

def _getUrl(installer):
    """"Try to get the url of the installer (order of priority will be:
    TESNexus, TESAlliance)."""
    url = None
    ma = bosh.reTesNexus.search(installer)
    if ma and ma.group(2):
        url = f'{bush.game.nexusUrl}mods/{ma.group(2)}/'
    if not url:
        ma = bosh.reTESA.search(installer)
        if ma and ma.group(2):
            url = u'http://tesalliance.org/forums/index.php?app' \
                  u'=downloads&showfile=' + ma.group(2)
    return url or u''

class _NotObLink(EnabledLink):

    def _enable(self):
        return not all( # disable on Oblivion (modding) esms
            x.match_oblivion_re() for x in self.iselected_infos())

class Mod_CreateLOOTReport(_NotObLink):
    """Creates a basic LOOT masterlist entry with URL and tags."""
    _text = _('Create LOOT Entry…')
    _help = _('Creates LOOT masterlist entries based on the tags you have '
              'applied to the selected plugins.')

    def Execute(self):
        log_txt = u''
        for i, (fileName, fileInfo) in enumerate(self.iselected_pairs()):
            if fileName == bush.game.master_file: continue
            # Gather all tags applied after the description (including existing
            # LOOT tags - we'll want to replace the existing LOOT entry with
            # this one after all)
            desc_tags = fileInfo.getBashTagsDesc()
            curr_tags = fileInfo.getBashTags()
            added = curr_tags - desc_tags
            removed = desc_tags - curr_tags
            # Name of file, plus a link if we can figure it out
            log_txt += u"  - name: '%s'\n" % fileName
            inst = fileInfo.get_table_prop(u'installer', u'')
            if inst:
                log_txt += u"    url: [ '%s' ]\n" % _getUrl(inst)
            # Tags applied after the description
            fmt_tags = sorted(added | {u'-%s' % t for t in removed})
            if fmt_tags:
                if len(fmt_tags) == 1:
                    log_txt += u'    tag: [ %s ]\n' % fmt_tags[0]
                else:
                    log_txt += u'    tag:\n'
                    for fmt_tag in fmt_tags:
                        log_txt += u'      - %s\n' % fmt_tag
        # Show results + copy to clipboard
        copy_text_to_clipboard(log_txt)
        self._showLog(log_txt, title=_('LOOT Entry'))

class Mod_CopyModInfo(ItemLink):
    """Copies the basic info about selected mod(s)."""
    _text = _('Copy Plugin Info…')
    _help = _('Copy some basic information about the selected plugins.')

    def Execute(self):
        info_txt = []
        # Create the report
        for fname, fileInfo in self.iselected_pairs():
            mod_text = [_('Plugin: %(plugin_file)s') % {'plugin_file': fname}]
            #-- Name of file, plus a link if we can figure it out
            linked_installer = fileInfo.get_table_prop('installer', '')
            if linked_installer:
                installer_url = _getUrl(linked_installer)
                if installer_url:
                    mod_text.append(_('URL: %(linked_url)s') % {
                        'linked_url': installer_url})
            labels = self.window.labels
            for col in self.window.allowed_cols:
                if col != 'File':
                    lab = labels[col](self.window, fname)
                    mod_text.append(f'{col}: {lab if lab else "-"}')
            #-- Version, if it exists
            if vers := fileInfo.get_version():
                mod_text.append(_('Version: %(plugin_ver)s') % {
                    'plugin_ver': vers})
            info_txt.append('\n'.join(mod_text))
        info_txt = '\n\n'.join(info_txt) # add a blank line in between mods
        if len(self.selected) > 5:
            info_txt = f'[spoiler]\n{info_txt}\n[/spoiler]'
        # Show results + copy to clipboard
        copy_text_to_clipboard(info_txt)
        self._showLog(info_txt, title=_('Plugin Info Report'))

#------------------------------------------------------------------------------
class Mod_ListDependent(OneItemLink):
    """Copies list of dependents to clipboard."""
    _text = _('List Dependent…')

    @property
    def link_help(self):
        return _('Displays and copies to the clipboard a list of plugins that '
                 'have %(master_name)s as master.') % (
            {'master_name': self._selected_item})

    def Execute(self):
        dependent = ListDependentDialog.make_highlight_entry(
            _('The following plugins are dependent on %(master_name)s, '
              'meaning they have that plugin as a master.') % {
                'master_name': self._selected_item},
            load_order.get_ordered(self._selected_info.get_dependents()),
        )
        ListDependentDialog(self.window,
            highlight_items=[dependent]).show_modeless()

# Ghosting --------------------------------------------------------------------
#------------------------------------------------------------------------------
class _GhostLink(ItemLink):
    # usual case, toggle ghosting and ghost inactive if allowed after toggling
    @staticmethod
    def setAllow(filename): return not _GhostLink.getAllow(filename)
    @staticmethod
    def toGhost(filename): return _GhostLink.getAllow(filename) and \
        not load_order.cached_is_active(filename) # cannot ghost active mods
    @staticmethod
    def getAllow(filename):
        return bosh.modInfos[filename].get_table_prop('allowGhosting', True)

    def Execute(self):
        """Loop selected files applying allow ghosting settings and
        (un)ghosting as needed."""
        ghost_changed = []
        set_allow = self.__class__.setAllow
        to_ghost = self.__class__.toGhost
        for fileName, fileInfo in self.iselected_pairs():
            fileInfo.set_table_prop('allowGhosting', set_allow(fileName))
            if fileInfo.setGhost(to_ghost(fileName)):
                ghost_changed.append(fileName)
        self.refresh_sel(ghost_changed)

class _Mod_AllowGhosting_All(_GhostLink, ItemLink):
    _text, _help = _(u'Allow Ghosting'), _(u'Allow Ghosting for selected mods')
    setAllow = staticmethod(lambda fname: True) # allow ghosting
    toGhost = staticmethod(lambda fname:not load_order.cached_is_active(fname))

#------------------------------------------------------------------------------
class _Mod_DisallowGhosting_All(_GhostLink, ItemLink):
    _text = _(u'Disallow Ghosting')
    _help = _(u'Disallow Ghosting for selected mods')
    setAllow = staticmethod(lambda filename: False) # disallow ghosting...
    toGhost = staticmethod(lambda filename: False) # ...so unghost if ghosted

#------------------------------------------------------------------------------
class _DirectGhostLink(_GhostLink, EnabledLink):
    setAllow = staticmethod(lambda fname: True) # allow ghosting

    def _enable(self):
        # Enable only if at least one plugin's ghost status would be changed
        ghost_minfs = self._data_store
        return any(self.__class__.toGhost(p) != ghost_minfs[p].is_ghost
                   for p in self.selected)

class _Mod_Ghost(_DirectGhostLink):
    _text = _('Ghost')
    _help = _("Ghost selected plugins. Active plugins can't be ghosted.")
    toGhost = staticmethod(lambda fname: not load_order.cached_is_active(fname))

class _Mod_Unghost(_DirectGhostLink):
    _text = _('Unghost')
    _help = _('Unghost selected plugins.')
    toGhost = staticmethod(lambda fname: False)

class Mod_GhostUnghost(TransLink):
    """Ghost or unghost selected mod(s)."""
    def _decide(self, window, selection):
        # If any of the selected plugins can be ghosted, return the ghosting
        # link - otherwise, default to unghost
        if any(_Mod_Ghost.toGhost(p) != window.data_store[p].is_ghost
               for p in selection):
            return _Mod_Ghost()
        return _Mod_Unghost()

#------------------------------------------------------------------------------
class _Mod_AllowGhostingInvert_All(_GhostLink, ItemLink):
    _text = _(u'Invert Ghosting')
    _help = _(u'Invert Ghosting for selected mods')

#------------------------------------------------------------------------------
class Mod_AllowGhosting(TransLink):
    """Toggles Ghostability."""

    def _decide(self, window, selection):
        if len(selection) == 1:
            class _CheckLink(_GhostLink, CheckLink):
                _text = _(u'Disallow Ghosting')
                _help = _(u'Toggle Ghostability')
                def _check(self): return not self.getAllow(self.selected[0])
            return _CheckLink()
        else:
            subMenu = balt.MenuLink(_('Ghosting..'))
            subMenu.links.append_link(_Mod_AllowGhosting_All())
            subMenu.links.append_link(_Mod_DisallowGhosting_All())
            subMenu.links.append_link(_Mod_AllowGhostingInvert_All())
            return subMenu

# BP Links --------------------------------------------------------------------
#------------------------------------------------------------------------------
class Mod_CheckQualifications(ItemLink):
    """Check various mergeability criteria - BP mergeability, ESL capability
    and MID capability."""
    _text = _('Check Qualifications…')

    @property
    def link_help(self):
        m_checks = bush.game.mergeability_checks
        if MergeabilityCheck.MID_CHECK in m_checks:
            if MergeabilityCheck.ESL_CHECK in m_checks:
                if MergeabilityCheck.MERGE in m_checks:
                    # MID + ESL + Merge
                    return _('Scan the selected plugins to determine '
                             'whether or not they can be merged into the '
                             'Bashed Patch, assigned the ESL flag or assigned '
                             'the MID flag, reporting also the reasons '
                             'if they cannot.')
                # MID + ESL
                return _('Scan the selected plugins to determine whether or '
                         'not they can be assigned the ESL flag or assigned '
                         'the MID flag, reporting also the reasons if '
                         'they cannot.')
            elif MergeabilityCheck.MERGE in m_checks:
                # MID + Merge
                return _('Scan the selected plugins to determine whether or '
                         'not they can be merged into the Bashed Patch or '
                         'assigned the MID flag, reporting also the '
                         'reasons if they cannot.')
            # MID
            return _('Scan the selected plugins to determine whether or not '
                     'they can be assigned the MID flag, reporting also '
                     'the reasons if they cannot.')
        else:
            if MergeabilityCheck.ESL_CHECK in m_checks:
                if MergeabilityCheck.MERGE in m_checks:
                    # ESL + Merge
                    return _('Scan the selected plugins to determine '
                             'whether or not they can be merged into the '
                             'Bashed Patch or assigned the ESL flag, '
                             'reporting also the reasons if they cannot.')
                # ESL
                return _('Scan the selected plugins to determine '
                         'whether or not they can be assigned the ESL flag, '
                         'reporting also the reasons if they cannot.')
            # Merge
            return _('Scan the selected plugins to determine whether or not '
                     'they can be merged into the Bashed Patch, reporting '
                     'also the reasons if they cannot.')

    @balt.conversation
    def Execute(self):
        prog = balt.Progress(self._text + ' ' * 30)
        result = bosh.modInfos.rescanMergeable(self.selected, prog,
                                               return_results=True)
        mergeability_strs = {
            MergeabilityCheck.MERGE: (_('Not Mergeable Into Bashed Patch'),
                                      _('Mergeable Into Bashed Patch')),
            MergeabilityCheck.ESL_CHECK: (_('Not ESL-Capable'),
                                          _('ESL-Capable')),
            MergeabilityCheck.MID_CHECK: (_('Not MID-Capable'),
                                          _('MID-Capable')),
        }
        message = ['= ' + _('Qualification Check Results')]
        for p in self.selected:
            message.append('')
            message.append(f'== {p}')
            for chk_ty, chk_reason in result[p].items():
                message.append('')
                chk_result = not chk_reason # no reason why we shouldn't merge
                message.append(f'=== {mergeability_strs[chk_ty][chk_result]}')
                for r in chk_reason:
                    message.append(f'.    {r}')
        self.refresh_sel()
        self._showWryeLog('\n'.join(message), title=self._text)

#------------------------------------------------------------------------------
class _Mod_BP_Link(OneItemLink):
    """Enabled on Bashed patch items."""
    def _enable(self):
        return super(_Mod_BP_Link, self)._enable() \
               and self._selected_info.isBP()

    def _find_parent_bp(self):
        """Find the correct Bashed Patch to use for working on this BP file.
        Handles both regular BPs and BP parts correctly."""
        bp_parent_str = self._selected_info.get_table_prop('bp_split_parent')
        if bp_parent_str is None:
            return self._selected_info # Not a part
        if bp_parent := bosh.modInfos.get(bp_parent_str):
            return bp_parent # Is a part, found parent
        return None # Is a part, did not find parent

    def _error_no_parent_bp(self):
        """Show an error message for when a BP part could not find its
        parent."""
        self._showError(
            _('This is part of a split Bashed Patch, but Wrye Bash failed '
              'to determine its parent. If you renamed or deleted the '
              'parent, this part may have become detached. In that case, '
              'just delete it and use the main BP to rebuild.'),
            title=_('Detached Bashed Patch Part'))

class Mod_RebuildPatch(_Mod_BP_Link):
    """Updates a Bashed Patch."""
    _text = _('Rebuild Patch…')
    _help = _(u'Rebuild the Bashed Patch')

    @balt.conversation
    def Execute(self):
        """Handle activation event."""
        self._reactivate_mods, self._bps = set(), []
        try:
            if not self._execute_bp(self._find_parent_bp(), bosh.modInfos):
                return # prevent settings save
        except CancelError:
            return # prevent settings save
        finally:
            count, resave = 0, False
            to_act = dict.fromkeys(self._bps, True)
            to_act.update(dict.fromkeys(self._reactivate_mods, False))
            for fn_mod, is_bp in to_act.items():
                message = _('Activate %(bp_name)s?') % {'bp_name': fn_mod}
                if not is_bp or load_order.cached_is_active(fn_mod) or (
                        bass.inisettings['PromptActivateBashedPatch'] and
                        self._askYes(message, fn_mod)):
                    try:
                        act = bosh.modInfos.lo_activate(fn_mod, doSave=is_bp)
                        if is_bp and act != [fn_mod]:
                            msg = _('Masters Activated: %(num_activated)d') % {
                                'num_activated': len({*act} - {fn_mod})}
                            Link.Frame.set_status_info(msg)
                        count += len(act)
                        resave |= not is_bp and bool(act)
                    except PluginsFullError:
                        msg = _('Unable to activate plugin %(bp_name)s because'
                            ' the load order is full.') % {'bp_name': fn_mod}
                        self._showError(msg)
                        break # don't keep trying
            if resave:
                bosh.modInfos.cached_lo_save_active()
            self.window.propagate_refresh(Store.SAVES.IF(count))
        # save data to disc in case of later improper shutdown leaving the
        # user guessing as to what options they built the patch with
        Link.Frame.SaveSettings() ##: just modInfos ?

    def _execute_bp(self, patch_info, mod_infos):
        if patch_info is None:
            self._error_no_parent_bp()
            return False
        # Clean up some memory
        bolt.GPathPurge()
        # We need active mods
        if not load_order.cached_active_tuple():
            self._showWarning(
                _('That which does not exist cannot be patched.') + '\n' +
                _('Load some plugins and try again.'),
                title=_('Existential Error'))
            return False
        # Read the config
        bp_config = patch_info.get_table_prop('bash.patch.configs',{})
        if _configIsCBash(bp_config):
            if not self._askYes(
                    _('This patch was built in CBash mode. This is no longer '
                      'supported. You can either use Wrye Bash 307 to '
                      'convert it to PBash format, or you can click "Yes" '
                      'below to make Wrye Bash reset the configuration to '
                      'default. If you click "No", the patch building will '
                      'abort now.'), title=_('Unsupported CBash Patch')):
                return False
            bp_config = {}
        # Create the PatchFile instance
        bashed_patch = PatchFile(patch_info, mod_infos)
        #--Check if we should be deactivating some plugins
        if self._ask_deactivate_mergeable(bashed_patch):
            # we might have de-activated plugins so recalculate active sets
            bashed_patch.set_active_arrays(bosh.modInfos)
        missing, delinquent = bashed_patch.active_mm, bashed_patch.delinquent
        bp_master_errors = []
        if missing:
            bp_master_errors.append(MasterErrorsDialog.make_highlight_entry(_(
                'The following plugins have missing masters and are active. '
                'This will cause the game to crash. Please disable them.'),
                missing))
        if delinquent:
            bp_master_errors.append(MasterErrorsDialog.make_highlight_entry(_(
                'These mods have delinquent masters, which means they load '
                'before their masters. This is undefined behavior. Please '
                'adjust your load order to fix this.'), delinquent))
        if bp_master_errors:
            MasterErrorsDialog.display_dialog(self.window,
                highlight_items=bp_master_errors)
            return False
        # No errors, proceed with building the BP
        PatchDialog.display_dialog(self.window, bashed_patch,
                                   self._bps, bp_config)
        return True

    def _ask_deactivate_mergeable(self, bashed_patch):
        merge, noMerge, deactivate = [], [], []
        mergeable = MergeabilityCheck.MERGE.cached_types(
            bashed_patch.p_file_minfos)[0]
        for mod in bashed_patch.load_dict:
            mod_inf = bosh.modInfos[mod]
            tags = mod_inf.getBashTags()
            if mod_inf in mergeable:
                if 'MustBeActiveIfImported' in tags:
                    continue
                elif 'NoMerge' in tags:
                    noMerge.append(mod)
                else:
                    merge.append(mod)
            elif 'Deactivate' in tags:
                deactivate.append(mod)
        if not merge and not noMerge and not deactivate:
            return False # Nothing to deselect
        dbp_result = DeactivateBeforePatchEditor.display_dialog(self.window,
            plugins_mergeable=merge, plugins_nomerge=noMerge,
            plugins_deactivate=deactivate)
        ed_ok, ed_mergeable, ed_nomerge, ed_deactivate = dbp_result
        to_deselect = set(chain(ed_mergeable, ed_nomerge, ed_deactivate))
        if not ed_ok or not to_deselect:
            return False # Aborted by user or nothing left enabled
        self._reactivate_mods = ed_nomerge
        with BusyCursor():
            bosh.modInfos.lo_deactivate(*to_deselect, doSave=True)
            self.window.propagate_refresh(Store.SAVES.DO())
        return True

#------------------------------------------------------------------------------
class Mod_ListPatchConfig(_Mod_BP_Link):
    """Lists the Bashed Patch configuration and copies to the clipboard."""
    _text = _('List Patch Config…')
    _help = _('Lists the Bashed Patch configuration and copies it to the '
              'clipboard.')

    def Execute(self):
        #--Config
        bp_parent_info = self._find_parent_bp()
        if bp_parent_info is None:
            self._error_no_parent_bp()
            return
        config = bp_parent_info.get_table_prop('bash.patch.configs', {})
        # Detect and warn about patch mode
        if _configIsCBash(config):
            self._showError(_(u'The selected patch was built in CBash mode, '
                              u'which is no longer supported by this version '
                              u'of Wrye Bash.'),
                title=_(u'Unsupported CBash Patch'))
            return
        _gui_patchers = [copy.deepcopy(x) for x in all_gui_patchers]
        #--Log & Clipboard text
        log = bolt.LogFile(io.StringIO())
        log.setHeader('= %s %s' % (bp_parent_info.fn_key, _('Config')))
        log(_('This is the current configuration of this Bashed Patch. This '
              'report has also been copied into your clipboard.') + '\n')
        clip = io.StringIO()
        clip.write('%s %s:\n' % (bp_parent_info.fn_key, _('Config')))
        clip.write(u'[spoiler]\n')
        log.setHeader(u'== '+_(u'Patch Mode'))
        clip.write(u'== '+_(u'Patch Mode')+u'\n')
        log(u'Python')
        clip.write(u' ** Python\n')
        temp_bp = PatchFile(bp_parent_info, bosh.modInfos)
        for patcher in _gui_patchers:
            patcher._bp = temp_bp
            patcher.log_config(config, clip, log)
        #-- Show log
        clip.write(u'[/spoiler]')
        copy_text_to_clipboard(clip.getvalue())
        log_text = log.out.getvalue()
        self._showWryeLog(log_text, title=_(u'Bashed Patch Configuration'))

# Cleaning submenu ------------------------------------------------------------
#------------------------------------------------------------------------------
class _DirtyLink(ItemLink):
    def _ignoreDirty(self, fileInfo): raise NotImplementedError

    def Execute(self):
        for fileName, fileInfo in self.iselected_pairs():
            fileInfo.set_table_prop(u'ignoreDirty',
                                    self._ignoreDirty(fileName))
        self.refresh_sel()

class _Mod_SkipDirtyCheckAll(_DirtyLink, CheckLink):
    _help = _("Set whether to check or not the selected plugins against "
              "LOOT's dirty plugins list.")

    def __init__(self, bSkip):
        super(_Mod_SkipDirtyCheckAll, self).__init__()
        self.skip = bSkip
        self._text = (_("Don't Check Against LOOT's Masterlist") if self.skip
                      else _("Check Against LOOT's Masterlist"))

    def _check(self):
        return all(finf.get_table_prop('ignoreDirty', False) == self.skip
                   for finf in self.iselected_infos())

    def _ignoreDirty(self, fileInfo): return self.skip

class _Mod_SkipDirtyCheckInvert(_DirtyLink, ItemLink):
    _text = _("Invert Checking Against LOOT's Masterlist")
    _help = _("Invert checking against LOOT's dirty plugins list for selected "
              "plugins.")

    def _ignoreDirty(self, fileInfo):
        return not fileInfo.get_table_prop('ignoreDirty', False)

class Mod_SkipDirtyCheck(TransLink):
    """Toggles scanning for dirty mods on a per-mod basis."""

    def _decide(self, window, selection):
        if len(selection) == 1:
            class _CheckLink(_DirtyLink, CheckLink):
                _text = _("Don't Check Against LOOT's Masterlist")
                _help = _("Toggles scanning for dirty plugins against LOOT's "
                          "masterlist on a per-plugin basis.")

                def _check(self): return next(self.iselected_infos()
                    ).get_table_prop(u'ignoreDirty', False)
                def _ignoreDirty(self, fileInfo): return self._check() ^ True

            return _CheckLink()
        else:
            subMenu = balt.MenuLink(_('Dirty Edit Scanning..'))
            subMenu.links.append_link(_Mod_SkipDirtyCheckAll(True))
            subMenu.links.append_link(_Mod_SkipDirtyCheckAll(False))
            subMenu.links.append_link(_Mod_SkipDirtyCheckInvert())
            return subMenu

#------------------------------------------------------------------------------
class Mod_ScanDirty(ItemLink):
    """Give detailed printout of what Wrye Bash is detecting as UDR records."""
    _text = _('Scan for Deleted Records')
    _help = _('Gives a detailed report of deleted records in the selected '
              'plugins.')

    def Execute(self):
        """Handle execution"""
        all_present_minfs = dict(self.iselected_pairs())
        # This part of the method shares a lot of code with
        # mods_metadata.checkMods, but we can't deduplicate because the
        # performance hit to checkMods would be too great :(
        # I kept the names unchanged so that it's easier to see what's just
        # copy-pasted in case refactoring becomes possible in the future. See
        # there for comments on what this is doing as well.
        game_master_name = bush.game.master_file
        all_deleted_refs = defaultdict(list) # fn_key -> list[fid]
        all_deleted_navms = defaultdict(list) # fn_key -> list[fid]
        all_deleted_others = defaultdict(list) # fn_key -> list[fid]
        try:
            with balt.Progress(_('Deleted Records'), abort=True) as progress:
                progress.setFull(len(all_present_minfs))
                load_progress = SubProgress(progress, 0, 0.7)
                load_progress.setFull(len(all_present_minfs))
                all_extracted_data = {}
                for i, (fn, present_minf) in enumerate(
                        all_present_minfs.items()):
                    if fn == game_master_name:
                        continue # The game master can't have deleted records
                    mod_progress = SubProgress(load_progress, i, i + 1)
                    ext_data = ModHeaderReader.extract_mod_data(present_minf,
                                                                mod_progress)
                    all_extracted_data[fn] = ext_data
                if all_extracted_data:
                    scan_progress = SubProgress(progress, 0.7, 0.9)
                    scan_progress.setFull(len(all_extracted_data))
                all_ref_types = RecordType.sig_to_class[b'CELL'].ref_types
                for i, (plugin_fn, ext_data) in enumerate(
                        all_extracted_data.items()):
                    scan_progress(i, (_('Scanning: %(scanning_plugin)s') % {
                        'scanning_plugin': plugin_fn}))
                    add_deleted_ref = all_deleted_refs[plugin_fn].append
                    add_deleted_navm = all_deleted_navms[plugin_fn].append
                    add_deleted_rec = all_deleted_others[plugin_fn].append
                    for r, d in ext_data.items():
                        for r_header, r_eid in d:
                            if r_header.flags1 & 0x00000020:
                                if (w_rec_type := r_header.recType) == b'NAVM':
                                    add_deleted_navm(r_header.fid)
                                elif w_rec_type in all_ref_types:
                                    add_deleted_ref(r_header.fid)
                                else:
                                    add_deleted_rec(r_header.fid)
        except CancelError:
            return
        log = bolt.LogFile(io.StringIO())
        log.setHeader(u'= '+_(u'Deleted Records'))
        log(_('This is a report of deleted records that were found in the '
              'selected plugins.') + u'\n')
        # Change a FID to something more useful for displaying
        def _log_fids(del_title, del_fids):
            nonlocal full_dirty_msg
            mod_masters = modInfo.masterNames
            len_mas = len(mod_masters)
            full_dirty_msg += '\n'.join([f'  * {del_title}: {len(del_fids)}',
                *(f"    * "
                  f"{_('%(dirty_formid)s (from master %(orig_master)s)')} " % {
                    'dirty_formid': f'{d_fid.short_fid:08X}',
                    'orig_master': mod_masters[min(d_fid.mod_dex, len_mas - 1)]
                } for d_fid in sorted(del_fids))])
        dirty_plugins = []
        clean_plugins = []
        skipped_plugins = []
        for i, (plugin_fn, modInfo) in enumerate(all_present_minfs.items()):
            del_navms = all_deleted_navms[plugin_fn]
            del_refs = all_deleted_refs[plugin_fn]
            del_others = all_deleted_others[plugin_fn]
            if plugin_fn == game_master_name or plugin_fn.fn_ext == '.esu':
                skipped_plugins.append(f'* __{modInfo}__')
            elif del_navms or del_refs or del_others:
                full_dirty_msg = f'* __{modInfo}__:\n'
                if del_navms:
                    _log_fids(_('Deleted Navmeshes'), del_navms)
                if del_refs:
                    _log_fids(_('Deleted References'), del_refs)
                if del_others:
                    _log_fids(_('Deleted Base Records'), del_others)
                dirty_plugins.append(full_dirty_msg)
            else:
                clean_plugins.append(f'* __{modInfo}__')
        if dirty_plugins:
            log(_('Detected %(num_dirty_plugins)d plugins with deleted '
                  'records:') % {'num_dirty_plugins': len(dirty_plugins)})
            for p in dirty_plugins:
                log(p)
            log(u'\n')
        if clean_plugins:
            log(_('Detected %(num_clean_plugins)d plugins without deleted '
                  'records:') % {'num_clean_plugins': len(clean_plugins)})
            for p in clean_plugins:
                log(p)
            log(u'\n')
        if skipped_plugins:
            log(_('Skipped %(num_skipped_plugins)d plugins:') % {
                'num_skipped_plugins': len(skipped_plugins)})
            for p in skipped_plugins:
                log(p)
            log(u'\n')
        self._showWryeLog(log.out.getvalue(), asDialog=False,
            title=_('Scan for Deleted Records - Report'))

#------------------------------------------------------------------------------
class Mod_RemoveWorldOrphans(_NotObLink, _LoadLink):
    """Remove orphaned cell records."""
    _text = _(u'Remove World Orphans')
    _help = _(u'Remove orphaned cell records')
    _load_sigs = [b'CELL', b'WRLD']

    def Execute(self):
        message = _('In some circumstances, editing a plugin will leave '
                    'orphaned cell (CELL) records in the worldspace (WRLD) '
                    'group. This command will remove such orphans.')
        if not self._askContinue(message, 'bash.removeWorldOrphans.continue',
                title=_('Remove World Orphans')): return
        for index, (fileName, fileInfo) in enumerate(self.iselected_pairs()):
            if fileInfo.match_oblivion_re():
                self._showWarning(_('Skipping %(skipping_plugin)s.') % {
                    'skipping_plugin': fileInfo},
                    title=_('Remove World Orphans'))
                continue
            #--Export
            with balt.Progress(_('Remove World Orphans')) as progress:
                progress(0, _('Reading %(reading_plugin)s.') % {
                    'reading_plugin': fileInfo})
                modFile = self._load_mod(fileInfo,
                    progress=SubProgress(progress, 0, 0.7))
                orphans = (b'WRLD' in modFile.tops) and modFile.tops[b'WRLD'].orphansSkipped
                if orphans:
                    progress(0.1, _('Saving %(saving_plugin)s.') % {
                        'saving_plugin': fileInfo})
                    modFile.safeSave() ##: todo setChanged?
                progress(1.0, _('Done.'))
            #--Log
            if orphans:
                self._showOk(_('Orphan cell blocks removed: '
                               '%(num_orphans_removed)d.') % {
                    'num_orphans_removed': orphans}, fileName)
            else:
                self._showOk(_('No changes required.'), fileName)

#------------------------------------------------------------------------------
class Mod_FogFixer(ItemLink):
    """Fix fog on selected cells."""
    _text = _('Nvidia Fog Fix')
    _help = _('Modify fog values in interior cells to avoid the Nvidia black '
              'screen bug')

    def Execute(self):
        message = _('Apply Nvidia fog fix. This modifies fog values in '
                    'interior cells to avoid the Nvidia black screen bug.')
        if not self._askContinue(message, u'bash.cleanMod.continue',
                                 _(u'Nvidia Fog Fix')): return
        fixed = {}
        with balt.Progress(_(u'Nvidia Fog Fix')) as progress:
            progress.setFull(len(self.selected))
            for index,(fileName,fileInfo) in enumerate(self.iselected_pairs()):
                if fileName == bush.game.master_file: continue
                progress(index, _('Scanning %(scanning_plugin)s') % {
                    'scanning_plugin': fileName})
                fog_fixer = bosh.mods_metadata.NvidiaFogFixer(fileInfo)
                fog_fixer.fix_fog(SubProgress(progress, index, index + 1))
                if fog_fixer.fixedCells:
                    fixed[fileName] = fog_fixer.fixedCells
        if fixed:
            message = '===' + _('Cells Fixed:') + '\n' + '\n'.join([
                f'* {fixed_pname}: {len(cells_fixed)}'
                for fixed_pname, cells_fixed in fixed.items()])
            self._showWryeLog(message)
            self.refresh_sel(fixed)
        else:
            message = _(u'No changes required.')
            self._showOk(message)

# Rest of menu Links ----------------------------------------------------------
#------------------------------------------------------------------------------
class _CopyToLink(EnabledLink):
    def __init__(self, plugin_ext):
        super().__init__(plugin_ext)
        self._target_ext = plugin_ext
        self._help = _('Creates a copy of the selected plugins with the '
                       'extensions changed to %(new_plugin_ext)s.') % {
            'new_plugin_ext': plugin_ext}

    def _enable(self):
        return any(p.get_extension() != self._target_ext
                   for p in self.iselected_infos())

    @balt.conversation
    def Execute(self):
        modInfos, added = bosh.modInfos, {}
        pflags = bush.game.plugin_flags
        force_flags = pflags.guess_flags(self._target_ext, bush.game)
        force_flags = pflags.check_flag_assignments(force_flags)
        mod_previous = FNDict()
        with BusyCursor(): # ONAM generation can take a bit
            for curName, minfo in self.iselected_pairs():
                if self._target_ext == curName.fn_ext: continue
                newName = FName(f'{curName.fn_body}{self._target_ext}')
                #--Replace existing file?
                newTime = None
                if newName in modInfos:
                    existing = modInfos[newName]
                    # abs_path as existing may be ghosted
                    if not self._askYes(
                            _('Replace existing %(existing_plugin)s?') % {
                                'existing_plugin': existing.abs_path.stail}):
                        continue
                    existing.makeBackup()
                    newTime = existing.ftime
                # Copy and set flag - will use ghosted path if needed
                minfo.copy_to(minfo.info_dir.join(newName), set_time=newTime)
                added[newName] = minfo
                if newTime is None: # otherwise it has a load order already!
                    mod_previous[newName] = curName
        #--Repopulate
        if added:
            rinf = RefrIn.from_tabled_infos(added, exclude=True)
            rdata = modInfos.refresh(rinf, insert_after=mod_previous)
            if force_flags:
                for new in rdata.to_add:
                    bosh.modInfos[new].set_plugin_flags(force_flags)
            self.window.propagate_refresh(Store.SAVES.DO(),
                                  detail_item=next(reversed(added)))
            self.window.SelectItemsNoCallback(added)

class Mod_CopyToMenu(MenuLink):
    """Makes copies of the selected plugin(s) with changed extension."""
    _text = _('Copy To..')

    def __init__(self):
        super(Mod_CopyToMenu, self).__init__()
        for plugin_ext in sorted(bush.game.espm_extensions):
            self.append(_CopyToLink(plugin_ext))

#------------------------------------------------------------------------------
class Mod_DecompileAll(_NotObLink, _LoadLink):
    """Removes effects of a "recompile all" on the mod."""
    _text = _(u'Decompile All')
    _help = _(u'Removes effects of a "recompile all" on the mod')
    _load_sigs = [b'SCPT']

    def Execute(self):
        message = _("This command will remove the effects of a 'Compile All' "
                    "by removing all scripts whose sources appear to be "
                    "identical to the last version that they override.")
        if not self._askContinue(message, u'bash.decompileAll.continue',
                                 _(u'Decompile All')): return
        with BusyCursor():
            for fileInfo in self.iselected_infos():
                if fileInfo.match_oblivion_re():
                    self._showWarning(_('Skipping %(skipping_plugin)s') % {
                        'skipping_plugin': fileInfo}, title=_('Decompile All'))
                    continue
                modFile = self._load_mod(fileInfo)
                badGenericLore = False
                removed = []
                id_text = {}
                if scpt_grp := modFile.tops.get(b'SCPT'):
                    master_factory = self._load_fact(keepAll=False)
                    for master in modFile.tes4.masters:
                        masterFile = self._load_mod(bosh.modInfos[master],
                                                    load_fact=master_factory)
                        for rfid, r in masterFile.tops[b'SCPT'].iter_present_records():
                            id_text[rfid] = r.script_source
                    newRecords = {}
                    generic_lore_fid = bush.game.master_fid(0x025811)
                    for rfid, record in scpt_grp.iter_present_records():
                        #--Special handling for genericLoreScript
                        if (rfid in id_text and rfid == generic_lore_fid and
                            record.compiled_size == 4 and
                            record.last_index == 0):
                            removed.append(record.eid)
                            badGenericLore = True
                        elif (rfid in id_text and
                              id_text[rfid] == record.script_source):
                            removed.append(record.eid)
                        else:
                            # don't bother with record.group_key() for 'SCPT'
                            record.setChanged()
                            newRecords[rfid] = record
                    scpt_grp.id_records = newRecords
                if len(removed) >= 50 or badGenericLore:
                    modFile.safeSave()
                    msg = '\n'.join([
                        _('Scripts removed: %(num_scripts_removed)d.'),
                        _('Scripts remaining: %(num_scripts_remaining)d'),
                    ]) % {'num_scripts_removed': len(removed),
                          'num_scripts_remaining': len(scpt_grp.id_records)}
                elif removed:
                    msg = _('Only %(num_scripts_removed)d scripts were '
                            'identical. This is probably intentional, so no '
                            'changes have been made.') % {
                        'num_scripts_removed': len(removed)}
                else:
                    msg = _('No changes required.')
                self._showOk(msg, fileInfo.fn_key)

#------------------------------------------------------------------------------
class AFlipFlagLink(EnabledLink):
    """Base class for links that enable or disable a flag in the plugin
    header."""

    def __init__(self, plugin_flag: PluginFlag | None = None):
        super().__init__()
        self._plugin_flag: PluginFlag = plugin_flag
        self._allowed_ext = plugin_flag.convert_exts
        self._continue_msg = plugin_flag.continue_message
        self._help = plugin_flag.help_flip

    def _initData(self, window, selection):
        super()._initData(window, selection)
        first_flagged = self._plugin_flag.has_flagged(self._first_selected())
        self._flag_value = not first_flagged # flip the (common) flag value
        do_enable = all(
            self._can_convert(k, v) for k, v in self.iselected_pairs())
        self._to_flip = [*self.iselected_infos()] if do_enable else []

    def _can_convert(self, fn_mod, m):
        """Allow if all selected mods have valid extensions, have the same
        flag state and are capable to be flagged with self._plugin_flag."""
        pf = self._plugin_flag
        return fn_mod.fn_ext in self._allowed_ext and pf.has_flagged(
            m) != self._flag_value and (not self._flag_value or not hasattr(
            pf, 'merge_check') or (pf.merge_check in m.merge_types()))

    def _enable(self): return bool(self._to_flip)

    @property
    def link_text(self):
        return (_('Add %(pflag)s Flag') if self._flag_value else _(
          'Remove %(pflag)s Flag')) % {'pflag': self._plugin_flag.name} # .title()}

    @balt.conversation
    def Execute(self):
        with BusyCursor():
            if self._continue_msg and not self._askContinue(
                    *self._continue_msg): return
            # if _flag_value=True no other conflicting flags should be on
            set_flags = {self._plugin_flag: self._flag_value}
            for minfo in self._to_flip:
                minfo.set_plugin_flags(set_flags)
            ##: HACK: forcing active refresh cause mods may be reordered and
            # we then need to sync order in skyrim's plugins.txt
            ldiff = bosh.modInfos.refreshLoadOrder()
            # This will have changed the plugin, so let BAIN know
            bosh.modInfos._notify_bain(
                altered={p.abs_path for p in self.iselected_infos()})
            # We need to RefreshUI all higher-loading plugins than the lowest
            # plugin that was affected to update the Indices column
            rdata = ldiff.to_rdata()
            rdata.redraw.update(self.selected)
            self.window.propagate_refresh(Store.SAVES.DO(), rdata=rdata)

#------------------------------------------------------------------------------
class Mod_FlipMasters(OneItemLink, AFlipFlagLink):
    """Swaps masters between esp and esm versions."""
    _help = _(u'Flips the ESM flag on all masters of the selected plugin, '
              u'allowing you to load it in the %(ck_name)s.') % (
              {u'ck_name': bush.game.Ck.long_name})
    _continue_msg = (_('WARNING! For advanced modders only! Flips the ESM flag '
        'of all ESP masters of the selected plugin. Useful for '
        'loading ESP-mastered mods in the %(ck_name)s.') % {
            'ck_name': bush.game.Ck.long_name}, 'bash.flipMasters.continue')

    def __init__(self):
        super(AFlipFlagLink, self).__init__()
        self._plugin_flag = bush.game.master_flag

    def _initData(self, window, selection):
        super(AFlipFlagLink, self)._initData(window, selection)
        present_mods = window.data_store
        modinfo_masters = present_mods[selection[0]].masterNames
        if len(selection) == 1 and len(modinfo_masters) > 1:
            self._to_flip = [present_mods[m] for m in # espMasters
                modinfo_masters if m in present_mods and m.fn_ext == '.esp']
            # for refresh in Execute - selection is shared with all other links
            self.selected = [selection[0], *self._to_flip]
        else:
            self._to_flip = []
        # all elements in _to_flip have an .esp extension - check the esm flag
        self._flag_value = not any(map(bush.game.master_flag.has_flagged,
                                       self._to_flip))

    @property
    def link_text(self):
        return _('Add ESM Flag to Masters') if self._flag_value else _(
            'Remove ESM Flag From Masters')

#------------------------------------------------------------------------------
class Mod_SetVersion(OneItemLink):
    """Sets version of file back to 0.8."""
    _text = _('Version 0.8')
    _help = _('Sets header version of the selected plugin back to 0.8.')
    message = _('WARNING! For advanced modders only! This feature allows you '
                'to edit newer official plugins in the %(ck_name)s by '
                'resetting the internal header version number back to 0.8. '
                'While this will make the plugin editable, it may also break '
                'the plugin in unpredictable ways.') % {
        'ck_name': bush.game.Ck.long_name}

    def _enable(self):
        return (super(Mod_SetVersion, self)._enable() and
                int(10 * self._selected_info.header.version) != 8)

    def Execute(self):
        if not self._askContinue(self.message, 'bash.setModVersion.continue',
                title=self._text):
            return
        self._selected_info.makeBackup()
        self._selected_info.header.version = 0.8
        self._selected_info.header.setChanged()
        self._selected_info.writeHeader()
        self.refresh_sel()

#------------------------------------------------------------------------------
# Import/Export submenus ------------------------------------------------------
#------------------------------------------------------------------------------
#--Import only
class Mod_Fids_Replace(OneItemLink):
    """Replace fids according to text file."""
    _text = _('Form IDs…')
    _help = _(u'Replace fids according to text file')
    message = _(u'For advanced modders only! Systematically replaces one set '
        u'of Form Ids with another in npcs, creatures, containers and leveled '
        u'lists according to a Replacers.csv file.')

    @staticmethod
    def _parser():
        return FidReplacer()

    def Execute(self):
        if not self._askContinue(self.message, 'bash.formIds.replace.continue',
                                 _(u'Import Form IDs')): return
        textDir = bass.dirs[u'patches']
        #--File dialog
        textPath = self._askOpen(_('Form ID mapper file:'), textDir, '',
                                 '*_Formids.csv')
        if not textPath: return
        #--Extension error check
        if textPath.cext != u'.csv':
            self._showError(_(u'Source file must be a csv file.'))
            return
        #--Export
        with balt.Progress(_(u'Import Form IDs')) as progress:
            replacer = self._parser()
            progress(0.1, _('Reading %(reading_file)s.') % {
                'reading_file': textPath.stail})
            replacer.read_csv(textPath)
            progress(0.2, _('Applying to %(applying_plugin)s.') % {
                'applying_plugin': self._selected_item})
            fids_changed = replacer.updateMod(self._selected_info)
            progress(1.0,_(u'Done.'))
        #--Log
        if not fids_changed: self._showOk(_(u'No changes required.'))
        else:
            self._showLog(fids_changed, title=_('Objects Changed'),
                          asDialog=True)

class Mod_Face_Import(OneItemLink):
    """Imports a face from a save to an esp."""
    _text = _('Face…')
    _help = _(u'Imports a face from a save to an ESP file.')

    def Execute(self):
        #--Select source face file
        srcDir = bosh.saveInfos.store_dir
        wildcard = (_('%(game_name)s Saves') +
                    ' (*%(save_ext_on)s;*%(save_ext_off)s)|*%(save_ext_on)s;'
                    '*%(save_ext_off)s') % {
            'game_name': bush.game.display_name,
            'save_ext_on': bush.game.Ess.ext,
            'save_ext_off': bush.game.Ess.ext[:-1] + 'r'}
        #--File dialog
        srcPath = self._askOpen(_('Face Source:'), defaultDir=srcDir,
                                wildcard=wildcard)
        if not srcPath: return
        #--Get face
        srcInfo = bosh.SaveInfo(srcPath, load_cache=True)
        srcFace = bosh.faces.PCFaces.save_getPlayerFace(srcInfo)
        #--Save Face
        npc = bosh.faces.PCFaces.mod_addFace(self._selected_info, srcFace)
        ##: Saves an image of the save file's screenshot for some reason?
        imagePath = bosh.modInfos.store_dir.join(u'Docs', u'Images', npc.eid + u'.jpg')
        if not imagePath.exists():
            srcInfo.header.read_save_header(load_image=True)
            image = BmpFromStream(*srcInfo.header.image_parameters)
            imagePath.head.makedirs()
            image.save_bmp(imagePath.s)
        self.refresh_sel()
        self._showOk(_('Imported face to: %(target_npc_edid)s') % {
            'target_npc_edid': npc.eid}, title=self._selected_item)

#--Common
class _Import_Export_Link(AppendableLink):
    """Mixin for Export and Import links that handles adding them automatically
    depending on the game's record types."""
    def _append(self, window):
        test_parser = self._parser()
        try:
            # Check if all record types required by this parser exist for this
            # game and are supported for loading
            return all(sig in bush.game.mergeable_sigs
                       for sig in test_parser.all_types)
        except AttributeError:
            # FIXME(inf) old-style export link, drop once parsers refactored
            return True

class _Mod_Export_Link(_Import_Export_Link, _CsvExport_Link):
    def Execute(self):
        textPath = self._csv_out(
            f'{self.selected[0].fn_body}{self.__class__.csvFile}')
        if not textPath: return
        #--Export
        lo_plugins_set = set(self.window.data_store)
        with balt.Progress(self.__class__.progressTitle) as progress:
            parser = self._parser()
            readProgress = SubProgress(progress, 0.1, 0.8)
            readProgress.setFull(len(self.selected))
            for index,(fileName,fileInfo) in enumerate(self.iselected_pairs()):
                e_missing_masters = set(fileInfo.masterNames) - lo_plugins_set
                if e_missing_masters:
                    err_msg = _('%(filename)s is missing one or more masters. '
                                'Without these, a data export is not '
                                'possible:') % {'filename': fileName}
                    err_msg += '\n\n' + '\n'.join([
                        f' - {m}' for m in e_missing_masters])
                    self._showError(err_msg, title=_('Missing Masters'))
                    return
                readProgress(index, _('Reading %(reading_plugin)s.') % {
                    'reading_plugin': fileName})
                parser.readFromMod(fileInfo)
            progress(0.8, _('Exporting to %(exporting_file)s.') % {
                'exporting_file': textPath.stail})
            parser.write_text_file(textPath)
            progress(1.0, _('Done.'))

    def _parser(self): raise NotImplementedError

class _Mod_Import_Link(_Import_Export_Link, OneItemLink):
    noChange = _(u'No changes required.')
    supportedExts = {u'.csv'}
    progressTitle = continueInfo = continueKey = u'OVERRIDE'
    _parser_class = _AParser

    def _parser(self): return self.__class__._parser_class()
    @property
    def _wildcard(self):
        if len(self.supportedExts) == 1: return u'*' + self.__class__.csvFile
        espml = u';*'.join(bush.game.espm_extensions)
        return _(u'Mod/Text File') + u'|*' + self.__class__.csvFile + u';*' \
               + espml + u';*.ghost'

    def _import_from(self):
        textName = self._selected_item.fn_body + self.__class__.csvFile
        textDir = bass.dirs[u'patches']
        #--File dialog
        textPath = self._askOpen(self.__class__.askTitle, textDir, textName,
                                 self._wildcard)
        return textPath

    def _import(self, ext, textPath):
        with balt.Progress(self.__class__.progressTitle) as progress:
            parser = self._parser()
            progress(0.1, _('Reading %(reading_file)s.') % {
                'reading_file': textPath.stail})
            if ext == u'.csv':
                parser.read_csv(textPath)
            else:
                srcInfo = bosh.ModInfo(textPath)
                parser.readFromMod(srcInfo)
            progress(0.2, _('Applying to %(applying_plugin)s.') % {
                'applying_plugin': self._selected_item})
            changes = parser.writeToMod(self._selected_info)
            progress(1.0, _('Done.'))
        return changes

    def _showLog(self, logText, title='', asDialog=False):
        super()._showLog(logText, title=title or self.__class__.progressTitle,
                         asDialog=asDialog)

    def _log(self, changes, fileName):
        self._showLog(f'* {changes:03d}  {fileName}\n')

    def show_change_log(self, changes, fileName): ##: implement for Scripts
        if not changes:
            self._showOk(self.__class__.noChange, self.__class__.progressTitle)
        else:
            self._log(changes, fileName)

    def Execute(self):
        if not self._askContinueImport(): return
        supportedExts = self.__class__.supportedExts
        csv_filename = self.__class__.csvFile
        textPath = self._import_from()
        if not textPath: return
        #--Extension error check
        ext = textPath.cext
        if ext not in supportedExts:
            plugin_exts = ', '.join(sorted(bush.game.espm_extensions
                                           | {'.ghost'}))
            if len(supportedExts) > 1:
                csv_err = _('Source file must be a %(csv_ext)s file or a '
                            'plugin (%(plugin_exts)s).') % {
                    'csv_ext': csv_filename, 'plugin_exts': plugin_exts}
            else:
                csv_err = _('Source file must be a %(csv_ext)s file.') % {
                    'csv_ext': csv_filename}
            self._showError(csv_err)
            return
        #--Import
        changes = self._import(ext, textPath)
        #--Log
        self.show_change_log(changes, self._selected_item)

    def _askContinueImport(self):
        return self._askContinue(self.__class__.continueInfo,
            self.__class__.continueKey, self.__class__.progressTitle)

#--Links ----------------------------------------------------------------------
class Mod_ActorLevels_Export(_Mod_Export_Link):
    """Export actor levels from mod to text file."""
    askTitle = _(u'Export NPC levels to:')
    csvFile = u'_NPC_Levels.csv'
    progressTitle = _(u'Export NPC levels')
    _text = _('NPC Levels…')
    _help = _(u'Export NPC level info from mod to text file.')

    def _parser(self):
        return ActorLevels()

    def Execute(self): # overrides _Mod_Export_Link
        message = (_(
            'This command will export the level info for NPCs whose level is '
            'offset with respect to the player. The exported file can be '
            'edited with most spreadsheet programs and then '
            'reimported.') + '\n\n' + _(
            'See the Wrye Bash readme for more info.'))
        if not self._askContinue(message, u'bash.actorLevels.export.continue',
                                 _(u'Export NPC Levels')): return
        super(Mod_ActorLevels_Export, self).Execute()

class Mod_ActorLevels_Import(_Mod_Import_Link):
    """Imports actor levels from text file to mod."""
    askTitle = _(u'Import NPC levels from:')
    csvFile = u'_NPC_Levels.csv'
    progressTitle = _(u'Import NPC Levels')
    _text = _('NPC Levels…')
    _help = _(u'Import NPC level info from text file to mod')
    continueInfo = _(
        u'This command will import NPC level info from a previously exported '
        u'file.') + u'\n\n' + _('See the Wrye Bash readme for more info.')
    continueKey = u'bash.actorLevels.import.continue'
    noChange = _(u'No relevant NPC levels to import.')
    _parser_class = ActorLevels

#------------------------------------------------------------------------------
class Mod_FactionRelations_Export(_Mod_Export_Link):
    """Export faction relations from mod to text file."""
    askTitle = _(u'Export faction relations to:')
    csvFile = u'_Relations.csv'
    progressTitle = _(u'Export Relations')
    _text = _('Relations…')
    _help = _(u'Export faction relations from mod to text file')

    def _parser(self):
        return FactionRelations()

class Mod_FactionRelations_Import(_Mod_Import_Link):
    """Imports faction relations from text file to mod."""
    askTitle = _(u'Import faction relations from:')
    csvFile = u'_Relations.csv'
    progressTitle = _(u'Import Relations')
    _text = _('Relations…')
    _help = _(u'Import faction relations from text file to mod')
    continueInfo = _(
        u'This command will import faction relation info from a previously '
        u'exported file.') + u'\n\n' + _(
        'See the Wrye Bash readme for more info.')
    continueKey = u'bash.factionRelations.import.continue'
    noChange = _(u'No relevant faction relations to import.')
    _parser_class = FactionRelations

#------------------------------------------------------------------------------
class Mod_Factions_Export(_Mod_Export_Link):
    """Export factions from mod to text file."""
    askTitle = _(u'Export factions to:')
    csvFile = u'_Factions.csv'
    progressTitle = _(u'Export Factions')
    _text = _('Factions…')
    _help = _(u'Export factions from mod to text file')

    def _parser(self):
        return ActorFactions()

class Mod_Factions_Import(_Mod_Import_Link):
    """Imports factions from text file to mod."""
    askTitle = _(u'Import Factions from:')
    csvFile = u'_Factions.csv'
    progressTitle = _(u'Import Factions')
    _text = _('Factions…')
    _help = _(u'Import factions from text file to mod')
    continueInfo = _(
        u'This command will import faction ranks from a previously exported '
        u'file.') + u'\n\n' + _('See the Wrye Bash readme for more info.')
    continueKey = u'bash.factionRanks.import.continue'
    noChange = _(u'No relevant faction ranks to import.')
    _parser_class = ActorFactions

    def _log(self, changes, fileName):
        log_out = (f'* {grp_name} : {v:03d}  {fileName}' for
                   grp_name, v in sorted(changes.items()))
        self._showLog('\n'.join(log_out))

#------------------------------------------------------------------------------
class Mod_Scripts_Export(_Mod_Export_Link, OneItemLink):
    """Export scripts from mod to text file."""
    _text = _('Scripts…')
    _help = _('Export scripts from plugin to text files.')

    def _parser(self):
        return ScriptText()

    def Execute(self): # overrides _Mod_Export_Link
        fileInfo = self._selected_info
        defaultPath = bass.dirs['patches'].join(
            _('%(script_export_target)s Exported Scripts') % {
                'script_export_target': fileInfo})
        if not ExportScriptsDialog.display_dialog(Link.Frame):
            return
        def_exists = defaultPath.exists()
        if not def_exists:
            defaultPath.makedirs()
        textDir = self._askDirectory(
            message=_('Choose which folder to export the scripts to:'),
            defaultPath=defaultPath)
        if not def_exists and textDir != defaultPath and not [
            # user might have created a file through the dialog (unlikely but)
                *defaultPath.ilist()]:
            defaultPath.removedirs()
        if not textDir: return
        #--Export
        #try:
        scriptText = self._parser()
        scriptText.readFromMod(fileInfo)
        with balt.Progress(_(u'Export Scripts')) as progress:
            exportedScripts = scriptText.export_scripts(textDir, progress,
                bass.settings[u'bash.mods.export.skip'],
                bass.settings[u'bash.mods.export.deprefix'],
                bass.settings[u'bash.mods.export.skipcomments'])
        #finally:
        msg = (_('Exported %(num_exported_scripts)d scripts from '
                 '%(script_export_target)s:')) % {
            'num_exported_scripts': len(exportedScripts),
            'script_export_target': fileInfo}
        msg +='\n' + '\n'.join(exportedScripts)
        self._showLog(msg, title=_(u'Export Scripts'), asDialog=True)

class Mod_Scripts_Import(_Mod_Import_Link):
    """Import scripts from text file."""
    _text = _('Scripts…')
    _help = _('Import scripts from text files.')
    continueInfo = _('Import script from text files. This will replace '
                     'existing scripts and is not reversible (except by '
                     'restoring from a backup)!')
    continueKey = u'bash.scripts.import.continue'
    progressTitle = _(u'Import Scripts')
    _parser_class = ScriptText

    def Execute(self):
        if not self._askContinueImport(): return
        defaultPath = bass.dirs['patches'].join(
            _('%(script_import_target)s Exported Scripts') % {
                'script_import_target': self._selected_item})
        if not defaultPath.exists():
            defaultPath = bass.dirs[u'patches']
        textDir = self._askDirectory(
            message=_('Choose which folder to import scripts from:'),
            defaultPath=defaultPath)
        if not textDir: return
        message = _("Import scripts that don't exist in the plugin as new "
                    "scripts? If you choose No, they will just be skipped.")
        makeNew = self._askYes(message, _('Import Scripts'), questionIcon=True)
        scriptText: ScriptText = self._parser()
        with balt.Progress(_(u'Import Scripts')) as progress:
            scriptText.read_script_folder(textDir, progress)
        altered, added = scriptText.writeToMod(self._selected_info, makeNew)
        #--Log
        if not (altered or added):
            self._showOk(_(u'No changed or new scripts to import.'),
                         _(u'Import Scripts'))
            return
        log_msg = []
        for msg, scripts in (
                (_('Imported %(num_scripts_affected)d changed scripts from '
                   '%(script_import_target)s:'), altered),
                (_('Imported %(num_scripts_affected)d new scripts from '
                   '%(script_import_target)s:'), added)):
            if scripts:
                fmt_msg = msg % {'num_scripts_affected': len(scripts),
                                 'script_import_target': textDir}
                log_msg.append(fmt_msg + '\n*' + '\n*'.join(sorted(scripts)))
        self._showLog('\n\n'.join(log_msg), title=_('Import Scripts'))

#------------------------------------------------------------------------------
class Mod_Stats_Export(_Mod_Export_Link):
    """Exports stats from the selected plugin to a CSV file (for the record
    types specified in bush.game.stats_attrs)."""
    askTitle = _(u'Export stats to:')
    csvFile = u'_Stats.csv'
    progressTitle = _(u'Export Stats')
    _text = _('Stats…')
    _help = _(u'Export stats from mod to text file')

    def _parser(self):
        return ItemStats()

class Mod_Stats_Import(_Mod_Import_Link):
    """Import stats from text file."""
    askTitle = _(u'Import stats from:')
    csvFile = u'_Stats.csv'
    progressTitle = _(u'Import Stats')
    _text = _('Stats…')
    _help = _(u'Import stats from text file')
    continueInfo = _(u'Import item stats from a text file. This will replace '
                     u'existing stats and is not reversible!')
    continueKey = u'bash.stats.import.continue'
    noChange = _(u'No relevant stats to import.')
    _parser_class = ItemStats

    def _log(self, changes, fileName):
        msg = (f'* {count:03d}  {modName}' for modName, count in
               dict_sort(changes))
        self._showLog('\n'.join(msg))

#------------------------------------------------------------------------------
class Mod_Prices_Export(_Mod_Export_Link):
    """Export item prices from mod to text file."""
    askTitle = _('Export Prices To:')
    csvFile = u'_Prices.csv'
    progressTitle = _(u'Export Prices')
    _text = _('Prices…')
    _help = _('Export item prices from a plugin to a text file.')

    def _parser(self):
        return ItemPrices()

class Mod_Prices_Import(_Mod_Import_Link):
    """Import prices from text file or other mod."""
    askTitle = _('Import Prices From:')
    csvFile = u'_Prices.csv'
    progressTitle = _(u'Import Prices')
    _text = _('Prices…')
    _help = _('Import item prices from a text file or another plugin.')
    continueInfo = _('Import item prices from a text file. This will '
                     'replace existing prices and is not reversible!')
    continueKey = u'bash.prices.import.continue'
    noChange = _(u'No relevant prices to import.')
    supportedExts = {u'.csv', u'.ghost'} | bush.game.espm_extensions
    _parser_class = ItemPrices

    def _log(self, changes, fileName):
        msg = (_('Imported Prices:') + f'\n* {modName}: {count:d}' for
               modName, count in dict_sort(changes))
        self._showLog('\n'.join(msg))

#------------------------------------------------------------------------------
class Mod_SigilStoneDetails_Export(_Mod_Export_Link):
    """Export Sigil Stone details from mod to text file."""
    askTitle = _('Export Sigil Stone Details To:')
    csvFile = u'_SigilStones.csv'
    progressTitle = _('Export Sigil Stone Details')
    _text = _('Sigil Stones…')
    _help = _('Export sigil stone details from a plugin to a text file.')

    def _parser(self):
        return SigilStoneDetails()

class Mod_SigilStoneDetails_Import(_Mod_Import_Link):
    """Import Sigil Stone details from text file."""
    askTitle = _('Import Sigil Stone Details From:')
    csvFile = u'_SigilStones.csv'
    progressTitle = _('Import Sigil Stone Details')
    _text = _('Sigil Stones…')
    _help = _('Import sigil stone details from a text file to a plugin.')
    continueInfo = _('Import sigil stone details from a text file. This will '
                     'replace the existing data on sigil stones with the same '
                     'FormIDs and is not reversible!')
    continueKey = u'bash.SigilStone.import.continue'
    noChange = _('No relevant sigil stone details to import.')
    _parser_class = SigilStoneDetails

    def _log(self, changes, fileName):
        msg = [_('Imported sigil stone details to '
                 '%(sigil_import_target)s:') % {
            'sigil_import_target': fileName}]
        msg.extend(f'* {eid}' for eid in sorted(changes))
        self._showLog('\n'.join(msg))

#------------------------------------------------------------------------------
class _SpellRecords_Link(ItemLink):
    """Common code from Mod_SpellRecords_{Ex,Im}port."""
    _do_what: str
    progressTitle: str

    def __init__(self, _text=None):
        super().__init__(_text)
        self.do_detailed = False

    def _parser(self):
        return SpellRecords(detailed=self.do_detailed)

    def Execute(self):
        message = f'{self._do_what}\n' + _('If you choose No, they will just '
                                           'be skipped).')
        self.do_detailed = self._askYes(message, self.progressTitle,
                                        questionIcon=True)
        super().Execute()

class Mod_SpellRecords_Export(_SpellRecords_Link, _Mod_Export_Link):
    """Export Spell details from mod to text file."""
    askTitle = _('Export Spell Details To:')
    csvFile = u'_Spells.csv'
    progressTitle = _('Export Spell Details')
    _text = _('Spells…')
    _help = _('Export spell details from a plugin to a text file.')
    _do_what = _(u'Export flags and effects?')

class Mod_SpellRecords_Import(_SpellRecords_Link, _Mod_Import_Link):
    """Import Spell details from text file."""
    askTitle = _('Import Spell Details From:')
    csvFile = u'_Spells.csv'
    progressTitle = _('Import Spell Details')
    _text = _('Spells…')
    _help = _('Import spell details from a text file to a plugin.')
    continueInfo = _('Import spell details from a text file. This will '
                     'replace the existing data on spells with the same '
                     'FormIDs and is not reversible!')
    continueKey = u'bash.SpellRecords.import.continue'
    noChange = _('No relevant spell details to import.')
    _do_what = _(u'Import flags and effects?')

    def _log(self, changes, fileName):
        msg = [_('Imported Spell details to %(spell_import_target)s:') % {
            'spell_import_target': fileName}]
        msg.extend(f'* {eid}' for eid in sorted(changes))
        self._showLog('\n'.join(msg))

#------------------------------------------------------------------------------
class Mod_IngredientDetails_Export(_Mod_Export_Link):
    """Export Ingredient details from mod to text file."""
    askTitle = _('Export Ingredient Details To:')
    csvFile = u'_Ingredients.csv'
    progressTitle = _('Export Ingredient Details')
    _text = _('Ingredients…')
    _help = _('Export ingredient details from a plugin to a text file.')

    def _parser(self):
        return IngredientDetails()

class Mod_IngredientDetails_Import(_Mod_Import_Link):
    """Import Ingredient details from text file."""
    askTitle = _('Import Ingredient Details From:')
    csvFile = u'_Ingredients.csv'
    progressTitle = _('Import Ingredient Details')
    _text = _('Ingredients…')
    _help = _('Import ingredient details from a text file to a plugin.')
    continueInfo = _('Import ingredient details from a text file. This will '
                     'replace the existing data on ingredients with the same '
                     'FormIDs and is not reversible!')
    continueKey = u'bash.Ingredient.import.continue'
    noChange = _('No relevant ingredient details to import.')
    _parser_class = IngredientDetails

    def _log(self, changes, fileName):
        msg = [_('Imported Ingredient details to '
                 '%(ingredient_import_target)s:') % {
            'ingredient_import_target': fileName}]
        msg.extend(f'* {eid}' for eid in sorted(changes))
        self._showLog('\n'.join(msg))

#------------------------------------------------------------------------------
class Mod_EditorIds_Export(_Mod_Export_Link):
    """Export editor ids from mod to text file."""
    askTitle = _('Export Editor IDs to:')
    csvFile = u'_Eids.csv'
    progressTitle = _('Export Editor IDs')
    _text = _('Editor IDs…')
    _help = _(u'Export faction editor IDs from plugin to text file.')

    def _parser(self):
        return EditorIds()

class Mod_EditorIds_Import(_Mod_Import_Link):
    """Import editor ids from text file."""
    askTitle = _('Import Editor IDs from:')
    csvFile = u'_Eids.csv'
    continueInfo = _('Import editor IDs from a CSV file. This will replace '
                     'existing IDs and is not reversible!')
    continueKey = u'bash.editorIds.import.continue'
    progressTitle = _(u'Import Editor IDs')
    _text = _('Editor IDs…')
    _help = _('Import faction editor IDs from CSV file.')

    def _parser(self, questionableEidsSet=None, badEidsList=None):
        return EditorIds(questionableEidsSet=questionableEidsSet,
                         badEidsList=badEidsList)

    def Execute(self):
        if not self._askContinueImport(): return
        textPath = self._import_from()
        if not textPath: return
        #--Extension error check
        if textPath.cext != u'.csv':
            self._showError(_(u'Source file must be a CSV file.'))
            return
        #--Import
        questionableEidsSet = set()
        badEidsList = []
        try:
            with balt.Progress(self.__class__.progressTitle) as progress:
                editorIds = self._parser(questionableEidsSet, badEidsList)
                progress(0.1, _('Reading %(reading_file)s.') % {
                    'reading_file': textPath.stail})
                editorIds.read_csv(textPath)
                progress(0.2, _('Applying to %(applying_plugin)s.') % {
                    'applying_plugin': self._selected_item})
                changes = editorIds.writeToMod(self._selected_info)
                progress(1.0,_(u'Done.'))
            #--Log
            if not changes:
                self._showOk(self.__class__.noChange)
            else:
                buff = []
                for old, new in sorted(changes):
                    prefix = '* ' if new in questionableEidsSet else ''
                    buff.append(f"{prefix}'{old}' >> '{new}'")
                if questionableEidsSet:
                    buff.append("\n'*': " + _(
                        'These Editor IDs begin with numbers and may '
                        'therefore cause the script compiler to generate '
                        'unexpected results.'))
                if badEidsList:
                    buff.append('\n' + _('The following Editor IDs are '
                                         'malformed and were not imported:'))
                    for badEid in badEidsList:
                        buff.append(f"  '{badEid}'")
                log_text = '\n'.join(buff)
                self._showLog(f'{log_text}\n', title=_('Objects Changed'))
        except (BoltError, NotImplementedError) as e:
            self._showWarning(f'{e!r}')

#------------------------------------------------------------------------------
class Mod_FullNames_Export(_Mod_Export_Link):
    """Export full names from mod to text file."""
    askTitle = _(u'Export names to:')
    csvFile = u'_Names.csv'
    progressTitle = _(u'Export Names')
    _text = _('Names…')
    _help = _(u'Export full names from mod to text file')

    def _parser(self):
        return FullNames()

class Mod_FullNames_Import(_Mod_Import_Link):
    """Import full names from text file or other mod."""
    askTitle = _(u'Import names from:')
    csvFile = u'_Names.csv'
    progressTitle = _(u'Import Names')
    continueInfo = _(
        u'Import record names from a text file. This will replace existing '
        u'names and is not reversible!')
    continueKey = u'bash.fullNames.import.continue'
    _text = _('Names…')
    _help = _(u'Import full names from text file or other mod')
    supportedExts = {u'.csv', u'.ghost'} | bush.game.espm_extensions

    def _parser(self):
        return FullNames()

    def _log(self, changes, fileName):
        msg = (f'{eid}:   {oldFull} >> {newFull}' for
               eid, (oldFull, newFull) in dict_sort(changes))
        self._showLog('\n'.join(msg), title=_('Objects Renamed'))

#------------------------------------------------------------------------------
class Mod_Duplicate(File_Duplicate):
    """Version of File_Duplicate that checks for BSAs and plugin-name-specific
    directories."""
    def _disallow_copy(self, fileInfo):
        #--Mod with resources? Warn on rename if file has bsa and/or dialog
        msg = fileInfo.ask_resources_ok(
            bsa_and_blocking_msg=self._bsa_and_blocking_msg,
            bsa_msg=self._bsa_msg, blocking_msg=self._blocking_msg)
        return msg and not self._askWarning(msg,
                title=_('Duplicate %(target_file_name)s') % {
                    'target_file_name': fileInfo})

#------------------------------------------------------------------------------
class Mod_Snapshot(ItemLink):
    """Take a snapshot of the file."""
    _help = _("Creates a snapshot copy of the selected files in a "
              "'Snapshots' subdirectory.")

    @property
    def link_text(self):
        return (_('Snapshot'), _('Snapshot…'))[len(self.selected) == 1]

    def Execute(self):
        for fileName, fileInfo in self.iselected_pairs():
            destDir, destName, wildcard = fileInfo.getNextSnapshot()
            if len(self.selected) == 1:
                destPath = self._askSave(
                    title=_('Save snapshot as:'), defaultDir=destDir,
                    defaultFile=destName, wildcard=wildcard)
                if not destPath: return
                (destDir,destName) = destPath.headTail
            #--Extract version number
            fileRoot = fileName.fn_body
            destRoot = destName.sroot
            fileVersion = bolt.getMatch(
                re.search(r'[ _]+v?([.\d]+)$', fileRoot), 1)
            snapVersion = bolt.getMatch(re.search(r'-[\d.]+$', destRoot))
            fileHedr = fileInfo.header
            if (fileVersion or snapVersion) and bosh.reVersion.search(fileHedr.description):
                if fileVersion and snapVersion:
                    newVersion = fileVersion+snapVersion
                elif snapVersion:
                    newVersion = snapVersion[1:]
                else:
                    newVersion = fileVersion
                newDescription = bosh.reVersion.sub(fr'\1 {newVersion}', fileHedr.description, 1)
                fileInfo.writeDescription(newDescription)
                self.window.panel.SetDetails(fileName)
            #--Copy file
            fileInfo.fs_copy(destDir.join(destName))

#------------------------------------------------------------------------------
class Mod_RevertToSnapshot(OneItemLink):
    """Revert to Snapshot."""
    _text = _('Revert to Snapshot…')
    _help = _('Revert to a previously created snapshot from the '
              'Bash/Snapshots dir.')

    @balt.conversation
    def Execute(self):
        """Revert to Snapshot."""
        if not self._ask_revert(): return
        sel_file = self._selected_item
        with BusyCursor(), TempFile() as known_good_copy:
            info_path = (sel_inf := self._selected_info).abs_path
            # Make a temp copy first in case reverting to snapshot fails
            sel_inf.fs_copy(GPath_no_norm(known_good_copy))
            # keep load order (so mtime)
            self._backup_path.copyTo(info_path, set_time=sel_inf.ftime)
            self._data_store.refresh(RefrIn.from_tabled_infos({
                sel_file: sel_inf}, exclude=True))
            if not self._data_store.get(sel_file):
                # Reverting to snapshot failed - may be corrupt
                bolt.deprint('Failed to revert to snapshot', traceback=True)
                self.window.panel.ClearDetails()
                if self._askYes(
                    _("Failed to revert %(target_file_name)s to snapshot "
                      "%(snapshot_file_name)s. The snapshot file may be "
                      "corrupt. Do you want to restore the original file "
                      "again? 'No' keeps the reverted, possibly broken "
                      "snapshot instead.") % {'target_file_name': sel_file,
                            'snapshot_file_name': self._backup_path.tail},
                        title=_('Revert to Snapshot - Error')):
                    # Restore the known good file again - no error check needed
                    info_path.replace_with_temp(known_good_copy)
                    self._data_store.refresh(RefrIn.from_tabled_infos({
                        sel_file: sel_inf}))
        # don't refresh saves as neither selection state nor load order change
        self.refresh_sel()

    @property
    def _backup_path(self):
        if self.__backup_path: return self.__backup_path
        #--Snapshot finder
        srcDir, _destName, wildcard = self._selected_info.getNextSnapshot()
        #--File dialog
        msg = _('Revert %(target_file_name)s to snapshot:') % {
            'target_file_name': self._selected_item}
        self.__backup_path = self._askOpen(msg, defaultDir=srcDir,
                                           wildcard=wildcard)
        return self.__backup_path

    def _ask_revert(self):
        self.__backup_path = None
        sel_file = self._selected_item
        if not (snapPath := self._backup_path): return
        #--Warning box
        message = (_('Revert %(target_file_name)s to snapshot '
                     '%(snapsnot_file_name)s dated %(snapshot_date)s?') % {
            'target_file_name': sel_file, 'snapsnot_file_name': snapPath.tail,
            'snapshot_date': format_date(snapPath.mtime)})
        return self._askYes(message, _('Revert to Snapshot'))
