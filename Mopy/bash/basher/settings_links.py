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

import locale
import sys
import wx
from ..balt import ItemLink, vSizer, hSizer, hspacer, Button, AppendableLink, \
    RadioLink, CheckLink, MenuLink, TransLink, EnabledLink, BoolLink, \
    StaticText, tooltip, Link, staticBitmap, hspace
from .. import barb, bush, balt, bass, bolt, env, exception
from ..bolt import deprint, GPath
from . import BashFrame, BashStatusBar
from .dialogs import ColorDialog
from .app_buttons import App_Button # TODO(ut): ugly
# TODO(ut): settings links do not seem to use Link.data attribute - it's None..

__all__ = ['Settings_BackupSettings', 'Settings_RestoreSettings',
           'Settings_SaveSettings', 'Settings_ExportDllInfo',
           'Settings_ImportDllInfo', 'Settings_Colors', 'Settings_IconSize',
           'Settings_UnHideButtons', 'Settings_StatusBar_ShowVersions',
           'Settings_Languages', 'Settings_PluginEncodings', 'Settings_Games',
           'Settings_UseAltName', 'Settings_Deprint',
           'Settings_DumpTranslator', 'Settings_UAC']

def _bassLang(): return bass.language if bass.language else \
    locale.getlocale()[0].split('_', 1)[0]
#------------------------------------------------------------------------------
# Settings Links --------------------------------------------------------------
#------------------------------------------------------------------------------
class Settings_BackupSettings(ItemLink):
    """Saves Bash's settings and user data.."""
    _text =_(u'Backup Settings...')
    help = _(u"Backup all of Wrye Bash's settings/data to an archive file.")

    @balt.conversation
    def Execute(self):
        msg = _(u'Do you want to backup your Bash settings now?')
        if not balt.askYes(Link.Frame, msg,_(u'Backup Bash Settings?')): return
        BashFrame.SaveSettings(Link.Frame)
        dialog = balt.Dialog(Link.Frame,_(u'Backup Images?'),size=(400,200))
        icon = staticBitmap(dialog)
        sizer = vSizer(
            (hSizer((icon,0,wx.ALL,6), hspace(6),
                    (StaticText(dialog,_(u'Do you want to backup any images?'),
                                noAutoResize=True),1,wx.EXPAND),
                    ),1,wx.EXPAND|wx.ALL,6),
            (hSizer(hspacer,
                    Button(dialog, label=_(u'Backup All Images'),
                           onButClick=lambda: dialog.EndModal(2)), hspace(),
                    Button(dialog, label=_(u'Backup Changed Images'),
                           onButClick=lambda: dialog.EndModal(1)), hspace(),
                    Button(dialog, label=_(u'None'),
                           onButClick=lambda: dialog.EndModal(0)),
                    ),0,wx.EXPAND|wx.ALL^wx.TOP,6),
            )
        dialog.SetSizer(sizer)
        with dialog: images = dialog.ShowModal()
        with balt.BusyCursor():
            backup = barb.BackupSettings(Link.Frame,backup_images=images)
        try: # no BusyCursor() here, the prompt in Apply will invalidate it
            backup.Apply()
        except exception.StateError:
            deprint(u'Backup settings failed', traceback=True)
            backup.WarnFailed()
        except exception.BackupCancelled:
            pass

#------------------------------------------------------------------------------
class Settings_RestoreSettings(ItemLink):
    """Saves Bash's settings and user data.."""
    _text = _(u'Restore Settings...')
    help = _(u"Restore all of Wrye Bash's settings/data from a backup archive "
             u"file.")

    @balt.conversation
    def Execute(self):
        msg = _(u'Do you want to restore your Bash settings from a backup?')
        msg += u'\n\n' + _(u'This will force a restart of Wrye Bash once your '
                           u'settings are restored.')
        if not balt.askYes(Link.Frame, msg, _(u'Restore Bash Settings?')):
            return
        backup = None # barb.RestoreSettings may raise....
        try:
            backup = barb.RestoreSettings(Link.Frame)
            backup.restore_images = balt.askYes(Link.Frame,
                _(u'Do you want to restore saved images as well as settings?'),
                _(u'Restore Settings'))
            with balt.BusyCursor(): backup.Apply()
        except exception.StateError:
            deprint(u'Restore settings failed:', traceback=True)
            if backup: backup.WarnFailed()
        except exception.BackupCancelled:
            pass

