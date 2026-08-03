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
#  Wrye Bash copyright (C) 2005-2009 Wrye, 2010-2026 Wrye Bash Team
#  https://github.com/wrye-bash
#
# =============================================================================
"""Houses methods related to localization, including early setup code for
detecting and setting locale."""

__author__ = 'Infernio'

import gettext
import locale
import os
import sys
import time
import warnings
# Minimal local imports - needs to be imported early in bash
from . import bolt

# so we can `import locale` in the intrpreter to install `_` when importing
# from modules that use it
gettext.NullTranslations().install()

def set_c_locale():
    # Hack see: https://discuss.wxpython.org/t/wxpython4-1-1-python3-8-locale-wxassertionerror/35168/3
    if sys.platform.startswith('win') and sys.version_info > (3, 8):
        for cat in (locale.LC_COLLATE, locale.LC_CTYPE, locale.LC_MONETARY,
                    locale.LC_TIME):  # locale.LC_NUMERIC
            locale.setlocale(cat, 'C')

#------------------------------------------------------------------------------
# Locale Detection & Setup
_WEBLATE_URL = 'https://hosted.weblate.org/engage/wrye-bash/'

def setup_locale(target_lang):
    """Install the Wrye Bash translations for target_lang - the language the
    user specified on the command line or we got from bass.boot_settings - or
    for the user's default locale if None: find a matching translation file
    in the 'Mopy/bash/l10n' folder, else fall back to English. No wx needed -
    set_wx_locale sets its locale to the one we end up with.

    bolt.deprint must be set up and ready to use and the working directory must
    be correct (otherwise detection of translation files will not work and this
    method will always set locale to English).

    :return: The name of the locale we ended up with."""
    if not target_lang: # Fall back on the default language
        try:
            with warnings.catch_warnings():
                # Work around https://github.com/python/cpython/issues/82986
                warnings.simplefilter('ignore', category=DeprecationWarning)
                target_lang, enc = locale.getdefaultlocale()
        except AttributeError:
            bolt.deprint('getdefaultlocale no longer exists, this will '
                         'probably break on Windows now')
            target_lang, enc = locale.getlocale()
        bolt.deprint(f'falling back to ({target_lang}, {enc}) from default '
                     f'locale')
    target_name = target_lang and target_lang.replace('-', '_')
    trans_path = __get_translations_dir()
    def _advertise_weblate(base_msg: str):
        """Small helper for advertising our weblate to users who may end up
        reading the log."""
        bolt.deprint('\n'.join([
            base_msg,
            '',
            'Want to help translate Wrye Bash into your language? '
            'Visit our Weblate page!',
            '', f'  {_WEBLATE_URL}', '',
        ]))
    # English is the default, so it doesn't have a translation file
    # For all other languages, check if we have a translation
    mo = None
    if not target_name or target_name.startswith('en_'): # en_ gives en_GB on my system
        target_name = 'en_US'
    else:
        supported_l10ns = {f[:-3] for f in os.listdir(trans_path) if
                           f[-3:] in ('.mo', '.po')}
        # Check if we support this exact language or any similar
        # languages (i.e. same prefix)
        wanted_prefix = target_name.split('_', 1)[0]
        matches = [f for f in supported_l10ns if
                   target_name == f or f.split('_', 1)[0] == wanted_prefix]
        # first check exact target then similar languages
        if matches := sorted(matches, key=lambda x: x != target_name):
            if target_name == (f := matches[0]):
                bolt.deprint(f"Found translation file for language "
                             f"'{target_name}'")
            else:  # Note we pick the first(!) similar we run across
                _advertise_weblate(f"No translation file for language "
                                   f"'{target_name}', using similar "
                                   f"language with translation file '{f}' "
                                   f"instead")
                target_name = f
            mo = os.path.join(trans_path, target_name + '.mo')
        else:
            # We don't have a translation file for this any language in this
            # family, fall back to English (and ask the user to contribute :))
            target_name = 'en_US'
            _advertise_weblate(f"No translation file for the language "
                               f"family '{wanted_prefix}', will fall back "
                               f"to '{target_name}'")
    # Next, install the Wrye Bash translations
    if mo is not None: # else we're using English
        po = mo[:-2] + 'po'
        try:
            if os.path.isfile(mo):
                if os.path.isfile(po) and (os.path.getmtime(mo) <
                                           os.path.getmtime(po)):
                    # .mo file older than .po file (dev env only)
                    bolt.deprint('\n'.join([
                        f'.mo file possibly outdated ({mo}). If you manually '
                        f'edited the .po file, run scripts/compile_l10n.py',
                        'Using possibly outdated .mo file regardless',
                        '',
                        'Note: if you are trying to translate Wrye Bash, '
                        'please do so via our weblate page!',
                        '', f'  {_WEBLATE_URL}', '',
                    ]))
                with open(mo, 'rb') as trans_file:
                    trans = gettext.GNUTranslations(trans_file)
                # Everything has gone smoothly, install the translation and
                # remember what we ended up with as the final locale
                trans.install()
            else:
                if os.path.isfile(po):
                    # .mo file missing, .po file exists (dev env only)
                    bolt.deprint(f'Missing .mo file ({mo}), but .po file '
                                 f'exists. Run scripts/compile_l10n.py')
                else:
                    # .mo file missing, no .po file (production only)
                    bolt.deprint(f'Missing .mo file ({mo}) - this should '
                                 f'really not happen, please report this!')
                bolt.deprint('Falling back to English (en_US)')
        except (UnicodeError, OSError):
            bolt.deprint('Error loading translation file:', traceback=True)
    # adieu, user locale
    set_c_locale()
    return target_name

def set_wx_locale(__wx, locale_name):
    """Set the wx locale to locale_name, as setup_locale returned it, or to
    the default language if wx does not know it - wx crashes loading images
    otherwise. Returns the wx.Locale, which must stay alive."""
    lang_info = __wx.Locale.FindLanguageInfo(locale_name)
    wx_locale = __wx.Locale(lang_info.Language if lang_info else
                            __wx.LANGUAGE_DEFAULT)
    bolt.deprint(f"Set wxPython locale to '{locale_name}'")
    set_c_locale() # adieu again
    return wx_locale

def __get_translations_dir():
    trans_path = os.path.join(os.getcwd(), u'bash', u'l10n')
    if not os.path.exists(trans_path):
        # HACK: the CI has to run tests from the top dir, which causes us to
        # have a non-Mopy working dir here. Real fix is ditching the fake
        # startup and adding a real headless mode to WB (see #568, #554 and #600)
        trans_path = os.path.join(os.getcwd(), u'Mopy', u'bash', u'l10n')
    return trans_path

#------------------------------------------------------------------------------
# Formatting
def format_date(secs: float) -> str:
    """Convert time to string formatted to to locale's default date/time.

    :param secs: Formats the specified number of seconds into a string."""
    try:
        try:
            local = time.localtime(secs)
        except (OSError, ValueError):
            # local time in windows can't handle negative values
            local = time.gmtime(secs)
        return time.strftime(u'%c', local)
    except OSError:
        bolt.deprint(f'Error formatting date/time - {locals()=}',
                     traceback=True)
        return f'{secs}'
