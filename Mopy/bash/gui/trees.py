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
"""Provides wrappers around basic trees, including both imperative/eager and
virtual/lazy APIs for constructing such trees."""
from __future__ import annotations

__author__ = 'Infernio'

from collections.abc import Iterable
from dataclasses import dataclass
from typing import Self

import wx as _wx

from .base_components import _AComponent, Color
from .misc_components import Font

@dataclass(slots=True, kw_only=True)
class TreeNodeFormat:
    """Dataclass holding information on how to decorate a single TreeNode."""
    # An index into the parent Tree's image list indicating the image to use
    # for this node. Must be None if the image list was not specified.
    icon_idx: int | None
    # The background color to use for this node.
    back_color: Color
    # The foreground/text color to use for this node.
    text_color: Color
    # If True, render this node's text in bold.
    bold: bool
    # If True, render this node's text in italics.
    italics: bool
    # If True, underline this node's text.
    underline: bool

##: There are probably more places where pause_drawing here should be added in
# the future (e.g. would it help with DeleteChildren?)
class TreeNode:
    """A single node in a Tree. Its children may be retrieved via the
    child_nodes property."""
    __slots__ = ('_parent_tree', '_native_parent', '_native_node_id',
                 '_node_text', '_child_nodes')

    def __init__(self, parent_tree: Tree, native_parent: _wx.TreeCtrl,
            native_node_id: _wx.TreeItemId, node_text: str):
        self._parent_tree = parent_tree
        self._native_parent = native_parent
        self._native_node_id = native_node_id
        self._node_text = node_text
        self._child_nodes: list[Self] = []

    # This Node ---------------------------------------------------------------
    def decorate_node(self, tif: TreeNodeFormat | None):
        """Decorate this tree node with the specified tree node format."""
        if tif is None:
            return # Simply skip decorating entirely
        if tif.icon_idx is not None:
            self._native_parent.SetItemImage(self._native_node_id,
                tif.icon_idx)
        self._native_parent.SetItemBackgroundColour(self._native_node_id,
            tif.back_color.to_rgba_tuple())
        self._native_parent.SetItemTextColour(self._native_node_id,
            tif.text_color.to_rgba_tuple())
        self._native_parent.SetItemFont(self._native_node_id, Font.Style(
            self._native_parent.GetItemFont(self._native_node_id),
            strong=tif.bold, slant=tif.italics, underline=tif.underline))

    def collapse_node(self, recursively=False):
        """Programmatically collapse this node. If recursively is True,
        collapse all its subnodes as well."""
        if recursively:
            self._native_parent.CollapseAllChildren(self._native_node_id)
        else:
            self._native_parent.Collapse(self._native_node_id)

    def expand_node(self, recursively=False):
        """Programmatically expand this node. If recursively is True, expand
        all its subnodes as well."""
        if recursively:
            self._native_parent.ExpandAllChildren(self._native_node_id)
        else:
            self._native_parent.Expand(self._native_node_id)

    # Children ----------------------------------------------------------------
    def _wrap_child(self, new_child_id: _wx.TreeItemId, child_text: str,
            child_node_type: type[TreeNode] | None = None):
        """Internal method holding shared code for append_child et al."""
        if child_node_type is None:
            child_node_type = self.__class__
        new_child =  child_node_type(self._parent_tree, self._native_parent,
            new_child_id, child_text)
        # The wx tree API is stupid and needs us to call up to the parent
        # constantly. That's usually not a problem for PyCharm since we'll just
        # be calling self._native_parent.SomeMethod(), but since *this*
        # tracking is custom and on the Python side, but relies on native wx
        # IDs, we do not want _notify_child_added escaping this file. But that
        # needs an underscore, so:
        # noinspection PyProtectedMember
        self._parent_tree._notify_child_added(new_child, new_child_id)
        return new_child

    def append_child(self, child_text: str, *,
            child_node_type: type[TreeNode] | None = None):
        """Create a new tree node with the specified text and add it as the
        last child of this node."""
        wrapped_child = self._wrap_child(self._native_parent.AppendItem(
            self._native_node_id, child_text), child_text, child_node_type)
        self._child_nodes.append(wrapped_child)
        return wrapped_child

    def delete_child(self, child_index: int):
        """Delete the child node of this node with the specified index, as well
        as all of its subnodes."""
        # Same reasoning as above
        # noinspection PyProtectedMember
        notify_del = self._parent_tree._notify_child_deleted
        to_del_node = self._child_nodes[child_index]
        for subnode in to_del_node.iter_subnodes():
            notify_del(subnode._native_node_id)
        # This will delete all its children as well
        self._native_parent.Delete(to_del_node._native_node_id)
        del self._child_nodes[child_index]

    def delete_children(self):
        """Delete all child nodes of this node, as well as all of their
        subnodes."""
        # Same reasoning as above
        # noinspection PyProtectedMember
        notify_del = self._parent_tree._notify_child_deleted
        for to_del_node in self._child_nodes:
            for subnode in to_del_node.iter_subnodes():
                notify_del(subnode._native_node_id)
        self._native_parent.DeleteChildren(self._native_node_id)
        self._child_nodes.clear()

    def insert_child(self, child_index: int, child_text: str, *,
            child_node_type: type[TreeNode] | None = None):
        """Create a new tree node with the specified text and add it at the
        specified index in the children of this node."""
        wrapped_child = self._wrap_child(self._native_parent.InsertItem(
            self._native_node_id, child_index, child_text), child_text,
            child_node_type)
        self._child_nodes.insert(child_index, wrapped_child)
        return wrapped_child

    def prepend_child(self, child_text: str, *,
            child_node_type: type[TreeNode] | None = None):
        """Create a new tree node with the specified text and add it as the
        first child of this node."""
        wrapped_child = self._wrap_child(self._native_parent.PrependItem(
            self._native_node_id, child_text), child_text, child_node_type)
        self._child_nodes.insert(0, wrapped_child)
        return wrapped_child

    def iter_child_nodes(self):
        """An iterator yielding the nodes that are direct children of this
        node."""
        return iter(self._child_nodes)

    def iter_subnodes(self):
        """An iterator yielding all nodes that are below this node, either
        because they are direct children of it or because they are children of
        those children, etc. Note that, for virtual nodes, this will *not*
        expand them but simply not yield any subnodes below them."""
        for subnode in self.iter_child_nodes():
            yield subnode
            yield from subnode.iter_subnodes()

    # Events ------------------------------------------------------------------
    def on_activated(self):
        """Called whenever this node was activated via double click or
        keyboard. Does nothing by default. May return EventResults."""

    def on_expanding(self):
        """Called whenever this node is being expanded in a VirtualTree. Does
        nothing by default. May return EventResults."""

    # Other -------------------------------------------------------------------
    @property
    def node_text(self):
        """The text shown on this node."""
        return self._node_text

    def __repr__(self):
        return (f'{self.__class__.__name__}<{self._node_text}, '
                f'{len(self._child_nodes)} children>')

