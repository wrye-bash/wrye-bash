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
"""This module is responsible for setting the game module to be used in the
current session. Exports the somewhat unfortunately named `game` GameInfo
instance, which encapsulates static info on current game for the rest of
Bash to use, so must be imported and run high up in the booting sequence.
"""

# Imports ---------------------------------------------------------------------
import collections
import textwrap
from . import bass
from . import game as game_init
from .bolt import GPath, Path, deprint, dict_sort
from .env import get_registry_game_path, get_win_store_game_path
from .exception import BoltError
from .game import patch_game

# Game detection --------------------------------------------------------------
game = None         # type: patch_game.PatchGame
foundGames = {}     # {'name': Path} dict used by the Settings switch game menu

# Module Cache
_allGames = {}        # 'name' -> GameInfo
_registryGames = {}   # 'name' -> path
_win_store_games = {} # 'name' -> path

def reset_bush_globals():
    global game
    game = None
    for d in (_allGames, _registryGames):
        d.clear()

def _supportedGames():
    """Set games supported by Bash and return their paths from the registry."""
    # rebuilt cache
    reset_bush_globals()
    import pkgutil
    # Detect known games from the registry and Windows Store
    for importer, modname, ispkg in pkgutil.iter_modules(game_init.__path__):
        if not ispkg: continue # game support modules are packages
        # Equivalent of "from game import <modname>"
        try:
            module = __import__(u'game',globals(),locals(),[modname],-1)
            game_type = getattr(module, modname).GAME_TYPE
            _allGames[game_type.displayName] = game_type
            # Get this game's install path(s)
            registry_path = get_registry_game_path(game_type)
            win_store_path = get_win_store_game_path(game_type)
        except (ImportError, AttributeError):
            deprint(u'Error in game support module:', modname, traceback=True)
            continue
        # If we have the same game in multiple places, let the registry win.
        # This shouldn't happen since the MS versions are separate WB games
        if registry_path:
            _registryGames[game_type.displayName] = registry_path
        elif win_store_path:
            _win_store_games[game_type.displayName] = win_store_path
        del module
    # unload some modules, _supportedGames is meant to run once
    del pkgutil
    # Dump out info about all games that we *could* launch, but wrap it
    deprint(u'The following games are supported by this version of Wrye Bash:')
    all_supported_games = u', '.join(sorted(_allGames))
    for wrapped_line in textwrap.wrap(all_supported_games):
        deprint(u' ' + wrapped_line)
    # Dump out info about all games that we *actually* found
    deprint(u'Wrye Bash looked for games in the following places:')
    deprint(u' 1. Windows Registry:')
    if _registryGames:
        deprint(u'  The following installed games were found via the '
                u'registry:')
        for found_name, found_path in dict_sort(_registryGames):
            deprint(u'   %s: %s' % (found_name, found_path))
    else:
        deprint(u'  No installed games were found via the registry')
    for wrapped_line in textwrap.wrap(
            u'Make sure to run the launcher of each game you installed through '
            u'Steam once, otherwise Wrye Bash will not be able to find it.'):
        deprint(u'  ' + wrapped_line)
    deprint(u' 2. Windows Store:')
    if _win_store_games:
        deprint(u'  The following installed games with modding enabled were '
                u'found via the Windows Store:')
        for found_name, found_path in dict_sort(_win_store_games):
            deprint(u'   %s: %s' % (found_name, found_path))
    else:
        deprint(u'  No installed games with modding enabled were found via '
                u'the Windows Store.')
    for wrapped_line in textwrap.wrap(
            u'Make sure to enable mods for each Windows Store game you have '
            u'installed, otherwise Wrye Bash will not be able to find it.'):
        deprint(u'  ' + wrapped_line)
    # Join the dicts of games we found from all global sources, PY3: dict union
    all_found_games = _registryGames.copy()
    all_found_games.update(_win_store_games)
    return all_found_games

