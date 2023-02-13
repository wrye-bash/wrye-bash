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
"""Pure Python implementation of some components of libloot-python needed by
Wrye Bash. This file handles parsing the masterlists, including condition
syntax.

Recommended reading before working on this file:
https://loot-api.readthedocs.io/en/latest/metadata/file_structure.html
https://loot-api.readthedocs.io/en/latest/metadata/data_structures/index.html
https://loot-api.readthedocs.io/en/latest/metadata/conditions.html."""

from __future__ import annotations

__author__ = 'Infernio'

import re
from collections import deque
from copy import deepcopy

import yaml

from .bolt import AFile, FName, FNDict, Path, deprint
from .exception import BoltError, EvalError, LexerError, ParserError
from .loot_conditions import Comparison, ConditionAnd, ConditionFunc, \
    ConditionNot, ConditionOr, _ACondition, is_regex

# Typing
_RTags = tuple[set[str], set[str]] # 'returned tags'

# Try to use the C version (way faster), if that isn't possible fall back to
# the pure Python version
try:
    from yaml import CSafeLoader as SafeLoader
    deprint('Using LibYAML-based parser')
except ImportError:
    from yaml import SafeLoader
    deprint('Failed to import LibYAML-based parser, falling back to Python '
            'version')

# API
libloot_version = '0.18.x' # The libloot version with which this implementation
                           # is compatible

