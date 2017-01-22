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

"""Menu items for the _item_ menu of the mods tab - their window attribute
points to BashFrame.modList singleton."""

import StringIO
import collections
import copy
import os
import time
from operator import attrgetter
from .. import bass, bosh, bolt, balt, bush, parsers, load_order
from ..bass import Resources
from ..balt import ItemLink, Link, TextCtrl, toggleButton, vSizer, \
    StaticText, hspacer, CheckLink, EnabledLink, AppendableLink, TransLink, \
    RadioLink, SeparatorLink, ChoiceLink, OneItemLink, Image, ListBoxes, \
    OkButton
from ..bolt import GPath, SubProgress, AbstractError, CancelError, formatDate
from ..bosh import faces
from ..patcher import configIsCBash, exportConfig, patch_files
from .frames import DocBrowser
from .constants import JPEG, settingDefaults
from ..cint import CBashApi, FormID
from .patcher_dialog import PatchDialog, CBash_gui_patchers, PBash_gui_patchers

__all__ = ['Mod_FullLoad', 'Mod_CreateDummyMasters', 'Mod_OrderByName',
           'Mod_Groups', 'Mod_Ratings', 'Mod_Details', 'Mod_ShowReadme',
           'Mod_ListBashTags', 'Mod_CreateBOSSReport', 'Mod_CopyModInfo',
           'Mod_AllowGhosting', 'Mod_Ghost', 'Mod_MarkMergeable',
           'Mod_Patch_Update', 'Mod_ListPatchConfig', 'Mod_ExportPatchConfig',
           'CBash_Mod_CellBlockInfo_Export', 'Mod_EditorIds_Export',
           'Mod_FullNames_Export', 'Mod_Prices_Export', 'Mod_Stats_Export',
           'Mod_Factions_Export', 'Mod_ActorLevels_Export', 'Mod_Redate',
           'CBash_Mod_MapMarkers_Export', 'Mod_FactionRelations_Export',
           'Mod_IngredientDetails_Export', 'Mod_Scripts_Export',
           'Mod_SigilStoneDetails_Export', 'Mod_SpellRecords_Export',
           'Mod_EditorIds_Import', 'Mod_FullNames_Import', 'Mod_Prices_Import',
           'Mod_Stats_Import', 'Mod_Factions_Import', 'Mod_ActorLevels_Import',
           'CBash_Mod_MapMarkers_Import', 'Mod_FactionRelations_Import',
           'Mod_IngredientDetails_Import', 'Mod_Scripts_Import',
           'Mod_SigilStoneDetails_Import', 'Mod_SpellRecords_Import',
           'Mod_Face_Import', 'Mod_Fids_Replace', 'Mod_SkipDirtyCheck',
           'Mod_ScanDirty', 'Mod_RemoveWorldOrphans', 'Mod_FogFixer',
           'Mod_UndeleteRefs', 'Mod_AddMaster', 'Mod_CopyToEsmp',
           'Mod_DecompileAll', 'Mod_FlipSelf', 'Mod_FlipMasters',
           'Mod_SetVersion', 'Mod_ListDependent', 'Mod_JumpToInstaller']

#------------------------------------------------------------------------------
# Mod Links -------------------------------------------------------------------
#------------------------------------------------------------------------------
class Mod_FullLoad(OneItemLink):
    """Tests all record definitions against a specific mod"""
    _text = _(u'Test Full Record Definitions...')

    def Execute(self):
        with balt.Progress(_(u'Loading:') + u'\n%s'
                % self._selected_item.stail) as progress:
            print bosh.MreRecord.type_class
            readClasses = bosh.MreRecord.type_class
            print readClasses.values()
            loadFactory = parsers.LoadFactory(False, *readClasses.values())
            modFile = parsers.ModFile(self._selected_info, loadFactory)
            try:
                modFile.load(True, progress)
            except:
                deprint('exception:\n', traceback=True)

# File submenu ----------------------------------------------------------------
# the rest of the File submenu links come from file_links.py
class Mod_CreateDummyMasters(OneItemLink):
    """TES4Edit tool, makes dummy plugins for each missing master, for use if looking at a 'Filter' patch."""
    _text = _(u'Create Dummy Masters...')
    help = _(u"TES4Edit tool, makes dummy plugins for each missing master of"
             u" the selected mod, for use if looking at a 'Filter' patch")

    def _enable(self):
        return super(Mod_CreateDummyMasters, self)._enable() and \
               self._selected_info.getStatus() == 30  # Missing masters

    def Execute(self):
        """Create Dummy Masters"""
        msg = _(u"This is an advanced feature for editing 'Filter' patches in "
                u"TES4Edit.  It will create dummy plugins for each missing "
                u"master.  Are you sure you want to continue?") + u'\n\n' + _(
                u"To remove these files later, use 'Clean Dummy Masters...'")
        if not self._askYes(msg, title=_(u'Create Files')): return
        doCBash = bass.settings['bash.CBashEnabled'] # something odd's going on, can't rename temp names
        if doCBash:
            newFiles = []
        refresh = []
        # creates esp files - so place them correctly after the last esm
        previous_master = bosh.modInfos.cached_lo_last_esm()
        for master in self._selected_info.header.masters:
            if master in bosh.modInfos:
                continue
            # Missing master, create a dummy plugin for it
            newInfo = bosh.ModInfo(self._selected_info.dir, master)
            refresh.append((master, newInfo, previous_master))
            previous_master = master
            if doCBash:
                # TODO: CBash doesn't handle unicode.  Make temp unicode safe
                # files, then rename them to the correct unicode name later
                newFiles.append(newInfo.getPath().stail)
            else:
                newFile = parsers.ModFile(newInfo, parsers.LoadFactory(True))
                newFile.tes4.author = u'BASHED DUMMY'
                newFile.safeSave()
        if doCBash:
            with ObCollection(ModsPath=bass.dirs['mods'].s) as Current:
                tempname = u'_DummyMaster.esp.tmp'
                modFile = Current.addMod(tempname, CreateNew=True)
                Current.load()
                modFile.TES4.author = u'BASHED DUMMY'
                for newFile in newFiles:
                    modFile.save(CloseCollection=False,DestinationName=newFile)
        to_select = []
        for mod, info, previous in refresh:
            # add it to modInfos or lo_insert_after blows for timestamp games
            bosh.modInfos.refreshFile(mod)
            bosh.modInfos.cached_lo_insert_after(previous, mod)
            to_select.append(mod)
        bosh.modInfos.cached_lo_save_lo()
        bosh.modInfos.refresh(refresh_infos=False)
        self.window.RefreshUI(refreshSaves=True, detail_item=to_select[-1])
        self.window.SelectItemsNoCallback(to_select)

class Mod_OrderByName(EnabledLink):
    """Sort the selected files."""
    _text = _(u'Sort')
    help = _(u"Sort the selected files.")

    def _enable(self): return len(self.selected) > 1

    @balt.conversation
    def Execute(self):
        message = _(u'Reorder selected mods in alphabetical order?  The first '
            u'file will be given the date/time of the current earliest file '
            u'in the group, with consecutive files following at 1 minute '
            u'increments.') if not load_order.using_txt_file() else _(
            u'Reorder selected mods in alphabetical order starting at the '
            u'lowest ordered?')
        message += (u'\n\n' + _(
            u'Note that some mods need to be in a specific order to work '
            u'correctly, and this sort operation may break that order.'))
        if not self._askContinue(message, 'bash.sortMods.continue',
                                 _(u'Sort Mods')): return
        #--Do it
        self.selected.sort()
        self.selected.sort(key=attrgetter('cext')) # sort esm first
        if not load_order.using_txt_file():
            #--Get first time from first selected file.
            newTime = min(x.mtime for x in self.iselected_infos())
            for inf in self.iselected_infos():
                inf.setmtime(newTime)
                newTime += 60
            #--Refresh
            with load_order.Unlock():
                bosh.modInfos.refresh(refresh_infos=False, _modTimesChange=True)
        else:
            lowest = load_order.get_ordered(self.selected)[0]
            bosh.modInfos.cached_lo_insert_at(lowest, self.selected)
            bosh.modInfos.cached_lo_save_lo()
        self.window.RefreshUI(refreshSaves=True)

class Mod_Redate(AppendableLink, ItemLink):
    """Move the selected files to start at a specified date."""
    _text = _(u'Redate...')
    help = _(u"Move the selected files to start at a specified date.")

    def _append(self, window): return not load_order.using_txt_file()

    @balt.conversation
    def Execute(self):
        #--Ask user for revised time.
        newTimeStr = self._askText(
            _(u'Redate selected mods starting at...'),
            title=_(u'Redate Mods'), default=formatDate(int(time.time())))
        if not newTimeStr: return
        try:
            newTimeTup = bolt.unformatDate(newTimeStr, u'%c')
            newTime = int(time.mktime(newTimeTup))
        except ValueError:
            self._showError(_(u'Unrecognized date: ') + newTimeStr)
            return
        #--Do it
        selInfos = [x for x in self.iselected_infos()]
        selInfos.sort(key=attrgetter('mtime'))
        for fileInfo in selInfos:
            fileInfo.setmtime(newTime)
            newTime += 60
        #--Refresh
        with load_order.Unlock():
            bosh.modInfos.refresh(refresh_infos=False, _modTimesChange=True)
        self.window.RefreshUI(refreshSaves=True)

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
        newName = balt.askText(self.parent, self.addPrompt)
        if newName is None: return
        if newName in self.mod_labels:
            balt.showError(self.parent,_(u'Name must be unique.'))
            return False
        elif len(newName) == 0 or len(newName) > 64:
            balt.showError(self.parent,
                _(u'Name must be between 1 and 64 characters long.'))
            return False
        bass.settings.setChanged(self.setKey)
        self.mod_labels.append(newName)
        self.mod_labels.sort()
        return newName

    def _refresh(self, redraw): # editing mod labels should not affect saves
        self.parent.RefreshUI(redraw=redraw, refreshSaves=False)

    def rename(self,oldName,newName):
        """Renames oldName to newName."""
        #--Right length?
        if len(newName) == 0 or len(newName) > 64:
            balt.showError(self.parent,
                _(u'Name must be between 1 and 64 characters long.'))
            return False
        #--Rename
        bass.settings.setChanged(self.setKey)
        self.mod_labels.remove(oldName)
        self.mod_labels.append(newName)
        self.mod_labels.sort()
        #--Edit table entries.
        colGroup = bosh.modInfos.table.getColumn(self.column)
        changed= []
        for fileName in colGroup.keys():
            if colGroup[fileName] == oldName:
                colGroup[fileName] = newName
                changed.append(fileName)
        self._refresh(redraw=changed)
        #--Done
        return newName

    def remove(self,item):
        """Removes group."""
        bass.settings.setChanged(self.setKey)
        self.mod_labels.remove(item)
        #--Edit table entries.
        colGroup = bosh.modInfos.table.getColumn(self.column)
        changed= []
        for fileName in colGroup.keys():
            if colGroup[fileName] == item:
                del colGroup[fileName]
                changed.append(fileName)
        self._refresh(redraw=changed)
        #--Done
        return True

    def setTo(self, items):
        """Set the bosh.settings[self.setKey] list to the items given - do
        not update mod List for removals (i.e. if a group/rating is removed
        there may be mods still assigned to it or rated) - it's a feature.
        """
        items.sort(key=lambda a: a.lower())
        if self.mod_labels == items: return False
        bass.settings.setChanged(self.setKey)
        # do not reassign self.mod_labels! points to settings[self.setKey]
        self.mod_labels[:] = items
        return True

class _Mod_Labels(ChoiceLink):
    """Add mod label links."""
    extraButtons = {} # extra actions for the edit dialog

    def _refresh(self): # editing mod labels should not affect saves
        self.window.RefreshUI(redraw=self.selected, refreshSaves=False)

    def __init__(self):
        super(_Mod_Labels, self).__init__()
        self.mod_labels = bass.settings[self.setKey]
        #-- Links
        _self = self
        class _Edit(ItemLink):
            _text = help = _self.editMenuText
            def Execute(self):
                """Show label editing dialog."""
                data = _Mod_LabelsData(self.window, _self)  # ListEditorData
                with balt.ListEditor(self.window, _self.editWindowTitle, data,
                                     _self.extraButtons) as _self.listEditor:
                    _self.listEditor.ShowModal()  ##: consider only refreshing
                    # the mod list if this returns true
                del _self.listEditor  ##: used by the buttons code - should be
                # encapsulated
        class _None(ItemLink):
            _text = _(u'None')
            help = _(u'Clear labels from selected mod(s)')
            def Execute(self):
                """Handle selection of None."""
                fileLabels = bosh.modInfos.table.getColumn(_self.column)
                for fileName in self.selected:
                    fileLabels[fileName] = u''
                _self._refresh()
        self.extraItems = [_Edit(), SeparatorLink(), _None()]

    def _initData(self, window, selection):
        super(_Mod_Labels, self)._initData(window, selection)
        _self = self
        class _LabelLink(ItemLink):
            def Execute(self):
                fileLabels = bosh.modInfos.table.getColumn(_self.column)
                for fileName in self.selected:
                    fileLabels[fileName] = self._text
                _self._refresh()
        self.__class__.choiceLinkType = _LabelLink

    @property
    def _choices(self): return sorted(self.mod_labels, key=lambda a: a.lower())

