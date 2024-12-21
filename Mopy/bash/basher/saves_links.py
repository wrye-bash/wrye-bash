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

"""Menu items for the main and item menus of the saves tab - their window
attribute points to SaveList singleton."""

import io
import os
import re
import shutil

from .dialogs import ImportFaceDialog
from .. import balt, bass, bolt, bosh, bush, initialization, load_order
from ..balt import AppendableLink, CheckLink, ChoiceLink, EnabledLink, \
    ItemLink, Link, OneItemLink, SeparatorLink
from ..bass import Store
from ..bolt import FName, GPath, Path, RefrIn, SubProgress, RefrData
from ..bosh import _saves, faces
from ..brec import ShortFidWriteContext
from ..exception import ArgumentError, BoltError, ModError
from ..gui import BusyCursor, FileSave, askText, showError, askYes, showOk, \
    BmpFromStream
from ..mod_files import LoadFactory, MasterMap, ModFile

__all__ = ['Saves_Profiles', 'Save_Renumber', 'Save_Move',
           u'Save_ActivateMasters', u'Save_DiffMasters', u'Save_Stats',
           u'Save_StatObse', u'Save_EditPCSpells', u'Save_RenamePlayer',
           u'Save_EditCreatedEnchantmentCosts', u'Save_ImportFace',
           u'Save_EditCreated', u'Save_ReweighPotions', u'Save_UpdateNPCLevels',
           u'Save_ExportScreenshot', u'Save_Unbloat', u'Save_RepairAbomb',
           u'Save_RepairHair', u'Save_StatPluggy', u'Save_ReorderMasters']

#------------------------------------------------------------------------------
# Saves Links -----------------------------------------------------------------
#------------------------------------------------------------------------------
def _win_join(saves_subdir):
    """Join base (default) save dir with subdir using the windows path
    separator. Needed as we want to write this separator to the game ini
    file."""
    return u'\\'.join([bush.game.Ini.save_prefix, saves_subdir])

class Saves_ProfilesData(balt.ListEditorData):
    """Data capsule for save profiles editing dialog."""
    def __init__(self,parent):
        """Initialize."""
        self.baseSaves = bass.dirs[u'saveBase'].join(u'Saves')
        #--GUI
        super().__init__(parent)
        self._parent_list = parent
        self.showAdd    = True
        self.showRename = True
        self.showRemove = True
        self.showInfo   = True
        self.infoWeight = 2
        self.infoReadOnly = False

    def getItemList(self):
        """Returns load list keys in alpha order."""
        #--Get list of directories in Hidden, but do not include default.
        return initialization.getLocalSaveDirs()

    #--Info box
    def getInfo(self,item):
        """Returns string info on specified item."""
        profileSaves = _win_join(item)
        return bosh.saveInfos.get_profile_attr(profileSaves, 'info',
            _('About %(save_profile)s:') % {'save_profile': item})

    def setInfo(self, item, info_text):
        """Sets string info on specified item."""
        profileSaves = _win_join(item)
        bosh.saveInfos.set_profile_attr(profileSaves, u'info', info_text)

    def add(self):
        """Adds a new profile."""
        newName = askText(self.parent, _('Enter profile name:'))
        if not self._validate_prof_name(newName): return
        self.baseSaves.join(newName).makedirs()
        newSaves = _win_join(newName)
        bosh.saveInfos.set_profile_attr(newSaves, 'vOblivion',
                                        bosh.modInfos.voCurrent)
        return newName

    def rename(self,oldName,newName):
        """Renames profile oldName to newName."""
        newName = newName.strip()
        if not self._validate_prof_name(newName): return
        #--Rename
        oldDir, newDir = map(self.baseSaves.join, (oldName, newName))
        oldDir.moveTo(newDir)
        oldSaves, newSaves = map(_win_join, (oldName, newName))
        if bosh.saveInfos.localSave == oldSaves:
            # this will clear and refresh SaveInfos - we could be smarter as
            # only the abs_path of the infos changes - not worth the complexity
            self._parent_list.set_local_save(newSaves)
        bosh.saveInfos.rename_profile(oldSaves, newSaves)
        return newName

    def _validate_prof_name(self, newName):
        #--Error checks
        if not newName: return False
        lowerNames = {savedir.lower() for savedir in self.getItemList()}
        if newName.lower() in lowerNames:
            showError(self.parent, _('Name must be unique.'))
            return False
        if len(newName) == 0 or len(newName) > 64:
            showError(self.parent, _('Name must be between 1 and 64 '
                                     'characters long.'))
            return False
        try:
            newName.encode('cp1252')
        except UnicodeEncodeError:
            showError(self.parent, _('Name must be encodable in Windows '
                'Codepage 1252 (Western European), due to limitations of '
                '%(gameIni)s.') % {'gameIni': bush.game.Ini.dropdown_inis[0]})
            return False
        if inv := Path.has_invalid_chars(newName):
            showError(self.parent, _('Name must not contain invalid chars for '
                'a windows path like %(inv)s') % {'inv': inv})
            return False
        return True

    def remove(self,profile):
        """Remove save profile."""
        profileSaves = _win_join(profile)
        #--Can't remove active or Default directory.
        if bosh.saveInfos.localSave == profileSaves:
            showError(self.parent, _('Active profile cannot be removed.'))
            return False
        #--Get file count. If > zero, verify with user.
        profileDir = bass.dirs[u'saveBase'].join(profileSaves)
        files = [save_file for save_file in profileDir.ilist() if
                 bosh.SaveInfos.rightFileType(save_file)]
        if files:
            message = _('Delete profile %(save_profile)s and the '
                        '%(num_contained_saves)d save files it contains?') % {
                'save_profile': profile, 'num_contained_saves': len(files)}
            if not askYes(self.parent, message, _('Delete Profile')):
                return False
        #--Remove directory
        if GPath(bush.game.my_games_name).join(u'Saves').s not in profileDir.s:
            raise BoltError(f'Sanity check failed: No '
                f'"{bush.game.my_games_name}\\Saves" in {profileDir}.')
        shutil.rmtree(profileDir.s) #--DO NOT SCREW THIS UP!!!
        bosh.saveInfos.rename_profile(profileSaves, None)
        return True

