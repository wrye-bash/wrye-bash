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
#  Wrye Bash copyright (C) 2005-2009 Wrye, 2010-2020 Wrye Bash Team
#  https://github.com/wrye-bash
#
# =============================================================================

__author__ = u'Ganda'

from collections import defaultdict
import wx.adv as wiz

from .. import balt, bass, bolt, bush, env
from ..balt import EnabledLink, Links, colors
from ..exception import AbstractError
from ..fomod import FailedCondition, FomodInstaller, InstallerGroup, \
    InstallerOption, InstallerPage
from ..gui import CENTER, CheckBox, VBoxedLayout, HLayout, Label, \
    LayoutOptions, TextArea, VLayout, WizardDialog, EventResult, \
    PictureWithCursor, RadioButton, ScrollableWindow, Stretch, Table, \
    BusyCursor

class FomodInstallInfo(object):
    __slots__ = (u'canceled', u'install_files', u'should_install')

    def __init__(self):
        # canceled: true if the user canceled or if an error occurred
        self.canceled = False
        # install_files: file->dest mapping of files to install
        self.install_files = bolt.LowerDict()
        # should_install: boolean on whether to install the files
        self.should_install = True

class InstallerFomod(WizardDialog):
    _def_size = (600, 500)

    def __init__(self, parent_window, target_installer):
        # True prevents actually moving to the 'next' page.
        # We use this after the "Next" button is pressed,
        # while the parser is running to return the _actual_ next page
        self.block_change = True
        # 'finishing' is to allow the "Next" button to be used
        # when its name is changed to 'Finish' on the last page of the wizard
        self.finishing = False
        # saving this list allows for faster processing of the files the fomod
        # installer will return.
        self.files_list = [a[0] for a in target_installer.fileSizeCrcs]
        # All extracted files need to be specified relative to this root path
        self.installer_root = (
            target_installer.extras_dict.get(u'root_path', u'')
            if target_installer.fileRootIdex else u'')
        fm_file = target_installer.fomod_file().s
        gver = env.get_file_version(bass.dirs[u'app'].join(
            bush.game.version_detect_file).s)
        self.fomod_parser = FomodInstaller(
            fm_file, self.files_list, self.installer_root, bass.dirs[u'mods'],
            u'.'.join([unicode(i) for i in gver]))
        super(InstallerFomod, self).__init__(
            parent_window, sizes_dict=bass.settings,
            title=_(u'FOMOD Installer - %s') % self.fomod_parser.fomod_name,
            size_key=u'bash.fomod.size', pos_key=u'bash.fomod.pos')
        self.is_arch = target_installer.is_archive()
        if self.is_arch:
            self.archive_path = bass.getTempDir()
        else:
            self.archive_path = target_installer.ipath
        # 'dummy' page tricks the wizard into always showing the "Next" button
        class _PageDummy(wiz.WizardPage): pass
        self.fm_dummy = _PageDummy(self._native_widget)
        # Intercept the changing event so we can implement 'block_change'
        self.on_wiz_page_change.subscribe(self.on_change)
        self.fm_ret = FomodInstallInfo()
        self.first_page = True

    def save_size(self):
        # Otherwise, regular resize, save the size if we're not maximized
        self.on_closing(destroy=False)

    def on_change(self, is_forward, evt_page):
        if is_forward:
            if not self.finishing:
                # Next, continue script execution
                if self.block_change:
                    # Tell the current page that next was pressed,
                    # So the parser can continue parsing,
                    # Then show the page that the parser returns,
                    # rather than the dummy page
                    sel_opts = evt_page.on_next()
                    self.block_change = False
                    next_page = self.fomod_parser.move_to_next(sel_opts)
                    if next_page is None:
                        self.finishing = True
                        self._native_widget.ShowPage(
                            PageFinish(self))
                    else:
                        self.finishing = False
                        self._native_widget.ShowPage(
                            PageSelect(self, next_page))
                    return EventResult.CANCEL
                else:
                    self.block_change = True
        else:
            # Previous, pop back to the last state,
            # and resume execution
            self.block_change = False
            self.finishing = False
            prev_page, prev_selected = self.fomod_parser.move_to_prev()
            if prev_page: # at the start
                gui_page = PageSelect(self, prev_page)
                gui_page.apply_selection(prev_selected)
                self._native_widget.ShowPage(gui_page)
            return EventResult.CANCEL

    def run_fomod(self):
        try:
            first_page = self.fomod_parser.start_fomod()
        except FailedCondition as e:
            fm_warning = _(u'This installer cannot start due to the following '
                           u'unmet conditions:') + u'\n'
            for l in str(e).splitlines():
                fm_warning += u'  {}\n'.format(l)
            balt.showWarning(self, fm_warning,
                             title=_(u'Cannot Run Installer'), do_center=True)
            self.fm_ret.canceled = True
        else:
            if first_page is not None:  # if installer has any gui pages
                self.fm_ret.canceled = not self._native_widget.RunWizard(
                    PageSelect(self, first_page))
            # Invert keys and values ahead of time here, so that BAIN doesn't
            # have to do it just in time
            self.fm_ret.install_files = bolt.LowerDict({
                v: k for k, v
                in self.fomod_parser.get_fomod_files().iteritems()})
        # Clean up temp files
        if self.is_arch:
            bass.rmTempDir()
        return self.fm_ret

