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
#  Wrye Bash copyright (C) 2005-2009 Wrye, 2010-2015 Wrye Bash Team
#  https://github.com/wrye-bash
#
# =============================================================================

"""This module defines static data for use by other modules in the Wrye Bash package.
Its use should generally be restricted to large chunks of data and/or chunks of data
that are used by multiple objects."""

# Imports ---------------------------------------------------------------------
import collections
import struct
import game as game_init
from bolt import GPath, Path, deprint
from env import get_game_path
from exception import BoltError

# Game detection --------------------------------------------------------------
game = None         # type: game_init.GameInfo
game_mod = None     # type: game_init
gamePath = None     # absolute bolt Path to the game directory
foundGames = {}     # {'name': Path} dict used by the Settings switch game menu

# Module Cache
_allGames = {}        # 'name' -> GameInfo
_allModules = {}      # 'name' -> module
_registryGames = {}   # 'name' -> path
_fsName_display = {}
_display_fsName = {}

def _supportedGames(useCache=True):
    """Set games supported by Bash and return their paths from the registry."""
    if useCache and _allGames: return _registryGames.copy()
    # rebuilt cache
    _allGames.clear()
    _registryGames.clear()
    _fsName_display.clear()
    _display_fsName.clear()
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
            game_path = get_game_path(game_type)
        except (ImportError, AttributeError):
            deprint(u'Error in game support module:', modname, traceback=True)
            continue
        if game_path: _registryGames[game_type.fsName] = game_path
        del module
    # unload some modules, _supportedGames is meant to run once
    del pkgutil
    _display_fsName.update({v: k for k, v in _fsName_display.iteritems()})
    deprint(u'Detected the following supported games via Windows Registry:')
    for foundName in _registryGames:
        deprint(u' %s:' % foundName, _registryGames[foundName])
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
    Return (foundGames, name)
      - foundGames: a dict from supported games to their paths (the path will
      default to the windows registry path to the game, if present)
      - name: the game found in the first installDir or None if no game was
      found - a 'suggestion' for a game to use (if no game is specified/found
      via -g argument).
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
    if bash_ini_ and bash_ini_.has_option(u'General', u'sOblivionPath') \
               and not bash_ini_.get(u'General', u'sOblivionPath') == u'.':
        test_path = GPath(bash_ini_.get(u'General', u'sOblivionPath').strip())
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
        for name, info in _allGames.items():
            if test_path.join(info.exe).exists():
                # Must be this game
                deprint(foundMsg % {'gamename': name}, test_path)
                foundGames_[name] = test_path
                return foundGames_, name
        # no game exe in this install path - print error message
        deprint(errorMsg % {'path': test_path.s})
    # no game found in installPaths - foundGames are the ones from the registry
    return foundGames_, None

def __setGame(name, msg):
    """Set bush game globals - raise if they are already set."""
    global gamePath, game, game_mod
    if game is not None: raise BoltError(u'Trying to reset the game')
    gamePath = foundGames[name]
    game = _allGames[name]
    game_mod = _allModules[name]
    deprint(msg % {'gamename': name}, gamePath)
    # Unload the other modules from the cache
    for i in _allGames.keys():
        if i != name:
            del _allGames[i]
            del _allModules[i]  # the keys should be the same
    game.init()

def detect_and_set_game(cli_game_dir=u'', bash_ini_=None, name=None):
    if name is None: # detect available games
        foundGames_, name = _detectGames(cli_game_dir, bash_ini_)
        foundGames.update(foundGames_) # set the global name -> game path dict
    else:
        name = _display_fsName[name] # we are passed a display name in
    if name is not None: # try the game returned by detectGames() or specified
        __setGame(name, u' Using %(gamename)s game:')
        return None
    elif len(foundGames) == 1:
        __setGame(foundGames.keys()[0], u'Single game found [%(gamename)s]:')
        return None
    # No match found, return the list of possible games (may be empty if
    # nothing is found in registry)
    return [_fsName_display[k] for k in foundGames]

def game_path(display_name): return foundGames[_display_fsName[display_name]]
def get_display_name(fs_name): return _fsName_display[fs_name]

# Id Functions ----------------------------------------------------------------
def getIdFunc(modName):
    return lambda x: (GPath(modName),x)

ob = getIdFunc(u'Oblivion.esm')
cobl = getIdFunc(u'Cobl Main.esm')