#------------------------------------------------------------------------------
class Saves_Profiles(ChoiceLink):
    """Select a save set profile -- i.e., the saves directory."""
    # relative path to save base dir as in My Games/Oblivion
    _my_games = bass.dirs[u'saveBase'].s[
                bass.dirs[u'saveBase'].cs.find(u'my games'):]
    _my_games = GPath(_my_games)

    @property
    def _choices(self): return initialization.getLocalSaveDirs()

    class _ProfileLink(CheckLink, EnabledLink):
        @property
        def link_help(self):
            profile_dir = Saves_Profiles._my_games.join(
                bush.game.Ini.save_prefix, self._text)
            return _('Set profile to %(save_profile_name)s '
                     '(%(save_profile_dir)s).') % {
                'save_profile_name': self._text,
                'save_profile_dir': profile_dir}

        @property
        def relativePath(self): return _win_join(self._text)

        def _check(self): return bosh.saveInfos.localSave == self.relativePath

        def _enable(self): return not self._check()

        def Execute(self):
            new_dir = self.relativePath
            with BusyCursor():
                self.window.set_local_save(new_dir, do_swap=self._askYes)
                self.window.DeleteAll() # let call below repopulate
                self.window.propagate_refresh(Store.MODS.DO(),detail_item=None)
                self.window.panel.ShowPanel()
                Link.Frame.warn_corrupted(warn_saves=True)

    choiceLinkType = _ProfileLink

    class _Default(_ProfileLink):
        _text = _(u'Default')

        @property
        def link_help(self):
            profile_dir = Saves_Profiles._my_games.join(
                bush.game.Ini.save_prefix)
            return _('Set profile to the default (%(save_profile_dir)s).') % {
                'save_profile_dir': profile_dir}

        @property
        def relativePath(self): return bush.game.Ini.save_prefix

    class _Edit(ItemLink):
        _text = _('Edit Profiles…')
        _help = _(u'Show save profiles editing dialog')

        def Execute(self):
            """Show save profiles editing dialog."""
            sp_data = Saves_ProfilesData(self.window)
            balt.ListEditor.display_dialog(self.window, _(u'Save Profiles'),
                                           sp_data)

    extraItems = [_Edit(), SeparatorLink(), _Default()]

#------------------------------------------------------------------------------
class _Save_ChangeLO(OneItemLink):
    """Abstract class for links that alter load order."""
    def Execute(self):
        lo_warn_msg = self._lo_operation()
        self.window.propagate_refresh(Store.MODS.DO(), focus_list=False)
        self.window.Focus()
        if lo_warn_msg:
            self._showWarning(lo_warn_msg, self._selected_item)

    def _lo_operation(self):
        raise NotImplementedError

class Save_ActivateMasters(_Save_ChangeLO):
    """Sets the active mods to the save game's masters."""
    _text = _(u'Activate Masters')
    _help = _(u'Activates exactly the plugins present in the master list of '
              u'this save.')

    def _lo_operation(self):
        return bosh.modInfos.lo_activate_exact(self._selected_info.masterNames)

#------------------------------------------------------------------------------
class Save_ReorderMasters(_Save_ChangeLO):
    """Changes the load order to match the save game's masters."""
    _text = _(u'Reorder Masters')
    _help = _(u'Reorders the plugins in the current load order to match the '
              u'order of plugins in this save.')

    def _lo_operation(self):
        return bosh.modInfos.lo_reorder(self._selected_info.masterNames)

