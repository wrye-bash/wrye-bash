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
#  Wrye Bash copyright (C) 2005-2009 Wrye, 2010-2026 Wrye Bash Team
#  https://github.com/wrye-bash
#
# =============================================================================
"""Module containing the PatcherConfig classes from which the game chooses
which ones to mixin with the _PatcherPanel types."""
from __future__ import annotations

from collections import defaultdict
from functools import partial
from itertools import chain
from typing import ClassVar

from .base import APatcher, ListPatcher, MultiTweakItem
from .patchers import checkers, mergers, multitweak_actors, \
    multitweak_assorted, multitweak_clothes, multitweak_names, \
    multitweak_races, multitweak_settings, preservers
from .patchers.base import AliasPluginNamesPatcher, MultiTweaker, \
    MergePatchesPatcher, ReplaceFormIDsPatcher
from .. import bass, bosh, load_order
from ..bolt import forward_compat_path_to_fn, FName, FNDict, \
    forward_compat_path_to_fn_list
from ..plugin_types import MergeabilityCheck

class PatcherConfig:
    """Mixin to add configuration API to the patchers."""
    patcher_name: ClassVar[str]
    # The key that will be used to read and write entries for BP configs
    # These are sometimes quite ugly - backwards compat leftover from when
    # those were the class names and got written directly into the configs
    _config_key: ClassVar[str]
    patcher_type: ClassVar[type[APatcher]]
    patcher_desc: ClassVar[str] # only used in the GUI - keep it so
    # CONFIG DEFAULTS
    isEnabled = False # is the patcher enabled on a new bashed patch ?
    _override = ('patcher_name', '_config_key', 'patcher_type', 'patcher_desc')

    def __init__(self, bp_file, *args, **kwargs):
        c = self.__class__
        if xxx := [x for x in c._override if not hasattr(c, x)]:
            raise SyntaxError(f'{c.__name__}: missing class variable(s) {xxx}')
        super().__init__(*args, **kwargs)
        # executing bashed patch file, use only for info on active mod arrays
        self._bp = bp_file

    def _getConfig(self, configs):
        """Get config from configs dictionary and/or set to default.

        Called in basher.patcher_dialog.PatchDialog#__init__, before the
        dialog is shown, to update the patch options based on the previous
        config for this patch loaded via get_table_prop('bash.patch.configs').
        Fallback to default_XXX class vars for missing config entries."""
        self._is_first_load = not configs
        # Remember whether we were present in the config for bolding later
        self._was_present = (cls := self.__class__)._config_key in configs
        config = configs[cls._config_key] if self._was_present else {}
        for att, def_val, *funct in cls._config_attrs():
            val = config.get(att, def_val)
            setattr(self, att, funct[0](val) if funct else val)
        # return the config dict for this patcher to read additional values
        return config

    @classmethod
    def _config_attrs(cls):
        return ('isEnabled', cls.isEnabled),

    def saveConfig(self, configs):
        """Save config to configs dictionary.

        Most patchers just save their enabled state, except the
        _ListPatcherPanel subclasses - which save their choices - and the
        AliasPluginNames that saves the aliases."""
        config = configs[self.__class__._config_key] = {}
        for att, *_rest in self._config_attrs():
            config[att] = getattr(self, att)
        return config # return the config dict for this patcher to further edit

    @classmethod
    def log_config(cls, config, clip, log):
        ckey = cls._config_key
        # Check if the patcher is in the config and was enabled
        if ckey not in config or not (conf := config[ckey]).get('isEnabled'):
            return
        humanName = cls.patcher_name
        log.setHeader(f'== {humanName}')
        clip.write('\n')
        clip.write(f'== {humanName}\n')
        cls._log_config(conf, config, clip, log)

    @classmethod
    def _log_config(cls, conf, config, clip, log):
        items = conf.get(u'configItems', [])
        if not items:
            log(u' ')
            return
        checks = conf.get(u'configChecks', {})
        for item in items:
            checked = checks.get(item, False)
            if checked:
                log(f'* __{item}__')
                clip.write(f' ** {item}\n')
            else:
                log(f'. ~~{item}~~')
                clip.write(f'    {item}\n')

    def import_config(self, patchConfigs, **kwargs):
        self._getConfig(patchConfigs) # set isEnabled and load additional config

    def get_patcher_instance(self, patch_file):
        """Instantiate and return an instance of self.__class__.patcher_type,
        initialized with the config options from the Gui"""
        return self.patcher_type(self.patcher_name, patch_file)

