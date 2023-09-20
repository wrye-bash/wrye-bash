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
from __future__ import annotations

import re
from collections import defaultdict
from itertools import chain

from .patcher_dialog import PatchDialog, all_gui_patchers
from .. import bass, bolt, bosh, bush, load_order
from ..balt import CheckLink, Links, SeparatorLink
from ..bolt import FName, dict_sort, forward_compat_path_to_fn, \
    forward_compat_path_to_fn_list, text_wrap
from ..gui import TOP, Button, CheckBox, CheckListBox, DeselectAllButton, \
    EventResult, FileOpenMultiple, HBoxedLayout, Label, LayoutOptions, \
    ListBox, PanelWin, SearchBar, SelectAllButton, Spacer, TextArea, VLayout, \
    askText, showError, askNumber
from ..patcher.base import APatcher, MultiTweakItem, ListPatcher
from ..patcher.patchers import checkers, mergers, multitweak_actors, \
    multitweak_assorted, multitweak_clothes, multitweak_names, \
    multitweak_races, multitweak_settings, preservers
from ..patcher.patchers.base import AliasPluginNamesPatcher, \
    MergePatchesPatcher, MultiTweaker, ReplaceFormIDsPatcher

class _PatcherPanel(object):
    """Basic patcher panel with no options."""
    patcher_name = u'UNDEFINED'
    patcher_desc = u'UNDEFINED'
    # The key that will be used to read and write entries for BP configs
    # These are sometimes quite ugly - backwards compat leftover from when
    # those were the class names and got written directly into the configs
    _config_key: str = None
    patcher_type: APatcher = None
    # CONFIG DEFAULTS
    default_isEnabled = False # is the patcher enabled on a new bashed patch ?
    selectCommands = True # whether this panel displays De/Select All

    def __init__(self): # WIP- investigate why we instantiate gui patchers once
        if not self.__class__._config_key:
            raise SyntaxError(f'No _config_key set for patcher panel class '
                              f'{self.__class__.__name__}')
        self.gConfigPanel = None
        # Used to keep track of the state of the patcher label
        self._is_bolded = False
        self._is_italicized = False
        # executing bashed patch file, use only for info on active mod arrays
        self._bp = None

    @property
    def patcher_tip(self):
        # Remove everything but the first sentence from the first line of the
        # patcher description
        return re.sub(r'\..*', '.', self.patcher_desc.split('\n')[0])

    def _enable_self(self, self_enabled=True):
        """Enables or disables this patcher and notifies the patcher dialog."""
        self.isEnabled = self_enabled
        self.patch_dialog.check_patcher(self, self_enabled)

    def _style_patcher_label(self, bold=False, italics=False):
        self._is_bolded |= bold
        self._is_italicized |= italics
        self.patch_dialog.style_patcher(self, bold=self._is_bolded,
                                        italics=self._is_italicized)

    def _GetIsFirstLoad(self):
        return getattr(self, u'is_first_load', False)

    def GetConfigPanel(self, parent: PatchDialog, config_layout, gTipText):
        """Show config."""
        if self.gConfigPanel: return self.gConfigPanel
        self.patch_dialog = parent
        self.gTipText = gTipText
        self.gConfigPanel = PanelWin(parent, no_border=False)
        self.main_layout = VLayout(
            item_expand=True, item_weight=1, spacing=4, items=[
                (Label(self.gConfigPanel, text_wrap(self.patcher_desc, 70)),
                 LayoutOptions(weight=0))])
        self.main_layout.apply_to(self.gConfigPanel)
        config_layout.add(self.gConfigPanel)
        # Bold the patcher if it's new, but the patch itself isn't new
        if not self._was_present and not self._GetIsFirstLoad():
            self._style_patcher_label(bold=True)
        return self.gConfigPanel

    def Layout(self):
        """Layout control components."""
        if self.gConfigPanel:
            self.gConfigPanel.update_layout()

    def _set_focus(self): # TODO(ut) check if set_focus is enough
        self.patch_dialog.gPatchers.set_focus_from_kb()

    #--Config Phase -----------------------------------------------------------
    def _getConfig(self, configs):
        """Get config from configs dictionary and/or set to default.

        Called in basher.patcher_dialog.PatchDialog#__init__, before the
        dialog is shown, to update the patch options based on the previous
        config for this patch stored in modInfos.table[patch][
        'bash.patch.configs']. If no config is saved then the class
        default_XXX values are used for the relevant attributes."""
        # Remember whether we were present in the config for bolding later
        self._was_present = self.__class__._config_key in configs
        config = (configs[self.__class__._config_key]
                  if self._was_present else {})
        self.isEnabled = config.get(u'isEnabled',
                                    self.__class__.default_isEnabled)
        # return the config dict for this patcher to read additional values
        return config

    def saveConfig(self, configs):
        """Save config to configs dictionary.

        Most patchers just save their enabled state, except the
        _ListPatcherPanel subclasses - which save their choices - and the
        AliasPluginNames that saves the aliases."""
        config = configs[self.__class__._config_key] = {}
        config[u'isEnabled'] = self.isEnabled
        return config # return the config dict for this patcher to further edit

    def log_config(self, config, clip, log):
        ckey = self.__class__._config_key
        # Check if the patcher is in the config and was enabled
        if ckey not in config or not (conf := config[ckey]).get('isEnabled'):
            return
        humanName = self.__class__.patcher_name
        log.setHeader(u'== ' + humanName)
        clip.write(u'\n')
        clip.write(u'== ' + humanName + u'\n')
        self._log_config(conf, config, clip, log)

    def _log_config(self, conf, config, clip, log):
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

    def import_config(self, patchConfigs, set_first_load=False, default=False,
                      _decouple=False):
        self.is_first_load = set_first_load
        self._getConfig(patchConfigs) # set isEnabled and load additional config
        if not _decouple: self._import_config(default)

    def _import_config(self, default=False): pass

    def mass_select(self, select=True):
        self._enable_self(select)
        self._set_focus()

    def get_patcher_instance(self, patch_file):
        """Instantiate and return an instance of self.__class__.patcher_type,
        initialized with the config options from the Gui"""
        return self.patcher_type(self.patcher_name, patch_file)

