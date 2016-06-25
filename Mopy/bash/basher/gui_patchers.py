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

import string
import wx
from .. import bass, bosh, bush, balt
from ..balt import fill, StaticText, vSizer, checkBox, Button, hsbSizer, Links, \
    SeparatorLink, CheckLink, Link, vspace
from ..bolt import GPath

class _PatcherPanel(object):
    """Basic patcher panel with no options."""
    def SetCallbackFns(self,checkPatcherFn,boldPatcherFn):
        self._checkPatcherFn = checkPatcherFn
        self._boldPatcherFn = boldPatcherFn

    def SetIsFirstLoad(self,isFirstLoad):
        self._isFirstLoad = isFirstLoad

    def _EnsurePatcherEnabled(self):
        if hasattr(self, '_checkPatcherFn'):
            self._checkPatcherFn(self)

    def _BoldPatcherLabel(self):
        if hasattr(self, '_boldPatcherFn'):
            self._boldPatcherFn(self)

    def _GetIsFirstLoad(self):
        if hasattr(self, '_isFirstLoad'):
            return self._isFirstLoad
        else:
            return False

    def GetConfigPanel(self,parent,gConfigSizer,gTipText):
        """Show config."""
        if not self.gConfigPanel:
            self.gTipText = gTipText
            gConfigPanel = self.gConfigPanel = wx.Window(parent)
            text = fill(self.text,70)
            gText = StaticText(self.gConfigPanel,text)
            gSizer = vSizer(gText)
            gConfigPanel.SetSizer(gSizer)
            gConfigSizer.Add(gConfigPanel,1,wx.EXPAND)
        return self.gConfigPanel

    def Layout(self):
        """Layout control components."""
        if self.gConfigPanel:
            self.gConfigPanel.Layout()

#------------------------------------------------------------------------------
class _AliasesPatcherPanel(_PatcherPanel):
    def GetConfigPanel(self,parent,gConfigSizer,gTipText):
        """Show config."""
        if self.gConfigPanel: return self.gConfigPanel
        #--Else...
        #--Tip
        self.gTipText = gTipText
        gConfigPanel = self.gConfigPanel = wx.Window(parent)
        # CRUFT (ut) PBASH -> CBASH difference - kept PBash:
        # -        text = fill(self.__class__.text,70)
        # +        text = fill(self.text,70)
        text = fill(self.text,70)
        gText = StaticText(gConfigPanel,text)
        #gExample = StaticText(gConfigPanel,
        #    _(u"Example Mod 1.esp >> Example Mod 1.2.esp"))
        #--Aliases Text
        self.gAliases = balt.TextCtrl(gConfigPanel, multiline=True,
                                      onKillFocus=self.OnEditAliases)
        self.SetAliasText()
        #--Sizing
        gSizer = vSizer(
            gText,
            #(gExample,0,wx.EXPAND|wx.TOP,8),
            vspace(), (self.gAliases, 1, wx.EXPAND))
        gConfigPanel.SetSizer(gSizer)
        gConfigSizer.Add(gConfigPanel,1,wx.EXPAND)
        return self.gConfigPanel

    def SetAliasText(self):
        """Sets alias text according to current aliases."""
        self.gAliases.SetValue(u'\n'.join([
            u'%s >> %s' % (key.s,value.s) for key,value in sorted(self.aliases.items())]))

    def OnEditAliases(self):
        text = self.gAliases.GetValue()
        self.aliases.clear()
        for line in text.split(u'\n'):
            fields = map(string.strip,line.split(u'>>'))
            if len(fields) != 2 or not fields[0] or not fields[1]: continue
            self.aliases[GPath(fields[0])] = GPath(fields[1])
        self.SetAliasText()

