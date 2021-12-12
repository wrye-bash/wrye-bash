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

import copy
import re
from collections import defaultdict
from itertools import chain
# Internal
from .. import bass, bosh, bush, balt, load_order, bolt, exception
from ..balt import Links, SeparatorLink, CheckLink
from ..bolt import GPath, text_wrap, dict_sort
from ..gui import Button, CheckBox, HBoxedLayout, Label, LayoutOptions, \
    Spacer, TextArea, TOP, VLayout, EventResult, PanelWin, ListBox, \
    CheckListBox, DeselectAllButton, SelectAllButton, FileOpenMultiple
from ..patcher import patch_files, patches_set, base

reCsvExt = re.compile(r'\.csv$', re.I | re.U)

class _PatcherPanel(object):
    """Basic patcher panel with no options."""
    patcher_name = u'UNDEFINED'
    patcher_desc = u'UNDEFINED'
    autoKey = set()
    # The key that will be used to read and write entries for BP configs
    # These are sometimes quite ugly - backwards compat leftover from when
    # those were the class names and got written directly into the configs
    _config_key = None # type: str
    patcher_type = None # type: base.Abstract_Patcher
    # CONFIG DEFAULTS
    default_isEnabled = False # is the patcher enabled on a new bashed patch ?
    selectCommands = True # whether this panel displays De/Select All

    def __init__(self): # WIP- investigate why we instantiate gui patchers once
        if not self.__class__._config_key:
            raise SyntaxError(u'No _config_key set for patcher panel class '
                              u'%s' % self.__class__.__name__)
        self.gConfigPanel = None
        # Used to keep track of the state of the patcher label
        self._is_bolded = False
        self._is_slanted = False

    @property
    def patcher_tip(self):
        # Remove everything but the first sentence from the first line of the
        # patcher description
        return re.sub(r'\..*', u'.', self.patcher_desc.split(u'\n')[0],
                      flags=re.U)

    def SetIsFirstLoad(self,isFirstLoad):
        self.is_first_load = isFirstLoad

    def _enable_self(self, self_enabled=True):
        """Enables or disables this patcher and notifies the patcher dialog."""
        self.isEnabled = self_enabled
        self.patch_dialog.check_patcher(self, self_enabled)

    def _style_patcher_label(self, bold=False, slant=False):
        self._is_bolded |= bold
        self._is_slanted |= slant
        self.patch_dialog.style_patcher(self, bold=self._is_bolded,
                                        slant=self._is_slanted)

    def _GetIsFirstLoad(self):
        return getattr(self, u'is_first_load', False)

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
                (Label(self.gConfigPanel, text_wrap(self.patcher_desc, 70)),
                 LayoutOptions(weight=0))])
        self.main_layout.apply_to(self.gConfigPanel)
        config_layout.add(self.gConfigPanel)
        # Bold the patcher if it's new, but the patch itself isn't new
        if not self._was_present and not self._GetIsFirstLoad():
            self._style_patcher_label(bold=True)
        return self.gConfigPanel

    def Layout(self):
        """Layout control components."""
        if self.gConfigPanel:
            self.gConfigPanel.update_layout()

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
        # Remember whether we were present in the config for bolding later
        self._was_present = self.__class__._config_key in configs
        config = (configs[self.__class__._config_key]
                  if self._was_present else {})
        self.isEnabled = config.get(u'isEnabled',
                                    self.__class__.default_isEnabled)
        # return the config dict for this patcher to read additional values
        return config

    def saveConfig(self, configs):
        """Save config to configs dictionary.

        Most patchers just save their enabled state, except the
        _ListPatcherPanel subclasses - which save their choices - and the
        AliasModNames that saves the aliases."""
        config = configs[self.__class__._config_key] = {}
        config[u'isEnabled'] = self.isEnabled
        return config # return the config dict for this patcher to further edit

    def log_config(self, config, clip, log):
        ckey = self.__class__._config_key
        humanName = self.__class__.patcher_name
        # Patcher in the config?
        if ckey not in config: return
        # Patcher active?
        conf = config[ckey]
        if not conf.get(u'isEnabled', False): return
        # Active
        log.setHeader(u'== ' + humanName)
        clip.write(u'\n')
        clip.write(u'== ' + humanName + u'\n')
        self._log_config(conf, config, clip, log)

    def _log_config(self, conf, config, clip, log):
        items = conf.get(u'configItems', [])
        if len(items) == 0:
            log(u' ')
        for item in conf.get(u'configItems', []):
            checks = conf.get(u'configChecks', {})
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

    def mass_select(self, select=True):
        self._enable_self(select)

    def get_patcher_instance(self, patch_file):
        """Instantiate and return an instance of self.__class__.patcher_type,
        initialized with the config options from the Gui"""
        return self.patcher_type(self.patcher_name, patch_file)

