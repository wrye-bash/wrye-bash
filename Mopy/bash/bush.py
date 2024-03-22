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
#  Wrye Bash copyright (C) 2005-2009 Wrye, 2010-2024 Wrye Bash Team
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
from .env import get_egs_game_paths, get_legacy_ws_game_info, \
    get_legacy_ws_game_paths, get_gog_game_paths, get_ws_game_paths, \
    get_steam_game_paths, get_file_version, get_game_version_fallback, \
    get_disc_game_paths
from .exception import BoltError
from .game import GameInfo, patch_game

# Game detection --------------------------------------------------------------
game: patch_game.PatchGame | None = None
ws_info: 'env._LegacyWinAppInfo' | None = None
foundGames: dict[str, Path] = {} # dict used by the Settings switch game menu

# Module Cache
_allGames: dict[str, type[GameInfo]] = {}
_steam_games: dict[str, list[Path]] = {}
_gog_games: dict[str, list[Path]] = {}
_disc_games: dict[str, list[Path]] = {}
_ws_legacy_games: dict[str, list[Path]] = {}
_ws_games: dict[str, list[Path]] = {}
_egs_games: dict[str, list[Path]] = {}

def reset_bush_globals():
    global game
    global ws_info
    game = None
    ws_info = None
    for d in (_allGames, _steam_games, _gog_games, _ws_legacy_games, _ws_games,
              _egs_games):
        d.clear()

def _print_found_games(game_dict):
    """Formats and prints the specified dictionary of game detections in a
    human-readable way."""
    msgs = []
    for found_name, found_paths in dict_sort(game_dict):
        if len(found_paths) == 1:
            # Single path, just print the name and path
            msgs.append(f'   - {found_name}: {found_paths[0]}')
        else:
            # Multiple paths, format as a multiline list
            msg = f'   - {found_name}: [{found_paths[0]},\n'
            # 8 == len('   - : [')
            space_padding = u' ' * (8 + len(found_name))
            msg += '\n'.join(f'{space_padding}{p},' for p in found_paths[1:-1])
            msg += f'\n{space_padding}{found_paths[-1]}]'
            msgs.append(msg)
    return msgs

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
        for gt_display_name, game_type in game_types.items():
            steam_paths = get_steam_game_paths(game_type)
            if steam_paths:
                _steam_games[gt_display_name] = steam_paths
            gog_paths = get_gog_game_paths(game_type)
            if gog_paths:
                _gog_games[gt_display_name] = gog_paths
            disc_paths = get_disc_game_paths(game_type, _steam_games.values(),
                _gog_games.values())
            if disc_paths:
                _disc_games[gt_display_name] = disc_paths
            ws_legacy_paths = get_legacy_ws_game_paths(game_type)
            if ws_legacy_paths:
                _ws_legacy_games[gt_display_name] = ws_legacy_paths
            if not skip_ws_games:
                ws_paths = get_ws_game_paths(game_type)
                if ws_paths:
                    _ws_games[gt_display_name] = ws_paths
            egs_paths = get_egs_game_paths(game_type)
            if egs_paths:
                _egs_games[gt_display_name] = egs_paths
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
    msg.append('Wrye Bash looked for installations of supported games in the '
               'following places:')
    msg.append(' 1. Steam:')
    if _steam_games:
        msg.append('  The following supported games were found via Steam:')
        msg.extend(_print_found_games(_steam_games))
    else:
        msg.append('  No supported games were found via Steam.')
    msg.append(' 2. GOG (via Windows Registry):')
    if _gog_games:
        msg.append('  The following supported games were found via GOG:')
        msg.extend(_print_found_games(_gog_games))
    else:
        msg.append('  No supported games were found via GOG.')
    msg.append(' 3. Disc Versions (via Windows Registry):')
    if _disc_games:
        msg.append('  The following disc versions of supported games were '
                   'found:')
        msg.extend(_print_found_games(_disc_games))
    else:
        msg.append('  No disc versions of supported games were found.')
    msg.append(' 4. Windows Store (Legacy):')
    if _ws_legacy_games:
        msg.append('  The following supported games with modding enabled were '
                   'found via the legacy Windows Store:')
        msg.extend(_print_found_games(_ws_legacy_games))
    else:
        msg.append('  No supported games with modding enabled were found via '
                   'the legacy Windows Store.')
    msg.append(' 5. Windows Store:')
    if skip_ws_games:
        msg.append('  Windows Store game detection was disabled via bash.ini.')
    elif _ws_games:
        msg.append('  The following supported games were found via the '
                   'Windows Store:')
        msg.extend(_print_found_games(_ws_games))
    else:
        msg.append('  No supported games were found via the Windows Store.')
    msg.append(' 6. Epic Games Store:')
    if _egs_games:
        msg.append('  The following supported games were found via the Epic '
                   'Games Store:')
        msg.extend(_print_found_games(_egs_games))
    else:
        msg.append('  No supported games were found via the Epic Games '
                   'Store.')
    deprint('\n'.join(msg))
    # Merge the dicts of games we found from all global sources
    all_found_games = _steam_games.copy()
    def merge_games(to_merge_games):
        """Helper method for merging games and install paths from various
        sources into the final all_found_games dict."""
        for found_game, found_paths in to_merge_games.items():
            if found_game in all_found_games:
                all_found_games[found_game].extend(found_paths)
            else:
                all_found_games[found_game] = found_paths
    merge_games(_gog_games)
    merge_games(_disc_games)
    merge_games(_ws_legacy_games)
    merge_games(_ws_games)
    merge_games(_egs_games)
    return all_found_games

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
            cli_path = Path.getcwd().join(cli_path)
        installPaths['cmd'] = (cli_path,
            'Set game mode to %(gamename)s specified via -o argument: ',
            'No known game in the path specified via -o argument: %(path)s')
    #--Second: check if sOblivionPath is specified in the ini
    if ini_game_path := bass.get_path_from_ini('OblivionPath', 'mopy'):
        installPaths['ini'] = (ini_game_path,
            'Set game mode to %(gamename)s based on sOblivionPath setting in '
            'bash.ini: ',
            'No known game in the path specified in sOblivionPath ini '
            'setting: %(path)s')
    #--Third: Detect what game is installed one directory up from Mopy
    one_up_path = GPath(bass.dirs['mopy']).head
    if not one_up_path.is_absolute():
        one_up_path = Path.getcwd().join(one_up_path)
    installPaths['upMopy'] = (one_up_path,
        'Set game mode to %(gamename)s found in parent directory of '
        'Mopy: ',
        'No known game in parent directory of Mopy: %(path)s')
    #--Detect
    deprint('Detecting games via the -o argument, bash.ini and relative path:')
    # iterate installPaths in insert order ('cmd', 'ini', 'upMopy')
    for test_path, foundMsg, errorMsg in installPaths.values():
        for gamename, info in _allGames.items():
            if info.test_game_path(test_path):
                # Must be this game
                deprint(foundMsg % {u'gamename': gamename}, test_path)
                foundGames_[gamename] = [test_path]
                return foundGames_, gamename, test_path
        # no game exe in this install path - print error message
        deprint(errorMsg % {u'path': test_path})
    # no game found in installPaths - foundGames are the ones from the registry
    return foundGames_, None, None