#--Groups ---------------------------------------------------------------------
class _Mod_Groups_Export(ItemLink):
    """Export mod groups to text file."""
    askTitle = _(u'Export groups to:')
    csvFile = u'_Groups.csv'
    _text = _(u'Export Groups')
    help = _(u'Export groups of selected mods to a csv file')

    def Execute(self):
        textName = u'My' + self.__class__.csvFile
        textDir = bass.dirs['patches']
        textDir.makedirs()
        #--File dialog
        textPath = self._askSave(title=self.__class__.askTitle,
                                 defaultDir=textDir, defaultFile=textName,
                                 wildcard=u'*' + self.__class__.csvFile)
        if not textPath: return
        #--Export
        modGroups = bosh.ModGroups()
        modGroups.readFromModInfos(self.selected)
        modGroups.writeToText(textPath)
        self._showOk(_(u"Exported %d mod/groups.") % len(modGroups.mod_group))

class _Mod_Groups_Import(ItemLink):
    """Import mod groups from text file."""
    _text = _(u'Import Groups')
    help = _(u'Import groups for selected mods from a csv file (filename must'
             u' end in _Groups.csv)')

    def Execute(self):
        message = _(
            u"Import groups from a text file ? This will assign to selected "
            u"mods the group they are assigned in the text file, if any.")
        if not self._askContinue(message, 'bash.groups.import.continue',
                                 _(u'Import Groups')): return
        textDir = bass.dirs['patches']
        #--File dialog
        textPath = self._askOpen(_(u'Import names from:'),textDir,
            u'', u'*_Groups.csv',mustExist=True)
        if not textPath: return
        (textDir,textName) = textPath.headTail
        #--Extension error check
        if textName.cext != u'.csv':
            self._showError(_(u'Source file must be a csv file.'))
            return
        #--Import
        modGroups = bosh.ModGroups()
        modGroups.readFromText(textPath)
        changed = modGroups.writeToModInfos(self.selected)
        bosh.modInfos.refresh()
        self.window.RefreshUI(refreshSaves=False) # was True (importing groups)
        self._showOk(_(u"Imported %d mod/groups (%d changed).") % (
            len(modGroups.mod_group), changed), _(u"Import Groups"))

class Mod_Groups(_Mod_Labels):
    """Add mod group links."""
    def __init__(self):
        self.column     = 'group'
        self.setKey     = 'bash.mods.groups'
        self.addPrompt  = _(u'Add group:')
        self.extraButtons = collections.OrderedDict([
            (_(u'Refresh'), self._doRefresh), (_(u'Sync'), self._doSync),
            (_(u'Reset'), self._doReset)] )
        self.editMenuText   = _(u'Edit Groups...')
        self.editWindowTitle = _(u'Groups')
        super(Mod_Groups, self).__init__()
        self.extraItems = [_Mod_Groups_Export(),
                           _Mod_Groups_Import()] + self.extraItems

    def _initData(self, window, selection):
        super(Mod_Groups, self)._initData(window, selection)
        selection = set(selection)
        mod_group = bosh.modInfos.table.getColumn('group').items()
        modGroup = set([x[1] for x in mod_group if x[0] in selection])
        class _CheckGroup(CheckLink, self.__class__.choiceLinkType):
            def _check(self):
                """Check the Link if any of the selected mods belongs to it."""
                return self._text in modGroup
        self.__class__.choiceLinkType = _CheckGroup

    def _doRefresh(self):
        """Add to the list of groups groups currently assigned to mods."""
        self.listEditor.SetItemsTo(list(set(bass.settings[
            'bash.mods.groups']) | bosh.ModGroups.assignedGroups()))

    def _doSync(self):
        """Set the list of groups to groups currently assigned to mods."""
        msg = _(u'This will set the list of available groups to the groups '
                u'currently assigned to mods. Continue ?')
        if not balt.askContinue(self.listEditor, msg,
                                'bash.groups.sync.continue',
                                _(u'Sync Groups')): return
        self.listEditor.SetItemsTo(list(bosh.ModGroups.assignedGroups()))

    def _doReset(self):
        """Set the list of groups to the default groups list.

        Won't clear user set groups from the modlist - most probably not
        what the user wants.
        """
        msg = _(u"This will reset the list of available groups to the default "
                u"group list. It won't however remove non default groups from "
                u"mods that are already tagged with them. Continue ?")
        if not balt.askContinue(self.listEditor, msg,
                                'bash.groups.reset.continue',
                                _(u'Reset Groups')): return
        self.listEditor.SetItemsTo(list(settingDefaults['bash.mods.groups']))

#--Ratings --------------------------------------------------------------------
class Mod_Ratings(_Mod_Labels):
    """Add mod rating links."""
    def __init__(self):
        self.column     = 'rating'
        self.setKey     = 'bash.mods.ratings'
        self.addPrompt  = _(u'Add rating:')
        self.editMenuText   = _(u'Edit Ratings...')
        self.editWindowTitle = _(u'Ratings')
        super(Mod_Ratings, self).__init__()

# Mod info menus --------------------------------------------------------------
#------------------------------------------------------------------------------
class Mod_Details(OneItemLink):
    """Show Mod Details"""
    _text = _(u'Details...')
    help = _(u'Show Mod Details')

    def Execute(self):
        with balt.Progress(self._selected_item.s) as progress:
            mod_details = bosh.mods_metadata.ModDetails()
            mod_details.readFromMod(self._selected_info,
                                    SubProgress(progress, 0.1, 0.7))
            buff = StringIO.StringIO()
            progress(0.7,_(u'Sorting records.'))
            for group in sorted(mod_details.group_records):
                buff.write(group+u'\n')
                if group in ('CELL','WRLD','DIAL'):
                    buff.write(u'  '+_(u'(Details not provided for this record type.)')+u'\n\n')
                    continue
                records = mod_details.group_records[group]
                records.sort(key = lambda a: a[1].lower())
                #if group != 'GMST': records.sort(key = lambda a: a[0] >> 24)
                for fid,eid in records:
                    buff.write(u'  %08X %s\n' % (fid,eid))
                buff.write(u'\n')
            self._showLog(buff.getvalue(), title=self._selected_item.s,
                          fixedFont=True, icons=Resources.bashBlue)
            buff.close()

class Mod_ShowReadme(OneItemLink):
    """Open the readme."""
    _text = _(u'Readme...')
    help = _(u'Open the readme')

    def Execute(self):
        if not Link.Frame.docBrowser:
            DocBrowser().Show()
            bass.settings['bash.modDocs.show'] = True
        #balt.ensureDisplayed(docBrowser)
        Link.Frame.docBrowser.SetMod(self._selected_item)
        Link.Frame.docBrowser.Raise()

class Mod_ListBashTags(ItemLink):
    """Copies list of bash tags to clipboard."""
    _text = _(u"List Bash Tags...")
    help = _(u'Copies list of bash tags to clipboard')

    def Execute(self):
        #--Get masters list
        modInfos = [x for x in self.iselected_infos()]
        text = bosh.modInfos.getTagList(modInfos)
        balt.copyToClipboard(text)
        self._showLog(text, title=_(u"Bash Tags"), fixedFont=False,
                      icons=Resources.bashBlue)

def _getUrl(fileName, installer, text):
    """"Try to get the url of the file (order of priority will be: TESNexus,
    TESAlliance)."""
    url = None
    ma = bosh.reTesNexus.search(installer)
    if ma and ma.group(2):
        url = bush.game.nexusUrl + u'downloads/file.php?id=' + ma.group(2)
    if not url:
        ma = bosh.reTESA.search(installer)
        if ma and ma.group(2):
            url = u'http://tesalliance.org/forums/index.php?app' \
                  u'=downloads&showfile=' + ma.group(2)
    if url: text += u'[url=' + url + u']' + fileName.s + u'[/url]'
    else: text += fileName.s
    return text

class Mod_CreateBOSSReport(EnabledLink):
    """Copies appropriate information for making a report in the BOSS thread."""
    _text = _(u"Create BOSS Report...")

    def _enable(self):
        return len(self.selected) != 1 or (
            not bosh.reOblivion.match(self.selected[0].s))

    def Execute(self):
        text = u''
        if len(self.selected) > 5:
            spoiler = True
            text += u'[spoiler]\n'
        else:
            spoiler = False
        # Scan for ITM and UDR's
        modInfos = [x for x in self.iselected_infos()]
        try:
            with balt.Progress(_(u"Dirty Edits"),u'\n'+u' '*60,abort=True) as progress:
                udr_itm_fog = bosh.mods_metadata.ModCleaner.scan_Many(modInfos, progress=progress)
        except bolt.CancelError:
            return
        # Create the report
        for i, (fileName, fileInfo) in enumerate(self.iselected_pairs()):
            if fileName == u'Oblivion.esm': continue
            #-- Name of file, plus a link if we can figure it out
            installer = bosh.modInfos.table.getItem(fileName,'installer',u'')
            if not installer: text += fileName.s
            else: text = _getUrl(fileName, installer, text)
            #-- Version, if it exists
            version = bosh.modInfos.getVersion(fileName)
            if version:
                text += u'\n'+_(u'Version')+u': %s' % version
            #-- CRC
            text += u'\n'+_(u'CRC')+u': %08X' % fileInfo.cachedCrc()
            #-- Dirty edits
            if udr_itm_fog:
                udrs,itms,fogs = udr_itm_fog[i]
                if udrs or itms:
                    if bass.settings['bash.CBashEnabled']:
                        text += (u'\nUDR: %i, ITM: %i '+_(u'(via Wrye Bash)')) % (len(udrs),len(itms))
                    else:
                        text += (u'\nUDR: %i, ITM not scanned '+_(u'(via Wrye Bash)')) % len(udrs)
            text += u'\n\n'
        if spoiler: text += u'[/spoiler]'

        # Show results + copy to clipboard
        balt.copyToClipboard(text)
        self._showLog(text, title=_(u'BOSS Report'), fixedFont=False,
                      icons=Resources.bashBlue)

class Mod_CopyModInfo(ItemLink):
    """Copies the basic info about selected mod(s)."""
    _text = _(u'Copy Mod Info...')
    help = _(u'Copies the basic info about selected mod(s)')

    def Execute(self):
        text = u''
        if len(self.selected) > 5:
            spoiler = True
            text += u'[spoiler]'
        else:
            spoiler = False
        # Create the report
        isFirst = True
        for i,fileName in enumerate(self.selected):
            # add a blank line in between mods
            if isFirst: isFirst = False
            else: text += u'\n\n'
            #-- Name of file, plus a link if we can figure it out
            installer = bosh.modInfos.table.getItem(fileName,'installer',u'')
            if not installer: text += fileName.s
            else: text = _getUrl(fileName, installer, text)
            labels = self.window.labels
            for col in self.window.cols:
                if col == 'File': continue
                lab = labels[col](self.window, fileName)
                text += u'\n%s: %s' % (col, lab if lab else u'-')
            #-- Version, if it exists
            version = bosh.modInfos.getVersion(fileName)
            if version:
                text += u'\n'+_(u'Version')+u': %s' % version
        if spoiler: text += u'[/spoiler]'
        # Show results + copy to clipboard
        balt.copyToClipboard(text)
        self._showLog(text, title=_(u'Mod Info Report'), fixedFont=False,
                      icons=Resources.bashBlue)

class Mod_ListDependent(OneItemLink):
    """Copies list of masters to clipboard."""
    _text = _(u"List Dependencies")

    def _initData(self, window, selection):
        super(Mod_ListDependent, self)._initData(window, selection)
        self.help = _(u"Displays and copies to the clipboard a list of mods "
                      u"that have %(filename)s as master.") % (
                        {'filename': selection[0]})
        self.legend = _(u'Mods dependent on %(filename)s') % (
                        {'filename': selection[0]})

    def Execute(self):
        ##: HACK - refactor getModList
        modInfos = self.window.data_store
        merged, imported = modInfos.merged, modInfos.imported
        head, bul = u'=== ', u'* '
        with bolt.sio() as out:
            log = bolt.LogFile(out)
            log(u'[spoiler][xml]')
            log.setHeader(head + self.legend + u': ')
            loOrder =  lambda tup: load_order.loIndexCachedOrMax(tup[0])
            text = u''
            for mod, info in sorted(modInfos.items(), key=loOrder):
                if self._selected_item in info.header.masters:
                    hexIndex = modInfos.hexIndexString(mod)
                    if hexIndex:
                        prefix = bul + hexIndex
                    elif mod in merged:
                        prefix = bul + u'++'
                    else:
                        prefix = bul + (u'**' if mod in imported else u'__')
                    text = u'%s  %s' % (prefix, mod.s,)
                    log(text)
            if not text:  log(u'None')
            log(u'[/xml][/spoiler]')
            text = bolt.winNewLines(log.out.getvalue())
        balt.copyToClipboard(text)
        self._showLog(text, title=self.legend, fixedFont=False,
                      icons=Resources.bashBlue)

