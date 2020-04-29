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
#  Wrye Bash copyright (C) 2005-2009 Wrye, 2010-2020 Wrye Bash Team
#  https://github.com/wrye-bash
#
# =============================================================================

"""Requirement for further reading:
https://github.com/wrye-bash/wrye-bash/wiki/%5Bdev%5D-Fomod-for-Devs

This is a very simplistic backend installer for FOMOD. Ported from
GandaG/pyfomod.

Only entry point is FomodInstaller. Parsing of the xml tree is done via
Python's std lib and only as-needed (so that instancing this class isn't
too performance-heavy and the burden is divided between installer pages).

The only return values (other than exceptions) a user is expected to have
out of the FomodInstaller methods are the three wrapper classes:
InstallerPage, that wraps 'installStep'; InstallerGroup, that wraps 'group';
InstallerOption, that wraps 'plugin'. These allow for a more pythonic
interaction with the FOMOD tree - they mimic ElementTree elements such that
their children are available by iteration (subclassing Sequence) and useful
xml attributes/text are available via instance attributes."""

__author__ = u'Ganda'

from collections import OrderedDict, Sequence
from distutils.version import LooseVersion
from xml.etree import ElementTree as etree

from . import bush
from .bolt import GPath
from .load_order import cached_is_active

class FailedCondition(Exception):
    """Exception used to signal when a dependencies check is failed. Message
    passed to it should be human-readable and proper for a user to
    understand."""
    pass

class InstallerPage(Sequence):
    def __init__(self, parent_installer, page_object):
        """Wrapper around the ElementTree element 'installStep'.

        Provides the page's name via the `name` instance attribute
        and the page's groups via Sequence API (this behaves like a list).

        :param parent_installer: the parent FomodInstaller
        :param page_object: the ElementTree element for an 'installStep'"""
        self._parent_installer = parent_installer
        self.page_object = page_object # the original ElementTree element
        self._group_list = parent_installer.order_list([
            InstallerGroup(parent_installer, xml_group_obj)
            for xml_group_obj in page_object.findall(u'optionalFileGroups/*')
        ], page_object.get(u'order', u'Ascending'))
        self.name = page_object.get(u'name')

    def __getitem__(self, k):
        return self._group_list[k]

    def __len__(self):
        return len(self._group_list)

class InstallerGroup(Sequence):
    def __init__(self, parent_installer, group_object):
        """Wrapper around the ElementTree element 'group'.

        Provides the group's name and type via the `name` and `type` instance
        attributes, respectively, and the group's option via Sequence API
        (this behaves like a list).

        :param parent_installer: the parent FomodInstaller
        :param group_object: the ElementTree element for a 'group'"""
        self._parent_installer = parent_installer
        self.group_object = group_object
        self._option_list = parent_installer.order_list([
            InstallerOption(parent_installer, xml_option_object)
            for xml_option_object in group_object.findall(u'plugins/*')
        ], group_object.get(u'order', u'Ascending'))
        self.name = group_object.get(u'name')
        self.type = group_object.get(u'type')

    def __getitem__(self, k):
        return self._option_list[k]

    def __len__(self):
        return len(self._option_list)

class InstallerOption(object):
    def __init__(self, parent_installer, option_object):
        """Wrapper around the ElementTree element 'plugin'.

        Provides the option's name, description, image path and type
        via instance attributes with the same names.

        :param parent_installer: the parent FomodInstaller
        :param option_object: the ElementTree element for a 'plugin'"""
        self._parent_installer = parent_installer
        self.option_object = option_object
        self.name = option_object.get(u'name')
        self.description = option_object.findtext(u'description', u'').strip()
        xml_img_path = option_object.find(u'image')
        if xml_img_path is not None:
            self.option_image = xml_img_path.get(u'path')
        else:
            self.option_image = u''
        type_elem = option_object.find(u'typeDescriptor/type')
        if type_elem is not None:
            self.type = type_elem.get(u'name')
        else:
            default = option_object.find(
                u'typeDescriptor/dependencyType/defaultType').get(u'name')
            patterns = option_object.findall(
                u'typeDescriptor/dependencyType/patterns/*')
            for pattern in patterns:
                try:
                    self._parent_installer.test_conditions(pattern.find(
                        u'dependencies'))
                except FailedCondition:
                    pass
                else:
                    self.type = pattern.find(u'type').get(u'name')
                    break
            else:
                self.type = default