#------------------------------------------------------------------------------
class _AliasesPatcherPanel(_PatcherPanel):
    patcher_name = _('Alias Plugin Names')
    patcher_desc = _('Specify plugin aliases for reading CSV source files.')

    def GetConfigPanel(self, parent: PatchDialog, config_layout, gTipText):
        """Show config."""
        if self.gConfigPanel: return self.gConfigPanel
        gConfigPanel = super().GetConfigPanel(parent, config_layout, gTipText)
        #gExample = Label(gConfigPanel,
        #    _(u"Example Mod 1.esp >> Example Mod 1.2.esp"))
        #--Aliases Text
        self.gAliases = TextArea(gConfigPanel)
        self.gAliases.on_focus_lost.subscribe(self.OnEditAliases)
        self.SetAliasText()
        #--Sizing
        self.main_layout.add((self.gAliases,
                              LayoutOptions(expand=True, weight=1)))
        return self.gConfigPanel

    def SetAliasText(self):
        """Sets alias text according to current aliases."""
        self.gAliases.text_content = u'\n'.join([
            f'{alias_target} >> {alias_repl}'
            for alias_target, alias_repl in dict_sort(self._fn_aliases)])

    def OnEditAliases(self):
        aliases_text = self.gAliases.text_content
        self._fn_aliases.clear()
        for line in aliases_text.split(u'\n'):
            fields = [s.strip() for s in line.split(u'>>')]
            if len(fields) != 2 or not fields[0] or not fields[1]: continue
            self._fn_aliases[fields[0]] = FName(fields[1])
        self.SetAliasText()

    #--Config Phase -----------------------------------------------------------
    def _getConfig(self, configs):
        """Get config from configs dictionary and/or set to default."""
        config = super()._getConfig(configs)
        #--Update old configs to use Paths instead of strings.
        # call str twice in case v._s was a str subtype
        self._fn_aliases = forward_compat_path_to_fn(config.get('aliases', {}),
            value_type=lambda v: FName(str('%s' % v)))
        return config

    def saveConfig(self, configs):
        """Save config to configs dictionary."""
        config = super(_AliasesPatcherPanel, self).saveConfig(configs)
        config[u'aliases'] = self._fn_aliases
        return config

    def _log_config(self, conf, config, clip, log):
        aliases = config.get(u'aliases', {})
        for mod, alias in aliases.items():
            log(f'* __{mod}__ >> {alias}')
            clip.write(f'  {mod} >> {alias}\n')

    def get_patcher_instance(self, patch_file):
        """Set patch_file aliases dict"""
        if self.isEnabled:
            patch_file.pfile_aliases = self._fn_aliases
        return self.patcher_type(self.patcher_name, patch_file)

