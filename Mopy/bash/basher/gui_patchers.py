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
from __future__ import division
import copy
import re
from collections import defaultdict
from operator import itemgetter
# Internal
from .. import bass, bosh, bush, balt, load_order, bolt, exception
from ..balt import text_wrap, Links, SeparatorLink, CheckLink
from ..bolt import GPath
from ..gui import Button, CheckBox, HBoxedLayout, Label, LayoutOptions, \
    Spacer, TextArea, TOP, VLayout, EventResult, PanelWin, ListBox, \
    CheckListBox
from ..patcher import patch_files, patches_set, base

reCsvExt = re.compile(u'' r'\.csv$', re.I | re.U)

class _PatcherPanel(object):
    """Basic patcher panel with no options."""
    selectCommands = True # whether this panel displays De/Select All
    # CONFIG DEFAULTS
    default_isEnabled = False # is the patcher enabled on a new bashed patch ?
    patcher_type = None # type: base.Abstract_Patcher
    _patcher_txt = u'UNDEFINED'
    patcher_name = u'UNDEFINED'

    def __init__(self): # WIP- investigate why we instantiate gui patchers once
        self.gConfigPanel = None

    @property
    def patcher_tip(self):
        return re.sub(u'' r'\..*', u'.', self._patcher_txt.split(u'\n')[0],
                      flags=re.U)

    @property
    def patcher_text(self):
        return self.__class__._patcher_txt

    def SetIsFirstLoad(self,isFirstLoad):
        self.is_first_load = isFirstLoad

    def _EnsurePatcherEnabled(self):
        self.patch_dialog.CheckPatcher(self)
        self.isEnabled = True

    def _BoldPatcherLabel(self): self.patch_dialog.BoldPatcher(self)

    def _GetIsFirstLoad(self):
        if hasattr(self, 'is_first_load'):
            return self.is_first_load
        else:
            return False

    def GetConfigPanel(self, parent, config_layout, gTipText):
        """Show config.

        :type parent: basher.patcher_dialog.PatchDialog
        """
        if self.gConfigPanel: return self.gConfigPanel
        self.patch_dialog = parent
        self.gTipText = gTipText
        self.gConfigPanel = PanelWin(parent, no_border=False)
        self.main_layout = VLayout(
            item_expand=True, item_weight=1, spacing=4, items=[
                (Label(self.gConfigPanel, text_wrap(self._patcher_txt, 70)),
                 LayoutOptions(weight=0))])
        self.main_layout.apply_to(self.gConfigPanel)
        config_layout.add(self.gConfigPanel)
        return self.gConfigPanel

    def Layout(self):
        """Layout control components."""
        if self.gConfigPanel:
            self.gConfigPanel.pnl_layout()

    def _set_focus(self): # TODO(ut) check if set_focus is enough
        self.patch_dialog.gPatchers.set_focus_from_kb()

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
        humanName = self.__class__.patcher_name
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

    def get_patcher_instance(self, patch_file):
        """Instantiate and return an instance of self.__class__.patcher_type,
        initialized with the config options from the Gui"""
        return self.patcher_type(self.patcher_name, patch_file)

#------------------------------------------------------------------------------
class _AliasesPatcherPanel(_PatcherPanel):
    # CONFIG DEFAULTS
    default_aliases = {}
    patcher_name = _(u'Alias Mod Names')
    _patcher_txt = _(u'Specify mod aliases for reading CSV source files.')

    @property
    def patcher_tip(self): return u''

    def GetConfigPanel(self, parent, config_layout, gTipText):
        """Show config."""
        if self.gConfigPanel: return self.gConfigPanel
        gConfigPanel = super(_AliasesPatcherPanel, self).GetConfigPanel(parent,
            config_layout, gTipText)
        #gExample = Label(gConfigPanel,
        #    _(u"Example Mod 1.esp >> Example Mod 1.2.esp"))
        #--Aliases Text
        self.gAliases = TextArea(gConfigPanel)
        self.gAliases.on_focus_lost.subscribe(self.OnEditAliases)
        self.SetAliasText()
        #--Sizing
        self.main_layout.add((self.gAliases,
                              LayoutOptions(expand=True, weight=1)))
        return self.gConfigPanel

    def SetAliasText(self):
        """Sets alias text according to current aliases."""
        self.gAliases.text_content = u'\n'.join([
            u'%s >> %s' % (key.s,value.s) for key,value in sorted(self.aliases.items())])

    def OnEditAliases(self):
        aliases_text = self.gAliases.text_content
        self.aliases.clear()
        for line in aliases_text.split(u'\n'):
            fields = map(unicode.strip,line.split(u'>>'))
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

    def get_patcher_instance(self, patch_file):
        """Set patch_file aliases dict"""
        if self.isEnabled:
            patch_file.aliases = self.aliases
        return self.patcher_type(self.patcher_name, patch_file)

