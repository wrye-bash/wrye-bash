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
#  Wrye Bash copyright (C) 2005-2009 Wrye, 2010-2014 Wrye Bash Team
#  https://github.com/wrye-bash
#
# =============================================================================

# Imports ---------------------------------------------------------------------
#--Standard
import cPickle
import StringIO
import copy
import locale
import os
import stat
import re
import shutil
import struct
import sys
import time
import subprocess
import collections
import codecs
import gettext
import traceback
import csv
import tempfile
from subprocess import Popen, PIPE
close_fds = True
import types
from binascii import crc32
import ConfigParser
import bass
import chardet
#-- To make commands executed with Popen hidden
startupinfo = None
if os.name == u'nt':
    startupinfo = subprocess.STARTUPINFO()
    startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW

#-- Forward declarations
class Path(object): pass

# Unicode ---------------------------------------------------------------------
#--decode unicode strings
#  This is only useful when reading fields from mods, as the encoding is not
#  known.  For normal filesystem interaction, these functions are not needed
encodingOrder = (
    'ascii',    # Plain old ASCII (0-127)
    'gbk',      # GBK (simplified Chinese + some)
    'cp932',    # Japanese
    'cp949',    # Korean
    'cp1252',   # English (extended ASCII)
    'utf8',
    'cp500',
    'UTF-16LE',
    'mbcs',
    )

_encodingSwap = {
    # The encoding detector reports back some encodings that
    # are subsets of others.  Use the better encoding when
    # given the option
    # 'reported encoding':'actual encoding to use',
    'GB2312': 'gbk',        # Simplified Chinese
    'SHIFT_JIS': 'cp932',   # Japanese
    'windows-1252': 'cp1252',
    'windows-1251': 'cp1251',
    }

# Preferred encoding to use when decoding/encoding strings in plugin files
# None = auto
# setting it tries the specified encoding first
pluginEncoding = None

def _getbestencoding(text):
    """Tries to detect the encoding a bitstream was saved in.  Uses Mozilla's
       detection library to find the best match (heurisitcs)"""
    result = chardet.detect(text)
    encoding,confidence = result['encoding'],result['confidence']
    encoding = _encodingSwap.get(encoding,encoding)
    ## Debug: uncomment the following to output stats on encoding detection
    #print
    #print '%s: %s (%s)' % (repr(text),encoding,confidence)
    return encoding,confidence

def _unicode(text,encoding=None,avoidEncodings=()):
    if isinstance(text,unicode) or text is None: return text
    # Try the user specified encoding first
    if encoding:
        try: return unicode(text,encoding)
        except UnicodeDecodeError: pass
    # Try to detect the encoding next
    encoding,confidence = _getbestencoding(text)
    if encoding and confidence >= 0.55 and (encoding not in avoidEncodings or confidence == 1.0):
        try: return unicode(text,encoding)
        except UnicodeDecodeError: pass
    # If even that fails, fall back to the old method, trial and error
    for encoding in encodingOrder:
        try: return unicode(text,encoding)
        except UnicodeDecodeError: pass
    raise UnicodeDecodeError(u'Text could not be decoded using any method')

def _encode(text,encodings=encodingOrder,firstEncoding=None,returnEncoding=False):
    if isinstance(text,str) or text is None:
        if returnEncoding: return (text,None)
        else: return text
    # Try user specified encoding
    if firstEncoding:
        try:
            text = text.encode(firstEncoding)
            if returnEncoding: return (text,firstEncoding)
            else: return text
        except UnicodeEncodeError:
            pass
    goodEncoding = None
    # Try the list of encodings in order
    for encoding in encodings:
        try:
            temp = text.encode(encoding)
            detectedEncoding = _getbestencoding(temp)
            if detectedEncoding == encoding:
                # This encoding also happens to be detected
                # By the encoding detector as the same thing,
                # which means use it!
                if returnEncoding: return (temp,encoding)
                else: return temp
            # The encoding detector didn't detect it, but
            # it works, so save it for later
            if not goodEncoding: goodEncoding = (temp,encoding)
        except UnicodeEncodeError:
            pass
    # Non of the encodings also where detectable via the
    # detector, so use the first one that encoded without error
    if goodEncoding:
        if returnEncoding: return goodEncoding
        else: return goodEncoding[0]
    raise UnicodeEncodeError(u'Text could not be encoded using any of the following encodings: %s' % encodings)

# Localization ----------------------------------------------------------------
def dumpTranslator(outPath,language,*files):
    """Dumps all tranlatable strings in python source files to a new text file.
       as this requires the source files, it will not work in WBSA mode, unless
       the source files are also installed"""
    outTxt = u'%sNEW.txt' % language
    fullTxt = os.path.join(outPath,outTxt)
    tmpTxt = os.path.join(outPath,u'%sNEW.tmp' % language)
    oldTxt = os.path.join(outPath,u'%s.txt' % language)
    if not files:
        file = os.path.split(__file__)[1]
        files = [x for x in os.listdir(os.getcwdu()) if (x.lower().endswith(u'.py') or x.lower().endswith(u'.pyw'))]
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
                        text = line.strip('\r\n')[7:-1]
                        # Replace escape sequences
                        text = text.replace('\\"','"')      # Quote
                        text = text.replace('\\t','\t')     # Tab
                        text = text.replace('\\\\', '\\')   # Backslash
                        translated = _(text)
                        if text != translated:
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

def initTranslator(language=None,path=None):
    if not language:
        try:
            language = locale.getlocale()[0].split('_',1)[0]
            language = _unicode(language)
        except UnicodeError:
            deprint(u'Still unicode problems detecting locale:', repr(locale.getlocale()),traceback=True)
            # Default to English
            language = u'English'
    path = path or os.path.join(u'bash',u'l10n')
    if language.lower() == u'german': language = u'de'
    txt,po,mo = (os.path.join(path,language+ext)
                 for ext in (u'.txt',u'.po',u'.mo'))
    if not os.path.exists(txt) and not os.path.exists(mo):
        if language.lower() != u'english':
            print u'No translation file for language:', language
        trans = gettext.NullTranslations()
    else:
        try:
            if not os.path.exists(mo) or (os.path.getmtime(txt) > os.path.getmtime(mo)):
                # Compile
                shutil.copy(txt,po)
                args = [u'm',u'-o',mo,po]
                if hasattr(sys,'frozen'):
                    import msgfmt
                    old_argv = sys.argv[:]
                    sys.argv = args
                    msgfmt.main()
                    sys.argv = old_argv
                else:
                    m = os.path.join(sys.prefix,u'Tools',u'i18n',u'msgfmt.py')
                    subprocess.call([m,u'-o',mo,po],shell=True)
                os.remove(po)
            # install translator
            with open(mo,'rb') as file:
                trans = gettext.GNUTranslations(file)
        except:
            print 'Error loading translation file:'
            traceback.print_exc()
            trans = gettext.NullTranslations()
    trans.install(unicode=True)

#--Do translator test and set
if locale.getlocale() == (None,None):
    locale.setlocale(locale.LC_ALL,u'')
initTranslator(bass.language)

