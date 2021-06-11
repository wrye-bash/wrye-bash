# -*- coding: utf-8 -*-
#
# GPL License and Copyright Notice ============================================
#  This file is part of Wrye Bash.
#
#  Wrye Bash is free software: you can redistribute it and/or
#  modify it under the terms of the GNU General Public License
#  as published by the Free Software Foundation, either version 3
#  of the License, or (at your option) any later version.
#
#  Wrye Bash is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
#
#  You should have received a copy of the GNU General Public License
#  along with Wrye Bash.  If not, see <https://www.gnu.org/licenses/>.
#
#  Wrye Bash copyright (C) 2005-2009 Wrye, 2010-2021 Wrye Bash Team
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

from collections import OrderedDict
from distutils.version import LooseVersion
from xml.etree import ElementTree as etree

from . import bush
from .bolt import GPath, Path
from .load_order import cached_is_active

class FailedCondition(Exception):
    """Exception used to signal when a dependencies check is failed. Message
    passed to it should be human-readable and proper for a user to
    understand."""
    pass

class _AFomodBase(object):
    """Base class for FOMOD components. Defines a key to sort instances of this
    class by."""
    __slots__ = (u'_parent_installer', u'sort_key')

    def __init__(self, parent_installer, sort_key):
        """Creates a new _AFomodBase with the specified parent and sort key.

        :param parent_installer: The parent FomodInstaller.
        :param sort_key: An object to use for sorting instances of this
            class."""
        self._parent_installer = parent_installer
        self.sort_key = sort_key

class InstallerPage(_AFomodBase):
    """Wrapper around the ElementTree element 'installStep'. Provides the
    page's name via the `page_name` instance attribute and the page's groups
    via list emulation."""
    __slots__ = (u'page_name', u'page_object', u'_group_list')

    def __init__(self, parent_installer, page_object):
        """Creates a new InstallerPage with the specified parent and XML
        object.

        :param parent_installer: The parent FomodInstaller.
        :param page_object: The ElementTree element for an 'installStep'."""
        self.page_name = page_object.get(u'name')
        super(InstallerPage, self).__init__(parent_installer, self.page_name)
        self.page_object = page_object # the original ElementTree element
        self._group_list = parent_installer.order_list(
            [InstallerGroup(parent_installer, xml_group_obj) for xml_group_obj
                in page_object.findall(u'optionalFileGroups/*')],
            page_object.find(u'optionalFileGroups').get(u'order',
                u'Ascending'))

    def __getitem__(self, k):
        return self._group_list[k]

    def __len__(self):
        return len(self._group_list)

class InstallerGroup(_AFomodBase):
    """Wrapper around the ElementTree element 'group'. Provides the group's
    name and type via the `group_name` and `group_type` instance attributes,
    respectively, and the group's options via list emulation."""
    __slots__ = (u'group_name', u'group_object', u'_option_list',
                 u'group_type')

    def __init__(self, parent_installer, group_object):
        """Creates a new InstallerGroup with the specified parent and XML
        object.

        :param parent_installer: The parent FomodInstaller.
        :param group_object: The ElementTree element for a 'group'."""
        self.group_name = group_object.get(u'name')
        super(InstallerGroup, self).__init__(parent_installer, self.group_name)
        self.group_object = group_object
        self._option_list = parent_installer.order_list([
            InstallerOption(parent_installer, xml_option_object)
            for xml_option_object in group_object.findall(u'plugins/*')],
            group_object.find(u'plugins').get(u'order', u'Ascending'))
        self.group_type = group_object.get(u'type')

    def __getitem__(self, k):
        return self._option_list[k]

    def __len__(self):
        return len(self._option_list)

class InstallerOption(_AFomodBase):
    """Wrapper around the ElementTree element 'plugin'. Provides the option's
    name, description, image path and type via the instance attributes
    option_name, option_desc, option_image and option_type respectively."""
    __slots__ = (u'option_name', u'option_object', u'option_desc',
                 u'option_image', u'option_type')

    def __init__(self, parent_installer, option_object):
        """Creates a new InstallerOption with the specified parent and XML
        object.

        :param parent_installer: The parent FomodInstaller.
        :param option_object: The ElementTree element for a 'plugin'."""
        self.option_name = option_object.get(u'name')
        super(InstallerOption, self).__init__(parent_installer,
                                              self.option_name)
        self.option_object = option_object
        self.option_desc = option_object.findtext(u'description', u'').strip()
        xml_img_path = option_object.find(u'image')
        if xml_img_path is not None:
            self.option_image = xml_img_path.get(u'path')
        else:
            self.option_image = u''
        type_elem = option_object.find(u'typeDescriptor/type')
        if type_elem is not None:
            self.option_type = type_elem.get(u'name')
        else:
            default_type = option_object.find(
                u'typeDescriptor/dependencyType/defaultType').get(u'name')
            dep_patterns = option_object.findall(
                u'typeDescriptor/dependencyType/patterns/*')
            for dep_pattern in dep_patterns:
                try:
                    self._parent_installer.test_conditions(dep_pattern.find(
                        u'dependencies'))
                except FailedCondition:
                    pass
                else:
                    self.option_type = dep_pattern.find(u'type').get(u'name')
                    break
            else:
                self.option_type = default_type

