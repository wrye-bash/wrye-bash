# -*- coding: utf-8 -*-
#
# bait/presenter/view_commands.py
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

from cStringIO import StringIO


# command IDs
ADD_GROUP = 1
ADD_PACKAGE = 2
EXPAND_GROUP = 3
CLEAR_PACKAGES = 4
SET_FILTER_STATS = 5
SET_STATUS = 6
SET_PACKAGE_LABEL = 7
ADD_FILE = 8
CLEAR_FILES = 9
SET_FILE_DETAILS = 10
SELECT_PACKAGES = 11
EXPAND_DIR = 12
SELECT_FILES = 13
SET_STYLE_MAPS = 14
SET_PACKAGE_INFO = 15
DISPLAY_ERROR = 16
SET_SUMMARY = 17

# style values
FONT_STYLE_BOLD_FLAG = 1
FONT_STYLE_ITALICS_FLAG = 2
TEXT_DISABLED = 1
TEXT_HAS_INACTIVE_OVERRIDDE = 2
HIGHLIGHT_ERROR = 3
HIGHLIGHT_MISSING_DEPENDENCY = 4
HIGHLIGHT_DIRTY = 5
HIGHLIGHT_LOADING = 6
HIGHLIGHT_OK = 7
ICON_PROJECT_MATCHES = 1
ICON_PROJECT_MATCHES_WIZ = 2
ICON_PROJECT_MISMATCHED = 3
ICON_PROJECT_MISMATCHED_WIZ = 4
ICON_PROJECT_MISSING = 5
ICON_PROJECT_MISSING_WIZ = 6
ICON_PROJECT_EMPTY = 7
ICON_PROJECT_EMPTY_WIZ = 8
ICON_PROJECT_UNINSTALLABLE = 9
ICON_INSTALLER_MATCHES = 10
ICON_INSTALLER_MATCHES_WIZ = 11
ICON_INSTALLER_MISMATCHED = 12
ICON_INSTALLER_MISMATCHED_WIZ = 13
ICON_INSTALLER_MISSING = 14
ICON_INSTALLER_MISSING_WIZ = 15
ICON_INSTALLER_EMPTY = 16
ICON_INSTALLER_EMPTY_WIZ = 17
ICON_INSTALLER_UNINSTALLABLE = 18

# status states
STATUS_OK = 1
STATUS_LOADING = 2
STATUS_DIRTY = 3
STATUS_UNSTABLE = 4

OP_ANNEAL = 1
OP_RENAME = 2
OP_DELETE = 3


class ViewCommandStyle:
    def __init__(self, fontStyleMask=None, textColorId=None, hilightColorId=None,
                 checkboxState=None, iconId=None):
        self.fontStyleMask = fontStyleMask
        self.textColorId = textColorId
        self.hilightColorId = hilightColorId
        self.checkboxState = checkboxState
        self.iconId = iconId

class IoOperation:
    def __init__(self, type, target):
        self.type = type
        self.target = target


# command classes
class ViewCommand:
    '''The commandId refers to the subclass type.  The requestId is the id of
    the associated request that instigated this command.  If this command was
    not sent in response to a request, it will be set to None'''
    def __init__(self, commandId):
        self.commandId = commandId
    def __str__(self):
        outStr = StringIO()
        outStr.write(self.__class__.__name__)
        outStr.write("[")
        isFirst = True
        for varName in self.__dict__:
            if not varName.startswith("_"):
                if not isFirst:
                    outStr.write("; ")
                outStr.write(varName)
                outStr.write("=")
                outStr.write(str(self.__dict__[varName]))
                isFirst = False
        outStr.write("]")
        return outStr.getvalue()


class _AddNode(ViewCommand):
    '''Adds a node to a tree
       The parent node will either have been previously sent or will be None,
       meaning top-level.  The predecessor node will either have been previously
       sent or be None, meaning "first child of parent"'''
    def __init__(self, commandId, label, nodeId, parentNodeId, predecessorNodeId,
                 style=None):
        ViewCommand.__init__(self, commandId)
        self.label = label
        self.nodeId = nodeId
        self.parentNodeId = parentNodeId
        self.predecessorNodeId = predecessorNodeId
        self.style = style

class AddGroup(_AddNode):
    '''Adds a group node to the packages tree'''
    def __init__(self, label, nodeId, parentNodeId, predecessorNodeId, style=None):
        _AddNode.__init__(self, ADD_GROUP, label, nodeId, parentNodeId, predecessorNodeId,
                          style)

class AddPackage(_AddNode):
    '''Adds a package node to the packages tree'''
    def __init__(self, label, nodeId, parentNodeId, predecessorNodeId, style=None):
        _AddNode.__init__(self, ADD_PACKAGE, label, nodeId, parentNodeId,
                          predecessorNodeId, style)

class ExpandGroup(ViewCommand):
    def __init__(self, nodeId):
        ViewCommand.__init__(self, EXPAND_GROUP)
        self.nodeId = nodeId

