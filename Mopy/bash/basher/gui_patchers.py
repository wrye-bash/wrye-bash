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

import string
import wx
from .. import bosh, bush, balt
from ..balt import fill, staticText, vSizer, checkBox, button, hsbSizer, Links, \
    SeparatorLink, CheckLink, Link
from ..bolt import GPath

class Patcher:
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
            gText = staticText(self.gConfigPanel,text)
            gSizer = vSizer(gText)
            gConfigPanel.SetSizer(gSizer)
            gConfigSizer.Add(gConfigPanel,1,wx.EXPAND)
        return self.gConfigPanel

    def Layout(self):
        """Layout control components."""
        if self.gConfigPanel:
            self.gConfigPanel.Layout()

#------------------------------------------------------------------------------
class _AliasesPatcher(Patcher):
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
        gText = staticText(gConfigPanel,text)
        #gExample = staticText(gConfigPanel,
        #    _(u"Example Mod 1.esp >> Example Mod 1.2.esp"))
        #--Aliases Text
        self.gAliases = balt.textCtrl(gConfigPanel, multiline=True,
                                      onKillFocus=self.OnEditAliases)
        self.SetAliasText()
        #--Sizing
        gSizer = vSizer(
            gText,
            #(gExample,0,wx.EXPAND|wx.TOP,8),
            (self.gAliases,1,wx.EXPAND|wx.TOP,4))
        gConfigPanel.SetSizer(gSizer)
        gConfigSizer.Add(gConfigPanel,1,wx.EXPAND)
        return self.gConfigPanel

    def SetAliasText(self):
        """Sets alias text according to current aliases."""
        self.gAliases.SetValue(u'\n'.join([
            u'%s >> %s' % (key.s,value.s) for key,value in sorted(self.aliases.items())]))

    def OnEditAliases(self,event):
        text = self.gAliases.GetValue()
        self.aliases.clear()
        for line in text.split(u'\n'):
            fields = map(string.strip,line.split(u'>>'))
            if len(fields) != 2 or not fields[0] or not fields[1]: continue
            self.aliases[GPath(fields[0])] = GPath(fields[1])
        self.SetAliasText()

