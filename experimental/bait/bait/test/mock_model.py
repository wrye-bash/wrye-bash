# -*- coding: utf-8 -*-
#
# bait/test/mock_model.py
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
import copy
import datetime
import itertools
import logging
import random
import threading
import time

from .. import model
from ..model import node_attributes, node_children, node_details
from ..util import monitored_thread


_logger = logging.getLogger(__name__)

_ATTRIBUTES_IDX = 0
_CHILDREN_IDX = 1
_DETAILS_IDX = 2

_maxTime = int(time.time())
_minTime = int(0.9 * _maxTime)


def _generate_group_node(label, parentId, childrenList):
    return [node_attributes.GroupNodeAttributes(
                label, parentId, node_attributes.ContextMenuIds.GROUP),
            node_children.NodeChildren(childrenList),
            None]


def _generate_package_node(parentId, attributeMap):
    label = "attributes:"
    attribute = None
    for attribute in attributeMap:
        label += " " + attribute

    if "isArchive" in attributeMap:
        contextMenuId = node_attributes.ContextMenuIds.ARCHIVE
    else:
        contextMenuId = node_attributes.ContextMenuIds.PROJECT
    attributes = node_attributes.PackageNodeAttributes(
        label, parentId, contextMenuId, **attributeMap)
    del parentId
    del attributeMap
    del label
    del attribute
    del contextMenuId

    # generate believable-looking details given a set of attributes
    isArchive = attributes.isArchive
    isHidden = attributes.isHidden
    isInstalled = attributes.isInstalled
    lastModifiedTimestamp = str(
        datetime.datetime.fromtimestamp(random.randint(_minTime, _maxTime)))

    numSelectedMatched = random.randint(1, 100) if attributes.hasMatched else 0
    numSelectedMismatched = random.randint(1, 10) if attributes.hasMismatched else 0
    numSelectedOverridden = random.randint(1, 10) if attributes.isDirty else 0
    numSelectedMissing = random.randint(1, 100) if attributes.hasMissing else 0
    numTotalSelected = numSelectedMatched + numSelectedMismatched + \
                     numSelectedOverridden + numSelectedMissing
    numUnselectedMatched = random.randint(1, 100) if attributes.hasMatched else 0
    numUnselectedMismatched = random.randint(1, 10) if attributes.hasMismatched else 0
    numUnselectedOverridden = random.randint(0, 10)
    numUnselectedMissing = random.randint(1, 100) if attributes.hasMissing else 0
    numTotalUnselected = numUnselectedMatched + numUnselectedMismatched + \
                     numUnselectedOverridden + numUnselectedMissing
    numTotalMatched = numSelectedMatched + numUnselectedMatched
    numTotalMismatched = numSelectedMismatched + numUnselectedMismatched
    numTotalOverridden = numSelectedOverridden + numUnselectedOverridden
    numTotalMissing = numSelectedMissing + numUnselectedMissing
    numTotalSelectable = numTotalSelected + numTotalUnselected

    numOverridden = numSelectedOverridden
    numSkipped = random.randint(1, 10)
    numFiles = numTotalSelectable + numSkipped
    numDirty = random.randint(1, numFiles) if attributes.isDirty else 0

    packageBytes = random.randint(numFiles*1024, numFiles*16*1024)
    selectedBytes = random.randint(
        numTotalSelected*1024, packageBytes-numTotalUnselected*1024) \
                  if numTotalSelected > 0 else 0
    imageFileHandle = None

    detailsKwArgs = dict(locals())
    del detailsKwArgs["attributes"]

    return [attributes, None, node_details.PackageNodeDetails(**detailsKwArgs)]


def _generate_moving_packages(data, parentId, movingChildren):
    nextId = parentId + 1
    attributeLists = [
        ["alwaysVisible", "hasMatched"],
        ["isInstalled", "hasMissingDeps", "isArchive", "hasWizard"],
        ["isNotInstalled", "isDirty", "hasMismatched"],
        ["isHidden",  "isArchive", "updateAvailable", "hasSubpackages"]]
    for idx in xrange(4):
        attributeMap = {key:True for key in attributeLists[idx]}
        data[nextId] = _generate_package_node(parentId, attributeMap)
        movingChildren.append(nextId)
        nextId += 1
    return nextId