#------------------------------------------------------------------------------
class _ListPatcherPanel(_PatcherPanel):
    """Patcher panel with option to select source elements."""
    listLabel = _(u'Source Mods/Files')
    forceAuto = True
    forceItemCheck = False #--Force configChecked to True for all items
    canAutoItemCheck = True #--GUI: Whether new items are checked by default
    show_empty_sublist_checkbox = False
    # ADDITIONAL CONFIG DEFAULTS FOR LIST PATCHER
    default_autoIsChecked = True
    default_remove_empty_sublists = bush.game.fsName == u'Oblivion'
    default_configItems   = []
    default_configChecks  = {}
    default_configChoices = {}
    # Only for CBash patchers
    unloadedText = u'\n\n' + _(u'Any non-active, non-merged mods in the'
                               u' following list will be IGNORED.')
    @property
    def patcher_text(self):
        pt = self.__class__._patcher_txt
        try:
            if not self.patcher_type.allowUnloaded:
                pt += self.unloadedText
        except AttributeError:
            pass
        return pt

    def GetConfigPanel(self, parent, config_layout, gTipText):
        """Show config."""
        if self.gConfigPanel: return self.gConfigPanel
        gConfigPanel = super(_ListPatcherPanel, self).GetConfigPanel(
            parent, config_layout, gTipText)
        self.forceItemCheck = self.__class__.forceItemCheck
        self.selectCommands = self.__class__.selectCommands
        if self.forceItemCheck:
            self.gList = ListBox(gConfigPanel, isSingle=False)
        else:
            self.gList = CheckListBox(gConfigPanel, onCheck=self.OnListCheck)
        #--Manual controls
        if self.forceAuto:
            side_button_layout = None
            self.SetItems(self.getAutoItems())
        else:
            right_side_components = []
            if self.show_empty_sublist_checkbox:
                self.g_remove_empty = CheckBox(
                    gConfigPanel, _(u'Remove Empty Sublists'),
                    checked=self.remove_empty_sublists)
                self.g_remove_empty.on_checked.subscribe(
                    self._on_remove_empty_checked)
                right_side_components.extend([self.g_remove_empty])
            self.gAuto = CheckBox(gConfigPanel, _(u'Automatic'),
                                  checked=self.autoIsChecked)
            self.gAuto.on_checked.subscribe(self.OnAutomatic)
            self.gAdd = Button(gConfigPanel, _(u'Add'))
            self.gAdd.on_clicked.subscribe(self.OnAdd)
            self.gRemove = Button(gConfigPanel, _(u'Remove'))
            self.gRemove.on_clicked.subscribe(self.OnRemove)
            right_side_components.extend([self.gAuto, Spacer(4), self.gAdd,
                                          self.gRemove])
            self.OnAutomatic(self.autoIsChecked)
            side_button_layout = VLayout(
                spacing=4, items=right_side_components)
        self.main_layout.add(
            (HBoxedLayout(gConfigPanel, title=self.__class__.listLabel,
                          spacing=4, items=[
                (self.gList, LayoutOptions(expand=True, weight=1)),
                (side_button_layout, LayoutOptions(v_align=TOP)),
                (self._get_select_layout(), LayoutOptions(expand=True))]),
             LayoutOptions(expand=True, weight=1)))
        return gConfigPanel

    def _on_remove_empty_checked(self, is_checked):
        self.remove_empty_sublists = is_checked

    def _get_select_layout(self):
        if not self.selectCommands: return None
        self.gSelectAll = Button(self.gConfigPanel, _(u'Select All'))
        self.gSelectAll.on_clicked.subscribe(lambda: self.mass_select(True))
        self.gDeselectAll = Button(self.gConfigPanel, _(u'Deselect All'))
        self.gDeselectAll.on_clicked.subscribe(lambda: self.mass_select(False))
        return VLayout(spacing=4, items=[self.gSelectAll, self.gDeselectAll])

    def SetItems(self,items):
        """Set item to specified set of items."""
        items = self.items = self.sortConfig(items)
        forceItemCheck = self.forceItemCheck
        defaultItemCheck = self.__class__.canAutoItemCheck and bass.inisettings['AutoItemCheck']
        self.gList.lb_clear()
        isFirstLoad = self._GetIsFirstLoad()
        patcherOn = False
        patcherBold = False
        for index,item in enumerate(items):
            itemLabel = self.getItemLabel(item)
            self.gList.lb_insert(itemLabel, index)
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
                        self.gList.lb_bold_font_at_index(index)
                        patcherBold = True
                self.gList.lb_check_at_index(index,
                    self.configChecks.setdefault(
                        item, effectiveDefaultItemCheck))
        self.configItems = items
        if patcherOn:
            self._EnsurePatcherEnabled()
        if patcherBold:
            self._BoldPatcherLabel()

    def OnListCheck(self, lb_selection_dex=None):
        """One of list items was checked. Update all configChecks states."""
        ensureEnabled = False
        for index,item in enumerate(self.items):
            checked = self.gList.lb_is_checked_at_index(index)
            self.configChecks[item] = checked
            if checked:
                ensureEnabled = True
        if lb_selection_dex is not None:
            if self.gList.lb_is_checked_at_index(lb_selection_dex):
                self._EnsurePatcherEnabled()
        elif ensureEnabled:
            self._EnsurePatcherEnabled()

    def OnAutomatic(self, is_checked):
        """Automatic checkbox changed."""
        self.autoIsChecked = is_checked
        self.gAdd.enabled = not self.autoIsChecked
        self.gRemove.enabled = not self.autoIsChecked
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
            folder, fname = srcPath.headTail
            if folder == srcDir and fname not in self.configItems:
                self.configItems.append(fname)
        self.SetItems(self.configItems)

    def OnRemove(self):
        """Remove button clicked."""
        selections = self.gList.lb_get_selections()
        newItems = [item for index,item in enumerate(self.configItems) if index not in selections]
        self.SetItems(newItems)

    @staticmethod
    def sortConfig(items):
        """Return sorted items. Default assumes mods and sorts by load
        order."""
        return load_order.get_ordered(items)

    def mass_select(self, select=True):
        try:
            self.gList.set_all_checkmarks(checked=select)
            self.OnListCheck()
        except AttributeError:
            pass #ListBox instead of CheckListBox
        self._set_focus()

    #--Config Phase -----------------------------------------------------------
    def getConfig(self, configs):
        """Get config from configs dictionary and/or set to default."""
        config = super(_ListPatcherPanel, self).getConfig(configs)
        self.autoIsChecked = self.forceAuto or config.get(
            'autoIsChecked', self.__class__.default_autoIsChecked)
        self.remove_empty_sublists = config.get(
            'remove_empty_sublists',
            self.__class__.default_remove_empty_sublists)
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
                srcPath.s) and srcPath in patches_set())):
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
        config['remove_empty_sublists'] = self.remove_empty_sublists
        return config

    def getItemLabel(self,item):
        """Returns label for item to be used in list"""
        return u'%s' % item # Path or basestring - YAK

    def getAutoItems(self):
        """Returns list of items to be used for automatic configuration."""
        autoItems = self._get_auto_mods()
        reFile = re.compile(
            u'_(' + (u'|'.join(self.__class__.autoKey)) + r')\.csv$', re.U)
        for fileName in sorted(patches_set()):
            if reFile.search(fileName.s):
                autoItems.append(fileName)
        return autoItems

    def _get_auto_mods(self):
        mods_prior_to_patch = load_order.cached_lower_loading_espms(
            patch_files.executing_patch)
        return [mod for mod in mods_prior_to_patch if
                self.__class__.autoKey & bosh.modInfos[mod].getBashTags()]

    def _import_config(self, default=False):
        super(_ListPatcherPanel, self)._import_config(default)
        if default:
            self.SetItems(self.getAutoItems())
            return
        for index, item in enumerate(self.items):
            try:
                self.gList.lb_check_at_index(index, self.configChecks[item])
            except KeyError: # keys should be all bolt.Paths
                pass
                # bolt.deprint(_(u'item %s not in saved configs [%s]') % (
                #     item, u', '.join(map(repr, self.configChecks))))

    def get_patcher_instance(self, patch_file):
        patcher_sources = self._get_list_patcher_srcs(patch_file)
        return self.patcher_type(self.patcher_name, patch_file,
                                 patcher_sources)

    def _get_list_patcher_srcs(self, patch_file):
        patcher_sources = [x for x in self.configItems if self.configChecks[x]]
        return patcher_sources

