#===============================================================================
# Convert old format translation files to new format translation files
# If the language isn't one of 'de','italian','pt_opt','russian',
# or 'chinese', you'll have to edit the file and put in the correct
# charset later
#
# Usage:
#  Place in the same folder as your translation .txt file(s)
#  Run the script.  The old translation file will be backed up
#===============================================================================
import os
import re

header = r"""# SOME DESCRIPTIVE TITLE.
# Copyright (C) YEAR ORGANIZATION
# FIRST AUTHOR <EMAIL@ADDRESS>, YEAR.
#
msgid ""
msgstr ""
"Project-Id-Version: PACKAGE VERSION\n"
"POT-Creation-Date: 2011-12-18 18:26+Alaskan Standard Time\n"
"PO-Revision-Date: YEAR-MO-DA HO:MI+ZONE\n"
"Last-Translator: FULL NAME <EMAIL@ADDRESS>\n"
"Language-Team: LANGUAGE <LL@li.org>\n"
"MIME-Version: 1.0\n"
"Content-Type: text/plain; charset=%s\n"
"Content-Transfer-Encoding: utf8\n"
"Generated-By: pygettext.py 1.5\n"
"""

reStart = re.compile(r'^=== (.*?), (\d*)$')
reTranslateTo = re.compile(r'^>>>>$')
reStartMatch = reStart.match
reTransToMatch = reTranslateTo.match

reNonEscapedQuote = re.compile(r'[^\\]\"')
subDQuote = reNonEscapedQuote.sub

reFixQuotes = re.compile(r'\\\s*\"')
subFixQuotes = reFixQuotes.sub

def main():
    for file in os.listdir(os.getcwdu()):
        basename,ext = os.path.splitext(file)
        ext = ext.lower()
        if ext != u'.txt': continue
        newFile = basename+'.tmp'
        basename = basename.lower()
        if os.path.exists(file+'.bak'):
            os.remove(file)
            os.rename(file+'.bak',file)
        with open(file,'r') as ins:
            with open(newFile,'w') as out:
                print 'converting', file
                if basename in ('de','italian','pt_opt'): charset = 'cp1252'
                elif basename == 'russian': charset = 'cp1251'
                elif basename == 'chinese': charset = 'cp936'
                else: charset = 'CHARSET'
                out.write(header % charset)
                start = False
                trans = False
                for i,line in enumerate(ins):
                    if not start:
                        maStart = reStartMatch(line)
                        if maStart:
                            out.write('\n#: bash\\%s:%s\n' % (maStart.group(1),maStart.group(2)))
                            start = True
                            trans = False
                            continue
                    elif not trans:
                        maTrans = reTransToMatch(line)
                        if maTrans:
                            trans = True
                            start = False
                            continue
                    if start or trans:
                        if '"' in line:
                            line = subFixQuotes('\\"',line)
                            line = subDQuote('\\"',line)
                        lines = line.split('\\n')
                    if start:
                        out.write('msgid ')
                        for line in lines:
                            out.write('"%s"\n' % line.strip('\n\r'))
                    elif trans:
                        out.write('msgstr ')
                        for line in lines:
                            out.write('"%s"\n' % line.strip('\n\r'))
        os.rename(file,file+'.bak')
        os.rename(newFile,file)

if __name__=='__main__':
    main()