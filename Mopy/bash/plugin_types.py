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
"""Houses data structures to represent plugin types - usually these are set
as flags but file extension may play a role. The PluginFlag enum is used to
define the various flags a plugin can have, while the MergeabilityCheck enum
is used to define the various mergeability checks that a game can have. We
might need game specific information (check the game_handle argument) but these
classes are above GameInfo - keep this module top level. PF was created after
MC as plugin types started proliferating - their contract is still WIP."""
import os
import sys
from collections import Counter, defaultdict
from enum import Enum
from typing import final

# we are imported early (in game/__init__), so only import from library modules
from .bolt import sig_to_str
from .exception import ModError

# global holding the scale flags mapped to their offsets see _init_plugin_types
# ESL, MID in this order - avoid using it, it's for caching function parameters
scale_flags = {}

__exit = lambda x: True # trick to exit early on non-verbose mode

def is_vanilla(mod_info, reasons, game_handle):
    """Mark vanilla plugins as non-mergeable - don't do the load checks in
    PBash."""
    if mod_info.fn_key.lower() in game_handle.bethDataFiles:
        return True if reasons is None else not reasons.append(_(
            'Is Vanilla Plugin')) # return True - block rest of checks

def _pbash_mergeable_no_load(modInfo, minfos, reasons, game_handle):
    if is_vanilla(modInfo, reasons, game_handle):
        return False # don't do further checks even in verbose mode
    _exit = __exit if reasons is None else reasons.append # append returns None
    if game_handle.master_flag.has_flagged(modInfo) and _exit(_(
            'This plugin has the ESM flag.')):
        return False
    #--Bashed Patch
    if modInfo.isBP() and _exit(_('This plugin is a Bashed Patch.')):
        return False
    # Plugin INIs would get deactivated if the plugin got merged
    if ((plugin_ini_name := modInfo.get_ini_name()) in minfos.plugin_inis and
            _exit(_('This plugin has an associated INI file '
                    '(%(plugin_ini_name)s).') % {
                'plugin_ini_name': plugin_ini_name})):
        return False
    #--Bsa / blocking resources?
    hasBsa, has_blocking_resources = modInfo.hasResources()
    if hasBsa and _exit(_('This plugin has an associated %(bsa_ext)s file.'
                          ) % {'bsa_ext': game_handle.Bsa.bsa_extension}):
        return False
    if has_blocking_resources:
        dir_list = '\n  - '.join(f'{pnd}{os.sep}%(blocking_plugin_name)s'
            for pnd in game_handle.plugin_name_specific_dirs if pnd)
        if _exit((_('Has plugin-specific directory - one of the following:') +
              f'\n  - {dir_list}') % {'blocking_plugin_name': modInfo.fn_key}):
            return False
    #--Missing Strings Files?
    if modInfo.fn_key in minfos.missing_strings:
        if reasons is None: return False
        from . import oblivionIni
        i_lang = oblivionIni.get_ini_language(game_handle.Ini.default_game_lang)
        strings_example = (f'{os.path.join("Strings", modInfo.fn_key.fn_body)}'
                           f'_{i_lang}.STRINGS')
        reasons.append(_('Missing string translation files '
                         '(%(strings_example)s, etc).') % {
            'strings_example': strings_example})
    # if not verbose we already returned False, else we continue anyway
    return True

def isPBashMergeable(modInfo, minfos, reasons, game_handle):
    """Return True or error message indicating whether specified mod is
    mergeable."""
    if not _pbash_mergeable_no_load(modInfo, minfos, reasons, game_handle):
        return False  # non verbose mode or vanilla plugin
    _exit = __exit if reasons is None else reasons.append # append returns None
    if not game_handle.Esp.canBash and _exit(
        _('Wrye Bash does not currently support loading plugins for '
          '%(game_name)s.') % {'game_name': game_handle.display_name}):
        return False
    #--Load test: use generic MreRecord (without unpacking). ModFile.load will
    # unpack the header which is enough for record.flags1|fid checks
    from .mod_files import LoadFactory, ModFile # don't import brec in boot
    merge_types_fact = LoadFactory(False, generic=game_handle.mergeable_sigs)
    modFile = ModFile(modInfo, merge_types_fact)
    try:
        modFile.load_plugin(loadStrings=False, catch_errors=False)
    except ModError as error:
        if _exit(f'{error}.'): return False
    #--Skipped over types?
    if modFile.topsSkipped and _exit(
            _('Wrye Bash does not support the following record types: '
              '%(unsupported_rec_types)s.') % {
                'unsupported_rec_types': _join_sigs(modFile.topsSkipped)}):
        return False
    #--Empty mod
    elif not modFile.tops and _exit(_('This plugin is empty.')):
        return False
    #--New record
    newblocks = []
    self_name = modInfo.fn_key
    for top_sig, block in modFile.tops.items():
        for candidate_rec in block.iter_records(): # skip deleted/ignored
            if candidate_rec.group_key().mod_fn == self_name:
                if reasons is None: return False
                newblocks.append(top_sig)
                break
    if newblocks: reasons.append(
        _('This plugin has new records in the following groups: '
          '%(new_rec_groups)s.') % {'new_rec_groups': _join_sigs(newblocks)})
    dependent = _dependent(self_name, minfos)
    if dependent and _exit(_('This plugin is a master of the following non-mergeable '
              'plugins: %(non_mergeable_plugins)s.') % {
                'non_mergeable_plugins': ', '.join(sorted(dependent))}):
        return False
    # Client must make sure NoMerge tag not in tags - if in tags
    # don't show up as mergeable.
    return not reasons