#------------------------------------------------------------------------------
class Save_ImportFace(OneItemLink):
    """Imports a face from another save."""
    _text = _('Import Face…')
    _help = _(u'Import a face from another save')

    @balt.conversation
    def Execute(self):
        #--Select source face file
        srcDir = self._selected_info.info_dir
        exts = u';*'.join(bush.game.espm_extensions | {
            bush.game.Ess.ext, bush.game.Ess.ext[-1] + u'r'})
        wildcard = _('Source Files') + f' (*{exts})|*{exts}'
        #--File dialog
        srcPath = self._askOpen(title=_('Face Source:'), defaultDir=srcDir,
                                wildcard=wildcard)
        if not srcPath: return
        fname = srcPath.tail.s
        if bosh.SaveInfos.rightFileType(fname): # Import from a save
            #--Get face
            srcInfo = bosh.SaveInfo(srcPath)
            with balt.Progress(fname) as progress:
                saveFile = _saves.SaveFile(srcInfo)
                saveFile.load(progress)
            srcFaces = faces.PCFaces.save_getFaces(saveFile)
        elif bosh.ModInfos.rightFileType(fname): # Import from a mod
            #--Get faces
            srcInfo = bosh.ModInfo(srcPath)
            srcFaces = faces.PCFaces.mod_getFaces(srcInfo)
            #--No faces to import?
            if not srcFaces:
                self._showOk(_('No player faces found in '
                               '%(face_import_target)s.') % {
                    'face_import_target': fname}, fname)
                return
        else: return
        #--Dialog
        ImportFaceDialog.display_dialog(self.window, fname,
                                        self._selected_info, srcFaces)

#------------------------------------------------------------------------------
class Save_RenamePlayer(ItemLink):
    """Renames the Player character in a save game."""
    _text = _('Rename Player…')
    _help = _(u'Rename the Player character in a save game')

    def Execute(self):
        # get new player name - must not be empty
        saveInfo = self._first_selected()
        newName = self._askText(
            _(u'Enter new player name. E.g. Conan the Bold'),
            title=_(u'Rename player'), default=saveInfo.header.pcName)
        if not newName: return
        for save_inf in self.iselected_infos():
            savedPlayer = _saves.Save_NPCEdits(save_inf)
            savedPlayer.renamePlayer(newName)
        bosh.saveInfos.refresh()
        self.refresh_sel()

#------------------------------------------------------------------------------
class Save_ExportScreenshot(OneItemLink):
    """Exports the saved screenshot from a save game."""
    _text = _('Export Screenshot…')
    _help = _(u'Export the saved screenshot from a save game')

    def Execute(self):
        imagePath = FileSave.display_dialog(Link.Frame,
            title=_('Save Screenshot As:'), defaultDir=bass.dirs['patches'].s,
            defaultFile=_('Screenshot %(save_name)s.jpg') % {
                'save_name': self._selected_item}, wildcard='*.jpg')
        if not imagePath: return
        image = BmpFromStream(*self._selected_info.header.image_parameters)
        image.save_bmp(imagePath.s)

#------------------------------------------------------------------------------
##: Split in two, one OneItemLink diffing against active plugins and one link
# that needs two or more plugins and diffs those against each other
class Save_DiffMasters(EnabledLink):
    """Shows how saves masters differ from active mod list."""
    _text = _('Diff Masters…')
    _help = _('Show how the masters of a save differ from active mod list or '
              'another save')

    def _enable(self): return len(self.selected) in (1,2)

    def Execute(self):
        oldNew = self.selected
        oldNew.sort(key=lambda x: bosh.saveInfos[x].ftime)
        oldName = oldNew[0]
        oldInfo = self._data_store[oldName]
        oldMasters = set(oldInfo.masterNames)
        if len(self.selected) == 1:
            newName = GPath(_(u'Active Masters'))
            newMasters = set(load_order.cached_active_tuple())
        else:
            newName = oldNew[1]
            newInfo = self._data_store[newName]
            newMasters = set(newInfo.masterNames)
        missing = oldMasters - newMasters
        added = newMasters - oldMasters
        if not missing and not added:
            message = _(u'Masters are the same.')
            self._showInfo(message, title=_(u'Diff Masters'))
        else:
            message = u''
            if missing:
                message += '=== ' + _('Removed Masters') + f' ({oldName}):\n* '
                message += u'\n* '.join(load_order.get_ordered(missing))
                if added: message += u'\n\n'
            if added:
                message += u'=== ' + _(u'Added Masters') + f' ({newName}):\n* '
                message += u'\n* '.join(load_order.get_ordered(added))
            self._showWryeLog(message, title=_(u'Diff Masters'))