#------------------------------------------------------------------------------
class ListPatcher(Patcher):
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
        gText = staticText(self.gConfigPanel,text)
        if self.forceItemCheck:
            self.gList = balt.listBox(gConfigPanel, isSingle=False)
        else:
            self.gList = balt.listBox(gConfigPanel, kind='checklist')
            self.gList.Bind(wx.EVT_CHECKLISTBOX,self.OnListCheck)
        #--Events
        self.gList.Bind(wx.EVT_MOTION,self.OnMouse)
        self.gList.Bind(wx.EVT_RIGHT_DOWN,self.OnMouse)
        self.gList.Bind(wx.EVT_RIGHT_UP,self.OnMouse)
        self.mouseItem = -1
        self.mouseState = None
        #--Manual controls
        if self.forceAuto:
            gManualSizer = None
            self.SetItems(self.getAutoItems())
        else:
            self.gAuto = checkBox(gConfigPanel, _(u'Automatic'),
                                  onCheck=self.OnAutomatic,
                                  checked=self.autoIsChecked)
            self.gAdd = button(gConfigPanel,_(u'Add'),onClick=self.OnAdd)
            self.gRemove = button(gConfigPanel,_(u'Remove'),onClick=self.OnRemove)
            self.OnAutomatic()
            gManualSizer = (vSizer(
                (self.gAuto,0,wx.TOP,2),
                (self.gAdd,0,wx.TOP,12),
                (self.gRemove,0,wx.TOP,4),
                ),0,wx.EXPAND|wx.LEFT,4)
        if self.selectCommands:
            self.gSelectAll= button(gConfigPanel,_(u'Select All'),onClick=self.SelectAll)
            self.gDeselectAll = button(gConfigPanel,_(u'Deselect All'),onClick=self.DeselectAll)
            gSelectSizer = (vSizer(
                (self.gSelectAll,0,wx.TOP,12),
                (self.gDeselectAll,0,wx.TOP,4),
                ),0,wx.EXPAND|wx.LEFT,4)
        else: gSelectSizer = None
        #--Layout
        gSizer = vSizer(
            (gText,),
            (balt.hsbSizer((gConfigPanel,wx.ID_ANY,self.__class__.listLabel),
                ((4,0),0,wx.EXPAND),
                (self.gList,1,wx.EXPAND|wx.TOP,2),
                gManualSizer,gSelectSizer,
                ),1,wx.EXPAND|wx.TOP,4),
            )
        gConfigPanel.SetSizer(gSizer)
        gConfigSizer.Add(gConfigPanel,1,wx.EXPAND)
        return gConfigPanel

    def SetItems(self,items):
        """Set item to specified set of items."""
        items = self.items = self.sortConfig(items)
        forceItemCheck = self.forceItemCheck
        defaultItemCheck = self.__class__.canAutoItemCheck and bosh.inisettings['AutoItemCheck']
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

    def OnAutomatic(self,event=None):
        """Automatic checkbox changed."""
        self.autoIsChecked = self.gAuto.IsChecked()
        self.gAdd.Enable(not self.autoIsChecked)
        self.gRemove.Enable(not self.autoIsChecked)
        if self.autoIsChecked:
            self.SetItems(self.getAutoItems())

    def OnAdd(self,event):
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

    def OnRemove(self,event):
        """Remove button clicked."""
        selected = self.gList.GetSelections()
        newItems = [item for index,item in enumerate(self.configItems) if index not in selected]
        self.SetItems(newItems)

    #--Choice stuff ---------------------------------------
    def OnMouse(self,event):
        """Check mouse motion to detect right click event."""
        if event.RightDown():
            self.mouseState = (event.m_x,event.m_y)
            event.Skip()
        elif event.RightUp() and self.mouseState:
            self.ShowChoiceMenu(event)
        elif event.Dragging():
            if self.mouseState:
                oldx,oldy = self.mouseState
                if max(abs(event.m_x-oldx),abs(event.m_y-oldy)) > 4:
                    self.mouseState = None
        else:
            self.mouseState = False
            event.Skip()

    def ShowChoiceMenu(self,event):
        """Displays a popup choice menu if applicable.
        NOTE: Assume that configChoice returns a set of chosen items."""
        if not self.choiceMenu: return
        #--Item Index
        itemHeight = self.gList.GetCharHeight() if self.forceItemCheck else \
            self.gList.GetItemHeight()
        itemIndex = event.m_y/itemHeight + self.gList.GetScrollPos(wx.VERTICAL)
        if itemIndex >= len(self.items): return
        self.gList.SetSelection(itemIndex)
        choiceSet = self.getChoice(self.items[itemIndex])
        #--Build Menu
        class _OnItemChoice(CheckLink):
            def __init__(self, _text, index):
                super(_OnItemChoice, self).__init__(_text)
                self.index = index
            def _check(self): return self.text in choiceSet
            def Execute(self, event_): _onItemChoice(self.index)
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

    def SelectAll(self,event=None):
        """'Select All' Button was pressed, update all configChecks states."""
        try:
            for index, item in enumerate(self.items):
                self.gList.Check(index,True)
            self.OnListCheck()
        except AttributeError:
            pass #ListBox instead of CheckListBox
        self.gConfigPanel.GetParent().gPatchers.SetFocusFromKbd()

    def DeselectAll(self,event=None):
        """'Deselect All' Button was pressed, update all configChecks states."""
        try:
            self.gList.SetChecked([])
            self.OnListCheck()
        except AttributeError:
            pass #ListBox instead of CheckListBox
        self.gConfigPanel.GetParent().gPatchers.SetFocusFromKbd()