#------------------------------------------------------------------------------
class _ChoiceMenuMixin(object):

    def _bind_mouse_events(self, right_click_list):
        # type: (CheckListBox | ListBox) -> None
        right_click_list.on_mouse_motion.subscribe(self._handle_mouse_motion)
        right_click_list.on_mouse_right_down.subscribe(self._right_mouse_click)
        right_click_list.on_mouse_right_up.subscribe(self._right_mouse_up)
        self.mouse_pos = None

    def _right_mouse_click(self, pos): self.mouse_pos = pos

    def _right_mouse_up(self, lb_selection_dex):
        if self.mouse_pos: self.ShowChoiceMenu(lb_selection_dex)
        # return

    def _handle_mouse_motion(self, wrapped_evt, lb_dex):
        """Check mouse motion to detect right click event."""
        if wrapped_evt.is_dragging: # cancel right up if user drags mouse away of the item
            if self.mouse_pos:
                oldx, oldy = self.mouse_pos
                x, y = wrapped_evt.evt_pos
                if max(abs(x - oldx), abs(y - oldy)) > 4:
                    self.mouse_pos = None
                return EventResult.FINISH ##: needed?
        else:
            self.mouse_pos = None

    def ShowChoiceMenu(self, lb_selection_dex): raise exception.AbstractError

