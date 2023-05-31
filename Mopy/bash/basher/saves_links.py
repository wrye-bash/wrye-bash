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

"""Menu items for the main and item menus of the saves tab - their window
attribute points to BashFrame.saveList singleton."""

import io
import re
import shutil

from . import BashFrame
from .dialogs import ImportFaceDialog
from .. import balt, bass, bolt, bosh, bush, initialization, load_order
from ..balt import AppendableLink, CheckLink, ChoiceLink, EnabledLink, \
    ItemLink, Link, OneItemLink, SeparatorLink
from ..bolt import FName, GPath, Path, SubProgress
from ..bosh import _saves, faces
from ..brec import ShortFidWriteContext
from ..exception import ArgumentError, BoltError, ModError
from ..gui import BusyCursor, FileSave, ImageWrapper, askText, showError, \
    askYes, showOk
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
        balt.ListEditorData.__init__(self,parent)
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
        return bosh.saveInfos.get_profile_attr(profileSaves, u'info',
                                               _(u'About %s:') % item)
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
            Link.Frame.saveList.set_local_save(newSaves, refreshSaveInfos=True)
        bosh.saveInfos.rename_profile(oldSaves, newSaves)
        return newName

    def _validate_prof_name(self, newName):
        #--Error checks
        if not newName: return False
        lowerNames = {save_dir.lower() for save_dir in self.getItemList()}
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
            message = _('Delete profile %s and the %d save files it '
                        'contains?') % (profile, len(files))
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
            profile_dir = Saves_Profiles._my_games.join(self._text)
            return _(u'Set profile to %s (%s)') % (self._text, profile_dir)
        @property
        def relativePath(self): return _win_join(self._text)
        def _check(self): return bosh.saveInfos.localSave == self.relativePath
        def _enable(self): return not self._check()
        def Execute(self):
            arcSaves = bosh.saveInfos.localSave
            newSaves = self.relativePath
            with BusyCursor():
                Link.Frame.saveList.set_local_save(newSaves, refreshSaveInfos=False)
                bosh.modInfos.swapPluginsAndMasterVersion(arcSaves, newSaves)
                Link.Frame.modList.RefreshUI(refreshSaves=False,
                                             focus_list=False)
                bosh.saveInfos.refresh()
                self.window.DeleteAll() # let call below repopulate
                self.window.RefreshUI(detail_item=None)
                self.window.panel.ShowPanel()
                Link.Frame.warn_corrupted(warn_saves=True)

    choiceLinkType = _ProfileLink

    class _Default(_ProfileLink):
        _text = _(u'Default')

        @property
        def link_help(self):
            profile_dir = Saves_Profiles._my_games.join(
                bush.game.Ini.save_prefix)
            return _(u'Set profile to the default (%s).') % profile_dir

        @property
        def relativePath(self): return bush.game.Ini.save_prefix

    class _Edit(ItemLink):
        _text = _(u'Edit Profiles...')
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
        BashFrame.modList.RefreshUI(refreshSaves=True, focus_list=False)
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
    _text = _(u'Import Face...')
    _help = _(u'Import a face from another save')

    @balt.conversation
    def Execute(self):
        #--Select source face file
        srcDir = self._selected_info.info_dir
        exts = u';*'.join(bush.game.espm_extensions | {
            bush.game.Ess.ext, bush.game.Ess.ext[-1] + u'r'})
        wildcard = _('%s Files') % bush.game.displayName + \
                   f' (*{exts})|*{exts}'
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
                self._showOk(_(u'No player (PC) faces found in %s.') % fname,
                             fname)
                return
        else: return
        #--Dialog
        ImportFaceDialog.display_dialog(self.window, fname,
                                        self._selected_info, srcFaces)

#------------------------------------------------------------------------------
class Save_RenamePlayer(ItemLink):
    """Renames the Player character in a save game."""
    _text = _(u'Rename Player...')
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
        self.window.RefreshUI(redraw=self.selected)