#------------------------------------------------------------------------------
class _ListPatcherPanel(_PatcherPanel):
    """Patcher panel with option to select source elements."""
    listLabel = _(u'Source Mods/Files')

    def GetConfigPanel(self,parent,gConfigSizer,gTipText):
        """Show config."""
        if self.gConfigPanel: return self.gConfigPanel
        #--Else...
        self.forceItemCheck = self.__class__.forceItemCheck
        self.selectCommands = self.__class__.selectCommands
        self.gTipText = gTipText
        gConfigPanel = self.gConfigPanel = wx.Window(parent)
        text = fill(self.text,70)
        gText = StaticText(self.gConfigPanel,text)
        if self.forceItemCheck:
            self.gList = balt.listBox(gConfigPanel, isSingle=False)
        else:
            self.gList = balt.listBox(gConfigPanel, kind='checklist')
            self.gList.Bind(wx.EVT_CHECKLISTBOX,self.OnListCheck)
        #--Events
        self.gList.Bind(wx.EVT_MOTION,self.OnMouse)
        self.gList.Bind(wx.EVT_RIGHT_DOWN,self.OnMouse)
        self.gList.Bind(wx.EVT_RIGHT_UP,self.OnMouse)
        self.mouse_dex = -1
        self.mouse_pos = None
        #--Manual controls
        if self.forceAuto:
            gManualSizer = None
            self.SetItems(self.getAutoItems())
        else:
            self.gAuto = checkBox(gConfigPanel, _(u'Automatic'),
                                  onCheck=self.OnAutomatic,
                                  checked=self.autoIsChecked)
            self.gAdd = Button(gConfigPanel, _(u'Add'), onButClick=self.OnAdd)
            self.gRemove = Button(gConfigPanel, _(u'Remove'),
                                  onButClick=self.OnRemove)
            self.OnAutomatic()
            gManualSizer = (vSizer(
                vspace(2), self.gAuto,
                vspace(12), self.gAdd,
                vspace(4), self.gRemove,
                ),0,wx.EXPAND|wx.LEFT,4)
        if self.selectCommands:
            self.gSelectAll = Button(gConfigPanel, _(u'Select All'),
                                     onButClick=self.SelectAll)
            self.gDeselectAll = Button(gConfigPanel, _(u'Deselect All'),
                                       onButClick=self.DeselectAll)
            gSelectSizer = (vSizer(
                vspace(12), self.gSelectAll,
                vspace(4), self.gDeselectAll,
                ),0,wx.EXPAND|wx.LEFT,4)
        else: gSelectSizer = None
        #--Layout
        gSizer = vSizer(
            (gText,), vspace(),
            (balt.hsbSizer((gConfigPanel,wx.ID_ANY,self.__class__.listLabel),
                ((4,0),0,wx.EXPAND),
                (self.gList,1,wx.EXPAND|wx.TOP,2),
                gManualSizer,gSelectSizer,
                ),1,wx.EXPAND),
            )
        gConfigPanel.SetSizer(gSizer)
        gConfigSizer.Add(gConfigPanel,1,wx.EXPAND)
        return gConfigPanel

    def SetItems(self,items):
        """Set item to specified set of items."""
        items = self.items = self.sortConfig(items)
        forceItemCheck = self.forceItemCheck
        defaultItemCheck = self.__class__.canAutoItemCheck and bass.inisettings['AutoItemCheck']
        self.gList.Clear()
        isFirstLoad = self._GetIsFirstLoad()
        patcherOn = False
        patcherBold = False
        for index,item in enumerate(items):
            itemLabel = self.getItemLabel(item)
            self.gList.Insert(itemLabel,index)
            if forceItemCheck:
                if self.configChecks.get(item) is None:
                    patcherOn = True
                self.configChecks[item] = True
            else:
                effectiveDefaultItemCheck = defaultItemCheck and not itemLabel.endswith(u'.csv')
                if self.configChecks.get(item) is None:
                    if effectiveDefaultItemCheck:
                        patcherOn = True
                    if not isFirstLoad:
                        # indicate that this is a new item by bolding it and its parent patcher
                        font = self.gConfigPanel.GetFont()
                        font.SetWeight(wx.FONTWEIGHT_BOLD)
                        self.gList.SetItemFont(index, font)
                        patcherBold = True
                self.gList.Check(index,self.configChecks.setdefault(item,effectiveDefaultItemCheck))
        self.configItems = items
        if patcherOn:
            self._EnsurePatcherEnabled()
        if patcherBold:
            self._BoldPatcherLabel()

    def OnListCheck(self,event=None):
        """One of list items was checked. Update all configChecks states."""
        ensureEnabled = False
        for index,item in enumerate(self.items):
            checked = self.gList.IsChecked(index)
            self.configChecks[item] = checked
            if checked:
                ensureEnabled = True
        if event is not None:
            if self.gList.IsChecked(event.GetSelection()):
                self._EnsurePatcherEnabled()
        elif ensureEnabled:
            self._EnsurePatcherEnabled()

    def OnAutomatic(self):
        """Automatic checkbox changed."""
        self.autoIsChecked = self.gAuto.IsChecked()
        self.gAdd.Enable(not self.autoIsChecked)
        self.gRemove.Enable(not self.autoIsChecked)
        if self.autoIsChecked:
            self.SetItems(self.getAutoItems())

    def OnAdd(self):
        """Add button clicked."""
        srcDir = bosh.modInfos.dir
        wildcard = bush.game.displayName+_(u' Mod Files')+u' (*.esp;*.esm)|*.esp;*.esm'
        #--File dialog
        title = _(u'Get ')+self.__class__.listLabel
        srcPaths = balt.askOpenMulti(self.gConfigPanel,title,srcDir, u'', wildcard)
        if not srcPaths: return
        #--Get new items
        for srcPath in srcPaths:
            dir,name = srcPath.headTail
            if dir == srcDir and name not in self.configItems:
                self.configItems.append(name)
        self.SetItems(self.configItems)

    def OnRemove(self):
        """Remove button clicked."""
        selections = self.gList.GetSelections()
        newItems = [item for index,item in enumerate(self.configItems) if index not in selections]
        self.SetItems(newItems)

    #--Choice stuff ---------------------------------------
    def OnMouse(self,event):
        """Check mouse motion to detect right click event."""
        if event.RightDown():
            self.mouse_pos = event.GetPosition()
            event.Skip()
        elif event.RightUp() and self.mouse_pos:
            self.ShowChoiceMenu(event)
        elif event.Dragging():
            if self.mouse_pos:
                oldx, oldy = self.mouse_pos
                x, y = event.GetPosition()
                if max(abs(x - oldx), abs(y - oldy)) > 4:
                    self.mouse_pos = None
        else:
            self.mouse_pos = None
            event.Skip()

    def ShowChoiceMenu(self,event):
        """Displays a popup choice menu if applicable.
        NOTE: Assume that configChoice returns a set of chosen items."""
        if not self.choiceMenu: return
        #--Item Index
        itemIndex = self.gList.HitTest(event.GetPosition())
        if itemIndex < 0: return
        self.gList.SetSelection(itemIndex)
        choiceSet = self.getChoice(self.items[itemIndex])
        #--Build Menu
        class _OnItemChoice(CheckLink):
            def __init__(self, _text, index):
                super(_OnItemChoice, self).__init__(_text)
                self.index = index
            def _check(self): return self.text in choiceSet
            def Execute(self): _onItemChoice(self.index)
        def _onItemChoice(dex):
            """Handle choice menu selection."""
            item = self.items[itemIndex]
            choice = self.choiceMenu[dex]
            choiceSet = self.configChoices[item]
            choiceSet ^= {choice}
            if choice != u'Auto':
                choiceSet.discard(u'Auto')
            elif u'Auto' in self.configChoices[item]:
                self.getChoice(item)
            self.gList.SetString(itemIndex, self.getItemLabel(item))
        links = Links()
        for index,label in enumerate(self.choiceMenu):
            if label == u'----':
                links.append(SeparatorLink())
            else:
                links.append(_OnItemChoice(label, index))
        #--Show/Destroy Menu
        links.PopupMenu(self.gList, Link.Frame, None)

    def SelectAll(self):
        """'Select All' Button was pressed, update all configChecks states."""
        try:
            for index, item in enumerate(self.items):
                self.gList.Check(index,True)
            self.OnListCheck()
        except AttributeError:
            pass #ListBox instead of CheckListBox
        self.gConfigPanel.GetParent().gPatchers.SetFocusFromKbd()

    def DeselectAll(self):
        """'Deselect All' Button was pressed, update all configChecks states."""
        try:
            self.gList.SetChecked([])
            self.OnListCheck()
        except AttributeError:
            pass #ListBox instead of CheckListBox
        self.gConfigPanel.GetParent().gPatchers.SetFocusFromKbd()