#------------------------------------------------------------------------------
class ListPatcherConfig(PatcherConfig):
    """Patcher config for ListPatcherConfig."""
    patcher_type: ClassVar[type[ListPatcher]]
    _autocheck_new = True

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.configItems: list[FName] = []
        self.configChecks: dict[FName, bool] = {}
        self.configChoices: dict[FName, set[str]] = {}
        self._item_config: dict[FName, bool] = {}
        self._check = self._autocheck_new and bass.inisettings['AutoItemCheck']

    def _getConfig(self, configs):
        """Merge entries from the config with existing ones - if we're loading
        the first config, the existing ones will be empty. Otherwise, we're
        restoring a config into an existing state, so don't delete the already
        present items and keep the checked/choices state for those."""
        conf_copy = dict(self._item_config)
        config = super()._getConfig(configs) # loads self.configItems and co
        (conf_items := self.configItems).extend(
            it for it in conf_copy.keys() - {*conf_items})
        #--Verify file existence
        conf_items = self.patcher_type.get_sources(self._bp, conf_items)
        # Restore the old checked/choices state (if the items in question
        # are actually still present in the Data folder)
        self._item_config = self._merge_configs(conf_copy, set(conf_items))
        return config

    @classmethod
    def _config_attrs(cls):
        return (*super()._config_attrs(),
                ('configItems', [], forward_compat_path_to_fn_list),
                ('configChecks', {}, forward_compat_path_to_fn),
                ('configChoices', {}, forward_compat_path_to_fn))

    def saveConfig(self, configs):
        """Save config to configs dictionary."""
        ic = self._item_config
        self.configChecks = {k: isinstance(v, set) or v for k, v in ic.items()}
        self.configChoices = {k: v if isinstance(v, set) else set() for k, v in
                              ic.items()}
        self.configItems = [*ic]
        return super().saveConfig(configs)

    def get_patcher_instance(self, patch_file):
        patcher_sources = self._get_list_patcher_srcs()
        return self.patcher_type(self.patcher_name, patch_file,
                                 patcher_sources)

    def import_config(self, patchConfigs, **kwargs):
        super().import_config(patchConfigs)
        kwargs.setdefault('is_auto', self._is_first_load)
        self._sort_and_update_items(**kwargs)

    def _sort_and_update_items(self, is_auto=True, do_sort=True):
        if is_auto:
            for mod in (unsort := self.__class__.patcher_type.get_sources(
                    self._bp)):
                self._set_choice(mod)
        else:
            unsort = self._item_config
        unsort = load_order.cached_sort(unsort) if do_sort else unsort
        self._item_config = {k: self._item_config[k] for k in unsort}

    def _set_choice(self, item):
        """Check or uncheck new items."""
        if self._item_config.get(item) is None:
            self._item_config[item] = self._check and not item.lower(
                ).endswith('.csv')

    def _merge_configs(self, curr_conf, present_config_items):
        checks = {**curr_conf, **self.configChecks} # latter is freshly loaded
        return {k: v for k, v in checks.items() if k in present_config_items}

    @classmethod
    def _mod_label(cls, item: FName, conf_choices):
        """Returns label for item to be used in GUI list and in logging."""
        return item

    def _get_list_patcher_srcs(self):
        # ListsMerger instances get all the listed sources
        return [k for k, v in self._item_config.items() if v is not False]