class PageInstaller(wiz.WizardPage):
    """Base class for all the parser wizard pages, just to handle a couple
    simple things here."""

    def __init__(self, page_parent):
        super(PageInstaller, self).__init__(page_parent._native_widget)
        self._page_parent = page_parent # type: InstallerFomod
        self._enable_forward(True)

    def _enable_forward(self, do_enable):
        self._page_parent.enable_forward_btn(do_enable)

    def GetNext(self):
        return self._page_parent.fm_dummy

    def GetPrev(self):
        if self._page_parent.fomod_parser.has_prev():
            return self._page_parent.fm_dummy
        return None

    def on_next(self):
        """Create flow control objects etc, implemented by sub-classes."""
        pass

class PageSelect(PageInstaller):
    """A Page that shows a message up top, with a selection box on the left
    (multi- or single- selection), with an optional associated image and
    description for each option, shown when that item is selected."""
    _option_type_info = defaultdict(lambda: (u'', colors.BLACK))
    _option_type_info[u'Required'] = (_(u'This option is required.'),
                                      colors.BLACK)
    _option_type_info[u'Recommended'] = (_(u'This option is recommended.'),
                                         colors.BLACK)
    _option_type_info[u'CouldBeUsable'] = (_(u'This option could result in '
                                             u'instability.'), colors.RED)
    _option_type_info[u'NotUsable'] = (_(u'This option cannot be selected.'),
                                       colors.RED)

    def __init__(self, page_parent, inst_page):
        """:type inst_page: InstallerPage"""
        super(PageSelect, self).__init__(page_parent)
        # For runtime retrieval of option/checkable info
        self.checkable_to_option = {}
        self.checkable_to_group = {}
        self.group_option_map = defaultdict(list)
        # To undo user changes to 'frozen' radio button groups
        self._frozen_states = {}
        self._current_image = None
        self._img_cache = {} # creating images can be really expensive
        self._bmp_item = PictureWithCursor(self, 0, 0, background=None)
        self._bmp_item.on_mouse_middle_up.subscribe(self._open_image)
        self._bmp_item.on_mouse_left_dclick.subscribe(self._open_image)
        # Shows required/recommended/etc. status of hovered-over option
        self._option_type_label = Label(self, u'')
        self._text_item = TextArea(self, editable=False, auto_tooltip=False)
        # Create links to facilitate mass (de)selection
        self._group_links = Links()
        self._group_links.append(_Group_SelectAll())
        self._group_links.append(_Group_DeselectAll())
        self._group_links.append(_Group_ToggleAll())
        panel_groups = ScrollableWindow(self)
        groups_layout = VLayout(spacing=5, item_expand=True)
        first_checkable = None
        for grp in inst_page: # type: InstallerGroup
            options_layout = VBoxedLayout(panel_groups, title=grp.group_name,
                spacing=2)
            first_selectable = None
            any_selected = False
            gtype = grp.group_type
            group_force_selection = gtype in (u'SelectExactlyOne',
                                              u'SelectAtLeastOne')
            # A set of all option checkables to block in this group
            checkables_to_block = set()
            # Whether or not to block *all* checkables in this group. Whenever
            # there is a required option in a ExactlyOne/AtMostOne group all,
            # other options need to be blocked to ensure the required stays
            # selected.
            block_all_in_group = False
            for option in grp: # type: InstallerOption
                otype = option.option_type
                if gtype in (u'SelectExactlyOne', u'SelectAtMostOne'):
                    checkable = RadioButton(panel_groups,
                                            label=option.option_name,
                                            is_group=option is grp[0])
                else:
                    checkable = CheckBox(panel_groups,
                                         label=option.option_name)
                    # Mass selection makes no sense on radio buttons
                    checkable.on_context.subscribe(self._handle_context_menu)
                    if gtype == u'SelectAll':
                        checkable.is_checked = True
                        any_selected = True
                        checkables_to_block.add(checkable)
                # Remember the first checkable we created for later
                if not first_checkable:
                    first_checkable = checkable
                if otype == u'Required':
                    checkable.is_checked =  True
                    any_selected = True
                    if gtype in (u'SelectExactlyOne', u'SelectAtMostOne'):
                        block_all_in_group = True
                    else:
                        checkables_to_block.add(checkable)
                elif otype == u'Recommended':
                    if not any_selected or not group_force_selection:
                        checkable.is_checked = True
                        any_selected = True
                elif otype in (u'Optional', u'CouldBeUsable'):
                    if first_selectable is None:
                        first_selectable = checkable
                elif otype == u'NotUsable':
                    checkable.is_checked = False
                    checkables_to_block.add(checkable)
                self.checkable_to_option[checkable] = option
                self.checkable_to_group[checkable] = grp
                options_layout.add(checkable)
                checkable.on_hovered.subscribe(self._set_option_details)
                self.group_option_map[grp].append(checkable)
            # Done adding all options, move on to any last minute tweaks before
            # finalizing the group
            if not any_selected and group_force_selection:
                if first_selectable is not None:
                    first_selectable.is_checked = True
                    any_selected = True
            if block_all_in_group:
                checkables_to_block |= set(self.group_option_map[grp])
            # We'll need this when blocking user interaction with an unusable
            # option
            initial_state = {c: c.is_checked for c in
                             self.group_option_map[grp]}
            if gtype == u'SelectAtMostOne':
                none_button = RadioButton(panel_groups, label=_(u'None'))
                if not any_selected:
                    none_button.is_checked = True
                elif block_all_in_group:
                    checkables_to_block.add(none_button)
                options_layout.add(none_button)
                initial_state[none_button] = none_button.is_checked
            # At this point, all checkables that may have to be blocked have
            # been added, so perform the blocking and create the final layout
            for block_chk in checkables_to_block:
                # For simplicity, we remember the initial state of all blocked
                # checkables in this group even if we don't end up needing it
                self._frozen_states[block_chk] = initial_state
                ##: This will reset user choices if they've checked any usable
                # options before checking an unusable one. We should find a way
                # to catch 'valid' user interactions and update the frozen
                # states at that point. Simply subscribing to all non-blocked
                # on_clicked events does not work because they fire too early
                # (e.g. radio buttons won't have run their logic for unchecking
                # the other button yet).
                block_chk.block_user(self._handle_block_user)
            groups_layout.add(options_layout)
        # Show details for the first option on this page by default
        if first_checkable:
            self._set_option_details(first_checkable)
        groups_layout.apply_to(panel_groups)
        VLayout(spacing=10, item_expand=True, items=[
            (HLayout(spacing=5, item_expand=True, item_weight=1, items=[
                VBoxedLayout(self, title=inst_page.page_name, item_expand=True,
                             item_weight=1, items=[panel_groups]),
                VLayout(spacing=5, item_expand=True, item_weight=1, items=[
                    self._bmp_item,
                    (self._option_type_label,
                     LayoutOptions(expand=False, h_align=CENTER, weight=0)),
                    self._text_item,
                ]),
            ]), LayoutOptions(weight=1)),
        ]).apply_to(self)
        self.Layout()

    def _open_image(self, _dclick_ignored=0):
        if self._current_image: # sanity check
            self._current_image.start()

    def _handle_block_user(self, block_checkable):
        # As per the RadioButton docstring, we need to implement some custom
        # logic to freeze the entire radio button group
        ##: Could maybe be de-wx'd further and moved to gui? RadioButtonGroup?
        frozen_state = self._frozen_states.get(block_checkable)
        if frozen_state:
            for chk, chk_state in frozen_state.iteritems():
                chk.is_checked = chk_state
        block_option = self.checkable_to_option[block_checkable]
        # Adjust the warning based on whether the problem is due to this option
        # or another one in the same group
        if block_option.option_type == u'NotUsable':
            balt.showWarning(self, _(u'This option cannot be enabled.'))
        elif isinstance(block_checkable, CheckBox):
            balt.showWarning(self, _(u'This option is required and cannot be '
                                     u'disabled.'))
        else: # RadioButton
            balt.showWarning(self, _(u'One of the options in this group is '
                                     u'required and cannot be unselected by '
                                     u'choosing a different option.'))

    def _handle_context_menu(self, checkable):
        """Shows the right click menu with mass (de)select options."""
        self._group_links.popup_menu(self, checkable)

    def _set_option_details(self, checkable):
        """Sets the image and description on the right side based on the
        specified checkable."""
        option = self.checkable_to_option[checkable]
        self._enable_forward(True)
        opt_img = self._page_parent.archive_path.join(
            self._page_parent.installer_root, option.option_image)
        self._current_image = opt_img # To allow opening it via double click
        try:
            final_image = self._img_cache[opt_img]
        except KeyError:
            final_image = opt_img
        self._img_cache[opt_img] = self._bmp_item.set_bitmap(final_image)
        # Check if we need to display a special string above the description
        type_desc, type_color = self._option_type_info[option.option_type]
        if self.checkable_to_group[checkable].group_type == u'SelectAll':
            # Ugh. Some FOMODs set SelectAll but don't mark the options as
            # required. In such a case, we let the SelectAll win.
            type_desc, type_color = self._option_type_info[u'Required']
        self._option_type_label.label_text = type_desc
        self._option_type_label.set_foreground_color(type_color)
        self._text_item.text_content = option.option_desc
        self.Layout() # Otherwise the h_align won't work

    def show_fomod_error(self, fm_error):
        fm_error += u'\n' + _(u'Please ensure the FOMOD files are correct and '
                              u'contact the Wrye Bash Dev Team.')
        balt.showWarning(self, fm_error, do_center=True)

    def on_next(self):
        sel_options = []
        for grp, option_chks in self.group_option_map.iteritems():
            opts_selected = [self.checkable_to_option[c] for c in option_chks
                             if c.is_checked]
            option_len = len(opts_selected)
            gtype = grp.group_type
            if gtype == u'SelectExactlyOne' and option_len != 1:
                fm_err = _(u'Group "{}" should have exactly 1 option selected '
                           u'but has {}.').format(grp.group_name, option_len)
                self.show_fomod_error(fm_err)
            elif gtype == u'SelectAtMostOne' and option_len > 1:
                fm_err = _(u'Group "{}" should have at most 1 option selected '
                           u'but has {}.').format(grp.group_name, option_len)
                self.show_fomod_error(fm_err)
            elif gtype == u'SelectAtLeast' and option_len < 1:
                fm_err = _(u'Group "{}" should have at least 1 option '
                           u'selected but has {}.').format(grp.group_name,
                                                           option_len)
                self.show_fomod_error(fm_err)
            elif gtype == u'SelectAll' and option_len != len(option_chks):
                fm_err = _(u'Group "{}" should have all options selected but '
                           u'has only {}.').format(grp.group_name,
                                                   option_len)
                self.show_fomod_error(fm_err)
            sel_options.extend(opts_selected)
        return sel_options

    def apply_selection(self, opt_selection):
        for checkable_list in self.group_option_map.itervalues():
            for checkable in checkable_list:
                if self.checkable_to_option[checkable] in opt_selection:
                    checkable.is_checked = True

