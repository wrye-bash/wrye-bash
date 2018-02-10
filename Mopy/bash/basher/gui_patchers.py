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
import copy
import string
import re
from operator import itemgetter
import wx
# Internal
from .. import bass, bosh, bush, balt, load_order, bolt, exception
from ..balt import fill, StaticText, vSizer, checkBox, Button, hsbSizer, \
    Links, SeparatorLink, CheckLink, Link, vspace, VSizer
from ..bolt import GPath
from ..patcher import patch_files

reCsvExt = re.compile(ur'\.csv$', re.I | re.U)

class _PatcherPanel(object):
    """Basic patcher panel with no options."""
    selectCommands = True # whether this panel displays De/Select All
    style = wx.TAB_TRAVERSAL
    # CONFIG DEFAULTS
    default_isEnabled = False # is the patcher enabled on a new bashed patch ?

    def SetIsFirstLoad(self,isFirstLoad):
        self._isFirstLoad = isFirstLoad

    def _EnsurePatcherEnabled(self):
        self.patch_dialog.CheckPatcher(self)
        self.isEnabled = True

    def _BoldPatcherLabel(self): self.patch_dialog.BoldPatcher(self)

    def _GetIsFirstLoad(self):
        if hasattr(self, '_isFirstLoad'):
            return self._isFirstLoad
        else:
            return False

    def GetConfigPanel(self,parent,gConfigSizer,gTipText):
        """Show config.

        :type parent: basher.patcher_dialog.PatchDialog
        """
        if self.gConfigPanel: return self.gConfigPanel
        self.patch_dialog = parent
        self.gTipText = gTipText
        self.gConfigPanel = wx.Panel(parent, style=self.__class__.style)
        patcher_txt = fill(self.text, 70)
        gText = StaticText(self.gConfigPanel, patcher_txt)
        self.gSizer = VSizer(gText)
        self.gConfigPanel.SetSizer(self.gSizer)
        gConfigSizer.Add(self.gConfigPanel, 1, wx.EXPAND)
        return self.gConfigPanel

    def Layout(self):
        """Layout control components."""
        if self.gConfigPanel:
            self.gConfigPanel.Layout()

    #--Config Phase -----------------------------------------------------------
    def getConfig(self, configs):
        """Get config from configs dictionary and/or set to default.

        Called in basher.patcher_dialog.PatchDialog#__init__, before the
        dialog is shown, to update the patch options based on the previous
        config for this patch stored in modInfos.table[patch][
        'bash.patch.configs']. If no config is saved then the class
        default_XXX values are used for the relevant attributes."""
        config = configs.setdefault(self.__class__.__name__, {})
        self.isEnabled = config.get('isEnabled',
                                    self.__class__.default_isEnabled)
        # return the config dict for this patcher to read additional values
        return config

    def saveConfig(self, configs):
        """Save config to configs dictionary.

        Most patchers just save their enabled state, except the AListPatcher
        subclasses - which save their choices - and the AliasesPatcher that
        saves the aliases."""
        config = configs[self.__class__.__name__] = {}
        config['isEnabled'] = self.isEnabled
        return config # return the config dict for this patcher to further edit

    def log_config(self, config, clip, log):
        className = self.__class__.__name__
        humanName = self.__class__.name
        # Patcher in the config?
        if not className in config: return
        # Patcher active?
        conf = config[className]
        if not conf.get('isEnabled',False): return
        # Active
        log.setHeader(u'== ' + humanName)
        clip.write(u'\n')
        clip.write(u'== ' + humanName + u'\n')
        self._log_config(conf, config, clip, log)

    def _log_config(self, conf, config, clip, log):
        items = conf.get('configItems', [])
        if len(items) == 0:
            log(u' ')
        for item in conf.get('configItems', []):
            checks = conf.get('configChecks', {})
            checked = checks.get(item, False)
            if checked:
                log(u'* __%s__' % item)
                clip.write(u' ** %s\n' % item)
            else:
                log(u'. ~~%s~~' % item)
                clip.write(u'    %s\n' % item)

    def import_config(self, patchConfigs, set_first_load=False, default=False):
        self.SetIsFirstLoad(set_first_load)
        self.getConfig(patchConfigs) # set isEnabled and load additional config
        self._import_config(default)

    def _import_config(self, default=False): pass

    def mass_select(self, select=True): self.isEnabled = select

    def _bold(self, index, cntrl):
        get_font = self.gConfigPanel.GetFont()
        cntrl.SetItemFont(index, balt.Font.Style(get_font, bold=True))