def _generate_blinking_packages(data, parentId, blinkingChildren):
    nextId = parentId + 1
    for idx in xrange(10):
        data[nextId] = _generate_package_node(parentId, {"isArchive":False})
        blinkingChildren.append(nextId)
        nextId += 1
    return nextId

def _expand_list(oneEachOf):
    retlist = [[]]
    for one in oneEachOf:
        newretlist = []
        for expansion in _expand_choices(one):
            for oldlist in retlist:
                newlist = list(oldlist)
                newlist.extend(expansion)
                newretlist.append(newlist)
        retlist = newretlist
    return retlist

def _expand_set(allCombinationsOf):
    retlist = []
    skipZero = True
    if None in allCombinationsOf:
        allCombinationsOf = set(allCombinationsOf)
        allCombinationsOf.discard(None)
        skipZero = False
    for numChoices in xrange(len(allCombinationsOf)+1):
        if numChoices == 0 and skipZero:
            continue
        for choices in itertools.combinations(allCombinationsOf, numChoices):
            retlist.extend(_expand_choices(list(choices)))
    return retlist

def _expand_tuple(oneOf):
    retlist = []
    for one in oneOf:
        retlist.extend(_expand_choices(one))
    return retlist

# returns list of lists of strings.
def _expand_choices(choices):
    if type(choices) == set:
        return _expand_set(choices)
    elif type(choices) == list:
        return _expand_list(choices)
    elif type(choices) == tuple:
        return _expand_tuple(choices)
    else:
        return [[choices]]

def _generate_packages_expected_attributes(data, parentId, parentChildren):
    nextId = parentId + 1
    usedSets = set()
    # tuples indicate "one of"
    # sets indicate "all combinations of"
    # lists indicate "one each of"
    choices = (
        # used for virtual "installed data" package
        ["alwaysVisible", "isInstalled",
         ("hasMatched",
          ["hasMatched", "isDirty", "hasMismatched"],
          ["isDirty", "hasMismatched"]),
         set((None, "hasMissingDeps"))],
        # must have an attribute related to a file that should be installed
        ["isInstalled",
         ("hasMatched", ["isDirty", set(("hasMismatched", "hasMissing", "hasMatched"))]),
         set((None, "isArchive", "hasWizard", "updateAvailable", "hasSubpackages",
              "hasMissingDeps"))],
        # can have a wider variety of attributes, including corruption
        ["isNotInstalled",
         set((None, "updateAvailable", "isArchive")),
         (set((None, "isNew", "isDirty", "hasMissingDeps", "hasWizard", "hasMatched",
               "hasMismatched", "hasMissing", "hasSubpackages")),
          ("isUnrecognized", "isCorrupt"))],
        ["isHidden",
         set((None, "updateAvailable", "isArchive")),
         ("isUnrecognized", "isCorrupt",
          set((None, "hasMissingDeps", "hasWizard", "hasMatched", "hasMismatched",
               "hasMissing", "hasSubpackages")))])
    for choice in choices:
        groupChildren = []
        data[nextId] = _generate_group_node("%s Group"%choice[0], parentId, groupChildren)
        parentChildren.append(nextId)
        groupId = nextId
        nextId += 1
        for trueList in _expand_choices(choice):
            attributeMap = {key:True for key in trueList}
            data[nextId] = _generate_package_node(groupId, attributeMap)
            groupChildren.append(nextId)
            usedSets.add(frozenset(trueList))
            nextId += 1
    return nextId, usedSets

