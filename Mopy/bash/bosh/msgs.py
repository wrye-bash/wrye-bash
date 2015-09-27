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
import datetime
import re
import time
from .. import bush
from ..bolt import DataDict, sio
from . import PickleDict

class Messages(DataDict):
    """PM message archive."""
    def __init__(self):
        from . import dirs
        self.dictFile = PickleDict(dirs['saveBase'].join(u'Messages.dat'))
        self.data = self.dictFile.data #--data[hash] = (subject,author,date,text)
        self.hasChanged = False
        self.loaded = False

    def refresh(self):
        if not self.loaded:
            self.dictFile.load()
            if len(self.data) == 1 and 'data' in self.data:
                realData = self.data['data']
                self.data.clear()
                self.data.update(realData)
            self.loaded = True

    def save(self):
        """Saves to pickle file."""
        self.dictFile.save()
        self.hasChanged = False

    def delete(self, key, **kwargs):
        """Delete entry."""
        del self.data[key]
        self.hasChanged = True

    def delete_Refresh(self, deleted): pass

    def search(self,term):
        """Search entries for term."""
        term = term.strip()
        if not term: return None
        items = []
        reTerm = re.compile(term,re.I)
        for key,(subject,author,date,text) in self.iteritems():
            if (reTerm.search(subject) or
                reTerm.search(author) or
                reTerm.search(text)
                ):
                items.append(key)
        return items

    def writeText(self,path,*keys):
        """Return html text for each key."""
        with path.open('w',encoding='utf-8-sig') as out:
            out.write(bush.messagesHeader)
            for key in keys:
                out.write(self.data[key][3])
                out.write(u'\n<br />')
            out.write(u"\n</div></body></html>")

    def importArchive(self,path):
        """Import archive file into data."""
        #--Today, yesterday handling
        maPathDate = re.match(ur'(\d+)\.(\d+)\.(\d+)',path.stail,flags=re.U)
        dates = {'today':None,'yesterday':None,'previous':None}
        if maPathDate:
            year,month,day = map(int,maPathDate.groups())
            if year < 100: year += 2000
            dates['today'] = datetime.datetime(year,month,day)
            dates['yesterday'] = dates['today'] - datetime.timedelta(1)
        reRelDate = re.compile(ur'(Today|Yesterday), (\d+):(\d+) (AM|PM)',re.U)
        reAbsDateNew = re.compile(ur'(\d+) (\w+) (\d+) - (\d+):(\d+) (AM|PM)',re.U)
        reAbsDate = re.compile(ur'(\w+) (\d+) (\d+), (\d+):(\d+) (AM|PM)',re.U)
        month_int = dict((x,i+1) for i,x in
            enumerate(u'Jan,Feb,Mar,Apr,May,Jun,Jul,Aug,Sep,Oct,Nov,Dec'.split(u',')))
        month_int.update(dict((x,i+1) for i,x in
            enumerate(u'January,February,March,April,May,June,July,August,September,October,November,December'.split(u','))))
        def getTime(sentOn):
            maRelDate = reRelDate.search(sentOn)
            if not maRelDate:
                #date = time.strptime(sentOn,'%b %d %Y, %I:%M %p')[:-1]+(0,)
                maAbsDate = reAbsDate.match(sentOn)
                if maAbsDate:
                    month,day,year,hour,minute,ampm = maAbsDate.groups()
                else:
                    maAbsDate = reAbsDateNew.match(sentOn)
                    day,month,year,hour,minute,ampm = maAbsDate.groups()
                day,year,hour,minute = map(int,(day,year,hour,minute))
                month = month_int[month]
                hour = (hour,0)[hour==12] + (0,12)[ampm=='PM']
                date = (year,month,day,hour,minute,0,0,0,-1)
                dates['previous'] = datetime.datetime(year,month,day)
            else:
                if not dates['yesterday']:
                    dates['yesterday'] = dates['previous'] + datetime.timedelta(1)
                    dates['today'] = dates['yesterday'] + datetime.timedelta(1)
                strDay,hour,minute,ampm = maRelDate.groups()
                hour,minute = map(int,(hour,minute))
                hour = (hour,0)[hour==12] + (0,12)[ampm==u'PM']
                ymd = dates[strDay.lower()]
                date = ymd.timetuple()[0:3]+(hour,minute,0,0,0,0)
            return time.mktime(date)
        #--Html entity substitution
        from htmlentitydefs import name2codepoint
        def subHtmlEntity(match):
            entity = match.group(2)
            if match.group(1) == u"#":
                return unichr(int(entity)).encode()
            else:
                cp = name2codepoint.get(entity)
                if cp:
                    return unichr(cp).encode()
                else:
                    return match.group()
        #--Re's
        reHtmlEntity = re.compile(u"&(#?)(\d{1,5}|\w{1,8});",re.U)

        #New style re's
        reLineEndings   = re.compile(u"(?:\n)|(?:\r\n)",re.U)
        reBodyNew       = re.compile(u"<body id='ipboard_body'>",re.U)
        reTitleNew      = re.compile(u'<div id=["\']breadcrumb["\']>Bethesda Softworks Forums -> (.*?)</div>',re.U)
        reAuthorNew     = re.compile(u'<h3><a href=["\']http\://forums\.bethsoft\.com/index\.php\?/user/.*?/["\']>(.*?)</a></h3>',re.U)
        reDateNew       = re.compile(u'Sent (.*?)$',re.U)
        reMessageNew    = re.compile(u'<div class=["\']post entry-content["\']>',re.U)
        reEndMessageNew = re.compile(u'^        </div>$',re.U)
        #Old style re's
        reBody         = re.compile(u'<body>',re.U)
        reWrapper      = re.compile(u'<div id=["\']ipbwrapper["\']>',re.U) #--Will be removed
        reMessage      = re.compile(u'<div class="borderwrapm">',re.U)
        reMessageOld   = re.compile(u"<div class='tableborder'>",re.U)
        reTitle        = re.compile(u'<div class="maintitle">PM: (.+)</div>',re.U)
        reTitleOld     = re.compile(u'<div class=\'maintitle\'><img[^>]+>&nbsp;',re.U)
        reSignature    = re.compile(u'<div class="formsubtitle">',re.U)
        reSignatureOld = re.compile(u'<div class=\'pformstrip\'>',re.U)
        reSent         = re.compile(u'Sent (by|to) <b>(.+)</b> on (.+)</div>',re.U)
        #--Final setup, then parse the file
        (HEADER,BODY,MESSAGE,OLDSTYLE,NEWSTYLE,AUTHOR,DATE,MESSAGEBODY) = range(8)
        whichStyle = OLDSTYLE
        mode = HEADER
        buff = None
        subject = u"<No Subject>"
        author = None
        with path.open() as ins:
            for line in ins:
    ##            print mode,'>>',line,
                if mode == HEADER: #--header
                    if reBodyNew.search(line):
                        mode = BODY
                        whichStyle = NEWSTYLE
                    elif reBody.search(line):
                        mode = BODY
                        whichStyle = OLDSTYLE
                if mode != HEADER and whichStyle == OLDSTYLE:
                    line = reMessageOld.sub(u'<div class="borderwrapm">',line)
                    line = reTitleOld.sub(u'<div class="maintitle">',line)
                    line = reSignatureOld.sub(u'<div class="formsubtitle">',line)
                    if mode == BODY:
                        if reMessage.search(line):
                            subject = u"<No Subject>"
                            buff = sio()
                            buff.write(reWrapper.sub(u'',line))
                            mode = MESSAGE
                    elif mode == MESSAGE:
                        if reTitle.search(line):
                            subject = reTitle.search(line).group(1)
                            subject = reHtmlEntity.sub(subHtmlEntity,subject)
                            buff.write(line)
                        elif reSignature.search(line):
                            maSent = reSent.search(line)
                            if maSent:
                                direction = maSent.group(1)
                                author = maSent.group(2)
                                date = getTime(maSent.group(3))
                                messageKey = u'::'.join((subject,author,unicode(int(date))))
                                newSent = (_(u'Sent %s <b>%s</b> on %s</div>') % (direction,
                                    author,time.strftime(u'%b %d %Y, %I:%M %p',time.localtime(date))))
                                line = reSent.sub(newSent,line,1)
                                buff.write(line)
                                self.data[messageKey] = (subject,author,date,buff.getvalue())
                            buff.close()
                            buff = None
                            mode = BODY
                        else:
                            buff.write(line)
                elif mode != HEADER and whichStyle == NEWSTYLE:
                    if mode == BODY:
                        if reTitleNew.search(line):
                            subject = reTitleNew.search(line).group(1)
                            subject = reHtmlEntity.sub(subHtmlEntity,subject)
                            mode = AUTHOR
                    elif mode == AUTHOR:
                        if reAuthorNew.search(line):
                            author = reAuthorNew.search(line).group(1)
                            mode = DATE
                    elif mode == DATE:
                        if reDateNew.search(line):
                            date = reDateNew.search(line).group(1)
                            date = getTime(date)
                            mode = MESSAGE
                    elif mode == MESSAGE:
                        if reMessageNew.search(line):
                            buff = sio()
                            buff.write(u'<br /><div class="borderwrapm">\n')
                            buff.write(u'    <div class="maintitle">PM: %s</div>\n' % subject)
                            buff.write(u'    <div class="tablefill"><div class="postcolor">')
                            mode = MESSAGEBODY
                    elif mode == MESSAGEBODY:
                        if reEndMessageNew.search(line):
                            buff.write(u'    <div class="formsubtitle">Sent by <b>%s</b> on %s</div>\n' % (author,time.strftime('%b %d %Y, %I:%M %p',time.localtime(date))))
                            messageKey = u'::'.join((subject,author,unicode(int(date))))
                            self.data[messageKey] = (subject,author,date,buff.getvalue())
                            buff.close()
                            buff = None
                            mode = AUTHOR
                        else:
                            buff.write(reLineEndings.sub(u'',line))
        self.hasChanged = True
        self.save()

#------------------------------------------------------------------------------
