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
#  Wrye Bash copyright (C) 2005-2009 Wrye, 2010-2020 Wrye Bash Team
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
    # Name of the game's filesystem folder.
    fsName = u'' ## Example: u'Skyrim'
    # Alternate display name of Wrye Bash when managing this game
    altName = u'' ## Example: u'Wrye Smash'
    # Name of the prefix of the '<X> Mods' folder, i.e. <X> is this string.
    # Preferably pick a single word here, equal to fsName if possible.
    bash_root_prefix = u'' ## Example: u'Skyrim'
    # True if the game uses the 'My Documents' folder, False to just use the
    # game path
    uses_personal_folders = True
    # The exe to use when launching the game (without xSE present)
    launch_exe = u'' ## Example: u'TESV.exe'
    # Path to a file to look for to see if this is the right game when joined
    # with the -o parameter. Must be unique among all games. As a rule of
    # thumb, use the file you specified in launch_exe, unless that file is
    # shared by multiple games, in which case you MUST find unique files - see
    # Skyrim and Enderal, which share TESV.exe.
    game_detect_file = u''
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
    # The directory containing the taglist for this game, relative to
    # 'Mopy/taglists'
    taglist_dir = u''
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

    class Ck(object):
        """Information about the official plugin editor (generally called some
        variation of 'Creation Kit') for this game."""
        ck_abbrev = u''   # Abbreviated name
        long_name = u''   # Full name
        exe = u'*DNE*'    # Executable to run
        # Argument to pass to the script extender to load the CK. If None,
        # indicates that this game's script extender does not have this feature
        se_args = None
        image_name = u''  # Image name template for the status bar

    class Se(object):
        """Information about the Script Extender for this game."""
        se_abbrev = u''   # Abbreviated name. If this is empty, it signals that
                          # no xSE is available for this game. Note that this
                          # should NEVER be used to program other xSE
                          # behavior - create new variables like plugin_dir and
                          # cosave_ext instead.
        long_name = u''   # Full name
        exe = u''         # Exe to run
        ver_files = []    # List of file names to use for version detection.
                          # Tried in order until one exists. Needed because
                          # it's technically not required to install the EXE.
        plugin_dir = u''  # One level above the directory in which xSE plugins
                          # should be placed (e.g. when plugins should be in
                          # Data\OBSE\Plugins, this should be u'OBSE')
        cosave_tag = u''  # The magic tag that the cosaves use (e.g. u'SKSE').
                          # If this is empty, it signals that this script
                          # extender has no cosaves.
        cosave_ext = u''  # The extension that the cosaves use (e.g. u'.skse')
        url = u''         # URL to download from
        url_tip = u''     # Tooltip for mouse over the URL

    class Sd(object):
        """Information about Script Dragon for this game."""
        sd_abbrev = u''   # Abbreviated name. If this is empty, it signals that
                          # no Script Dragon is available for this game.
        long_name = u''   # Full name
        install_dir = u'' # The directory, relative to the Data folder, into
                          # which Script Dragon plugins will be installed.

    class Sp(object):
        """Information about SkyProc patchers for this game."""
        sp_abbrev = u''   # Abbreviated name. If this is empty, it signals that
                          # this game does not support SkyProc patchers.
        long_name = u''   # Full name
        install_dir = u'' # The directory, relative to the Data folder, into
                          # which SkyProc patchers will be installed.

    class Ge(object):
        """Information about the Graphics Extender for this game."""
        ge_abbrev = u'' # Abbreviated name. If this is empty, it signals
                        # that no graphics extender is available for this game.
        long_name = u'' # Full name
        # exe is treated specially here.  If it is a string, then it should
        # be the path relative to the root directory of the game, if it is
        # a list, each list element should be an iterable to pass to Path.join
        # relative to the root directory of the game.  In this case,
        # each filename will be tested in reverse order.  This was required
        # for Oblivion, as the newer OBGE has a different filename than the
        # older OBGE
        exe = u''
        url = u''       # URL to download from
        url_tip = u''   # Tooltip for mouse over the URL

    class Laa(object):
        """Information about the LAA (Large Address Aware) launcher for this
        game."""
        laa_name = u''      # Display name of the launcher
        exe = u'*DNE*'      # Executable to run
        launchesSE = False  # Whether the launcher will automatically launch
                            # the SE

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
        # Whether this game supports mod ini files aka ini fragments
        supports_mod_inis = True

    class Ess(object):
        """Information about WB's capabilities with regards to save file
        viewing and editing for this game."""
        canReadBasic = True # Can read the info needed for the Save Tab display
        canEditMore = False # Advanced editing
        ext = u'.ess'       # Save file extension

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
        # The default value for Ini.resource_override_key if it's missing from
        # the game INI
        resource_override_defaults = []
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
        no_skip_dirs = {}
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
        canBash = False         # Can create Bashed Patches
        canEditHeader = False   # Can edit basic info in the main header
                                # record - generally has signature 'TES4'
        # Valid ESM/ESP header versions
        #  These are the valid 'version' numbers for the game file headers
        validHeaderVersions = tuple()
        # used to locate string translation files
        stringsFiles = [
            ((u'Strings',), u'%(body)s_%(language)s.STRINGS'),
            ((u'Strings',), u'%(body)s_%(language)s.DLSTRINGS'),
            ((u'Strings',), u'%(body)s_%(language)s.ILSTRINGS'),
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

    # Bash Tags supported by this game
    allTags = set()

    # Patchers available when building a Bashed Patch (referenced by GUI class
    # name, see gui_patchers.py for their definitions).
    patchers = set()

    # Magic Info
    weaponTypes = ()

    # Race Info, used in faces.py
    raceNames = {}
    raceShortNames = {}
    raceHairMale = {}
    raceHairFemale = {}

    # Record information - set in cls.init ------------------------------------
    # Mergeable record types
    mergeClasses = ()
    # Extra read classes: these record types will always be loaded, even if
    # patchers don't need them directly (for example, for MGEF info)
    readClasses = ()
    writeClasses = ()

    # Class attributes moved to constants module, set dynamically at init
    #--Game ESM/ESP/BSA files
    ## These are all of the ESM,ESP,and BSA data files that belong to the game
    ## These filenames need to be in lowercase,
    bethDataFiles = set()  # initialize with literal

    # Function Info -----------------------------------------------------------
    # CTDA Data for the game. Maps function ID to tuple with name of function
    # and the parameter types of the function.
    # 0: no param; 1: int param; 2: formid param; 3: float param
    # Note that each line must have the same number of parameters after the
    # function name - so pad out functions with fewer parameters with zeroes
    condition_function_data = {}
    # The function index for the GetVATSValue function. This function is
    # special, because the type of its second parameter depends on the value of
    # the first parameter.
    getvatsvalue_index = 0

    # Known record types - maps integers from the save format to human-readable
    # names for the record types. Used in save editing code.
    save_rec_types = {}

    """
    GLOB record tweaks used by
    patcher.patchers.multitweak_settings.TweakSettingsPatcher

    Each entry is a tuple in the following format:
      (DisplayText, MouseoverText, GLOB EditorID, Option1, Option2, ...,
      OptionN)
      -EditorID can be a plain string, or a tuple of multiple Editor IDs.
      If it's a tuple, then Value (below) must be a tuple of equal length,
      providing values for each GLOB
    Each Option is a tuple:
      (DisplayText, Value)
      - If you enclose DisplayText in brackets like this: _(u'[Default]'),
      then the patcher will treat this option as the default value.
      - If you use _(u'Custom') as the entry, the patcher will bring up a
      number input dialog

    To make a tweak Enabled by Default, enclose the tuple entry for the
    tweak in a list, and make a dictionary as the second list item with {
    u'default_enabled': True}. See the UOP Vampire face fix for an example of
    this (in the GMST Tweaks)
    """
    GlobalsTweaks = []

    """
    GMST record tweaks used by
    patcher.patchers.multitweak_settings.TweakSettingsPatcher

    Each entry is a tuple in the following format:
      (DisplayText, MouseoverText, GMST EditorID, Option1, Option2, ...,
      OptionN)
      - EditorID can be a plain string, or a tuple of multiple Editor IDs.
      If it's a tuple, then Value (below) must be a tuple of equal length,
      providing values for each GMST
    Each Option is a tuple:
      (DisplayText, Value)
      - If you enclose DisplayText in brackets like this: _(u'[Default]'),
      then the patcher will treat this option as the default value.
      - If you use _(u'Custom') as the entry, the patcher will bring up a
      number input dialog

    To make a tweak Enabled by Default, enclose the tuple entry for the
    tweak in a list, and make a dictionary as the second list item with {
    u'default_enabled': True}. See the UOP Vampire facefix for an example of
    this (in the GMST Tweaks)
    """
    GmstTweaks = []

    #--------------------------------------------------------------------------
    # Leveled Lists
    #--------------------------------------------------------------------------
    listTypes = ()

    #--------------------------------------------------------------------------
    # Import Names
    #--------------------------------------------------------------------------
    namesTypes = set()  # initialize with literal

    #--------------------------------------------------------------------------
    # Import Prices
    #--------------------------------------------------------------------------
    pricesTypes = {}

    #--------------------------------------------------------------------------
    # Import Stats
    #--------------------------------------------------------------------------
    statsTypes = {}
    statsHeaders = ()

    #--------------------------------------------------------------------------
    # Import Sounds
    #--------------------------------------------------------------------------
    soundsTypes = {}

    #--------------------------------------------------------------------------
    # Import Cells
    #--------------------------------------------------------------------------
    cellRecAttrs = {}
    cell_float_attrs = set()
    cell_skip_interior_attrs = set()

    #--------------------------------------------------------------------------
    # Import Graphics
    #--------------------------------------------------------------------------
    graphicsTypes = {}
    graphicsFidTypes = {}
    graphicsModelAttrs = ()

    #--------------------------------------------------------------------------
    # Import Inventory
    #--------------------------------------------------------------------------
    inventoryTypes = ()

    #--------------------------------------------------------------------------
    # Race Records
    #--------------------------------------------------------------------------
    default_eyes = {}

    #--------------------------------------------------------------------------
    # Import Keywords
    #--------------------------------------------------------------------------
    keywords_types = ()

    #--------------------------------------------------------------------------
    # Import Text
    #--------------------------------------------------------------------------
    text_types = {}

    #--------------------------------------------------------------------------
    # Import Object Bounds
    #--------------------------------------------------------------------------
    object_bounds_types = set()

    #--------------------------------------------------------------------------
    # Contents Checker
    #--------------------------------------------------------------------------
    cc_valid_types = {}
    # (targeted types, structs/groups name, entry/item name)
    # OR (targeted types, fid list name)
    cc_passes = ()

    #--------------------------------------------------------------------------
    # Import Scripts
    #--------------------------------------------------------------------------
    scripts_types = set()

    #--------------------------------------------------------------------------
    # Import Destructible
    #--------------------------------------------------------------------------
    destructible_types = set()

    #--------------------------------------------------------------------------
    # Import Actors
    #--------------------------------------------------------------------------
    actor_importer_attrs = {}
    actor_types = ()

    #--------------------------------------------------------------------------
    # Import Spell Stats
    #--------------------------------------------------------------------------
    spell_stats_attrs = ()
    spell_stats_types = {b'SPEL'}

    #--------------------------------------------------------------------------
    # Tweak Actors
    #--------------------------------------------------------------------------
    actor_tweaks = set()

    #--------------------------------------------------------------------------
    # Tweak Assorted
    #--------------------------------------------------------------------------
    nirnroots = _(u'Nirnroots')

    #--------------------------------------------------------------------------
    # Tweak Names
    #--------------------------------------------------------------------------
    body_tags = u''

    #--------------------------------------------------------------------------
    # Import Relations
    #--------------------------------------------------------------------------
    relations_attrs = ()
    relations_csv_header = u''
    relations_csv_row_format = u''

    #--------------------------------------------------------------------------
    # Import Enchantment Stats
    #--------------------------------------------------------------------------
    ench_stats_attrs = ()

    #--------------------------------------------------------------------------
    # Import Effect Stats
    #--------------------------------------------------------------------------
    mgef_stats_attrs = ()

    #--------------------------------------------------------------------------
    # Tweak Assorted
    #--------------------------------------------------------------------------
    assorted_tweaks = set()
    # Only allow the 'mark playable' tweaks to mark a piece of armor/clothing
    # as playable if it has at least one biped flag that is not in this set.
    nonplayable_biped_flags = set()
    # The record attribute and flag name needed to find out if a piece of armor
    # is non-playable. Locations differ in TES4, FO3/FNV and TES5.
    not_playable_flag = (u'flags1', u'isNotPlayable')
    # Tuple containing the name of the attribute and the value it has to be set
    # to in order for a weapon to count as a staff for reweighing purposes
    staff_condition = ()
    # The record type that contains the static attenuation field tweaked by the
    # static attenuation tweaks. SNDR on newer games, SOUN on older games.
    static_attenuation_rec_type = b'SNDR'

    #--------------------------------------------------------------------------
    # Magic Effects - Oblivion-specific
    #--------------------------------------------------------------------------
    # Doesn't list MGEFs that use actor values, but rather MGEFs that have a
    # generic name.
    # Ex: Absorb Attribute becomes Absorb Magicka if the effect's actorValue
    #     field contains 9, but it is actually using an attribute rather than
    #     an actor value
    # Ex: Burden uses an actual actor value (encumbrance) but it isn't listed
    #     since its name doesn't change
    generic_av_effects = set()
    # MGEFs that are considered hostile
    hostile_effects = set()
    # Maps MGEF signatures to certain MGEF properties
    mgef_basevalue = dict()
    mgef_name = dict()
    mgef_school = dict()

    # Human-readable names for each actor value
    actor_values = []

    # Record type to name dictionary
    record_type_name = {}

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

    # Set in game/*/patcher.py used in Mopy/bash/basher/gui_patchers.py
    gameSpecificPatchers = {}
    gameSpecificListPatchers = {}
    game_specific_import_patchers = {}

    # Import from the constants module ----------------------------------------
    # Class attributes moved to constants module, set dynamically at init
    _constants_members = {
        u'GlobalsTweaks', u'GmstTweaks', u'actor_importer_attrs',
        u'actor_tweaks', u'actor_types', u'actor_values', u'bethDataFiles',
        u'body_tags', u'cc_valid_types', u'cc_passes',
        u'cell_float_attrs', u'cellRecAttrs',
        u'cell_skip_interior_attrs', u'condition_function_data',
        u'default_eyes', u'destructible_types', u'ench_stats_attrs',
        u'generic_av_effects', u'getvatsvalue_index',
        u'graphicsFidTypes', u'graphicsModelAttrs', u'graphicsTypes',
        u'hostile_effects', u'inventoryTypes', u'keywords_types', u'listTypes',
        u'mgef_basevalue', u'mgef_name', u'mgef_school', u'mgef_stats_attrs',
        u'namesTypes', u'nirnroots', u'object_bounds_types', u'pricesTypes',
        u'record_type_name', u'relations_attrs', u'relations_csv_header',
        u'relations_csv_row_format', u'save_rec_types', u'scripts_types',
        u'soundsLongsTypes', u'soundsTypes', u'spell_stats_attrs',
        u'spell_stats_types', u'statsHeaders', u'statsTypes', u'text_types',
        u'assorted_tweaks', u'staff_condition', u'static_attenuation_rec_type',
        u'nonplayable_biped_flags', u'not_playable_flag'
    }

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
        constants = importlib.import_module(u'.constants',
            package=package_name)
        for k in dir(constants):
            if k.startswith(u'_'): continue
            if k not in cls._constants_members:
                raise SyntaxError(u"Unexpected game constant '%s', check for "
                                  u'typos or update _constants_members' % k)
            setattr(cls, k, getattr(constants, k))
        tweaks_module = importlib.import_module(u'.default_tweaks',
            package=package_name)
        cls.default_tweaks = tweaks_module.default_tweaks
        vf_module = importlib.import_module(u'.vanilla_files',
            package=package_name)
        cls.vanilla_files = vf_module.vanilla_files
        patchers_module = importlib.import_module(u'.patcher',
            package=package_name)
        cls.gameSpecificPatchers = patchers_module.gameSpecificPatchers
        cls.gameSpecificListPatchers = patchers_module.gameSpecificListPatchers
        cls.game_specific_import_patchers = \
            patchers_module.game_specific_import_patchers

    @staticmethod
    def _validate_records():
        """Performs validation on the record syntax for all decoded records."""
        for rec_class in brec.MreRecord.type_class.itervalues():
            if issubclass(rec_class, brec.MelRecord):
                rec_class.validate_record_syntax()

    @classmethod
    def supported_games(cls):
        game_types = set(cls.__subclasses__())
        game_types.update(
            chain.from_iterable(c.__subclasses__() for c in list(game_types)))
        return game_types

GAME_TYPE = None