#------------------------------------------------------------------------------
class Save_Renumber(EnabledLink):
    """Renumbers a whole lot of save files."""
    _text = _('Renumber Saves…')
    _help = _(u'Renumber a whole lot of save files. Savename must be of the '
              u'form "Save <some number><optional text>"')
    _re_numbered_save = re.compile(r'^(save ?)(\d*)(.*)', re.I)

    def _enable(self):
        self._matches = [(s_groups, sinf) for sinf in self.iselected_infos() if
            (save_match := self._re_numbered_save.match(sinf.fn_key)) and
            (s_groups := save_match.groups())[1]]
        return bool(self._matches)

    @balt.conversation
    def Execute(self):
        nfn_number = self._askNumber(
            _(u'Enter new number to start numbering the selected saves at.'),
            prompt=_(u'Save Number'), title=_('Renumber Saves'), initial_num=1,
            min_num=1, max_num=10000)
        if nfn_number is None: return
        rdata = None
        for s_groups, sinf in self._matches:
            # We have to pass the root, so strip off the extension
            ofn_root = FName(s_groups[2]).fn_body
            nfn_save = FName(f'{s_groups[0]}{nfn_number:d}{ofn_root}')
            if nfn_save != sinf.fn_key.fn_body:
                if (rdata := self.window.try_rename(sinf, nfn_save,
                                                    rdata)) is None:
                    break
                nfn_number += 1
        if rdata:
            self.window.RefreshUI(rdata)
            self.window.SelectItemsNoCallback(rdata.redraw)

#------------------------------------------------------------------------------
class Save_EditCreatedData(balt.ListEditorData):
    """Data capsule for custom item editing dialog."""
    def __init__(self, parent, saveFile, types_set):
        self._changed = False
        self.saveFile = saveFile
        name_nameRecords = self.name_nameRecords = {}
        self.enchantments = {}
        #--Parse records and get into name_nameRecords
        with ShortFidWriteContext(): # needed for the getSize below
            for rfid, record in saveFile.created.items():
                if record._rec_sig == b'ENCH':
                    self.enchantments[record.fid] = record.getTypeCopy()
                elif record._rec_sig in types_set:
                    record = record.getTypeCopy()
                    if not record.full: continue
                    record.getSize() #--Since type copy makes it changed.
                    saveFile.created[rfid] = record
                    record_full = record.full
                    if record_full not in name_nameRecords:
                        name_nameRecords[record_full] = (record_full, [])
                    name_nameRecords[record_full][1].append(record)
        #--GUI
        balt.ListEditorData.__init__(self,parent)
        self.showRename = True
        self.showInfo = True
        self.showSave = True
        self.showCancel = True

    def getItemList(self):
        """Returns load list keys in alpha order."""
        items = sorted(self.name_nameRecords)
        items.sort(key=lambda x: self.name_nameRecords[x][1][0]._rec_sig)
        return items

    _attrs = {
        b'CLOT': (f'{_("Clothing")}\n{_("Flags: %(active_flags)s")}', ()),
        b'ARMO': (f'{_("Armor")}\n{_("Flags: %(active_flags)s")}', (
            'strength', 'value', 'weight')),
        b'WEAP': ('', ('damage', 'value', 'speed', 'reach', 'weight')),
    }
    def getInfo(self,item):
        """Returns string info on specified item."""
        buff = []
        record_full, recs = self.name_nameRecords[item]
        record = recs[0]
        #--Armor, clothing, weapons
        rsig = record.rec_sig
        if rsig in self._attrs:
            info_str, attrs = self._attrs[rsig]
            if rsig == b'WEAP':
                buff.append(bush.game.weaponTypes[record.weaponType])
            else:
                buff.append(info_str % {'active_flags': ', '.join(
                    record.biped_flags.getTrueAttrs())})
            for attr in attrs:
                buff.append(f'{attr}: {getattr(record, attr)}')
        #--Enchanted? Switch record to enchantment.
        if hasattr(record,'enchantment') and \
                record.enchantment in self.enchantments:
            buff.append('\n' + _('Enchantment:'))
            record = self.enchantments[record.enchantment].getTypeCopy()
        #--Magic effects
        if rsig in (b'ALCH', b'SPEL', b'ENCH'):
            buff.append(record.getEffectsSummary())
        #--Done
        return '\n'.join(buff)

    def rename(self,oldName,newName):
        """Renames oldName to newName."""
        #--Right length?
        if len(newName) == 0:
            return False
        elif len(newName) > 128:
            showError(self.parent, _('Name is too long.'))
            return False
        elif newName in self.name_nameRecords:
            showError(self.parent, _('Name is already used.'))
            return False
        #--Rename
        self.name_nameRecords[newName] = self.name_nameRecords.pop(oldName)
        self._changed = True
        return newName

    def save(self):
        """Handles save button."""
        if not self._changed:
            showOk(self.parent, _('No changes made.'))
        else:
            self._changed = False #--Allows graceful effort if close fails.
            count = 0
            with ShortFidWriteContext(): # needed for the getSize below
                for newName,(oldName,recs) in self.name_nameRecords.items():
                    if newName == oldName: continue
                    for record in recs:
                        record.full = newName
                        record.setChanged()
                        record.getSize()
                    count += 1
            self.saveFile.safeSave()
            msg = _('Names modified: %(num_names_changed)d.') % {
                'num_names_changed': count}
            showOk(self.parent, msg, title=self.saveFile.fileInfo.fn_key)

