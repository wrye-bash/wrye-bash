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
#  Wrye Bash copyright (C) 2005-2009 Wrye, 2010-2023 Wrye Bash Team
#  https://github.com/wrye-bash
#
# =============================================================================
"""Export a Wrye text to html converter."""
from __future__ import annotations

import html
import io
import re
import string
from urllib.parse import quote

from . import exception
from .bolt import Path, GPath, to_unix_newlines

html_start = """<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.0 Strict//EN" "http://www.w3.org/TR/xhtml1/DTD/xhtml1-strict.dtd">
<html xmlns="http://www.w3.org/1999/xhtml" xml:lang="en" lang="en">
    <head>
        <meta http-equiv="Content-Type" content="text/html;charset=utf-8" />
        <title>%s</title>
        <style type="text/css">%s</style>
    </head>
    <body>
"""
html_end = """    </body>
</html>
"""
default_css = """
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

# WryeText --------------------------------------------------------------------
def genHtml(ins, out=None, *css_dirs):
    """Reads a wtxt input stream and writes an html output stream.

    Headings:
    = HHHH >> H1 "HHHH"
    == HHHH >> H2 "HHHH"
    === HHHH >> H3 "HHHH"
    ==== HHHH >> H4 "HHHH"
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
      __Bold__
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
    2 for two levels, etc.)."""
    # Path or Stream? -----------------------------------------------
    if isinstance(ins, (Path, str)):
        srcPath = GPath(ins)
        outPath = GPath(out) or srcPath.root+'.html'
        css_dirs = (srcPath.head,) + css_dirs
        ins = srcPath.open('r', encoding='utf-8-sig')
        out = outPath.open('w', encoding='utf-8-sig')
    else:
        srcPath = outPath = None
    # Setup
    outWrite = out.write
    css_dirs = (GPath(d) for d in css_dirs)
    # Setup ---------------------------------------------------------
    #--Headers
    reHead = re.compile('(=+) *(.+)')
    headFormat = u"<h%d><a id='%s'>%s</a></h%d>\n"
    headFormatNA = '<h%d>%s</h%d>\n'
    #--List
    reWryeList = re.compile('( *)([-x!?.+*o])(.*)')
    #--Code
    reCode = re.compile(r'\[code\](.*?)\[/code\]', re.I)
    reCodeStart = re.compile(r'(.*?)\[code\](.*?)$', re.I)
    reCodeEnd = re.compile(r'(.*?)\[/code\](.*?)$', re.I)
    reCodeBoxStart = re.compile(r'\s*\[codebox\](.*?)', re.I)
    reCodeBoxEnd = re.compile(r'(.*?)\[/codebox\]\s*', re.I)
    reCodeBox = re.compile(r'\s*\[codebox\](.*?)\[/codebox\]\s*', re.I)
    codeLines = None
    codeboxLines = None
    from .ScriptParser import PreParser
    codebox = PreParser().codebox
    def subCode(ma_code):
        try:
            return ' '.join(codebox([ma_code.group(1)], False, False))
        except:
            return ma_code(1)
    #--Misc. text
    reHr = re.compile('^------+$')
    reEmpty = re.compile(r'\s+$')
    reMDash = re.compile(' -- ')
    rePreBegin = re.compile('<pre',re.I)
    rePreEnd = re.compile('</pre>',re.I)
    anchorlist = [] #to make sure that each anchor is unique.
    def subAnchor(ma_anchor):
        text = ma_anchor.group(1)
        anchor = quote(reWd.sub('', text))
        count = 0
        if re.match(r'\d', anchor):
            anchor = '_' + anchor
        while anchor in anchorlist and count < 10:
            count += 1
            if count == 1:
                anchor += str(count)
            else:
                anchor = anchor[:-1] + str(count)
        anchorlist.append(anchor)
        return f"<a id='{anchor}'>{text}</a>"
    #--Bold, Italic, BoldItalic
    reBold = re.compile('__')
    reItalic = re.compile('~~')
    reBoldItalic = re.compile(r'\*\*')
    states = {'bold': False, 'italic': False, 'boldItalic': False,
              'code': 0}
    def subBold(_ma_bold):
        state = states['bold'] = not states['bold']
        return '<b>' if state else '</b>'
    def subItalic(_ma_italic):
        state = states['italic'] = not states['italic']
        return '<i>' if state else '</i>'
    def subBoldItalic(_ma_bold_icalic):
        state = states['boldItalic'] = not states['boldItalic']
        return '<i><b>' if state else '</b></i>'
    #--Preformatting
    #--Links
    reLink = re.compile(r'\[\[(.*?)\]\]')
    reHttp = re.compile(' (http://[_~a-zA-Z0-9./%-]+)')
    reWww = re.compile(r' (www\.[_~a-zA-Z0-9./%-]+)')
    reWd = re.compile(fr'(<[^>]+>|\[\[[^\]]+\]\]|\s+|['
                      fr'{re.escape(string.punctuation.replace("_", ""))}]+)')
    rePar = re.compile(r'^(\s*[a-zA-Z(;]|\*\*|~~|__|\s*<i|\s*<a)')
    reFullLink = re.compile(r'(:|#|\.[a-zA-Z0-9]{2,4}$)')
    reColor = re.compile(
        r'\[\s*color\s*=[\s\"\']*(.+?)[\s\"\']*\](.*?)\[\s*/\s*color\s*\]',
        re.I)
    reBGColor = re.compile(
        r'\[\s*bg\s*=[\s\"\']*(.+?)[\s\"\']*\](.*?)\[\s*/\s*bg\s*\]', re.I)
    def subColor(ma_sub_color):
        return (f'<span style="color:{ma_sub_color.group(1)};">'
                f'{ma_sub_color.group(2)}</span>')
    def subBGColor(ma_bg_color):
        return (f'<span style="background-color:{ma_bg_color.group(1)};">'
                f'{ma_bg_color.group(2)}</span>')
    def subLink(ma_link):
        address = text = ma_link.group(1).strip()
        if '|' in text:
            (address,text) = [chunk.strip() for chunk in text.split('|',1)]
            if address == '#': address += quote(reWd.sub('', text))
        if address.startswith('!'):
            newWindow = ' target="_blank"'
            if address == text:
                # We have no text, cut off the '!' here too
                text = text[1:]
            address = address[1:]
        else:
            newWindow = ''
        if not reFullLink.search(address):
            address += '.html'
        return f'<a href="{address}"{newWindow}>{text}</a>'
    #--Tags
    reAnchorTag = re.compile('{{A:(.+?)}}')
    reContentsTag = re.compile(r'\s*{{CONTENTS=?(\d+)}}\s*$')
    reAnchorHeadersTag = re.compile(r'\s*{{ANCHORHEADERS=(\d+)}}\s*$')
    reCssTag = re.compile(r'\s*{{CSS:(.+?)}}\s*$')
    #--Defaults ----------------------------------------------------------
    title = ''
    spaces = ''
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
        line = html.escape(to_unix_newlines(line))
        #--Codebox -----------------------------------
        if codeboxLines is not None:
            maCodeBoxEnd = reCodeBoxEnd.match(line)
            if maCodeBoxEnd:
                codeboxLines.append(maCodeBoxEnd.group(1))
                outLinesAppend('<pre style="width:850px;">')
                try:
                    codeboxLines = codebox(codeboxLines)
                except:
                    pass
                outLinesExtend(codeboxLines)
                outLinesAppend('</pre>\n')
                codeboxLines = None
                continue
            else:
                codeboxLines.append(line)
                continue
        maCodeBox = reCodeBox.match(line)
        if maCodeBox:
            outLines.append('<pre style="width:850px;">')
            try:
                outLinesExtend(codebox([maCodeBox.group(1)]))
            except:
                outLinesAppend(maCodeBox.group(1))
            outLinesAppend('</pre>\n')
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
                    codeLines = codebox(codeLines, False)
                except:
                    pass
                outLinesExtend(codeLines)
                codeLines = None
                line = maCodeEnd.group(2)
            else:
                codeLines.append(line)
                continue
        line = reCode.sub(subCode, line)
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
        maList  = reWryeList.match(line)
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
            anchorHeaders = maAnchorHeaders.group(1) != '0'
            continue
        #--CSS
        elif maCss:
            #--Directory spec is not allowed, so use tail.
            cssName = GPath(maCss.group(1).strip()).tail
            continue
        #--Headers
        elif maHead:
            lead,text = maHead.group(1,2)
            text = re.sub(' *=*#?$', '', text.strip())
            anchor = quote(reWd.sub('', text))
            level_ = len(lead)
            if anchorHeaders:
                if re.match(r'\d', anchor):
                    anchor = '_' + anchor
                count = 0
                while anchor in anchorlist and count < 10:
                    count += 1
                    if count == 1:
                        anchor += str(count)
                    else:
                        anchor = anchor[:-1] + str(count)
                anchorlist.append(anchor)
                line = (headFormatNA,headFormat)[anchorHeaders] % (level_,anchor,text,level_)
                if addContents: contents.append((level_,anchor,text))
            else:
                line = headFormatNA % (level_,text,level_)
            #--Title?
            if not title and level_ <= 2: title = text
        #--Paragraph
        elif maPar and not states['code']:
            line = f'<p>{line}</p>\n'
        #--List item
        elif maList:
            spaces = maList.group(1)
            bullet = maList.group(2)
            text = maList.group(3)
            if bullet == '.': bullet = '&nbsp;'
            elif bullet == '*': bullet = '&bull;'
            level_ = len(spaces)//2 + 1
            line = f'{spaces}<p class="list-{level_}">{bullet}&nbsp;'
            line = line + text + '</p>\n'
        #--Empty line
        elif maEmpty:
            line = spaces+'<p class="empty">&nbsp;</p>\n'
        #--Misc. Text changes --------------------
        line = reHr.sub('<hr>',line)
        line = reMDash.sub(' &#150; ',line)
        #--Bold/Italic subs
        line = reBold.sub(subBold,line)
        line = reItalic.sub(subItalic,line)
        line = reBoldItalic.sub(subBoldItalic,line)
        #--Wtxt Tags
        line = reAnchorTag.sub(subAnchor,line)
        #--Hyperlinks
        line = reLink.sub(subLink,line)
        line = reHttp.sub(r' <a href="\1">\1</a>', line)
        line = reWww.sub(r' <a href="http://\1">\1</a>', line)
        #--Save line ------------------
        #print line,
        outLines.append(line)
    #--Get Css -----------------------------------------------------------
    if not cssName:
        css = default_css
    else:
        if cssName.ext != '.css':
            raise exception.BoltError(f'Invalid Css file: {cssName}')
        for css_dir in css_dirs:
            cssPath = GPath(css_dir).join(cssName)
            if cssPath.exists(): break
        else:
            raise exception.BoltError(f'Css file not found: {cssName}')
        with cssPath.open('r', encoding='utf-8-sig') as cssIns:
            css = ''.join(cssIns.readlines())
        if '<' in css:
            raise exception.BoltError(f'Non css tag in {cssPath}')
    #--Write Output ------------------------------------------------------
    outWrite(html_start % (title,css))
    didContents = False
    for line in outLines:
        if reContentsTag.match(line):
            if contents and not didContents:
                baseLevel = min([level_ for (level_,name_,text) in contents])
                for (level_,name_,text) in contents:
                    level_ = level_ - baseLevel + 1
                    if level_ <= addContents:
                        outWrite(f'<p class="list-{level_}">&bull;&nbsp; '
                                 f'<a href="#{name_}">{text}</a></p>\n')
                didContents = True
        else:
            outWrite(line)
    outWrite(html_end)
    #--Close files?
    if srcPath:
        ins.close()
        out.close()

def convert_wtext_to_html(logPath, logText, *css_dirs):
    ins = io.StringIO(logText + '\n{{CSS:wtxt_sand_small.css}}')
    with logPath.open('w', encoding='utf-8-sig') as out:
        genHtml(ins, out, *css_dirs)