class _TweakPatcherPanel(_ChoiceMenuMixin, _PatcherPanel):
    """Patcher panel with list of checkable, configurable tweaks."""
    tweak_label = _(u'Tweaks')

    def GetConfigPanel(self, parent, config_layout, gTipText):
        """Show config."""
        if self.gConfigPanel: return self.gConfigPanel
        gConfigPanel = super(_TweakPatcherPanel, self).GetConfigPanel(
            parent, config_layout, gTipText)
        self.gTweakList = CheckListBox(self.gConfigPanel,
                                       onCheck=self.TweakOnListCheck)
        #--Events
        self._bind_mouse_events(self.gTweakList)
        self.gTweakList.on_mouse_leaving.subscribe(self._mouse_leaving)
        self.mouse_dex = -1
        #--Layout
        self.main_layout.add(
            (HBoxedLayout(gConfigPanel, title=self.__class__.tweak_label,
                          item_expand=True, spacing=4, items=[
                    (self.gTweakList, LayoutOptions(weight=1)),
                    self._get_tweak_select_layout()]),
             LayoutOptions(expand=True, weight=1)))
        return gConfigPanel

    def _get_tweak_select_layout(self):
        if self.selectCommands:
            self.gTweakSelectAll = Button(self.gConfigPanel, _(u'Select All'))
            self.gTweakSelectAll.on_clicked.subscribe(
                lambda: self.mass_select(True))
            self.gTweakDeselectAll = Button(self.gConfigPanel,
                                            _(u'Deselect All'))
            self.gTweakDeselectAll.on_clicked.subscribe(
                lambda: self.mass_select(False))
            tweak_select_layout = VLayout(spacing=4, items=[
                self.gTweakSelectAll, self.gTweakDeselectAll])
        else: tweak_select_layout = None
        #--Init GUI
        self.SetTweaks()
        return tweak_select_layout

    @staticmethod
    def _label(label, value): # edit label text with value
        formatStr = u' %s' if isinstance(value, basestring) else u' %4.2f '
        return label + formatStr % value

    def SetTweaks(self):
        """Set item to specified set of items."""
        self.gTweakList.lb_clear()
        isFirstLoad = self._GetIsFirstLoad()
        patcherBold = False
        for index,tweak in enumerate(self._all_tweaks):
            label = tweak.getListLabel()
            if tweak.choiceLabels and tweak.choiceLabels[tweak.chosen].startswith(u'Custom'):
                label = self._label(label, tweak.choiceValues[tweak.chosen][0])
            self.gTweakList.lb_insert(label, index)
            self.gTweakList.lb_check_at_index(index, tweak.isEnabled)
            if not isFirstLoad and tweak.isNew():
                # indicate that this is a new item by bolding it and its parent patcher
                self.gTweakList.lb_bold_font_at_index(index)
                patcherBold = True
        if patcherBold:
            self._BoldPatcherLabel()

    def TweakOnListCheck(self, lb_selection_dex=None):
        """One of list items was checked. Update all check states."""
        ensureEnabled = False
        for index, tweak in enumerate(self._all_tweaks):
            checked = self.gTweakList.lb_is_checked_at_index(index)
            tweak.isEnabled = checked
            if checked:
                ensureEnabled = True
        if lb_selection_dex is not None:
            if self.gTweakList.lb_is_checked_at_index(lb_selection_dex):
                self._EnsurePatcherEnabled()
        elif ensureEnabled:
            self._EnsurePatcherEnabled()

    def _mouse_leaving(self):
            self.gTipText.label_text = u''
            self.mouse_pos = None

    def _handle_mouse_motion(self, wrapped_evt, lb_dex):
        """Check mouse motion to detect right click event. If any mouse button
         is held pressed, is_moving is False and is_dragging is True."""
        if wrapped_evt.is_moving:
            self.mouse_pos = None
            if lb_dex != self.mouse_dex:
                # Show tip text when changing item
                self.mouse_dex = lb_dex
                tip = 0 <= lb_dex < len(self._all_tweaks) and self._all_tweaks[
                    lb_dex].tweak_tip
                self.gTipText.label_text = tip or u''
        else:
            super(_TweakPatcherPanel, self)._handle_mouse_motion(wrapped_evt,
                                                                 lb_dex)

    def ShowChoiceMenu(self, tweakIndex):
        """Displays a popup choice menu if applicable."""
        if tweakIndex >= len(self._all_tweaks): return
        tweak = self._all_tweaks[tweakIndex]
        choiceLabels = tweak.choiceLabels
        if len(choiceLabels) <= 1: return
        self.gTweakList.lb_select_index(tweakIndex)
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
        links.new_menu(self.gTweakList, None)

    def tweak_choice(self, index, tweakIndex):
        """Handle choice menu selection."""
        self._all_tweaks[tweakIndex].chosen = index
        self.gTweakList.lb_set_label_at_index(tweakIndex, self._all_tweaks[tweakIndex].getListLabel())
        self.gTweakList.lb_check_at_index(tweakIndex, True) # wx.EVT_CHECKLISTBOX is NOT
        self.TweakOnListCheck() # fired so this line is needed (?)

    _msg = _(u'Enter the desired custom tweak value.') + u'\n' + _(
        u'Due to an inability to get decimal numbers from the wxPython '
        u'prompt please enter an extra zero after your choice if it is not '
        u'meant to be a decimal.') + u'\n' + _(
        u'If you are trying to enter a decimal multiply it by 10, '
        u'for example for 0.3 enter 3 instead.')

    def tweak_custom_choice(self, index, tweakIndex):
        """Handle choice menu selection."""
        tweak = self._all_tweaks[tweakIndex]
        value = []
        for i, v in enumerate(tweak.choiceValues[index]):
            if isinstance(v,float):
                label = self._msg + u'\n' + tweak.key[i]
                new = balt.askNumber(
                    self.gConfigPanel, label, prompt=_(u'Value'),
                    title=tweak.tweak_name + _(u' ~ Custom Tweak Value'),
                    value=tweak.choiceValues[index][i], min=-10000, max=10000)
                if new is None: #user hit cancel
                    return
                value.append(float(new)/10)
            elif isinstance(v,int):
                label = _(u'Enter the desired custom tweak value.') + u'\n' + \
                        tweak.key[i]
                new = balt.askNumber(
                    self.gConfigPanel, label, prompt=_(u'Value'),
                    title=tweak.tweak_name + _(u' ~ Custom Tweak Value'),
                    value=tweak.choiceValues[index][i], min=-10000, max=10000)
                if new is None: #user hit cancel
                    return
                value.append(new)
            elif isinstance(v,basestring):
                label = _(u'Enter the desired custom tweak text.') + u'\n' + \
                        tweak.key[i]
                new = balt.askText(
                    self.gConfigPanel, label,
                    title=tweak.tweak_name + _(u' ~ Custom Tweak Text'),
                    default=tweak.choiceValues[index][i], strip=False) ##: strip ?
                if new is None: #user hit cancel
                    return
                value.append(new)
        if not value: value = tweak.choiceValues[index]
        tweak.choiceValues[index] = tuple(value)
        tweak.chosen = index
        label = self._label(tweak.getListLabel(), tweak.choiceValues[index][0])
        self.gTweakList.lb_set_label_at_index(tweakIndex, label)
        self.gTweakList.lb_check_at_index(tweakIndex, True) # wx.EVT_CHECKLISTBOX is NOT
        self.TweakOnListCheck() # fired so this line is needed (?)

    def mass_select(self, select=True):
        """'Select All' or 'Deselect All' button was pressed, update all
        configChecks states."""
        super(_TweakPatcherPanel, self).mass_select(select)
        try:
            self.gTweakList.set_all_checkmarks(checked=select)
            self.TweakOnListCheck()
        except AttributeError:
            pass #ListBox instead of CheckListBox
        self._set_focus()

    #--Config Phase -----------------------------------------------------------
    def getConfig(self, configs):
        """Get config from configs dictionary and/or set to default."""
        config = super(_TweakPatcherPanel, self).getConfig(configs)
        self._all_tweaks = self.patcher_type.tweak_instances()
        for tweak in self._all_tweaks:
            tweak.init_tweak_config(config)
        return config

    def saveConfig(self, configs):
        """Save config to configs dictionary."""
        config = super(_TweakPatcherPanel, self).saveConfig(configs)
        for tweak in self._all_tweaks:
            tweak.save_tweak_config(config)
        return config

    def _log_config(self, conf, config, clip, log):
        self.getConfig(config) # set self._all_tweaks and load their config
        for tweak in self._all_tweaks:
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
        for index, tweakie in enumerate(self._all_tweaks):
            try:
                self.gTweakList.lb_check_at_index(index, tweakie.isEnabled)
                self.gTweakList.lb_set_label_at_index(index, tweakie.getListLabel())
            except KeyError: pass # no such key don't spam the log
            except: bolt.deprint(_(u'Error importing Bashed patch '
                u'configuration. Item %s skipped.') % tweakie, traceback=True)

    def get_patcher_instance(self, patch_file):
        enabledTweaks = [t for t in self._all_tweaks if t.isEnabled]
        return self.patcher_type(self.patcher_name, patch_file, enabledTweaks)

