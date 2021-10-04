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
#  Wrye Bash copyright (C) 2005-2009 Wrye, 2010-2021 Wrye Bash Team
#  https://github.com/wrye-bash
#
# =============================================================================
"""Sets up the necessary environment to run Wrye Bash tests. This whole file is
quite hacky, but running tests for WB is going to be a bit hacky no matter
what."""

import os
import toml
import traceback

import wx as _wx

class FailedTest(Exception):
    """Misc exception for when a test should fail for meta reasons."""

_meta_cache = {}
def get_meta_value(base_file_path, meta_key):
    """Returns the value corresponding to the given meta key from the meta file
    for the specified file. Gives helpful error messages if the file is
    missing, malformed, is missing the specified key, etc."""
    base_file_path = u'%s' % base_file_path # To support bolt.Path as well
    meta_file = base_file_path + u'.meta'
    try:
        parsed_meta = _meta_cache[base_file_path]
    except KeyError:
        try:
            parsed_meta = _meta_cache[base_file_path] = toml.load(meta_file)
        except TypeError: # File is missing
            raise FailedTest(u'%s is missing a .meta file.' % base_file_path)
        except toml.TomlDecodeError: # File has incorrect syntax
            traceback.print_exc()
            raise FailedTest(u'%s has malformed TOML syntax. Check the log '
                             u'for a traceback pointing to the '
                             u'problem.' % meta_file)
    try:
        return parsed_meta[meta_key]
    except KeyError:
        raise FailedTest(u"%s is missing the key '%s'" % (meta_file, meta_key))

def iter_games(resource_subfolder):
    """Yields all games for which resources from the specified subfolder are
    available."""
    full_subfolder = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                  u'test_resources', resource_subfolder)
    for game_folder in os.listdir(full_subfolder):
        # Don't return README.md as a game
        if os.path.isdir(os.path.join(full_subfolder, game_folder)):
            yield game_folder

def iter_resources(resource_subfolder, filter_by_game=frozenset()):
    """Yields all resources in the specified test_resources subfolder. Note
    that absolute paths are returned, as the intended use case of this method
    is for testing AFile-based classes.

    :param filter_by_game: If nonempty, limits yielded resources to ones from
        that game's subfolder only."""
    full_subfolder = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                  u'test_resources', resource_subfolder)
    for game_folder in os.listdir(full_subfolder):
        if filter_by_game and game_folder not in filter_by_game: continue
        full_game_folder = os.path.join(full_subfolder, game_folder)
        for resource_file in os.listdir(full_game_folder):
            yield os.path.join(full_game_folder, resource_file)

# Here be hacks ---------------------------------------------------------------
# Maps the resource subfolder game names back to displayNames
resource_to_displayName = {
    u'enderal': u'Enderal',
    u'enderalse': u'Enderal Special Edition',
    u'fallout3': u'Fallout 3',
    u'fallout4': u'Fallout 4',
    u'fallout4vr': u'Fallout 4 VR',
    u'falloutnv': u'Fallout New Vegas',
    u'morrowind': u'Morrowind',
    u'oblivion': u'Oblivion',
    u'skyrim': u'Skyrim',
    u'skyrimse': u'Skyrim Special Edition',
    u'skyrimvr': u'Skyrim VR',
    u'ws_fallout4': u'Fallout 4 (WS)',
    u'ws_morrowind': u'Morrowind (WS)',
    u'ws_oblivion': u'Oblivion (WS)',
    u'ws_skyrimse': u'Skyrim Special Edition (WS)',
}
# Cache for created and initialized GameInfos
_game_cache = {}
def set_game(game_fsName):
    """Hotswitches bush.game to the game with the specified resource subfolder
    name."""
    # noinspection PyProtectedMember
    try:
        bush.game = _game_cache[game_fsName]
    except KeyError:
        bush.game = new_game = bush._allGames[game_fsName](u'')
        from .. import brec
        brec.MelModel = None
        new_game.init()
        _game_cache[game_fsName] = new_game

def _emulate_startup():
    """Emulates a normal Wrye Bash startup, but without launching basher
    etc."""
    # bush needs _() to be available, so need to do it like this
    global bush
    from .. import localize
    app = _wx.App()
    localize.setup_locale(u'English', _wx)
    from .. import bush
    # noinspection PyProtectedMember
    bush._supportedGames()
    set_game(u'Oblivion') # just need to pick one to start

_emulate_startup()
