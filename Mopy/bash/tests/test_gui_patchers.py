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
"""Regression tests for shared patcher panel behavior."""
from types import SimpleNamespace
from unittest.mock import Mock

import pytest

from .. import bass
from ..bolt import FName, GPath

@pytest.fixture
def panels(monkeypatch, tmp_path):
    # basher's menu definitions need these paths even without a main window.
    for dir_key in ('bainData', 'saveBase'):
        monkeypatch.setitem(bass.dirs, dir_key, GPath(str(tmp_path)))
    from ..basher import gui_patchers
    return gui_patchers

def _search_panel(panel_type, all_items):
    # Exercise the actual panel methods without creating native controls.
    panel = panel_type.__new__(panel_type)
    panel._all_items = all_items
    panel._curr_items = []
    panel._populate_item_list = Mock()
    return panel

@pytest.mark.parametrize('search_str, expected', [
    (' ALPHA ', ['Alpha.esp']),
    ('.CSV', ['Tags.csv']),
    ('missing', []),
    ('', ['Zulu.esp', 'Alpha.esp', 'Tags.csv']),
])
def test_source_search(panels, search_str, expected):
    panel = _search_panel(panels._ListPatcherPanel,
        list(map(FName, ['Zulu.esp', 'Alpha.esp', 'Tags.csv'])))
    assert panel._handle_item_search.__func__ is (
        panels._ListPanel._handle_item_search)
    panel._handle_item_search(search_str)
    assert panel._curr_items == list(map(FName, expected))
    panel._populate_item_list.assert_called_once_with()

@pytest.mark.parametrize('search_str, expected', [
    (' GRASS ', [0]),
    ('DISTANCE', [1]),
    ('grass adjust', []), # Do not match across name/description boundaries.
    ('missing', []),
    ('', [0, 1]),
])
def test_tweak_search(panels, search_str, expected):
    all_items = [
        SimpleNamespace(tweak_name='Grass', tweak_tip='Adjust density'),
        SimpleNamespace(tweak_name='View', tweak_tip='Change distance'),
    ]
    panel = _search_panel(panels._TweakPatcherPanel, all_items)
    assert panel._handle_item_search.__func__ is (
        panels._ListPanel._handle_item_search)
    panel._handle_item_search(search_str)
    assert panel._curr_items == [all_items[i] for i in expected]
    panel._handle_item_search('')
    assert panel._curr_items == all_items

def test_source_search_after_source_changes(panels):
    panel = _search_panel(panels._ListPatcherPanel, [FName('Old.esp')])
    panel._item_config = {FName('New.esp'): True, FName('Other.esp'): False}
    panel._item_search = SimpleNamespace(text_content='Old')
    panel._sort_and_update_items(is_auto=False, do_sort=False)
    assert panel._item_search.text_content == ''
    panel._handle_item_search('')
    assert panel._curr_items == [FName('New.esp'), FName('Other.esp')]

def test_tweak_config_keeps_filtered_out_items(panels):
    from ..patcher.config_patchers import TweakPatcherConfig
    visible_tweak = SimpleNamespace(isEnabled=False, save_tweak_config=Mock())
    hidden_tweak = SimpleNamespace(isEnabled=True, save_tweak_config=Mock())

    class _TestConfig(TweakPatcherConfig):
        patcher_name = patcher_desc = 'Test'
        _config_key = 'test'
        patcher_type = Mock()

        @classmethod
        def _tweaks_config(cls, config, bashed_patch=None):
            return [visible_tweak, hidden_tweak]

    config = _TestConfig(None)
    config.import_config({})
    assert config._all_items == config._curr_items
    config._curr_items = [visible_tweak]
    saved_configs = {}
    config.saveConfig(saved_configs)
    visible_tweak.save_tweak_config.assert_called_once_with(
        saved_configs['test'])
    hidden_tweak.save_tweak_config.assert_called_once_with(
        saved_configs['test'])
    config.get_patcher_instance(None)
    config.patcher_type.assert_called_once_with('Test', None, [hidden_tweak])

def _population_panel(panel_type, current_items):
    panel = panel_type.__new__(panel_type)
    panel._curr_items = current_items
    panel.gList = Mock()
    panel.gList.lb_get_items_count.return_value = len(current_items)
    panel._style_patcher_label = Mock()
    panel._enable_self = Mock()
    return panel

