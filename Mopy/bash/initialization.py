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
"""Functions for initializing Bash data structures on boot. For now exports
functions to initialize bass.dirs that need be initialized high up into the
boot sequence to be able to backup/restore settings."""
from __future__ import annotations

import io
from configparser import ConfigParser, MissingSectionHeaderError

# Local - make sure that all imports here are carefully done in bash.py first
from .bass import dirs, get_path_from_ini
from .bolt import GPath, Path, decoder, deprint, os_name, top_level_dirs
from .env import get_legacy_ws_game_info, get_local_app_data_path, \
    get_personal_path, shellMakeDirs, is_case_sensitive, \
    get_case_sensitivity_advice
from .exception import BoltError, NonExistentDriveError
# no other Bash imports!

mopy_dirs_initialized = bash_dirs_initialized = False

def _get_ini_option(ini_parser, option_key) -> str | None:
    if not ini_parser:
        return None
    # logic for getting the path from the ini - get(section, key,
    # fallback=default). section is case sensitive - key is not
    return ini_parser.get('General', option_key, fallback=None)

def _get_cli_ini_path(my_docs_path, cli_switch, ini_path_key, game_info,
                      fallback, fail_msg, not_exists_msg):
    if my_docs_path:
        my_docs_path = GPath(my_docs_path)
        sErrorInfo = _('Folder path specified on command line '
                       '(%(cli_switch)s)') % {'cli_switch': cli_switch}
    else:
        my_docs_path = get_path_from_ini(ini_path_key)
        if my_docs_path:
            sErrorInfo = _('Folder path specified in bash.ini '
                           '(%(bash_ini_setting)s)') % {
                             'bash_ini_setting': f's{ini_path_key}'}
        else:
            my_docs_path, sErrorInfo = fallback(game_info)
    if my_docs_path is None:
        raise BoltError('\n'.join([fail_msg,
            _('Additional info: %(error_info)s') % {'error_info': sErrorInfo},
        ]))
    #  If path is relative, make absolute ##: only do that in the cli_switch case
    if not my_docs_path.is_absolute():
        my_docs_path = dirs['app'].join(my_docs_path)
    #  Error check
    if not my_docs_path.exists():
        raise BoltError('\n'.join([not_exists_msg % {'folder': my_docs_path},
            _('Additional info: %(error_info)s') % {'error_info': sErrorInfo},
        ]))
    return my_docs_path

def getOblivionModsPath(game_info, cli_path_arg):
    if cli_path_arg:
        return (cli_path if (cli_path := GPath(cli_path_arg)).is_absolute()
                else dirs['app'].join(cli_path), 'Command Line Argument')
    ob_mods_path = get_path_from_ini('OblivionMods')
    if ob_mods_path:
        return ob_mods_path, ['[General]', 'sOblivionMods']
    ws_info = get_legacy_ws_game_info(game_info)
    if not ws_info.installed:
        # Currently the standard location, next to the game install
        ob_mods_path = GPath(GPath(u'..').join(
            f'{game_info.bash_root_prefix} Mods'))
        ob_mods_path = dirs['app'].join(ob_mods_path)
        src = u'Relative Path'
    else:
        # New location for Windows Store games,
        # Documents\Wrye Bash\{game} Mods
        ob_mods_path = dirs[u'personal'].join(
            u'Wrye Bash', f'{game_info.bash_root_prefix} Mods')
        src = u'My Documents'
    return ob_mods_path, src

def _get_ini_path(ini_key, dir_key, *args):
    idata_path = get_path_from_ini(ini_key)
    if idata_path:
        src = ['[General]', f's{ini_key}']
    else:
        idata_path = dirs[dir_key].join(*args)
        src = 'Relative Path'
    return idata_path, src