CBash = 0
images_list = {
    295 : {
        u'3dsmax16.png' : 1176,
        u'3dsmax24.png' : 2152,
        u'3dsmax32.png' : 3225,
        u'3dsmaxblack16.png' : 1085,
        u'3dsmaxblack24.png' : 1925,
        u'3dsmaxblack32.png' : 2669,
        u'abcamberaudioconverter16.png' : 1271,
        u'abcamberaudioconverter24.png' : 2468,
        u'abcamberaudioconverter32.png' : 3888,
        u'andreamosaic16.png' : 807,
        u'andreamosaic24.png' : 1111,
        u'andreamosaic32.png' : 1191,
        u'anifx16.png' : 1204,
        u'anifx24.png' : 2192,
        u'anifx32.png' : 3292,
        u'artofillusion16.png' : 1086,
        u'artofillusion24.png' : 1975,
        u'artofillusion32.png' : 2869,
        u'artweaver05_16.png' : 1159,
        u'artweaver05_24.png' : 2097,
        u'artweaver05_32.png' : 3178,
        u'artweaver16.png' : 1193,
        u'artweaver24.png' : 2286,
        u'artweaver32.png' : 3565,
        u'audacity16.png' : 1175,
        u'audacity24.png' : 2269,
        u'audacity32.png' : 3319,
        u'autocad16.png' : 1083,
        u'autocad24.png' : 1906,
        u'autocad32.png' : 2539,
        u'bashmon16.png' : 1212,
        u'bashmon24.png' : 2311,
        u'bashmon32.png' : 3025,
        u'bash_16.png' : 1198,
        u'bash_16_blue.png' : 1198,
        u'bash_24.png' : 1230,
        u'bash_24_2.png' : 1230,
        u'bash_24_blue.png' : 1230,
        u'bash_32.ico' : 2238,
        u'bash_32.png' : 1338,
        u'bash_32_2.png' : 1338,
        u'bash_32_blue.png' : 1338,
        u'blender16.png' : 3504,
        u'blender24.png' : 1967,
        u'blender32.png' : 2668,
        u'boss16.png' : 362,
        u'boss24.png' : 679,
        u'boss32.png' : 579,
        u'brick16.png' : 452,
        u'brick24.png' : 2248,
        u'brick32.png' : 2092,
        u'bricksntiles16.png' : 1258,
        u'bricksntiles24.png' : 2441,
        u'bricksntiles32.png' : 3410,
        u'brick_edit16.png' : 775,
        u'brick_edit24.png' : 4562,
        u'brick_edit32.png' : 5880,
        u'brick_error16.png' : 798,
        u'brick_error24.png' : 4599,
        u'brick_error32.png' : 5383,
        u'brick_go16.png' : 790,
        u'brick_go24.png' : 4534,
        u'brick_go32.png' : 5857,
        u'bsacommander16.png' : 685,
        u'bsacommander24.png' : 2276,
        u'bsacommander32.png' : 2864,
        u'calculator16.png' : 952,
        u'calculator24.png' : 1646,
        u'calculator32.png' : 2328,
        u'cancel.png' : 36780,
        u'check.png' : 689,
        u'checkbox_blue_imp.png' : 162,
        u'checkbox_blue_inc.png' : 875,
        u'checkbox_blue_off.png' : 115,
        u'checkbox_blue_on.png' : 180,
        u'checkbox_blue_on_24.png' : 405,
        u'checkbox_blue_on_32.png' : 254,
        u'checkbox_green_imp.png' : 156,
        u'checkbox_green_inc.png' : 875,
        u'checkbox_green_inc_wiz.png' : 420,
        u'checkbox_green_off.png' : 116,
        u'checkbox_green_off_24.png' : 2887,
        u'checkbox_green_off_32.png' : 2883,
        u'checkbox_green_off_wiz.png' : 393,
        u'checkbox_green_on.png' : 174,
        u'checkbox_green_on_24.png' : 403,
        u'checkbox_green_on_32.png' : 248,
        u'checkbox_grey_inc.png' : 159,
        u'checkbox_grey_off.png' : 125,
        u'checkbox_grey_on.png' : 173,
        u'checkbox_orange_imp.png' : 156,
        u'checkbox_orange_inc.png' : 875,
        u'checkbox_orange_inc_wiz.png' : 421,
        u'checkbox_orange_off.png' : 116,
        u'checkbox_orange_off_wiz.png' : 392,
        u'checkbox_orange_on.png' : 181,
        u'checkbox_purple_imp.png' : 168,
        u'checkbox_purple_inc.png' : 875,
        u'checkbox_purple_off.png' : 136,
        u'checkbox_purple_on.png' : 194,
        u'checkbox_red_imp.png' : 155,
        u'checkbox_red_inc.png' : 875,
        u'checkbox_red_inc_wiz.png' : 418,
        u'checkbox_red_off.png' : 115,
        u'checkbox_red_off_24.png' : 2889,
        u'checkbox_red_off_32.png' : 2883,
        u'checkbox_red_off_wiz.png' : 395,
        u'checkbox_red_on.png' : 174,
        u'checkbox_red_x.png' : 875,
        u'checkbox_red_x_24.png' : 3037,
        u'checkbox_red_x_32.png' : 2989,
        u'checkbox_white_inc.png' : 159,
        u'checkbox_white_inc_wiz.png' : 416,
        u'checkbox_white_off.png' : 125,
        u'checkbox_white_off_wiz.png' : 400,
        u'checkbox_white_on.png' : 174,
        u'checkbox_yellow_imp.png' : 161,
        u'checkbox_yellow_inc.png' : 173,
        u'checkbox_yellow_inc_wiz.png' : 421,
        u'checkbox_yellow_off.png' : 114,
        u'checkbox_yellow_off_wiz.png' : 393,
        u'checkbox_yellow_on.png' : 184,
        u'crazybump16.png' : 1031,
        u'crazybump24.png' : 1768,
        u'crazybump32.png' : 2483,
        u'custom1016.png' : 349,
        u'custom1024.png' : 782,
        u'custom1032.png' : 723,
        u'custom1116.png' : 299,
        u'custom1124.png' : 679,
        u'custom1132.png' : 610,
        u'custom116.png' : 289,
        u'custom1216.png' : 359,
        u'custom1224.png' : 768,
        u'custom1232.png' : 717,
        u'custom124.png' : 625,
        u'custom1316.png' : 362,
        u'custom132.png' : 576,
        u'custom1324.png' : 778,
        u'custom1332.png' : 710,
        u'custom1416.png' : 334,
        u'custom1424.png' : 741,
        u'custom1432.png' : 683,
        u'custom1516.png' : 357,
        u'custom1524.png' : 771,
        u'custom1532.png' : 726,
        u'custom1616.png' : 372,
        u'custom1624.png' : 790,
        u'custom1632.png' : 751,
        u'custom1716.png' : 334,
        u'custom1724.png' : 726,
        u'custom1732.png' : 665,
        u'custom1816.png' : 365,
        u'custom1824.png' : 783,
        u'custom1832.png' : 736,
        u'custom216.png' : 364,
        u'custom224.png' : 679,
        u'custom232.png' : 668,
        u'custom316.png' : 390,
        u'custom324.png' : 700,
        u'custom332.png' : 678,
        u'custom416.png' : 344,
        u'custom424.png' : 675,
        u'custom432.png' : 629,
        u'custom516.png' : 387,
        u'custom524.png' : 699,
        u'custom532.png' : 675,
        u'custom616.png' : 392,
        u'custom624.png' : 725,
        u'custom632.png' : 703,
        u'custom716.png' : 332,
        u'custom724.png' : 662,
        u'custom732.png' : 619,
        u'custom816.png' : 402,
        u'custom824.png' : 717,
        u'custom832.png' : 690,
        u'custom916.png' : 406,
        u'custom924.png' : 732,
        u'custom932.png' : 709,
        u'database_connect16.png' : 763,
        u'database_connect24.png' : 4548,
        u'database_connect32.png' : 5079,
        u'ddsconverter16.png' : 1123,
        u'ddsconverter24.png' : 2134,
        u'ddsconverter32.png' : 2809,
        u'debug16.png' : 1133,
        u'debug24.png' : 2167,
        u'debug32.png' : 3142,
        u'deeppaint16.png' : 1039,
        u'deeppaint24.png' : 1664,
        u'deeppaint32.png' : 2300,
        u'diamond_green_inc.png' : 208,
        u'diamond_green_inc_wiz.png' : 457,
        u'diamond_green_off.png' : 189,
        u'diamond_green_off_wiz.png' : 431,
        u'diamond_grey_inc.png' : 189,
        u'diamond_grey_off.png' : 189,
        u'diamond_orange_inc.png' : 217,
        u'diamond_orange_inc_wiz.png' : 455,
        u'diamond_orange_off.png' : 195,
        u'diamond_orange_off_wiz.png' : 430,
        u'diamond_red_inc.png' : 210,
        u'diamond_red_inc_wiz.png' : 451,
        u'diamond_red_off.png' : 191,
        u'diamond_red_off_wiz.png' : 430,
        u'diamond_white_inc.png' : 190,
        u'diamond_white_off.png' : 190,
        u'diamond_white_off_wiz.png' : 429,
        u'diamond_yellow_inc.png' : 209,
        u'diamond_yellow_inc_wiz.png' : 451,
        u'diamond_yellow_off.png' : 189,
        u'diamond_yellow_off_wiz.png' : 428,
        u'docbrowser16.png' : 1010,
        u'docbrowser24.png' : 1979,
        u'docbrowser32.png' : 2845,
        u'doc_on.png' : 149,
        u'dogwaffle16.png' : 921,
        u'dogwaffle24.png' : 1515,
        u'dogwaffle32.png' : 2123,
        u'dos.png' : 362,
        u'eggtranslator16.png' : 1101,
        u'eggtranslator24.png' : 2059,
        u'eggtranslator32.png' : 3267,
        u'error.jpg' : 45270,
        u'evgaprecision16.png' : 1185,
        u'evgaprecision24.png' : 2123,
        u'evgaprecision32.png' : 3267,
        u'exclamation.png' : 701,
        u'faststoneimageviewer16.png' : 1116,
        u'faststoneimageviewer24.png' : 2125,
        u'faststoneimageviewer32.png' : 3202,
        u'filezilla16.png' : 853,
        u'filezilla24.png' : 1448,
        u'filezilla32.png' : 1601,
        u'finish.png' : 42978,
        u'fraps16.png' : 1153,
        u'fraps24.png' : 2075,
        u'fraps32.png' : 2857,
        u'freemind16.png' : 1215,
        u'freemind24.png' : 2223,
        u'freemind32.png' : 3279,
        u'freemind8.1custom_16.png' : 1244,
        u'freemind8.1custom_24.png' : 2359,
        u'freemind8.1custom_32.png' : 3605,
        u'freeplane16.png' : 1165,
        u'freeplane24.png' : 2139,
        u'freeplane32.png' : 3176,
        u'genetica16.png' : 1254,
        u'genetica24.png' : 2424,
        u'genetica32.png' : 3697,
        u'geneticaviewer16.png' : 1230,
        u'geneticaviewer24.png' : 2237,
        u'geneticaviewer32.png' : 3073,
        u'geniuxphotoefx16.png' : 1259,
        u'geniuxphotoefx24.png' : 2405,
        u'geniuxphotoefx32.png' : 3674,
        u'gimp16.png' : 997,
        u'gimp24.png' : 1740,
        u'gimp32.png' : 2489,
        u'gimpshop16.png' : 1135,
        u'gimpshop24.png' : 2435,
        u'gimpshop32.png' : 2895,
        u'gmax16.png' : 913,
        u'gmax24.png' : 1639,
        u'gmax32.png' : 2419,
        u'group_gear16.png' : 824,
        u'group_gear24.png' : 4698,
        u'group_gear32.png' : 6136,
        u'help16.png' : 3730,
        u'help24.png' : 4660,
        u'help32.png' : 5518,
        u'icofx16.png' : 1227,
        u'icofx24.png' : 2266,
        u'icofx32.png' : 3285,
        u'ini-all natural.png' : 121810,
        u'ini-oblivion.png' : 126961,
        u'inkscape16.png' : 1125,
        u'inkscape24.png' : 1976,
        u'inkscape32.png' : 2906,
        u"insanity'sreadmegenerator16.png" : 1187,
        u"insanity'sreadmegenerator24.png" : 2227,
        u"insanity'sreadmegenerator32.png" : 3436,
        u"insanity'srng16.png" : 1164,
        u"insanity'srng24.png" : 2223,
        u"insanity'srng32.png" : 3343,
        u'interactivemapofcyrodiil16.png' : 960,
        u'interactivemapofcyrodiil24.png' : 1840,
        u'interactivemapofcyrodiil32.png' : 2860,
        u'irfanview16.png' : 1124,
        u'irfanview24.png' : 2016,
        u'irfanview32.png' : 2828,
        u'isobl16.png' : 1056,
        u'isobl24.png' : 2088,
        u'isobl32.png' : 3314,
        u'itemizer16.png' : 972,
        u'itemizer24.png' : 1733,
        u'itemizer32.png' : 2472,
        u'k-3d16.png' : 1183,
        u'k-3d24.png' : 2130,
        u'k-3d32.png' : 3173,
        u'list16.png' : 1153,
        u'list24.png' : 2061,
        u'list32.png' : 2902,
        u'logitechkeyboard16.png' : 622,
        u'logitechkeyboard24.png' : 1625,
        u'logitechkeyboard32.png' : 2154,
        u'mapzone16.png' : 1021,
        u'mapzone24.png' : 1767,
        u'mapzone32.png' : 2576,
        u'maya16.png' : 960,
        u'maya24.png' : 1755,
        u'maya32.png' : 2748,
        u'mcowavi32.png' : 3921,
        u'mcowbash16.png' : 1092,
        u'mediamonkey16.png' : 1127,
        u'mediamonkey24.png' : 2076,
        u'mediamonkey32.png' : 2975,
        u'meshlab16.png' : 1079,
        u'meshlab24.png' : 1860,
        u'meshlab32.png' : 2573,
        u'milkshape3d16.png' : 988,
        u'milkshape3d24.png' : 1694,
        u'milkshape3d32.png' : 2422,
        u'modchecker16.png' : 1120,
        u'modchecker24.png' : 1763,
        u'modchecker32.png' : 3161,
        u'modlistgenerator16.png' : 1203,
        u'modlistgenerator24.png' : 2265,
        u'modlistgenerator32.png' : 3321,
        u'mtes4manager16.png' : 1182,
        u'mtes4manager24.png' : 2479,
        u'mtes4manager32.png' : 3246,
        u'mudbox16.png' : 1066,
        u'mudbox24.png' : 1997,
        u'mudbox32.png' : 2869,
        u'mypaint16.png' : 1081,
        u'mypaint24.png' : 1986,
        u'mypaint32.png' : 2787,
        u'nifskope16.png' : 1233,
        u'nifskope24.png' : 2331,
        u'nifskope32.png' : 3583,
        u'niftools16.png' : 974,
        u'niftools24.png' : 1968,
        u'niftools32.png' : 2503,
        u'notepad++16.png' : 1203,
        u'notepad++24.png' : 2234,
        u'notepad++32.png' : 3490,
        u'nvidia16.png' : 988,
        u'nvidia24.png' : 1823,
        u'nvidia32.png' : 2814,
        u'nvidiamelody16.png' : 865,
        u'nvidiamelody24.png' : 1481,
        u'nvidiamelody32.png' : 2187,
        u'oblivion16.png' : 3542,
        u'oblivion24.png' : 1528,
        u'oblivion32.png' : 3090,
        u'oblivionbookcreator16.png' : 945,
        u'oblivionbookcreator24.png' : 1676,
        u'oblivionbookcreator32.png' : 2405,
        u'oblivionfaceexchangerlite16.png' : 910,
        u'oblivionfaceexchangerlite24.png' : 1550,
        u'oblivionfaceexchangerlite32.png' : 2208,
        u'obmm16.png' : 1093,
        u'obmm24.png' : 2101,
        u'obmm32.png' : 3176,
        u'obse16.png' : 281,
        u'openoffice16.png' : 1090,
        u'openoffice24.png' : 1945,
        u'openoffice32.png' : 2735,
        u'page_find16.png' : 879,
        u'page_find24.png' : 4768,
        u'page_find32.png' : 5269,
        u'paint.net16.png' : 1134,
        u'paint.net24.png' : 2072,
        u'paint.net32.png' : 2984,
        u'paintshopprox316.png' : 3588,
        u'paintshopprox324.png' : 4575,
        u'paintshopprox332.png' : 5241,
        u'pes16.png' : 955,
        u'pes24.png' : 1834,
        u'pes32.png' : 2735,
        u'photobie16.png' : 1060,
        u'photobie24.png' : 1826,
        u'photobie32.png' : 2544,
        u'photofiltre16.png' : 1006,
        u'photofiltre24.png' : 1777,
        u'photofiltre32.png' : 2616,
        u'photoscape16.png' : 983,
        u'photoscape24.png' : 1722,
        u'photoscape32.png' : 2224,
        u'photoseam16.png' : 1271,
        u'photoseam24.png' : 2441,
        u'photoseam32.png' : 3775,
        u'photoshop16.png' : 1275,
        u'photoshop24.png' : 2490,
        u'photoshop32.png' : 3929,
        u'pixelformer16.png' : 1045,
        u'pixelformer24.png' : 1088,
        u'pixelformer32.png' : 1121,
        u'pixelstudiopro16.png' : 1088,
        u'pixelstudiopro24.png' : 1886,
        u'pixelstudiopro32.png' : 2371,
        u'pixia16.png' : 1236,
        u'pixia24.png' : 2332,
        u'pixia32.png' : 3547,
        u'pythonlogo16.png' : 1145,
        u'pythonlogo24.png' : 1963,
        u'pythonlogo32.png' : 2625,
        u'questionmarksquare16.png' : 363,
        u'radvideotools16.png' : 1182,
        u'radvideotools24.png' : 2117,
        u'radvideotools32.png' : 3072,
        u'randomnpc16.png' : 928,
        u'randomnpc24.png' : 1751,
        u'randomnpc32.png' : 2434,
        u'red_x.png' : 178,
        u'save_off.png' : 908,
        u'save_on.png' : 177,
        u'sculptris16.png' : 1229,
        u'sculptris24.png' : 2352,
        u'sculptris32.png' : 3646,
        u'selectmany.jpg' : 110594,
        u'selectone.jpg' : 85738,
        u'skype16.png' : 1164,
        u'skype24.png' : 2129,
        u'skype32.png' : 2897,
        u'softimagemodtool16.png' : 927,
        u'softimagemodtool24.png' : 1626,
        u'softimagemodtool32.png' : 2413,
        u'sourceforge16.png' : 680,
        u'speedtree16.png' : 993,
        u'speedtree24.png' : 1970,
        u'speedtree32.png' : 2806,
        u'steam16.png' : 537,
        u'steam24.png' : 836,
        u'steam32.png' : 1004,
        u'switch16.png' : 1041,
        u'switch24.png' : 1800,
        u'switch32.png' : 2538,
        u'table_error16.png' : 687,
        u'table_error24.png' : 4714,
        u'table_error32.png' : 4978,
        u'tabula16.png' : 1019,
        u'tabula24.png' : 1899,
        u'tabula32.png' : 3041,
        u'tes4edit16.png' : 1156,
        u'tes4edit24.png' : 2000,
        u'tes4edit32.png' : 2547,
        u'tes4files16.png' : 849,
        u'tes4files24.png' : 2262,
        u'tes4files32.png' : 3789,
        u'tes4gecko16.png' : 1197,
        u'tes4gecko24.png' : 2230,
        u'tes4gecko32.png' : 2803,
        u'tesvgecko16.png' : 639,
        u'tesvgecko24.png' : 954,
        u'tesvgecko32.png' : 1535,
        u'tes4lodgen16.png' : 1227,
        u'tes4lodgen24.png' : 2467,
        u'tes4lodgen32.png' : 3721,
        u'tes4trans16.png' : 1095,
        u'tes4trans24.png' : 1923,
        u'tes4trans32.png' : 2503,
        u'tes4view16.png' : 1131,
        u'tes4view24.png' : 2071,
        u'tes4view32.png' : 2778,
        u'tes4wizbain16.png' : 1182,
        u'tes4wizbain24.png' : 2161,
        u'tes4wizbain32.png' : 3324,
        u'tesa16.png' : 1175,
        u'tesa24.png' : 2173,
        u'tesa32.png' : 3083,
        u'tescs16.png' : 1078,
        u'tescs24.png' : 1894,
        u'tescs32.png' : 2505,
        u'tesnexus16.png' : 272,
        u'texturemaker16.png' : 1158,
        u'texturemaker24.png' : 2137,
        u'texturemaker32.png' : 3277,
        u'treed16.png' : 807,
        u'treed24.png' : 1738,
        u'treed32.png' : 2121,
        u'truespace16.png' : 1244,
        u'truespace24.png' : 2328,
        u'truespace32.png' : 3541,
        u'twistedbrush16.png' : 1089,
        u'twistedbrush24.png' : 2112,
        u'twistedbrush32.png' : 3159,
        u'unofficialelderscrollspages16.png' : 1216,
        u'unofficialelderscrollspages24.png' : 2277,
        u'unofficialelderscrollspages32.png' : 3685,
        u'versions.png' : 42287,
        u'winamp16.png' : 1098,
        u'winamp24.png' : 2043,
        u'winamp32.png' : 2787,
        u'wings3d16.png' : 1015,
        u'wings3d24.png' : 1779,
        u'wings3d32.png' : 2324,
        u'winmerge16.png' : 1136,
        u'winmerge24.png' : 2085,
        u'winmerge32.png' : 2981,
        u'winsnap16.png' : 1268,
        u'winsnap24.png' : 2474,
        u'winsnap32.png' : 3706,
        u'wizard.png' : 442,
        u'wizardscripthighlighter.jpg' : 175127,
        u'wryebash_01.png' : 128009,
        u'wryebash_02.png' : 13209,
        u'wryebash_03.png' : 130445,
        u'wryebash_04.png' : 91759,
        u'wryebash_05.png' : 237791,
        u'wryebash_06.png' : 452714,
        u'wryebash_07.png' : 32293,
        u'wryebash_08.png' : 20960,
        u'wryebash_docbrowser.png' : 37078,
        u'wryebash_peopletab.png' : 83310,
        u'wryemonkey16.jpg' : 721,
        u'wryemonkey16.png' : 1011,
        u'wryemonkey24.png' : 1982,
        u'wryemonkey32.png' : 3222,
        u'wrye_monkey_87.jpg' : 2682,
        u'wtv16.png' : 990,
        u'wtv24.png' : 1902,
        u'wtv32.png' : 2937,
        u'x.png' : 655,
        u'xnormal16.png' : 806,
        u'xnormal24.png' : 1355,
        u'xnormal32.png' : 1827,
        u'xnview16.png' : 1101,
        u'xnview24.png' : 2145,
        u'xnview32.png' : 2926,
        u'zoom_on.png' : 237
        },
    }
