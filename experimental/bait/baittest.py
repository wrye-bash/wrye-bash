#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# baittest


import logging
import logging.config
import multiprocessing
import os.path
import threading
import wx

from bait import bait_factory
from bait.test import mock_model


class MainWindow(wx.Frame):
    def __init__(self, parent, title):
        # TODO: save and restore last window size
        wx.Frame.__init__(self, parent, title=title, size=(1050,600))
        self.Bind(wx.EVT_CLOSE, self._on_close)
        notebook = wx.Notebook(self)
        # TODO: use real model
        model_ = mock_model.MockModel()
        self._baitView = bait_factory.CreateBaitView(notebook, model=model_)
        #self._baitView = bait_factory.CreateBaitView(notebook,
        #                         os.path.join("testtmp", "installers"),
        #                         os.path.join("testtmp", "gamedata"),
        #                         os.path.join("testtmp", "presenterdata"),
        #                         os.path.join("testtmp", "modeldata"))
        notebook.AddPage(self._baitView, "Installers")
        for tabName in ("Mods", "Saves", "INI Edits", "Screenshots", "People"):
            notebook.AddPage(wx.Panel(notebook), tabName)
        sizer = wx.BoxSizer()
        sizer.Add(notebook, 1, wx.EXPAND)
        self.SetMinSize(sizer.GetMinSize())
        self.SetSizer(sizer)
        self.CreateStatusBar()
        self.Show(True)
        self._baitView.start()

    def _on_close(self, event):
        self._baitView.shutdown()
        event.Skip()

if __name__ == "__main__":
    multiprocessing.current_process().name = "Main"
    threading.current_thread().name = "Main"
    logging.config.fileConfig("logging.conf")
    logger = logging.getLogger("baittest")
    logger.info("starting baittest")
    app = wx.App(False)
    frame = MainWindow(None, "Bash Asynchronous Installer Tab (bait) Test App")
    app.MainLoop()
    logger.info("exiting baittest")
