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
#  Wrye Bash copyright (C) 2005-2009 Wrye, 2010-2026 Wrye Bash Team
#  https://github.com/wrye-bash
#
# =============================================================================
from __future__ import annotations

import re
from collections import defaultdict
from itertools import chain
from typing import ClassVar

from .patcher_dialog import gpatcher_types
from .. import bass, bolt, bosh, bush, load_order
from ..balt import CheckLink, SeparatorLink
from ..bolt import FName, dict_sort, forward_compat_path_to_fn, \
    forward_compat_path_to_fn_list, text_wrap
from ..gui import TOP, Button, CheckBox, CheckListBox, DeselectAllButton, \
    EventResult, FileOpenMultiple, HBoxedLayout, Label, LayoutOptions, Lazy, \
    ListBox, Links, PanelWin, SearchBar, SelectAllButton, Spacer, TextArea, \
    VLayout, askText, showError, askNumber
from ..patcher.base import APatcher, MultiTweakItem, ListPatcher
from ..patcher.patchers import checkers, mergers, multitweak_actors, \
    multitweak_assorted, multitweak_clothes, multitweak_names, \
    multitweak_races, multitweak_settings, preservers
from ..patcher.patchers.base import AliasPluginNamesPatcher, \
    MergePatchesPatcher, MultiTweaker, ReplaceFormIDsPatcher
from ..plugin_types import MergeabilityCheck

class PatcherConfig:
    """Mixin to add configuration API to the patchers."""
    patcher_name: ClassVar[str]
    # The key that will be used to read and write entries for BP configs
    # These are sometimes quite ugly - backwards compat leftover from when
    # those were the class names and got written directly into the configs
    _config_key: ClassVar[str]
    patcher_type: ClassVar[type[APatcher]]
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
        self._was_present = self.__class__._config_key in configs
        config = (configs[self.__class__._config_key]
                  if self._was_present else {})
        for att, def_val in self._config_attrs():
            setattr(self, att, config.get(att, def_val))
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
        for att, _dflt in self._config_attrs():
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

class _PatcherPanel(Lazy, PanelWin):
    """Basic patcher panel with no options."""
    patcher_desc: ClassVar[str]
    selectCommands = True # whether this panel displays De/Select All
    _override = *PatcherConfig._override, 'patcher_desc'

    def __init__(self):
        super().__init__(no_border=False)
        # Used to keep track of the state of the patcher label
        self._is_bolded = False
        self._is_italicized = False

    def native_init(self, *args, patch_configs=None, **kwargs):
        if freshly_created := super().native_init(*args, **kwargs):
            self.visible = False # needed else all pathcers appear at once
            self.main_layout = VLayout(
                item_expand=True, item_weight=1, spacing=4, items=[
                    (Label(self, text_wrap(self.patcher_desc, 70)),
                     LayoutOptions(weight=0))])
            self.main_layout.apply_to(self)
            self._parent.config_layout.add(self)
            self._is_first_load = 0 == len(patch_configs)
            self._getConfig(patch_configs) # set isEnabled and load additional config
            # Bold the patcher if it's new, but the patch itself isn't new
            if not self._was_present and not self._is_first_load:
                self._style_patcher_label(bold=True)
        return freshly_created

    def _style_patcher_label(self, bold=False, italics=False):
        self._is_bolded |= bold
        self._is_italicized |= italics
        self._parent.style_patcher(self, bold=self._is_bolded,
                                   italics=self._is_italicized)

    def mass_select(self, select=True):
        self._enable_self(select)
        self._set_focus()

    @property
    def patcher_tip(self):
        # Remove everything but the first sentence from the first line of the
        # patcher description
        return re.sub(r'\..*', '.', self.patcher_desc.split('\n')[0])

    def _enable_self(self, self_enabled=True):
        """Enables or disables this patcher and notifies the patcher dialog."""
        self.isEnabled = self_enabled
        self._parent.check_patcher(self, self_enabled)

    def _set_focus(self): # TODO(ut) check if set_focus is enough
        self._parent.gPatchers.set_focus_from_kb()

#------------------------------------------------------------------------------
class AliasesPatcherConfig(PatcherConfig):
    """Patcher config for AliasPluginNamesPatcher."""
    patcher_name = _('Alias Plugin Names')
    patcher_desc = _('Specify plugin aliases for reading CSV source files.')
    _config_key = 'AliasesPatcher'
    patcher_type = AliasPluginNamesPatcher

    def _getConfig(self, configs):
        """Get config from configs dictionary and/or set to default."""
        config = super()._getConfig(configs)
        #--Update old configs to use Paths instead of strings.
        # call str twice in case v._s was a str subtype
        self.aliases = forward_compat_path_to_fn(self.aliases, fn_value=True)
        return config

    @classmethod
    def _config_attrs(cls):
        return *super()._config_attrs(), ('aliases', {})

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

class _AliasesPatcherPanel(AliasesPatcherConfig, _PatcherPanel):

    def native_init(self, *args, **kwargs):
        if freshly_created :=  super().native_init(*args, **kwargs):
            #--Aliases Text
            # gExample = Label(self, _("ExampleMod1.esp >> ExampleMod1.2.esp"))
            self.gAliases = TextArea(self)
            self.gAliases.on_focus_lost.subscribe(self.OnEditAliases)
            self.SetAliasText()
            #--Sizing
            self.main_layout.add((self.gAliases, LayoutOptions(
                expand=True, weight=1)))
        return freshly_created

    def SetAliasText(self):
        """Sets alias text according to current aliases."""
        self.gAliases.text_content = u'\n'.join([
            f'{alias_target} >> {alias_repl}'
            for alias_target, alias_repl in dict_sort(self.aliases)])

    def OnEditAliases(self):
        aliases_text = self.gAliases.text_content
        self.aliases.clear()
        for line in aliases_text.split(u'\n'):
            fields = [s.strip() for s in line.split(u'>>')]
            if len(fields) != 2 or not fields[0] or not fields[1]: continue
            self.aliases[fields[0]] = FName(fields[1])
        self.SetAliasText()

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
        conf_items = forward_compat_path_to_fn_list(self.configItems)
        conf_items.extend(it for it in conf_copy.keys() - {*conf_items})
        #--Verify file existence
        conf_items = self.patcher_type.get_sources(self._bp, conf_items)
        # Restore the old checked/choices state (if the items in question
        # are actually still present in the Data folder)
        self._item_config = self._merge_configs(conf_copy, set(conf_items))
        return config

    @classmethod
    def _config_attrs(cls):
        return *super()._config_attrs(), ('configItems', []), (
            'configChecks', {}), ('configChoices', {})

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

    def _merge_configs(self, conf_checks, present_config_items):
        return {k: v for k, v in {**conf_checks, **forward_compat_path_to_fn(
            self.configChecks)}.items() if k in present_config_items}

    @classmethod
    def _mod_label(cls, item: FName, conf_choices):
        """Returns label for item to be used in GUI list and in logging."""
        return item

    def _get_list_patcher_srcs(self):
        # ListsMerger instances get all the listed sources
        return [k for k, v in self._item_config.items() if v is not False]

