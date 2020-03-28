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
"""Pure Python implementation of some components of libloot-python needed by
Wrye Bash. This file handles the evaluation of conditions.

Recommended reading before working on this file:
https://loot-api.readthedocs.io/en/latest/metadata/conditions.html."""

import operator
import re

from .. import bass, bush
from ..bolt import GPath, Path
from ..env import get_file_version
from ..exception import AbstractError, ParserError, FileError
from ..load_order import cached_active_tuple, cached_is_active, in_master_block

__author__ = u'Infernio'

# Conditions
class _ACondition(object):
    """Abstract base class for all conditions."""
    __slots__ = ()

    def evaluate(self):
        # type: () -> bool
        """Evaluates this condition, resolving it to a boolean value."""
        raise AbstractError()

class ConditionAnd(_ACondition):
    """Combines two conditions, evaluates to True iff both conditions evaluate
    to True."""
    __slots__ = (u'first_cond', u'second_cond')

    def __init__(self, first_cond, second_cond):
        # type: (_ACondition, _ACondition) -> None
        self.first_cond = first_cond
        self.second_cond = second_cond

    def evaluate(self):
        return self.first_cond.evaluate() and self.second_cond.evaluate()

    def __repr__(self):
        return u'(%r and %r)' % (self.first_cond, self.second_cond)

class ConditionFunc(_ACondition):
    """Calls a function of the specified name with the specified arguments.
    Currently supported functions are:
        - active
        - checksum
        - file
        - is_master
        - many
        - many_active
        - product_version
        - version"""
    __slots__ = (u'func_name', u'func_args')

    def __init__(self, func_name, func_args):
        # type: (unicode, list) -> None
        self.func_name = func_name
        self.func_args = func_args

    def evaluate(self):
        # Call the appropriate function, wrapping the error to make a nicer
        # error message if no appropriate function was found
        try:
            return _function_mapping[self.func_name](*self.func_args)
        except KeyError:
            raise ParserError(u"Unknown function '%s'" % self.func_name)

    def __repr__(self):
        return u'%s(%s)' % (
            self.func_name, u', '.join([u'%r' % a for a in self.func_args]))

class ConditionNot(_ACondition):
    """Evaluates to True iff the specified condition evaluates to False."""
    __slots__ = (u'target_cond',)

    def __init__(self, target_cond):
        # type: (_ACondition) -> None
        self.target_cond = target_cond

    def evaluate(self):
        return not self.target_cond.evaluate()

    def __repr__(self):
        return u'(not %r)' % self.target_cond

class ConditionOr(_ACondition):
    """Combines two conditions, evaluates to True iff at least one of the two
    evaluates to True."""
    __slots__ = (u'first_cond', u'second_cond')

    def __init__(self, first_cond, second_cond):
        # type: (_ACondition, _ACondition) -> None
        self.first_cond = first_cond
        self.second_cond = second_cond

    def evaluate(self):
        return self.first_cond.evaluate() or self.second_cond.evaluate()

    def __repr__(self):
        return u'(%r or %r)' % (self.first_cond, self.second_cond)

# Functions
def _fn_active(path_or_regex):
    # type: (unicode) -> bool
    """Takes either a file path or a regex. Returns True iff at least one
    active plugin matches the specified path or regex.

    :param path_or_regex: The file path or regex to check."""
    if _is_regex(path_or_regex):
        # Regex means we have to look at each active plugin - plugins can
        # obviously only be in Data, no need to process the path here
        file_regex = re.compile(path_or_regex)
        return any(file_regex.match(x.s) for x in cached_active_tuple())
    else:
        return cached_is_active(GPath(path_or_regex))

def _fn_checksum(file_path, expected_crc):
    # type: (unicode, int) -> bool
    """Takes a file path. Returns True if the file that the path resolves to
    exists and its CRC32 matches the specified expected CRC.

    :param file_path: The path of the file to check.
    :param expected_crc: The expected CRC32 value."""
    try:
        return _process_path(file_path).crc == expected_crc
    except IOError:
        return False # Doesn't exist or is a directory

