#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# viewtest


import logging
import logging.config
import multiprocessing
import threading
import wx

from bait import bait_factory
from bait.test import mock_presenter


_logger = None


class MainWindow(wx.Frame):
    def __init__(self, parent, title):
        wx.Frame.__init__(self, parent, title=title, size=(1050,600))
        self.Bind(wx.EVT_CLOSE, self._on_close)
        self._baitView = bait_factory.CreateBaitView(
            self, presenter=mock_presenter.MockPresenter())
        sizer = wx.BoxSizer()
        sizer.Add(self._baitView, 1, wx.EXPAND)
        self.SetMinSize(sizer.GetMinSize())
        self.SetSizer(sizer)
        self.CreateStatusBar()
        self.Show(True)
        try:
            self._baitView.start()
        except Exception as e:
            _logger.error("caught exception while starting up")
            _logger.exception(e)
            self._baitView.shutdown()
            raise

    def _on_close(self, event):
        self._baitView.shutdown()
        event.Skip()


if __name__ == "__main__":
    multiprocessing.current_process().name = "Main"
    threading.current_thread().name = "Main"
    logging.config.fileConfig("logging.conf")
    _logger = logging.getLogger("viewtest")
    _logger.info("starting viewtest")
    app = wx.App(False)
    frame = MainWindow(None, "Bash Asynchronous Installer Tab (bait) View Test")
    app.MainLoop()
    _logger.info("exiting viewtest")
