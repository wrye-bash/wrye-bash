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
#  Wrye Bash copyright (C) 2005-2009 Wrye, 2010-2024 Wrye Bash Team
#  https://github.com/wrye-bash
#
# =============================================================================
"""Specific parser for Wrye Bash."""
from __future__ import annotations

import os
import traceback

from .. import ScriptParser, bass, bolt, bosh, bush, load_order
from ..ScriptParser import error, PreParser
from ..balt import ItemLink
from ..bolt import FName, FNDict, LooseVersion
from ..env import get_file_version, to_os_path
from ..gui import CENTER, RIGHT, CheckBox, CheckListBox, GridLayout, \
    HBoxedLayout, HLayout, HyperlinkLabel, Label, LayoutOptions, Links, \
    ListBox, PictureWithCursor, StaticBmp, Stretch, TextArea, VLayout, \
    WizardDialog, WizardPage, get_image_dir, get_image
from ..ini_files import OBSEIniFile, IniFileInfo
from ..wbtemp import cleanup_temp_dir

def _err_invalid_for_syntax(exp_syntax: str):
    error(_("Invalid syntax for 'For' statement. Expected format: "
            "%(expected_syntax)s")) % {'expected_syntax': exp_syntax}

class WizInstallInfo(object):
    __slots__ = ('canceled', 'select_plugins', 'rename_plugins',
                 'select_sub_packages', 'ini_edits', 'should_install')
    # canceled: Set to true if the user canceled the wizard, or if an error
    # occurred
    # select_plugins: Set of plugins to 'select' for install
    # rename_plugins: Dictionary of renames for plugins.  In the format of:
    #   'original name':'new name'
    # select_sub_packages: Set of sub-packages to 'select' for install
    # ini_edits: Dictionary of INI edits to apply/create.  In the format of:
    #   'ini file': {
    #      'section': {
    #         'key': value
    #         }
    #      }
    #    For BatchScript type ini's, the 'section' will either be 'set',
    #    'setGS' or 'SetNumericGameSetting'
    # should_install: Set to True if after configuring this package, it should
    # also be installed.

    def __init__(self):
        self.canceled = False
        self.select_plugins = set()
        self.rename_plugins: FNDict[FName, FName] = FNDict()
        self.select_sub_packages = set()
        self.ini_edits = bolt.LowerDict()
        self.should_install = False

class InstallerWizard(WizardDialog):
    """Class used by Wrye Bash, creates a wx Wizard that dynamically creates
    pages based on a script."""
    _def_size = (600, 500)
    _key_prefix = 'bash.wizard'

    def __init__(self, parent, installer, bAuto, progress):
        super().__init__(parent, title=_('Installer Wizard'),
            sizes_dict=bass.settings)
        # get the wizard file - if we are an archive pass a progress to unpack
        self._wizard_dir = installer.get_wizard_file_dir(progress)
        self._wizard_file = self._wizard_dir.join(installer.hasWizard)
        # parser that will spit out the pages
        self.parser = WryeParser(self, installer, bAuto)
        self.ret = WizInstallInfo()

    def disable_wiz_buttons(self):
        """Disables all navigation buttons except for Cancel."""
        for b in (self._back_button, self._next_button, self._finish_button):
            b.enabled = False

    def enable_forward(self, btn_enabled):
        """Enables or disables both the next and finish buttons."""
        self._next_button.enabled = btn_enabled
        self._finish_button.enabled = btn_enabled

    def save_size(self): ##: needed?
        # Otherwise, regular resize, save the size if we're not maximized
        self.on_closing(destroy=False)

    def _has_next_page(self):
        return not self.parser.parser_finished

    def _has_prev_page(self):
        return self.parser.choiceIdex > 0

    def _get_next_page(self):
        # If we're still on the dummy page, then we're only changing to the
        # first page, so skip the OnNext call
        if self._curr_page != self._dummy_page:
            self._curr_page.OnNext()
        return self.parser.Continue()

    def _get_prev_page(self):
        return self.parser.Back()

    def _cancel_wizard(self, msg=None):
        self.ret.canceled = msg or True

    def Run(self):
        err_msg = self.parser.Begin(self._wizard_file, self._wizard_dir)
        if err_msg:
            self._cancel_wizard(err_msg) # Wizard could not be read
        else:
            self._run_wizard()
        if self.parser.bArchive:
            cleanup_temp_dir(self._wizard_dir)
        return self.ret

