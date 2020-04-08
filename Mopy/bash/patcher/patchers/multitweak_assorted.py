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

"""This module contains oblivion multitweak item patcher classes that belong
to the Assorted Multitweaker - as well as the AssortedTweaker itself."""
from __future__ import division
import random
import re
from collections import Counter
# Internal
from ... import bush, load_order
from ...bolt import GPath, deprint, floats_equal
from ...cint import MGEFCode
from ...exception import AbstractError
from ...patcher.base import AMultiTweakItem
from ...patcher.patchers.base import MultiTweakItem, CBash_MultiTweakItem
from ...patcher.patchers.base import MultiTweaker, CBash_MultiTweaker

# Patchers: 30 ----------------------------------------------------------------
class _AAssortedTweak(AMultiTweakItem):
    """Hasty abstraction over PBash/CBash records differences to allow moving
    wants_record overrides into the abstract classes."""
    @staticmethod
    def _any_body_flag_set(record):
        """Checks if any body flag but the right ring flag is set. If only the
        right ring and no other body flags are set, then this is probably a
        token that wasn't zeroed (which there are a lot of)."""
        raise AbstractError(u'_any_body_flag_set not implemented')

    @staticmethod
    def _is_nonplayable(record):
        """Returns True if the specified record is marked as nonplayable."""
        raise AbstractError(u'_is_nonplayable not implemented')

    @staticmethod
    def _is_scroll(record):
        """Returns True if this record has the 'is scroll' flag set."""
        raise AbstractError(u'_is_scroll not implemented')

class _AssortPTweak(_AAssortedTweak, MultiTweakItem):
    """An assorted PBash tweak."""
    @staticmethod
    def _any_body_flag_set(record):
        return (record.flags.leftRing or record.flags.foot or
                record.flags.hand or record.flags.amulet or
                record.flags.lowerBody or record.flags.upperBody or
                record.flags.head or record.flags.hair or
                record.flags.tail or record.flags.shield)

    @staticmethod
    def _is_nonplayable(record):
        return record.flags.notPlayable

    @staticmethod
    def _is_scroll(record):
        return record.flags.isScroll

class _AssortCTweak(_AAssortedTweak, CBash_MultiTweakItem):
    """An assorted CBash tweak."""
    @staticmethod
    def _any_body_flag_set(record):
        return (record.IsLeftRing or record.IsFoot or record.IsHand or
                record.IsAmulet or record.IsLowerBody or record.IsUpperBody or
                record.IsHead or record.IsHair or record.IsTail or
                record.IsShield)

    @staticmethod
    def _is_nonplayable(record):
        return record.IsNonPlayable

    @staticmethod
    def _is_scroll(record):
        return record.IsScroll

#------------------------------------------------------------------------------
class _AShowsTweak(_AAssortedTweak):
    """Shared parts of CBash/PBash show clothing/armor tweaks."""
    _hides_bit = None # override in implementations

    def wants_record(self, record):
        return (int(record.flags) >> self._hides_bit & 1 # CBash/PBash-agnostic
                and not self._is_nonplayable(record))

class _PShowsTweak(_AShowsTweak, _AssortPTweak):
    """Shared code of PBash armor/clothing shows tweaks."""
    def buildPatch(self,log,progress,patchFile):
        """Edits patch file as desired. Will write to log."""
        count = Counter()
        keep = patchFile.getKeeper()
        for record in getattr(patchFile, self.tweak_read_classes[0]).records:
            if self.wants_record(record):
                record.flags[self._hides_bit] = False
                keep(record.fid)
                count[record.fid[0]] += 1
        self._patchLog(log,count)

class _CShowsTweak(_AShowsTweak, _AssortCTweak):
    """Shared code of CBash armor/clothing shows tweaks."""
    def apply(self,modFile,record,bashTags):
        """Edits patch file as desired."""
        if self.wants_record(record):
            override = record.CopyAsOverride(self.patchFile)
            if override:
                override.flags &= ~(1 << self._hides_bit)
                self.mod_count[modFile.GName] += 1
                record.UnloadRecord()
                record._RecordID = override._RecordID

#------------------------------------------------------------------------------
class _AArmoShowsTweak(_AShowsTweak):
    """Fix armor to show amulets/rings."""
    tweak_read_classes = b'ARMO',
    tweak_log_msg = _(u'Armor Pieces Tweaked: %(total_changed)d')

class _AArmoShowsAmuletsTweak(_AArmoShowsTweak):
    tweak_name = _(u'Armor Shows Amulets')
    tweak_tip = _(u'Prevents armor from hiding amulets.')
    tweak_key = u'armorShowsAmulets'
    _hides_bit = 17

class AssortedTweak_ArmorShows_Amulets(_AArmoShowsAmuletsTweak,
                                       _PShowsTweak): pass
class CBash_AssortedTweak_ArmorShows_Amulets(_AArmoShowsAmuletsTweak,
                                             _CShowsTweak): pass

class _AArmoShowsRingsTweak(_AArmoShowsTweak):
    tweak_name = _(u'Armor Shows Rings')
    tweak_tip = _(u'Prevents armor from hiding rings.')
    tweak_key = u'armorShowsRings'
    _hides_bit = 16

class AssortedTweak_ArmorShows_Rings(_AArmoShowsRingsTweak, _PShowsTweak): pass
class CBash_AssortedTweak_ArmorShows_Rings(_AArmoShowsRingsTweak,
                                           _CShowsTweak): pass

#------------------------------------------------------------------------------
class _AClotShowsTweak(_AShowsTweak):
    """Fix robes, gloves and the like to show amulets/rings."""
    tweak_read_classes = b'CLOT',
    tweak_log_msg = _(u'Clothing Pieces Tweaked: %(total_changed)d')

class _AClotShowsAmuletsTweak(_AClotShowsTweak):
    tweak_name = _(u'Clothing Shows Amulets')
    tweak_tip = _(u'Prevents Clothing from hiding amulets.')
    tweak_key = u'ClothingShowsAmulets'
    _hides_bit = 17

class AssortedTweak_ClothingShows_Amulets(_AClotShowsAmuletsTweak,
                                          _PShowsTweak): pass
class CBash_AssortedTweak_ClothingShows_Amulets(_AClotShowsAmuletsTweak,
                                                _CShowsTweak): pass

class _AClotShowsRingsTweak(_AClotShowsTweak):
    tweak_name = _(u'Clothing Shows Rings')
    tweak_tip = _(u'Prevents Clothing from hiding rings.')
    tweak_key = u'ClothingShowsRings'
    _hides_bit = 16

class AssortedTweak_ClothingShows_Rings(_AClotShowsRingsTweak,
                                        _PShowsTweak): pass
class CBash_AssortedTweak_ClothingShows_Rings(_AClotShowsRingsTweak,
                                              _CShowsTweak): pass

#------------------------------------------------------------------------------
class AAssortedTweak_BowReach(_AAssortedTweak):
    """Fix bows to have reach = 1.0."""
    tweak_read_classes = b'WEAP',
    tweak_name = _(u'Bow Reach Fix')
    tweak_tip = _(u'Fix bows with zero reach (zero reach causes CTDs).')
    tweak_key = u'BowReach'
    tweak_choices = [(u'1.0', u'1.0')]
    tweak_log_msg = _(u'Bows Fixed: %(total_changed)d')
    default_enabled = True

    def wants_record(self, record):
        return record.weaponType == 5 and record.reach <= 0

class AssortedTweak_BowReach(AAssortedTweak_BowReach, _AssortPTweak):
    def buildPatch(self,log,progress,patchFile):
        """Edits patch file as desired. Will write to log."""
        count = Counter()
        keep = patchFile.getKeeper()
        for record in patchFile.WEAP.records:
            if self.wants_record(record):
                record.reach = 1
                keep(record.fid)
                count[record.fid[0]] += 1
        self._patchLog(log,count)

class CBash_AssortedTweak_BowReach(AAssortedTweak_BowReach, _AssortCTweak):
    def apply(self,modFile,record,bashTags):
        """Edits patch file as desired."""
        if self.wants_record(record):
            override = record.CopyAsOverride(self.patchFile)
            if override:
                override.reach = 1.0
                self.mod_count[modFile.GName] += 1
                record.UnloadRecord()
                record._RecordID = override._RecordID

