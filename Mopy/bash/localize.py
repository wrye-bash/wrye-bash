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
"""Houses methods for detecting and setting wx and Wrye Bash locale."""

__author__ = 'Infernio'

import gettext
import importlib
import os
import shutil
import subprocess
import sys
import traceback

# Minimal local imports - needs to be imported statically in bash
import bass
import bolt

def setup_locale(cli_lang, _wx):
    """Sets up wx and Wrye Bash locales, ensuring they match or falling back
    to English if that is impossible. Also considers cli_lang as an override,
    installs the gettext translation and remembers the locale we end up with
    as bass.active_locale.

    bolt.deprint must be set up and ready to use (i.e. hooked up to the
    BashBugDump if debug mode is enabled) and the working directory must be
    correct (otherwise detection of translation files will not work and this
    method will always set locale to English).

    :param cli_lang: The language the user specified on the command line, or
        None.
    :param _wx: The wx instance to use. TODO(inf) ugly - better way?
    :return: The wx.Locale object we ended up using."""
    # We need a throwaway wx.App so that the calls below work
    _temp_app = _wx.App(False)
    # Set the wx language - otherwise we will crash when loading any images
    if cli_lang and _wx.Locale.FindLanguageInfo(cli_lang):
        # The user specified a language that wx recognizes and WB supports
        target_language = _wx.Locale.FindLanguageInfo(cli_lang)
    else:
        # Fall back on the default language
        target_language = _wx.LANGUAGE_DEFAULT
    # We now have a language that wx supports, but we don't know if WB supports
    # it - so check that next
    target_locale = _wx.Locale(target_language)
    target_name = target_locale.GetSysName().split(u'_', 1)[0]
    # Ugly hack, carried forward from bolt.initTranslator
    if target_name.lower() == u'german':
        target_name = u'de'
    # English is the default, so it doesn't have a translation file
    # For all other languages, check if we have a translation
    trans_path = os.path.join(os.getcwdu(), u'bash', u'l10n')
    if target_name.lower() != u'english' and not os.path.exists(os.path.join(
            trans_path, target_name + u'.txt')):
        # WB does not support the default language, use English instead
        target_locale = _wx.Locale(_wx.LANGUAGE_ENGLISH)
        bolt.deprint(u"No translation file for language '%s', falling back to "
                     u"English" % target_name)
        target_name = target_locale.GetSysName().split(u'_', 1)[0]
    bolt.deprint(u"Set wx locale to '%s' (%s)" % (
        target_name, target_locale.GetCanonicalName()))
    # Next, set the Wrye Bash locale based on the one we grabbed from wx
    txt, po, mo = (os.path.join(trans_path, target_name + ext)
                   for ext in (u'.txt', u'.po', u'.mo'))
    if not os.path.exists(txt) and not os.path.exists(mo):
        # We're using English or don't have a translation file - either way,
        # prepare the English translation
        trans = gettext.NullTranslations()
        bolt.deprint(u"Set Wrye Bash locale to 'English'")
    else:
        try:
            # We have a translation file, check if it has to be compiled
            if not os.path.exists(mo) or (os.path.getmtime(txt) >
                                          os.path.getmtime(mo)):
                # Try compiling - have to do it differently if we're a
                # standalone build
                shutil.copy(txt, po)
                args = [u'm', u'-o', mo, po]
                if hasattr(sys, 'frozen'):
                    # Delayed import, since it's only present on standalone
                    msgfmt = importlib.import_module('msgfmt')
                    old_argv = sys.argv[:]
                    sys.argv = args
                    msgfmt.main()
                    sys.argv = old_argv
                else:
                    # msgfmt is only in Tools, so call it explicitly
                    m = os.path.join(sys.prefix, u'Tools', u'i18n',
                                     u'msgfmt.py')
                    subprocess.call([sys.executable, m, u'-o', mo, po],
                                    shell=True)
                # Clean up the temp file we created for compilation
                os.remove(po)
            # We've succesfully compiled the translation, read it into memory
            with open(mo,'rb') as trans_file:
                trans = gettext.GNUTranslations(trans_file)
            bolt.deprint(u"Set Wrye Bash locale to '%s'" % target_name)
        # TODO(inf) Tighten this except
        except:
            bolt.deprint(u'Error loading translation file:')
            traceback.print_exc()
            trans = gettext.NullTranslations()
    # Everything has gone smoothly, install the translation and remember what
    # we ended up with as the final locale
    trans.install(unicode=True)
    bass.active_locale = target_name
    del _temp_app
    return target_locale