class PageInstaller(WizardPage):
    """Base class for all the parser wizard pages, just to handle a couple
    simple things here."""

    def __init__(self, parent):
        self._wiz_parent = parent
        super(PageInstaller, self).__init__(parent)

    def OnNext(self):
        #This is what needs to be implemented by sub-classes,
        #this is where flow control objects etc should be
        #created
        pass

class PageError(PageInstaller):
    """Page that shows an error message, has only a "Cancel" button enabled,
    and cancels any changes made."""

    def __init__(self, parent, title, errorMsg):
        super(PageError, self).__init__(parent)
        parent.disable_wiz_buttons()
        # Layout stuff
        VLayout(spacing=5, items=[
            Label(self, title),
            (TextArea(self, editable=False, init_text=errorMsg,
                      auto_tooltip=False),
             LayoutOptions(weight=1, expand=True))
        ]).apply_to(self)
        self.update_layout()

class PageSelect(PageInstaller):
    """A page that shows a message up top, with a selection box on the left
    (multi- or single- selection), with an optional associated image and
    description for each option, shown when that item is selected."""

    def __init__(self, parent, bMany, desc, items_default, listDescs,
                 image_paths):
        PageInstaller.__init__(self, parent)
        self.listItems = list(items_default)
        self._image_paths = image_paths
        self.descs = listDescs
        self.bMany = bMany
        self.index = None
        self.title_desc = Label(self, desc)
        self.textItem = TextArea(self, editable=False, auto_tooltip=False)
        self.bmp_item = PictureWithCursor(self, 0, 0, background=None)
        kwargs = dict(choices=self.listItems, isHScroll=True,
                      onSelect=self.OnSelect)
        self._page_parent = parent
        # Create links to facilitate mass (de)selection
        self._page_links = Links()
        if bMany:
            self.listOptions = CheckListBox(self, **kwargs)
            self.listOptions.on_mouse_right_up.subscribe(self._on_right_click)
            self._page_links.append_link(_Page_SelectAll(self.listOptions))
            self._page_links.append_link(_Page_DeselectAll(self.listOptions))
            self._page_links.append_link(_Page_ToggleAll(self.listOptions))
            for index, dflt in enumerate(items_default.values()):
                self.listOptions.lb_check_at_index(index, dflt)
        else:
            self.listOptions = ListBox(self, **kwargs)
            parent.enable_forward(False)
            for index, dflt in enumerate(items_default.values()):
                if dflt:
                    self.listOptions.lb_select_index(index)
                    self.Selection(index)
                    break
        VLayout(item_expand=True, spacing=5, items=[
            HBoxedLayout(self, items=[self.title_desc]),
            Label(self, _('Options:')),
            (HLayout(item_expand=True, item_weight=1,
                     items=[self.listOptions, self.bmp_item]),
             LayoutOptions(weight=1)),
            Label(self, _('Description:')),
            (self.textItem, LayoutOptions(weight=1))
        ]).apply_to(self)
        self.update_layout()
        self.bmp_item.on_mouse_middle_up.subscribe(self._click_on_image)
        self.bmp_item.on_mouse_left_dclick.subscribe(
            lambda selected_index: self._click_on_image())

    def OnSelect(self, lb_selection_dex, _lb_selection_str):
        self.listOptions.lb_select_index(lb_selection_dex) # event.Skip() won't do
        self.Selection(lb_selection_dex)

    def _click_on_image(self):
        img = self._image_paths[self.index]
        if not img:
            return # None - no image path specified
        try:
            img.start()
        except FileNotFoundError:
            pass # Image path specified, but no image present at that path
        except OSError:
            bolt.deprint(f'Failed to open {img}.', traceback=True)

    def _on_right_click(self, lb_selection_dex):
        """Internal callback to show the context menu for appropriate pages."""
        self._page_links.popup_menu(self, None)
        self.Selection(lb_selection_dex)

    def Selection(self, index):
        self._page_parent.enable_forward(True)
        self.index = index
        self.textItem.text_content = self.descs[index]
        self.bmp_item.set_bitmap(self._image_paths[index])
        # self.Layout() # the bitmap would change size and show blurred

    def OnNext(self):
        temp_items = []
        if self.bMany:
            index = -1
            for item in self.listItems:
                index += 1
                if self.listOptions.lb_is_checked_at_index(index):
                    temp_items.append(item)
        else:
            for i in self.listOptions.lb_get_selections():
                temp_items.append(self.listItems[i])
        choice_idex = self._wiz_parent.parser.choiceIdex
        if choice_idex < len(self._wiz_parent.parser.choices):
            oldChoices = self._wiz_parent.parser.choices[choice_idex]
            if temp_items == oldChoices:
                pass
            else:
                self._wiz_parent.parser.choices = self._wiz_parent.parser.choices[0:choice_idex]
                self._wiz_parent.parser.choices.append(temp_items)
        else:
            self._wiz_parent.parser.choices.append(temp_items)
        self._wiz_parent.parser.PushFlow('Select', False, ['SelectOne', 'SelectMany', 'Case', 'Default', 'EndSelect'], values=temp_items, hitCase=False)