#------------------------------------------------------------------------------
class _AliasesPatcherPanel(_PatcherPanel):
    # CONFIG DEFAULTS
    default_aliases = {}

    def GetConfigPanel(self,parent,gConfigSizer,gTipText):
        """Show config."""
        if self.gConfigPanel: return self.gConfigPanel
        gConfigPanel = super(_AliasesPatcherPanel, self).GetConfigPanel(parent,
            gConfigSizer, gTipText)
        #gExample = StaticText(gConfigPanel,
        #    _(u"Example Mod 1.esp >> Example Mod 1.2.esp"))
        #--Aliases Text
        self.gAliases = balt.TextCtrl(gConfigPanel, multiline=True,
                                      onKillFocus=self.OnEditAliases)
        self.SetAliasText()
        #--Sizing
        self.gSizer.AddElements(
            #(gExample,0,wx.EXPAND|wx.TOP,8),
            vspace(), (self.gAliases, 1, wx.EXPAND))
        return self.gConfigPanel

    def SetAliasText(self):
        """Sets alias text according to current aliases."""
        self.gAliases.SetValue(u'\n'.join([
            u'%s >> %s' % (key.s,value.s) for key,value in sorted(self.aliases.items())]))

    def OnEditAliases(self):
        aliases_text = self.gAliases.GetValue()
        self.aliases.clear()
        for line in aliases_text.split(u'\n'):
            fields = map(string.strip,line.split(u'>>'))
            if len(fields) != 2 or not fields[0] or not fields[1]: continue
            self.aliases[GPath(fields[0])] = GPath(fields[1])
        self.SetAliasText()

    #--Config Phase -----------------------------------------------------------
    def getConfig(self, configs):
        """Get config from configs dictionary and/or set to default."""
        config = super(_AliasesPatcherPanel, self).getConfig(configs)
        #--Update old configs to use Paths instead of strings.
        self.aliases = dict(# map(GPath, item) gives a list (item is a tuple)
            map(GPath, item) for item in
            config.get('aliases', self.__class__.default_aliases).iteritems())
        return config

    def saveConfig(self, configs):
        """Save config to configs dictionary."""
        #--Toss outdated configCheck data.
        config = super(_AliasesPatcherPanel, self).saveConfig(configs)
        config['aliases'] = self.aliases
        return config

    def _log_config(self, conf, config, clip, log):
        aliases = conf.get('aliases', {})
        for mod, alias in aliases.iteritems():
            log(u'* __%s__ >> %s' % (mod.s, alias.s))
            clip.write(u'  %s >> %s\n' % (mod.s, alias.s))