#------------------------------------------------------------------------------
class Save_EditCreated(OneItemLink):
    """Allows user to rename custom items (spells, enchantments, etc)."""
    menuNames = {b'ENCH':_('Rename Enchanted…'),
                 b'SPEL':_('Rename Spells…'),
                 b'ALCH':_('Rename Potions…')
                 }
    rec_types = {b'ENCH': {b'ARMO', b'CLOT', b'WEAP'}, b'SPEL': {b'SPEL'},
                 b'ALCH': {b'ALCH'}}
    _help = _(u'Allow user to rename custom items (spells, enchantments, etc)')

    def __init__(self, save_rec_type):
        if save_rec_type not in self.menuNames:
            raise ArgumentError
        super().__init__()
        self.save_rec_type = save_rec_type
        self._text = self.menuNames[self.save_rec_type]

    def Execute(self):
        #--Get SaveFile
        with balt.Progress(_('Loading…')) as progress:
            saveFile = _saves.SaveFile(self._selected_info)
            saveFile.load(progress)
        #--No custom items?
        types_set = Save_EditCreated.rec_types[self.save_rec_type]
        if not any(rec._rec_sig in types_set for rec in
                   saveFile.created.values()):
            self._showOk(_(u'No items to edit.'))
            return
        #--Open editor dialog
        secd = Save_EditCreatedData(self.window,saveFile,types_set)
        balt.ListEditor.display_dialog(self.window, self._text, secd)

#------------------------------------------------------------------------------
class Save_EditPCSpellsData(balt.ListEditorData):
    """Data capsule for pc spell editing dialog."""
    def __init__(self,parent,saveInfo):
        """Initialize."""
        self.saveSpells = _saves.SaveSpells(saveInfo)
        with balt.Progress(_(u'Loading Masters')) as progress:
            self.saveSpells.load_data(progress, bosh.modInfos)
        self.player_spells = self.saveSpells.getPlayerSpells()
        self.removed = set()
        #--GUI
        balt.ListEditorData.__init__(self,parent)
        self.showRemove = True
        self.showInfo = True
        self.showSave = True
        self.showCancel = True

    def getItemList(self):
        """Returns load list keys in alpha order."""
        return sorted(self.player_spells, key=lambda a: a.lower())

    def getInfo(self,item):
        """Returns string info on specified item."""
        iref,record = self.player_spells[item]
        return record.getEffectsSummary()

    def remove(self,item):
        """Removes item. Return true on success."""
        if not item in self.player_spells: return False
        iref,record = self.player_spells[item]
        self.removed.add(iref)
        del self.player_spells[item]
        return True

    def save(self):
        """Handles save button click."""
        self.saveSpells.removePlayerSpells(self.removed)

#------------------------------------------------------------------------------
class Save_EditPCSpells(OneItemLink):
    """Save spell list editing dialog."""
    _text = _('Delete Spells…')
    _help = _('Delete unused spells from your spell list in the selected save.'
              ' Warning: This cannot be undone.')

    def Execute(self):
        pc_spell_data = Save_EditPCSpellsData(self.window, self._selected_info)
        balt.ListEditor.display_dialog(self.window, _(u'Player Spells'),
                                       pc_spell_data)

#------------------------------------------------------------------------------
class Save_EditCreatedEnchantmentCosts(OneItemLink):
    """Dialog and Menu for setting number of uses for Cast When Used Enchantments."""
    _text = _('Set Number of Uses for Weapon Enchantments…')
    _help = _(u'Set number of uses for Cast When Used Enchantments')

    def Execute(self):
        msg = _('Enter the number of uses you desire per recharge for all '
              'custom made enchantments.') + '\n' + _(
            '(Enter 0 for unlimited uses)')
        dialog = self._askNumber(msg, prompt=_('Uses'), title=_(
            'Number of Uses'), initial_num=50, min_num=0, max_num=10000)
        if dialog is None: return
        Enchantments = _saves.SaveEnchantments(self._selected_info)
        Enchantments.load_data()
        Enchantments.setCastWhenUsedEnchantmentNumberOfUses(dialog)