class LOOTParser(object):
    """The main frontend for interacting with LOOT's masterlists. Provides
    methods to parse masterlists and to retrieve information from them."""
    __slots__ = ('_cached_masterlist', '_cached_regexes', '_cached_merges',
                 '_masterlist', '_userlist', '_taglist', '_tagCache')

    def __init__(self, masterlist_path: Path, userlist_path: Path,
            taglist_path: Path):
        """Initialize a LOOTParser instance with the three specified
        masterlist paths. These will be cached via AFile and updated when
        refreshBashTags is called. Note that the order in which we read them
        is masterlist (+ userlist if present), then taglist if masterlist is
        not present.

        :param masterlist_path: The path to the LOOT masterlist that should be
            parsed.
        :param userlist_path: Optional, the path to the LOOT userlist that
            should be parsed and merged with the masterlist.
        :param taglist_path: the path to Bash's own cached masterlists - those
            must always exist."""
        self._cached_masterlist: dict[FName, _PluginEntry] = FNDict()
        self._cached_regexes = {}
        self._cached_merges = {}
        deprint('Using these LOOT paths:')
        deprint(f' Masterlist: {masterlist_path}')
        deprint(f' Userlist: {userlist_path}')
        deprint(f' Taglist (fallback): {taglist_path}')
        self._masterlist  = AFile(masterlist_path)
        self._userlist  = AFile(userlist_path)
        self._taglist  = AFile(taglist_path)
        self._refresh_tags_cache(_force=True)
        # Old api
        self._tagCache: dict[FName, _RTags] = {}
        deprint(f'Initialized loot_parser, compatible with libloot '
                f'v{libloot_version}')

    def _refresh_tags_cache(self, _force=False):
        try:
            # keep _force last to update AFile's caches
            if self._masterlist.do_update(raise_on_error=True) or \
                    self._userlist.do_update() or _force:
                args = [self._masterlist.abs_path]
                if self._userlist.abs_path.exists(): args.append(
                    self._userlist.abs_path)
                self.load_lists(*args)
                return True
        except (OSError, yaml.YAMLError):
        #--No masterlist or an error occurred while reading it, use the taglist
            try:
                if self._taglist.do_update(raise_on_error=True) or _force:
                    self.load_lists(self._taglist.abs_path)
                return True
            except OSError:
                # Missing taglist is fine, happens if someone cloned without
                # running update_taglist.py
                pass
            except yaml.YAMLError as e:
                raise BoltError(
                    f'{self._taglist.abs_path} could not be parsed ({e!r}). '
                    f'Please ensure Wrye Bash is installed correctly.')
        return False

    def get_plugin_tags(self, plugin_name: FName, catch_errors=True) -> _RTags:
        """Retrieves added and removed tags for the specified plugin. If the
        plugin has no entry in the masterlist, two empty sets are returned.
        This method will evaluate any conditions that may be attached to the
        tags, but the result will *not* be cached.

        :param plugin_name: The name of the plugin whose tags should be
            retrieved.
        :param catch_errors: If False, no errors will be caught - you will have
            to handle them manually. Intended for unit tests.
        :return: A tuple containing two sets, one with added and one with
            removed tags."""
        def get_resolved_tags(res_entry):
            # We may have to evaluate conditions now
            try:
                return (_resolve_tags(res_entry.tags_added),
                        _resolve_tags(res_entry.tags_removed))
            except (LexerError, ParserError, EvalError):
                if not catch_errors:
                    raise
                deprint('Error while evaluating LOOT condition',
                    traceback=True)
                return set(), set()
        if plugin_name in self._cached_merges:
            return get_resolved_tags(self._cached_merges[plugin_name])
        return get_resolved_tags(self._perform_merge(plugin_name))

    def load_lists(self, masterlist_path: Path,
            userlist_path: Path | None = None, catch_errors=True):
        """Parses and stores the specified LOOT masterlist, and optionally
        merges any additions from the specified userlist in.

        :param masterlist_path: The path to the LOOT masterlist that should be
            parsed.
        :param userlist_path: Optional, the path to the LOOT userlist that
            should be parsed and merged with the masterlist.
        :param catch_errors: If False, no errors will be caught - you will have
            to handle them manually. Intended for unit tests."""
        try:
            masterlist = _parse_list(masterlist_path)
            if userlist_path:
                userlist = None
                # Userlists often end up in all kinds of wild formats, meaning
                # they can cause all kinds of wild errors too - skip and
                # complain if that happens
                try:
                    userlist = _parse_list(userlist_path)
                except Exception:
                    if not catch_errors:
                        raise
                    deprint(f'Failed to parse LOOT userlist {userlist_path}, '
                            f'it likely has malformed syntax', traceback=True)
                if userlist is not None:
                    _merge_lists(masterlist, userlist)
            self._cached_masterlist = masterlist
            self._cached_regexes = [(re.compile(r, re.I).match, e) for r, e in
                                    masterlist.items() if is_regex(r)]
            self._cached_merges = {}
        except (re.error, TypeError, yaml.YAMLError):
            if not catch_errors:
                raise
            deprint(f'Error when parsing LOOT masterlist {masterlist_path}, '
                    f'it likely has malformed syntax', traceback=True)

    def is_plugin_dirty(self, plugin_name: FName, mod_infos) -> bool:
        """Checks if the specified plugin is dirty according to the information
        inside the LOOT masterlist (or userlist, if it was parsed).

        :param plugin_name: The name of the plugin whose dirty info should be
            checked.
        :param mod_infos: bosh.modInfos. Must be up to date."""
        def check_dirty(res_entry):
            return (res_entry and mod_infos[plugin_name].cached_mod_crc()
                    in res_entry.dirty_crcs)
        if plugin_name in self._cached_merges:
            return check_dirty(self._cached_merges[plugin_name])
        return check_dirty(self._perform_merge(plugin_name))

    def _perform_merge(self, plugin_s: FName) -> _PluginEntry:
        """Checks the masterlist and all regexes for a match with the spcified
        plugin name string, then merges the resulting entries, stores the final
        entry in _cached_merges and returns it."""
        all_entries = []
        # Check for a literal match first
        main_entry = self._cached_masterlist.get(plugin_s)
        if main_entry:
            all_entries.append(main_entry)
        for match_plugin, plugin_entry in self._cached_regexes:
            if match_plugin(plugin_s):
                all_entries.append(plugin_entry)
        if not all_entries:
            # Plugin has no entry in the masterlist, this is fine
            merged_entry = _PluginEntry({})
        elif len(all_entries) == 1:
            # There is only one entry, so we can avoid the deepcopy (we only
            # ever mutate deepcopied entries, so this is safe)
            merged_entry = all_entries[0]
        else:
            # Merge the later entries with the first one
            merged_entry = deepcopy(all_entries[0])
            for plugin_entry in all_entries[1:]:
                merged_entry.merge_with(plugin_entry)
        self._cached_merges[plugin_s] = merged_entry
        return merged_entry

    # Old ConfigHelpers API -----------------------------
    def refreshBashTags(self):
        """Reloads tag info if file dates have changed."""
        if self._refresh_tags_cache():
            self._tagCache = {}

    ##: move cache into loot_parser, then build more sophisticated invalidation
    # mechanism to handle CRCs, active status, etc. - ref #353
    def get_tags_from_loot(self, modName: FName) -> _RTags:
        """Gets bash tag info from the cache, or from loot_parser if it is not
        cached."""
        try:
            return self._tagCache[modName]
        except KeyError:
            self._tagCache[modName] = ca_tags = self.get_plugin_tags(modName)
            return ca_tags