#------------------------------------------------------------------------------
class TweakPatcher(Patcher):
    """Patcher panel with list of checkable, configurable tweaks."""
    listLabel = _(u"Tweaks")

    def GetConfigPanel(self,parent,gConfigSizer,gTipText):
        """Show config."""
        if self.gConfigPanel: return self.gConfigPanel
        #--Else...
        self.gTipText = gTipText
        gConfigPanel = self.gConfigPanel = wx.Window(parent,style=wx.TAB_TRAVERSAL)
        text = fill(self.__class__.text,70)
        gText = staticText(self.gConfigPanel,text)
        self.gTweakList = balt.listBox(gConfigPanel, kind='checklist')
        #--Events
        self.gTweakList.Bind(wx.EVT_CHECKLISTBOX,self.TweakOnListCheck)
        self.gTweakList.Bind(wx.EVT_MOTION,self.TweakOnMouse)
        self.gTweakList.Bind(wx.EVT_LEAVE_WINDOW,self.TweakOnMouse)
        self.gTweakList.Bind(wx.EVT_RIGHT_DOWN,self.TweakOnMouse)
        self.gTweakList.Bind(wx.EVT_RIGHT_UP,self.TweakOnMouse)
        self.mouseItem = -1
        self.mouseState = None
        if self.selectCommands:
            self.gSelectAll= button(gConfigPanel,_(u'Select All'),onClick=self.TweakSelectAll)
            self.gDeselectAll = button(gConfigPanel,_(u'Deselect All'),onClick=self.TweakDeselectAll)
            gSelectSizer = (vSizer(
                (self.gSelectAll,0,wx.TOP,12),
                (self.gDeselectAll,0,wx.TOP,4),
                ),0,wx.EXPAND|wx.LEFT,4)
        else: gSelectSizer = None
        #--Init GUI
        self.SetTweaks()
        #--Layout
        gSizer = vSizer(
            (gText,),
            (hsbSizer((gConfigPanel,wx.ID_ANY,self.__class__.listLabel),
                ((4,0),0,wx.EXPAND),
                (self.gTweakList,1,wx.EXPAND|wx.TOP,2),
                gSelectSizer,
                ),1,wx.EXPAND|wx.TOP,4),
            )
        gConfigPanel.SetSizer(gSizer)
        gConfigSizer.Add(gConfigPanel,1,wx.EXPAND)
        return gConfigPanel

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
            self.mouseState = (event.m_x,event.m_y)
            event.Skip()
        elif event.RightUp() and self.mouseState:
            self.ShowChoiceMenu(event)
        elif event.Leaving():
            self.gTipText.SetLabel(u'')
            self.mouseState = False
            event.Skip()
        elif event.Dragging():
            if self.mouseState:
                oldx,oldy = self.mouseState
                if max(abs(event.m_x-oldx),abs(event.m_y-oldy)) > 4:
                    self.mouseState = None
        elif event.Moving():
            mouseItem = event.m_y/self.gTweakList.GetItemHeight() + self.gTweakList.GetScrollPos(wx.VERTICAL)
            self.mouseState = False
            if mouseItem != self.mouseItem:
                self.mouseItem = mouseItem
                self.MouseEnteredItem(mouseItem)
            event.Skip()
        else:
            self.mouseState = False
            event.Skip()

    def MouseEnteredItem(self,item):
        """Show tip text when changing item."""
        #--Following isn't displaying correctly.
        tip = item < len(self.tweaks) and self.tweaks[item].tip
        if tip:
            self.gTipText.SetLabel(tip)
        else:
            self.gTipText.SetLabel(u'')

    def ShowChoiceMenu(self,event):
        """Displays a popup choice menu if applicable."""
        #--Tweak Index
        tweakIndex = event.m_y/self.gTweakList.GetItemHeight() + self.gTweakList.GetScrollPos(wx.VERTICAL)
        self.rightClickTweakIndex = tweakIndex
        #--Tweaks
        tweaks = self.tweaks
        if tweakIndex >= len(tweaks): return
        tweak = tweaks[tweakIndex]
        choiceLabels = tweak.choiceLabels
        if len(choiceLabels) <= 1: return
        self.gTweakList.SetSelection(tweakIndex)
        #--Build Menu
        links = Links()
        _self = self # ugly, OnTweakCustomChoice is too big to make it local though
        class _ValueLink(CheckLink):
            def __init__(self, _text, index):
                super(_ValueLink, self).__init__(_text)
                self.index = index
            def _check(self): return self.index == tweak.chosen
            def Execute(self, event_): _self.OnTweakChoice(self.index)
        class _ValueLinkCustom(_ValueLink):
            def Execute(self, event_): _self.OnTweakCustomChoice(self.index)
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

    def OnTweakChoice(self, index):
        """Handle choice menu selection."""
        tweakIndex = self.rightClickTweakIndex
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

    def OnTweakCustomChoice(self, index):
        """Handle choice menu selection."""
        tweakIndex = self.rightClickTweakIndex
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
                    default=tweak.choiceValues[index][i])
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

    def TweakSelectAll(self,event=None):
        """'Select All' Button was pressed, update all configChecks states."""
        try:
            for index, item in enumerate(self.tweaks):
                self.gTweakList.Check(index,True)
            self.TweakOnListCheck()
        except AttributeError:
            pass #ListBox instead of CheckListBox
        self.gConfigPanel.GetParent().gPatchers.SetFocusFromKbd()

    def TweakDeselectAll(self,event=None):
        """'Deselect All' Button was pressed, update all configChecks states."""
        try:
            self.gTweakList.SetChecked([])
            self.TweakOnListCheck()
        except AttributeError:
            pass #ListBox instead of CheckListBox
        self.gConfigPanel.GetParent().gPatchers.SetFocusFromKbd()

