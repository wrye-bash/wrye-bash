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
import wx # YAK - sizers
from collections import OrderedDict
# Local
from . import BashTab, _SashDetailsPanel, MasterList
from .. import load_order, bosh
from ..balt import UIList, vSizer, vspace, hSizer, StaticText, TextCtrl
from ..bolt import formatDate

class _LoMasterList(MasterList):
    mainMenu = itemMenu = None
    _col_names = {
        'File': _(u'File'),
        'Current Order': _(u'Current LO'),
        'Num': _(u'LO'),
        }
    def _generate_master_infos(self):
        for mi, masters_name in enumerate(self.fileInfo.lord.loadOrder):
            masterInfo = bosh.MasterInfo(masters_name)
            self.data_store[mi] = masterInfo

    @staticmethod
    def _get_column_name(colKey):
        return _LoMasterList._col_names.get(colKey, colKey)

class LoDetails(_SashDetailsPanel):
    keyPrefix = 'bash.mods.loadOrders.details' # used in sash/scroll position, sorting
    _master_list_type = _LoMasterList
    _masters_text = _(u"Saved Load Order:")

    @property
    def file_info(self):
        return self.panel_uilist.data_store[self._displayed_lo_index] \
            if self._displayed_lo_index is not None else None
    @property
    def displayed_item(self): return self._displayed_lo_index
    @property
    def file_infos(self): return self.panel_uilist.data_store
    @property
    def allowDetailsEdit(self): return False

    def __init__(self, parent):
        super(LoDetails, self).__init__(parent)
        self._displayed_lo_index = None
        #--Layout
        detailsSizer = vSizer(vspace(),
            (hSizer(
                (StaticText(self.top,_(u"Load order save date:")))),0,wx.EXPAND),
            (hSizer((self.file,1,wx.EXPAND)),0,wx.EXPAND),
            )
        detailsSizer.SetSizeHints(self.top)
        self.top.SetSizer(detailsSizer)
        #--Lo Info
        textWidth = 200
        self.gInfo = TextCtrl(self._bottom_low_panel, size=(textWidth, 64),
                              multiline=True, # onText=self.OnInfoEdit,
                              maxChars=2048)
        tagsSizer = vSizer(vspace(),
            (StaticText(self._bottom_low_panel, _(u"Bash Tags:"))),
            (hSizer((self.gInfo, 1, wx.EXPAND)), 1, wx.EXPAND))
        tagsSizer.SetSizeHints(self.masterPanel)
        self._bottom_low_panel.SetSizer(tagsSizer)
        self.bottom.SetSizer(vSizer((self.subSplitter,1,wx.EXPAND)))

    def _resetDetails(self):
        self._displayed_lo_index = None
        self.fileStr = u''

    def SetFile(self,fileName='SAME'):
        fileName = super(LoDetails, self).SetFile(fileName)
        if fileName:
            self._displayed_lo_index = fileName
            #--Remember values for edit checks
            self.fileStr = formatDate(self.file_info.date)
        else: self.fileStr = u''
        #--Set fields
        self.file.SetValue(self.fileStr)
        self.uilist.SetFileInfo(self.file_info)

class LoList(UIList):
    labels = OrderedDict([
        ('Index',    lambda self, p: unicode(p)),
        ('Date',     lambda self, p: formatDate(self.data_store[p].date)),
    ])
    _sort_keys = {
        'Index': None, # just sort by index
        'Date' : lambda self, a: self.data_store[a].date,
    }
    _default_sort_col = 'Index'

class LoPanel(BashTab):
    _details_panel_type = LoDetails
    _ui_list_type = LoList
    keyPrefix = 'bash.mods.loadOrders'

    def __init__(self, parent):
        self.listData = {x: y for x, y in
                         enumerate(load_order.get_saved_load_orders())}
        super(LoPanel, self).__init__(parent)