# Implementation
class _PluginEntry(object):
    """Represents stored information about a plugin's entry in the LOOT
    masterlist and/or userlist."""
    __slots__ = ('dirty_crcs', 'tags_added', 'tags_removed')

    def __init__(self, yaml_entry: dict):
        """Parses the specified dictionary, as created by PyYAML's parse of the
        LOOT masterlist. Expects a dict with syntax like this:

            {
                # note that 'util' is required by libloot, but ignored here
                'dirty': [{'crc': 0xDEADBEEF, 'util': 'foo'}, ...],
                # any combination of these two styles of tags:
                #  - unconditional
                'tag': ['C.Water', '-Deactivate', ...],
                #  - conditional
                'tag': [{'name': 'Delev', 'condition': 'file("foo.esp")'}, ...]
            }

        Any of the initial keys may be missing, in which case an empty list is
        assumed as the default."""
        self.dirty_crcs = {c['crc'] for c in yaml_entry.get('dirty', ())}
        self.tags_added = set()
        self.tags_removed = set()
        # Need to handle a starting '-', which means removed
        for tag in yaml_entry.get('tag', ()):
            try:
                removes = tag[0] == '-'
                target_tag = tag[1:] if removes else tag
            except KeyError:
                # This is a dict, means we'll have to handle conditions later
                tag_name = tag['name']
                removes = tag_name[0] == '-'
                target_tag = _ConditionalTag(
                    (tag_name[1:] if removes else tag_name), tag['condition'])
            target_set = self.tags_removed if removes else self.tags_added
            target_set.add(target_tag)

    def merge_with(self, other_entry: _PluginEntry):
        """Merges the information stored in this plugin entry with the
        information stored in other_entry. Since another list can never remove
        things from the original list (a limitation imposed by LOOT's GUI and
        libloot itself), we only need to make a union of each set.

        :param other_entry: The plugin entry to merge into this one."""
        self.dirty_crcs |= other_entry.dirty_crcs
        self.tags_added |= other_entry.tags_added
        self.tags_removed |= other_entry.tags_removed

    def __repr__(self):
        return (f'<added: {self.tags_added!r}, '
                f'removed: {self.tags_removed!r}, dirty: {self.dirty_crcs!r}>')

class _ConditionalTag(object):
    """Represents a tag that may or may not be applied to a mod right now,
    depending on whether or not its condition evaluates to True."""
    __slots__ = ('tag_name', 'tag_condition')
    tag_condition: str | _ACondition

    def __init__(self, tag_name: str, tag_condition: str):
        """Creates a new _ConditionalTag with the specified tag name and tag
        condition.

        :param tag_name: The name of the tag.
        :param tag_condition: A condition string that determines whether or not
            this tag will be applied. See the links at the top of this file for
            more information."""
        self.tag_name = tag_name
        self.tag_condition = tag_condition

    def eval_condition(self) -> bool:
        """Evaluates this tag's condition, parsing and caching it first if it's
        still a string.

        :return: The boolean value that the condition evaluated to."""
        try:
            return self.tag_condition.evaluate()
        except AttributeError:
            # Lazily parse the condition and cache it
            self.tag_condition = _process_condition_string(self.tag_condition)
            return self.tag_condition.evaluate()

    def __repr__(self):
        return f'{self.tag_name} if {self.tag_condition!r}'

def _resolve_tags(tag_set: set[str | _ConditionalTag]) -> set[str]:
    """Convenience method to evaluate conditions for a set of tags (may
    contain both conditional and unconditional (i.e. just a string) tags)
    and return only the names of those tags that will actually apply.

    :param tag_set: The set of tags to resolve.
    :return: A set of strings, containing only unconditional tags and
        conditional tags whose conditions evaluated to True."""
    resulting_tags = set()
    add_resulting_tag = resulting_tags.add
    for tag in tag_set:
        # Most tags are unconditional, so avoid try-except
        if isinstance(tag, _ConditionalTag):
            if tag.eval_condition():
                add_resulting_tag(tag.tag_name)
        else:
            add_resulting_tag(tag)
    return resulting_tags