class _ListPatcherPanel(ListPatcherConfig, _PatcherPanel):
    """Patcher panel with option to select source elements."""
    _autocheck_new = True #--GUI: Whether new items are checked by default
    gList: ListBox | CheckListBox

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # List of items that are currently visible (according to the search)
        self._curr_items: list[FName] = []
        # Set of items that are new and hence need to remain bolded
        self._new_items: set[FName] = set()
        self._check = self._autocheck_new and bass.inisettings['AutoItemCheck']

    def native_init(self, *args, **kwargs):
        if freshly_created := super().native_init(*args, **kwargs):
            self._get_glist()
            self._item_search = SearchBar(self, hint=_('Search Sources'))
            self._item_search.on_text_changed.subscribe(
                self._handle_item_search)
            #--Manual controls
            side_button_layout = self._auto_layout()
            self.main_layout.add(
                (HBoxedLayout(self, title=self._list_label,
                              item_expand=True, spacing=4, items=[
                        (VLayout(spacing=4, item_expand=True, items=[
                            self._item_search,
                            (self.gList, LayoutOptions(weight=1)),
                        ]), LayoutOptions(weight=1)),
                        (side_button_layout, LayoutOptions(v_align=TOP)),
                        self._get_select_layout(),
                    ]), LayoutOptions(expand=True, weight=1)))
        return freshly_created

    def _auto_layout(self, right_side_components=None):
        self._sort_and_update_items()
        return None

    def _sort_and_update_items(self, is_auto=True, do_sort=True):
        """Helper for LO-sorting items and updating the internal caches for
        them."""
        if is_auto:
            for mod in (unsort := self.__class__.patcher_type.get_sources(
                    self._bp)):
                self._set_choice(mod)
        else:
            unsort = self._item_config
        unsort = load_order.cached_sort(unsort) if do_sort else unsort
        self._item_config = {k: self._item_config[k] for k in unsort}
        # Clear the search bar - this will _handle_item_search, which will call
        # _do_populate_item_list in turn
        self._item_search.text_content = ''

    def _set_choice(self, item):
        """Only called when loading automatically for _ListPatcherPanel."""
        if self._item_config.get(item) is None:
            if not self._is_first_load:
                self._new_items.add(item)
            self._item_config[item] = self._check and not item.lower(
                ).endswith('.csv')

    def _get_glist(self):
        self.gList = CheckListBox(self)
        self.gList.on_box_checked.subscribe(self.OnListCheck)

    @property
    def _list_label(self):
        try:
            return self.__class__.listLabel
        except AttributeError:
            return _('Source Plugins/Files') if self.patcher_type._csv_key \
                else _('Source Plugins')

    def _handle_item_search(self, search_str):
        """Internal callback used to repopulate the item list whenever the
        text in the search bar changes."""
        lower_search_str = search_str.strip().lower()
        self._curr_items = [i for i in self._item_config if
                            lower_search_str in i.lower()]
        with self.gList.pause_drawing():
            self._do_populate_item_list()

    def _get_select_layout(self):
        if not self.selectCommands: return None
        self.gSelectAll = SelectAllButton(self, btn_tooltip=_(
            'Activate all currently visible sources.'),
            on_click=lambda: self.mass_select(True))
        self.gDeselectAll = DeselectAllButton(self, btn_tooltip=_(
            'Deactivate all currently visible sources.'),
            on_click=lambda: self.mass_select(False))
        return VLayout(spacing=4, items=[self.gSelectAll, self.gDeselectAll])

    def _do_populate_item_list(self):
        """Populate the patcher's item list based on the currently searched for
        items."""
        self.gList.lb_clear()
        patcherOn = False
        patcher_bold = False
        for index, item in enumerate(self._curr_items):
            itemLabel = self._mod_label(item, self._item_config)
            self.gList.lb_insert(itemLabel, index)
            # Indicate that this is a new item by bolding it and its parent patcher
            if do_bold := item in self._new_items:
                self.gList.lb_style_font_at_index(index, bold=True)
            patcherOn |= self._check_item(item, index)
            patcher_bold |= do_bold
        if patcherOn:
            self._enable_self()
        # Bold it if it has a new item, italicize it if it has no items
        patcher_italics = self.gList.lb_get_items_count() == 0
        self._style_patcher_label(bold=patcher_bold, italics=patcher_italics)

    def _check_item(self, item, index):
        self.gList.lb_check_at_index(index, val := self._item_config[item])
        return val

    def OnListCheck(self, _lb_selection_dex=None):
        """One of list items was checked. Update all configChecks states."""
        for i, item in enumerate(self._curr_items):
            self._item_config[item] = self.gList.lb_is_checked_at_index(i)
        self._enable_self(any(self._item_config.values()))

    def mass_select(self, select=True):
        try:
            self.gList.set_all_checkmarks(checked=select)
            self.OnListCheck()
        except AttributeError:
            pass #ListBox instead of CheckListBox
        super().mass_select(select)

    # Config Phase Overrides
    def import_config(self, patchConfigs, set_first_load):
        super().import_config(patchConfigs, set_first_load)
        if set_first_load:
            self._sort_and_update_items()
            return
        # Reset the search bar, this will call _handle_item_search
        self._item_search.text_content = ''
        for index, (item, checkmark) in enumerate(self._item_config.items()):
            try:
                self.gList.lb_check_at_index(index, checkmark)
            except KeyError:
                pass