#------------------------------------------------------------------------------
class AAssortedTweak_SkyrimStyleWeapons(_AAssortedTweak):
    """Sets all one handed weapons as blades, two handed weapons as blunt."""
    tweak_read_classes = b'WEAP',
    tweak_name = _(u'Skyrim-style Weapons')
    tweak_tip = _(u'Sets all one handed weapons as blades, two handed weapons '
                  u'as blunt.')
    tweak_key = u'skyrimweaponsstyle'
    tweak_choices = [(u'1.0', u'1.0')]
    tweak_log_msg = _(u'Weapons Adjusted: %(total_changed)d')

    def wants_record(self, record):
        return record.weaponType in (1, 2)

class AssortedTweak_SkyrimStyleWeapons(AAssortedTweak_SkyrimStyleWeapons,
                                       _AssortPTweak):
    def buildPatch(self,log,progress,patchFile):
        """Edits patch file as desired. Will write to log."""
        count = Counter()
        keep = patchFile.getKeeper()
        for record in patchFile.WEAP.records:
            if self.wants_record(record):
                record.weaponType = (3 if record.weaponType == 1 else 0)
                keep(record.fid)
                count[record.fid[0]] += 1
        self._patchLog(log,count)

class CBash_AssortedTweak_SkyrimStyleWeapons(AAssortedTweak_SkyrimStyleWeapons,
                                             _AssortCTweak):
    def apply(self,modFile,record,bashTags):
        """Edits patch file as desired."""
        if self.wants_record(record):
            override = record.CopyAsOverride(self.patchFile)
            if override:
                override.weaponType = (3 if override.weaponType == 1 else 0)
                self.mod_count[modFile.GName] += 1
                record.UnloadRecord()
                record._RecordID = override._RecordID

#------------------------------------------------------------------------------
class AAssortedTweak_ConsistentRings(_AAssortedTweak):
    """Sets rings to all work on same finger."""
    tweak_read_classes = b'CLOT',
    tweak_name = _(u'Right Hand Rings')
    tweak_tip = _(u'Fixes rings to unequip consistently by making them '
                  u'prefer the right hand.')
    tweak_key = u'ConsistentRings'
    tweak_choices = [(u'1.0', u'1.0')]
    tweak_log_msg = _(u'Rings Fixed: %(total_changed)d')
    default_enabled = True

class AssortedTweak_ConsistentRings(AAssortedTweak_ConsistentRings,
                                    _AssortPTweak):
    def wants_record(self, record):
        return record.flags.leftRing

    def buildPatch(self,log,progress,patchFile):
        """Edits patch file as desired. Will write to log."""
        count = Counter()
        keep = patchFile.getKeeper()
        for record in patchFile.CLOT.records:
            if self.wants_record(record):
                record.flags.leftRing = False
                record.flags.rightRing = True
                keep(record.fid)
                count[record.fid[0]] += 1
        self._patchLog(log,count)

class CBash_AssortedTweak_ConsistentRings(AAssortedTweak_ConsistentRings,
                                          _AssortCTweak):
    def wants_record(self, record):
        return record.IsLeftRing

    def apply(self,modFile,record,bashTags):
        """Edits patch file as desired. """
        if self.wants_record(record):
            override = record.CopyAsOverride(self.patchFile)
            if override:
                override.IsLeftRing = False
                override.IsRightRing = True
                self.mod_count[modFile.GName] += 1
                record.UnloadRecord()
                record._RecordID = override._RecordID

#------------------------------------------------------------------------------
_playable_skips = re.compile(
    u'(?:skin)|(?:test)|(?:mark)|(?:token)|(?:willful)|(?:see.*me)|('
    u'?:werewolf)|(?:no wings)|(?:tsaesci tail)|(?:widget)|(?:dummy)|('
    u'?:ghostly immobility)|(?:corpse)', re.I)

class _APlayableTweak(_AAssortedTweak):
    """Shared code of PBash/CBash armor/clothing playable tweaks."""
    def wants_record(self, record):
        if (not self._is_nonplayable(record) or
            not self._any_body_flag_set(record) or record.script): return False
        clothing_name = record.full
        return (clothing_name  # probably truly shouldn't be playable
                and not _playable_skips.search(clothing_name))

class _PPlayableTweak(_APlayableTweak, _AssortPTweak):
    """Shared code of PBash armor/clothing playable tweaks."""
    def buildPatch(self,log,progress,patchFile):
        """Edits patch file as desired. Will write to log."""
        count = Counter()
        keep = patchFile.getKeeper()
        for record in getattr(patchFile, self.tweak_read_classes[0]).records:
            if self.wants_record(record):
                record.flags.notPlayable = 0
                keep(record.fid)
                count[record.fid[0]] += 1
        self._patchLog(log,count)

class _CPlayableTweak(_APlayableTweak, _AssortCTweak):
    """Shared code of CBash armor/clothing playable tweaks."""
    scanOrder = 29 # Run before the show armor/clothing tweaks
    editOrder = 29

    def apply(self,modFile,record,bashTags):
        """Edits patch file as desired. """
        if self.wants_record(record):
            override = record.CopyAsOverride(self.patchFile)
            if override:
                override.IsNonPlayable = False
                self.mod_count[modFile.GName] += 1
                record.UnloadRecord()
                record._RecordID = override._RecordID

#------------------------------------------------------------------------------
class AAssortedTweak_ClothingPlayable(_APlayableTweak):
    """Sets all clothes to playable."""
    tweak_read_classes = b'CLOT',
    tweak_name = _(u'All Clothing Playable')
    tweak_tip = _(u'Sets all clothing to be playable.')
    tweak_key = u'PlayableClothing'
    tweak_choices = [(u'1.0', u'1.0')]
    tweak_log_header = _(u'Playable Clothes')
    tweak_log_msg = _(u'Clothes Set As Playable: %(total_changed)d')

class AssortedTweak_ClothingPlayable(AAssortedTweak_ClothingPlayable,
                                     _PPlayableTweak): pass
class CBash_AssortedTweak_ClothingPlayable(AAssortedTweak_ClothingPlayable,
                                           _CPlayableTweak): pass

#------------------------------------------------------------------------------
class AAssortedTweak_ArmorPlayable(_APlayableTweak):
    """Sets all armors to be playable."""
    tweak_read_classes = b'ARMO',
    tweak_name = _(u'All Armor Playable')
    tweak_tip = _(u'Sets all armor to be playable.')
    tweak_key = u'PlayableArmor'
    tweak_choices = [(u'1.0', u'1.0')]
    tweak_log_header = _(u'Playable Armor')
    tweak_log_msg = _(u'Armor Pieces Set As Playable: %(total_changed)d')

class AssortedTweak_ArmorPlayable(AAssortedTweak_ArmorPlayable,
                                  _PPlayableTweak): pass
class CBash_AssortedTweak_ArmorPlayable(AAssortedTweak_ArmorPlayable,
                                        _CPlayableTweak): pass

