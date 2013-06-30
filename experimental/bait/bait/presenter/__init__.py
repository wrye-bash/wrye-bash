# -*- coding: utf-8 -*-
#
# bait/presenter/__init__.py
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
from ..model import node_attributes
from ..util import debug_utils, enum


class DetailsTabIds(enum.Enum):
    __enumerables__ = (
        'NONE', 'GENERAL', 'DIRTY', 'CONFLICTS', 'SELECTED', 'UNSELECTED', 'SKIPPED')
    # for autocomplete
    NONE = None
    GENERAL = None
    DIRTY = None
    CONFLICTS = None
    SELECTED = None
    UNSELECTED = None
    SKIPPED = None

class FilterIds(enum.FlagEnum):
    __enumerables__ = (
        'NONE',
        'PACKAGES_HIDDEN', 'PACKAGES_INSTALLED', 'PACKAGES_NOT_INSTALLED',
        'PACKAGES_ALWAYS_VISIBLE', 'FILES_PLUGINS', 'FILES_RESOURCES', 'FILES_OTHER',
        'DIRTY_ADD', 'DIRTY_UPDATE', 'DIRTY_DELETE',
        'CONFLICTS_SELECTED', 'CONFLICTS_UNSELECTED', 'CONFLICTS_ACTIVE',
        'CONFLICTS_INACTIVE', 'CONFLICTS_HIGHER', 'CONFLICTS_LOWER', 'CONFLICTS_MATCHED',
        'CONFLICTS_MISMATCHED', 'SELECTED_MATCHED', 'SELECTED_MISMATCHED',
        'SELECTED_HAS_CONFLICTS', 'SELECTED_NO_CONFLICTS', 'SELECTED_MISSING',
        'UNSELECTED_MATCHED', 'UNSELECTED_MISMATCHED', 'UNSELECTED_HAS_CONFLICTS',
        'UNSELECTED_NO_CONFLICTS', 'UNSELECTED_MISSING',
        'SKIPPED_NONGAME', 'SKIPPED_MASKED')
    # for autocomplete
    NONE = None
    PACKAGES_HIDDEN = None
    PACKAGES_INSTALLED = None
    PACKAGES_NOT_INSTALLED = None
    #PACKAGES_ALWAYS_VISIBLE = None # not intended to be used externally
    FILES_PLUGINS = None
    FILES_RESOURCES = None
    FILES_OTHER = None
    DIRTY_ADD = None
    DIRTY_UPDATE = None
    DIRTY_DELETE = None
    CONFLICTS_SELECTED = None
    CONFLICTS_UNSELECTED = None
    CONFLICTS_ACTIVE = None
    CONFLICTS_INACTIVE = None
    CONFLICTS_HIGHER = None
    CONFLICTS_LOWER = None
    CONFLICTS_MATCHED = None
    CONFLICTS_MISMATCHED = None
    SELECTED_MATCHED = None
    SELECTED_MISMATCHED = None
    SELECTED_MISSING = None
    SELECTED_HAS_CONFLICTS = None
    SELECTED_NO_CONFLICTS = None
    UNSELECTED_MATCHED = None
    UNSELECTED_MISMATCHED = None
    UNSELECTED_MISSING = None
    UNSELECTED_HAS_CONFLICTS = None
    UNSELECTED_NO_CONFLICTS = None
    SKIPPED_NONGAME = None
    SKIPPED_MASKED = None

class CommandIds(enum.Enum):
    __enumerables__ = ('UNKNOWN', 'SET_GLOBAL_SETTINGS', 'SET_PACKAGE_CONTENTS_INFO',
                       'SET_STATUS_OK', 'SET_STATUS_DIRTY', 'SET_STATUS_LOADING',
                       'SET_STATUS_IO', 'SET_STYLE_MAPS', 'UPDATE_NODE', 'ADD_NODE',
                       'MOVE_NODE', 'REMOVE_NODE', 'CLEAR_TREE', 'SET_FILTER_STATS',
                       'SET_GENERAL_TAB_INFO', 'SET_DIRTY_TAB_INFO',
                       'SET_CONFLICTS_TAB_INFO', 'SET_FILE_LIST_TAB_INFO',
                       'DISPLAY_ERROR', 'ASK_CONFIRMATION', 'EXTENDED')
    # for autocomplete
    SET_GLOBAL_SETTINGS = None
    SET_PACKAGE_CONTENTS_INFO = None
    SET_STATUS_OK = None
    SET_STATUS_DIRTY = None
    SET_STATUS_LOADING = None
    SET_STATUS_IO = None
    SET_STYLE_MAPS = None
    UPDATE_NODE = None
    ADD_NODE = None
    MOVE_NODE = None
    REMOVE_NODE = None
    CLEAR_TREE = None
    SET_FILTER_STATS = None
    SET_GENERAL_TAB_INFO = None
    SET_DIRTY_TAB_INFO = None
    SET_CONFLICTS_TAB_INFO = None
    SET_FILE_LIST_TAB_INFO = None
    DISPLAY_ERROR = None
    ASK_CONFIRMATION = None
    EXTENDED = None