# Default Eyes/Hair -----------------------------------------------------------
standardEyes = [ob(x) for x in (0x27306,0x27308,0x27309)] + [cobl(x) for x in (0x000821, 0x000823, 0x000825, 0x000828, 0x000834, 0x000837, 0x000839, 0x00084F, )]

defaultEyes = {
    #--Oblivion.esm
    ob(0x23FE9): #--Argonian
        [ob(0x3E91E)] + [cobl(x) for x in (0x01F407, 0x01F408, 0x01F40B, 0x01F40C, 0x01F410, 0x01F411, 0x01F414, 0x01F416, 0x01F417, 0x01F41A, 0x01F41B, 0x01F41E, 0x01F41F, 0x01F422, 0x01F424, )],
    ob(0x0224FC): #--Breton
        standardEyes,
    ob(0x0191C1): #--Dark Elf
        [ob(0x27307)] + [cobl(x) for x in (0x000861,0x000864,0x000851)],
    ob(0x019204): #--High Elf
        standardEyes,
    ob(0x000907): #--Imperial
        standardEyes,
    ob(0x022C37): #--Khajiit
        [ob(0x375c8)] + [cobl(x) for x in (0x00083B, 0x00083E, 0x000843, 0x000846, 0x000849, 0x00084C, )],
    ob(0x0224FD): #--Nord
        standardEyes,
    ob(0x0191C0): #--Orc
        [ob(0x2730A)]+[cobl(x) for x in (0x000853, 0x000855, 0x000858, 0x00085A, 0x00085C, 0x00085E, )],
    ob(0x000D43): #--Redguard
        standardEyes,
    ob(0x0223C8): #--Wood Elf
        standardEyes,
    #--Cobl
    cobl(0x07948): #--cobRaceAureal
        [ob(0x54BBA)],
    cobl(0x02B60): #--cobRaceHidden
        [cobl(x) for x in (0x01F43A, 0x01F438, 0x01F439, 0x0015A7, 0x01792C, 0x0015AC, 0x0015A8, 0x0015AB, 0x0015AA,)],
    cobl(0x07947): #--cobRaceMazken
        [ob(0x54BB9)],
    cobl(0x1791B): #--cobRaceOhmes
        [cobl(x) for x in (0x017901, 0x017902, 0x017903, 0x017904, 0x017905, 0x017906, 0x017907, 0x017908, 0x017909, 0x01790A, 0x01790B, 0x01790C, 0x01790D, 0x01790E, 0x01790F, 0x017910, 0x017911, 0x017912, 0x017913, 0x017914, 0x017915, 0x017916, 0x017917, 0x017918, 0x017919, 0x01791A, 0x017900,)],
    cobl(0x1F43C): #--cobRaceXivilai
        [cobl(x) for x in (0x01F437, 0x00531B, 0x00531C, 0x00531D, 0x00531E, 0x00531F, 0x005320, 0x005321, 0x01F43B, 0x00DBE1, )],
    }

