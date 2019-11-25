# -*- coding: utf-8 -*-
#
# GPL License and Copyright Notice ============================================
#  This file is part of Wrye Bash.
#
#  Wrye Bash is free software; you can redistribute it and/or
#  modify it under the terms of the GNU General Public License
#  as published by the Free Software Foundation; either version 2
#  of the License, or (at your option) any later version.
#
#  Wrye Bash is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
#
#  You should have received a copy of the GNU General Public License
#  along with Wrye Bash; if not, write to the Free Software Foundation,
#  Inc., 59 Temple Place - Suite 330, Boston, MA  02111-1307, USA.
#
#  Wrye Bash copyright (C) 2005-2009 Wrye, 2010-2019 Wrye Bash Team
#  https://github.com/wrye-bash
#
# =============================================================================

"""
Requirement for further reading: https://github.com/wrye-bash/wrye-bash/wiki/%5Bdev%5D-Fomod-for-Devs

This is a very simplistic backend installer for FOMOD. Ported from GandaG/pyfomod

Only entry point is FomodInstaller. Parsing of the xml tree is done via
Python's std lib and only as-needed (so that instancing this class isn't
too performance-heavy and the burden is divided between installer pages)

The only return values (other than exceptions) a user is expected to have
out of the FomodInstaller methods are the three wrapper classes:
InstallerPage, that wraps 'installStep'; InstallerGroup, that wraps 'group';
InstallerOption, that wraps 'plugin'. These allow for a more pythonic
interaction with the FOMOD tree - they mimic ElementTree elements such that
their children are available by iteration (subclassing Sequence) and useful
xml attributes/text are available via instance attributes.
"""

import os
from collections import OrderedDict, Sequence
from distutils.version import LooseVersion
from xml.etree import ElementTree as etree

from .bolt import Path
from .load_order import cached_is_active

__author__ = "Ganda"

class FailedCondition(Exception):
    """
    Exception used to signal when a dependencies check is failed.
    Message passed to it should be human-readable and proper for
    a user to understand.
    """
    pass


class InstallerPage(Sequence):
    def __init__(self, installer, page):
        """
        Wrapper around the ElementTree element 'installStep'.

        Provides the page's name via the `name` instance attribute
        and the page's groups via Sequence API (this behaves like a list)

        :param installer: the parent FomodInstaller
        :param page: the ElementTree element for an 'installStep'
        """
        self._installer = installer
        self._object = page  # the original ElementTree element
        self._group_list = installer._order_list(
            [
                InstallerGroup(installer, group)
                for group in page.findall("optionalFileGroups/*")
            ],
            page.get("order", "Ascending"),
        )
        self.name = page.get("name")

    def __getitem__(self, key):
        return self._group_list[key]

    def __len__(self):
        return len(self._group_list)


class InstallerGroup(Sequence):
    def __init__(self, installer, group):
        """
        Wrapper around the ElementTree element 'group'.

        Provides the group's name and type via the `name` and `type` instance
        attributes, respectively, and the group's option via Sequence API
        (this behaves like a list)

        :param installer: the parent FomodInstaller
        :param group: the ElementTree element for an 'group'
        """
        self._installer = installer
        self._object = group
        self._option_list = installer._order_list(
            [
                InstallerOption(installer, option)
                for option in group.findall("plugins/*")
            ],
            group.get("order", "Ascending"),
        )
        self.name = group.get("name")
        self.type = group.get("type")

    def __getitem__(self, key):
        return self._option_list[key]

    def __len__(self):
        return len(self._option_list)


class InstallerOption(object):
    def __init__(self, installer, option):
        """
        Wrapper around the ElementTree element 'plugin'.

        Provides the option's name, description, image path and type
        via instance attributes with the same names.

        :param installer: the parent FomodInstaller
        :param option: the ElementTree element for an 'plugin'
        """
        self._installer = installer
        self._object = option
        self.name = option.get("name")
        self.description = option.findtext("description", "").strip()
        image = option.find("image")
        if image is not None:
            self.image = image.get("path")
        else:
            self.image = ""
        type_elem = option.find("typeDescriptor/type")
        if type_elem is not None:
            self.type = type_elem.get("name")
        else:
            default = option.find("typeDescriptor/dependencyType/defaultType").get(
                "name"
            )
            patterns = option.findall("typeDescriptor/dependencyType/patterns/*")
            for pattern in patterns:
                try:
                    self._installer._test_conditions(pattern.find("dependencies"))
                except FailedCondition:
                    pass
                else:
                    self.type = pattern.find("type").get("name")
                    break
            else:
                self.type = default