#------------------------------------------------------------------------------
class _TweakPatcherPanel(_PatcherPanel):
    """Patcher panel with list of checkable, configurable tweaks."""
    listLabel = _(u"Tweaks")
    style = wx.TAB_TRAVERSAL

    def GetConfigPanel(self,parent,gConfigSizer,gTipText):
        """Show config."""
        if self.gConfigPanel: return self.gConfigPanel
        #--Else...
        gConfigPanel, gText = self._build_tweaks_list(gTipText, parent)
        if self.selectCommands:
            self.gSelectAll = Button(gConfigPanel, _(u'Select All'),
                                     onButClick=self.TweakSelectAll)
            self.gDeselectAll = Button(gConfigPanel, _(u'Deselect All'),
                                       onButClick=self.TweakDeselectAll)
            gSelectSizer = (vSizer(
                 vspace(12), self.gSelectAll,
                 vspace(4), self.gDeselectAll,
                ),0,wx.EXPAND|wx.LEFT,4)
        else: gSelectSizer = None
        #--Init GUI
        self.SetTweaks()
        #--Layout
        gSizer = vSizer(
            (gText,), vspace(),
            (hsbSizer((gConfigPanel,wx.ID_ANY,self.__class__.listLabel),
                ((4,0),0,wx.EXPAND),
                (self.gTweakList,1,wx.EXPAND|wx.TOP,2),
                gSelectSizer,
                ),1,wx.EXPAND),
            )
        gConfigPanel.SetSizer(gSizer)
        gConfigSizer.Add(gConfigPanel,1,wx.EXPAND)
        return gConfigPanel

    def _build_tweaks_list(self, gTipText, parent):
        self.gTipText = gTipText
        gConfigPanel = self.gConfigPanel = wx.Window(
            parent, style=self.__class__.style)
        text = fill(self.__class__.text, 70)
        gText = StaticText(self.gConfigPanel, text)
        self.gTweakList = balt.listBox(gConfigPanel, kind='checklist')
        #--Events
        self.gTweakList.Bind(wx.EVT_CHECKLISTBOX, self.TweakOnListCheck)
        self.gTweakList.Bind(wx.EVT_MOTION, self.TweakOnMouse)
        self.gTweakList.Bind(wx.EVT_LEAVE_WINDOW, self.TweakOnMouse)
        self.gTweakList.Bind(wx.EVT_RIGHT_DOWN, self.TweakOnMouse)
        self.gTweakList.Bind(wx.EVT_RIGHT_UP, self.TweakOnMouse)
        self.mouse_dex = -1
        self.mouse_pos = None
        return gConfigPanel, gText

    @staticmethod
    def _label(label, value): # edit label text with value
        formatStr = u' %s' if isinstance(value, basestring) else u' %4.2f '
        return label + formatStr % value

    def SetTweaks(self):
        """Set item to specified set of items."""
        self.gTweakList.Clear()
        isFirstLoad = self._GetIsFirstLoad()
        patcherBold = False
        for index,tweak in enumerate(self.tweaks):
            label = tweak.getListLabel()
            if tweak.choiceLabels and tweak.choiceLabels[tweak.chosen].startswith(u'Custom'):
                label = self._label(label, tweak.choiceValues[tweak.chosen][0])
            self.gTweakList.Insert(label,index)
            self.gTweakList.Check(index,tweak.isEnabled)
            if not isFirstLoad and tweak.isNew():
                # indicate that this is a new item by bolding it and its parent patcher
                font = self.gConfigPanel.GetFont()
                font.SetWeight(wx.FONTWEIGHT_BOLD)
                self.gTweakList.SetItemFont(index, font)
                patcherBold = True
        if patcherBold:
            self._BoldPatcherLabel()

    def TweakOnListCheck(self,event=None):
        """One of list items was checked. Update all check states."""
        ensureEnabled = False
        for index, tweak in enumerate(self.tweaks):
            checked = self.gTweakList.IsChecked(index)
            tweak.isEnabled = checked
            if checked:
                ensureEnabled = True
        if event is not None:
            if self.gTweakList.IsChecked(event.GetSelection()):
                self._EnsurePatcherEnabled()
        elif ensureEnabled:
            self._EnsurePatcherEnabled()

    def TweakOnMouse(self,event):
        """Check mouse motion to detect right click event."""
        if event.RightDown():
            self.mouse_pos = event.GetPosition()
            event.Skip()
        elif event.RightUp() and self.mouse_pos:
            self.ShowChoiceMenu(event)
        elif event.Leaving():
            self.gTipText.SetLabel(u'')
            self.mouse_pos = None
            event.Skip()
        elif event.Dragging():
            if self.mouse_pos:
                oldx, oldy = self.mouse_pos
                x, y = event.GetPosition()
                if max(abs(x - oldx), abs(y - oldy)) > 4:
                    self.mouse_pos = None
        elif event.Moving():
            mouseItem = self.gTweakList.HitTest(event.GetPosition())
            self.mouse_pos = None
            if mouseItem != self.mouse_dex:
                # Show tip text when changing item
                self.mouse_dex = mouseItem
                tip = 0 <= mouseItem < len(self.tweaks) and self.tweaks[
                    mouseItem].tip
                if tip:
                    self.gTipText.SetLabel(tip)
                else:
                    self.gTipText.SetLabel(u'')
            event.Skip()
        else:
            self.mouse_pos = None
            event.Skip()

    def ShowChoiceMenu(self,event):
        """Displays a popup choice menu if applicable."""
        #--Tweak Index
        tweakIndex = self.gTweakList.HitTest(event.GetPosition())
        #--Tweaks
        tweaks = self.tweaks
        if tweakIndex >= len(tweaks): return
        tweak = tweaks[tweakIndex]
        choiceLabels = tweak.choiceLabels
        if len(choiceLabels) <= 1: return
        self.gTweakList.SetSelection(tweakIndex)
        #--Build Menu
        links = Links()
        _self = self # ugly, tweak_custom_choice is too big to make it local though
        class _ValueLink(CheckLink):
            def __init__(self, _text, index):
                super(_ValueLink, self).__init__(_text)
                self.index = index
            def _check(self): return self.index == tweak.chosen
            def Execute(self): _self.tweak_choice(self.index, tweakIndex)
        class _ValueLinkCustom(_ValueLink):
            def Execute(self): _self.tweak_custom_choice(self.index,tweakIndex)
        for index,label in enumerate(choiceLabels):
            if label == u'----':
                links.append(SeparatorLink())
            elif label.startswith(_(u'Custom')):
                label = self._label(label, tweak.choiceValues[index][0])
                links.append(_ValueLinkCustom(label, index))
            else:
                links.append(_ValueLink(label, index))
        #--Show/Destroy Menu
        links.PopupMenu(self.gTweakList, Link.Frame, None)

    def tweak_choice(self, index, tweakIndex):
        """Handle choice menu selection."""
        self.tweaks[tweakIndex].chosen = index
        self.gTweakList.SetString(tweakIndex,self.tweaks[tweakIndex].getListLabel())
        self.gTweakList.Check(tweakIndex, True) # wx.EVT_CHECKLISTBOX is NOT
        self.TweakOnListCheck() # fired so this line is needed (?)

    _msg = _(u'Enter the desired custom tweak value.') + u'\n' + _(
        u'Due to an inability to get decimal numbers from the wxPython '
        u'prompt please enter an extra zero after your choice if it is not '
        u'meant to be a decimal.') + u'\n' + _(
        u'If you are trying to enter a decimal multiply it by 10, '
        u'for example for 0.3 enter 3 instead.')

    def tweak_custom_choice(self, index, tweakIndex):
        """Handle choice menu selection."""
        tweak = self.tweaks[tweakIndex]
        value = []
        for i, v in enumerate(tweak.choiceValues[index]):
            if isinstance(v,float):
                label = self._msg + u'\n' + tweak.key[i]
                new = balt.askNumber(
                    self.gConfigPanel, label, prompt=_(u'Value'),
                    title=tweak.label + _(u' ~ Custom Tweak Value'),
                    value=tweak.choiceValues[index][i], min=-10000, max=10000)
                if new is None: #user hit cancel
                    return
                value.append(float(new)/10)
            elif isinstance(v,int):
                label = _(u'Enter the desired custom tweak value.') + u'\n' + \
                        tweak.key[i]
                new = balt.askNumber(
                    self.gConfigPanel, label, prompt=_(u'Value'),
                    title=tweak.label + _(u' ~ Custom Tweak Value'),
                    value=tweak.choiceValues[index][i], min=-10000, max=10000)
                if new is None: #user hit cancel
                    return
                value.append(new)
            elif isinstance(v,basestring):
                label = _(u'Enter the desired custom tweak text.') + u'\n' + \
                        tweak.key[i]
                new = balt.askText(
                    self.gConfigPanel, label,
                    title=tweak.label + _(u' ~ Custom Tweak Text'),
                    default=tweak.choiceValues[index][i], strip=False) ##: strip ?
                if new is None: #user hit cancel
                    return
                value.append(new)
        if not value: value = tweak.choiceValues[index]
        tweak.choiceValues[index] = tuple(value)
        tweak.chosen = index
        label = self._label(tweak.getListLabel(), tweak.choiceValues[index][0])
        self.gTweakList.SetString(tweakIndex, label)
        self.gTweakList.Check(tweakIndex, True) # wx.EVT_CHECKLISTBOX is NOT
        self.TweakOnListCheck() # fired so this line is needed (?)

    def TweakSelectAll(self):
        """'Select All' Button was pressed, update all configChecks states."""
        try:
            for index, item in enumerate(self.tweaks):
                self.gTweakList.Check(index,True)
            self.TweakOnListCheck()
        except AttributeError:
            pass #ListBox instead of CheckListBox
        self.gConfigPanel.GetParent().gPatchers.SetFocusFromKbd()

    def TweakDeselectAll(self):
        """'Deselect All' Button was pressed, update all configChecks
        states."""
        try:
            self.gTweakList.SetChecked([])
            self.TweakOnListCheck()
        except AttributeError:
            pass #ListBox instead of CheckListBox
        self.gConfigPanel.GetParent().gPatchers.SetFocusFromKbd()