def init_dirs(game_info, opts, init_warnings):
    """Initialize bass.dirs dictionary. We need the bash.ini and the game
    being set, so this is called upon setting the game. Global structures
    that need info on Bash / Game dirs should be initialized here and set
    as globals in module scope. It may be called two times if restoring
    settings fails."""
    if not mopy_dirs_initialized:
        raise BoltError('init_dirs: Mopy dirs uninitialized')
    personal, localAppData = opts.personalPath, opts.localAppDataPath
    #--Oblivion (Application) Directories
    dirs['app'] = game_info.gamePath
    dirs['exe'] = dirs['app'].join(*game_info.executable_dir)
    dirs[u'defaultPatches'] = (
        dirs[u'mopy'].join(u'Bash Patches', game_info.bash_patches_dir)
        if game_info.bash_patches_dir else u'')
    dirs[u'taglists'] = dirs[u'mopy'].join(u'taglists', game_info.taglist_dir)
    # Determine the user's personal (i.e. My Documents) folder. Attempt to pull
    # from, in order:
    #  - CLI
    #  - bash.ini
    #  - Windows only:
    #    - SHGetKnownFolderPath
    #  - Linux only:
    #    - Proton prefix (For Windows games installed via Steam's Proton)
    #    - XDG_DOCUMENTS_DIR
    #    - ~/Documents
    dirs['personal'] = personal = _get_cli_ini_path(personal, '-p',
        'PersonalPath', game_info, get_personal_path,
        _('Failed to determine personal folder.'), _(
            'Personal folder does not exist: %(folder)s'))
    dirs['saveBase'] = game_info.Ess.base_saves_path(personal,
        game_info.my_games_name, dirs) # for Morrowind we will lookup 'app'
    deprint(f'My Games location set to {dirs[u"saveBase"]}')
    # Determine the user's AppData\Local (i.e. %LOCALAPPDATA%) folder. Attempt
    # to pull from, in order:
    #  - CLI
    #  - bash.ini
    #  - Windows only:
    #    - SHGetKnownFolderPath
    #  - Linux only:
    #    - Proton prefix (For Windows games installed via Steam's Proton)
    #    - XDG_DATA_HOME
    #    - ~/.local/share
    dirs['local_appdata'] = localAppData = _get_cli_ini_path(localAppData,
        '-l', 'LocalAppDataPath', game_info, get_local_app_data_path,
        _('Failed to determine LocalAppData folder.'),
        _('LocalAppData folder does not exist: %(folder)s'))
    if game_info.appdata_name:
        # AppData for the game, depends on if it's a WS game or not.
        ws_info = get_legacy_ws_game_info(game_info)
        if ws_info.installed:
            version_info = ws_info.get_installed_version()
            dirs['userApp'] = localAppData.join(
                'Packages', version_info.full_name, 'LocalCache', 'Local',
                game_info.appdata_name)
        else:
            dirs['userApp'] = localAppData.join(game_info.appdata_name)
        deprint(f'LocalAppData location set to {dirs["userApp"]}')
    else:
        # Let any usage of userApp blow up, such a game needs to override
        # determine_lo_dir() (and future usages need to account for such games)
        deprint('No LocalAppData folder set for this game')
    # The Data folder and the LO path, may be overridden by
    # bUseMyGamesDirectory (see below)
    dirs['mods'] = dirs['app'].join(*game_info.mods_dir_path)
    lo_dir = game_info.get_lo_dir(dirs)
    # Use local copy of the oblivion.ini if present
    # see: http://en.uesp.net/wiki/Oblivion:Ini_Settings
    # Oblivion reads the Oblivion.ini in the directory where it exists
    # first, and only if bUseMyGamesDirectory is non-existent or set to 1 does
    # it then look for My Documents\My Games\Oblivion.ini. In other words,
    # both can exist simultaneously, and only the value of bUseMyGamesDirectory
    # in the Oblivion.ini directory where Oblivion.exe is run from will
    # actually matter.
    # Utumno: not sure how/if this applies to other games - Infernio: should at
    # least apply to Oblivion Remastered too
    game_ini_name = game_info.Ini.dropdown_inis[0]
    parent_data_game_ini = dirs['mods'].head.join(game_ini_name)
    if game_info.Ini.game_inis_in_my_documents:
        game_ini_path = dirs['saveBase'].join(game_ini_name)
    else:
        game_ini_path = parent_data_game_ini
    if parent_data_game_ini.is_file():
        ##: use GameIni here
        oblivionIni = ConfigParser(allow_no_value=True, strict=False)
        try:
            try:
                # Try UTF-8 first, will also work for ASCII-encoded files
                oblivionIni.read(parent_data_game_ini, encoding='utf8')
            except UnicodeDecodeError:
                # No good, this is a nonstandard encoding
                with parent_data_game_ini.open(u'rb') as ins:
                    ini_contents = ins.read()
                oblivionIni.read_file(io.StringIO(decoder(ini_contents)))
        except MissingSectionHeaderError:
            # Probably not actually a game INI - might be reshade
            init_warnings.append(_(
                'The global INI file in your game directory (%(global_ini)s) '
                'does not appear to be a valid game INI. It might come from '
                'an incorrectly installed third party tool. Consider deleting '
                'it and validating your game files.') % {
                'global_ini': parent_data_game_ini})
        # is bUseMyGamesDirectory set to 0?
        if _get_ini_option(oblivionIni, 'bUseMyGamesDirectory') == '0':
            # Avoid the My Games directory for INIs and saves
            game_ini_path = parent_data_game_ini
            dirs['saveBase'] = dirs['app']
            lo_dir = dirs['app']
            # Set the data folder to sLocalMasterPath if that option is set
            s_local_mp = _get_ini_option(oblivionIni, 'SLocalMasterPath')
            if s_local_mp:
                dirs['mods'] = dirs['app'].join(s_local_mp)
    deprint(f'{game_info.mods_dir_name} folder set to {dirs["mods"]}')
    dirs['lo'] = lo_dir
    deprint(f'Load order folder set to {dirs["lo"]}')
    # Check and warn if the Data folder is case-sensitive
    if is_case_sensitive(dirs['mods']):
        ci_warn = _(
            'The %(data_folder)s folder is case sensitive. This will cause '
            'serious problems for Wrye Bash, like BAIN not working if the '
            'case differs between a mod-added file and an existing version of '
            'that file in the Data folder.') % {
            'data_folder': game_info.mods_dir_name}
        init_warnings.append(ci_warn + '\n\n' + get_case_sensitivity_advice())
    # these are relative to the mods path so they must be set here
    dirs[u'patches'] = dirs[u'mods'].join(u'Bash Patches')
    dirs['tag_files'] = dirs['mods'].join('BashTags')
    dirs[u'ini_tweaks'] = dirs[u'mods'].join(u'INI Tweaks')
    #--Mod Data, Installers
    oblivionMods, oblivionModsSrc = getOblivionModsPath(game_info,
                                                        opts.oblivionMods)
    dirs[u'bash_root'] = oblivionMods
    deprint(f'Game Mods location set to {oblivionMods}')
    dirs['modsBash'], modsBashSrc = _get_ini_path('BashModData', 'bash_root',
                                                  'Bash Mod Data')
    if game_info.check_legacy_paths:
        mpath = dirs['modsBash']
        old_path = dirs['app'].join(*game_info.mods_dir_path, 'Bash')
        if not mpath.is_dir() and old_path.is_dir():
            dirs['modsBash'], modsBashSrc = old_path, 'Relative path'
    deprint(f'Bash Mod Data location set to {dirs[u"modsBash"]}')
    dirs[u'installers'] = oblivionMods.join(u'Bash Installers')
    if game_info.check_legacy_paths:
        ipath = dirs['installers']
        old_path = dirs['app'].join('Installers')
        dirs['installers'] = (old_path, ipath)[
            ipath.is_dir() or not old_path.is_dir()]
    deprint(f'Installers location set to {dirs[u"installers"]}')
    dirs['bainData'], bainDataSrc = _get_ini_path('InstallersData',
                                                  'installers', 'Bash')
    deprint(f'Installers bash data location set to {dirs[u"bainData"]}')
    dirs[u'bsaCache'] = dirs[u'bainData'].join(u'BSA Cache')
    dirs[u'converters'] = dirs[u'installers'].join(u'Bain Converters')
    dirs[u'dupeBCFs'] = dirs[u'converters'].join(u'--Duplicates')
    dirs[u'corruptBCFs'] = dirs[u'converters'].join(u'--Corrupt')
    # create bash user folders, keep these in order
    dir_keys = (u'modsBash', u'installers', u'converters', u'dupeBCFs',
                u'corruptBCFs', u'bainData', u'bsaCache')
    deprint(u'Checking if WB directories exist and creating them if needed:')
    try:
        for dir_key in dir_keys:
            wanted_dir = dirs[dir_key]
            deprint(f' - {wanted_dir}')
            shellMakeDirs([wanted_dir])
    except NonExistentDriveError as e:
        # NonExistentDriveError is thrown by shellMakeDirs if any of the
        # directories cannot be created due to residing on a non-existing
        # drive (in posix if permission is denied). Find which keys are
        # causing the errors
        msg = _dirs_err_msg(e, dir_keys, bainDataSrc, modsBashSrc,
                            oblivionMods, oblivionModsSrc)
        raise BoltError(msg)
    global bash_dirs_initialized
    bash_dirs_initialized = True
    return game_ini_path

