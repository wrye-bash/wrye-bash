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

from .. import model
from ..util import debug_utils, enum


class CommandIds(enum.Enum):
    __enumerables__ = ('UNKNOWN', 'ADD_GROUP', 'UPDATE_GROUP', 'ADD_PACKAGE',
                       'UPDATE_PACKAGE', 'REMOVE_PACKAGES_TREE_NODE', 'EXPAND_GROUP',
                       'CLEAR_PACKAGES', 'SET_FILTER_STATS', 'SET_STATUS',
                       'SET_PACKAGE_LABEL', 'ADD_FILE', 'CLEAR_FILES', 'SET_FILE_DETAILS',
                       'SELECT_PACKAGES', 'EXPAND_DIR', 'SELECT_FILES', 'SET_STYLE_MAPS',
                       'SET_PACKAGE_INFO', 'DISPLAY_ERROR', 'SET_SUMMARY')
    # for autocomplete
    ADD_GROUP = None
    UPDATE_GROUP = None
    ADD_PACKAGE = None
    UPDATE_PACKAGE = None
    REMOVE_PACKAGES_TREE_NODE = None
    EXPAND_GROUP = None
    CLEAR_PACKAGES = None
    SET_FILTER_STATS = None
    SET_STATUS = None
    SET_PACKAGE_LABEL = None
    ADD_FILE = None
    CLEAR_FILES = None
    SET_FILE_DETAILS = None
    SELECT_PACKAGES = None
    EXPAND_DIR = None
    SELECT_FILES = None
    SET_STYLE_MAPS = None
    SET_PACKAGE_INFO = None
    DISPLAY_ERROR = None
    SET_SUMMARY = None

class FontStyleIds(enum.FlagEnum):
    __enumerables__ = ('NONE', 'BOLD', 'ITALICS')
    # for autocomplete
    NONE = None
    BOLD = None
    ITALICS = None

class ForegroundColorIds(enum.Enum):
    __enumerables__ = ('UNKNOWN', 'DISABLED', 'HAS_SUBPACKAGES', 'HAS_INACTIVE_OVERRIDE')
    # for autocomplete
    DISABLED = None
    HAS_SUBPACKAGES = None
    HAS_INACTIVE_OVERRIDDE = None

class HighlightColorIds(enum.Enum):
    __enumerables__ = ('UNKNOWN', 'ERROR', 'MISSING_DEPENDENCY', 'DIRTY', 'LOADING', 'OK')
    # for autocomplete
    ERROR = None
    MISSING_DEPENDENCY = None
    DIRTY = None
    LOADING = None
    OK = None

class IconIds(enum.Enum):
    __enumerables__ = ('UNKNOWN', 'PROJECT_MATCHES', 'PROJECT_MATCHES_WIZ',
                       'PROJECT_MISMATCHED', 'PROJECT_MISMATCHED_WIZ', 'PROJECT_MISSING',
                       'PROJECT_MISSING_WIZ', 'PROJECT_EMPTY', 'PROJECT_EMPTY_WIZ',
                       'PROJECT_UNINSTALLABLE', 'INSTALLER_MATCHES',
                       'INSTALLER_MATCHES_WIZ', 'INSTALLER_MISMATCHED',
                       'INSTALLER_MISMATCHED_WIZ', 'INSTALLER_MISSING',
                       'INSTALLER_MISSING_WIZ', 'INSTALLER_EMPTY', 'INSTALLER_EMPTY_WIZ',
                       'INSTALLER_UNINSTALLABLE')
    # for autocomplete
    PROJECT_MATCHES = None
    PROJECT_MATCHES_WIZ = None
    PROJECT_MISMATCHED = None
    PROJECT_MISMATCHED_WIZ = None
    PROJECT_MISSING = None
    PROJECT_MISSING_WIZ = None
    PROJECT_EMPTY = None
    PROJECT_EMPTY_WIZ = None
    PROJECT_UNINSTALLABLE = None
    INSTALLER_MATCHES = None
    INSTALLER_MATCHES_WIZ = None
    INSTALLER_MISMATCHED = None
    INSTALLER_MISMATCHED_WIZ = None
    INSTALLER_MISSING = None
    INSTALLER_MISSING_WIZ = None
    INSTALLER_EMPTY = None
    INSTALLER_EMPTY_WIZ = None
    INSTALLER_UNINSTALLABLE = None

class Status(model.Status):
    pass

class Style(debug_utils.Dumpable):
    def __init__(self, fontStyleMask=FontStyleIds.NONE, foregroundColorId=None,
                 highlightColorId=None, checkboxState=None, iconId=None):
        self.fontStyleMask = fontStyleMask
        self.foregroundColorId = foregroundColorId
        self.highlightColorId = highlightColorId
        self.checkboxState = checkboxState
        self.iconId = iconId
    def __cmp__(self, other):
        return self.fontStyleMask == other.fontStyleMask and \
               self.foregroundColorId == other.foregroundColorId and \
               self.highlightColorId == other.highlightColorId and \
               self.checkboxState == other.checkboxState and \
               self.iconId == other.iconId

class IoOperation(debug_utils.Dumpable):
    def __init__(self, type, target):
        self.type = type
        self.target = target


# command classes
class ViewCommand(debug_utils.Dumpable):
    '''The commandId indicates the subclass type'''
    def __init__(self, commandId):
        self.commandId = commandId

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
        _AddNode.__init__(self, CommandIds.ADD_GROUP, label, nodeId, parentNodeId,
                          predecessorNodeId, style)

