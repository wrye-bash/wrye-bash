# -*- coding: utf-8 -*-
#
# bait/presenter/bait_presenter.py
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

class BaitPresenter:
    def __init__(self, model, viewCommandQueue, presenterStateRootPath=None)
        self.viewCommandQueue = viewCommandQueue
        self._model = model
        self._stateRootPath = presenterStateRootPath

    def start(self):
        # TODO
        pass

    def shutdown(self):
        # TODO
        pass