class Mod_JumpToInstaller(AppendableLink, OneItemLink):
    """Go to the installers tab and highlight the mods installer"""
    _text = _(u"Jump to installer")

    def _initData(self, window, selection):
        super(Mod_JumpToInstaller, self)._initData(window, selection)
        self.help = _(u"Jump to the installer of %(filename)s if it exists") \
                    % ({'filename': selection[0]}) + u'. '
        self.help += _(u'You can Alt click on the mod to the same effect')
        self._installer = self.window.get_installer(self._selected_item)

    def _append(self, window): return balt.Link.Frame.iPanel and bass.settings[
        'bash.installers.enabled']

    def _enable(self):
        return super(Mod_JumpToInstaller, self)._enable() and \
               self._installer is not None # need a boolean here

    def Execute(self): self.window.jump_to_mods_installer(self._selected_item)

# Ghosting --------------------------------------------------------------------
#------------------------------------------------------------------------------
class _GhostLink(ItemLink):
    # usual case, toggle ghosting and ghost inactive if allowed after toggling
    @staticmethod
    def setAllow(filename): return not _GhostLink.getAllow(filename)
    @staticmethod
    def toGhost(filename): return _GhostLink.getAllow(filename) and \
        not load_order.isActiveCached(filename) # cannot ghost active mods
    @staticmethod
    def getAllow(filename):
        return bosh.modInfos.table.getItem(filename, 'allowGhosting', True)

    def _loop(self):
        """Loop selected files applying allow ghosting settings and
        (un)ghosting as needed."""
        files = []
        for fileName, fileInfo in self.iselected_pairs():
            bosh.modInfos.table.setItem(fileName, 'allowGhosting',
                                        self.__class__.setAllow(fileName))
            oldGhost = fileInfo.isGhost
            if fileInfo.setGhost(self.__class__.toGhost(fileName)) != oldGhost:
                files.append(fileName)
        return files

    def Execute(self):
        changed = self._loop()
        self.window.RefreshUI(redraw=changed, refreshSaves=False)

class _Mod_AllowGhosting_All(_GhostLink, ItemLink):
    _text, help = _(u"Allow Ghosting"), _(u'Allow Ghosting for selected mods')
    setAllow = staticmethod(lambda fname: True) # allow ghosting
    toGhost = staticmethod(lambda name: not load_order.isActiveCached(name))

#------------------------------------------------------------------------------
class _Mod_DisallowGhosting_All(_GhostLink, ItemLink):
    _text = _(u'Disallow Ghosting')
    help = _(u'Disallow Ghosting for selected mods')
    setAllow = staticmethod(lambda filename: False) # disallow ghosting...
    toGhost = staticmethod(lambda filename: False) # ...so unghost if ghosted

#------------------------------------------------------------------------------
class Mod_Ghost(_GhostLink, EnabledLink): ##: consider an unghost all Link
    setAllow = staticmethod(lambda fname: True) # allow ghosting
    toGhost = staticmethod(lambda name: not load_order.isActiveCached(name))

    def _initData(self, window, selection):
        super(Mod_Ghost, self)._initData(window, selection)
        if len(selection) == 1:
            self.help = _(u"Ghost/Unghost selected mod.  Active mods can't be ghosted")
            self.mname = selection[0]
            self.fileInfo = bosh.modInfos[self.mname]
            self.isGhost = self.fileInfo.isGhost
            self._text = _(u"Ghost") if not self.isGhost else _(u"Unghost")
        else:
            self.help = _(u"Ghost selected mods.  Active mods can't be ghosted")
            self._text = _(u"Ghost")

    def _enable(self):
        # only enable ghosting for one item if not active
        if len(self.selected) == 1 and not self.isGhost:
            return not load_order.isActiveCached(self.mname)
        return True

    def Execute(self):
        files = []
        if len(self.selected) == 1:
            # toggle - ghosting only enabled if plugin is inactive
            if not self.isGhost: # ghosting - override allowGhosting with True
                bosh.modInfos.table.setItem(self.mname, 'allowGhosting', True)
            self.fileInfo.setGhost(not self.isGhost)
            files.append(self.mname)
        else:
            files = self._loop()
        self.window.RefreshUI(redraw=files, refreshSaves=False)

#------------------------------------------------------------------------------
class _Mod_AllowGhostingInvert_All(_GhostLink, ItemLink):
    _text = _(u'Invert Ghosting')
    help = _(u'Invert Ghosting for selected mods')

#------------------------------------------------------------------------------
class Mod_AllowGhosting(TransLink):
    """Toggles Ghostability."""

    def _decide(self, window, selection):
        if len(selection) == 1:
            class _CheckLink(_GhostLink, CheckLink):
                _text = _(u"Disallow Ghosting")
                help = _(u"Toggle Ghostability")
                def _check(self): return not self.getAllow(self.selected[0])
            return _CheckLink()
        else:
            subMenu = balt.MenuLink(_(u"Ghosting"))
            subMenu.links.append(_Mod_AllowGhosting_All())
            subMenu.links.append(_Mod_DisallowGhosting_All())
            subMenu.links.append(_Mod_AllowGhostingInvert_All())
            return subMenu

# BP Links --------------------------------------------------------------------
#------------------------------------------------------------------------------
class Mod_MarkMergeable(ItemLink):
    """Returns true if can act as patch mod."""
    def __init__(self,doCBash):
        Link.__init__(self)
        self.doCBash = doCBash
        self._text = _(u'Mark Mergeable (CBash)...') if doCBash else _(
            u'Mark Mergeable...')
        self.help = _(u'Scans the selected plugin(s) to determine if they are '
                      u'mergeable into the %(patch_type)s bashed patch, '
                      u'reporting also the reason they are unmergeable') % {
                        'patch_type': _(u'Cbash') if doCBash else _(u'Python')}

    @balt.conversation
    def Execute(self):
        with balt.Progress(self._text + u' ' * 30) as prog:
            result, tagged_no_merge = bosh.modInfos.rescanMergeable(
                self.selected, prog, self.doCBash)
        yes = [x for x in self.selected if
               x not in tagged_no_merge and x in bosh.modInfos.mergeable]
        no = set(self.selected) - set(yes)
        no = [u"%s:%s" % (x, y) for x, y in result.iteritems() if x in no]
        message = u'== %s ' % ([u'Python', u'CBash'][self.doCBash]) + _(
            u'Mergeability') + u'\n\n'
        if yes:
            message += u'=== ' + _(u'Mergeable') + u'\n* ' + u'\n\n* '.join(
                x.s for x in yes)
        if yes and no:
            message += u'\n\n'
        if no:
            message += u'=== ' + _(u'Not Mergeable') + u'\n* ' + '\n\n* '.join(
                no)
        self.window.RefreshUI(redraw=self.selected, refreshSaves=False)
        if message != u'':
            self._showWryeLog(message, title=_(u'Mark Mergeable'),
                              icons=Resources.bashBlue)

#------------------------------------------------------------------------------
class _Mod_BP_Link(OneItemLink):
    """Enabled on Bashed patch items."""
    def _enable(self):
        return super(_Mod_BP_Link, self)._enable() and bosh.modInfos.isBP(
            self._selected_item)

class _Mod_Patch_Update(_Mod_BP_Link):
    """Updates a Bashed Patch."""
    def __init__(self,doCBash=False):
        super(_Mod_Patch_Update, self).__init__()
        self.doCBash = doCBash
        self.CBashMismatch = False
        self._text = _(u'Rebuild Patch (CBash *BETA*)...') if doCBash else _(
            u'Rebuild Patch...')
        self.help = _(u'Rebuild the Bashed Patch (CBash)') if doCBash else _(
                    u'Rebuild the Bashed Patch')

    def _initData(self, window, selection):
        super(_Mod_Patch_Update, self)._initData(window, selection)
        # Detect if the patch was build with Python or CBash
        config = bosh.modInfos.table.getItem(self._selected_item,
                                             'bash.patch.configs', {})
        thisIsCBash = configIsCBash(config)
        self.CBashMismatch = bool(thisIsCBash != self.doCBash)

    @balt.conversation
    def Execute(self):
        """Handle activation event."""
        try:
            if not self._Execute(): return # prevent settings save
        except CancelError:
            return # prevent settings save
        # save data to disc in case of later improper shutdown leaving the
        # user guessing as to what options they built the patch with
        Link.Frame.SaveSettings()

    def _Execute(self):
        # Clean up some memory
        bolt.GPathPurge()
        # We need active mods
        if not load_order.activeCached():
            self._showWarning(
                _(u'That which does not exist cannot be patched.') + u'\n' +
                _(u'Load some mods and try again.'),
                _(u'Existential Error'))
            return
        # Verify they want to build a previous Python patch in CBash mode, or vice versa
        if self.doCBash and not self._askContinue(_(
                u"Building with CBash is cool.  It's faster and allows more "
                u"things to be handled, but it is still in BETA.  If you "
                u"have problems, post them in the official thread, then use "
                u"the non-CBash build function."),
            'bash.patch.ReallyUseCBash.295.continue'):
            return
        importConfig = True
        msg = _(u"The patch you are rebuilding (%s) was created in %s "
                u"mode.  You are trying to rebuild it using %s mode.  Should "
                u"Wrye Bash attempt to import your settings (some may not be "
                u"copied correctly)?  Selecting 'No' will load the bashed"
                u" patch defaults.")
        if self.CBashMismatch:
            old_mode = [u'CBash', u'Python'][self.doCBash]
            new_mode = [u'Python', u'CBash'][self.doCBash]
            msg %= self._selected_item.s, old_mode, new_mode
            title = _(u'Import %s config ?') % old_mode
            if not self._askYes(msg, title=title): importConfig = False
        patch_files.executing_patch = self._selected_item
        mods_prior_to_patch = load_order.cached_lord.loadOrder[
                              :load_order.loIndexCached(self._selected_item)]
        if self.doCBash or bass.settings['bash.CBashEnabled']:
            # if doing a python patch but CBash is enabled, it's very likely
            # that the merge info currently is from a CBash mode scan, rescan
            prog = balt.Progress(_(u"Mark Mergeable") + u' ' * 30)
            with prog:
                bosh.modInfos.rescanMergeable(mods_prior_to_patch, prog,
                                              self.doCBash)
            self.window.RefreshUI(refreshSaves=False) # rescanned mergeable
        #--Check if we should be deactivating some plugins
        active_prior_to_patch = [x for x in mods_prior_to_patch if
                                 load_order.isActiveCached(x)]
        self._ask_deactivate_mergeable(active_prior_to_patch)
        previousMods = set()
        missing = collections.defaultdict(list)
        delinquent = collections.defaultdict(list)
        for mod in load_order.activeCached():
            if mod == self._selected_item: break
            for master in bosh.modInfos[mod].header.masters:
                if not load_order.isActiveCached(master):
                    missing[mod].append(master)
                elif master not in previousMods:
                    delinquent[mod].append(master)
            previousMods.add(mod)
        if missing or delinquent:
            proceed_ = _(u'WARNING!') + u'\n' + _(
                u'The following mod(s) have master file error(s).  Please '
                u'adjust your load order to rectify those problem(s) before '
                u'continuing.  However you can still proceed if you want to. '
                u' Proceed?')
            missingMsg = _(
                u'These mods have missing masters; which will make your game '
                u'unusable, and you will probably have to regenerate your '
                u'patch after fixing them.  So just go fix them now.')
            delinquentMsg = _(
                u'These mods have delinquent masters which will make your '
                u'game unusable and you quite possibly will have to '
                u'regenerate your patch after fixing them.  So just go fix '
                u'them now.')
            with ListBoxes(Link.Frame, _(u'Master Errors'), proceed_,[
                [_(u'Missing Master Errors'), missingMsg, missing],
                [_(u'Delinquent Master Errors'), delinquentMsg, delinquent]],
                liststyle='tree',bOk=_(u'Continue Despite Errors')) as warning:
                   if not warning.askOkModal(): return
        with PatchDialog(self.window, self._selected_info, self.doCBash,
                         importConfig) as patchDialog:
            patchDialog.ShowModal()
        return self._selected_item

    def _ask_deactivate_mergeable(self, active_prior_to_patch):
        unfiltered, merge, noMerge, deactivate = [], [], [], []
        for mod in active_prior_to_patch:
            tags = bosh.modInfos[mod].getBashTags()
            if u'Filter' in tags: unfiltered.append(mod)
            elif mod in bosh.modInfos.mergeable:
                if u'NoMerge' in tags: noMerge.append(mod)
                else: merge.append(mod)
            elif u'Deactivate' in tags: deactivate.append(mod)
        checklists = []
        unfilteredKey = _(u"Tagged 'Filter'")
        mergeKey = _(u"Mergeable")
        noMergeKey = _(u"Mergeable, but tagged 'NoMerge'")
        deactivateKey = _(u"Tagged 'Deactivate'")
        if unfiltered:
            group = [unfilteredKey, _(u"These mods should be deactivated "
                u"before building the patch, and then merged or imported into "
                u"the Bashed Patch."), ]
            group.extend(unfiltered)
            checklists.append(group)
        if merge:
            group = [mergeKey, _(u"These mods are mergeable.  "
                u"While it is not important to Wrye Bash functionality or "
                u"the end contents of the Bashed Patch, it is suggested that "
                u"they be deactivated and merged into the patch.  This helps "
                u"avoid the Oblivion maximum esp/esm limit."), ]
            group.extend(merge)
            checklists.append(group)
        if noMerge:
            group = [noMergeKey, _(u"These mods are mergeable, but tagged "
                u"'NoMerge'.  They should be deactivated before building the "
                u"patch and imported into the Bashed Patch."), ]
            group.extend(noMerge)
            checklists.append(group)
        if deactivate:
            group = [deactivateKey, _(u"These mods are tagged 'Deactivate'.  "
                u"They should be deactivated before building the patch, and "
                u"merged or imported into the Bashed Patch."), ]
            group.extend(deactivate)
            checklists.append(group)
        if not checklists: return
        with ListBoxes(Link.Frame,
            _(u"Deactivate these mods prior to patching"),
            _(u"The following mods should be deactivated prior to building "
              u"the patch."), checklists, bCancel=_(u'Skip')) as dialog:
            if not dialog.askOkModal(): return
            deselect = set()
            for (lst, key) in [(unfiltered, unfilteredKey),
                               (merge, mergeKey),
                               (noMerge, noMergeKey),
                               (deactivate, deactivateKey), ]:
                deselect |= set(dialog.getChecked(key, lst))
            if not deselect: return
        with balt.BusyCursor():
            bosh.modInfos.lo_deactivate(deselect, doSave=True)
        self.window.RefreshUI(refreshSaves=True)