class _FomodFileInfo(object):
    def __init__(self, source, destination, priority):
        """Stores file info.

        :param source: string source path
        :param destination: string destination path
        :param priority: file priority"""
        self.source = source
        self.destination = destination
        self.priority = priority

    @classmethod
    def process_files(cls, files_elem, file_list):
        """Processes the elements in *files_elem* into a list of
        _FomodFileInfo.

        When parsing these elements there are a number of edge cases that must
        be taken into account, like a missing destination attribute having the
        same value as the source attribute or a 'file' element installing a
        folder.

        The returned list consists only of 'src file' -> 'dst file' mappings
        and never any folders to simplify installation later on (python has a
        hard time copying folders).

        :param files_elem: list of ElementTree elements 'file' and 'folder'
        :param file_list: list of files in the mod being installed"""
        result = []
        for file_object in files_elem.findall(u'*'):
            source = file_object.get(u'source')
            if source.endswith((u'/', u'\\')):
                source = source[:-1]
            source = GPath(source)
            destination = file_object.get(u'destination', None)
            if destination is None:  # omitted destination
                destination = source
            elif file_object.tag == u'file' and (
                not destination or destination.endswith((u'/', u'\\'))):
                # if empty or with a trailing slash then dest refers
                # to a folder. Post-processing to add the filename to the
                # end of the path.
                destination = GPath(destination).join(GPath(source).tail)
            else:
                # destination still needs normalizing
                destination = GPath(destination)
            priority = int(file_object.get(u'priority', u'0'))
            source_lower = source.s.lower()
            # We need to include the path separators when checking, since
            # otherwise we may end up matching e.g. 'Foo - A/bar.esp' to the
            # source 'Foo', when the source 'Foo - A' exists.
            source_starts = (source_lower + u'/', source_lower + u'\\')
            for fsrc in file_list:
                fsrc_lower = fsrc.lower()
                if fsrc_lower == source_lower:  # it's a file
                    result.append(cls(source, destination, priority))
                elif fsrc_lower.startswith(source_starts):
                    # it's a folder
                    source_len = len(source)
                    fdest = destination.s + fsrc[source_len:]
                    if fdest.startswith((u'/', u'\\')):
                        fdest = fdest[1:]
                    result.append(cls(GPath(fsrc), GPath(fdest), priority))
        return result