class _FomodFileInfo(object):
    def __init__(self, source, destination, priority):
        """
        Stores file info.

        :param source: string source path
        :param destination: string destination path
        :param priority: file priority
        """
        self.source = source
        self.destination = destination
        self.priority = priority

    @classmethod
    def process_files(cls, files_elem, file_list):
        """
        Processes the elements in *files_elem* into a list of _FomodFileInfo.

        When parsing these elements there are a number of edge cases that must
        be taken into account, like a missing destination attribute having the
        same value as the source attribute or a 'file' element installing a
        folder.

        The returned list consists only of "src file" -> "dst file" mappings
        and never any folders to simplify installationlater on (python has a
        hard time copying folders)

        :param files_elem: list of ElementTree elements 'file' and 'folder'
        :param file_list: list of files in the mod being installed
        """
        result = []
        for file_object in files_elem.findall("*"):
            source = file_object.get("source")
            if source.endswith(("/", "\\")):
                source = source[:-1]
            source = Path(source)
            destination = file_object.get("destination", None)
            if destination is None:  # omitted destination
                destination = source
            elif file_object.tag == "file" and (
                not destination or destination.endswith(("/", "\\"))
            ):
                # if empty or with a trailing slash then dest refers
                # to a folder. Post-processing to add the filename to the
                # end of the path.
                destination = Path(destination).join(Path(source).tail)
            else:
                # destination still needs normalizing
                destination = Path(destination)
            priority = int(file_object.get("priority", "0"))
            for fname in file_list:
                if fname.lower() == source.s.lower():  # it's a file
                    result.append(cls(source, destination, priority))
                elif fname.lower().startswith(source.s.lower()):  # it's a folder
                    source_len = len(source)
                    fdest = destination.s + fname[source_len:]
                    if fdest.startswith(os.sep):
                        fdest = fdest[1:]
                    result.append(cls(Path(fname), Path(fdest), priority))
        return result