#------------------------------------------------------------------------------
class _ListPatcherPanel(_PatcherPanel):
    """Patcher panel with option to select source elements."""
    listLabel = _(u'Source Mods/Files')
    forceAuto = True
    forceItemCheck = False #--Force configChecked to True for all items
    canAutoItemCheck = True #--GUI: Whether new items are checked by default
    #--Compiled re used by getAutoItems
    autoRe = re.compile(ur"^UNDEFINED$", re.I | re.U)
    # ADDITIONAL CONFIG DEFAULTS FOR LIST PATCHER
    default_autoIsChecked = True
    default_configItems   = []
    default_configChecks  = {}
    default_configChoices = {}

    def GetConfigPanel(self,parent,gConfigSizer,gTipText):
        """Show config."""
        if self.gConfigPanel: return self.gConfigPanel
        gConfigPanel = super(_ListPatcherPanel, self).GetConfigPanel(parent,
            gConfigSizer, gTipText)
        self.forceItemCheck = self.__class__.forceItemCheck
        self.selectCommands = self.__class__.selectCommands
        if self.forceItemCheck:
            self.gList = balt.listBox(gConfigPanel, isSingle=False)
        else:
            self.gList = balt.listBox(gConfigPanel, kind='checklist',
                                      onCheck=self.OnListCheck)
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
        gSelectSizer = self._get_select_sizer()
        #--Layout
        self.gSizer.AddElements(vspace(),
            (hsbSizer(gConfigPanel, self.__class__.listLabel,
                ((4,0),0,wx.EXPAND),
                (self.gList,1,wx.EXPAND|wx.TOP,2),
                gManualSizer,gSelectSizer,
                ),1,wx.EXPAND),
            )
        return gConfigPanel

    def _get_select_sizer(self):
        if not self.selectCommands: return None
        self.gSelectAll = Button(self.gConfigPanel, _(u'Select All'),
                                 onButClick=self.SelectAll)
        self.gDeselectAll = Button(self.gConfigPanel, _(u'Deselect All'),
                                   onButClick=self.DeselectAll)
        return (vSizer(
            vspace(12), self.gSelectAll, vspace(4), self.gDeselectAll),
                0, wx.EXPAND | wx.LEFT, 4)

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
                        self._bold(index, self.gList)
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
        srcDir = bosh.modInfos.store_dir
        wildcard = bosh.modInfos.plugin_wildcard()
        #--File dialog
        title = _(u'Get ')+self.__class__.listLabel
        srcPaths = balt.askOpenMulti(self.gConfigPanel,title,srcDir, u'', wildcard)
        if not srcPaths: return
        #--Get new items
        for srcPath in srcPaths:
            folder, name = srcPath.headTail
            if folder == srcDir and name not in self.configItems:
                self.configItems.append(name)
        self.SetItems(self.configItems)

    def OnRemove(self):
        """Remove button clicked."""
        selections = self.gList.GetSelections()
        newItems = [item for index,item in enumerate(self.configItems) if index not in selections]
        self.SetItems(newItems)

    @staticmethod
    def sortConfig(items):
        """Return sorted items. Default assumes mods and sorts by load
        order."""
        return load_order.get_ordered(items)

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

    def mass_select(self, select=True):
        self.SelectAll() if select else self.DeselectAll()

    #--Config Phase -----------------------------------------------------------
    def getConfig(self, configs):
        """Get config from configs dictionary and/or set to default."""
        config = super(_ListPatcherPanel, self).getConfig(configs)
        self.autoIsChecked = self.forceAuto or config.get(
            'autoIsChecked', self.__class__.default_autoIsChecked)
        self.configItems = copy.deepcopy(
            config.get('configItems', self.__class__.default_configItems))
        self.configChecks = copy.deepcopy(
            config.get('configChecks', self.__class__.default_configChecks))
        self.configChoices = copy.deepcopy(
            config.get('configChoices', self.__class__.default_configChoices))
        #--Verify file existence
        newConfigItems = []
        for srcPath in self.configItems:
            if (srcPath in bosh.modInfos or (reCsvExt.search(
                srcPath.s) and srcPath in self.patches_set)):
                newConfigItems.append(srcPath)
        self.configItems = newConfigItems
        if self.__class__.forceItemCheck:
            for item in self.configItems:
                self.configChecks[item] = True
        return config

    def saveConfig(self, configs):
        """Save config to configs dictionary."""
        #--Toss outdated configCheck data.
        config = super(_ListPatcherPanel, self).saveConfig(configs)
        listSet = set(self.configItems)
        self.configChecks = config['configChecks'] = dict(
            [(key, value) for key, value in self.configChecks.iteritems() if
             key in listSet])
        self.configChoices = config['configChoices'] = dict(
            [(key, value) for key, value in self.configChoices.iteritems() if
             key in listSet])
        config['configItems'] = self.configItems
        config['autoIsChecked'] = self.autoIsChecked
        return config

    def getItemLabel(self,item):
        """Returns label for item to be used in list"""
        return u'%s' % item # Path or basestring - YAK

    def getAutoItems(self):
        """Returns list of items to be used for automatic configuration."""
        autoItems = self._get_auto_mods()
        reFile = re.compile(
            u'_(' + (u'|'.join(self.__class__.autoKey)) + ur')\.csv$', re.U)
        for fileName in sorted(self.patches_set):
            if reFile.search(fileName.s):
                autoItems.append(fileName)
        return autoItems

    def _get_auto_mods(self):
        autoRe = self.__class__.autoRe
        mods_prior_to_patch = load_order.cached_lower_loading_espms(
            patch_files.executing_patch, bosh.modInfos)
        return [mod for mod in mods_prior_to_patch if autoRe.match(mod.s) or (
            self.__class__.autoKey & bosh.modInfos[mod].getBashTags())]

    def _import_config(self, default=False):
        super(_ListPatcherPanel, self)._import_config(default)
        if default:
            self.SetItems(self.getAutoItems())
            return
        for index, item in enumerate(self.items):
            try:
                self.gList.Check(index, self.configChecks[item])
            except KeyError: # keys should be all bolt.Paths
                pass
                # bolt.deprint(_(u'item %s not in saved configs [%s]') % (
                #     item, u', '.join(map(repr, self.configChecks))))

