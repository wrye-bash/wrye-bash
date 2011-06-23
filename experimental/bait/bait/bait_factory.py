# -*- coding: utf-8 -*-
#
# bait/bait_factory.py
#
# GPL License and Copyright Notice ============================================
#  This file is part of Wrye Bash.
#
#  Wrye Bash is free software: you can redistribute it and/or modify
#  it under the terms of the GNU General Public License as published by
#  the Free Software Foundation, either version 3 of the License, or
#  (at your option) any later version.
#
#  Wrye Bash is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
#
#  You should have received a copy of the GNU General Public License
#  along with Wrye Bash.  If not, see <http://www.gnu.org/licenses/>.
#
#  Wrye Bash Copyright (C) 2011 Myk Taylor
#
# =============================================================================

import Queue
import logging
import multiprocessing

from .view import bait_view
from .presenter import bait_presenter
from .model import bait_model


_logger = logging.getLogger(__name__)


def _create_queue(isMultiprocess):
    """Creates a communications queue"""
    if (isMultiprocess is True):
        return multiprocessing.Queue()
    else:
        return Queue.Queue()

def CreateBaitView(parent, presenter=None, model=None, isMultiprocess=False):
    _logger.debug("creating BAIT components")

    if presenter is not None:
        _logger.debug("using custom presenter (class: %s)", presenter.__class__)
    else:
        if model is not None:
            _logger.debug("using custom model (class: %s)", model.__class__)
        else:
            _logger.debug("instantiating default model")
            model = bait_model.BaitModel(_create_queue(isMultiprocess))
        _logger.debug("instantiating default presenter")
        presenter = bait_presenter.BaitPresenter(model, _create_queue(isMultiprocess))

    return bait_view.BaitView(parent, presenter)