#------------------------------------------------------------------------------
class _DoublePatcherPanel(_TweakPatcherPanel, _ListPatcherPanel):
    """Patcher panel with option to select source elements."""
    listLabel = _(u'Source Mods/Files')
    style = 0

    def GetConfigPanel(self,parent,gConfigSizer,gTipText): # TODO(ut): use super !
        """Show config."""
        if self.gConfigPanel: return self.gConfigPanel
        #--Else...
        gConfigPanel, gText = self._build_tweaks_list(gTipText, parent)
        #--Import List
        self.gList = balt.listBox(gConfigPanel, kind='checklist')
        self.gList.Bind(wx.EVT_MOTION,self.OnMouse)
        self.gList.Bind(wx.EVT_RIGHT_DOWN,self.OnMouse)
        self.gList.Bind(wx.EVT_RIGHT_UP,self.OnMouse)
        #--Buttons
        self.gSelectAll = Button(gConfigPanel, _(u'Select All'),
                                 onButClick=self.SelectAll)
        self.gDeselectAll = Button(gConfigPanel, _(u'Deselect All'),
                                   onButClick=self.DeselectAll)
        gSelectSizer = (vSizer(
             vspace(12), self.gSelectAll,
             vspace(4), self.gDeselectAll,
            ),0,wx.EXPAND|wx.LEFT,4)
        self.gTweakSelectAll = Button(gConfigPanel, _(u'Select All'),
                                      onButClick=self.TweakSelectAll)
        self.gTweakDeselectAll = Button(gConfigPanel, _(u'Deselect All'),
                                        onButClick=self.TweakDeselectAll)
        gTweakSelectSizer = (vSizer(
             vspace(12), self.gTweakSelectAll,
             vspace(4), self.gTweakDeselectAll,
            ),0,wx.EXPAND|wx.LEFT,4)
        #--Layout
        gSizer = vSizer(
            (gText,), vspace(),
            (hsbSizer((gConfigPanel,wx.ID_ANY,self.__class__.listLabel),
                ((4,0),0,wx.EXPAND),
                (self.gList,1,wx.EXPAND|wx.TOP,2),
                gSelectSizer,),1,wx.EXPAND), vspace(),
            (hsbSizer((gConfigPanel,wx.ID_ANY,self.__class__.subLabel),
                ((4,0),0,wx.EXPAND),
                (self.gTweakList,1,wx.EXPAND|wx.TOP,2),
                gTweakSelectSizer,),1,wx.EXPAND),
            )
        gConfigPanel.SetSizer(gSizer)
        gConfigSizer.Add(gConfigPanel,1,wx.EXPAND)
        #--Initialize
        self.SetItems(self.getAutoItems())
        self.SetTweaks()
        return gConfigPanel