##: A lot of the lexing/parsing stuff here could probably be moved to a
# generic top-level file and used to eventually write a better wizard parser
def _process_condition_string(condition_string: str) -> _ACondition:
    """The driver function for condition string parsing. Performs lexical
    analysis on the specified condition string and then parses the resulting
    tokens, resulting in an _ACondition-derived object.

    :param condition_string: The condition string to process.
    :return: The resulting condition object."""
    return _parse_condition(_lex_condition_string(condition_string))

class _Token(object):
    """Represents a token used by the lexer."""
    __slots__ = ('token_tag', 'token_text', 'line_offset', 'condition_str')

    def __init__(self, token_tag: str, token_text: str, line_offset: int,
            condition_str: str):
        """Creates a new token with the specified properties.

        :param token_tag: The tag to assign to this token. This can be used to
            handle different 'types' of tokens (e.g. strings, keywords, etc.).
        :param token_text: The text that this matched this token's regex.
        :param line_offset: The offset inside the condition string at which
            this token was created. Used when printing errors.
        :param condition_str: The entire condition string that this token was
            in. Used when printing errors."""
        self.token_tag = token_tag
        self.token_text = token_text
        self.line_offset = line_offset
        self.condition_str = condition_str

    @property
    def debug_info(self):
        """Returns debug information about this token that can be fed to a
        lexer or parser error to highlight the point in the file where the
        error occurred.

        :return: A tuple containing the original condition string, the starting
            offset of this token and the ending position of this token."""
        return (self.condition_str, self.line_offset,
                self.line_offset + len(self.token_text))

    def __repr__(self):
        return f'{self.token_tag}: {self.token_text}'

# Token tags
_IGNORE     = None
_AND        = 'AND'
_OR         = 'OR'
_NOT        = 'NOT'
_COMPARISON = 'COMPARISON'
_LPAREN     = 'LPAREN'
_RPAREN     = 'RPAREN'
_COMMA      = 'COMMA'
_STRING     = 'STRING'
_CHECKSUM   = 'CHECKSUM'
_FUNCTION   = 'FUNCTION'

# The actual regexes used by the lexer
_token_regexes = (
    (re.compile(' +'),                     _IGNORE),
    (re.compile('and'),                    _AND),
    (re.compile('or'),                     _OR),
    (re.compile('not'),                    _NOT),
    (re.compile('\\('),                    _LPAREN),
    (re.compile('\\)'),                    _RPAREN),
    (re.compile(','),                      _COMMA),
    (re.compile('(?:(?:<|>)=?)|(?:!|=)='), _COMPARISON),
    ##: Verify that we don't have to worry about escapes
    # This is not a typo: empty strings are forbidden by the grammar
    (re.compile('"[^"]+"'),                _STRING),
    (re.compile('[0-9ABCDEF]+'),           _CHECKSUM),
    (re.compile('[a-z_]+'),                _FUNCTION),
)

def _lex_condition_string(condition_string: str) -> deque[_Token]:
    """Performs lexical analysis ('lexing') on the specified condition string,
    turning it into a deque of tokens. This is done to make the parser much
    simpler and much more human-readable.

    The regexes specified in _token_regexes are applied one by one until a
    match is found, at which point a token is created from the matched text and
    the appropriate tag. If the token has a truthy tag (i.e. not None or an
    empty string), then it will be stored for use by the parser - otherwise, it
    will be discarded. This is useful for handling comments and whitespace. The
    index into the string is then forwarded to the end of the match and the
    process is repeated, until we have reached EOL.

    If at any point during this process no regex can match the remaining
    condition substring, an error is raised.

    :param condition_string: The string to lex.
    :return: A deque containing each stored token."""
    tokens = deque()
    i = 0
    while i < len(condition_string):
        token_match = None
        for token_pattern, token_tag in _token_regexes:
            token_match = token_pattern.match(condition_string, i)
            if token_match:
                # We found a match, check if we should keep the token
                if token_tag:
                    tokens.append(_Token(
                        token_tag, token_match.group(0), token_match.start(0),
                        condition_string))
                break
        if not token_match:
            # No token regex matched the input, complain about it
            raise LexerError(f"Illegal character '{condition_string[i]}'",
                             condition_string, i)
        else:
            i = token_match.end(0) # Forward to the end of the match
    return tokens

