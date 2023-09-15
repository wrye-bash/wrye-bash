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
"""Menu items for the _item_ menu of the mods tab - their window attribute
points to BashFrame.modList singleton."""

import copy
import io
import traceback
from collections import defaultdict
from collections.abc import Iterable
from itertools import chain

from .constants import settingDefaults
from .dialogs import DeactivateBeforePatchEditor, ExportScriptsDialog, \
    MasterErrorsDialog
from .files_links import File_Duplicate, File_Redate
from .frames import DocBrowser
from .patcher_dialog import PatchDialog, all_gui_patchers
from .. import balt, bass, bolt, bosh, bush, load_order
from ..balt import AppendableLink, CheckLink, ChoiceLink, EnabledLink, \
    ItemLink, Link, MenuLink, OneItemLink, SeparatorLink, TransLink
from ..bolt import FName, SubProgress, dict_sort, sig_to_str
from ..brec import RecordType
from ..exception import BoltError, CancelError
from ..gui import BusyCursor, ImageWrapper, copy_text_to_clipboard, askText, \
    showError
from ..mod_files import LoadFactory, ModFile, ModHeaderReader
from ..parsers import ActorFactions, ActorLevels, CsvParser, EditorIds, \
    FactionRelations, FidReplacer, FullNames, IngredientDetails, ItemPrices, \
    ItemStats, ScriptText, SigilStoneDetails, SpellRecords, _AParser
from ..patcher.patch_files import PatchFile

__all__ = [u'Mod_FullLoad', u'Mod_CreateDummyMasters', u'Mod_OrderByName',
           u'Mod_Groups', u'Mod_Ratings', u'Mod_Details', u'Mod_ShowReadme',
           u'Mod_ListBashTags', u'Mod_CreateLOOTReport', u'Mod_CopyModInfo',
           u'Mod_AllowGhosting', u'Mod_GhostUnghost', u'Mod_MarkMergeable',
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
           u'Mod_FlipEsm', u'Mod_FlipEsl', u'Mod_FlipMasters',
           'Mod_SetVersion', 'Mod_ListDependent', 'Mod_Move',
           'Mod_RecalcRecordCounts', 'Mod_Duplicate', 'Mod_DumpSubrecords']

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
    _text = 'Test Record Definitions...'
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

# File submenu ----------------------------------------------------------------
# the rest of the File submenu links come from file_links.py
class Mod_CreateDummyMasters(OneItemLink, _LoadLink):
    """xEdit tool, makes dummy plugins for each missing master, for use if
    looking at a 'Filter' patch."""
    _text = _(u'Create Dummy Masters...')
    _help = _(u'Creates empty plugins for each missing master of the selected '
              u'mod, allowing it to be loaded by tools like %s or the %s.') % (
        bush.game.Xe.full_name, bush.game.Ck.long_name)

    def _enable(self):
        return super(Mod_CreateDummyMasters, self)._enable() and \
               self._selected_info.getStatus() == 30  # Missing masters

    def Execute(self):
        """Create Dummy Masters"""
        msg = (_(u'This is an advanced feature, originally intended for '
                 u"viewing and editing 'Filter' patches in %s. It will create "
                 u'empty plugins for each missing master. Are you sure you '
                 u'want to continue?') % bush.game.Xe.full_name + u'\n\n' +
               _(u"To remove these files later, use 'Remove Dummy "
                 u"Masters...'."))
        if not self._askYes(msg, title=_(u'Create Files')): return
        to_refresh = []
        # creates esp files - so place them correctly after the last esm
        previous_master = bosh.modInfos.cached_lo_last_esm()
        for master in self._selected_info.masterNames:
            if master in bosh.modInfos:
                continue
            # Missing master, create a dummy plugin for it
            newInfo = bosh.ModInfo(self._selected_info.info_dir.join(master))
            to_refresh.append((master, newInfo, previous_master))
            previous_master = master
            newFile = ModFile(newInfo, self._load_fact()) ###
            newFile.tes4.author = u'BASHED DUMMY'
            # Add the appropriate flags based on extension. This is obviously
            # just a guess - you can have a .esm file without an ESM flag in
            # Skyrim LE - but these are also just dummy masters.
            ciext = newInfo.fn_key.fn_ext
            if ciext in ('.esl', '.esm'):
                newFile.tes4.flags1.esm_flag = True
            if ciext == '.esl' and bush.game.has_esl:
                newFile.tes4.flags1.esl_flag = True
            newFile.safeSave()
        to_select = []
        for mod, info, previous in to_refresh:
            # add it to modInfos or lo_insert_after blows for timestamp games
            bosh.modInfos.new_info(mod, notify_bain=True)
            bosh.modInfos.cached_lo_insert_after(previous, mod)
            to_select.append(mod)
        bosh.modInfos.cached_lo_save_lo()
        bosh.modInfos.refresh(refresh_infos=False)
        self.window.RefreshUI(refreshSaves=True, detail_item=to_select[-1])
        self.window.SelectItemsNoCallback(to_select)

#------------------------------------------------------------------------------
class Mod_OrderByName(EnabledLink):
    """Sort the selected files."""
    _text = _('Order by Name')
    _help = _(u'Reorder the selected plugins to be in alphabetical order. '
              u'Only works if the selected plugins may be reordered.')

    def _enable(self):
        # Can't be used if at least one of the selected mods is pinned
        return (len(self.selected) > 1
                and not load_order.filter_pinned(self.selected))

    @balt.conversation
    def Execute(self):
        message = _(u'Reorder selected mods in alphabetical order?  The first '
            u'file will be given the date/time of the current earliest file '
            u'in the group, with consecutive files following at 1 minute '
            u'increments.') if not bush.game.using_txt_file else _(
            u'Reorder selected mods in alphabetical order starting at the '
            u'lowest ordered?')
        message += (u'\n\n' + _(
            u'Note that some mods need to be in a specific order to work '
            u'correctly, and this sort operation may break that order.'))
        if not self._askContinue(message, u'bash.sortMods.continue',
                                 title=self._text): return
        #--Do it
        self.selected.sort()
        self.selected.sort( # sort masters first
            key=lambda m: not bosh.modInfos[m].in_master_block())
        lowest = load_order.get_ordered(self.selected)[0]
        bosh.modInfos.cached_lo_insert_at(lowest, self.selected)
        # Reorder the actives too to avoid bogus LO warnings
        bosh.modInfos.cached_lo_save_all()
        self.window.RefreshUI(refreshSaves=True)