class UpdateGroup(_AddNode):
    '''Updates a group node in the packages tree'''
    def __init__(self, label, nodeId, parentNodeId, predecessorNodeId, style=None):
        _AddNode.__init__(self, CommandIds.UPDATE_GROUP, label, nodeId, parentNodeId,
                          predecessorNodeId, style)

class AddPackage(_AddNode):
    '''Adds a package node to the packages tree'''
    def __init__(self, label, nodeId, parentNodeId, predecessorNodeId, style=None):
        _AddNode.__init__(self, CommandIds.ADD_PACKAGE, label, nodeId, parentNodeId,
                          predecessorNodeId, style)

class UpdatePackage(_AddNode):
    '''Updates a package node in the packages tree'''
    def __init__(self, label, nodeId, parentNodeId, predecessorNodeId, style=None):
        _AddNode.__init__(self, CommandIds.UPDATE_PACKAGE, label, nodeId, parentNodeId,
                          predecessorNodeId, style)

class _RemoveNode(ViewCommand):
    '''Removes a node from a tree'''
    def __init__(self, commandId, nodeId):
        ViewCommand.__init__(self, commandId)
        self.nodeId = nodeId

class RemovePackagesTreeNode(_RemoveNode):
    '''Removes a node from the packages tree'''
    def __init__(self, nodeId):
        _RemoveNode.__init__(self, CommandIds.REMOVE_PACKAGES_TREE_NODE, nodeId)

class _ExpandCommand(ViewCommand):
    '''Controls expansion and collapse of tree nodes'''
    def __init__(self, commandId, nodeId, isExpanded):
        ViewCommand.__init__(self, CommandIds.EXPAND_GROUP)
        self.nodeId = nodeId
        self.isExpanded = isExpanded

class ExpandGroup(_ExpandCommand):
    def __init__(self, nodeId, isExpanded):
        _ExpandCommand.__init__(self, CommandIds.EXPAND_GROUP, nodeId, isExpanded)

class ExpandDir(_ExpandCommand):
    def __init__(self, nodeId, isExpanded):
        _ExpandCommand.__init__(self, CommandIds.EXPAND_DIR, nodeId, isExpanded)

class ClearPackages(ViewCommand):
    def __init__(self):
        ViewCommand.__init__(self, CommandIds.CLEAR_PACKAGES)

class SelectPackages(ViewCommand):
    '''nodeIds will be a list of node Ids to select'''
    def __init__(self, nodeIds):
        ViewCommand.__init__(self, CommandIds.SELECT_PACKAGES)
        self.nodeIds = nodeIds

class SelectFiles(ViewCommand):
    '''nodeIds will be a list of node Ids to select'''
    def __init__(self, nodeIds):
        ViewCommand.__init__(self, CommandIds.SELECT_FILES)
        self.nodeIds = nodeIds

class SetFilterStats(ViewCommand):
    def __init__(self, filterId, current, total):
        ViewCommand.__init__(self, CommandIds.SET_FILTER_STATS)
        self.filterId = filterId
        self.current = current
        self.total = total

class SetSummary(ViewCommand):
    def __init__(self, installedFiles, installedPlugins, bainMb, installedMb, freeMb):
        ViewCommand.__init__(self, CommandIds.SET_SUMMARY)
        self.installedFiles = installedFiles
        self.installedPlugins = installedPlugins
        self.bainMb = bainMb
        self.installedMb = installedMb
        self.freeMb = freeMb

class SetStatus(ViewCommand):
    def __init__(self, status, highlightColorId, loadingComplete=None,
                 loadingTotal=None, ioOperations=None):
        ViewCommand.__init__(self, CommandIds.SET_STATUS)
        self.status = status
        self.highlightColorId = highlightColorId
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
        _SetText.__init__(self, CommandIds.SET_PACKAGE_LABEL, text)

class AddFile(_AddNode):
    '''Adds a subpackage/file/directory node to the file tree'''
    def __init__(self, label, nodeId, parentNodeId, predecessorNodeId, style=None):
        _AddNode.__init__(self, CommandIds.ADD_FILE, label, nodeId, parentNodeId,
                          predecessorNodeId, style)

class ClearFiles(ViewCommand):
    def __init__(self):
        ViewCommand.__init__(self, CommandIds.CLEAR_FILES)

class SetFileDetails(_SetText):
    def __init__(self, text):
        _SetText.__init__(self, CommandIds.SET_FILE_DETAILS, text)

class SetStyleMaps(ViewCommand):
    '''Contains the map from style IDs to RGB tuples (for colors) and file resources
    (for images)'''
    def __init__(self, foregroundColorMap, highlightColorMap,
                 checkedIconMap, uncheckedIconMap):
        ViewCommand.__init__(self, CommandIds.SET_STYLE_MAPS)
        self.foregroundColorMap = foregroundColorMap
        self.highlightColorMap = highlightColorMap
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
        ViewCommand.__init__(self, CommandIds.SET_PACKAGE_INFO)
        self.tabId = tabId
        self.data = data

class DisplayError(ViewCommand):
    """Error codes instead of a message since we want to avoid localizable strings in
    the non-view layers"""
    def __init__(self, errorCode, resourceName):
        ViewCommand.__init__(self, CommandIds.DISPLAY_ERROR)
        self.errorCode = errorCode
        self.resourceName = resourceName