#------------------------------------------------------------------------------
class AAssortedTweak_DarnBooks(_AAssortedTweak):
    """DarNifies books."""
    tweak_read_classes = b'BOOK',
    tweak_name = _(u'DarNified Books')
    tweak_tip = _(u'Books will be reformatted for DarN UI.')
    tweak_key = u'DarnBooks'
    tweak_choices = [(u'default', u'default')]
    tweak_log_msg = _(u'Books DarNified: %(total_changed)d')
    _align_text = {u'^^': u'center', u'<<': u'left', u'>>': u'right'}
    _re_align = re.compile(u'' r'^(<<|\^\^|>>)', re.M)
    _re_bold = re.compile(u'' r'(__|\*\*|~~)')
    _re_color = re.compile(u'<font color="?([a-fA-F0-9]+)"?>', re.I + re.M)
    _re_div = re.compile(u'<div', re.I + re.M)
    _re_head_2 = re.compile(u'' r'^(<<|\^\^|>>|)==\s*(\w[^=]+?)==\s*\r\n',
                            re.M)
    _re_head_3 = re.compile(u'' r'^(<<|\^\^|>>|)===\s*(\w[^=]+?)\r\n', re.M)
    _re_font = re.compile(u'<font', re.I + re.M)
    _re_font_1 = re.compile(u'(<?<font face=1( ?color=[0-9a-zA]+)?>)+',
                            re.I | re.M)
    _re_tag_in_word = re.compile(u'([a-z])<font face=1>', re.M)

    def wants_record(self, record):
        return (record.text and not record.enchantment and
                record.text != self._darnify(record))

    def _darnify(self, record):
        """Darnifies the text of the specified record and returns it as a
        string."""
        self.inBold = False
        # There are some FUNKY quotes that don't translate properly (they are
        # in *latin* encoding, not even cp1252 or something normal but
        # non-unicode). Get rid of those before we blow up.
        rec_text = record.text.replace(u'\u201d', u'')
        if self._re_head_2.match(rec_text):
            rec_text = self._re_head_2.sub(
                u'' r'\1<font face=1 color=220000>\2<font face=3 '
                u'' r'color=444444>\r\n', rec_text)
            rec_text = self._re_head_3.sub(
                u'' r'\1<font face=3 color=220000>\2<font face=3 '
                u'' r'color=444444>\r\n', rec_text)
            rec_text = self._re_align.sub(self._replace_align, rec_text)
            rec_text = self._re_bold.sub(self._replace_bold, rec_text)
            rec_text = re.sub(u'' r'\r\n', u'' r'<br>\r\n', rec_text)
        else:
            ma_color = self._re_color.search(rec_text)
            if ma_color:
                color = ma_color.group(1)
            elif self._is_scroll(record):
                color = u'000000'
            else:
                color = u'444444'
            font_face = u'<font face=3 color='+color+u'>'
            rec_text = self._re_tag_in_word.sub(u'' r'\1', rec_text)
            if (self._re_div.search(rec_text) and
                    not self._re_font.search(rec_text)):
                rec_text = font_face + rec_text
            else:
                rec_text = self._re_font_1.sub(font_face, rec_text)
        return rec_text

    # Helper methods for _darnify
    def _replace_bold(self, mo):
        self.inBold = not self.inBold
        return u'<font face=3 color=%s>' % (
            u'440000' if self.inBold else u'444444')

    def _replace_align(self, mo):
        return u'<div align=%s>' % self._align_text[mo.group(1)]

class AssortedTweak_DarnBooks(AAssortedTweak_DarnBooks, _AssortPTweak):
    def buildPatch(self,log,progress,patchFile):
        """Edits patch file as desired. Will write to log."""
        count = Counter()
        keep = patchFile.getKeeper()
        for record in patchFile.BOOK.records:
            if self.wants_record(record):
                record.text = self._darnify(record)
                keep(record.fid)
                count[record.fid[0]] += 1
        self._patchLog(log,count)

class CBash_AssortedTweak_DarnBooks(AAssortedTweak_DarnBooks, _AssortCTweak):
    def apply(self,modFile,record,bashTags):
        """Edits patch file as desired."""
        if self.wants_record(record):
            override = record.CopyAsOverride(self.patchFile)
            if override:
                override.text = self._darnify(record)
                self.mod_count[modFile.GName] += 1
                record.UnloadRecord()
                record._RecordID = override._RecordID

#------------------------------------------------------------------------------
class AAssortedTweak_FogFix(_AAssortedTweak):
    """Fix fog in cell to be non-zero."""
    tweak_name = _(u'Nvidia Fog Fix')
    tweak_tip = _(u'Fix fog related Nvidia black screen problems.')
    tweak_key = u'FogFix'
    tweak_choices = [(u'0.0001', u'0.0001')]
    tweak_log_msg = _(u'Cells With Fog Tweaked To 0.0001: %(total_changed)d')
    default_enabled = True

    def wants_record(self, record):
        # All of these floats must be approximately equal to 0. They can be
        # None in CBash as well, so guard against that.
        for fog_attr in (u'fogNear', u'fogFar', u'fogClip'):
            fog_val = getattr(record, fog_attr)
            if fog_val is not None and not floats_equal(fog_val, 0.0):
                return False
        return True

class AssortedTweak_FogFix(AAssortedTweak_FogFix, _AssortPTweak):
    supports_pooling = False
    tweak_read_classes = b'CELL', b'WRLD', # WRLD is useless, but we want this
    # patcher to run in the same group as the CellImporter, so we'll have to
    # skip worldspaces. It shouldn't be a problem in those CELLs.

    def tweak_scan_file(self, mod_file, patch_file):
        if b'CELL' not in mod_file.tops: return
        should_add_cell = self.wants_record
        add_cell = patch_file.CELL.setCell
        for cell_block in mod_file.CELL.cellBlocks:
            curr_cell = cell_block.cell
            if should_add_cell(curr_cell):
                add_cell(curr_cell)

    def buildPatch(self,log,progress,patchFile):
        """Adds merged lists to patchfile."""
        keep = patchFile.getKeeper()
        count = Counter()
        for cellBlock in patchFile.CELL.cellBlocks:
            cell = cellBlock.cell
            if self.wants_record(cell):
                cell.fogNear = 0.0001
                keep(cell.fid)
                count[cell.fid[0]] += 1
        self._patchLog(log, count)

class CBash_AssortedTweak_FogFix(AAssortedTweak_FogFix, _AssortCTweak):
    tweak_read_classes = b'CELLS', # or CELL, but we want this patcher to
    # run in the same group as the CellImporter, so we'll have to skip
    # worldspaces. It shouldn't be a problem in those CELLs.

    def wants_record(self, record):
        # It's a CELL that showed up because we said CELLS instead of CELL
        return super(CBash_AssortedTweak_FogFix, self).wants_record(
            record) and not record.Parent

    def apply(self,modFile,record,bashTags):
        """Edits patch file as desired."""
        if self.wants_record(record):
            override = record.CopyAsOverride(self.patchFile)
            if override:
                override.fogNear = 0.0001
                self.mod_count[modFile.GName] += 1
                record.UnloadRecord()
                record._RecordID = override._RecordID

#------------------------------------------------------------------------------
class AAssortedTweak_NoLightFlicker(_AAssortedTweak):
    """Remove light flickering for low end machines."""
    tweak_read_classes = b'LIGH',
    tweak_name = _(u'No Light Flicker')
    tweak_tip = _(u'Remove flickering from lights. For use on low-end '
                  u'machines.')
    tweak_key = u'NoLightFlicker'
    tweak_choices = [(u'1.0', u'1.0')]
    tweak_log_msg = _(u'Lights Unflickered: %(total_changed)d')
    _flicker_flags = 0x000001C8 # (flickers, flickerSlow, pulse, pulseSlow)

    def wants_record(self, record):
        return int(record.flags & self._flicker_flags)

class AssortedTweak_NoLightFlicker(AAssortedTweak_NoLightFlicker,
                                   _AssortPTweak):
    def buildPatch(self,log,progress,patchFile):
        """Edits patch file as desired. Will write to log."""
        count = Counter()
        keep = patchFile.getKeeper()
        for record in patchFile.LIGH.records:
            if self.wants_record(record):
                record.flags &= ~self._flicker_flags
                keep(record.fid)
                count[record.fid[0]] += 1
        self._patchLog(log,count)

class CBash_AssortedTweak_NoLightFlicker(AAssortedTweak_NoLightFlicker,
                                         _AssortCTweak):
    def apply(self,modFile,record,bashTags):
        """Edits patch file as desired. """
        if self.wants_record(record):
            override = record.CopyAsOverride(self.patchFile)
            if override:
                override.flags &= ~self._flicker_flags
                self.mod_count[modFile.GName] += 1
                record.UnloadRecord()
                record._RecordID = override._RecordID

#------------------------------------------------------------------------------
class AMultiTweakItem_Weight(_AAssortedTweak):
    _log_weight_value = u'OVERRIDE' # avoid pycharm warning

    @property
    def chosen_weight(self): return self.choiceValues[self.chosen][0]

    def _patchLog(self, log, count):
        """Will write to log for a class that has a weight field"""
        log.setHeader(u'=== ' + self.tweak_log_header)
        log(self._log_weight_value % self.chosen_weight)
        log(u'* ' + self.tweak_log_msg % {
            u'total_changed': sum(count.values())})
        for src_plugin in load_order.get_ordered(count.keys()):
            log(u'  * %s: %d' % (src_plugin.s, count[src_plugin]))

# see https://github.com/wrye-bash/wrye-bash/commit/3aa3c941b2de6d751f71e50613ba20ac14f477e8
# CBash only, PBash gets away with just knowing the FormID of SEFF and always
# assuming it exists, since it's from Oblivion.esm. CBash handles this by
# making sure the MGEF records are almost always read in, and always before
# patchers that will need them.
_SEFF = MGEFCode(b'SEFF')