# Errors ----------------------------------------------------------------------
class BoltError(Exception):
    """Generic error with a string message."""
    def __init__(self,message):
        self.message = message
    def __str__(self):
        return self.message

#------------------------------------------------------------------------------
class AbstractError(BoltError):
    """Coding Error: Abstract code section called."""
    def __init__(self,message=u'Abstract section called.'):
        BoltError.__init__(self,message)

#------------------------------------------------------------------------------
class ArgumentError(BoltError):
    """Coding Error: Argument out of allowed range of values."""
    def __init__(self,message=u'Argument is out of allowed ranged of values.'):
        BoltError.__init__(self,message)

#------------------------------------------------------------------------------
class StateError(BoltError):
    """Error: Object is corrupted."""
    def __init__(self,message=u'Object is in a bad state.'):
        BoltError.__init__(self,message)

#------------------------------------------------------------------------------
class UncodedError(BoltError):
    """Coding Error: Call to section of code that hasn't been written."""
    def __init__(self,message=u'Section is not coded yet.'):
        BoltError.__init__(self,message)

#------------------------------------------------------------------------------
class CancelError(BoltError):
    """User pressed 'Cancel' on the progress meter."""
    def __init__(self,message=u'Action aborted by user.'):
        BoltError.__init__(self, message)

class SkipError(BoltError):
    """User pressed Skipped n operations."""
    def __init__(self,count=None,message=u'%s actions skipped by user.'):
        if count:
            message = message % count
        else:
            message = u'Action skipped by user.'
        BoltError.__init__(self,message)

#------------------------------------------------------------------------------
class PermissionError(BoltError):
    """Wrye Bash doesn't have permission to access the specified file/directory."""
    def __init__(self,message=u'Access is denied.'):
        BoltError.__init__(self,message)

#------------------------------------------------------------------------------
class FileError(BoltError):
    """TES4/Tes4SaveFile Error: File is corrupted."""
    def __init__(self,inName,message):
        BoltError.__init__(self,message)
        self.inName = inName

    def __str__(self):
        if self.inName:
            if isinstance(self.inName, basestring):
                return self.inName+u': '+self.message
            return self.inName.s+u': '+self.message
        else:
            return u'Unknown File: '+self.message

#------------------------------------------------------------------------------
class FileEditError(BoltError):
    """Unable to edit a file"""
    def __init__(self,filePath,message=None):
        message = message or u"Unable to edit file %s." % filePath.s
        BoltError.__init__(self,message)
        self.filePath = filePath

# LowStrings ------------------------------------------------------------------
class LString(object):
    """Strings that compare as lower case strings."""
    __slots__ = ('_s','_cs')

    def __init__(self,s):
        if isinstance(s,LString):
            self._s = s._s
            self._cs = s._cs
        else:
            self._s = s
            self._cs = s.lower()

    def __getstate__(self):
        """Used by pickler. _cs is redundant,so don't include."""
        return self._s

    def __setstate__(self,s):
        """Used by unpickler. Reconstruct _cs."""
        self._s = s
        self._cs = s.lower()

    def __len__(self):
        return len(self._s)

    def __str__(self):
        return self._s

    def __repr__(self):
        return u'bolt.LString('+repr(self._s)+u')'

    def __add__(self,other):
        return LString(self._s + other)

    #--Hash/Compare
    def __hash__(self):
        return hash(self._cs)
    def __cmp__(self, other):
        if isinstance(other,LString): return cmp(self._cs, other._cs)
        else: return cmp(self._cs, other.lower())

# sio - StringIO wrapper so it uses the 'with' statement, so they can be used
#  in the same functions that accept files as input/output as well.  Really,
#  StringIO objects don't need to 'close' ever, since the data is unallocated
#  once the object is destroyed.
#------------------------------------------------------------------------------
class sio(StringIO.StringIO):
    def __enter__(self): return self
    def __exit__(self,*args,**kwdargs): self.close()

# Paths -----------------------------------------------------------------------
#------------------------------------------------------------------------------
_gpaths = {}
#Path = None
def GPath(name):
    """Returns common path object for specified name/path."""
    if name is None: return None
    elif not name: norm = name
    elif isinstance(name,Path): norm = name._s
    elif isinstance(name,unicode): norm = os.path.normpath(name)
    else: norm = os.path.normpath(_unicode(name))
    path = _gpaths.get(norm)
    if path is not None: return path
    else: return _gpaths.setdefault(norm,Path(norm))

def GPathPurge():
    """Cleans out the _gpaths dictionary of any unused bolt.Path objects.
       We cannot use a weakref.WeakValueDictionary in this case for 2 reasons:
        1) bolt.Path, due to its class structure, cannot be made into weak
           references
        2) the objects would be deleted as soon as the last reference goes
           out of scope (not the behavior we want).  We want the object to
           stay alive as long as we will possibly be needing it, IE: as long
           as we're still on the same tab.
       So instead, we'll manually call our flushing function a few times:
        1) When switching tabs
        2) Prior to building a bashed patch
        3) Prior to saving settings files
    """
    for key in _gpaths.keys():
        # Using .keys() allows use to modify the dictionary while iterating
        if sys.getrefcount(_gpaths[key]) == 2:
            # 1 for the reference in the _gpath dictionary,
            # 1 for the temp reference passed to sys.getrefcount
            # meanin the object is not reference anywhere else
            del _gpaths[key]

