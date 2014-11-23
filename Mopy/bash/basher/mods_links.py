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
from . import CheckLink, BoolLink, Mod_BaloGroups_Edit, bashBlue, \
    bashFrameSetTitle
from .. import bosh, bolt, balt, bass
import locale
import sys
from ..balt import _Link
from ..bolt import deprint, GPath

modList = None

class Mods_EsmsFirst(CheckLink):
    """Sort esms to the top."""
    help = _(u'Sort masters by type')

    def __init__(self,prefix=u''):
        CheckLink.__init__(self)
        self.prefix = prefix
        self.text = self.prefix + _(u'Type')

    def _check(self): return self.window.esmsFirst

    def Execute(self,event):
        self.window.esmsFirst = not self.window.esmsFirst
        self.window.PopulateItems()

#------------------------------------------------------------------------------
class Mods_SelectedFirst(CheckLink):
    """Sort loaded mods to the top."""
    help = _(u'Sort loaded mods to the top')

    def __init__(self,prefix=u''):
        CheckLink.__init__(self)
        self.prefix = prefix
        self.text = self.prefix + _(u'Selection')

    def _check(self): return self.window.selectedFirst

    def Execute(self,event):
        self.window.selectedFirst = not self.window.selectedFirst
        self.window.PopulateItems()

#------------------------------------------------------------------------------
class Mods_ScanDirty(BoolLink):
    """Read mod CRC's to check for dirty mods."""
    text = _(u"Check mods against BOSS's dirty mod list")
    key = 'bash.mods.scanDirty'

    def Execute(self,event):
        BoolLink.Execute(self,event)
        self.window.PopulateItems()

#------------------------------------------------------------------------------
class Mods_AutoGhost(BoolLink):
    """Toggle Auto-ghosting."""
    text, key = _(u'Auto-Ghost'), 'bash.mods.autoGhost'

    def Execute(self,event):
        BoolLink.Execute(self,event)
        files = bosh.modInfos.autoGhost(True)
        self.window.RefreshUI(files)

#------------------------------------------------------------------------------
class Mods_AutoGroup(BoolLink):
    """Turn on autogrouping."""
    text = _(u'Auto Group (Deprecated -- Please use BOSS instead)')
    key = 'bash.balo.autoGroup'

    def Execute(self,event):
        BoolLink.Execute(self,event)
        bosh.modInfos.updateAutoGroups()

#------------------------------------------------------------------------------
class Mods_Deprint(CheckLink):
    """Turn on deprint/delist."""
    text = _(u'Debug Mode')
    help = _(u"Turns on extra debug prints to help debug an error or just for "
             u"advanced testing.")

    def _check(self): return bolt.deprintOn

    def Execute(self,event):
        deprint(_(u'Debug Printing: Off'))
        bolt.deprintOn = not bolt.deprintOn
        deprint(_(u'Debug Printing: On'))

#------------------------------------------------------------------------------
class Mods_FullBalo(BoolLink):
    """Turn Full Balo off/on."""
    text = _(u'Full Balo (Deprecated -- Please use BOSS instead)')
    key = 'bash.balo.full'

    def Execute(self,event):
        if not bosh.settings[self.key]:
            message = (_(u'Activate Full Balo?')
                       + u'\n\n' +
                       _(u'Full Balo segregates mods by groups, and then autosorts mods within those groups by alphabetical order.  Full Balo is still in development and may have some rough edges.')
                       )
            if balt.askContinue(self.window,message,'bash.balo.full.continue',_(u'Balo Groups')):
                dialog = Mod_BaloGroups_Edit(self.window)
                dialog.ShowModal()
                dialog.Destroy()
            return
        else:
            bosh.settings[self.key] = False
            bosh.modInfos.fullBalo = False
            bosh.modInfos.refresh(doInfos=False)

#------------------------------------------------------------------------------
class Mods_DumpTranslator(_Link):
    """Dumps new translation key file using existing key, value pairs."""
    text = _(u'Dump Translator')
    help = _(u"Generate a new version of the translator file for your locale.")

    def AppendToMenu(self,menu,window,data):
        if not hasattr(sys,'frozen'):
            # Can't dump the strings if the files don't exist.
            _Link.AppendToMenu(self,menu,window,data)

    def Execute(self,event):
        message = (_(u'Generate Bash program translator file?')
                   + u'\n\n' +
                   _(u'This function is for translating Bash itself (NOT mods) into non-English languages.  For more info, see Internationalization section of Bash readme.')
                   )
        if not balt.askContinue(self.window,message,'bash.dumpTranslator.continue',_(u'Dump Translator')):
            return
        language = bass.language if bass.language else locale.getlocale()[0].split('_',1)[0]
        outPath = bosh.dirs['l10n']
        bashPath = GPath(u'bash')
        # FIXME no more basher below
        files = [bashPath.join(x+u'.py').s for x in (u'bolt',
                                                     u'balt',
                                                     u'bush',
                                                     u'bosh',
                                                     u'bash',
                                                     u'basher',
                                                     u'bashmon',
                                                     u'belt',
                                                     u'bish',
                                                     u'barg',
                                                     u'barb',
                                                     u'bass',
                                                     u'cint',
                                                     u'ScriptParser')]
        # Include Game files
        bashPath = bashPath.join(u'game')
        files.extend([bashPath.join(x).s for x in bosh.dirs['mopy'].join(u'bash','game').list() if x.cext == u'.py' and x != u'__init__.py'])
        with balt.BusyCursor():
            outFile = bolt.dumpTranslator(outPath.s,language,*files)
        balt.showOk(self.window,
            _(u'Translation keys written to ')+u'Mopy\\bash\\l10n\\'+outFile,
            _(u'Dump Translator')+u': '+outPath.stail)

