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
"""GameInfo class encapsulating static info for active game. Avoid adding
state and methods. game.GameInfo#init classmethod is used to import rest of
active game package as needed (currently the record and constants modules)
and to set some brec.RecordHeader/MreRecord class variables."""
import importlib
import re
import sys
from enum import Enum
from itertools import chain, product
from os.path import join as _j

from .. import bass, bolt, initialization
from ..plugin_types import MergeabilityCheck, PluginFlag, AMasterFlag, \
    isPBashMergeable
from ..bolt import FNDict, fast_cached_property
from ..exception import InvalidPluginFlagsError, ModError

# Constants and Helpers -------------------------------------------------------
# Files shared by versions of games that are published on the Windows Store
WS_COMMON_FILES = {'appxmanifest.xml'}

class ObjectIndexRange(Enum):
    """Valid values for object_index_range."""
    # FormIDs with object indices in the range 0x000-0x7FF are always
    # reserved for the engine
    RESERVED = 0
    # Plugins with a header version >= object_index_range_expansion_ver and at
    # least one master can use the range 0x000-0x7FF for their own purposes
    EXPANDED_CONDITIONAL = 1
    # Plugins with at least one master can use the range 0x001-0x7FF
    # for their own purposes
    EXPANDED_ALWAYS = 2

class _MasterFlag(AMasterFlag):
    """Enum with a single member for the Master flag."""
    ESM = ('esm_flag', '_is_master', 'm')

class _EslMixin(PluginFlag):
    """Mixin for ESL and newer games. The flags in this emum can not be set
    together but seems they are always compatible with AMasterFlag's."""
    _ignore_ = ('ESL', 'unflaggable', 'error_msgs', '_error_msgs') # typing
    unflaggable = {}
    _error_msgs = {}
    error_msgs = {}
    ESL = PluginFlag

    def __init__(self, flag_attr, mod_info_attr, ui_letter_key,
                 max_plugins=None, merge_check=None, offset=None, **kwargs):
        kwargs.setdefault('convert_exts', ('.esm', '.esp', '.esu'))
        super().__init__(flag_attr, mod_info_attr, ui_letter_key, **kwargs)
        self.max_plugins = max_plugins
        self.merge_check: MergeabilityCheck | None = merge_check
        self._offset = offset
        if self.name == 'ESL':
            self.help_flip = _('Flip the ESL flag on the selected plugins, '
                'turning light plugins into regular ones and vice versa.')

    # Additional API for ESL and newer games ----------------------------------
    def can_convert(self, modInfo, _minfos, reasons, _game_handle):
        """Determine whether the specified mod can be converted to our type.
        Optionally also return the reasons it can't be converted.

        :param modInfo: The mod to check.
        :param _minfos: Ignored. Needed to mirror the signature of
                        isPBashMergeable.
        :param reasons: A list of strings that should be filled with the
                        reasons why we can't flag this mod, or None if only the
                        return value of this method is of interest.
        :param _game_handle: unused - mirror the signature of isPBashMergeable.
        :return: True if we can flag the specified mod."""
        it = iter(self.unflaggable[self.name])
        ##: dragons - needs to generalize to arbitrary flag combinations and
        ##: be unified with validate_type - so we need changes in checkMods
        already_flagged, conflicting_flag = next(it)
        for mem in type(self):
            if mem.cached_type(modInfo):
                if reasons is None: return False
                reasons.append(already_flagged if mem is self else
                               conflicting_flag)
        chks = [*type(self).error_msgs[self].values()][:2] #len(it)=2 for OVERLAY
        try:
            return self.validate_type(modInfo, it, reasons, chks)
        except ModError as e:
            if reasons is not None: reasons.append(str(e))
            return False

    def validate_type(self, modinf, error_sets, reasons=None, merge_checks=None):
        merge_checks = merge_checks or type(self).error_msgs[self].values()
        for err_set, typecheck in zip(error_sets, merge_checks, strict=True):
            if typecheck(modinf):
                try:
                    err_set.add(modinf.fn_key)
                except AttributeError:
                    if reasons is None: return False
                    reasons.append(err_set)
        return not reasons

    @classmethod
    def check_flag_assignments(cls, flag_dict: dict[PluginFlag, bool],
                               raise_on_invalid=True):
        """Check if the flags in flag_dict are compatible."""
        set_true = [k for k, v in flag_dict.items() if k in cls and v]
        if raise_on_invalid and len(set_true) > 1:
            raise InvalidPluginFlagsError([k.name for k in set_true])
        elif not set_true:
            return flag_dict
        return {**flag_dict, **{ # set all other flags to False
            k: k in set_true for k in cls}}

    # Overrides ---------------------------------------------------------------
    def set_mod_flag(self, mod_info, set_flag, game_handle):
        if super().set_mod_flag(mod_info, set_flag, game_handle):
            return # we were passed a flags1 instance or we set the flag
        if self is type(self).ESL: # if ESL flag wasn't set check the extension
            setattr(mod_info, self._mod_info_attr,
                    mod_info.get_extension() == '.esl')

    @classmethod
    def guess_flags(cls, mod_fn_ext, game_handle, masters_supplied=()):
        return {game_handle.master_flags.ESM: True, cls.ESL: True} if \
            mod_fn_ext == '.esl' else super().guess_flags(
            mod_fn_ext, game_handle)

    @classmethod
    def format_fid(cls, whole_lo_fid, fid_orig_plugin, mod_infos):
        """Format a whole-LO FormID, which can exceed normal FormID limits
        (e.g. 211000800 is perfectly fine in a load order with ESLs), so
        that xEdit (and the game) can understand it."""
        orig_minf = mod_infos[fid_orig_plugin]
        proper_index = mod_infos.real_indices[fid_orig_plugin][0]
        for pflag in cls: ##: optimize this (and some few other pflag-loops)
            if pflag._offset and pflag.cached_type(orig_minf):
                return (f'FE{proper_index - pflag._offset:03X}'
                        f'{whole_lo_fid & 0x00000FFF:03X}')
        return f'{proper_index:02X}{whole_lo_fid & 0x00FFFFFF:06X}'

    @classmethod
    def checkboxes(cls):
        # Check the ESL checkbox by default for ESL games, since one of the
        # most common use cases for the create mod command on those games is
        # to create BSA-loading dummies.
        return {cls.ESL: {'cb_label': _('ESL Flag'), 'chkbx_tooltip': _(
            'Whether or not the resulting plugin will be '
            'light, i.e have the ESL flag.'), 'checked': True}}

    @classmethod
    def deactivate_msg(cls):
        return _('The following plugins have been deactivated because only '
            '%(max_regular_plugins)d regular plugins and %(max_esl_plugins)d '
            'ESL-flagged plugins may be active at the same time.') % {
                'max_regular_plugins': cls.max_plugins,
                'max_esl_plugins': cls.ESL.max_plugins}

