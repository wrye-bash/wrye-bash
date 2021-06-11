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
#  Wrye Bash copyright (C) 2005-2009 Wrye, 2010-2021 Wrye Bash Team
#  https://github.com/wrye-bash
#
# =============================================================================

"""Menu items for the main and item menus of the ini tweaks tab - their window
attribute points to BashFrame.iniList singleton.
"""
from .. import bass, bosh, balt
from ..balt import ItemLink, BoolLink, EnabledLink, OneItemLink
from ..gui import copy_text_to_clipboard

__all__ = [u'INI_SortValid', u'INI_AllowNewLines', u'INI_ListINIs',
           u'INI_Apply', u'INI_CreateNew', u'INI_ListErrors',
           u'INI_FileOpenOrCopy', u'INI_Delete']

class INI_SortValid(BoolLink):
    """Sort valid INI Tweaks to the top."""
    _text, _bl_key, _help = _(u'Valid Tweaks First'), u'bash.ini.sortValid', \
                            _(u'Valid tweak files will be shown first.')

    def Execute(self):
        super(INI_SortValid, self).Execute()
        self.window.SortItems()

#------------------------------------------------------------------------------
class INI_AllowNewLines(BoolLink):
    """Consider INI Tweaks with new lines valid."""
    _text = _(u'Allow Tweaks with New Settings')
    _bl_key = u'bash.ini.allowNewLines'
    _help = _(u'Tweak files adding new sections/settings are considered valid')

    def Execute(self):
        super(INI_AllowNewLines, self).Execute()
        self.window.RefreshUI()

#------------------------------------------------------------------------------
class INI_ListINIs(ItemLink):
    """List errors that make an INI Tweak invalid."""
    _text = _(u'List Active INI Tweaks...')
    _help = _(u'Lists all fully applied tweak files.')

    def Execute(self):
        """Handle printing out the errors."""
        tweak_list = self.window.ListTweaks()
        copy_text_to_clipboard(tweak_list)
        self._showLog(tweak_list, title=_(u'Active INIs'), fixedFont=False)

#------------------------------------------------------------------------------
class INI_ListErrors(EnabledLink):
    """List errors that make an INI Tweak invalid."""
    _text = _(u'List Errors...')
    _help = _(u'Lists any errors in the tweak file causing it to be invalid.')

    def _enable(self):
        return any(map(lambda inf: inf.tweak_status() < 0,
                        self.iselected_infos()))

    def Execute(self):
        """Handle printing out the errors."""
        error_text = u'\n'.join(inf.listErrors() for inf in
                                self.iselected_infos())
        copy_text_to_clipboard(error_text)
        self._showLog(error_text, title=_(u'INI Tweak Errors'),
                      fixedFont=False)

#------------------------------------------------------------------------------
class INI_FileOpenOrCopy(EnabledLink):
    """Open specified file(s) only if they aren't Bash supplied defaults."""
    def _targets_default(self):
        return next(self.iselected_infos()).is_default_tweak

    def _enable(self):
        first_default = self._targets_default()
        return all(i.is_default_tweak == first_default
                   for i in self.iselected_infos())

    @property
    def link_text(self):
        return [_(u'Open...'), _(u'Copy...')][self._targets_default()]

    @property
    def link_help(self):
        return  [_(u"Open the selected INI file(s) with the system's default "
                   u"program."),
                 _(u"Make an editable copy of the selected default "
                   u"tweak(s).")][self._targets_default()]

    def Execute(self):
        newly_copied = []
        for i in self.selected:
            if bosh.iniInfos.open_or_copy(i):
                newly_copied.append(i)
        self.window.RefreshUI(redraw=newly_copied)

#------------------------------------------------------------------------------
class INI_Delete(balt.UIList_Delete, EnabledLink):
    """Delete the file and all backups."""

    def _initData(self, window, selection):
        super(INI_Delete, self)._initData(window, selection)
        self.selected = self.window.filterOutDefaultTweaks(self.selected)
        if len(self.selected) and len(selection) == 1:
            self._help = _(u'Delete %(filename)s.') % ({u'filename': selection[0]})
        elif len(self.selected):
            self._help = _(
                u"Delete selected tweaks (default tweaks won't be deleted)")
        else: self._help = _(u"Bash default tweaks can't be deleted")

    def _enable(self): return len(self.selected) > 0

#------------------------------------------------------------------------------
class INI_Apply(EnabledLink):
    """Apply an INI Tweak."""
    _text = _(u'Apply')

    @property
    def link_help(self):
        if len(self.selected) == 1:
            tweak = self.selected[0]
            return _(u"Applies '%(tweak)s' to '%(ini)s'.") % {
                u'tweak': tweak, u'ini': self.window.current_ini_name}
        else:
            return _(u"Applies selected tweaks to '%(ini)s'.") % {
            u'ini': self.window.current_ini_name}

    def _enable(self):
        return all(map(bosh.INIInfo.is_applicable, self.iselected_infos()))

    def Execute(self):
        """Handle applying INI Tweaks."""
        if self.window.apply_tweaks(self.iselected_infos()):
            self.window.panel.ShowPanel()

#------------------------------------------------------------------------------
class INI_CreateNew(OneItemLink):
    """Create a new INI Tweak using the settings from the tweak file,
    but values from the target INI."""
    _text = _(u'Create Tweak with current settings...')

    @property
    def link_help(self):
        if not len(self.selected) == 1:
            return _(u'Please choose one Ini Tweak')
        else:
            return _(u"Creates a new tweak based on '%(tweak)s' but with "
                          u"values from '%(ini)s'.") % {
                u'tweak': (self.selected[0]), u'ini': self.window.current_ini_name}

    def _enable(self): return super(INI_CreateNew, self)._enable() and \
                              self._selected_info.tweak_status >= 0

    @balt.conversation
    def Execute(self):
        """Handle creating a new INI tweak."""
        pathFrom = self._selected_item
        fileName = pathFrom.sbody + u' - Copy' + pathFrom.ext
        tweak_path = self._askSave(
            title=_(u'Copy Tweak with current settings...'),
            defaultDir=bass.dirs[u'ini_tweaks'], defaultFile=fileName,
            wildcard=_(u'INI Tweak File (*.ini)|*.ini'))
        if bosh.iniInfos.duplicate_ini(pathFrom, tweak_path):
            self.window.RefreshUI(redraw=[tweak_path.tail], # to_add
                                  detail_item=tweak_path.tail)