#------------------------------------------------------------------------------
class Save_ExportScreenshot(OneItemLink):
    """Exports the saved screenshot from a save game."""
    _text = _(u'Export Screenshot...')
    _help = _(u'Export the saved screenshot from a save game')

    def Execute(self):
        imagePath = FileSave.display_dialog(Link.Frame,
            _(u'Save Screenshot as:'), bass.dirs[u'patches'].s,
            _(u'Screenshot %s.jpg') % self._selected_item, u'*.jpg')
        if not imagePath: return
        # TODO(inf) de-wx! All the image stuff is still way too close to wx
        image = ImageWrapper.bmp_from_bitstream(
            *self._selected_info.header.image_parameters).ConvertToImage()
        image.SaveFile(imagePath.s, ImageWrapper.img_types['.jpg'])

#------------------------------------------------------------------------------
##: Split in two, one OneItemLink diffing against active plugins and one link
# that needs two or more plugins and diffs those against each other
class Save_DiffMasters(EnabledLink):
    """Shows how saves masters differ from active mod list."""
    _text = _(u'Diff Masters...')
    _help = _(u'Show how the masters of a save differ from active mod list or'
             u' another save')

    def _enable(self): return len(self.selected) in (1,2)

    def Execute(self):
        oldNew = self.selected
        oldNew.sort(key=lambda x: bosh.saveInfos[x].mtime)
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
                message += u'=== '+_(u'Removed Masters')+u' (%s):\n* ' % oldName
                message += u'\n* '.join(load_order.get_ordered(missing))
                if added: message += u'\n\n'
            if added:
                message += u'=== ' + _(u'Added Masters') + f' ({newName}):\n* '
                message += u'\n* '.join(load_order.get_ordered(added))
            self._showWryeLog(message, title=_(u'Diff Masters'))

#------------------------------------------------------------------------------
class Save_Renumber(EnabledLink):
    """Renumbers a whole lot of save files."""
    _text = _('Renumber Saves...')
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
        old_names = set()
        new_names = set()
        for s_groups, sinf in self._matches:
            # We have to pass the root, so strip off the extension
            ofn_root = FName(s_groups[2]).fn_body
            nfn_save = FName(f'{s_groups[0]}{nfn_number:d}{ofn_root}')
            if nfn_save != sinf.fn_key.fn_body:
                if not self.window.try_rename(sinf, nfn_save, new_names,
                                              old_names):
                    break
                nfn_number += 1
        if new_names:
            self.window.RefreshUI(redraw=new_names, to_del=old_names)
            self.window.SelectItemsNoCallback(new_names)

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

    _attrs = {b'CLOT': (f'{_("Clothing")}\n{_("Flags: ")}', ()), b'ARMO': (
        f'{_("Armor")}\n{_("Flags: ")}', ('strength', 'value', 'weight')),
              b'WEAP': ('', ('damage', 'value', 'speed', 'reach', 'weight'))}
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
                buff.append(info_str + ', '.join(
                    record.biped_flags.getTrueAttrs()))
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
            showOk(self.parent, _('Names modified: %d.') % count,
                   self.saveFile.fileInfo.fn_key)