#------------------------------------------------------------------------------
class Save_Move(ChoiceLink):
    """Moves or copies selected files to alternate profile."""

    def __init__(self, copyMode=False):
        super(Save_Move, self).__init__()
        self.copyMode = copyMode
        self._help_str = (_('Copy the selected saves to %(save_profile)s.')
                          if copyMode else
                          _('Copy the selected saves to %(save_profile)s.'))

    @property
    def _choices(self): return initialization.getLocalSaveDirs()

    def _initData(self, window, selection):
        super(Save_Move, self)._initData(window, selection)
        saves_dir = bosh.saveInfos.localSave
        _self = self
        class _Default(EnabledLink):
            _text = _('Default')
            _help = _self._help_str % {
                'save_profile': bush.game.Ini.save_prefix}
            def _enable(self):
                return saves_dir != bush.game.Ini.save_prefix
            def Execute(self): _self.MoveFiles(profile=None)
        class _SaveProfileLink(EnabledLink):
            @property
            def link_help(self):
                return _self._help_str % {
                    'save_profile': os.path.join(
                        bush.game.Ini.save_prefix, self._text)}
            def _enable(self):
                return saves_dir != _win_join(self._text)
            def Execute(self): _self.MoveFiles(profile=self._text)
        self.__class__.choiceLinkType = _SaveProfileLink
        self.extraItems = [_Default()]

    def MoveFiles(self, profile: str | None):
        destDir = bass.dirs['saveBase'].join('Saves')
        if profile is not None:
            destDir = destDir.join(profile)
        if destDir == bosh.saveInfos.store_dir:
            self._showError(_(u"You can't move saves to the current profile!"))
            return
        try:
            count = self._move_saves(destDir, profile)
        finally:
            if not self.copyMode: # files moved to other profile, refresh
                if moved := bosh.saveInfos.check_existence(
                        self.iselected_infos()):
                    bosh.saveInfos.refresh(RefrIn(del_infos=moved))
                self.window.RefreshUI(RefrData(to_del=moved))
        profile_rel = os.path.relpath(destDir, bass.dirs['saveBase'])
        msg = (_('%(num_save_files)d files copied to %(save_profile)s.')
               if self.copyMode else
               _('%(num_save_files)d files moved to %(save_profile)s.'))
        self._showInfo(msg % {'num_save_files': count,
                              'save_profile': profile_rel},
            title=_('Saves Copied') if self.copyMode else _('Saves Moved'))

    def _move_saves(self, destDir, profile: str | None):
        #--bashDir
        destTable = bolt.DataTable(destDir.join('Bash', 'Table.dat'),
                                   load_pickle=True)
        count = do_save = 0
        ask = True
        for fileName, save_inf in self.iselected_pairs():
            if ask and destDir.join(fileName).exists():
                profile_dir = bush.game.Ini.save_prefix
                if profile is not None:
                    profile_dir = os.path.join(profile_dir, profile)
                message = (_('A file named %(conflicting_save)s already '
                             'exists in %(save_profile)s. Overwrite it?') % {
                    'conflicting_save': fileName, 'save_profile': profile_dir})
                result = self._askContinueShortTerm(message,
                                                    title=_(u'Move File'))
                #if result is true just do the job but ask next time if applicable as well
                if not result: continue
                ask = ask and result != 2 # so don't warn for rest of operation
            if self.copyMode:
                save_inf.fs_copy(destDir.join(fileName))
            else:
                save_inf.move_info(destDir)
            if att_dict := save_inf.get_persistent_attrs(frozenset()):
                destTable.pickled_data[fileName] = att_dict
                do_save = 1
            count += 1
        if do_save: destTable.save()
        return count

#------------------------------------------------------------------------------
class Save_RepairAbomb(OneItemLink):
    """Repairs animation slowing by resetting counter(?) at end of TesClass
    data."""
    _text = _(u'Repair Abomb')
    _help = _(u'Repair animation slowing')

    def Execute(self):
        #--File Info
        fileInfo = self._selected_info
        #--Check current value
        saveFile = _saves.SaveFile(fileInfo)
        saveFile.load()
        (tcSize,abombCounter,abombFloat) = saveFile.getAbomb()
        #--Continue?
        progress = 100 * abombFloat / 524288.0 # 0x49000000 cast to a float
        newCounter = 0x41000000
        if abombCounter <= newCounter:
            self._showOk(_(u'Abomb counter is too low to reset.'))
            return
        msg = '\n\n'.join([
            _('Reset Abomb counter (current progress: '
              '%(abomb_progress)s)?') % {'abomb_progress': f'{progress:.0f}%'},
            _("Note: Abomb animation slowing won't occur until progress is "
              "near %(critical_pct)s.") % {'critical_pct': '100%'}])
        if self._askYes(msg, title=_('Repair Abomb'), default_is_yes=False):
            saveFile.setAbomb(newCounter)
            saveFile.safeSave()
            self._showOk(_(u'Abomb counter reset.'))

#------------------------------------------------------------------------------
class Save_RepairHair(OneItemLink):
    """Repairs hair that has been zeroed due to removal of a hair mod."""
    _text = _(u'Repair Hair')
    _help = _(u'Repair hair that has been zeroed due to removal of a hair mod.')

    def Execute(self):
        #--File Info
        if bosh.faces.PCFaces.save_repairHair(self._selected_info):
            self._showOk(_(u'Hair repaired.'))
        else:
            self._showOk(_(u'No repair necessary.'), self._selected_item)

