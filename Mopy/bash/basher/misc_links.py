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
#  Wrye Bash copyright (C) 2005-2009 Wrye, 2010-2019 Wrye Bash Team
#  https://github.com/wrye-bash
#
# =============================================================================

from collections import defaultdict
import re
import time
from ..balt import EnabledLink, AppendableLink, ItemLink, RadioLink, \
    ChoiceMenuLink, CheckLink, UIList_Rename, OneItemLink, SeparatorLink
from ..gui import Image
from .. import bass, balt, bosh, bush
from .import People_Link, SaveDetails
from ..bolt import GPath

__all__ = ['ColumnsMenu', 'Master_ChangeTo', 'Master_Disable',
           'Screens_NextScreenShot', 'Screens_JpgQuality',
           'Screens_JpgQualityCustom', 'Screen_Rename', 'Screen_ConvertTo',
           'People_AddNew', 'People_Import', 'People_Karma', 'People_Export',
           'Master_AllowEdit', 'Master_ClearRenames', 'SortByMenu']

# Screen Links ----------------------------------------------------------------
#------------------------------------------------------------------------------
class Screens_NextScreenShot(EnabledLink):
    """Sets screenshot base name and number."""
    _text = _(u'Next Shot...')
    _help = _(u'Set screenshot base name and number')
    rePattern = re.compile(u'' r'^(.+?)(\d*)$', re.I | re.U)

    def _enable(self):
        return not bosh.oblivionIni.isCorrupted \
               and bosh.oblivionIni.abs_path.exists()

    @property
    def menu_help(self):
        if not self._enable():
            return self._help + u'.  ' + _(u'%(ini)s must exist') % {
                'ini': bush.game.iniFiles[0]}
        else: return self._help

    def Execute(self):
        base_key = bush.game.Ini.screenshot_base_key
        index_key = bush.game.Ini.screenshot_index_key
        enabled_key = bush.game.Ini.screenshot_enabled_key
        base = bosh.oblivionIni.getSetting(*base_key)
        index = bosh.oblivionIni.getSetting(*index_key)
        pattern = self._askText(
            _(u'Screenshot base name, optionally with next screenshot number.')
            + u'\n' +
            _(u'E.g. ScreenShot, ScreenShot_101 or Subdir\\ScreenShot_201.'),
            default=base + index)
        if not pattern: return
        new_base, new_index = self.__class__.rePattern.match(pattern).groups()
        settings_screens = defaultdict(dict)
        settings_screens[base_key[0]][base_key[1]] = new_base
        settings_screens[index_key[0]][index_key[1]] = (new_index or index)
        settings_screens[enabled_key[0]][enabled_key[1]] = enabled_key[2]
        screens_dir = GPath(new_base).head
        if screens_dir:
            if not screens_dir.isabs(): screensDir = bass.dirs[u'app'].join(
                screens_dir)
            screens_dir.makedirs()
        bosh.oblivionIni.saveSettings(settings_screens)
        bosh.screen_infos.refresh()
        self.window.RefreshUI()

#------------------------------------------------------------------------------
class Screen_ConvertTo(EnabledLink):
    """Converts selected images to another type."""
    _help = _(u'Convert selected images to another format')

    def __init__(self,ext,imageType):
        super(Screen_ConvertTo, self).__init__()
        self.ext = ext.lower()
        self.imageType = imageType
        self._text = _(u'Convert to %s') % self.ext

    def _enable(self):
        self.convertable = [s for s in self.selected if
                            s.cext != u'.' + self.ext]
        return bool(self.convertable)

    def Execute(self):
        try:
            with balt.Progress(_(u'Converting to %s') % self.ext) as progress:
                progress.setFull(len(self.convertable))
                for index, fileName in enumerate(self.convertable):
                    progress(index,fileName.s)
                    srcPath = bosh.screen_infos[fileName].abs_path
                    destPath = srcPath.root+u'.'+self.ext
                    if srcPath == destPath or destPath.exists(): continue
                    bitmap = Image.Load(srcPath, quality=bass.settings[
                        'bash.screens.jpgQuality'])
                    result = bitmap.SaveFile(destPath.s,self.imageType)
                    if not result: continue
                    srcPath.remove()
        finally:
            bosh.screen_infos.refresh()
            self.window.RefreshUI()

#------------------------------------------------------------------------------
class Screens_JpgQuality(RadioLink):
    """Sets JPEG quality for saving."""
    _help = _(u'Sets JPEG quality for saving')

    def __init__(self, quality):
        super(Screens_JpgQuality, self).__init__()
        self.quality = quality
        self._text = u'%i' % self.quality

    def _check(self):
        return self.quality == bass.settings['bash.screens.jpgQuality']

    def Execute(self):
        bass.settings['bash.screens.jpgQuality'] = self.quality