class _ChoiceMenuMixin(object):
    #--List of possible choices for each config item. Item 0 is default.
    _right_click_list = 'gList'

    def _bind_mouse_events(self):
        right_click_list = self.__getattribute__(self._right_click_list)
        right_click_list.Bind(wx.EVT_MOTION, self.OnMouse)
        right_click_list.Bind(wx.EVT_RIGHT_DOWN, self.OnMouse)
        right_click_list.Bind(wx.EVT_RIGHT_UP, self.OnMouse)
        self.mouse_pos = None

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

    def ShowChoiceMenu(self, event): raise exception.AbstractError

#------------------------------------------------------------------------------
class _TweakPatcherPanel(_ChoiceMenuMixin, _PatcherPanel):
    """Patcher panel with list of checkable, configurable tweaks."""
    tweak_label = _(u"Tweaks")
    _right_click_list = 'gTweakList'

    def GetConfigPanel(self,parent,gConfigSizer,gTipText):
        """Show config."""
        if self.gConfigPanel: return self.gConfigPanel
        gConfigPanel = super(_TweakPatcherPanel, self).GetConfigPanel(parent,
            gConfigSizer, gTipText)
        self._build_tweaks_list()
        gTweakSelectSizer = self._get_tweak_select_sizer()
        #--Layout
        self.gSizer.AddElements(vspace(),
            (hsbSizer(gConfigPanel, self.__class__.tweak_label,
                ((4,0),0,wx.EXPAND),
                (self.gTweakList,1,wx.EXPAND|wx.TOP,2),
                gTweakSelectSizer,
                ),1,wx.EXPAND),
            )
        return gConfigPanel

    def _build_tweaks_list(self):
        self.gTweakList = balt.listBox(self.gConfigPanel, kind='checklist',
                                       onCheck=self.TweakOnListCheck)
        #--Events
        self._bind_mouse_events()
        self.gTweakList.Bind(wx.EVT_LEAVE_WINDOW, self.OnMouse)
        self.mouse_dex = -1

    def _get_tweak_select_sizer(self, ):
        if self.selectCommands:
            self.gTweakSelectAll = Button(self.gConfigPanel,
                _(u'Select All'), onButClick=self.TweakSelectAll)
            self.gTweakDeselectAll = Button(self.gConfigPanel,
                _(u'Deselect All'), onButClick=self.TweakDeselectAll)
            gTweakSelectSizer = (vSizer(
                 vspace(12), self.gTweakSelectAll,
                 vspace(4), self.gTweakDeselectAll,
                ),0,wx.EXPAND|wx.LEFT,4)
        else: gTweakSelectSizer = None
        #--Init GUI
        self.SetTweaks()
        return gTweakSelectSizer

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
                self._bold(index, self.gTweakList)
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

    def OnMouse(self, event):
        """Check mouse motion to detect right click event."""
        if event.Leaving():
            self.gTipText.SetLabel(u'')
            self.mouse_pos = None
            event.Skip()
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
            super(_TweakPatcherPanel, self).OnMouse(event)

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

    def mass_select(self, select=True):
        super(_TweakPatcherPanel, self).mass_select(select)
        self.TweakSelectAll() if select else self.TweakDeselectAll()

    #--Config Phase -----------------------------------------------------------
    def getConfig(self, configs):
        """Get config from configs dictionary and/or set to default."""
        config = super(_TweakPatcherPanel, self).getConfig(configs)
        self.tweaks = copy.deepcopy(self.__class__.tweaks)
        for tweak in self.tweaks:
            tweak.get_tweak_config(config)
        return config

    def saveConfig(self, configs):
        """Save config to configs dictionary."""
        config = super(_TweakPatcherPanel, self).saveConfig(configs)
        for tweak in self.tweaks:
            tweak.save_tweak_config(config)
        self.enabledTweaks = [tweak for tweak in self.tweaks if
                              tweak.isEnabled]
        self.isActive = len(self.enabledTweaks) > 0 ##: NOT HERE !!!!
        return config

    def _log_config(self, conf, config, clip, log):
        self.getConfig(config) # will set self.tweaks and load their config
        for tweak in self.tweaks:
            if tweak.key in conf:
                enabled, value = conf.get(tweak.key, (False, u''))
                label = tweak.getListLabel().replace(u'[[', u'[').replace(
                    u']]', u']')
                if enabled:
                    log(u'* __%s__' % label)
                    clip.write(u' ** %s\n' % label)
                else:
                    log(u'. ~~%s~~' % label)
                    clip.write(u'    %s\n' % label)

    def _import_config(self, default=False):
        super(_TweakPatcherPanel, self)._import_config(default)
        for index, tweakie in enumerate(self.tweaks):
            try:
                self.gTweakList.Check(index, tweakie.isEnabled)
                self.gTweakList.SetString(index, tweakie.getListLabel())
            except KeyError: pass # no such key don't spam the log
            except: bolt.deprint(_(u'Error importing Bashed patch '
                u'configuration. Item %s skipped.') % tweakie, traceback=True)