# Precedence climbing algorithm in this section adapted from
# https://eli.thegreenplace.net/2012/08/02/parsing-expressions-by-precedence-climbing
class _OperatorInfo(object):
    """Stores the precedence and associativity of a binary operator."""
    __slots__ = ('precedence', 'left_associative')

    def __init__(self, prec: int, assoc: bool):
        """Creates a new _OperatorInfo with the specified precedence and
        associativity.

        :param prec: An integer representing the operator's precedence. A
            larger number means higher precedence.
        :param assoc: If True, then this operator is left-associative."""
        self.precedence = prec
        self.left_associative = assoc

    @property
    def next_min_precedence(self) -> int:
        """Computes the next minimum precedence needed to move the operator
        computation to the right. For left-associative operators, a different
        operator with higher precedence is needed, while right-associative
        operators obviously want to move right as far as possible.

        :return: An integer representing the minimum precedence that the next
            binary operator must have to move the computation to the right."""
        return self.precedence + (1 if self.left_associative else 0)

# Stores information about each valid binary operator
_op_info = {
    _AND: _OperatorInfo(2, True),
    _OR:  _OperatorInfo(1, True),
}

# Maps each operator tag to the class that implements the operator
_op_impl = {
    _AND: ConditionAnd,
    _OR:  ConditionOr,
}

def _parse_condition(tokens: deque[_Token], min_prec=1) -> _ACondition:
    """Parses the specified deque of tokens, returning an _ACondition-derived
    instance representing the resulting condition. This method uses a
    precedence climbing algorithm based on atoms (see _parse_atom below) to
    implement correct operator precedence.

    :param tokens: The deque of tokens that should be parsed.
    :param min_prec: The minumum precedence needed for the next operator, if
        any, to take over the computation. 1 by default.
    :return: The parsed condition."""
    # Begin by parsing the LHS as an atom
    lhs = _parse_atom(tokens)
    curr_token = _peek_token(tokens)
    # Check that
    #  1. We're not at EOL yet
    #  2. The current token is a binary operator
    #  3. The precedence is sufficient to keep moving right
    while (curr_token and
           curr_token in _op_info and
           _op_info[curr_token].precedence >= min_prec):
        _pop_token(tokens, curr_token)
        # Compute the RHS, making sure to pass the next min precedence
        rhs = _parse_condition(
            tokens, _op_info[curr_token].next_min_precedence)
        # Update the LHS by combining it with the RHS using the appropriate
        # operator implementation - don't forget to peek the next token now!
        lhs = _op_impl[curr_token](lhs, rhs)
        curr_token = _peek_token(tokens)
    # We're done - return whatever the LHS is now (either an atom or a binary
    # operator that eventually resolves down to atoms)
    return lhs

def _parse_atom(tokens: deque[_Token], accept_not=True) -> _ACondition:
    """Parses the specified deque of tokens, returning an atom (which is either
    a function call, a parenthesized condition or a negated function call (e.g.
    'not file("foo.esp")')).

    :param tokens: The deque of tokens that should be parsed.
    :param accept_not: Whether or not to accept 'not' expressions as atoms.
        Used to avoid accepting 'not not' expressions.
    :return: The parsed atom."""
    ttag = _peek_token(tokens)
    if ttag == _FUNCTION:
        return _parse_function(tokens)
    elif ttag == _LPAREN:
        # Parentheses override all precedence rules - treat them as atoms
        _pop_token(tokens, _LPAREN)
        ret_cond = _parse_condition(tokens)
        _pop_token(tokens, _RPAREN)
        return ret_cond
    elif accept_not and ttag == _NOT:
        # 'not' is unary, so can't be handled by the regular algorithm
        _pop_token(tokens, _NOT)
        return ConditionNot(_parse_atom(tokens, accept_not=False))
    else:
        raise ParserError(f'Unexpected token {ttag} - expected one of '
                          f'{[_FUNCTION, _LPAREN, _NOT]}',
                          *_pop_token(tokens, ttag).debug_info)

