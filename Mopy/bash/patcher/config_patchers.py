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
from typing import ClassVar

from .. import bosh, bush
from ..bolt import forward_compat_path_to_fn, FName, \
    forward_compat_path_to_fn_list
from .base import APatcher, ListPatcher
from .patchers import mergers
from .patchers.base import AliasPluginNamesPatcher, MultiTweaker

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
    default_isEnabled = False # is the patcher enabled on a new bashed patch ?
    _override = ('patcher_name', '_config_key', 'patcher_type')

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
        return ('isEnabled', cls.default_isEnabled),

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

    def import_config(self, patchConfigs, set_first_load):
        self._is_first_load = set_first_load
        self._getConfig(patchConfigs) # set isEnabled and load additional config

    def get_patcher_instance(self, patch_file):
        """Instantiate and return an instance of self.__class__.patcher_type,
        initialized with the config options from the Gui"""
        return self.patcher_type(self.patcher_name, patch_file)

#------------------------------------------------------------------------------
class AliasesPatcherConfig(PatcherConfig):
    """Patcher config for AliasPluginNamesPatcher."""
    patcher_name = _('Alias Plugin Names')
    patcher_desc = _('Specify plugin aliases for reading CSV source files.')
    _config_key = 'AliasesPatcher'
    patcher_type = AliasPluginNamesPatcher

    @classmethod
    def _config_attrs(cls):
        return *super()._config_attrs(), ('aliases', {}, partial(
            # call str twice in case v._s was a str subtype
            forward_compat_path_to_fn, fn_value=True))

    @classmethod
    def _log_config(cls, conf, config, clip, log):
        fn_aliases = config.get(u'aliases', {})
        for mod, alias in fn_aliases.items():
            log(f'* __{mod}__ >> {alias}')
            clip.write(f'  {mod} >> {alias}\n')

    def get_patcher_instance(self, patch_file):
        """Set patch_file aliases dict"""
        if self.isEnabled:
            patch_file.pfile_aliases = self.aliases
        return self.patcher_type(self.patcher_name, patch_file)

#------------------------------------------------------------------------------
class ListPatcherConfig(PatcherConfig):
    """Patcher config for ListPatcherConfig."""
    patcher_type: ClassVar[type[ListPatcher]]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.configItems: list[FName] = []
        self.configChecks: dict[FName, bool] = {}
        self.configChoices: dict[FName, set[str]] = {}
        self._item_config: dict[FName, bool] = {}

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
    def _tweaks_config(cls, config, bashed_patch=None):
        all_tweaks = cls.patcher_type.tweak_instances(bashed_patch)
        for tweak in all_tweaks:
            tweak.init_tweak_config(config)
        return all_tweaks

#------------------------------------------------------------------------------
class _ImporterPatcherConfig(ListPatcherConfig):

    def saveConfig(self, configs):
        """Save config to configs dictionary."""
        config = super().saveConfig(configs)
        if self.isEnabled:
            configs[u'ImportedMods'].update(
                [item for item, value in self._item_config.items() if
                 value and bosh.ModInfos.check_filename(item)])
        return config

#------------------------------------------------------------------------------
class _ListMergerConfig(ListPatcherConfig):
    patcher_type: ClassVar[type[mergers.AListsMerger]]
    _item_config: dict[FName, set[str]]

    def _merge_configs(self, curr_conf, present_config_items):
        choices = {**curr_conf, **self.configChoices}
        return {k: v for k, v in choices.items() if k in present_config_items}

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

class LeveledListsConfig(_ListMergerConfig):
    patcher_name = _('Leveled Lists')
    patcher_desc = '\n\n'.join([
        _('Merges changes to leveled lists from all active and/or merged '
          'plugins.'),
        _('Advanced users may override Relev/Delev tags for any mod (active '
          'or inactive) using the list below.')])
    _config_key = 'ListsMerger'
    patcher_type = mergers.LeveledListsPatcher
    default_isEnabled = True

    def get_patcher_instance(self, patch_file, rem_emp=False):
        return super().get_patcher_instance(patch_file,
                                            self.remove_empty_sublists)

    @classmethod
    def _config_attrs(cls): ##: Hack, this should not use display_name
        return *super()._config_attrs(), ('remove_empty_sublists',
                                          bush.game.display_name == 'Oblivion')