# Magic Info ------------------------------------------------------------------
magicEffects = {
    'ABAT': [5,_(u'Absorb Attribute'),0.95],
    'ABFA': [5,_(u'Absorb Fatigue'),6],
    'ABHE': [5,_(u'Absorb Health'),16],
    'ABSK': [5,_(u'Absorb Skill'),2.1],
    'ABSP': [5,_(u'Absorb Magicka'),7.5],
    'BA01': [1,_(u'Bound Armor Extra 01'),0],#--Formid == 0
    'BA02': [1,_(u'Bound Armor Extra 02'),0],#--Formid == 0
    'BA03': [1,_(u'Bound Armor Extra 03'),0],#--Formid == 0
    'BA04': [1,_(u'Bound Armor Extra 04'),0],#--Formid == 0
    'BA05': [1,_(u'Bound Armor Extra 05'),0],#--Formid == 0
    'BA06': [1,_(u'Bound Armor Extra 06'),0],#--Formid == 0
    'BA07': [1,_(u'Bound Armor Extra 07'),0],#--Formid == 0
    'BA08': [1,_(u'Bound Armor Extra 08'),0],#--Formid == 0
    'BA09': [1,_(u'Bound Armor Extra 09'),0],#--Formid == 0
    'BA10': [1,_(u'Bound Armor Extra 10'),0],#--Formid == 0
    'BABO': [1,_(u'Bound Boots'),12],
    'BACU': [1,_(u'Bound Cuirass'),12],
    'BAGA': [1,_(u'Bound Gauntlets'),8],
    'BAGR': [1,_(u'Bound Greaves'),12],
    'BAHE': [1,_(u'Bound Helmet'),12],
    'BASH': [1,_(u'Bound Shield'),12],
    'BRDN': [0,_(u'Burden'),0.21],
    'BW01': [1,_(u'Bound Order Weapon 1'),1],
    'BW02': [1,_(u'Bound Order Weapon 2'),1],
    'BW03': [1,_(u'Bound Order Weapon 3'),1],
    'BW04': [1,_(u'Bound Order Weapon 4'),1],
    'BW05': [1,_(u'Bound Order Weapon 5'),1],
    'BW06': [1,_(u'Bound Order Weapon 6'),1],
    'BW07': [1,_(u'Summon Staff of Sheogorath'),1],
    'BW08': [1,_(u'Bound Priest Dagger'),1],
    'BW09': [1,_(u'Bound Weapon Extra 09'),0],#--Formid == 0
    'BW10': [1,_(u'Bound Weapon Extra 10'),0],#--Formid == 0
    'BWAX': [1,_(u'Bound Axe'),39],
    'BWBO': [1,_(u'Bound Bow'),95],
    'BWDA': [1,_(u'Bound Dagger'),14],
    'BWMA': [1,_(u'Bound Mace'),91],
    'BWSW': [1,_(u'Bound Sword'),235],
    'CALM': [3,_(u'Calm'),0.47],
    'CHML': [3,_(u'Chameleon'),0.63],
    'CHRM': [3,_(u'Charm'),0.2],
    'COCR': [3,_(u'Command Creature'),0.6],
    'COHU': [3,_(u'Command Humanoid'),0.75],
    'CUDI': [5,_(u'Cure Disease'),1400],
    'CUPA': [5,_(u'Cure Paralysis'),500],
    'CUPO': [5,_(u'Cure Poison'),600],
    'DARK': [3,_(u'DO NOT USE - Darkness'),0],
    'DEMO': [3,_(u'Demoralize'),0.49],
    'DGAT': [2,_(u'Damage Attribute'),100],
    'DGFA': [2,_(u'Damage Fatigue'),4.4],
    'DGHE': [2,_(u'Damage Health'),12],
    'DGSP': [2,_(u'Damage Magicka'),2.45],
    'DIAR': [2,_(u'Disintegrate Armor'),6.2],
    'DISE': [2,_(u'Disease Info'),0], #--Formid == 0
    'DIWE': [2,_(u'Disintegrate Weapon'),6.2],
    'DRAT': [2,_(u'Drain Attribute'),0.7],
    'DRFA': [2,_(u'Drain Fatigue'),0.18],
    'DRHE': [2,_(u'Drain Health'),0.9],
    'DRSK': [2,_(u'Drain Skill'),0.65],
    'DRSP': [2,_(u'Drain Magicka'),0.18],
    'DSPL': [4,_(u'Dispel'),3.6],
    'DTCT': [4,_(u'Detect Life'),0.08],
    'DUMY': [2,_(u'Mehrunes Dagon'),0], #--Formid == 0
    'FIDG': [2,_(u'Fire Damage'),7.5],
    'FISH': [0,_(u'Fire Shield'),0.95],
    'FOAT': [5,_(u'Fortify Attribute'),0.6],
    'FOFA': [5,_(u'Fortify Fatigue'),0.04],
    'FOHE': [5,_(u'Fortify Health'),0.14],
    'FOMM': [5,_(u'Fortify Magicka Multiplier'),0.04],
    'FOSK': [5,_(u'Fortify Skill'),0.6],
    'FOSP': [5,_(u'Fortify Magicka'),0.15],
    'FRDG': [2,_(u'Frost Damage'),7.4],
    'FRNZ': [3,_(u'Frenzy'),0.04],
    'FRSH': [0,_(u'Frost Shield'),0.95],
    'FTHR': [0,_(u'Feather'),0.1],
    'INVI': [3,_(u'Invisibility'),40],
    'LGHT': [3,_(u'Light'),0.051],
    'LISH': [0,_(u'Shock Shield'),0.95],
    'LOCK': [0,_(u'DO NOT USE - Lock'),30],
    'MYHL': [1,_(u'Summon Mythic Dawn Helm'),110],
    'MYTH': [1,_(u'Summon Mythic Dawn Armor'),120],
    'NEYE': [3,_(u'Night-Eye'),22],
    'OPEN': [0,_(u'Open'),4.3],
    'PARA': [3,_(u'Paralyze'),475],
    'POSN': [2,_(u'Poison Info'),0],
    'RALY': [3,_(u'Rally'),0.03],
    'REAN': [1,_(u'Reanimate'),10],
    'REAT': [5,_(u'Restore Attribute'),38],
    'REDG': [4,_(u'Reflect Damage'),2.5],
    'REFA': [5,_(u'Restore Fatigue'),2],
    'REHE': [5,_(u'Restore Health'),10],
    'RESP': [5,_(u'Restore Magicka'),2.5],
    'RFLC': [4,_(u'Reflect Spell'),3.5],
    'RSDI': [5,_(u'Resist Disease'),0.5],
    'RSFI': [5,_(u'Resist Fire'),0.5],
    'RSFR': [5,_(u'Resist Frost'),0.5],
    'RSMA': [5,_(u'Resist Magic'),2],
    'RSNW': [5,_(u'Resist Normal Weapons'),1.5],
    'RSPA': [5,_(u'Resist Paralysis'),0.75],
    'RSPO': [5,_(u'Resist Poison'),0.5],
    'RSSH': [5,_(u'Resist Shock'),0.5],
    'RSWD': [5,_(u'Resist Water Damage'),0], #--Formid == 0
    'SABS': [4,_(u'Spell Absorption'),3],
    'SEFF': [0,_(u'Script Effect'),0],
    'SHDG': [2,_(u'Shock Damage'),7.8],
    'SHLD': [0,_(u'Shield'),0.45],
    'SLNC': [3,_(u'Silence'),60],
    'STMA': [2,_(u'Stunted Magicka'),0],
    'STRP': [4,_(u'Soul Trap'),30],
    'SUDG': [2,_(u'Sun Damage'),9],
    'TELE': [4,_(u'Telekinesis'),0.49],
    'TURN': [1,_(u'Turn Undead'),0.083],
    'VAMP': [2,_(u'Vampirism'),0],
    'WABR': [0,_(u'Water Breathing'),14.5],
    'WAWA': [0,_(u'Water Walking'),13],
    'WKDI': [2,_(u'Weakness to Disease'),0.12],
    'WKFI': [2,_(u'Weakness to Fire'),0.1],
    'WKFR': [2,_(u'Weakness to Frost'),0.1],
    'WKMA': [2,_(u'Weakness to Magic'),0.25],
    'WKNW': [2,_(u'Weakness to Normal Weapons'),0.25],
    'WKPO': [2,_(u'Weakness to Poison'),0.1],
    'WKSH': [2,_(u'Weakness to Shock'),0.1],
    'Z001': [1,_(u'Summon Rufio\'s Ghost'),13],
    'Z002': [1,_(u'Summon Ancestor Guardian'),33.3],
    'Z003': [1,_(u'Summon Spiderling'),45],
    'Z004': [1,_(u'Summon Flesh Atronach'),1],
    'Z005': [1,_(u'Summon Bear'),47.3],
    'Z006': [1,_(u'Summon Gluttonous Hunger'),61],
    'Z007': [1,_(u'Summon Ravenous Hunger'),123.33],
    'Z008': [1,_(u'Summon Voracious Hunger'),175],
    'Z009': [1,_(u'Summon Dark Seducer'),1],
    'Z010': [1,_(u'Summon Golden Saint'),1],
    'Z011': [1,_(u'Wabba Summon'),0],
    'Z012': [1,_(u'Summon Decrepit Shambles'),45],
    'Z013': [1,_(u'Summon Shambles'),87.5],
    'Z014': [1,_(u'Summon Replete Shambles'),150],
    'Z015': [1,_(u'Summon Hunger'),22],
    'Z016': [1,_(u'Summon Mangled Flesh Atronach'),22],
    'Z017': [1,_(u'Summon Torn Flesh Atronach'),32.5],
    'Z018': [1,_(u'Summon Stitched Flesh Atronach'),75.5],
    'Z019': [1,_(u'Summon Sewn Flesh Atronach'),195],
    'Z020': [1,_(u'Extra Summon 20'),0],
    'ZCLA': [1,_(u'Summon Clannfear'),75.56],
    'ZDAE': [1,_(u'Summon Daedroth'),123.33],
    'ZDRE': [1,_(u'Summon Dremora'),72.5],
    'ZDRL': [1,_(u'Summon Dremora Lord'),157.14],
    'ZFIA': [1,_(u'Summon Flame Atronach'),45],
    'ZFRA': [1,_(u'Summon Frost Atronach'),102.86],
    'ZGHO': [1,_(u'Summon Ghost'),22],
    'ZHDZ': [1,_(u'Summon Headless Zombie'),56],
    'ZLIC': [1,_(u'Summon Lich'),350],
    'ZSCA': [1,_(u'Summon Scamp'),30],
    'ZSKA': [1,_(u'Summon Skeleton Guardian'),32.5],
    'ZSKC': [1,_(u'Summon Skeleton Champion'),152],
    'ZSKE': [1,_(u'Summon Skeleton'),11.25],
    'ZSKH': [1,_(u'Summon Skeleton Hero'),66],
    'ZSPD': [1,_(u'Summon Spider Daedra'),195],
    'ZSTA': [1,_(u'Summon Storm Atronach'),125],
    'ZWRA': [1,_(u'Summon Faded Wraith'),87.5],
    'ZWRL': [1,_(u'Summon Gloom Wraith'),260],
    'ZXIV': [1,_(u'Summon Xivilai'),200],
    'ZZOM': [1,_(u'Summon Zombie'),16.67],
    }

