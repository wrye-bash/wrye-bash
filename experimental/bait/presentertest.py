#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# presentertest

import Queue
import fileinput
import logging
import logging.config
import threading

from bait import presenter
from bait.presenter import bait_presenter
from bait.test import mock_model


_logger = None


class Main:
    def __init__(self):
        presenterOutputQueue = Queue.Queue()
        _model = mock_model.MockModel()
        self._presenter = bait_presenter.BaitPresenter(_model, presenterOutputQueue)
        try:
            self._presenter.start(presenter.DETAILS_TAB_ID_GENERAL, {})
        except:
            self._presenter.shutdown()
            raise
        self._monitorThread = threading.Thread(name="Monitor", target=self.monitor_queue)
        self._monitorThread.start()

    def shutdown(self):
        _logger.info("starting shutdown sequence")
        self._presenter.shutdown()
        self._monitorThread.join()
        _logger.info("finished shutting down")

    def monitor_queue(self):
        _logger.info("monitoring UI update events")
        viewCommandQueue = self._presenter.viewCommandQueue
        while True:
            viewCommand = viewCommandQueue.get()
            if viewCommand is None:
                viewCommandQueue.task_done()
                break
            _logger.info("received ViewCommand: %s %s",
                         viewCommand.__class__.__name__, viewCommand.__dict__)
            viewCommandQueue.task_done()

    def main_loop(self):
        _logger.info("starting main loop")
        for line in fileinput.input():
            pass


if __name__ == "__main__":
    threading.current_thread().name = "Main"
    logging.config.fileConfig("logging.conf")
    _logger = logging.getLogger("presentertest")
    _logger.info("starting presentertest")
    app = Main()
    app.main_loop()
    app.shutdown()
    _logger.info("exiting presentertest")
    logging.shutdown()