#------------------------------------------------------------------------------
# Config Patcher classes
# Do _not_ change the _config_key attr or you will break existing BP configs
#------------------------------------------------------------------------------
# Patchers 10 -----------------------------------------------------------------
class AliasPluginNames(PatcherConfig):
    """Patcher config for AliasPluginNamesPatcher."""
    patcher_name = _('Alias Plugin Names')
    patcher_desc = _('Specify plugin aliases for reading CSV source files.')
    _config_key = 'AliasesPatcher'
    patcher_type = AliasPluginNamesPatcher
    aliases: FNDict  # AliasPluginNames uses forward_compat_path_to_fn

    @classmethod
    def _config_attrs(cls):
        return *super()._config_attrs(), ('aliases', {}, partial(
            # call str twice in case v._s was a str subtype
            forward_compat_path_to_fn, fn_value=True))

    @classmethod
    def _log_config(cls, conf, config, clip, log):
        fn_aliases = config.get('aliases', {})
        for mod, alias in fn_aliases.items():
            log(f'* __{mod}__ >> {alias}')
            clip.write(f'  {mod} >> {alias}\n')

    def get_patcher_instance(self, patch_file):
        """Set patch_file aliases dict"""
        if self.isEnabled:
            patch_file.pfile_aliases = self.aliases
        return self.patcher_type(self.patcher_name, patch_file)

#------------------------------------------------------------------------------
class MergePatches(ListPatcherConfig):
    """Merges specified patches into Bashed Patch."""
    _list_label = _('Mergeable Plugins')
    patcher_name = _('Merge Patches')
    patcher_desc = _('Merge patch plugins into the Bashed Patch.')
    _config_key = 'PatchMerger'
    patcher_type = MergePatchesPatcher

# Patchers 20 -----------------------------------------------------------------
class ImporterPatcherConfig(ListPatcherConfig):

    def saveConfig(self, configs):
        """Save config to configs dictionary."""
        config = super().saveConfig(configs)
        if self.isEnabled:
            configs['ImportedMods'].update(
                [item for item, value in self._item_config.items() if
                 value and bosh.ModInfos.check_filename(item)])
        return config

#------------------------------------------------------------------------------
class ImportGraphics(ImporterPatcherConfig):
    """Merges changes to graphics (models and icons)."""
    patcher_name = _('Import Graphics')
    patcher_desc = _('Import graphics (models, icons, etc.) from source '
                     'plugins.')
    _config_key = 'GraphicsPatcher'
    patcher_type = preservers.ImportGraphicsPatcher

# -----------------------------------------------------------------------------
class ImportActorsAIPackages(ImporterPatcherConfig):
    """Merges changes to the AI Packages of Actors."""
    patcher_name = _('Import Actors: AI Packages')
    patcher_desc = _('Import actor AI Package links from source plugins.')
    _config_key = 'NPCAIPackagePatcher'
    patcher_type = mergers.ImportActorsAIPackagesPatcher

# -----------------------------------------------------------------------------
class ImportActors(ImporterPatcherConfig):
    """Merges changes to actors."""
    patcher_name = _('Import Actors')
    patcher_desc = _('Import various actor attributes from source plugins.')
    _config_key = 'ActorImporter'
    patcher_type = preservers.ImportActorsPatcher

# -----------------------------------------------------------------------------
class ImportActorsPerks(ImporterPatcherConfig):
    """Merges changes to actor perks."""
    patcher_name = _('Import Actors: Perks')
    patcher_desc = _('Import actor perks from source plugins.')
    _config_key = 'ImportActorsPerks'
    patcher_type = mergers.ImportActorsPerksPatcher

# -----------------------------------------------------------------------------
class ImportCells(ImporterPatcherConfig):
    """Merges changes to cells (climate, lighting, and water.)"""
    patcher_name = _('Import Cells')
    patcher_desc = _('Import cells (climate, lighting, and water) from '
                     'source plugins.')
    _config_key = 'CellImporter'
    patcher_type = preservers.ImportCellsPatcher

