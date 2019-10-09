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
"""Houses methods related to localization, including early setup code for
detecting and setting locale as well as code for creating Wrye Bash translation
files."""

__author__ = 'Infernio'

import gettext
import importlib
import locale
import os
import pkgutil
import re
import shutil
import subprocess
import sys
import time
import traceback

# Minimal local imports - needs to be imported statically in bash
import bass
import bolt

#------------------------------------------------------------------------------
# Locale Detection & Setup
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

#------------------------------------------------------------------------------
# Internationalization
def _findAllBashModules(files=[], bashPath=None, cwd=None,
                        exts=('.py', '.pyw'), exclude=(u'chardet',),
                        _firstRun=False):
    """Return a list of all Bash files as relative paths to the Mopy
    directory.

    :param files: files list cache - populated in first run. In the form: [
    u'Wrye Bash Launcher.pyw', u'bash\\balt.py', ..., u'bash\\__init__.py',
    u'bash\\basher\\app_buttons.py', ...]
    :param bashPath: the relative path from Mopy
    :param cwd: initially C:\...\Mopy - but not at the time def is executed !
    :param exts: extensions to keep in listdir()
    :param exclude: tuple of excluded packages
    :param _firstRun: internal use
    """
    if not _firstRun and files:
        return files # cache, not likely to change during execution
    cwd = cwd or os.getcwdu()
    files.extend([(bashPath or bolt.Path(u'')).join(m).s for m in
                  os.listdir(cwd) if m.lower().endswith(exts)])
    # find subpackages -- p=(module_loader, name, ispkg)
    for p in pkgutil.iter_modules([cwd]):
        if not p[2] or p[1] in exclude: continue
        _findAllBashModules(
            files, bashPath.join(p[1]) if bashPath else bolt.GPath(u'bash'),
            cwd=os.path.join(cwd, p[1]), _firstRun=True)
    return files

def dumpTranslator(outPath, lang, *files):
    """Dumps all translatable strings in python source files to a new text file.
       as this requires the source files, it will not work in WBSA mode, unless
       the source files are also installed"""
    outTxt = u'%sNEW.txt' % lang
    fullTxt = os.path.join(outPath,outTxt)
    tmpTxt = os.path.join(outPath,u'%sNEW.tmp' % lang)
    oldTxt = os.path.join(outPath,u'%s.txt' % lang)
    if not files: files = _findAllBashModules()
    args = [u'p',u'-a',u'-o',fullTxt]
    args.extend(files)
    if hasattr(sys,'frozen'):
        import pygettext
        old_argv = sys.argv[:]
        sys.argv = args
        pygettext.main()
        sys.argv = old_argv
    else:
        p = os.path.join(sys.prefix,u'Tools',u'i18n',u'pygettext.py')
        args[0] = p
        subprocess.call(args,shell=True)
    # Fill in any already translated stuff...?
    try:
        reMsgIdsStart = re.compile('#:')
        reEncoding = re.compile(r'"Content-Type:\s*text/plain;\s*charset=(.*?)\\n"$',re.I)
        reNonEscapedQuote = re.compile(r'([^\\])"')
        def subQuote(match): return match.group(1)+'\\"'
        encoding = None
        with open(tmpTxt,'w') as out:
            outWrite = out.write
            #--Copy old translation file header, and get encoding for strings
            with open(oldTxt,'r') as ins:
                for line in ins:
                    if not encoding:
                        match = reEncoding.match(line.strip('\r\n'))
                        if match:
                            encoding = match.group(1)
                    match = reMsgIdsStart.match(line)
                    if match: break
                    outWrite(line)
            #--Read through the new translation file, fill in any already
            #  translated strings
            with open(fullTxt,'r') as ins:
                header = False
                msgIds = False
                for line in ins:
                    if not header:
                        match = reMsgIdsStart.match(line)
                        if match:
                            header = True
                            outWrite(line)
                        continue
                    elif line[0:7] == 'msgid "':
                        stripped = line.strip('\r\n')[7:-1]
                        # Replace escape sequences
                        stripped = stripped.replace('\\"','"')      # Quote
                        stripped = stripped.replace('\\t','\t')     # Tab
                        stripped = stripped.replace('\\\\', '\\')   # Backslash
                        translated = _(stripped)
                        if stripped != translated:
                            # Already translated
                            outWrite(line)
                            outWrite('msgstr "')
                            translated = translated.encode(encoding)
                            # Re-escape the escape sequences
                            translated = translated.replace('\\','\\\\')
                            translated = translated.replace('\t','\\t')
                            translated = reNonEscapedQuote.sub(subQuote,translated)
                            outWrite(translated)
                            outWrite('"\n')
                        else:
                            # Not translated
                            outWrite(line)
                            outWrite('msgstr ""\n')
                    elif line[0:8] == 'msgstr "':
                        continue
                    else:
                        outWrite(line)
    except:
        try: os.remove(tmpTxt)
        except: pass
    else:
        try:
            os.remove(fullTxt)
            os.rename(tmpTxt,fullTxt)
        except:
            if os.path.exists(fullTxt):
                try: os.remove(tmpTxt)
                except: pass
    return outTxt

#------------------------------------------------------------------------------
# Formatting
def formatDate(value):
    """Convert time to string formatted to to locale's default date/time."""
    try:
        local = time.localtime(value)
    except ValueError: # local time in windows can't handle negative values
        local = time.gmtime(value)
        # deprint(u'Timestamp %d failed to convert to local, using %s' % (
        #     value, local))
    return bolt.decode(time.strftime('%c', local),
                       locale.getpreferredencoding(do_setlocale=False))

def unformatDate(date, formatStr):
    """Basically a wrapper around time.strptime. Exists to get around bug in
    strptime for Japanese locale."""
    try:
        return time.strptime(date, '%c')
    except ValueError:
        if formatStr == '%c' and bass.active_locale.lower() == u'japanese':
            date = re.sub(u'^([0-9]{4})/([1-9])', r'\1/0\2', date, flags=re.U)
            return time.strptime(date, '%c')
        else:
            raise