class _ViewCommand(debug_utils.Dumpable):
    '''The commandId indicates the subclass type'''
    def __init__(self, commandId):
        self.commandId = commandId

class _SetSettingsCommand(_ViewCommand):
    '''Base class for settings-related commands'''
    def __init__(self, commandId, skipDistantLod, skipLodMeshes,
                 skipLodTextures, skipLodNormals, skipVoices):
        _ViewCommand.__init__(self, commandId)
        self.skipDistantLod = skipDistantLod
        self.skipLodMeshes = skipLodMeshes
        self.skipLodTextures = skipLodTextures
        self.skipLodNormals = skipLodNormals
        self.skipVoices = skipVoices

class SetGlobalSettingsCommand(_SetSettingsCommand):
    '''A value of None indicates that the setting has not changed'''
    def __init__(self, rememberTreeExpansionState=None, skipDistantLod=None,
                 skipLodMeshes=None, skipLodTextures=None, skipLodNormals=None,
                 skipVoices=None):
        _SetSettingsCommand.__init__(self, CommandIds.SET_GLOBAL_SETTINGS, skipDistantLod,
                 skipLodMeshes, skipLodTextures, skipLodNormals, skipVoices)
        self.rememberTreeExpansionState = rememberTreeExpansionState

class SetPackageContentsInfoCommand(_SetSettingsCommand):
    '''Sets the title for the package contents pane as well as the settings in the package
       contents settings menu.  For the title, None means no package is selected and a
       blank string means multiple packages are selected.  For the settings, None means
       "defer to default".  The enabled parameter controls whether the entire package
       contents pane is enabled or disabled.'''
    def __init__(self, title, enabled, skipDistantLod=None, skipLodMeshes=None,
                 skipLodTextures=None, skipLodNormals=None, skipVoices=None):
        _SetSettingsCommand.__init__(self, CommandIds.SET_PACKAGE_CONTENTS_INFO, skipDistantLod,
                 skipLodMeshes, skipLodTextures, skipLodNormals, skipVoices)
        self.title = title
        self.enabled = enabled

class SetStatusOkCommand(_ViewCommand):
    '''Sets the status panel to the "OK" state and populates statistics'''
    def __init__(self, numInstalledFiles, installedMb, freeInstalledMb,
                 numLibraryFiles, libraryMb, freeLibraryMb):
        _ViewCommand.__init__(self, CommandIds.SET_STATUS_OK)
        self.numInstalledFiles = numInstalledFiles
        self.installedMb = installedMb
        self.freeInstalledMb = freeInstalledMb
        self.numLibraryFiles = numLibraryFiles
        self.libraryMb = libraryMb
        self.freeLibraryMb = freeLibraryMb

class SetStatusDirtyCommand(_ViewCommand):
    '''Sets the status panel to the "dirty" state and shows dirty package names'''
    def __init__(self, dirtyPackageNodeIds):
        _ViewCommand.__init__(self, CommandIds.SET_STATUS_DIRTY)
        self.dirtyPackageNodeIds = dirtyPackageNodeIds

class SetStatusLoadingCommand(_ViewCommand):
    '''Sets the status panel to the "loading" state and shows progress'''
    def __init__(self, progressComplete, progressTotal):
        _ViewCommand.__init__(self, CommandIds.SET_STATUS_LOADING)
        self.progressComplete = progressComplete
        self.progressTotal = progressTotal

class PackageOperationIds(enum.Enum):
    __enumerables__ = (
        'UNKNOWN', 'INSTALL', 'UNINSTALL', 'ANNEAL', 'RENAME', 'DELETE', 'COPY')
    # for autocomplete
    INSTALL = None
    UNINSTALL = None
    ANNEAL = None
    RENAME = None
    DELETE = None
    COPY = None

class PackageOperationInfo(debug_utils.Dumpable):
    def __init__(self, packageOperationId, target):
        self.packageOperationId = packageOperationId
        self.packageNodeId = packageNodeId

class SetStatusIOCommand(_ViewCommand):
    '''Sets the status panel to the "I/O" state and shows pending operations'''
    def __init__(self, packageOperationInfos):
        _ViewCommand.__init__(self, CommandIds.SET_STATUS_IO)
        self.packageOperationInfos = packageOperationInfos

