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
#  Wrye Bash copyright (C) 2005-2009 Wrye, 2010-2020 Wrye Bash Team
#  https://github.com/wrye-bash
#
# =============================================================================
from collections import OrderedDict
# Local
from . import _ModsSavesDetails, BashTab, MasterList
from .. import load_order, bosh
from ..balt import UIList
from ..gui import Label, LayoutOptions, TextArea, VLayout
from ..localize import format_date

class _LoMasterList(MasterList):
    mainMenu = itemMenu = None
    _col_names = {
        u'File': _(u'File'),
        u'Current Order': _(u'Current LO'),
        u'Num': _(u'LO'),
    }

    def _generate_master_infos(self):
        for mi, masters_name in enumerate(self.fileInfo.lord.loadOrder):
            self.data_store[mi] = bosh.MasterInfo(masters_name)

    @staticmethod
    def _get_column_name(colKey):
        return _LoMasterList._col_names.get(colKey, colKey)

class LoDetails(_ModsSavesDetails):
    minimumSize = 64 # allow making the master list really big
    # used in sash/scroll position, sorting
    keyPrefix = u'bash.mods.load_orders.details'
    _master_list_type = _LoMasterList
    _masters_text = _(u'Saved Load Order:')
    _panel_border = 4

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

    def __init__(self, parent, ui_list_panel):
        super(LoDetails, self).__init__(parent, ui_list_panel)
        top, bottom = self.left, self.right
        self.file.editable = False ##: at least for now?
        self.g_lo_notes = TextArea(self._bottom_low_panel,
                                   max_length=2048) # TODO(inf) NYI
        VLayout(item_expand=True, items=[
            Label(top, _(u'Load Order Save Date:')),
            (self.file, LayoutOptions(weight=1)),
        ]).apply_to(top)
        VLayout(items=[
            Label(self._bottom_low_panel, _(u'Load Order Notes:')),
            (self.g_lo_notes, LayoutOptions(expand=True, weight=1))
        ]).apply_to(self._bottom_low_panel)

    def _resetDetails(self):
        self._displayed_lo_index = None
        self.fileStr = u''

    def SetFile(self, fileName=u'SAME'):
        fileName = super(LoDetails, self).SetFile(fileName)
        if fileName:
            self._displayed_lo_index = fileName
            #--Remember values for edit checks
            self.fileStr = format_date(self.file_info.date)
        else: self.fileStr = u''
        #--Set fields
        self.file.text_content = self.fileStr
        self.uilist.SetFileInfo(self.file_info)

class LoList(UIList):
    labels = OrderedDict([
        (u'Index', lambda self, p: unicode(p)),
        (u'Date',  lambda self, p: format_date(self.data_store[p].date)),
    ])
    _sort_keys = {
        u'Index': None, # just sort by index
        u'Date' : lambda self, a: self.data_store[a].date,
    }
    _default_sort_col = u'Index'

class LoPanel(BashTab):
    _details_panel_type = LoDetails
    _ui_list_type = LoList
    _panel_border = 4 # Add some space on the edges, looks better in a dialog
    keyPrefix = u'bash.mods.load_orders'

    def __init__(self, parent):
        class _LoListData(dict):
            """Quick HACK for SashUIListPanel.ClosePanel"""
            def save(self): pass
        self.listData = _LoListData({x: y for x, y in enumerate(
            load_order.get_saved_load_orders())})
        super(LoPanel, self).__init__(parent)