#------------------------------------------------------------------------------
class Mod_Move(EnabledLink):
    """Moves selected mod(s) to a different LO position."""
    _text = _('Move To...')
    _help = _('Move the selected plugin(s) to a position of your choice. '
              'Only works if the selected plugin(s) may be reordered.')

    def _enable(self):
        # Can't be used if at least one of the selected mods is pinned
        return not load_order.filter_pinned(self.selected)

    def Execute(self):
        entered_text = u''
        # Default to the index of the first selected active plugin, or 0
        enabled_selected = [p for p in self.selected
                            if load_order.cached_is_active(p)]
        default_index = (load_order.cached_active_index(enabled_selected[0])
                         if enabled_selected else 0)
        try:
            # Only accept hexadecimal numbers, trying to guess what they are
            # will just lead to sadness
            entered_text = self._askText(
                _(u'Please enter the plugin index to which the selected '
                  u'plugins should be moved.') + u'\n' +
                _(u'Note that it must be a hexadecimal number, as shown in '
                  u'the Mods tab.'),
                default=u'%X' % default_index)
            if not entered_text: return # Abort if canceled or empty string
            target_index = int(entered_text, base=16)
        except (TypeError, ValueError):
            self._showError(_(u"'%s' is not a valid hexadecimal number.") %
                            entered_text)
            return
        # We can obviously only target active plugins, since inactive
        # plugins do not have a *user-exposed* index
        active_plugins = load_order.cached_active_tuple()
        # Clamp between 0 and max plugin index
        target_index = max(0, min(target_index, len(active_plugins) - 1))
        bosh.modInfos.cached_lo_insert_at(active_plugins[target_index],
                                          self.selected)
        # Reorder the actives too to avoid bogus LO warnings
        bosh.modInfos.cached_lo_save_all()
        self.window.RefreshUI(refreshSaves=True, detail_item=self.selected[0])

#------------------------------------------------------------------------------
class Mod_Redate(File_Redate):
    """Mods tab version of the Redate command."""
    def _infos_to_redate(self):
        return [self._data_store[to_redate] for to_redate
                in load_order.get_ordered(self.selected)]

    def _perform_refresh(self):
        bosh.modInfos.refresh(refresh_infos=False, _modTimesChange=True)

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

    def _refresh(self, redraw): # editing mod labels should not affect saves
        self.parent.RefreshUI(redraw=redraw, refreshSaves=False)

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
        colGroup = bosh.modInfos.table.getColumn(self.column)
        renamed = []
        for fileName, val in colGroup.items():
            if val == oldName:
                colGroup[fileName] = newName
                renamed.append(fileName)
        self._refresh(redraw=renamed)
        #--Done
        return newName

    def remove(self,item):
        """Removes group."""
        self.mod_labels.remove(item)
        #--Edit table entries.
        colGroup = bosh.modInfos.table.getColumn(self.column)
        deletd = []
        for fileName, val in list(colGroup.items()):
            if val == item:
                del colGroup[fileName]
                deletd.append(fileName)
        self._refresh(redraw=deletd)
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
    edit_menu_text = _(u'Edit Groups...')
    edit_window_title = _(u'Groups')
    column     = u'group'
    setKey     = u'bash.mods.groups'
    addPrompt  = _(u'Add group:')

    def _refresh(self): # editing mod labels should not affect saves
        self.window.RefreshUI(redraw=self.selected, refreshSaves=False)

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
                del _self.listEditor  ##: used by the buttons code - should be
                # encapsulated
        class _None(CheckLink):
            _text = _(u'None')
            _help = _(u'Clear labels from selected mod(s)')
            def Execute(self):
                """Handle selection of None."""
                fileLabels = bosh.modInfos.table.getColumn(_self.column)
                for fileName in self.selected:
                    fileLabels[fileName] = u''
                _self._refresh()
            def _check(self):
                return _self._none_checked
        self.extraItems = [_Edit(), SeparatorLink(), _None()]

    def _initData(self, window, selection):
        super(_Mod_Labels, self)._initData(window, selection)
        _self = self
        label_column = bosh.modInfos.table.getColumn(self.column)
        selection_set = set(selection)
        column_contents = {x[1] for x in label_column.items()
                           if x[0] in selection_set}
        self._none_checked = not any(column_contents)
        class _LabelLink(CheckLink):
            def Execute(self):
                for fileInfo in self.iselected_infos():
                    fileInfo.set_table_prop(_self.column, self._text)
                _self._refresh()
            @property
            def link_help(self): return _(
                u"Applies the label '%(lbl)s' to the selected mod(s).") % {
                                            u'lbl': self._text}
            def _check(self):
                """Check the link if any of the selected plugins have labels
                matching this one."""
                return self._text in column_contents
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

    def readFromModInfos(self,mods=None):
        """Imports mods/groups from modInfos."""
        column = bosh.modInfos.table.getColumn(u'group')
        mods = mods or list(column) # if mods are None read groups for all mods
        groups = tuple(column.get(x) for x in mods)
        self.mod_group.update((x, y) for x, y in zip(mods, groups) if y)

    @staticmethod
    def assignedGroups():
        """Return all groups that are currently assigned to mods."""
        column = bosh.modInfos.table.getColumn(u'group')
        return {x for x in column.values() if x}

    def writeToModInfos(self,mods=None):
        """Exports mod groups to modInfos."""
        mod_group = self.mod_group
        column = bosh.modInfos.table.getColumn(u'group')
        changed_count = 0
        for mod in (mods or bosh.modInfos.table):
            if mod in mod_group and column.get(mod) != mod_group[mod]:
                column[mod] = mod_group[mod]
                changed_count += 1
        return changed_count

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
    _text = _('Export Groups...')
    _help = _('Export groups of selected mods to a .csv file.')

    def Execute(self):
        textName = u'My' + self.__class__.csvFile
        textPath = self._csv_out(textName)
        if not textPath: return
        #--Export
        modGroups = _ModGroups()
        modGroups.readFromModInfos(self.selected)
        modGroups.write_text_file(textPath)
        self._showOk(_(u'Exported %d mod/groups.') % len(modGroups.mod_group))

class _Mod_Groups_Import(ItemLink):
    """Import mod groups from text file."""
    _text = _('Import Groups...')
    _help = _('Import groups for selected mods from a .csv file (filename '
              'must end in _Groups.csv).')

    def Execute(self):
        message = _(
            u'Import groups from a text file ? This will assign to selected '
            u'mods the group they are assigned in the text file, if any.')
        if not self._askContinue(message, u'bash.groups.import.continue',
                                 _(u'Import Groups')): return
        textDir = bass.dirs[u'patches']
        #--File dialog
        textPath = self._askOpen(_('Import names from:'), textDir, '',
                                 '*_Groups.csv')
        if not textPath: return
        #--Extension error check
        if textPath.cext != u'.csv':
            self._showError(_(u'Source file must be a csv file.'))
            return
        #--Import
        modGroups = _ModGroups()
        modGroups.read_csv(textPath)
        changed_count = modGroups.writeToModInfos(self.selected)
        bosh.modInfos.refresh()
        self.window.RefreshUI(refreshSaves=False) # was True (importing groups)
        self._showOk(_(u'Imported %d mod/groups (%d changed).') % (
            len(modGroups.mod_group), changed_count), _(u'Import Groups'))

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
        self.listEditor.SetItemsTo(list(set(bass.settings[
            u'bash.mods.groups']) | _ModGroups.assignedGroups()))

    def _doSync(self):
        """Set the list of groups to groups currently assigned to mods."""
        msg = _(u'This will set the list of available groups to the groups '
                u'currently assigned to mods. Continue ?')
        if not balt.askContinue(self.listEditor, msg,
                                u'bash.groups.sync.continue',
                                _(u'Sync Groups')): return
        self.listEditor.SetItemsTo(list(_ModGroups.assignedGroups()))

    def _doReset(self):
        """Set the list of groups to the default groups list.

        Won't clear user set groups from the modlist - most probably not
        what the user wants.
        """
        msg = _(u'This will reset the list of available groups to the default '
                u"group list. It won't however remove non default groups from "
                u'mods that are already tagged with them. Continue ?')
        if not balt.askContinue(self.listEditor, msg,
                                u'bash.groups.reset.continue',
                                _(u'Reset Groups')): return
        self.listEditor.SetItemsTo(list(settingDefaults[u'bash.mods.groups']))

    def SetItemsTo(self, items):
        if self._listEditorData.setTo(items):
            self._list_items = self._listEditorData.getItemList()
            self.listBox.lb_set_items(self._list_items)