class Mod_Patch_Update(TransLink, _Mod_Patch_Update):

    def _decide(self, window, selection):
        """Return a radio button if CBash is enabled a simple item
        otherwise."""
        enable = len(selection) == 1 and bosh.modInfos.isBP(selection[0])
        if enable and bass.settings['bash.CBashEnabled']:
            class _RadioLink(RadioLink, _Mod_Patch_Update):
                def _check(self): return not self.CBashMismatch
            return _RadioLink(self.doCBash)
        return _Mod_Patch_Update(self.doCBash)

#------------------------------------------------------------------------------
class Mod_ListPatchConfig(_Mod_BP_Link):
    """Lists the Bashed Patch configuration and copies to the clipboard."""
    _text = _(u'List Patch Config...')
    help = _(
        u'Lists the Bashed Patch configuration and copies it to the clipboard')

    def Execute(self):
        #--Patcher info
        groupOrder = dict([(group,index) for index,group in
            enumerate((_(u'General'),_(u'Importers'),
                       _(u'Tweakers'),_(u'Special')))])
        #--Config
        config = bosh.modInfos.table.getItem(self._selected_item,
                                             'bash.patch.configs', {})
        # Detect CBash/Python mode patch
        doCBash = configIsCBash(config)
        patchers = [copy.deepcopy(x) for x in
                    (CBash_gui_patchers if doCBash else PBash_gui_patchers)]
        patchers.sort(key=lambda a: a.__class__.name)
        patchers.sort(key=lambda a: groupOrder[a.__class__.group])
        #--Log & Clipboard text
        log = bolt.LogFile(StringIO.StringIO())
        log.setHeader(u'= %s %s' % (self._selected_item, _(u'Config')))
        log(_(u'This is the current configuration of this Bashed Patch.  This report has also been copied into your clipboard.')+u'\n')
        clip = StringIO.StringIO()
        clip.write(u'%s %s:\n' % (self._selected_item, _(u'Config')))
        clip.write(u'[spoiler][xml]\n')
        # CBash/Python patch?
        log.setHeader(u'== '+_(u'Patch Mode'))
        clip.write(u'== '+_(u'Patch Mode')+u'\n')
        if doCBash:
            if bass.settings['bash.CBashEnabled']:
                msg = u'CBash %s' % (CBashApi.VersionText,)
            else:
                # It's a CBash patch config, but CBash.dll is unavailable (either by -P command line, or it's not there)
                msg = u'CBash'
            log(msg)
            clip.write(u' ** %s\n' % msg)
        else:
            log(u'Python')
            clip.write(u' ** Python\n')
        for patcher in patchers:
            patcher.log_config(config, clip, log)
        #-- Show log
        clip.write(u'[/xml][/spoiler]')
        balt.copyToClipboard(clip.getvalue())
        clip.close()
        text = log.out.getvalue()
        log.out.close()
        self._showWryeLog(text, title=_(u'Bashed Patch Configuration'),
                          icons=Resources.bashBlue)

class Mod_ExportPatchConfig(_Mod_BP_Link):
    """Exports the Bashed Patch configuration to a Wrye Bash readable file."""
    _text = _(u'Export Patch Config...')
    help = _(
        u'Exports the Bashed Patch configuration to a Wrye Bash readable file')

    @balt.conversation
    def Execute(self):
        #--Config
        config = bosh.modInfos.table.getItem(self._selected_item,
                                             'bash.patch.configs', {})
        exportConfig(patch_name=self._selected_item.s, config=config,
                     isCBash=configIsCBash(config), win=self.window,
                     outDir=bass.dirs['patches'])

# Cleaning submenu ------------------------------------------------------------
#------------------------------------------------------------------------------
class _DirtyLink(ItemLink):
    def _ignoreDirty(self, filename): raise AbstractError

    def Execute(self):
        for fileName in self.selected:
            bosh.modInfos.table.setItem(fileName, 'ignoreDirty',
                                        self._ignoreDirty(fileName))
        self.window.RefreshUI(redraw=self.selected, refreshSaves=False)

class _Mod_SkipDirtyCheckAll(_DirtyLink, CheckLink):
    help = _(u"Set whether to check or not the selected mod(s) against LOOT's "
             u"dirty mod list")

    def __init__(self, bSkip):
        super(_Mod_SkipDirtyCheckAll, self).__init__()
        self.skip = bSkip
        self._text = _(
            u"Don't check against LOOT's dirty mod list") if self.skip else _(
            u"Check against LOOT's dirty mod list")

    def _check(self):
        for fileName in self.selected:
            if bosh.modInfos.table.getItem(fileName,
                    'ignoreDirty', self.skip) != self.skip: return False
        return True

    def _ignoreDirty(self, filename): return self.skip

class _Mod_SkipDirtyCheckInvert(_DirtyLink, ItemLink):
    _text = _(u"Invert checking against LOOT's dirty mod list")
    help = _(
        u"Invert checking against LOOT's dirty mod list for selected mod(s)")

    def _ignoreDirty(self, filename):
        return not bosh.modInfos.table.getItem(filename, 'ignoreDirty', False)

class Mod_SkipDirtyCheck(TransLink):
    """Toggles scanning for dirty mods on a per-mod basis."""

    def _decide(self, window, selection):
        if len(selection) == 1:
            class _CheckLink(_DirtyLink, CheckLink):
                _text = _(u"Don't check against LOOT's dirty mod list")
                help = _(u"Toggles scanning for dirty mods on a per-mod basis")

                def _check(self): return bosh.modInfos.table.getItem(
                        self.selected[0], 'ignoreDirty', False)
                def _ignoreDirty(self, filename): return self._check() ^ True

            return _CheckLink()
        else:
            subMenu = balt.MenuLink(_(u"Dirty edit scanning"))
            subMenu.links.append(_Mod_SkipDirtyCheckAll(True))
            subMenu.links.append(_Mod_SkipDirtyCheckAll(False))
            subMenu.links.append(_Mod_SkipDirtyCheckInvert())
            return subMenu

#------------------------------------------------------------------------------
class Mod_ScanDirty(ItemLink):
    """Give detailed printout of what Wrye Bash is detecting as UDR and ITM
    records"""
    help = _(u'Give detailed printout of what Wrye Bash is detecting as UDR'
             u' and ITM records')

    def _initData(self, window, selection):
        super(Mod_ScanDirty, self)._initData(window, selection)
        # settings['bash.CBashEnabled'] is set once in BashApp.Init() AFTER
        # InitLinks() is called in bash.py
        self._text = _(u'Scan for Dirty Edits') if bass.settings[
            'bash.CBashEnabled'] else _(u"Scan for UDR's")

    def Execute(self):
        """Handle execution"""
        modInfos = [x for x in self.iselected_infos()]
        try:
            with balt.Progress(_(u'Dirty Edits'),u'\n'+u' '*60,abort=True) as progress:
                ret = bosh.mods_metadata.ModCleaner.scan_Many(modInfos, progress=progress, detailed=True)
        except bolt.CancelError:
            return
        log = bolt.LogFile(StringIO.StringIO())
        log.setHeader(u'= '+_(u'Scan Mods'))
        log(_(u'This is a report of records that were detected as either Identical To Master (ITM) or a deleted reference (UDR).')
            + u'\n')
        # Change a FID to something more usefull for displaying
        if bass.settings['bash.CBashEnabled']:
            def strFid(fid):
                return u'%s: %06X' % (fid[0],fid[1])
        else:
            def strFid(fid):
                modId = (0xFF000000 & fid) >> 24
                modName = modInfo.masterNames[modId]
                id_ = 0x00FFFFFF & fid
                return u'%s: %06X' % (modName,id_)
        dirty = []
        clean = []
        error = []
        for i,modInfo in enumerate(modInfos):
            udrs,itms,fog = ret[i]
            if modInfo.name == GPath(u'Unofficial Oblivion Patch.esp'):
                # Record for non-SI users, shows up as ITM if SI is installed (OK)
                if bass.settings['bash.CBashEnabled']:
                    itms.discard(FormID(GPath(u'Oblivion.esm'),0x00AA3C))
                else:
                    itms.discard((GPath(u'Oblivion.esm'),0x00AA3C))
            if modInfo.header.author in (u'BASHED PATCH',u'BASHED LISTS'): itms = set()
            if udrs or itms:
                pos = len(dirty)
                dirty.append(u'* __'+modInfo.name.s+u'__:\n')
                dirty[pos] += u'  * %s: %i\n' % (_(u'UDR'),len(udrs))
                for udr in sorted(udrs):
                    if udr.parentEid:
                        parentStr = u"%s '%s'" % (strFid(udr.parentFid),udr.parentEid)
                    else:
                        parentStr = strFid(udr.parentFid)
                    if udr.parentType == 0:
                        # Interior CELL
                        item = u'%s -  %s attached to Interior CELL (%s)' % (
                            strFid(udr.fid),udr.type,parentStr)
                    else:
                        # Exterior CELL
                        if udr.parentParentEid:
                            parentParentStr = u"%s '%s'" % (strFid(udr.parentParentFid),udr.parentParentEid)
                        else:
                            parentParentStr = strFid(udr.parentParentFid)
                        if udr.pos is None:
                            atPos = u''
                        else:
                            atPos = u' at %s' % (udr.pos,)
                        item = u'%s - %s attached to Exterior CELL (%s), attached to WRLD (%s)%s' % (
                            strFid(udr.fid),udr.type,parentStr,parentParentStr,atPos)
                    dirty[pos] += u'    * %s\n' % item
                if not bass.settings['bash.CBashEnabled']: continue
                if itms:
                    dirty[pos] += u'  * %s: %i\n' % (_(u'ITM'),len(itms))
                for fid in sorted(itms):
                    dirty[pos] += u'    * %s\n' % strFid(fid)
            elif udrs is None or itms is None:
                error.append(u'* __'+modInfo.name.s+u'__')
            else:
                clean.append(u'* __'+modInfo.name.s+u'__')
        #-- Show log
        if dirty:
            log(_(u'Detected %d dirty mods:') % len(dirty))
            for mod in dirty: log(mod)
            log(u'\n')
        if clean:
            log(_(u'Detected %d clean mods:') % len(clean))
            for mod in clean: log(mod)
            log(u'\n')
        if error:
            log(_(u'The following %d mods had errors while scanning:') % len(error))
            for mod in error: log(mod)
        self._showWryeLog(log.out.getvalue(),
                          title=_(u'Dirty Edit Scan Results'), asDialog=False,
                          icons=Resources.bashBlue)
        log.out.close()

#------------------------------------------------------------------------------
class Mod_RemoveWorldOrphans(EnabledLink):
    """Remove orphaned cell records."""
    _text = _(u'Remove World Orphans')
    help = _(u'Remove orphaned cell records')

    def _enable(self):
        return len(self.selected) != 1 or (
            not bosh.reOblivion.match(self.selected[0].s))

    def Execute(self):
        message = _(u"In some circumstances, editing a mod will leave orphaned cell records in the world group. This command will remove such orphans.")
        if not self._askContinue(message, 'bash.removeWorldOrphans.continue',
                                 _(u'Remove World Orphans')): return
        for index, (fileName, fileInfo) in enumerate(self.iselected_pairs()):
            if bosh.reOblivion.match(fileName.s):
                self._showWarning(_(u"Skipping %s") % fileName.s,
                                  _(u'Remove World Orphans'))
                continue
            #--Export
            with balt.Progress(_(u"Remove World Orphans")) as progress:
                loadFactory = parsers.LoadFactory(True,
                        bosh.MreRecord.type_class['CELL'],
                        bosh.MreRecord.type_class['WRLD'])
                modFile = parsers.ModFile(fileInfo, loadFactory)
                progress(0,_(u'Reading') + u' ' + fileName.s + u'.')
                modFile.load(True,SubProgress(progress,0,0.7))
                orphans = ('WRLD' in modFile.tops) and modFile.WRLD.orphansSkipped
                if orphans:
                    progress(0.1,_(u"Saving %s.") % fileName.s)
                    modFile.safeSave()
                progress(1.0,_(u"Done."))
            #--Log
            if orphans:
                self._showOk(_(u"Orphan cell blocks removed: %d.") % orphans,
                             fileName.s)
            else:
                self._showOk(_(u"No changes required."), fileName.s)