#------------------------------------------------------------------------------
class DoublePatcher(TweakPatcher,ListPatcher):
    """Patcher panel with option to select source elements."""
    listLabel = _(u'Source Mods/Files')

    def GetConfigPanel(self,parent,gConfigSizer,gTipText):
        """Show config."""
        if self.gConfigPanel: return self.gConfigPanel
        #--Else...
        self.gTipText = gTipText
        gConfigPanel = self.gConfigPanel = wx.Window(parent)
        text = fill(self.text,70)
        gText = staticText(self.gConfigPanel,text)
        #--Import List
        self.gList = balt.listBox(gConfigPanel, kind='checklist')
        self.gList.Bind(wx.EVT_MOTION,self.OnMouse)
        self.gList.Bind(wx.EVT_RIGHT_DOWN,self.OnMouse)
        self.gList.Bind(wx.EVT_RIGHT_UP,self.OnMouse)
        #--Tweak List
        self.gTweakList = balt.listBox(gConfigPanel, kind='checklist')
        self.gTweakList.Bind(wx.EVT_CHECKLISTBOX,self.TweakOnListCheck)
        self.gTweakList.Bind(wx.EVT_MOTION,self.TweakOnMouse)
        self.gTweakList.Bind(wx.EVT_LEAVE_WINDOW,self.TweakOnMouse)
        self.gTweakList.Bind(wx.EVT_RIGHT_DOWN,self.TweakOnMouse)
        self.gTweakList.Bind(wx.EVT_RIGHT_UP,self.TweakOnMouse)
        self.mouseItem = -1
        self.mouseState = None
        #--Buttons
        self.gSelectAll = button(gConfigPanel,_(u'Select All'),onClick=self.SelectAll)
        self.gDeselectAll = button(gConfigPanel,_(u'Deselect All'),onClick=self.DeselectAll)
        gSelectSizer = (vSizer(
            (self.gSelectAll,0,wx.TOP,12),
            (self.gDeselectAll,0,wx.TOP,4),
            ),0,wx.EXPAND|wx.LEFT,4)
        self.gTweakSelectAll = button(gConfigPanel,_(u'Select All'),onClick=self.TweakSelectAll)
        self.gTweakDeselectAll = button(gConfigPanel,_(u'Deselect All'),onClick=self.TweakDeselectAll)
        gTweakSelectSizer = (vSizer(
            (self.gTweakSelectAll,0,wx.TOP,12),
            (self.gTweakDeselectAll,0,wx.TOP,4),
            ),0,wx.EXPAND|wx.LEFT,4)
        #--Layout
        gSizer = vSizer(
            (gText,),
            (hsbSizer((gConfigPanel,wx.ID_ANY,self.__class__.listLabel),
                ((4,0),0,wx.EXPAND),
                (self.gList,1,wx.EXPAND|wx.TOP,2),
                gSelectSizer,),1,wx.EXPAND|wx.TOP,4),
            (hsbSizer((gConfigPanel,wx.ID_ANY,self.__class__.subLabel),
                ((4,0),0,wx.EXPAND),
                (self.gTweakList,1,wx.EXPAND|wx.TOP,2),
                gTweakSelectSizer,),1,wx.EXPAND|wx.TOP,4),
            )
        gConfigPanel.SetSizer(gSizer)
        gConfigSizer.Add(gConfigPanel,1,wx.EXPAND)
        #--Initialize
        self.SetItems(self.getAutoItems())
        self.SetTweaks()
        return gConfigPanel