def _fn_file(path_or_regex):
    # type: (unicode) -> bool
    """Takes either a file path or a regex. Returns True iff at least one
    file exists that matches the specified path or regex.

    :param path_or_regex: The file path or regex to check."""
    # Takes either a regex or a file path
    if _is_regex(path_or_regex):
        # Regex means we have to look at each file in the parent directory
        # Note that only the last part of the path may be a regex, so no need
        # to check every step of the way
        final_sep = path_or_regex.rfind(u'/')
        # Note that we don't have to error check here due to the +1 offset
        file_regex = re.compile(path_or_regex[final_sep + 1:])
        parent_dir = _process_path(path_or_regex[:final_sep + 1])
        return any(file_regex.match(x.s) for x in parent_dir.list())
    else:
        return _process_path(path_or_regex).exists()

def _fn_is_master(file_path):
    # type: (unicode) -> bool
    """Takes a file path. Returns True iff a plugin with the specified name
    exists and is treated as a master by the currently managed game.

    :param file_path: The file path to check."""
    plugin_path = GPath(file_path)
    from . import modInfos
    # Need to check if it's on disk first, otherwise modInfos[x] errors
    return plugin_path in modInfos and in_master_block(modInfos[plugin_path])

def _fn_many(path_regex):
    # type: (unicode) -> bool
    """Takes a regex. Returns True iff more than 1 file matching the specified
    regex exists.

    :param path_regex: The regex to check."""
    # Same idea as in _fn_file
    final_sep = path_regex.rfind(u'/')
    file_regex = re.compile(path_regex[final_sep + 1:])
    parent_dir = _process_path(path_regex[:final_sep + 1])
    # Check if we have more than one matching file
    return len([x for x in parent_dir.list() if file_regex.match(x.s)]) > 1

def _fn_many_active(path_regex):
    # type: (unicode) -> bool
    """Takes a regex. Returns True iff more than 1 active plugin matches the
    specified regex.

    :param path_regex: The regex to check."""
    file_regex = re.compile(path_regex)
    # Check if we have more than one matching active plugin
    return len([x for x in cached_active_tuple() if file_regex.match(x.s)]) > 1

def _fn_product_version(file_path, expected_ver, comparison):
    # type: (unicode, unicode, Comparison) -> bool
    """Takes a file path, an expected version and a comparison operator.
    Returns True iff the file path resolves to an executable (.exe or .dll) and
    its version compares successfully against the specified expected version,
    using the specified comparison operator.

    Note that a nonexistent file is treated as having the version 0 and an
    error is raised if the file exists, but is not an executable. These
    behaviors are mandated by the libloot specification.

    A limitation of Wrye Bash's implementation is that it doesn't just check
    product versions. Instead, both FileVersion and ProductVersion are checked,
    both the fixed and string field variants, and the first non-default version
    (i.e. not 1.0.0.0 or 0.0.0.0) is used. See env.get_file_version for more
    details.

    :param file_path: The file path to check.
    :param expected_ver: The version to check against.
    :param comparison: The comparison operator to use."""
    file_path = _process_path(file_path)
    actual_ver = [0]
    if file_path.isfile():
        if file_path.cext in (u'.exe', u'.dll'):
            # Read version from executable fields
            actual_ver = list(get_file_version(file_path.s))
        else:
            raise FileError(file_path.s, u'Product version query was '
                                         u'requested, but the file is not an '
                                         u'executable.')
    return comparison.compare(
        actual_ver, [int(x) for x in expected_ver.split(u'.')])

