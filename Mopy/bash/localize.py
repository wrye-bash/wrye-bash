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
#  Wrye Bash copyright (C) 2005-2009 Wrye, 2010-2022 Wrye Bash Team
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
import subprocess
import sys
import time

# Minimal local imports - needs to be imported early in bash
from . import bass, bolt

def set_c_locale():
    # Hack see: https://discuss.wxpython.org/t/wxpython4-1-1-python3-8-locale-wxassertionerror/35168/3
    if sys.platform.startswith('win') and sys.version_info > (3, 8):
        for cat in (locale.LC_COLLATE, locale.LC_CTYPE, locale.LC_MONETARY,
                    locale.LC_TIME):  # locale.LC_NUMERIC
            locale.setlocale(cat, 'C')

#------------------------------------------------------------------------------
# Locale Detection & Setup
def setup_locale(cli_lang, _wx):
    """Set up wx Locale and Wrye Bash translations. If cli_lang is given,
    will validate it is a supported wx language code, otherwise will fallback
    to user default locale. Then will try to find a matching translation file
    in the 'Mopy/bash/l10n' folder. If a translation file was found (even for
    a similar language) we will try to install the gettext translation
    otherwise we will still try to set the locale to the user specified/default
    Finally  remembers the locale we end up with as bass.active_locale.

    bolt.deprint must be set up and ready to use and the working directory must
    be correct (otherwise detection of translation files will not work and this
    method will always set locale to English).

    :param cli_lang: The language the user specified on the command line, or
        None.
    :return: The wx.Locale object we ended up using."""
    # Set the wx language - otherwise we will crash when loading any images
    cli_target = cli_lang and _wx.Locale.FindLanguageInfo(cli_lang)
    if cli_target:
        # The user specified a language that wx recognizes
        target_name = cli_target.CanonicalName
    else:
        # Fall back on the default language
        language_code, enc = locale.getdefaultlocale()
        bolt.deprint(f'{cli_lang=} - {cli_target=} - falling back to '
                     f'({language_code}, {enc}) from getdefaultlocale')
        lang_info = _wx.Locale.FindLanguageInfo(language_code)
        target_name = lang_info and lang_info.CanonicalName
        bolt.deprint(f'wx gave back {target_name}')
    # We now have a language that wx supports, but we don't know if WB supports
    # it - so check that next
    trans_path = __get_translations_dir()
    # English is the default, so it doesn't have a translation file
    # For all other languages, check if we have a translation
    po = mo = None
    if not target_name or target_name.startswith('en_'): # en_ gives en_GB on my system
        target_name = 'en_US'
    else:
        supported_l10ns = [f[:-3] for f in os.listdir(trans_path) if
                           f[-3:] == '.po']
        # Check if we support this exact language or any similar
        # languages (i.e. same prefix)
        wanted_prefix = target_name.split('_', 1)[0]
        matches = [f for f in supported_l10ns if
                   target_name == f or f.split('_', 1)[0] == wanted_prefix]
        # first check exact target then similar languages
        for f in sorted(matches, key=lambda x: x != target_name):
            # Try switching wx to this locale as well
            lang_info = _wx.Locale.FindLanguageInfo(f)
            if lang_info:
                if target_name == f:
                    bolt.deprint(f"Found translation file for language "
                                 f"'{target_name}'")
                else:  # Note we pick the first similar we run across
                    bolt.deprint(f"No translation file for language "
                                 f"'{target_name}', using similar language "
                                 f"with translation file '{f}' instead")
                    target_name = f
                po, mo = (os.path.join(trans_path, target_name + ext) for ext
                          in (u'.po', u'.mo'))
                break
        else:
            if not matches: # TODO: is this any use? we set C locale anyway
                bolt.deprint(f"Wrye Bash does not support the language "
                             f"family '{wanted_prefix}', will however "
                             f"try to set locale to '{target_name}'")
            else: # TODO: needs more tweaking - probably we should unify with above
                # If that didn't work, all we can do is complain
                # about it and fall back to English
                bolt.deprint(f"wxPython does not support the language family '"
                             f"{wanted_prefix}', will fall back to "
                             f"'{target_name := 'en_US'}'")
    lang_info = _wx.Locale.FindLanguageInfo(target_name)
    target_language = lang_info.Language
    target_locale = _wx.Locale(target_language)
    bolt.deprint(f"Set wxPython locale to '{target_name}'")
    # Next, set the Wrye Bash locale based on the one we grabbed from wx
    if po is mo is None:
        # We're using English or don't have a translation file - either way,
        # prepare the English translation
        trans = gettext.NullTranslations()
    else:
        try:
            # We have a translation file, check if it has to be compiled
            if not os.path.isfile(mo) or (os.path.getmtime(po) >
                                          os.path.getmtime(mo)):
                # Try compiling - have to do it differently if we're a
                # standalone build
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
                    from .env import python_tools_dir
                    m = os.path.join(python_tools_dir(), u'i18n', u'msgfmt.py')
                    subprocess.call([sys.executable, m, u'-o', mo, po])
            # We've successfully compiled the translation, read it into memory
            with open(mo, u'rb') as trans_file:
                trans = gettext.GNUTranslations(trans_file)
        except (UnicodeError, OSError):
            bolt.deprint('Error loading translation file:', traceback=True)
            trans = gettext.NullTranslations()
    # Everything has gone smoothly, install the translation and remember what
    # we ended up with as the final locale
    trans.install()
    bass.active_locale = target_name
    # adieu, user locale
    set_c_locale()
    return target_locale

