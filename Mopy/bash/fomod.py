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
#  Wrye Bash copyright (C) 2005-2009 Wrye, 2010-2023 Wrye Bash Team
#  https://github.com/wrye-bash
#
# =============================================================================

"""Requirement for further reading:
https://github.com/wrye-bash/wrye-bash/wiki/%5Bdev%5D-Fomod-for-Devs

This is WB's backend implementation for FOMOD. Originally ported from
GandaG/pyfomod, it has seen significant refactoring and extension since then
and now implements pretty much the entire FOMOD format.

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

import functools
from enum import Enum

from . import bass, bosh, bush, env # for modInfos
from .bolt import FName, GPath, LooseVersion, Path, gen_enum_parser
from .exception import XMLParsingError
from .fomod_schema import schema_string
from .load_order import cached_is_active

try:
    # lxml is optional, but without it we can't validate schemata
    from lxml import etree
    _can_validate = True
except ImportError:
    from xml.etree import ElementTree as etree
    _can_validate = False

class FailedCondition(Exception):
    """Exception used to signal when a dependencies check is failed. Message
    passed to it should be human-readable and proper for a user to
    understand."""

class FileState(Enum):
    """The various states that a file can have. Implements the XML simpleType
    'state'."""
    MISSING = 'Missing'
    INACTIVE = 'Inactive'
    ACTIVE = 'Active'

_fs_parser = gen_enum_parser(FileState)

class GroupType(Enum):
    """The various types that a group can have. Implements the XML simpleType
    'type'."""
    SELECT_AT_LEAST_ONE = 'SelectAtLeastOne'
    SELECT_AT_MOST_ONE = 'SelectAtMostOne'
    SELECT_EXACTLY_ONE = 'SelectExactlyOne'
    SELECT_ALL = 'SelectAll'
    SELECT_ANY = 'SelectAny'

_gt_parser = gen_enum_parser(GroupType)

class OptionType(Enum):
    """The various types that an option can have. Implements the XML enum
    'pluginType'."""
    REQUIRED = 'Required'
    OPTIONAL = 'Optional'
    RECOMMENDED = 'Recommended'
    NOT_USABLE = 'NotUsable'
    COULD_BE_USABLE = 'CouldBeUsable'

_ot_parser = gen_enum_parser(OptionType)

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

@functools.cache
def _parsed_schema():
    return etree.fromstring(schema_string)

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

    def __repr__(self):
        return f'InstallerPage<{self.page_name}, {len(self)} group(s)>'

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
        self.group_type = _gt_parser[group_object.get('type')]

    def __getitem__(self, k):
        return self._option_list[k]

    def __len__(self):
        return len(self._option_list)

    def __repr__(self):
        return f'InstallerGroup<{self.group_name}, {len(self)} option(s)>'

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
            opt_type_str = type_elem.get('name')
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
                    opt_type_str = dep_pattern.find('type').get('name')
                    break
            else:
                opt_type_str = default_type
        self.option_type = _ot_parser[opt_type_str]

    def __repr__(self):
        return f'InstallerOption<{self.option_name}>'

class _FomodFileInfo(object):
    """Stores information about a single file that is going to be installed."""
    __slots__ = (u'file_source', u'file_destination', u'file_priority')

    def __init__(self, file_source: Path, file_destination: Path,
                 file_priority: int) -> None:
        """Creates a new _FomodFileInfo with the specified properties.

        :param file_source: The source path.
        :param file_destination: The destination path.
        :param file_priority: The relative file priority."""
        self.file_source = file_source
        self.file_destination = file_destination
        self.file_priority = file_priority

    def __repr__(self):
        return f'{self.__class__.__name__}<{self.file_source} -> ' \
               f'{self.file_destination} with priority {self.file_priority}>'

    @classmethod
    def process_files(cls, files_elem, file_list, inst_root, is_usable):
        """Processes the elements in files_elem into two lists of
        _FomodFileInfo instances. The first one contains the regular, processed
        files, the second contains processed files that *must* be installed due
        to having alwaysInstall or a valid installIfUsable attribute.

        When parsing these elements there are a number of edge cases that must
        be taken into account, like a missing destination attribute having the
        same value as the source attribute or a 'file' element installing a
        folder.

        The returned list consists only of 'src file' -> 'dst file' mappings
        and never any folders to simplify installation later on (python has a
        hard time copying folders).

        :param files_elem: An ElementTree element housing the 'file' and
            'folder' elements we want to install
        :param file_list: A list of all files in the parent package.
        :param inst_root: The root path to retrieve sources relative to.
        :param is_usable: True if the type of the option/plugin that this file
            list belongs to is anything but NotUsable."""
        fm_infos_con = []
        fm_infos_req = []
        md_lower = bush.game.mods_dir.lower()
        md_lower_slash = tuple(md_lower + s for s in (u'/', u'\\'))
        md_lower_strip = len(md_lower) + 1 # for the (back)slash
        for file_object in files_elem.findall(u'*'):
            file_src = inst_root + file_object.get(u'source')
            if file_src.endswith((u'/', u'\\')):
                file_src = file_src[:-1] ##: Doesn't GPath already do this?
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
            # Check the fileSystemItem attributes alwaysInstall and
            # installIfUsable, which may make arbitrary files required
            if file_object.get('alwaysInstall', 'false') in ('true', '1'):
                fm_infos_target = fm_infos_req
            elif (file_object.get('installIfUsable', 'false') in ('true', '1')
                  and is_usable):
                fm_infos_target = fm_infos_req
            else:
                fm_infos_target = fm_infos_con
            for fsrc in file_list:
                fsrc_lower = fsrc.lower()
                if fsrc_lower == source_lower: # it's a file
                    fm_infos_target.append(cls(file_src, file_dest, file_prty))
                elif fsrc_lower.startswith(source_starts): # it's a folder
                    fdest = file_dest.s + fsrc[len(file_src):]
                    if fdest.startswith((u'/', u'\\')):
                        fdest = fdest[1:]
                    fm_infos_target.append(cls(GPath(fsrc), GPath(fdest),
                                           file_prty))
        return fm_infos_con, fm_infos_req

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
    __slots__ = ('fomod_tree', 'fomod_name', 'file_list', 'dst_dir',
                 'game_version', '_current_page', '_all_pages',
                 '_previous_pages', '_has_finished', 'installer_root')

    def __init__(self, mc_path, file_list, inst_root, dst_dir, game_version):
        """Creates a new FomodInstaller with the specified properties.

        :param mc_path: string path to 'ModuleConfig.xml'
        :param file_list: the list of recognized files of the mod being
            installed
        :param inst_root: The root path of the installer. All files are
            specified relative to this by the FOMOD config.
        :param dst_dir: the destination directory - <Game>/Data
        :param game_version: version of the game launch exe"""
        try:
            self.fomod_tree = etree.parse(mc_path)
        except etree.ParseError as e:
            # Wrap ParseErrors so that GUI code can catch and handle them
            raise XMLParsingError(str(e)) from e
        self.fomod_name = self.fomod_tree.findtext(u'moduleName', u'').strip()
        self.file_list = file_list
        self.installer_root = inst_root
        self.dst_dir = dst_dir
        self.game_version = game_version
        self._current_page = None
        self._all_pages: dict[int, InstallerPage] = {}
        self._previous_pages: dict[InstallerPage, list[InstallerOption]] = {}
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
            current_index = ordered_pages.index(
                self._current_page.page_object) + 1
        else:
            # We're at the start of the wizard, consider the first page too
            current_index = 0
        for next_page in ordered_pages[current_index:]:
            try:
                # We have a page, but need to check if it's actually visible
                page_conditions = next_page.find(u'visible')
                if page_conditions is not None:
                    self.test_conditions(page_conditions)
            except FailedCondition:
                # The page is not visible, but we still have to construct it to
                # check for alwaysInstall and installIfUsable
                self._all_pages[current_index] = InstallerPage(self, next_page)
            else:
                # We have a visible page, wrap it and return that
                self._current_page = InstallerPage(self, next_page)
                self._all_pages[current_index] = self._current_page
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
        prev_page, prev_selected = self._previous_pages.popitem()
        self._current_page = prev_page
        return prev_page, prev_selected

    def get_fomod_files(self):
        collected_files = []
        required_files_elem = self.fomod_tree.find(u'requiredInstallFiles')
        if required_files_elem is not None:
            # No need to worry about the con/req split here - we're in the
            # requiredInstallFiles section, so all files are required
            con_files, req_files = _FomodFileInfo.process_files(
                required_files_elem, self.file_list, self.installer_root,
                is_usable=True)
            collected_files.extend(con_files)
            collected_files.extend(req_files)
        for pre_page in self._all_pages.values():
            # All options that were available on this page
            all_options = [option for grp in pre_page for option in grp]
            # Set of only the option objects that the user actually selected.
            # If the page was not shown, then this will be empty and so we will
            # only install the alwaysInstall/installIfUsable options
            selected_options = set(self._previous_pages.get(pre_page, []))
            for option in all_options:
                option_files = option.option_object.find('files')
                if option_files is not None:
                    # Here we have to worry about the con/req split
                    op_usable = option.option_type is not OptionType.NOT_USABLE
                    con_files, req_files = _FomodFileInfo.process_files(
                        option_files, self.file_list, self.installer_root,
                        is_usable=op_usable)
                    collected_files.extend(req_files)
                    # Only include the conditional files if the option was
                    # actually selected
                    if option in selected_options:
                        collected_files.extend(con_files)
        for cond_pattern in self.fomod_tree.findall(
                u'conditionalFileInstalls/patterns/pattern'):
            dep_conditions = cond_pattern.find(u'dependencies')
            cond_files = cond_pattern.find(u'files')
            # We do not have to worry about the con/req split here, the
            # conditions for this section are the only thing that matters
            con_files, req_files = _FomodFileInfo.process_files(
                cond_files, self.file_list, self.installer_root,
                is_usable=True)
            try:
                self.test_conditions(dep_conditions)
                # Only include any files at all if the check passed
                collected_files.extend(req_files)
                collected_files.extend(con_files)
            except FailedCondition:
                pass
        file_dict = {}  # dst -> src
        priority_dict = {}  # dst -> priority
        for fm_info in collected_files:
            fm_info_dest = fm_info.file_destination
            if (fm_info_dest in priority_dict
                    and priority_dict[fm_info_dest] > fm_info.file_priority):
                # Don't overwrite the higher-priority file
                continue
            file_dict[fm_info_dest] = fm_info.file_source
            priority_dict[fm_info_dest] = fm_info.file_priority
        # return everything in strings
        return {a.s: b.s for a, b in file_dict.items()}

    def try_validate(self):
        """Tries to validate this FOMOD installer against the FOMOD schema.
        Returns a boolean indicating if the document was valid and and error
        log. Note that if the boolean is True, the log may be None."""
        if not _can_validate:
            return True, None # lxml is not installed, we can't do validation
        validator = etree.XMLSchema(_parsed_schema())
        was_valid = validator.validate(self.fomod_tree)
        return was_valid, validator.error_log

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

    # Translating this is non-trivial due to grammar differences between
    # languages, so give translators as much freedom as possible by exhausting
    # all six possibilities and offering a translation for each.
    _readable_state_errors = {
        (FileState.MISSING, FileState.INACTIVE): _(
            'File %(target_file_name)s should be missing, but is inactive '
            'instead.'),
        (FileState.MISSING, FileState.ACTIVE): _(
            'File %(target_file_name)s should be missing, but is active '
            'instead.'),
        (FileState.INACTIVE, FileState.MISSING): _(
            'File %(target_file_name)s should be inactive, but is missing '
            'instead.'),
        (FileState.INACTIVE, FileState.ACTIVE): _(
            'File %(target_file_name)s should be inactive, but is active '
            'instead.'),
        (FileState.ACTIVE, FileState.MISSING): _(
            'File %(target_file_name)s should be active, but is missing '
            'instead.'),
        (FileState.ACTIVE, FileState.INACTIVE): _(
            'File %(target_file_name)s should be active, but is inactive '
            'instead.'),
    }

    def _test_file_condition(self, condition):
        test_file = FName(condition.get('file'))
        target_type = _fs_parser[condition.get('state')]
        # Check if it's missing, ghosted or (in)active
        if not self.dst_dir.join(test_file).exists():
            if test_file not in bosh.modInfos:
                actual_type = FileState.MISSING
            else: # file in modInfos - its ghost must exist
                actual_type = FileState.INACTIVE
        else:
            actual_type = (FileState.ACTIVE if cached_is_active(test_file)
                           else FileState.INACTIVE)
        if actual_type is not target_type:
            raise FailedCondition(self._readable_state_errors[
                (target_type, actual_type)] % {'target_file_name': test_file})

    def _test_flag_condition(self, condition):
        fm_flag_name = condition.get(u'flag')
        fm_flag_value = condition.get(u'value', u'')
        actual_flag_value = self._fomod_flags().get(fm_flag_name, u'')
        if actual_flag_value != fm_flag_value:
            raise FailedCondition(_('Flag %(target_flag_name)s was expected '
                                    "to have value '%(val_want)s' but has "
                                    "value '%(val_have)s' instead.") % {
                'target_flag_name': fm_flag_name,
                'val_want': fm_flag_value,
                'val_have': actual_flag_value,
            })

    def _test_version_condition(self, condition):
        target_ver = LooseVersion(condition.get('version'))
        game_ver = LooseVersion(self.game_version)
        if game_ver < target_ver:
            raise FailedCondition(_('%(game_name)s version %(ver_want)s '
                                    'is required, but %(ver_have)s was '
                                    'found.') % {
                'game_name': bush.game.display_name,
                'ver_have': game_ver,
                'ver_want': target_ver,
            })

    def _test_fomm_condition(self, _condition):
        # Always accept FOMM conditions, seeing as we can't possibly compare
        # our own version against whatever version of FOMM might be 'required'.
        # Plus the FOMOD format is pretty much frozen now, so we support pretty
        # much all of it
        pass

    def _test_se_condition(self, condition):
        if not bush.game.Se.se_abbrev:
            return # No script extender, pass all tests
        target_ver = LooseVersion(condition.get('version'))
        ver_path = None
        for ver_file in bush.game.Se.ver_files:
            ver_path = bass.dirs['app'].join(ver_file)
            if ver_path.exists(): break
        if ver_path is None:
            raise FailedCondition(_('%(se_name)s version %(ver_want)s or '
                                    'higher is required, but could not be '
                                    'found.') % {
                'se_name': bush.game.Se.se_abbrev,
                'ver_want': target_ver,
            })
        parsed_ver = env.get_file_version(ver_path.s)
        if parsed_ver == (0, 0, 0, 0):
            actual_ver = LooseVersion('0')
        else:
            actual_ver = LooseVersion('.'.join(str(s) for s in parsed_ver))
        if actual_ver < target_ver:
            raise FailedCondition(_('%(se_name)s version %(ver_want)s or '
                                    'higher is required, but version '
                                    '%(ver_have)s was found instead.') % {
                'se_name': bush.game.Se.se_abbrev,
                'ver_want': target_ver,
                'ver_have': actual_ver,
            })

    def test_conditions(self, fomod_conditions):
        cond_op = fomod_conditions.get(u'operator', u'And')
        failed_conditions = []
        all_conditions = fomod_conditions.findall(u'*')
        for condition in all_conditions:
            try:
                self._condition_tests[condition.tag](self, condition)
            except FailedCondition as e:
                failed_conditions.extend([a for a in str(e).splitlines()])
                if cond_op == u'And':
                    raise FailedCondition(u'\n'.join(failed_conditions))
        if cond_op == u'Or' and len(failed_conditions) == len(all_conditions):
            raise FailedCondition(u'\n'.join(failed_conditions))

    _condition_tests = {
        'fileDependency': _test_file_condition,
        'flagDependency': _test_flag_condition,
        'gameDependency': _test_version_condition,
        'fommDependency': _test_fomm_condition,
        'foseDependency': _test_se_condition,
        'dependencies': test_conditions,
    }

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
