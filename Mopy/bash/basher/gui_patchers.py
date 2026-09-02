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
    PatcherConfig, TweakPatcherConfig, AliasPluginNames as _APConfig, \
    LeveledLists as _LLConfig

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
class AliasPluginNames(_PatcherPanel, _APConfig):

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
class _ListPanel(_PatcherPanel):
    _list_label = ''
    _auto_enable_on_populate = False
    _search_hint = _('Search Sources')
    _select_all_tooltip = _('Activate all currently visible sources.')
    _deselect_all_tooltip = _('Deactivate all currently visible sources.')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._all_items: list[FName | MultiTweakItem] = []
        # List of items that are currently visible (according to the search)
        self._curr_items = []

    def native_init(self, *args, **kwargs):
        if freshly_created := super().native_init(*args, **kwargs):
            self._get_glist()
            self._item_search = SearchBar(self, hint=self._search_hint)
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

    def _get_glist(self):
        self.gList = CheckListBox(self)
        self.gList.on_box_checked.subscribe(self._on_list_check)

    def _auto_layout(self, right_side_components=None):
        self._populate_item_list()
        return None

    def _get_select_layout(self):
        if not self.selectCommands: return None
        select_all = SelectAllButton(self,
            btn_tooltip=self._select_all_tooltip,
            on_click=lambda: self.mass_select(True))
        deselect_all = DeselectAllButton(self,
            btn_tooltip=self._deselect_all_tooltip,
            on_click=lambda: self.mass_select(False))
        return VLayout(spacing=4, items=[select_all, deselect_all])

    def _populate_item_list(self):
        with self.gList.pause_drawing():
            self._do_populate_item_list()

    def _do_populate_item_list(self):
        """Populate and style the currently visible entries."""
        self.gList.lb_clear()
        patcher_on = False
        patcher_bold = False
        for index, list_item in enumerate(self._curr_items):
            self.gList.lb_insert(self._get_item_label(list_item), index)
            if do_bold := self._is_item_new(list_item):
                self.gList.lb_style_font_at_index(index, bold=True)
            patcher_on |= self._check_item(list_item, index)
            patcher_bold |= do_bold
        if patcher_on and self._auto_enable_on_populate:
            self._enable_self()
        # Bold it if it has a new item, italicize it if it has no items.
        self._style_patcher_label(bold=patcher_bold,
            italics=self.gList.lb_get_items_count() == 0)

    def _check_item(self, list_item, index):
        checked = self._is_item_checked(list_item)
        self.gList.lb_check_at_index(index, checked)
        return checked

    def _get_item_label(self, list_item):
        raise NotImplementedError

    def _is_item_checked(self, list_item):
        raise NotImplementedError

    def _is_item_new(self, list_item):
        raise NotImplementedError

    def _handle_item_search(self, search_str):
        """Repopulate the list when the search text changes."""
        lower_search_str = search_str.strip().lower()
        self._curr_items = [i for i in self._all_items if any(
            lower_search_str in s.lower()
            for s in self._get_item_search_strings(i))]
        self._populate_item_list()

    def _get_item_search_strings(self, list_item):
        return (list_item,)

    def mass_select(self, select=True):
        try:
            self.gList.set_all_checkmarks(checked=select)
            self._on_list_check()
        except AttributeError:
            pass # ListBox instead of CheckListBox
        super().mass_select(select)