#------------------------------------------------------------------------------
class _ChoiceMenuMixin(object):

    def _bind_mouse_events(self, right_click_list: ListBox | CheckListBox):
        right_click_list.on_mouse_motion.subscribe(self._handle_mouse_motion)
        right_click_list.on_mouse_right_down.subscribe(self._right_mouse_click)
        right_click_list.on_mouse_right_up.subscribe(self._right_mouse_up)
        self.mouse_pos = None

    def _right_mouse_click(self, pos): self.mouse_pos = pos

    def _right_mouse_up(self, lb_selection_dex):
        if self.mouse_pos: self.ShowChoiceMenu(lb_selection_dex)
        # return

    def _handle_mouse_motion(self, wrapped_evt, lb_dex):
        """Check mouse motion to detect right click event."""
        if wrapped_evt.is_dragging: # cancel right up if user drags mouse away of the item
            if self.mouse_pos:
                oldx, oldy = self.mouse_pos
                x, y = wrapped_evt.evt_pos
                if max(abs(x - oldx), abs(y - oldy)) > 4:
                    self.mouse_pos = None
                return EventResult.FINISH ##: needed?
        else:
            self.mouse_pos = None

    def ShowChoiceMenu(self, lb_selection_dex): raise NotImplementedError

_label_formats = {str: u'%s', float: u'%4.2f', int: u'%d'}
def _custom_label(label_text, val): # edit label text with value
    return f'{label_text}: {_label_formats[type(val)] % val}'

class TweakPatcherConfig(PatcherConfig):
    patcher_type: ClassVar[type[MultiTweaker]]

    def _getConfig(self, configs):
        """Get config from configs dictionary and/or set to default."""
        config = super()._getConfig(configs)
        self._all_tweaks = self._curr_tweaks = self._tweaks_config(config,
                                                                   self._bp)
        return config

    @classmethod
    def _tweaks_config(cls, config, bashed_patch=None):
        all_tweaks = cls.patcher_type.tweak_instances(bashed_patch)
        for tweak in all_tweaks:
            tweak.init_tweak_config(config)
        return all_tweaks

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