#------------------------------------------------------------------------------
class Save_EditCreated(OneItemLink):
    """Allows user to rename custom items (spells, enchantments, etc)."""
    menuNames = {b'ENCH':_(u'Rename Enchanted...'),
                 b'SPEL':_(u'Rename Spells...'),
                 b'ALCH':_(u'Rename Potions...')
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
        with balt.Progress(_(u'Loading...')) as progress:
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
    _text = _(u'Delete Spells...')
    _help = _(u'Delete unused spells from your spell list in the selected save.'
             u' Warning: This cannot be undone')

    def Execute(self):
        pc_spell_data = Save_EditPCSpellsData(self.window, self._selected_info)
        balt.ListEditor.display_dialog(self.window, _(u'Player Spells'),
                                       pc_spell_data)

#------------------------------------------------------------------------------
class Save_EditCreatedEnchantmentCosts(OneItemLink):
    """Dialog and Menu for setting number of uses for Cast When Used Enchantments."""
    _text = _(u'Set Number of Uses for Weapon Enchantments...')
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
    local = None

    def __init__(self, copyMode=False):
        super(Save_Move, self).__init__()
        self.copyMode = copyMode
        self._help_str = _(u'Copy save(s) to %s') if copyMode else _(
            u'Move save(s) to %s')

    @property
    def _choices(self): return initialization.getLocalSaveDirs()

    def _initData(self, window, selection):
        super(Save_Move, self)._initData(window, selection)
        Save_Move.local = bosh.saveInfos.localSave
        _self = self
        class _Default(EnabledLink):
            _text = _(u'Default')
            _help = _self._help_str % bass.dirs[u'saveBase'].join(
                bush.game.Ini.save_prefix)
            def _enable(self):
                return Save_Move.local != bush.game.Ini.save_prefix
            def Execute(self): _self.MoveFiles(_(u'Default'))
        class _SaveProfileLink(EnabledLink):
            @property
            def link_help(self):
                return _self._help_str % bass.dirs[u'saveBase'].join(
                    bush.game.Ini.save_prefix, self._text)
            def _enable(self):
                return Save_Move.local != _win_join(self._text)
            def Execute(self): _self.MoveFiles(self._text)
        self.__class__.choiceLinkType = _SaveProfileLink
        self.extraItems = [_Default()]

    def MoveFiles(self,profile):
        destDir = bass.dirs[u'saveBase'].join(u'Saves')
        if profile != _(u'Default'):
            destDir = destDir.join(profile)
        if destDir == bosh.saveInfos.store_dir:
            self._showError(_(u"You can't move saves to the current profile!"))
            return
        try:
            count = self._move_saves(destDir, profile)
        finally:
            if not self.copyMode: # files moved to other profile, refresh
                moved = bosh.saveInfos.delete_refresh(self.selected, None,
                                                      check_existence=True)
                self.window.RefreshUI(to_del=moved)
        msg = (_(u'%d files copied to %s.') if self.copyMode else _(
            u'%d files moved to %s.')) % (count, profile)
        self._showInfo(msg, title=_(u'Copy File'))

    def _move_saves(self, destDir, profile):
        savesTable = bosh.saveInfos.table
        #--bashDir
        destTable = bolt.DataTable(bolt.PickleDict(destDir.join(
            u'Bash', u'Table.dat')))
        count = 0
        ask = True
        for fileName in self.selected:
            if ask and destDir.join(fileName).exists():
                message = (_(u'A file named %s already exists in %s. Overwrite it?')
                    % (fileName,profile))
                result = self._askContinueShortTerm(message,
                                                    title=_(u'Move File'))
                #if result is true just do the job but ask next time if applicable as well
                if not result: continue
                elif result == 2: ask = False #so don't warn for rest of operation
            if self.copyMode:
                bosh.saveInfos.copy_info(fileName, destDir)
                if fileName in savesTable:
                    destTable[fileName] = savesTable[fileName]
            else:
                bosh.saveInfos.move_info(fileName, destDir)
                if fileName in savesTable:
                    destTable[fileName] = savesTable.pop(fileName)
            count += 1
        destTable.save()
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
        message = _('Reset Abomb counter? (Current progress: %.0f%%.)'
                    ) % progress
        message += '\n\n' + _("Note: Abomb animation slowing won't occur "
                              "until progress is near 100%.")
        if self._askYes(message, _('Repair Abomb'), default_is_yes=False):
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
    _text = _(u'Reweigh Potions...')
    _help = _(u'Change weight of all player potions to specified value')

    def Execute(self):
        #--Query value
        default = u'%0.2f' % (bass.settings.get(
            u'bash.reweighPotions.newWeight', 0.2),)
        newWeight = self._askText(_(u'Set weight of all player potions to...'),
                                  title=_(u'Reweigh Potions'), default=default)
        if not newWeight: return
        try:
            newWeight = float(newWeight)
            if newWeight < 0 or newWeight > 100: raise ValueError
        except ValueError:
            self._showOk(_(u'Invalid weight: %s') % newWeight)
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
                self._showOk(_(u'Potions reweighed: %d.') % count,
                             self._selected_item)
            else:
                progress.Destroy()
                self._showOk(_(u'No potions to reweigh!'), self._selected_item)

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
            self._showLog(statslog, title=self._selected_item, fixedFont=False)

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
        self._showLog(logtxt, title=self._cosave.abs_path.tail,
                      fixedFont=False)

#------------------------------------------------------------------------------
class Save_StatObse(_Save_StatCosave):
    """Dump .obse records."""
    _text = _(u'Dump %s Contents') % bush.game.Se.cosave_ext.lower()
    _help = _(u'Dumps contents of associated %s cosave into a log.') % \
            bush.game.Se.se_abbrev

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
    _text = _('Remove Bloat...')
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
        message = [_(u'Remove savegame bloating?')]
        if createdCounts:
            for (created_item_rec_type, rec_full), count_ in sorted(
                    createdCounts.items()):
                message.append(u'  %s %s: %u' % (
                    created_item_rec_type, rec_full, count_))
        if nullRefCount:
            message.append(f'  {_("Null Ref Objects:")} {nullRefCount:d}')
        message.extend(['', _('WARNING: This is a risky procedure that may '
            'corrupt your savegame!  Use only if necessary!')])
        if not self._askYes('\n'.join(message), _('Remove bloating?')):
            return
        #--Remove bloating
        with balt.Progress(_(u'Removing Bloat')) as progress:
            nums = saveFile.removeBloating(createdCounts,True,SubProgress(progress,0,0.9))
            progress(0.9,_(u'Saving...'))
            saveFile.safeSave()
        self._showOk((_(u'Uncreated Objects: %d') + u'\n' +
                      _(u'Uncreated Refs: %d') + u'\n' +
                      _(u'UnNulled Refs: %d')) % nums, self._selected_item)
        self.window.RefreshUI(redraw=[self._selected_item])

#------------------------------------------------------------------------------
class Save_UpdateNPCLevels(EnabledLink):
    """Update NPC levels from active mods."""
    _text = _(u'Update NPC Levels...')
    _help = _(u'Update NPC levels from active mods')

    def _enable(self): return bool(load_order.cached_active_tuple())

    def Execute(self):
        msg = _('This will relevel the NPCs in the selected save game(s) '
                'according to the npc levels in the currently active mods.  '
                'This supersedes the older "Import NPC Levels" command.')
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
                subProgress(index, _(u'Scanning %s') % modName)
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
                    fid = mapToOrdered(rid.short_fid, None)
                    if not fid: continue
                    npc_info[fid] = (npc.eid, npc.level_offset, npc.calcMin,
                                     npc.calcMax, npc.flags.pcLevelOffset)
            #--Loop over savefiles
            subProgress = SubProgress(progress,0.4,1.0,len(self.selected))
            msg = [_(u'NPCs Releveled:')]
            for index, saveInfo in enumerate(self.iselected_infos()):
                subProgress(index, _('Updating %s') % saveInfo)
                saveFile = _saves.SaveFile(saveInfo)
                saveFile.load()
                mapToOrdered = MasterMap(saveFile._masters, ordered)
                releveledCount = 0
                #--Loop over change records
                fid_rec = saveFile.fid_recNum
                for recId, (rec_kind, recFlags, version, rdata) in \
                        fid_rec.items():
                    orderedRecId = mapToOrdered(recId,None)
                    if rec_kind != 35 or recId == 7 or orderedRecId not in \
                            npc_info: continue
                    eid, level_offset, calcMin, calcMax, pcLevelOffset = \
                        npc_info[orderedRecId]
                    npc = _saves.SreNPC(recFlags, rdata)
                    acbs = npc.acbs
                    if acbs and (acbs.level_offset != level_offset or
                                 acbs.calcMin != calcMin or
                                 acbs.calcMax != calcMax or
                                 acbs.flags.pcLevelOffset != pcLevelOffset):
                        acbs.flags.pcLevelOffset = pcLevelOffset
                        acbs.level_offset = level_offset
                        acbs.calcMin = calcMin
                        acbs.calcMax = calcMax
                        releveledCount += 1
                        fid_rec[recId] = npc.getTuple(version)
                #--Save changes?
                subProgress(index + 0.5, _('Updating %s') % saveInfo)
                if releveledCount:
                    saveFile.safeSave()
                msg.append(f'{releveledCount:d} {saveInfo}')
        if modErrors:
            msg.append('\n' + _('Some mods had load errors and were skipped:'))
            msg.append('* ' + '\n* '.join(modErrors))
        self._showOk('\n'.join(msg), _(u'Update NPC Levels'))
