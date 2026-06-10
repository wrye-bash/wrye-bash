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
"""This module is responsible for setting the game module to be used in the
current session. Exports the somewhat unfortunately named `game` GameInfo
instance, which encapsulates static info on current game for the rest of
Bash to use, so must be imported and run high up in the booting sequence.
"""
from __future__ import annotations

import pkgutil
from collections import defaultdict

from . import game as game_init, bass
from .bolt import GPath, Path, deprint, dict_sort
from .env import get_file_version, get_game_paths_from_stores, \
    get_game_version_fallback, get_legacy_ws_game_info
from .exception import BoltError
from .game import GameInfo, patch_game

# Game detection --------------------------------------------------------------
game: patch_game.PatchGame = None
ws_info: 'env._LegacyWinAppInfo | None' = None
foundGames: dict[str, list[Path]] = {} # dict used by the Settings switch game menu

# Module Cache
_allGames: dict[str, type[GameInfo]] = {}
# we currently don't really need to cache this - I keep it just for debugging
# store -> (game display name -> paths list)
_game_stores: dict[str, dict[str, list[Path]]] = defaultdict(dict)

def reset_bush_globals():
    global game
    global ws_info
    game = None
    ws_info = None
    for d in (_allGames, _game_stores):
        d.clear()

def _print_found_games(skip_ws_games, msg):
    """Formats and prints the specified dictionary of game detections in a
    human-readable way."""
    msg.append('Wrye Bash looked for installations of supported games in the '
               'following places:')
    succ_err = _store_msgs(skip_ws_games)
    for game_st, (found_m, not_found_m) in succ_err.items():
        if not (found := _game_stores.get(game_st)):
            msg.append(f'{game_st}  {not_found_m}')
            continue
        msg.append(f'{game_st}  {found_m}')
        for found_name, found_paths in dict_sort(found):
            if len(found_paths) == 1:
                # Single path, just print the name and path
                msg.append(f'   - {found_name}: {found_paths[0]}')
                continue
            # Multiple paths, format as a multiline list
            msg.append(f'   - {found_name}: [{found_paths[0]},')
            space_padding = ' ' * (8 + len(found_name)) # 8 == len('   - : [')
            li = ',\n'.join(f'{space_padding}{p}' for p in found_paths[1:])
            msg.append(f'{li}]')

def _store_msgs(skip_ws_games):
    return {
        ' 1. Steam:': (
            'The following supported games were found via Steam:',
            'No supported games were found via Steam.'),
        ' 2. GOG (via Windows Registry):': (
            'The following supported games were found via GOG:',
            'No supported games were found via GOG.'),
        ' 3. Disc Versions (via Windows Registry):': (
            'The following disc versions of supported games were found:',
            'No disc versions of supported games were found.'),
        ' 4. Windows Store (Legacy):': (
            'The following supported games with modding enabled were found '
            'via the legacy Windows Store:',
            'No supported games with modding enabled were found via the legacy '
            'Windows Store.'),
        ' 5. Windows Store:': (
            'The following supported games were found via the Windows Store:',
            'Windows Store game detection was disabled via bash.ini.' if
            skip_ws_games else 'No supported games were found via the '
                               'Windows Store.'),
        ' 6. Epic Games Store:': (
            'The following supported games were found via the Epic Games Store:',
            'No supported games were found via the Epic Games Store.'),
    }

def _supportedGames(skip_ws_games=False):
    """Set games supported by Bash and return their paths from the registry."""
    # rebuilt cache
    reset_bush_globals()
    # Detect known games from the registry and Windows Store
    for _importer, modname, ispkg in pkgutil.iter_modules(game_init.__path__):
        if not ispkg: continue # game support modules are packages
        # Equivalent of "from game import <modname>"
        try:
            module = __import__('game', globals(), locals(), [modname], 1)
            module_container = getattr(module, modname)
            if not hasattr(module_container, 'GAME_TYPE'):
                # PyInstaller's iter_modules gives us an __init__.py file with
                # ispkg=True, skip it
                continue
            gtype = module_container.GAME_TYPE
            game_types = gtype if isinstance(gtype, dict) else {
                gtype.unique_display_name: gtype}
            _allGames.update(game_types)
        except (ImportError, AttributeError):
            deprint(f'Error in game support module {modname}', traceback=True)
            continue
        # Get this game's install path(s)
        get_game_paths_from_stores(game_types, skip_ws_games, _game_stores)
        del module
    # Dump out info about all games that we *could* launch, but deduplicate for
    # games with versions from multiple store fronts
    ##: This is pretty hacky - these should be 'variants' instead (see also the
    # hack in settings_dialog)
    msg = ['The following games are supported by this version of Wrye Bash:']
    deduped_games = defaultdict(set)
    for g, _v in dict_sort(_allGames):
        g_split = g.split('(')
        base_game_name = g_split[0].strip()
        if len(g_split) > 1:
            deduped_games[base_game_name].add(g_split[1][:-1])
        else:
            deduped_games[base_game_name].add('Unknown')
    for base_game_name, game_variants in deduped_games.items():
        fmt_game_variants = ', '.join(sorted(game_variants))
        msg.append(f'  - {base_game_name} ({fmt_game_variants})')
    # Dump out info about all games that we *actually* found
    _print_found_games(skip_ws_games, msg)
    deprint('\n'.join(msg))
    # Merge the dicts of games we found from all global sources
    all_found_games = defaultdict(list)
    for to_merge_games in _game_stores.values():
        for found_game, found_paths in to_merge_games.items():
            all_found_games[found_game].extend(found_paths)
    return all_found_games