class _PSeffWeightTweak(AMultiTweakItem_Weight, _AssortPTweak):
    """Mixin for PBash weight tweaks that need to ignore SEFF effects."""
    def wants_record(self, record):
        # Skip OBME records, at least for now
        return (super(_PSeffWeightTweak, self).wants_record(record) and
                record.obme_record_version is None and
                not (b'SEFF', 0) in record.getEffects())

class _CSeffWeightTweak(AMultiTweakItem_Weight, _AssortCTweak):
    """Mixin for CBash weight tweaks that need to ignore SEFF effects."""
    def wants_record(self, record):
        return super(_CSeffWeightTweak, self).wants_record(
            record) and not any(e.name == _SEFF for e in record.effects)

class AAssortedTweak_PotionWeight(AMultiTweakItem_Weight):
    """Reweighs standard potions down to 0.1."""
    tweak_read_classes = b'ALCH',
    tweak_name = _(u'Reweigh: Potions (Maximum)')
    tweak_tip = _(u'Potion weight will be capped.')
    tweak_key = u'MaximumPotionWeight'
    tweak_choices = [(u'0.1', 0.1), (u'0.2', 0.2), (u'0.4', 0.4),
                     (u'0.6', 0.6), (_(u'Custom'), 0.0)]
    tweak_log_msg = _(u'Potions Reweighed: %(total_changed)d')
    _log_weight_value = _(u'Potions set to maximum weight of %f.')

    def wants_record(self, record):
        return (self.chosen_weight < record.weight < 1.0 and
                not floats_equal(record.weight, self.chosen_weight))

class AssortedTweak_PotionWeight(_PSeffWeightTweak,
                                 AAssortedTweak_PotionWeight):
    def buildPatch(self,log,progress,patchFile):
        """Edits patch file as desired. Will write to log."""
        count = Counter()
        keep = patchFile.getKeeper()
        for record in patchFile.ALCH.records:
            if self.wants_record(record):
                record.weight = self.chosen_weight
                keep(record.fid)
                count[record.fid[0]] += 1
        self._patchLog(log, count)

class CBash_AssortedTweak_PotionWeight(_CSeffWeightTweak,
                                       AAssortedTweak_PotionWeight):
    def apply(self,modFile,record,bashTags):
        """Edits patch file as desired. """
        maxWeight = self.chosen_weight
        if self.wants_record(record):
            override = record.CopyAsOverride(self.patchFile)
            if override:
                override.weight = maxWeight
                self.mod_count[modFile.GName] += 1
                record.UnloadRecord()
                record._RecordID = override._RecordID

#------------------------------------------------------------------------------
class AAssortedTweak_IngredientWeight(AMultiTweakItem_Weight):
    """Reweighs standard ingredients down to 0.1."""
    tweak_read_classes = b'INGR',
    tweak_name = _(u'Reweigh: Ingredients')
    tweak_tip = _(u'Ingredient weight will be capped.')
    tweak_key = u'MaximumIngredientWeight'
    tweak_choices = [(u'0.1', 0.1), (u'0.2', 0.2), (u'0.4', 0.4),
                     (u'0.6', 0.6), (_(u'Custom'), 0.0)]
    tweak_log_msg = _(u'Ingredients Reweighed: %(total_changed)d')
    _log_weight_value = _(u'Ingredients set to maximum weight of %f.')

    def wants_record(self, record):
        return (record.weight > self.chosen_weight and
                not floats_equal(record.weight, self.chosen_weight))

class AssortedTweak_IngredientWeight(_PSeffWeightTweak,
                                     AAssortedTweak_IngredientWeight):
    def buildPatch(self,log,progress,patchFile):
        """Edits patch file as desired. Will write to log."""
        count = Counter()
        keep = patchFile.getKeeper()
        for record in patchFile.INGR.records:
            if self.wants_record(record):
                record.weight = self.chosen_weight
                keep(record.fid)
                count[record.fid[0]] += 1
        self._patchLog(log, count)

class CBash_AssortedTweak_IngredientWeight(_CSeffWeightTweak,
                                           AAssortedTweak_IngredientWeight):
    def apply(self,modFile,record,bashTags):
        """Edits patch file as desired. """
        if self.wants_record(record):
            override = record.CopyAsOverride(self.patchFile)
            if override:
                override.weight = self.chosen_weight
                self.mod_count[modFile.GName] += 1
                record.UnloadRecord()
                record._RecordID = override._RecordID

#------------------------------------------------------------------------------
class AAssortedTweak_PotionWeightMinimum(AMultiTweakItem_Weight):
    """Reweighs any potions up to 4."""
    tweak_read_classes = b'ALCH',
    tweak_name = _(u'Reweigh: Potions (Minimum)')
    tweak_tip = _(u'Potion weight will be floored.')
    tweak_key = u'MinimumPotionWeight'
    tweak_choices = [(u'0.1', 0.1), (u'0.5', 0.5), (u'1.0', 1.0),
                     (u'2.0', 2.0), (u'4.0', 4.0), (_(u'Custom'), 0.0)]
    tweak_log_msg = _(u'Potions Reweighed: %(total_changed)d')
    _log_weight_value = _(u'Potions set to minimum weight of %f.')

    def wants_record(self, record): # note no SEFF condition
        return (record.weight < self.chosen_weight and
                not floats_equal(record.weight, self.chosen_weight))

class AssortedTweak_PotionWeightMinimum(_AssortPTweak,
                                        AAssortedTweak_PotionWeightMinimum):
    def buildPatch(self,log,progress,patchFile):
        """Edits patch file as desired. Will write to log."""
        count = Counter()
        keep = patchFile.getKeeper()
        for record in patchFile.ALCH.records:
            if self.wants_record(record):
                record.weight = self.chosen_weight
                keep(record.fid)
                count[record.fid[0]] += 1
        self._patchLog(log, count)

class CBash_AssortedTweak_PotionWeightMinimum(
    _AssortCTweak, AAssortedTweak_PotionWeightMinimum):
    scanOrder = 33 #Have it run after the max weight for consistent results
    editOrder = 33

    def apply(self,modFile,record,bashTags):
        """Edits patch file as desired. """
        if self.wants_record(record):
            override = record.CopyAsOverride(self.patchFile)
            if override:
                override.weight = self.chosen_weight
                self.mod_count[modFile.GName] += 1
                record.UnloadRecord()
                record._RecordID = override._RecordID

#------------------------------------------------------------------------------
class AAssortedTweak_StaffWeight(AMultiTweakItem_Weight):
    """Reweighs staves."""
    tweak_read_classes = b'WEAP',
    tweak_name = _(u'Reweigh: Staves')
    tweak_tip =  _(u'Staff weight will be capped.')
    tweak_key = u'StaffWeight'
    tweak_choices = [(u'1', 1.0), (u'2', 2.0), (u'3', 3.0), (u'4', 4.0),
                     (u'5', 5.0), (u'6', 6.0), (u'7', 7.0), (u'8', 8.0),
                     (_(u'Custom'), 0.0)]
    tweak_log_msg = _(u'Staves Reweighed: %(total_changed)d')
    _log_weight_value = _(u'Staves set to maximum weight of %f.')

    def wants_record(self, record):
        return (record.weaponType == 4 and record.weight > self.chosen_weight
                and not floats_equal(record.weight, self.chosen_weight))

class AssortedTweak_StaffWeight(AAssortedTweak_StaffWeight, _AssortPTweak):
    def buildPatch(self,log,progress,patchFile):
        """Edits patch file as desired. Will write to log."""
        count = Counter()
        keep = patchFile.getKeeper()
        for record in patchFile.WEAP.records:
            if self.wants_record(record):
                record.weight = self.chosen_weight
                keep(record.fid)
                count[record.fid[0]] += 1
        self._patchLog(log, count)

class CBash_AssortedTweak_StaffWeight(AAssortedTweak_StaffWeight,
                                      _AssortCTweak):
    def apply(self,modFile,record,bashTags):
        """Edits patch file as desired. """
        if self.wants_record(record):
            override = record.CopyAsOverride(self.patchFile)
            if override:
                override.weight = self.chosen_weight
                self.mod_count[modFile.GName] += 1
                record.UnloadRecord()
                record._RecordID = override._RecordID