class _PageLink(ItemLink):
    """Base class for mass (de)select page links."""
    def __init__(self, link_clb: CheckListBox):
        super().__init__()
        self._link_clb = link_clb

    def Execute(self):
        with self._link_clb.pause_drawing():
            for i in range(self._link_clb.lb_get_items_count()):
                self._link_clb.lb_check_at_index(i, self._should_enable(
                    self._link_clb.lb_is_checked_at_index(i)))

    def _should_enable(self, check_state):
        """Returns True if a checkbox with the specified state should be
        enabled."""
        raise NotImplementedError

class _Page_SelectAll(_PageLink):
    """Select all options on this page."""
    _text = _('Select All')
    _help = _('Selects all options on this page.')

    def _should_enable(self, check_state): return True

class _Page_DeselectAll(_PageLink):
    """Deselect all options on this page."""
    _text = _('Deselect All')
    _help = _('Deselects all options on this page.')

    def _should_enable(self, check_state): return False

class _Page_ToggleAll(_PageLink):
    """Toggle all options on this page."""
    _text = _('Toggle Selection')
    _help = _('Deselects all selected options on this page and vice versa.')

    def _should_enable(self, check_state): return not check_state

def generateTweakLines(wizardEdits, target):
    lines = ['; ' + _(
        "Generated by Wrye Bash %(wb_version)s for '%(target_ini)s' via "
        "wizard") % {'wb_version': bass.AppVersion, 'target_ini': target}]
    for realSection, values in wizardEdits.items():
        if not values:
            continue
        try: # OBSE pseudo section
            sect = OBSEIniFile.ci_pseudosections.get(realSection, realSection)
            for setting, (value, _comment, is_deleted) in values.items():
                line = OBSEIniFile.fmt_setting(setting, value, sect) # KeyError
                lines.append(f';-{line}' if is_deleted else line)
            continue
        except KeyError: # normal ini, assume pseudosections don't appear there
            lines.append('')
            lines.append(f'[{realSection}]')
        for setting, (value, comment, is_deleted) in values.items():
            line = IniFileInfo.fmt_setting(setting, value, realSection, comment)
            lines.append(f';-{line}' if is_deleted else line)
    return lines

