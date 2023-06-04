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
#  Wrye Bash copyright (C) 2005-2009 Wrye, 2010-2023 Wrye Bash Team
#  https://github.com/wrye-bash
#
# =============================================================================

__author__ = u'Ganda'

from collections import defaultdict

from .. import balt, bass, bolt, bush
from ..balt import EnabledLink, Links, colors
from ..env import get_file_version, get_game_version_fallback, to_os_path
from ..fomod import FailedCondition, FomodInstaller, GroupType, \
    InstallerGroup, InstallerOption, InstallerPage, OptionType
from ..gui import CENTER, TOP, BusyCursor, Button, CancelButton, CheckBox, \
    DialogWindow, HLayout, HorizontalLine, Label, LayoutOptions, OkButton, \
    PictureWithCursor, RadioButton, ScrollableWindow, Stretch, Table, \
    TextArea, VBoxedLayout, VLayout, WizardDialog, WizardPage, \
    copy_text_to_clipboard, showWarning
from ..wbtemp import cleanup_temp_dir

class FomodInstallInfo(object):
    __slots__ = (u'canceled', u'install_files', u'should_install')

    def __init__(self):
        # canceled: true if the user canceled or if an error occurred
        self.canceled = False
        # install_files: file->dest mapping of files to install
        self.install_files = bolt.LowerDict()
        # should_install: boolean on whether to install the files
        self.should_install = True

class ValidatorPopup(DialogWindow):
    """Implements the error popup shown to the user when schema validation
    fails."""
    _def_size = (650, 400)
    _warning_msg = _(
        'The ModuleConfig.xml file used to specify the FOMOD installer for '
        'this package does not conform to the FOMOD specification. This '
        'should be reported to and fixed by the mod author. Please share the '
        'error log shown below with them as well. You can use the "Copy Log" '
        'button to easily copy it.') + '\n\n' + _(
        'This warning can also be turned off globally via "Settings > '
        'Validate FOMODs", but be aware that by doing so, Wrye Bash may fail '
        'to install or incorrectly install invalid packages.') + '\n\n'

    def __init__(self, parent, fm_name, error_lines):
        super().__init__(parent,
            title=_('FOMOD Validation Failed - %(fomod_title)s') % {
                'fomod_title': fm_name},
            sizes_dict=balt.sizes)
        copy_log_btn = Button(self, _('Copy Log'))
        copy_log_btn.tooltip = _('Copies the contents of the error log to the '
                                 'clipboard.')
        copy_log_btn.on_clicked.subscribe(self._handle_copy)
        self._error_log = TextArea(self,
            self._warning_msg + '\n'.join(error_lines), auto_tooltip=False,
            editable=False)
        continue_btn = OkButton(self, _('Continue Anyway'))
        continue_btn.tooltip = _(
            'If you continue regardless, Wrye Bash may fail to install the '
            'package or have to make guesses as to what was intended.')
        VLayout(item_expand=True, border=10, spacing=6, items=[
            (HLayout(spacing=10, items=[
                (balt.staticBitmap(self), LayoutOptions(v_align=TOP)),
                (self._error_log, LayoutOptions(expand=True, weight=1)),
            ]), LayoutOptions(weight=1)),
            HLayout(items=[
                Stretch(),
                copy_log_btn,
            ]),
            HorizontalLine(self),
            HLayout(items=[
                continue_btn,
                Stretch(),
                CancelButton(self, _('Cancel Installation')),
            ]),
        ]).apply_to(self)

    def _handle_copy(self):
        """Called when the Copy Log button is clicked. Simply copies the
        contents of the error log to the clipboard, minus the warning
        message."""
        copy_text_to_clipboard(
            self._error_log.text_content[len(self._warning_msg):])

