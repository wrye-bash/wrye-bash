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
#  Wrye Bash copyright (C) 2005-2009 Wrye, 2010-2019 Wrye Bash Team
#  https://github.com/wrye-bash
#
# =============================================================================

__author__ = "Ganda"

from collections import defaultdict
import wx
import wx.wizard as wiz

from .. import balt, bass, bolt, bosh, bush, env
from ..fomod import FailedCondition, FomodInstaller


class WizardReturn(object):
    __slots__ = ("cancelled", "install_files", "install", "page_size", "pos")

    def __init__(self):
        # cancelled: true if the user canceled or if an error occurred
        self.cancelled = False
        # install_files: file->dest mapping of files to install
        self.install_files = bolt.LowerDict()
        # install: boolean on whether to install the files
        self.install = True
        # page_size: Tuple/wxSize of the saved size of the Wizard
        self.page_size = balt.defSize
        # pos: Tuple/wxPoint of the saved position of the Wizard
        self.pos = balt.defPos


class InstallerFomod(wiz.Wizard):
    def __init__(self, parent_window, installer, page_size, pos):
        # True prevents actually moving to the 'next' page.
        # We use this after the "Next" button is pressed,
        # while the parser is running to return the _actual_ next page
        self.block_change = True
        # 'finishing' is to allow the "Next" button to be used
        # when its name is changed to 'Finish' on the last page of the wizard
        self.finishing = False
        # saving this list allows for faster processing of the files the fomod
        # installer will return.
        self.files_list = [a[0] for a in installer.fileSizeCrcs]

        fomod_file = installer.fomod_file().s
        data_path = bass.dirs["mods"]
        ver = env.get_file_version(bass.dirs["app"].join(
            *bush.game.version_detect_file).s)
        game_ver = u".".join([unicode(i) for i in ver])

        self.parser = FomodInstaller(fomod_file, self.files_list, data_path, game_ver)

        style = wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER | wx.MAXIMIZE_BOX
        wiz.Wizard.__init__(
            self,
            parent_window,
            title=_(u"FOMOD Installer - " + self.parser.fomod_name),
            pos=pos,
            style=style,
        )

        self.is_archive = isinstance(installer, bosh.InstallerArchive)
        if self.is_archive:
            self.archive_path = bass.getTempDir()
        else:
            self.archive_path = bass.dirs["installers"].join(installer.archive)

        # 'dummy' page tricks the wizard into always showing the "Next" button
        self.dummy = wiz.PyWizardPage(self)

        # Intercept the changing event so we can implement 'block_change'
        self.Bind(wiz.EVT_WIZARD_PAGE_CHANGING, self.on_change)
        self.ret = WizardReturn()
        self.ret.page_size = page_size

        # So we can save window size
        self.Bind(wx.EVT_SIZE, self.on_size)
        self.Bind(wx.EVT_CLOSE, self.on_close)
        self.Bind(wiz.EVT_WIZARD_CANCEL, self.on_close)
        self.Bind(wiz.EVT_WIZARD_FINISHED, self.on_close)

        # Set the minimum size for pages, and setup on_size to resize the
        # First page to the saved size
        self.SetPageSize((600, 500))
        self.first_page = True

    def on_close(self, event):
        if not self.IsMaximized():
            # Only save the current size if the page isn't maximized
            self.ret.page_size = self.GetSize()
            self.ret.pos = self.GetPosition()
        event.Skip()

    def on_size(self, event):
        if self.first_page:
            # On the first page, resize it to the saved size
            self.first_page = False
            self.SetSize(self.ret.page_size)
        else:
            # Otherwise, regular resize, save the size if we're not
            # maximized
            if not self.IsMaximized():
                self.ret.page_size = self.GetSize()
                self.pos = self.GetPosition()
            event.Skip()

    def on_change(self, event):
        if event.GetDirection():
            if not self.finishing:
                # Next, continue script execution
                if self.block_change:
                    # Tell the current page that next was pressed,
                    # So the parser can continue parsing,
                    # Then show the page that the parser returns,
                    # rather than the dummy page
                    selection = event.GetPage().on_next()
                    event.Veto()
                    self.block_change = False
                    next_page = self.parser.next_(selection)
                    if next_page is None:
                        self.finishing = True
                        self.ShowPage(PageFinish(self))
                    else:
                        self.finishing = False
                        self.ShowPage(PageSelect(self, next_page))
                else:
                    self.block_change = True
        else:
            # Previous, pop back to the last state,
            # and resume execution
            event.Veto()
            self.block_change = False
            self.finishing = False
            payload = self.parser.previous()
            if payload is None:  # at the start
                return  # do nothing
            page, previous_selection = payload
            gui_page = PageSelect(self, page)
            gui_page.select(previous_selection)
            self.ShowPage(gui_page)

    def run(self):
        try:
            first_page = self.parser.start()
        except FailedCondition as exc:
            msg = "This installer cannot start due to the following unmet conditions:\n"
            for line in str(exc).splitlines():
                msg += "  {}\n".format(line)
            balt.showWarning(self, msg, title="Cannot Run Installer",
                             do_center=True)
            self.ret.cancelled = True
        else:
            if first_page is not None:  # if installer has any gui pages
                self.ret.cancelled = not self.RunWizard(PageSelect(self, first_page))
            self.ret.install_files = bolt.LowerDict(self.parser.files())
        # Clean up temp files
        if self.is_archive:
            bass.rmTempDir()
        return self.ret


