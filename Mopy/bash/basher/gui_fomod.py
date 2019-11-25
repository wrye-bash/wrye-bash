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

from collections import defaultdict
import wx
import wx.wizard as wiz

from .. import balt, bass, bolt, bosh, bush, env
from ..balt import Events, set_event_hook
from ..gui import CENTER, CheckBox, HBoxedLayout, HLayout, Label, \
    LayoutOptions, TextArea, VLayout
from ..fomod import FailedCondition, FomodInstaller

__author__ = "Ganda"

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
        self.parser = FomodInstaller(fomod_file, self.files_list, data_path,
                                     u'.'.join([unicode(i) for i in ver]))
        wiz.Wizard.__init__(
            self, parent_window,
            title=_(u'FOMOD Installer - %s') % self.parser.fomod_name, pos=pos,
            style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER | wx.MAXIMIZE_BOX)
        self.is_archive = isinstance(installer, bosh.InstallerArchive)
        if self.is_archive:
            self.archive_path = bass.getTempDir()
        else:
            self.archive_path = bass.dirs["installers"].join(installer.archive)
        # 'dummy' page tricks the wizard into always showing the "Next" button
        self.dummy = wiz.PyWizardPage(self)
        # Intercept the changing event so we can implement 'block_change'
        set_event_hook(self, Events.WIZARD_PAGE_CHANGING, self.on_change)
        self.ret = WizardReturn()
        self.ret.page_size = page_size
        # So we can save window size
        set_event_hook(self, Events.RESIZE, self.on_size)
        set_event_hook(self, Events.CLOSE, self.on_close)
        set_event_hook(self, Events.WIZARD_CANCEL, self.on_close)
        set_event_hook(self, Events.WIZARD_FINISHED, self.on_close)
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
                self.ret.pos = self.GetPosition()
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
            msg = _(u'This installer cannot start due to the following unmet '
                    u'conditions:\n')
            for line in str(exc).splitlines():
                msg += u'  {}\n'.format(line)
            balt.showWarning(self, msg, title=_(u'Cannot Run Installer'),
                             do_center=True)
            self.ret.cancelled = True
        else:
            if first_page is not None:  # if installer has any gui pages
                self.ret.cancelled = not self.RunWizard(
                    PageSelect(self, first_page))
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
        super(PageInstaller, self).__init__(parent)
        self.parent = parent
        self._enableForward(True)

    def _enableForward(self, enable):
        self.parent.FindWindowById(wx.ID_FORWARD).Enable(enable)

    def GetNext(self):
        return self.parent.dummy

    def GetPrev(self):
        if self.parent.parser.has_previous():
            return self.parent.dummy
        return None

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
        super(PageError, self).__init__(parent)
        # Disable the "Finish"/"Next" button
        self._enableForward(False)
        VLayout(spacing=5, items=[
            Label(parent, title),
            (TextArea(self, init_text=error_msg, editable=False,
                      auto_tooltip=False), LayoutOptions(fill=True, weight=1)),
        ]).apply_to(self)
        # TODO(inf) Are all these Layout() calls needed? belt does them, so I
        #  assume that's why they're here, but belt isn't a good GUI example :P
        #  If yes, then: de-wx!
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
    _option_type_string["Required"] = _(u'=== This option is required ===\n\n')
    _option_type_string["Recommended"] = _(u'=== This option is recommended '
                                           u'===\n\n')
    _option_type_string["CouldBeUsable"] = _(u'=== This option could result '
                                             u'in instability ===\n\n')
    _option_type_string["NotUsable"] = _(u'=== This option cannot be selected '
                                         u'===\n\n')

    def __init__(self, parent, page):
        super(PageSelect, self).__init__(parent)
        self.group_option_map = defaultdict(list)
        self.bmp_item = balt.Picture(self, 0, 0, background=None)
        self._img_cache = {} # creating images can be really expensive
        self.text_item = TextArea(self, editable=False, auto_tooltip=False)
        # TODO(inf) de-wx!
        panel_groups = wx.ScrolledWindow(self)
        panel_groups.SetScrollbars(20, 20, 50, 50)
        groups_layout = VLayout(spacing=5, default_fill=True)
        for group in page:
            options_layout = VLayout(spacing=2)
            first_selectable = None
            any_selected = False
            # whenever there is a required option in a exactlyone/atmostone
            # group all other options need to be disabled to ensure the
            # required stays selected
            required_disable = False
            # group type forces selection
            group_type = group.type
            group_force_selection = group_type in ("SelectExactlyOne",
                                                   "SelectAtLeastOne")
            for option in group:
                if group_type in ("SelectExactlyOne", "SelectAtMostOne"):
                    # TODO(inf) de-wx!
                    button = wx.RadioButton(
                        panel_groups, label=option.name,
                        style=wx.RB_GROUP if option is group[0] else 0)
                else:
                    button = CheckBox(panel_groups, label=option.name)
                    if group_type == "SelectAll":
                        button.is_checked = True
                        any_selected = True
                        button.enabled = False
                if option.type == "Required":
                    SetComponentValue_(button, True)
                    any_selected = True
                    if group_type in ("SelectExactlyOne", "SelectAtMostOne"):
                        required_disable = True
                    else:
                        EnableComponent_(button, False)
                elif option.type == "Recommended":
                    if not any_selected or not group_force_selection:
                        SetComponentValue_(button, True)
                        any_selected = True
                elif option.type in ("Optional", "CouldBeUsable"):
                    if first_selectable is None:
                        first_selectable = button
                elif option.type == "NotUsable":
                    SetComponentValue_(button, False)
                    EnableComponent_(button, False)
                # TODO(inf) This is very hacky, there has to a better way than
                #  abusing __dict__ for this
                LinkOptionObject_(button, option)
                options_layout.add(button)
                BindCallback_(button, Events.HOVER, self.on_hover)
                self.group_option_map[group].append(button)
            if not any_selected and group_force_selection:
                if first_selectable is not None:
                    SetComponentValue_(first_selectable, True)
                    any_selected = True
            if required_disable:
                for button in self.group_option_map[group]:
                    EnableComponent_(button, False)
            if group_type == "SelectAtMostOne":
                none_button = wx.RadioButton(panel_groups, label=_(u'None'))
                if not any_selected:
                    none_button.SetValue(True)
                elif required_disable:
                    none_button.Disable()
                options_layout.add(none_button)
            groups_layout.add(HBoxedLayout(
                panel_groups, title=group.name, default_fill=True,
                default_weight=1, items=[options_layout]))
        groups_layout.apply_to(panel_groups)
        VLayout(spacing=10, default_fill=True, items=[
            (HLayout(spacing=5, default_fill=True, default_weight=1, items=[
                HBoxedLayout(self, title=page.name, default_fill=True,
                             default_weight=1, items=[panel_groups]),
                VLayout(spacing=5, default_fill=True, default_weight=1, items=[
                    self.bmp_item, self.text_item
                ]),
            ]), LayoutOptions(weight=1)),
        ]).apply_to(self)
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
        self.text_item.text_content = (self._option_type_string[option.type]
                                       + option.description)

    def on_error(self, msg):
        msg += _(u'\nPlease ensure the FOMOD files are correct and contact '
                 u'the Wrye Bash Dev Team.')
        balt.showWarning(self, msg, do_center=True)

    def on_next(self):
        selection = []
        for group, option_buttons in self.group_option_map.iteritems():
            group_selected = [a.option_object for a in option_buttons
                              if GetComponentValue_(a)]
            option_len = len(group_selected)
            if group.type == "SelectExactlyOne" and option_len != 1:
                msg = _(u'Group "{}" should have exactly 1 option selected '
                        u'but has {}.').format(group.name, option_len)
                self.on_error(msg)
            elif group.type == "SelectAtMostOne" and option_len > 1:
                msg = _(u'Group "{}" should have at most 1 option selected '
                        u'but has {}.').format(group.name, option_len)
                self.on_error(msg)
            elif group.type == "SelectAtLeast" and option_len < 1:
                msg = _(u'Group "{}" should have at least 1 option selected '
                        u'but has {}.').format(group.name, option_len)
                self.on_error(msg)
            elif (group.type == "SelectAll"
                  and option_len != len(option_buttons)):
                msg = _(u'Group "{}" should have all options selected but has '
                        u'only {}.').format(group.name, option_len)
                self.on_error(msg)
            selection.extend(group_selected)
        return selection

    def select(self, selection):
        for button_list in self.group_option_map.itervalues():
            for button in button_list:
                if button.option_object in selection:
                    SetComponentValue_(button, True)