#------------------------------------------------------------------------------
class Settings_SaveSettings(ItemLink):
    """Saves Bash's settings and user data."""
    _text = _(u'Save Settings')
    help = _(u"Save all of Wrye Bash's settings/data now.")

    def Execute(self):
        BashFrame.SaveSettings(Link.Frame)

#------------------------------------------------------------------------------
class Settings_ExportDllInfo(AppendableLink, ItemLink):
    """Exports list of good and bad dll's."""
    _text = _(
        u"Export list of allowed/disallowed %s plugin dlls") % bush.game.se_sd
    help = _(u"Export list of allowed/disallowed plugin dlls to a txt file"
        u" (for BAIN).")

    def _append(self, window): return bush.game.se_sd

    def Execute(self):
        textDir = bass.dirs['patches']
        textDir.makedirs()
        #--File dialog
        title = _(u'Export list of allowed/disallowed %s plugin dlls to:') % \
                bush.game.se_sd
        file_ = bush.game.se.shortName + u' ' + _(u'dll permissions') + u'.txt'
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
    _text = _(
        u"Import list of allowed/disallowed %s plugin dlls") % bush.game.se_sd
    help = _(u"Import list of allowed/disallowed plugin dlls from a txt file"
        u" (for BAIN).")

    def _append(self, window): return bush.game.se_sd

    def Execute(self):
        textDir = bass.dirs['patches']
        textDir.makedirs()
        #--File dialog
        defFile = bush.game.se.shortName + u' ' + _(
            u'dll permissions') + u'.txt'
        title = _(u'Import list of allowed/disallowed %s plugin dlls from:') \
                % bush.game.se_sd
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
                        print dll,':',ver
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
class Settings_Colors(ItemLink):
    """Shows the color configuration dialog."""
    _text = _(u'Colors...')
    help = _(u"Configure the custom colors used in the UI.")

    def Execute(self): ColorDialog.Display()

#------------------------------------------------------------------------------
class Settings_IconSize(RadioLink):
    def __init__(self, sb_icon_size):
        super(Settings_IconSize, self).__init__()
        self.sb_icon_size = sb_icon_size
        self._text = unicode(sb_icon_size)
        self.help = _(u"Sets the status bar icons to %(sb_icon_size)s pixels") % (
            {'sb_icon_size': unicode(sb_icon_size)})

    def _check(self):
        return self.sb_icon_size == bass.settings['bash.statusbar.iconSize']

    def Execute(self):
        bass.settings['bash.statusbar.iconSize'] = self.sb_icon_size
        Link.Frame.statusBar.UpdateIconSizes()

#------------------------------------------------------------------------------
class Settings_StatusBar_ShowVersions(CheckLink):
    """Show/Hide version numbers for buttons on the statusbar."""
    _text = _(u'Show App Version')
    help = _(u"Show/hide version numbers for buttons on the status bar.")

    def _check(self): return bass.settings['bash.statusbar.showversion']

    def Execute(self):
        bass.settings['bash.statusbar.showversion'] ^= True
        for button in BashStatusBar.buttons:
            if isinstance(button, App_Button):
                if button.gButton:
                    button.gButton.SetToolTip(tooltip(button.sb_button_tip))
        if BashStatusBar.obseButton.button_state:
            for button in App_Button.obseButtons:
                button.gButton.SetToolTip(tooltip(getattr(button,'obseTip',u'')))