_succ_err = {
    'cmd': ('Set game mode to %(gamename)s specified via -o argument: ',
            'No known game in the path specified via -o argument: %(path)s'),
    'ini': ('Set game mode to %(gamename)s based on sOblivionPath setting in '
            'bash.ini: ',
            'No known game in the path specified in sOblivionPath ini '
            'setting: %(path)s'),
    'upMopy': ('Set game mode to %(gamename)s found in parent directory of '
               'Mopy: ',
               'No known game in parent directory of Mopy: %(path)s')}

def _detectGames(cli_path_arg: str = '') -> tuple[
        dict[str, list[Path]], str | None, Path | None]:
    """Detect which supported games are installed.

    - If Bash supports no games raise.
    - For each game supported by Bash check for a supported game executable
    in the following dirs, in decreasing precedence:
       - the path provided by the -o cli argument if any
       - the sOblivionPath bash ini entry if present
       - one directory up from Mopy
    If a game exe is found update the path to this game and return immediately.
    Return (foundGames, gamename, test_path)
      - foundGames: a dict from supported games to their paths (the path will
      default to the windows registry path to the game, if present)
      - gamename: the game found in the first installDir or None if no game was
      - test_path: Path to the game directory that was tested for `gamename`.
    """
    #--Find all supported games and all games installed via various sources
    if not bass.mopy_dirs_initialized:
        raise BoltError('_detectGames: Mopy dirs uninitialized')
    skip_new_ws = bass.inisettings['SkipWSDetection']
    # _supportedGames sets _allGames if not set
    foundGames_ = _supportedGames(skip_new_ws)
    if not _allGames: # if allGames is empty something goes badly wrong
        raise BoltError('No game support modules found in Mopy/bash/game.')
    # check in order of precedence the -o argument, the ini and our parent dir
    installPaths = {} # key -> (path, found msg, error msg)
    #--First: path specified via the -o command line argument
    if cli_path_arg:
        cli_path = GPath(cli_path_arg)
        if not cli_path.is_absolute():
            cli_path = bass.dirs['mopy'].join(cli_path)
        installPaths['cmd'] = cli_path
    #--Second: check if sOblivionPath is specified in the ini
    if ini_game_path := bass.get_path_from_ini('OblivionPath', 'mopy'):
        installPaths['ini'] = ini_game_path
    #--Third: Detect what game is installed one directory up from Mopy
    one_up_path = GPath(bass.dirs['mopy']).head
    if not one_up_path.is_absolute():
        one_up_path = bass.dirs['mopy'].join(one_up_path)
    installPaths['upMopy'] = one_up_path
    #--Detect
    deprint('Detecting games via the -o argument, bash.ini and relative path:')
    # iterate installPaths in insert order ('cmd', 'ini', 'upMopy')
    for key, test_path in installPaths.items():
        for gamename, info in _allGames.items():
            if info.test_game_path(test_path):
                # Must be this game
                deprint(_succ_err[key][0] % {'gamename': gamename}, test_path)
                foundGames_[gamename] = [test_path]
                return foundGames_, gamename, test_path
        # no game exe in this install path - print error message
        deprint(_succ_err[key][1] % {'path': test_path})
    # no game found in installPaths - foundGames are the ones from the registry
    return foundGames_, None, None

def __setGame(gamename, gamePath, msg, opts, init_warnings):
    """Set bush game globals - raise if they are already set."""
    global game
    global ws_info
    if game is not None or ws_info is not None:
        raise BoltError(u'Trying to reset the game')
    game = _allGames[gamename](gamePath, opts, init_warnings)
    ws_info = get_legacy_ws_game_info(game)
    deprint(msg % {u'gamename': gamename}, gamePath)
    # Unload the other modules from the cache
    _allGames.clear()
    game.init()

def detect_and_set_game(opts, init_warnings, gname=None, gm_path=None):
    if gname is None: # detect available games
        foundGames_, gname, gm_path = _detectGames(opts.oblivionPath)
        foundGames.update(foundGames_) # set the global name -> game path dict
    # Try the game returned by detectGames() or specified
    if gname is not None and gm_path is not None:
        msg = 'Using %(gamename)s game:'
        __setGame(gname, gm_path, msg, opts, init_warnings)
        return None
    elif len(foundGames) == 1 and len(single_game_paths := next(
            iter(foundGames.values()))) == 1:
        __setGame(next(iter(foundGames)), single_game_paths[0],
                  'Single game found [%(gamename)s]:', opts, init_warnings)
        return None
    # No match found, return the list of possible games (may be empty if
    # nothing is found in registry)
    return {_allGames[found_game]: fg_path for found_game, fg_path
            in foundGames.items()}

def game_path(target_unique_dn): return foundGames[target_unique_dn]

def game_version():
    """Get the game version - be careful about Windows Store versions."""
    test_path = bass.dirs['exe'].join(game.version_detect_file)
    try:
        gver = get_file_version(test_path.s)
        if gver == (0, 0, 0, 0) and ws_info.installed:
            gver = get_game_version_fallback(test_path, ws_info)
    except OSError:
        gver = get_game_version_fallback(test_path, ws_info)
    return gver