#------------------------------------------------------------------------------
# GUI Patcher classes - mixins of patchers and the GUI patchers defined above -
#------------------------------------------------------------------------------
##: consider dynamically create those (game independent ?) UI patchers based on
# dictionaries in bash.patcher.__init__.py (see the game specific creation
# below)
from ..patcher.patchers import base
from ..patcher.patchers import importers
from ..patcher.patchers import multitweak_actors, multitweak_assorted, \
    multitweak_clothes, multitweak_names, multitweak_settings, \
    races_multitweaks
from ..patcher.patchers import special

# Patchers 10 -----------------------------------------------------------------
class AliasesPatcher(_AliasesPatcher, base.AliasesPatcher): pass
class CBash_AliasesPatcher(_AliasesPatcher, base.CBash_AliasesPatcher): pass

class PatchMerger(base.PatchMerger,ListPatcher):
    listLabel = _(u'Mergeable Mods')
class CBash_PatchMerger(base.CBash_PatchMerger,ListPatcher):
    listLabel = _(u'Mergeable Mods')
# Patchers 20 -----------------------------------------------------------------
class GraphicsPatcher(importers.GraphicsPatcher,ListPatcher): pass
class CBash_GraphicsPatcher(importers.CBash_GraphicsPatcher,ListPatcher): pass

class KFFZPatcher(importers.KFFZPatcher,ListPatcher): pass
class CBash_KFFZPatcher(importers.CBash_KFFZPatcher,ListPatcher): pass

class NPCAIPackagePatcher(importers.NPCAIPackagePatcher,ListPatcher): pass
class CBash_NPCAIPackagePatcher(importers.CBash_NPCAIPackagePatcher,
                                ListPatcher): pass

class ActorImporter(importers.ActorImporter,ListPatcher): pass
class CBash_ActorImporter(importers.CBash_ActorImporter,ListPatcher): pass

class DeathItemPatcher(importers.DeathItemPatcher,ListPatcher): pass
class CBash_DeathItemPatcher(importers.CBash_DeathItemPatcher,ListPatcher): pass

class CellImporter(importers.CellImporter,ListPatcher): pass
class CBash_CellImporter(importers.CBash_CellImporter,ListPatcher): pass

class ImportFactions(importers.ImportFactions,ListPatcher): pass
class CBash_ImportFactions(importers.CBash_ImportFactions,ListPatcher): pass

class ImportRelations(importers.ImportRelations,ListPatcher): pass
class CBash_ImportRelations(importers.CBash_ImportRelations,ListPatcher): pass

class ImportInventory(importers.ImportInventory,ListPatcher): pass
class CBash_ImportInventory(importers.CBash_ImportInventory,ListPatcher): pass

class ImportActorsSpells(importers.ImportActorsSpells,ListPatcher): pass
class CBash_ImportActorsSpells(importers.CBash_ImportActorsSpells,
                               ListPatcher): pass

class NamesPatcher(importers.NamesPatcher,ListPatcher): pass
class CBash_NamesPatcher(importers.CBash_NamesPatcher,ListPatcher): pass

class NpcFacePatcher(importers.NpcFacePatcher,ListPatcher): pass
class CBash_NpcFacePatcher(importers.CBash_NpcFacePatcher,ListPatcher): pass