#------------------------------------------------------------------------------
class _DoublePatcherPanel(_TweakPatcherPanel, _ListPatcherPanel):
    """Only used in Race Patcher which features a double panel (source mods
    and tweaks)."""
    listLabel = _(u'Race Mods')
    tweak_label = _(u'Race Tweaks')
    # CONFIG DEFAULTS
    default_isEnabled = True # isActive will be set to True in initPatchFile

    def GetConfigPanel(self, parent, config_layout, gTipText):
        """Show config."""
        if self.gConfigPanel: return self.gConfigPanel
        gConfigPanel = super(_DoublePatcherPanel, self).GetConfigPanel(parent,
            config_layout, gTipText)
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

    def get_patcher_instance(self, patch_file):
        enabledTweaks = [t for t in self._all_tweaks if t.isEnabled]
        patcher_sources = [x for x in self.configItems if self.configChecks[x]]
        return self.patcher_type(self.patcher_name, patch_file,
                                 patcher_sources, enabledTweaks)

#------------------------------------------------------------------------------
class _ImporterPatcherPanel(_ListPatcherPanel):

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

    def GetConfigPanel(self, parent, config_layout, gTipText):
        if self.gConfigPanel: return self.gConfigPanel
        gConfigPanel = super(_ListsMergerPanel, self).GetConfigPanel(
            parent, config_layout, gTipText)
        self._bind_mouse_events(self.gList)
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

    def ShowChoiceMenu(self, itemIndex):
        """Displays a popup choice menu if applicable.
        NOTE: Assume that configChoice returns a set of chosen items."""
        #--Item Index
        if itemIndex < 0: return
        self.gList.lb_select_index(itemIndex)
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
            self.gList.lb_set_label_at_index(itemIndex, self.getItemLabel(item))
        links = Links()
        for index,label in enumerate(self.choiceMenu):
            if label == u'----':
                links.append(SeparatorLink())
            else:
                links.append(_OnItemChoice(label, index))
        #--Show/Destroy Menu
        links.new_menu(self.gList, None)

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
            patch_files.executing_patch)
        return [mod for mod in mods_prior_to_patch if (
            mod in bosh.modInfos.mergeable and u'NoMerge' not in bosh.modInfos[
                mod].getBashTags())]

class _GmstTweakerPanel(_TweakPatcherPanel):
    # CONFIG DEFAULTS
    default_isEnabled = True

#------------------------------------------------------------------------------
# GUI Patcher classes
# Do _not_ rename the gui patcher classes or you will break existing BP configs
#------------------------------------------------------------------------------
from ..patcher.patchers import base
from ..patcher.patchers import importers
from ..patcher.patchers import multitweak_actors, multitweak_assorted, \
    multitweak_clothes, multitweak_names, multitweak_settings, \
    races_multitweaks
from ..patcher.patchers import special

# Patchers 10 -----------------------------------------------------------------
class AliasesPatcher(_AliasesPatcherPanel): patcher_type = base.AliasesPatcher
class CBash_AliasesPatcher(_AliasesPatcherPanel):
    patcher_type = base.CBash_AliasesPatcher

class _APatchMerger(_MergerPanel):
    """Merges specified patches into Bashed Patch."""
    patcher_name = _(u'Merge Patches')
    _patcher_txt = _(u'Merge patch mods into Bashed Patch.')
    autoKey = {u'Merge'}

class PatchMerger(_APatchMerger): patcher_type = base.PatchMerger
class CBash_PatchMerger(_APatchMerger): patcher_type = base.CBash_PatchMerger

# Patchers 20 -----------------------------------------------------------------
class _AGraphicsPatcher(_ImporterPatcherPanel):
    """Merges changes to graphics (models and icons)."""
    patcher_name = _(u'Import Graphics')
    _patcher_txt = _(u'Import graphics (models, icons, etc.) from source '
                     u'mods.')
    autoKey = {u'Graphics'}

class GraphicsPatcher(_AGraphicsPatcher):
    patcher_type = importers.GraphicsPatcher
class CBash_GraphicsPatcher(_AGraphicsPatcher):
    patcher_type = importers.CBash_GraphicsPatcher

# -----------------------------------------------------------------------------
class _AKFFZPatcher(_ImporterPatcherPanel):
    """Merges changes to actor animation lists."""
    patcher_name = _(u'Import Actors: Animations')
    _patcher_txt = _(u'Import actor animations from source mods.')
    autoKey = {u'Actors.Anims'}

class KFFZPatcher(_AKFFZPatcher):
    patcher_type = importers.KFFZPatcher
class CBash_KFFZPatcher(_AKFFZPatcher):
    patcher_type = importers.CBash_KFFZPatcher

# -----------------------------------------------------------------------------
class _ANPCAIPackagePatcher(_ImporterPatcherPanel):
    """Merges changes to the AI Packages of Actors."""
    patcher_name = _(u'Import Actors: AI Packages')
    _patcher_txt = _(u'Import actor AI Package links from source mods.')
    autoKey = {u'Actors.AIPackages', u'Actors.AIPackagesForceAdd'}

class NPCAIPackagePatcher(_ANPCAIPackagePatcher):
    patcher_type = importers.NPCAIPackagePatcher
class CBash_NPCAIPackagePatcher(_ANPCAIPackagePatcher):
    patcher_type = importers.CBash_NPCAIPackagePatcher

# -----------------------------------------------------------------------------
class _AActorImporter(_ImporterPatcherPanel):
    """Merges changes to actors."""
    patcher_name = _(u'Import Actors')
    _patcher_txt = _(u'Import various actor attributes from source mods.')
    autoKey = bush.game.actor_importer_auto_key

class ActorImporter(_AActorImporter):
    patcher_type = importers.ActorImporter
class CBash_ActorImporter(_AActorImporter):
    patcher_type = importers.CBash_ActorImporter
    patcher_type.autoKey = _AActorImporter.autoKey ##: autoKey hack