#------------------------------------------------------------------------------
class Mods_ListMods(_Link):
    """Copies list of mod files to clipboard."""
    text = _(u"List Mods...")
    help = _(u"Copies list of active mod files to clipboard.")

    def Execute(self,event):
        #--Get masters list
        text = bosh.modInfos.getModList(showCRC=balt.getKeyState(67))
        balt.copyToClipboard(text)
        balt.showLog(self.window,text,_(u"Active Mod Files"),asDialog=False,fixedFont=False,icons=bashBlue)

#------------------------------------------------------------------------------
class Mods_ListBashTags(_Link):
    """Copies list of bash tags to clipboard."""
    text = _(u"List Bash Tags...")
    help = _(u"Copies list of bash tags to clipboard.")

    def Execute(self,event):
        #--Get masters list
        text = bosh.modInfos.getTagList()
        balt.copyToClipboard(text)
        balt.showLog(self.window,text,_(u"Bash Tags"),asDialog=False,fixedFont=False,icons=bashBlue)

#------------------------------------------------------------------------------
class Mods_LockTimes(CheckLink):
    """Turn on resetMTimes feature."""
    text = _(u'Lock Load Order')
    help = _(u"Will reset mod Load Order to whatever Wrye Bash has saved for"
             u" them whenever Wrye Bash refreshes data/starts up.")

    def _check(self): return bosh.modInfos.lockLO

    def Execute(self,event):
        lockLO = not bosh.modInfos.lockLO
        if not lockLO: bosh.modInfos.mtimes.clear()
        bosh.settings['bosh.modInfos.resetMTimes'] = bosh.modInfos.lockLO = lockLO
        bosh.modInfos.refresh(doInfos=False)
        modList.RefreshUI()

#------------------------------------------------------------------------------
class Mods_OblivionVersion(CheckLink):
    """Specify/set Oblivion version."""
    help = _(u'Specify/set Oblivion version')

    def __init__(self,key,setProfile=False):
        CheckLink.__init__(self)
        self.key = self.text = key
        self.setProfile = setProfile

    def AppendToMenu(self,menu,window,data): # TODO(ut): MI with enabled
        menuItem = CheckLink.AppendToMenu(self,menu,window,data)
        menuItem.Enable(bosh.modInfos.voCurrent is not None and self.key in bosh.modInfos.voAvailable)
        if bosh.modInfos.voCurrent == self.key: menuItem.Check()

    def Execute(self,event):
        """Handle selection."""
        if bosh.modInfos.voCurrent == self.key: return
        bosh.modInfos.setOblivionVersion(self.key)
        bosh.modInfos.refresh()
        modList.RefreshUI()
        if self.setProfile:
            bosh.saveInfos.profiles.setItem(bosh.saveInfos.localSave,'vOblivion',self.key)
        bashFrameSetTitle()

#------------------------------------------------------------------------------
class Mods_Tes4ViewExpert(BoolLink):
    """Toggle Tes4Edit expert mode (when launched via Bash)."""
    text, key = _(u'Tes4Edit Expert'), 'tes4View.iKnowWhatImDoing'

#------------------------------------------------------------------------------
class Mods_Tes5ViewExpert(BoolLink):
    """Toggle Tes5Edit expert mode (when launched via Bash)."""
    text, key = _(u'Tes5Edit Expert'), 'tes5View.iKnowWhatImDoing'

#------------------------------------------------------------------------------
class Mods_BOSSDisableLockTimes(BoolLink):
    """Toggle Lock Load Order disabling when launching BOSS through Bash."""
    text = _(u'BOSS Disable Lock Load Order')
    key = 'BOSS.ClearLockTimes'
    help = _(u"If selected, will temporarily disable Bash's Lock Load Order"
             u" when running BOSS through Bash.")

#------------------------------------------------------------------------------
class Mods_BOSSLaunchGUI(BoolLink):
    """If BOSS.exe is available then BOSS GUI.exe should be too."""
    text, key, help = _(u'Launch using GUI'), 'BOSS.UseGUI', \
                      _(u"If selected, Bash will run BOSS's GUI.")