#------------------------------------------------------------------------------
class Path(object):
    """A file path. May be just a directory, filename or full path."""
    """Paths are immutable objects that represent file directory paths."""

    #--Class Vars/Methods -------------------------------------------
    norm_path = {} #--Dictionary of paths
    mtimeResets = [] #--Used by getmtime

    @staticmethod
    def get(name):
        """Returns path object for specified name/path."""
        if isinstance(name,Path): norm = name._s
        elif isinstance(name,str): norm = os.path.normpath(_unicode(name))
        else: norm = os.path.normpath(name)
        return Path.norm_path.setdefault(norm,Path(norm))

    @staticmethod
    def getNorm(name):
        """Return the normpath for specified name/path object."""
        if isinstance(name,Path): return name._s
        elif not name: return name
        elif isinstance(name,str): name = _unicode(name)
        return os.path.normpath(name)

    @staticmethod
    def getCase(name):
        """Return the normpath+normcase for specified name/path object."""
        if not name: return name
        if isinstance(name,Path): return name._cs
        elif isinstance(name,str): name = _unicode(name)
        return os.path.normcase(os.path.normpath(name))

    @staticmethod
    def getcwd():
        return Path(os.getcwdu())

    def setcwd(self):
        """Set cwd. Works as either instance or class method."""
        if isinstance(self,Path): dir = self._s
        else: dir = self
        os.chdir(dir)

    #--Instance stuff --------------------------------------------------
    #--Slots: _s is normalized path. All other slots are just pre-calced
    #  variations of it.
    __slots__ = ('_s','_cs','_csroot','_sroot','_shead','_stail','_ext','_cext','_sbody','_csbody')

    def __init__(self, name):
        """Initialize."""
        if isinstance(name,Path):
            self.__setstate__(name._s)
        else:
            self.__setstate__(name)

    def __getstate__(self):
        """Used by pickler. _cs is redundant,so don't include."""
        return self._s

    def __setstate__(self,norm):
        """Used by unpickler. Reconstruct _cs."""
        # Older pickle files stored filename in str, not unicode
        if not isinstance(norm,unicode): norm = _unicode(norm)
        self._s = norm
        self._cs = os.path.normcase(self._s)
        self._sroot,self._ext = os.path.splitext(self._s)
        self._shead,self._stail = os.path.split(self._s)
        self._cext = os.path.normcase(self._ext)
        self._csroot = os.path.normcase(self._sroot)
        self._sbody = os.path.basename(os.path.splitext(self._s)[0])
        self._csbody = os.path.normcase(self._sbody)

    def __len__(self):
        return len(self._s)

    def __repr__(self):
        return u"bolt.Path("+repr(self._s)+u")"

    def __unicode__(self):
        return self._s

    #--Properties--------------------------------------------------------
    #--String/unicode versions.
    @property
    def s(self):
        "Path as string."
        return self._s
    @property
    def cs(self):
        "Path as string in normalized case."
        return self._cs
    @property
    def csroot(self):
        "Root as string."
        return self._csroot
    @property
    def sroot(self):
        "Root as string."
        return self._sroot
    @property
    def shead(self):
        "Head as string."
        return self._shead
    @property
    def stail(self):
        "Tail as string."
        return self._stail
    @property
    def sbody(self):
        "For alpha\beta.gamma returns beta as string."
        return self._sbody
    @property
    def csbody(self):
        "For alpha\beta.gamma returns beta as string in normalized case."
        return self._csbody

    #--Head, tail
    @property
    def headTail(self):
        "For alpha\beta.gamma returns (alpha,beta.gamma)"
        return map(GPath,(self._shead,self._stail))
    @property
    def head(self):
        "For alpha\beta.gamma, returns alpha."
        return GPath(self._shead)
    @property
    def tail(self):
        "For alpha\beta.gamma, returns beta.gamma."
        return GPath(self._stail)
    @property
    def body(self):
        "For alpha\beta.gamma, returns beta."
        return GPath(self._sbody)

    #--Root, ext
    @property
    def rootExt(self):
        return (GPath(self._sroot),self._ext)
    @property
    def root(self):
        "For alpha\beta.gamma returns alpha\beta"
        return GPath(self._sroot)
    @property
    def ext(self):
        "Extension (including leading period, e.g. '.txt')."
        return self._ext
    @property
    def cext(self):
        "Extension in normalized case."
        return self._cext
    @property
    def temp(self,unicodeSafe=True):
        """Temp file path.  If unicodeSafe is True, the returned
        temp file will be a fileName that can be passes through Popen
        (Popen automatically tries to encode the name)"""
        baseDir = GPath(tempfile.gettempdir()).join(u'WryeBash_temp')
        baseDir.makedirs()
        dirJoin = baseDir.join
        if unicodeSafe:
            try:
                self._s.encode('ascii')
                return dirJoin(self.tail+u'.tmp')
            except UnicodeEncodeError:
                ret = unicode(self._s.encode('ascii','xmlcharrefreplace'),'ascii')+u'_unicode_safe.tmp'
                return dirJoin(ret)
        else:
            return dirJoin(self.tail+u'.tmp')

    @staticmethod
    def tempDir(prefix=None):
        return GPath(tempfile.mkdtemp(prefix=prefix))

    @staticmethod
    def baseTempDir():
        return GPath(tempfile.gettempdir())

    @property
    def backup(self):
        "Backup file path."
        return self+u'.bak'

    #--size, atime, ctime
    @property
    def size(self):
        "Size of file or directory."
        if self.isdir():
            join = os.path.join
            getSize = os.path.getsize
            try:
                return sum([sum(map(getSize,map(lambda z: join(x,z),files))) for x,y,files in os.walk(self._s)])
            except ValueError:
                return 0
        else:
            try:
                return os.path.getsize(self._s)
            except WindowsError, werr:
                    if werr.winerror != 123: raise
                    deprint(u'Unable to determine size of %s - probably a unicode error' % self._s)
                    return 0
    @property
    def atime(self):
        try:
            return os.path.getatime(self._s)
        except WindowsError, werr:
            if werr.winerror != 123: raise
            deprint(u'Unable to determine atime of %s - probably a unicode error' % self._s)
            return 1309853942.895 #timestamp of oblivion.exe (also known as any random time may work).
    @property
    def ctime(self):
        return os.path.getctime(self._s)

    #--Mtime
    def getmtime(self,maxMTime=False):
        """Returns mtime for path. But if mtime is outside of epoch, then resets
        mtime to an in-epoch date and uses that."""
        if self.isdir() and maxMTime:
            #fastest implementation I could make
            c = []
            cExtend = c.extend
            join = os.path.join
            getM = os.path.getmtime
            try:
                [cExtend([getM(join(root,dir)) for dir in dirs] + [getM(join(root,file)) for file in files]) for root,dirs,files in os.walk(self._s)]
            except: #slower but won't fail (fatally) on funky unicode files when Bash in ANSI Mode.
                [cExtend([GPath(join(root,dir)).mtime for dir in dirs] + [GPath(join(root,file)).mtime for file in files]) for root,dirs,files in os.walk(self._s)]
            try:
                return max(c)
            except ValueError:
                return 0
        try:
            mtime = int(os.path.getmtime(self._s))
        except WindowsError, werr:
                if werr.winerror != 123: raise
                deprint(u'Unable to determine modified time of %s - probably a unicode error' % self._s)
                mtime = 1146007898.0 #0blivion.exe's time... random basically.
        #--Y2038 bug? (os.path.getmtime() can't handle years over unix epoch)
        if mtime <= 0:
            import random
            #--Kludge mtime to a random time within 10 days of 1/1/2037
            mtime = time.mktime((2037,1,1,0,0,0,3,1,0))
            mtime += random.randint(0,10*24*60*60) #--10 days in seconds
            self.mtime = mtime
            Path.mtimeResets.append(self)
        return mtime
    def setmtime(self,mtime):
        try:
            os.utime(self._s,(self.atime,int(mtime)))
        except WindowsError, werr:
            if werr.winerror != 123: raise
            deprint(u'Unable to set modified time of %s - probably a unicode error' % self._s)
    mtime = property(getmtime,setmtime,doc="Time file was last modified.")

    @property
    def stat(self):
        """File stats"""
        return os.stat(self._s)

    @property
    def version(self):
        """File version (exe/dll) embeded in the file properties (windows only)."""
        try:
            import win32api
            info = win32api.GetFileVersionInfo(self._s,u'\\')
            ms = info['FileVersionMS']
            ls = info['FileVersionLS']
            version = (win32api.HIWORD(ms),win32api.LOWORD(ms),win32api.HIWORD(ls),win32api.LOWORD(ls))
        except:
            version = (0,0,0,0)
        return version

    @property
    def strippedVersion(self):
        """.version with leading and trailing zeros stripped."""
        version = list(self.version)
        while len(version) > 1 and version[0] == 0:
            version.pop(0)
        while len(version) > 1 and version[-1] == 0:
            version.pop()
        return tuple(version)

    #--crc
    @property
    def crc(self):
        """Calculates and returns crc value for self."""
        size = self.size
        crc = 0L
        with self.open('rb') as ins:
            insRead = ins.read
            insTell = ins.tell
            while insTell() < size:
                crc = crc32(insRead(512),crc)
        return crc & 0xffffffff

    #--crc with progress bar
    def crcProgress(self, progress):
        """Calculates and returns crc value for self, updating progress as it goes."""
        size = self.size
        progress.setFull(max(size,1))
        crc = 0L
        try:
            with self.open('rb') as ins:
                insRead = ins.read
                insTell = ins.tell
                while insTell() < size:
                    crc = crc32(insRead(2097152),crc) # 2MB at a time, probably ok
                    progress(insTell())
        except IOError, ierr:
            #if werr.winerror != 123: raise
            deprint(u'Unable to get crc of %s - probably a unicode error' % self._s)
        return crc & 0xFFFFFFFF

    #--Path stuff -------------------------------------------------------
    #--New Paths, subpaths
    def __add__(self,other):
        return GPath(self._s + Path.getNorm(other))
    def join(*args):
        norms = [Path.getNorm(x) for x in args]
        return GPath(os.path.join(*norms))
    def list(self):
        """For directory: Returns list of files."""
        if not os.path.exists(self._s): return []
        return [GPath(x) for x in os.listdir(self._s)]
    def walk(self,topdown=True,onerror=None,relative=False):
        """Like os.walk."""
        if relative:
            start = len(self._s)
            for root,dirs,files in os.walk(self._s,topdown,onerror):
                yield (GPath(root[start:]),[GPath(x) for x in dirs],[GPath(x) for x in files])
        else:
            for root,dirs,files in os.walk(self._s,topdown,onerror):
                yield (GPath(root),[GPath(x) for x in dirs],[GPath(x) for x in files])

    def split(self):
        """Splits the path into each of it's sub parts.  IE: C:\Program Files\Bethesda Softworks
           would return ['C:','Program Files','Bethesda Softworks']"""
        dirs = []
        drive, path = os.path.splitdrive(self.s)
        path = path.strip(os.path.sep)
        l,r = os.path.split(path)
        while l != u'':
            dirs.append(r)
            l,r = os.path.split(l)
        dirs.append(r)
        if drive != u'':
            dirs.append(drive)
        dirs.reverse()
        return dirs
    def relpath(self,path):
        return GPath(os.path.relpath(self._s,Path.getNorm(path)))

    def drive(self):
        """Returns the drive part of the path string."""
        return GPath(os.path.splitdrive(self._s)[0])

    def cdrive(self):
        """Returns the case-insensitive drive part of the path string."""
        return GPath(os.path.splitdrive(self._cs)[0])

    #--File system info
    #--THESE REALLY OUGHT TO BE PROPERTIES.
    def exists(self):
        return os.path.exists(self._s)
    def isdir(self):
        return os.path.isdir(self._s)
    def isfile(self):
        return os.path.isfile(self._s)
    def isabs(self):
        return os.path.isabs(self._s)

    #--File system manipulation
    @staticmethod
    def _onerror(func,path,exc_info):
        """shutil error handler: remove RO flag"""
        if not os.access(path,os.W_OK):
            os.chmod(path,stat.S_IWUSR|stat.S_IWOTH)
            func(path)
        else:
            raise

    def clearRO(self):
        """Clears RO flag on self"""
        if not self.isdir():
            os.chmod(self._s,stat.S_IWUSR|stat.S_IWOTH)
        else:
            try:
                cmd = ur'attrib -R "%s\*" /S /D' % self._s
                subprocess.call(cmd,stdout=subprocess.PIPE,startupinfo=startupinfo)
            except UnicodeError:
                flags = stat.S_IWUSR|stat.S_IWOTH
                chmod = os.chmod
                for root,dirs,files in os.walk(self._s):
                    rootJoin = root.join
                    for dir in dirs:
                        try: chmod(rootJoin(dir),flags)
                        except: pass
                    for file in files:
                        try: chmod(rootJoin(file),flags)
                        except: pass

    def open(self,*args,**kwdargs):
        if self._shead and not os.path.exists(self._shead):
            os.makedirs(self._shead)
        if 'encoding' in kwdargs:
            return codecs.open(self._s,*args,**kwdargs)
        else:
            return open(self._s,*args,**kwdargs)
    def makedirs(self):
        if not self.exists(): os.makedirs(self._s)
    def remove(self):
        try:
            if self.exists(): os.remove(self._s)
        except WindowsError:
            # Clear RO flag
            os.chmod(self._s,stat.S_IWUSR|stat.S_IWOTH)
            os.remove(self._s)
    def removedirs(self):
        try:
            if self.exists(): os.removedirs(self._s)
        except WindowsError:
            self.clearRO()
            os.removedirs(self._s)
    def rmtree(self,safety='PART OF DIRECTORY NAME'):
        """Removes directory tree. As a safety factor, a part of the directory name must be supplied."""
        if self.isdir() and safety and safety.lower() in self._cs:
            shutil.rmtree(self._s,onerror=Path._onerror)

    #--start, move, copy, touch, untemp
    def start(self, exeArgs=None):
        """Starts file as if it had been doubleclicked in file explorer."""
        if self._cext == u'.exe':
            if not exeArgs:
                subprocess.Popen([self.s], close_fds=close_fds)
            else:
                subprocess.Popen(exeArgs, executable=self.s, close_fds=close_fds)
        else:
            os.startfile(self._s)
    def copyTo(self,destName):
        destName = GPath(destName)
        if self.isdir():
            shutil.copytree(self._s,destName._s)
        else:
            if destName._shead and not os.path.exists(destName._shead):
                os.makedirs(destName._shead)
            shutil.copyfile(self._s,destName._s)
            destName.mtime = self.mtime
    def moveTo(self,destName):
        if not self.exists():
            raise StateError(self._s + u' cannot be moved because it does not exist.')
        destPath = GPath(destName)
        if destPath._cs == self._cs: return
        if destPath._shead and not os.path.exists(destPath._shead):
            os.makedirs(destPath._shead)
        elif destPath.exists():
            destPath.remove()
        try:
            shutil.move(self._s,destPath._s)
        except WindowsError:
            self.clearRO()
            shutil.move(self._s,destPath._s)

    def tempMoveTo(self,destName):
        """Temporarily rename/move an object.  Use with the 'with' statement"""
        class temp(object):
            def __init__(self,oldPath,newPath):
                self.newPath = GPath(newPath)
                self.oldPath = GPath(oldPath)

            def __enter__(self): return self.newPath
            def __exit__(self,*args,**kwdargs): self.newPath.moveTo(self.oldPath)
        self.moveTo(destName)
        return temp(self,destName)

    def unicodeSafe(self):
        """Temporarily rename (only if necessary) the file to a unicode safe name.
           Use with the 'with' statement."""
        try:
            self._s.encode('ascii')
            class temp(object):
                def __init__(self,path):
                    self.path = path
                def __enter__(self): return self.path
                def __exit__(self,*args,**kwdargs): pass
            return temp(self)
        except UnicodeEncodeError:
            return self.tempMoveTo(self.temp)

    def touch(self):
        """Like unix 'touch' command. Creates a file with current date/time."""
        if self.exists():
            self.mtime = time.time()
        else:
            with self.temp.open('w'):
                pass
            self.untemp()
    def untemp(self,doBackup=False):
        """Replaces file with temp version, optionally making backup of file first."""
        if self.temp.exists():
            if self.exists():
                if doBackup:
                    self.backup.remove()
                    shutil.move(self._s, self.backup._s)
                else:
                    os.remove(self._s)
            shutil.move(self.temp._s, self._s)
    def editable(self):
        """Safely check whether a file is editable."""
        delete = not os.path.exists(self._s)
        try:
            with open(self._s,'ab') as f:
                return True
        except:
            return False
        finally:
            # If the file didn't exist before, remove the created version
            if delete:
                try:
                    os.remove(self._s)
                except:
                    pass

    #--Hash/Compare
    def __hash__(self):
        return hash(self._cs)
    def __cmp__(self, other):
        if isinstance(other,Path):
            return cmp(self._cs, other._cs)
        else:
            return cmp(self._cs, Path.getCase(other))

# Util Constants --------------------------------------------------------------
#--Unix new lines
reUnixNewLine = re.compile(ur'(?<!\r)\n',re.U)

# Util Classes ----------------------------------------------------------------
#------------------------------------------------------------------------------
class CsvReader:
    """For reading csv files. Handles comma, semicolon and tab separated (excel) formats.
       CSV files must be encoded in UTF-8"""
    @staticmethod
    def utf_8_encoder(unicode_csv_data):
        for line in unicode_csv_data:
            yield line.encode('utf8')

    def __init__(self,path):
        self.ins = path.open('rb',encoding='utf-8-sig')
        format = ('excel','excel-tab')[u'\t' in self.ins.readline()]
        if format == 'excel':
            delimiter = (',',';')[u';' in self.ins.readline()]
            self.ins.seek(0)
            self.reader = csv.reader(CsvReader.utf_8_encoder(self.ins),format,delimiter=delimiter)
        else:
            self.ins.seek(0)
            self.reader = csv.reader(CsvReader.utf_8_encoder(self.ins),format)

    def __enter__(self): return self
    def __exit__(self,*args,**kwdargs): self.ins.close()

    def __iter__(self):
        for iter in self.reader:
            yield [unicode(x,'utf8') for x in iter]

    def close(self):
        self.reader = None
        self.ins.close()