class _ListPatcherPanel(_ListPanel, ListPatcherConfig):
    """Patcher panel with option to select source elements."""
    gList: CheckListBox
    # Unlike tweak panels, checked sources enable the panel when populated.
    _auto_enable_on_populate = True

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Set of items that are new and hence need to remain bolded
        self._new_items: set[FName] = set()

    # List Panel implementation -----------------------------------------------
    def _auto_layout(self, right_side_components=None):
        self._sort_and_update_items()
        return None

    def _sort_and_update_items(self, is_auto=True, do_sort=True):
        """Helper for LO-sorting items and updating the internal caches for
        them."""
        super()._sort_and_update_items(is_auto, do_sort)
        self._all_items = list(self._item_config)
        # Clear the search bar - this will _handle_item_search, which will call
        # _do_populate_item_list in turn
        self._item_search.text_content = ''

    def _set_choice(self, item):
        """Only called when loading automatically for _ListPatcherPanel."""
        if not self._is_first_load and self._item_config.get(item) is None:
            self._new_items.add(item)
        super()._set_choice(item)

    def _get_item_label(self, list_item):
        return self._mod_label(list_item, self._item_config)

    def _is_item_checked(self, list_item):
        return self._item_config[list_item]

    def _is_item_new(self, list_item):
        return list_item in self._new_items

    def _on_list_check(self, _lb_selection_dex=None):
        """One of list items was checked. Update all configChecks states."""
        for i, item in enumerate(self._curr_items):
            self._item_config[item] = self.gList.lb_is_checked_at_index(i)
        self._enable_self(any(self._item_config.values()))

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

    def ShowChoiceMenu(self, lb_index): raise NotImplementedError

_label_formats = {str: u'%s', float: u'%4.2f', int: u'%d'}
def _custom_label(label_text, val): # edit label text with value
    return f'{label_text}: {_label_formats[type(val)] % val}'

class _TweakPatcherPanel(_ChoiceMenuMixin, _ListPanel, TweakPatcherConfig):
    """Patcher panel with list of checkable, configurable tweaks."""
    _list_label = _('Tweaks')
    _search_hint = _('Search Tweaks')
    _select_all_tooltip = _('Activate all currently visible tweaks.')
    _deselect_all_tooltip = _('Deactivate all currently visible tweaks.')

    def native_init(self, *args, **kwargs):
        if freshly_created := super().native_init(*args, **kwargs):
            #--Events
            self._bind_mouse_events(self.gList)
            self.gList.on_mouse_leaving.subscribe(self._mouse_leaving)
            self.mouse_dex = -1
        return freshly_created

    def _get_item_label(self, list_item):
        item_label = list_item.getListLabel()
        if list_item.choiceLabels and list_item.choiceLabels[
                list_item.chosen] == list_item.custom_choice:
            item_label = _custom_label(item_label,
                list_item.choiceValues[list_item.chosen][0])
        return item_label

    def _is_item_checked(self, list_item):
        return list_item.isEnabled

    def _is_item_new(self, list_item):
        return not self._is_first_load and list_item.isNew()

    def _on_list_check(self, _lb_selection_dex=None):
        """One of list items was checked. Update all check states."""
        for index, tweak in enumerate(self._curr_items):
            tweak.isEnabled = self.gList.lb_is_checked_at_index(index)
        self._enable_self(any(t.isEnabled for t in self._all_items))

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
                    self._curr_items[lb_dex].tweak_tip
                    if 0 <= lb_dex < len(self._curr_items) else '')
        else:
            super(_TweakPatcherPanel, self)._handle_mouse_motion(wrapped_evt,
                                                                 lb_dex)

    def _get_item_search_strings(self, list_item):
        return list_item.tweak_name, list_item.tweak_tip

    def ShowChoiceMenu(self, lb_index):
        """Displays a popup choice menu if applicable."""
        if lb_index >= len(self._curr_items): return
        tweak = self._curr_items[lb_index]
        choiceLabels = tweak.choiceLabels
        if len(choiceLabels) <= 1: return
        self.gList.lb_select_index(lb_index)
        #--Build Menu
        links = Links()
        _self = self # ugly, tweak_custom_choice is too big to make it local though
        class _ValueLink(CheckLink):
            def __init__(self, _text):
                super(_ValueLink, self).__init__(_text)
                self.index = index
            def _check(self): return self.index == tweak.chosen
            def Execute(self): _self.tweak_choice(self.index, lb_index)
        class _ValueLinkCustom(_ValueLink):
            def Execute(self):
                _self.tweak_custom_choice(self.index, lb_index)
        for index, itm_txt in enumerate(choiceLabels):
            if itm_txt == '----':
                links.append_link(SeparatorLink())
            elif itm_txt == tweak.custom_choice:
                itm_txt = _custom_label(itm_txt, tweak.choiceValues[index][0])
                links.append_link(_ValueLinkCustom(itm_txt))
            else:
                links.append_link(_ValueLink(itm_txt))
        #--Show/Destroy Menu
        links.popup_menu(self.gList, None)

    def tweak_choice(self, index, tweakIndex):
        """Handle choice menu selection."""
        self._curr_items[tweakIndex].chosen = index
        self.gList.lb_set_label_at_index(
            tweakIndex, self._curr_items[tweakIndex].getListLabel())
        self.gList.lb_check_at_index(tweakIndex, True)
        # wx.EVT_CHECKLISTBOX is NOT fired so this line is needed (?)
        self._on_list_check()

    def tweak_custom_choice(self, index, tweakIndex):
        """Handle choice menu selection."""
        tweak: MultiTweakItem = self._curr_items[tweakIndex]
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
            self.gList.lb_set_label_at_index(tweakIndex, custom_label)
            self.gList.lb_check_at_index(tweakIndex, True)
            self._on_list_check() # fired so this line is needed (?)
        else:
            # The tweak doesn't like the values the user chose, let them know
            error_header = tweak.validation_error_header(values) + '\n\n'
            showError(self, error_header + validation_error, title=_(
                '%(tweak_title)s - Error') % {'tweak_title': tweak.tweak_name})

    # Config phase overrides
    def import_config(self, patchConfigs, **kwargs):
        super().import_config(patchConfigs, **kwargs)
        # Reset the search bar, this will call _handle_item_search
        self._item_search.text_content = ''