#------------------------------------------------------------------------------
# GUI Patcher classes - mixins of patchers and the GUI patchers defined above -
# Do _not_ rename the gui patcher classes or you will break existing BP configs
#------------------------------------------------------------------------------
from ..patcher.patchers import base
from ..patcher.patchers import importers
from ..patcher.patchers import multitweak_actors, multitweak_assorted, \
    multitweak_clothes, multitweak_names, multitweak_settings, \
    races_multitweaks
from ..patcher.patchers import special

# Patchers 10 -----------------------------------------------------------------
class AliasesPatcher(_AliasesPatcherPanel, base.AliasesPatcher): pass
class CBash_AliasesPatcher(_AliasesPatcherPanel,
                           base.CBash_AliasesPatcher): pass

class PatchMerger(base.PatchMerger, _ListPatcherPanel):
    listLabel = _(u'Mergeable Mods')
class CBash_PatchMerger(base.CBash_PatchMerger, _ListPatcherPanel):
    listLabel = _(u'Mergeable Mods')

# Patchers 20 -----------------------------------------------------------------
class GraphicsPatcher(importers.GraphicsPatcher, _ListPatcherPanel): pass
class CBash_GraphicsPatcher(importers.CBash_GraphicsPatcher,
                            _ListPatcherPanel): pass