def __get_translations_dir():
    trans_path = os.path.join(os.getcwd(), u'bash', u'l10n')
    if not os.path.exists(trans_path):
        # HACK: the CI has to run tests from the top dir, which causes us to
        # have a non-Mopy working dir here. Real fix is ditching the fake
        # startup and adding a real headless mode to WB (see #568, #554 and #600)
        trans_path = os.path.join(os.getcwd(), u'Mopy', u'bash', u'l10n')
    return trans_path

#------------------------------------------------------------------------------
# Internationalization
def _find_all_bash_modules(bash_path=None, cur_dir=None, _files=None):
    """Internal helper function. Returns a list of all Bash files as relative
    paths to the Mopy directory.

    :param bash_path: The relative path from Mopy.
    :param cur_dir: The directory to look for modules in. Defaults to cwd.
    :param _files: Internal parameter used to collect file recursively."""
    if bash_path is None: bash_path = u''
    if cur_dir is None: cur_dir = os.getcwd()
    if _files is None: _files = []
    _files.extend([os.path.join(bash_path, m) for m in os.listdir(cur_dir)
                   if m.lower().endswith((u'.py', u'.pyw'))]) ##: glob?
    # Find packages - returned format is (module_loader, name, is_pkg)
    for module_loader, pkg_name, is_pkg in pkgutil.iter_modules([cur_dir]):
        if not is_pkg: # Skip it if it's not a package
            continue
        # Recurse into the package we just found
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
    new_po = os.path.join(out_path, f'{lang}NEW.po')
    tmp_po = os.path.join(out_path, f'{lang}NEW.tmp')
    old_po = os.path.join(out_path, f'{lang}.po')
    gt_args = [u'p', u'-a', u'-o', new_po]
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
        from .env import python_tools_dir
        gt_args.insert(1, os.path.join(python_tools_dir(), u'i18n',
                                       u'pygettext.py'))
        subprocess.call(gt_args, shell=True)
    # Fill in any already translated stuff...?
    try:
        re_msg_ids_start = re.compile(b'#:')
        re_encoding = re.compile(
            br'"Content-Type:\s*text/plain;\s*charset=(.*?)\\n"$', re.I)
        re_non_escaped_quote = re.compile(r'([^\\])"')
        def sub_quote(regex_match):
            return regex_match.group(1) + r'\"'
        target_enc = None
        # Do all this in binary mode and carefully handle encodings
        with open(tmp_po, u'wb') as out:
            # Copy old translation file header, and get encoding for strings
            with open(old_po, u'rb') as ins:
                for old_line in ins:
                    if not target_enc:
                        # Chop off the terminating newline
                        encoding_match = re_encoding.match(
                            old_line.rstrip(b'\r\n'))
                        if encoding_match:
                            # Encoding names are all ASCII, so this is safe
                            target_enc = str(encoding_match.group(1), 'ascii')
                    if re_msg_ids_start.match(old_line):
                        break # Break once we hit the first translatable string
                    out.write(old_line)
            # Read through the new translation file, fill in any already
            # translated strings
            with open(new_po, u'rb') as ins:
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
                        stripped_line = str(new_line, target_enc)
                        stripped_line = stripped_line.strip(u'\r\n')[7:-1]
                        # Replace escape sequences - Quote, Tab, Backslash
                        stripped_line = stripped_line.replace(u'\\"', u'"')
                        stripped_line = stripped_line.replace(u'\\t', u'\t')
                        stripped_line = stripped_line.replace(u'\\\\', u'\\')
                        # Try translating, check if that changes the string
                        ##: This is a neat, pragmatic implementation - but of
                        # course limits us to only ever dumping translations
                        # for the current language
                        translated_line: str = _(stripped_line)
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
                            out.write(b'"\r\n')
                        else:
                            # Not translated, write out an empty msgstr
                            out.write(b'msgstr ""\r\n')
                    elif new_line.startswith(b'msgstr "'):
                        # Skip all msgstr lines from new_po (handled above)
                        continue
                    else:
                        out.write(new_line)
    except (OSError, UnicodeError):
        bolt.deprint(u'Error while dumping translation file:', traceback=True)
        try: os.remove(tmp_po)
        except OSError: pass
    else:
        # Replace the empty translation file generated by pygettext with the
        # temp one we just created
        try:
            os.remove(new_po)
            os.rename(tmp_po, new_po)
        except OSError:
            if os.path.exists(new_po):
                try: os.remove(tmp_po)
                except OSError: pass
    return new_po

#------------------------------------------------------------------------------
# Formatting
def format_date(secs: float) -> str:
    """Convert time to string formatted to to locale's default date/time.

    :param secs: Formats the specified number of seconds into a string."""
    try:
        local = time.localtime(secs)
    except (OSError, ValueError):
        # local time in windows can't handle negative values
        local = time.gmtime(secs)
    return time.strftime(u'%c', local)