#------------------------------------------------------------------------------
class AAssortedTweak_ArrowWeight(AMultiTweakItem_Weight):
    tweak_read_classes = b'AMMO',
    tweak_name = _(u'Reweigh: Arrows')
    tweak_tip = _(u'Arrow weights will be capped.')
    tweak_key = u'MaximumArrowWeight'
    tweak_choices = [(u'0', 0.0), (u'0.1', 0.1), (u'0.2', 0.2), (u'0.4', 0.4),
                     (u'0.6', 0.6), (_(u'Custom'), 0.0)]
    tweak_log_msg = _(u'Arrows Reweighed: %(total_changed)d')
    _log_weight_value = _(u'Arrows set to maximum weight of %f.')

    def wants_record(self, record):
        return (record.weight > self.chosen_weight and
                not floats_equal(record.weight, self.chosen_weight))

class AssortedTweak_ArrowWeight(AAssortedTweak_ArrowWeight, _AssortPTweak):
    def buildPatch(self,log,progress,patchFile):
        """Edits patch file as desired. Will write to log."""
        count = Counter()
        keep = patchFile.getKeeper()
        for record in patchFile.AMMO.records:
            if self.wants_record(record):
                record.weight = self.chosen_weight
                keep(record.fid)
                count[record.fid[0]] += 1
        self._patchLog(log, count)

class CBash_AssortedTweak_ArrowWeight(AAssortedTweak_ArrowWeight,
                                      _AssortCTweak):
    def apply(self,modFile,record,bashTags):
        """Edits patch file as desired. """
        if self.wants_record(record):
            override = record.CopyAsOverride(self.patchFile)
            if override:
                override.weight = self.chosen_weight
                self.mod_count[modFile.GName] += 1
                record.UnloadRecord()
                record._RecordID = override._RecordID

#------------------------------------------------------------------------------
class AAssortedTweak_ScriptEffectSilencer(_AAssortedTweak):
    """Silences the script magic effect and gives it an extremely high
    speed."""
    tweak_read_classes = b'MGEF',
    tweak_name = _(u'Magic: Script Effect Silencer')
    tweak_tip = _(u'Script Effect will be silenced and have no graphics.')
    tweak_key = u'SilentScriptEffect'
    tweak_choices = [(u'0', 0)]
    tweak_log_msg = _(u'Script Effect silenced.')
    default_enabled = True
    _silent_attrs = {} # override in implementations

    def wants_record(self, record):
        # u'' here is on purpose! We're checking the EDID, which gets decoded
        return record.eid == u'SEFF' and any(
            getattr(record, a) != v for a, v in self._silent_attrs.iteritems())

class AssortedTweak_ScriptEffectSilencer(AAssortedTweak_ScriptEffectSilencer,
                                         _AssortPTweak):
    _null_ref = (GPath(bush.game.master_file), 0)
    _silent_attrs = {u'model': None, u'projectileSpeed': 9999,
                     u'light': _null_ref, u'effectShader': _null_ref,
                     u'enchantEffect': _null_ref, u'castingSound': _null_ref,
                     u'boltSound': _null_ref, u'hitSound': _null_ref,
                     u'areaSound': _null_ref}

    def buildPatch(self,log,progress,patchFile):
        """Edits patch file as desired. Will write to log."""
        keep = patchFile.getKeeper()
        s_attrs = self._silent_attrs
        for record in patchFile.MGEF.records:
            if self.wants_record(record):
                record.flags.noHitEffect = True
                for attr in s_attrs: setattr(record, attr, s_attrs[attr])
                keep(record.fid)
        self._patchLog(log, {}) # count would be pointless, always one record

class CBash_AssortedTweak_ScriptEffectSilencer(
    AAssortedTweak_ScriptEffectSilencer, _AssortCTweak):
    _silent_attrs = {
        u'modPath': None, u'modb': None, u'modt_p': None,
        u'projectileSpeed': 9999, u'light': None, u'effectShader': None,
        u'enchantEffect': None, u'castingSound': None, u'boltSound': None,
        u'hitSound': None, u'areaSound': None, u'IsNoHitEffect': True}

    def apply(self,modFile,record,bashTags):
        """Edits patch file as desired. """
        if self.wants_record(record):
            override = record.CopyAsOverride(self.patchFile)
            if override:
                s_attrs = self._silent_attrs
                for attr in s_attrs: setattr(override, attr, s_attrs[attr])
                record.UnloadRecord()
                record._RecordID = override._RecordID

#------------------------------------------------------------------------------
class AAssortedTweak_HarvestChance(_AAssortedTweak):
    """Adjust Harvest Chances."""
    tweak_read_classes = b'FLOR',
    tweak_name = _(u'Harvest Chance')
    tweak_tip = _(u'Harvest chances on all plants will be set to the chosen '
                  u'percentage.')
    tweak_key = u'HarvestChance'
    tweak_choices = [(u'10%', 10), (u'20%', 20), (u'30%', 30), (u'40%', 40),
                     (u'50%', 50), (u'60%', 60), (u'70%', 70), (u'80%', 80),
                     (u'90%', 90), (u'100%', 100), (_(u'Custom'), 0)]
    tweak_log_msg = _(u'Harvest Chances Changed: %(total_changed)d')
    _season_attrs = (u'spring', u'summer', u'fall', u'winter')

    @property
    def chosen_chance(self):
        return self.choiceValues[self.chosen][0]

    def wants_record(self, record):
        return (u'nirnroot' not in record.eid.lower() # skip Nirnroots
                and any(getattr(record, a) != self.chosen_chance for a
                        in self._season_attrs))

class AssortedTweak_HarvestChance(AAssortedTweak_HarvestChance, _AssortPTweak):
    def buildPatch(self,log,progress,patchFile):
        """Edits patch file as desired. Will write to log."""
        count = Counter()
        keep = patchFile.getKeeper()
        for record in patchFile.FLOR.records:
            if self.wants_record(record):
                for attr in self._season_attrs:
                    setattr(record, attr, self.chosen_chance)
                keep(record.fid)
                count[record.fid[0]] += 1
        self._patchLog(log,count)

class CBash_AssortedTweak_HarvestChance(AAssortedTweak_HarvestChance,
                                        _AssortCTweak):
    def apply(self,modFile,record,bashTags):
        """Edits patch file as desired. """
        if self.wants_record(record):
            override = record.CopyAsOverride(self.patchFile)
            if override:
                for attr in self._season_attrs:
                    setattr(override, attr, self.chosen_chance)
                self.mod_count[modFile.GName] += 1
                record.UnloadRecord()
                record._RecordID = override._RecordID

#------------------------------------------------------------------------------
class AAssortedTweak_WindSpeed(_AAssortedTweak):
    """Disables Weather winds."""
    tweak_read_classes = b'WTHR',
    tweak_name = _(u'Disable Wind')
    tweak_tip = _(u'Disables the wind on all weathers.')
    tweak_key = u'windSpeed'
    tweak_log_msg = _(u'Winds Disabled: %(total_changed)d')
    tweak_choices = [(u'Disable', 0)]

    def wants_record(self, record):
        return record.windSpeed != 0

class AssortedTweak_WindSpeed(AAssortedTweak_WindSpeed, _AssortPTweak):
    def buildPatch(self,log,progress,patchFile):
        """Edits patch file as desired. Will write to log."""
        count = Counter()
        keep = patchFile.getKeeper()
        for record in patchFile.WTHR.records:
            if self.wants_record(record):
                record.windSpeed = 0
                keep(record.fid)
                count[record.fid[0]] += 1
        self._patchLog(log,count)

class CBash_AssortedTweak_WindSpeed(AAssortedTweak_WindSpeed,
                                    _AssortCTweak):
    def apply(self,modFile,record,bashTags):
        """Edits patch file as desired. """
        if self.wants_record(record):
            override = record.CopyAsOverride(self.patchFile)
            if override:
                override.windSpeed = 0
                self.mod_count[modFile.GName] += 1
                record.UnloadRecord()
                record._RecordID = override._RecordID

#------------------------------------------------------------------------------
class AAssortedTweak_UniformGroundcover(_AAssortedTweak):
    """Eliminates random variation in groundcover."""
    tweak_read_classes = b'GRAS',
    tweak_name = _(u'Uniform Groundcover')
    tweak_tip = _(u'Eliminates random variation in groundcover (grasses, '
                  u'shrubs, etc.).')
    tweak_key = u'UniformGroundcover'
    tweak_choices = [(u'1.0', u'1.0')]
    tweak_log_msg = _(u'Grasses Normalized: %(total_changed)d')

    def wants_record(self, record):
        return record.heightRange != 0

