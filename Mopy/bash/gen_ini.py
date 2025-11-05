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
#  Wrye Bash copyright (C) 2005-2009 Wrye, 2010-2025 Wrye Bash Team
#  https://github.com/wrye-bash
#
# =============================================================================
"""Houses bash_default.ini & functions for generating it."""

__author__ = 'sibir'

from os import path
from textwrap import fill
from zlib import crc32

def _wrap_ini_comment(txt, indent=';--'):
    """Wrap translatable comments in bash_default.ini."""
    return fill(txt, 80, initial_indent=indent, subsequent_indent=';    ')

def _generate_default_bash_ini():
    """Return the translated bash_default.ini & checksum for comparison."""
    default_bash_ini = fr""";#   ____            _       _       _   ____  __ _____ 
;#  |  _ \          | |     (_)     (_) |___ \/_ | ____|
;#  | |_) | __ _ ___| |__    _ _ __  _    __) || | |__  
;#  |  _ < / _` / __| '_ \  | | '_ \| |  |__ < | |___ \ 
;#  | |_) | (_| \__ \ | | |_| | | | | |  ___) || |___) |
;#  |____/ \__,_|___/_| |_(_)_|_| |_|_| |____/ |_|____/

{_wrap_ini_comment(_(
    "This is the generic version of %(bash_config_file)s. You must copy or "
    'rename it to "%(bash_config_file)s" before it can be used. It is '""
    "distributed as %(bash_default_config_file)s so that your changes won't "
    "be accidentally erased during an upgrade to Wrye Bash.") % {
        'bash_config_file': 'bash.ini',
        'bash_default_config_file': 'bash_default.ini'})}

{_wrap_ini_comment(_(
    "You do NOT need to set values for all of these, only those you wish to "
    "change from their default values. In most cases, you just uncomment "
    "(remove the ;) from the option you want to use and possibly change the "
    "value."), ';  ')}

{_wrap_ini_comment(_('Bool options (starting with b) can use use any of:'),
        ';  ')}
;    True, 1, Yes, On
;    False, 0, No, Off

{_wrap_ini_comment(_('Paths - You can use either:'), ';  ')}
{_wrap_ini_comment(_('Absolute Path'), ';    ')}
;      {_('Example')}=C:\Games\Oblivion Mods
{_wrap_ini_comment(_(
        'Relative path, where path is relative to the game install directory'),
        ';    ')}
;      {_('Example')}=Tools\Tes4Files.exe
{_wrap_ini_comment(_('In some cases, the path of "." means select a default.'),
        ';    ')}


;    _____                                 _
;   / ____|                               | |
;  | |  __   ___  _ __    ___  _ __  __ _ | |
;  | | |_ | / _ \| '_ \  / _ \| '__|/ _` || |
;  | |__| ||  __/| | | ||  __/| |  | (_| || |
;   \_____| \___||_| |_| \___||_|   \__,_||_|

[General]

{_wrap_ini_comment(_(
    "%(oblivion_mods)s is an alternate root directory for Bash Installers and "
    "other Wrye Bash data. Putting it under the game's install directory can "
    "cause performance problems during gameplay, so by default it is placed "
    "at the same level as the game folder. Here are the Oblivion and Skyrim "
    "defaults, and two other examples.") % {'oblivion_mods': 'sOblivionMods'})}
;sOblivionMods=..\Oblivion Mods
;sOblivionMods=..\Skyrim Mods
;sOblivionMods=C:\Games\Oblivion Mods
;sOblivionMods=C:\Steam\SteamApps\common\Skyrim Mods


{_wrap_ini_comment(_(
    "%(bash_mod_data)s is the directory containing data about your mods, ini "
    "edits, etc. If using MOM, mTES4 Manager, or other utilities to manage "
    "multiple installs, you will want to change this to keep the Wrye Bash "
    "data with your saved games. You'll need to use an absolute path to your "
    "saved games folder, so here are the defaults and a few examples.") % {
        'bash_mod_data': 'sBashModData'})}
;sBashModData=..\Oblivion Mods\Bash Mod Data
;sBashModData=..\Skyrim Mods\Bash Mod Data
;sBashModData=C:\Documents and Settings\Wrye\My Documents\My Games\Oblivion\Bash Mod Data
;sBashModData=C:\Users\Wrye\AppData\Local\Skyrim\Bash Mod Data


{_wrap_ini_comment(_(
    "%(installers_data)s is the directory containing data about which "
    "installers are installed by Wrye Bash. If you changed %(bash_mod_data)s "
    "above, you'll probably want to change this one too. Examples:") % {
       'installers_data': 'sInstallersData', 'bash_mod_data': 'sBashModData'})}
;sInstallersData=..\Oblivion Mods\Bash Installers\Bash
;sInstallersData=..\Skyrim Mods\Bash Installers\Bash
;sInstallersData=C:\Documents and Settings\Wrye\My Documents\My Games\Oblivion\Bash Installers\Bash
;sInstallersData=C:\Users\Wrye\AppData\Local\Skyrim\Bash Installers\Bash
;sInstallersData=C:\Users\Wrye\AppData\Local\Skyrim\Bash Installers Data


{_wrap_ini_comment(_(
    "%(oblivion_path)s is the game directory (containing Oblivion.exe, "
    'TESV.exe, etc.). A "normal" install of Wrye Bash will place the '
    "%(wb_dir)s directory in your game directory. Use this argument only if "
    "you placed Wrye Bash outside of the game directory and the automatic "
    "detection and %(cli_game_detect)s command line parameter fail to find "
    "the game. *If using a relative path, it will be relative to the "
    "%(wb_dir)s directory.*") % {'oblivion_path': 'sOblivionPath',
                                 'wb_dir': 'Mopy', 'cli_game_detect': '-o'})}
;sOblivionPath=C:\Games\Oblivion
;sOblivionPath=G:\Oblivion
;sOblivionPath=G:\Steam\SteamApps\common\Skyrim


{_wrap_ini_comment(_("User directory arguments."))}
{_wrap_ini_comment(_(
    "These arguments allow you to specify your user directories in several "
    "ways. These are only useful if the regular procedure for getting the "
    "user directory fails."), ';    ')}


{_wrap_ini_comment(_(
    "%(user_path)s is the user profile path. May help if HOMEDRIVE and/or "
    "HOMEPATH are missing from the user's environment.") % {
        'user_path': 'sUserPath'})}
;sUserPath=C:\Documents and Settings\Wrye
;sUserPath=C:\Users\Wrye


{_wrap_ini_comment(_("%(personal_path)s is the user's personal directory "
    '("%(documents)s"). Should be used in conjunction with either the '
    "%(cli_lad_path)s command line argument or setting %(lad_path)s.") % {
        'personal_path': 'sPersonalPath', 'documents': 'Documents',
        'cli_lad_path': '-l', 'lad_path': 'sLocalAppDataPath'})}
;sPersonalPath=C:\Documents and Settings\Wrye\My Documents
;sPersonalPath=C:\Users\Wrye\Documents


{_wrap_ini_comment(_(
    "%(lad_path)s is the user's local application data directory. Should be "
    "used in conjunction with either the %(cli_personal_path)s command line "
    "argument or setting %(personal_path)s.") % {
        'lad_path': 'sLocalAppDataPath', 'cli_personal_path': '-p',
        'personal_path': 'sPersonalPath'})}
;sLocalAppDataPath=C:\Documents and Settings\Wrye\Local Settings\Application Data
;sLocalAppDataPath=C:\Users\Wrye\AppData\Local


;    _____        _    _    _
;   / ____|      | |  | |  (_)
;  | (___    ___ | |_ | |_  _  _ __    __ _  ___
;   \___ \  / _ \| __|| __|| || '_ \  / _` |/ __|
;   ____) ||  __/| |_ | |_ | || | | || (_| |\__ \
;  |_____/  \___| \__| \__||_||_| |_| \__, ||___/
;                                      __/ |
;                                     |___/

[Settings]

{_wrap_ini_comment(_(
    "%(reset_bsa_timestamps)s: whether or not Wrye Bash should automatically "
    "set BSA timestamps. If enabled, BSAs will be set to %(redate_date)s "
    "automatically. It is intended to prevent files in BSAs from overriding "
    "loose files. Default is %(default)s.") % {
        'reset_bsa_timestamps': 'bResetBSATimestamps',
        'redate_date': '1-1-2006', 'default': 'True'})}
;bResetBSATimestamps=False


{_wrap_ini_comment(_(
    "%(skip_reset_time_notif)s: whether or not to skip notification about mod "
    "modification times reset by %(lock_load_order)s and other load order "
    "corrections. The default is %(default)s, but, if you find the alerts "
    "annoying, you can hide them.") % {
        'skip_reset_time_notif': 'bSkipResetTimeNotifications',
        'lock_load_order': f"{_('Lock Load Order')}", 'default': 'False'})}
;bSkipResetTimeNotifications=True


{_wrap_ini_comment(_(
    "%(auto_item_check)s: determines whether to automatically check new items "
    "in the %(bashed_patch)s. Default is %(default)s.") % {
        'auto_item_check': 'bAutoItemCheck', 'bashed_patch': 'Bashed Patch',
        'default': 'True'})}
;bAutoItemCheck=False


{_wrap_ini_comment(_(
    "%(skip_hide_confirm)s: determines whether the hide confirmations are "
    "shown. Default is %(default)s.") % {
        'skip_hide_confirm': 'bSkipHideConfirmation', 'default': 'False'})}
;bSkipHideConfirmation=True


{_wrap_ini_comment(_(
    "%(sound_any)s: if set, plays that sound in the specified situation. Can "
    "be an absolute or relative path from the app directory. Default is empty "
    "(no sound).") % {'sound_any': 'sSound*'})}
{_wrap_ini_comment(_('%(sound_error)s: %(bashed_patch)s build error') % {
        'sound_error': 'sSoundError', 'bashed_patch': 'Bashed Patch'}, ';  ')}
{_wrap_ini_comment(_('%(sound_success)s: %(bashed_patch)s build success') % {
        'sound_success': 'sSoundSuccess', 'bashed_patch': 'Bashed Patch'},
        ';  ')}
;sSoundError=.
;sSoundSuccess=.


{_wrap_ini_comment(_(
    "%(show_dev_tools)s: whether to show some menu options and %(status_bar)s "
    "buttons that are really only useful for people programming Wrye Bash. "
    "Default is %(default)s.") % {
        'show_dev_tools': 'bShowDevTools', 'status_bar': 'Status Bar',
        'default': 'False'})}
;bShowDevTools=True


{_wrap_ini_comment(_(
    "%(ensure_bp_exists)s: whether or not Wrye Bash should automatically "
    "ensure a %(bashed_patch)s exists. Default is %(default)s.") % {
        'ensure_bp_exists': 'bEnsurePatchExists',
        'bashed_patch': 'Bashed Patch', 'default': 'True'})}
;bEnsurePatchExists=False


{_wrap_ini_comment(_(
    "%(script_file_ext)s: the extension that will be used for the exported "
    "scripts when running '%(exp_scripts)s' (defaults to %(default)s).") % {
        'script_file_ext': 'sScriptFileExt', 'exp_scripts': 'Export Scripts',
        'default': '.txt'})}
;sScriptFileExt=.txt


{_wrap_ini_comment(_(
    '%(ob_txt_bsa_name)s: use if you have renamed "%(ob_txt_bsa)s" and are '
    "using %(bsa_redir)s (does not apply to other games).") % {
        'ob_txt_bsa_name': 'sOblivionTexturesBSAName',
        'ob_txt_bsa': 'Oblivion - Textures - Compressed.bsa',
        'bsa_redir': 'BSA Redirection'})}
;sOblivionTexturesBSAName=.


{_wrap_ini_comment(_(
    "%(7z_ex_comp_args)s: if set to something other than default, adds these "
    "as command line arguments for compressing with %(archiver)s. If you "
    "always want Solid on and a block size of 1mb you would specify: "
    "%(default)s") % {'7z_ex_comp_args': 's7zExtraCompressionArguments',
                      'archiver': '7z', 'default': '-ms=on -ms=1m'})}
;s7zExtraCompressionArguments=-ms=on -ms=1m


{_wrap_ini_comment(_(
    "%(xedit_cli)s: additional command line arguments to pass to xEdit when "
    "launched via Wrye Bash with xEdit expert mode enabled.") % {
        'xedit_cli': 'sxEditCommandLineArguments'})}
;sxEditCommandLineArguments=-AllowMasterFilesEdit


{_wrap_ini_comment(_(
    "%(enable_splash_screen)s: use this to enable or disable the startup "
    "splash screen. Default is %(default)s.") % {
        'enable_splash_screen': 'bEnableSplashScreen', 'default': 'True'})}
;bEnableSplashScreen=False


{_wrap_ini_comment(_(
    "%(prompt_act_bp)s: prompt to activate the %(bashed_patch)s after it is "
    "built. Default is %(default)s.") % {
        'prompt_act_bp': 'bPromptActivateBashedPatch',
        'bashed_patch': 'Bashed Patch', 'default': 'True'})}
;bPromptActivateBashedPatch=False


{_wrap_ini_comment(_(
    "%(warn_too_many_files)s: use this to enable or disable the warning on "
    "too many mods/BSAs on startup. Default is %(default)s.") % {
        'warn_too_many_files': 'bWarnTooManyFiles', 'default': 'True'})}
;bWarnTooManyFiles=False


{_wrap_ini_comment(_(
    "%(skip_bain_dirs)s: provide a list of directories, separated by the pipe "
    "symbol, |, to be skipped inside Bash Installers directory.") % {
        'skip_bain_dirs': 'sSkippedBashInstallersDirs'})}
;sSkippedBashInstallersDirs=cache|categories|downloads|ModProfiles|ReadMe


{_wrap_ini_comment(_(
    "%(command_7z)s: provide the path to a %(archiver)s executable to use in "
    "unix-based systems") % {'command_7z': 'sCommand7z', 'archiver': '7z'})}
;sCommand7z=/Users/me/7zz


{_wrap_ini_comment(_(
    "%(skip_ws_detect)s: skips detection of games via the Windows Store. The "
    "reason for this setting's existence is that Windows Store detection "
    "requires querying every single mounted drive on the computer, which can "
    "be slow if you have network drives or slow hard drives connected. If you "
    "notice Wrye Bash taking excessively long to boot and don't use Windows "
    "Store versions of games, try setting this option to %(option)s. Default "
    "is %(default)s.") % {'skip_ws_detect': 'bSkipWSDetection',
                          'option': 'True', 'default': 'False'})}
;bSkipWSDetection=True


;  _______             _      ____          _    _
; |__   __|           | |    / __ \        | |  (_)
;    | |  ___    ___  | |   | |  | | _ __  | |_  _   ___   _ __   ___
;    | | / _ \  / _ \ | |   | |  | || '_ \ | __|| | / _ \ | '_ \ / __|
;    | || (_) || (_) || |   | |__| || |_) || |_ | || (_) || | | |\__ \
;    |_| \___/  \___/ |_|    \____/ | .__/  \__||_| \___/ |_| |_||___/
;                                   | |
;                                   |_|

[Tool Options]

{_wrap_ini_comment(_("Whether or not to show the various larger non-core tool "
    "launcher segments."))}
;bShowTextureToolLaunchers=True
;bShowModelingToolLaunchers=True
;bShowAudioToolLaunchers=True


{_wrap_ini_comment(_(
    "All tool launcher paths can be absolute or relative paths from the head "
    "of the game folder (the folder with, e.g., Oblivion.exe or TESV.exe in "
    "it). A few Java programs also have matching entries for argument options."
))}


;==================================================;
;=========ESM/ESP/LOD/NIF Tool Launchers===========;
;==================================================;

;sTes4GeckoPath=Tes4Gecko.jar
;sTes4GeckoJavaArg=-Xmx1024m

;sTes4FilesPath=Tools\Tes4Files.exe

;sTes4EditPath=TES4Edit.exe

;sTes5EditPath=TES5Edit.exe

;sEnderalEditPath=EnderalEdit.exe

;sSSEEditPath=SSEEdit.exe

;sFo4EditPath=FO4Edit.exe

;sFo3EditPath=FO3Edit.exe

;sFnvEditPath=FNVEdit.exe

;sTes4LodGenPath=Tes4LodGen.exe

;sNifskopePath=C:\Program Files\NifTools\NifSkope\nifskope.exe

;sTes5GeckoPath=C:\Program Files\Dark Creations\TESVGecko\TESVGecko.exe


;==================================================;
;===========3D Modeling Tool Launchers=============;
;==================================================;

;sArtOfIllusion=C:\Program Files\ArtOfIllusion\Art of Illusion.exe

;sAutoCad=C:\Program Files\Autodesk Architectural Desktop 3\acad.exe

;sBlenderPath=C:\Program Files\Blender Foundation\Blender\Blender.exe

;sGmaxPath=C:\GMAX\gmax.exe

;sMaxPath=C:\Program Files\Autodesk\3ds Max 2010\3dsmax.exe

;sMayaPath=C:\not\a\valid\path.exe

;sMilkshape3D=C:\Program Files\MilkShape 3D 1.8.4\ms3d.exe

;sMudbox=C:\Program Files\Autodesk\Mudbox2011\mudbox.exe

;sSculptris=C:\Program Files\sculptris\Sculptris.exe

;sSoftimageModTool=C:\Softimage\Softimage_Mod_Tool_7.5\Application\bin\XSI.bat

;sSpeedTree=C:\not\a\valid\path.exe

;sTreed=C:\Program Files\gile[s]\plugins\tree[d]\tree[d].exe

;sWings3D=C:\Program Files\wings3d_1.2\Wings3D.exe


;==================================================;
;==========Texturing/DDS Tool Launchers============;
;==================================================;

;sAniFX=C:\Program Files\AniFX 1.0\AniFX.exe

;sArtweaver=C:\Program Files\Artweaver 1.0\Artweaver.exe

;sCrazyBump=C:\Program Files\Crazybump\CrazyBump.exe

;sDDSConverter=C:\Program Files\DDS Converter 2\DDS Converter 2.exe

;sDeepPaint=C:\Program Files\Right Hemisphere\Deep Paint\DeepPaint.exe

;sDogwaffle=C:\Program Files\project dogwaffle\dogwaffle.exe

;sGenetica=C:\Program Files\Spiral Graphics\Genetica 3.5\Genetica.exe

;sGeneticaViewer=C:\Program Files\Spiral Graphics\Genetica Viewer 3\Genetica Viewer 3.exe

;sGIMP=C:\Program Files\GIMP 2\bin\gimp-2.8.exe

;sIcoFX=C:\Program Files\IcoFX 1.6\IcoFX.exe

;sInkscape=C:\Program Files\Inkscape\inkscape.exe

;sKrita=C:\Program Files\Krita (x86)\bin\krita.exe

;sMaPZone=C:\Program Files\Allegorithmic\MaPZone 2.6\MaPZone2.exe

;sMyPaint=C:\Program Files\MyPaint\mypaint.exe

;sNVIDIAMelody=C:\Program Files\NVIDIA Corporation\Melody\Melody.exe

;sPaintNET=C:\Program Files\Paint.NET\PaintDotNet.exe

;sPaintShopPhotoPro=C:\Program Files\Corel\Corel PaintShop Photo Pro\X3\PSPClassic\Corel Paint Shop Pro Photo.exe

;sPhotobie=C:\Program Files\Photobie\Photobie.exe

;sPhotoFiltre=C:\Program Files\PhotoFiltre\PhotoFiltre.exe

;sPhotoScape=C:\Program Files\PhotoScape\PhotoScape.exe

;sPhotoSEAM=C:\Program Files\PhotoSEAM\PhotoSEAM.exe

;sPhotoshopPath=C:\Program Files\Adobe\Adobe Photoshop CS3\Photoshop.exe

;sPixelStudio=C:\Program Files\Pixel\Pixel.exe

;sPixia=C:\Program Files\Pixia\pixia.exe

;sTextureMaker=C:\Program Files\Texture Maker\texturemaker.exe

;sTwistedBrush=C:\Program Files\Pixarra\TwistedBrush Open Studio\tbrush_open_studio.exe

;sWTV=C:\Program Files\WindowsTextureViewer\WTV.exe

;sxNormal=C:\Program Files\Santiago Orgaz\xNormal\3.17.3\x86\xNormal.exe


;==================================================;
;=========General/Modding Tool Launchers===========;
;==================================================;

;sBSACMD=C:\Program Files\BSACommander\bsacmd.exe

;sEggTranslator=C:\Program Files\Egg Translator\EggTranslator.exe

;sISOBL=ISOBL.exe

;sISRMG=Insanitys ReadMe Generator.exe

;sISRNG=Random Name Generator.exe

;sISRNPCG=Random NPC.exe

;sMAP=Modding Tools\Interactive Map of Cyrodiil and Shivering Isles 3.52\Mapa v 3.52.exe

;sOblivionBookCreatorPath=Data\OblivionBookCreator.jar
;sOblivionBookCreatorJavaArg=-Xmx1024m

;sOBMLG=Modding Tools\Oblivion Mod List Generator\Oblivion Mod List Generator.exe

;sOBFEL=C:\Program Files\Oblivion Face Exchange Lite\OblivionFaceExchangeLite.exe

;sRADVideo=C:\Program Files\RADVideo\radvideo.exe

;sTabula=Modding Tools\Tabula.exe


;==================================================;
;======Screenshot/Benchmarking Tool Launchers======;
;==================================================;

;sFraps=C:\Fraps\Fraps.exe

;sIrfanView=C:\Program Files\IrfanView\i_view32.exe

;sXnView=C:\Program Files\XnView\xnview.exe

;sFastStone=C:\Program Files\FastStone Image Viewer\FSViewer.exe

;sWinSnap=C:\Program Files\WinSnap\WinSnap.exe


;==================================================;
;============Sound/Audio Tool Launchers============;
;==================================================;

;sABCAmberAudioConverter=C:\Program Files\ABC Amber Audio Converter\abcaudio.exe

;sAudacity=C:\Program Files\Audacity\Audacity.exe

;sMediaMonkey=C:\Program Files\MediaMonkey\MediaMonkey.exe

;sSwitch=C:\Program Files\NCH Swift Sound\Switch\switch.exe


;==================================================;
;=========Text/Development Tool Launchers==========;
;==================================================;

;sNPP=C:\Program Files\Notepad++\notepad++.exe

;sWinMerge=C:\Program Files\WinMerge\WinMergeU.exe

;sFreeMind=C:\Program Files\FreeMind\Freemind.exe

;sFreeplane=C:\Program Files\Freeplane\freeplane.exe


;==================================================;
;========Other/Miscellaneous Tool Launchers========;
;==================================================;

;sEVGAPrecision=C:\Program Files\EVGA Precision\EVGAPrecision.exe

;sFileZilla=C:\Program Files\FileZilla FTP Client\filezilla.exe

;sLogitechKeyboard=C:\Program Files\Logitech\GamePanel Software\G-series Software\LGDCore.exe

;sSteam=C:\Program Files\Steam\steam.exe

;sBOSS=BOSS\BOSS.EXE

;sLOOT=LOOT\LOOT.exe
;sLOOT=/opt/loot/LOOT

;sOBMM=OblivionModManager.exe
"""

    return default_bash_ini, crc32(default_bash_ini.encode())

def write_default_bash_ini():
    """Write bash_default.ini if missing or changed."""
    default_bash_ini, default_ini_crc = _generate_default_bash_ini()
    if path.exists('bash_default.ini'):
        with open('bash_default.ini', 'r') as f:
            curr_default_ini_crc = crc32(f.read().encode())
    else:
        curr_default_ini_crc = 0
    if curr_default_ini_crc != default_ini_crc:
        with open('bash_default.ini', 'w') as f:
            f.write(default_bash_ini)