_strU = struct.Struct('I').unpack

mgef_school = dict((x, y) for x, [y, z, _num] in magicEffects.items())
mgef_name = dict((x, z) for x, [y, z, __num] in magicEffects.items())
mgef_basevalue = dict((x,a) for x,[y,z,a] in magicEffects.items())
mgef_school.update({_strU(x)[0]:y for x,[y,z,a] in magicEffects.items()})
mgef_name.update({_strU(x)[0]:z for x,[y,z,a] in magicEffects.items()})
mgef_basevalue.update({_strU(x)[0]:a for x,[y,z,a] in magicEffects.items()})

hostileEffects = {
    'ABAT', #--Absorb Attribute
    'ABFA', #--Absorb Fatigue
    'ABHE', #--Absorb Health
    'ABSK', #--Absorb Skill
    'ABSP', #--Absorb Magicka
    'BRDN', #--Burden
    'DEMO', #--Demoralize
    'DGAT', #--Damage Attribute
    'DGFA', #--Damage Fatigue
    'DGHE', #--Damage Health
    'DGSP', #--Damage Magicka
    'DIAR', #--Disintegrate Armor
    'DIWE', #--Disintegrate Weapon
    'DRAT', #--Drain Attribute
    'DRFA', #--Drain Fatigue
    'DRHE', #--Drain Health
    'DRSK', #--Drain Skill
    'DRSP', #--Drain Magicka
    'FIDG', #--Fire Damage
    'FRDG', #--Frost Damage
    'FRNZ', #--Frenzy
    'PARA', #--Paralyze
    'SHDG', #--Shock Damage
    'SLNC', #--Silence
    'STMA', #--Stunted Magicka
    'STRP', #--Soul Trap
    'SUDG', #--Sun Damage
    'TURN', #--Turn Undead
    'WKDI', #--Weakness to Disease
    'WKFI', #--Weakness to Fire
    'WKFR', #--Weakness to Frost
    'WKMA', #--Weakness to Magic
    'WKNW', #--Weakness to Normal Weapons
    'WKPO', #--Weakness to Poison
    'WKSH', #--Weakness to Shock
    }