class InstallerFomod(WizardDialog):
    _def_size = (600, 500)

    def __init__(self, parent_window, target_installer, show_install_chkbox):
        # saving this list allows for faster processing of the files the fomod
        # installer will return.
        files_list = [a[0] for a in target_installer.fileSizeCrcs]
        # All extracted files need to be specified relative to this root path
        self.installer_root = (
            target_installer.extras_dict.get(u'root_path', u'')
            if target_installer.fileRootIdex else u'')
        self._fomod_dir = target_installer.get_fomod_file_dir()
        fm_file = self._fomod_dir.join(target_installer.has_fomod_conf).s
        self._show_install_checkbox = show_install_chkbox
        # Get the game version, be careful about Windows Store games
        test_path = bass.dirs[u'app'].join(bush.game.version_detect_file)
        try:
            gver = get_file_version(test_path.s)
            if gver == (0, 0, 0, 0) and bush.ws_info.installed:
                gver = get_game_version_fallback(test_path, bush.ws_info)
        except OSError:
            gver = get_game_version_fallback(test_path, bush.ws_info)
        version_string = u'.'.join([str(i) for i in gver])
        self.fomod_parser = FomodInstaller(
            fm_file, files_list, self.installer_root, bass.dirs[u'mods'],
            version_string)
        super(InstallerFomod, self).__init__(
            parent_window, sizes_dict=bass.settings,
            title=_('FOMOD Installer - %(fomod_title)s') % {
                'fomod_title': self.fomod_parser.fomod_name},
            size_key='bash.fomod.size', pos_key='bash.fomod.pos')
        self._is_arch = target_installer.is_archive
        self.fm_ret = FomodInstallInfo()

    def save_size(self): ##: needed?
        # Otherwise, regular resize, save the size if we're not maximized
        self.on_closing(destroy=False)

    def _has_next_page(self):
        return self.fomod_parser.has_next()

    def _has_prev_page(self):
        return self.fomod_parser.has_prev()

    def _get_next_page(self):
        # If we're still on the dummy page, then we're only changing to the
        # first page, so skip trying to save user selections
        if self._curr_page != self._dummy_page:
            sel_opts = self._curr_page.on_next()
        else:
            sel_opts = None
        next_page = self.fomod_parser.move_to_next(sel_opts)
        if next_page is None:
            return PageFinish(self, self._show_install_checkbox)
        else:
            return PageSelect(self, next_page)

    def _get_prev_page(self):
        # Pop back to the last state and resume execution
        prev_page, prev_selected = self.fomod_parser.move_to_prev()
        if prev_page: # at the start
            gui_page = PageSelect(self, prev_page)
            gui_page.apply_selection(prev_selected)
            return gui_page
        return None

    def _cancel_wizard(self):
        self.fm_ret.canceled = True

    def run_fomod(self):
        try:
            self.fomod_parser.check_start_conditions()
        except FailedCondition as e:
            fm_warning = _('This installer cannot start due to the following '
                           'unmet conditions:') + '\n' + '\n'.join(
                f' - {l}' for l in str(e).splitlines())
            showWarning(self, fm_warning, title=_('Cannot Run Installer'),
                        do_center=True)
            self._cancel_wizard()
        else:
            self._run_wizard()
            # Invert keys and values ahead of time here, so that BAIN doesn't
            # have to do it just in time
            self.fm_ret.install_files = bolt.LowerDict({
                v: k for k, v
                in self.fomod_parser.get_fomod_files().items()})
        if self._is_arch:
            cleanup_temp_dir(self._fomod_dir)
        return self.fm_ret

    def validate_fomod(self):
        """Validates this FOMOD installer against the schema."""
        if not bass.settings['bash.installers.validate_fomods']:
            return True
        was_valid, error_log = self.fomod_parser.try_validate()
        if was_valid:
            return True
        error_lines = []
        for xml_error in error_log:
            error_lines.append(f'Line {xml_error.line}, column '
                               f'{xml_error.column}:')
            error_lines.append(f'  {xml_error.message}')
            error_lines.append(f'  XML Path: {xml_error.path}')
            error_lines.append('')
        return ValidatorPopup.display_dialog(self,
            self.fomod_parser.fomod_name, error_lines)