#------------------------------------------------------------------------------
class _DoublePatcherPanel(_TweakPatcherPanel, _ListPatcherPanel):
    """Only used in Race Patcher which features a double panel (source mods
    and tweaks)."""
    listLabel = _(u'Race Mods')
    tweak_label = _(u'Race Tweaks')
    # CONFIG DEFAULTS
    default_isEnabled = True # isActive will be set to True in initPatchFile

    def GetConfigPanel(self,parent,gConfigSizer,gTipText):
        """Show config."""
        if self.gConfigPanel: return self.gConfigPanel
        gConfigPanel = super(_DoublePatcherPanel, self).GetConfigPanel(parent,
            gConfigSizer, gTipText)
        return gConfigPanel

    #--Config Phase -----------------------------------------------------------
    def getAutoItems(self):
        """Returns list of items to be used for automatic configuration."""
        return self._get_auto_mods()

    def _log_config(self, conf, config, clip, log):
        _ListPatcherPanel._log_config(self, conf, config, clip, log)
        log.setHeader(u'== ' + self.tweak_label)
        clip.write(u'\n')
        clip.write(u'== ' + self.tweak_label + u'\n')
        _TweakPatcherPanel._log_config(self, conf, config, clip, log)

#------------------------------------------------------------------------------
class _ImporterPatcherPanel(_ListPatcherPanel):

    #--Config Phase -----------------------------------------------------------
    autoRe = re.compile(ur"^UNDEFINED$",re.I|re.U) # overridden by
    # NamesPatcher, NpcFacePatcher, and not used by ImportInventory,
    # ImportRelations, ImportFactions
    def saveConfig(self, configs):
        """Save config to configs dictionary."""
        config = super(_ImporterPatcherPanel, self).saveConfig(configs)
        if self.isEnabled:
            importedMods = [item for item,value in
                            self.configChecks.iteritems() if
                            value and bosh.ModInfos.rightFileType(item)]
            configs['ImportedMods'].update(importedMods)
        return config

