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
#  Wrye Bash copyright (C) 2005-2009 Wrye, 2010-2022 Wrye Bash Team
#  https://github.com/wrye-bash
#
# =============================================================================
"""Houses DocumentViewer, a class for viewing various types of documents (e.g.
webpages, text and PDFs)."""

__author__ = u'Infernio'

# Try to import html2 webview, may not be available everywhere
try:
    import wx.html2 as _wx_html2
    if _wx_html2.WebView.IsBackendAvailable(_wx_html2.WebViewBackendEdge):
        _browser_backend = _wx_html2.WebViewBackendEdge
    else:
        _browser_backend = _wx_html2.WebViewBackendDefault
except ImportError:
    _wx_html2 = _browser_backend = None
# Try to import the PDF viewer, may not be available everywhere
try:
    # wx.lib.pdfviewer uses a raw print statment, UGH!
    from ..bolt import redirect_stdout_to_deprint
    with redirect_stdout_to_deprint():
        from wx.lib.pdfviewer import pdfViewer as _PdfViewer
except ImportError:
    _PdfViewer = None
import wx as _wx

import webbrowser
from enum import Enum
from urllib.request import pathname2url
from urllib.parse import urljoin

from .base_components import _AComponent
from .buttons import BackwardButton, ForwardButton, ReloadButton
from .text_components import TextArea
from .layouts import VLayout
from .. import bass ##: drop this
from ..bolt import decoder, deprint
from ..exception import StateError

def web_viewer_available():
    """Checks if WebViewer and its wx backing are available, meaning that we
    can render HTML.

    :return: True if we can render HTML."""
    return bool(_wx_html2)

def pdf_viewer_available():
    """Checks if pdfViewer is available, meaning that we can display PDFs.

    :return: True if we can render PDFs."""
    return bool(_PdfViewer) and _wx.VERSION >= (4, 1)

class ViewerMode(Enum):
    """The different types of viewers that DocumentViewer can display."""
    HTML = 'html'
    PDF =  'pdf'
    TEXT = 'txt'

class WebViewer(_AComponent):
    """Implements an HTML & CSS renderer with JavaScript support. May not be
    available on all platforms (see gui.webview.web_viewer_available()). Also
    creates three navigation buttons for going back and forwards in the
    browsing history and reloading the current page.

    Basic control from the Python side is offered through methods for
    navigating the history, clearing the history, navigating to a URL and
    reloading the current page."""
    _wx_widget_type = _wx_html2.WebView.New
    _native_widget: _wx_html2.WebView

    def __init__(self, parent, reload_ico, buttons_parent=None):
        """Creates a new WebViewer with the specified parent.

        :param parent: The object that this web viewer belongs to. May be a wx
                       object or a component.
        :param reload_ico: a _wx.Bitmap to use for the reload button
        :param buttons_parent: The object that the navigation buttons belong
                               to. If None, the same parent will be used."""
        if buttons_parent is None: buttons_parent = parent
        super().__init__(parent, backend=_browser_backend)
        self._back_button = BackwardButton(buttons_parent)
        self._back_button.on_clicked.subscribe(self.go_back)
        self._forward_button = ForwardButton(buttons_parent)
        self._forward_button.on_clicked.subscribe(self.go_forward)
        self._reload_button = ReloadButton(buttons_parent, reload_ico)
        self._reload_button.on_clicked.subscribe(self.reload)
        # Events - internal use only for now, expose if needed
        self._on_new_window = self._evt_handler(
            _wx_html2.EVT_WEBVIEW_NEWWINDOW, lambda event: [event.GetURL()])
        self._on_new_window.subscribe(self._handle_new_window_opened)
        self._on_loading = self._evt_handler(_wx_html2.EVT_WEBVIEW_NAVIGATED)
        self._on_loading.subscribe(self.update_buttons)

    @staticmethod
    def _handle_new_window_opened(new_url): # type: (str) -> None
        """Internal method used as a callback when attempting to open a link
        in a new tab or window. We don't support that, so we just open it in
        the user's browser instead.

        :param new_url: The URL of the visited page."""
        webbrowser.open(new_url, new=2)

    def clear_history(self):
        """Clears the browsing history. Navigation buttons will be updated."""
        self._native_widget.ClearHistory()
        self.update_buttons()

    def get_navigation_buttons(self):
        """Returns a tuple containing references to the three navigation
        buttons for this WebViewer. The first is a 'back' button that will go
        to the last page in the browsing history when clicked, the second is a
        'forward' button that will go to the next page in the browsing history
        when clicked and the third is a 'reload' button which will reload the
        current page. They will be disabled when there are no pages for them to
        go to or when the entire WebViewer is disabled.

        :return: A tuple containing the navigation buttons for this
                 WebViewer."""
        return self._back_button, self._forward_button, self._reload_button

    def go_back(self):
        """Goes one step back in the browsing history, if that is possible.
        Navigation buttons will be updated accordingly."""
        if self._native_widget.CanGoBack():
            self._native_widget.GoBack()
        # do this just in case CanGoBack() is false and we're out of sync
        self.update_buttons()

    def go_forward(self):
        """Goes one step forward in the browsing history, if that is possible.
        Navigation buttons will be updated accordingly."""
        if self._native_widget.CanGoForward():
            self._native_widget.GoForward()
        # do this just in case CanGoForward() is false and we're out of sync
        self.update_buttons()

    def open_file(self, file_path): # type: (str) -> None
        """Opens the specified file by turning it into a 'file:' URL.

        :param file_path: The path to the file to open."""
        file_url = urljoin(u'file:', pathname2url(file_path))
        self.open_url(file_url)

    def open_url(self, url): # type: (str) -> None
        """Opens the specified URL.

        :param url: The URL to open."""
        self._native_widget.LoadURL(url)

    def reload(self, bypass_cache=False):
        """Reloads the current website.

        :param bypass_cache: If set to True, disregard any entries in the
                             cache and reload them from the website instead."""
        if bypass_cache:
            reload_flags = _wx_html2.WEBVIEW_RELOAD_NO_CACHE
        else:
            reload_flags = _wx_html2.WEBVIEW_RELOAD_DEFAULT
        self._native_widget.Reload(reload_flags)

    def update_buttons(self):
        """Enables or disables the navigation buttons depending on the status
        of the browsing history (is there anything to go back / forward to?)
        and whether or not the WebViewer itself is enabled (if the WebViewer
        is disabled, the navigation buttons will be disabled as well)."""
        can_enable = self.enabled
        self._back_button.enabled = can_enable and \
                                    self._native_widget.CanGoBack()
        self._forward_button.enabled = can_enable and \
                                       self._native_widget.CanGoForward()
        self._reload_button.enabled = can_enable