# -----------------------------------------------------------------------------
class ImportActorsFactions(ImporterPatcherConfig):
    """Import factions to creatures and NPCs."""
    patcher_name = _('Import Actors: Factions')
    patcher_desc = _('Import actor factions from source plugins/files.')
    _config_key = 'ImportFactions'
    patcher_type = preservers.ImportActorsFactionsPatcher

# -----------------------------------------------------------------------------
class ImportRelations(ImporterPatcherConfig):
    """Import faction relations to factions."""
    patcher_name = _('Import Relations')
    patcher_desc = _('Import relations from source plugins/files.')
    _config_key = 'ImportRelations'
    patcher_type = mergers.ImportRelationsPatcher

# -----------------------------------------------------------------------------
class ImportInventory(ImporterPatcherConfig):
    """Merge changes to actor inventories."""
    patcher_name = _('Import Inventory')
    patcher_desc = _('Merges changes to items in various inventories.')
    _config_key = 'ImportInventory'
    patcher_type = mergers.ImportInventoryPatcher

# -----------------------------------------------------------------------------
class ImportOutfits(ImporterPatcherConfig):
    """Merge changes to outfits."""
    patcher_name = _('Import Outfits')
    patcher_desc = _('Merges changes to NPC outfits.')
    _config_key = 'ImportOutfits'
    patcher_type = mergers.ImportOutfitsPatcher

# -----------------------------------------------------------------------------
class ImportActorsSpells(ImporterPatcherConfig):
    """Merges changes to the spells lists of Actors."""
    patcher_name = _('Import Actors: Spells')
    patcher_desc = _('Merges changes to actor spell / effect lists.')
    _config_key = 'ImportActorsSpells'
    patcher_type = mergers.ImportActorsSpellsPatcher

# -----------------------------------------------------------------------------
class ImportNames(ImporterPatcherConfig):
    """Import names from sources."""
    patcher_name = _('Import Names')
    patcher_desc = _('Import names from source plugins/files.')
    _config_key = 'NamesPatcher'
    patcher_type = preservers.ImportNamesPatcher

# -----------------------------------------------------------------------------
class ImportActorsFaces(ImporterPatcherConfig):
    """NPC Faces patcher, for use with TNR or similar plugins."""
    patcher_name = _('Import Actors: Faces')
    patcher_desc = _('Import NPC face/eyes/hair from source plugins. For use '
                     'with TNR and similar mods.')
    _config_key = 'NpcFacePatcher'
    patcher_type = preservers.ImportActorsFacesPatcher

# -----------------------------------------------------------------------------
class ImportSounds(ImporterPatcherConfig):
    """Imports sounds from source plugins into patch."""
    patcher_name = _('Import Sounds')
    patcher_desc = _('Import sounds (from Magic Effects, Containers, '
                     'Activators, Lights, Weathers and Doors) from source '
                     'plugins.')
    _config_key = 'SoundPatcher'
    patcher_type = preservers.ImportSoundsPatcher

# -----------------------------------------------------------------------------
class ImportStats(ImporterPatcherConfig):
    """Import stats from mod file."""
    patcher_name = _('Import Stats')
    patcher_desc = _('Import stats from any pickupable items from source '
                     'plugins/files.')
    _config_key = 'StatsPatcher'
    patcher_type = preservers.ImportStatsPatcher

# -----------------------------------------------------------------------------
class ImportScripts(ImporterPatcherConfig):
    """Imports attached scripts on objects."""
    patcher_name = _('Import Scripts')
    patcher_desc = _('Import scripts on various objects (e.g. containers, '
                     'weapons, etc.) from source plugins.')
    _config_key = 'ImportScripts'
    patcher_type = preservers.ImportScriptsPatcher

# -----------------------------------------------------------------------------
class ImportRaces(ImporterPatcherConfig):
    """Imports race-related data."""
    patcher_name = _('Import Races')
    patcher_desc = _('Import race eyes, hair, body, voice, etc. from source '
                     'plugins.')
    _config_key = 'ImportRaces'
    patcher_type = preservers.ImportRacesPatcher