# PageInstaller ----------------------------------------------
#  base class for all the parser wizard pages, just to handle
#  a couple simple things here
# ------------------------------------------------------------
class PageInstaller(wiz.PyWizardPage):
    def __init__(self, parent):
        wiz.PyWizardPage.__init__(self, parent)
        self.parent = parent
        self._enableForward(True)

    def _enableForward(self, enable):
        self.parent.FindWindowById(wx.ID_FORWARD).Enable(enable)

    def GetNext(self):
        return self.parent.dummy

    def GetPrev(self):
        return self.parent.dummy

    def on_next(self):
        # This is what needs to be implemented by sub-classes,
        # this is where flow control objects etc should be
        # created
        pass


# PageError --------------------------------------------------
#  Page that shows an error message, has only a "Cancel"
#  button enabled, and cancels any changes made
# -------------------------------------------------------------
class PageError(PageInstaller):
    def __init__(self, parent, title, error_msg):
        PageInstaller.__init__(self, parent)

        # Disable the "Finish"/"Next" button
        self._enableForward(False)

        # Layout stuff
        sizer_main = wx.FlexGridSizer(2, 1, 5, 5)
        text_error = balt.RoTextCtrl(self, error_msg, autotooltip=False)
        sizer_main.Add(balt.StaticText(parent, label=title))
        sizer_main.Add(text_error, 0, wx.ALL | wx.CENTER | wx.EXPAND)
        sizer_main.AddGrowableCol(0)
        sizer_main.AddGrowableRow(1)
        self.SetSizer(sizer_main)
        self.Layout()

    def GetNext(self):
        return None

    def GetPrev(self):
        return None


