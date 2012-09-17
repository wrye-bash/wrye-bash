#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# baittest


import argparse
import locale
import logging
import logging.config
import multiprocessing
import re
import sys
import threading
import wx

from bait import bait_factory
from bait.test import mock_presenter, mock_model


_logger = None


class _MainWindow(wx.Frame):
    def __init__(self, options):
        windowTitle = "Bash Asynchronous Installer Tab (BAIT) Test App"
        if options.view:
            windowTitle += " [view test]"
        elif options.presenter:
            windowTitle += " [presenter test]"
        elif options.model:
            windowTitle += " [model test]"
        wx.Frame.__init__(self, None, title=windowTitle,
                          size=(options.width,options.height))
        self.Bind(wx.EVT_CLOSE, self._on_close)
        notebook = wx.Notebook(self)
        if options.model:
            raise NotImplementedError("mock IO proxy not yet implemented")
        elif options.presenter:
            self._baitView = bait_factory.CreateBaitView(
                notebook,
                model=mock_model.MockModel(), isMultiprocess=options.multiprocess)
        elif options.view:
            self._baitView = bait_factory.CreateBaitView(
                notebook,
                presenter=mock_presenter.MockPresenter(),
                isMultiprocess=options.multiprocess)
        else:
            self._baitView = bait_factory.CreateBaitView(
                notebook, isMultiprocess=options.multiprocess)
        notebook.AddPage(self._baitView, "Installers")
        for tabName in ("Mods", "Saves", "INI Edits", "Screenshots", "People"):
            notebook.AddPage(wx.Panel(notebook), tabName)
        sizer = wx.BoxSizer()
        sizer.Add(notebook, 1, wx.EXPAND)
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
        if not options.quiet:
            # TODO: put up a dialog explaining the current mode and how to get to other modes
            # TODO: list what is done and what is not done
            pass

    def _on_close(self, event):
        self._baitView.shutdown()
        event.Skip()


def _dump_env():
    _logger.info("Python version: %d.%d.%d",
                 sys.version_info.major, sys.version_info.minor, sys.version_info.micro)
    _logger.info("wxPython version: %s", wx.version())
    _logger.info("input encoding: %s; output encoding: %s; locale: %s",
                 sys.stdin.encoding, sys.stdout.encoding, locale.getdefaultlocale())

def _parse_commandline():
    parser = argparse.ArgumentParser(description='The BAIT interactive GUI test driver.')

    parser.add_argument(
        '-w', '--windowsize', metavar='DIMENSIONS', default='1050x600',
        help='the dimensions of the GUI window;  defaults to "%(default)s"')
    parser.add_argument(
        '-x', '--multiprocess', action='store_true',
        help='test multiprocess operation; if this is not specified, all layers run in' \
        ' the same process')
    parser.add_argument(
        '-q', '--quiet', action='store_true',
        help='do not put up the explanitory window at program start')

    testTargetGroup = parser.add_argument_group(
        'Test targets',
        'Specify one of the following options to mock out lower layers and test with' \
        ' dummy data.')
    testTargets = testTargetGroup.add_mutually_exclusive_group()
    # default to true for now until we get the other pieces working
    testTargets.add_argument('-v', '--view', action='store_true', default=True,
                             help='test the view by mocking out the presenter')
    testTargets.add_argument('-p', '--presenter', action='store_true',
                             help='test the presenter by mocking out the model')
    testTargets.add_argument('-m', '--model', action='store_true',
                             help='test the model by mocking out the I/O interface')

    pathGroup = parser.add_argument_group(
        'Paths',
        'Specifies the paths used by the BAIT stack.  Note that these paths are only ' \
        'used if nothing is mocked out.')
    pathGroup.add_argument(
        '-i', '--installersRoot', metavar='PATH', default='testdata/installers',
        help='the root directory for the installers; defaults to "%(default)s"')
    pathGroup.add_argument(
        '-d', '--dataRoot', metavar='PATH', default='testdata/data',
        help='the root directory for the installed data; defaults to "%(default)s"')
    pathGroup.add_argument(
        '-s', '--stateRoot', metavar='PATH', default=None,
        help='the root directory for the state.  If this is not set (the default),' \
        ' saved state is not loaded or persisted between runs.')
    pathGroup.add_argument(
        '-c', '--cacheRoot', metavar='PATH', default='testdata/cache',
        help='the root directory for the preview cache; defaults to "%(default)s"')

    options = parser.parse_args()

    # transform the dimensions string into width and height parameters
    dimensionMatch = re.match("(\d+)x(\d+)", options.windowsize, re.I)
    if dimensionMatch is None:
        parser.exit(2, "invalid GUI window dimensions: %s\n" % options.windowsize)
    options.width = int(dimensionMatch.group(1))
    options.height = int(dimensionMatch.group(2))

    return options


if __name__ == "__main__":
    multiprocessing.current_process().name = "Main"
    threading.current_thread().name = "Main"
    logging.config.fileConfig("logging.conf")
    _logger = logging.getLogger("baittest")
    _logger.info("starting baittest")
    _dump_env()
    options = _parse_commandline()
    _logger.info("options: %s", options)
    app = wx.App(False)
    _MainWindow(options)
    app.MainLoop()
    _logger.info("exiting baittest")