class PageFinish(PageInstaller):
    def __init__(self, page_parent):
        super(PageFinish, self).__init__(page_parent)
        check_install = CheckBox(
            self, _(u'Install this package'),
            checked=self._page_parent.fm_ret.should_install)
        check_install.on_checked.subscribe(self._on_check_install)
        use_table = bass.settings[u'bash.fomod.use_table']
        check_output = CheckBox(self, _(u'Use Table View'), checked=use_table,
                                chkbx_tooltip=_(u'Switch to a table-based '
                                                u'view of the files that are '
                                                u'going to be installed.'))
        check_output.on_checked.subscribe(self._on_switch_output)
        # This can take a bit for very large FOMOD installs
        with BusyCursor():
            installer_output = self._page_parent.fomod_parser.get_fomod_files()
            # Create the two alternative output displays and fill them with
            # data from the FOMOD parser
            self._output_text = TextArea(
                self, editable=False, auto_tooltip=False,
                init_text=self.display_files(installer_output))
            sorted_output = sorted(installer_output.iteritems(),
                                   key=lambda t: t[1].lower()) # sort by source
            output_table_data = {
                _(u'Source'): [t[1] for t in sorted_output],
                _(u'Destination'): [t[0] for t in sorted_output],
            }
            self._output_table = Table(self, output_table_data, editable=False)
        # Choose which output view to use, then create the layout
        self._update_output()
        VLayout(spacing=10, item_expand=True, items=[
            (Label(self, _(u'Files To Install')),
             LayoutOptions(expand=False, h_align=CENTER)),
            (self._output_table, LayoutOptions(weight=1)),
            (self._output_text, LayoutOptions(weight=1)),
            HLayout(items=[check_install, Stretch(), check_output]),
        ]).apply_to(self)
        self.Layout()

    def _on_check_install(self, checked):
        self._page_parent.fm_ret.should_install = checked

    def _on_switch_output(self, checked):
        bass.settings[u'bash.fomod.use_table'] = checked
        self._update_output()

    def _update_output(self):
        use_table = bass.settings[u'bash.fomod.use_table']
        self._output_table.visible = use_table
        self._output_text.visible = not use_table
        self.Layout()

    def GetNext(self):
        return None

    @staticmethod
    def display_files(file_dict):
        if not file_dict: return u''
        lines = [u'{} -> {}'.format(v, k) for k, v in file_dict.iteritems()]
        lines.sort(key=unicode.lower)
        return u'\n'.join(lines)