#------------------------------------------------------------------------------
class Mod_FogFixer(ItemLink):
    """Fix fog on selected cells."""
    _text = _(u'Nvidia Fog Fix')
    help = _(u'Modify fog values in interior cells to avoid the Nvidia black '
             u'screen bug')

    def Execute(self):
        message = _(u'Apply Nvidia fog fix.  This modify fog values in interior cells to avoid the Nvidia black screen bug.')
        if not self._askContinue(message, 'bash.cleanMod.continue',
                                 _(u'Nvidia Fog Fix')): return
        with balt.Progress(_(u'Nvidia Fog Fix')) as progress:
            progress.setFull(len(self.selected))
            fixed = []
            for index,(fileName,fileInfo) in enumerate(self.iselected_pairs()):
                if fileName.cs in bush.game.masterFiles: continue
                progress(index,_(u'Scanning')+fileName.s)
                fog_fixer = bosh.mods_metadata.NvidiaFogFixer(fileInfo)
                fog_fixer.fix_fog(SubProgress(progress, index, index + 1))
                if fog_fixer.fixedCells:
                    fixed.append(
                        u'* %4d %s' % (len(fog_fixer.fixedCells), fileName.s))
        if fixed:
            message = u'==='+_(u'Cells Fixed')+u':\n'+u'\n'.join(fixed)
            self._showWryeLog(message, title=_(u'Nvidia Fog Fix'),
                              icons=Resources.bashBlue)
        else:
            message = _(u'No changes required.')
            self._showOk(message)

#------------------------------------------------------------------------------
class Mod_UndeleteRefs(EnabledLink):
    """Undeletes refs in cells."""
    _text = _(u'Undelete Refs')
    help = _(u'Undeletes refs in cells')
    warn = _(u"Changes deleted refs to ignored.  This is a very advanced "
             u"feature and should only be used by modders who know exactly "
             u"what they're doing.")

    def _enable(self):
        return len(self.selected) != 1 or (
            not bosh.reOblivion.match(self.selected[0].s))

    def Execute(self):
        if not self._askContinue(self.warn, 'bash.undeleteRefs.continue',
                                 self._text): return
        with balt.Progress(self._text) as progress:
            progress.setFull(len(self.selected))
            hasFixed = False
            log = bolt.LogFile(StringIO.StringIO())
            for index,(fileName,fileInfo) in enumerate(self.iselected_pairs()):
                if bosh.reOblivion.match(fileName.s):
                    self._showWarning(_(u'Skipping') + u' ' + fileName.s,
                                      self._text)
                    continue
                progress(index,_(u'Scanning')+u' '+fileName.s+u'.')
                cleaner = bosh.mods_metadata.ModCleaner(fileInfo)
                cleaner.clean(bosh.mods_metadata.ModCleaner.UDR,
                              SubProgress(progress, index, index + 1))
                if cleaner.udr:
                    hasFixed = True
                    log.setHeader(u'== '+fileName.s)
                    for fid in sorted(cleaner.udr):
                        log(u'. %08X' % fid)
        if hasFixed:
            message = log.out.getvalue()
        else:
            message = _(u"No changes required.")
        self._showWryeLog(message, title=self._text, icons=Resources.bashBlue)
        log.out.close()

# Rest of menu Links ----------------------------------------------------------
#------------------------------------------------------------------------------
class Mod_AddMaster(OneItemLink):
    """Adds master."""
    _text = _(u'Add Master...')

    def Execute(self):
        message = _(u"WARNING! For advanced modders only! Adds specified "
                    u"master to list of masters, thus ceding ownership of "
                    u"new content of this mod to the new master. Useful for "
                    u"splitting mods into esm/esp pairs.")
        if not self._askContinue(message, 'bash.addMaster.continue',
                                 _(u'Add Master')): return
        wildcard = _(u'%s Masters') % bush.game.displayName + \
                   u' (*.esm;*.esp)|*.esm;*.esp'
        masterPaths = self._askOpenMulti(title=_(u'Add master:'),
                                         defaultDir=self._selected_info.dir,
                                         wildcard=wildcard)
        if not masterPaths: return
        names = []
        for masterPath in masterPaths:
            (dir_,name) = masterPath.headTail
            if dir_ != self._selected_info.dir:
                return self._showError(_(
                    u"File must be selected from %s Data Files directory.")
                                       % bush.game.fsName)
            if name in self._selected_info.header.masters:
                return self._showError(_(u"%s is already a master!") % name.s)
            names.append(name)
        # actually do the modification
        for masters_name in load_order.get_ordered(names):
            if masters_name in bosh.modInfos:
                #--Avoid capitalization errors by getting the actual name from modinfos.
                masters_name = bosh.modInfos[masters_name].name
            self._selected_info.header.masters.append(masters_name)
        self._selected_info.header.changed = True
        self._selected_info.writeHeader()
        bosh.modInfos.refreshFile(self._selected_item)
        self.window.RefreshUI(refreshSaves=False) # why refreshing saves ?

#------------------------------------------------------------------------------
class Mod_CopyToEsmp(EnabledLink):
    """Create an esp(esm) copy of selected esm(esp)."""

    def _initData(self, window, selection):
        super(Mod_CopyToEsmp, self)._initData(window, selection)
        fileInfo = bosh.modInfos[selection[0]]
        self._is_esm = fileInfo.isEsm()
        self._text = _(u'Copy to Esp') if self._is_esm else _(u'Copy to Esm')

    def _enable(self):
        """Disable if selected are mixed esm/p's or inverted mods."""
        for fileInfo in self.iselected_infos():
            if fileInfo.isInvertedMod() or fileInfo.isEsm() != self._is_esm:
                return False
        return True

    def Execute(self):
        modInfos, added = bosh.modInfos, []
        save_lo = False
        for curName, fileInfo in ((x, modInfos[x]) for x in self.selected):
            newType = (fileInfo.isEsm() and u'esp') or u'esm'
            newName = curName.root + u'.' + newType # calls GPath internally
            #--Replace existing file?
            timeSource = None
            if newName in modInfos:
                existing = modInfos[newName]
                if not self._askYes(_( # getPath() as existing may be ghosted
                        u'Replace existing %s?') % existing.getPath()):
                    continue
                existing.makeBackup()
                timeSource = newName
            #--New Time
            newTime = modInfos[timeSource].mtime if timeSource else None
            #--Copy, set type, update mtime - will use ghosted path if needed
            modInfos.copy_info(curName, fileInfo.dir, newName,
                               set_mtime=newTime)
            added.append(newName)
            newInfo = modInfos[newName]
            newInfo.setType(newType)
            if timeSource is None: # otherwise it has a load order already !
                modInfos.cached_lo_insert_after(modInfos.cached_lo_last_esm(),
                                                newName)
                save_lo = True
        #--Repopulate
        if added:
            if save_lo: modInfos.cached_lo_save_lo()
            modInfos.refresh(refresh_infos=False)
            self.window.RefreshUI(refreshSaves=True, # just in case
                                  detail_item=added[-1])
            self.window.SelectItemsNoCallback(added)

#------------------------------------------------------------------------------
class Mod_DecompileAll(EnabledLink):
    """Removes effects of a "recompile all" on the mod."""
    _text = _(u'Decompile All')
    help = _(u'Removes effects of a "recompile all" on the mod')

    def _enable(self):
        return len(self.selected) != 1 or (
        not bosh.reOblivion.match(self.selected[0].s)) # disable on Oblivion.esm

    def Execute(self):
        message = _(u"This command will remove the effects of a 'compile all' by removing all scripts whose texts appear to be identical to the version that they override.")
        if not self._askContinue(message, 'bash.decompileAll.continue',
                                 _(u'Decompile All')): return
        for fileName, fileInfo in self.iselected_pairs():
            if bosh.reOblivion.match(fileName.s):
                self._showWarning(_(u"Skipping %s") % fileName.s,
                                  _(u'Decompile All'))
                continue
            loadFactory = parsers.LoadFactory(True, bosh.MreRecord.type_class['SCPT'])
            modFile = parsers.ModFile(fileInfo, loadFactory)
            modFile.load(True)
            badGenericLore = False
            removed = []
            id_text = {}
            if modFile.SCPT.getNumRecords(False):
                loadFactory = parsers.LoadFactory(False, bosh.MreRecord.type_class['SCPT'])
                for master in modFile.tes4.masters:
                    masterFile = parsers.ModFile(bosh.modInfos[master], loadFactory)
                    masterFile.load(True)
                    mapper = masterFile.getLongMapper()
                    for record in masterFile.SCPT.getActiveRecords():
                        id_text[mapper(record.fid)] = record.scriptText
                mapper = modFile.getLongMapper()
                newRecords = []
                for record in modFile.SCPT.records:
                    fid = mapper(record.fid)
                    #--Special handling for genericLoreScript
                    if (fid in id_text and record.fid == 0x00025811 and
                        record.compiledSize == 4 and record.lastIndex == 0):
                        removed.append(record.eid)
                        badGenericLore = True
                    elif fid in id_text and id_text[fid] == record.scriptText:
                        removed.append(record.eid)
                    else:
                        newRecords.append(record)
                modFile.SCPT.records = newRecords
                modFile.SCPT.setChanged()
            if len(removed) >= 50 or badGenericLore:
                modFile.safeSave()
                self._showOk((_(u'Scripts removed: %d.') + u'\n' +
                              _(u'Scripts remaining: %d')) %
                             (len(removed), len(modFile.SCPT.records)),
                             fileName.s)
            elif removed:
                self._showOk(_(u"Only %d scripts were identical.  This is "
                               u"probably intentional, so no changes have "
                               u"been made.") % len(removed),fileName.s)
            else:
                self._showOk(_(u"No changes required."), fileName.s)

#------------------------------------------------------------------------------
class _Esm_Flip(EnabledLink):

    def _esm_flip_refresh(self, espify, updated):
        with balt.BusyCursor():
            ##: HACK: forcing active refresh cause mods may be reordered and
            # we then need to sync order in skyrim's plugins.txt
            bosh.modInfos.refreshLoadOrder(forceRefresh=True, forceActive=True)
            if espify: # converted to esps - rescan mergeable
                bosh.modInfos.rescanMergeable(updated, bolt.Progress())
            # will be moved to the top - note that modification times won't
            # change - so mods will revert to their original position once back
            # to esp from esm (Oblivion etc). Refresh saves due to esms move
        self.window.RefreshUI(redraw=updated, refreshSaves=True)

class Mod_FlipSelf(_Esm_Flip):
    """Flip an esp(esm) to an esm(esp)."""

    def _initData(self, window, selection):
        super(Mod_FlipSelf, self)._initData(window, selection)
        fileInfo = bosh.modInfos[selection[0]]
        self.isEsm = fileInfo.isEsm()
        self._text = _(u'Espify Self') if self.isEsm else _(u'Esmify Self')

    def _enable(self):
        for item, fileInfo in self.iselected_pairs():
            if fileInfo.isEsm() != self.isEsm or not item.cext[-1] == u'p':
                return False
        return True

    @balt.conversation
    def Execute(self):
        message = (_(u'WARNING! For advanced modders only!')
                   + u'\n\n' +
                   _(u'This command flips an internal bit in the mod, converting an esp to an esm and vice versa.  Note that it is this bit and NOT the file extension that determines the esp/esm state of the mod.')
                   )
        if not self._askContinue(message, 'bash.flipToEsmp.continue',
                                 _(u'Flip to Esm')): return
        for fileInfo in self.iselected_infos():
            header = fileInfo.header
            header.flags1.esm = not header.flags1.esm
            fileInfo.writeHeader()
        self._esm_flip_refresh(self.isEsm, self.selected)

#------------------------------------------------------------------------------
class Mod_FlipMasters(OneItemLink, _Esm_Flip):
    """Swaps masters between esp and esm versions."""
    help = _(
        u"Flip esp/esm bit of esp masters to convert them to/from esm state")

    def _initData(self, window, selection):
        super(Mod_FlipMasters, self)._initData(window, selection)
        self._text = _(u'Esmify Masters')
        masters = self._selected_info.header.masters
        enable = len(selection) == 1 and len(masters) > 1
        self.espMasters = [master for master in masters
            if bosh.reEspExt.search(master.s)] if enable else []
        self.enable = enable and bool(self.espMasters)
        if not self.enable: return
        for masterName in self.espMasters:
            masterInfo = bosh.modInfos.get(masterName, None)
            if masterInfo and masterInfo.isInvertedMod():
                self._text = _(u'Espify Masters')
                self.toEsm = False
                break
        else:
            self.toEsm = True

    def _enable(self): return self.enable

    @balt.conversation
    def Execute(self):
        message = _(u"WARNING! For advanced modders only! Flips esp/esm bit of"
                    u" esp masters to convert them to/from esm state. Useful"
                    u" for building/analyzing esp mastered mods.")
        if not self._askContinue(message, 'bash.flipMasters.continue'): return
        updated = [self._selected_item]
        for masterPath in self.espMasters:
            masterInfo = bosh.modInfos.get(masterPath,None)
            if masterInfo:
                masterInfo.header.flags1.esm = self.toEsm
                masterInfo.writeHeader()
                updated.append(masterPath)
        self._esm_flip_refresh(not self.toEsm, updated)