class _ListsMergerPanel(_ChoiceMenuMixin, _ListPatcherPanel):
    listLabel = _(u'Override Delev/Relev Tags')

    #--Config Phase -----------------------------------------------------------
    forceAuto = False
    forceItemCheck = True #--Force configChecked to True for all items
    choiceMenu = (u'Auto', u'----', u'Delev', u'Relev')
    # CONFIG DEFAULTS
    default_isEnabled = True
    selectCommands = False

    def _get_set_choice(self, item):
        """Get default config choice."""
        config_choice = self.configChoices.get(item)
        if not isinstance(config_choice,set): config_choice = {u'Auto'}
        if u'Auto' in config_choice:
            if item in bosh.modInfos:
                bashTags = bosh.modInfos[item].getBashTags()
                config_choice = {u'Auto'} | (self.autoKey & bashTags)
        self.configChoices[item] = config_choice
        return config_choice

    def getItemLabel(self,item):
        """Returns label for item to be used in list"""
        choice = map(itemgetter(0),self.configChoices.get(item,tuple()))
        item  = u'%s' % item # Path or basestring - YAK
        if choice:
            return u'%s [%s]' % (item,u''.join(sorted(choice)))
        else:
            return item

    def GetConfigPanel(self,parent,gConfigSizer,gTipText):
        if self.gConfigPanel: return self.gConfigPanel
        gConfigPanel = super(_ListsMergerPanel, self).GetConfigPanel(parent,
            gConfigSizer, gTipText)
        self._bind_mouse_events()
        return gConfigPanel

    def getConfig(self, configs):
        """Get config from configs dictionary and/or set to default."""
        config = super(_ListsMergerPanel, self).getConfig(configs)
        #--Make sure configChoices are set (as choiceMenu exists).
        for item in self.configItems:
            self._get_set_choice(item)
        return config

    def _get_auto_mods(self):
        autoItems = super(_ListsMergerPanel, self)._get_auto_mods()
        for mod in autoItems: self._get_set_choice(mod)
        return autoItems

    def ShowChoiceMenu(self,event):
        """Displays a popup choice menu if applicable.
        NOTE: Assume that configChoice returns a set of chosen items."""
        #--Item Index
        itemIndex = self.gList.HitTest(event.GetPosition())
        if itemIndex < 0: return
        self.gList.SetSelection(itemIndex)
        choiceSet = self._get_set_choice(self.items[itemIndex])
        #--Build Menu
        class _OnItemChoice(CheckLink):
            def __init__(self, _text, index):
                super(_OnItemChoice, self).__init__(_text)
                self.index = index
            def _check(self): return self._text in choiceSet
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
                self._get_set_choice(item)
            self.gList.SetString(itemIndex, self.getItemLabel(item))
        links = Links()
        for index,label in enumerate(self.choiceMenu):
            if label == u'----':
                links.append(SeparatorLink())
            else:
                links.append(_OnItemChoice(label, index))
        #--Show/Destroy Menu
        links.PopupMenu(self.gList, Link.Frame, None)

    def _log_config(self, conf, config, clip, log):
        self.configChoices = conf.get('configChoices', {})
        for item in conf.get('configItems', []):
            log(u'. __%s__' % self.getItemLabel(item))
            clip.write(u'    %s\n' % self.getItemLabel(item))

    def _import_config(self, default=False): # TODO(ut):non default not handled
        if default:
            super(_ListsMergerPanel, self)._import_config(default)

    def mass_select(self, select=True): self.isEnabled = select

class _MergerPanel(_ListPatcherPanel):
    listLabel = _(u'Mergeable Mods')

    def getAutoItems(self):
        """Returns list of items to be used for automatic configuration."""
        mods_prior_to_patch = load_order.cached_lower_loading_espms(
            patch_files.executing_patch, bosh.modInfos)
        return [mod for mod in mods_prior_to_patch if (
            mod in bosh.modInfos.mergeable and u'NoMerge' not in bosh.modInfos[
                mod].getBashTags())]