# -----------------------------------------------------------------------------
class ImportRacesRelations(ImporterPatcherConfig):
    """Imports race-faction relations."""
    patcher_name = _('Import Races: Relations')
    patcher_desc = _('Import race-faction relations from source plugins.')
    _config_key = 'ImportRacesRelations'
    patcher_type = mergers.ImportRacesRelationsPatcher

# -----------------------------------------------------------------------------
class ImportRacesSpells(ImporterPatcherConfig):
    """Imports race spells/abilities."""
    patcher_name = _('Import Races: Spells')
    patcher_desc = _('Import race abilities and spells from source plugins.')
    _config_key = 'ImportRacesSpells'
    patcher_type = mergers.ImportRacesSpellsPatcher

# -----------------------------------------------------------------------------
class ImportSpellStats(ImporterPatcherConfig):
    """Import spell changes from mod files."""
    patcher_name = _('Import Spell Stats')
    patcher_desc = _('Import stats from spells from source plugins/files.')
    _config_key = 'SpellsPatcher'
    patcher_type = preservers.ImportSpellStatsPatcher

# -----------------------------------------------------------------------------
class ImportDestructible(ImporterPatcherConfig):
    patcher_name = _('Import Destructible')
    patcher_desc = _('Preserves changes to destructible records.')
    _config_key = 'DestructiblePatcher'
    patcher_type = preservers.ImportDestructiblePatcher

# -----------------------------------------------------------------------------
class ImportKeywords(ImporterPatcherConfig):
    patcher_name = _('Import Keywords')
    patcher_desc = _('Import keyword changes from source plugins.')
    _config_key = 'KeywordsImporter'
    patcher_type = preservers.ImportKeywordsPatcher

# -----------------------------------------------------------------------------
class ImportText(ImporterPatcherConfig):
    patcher_name = _('Import Text')
    patcher_desc = _('Import various types of long-form text like book '
                     'texts, effect descriptions, etc. from source plugins.')
    _config_key = 'TextImporter'
    patcher_type = preservers.ImportTextPatcher

# -----------------------------------------------------------------------------
class ImportObjectBounds(ImporterPatcherConfig):
    patcher_name = _('Import Object Bounds')
    patcher_desc = _('Import object bounds for various actors, items and '
                     'objects.')
    _config_key = 'ObjectBoundsImporter'
    patcher_type = preservers.ImportObjectBoundsPatcher

# -----------------------------------------------------------------------------
class ImportEnchantmentStats(ImporterPatcherConfig):
    patcher_name = _('Import Enchantment Stats')
    patcher_desc = _('Import stats from enchantments from source plugins.')
    _config_key = 'ImportEnchantmentStats'
    patcher_type = preservers.ImportEnchantmentStatsPatcher

# -----------------------------------------------------------------------------
class ImportEffectStats(ImporterPatcherConfig):
    patcher_name = _('Import Effect Stats')
    patcher_desc = _('Import stats from magic/base effects from source '
                     'plugins.')
    _config_key = 'ImportEffectsStats'
    patcher_type = preservers.ImportEffectStatsPatcher

# -----------------------------------------------------------------------------
class ImportEnchantments(ImporterPatcherConfig):
    patcher_name = _('Import Enchantments')
    patcher_desc = _('Import enchantments from armor, weapons, etc. from '
                     'source plugins.')
    _config_key = 'ImportEnchantments'
    patcher_type = preservers.ImportEnchantmentsPatcher

