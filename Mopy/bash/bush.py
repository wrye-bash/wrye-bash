# -*- coding: utf-8 -*-
#
# GPL License and Copyright Notice ============================================
#  This file is part of Wrye Bash.
#
#  Wrye Bash is free software; you can redistribute it and/or
#  modify it under the terms of the GNU General Public License
#  as published by the Free Software Foundation; either version 2
#  of the License, or (at your option) any later version.
#
#  Wrye Bash is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
#
#  You should have received a copy of the GNU General Public License
#  along with Wrye Bash; if not, write to the Free Software Foundation,
#  Inc., 59 Temple Place - Suite 330, Boston, MA  02111-1307, USA.
#
#  Wrye Bash copyright (C) 2005-2009 Wrye, 2010-2019 Wrye Bash Team
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
from . import game as game_init
from . import bass
from .bolt import GPath, Path, deprint
from .env import get_registry_game_path
from .exception import BoltError

# Game detection --------------------------------------------------------------
game = None         # type: game_init.GameInfo
game_mod = None     # type: game_init
foundGames = {}     # {'name': Path} dict used by the Settings switch game menu

# Module Cache
_allGames = {}        # 'name' -> GameInfo
_allModules = {}      # 'name' -> module
_registryGames = {}   # 'name' -> path
_fsName_display = {}
_display_fsName = {}

def reset_bush_globals():
    global game, game_mod
    game = game_mod = None
    for d in (_allGames, _allModules, _registryGames, _fsName_display,
              _display_fsName):
        d.clear()

def _supportedGames():
    """Set games supported by Bash and return their paths from the registry."""
    # rebuilt cache
    reset_bush_globals()
    import pkgutil
    # Detect the known games
    for importer, modname, ispkg in pkgutil.iter_modules(game_init.__path__):
        if not ispkg: continue # game support modules are packages
        # Equivalent of "from game import <modname>"
        try:
            module = __import__('game',globals(),locals(),[modname],-1)
            submod = getattr(module,modname)
            game_type = submod.GAME_TYPE
            _allModules[game_type.fsName] = submod
            _allGames[game_type.fsName] = game_type
            _fsName_display[game_type.fsName] = game_type.displayName
            #--Get this game's install path
            registry_path = get_registry_game_path(game_type)
        except (ImportError, AttributeError):
            deprint(u'Error in game support module:', modname, traceback=True)
            continue
        if registry_path: _registryGames[game_type.fsName] = registry_path
        del module
    # unload some modules, _supportedGames is meant to run once
    del pkgutil
    _display_fsName.update({v: k for k, v in _fsName_display.iteritems()})
    # Dump out info about all games that we *could* launch, but wrap it
    deprint(u'The following games are supported by this version of Wrye Bash:')
    all_supported_games = u', '.join(sorted(_display_fsName.keys()))
    for wrapped_line in textwrap.wrap(all_supported_games):
        deprint(u' ' + wrapped_line)
    # Dump out info about all games that we *actually* found
    deprint(u'The following installed games were found via Windows Registry:')
    for found_name in sorted(_registryGames.keys()):
        deprint(u' %s: %s' % (found_name, _registryGames[found_name]))
    return _registryGames.copy()

def _detectGames(cli_path=u'', bash_ini_=None):
    """Detect which supported games are installed.

    - If Bash supports no games raise.
    - For each game supported by Bash check for a supported game executable
    in the following dirs, in decreasing precedence:
       - the path provided by the -o cli argument if any
       - the sOblivionPath Bash Ini entry if present
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
        installPaths['cmd'] = (test_path,
            _(u'Set game mode to %(gamename)s specified via -o argument') +
              u': ',
            _(u'No known game in the path specified via -o argument: ' +
              u'%(path)s'))
    #--Second: check if sOblivionPath is specified in the ini
    ini_game_path = bass.get_ini_option(bash_ini_, u'sOblivionPath')
    if ini_game_path and not ini_game_path == u'.':
        test_path = GPath(ini_game_path.strip())
        if not test_path.isabs():
            test_path = Path.getcwd().join(test_path)
        installPaths['ini'] = (test_path,
            _(u'Set game mode to %(gamename)s based on sOblivionPath setting '
              u'in bash.ini') + u': ',
            _(u'No known game in the path specified in sOblivionPath ini '
              u'setting: %(path)s'))
    #--Third: Detect what game is installed one directory up from Mopy
    test_path = Path.getcwd()
    if test_path.cs[-4:] == u'mopy':
        test_path = GPath(test_path.s[:-5])
        if not test_path.isabs():
            test_path = Path.getcwd().join(test_path)
        installPaths['upMopy'] = (test_path,
            _(u'Set game mode to %(gamename)s found in parent directory of'
              u' Mopy') + u': ',
            _(u'No known game in parent directory of Mopy: %(path)s'))
    #--Detect
    deprint(u'Detecting games via the -o argument, bash.ini and relative path:')
    # iterate installPaths in insert order ('cmd', 'ini', 'upMopy')
    for test_path, foundMsg, errorMsg in installPaths.itervalues():
        for gamename, info in _allGames.items():
            if test_path.join(*info.game_detect_file).exists():
                # Must be this game
                deprint(foundMsg % {'gamename': gamename}, test_path)
                foundGames_[gamename] = test_path
                return foundGames_, gamename
        # no game exe in this install path - print error message
        deprint(errorMsg % {'path': test_path.s})
    # no game found in installPaths - foundGames are the ones from the registry
    return foundGames_, None

def __setGame(gamename, msg):
    """Set bush game globals - raise if they are already set."""
    global game, game_mod
    if game is not None: raise BoltError(u'Trying to reset the game')
    gamePath = foundGames[gamename]
    game = _allGames[gamename](gamePath)
    game_mod = _allModules[gamename]
    deprint(msg % {'gamename': gamename}, gamePath)
    # Unload the other modules from the cache
    _allGames.clear()
    _allModules.clear()
    game.init()

def detect_and_set_game(cli_game_dir=u'', bash_ini_=None, name=None):
    if name is None: # detect available games
        foundGames_, name = _detectGames(cli_game_dir, bash_ini_)
        foundGames.update(foundGames_) # set the global name -> game path dict
    else:
        name = _display_fsName[name] # we are passed a display name in
    if name is not None: # try the game returned by detectGames() or specified
        __setGame(name, u' Using %(gamename)s game:')
        return None, None
    elif len(foundGames) == 1:
        __setGame(foundGames.keys()[0], u'Single game found [%(gamename)s]:')
        return None, None
    # No match found, return the list of possible games (may be empty if
    # nothing is found in registry)
    game_icons = {_fsName_display[g]: bass.dirs['images'].join(g + u'32.png').s
                  for g in foundGames}
    return game_icons.keys(), game_icons

def game_path(display_name): return foundGames[_display_fsName[display_name]]
def get_display_name(fs_name): return _fsName_display[fs_name]