# PageSelect -------------------------------------------------
#  A Page that shows a message up top, with a selection box on
#  the left (multi- or single- selection), with an optional
#  associated image and description for each option, shown when
#  that item is selected
# ------------------------------------------------------------
class PageSelect(PageInstaller):
    _option_type_string = defaultdict(str)
    _option_type_string["Required"] = "=== This option is required ===\n\n"
    _option_type_string["Recommended"] = \
        "=== This option is recommended ===\n\n"
    _option_type_string["CouldBeUsable"] = \
        "=== This option could result in instability ===\n\n"
    _option_type_string["NotUsable"] = \
        "=== This option cannot be selected ===\n\n"

    def __init__(self, parent, page):
        PageInstaller.__init__(self, parent)

        # group_sizer -> [option_button, ...]
        self.group_option_map = {}

        sizer_main = wx.FlexGridSizer(2, 1, 10, 10)
        label_step_name = balt.StaticText(self, page.name,
                                          style=wx.ALIGN_CENTER)
        label_step_name.SetFont(wx.Font(12, wx.DEFAULT, wx.NORMAL, wx.NORMAL, 0, ""))
        sizer_main.Add(label_step_name, 0, wx.EXPAND)
        sizer_content = wx.GridSizer(1, 2, 5, 5)

        sizer_extra = wx.GridSizer(2, 1, 5, 5)
        self.bmp_item = balt.Picture(self, 0, 0, background=None)
        self._img_cache = {} # creating images can be really expensive
        self.text_item = balt.RoTextCtrl(self, autotooltip=False)
        sizer_extra.Add(self.bmp_item, 1, wx.EXPAND | wx.ALL)
        sizer_extra.Add(self.text_item, 1, wx.EXPAND | wx.ALL)

        panel_groups = wx.ScrolledWindow(self, -1)
        panel_groups.SetScrollbars(20, 20, 50, 50)
        sizer_groups = wx.FlexGridSizer(len(page), 1, 5, 5)
        for row in xrange(len(page)):
            sizer_groups.AddGrowableRow(row)
        for group in page:
            options_num = len(group)

            sizer_group = wx.FlexGridSizer(2, 1, 7, 7)
            sizer_group.AddGrowableRow(1)
            sizer_group.group_object = group
            sizer_group.Add(balt.StaticText(panel_groups, group.name))

            sizer_options = wx.GridSizer(options_num, 1, 2, 2)
            sizer_group.Add(sizer_options)

            first_selectable = None
            any_selected = False

            # whenever there is a required option in a exactlyone/atmostone group
            # all other options need to be disable to ensure the required stays
            # selected
            required_disable = False

            # group type forces selection
            group_type = group.type
            group_force_selection = group_type in (
                "SelectExactlyOne",
                "SelectAtLeastOne",
            )

            for option in group:
                if group_type in ("SelectExactlyOne", "SelectAtMostOne"):
                    radio_style = wx.RB_GROUP if option is group[0] else 0
                    button = wx.RadioButton(
                        panel_groups, label=option.name, style=radio_style
                    )
                else:
                    button = balt.checkBox(panel_groups, label=option.name)
                    if group_type == "SelectAll":
                        button.SetValue(True)
                        any_selected = True
                        button.Disable()

                if option.type == "Required":
                    button.SetValue(True)
                    any_selected = True
                    if group_type in ("SelectExactlyOne", "SelectAtMostOne"):
                        required_disable = True
                    else:
                        button.Disable()
                elif option.type == "Recommended":
                    if not any_selected or not group_force_selection:
                        button.SetValue(True)
                        any_selected = True
                elif option.type in ("Optional", "CouldBeUsable"):
                    if first_selectable is None:
                        first_selectable = button
                elif option.type == "NotUsable":
                    button.SetValue(False)
                    button.Disable()

                button.option_object = option
                sizer_options.Add(button)
                button.Bind(wx.EVT_ENTER_WINDOW, self.on_hover)
                self.group_option_map.setdefault(sizer_group, []).append(button)

            if not any_selected and group_force_selection:
                if first_selectable is not None:
                    first_selectable.SetValue(True)
                    any_selected = True

            if required_disable:
                for button in self.group_option_map[sizer_group]:
                    button.Disable()

            if group_type == "SelectAtMostOne":
                none_button = wx.RadioButton(panel_groups, label="None")
                if not any_selected:
                    none_button.SetValue(True)
                elif required_disable:
                    none_button.Disable()
                sizer_options.Add(none_button)

            sizer_groups.Add(sizer_group, wx.ID_ANY, wx.EXPAND)

        panel_groups.SetSizer(sizer_groups)
        sizer_content.Add(panel_groups, 1, wx.EXPAND)
        sizer_content.Add(sizer_extra, 1, wx.EXPAND)
        sizer_main.Add(sizer_content, 1, wx.EXPAND)
        sizer_main.AddGrowableRow(1)
        sizer_main.AddGrowableCol(0)

        self.SetSizer(sizer_main)
        self.Layout()

    # fixme XXX: hover doesn't work on disabled buttons
    # fixme XXX: types other than optional should be shown in some visual way (button colour?)
    def on_hover(self, event):
        button = event.GetEventObject()
        option = button.option_object
        self._enableForward(True)

        self.bmp_item.Freeze()
        img = self.parent.archive_path.join(option.image)
        try:
            image = self._img_cache[img]
        except KeyError:
            image = self._img_cache.setdefault(img, (
                    img.isfile() and balt.Image(img.s).GetBitmap()) or None)
        self.bmp_item.SetBitmap(image)
        self.bmp_item.Thaw()
        self.text_item.SetValue(
            self._option_type_string[option.type] + option.description)

    def on_error(self, msg):
        msg += (
            "\nPlease ensure the fomod files are correct and "
            "contact the Wrye Bash Dev Team."
        )
        balt.showWarning(self, msg, title="Warning", do_center=True)

    def on_next(self):
        selection = []
        for group_sizer, option_buttons in self.group_option_map.iteritems():
            group = group_sizer.group_object
            group_selected = [a.option_object for a in option_buttons if a.GetValue()]
            option_len = len(group_selected)
            if group.type == "SelectExactlyOne" and option_len != 1:
                msg = (
                    'Group "{}" should have exactly 1 option selected '
                    "but has {}.".format(group.name, option_len)
                )
                self.on_error(msg)
            elif group.type == "SelectAtMostOne" and option_len > 1:
                msg = (
                    'Group "{}" should have at most 1 option selected '
                    "but has {}.".format(group.name, option_len)
                )
                self.on_error(msg)
            elif group.type == "SelectAtLeast" and option_len < 1:
                msg = (
                    'Group "{}" should have at least 1 option selected '
                    "but has {}.".format(group.name, option_len)
                )
                self.on_error(msg)
            elif group.type == "SelectAll" and option_len != len(option_buttons):
                msg = (
                    'Group "{}" should have all options selected '
                    "but has only {}.".format(group.name, option_len)
                )
                self.on_error(msg)
            selection.extend(group_selected)
        return selection

    def select(self, selection):
        for button_list in self.group_option_map.itervalues():
            for button in button_list:
                if button.option_object in selection:
                    button.SetValue(True)


