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
#  Wrye Bash copyright (C) 2005-2009 Wrye, 2010-2022 Wrye Bash Team
#  https://github.com/wrye-bash
#
# =============================================================================
"""Module housing a GameInfo subtype allowing to build a Bashed patch."""
import importlib

from . import GameInfo

class PatchGame(GameInfo):
    """Game that supports a Bashed patch. Provides record related values used
    by the patcher/parsers/saves code. Those are read in dynamically from this
    or a parent's game 'patcher' package, apart from a few that are overridden
    in the class body. This is done for decluttering the game overrides from
    too specific (and often big) data structures - however the exact constants
    included here is still WIP."""

    # Bash Tags supported by this game. List only tags that aren't used by
    # patchers here (e.g. Deactivate, Filter, etc.), patcher-based tags get
    # dynamically added in gui_patchers.
    allTags = {u'Deactivate', u'Filter', u'MustBeActiveIfImported'}

    # Patchers available when building a Bashed Patch (referenced by GUI class
    # name, see gui_patchers.py for their definitions).
    patchers = set()

    # Set in _dynamic_import_modules used in Mopy/bash/basher/gui_patchers.py
    gameSpecificPatchers = {}
    gameSpecificListPatchers = {}
    game_specific_import_patchers = {}

    # Record information - set in cls.init ------------------------------------
    # Mergeable record types
    mergeable_sigs = {}
    # Extra read classes: these record types will always be loaded, even if
    # patchers don't need them directly (for example, for MGEF info)
    readClasses = ()
    writeClasses = ()

    # Magic Info
    weaponTypes = ()

    # Race Info, used in faces.py
    raceNames = {}
    raceShortNames = {}
    raceHairMale = {}
    raceHairFemale = {}

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

    # Dynamic importer --------------------------------------------------------
    _constants_members = {
        # patcher and tweaks constants
        u'actor_importer_attrs', u'actor_tweaks', u'actor_types',
        u'actor_values', u'assorted_tweaks', u'names_tweaks', u'cc_passes',
        'cc_valid_types', 'cellRecAttrs', 'spell_types',
        u'cell_skip_interior_attrs', u'condition_function_data',
        u'default_eyes', u'destructible_types', u'ench_stats_attrs',
        u'generic_av_effects', u'getvatsvalue_index', u'graphicsFidTypes',
        u'graphicsModelAttrs', u'graphicsTypes', u'hostile_effects',
        u'import_races_attrs', u'inventoryTypes', u'default_wp_timescale',
        u'keywords_types', u'listTypes', u'mgef_basevalue', u'mgef_name',
        u'mgef_school', u'mgef_stats_attrs', u'namesTypes',
        u'nonplayable_biped_flags', u'not_playable_flag', u'body_part_codes',
        u'object_bounds_types', u'pricesTypes', u'race_tweaks',
        'race_tweaks_need_collection', 'relations_attrs', 'gold_attrs',
        u'relations_csv_header', u'relations_csv_row_format',
        u'save_rec_types', u'scripts_types', u'settings_tweaks',
        u'soundsLongsTypes', u'soundsTypes', u'spell_stats_attrs',
        u'spell_stats_types', u'staff_condition', 'enchantment_types',
        u'static_attenuation_rec_type', u'statsTypes', 'text_replacer_rpaths',
        u'text_types',
    }

    _patcher_package = u'' # read the patcher of another (parent) game
    @classmethod
    def _dynamic_import_modules(cls, package_name):
        """Dynamically import the patcher module."""
        super(PatchGame, cls)._dynamic_import_modules(package_name)
        package_name = cls._patcher_package or package_name
        patchers_module = importlib.import_module(u'.patcher',
            package=package_name)
        for k in dir(patchers_module):
            if k.startswith(u'_'): continue
            if k not in cls._constants_members:
                raise SyntaxError(u"Unexpected game constant '%s', check for "
                                  u'typos or update _constants_members' % k)
            setattr(cls, k, getattr(patchers_module, k))

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
    pricesTypes = set()

    #--------------------------------------------------------------------------
    # Import Stats
    #--------------------------------------------------------------------------
    statsTypes = {}

    #--------------------------------------------------------------------------
    # Import Sounds
    #--------------------------------------------------------------------------
    soundsTypes = {}

    #--------------------------------------------------------------------------
    # Import Cells
    #--------------------------------------------------------------------------
    cellRecAttrs = {}
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
    # NPC Checker
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
    actor_types = (b'NPC_',)
    spell_types = (b'SPEL',)

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
    # Tweak Names
    #--------------------------------------------------------------------------
    names_tweaks = set()
    body_part_codes = ()
    text_replacer_rpaths = {}
    ##: This is a pretty ugly hack. We need to be able to create FormIDs in
    # these for newer games than Oblivion, but master_file is only defined in
    # here and importing it in the patcher files is probably a huge headache.
    # The first parameter is required since Python automatically passes it when
    # called: bush.game.gold_attrs(x) -> _gm_master == x
    gold_attrs = lambda _self_ignore, _gm_master: {}

    #--------------------------------------------------------------------------
    # Tweak Settings
    #--------------------------------------------------------------------------
    settings_tweaks = set()

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
    # Import Enchantments
    #--------------------------------------------------------------------------
    enchantment_types = set()

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
    # Localized version of 'Nirnroots' in Tamriel, 'Vynroots' in Vyn
    nirnroots = _(u'Nirnroots')

    #--------------------------------------------------------------------------
    # Import Races
    #--------------------------------------------------------------------------
    import_races_attrs = {}

    #--------------------------------------------------------------------------
    # Tweak Races
    #--------------------------------------------------------------------------
    race_tweaks = set()
    # Whether or not Tweak Races should collect extra data from EYES, HAIR and
    # RACE records and make it available to the tweaks
    race_tweaks_need_collection = False

    #--------------------------------------------------------------------------
    # Timescale Checker
    #--------------------------------------------------------------------------
    # The effective timescale to which the wave periods of this game's grass
    # are specified
    default_wp_timescale = 10

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
    mgef_basevalue = {}
    mgef_name = {}
    mgef_school = {}

    # Human-readable names for each actor value
    actor_values = []
