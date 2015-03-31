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

"""Menu items for the main and item menus of the ini tweaks tab - their window
attribute points to BashFrame.iniList singleton.
"""

from .. import bosh, balt, bush
from ..bass import Resources
from ..balt import ItemLink, BoolLink, EnabledLink, OneItemLink

__all__ = ['INI_SortValid', 'INI_AllowNewLines', 'INI_ListINIs', 'INI_Apply',
           'INI_CreateNew', 'INI_ListErrors', 'INI_FileOpenOrCopy',
           'INI_Delete']

class INI_SortValid(BoolLink):
    """Sort valid INI Tweaks to the top."""
    text, key, help = _(u'Valid Tweaks First'), 'bash.ini.sortValid', \
                      _(u'Valid tweak files will be shown first.')

    def Execute(self,event):
        BoolLink.Execute(self,event)
        self.window.SortItems()

#------------------------------------------------------------------------------
class INI_AllowNewLines(BoolLink):
    """Consider INI Tweaks with new lines valid."""
    text = _(u'Allow Tweaks with New Lines')
    key = 'bash.ini.allowNewLines'
    help = _(u'Tweak files with new lines are considered valid..')

    def Execute(self,event):
        BoolLink.Execute(self,event)
        self.window.RefreshUI()

#------------------------------------------------------------------------------
class INI_ListINIs(ItemLink):
    """List errors that make an INI Tweak invalid."""
    text = _(u'List Active INIs...')
    help = _(u'Lists all fully applied tweak files.')

    def Execute(self,event):
        """Handle printing out the errors."""
        text = self.window.ListTweaks()
        balt.copyToClipboard(text)
        self._showLog(text, title=_(u'Active INIs'), fixedFont=False,
                      icons=Resources.bashBlue)

#------------------------------------------------------------------------------
class INI_ListErrors(EnabledLink):
    """List errors that make an INI Tweak invalid."""
    text = _(u'List Errors...')
    help = _(u'Lists any errors in the tweak file causing it to be invalid.')

    def _enable(self):
        for i in self.selected:
            if bosh.iniInfos[i].getStatus() < 0:
                return True
        return False

    def Execute(self,event):
        """Handle printing out the errors."""
        text = u''
        for i in self.selected:
            fileInfo = bosh.iniInfos[i]
            text += u'%s\n' % fileInfo.listErrors()
        balt.copyToClipboard(text)
        self._showLog(text, title=_(u'INI Tweak Errors'), fixedFont=False,
                      icons=Resources.bashBlue)

#------------------------------------------------------------------------------
class INI_FileOpenOrCopy(OneItemLink):
    """Open specified file(s) only if they aren't Bash supplied defaults."""
    def _initData(self, window, selection):
        super(INI_FileOpenOrCopy, self)._initData(window, selection)
        if not len(selection) == 1:
            self.text = _(u'Open/Copy...')
            self.help = _(u'Only one INI file can be opened or copied at a time.')
        elif bosh.dirs['tweaks'].join(selection[0]).isfile():
            self.text = _(u'Open...')
            self.help = _(u"Open '%s' with the system's default program.") % selection[0]
        else:
            self.text = _(u'Copy...')
            self.help = _(u"Make an editable copy of the default tweak '%s'.") % selection[0]

    def Execute(self,event):
        """Handle selection."""
        dir = self.window.data.dir
        for file in self.selected:
            if bosh.dirs['tweaks'].join(file).isfile():
                dir.join(file).start()
            else:
                srcFile = bosh.iniInfos[file].dir.join(file)
                destFile = bosh.dirs['tweaks'].join(file)
                balt.shellMakeDirs(bosh.dirs['tweaks'],self.window)
                balt.shellCopy(srcFile,destFile,self.window,False,False,False)
                self.window.data.refresh()
                self.window.RefreshUI()

#------------------------------------------------------------------------------
class INI_Delete(balt.UIList_Delete, EnabledLink):
    """Delete the file and all backups."""

    def _initData(self, window, selection):
        super(INI_Delete, self)._initData(window, selection)
        self.selected = self.window.filterOutDefaultTweaks(self.selected)
        if len(self.selected) and len(selection) == 1:
            self.help = _(u"Delete %(filename)s.") % ({'filename': selection[0]})
        elif len(self.selected):
            self.help = _(
                u"Delete selected tweaks (default tweaks won't be deleted)")
        else: self.help = _(u"Bash default tweaks can't be deleted")

    def _enable(self): return len(self.selected) > 0