#--Ratings --------------------------------------------------------------------
class Mod_Ratings(_Mod_Labels):
    """Add mod rating links."""
    edit_menu_text = _(u'Edit Ratings...')
    edit_window_title = _(u'Ratings')
    column     = u'rating'
    setKey     = u'bash.mods.ratings'
    addPrompt  = _(u'Add rating:')

# Mod info menus --------------------------------------------------------------
#------------------------------------------------------------------------------
class Mod_Details(OneItemLink):
    """Show Mod Details"""
    _text = _(u'Details...')
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
                recs = [(f, e) for f, (_h, e) in group_records.items()]
                recs.sort(key=lambda r: r[1].lower())
                for f, e in recs:
                    buff.append(f'  {f} {e}')
                buff.append('') # an empty line
            self._showLog('\n'.join(buff), title=self._selected_item,
                          fixedFont=True)

class Mod_ShowReadme(OneItemLink):
    """Open the readme."""
    _text = _(u'Readme...')
    _help = _(u'Open the readme')

    def Execute(self):
        if not Link.Frame.docBrowser:
            DocBrowser().show_frame()
        Link.Frame.docBrowser.SetMod(self._selected_item)
        Link.Frame.docBrowser.raise_frame()

class Mod_ListBashTags(ItemLink):
    """Copies list of bash tags to clipboard."""
    _text = _(u'List Bash Tags...')
    _help = _(u'Copies list of bash tags to clipboard')

    def Execute(self):
        #--Get masters list
        tags_text = bosh.modInfos.getTagList(list(self.iselected_infos()))
        copy_text_to_clipboard(tags_text)
        self._showLog(tags_text, title=_(u'Bash Tags'), fixedFont=False)

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
    _text = _(u'Create LOOT Entry...')
    _help = _(u'Creates LOOT masterlist entries based on the tags you have '
              u'applied to the selected plugin(s).')

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
        self._showLog(log_txt, title=_(u'LOOT Entry'), fixedFont=False)

class Mod_CopyModInfo(ItemLink):
    """Copies the basic info about selected mod(s)."""
    _text = _('Copy Plugin Info...')
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
                mod_text.append(_('Version') + f': {vers}')
            info_txt.append('\n'.join(mod_text))
        info_txt = '\n\n'.join(info_txt) # add a blank line in between mods
        if len(self.selected) > 5:
            info_txt = f'[spoiler]\n{info_txt}\n[/spoiler]'
        # Show results + copy to clipboard
        copy_text_to_clipboard(info_txt)
        self._showLog(info_txt, title=_('Plugin Info Report'), fixedFont=False)

class Mod_ListDependent(OneItemLink):
    """Copies list of masters to clipboard."""
    _text = _(u'List Dependent...')

    @property
    def link_help(self):
        return _(u'Displays and copies to the clipboard a list of mods that '
                 u'have %(filename)s as master.') % (
            {u'filename': self._selected_item})

    def Execute(self):
        ##: HACK - refactor getModList
        sel_target = self._selected_item
        legend = _(u'Mods dependent on %(filename)s') % (
            {u'filename': sel_target})
        modInfos = self._data_store
        merged_, imported_ = modInfos.merged, modInfos.imported
        head, bul = u'=== ', u'* '
        log = bolt.LogFile(io.StringIO())
        log(u'[spoiler]')
        log.setHeader(head + legend + u': ')
        text_list = u''
        for mod in load_order.get_ordered(
                self._selected_info.get_dependents()):
            hexIndex = modInfos.hexIndexString(mod)
            if hexIndex:
                prefix = bul + hexIndex
            elif mod in merged_:
                prefix = bul + u'++'
            else:
                prefix = bul + (u'**' if mod in imported_ else u'__')
            text_list = u'%s  %s' % (prefix, mod)
            log(text_list)
        if not text_list:  log(u'None')
        log(u'[/spoiler]')
        text_list = log.out.getvalue()
        copy_text_to_clipboard(text_list)
        self._showLog(text_list, title=legend, fixedFont=False)

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
        return bosh.modInfos.table.getItem(filename, u'allowGhosting', True)

    def Execute(self):
        """Loop selected files applying allow ghosting settings and
        (un)ghosting as needed."""
        ghost_changed = []
        set_allow = self.__class__.setAllow
        to_ghost = self.__class__.toGhost
        for fileName, fileInfo in self.iselected_pairs():
            fileInfo.set_table_prop(u'allowGhosting', set_allow(fileName))
            oldGhost = fileInfo.isGhost
            if fileInfo.setGhost(to_ghost(fileName)) != oldGhost:
                ghost_changed.append(fileName)
        self.window.RefreshUI(redraw=ghost_changed, refreshSaves=False)

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
        return any(self.__class__.toGhost(p) != ghost_minfs[p].isGhost
                   for p in self.selected)

class _Mod_Ghost(_DirectGhostLink):
    _text = _(u'Ghost')
    _help = _(u"Ghost selected mod(s). Active mods can't be ghosted.")
    toGhost = staticmethod(lambda fname: not load_order.cached_is_active(fname))

class _Mod_Unghost(_DirectGhostLink):
    _text = _(u'Unghost')
    _help = _(u'Unghost selected mod(s).')
    toGhost = staticmethod(lambda fname: False)