def _dirs_err_msg(e, dir_keys, bainDataSrc, modsBashSrc, oblivionMods,
                  oblivionModsSrc):
    badKeys = set()  # List of dirs[key] items that are invalid
    # First, determine which dirs[key] items are causing it
    for dir_key in dir_keys:
        if dirs[dir_key] in e.failed_paths:
            badKeys.add(dir_key)
    # Now, work back from those to determine which setting created those
    if os_name == 'posix':
        m = _("Please check the settings for the following paths in your "
              "bash.ini, the drive does not exist or you don't have write "
              "permissions")
    else:
        m = _(u'Please check the settings for the following paths in your '
              u'bash.ini, the drive does not exist')
    msg = _(u'Error creating required Wrye Bash directories.') + f'  {m}:\n\n'
    relativePathError = []
    if u'modsBash' in badKeys:
        if isinstance(modsBashSrc, list):
            msg += (' '.join(modsBashSrc) + f'\n    {dirs[u"modsBash"]}\n')
        else:
            relativePathError.append(dirs[u'modsBash'])
    if {u'installers', u'converters', u'dupeBCFs', u'corruptBCFs'} & badKeys:
        # All derived from oblivionMods -> getOblivionModsPath
        if isinstance(oblivionModsSrc, list):
            msg += (u' '.join(oblivionModsSrc) + f'\n    {oblivionMods}\n')
        else:
            relativePathError.append(oblivionMods)
    if {u'bainData', u'bsaCache'} & badKeys:
        # Both derived from 'bainData' -> getBainDataPath
        # Sometimes however, getBainDataPath falls back to oblivionMods,
        # So check to be sure we haven't already added a message about that
        if bainDataSrc != oblivionModsSrc:
            if isinstance(bainDataSrc, list):
                msg += u' '.join(bainDataSrc) + f'\n    {dirs[u"bainData"]}\n'
            else:
                relativePathError.append(dirs[u'bainData'])
    if relativePathError:
        msg += u'\n' + _(u'A path error was the result of relative paths.')
        msg += u'  ' + _(u'The following paths are causing the errors, '
                         u'however usually a relative path should be fine.')
        msg += u'  ' + _(u'Check your setup to see if you are using '
                         u'symbolic links or NTFS Junctions') + u':\n\n'
        msg += u'\n'.join([f'{x}' for x in relativePathError])
    return msg

