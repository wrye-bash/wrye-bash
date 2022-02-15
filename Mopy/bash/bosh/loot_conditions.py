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
#  Wrye Bash copyright (C) 2005-2009 Wrye, 2010-2022 Wrye Bash Team
#  https://github.com/wrye-bash
#
# =============================================================================
"""Pure Python implementation of some components of libloot-python needed by
Wrye Bash. This file handles the evaluation of conditions.

Recommended reading before working on this file:
https://loot-api.readthedocs.io/en/latest/metadata/conditions.html."""

__author__ = u'Infernio'

import operator
import os
import re

from .. import bass, bush
from ..bolt import GPath, Path, deprint, LooseVersion
from ..env import get_file_version
from ..exception import AbstractError, EvalError, FileError
from ..load_order import cached_active_tuple, cached_is_active, in_master_block

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
        # type: (str, list) -> None
        self.func_name = func_name
        self.func_args = func_args

    def evaluate(self):
        # Call the appropriate function, wrapping the error to make a nicer
        # error message if no appropriate function was found
        try:
            wanted_func = _function_mapping[self.func_name]
        except KeyError:
            raise EvalError(u"Unknown function '%s'" % self.func_name)
        try:
            return wanted_func(*self.func_args)
        except EvalError: raise
        except Exception:
            # Reraise because we can gracefully handle this by skipping the
            # tags for this plugin
            deprint(u'Error while evaluating function', traceback=True)
            raise EvalError(u'Error while evaluating function')

    def __repr__(self):
        fmt_args = []
        for a in self.func_args:
            if isinstance(a, str): # String
                fmt_a = u'"%s"' % a
            elif isinstance(a, int): # Checksum
                fmt_a = u'%X' % a
            else: # Comparison
                fmt_a = u'%r' % a
            fmt_args.append(fmt_a)
        return u'%s(%s)' % (
            self.func_name, u', '.join(fmt_args))

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
    # type: (str) -> bool
    """Takes either a file path or a regex. Returns True iff at least one
    active plugin matches the specified path or regex.

    :param path_or_regex: The file path or regex to check."""
    if is_regex(path_or_regex):
        # Regex means we have to look at each active plugin - plugins can
        # obviously only be in Data, no need to process the path here
        matches_regex = re.compile(path_or_regex).match
        return any(map(matches_regex, (p.s for p in cached_active_tuple())))
    else:
        return cached_is_active(GPath(path_or_regex))

def _fn_checksum(file_path, expected_crc):
    # type: (str, int) -> bool
    """Takes a file path. Returns True if the file that the path resolves to
    exists and its CRC32 matches the specified expected CRC.

    :param file_path: The path of the file to check.
    :param expected_crc: The expected CRC32 value."""
    try:
        return _process_path(file_path).crc == expected_crc
    except OSError:
        return False # Doesn't exist or is a directory

def _fn_file(path_or_regex):
    # type: (str) -> bool
    """Takes either a file path or a regex. Returns True iff at least one
    file exists that matches the specified path or regex.

    :param path_or_regex: The file path or regex to check."""
    # Takes either a regex or a file path
    if is_regex(path_or_regex):
        # Regex means we have to look at each file in the parent directory
        # Note that only the last part of the path may be a regex, so no need
        # to check every step of the way
        final_sep = path_or_regex.rfind(u'/')
        # Note that we don't have to error check here due to the +1 offset
        matches_regex = re.compile(path_or_regex[final_sep + 1:]).match
        parent_dir = _process_path(path_or_regex[:final_sep + 1])
        for f in _iter_dir(parent_dir):
            if matches_regex(f):
                return True
        return False
    else:
        return _process_path(path_or_regex).exists()

def _fn_is_master(file_path):
    # type: (str) -> bool
    """Takes a file path. Returns True iff a plugin with the specified name
    exists and is treated as a master by the currently managed game.

    :param file_path: The file path to check."""
    plugin_path = GPath(file_path)
    from . import modInfos
    # Need to check if it's on disk first, otherwise modInfos[x] errors
    return plugin_path in modInfos and in_master_block(modInfos[plugin_path])

