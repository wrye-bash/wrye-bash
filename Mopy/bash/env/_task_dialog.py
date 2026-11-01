# -*- coding: utf-8 -*-
#
#       taskdialog.py
#
#       Copyright © 2009 Te-jé Rodgers <contact@tejerodgers.com>
#
#       This file is part of Curtains
#
#       Curtains is free software; you can redistribute it and/or modify
#       it under the terms of the GNU Lesser General Public License as
#       published by the Free Software Foundation; either version 3 of the
#       License, or (at your option) any later version.
#
#       This program is distributed in the hope that it will be useful,
#       but WITHOUT ANY WARRANTY; without even the implied warranty of
#       MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#       GNU Lesser General Public License for more details.
#
#       You should have received a copy of the GNU Lesser General Public
#       License along with this program; if not, write to the Free Software
#       Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston,
#       MA 02110-1301, USA.
#
# Edits have been made to it to fit Wrye Bash's code style and to port it to
# 64bit/python3.
"""Wrapper for the Win32 task dialog (TaskDialogIndirect), vendored from
Curtains' taskdialog.py. Windows only - imported by env/windows.py, which
exports TaskDialog as part of the env API. Raises an AttributeError on import
if TaskDialogIndirect is not available (before Vista)."""

from ctypes import POINTER, WINFUNCTYPE, Structure, Union, byref, c_int, \
    c_long, c_longlong, c_uint, c_ulong, c_ushort, c_void_p, c_wchar, \
    c_wchar_p, sizeof, windll, wstring_at
from ctypes.wintypes import MAX_PATH as _MAX_PATH

_indirect = windll.comctl32.TaskDialogIndirect
_indirect.restype = c_void_p

_BUTTONID_OFFSET                 = 1000

#---Internal Flags. Leave these alone unless you know what you're doing---#
_ENABLE_HYPERLINKS               = 0x0001
_USE_HICON_MAIN                  = 0x0002
_USE_HICON_FOOTER                = 0x0004
_ALLOW_DIALOG_CANCELLATION       = 0x0008
_USE_COMMAND_LINKS               = 0x0010
_USE_COMMAND_LINKS_NO_ICON       = 0x0020
_EXPAND_FOOTER_AREA              = 0x0040
_EXPANDED_BY_DEFAULT             = 0x0080
_VERIFICATION_FLAG_CHECKED       = 0x0100
_SHOW_PROGRESS_BAR               = 0x0200
_SHOW_MARQUEE_PROGRESS_BAR       = 0x0400
_CALLBACK_TIMER                  = 0x0800
_POSITION_RELATIVE_TO_WINDOW     = 0x1000
_RTL_LAYOUT                      = 0x2000
_NO_DEFAULT_RADIO_BUTTON         = 0x4000
_CAN_BE_MINIMIZED                = 0x8000

#-------------Events---------------#
_CREATED                         = 0
_NAVIGATED                       = 1
_BUTTON_CLICKED                  = 2
_HYPERLINK_CLICKED               = 3
_TIMER                           = 4
_DESTROYED                       = 5
_RADIO_BUTTON_CLICKED            = 6
_DIALOG_CONSTRUCTED              = 7
_VERIFICATION_CLICKED            = 8
_HELP                            = 9
_EXPANDER_BUTTON_CLICKED         = 10

#-------Callback Type--------#
_PFTASKDIALOGCALLBACK = WINFUNCTYPE(c_void_p, c_void_p, c_uint, c_uint, c_long,
                                    c_long)

#-------Win32 Stucts/Unions--------#
# Callers do not have to worry about using these.
class _TASKDIALOG_BUTTON(Structure):
    _pack_ = 1
    _fields_ = [(u'nButtonID', c_int),
                (u'pszButtonText', c_wchar_p)]

class _FOOTERICON(Union):
    _pack_ = 1
    _fields_ = [(u'hFooterIcon', c_void_p),
                (u'pszFooterIcon', c_ushort)]

class _MAINICON(Union):
    _pack_ = 1
    _fields_ = [(u'hMainIcon', c_void_p),
                (u'pszMainIcon', c_ushort)]