# Some links for easier mass (de)selection of options
# self.window points to the InstallerPage that we're on, self.selected points
# to the _ACheckable instance that was right clicked.
# FIXME(inf) PyCharm spits out annoying type warnings for this section and I
#  can't update the type hints in balt.py due to cyclic imports :(
class _GroupLink(EnabledLink):
    """Select, deselect or toggle all options in a group."""
    def __init__(self):
        super(_GroupLink, self).__init__()

    def _enable(self):
        # Disable for required options, user can't change those
        return not self.selected.is_blocked()

    @property
    def link_help(self):
        return self._help % self.selected_group.group_name

    @property
    def selected_group(self): # type: () -> InstallerGroup
        """Returns the group that the clicked on option belongs to."""
        return self.window.checkable_to_group[self.selected]

class _Group_MassSelect(_GroupLink):
    """Base class for all three types of 'mass select' group links."""
    def Execute(self):
        for checkable in self.window.group_option_map[self.selected_group]:
            # NotUsable options can't ever be enabled, so skip those
            otype = self.window.checkable_to_option[checkable].option_type
            checkable.is_checked = (otype != u'NotUsable'
                                    and self._should_enable(checkable))

    def _should_enable(self, checkable):
        """Returns True if the specified checkable should be enabled."""
        raise AbstractError(u'_enable_checkable not implemented')

class _Group_SelectAll(_Group_MassSelect):
    """Select all options in the selected group."""
    _text = _(u'Select All')
    _help = _(u"Selects all options in the '%s' group.")

    def _should_enable(self, checkable): return True

class _Group_DeselectAll(_Group_MassSelect):
    """Deselect all options in the selected group."""
    _text = _(u'Deselect All')
    _help = _(u"Deselects all options in the '%s' group.")

    def _should_enable(self, checkable): return False

class _Group_ToggleAll(_Group_MassSelect):
    """Toggle all options in the selected group."""
    _text = _(u'Toggle Selection')
    _help = _(u"Deselects all selected options in the '%s' group and vice "
              u'versa.')

    def _should_enable(self, checkable): return not checkable.is_checked
