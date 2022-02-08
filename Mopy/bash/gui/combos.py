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
"""Houses some high-level components that are formed by combining other
components."""

__author__ = u'Infernio'

import wx as _wx

from .base_components import _AComponent
from .buttons import Button
from .events import EventResult
from .layouts import HBoxedLayout, HLayout, LayoutOptions, Spacer, Stretch, \
    VLayout
from .misc_components import HorizontalLine
from .multi_choices import ListBox
from .text_components import Label, HyperlinkLabel
from .top_level_windows import _APageComponent, PanelWin
from ..bolt import dict_sort

class DoubleListBox(PanelWin):
    """A combination of two ListBoxes and left/right buttons to move items
    between the two lists. Note that this implementation currently only works
    with sorted ListBoxes."""
    def __init__(self, parent, left_label, right_label, left_btn_tooltip=u'',
            right_btn_tooltip=u''):
        super(DoubleListBox, self).__init__(parent)
        self._left_list = ListBox(self, isSort=True, isHScroll=True,
            onSelect=lambda _lb_dex, _item_text: self._handle_list_selected(
                self._left_list))
        self._right_list = ListBox(self, isSort=True, isHScroll=True,
            onSelect=lambda _lb_dex, _item_text: self._handle_list_selected(
                self._right_list))
        self._move_right_btn = Button(self, u'>>', exact_fit=True,
            btn_tooltip=right_btn_tooltip)
        self._move_right_btn.on_clicked.subscribe(
            lambda: self._handle_move_button(self._move_right_btn))
        self._move_left_btn = Button(self, u'<<', exact_fit=True,
            btn_tooltip=left_btn_tooltip)
        self._move_left_btn.on_clicked.subscribe(
            lambda: self._handle_move_button(self._move_left_btn))
        # Move buttons start out disabled, they only get enabled once something
        # is selected by the user
        self._disable_move_buttons()
        HLayout(item_expand=True, spacing=4, items=[
            (HBoxedLayout(self, item_border=3, item_expand=True,
                item_weight=1, title=left_label,
                items=[self._left_list]), LayoutOptions(weight=1)),
            VLayout(spacing=4, items=[
                Stretch(), self._move_right_btn, self._move_left_btn,
                Stretch()
            ]),
            (HBoxedLayout(self, item_border=3, item_expand=True,
                item_weight=1, title=right_label,
                items=[self._right_list]), LayoutOptions(weight=1)),
        ]).apply_to(self)
        # Optional callback to call when a move button has been used. Runs
        # after the item has been moved and a new one has been selected.
        self.move_btn_callback = None

    def _disable_move_buttons(self):
        """Disables both move buttons."""
        for move_btn in (self._move_right_btn, self._move_left_btn):
            move_btn.enabled = False

    @property
    def _chosen_left(self):
        """Returns the name of the item that is currently selected by the user
        in the left list. Note that this will raise an error if no item has
        been selected, so it is only safe to call if that has already been
        checked."""
        return self._left_list.lb_get_selected_strings()[0]

    @property
    def _chosen_right(self):
        """Returns the name of the item that is currently selected by the user
        in the right list. Note that this will raise an error if no item has
        been selected, so it is only safe to call if that has already been
        checked."""
        return self._right_list.lb_get_selected_strings()[0]

    def _handle_list_selected(self, my_list):
        """Internal callback, called when an item in one of the two lists is
        selected. Deselects the other list and enables the right move
        button."""
        if my_list == self._left_list:
            other_list = self._right_list
            my_btn = self._move_right_btn
            other_btn = self._move_left_btn
        else:
            other_list = self._left_list
            my_btn = self._move_left_btn
            other_btn = self._move_right_btn
        other_list.lb_select_none()
        my_btn.enabled = True
        other_btn.enabled = False

    def _handle_move_button(self, my_btn):
        """Internal callback, called when one of the move buttons is clicked.
        Performs an actual move from one list to the other."""
        if my_btn == self._move_right_btn:
            chosen_item = self._chosen_left
            from_list = self._left_list
            to_list = self._right_list
        else:
            chosen_item = self._chosen_right
            from_list = self._right_list
            to_list = self._left_list
        # Add the item to the other list. These ListBoxes are sorted, so no
        # need to worry about where to insert it
        to_list.lb_append(chosen_item)
        sel_index = from_list.lb_get_selections()[0]
        item_count = from_list.lb_get_items_count()
        # Delete the item from our list
        from_list.lb_delete_at_index(sel_index)
        if item_count == 1:
            # If we only had one item left, don't select anything now. We do
            # need to disable the move buttons now, since nothing is selected
            self._disable_move_buttons()
        elif sel_index == item_count - 1:
            # If the last item was selected, select the one before that now
            from_list.lb_select_index(sel_index - 1)
        else:
            # Otherwise, the index will have shifted down by one, so just
            # select the item at the old index
            from_list.lb_select_index(sel_index)
        # If we have a callback, give that a chance to run now
        if self.move_btn_callback:
            self.move_btn_callback()

    @property
    def left_items(self):
        """Returns a list of the items in the left list."""
        return self._left_list.lb_get_str_items()

    @left_items.setter
    def left_items(self, new_left_items):
        """Changes the items in the left list to the specified list of
        items."""
        self._left_list.lb_set_items(new_left_items)
        self._update_selections()

    @property
    def right_items(self):
        """Returns a list of the items in the right list."""
        return self._right_list.lb_get_str_items()

    @right_items.setter
    def right_items(self, new_right_items):
        """Changes the items in the right list to the specified list of
        items."""
        self._right_list.lb_set_items(new_right_items)
        self._update_selections()

    def _update_selections(self):
        """If repopulating caused our selections to disappear, disable the move
        buttons again."""
        if (not self._left_list.lb_get_selections()
                and not self._right_list.lb_get_selections()):
            self._disable_move_buttons()