#------------------------------------------------------------------------------
class Flags(object):
    """Represents a flag field."""
    __slots__ = ['_names','_field']

    @staticmethod
    def getNames(*names):
        """Returns dictionary mapping names to indices.
        Names are either strings or (index,name) tuples.
        E.g., Flags.getNames('isQuest','isHidden',None,(4,'isDark'),(7,'hasWater'))"""
        namesDict = {}
        for index,name in enumerate(names):
            if isinstance(name,tuple):
                namesDict[name[1]] = name[0]
            elif name: #--skip if "name" is 0 or None
                namesDict[name] = index
        return namesDict

    #--Generation
    def __init__(self,value=0,names=None):
        """Initialize. Attrs, if present, is mapping of attribute names to indices. See getAttrs()"""
        object.__setattr__(self,'_field',int(value) | 0L)
        object.__setattr__(self,'_names',names or {})

    def __call__(self,newValue=None):
        """Returns a clone of self, optionally with new value."""
        if newValue is not None:
            return Flags(int(newValue) | 0L,self._names)
        else:
            return Flags(self._field,self._names)

    def __deepcopy__(self,memo={}):
        newFlags=Flags(self._field,self._names)
        memo[id(self)] = newFlags
        return newFlags

    #--As hex string
    def hex(self):
        """Returns hex string of value."""
        return u'%08X' % (self._field,)
    def dump(self):
        """Returns value for packing"""
        return self._field

    #--As int
    def __int__(self):
        """Return as integer value for saving."""
        return self._field
    def __getstate__(self):
        """Return values for pickling."""
        return self._field, self._names
    def __setstate__(self,fields):
        """Used by unpickler."""
        self._field = fields[0]
        self._names = fields[1]

    #--As list
    def __getitem__(self, index):
        """Get value by index. E.g., flags[3]"""
        return bool((self._field >> index) & 1)

    def __setitem__(self,index,value):
        """Set value by index. E.g., flags[3] = True"""
        value = ((value or 0L) and 1L) << index
        mask = 1L << index
        self._field = ((self._field & ~mask) | value)

    #--As class
    def __getattr__(self,name):
        """Get value by flag name. E.g. flags.isQuestItem"""
        try:
            names = object.__getattribute__(self,'_names')
            index = names[name]
            return (object.__getattribute__(self,'_field') >> index) & 1 == 1
        except KeyError:
            raise AttributeError(name)

    def __setattr__(self,name,value):
        """Set value by flag name. E.g., flags.isQuestItem = False"""
        if name in ('_field','_names'):
            object.__setattr__(self,name,value)
        else:
            self.__setitem__(self._names[name],value)

    #--Native operations
    def __eq__( self, other):
        """Logical equals."""
        if isinstance(other,Flags):
            return self._field == other._field
        else:
            return self._field == other

    def __ne__( self, other):
        """Logical not equals."""
        if isinstance(other,Flags):
            return self._field != other._field
        else:
            return self._field != other

    def __and__(self,other):
        """Bitwise and."""
        if isinstance(other,Flags): other = other._field
        return self(self._field & other)

    def __invert__(self):
        """Bitwise inversion."""
        return self(~self._field)

    def __or__(self,other):
        """Bitwise or."""
        if isinstance(other,Flags): other = other._field
        return self(self._field | other)

    def __xor__(self,other):
        """Bitwise exclusive or."""
        if isinstance(other,Flags): other = other._field
        return self(self._field ^ other)

    def getTrueAttrs(self):
        """Returns attributes that are true."""
        trueNames = [name for name in self._names if getattr(self,name)]
        trueNames.sort(key = lambda xxx: self._names[xxx])
        return tuple(trueNames)

#------------------------------------------------------------------------------
class DataDict:
    """Mixin class that handles dictionary emulation, assuming that dictionary is its 'data' attribute."""

    def __contains__(self,key):
        return key in self.data
    def __getitem__(self,key):
        if self.data.has_key(key):
            return self.data[key]
        else:
            if isinstance(key, Path):
                try:
                    import bush
                    return self.data[Path(bush.game.masterFiles[0])]
                except:
                    try:
                        return self.data[Path(u'Oblivion.esm')]
                    except:
                        print
                        print "An error occurred trying to access data for mod file:", key
                        print "This can occur when the game's main ESM file is corrupted."
                        print
                        raise
    def __setitem__(self,key,value):
        self.data[key] = value
    def __delitem__(self,key):
        del self.data[key]
    def __len__(self):
        return len(self.data)
    def setdefault(self,key,default):
        return self.data.setdefault(key,default)
    def keys(self):
        return self.data.keys()
    def values(self):
        return self.data.values()
    def items(self):
        return self.data.items()
    def has_key(self,key):
        return self.data.has_key(key)
    def get(self,key,default=None):
        return self.data.get(key,default)
    def pop(self,key,default=None):
        return self.data.pop(key,default)
    def iteritems(self):
        return self.data.iteritems()
    def iterkeys(self):
        return self.data.iterkeys()
    def itervalues(self):
        return self.data.itervalues()

#------------------------------------------------------------------------------
from collections import MutableSet
class OrderedSet(list, MutableSet):
    """A set like object, that remembers the order items were added to it.
       Since it has order, a few list functions were added as well:
        - index(value)
        - __getitem__(index)
        - __call__ -> to enable 'enumerate'
       If an item is dicarded, then later readded, it will be added
       to the end of the set.
    """
    def update(self, *args, **kwdargs):
        if kwdargs: raise TypeError(("update() takes no keyword arguments"))
        for s in args:
            for e in s:
                self.add(e)

    def add(self, elem):
        if elem not in self:
            self.append(elem)
    def discard(self, elem): self.pop(self.index(elem),None)
    def __or__(self,other):
        left = OrderedSet(self)
        left.update(other)
        return left
    def __repr__(self): return u'OrderedSet%s' % unicode(list(self))[1:-1]
    def __unicode__(self): return u'{%s}' % unicode(list(self))[1:-1]

#------------------------------------------------------------------------------
class MemorySet(object):
    """Specialization of the OrderedSet, where it remembers the order of items
       event if they're removed.  Also, combining and comparing to other MemorySet's
       takes this into account:
        a|b -> returns union of a and b, but keeps the ordering of b where possible.
               if an item in a was also in b, but deleted, it will be added to the
               deleted location.
        a&b -> same as a|b, but only items 'not-deleted' in both a and b are marked
               as 'not-deleted'
        a^b -> same as a|b, but only items 'not-deleted' in a but not b, or b but not
               a are marked as 'not-deleted'
        a-b -> same as a|b, but any 'not-deleted' items in b are marked as deleted

        a==b -> compares the 'not-deleted' items of the MemorySets.  If both are the same,
                and in the same order, then they are equal.
        a!=b -> oposite of a==b
    """
    def __init__(self, *args, **kwdargs):
        self.items = OrderedSet(*args, **kwdargs)
        self.mask = [True for i in range(len(self.items))]

    def add(self,elem):
        if elem in self.items: self.mask[self.items.index(elem)] = True
        else:
            self.items.add(elem)
            self.mask.append(True)
    def discard(self,elem):
        if elem in self.items: self.mask[self.items.index(elem)] = False
    discarded = property(lambda self: OrderedSet([x for i,x in enumerate(self.items) if not self.mask[i]]))

    def __len__(self): return sum(self.mask)
    def __iter__(self):
        for i,elem in enumerate(self.items):
            if self.mask[i]: yield self.items[i]
    def __str__(self): return u'{%s}' % (','.join(map(repr,self._items())))
    def __repr__(self): return u'MemorySet([%s])' % (','.join(map(repr,self._items())))
    def forget(self, elem):
        # Permanently remove an item from the list.  Don't remember its order
        if elem in self.items:
            idex = self.items.index(elem)
            self.items.discard(elem)
            del self.mask[idex]

    def _items(self): return OrderedSet([x for x in self])

    def __or__(self,other):
        """Return items in self or in other"""
        discards = (self.discarded-other._items())|(other.discarded-self._items())
        right = list(other.items)
        left = list(self.items)

        for idex,elem in enumerate(left):
            # elem is already in the other one, skip
            if elem in right: continue

            # Figure out best place to put it
            if idex == 0:
                # put it in front
                right.insert(0,elem)
            elif idex == len(left)-1:
                # put in in back
                right.append(elem)
            else:
                # Find out what item it comes after
                afterIdex = idex-1
                while afterIdex > 0 and left[afterIdex] not in right:
                    afterIdex -= 1
                insertIdex = right.index(left[afterIdex])+1
                right.insert(insertIdex,elem)
        ret = MemorySet(right)
        ret.mask = [x not in discards for x in right]
        return ret
    def __and__(self,other):
        items = self.items & other.items
        discards = self.discarded | other.discarded
        ret = MemorySet(items)
        ret.mask = [x not in discards for x in items]
        return ret
    def __sub__(self,other):
        discards = self.discarded | other._items()
        ret = MemorySet(self.items)
        ret.mask = [x not in discards for x in self.items]
        return ret
    def __xor__(self,other):
        items = (self|other).items
        discards = items - (self._items()^other._items())
        ret = MemorySet(items)
        ret.mask = [x not in discards for x in items]
        return ret

    def __eq__(self,other): return list(self) == list(other)
    def __ne__(self,other): return list(self) != list(other)

#------------------------------------------------------------------------------
class MainFunctions:
    """Encapsulates a set of functions and/or object instances so that they can
    be called from the command line with normal command line syntax.

    Functions are called with their arguments. Object instances are called
    with their method and method arguments. E.g.:
    * bish bar arg1 arg2 arg3
    * bish foo.bar arg1 arg2 arg3"""

    def __init__(self):
        """Initialization."""
        self.funcs = {}

    def add(self,func,key=None):
        """Add a callable object.
        func - A function or class instance.
        key - Command line invocation for object (defaults to name of func).
        """
        key = key or func.__name__
        self.funcs[key] = func
        return func

    def main(self):
        """Main function. Call this in __main__ handler."""
        #--Get func
        args = sys.argv[1:]
        attrs = args.pop(0).split(u'.')
        key = attrs.pop(0)
        func = self.funcs.get(key)
        if not func:
            msg = _(u"Unknown function/object: %s") % key
            try: print msg
            except UnicodeError: print msg.encode('mbcs')
            return
        for attr in attrs:
            func = getattr(func,attr)
        #--Separate out keywords args
        keywords = {}
        argDex = 0
        reKeyArg  = re.compile(ur'^\-(\D\w+)',re.U)
        reKeyBool = re.compile(ur'^\+(\D\w+)',re.U)
        while argDex < len(args):
            arg = args[argDex]
            if reKeyArg.match(arg):
                keyword = reKeyArg.match(arg).group(1)
                value   = args[argDex+1]
                keywords[keyword] = value
                del args[argDex:argDex+2]
            elif reKeyBool.match(arg):
                keyword = reKeyBool.match(arg).group(1)
                keywords[keyword] = True
                del args[argDex]
            else:
                argDex = argDex + 1
        #--Apply
        apply(func,args,keywords)

#--Commands Singleton
_mainFunctions = MainFunctions()
def mainfunc(func):
    """A function for adding funcs to _mainFunctions.
    Used as a function decorator ("@mainfunc")."""
    _mainFunctions.add(func)
    return func

#------------------------------------------------------------------------------
class PickleDict:
    """Dictionary saved in a pickle file.
    Note: self.vdata and self.data are not reassigned! (Useful for some clients.)"""
    def __init__(self,path,readOnly=False):
        """Initialize."""
        self.path = path
        self.backup = path.backup
        self.readOnly = readOnly
        self.vdata = {}
        self.data = {}

    def exists(self):
        return self.path.exists() or self.backup.exists()

    def load(self):
        """Loads vdata and data from file or backup file.

        If file does not exist, or is corrupt, then reads from backup file. If
        backup file also does not exist or is corrupt, then no data is read. If
        no data is read, then self.data is cleared.

        If file exists and has a vdata header, then that will be recorded in
        self.vdata. Otherwise, self.vdata will be empty.

        Returns:
          0: No data read (files don't exist and/or are corrupt)
          1: Data read from file
          2: Data read from backup file
        """
        self.vdata.clear()
        self.data.clear()
        for path in (self.path,self.backup):
            if path.exists():
                ins = None
                try:
                    with path.open('rb') as ins:
                        try:
                            header = cPickle.load(ins)
                        except ValueError:
                            os.remove(path)
                            continue # file corrupt - try next file
                        if header == 'VDATA2':
                            self.vdata.update(cPickle.load(ins))
                            self.data.update(cPickle.load(ins))
                        elif header == 'VDATA':
                            # translate data types to new hierarchy
                            class _Translator:
                                def __init__(self, fileToWrap):
                                    self._file = fileToWrap
                                def read(self, numBytes):
                                    return self._translate(self._file.read(numBytes))
                                def readline(self):
                                    return self._translate(self._file.readline())
                                def _translate(self, s):
                                    return re.sub(u'^(bolt|bosh)$', r'bash.\1', s,flags=re.U)
                            translator = _Translator(ins)
                            try:
                                self.vdata.update(cPickle.load(translator))
                                self.data.update(cPickle.load(translator))
                            except:
                                deprint(u'unable to unpickle data', traceback=True)
                                raise
                        else:
                            self.data.update(header)
                    return 1 + (path == self.backup)
                except (EOFError, ValueError):
                    pass
        #--No files and/or files are corrupt
        return 0

    def save(self):
        """Save to pickle file."""
        if self.readOnly: return False
        #--Pickle it
        with self.path.temp.open('wb') as out:
            for data in ('VDATA2',self.vdata,self.data):
                cPickle.dump(data,out,-1)
        self.path.untemp(True)
        return True