#------------------------------------------------------------------------------
class Settings_Languages(TransLink):
    """Menu for available Languages."""
    def _decide(self, window, selection):
        languages = []
        for file in bass.dirs['l10n'].list():
            if file.cext == u'.txt' and file.csbody[-3:] != u'new':
                languages.append(file.body)
        if languages:
            subMenu = MenuLink(_(u'Language'))
            for lang in languages:
                subMenu.links.append(Settings_Language(lang.s))
            if GPath('english') not in languages:
                subMenu.links.append(Settings_Language('English'))
            return subMenu
        else:
            class _NoLang(EnabledLink):
                _text = _(u'Language')
                help = _(u"Wrye Bash was unable to detect any translation"
                         u" files.")
                def _enable(self): return False
            return _NoLang()

#------------------------------------------------------------------------------
class Settings_Language(RadioLink):
    """Specific language for Wrye Bash."""
    languageMap = {
        u'chinese (simplified)': _(u'Chinese (Simplified)') + u' (简体中文)',
        u'chinese (traditional)': _(u'Chinese (Traditional)') + u' (繁体中文)',
        u'de': _(u'German') + u' (Deutsch)',
        u'pt_opt': _(u'Portuguese') + u' (português)',
        u'italian': _(u'Italian') + u' (italiano)',
        u'russian': _(u'Russian') + u' (ру́сский язы́к)',
        u'english': _(u'English') + u' (English)',
        }

    def __init__(self, lang):
        super(Settings_Language, self).__init__()
        self._lang = lang
        self._text = self.__class__.languageMap.get(self._lang.lower(),
                                                    self._lang)

    def _initData(self, window, selection):
        if self._lang == _bassLang():
            self.help = _(
                "Currently using %(languagename)s as the active language.") % (
                            {'languagename': self._text})
            self.check = True
        else:
            self.help = _(
                "Restart Wrye Bash and use %(languagename)s as the active "
                "language.") % ({'languagename': self._text})
            self.check = False

    def _check(self): return self.check

    def Execute(self):
        if self._lang == _bassLang(): return
        if balt.askYes(Link.Frame,
                _(u'Wrye Bash needs to restart to change languages.  Do you '
                  u'want to restart?'), _(u'Restart Wrye Bash')):
            Link.Frame.Restart(('--Language',self._lang))

#------------------------------------------------------------------------------
class Settings_PluginEncodings(MenuLink):
    encodings = {
        'gbk': _(u'Chinese (Simplified)'),
        'big5': _(u'Chinese (Traditional)'),
        'cp1251': _(u'Russian'),
        'cp932': _(u'Japanese (Shift_JIS)'),
        'utf-8': _(u'UTF-8'),
        'cp1252': _(u'Western European (English, French, German, etc)'),
        }
    def __init__(self):
        super(Settings_PluginEncodings, self).__init__(_(u'Plugin Encoding'))
        bolt.pluginEncoding = bass.settings['bash.pluginEncoding'] # TODO(ut): why is this init here ??
        self.links.append(Settings_PluginEncoding(_(u'Automatic'),None))
        # self.links.append(SeparatorLink())
        enc_name = sorted(Settings_PluginEncodings.encodings.items(),key=lambda x: x[1])
        for encoding,name in enc_name:
            self.links.append(Settings_PluginEncoding(name,encoding))