#------------------------------------------------------------------------------
class _ListsMergerPanel(_ChoiceMenuMixin, _ListPatcherPanel, ListMergerConfig):
    """Mergers targeting all mods in the LO, with the option to override
    tags."""
    choiceMenu: ClassVar[tuple[str, ...]]
    _add_dialog_title: str
    # CONFIG DEFAULTS
    selectCommands = False
    gList: ListBox

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

    def _on_auto_check(self, is_checked):
        """Automatic checkbox changed."""
        self.autoIsChecked = is_checked
        if is_checked:
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

    def ShowChoiceMenu(self, lb_index):
        """Displays a popup choice menu if applicable.
        NOTE: Assume that configChoice returns a set of chosen items."""
        #--Item Index
        if lb_index < 0: return
        (gui_li := self.gList).lb_select_index(lb_index)
        choiceSet = self._item_config[(curr := self._curr_items)[lb_index]]
        #--Build Menu
        choices, choice_menu, _self = self._item_config, self.choiceMenu, self
        class _OnItemChoice(CheckLink):
            def __init__(self, _text, dex):
                super(_OnItemChoice, self).__init__(_text)
                self._index = dex
            def _check(self): return self._text in choiceSet
            def Execute(self):
                item = curr[lb_index]
                choice_set = choices[item]
                choice_set ^= {choice := choice_menu[self._index]}
                if choice != 'Auto':
                    choice_set.discard('Auto')
                elif 'Auto' in choice_set:
                    _self._set_choice(item)
                gui_li.lb_set_label_at_index(lb_index, _self._mod_label(
                    item, choices))
        links = Links()
        for index, item_label in enumerate(choice_menu):
            links.append_link(SeparatorLink() if item_label == '----' else
                              _OnItemChoice(item_label, index))
        #--Show/Destroy Menu
        links.popup_menu(gui_li, None)

#------------------------------------------------------------------------------
class LeveledLists(_ListsMergerPanel, _LLConfig):
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
def init_gui_patchers():
    gpatcher_types.clear()
    skey = {p: j for j, p in enumerate(all_patcher_types)}
    for k, v in game_patcher_config_types.items():
        pan = globals()[k]
        for cls_name, conf_cls in v.items():
            pconf_type = pan if cls_name == k else type(
                cls_name, (pan, conf_cls,), {})
            gpatcher_types.append(pconf_type)
            skey[pconf_type] = skey[conf_cls]
    gpatcher_types.sort(key=skey.__getitem__)