class PageFinish(PageInstaller):
    """Page displayed at the end of a wizard, showing which sub-packages and
    which plugins will be selected. Also displays some notes for the user."""

    def __init__(self, parent, wrye_parser: WryeParser):
        PageInstaller.__init__(self, parent)
        subs = sorted(wrye_parser.sublist)
        #--make the list that will be displayed
        renames = wrye_parser.plugin_renames
        displayed_plugins = [f'{x} -> {renames[x]}' if x in renames else x for
                             x in wrye_parser.plugin_enabled]
        self._wiz_parent.ret.rename_plugins = renames
        parent.parser.choiceIdex += 1
        textTitle = Label(self, _('The installer script has finished, and '
                                  'will apply the following settings:'))
        textTitle.wrap(parent.get_page_size()[0] - 10)
        # Sub-packages
        self.listSubs = CheckListBox(self, choices=subs)
        self.listSubs.on_box_checked.subscribe(self._on_select_subs)
        for index, fn_key in enumerate(subs):
            if wrye_parser.sublist[fn_key]:
                self.listSubs.lb_check_at_index(index, True)
                self._wiz_parent.ret.select_sub_packages.add(str(fn_key))
        self.plugin_selection = CheckListBox(self, choices=displayed_plugins)
        self.plugin_selection.on_box_checked.subscribe(self._on_select_plugin)
        for index, (key, do_enable) in enumerate(wrye_parser.plugin_enabled.items()):
            if do_enable:
                self.plugin_selection.lb_check_at_index(index, True)
                self._wiz_parent.ret.select_plugins.add(key)
        # Ini tweaks
        self.listInis = ListBox(self, onSelect=self._on_select_ini,
                                choices=list(wrye_parser.iniedits))
        self.listTweaks = ListBox(self)
        self._wiz_parent.ret.ini_edits = wrye_parser.iniedits
        # Apply/install checkboxes
        self.checkApply = CheckBox(self, _('Apply these selections'),
                                   checked=wrye_parser.bAuto)
        self.checkApply.on_checked.subscribe(parent.enable_forward)
        auto = bass.settings['bash.installers.autoWizard']
        self.checkInstall = CheckBox(self, _('Install this package'),
                                     checked=auto)
        self.checkInstall.on_checked.subscribe(self.OnCheckInstall)
        self._wiz_parent.ret.should_install = auto
        # Layout
        layout = VLayout(item_expand=True, spacing=4, items=[
            HBoxedLayout(self, items=[textTitle]),
            (HLayout(item_expand=True, item_weight=1, spacing=5, items=[
                VLayout(item_expand=True,
                        items=[Label(self, _('Sub-Packages')),
                               (self.listSubs, LayoutOptions(weight=1))]),
                VLayout(item_expand=True,
                        items=[Label(self, _('Plugins')),
                               (self.plugin_selection,
                                LayoutOptions(weight=1))]),
             ]), LayoutOptions(weight=1)),
            Label(self, _('INI Tweaks:')),
            (HLayout(item_expand=True, item_weight=1, spacing=5,
                     items=[self.listInis, self.listTweaks]),
             LayoutOptions(weight=1)),
            Label(self, _('Notes:')),
            (TextArea(self, init_text=''.join(wrye_parser.notes),
                      auto_tooltip=False), LayoutOptions(weight=1)),
            HLayout(items=[
                Stretch(),
                VLayout(spacing=2, items=[self.checkApply, self.checkInstall])
            ])
        ])
        layout.apply_to(self)
        parent.enable_forward(wrye_parser.bAuto)
        self._wiz_parent.finishing = True
        self.update_layout()

    def OnCheckInstall(self, is_checked):
        self._wiz_parent.ret.should_install = is_checked

    # Undo selecting/deselection of items for UI consistency
    def _on_select_subs(self, lb_selection_dex):
        self.listSubs.toggle_checked_at_index(lb_selection_dex)

    def _on_select_plugin(self, lb_selection_dex):
        self.plugin_selection.toggle_checked_at_index(lb_selection_dex)

    def _on_select_ini(self, lb_selection_dex, lb_selection_str):
        lines = generateTweakLines(
            self._wiz_parent.ret.ini_edits[lb_selection_str], lb_selection_str)
        self.listTweaks.lb_set_items(lines)
        self.listInis.lb_select_index(lb_selection_dex)

