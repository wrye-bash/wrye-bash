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
"""GameInfo class encapsulating static info for active game. Avoid adding
state and methods. game.GameInfo#init classmethod is used to import rest of
active game package as needed (currently the record and constants modules)
and to set some brec.RecordHeader/MreRecord class variables."""
import importlib
from enum import Enum
from itertools import chain
from os.path import join as _j

from .. import bolt
from ..bolt import FNDict, fast_cached_property

# Constants and Helpers -------------------------------------------------------
# Files shared by versions of games that are published on the Windows Store
WS_COMMON_FILES = {'appxmanifest.xml'}

class ObjectIndexRange(Enum):
    """Valid values for object_index_range."""
    # FormIDs with object indices in the range 0x000-0x7FF are always
    # reserved for the engine
    RESERVED = 0
    # Plugins with a header version >= 1.0 and at least one master can
    # use the range 0x000-0x7FF for their own purposes
    EXPANDED_CONDITIONAL = 1
    # Plugins with at least one master can use the range 0x001-0x7FF
    # for their own purposes
    EXPANDED_ALWAYS = 2

# Abstract class - to be overriden --------------------------------------------
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
    # Registry keys to read to find the install location. This is a list of
    # tuples of two strings, where each tuple defines the subkey and entry to
    # try. Multiple tuples in the list will be tried in order, with the first
    # one that works being used.
    # These are relative to:
    #  HKLM\Software
    #  HKLM\Software\Wow6432Node
    #  HKCU\Software
    #  HKCU\Software\Wow6432Node
    # Example: [(r'Bethesda Softworks\Oblivion', 'Installed Path')]
    registry_keys = []
    # URL to the Nexus site for this game
    nexusUrl = u''   # URL
    nexusName = u''  # Long Name
    nexusKey = u''   # Key for the "always ask this question" setting in
                     # settings.dat

    # Additional game info - override as needed -------------------------------
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
    # game. Some examples are sound\voice\PLUGIN_NAME.esp, or the facegendata
    # ones. An empty list means that the game does not have any such
    # directories.
    plugin_name_specific_dirs = [_j('sound', 'voice')]
    # Whether or not to check for 'Bash' and 'Installers' folders inside the
    # game folder and use those instead of the default paths when present
    check_legacy_paths = False

    def __init__(self, gamePath):
        self.gamePath = gamePath # absolute bolt Path to the game directory
        self.has_esl = u'.esl' in self.espm_extensions

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
        se_args = None
        # Image name template for the status bar, relative to images/tools
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
        master_limit = 255 # 256 - 1 for the plugin itself
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
    # DefaultIniFile.__init__ for how the tweaks are parsed.
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
        if self.displayName != 'Oblivion': # hack to avoid a bunch of overrides
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
        version_strs, current_esm = set(), None
        for modding_esm, esm_size in self.modding_esm_size.items():
            if (info := mod_infos.get(modding_esm)) and info.fsize == esm_size:
                version_strs.add(self.size_esm_version[esm_size])
        if _master_esm := mod_infos.get(self.master_file):
            current_esm = self.size_esm_version.get(_master_esm.fsize, None)
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