def __setGame(gamename, gamePath, msg):
    """Set bush game globals - raise if they are already set."""
    global game
    global ws_info
    if game is not None or ws_info is not None:
        raise BoltError(u'Trying to reset the game')
    game = _allGames[gamename](gamePath)
    ws_info = get_legacy_ws_game_info(game)
    deprint(msg % {u'gamename': gamename}, gamePath)
    # Unload the other modules from the cache
    _allGames.clear()
    game.init()

def detect_and_set_game(cli_game_dir, gname=None, gm_path=None):
    if gname is None: # detect available games
        foundGames_, gname, gm_path = _detectGames(cli_game_dir)
        foundGames.update(foundGames_) # set the global name -> game path dict
    # Try the game returned by detectGames() or specified
    if gname is not None and gm_path is not None:
        __setGame(gname, gm_path, u'Using %(gamename)s game:')
        return None
    elif len(foundGames) == 1 and len(next(iter(foundGames))) == 1:
        single_game = next(iter(foundGames))
        __setGame(single_game, next(iter(foundGames[single_game])),
                  u'Single game found [%(gamename)s]:')
        return None
    # No match found, return the list of possible games (may be empty if
    # nothing is found in registry)
    return {_allGames[found_game]: fg_path for found_game, fg_path
            in foundGames.items()}

def game_path(target_unique_dn): return foundGames[target_unique_dn]

def game_version():
    """Get the game version - be careful about Windows Store versions."""
    test_path = bass.dirs['app'].join(game.version_detect_file)
    try:
        gver = get_file_version(test_path.s)
        if gver == (0, 0, 0, 0) and ws_info.installed:
            gver = get_game_version_fallback(test_path, ws_info)
    except OSError:
        gver = get_game_version_fallback(test_path, ws_info)
    return gver