_EslMixin.count_str = _('Mods: %(status_num)d/%(total_status_num)d (ESP/M: '
                        '%(status_num_espm)d, ESL: %(ESL)d)')
# EslMixin.ESL.name must always be 'ESL'
_EslMixin._error_msgs = {'ESL': {('=== ' + _('Incorrect ESL Flag'),
    _("The following plugins have an ESL flag, but do not qualify. Either "
      "remove the flag with 'Remove ESL Flag', or change the extension to "
      "'.esp' if it is '.esl'.")): lambda minfo:
                not minfo.formids_in_esl_range()}}
_EslMixin.unflaggable = {'ESL': [[_('This plugin is already ESL-flagged.'),
    _('This plugin has the Overlay flag.')],
    _('This plugin contains records with FormIDs greater than 0xFFF.')]}

class EslPluginFlag(_EslMixin, PluginFlag):
    # 4096 is hard limit, game runs out of fds sooner, testing needed
    ESL = ('esl_flag', '_is_esl', 'l', 4096,
           MergeabilityCheck.ESL_CHECK, 253)

class _SFPluginFlag(_EslMixin, PluginFlag):
    # order matters for UI keys
    ESL = ('esl_flag', '_is_esl', 'l', 4096,
           MergeabilityCheck.ESL_CHECK, 253)
    OVERLAY = ('overlay_flag', '_is_overlay', 'o', 0,
               MergeabilityCheck.OVERLAY_CHECK)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.name == 'OVERLAY':
            msg = _('WARNING! For advanced modders only!') + '\n\n' + _(
                'This command flips an internal bit in the mod, '
                'converting a regular plugin to an overlay plugin and '
                'vice versa. The Overlay flag is still new and our '
                'understanding of how it works may be incomplete. Back '
                'up your plugins and saves before using this!')
            self.continue_message = (
                msg, 'bash.flip_to_overlay.continue', _('Flip to Overlay'))
            self.help_flip = _(
                'Flip the Overlay flag on the selected plugins, turning '
                'overlay plugins into regular ones and vice versa.')

    def set_mod_flag(self, mod_info, set_flag, game_handle):
        if super().set_mod_flag(mod_info, set_flag, game_handle):
            return # we were passed a flags1 instance or the flag was set
        if self is (cls := type(self)).ESL:
            # .esl extension does not matter for overlay flagged plugins todo ESM?
            if not cls.OVERLAY.has_flagged(mod_info):
                setattr(mod_info, self._mod_info_attr,
                        mod_info.get_extension() == '.esl')

    @classmethod
    def checkboxes(cls):
        ttip = _('Whether or not the resulting plugin will only be able to '
                 'contain overrides, i.e. have the Overlay flag.')
        return {**super().checkboxes(), cls.OVERLAY: {
            'cb_label': _('Overlay Flag'), 'chkbx_tooltip': ttip}}

    @classmethod
    def guess_flags(cls, mod_fn_ext, game_handle, masters_supplied=()):
        sup = super().guess_flags(mod_fn_ext, game_handle)
        return sup if masters_supplied else {**sup, cls.OVERLAY: False}

_SFPluginFlag.count_str = _('Mods: %(status_num)d/%(total_status_num)d (ESP/M: '
                           '%(status_num_espm)d, ESL: %(ESL)d, Overlay: '
                           '%(OVERLAY)d)')