class _TweakPatcherPanel(TweakPatcherConfig, _ChoiceMenuMixin, _PatcherPanel):
    """Patcher panel with list of checkable, configurable tweaks."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # List of all tweaks that this tweaker can house
        self._all_tweaks: list[MultiTweakItem] = []
        # List of tweaks that are currently visible (according to the search)
        self._curr_tweaks: list[MultiTweakItem] = []

    def native_init(self, *args, **kwargs):
        if freshly_created := super().native_init(*args, **kwargs):
            self.gTweakList = CheckListBox(self)
            self.gTweakList.on_box_checked.subscribe(self.TweakOnListCheck)
            self._tweak_search = SearchBar(self, hint=_('Search Tweaks'))
            self._tweak_search.on_text_changed.subscribe(
                self._handle_tweak_search)
            #--Events
            self._bind_mouse_events(self.gTweakList)
            self.gTweakList.on_mouse_leaving.subscribe(self._mouse_leaving)
            self.mouse_dex = -1
            #--Layout
            self.main_layout.add(
                (HBoxedLayout(self, title=_('Tweaks'), item_expand=True,
                    spacing=4, items=[
                        (VLayout(item_expand=True, spacing=4, items=[
                            self._tweak_search,
                            (self.gTweakList, LayoutOptions(weight=1)),
                        ]), LayoutOptions(weight=1)),
                        self._get_tweak_select_layout()
                ]), LayoutOptions(expand=True, weight=1)))
        return freshly_created

    def _get_tweak_select_layout(self):
        if self.selectCommands:
            self.gTweakSelectAll = SelectAllButton(self, btn_tooltip=_(
                'Activate all currently visible tweaks.'),
                on_click=lambda: self.mass_select(True))
            self.gTweakDeselectAll = DeselectAllButton(self, btn_tooltip=_(
                'Deactivate all currently visible tweaks.'),
                on_click=lambda: self.mass_select(False))
            tweak_select_layout = VLayout(spacing=4, items=[
                self.gTweakSelectAll, self.gTweakDeselectAll])
        else: tweak_select_layout = None
        #--Init GUI
        self._populate_tweak_list()
        return tweak_select_layout

    def _populate_tweak_list(self):
        """Populate the patcher's tweak list based on the currently searched
        for tweaks."""
        with self.gTweakList.pause_drawing():
            self._do_populate_tweak_list()

    def _do_populate_tweak_list(self):
        self.gTweakList.lb_clear()
        patcher_bold = False
        for index, tweak in enumerate(self._curr_tweaks):
            item_label = tweak.getListLabel()
            if tweak.choiceLabels and tweak.choiceLabels[
                tweak.chosen] == tweak.custom_choice:
                item_label = _custom_label(item_label, tweak.choiceValues[tweak.chosen][0])
            self.gTweakList.lb_insert(item_label, index)
            self.gTweakList.lb_check_at_index(index, tweak.isEnabled)
            if not self._is_first_load and tweak.isNew():
                # Indicate that this is a new item by bolding it and its parent
                # patcher
                self.gTweakList.lb_style_font_at_index(index, bold=True)
                patcher_bold = True
        # Bold it if it has a new item, italicize it if it has no items
        patcher_italics = self.gTweakList.lb_get_items_count() == 0
        self._style_patcher_label(bold=patcher_bold, italics=patcher_italics)

    def TweakOnListCheck(self, _lb_selection_dex=None):
        """One of list items was checked. Update all check states."""
        for index, tweak in enumerate(self._curr_tweaks):
            tweak.isEnabled = self.gTweakList.lb_is_checked_at_index(index)
        self._enable_self(any(t.isEnabled for t in self._all_tweaks))

    def _mouse_leaving(self):
        self._parent.gTipText.label_text = ''
        self.mouse_pos = None

    def _handle_mouse_motion(self, wrapped_evt, lb_dex):
        """Check mouse motion to detect right click event. If any mouse button
         is held pressed, is_moving is False and is_dragging is True."""
        if wrapped_evt.is_moving:
            self.mouse_pos = None
            if lb_dex != self.mouse_dex:
                # Show tip text when changing item
                self.mouse_dex = lb_dex
                self._parent.gTipText.label_text = (
                    self._curr_tweaks[lb_dex].tweak_tip
                    if 0 <= lb_dex < len(self._curr_tweaks) else '')
        else:
            super(_TweakPatcherPanel, self)._handle_mouse_motion(wrapped_evt,
                                                                 lb_dex)

    def _handle_tweak_search(self, search_str):
        """Internal callback used to repopulate the tweak list whenever the
        text in the search bar changes."""
        lower_search_str = search_str.strip().lower()
        self._curr_tweaks = [t for t in self._all_tweaks
                             if lower_search_str in t.tweak_name.lower()
                             or lower_search_str in t.tweak_tip.lower()]
        self._populate_tweak_list()

    def ShowChoiceMenu(self, tweakIndex):
        """Displays a popup choice menu if applicable."""
        if tweakIndex >= len(self._curr_tweaks): return
        tweak = self._curr_tweaks[tweakIndex]
        choiceLabels = tweak.choiceLabels
        if len(choiceLabels) <= 1: return
        self.gTweakList.lb_select_index(tweakIndex)
        #--Build Menu
        links = Links()
        _self = self # ugly, tweak_custom_choice is too big to make it local though
        class _ValueLink(CheckLink):
            def __init__(self, _text, index):
                super(_ValueLink, self).__init__(_text)
                self.index = index
            def _check(self): return self.index == tweak.chosen
            def Execute(self): _self.tweak_choice(self.index, tweakIndex)
        class _ValueLinkCustom(_ValueLink):
            def Execute(self):
                _self.tweak_custom_choice(self.index, tweakIndex)
        for index, itm_txt in enumerate(choiceLabels):
            if itm_txt == '----':
                links.append_link(SeparatorLink())
            elif itm_txt == tweak.custom_choice:
                itm_txt = _custom_label(itm_txt, tweak.choiceValues[index][0])
                links.append_link(_ValueLinkCustom(itm_txt, index))
            else:
                links.append_link(_ValueLink(itm_txt, index))
        #--Show/Destroy Menu
        links.popup_menu(self.gTweakList, None)

    def tweak_choice(self, index, tweakIndex):
        """Handle choice menu selection."""
        self._curr_tweaks[tweakIndex].chosen = index
        self.gTweakList.lb_set_label_at_index(
            tweakIndex, self._curr_tweaks[tweakIndex].getListLabel())
        self.gTweakList.lb_check_at_index(tweakIndex, True)
        # wx.EVT_CHECKLISTBOX is NOT fired so this line is needed (?)
        self.TweakOnListCheck()

    def tweak_custom_choice(self, index, tweakIndex):
        """Handle choice menu selection."""
        tweak = self._curr_tweaks[tweakIndex]
        values = []
        new = None
        # Check the default values since the type of values accepted by the
        # tweak could have changed and so old custom values may have the wrong
        # type now
        for i, v in enumerate(tweak.choiceValues[tweak.default]):
            if tweak.show_key_for_custom:
                ##: Mirrors chosen_eids, but all this is hacky - we should
                # enforce that keys for settings tweaks *must* be tuples and
                # then get rid of this
                key_display = tweak.tweak_key[i] if isinstance(
                    tweak.tweak_key, tuple) else tweak.tweak_key
                default_tweak_fmt = ' ' + _('(Default: %(default_tweak_val)s)')
            else:
                key_display = ''
                default_tweak_fmt = _('Default: %(default_tweak_val)s')
            default_tweak_fmt %= {'default_tweak_val': v}
            if isinstance(v, float):
                msg = (
                    f'{_("Enter the desired custom tweak value.")}\n\n'
                    f'{_("Note: A floating point number is expected here.")}'
                    f'\n\n{key_display}{default_tweak_fmt}'
                )
                while new is None: # keep going until user entered valid float
                    new = askText(self, msg, title=_(
                        '%(tweak_title)s - Custom Tweak Value') % {
                            'tweak_title': tweak.tweak_name},
                        default_txt=str(tweak.choiceValues[index][i]))
                    if new is None: #user hit cancel
                        return
                    try:
                        values.append(float(new))
                        new = None # Reset, we may have a multi-key tweak
                        break
                    except ValueError:
                        msg = _("'%(invalid_float)s' is not a valid floating "
                                "point number.") % {'invalid_float': new}
                        showError(self, msg, title=_('%(tweak_title)s - Error'
                                    ) % {'tweak_title': tweak.tweak_name})
                        new = None # invalid float, try again
            elif isinstance(v, int):
                msg = (f"{_('Enter the desired custom tweak value.')}\n\n"
                       f"{key_display}{default_tweak_fmt}")
                new = askNumber(self, msg, prompt=_('Value'), title=_(
                    '%(tweak_title)s - Custom Tweak Value') % {
                        'tweak_title': tweak.tweak_name},
                    initial_num=tweak.choiceValues[index][i], min_num=-10000,
                    max_num=10000)
                if new is None: #user hit cancel
                    return
                values.append(new)
            elif isinstance(v, str):
                msg = (f"{_('Enter the desired custom tweak text.')}\n\n"
                       f"{key_display}{default_tweak_fmt}")
                # Don't strip - at least for Tweak Names, custom choices with
                # trailing whitespace are necessary (e.g. consider a custom
                # choice '%s* ', which renames 'Fireball' to 'D* Fireball')
                new = askText(self, msg, title=_(
                    '%(tweak_title)s - Custom Tweak Text') % {
                        'tweak_title': tweak.tweak_name},
                    default_txt=tweak.choiceValues[index][i], strip=False)
                if new is None: #user hit cancel
                    return
                values.append(new)
        if not values:
            values = tweak.choiceValues[index]
        values = tuple(values)
        validation_error = tweak.validate_values(values)
        if validation_error is None: # no error, we're good to go
            tweak.choiceValues[index] = values
            tweak.chosen = index
            custom_label = _custom_label(tweak.getListLabel(), values[0])
            self.gTweakList.lb_set_label_at_index(tweakIndex, custom_label)
            self.gTweakList.lb_check_at_index(tweakIndex, True)
            self.TweakOnListCheck() # fired so this line is needed (?)
        else:
            # The tweak doesn't like the values the user chose, let them know
            error_header = tweak.validation_error_header(values) + '\n\n'
            showError(self, error_header + validation_error, title=_(
                '%(tweak_title)s - Error') % {'tweak_title': tweak.tweak_name})

    def mass_select(self, select=True):
        """'Select All' or 'Deselect All' button was pressed, update all
        configChecks states."""
        self.gTweakList.set_all_checkmarks(checked=select)
        self.TweakOnListCheck()
        super().mass_select(select)

    # Config phase overrides
    def import_config(self, *args):
        super().import_config(*args)
        # Reset the search bar, this will call _handle_tweak_search
        self._tweak_search.text_content = ''
        for index, tweakie in enumerate(self._all_tweaks):
            try:
                self.gTweakList.lb_check_at_index(index, tweakie.isEnabled)
                self.gTweakList.lb_set_label_at_index(index, tweakie.getListLabel())
            except KeyError: pass # no such key don't spam the log
            except: bolt.deprint('Error importing Bashed Patch configuration. '
                                 f'Item {tweakie} skipped.', traceback=True)

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

class _ImporterPatcherPanel(_ImporterPatcherConfig, _ListPatcherPanel): pass

class _ListMergerConfig(ListPatcherConfig):
    patcher_type: ClassVar[type[mergers.AListsMerger]]

    def _merge_configs(self, conf_checks, present_config_items):
        return {k: v for k, v in {**conf_checks, **forward_compat_path_to_fn(
            self.configChoices)}.items() if k in present_config_items}

    @classmethod
    def _config_attrs(cls):
        return *super()._config_attrs(), ('autoIsChecked', True)

    @classmethod
    def _log_config(cls, conf, config, clip, log):
        conf_choices = conf.get('configChoices', {})
        for item in (cls._mod_label(i, conf_choices) for i in conf.get(
                'configItems', [])):
            log(f'. __{item}__')
            clip.write(f'    {item}\n')

    @classmethod
    def _mod_label(cls, item, conf_choices):
        return cls.patcher_type.annotate_plugin(item, conf_choices)

class _ListsMergerPanel(_ListMergerConfig,_ChoiceMenuMixin, _ListPatcherPanel):
    """Mergers targeting all mods in the LO, with the option to override
    tags."""
    choiceMenu: ClassVar[tuple[str, ...]]
    _add_dialog_title: str
    # CONFIG DEFAULTS
    selectCommands = False
    _item_config: dict[FName, set[str]]

    def native_init(self, *args, **kwargs):
        if freshly_created := super().native_init(*args, **kwargs):
            self._bind_mouse_events(self.gList)
        return freshly_created

    def _auto_layout(self, right_side_components=None):
        right_side_components = right_side_components or []
        self._add_rem_bt = [Button(self, _('Add'), on_click=self._on_add),
                            Button(self, _('Remove'), on_click=self._on_rem)]
        right_side_components.extend([CheckBox(self, _('Automatic'),
            checked=self.autoIsChecked, on_check=self._on_auto_check),
            Spacer(4), *self._add_rem_bt])
        self._sort_and_update_items( # will also call _update_manual_buttons
            self.autoIsChecked)
        return VLayout(spacing=4, items=right_side_components)

    def _set_choice(self, item):
        """Refresh mods that have an Auto choice set. We need to do this when
        we load a config, unlike super, as tags may have changed)."""
        if (config_choice := self._item_config.get(item)) is None:
            if not self._is_first_load:
                self._new_items.add(item)
            config_choice = {'Auto'}
        if 'Auto' in config_choice:
            tags = self._bp.all_tags.get(item, set())
            config_choice = {'Auto', *(self.patcher_type.patcher_tags & tags)}
        self._item_config[item] = config_choice
        return config_choice

    def _on_auto_check(self, is_checked):
        """Automatic checkbox changed."""
        self.autoIsChecked = is_checked
        if self.autoIsChecked:
            self._sort_and_update_items()
        else: # In autoIsChecked case, this is called by _handle_item_search
            self._update_manual_buttons(not self._item_search.text_content)

    def _handle_item_search(self, search_str):
        super()._handle_item_search(search_str)
        self._update_manual_buttons(
            not (self.autoIsChecked or self._item_search.text_content))

    def _update_manual_buttons(self, btns_enabled):
        """Helper that enables or disables the add/remove buttons based on
        internal state."""
        for butt in self._add_rem_bt: butt.enabled = btns_enabled

    def get_patcher_instance(self, patch_file, rem_emp=False):
        patcher_sources = self._get_list_patcher_srcs()
        return self.patcher_type(self.patcher_name, patch_file,
            patcher_sources, rem_emp, defaultdict(set, self._item_config))

    def _on_add(self):
        ds = bosh.modInfos
        srcDir = ds.store_dir
        wildcard = ds.unhide_wildcard()
        #--File dialog
        srcPaths = FileOpenMultiple.display_dialog(self,
            self._add_dialog_title, srcDir, '', wildcard)
        if not srcPaths: return
        #--Get new items
        for srcPath in srcPaths:
            if srcPath.head == srcDir and (body_ext := ds.check_filename(
                    srcPath.stail)): # we need check_filename for ghosts!
                if (fn := FName(''.join(body_ext))) in self._bp.all_plugins \
                    and self._bp.all_tags[fn] & self.patcher_type.patcher_tags:
                    self._set_choice(fn)
        self._sort_and_update_items(is_auto=False)

    def _on_rem(self):
        """Remove button clicked."""
        selections = self.gList.lb_get_selections()
        self._item_config = dict(item for index, item in enumerate(
            self._item_config.items()) if index not in selections)
        self._sort_and_update_items(is_auto=False, do_sort=False)

    def ShowChoiceMenu(self, itemIndex):
        """Displays a popup choice menu if applicable.
        NOTE: Assume that configChoice returns a set of chosen items."""
        #--Item Index
        if itemIndex < 0: return
        (gui_li := self.gList).lb_select_index(itemIndex)
        choiceSet = self._item_config[(curr := self._curr_items)[itemIndex]]
        #--Build Menu
        choices, choice_menu, _self = self._item_config, self.choiceMenu, self
        class _OnItemChoice(CheckLink):
            def __init__(self, _text, dex):
                super(_OnItemChoice, self).__init__(_text)
                self._index = dex
            def _check(self): return self._text in choiceSet
            def Execute(self):
                item = curr[itemIndex]
                choice_set = choices[item]
                choice_set ^= {choice := choice_menu[self._index]}
                if choice != 'Auto':
                    choice_set.discard('Auto')
                elif 'Auto' in choice_set:
                    _self._set_choice(item)
                gui_li.lb_set_label_at_index(itemIndex, _self._mod_label(
                    item, choices))
        links = Links()
        for index, item_label in enumerate(choice_menu):
            links.append_link(SeparatorLink() if item_label == '----' else
                              _OnItemChoice(item_label, index))
        #--Show/Destroy Menu
        links.popup_menu(gui_li, None)

    # Config Phase Overrides
    def _getConfig(self, configs):
        config = super()._getConfig(configs)
        for item in self._item_config:
            self._set_choice(item) # see docs in self._set_choice
        return config

    def import_config(self, *args):
        super(_ListPatcherPanel, self).import_config(*args) # bypass super!
        self._on_auto_check(self.autoIsChecked)

    def _style_patcher_label(self, bold=False, italics=False):
        # Never italicize these since they will run even if there are no tagged
        # source plugins
        super(_ListsMergerPanel, self)._style_patcher_label(bold=bold)

#------------------------------------------------------------------------------
# GUI Patcher classes
# Do _not_ change the _config_key attr or you will break existing BP configs
#------------------------------------------------------------------------------
# Patchers 10 -----------------------------------------------------------------
class AliasPluginNames(_AliasesPatcherPanel): pass

class MergePatches(_ListPatcherPanel):
    """Merges specified patches into Bashed Patch."""
    listLabel = _('Mergeable Plugins')
    patcher_name = _(u'Merge Patches')
    patcher_desc = _('Merge patch plugins into the Bashed Patch.')
    _config_key = u'PatchMerger'
    patcher_type = MergePatchesPatcher

# Patchers 20 -----------------------------------------------------------------
class ImportGraphics(_ImporterPatcherPanel):
    """Merges changes to graphics (models and icons)."""
    patcher_name = _(u'Import Graphics')
    patcher_desc = _('Import graphics (models, icons, etc.) from source '
                     'plugins.')
    _config_key = u'GraphicsPatcher'
    patcher_type = preservers.ImportGraphicsPatcher

# -----------------------------------------------------------------------------
class ImportActorsAIPackages(_ImporterPatcherPanel):
    """Merges changes to the AI Packages of Actors."""
    patcher_name = _(u'Import Actors: AI Packages')
    patcher_desc = _('Import actor AI Package links from source plugins.')
    _config_key = u'NPCAIPackagePatcher'
    patcher_type = mergers.ImportActorsAIPackagesPatcher

# -----------------------------------------------------------------------------
class ImportActors(_ImporterPatcherPanel):
    """Merges changes to actors."""
    patcher_name = _(u'Import Actors')
    patcher_desc = _('Import various actor attributes from source plugins.')
    _config_key = u'ActorImporter'
    patcher_type = preservers.ImportActorsPatcher

# -----------------------------------------------------------------------------
class ImportActorsPerks(_ImporterPatcherPanel):
    """Merges changes to actor perks."""
    patcher_name = _(u'Import Actors: Perks')
    patcher_desc = _('Import actor perks from source plugins.')
    _config_key = u'ImportActorsPerks'
    patcher_type = mergers.ImportActorsPerksPatcher

# -----------------------------------------------------------------------------
class ImportCells(_ImporterPatcherPanel):
    """Merges changes to cells (climate, lighting, and water.)"""
    patcher_name = _(u'Import Cells')
    patcher_desc = _('Import cells (climate, lighting, and water) from '
                     'source plugins.')
    _config_key = u'CellImporter'
    patcher_type = preservers.ImportCellsPatcher

# -----------------------------------------------------------------------------
class ImportActorsFactions(_ImporterPatcherPanel):
    """Import factions to creatures and NPCs."""
    patcher_name = _(u'Import Actors: Factions')
    patcher_desc = _('Import actor factions from source plugins/files.')
    _config_key = u'ImportFactions'
    patcher_type = preservers.ImportActorsFactionsPatcher

# -----------------------------------------------------------------------------
class ImportRelations(_ImporterPatcherPanel):
    """Import faction relations to factions."""
    patcher_name = _(u'Import Relations')
    patcher_desc = _('Import relations from source plugins/files.')
    _config_key = u'ImportRelations'
    patcher_type = mergers.ImportRelationsPatcher

# -----------------------------------------------------------------------------
class ImportInventory(_ImporterPatcherPanel):
    """Merge changes to actor inventories."""
    patcher_name = _('Import Inventory')
    patcher_desc = _('Merges changes to items in various inventories.')
    _config_key = 'ImportInventory'
    patcher_type = mergers.ImportInventoryPatcher

# -----------------------------------------------------------------------------
class ImportOutfits(_ImporterPatcherPanel):
    """Merge changes to outfits."""
    patcher_name = _(u'Import Outfits')
    patcher_desc = _(u'Merges changes to NPC outfits.')
    _config_key = u'ImportOutfits'
    patcher_type = mergers.ImportOutfitsPatcher

# -----------------------------------------------------------------------------
class ImportActorsSpells(_ImporterPatcherPanel):
    """Merges changes to the spells lists of Actors."""
    patcher_name = _(u'Import Actors: Spells')
    patcher_desc = _(u'Merges changes to actor spell / effect lists.')
    _config_key = u'ImportActorsSpells'
    patcher_type = mergers.ImportActorsSpellsPatcher

# -----------------------------------------------------------------------------
class ImportNames(_ImporterPatcherPanel):
    """Import names from sources."""
    patcher_name = _(u'Import Names')
    patcher_desc = _('Import names from source plugins/files.')
    _config_key = u'NamesPatcher'
    patcher_type = preservers.ImportNamesPatcher

# -----------------------------------------------------------------------------
class ImportActorsFaces(_ImporterPatcherPanel):
    """NPC Faces patcher, for use with TNR or similar plugins."""
    patcher_name = _(u'Import Actors: Faces')
    patcher_desc = _('Import NPC face/eyes/hair from source plugins. For use '
                     'with TNR and similar mods.')
    _config_key = u'NpcFacePatcher'
    patcher_type = preservers.ImportActorsFacesPatcher

# -----------------------------------------------------------------------------
class ImportSounds(_ImporterPatcherPanel):
    """Imports sounds from source plugins into patch."""
    patcher_name = _(u'Import Sounds')
    patcher_desc = _('Import sounds (from Magic Effects, Containers, '
                     'Activators, Lights, Weathers and Doors) from source '
                     'plugins.')
    _config_key = u'SoundPatcher'
    patcher_type = preservers.ImportSoundsPatcher

# -----------------------------------------------------------------------------
class ImportStats(_ImporterPatcherPanel):
    """Import stats from mod file."""
    patcher_name = _(u'Import Stats')
    patcher_desc = _('Import stats from any pickupable items from source '
                     'plugins/files.')
    _config_key = u'StatsPatcher'
    patcher_type = preservers.ImportStatsPatcher

# -----------------------------------------------------------------------------
class ImportScripts(_ImporterPatcherPanel):
    """Imports attached scripts on objects."""
    patcher_name = _(u'Import Scripts')
    patcher_desc = _('Import scripts on various objects (e.g. containers, '
                     'weapons, etc.) from source plugins.')
    _config_key = u'ImportScripts'
    patcher_type = preservers.ImportScriptsPatcher

# -----------------------------------------------------------------------------
class ImportRaces(_ImporterPatcherPanel):
    """Imports race-related data."""
    patcher_name = _(u'Import Races')
    patcher_desc = _('Import race eyes, hair, body, voice, etc. from source '
                     'plugins.')
    _config_key = u'ImportRaces'
    patcher_type = preservers.ImportRacesPatcher

# -----------------------------------------------------------------------------
class ImportRacesRelations(_ImporterPatcherPanel):
    """Imports race-faction relations."""
    patcher_name = _(u'Import Races: Relations')
    patcher_desc = _('Import race-faction relations from source plugins.')
    _config_key = u'ImportRacesRelations'
    patcher_type = mergers.ImportRacesRelationsPatcher

# -----------------------------------------------------------------------------
class ImportRacesSpells(_ImporterPatcherPanel):
    """Imports race spells/abilities."""
    patcher_name = _(u'Import Races: Spells')
    patcher_desc = _('Import race abilities and spells from source plugins.')
    _config_key = u'ImportRacesSpells'
    patcher_type = mergers.ImportRacesSpellsPatcher

# -----------------------------------------------------------------------------
class ImportSpellStats(_ImporterPatcherPanel):
    """Import spell changes from mod files."""
    patcher_name = _(u'Import Spell Stats')
    patcher_desc = _('Import stats from spells from source plugins/files.')
    _config_key = u'SpellsPatcher'
    patcher_type = preservers.ImportSpellStatsPatcher

# -----------------------------------------------------------------------------
class ImportDestructible(_ImporterPatcherPanel):
    patcher_name = _('Import Destructible')
    patcher_desc = _('Preserves changes to destructible records.')
    _config_key = 'DestructiblePatcher'
    patcher_type = preservers.ImportDestructiblePatcher

# -----------------------------------------------------------------------------
class ImportKeywords(_ImporterPatcherPanel):
    patcher_name = _(u'Import Keywords')
    patcher_desc = _('Import keyword changes from source plugins.')
    _config_key = u'KeywordsImporter'
    patcher_type = preservers.ImportKeywordsPatcher

# -----------------------------------------------------------------------------
class ImportText(_ImporterPatcherPanel):
    patcher_name = _(u'Import Text')
    patcher_desc = _('Import various types of long-form text like book '
                     'texts, effect descriptions, etc. from source plugins.')
    _config_key = u'TextImporter'
    patcher_type = preservers.ImportTextPatcher

# -----------------------------------------------------------------------------
class ImportObjectBounds(_ImporterPatcherPanel):
    patcher_name = _(u'Import Object Bounds')
    patcher_desc = _(u'Import object bounds for various actors, items and '
                     u'objects.')
    _config_key = u'ObjectBoundsImporter'
    patcher_type = preservers.ImportObjectBoundsPatcher

# -----------------------------------------------------------------------------
class ImportEnchantmentStats(_ImporterPatcherPanel):
    patcher_name = _(u'Import Enchantment Stats')
    patcher_desc = _('Import stats from enchantments from source plugins.')
    _config_key = u'ImportEnchantmentStats'
    patcher_type = preservers.ImportEnchantmentStatsPatcher

# -----------------------------------------------------------------------------
class ImportEffectStats(_ImporterPatcherPanel):
    patcher_name = _('Import Effect Stats')
    patcher_desc = _('Import stats from magic/base effects from source '
                     'plugins.')
    _config_key = 'ImportEffectsStats'
    patcher_type = preservers.ImportEffectStatsPatcher

# -----------------------------------------------------------------------------
class ImportEnchantments(_ImporterPatcherPanel):
    patcher_name = _('Import Enchantments')
    patcher_desc = _('Import enchantments from armor, weapons, etc. from '
                     'source plugins.')
    _config_key = 'ImportEnchantments'
    patcher_type = preservers.ImportEnchantmentsPatcher

# Patchers 30 -----------------------------------------------------------------
class TweakAssorted(_TweakPatcherPanel):
    patcher_name = _(u'Tweak Assorted')
    patcher_desc = _(u'Tweak various records in miscellaneous ways.')
    _config_key = u'AssortedTweaker'
    patcher_type = multitweak_assorted.TweakAssortedPatcher
    default_isEnabled = True

# -----------------------------------------------------------------------------
class TweakClothes(_TweakPatcherPanel):
    patcher_name = _(u'Tweak Clothes')
    patcher_desc = _(u'Tweak clothing weight and blocking.')
    _config_key = u'ClothesTweaker'
    patcher_type = multitweak_clothes.TweakClothesPatcher

# -----------------------------------------------------------------------------
class TweakSettings(_TweakPatcherPanel):
    patcher_name = _(u'Tweak Settings')
    patcher_desc = _(u'Tweak game settings.')
    _config_key = u'GmstTweaker'
    patcher_type = multitweak_settings.TweakSettingsPatcher
    # CONFIG DEFAULTS
    default_isEnabled = True

# -----------------------------------------------------------------------------
class TweakNames(_TweakPatcherPanel):
    patcher_name = _(u'Tweak Names')
    patcher_desc = _(u'Tweak object names to sort them by type/stats or to '
                     u'improve things like lore friendliness.')
    _config_key = u'NamesTweaker'
    patcher_type = multitweak_names.TweakNamesPatcher

# -----------------------------------------------------------------------------
class TweakActors(_TweakPatcherPanel):
    patcher_name = _(u'Tweak Actors')
    patcher_desc = _(u'Tweak NPC and Creatures records in specified ways.')
    _config_key = u'TweakActors'
    patcher_type = multitweak_actors.TweakActorsPatcher

# -----------------------------------------------------------------------------
class TweakRaces(_TweakPatcherPanel):
    patcher_name = _(u'Tweak Races')
    patcher_desc = _(u'Tweak race records in specified ways.')
    _config_key = u'TweakRaces'
    patcher_type = multitweak_races.TweakRacesPatcher

# Patchers 40 -----------------------------------------------------------------
class ReplaceFormIDs(_ListPatcherPanel):
    """Imports Form Id replacers into the Bashed Patch."""
    patcher_name = _(u'Replace Form IDs')
    patcher_desc = _(u'Imports Form Id replacers from csv files into the '
                     u'Bashed Patch.')
    _config_key = u'UpdateReferences'
    patcher_type = ReplaceFormIDsPatcher
    _autocheck_new = False #--GUI: Whether new items are checked by default.

# -----------------------------------------------------------------------------
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

class LeveledLists(LeveledListsConfig, _ListsMergerPanel):
    listLabel = _('Override Delev/Relev Tags')
    _add_dialog_title = _('Add Delev/Relev Tags to Plugin')
    choiceMenu = ('Auto', '----', 'Delev', 'Relev')

    def _auto_layout(self, right_side_components=None):
        return super()._auto_layout([CheckBox(self, _('Remove Empty Sublists'),
            checked=self.remove_empty_sublists,
            on_check=self._on_remove_empty_checked)])

    def _on_remove_empty_checked(self, is_checked):
        self.remove_empty_sublists = is_checked

    def _get_glist(self):
        self.gList = ListBox(self, isSingle=False)

    def _check_item(self, item, index):
        return False

class FormIDLists(_ListsMergerPanel): # Fallout3/FalloutNV only
    patcher_name = _('FormID Lists')
    patcher_desc = '\n\n'.join([
        _('Merges changes to FormID lists from all active and/or merged '
          'plugins.'),
        _('Advanced users may override Deflst tags for any mod (active or '
          'inactive) using the list below.')])
    _config_key = 'FidListsMerger'
    patcher_type = mergers.FormIDListsPatcher
    listLabel = _('Override Deflst Tag')
    _add_dialog_title = _('Add Deflst Tag to Plugin')
    choiceMenu = ('Auto', '----', 'Deflst')

# -----------------------------------------------------------------------------
class ContentsChecker(PatcherConfig, _PatcherPanel):
    """Checks contents of leveled lists, inventories and containers for
    correct content types."""
    patcher_name = _('Contents Checker')
    patcher_desc = _(u'Checks contents of leveled lists, inventories and '
                     u'containers for correct types.')
    _config_key = u'ContentsChecker'
    patcher_type = checkers.ContentsCheckerPatcher
    default_isEnabled = True

# -----------------------------------------------------------------------------
class RaceChecker(PatcherConfig, _PatcherPanel):
    """Sorts hairs and eyes."""
    patcher_name = _(u'Race Checker')
    patcher_desc = _(u'Sorts race hairs and eyes.')
    _config_key = u'RaceChecker'
    patcher_type = checkers.RaceCheckerPatcher
    default_isEnabled = True

#------------------------------------------------------------------------------
class NpcChecker(PatcherConfig, _PatcherPanel):
    """Assigns missing hair and eyes."""
    patcher_name = _(u'NPC Checker')
    patcher_desc = _(u'This will randomly assign hairs and eyes to NPCs that '
                     u'are otherwise missing them.')
    _config_key = u'NpcChecker'
    patcher_type = checkers.NpcCheckerPatcher
    default_isEnabled = True

#------------------------------------------------------------------------------
class TimescaleChecker(PatcherConfig, _PatcherPanel):
    """Adjusts the wave period of grass match changes in the timescale."""
    patcher_name = _(u'Timescale Checker')
    patcher_desc = u'\n'.join([
        _(u'Adjusts the wave period of grasses to match changes in the '
          u'timescale.'),
        _(u'Does nothing if you are not using a nonstandard timescale.'),
        u'',
        _(u'Incompatible with plugins that change grass wave periods to match '
          u'a different timescale. Uninstall such plugins before using this.'),
    ])
    _config_key = u'TimescaleChecker'
    patcher_type = checkers.TimescaleCheckerPatcher
    default_isEnabled = True

#------------------------------------------------------------------------------
# Game specific GUI Patchers --------------------------------------------------
#------------------------------------------------------------------------------
# Patchers with no options
for gsp_name, gsp_class in bush.game.gameSpecificPatchers.items():
    globals()[gsp_name] = type(gsp_name, (PatcherConfig, _PatcherPanel,),
        gsp_class.gui_cls_vars())
# Simple list patchers
for gsp_name, gsp_class in bush.game.gameSpecificListPatchers.items():
    gsp_bases = (_ListPatcherPanel,)
    globals()[gsp_name] = type(gsp_name, gsp_bases, gsp_class.gui_cls_vars())
# Import patchers
for gsp_name, gsp_class in bush.game.game_specific_import_patchers.items():
    gsp_bases = (_ImporterPatcherPanel,)
    globals()[gsp_name] = type(gsp_name, gsp_bases, gsp_class.gui_cls_vars())

def initPatchers():
    group_order = {p_grp: i for i, p_grp in enumerate(
        ('General', 'Importers', 'Tweakers', 'Special'))}
    # If we want to merge patches into the BP, we need the patch merger
    final_patchers = bush.game.patchers.copy()
    if MergeabilityCheck.MERGE in bush.game.mergeability_checks:
        final_patchers.add('MergePatches')
        # And the NoMerge tag needs to get added too
        bush.game.allTags.add('NoMerge')
    patcher_classes = [globals()[p] for p in final_patchers]
    # Sort alphabetically first for aesthetic reasons
    patcher_classes.sort(key=lambda a: a.patcher_name)
    # After that, sort by group to make patchers instantiate in the right order
    patcher_classes.sort(
        key=lambda a: group_order[a.patcher_type.patcher_group])
    gpatcher_types.extend(patcher_classes)
    # Update the set of all tags for this game based on the available patchers
    bush.game.allTags.update(chain.from_iterable(
        getattr(p.patcher_type, 'patcher_tags', ()) for p in gpatcher_types))