class PDFViewer(_AComponent):
    """Implements a simple PDF viewer. Only available if PyMuPDF or PyPDF2 is
    installed. PyPDF2 is pure Python, but PyMuPDF is *vastly* more complete and
    hence preferred."""
    _wx_widget_type = _PdfViewer
    _native_widget: _PdfViewer

    def __init__(self, parent):
        super(PDFViewer, self).__init__(parent, nid=-1, pos=(-1, -1),
            size=(-1, -1), style=0) # has no defaults, so need to specify them

    def open_file(self, file_path: str) -> None:
        """Opens the specified PDF file.

        :param file_path: The path to the file to open."""
        self._native_widget.LoadFile(file_path)

class DocumentViewer(_AComponent):
    """A viewer for a variety of document types. Can display webpages, text and
    PDFs."""
    _wx_widget_type = _wx.Window

    def __init__(self, parent):
        """Creates a new DocumentViewer with the specified parent.

        :param parent: The object that this HTML display belongs to. May be a
                       wx object or a component."""
        super(DocumentViewer, self).__init__(parent)
        # init the fallback/plaintext widget
        self._text_ctrl = TextArea(self, editable=False, auto_tooltip=False)
        items = [self._text_ctrl]
        reload_ico = _wx.Bitmap(bass.dirs[u'images'].join(u'reload16.png').s,
                                _wx.BITMAP_TYPE_PNG)
        if web_viewer_available():
            # We can render HTML, create the WebViewer and use its buttons
            self._html_ctrl = WebViewer(self, reload_ico, parent)
            self._prev_button, self._next_button, self._reload_button = \
                self._html_ctrl.get_navigation_buttons()
            items.append(self._html_ctrl)
            self._text_ctrl.enabled = False
        else:
            # Emulate the buttons WebViewer would normally provide
            self._prev_button = BackwardButton(parent)
            self._next_button = ForwardButton(parent)
            self._reload_button = ReloadButton(parent, reload_ico)
        if pdf_viewer_available():
            self._pdf_ctrl = PDFViewer(self)
            items.append(self._pdf_ctrl)
        VLayout(item_weight=4, item_expand=True, items=items).apply_to(self)
        self.switch_to_text() # default to text

    def _update_views(self, new_viewer_mode: ViewerMode):
        """Internal method to switch between display types, as well as
        update the state of the WebViewer buttons.

        :param new_viewer_mode: The ViewerMode that we're switching to."""
        if web_viewer_available():
            self._html_ctrl.enabled = new_viewer_mode is ViewerMode.HTML
            self._html_ctrl.visible = new_viewer_mode is ViewerMode.HTML
            self._html_ctrl.update_buttons()
        if pdf_viewer_available():
            self._pdf_ctrl.enabled = new_viewer_mode is ViewerMode.PDF
            self._pdf_ctrl.visible = new_viewer_mode is ViewerMode.PDF
        self._text_ctrl.enabled = new_viewer_mode is ViewerMode.TEXT
        self._text_ctrl.visible = new_viewer_mode is ViewerMode.TEXT

    @property
    def fallback_text(self):
        """Returns the fallback text displayed by the text display."""
        return self._text_ctrl.text_content

    @fallback_text.setter
    def fallback_text(self, new_fallback):
        """Changes the fallback text that will be displayed by the text
        display, but does not switch to text mode - see switch_to_text()."""
        self._text_ctrl.text_content = new_fallback

    def load_text(self, target_text):
        """Switches to text mode (see switch_to_text()) and sets the
        specified text as the unmodified contents of the text display."""
        if not isinstance(target_text, str): # needs to be unicode by now
            raise StateError('DocumentViewer can only load unicode text.')
        self._text_ctrl.text_content = target_text
        self._text_ctrl.modified = False
        self.switch_to_text()

    def is_text_modified(self):
        """Returns True if the text display has been marked as modified,
        either by the user editing it or by calling set_text_modified(True)."""
        return self._text_ctrl.modified

    def set_text_modified(self, text_modified):
        """Changes whether the text display is marked as modified or not."""
        self._text_ctrl.modified = text_modified

    def set_text_editable(self, text_editable):
        # type: (bool) -> None
        """Changes whether or not the text display is editable."""
        self._text_ctrl.editable = text_editable

    def switch_to_html(self):
        """Disables the other viewers and switches to HTML mode, if WebViewer
        is available."""
        if not web_viewer_available(): return
        self._update_views(new_viewer_mode=ViewerMode.HTML)
        self.update_layout()

    def switch_to_pdf(self):
        """Disables the other viewers and switches to PDF mode, if PDFViewer is
        available."""
        if not pdf_viewer_available(): return
        self._update_views(new_viewer_mode=ViewerMode.PDF)
        self.update_layout()

    def switch_to_text(self):
        """Disables the other viewers and switches to raw text mode."""
        self._update_views(new_viewer_mode=ViewerMode.TEXT)
        self.update_layout()

    def get_buttons(self):
        """Returns the three navigation buttons as a tuple."""
        return self._prev_button, self._next_button, self._reload_button

    def try_load_html(self, file_path):
        """Load a HTML file if WebViewer is available, or load the text.

        :param file_path: A bolt.Path instance or a unicode string."""
        if web_viewer_available():
            self._html_ctrl.clear_history()
            self._html_ctrl.open_file(u'%s' % file_path)
            self.switch_to_html()
        else:
            self.try_load_text(file_path)

    def try_load_pdf(self, file_path):
        """Load a PDF file if PDFViewer is available, or load the text.

        :param file_path: A bolt.Path instance or a unicode string."""
        pdf_path = u'%s' % file_path
        with open(pdf_path, u'rb') as ins:
            pdf_valid = ins.read(4) == b'%PDF'
        if not pdf_valid:
            deprint(u'%s is not a valid PDF' % pdf_path)
        if pdf_valid and pdf_viewer_available():
            self._pdf_ctrl.open_file(pdf_path)
            self.switch_to_pdf()
        else:
            self.try_load_text(file_path)

    def try_load_text(self, file_path):
        """Load a file as raw text.

        :param file_path: A bolt.Path instance or a unicode string."""
        # We can't assume that this is UTF-8 - e.g. some official Beth docs in
        # Morrowind are cp1252. However, it most likely is UTF-8 or
        # UTF-8-compatible (ASCII), so try that first.
        with file_path.open(u'rb') as ins:
            self.load_text(decoder(ins.read(), u'utf-8'))