class _FomodFileInfo(object):
    """Stores information about a single file that is going to be installed."""
    __slots__ = (u'file_source', u'file_destination', u'file_priority')

    def __init__(self, file_source, file_destination, file_priority):
        # type: (Path, Path, int) -> None
        """Creates a new _FomodFileInfo with the specified properties.

        :param file_source: The source path.
        :param file_destination: The destination path.
        :param file_priority: The relative file priority."""
        self.file_source = file_source
        self.file_destination = file_destination
        self.file_priority = file_priority

    def __repr__(self):
        return u'%s<%s -> %s with priority %s>' % (
            self.__class__.__name__, self.file_source, self.file_destination,
            self.file_priority)

    @classmethod
    def process_files(cls, files_elem, file_list, inst_root):
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
        :param file_list: list of files in the mod being installed
        :param inst_root: The root path to retrieve sources relative to."""
        fm_infos = []
        md_lower = bush.game.mods_dir.lower()
        md_lower_slash = tuple(md_lower + s for s in (u'/', u'\\'))
        md_lower_strip = len(md_lower) + 1 # for the (back)slash
        for file_object in files_elem.findall(u'*'):
            file_src = inst_root + file_object.get(u'source')
            if file_src.endswith((u'/', u'\\')):
                file_src = file_src[:-1]
            file_src = GPath(file_src)
            file_dest = file_object.get(u'destination', None)
            if file_dest is None: # omitted destination
                file_dest = file_src
            elif file_object.tag == u'file' and (
                not file_dest or file_dest.endswith((u'/', u'\\'))):
                # if empty or with a trailing slash then dest refers
                # to a folder. Post-processing to add the filename to the
                # end of the path.
                file_dest = GPath(file_dest).join(file_src.tail)
            else:
                # destination still needs normalizing
                file_dest = GPath(file_dest)
            # Be forgiving of FOMODs that specify redundant 'Data' folders in
            # the destination
            file_dest_s = file_dest.s
            dest_lower = file_dest_s.lower()
            if dest_lower == md_lower:
                file_dest_s = u''
            else:
                while dest_lower.startswith(md_lower_slash):
                    file_dest_s = file_dest_s[md_lower_strip:]
                    dest_lower = file_dest_s.lower()
            if file_dest_s != file_dest.s:
                file_dest = GPath(file_dest_s)
            file_prty = int(file_object.get(u'priority', u'0'))
            source_lower = file_src.s.lower()
            # We need to include the path separators when checking, since
            # otherwise we may end up matching e.g. 'Foo - A/bar.esp' to the
            # source 'Foo', when the source 'Foo - A' exists.
            source_starts = (source_lower + u'/', source_lower + u'\\')
            for fsrc in file_list:
                fsrc_lower = fsrc.lower()
                if fsrc_lower == source_lower: # it's a file
                    fm_infos.append(cls(file_src, file_dest, file_prty))
                elif fsrc_lower.startswith(source_starts): # it's a folder
                    fdest = file_dest.s + fsrc[len(file_src):]
                    if fdest.startswith((u'/', u'\\')):
                        fdest = fdest[1:]
                    fm_infos.append(cls(GPath(fsrc), GPath(fdest), file_prty))
        return fm_infos

class FomodInstaller(object):
    """Represents the installer itself. Keeps parsing on instancing to a
    minimum to reduce performance impact.

    To evaluate 'moduleDependencies' and receive the first page
    (InstallerPage), call `start_fomod()`. If you receive `None` it's because
    the installer had no visible pages and has finished.

    Once the user has performed their selections (a list of
    InstallerOption), you can pass these to `move_to_next(selections)` to
    receive the next page. Keep in mind these selections are not validated at
    all - this must be done by the callers of this method. If you receive
    `None` it's because you have reached the end of the installer's pages.

    If the user desires to go to a previous page, you can call
    `move_to_prev()`. It will return a tuple of the previous InstallerPage
    and a list of the selected InstallerOptions on that page. If you receive
    `(None, None)` it's because you have reached the start of the installer.

    Once the installer has finished, you may call `get_fomod_files()` to
    receive a mapping of 'file source string' -> 'file destination string'.
    These are the files to be installed. This installer does not install or
    provide any way to do so, leaving that at your discretion."""
    __slots__ = (u'fomod_tree', u'fomod_name', u'file_list', u'dst_dir',
                 u'game_version', u'_current_page', u'_previous_pages',
                 u'_has_finished', u'installer_root')

    def __init__(self, mc_path, file_list, inst_root, dst_dir, game_version):
        """Creates a new FomodInstaller with the specified properties.

        :param mc_path: string path to 'ModuleConfig.xml'
        :param file_list: the list of recognized files of the mod being
            installed
        :param inst_root: The root path of the installer. All files are
            specified relative to this by the FOMOD config.
        :param dst_dir: the destination directory - <Game>/Data
        :param game_version: version of the game launch exe"""
        self.fomod_tree = etree.parse(mc_path)
        self.fomod_name = self.fomod_tree.findtext(u'moduleName', u'').strip()
        self.file_list = file_list
        self.installer_root = inst_root
        self.dst_dir = dst_dir
        self.game_version = game_version
        self._current_page = None
        self._previous_pages = OrderedDict()
        self._has_finished = False

    def check_start_conditions(self):
        """Checks if the FOMOD installer can be started in the first place."""
        root_conditions = self.fomod_tree.find(u'moduleDependencies')
        if root_conditions is not None:
            self.test_conditions(root_conditions)

    def has_next(self):
        """Returns True if the parser has not yet finished."""
        return not self._has_finished

    def move_to_next(self, user_selection):
        if self._has_finished:
            return None
        if user_selection is not None:
            # Store the choices made on the current page for later retrieval
            all_options = (option for grp in self._current_page
                           for option in grp)
            sort_map = {o: i for i, o in enumerate(all_options)}
            sorted_selection = sorted(user_selection, key=sort_map.__getitem__)
            self._previous_pages[self._current_page] = sorted_selection
        install_steps = self.fomod_tree.find(u'installSteps')
        if install_steps is not None:
            # Order the pages by name - note that almost all ModuleConfigs in
            # the wild use 'Explicit' ordering here (for obvious reasons, you
            # generally want the installation steps to be in a fixed order)
            ordered_pages = self.order_list(
                self.fomod_tree.findall(u'installSteps/installStep'),
                install_steps.get(u'order', u'Ascending'),
                ol_key_f=lambda e: e.get(u'name'))
        else:
            ordered_pages = [] # no installSteps -> no pages
        if self._current_page is not None:
            # We already have a page, use the index of the current one
            current_index = ordered_pages.index(self._current_page.page_object)
        else:
            # We're at the start of the wizard, consider the first page too
            current_index = -1
        for next_page in ordered_pages[current_index + 1:]:
            try:
                # We have a page, but need to check if it's actually visible
                page_conditions = next_page.find(u'visible')
                if page_conditions is not None:
                    self.test_conditions(page_conditions)
            except FailedCondition:
                continue
            else:
                # We have a visible page, wrap it and return that
                self._current_page = InstallerPage(self, next_page)
                return self._current_page
        else:
            # We have no visible pages, finish the entire wizard
            self._has_finished = True
            self._current_page = None
            return None

    def has_prev(self):
        """Returns True if the parser has a previous InstallerPage that can be
        moved to."""
        return bool(self._previous_pages)

    def move_to_prev(self):
        self._has_finished = False
        prev_page, prev_selected = self._previous_pages.popitem(last=True)
        self._current_page = prev_page
        return prev_page, prev_selected

    def get_fomod_files(self):
        required_files = []
        required_files_elem = self.fomod_tree.find(u'requiredInstallFiles')
        if required_files_elem is not None:
            required_files = _FomodFileInfo.process_files(
                required_files_elem, self.file_list, self.installer_root)
        user_files = []
        selected_options = [option.option_object
                            for options in self._previous_pages.values()
                            for option in options]
        for option in selected_options:
            option_files = option.find(u'files')
            if option_files is not None:
                user_files.extend(_FomodFileInfo.process_files(
                    option_files, self.file_list, self.installer_root))
        conditional_files = []
        for cond_pattern in self.fomod_tree.findall(
                u'conditionalFileInstalls/patterns/pattern'):
            dep_conditions = cond_pattern.find(u'dependencies')
            cond_files = cond_pattern.find(u'files')
            try:
                self.test_conditions(dep_conditions)
            except FailedCondition:
                pass
            else:
                conditional_files.extend(_FomodFileInfo.process_files(
                    cond_files, self.file_list, self.installer_root))
        file_dict = {}  # dst -> src
        priority_dict = {}  # dst -> priority
        for fm_info in required_files + user_files + conditional_files:
            fm_info_dest = fm_info.file_destination
            if fm_info_dest in priority_dict:
                if priority_dict[fm_info_dest] > fm_info.file_priority:
                    continue
                del file_dict[fm_info_dest]
            file_dict[fm_info_dest] = fm_info.file_source
            priority_dict[fm_info_dest] = fm_info.file_priority
        # return everything in strings
        return {a.s: b.s for a, b in file_dict.items()}

    def _fomod_flags(self):
        """Returns a mapping of 'flag name' -> 'flag value'.
        Useful for either debugging or testing flag dependencies."""
        fm_flag_dict = {}
        fm_flags_list = [option.option_object.find(u'conditionFlags')
                         for options in self._previous_pages.values()
                         for option in options]
        for fm_flags in fm_flags_list:
            if fm_flags is None:
                continue
            for fm_flag in fm_flags.findall(u'flag'):
                fm_flag_name = fm_flag.get(u'name')
                fm_flag_value = fm_flag.text
                fm_flag_dict[fm_flag_name] = fm_flag_value
        return fm_flag_dict

    def _test_file_condition(self, condition):
        test_file = GPath(condition.get(u'file'))
        test_type = condition.get(u'state')
        # Check if it's missing, ghosted or (in)active
        if not self.dst_dir.join(test_file).exists():
            actual_type = u'Missing'
        ##: Needed? Shouldn't this be handled by cached_is_active?
        elif (test_file.cext in bush.game.espm_extensions and
              self.dst_dir.join(test_file + u'.ghost').exists()):
            actual_type = u'Inactive'
        else:
            actual_type = (u'Active' if cached_is_active(test_file)
                           else u'Inactive')
        if actual_type != test_type:
            raise FailedCondition(
                u'File {} should be {} but is {} instead.'.format(
                    test_file, test_type, actual_type))

    def _test_flag_condition(self, condition):
        fm_flag_name = condition.get(u'flag')
        fm_flag_value = condition.get(u'value', u'')
        actual_flag_value = self._fomod_flags().get(fm_flag_name, u'')
        if actual_flag_value != fm_flag_value:
            raise FailedCondition(
                u'Flag {} was expected to have {} but has {} instead.'.format(
                    fm_flag_name, fm_flag_value, actual_flag_value))

    def _test_version_condition(self, condition):
        target_ver = condition.get(u'version')
        game_ver = LooseVersion(self.game_version)
        target_ver = LooseVersion(target_ver)
        if game_ver < target_ver:
            raise FailedCondition(
                u'Game version is {} but {} is required.'.format(
                    game_ver, target_ver))

    def test_conditions(self, fomod_conditions):
        cond_op = fomod_conditions.get(u'operator', u'And')
        failed_conditions = []
        all_conditions = fomod_conditions.findall(u'*')
        for condition in all_conditions:
            try:
                test_func = self._condition_tests.get(condition.tag, None)
                if test_func:
                    test_func(self, condition)
            except FailedCondition as e:
                failed_conditions.extend([a for a in str(e).splitlines()])
                if cond_op == u'And':
                    raise FailedCondition(u'\n'.join(failed_conditions))
        if cond_op == u'Or' and len(failed_conditions) == len(all_conditions):
            raise FailedCondition(u'\n'.join(failed_conditions))

    _condition_tests = {u'fileDependency': _test_file_condition,
                        u'flagDependency': _test_flag_condition,
                        u'gameDependency': _test_version_condition,
                        u'dependencies': test_conditions, }

    # Valid values for 'order' attributes
    _valid_values = {u'Explicit', u'Ascending', u'Descending'}

    @classmethod
    def order_list(cls, unordered_list, order_str,
                   ol_key_f=lambda x: x.sort_key):
        if order_str == u'Explicit':
            return unordered_list
        if order_str not in cls._valid_values:
            raise ValueError(u'Unknown order type %s - expected one of [%s]'
                             % (order_str, u', '.join(cls._valid_values)))
        return sorted(unordered_list, key=ol_key_f,
                      reverse=order_str == u'Descending')