#------------------------------------------------------------------------------
class Mod_SetVersion(OneItemLink):
    """Sets version of file back to 0.8."""
    _text = _(u'Version 0.8')
    help = _(u'Sets version of file back to 0.8')
    message = _(u"WARNING! For advanced modders only! This feature allows you "
        u"to edit newer official mods in the TES Construction Set by resetting"
        u" the internal file version number back to 0.8. While this will make "
        u"the mod editable, it may also break the mod in some way.")

    def _enable(self):
        return (super(Mod_SetVersion, self)._enable() and
                int(10 * self._selected_info.header.version) != 8)

    def Execute(self):
        if not self._askContinue(self.message, 'bash.setModVersion.continue',
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
from ..parsers import FidReplacer, CBash_FidReplacer

class Mod_Fids_Replace(OneItemLink):
    """Replace fids according to text file."""
    _text = _(u'Form IDs...')
    help = _(u'Replace fids according to text file')
    message = _(u"For advanced modders only! Systematically replaces one set "
        u"of Form Ids with another in npcs, creatures, containers and leveled "
        u"lists according to a Replacers.csv file.")

    @staticmethod
    def _parser():
        return CBash_FidReplacer() if CBashApi.Enabled else FidReplacer()

    def Execute(self):
        if not self._askContinue(self.message, 'bash.formIds.replace.continue',
                                 _(u'Import Form IDs')): return
        textDir = bass.dirs['patches']
        #--File dialog
        textPath = self._askOpen(_(u'Form ID mapper file:'),textDir,
            u'', u'*_Formids.csv',mustExist=True)
        if not textPath: return
        (textDir,textName) = textPath.headTail
        #--Extension error check
        if textName.cext != u'.csv':
            self._showError(_(u'Source file must be a csv file.'))
            return
        #--Export
        with balt.Progress(_(u"Import Form IDs")) as progress:
            replacer = self._parser()
            progress(0.1,_(u'Reading') + u' ' + textName.s + u'.')
            replacer.readFromText(textPath)
            progress(0.2, _(u'Applying to') +u' ' +self._selected_item.s +u'.')
            changed = replacer.updateMod(self._selected_info)
            progress(1.0,_(u'Done.'))
        #--Log
        if not changed: self._showOk(_(u"No changes required."))
        else: self._showLog(changed, title=_(u'Objects Changed'),
                            asDialog=True, icons=Resources.bashBlue)

class Mod_Face_Import(OneItemLink):
    """Imports a face from a save to an esp."""
    _text = _(u'Face...')

    def Execute(self):
        #--Select source face file
        srcDir = bosh.saveInfos.store_dir
        wildcard = _(u'%s Files')%bush.game.displayName+u' (*.ess;*.esr)|*.ess;*.esr'
        #--File dialog
        srcPath = self._askOpen(_(u'Face Source:'), defaultDir=srcDir,
                                wildcard=wildcard, mustExist=True)
        if not srcPath: return
        #--Get face
        srcDir,srcName = srcPath.headTail
        srcInfo = bosh.SaveInfo(srcDir,srcName)
        srcFace = bosh.faces.PCFaces.save_getPlayerFace(srcInfo)
        #--Save Face
        npc = bosh.faces.PCFaces.mod_addFace(self._selected_info, srcFace)
        #--Save Face picture? # FIXME(ut) does not save face picture but save screen ?!
        imagePath = bosh.modInfos.store_dir.join(u'Docs', u'Images', npc.eid + u'.jpg')
        if not imagePath.exists():
            srcInfo.readHeader()
            width,height,data = srcInfo.header.image
            image = Image.GetImage(data, height, width)
            imagePath.head.makedirs()
            image.SaveFile(imagePath.s,JPEG)
        self.window.RefreshUI(refreshSaves=False) # import save to esp
        self._showOk(_(u'Imported face to: %s') % npc.eid,
                     self._selected_item.s)

#--Common
class _Mod_Export_Link(ItemLink):

    def Execute(self):
        textName = self.selected[0].root + self.__class__.csvFile
        textDir = bass.dirs['patches']
        textDir.makedirs()
        #--File dialog
        textPath = self._askSave(title=self.__class__.askTitle,
                                 defaultDir=textDir, defaultFile=textName,
                                 wildcard=u'*' + self.__class__.csvFile)
        if not textPath: return
        (textDir, textName) = textPath.headTail
        #--Export
        with balt.Progress(self.__class__.progressTitle) as progress:
            parser = self._parser()
            readProgress = SubProgress(progress, 0.1, 0.8)
            readProgress.setFull(len(self.selected))
            for index,(fileName,fileInfo) in enumerate(self.iselected_pairs()):
                readProgress(index, _(u'Reading') + u' ' + fileName.s + u'.')
                parser.readFromMod(fileInfo)
            progress(0.8, _(u'Exporting to') + u' ' + textName.s + u'.')
            parser.writeToText(textPath)
            progress(1.0, _(u'Done.'))

    def _parser(self): raise AbstractError

class _Mod_Import_Link(OneItemLink):
    noChange = _(u"No changes required.")
    supportedExts = {u'.csv'}
    progressTitle = continueInfo = continueKey = 'OVERRIDE'

    def _parser(self): raise AbstractError
    @property
    def _wildcard(self):
        if len(self.supportedExts) == 1: return u'*' + self.__class__.csvFile
        return _(u'Mod/Text File') + u'|*' + self.__class__.csvFile + \
               u';*.esp;*.esm;*.ghost'

    def _import(self, ext, textDir, textName, textPath):
        with balt.Progress(self.__class__.progressTitle) as progress:
            parser = self._parser()
            progress(0.1, _(u'Reading') + u' ' + textName.s + u'.')
            if ext == u'.csv':
                parser.readFromText(textPath)
            else:
                srcInfo = bosh.ModInfo(textDir, textName)
                parser.readFromMod(srcInfo)
            progress(0.2, _(u'Applying to') +u' ' +self._selected_item.s +u'.')
            changed = parser.writeToMod(self._selected_info)
            progress(1.0, _(u'Done.'))
        return changed

    def _showLog(self, logText, title=u'', asDialog=True, fixedFont=False,
                 icons=Resources.bashBlue, size=True):
        super(_Mod_Import_Link, self)._showLog(logText,
            title=title or self.__class__.progressTitle, asDialog=asDialog,
            fixedFont=fixedFont, icons=icons, size=size)

    def _log(self, changed, fileName):
        with bolt.sio() as buff:
            buff.write(u'* %03d  %s\n' % (changed, fileName.s))
            text = buff.getvalue()
            self._showLog(text)

    def show_change_log(self, changed, fileName):
        if not changed:
            self._showOk(self.__class__.noChange, self.__class__.progressTitle)
        else:
            self._log(changed, fileName)

    def Execute(self):
        if not self._askContinueImport(): return
        supportedExts = self.__class__.supportedExts
        textName = self._selected_item.root + self.__class__.csvFile
        textDir = bass.dirs['patches']
        #--File dialog
        textPath = self._askOpen(self.__class__.askTitle, textDir, textName,
                                 self._wildcard, mustExist=True)
        if not textPath: return
        (textDir, textName) = textPath.headTail
        #--Extension error check
        ext = textName.cext
        if ext not in supportedExts:
            self._showError(_(u'Source file must be a {0} file{1}.'.format(
                self.__class__.csvFile, (len(supportedExts) > 1 and
                    u" or mod (.esp or .esm or .ghost)") or u"")))
            return
        #--Import
        changed = self._import(ext, textDir, textName, textPath)
        #--Log
        self.show_change_log(changed, self._selected_item)

    def _askContinueImport(self):
        return self._askContinue(self.__class__.continueInfo,
            self.__class__.continueKey, self.__class__.progressTitle)

#--Links ----------------------------------------------------------------------
from ..parsers import ActorLevels, CBash_ActorLevels

class Mod_ActorLevels_Export(_Mod_Export_Link):
    """Export actor levels from mod to text file."""
    askTitle = _(u'Export NPC levels to:')
    csvFile = u'_NPC_Levels.csv'
    progressTitle = _(u'Export NPC levels')
    _text = _(u'NPC Levels...')
    help = _(u"Export NPC level info from mod to text file.")

    def _parser(self):
        return CBash_ActorLevels() if CBashApi.Enabled else ActorLevels()

    def Execute(self): # overrides _Mod_Export_Link
        message = (_(u'This command will export the level info for NPCs whose level is offset with respect to the PC.  The exported file can be edited with most spreadsheet programs and then reimported.')
                   + u'\n\n' +
                   _(u'See the Bash help file for more info.'))
        if not self._askContinue(message, 'bash.actorLevels.export.continue',
                                 _(u'Export NPC Levels')): return
        super(Mod_ActorLevels_Export, self).Execute()

class Mod_ActorLevels_Import(_Mod_Import_Link):
    """Imports actor levels from text file to mod."""
    askTitle = _(u'Import NPC levels from:')
    csvFile = u'_NPC_Levels.csv'
    progressTitle = _(u'Import NPC Levels')
    _text = _(u'NPC Levels...')
    help = _(u"Import NPC level info from text file to mod")
    continueInfo = _(
        u'This command will import NPC level info from a previously exported '
        u'file.') + u'\n\n' + _(u'See the Bash help file for more info.')
    continueKey = 'bash.actorLevels.import.continue'
    noChange = _(u'No relevant NPC levels to import.')

    def _parser(self):
        return CBash_ActorLevels() if CBashApi.Enabled else ActorLevels()

#------------------------------------------------------------------------------
from ..parsers import FactionRelations, CBash_FactionRelations

class Mod_FactionRelations_Export(_Mod_Export_Link):
    """Export faction relations from mod to text file."""
    askTitle = _(u'Export faction relations to:')
    csvFile = u'_Relations.csv'
    progressTitle = _(u'Export Relations')
    _text = _(u'Relations...')
    help = _(u'Export faction relations from mod to text file')

    def _parser(self):
        return CBash_FactionRelations() if CBashApi.Enabled else \
            FactionRelations()

class Mod_FactionRelations_Import(_Mod_Import_Link):
    """Imports faction relations from text file to mod."""
    askTitle = _(u'Import faction relations from:')
    csvFile = u'_Relations.csv'
    progressTitle = _(u'Import Relations')
    _text = _(u'Relations...')
    help = _(u'Import faction relations from text file to mod')
    continueInfo = _(
        u"This command will import faction relation info from a previously "
        u"exported file.") + u'\n\n' + _(
        u"See the Bash help file for more info.")
    continueKey = 'bash.factionRelations.import.continue'
    noChange = _(u'No relevant faction relations to import.')

    def _parser(self):
        return CBash_FactionRelations() if CBashApi.Enabled else \
            FactionRelations()

#------------------------------------------------------------------------------
from ..parsers import ActorFactions, CBash_ActorFactions

class Mod_Factions_Export(_Mod_Export_Link):
    """Export factions from mod to text file."""
    askTitle = _(u'Export factions to:')
    csvFile = u'_Factions.csv'
    progressTitle = _(u'Export Factions')
    _text = _(u'Factions...')
    help = _(u'Export factions from mod to text file')

    def _parser(self):
        return CBash_ActorFactions() if CBashApi.Enabled else ActorFactions()

class Mod_Factions_Import(_Mod_Import_Link):
    """Imports factions from text file to mod."""
    askTitle = _(u'Import Factions from:')
    csvFile = u'_Factions.csv'
    progressTitle = _(u'Import Factions')
    _text = _(u'Factions...')
    help = _(u'Import factions from text file to mod')
    continueInfo = _(
        u"This command will import faction ranks from a previously exported "
        u"file.") + u'\n\n' + _(u'See the Bash help file for more info.')
    continueKey = 'bash.factionRanks.import.continue'
    noChange = _(u'No relevant faction ranks to import.')

    def _parser(self):
        return CBash_ActorFactions() if CBashApi.Enabled else ActorFactions()

    def _log(self, changed, fileName):
         with bolt.sio() as buff:
            for groupName in sorted(changed):
                buff.write(u'* %s : %03d  %s\n' % (
                    groupName, changed[groupName], fileName.s))
            self._showLog(buff.getvalue())

#------------------------------------------------------------------------------
from ..parsers import ScriptText, CBash_ScriptText

class Mod_Scripts_Export(_Mod_Export_Link):
    """Export scripts from mod to text file."""
    _text = _(u'Scripts...')
    help = _(u'Export scripts from mod to text file')

    def _parser(self):
        return CBash_ScriptText() if CBashApi.Enabled else ScriptText()

    def Execute(self): # overrides _Mod_Export_Link
        fileName, fileInfo = next(self.iselected_pairs()) # first selected pair
        defaultPath = bass.dirs['patches'].join(fileName.s + u' Exported Scripts')
        def OnOk():
            dialog.EndModal(1)
            bass.settings['bash.mods.export.deprefix'] = gdeprefix.GetValue().strip()
            bass.settings['bash.mods.export.skip'] = gskip.GetValue().strip()
            bass.settings['bash.mods.export.skipcomments'] = gskipcomments.GetValue()
        dialog = balt.Dialog(Link.Frame, _(u'Export Scripts Options'),
                             size=(400, 180), resize=False)
        okButton = OkButton(dialog, onButClick=OnOk)
        gskip = TextCtrl(dialog)
        gdeprefix = TextCtrl(dialog)
        gskipcomments = toggleButton(dialog, _(u'Filter Out Comments'),
            toggle_tip=_(u"If active doesn't export comments in the scripts"))
        gskip.SetValue(bass.settings['bash.mods.export.skip'])
        gdeprefix.SetValue(bass.settings['bash.mods.export.deprefix'])
        gskipcomments.SetValue(bass.settings['bash.mods.export.skipcomments'])
        sizer = vSizer(
            StaticText(dialog,_(u"Skip prefix (leave blank to not skip any), non-case sensitive):"),noAutoResize=True),
            gskip,
            hspacer,
            StaticText(dialog,(_(u'Remove prefix from file names i.e. enter cob to save script cobDenockInit')
                               + u'\n' +
                               _(u'as DenockInit.ext rather than as cobDenockInit.ext')
                               + u'\n' +
                               _(u'(Leave blank to not cut any prefix, non-case sensitive):')
                               ),noAutoResize=True),
            gdeprefix,
            hspacer,
            gskipcomments,
            balt.ok_and_cancel_sizer(dialog, okButton=okButton),
            )
        dialog.SetSizer(sizer)
        with dialog: questions = dialog.ShowModal()
        if questions != 1: return #because for some reason cancel/close dialogue is returning 5101!
        if not defaultPath.exists():
            defaultPath.makedirs()
        textDir = self._askDirectory(
            message=_(u'Choose directory to export scripts to'),
            defaultPath=defaultPath)
        if textDir != defaultPath:
            for asDir,sDirs,sFiles in os.walk(defaultPath.s):
                if not (sDirs or sFiles):
                    defaultPath.removedirs()
        if not textDir: return
        #--Export
        #try:
        scriptText = self._parser()
        scriptText.readFromMod(fileInfo,fileName.s)
        exportedScripts = scriptText.writeToText(fileInfo,bass.settings['bash.mods.export.skip'],textDir,bass.settings['bash.mods.export.deprefix'],fileName.s,bass.settings['bash.mods.export.skipcomments'])
        #finally:
        self._showLog(exportedScripts, title=_(u'Export Scripts'),
                      asDialog=True, icons=Resources.bashBlue)

class Mod_Scripts_Import(_Mod_Import_Link):
    """Import scripts from text file."""
    _text = _(u'Scripts...')
    help = _(u'Import scripts from text file')
    continueInfo = _(
        u"Import script from a text file.  This will replace existing "
        u"scripts and is not reversible (except by restoring from backup)!")
    continueKey = 'bash.scripts.import.continue'
    progressTitle = _(u'Import Scripts')

    def _parser(self):
        return CBash_ScriptText() if CBashApi.Enabled else ScriptText()

    def Execute(self):
        if not self._askContinueImport(): return
        defaultPath = bass.dirs['patches'].join(
            self._selected_item.s + u' Exported Scripts')
        if not defaultPath.exists():
            defaultPath = bass.dirs['patches']
        textDir = self._askDirectory(
            message=_(u'Choose directory to import scripts from'),
            defaultPath=defaultPath)
        if textDir is None:
            return
        message = (_(u"Import scripts that don't exist in the esp as new"
                     u" scripts?") + u'\n' +
                   _(u'(If not they will just be skipped).')
                   )
        makeNew = self._askYes(message, _(u'Import Scripts'),
                               questionIcon=True)
        scriptText = self._parser()
        scriptText.readFromText(textDir.s, self._selected_info)
        changed, added = scriptText.writeToMod(self._selected_info, makeNew)
        #--Log
        if not (len(changed) or len(added)):
            self._showOk(_(u"No changed or new scripts to import."),
                         _(u"Import Scripts"))
            return
        if changed:
            changedScripts = (_(u'Imported %d changed scripts from %s:') +
                              u'\n%s') % (
                len(changed), textDir.s, u'*' + u'\n*'.join(sorted(changed)))
        else:
            changedScripts = u''
        if added:
            addedScripts = (_(u'Imported %d new scripts from %s:')
                            + u'\n%s') % (
                len(added), textDir.s, u'*' + u'\n*'.join(sorted(added)))
        else:
            addedScripts = u''
        report = None
        if changed and added:
            report = changedScripts + u'\n\n' + addedScripts
        elif changed:
            report = changedScripts
        elif added:
            report = addedScripts
        self._showLog(report, title=_(u'Import Scripts'))

#------------------------------------------------------------------------------
from ..parsers import ItemStats, CBash_ItemStats

class Mod_Stats_Export(_Mod_Export_Link):
    """Exports stats from the selected plugin to a CSV file (for the record
    types specified in bush.game.statsTypes)."""
    askTitle = _(u'Export stats to:')
    csvFile = u'_Stats.csv'
    progressTitle = _(u"Export Stats")
    _text = _(u'Stats...')
    help = _(u'Export stats from mod to text file')

    def _parser(self):
        return CBash_ItemStats() if CBashApi.Enabled else ItemStats()

class Mod_Stats_Import(_Mod_Import_Link):
    """Import stats from text file."""
    askTitle = _(u'Import stats from:')
    csvFile = u'_Stats.csv'
    progressTitle = _(u'Import Stats')
    _text = _(u'Stats...')
    help = _(u'Import stats from text file')
    continueInfo = _(u"Import item stats from a text file. This will replace "
                     u"existing stats and is not reversible!")
    continueKey = 'bash.stats.import.continue'
    noChange = _(u"No relevant stats to import.")

    def _parser(self):
        return CBash_ItemStats() if CBashApi.Enabled else ItemStats()

    def _log(self, changed, fileName):
        with bolt.sio() as buff:
            for modName in sorted(changed):
                buff.write(u'* %03d  %s\n' % (changed[modName], modName.s))
            self._showLog(buff.getvalue())
            buff.close()

#------------------------------------------------------------------------------
from ..parsers import ItemPrices, CBash_ItemPrices

class Mod_Prices_Export(_Mod_Export_Link):
    """Export item prices from mod to text file."""
    askTitle = _(u'Export prices to:')
    csvFile = u'_Prices.csv'
    progressTitle = _(u'Export Prices')
    _text = _(u'Prices...')
    help = _(u'Export item prices from mod to text file')

    def _parser(self):
        return CBash_ItemPrices() if CBashApi.Enabled else ItemPrices()

class Mod_Prices_Import(_Mod_Import_Link):
    """Import prices from text file or other mod."""
    askTitle = _(u'Import prices from:')
    csvFile = u'_Prices.csv'
    progressTitle = _(u'Import Prices')
    _text = _(u'Prices...')
    help = _(u'Import item prices from text file or other mod')
    continueInfo = _(u"Import item prices from a text file.  This will "
                     u"replace existing prices and is not reversible!")
    continueKey = 'bash.prices.import.continue'
    noChange = _(u'No relevant prices to import.')
    supportedExts = {u'.csv', u'.ghost', u'.esm', u'.esp'}

    def _parser(self):
        return CBash_ItemPrices() if CBashApi.Enabled else ItemPrices()

    def _log(self, changed, fileName):
        with bolt.sio() as buff:
            for modName in sorted(changed):
                buff.write(_(u'Imported Prices:')
                           + u'\n* %s: %d\n' % (modName.s,changed[modName]))
            self._showLog(buff.getvalue())

#------------------------------------------------------------------------------
from ..parsers import SigilStoneDetails, CBash_SigilStoneDetails

class Mod_SigilStoneDetails_Export(_Mod_Export_Link):
    """Export Sigil Stone details from mod to text file."""
    askTitle = _(u'Export Sigil Stone details to:')
    csvFile = u'_SigilStones.csv'
    progressTitle = _(u'Export Sigil Stone details')
    _text = _(u'Sigil Stones...')
    help = _(u'Export Sigil Stone details from mod to text file')

    def _parser(self):
        return CBash_SigilStoneDetails() if CBashApi.Enabled else \
            SigilStoneDetails()

class Mod_SigilStoneDetails_Import(_Mod_Import_Link):
    """Import Sigil Stone details from text file."""
    askTitle = _(u'Import Sigil Stone details from:')
    csvFile = u'_SigilStones.csv'
    progressTitle = _(u'Import Sigil Stone details')
    _text = _(u'Sigil Stones...')
    help = _(u'Import Sigil Stone details from text file')
    continueInfo = _(
        u"Import Sigil Stone details from a text file.  This will replace "
        u"the existing data on sigil stones with the same form ids and is "
        u"not reversible!")
    continueKey = 'bash.SigilStone.import.continue'
    noChange = _(u'No relevant Sigil Stone details to import.')

    def _parser(self):
        return CBash_SigilStoneDetails() if CBashApi.Enabled else \
            SigilStoneDetails()

    def _log(self, changed, fileName):
        with bolt.sio() as buff:
            buff.write((_(u'Imported Sigil Stone details to mod %s:')
                        +u'\n') % fileName.s)
            for eid in sorted(changed):
                buff.write(u'* %s\n' % eid)
            self._showLog(buff.getvalue())

#------------------------------------------------------------------------------
from ..parsers import SpellRecords, CBash_SpellRecords

class Mod_SpellRecords_Export(_Mod_Export_Link):
    """Export Spell details from mod to text file."""
    askTitle = _(u'Export Spell details to:')
    csvFile = u'_Spells.csv'
    progressTitle = _(u'Export Spell details')
    _text = _(u'Spells...')
    help = _(u'Export Spell details from mod to text file')

    def _parser(self):
        message = (_(u'Export flags and effects?')
                   + u'\n' +
                   _(u'(If not they will just be skipped).')
                   )
        doDetailed = self._askYes(message, _(u'Export Spells'),
                                  questionIcon=True)
        return CBash_SpellRecords(detailed=doDetailed) if CBashApi.Enabled \
            else SpellRecords(detailed=doDetailed)

class Mod_SpellRecords_Import(_Mod_Import_Link):
    """Import Spell details from text file."""
    askTitle = _(u'Import Spell details from:')
    csvFile = u'_Spells.csv'
    progressTitle = _(u'Import Spell details')
    _text = _(u'Spells...')
    help = _(u'Import Spell details from text file')
    continueInfo = _(u"Import Spell details from a text file.  This will "
        u"replace the existing data on spells with the same form ids and is "
        u"not reversible!")
    continueKey = 'bash.SpellRecords.import.continue'
    noChange = _(u'No relevant Spell details to import.')

    def _parser(self):
        message = (_(u'Import flags and effects?')
                   + u'\n' +
                   _(u'(If not they will just be skipped).')
                   )
        doDetailed = self._askYes(message, _(u'Import Spell details'),
                                  questionIcon=True)
        return CBash_SpellRecords(detailed=doDetailed) if CBashApi.Enabled \
            else SpellRecords(detailed=doDetailed)

    def _log(self, changed, fileName):
        with bolt.sio() as buff:
            buff.write((_(u'Imported Spell details to mod %s:')
                        +u'\n') % fileName.s)
            for eid in sorted(changed):
                buff.write(u'* %s\n' % eid)
            self._showLog(buff.getvalue())

#------------------------------------------------------------------------------
from ..parsers import IngredientDetails, CBash_IngredientDetails

class Mod_IngredientDetails_Export(_Mod_Export_Link):
    """Export Ingredient details from mod to text file."""
    askTitle = _(u'Export Ingredient details to:')
    csvFile = u'_Ingredients.csv'
    progressTitle = _(u'Export Ingredient details')
    _text = _(u'Ingredients...')
    help = _(u'Export Ingredient details from mod to text file')

    def _parser(self):
        return CBash_IngredientDetails() if CBashApi.Enabled else \
            IngredientDetails()

class Mod_IngredientDetails_Import(_Mod_Import_Link):
    """Import Ingredient details from text file."""
    askTitle = _(u'Import Ingredient details from:')
    csvFile = u'_Ingredients.csv'
    progressTitle = _(u'Import Ingredient details')
    _text = _(u'Ingredients...')
    help = _(u'Import Ingredient details from text file')
    continueInfo = _(u"Import Ingredient details from a text file.  This will "
                     u"replace the existing data on Ingredients with the same "
                     u"form ids and is not reversible!")
    continueKey = 'bash.Ingredient.import.continue'
    noChange = _(u'No relevant Ingredient details to import.')

    def _parser(self):
        return CBash_IngredientDetails() if CBashApi.Enabled else \
            IngredientDetails()

    def _log(self, changed, fileName):
        with bolt.sio() as buff:
            buff.write((_(u'Imported Ingredient details to mod %s:')
                        + u'\n') % fileName.s)
            for eid in sorted(changed):
                buff.write(u'* %s\n' % eid)
            self._showLog(buff.getvalue())

#------------------------------------------------------------------------------
from ..parsers import EditorIds, CBash_EditorIds

class Mod_EditorIds_Export(_Mod_Export_Link):
    """Export editor ids from mod to text file."""
    askTitle = _(u'Export eids to:')
    csvFile = u'_Eids.csv'
    progressTitle = _(u"Export Editor Ids")
    _text = _(u'Editor Ids...')
    help = _(u'Export faction editor ids from mod to text file')

    def _parser(self):
        return CBash_EditorIds() if CBashApi.Enabled else EditorIds()

class Mod_EditorIds_Import(_Mod_Import_Link):
    """Import editor ids from text file."""
    askTitle = _(u'Import eids from:')
    csvFile = u'_Eids.csv'
    continueInfo = _(u"Import editor ids from a text file. This will replace "
                     u"existing ids and is not reversible!")
    continueKey = 'bash.editorIds.import.continue'
    progressTitle = _(u'Import Editor Ids')
    _text = _(u'Editor Ids...')
    help = _(u'Import faction editor ids from text file')

    def _parser(self):
        return CBash_EditorIds() if CBashApi.Enabled else EditorIds()

    def Execute(self):
        if not self._askContinueImport(): return
        textName = self._selected_item.root + self.__class__.csvFile
        textDir = bass.dirs['patches']
        #--File dialog
        textPath = self._askOpen(self.__class__.askTitle,textDir,
            textName, self._wildcard ,mustExist=True)
        if not textPath: return
        (textDir,textName) = textPath.headTail
        #--Extension error check
        if textName.cext != u'.csv':
            self._showError(_(u'Source file must be a csv file.'))
            return
        #--Import
        questionableEidsSet = set()
        badEidsList = []
        try:
            with balt.Progress(self.__class__.progressTitle) as progress:
                editorIds = self._parser()
                progress(0.1,_(u'Reading') + u' ' + textName.s + u'.')
                editorIds.readFromText(textPath,questionableEidsSet,badEidsList)
                progress(0.2, _(u"Applying to %s.") % (self._selected_item.s,))
                changed = editorIds.writeToMod(self._selected_info)
                progress(1.0,_(u"Done."))
            #--Log
            if not changed:
                self._showOk(self.__class__.noChange)
            else:
                buff = StringIO.StringIO()
                format_ = u"%s'%s' >> '%s'\n"
                for old,new in sorted(changed):
                    if new in questionableEidsSet:
                        prefix = u'* '
                    else:
                        prefix = u''
                    buff.write(format_ % (prefix,old,new))
                if questionableEidsSet:
                    buff.write(u'\n* '+_(u'These editor ids begin with numbers and may therefore cause the script compiler to generate unexpected results')+u'\n')
                if badEidsList:
                    buff.write(u'\n'+_(u'The following EIDs are malformed and were not imported:')+u'\n')
                    for badEid in badEidsList:
                        buff.write(u"  '%s'\n" % badEid)
                text = buff.getvalue()
                buff.close()
                self._showLog(text, title=_(u'Objects Changed'))
        except bolt.BoltError as e:
            self._showWarning('%r' % e)

#------------------------------------------------------------------------------
from ..parsers import FullNames, CBash_FullNames

class Mod_FullNames_Export(_Mod_Export_Link):
    """Export full names from mod to text file."""
    askTitle = _(u'Export names to:')
    csvFile = u'_Names.csv'
    progressTitle = _(u"Export Names")
    _text = _(u'Names...')
    help = _(u'Export full names from mod to text file')

    def _parser(self):
        return CBash_FullNames() if CBashApi.Enabled else FullNames()

class Mod_FullNames_Import(_Mod_Import_Link):
    """Import full names from text file or other mod."""
    askTitle = _(u'Import names from:')
    csvFile = u'_Names.csv'
    progressTitle = _(u'Import Names')
    continueInfo = _(
        u"Import record names from a text file. This will replace existing "
        u"names and is not reversible!")
    continueKey = 'bash.fullNames.import.continue'
    _text = _(u'Names...')
    help = _(u'Import full names from text file or other mod')
    supportedExts = {u'.csv', u'.ghost', u'.esm', u'.esp'}

    def _parser(self):
        return CBash_FullNames() if CBashApi.Enabled else FullNames()

    def _log(self, changed, fileName):
        with bolt.sio() as buff:
            format_ = u'%s:   %s >> %s\n'
            #buff.write(format_ % (_(u'Editor Id'),_(u'Name')))
            for eid in sorted(changed.keys()):
                full, newFull = changed[eid]
                try:
                    buff.write(format_ % (eid, full, newFull))
                except:
                    print u'unicode error:', (format_, eid, full, newFull)
            self._showLog(buff.getvalue(), title=_(u'Objects Renamed'))

# CBash only Import/Export ----------------------------------------------------
class _Mod_Export_Link_CBash(_Mod_Export_Link, EnabledLink):
    def _enable(self): return CBashApi.Enabled

class _Mod_Import_Link_CBash(_Mod_Import_Link):
    def _enable(self):
        return super(_Mod_Import_Link_CBash, self)._enable() and \
               CBashApi.Enabled

#------------------------------------------------------------------------------
from ..parsers import CBash_MapMarkers

class CBash_Mod_MapMarkers_Export(_Mod_Export_Link_CBash):
    """Export map marker stats from mod to text file."""
    askTitle = _(u'Export Map Markers to:')
    csvFile = u'_MapMarkers.csv'
    progressTitle = _(u'Export Map Markers')
    _text = _(u'Map Markers...')
    help = _(u'Export map marker stats from mod to text file')

    def _parser(self): return CBash_MapMarkers()

class CBash_Mod_MapMarkers_Import(_Mod_Import_Link_CBash):
    """Import MapMarkers from text file."""
    askTitle = _(u'Import Map Markers from:')
    csvFile = u'_MapMarkers.csv'
    progressTitle = _(u'Import Map Markers')
    _text = _(u'Map Markers...')
    help = _(u'Import MapMarkers from text file')
    continueInfo = _(
        u"Import Map Markers data from a text file.  This will replace "
        u"the existing data on map markers with the same editor ids and is "
        u"not reversible!")
    continueKey = 'bash.MapMarkers.import.continue'

    def _parser(self): return CBash_MapMarkers()

    def Execute(self):
        if not self._askContinueImport(): return
        textName = self._selected_item.root + self.__class__.csvFile
        textDir = bass.dirs['patches']
        #--File dialog
        textPath = self._askOpen(self.__class__.askTitle,
            textDir, textName, u'*_MapMarkers.csv',mustExist=True)
        if not textPath: return
        (textDir,textName) = textPath.headTail
        #--Extension error check
        ext = textName.cext
        if ext != u'.csv':
            self._showError(_(u'Source file must be a MapMarkers.csv file'))
            return
        #--Import
        changed = self._import(ext, textDir, textName, textPath)
        #--Log
        if not changed:
            self._showOk(_(u'No relevant Map Markers to import.'),
                         _(u'Import Map Markers'))
        else:
            buff = StringIO.StringIO()
            buff.write((_(u'Imported Map Markers to mod %s:') + u'\n') % (
                self._selected_item.s,))
            for eid in sorted(changed):
                buff.write(u'* %s\n' % eid)
            self._showLog(buff.getvalue())
            buff.close()

#------------------------------------------------------------------------------
from ..parsers import CBash_CellBlockInfo

class CBash_Mod_CellBlockInfo_Export(_Mod_Export_Link_CBash):
    """Export Cell Block Info to text file
    (in the form of Cell, block, subblock)."""
    askTitle = _(u'Export Cell Block Info to:')
    csvFile = u'_CellBlockInfo.csv'
    progressTitle = _(u"Export Cell Block Info")
    _text = _(u'Cell Block Info...')
    help = _(u'Export Cell Block Info to text file (in the form of Cell,'
             u' block, subblock)')

    def _parser(self): return CBash_CellBlockInfo()

# Unused ? --------------------------------------------------------------------
from ..parsers import CompleteItemData, CBash_CompleteItemData

class Mod_ItemData_Export(_Mod_Export_Link): # CRUFT
    """Export pretty much complete item data from mod to text file."""
    askTitle = _(u'Export item data to:')
    csvFile = u'_ItemData.csv'
    progressTitle = _(u"Export Item Data")
    _text = _(u'Item Data...')
    help = _(u'Export pretty much complete item data from mod to text file')

    def _parser(self):
        return CBash_CompleteItemData() if CBashApi.Enabled else \
            CompleteItemData()

class Mod_ItemData_Import(_Mod_Import_Link): # CRUFT
    """Import stats from text file or other mod."""
    askTitle = _(u'Import item data from:')
    csvFile = u'_ItemData.csv'
    progressTitle = _(u'Import Item Data')
    _text = _(u'Item Data...')
    help = _(u'Import pretty much complete item data from text file or other'
             u' mod')
    continueInfo = _(
        u"Import pretty much complete item data from a text file.  This will "
        u"replace existing data and is not reversible!")
    continueKey = 'bash.itemdata.import.continue'
    noChange = _(u'No relevant data to import.')

    def _parser(self):
    # CBash_CompleteItemData.writeToText is disabled, apparently has problems
        return CompleteItemData()

    def _log(self, changed, fileName):
        with bolt.sio() as buff:
            for modName in sorted(changed):
                buff.write(_(u'Imported Item Data:') + u'\n* %03d  %s:\n' % (
                    changed[modName], modName.s))
            self._showLog(buff.getvalue())

#------------------------------------------------------------------------------
from ..bolt import deprint
from ..cint import ObCollection

class MasterList_AddMasters(ItemLink): # CRUFT
    """Adds a master."""
    _text = _(u'Add Masters...')
    help = _(u'Adds specified master to list of masters')

    def Execute(self):
        message = _(u"WARNING!  For advanced modders only!  Adds specified master to list of masters, thus ceding ownership of new content of this mod to the new master.  Useful for splitting mods into esm/esp pairs.")
        if not self._askContinue(message, 'bash.addMaster.continue',
                                 _(u'Add Masters')): return
        modInfo = self.window.fileInfo
        wildcard = bush.game.displayName+u' '+_(u'Masters')+u' (*.esm;*.esp)|*.esm;*.esp'
        masterPaths = self._askOpenMulti(
                            title=_(u'Add masters:'), defaultDir=modInfo.dir,
                            wildcard=wildcard)
        if not masterPaths: return
        names = []
        for masterPath in masterPaths:
            (dir_,name) = masterPath.headTail
            if dir_ != modInfo.dir:
                return self._showError(_(
                    u"File must be selected from %s Data Files directory.")
                                       % bush.game.fsName)
            if name in modInfo.header.masters:
                return self._showError(
                    name.s + u' ' + _(u"is already a master."))
            names.append(name)
        for masterName in load_order.get_ordered(names):
            if masterName in bosh.modInfos:
                masterName = bosh.modInfos[masterName].name
            modInfo.header.masters.append(masterName)
        modInfo.header.changed = True
        self.window.SetFileInfo(modInfo)
        self.window.InitEdit()
        self.window.SetMasterlistEdited(repopulate=True)

#------------------------------------------------------------------------------
class MasterList_CleanMasters(AppendableLink, ItemLink): # CRUFT
    """Remove unneeded masters."""
    _text, help = _(u'Clean Masters...'), _(u'Remove unneeded masters')

    def _append(self, window): return bass.settings['bash.CBashEnabled']

    def Execute(self):
        message = _(u"WARNING!  For advanced modders only!  Removes masters that are not referenced in any records.")
        if not self._askContinue(message, 'bash.cleanMaster.continue',
                                 _(u'Clean Masters')): return
        modInfo = self.window.fileInfo
        mpath = modInfo.getPath()

        with ObCollection(ModsPath=bass.dirs['mods'].s) as Current:
            modFile = Current.addMod(mpath.stail)
            Current.load()
            oldMasters = modFile.TES4.masters
            cleaned = modFile.CleanMasters()
            if cleaned:
                newMasters = modFile.TES4.masters
                removed = [GPath(x) for x in oldMasters if x not in newMasters]
                removeKey = _(u'Masters')
                group = [removeKey, _(
                    u'These master files are not referenced within the mod, '
                    u'and can safely be removed.'), ]
                group.extend(removed)
                checklists = [group]
                with ListBoxes(Link.Frame, _(u'Remove these masters?'), _(
                        u'The following master files can be safely removed.'),
                        checklists) as dialog:
                    if not dialog.askOkModal(): return
                    newMasters.extend(
                        dialog.getChecked(removeKey, removed, checked=False))
                    modFile.TES4.masters = newMasters
                    modFile.save()
                    deprint(u'to remove:', removed)
            else:
                self._showOk(_(u'No Masters to clean.'), _(u'Clean Masters'))
