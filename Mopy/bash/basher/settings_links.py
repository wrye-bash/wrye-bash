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
#  Wrye Bash copyright (C) 2005-2009 Wrye, 2010-2020 Wrye Bash Team
#  https://github.com/wrye-bash
#
# =============================================================================

from __future__ import print_function
import sys

from .settings_dialog import SettingsDialog
from .. import bush, balt, bass, bolt, env
from ..balt import ItemLink, AppendableLink, RadioLink, CheckLink, MenuLink, \
    EnabledLink, BoolLink, Link
from ..bolt import deprint
from ..gui import BusyCursor
from ..localize import dump_translator
# TODO(ut): settings links do not seem to use Link.data attribute - it's None..

__all__ = [u'GlobalSettingsMenu']

#------------------------------------------------------------------------------
# Settings Links --------------------------------------------------------------
#------------------------------------------------------------------------------
class Settings_ExportDllInfo(AppendableLink, ItemLink):
    """Exports list of good and bad dll's."""
    _text = _(u"Export list of allowed/disallowed %s plugin DLLs") % \
        bush.game.Se.se_abbrev
    _help = _(u"Export list of allowed/disallowed plugin DLLs to a txt file"
              u" (for BAIN).")

    def _append(self, window): return bool(bush.game.Se.se_abbrev or
                                           bush.game.Sd.sd_abbrev)

    def Execute(self):
        textDir = bass.dirs['patches']
        textDir.makedirs()
        #--File dialog
        title = _(u'Export list of allowed/disallowed plugin DLLs to:')
        file_ = bush.game.Se.se_abbrev + u' ' + _(u'DLL permissions') + u'.txt'
        textPath = self._askSave(title=title, defaultDir=textDir,
                                 defaultFile=file_, wildcard=u'*.txt')
        if not textPath: return
        with textPath.open('w',encoding='utf-8-sig') as out:
            out.write(u'goodDlls '+_(u'(those dlls that you have chosen to allow to be installed)')+u'\r\n')
            if bass.settings['bash.installers.goodDlls']:
                for dll in bass.settings['bash.installers.goodDlls']:
                    out.write(u'dll:'+dll+u':\r\n')
                    for index, version in enumerate(bass.settings['bash.installers.goodDlls'][dll]):
                        out.write(u'version %02d: %s\r\n' % (index, version))
            else: out.write(u'None\r\n')
            out.write(u'badDlls '+_(u'(those dlls that you have chosen to NOT allow to be installed)')+u'\r\n')
            if bass.settings['bash.installers.badDlls']:
                for dll in bass.settings['bash.installers.badDlls']:
                    out.write(u'dll:'+dll+u':\r\n')
                    for index, version in enumerate(bass.settings['bash.installers.badDlls'][dll]):
                        out.write(u'version %02d: %s\r\n' % (index, version))
            else: out.write(u'None\r\n')

#------------------------------------------------------------------------------
class Settings_ImportDllInfo(AppendableLink, ItemLink):
    """Imports list of good and bad dll's."""
    _text = _(u"Import list of allowed/disallowed %s plugin DLLs") % \
        bush.game.Se.se_abbrev
    _help = _(u"Import list of allowed/disallowed plugin DLLs from a txt file"
        u" (for BAIN).")

    def _append(self, window): return bool(bush.game.Se.se_abbrev or
                                           bush.game.Sd.sd_abbrev)

    def Execute(self):
        textDir = bass.dirs['patches']
        textDir.makedirs()
        #--File dialog
        defFile = bush.game.Se.se_abbrev + u' ' + _(
            u'dll permissions') + u'.txt'
        title = _(u'Import list of allowed/disallowed plugin DLLs from:')
        textPath = self._askOpen(title=title, defaultDir=textDir,
                                 defaultFile=defFile, wildcard=u'*.txt',
                                 mustExist=True)
        if not textPath: return
        message = (_(u'Merge permissions from file with current dll permissions?')
                   + u'\n' +
                   _(u"('No' Replaces current permissions instead.)")
                   )
        replace = not balt.askYes(Link.Frame, message,
                                  _(u'Merge permissions?'))
        try:
            with textPath.open('r',encoding='utf-8-sig') as ins:
                Dlls = {'goodDlls':{},'badDlls':{}}
                for line in ins:
                    line = line.strip()
                    if line.startswith(u'goodDlls'):
                        current = Dlls['goodDlls']
                    if line.startswith(u'badDlls'):
                        current = Dlls['badDlls']
                    elif line.startswith(u'dll:'):
                        dll = line.split(u':',1)[1].strip()
                        current.setdefault(dll,[])
                    elif line.startswith(u'version'):
                        ver = line.split(u':',1)[1]
                        ver = eval(ver)
                        current[dll].append(ver)
                        print(dll,':',ver)
            if not replace:
                bass.settings['bash.installers.goodDlls'].update(Dlls['goodDlls'])
                bass.settings['bash.installers.badDlls'].update(Dlls['badDlls'])
            else:
                bass.settings['bash.installers.goodDlls'], bass.settings['bash.installers.badDlls'] = Dlls['goodDlls'], Dlls['badDlls']
        except UnicodeError:
            self._showError(_(u'Wrye Bash could not load %s, because it is not'
                              u' saved in UTF-8 format.  Please resave it in '
                              u'UTF-8 format and try again.') % textPath.s)
        except Exception as e:
            deprint(u'Error reading', textPath.s, traceback=True)
            self._showError(_(u'Wrye Bash could not load %s, because there was'
                              u' an error in the format of the file.')
                            % textPath.s)

