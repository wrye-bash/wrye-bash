# -*- coding: utf-8 -*-
#
# bait/presenter/bait_presneter_test.py
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

from .. import presenter
from . import bait_presenter
from ..test import mock_model


def presenter_test():
    presenterOutputQueue = Queue.Queue()
    _model = mock_model.MockModel()
    _presenter = bait_presenter.BaitPresenter(_model, presenterOutputQueue)
    _presenter.start(presenter.DetailsTabIds.GENERAL, {})

    # TODO: test

    _presenter.shutdown()