hostileEffects |= set((_strU(x)[0] for x in hostileEffects))

#Doesn't list mgefs that use actor values, but rather mgefs that have a generic name
#Ex: Absorb Attribute becomes Absorb Magicka if the effect's actorValue field contains 9
#    But it is actually using an attribute rather than an actor value
#Ex: Burden uses an actual actor value (encumbrance) but it isn't listed since its name doesn't change
genericAVEffects = {
    'ABAT', #--Absorb Attribute (Use Attribute)
    'ABSK', #--Absorb Skill (Use Skill)
    'DGAT', #--Damage Attribute (Use Attribute)
    'DRAT', #--Drain Attribute (Use Attribute)
    'DRSK', #--Drain Skill (Use Skill)
    'FOAT', #--Fortify Attribute (Use Attribute)
    'FOSK', #--Fortify Skill (Use Skill)
    'REAT', #--Restore Attribute (Use Attribute)
    }
genericAVEffects |= set((_strU(x)[0] for x in genericAVEffects))

actorValues = [
    _(u'Strength'), #--00
    _(u'Intelligence'),
    _(u'Willpower'),
    _(u'Agility'),
    _(u'Speed'),
    _(u'Endurance'),
    _(u'Personality'),
    _(u'Luck'),
    _(u'Health'),
    _(u'Magicka'),

    _(u'Fatigue'), #--10
    _(u'Encumbrance'),
    _(u'Armorer'),
    _(u'Athletics'),
    _(u'Blade'),
    _(u'Block'),
    _(u'Blunt'),
    _(u'Hand To Hand'),
    _(u'Heavy Armor'),
    _(u'Alchemy'),

    _(u'Alteration'), #--20
    _(u'Conjuration'),
    _(u'Destruction'),
    _(u'Illusion'),
    _(u'Mysticism'),
    _(u'Restoration'),
    _(u'Acrobatics'),
    _(u'Light Armor'),
    _(u'Marksman'),
    _(u'Mercantile'),

    _(u'Security'), #--30
    _(u'Sneak'),
    _(u'Speechcraft'),
    u'Aggression',
    u'Confidence',
    u'Energy',
    u'Responsibility',
    u'Bounty',
    u'UNKNOWN 38',
    u'UNKNOWN 39',

    u'MagickaMultiplier', #--40
    u'NightEyeBonus',
    u'AttackBonus',
    u'DefendBonus',
    u'CastingPenalty',
    u'Blindness',
    u'Chameleon',
    u'Invisibility',
    u'Paralysis',
    u'Silence',

    u'Confusion', #--50
    u'DetectItemRange',
    u'SpellAbsorbChance',
    u'SpellReflectChance',
    u'SwimSpeedMultiplier',
    u'WaterBreathing',
    u'WaterWalking',
    u'StuntedMagicka',
    u'DetectLifeRange',
    u'ReflectDamage',

    u'Telekinesis', #--60
    u'ResistFire',
    u'ResistFrost',
    u'ResistDisease',
    u'ResistMagic',
    u'ResistNormalWeapons',
    u'ResistParalysis',
    u'ResistPoison',
    u'ResistShock',
    u'Vampirism',

    u'Darkness', #--70
    u'ResistWaterDamage',
    ]