# Patchers 30 -----------------------------------------------------------------
class TweakPatcherConfig(PatcherConfig):
    patcher_type: ClassVar[type[MultiTweaker]]

    def _getConfig(self, configs):
        """Get config from configs dictionary and/or set to default."""
        config = super()._getConfig(configs)
        self._all_tweaks = self._curr_tweaks = self._tweaks_config(config,
                                                                   self._bp)
        return config

    def saveConfig(self, configs):
        """Save config to configs dictionary."""
        config = super().saveConfig(configs)
        for tweak in self._all_tweaks:
            tweak.save_tweak_config(config)
        return config

    @classmethod
    def _log_config(cls, conf, config, clip, log):
        all_tweaks = cls._tweaks_config(config) # load tweaks config
        for tweak in all_tweaks:
            if tweak.tweak_key in conf:
                enabled, value = conf.get(tweak.tweak_key, (False, u''))
                list_label = tweak.getListLabel().replace('[[', '[').replace(
                    ']]', ']')
                if enabled:
                    log(f'* __{list_label}__')
                    clip.write(f' ** {list_label}\n')
                else:
                    log(f'. ~~{list_label}~~')
                    clip.write(f'    {list_label}\n')

    def get_patcher_instance(self, patch_file):
        enabledTweaks = [t for t in self._all_tweaks if t.isEnabled]
        return self.patcher_type(self.patcher_name, patch_file, enabledTweaks)

    @classmethod
    def _tweaks_config(cls, config, bashed_patch=None) -> list[MultiTweakItem]:
        all_tweaks = cls.patcher_type.tweak_instances(bashed_patch)
        for tweak in all_tweaks:
            tweak.init_tweak_config(config)
        return all_tweaks

#------------------------------------------------------------------------------
class TweakAssorted(TweakPatcherConfig):
    patcher_name = _('Tweak Assorted')
    patcher_desc = _('Tweak various records in miscellaneous ways.')
    _config_key = 'AssortedTweaker'
    patcher_type = multitweak_assorted.TweakAssortedPatcher
    isEnabled = True

# -----------------------------------------------------------------------------
class TweakClothes(TweakPatcherConfig):
    patcher_name = _('Tweak Clothes')
    patcher_desc = _('Tweak clothing weight and blocking.')
    _config_key = 'ClothesTweaker'
    patcher_type = multitweak_clothes.TweakClothesPatcher

# -----------------------------------------------------------------------------
class TweakSettings(TweakPatcherConfig):
    patcher_name = _('Tweak Settings')
    patcher_desc = _('Tweak game settings.')
    _config_key = 'GmstTweaker'
    patcher_type = multitweak_settings.TweakSettingsPatcher
    # CONFIG DEFAULTS
    isEnabled = True

# -----------------------------------------------------------------------------
class TweakNames(TweakPatcherConfig):
    patcher_name = _('Tweak Names')
    patcher_desc = _('Tweak object names to sort them by type/stats or to '
                     'improve things like lore friendliness.')
    _config_key = 'NamesTweaker'
    patcher_type = multitweak_names.TweakNamesPatcher

# -----------------------------------------------------------------------------
class TweakActors(TweakPatcherConfig):
    patcher_name = _('Tweak Actors')
    patcher_desc = _('Tweak NPC and Creatures records in specified ways.')
    _config_key = 'TweakActors'
    patcher_type = multitweak_actors.TweakActorsPatcher

# -----------------------------------------------------------------------------
class TweakRaces(TweakPatcherConfig):
    patcher_name = _('Tweak Races')
    patcher_desc = _('Tweak race records in specified ways.')
    _config_key = 'TweakRaces'
    patcher_type = multitweak_races.TweakRacesPatcher

# Patchers 40 -----------------------------------------------------------------
class ReplaceFormIDs(ListPatcherConfig):
    """Imports Form Id replacers into the Bashed Patch."""
    patcher_name = _('Replace Form IDs')
    patcher_desc = _('Imports Form Id replacers from csv files into the '
                     'Bashed Patch.')
    _config_key = 'UpdateReferences'
    patcher_type = ReplaceFormIDsPatcher
    _autocheck_new = False #--GUI: Whether new items are checked by default.