def _fn_many(path_regex):
    # type: (str) -> bool
    """Takes a regex. Returns True iff more than 1 file matching the specified
    regex exists.

    :param path_regex: The regex to check."""
    # Same idea as in _fn_file
    final_sep = path_regex.rfind(u'/')
    matches_regex = re.compile(path_regex[final_sep + 1:]).match
    parent_dir = _process_path(path_regex[:final_sep + 1])
    # Check if we have more than one matching file
    matching_count = 0
    for f in _iter_dir(parent_dir):
        if matches_regex(f):
            matching_count += 1
            if matching_count > 1:
                return True
    return False

def _fn_many_active(path_regex):
    # type: (str) -> bool
    """Takes a regex. Returns True iff more than 1 active plugin matches the
    specified regex.

    :param path_regex: The regex to check."""
    matches_regex = re.compile(path_regex).match
    # Check if we have more than one matching active plugin
    matching_count = 0
    for p in cached_active_tuple():
        if matches_regex(p.s):
            matching_count += 1
            if matching_count > 1:
                return True
    return False

##: Maybe tweak the implementation to match LOOT's by adding some params to
# env.get_file_version?
def _fn_product_version(file_path, expected_ver, comparison):
    # type: (str, str, Comparison) -> bool
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
    if file_path.cext in ('.exe', '.dll'):
        # Read version from executable fields
        actual_ver = LooseVersion(_read_binary_ver(file_path.s))
    else:
        raise FileError(file_path, 'Product version query was requested, '
                                   'but the file is not an executable.')
    return comparison.compare(actual_ver, LooseVersion(expected_ver))

def _fn_version(file_path, expected_ver, comparison):
    # type: (str, str, Comparison) -> bool
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
    if file_path.cext in bush.game.espm_extensions:
        # Read version from the description
        from . import modInfos
        actual_ver = LooseVersion(
            modInfos.getVersion(file_path.stail) or '0')
    elif file_path.cext in ('.exe', '.dll'):
        # Read version from executable fields
        actual_ver = LooseVersion(_read_binary_ver(file_path.s))
    else:
        raise FileError(file_path, 'Version query was requested, but the '
                                   'file is not a plugin or executable.')
    return comparison.compare(actual_ver, LooseVersion(expected_ver))

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
def is_regex(string_to_check):
    # type: (str) -> bool
    """Checks if the specified string is to be treated as a regex for purposes
    of differentiating between file paths and regexes for the functions that
    can take either one. This is done by checking if the string contains one of
    several special characters - see
    https://loot-api.readthedocs.io/en/latest/metadata/conditions.html#functions
    for the details.

    :param string_to_check: The string to check for regex characters."""
    for regex_char in r':\*?|':
        if regex_char in string_to_check:
            return True
    return False

def _process_path(file_path):
    # type: (str) -> Path
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
        if not path_component: continue # skip empty components
        if path_component == u'..':
            # Check if this is a misplaced parent specifier
            if parents_done:
                raise EvalError(u"Illegal file path: Unexpected '..' (may "
                                u'only be at the start of the path).',
                                file_path)
            parents += 1
        else:
            # Remember that we're done parsing any parent specifiers
            parents_done = True
            child_components.append(path_component)
    relative_path = bass.dirs[u'mods']
    # Move up by the number of requested parents
    for x in range(parents):
        relative_path = relative_path.head
    # If that put us outside the game folder, the path is invalid
    if not os.path.realpath(relative_path).startswith(bass.dirs[u'app'].s):
        raise EvalError(u'Illegal file path: May not specify paths that '
                        u'resolve to outside the game folder.', file_path)
    return relative_path.join(*child_components)

def _read_binary_ver(binary_path):
    """Reads version information from a binary at the specified path, returning
    it as a string for LooseVersion."""
    binary_ver = get_file_version(binary_path)
    # Handle special case of (0, 0, 0, 0) - no version present
    if binary_ver == (0, 0, 0, 0):
        return '0'
    return '.'.join(str(s) for s in binary_ver)

def _iter_dir(parent_dir):
    """Takes a path and returns an iterator of the filenames (as strings) of
    files in that folder. .ghost extensions will be chopped off."""
    return (f.sroot if f.cext == u'.ghost' else f.s for f in parent_dir.list())

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
        # type: (str) -> None
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
            raise EvalError(u"Invalid comparison operator '%s', expected one "
                            u"of [%s]" % (self.cmp_operator, u', '.join([
                u'%s' % x for x in self._cmp_functions])))

    def __repr__(self):
        return u'%s' % self.cmp_operator