class PageInstaller(WizardPage):
    """Base class for all the parser wizard pages, just to handle a couple
    simple things here."""

    def __init__(self, page_parent: InstallerFomod):
        super(PageInstaller, self).__init__(page_parent)
        self._page_parent = page_parent

    def on_next(self):
        """Create flow control objects etc, implemented by sub-classes."""

class PageSelect(PageInstaller):
    """A Page that shows a message up top, with a selection box on the left
    (multi- or single- selection), with an optional associated image and
    description for each option, shown when that item is selected."""
    # Syntax: tuple containing text to show for an option of this type and a
    # boolean indicating whether to mark the text as a warning or not
    _option_type_info = defaultdict(lambda: ('', False), {
        OptionType.REQUIRED: (_('This option is required.'), False),
        OptionType.RECOMMENDED: (_('This option is recommended.'), False),
        OptionType.COULD_BE_USABLE: (_('This option could result in '
                                       'instability.'), True),
        OptionType.NOT_USABLE: (_('This option cannot be selected.'), True),
    })
    group_option_map: defaultdict[InstallerGroup, list[RadioButton | CheckBox]]

    def __init__(self, page_parent, inst_page: InstallerPage):
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
            group_force_selection = gtype in (GroupType.SELECT_EXACTLY_ONE,
                                              GroupType.SELECT_AT_LEAST_ONE)
            # A set of all option checkables to block in this group
            checkables_to_block = set()
            # Whether or not to block *all* checkables in this group. Whenever
            # there is a required option in a ExactlyOne/AtMostOne group all,
            # other options need to be blocked to ensure the required stays
            # selected.
            block_all_in_group = False
            for option in grp: # type: InstallerOption
                otype = option.option_type
                if gtype in (GroupType.SELECT_EXACTLY_ONE,
                             GroupType.SELECT_AT_MOST_ONE):
                    checkable = RadioButton(panel_groups,
                                            rb_label=option.option_name,
                                            is_group=option is grp[0])
                else:
                    checkable = CheckBox(panel_groups,
                                         cb_label=option.option_name)
                    # Mass selection makes no sense on radio buttons
                    checkable.on_context.subscribe(self._handle_context_menu)
                    if gtype is GroupType.SELECT_ALL:
                        checkable.is_checked = True
                        any_selected = True
                        checkables_to_block.add(checkable)
                # Remember the first checkable we created for later
                if not first_checkable:
                    first_checkable = checkable
                if otype is OptionType.REQUIRED:
                    checkable.is_checked =  True
                    any_selected = True
                    if gtype in (GroupType.SELECT_EXACTLY_ONE,
                                 GroupType.SELECT_AT_MOST_ONE):
                        block_all_in_group = True
                    else:
                        checkables_to_block.add(checkable)
                elif otype is OptionType.RECOMMENDED:
                    if not any_selected or not group_force_selection:
                        checkable.is_checked = True
                        any_selected = True
                elif otype in (OptionType.OPTIONAL,
                               OptionType.COULD_BE_USABLE):
                    if first_selectable is None:
                        first_selectable = checkable
                elif otype is OptionType.NOT_USABLE:
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
            if gtype is GroupType.SELECT_AT_MOST_ONE:
                none_button = RadioButton(panel_groups, rb_label=_('None'))
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
        self.update_layout()

    def _open_image(self, _dclick_ignored=0):
        # May be None if we're on Linux and a path didn't end up existing
        if self._current_image:
            self._current_image.start()

    def _handle_block_user(self, block_checkable):
        # As per the RadioButton docstring, we need to implement some custom
        # logic to freeze the entire radio button group
        ##: Could maybe be de-wx'd further and moved to gui? RadioButtonGroup?
        frozen_state = self._frozen_states.get(block_checkable)
        if frozen_state:
            for chk, chk_state in frozen_state.items():
                chk.is_checked = chk_state
        block_option = self.checkable_to_option[block_checkable]
        # Adjust the warning based on whether the problem is due to this option
        # or another one in the same group
        if block_option.option_type is OptionType.NOT_USABLE:
            showWarning(self, _('This option cannot be enabled.'))
        elif isinstance(block_checkable, CheckBox):
            showWarning(self,
                        _('This option is required and cannot be disabled.'))
        else: # RadioButton
            showWarning(self, _('One of the options in this group is required '
                'and cannot be unselected by choosing a different option.'))

    def _handle_context_menu(self, checkable):
        """Shows the right click menu with mass (de)select options."""
        self._group_links.popup_menu(self, checkable)

    def _set_option_details(self, checkable):
        """Sets the image and description on the right side based on the
        specified checkable."""
        option = self.checkable_to_option[checkable]
        opt_img = option.option_image
        # Note that these are almost always Windows paths, so we have to
        # convert them if we're on Linux
        opt_img_path = to_os_path(self._page_parent._fomod_dir.join(
            self._page_parent.installer_root, opt_img))
        self._current_image = opt_img_path # To allow opening via double click
        try:
            final_image = self._img_cache[opt_img]
        except KeyError:
            final_image = opt_img_path
        self._img_cache[opt_img] = self._bmp_item.set_bitmap(final_image)
        # Check if we need to display a special string above the description
        type_desc, type_warn = self._option_type_info[option.option_type]
        cg_type = self.checkable_to_group[checkable].group_type
        if cg_type is GroupType.SELECT_ALL:
            # Ugh. Some FOMODs set SelectAll but don't mark the options as
            # required. In such a case, we let the SelectAll win.
            type_desc, type_warn = self._option_type_info[OptionType.REQUIRED]
        self._option_type_label.label_text = type_desc
        if type_warn:
            self._option_type_label.set_foreground_color(
                colors[u'default.warn'])
        else:
            self._option_type_label.reset_foreground_color()
        self._text_item.text_content = option.option_desc
        self.update_layout() # Otherwise the h_align won't work

    def show_fomod_error(self, fm_error):
        fm_error += u'\n' + _(u'Please ensure the FOMOD files are correct and '
                              u'contact the Wrye Bash Dev Team.')
        showWarning(self, fm_error, do_center=True)

    def on_next(self):
        sel_options = []
        for grp, option_chks in self.group_option_map.items():
            opts_selected = [self.checkable_to_option[c] for c in option_chks
                             if c.is_checked]
            option_len = len(opts_selected)
            gtype = grp.group_type
            if gtype is GroupType.SELECT_EXACTLY_ONE and option_len != 1:
                fm_err = _(u'Group "{}" should have exactly 1 option selected '
                           u'but has {}.').format(grp.group_name, option_len)
                self.show_fomod_error(fm_err)
            elif gtype is GroupType.SELECT_AT_MOST_ONE and option_len > 1:
                fm_err = _(u'Group "{}" should have at most 1 option selected '
                           u'but has {}.').format(grp.group_name, option_len)
                self.show_fomod_error(fm_err)
            elif gtype is GroupType.SELECT_AT_LEAST_ONE and option_len < 1:
                fm_err = _(u'Group "{}" should have at least 1 option '
                           u'selected but has {}.').format(grp.group_name,
                                                           option_len)
                self.show_fomod_error(fm_err)
            elif (gtype is GroupType.SELECT_ALL
                  and option_len != len(option_chks)):
                fm_err = _(u'Group "{}" should have all options selected but '
                           u'has only {}.').format(grp.group_name,
                                                   option_len)
                self.show_fomod_error(fm_err)
            sel_options.extend(opts_selected)
        return sel_options

    def apply_selection(self, opt_selection):
        for checkable_list in self.group_option_map.values():
            for checkable in checkable_list:
                if self.checkable_to_option[checkable] in opt_selection:
                    checkable.is_checked = True