class AssortedTweak_UniformGroundcover(AAssortedTweak_UniformGroundcover,
                                       _AssortPTweak):
    def buildPatch(self,log,progress,patchFile):
        """Edits patch file as desired. Will write to log."""
        count = Counter()
        keep = patchFile.getKeeper()
        for record in patchFile.GRAS.records:
            if self.wants_record(record):
                record.heightRange = 0
                keep(record.fid)
                count[record.fid[0]] += 1
        self._patchLog(log,count)

class CBash_AssortedTweak_UniformGroundcover(AAssortedTweak_UniformGroundcover,
                                             _AssortCTweak):
    def apply(self,modFile,record,bashTags):
        """Edits patch file as desired. """
        if self.wants_record(record):
            override = record.CopyAsOverride(self.patchFile)
            if override:
                override.heightRange = 0
                self.mod_count[modFile.GName] += 1
                record.UnloadRecord()
                record._RecordID = override._RecordID

#------------------------------------------------------------------------------
class AAssortedTweak_SetCastWhenUsedEnchantmentCosts(_AAssortedTweak):
    """Sets Cast When Used Enchantment number of uses."""
    tweak_read_classes = b'ENCH',
    tweak_name = _(u'Number of uses for pre-enchanted weapons and staves')
    tweak_tip = _(u'The charge amount and cast cost will be edited so that '
                  u'all enchanted weapons and staves have the amount of uses '
                  u'specified. Cost will be rounded up to 1 (unless set to '
                  u'unlimited) so number of uses may not exactly match for '
                  u'all weapons.')
    tweak_key = u'Number of uses:'
    tweak_choices = [(u'1', 1), (u'5', 5), (u'10', 10), (u'20', 20),
                     (u'30', 30), (u'40', 40), (u'50', 50), (u'80', 80),
                     (u'100', 100), (u'250', 250), (u'500', 500),
                     (_(u'Unlimited'), 0), (_(u'Custom'), 0)]
    tweak_log_header = _(u'Set Enchantment Number of Uses')
    tweak_log_msg = _(u'Enchantments Set: %(total_changed)d')

    def wants_record(self, record):
        if record.itemType not in (1, 2): return False
        new_cost, new_amount = self._calc_cost_and_amount(record)
        return (record.enchantCost != new_cost or
                record.chargeAmount != new_amount)

    def _calc_cost_and_amount(self, record):
        """Calculates the new enchantment cost and charge amount for the
        specified record based on the number of uses the user chose."""
        chosen_uses = self.choiceValues[self.chosen][0]
        final_cost = (max(record.chargeAmount // chosen_uses, 1)
                      if chosen_uses != 0 else 0)
        return final_cost, final_cost * chosen_uses

class AssortedTweak_SetCastWhenUsedEnchantmentCosts(
    AAssortedTweak_SetCastWhenUsedEnchantmentCosts, _AssortPTweak):
    def buildPatch(self,log,progress,patchFile):
        """Edits patch file as desired. Will write to log."""
        count = Counter()
        keep = patchFile.getKeeper()
        for record in patchFile.ENCH.records:
            if self.wants_record(record):
                new_cost, new_amount = self._calc_cost_and_amount(record)
                record.enchantCost = new_cost
                record.chargeAmount = new_amount
                keep(record.fid)
                count[record.fid[0]] += 1
        self._patchLog(log,count)

class CBash_AssortedTweak_SetCastWhenUsedEnchantmentCosts(
    AAssortedTweak_SetCastWhenUsedEnchantmentCosts, _AssortCTweak):

    def apply(self,modFile,record,bashTags):
        """Edits patch file as desired. """
        if self.wants_record(record):
            override = record.CopyAsOverride(self.patchFile)
            if override:
                new_cost, new_amount = self._calc_cost_and_amount(record)
                override.enchantCost = new_cost
                override.chargeAmount = new_amount
                self.mod_count[modFile.GName] += 1
                record.UnloadRecord()
                record._RecordID = override._RecordID

#------------------------------------------------------------------------------
##: It's possible to simplify this further, but will require some effort
##: Also, will have to become more powerful in the process if we want it to
# support FO3/FNV eventually
class AAssortedTweak_DefaultIcons(_AAssortedTweak):
    """Sets a default icon for any records that don't have any icon
    assigned."""
    tweak_name = _(u'Default Icons')
    tweak_tip = _(u"Sets a default icon for any records that don't have any "
                  u'icon assigned.')
    tweak_key = u'icons'
    tweak_choices = [(u'1', 1)]
    _default_icons = {
        b'ALCH': u'Clutter\\Potions\\IconPotion01.dds',
        b'AMMO': u'Weapons\\IronArrow.dds',
        b'APPA': u'Clutter\\IconMortarPestle.dds',
        b'ARMO': ((u'Armor\\Iron\\M\\Cuirass.dds',
                   u'Armor\\Iron\\F\\Cuirass.dds'),
                 (u'Armor\\Iron\\M\\Greaves.dds',
                  u'Armor\\Iron\\F\\Greaves.dds'),
                 (u'Armor\\Iron\\M\\Helmet.dds',),
                 (u'Armor\\Iron\\M\\Gauntlets.dds',
                  u'Armor\\Iron\\F\\Gauntlets.dds'),
                 (u'Armor\\Iron\\M\\Boots.dds',),
                 (u'Armor\\Iron\\M\\Shield.dds',),
                 (u'Armor\\Iron\\M\\Shield.dds',),), # Default Armor icon
        b'BOOK': u'Clutter\\iconbook%d.dds',
        b'BSGN': u'Clutter\\iconbook%d.dds',
        b'CLAS': u'Clutter\\iconbook%d.dds',
        b'CLOT': ((u'Clothes\\MiddleClass\\01\\M\\Shirt.dds',
                   u'Clothes\\MiddleClass\\01\\F\\Shirt.dds'),
                 (u'Clothes\\MiddleClass\\01\\M\\Pants.dds',
                  u'Clothes\\MiddleClass\\01\\F\\Pants.dds'),
                 (u'Clothes\\MythicDawnrobe\\hood.dds',),
                 (u'Clothes\\LowerClass\\Jail\\M\\'
                  u'JailShirtHandcuff.dds',),
                 (u'Clothes\\MiddleClass\\01\\M\\Shoes.dds',
                  u'Clothes\\MiddleClass\\01\\F\\Shoes.dds'),
                 (u'Clothes\\Ring\\RingNovice.dds',),
                 (u'Clothes\\Amulet\\AmuletSilver.dds',),),
##                'FACT': u"", ToDo
        b'INGR': u'Clutter\\IconSeeds.dds',
        b'KEYM': (u'Clutter\\Key\\Key.dds', u'Clutter\\Key\\Key02.dds'),
        b'LIGH': u'Lights\\IconTorch02.dds',
        b'MISC': u'Clutter\\Soulgems\\AzurasStar.dds',
        b'QUST': u'Quest\\icon_miscellaneous.dds',
        b'SGST': u'IconSigilStone.dds',
        b'SLGM': u'Clutter\\Soulgems\\AzurasStar.dds',
        b'WEAP': (u'Weapons\\IronDagger.dds', u'Weapons\\IronClaymore.dds',
                  u'Weapons\\IronMace.dds', u'Weapons\\IronBattleAxe.dds',
                  u'Weapons\\Staff.dds', u'Weapons\\IronBow.dds',),
    }
    tweak_read_classes = tuple(_default_icons)
    tweak_log_msg = _(u'Default Icons Set: %(total_changed)d')
    default_enabled = True

    def wants_record(self, record):
        return (not getattr(record, u'iconPath', None) and
                not getattr(record, u'maleIconPath', None) and
                not getattr(record, u'femaleIconPath', None))

    def _assign_icons(self, record, d_icons):
        """Assigns the specified default icons to the specified record."""
        try:
            if isinstance(d_icons, tuple):
                if len(d_icons) == 1:
                    record.maleIconPath = d_icons[0]
                else:
                    record.maleIconPath, record.femaleIconPath = d_icons
            else:
                record.iconPath = d_icons
        except ValueError:
            deprint(u'Error while assigning default icons to %r' % record)
            raise

class AssortedTweak_DefaultIcons(AAssortedTweak_DefaultIcons, _AssortPTweak):
    def wants_record(self, record):
        rsig = record.recType
        if (rsig == b'LIGH' and not record.flags.canTake or
                rsig == b'QUST' and not record.stages or
                rsig in (b'ARMO', b'CLOT') and
                record.flags.notPlayable): return False
        return super(AssortedTweak_DefaultIcons, self).wants_record(record)

    def buildPatch(self,log,progress,patchFile):
        count = Counter()
        keep = patchFile.getKeeper()
        for curr_sig in self.tweak_read_classes:
            if curr_sig not in patchFile.tops: continue
            for record in patchFile.tops[curr_sig].records:
                if self.wants_record(record):
                    d_icons = self._default_icons[curr_sig]
                    if isinstance(d_icons, tuple):
                        if curr_sig in (b'ARMO', b'CLOT'):
                            # Choose based on body flags:
                            body_flags = record.flags
                            if body_flags.upperBody:
                                d_icons = d_icons[0]
                            elif body_flags.lowerBody:
                                d_icons = d_icons[1]
                            elif body_flags.head or body_flags.hair:
                                d_icons = d_icons[2]
                            elif body_flags.hand:
                                d_icons = d_icons[3]
                            elif body_flags.foot:
                                d_icons = d_icons[4]
                            elif (curr_sig == b'ARMO' and body_flags.shield or
                                  curr_sig == b'CLOT' and (
                                          body_flags.leftRing or
                                          body_flags.rightRing)):
                                d_icons = d_icons[5]
                            else: # Default icon, probably a token or somesuch
                                d_icons = d_icons[6]
                        elif curr_sig == b'KEYM':
                            d_icons = d_icons[random.randint(0, 1)]
                        elif curr_sig == b'WEAP':
                            # Choose based on weapon type:
                            try:
                                d_icons = d_icons[record.weaponType]
                            except IndexError: # just in case
                                d_icons = d_icons[0]
                    elif curr_sig in (b'BOOK', b'BSGN', b'CLAS'):
                        # Just a random book icon - for class/birthsign as well.
                        d_icons = d_icons % (random.randint(1, 13))
                    self._assign_icons(record, d_icons)
                    keep(record.fid)
                    count[record.fid[0]] += 1
        self._patchLog(log,count)

class CBash_AssortedTweak_DefaultIcons(AAssortedTweak_DefaultIcons,
                                       _AssortCTweak):
    def wants_record(self, record):
        if (record._Type == b'LIGH' and not record.IsCanTake or
                record._Type == b'QUST' and not record.stages or
                record._Type in (b'ARMO', b'CLOT') and record.IsNonPlayable):
            return False
        return super(CBash_AssortedTweak_DefaultIcons, self).wants_record(
            record)

    def apply(self,modFile,record,bashTags):
        """Edits patch file as desired. """
        if self.wants_record(record):
            override = record.CopyAsOverride(self.patchFile)
            if override:
                d_icons = self._default_icons[override._Type]
                if isinstance(d_icons, tuple):
                    if override._Type in (b'ARMO', b'CLOT'):
                        #choose based on body flags:
                        if override.IsUpperBody:
                            d_icons = d_icons[0]
                        elif override.IsLowerBody:
                            d_icons = d_icons[1]
                        elif override.IsHead or record.IsHair:
                            d_icons = d_icons[2]
                        elif override.IsHand:
                            d_icons = d_icons[3]
                        elif override.IsFoot:
                            d_icons = d_icons[4]
                        elif (override._Type == b'ARMO' and override.IsShield
                              or override._Type == b'CLOT' and
                              override.IsLeftRing or override.IsRightRing):
                            d_icons = d_icons[5]
                        else: # Default icon, probably a token or somesuch
                            d_icons = d_icons[6]
                    elif override._Type == b'KEYM':
                        d_icons = d_icons[random.randint(0,1)]
                    elif override._Type == b'WEAP':
                        #choose based on weapon type:
                        try:
                            d_icons = d_icons[override.weaponType]
                        except IndexError: #just in case
                            d_icons = d_icons[0]
                elif override._Type in (b'BOOK', b'BSGN', b'CLAS'):
                    # just a random book icon - for class/birthsign as well.
                    d_icons = d_icons % (random.randint(1,13))
                self._assign_icons(override, d_icons)
                self.mod_count[modFile.GName] += 1
                record.UnloadRecord()
                record._RecordID = override._RecordID

#------------------------------------------------------------------------------
class _AAttenuationTweak(_AAssortedTweak):
    """Shared code of PBash/CBash sound attenuation tweaks."""
    tweak_read_classes = b'SOUN',
    tweak_choices = [(u'0%', 0), (u'5%', 5), (u'10%', 10), (u'20%', 20),
                     (u'50%', 50), (u'80%', 80), (_(u'Custom'), 0)]
    tweak_log_msg = _(u'Sounds Modified: %(total_changed)d')

    @property
    def chosen_atten(self): return self.choiceValues[self.chosen][0] / 100

    def wants_record(self, record):
        return record.staticAtten and self.chosen_atten != 1 # avoid ITPOs

class _PAttenuationTweak(_AAttenuationTweak, _AssortPTweak):
    """Shared code of PBash sound attenuation tweaks."""
    def buildPatch(self,log,progress,patchFile):
        """Edits patch file as desired. Will write to log."""
        count = Counter()
        keep = patchFile.getKeeper()
        for record in patchFile.SOUN.records:
            if self.wants_record(record):
                # Must be an int on py3, otherwise errors on dump
                record.staticAtten = int(record.staticAtten *
                                         self.chosen_atten)
                keep(record.fid)
                count[record.fid[0]] += 1
        self._patchLog(log, count)

class _CAttenuationTweak(_AAttenuationTweak, _AssortCTweak):
    """Shared code of CBash sound attenuation tweaks."""
    def apply(self,modFile,record,bashTags):
        """Edits patch file as desired. """
        if self.wants_record(record):
            override = record.CopyAsOverride(self.patchFile)
            if override:
                # Must be an int, otherwise cint errors on dump
                override.staticAtten = int(override.staticAtten *
                                           self.chosen_atten)
                self.mod_count[modFile.GName] += 1
                record.UnloadRecord()
                record._RecordID = override._RecordID

#------------------------------------------------------------------------------
_nirnroot_words = {u'nirnroot', u'vynroot', u'vynwurz'}
def _is_nirnroot(record):
    return any(x in record.eid.lower() for x in _nirnroot_words)

class AAssortedTweak_SetSoundAttenuationLevels(_AAttenuationTweak):
    """Sets Sound Attenuation Levels for all records except Nirnroots."""
    tweak_name = _(u'Set Sound Attenuation Levels')
    tweak_tip = _(u'Sets sound attenuation levels to tweak%*current level. '
                  u'Does not affect {}.').format(bush.game.nirnroots)
    tweak_key = u'Attenuation%:'

    def wants_record(self, record):
        return super(AAssortedTweak_SetSoundAttenuationLevels,
                     self).wants_record(
            record) and not _is_nirnroot(record)

class AssortedTweak_SetSoundAttenuationLevels(
    AAssortedTweak_SetSoundAttenuationLevels, _PAttenuationTweak): pass
class CBash_AssortedTweak_SetSoundAttenuationLevels(
    AAssortedTweak_SetSoundAttenuationLevels, _CAttenuationTweak): pass

#------------------------------------------------------------------------------
class AAssortedTweak_SetSoundAttenuationLevels_NirnrootOnly(
    _AAttenuationTweak):
    """Sets Sound Attenuation Levels for Nirnroots."""
    tweak_name = _(u'Set Sound Attenuation Levels: %s '
                   u'Only') % bush.game.nirnroots
    tweak_tip = _(u'Sets sound attenuation levels to tweak%*current level. '
                  u'Only affects {}.').format(bush.game.nirnroots)
    tweak_key = u'Nirnroot Attenuation%:'

    def wants_record(self, record):
        return super(AAssortedTweak_SetSoundAttenuationLevels_NirnrootOnly,
                     self).wants_record(
            record) and _is_nirnroot(record)

class AssortedTweak_SetSoundAttenuationLevels_NirnrootOnly(
    AAssortedTweak_SetSoundAttenuationLevels_NirnrootOnly,
    _PAttenuationTweak): pass
class CBash_AssortedTweak_SetSoundAttenuationLevels_NirnrootOnly(
    AAssortedTweak_SetSoundAttenuationLevels_NirnrootOnly,
    _CAttenuationTweak): pass

#------------------------------------------------------------------------------
class AAssortedTweak_FactioncrimeGoldMultiplier(_AAssortedTweak):
    """Fix factions with unset crime gold multiplier to have a
    crime gold multiplier of 1.0."""
    tweak_read_classes = b'FACT',
    tweak_name = _(u'Faction Crime Gold Multiplier Fix')
    tweak_tip = _(u'Fix factions with unset Crime Gold Multiplier to have a '
                  u'Crime Gold Multiplier of 1.0.')
    tweak_key = u'FactioncrimeGoldMultiplier'
    tweak_choices = [(u'1.0', u'1.0')]
    tweak_log_msg = _(u'Factions Fixed: %(total_changed)d')

class AssortedTweak_FactioncrimeGoldMultiplier(
    AAssortedTweak_FactioncrimeGoldMultiplier, _AssortPTweak):
    def wants_record(self, record):
        return record.crime_gold_multiplier is None

    def buildPatch(self,log,progress,patchFile):
        """Edits patch file as desired. Will write to log."""
        count = Counter()
        keep = patchFile.getKeeper()
        for record in patchFile.FACT.records:
            if self.wants_record(record):
                record.crime_gold_multiplier = 1.0
                keep(record.fid)
                count[record.fid[0]] += 1
        self._patchLog(log,count)

class CBash_AssortedTweak_FactioncrimeGoldMultiplier(
    AAssortedTweak_FactioncrimeGoldMultiplier, _AssortCTweak):
    def wants_record(self, record):
        return record.crimeGoldMultiplier is None

    def apply(self,modFile,record,bashTags):
        """Edits patch file as desired."""
        if self.wants_record(record):
            override = record.CopyAsOverride(self.patchFile)
            if override:
                override.crimeGoldMultiplier = 1.0
                self.mod_count[modFile.GName] += 1
                record.UnloadRecord()
                record._RecordID = override._RecordID

#------------------------------------------------------------------------------
class AAssortedTweak_LightFadeValueFix(_AAssortedTweak):
    """Remove light flickering for low end machines."""
    tweak_read_classes = b'LIGH',
    tweak_name = _(u'No Light Fade Value Fix')
    tweak_tip = _(u'Sets Light Fade values to default of 1.0 if not set.')
    tweak_key = u'NoLightFadeValueFix'
    tweak_choices = [(u'1.0', u'1.0')]
    tweak_log_msg = _(u'Lights With Fade Values Added: %(total_changed)d')

    def wants_record(self, record):
        return record.fade is None

class AssortedTweak_LightFadeValueFix(AAssortedTweak_LightFadeValueFix,
                                      _AssortPTweak):
    def buildPatch(self,log,progress,patchFile):
        """Edits patch file as desired. Will write to log."""
        count = Counter()
        keep = patchFile.getKeeper()
        for record in patchFile.LIGH.records:
            if self.wants_record(record):
                record.fade = 1.0
                keep(record.fid)
                count[record.fid[0]] += 1
        self._patchLog(log,count)

class CBash_AssortedTweak_LightFadeValueFix(AAssortedTweak_LightFadeValueFix,
                                            _AssortCTweak):
    def apply(self,modFile,record,bashTags):
        """Edits patch file as desired. """
        if self.wants_record(record):
            override = record.CopyAsOverride(self.patchFile)
            if override:
                override.fade = 1.0
                self.mod_count[modFile.GName] += 1
                record.UnloadRecord()
                record._RecordID = override._RecordID

#------------------------------------------------------------------------------
class AAssortedTweak_TextlessLSCRs(_AAssortedTweak):
    """Removes the description from loading screens."""
    tweak_read_classes = b'LSCR',
    tweak_name = _(u'No Description Loading Screens')
    tweak_tip = _(u'Removes the description from loading screens.')
    tweak_key = u'NoDescLSCR'
    tweak_choices = [(u'1.0', u'1.0')]
    tweak_log_msg = _(u'Loading Screens Tweaked: %(total_changed)d')

    def wants_record(self, record):
        return record.text

class AssortedTweak_TextlessLSCRs(AAssortedTweak_TextlessLSCRs, _AssortPTweak):
    def buildPatch(self,log,progress,patchFile):
        """Edits patch file as desired. Will write to log."""
        count = Counter()
        keep = patchFile.getKeeper()
        for record in patchFile.LSCR.records:
            if self.wants_record(record):
                record.text = u''
                keep(record.fid)
                count[record.fid[0]] += 1
        self._patchLog(log,count)

class CBash_AssortedTweak_TextlessLSCRs(AAssortedTweak_TextlessLSCRs,
                                        _AssortCTweak):
    def apply(self,modFile,record,bashTags):
        """Edits patch file as desired. """
        if self.wants_record(record):
            override = record.CopyAsOverride(self.patchFile)
            if override:
                override.text = u''
                self.mod_count[modFile.GName] += 1
                record.UnloadRecord()
                record._RecordID = override._RecordID

class AssortedTweaker(MultiTweaker):
    """Tweaks assorted stuff. Sub-tweaks behave like patchers themselves."""
    scanOrder = 32
    editOrder = 32

    @classmethod
    def tweak_instances(cls):
        return sorted([
            AssortedTweak_ArmorShows_Amulets(),
            AssortedTweak_ArmorShows_Rings(),
            AssortedTweak_ClothingShows_Amulets(),
            AssortedTweak_ClothingShows_Rings(),
            AssortedTweak_ArmorPlayable(),
            AssortedTweak_ClothingPlayable(),
            AssortedTweak_BowReach(),
            AssortedTweak_ConsistentRings(),
            AssortedTweak_DarnBooks(),
            AssortedTweak_FogFix(),
            AssortedTweak_NoLightFlicker(),
            AssortedTweak_PotionWeight(),
            AssortedTweak_PotionWeightMinimum(),
            AssortedTweak_StaffWeight(),
            AssortedTweak_SetCastWhenUsedEnchantmentCosts(),
            AssortedTweak_WindSpeed(),
            AssortedTweak_UniformGroundcover(),
            AssortedTweak_HarvestChance(),
            AssortedTweak_IngredientWeight(),
            AssortedTweak_ArrowWeight(),
            AssortedTweak_ScriptEffectSilencer(),
            AssortedTweak_DefaultIcons(),
            AssortedTweak_SetSoundAttenuationLevels(),
            AssortedTweak_SetSoundAttenuationLevels_NirnrootOnly(),
            AssortedTweak_FactioncrimeGoldMultiplier(),
            AssortedTweak_LightFadeValueFix(),
            AssortedTweak_SkyrimStyleWeapons(),
            AssortedTweak_TextlessLSCRs(),
            ],key=lambda a: a.tweak_name.lower())

class CBash_AssortedTweaker(CBash_MultiTweaker):
    """Tweaks assorted stuff. Sub-tweaks behave like patchers themselves."""
    scanOrder = 32
    editOrder = 32

    @classmethod
    def tweak_instances(cls):
        return sorted([
            CBash_AssortedTweak_ArmorShows_Amulets(),
            CBash_AssortedTweak_ArmorShows_Rings(),
            CBash_AssortedTweak_ClothingShows_Amulets(),
            CBash_AssortedTweak_ClothingShows_Rings(),
            CBash_AssortedTweak_ArmorPlayable(),
            CBash_AssortedTweak_ClothingPlayable(),
            CBash_AssortedTweak_BowReach(),
            CBash_AssortedTweak_ConsistentRings(),
            CBash_AssortedTweak_DarnBooks(),
            CBash_AssortedTweak_FogFix(),
            CBash_AssortedTweak_NoLightFlicker(),
            CBash_AssortedTweak_PotionWeight(),
            CBash_AssortedTweak_PotionWeightMinimum(),
            CBash_AssortedTweak_StaffWeight(),
            CBash_AssortedTweak_SetCastWhenUsedEnchantmentCosts(),
            CBash_AssortedTweak_HarvestChance(),
            CBash_AssortedTweak_WindSpeed(),
            CBash_AssortedTweak_UniformGroundcover(),
            CBash_AssortedTweak_IngredientWeight(),
            CBash_AssortedTweak_ArrowWeight(),
            CBash_AssortedTweak_ScriptEffectSilencer(),
            CBash_AssortedTweak_DefaultIcons(),
            CBash_AssortedTweak_SetSoundAttenuationLevels(),
            CBash_AssortedTweak_SetSoundAttenuationLevels_NirnrootOnly(),
            CBash_AssortedTweak_FactioncrimeGoldMultiplier(),
            CBash_AssortedTweak_LightFadeValueFix(),
            CBash_AssortedTweak_SkyrimStyleWeapons(),
            CBash_AssortedTweak_TextlessLSCRs(),
            ],key=lambda a: a.tweak_name.lower())