def _generate_packages_unexpected_attributes(data, parentId, parentChildren, skipSets):
    nextId = parentId + 1
    attributes = [
        "isDirty", "isInstalled", "isNotInstalled", "isHidden", "isNew", "hasMissingDeps",
        "isUnrecognized", "isCorrupt", "updateAvailable", "alwaysVisible", "isArchive",
        "hasWizard", "hasMatched", "hasMismatched", "hasMissing", "hasSubpackages"]
    for numTrue in xrange(len(attributes)+1):
        groupChildren = []
        data[nextId] = _generate_group_node("%d attribute(s)"%numTrue,
                                            parentId, groupChildren)
        parentChildren.append(nextId)
        groupId = nextId
        nextId += 1
        for trueList in itertools.combinations(attributes, numTrue):
            if frozenset(trueList) in skipSets:
                continue
            attributeMap = {key:True for key in trueList}
            data[nextId] = _generate_package_node(groupId, attributeMap)
            groupChildren.append(nextId)
            nextId += 1
    return nextId


class MockModel:
    def __init__(self):
        self.updateNotificationQueue = Queue.Queue()
        self._updateLock = threading.Lock()
        self._threads = []
        self._shutdown = False
        self._data = {}

        # root node
        self._threads.append(monitored_thread.MonitoredThread(
            target=self._status_run, name="ModelStatus"))
        rootChildren = []
        self._data[model.ROOT_NODE_ID] = [
            node_attributes.RootNodeAttributes(
                node_attributes.StatusLoadingData(0, 100)),
            node_children.NodeChildren(rootChildren),
            None]

        # reset trigger
        self._data[1] = _generate_group_node("ResetGroup", model.ROOT_NODE_ID, [2])
        rootChildren.append(1)
        self._data[2] = [
            node_attributes.PackageNodeAttributes(
                "Edit comments to reset package list", 1,
                node_attributes.ContextMenuIds.PROJECT, alwaysVisible=True),
            None,
            node_details.PackageNodeDetails()]

        nextId = 3

        # group with moving packages
        self._threads.append(monitored_thread.MonitoredThread(
            target=self._moving_run, name="ModelMover", args=(nextId,)))
        movingChildren = []
        self._data[nextId] = _generate_group_node(
            "Packages that change relative priority", model.ROOT_NODE_ID, movingChildren)
        rootChildren.append(nextId)
        nextId = _generate_moving_packages(self._data, nextId, movingChildren)

        # group with packages that change their attributes periodically
        self._threads.append(monitored_thread.MonitoredThread(
            target=self._blinking_run, name="ModelBlinker", args=(nextId,)))
        blinkingChildren = []
        self._data[nextId] = _generate_group_node(
            "Packages that change attributes", model.ROOT_NODE_ID, blinkingChildren)
        rootChildren.append(nextId)
        nextId = _generate_blinking_packages(self._data, nextId, blinkingChildren)

        # packages with valid, expected attribute combinations
        expectedAttributesChildren = []
        self._data[nextId] = _generate_group_node(
            "Packages with expected attribute combinations", model.ROOT_NODE_ID,
            expectedAttributesChildren)
        rootChildren.append(nextId)
        nextId, attributeCombinations = _generate_packages_expected_attributes(
            self._data, nextId, expectedAttributesChildren)

        # packages with all other attribute combinations
        unexpectedAttributesChildren = []
        self._data[nextId] = _generate_group_node(
            "Packages with unexpected attribute combinations", model.ROOT_NODE_ID,
            unexpectedAttributesChildren)
        rootChildren.append(nextId)
        nextId = _generate_packages_unexpected_attributes(
            self._data, nextId, unexpectedAttributesChildren, attributeCombinations)
        del attributeCombinations

        self._packageNodeIds = set(xrange(nextId))
        self._numPackages = nextId - 1


    def start(self):
        _logger.debug("mock model starting")
        for thread in self._threads:
            thread.setDaemon(True)
            thread.start()

    def pause(self):
        _logger.debug("mock model pausing")

    def resume(self):
        _logger.debug("mock model resuming")

    def shutdown(self):
        _logger.debug("mock model shutting down")
        with self._updateLock:
            self._shutdown = True
            self.updateNotificationQueue.put(None)

    def get_node_attributes(self, nodeId):
        self._packageNodeIds.discard(nodeId)
        return self._get_node_element(nodeId, "attributes", _ATTRIBUTES_IDX)

    def get_node_children(self, nodeId):
        return self._get_node_element(nodeId, "children", _CHILDREN_IDX)

    def get_node_details(self, nodeId):
        return self._get_node_element(nodeId, "details", _DETAILS_IDX)

    def _get_node_element(self, nodeId, elementName, elementIdx):
        if nodeId in self._data:
            _logger.debug("retrieving %s for node %d", elementName, nodeId)
            return self._data[nodeId][elementIdx]
        _logger.debug("no %s to retrieve for node %d", elementName, nodeId)
        return None

    def _status_run(self):
        rootNode = self._data[model.ROOT_NODE_ID]
        total = self._numPackages
        cur = 0
        iterations = 0
        while cur < total:
            time.sleep(1)
            iterations += 1
            cur = total - len(self._packageNodeIds)
            _logger.debug("updating status: %d/%d", cur, total)
            rootNode[_ATTRIBUTES_IDX] = node_attributes.RootNodeAttributes(
                node_attributes.StatusLoadingData(cur, total),
                version=cur)
            with self._updateLock:
                if self._shutdown: return
                self.updateNotificationQueue.put((model.UpdateTypes.ATTRIBUTES,
                                                  model.NodeTypes.ROOT,
                                                  model.ROOT_NODE_ID, cur))
        statsLogger = logging.getLogger("STATISTICS")
        _logger.info("loaded %d packages in %d seconds", total, iterations)
        statsLogger.info("loaded %d packages in %d seconds", total, iterations)
        rootNode[_ATTRIBUTES_IDX] = node_attributes.RootNodeAttributes(
            node_attributes.StatusOkData(12345, 3123, 250000, 123000, 22000, 250000),
            version=cur+1)
        with self._updateLock:
            if self._shutdown: return
            self.updateNotificationQueue.put((model.UpdateTypes.ATTRIBUTES,
                                              model.NodeTypes.ROOT,
                                              model.ROOT_NODE_ID, cur+1))

    def _moving_run(self, movingGroupNodeId):
        groupNode = self._data[movingGroupNodeId]
        while True:
            time.sleep(1)
            _logger.debug("updating moving group")
            prevGroupNodeChildren = groupNode[_CHILDREN_IDX]
            childList = list(prevGroupNodeChildren.children)
            random.shuffle(childList)
            version = prevGroupNodeChildren.version + 1
            groupNode[_CHILDREN_IDX] = node_children.NodeChildren(childList,
                                                                  version=version)
            with self._updateLock:
                if self._shutdown: return
                self.updateNotificationQueue.put((model.UpdateTypes.CHILDREN,
                                                  model.NodeTypes.GROUP,
                                                  movingGroupNodeId, version))

    def _blinking_run(self, blinkingGroupNodeId):
        groupNode = self._data[blinkingGroupNodeId]
        childNodeIds = groupNode[_CHILDREN_IDX].children
        while True:
            time.sleep(10)
            _logger.debug("updating blinking group")
            for childNodeId in childNodeIds:
                childNode = self._data[childNodeId]
                prevChildAttributes = childNode[_ATTRIBUTES_IDX]
                version = prevChildAttributes.version + 1
                # copy the attributes from some other random node
                randomAttributes = random.choice(self._data)[_ATTRIBUTES_IDX]
                while randomAttributes.nodeType != model.NodeTypes.PACKAGE:
                    randomAttributes = random.choice(self._data)[_ATTRIBUTES_IDX]
                childAttributes = copy.copy(randomAttributes)
                childAttributes.parentNodeId = blinkingGroupNodeId
                childAttributes.version=version
                childNode[_ATTRIBUTES_IDX] = childAttributes
                with self._updateLock:
                    if self._shutdown: return
                    self.updateNotificationQueue.put((model.UpdateTypes.ATTRIBUTES,
                                                      model.NodeTypes.PACKAGE,
                                                      childNodeId, version))
