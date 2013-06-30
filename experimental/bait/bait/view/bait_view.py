# -*- coding: utf-8 -*-
#
# bait/view/bait_view.py
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

import logging

from .. import presenter
from .impl import command_handler, filter_registry, image_loader, installer_tab


_logger = logging.getLogger(__name__)


class BaitView:
    '''This API was designed to be used from a single thread'''

    def __init__(self, wxParentNotebook, presenter_, viewIoGateway=None):
        '''Creates and configures bait widget hierarchies'''
        _logger.debug("initializing bait view")
        filterRegistry = filter_registry.FilterRegistry()
        self._installerTab = installer_tab.InstallerTab(
            wxParentNotebook, presenter_, filterRegistry, viewIoGateway)
        self._imageLoader = image_loader.ImageLoader(viewIoGateway,
                                                     presenter_.viewCommandQueue)
        self._commandHandler = command_handler.CommandHandler(
            presenter_.viewCommandQueue, filterRegistry,
            self._installerTab, self._imageLoader)
        self._presenter = presenter_

    def start(self):
        '''Loads saved state, starts threads and subcomponents (including presenter)'''
        filterStateMap = {
            presenter.FilterIds.PACKAGES_HIDDEN:False,
            presenter.FilterIds.PACKAGES_INSTALLED:True,
            presenter.FilterIds.PACKAGES_NOT_INSTALLED:True,
            presenter.FilterIds.FILES_PLUGINS:True,
            presenter.FilterIds.FILES_RESOURCES:False,
            presenter.FilterIds.FILES_OTHER:False,
            presenter.FilterIds.DIRTY_ADD:True,
            presenter.FilterIds.DIRTY_UPDATE:True,
            presenter.FilterIds.DIRTY_DELETE:True,
            presenter.FilterIds.CONFLICTS_SELECTED:True,
            presenter.FilterIds.CONFLICTS_UNSELECTED:False,
            presenter.FilterIds.CONFLICTS_ACTIVE:True,
            presenter.FilterIds.CONFLICTS_INACTIVE:False,
            presenter.FilterIds.CONFLICTS_HIGHER:True,
            presenter.FilterIds.CONFLICTS_LOWER:False,
            presenter.FilterIds.SELECTED_MATCHED:True,
            presenter.FilterIds.SELECTED_MISMATCHED:True,
            presenter.FilterIds.SELECTED_MISSING:True,
            presenter.FilterIds.SELECTED_NO_CONFLICTS:True,
            presenter.FilterIds.SELECTED_HAS_CONFLICTS:True,
            presenter.FilterIds.UNSELECTED_MATCHED:True,
            presenter.FilterIds.UNSELECTED_MISMATCHED:True,
            presenter.FilterIds.UNSELECTED_MISSING:True,
            presenter.FilterIds.UNSELECTED_NO_CONFLICTS:True,
            presenter.FilterIds.UNSELECTED_HAS_CONFLICTS:True,
            presenter.FilterIds.SKIPPED_NONGAME:True,
            presenter.FilterIds.SKIPPED_MASKED:False}
        filterMask = presenter.FilterIds.NONE
        for filterId in filterStateMap:
            if filterStateMap[filterId]:
                filterMask |= filterId
        self._installerTab.load(filterMask)
        _logger.debug("starting presenter")
        self._presenter.start(presenter.DetailsTabIds.GENERAL, filterMask)
        _logger.debug("starting processing threads")
        self._imageLoader.start()
        self._commandHandler.start()
        _logger.debug("view successfully started")

    def shutdown(self):
        '''Saves any dirty state, shuts down threads and subcomponents'''
        _logger.debug("discarding further output from presenter")
        self._imageLoader.shutdown_output()
        self._commandHandler.set_ignore_updates()
        _logger.debug("shutting down presenter")
        self._presenter.shutdown()
        _logger.debug("shutting down processing threads")
        self._commandHandler.shutdown()
        self._imageLoader.shutdown_input()
        _logger.debug("saving dirty widget state")
        self._installerTab.save_state()
        _logger.debug("view successfully shut down")

    def pause(self):
        '''Suggests that bait suspend operations; may not take effect immediately'''
        _logger.debug("pause requested")
        self._presenter.pause()

    def resume(self):
        '''Resumes from a pause'''
        _logger.debug("resume requested")
        self._presenter.resume()