def _parse_function(tokens: deque[_Token]) -> ConditionFunc:
    """Parses the specified deque of tokens, returning a function call. These
    have the syntax 'FUNCTION LPAREN argument [ COMMA argument ]* RPAREN'. See
    _parse_argument below for the definition of an argument.

    :param tokens: The deque of tokens that should be parsed.
    :return: The parsed function call."""
    func_args = []
    func_name = _pop_token(tokens, _FUNCTION).token_text
    _pop_token(tokens, _LPAREN)
    # One argument is required
    func_args.append(_parse_argument(tokens))
    while _peek_token(tokens) == _COMMA:
        # Every further argument has a comma preceding it
        _pop_token(tokens, _COMMA)
        func_args.append(_parse_argument(tokens))
    _pop_token(tokens, _RPAREN)
    return ConditionFunc(func_name, func_args)

def _parse_argument(tokens: deque[_Token]) -> str | int | Comparison:
    """Parses the specified deque of tokens, returning an argument (which is
    either a string, a checksum or a comparison operator).

    :param tokens: The deque of tokens that should be parsed.
    :return: The parsed function call."""
    token = _pop_token(tokens)
    ttag = token.token_tag
    # Ordered by frequency - for performance
    if ttag == _STRING:
        return token.token_text[1:-1] # cut off the quotation marks
    elif ttag == _CHECKSUM:
        return int(token.token_text, base=16) # always hex
    elif ttag == _COMPARISON:
        return Comparison(token.token_text)
    else:
        raise ParserError(f'Unexpected token {ttag} - expected one of '
                          f'{[_CHECKSUM, _COMPARISON, _STRING]}',
            *token.debug_info)

def _peek_token(tokens: deque[_Token]) -> str:
    """Helper method to peek at the first token on the left side of the
    specified deque of tokens. Gracefully handles an empty deque by returning
    None. Note that unlike _pop_token, this returns the tag of the token
    directly, because peeking the tag is much more commonly needed than peeking
    the entire token.

    :param tokens: The deque of tokens to peek from.
    :return: The tag of the first token on the left side of the specified
        deque."""
    return tokens[0].token_tag if tokens else None

def _pop_token(tokens: deque[_Token],
        expected_tag: str | None = None) -> _Token:
    """Helper method to pop the first token on the left side of the specified
    deque of tokens. Can optionally check if the popped token's tag matches an
    expected tag. Raises an error if that is not the case or if no token can be
    popped (due to the deque being empty).

    :param tokens: The deque of tokens to pop from.
    :param expected_tag: The tag that we expect to pop. If set to a truthy
        value and the popped token's tag does not match this, an error will be
        raised.
    :return: The popped token."""
    if not tokens:
        raise ParserError(f'Attempted to pop a token '
                          f'({expected_tag if expected_tag else "ANY"}), '
                          f'but no tokens are left on the stack.\nMost '
                          f'likely, a character has been misplaced or a '
                          f'closing parenthesis is missing.')
    token = tokens.popleft()
    if expected_tag and token.token_tag != expected_tag:
        raise ParserError(f'Expected {expected_tag} token, but got '
                          f'{token.token_tag}', *token.debug_info)
    return token

# Implementation - Misc
def _merge_lists(first_list: dict[FName, _PluginEntry],
        second_list: dict[FName, _PluginEntry]):
    """Merges additions from the second masterlist into the first one. See
    _PluginEntry.merge_with for more information on the procedure. Entirely new
    entries are simply copied over instead of merged.

    :param first_list: The list to merge information into.
    :param second_list: The list to merge information from."""
    for plugin_name, second_entry in second_list.items():
        try:
            first_list[plugin_name].merge_with(second_entry)
        except KeyError:
            # This plugin had no entry in the first list, just copy it cover
            first_list[plugin_name] = second_entry

def _parse_list(list_path: Path) -> dict[FName, _PluginEntry]:
    """Parses the specified masterlist or userlist and returns a FNDict
    mapping plugins to _PluginEntry instances. To parse the YAML, PyYAML is
    used - the C version if possible.

    :param list_path: The path to the list that should be parsed.
    :return: A FNDict representing the list's contents."""
    with list_path.open('r', encoding='utf-8') as ins:
        list_contents = yaml.load(ins, Loader=SafeLoader)
    # The list contents may be None if the list file exists, but is an entirely
    # empty YAML file. Just return an empty dict in that case. Similarly, if
    # parsing the contents does not result in a dict (e.g. if the file is just
    # a long string of random characters), return an empty dict as well.
    if not isinstance(list_contents, dict):
        deprint(f'Masterlist file {list_path} is empty or invalid')
        return FNDict()
    return FNDict({p['name']: _PluginEntry(p) for p in
                   list_contents.get('plugins', ())})