# -----------------------------------------------------------------------------
class _ADeathItemPatcher(_ImporterPatcherPanel):
    """Merges changes to actor death items."""
    patcher_name = _(u'Import Actors: Death Items')
    _patcher_txt = _(u'Import actor death items from source mods.')
    autoKey = {u'Actors.DeathItem'}

class DeathItemPatcher(_ADeathItemPatcher):
    patcher_type = importers.DeathItemPatcher
class CBash_DeathItemPatcher(_ADeathItemPatcher):
    patcher_type = importers.CBash_DeathItemPatcher

# -----------------------------------------------------------------------------
class _ACellImporter(_ImporterPatcherPanel):
    """Merges changes to cells (climate, lighting, and water.)"""
    _patcher_txt = _(u'Import cells (climate, lighting, and water) from '
                     u'source mods.')
    patcher_name = _(u'Import Cells')

class CellImporter(_ACellImporter):
    patcher_type = importers.CellImporter
    autoKey = bush.game.cellAutoKeys
class CBash_CellImporter(_ACellImporter):
    autoKey = {u'C.Climate', u'C.Light', u'C.Water', u'C.Owner', u'C.Name',
               u'C.RecordFlags', u'C.Music'}  #,u'C.Maps'
    patcher_type = importers.CBash_CellImporter
    patcher_type.autoKey = autoKey ##: autoKey hack

# -----------------------------------------------------------------------------
class _AImportFactions(_ImporterPatcherPanel):
    """Import factions to creatures and NPCs."""
    patcher_name = _(u'Import Factions')
    _patcher_txt = _(u'Import factions from source mods/files.')
    autoKey = {u'Factions'}

class ImportFactions(_AImportFactions):
    patcher_type = importers.ImportFactions
class CBash_ImportFactions(_AImportFactions):
    patcher_type = importers.CBash_ImportFactions

# -----------------------------------------------------------------------------
class _AImportRelations(_ImporterPatcherPanel):
    """Import faction relations to factions."""
    patcher_name = _(u'Import Relations')
    _patcher_txt = _(u'Import relations from source mods/files.')
    autoKey = {u'Relations'}

class ImportRelations(_AImportRelations):
    patcher_type = importers.ImportRelations
class CBash_ImportRelations(_AImportRelations):
    patcher_type = importers.CBash_ImportRelations

# -----------------------------------------------------------------------------
class _AImportInventory(_ImporterPatcherPanel):
    """Merge changes to actor inventories."""
    patcher_name = _(u'Import Inventory')
    _patcher_txt = _(u'Merges changes to NPC, creature and container '
                     u'inventories.')
    autoKey = {u'Invent', u'InventOnly'}

class ImportInventory(_AImportInventory):
    patcher_type = importers.ImportInventory
class CBash_ImportInventory(_AImportInventory):
    patcher_type = importers.CBash_ImportInventory

# -----------------------------------------------------------------------------
class _AImportActorsSpells(_ImporterPatcherPanel):
    """Merges changes to the spells lists of Actors."""
    patcher_name = _(u'Import Actors: Spells')
    _patcher_txt = _(u'Merges changes to actor spell / effect lists.')
    autoKey = {u'Actors.Spells', u'Actors.SpellsForceAdd'}

class ImportActorsSpells(_AImportActorsSpells):
    patcher_type = importers.ImportActorsSpells
class CBash_ImportActorsSpells(_AImportActorsSpells):
    patcher_type = importers.CBash_ImportActorsSpells

# -----------------------------------------------------------------------------
class _ANamesPatcher(_ImporterPatcherPanel):
    """Import names from source mods/files."""
    patcher_name = _(u'Import Names')
    _patcher_txt = _(u'Import names from source mods/files.')
    autoKey = {u'Names'}

class NamesPatcher(_ANamesPatcher):
    patcher_type = importers.NamesPatcher
class CBash_NamesPatcher(_ANamesPatcher):
    patcher_type = importers.CBash_NamesPatcher

# -----------------------------------------------------------------------------
class _ANpcFacePatcher(_ImporterPatcherPanel):
    """NPC Faces patcher, for use with TNR or similar mods."""
    patcher_name = _(u'Import NPC Faces')
    _patcher_txt = _(u'Import NPC face/eyes/hair from source mods. For use '
                     u'with TNR and similar mods.')
    autoKey = {u'NpcFaces', u'NpcFacesForceFullImport', u'Npc.HairOnly',
               u'Npc.EyesOnly'}

    def _get_auto_mods(self, autoRe=re.compile(u'^TNR .*.esp$', re.I | re.U)):
        """Pick TNR esp if present in addition to appropriately tagged mods."""
        mods_prior_to_patch = load_order.cached_lower_loading_espms(
            patch_files.executing_patch)
        return [mod for mod in mods_prior_to_patch if autoRe.match(mod.s) or (
            self.__class__.autoKey & bosh.modInfos[mod].getBashTags())]

class NpcFacePatcher(_ANpcFacePatcher):
    patcher_type = importers.NpcFacePatcher
class CBash_NpcFacePatcher(_ANpcFacePatcher):
    patcher_type = importers.CBash_NpcFacePatcher

# -----------------------------------------------------------------------------
class _ASoundPatcher(_ImporterPatcherPanel):
    """Imports sounds from source mods into patch."""
    patcher_name = _(u'Import Sounds')
    autoKey = {u'Sound'}

class SoundPatcher(_ASoundPatcher):
    _patcher_txt = _(u'Import sounds (from Magic Effects, Containers, '
                     u'Activators, Lights, Weathers and Doors) from source '
                     u'mods.')
    patcher_type = importers.SoundPatcher
class CBash_SoundPatcher(_ASoundPatcher):
    _patcher_txt = _(u'Import sounds (from Activators, Containers, Creatures, '
                     u'Doors, Lights, Magic Effects and Weathers) from source '
                     u'mods.')
    patcher_type = importers.CBash_SoundPatcher