#------------------------------------------------------------------------------
##: A lot of this belongs into _ListsMergerPanel (e.g. the whole GetConfigPanel
# split, remove empty sublists, etc.). Would also put forceAuto and
# forceItemCheck to rest
class _ListPatcherPanel(_PatcherPanel):
    """Patcher panel with option to select source elements."""
    forceAuto = True
    forceItemCheck = False #--Force configChecked to True for all items
    canAutoItemCheck = True #--GUI: Whether new items are checked by default
    show_empty_sublist_checkbox = False
    # ADDITIONAL CONFIG DEFAULTS FOR LIST PATCHER
    ##: Hack, this should not use display_name
    default_remove_empty_sublists = bush.game.display_name == 'Oblivion'
    gList: ListBox | CheckListBox
    patcher_type: ListPatcher

    def __init__(self):
        super().__init__()
        self.configItems: list[FName] = []
        self.configChecks: dict[FName, bool] = {}
        self.configChoices: dict[FName, set[str]] = {}
        # List of items that are currently visible (according to the search)
        self._curr_items: list[FName] = []
        # Set of items that are new and hence need to remain bolded
        self._new_items: set[FName] = set()

    def _sort_and_update_items(self, unsorted_items):
        """Helper for LO-sorting items and updating the internal caches for
        them."""
        self.configItems = load_order.get_ordered(unsorted_items)
        # Clear the search bar - this will _handle_item_search, which will call
        # _populate_item_list in turn
        self._item_search.text_content = ''

    def GetConfigPanel(self, parent: PatchDialog, config_layout, gTipText):
        """Show config."""
        if self.gConfigPanel: return self.gConfigPanel
        gConfigPanel = super().GetConfigPanel(parent, config_layout, gTipText)
        self.forceItemCheck = self.__class__.forceItemCheck
        self.selectCommands = self.__class__.selectCommands
        if self.forceItemCheck:
            self.gList = ListBox(gConfigPanel, isSingle=False)
        else:
            self.gList = CheckListBox(gConfigPanel)
            self.gList.on_box_checked.subscribe(self.OnListCheck)
        self._item_search = SearchBar(gConfigPanel, hint=_('Search Sources'))
        self._item_search.on_text_changed.subscribe(self._handle_item_search)
        #--Manual controls
        if self.forceAuto:
            side_button_layout = None
            self._sort_and_update_items(self._get_auto_items())
        else:
            right_side_components = []
            if self.show_empty_sublist_checkbox:
                self.g_remove_empty = CheckBox(
                    gConfigPanel, _(u'Remove Empty Sublists'),
                    checked=self.remove_empty_sublists)
                self.g_remove_empty.on_checked.subscribe(
                    self._on_remove_empty_checked)
                right_side_components.append(self.g_remove_empty)
            self.gAuto = CheckBox(gConfigPanel, _(u'Automatic'),
                                  checked=self.autoIsChecked)
            self.gAuto.on_checked.subscribe(self.OnAutomatic)
            self.gAdd = Button(gConfigPanel, _(u'Add'))
            self.gAdd.on_clicked.subscribe(self.OnAdd)
            self.gRemove = Button(gConfigPanel, _(u'Remove'))
            self.gRemove.on_clicked.subscribe(self.OnRemove)
            right_side_components.extend([self.gAuto, Spacer(4), self.gAdd,
                                          self.gRemove])
            self.OnAutomatic(self.autoIsChecked)
            if not self.autoIsChecked:
                # Populating the list when autoIsChecked is handled by
                # OnAutomatic above
                self._sort_and_update_items(self.configItems)
            side_button_layout = VLayout(
                spacing=4, items=right_side_components)
        self.main_layout.add(
            (HBoxedLayout(gConfigPanel, title=self._list_label,
                          item_expand=True, spacing=4, items=[
                    (VLayout(spacing=4, item_expand=True, items=[
                        self._item_search,
                        (self.gList, LayoutOptions(weight=1)),
                    ]), LayoutOptions(weight=1)),
                    (side_button_layout, LayoutOptions(v_align=TOP)),
                    self._get_select_layout(),
                ]), LayoutOptions(expand=True, weight=1)))
        return gConfigPanel

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
        self._curr_items = [i for i in self.configItems if
                            lower_search_str in i.lower()]
        self._populate_item_list()
        if not self.forceAuto:
            self._update_manual_buttons()

    def _update_manual_buttons(self):
        """Helper that enables or disables the add/remove buttons based on
        internal state."""
        btns_enabled = not self.autoIsChecked and not bool(
            self._item_search.text_content)
        self.gAdd.enabled = btns_enabled
        self.gRemove.enabled = btns_enabled

    def _on_remove_empty_checked(self, is_checked):
        self.remove_empty_sublists = is_checked

    def _get_select_layout(self):
        if not self.selectCommands: return None
        self.gSelectAll = SelectAllButton(self.gConfigPanel,
            btn_tooltip=_('Activate all currently visible sources.'))
        self.gSelectAll.on_clicked.subscribe(lambda: self.mass_select(True))
        self.gDeselectAll = DeselectAllButton(self.gConfigPanel,
            btn_tooltip=_('Deactivate all currently visible sources.'))
        self.gDeselectAll.on_clicked.subscribe(lambda: self.mass_select(False))
        return VLayout(spacing=4, items=[self.gSelectAll, self.gDeselectAll])

    def _populate_item_list(self):
        """Populate the patcher's item list based on the currently searched for
        items."""
        with self.gList.pause_drawing():
            self._do_populate_item_list()

    def _do_populate_item_list(self):
        forceItemCheck = self.forceItemCheck
        defaultItemCheck = self.__class__.canAutoItemCheck and bass.inisettings[u'AutoItemCheck']
        self.gList.lb_clear()
        isFirstLoad = self._GetIsFirstLoad()
        patcherOn = False
        patcher_bold = False
        for index, item in enumerate(self._curr_items):
            itemLabel = self.getItemLabel(item)
            self.gList.lb_insert(itemLabel, index)
            if forceItemCheck:
                if self.configChecks.get(item) is None:
                    patcherOn = True
                self.configChecks[item] = True
            else:
                effectiveDefaultItemCheck = defaultItemCheck and not itemLabel.endswith(u'.csv')
                if self.configChecks.get(item) is None:
                    if effectiveDefaultItemCheck:
                        patcherOn = True
                    if not isFirstLoad:
                        # Indicate that this is a new item by bolding it and
                        # its parent patcher
                        self._new_items.add(item)
                        patcher_bold = True
                # Restore the bolded font for this item if it was new the first
                # time we populated the list
                if item in self._new_items:
                    self.gList.lb_style_font_at_index(index, bold=True)
                self.gList.lb_check_at_index(index,
                    self.configChecks.setdefault(
                        item, effectiveDefaultItemCheck))
        if patcherOn:
            self._enable_self()
        # Bold it if it has a new item, italicize it if it has no items
        patcher_italics = self.gList.lb_get_items_count() == 0
        self._style_patcher_label(bold=patcher_bold, italics=patcher_italics)

    def OnListCheck(self, _lb_selection_dex=None):
        """One of list items was checked. Update all configChecks states."""
        for i, item in enumerate(self._curr_items):
            self.configChecks[item] = self.gList.lb_is_checked_at_index(i)
        self._enable_self(any(self.configChecks.values()))

    def OnAutomatic(self, is_checked):
        """Automatic checkbox changed."""
        self.autoIsChecked = is_checked
        if self.autoIsChecked:
            self._sort_and_update_items(self._get_auto_items())
        else:
            # In autoIsChecked case, this is called by _handle_item_search
            self._update_manual_buttons()

    def OnAdd(self):
        """Add button clicked."""
        srcDir = bosh.modInfos.store_dir
        wildcard = bosh.modInfos.plugin_wildcard()
        #--File dialog
        title = _('Get ') + self._list_label
        srcPaths = FileOpenMultiple.display_dialog(self.gConfigPanel, title,
                                                   srcDir, u'', wildcard)
        if not srcPaths: return
        #--Get new items
        for srcPath in srcPaths:
            folder, fname = srcPath.headTail
            if folder == srcDir and (fn := FName(fname.s)) not in \
                    self.configItems: self.configItems.append(fn)
        self._sort_and_update_items(self.configItems)

    def OnRemove(self):
        """Remove button clicked."""
        selections = self.gList.lb_get_selections()
        newItems = [item for index, item in enumerate(self.configItems)
                    if index not in selections]
        self._sort_and_update_items(newItems)

    def mass_select(self, select=True):
        try:
            self.gList.set_all_checkmarks(checked=select)
            self.OnListCheck()
        except AttributeError:
            pass #ListBox instead of CheckListBox
        super().mass_select(select)

    #--Config Phase -----------------------------------------------------------
    def _getConfig(self, configs):
        """Get config from configs dictionary and/or set to default."""
        config = super()._getConfig(configs)
        self.autoIsChecked = self.forceAuto or config.get('autoIsChecked',True)
        self.remove_empty_sublists = config.get('remove_empty_sublists',
            self.__class__.default_remove_empty_sublists)
        # Merge entries from the config with existing ones - if we're loading
        # the first config, the existing ones will be empty. Otherwise, we're
        # restoring a config into an existing state, so don't delete the
        # already present items
        existing_config_items = set(self.configItems)
        for cfg_item in forward_compat_path_to_fn_list(
                config.get('configItems', [])):
            if cfg_item not in existing_config_items:
                self.configItems.append(cfg_item)
        #--Verify file existence
        self.configItems = self.patcher_type.get_sources(self._bp,
                                                         self.configItems)
        if self._was_present:
            present_config_items = set(self.configItems)
            # We first have to reset the checked/choices state for each newer
            # item (on first load there are no newer items, so this is a
            # noop)...
            for fn_item in list(self.configChecks):
                self.configChecks[fn_item] = False
            for fn_item in list(self.configChoices):
                self.configChoices[fn_item] = set()
            # ...and then we can restore the old checked/choices state (if the
            # items in question are actually still present in the Data folder)
            for fn_item, item_checked in forward_compat_path_to_fn(
                    config.get('configChecks', {})).items():
                if fn_item in present_config_items:
                    self.configChecks[fn_item] = item_checked
            for fn_item, choices_set in forward_compat_path_to_fn(
                    config.get('configChoices', {})).items():
                if fn_item in present_config_items:
                    self.configChoices[fn_item] = choices_set
        else:
            # There was no config for us, so simply reset these two to their
            # default values so they get filled with defaults during list
            # population later on
            self.configChecks = {}
            self.configChoices = {}
        if self.__class__.forceItemCheck:
            for item in self.configItems:
                self.configChecks[item] = True
        return config

    def saveConfig(self, configs):
        """Save config to configs dictionary."""
        config = super(_ListPatcherPanel, self).saveConfig(configs)
        #--Toss outdated configCheck data.
        listSet = set(self.configItems)
        config['configChecks'] = {k: v for k, v in self.configChecks.items()
                                  if k in listSet}
        config['configChoices'] = {k: v for k, v in self.configChoices.items()
                                   if k in listSet}
        config[u'configItems'] = self.configItems
        config[u'autoIsChecked'] = self.autoIsChecked
        config[u'remove_empty_sublists'] = self.remove_empty_sublists
        return config

    def getItemLabel(self,item):
        """Returns label for item to be used in list"""
        return f'{item}' # Path or string - YAK

    def _get_auto_items(self):
        """Returns list of items to be used for automatic configuration."""
        return self.__class__.patcher_type.get_sources(self._bp)

    def _import_config(self, default=False):
        super(_ListPatcherPanel, self)._import_config(default)
        if default:
            self._sort_and_update_items(self._get_auto_items())
            return
        # Reset the search bar, this will call _handle_item_search
        self._item_search.text_content = ''
        for index, item in enumerate(self._curr_items):
            try:
                self.gList.lb_check_at_index(index, self.configChecks[item])
            except KeyError: # keys should be all bolt.Paths
                pass
                # bolt.deprint(u'item %s not in saved configs [%s]' % (
                #     item, u', '.join([repr(c) for c in self.configChecks])))

    def get_patcher_instance(self, patch_file):
        patcher_sources = self._get_list_patcher_srcs()
        return self.patcher_type(self.patcher_name, patch_file,
                                 patcher_sources)

    def _get_list_patcher_srcs(self):
        return [x for x in self.configItems if self.configChecks[x]]

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