class PageFinish(PageInstaller):
    def __init__(self, page_parent, show_install_chkbox):
        super(PageFinish, self).__init__(page_parent)
        check_install = CheckBox(
            self, _(u'Install this package'),
            checked=self._page_parent.fm_ret.should_install)
        check_install.on_checked.subscribe(self._on_check_install)
        check_install.visible = show_install_chkbox
        use_table = bass.settings[u'bash.fomod.use_table']
        check_tab_view = CheckBox(
            self, _(u'Use Table View'), checked=use_table,
            chkbx_tooltip=_(u'Switch to a table-based view of the files that '
                            u'are going to be installed.'))
        check_tab_view.on_checked.subscribe(self._on_switch_output)
        # This can take a bit for very large FOMOD installs
        with BusyCursor():
            installer_output = self._page_parent.fomod_parser.get_fomod_files()
            # Create the two alternative output displays and fill them with
            # data from the FOMOD parser
            self._output_text = TextArea(
                self, editable=False, auto_tooltip=False,
                init_text=self.display_files(installer_output))
            sorted_output = bolt.dict_sort(installer_output,
                key_f=lambda k: installer_output[k].lower())  # sort by source
            sorted_src = []
            sorted_dst = []
            for d, s in sorted_output:
                sorted_src.append(s)
                sorted_dst.append(d)
            output_table_data = {
                _(u'Source'): sorted_src,
                _(u'Destination'): sorted_dst,
            }
            self._output_table = Table(self, output_table_data, editable=False)
        # Choose which output view to use, then create the layout
        self._update_output()
        VLayout(spacing=10, item_expand=True, items=[
            (Label(self, _(u'Files To Install')),
             LayoutOptions(expand=False, h_align=CENTER)),
            (self._output_table, LayoutOptions(weight=1)),
            (self._output_text, LayoutOptions(weight=1)),
            HLayout(items=[check_install, Stretch(), check_tab_view]),
        ]).apply_to(self)
        self.update_layout()

    def _on_check_install(self, checked):
        self._page_parent.fm_ret.should_install = checked

    def _on_switch_output(self, checked):
        bass.settings[u'bash.fomod.use_table'] = checked
        self._update_output()

    def _update_output(self):
        use_table = bass.settings[u'bash.fomod.use_table']
        self._output_table.visible = use_table
        self._output_text.visible = not use_table
        self.update_layout()

    @staticmethod
    def display_files(file_dict):
        if not file_dict: return u''
        lines = [f'{v} -> {k}' for k, v in file_dict.items()]
        lines.sort(key=str.lower)
        return u'\n'.join(lines)