class FomodInstaller(object):
    def __init__(self, root, file_list, dst_dir, game_version):
        """
        Represents the installer itself. Keeps parsing on instancing to a
        minimum to reduce performance impact.

        To evaluate 'moduleDependencies' and receive the first page (InstallerPage),
        call `start()`. If you receive `None` it's because the installer had no visible
        pages and has finished.

        Once the user has performed their selections (a list of InstallerOption), you can
        pass these to `next_(selections)` to receive the next page. Keep in mind these
        selections are not validated at all - this must be done by the callers of this method.
        If you receive `None` it's because you have reached the end of the installer's pages.

        If the user desires to go to a previous page, you can call `previous()`. It will return
        a tuple of the previous InstallerPage and a list of the selected InstallerOption on that
        page. If you receive `None` it's because you have reached the start of the installer.

        Once the installer has finished, you may call `files()` to receive a mapping of
        "file source string" -> "file destination string". These are the files to be installed.
        This installer does not install or provide any way to do so, leaving that at your discretion.

        :param root: string path to "ModuleConfig.xml"
        :param file_list: the list of recognized files of the mod being installed
        :param dst_dir: the destination directory - <Game>/Data
        :param game_version: version of the game launch exe
        """
        self.tree = etree.parse(root)
        self.fomod_name = self.tree.findtext("moduleName", "").strip()
        self.file_list = file_list
        self.dst_dir = dst_dir
        self.game_version = game_version
        self._current_page = None
        self._previous_pages = OrderedDict()
        self._has_finished = False

    def start(self):
        root_conditions = self.tree.find("moduleDependencies")
        if root_conditions is not None:
            self._test_conditions(root_conditions)
        first_page = self.tree.find("installSteps/installStep")
        if first_page is None:
            return None
        self._current_page = InstallerPage(self, first_page)
        return self._current_page

    def next_(self, selection):
        if self._has_finished or self._current_page is None:
            return None
        sort_list = [option for group in self._current_page for option in group]
        sorted_selection = sorted(selection, key=sort_list.index)
        self._previous_pages[self._current_page] = sorted_selection
        ordered_pages = self._order_list(
            self.tree.findall("installSteps/installStep"),
            self.tree.find("installSteps").get("order", "Ascending"),
        )
        current_index = ordered_pages.index(self._current_page._object)
        for page in ordered_pages[current_index + 1 :]:
            try:
                conditions = page.find("visible")
                if conditions is not None:
                    self._test_conditions(conditions)
            except FailedCondition:
                pass
            else:
                self._current_page = InstallerPage(self, page)
                return self._current_page
        else:
            self._has_finished = True
            self._current_page = None
        return None

    def previous(self):
        self._has_finished = False
        try:
            page, options = self._previous_pages.popitem(last=True)
            self._current_page = page
            return page, options
        except KeyError:
            self._current_page = None
            return None

    def has_previous(self):
        return bool(self._previous_pages)

    def files(self):
        required_files = []
        required_files_elem = self.tree.find("requiredInstallFiles")
        if required_files_elem is not None:
            required_files = _FomodFileInfo.process_files(required_files_elem, self.file_list)
        user_files = []
        selected_options = [
            option._object for options in self._previous_pages.values() for option in options
        ]
        for option in selected_options:
            option_files = option.find("files")
            if option_files is not None:
                user_files.extend(_FomodFileInfo.process_files(option_files, self.file_list))
        conditional_files = []
        for pattern in self.tree.findall("conditionalFileInstalls/patterns/pattern"):
            conditions = pattern.find("dependencies")
            files = pattern.find("files")
            try:
                self._test_conditions(conditions)
            except FailedCondition:
                pass
            else:
                conditional_files.extend(_FomodFileInfo.process_files(files, self.file_list))
        file_dict = {}  # dst -> src
        priority_dict = {}  # dst -> priority
        for info in required_files + user_files + conditional_files:
            if info.destination in priority_dict:
                if priority_dict[info.destination] > info.priority:
                    continue
                del file_dict[info.destination]
            file_dict[info.destination] = info.source
            priority_dict[info.destination] = info.priority
        # return everything in strings
        return {a.s: b.s for a, b in file_dict.iteritems()}

    def _flags(self):
        """
        Returns a mapping of "flag name" -> "flag value".
        Useful for either debugging or testing flag dependencies.
        """
        flag_dict = {}
        flags_list = [
            option._object.find("conditionFlags")
            for options in self._previous_pages.values()
            for option in options
        ]
        for flags in flags_list:
            if flags is None:
                continue
            for flag in flags.findall("flag"):
                flag_name = flag.get("name")
                flag_value = flag.text
                flag_dict[flag_name] = flag_value
        return flag_dict

    def _test_file_condition(self, condition):
        file_name = condition.get("file")
        file_type = condition.get("state")
        file_path = self.dst_dir.join(file_name)
        if not file_path.exists(): # TODO: ghosts?
            actual_type = "Missing"
        else:
            actual_type = "Active" if cached_is_active(file_name) else "Inactive"
        if actual_type != file_type:
            raise FailedCondition(
                "File {} should be {} but is {} instead.".format(
                    file_name, file_type, actual_type
                )
            )

    def _test_flag_condition(self, condition):
        flag_name = condition.get("flag")
        flag_value = condition.get("value")
        actual_value = self._flags().get(flag_name, None)
        if actual_value != flag_value:
            raise FailedCondition(
                "Flag {} was expected to have {} but has {} instead.".format(
                    flag_name, flag_value, actual_value
                )
            )

    def _test_version_condition(self, condition):
        version = condition.get("version")
        game_version = LooseVersion(self.game_version)
        version = LooseVersion(version)
        if game_version < version:
            raise FailedCondition(
                "Game version is {} but {} is required.".format(
                    game_version, version)
            )

    def _test_conditions(self, conditions):
        op = conditions.get("operator", "And")
        failed = []
        condition_list = conditions.findall("*")
        for condition in condition_list:
            try:
                test_func = self._condition_tests.get(condition.tag, None)
                if test_func:
                    test_func(self, condition)
            except FailedCondition as exc:
                failed.extend([a for a in str(exc).splitlines()])
                if op == "And":
                    raise FailedCondition("\n".join(failed))
        if op == "Or" and len(failed) == len(condition_list):
            raise FailedCondition("\n".join(failed))

    _condition_tests = {"fileDependency": _test_file_condition,
                        "flagDependency": _test_flag_condition,
                        "gameDependency": _test_version_condition,
                        "dependencies": _test_conditions, }

    @staticmethod
    def _order_list(unordered_list, order, _valid_values=frozenset(
        ("Explicit", "Ascending", "Descending"))):
        if order == "Explicit":
            return unordered_list
        if order not in _valid_values:
            raise ValueError(
                "Arguments are incorrect: {}, {}".format(unordered_list, order)
            )
        return sorted(unordered_list, key=lambda x: x.name,
                      reverse=order == "Descending")