class _TASKDIALOGCONFIG(Structure):
    _pack_ = 1
    _fields_ = [(u'cbSize', c_uint),
                (u'hwndParent', c_void_p),
                (u'hInstance', c_void_p),
                (u'dwFlags', c_uint),
                (u'dwCommonButtons', c_uint),
                (u'pszWindowTitle', c_wchar_p),
                (u'uMainIcon', _MAINICON),
                (u'pszMainInstruction', c_wchar_p),
                (u'pszContent', c_wchar_p),
                (u'cButtons', c_uint),
                (u'pButtons', POINTER(_TASKDIALOG_BUTTON)),
                (u'nDefaultButton', c_int),
                (u'cRadioButtons', c_uint),
                (u'pRadioButtons', POINTER(_TASKDIALOG_BUTTON)),
                (u'nDefaultRadioButton', c_int),
                (u'pszVerificationText', c_wchar_p),
                (u'pszExpandedInformation', c_wchar_p),
                (u'pszExpandedControlText', c_wchar_p),
                (u'pszCollapsedControlText', c_wchar_p),
                (u'uFooterIcon', _FOOTERICON),
                (u'pszFooter', c_wchar_p),
                (u'pfCallback', _PFTASKDIALOGCALLBACK),
                (u'lpCallbackData', c_longlong),
                (u'cxWidth', c_uint)]

    _anonymous_ = (u'uMainIcon', u'uFooterIcon',)

#--Stock ICON IDs
_SIID_DOCNOASSOC         = 0
_SIID_DOCASSOC           = 1
_SIID_APPLICATION        = 2
_SIID_FOLDER             = 3
_SIID_FOLDEROPEN         = 4
_SIID_DRIVE525           = 5
_SIID_DRIVE35            = 6
_SIID_DRIVEREMOVE        = 7
_SIID_DRIVEFIXED         = 8
_SIID_DRIVENET           = 9
_SIID_DRIVENETDISABLED   = 10
_SIID_DRIVECD            = 11
_SIID_DRIVERAM           = 12
_SIID_WORLD              = 13
_SIID_SERVER             = 15
_SIID_PRINTER            = 16
_SIID_MYNETWORK          = 17
_SIID_FIND               = 22
_SIID_HELP               = 23
_SIID_SHARE              = 28
_SIID_LINK               = 29
_SIID_SLOWFILE           = 30
_SIID_RECYCLER           = 31
_SIID_RECYCLERFULL       = 32
_SIID_MEDIACDAUDIO       = 40
_SIID_LOCK               = 47
_SIID_AUTOLIST           = 49
_SIID_PRINTERNET         = 50
_SIID_SERVERSHARE        = 51
_SIID_PRINTERFAX         = 52
_SIID_PRINTERFAXNET      = 53
_SIID_PRINTERFILE        = 54
_SIID_STACK              = 55
_SIID_MEDIASVCD          = 56
_SIID_STUFFEDFOLDER      = 57
_SIID_DRIVEUNKNOWN       = 58
_SIID_DRIVEDVD           = 59
_SIID_MEDIADVD           = 60
_SIID_MEDIADVDRAM        = 61
_SIID_MEDIADVDRW         = 62
_SIID_MEDIADVDR          = 63
_SIID_MEDIADVDROM        = 64
_SIID_MEDIACDAUDIOPLUS   = 65
_SIID_MEDIACDRW          = 66
_SIID_MEDIACDR           = 67
_SIID_MEDIACDBURN        = 68
_SIID_MEDIABLANKCD       = 69
_SIID_MEDIACDROM         = 70
_SIID_AUDIOFILES         = 71
_SIID_IMAGEFILES         = 72
_SIID_VIDEOFILES         = 73
_SIID_MIXEDFILES         = 74
_SIID_FOLDERBACK         = 75
_SIID_FOLDERFRONT        = 76
_SIID_SHIELD             = 77
_SIID_WARNING            = 78
_SIID_INFO               = 79
_SIID_ERROR              = 80
_SIID_KEY                = 81
_SIID_SOFTWARE           = 82
_SIID_RENAME             = 83
_SIID_DELETE             = 84
_SIID_MEDIAAUDIODVD      = 85
_SIID_MEDIAMOVIEDVD      = 86
_SIID_MEDIAENHANCEDCD    = 87
_SIID_MEDIAENHANCEDDVD   = 88
_SIID_MEDIAHDDVD         = 89
_SIID_MEDIABLURAY        = 90
_SIID_MEDIAVCD           = 91
_SIID_MEDIADVDPLUSR      = 92
_SIID_MEDIADVDPLUSRW     = 93
_SIID_DESKTOPPC          = 94
_SIID_MOBILEPC           = 95
_SIID_USERS              = 96
_SIID_MEDIASMARTMEDIA    = 97
_SIID_MEDIACOMPACTFLASH  = 98
_SIID_DEVICECELLPHONE    = 99
_SIID_DEVICECAMERA       = 100
_SIID_DEVICEVIDEOCAMERA  = 101
_SIID_DEVICEAUDIOPLAYER  = 102
_SIID_NETWORKCONNECT     = 103
_SIID_INTERNET           = 104
_SIID_ZIPFILE            = 105
_SIID_SETTINGS           = 106
_SIID_DRIVEHDDVD         = 132
_SIID_DRIVEBD            = 133
_SIID_MEDIAHDDVDROM      = 134
_SIID_MEDIAHDDVDR        = 135
_SIID_MEDIAHDDVDRAM      = 136
_SIID_MEDIABDROM         = 137
_SIID_MEDIABDR           = 138
_SIID_MEDIABDRE          = 139
_SIID_CLUSTEREDDRIVE     = 140
_SIID_MAX_ICONS          = 175