class Mod_GhostUnghost(TransLink):
    """Ghost or unghost selected mod(s)."""
    def _decide(self, window, selection):
        # If any of the selected plugins can be ghosted, return the ghosting
        # link - otherwise, default to unghost
        if any(_Mod_Ghost.toGhost(p) != window.data_store[p].isGhost
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
            subMenu.links.append(_Mod_AllowGhosting_All())
            subMenu.links.append(_Mod_DisallowGhosting_All())
            subMenu.links.append(_Mod_AllowGhostingInvert_All())
            return subMenu

# BP Links --------------------------------------------------------------------
#------------------------------------------------------------------------------
class Mod_MarkMergeable(ItemLink):
    """Returns true if can act as patch mod."""
    def __init__(self):
        Link.__init__(self)
        if bush.game.check_esl:
            self._text = _(u'Check ESL Qualifications')
            self._help = _(u'Scans the selected plugin(s) to determine '
                           u'whether or not they can be assigned the ESL '
                           u'flag, reporting also the reason(s) if they '
                           u'cannot be ESL-flagged.')
        else:
            self._text = _(u'Mark Mergeable...')
            self._help = _(u'Scans the selected plugin(s) to determine if '
                           u'they are mergeable into the Python Bashed Patch, '
                           u'reporting also the reason(s) if they are '
                           u'unmergeable.')

    @balt.conversation
    def Execute(self):
        result, tagged_no_merge = bosh.modInfos.rescanMergeable(self.selected,
            return_results=True)
        yes = [x for x in self.selected if
               x not in tagged_no_merge and x in bosh.modInfos.mergeable]
        no = set(self.selected) - set(yes)
        no = [u'%s:%s' % (x, y) for x, y in result.items() if x in no]
        if bush.game.check_esl:
            message = u'== %s\n\n' % _(
                u'Plugins that qualify for ESL flagging.')
        else:
            message = u'== %s ' % _(u'Python Mergeability') + u'\n\n'
        if yes:
            message += u'=== ' + (
                _(u'ESL Capable') if bush.game.check_esl else _(
                    u'Mergeable')) + u'\n* ' + u'\n\n* '.join(yes)
        if yes and no:
            message += u'\n\n'
        if no:
            message += u'=== ' + (_(
                u'ESL Incapable') if bush.game.check_esl else _(
                u'Not Mergeable')) + u'\n* ' + u'\n\n* '.join(no)
        self.window.RefreshUI(redraw=self.selected, refreshSaves=False)
        if message != u'':
            title_ = _(u'Check ESL Qualifications') if \
                bush.game.check_esl else _(u'Mark Mergeable')
            self._showWryeLog(message, title=title_)

#------------------------------------------------------------------------------
class _Mod_BP_Link(OneItemLink):
    """Enabled on Bashed patch items."""
    def _enable(self):
        return super(_Mod_BP_Link, self)._enable() \
               and self._selected_info.isBP()

class Mod_RebuildPatch(_Mod_BP_Link):
    """Updates a Bashed Patch."""
    _text = _(u'Rebuild Patch...')
    _help = _(u'Rebuild the Bashed Patch')

    @balt.conversation
    def Execute(self):
        """Handle activation event."""
        self.mods_to_reselect = set()
        try:
            if not self._execute_bp(self._selected_info, bosh.modInfos):
                return # prevent settings save
        except CancelError:
            return # prevent settings save
        finally:
            if self.mods_to_reselect: # may be cleared in PatchDialog#PatchExecute
                for mod in self.mods_to_reselect:
                    bosh.modInfos.lo_activate(mod, doSave=False)
                bosh.modInfos.cached_lo_save_active()
                self.window.RefreshUI(refreshSaves=True)
        # save data to disc in case of later improper shutdown leaving the
        # user guessing as to what options they built the patch with
        Link.Frame.SaveSettings() ##: just modInfos ?

    def _execute_bp(self, patch_info, mod_infos):
        # Clean up some memory
        bolt.GPathPurge()
        # We need active mods
        if not load_order.cached_active_tuple():
            self._showWarning(
                _('That which does not exist cannot be patched.') + '\n' +
                _('Load some mods and try again.'), _('Existential Error'))
            return False
        # Read the config
        bp_config = self._selected_info.get_table_prop('bash.patch.configs',{})
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
        def mk_error(warn_msg: str, warning_items: Iterable[FName]):
            return MasterErrorsDialog.make_change_entry(
                mods_list_images=self.window._icons, mods_change_desc=warn_msg,
                decorated_plugins=self.window.decorate_tree_dict(
                    {i: [] for i in sorted(warning_items)}))
        bp_master_errors = []
        if missing:
            bp_master_errors.append(mk_error(_(
                'The following plugins have missing masters and are active. '
                'This will cause the game to crash. Please disable them.'),
                missing))
        if delinquent:
            bp_master_errors.append(mk_error(_(
                'These mods have delinquent masters, which means they load '
                'before their masters. This is undefined behavior. Please '
                'adjust your load order to fix this.'), delinquent))
        if bp_master_errors:
            MasterErrorsDialog.display_dialog(self.window,
                highlight_changes=bp_master_errors)
            return False
        # No errors, proceed with building the BP
        PatchDialog.display_dialog(self.window, bashed_patch,
                                   self.mods_to_reselect, bp_config)
        return True

    def _ask_deactivate_mergeable(self, bashed_patch):
        merge, noMerge, deactivate = [], [], []
        for mod in bashed_patch.load_dict:
            tags = bosh.modInfos[mod].getBashTags()
            if not bush.game.check_esl and mod in bosh.modInfos.mergeable:
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
        self.mods_to_reselect = ed_nomerge
        with BusyCursor():
            bosh.modInfos.lo_deactivate(to_deselect, doSave=True)
            self.window.RefreshUI(refreshSaves=True)
        return True

#------------------------------------------------------------------------------
class Mod_ListPatchConfig(_Mod_BP_Link):
    """Lists the Bashed Patch configuration and copies to the clipboard."""
    _text = _(u'List Patch Config...')
    _help = _(
        u'Lists the Bashed Patch configuration and copies it to the clipboard')

    def Execute(self):
        #--Config
        config = self._selected_info.get_table_prop(u'bash.patch.configs', {})
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
        log.setHeader(u'= %s %s' % (self._selected_item, _(u'Config')))
        log(_(u'This is the current configuration of this Bashed Patch.  This '
              u'report has also been copied into your clipboard.')+u'\n')
        clip = io.StringIO()
        clip.write(u'%s %s:\n' % (self._selected_item, _(u'Config')))
        clip.write(u'[spoiler]\n')
        log.setHeader(u'== '+_(u'Patch Mode'))
        clip.write(u'== '+_(u'Patch Mode')+u'\n')
        log(u'Python')
        clip.write(u' ** Python\n')
        for patcher in _gui_patchers:
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
        self.window.RefreshUI(redraw=self.selected, refreshSaves=False)

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
            subMenu.links.append(_Mod_SkipDirtyCheckAll(True))
            subMenu.links.append(_Mod_SkipDirtyCheckAll(False))
            subMenu.links.append(_Mod_SkipDirtyCheckInvert())
            return subMenu

#------------------------------------------------------------------------------
class Mod_ScanDirty(ItemLink):
    """Give detailed printout of what Wrye Bash is detecting as UDR records."""
    _text = _(u'Scan for Deleted Records')
    _help = _(u'Gives a detailed printout of deleted records in the selected '
              u'plugin(s).')

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
                scan_progress = SubProgress(progress, 0.7, 0.9)
                scan_progress.setFull(len(all_extracted_data))
                all_ref_types = RecordType.sig_to_class[b'CELL'].ref_types
                for i, (plugin_fn, ext_data) in enumerate(
                        all_extracted_data.items()):
                    scan_progress(i, (_(u'Scanning: %s') % plugin_fn))
                    add_deleted_ref = all_deleted_refs[plugin_fn].append
                    add_deleted_navm = all_deleted_navms[plugin_fn].append
                    add_deleted_rec = all_deleted_others[plugin_fn].append
                    for r, d in ext_data.items():
                        for r_fid, (r_header, r_eid) in d.items():
                            if r_header.flags1 & 0x00000020:
                                if (w_rec_type := r_header.recType) == b'NAVM':
                                    add_deleted_navm(r_fid)
                                elif w_rec_type in all_ref_types:
                                    add_deleted_ref(r_fid)
                                else:
                                    add_deleted_rec(r_fid)
        except CancelError:
            return
        log = bolt.LogFile(io.StringIO())
        log.setHeader(u'= '+_(u'Deleted Records'))
        log(_(u'This is a report of deleted records that were found in the '
              u'selected plugin(s).') + u'\n')
        # Change a FID to something more useful for displaying
        def _log_fids(del_title, del_fids):
            nonlocal full_dirty_msg
            mod_masters = modInfo.masterNames
            len_mas = len(mod_masters)
            full_dirty_msg += '\n'.join([f'  * {del_title}: {len(del_fids)}',
                *(f'    * {d_fid.short_fid:08X} (from master '
                  f'{mod_masters[min(d_fid.mod_dex, len_mas - 1)]})'
                  for d_fid in sorted(del_fids))])
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
            log(_(u'Detected %d plugin(s) with deleted '
                  u'records:') % len(dirty_plugins))
            for p in dirty_plugins:
                log(p)
            log(u'\n')
        if clean_plugins:
            log(_(u'Detected %d plugin(s) without deleted '
                  u'records:') % len(clean_plugins))
            for p in clean_plugins:
                log(p)
            log(u'\n')
        if skipped_plugins:
            log(_(u'Skipped %d plugin(s):') % len(skipped_plugins))
            for p in skipped_plugins:
                log(p)
            log(u'\n')
        self._showWryeLog(log.out.getvalue(), title=_(u'Dirty Record Results'),
                          asDialog=False)

#------------------------------------------------------------------------------
class Mod_RemoveWorldOrphans(_NotObLink, _LoadLink):
    """Remove orphaned cell records."""
    _text = _(u'Remove World Orphans')
    _help = _(u'Remove orphaned cell records')
    _load_sigs = [b'CELL', b'WRLD']

    def Execute(self):
        message = _('In some circumstances, editing a mod will leave orphaned '
                    'cell records in the world group. This command will '
                    'remove such orphans.')
        if not self._askContinue(message, u'bash.removeWorldOrphans.continue',
                                 _(u'Remove World Orphans')): return
        for index, (fileName, fileInfo) in enumerate(self.iselected_pairs()):
            if fileInfo.match_oblivion_re():
                self._showWarning(_('Skipping %s') % fileInfo,
                                  _('Remove World Orphans'))
                continue
            #--Export
            with balt.Progress(_(u'Remove World Orphans')) as progress:
                progress(0,_(u'Reading') + u' %s.' % fileInfo)
                modFile = self._load_mod(fileInfo,
                    progress=SubProgress(progress, 0, 0.7))
                orphans = (b'WRLD' in modFile.tops) and modFile.tops[b'WRLD'].orphansSkipped
                if orphans:
                    progress(0.1, _(u'Saving %s.') % fileInfo)
                    modFile.safeSave() ##: todo setChanged?
                progress(1.0,_(u'Done.'))
            #--Log
            if orphans:
                self._showOk(_(u'Orphan cell blocks removed: %d.') % orphans,
                             fileName)
            else:
                self._showOk(_(u'No changes required.'), fileName)

#------------------------------------------------------------------------------
class Mod_FogFixer(ItemLink):
    """Fix fog on selected cells."""
    _text = _(u'Nvidia Fog Fix')
    _help = _(u'Modify fog values in interior cells to avoid the Nvidia black '
             u'screen bug')

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
                progress(index, _(u'Scanning %s') % fileName)
                fog_fixer = bosh.mods_metadata.NvidiaFogFixer(fileInfo)
                fog_fixer.fix_fog(SubProgress(progress, index, index + 1))
                if fog_fixer.fixedCells:
                    fixed[fileName] = fog_fixer.fixedCells
        if fixed:
            message = '===' + _('Cells Fixed:') + '\n' + '\n'.join([
                f'* {fixed_pname}: {len(cells_fixed)}'
                for fixed_pname, cells_fixed in fixed.items()])
            self._showWryeLog(message)
            self.window.RefreshUI(redraw=list(fixed))
        else:
            message = _(u'No changes required.')
            self._showOk(message)

# Rest of menu Links ----------------------------------------------------------
#------------------------------------------------------------------------------
class _CopyToLink(EnabledLink):
    def __init__(self, plugin_ext):
        super(_CopyToLink, self).__init__(plugin_ext)
        self._target_ext = plugin_ext
        self._help = _(u'Creates a copy of the selected plugin(s) with the '
                       u'extension changed to %s.') % plugin_ext

    def _enable(self):
        return any(p.get_extension() != self._target_ext
                   for p in self.iselected_infos())

    def Execute(self):
        modInfos, added = bosh.modInfos, []
        do_save_lo = False
        add_esl_flag = self._target_ext == u'.esl'
        add_esm_flag = add_esl_flag or self._target_ext == '.esm'
        with BusyCursor(): # ONAM generation can take a bit
            for curName, minfo in self.iselected_pairs():
                if self._target_ext == curName.fn_ext: continue
                newName = FName(curName.fn_body + self._target_ext)
                #--Replace existing file?
                timeSource = None
                if newName in modInfos:
                    existing = modInfos[newName]
                    # getPath() as existing may be ghosted
                    if not self._askYes(_(u'Replace existing %s?') %
                                        existing.getPath()):
                        continue
                    existing.makeBackup()
                    timeSource = newName
                newTime = modInfos[timeSource].mtime if timeSource else None
                # Copy and set flag - will use ghosted path if needed
                modInfos.copy_info(curName, minfo.info_dir, newName,
                                   set_mtime=newTime)
                added.append(newName)
                newInfo = modInfos[newName]
                newInfo.set_esm_flag(add_esm_flag)
                newInfo.set_esl_flag(add_esl_flag)
                if timeSource is None: # otherwise it has a load order already!
                    modInfos.cached_lo_insert_after(
                        modInfos.cached_lo_last_esm(), newName)
                    do_save_lo = True
        #--Repopulate
        if added:
            if do_save_lo: modInfos.cached_lo_save_lo()
            modInfos.refresh(refresh_infos=False)
            self.window.RefreshUI(refreshSaves=True, # just in case
                                  detail_item=added[-1])
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
        message = _(u"This command will remove the effects of a 'compile all' "
                    u"by removing all scripts whose sources appear to be "
                    u"identical to the version that they override.")
        if not self._askContinue(message, u'bash.decompileAll.continue',
                                 _(u'Decompile All')): return
        with BusyCursor():
            for fileInfo in self.iselected_infos():
                if fileInfo.match_oblivion_re():
                    self._showWarning(_('Skipping %s') % fileInfo,
                                      _('Decompile All'))
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
                    m =(_(u'Scripts removed: %d.') + u'\n' +
                        _(u'Scripts remaining: %d')) % (
                        len(removed), len(scpt_grp.id_records))
                elif removed:
                    m = _(u'Only %d scripts were identical.  This is probably '
                          u'intentional, so no changes have been made.'
                          ) % len(removed)
                else:
                    m = _(u'No changes required.')
                self._showOk(m, fileInfo.fn_key)

#------------------------------------------------------------------------------
class _Esm_Esl_Flip(EnabledLink):
    _add_flag: str
    _remove_flag: str

    @property
    def _already_flagged(self): raise NotImplementedError

    def _exec_flip(self): raise NotImplementedError

    @property
    def link_text(self):
        return self._remove_flag if self._already_flagged else self._add_flag

    @balt.conversation
    def Execute(self):
        with BusyCursor():
            self._exec_flip()
            ##: HACK: forcing active refresh cause mods may be reordered and
            # we then need to sync order in skyrim's plugins.txt
            bosh.modInfos.refreshLoadOrder()
            # converted to esps/esls - rescan mergeable
            bosh.modInfos.rescanMergeable(self.selected, bolt.Progress())
            # This will have changed the plugin, so let BAIN know
            bosh.modInfos._notify_bain(
                altered={p.abs_path for p in self.iselected_infos()})
            # We need to RefreshUI all higher-loading plugins than the lowest
            # plugin that was affected to update the Indices column
            lowest_selected = min(self.selected,
                                  key=load_order.cached_lo_index_or_max)
            self.window.RefreshUI(
                redraw=load_order.cached_higher_loading(lowest_selected),
                refreshSaves=True)

class Mod_FlipEsm(_Esm_Esl_Flip):
    """Flip ESM flag. Extension must be .esp or .esu."""
    _help = _(u'Flips the ESM flag on the selected plugin(s), turning a master'
              u' into a regular plugin and vice versa.')
    _add_flag, _remove_flag = _(u'Add ESM Flag'), _(u'Remove ESM Flag')

    @property
    def _already_flagged(self):
        return self._first_selected().has_esm_flag()

    def _enable(self):
        """For pre esl games check if all mods are of the same type (esm or
        esp), based on the flag and if are all esp extension files. For esl
        games the esp extension is even more important as .esm and .esl files
        implicitly have the master flag set no matter what."""
        first_is_esm = self._already_flagged
        return all(m.fn_ext in (u'.esp', u'.esu') and
                   minfo.has_esm_flag() == first_is_esm
                   for m, minfo in self.iselected_pairs())

    def _exec_flip(self):
        message = (_(u'WARNING! For advanced modders only!') + u'\n\n' +
            _(u'This command flips an internal bit in the mod, converting an '
              u'ESP to an ESM and vice versa. For older games (Skyrim and '
              u'earlier), only this bit determines whether or not a plugin is '
              u'loaded as a master. In newer games (FO4 and later), files '
              u'with the ".esm" and ".esl" extension are always forced to '
              u'load as masters. Therefore, we disallow selecting those '
              u'plugins for ESP/ESM conversion on newer games.'))
        if not self._askContinue(message, u'bash.flipToEsmp.continue',
                                 _(u'Flip to ESM')): return
        for modInfo in self.iselected_infos():
            modInfo.set_esm_flag(not modInfo.has_esm_flag())

class Mod_FlipEsl(_Esm_Esl_Flip):
    """Flip an esp(esl) to an esl(esp)."""
    _help = _(u'Flips the ESL flag on the selected plugin(s), turning a light '
              u'plugin into a regular one and vice versa.')
    _add_flag, _remove_flag = _(u'Add ESL Flag'), _(u'Remove ESL Flag')

    @property
    def _already_flagged(self):
        return self._first_selected().has_esl_flag()

    def _enable(self):
        """Allow if all selected mods have valid extensions, have same esl flag
        and are esl capable if converting to esl."""
        first_is_esl = self._already_flagged
        return all(m.fn_ext in (u'.esm', u'.esp', u'.esu') and
                   minfo.has_esl_flag() == first_is_esl and
                   (first_is_esl or m in bosh.modInfos.mergeable)
                   for m, minfo in self.iselected_pairs())

    def _exec_flip(self):
        message = (_(u'WARNING! For advanced modders only!') + u'\n\n' +
            _(u'This command flips an internal bit in the mod, converting an '
              u'ESP to an ESL and vice versa.  Note that it is this bit OR '
              u'the ".esl" file extension that turns a mod into a light '
              u'plugin. We therefore disallow selecting files with the .esl '
              u'extension for converting into a light plugin (as they '
              u'implicitly are light plugins already).'))
        if not self._askContinue(message, u'bash.flipToEslp.continue',
                                 _(u'Flip to ESL')): return
        for modInfo in self.iselected_infos():
            modInfo.set_esl_flag(not modInfo.has_esl_flag())

#------------------------------------------------------------------------------
class Mod_FlipMasters(OneItemLink, _Esm_Esl_Flip):
    """Swaps masters between esp and esm versions."""
    _help = _(u'Flips the ESM flag on all masters of the selected plugin, '
              u'allowing you to load it in the %(ck_name)s.') % (
              {u'ck_name': bush.game.Ck.long_name})
    _add_flag = _('Add ESM Flag to Masters')
    _remove_flag = _(u'Remove ESM Flag From Masters')

    @property
    def _already_flagged(self): return not self.toEsm

    def _initData(self, window, selection):
        present_mods = window.data_store
        modinfo_masters = present_mods[selection[0]].masterNames
        if len(selection) == 1 and len(modinfo_masters) > 1:
            self.espMasters = [m for m in modinfo_masters if
                               m in present_mods and m.fn_ext == '.esp']
            self._do_enable = bool(self.espMasters)
        else:
            self.espMasters = []
            self._do_enable = False
        for mastername in self.espMasters:
            masterInfo = bosh.modInfos.get(mastername, None)
            if masterInfo and masterInfo.isInvertedMod():
                self.toEsm = False
                break
        else:
            self.toEsm = True
        super(Mod_FlipMasters, self)._initData(window, selection)

    def _enable(self): return self._do_enable

    def _exec_flip(self):
        message = _(u'WARNING! For advanced modders only! Flips the ESM flag '
                    u'of all ESP masters of the selected plugin. Useful for '
                    u'loading ESP-mastered mods in the %(ck_name)s.') % (
                    {u'ck_name': bush.game.Ck.long_name})
        if not self._askContinue(message, u'bash.flipMasters.continue'): return
        for masterPath in self.espMasters:
            master_mod_info = bosh.modInfos.get(masterPath)
            if master_mod_info:
                master_mod_info.set_esm_flag(self.toEsm)
                self.selected.append(masterPath) # for refresh in Execute

#------------------------------------------------------------------------------
class Mod_SetVersion(OneItemLink):
    """Sets version of file back to 0.8."""
    _text = _(u'Version 0.8')
    _help = _(u'Sets version of file back to 0.8.')
    message = _(u'WARNING! For advanced modders only! This feature allows you '
                u'to edit newer official mods in the %s by resetting the '
                u'internal file version number back to 0.8. While this will '
                u'make the mod editable, it may also break the mod in some '
                u'way.') % bush.game.Ck.long_name

    def _enable(self):
        return (super(Mod_SetVersion, self)._enable() and
                int(10 * self._selected_info.header.version) != 8)

    def Execute(self):
        if not self._askContinue(self.message, u'bash.setModVersion.continue',
                                 _(u'Set File Version')): return
        self._selected_info.makeBackup()
        self._selected_info.header.version = 0.8
        self._selected_info.header.setChanged()
        self._selected_info.writeHeader()
        #--Repopulate
        self.window.RefreshUI(redraw=[self._selected_item],
                              refreshSaves=False) # version: why affect saves ?

#------------------------------------------------------------------------------
# Import/Export submenus ------------------------------------------------------
#------------------------------------------------------------------------------
#--Import only
class Mod_Fids_Replace(OneItemLink):
    """Replace fids according to text file."""
    _text = _(u'Form IDs...')
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
            progress(0.1, _(u'Reading') + f' {textPath.stail}.')
            replacer.read_csv(textPath)
            progress(0.2, _(u'Applying to') + f' {self._selected_item}.')
            fids_changed = replacer.updateMod(self._selected_info)
            progress(1.0,_(u'Done.'))
        #--Log
        if not fids_changed: self._showOk(_(u'No changes required.'))
        else: self._showLog(fids_changed, title=_(u'Objects Changed'),
                            asDialog=True)

class Mod_Face_Import(OneItemLink):
    """Imports a face from a save to an esp."""
    _text = _(u'Face...')
    _help = _(u'Imports a face from a save to an ESP file.')

    def Execute(self):
        #--Select source face file
        srcDir = bosh.saveInfos.store_dir
        wildcard = (_(u'%(game_name)s Saves (*%(save_ext_on)s;'
                      u'*%(save_ext_off)s)')
                    + u'|*%(save_ext_on)s;*%(save_ext_off)s') % {
            'game_name': bush.game.display_name,
            u'save_ext_on': bush.game.Ess.ext,
            u'save_ext_off': bush.game.Ess.ext[:-1] + u'r',
        }
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
            # TODO(inf) de-wx! Again, image/bitmap stuff
            image = ImageWrapper.bmp_from_bitstream(
                *srcInfo.header.image_parameters).ConvertToImage()
            imagePath.head.makedirs()
            image.SaveFile(imagePath.s, ImageWrapper.img_types['.jpg'])
        self.window.RefreshUI(refreshSaves=False) # import save to esp
        self._showOk(_(u'Imported face to: %s') % npc.eid, self._selected_item)

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
        lo_plugins_set = set(load_order.cached_lo_tuple())
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
                readProgress(index, _('Reading') + f' {fileName}.')
                parser.readFromMod(fileInfo)
            progress(0.8, _(u'Exporting to') + f' {textPath.stail}.')
            parser.write_text_file(textPath)
            progress(1.0, _(u'Done.'))

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
            progress(0.1, _(u'Reading') + f' {textPath.stail}.')
            if ext == u'.csv':
                parser.read_csv(textPath)
            else:
                srcInfo = bosh.ModInfo(textPath)
                parser.readFromMod(srcInfo)
            progress(0.2, _(u'Applying to') + f' {self._selected_item}.')
            changes = parser.writeToMod(self._selected_info)
            progress(1.0, _(u'Done.'))
        return changes

    def _showLog(self, logText, title=u'', asDialog=False, fixedFont=False,
                 lg_icons=Link._default_icons):
        super(_Mod_Import_Link, self)._showLog(logText,
            title=title or self.__class__.progressTitle, asDialog=asDialog,
            fixedFont=fixedFont, lg_icons=lg_icons)

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
            plugin_exts = u'or '.join(sorted(bush.game.espm_extensions
                                             | {u'.ghost'}))
            if len(supportedExts) > 1:
                csv_err = _(u'Source file must be a %s file or a plugin '
                            u'(%s).') % (csv_filename, plugin_exts)
            else:
                csv_err = _(u'Source file must be a %s file.') % csv_filename
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
    _text = _(u'NPC Levels...')
    _help = _(u'Export NPC level info from mod to text file.')

    def _parser(self):
        return ActorLevels()

    def Execute(self): # overrides _Mod_Export_Link
        message = (_(
            'This command will export the level info for NPCs whose level is '
            'offset with respect to the PC.  The exported file can be edited '
            'with most spreadsheet programs and then reimported.') + u'\n\n' +
                   _('See the Wrye Bash readme for more info.'))
        if not self._askContinue(message, u'bash.actorLevels.export.continue',
                                 _(u'Export NPC Levels')): return
        super(Mod_ActorLevels_Export, self).Execute()

class Mod_ActorLevels_Import(_Mod_Import_Link):
    """Imports actor levels from text file to mod."""
    askTitle = _(u'Import NPC levels from:')
    csvFile = u'_NPC_Levels.csv'
    progressTitle = _(u'Import NPC Levels')
    _text = _(u'NPC Levels...')
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
    _text = _(u'Relations...')
    _help = _(u'Export faction relations from mod to text file')

    def _parser(self):
        return FactionRelations()

class Mod_FactionRelations_Import(_Mod_Import_Link):
    """Imports faction relations from text file to mod."""
    askTitle = _(u'Import faction relations from:')
    csvFile = u'_Relations.csv'
    progressTitle = _(u'Import Relations')
    _text = _(u'Relations...')
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
    _text = _(u'Factions...')
    _help = _(u'Export factions from mod to text file')

    def _parser(self):
        return ActorFactions()

class Mod_Factions_Import(_Mod_Import_Link):
    """Imports factions from text file to mod."""
    askTitle = _(u'Import Factions from:')
    csvFile = u'_Factions.csv'
    progressTitle = _(u'Import Factions')
    _text = _(u'Factions...')
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
    _text = _(u'Scripts...')
    _help = _(u'Export scripts from mod to text file')

    def _parser(self):
        return ScriptText()

    def Execute(self): # overrides _Mod_Export_Link
        fileInfo = next(self.iselected_infos()) # first selected info
        defaultPath = bass.dirs['patches'].join(f'{fileInfo} Exported Scripts')
        if not ExportScriptsDialog.display_dialog(Link.Frame):
            return
        def_exists = defaultPath.exists()
        if not def_exists:
            defaultPath.makedirs()
        textDir = self._askDirectory(
            message=_(u'Choose directory to export scripts to'),
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
        msg = (_(u'Exported %d scripts from %s:') + u'\n%s') % (
            len(exportedScripts), fileInfo, u'\n'.join(exportedScripts))
        self._showLog(msg, title=_(u'Export Scripts'), asDialog=True)

class Mod_Scripts_Import(_Mod_Import_Link):
    """Import scripts from text file."""
    _text = _(u'Scripts...')
    _help = _(u'Import scripts from text file')
    continueInfo = _(
        u'Import script from a text file.  This will replace existing '
        u'scripts and is not reversible (except by restoring from backup)!')
    continueKey = u'bash.scripts.import.continue'
    progressTitle = _(u'Import Scripts')
    _parser_class = ScriptText

    def Execute(self):
        if not self._askContinueImport(): return
        defaultPath = bass.dirs[u'patches'].join(
            f'{self._selected_item} Exported Scripts')
        if not defaultPath.exists():
            defaultPath = bass.dirs[u'patches']
        textDir = self._askDirectory(
            message=_(u'Choose directory to import scripts from'),
            defaultPath=defaultPath)
        if not textDir: return
        message = _("Import scripts that don't exist in the esp as new"
            ' scripts?') + '\n' + _('(If not they will just be skipped).')
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
                (_('Imported %d changed scripts from %s:'), altered),
                (_('Imported %d new scripts from %s:'), added)):
            if scripts:
                log_msg.append(msg % (len(scripts), textDir) + (
                        '\n*%s' % '\n*'.join(sorted(scripts))))
        self._showLog('\n\n'.join(log_msg), title=_('Import Scripts'))

#------------------------------------------------------------------------------
class Mod_Stats_Export(_Mod_Export_Link):
    """Exports stats from the selected plugin to a CSV file (for the record
    types specified in bush.game.stats_attrs)."""
    askTitle = _(u'Export stats to:')
    csvFile = u'_Stats.csv'
    progressTitle = _(u'Export Stats')
    _text = _(u'Stats...')
    _help = _(u'Export stats from mod to text file')

    def _parser(self):
        return ItemStats()

class Mod_Stats_Import(_Mod_Import_Link):
    """Import stats from text file."""
    askTitle = _(u'Import stats from:')
    csvFile = u'_Stats.csv'
    progressTitle = _(u'Import Stats')
    _text = _(u'Stats...')
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
    askTitle = _(u'Export prices to:')
    csvFile = u'_Prices.csv'
    progressTitle = _(u'Export Prices')
    _text = _(u'Prices...')
    _help = _(u'Export item prices from mod to text file')

    def _parser(self):
        return ItemPrices()

class Mod_Prices_Import(_Mod_Import_Link):
    """Import prices from text file or other mod."""
    askTitle = _(u'Import prices from:')
    csvFile = u'_Prices.csv'
    progressTitle = _(u'Import Prices')
    _text = _(u'Prices...')
    _help = _(u'Import item prices from text file or other mod')
    continueInfo = _(u'Import item prices from a text file.  This will '
                     u'replace existing prices and is not reversible!')
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
    askTitle = _(u'Export Sigil Stone details to:')
    csvFile = u'_SigilStones.csv'
    progressTitle = _(u'Export Sigil Stone details')
    _text = _(u'Sigil Stones...')
    _help = _(u'Export Sigil Stone details from mod to text file')

    def _parser(self):
        return SigilStoneDetails()

class Mod_SigilStoneDetails_Import(_Mod_Import_Link):
    """Import Sigil Stone details from text file."""
    askTitle = _(u'Import Sigil Stone details from:')
    csvFile = u'_SigilStones.csv'
    progressTitle = _(u'Import Sigil Stone details')
    _text = _(u'Sigil Stones...')
    _help = _(u'Import Sigil Stone details from text file')
    continueInfo = _(
        u'Import Sigil Stone details from a text file.  This will replace '
        u'the existing data on sigil stones with the same form ids and is '
        u'not reversible!')
    continueKey = u'bash.SigilStone.import.continue'
    noChange = _(u'No relevant Sigil Stone details to import.')
    _parser_class = SigilStoneDetails

    def _log(self, changes, fileName):
        msg = [_('Imported Sigil Stone details to mod %s:') % fileName]
        msg.extend(f'* {eid}' for eid in sorted(changes))
        self._showLog('\n'.join(msg))

#------------------------------------------------------------------------------
class _SpellRecords_Link(ItemLink):
    """Common code from Mod_SpellRecords_{Ex,Im}port."""
    _do_what = progressTitle = u'OVERRIDE' # avoid pycharm warnings

    def __init__(self, _text=None):
        super(_SpellRecords_Link, self).__init__(_text)
        self.do_detailed = False

    def _parser(self):
        return SpellRecords(detailed=self.do_detailed)

    def Execute(self):
        message = f'{self._do_what}\n' + _(
            '(If not, they will just be skipped).')
        self.do_detailed = self._askYes(message, self.progressTitle,
                                        questionIcon=True)
        super().Execute()

class Mod_SpellRecords_Export(_SpellRecords_Link, _Mod_Export_Link):
    """Export Spell details from mod to text file."""
    askTitle = _(u'Export Spell details to:')
    csvFile = u'_Spells.csv'
    progressTitle = _(u'Export Spell details')
    _text = _(u'Spells...')
    _help = _(u'Export Spell details from mod to text file')
    _do_what = _(u'Export flags and effects?')

class Mod_SpellRecords_Import(_SpellRecords_Link, _Mod_Import_Link):
    """Import Spell details from text file."""
    askTitle = _(u'Import Spell details from:')
    csvFile = u'_Spells.csv'
    progressTitle = _(u'Import Spell details')
    _text = _(u'Spells...')
    _help = _(u'Import Spell details from text file')
    continueInfo = _(u'Import Spell details from a text file.  This will '
        u'replace the existing data on spells with the same form ids and is '
        u'not reversible!')
    continueKey = u'bash.SpellRecords.import.continue'
    noChange = _(u'No relevant Spell details to import.')
    _do_what = _(u'Import flags and effects?')

    def _log(self, changes, fileName):
        msg = [_('Imported Spell details to mod %s:') % fileName]
        msg.extend(f'* {eid}' for eid in sorted(changes))
        self._showLog('\n'.join(msg))

#------------------------------------------------------------------------------
class Mod_IngredientDetails_Export(_Mod_Export_Link):
    """Export Ingredient details from mod to text file."""
    askTitle = _(u'Export Ingredient details to:')
    csvFile = u'_Ingredients.csv'
    progressTitle = _(u'Export Ingredient details')
    _text = _(u'Ingredients...')
    _help = _(u'Export Ingredient details from mod to text file')

    def _parser(self):
        return IngredientDetails()

class Mod_IngredientDetails_Import(_Mod_Import_Link):
    """Import Ingredient details from text file."""
    askTitle = _(u'Import Ingredient details from:')
    csvFile = u'_Ingredients.csv'
    progressTitle = _(u'Import Ingredient details')
    _text = _(u'Ingredients...')
    _help = _(u'Import Ingredient details from text file')
    continueInfo = _(u'Import Ingredient details from a text file.  This will '
                     u'replace the existing data on Ingredients with the same '
                     u'form ids and is not reversible!')
    continueKey = u'bash.Ingredient.import.continue'
    noChange = _(u'No relevant Ingredient details to import.')
    _parser_class = IngredientDetails

    def _log(self, changes, fileName):
        msg = [_('Imported Ingredient details to mod %s:') % fileName]
        msg.extend(f'* {eid}' for eid in sorted(changes))
        self._showLog('\n'.join(msg))

#------------------------------------------------------------------------------
class Mod_EditorIds_Export(_Mod_Export_Link):
    """Export editor ids from mod to text file."""
    askTitle = _('Export Editor IDs to:')
    csvFile = u'_Eids.csv'
    progressTitle = _('Export Editor IDs')
    _text = _('Editor IDs...')
    _help = _(u'Export faction editor IDs from plugin to text file.')

    def _parser(self):
        return EditorIds()

class Mod_EditorIds_Import(_Mod_Import_Link):
    """Import editor ids from text file."""
    askTitle = _('Import Editor IDs from:')
    csvFile = u'_Eids.csv'
    continueInfo = _('Import editor IDs from a text file. This will replace '
                     'existing IDs and is not reversible!')
    continueKey = u'bash.editorIds.import.continue'
    progressTitle = _(u'Import Editor IDs')
    _text = _('Editor IDs...')
    _help = _('Import faction editor IDs from text file.')

    def _parser(self, questionableEidsSet=None, badEidsList=None):
        return EditorIds(questionableEidsSet=questionableEidsSet,
                         badEidsList=badEidsList)

    def Execute(self):
        if not self._askContinueImport(): return
        textPath = self._import_from()
        if not textPath: return
        #--Extension error check
        if textPath.cext != u'.csv':
            self._showError(_(u'Source file must be a csv file.'))
            return
        #--Import
        questionableEidsSet = set()
        badEidsList = []
        try:
            with balt.Progress(self.__class__.progressTitle) as progress:
                editorIds = self._parser(questionableEidsSet, badEidsList)
                progress(0.1, _(u'Reading') + f' {textPath.stail}.')
                editorIds.read_csv(textPath)
                progress(0.2, _(u'Applying to %s.') % self._selected_item)
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
                    buff.append('\n* ' + _('These editor ids begin with '
                        'numbers and may therefore cause the script compiler '
                        'to generate unexpected results'))
                if badEidsList:
                    buff.append('\n' + _('The following EIDs are malformed '
                                         'and were not imported:'))
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
    _text = _(u'Names...')
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
    _text = _(u'Names...')
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