# Currently unused, will be used for the Scripts tab (#502)
class AVirtualTreeNode(TreeNode):
    """Base class for virtual tree nodes."""
    __slots__ = ()

    def __init__(self, parent_tree: Tree, native_parent: _wx.TreeCtrl,
            native_node_id: _wx.TreeItemId, node_text: str):
        super().__init__(parent_tree, native_parent, native_node_id, node_text)
        # If we know this node will have children, mark it as expandable - the
        # actual children will be created in on_expanding
        if self.has_children():
            self._set_has_children(has_children=True)

    def _set_has_children(self, *, has_children: bool):
        self._native_parent.SetItemHasChildren(self._native_node_id,
            has_children)

    def on_expanding(self):
        with self._parent_tree.pause_drawing():
            for child_text in self.get_child_texts():
                self.append_child(child_text)

    def delete_children(self):
        super().delete_children()
        # Clear the 'has children' flag if we haven't expanded this one yet but
        # did delete all its (not yet constructed) children
        self._set_has_children(has_children=False)

    # Abstract API ------------------------------------------------------------
    def has_children(self) -> bool:
        raise NotImplementedError

    def get_child_texts(self) -> Iterable[str]:
        raise NotImplementedError

class Tree(_AComponent):
    """A Tree. Always has a root node, though you may hide it. Create a
    hierarchy by calling {append,insert,prepend}_child on the root node to add
    children to it, then call them on those children, etc. Note that the root
    node can currently not be deleted, but all children of it can be deleted by
    calling delete_child on the root node.

    Note that if you want to use virtual tree nodes, you need to use
    VirtualTree as well."""
    _native_widget: _wx.TreeCtrl

    def __init__(self, parent, image_list=None, *,
            root_text: str | None = None,
            root_node_type: type[TreeNode] = TreeNode):
        """Create a new Tree with the specified root text.

        :param parent: The object that this tree belongs to. May be a wx object
            or a component.
        :param image_list: An ImageList instance, or None if the tree items
            do not have any images.
        :param root_text: The text to use for the root element. If set to None,
            the root element will be hidden. That is useful if you want to
            simulate having multiple roots.
        :param root_node_type: If you want the root node to be virtual, set
            this to an AVirtualTreeNode-derived type."""
        style = _wx.TR_DEFAULT_STYLE
        if root_text is None:
            style |= _wx.TR_HIDE_ROOT
        super().__init__(parent, style=style)
        if image_list is not None:
            self._native_widget.SetImageList(self._resolve(image_list))
        self._native_tree_id_to_child = {}
        on_node_activated = self._evt_handler(_wx.EVT_TREE_ITEM_ACTIVATED,
            self._evt_to_node_processor)
        on_node_activated.subscribe(self._handle_node_activated)
        final_root_text = root_text or ''
        root_id = self._native_widget.AddRoot(final_root_text)
        self._root_node = root_node_type(self, self._native_widget, root_id,
            final_root_text)
        self._notify_child_added(self._root_node, root_id)

    # Internal API ------------------------------------------------------------
    def _evt_to_node_processor(self, tree_evt: _wx.TreeEvent):
        """Internal event processor, converts a tree event into the affected
        child node."""
        return [self._native_tree_id_to_child[tree_evt.GetItem()]]

    @staticmethod
    def _handle_node_activated(affected_node: TreeNode):
        """Internal callback, called when a node is activated. Simply delegates
        to the node itself."""
        return affected_node.on_activated()

    def _notify_child_added(self, new_child: TreeNode,
            native_child_id: _wx.TreeItemId):
        """Notify this tree of a new child with the specified native ID having
        been created in this tree."""
        self._native_tree_id_to_child[native_child_id] = new_child

    def _notify_child_deleted(self, native_child_id: _wx.TreeItemId):
        """Notify this tree of a child with the specified native ID having been
        deleted."""
        del self._native_tree_id_to_child[native_child_id]

    # Public API --------------------------------------------------------------
    def collapse_everything(self):
        """Recursively collapse all nodes in this tree."""
        self._native_widget.CollapseAll()

    def expand_everything(self):
        """Recursively expand all nodes in this tree."""
        self._native_widget.ExpandAll()

    @property
    def root_node(self):
        """The root node. May not be visible."""
        return self._root_node

# Currently unused, will be used for the Scripts tab (#502)
class VirtualTree(Tree):
    """A tree with support for virtual nodes. If you want to use any virtual
    tree nodes (i.e. ones derived from AVirtualTreeNode), then you have to use
    this class as well."""
    def __init__(self, parent, *, root_text: str | None = None,
            root_node_type: type[TreeNode] = TreeNode):
        super().__init__(parent, root_text=root_text,
            root_node_type=root_node_type)
        on_node_expanding = self._evt_handler(_wx.EVT_TREE_ITEM_EXPANDING,
            self._evt_to_node_processor)
        on_node_expanding.subscribe(self._handle_node_expanding)

    @staticmethod
    def _handle_node_expanding(affected_node: TreeNode):
        """Internal callback, called when a node is being expanded. Simply
        delegates to the node itself."""
        return affected_node.on_expanding()