#------------------------------------------------------------------------------
class Settings_PluginEncoding(RadioLink):
    def __init__(self,name,encoding):
        super(Settings_PluginEncoding, self).__init__()
        self._text = name
        self.encoding = encoding
        self.help = _(u"Select %(encodingname)s encoding for Wrye Bash to use."
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
        for fsName in bush.foundGames:
            self.links.append(_Settings_Game(fsName))

class _Settings_Game(RadioLink):
    def __init__(self,game):
        super(_Settings_Game, self).__init__()
        self._text = bush.get_display_name(game)
        self.help = _(u"Restart Wrye Bash to manage %(game)s.") % (
            {'game': self._text})

    def _check(self): return self._text == bush.game.displayName

    def Execute(self):
        if self._check(): return
        Link.Frame.Restart(('-o', bush.game_path(self._text).s))

#------------------------------------------------------------------------------
class Settings_UnHideButtons(TransLink):
    """Menu to unhide a StatusBar button."""

    def _decide(self, window, selection):
        hide = bass.settings['bash.statusbar.hide']
        hidden = []
        for link in BashStatusBar.buttons:
            if link.uid in hide:
                hidden.append(link)
        if hidden:
            subMenu = MenuLink(_(u'Unhide Buttons'))
            for link in hidden:
                subMenu.links.append(Settings_UnHideButton(link))
            return subMenu
        else:
            class _NoButtons(EnabledLink):
                _text = _(u'Unhide Buttons')
                help = _(u"No hidden buttons available to unhide.")
                def _enable(self): return False
            return _NoButtons()

#------------------------------------------------------------------------------
class Settings_UnHideButton(ItemLink):
    """Unhide a specific StatusBar button."""
    def __init__(self,link):
        super(Settings_UnHideButton, self).__init__()
        self.link = link
        button = self.link.gButton
        # Get a title for the hidden button
        if button:
            # If the wx.Button object exists (it was hidden this session),
            # Use the tooltip from it
            tip_ = button.GetToolTip().GetTip()
        else:
            # If the link is an App_Button, it will have a 'sb_button_tip' attribute
            tip_ = getattr(self.link,'sb_button_tip',None) # YAK YAK YAK
        if tip_ is None:
            # No good, use its uid as a last resort
            tip_ = self.link.uid
        self._text = tip_
        self.help = _(u"Unhide the '%s' status bar button.") % tip_

    def Execute(self): Link.Frame.statusBar.UnhideButton(self.link)

#------------------------------------------------------------------------------
class Settings_UseAltName(BoolLink):
    _text, key, help = _(u'Use Alternate Wrye Bash Name'), 'bash.useAltName', \
        _(u'Use an alternate display name for Wrye Bash based on the game it'
          u' is managing.')

    def Execute(self):
        super(Settings_UseAltName, self).Execute()
        Link.Frame.SetTitle()

#------------------------------------------------------------------------------
class Settings_UAC(AppendableLink, ItemLink):
    _text = _(u'Administrator Mode')
    help = _(u'Restart Wrye Bash with administrator privileges.')

    def _append(self, window): return env.isUAC

    def Execute(self):
        if balt.askYes(Link.Frame,
                _(u'Restart Wrye Bash with administrator privileges?'),
                _(u'Administrator Mode'), ):
            Link.Frame.Restart(True,True)

class Settings_Deprint(CheckLink):
    """Turn on deprint/delist."""
    _text = _(u'Debug Mode')
    help = _(u"Turns on extra debug prints to help debug an error or just for "
             u"advanced testing.")

    def _check(self): return bolt.deprintOn

    def Execute(self):
        deprint(_(u'Debug Printing: Off'))
        bolt.deprintOn = not bolt.deprintOn
        deprint(_(u'Debug Printing: On'))

class Settings_DumpTranslator(AppendableLink, ItemLink):
    """Dumps new translation key file using existing key, value pairs."""
    _text = _(u'Dump Translator')
    help = _(u"Generate a new version of the translator file for your locale.")

    def _append(self, window):
        """Can't dump the strings if the files don't exist."""
        return not hasattr(sys,'frozen')

    def Execute(self):
        message = _(u'Generate Bash program translator file?') + u'\n\n' + _(
            u'This function is for translating Bash itself (NOT mods) into '
            u'non-English languages.  For more info, '
            u'see Internationalization section of Bash readme.')
        if not self._askContinue(message, 'bash.dumpTranslator.continue',
                                _(u'Dump Translator')): return
        outPath = bass.dirs['l10n']
        with balt.BusyCursor():
            outFile = bolt.dumpTranslator(outPath.s, _bassLang())
        self._showOk(_(
            u'Translation keys written to ') + u'Mopy\\bash\\l10n\\' + outFile,
                     _(u'Dump Translator') + u': ' + outPath.stail)