#------------------------------------------------------------------------------
class Screens_JpgQualityCustom(Screens_JpgQuality):
    """Sets a custom JPG quality."""
    def __init__(self):
        super(Screens_JpgQualityCustom, self).__init__(
            bass.settings['bash.screens.jpgCustomQuality'])
        self._text = _(u'Custom [%i]') % self.quality

    def Execute(self):
        quality = self._askNumber(_(u'JPEG Quality'), value=self.quality,
                                  min=0, max=100)
        if quality is None: return
        self.quality = quality
        bass.settings['bash.screens.jpgCustomQuality'] = self.quality
        self._text = _(u'Custom [%i]') % quality
        super(Screens_JpgQualityCustom, self).Execute()

#------------------------------------------------------------------------------
class Screen_Rename(UIList_Rename):
    """Renames files by pattern."""
    _help = _(u'Renames files by pattern')

# People Links ----------------------------------------------------------------
#------------------------------------------------------------------------------
class People_AddNew(ItemLink, People_Link):
    """Add a new record."""
    dialogTitle = _(u'Add New Person')
    _text = _(u'Add...')
    _help = _(u'Add a new record')

    def Execute(self):
        person = self._askText(_(u"Add new person:"), self.dialogTitle)
        if not person: return
        if person in self.pdata: return self._showInfo(
            person + _(u" already exists."), title=self.dialogTitle)
        self.pdata[person] = (time.time(),0,u'')
        self.window.RefreshUI(redraw=[person])
        self.window.EnsureVisibleItem(person, focus=True)
        self.pdata.setChanged()

#------------------------------------------------------------------------------
class People_Export(ItemLink, People_Link):
    """Export people to text archive."""
    dialogTitle = _(u"Export People")
    _text = _(u'Export...')
    _help = _(u'Export people to text archive')

    def Execute(self):
        textDir = bass.settings.get('bash.workDir', bass.dirs['app'])
        #--File dialog
        export_path = self._askSave(title=_(u'Export people to text file:'),
                             defaultDir=textDir, defaultFile=u'People.txt',
                             wildcard=u'*.txt')
        if not export_path: return
        bass.settings['bash.workDir'] = export_path.head
        self.pdata.dumpText(export_path, self.selected)
        self._showInfo(_(u'Records exported: %d.') % len(self.selected),
                       title=self.dialogTitle)

#------------------------------------------------------------------------------
class People_Import(ItemLink, People_Link):
    """Import people from text archive."""
    dialogTitle = _(u"Import People")
    _text = _(u'Import...')
    _help = _(u'Import people from text archive')

    def Execute(self):
        textDir = bass.settings.get('bash.workDir', bass.dirs['app'])
        #--File dialog
        import_path = self._askOpen(title=_(u'Import people from text file:'),
                                    defaultDir=textDir, wildcard=u'*.txt',
                                    mustExist=True)
        if not import_path: return
        bass.settings['bash.workDir'] = import_path.head
        newNames = self.pdata.loadText(import_path)
        self._showInfo(_(u"People imported: %d") % len(newNames),
                       title=self.dialogTitle)
        self.window.RefreshUI()

#------------------------------------------------------------------------------
class People_Karma(ChoiceMenuLink, People_Link):
    """Add Karma setting links."""
    _text = _(u'Karma')
    karma_labels = [u'%+d' % x for x in xrange(5, -6, -1)]

    class _Karma(ItemLink, People_Link):
        def Execute(self):
            karma = int(self._text)
            for item in self.selected:
                self.pdata[item] = (time.time(), karma, self.pdata[item][2])
            self.window.RefreshUI()
            self.pdata.setChanged()

    choiceLinkType = _Karma

    @property
    def _choices(self): return self.__class__.karma_labels

# Masters Links ---------------------------------------------------------------
#------------------------------------------------------------------------------
class Master_AllowEdit(CheckLink, EnabledLink):
    _text, _help = _(u'Allow edit'), _(u'Allow editing the masters list')

    def _enable(self): return self.window.panel.detailsPanel.allowDetailsEdit
    def _check(self): return self.window.allowEdit
    def Execute(self): self.window.allowEdit ^= True

class Master_ClearRenames(ItemLink):
    _text = _(u'Clear Renames')
    _help = _(u'Clear internal Bash renames dictionary')

    def Execute(self):
        bass.settings['bash.mods.renames'].clear()
        self.window.RefreshUI()

class _Master_EditList(OneItemLink): # one item cause _singleSelect = True

    def _enable(self): return self.window.allowEdit

    @property
    def menu_help(self):
        if not self._enable(): return self.__class__._help + u'.  ' + _(
                u'You must first allow editing from the column menu')
        else: return self.__class__._help