#------------------------------------------------------------------------------
class Settings(DataDict):
    """Settings/configuration dictionary with persistent storage.

    Default setting for configurations are either set in bulk (by the
    loadDefaults function) or are set as needed in the code (e.g., various
    auto-continue settings for bash. Only settings that have been changed from
    the default values are saved in persistent storage.

    Directly setting a value in the dictionary will mark it as changed (and thus
    to be archived). However, an indirect change (e.g., to a value that is a
    list) must be manually marked as changed by using the setChanged method."""

    def __init__(self,dictFile):
        """Initialize. Read settings from dictFile."""
        self.dictFile = dictFile
        if self.dictFile:
            dictFile.load()
            self.vdata = dictFile.vdata.copy()
            self.data = dictFile.data.copy()
        else:
            self.vdata = {}
            self.data = {}
        self.defaults = {}
        self.changed = []
        self.deleted = []

    def loadDefaults(self,defaults):
        """Add default settings to dictionary. Will not replace values that are already set."""
        self.defaults = defaults
        for key in defaults.keys():
            if key not in self.data:
                self.data[key] = copy.deepcopy(defaults[key])

    def setDefault(self,key,default):
        """Sets a single value to a default value if it has not yet been set."""

    def save(self):
        """Save to pickle file. Only key/values marked as changed are saved."""
        dictFile = self.dictFile
        if not dictFile or dictFile.readOnly: return
        dictFile.load()
        dictFile.vdata = self.vdata.copy()
        for key in self.deleted:
            dictFile.data.pop(key,None)
        for key in self.changed:
            if self.data[key] == self.defaults.get(key,None):
                dictFile.data.pop(key,None)
            else:
                dictFile.data[key] = self.data[key]
        dictFile.save()

    def setChanged(self,key):
        """Marks given key as having been changed. Use if value is a dictionary, list or other object."""
        if key not in self.data:
            raise ArgumentError(u'No settings data for '+key)
        if key not in self.changed:
            self.changed.append(key)

    def getChanged(self,key,default=None):
        """Gets and marks as changed."""
        if default != None and key not in self.data:
            self.data[key] = default
        self.setChanged(key)
        return self.data.get(key)

    #--Dictionary Emulation
    def __setitem__(self,key,value):
        """Dictionary emulation. Marks key as changed."""
        if key in self.deleted: self.deleted.remove(key)
        if key not in self.changed: self.changed.append(key)
        self.data[key] = value

    def __delitem__(self,key):
        """Dictionary emulation. Marks key as deleted."""
        if key in self.changed: self.changed.remove(key)
        if key not in self.deleted: self.deleted.append(key)
        del self.data[key]

    def setdefault(self,key,value):
        """Dictionary emulation. Will not mark as changed."""
        if key in self.data:
            return self.data[key]
        if key in self.deleted: self.deleted.remove(key)
        self.data[key] = value
        return value

    def pop(self,key,default=None):
        """Dictionary emulation: extract value and delete from dictionary."""
        if key in self.changed: self.changed.remove(key)
        if key not in self.deleted: self.deleted.append(key)
        return self.data.pop(key,default)

#------------------------------------------------------------------------------
class StructFile(file):
    """File reader/writer with extra functions for handling structured data."""
    def unpack(self,format,size):
        """Reads and unpacks according to format."""
        return struct.unpack(format,self.read(size))

    def pack(self,format,*data):
        """Packs data according to format."""
        self.write(struct.pack(format,*data))

    def readNetString(self):
        """Read a .net string. THIS CODE IS DUBIOUS!"""
        pos = self.tell()
        strLen, = self.unpack('B',1)
        if strLen >= 128:
            self.seek(pos)
            strLen, = self.unpack('H',2)
            strLen = strLen & 0x7f | (strLen >> 1) & 0xff80
            if strLen > 0x7FFF:
                raise UncodedError(u'String too long to convert.')
        return self.read(strLen)

    def writeNetString(self,str):
        """Write string as a .net string. THIS CODE IS DUBIOUS!"""
        strLen = len(str)
        if strLen < 128:
            self.pack('b',strLen)
        elif strLen > 0x7FFF: #--Actually probably fails earlier.
            raise UncodedError(u'String too long to convert.')
        else:
            strLen =  0x80 | strLen & 0x7f | (strLen & 0xff80) << 1
            self.pack('H',strLen)
        self.write(str)

#------------------------------------------------------------------------------
class BinaryFile(StructFile):
    """File reader/writer easier to read specific number of bytes."""
    def __init__(self,*args,**kwdargs):
        # Ensure we're reading/writing in binary mode
        if len(args) < 2:
            mode = kwdargs.get('mode',None)
            if mode =='r': mode = 'rb'
            elif mode == 'w': mode = 'wb'
            elif mode == 'rb' or mode == 'wb':
                pass
            else: mode = 'rb'
            kwdargs['mode'] = mode
        else:
            new_args = list(args)
            if args[1] == 'r': new_args[1] = 'rb'
            elif args[1] == 'w': new_args[1] = 'wb'
            elif args[1] == 'rb' or args[1] == 'wb':
                pass
            else: new_args[1] = 'rb'
            args = tuple(new_args)
        types.FileType.__init__(self,*args,**kwdargs)

    def readPascalString(self): return self.read(self.readByte())
    def readCString(self):
        pos = self.tell()
        while self.readByte() != 0:
            pass
        end = self.tell()
        self.seek(pos)
        return self.read(end-pos+1)
    # readNetString defined in StructFile
    def readByte(self): return struct.unpack('B',self.read(1))[0]
    def readBytes(self, numBytes): return list(struct.unpack('b'*numBytes,self.read(numBytes)))
    def readInt16(self): return struct.unpack('h',self.read(2))[0]
    def readInt32(self): return struct.unpack('i',self.read(4))[0]
    def readInt64(self): return struct.unpack('q',self.read(8))[0]

    def writeString(self, text):
        self.writeByte(len(text))
        self.write(text)
    def writeByte(self, byte): self.write(struct.pack('B',byte))
    def writeBytes(self, bytes): self.write(struct.pack('b'*len(bytes),*bytes))
    def writeInt16(self, int16): self.write(struct.pack('h',int16))
    def writeInt32(self, int32): self.write(struct.pack('i',int32))
    def writeInt64(self, int64): self.write(struct.pack('q',int64))

#------------------------------------------------------------------------------
class TableColumn:
    """Table accessor that presents table column as a dictionary."""
    def __init__(self,table,column):
        self.table = table
        self.column = column
    #--Dictionary Emulation
    def __iter__(self):
        """Dictionary emulation."""
        tableData = self.table.data
        column = self.column
        return (key for key in tableData.keys() if (column in tableData[key]))
    def keys(self):
        return list(self.__iter__())
    def items(self):
        """Dictionary emulation."""
        tableData = self.table.data
        column = self.column
        return [(key,tableData[key][column]) for key in tableData.keys()
            if (column in tableData[key])]
    def has_key(self,key):
        """Dictionary emulation."""
        return self.__contains__(key)
    def clear(self):
        """Dictionary emulation."""
        self.table.delColumn(self.column)
    def get(self,key,default=None):
        """Dictionary emulation."""
        return self.table.getItem(key,self.column,default)
    #--Overloaded
    def __contains__(self,key):
        """Dictionary emulation."""
        tableData = self.table.data
        return tableData.has_key(key) and tableData[key].has_key(self.column)
    def __getitem__(self,key):
        """Dictionary emulation."""
        return self.table.data[key][self.column]
    def __setitem__(self,key,value):
        """Dictionary emulation. Marks key as changed."""
        self.table.setItem(key,self.column,value)
    def __delitem__(self,key):
        """Dictionary emulation. Marks key as deleted."""
        self.table.delItem(key,self.column)

#------------------------------------------------------------------------------
class Table(DataDict):
    """Simple data table of rows and columns, saved in a pickle file. It is
    currently used by modInfos to represent properties associated with modfiles,
    where each modfile is a row, and each property (e.g. modified date or
    'mtime') is a column.

    The "table" is actually a dictionary of dictionaries. E.g.
        propValue = table['fileName']['propName']
    Rows are the first index ('fileName') and columns are the second index
    ('propName')."""

    def __init__(self,dictFile):
        """Intialize and read data from dictFile, if available."""
        self.dictFile = dictFile
        dictFile.load()
        self.vdata = dictFile.vdata
        self.data = dictFile.data
        self.hasChanged = False

    def save(self):
        """Saves to pickle file."""
        dictFile = self.dictFile
        if self.hasChanged and not dictFile.readOnly:
            self.hasChanged = not dictFile.save()

    def getItem(self,row,column,default=None):
        """Get item from row, column. Return default if row,column doesn't exist."""
        data = self.data
        if row in data and column in data[row]:
            return data[row][column]
        else:
            return default

    def getColumn(self,column):
        """Returns a data accessor for column."""
        return TableColumn(self,column)

    def setItem(self,row,column,value):
        """Set value for row, column."""
        data = self.data
        if row not in data:
            data[row] = {}
        data[row][column] = value
        self.hasChanged = True

    def setItemDefault(self,row,column,value):
        """Set value for row, column."""
        data = self.data
        if row not in data:
            data[row] = {}
        self.hasChanged = True
        return data[row].setdefault(column,value)

    def delItem(self,row,column):
        """Deletes item in row, column."""
        data = self.data
        if row in data and column in data[row]:
            del data[row][column]
            self.hasChanged = True

    def delRow(self,row):
        """Deletes row."""
        data = self.data
        if row in data:
            del data[row]
            self.hasChanged = True

    def delColumn(self,column):
        """Deletes column of data."""
        data = self.data
        for rowData in data.values():
            if column in rowData:
                del rowData[column]
                self.hasChanged = True

    def moveRow(self,oldRow,newRow):
        """Renames a row of data."""
        data = self.data
        if oldRow in data:
            data[newRow] = data[oldRow]
            del data[oldRow]
            self.hasChanged = True

    def copyRow(self,oldRow,newRow):
        """Copies a row of data."""
        data = self.data
        if oldRow in data:
            data[newRow] = data[oldRow].copy()
            self.hasChanged = True

    #--Dictionary emulation
    def __setitem__(self,key,value):
        self.data[key] = value
        self.hasChanged = True
    def __delitem__(self,key):
        del self.data[key]
        self.hasChanged = True
    def setdefault(self,key,default):
        if key not in self.data: self.hasChanged = True
        return self.data.setdefault(key,default)
    def pop(self,key,default=None):
        self.hasChanged = True
        return self.data.pop(key,default)

#------------------------------------------------------------------------------
class TankData:
    """Data source for a Tank table."""

    def __init__(self,params):
        """Initialize."""
        self.tankParams = params
        #--Default settings. Subclasses should define these.
        self.tankKey = self.__class__.__name__
        self.tankColumns = [] #--Full possible set of columns.
        self.title = self.__class__.__name__
        self.hasChanged = False

    #--Parameter access
    def getParam(self,key,default=None):
        """Get a GUI parameter.
        Typical Parameters:
        * columns: list of current columns.
        * colNames: column_name dict
        * colWidths: column_width dict
        * colAligns: column_align dict
        * colReverse: column_reverse dict (colReverse[column] = True/False)
        * colSort: current column being sorted on
        """
        return self.tankParams.get(self.tankKey+'.'+key,default)

    def defaultParam(self,key,value):
        """Works like setdefault for dictionaries."""
        return self.tankParams.setdefault(self.tankKey+'.'+key,value)

    def updateParam(self,key,default=None):
        """Get a param, but also mark it as changed.
        Used for deep params like lists and dictionaries."""
        return self.tankParams.getChanged(self.tankKey+'.'+key,default)

    def setParam(self,key,value):
        """Set a GUI parameter."""
        self.tankParams[self.tankKey+'.'+key] = value

    #--Collection
    def setChanged(self,hasChanged=True):
        """Mark as having changed."""
        pass

    def refresh(self):
        """Refreshes underlying data as needed."""
        pass

    def getRefreshReport(self):
        """Returns a (string) report on the refresh operation."""
        return None

    def getSorted(self,column,reverse):
        """Returns items sorted according to column and reverse."""
        raise AbstractError

    #--Item Info
    def getColumns(self,item=None):
        """Returns text labels for item or for row header if item == None."""
        columns = self.getParam('columns',self.tankColumns)
        if item == None: return columns[:]
        raise AbstractError

    def getName(self,item):
        """Returns a string name of item for use in dialogs, etc."""
        return item

    def getGuiKeys(self,item):
        """Returns keys for icon and text and background colors."""
        iconKey = textKey = backKey = None
        return (iconKey,textKey,backKey)

    def getMouseText(self,*args,**kwdargs):
        pass

# Util Functions --------------------------------------------------------------
#------------------------------------------------------------------------------
def copyattrs(source,dest,attrs):
    """Copies specified attrbutes from source object to dest object."""
    for attr in attrs:
        setattr(dest,attr,getattr(source,attr))

def cstrip(inString):
    """Convert c-string (null-terminated string) to python string."""
    zeroDex = inString.find('\x00')
    if zeroDex == -1:
        return inString
    else:
        return inString[:zeroDex]

def csvFormat(format):
    """Returns csv format for specified structure format."""
    csvFormat = u''
    for char in format:
        if char in u'bBhHiIlLqQ': csvFormat += u',%d'
        elif char in u'fd': csvFormat += u',%f'
        elif char in u's': csvFormat += u',"%s"'
    return csvFormat[1:] #--Chop leading comma

deprintOn = False

class tempDebugMode(object):
    __slots__=('_old')
    def __init__(self):
        global deprintOn
        self._old = deprintOn
        deprintOn = True

    def __enter__(self): return self
    def __exit__(self,*args,**kwdargs):
        global deprintOn
        deprintOn = self._old

def deprint(*args,**keyargs):
    """Prints message along with file and line location."""
    if not deprintOn and not keyargs.get('on'): return

    if keyargs.get('trace',True):
        import inspect
        stack = inspect.stack()
        file,line,function = stack[1][1:4]

        msg = u'%s %4d %s: ' % (GPath(file).tail.s,line,function)
    else:
        msg = u''
    try:
        msg += u' '.join([u'%s'%x for x in args])
    except UnicodeError:
        # If the args failed to convert to unicode for some reason
        # we still want the message displayed any way we can
        for x in args:
            try:
                msg += u' %s' % x
            except UnicodeError:
                msg += u' %s' % repr(x)

    if keyargs.get('traceback',False):
        o = StringIO.StringIO(msg)
        o.write(u'\n')
        traceback.print_exc(file=o)
        value = o.getvalue()
        try:
            msg += u'%s' % value
        except UnicodeError:
            msg += u'%s' % repr(value)
        o.close()
    try:
        # Should work if stdout/stderr is going to wxPython output
        print msg
    except UnicodeError:
        # Nope, it's going somewhere else
        print msg.encode('mbcs')