#------------------------------------------------------------------------------
class Save_ReweighPotions(OneItemLink):
    """Changes weight of all player potions to specified value."""
    _text = _('Reweigh Potions…')
    _help = _(u'Change weight of all player potions to specified value')

    def Execute(self):
        #--Query value
        default = u'%0.2f' % (bass.settings.get(
            u'bash.reweighPotions.newWeight', 0.2),)
        newWeight = self._askText(
            _('Set weight of all player-created potions to:'),
            default=default, title=_('Reweigh Potions'))
        if not newWeight: return
        try:
            newWeight = float(newWeight)
            if newWeight < 0 or newWeight > 100: raise ValueError
        except ValueError:
            self._showError(_('Invalid weight: %(invalid_weight)s') % {
                'invalid_weight': newWeight}, title=_('Reweigh Potions'))
            return
        bass.settings[u'bash.reweighPotions.newWeight'] = newWeight
        #--Do it
        with balt.Progress(_(u'Reweigh Potions')) as progress:
            saveFile = _saves.SaveFile(self._selected_info)
            saveFile.load(SubProgress(progress,0,0.5))
            count = 0
            progress(0.5,_(u'Processing.'))
            for rfid, record in saveFile.created.items():
                if record._rec_sig == b'ALCH':
                    record = record.getTypeCopy()
                    record.weight = newWeight
                    record.getSize()
                    saveFile.created[rfid] = record
                    count += 1
            if count:
                saveFile.safeSave(SubProgress(progress,0.6,1.0))
                progress.Destroy()
                self._showOk(_('Potions reweighed: %(num_reweighed)d.') % {
                    'num_reweighed': count}, title=_('Reweigh Potions'))
            else:
                progress.Destroy()
                self._showOk(_('No potions to reweigh!'),
                    title=_('Reweigh Potions'))

#------------------------------------------------------------------------------
class Save_Stats(OneItemLink):
    """Show savefile statistics."""
    _text = _(u'Statistics')
    _help = _(u'Show savefile statistics')

    def Execute(self):
        saveFile = _saves.SaveFile(self._selected_info)
        with balt.Progress(_(u'Statistics')) as progress:
            saveFile.load(SubProgress(progress,0,0.9))
            log = bolt.LogFile(io.StringIO())
            progress(0.9,_(u'Calculating statistics.'))
            saveFile.logStats(log)
            progress.Destroy()
            statslog = log.out.getvalue()
            self._showLog(statslog, title=self._selected_item)

#------------------------------------------------------------------------------
class _Save_StatCosave(AppendableLink, OneItemLink):
    """Base for xSE and pluggy cosaves stats menus"""
    def _enable(self):
        if not super(_Save_StatCosave, self)._enable(): return False
        self._cosave = self._get_cosave()
        return bool(self._cosave)

    def _get_cosave(self):
        raise NotImplementedError

    def Execute(self):
        with BusyCursor():
            log = bolt.LogFile(io.StringIO())
            self._cosave.dump_to_log(log, self._selected_info.header.masters)
            logtxt = log.out.getvalue()
        self._showLog(logtxt, title=self._cosave.abs_path.tail)

#------------------------------------------------------------------------------
class Save_StatObse(_Save_StatCosave):
    """Dump .obse records."""
    _text = _('Dump %(co_ext)s Contents') % {
        'co_ext': bush.game.Se.cosave_ext.lower()}
    _help = _('Create a report of the contents of the associated %(xse_abbr)s '
              'cosave.') % {'xse_abbr': bush.game.Se.se_abbrev}

    def _get_cosave(self):
        return self._selected_info.get_xse_cosave()

    def _append(self, window): return bool(bush.game.Se.se_abbrev)

#------------------------------------------------------------------------------
class Save_StatPluggy(_Save_StatCosave):
    """Dump Pluggy blocks from .pluggy files."""
    _text = _(u'Dump .pluggy Contents')
    _help = _(u'Dumps contents of associated Pluggy cosave into a log.')

    def _get_cosave(self):
        return self._selected_info.get_pluggy_cosave()

    def _append(self, window): return bush.game.has_standalone_pluggy

#------------------------------------------------------------------------------
class Save_Unbloat(OneItemLink):
    """Unbloats savegame."""
    _text = _('Remove Bloat…')
    _help = _('Unbloat savegame. Experimental ! Back up your saves before '
              'using it on them')

    def Execute(self):
        #--File Info
        with balt.Progress(_(u'Scanning for Bloat')) as progress:
            #--Scan and report
            saveFile = _saves.SaveFile(self._selected_info)
            saveFile.load(SubProgress(progress,0,0.8))
            createdCounts,nullRefCount = saveFile.findBloating(SubProgress(progress,0.8,1.0))
        #--Dialog
        if not createdCounts and not nullRefCount:
            self._showOk(_(u'No bloating found.'), self._selected_item)
            return
        msg = [_('Remove savegame bloating?')]
        if createdCounts:
            for (created_item_rec_type, rec_full), count_ in sorted(
                    createdCounts.items()):
                msg.append(f'  {created_item_rec_type} {rec_full}: {count_}')
        if nullRefCount:
            msg.append('  ' + _('Null Reference Objects: %(num_ref_objs)d') % {
                'num_ref_objs': nullRefCount})
        msg.append('')
        msg.append(_('WARNING: This is a risky procedure that may corrupt '
                     'your savegame! Use it only if necessary!'))
        if not self._askYes('\n'.join(msg), _('Remove bloating?')):
            return
        #--Remove bloating
        with balt.Progress(_('Removing Bloat')) as progress:
            nums = saveFile.removeBloating(createdCounts,True,SubProgress(progress,0,0.9))
            progress(0.9,_('Saving…'))
            saveFile.safeSave()
        msg = [_('Uncreated Objects: %(num_uncreated_objs)d'),
               _('Uncreated References: %(num_uncreated_refs)d'),
               _('Un-nulled Refs: %(num_unnulled_refs)d')]
        self._showOk('\n'.join(msg) % {'num_uncreated_objs': nums[0],
                                       'num_uncreated_refs': nums[1],
                                       'num_unnulled_refs': nums[2]},
            self._selected_item)
        self.refresh_sel()