#------------------------------------------------------------------------------
class Settings_PluginEncodings(MenuLink):
    _plugin_encodings = {
        'gbk': _(u'Chinese (Simplified)'),
        'big5': _(u'Chinese (Traditional)'),
        'cp1251': _(u'Russian'),
        'cp932': _(u'Japanese (Shift_JIS)'),
        'utf-8': _(u'UTF-8'),
        'cp1252': _(u'Western European (English, French, German, etc)'),
        }
    def __init__(self):
        super(Settings_PluginEncodings, self).__init__(_(u'Plugin Encoding'))
        self.links.append(Settings_PluginEncoding(_(u'Automatic'),None))
        # self.links.append(SeparatorLink())
        enc_name = sorted(self._plugin_encodings.items(), key=lambda x: x[1])
        for encoding,name in enc_name:
            self.links.append(Settings_PluginEncoding(name,encoding))

#------------------------------------------------------------------------------
class Settings_PluginEncoding(RadioLink):
    def __init__(self,name,encoding):
        super(Settings_PluginEncoding, self).__init__()
        self._text = name
        self.encoding = encoding
        self._help = _(u"Select %(encodingname)s encoding for Wrye Bash to use."
            ) % ({'encodingname': self._text})

    def _check(self): return self.encoding == bass.settings[
        'bash.pluginEncoding']

    def Execute(self):
        bass.settings['bash.pluginEncoding'] = self.encoding
        bolt.pluginEncoding = self.encoding

#------------------------------------------------------------------------------
class Settings_Games(MenuLink):

    def __init__(self):
        super(Settings_Games, self).__init__(_(u'Game'))
        for disp_name in bush.foundGames:
            self.links.append(_Settings_Game(disp_name))

class _Settings_Game(RadioLink):
    def __init__(self,game):
        super(_Settings_Game, self).__init__()
        self._text = game
        self._help = _(u"Restart Wrye Bash to manage %(game)s.") % (
            {'game': self._text})

    def _check(self): return self._text == bush.game.displayName

    def Execute(self):
        if self._check(): return
        if not balt.askContinue(Link.Frame,
                                _(u'Note: Switching games this way will '
                                  u'simply relaunch this Wrye Bash '
                                  u'installation with the -o command line '
                                  u'switch.\n\nThat means manually added '
                                  u'application launchers in the status bar '
                                  u'will not change after switching.'),
                                'bash.switch_games_warning.shown'):
            return
        Link.Frame.Restart(['--oblivionPath', bush.game_path(self._text).s])

#------------------------------------------------------------------------------
class Settings_UseAltName(BoolLink):
    _text, key, _help = _(u'Use Alternate Wrye Bash Name'), 'bash.useAltName',\
        _(u'Use an alternate display name for Wrye Bash based on the game it'
          u' is managing.')

    def Execute(self):
        super(Settings_UseAltName, self).Execute()
        Link.Frame.set_bash_frame_title()

#------------------------------------------------------------------------------
class Settings_UAC(AppendableLink, ItemLink):
    _text = _(u'Administrator Mode')
    _help = _(u'Restart Wrye Bash with administrator privileges.')

    def _append(self, window): return env.isUAC

    def Execute(self):
        if balt.askYes(Link.Frame,
                _(u'Restart Wrye Bash with administrator privileges?'),
                _(u'Administrator Mode'), ):
            Link.Frame.Restart(['--uac'])

class Settings_Deprint(CheckLink):
    """Turn on deprint/delist."""
    _text = _(u'Debug Mode')
    _help = _(u"Turns on extra debug prints to help debug an error or just for "
             u"advanced testing.")

    def _check(self): return bolt.deprintOn

    def Execute(self):
        deprint(u'Debug Printing: Off')
        bolt.deprintOn = not bolt.deprintOn
        deprint(u'Debug Printing: On')

class Settings_DumpTranslator(AppendableLink, ItemLink):
    """Dumps new translation key file using existing key, value pairs."""
    _text = _(u'Dump Translator')
    _help = _(u"Generate a new version of the translator file for your locale.")

    def _append(self, window):
        """Can't dump the strings if the files don't exist."""
        return not hasattr(sys,'frozen')

    def Execute(self):
        message = _(u'Generate Bash program translator file?') + u'\n\n' + _(
            u'This function is for translating Bash itself (NOT mods) into '
            u'non-English languages.  For more info, '
            u'see Internationalization section of Bash readme.')
        if not self._askContinue(message, 'bash.dump_translator.continue',
                                _(u'Dump Translator')): return
        outPath = bass.dirs['l10n']
        with BusyCursor():
            outFile = dump_translator(outPath.s, bass.active_locale)
        self._showOk(_(u'Translation keys written to %s') % outFile,
                     self._text + u': ' + outPath.stail)

#------------------------------------------------------------------------------
class Settings_ShowGlobalMenu(BoolLink):
    _text = _(u'Show Global Menu')
    _help = _(u'If checked, a global menu will be shown above the tabs. If '
              u'disabled, its options will still be accessible by '
              u'right-clicking the columns.')
    key = u'bash.show_global_menu'

    def Execute(self):
        super(Settings_ShowGlobalMenu, self).Execute()
        Link.Frame.refresh_global_menu_visibility()

#------------------------------------------------------------------------------
class GlobalSettingsMenu(ItemLink):
    _text = _(u'Global Settings...')
    _help = _(u'Allows you to configure various settings that apply to the '
              u'entirety of Wrye Bash, not just one tab.')

    def Execute(self):
        SettingsDialog.display_dialog()
