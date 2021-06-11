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
#  Wrye Bash copyright (C) 2005-2009 Wrye, 2010-2021 Wrye Bash Team
#  https://github.com/wrye-bash
#
# =============================================================================
"""GameInfo class encapsulating static info for active game. Avoid adding
state and methods. game.GameInfo#init classmethod is used to import rest of
active game package as needed (currently the record and constants modules)
and to set some brec.RecordHeader/MreRecord class variables."""

import importlib
from collections import defaultdict
from itertools import chain
from os.path import join as _j

from .. import brec

class GameInfo(object):
    # Main game info - should be overridden -----------------------------------
    # Name of the game to use in UI.
    displayName = u'' ## Example: u'Skyrim'
    # A name used throughout the codebase for identifying the current game in
    # various situations, e.g. to decide which BSAs to use, which save header
    # types to use, etc.
    fsName = u'' ## Example: u'Skyrim'
    # Alternate display name of Wrye Bash when managing this game
    altName = u'' ## Example: u'Wrye Smash'
    # Name of the icon to use for the game, including a %u specifier for the
    # icon size (16/24/32)
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
    game_detect_includes = []
    # Path to one or more files to look for to see if this is *not* the right
    # game when joined with the game's root path. Used to differentia between
    # versions of the game distributed on different platforms (Windows Store).
    game_detect_excludes = []
    # Path to a file to pass to env.get_file_version to determine the game's
    # version. Usually the same as launch_exe, but some games need different
    # ones here (e.g. Enderal, which has Skyrim's version in the launch_exe,
    # and therefore needs a different file here).
    version_detect_file = u''
    # The main plugin Wrye Bash should look for
    master_file = u''
    # The directory in which mods and other data files reside. This is relative
    # to the game directory.
    mods_dir = u'Data'
    # The name of the directory containing the taglist for this game, relative
    # to 'Mopy/taglists'
    taglist_dir = u''
    # The name of the directory that LOOT writes its masterlist into, relative
    # to '%LocalAppData%\LOOT'
    loot_dir = u''
    # The name that this game has on the BOSS command line. If empty, indicates
    # that BOSS does not support this game
    boss_game_name = u''
    # Registry keys to read to find the install location
    # These are relative to:
    #  HKLM\Software
    #  HKLM\Software\Wow6432Node
    #  HKCU\Software
    #  HKCU\Software\Wow6432Node
    # Example: (u'Bethesda Softworks\\Oblivion', u'Installed Path')
    regInstallKeys = ()
    # URL to the Nexus site for this game
    nexusUrl = u''   # URL
    nexusName = u''  # Long Name
    nexusKey = u''   # Key for the "always ask this question" setting in
                     # settings.dat

    # Additional game info - override as needed -------------------------------
    # URL to download patches for the main game.
    patchURL = u''
    # Tooltip to display over the URL when displayed
    patchTip = u'Update via Steam'
    # plugin extensions
    espm_extensions = {u'.esm', u'.esp', u'.esu'}
    # Load order info
    using_txt_file = True
    # bethesda net export files
    has_achlist = False
    # check if a plugin is convertible to a light master instead of checking
    # mergeability
    check_esl = False
    # Whether or not this game has standalone .pluggy cosaves
    has_standalone_pluggy = False
    # Information about Plugin-Name-specific Directories supported by this
    # game. Some examples are sound\voices\PLUGIN_NAME.esp, or the facegendata
    # ones. An empty list means that the game does not have any such
    # directories.
    plugin_name_specific_dirs = [_j(u'sound', u'voice')]

    def __init__(self, gamePath):
        self.gamePath = gamePath # absolute bolt Path to the game directory
        self.has_esl = u'.esl' in self.espm_extensions

    class Ws(object):
        """Information about this game on the Windows Store."""
        # A list of directory names for different language versions that ship
        # with this game. Each one acts as a separate game installation under
        # the main Windows Store path. If empty, indicates that the Windows
        # Store location is the game installtion
        game_language_dirs = []
        # The publisher name for common games. Currently only 'Bethesda' is
        # allowed for Bethesda games. If specified, publisher_id is not
        # required
        publisher_name = u''
        # The publisher ID for the publisher of the game. Required except for
        # common publishers supported above. For example, Bethesda's publisher
        # ID is '3275kfvn8vcwc'
        publisher_id = u''
        # The internal name used by the Windows Store to identify the game.
        # For example, Morrowind is 'BethesdaSofworks.TESMorrowind-PC'
        win_store_name = u''

    class Ck(object):
        """Information about the official plugin editor (generally called some
        variation of 'Creation Kit') for this game."""
        # Abbreviated name
        ck_abbrev = u''
        # Full name
        long_name = u''
        # Executable to run
        exe = u'*DNE*'
        # Argument to pass to the script extender to load the CK. If None,
        # indicates that this game's script extender does not have this feature
        se_args = None
        # Image name template for the status bar
        image_name = u''

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

    class Laa(object):
        """Information about the LAA (Large Address Aware) launcher for this
        game."""
        # Display name of the launcher
        laa_name = u''
        # Executable to run
        exe = u'*DNE*'
        # Whether the launcher will automatically launch the SE
        launchesSE = False

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
        # INI files that should show up in the INI Edits tab. Note that the
        # first one *must* be the main INI!
        #  Example: [u'Oblivion.ini']
        dropdown_inis = []
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
        # The INI entries listing vanilla BSAs to load
        resource_archives_keys = ()
        # An INI key listing BSAs that will override all plugin BSAs. Blank if
        # it doesn't exist for this game
        resource_override_key = u''
        # The default value for resource_override_key if it's missing from the
        # game INI
        resource_override_defaults = []
        # Whether this game supports mod ini files aka ini fragments
        supports_mod_inis = True

    class Ess(object):
        """Information about WB's capabilities with regards to save file
        viewing and editing for this game."""
        # Can read the info needed for the Save Tab display
        canReadBasic = True
        # Advanced editing
        canEditMore = False
        # Save file extension
        ext = u'.ess'
        # If True, then this game will reliably and safely remove a missing
        # master from an existing save if you just load the game without that
        # master
        can_safely_remove_masters = False

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
        # will be used for BSAs which are not explicitly listed. Format is
        # ISO 8601 (year-month-day). Generally used to redate the vanilla BSAs
        # before all mod BSAs, and all BSAs before loose files by choosing
        # dates older than the game's release date.
        redate_dict = defaultdict(lambda: u'2006-01-01')
        # All BSA versions accepted by this game. If empty, indicates that this
        # game does not use BSA versions and so BSA version checks will be
        # skipped entirely.
        valid_versions = set()

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
        full_name = u'xEdit'
        # A prefix for settings keys related to this version of xEdit (e.g.
        # expert mode)
        xe_key_prefix = u''

    class Bain(object):
        """Information about what BAIN should do for this game."""
        # The allowed default data directories that BAIN can install to
        data_dirs = {
            u'ini',
            u'meshes',
            u'music',
            u'sound',
            u'textures',
            u'video'
        }
        # Directories in the Data folder to exclude from Clean Data
        keep_data_dirs = set()
        # Files in the Data folder to exclude from Clean Data
        keep_data_files = set()
        # File prefixes in the Data folder to exclude from Clean Data
        keep_data_file_prefixes = set()
        # Files BAIN shouldn't skip
        no_skip = ()
        # Directories where specific file extensions should not be skipped
        no_skip_dirs = {
            # BashTags files are obviously not docs, so don't skip them
            u'bashtags': [u'.txt'],
        }
        # Folders BAIN should never CRC check in the Data directory
        skip_bain_refresh = set(
            # Use lowercase names
        )
        # Wrye Bash files to exclude from Clean Data
        wrye_bash_data_files = set()
        # Wrye Bash directories to exclude from Clean Data
        wrye_bash_data_dirs = {u'Bash Patches', u'BashTags', u'INI Tweaks'}

    # Plugin format stuff
    class Esp(object):
        # Wrye Bash capabilities
        # Can create Bashed Patches
        canBash = False
        # Can edit basic info in the main header record - generally has
        # signature b'TES4'
        canEditHeader = False
        # Valid ESM/ESP header versions. These are the valid 'version' numbers
        # for the game file headers
        validHeaderVersions = tuple()
        # used to locate string translation files
        stringsFiles = [
            u'%(body)s_%(language)s.STRINGS',
            u'%(body)s_%(language)s.DLSTRINGS',
            u'%(body)s_%(language)s.ILSTRINGS',
        ]
        # Signature of the main plugin header record type
        plugin_header_sig = b'TES4'
        # If True, then plugins with at least one master can use the
        # 0x000-0x800 range for their own records.
        # If False, that range is reserved for hardcoded engine records.
        expanded_plugin_range = False
        # If True, check if the main header's DATA subrecords match the on-disk
        # master sizes and highlight the corresponding masters with a light
        # background color if that is the case. Needs meaningful information in
        # the DATA subrecords.
        check_master_sizes = False
        # If True, generate ONAM by reading each temp CELL child when adding
        # the ESM flag to plugins and discard it when removing the ESM flag.
        generate_temp_child_onam = False
        # The maximum number of entries inside a leveled list for this game.
        # Zero means no limit.
        max_lvl_list_size = 0
        # A tuple containing all biped flag names (in order) for this game
        biped_flag_names = ()
        # The maximum number of masters that a plugin can have for this game.
        master_limit = 255 # 256 - 1 for the plugin itself
        # All 'reference' types, i.e. record types that occur in CELL/WLRD
        # groups and place some sort of thing into the cell (e.g. ACHR, REFR,
        # PMIS, etc.)
        reference_types = set()

    # Class attributes moved to constants module, set dynamically at init
    #--Game ESM/ESP/BSA files
    ## These are all of the ESM,ESP,and BSA data files that belong to the game
    ## These filenames need to be in lowercase,
    bethDataFiles = set()  # initialize with literal

    # Known record types - maps integers from the save format to human-readable
    # names for the record types. Used in save editing code.
    save_rec_types = {}

    # Set in game/*/default_tweaks.py, this is a dictionary mapping names for
    # 'default' INI tweaks (i.e. ones that we ship with WB and that can't be
    # deleted) to OrderedDicts that implement the actual tweaks. See
    # DefaultIniFile.__init__ for how the tweaks are parsed.
    default_tweaks = {}

    # Set in game/*/vanilla_files.py, this is a set listing every file that
    # exists in the Data directory of the game in a purely vanilla
    # installation. Set in a separate file because this can be *very* large,
    # and would make editing the constants a miserable experience if included
    # (see e.g. skyrim/vanilla_files.py).
    vanilla_files = set()

    @property
    def plugin_header_class(self):
        return brec.MreRecord.type_class[self.Esp.plugin_header_sig]

    @classmethod
    def init(cls):
        # Setting RecordHeader class variables --------------------------------
        # Top types in order of the main ESM
        header_type = brec.RecordHeader
        header_type.top_grup_sigs = []
        header_type.valid_header_sigs = set(
            header_type.top_grup_sigs + [b'GRUP', b'TES4'])
        # Record Types
        brec.MreRecord.type_class = {x.rec_sig: x for x in ()}
        # Simple records
        brec.MreRecord.simpleTypes = (
                set(brec.MreRecord.type_class) - {b'TES4'})
        cls._validate_records()

    @classmethod
    def _dynamic_import_modules(cls, package_name):
        """Dynamically import package modules to avoid importing them for every
        game. We need to pass the package name in for importlib to work.
        Currently populates the GameInfo namespace with the members defined in
        the relevant constants.py and imports default_tweaks.py and
        vanilla_files.py."""
        tweaks_module = importlib.import_module(u'.default_tweaks',
            package=package_name)
        cls.default_tweaks = tweaks_module.default_tweaks
        vf_module = importlib.import_module(u'.vanilla_files',
            package=package_name)
        cls.vanilla_files = vf_module.vanilla_files

    @staticmethod
    def _validate_records():
        """Performs validation on the record syntax for all decoded records."""
        sr_to_r = brec.MreRecord.subrec_sig_to_record_sig
        for rec_class in brec.MreRecord.type_class.values():
            if issubclass(rec_class, brec.MelRecord):
                rec_class.validate_record_syntax()
                for sr_sig in rec_class.melSet.loaders:
                    sr_to_r[sr_sig].add(rec_class.rec_sig)

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

WS_COMMON = [u'appxmanifest.xml']

GAME_TYPE = None
