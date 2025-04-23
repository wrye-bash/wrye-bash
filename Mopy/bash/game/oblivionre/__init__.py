from os.path import join as _j

from .. import GameInfo
from ..oblivion import AOblivionGameInfo
from ..store_mixins import SteamMixin

class _AOblivionReGameInfo(AOblivionGameInfo):
    display_name = 'Oblivion Remastered'
    # TODO(OblivionRE): I did a preliminary scan of all fsName usages and
    #  added 'OblivionRE' where obviously correct, but I might've missed some
    fsName = 'OblivionRE'
    altName = 'Wrye Bash Remastered'
    bash_root_prefix = 'OblivionRE'
    bak_game_name = 'OblivionRE'
    my_games_name = 'Oblivion Remastered'
    # TODO(OblivionRE): plugins.txt is in the Data folder...
    appdata_name = ''
    game_detect_includes = {'OblivionRemastered'}
    game_detect_excludes = set()
    # TODO(OblivionRE): This is used for display as well... split this into two
    #  variables, one for "Data folder name" and one for "Path to folder that
    #  contains the Data folder name"
    mods_dir = _j('OblivionRemastered', 'Content', 'Dev', 'ObvData', 'Data')
    nexusUrl = 'https://www.nexusmods.com/games/oblivionremastered/'
    nexusName = 'Oblivion Remastered Nexus'
    nexusKey = 'bash.installers.openOblivionRemasteredNexus.continue'

    has_standalone_pluggy = False
    check_legacy_paths = False
    has_obmm = False

    class Ck(GameInfo.Ck): # TODO(OblivionRE): No CS - ever?
        pass

    class Se(GameInfo.Se): # TODO(OblivionRE): No SE for now
        pass

    class Ge(GameInfo.Ge):
        pass

    class Ess(GameInfo.Ess): # TODO(OblivionRE): Save editing disabled for safety right now
        canReadBasic = False # TODO(OblivionRE): New save format
        ext = '.sav'

    class Xe(GameInfo.Xe): # TODO(OblivionRE): No xEdit arg yet
        pass

    # TODO(OblivionRE): Does Bain need updates?

    class Esp(AOblivionGameInfo.Esp):
        # TODO(OblivionRE): All editing disabled until we update this
        canBash = False
        canEditHeader = False

    # TODO(OblivionRE): Update bethDataFiles and vanilla_files

    @classmethod
    def init(cls, _package_name=None):
        super().init(_package_name or __name__)

class SteamOblivionReGameInfo(SteamMixin, _AOblivionReGameInfo):
    class St(_AOblivionReGameInfo.St):
        steam_ids = [2623190]

GAME_TYPE = SteamOblivionReGameInfo