#------------------------------------------------------------------------------
class _AliasesPatcherPanel(_PatcherPanel):
    patcher_name = _(u'Alias Mod Names')
    patcher_desc = _(u'Specify mod aliases for reading CSV source files.')

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
            u'%s >> %s' % (alias_target, alias_repl)
            for alias_target, alias_repl in dict_sort(self._ci_aliases)])

    def OnEditAliases(self):
        aliases_text = self.gAliases.text_content
        self._ci_aliases.clear()
        for line in aliases_text.split(u'\n'):
            fields = [s.strip() for s in line.split(u'>>')]
            if len(fields) != 2 or not fields[0] or not fields[1]: continue
            self._ci_aliases[GPath(fields[0])] = GPath(fields[1])
        self.SetAliasText()

    #--Config Phase -----------------------------------------------------------
    def getConfig(self, configs):
        """Get config from configs dictionary and/or set to default."""
        config = super(_AliasesPatcherPanel, self).getConfig(configs)
        #--Update old configs to use Paths instead of strings.
        self._ci_aliases = dict(
            [GPath(i) for i in item] for item in
            config.get(u'aliases', {}).items())
        return config

    def saveConfig(self, configs):
        """Save config to configs dictionary."""
        #--Toss outdated configCheck data.
        config = super(_AliasesPatcherPanel, self).saveConfig(configs)
        config[u'aliases'] = self._ci_aliases
        return config

    def _log_config(self, conf, config, clip, log):
        aliases = config.get(u'aliases', {})
        for mod, alias in aliases.items():
            log(u'* __%s__ >> %s' % (mod, alias))
            clip.write(u'  %s >> %s\n' % (mod, alias))

    def get_patcher_instance(self, patch_file):
        """Set patch_file aliases dict"""
        if self.isEnabled:
            patch_file.pfile_aliases = self._ci_aliases
        return self.patcher_type(self.patcher_name, patch_file)