#------------------------------------------------------------------------------
class Save_UpdateNPCLevels(EnabledLink):
    """Update NPC levels from active mods."""
    _text = _('Update NPC Levels…')
    _help = _(u'Update NPC levels from active mods')

    def _enable(self): return bool(load_order.cached_active_tuple())

    def Execute(self):
        msg = _('This will relevel the NPCs in the selected saves according '
                'to the NPC levels in the currently active plugins. This '
                'supersedes the older "Import NPC Levels" command.')
        if not self._askContinue(msg, u'bash.updateNpcLevels.continue',
                                 _(u'Update NPC Levels')): return
        with balt.Progress(_(u'Update NPC Levels')) as progress:
            #--Loop over active mods
            npc_info = {}
            lf = LoadFactory(False, by_sig=[b'NPC_'])
            ordered = list(load_order.cached_active_tuple())
            subProgress = SubProgress(progress,0,0.4,len(ordered))
            modErrors = []
            for index,modName in enumerate(ordered):
                subProgress(index, _('Scanning %(scanning_plugin)s') % {
                    'scanning_plugin': modName})
                modInfo = bosh.modInfos[modName]
                modFile = ModFile(modInfo, lf)
                try:
                    modFile.load_plugin()
                except ModError as x:
                    modErrors.append(f'{x}')
                    continue
                if not (npc_block := modFile.tops.get(b'NPC_')): continue
                #--Loop over mod NPCs
                mapToOrdered = MasterMap(modFile.augmented_masters(), ordered)
                for rid, npc in npc_block.iter_present_records():
                    fid = mapToOrdered(rid, None)
                    if not fid: continue
                    npc_info[fid] = (npc.eid, npc.level_offset,
                                     npc.calc_min_level, npc.calc_max_level,
                                     npc.npc_flags.pc_level_offset)
            #--Loop over savefiles
            subProgress = SubProgress(progress,0.4,1.0,len(self.selected))
            msg = [_(u'NPCs Releveled:')]
            for index, saveInfo in enumerate(self.iselected_infos()):
                subProgress(index, _('Updating %(updating_save)s') % {
                    'updating_save': saveInfo})
                saveFile = _saves.SaveFile(saveInfo)
                saveFile.load()
                mapToOrdered = MasterMap(saveFile._masters, ordered)
                releveledCount = 0
                #--Loop over change records
                fid_rec = saveFile.fid_recNum
                for recId, (rec_kind, recFlags, version, rdata) in \
                        fid_rec.items():
                    orderedRecId = mapToOrdered(recId, None)
                    if (rec_kind != 35 or recId == 7 or
                            orderedRecId not in npc_info):
                        continue
                    eid, info_lo, info_min_lv, info_max_lv, info_pc_lo = \
                        npc_info[orderedRecId]
                    npc = _saves.SreNPC(recFlags, rdata)
                    acbs = npc.acbs
                    if acbs and (acbs.level_offset != info_lo or
                                 acbs.calc_min_level != info_min_lv or
                                 acbs.calc_max_level != info_max_lv or
                                 acbs.npc_flags.pc_level_offset != info_pc_lo):
                        acbs.level_offset = info_lo
                        acbs.calc_min_level = info_min_lv
                        acbs.calc_max_level = info_max_lv
                        acbs.npc_flags.pc_level_offset = info_pc_lo
                        releveledCount += 1
                        fid_rec[recId] = npc.getTuple(version)
                #--Save changes?
                subProgress(index + 0.5, _('Updating %(updating_save)s') % {
                    'updating_save': saveInfo})
                if releveledCount:
                    saveFile.safeSave()
                msg.append(f'{releveledCount:d} {saveInfo}')
        if modErrors:
            msg.append('\n' + _('Some mods had load errors and were skipped:'))
            msg.append('* ' + '\n* '.join(modErrors))
        self._showOk('\n'.join(msg), _(u'Update NPC Levels'))