class _TweakPatcherPanel(_ChoiceMenuMixin, _PatcherPanel):
    """Patcher panel with list of checkable, configurable tweaks."""
    patcher_type: MultiTweaker

    def __init__(self):
        super().__init__()
        # List of all tweaks that this tweaker can house
        self._all_tweaks: list[MultiTweakItem] = []
        # List of tweaks that are currently visible (according to the search)
        self._curr_tweaks: list[MultiTweakItem] = []

    def GetConfigPanel(self, parent: PatchDialog, config_layout, gTipText):
        """Show config."""
        if self.gConfigPanel: return self.gConfigPanel
        gConfigPanel = super().GetConfigPanel(parent, config_layout, gTipText)
        self.gTweakList = CheckListBox(gConfigPanel)
        self.gTweakList.on_box_checked.subscribe(self.TweakOnListCheck)
        self._tweak_search = SearchBar(gConfigPanel, hint=_('Search Tweaks'))
        self._tweak_search.on_text_changed.subscribe(self._handle_tweak_search)
        #--Events
        self._bind_mouse_events(self.gTweakList)
        self.gTweakList.on_mouse_leaving.subscribe(self._mouse_leaving)
        self.mouse_dex = -1
        #--Layout
        self.main_layout.add(
            (HBoxedLayout(gConfigPanel, title=_('Tweaks'), item_expand=True,
                spacing=4, items=[
                    (VLayout(item_expand=True, spacing=4, items=[
                        self._tweak_search,
                        (self.gTweakList, LayoutOptions(weight=1)),
                    ]), LayoutOptions(weight=1)),
                    self._get_tweak_select_layout()
            ]), LayoutOptions(expand=True, weight=1)))
        return gConfigPanel

    def _get_tweak_select_layout(self):
        if self.selectCommands:
            self.gTweakSelectAll = SelectAllButton(self.gConfigPanel,
                btn_tooltip=_('Activate all currently visible tweaks.'))
            self.gTweakSelectAll.on_clicked.subscribe(
                lambda: self.mass_select(True))
            self.gTweakDeselectAll = DeselectAllButton(self.gConfigPanel,
               btn_tooltip=_('Deactivate all currently visible tweaks.'))
            self.gTweakDeselectAll.on_clicked.subscribe(
                lambda: self.mass_select(False))
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
        isFirstLoad = self._GetIsFirstLoad()
        patcher_bold = False
        for index, tweak in enumerate(self._curr_tweaks):
            item_label = tweak.getListLabel()
            if tweak.choiceLabels and tweak.choiceLabels[
                tweak.chosen] == tweak.custom_choice:
                item_label = _custom_label(item_label, tweak.choiceValues[tweak.chosen][0])
            self.gTweakList.lb_insert(item_label, index)
            self.gTweakList.lb_check_at_index(index, tweak.isEnabled)
            if not isFirstLoad and tweak.isNew():
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
        self.gTipText.label_text = u''
        self.mouse_pos = None

    def _handle_mouse_motion(self, wrapped_evt, lb_dex):
        """Check mouse motion to detect right click event. If any mouse button
         is held pressed, is_moving is False and is_dragging is True."""
        if wrapped_evt.is_moving:
            self.mouse_pos = None
            if lb_dex != self.mouse_dex:
                # Show tip text when changing item
                self.mouse_dex = lb_dex
                self.gTipText.label_text = (
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
            def Execute(self): _self.tweak_custom_choice(self.index,tweakIndex)
        for index, itm_txt in enumerate(choiceLabels):
            if itm_txt == '----':
                links.append(SeparatorLink())
            elif itm_txt == tweak.custom_choice:
                itm_txt = _custom_label(itm_txt, tweak.choiceValues[index][0])
                links.append(_ValueLinkCustom(itm_txt, index))
            else:
                links.append(_ValueLink(itm_txt, index))
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

    _msg = _(u'Enter the desired custom tweak value.') + u'\n' + _(
        u'Due to an inability to get decimal numbers from the wxPython '
        u'prompt please enter an extra zero after your choice if it is not '
        u'meant to be a decimal.') + u'\n' + _(
        u'If you are trying to enter a decimal multiply it by 10, '
        u'for example for 0.3 enter 3 instead.')

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
                key_display = u'\n\n' + tweak.tweak_key[i] if isinstance(
                    tweak.tweak_key, tuple) else tweak.tweak_key
            else:
                key_display = u''
            if isinstance(v, float):
                msg = (_('Enter the desired custom tweak value.') + '\n\n' + _(
                    'Note: A floating point number is expected here.'))
                msg = f'{msg}{key_display}'
                while new is None: # keep going until user entered valid float
                    new = askText(self.gConfigPanel, msg,
                           title=tweak.tweak_name + _(' - Custom Tweak Value'),
                           default_txt=str(tweak.choiceValues[index][i]))
                    if new is None: #user hit cancel
                        return
                    try:
                        values.append(float(new))
                        new = None # Reset, we may have a multi-key tweak
                        break
                    except ValueError:
                        ermsg = _("'%s' is not a valid floating point number."
                                  ) % new
                        showError(self.gConfigPanel, ermsg,
                                  title=tweak.tweak_name + _(' - Error'))
                        new = None # invalid float, try again
            elif isinstance(v, int):
                msg = _('Enter the desired custom tweak value.') + key_display
                new = askNumber(self.gConfigPanel, msg, prompt=_('Value'),
                    title=tweak.tweak_name + _(' - Custom Tweak Value'),
                    initial_num=tweak.choiceValues[index][i], min_num=-10000,
                    max_num=10000)
                if new is None: #user hit cancel
                    return
                values.append(new)
            elif isinstance(v, str):
                msg = _(u'Enter the desired custom tweak text.') + key_display
                new = askText(self.gConfigPanel, msg,
                    title=tweak.tweak_name + _(' - Custom Tweak Text'),
                    default_txt=tweak.choiceValues[index][i], strip=False) ##: strip ?
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
            showError(self.gConfigPanel, error_header + validation_error,
                      title=_('%s - Error') % tweak.tweak_name)

    def mass_select(self, select=True):
        """'Select All' or 'Deselect All' button was pressed, update all
        configChecks states."""
        self.gTweakList.set_all_checkmarks(checked=select)
        self.TweakOnListCheck()
        super().mass_select(select)

    #--Config Phase -----------------------------------------------------------
    def _getConfig(self, configs):
        """Get config from configs dictionary and/or set to default."""
        config = super()._getConfig(configs)
        all_tweaks = self.patcher_type.tweak_instances(self._bp)
        self._all_tweaks = self._curr_tweaks = all_tweaks
        for tweak in self._all_tweaks:
            tweak.init_tweak_config(config)
        return config

    def saveConfig(self, configs):
        """Save config to configs dictionary."""
        config = super(_TweakPatcherPanel, self).saveConfig(configs)
        for tweak in self._all_tweaks:
            tweak.save_tweak_config(config)
        return config

    def _log_config(self, conf, config, clip, log):
        self._getConfig(config) # set self._all_tweaks and load their config
        for tweak in self._all_tweaks:
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

    def _import_config(self, default=False):
        super(_TweakPatcherPanel, self)._import_config(default)
        # Reset the search bar, this will call _handle_tweak_search
        self._tweak_search.text_content = ''
        for index, tweakie in enumerate(self._all_tweaks):
            try:
                self.gTweakList.lb_check_at_index(index, tweakie.isEnabled)
                self.gTweakList.lb_set_label_at_index(index, tweakie.getListLabel())
            except KeyError: pass # no such key don't spam the log
            except: bolt.deprint('Error importing Bashed Patch configuration. '
                                 f'Item {tweakie} skipped.', traceback=True)

    def get_patcher_instance(self, patch_file):
        enabledTweaks = [t for t in self._all_tweaks if t.isEnabled]
        return self.patcher_type(self.patcher_name, patch_file, enabledTweaks)

#------------------------------------------------------------------------------
class _ImporterPatcherPanel(_ListPatcherPanel):

    def saveConfig(self, configs):
        """Save config to configs dictionary."""
        config = super(_ImporterPatcherPanel, self).saveConfig(configs)
        if self.isEnabled:
            configs[u'ImportedMods'].update(
                [item for item, value in self.configChecks.items() if
                 value and bosh.ModInfos.rightFileType(item)])
        return config

class _ListsMergerPanel(_ChoiceMenuMixin, _ListPatcherPanel):
    listLabel = _('Override Delev/Relev Tags')

    #--Config Phase -----------------------------------------------------------
    forceAuto = False
    forceItemCheck = True #--Force configChecked to True for all items
    choiceMenu = (u'Auto', u'----', u'Delev', u'Relev')
    # CONFIG DEFAULTS
    default_isEnabled = True
    selectCommands = False

    def _get_set_choice(self, item):
        """Get default config choice."""
        config_choice = self.configChoices.get(item)
        if not isinstance(config_choice,set): config_choice = {u'Auto'}
        if u'Auto' in config_choice:
            bashTags = self._bp.all_tags.get(item, set())
            config_choice = {'Auto',
                             *(self.patcher_type.patcher_tags & bashTags)}
        self.configChoices[item] = config_choice
        return config_choice

    def getItemLabel(self,item):
        # Note that we do *not* want to escape the & here - that puts *two*
        # ampersands in the resulting ListBox for some reason
        choice = ''.join(
            sorted(i[0] for i in self.configChoices.get(item, ()) if i))
        return f'{item}{f" [{choice}]" if choice else ""}'

    def GetConfigPanel(self, parent: PatchDialog, config_layout, gTipText):
        if self.gConfigPanel: return self.gConfigPanel
        gConfigPanel = super().GetConfigPanel(parent, config_layout, gTipText)
        self._bind_mouse_events(self.gList)
        return gConfigPanel

    def _getConfig(self, configs):
        """Get config from configs dictionary and/or set to default."""
        config = super()._getConfig(configs)
        #--Make sure configChoices are set (as choiceMenu exists).
        for item in self.configItems:
            self._get_set_choice(item)
        return config

    def _get_auto_items(self):
        for mod in self._bp.all_plugins:
            self._get_set_choice(mod)
        return super()._get_auto_items()

    def ShowChoiceMenu(self, itemIndex):
        """Displays a popup choice menu if applicable.
        NOTE: Assume that configChoice returns a set of chosen items."""
        #--Item Index
        if itemIndex < 0: return
        self.gList.lb_select_index(itemIndex)
        choiceSet = self._get_set_choice(self._curr_items[itemIndex])
        #--Build Menu
        class _OnItemChoice(CheckLink):
            def __init__(self, _text, index):
                super(_OnItemChoice, self).__init__(_text)
                self.index = index
            def _check(self): return self._text in choiceSet
            def Execute(self): _onItemChoice(self.index)
        def _onItemChoice(dex):
            """Handle choice menu selection."""
            item = self._curr_items[itemIndex]
            choice = self.choiceMenu[dex]
            choiceSet = self.configChoices[item]
            choiceSet ^= {choice}
            if choice != u'Auto':
                choiceSet.discard(u'Auto')
            elif u'Auto' in self.configChoices[item]:
                self._get_set_choice(item)
            self.gList.lb_set_label_at_index(itemIndex, self.getItemLabel(item))
        links = Links()
        for index, item_label in enumerate(self.choiceMenu):
            if item_label == '----':
                links.append(SeparatorLink())
            else:
                links.append(_OnItemChoice(item_label, index))
        #--Show/Destroy Menu
        links.popup_menu(self.gList, None)

    def _log_config(self, conf, config, clip, log):
        self.configChoices = conf.get(u'configChoices', {})
        for item in map(self.getItemLabel, conf.get(u'configItems', [])):
            log(f'. __{item}__')
            clip.write(f'    {item}\n')

    def _import_config(self, default=False): # TODO(ut):non default not handled
        if default:
            super(_ListsMergerPanel, self)._import_config(default)

    def _style_patcher_label(self, bold=False, italics=False):
        # Never italicize these since they will run even if there are no tagged
        # source plugins
        super(_ListsMergerPanel, self)._style_patcher_label(bold=bold)

class _GmstTweakerPanel(_TweakPatcherPanel):
    # CONFIG DEFAULTS
    default_isEnabled = True

#------------------------------------------------------------------------------
# GUI Patcher classes
# Do _not_ change the _config_key attr or you will break existing BP configs
#------------------------------------------------------------------------------
# Patchers 10 -----------------------------------------------------------------
class AliasPluginNames(_AliasesPatcherPanel):
    _config_key = 'AliasesPatcher'
    patcher_type = AliasPluginNamesPatcher

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
class TweakSettings(_GmstTweakerPanel):
    patcher_name = _(u'Tweak Settings')
    patcher_desc = _(u'Tweak game settings.')
    _config_key = u'GmstTweaker'
    patcher_type = multitweak_settings.TweakSettingsPatcher

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
    canAutoItemCheck = False #--GUI: Whether new items are checked by default.

# -----------------------------------------------------------------------------
class _AListsMerger(_ListsMergerPanel):
    """Mergers targeting all mods in the LO, with the option to override
    tags."""
    def get_patcher_instance(self, patch_file):
        patcher_sources = self._get_list_patcher_srcs()
        return self.patcher_type(self.patcher_name, patch_file,
                                 patcher_sources,
                                 self.remove_empty_sublists,
                                 defaultdict(tuple, self.configChoices))

class LeveledLists(_AListsMerger):
    patcher_name = _(u'Leveled Lists')
    patcher_desc = u'\n\n'.join([
        _('Merges changes to leveled lists from all active and/or merged '
          'plugins.'),
        _(u'Advanced users may override Relev/Delev tags for any mod (active '
          u'or inactive) using the list below.')])
    _config_key = u'ListsMerger'
    patcher_type = mergers.LeveledListsPatcher
    show_empty_sublist_checkbox = True

class FormIDLists(_AListsMerger):
    patcher_name = _(u'FormID Lists')
    patcher_desc = u'\n\n'.join([
        _('Merges changes to FormID lists from all active and/or merged '
          'plugins.'),
        _(u'Advanced users may override Deflst tags for any mod (active or '
          u'inactive) using the list below.')])
    _config_key = u'FidListsMerger'
    patcher_type = mergers.FormIDListsPatcher
    listLabel = _('Override Deflst Tags')
    forceItemCheck = False #--Force configChecked to True for all items
    choiceMenu = (u'Auto', u'----', u'Deflst')
    # CONFIG DEFAULTS
    default_isEnabled = False

# -----------------------------------------------------------------------------
class ContentsChecker(_PatcherPanel):
    """Checks contents of leveled lists, inventories and containers for
    correct content types."""
    patcher_name = _(u'Contents Checker')
    patcher_desc = _(u'Checks contents of leveled lists, inventories and '
                     u'containers for correct types.')
    _config_key = u'ContentsChecker'
    patcher_type = checkers.ContentsCheckerPatcher
    default_isEnabled = True

# -----------------------------------------------------------------------------
class RaceChecker(_PatcherPanel):
    """Sorts hairs and eyes."""
    patcher_name = _(u'Race Checker')
    patcher_desc = _(u'Sorts race hairs and eyes.')
    _config_key = u'RaceChecker'
    patcher_type = checkers.RaceCheckerPatcher
    default_isEnabled = True

#------------------------------------------------------------------------------
class NpcChecker(_PatcherPanel):
    """Assigns missing hair and eyes."""
    patcher_name = _(u'NPC Checker')
    patcher_desc = _(u'This will randomly assign hairs and eyes to NPCs that '
                     u'are otherwise missing them.')
    _config_key = u'NpcChecker'
    patcher_type = checkers.NpcCheckerPatcher
    default_isEnabled = True

#------------------------------------------------------------------------------
class TimescaleChecker(_PatcherPanel):
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
    globals()[gsp_name] = type(gsp_name, (_PatcherPanel,),
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
    patcher_classes = [globals()[p] for p in bush.game.patchers]
    # Sort alphabetically first for aesthetic reasons
    patcher_classes.sort(key=lambda a: a.patcher_name)
    # After that, sort by group to make patchers instantiate in the right order
    patcher_classes.sort(
        key=lambda a: group_order[a.patcher_type.patcher_group])
    all_gui_patchers.extend((p() for p in patcher_classes))
    # Update the set of all tags for this game based on the available patchers
    bush.game.allTags.update(chain.from_iterable(
        getattr(p.patcher_type, 'patcher_tags', ()) for p in all_gui_patchers))