class PageVersions(PageInstaller):
    """Page for displaying what versions an installer requires/recommends and
    what you have installed for Game, *SE, *GE, and Wrye Bash."""
    def __init__(self, parent, bGameOk, gameHave, gameNeed, bSEOk, seHave,
                 seNeed, bGEOk, geHave, geNeed, bWBOk, wbHave, wbNeed):
        PageInstaller.__init__(self, parent)
        bmps = [*map(get_image, ('error_cross.16', 'checkmark.16'))]
        versions_layout = GridLayout(h_spacing=5, v_spacing=5,
                                     stretch_cols=[0, 1, 2, 3])
        versions_layout.append_row([None, Label(self, _('Need')),
                                    Label(self, _('Have'))])
        # Game
        linkGame = Label(self, bush.game.display_name)
        versions_layout.append_row([linkGame, Label(self, gameNeed),
                                    Label(self, gameHave),
                                    StaticBmp(self, bmps[bGameOk])])
        def _link_row(tool, tool_name, need, have, ok, title=None, url=None,
                      tooltip_=None):
            if tool is None or tool_name != '':
                link = HyperlinkLabel(self, title or tool.long_name,
                                      url or tool.url, always_unvisited=True)
                link.tooltip = tooltip_ or tool.url_tip
                versions_layout.append_row([link, Label(self, need),
                                            Label(self, have),
                                            StaticBmp(self, bmps[ok])])
        # Script Extender
        _link_row(bush.game.Se, bush.game.Se.se_abbrev, seNeed, seHave, bSEOk)
        # Graphics extender
        _link_row(bush.game.Ge, bush.game.Ge.ge_abbrev, geNeed, geHave, bGEOk)
        # Wrye Bash
        _link_row(None, '', wbNeed, wbHave, bWBOk, title='Wrye Bash',
                  url='https://www.nexusmods.com/site/mods/591',
                  tooltip_=_('Wrye Bash Download'))
        versions_box = HBoxedLayout(self, _('Version Requirements'),
                                    item_expand=True, item_weight=1,
                                    items=[versions_layout])
        text_warning = Label(self, _('WARNING: The following version '
                                     'requirements are not met for using '
                                     'this installer.'))
        text_warning.wrap(parent.get_page_size()[0] - 20)
        self.checkOk = CheckBox(self, _('Install anyway'))
        self.checkOk.on_checked.subscribe(parent.enable_forward)
        VLayout(items=[
            Stretch(1), (text_warning, LayoutOptions(h_align=CENTER)),
            Stretch(1), (versions_box, LayoutOptions(expand=True, weight=1)),
            Stretch(2),
            (self.checkOk, LayoutOptions(h_align=RIGHT, border=5))
        ]).apply_to(self)
        parent.enable_forward(False)
        self.update_layout()

def _need_have(need, have):
    have_fmt = '.'.join(map(str, have))
    if need == 'None':
        return [1, have_fmt]
    need_ver = LooseVersion('.'.join(map(str, need)))
    have_ver = LooseVersion(have_fmt)
    if have_ver > need_ver:
        return [1, have_fmt]
    elif have_ver < need_ver:
        return [-1, have_fmt]
    else:
        return [0, have_fmt]