#------------------------------------------------------------------------------
class ListMergerConfig(ListPatcherConfig):
    patcher_type: ClassVar[type[mergers.AListsMerger]]
    _item_config: dict[FName, set[str]]
    autoIsChecked = True

    def _getConfig(self, configs):
        config = super()._getConfig(configs)
        for item in self._item_config:
            self._set_choice(item)
        return config

    @classmethod
    def _config_attrs(cls):
        return *super()._config_attrs(), ('autoIsChecked', True)

    def _merge_configs(self, curr_conf, present_config_items):
        choices = {**curr_conf, **self.configChoices}
        return {k: v for k, v in choices.items() if k in present_config_items}

    def _set_choice(self, item):
        if (config_choice := self._item_config.get(item)) is None:
            config_choice = {'Auto'}
        if 'Auto' in config_choice:
            tags = self._bp.all_tags.get(item, set())
            config_choice = {'Auto', *(self.patcher_type.patcher_tags & tags)}
        self._item_config[item] = config_choice
        return config_choice

    def import_config(self, *args, **kwargs):
        return super().import_config(*args, is_auto=self.autoIsChecked)

    @classmethod
    def _log_config(cls, conf, config, clip, log):
        conf_choices = conf.get('configChoices', {})
        for item in (cls._mod_label(i, conf_choices) for i in conf.get(
                'configItems', [])):
            log(f'. __{item}__')
            clip.write(f'    {item}\n')

    def get_patcher_instance(self, patch_file, rem_emp=False):
        patcher_sources = self._get_list_patcher_srcs()
        return self.patcher_type(self.patcher_name, patch_file,
            patcher_sources, rem_emp, defaultdict(set, self._item_config))

    @classmethod
    def _mod_label(cls, item, conf_choices):
        return cls.patcher_type.annotate_plugin(item, conf_choices)

class LeveledLists(ListMergerConfig):
    patcher_name = _('Leveled Lists')
    patcher_desc = '\n\n'.join([
        _('Merges changes to leveled lists from all active and/or merged '
          'plugins.'),
        _('Advanced users may override Relev/Delev tags for any mod (active '
          'or inactive) using the list below.')])
    _config_key = 'ListsMerger'
    patcher_type = mergers.LeveledListsPatcher
    isEnabled = True # GUI default value
    _remove_empty = False # GUI default value

    def get_patcher_instance(self, patch_file, rem_emp=False):
        return super().get_patcher_instance(patch_file,
                                            self.remove_empty_sublists)

    @classmethod
    def _config_attrs(cls):
        return *super()._config_attrs(), ('remove_empty_sublists',
                                          cls._remove_empty)

# -----------------------------------------------------------------------------
class FormIDLists(ListMergerConfig): #497: Fallout3/FalloutNV only - ALPHA!
    patcher_name = _('FormID Lists')
    patcher_desc = '\n\n'.join([_('Merges changes to FormID lists from all '
        'active and/or merged plugins.'), _('Advanced users may override '
        'Deflst tags for any mod (active or inactive) using the list below.')])
    _config_key = 'FidListsMerger'
    patcher_type = mergers.FormIDListsPatcher
    _list_label = _('Override Deflst Tag')
    _add_dialog_title = _('Add Deflst Tag to Plugin')
    choiceMenu = ('Auto', '----', 'Deflst')

# -----------------------------------------------------------------------------
class ContentsChecker(PatcherConfig):
    """Checks contents of leveled lists, inventories and containers for
    correct content types."""
    patcher_name = _('Contents Checker')
    patcher_desc = _('Checks contents of leveled lists, inventories and '
                     'containers for correct types.')
    _config_key = 'ContentsChecker'
    patcher_type = checkers.ContentsCheckerPatcher
    isEnabled = True

# -----------------------------------------------------------------------------
class RaceChecker(PatcherConfig):
    """Sorts hairs and eyes."""
    patcher_name = _('Race Checker')
    patcher_desc = _('Sorts race hairs and eyes.')
    _config_key = 'RaceChecker'
    patcher_type = checkers.RaceCheckerPatcher
    isEnabled = True

#------------------------------------------------------------------------------
class NpcChecker(PatcherConfig):
    """Assigns missing hair and eyes."""
    patcher_name = _('NPC Checker')
    patcher_desc = _('This will randomly assign hairs and eyes to NPCs that '
                     'are otherwise missing them.')
    _config_key = 'NpcChecker'
    patcher_type = checkers.NpcCheckerPatcher
    isEnabled = True