class FomodInstaller(object):
    def __init__(self, root, file_list, dst_dir, game_version):
        """Represents the installer itself. Keeps parsing on instancing to a
        minimum to reduce performance impact.

        To evaluate 'moduleDependencies' and receive the first page
        (InstallerPage), call `start()`. If you receive `None` it's because the
        installer had no visible pages and has finished.

        Once the user has performed their selections (a list of
        InstallerOption), you can pass these to `next_(selections)` to receive
        the next page. Keep in mind these selections are not validated at all -
        this must be done by the callers of this method. If you receive `None`
        it's because you have reached the end of the installer's pages.

        If the user desires to go to a previous page, you can call
        `previous()`. It will return a tuple of the previous InstallerPage and
        a list of the selected InstallerOptions on that page. If you receive
        `None` it's because you have reached the start of the installer.

        Once the installer has finished, you may call `files()` to receive a
        mapping of 'file source string' -> 'file destination string'. These are
        the files to be installed. This installer does not install or provide
        any way to do so, leaving that at your discretion.

        :param root: string path to 'ModuleConfig.xml'
        :param file_list: the list of recognized files of the mod being
            installed
        :param dst_dir: the destination directory - <Game>/Data
        :param game_version: version of the game launch exe"""
        self.tree = etree.parse(root)
        self.fomod_name = self.tree.findtext(u'moduleName', u'').strip()
        self.file_list = file_list
        self.dst_dir = dst_dir
        self.game_version = game_version
        self._current_page = None
        self._previous_pages = OrderedDict()
        self._has_finished = False

    def start(self):
        root_conditions = self.tree.find(u'moduleDependencies')
        if root_conditions is not None:
            self.test_conditions(root_conditions)
        first_page = self.tree.find(u'installSteps/installStep')
        if first_page is None:
            return None
        self._current_page = InstallerPage(self, first_page)
        return self._current_page

    def next_(self, selection):
        if self._has_finished or self._current_page is None:
            return None
        sort_list = [option for group in self._current_page for option
                     in group]
        sorted_selection = sorted(selection, key=sort_list.index)
        self._previous_pages[self._current_page] = sorted_selection
        ordered_pages = self.order_list(
            self.tree.findall(u'installSteps/installStep'),
            self.tree.find(u'installSteps').get(u'order', u'Ascending'))
        current_index = ordered_pages.index(self._current_page.page_object)
        for page in ordered_pages[current_index + 1:]:
            try:
                conditions = page.find(u'visible')
                if conditions is not None:
                    self.test_conditions(conditions)
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
        required_files_elem = self.tree.find(u'requiredInstallFiles')
        if required_files_elem is not None:
            required_files = _FomodFileInfo.process_files(
                required_files_elem, self.file_list)
        user_files = []
        selected_options = [option.option_object
                            for options in self._previous_pages.values()
                            for option in options]
        for option in selected_options:
            option_files = option.find(u'files')
            if option_files is not None:
                user_files.extend(_FomodFileInfo.process_files(
                    option_files, self.file_list))
        conditional_files = []
        for pattern in self.tree.findall(
                u'conditionalFileInstalls/patterns/pattern'):
            conditions = pattern.find(u'dependencies')
            files = pattern.find(u'files')
            try:
                self.test_conditions(conditions)
            except FailedCondition:
                pass
            else:
                conditional_files.extend(_FomodFileInfo.process_files(
                    files, self.file_list))
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
        """Returns a mapping of 'flag name' -> 'flag value'.
        Useful for either debugging or testing flag dependencies."""
        flag_dict = {}
        flags_list = [option.option_object.find(u'conditionFlags')
                      for options in self._previous_pages.values()
                      for option in options]
        for flags in flags_list:
            if flags is None:
                continue
            for flag in flags.findall(u'flag'):
                flag_name = flag.get(u'name')
                flag_value = flag.text
                flag_dict[flag_name] = flag_value
        return flag_dict

    def _test_file_condition(self, condition):
        file_name = GPath(condition.get(u'file'))
        file_type = condition.get(u'state')
        # Check if it's missing, ghosted or (in)active
        if not self.dst_dir.join(file_name).exists():
            actual_type = u'Missing'
        elif (file_name.cext in bush.game.espm_extensions and
              self.dst_dir.join(file_name + u'.ghost').exists()):
            actual_type = u'Inactive'
        else:
            actual_type = (u'Active' if cached_is_active(file_name)
                           else u'Inactive')
        if actual_type != file_type:
            raise FailedCondition(
                u'File {} should be {} but is {} instead.'.format(
                    file_name, file_type, actual_type))

    def _test_flag_condition(self, condition):
        flag_name = condition.get(u'flag')
        flag_value = condition.get(u'value')
        actual_value = self._flags().get(flag_name, None)
        if actual_value != flag_value:
            raise FailedCondition(
                u'Flag {} was expected to have {} but has {} instead.'.format(
                    flag_name, flag_value, actual_value))

    def _test_version_condition(self, condition):
        version = condition.get(u'version')
        game_version = LooseVersion(self.game_version)
        version = LooseVersion(version)
        if game_version < version:
            raise FailedCondition(
                u'Game version is {} but {} is required.'.format(
                    game_version, version))

    def test_conditions(self, conditions):
        op = conditions.get(u'operator', u'And')
        failed = []
        condition_list = conditions.findall(u'*')
        for condition in condition_list:
            try:
                test_func = self._condition_tests.get(condition.tag, None)
                if test_func:
                    test_func(self, condition)
            except FailedCondition as exc:
                failed.extend([a for a in str(exc).splitlines()])
                if op == u'And':
                    raise FailedCondition(u'\n'.join(failed))
        if op == u'Or' and len(failed) == len(condition_list):
            raise FailedCondition(u'\n'.join(failed))

    _condition_tests = {u'fileDependency': _test_file_condition,
                        u'flagDependency': _test_flag_condition,
                        u'gameDependency': _test_version_condition,
                        u'dependencies': test_conditions, }

    @staticmethod
    def order_list(unordered_list, order, _valid_values=frozenset(
        (u'Explicit', u'Ascending', u'Descending'))):
        if order == u'Explicit':
            return unordered_list
        if order not in _valid_values:
            raise ValueError(u'Arguments are incorrect: {}, {}'.format(
                unordered_list, order))
        return sorted(unordered_list, key=lambda x: x.name,
                      reverse=order == u'Descending')