acbs = {
    u'Armorer': 0,
    u'Athletics': 1,
    u'Blade': 2,
    u'Block': 3,
    u'Blunt': 4,
    u'Hand to Hand': 5,
    u'Heavy Armor': 6,
    u'Alchemy': 7,
    u'Alteration': 8,
    u'Conjuration': 9,
    u'Destruction': 10,
    u'Illusion': 11,
    u'Mysticism': 12,
    u'Restoration': 13,
    u'Acrobatics': 14,
    u'Light Armor': 15,
    u'Marksman': 16,
    u'Mercantile': 17,
    u'Security': 18,
    u'Sneak': 19,
    u'Speechcraft': 20,
    u'Health': 21,
    u'Strength': 25,
    u'Intelligence': 26,
    u'Willpower': 27,
    u'Agility': 28,
    u'Speed': 29,
    u'Endurance': 30,
    u'Personality': 31,
    u'Luck': 32,
    }

# Save File Info --------------------------------------------------------------
saveRecTypes = {
    6 : _(u'Faction'),
    19: _(u'Apparatus'),
    20: _(u'Armor'),
    21: _(u'Book'),
    22: _(u'Clothing'),
    25: _(u'Ingredient'),
    26: _(u'Light'),
    27: _(u'Misc. Item'),
    33: _(u'Weapon'),
    35: _(u'NPC'),
    36: _(u'Creature'),
    39: _(u'Key'),
    40: _(u'Potion'),
    48: _(u'Cell'),
    49: _(u'Object Ref'),
    50: _(u'NPC Ref'),
    51: _(u'Creature Ref'),
    58: _(u'Dialog Entry'),
    59: _(u'Quest'),
    61: _(u'AI Package'),
    }

#--Cleanup --------------------------------------------------------------------
#------------------------------------------------------------------------------
del _strU
