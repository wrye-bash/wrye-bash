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
"""GameInfo class encapsulating static info for active game. Avoid adding
state and methods. game.GameInfo#init classmethod is used to import rest of
active game package as needed (currently the record and constants modules)
and to set some brec.RecordHeader/MreRecord class variables."""
import importlib

from .. import brec

class GameInfo(object):
    # Main game info - should be overridden -----------------------------------
    # Name of the game to use in UI.
    displayName = u'' ## Example: u'Skyrim'
    # Name of the game's filesystem folder.
    fsName = u'' ## Example: u'Skyrim'
    # Alternate display name of Wrye Bash when managing this game
    altName = u'' ## Example: u'Wrye Smash'
    # Name of game's default ini file.
    defaultIniFile = u''
    # True if the game uses the 'My Documents' folder, False to just use the
    # game path
    uses_personal_folders = True
    # The exe to use when launching the game (without xSE present)
    launch_exe = u'' ## Example: u'TESV.exe'
    # Path to a file to look for to see if this is the right game. Given as a
    # list of strings that will be joined with the -o parameter. Must be unique
    # among all games. As a rule of thumb, use the file you specified in
    # launch_exe, unless that file is shared by multiple games, in which case
    # you MUST find unique files - see Skyrim and Enderal, which share TESV.exe
    game_detect_file = []
    # Path to a file to pass to env.get_file_version to determine the game's
    # version. Usually the same as launch_exe, but some games need different
    # ones here (e.g. Enderal, which has Skyrim's version in the launch_exe,
    # and therefore needs a different file here).
    version_detect_file = []
    # The main plugin Wrye Bash should look for
    masterFiles = []
    # The directory in which mods and other data files reside. This is relative
    # to the game directory.
    mods_dir = u'Data'
    # INI files that should show up in the INI Edits tab
    #  Example: [u'Oblivion.ini']
    iniFiles = []
    # The pickle file for this game.  Holds encoded GMST IDs from the big list
    # below
    pklfile = u'bash\\db\\*GAMENAME*_ids.pkl'
    # The directory containing the masterlist for this game, relative to
    # 'Mopy/Bash Patches'
    masterlist_dir = u''
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
    # Extensions for external script files. Empty if this game doesn't have any
    script_extensions = {}
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
    # ones. All paths are given as lists for future cross-platform support. An
    # empty list means that the game does not have any such directories.
    plugin_name_specific_dirs = [[u'sound', u'voice']]

    def __init__(self, gamePath):
        self.gamePath = gamePath # absolute bolt Path to the game directory
        self.has_esl = u'.esl' in self.espm_extensions

    class Ck(object):
        """Information about the official plugin editor (generally called some
        variation of 'Creation Kit') for this game."""
        ck_abbrev = u''   # Abbreviated name
        long_name = u''   # Full name
        exe = u'*DNE*'    # Executable to run
        se_args = u''     # Argument to pass to the SE to load the CK
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
        # INI setting used to setup Save Profiles
        #  (section,key)
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
        # The extension used for BSA files
        bsa_extension = u'.bsa'
        # Whether or not the Archive.exe tool for this game creates BSL files
        has_bsl = False
        # All BSA versions accepted by this game. If empty, indicates that this
        # game does not use BSA versions and so BSA version checks will be
        # skipped entirely.
        valid_versions = set()
        # Maps vanilla plugin names to the BSA that contain their localization
        # strings
        vanilla_string_bsas = {}

    class Xe(object):
        """Information about xEdit for this game."""
        # The name that xEdit has for this game, e.g. 'TES5Edit' for Skyrim
        full_name = u'xEdit'
        # A settings key used to store whether or not 'expert' mode for xEdit
        # has been activated (the -IKnowWhatImDoing CLI switch)
        expert_key = ''

    # BAIN:
    #  These are the allowed default data directories that BAIN can install to
    dataDirs = {
        u'ini',
        u'meshes',
        u'music',
        u'sound',
        u'textures',
        u'video'
    }
    # Files BAIN shouldn't skip
    dontSkip = ()
    # Directories where specific file extensions should not be skipped by BAIN
    dontSkipDirs = {}
    # Folders BAIN should never CRC check in the Data directory
    SkipBAINRefresh = set((
        # Use lowercase names
    ))
    # Files to exclude from clean data
    wryeBashDataFiles = {u'Docs\\Bash Readme Template.html',
                         u'Docs\\wtxt_sand_small.css', u'Docs\\wtxt_teal.css',
                         u'Docs\\Bash Readme Template.txt'}
    wryeBashDataDirs = {u'Bash Patches', u'BashTags', u'INI Tweaks'}
    ignoreDataFiles = set()
    ignoreDataFilePrefixes = set()
    ignoreDataDirs = set()

    # Plugin format stuff
    class Esp(object):
        # Wrye Bash capabilities
        canBash = False         # Can create Bashed Patches
        canCBash = False        # CBash can handle this game's records
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

    # Bash Tags supported by this game
    allTags = set()

    # Patcher available when building a Bashed Patch (referenced by class name)
    # PatchMerger must come first if enabled, see
    # patcher.base.APatchMerger.__init__
    patchers = ()

    # CBash patchers available when building a Bashed Patch
    CBash_patchers = () # CBash_PatchMerger must come first if enabled!

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
    condition_function_data = {}

    # Known record types - maps integers from the save format to human-readable
    # names for the record types. Used in save editing code.
    save_rec_types = {}

    #--List of GMST's in the main plugin (Oblivion.esm) that have 0x00000000
    #  as the form id.  Any GMST as such needs it Editor Id listed here.
    gmstEids = []

    """
    GLOB record tweaks used by patcher.patchers.multitweak_settings.GmstTweaker

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
    'defaultEnabled ':True}. See the UOP Vampire face fix for an example of
    this (in the GMST Tweaks)
    """
    GlobalsTweaks = []

    """
    GMST record tweaks used by patcher.patchers.multitweak_settings.GmstTweaker

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
    'defaultEnabled ':True}. See the UOP Vampire facefix for an example of
    this (in the GMST Tweaks)
    """
    GmstTweaks = []

    #--------------------------------------------------------------------------
    # ListsMerger patcher (leveled list patcher)
    #--------------------------------------------------------------------------
    listTypes = ()

    #--------------------------------------------------------------------------
    # NamesPatcher
    #--------------------------------------------------------------------------
    namesTypes = set()  # initialize with literal

    #--------------------------------------------------------------------------
    # ItemPrices Patcher
    #--------------------------------------------------------------------------
    pricesTypes = {}

    #--------------------------------------------------------------------------
    # StatsImporter
    #--------------------------------------------------------------------------
    statsTypes = {}
    statsHeaders = ()

    #--------------------------------------------------------------------------
    # SoundPatcher
    #--------------------------------------------------------------------------
    # Needs longs in SoundPatcher
    soundsLongsTypes = set()  # initialize with literal
    soundsTypes = {}

    #--------------------------------------------------------------------------
    # CellImporter
    #--------------------------------------------------------------------------
    cellAutoKeys = set()  # use a set literal
    cellRecAttrs = {}
    cellRecFlags = {}

    #--------------------------------------------------------------------------
    # GraphicsPatcher
    #--------------------------------------------------------------------------
    graphicsLongsTypes = set()  # initialize with literal
    graphicsTypes = {}
    graphicsFidTypes = {}
    graphicsModelAttrs = ()

    #--------------------------------------------------------------------------
    # Inventory Patcher
    #--------------------------------------------------------------------------
    inventoryTypes = ()

    #--------------------------------------------------------------------------
    # Race Patcher
    #--------------------------------------------------------------------------
    default_eyes = {}

    #--------------------------------------------------------------------------
    # Keywords Patcher
    #--------------------------------------------------------------------------
    keywords_types = ()

    #--------------------------------------------------------------------------
    # Text Patcher
    #--------------------------------------------------------------------------
    text_long_types = set()
    text_types = {}

    #--------------------------------------------------------------------------
    # Object Bounds Patcher
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
    # Scripts Patcher
    #--------------------------------------------------------------------------
    scripts_types = set()

    #--------------------------------------------------------------------------
    # Destructible Patcher
    #--------------------------------------------------------------------------
    destructible_types = set()

    #--------------------------------------------------------------------------
    # Actor Patchers
    #--------------------------------------------------------------------------
    actor_importer_attrs = {}
    actor_importer_auto_key = set()
    actor_types = ()

    #--------------------------------------------------------------------------
    # Spell Stats Patcher
    #--------------------------------------------------------------------------
    spell_stats_attrs = ()

    #--------------------------------------------------------------------------
    # Actor Tweaker
    #--------------------------------------------------------------------------
    actor_tweaks = set()

    #--------------------------------------------------------------------------
    # Names Tweaker
    #--------------------------------------------------------------------------
    body_tags = u''

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
        'GlobalsTweaks', 'GmstTweaks', 'actor_importer_attrs',
        'actor_importer_auto_key', 'actor_tweaks', 'actor_types',
        'actor_values', 'bethDataFiles', 'body_tags', 'cc_valid_types',
        'cc_passes', 'cellAutoKeys', 'cellRecAttrs', 'cellRecFlags',
        'condition_function_data', 'default_eyes', 'destructible_types',
        'generic_av_effects', 'gmstEids', 'graphicsFidTypes',
        'graphicsLongsTypes', 'graphicsModelAttrs', 'graphicsTypes',
        'hostile_effects', 'inventoryTypes', 'keywords_types', 'listTypes',
        'mgef_basevalue', 'mgef_name', 'mgef_school', 'namesTypes',
        'object_bounds_types', 'pricesTypes', 'record_type_name',
        'save_rec_types', 'scripts_types', 'soundsLongsTypes', 'soundsTypes',
        'spell_stats_attrs', 'statsHeaders', 'statsTypes', 'text_long_types',
        'text_types',
    }

    @classmethod
    def init(cls):
        # Setting RecordHeader class variables --------------------------------
        # Top types in order of the main ESM
        brec.RecordHeader.topTypes = []
        brec.RecordHeader.recordTypes = set(
            brec.RecordHeader.topTypes + ['GRUP', 'TES4'])
        # Record Types
        brec.MreRecord.type_class = dict((x.classType,x) for x in  (
                ))
        # Simple records
        brec.MreRecord.simpleTypes = (
                set(brec.MreRecord.type_class) - {'TES4'})

    @classmethod
    def _dynamic_import_modules(cls, package_name):
        """Dynamically import package modules to avoid importing them for every
        game. We need to pass the package name in for importlib to work.
        Currently populates the GameInfo namespace with the members defined in
        the relevant constants.py and imports default_tweaks.py and
        vanilla_files.py."""
        constants = importlib.import_module('.constants', package=package_name)
        for k in dir(constants):
            if k.startswith('_'): continue
            if k not in cls._constants_members:
                raise RuntimeError(u'Unexpected game constant %s' % k)
            setattr(cls, k, getattr(constants, k))
        tweaks_module = importlib.import_module('.default_tweaks',
                                                package=package_name)
        cls.default_tweaks = tweaks_module.default_tweaks
        vf_module = importlib.import_module('.vanilla_files',
                                            package=package_name)
        cls.vanilla_files = vf_module.vanilla_files
        patchers_module = importlib.import_module('.patcher',
                                                  package=package_name)
        cls.gameSpecificPatchers = patchers_module.gameSpecificPatchers
        cls.gameSpecificListPatchers = patchers_module.gameSpecificListPatchers
        cls.game_specific_import_patchers = \
            patchers_module.game_specific_import_patchers

GAME_TYPE = None