class WryeParser(PreParser):
    """A derived class of Parser, for handling BAIN install wizards."""

    def __init__(self, wiz_parent, installer, bAuto):
        super().__init__()
        self._wiz_parent = wiz_parent
        self.installer = installer
        self.bArchive = installer.is_archive
        self._path = installer.fn_key
        if installer and installer.fileRootIdex:
            root_path = installer.extras_dict.get('root_path', '')
            self._path = os.path.join(self._path, root_path)
        self.bAuto = bAuto
        self.page = None
        self.choices = []
        self.choiceIdex = -1
        self.parser_finished = False
        ##: Figure out why BAIN insists on including an empty sub-package
        # everywhere. Broke this part of the code, hence the 'if s' below.
        self.sublist = bolt.FNDict.fromkeys([*installer.subNames][1:], False)
        # all plugins mapped to their must-install state - initially False
        self.plugin_enabled = FNDict.fromkeys(  # type:FNDict[(f:=FName),f]
            sorted(fn_ for sub_plugins in installer.espmMap.values() for fn_ in
                   sub_plugins), False)

    def Continue(self):
        self.page = None
        while self.cLine < len(self.lines):
            newline = self.lines[self.cLine]
            try:
                self.RunLine(newline)
            except ScriptParser.ParserError as e:
                bolt.deprint(f'Error in wizard script: {e}')
                msg = '\n'.join([
                    _('An error occurred in the wizard script:'),
                    _('Line %(line_num)d: %(line_contents)s') % {
                        'line_num': self.cLine,
                        'line_contents': newline.strip('\n')},
                     _('Error: %(script_error)s') % {'script_error': e}])
                return PageError(self._wiz_parent, _('Installer Wizard'), msg)
            except Exception:
                bolt.deprint('Error while running wizard', traceback=True)
                msg = '\n'.join([
                    _('An unhandled error occurred while parsing the wizard:'),
                    _('Line %(line_num)d: %(line_contents)s') % {
                        'line_num': self.cLine,
                        'line_contents': newline.strip('\n')},
                    '',
                    traceback.format_exc(),
                ])
                return PageError(self._wiz_parent, _('Installer Wizard'), msg)
            if self.page:
                return self.page
        self.cLine += 1
        self.cLineStart = self.cLine
        self.parser_finished = True
        return PageFinish(self._wiz_parent, self)

    def Back(self):
        if self.choiceIdex == 0:
            return
        # Rebegin
        self._reset_vars()
        self.parser_finished = False
        i = 0
        while self.ExecCount > 0 and i < len(self.lines):
            line = self.lines[i]
            i += 1
            if line.startswith('EndExec('):
                numLines = int(line[8:-1])
                del self.lines[i-numLines:i]
                i -= numLines
                self.ExecCount -= 1
        self._SelectAll(False)
        self.cLine = 0
        self.reversing = self.choiceIdex-1
        self.choiceIdex = -1
        return self.Continue()

    def _resolve_plugin_rename(self, plugin_name: str) -> FName | None:
        return fn if (fn := FName(plugin_name)) in self.plugin_enabled \
            else None

    # Functions...
    def fnCompareGameVersion(self, obWant):
        want_version = self._TestVersion_Want(obWant)
        return _need_have(want_version, bush.game_version())[0]

    def fnCompareSEVersion(self, seWant):
        if bush.game.Se.se_abbrev:
            ver_path = None
            for ver_file in bush.game.Se.ver_files:
                ver_path = bass.dirs['app'].join(ver_file)
                if ver_path.exists(): break
            return self._TestVersion(self._TestVersion_Want(seWant), ver_path)[
                0]
        else:
            # No script extender available for this game
            return 1

    def fnCompareGEVersion(self, geWant):
        if bush.game.Ge.ge_abbrev != '':
            return self._TestVersion_GE(self._TestVersion_Want(geWant))[0]
        else:
            # No graphics extender available for this game
            return 1

    def fnCompareWBVersion(self, wbWant):
        wbHave = bass.AppVersion
        return bolt.cmp_(LooseVersion(wbHave), LooseVersion(wbWant))

    def fnDataFileExists(self, *rel_paths):
        for rel_path in rel_paths:
            if rel_path in bosh.modInfos:
                continue # It's a (potentially ghosted) plugin, check next
            rel_path_os = to_os_path(bass.dirs['mods'].join(rel_path))
            if not rel_path_os or not rel_path_os.exists():
                return False
        return True

    def fn_get_plugin_lo(self, filename, default_val=-1):
        try:
            return load_order.cached_lo_index(FName(filename))
        except KeyError: # has no LO
            return default_val

    def fn_get_plugin_status(self, filename):
        p_name = FName(filename)
        if p_name in bosh.modInfos.merged: return 3   # Merged
        if load_order.cached_is_active(p_name): return 2  # Active
        if p_name in bosh.modInfos.imported: return 1 # Imported (not active/merged)
        if p_name in bosh.modInfos: return 0          # Inactive
        return -1                                   # Not found

    _for_syntax_from = '\n ' + '\n '.join([
        'For var_name from value_start to value_end',
        'For var_name from value_start to value_end by value_increment',
    ])
    _for_syntax_in = '\n ' + '\n '.join([
        'For var_name in SubPackages',
        'For var_name in subpackage_name',
    ])
    _for_syntax_any = _for_syntax_from + _for_syntax_in
    def kwdFor(self, *args):
        if self.LenFlow() > 0 and self.PeekFlow().type == 'For' and not self.PeekFlow().active:
            #Within an ending For statement, but we hit a new For, so we need to ignore the
            #next 'EndFor' towards THIS one
            self.PushFlow('For', False, ['For', 'EndFor'])
            return
        varname = args[0]
        if varname.type not in [ScriptParser.VARIABLE,ScriptParser.NAME]:
             _err_invalid_for_syntax(self._for_syntax_any)
        if args[1].text == 'from':
            #For varname from value_start to value_end [by value_increment]
            if (len(args) not in [5,7]) or (args[3].text != 'to') or (len(args)==7 and args[5].text != 'by'):
                _err_invalid_for_syntax(self._for_syntax_from)
            start = self.ExecuteTokens([args[2]])
            end = self.ExecuteTokens([args[4]])
            if len(args) == 7:
                by = self.ExecuteTokens([args[6]])
            elif start > end:
                by = -1
            else:
                by = 1
            self.variables[varname.text] = start
            self.PushFlow('For', True, ['For', 'EndFor'], ForType=0, cLine=self.cLine, varname=varname.text, end=end, by=by)
        elif args[1].text == 'in':
            # For sub in SubPackages / For file in sub
            if args[2].text == 'SubPackages':
                if len(args) > 4:
                    _err_invalid_for_syntax(self._for_syntax_in)
                List = sorted(self.sublist)
            else:
                sub_name = self.ExecuteTokens(args[2:])
                subpackage = sub_name if sub_name in self.sublist else None
                if subpackage is None:
                    error(_("Sub-package '%(sp_name)s' does not exist.") % {
                        'sp_name': sub_name})
                List = []
                if self.bArchive:
                    # Archive
                    for file_, _size, _crc in self.installer.fileSizeCrcs:
                        rel = bolt.GPath(file_).relpath(subpackage)
                        if not rel.s.startswith('..'):
                            List.append(rel.s)
                else:
                    sub = bass.dirs['installers'].join(self._path, subpackage)
                    for root_dir, dirs, files in sub.walk(relative=True):
                        for file_ in files:
                            rel = root_dir[1:].join(file_) # chop off path sep
                            List.append(rel.s)
                List.sort()
            if not List:
                self.variables[varname.text] = ''
                self.PushFlow('For', False, ['For','EndFor'])
            else:
                self.variables[varname.text] = List[0]
                self.PushFlow('For', True, ['For', 'EndFor'], ForType=1,
                              cLine=self.cLine, varname=varname.text,
                              List=List, index=0)
        else:
            _err_invalid_for_syntax(self._for_syntax_any)

    def _KeywordSelect(self, bMany, name_, *args):
        args = list(args)
        if self.LenFlow() > 0 and self.PeekFlow().type == 'Select' and not self.PeekFlow().active:
            #We're inside an invalid Case for a Select already, so just add a blank FlowControl for
            #this select
            self.PushFlow('Select', False, ['SelectOne', 'SelectMany', 'EndSelect'])
            return
        main_desc = args.pop(0)
        if len(args) % 3:
            error(_("Missing arguments to '%(keyword_name)s'.") % {
                'keyword_name': name_})
        images_ = []
        titles = {}
        descs = []
        image_paths = []
        while len(args):
            title = args.pop(0)
            is_default = title[0] == '|'
            if is_default:
                title = title[1:]
            titles[title] = is_default
            descs.append(args.pop(0))
            images_.append(args.pop(0))
        if self.bAuto:
            # auto wizard will resolve SelectOne/SelectMany only if default(s)
            # were specified.
            defaults_ = [t for t, dflt in titles.items() if dflt]
            if not bMany: defaults_ = defaults_[:1]
            if defaults_:
                self.PushFlow('Select', False,
                              ['SelectOne', 'SelectMany', 'Case',
                               'Default', 'EndSelect'], values=defaults_,
                              hitCase=False)
                return
        self.choiceIdex += 1
        if self.reversing:
            # We're using the 'Back' button
            self.reversing -= 1
            self.PushFlow('Select', False, ['SelectOne', 'SelectMany', 'Case', 'Default', 'EndSelect'], values = self.choices[self.choiceIdex], hitCase=False)
            return
        imageJoin = self._wizard_dir.join
        for i in images_:
            # Try looking inside the package first, then look if it's using one
            # of the images packaged with Wrye Bash (from
            # Mopy/bash/images/Wizard Images)
            # Note that these are almost always Windows paths, so we have to
            # convert them if we're on Linux
            wiz_img_path = to_os_path(imageJoin(i))
            if wiz_img_path and wiz_img_path.is_file():
                image_paths.append(wiz_img_path)
            elif i.lower().startswith('wizard images'):
                std_img_path = to_os_path(os.path.join(get_image_dir(), i))
                if std_img_path and std_img_path.is_file():
                    image_paths.append(std_img_path)
                else:
                    image_paths.append(None)
            else:
                image_paths.append(None)
        self.page = PageSelect(self._wiz_parent, bMany, main_desc, titles,
                               descs, image_paths)

    def _SelectSubPackage(self, bSelect, subpackage):
        if subpackage not in self.sublist:
            error(_("Sub-package '%(sp_name)s' is not a part of the "
                    "package.") % {'sp_name': subpackage})
        self.sublist[subpackage] = bSelect
        for fn_espm in self.installer.espmMap[subpackage]:
            if bSelect:
                self._select_plugin(True, fn_espm)
            else: # check if some other active subpackage includes fn_espm
                for fn_sub, is_act in self.sublist.items():
                    if is_act and fn_espm in self.installer.espmMap[fn_sub]:
                        return
                self._select_plugin(False, fn_espm)

    def _SelectAll(self, bSelect):
        self.sublist = FNDict.fromkeys(self.sublist, bSelect)
        self.plugin_enabled = FNDict.fromkeys(self.plugin_enabled, bSelect)

    def _select_plugin(self, should_activate, plugin_name):
        resolved_name = self._resolve_plugin_rename(plugin_name)
        if resolved_name:
            self.plugin_enabled[resolved_name] = should_activate
        else:
            error(_("Plugin '%(selected_plugin_name)s' is not a part of the "
                    "package.") % {'selected_plugin_name': plugin_name})

    def _select_all_plugins(self, should_activate):
        self.plugin_enabled = FNDict.fromkeys(self.plugin_enabled,
                                              should_activate)

    def kwdRequireVersions(self, game, se='None', ge='None', wbWant='0.0'):
        if self.bAuto: return
        gameWant = self._TestVersion_Want(game)
        if gameWant == 'None': game = 'None'
        seWant = self._TestVersion_Want(se)
        if seWant == 'None': se = 'None'
        geWant = self._TestVersion_Want(ge)
        if geWant == 'None': ge = 'None'
        if not wbWant: wbWant = '0.0'
        wbHave = bass.AppVersion
        need_have = _need_have(gameWant, bush.game_version())
        bGameOk = need_have[0] >= 0
        gameHave = need_have[1]
        if bush.game.Se.se_abbrev:
            ver_path = None
            for ver_file in bush.game.Se.ver_files:
                ver_path = bass.dirs['app'].join(ver_file)
                if ver_path.exists(): break
            need_have = self._TestVersion(seWant, ver_path)
            bSEOk = need_have[0] >= 0
            seHave = need_have[1]
        else:
            bSEOk = True
            seHave = 'None'
        if bush.game.Ge.ge_abbrev != '':
            need_have = self._TestVersion_GE(geWant)
            bGEOk = need_have[0] >= 0
            geHave = need_have[1]
        else:
            bGEOk = True
            geHave = 'None'
        bWBOk = LooseVersion(wbHave) >= LooseVersion(wbWant)
        if not bGameOk or not bSEOk or not bGEOk or not bWBOk:
            self.page = PageVersions(self._wiz_parent, bGameOk, gameHave, game,
                                     bSEOk, seHave, se, bGEOk, geHave, ge,
                                     bWBOk, wbHave, wbWant)

    def _TestVersion_GE(self, want):
        if isinstance(bush.game.Ge.exe, bytes):
            files = [bass.dirs['mods'].join(bush.game.Ge.exe)]
        else:
            files = [bass.dirs['mods'].join(*x) for x in bush.game.Ge.exe]
        need_have = [-1, 'None']
        for file in reversed(files):
            need_have = self._TestVersion(want, file)
            if need_have[1] != 'None':
                return need_have
        return need_have

    @staticmethod
    def _TestVersion_Want(want):
        try:
            need = tuple(int(i) for i in want.split('.'))
        except ValueError:
            need = 'None'
        return need

    @staticmethod
    def _TestVersion(need, file_, have=None):
        if not have and file_ and file_.exists():
            have = get_file_version(file_.s)
        if have:
            return _need_have(need, have)
        elif need == 'None':
            return [0, 'None']
        return [-1, 'None']

    def kwdReturn(self):
        self.page = PageFinish(self._wiz_parent, self)

    def kwdCancel(self, msg=_('No reason given')):
        self.page = PageError(self._wiz_parent, _('The installer wizard was canceled:'), msg)