# -----------------------------------------------------------------------------
class _AStatsPatcher(_ImporterPatcherPanel):
    """Import stats from mod file."""
    patcher_name = _(u'Import Stats')
    _patcher_txt = _(u'Import stats from any pickupable items from source '
                     u'mods/files.')
    autoKey = {u'Stats'}

class StatsPatcher(_AStatsPatcher):
    patcher_type = importers.StatsPatcher
class CBash_StatsPatcher(_AStatsPatcher):
    patcher_type = importers.CBash_StatsPatcher

# -----------------------------------------------------------------------------
class _AImportScripts(_ImporterPatcherPanel):
    """Imports attached scripts on objects."""
    patcher_name = _(u'Import Scripts')
    _patcher_txt = _(u'Import scripts on various objects (e.g. containers, '
                     u'weapons, etc.) from source mods.')
    autoKey = {u'Scripts'}

class ImportScripts(_AImportScripts):
    patcher_type = importers.ImportScripts
class CBash_ImportScripts(_AImportScripts):
    patcher_type = importers.CBash_ImportScripts

# -----------------------------------------------------------------------------
class _ASpellsPatcher(_ImporterPatcherPanel):
    """Import spell changes from mod files."""
    patcher_name = _(u'Import Spell Stats')
    _patcher_txt = _(u'Import stats from any spells / actor effects from '
                     u'source mods/files.')
    autoKey = {u'Spells', u'SpellStats'}

class SpellsPatcher(_ASpellsPatcher):
    patcher_type = importers.SpellsPatcher
class CBash_SpellsPatcher(_ASpellsPatcher):
    patcher_type = importers.CBash_SpellsPatcher

# Non CBash Importers----------------------------------------------------------
class DestructiblePatcher(_ImporterPatcherPanel):
    patcher_name = _(u'Import Destructible')
    _patcher_txt = _(u'Preserves changes to destructible records.\n\nWill '
                     u'have to use if a mod that allows you to destroy part '
                     u'of the environment is installed and active.')
    autoKey = {u'Destructible'}
    patcher_type = importers.DestructiblePatcher

class WeaponModsPatcher(_ImporterPatcherPanel):
    patcher_name = _(u'Import Weapon Modifications')
    _patcher_txt = _(u'Merges changes to weapon modifications.')
    autoKey = {u'WeaponMods'}
    patcher_type = importers.WeaponModsPatcher

class KeywordsImporter(_ImporterPatcherPanel):
    patcher_name = _(u'Import Keywords')
    _patcher_txt = _(u'Import keyword changes from source mods.')
    autoKey = {u'Keywords'}
    patcher_type = importers.KeywordsImporter

class TextImporter(_ImporterPatcherPanel):
    patcher_name = _(u'Import Text')
    _patcher_txt = _(u'Import various types of long-form text like book '
                     u'texts, effect descriptions, etc. from source mods.')
    autoKey = {u'Text'}
    patcher_type = importers.TextImporter

class ObjectBoundsImporter(_ImporterPatcherPanel):
    patcher_name = _(u'Import Object Bounds')
    _patcher_txt = _(u'Import object bounds for various actors, items and '
                     u'objects.')
    autoKey = {u'ObjectBounds'}
    patcher_type = importers.ObjectBoundsImporter

# Patchers 30 -----------------------------------------------------------------
class AssortedTweaker(_TweakPatcherPanel):
    patcher_name = _(u'Tweak Assorted')
    _patcher_txt = _(u'Tweak various records in miscellaneous ways.')
    patcher_type = multitweak_assorted.AssortedTweaker
    default_isEnabled = True
class CBash_AssortedTweaker(_TweakPatcherPanel):
    patcher_name = _(u'Tweak Assorted')
    _patcher_txt = _(u'Tweak various records in miscellaneous ways.')
    patcher_type = multitweak_assorted.CBash_AssortedTweaker
    default_isEnabled = True

class ClothesTweaker(_TweakPatcherPanel):
    patcher_name = _(u'Tweak Clothes')
    _patcher_txt = _(u'Tweak clothing weight and blocking.')
    patcher_type = multitweak_clothes.ClothesTweaker
class CBash_ClothesTweaker(_TweakPatcherPanel):
    patcher_name = _(u'Tweak Clothes')
    _patcher_txt = _(u'Tweak clothing weight and blocking.')
    patcher_type = multitweak_clothes.CBash_ClothesTweaker

class GmstTweaker(_GmstTweakerPanel):
    patcher_name = _(u'Tweak Settings')
    _patcher_txt = _(u'Tweak game settings.')
    patcher_type = multitweak_settings.GmstTweaker
class CBash_GmstTweaker(_GmstTweakerPanel):
    patcher_name = _(u'Tweak Settings')
    _patcher_txt = _(u'Tweak game settings.')
    patcher_type = multitweak_settings.CBash_GmstTweaker

class _ANamesTweaker(_TweakPatcherPanel):
    patcher_name = _(u'Tweak Names')
    _patcher_txt = _(u'Tweak object names in various ways such as lore '
                     u'friendliness or show type/quality.')

class NamesTweaker(_ANamesTweaker):
    patcher_type = multitweak_names.NamesTweaker
class CBash_NamesTweaker(_ANamesTweaker):
    patcher_type = multitweak_names.CBash_NamesTweaker

class TweakActors(_TweakPatcherPanel):
    patcher_name = _(u'Tweak Actors')
    _patcher_txt = _(u'Tweak NPC and Creatures records in specified ways.')
    patcher_type = multitweak_actors.TweakActors
class CBash_TweakActors(_TweakPatcherPanel):
    patcher_name = _(u'Tweak Actors')
    _patcher_txt = _(u'Tweak NPC and Creatures records in specified ways.')
    patcher_type = multitweak_actors.CBash_TweakActors