def init_dirs_mopy():
    dirs[u'mopy'] = Path.getcwd()
    dirs[u'bash'] = dirs[u'mopy'].join(u'bash')
    dirs[u'compiled'] = dirs[u'bash'].join(u'compiled')
    dirs[u'l10n'] = dirs[u'bash'].join(u'l10n')
    dirs[u'db'] = dirs[u'bash'].join(u'db')
    dirs[u'templates'] = dirs[u'mopy'].join(u'templates')
    dirs[u'images'] = dirs[u'bash'].join(u'images')
    from . import archives
    if os_name == u'nt': # don't add local directory to binaries on linux
        archives.exe7z = dirs[u'compiled'].join(archives.exe7z).s
    global mopy_dirs_initialized
    mopy_dirs_initialized = True

def getLocalSaveDirs(saves_folder: str):
    """Return a list of possible local save directories, NOT including the
    base directory."""
    baseSaves = dirs['saveBase'].join(saves_folder)
    # Path.ilist returns [] for non existent dirs
    localSaveDirs = [x for x in top_level_dirs(baseSaves) if
                     x not in ('Bash', 'Mash')]
    # Filter out non-encodable names
    bad = set()
    for folder in localSaveDirs:
        try:
            folder.encode('cp1252')
        except UnicodeEncodeError:
            bad.add(folder)
    localSaveDirs = sorted(x for x in localSaveDirs if x not in bad)
    return localSaveDirs