class FontStyleIds(enum.FlagEnum):
    __enumerables__ = ('NONE', 'NORMAL', 'BOLD', 'ITALICS')
    # for autocomplete
    NORMAL = None
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

class SetStyleMapsCommand(_ViewCommand):
    '''Contains the maps from styleIds to RGB tuples (for colors) and from iconIds to file
       resources (for images)'''
    def __init__(self, foregroundColorMap, highlightColorMap,
                 checkedIconMap, uncheckedIconMap):
        _ViewCommand.__init__(self, CommandIds.SET_STYLE_MAPS)
        self.foregroundColorMap = foregroundColorMap
        self.highlightColorMap = highlightColorMap
        self.checkedIconMap = checkedIconMap
        self.uncheckedIconMap = uncheckedIconMap

class Style(debug_utils.Dumpable):
    def __init__(self, fontStyleMask=FontStyleIds.NORMAL, foregroundColorId=None,
                 highlightColorId=None, checkboxState=None, iconId=None):
        self.fontStyleMask = fontStyleMask
        self.foregroundColorId = foregroundColorId
        self.highlightColorId = highlightColorId
        self.checkboxState = checkboxState
        self.iconId = iconId
    def __eq__(self, other):
        return other is not None and\
               self.fontStyleMask == other.fontStyleMask and \
               self.foregroundColorId == other.foregroundColorId and \
               self.highlightColorId == other.highlightColorId and \
               self.checkboxState == other.checkboxState and \
               self.iconId == other.iconId
    def __ne__(self, other):
        return not self.__eq__(other)

class NodeTreeIds(enum.Enum):
    __enumerables__ = ('UNKNOWN', 'PACKAGES', 'CONTENTS')
    # for autocomplete
    PACKAGES = None
    CONTENTS = None

class _ModifyNodeCommand(_ViewCommand):
    '''Base class for UpdateNode and AddNode'''
    def __init__(self, commandId, nodeTreeId, nodeId, label, isExpanded, style):
        _ViewCommand.__init__(self, commandId)
        self.nodeId = nodeId
        self.label = label
        self.isExpanded = isExpanded
        self.style = style
        self.nodeTreeId = nodeTreeId

class UpdateNodeCommand(_ModifyNodeCommand):
    '''Updates a node already in a tree.  An attribute value of None means that the value
       is unchanged.'''
    def __init__(self, nodeTreeId, nodeId, label=None, isExpanded=None, style=None):
        _ModifyNodeCommand.__init__(
            self, CommandIds.UPDATE_NODE, nodeTreeId, nodeId, label, isExpanded, style)

class ContextMenuIds(node_attributes.ContextMenuIds):
    pass

class AddNodeCommand(_ModifyNodeCommand):
    '''Adds a node to a tree.  The parent node will either have been previously sent or
       will be None, meaning top-level.  The predecessor node will either have been
       previously sent or be None, meaning "first child of parent"'''
    def __init__(self, nodeTreeId, nodeId, label, isExpanded, style, parentNodeId,
                 predecessorNodeId, contextMenuId, isSelected=False):
        _ModifyNodeCommand.__init__(
            self, CommandIds.ADD_NODE, nodeTreeId, nodeId, label, isExpanded, style)
        self.parentNodeId = parentNodeId
        self.predecessorNodeId = predecessorNodeId
        self.contextMenuId = contextMenuId
        self.isSelected = isSelected

class MoveNodeCommand(_ViewCommand):
    '''Reorders a tree leaf or branch among its siblings.  The new predecessor node will
       either have been previously sent or be None, meaning "first child of parent".
       Selection status of any moved nodes should be maintained.'''
    def __init__(self, nodeTreeId, nodeId, predecessorNodeId):
        _ViewCommand.__init__(self, CommandIds.MOVE_NODE)
        self.nodeTreeId = nodeTreeId
        self.nodeId = nodeId
        self.predecessorNodeId = predecessorNodeId

class RemoveNodeCommand(_ViewCommand):
    '''Removes a node from a tree'''
    def __init__(self, nodeTreeId, nodeId):
        _ViewCommand.__init__(self, CommandIds.REMOVE_NODE)
        self.nodeTreeId = nodeTreeId
        self.nodeId = nodeId

class ClearTreeCommand(_ViewCommand):
    def __init__(self, nodeTreeId):
        _ViewCommand.__init__(self, CommandIds.CLEAR_TREE)
        self.nodeTreeId = nodeTreeId

class SetFilterStatsCommand(_ViewCommand):
    def __init__(self, filterId, current, total):
        _ViewCommand.__init__(self, CommandIds.SET_FILTER_STATS)
        self.filterId = filterId
        self.current = current
        self.total = total

