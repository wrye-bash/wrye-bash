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
#  Wrye Bash copyright (C) 2005-2009 Wrye, 2010-2022 Wrye Bash Team
#  https://github.com/wrye-bash
#
# =============================================================================
"""Module housing a GameInfo subtype allowing to build a Bashed patch."""
import importlib

from . import GameInfo
from .. import bolt
from ..bolt import structs_cache

class PatchGame(GameInfo):
    """Game that supports a Bashed patch. Provides record related values used
    by the patcher/parsers/saves code. Those are read in dynamically from this
    or a parent's game 'patcher' package, apart from a few that are overridden
    in the class body. This is done for decluttering the game overrides from
    too specific (and often big) data structures - however the exact constants
    included here is still WIP."""

    @classmethod
    def check_loaded_mod(cls, patch_file, modFile):
        """Perform some game specific validation on a loaded modFile and update
        PatchFile instance variables."""
        if b'WRLD' in modFile.tops and modFile.tops[b'WRLD'].orphansSkipped:
            patch_file.worldOrphanMods.append(modFile.fileInfo.fn_key)

    # Bash Tags supported by this game. List only tags that aren't used by
    # patchers here (e.g. Deactivate, Filter, etc.), patcher-based tags get
    # dynamically added in gui_patchers.
    allTags = {'Deactivate', 'Filter', 'MustBeActiveIfImported'}

    # Patchers available when building a Bashed Patch (referenced by GUI class
    # name, see gui_patchers.py for their definitions).
    patchers = set()

    # Set in _dynamic_import_modules used in Mopy/bash/basher/gui_patchers.py
    gameSpecificPatchers = {}
    gameSpecificListPatchers = {}
    game_specific_import_patchers = {}

    # Record information - set in cls.init ------------------------------------
    top_groups = [] # list of the top groups ordered as in the main esm
    # those records have nested record groups
    complex_groups = {b'CELL', b'WRLD', b'DIAL'}
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
    # 0: no param; 1: int param; 2: FormID param; 3: float param
    # Note that each line must have the same number of parameters after the
    # function name - so pad out functions with fewer parameters with zeroes
    condition_function_data = {}
    # The function index for the GetVATSValue function. This function is
    # special, because the type of its second parameter depends on the value of
    # the first parameter.
    getvatsvalue_index = 0

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
    graphicsModelAttrs = set()

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
    # The first (self) parameter is automatically passed by Python when called
    gold_attrs = lambda _self: {}

    #--------------------------------------------------------------------------
    # Tweak Settings
    #--------------------------------------------------------------------------
    settings_tweaks = set()

    #--------------------------------------------------------------------------
    # Import Relations
    #--------------------------------------------------------------------------
    relations_attrs = ()

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
    # The record attribute and flag name needed to find out if a piece of armor
    # is non-playable. Locations differ in TES4, FO3/FNV and TES5.
    not_playable_flag = ('flags1', 'not_playable')
    # Tuple containing the name of the attribute and the value it has to be set
    # to in order for a weapon to count as a staff for reweighing purposes
    staff_condition = ()
    # The record type that contains the static attenuation field tweaked by the
    # static attenuation tweaks. SNDR on newer games, SOUN on older games.
    static_attenuation_rec_type = b'SNDR'
    # Localized version of 'Nirnroots' in Tamriel, 'Vynroots' in Vyn
    nirnroots = _('Nirnroots')

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

    @classmethod
    def _import_records(cls, package_name, plugin_form_vers=None, *,
                        __unp=structs_cache['I'].unpack):
        """Import the records, perform validation on the record syntax for
        all decoded records and have the RecordType class variables updated.
        :param plugin_form_vers: if not None set RecordHeader variable"""
        importlib.import_module('.records', package=package_name)
        from .. import brec
        rtype, rec_head = brec.RecordType, brec.RecordHeader
        if plugin_form_vers is not None:
            rec_head.plugin_form_version = plugin_form_vers
        rec_head.top_grup_sigs = {k: k for k in cls.top_groups}
        rec_head.top_grup_sigs.update((__unp(k)[0], k) for k in cls.top_groups)
        ##: complex_groups should not be needed but added due to fo4 DIAL (?)
        valid_header_sigs = {cls.Esp.plugin_header_sig, *cls.top_groups,
                             *rtype.nested_to_top, *cls.complex_groups}
        for rec_sig, rec_class in list(rtype.sig_to_class.items()):
            if issubclass(rec_class, brec.MelRecord):
                # when emulating startup in tests, an earlier loaded game may
                # override the rec_class in sig_to_class with a stub (for
                # instance <class 'bash.game.fallout4.records.MreCell'>)
                if rec_class.melSet is None:
                    bolt.deprint(f'{rec_class}: no melSet')
                    continue
                rec_class.validate_record_syntax()
        if miss := [s for s in valid_header_sigs if
                    s not in rtype.sig_to_class]:
            bolt.deprint(f'Signatures {miss} lack an implementation - '
                         f'defaulting to MreRecord')
            rtype.sig_to_class.update(dict.fromkeys(miss, brec.MreRecord))
        rtype.sig_to_class = {k: v for k, v in rtype.sig_to_class.items() if
                              k in valid_header_sigs}
        rec_head.valid_record_sigs = valid_header_sigs
        from ..mod_files import LoadFactory as Lf
        Lf.grup_class = dict.fromkeys(cls.top_groups, brec.TopGrup)
        Lf.grup_class[b'DIAL'] = brec.MobDials
        Lf.grup_class[b'CELL'] = brec.MobICells
        Lf.grup_class[b'WRLD'] = brec.MobWorlds
        # that's the case for most games so do it here and override if needed
        rtype.simpleTypes = set(cls.top_groups) - cls.complex_groups
        # set GRUP class variables
        mobs = brec.record_groups
        cell_class = rtype.sig_to_class[b'CELL']
        mobs.CellRefs._accepted_sigs = cell_class.ref_types
        mobs.TempRefs._accepted_sigs = mobs.CellChildren._accepted_sigs = {
            *cell_class.ref_types, *cell_class.interior_temp_extra}
        wrld_class = rtype.sig_to_class[b'WRLD']
        wrld_cell = {*wrld_class.ref_types, *wrld_class.exterior_temp_extra}
        mobs.WrldTempRefs._accepted_sigs = \
            mobs.ExtCellChildren._accepted_sigs = wrld_cell
        mobs.WorldChildren._accepted_sigs = {*wrld_cell,
                                             *wrld_class.wrld_children_extra}