def _join_sigs(rec_sigs):
    return ', '.join(map(sig_to_str, sorted(rec_sigs)))

def _dependent(minfo_key, minfos):
    """Get mods for which modInfo is a master mod (excluding BPs and
    mergeable)."""
    dependent = [mname for mname, info in minfos.items() if
                 not info.isBP() and minfo_key in info.masterNames and
                 MergeabilityCheck.MERGE not in info.merge_types()]
    return dependent

#------------------------------------------------------------------------------
# The int values are stored in the settings files (mergeability cache), so they
# should always remain the same just to be safe
class MergeabilityCheck(Enum):
    """The various mergeability checks that a game can have. See the comment
    above each of them for more information."""
    # If set for the game, the Merge Patches patcher will be enabled, the
    # NoMerge tag will be available and WB will check plugins for their BP
    # mergeability.
    MERGE = 0
    # If set for the game, WB will check plugins for their ESL flaggability
    ESL_CHECK = 1
    # If set for the game, WB will check plugins for their Overlay flaggability
    _OVERLAY_CHECK = 2 # disabled
    # If set for the game, WB will check plugins for their MID flaggability
    MID_CHECK = 3

    def cached_types(self, mod_infos):
        """Return *all* mod infos that passed our mergeability check, with a
        header and message for the mod checker UI."""
        match self:
            case MergeabilityCheck.MERGE:
                h, m = '=== ' + _('Mergeable'), _(
                    'The following plugins could be merged into a Bashed '
                    'Patch, but are currently not merged.')
            case _:
                h, m = ('=== ' + _('%(FLAG)s-Capable') % (n := {'FLAG': self}),
                    _('The following plugins could be %(FLAG)s-flagged.') % n)
        return [p for p in mod_infos.values() if self in p.merge_types()], h, m

    def display_info(self, minf, checkMark):
        """Return a UI settings key and a mouse text for the mod list UI."""
        if self not in minf.merge_types(): return '', ''
        match self:
            case MergeabilityCheck.MERGE:
                if 'NoMerge' in minf.getBashTags():
                    return 'mods.text.noMerge', _('Technically mergeable, '
                                                  'but has NoMerge tag.')
                if checkMark == 2: # Merged plugins won't be in master lists
                    mtext = _('Merged into Bashed Patch.')
                else:
                    mtext = _('Can be merged into Bashed Patch.')
            case MergeabilityCheck.ESL_CHECK:
                mtext = _('Can be ESL-flagged.')
            case MergeabilityCheck.MID_CHECK:
                mtext = _('Can be MID-flagged.')
        return 'mods.text.mergeable', mtext

    def __reduce_ex__(self, protocol): # pickle enum members as int
        return int, (self.value, )

    def __repr__(self):
        return self.name