class _GmstTweakerPanel(_TweakPatcherPanel):

    #--Config Phase -----------------------------------------------------------
    # CONFIG DEFAULTS
    default_isEnabled = True
    def getConfig(self,configs):
        """Get config from configs dictionary and/or set to default."""
        config = super(_GmstTweakerPanel, self).getConfig(configs)
        # Load game specific tweaks
        tweaksAppend = self.tweaks.append # self.tweaks defined in super, empty
        for cls,tweaks in self.__class__.class_tweaks:
            for tweak in tweaks:
                if isinstance(tweak,tuple):
                    tweaksAppend(cls(*tweak))
                elif isinstance(tweak,list):
                    args = tweak[0]
                    kwdargs = tweak[1]
                    tweaksAppend(cls(*args,**kwdargs))
        self.tweaks.sort(key=lambda a: a.label.lower())
        for tweak in self.tweaks:
            tweak.get_tweak_config(config)

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
class AliasesPatcher(base.AliasesPatcher, _AliasesPatcherPanel): pass
class CBash_AliasesPatcher(base.CBash_AliasesPatcher, _AliasesPatcherPanel):
    def getConfig(self,configs):
        """Get config from configs dictionary and/or set to default."""
        config = super(CBash_AliasesPatcher,self).getConfig(configs)
        self.srcs = [] #so as not to fail screaming when determining load
        # mods - but with the least processing required. ##: NOT HERE !
        return config

class PatchMerger(base.PatchMerger, _MergerPanel): pass
class CBash_PatchMerger(base.CBash_PatchMerger, _MergerPanel): pass

# Patchers 20 -----------------------------------------------------------------
class GraphicsPatcher(importers.GraphicsPatcher, _ImporterPatcherPanel): pass
class CBash_GraphicsPatcher(importers.CBash_GraphicsPatcher,
                            _ImporterPatcherPanel): pass

class KFFZPatcher(importers.KFFZPatcher, _ImporterPatcherPanel): pass
class CBash_KFFZPatcher(importers.CBash_KFFZPatcher, _ImporterPatcherPanel): pass

class NPCAIPackagePatcher(importers.NPCAIPackagePatcher,
                          _ImporterPatcherPanel): pass
class CBash_NPCAIPackagePatcher(importers.CBash_NPCAIPackagePatcher,
                                _ImporterPatcherPanel): pass

class ActorImporter(importers.ActorImporter, _ImporterPatcherPanel): pass
class CBash_ActorImporter(importers.CBash_ActorImporter,
                          _ImporterPatcherPanel): pass

class DeathItemPatcher(importers.DeathItemPatcher, _ImporterPatcherPanel): pass
class CBash_DeathItemPatcher(importers.CBash_DeathItemPatcher,
                             _ImporterPatcherPanel): pass

class CellImporter(importers.CellImporter, _ImporterPatcherPanel): pass
class CBash_CellImporter(importers.CBash_CellImporter, _ImporterPatcherPanel): pass

class ImportFactions(importers.ImportFactions, _ImporterPatcherPanel): pass
class CBash_ImportFactions(importers.CBash_ImportFactions,
                           _ImporterPatcherPanel): pass

class ImportRelations(importers.ImportRelations, _ImporterPatcherPanel): pass
class CBash_ImportRelations(importers.CBash_ImportRelations,
                            _ImporterPatcherPanel): pass

class ImportInventory(importers.ImportInventory, _ImporterPatcherPanel): pass
class CBash_ImportInventory(importers.CBash_ImportInventory,
                            _ImporterPatcherPanel): pass

class ImportActorsSpells(importers.ImportActorsSpells, _ImporterPatcherPanel): pass
class CBash_ImportActorsSpells(importers.CBash_ImportActorsSpells,
                               _ImporterPatcherPanel): pass

class NamesPatcher(importers.NamesPatcher, _ImporterPatcherPanel): pass
class CBash_NamesPatcher(importers.CBash_NamesPatcher, _ImporterPatcherPanel): pass

class NpcFacePatcher(importers.NpcFacePatcher, _ImporterPatcherPanel): pass
class CBash_NpcFacePatcher(importers.CBash_NpcFacePatcher,
                           _ImporterPatcherPanel): pass

class RoadImporter(importers.RoadImporter, _ImporterPatcherPanel): pass
class CBash_RoadImporter(importers.CBash_RoadImporter, _ImporterPatcherPanel): pass

class SoundPatcher(importers.SoundPatcher, _ImporterPatcherPanel): pass
class CBash_SoundPatcher(importers.CBash_SoundPatcher, _ImporterPatcherPanel): pass