class PageFinish(PageInstaller):
    def __init__(self, parent):
        super(PageFinish, self).__init__(parent)
        # TODO(inf) de-wx! Font API? If we do this, revert the display_files
        #  change below
        #label_title.SetFont(wx.Font(12, wx.DEFAULT, wx.NORMAL, wx.NORMAL, 0, ""))
        #text_item.SetFont(wx.Font(9, wx.MODERN, wx.NORMAL, wx.NORMAL, 0, ""))
        check_install = CheckBox(self, _(u'Install this package'),
                                 checked=self.parent.ret.install)
        check_install.on_checked.subscribe(self.on_check)
        installer_output = self.display_files(self.parent.parser.files())
        VLayout(spacing=10, default_fill=True, items=[
            (Label(self, _(u'Files To Install')),
             LayoutOptions(fill=False, h_align=CENTER)),
            (TextArea(self, editable=False, auto_tooltip=False,
                      init_text=installer_output), LayoutOptions(weight=1)),
            check_install,
        ]).apply_to(self)
        self.Layout()

    def on_check(self, is_checked):
        self.parent.ret.install = is_checked

    def GetNext(self):
        return None

    @staticmethod
    def display_files(file_dict):
        if not file_dict: return u''
        lines = [u'{} -> {}'.format(v, k) for k, v in file_dict.iteritems()]
        lines.sort(key=unicode.lower)
        return u'\n'.join(lines)

# FIXME(inf) Hacks until wx.RadioButton is wrapped, ugly names are on purpose
def EnableComponent_(component, is_enabled):
    if isinstance(component, wx.RadioButton):
        component.Enable(is_enabled)
    else:
        component.enabled = is_enabled

def SetComponentValue_(component, target_value):
    if isinstance(component, wx.RadioButton):
        component.SetValue(target_value)
    else:
        component.is_checked = target_value

def GetComponentValue_(component):
    if isinstance(component, wx.RadioButton):
        return component.GetValue()
    else:
        return component.is_checked

def BindCallback_(component, balt_event, target_callback):
    target = (component if isinstance(component, wx.RadioButton)
              else component._native_widget)
    set_event_hook(target, balt_event, target_callback)

def LinkOptionObject_(component, target_option):
    component.option_object = target_option
    if not isinstance(component, wx.RadioButton):
        component._native_widget.option_object = target_option