#def delist(header,items,on=False):
#    """Prints list as header plus items."""
#    if not deprintOn and not on: return
#    import inspect
#    stack = inspect.stack()
#    file,line,function = stack[1][1:4]
#    msg = u'%s %4d %s: %s' % (GPath(file).tail.s,line,function,header)
#    try:
#        print msg
#    except UnicodeError:
#        print msg.encode('mbcs')
#    if items == None:
#        print u'> None'
#    else:
#        for indexItem in enumerate(items):
#            msg = u'>%2d: %s' % indexItem
#            try:
#                print msg
#            except UnicodeError:
#                print msg.encode('mbcs')

#def dictFromLines(lines,sep=None):
#    """Generate a dictionary from a string with lines, stripping comments and skipping empty strings."""
#    temp = [reComment.sub(u'',x).strip() for x in lines.split(u'\n')]
#    if sep == None or type(sep) == type(u''):
#        temp = dict([x.split(sep,1) for x in temp if x])
#    else: #--Assume re object.
#        temp = dict([sep.split(x,1) for x in temp if x])
#    return temp

def getMatch(reMatch,group=0):
    """Returns the match or an empty string."""
    if reMatch: return reMatch.group(group)
    else: return u''

def intArg(arg,default=None):
    """Returns argument as an integer. If argument is a string, then it converts it using int(arg,0)."""
    if arg == None: return default
    elif isinstance(arg,types.StringTypes): return int(arg,0)
    else: return int(arg)

def invertDict(indict):
    """Invert a dictionary."""
    return dict((y,x) for x,y in indict.iteritems())

#def listFromLines(lines):
#    """Generate a list from a string with lines, stripping comments and skipping empty strings."""
#    temp = [reComment.sub(u'',x).strip() for x in lines.split(u'\n')]
#    temp = [x for x in temp if x]
#    return temp

def listSubtract(alist,blist):
    """Return a copy of first list minus items in second list."""
    result = []
    for item in alist:
        if item not in blist:
            result.append(item)
    return result

#def listJoin(*inLists):
#    """Joins multiple lists into a single list."""
#    outList = []
#    for inList in inLists:
#        outList.extend(inList)
#    return outList

#def listGroup(items):
#    """Joins items into a list for use in a regular expression.
#    E.g., a list of ('alpha','beta') becomes '(alpha|beta)'"""
#    return u'('+(u'|'.join(items))+u')'

#def rgbString(red,green,blue):
#    """Converts red, green blue ints to rgb string."""
#    return chr(red)+chr(green)+chr(blue)

#def rgbTuple(rgb):
#    """Converts red, green, blue string to tuple."""
#    return struct.unpack('BBB',rgb)

#def unQuote(inString):
#    """Removes surrounding quotes from string."""
#    if len(inString) >= 2 and inString[0] == u'"' and inString[-1] == u'"':
#        return inString[1:-1]
#    else:
#        return inString

def winNewLines(inString):
    """Converts unix newlines to windows newlines."""
    return reUnixNewLine.sub(u'\r\n',inString)

# Log/Progress ----------------------------------------------------------------
#------------------------------------------------------------------------------
class Log:
    """Log Callable. This is the abstract/null version. Useful version should
    override write functions.

    Log is divided into sections with headers. Header text is assigned (through
    setHeader), but isn't written until a message is written under it. I.e.,
    if no message are written under a given header, then the header itself is
    never written."""

    def __init__(self):
        """Initialize."""
        self.header = None
        self.prevHeader = None

    def setHeader(self,header,writeNow=False,doFooter=True):
        """Sets the header."""
        self.header = header
        if self.prevHeader:
            self.prevHeader += u'x'
        self.doFooter = doFooter
        if writeNow: self()

    def __call__(self,message=None,appendNewline=True):
        """Callable. Writes message, and if necessary, header and footer."""
        if self.header != self.prevHeader:
            if self.prevHeader and self.doFooter:
                self.writeFooter()
            if self.header:
                self.writeHeader(self.header)
            self.prevHeader = self.header
        if message: self.writeMessage(message,appendNewline)

    #--Abstract/null writing functions...
    def writeHeader(self,header):
        """Write header. Abstract/null version."""
        pass
    def writeFooter(self):
        """Write mess. Abstract/null version."""
        pass
    def writeMessage(self,message,appendNewline):
        """Write message to log. Abstract/null version."""
        pass

#------------------------------------------------------------------------------
class LogFile(Log):
    """Log that writes messages to file."""
    def __init__(self,out):
        self.out = out
        Log.__init__(self)

    def writeHeader(self,header):
        self.out.write(header+u'\n')

    def writeFooter(self):
        self.out.write(u'\n')

    def writeMessage(self,message,appendNewline):
        self.out.write(message)
        if appendNewline: self.out.write(u'\n')

#------------------------------------------------------------------------------
class Progress:
    """Progress Callable: Shows progress when called."""
    def __init__(self,full=1.0):
        if (1.0*full) == 0: raise ArgumentError(u'Full must be non-zero!')
        self.message = u''
        self.full = full
        self.state = 0
        self.debug = False

    def getParent(self):
        return None

    def setFull(self,full):
        """Set's full and for convenience, returns self."""
        if (1.0*full) == 0: raise ArgumentError(u'Full must be non-zero!')
        self.full = full
        return self

    def plus(self,increment=1):
        """Increments progress by 1."""
        self.__call__(self.state+increment)

    def __call__(self,state,message=''):
        """Update progress with current state. Progress is state/full."""
        if (1.0*self.full) == 0: raise ArgumentError(u'Full must be non-zero!')
        if message: self.message = message
        if self.debug: deprint(u'%0.3f %s' % (1.0*state/self.full, self.message))
        self.doProgress(1.0*state/self.full, self.message)
        self.state = state

    def doProgress(self,progress,message):
        """Default doProgress does nothing."""
        pass

#------------------------------------------------------------------------------
class SubProgress(Progress):
    """Sub progress goes from base to ceiling."""
    def __init__(self,parent,baseFrom=0.0,baseTo='+1',full=1.0,silent=False):
        """For creating a subprogress of another progress meter.
        progress: parent (base) progress meter
        baseFrom: Base progress when this progress == 0.
        baseTo: Base progress when this progress == full
          Usually a number. But string '+1' sets it to baseFrom + 1
        full: Full meter by this progress' scale."""
        Progress.__init__(self,full)
        if baseTo == '+1': baseTo = baseFrom + 1
        if (baseFrom < 0 or baseFrom >= baseTo):
            raise ArgumentError(u'BaseFrom must be >= 0 and BaseTo must be > BaseFrom')
        self.parent = parent
        self.baseFrom = baseFrom
        self.scale = 1.0*(baseTo-baseFrom)
        self.silent = silent

    def __call__(self,state,message=u''):
        """Update progress with current state. Progress is state/full."""
        if self.silent: message = u''
        self.parent(self.baseFrom+self.scale*state/self.full,message)
        self.state = state

#------------------------------------------------------------------------------
class ProgressFile(Progress):
    """Prints progress to file (stdout by default)."""
    def __init__(self,full=1.0,out=None):
        Progress.__init__(self,full)
        self.out = out or sys.stdout

    def doProgress(self,progress,message):
        msg = u'%0.2f %s\n' % (progress,message)
        try: self.out.write(msg)
        except UnicodeError: self.out.write(msg.encode('mbcs'))

#------------------------------------------------------------------------------
class StringTable(dict):
    """For reading .STRINGS, .DLSTRINGS, .ILSTRINGS files."""
    encodings = {
        # Encoding to fall back to if UTF-8 fails, based on language
        # Default is 1252 (Western European), so only list languages
        # different than that
        u'russian': 'cp1251',
        }

    def load(self,modFilePath,language=u'English',progress=Progress()):
        baseName = modFilePath.tail.body
        baseDir = modFilePath.head.join(u'Strings')
        files = (baseName+u'_'+language+x for x in (u'.STRINGS',u'.DLSTRINGS',
                                                   u'.ILSTRINGS'))
        files = (baseDir.join(file) for file in files)
        self.clear()
        progress.setFull(3)
        for i,file in enumerate(files):
            progress(i)
            self.loadFile(file,SubProgress(progress,i,i+1))

    def loadFile(self,path,progress,language=u'english'):
        if path.cext == u'.strings': format = 0
        else: format = 1
        language = language.lower()
        backupEncoding = self.encodings.get(language,'cp1252')
        try:
            with BinaryFile(path.s) as ins:
                insSeek = ins.seek
                insTell = ins.tell
                insUnpack = ins.unpack
                insReadCString = ins.readCString
                insRead = ins.read

                insSeek(0,os.SEEK_END)
                eof = insTell()
                insSeek(0)
                if eof < 8:
                    deprint(u"Warning: Strings file '%s' file size (%d) is less than 8 bytes.  8 bytes are the minimum required by the expected format, assuming the Strings file is empty."
                            % (path, eof))
                    return

                numIds,dataSize = insUnpack('=2I',8)
                progress.setFull(max(numIds,1))
                stringsStart = 8 + (numIds*8)
                if stringsStart != eof-dataSize:
                    deprint(u"Warning: Strings file '%s' dataSize element (%d) results in a string start location of %d, but the expected location is %d"
                            % (path, dataSize, eof-dataSize, stringsStart))

                id = -1
                offset = -1
                for x in xrange(numIds):
                    try:
                        progress(x)
                        id,offset = insUnpack('=2I',8)
                        pos = insTell()
                        insSeek(stringsStart+offset)
                        if format:
                            strLen, = insUnpack('I',4)
                            value = insRead(strLen)
                        else:
                            value = insReadCString()
                        value = cstrip(value)
                        try:
                            value = unicode(value,'utf-8')
                        except UnicodeDecodeError:
                            value = unicode(value,backupEncoding)
                        insSeek(pos)
                        self[id] = value
                    except:
                        deprint(u'Error reading string file:')
                        deprint(u'id:', id)
                        deprint(u'offset:', offset)
                        deprint(u'filePos:',  insTell())
                        raise
        except:
            deprint(u'Error loading string file:', path.stail, traceback=True)
            return