class KFFZPatcher(importers.KFFZPatcher, _ListPatcherPanel): pass
class CBash_KFFZPatcher(importers.CBash_KFFZPatcher, _ListPatcherPanel): pass

class NPCAIPackagePatcher(importers.NPCAIPackagePatcher,
                          _ListPatcherPanel): pass
class CBash_NPCAIPackagePatcher(importers.CBash_NPCAIPackagePatcher,
                                _ListPatcherPanel): pass

class ActorImporter(importers.ActorImporter, _ListPatcherPanel): pass
class CBash_ActorImporter(importers.CBash_ActorImporter,
                          _ListPatcherPanel): pass

class DeathItemPatcher(importers.DeathItemPatcher, _ListPatcherPanel): pass
class CBash_DeathItemPatcher(importers.CBash_DeathItemPatcher,
                             _ListPatcherPanel): pass

class CellImporter(importers.CellImporter, _ListPatcherPanel): pass
class CBash_CellImporter(importers.CBash_CellImporter, _ListPatcherPanel): pass

class ImportFactions(importers.ImportFactions, _ListPatcherPanel): pass
class CBash_ImportFactions(importers.CBash_ImportFactions,
                           _ListPatcherPanel): pass

class ImportRelations(importers.ImportRelations, _ListPatcherPanel): pass
class CBash_ImportRelations(importers.CBash_ImportRelations,
                            _ListPatcherPanel): pass

