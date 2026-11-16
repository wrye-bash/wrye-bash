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
"""Tests for the merging logic of _AMerger - see issue #745 for duplicates."""
from collections import namedtuple

import pytest

from ..patcher.patchers.mergers import ImportActorsFactionsPatcher, \
    ImportInventoryPatcher

_Entry = namedtuple('_Entry', ['item', 'count'])
_Faction = namedtuple('_Faction', ['faction', 'rank'])
# _entries_diff and _merge_delta only need _entry_key, so skip __init__
_merger = object.__new__(ImportInventoryPatcher)

def _ents(spec, entry_type=_Entry):
    """'A1 A5' -> [_Entry('A', 1), _Entry('A', 5)]"""
    return [entry_type(s[0], int(s[1:])) for s in spec.split()]

def _merge(merger, master, plugins):
    """Merge the changes plugins with the same master make to it."""
    entries = master
    for plugin in plugins:
        delta = ('Mod.esp', *merger._entries_diff(master, plugin))
        entries = merger._merge_delta(delta, entries)
    return entries

@pytest.mark.parametrize('master, plugins, merged', [
    # duplicates
    ('A1 A5', ['A1 A10'], 'A1 A10'), # change the right one
    ('A1 A1', ['A1 A2'], 'A2 A1'), # keep the equal one
    ('A1', ['A1 A1'], 'A1 A1'), # add one
    ('A1 A1', ['A1'], 'A1'), # remove one
    # plugins with the same master
    ('B1', ['B1 A1', 'B1 A1'], 'B1 A1'), # both add A - once
    ('A1', ['A2', 'A1 B1'], 'A2 B1'),
    ('A1 B1', ['B1', 'A1 B5'], 'B5'),
    ('A1', ['A2', ''], ''), # remove what another plugin changed
])
def test_merge(master, plugins, merged):
    assert _merge(_merger, _ents(master), map(_ents, plugins)) == _ents(
        merged)

def test_merge_factions():
    """Both plugins' factions make it, not just the last plugin's ones."""
    merger = object.__new__(ImportActorsFactionsPatcher)
    plugins = [_ents(p, _Faction) for p in ('A0 B1', 'A2 C0')]
    assert _merge(merger, _ents('A0', _Faction), plugins) == _ents(
        'A2 B1 C0', _Faction)

def test_merge_delta_copies():
    entries = _ents('A1')
    _merger._merge_delta(('Mod.esp', [], [(_Entry('B', 1), 1)], []), entries)
    assert entries == _ents('A1')
