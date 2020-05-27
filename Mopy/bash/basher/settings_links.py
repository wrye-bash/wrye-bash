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

from .settings_dialog import SettingsDialog
from .. import bush, balt, bass, bolt, env
from ..balt import ItemLink, AppendableLink, RadioLink, CheckLink, MenuLink, \
    BoolLink, Link
from ..bolt import deprint
# TODO(ut): settings links do not seem to use Link.data attribute - it's None..

__all__ = [u'GlobalSettingsMenu']

#------------------------------------------------------------------------------
# Settings Links --------------------------------------------------------------
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