#------------------------------------------------------------------------------
##: A lot of this belongs into _ListsMergerPanel (e.g. the whole GetConfigPanel
# split, remove empty sublists, etc.). Would also put forceAuto and
# forceItemCheck to rest
class _ListPatcherPanel(_PatcherPanel):
    """Patcher panel with option to select source elements."""
    listLabel = _(u'Source Mods')
    forceAuto = True
    forceItemCheck = False #--Force configChecked to True for all items
    canAutoItemCheck = True #--GUI: Whether new items are checked by default
    show_empty_sublist_checkbox = False
    # ADDITIONAL CONFIG DEFAULTS FOR LIST PATCHER
    default_autoIsChecked = True
    default_remove_empty_sublists = bush.game.displayName == u'Oblivion'
    default_configItems   = []
    default_configChecks  = {}
    default_configChoices = {}

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
            self.gList = CheckListBox(gConfigPanel)
            self.gList.on_box_checked.subscribe(self.OnListCheck)
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
                right_side_components.append(self.g_remove_empty)
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
            if not self.autoIsChecked:
                # SetItems when autoIsChecked is handled by OnAutomatic above
                self.SetItems(self.configItems)
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
        self.gSelectAll = SelectAllButton(self.gConfigPanel)
        self.gSelectAll.on_clicked.subscribe(lambda: self.mass_select(True))
        self.gDeselectAll = DeselectAllButton(self.gConfigPanel)
        self.gDeselectAll.on_clicked.subscribe(lambda: self.mass_select(False))
        return VLayout(spacing=4, items=[self.gSelectAll, self.gDeselectAll])

    def SetItems(self,items):
        """Set item to specified set of items."""
        items = self.items = load_order.get_ordered(items)
        forceItemCheck = self.forceItemCheck
        defaultItemCheck = self.__class__.canAutoItemCheck and bass.inisettings[u'AutoItemCheck']
        self.gList.lb_clear()
        isFirstLoad = self._GetIsFirstLoad()
        patcherOn = False
        patcher_bold = False
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
                        # Indicate that this is a new item by bolding it and
                        # its parent patcher
                        self.gList.lb_style_font_at_index(index, bold=True)
                        patcher_bold = True
                self.gList.lb_check_at_index(index,
                    self.configChecks.setdefault(
                        item, effectiveDefaultItemCheck))
        self.configItems = items
        if patcherOn:
            self._enable_self()
        # Bold it if it has a new item, slant it if it has no items
        patcher_slant = self.gList.lb_get_items_count() == 0
        self._style_patcher_label(bold=patcher_bold, slant=patcher_slant)

    def OnListCheck(self, _lb_selection_dex=None):
        """One of list items was checked. Update all configChecks states."""
        any_checked = False
        for i, item in enumerate(self.items):
            checked = self.gList.lb_is_checked_at_index(i)
            self.configChecks[item] = checked
            if checked:
                any_checked = True
        self._enable_self(any_checked)

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
        srcPaths = FileOpenMultiple.display_dialog(self.gConfigPanel, title,
                                                   srcDir, u'', wildcard)
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

    def mass_select(self, select=True):
        super(_ListPatcherPanel, self).mass_select(select)
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
            u'autoIsChecked', self.__class__.default_autoIsChecked)
        self.remove_empty_sublists = config.get(
            u'remove_empty_sublists',
            self.__class__.default_remove_empty_sublists)
        self.configItems = copy.deepcopy(
            config.get(u'configItems', self.__class__.default_configItems))
        self.configChecks = copy.deepcopy(
            config.get(u'configChecks', self.__class__.default_configChecks))
        self.configChoices = copy.deepcopy(
            config.get(u'configChoices', self.__class__.default_configChoices))
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
        self.configChecks = config[u'configChecks'] = {
            k: v for k, v in self.configChecks.items() if k in listSet}
        self.configChoices = config[u'configChoices'] = {
            k: v for k, v in self.configChoices.items() if k in listSet}
        config[u'configItems'] = self.configItems
        config[u'autoIsChecked'] = self.autoIsChecked
        config[u'remove_empty_sublists'] = self.remove_empty_sublists
        return config

    def getItemLabel(self,item):
        """Returns label for item to be used in list"""
        ret_label = u'%s' % item # Path or string - YAK
        return ret_label.replace(u'&', u'&&') # escape & - thanks wx

    def getAutoItems(self):
        """Returns list of items to be used for automatic configuration."""
        return self._get_auto_mods()

    def _get_auto_mods(self):
        mods_prior_to_patch = load_order.cached_lower_loading(
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
                # bolt.deprint(u'item %s not in saved configs [%s]' % (
                #     item, u', '.join([repr(c) for c in self.configChecks])))

    def get_patcher_instance(self, patch_file):
        patcher_sources = self._get_list_patcher_srcs()
        return self.patcher_type(self.patcher_name, patch_file,
                                 patcher_sources)

    def _get_list_patcher_srcs(self):
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

_label_formats = {str: u'%s', float: u'%4.2f', int: u'%d'}
def _custom_label(label, value): # edit label text with value
    return u'%s: %s' % (label, _label_formats[type(value)] % value)

class _TweakPatcherPanel(_ChoiceMenuMixin, _PatcherPanel):
    """Patcher panel with list of checkable, configurable tweaks."""
    tweak_label = _(u'Tweaks')

    def GetConfigPanel(self, parent, config_layout, gTipText):
        """Show config."""
        if self.gConfigPanel: return self.gConfigPanel
        gConfigPanel = super(_TweakPatcherPanel, self).GetConfigPanel(
            parent, config_layout, gTipText)
        self.gTweakList = CheckListBox(self.gConfigPanel)
        self.gTweakList.on_box_checked.subscribe(self.TweakOnListCheck)
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
            self.gTweakSelectAll = SelectAllButton(self.gConfigPanel)
            self.gTweakSelectAll.on_clicked.subscribe(
                lambda: self.mass_select(True))
            self.gTweakDeselectAll = DeselectAllButton(self.gConfigPanel)
            self.gTweakDeselectAll.on_clicked.subscribe(
                lambda: self.mass_select(False))
            tweak_select_layout = VLayout(spacing=4, items=[
                self.gTweakSelectAll, self.gTweakDeselectAll])
        else: tweak_select_layout = None
        #--Init GUI
        self.SetTweaks()
        return tweak_select_layout

    def SetTweaks(self):
        """Set item to specified set of items."""
        self.gTweakList.lb_clear()
        isFirstLoad = self._GetIsFirstLoad()
        patcher_bold = False
        for index,tweak in enumerate(self._all_tweaks):
            label = tweak.getListLabel()
            if tweak.choiceLabels and tweak.choiceLabels[
                tweak.chosen] == tweak.custom_choice:
                label = _custom_label(label, tweak.choiceValues[tweak.chosen][0])
            self.gTweakList.lb_insert(label, index)
            self.gTweakList.lb_check_at_index(index, tweak.isEnabled)
            if not isFirstLoad and tweak.isNew():
                # Indicate that this is a new item by bolding it and its parent
                # patcher
                self.gTweakList.lb_style_font_at_index(index, bold=True)
                patcher_bold = True
        # Bold it if it has a new item, slant it if it has no items
        patcher_slant = self.gTweakList.lb_get_items_count() == 0
        self._style_patcher_label(bold=patcher_bold, slant=patcher_slant)

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
                self._enable_self()
        elif ensureEnabled:
            self._enable_self()

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
            elif label == tweak.custom_choice:
                label = _custom_label(label, tweak.choiceValues[index][0])
                links.append(_ValueLinkCustom(label, index))
            else:
                links.append(_ValueLink(label, index))
        #--Show/Destroy Menu
        links.popup_menu(self.gTweakList, None)

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
        tweak = self._all_tweaks[tweakIndex] # type: base.AMultiTweakItem
        value = []
        new = None
        for i, v in enumerate(tweak.choiceValues[index]):
            if tweak.show_key_for_custom:
                ##: Mirrors chosen_eids, but all this is hacky - we should
                # enforce that keys for settings tweaks *must* be tuples and
                # then get rid of this
                key_display = u'\n\n' + tweak.tweak_key[i] if isinstance(
                    tweak.tweak_key, tuple) else tweak.tweak_key
            else:
                key_display = u''
            if isinstance(v,float):
                while new is None: # keep going until user entered valid float
                    label = (_(u'Enter the desired custom tweak value.')
                             + u'\n\n' +
                             _(u'Note: A floating point number is expected '
                               u'here.') + key_display)
                    new = balt.askText(
                        self.gConfigPanel, label,
                        title=tweak.tweak_name + _(u' - Custom Tweak Value'),
                        default=str(tweak.choiceValues[index][i]))
                    if new is None: #user hit cancel
                        return
                    try:
                        value.append(float(new))
                        new = None # Reset, we may have a multi-key tweak
                        break
                    except ValueError:
                        balt.showError(self.gConfigPanel,
                                       _(u"'%s' is not a valid floating point "
                                         u"number.") % new,
                                       title=tweak.tweak_name + _(u' - Error'))
                        new = None # invalid float, try again
            elif isinstance(v, int):
                label = (_(u'Enter the desired custom tweak value.')
                         + key_display)
                new = balt.askNumber(
                    self.gConfigPanel, label, prompt=_(u'Value'),
                    title=tweak.tweak_name + _(u' - Custom Tweak Value'),
                    value=tweak.choiceValues[index][i], min=-10000, max=10000)
                if new is None: #user hit cancel
                    return
                value.append(new)
            elif isinstance(v, str):
                label = (_(u'Enter the desired custom tweak text.')
                         + key_display)
                new = balt.askText(
                    self.gConfigPanel, label,
                    title=tweak.tweak_name + _(u' - Custom Tweak Text'),
                    default=tweak.choiceValues[index][i], strip=False) ##: strip ?
                if new is None: #user hit cancel
                    return
                value.append(new)
        if not value:
            value = tweak.choiceValues[index]
        value = tuple(value)
        validation_error = tweak.validate_values(value)
        if not validation_error: # no error, we're good to go
            tweak.choiceValues[index] = value
            tweak.chosen = index
            label = _custom_label(tweak.getListLabel(), value[0])
            self.gTweakList.lb_set_label_at_index(tweakIndex, label)
            self.gTweakList.lb_check_at_index(tweakIndex, True)
            self.TweakOnListCheck() # fired so this line is needed (?)
        else:
            # The tweak doesn't like the values the user chose, let them know
            error_header = (_(u'The value you entered (%s) is not valid '
                              u'for this tweak.') % value[0]
                            if len(value) == 1 else
                            _(u'The values you entered (%s) are not valid '
                              u'for this tweak.') % u', '.join(
                                str(s) for s in value))
            balt.showError(self.gConfigPanel,
                           error_header + u'\n\n' + validation_error,
                           title=_(u'%s - Error') % tweak.tweak_name)

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
            if tweak.tweak_key in conf:
                enabled, value = conf.get(tweak.tweak_key, (False, u''))
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
            except: bolt.deprint(u'Error importing Bashed Patch '
                                 u'configuration. Item %s skipped.' % tweakie,
                                 traceback=True)

    def get_patcher_instance(self, patch_file):
        enabledTweaks = [t for t in self._all_tweaks if t.isEnabled]
        return self.patcher_type(self.patcher_name, patch_file, enabledTweaks)

#------------------------------------------------------------------------------
class _ImporterPatcherPanel(_ListPatcherPanel):

    def saveConfig(self, configs):
        """Save config to configs dictionary."""
        config = super(_ImporterPatcherPanel, self).saveConfig(configs)
        if self.isEnabled:
            importedMods = [item for item,value in
                            self.configChecks.items() if
                            value and bosh.ModInfos.rightFileType(item)]
            configs[u'ImportedMods'].update(importedMods)
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
        # Note that we do *not* want to escape the & here - that puts *two*
        # ampersands in the resulting ListBox for some reason
        choice = [i[0] for i in self.configChoices.get(item, tuple())]
        if choice:
            return u'%s [%s]' % (item, u''.join(sorted(choice)))
        else:
            return u'%s' % item # Path or string - YAK

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
        links.popup_menu(self.gList, None)

    def _log_config(self, conf, config, clip, log):
        self.configChoices = conf.get(u'configChoices', {})
        for item in conf.get(u'configItems', []):
            log(u'. __%s__' % self.getItemLabel(item))
            clip.write(u'    %s\n' % self.getItemLabel(item))

    def _import_config(self, default=False): # TODO(ut):non default not handled
        if default:
            super(_ListsMergerPanel, self)._import_config(default)

    def mass_select(self, select=True): self.isEnabled = select

    def _style_patcher_label(self, bold=False, slant=False):
        # Never italicize these since they will run even if there are no tagged
        # source plugins
        super(_ListsMergerPanel, self)._style_patcher_label(bold=bold)

class _MergerPanel(_ListPatcherPanel):
    listLabel = _(u'Mergeable Mods')

    def getAutoItems(self):
        """Returns list of items to be used for automatic configuration."""
        mods_prior_to_patch = load_order.cached_lower_loading(
            patch_files.executing_patch)
        return [mod for mod in mods_prior_to_patch if (
            mod in bosh.modInfos.mergeable and u'NoMerge' not in bosh.modInfos[
                mod].getBashTags())]

class _GmstTweakerPanel(_TweakPatcherPanel):
    # CONFIG DEFAULTS
    default_isEnabled = True

class _AListPanelCsv(_ListPatcherPanel):
    """Base class for list panels that support CSV files as well."""
    listLabel = _(u'Source Mods/Files')
    # CSV files for this patcher have to end with _{this value}.csv
    _csv_key = None

    def getAutoItems(self):
        if not self._csv_key:
            raise SyntaxError(u'_csv_key not specified for CSV-supporting '
                              u'patcher panel (%s)' % self.__class__.__name__)
        auto_items = super(_AListPanelCsv, self).getAutoItems()
        csv_ending = u'_%s.csv' % self._csv_key
        for fileName in sorted(patches_set()):
            if fileName.s.endswith(csv_ending):
                auto_items.append(fileName)
        return auto_items

#------------------------------------------------------------------------------
# GUI Patcher classes
# Do _not_ change the _config_key attr or you will break existing BP configs
#------------------------------------------------------------------------------
from ..patcher.patchers import base
from ..patcher.patchers import checkers, mergers, preservers
from ..patcher.patchers import multitweak_actors, multitweak_assorted, \
    multitweak_clothes, multitweak_names, multitweak_settings, \
    multitweak_races

# Patchers 10 -----------------------------------------------------------------
class AliasModNames(_AliasesPatcherPanel):
    _config_key = u'AliasesPatcher'
    patcher_type = base.AliasModNamesPatcher

class MergePatches(_MergerPanel):
    """Merges specified patches into Bashed Patch."""
    patcher_name = _(u'Merge Patches')
    patcher_desc = _(u'Merge patch mods into Bashed Patch.')
    _config_key = u'PatchMerger'
    patcher_type = base.MergePatchesPatcher

# Patchers 20 -----------------------------------------------------------------
class ImportGraphics(_ImporterPatcherPanel):
    """Merges changes to graphics (models and icons)."""
    patcher_name = _(u'Import Graphics')
    patcher_desc = _(u'Import graphics (models, icons, etc.) from source '
                     u'mods.')
    autoKey = {u'Graphics'}
    _config_key = u'GraphicsPatcher'
    patcher_type = preservers.ImportGraphicsPatcher

# -----------------------------------------------------------------------------
class ImportActorsAnimations(_ImporterPatcherPanel):
    """Merges changes to actor animation lists."""
    patcher_name = _(u'Import Actors: Animations')
    patcher_desc = _(u'Import actor animations from source mods.')
    autoKey = {u'Actors.Anims'}
    _config_key = u'KFFZPatcher'
    patcher_type = preservers.ImportActorsAnimationsPatcher

# -----------------------------------------------------------------------------
class ImportActorsAIPackages(_ImporterPatcherPanel):
    """Merges changes to the AI Packages of Actors."""
    patcher_name = _(u'Import Actors: AI Packages')
    patcher_desc = _(u'Import actor AI Package links from source mods.')
    autoKey = {u'Actors.AIPackages', u'Actors.AIPackagesForceAdd'}
    _config_key = u'NPCAIPackagePatcher'
    patcher_type = mergers.ImportActorsAIPackagesPatcher

# -----------------------------------------------------------------------------
class ImportActors(_ImporterPatcherPanel):
    """Merges changes to actors."""
    patcher_name = _(u'Import Actors')
    patcher_desc = _(u'Import various actor attributes from source mods.')
    autoKey = set(chain.from_iterable(
        d for d in bush.game.actor_importer_attrs.values()))
    _config_key = u'ActorImporter'
    patcher_type = preservers.ImportActorsPatcher

# -----------------------------------------------------------------------------
class ImportActorsPerks(_ImporterPatcherPanel):
    """Merges changes to actor perks."""
    patcher_name = _(u'Import Actors: Perks')
    patcher_desc = _(u'Import actor perks from source mods.')
    autoKey = {u'Actors.Perks.Add', u'Actors.Perks.Change',
               u'Actors.Perks.Remove'}
    _config_key = u'ImportActorsPerks'
    patcher_type = mergers.ImportActorsPerksPatcher

# -----------------------------------------------------------------------------
class ImportActorsDeathItems(_ImporterPatcherPanel):
    """Merges changes to actor death items."""
    patcher_name = _(u'Import Actors: Death Items')
    patcher_desc = _(u'Import actor death items from source mods.')
    autoKey = {u'Actors.DeathItem'}
    _config_key = u'DeathItemPatcher'
    patcher_type = preservers.ImportActorsDeathItemsPatcher

# -----------------------------------------------------------------------------
class ImportCells(_ImporterPatcherPanel):
    """Merges changes to cells (climate, lighting, and water.)"""
    patcher_name = _(u'Import Cells')
    patcher_desc = _(u'Import cells (climate, lighting, and water) from '
                     u'source mods.')
    autoKey = set(bush.game.cellRecAttrs)
    _config_key = u'CellImporter'
    patcher_type = preservers.ImportCellsPatcher

# -----------------------------------------------------------------------------
class ImportActorsFactions(_ImporterPatcherPanel, _AListPanelCsv):
    """Import factions to creatures and NPCs."""
    patcher_name = _(u'Import Actors: Factions')
    patcher_desc = _(u'Import actor factions from source mods/files.')
    autoKey = {u'Factions'}
    _csv_key = u'Factions'
    _config_key = u'ImportFactions'
    patcher_type = preservers.ImportActorsFactionsPatcher

# -----------------------------------------------------------------------------
class ImportRelations(_ImporterPatcherPanel, _AListPanelCsv):
    """Import faction relations to factions."""
    patcher_name = _(u'Import Relations')
    patcher_desc = _(u'Import relations from source mods/files.')
    autoKey = {u'Relations.Add', u'Relations.Change', u'Relations.Remove'}
    _csv_key = u'Relations'
    _config_key = u'ImportRelations'
    patcher_type = mergers.ImportRelationsPatcher

# -----------------------------------------------------------------------------
class ImportInventory(_ImporterPatcherPanel):
    """Merge changes to actor inventories."""
    patcher_name = _(u'Import Inventory')
    patcher_desc = _(u'Merges changes to NPC, creature and container '
                     u'inventories.')
    autoKey = {u'Invent.Add', u'Invent.Change', u'Invent.Remove'}
    _config_key = u'ImportInventory'
    patcher_type = mergers.ImportInventoryPatcher

# -----------------------------------------------------------------------------
class ImportOutfits(_ImporterPatcherPanel):
    """Merge changes to outfits."""
    patcher_name = _(u'Import Outfits')
    patcher_desc = _(u'Merges changes to NPC outfits.')
    autoKey = {u'Outfits.Add', u'Outfits.Remove'}
    _config_key = u'ImportOutfits'
    patcher_type = mergers.ImportOutfitsPatcher

# -----------------------------------------------------------------------------
class ImportActorsSpells(_ImporterPatcherPanel):
    """Merges changes to the spells lists of Actors."""
    patcher_name = _(u'Import Actors: Spells')
    patcher_desc = _(u'Merges changes to actor spell / effect lists.')
    autoKey = {u'Actors.Spells', u'Actors.SpellsForceAdd'}
    _config_key = u'ImportActorsSpells'
    patcher_type = mergers.ImportActorsSpellsPatcher

# -----------------------------------------------------------------------------
class ImportNames(_ImporterPatcherPanel, _AListPanelCsv):
    """Import names from source mods/files."""
    patcher_name = _(u'Import Names')
    patcher_desc = _(u'Import names from source mods/files.')
    autoKey = {u'Names'}
    _csv_key = u'Names'
    _config_key = u'NamesPatcher'
    patcher_type = preservers.ImportNamesPatcher

# -----------------------------------------------------------------------------
class ImportActorsFaces(_ImporterPatcherPanel):
    """NPC Faces patcher, for use with TNR or similar mods."""
    patcher_name = _(u'Import Actors: Faces')
    patcher_desc = _(u'Import NPC face/eyes/hair from source mods. For use '
                     u'with TNR and similar mods.')
    autoKey = {u'NPC.Eyes', u'NPC.FaceGen', u'NPC.Hair',
               u'NpcFacesForceFullImport'}
    _config_key = u'NpcFacePatcher'
    patcher_type = preservers.ImportActorsFacesPatcher

    def _get_auto_mods(self, autoRe=re.compile(u'^TNR .*.esp$', re.I | re.U)):
        """Pick TNR esp if present in addition to appropriately tagged mods."""
        mods_prior_to_patch = load_order.cached_lower_loading(
            patch_files.executing_patch)
        return [mod for mod in mods_prior_to_patch if autoRe.match(mod.s) or (
            self.__class__.autoKey & bosh.modInfos[mod].getBashTags())]

# -----------------------------------------------------------------------------
class ImportSounds(_ImporterPatcherPanel):
    """Imports sounds from source mods into patch."""
    patcher_name = _(u'Import Sounds')
    patcher_desc = _(u'Import sounds (from Magic Effects, Containers, '
                     u'Activators, Lights, Weathers and Doors) from source '
                     u'mods.')
    autoKey = {u'Sound'}
    _config_key = u'SoundPatcher'
    patcher_type = preservers.ImportSoundsPatcher

# -----------------------------------------------------------------------------
class ImportStats(_ImporterPatcherPanel, _AListPanelCsv):
    """Import stats from mod file."""
    patcher_name = _(u'Import Stats')
    patcher_desc = _(u'Import stats from any pickupable items from source '
                     u'mods/files.')
    autoKey = {u'Stats'}
    _csv_key = u'Stats'
    _config_key = u'StatsPatcher'
    patcher_type = preservers.ImportStatsPatcher

# -----------------------------------------------------------------------------
class ImportScripts(_ImporterPatcherPanel):
    """Imports attached scripts on objects."""
    patcher_name = _(u'Import Scripts')
    patcher_desc = _(u'Import scripts on various objects (e.g. containers, '
                     u'weapons, etc.) from source mods.')
    autoKey = {u'Scripts'}
    _config_key = u'ImportScripts'
    patcher_type = preservers.ImportScriptsPatcher

# -----------------------------------------------------------------------------
class ImportRaces(_ImporterPatcherPanel):
    """Imports race-related data."""
    patcher_name = _(u'Import Races')
    patcher_desc = _(u'Import race eyes, hair, body, voice, etc. from source '
                     u'mods.')
    ##: Move to a game constant -> multi-game plus decouples this
    autoKey = set(chain.from_iterable(d for d in
        preservers.ImportRacesPatcher.rec_attrs.values()))
    _config_key = u'ImportRaces'
    patcher_type = preservers.ImportRacesPatcher

# -----------------------------------------------------------------------------
class ImportRacesRelations(_ImporterPatcherPanel):
    """Imports race-faction relations."""
    patcher_name = _(u'Import Races: Relations')
    patcher_desc = _(u'Import race-faction relations from source mods.')
    autoKey = {u'R.Relations.Add', u'R.Relations.Change',
               u'R.Relations.Remove'}
    _config_key = u'ImportRacesRelations'
    patcher_type = mergers.ImportRacesRelationsPatcher

# -----------------------------------------------------------------------------
class ImportRacesSpells(_ImporterPatcherPanel):
    """Imports race spells/abilities."""
    patcher_name = _(u'Import Races: Spells')
    patcher_desc = _(u'Import race abilities and spells from source mods.')
    autoKey = {u'R.AddSpells', u'R.ChangeSpells'}
    _config_key = u'ImportRacesSpells'
    patcher_type = mergers.ImportRacesSpellsPatcher

# -----------------------------------------------------------------------------
class ImportSpellStats(_ImporterPatcherPanel, _AListPanelCsv):
    """Import spell changes from mod files."""
    patcher_name = _(u'Import Spell Stats')
    patcher_desc = _(u'Import stats from any spells / actor effects from '
                     u'source mods/files.')
    autoKey = {u'SpellStats'}
    _csv_key = u'Spells'
    _config_key = u'SpellsPatcher'
    patcher_type = preservers.ImportSpellStatsPatcher

# -----------------------------------------------------------------------------
class ImportDestructible(_ImporterPatcherPanel):
    patcher_name = _(u'Import Destructible')
    patcher_desc = (_(u'Preserves changes to destructible records.')
                    + u'\n\n' +
                    _(u'Will have to use if a mod that allows you to destroy '
                      u'part of the environment is installed and active.'))
    autoKey = {u'Destructible'}
    _config_key = u'DestructiblePatcher'
    patcher_type = preservers.ImportDestructiblePatcher

# -----------------------------------------------------------------------------
class ImportKeywords(_ImporterPatcherPanel):
    patcher_name = _(u'Import Keywords')
    patcher_desc = _(u'Import keyword changes from source mods.')
    autoKey = {u'Keywords'}
    _config_key = u'KeywordsImporter'
    patcher_type = preservers.ImportKeywordsPatcher

# -----------------------------------------------------------------------------
class ImportText(_ImporterPatcherPanel):
    patcher_name = _(u'Import Text')
    patcher_desc = _(u'Import various types of long-form text like book '
                     u'texts, effect descriptions, etc. from source mods.')
    autoKey = {u'Text'}
    _config_key = u'TextImporter'
    patcher_type = preservers.ImportTextPatcher

# -----------------------------------------------------------------------------
class ImportObjectBounds(_ImporterPatcherPanel):
    patcher_name = _(u'Import Object Bounds')
    patcher_desc = _(u'Import object bounds for various actors, items and '
                     u'objects.')
    autoKey = {u'ObjectBounds'}
    _config_key = u'ObjectBoundsImporter'
    patcher_type = preservers.ImportObjectBoundsPatcher

# -----------------------------------------------------------------------------
class ImportEnchantmentStats(_ImporterPatcherPanel):
    patcher_name = _(u'Import Enchantment Stats')
    patcher_desc = _(u'Import stats from enchantments / object effects from '
                     u'source mods.')
    autoKey = {u'EnchantmentStats'}
    _config_key = u'ImportEnchantmentStats'
    patcher_type = preservers.ImportEnchantmentStatsPatcher

# -----------------------------------------------------------------------------
class ImportEffectsStats(_ImporterPatcherPanel):
    patcher_name = _(u'Import Effect Stats')
    patcher_desc = _(u'Import stats from magic / base effects from source '
                     u'mods.')
    autoKey = {u'EffectStats'}
    _config_key = u'ImportEffectsStats'
    patcher_type = preservers.ImportEffectsStatsPatcher

# Patchers 30 -----------------------------------------------------------------
class TweakAssorted(_TweakPatcherPanel):
    patcher_name = _(u'Tweak Assorted')
    patcher_desc = _(u'Tweak various records in miscellaneous ways.')
    _config_key = u'AssortedTweaker'
    patcher_type = multitweak_assorted.TweakAssortedPatcher
    default_isEnabled = True

# -----------------------------------------------------------------------------
class TweakClothes(_TweakPatcherPanel):
    patcher_name = _(u'Tweak Clothes')
    patcher_desc = _(u'Tweak clothing weight and blocking.')
    _config_key = u'ClothesTweaker'
    patcher_type = multitweak_clothes.TweakClothesPatcher

# -----------------------------------------------------------------------------
class TweakSettings(_GmstTweakerPanel):
    patcher_name = _(u'Tweak Settings')
    patcher_desc = _(u'Tweak game settings.')
    _config_key = u'GmstTweaker'
    patcher_type = multitweak_settings.TweakSettingsPatcher

# -----------------------------------------------------------------------------
class TweakNames(_TweakPatcherPanel):
    patcher_name = _(u'Tweak Names')
    patcher_desc = _(u'Tweak object names to sort them by type/stats or to '
                     u'improve things like lore friendliness.')
    _config_key = u'NamesTweaker'
    patcher_type = multitweak_names.TweakNamesPatcher

# -----------------------------------------------------------------------------
class TweakActors(_TweakPatcherPanel):
    patcher_name = _(u'Tweak Actors')
    patcher_desc = _(u'Tweak NPC and Creatures records in specified ways.')
    _config_key = u'TweakActors'
    patcher_type = multitweak_actors.TweakActorsPatcher

# -----------------------------------------------------------------------------
class TweakRaces(_TweakPatcherPanel):
    patcher_name = _(u'Tweak Races')
    patcher_desc = _(u'Tweak race records in specified ways.')
    _config_key = u'TweakRaces'
    patcher_type = multitweak_races.TweakRacesPatcher

# Patchers 40 -----------------------------------------------------------------
class ReplaceFormIDs(_AListPanelCsv):
    """Imports Form Id replacers into the Bashed Patch."""
    patcher_name = _(u'Replace Form IDs')
    patcher_desc = _(u'Imports Form Id replacers from csv files into the '
                     u'Bashed Patch.')
    _csv_key = u'Formids'
    _config_key = u'UpdateReferences'
    patcher_type = base.ReplaceFormIDsPatcher
    canAutoItemCheck = False #--GUI: Whether new items are checked by default.

# -----------------------------------------------------------------------------
class _AListsMerger(_ListsMergerPanel):
    """Mergers targeting all mods in the LO, with the option to override
    tags."""
    def get_patcher_instance(self, patch_file):
        patcher_sources = self._get_list_patcher_srcs()
        return self.patcher_type(self.patcher_name, patch_file,
                                 patcher_sources,
                                 self.remove_empty_sublists,
                                 defaultdict(tuple, self.configChoices))

class LeveledLists(_AListsMerger):
    patcher_name = _(u'Leveled Lists')
    patcher_desc = u'\n\n'.join([
        _(u'Merges changes to leveled lists from all active and/or merged '
          u'mods.'),
        _(u'Advanced users may override Relev/Delev tags for any mod (active '
          u'or inactive) using the list below.')])
    autoKey = {u'Delev', u'Relev'}
    _config_key = u'ListsMerger'
    patcher_type = mergers.LeveledListsPatcher
    show_empty_sublist_checkbox = True

class FormIDLists(_AListsMerger):
    patcher_name = _(u'FormID Lists')
    patcher_desc = u'\n\n'.join([
        _(u'Merges changes to FormID lists from all active and/or merged '
          u'mods.'),
        _(u'Advanced users may override Deflst tags for any mod (active or '
          u'inactive) using the list below.')])
    autoKey = {u'Deflst'}
    _config_key = u'FidListsMerger'
    patcher_type = mergers.FormIDListsPatcher
    listLabel = _(u'Override Deflst Tags')
    forceItemCheck = False #--Force configChecked to True for all items
    choiceMenu = (u'Auto', u'----', u'Deflst')
    # CONFIG DEFAULTS
    default_isEnabled = False

# -----------------------------------------------------------------------------
class ContentsChecker(_PatcherPanel):
    """Checks contents of leveled lists, inventories and containers for
    correct content types."""
    patcher_name = _(u'Contents Checker')
    patcher_desc = _(u'Checks contents of leveled lists, inventories and '
                     u'containers for correct types.')
    _config_key = u'ContentsChecker'
    patcher_type = checkers.ContentsCheckerPatcher
    default_isEnabled = True

# -----------------------------------------------------------------------------
class EyeChecker(_PatcherPanel):
    """Checks for and fixes googly eyes."""
    patcher_name = _(u'Eye Checker')
    patcher_desc = _(u"Filters race eyes in order to fix the 'googly eyes' "
                     u'bug.')
    _config_key = u'EyeChecker'
    patcher_type = checkers.EyeCheckerPatcher
    default_isEnabled = True

# -----------------------------------------------------------------------------
class RaceChecker(_PatcherPanel):
    """Sorts hairs and eyes."""
    patcher_name = _(u'Race Checker')
    patcher_desc = _(u'Sorts race hairs and eyes.')
    _config_key = u'RaceChecker'
    patcher_type = checkers.RaceCheckerPatcher
    default_isEnabled = True

#------------------------------------------------------------------------------
class NpcChecker(_PatcherPanel):
    """Assigns missing hair and eyes."""
    patcher_name = _(u'NPC Checker')
    patcher_desc = _(u'This will randomly assign hairs and eyes to NPCs that '
                     u'are otherwise missing them.')
    _config_key = u'NpcChecker'
    patcher_type = checkers.NpcCheckerPatcher
    default_isEnabled = True

#------------------------------------------------------------------------------
class TimescaleChecker(_PatcherPanel):
    """Adjusts the wave period of grass match changes in the timescale."""
    patcher_name = _(u'Timescale Checker')
    patcher_desc = u'\n'.join([
        _(u'Adjusts the wave period of grasses to match changes in the '
          u'timescale.'),
        _(u'Does nothing if you are not using a nonstandard timescale.'),
        u'',
        _(u'Incompatible with plugins that change grass wave periods to match '
          u'a different timescale. Uninstall such plugins before using this.'),
    ])
    _config_key = u'TimescaleChecker'
    patcher_type = checkers.TimescaleCheckerPatcher
    default_isEnabled = True

#------------------------------------------------------------------------------
# Game specific GUI Patchers --------------------------------------------------
#------------------------------------------------------------------------------
from .patcher_dialog import all_gui_patchers
# Dynamically create game specific UI patcher classes and add them to module's
# scope
# Patchers with no options
for gsp_name, gsp_class in bush.game.gameSpecificPatchers.items():
    globals()[gsp_name] = type(gsp_name, (_PatcherPanel,),
        gsp_class.gui_cls_vars())
# Simple list patchers
for gsp_name, gsp_class in bush.game.gameSpecificListPatchers.items():
    gsp_bases = (_ListPatcherPanel,)
    gsp_attrs = gsp_class.gui_cls_vars()
    if u'_csv_key' in gsp_attrs:
        # This patcher accepts CSV files, need to use the CSV base class
        gsp_bases = (_AListPanelCsv,)
    globals()[gsp_name] = type(gsp_name, gsp_bases, gsp_attrs)
# Import patchers
for gsp_name, gsp_class in bush.game.game_specific_import_patchers.items():
    gsp_bases = (_ImporterPatcherPanel,)
    gsp_attrs = gsp_class.gui_cls_vars()
    if u'_csv_key' in gsp_attrs:
        # This patcher accepts CSV files, need to add the CSV base class
        gsp_bases += (_AListPanelCsv,)
    globals()[gsp_name] = type(gsp_name, gsp_bases, gsp_attrs)

# Init Patchers
def initPatchers():
    group_order = {p_grp: i for i, p_grp in enumerate( # PY3: enum?
        (u'General', u'Importers', u'Tweakers', u'Special'))}
    patcher_classes = [globals()[p] for p in bush.game.patchers]
    # Sort alphabetically first for aesthetic reasons
    patcher_classes.sort(key=lambda a: a.patcher_name)
    # After that, sort by group to make patchers instantiate in the right order
    patcher_classes.sort(
        key=lambda a: group_order[a.patcher_type.patcher_group])
    all_gui_patchers.extend((p() for p in patcher_classes))
    # Update the set of all tags for this game based on the available patchers
    bush.game.allTags.update(chain.from_iterable(p.autoKey
                                                 for p in all_gui_patchers))
