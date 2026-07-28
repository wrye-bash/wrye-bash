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
from typing import ClassVar

from .patcher_dialog import gpatcher_types
from .. import bass, bolt, bosh, load_order
from ..balt import CheckLink, SeparatorLink
from ..bolt import FName, dict_sort, text_wrap
from ..gui import TOP, Button, CheckBox, CheckListBox, DeselectAllButton, \
    EventResult, FileOpenMultiple, HBoxedLayout, Label, LayoutOptions, Lazy, \
    ListBox, Links, PanelWin, SearchBar, SelectAllButton, Spacer, TextArea, \
    VLayout, askText, showError, askNumber
from ..gui.base_components import AObject
from ..patcher.base import MultiTweakItem
from ..patcher.config_patchers import all_patcher_types, \
    game_patcher_config_types, ListMergerConfig, ListPatcherConfig, \
    PatcherConfig, TweakPatcherConfig

class _PatcherPanel(Lazy, PanelWin, PatcherConfig):
    """Basic patcher panel with no options."""
    selectCommands = True # whether this panel displays De/Select All

    def __init__(self, *args, **kwargs):
        super(AObject, self).__init__(*args, **kwargs)
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
        self._enable_self(select) # TODO(ut) check if set_focus is enough
        self._parent.gPatchers.set_focus_from_kb()

    @property
    def patcher_tip(self):
        # Remove everything but the first sentence from the first line of the
        # patcher description
        return re.sub(r'\..*', '.', self.patcher_desc.split('\n')[0])

    def _enable_self(self, self_enabled=True):
        """Enables or disables this patcher and notifies the patcher dialog."""
        self.isEnabled = self_enabled
        self._parent.check_patcher(self, self_enabled)

#------------------------------------------------------------------------------
class _AliasesPatcherPanel(_PatcherPanel):

    def native_init(self, *args, **kwargs):
        if freshly_created := super().native_init(*args, **kwargs):
            #--Aliases Text
            # gExample = Label(self, _("ExampleMod1.esp >> ExampleMod1.2.esp"))
            self.gAliases = TextArea(self)
            self.gAliases.on_focus_lost.subscribe(self._on_edit_aliases)
            self._set_alias_text()
            #--Sizing
            self.main_layout.add((self.gAliases, LayoutOptions(
                expand=True, weight=1)))
        return freshly_created

    def _set_alias_text(self):
        """Sets alias text according to current aliases."""
        self.gAliases.text_content = u'\n'.join([
            f'{alias_target} >> {alias_repl}'
            for alias_target, alias_repl in dict_sort(self.aliases)])

    def _on_edit_aliases(self):
        aliases_text = self.gAliases.text_content
        self.aliases.clear()
        for line in aliases_text.split(u'\n'):
            fields = [s.strip() for s in line.split(u'>>')]
            if len(fields) != 2 or not fields[0] or not fields[1]: continue
            self.aliases[fields[0]] = FName(fields[1])
        self._set_alias_text()

#------------------------------------------------------------------------------
class _ListPatcherPanel(_PatcherPanel, ListPatcherConfig):
    """Patcher panel with option to select source elements."""
    _autocheck_new = True #--GUI: Whether new items are checked by default
    gList: ListBox | CheckListBox
    _list_label = ''

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
            list_label = self._list_label or (_('Source Plugins/Files') if
                self.patcher_type._csv_key else _('Source Plugins'))
            self.main_layout.add(
                (HBoxedLayout(self, title=list_label,
                              item_expand=True, spacing=4, items=[
                        (VLayout(spacing=4, item_expand=True, items=[
                            self._item_search,
                            (self.gList, LayoutOptions(weight=1)),
                        ]), LayoutOptions(weight=1)),
                        (side_button_layout, LayoutOptions(v_align=TOP)),
                        self._get_select_layout(),
                    ]), LayoutOptions(expand=True, weight=1)))
        return freshly_created

    def mass_select(self, select=True):
        try:
            self.gList.set_all_checkmarks(checked=select)
            self.OnListCheck()
        except AttributeError:
            pass #ListBox instead of CheckListBox
        super().mass_select(select)

    # List Panel implementation -----------------------------------------------
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

class _TweakPatcherPanel(_ChoiceMenuMixin, _PatcherPanel, TweakPatcherConfig):
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
class _ListsMergerPanel(_ChoiceMenuMixin, _ListPatcherPanel, ListMergerConfig):
    """Mergers targeting all mods in the LO, with the option to override
    tags."""
    choiceMenu: ClassVar[tuple[str, ...]]
    _add_dialog_title: str
    # CONFIG DEFAULTS
    selectCommands = False

    def native_init(self, *args, **kwargs):
        if freshly_created := super().native_init(*args, **kwargs):
            self._bind_mouse_events(self.gList)
        return freshly_created

    def _style_patcher_label(self, bold=False, italics=False):
        # Never italicize these since they will run even if there are no tagged
        # source plugins # TODO(ut): no?
        super()._style_patcher_label(bold=bold)

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

    def _handle_item_search(self, search_str):
        super()._handle_item_search(search_str)
        self._update_manual_buttons(
            not (self.autoIsChecked or self._item_search.text_content))

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

    def _update_manual_buttons(self, btns_enabled):
        """Helper that enables or disables the add/remove buttons based on
        internal state."""
        for butt in self._add_rem_bt: butt.enabled = btns_enabled

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

    @classmethod
    def _config_attrs(cls):
        return *super()._config_attrs(), ('autoIsChecked', True)

    def import_config(self, *args):
        super(_ListPatcherPanel, self).import_config(*args) # bypass super!
        self._on_auto_check(self.autoIsChecked)

#------------------------------------------------------------------------------
class _LeveledListsPanel(_ListsMergerPanel):
    _list_label = _('Override Delev/Relev Tags')
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

#------------------------------------------------------------------------------
# Game specific GUI Patchers --------------------------------------------------
#------------------------------------------------------------------------------
def initPatchers():
    gpatcher_types.clear()
    skey = {p: j for j, p in enumerate(all_patcher_types)}
    for k, v in game_patcher_config_types.items():
        pan = globals()[k]
        for cls_name, conf_cls in v.items():
            gpatcher_types.append(typ := type(cls_name, (pan, conf_cls,), {}))
            skey[typ] = skey[conf_cls]
    gpatcher_types.sort(key=skey.__getitem__)