# Some links for easier mass (de)selection of options
# self.window points to the InstallerPage that we're on, self.selected points
# to the _ACheckable instance that was right clicked.
# FIXME(inf) PyCharm spits out annoying type warnings for this section and I
#  can't update the type hints in balt.py due to cyclic imports :(
class _GroupLink(EnabledLink):
    """Select, deselect or toggle all options in a group."""

    def _enable(self):
        # Disable for required options, user can't change those
        return not self.selected.is_blocked()

    @property
    def link_help(self):
        return self._help % {
            'curr_fomod_group': self.selected_group.group_name}

    @property
    def selected_group(self) -> InstallerGroup:
        """Returns the group that the clicked on option belongs to."""
        return self.window.checkable_to_group[self.selected]

    def Execute(self):
        for checkable in self.window.group_option_map[self.selected_group]:
            # NotUsable options can't ever be enabled, so skip those
            otype = self.window.checkable_to_option[checkable].option_type
            checkable.is_checked = (otype is not OptionType.NOT_USABLE
                                    and self._should_enable(checkable))

    def _should_enable(self, checkable):
        """Returns True if the specified checkable should be enabled."""
        raise NotImplementedError

class _Group_SelectAll(_GroupLink):
    """Select all options in the selected group."""
    _text = _('Select All')
    _help = _("Selects all options in the '%(curr_fomod_group)s' group.")

    def _should_enable(self, checkable): return True

class _Group_DeselectAll(_GroupLink):
    """Deselect all options in the selected group."""
    _text = _('Deselect All')
    _help = _("Deselects all options in the '%(curr_fomod_group)s' group.")

    def _should_enable(self, checkable): return False

class _Group_ToggleAll(_GroupLink):
    """Toggle all options in the selected group."""
    _text = _('Toggle Selection')
    _help = _("Deselects all selected options in the '%(curr_fomod_group)s' "
              "group and vice versa.")

    def _should_enable(self, checkable): return not checkable.is_checked