_SFPluginFlag._error_msgs = {**_EslMixin._error_msgs,
  _SFPluginFlag.OVERLAY.name: {
    ('=== ' + _('Incorrect Overlay Flag: No Masters'), _(
        "The following plugins have an Overlay flag, but do not qualify "
        "because they do not have any masters. %(game_name)s will not treat "
        "these as Overlay plugins. Either remove the flag with 'Remove "
        "Overlay Flag', or use %(xedit_name)s to add at least one master to "
        "the plugin.")): lambda minfo: not minfo.masterNames,
    ('=== ' + _('Incorrect Overlay Flag: New Records'), _(
        "The following plugins have an Overlay flag, but do not qualify "
        "because they contain new records. These will be injected into the "
        "first master of the plugins in question, which can seriously break "
        "basic game data. Either remove the flag with 'Remove Overlay "
        "Flag', or remove the new records.")): lambda minfo:
                minfo.has_new_records(),
    ('=== ' + _('Incorrect Overlay Flag: ESL-Flagged'), _(
        "The following plugins have an Overlay flag, but do not qualify "
        "because they also have an ESL flag. These flags are mutually "
        "exclusive. %(game_name)s will not treat these as overlay plugins. "
        "Either remove the Overlay flag with 'Remove Overlay Flag', or "
        "remove the ESL flag with 'Remove ESL Flag'.")): lambda minfo:
                _SFPluginFlag.ESL.cached_type(minfo),
}}
_SFPluginFlag.unflaggable = {**_EslMixin.unflaggable,
    _SFPluginFlag.OVERLAY.name: [[_('This plugin is already Overlay-flagged.'),
                               _('This plugin has the ESL flag.')],
                              _('This plugin does not have any masters.'),
                              _('This plugin contains new records.')]}