class StatsPatcher(importers.StatsPatcher, _ImporterPatcherPanel): pass
class CBash_StatsPatcher(importers.CBash_StatsPatcher, _ImporterPatcherPanel): pass

class ImportScripts(importers.ImportScripts, _ImporterPatcherPanel): pass
class CBash_ImportScripts(importers.CBash_ImportScripts,
                          _ImporterPatcherPanel): pass

class SpellsPatcher(importers.SpellsPatcher, _ImporterPatcherPanel): pass
class CBash_SpellsPatcher(importers.CBash_SpellsPatcher,
                          _ImporterPatcherPanel): pass

# Patchers 30 -----------------------------------------------------------------
class AssortedTweaker(multitweak_assorted.AssortedTweaker,
                      _TweakPatcherPanel): default_isEnabled = True
class CBash_AssortedTweaker(multitweak_assorted.CBash_AssortedTweaker,
                            _TweakPatcherPanel): default_isEnabled = True

class ClothesTweaker(multitweak_clothes.ClothesTweaker,
                     _TweakPatcherPanel): pass
class CBash_ClothesTweaker(multitweak_clothes.CBash_ClothesTweaker,
                           _TweakPatcherPanel): pass

class GmstTweaker(multitweak_settings.GmstTweaker, _GmstTweakerPanel): pass
class CBash_GmstTweaker(multitweak_settings.CBash_GmstTweaker,
                        _GmstTweakerPanel): pass

class NamesTweaker(multitweak_names.NamesTweaker, _TweakPatcherPanel): pass
class CBash_NamesTweaker(multitweak_names.CBash_NamesTweaker,
                         _TweakPatcherPanel): pass

class TweakActors(multitweak_actors.TweakActors, _TweakPatcherPanel): pass
class CBash_TweakActors(multitweak_actors.CBash_TweakActors,
                        _TweakPatcherPanel): pass

# Patchers 40 -----------------------------------------------------------------
class UpdateReferences(base.UpdateReferences, _ListPatcherPanel):
    canAutoItemCheck = False #--GUI: Whether new items are checked by default.
class CBash_UpdateReferences(base.CBash_UpdateReferences,
                             _ListPatcherPanel):
    canAutoItemCheck = False #--GUI: Whether new items are checked by default.

class RacePatcher(races_multitweaks.RacePatcher, _DoublePatcherPanel): pass
class CBash_RacePatcher(races_multitweaks.CBash_RacePatcher,
                        _DoublePatcherPanel): pass

class ListsMerger(special.ListsMerger, _ListsMergerPanel): pass
class CBash_ListsMerger(special.CBash_ListsMerger, _ListsMergerPanel): pass

class ContentsChecker(special.ContentsChecker, _PatcherPanel):
    default_isEnabled = True
class CBash_ContentsChecker(special.CBash_ContentsChecker, _PatcherPanel):
    default_isEnabled = True

#------------------------------------------------------------------------------
# Game specific GUI Patchers --------------------------------------------------
#------------------------------------------------------------------------------
from .patcher_dialog import PBash_gui_patchers, CBash_gui_patchers, \
    otherPatcherDict
# Dynamically create game specific UI patcher classes and add them to module's
# scope
from importlib import import_module
gamePatcher = import_module('.patcher', ##: move in bush.py !
                       package=bush.game_mod.__name__)
for patcher_name, typeInfo in gamePatcher.gameSpecificPatchers.items():
    globals()[patcher_name] = type(patcher_name, (typeInfo.clazz, _PatcherPanel), {})
    if typeInfo.twinPatcher:
        otherPatcherDict[patcher_name] = typeInfo.twinPatcher
for patcher_name, typeInfo in gamePatcher.gameSpecificListPatchers.items():
    globals()[patcher_name] = type(patcher_name, (typeInfo.clazz, _ListPatcherPanel), {})
    if typeInfo.twinPatcher:
        otherPatcherDict[patcher_name] = typeInfo.twinPatcher

del import_module

# Init Patchers
def initPatchers():
    PBash_gui_patchers.extend((globals()[x]() for x in bush.game.patchers))
    CBash_gui_patchers.extend((globals()[x]() for x in bush.game.CBash_patchers))