@pytest.mark.parametrize('checked', [False, True])
def test_source_population(panels, checked):
    source = FName('Source.esp')
    panel = _population_panel(panels._ListPatcherPanel, [source])
    panel._item_config = {source: checked}
    panel._new_items = {source}
    panel._do_populate_item_list()
    panel.gList.lb_insert.assert_called_once_with(source, 0)
    panel.gList.lb_check_at_index.assert_called_once_with(0, checked)
    panel.gList.lb_style_font_at_index.assert_called_once_with(0, bold=True)
    panel._style_patcher_label.assert_called_once_with(bold=True,
                                                      italics=False)
    assert panel._enable_self.call_count == int(checked)

@pytest.mark.parametrize('first_load', [False, True])
def test_tweak_population(panels, first_load):
    tweak = SimpleNamespace(getListLabel=lambda: 'Grass', isEnabled=True,
        isNew=lambda: True, choiceLabels=['Custom'], custom_choice='Custom',
        chosen=0, choiceValues=[(5,)])
    panel = _population_panel(panels._TweakPatcherPanel, [tweak])
    panel._is_first_load = first_load
    panel._do_populate_item_list()
    panel.gList.lb_insert.assert_called_once_with('Grass: 5', 0)
    panel.gList.lb_check_at_index.assert_called_once_with(0, True)
    assert panel.gList.lb_style_font_at_index.call_count == int(not first_load)
    panel._style_patcher_label.assert_called_once_with(bold=not first_load,
                                                      italics=False)
    # Populating an enabled tweak must not enable a disabled tweak panel.
    panel._enable_self.assert_not_called()

@pytest.mark.parametrize('panel_name', ['_ListPatcherPanel',
                                      '_TweakPatcherPanel'])
def test_empty_population(panels, panel_name):
    panel = _population_panel(getattr(panels, panel_name), [])
    assert panel._do_populate_item_list.__func__ is (
        panels._ListPanel._do_populate_item_list)
    assert panel._check_item.__func__ is panels._ListPanel._check_item
    panel._do_populate_item_list()
    panel.gList.lb_clear.assert_called_once_with()
    panel._style_patcher_label.assert_called_once_with(bold=False,
                                                      italics=True)
    panel._enable_self.assert_not_called()

def test_merger_population_has_no_checkboxes(panels):
    source = FName('Source.esp')
    panel = _population_panel(panels.LeveledLists, [source])
    panel._item_config = {source: {'Auto', 'Delev'}}
    panel._new_items = set()
    panel._do_populate_item_list()
    panel.gList.lb_insert.assert_called_once_with(
        panel._mod_label(source, panel._item_config), 0)
    panel.gList.lb_check_at_index.assert_not_called()
    panel._enable_self.assert_not_called()

@pytest.mark.parametrize('is_tweak', [False, True])
def test_native_panel_search_and_selection(panels, monkeypatch, is_tweak):
    import wx

    from .. import load_order
    from ..gui import VLayout

    monkeypatch.setitem(bass.inisettings, 'AutoItemCheck', True)
    monkeypatch.setattr(load_order, 'cached_sort', list)
    source = FName('Source.esp')
    tweak = SimpleNamespace(tweak_name='Grass', tweak_tip='Adjust density',
        getListLabel=lambda: 'Grass', isEnabled=True, isNew=lambda: False,
        choiceLabels=[], chosen=0)
    base_panel = (panels._TweakPatcherPanel if is_tweak else
                  panels._ListPatcherPanel)

    class _TestPanel(base_panel):
        patcher_name = patcher_desc = 'Test'
        _config_key = 'test'
        patcher_type = SimpleNamespace(_csv_key=None,
            get_sources=lambda *args: [source])

        @classmethod
        def _tweaks_config(cls, config, bashed_patch=None):
            return [tweak]

    frame = wx.Frame(None) # Never shown; no game files are touched.
    frame.config_layout = VLayout()
    frame.style_patcher = Mock()
    frame.check_patcher = Mock()
    frame.gPatchers = Mock()
    panel = _TestPanel(None)
    try:
        assert panel.native_init(frame, patch_configs={})
        assert not panel.native_init(frame, patch_configs={}, recreate=False)
        assert panel.gList.lb_get_items_count() == 1
        assert panel.gList.lb_is_checked_at_index(0)
        panel._item_search.text_content = 'missing'
        wx.Yield()
        assert panel.gList.lb_get_items_count() == 0
        panel._item_search.text_content = 'DENSITY' if is_tweak else 'SOURCE'
        wx.Yield()
        assert panel.gList.lb_get_items_count() == 1
        panel.mass_select(False)
        assert not panel.gList.lb_is_checked_at_index(0)
        assert not panel.isEnabled
        panel.mass_select(True)
        assert panel.gList.lb_is_checked_at_index(0)
        assert panel.isEnabled
    finally:
        panel.native_destroy()
        frame.Destroy()