_VERSION_REGEX = re.compile(u'Version: ([\\d.]+)', re.I | re.U)
def _fn_version(file_path, expected_ver, comparison):
    # type: (unicode, unicode, Comparison) -> bool
    """Behaves like product_version, but extends its behavior to also allow
    plugin version checks. If the plugin's description contains a
    'Version: ...' section, then the version specified by that section is
    compared. The comparison is done case-insensitively, and any unicode word
    characters are allowed. If no version is found in the description, then
    the version 0 is assumed.

    See the _fn_product_version docstring for details on how executables are
    handled by these two functions.

    :param file_path: The file path to check.
    :param expected_ver: The version to check against.
    :param comparison: The comparison operator to use."""
    file_path = _process_path(file_path)
    actual_ver = [0]
    if file_path.isfile():
        if file_path.cext in bush.game.espm_extensions:
            # Read version from the description
            from . import modInfos
            ver_match = _VERSION_REGEX.search(
                modInfos[GPath(file_path.tail)].header.description)
            if ver_match:
                actual_ver = [int(x) for x in ver_match.group(1).split(u'.')]
        elif file_path.cext in (u'.exe', u'.dll'):
            # Read version from executable fields
            actual_ver = list(get_file_version(file_path.s))
        else:
            raise FileError(file_path.s, u'Version query was requested, but '
                                         u'the file is not a plugin or '
                                         u'executable.')
    return comparison.compare(
        actual_ver, [int(x) for x in expected_ver.split(u'.')])

# Maps the function names used in conditions to the functions implementing them
_function_mapping = {
    u'active':          _fn_active,
    u'checksum':        _fn_checksum,
    u'file':            _fn_file,
    u'is_master':       _fn_is_master,
    u'many':            _fn_many,
    u'many_active':     _fn_many_active,
    u'product_version': _fn_product_version,
    u'version':         _fn_version,
}

# Misc
def _is_regex(string_to_check):
    # type: (unicode) -> bool
    """Checks if the specified string is to be treated as a regex for purposes
    of differentiating between file paths and regexes for the functions that
    can take either one. This is done by checking if the string contains one of
    several special characters - see
    https://loot-api.readthedocs.io/en/latest/metadata/conditions.html#functions
    for the details.

    :param string_to_check: The string to check for regex characters."""
    return any(x in string_to_check for x in u':\\*?|')

def _process_path(file_path):
    # type: (unicode) -> Path
    """Processes a file path, prepending the path to the Data folder and
    resolving any '../' specifiers that it may have. Note that LOOT's file
    paths always use slashes as separators, so this methods also converts those
    into the platform-appropriate representation. The result is returned as a
    bolt.Path instance.

    :param file_path: The file path to process."""
    # File paths are always relative to the Data folder, but may have ../ in
    # front of them, which takes them n levels above the Data folder. They are
    # also *always* delimited by slashes, *not* backslashes.
    parents = 0
    parents_done = False
    child_components = []
    for path_component in file_path.split(u'/'):
        if path_component == u'..':
            if not path_component: continue # skip empty components
            # Check if this is a misplaced parent specifier
            if parents_done:
                raise ParserError(
                    u"Illegal file path: Unexpected '..' (may only be at the "
                    u"start of the path).", file_path)
            parents += 1
        else:
            # Remember that we're done parsing any parent specifiers
            parents_done = True
            child_components.append(path_component)
    relative_path = bass.dirs['mods']
    # Move up by the number of requested parents
    for x in xrange(parents):
        relative_path = relative_path.head
    return relative_path.join(*child_components)

class Comparison(object):
    """Implements a comparison operator. Takes a unicode string containing the
    operator."""
    __slots__ = (u'cmp_operator',)

    # Maps each operator string to an appropriate implementation
    _cmp_functions = {
        u'>': operator.gt,
        u'<': operator.lt,
        u'>=': operator.ge,
        u'<=': operator.le,
        u'==': operator.eq,
        u'!=': operator.ne,
    }

    def __init__(self, cmp_operator):
        # type: (unicode) -> None
        self.cmp_operator = cmp_operator

    def compare(self, first_val, second_val):
        """Executes the comparison on the two specified values.

        :param first_val: The first value to compare.
        :param second_val: The second value to compare."""
        # Ordered by frequency - for performance
        try:
            return self._cmp_functions[self.cmp_operator](
                first_val, second_val)
        except KeyError:
            raise ParserError(
                u"Invalid comparison operator '%s', expected one of [%s]" % (
                    self.cmp_operator,
                    u', '.join([u'%s' % x for x in self._cmp_functions])))

    def __repr__(self):
        return u'Comparison(%r)' % self.cmp_operator