#--SHGetIconInfo flags
_SHGSI_ICONLOCATION  = 0x00000000 # you always get icon location
_SHGSI_ICON          = 0x00000100 # get handle to the icon
_SHGSI_LARGEICON     = 0x00000000 # get large icon
_SHGSI_SMALLICON     = 0x00000001 # get small icon
_SHGSI_SHELLICONSIZE = 0x00000004 # get shell icon size
_SHGSI_SYSICONINDEX  = 0x00004000 # get system icon index
_SHGSI_LINKOVERLAY   = 0x00008000 # get icon with a link overlay on it
_SHGSI_SELECTED      = 0x00010000 # get icon in selected state

class _SHSTOCKICONINFO(Structure):
    _pack_ = 1
    _fields_ = [(u'cbSize', c_ulong),
                (u'hIcon', c_void_p),
                (u'iSysImageIndex', c_int),
                (u'iIcon', c_int),
                (u'szPath', c_wchar * _MAX_PATH)]

#------------------------------------------------------------------------------

#------Message codes------#
_SETISMARQUEE = 1127
_SETPBARRANGE = 1129
_SETPBARPOS = 1130
_SETMARQUEE = 1131
_SETELEMENT = 1132
_SETSHIELD = 1139
_UPDATEICON = 1140

_CONTENT = 0
_EX_INFO = 1
_FOOTER = 2
_HEADING = 3