def _detectGames(cli_path=u'', bash_ini_=None):
    """Detect which supported games are installed.

    - If Bash supports no games raise.
    - For each game supported by Bash check for a supported game executable
    in the following dirs, in decreasing precedence:
       - the path provided by the -o cli argument if any
       - the sOblivionPath bash ini entry if present
       - one directory up from Mopy
    If a game exe is found update the path to this game and return immediately.
    Return (foundGames, gamename)
      - foundGames: a dict from supported games to their paths (the path will
      default to the windows registry path to the game, if present)
      - gamename: the game found in the first installDir or None if no game was
      found - a 'suggestion' for a game to use.
    """
    #--Find all supported games and all games in the windows registry
    foundGames_ = _supportedGames() # sets _allGames if not set
    if not _allGames: # if allGames is empty something goes badly wrong
        raise BoltError(_(u'No game support modules found in Mopy/bash/game.'))
    # check in order of precedence the -o argument, the ini and our parent dir
    installPaths = collections.OrderedDict() #key->(path, found msg, error msg)
    #--First: path specified via the -o command line argument
    if cli_path != u'':
        test_path = GPath(cli_path)
        if not test_path.isabs():
            test_path = Path.getcwd().join(test_path)
        installPaths[u'cmd'] = (test_path,
            u'Set game mode to %(gamename)s specified via -o argument: ',
            u'No known game in the path specified via -o argument: '
            u'%(path)s')
    #--Second: check if sOblivionPath is specified in the ini
    ini_game_path = bass.get_ini_option(bash_ini_, u'sOblivionPath')
    if ini_game_path and not ini_game_path == u'.':
        test_path = GPath(ini_game_path.strip())
        if not test_path.isabs():
            test_path = Path.getcwd().join(test_path)
        installPaths[u'ini'] = (test_path,
            u'Set game mode to %(gamename)s based on sOblivionPath setting in '
            u'bash.ini: ',
            u'No known game in the path specified in sOblivionPath ini '
            u'setting: %(path)s')
    #--Third: Detect what game is installed one directory up from Mopy
    test_path = Path.getcwd()
    if test_path.cs[-4:] == u'mopy':
        test_path = GPath(test_path.s[:-5])
        if not test_path.isabs():
            test_path = Path.getcwd().join(test_path)
        installPaths[u'upMopy'] = (test_path,
            u'Set game mode to %(gamename)s found in parent directory of '
            u'Mopy: ',
            u'No known game in parent directory of Mopy: %(path)s')
    #--Detect
    deprint(u'Detecting games via the -o argument, bash.ini and relative '
            u'path:')
    # iterate installPaths in insert order ('cmd', 'ini', 'upMopy')
    for test_path, foundMsg, errorMsg in installPaths.itervalues():
        for gamename, info in _allGames.items():
            if all(test_path.join(g).exists() for g in info.game_detect_files):
                # Must be this game
                deprint(foundMsg % {u'gamename': gamename}, test_path)
                foundGames_[gamename] = test_path
                return foundGames_, gamename
        # no game exe in this install path - print error message
        deprint(errorMsg % {u'path': test_path})
    # no game found in installPaths - foundGames are the ones from the registry
    return foundGames_, None

def __setGame(gamename, msg):
    """Set bush game globals - raise if they are already set."""
    global game
    if game is not None: raise BoltError(u'Trying to reset the game')
    gamePath = foundGames[gamename]
    game = _allGames[gamename](gamePath)
    deprint(msg % {u'gamename': gamename}, gamePath)
    # Unload the other modules from the cache
    _allGames.clear()
    game.init()

def detect_and_set_game(cli_game_dir=u'', bash_ini_=None, gname=None):
    if gname is None: # detect available games
        foundGames_, gname = _detectGames(cli_game_dir, bash_ini_)
        foundGames.update(foundGames_) # set the global name -> game path dict
    if gname is not None: # try the game returned by detectGames() or specified
        __setGame(gname, u' Using %(gamename)s game:')
        return None
    elif len(foundGames) == 1:
        __setGame(next(iter(foundGames)), u'Single game found [%(gamename)s]:')
        return None
    # No match found, return the list of possible games (may be empty if
    # nothing is found in registry)
    game_icons = {g: bass.dirs[u'images'].join(g + u'32.png').s
                  for g in foundGames}
    return game_icons

def game_path(display_name): return foundGames[display_name]