# WryeText --------------------------------------------------------------------
codebox = None
class WryeText:
    """This class provides a function for converting wtxt text files to html
    files.

    Headings:
    = XXXX >> H1 "XXX"
    == XXXX >> H2 "XXX"
    === XXXX >> H3 "XXX"
    ==== XXXX >> H4 "XXX"
    Notes:
    * These must start at first character of line.
    * The XXX text is compressed to form an anchor. E.g == Foo Bar gets anchored as" FooBar".
    * If the line has trailing ='s, they are discarded. This is useful for making
      text version of level 1 and 2 headings more readable.

    Bullet Lists:
    * Level 1
      * Level 2
        * Level 3
    Notes:
    * These must start at first character of line.
    * Recognized bullet characters are: - ! ? . + * o The dot (.) produces an invisible
      bullet, and the * produces a bullet character.

    Styles:
      __Text__
      ~~Italic~~
      **BoldItalic**
    Notes:
    * These can be anywhere on line, and effects can continue across lines.

    Links:
     [[file]] produces <a href=file>file</a>
     [[file|text]] produces <a href=file>text</a>
     [[!file]] produces <a href=file target="_blank">file</a>
     [[!file|text]] produces <a href=file target="_blank">text</a>

    Contents
    {{CONTENTS=NN}} Where NN is the desired depth of contents (1 for single level,
    2 for two levels, etc.).
    """

    # Data ------------------------------------------------------------------------
    htmlHead = u"""<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.0 Strict//EN"
    "http://www.w3.org/TR/xhtml1/DTD/xhtml1-strict.dtd">
    <html xmlns="http://www.w3.org/1999/xhtml" xml:lang="en" lang="en">
    <head>
    <meta http-equiv="Content-Type" content="text/html;charset=utf-8" />
    <title>%s</title>
    <style type="text/css">%s</style>
    </head>
    <body>
    """
    defaultCss = u"""
    h1 { margin-top: 0in; margin-bottom: 0in; border-top: 1px solid #000000; border-bottom: 1px solid #000000; border-left: none; border-right: none; padding: 0.02in 0in; background: #c6c63c; font-family: "Arial", serif; font-size: 12pt; page-break-before: auto; page-break-after: auto }
    h2 { margin-top: 0in; margin-bottom: 0in; border-top: 1px solid #000000; border-bottom: 1px solid #000000; border-left: none; border-right: none; padding: 0.02in 0in; background: #e6e64c; font-family: "Arial", serif; font-size: 10pt; page-break-before: auto; page-break-after: auto }
    h3 { margin-top: 0in; margin-bottom: 0in; font-family: "Arial", serif; font-size: 10pt; font-style: normal; page-break-before: auto; page-break-after: auto }
    h4 { margin-top: 0in; margin-bottom: 0in; font-family: "Arial", serif; font-style: italic; page-break-before: auto; page-break-after: auto }
    a:link { text-decoration:none; }
    a:hover { text-decoration:underline; }
    p { margin-top: 0.01in; margin-bottom: 0.01in; font-family: "Arial", serif; font-size: 10pt; page-break-before: auto; page-break-after: auto }
    p.empty {}
    p.list-1 { margin-left: 0.15in; text-indent: -0.15in }
    p.list-2 { margin-left: 0.3in; text-indent: -0.15in }
    p.list-3 { margin-left: 0.45in; text-indent: -0.15in }
    p.list-4 { margin-left: 0.6in; text-indent: -0.15in }
    p.list-5 { margin-left: 0.75in; text-indent: -0.15in }
    p.list-6 { margin-left: 1.00in; text-indent: -0.15in }
    .code-n { background-color: #FDF5E6; font-family: "Lucide Console", monospace; font-size: 10pt; white-space: pre; }
    pre { border: 1px solid; overflow: auto; width: 750px; word-wrap: break-word; background: #FDF5E6; padding: 0.5em; margin-top: 0in; margin-bottom: 0in; margin-left: 0.25in}
    code { background-color: #FDF5E6; font-family: "Lucida Console", monospace; font-size: 10pt; }
    td.code { background-color: #FDF5E6; font-family: "Lucida Console", monospace; font-size: 10pt; border: 1px solid #000000; padding:5px; width:50%;}
    body { background-color: #ffffcc; }
    """

    # Conversion ---------------------------------------------------------------
    @staticmethod
    def genHtml(ins,out=None,*cssDirs):
        """Reads a wtxt input stream and writes an html output stream."""
        import string, urllib
        # Path or Stream? -----------------------------------------------
        if isinstance(ins,(Path,str,unicode)):
            srcPath = GPath(ins)
            outPath = GPath(out) or srcPath.root+u'.html'
            cssDirs = (srcPath.head,) + cssDirs
            ins = srcPath.open(encoding='utf-8-sig')
            out = outPath.open('w',encoding='utf-8-sig')
        else:
            srcPath = outPath = None
        # Setup
        outWrite = out.write

        cssDirs = map(GPath,cssDirs)
        # Setup ---------------------------------------------------------
        #--Headers
        reHead = re.compile(ur'(=+) *(.+)',re.U)
        headFormat = u"<h%d><a id='%s'>%s</a></h%d>\n"
        headFormatNA = u"<h%d>%s</h%d>\n"
        #--List
        reList = re.compile(ur'( *)([-x!?\.\+\*o])(.*)',re.U)
        #--Code
        reCode = re.compile(ur'\[code\](.*?)\[/code\]',re.I|re.U)
        reCodeStart = re.compile(ur'(.*?)\[code\](.*?)$',re.I|re.U)
        reCodeEnd = re.compile(ur'(.*?)\[/code\](.*?)$',re.I|re.U)
        reCodeBoxStart = re.compile(ur'\s*\[codebox\](.*?)',re.I|re.U)
        reCodeBoxEnd = re.compile(ur'(.*?)\[/codebox\]\s*',re.I|re.U)
        reCodeBox = re.compile(ur'\s*\[codebox\](.*?)\[/codebox\]\s*',re.I|re.U)
        codeLines = None
        codeboxLines = None
        def subCode(match):
            try:
                return u' '.join(codebox([match.group(1)],False,False))
            except:
                return match(1)
        #--Misc. text
        reHr = re.compile(u'^------+$',re.U)
        reEmpty = re.compile(ur'\s+$',re.U)
        reMDash = re.compile(ur' -- ',re.U)
        rePreBegin = re.compile(u'<pre',re.I|re.U)
        rePreEnd = re.compile(u'</pre>',re.I|re.U)
        anchorlist = [] #to make sure that each anchor is unique.
        def subAnchor(match):
            text = match.group(1)
            # This one's weird.  Encode the url to utf-8, then allow urllib to do it's magic.
            # urllib will automatically take any unicode characters and escape them, so to
            # convert back to unicode for purposes of storing the string, everything will
            # be in cp1252, due to the escapings.
            anchor = unicode(urllib.quote(reWd.sub(u'',text).encode('utf8')),'cp1252')
            count = 0
            if re.match(ur'\d', anchor):
                anchor = u'_' + anchor
            while anchor in anchorlist and count < 10:
                count += 1
                if count == 1:
                    anchor += unicode(count)
                else:
                    anchor = anchor[:-1] + unicode(count)
            anchorlist.append(anchor)
            return u"<a id='%s'>%s</a>" % (anchor,text)
        #--Bold, Italic, BoldItalic
        reBold = re.compile(ur'__',re.U)
        reItalic = re.compile(ur'~~',re.U)
        reBoldItalic = re.compile(ur'\*\*',re.U)
        states = {'bold':False,'italic':False,'boldItalic':False,'code':0}
        def subBold(match):
            state = states['bold'] = not states['bold']
            return u'<b>' if state else u'</b>'
        def subItalic(match):
            state = states['italic'] = not states['italic']
            return u'<i>' if state else u'</i>'
        def subBoldItalic(match):
            state = states['boldItalic'] = not states['boldItalic']
            return u'<i><b>' if state else u'</b></i>'
        #--Preformatting
        #--Links
        reLink = re.compile(ur'\[\[(.*?)\]\]',re.U)
        reHttp = re.compile(ur' (http://[_~a-zA-Z0-9\./%-]+)',re.U)
        reWww = re.compile(ur' (www\.[_~a-zA-Z0-9\./%-]+)',re.U)
        reWd = re.compile(ur'(<[^>]+>|\[\[[^\]]+\]\]|\s+|[%s]+)' % re.escape(string.punctuation.replace(u'_',u'')),re.U)
        rePar = re.compile(ur'^(\s*[a-zA-Z(;]|\*\*|~~|__|\s*<i|\s*<a)',re.U)
        reFullLink = re.compile(ur'(:|#|\.[a-zA-Z0-9]{2,4}$)',re.U)
        reColor = re.compile(ur'\[\s*color\s*=[\s\"\']*(.+?)[\s\"\']*\](.*?)\[\s*/\s*color\s*\]',re.I|re.U)
        reBGColor = re.compile(ur'\[\s*bg\s*=[\s\"\']*(.+?)[\s\"\']*\](.*?)\[\s*/\s*bg\s*\]',re.I|re.U)
        def subColor(match):
            return u'<span style="color:%s;">%s</span>' % (match.group(1),match.group(2))
        def subBGColor(match):
            return u'<span style="background-color:%s;">%s</span>' % (match.group(1),match.group(2))
        def subLink(match):
            address = text = match.group(1).strip()
            if u'|' in text:
                (address,text) = [chunk.strip() for chunk in text.split(u'|',1)]
                if address == u'#': address += unicode(urllib.quote(reWd.sub(u'',text).encode('utf8')),'cp1252')
            if address.startswith(u'!'):
                newWindow = u' target="_blank"'
                address = address[1:]
            else:
                newWindow = u''
            if not reFullLink.search(address):
                address = address+u'.html'
            return u'<a href="%s"%s>%s</a>' % (address,newWindow,text)
        #--Tags
        reAnchorTag = re.compile(u'{{A:(.+?)}}',re.U)
        reContentsTag = re.compile(ur'\s*{{CONTENTS=?(\d+)}}\s*$',re.U)
        reAnchorHeadersTag = re.compile(ur'\s*{{ANCHORHEADERS=(\d+)}}\s*$',re.U)
        reCssTag = re.compile(u'\s*{{CSS:(.+?)}}\s*$',re.U)
        #--Defaults ----------------------------------------------------------
        title = u''
        level = 1
        spaces = u''
        cssName = None
        #--Init
        outLines = []
        contents = []
        outLinesAppend = outLines.append
        outLinesExtend = outLines.extend
        addContents = 0
        inPre = False
        anchorHeaders = True
        #--Read source file --------------------------------------------------
        for line in ins:
            line = line.replace('\r\n','\n')
            #--Codebox -----------------------------------
            if codebox:
                if codeboxLines is not None:
                    maCodeBoxEnd = reCodeBoxEnd.match(line)
                    if maCodeBoxEnd:
                        codeboxLines.append(maCodeBoxEnd.group(1))
                        outLinesAppend(u'<pre style="width:850px;">')
                        try:
                            codeboxLines = codebox(codeboxLines)
                        except:
                            pass
                        outLinesExtend(codeboxLines)
                        outLinesAppend(u'</pre>\n')
                        codeboxLines = None
                        continue
                    else:
                        codeboxLines.append(line)
                        continue
                maCodeBox = reCodeBox.match(line)
                if maCodeBox:
                    outLines.append(u'<pre style="width:850px;">')
                    try:
                        outLinesExtend(codebox([maCodeBox.group(1)]))
                    except:
                        outLinesAppend(maCodeBox.group(1))
                    outLinesAppend(u'</pre>\n')
                    continue
                maCodeBoxStart = reCodeBoxStart.match(line)
                if maCodeBoxStart:
                    codeboxLines = [maCodeBoxStart.group(1)]
                    continue
            #--Code --------------------------------------
                if codeLines is not None:
                    maCodeEnd = reCodeEnd.match(line)
                    if maCodeEnd:
                        codeLines.append(maCodeEnd.group(1))
                        try:
                            codeLines = codebox(codeLines,False)
                        except:
                            pass
                        outLinesExtend(codeLines)
                        codeLines = None
                        line = maCodeEnd.group(2)
                    else:
                        codeLines.append(line)
                        continue
                line = reCode.sub(subCode,line)
                maCodeStart = reCodeStart.match(line)
                if maCodeStart:
                    line = maCodeStart.group(1)
                    codeLines = [maCodeStart.group(2)]
            #--Preformatted? -----------------------------
            maPreBegin = rePreBegin.search(line)
            maPreEnd = rePreEnd.search(line)
            if inPre or maPreBegin or maPreEnd:
                inPre = maPreBegin or (inPre and not maPreEnd)
                outLinesAppend(line)
                continue
            #--Font/Background Color
            line = reColor.sub(subColor,line)
            line = reBGColor.sub(subBGColor,line)
            #--Re Matches -------------------------------
            maContents = reContentsTag.match(line)
            maAnchorHeaders = reAnchorHeadersTag.match(line)
            maCss = reCssTag.match(line)
            maHead = reHead.match(line)
            maList  = reList.match(line)
            maPar   = rePar.match(line)
            maEmpty = reEmpty.match(line)
            #--Contents
            if maContents:
                if maContents.group(1):
                    addContents = int(maContents.group(1))
                else:
                    addContents = 100
                inPar = False
            elif maAnchorHeaders:
                anchorHeaders = maAnchorHeaders.group(1) != u'0'
                continue
            #--CSS
            elif maCss:
                #--Directory spec is not allowed, so use tail.
                cssName = GPath(maCss.group(1).strip()).tail
                continue
            #--Headers
            elif maHead:
                lead,text = maHead.group(1,2)
                text = re.sub(u' *=*#?$','',text.strip())
                anchor = unicode(urllib.quote(reWd.sub(u'',text).encode('utf8')),'cp1252')
                level = len(lead)
                if anchorHeaders:
                    if re.match(ur'\d', anchor):
                        anchor = u'_' + anchor
                    count = 0
                    while anchor in anchorlist and count < 10:
                        count += 1
                        if count == 1:
                            anchor += unicode(count)
                        else:
                            anchor = anchor[:-1] + unicode(count)
                    anchorlist.append(anchor)
                    line = (headFormatNA,headFormat)[anchorHeaders] % (level,anchor,text,level)
                    if addContents: contents.append((level,anchor,text))
                else:
                    line = headFormatNA % (level,text,level)
                #--Title?
                if not title and level <= 2: title = text
            #--Paragraph
            elif maPar and not states['code']:
                line = u'<p>'+line+u'</p>\n'
            #--List item
            elif maList:
                spaces = maList.group(1)
                bullet = maList.group(2)
                text = maList.group(3)
                if bullet == u'.': bullet = u'&nbsp;'
                elif bullet == u'*': bullet = u'&bull;'
                level = len(spaces)/2 + 1
                line = spaces+u'<p class="list-%i">'%level+bullet+u'&nbsp; '
                line = line + text + u'</p>\n'
            #--Empty line
            elif maEmpty:
                line = spaces+u'<p class="empty">&nbsp;</p>\n'
            #--Misc. Text changes --------------------
            line = reHr.sub(u'<hr>',line)
            line = reMDash.sub(u' &#150; ',line)
            #--Bold/Italic subs
            line = reBold.sub(subBold,line)
            line = reItalic.sub(subItalic,line)
            line = reBoldItalic.sub(subBoldItalic,line)
            #--Wtxt Tags
            line = reAnchorTag.sub(subAnchor,line)
            #--Hyperlinks
            line = reLink.sub(subLink,line)
            line = reHttp.sub(ur' <a href="\1">\1</a>',line)
            line = reWww.sub(ur' <a href="http://\1">\1</a>',line)
            #--Save line ------------------
            #print line,
            outLines.append(line)
        #--Get Css -----------------------------------------------------------
        if not cssName:
            css = WryeText.defaultCss
        else:
            if cssName.ext != u'.css':
                raise BoltError(u'Invalid Css file: '+cssName.s)
            for dir in cssDirs:
                cssPath = GPath(dir).join(cssName)
                if cssPath.exists(): break
            else:
                raise BoltError(u'Css file not found: '+cssName.s)
            with cssPath.open('r',encoding='utf-8-sig') as cssIns:
                css = u''.join(cssIns.readlines())
            if u'<' in css:
                raise BoltError(u'Non css tag in '+cssPath.s)
        #--Write Output ------------------------------------------------------
        outWrite(WryeText.htmlHead % (title,css))
        didContents = False
        for line in outLines:
            if reContentsTag.match(line):
                if contents and not didContents:
                    baseLevel = min([level for (level,name,text) in contents])
                    for (level,name,text) in contents:
                        level = level - baseLevel + 1
                        if level <= addContents:
                            outWrite(u'<p class="list-%d">&bull;&nbsp; <a href="#%s">%s</a></p>\n' % (level,name,text))
                    didContents = True
            else:
                outWrite(line)
        outWrite(u'</body>\n</html>\n')
        #--Close files?
        if srcPath:
            ins.close()
            out.close()

# Main -------------------------------------------------------------------------
if __name__ == '__main__' and len(sys.argv) > 1:
    #--Commands----------------------------------------------------------------
    @mainfunc
    def genHtml(*args,**keywords):
        """Wtxt to html. Just pass through to WryeText.genHtml."""
        if not len(args):
            args = [u"..\Wrye Bash.txt"]
        WryeText.genHtml(*args,**keywords)

    #--Command Handler --------------------------------------------------------
    _mainFunctions.main()