class RoadImporter(importers.RoadImporter,ListPatcher): pass
class CBash_RoadImporter(importers.CBash_RoadImporter,ListPatcher): pass

class SoundPatcher(importers.SoundPatcher,ListPatcher): pass
class CBash_SoundPatcher(importers.CBash_SoundPatcher,ListPatcher): pass

class StatsPatcher(importers.StatsPatcher,ListPatcher): pass
class CBash_StatsPatcher(importers.CBash_StatsPatcher,ListPatcher): pass

class ImportScripts(importers.ImportScripts,ListPatcher):pass
class CBash_ImportScripts(importers.CBash_ImportScripts,ListPatcher):pass

class SpellsPatcher(importers.SpellsPatcher,ListPatcher):pass
class CBash_SpellsPatcher(importers.CBash_SpellsPatcher,ListPatcher):pass

# Patchers 30 -----------------------------------------------------------------
class AssortedTweaker(multitweak_assorted.AssortedTweaker,TweakPatcher): pass
class CBash_AssortedTweaker(multitweak_assorted.CBash_AssortedTweaker,
                            TweakPatcher): pass

class ClothesTweaker(multitweak_clothes.ClothesTweaker,TweakPatcher): pass
class CBash_ClothesTweaker(multitweak_clothes.CBash_ClothesTweaker,
                           TweakPatcher): pass

class GmstTweaker(multitweak_settings.GmstTweaker,TweakPatcher): pass
class CBash_GmstTweaker(multitweak_settings.CBash_GmstTweaker,
                        TweakPatcher): pass

class NamesTweaker(multitweak_names.NamesTweaker,TweakPatcher): pass
class CBash_NamesTweaker(multitweak_names.CBash_NamesTweaker,
                         TweakPatcher): pass

class TweakActors(multitweak_actors.TweakActors,TweakPatcher): pass
class CBash_TweakActors(multitweak_actors.CBash_TweakActors,TweakPatcher): pass

# Patchers 40 -----------------------------------------------------------------
class UpdateReferences(base.UpdateReferences,ListPatcher): pass
class CBash_UpdateReferences(base.CBash_UpdateReferences,ListPatcher): pass

class RacePatcher(races_multitweaks.RacePatcher,DoublePatcher):
    listLabel = _(u'Race Mods')
class CBash_RacePatcher(races_multitweaks.CBash_RacePatcher,DoublePatcher):
    listLabel = _(u'Race Mods')

class ListsMerger(special.ListsMerger,ListPatcher):
    listLabel = _(u'Override Delev/Relev Tags')
class CBash_ListsMerger(special.CBash_ListsMerger,ListPatcher):
    listLabel = _(u'Override Delev/Relev Tags')

class ContentsChecker(special.ContentsChecker,Patcher): pass
class CBash_ContentsChecker(special.CBash_ContentsChecker,Patcher): pass

#------------------------------------------------------------------------------
# Game specific GUI Patchers --------------------------------------------------
#------------------------------------------------------------------------------
from .patcher_dialog import gui_patchers, CBash_gui_patchers, otherPatcherDict
# Dynamically create game specific UI patcher classes and add them to module's
# scope
from importlib import import_module
gamePatcher = import_module('.patcher', ##: move in bush.py !
                       package=bush.game.__name__)
for name, typeInfo in gamePatcher.gameSpecificPatchers.items():
    globals()[name] = type(name, (typeInfo.clazz, Patcher), {})
    if typeInfo.twinPatcher:
        otherPatcherDict[name] = typeInfo.twinPatcher
for name, typeInfo in gamePatcher.gameSpecificListPatchers.items():
    globals()[name] = type(name, (typeInfo.clazz, ListPatcher), {})
    if typeInfo.twinPatcher:
        otherPatcherDict[name] = typeInfo.twinPatcher

del import_module

# Init Patchers
def initPatchers():
    gui_patchers.extend((globals()[x]() for x in bush.game.patchers))
    CBash_gui_patchers.extend((globals()[x]() for x in bush.game.CBash_patchers))