class ImportInventory(importers.ImportInventory, _ListPatcherPanel): pass
class CBash_ImportInventory(importers.CBash_ImportInventory,
                            _ListPatcherPanel): pass

class ImportActorsSpells(importers.ImportActorsSpells, _ListPatcherPanel): pass
class CBash_ImportActorsSpells(importers.CBash_ImportActorsSpells,
                               _ListPatcherPanel): pass

class NamesPatcher(importers.NamesPatcher, _ListPatcherPanel): pass
class CBash_NamesPatcher(importers.CBash_NamesPatcher, _ListPatcherPanel): pass

class NpcFacePatcher(importers.NpcFacePatcher, _ListPatcherPanel): pass
class CBash_NpcFacePatcher(importers.CBash_NpcFacePatcher,
                           _ListPatcherPanel): pass

class RoadImporter(importers.RoadImporter, _ListPatcherPanel): pass
class CBash_RoadImporter(importers.CBash_RoadImporter, _ListPatcherPanel): pass

class SoundPatcher(importers.SoundPatcher, _ListPatcherPanel): pass
class CBash_SoundPatcher(importers.CBash_SoundPatcher, _ListPatcherPanel): pass

class StatsPatcher(importers.StatsPatcher, _ListPatcherPanel): pass
class CBash_StatsPatcher(importers.CBash_StatsPatcher, _ListPatcherPanel): pass