#------------------------------------------------------------------------------
class TimescaleChecker(PatcherConfig):
    """Adjusts the wave period of grass match changes in the timescale."""
    patcher_name = _('Timescale Checker')
    patcher_desc = '\n'.join([
        _('Adjusts the wave period of grasses to match changes in the '
          'timescale.'),
        _('Does nothing if you are not using a nonstandard timescale.'), '',
        _('Incompatible with plugins that change grass wave periods to match '
          'a different timescale. Uninstall such plugins before using this.'),
    ])
    _config_key = 'TimescaleChecker'
    patcher_type = checkers.TimescaleCheckerPatcher
    isEnabled = True

#------------------------------------------------------------------------------
# Collect the Game specific Config Patchers -----------------------------------
#------------------------------------------------------------------------------
game_patcher_config_types = defaultdict(dict) # map panel types to config types
# all patcher config classes for this game (globals or game_specific_patchers)
all_patcher_types: list[type[PatcherConfig]] = []
_gui_to_class = { # map GUI classes to globals in order to filter game pathcers
    '_PatcherPanel': {'ContentsChecker', 'NpcChecker', 'RaceChecker',
                      'TimescaleChecker'},
    'AliasPluginNames': {'AliasPluginNames'},
    '_ListPatcherPanel': {'MergePatches', 'ReplaceFormIDs', # importers follow
        'ImportGraphics', 'ImportActorsAIPackages',
        'ImportActors', 'ImportActorsPerks', 'ImportCells',
        'ImportActorsFactions', 'ImportRelations', 'ImportInventory',
        'ImportOutfits', 'ImportActorsSpells', 'ImportNames',
        'ImportActorsFaces', 'ImportSounds', 'ImportStats', 'ImportScripts',
        'ImportRaces', 'ImportRacesRelations', 'ImportRacesSpells',
        'ImportSpellStats', 'ImportDestructible', 'ImportKeywords',
        'ImportText', 'ImportObjectBounds', 'ImportEnchantmentStats',
        'ImportEffectStats', 'ImportEnchantments'},
    '_TweakPatcherPanel': {'TweakAssorted', 'TweakClothes', 'TweakSettings',
                           'TweakNames', 'TweakActors', 'TweakRaces'},
    '_ListsMergerPanel': {'FormIDLists'},
    'LeveledLists': {'LeveledLists'},
}

def init_patcher_types(game_handle):
    """Select PatcherConfig subtypes from globals and game_specific_patchers.
    Also check if MergePatchers should be included and set allTags by
    collecting patcher_tags."""
    game_patcher_config_types.clear()
    for gui_type, patcher_types in _gui_to_class.items():
         for p in patcher_types & game_handle.patchers:
             game_patcher_config_types[gui_type][p] = globals()[p]
    # Add game specific patchers
    for gui_type, patcher_types in game_handle.game_specific_patchers.items():
        game_patcher_config_types[gui_type].update(patcher_types)
    group_order = {p_grp: i for i, p_grp in enumerate(
        ('General', 'Importers', 'Tweakers', 'Special'))}
    # If we want to merge patches into the BP, we need the patch merger
    if MergeabilityCheck.MERGE in game_handle.mergeability_checks:
        game_patcher_config_types['_ListPatcherPanel']['MergePatches'] = \
            MergePatches
        # And the NoMerge tag needs to get added too
        game_handle.allTags.add('NoMerge')
    all_patcher_types.clear()
    all_patcher_types.extend(chain.from_iterable(
        v.values() for v in game_patcher_config_types.values()))
    # Sort by group to make patchers instantiate in the right order,
    # then alphabetically to display in the GUi
    all_patcher_types.sort(key=lambda a: (
        group_order[a.patcher_type.patcher_group], a.patcher_name))
    # Update the set of all tags for this game based on the available patchers
    game_handle.allTags.update(chain.from_iterable(getattr(
        p.patcher_type, 'patcher_tags', ()) for p in all_patcher_types))
