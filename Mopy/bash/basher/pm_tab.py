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
from collections import defaultdict
import re
from .. import balt
from .. import bosh
from ..balt import Links, TextCtrl, hSizer, vSizer
from . import SashPanel
from ..bosh import formatDate, msgs

class MessageList(balt.UIList):
    #--Class Data
    mainMenu = Links() #--Column menu
    itemMenu = Links() #--Single item menu
    reNoRe = re.compile(u'^Re: *',re.U)
    _recycle = False
    _default_sort_col = 'Date'
    _sort_keys = {'Date': lambda self, a: self.data[a][2],
                  'Subject': lambda self, a: MessageList.reNoRe.sub(
                     u'', self.data[a][0]),
                  'Author': lambda self, a: self.data[a][1],
                 }

    def __init__(self, parent, listData, keyPrefix, panel):
        self.gText = None
        self.searchResults = None
        self.persistent_columns = {'Subject'}
        #--Parent init
        super(MessageList, self).__init__(
            parent, data=listData, keyPrefix=keyPrefix, panel=panel)

    def GetItems(self):
        if self.searchResults is not None: return list(self.searchResults)
        return self.data.keys()

    #--Populate Item
    def getLabels(self, fileName):
        labels = defaultdict(lambda: u'-')
        subject,author,date = self.data[fileName][:3]
        labels['Subject'] = subject
        labels['Date'] = formatDate(date)
        labels['Author'] = author
        return labels

    @staticmethod
    def _gpath(item): return item

    def OnItemSelected(self,event=None):
        keys = self.GetSelected()
        path = bosh.dirs['saveBase'].join(u'Messages.html')
        bosh.messages.writeText(path,*keys)
        self.gText.Navigate(path.s,0x2) #--0x2: Clear History

    def _promptDelete(self, items, dialogTitle=_(u'Delete Messages'),
                      order=False, recycle=False):
        message = _(u'Delete these %d message(s)? This operation cannot'
                    u' be undone.') % len(items)
        yes = balt.askYes(self, message, title=dialogTitle)
        return items if yes else []

class MessagePanel(SashPanel):
    """Messages tab."""
    keyPrefix = 'bash.messages'

    def __init__(self,parent):
        """Initialize."""
        import wx.lib.iewin # IMPORTS wx TOO !
        SashPanel.__init__(self, parent, isVertical=False)
        gTop,gBottom = self.left,self.right
        #--Contents
        self.listData = bosh.messages = msgs.Messages()
        self.uiList = MessageList(
            gTop, listData=self.listData, keyPrefix=self.keyPrefix, panel=self)
        self.uiList.gText = wx.lib.iewin.IEHtmlWindow(
            gBottom, style=wx.NO_FULL_REPAINT_ON_RESIZE)
        #--Search ##: move to textCtrl subclass
        gSearchBox = self.gSearchBox = TextCtrl(gBottom,style=wx.TE_PROCESS_ENTER)
        gSearchButton = balt.Button(gBottom,_(u'Search'),onClick=self.DoSearch)
        gClearButton = balt.Button(gBottom,_(u'Clear'),onClick=self.DoClear)
        #--Events
        #--Following line should use EVT_COMMAND_TEXT_ENTER, but that seems broken.
        gSearchBox.Bind(wx.EVT_CHAR,self.OnSearchChar)
        #--Layout
        gTop.SetSizer(hSizer(
            (self.uiList,1,wx.GROW)))
        gBottom.SetSizer(vSizer(
            (self.uiList.gText,1,wx.GROW),
            (hSizer(
                (gSearchBox,1,wx.GROW),
                (gSearchButton,0,wx.LEFT,4),
                (gClearButton,0,wx.LEFT,4),
                ),0,wx.GROW|wx.TOP,4),
            ))
        wx.LayoutAlgorithm().LayoutWindow(self, gTop)
        wx.LayoutAlgorithm().LayoutWindow(self, gBottom)

    def _sbCount(self):
        used = len(self.uiList.GetItems())
        return _(u'PMs:') + u' %d/%d' % (used, len(self.uiList.data.keys()))

    def ShowPanel(self):
        """Panel is shown. Update self.data."""
        if bosh.messages.refresh():
            self.uiList.RefreshUI()
            #self.Refresh()
        super(MessagePanel, self).ShowPanel()

    def OnSearchChar(self,event):
        if event.GetKeyCode() in balt.wxReturn: self.DoSearch(None)
        else: event.Skip()

    def DoSearch(self,event):
        """Handle search button."""
        term = self.gSearchBox.GetValue()
        self.uiList.searchResults = self.uiList.data.search(term)
        self.uiList.RefreshUI()

    def DoClear(self,event):
        """Handle clear button."""
        self.gSearchBox.SetValue(u'')
        self.uiList.searchResults = None
        self.uiList.RefreshUI()