class Master_ChangeTo(_Master_EditList):
    """Rename/replace master through file dialog."""
    _text = _(u"Change to...")
    _help = _(u"Rename/replace master through file dialog")

    @balt.conversation
    def Execute(self):
        masterInfo = self._selected_info
        master_name = masterInfo.curr_name
        #--File Dialog
        wildcard = bosh.modInfos.plugin_wildcard()
        newPath = self._askOpen(title=_(u'Change master name to:'),
                                defaultDir=bosh.modInfos.store_dir,
                                defaultFile=master_name, wildcard=wildcard,
                                mustExist=True)
        if not newPath: return
        (newDir,newName) = newPath.headTail
        #--Valid directory?
        if newDir != bosh.modInfos.store_dir:
            self._showError(_(u"File must be selected from "
                u"%s Data Files directory." % bush.game.displayName))
            return
        elif newName == master_name:
            return
        #--Save Name
        masterInfo.set_name(newName)
        bass.settings.getChanged('bash.mods.renames')[master_name] = newName
        self.window.SetMasterlistEdited(repopulate=True)

#------------------------------------------------------------------------------
class Master_Disable(AppendableLink, _Master_EditList):
    """Rename/replace master through file dialog."""
    _text = _(u"Disable")
    _help = _(u"Disable master")

    def _append(self, window): #--Saves only
        return isinstance(window.detailsPanel, SaveDetails)

    def Execute(self):
        masterInfo = self._selected_info
        newName = GPath(re.sub(u'[mM]$', 'p', u'XX' + masterInfo.curr_name.s))
        #--Save Name
        masterInfo.set_name(newName)
        self.window.SetMasterlistEdited(repopulate=True)

# Column menu -----------------------------------------------------------------
#------------------------------------------------------------------------------
class _Column(CheckLink, EnabledLink):

    def __init__(self, _text='COLKEY'):
        """:param _text: not the link _text in this case, the key to the text
        """
        super(_Column, self).__init__()
        self.colName = _text
        self._text = bass.settings['bash.colNames'][_text]
        self._help = _(u"Show/Hide '%(colname)s' column.") % {
            'colname': self._text}

    def _enable(self):
        return self.colName not in self.window.persistent_columns

    def _check(self): return self.colName in self.window.cols

    def Execute(self):
        if self.colName in self.window.cols:
            self.window.cols.remove(self.colName)
        else:
            #--Ensure the same order each time
            cols = self.window.cols[:]
            del self.window.cols[:]
            self.window.cols.extend([x for x in self.window.allCols if
                                     x in cols or x == self.colName])
        self.window.PopulateColumns()
        self.window.RefreshUI()

class ColumnsMenu(ChoiceMenuLink):
    """Customize visible columns."""
    _text = _(u'Columns')
    choiceLinkType = _Column

    class _AutoWidth(RadioLink):
        wxFlag = 0
        def _check(self): return self.wxFlag == self.window.autoColWidths
        def Execute(self):
            self.window.autoColWidths = self.wxFlag
            self.window.autosizeColumns()

    class _Manual(_AutoWidth):
        _text = _(u'Manual')
        _help = _(
            u'Allow to manually resize columns. Applies to all Bash lists')

    class _Contents(_AutoWidth):
        _text, wxFlag = _(u'Fit Contents'), 1 # wx.LIST_AUTOSIZE
        _help = _(u'Fit columns to their content. Applies to all Bash lists.'
                 u' You can hit Ctrl + Numpad+ to the same effect')

    class _Header(_AutoWidth):
        _text, wxFlag = _(u'Fit Header'), 2 # wx.LIST_AUTOSIZE_USEHEADER
        _help = _(u'Fit columns to their content, keep header always visible. '
                 u' Applies to all Bash lists')

    extraItems = [_Manual(), _Contents(), _Header(), SeparatorLink()]

    @property
    def _choices(self): return self.window.allCols

# Sort By menu ----------------------------------------------------------------
#------------------------------------------------------------------------------
class _SortBy(RadioLink):
    """Sort files by specified key (sortCol)."""
    def __init__(self, _text='COLNAME'):
        super(_SortBy, self).__init__()
        self.sortCol = _text
        self._text = bass.settings['bash.colNames'][_text]
        self._help = _(u'Sort by %s') % self._text

    def _check(self): return self.window.sort_column == self.sortCol

    def Execute(self): self.window.SortItems(self.sortCol, 'INVERT')

class SortByMenu(ChoiceMenuLink):
    """Link-based interface to decide what to sort the list by."""
    _text = _(u'Sort by')
    choiceLinkType = _SortBy

    def __init__(self, sort_options=None):
        """Creates a new 'sort by' menu, optionally prepending the specified
        sort options before the choices. A separator is automatically inserted
        if any sort options are specified.

        :type sort_options: list[balt.Link]"""
        super(SortByMenu, self).__init__()
        if sort_options:
            self.extraItems = sort_options + [SeparatorLink()]

    @property
    def _choices(self): return self.window.allCols