class ImportScripts(importers.ImportScripts, _ListPatcherPanel): pass
class CBash_ImportScripts(importers.CBash_ImportScripts,
                          _ListPatcherPanel): pass

class SpellsPatcher(importers.SpellsPatcher, _ListPatcherPanel): pass
class CBash_SpellsPatcher(importers.CBash_SpellsPatcher,
                          _ListPatcherPanel): pass

# Patchers 30 -----------------------------------------------------------------
class AssortedTweaker(multitweak_assorted.AssortedTweaker,
                      _TweakPatcherPanel): pass
class CBash_AssortedTweaker(multitweak_assorted.CBash_AssortedTweaker,
                            _TweakPatcherPanel): pass

class ClothesTweaker(multitweak_clothes.ClothesTweaker,
                     _TweakPatcherPanel): pass
class CBash_ClothesTweaker(multitweak_clothes.CBash_ClothesTweaker,
                           _TweakPatcherPanel): pass

class GmstTweaker(multitweak_settings.GmstTweaker, _TweakPatcherPanel): pass
class CBash_GmstTweaker(multitweak_settings.CBash_GmstTweaker,
                        _TweakPatcherPanel): pass

class NamesTweaker(multitweak_names.NamesTweaker, _TweakPatcherPanel): pass
class CBash_NamesTweaker(multitweak_names.CBash_NamesTweaker,
                         _TweakPatcherPanel): pass

class TweakActors(multitweak_actors.TweakActors, _TweakPatcherPanel): pass
class CBash_TweakActors(multitweak_actors.CBash_TweakActors,
                        _TweakPatcherPanel): pass

# Patchers 40 -----------------------------------------------------------------
class UpdateReferences(base.UpdateReferences, _ListPatcherPanel): pass
class CBash_UpdateReferences(base.CBash_UpdateReferences,
                             _ListPatcherPanel): pass

class RacePatcher(races_multitweaks.RacePatcher, _DoublePatcherPanel):
    listLabel = _(u'Race Mods')
class CBash_RacePatcher(races_multitweaks.CBash_RacePatcher,
                        _DoublePatcherPanel):
    listLabel = _(u'Race Mods')

class ListsMerger(special.ListsMerger, _ListPatcherPanel):
    listLabel = _(u'Override Delev/Relev Tags')
class CBash_ListsMerger(special.CBash_ListsMerger, _ListPatcherPanel):
    listLabel = _(u'Override Delev/Relev Tags')

class ContentsChecker(special.ContentsChecker, _PatcherPanel): pass
class CBash_ContentsChecker(special.CBash_ContentsChecker, _PatcherPanel): pass

#------------------------------------------------------------------------------
# Game specific GUI Patchers --------------------------------------------------
#------------------------------------------------------------------------------
from .patcher_dialog import PBash_gui_patchers, CBash_gui_patchers, \
    otherPatcherDict
# Dynamically create game specific UI patcher classes and add them to module's
# scope
from importlib import import_module
gamePatcher = import_module('.patcher', ##: move in bush.py !
                       package=bush.game.__name__)
for name, typeInfo in gamePatcher.gameSpecificPatchers.items():
    globals()[name] = type(name, (typeInfo.clazz, _PatcherPanel), {})
    if typeInfo.twinPatcher:
        otherPatcherDict[name] = typeInfo.twinPatcher
for name, typeInfo in gamePatcher.gameSpecificListPatchers.items():
    globals()[name] = type(name, (typeInfo.clazz, _ListPatcherPanel), {})
    if typeInfo.twinPatcher:
        otherPatcherDict[name] = typeInfo.twinPatcher

del import_module

# Init Patchers
def initPatchers():
    PBash_gui_patchers.extend((globals()[x]() for x in bush.game.patchers))
    CBash_gui_patchers.extend((globals()[x]() for x in bush.game.CBash_patchers))