#------------------------------------------------------------------------------
class PluginFlag(Enum):
    """Enum for plugin flags and plugin types - they're friends with ModInfo
    to the point the latter lets it modify its private attributes. This
    intimate class relationship drastically simplifies client code."""
    _ignore_ = ('count_str', )
    count_str = ''

    def __init__(self, flag_attr, mod_info_attr, ui_letter_key,
                 convert_exts=('.esp', '.esu')):
        self._flag_attr = flag_attr # the ModInfo.header.flags1 attribute
        self._mod_info_attr = mod_info_attr # (private) ModInfo cache attribute
        self.fl_offset = None # index offset for games that support scale flags
        self.ui_letter_key = ui_letter_key # UI key mods.text.es{ui_letter_key}
        self.convert_exts = convert_exts # allowed exts for the AFlipFlagLink
        self.continue_message = () # continue message for the AFlipFlagLink
        self.help_flip = '' # help text for the AFlipFlagLink

    @final
    def has_flagged(self, mod_info):
        """Check if the self._flag_attr is set on the mod info flags."""
        return getattr(mod_info.header.flags1, self._flag_attr)

    @final
    def cached_type(self, minf):
        """Return the cached type of mod/master info - depends on the
        corresponding flag state and possibly on the file extension."""
        try:
            return getattr(minf, self._mod_info_attr)
        except AttributeError: # MasterInfo
            if minf.mod_info:
                return getattr(minf.mod_info, self._mod_info_attr)
            return minf.flag_fallback(self)

    @final
    def set_mod_flag(self, mod_info, set_flag, game_handle):
        """Set the flag on the mod info and update the internal mod info state.
        """
        try:
            if set_flag is not None:
                setattr(mod_info.header.flags1, self._flag_attr, set_flag)
            else: # just init
                set_flag = self.has_flagged(mod_info)
            if not set_flag: # if we are not flagged check the file extension
                set_flag = self._force_ext_flags(mod_info, game_handle,
                                                 mod_info.get_extension())
            setattr(mod_info, self._mod_info_attr, set_flag)
        except AttributeError: # mod_info is a ModInfo.header.flags1 instance
            setattr(mod_info, self._flag_attr, set_flag)

    def _force_ext_flags(self, mod_info, game_handle, mext):
        return False

    @classmethod
    def check_flag_assignments(cls, flag_dict, raise_on_invalid=True):
        return flag_dict

    @classmethod
    def guess_flags(cls, mod_fn_ext, game_handle, masters_supplied=()):
        """Guess the flags of a mod/master info from its filename extension.
        Also used to force the plugin type (for .esm/esl) in set_mod_flag."""
        return {game_handle.master_flag: True} if mod_fn_ext == '.esm' else {}

    # FIDs and mod index handling
    @classmethod
    def format_fid(cls, whole_lo_fid: int, _fid_orig_plugin, mod_infos):
        """For non-ESL games simple hexadecimal formatting will do."""
        return f'{whole_lo_fid:08X}'

    @classmethod
    def get_indexes(cls, iter_infos, *, __scale_flags=scale_flags):
        real_indexes = defaultdict(lambda: (sys.maxsize, ''))
        indexes = Counter()
        indexes.update(scale_flags)
        for p, inf in iter_infos:
            for pflag in __scale_flags:
                if pflag.cached_type(inf):
                    dexstr = pflag.index_str(proper_index := indexes[pflag])
                    break
            else:
                dexstr = '%02X' % (proper_index := indexes[pflag := 'regular'])
            real_indexes[p] = (proper_index, dexstr)
            indexes[pflag] += 1
        return real_indexes

    # UI and menu info
    @classmethod
    def checkboxes(cls):
        """Return a dict of init params for the plugin flags checkboxes in
        the CreateNewPlugin dialog."""
        return {}

    @classmethod
    def plugin_counts(cls, mod_infos, active_mods):
        counts = Counter(dict.fromkeys((mem.name for mem in cls), 0))
        regular_count = 0
        for m in active_mods:
            for member in cls:
                if member.cached_type(m):
                    counts[member.name] += 1
                    break
            else:
                regular_count += 1
        return cls.count_str % {**counts, 'status_num': len(active_mods),
          'total_status_num': len(mod_infos), 'status_num_espm': regular_count}

    @classmethod
    def deactivate_msg(cls):
        return _('The following plugins have been deactivated '
                 'because only %(max_regular_plugins)d plugins '
                 'may be active at the same time.') % {
            'max_regular_plugins': cls.max_plugins}

    def __str__(self):
        return self.name

    def __repr__(self):
        return self.name

# easiest way to define enum class variables
PluginFlag.count_str = _('Mods: %(status_num)d/%(total_status_num)d')
PluginFlag.max_plugins = 255

class AMasterFlag(PluginFlag):
    """Master flags - affect load order - mutually compatible and compatible
    with scale flags."""

    def __init__(self, *args, **kwargs):
        kwargs.setdefault('convert_exts', ('.esp', '.esu'))
        super().__init__(*args, **kwargs)
        if self.name == 'ESM':
            self.help_flip = _('Flip the ESM flag on the selected plugins, '
                'turning masters into regular plugins and vice versa.')

    def _force_ext_flags(self, mod_info, game_handle, mext):
        if self is not self.ESM: # only check extension for esms
            return False
        if game_handle.fsName == 'Morrowind':
            ##: This is wrong, but works for now. We need game-specific
            # record headers to parse the ESM flag for MW correctly - #480!
            return mext == '.esm'
        elif game_handle.Esp.extension_forces_flags:
            # For games since FO4/SSE, .esm and .esl files set the master flag
            # in memory even if not set on the file on disk. For .esp files we
            # must check for the flag explicitly.
            return self in self.guess_flags(mext, game_handle)

    @classmethod
    def checkboxes(cls):
        return {cls.ESM: {'cb_label': _('ESM Flag'), 'chkbx_tooltip': _(
            'Whether or not the the resulting plugin will be a master, i.e. '
            'have the ESM flag.')}}

    @classmethod
    def sort_masters_key(cls, mod_inf) -> tuple[bool, ...]:
        """Return a key so that ESMs come first."""
        return not cls.ESM.cached_type(mod_inf),