class TaskDialog(object):
    """Wrapper class for the Win32 task dialog."""

    stock_icons = {u'warning': 65535, u'error': 65534, u'information': 65533,
                   u'shield': 65532}
    stock_buttons = {u'ok': 0x01,  #1
                     u'yes': 0x02,  #2
                     u'no': 0x04,  #4
                     u'cancel': 0x08,  #8
                     u'retry': 0x10,  #16
                     u'close': 0x20}  #32
    stock_button_ids = {u'ok': 1, u'cancel': 2, u'retry': 4, u'yes': 6,
                        u'no': 7, u'close': 8}

    def __init__(self, title, heading, content, tsk_buttons=(), main_icon=None,
                 parenthwnd=None, footer=None):
        """Initialize the dialog."""
        self.__events = {_CREATED:[],
                         _NAVIGATED:[],
                         _BUTTON_CLICKED:[],
                         _HYPERLINK_CLICKED:[],
                         _TIMER:[],
                         _DESTROYED:[],
                         _RADIO_BUTTON_CLICKED:[],
                         _DIALOG_CONSTRUCTED:[],
                         _VERIFICATION_CLICKED:[],
                         _HELP:[],
                         _EXPANDER_BUTTON_CLICKED:[]}
        self.__stockb_indices = []
        self.__shield_buttons = []
        self.__handle = None
        # properties
        self._title = title
        self._heading = heading
        self._content = content
        self._footer = footer
        # main icon
        self._main_is_stock = main_icon in self.stock_icons
        self._main_icon = self.stock_icons[
            main_icon] if self._main_is_stock else main_icon
        # buttons
        tsk_buttons = list(tsk_buttons)
        self.set_buttons(tsk_buttons)
        # parent handle
        self._parent = parenthwnd

    def close(self):
        """Close the task dialog."""
        windll.user32.SendMessageW(self.__handle, 0x0010, 0, 0)

    def bind(self, task_dialog_event, func):
        """Bind a function to one of the task dialog events."""
        if task_dialog_event not in self.__events:
            raise Exception(u'The control does not support the event.')
        self.__events[task_dialog_event].append(func)
        return self

    @property
    def heading(self): return self._heading
    @heading.setter
    def heading(self, heading):
        """Set the heading / main instruction of the dialog."""
        self._heading = heading
        if self.__handle is not None:
            self.__update_element_text(_HEADING, heading)

    @property
    def content(self): return self._content
    @content.setter
    def content(self, content):
        """Set the text content or message that the dialog conveys."""
        self._content = content
        if self.__handle is not None:
            self.__update_element_text(_CONTENT, content)

    @property
    def footer(self): return self._footer
    @footer.setter
    def footer(self, footer):
        """Set the footer text of the dialog."""
        self._footer = footer
        if self.__handle is not None:
            self.__update_element_text(_FOOTER, footer)

    def set_buttons(self, tsk_buttons, convert_stock_buttons=True):
        """

           Set the buttons on the dialog using the list of strings in *buttons*
           where each string is the label for a new button.

           See the official documentation.

        """
        self._buttons = tsk_buttons
        self._conv_stock = convert_stock_buttons
        return self

    def set_radio_buttons(self, radio_buttons, default=0):
        """

           Add radio buttons to the dialog using the list of strings in
           *buttons*.

        """
        self._radio_buttons = radio_buttons
        self._default_radio = default
        return self

    def set_footer_icon(self, footer_icon: str):
        """Set the icon that appears in the footer of the dialog."""
        self._footer_is_stock = footer_icon in self.stock_icons
        self._footer_icon = self.stock_icons[
            footer_icon] if self._footer_is_stock else footer_icon
        return self

    def set_expander(self, expander_data, expanded=False, at_footer=False):
        """Set up a collapsible control that can reveal further information
        about the task that the dialog performs."""
        if len(expander_data) != 3: return self
        self._expander_data = expander_data
        self._expander_expanded = expanded
        self._expands_at_footer = at_footer
        return self

    def set_rangeless_progress_bar(self, ticks=50):
        """Set the progress bar on the task dialog as a marquee progress
        bar."""
        self._marquee_progress_bar = True
        self._marquee_speed = ticks
        return self

    def set_progress_bar(self, callback, low=0, high=100, pos=0):
        """Set the progress bar on the task dialog as a marquee progress
        bar."""
        _range = (high << 16) | low
        self._progress_bar = {u'func':callback, u'range': _range, u'pos':pos}
        return self

    def set_check_box(self, cbox_label, checked=False):
        """Set up a verification check box that appears on the task dialog."""
        self._cbox_label = cbox_label
        self._cbox_checked = checked
        return self

    def set_width(self, width):
        """Set the width, in pixels, of the taskdialog."""
        self._width = width
        return self

    def show(self, command_links=False, centered=True, can_cancel=False,
             can_minimize=False, hyperlinks=True, additional_flags=0):
        """Build and display the dialog box."""
        conf = self.__configure(command_links, centered, can_cancel,
                                can_minimize, hyperlinks, additional_flags)
        button = c_int()
        radio = c_int()
        checkbox = c_int()
        _indirect(byref(conf), byref(button), byref(radio), byref(checkbox))
        if button.value >= _BUTTONID_OFFSET:
            button = self.__custom_buttons[button.value - _BUTTONID_OFFSET][0]
        else:
            for stock_btn, stock_val in self.stock_button_ids.items():
                if stock_val == button.value:
                    button = stock_btn
                    break
            else:
                button = 0
        if getattr(self, u'_radio_buttons', False):
            radio = self._radio_buttons[radio.value]
        else:
            radio = radio.value
        checkbox = not (checkbox.value == 0)
        return button, radio, checkbox

    ###############################
    # Windows windll.user32 calls #
    ###############################
    def __configure(self, c_links, centered, close, minimize, h_links,
                    additional_flags):
        conf = _TASKDIALOGCONFIG()

        if c_links and getattr(self, '_buttons', []):
            additional_flags |= _USE_COMMAND_LINKS
        if centered:
            additional_flags |= _POSITION_RELATIVE_TO_WINDOW
        if close:
            additional_flags |= _ALLOW_DIALOG_CANCELLATION
        if minimize:
            additional_flags |= _CAN_BE_MINIMIZED
        if h_links:
            additional_flags |= _ENABLE_HYPERLINKS

        conf.cbSize = sizeof(_TASKDIALOGCONFIG)
        conf.hwndParent = self._parent
        conf.pszWindowTitle = self._title
        conf.pszMainInstruction = self._heading
        conf.pszContent = self._content

        # FIXME(ut): unpythonic, as the builder pattern above
        attributes = dir(self)

        if '_width' in attributes:
            conf.cxWidth = self._width

        if self._footer:
            conf.pszFooter = self._footer
        if '_footer_icon' in attributes:
            if self._footer_is_stock:
                conf.uFooterIcon.pszFooterIcon = self._footer_icon
            else:
                conf.uFooterIcon.hFooterIcon = self._footer_icon
                additional_flags |= _USE_HICON_FOOTER
        if self._main_icon is not None:
            if self._main_is_stock:
                conf.uMainIcon.pszMainIcon = self._main_icon
            else:
                conf.uMainIcon.hMainIcon = self._main_icon
                additional_flags |= _USE_HICON_MAIN

        if '_buttons' in attributes:
            custom_buttons = []
            # Enumerate through button list
            for i, button in enumerate(self._buttons):
                text, elevated, default = self.__parse_button(button)
                if text.lower() in self.stock_buttons and self._conv_stock:
                    # This is a stock button.
                    conf.dwCommonButtons = (conf.dwCommonButtons
                                            |self.stock_buttons[text.lower()])

                    bID = self.stock_button_ids[text.lower()]
                    if elevated:
                        self.__shield_buttons.append(bID)
                    if default:
                        conf.nDefaultButton = bID
                else:
                    custom_buttons.append((text, default, elevated))

            conf.cButtons = len(custom_buttons)
            array_type = _TASKDIALOG_BUTTON * conf.cButtons
            c_array = array_type()
            for i, tup in enumerate(custom_buttons):
                c_array[i] = _TASKDIALOG_BUTTON(i + _BUTTONID_OFFSET, tup[0])
                if tup[1]:
                    conf.nDefaultButton = i + _BUTTONID_OFFSET
                if tup[2]:
                    self.__shield_buttons.append(i + _BUTTONID_OFFSET)
            conf.pButtons = c_array
            self.__custom_buttons = custom_buttons

        if '_radio_buttons' in attributes:
            conf.cRadioButtons = len(self._radio_buttons)
            array_type = _TASKDIALOG_BUTTON * conf.cRadioButtons
            c_array = array_type()
            for i, button in enumerate(self._radio_buttons):
                c_array[i] = _TASKDIALOG_BUTTON(i, button)
            conf.pRadioButtons = c_array

            if self._default_radio is None:
                additional_flags |= _NO_DEFAULT_RADIO_BUTTON
            else:
                conf.nDefaultRadioButton = self._default_radio

        if '_expander_data' in attributes:
            conf.pszCollapsedControlText = self._expander_data[0]
            conf.pszExpandedControlText = self._expander_data[1]
            conf.pszExpandedInformation = self._expander_data[2]

            if self._expander_expanded:
                additional_flags |= _EXPANDED_BY_DEFAULT
            if self._expands_at_footer:
                additional_flags |= _EXPAND_FOOTER_AREA

        if '_cbox_label' in attributes:
            conf.pszVerificationText = self._cbox_label
            if self._cbox_checked:
                additional_flags |= _VERIFICATION_FLAG_CHECKED

        if '_marquee_progress_bar' in attributes:
            additional_flags |= _SHOW_MARQUEE_PROGRESS_BAR
            additional_flags |= _CALLBACK_TIMER

        if '_progress_bar' in attributes:
            additional_flags |= _SHOW_PROGRESS_BAR
            additional_flags |= _CALLBACK_TIMER

        conf.dwFlags = additional_flags
        conf.pfCallback = _PFTASKDIALOGCALLBACK(self.__callback)
        return conf

    @staticmethod
    def __parse_button(text):
        elevation = False
        default = False
        if text.startswith(u'+') and len(text) > 1:
            text = text[1:]
            elevation = True
        elif text.startswith(r'\+'):
            text = text[1:]
        if text.startswith(u'+\\') and text.isupper():
            text = text[0] + text[2:]
        elif text.startswith(u'\\') and text.isupper():
            text = text[1:]
        elif text.isupper():
            default = True
            splits = text.partition(u'&')
            if splits[0] == u'':
                text = splits[1] + splits[2].capitalize()
            else:
                text = splits[0].capitalize() + splits[1] + splits[2]
        return text, elevation, default

    def __callback(self, handle, notification, wparam, lparam, refdata):
        args = [self]
        if notification == _CREATED:
            self.__handle = handle
            for bID in self.__shield_buttons:
                windll.user32.SendMessageW(self.__handle, _SETSHIELD, bID, 1)
            if getattr(self, u'_marquee_progress_bar', False):
                self.__set_marquee_speed()
        elif notification == _BUTTON_CLICKED:
            if wparam >= _BUTTONID_OFFSET:
                button = self.__custom_buttons[wparam - _BUTTONID_OFFSET][0]
                args.append(button)
            else:
                for stock_btn, stock_val in self.stock_button_ids.items():
                    if stock_val == wparam:
                        button = stock_btn
                        break
                else:
                    button = 0
                args.append(button)
        elif notification == _HYPERLINK_CLICKED:
            args.append(wstring_at(lparam))
        elif notification == _RADIO_BUTTON_CLICKED:
            if getattr(self, u'_radio_buttons', False):
                radio = self._radio_buttons[wparam]
            else:
                radio = wparam
            args.append(radio)
        elif notification == _VERIFICATION_CLICKED:
            args.append(wparam)
        elif notification == _EXPANDER_BUTTON_CLICKED:
            if wparam == 0:
                collapsed = True
            else:
                collapsed = False
            args.append(collapsed)
        elif notification == _DESTROYED:
            self.__handle = None
        elif notification == _TIMER:
            args.append(wparam)
            if getattr(self, u'_progress_bar', False):
                callback = self._progress_bar[u'func']
                new_pos = callback(self)
                self._progress_bar[u'pos'] = new_pos
                self.__update_progress_bar()
        for func in self.__events[notification]:
            func(*args)

    def __set_marquee_speed(self):
        windll.user32.SendMessageW(self.__handle, _SETMARQUEE,
                                   1, self._marquee_speed)

    def __update_element_text(self, element, text):
        if self.__handle is None:
            raise Exception(u'Dialog is not yet created, or has been '
                            u'destroyed.')
        windll.user32.SendMessageW(self.__handle, _SETELEMENT, element, text)

    def __update_progress_bar(self):
        windll.user32.SendMessageW(self.__handle, _SETPBARRANGE, 0,
                                   self._progress_bar[u'range'])
        windll.user32.SendMessageW(self.__handle, _SETPBARPOS,
                                   self._progress_bar[u'pos'], 0)