# Abstract class - to be overridden -------------------------------------------
class GameInfo(object):
    # Main game info - should be overridden -----------------------------------
    # The name of the game that will be shown to the user. That is its *only*
    # use! There are a few places where this is (mis)used for other purposes
    # left, those should be hunted down and replaced with dedicated game vars
    display_name = '' ## Example: 'Skyrim'
    # A name that must be 100% unique per game, but will also be shown in the
    # GUI (namely when picking what game to launch). This is automatically set
    # to display_name, with a (Store) suffix appended (e.g. (Steam)) by the
    # appropriate mixin classes (e.g. SteamMixin), so there is generally no
    # need to set it manually
    unique_display_name = '' ## Example: 'Skyrim Special Edition (Steam)'
    # A name used throughout the codebase for identifying the current game in
    # various situations, e.g. to decide which BSAs to use, which save header
    # types to use, etc. *DEPRECATED* for new uses - introduce dedicated game
    # vars instead
    fsName = u'' ## Example: u'Skyrim'
    # Alternate display name of Wrye Bash when managing this game
    altName = u'' ## Example: u'Wrye Smash'
    # Name of the icon to use for the game, including a %u specifier for the
    # icon size (16/24/32). Relative to images/games/
    game_icon = u'' ## Example: u'skyrim_%u.png'
    # Name of the prefix of the '<X> Mods' folder, i.e. <X> is this string.
    # Preferably pick a single word without spaces here, but don't change it
    # once set due to backwards compatibility (duh)
    bash_root_prefix = u'' ## Example: u'Skyrim'
    # Name of the prefix for the game folder inside created backups and for
    # naming backups. Should not be changed once set, otherwise restoring old
    # backups will no longer work
    bak_game_name = u''
    # The name of the directory, relative to Mopy/templates, in which the BSA
    # redirection template for this game is placed. This folder is
    # *deprecated*, see issue #519
    template_dir = u''
    # The name of the directory, relative to Mopy/Bash Patches, in which
    # default Bashed Patch resource files (e.g. CSV files) are stored. If
    # empty, indicates that WB does not come with any such files for this game
    bash_patches_dir = u''
    # True if the game uses the 'My Documents' folder, False to just use the
    # game path
    uses_personal_folders = True
    # Name of the folder in My Documents\My Games that holds this game's data
    # (saves, INIs, etc.)
    my_games_name = u''
    # Name of the game's AppData folder, relative to %LocalAppData%
    appdata_name = u''
    # The exe to use when launching the game (without xSE present)
    launch_exe = u'' ## Example: u'TESV.exe'
    # Path to one or more files to look for to see if this is the right game
    # when joined with the game's root path (i.e. the one above the Data
    # folder). The combination of these files must be unique among all games.
    # As a rule of thumb, use the file you specified in launch_exe, unless that
    # file is shared by multiple games, in which case you MUST find unique
    # files - for an example, see Enderal and Skyrim (and the SE versions of
    # both).
    game_detect_includes = set()
    # Path to one or more files to look for to see if this is *not* the right
    # game when joined with the game's root path. Used to differentiate between
    # versions of the game distributed on different platforms (at the moment
    # these are GOG, Steam and Windows Store).
    game_detect_excludes = set()
    # Path to a file to pass to env.get_file_version to determine the game's
    # version. Usually the same as launch_exe, but some games need different
    # ones here (e.g. Enderal, which has Skyrim's version in the launch_exe,
    # and therefore needs a different file here).
    version_detect_file = u''
    # The main plugin Wrye Bash should look for
    master_file: bolt.FName = bolt.FName('')
    # The directory in which mods and other data files reside. This is relative
    # to the game directory.
    mods_dir = u'Data'
    # The name of the directory containing the taglist for this game, relative
    # to 'Mopy/taglists'
    taglist_dir = u''
    # The name of the directory that LOOT writes its masterlist into, relative
    # to '%LocalAppData%\LOOT'
    loot_dir = u''
    # The name that this game has on the LOOT command line. If empty, indicates
    # that LOOT does not support this game
    loot_game_name = ''
    # The name that this game has on the BOSS command line. If empty, indicates
    # that BOSS does not support this game
    boss_game_name = u''
    # Registry keys to read to find the install location for GOG. This is a
    # list of tuples of two strings, where each tuple defines the subkey and
    # entry to try. Multiple tuples in the list will be tried in order, with
    # the first one that works being used. Generally automatically generated
    # via GOGMixin, so there is usually no need to fill this in manually.
    # These are relative to:
    #  HKLM\Software
    #  HKLM\Software\Wow6432Node
    #  HKCU\Software
    #  HKCU\Software\Wow6432Node
    # Example: [(r'Bethesda Softworks\Oblivion', 'Installed Path')]
    gog_registry_keys = []
    # Same as above, but for the old disc versions of games
    disc_registry_keys = []
    # URL to the Nexus site for this game
    nexusUrl = u''   # URL
    nexusName = u''  # Long Name
    nexusKey = u''   # Key for the "always ask this question" setting in
                     # settings.dat

    # Additional game info - override as needed -------------------------------
    # All file extensions used by plugins for this game
    espm_extensions = {u'.esm', u'.esp', u'.esu'}
    # Load order info
    using_txt_file = True
    # True if the game's CK has Bethesda.net export files (achlist files)
    has_achlist = False
    # What mergeability checks to perform for this game. See MergeabilityCheck
    # for more information
    mergeability_checks = {MergeabilityCheck.MERGE: isPBashMergeable}
    # enum type of supported plugin flags - by default empty
    plugin_flags = PluginFlag
    # enum type of supported master plugin flags
    master_flags = _MasterFlag
    # Whether or not this game has standalone .pluggy cosaves
    has_standalone_pluggy = False
    # Information about Plugin-Name-specific Directories supported by this
    # game. Some examples are sound\voice\PLUGIN_NAME.esp, or the facegendata
    # ones. An empty list means that the game does not have any such
    # directories.
    plugin_name_specific_dirs = [_j('sound', 'voice')]
    # Whether or not to check for 'Bash' and 'Installers' folders inside the
    # game folder and use those instead of the default paths when present
    check_legacy_paths = False
    # define which types will have color key/mouse text - impose priority order
    plugin_type_text = {
        'l': _('Light plugin.'),
        'o': _('Overlay plugin.'),
        'b': _('Blueprint plugin.'),
        'm': _('Master plugin.'),
        'lm': _('Light Master plugin.'),
        'om': _('Overlay Master plugin.'),
        'bm': _('Blueprint Master plugin.'),
    }

    def __init__(self, gamePath, *args):
        self.gamePath = gamePath # absolute bolt Path to the game directory
        #--Initialize Directories to perform backup/restore operations
        #--They depend on setting the bash.ini and the game
        if args:
            self.game_ini_path = initialization.init_dirs(self, *args)
        self._init_plugin_types()

    # Master esm form ids factory
    __master_fids = {}
    @classmethod
    def master_fid(cls, object_id):
        """Create a FormId subclass representing a particular master record."""
        try:
            return cls.__master_fids[object_id]
        except KeyError:
            from .. import brec
            return cls.__master_fids.setdefault(object_id,
                brec.FormId.from_tuple((cls.master_file, object_id)))

    @staticmethod
    def get_fid_class(augmented_masters, in_overlay_plugin):
        from ..brec import FormId
        class _FormID(FormId):
            @fast_cached_property
            def long_fid(self, *, __masters=augmented_masters):
                try:
                    return __masters[self.mod_dex], self.short_fid & 0xFFFFFF
                except IndexError:
                    # Clamp HITMEs to the plugin's own address space
                    return __masters[-1], self.short_fid & 0xFFFFFF
        return _FormID

    class St:
        """Information about this game on Steam."""
        # The app IDs on Steam. An empty list indicates the game is not
        # available on Steam
        steam_ids = []

    class Ws(object):
        """Information about this game on the Windows Store."""
        # The publisher name for common games. Only needed for games that had
        # the older legacy installation method available. Can only be
        # 'Bethesda' or empty
        legacy_publisher_name = ''
        # The internal name used by the Windows Store to identify the game.
        # For example, Morrowind is 'BethesdaSofworks.TESMorrowind-PC'
        win_store_name = ''
        # A list of directory names for different language versions that ship
        # with this game. Each one acts as a separate game installation under
        # the main Windows Store path. If empty, indicates that the main path
        # *is* the game installation
        ws_language_dirs = []

    class Eg:
        """Information about this game on the Epic Games Store."""
        # The AppName in the Epic Games Store manifest for this game. May
        # contain multiple, in which case the first one that is present is
        # used. Empty if this game is not available on the Epic Games Store
        egs_app_names = []
        # A list of directory names for different language versions that ship
        # with this game. Each one acts as a separate game installation under
        # the main Epic Games Store path. If empty, indicates that the main path
        # *is* the game installation
        egs_language_dirs = []

    class Ck(object):
        """Information about the official plugin editor (generally called some
        variation of 'Creation Kit') for this game."""
        # Abbreviated name. If not present, indicates that this game does not
        # have an official plugin editor
        ck_abbrev = u''
        # Full name
        long_name = u''
        # Executable to run
        exe = u'*DNE*'
        # Argument to pass to the script extender to load the CK. If None,
        # indicates that this game's script extender does not have this feature
        se_args = ()
        # Image name template for the status bar, relative to images/tools
        image_name = ''

    class Se(object):
        """Information about the Script Extender for this game."""
        # Abbreviated name. If this is empty, it signals that no xSE is
        # available for this game. Note that this should NEVER be used to
        # program other xSE behavior - create new variables like plugin_dir and
        # cosave_ext instead.
        se_abbrev = u''
        # Full name
        long_name = u''
        # Exe to run
        exe = u''
        # List of file names to use for version detection. Tried in order until
        # one exists. Needed because it's technically not required to install
        # the EXE.
        ver_files = []
        # One level above the directory in which xSE plugins should be placed
        # (e.g. when plugins should be in Data\OBSE\Plugins, this should be
        # u'OBSE')
        plugin_dir = u''
        # The magic tag that the cosaves use (e.g. u'SKSE'). If this is empty,
        # it signals that this script extender has no cosaves.
        cosave_tag = u''
        # The extension that the cosaves use (e.g. u'.skse')
        cosave_ext = u''
        # URL to download from
        url = u''
        # Tooltip for mouse over the URL
        url_tip = u''
        # A list of xSE plugins that fix the plugin/BSA handle problem. Empty
        # if that does not apply to this game.
        limit_fixer_plugins = []

        @classmethod
        def exe_path_sc(cls):
            exe_xse = bass.dirs['app'].join(cls.exe)
            return exe_xse if exe_xse.is_file() else None

    class Sd(object):
        """Information about Script Dragon for this game."""
        # Abbreviated name. If this is empty, it signals that no Script Dragon
        # is available for this game.
        sd_abbrev = u''
        # Full name
        long_name = u''
        # The directory, relative to the Data folder, into which Script Dragon
        # plugins will be installed.
        install_dir = u''

    class Sp(object):
        """Information about SkyProc patchers for this game."""
        # Abbreviated name. If this is empty, it signals that this game does
        # not support SkyProc patchers.
        sp_abbrev = u''
        # Full name
        long_name = u''
        # The directory, relative to the Data folder, into which SkyProc
        # patchers will be installed.
        install_dir = u''

    class Ge(object):
        """Information about the Graphics Extender for this game."""
        # Abbreviated name. If this is empty, it signals that no graphics
        # extender is available for this game.
        ge_abbrev = u''
        # Full name
        long_name = u''
        # exe is treated specially here.  If it is a string, then it should
        # be the path relative to the root directory of the game, if it is
        # a list, each list element should be an iterable to pass to Path.join
        # relative to the root directory of the game.  In this case,
        # each filename will be tested in reverse order.  This was required
        # for Oblivion, as the newer OBGE has a different filename than the
        # older OBGE
        exe = u''
        # URL to download from
        url = u''
        # Tooltip for mouse over the URL
        url_tip = u''

    class Ini(object):
        """Information about this game's INI handling."""
        # True means new lines are allowed to be added via INI tweaks
        # (by default)
        allow_new_lines = True
        # INI Entry to enable BSA Redirection - two empty strings if this game
        # does not need BSA redirection
        bsa_redirection_key = (u'', u'')
        # Name of game's default ini file.
        default_ini_file = u''
        # The default value for the [General] sLanguage setting
        default_game_lang = 'English'
        # INI files that should show up in the INI Edits tab. Note that the
        # first one *must* be the main INI!
        #  Example: [u'Oblivion.ini']
        dropdown_inis = []
        # Whether or not this game supports the OBSE INI format
        has_obse_inis = False
        # INI setting used to setup Save Profiles
        #  (section, key)
        save_profiles_key = (u'General', u'SLocalSavePath')
        # Base dir for the save_profiles_key setting above
        save_prefix = u'Saves'
        # INI setting used to enable or disable screenshots
        #  (section, key, default value)
        screenshot_enabled_key = (u'Display', u'bAllowScreenShot', u'1')
        # INI setting used to set base screenshot name
        #  (section, key, default value)
        screenshot_base_key = (u'Display', u'sScreenShotBaseName',
                               u'ScreenShot')
        # INI setting used to set screenshot index
        #  (section, key, default value)
        screenshot_index_key = (u'Display', u'iScreenShotIndex', u'0')
        # The INI entries listing vanilla BSAs to load - those are loaded first
        # so make sure they come first by assigning negative indexes
        BSA_MIN, BSA_MAX = -sys.maxsize + 1, sys.maxsize
        start_dex_keys = {}
        engine_overrides = [] # SkyrimVR only - see there
        # Whether this game supports mod ini files aka ini fragments
        supports_mod_inis = True

        @classmethod
        def get_bsas_from_inis(cls, av_bsas, *ini_files_cached):
            """Get the load order of INI-loaded BSAs - in the vicinity of
            ±sys.maxsize. These BSAs are removed from av_bsas dict."""
            bsa_lo = {}
            bsa_cause = {}  # Reason each BSA was loaded
            for group_dex, (ini_idx, keys) in enumerate(
                    cls.start_dex_keys.items()):
                bsas_cause = []
                for ini_k in keys:
                    for ini_f in ini_files_cached: # higher loading first
                        if bsas := ini_f.getSetting('Archive', ini_k, ''):
                            bsas = (x.strip() for x in bsas.split(','))
                            bsas_cause.append(([av_bsas[b] for b in bsas
                                                if b in av_bsas],
                                f'{ini_f.abs_path.stail} ({ini_k})'))
                            break # The first INI with the key wins ##: Test this
                if not bsas_cause and group_dex == 1:
                    # fallback to the defaults set by the engine - must exist!
                    bsas_cause = [([av_bsas[b] for b in cls.engine_overrides],
                                   f'{cls.dropdown_inis[0]} ({keys[0]})')]
                for res_ov_bsas, res_ov_cause in bsas_cause:
                    for binf in res_ov_bsas:
                        bsa_lo[binf] = ini_idx
                        bsa_cause[binf] = res_ov_cause
                        # note the last entries load higher if ini_idx < 0 else
                        # lower (games with BSA_MAX keys if len(res_ov_bsas)>1)
                        ini_idx -= -1 if ini_idx < 0 else 1
                        del av_bsas[binf.fn_key]
            return bsa_lo, bsa_cause

    class Ess(object):
        """Information about WB's capabilities regarding save file
        viewing and editing for this game."""
        # Can read the info needed for the Save Tab display
        canReadBasic = True
        # Advanced editing
        canEditMore = False
        # If True, then this game will reliably and safely remove a missing
        # master from an existing save if you just load the game without that
        # master
        can_safely_remove_masters = False
        # Save file extension
        ext = u'.ess'
        # Whether or not this game has screenshots in its savegames
        has_screenshots = True

    class Bsa(object):
        """Information about the BSAs (Bethesda Archives) used by this game."""
        # Whether or not the INI setting ResetBSATimestamps should have any
        # effect on this game
        allow_reset_timestamps = False
        # Part of a regex used to determine which BSAs will attach to a plugin.
        # The full regex prepends the base name of the plugin (e.g. for
        # MyMod.esp, MyMod will be prepended) and appends Bsa.bsa_extension.
        # Most games accept arbitrary BSA names, hence this default
        attachment_regex = r'(?: \- \w+)?'
        # The extension used for BSA files
        bsa_extension = u'.bsa'
        # Whether or not the Archive.exe tool for this game creates BSL files
        has_bsl = False
        # Maps BSA names to the date to which they should be redated. Fallback
        # will be used for BSAs which are not explicitly listed. We hardcode
        # time.mktime result due to locale issues. Generally used to redate
        # the vanilla BSAs before all mod BSAs, and all BSAs before loose
        # files by choosing dates older than the game's release date.
        redate_dict = bolt.DefaultFNDict(lambda: 1136066400) # '2006-01-01'
        # All BSA versions accepted by this game. If empty, indicates that this
        # game does not use BSA versions and so BSA version checks will be
        # skipped entirely.
        valid_versions = set()

        _str_heuristics = tuple(enumerate(('main', 'interface')))
        @classmethod
        def heuristic_sort_key(cls, master_bsa_inf, ini_loaded):
            """Heuristics key to order ini-loaded bsas which might contain
            localized string files. Sort 'main', 'patch' and 'interface' to
            the front then follow the INI load order placing higher loading
            bsas first. Avoids parsing expensive BSAs for the game master
            strings (e.g. Skyrim.esm -> Skyrim - Textures0.bsa)."""
            bsa_body_lo = master_bsa_inf.fn_key.fn_body.lower()
            ini_lo = -ini_loaded[master_bsa_inf] # sort higher loading first
            for i, h in cls._str_heuristics:
                if h in bsa_body_lo:
                    return i, ini_lo
            return len(cls._str_heuristics), ini_lo

        @classmethod
        def attached_bsas(cls, bsa_infos, plugin_fn):
            """Return a list of all BSAs that the game will attach to
            plugin_fn."""
            bsa_pattern = (re.escape(plugin_fn.fn_body) +
                           f'{cls.attachment_regex}\\{cls.bsa_extension}')
            is_attached = re.compile(bsa_pattern, re.I).match
            return [binf for k, binf in bsa_infos.items() if is_attached(k)]

        @classmethod
        def update_bsa_lo(cls, lo, av_bsas, bsa_lodex, cause):
            # BSAs loaded based on plugin name load in the middle of the pack
            for i, p in enumerate(lo):
                for binf in cls.attached_bsas(av_bsas, p):
                    bsa_lodex[binf] = i
                    cause[binf] = p
                    del av_bsas[binf.fn_key]

    class Psc(object):
        """Information about script sources (only Papyrus right now) for this
        game."""
        # Extensions for external script sources. Empty if this game doesn't
        # have any.
        source_extensions = set()
        # Maps directories from which BAIN should redirect script sources from
        # to the directories that BAIN should redirect them to. Empty if this
        # is not applicable to this game.
        source_redirects = {}

    class Xe(object):
        """Information about xEdit for this game."""
        # The name that xEdit has for this game, e.g. 'TES5Edit' for Skyrim
        full_name = 'xEdit'
        # A prefix for settings keys related to this version of xEdit (e.g.
        # expert mode)
        xe_key_prefix = ''

    class Bain(object):
        """Information about what BAIN should do for this game. All strings in
        here must be lower-cased!"""
        # The allowed default data directories that BAIN can install to
        data_dirs = {
            'ini',
            'meshes',
            'music',
            'sound',
            'textures',
            'video'
        }
        # Directories in the Data folder to exclude from Clean Data
        keep_data_dirs = set()
        # Files in the Data folder to exclude from Clean Data
        keep_data_files = set()
        # File prefixes in the Data folder to exclude from Clean Data
        keep_data_file_prefixes = set()
        # The directory into which LOD meshes are installed
        lod_meshes_dir = _j('meshes', 'lod')
        # The directory into which LOD textures are installed
        lod_textures_dir = _j('textures', 'lod')
        # The suffix that LOD textures used as normals have in this game
        lod_textures_normals_suffix = '_n'
        # Literal file paths BAIN shouldn't skip
        no_skip = set()
        # Directories where specific file extensions should not be skipped
        no_skip_dirs = {
            # BashTags files are obviously not docs, so don't skip them
            'bashtags': {'.txt'},
        }
        # Compiled regex patterns matching files BAIN shouldn't skip
        no_skip_regexes = ()
        # Folders BAIN should never CRC check in the Data directory
        skip_bain_refresh = set(
            # Use lowercase names
        )
        # Wrye Bash files to exclude from Clean Data
        wrye_bash_data_files = set()
        # Wrye Bash directories to install and exclude from Clean Data
        wrye_bash_data_dirs = {'bash patches', 'bashtags', 'ini tweaks'}

    # Plugin format stuff
    class Esp(object):
        """Information about plugins."""
        # WB can create Bashed Patches
        canBash = False
        # WB can edit basic info in the main header record - generally has
        # signature b'TES4'
        canEditHeader = False
        # If True, check if the main header's DATA subrecords match the on-disk
        # master sizes and highlight the corresponding masters with a light
        # background color if that is the case. Needs meaningful information in
        # the DATA subrecords.
        check_master_sizes = False
        # If True, then plugins with a .esm extension will always be treated
        # as having the ESM flag set and plugins with a .esl extension will
        # always be treated as having the ESL and ESM flags set
        extension_forces_flags = False
        # If True, generate ONAM by reading each temp CELL child when adding
        # the ESM flag to plugins and discard it when removing the ESM flag.
        generate_temp_child_onam = False
        # The maximum number of masters that a plugin can have for this game.
        master_limit = 255
        # Maximum length of the Author string in the plugin header
        max_author_length = 511 # 512 - 1 for the null terminator
        # Maximum length of the Description string in the plugin header
        max_desc_length = 511 # 512 - 1 for the null terminator
        # The maximum number of entries inside a leveled list for this game.
        # Zero means no limit.
        max_lvl_list_size = 0
        # Determines the range of object indices that plugins are allowed to
        # use. See ObjectIndexRange for more details
        object_index_range = ObjectIndexRange.RESERVED
        # If object_index_range is ObjectIndexRange.EXPANDED_CONDITIONAL, this
        # indicates the minimum header version required to use the expanded
        # range
        object_index_range_expansion_ver = 0.0
        # Signature of the main plugin header record type
        plugin_header_sig = b'TES4'
        # Whether to sort LVSPs after SPELs in actors (CREA/NPC_)
        ##: Workaround, see MelSpellsTes4 for the proper solution
        sort_lvsp_after_spel = False
        # used to locate string translation files
        stringsFiles = [
            u'%(body)s_%(language)s.STRINGS',
            u'%(body)s_%(language)s.DLSTRINGS',
            u'%(body)s_%(language)s.ILSTRINGS',
        ]
        # Valid ESM/ESP header versions. These are the valid 'version' numbers
        # for the game file headers
        validHeaderVersions = tuple()
        # Whether to warn about plugins with header form
        # versions < RecordHeader.plugin_form_version
        warn_older_form_versions = False

    # Class attributes moved to constants module, set dynamically at init
    #--Game ESM/ESP/BSA files
    ## These are all of the ESM,ESP,and BSA data files that belong to the game
    ## These filenames need to be in lowercase,
    bethDataFiles = set()

    # Known record types - maps integers from the save format to human-readable
    # names for the record types. Used in save editing code.
    save_rec_types = {}

    # Set in game/*/default_tweaks.py, this is a dictionary mapping names for
    # 'default' INI tweaks (i.e. ones that we ship with WB and that can't be
    # deleted) to OrderedDicts that implement the actual tweaks. See
    # DefaultIniInfo.__init__ for how the tweaks are parsed.
    default_tweaks = {}

    # Set in game/*/vanilla_files.py, this is a set listing every file that
    # exists in the Data directory of the game in a purely vanilla
    # installation. Set in a separate file because this can be *very* large,
    # and would make editing the constants a miserable experience if included
    # (see e.g. skyrim/vanilla_files.py).
    vanilla_files = set()
    # property fields set in _init_records to avoid brec import
    _plugin_header_rec_type = None

    @property
    def plugin_header_class(self):
        return self._plugin_header_rec_type

    @fast_cached_property
    def modding_esm_size(self):
        # Hack to avoid a bunch of overrides
        if self.display_name != 'Oblivion':
            return FNDict()
        b, e = self.master_file.rsplit('.', 1)
        return FNDict({
            f'{b}_1.1.{e}':         247388848, #--Standard
            f'{b}_1.1b.{e}':        247388894, # Arthmoor has this size.
            f'{b}_GOTY non-SI.{e}': 247388812, # GOTY version
            f'{b}_SI.{e}':          277504985, # Shivering Isles 1.2
            f'{b}_GBR SI.{e}':      260961973, # GBR Main File Patch
        })

    @fast_cached_property
    def size_esm_version(self):
        return {y: x.split('_', 1)[1].rsplit('.', 1)[0] for x, y in
                self.modding_esm_size.items()}

    def modding_esms(self, mod_infos):
        """Set current (and available) master game esm(s) - Oblivion only."""
        if not self.modding_esm_size: return set(), None
        version_strs = set()
        for modding_esm, esm_size in self.modding_esm_size.items():
            if (info := mod_infos.get(modding_esm)) and info.fsize == esm_size:
                version_strs.add(self.size_esm_version[esm_size])
        current_esm = self.size_esm_version.get(
            mod_infos[self.master_file].fsize, None)
        return version_strs, current_esm

    @classmethod
    def init(cls, _package_name=None):
        """Dynamically import modules - Record[Type] variables not yet set!

        :param _package_name: the name of the game package to load if loading
                              from a derived game - used internally - don't
                              pass!"""
        cls._dynamic_import_modules(_package_name) # this better be not None

    @classmethod
    def _dynamic_import_modules(cls, package_name):
        """Dynamically import package modules to avoid importing them for every
        game. We need to pass the package name in for importlib to work.
        Populates the GameInfo namespace with the members defined in
        default_tweaks.py and vanilla_files.py and also imports game
        specific patchers. The patcher modules should not rely on records
        being initialized."""
        tweaks_module = importlib.import_module(u'.default_tweaks',
            package=package_name)
        cls.default_tweaks = tweaks_module.default_tweaks
        vf_module = importlib.import_module(u'.vanilla_files',
            package=package_name)
        cls.vanilla_files = vf_module.vanilla_files

    def _init_plugin_types(self, pflags=None):
        """Initialize plugin types for this game. This runs after all game
        directories have been set (see _ASkyrimVRGameInfo override) and
        *after* all overrides."""
        self.has_esl = '.esl' in self.espm_extensions
        pflags = pflags or (self.has_esl and EslPluginFlag)
        def _prod(*its):
            return (s for tup_str in product(*its) if (s := ''.join(tup_str)))
        if pflags:
            self.plugin_flags = pflags
            self.mergeability_checks = {mc: pflag.can_convert for pflag in
                pflags if (mc := pflag.merge_check) is not None}
            fmt = {'xedit_name': self.Xe.full_name,
                   'game_name': self.display_name}
            pflags.error_msgs = {
                pflags[k]: {(h, msg % fmt): lam for (h, msg), lam in v.items()}
                for k, v in pflags._error_msgs.items()}
            scale_flags = [f for f in pflags if f._offset is not None]
            # leave magic 255 below we might re-initialize!
            PluginFlag.max_plugins = 255 - len(scale_flags)
        pflags = self.plugin_flags
        master_suffixes = ['', *_prod(*
            (('', f.ui_letter_key) for f in self.master_flags))]
        type_prefixes = ['', *_prod(*(('', f.ui_letter_key) for f in pflags))]
        # plugin flags are mutually exclusive - generate mouse texts
        forbidden_suffixes = [su for su in type_prefixes if len(su) > 1]
        letter_flag = {f.ui_letter_key: f for f in pflags}
        con = _('Conflicting flags: %(conf_flags)s')
        flag_conflicts = {su: ', '.join(sorted(letter_flag[le].name
            for le in su)) for su in forbidden_suffixes}
        flag_conflicts = {su: con % {'conf_flags': flag_names} for
                          su, flag_names in flag_conflicts.items()}
        # add master suffixes to the forbidden suffixes
        self.forbidden_suffixes = {forb: fconf_msg for su, fconf_msg in
            flag_conflicts.items() for forb in _prod([su], master_suffixes)}
        # add the rest of the mouse texts
        combinations = {*_prod(
            [s for s in type_prefixes if s not in forbidden_suffixes],
            master_suffixes)}
        self.mod_keys = [f'mods.text.es{suff}' for suff in
                         self.plugin_type_text if suff in combinations]
        if self.mergeability_checks:
            self.mod_keys.append('mods.text.mergeable')
            if MergeabilityCheck.MERGE in self.mergeability_checks:
                self.mod_keys.append('mods.text.noMerge')
        if self.Esp.canBash:
            self.mod_keys.append('mods.text.bashedPatch')
        if self.forbidden_suffixes:
            self.mod_keys.append('mods.text.flags_conflict')

    @classmethod
    def supported_games(cls):
        game_types = set(cls.__subclasses__())
        game_types.update(
            chain.from_iterable(c.__subclasses__() for c in list(game_types)))
        return game_types

    @classmethod
    def test_game_path(cls, test_path):
        """Helper method to determine if required game detection files are
           present, and no excluded files are present, in the test path."""
        return (all(test_path.join(p).exists()
                for p in cls.game_detect_includes) and not
                any(test_path.join(p).exists()
                for p in cls.game_detect_excludes))

# The GameInfo-derived type used for this game, to be set by each game package
GAME_TYPE: type[GameInfo] | dict[str, type[GameInfo]]