class SetGeneralTabInfoCommand(_ViewCommand):
    '''Sets the data for the package contents General tab'''
    def __init__(self, isArchive=None, isHidden=None, isInstalled=None, packageBytes=0,
                 selectedBytes=0, lastModifiedTimestamp="", numFiles=0, numDirty=0,
                 numOverridden=0, numSkipped=0, numSelectedMatched=0,
                 numSelectedMismatched=0, numSelectedOverridden=0, numSelectedMissing=0,
                 numTotalSelected=0, numUnselectedMatched=0, numUnselectedMismatched=0,
                 numUnselectedOverridden=0, numUnselectedMissing=0,
                 numTotalUnselected=0, numTotalMatched=0, numTotalMismatched=0,
                 numTotalOverridden=0, numTotalMissing=0, numTotalSelectable=0,
                 imageFileHandle=None):
        _ViewCommand.__init__(self, CommandIds.SET_GENERAL_TAB_INFO)
        self.isArchive = isArchive
        self.isHidden = isHidden
        self.isInstalled = isInstalled
        self.packageBytes = packageBytes
        self.selectedBytes = selectedBytes
        self.lastModifiedTimestamp = lastModifiedTimestamp
        self.numFiles = numFiles
        self.numDirty = numDirty
        self.numOverridden = numOverridden
        self.numSkipped = numSkipped
        self.numSelectedMatched = numSelectedMatched
        self.numSelectedMismatched = numSelectedMismatched
        self.numSelectedOverridden = numSelectedOverridden
        self.numSelectedMissing = numSelectedMissing
        self.numTotalSelected = numTotalSelected
        self.numUnselectedMatched = numUnselectedMatched
        self.numUnselectedMismatched = numUnselectedMismatched
        self.numUnselectedOverridden = numUnselectedOverridden
        self.numUnselectedMissing = numUnselectedMissing
        self.numTotalUnselected = numTotalUnselected
        self.numTotalMatched = numTotalMatched
        self.numTotalMismatched = numTotalMismatched
        self.numTotalOverridden = numTotalOverridden
        self.numTotalMissing = numTotalMissing
        self.numTotalSelectable = numTotalSelectable
        self.imageFileHandle = imageFileHandle

class AnnealOperationIds(model.AnnealOperationIds):
    pass

class SetDirtyTabInfoCommand(_ViewCommand):
    '''Sets the data for the package contents Dirty tab.  annealOperations is a list of
       tuples of the form (annealOperationId, path)'''
    def __init__(self, annealOperations):
        _ViewCommand.__init__(self, CommandIds.SET_DIRTY_TAB_INFO)
        self.annealOperations = annealOperations

class SetConflictsTabInfoCommand(_ViewCommand):
    '''Sets the data for the package contents Conflicts tab.  conflictLists is a list of
       tuples of the form (conflictingPackageNodeId, [list of conflicting paths])'''
    def __init__(self, conflictLists):
        _ViewCommand.__init__(self, CommandIds.SET_CONFLICTS_TAB_INFO)
        self.conflictLists = conflictLists

class SetFileListTabInfoCommand(_ViewCommand):
    '''Sets the data for a package contents tab that displays a list of file paths'''
    def __init__(self, detailsTabId, paths):
        _ViewCommand.__init__(self, CommandIds.SET_FILE_LIST_TAB_INFO)
        self.detailsTabId = detailsTabId
        self.paths = paths

class ErrorCodes(model.Errors):
    pass

class DisplayErrorCommand(_ViewCommand):
    '''Error codes instead of a message since we want to avoid localizable strings in
       the non-view layers'''
    def __init__(self, errorCode, resourceName):
        _ViewCommand.__init__(self, CommandIds.DISPLAY_ERROR)
        self.errorCode = errorCode
        self.resourceName = resourceName

class ConfirmationQuestionIds(enum.Enum):
    __enumerables__ = ('UNKNOWN', 'INSTALL_OBSE_PLUGIN', 'DELETE')
    # for autocomplete
    INSTALL_OBSE_PLUGIN = None
    DELETE = None

class AskConfirmationCommand(_ViewCommand):
    '''Display a confirmation dialog'''
    def __init__(self, confirmationQuestionId, resourceName):
        _ViewCommand.__init__(self, CommandIds.ASK_CONFIRMATION)
        self.confirmationQuestionId = confirmationQuestionId
        self.resourceName = resourceName

class ExtendedCommand(_ViewCommand):
    '''Extend this class to implement non-presenter ViewCommands that the View should
       interpret'''
    def __init__(self):
        _ViewCommand.__init__(self, CommandIds.EXTENDED)