# Patchers 40 -----------------------------------------------------------------
class _AUpdateReferences(_ListPatcherPanel):
    """Imports Form Id replacers into the Bashed Patch."""
    patcher_name = _(u'Replace Form IDs')
    _patcher_txt = _(u'Imports Form Id replacers from csv files into the '
                     u'Bashed Patch.')
    autoKey = {u'Formids'}

class UpdateReferences(_AUpdateReferences):
    patcher_type = base.UpdateReferences
    canAutoItemCheck = False #--GUI: Whether new items are checked by default.
class CBash_UpdateReferences(_AUpdateReferences):
    patcher_type = base.CBash_UpdateReferences
    canAutoItemCheck = False #--GUI: Whether new items are checked by default.

class _ARacePatcher(_DoublePatcherPanel):
    """Merged leveled lists mod file."""
    patcher_name = _(u'Race Records')
    _patcher_txt = u'\n\n'.join([
        _(u'Merge race eyes, hair, body, voice from ACTIVE AND/OR MERGED '
          u'mods.  Any non-active, non-merged mods in the following list '
          u'will be IGNORED.'),
        _(u'Even if none of the below mods are checked, this will sort '
          u'hairs and eyes and attempt to remove googly eyes from all '
          u'active mods.  It will also randomly assign hairs and eyes to '
          u'npcs that are otherwise missing them.')]
    )
    autoKey = {u'R.Head', u'R.Ears', u'Eyes',
               u'Voice-F', u'R.ChangeSpells', u'R.Teeth', u'Voice-M',
               u'R.Attributes-M', u'R.Attributes-F', u'Body-F', u'Body-M',
               u'R.Mouth', u'R.Description', u'R.AddSpells', u'Body-Size-F',
               u'R.Relations', u'Body-Size-M', u'R.Skills', u'Hair'}

    @property
    def patcher_tip(self):
        return _(u'Merge race eyes, hair, body, voice from mods.')

class RacePatcher(_ARacePatcher):
    patcher_type = races_multitweaks.RacePatcher
class CBash_RacePatcher(_ARacePatcher):
    patcher_type = races_multitweaks.CBash_RacePatcher

class _AListsMerger(_ListsMergerPanel):
    """Merged leveled lists mod file."""
    patcher_name = _(u'Leveled Lists')
    _patcher_txt = u'\n\n'.join([
        _(u'Merges changes to leveled lists from ACTIVE/MERGED MODS ONLY.'),
        _(u'Advanced users may override Relev/Delev tags for any mod (active '
          u'or inactive) using the list below.')])
    autoKey = {u'Delev', u'Relev'}

    @property
    def patcher_tip(self):
        return _(u'Merges changes to leveled lists from all active mods.')

    def get_patcher_instance(self, patch_file):
        patcher_sources = self._get_list_patcher_srcs(patch_file)
        return self.patcher_type(self.patcher_name, patch_file,
                                 patcher_sources,
                                 self.remove_empty_sublists,
                                 defaultdict(tuple, self.configChoices))

class ListsMerger(_AListsMerger):
    patcher_type = special.ListsMerger
    show_empty_sublist_checkbox = True
class CBash_ListsMerger(_AListsMerger):
    patcher_type = special.CBash_ListsMerger
    show_empty_sublist_checkbox = True

class FidListsMerger(_AListsMerger):
    patcher_name = _(u'FormID Lists')
    _patcher_txt = u'\n\n'.join([
        _(u'Merges changes to formid lists from ACTIVE/MERGED MODS ONLY.') ,
        _(u'Advanced users may override Deflst tags for any mod (active or '
          u'inactive) using the list below.')])
    autoKey = {u'Deflst'}
    patcher_type = special.FidListsMerger
    listLabel = _(u'Override Deflst Tags')
    forceItemCheck = False #--Force configChecked to True for all items
    choiceMenu = (u'Auto', u'----', u'Deflst')
    # CONFIG DEFAULTS
    default_isEnabled = False

    @property
    def patcher_tip(self):
        return _(u'Merges changes to formid lists from all active mods.')

class _AContentsChecker(_PatcherPanel):
    """Checks contents of leveled lists, inventories and containers for
    correct content types."""
    patcher_name = _(u'Contents Checker')
    _patcher_txt = _(u'Checks contents of leveled lists, inventories and '
                     u'containers for correct types.')
    default_isEnabled = True

class ContentsChecker(_AContentsChecker):
    patcher_type = special.ContentsChecker
class CBash_ContentsChecker(_AContentsChecker):
    patcher_type = special.CBash_ContentsChecker

#------------------------------------------------------------------------------
# Game specific GUI Patchers --------------------------------------------------
#------------------------------------------------------------------------------
from .patcher_dialog import PBash_gui_patchers, CBash_gui_patchers, \
    otherPatcherDict
# Dynamically create game specific UI patcher classes and add them to module's
# scope
# Patchers with no options
for patcher_name, p_info in bush.game.gameSpecificPatchers.items():
    globals()[patcher_name] = type(patcher_name, (_PatcherPanel,),
                                   p_info.cls_vars)
    if p_info.twin_patcher:
        otherPatcherDict[patcher_name] = p_info.twin_patcher
# Simple list patchers
for patcher_name, p_info in bush.game.gameSpecificListPatchers.items():
    globals()[patcher_name] = type(patcher_name, (_ListPatcherPanel,),
                                   p_info.cls_vars)
    if p_info.twin_patcher:
        otherPatcherDict[patcher_name] = p_info.twin_patcher
# Import patchers
for patcher_name, p_info in bush.game.game_specific_import_patchers.items():
    globals()[patcher_name] = type(patcher_name, (_ImporterPatcherPanel,),
                                   p_info.cls_vars)
    if p_info.twin_patcher:
        otherPatcherDict[patcher_name] = p_info.twin_patcher

# Init Patchers
def initPatchers():
    PBash_gui_patchers.extend((globals()[x]() for x in bush.game.patchers))
    CBash_gui_patchers.extend((globals()[x]() for x in bush.game.CBash_patchers))