#------------------------------------------------------------------------------
class INI_Apply(EnabledLink):
    """Apply an INI Tweak."""
    text = _(u'Apply')

    def _initData(self, window, selection):
        super(INI_Apply, self)._initData(window, selection)
        self.iniPanel = self.window.panel
        ini = self.iniPanel.comboBox.GetValue()
        if len(selection) == 1:
            tweak = selection[0]
            self.help = _(u"Applies '%(tweak)s' to '%(ini)s'.") % {
                'tweak': tweak, 'ini': ini}
        else:
            self.help = _(u"Applies selected tweaks to '%(ini)s'.") % {
            'ini': ini}

    def _enable(self):
        if not bosh.settings['bash.ini.allowNewLines']:
            for i in self.selected:
                iniInfo = bosh.iniInfos[i]
                if iniInfo.status < 0:
                    return False # temp disabled for testing
        return True

    def Execute(self,event):
        """Handle applying INI Tweaks."""
        #-- If we're applying to Oblivion.ini, show the warning
        iniPanel = self.iniPanel
        choice = iniPanel.GetChoice().tail
        if choice in bush.game.iniFiles:
            message = (_(u'Apply an ini tweak to %s?') % choice
                       + u'\n\n' +
                       _(u'WARNING: Incorrect tweaks can result in CTDs and even damage to your computer!')
                       )
            if not self._askContinue(message, 'bash.iniTweaks.continue',
                                     _(u'INI Tweaks')): return
        needsRefresh = False
        for item in self.selected:
            #--No point applying a tweak that's already applied
            if bosh.iniInfos[item].status == 20: continue
            needsRefresh = True
            if bosh.dirs['tweaks'].join(item).isfile():
                self.window.data.ini.applyTweakFile(bosh.dirs['tweaks'].join(item))
            else:
                self.window.data.ini.applyTweakFile(bosh.dirs['defaultTweaks'].join(item))
        if needsRefresh:
            #--Refresh status of all the tweaks valid for this ini
            self.window.RefreshUIValid()
            iniPanel.iniContents.RefreshIniContents()
            iniPanel.tweakContents.RefreshTweakLineCtrl(self.selected[0])

#------------------------------------------------------------------------------
class INI_CreateNew(OneItemLink):
    """Create a new INI Tweak using the settings from the tweak file,
    but values from the target INI."""
    text = _(u'Create Tweak with current settings...')

    def _initData(self, window, selection):
        super(INI_CreateNew, self)._initData(window, selection)
        ini = self.window.panel.comboBox.GetValue()
        if not len(selection) == 1:
            self.help = _(u'Please choose one Ini Tweak')
        else:
            self.help = _(
                u"Creates a new tweak based on '%(tweak)s' but with values "
                u"from '%(ini)s'.") % {'tweak': (selection[0]), 'ini': ini}

    def _enable(self): return super(INI_CreateNew, self)._enable() and \
                              bosh.iniInfos[self.selected[0]].status >= 0

    def Execute(self,event):
        """Handle creating a new INI tweak."""
        pathFrom = self.selected[0]
        fileName = pathFrom.sbody + u' - Copy' + pathFrom.ext
        path = self._askSave(title=_(u'Copy Tweak with current settings...'),
                             defaultDir=bosh.dirs['tweaks'],
                             defaultFile=fileName,
                             wildcard=_(u'INI Tweak File (*.ini)|*.ini'))
        if not path: return
        bosh.iniInfos[pathFrom].dir.join(pathFrom).copyTo(path)
        # Now edit it with the values from the target INI
        self.window.data.refresh()
        oldTarget = self.window.data.ini
        target = bosh.BestIniFile(path)
        settings,deleted = target.getSettings()
        new_settings,deleted = oldTarget.getSettings()
        deleted = {}
        for section in settings:
            if section in new_settings:
                for setting in settings[section]:
                    if setting in new_settings[section]:
                        settings[section][setting] = new_settings[section][
                            setting]
        target.saveSettings(settings)
        self.window.RefreshUI()
        self.window.SelectItem(path.tail)
