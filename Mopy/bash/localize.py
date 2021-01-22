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
#  Wrye Bash copyright (C) 2005-2009 Wrye, 2010-2020 Wrye Bash Team
#  https://github.com/wrye-bash
#
# =============================================================================
"""Houses methods related to localization, including early setup code for
detecting and setting locale as well as code for creating Wrye Bash translation
files."""

__author__ = u'Infernio'

import gettext
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
from . import bass, bolt

#------------------------------------------------------------------------------
# Locale Detection & Setup
def setup_locale(cli_lang):
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
    :return: The wx.Locale object we ended up using."""
    # We need a throwaway wx.App so that the calls below work
    import wx as _wx
    _temp_app = _wx.App(False)
    # Set the wx language - otherwise we will crash when loading any images
    if cli_lang and _wx.Locale.FindLanguageInfo(cli_lang):
        # The user specified a language that wx recognizes and WB supports
        target_language = _wx.Locale.FindLanguageInfo(cli_lang).Language
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
                     u'English' % target_name)
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
                if bass.is_standalone:
                    # Delayed import, since it's only present on standalone
                    import msgfmt
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
            # We've successfully compiled the translation, read it into memory
            with open(mo,u'rb') as trans_file:
                trans = gettext.GNUTranslations(trans_file)
            bolt.deprint(u"Set Wrye Bash locale to '%s'" % target_name)
        except (UnicodeError, OSError):
            bolt.deprint(u'Error loading translation file:')
            traceback.print_exc()
            trans = gettext.NullTranslations()
    # Everything has gone smoothly, install the translation and remember what
    # we ended up with as the final locale
    # PY3: drop the unicode=True, gone in py3 (this is always unicode now)
    trans.install(unicode=True)
    bass.active_locale = target_name
    del _temp_app
    return target_locale

#------------------------------------------------------------------------------
# Internationalization
def _find_all_bash_modules(bash_path=None, cur_dir=None, _files=None):
    """Internal helper function. Returns a list of all Bash files as relative
    paths to the Mopy directory.

    :param bash_path: The relative path from Mopy.
    :param cur_dir: The directory to look for modules in. Defaults to cwd.
    :param _files: Internal parameter used to collect file recursively."""
    if bash_path is None: bash_path = u''
    if cur_dir is None: cur_dir = os.getcwdu()
    if _files is None: _files = []
    _files.extend([os.path.join(bash_path, m) for m in os.listdir(cur_dir)
                   if m.lower().endswith((u'.py', u'.pyw'))]) ##: glob?
    # Find subpackages - returned format is (module_loader, name, is_pkg)
    for module_loader, pkg_name, is_pkg in pkgutil.iter_modules([cur_dir]):
        if not is_pkg: # Skip it if it's not a package
            continue
        # Recurse into the subpackage we just found
        _find_all_bash_modules(
            os.path.join(bash_path, pkg_name) if bash_path else u'bash',
            os.path.join(cur_dir, pkg_name), _files)
    return _files

def dump_translator(out_path, lang):
    """Dumps all translatable strings in python source files to a new text
    file. As this requires the source files, it will not work in standalone
    mode, unless the source files are also installed.

    :param out_path: The directory containing localization files - typically
        bass.dirs[u'l10n'].
    :param lang: The language to dump a text file for.
    :return: The path to the file that the dump was written to."""
    new_txt = os.path.join(out_path, u'%sNEW.txt' % lang)
    tmp_txt = os.path.join(out_path, u'%sNEW.tmp' % lang)
    old_txt = os.path.join(out_path, u'%s.txt' % lang)
    gt_args = [u'p', u'-a', u'-o', new_txt]
    gt_args.extend(_find_all_bash_modules())
    # Need to do this differently on standalone
    if bass.is_standalone:
        # Delayed import, since it's only present on standalone
        import pygettext
        old_argv = sys.argv[:]
        sys.argv = gt_args
        pygettext.main()
        sys.argv = old_argv
    else:
        # pygettext is only in Tools, so call it explicitly
        gt_args[0] = sys.executable
        gt_args.insert(1, os.path.join(sys.prefix, u'Tools', u'i18n',
                                       u'pygettext.py'))
        subprocess.call(gt_args, shell=True)
    # Fill in any already translated stuff...?
    try:
        re_msg_ids_start = re.compile(u'#:')
        re_encoding = re.compile(
            u'' r'"Content-Type:\s*text/plain;\s*charset=(.*?)\\n"$', re.I)
        re_non_escaped_quote = re.compile(u'' r'([^\\])"')
        def sub_quote(regex_match):
            return regex_match.group(1) + r'\"'
        target_enc = None
        # Do all this in binary mode and carefully handle encodings
        with open(tmp_txt, u'wb') as out:
            # Copy old translation file header, and get encoding for strings
            with open(old_txt, u'rb') as ins:
                for old_line in ins:
                    if not target_enc:
                        # Chop off the terminating newline
                        encoding_match = re_encoding.match(
                            old_line.rstrip(b'\r\n'))
                        if encoding_match:
                            # Encoding names are all ASCII, so this is safe
                            target_enc = unicode(encoding_match.group(1),
                                                 u'ascii')
                    if re_msg_ids_start.match(old_line):
                        break # Break once we hit the first translatable string
                    out.write(old_line)
            # Read through the new translation file, fill in any already
            # translated strings
            with open(new_txt, u'rb') as ins:
                skipped_header = False
                for new_line in ins:
                    # First, skip the header - we already copied it above
                    if not skipped_header:
                        msg_ids_match = re_msg_ids_start.match(new_line)
                        if msg_ids_match:
                            skipped_header = True
                            out.write(new_line)
                        continue
                    elif new_line.startswith(b'msgid "'):
                        # Decode the line and retrieve only the msgid contents
                        stripped_line = unicode(new_line, target_enc)
                        stripped_line = stripped_line.strip(u'\r\n')[7:-1]
                        # Replace escape sequences - Quote, Tab, Backslash
                        stripped_line = stripped_line.replace(u'\\"', u'"')
                        stripped_line = stripped_line.replace(u'\\t', u'\t')
                        stripped_line = stripped_line.replace(u'\\\\', u'\\')
                        # Try translating, check if that changes the string
                        ##: This is a neat, pragmatic implementation - but of
                        # course limits us to only ever dumping translations
                        # for the current language
                        translated_line = _(stripped_line)
                        # We're going to need the msgid either way
                        out.write(new_line)
                        if translated_line != stripped_line:
                            # This has a translation, so write that one out
                            out.write(b'msgstr "')
                            # Escape any characters used in escape sequences
                            # and encode the resulting 'final' translation
                            final_ln = translated_line.replace(u'\\', u'\\\\')
                            final_ln = final_ln.replace(u'\t', u'\\t')
                            final_ln = re_non_escaped_quote.sub(
                                sub_quote, final_ln)
                            final_ln = final_ln.encode(target_enc)
                            out.write(final_ln)
                            out.write(b'"\n')
                        else:
                            # Not translated, write out an empty msgstr
                            out.write(b'msgstr ""\n')
                    elif new_line.startswith(b'msgstr "'):
                        # Skip all msgstr lines from new_txt (handled above)
                        continue
                    else:
                        out.write(new_line)
    except (OSError, IOError, UnicodeError):
        bolt.deprint(u'Error while dumping translation file:', traceback=True)
        try: os.remove(tmp_txt)
        except OSError: pass
    else:
        # Replace the empty translation file generated by pygettext with the
        # temp one we just created
        try:
            os.remove(new_txt)
            os.rename(tmp_txt, new_txt)
        except OSError:
            if os.path.exists(new_txt):
                try: os.remove(tmp_txt)
                except OSError: pass
    return new_txt

#------------------------------------------------------------------------------
# Formatting
def format_date(secs): # type: (float) -> unicode
    """Convert time to string formatted to to locale's default date/time.

    :param secs: Formats the specified number of seconds into a string."""
    try:
        local = time.localtime(secs)
    except ValueError: # local time in windows can't handle negative values
        local = time.gmtime(secs)
    return bolt.decoder(time.strftime(u'%c', local), ##: decoder?
                        locale.getpreferredencoding(do_setlocale=False))

# PY3: Probably drop in py3?
def unformat_date(date_str):
    """Basically a wrapper around time.strptime. Exists to get around bug in
    strptime for Japanese locale.

    :type date_str: str"""
    try:
        return time.strptime(date_str, u'%c')
    except ValueError:
        if bass.active_locale.lower() == u'japanese':
            date_str = re.sub(u'^([0-9]{4})/([1-9])', r'\1/0\2', date_str,
                              flags=re.U)
            return time.strptime(date_str, u'%c')
        else:
            raise