class WrappingTextMixin(_AComponent):
    """Mixin for components with a label that needs to be wrapped whenever the
    component is resized."""
    # Optional offset - wrap this many pixels sooner than we would otherwise
    _wrapping_offset = 0

    def __init__(self, panel_desc, *args, **kwargs):
        super(WrappingTextMixin, self).__init__(*args, **kwargs)
        self._panel_text = Label(self, panel_desc)
        self._panel_text.wrap(self.component_size[0] - self._wrapping_offset)
        self._last_width = self.component_size[0]
        self._on_size_changed = self._evt_handler(_wx.EVT_SIZE)
        self._on_size_changed.subscribe(self._wrap_text)

    def _wrap_text(self):
        """Internal callback that wraps the panel text."""
        if self._last_width != self.component_size[0]:
            self._last_width = self.component_size[0]
            self._panel_text.wrap(self._last_width - self._wrapping_offset)

class TreePanel(_APageComponent):
    """A panel with a tree of options where each leaf corresponds to a
    different subpanel. Note that only a depth of one or two is supported, but
    a depth of one is obviously pointless - just use ListPanel instead.

    Note that all pages and subpages will automatically be sorted by page
    name."""
    _wx_widget_type = _wx.Treebook
    _native_widget: _wx.Treebook

    class _LinkPage(WrappingTextMixin, PanelWin):
        """A panel with links to each subpage, that will take the user there
        when they click on them."""
        def __init__(self, parent, page_desc, select_page_callback,
                parent_page_name, sub_pages):
            super(TreePanel._LinkPage, self).__init__(page_desc, parent)
            def make_link(subpage_name):
                new_link = HyperlinkLabel(self, subpage_name, u'%s/%s' % (
                    parent_page_name, subpage_name), always_unvisited=True)
                new_link.on_link_clicked.subscribe(select_page_callback)
                return new_link
            layout_items = [self._panel_text, HorizontalLine(self)]
            layout_items.extend(HLayout(items=[Spacer(6), make_link(p)])
                                for p in sorted(sub_pages))
            VLayout(border=6, spacing=4, item_expand=True,
                    items=layout_items).apply_to(self)

    def __init__(self, parent, tree_geometry, page_descriptions):
        """Creates a new TreePanel with the specified tree geometry and page
        descriptions.

        :param tree_geometry: A dict mapping page names to either component
            classes or another dict. Components will be constructed with two
            parameters, parent and page description (see page_descriptions
            below), and act as leaves in the tree to display a page of options.
            They must inherit from ATreeMixin. A dict will create a level of
            subpages and an automatically generated 'link page'.
        :param page_descriptions: A dict mapping page names to descriptions."""
        super(TreePanel, self).__init__(parent)
        self._all_leaf_pages = []
        for page_name, page_val in dict_sort(tree_geometry):
            page_desc = page_descriptions.get(page_name, u'')
            if isinstance(page_val, dict):
                # This is not a leaf, add a link page and then the subpages
                link_page = self._LinkPage(self, page_desc, self.select_page,
                                           page_name, page_val)
                self.add_page(link_page, page_name)
                for subpage_name in sorted(page_val):
                    subpage_val = page_val[subpage_name]
                    if subpage_val.should_appear():
                        new_subpage = subpage_val(self, page_descriptions.get(
                            u'%s/%s' % (page_name, subpage_name), u''))
                        self._all_leaf_pages.append(new_subpage)
                        self.add_sub_page(new_subpage, subpage_name)
            else:
                if page_val.should_appear():
                    new_page = page_val(self, page_desc)
                    self._all_leaf_pages.append(new_page)
                    self.add_page(new_page, page_name)

    def add_sub_page(self, sub_page_component, sub_page_title):
        """Adds a subpage to the tree. The subpage will belong to the last page
        that was added via add_page."""
        self._native_widget.AddSubPage(self._resolve(sub_page_component),
            sub_page_title)

    def get_leaf_pages(self):
        """Returns a list of all leaf pages in this TreePanel."""
        return self._all_leaf_pages

    def select_page(self, page_path):
        """Scrolls to and selects the page corresponding to the specified path.
        The path must be a string of the form 'parent/child', where parent is
        the name of the parent page and child is the name of the child page."""
        parent_page, sub_page = page_path.split(u'/')
        ##: wx.TreeCtrl has the worst API ever, this desperately needs wrapping
        # and some rethinking (plus virtualizing etc.)
        tree_ctrl = self._native_widget.GetTreeCtrl()
        root_item = tree_ctrl.GetRootItem()
        # The root does not actually exist, so look at its first child. The
        # cookie value is only needed by wx to keep track of the current
        # iteration, it has no meaning outside of that
        curr_child, cookie = tree_ctrl.GetFirstChild(root_item)
        while curr_child.IsOk():
            # Check if we found the parent page yet
            if tree_ctrl.GetItemText(curr_child) == parent_page:
                # Found it - now to look for the child page
                curr_subchild, sub_cookie = tree_ctrl.GetFirstChild(curr_child)
                while curr_subchild.IsOk():
                    if tree_ctrl.GetItemText(curr_subchild) == sub_page:
                        # Found it - scroll to it and select it
                        tree_ctrl.ScrollTo(curr_subchild)
                        tree_ctrl.SelectItem(curr_subchild)
                        break
                    curr_subchild, sub_cookie = tree_ctrl.GetNextChild(
                        curr_child, sub_cookie)
                break
            curr_child, cookie = tree_ctrl.GetNextChild(root_item, cookie)
        # Need to return FINISH, otherwise the browser would try to open it
        return EventResult.FINISH

    def get_selected_page_path(self):
        """Returns the path to the currently selected page. E.g. if there's a
        page 'Bar' which is a child of the page 'Foo' and 'Bar' is currently
        selected, this would return 'Foo/Bar'."""
        ##: If you still don't believe me about the terrible API, look how
        # similar this mess is to the other method up there.
        tree_ctrl = self._native_widget.GetTreeCtrl()
        root_item = tree_ctrl.GetRootItem()
        # The root does not actually exist, so look at its first child. The
        # cookie value is only needed by wx to keep track of the current
        # iteration, it has no meaning outside of that
        curr_child, cookie = tree_ctrl.GetFirstChild(root_item)
        while curr_child.IsOk():
            child_name = tree_ctrl.GetItemText(curr_child)
            if tree_ctrl.IsSelected(curr_child):
                # It's a top-level page, just return the name
                return child_name
            # Otherwise, look at all *its* children
            curr_subchild, sub_cookie = tree_ctrl.GetFirstChild(curr_child)
            while curr_subchild.IsOk():
                subchild_name = tree_ctrl.GetItemText(curr_subchild)
                if tree_ctrl.IsSelected(curr_subchild):
                    # Found it as a subchild, separate them with a slash
                    return u'%s/%s' % (child_name, subchild_name)
                curr_subchild, sub_cookie = tree_ctrl.GetNextChild(
                    curr_child, sub_cookie)
            # None of the subchildren of this child are selected, move on to
            # the next child
            curr_child, cookie = tree_ctrl.GetNextChild(root_item, cookie)
        return None

class ATreeMixin(_AComponent):
    """A mixin for all leaf pages in a TreePanel."""
    @staticmethod
    def should_appear():
        """This component will only be constructed and shown to the user in the
        TreePanel if this method returns True. You can override this and use it
        to hide components that aren't relevant for the current state."""
        return True