class PageFinish(PageInstaller):
    def __init__(self, parent):
        PageInstaller.__init__(self, parent)

        sizer_main = wx.FlexGridSizer(3, 1, 10, 10)
        label_title = wx.StaticText(
            self, wx.ID_ANY, "Files To Install", style=wx.ALIGN_CENTER
        )
        label_title.SetFont(wx.Font(12, wx.DEFAULT, wx.NORMAL, wx.NORMAL, 0, ""))
        sizer_main.Add(label_title, 0, wx.EXPAND)
        text_item = balt.RoTextCtrl(self, autotooltip=False, hscroll=True)
        text_item.SetFont(wx.Font(9, wx.MODERN, wx.NORMAL, wx.NORMAL, 0, ""))
        files_dict = self.parent.parser.files()
        if files_dict:
            text_item.SetValue(self.display_files(files_dict))
        sizer_main.Add(text_item, 1, wx.EXPAND | wx.ALL)
        self.check_install = balt.checkBox(
            self,
            "Install this package",
            onCheck=self.on_check,
            checked=self.parent.ret.install,
        )
        sizer_main.Add(self.check_install, 1, wx.EXPAND | wx.ALL)

        sizer_main.AddGrowableRow(1)
        sizer_main.AddGrowableCol(0)

        self.SetSizer(sizer_main)
        self.Layout()

    def on_check(self):
        self.parent.ret.install = self.check_install.IsChecked()

    def GetNext(self):
        return None

    @staticmethod
    def display_files(file_dict):
        center_char = " -> "
        max_key_len = len(max(file_dict.keys(), key=len))
        max_value_len = len(max(file_dict.values(), key=len))
        lines = []
        for key, value in file_dict.iteritems():
            lines.append(
                "{0:<{1}}{2}{3:<{4}}".format(
                    value, max_value_len, center_char, key, max_key_len
                )
            )
        lines.sort(key=str.lower)
        final_text = "\n".join(lines)
        return final_text