class ExpandDir(ViewCommand):
    def __init__(self, nodeId):
        ViewCommand.__init__(self, EXPAND_DIR)
        self.nodeId = nodeId

class ClearPackages(ViewCommand):
    def __init__(self):
        ViewCommand.__init__(self, CLEAR_PACKAGES)

class SelectPackages(ViewCommand):
    '''nodeIds will be a list of node Ids to select'''
    def __init__(self, nodeIds):
        ViewCommand.__init__(self, SELECT_PACKAGES)
        self.nodeIds = nodeIds

class SelectFiles(ViewCommand):
    '''nodeIds will be a list of node Ids to select'''
    def __init__(self, nodeIds):
        ViewCommand.__init__(self, SELECT_FILES)
        self.nodeIds = nodeIds

class SetFilterStats(ViewCommand):
    def __init__(self, filterId, current, total):
        ViewCommand.__init__(self, SET_FILTER_STATS)
        self.filterId = filterId
        self.current = current
        self.total = total

class SetSummary(ViewCommand):
    def __init__(self, installedFiles, installedPlugins, bainMb, installedMb, freeMb):
        ViewCommand.__init__(self, SET_SUMMARY)
        self.installedFiles = installedFiles
        self.installedPlugins = installedPlugins
        self.bainMb = bainMb
        self.installedMb = installedMb
        self.freeMb = freeMb

class SetStatus(ViewCommand):
    def __init__(self, status, hilightColorId, loadingComplete=None,
                 loadingTotal=None, ioOperations=None):
        ViewCommand.__init__(self, SET_STATUS)
        self.status = status
        self.hilightColorId = hilightColorId
        self.loadingComplete = loadingComplete
        self.loadingTotal = loadingTotal
        self.ioOperations = ioOperations

class _SetText(ViewCommand):
    '''If text is None, it means nothing is selected.  If text is the
    empty string, it means there is no text to display for that item'''
    def __init__(self, commandId, text):
        ViewCommand.__init__(self, commandId)
        self.text = text

class SetPackageLabel(_SetText):
    """None means no package is selected, a blank label means multiple packages are
    selected"""
    def __init__(self, text):
        _SetText.__init__(self, SET_PACKAGE_LABEL, text)

class AddFile(_AddNode):
    '''Adds a subpackage/file/directory node to the file tree'''
    def __init__(self, label, nodeId, parentNodeId, predecessorNodeId, style=None):
        _AddNode.__init__(self, ADD_FILE, label, nodeId, parentNodeId,
                          predecessorNodeId, style)

class ClearFiles(ViewCommand):
    def __init__(self):
        ViewCommand.__init__(self, CLEAR_FILES)

class SetFileDetails(_SetText):
    def __init__(self, text):
        _SetText.__init__(self, SET_FILE_DETAILS, text)

class SetStyleMaps(ViewCommand):
    '''Contains the map from style IDs to RGB tuples (for colors) and file resources
    (for images)'''
    def __init__(self, colorMap, checkedIconMap, uncheckedIconMap):
        ViewCommand.__init__(self, SET_STYLE_MAPS)
        self.colorMap = colorMap
        self.checkedIconMap = checkedIconMap
        self.uncheckedIconMap = uncheckedIconMap

class SetPackageInfo(ViewCommand):
    """sets the data for one of the package info tabs
    For the General tab: data is a dictionary that has the following keys:
      isArchive: boolean indicating whether the package is an archive
      isHidden: boolean indicating whether the package is hidden
      isInstalled: boolean indicating whether the package is installed
      packageSize: a string representing the package size in the installers directory
      contentsSize: a string representing the cumulative size of the package contents
      lastModifiedTimestamp: a string representing the last modification date
      The following additional keys are optional, interpreted as 0 if absent
      numFiles, numDirty, numOverridden, numSkipped,
      numSelectedMatched, numSelectedMismatched, numSelectedOverridden,
      numSelectedMissing, numTotalSelected, numUnselectedMatched,
      numUnselectedMismatched, numUnselectedOverridden, numUnselectelectedMissing,
      numTotalUnselected, numTotalMatched, numTotalMismatched, numTotalOverridden,
      numTotalMissing, numTotalSelectable
    For the Dirty tab: data is a list of tuples: (actionType, path), where actionType
      is one of the dirty filter IDs
    For the Conflicts tab, TODO: define
    """
    def __init__(self, tabId, data):
        ViewCommand.__init__(self, SET_PACKAGE_INFO)
        self.tabId = tabId
        self.data = data

class DisplayError(ViewCommand):
    """Error codes instead of a message since we want to avoid localizable strings in
    the non-view layers"""
    def __init__(self, errorCode, resourceName):
        ViewCommand.__init__(self, DISPLAY_ERROR)
        self.errorCode = errorCode
        self.resourceName = resourceName

