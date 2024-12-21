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
#  Wrye Bash copyright (C) 2005-2009 Wrye, 2010-2024 Wrye Bash Team
#  https://github.com/wrye-bash
#
# =============================================================================
"""This module contains all custom exceptions for Wrye Bash."""

import platform

# NO LOCAL IMPORTS! This has to be importable from any module/package.

class BoltError(Exception):
    """Generic error with a string message."""
    def __init__(self, message):
        self.message = message
    def __str__(self):
        return self.message

# Code errors -----------------------------------------------------------------
class ArgumentError(BoltError):
    """Coding Error: Argument out of allowed range of values."""
    def __init__(self, message=u'Argument is out of allowed ranged of values.'):
        super(ArgumentError, self).__init__(message)

# UI exceptions ---------------------------------------------------------------
class CancelError(BoltError):
    """User pressed 'Cancel' on the progress meter."""
    def __init__(self, message=u'Action aborted by user.'):
        super(CancelError, self).__init__(message)

class SkipError(CancelError):
    """User pressed Skipped n operations."""
    def __init__(self):
        super(SkipError, self).__init__(u'Action skipped by user.')

# File exceptions -------------------------------------------------------------
class FileError(BoltError):
    """An error that occurred while handling a file."""
    def __init__(self, in_name, message):
        super(FileError, self).__init__(message)
        self._in_name = (in_name and f'{in_name}') or 'Unknown File'

    def __str__(self):
        return f'{self._in_name}: {self.message}'

class SaveFileError(FileError):
    """Save File Error: File is corrupted."""
    pass

class FileEditError(BoltError): ##: never raised?
    """Unable to edit a file"""
    def __init__(self, file_path, message=None):
        ## type: (Path, str) -> None
        message = message or f'Unable to edit file {file_path}.'
        super(FileEditError, self).__init__(message)
        self.filePath = file_path

class FailedIniInferError(FileError):
    """Failed to infer INI type."""
    def __init__(self, in_name):
        super().__init__(in_name, 'Failed to infer INI type')

# Mod I/O Errors --------------------------------------------------------------
class ModError(FileError):
    """Mod Error: File is corrupted."""
    pass

def _join_sigs(debug_str):
    if isinstance(debug_str, bytes):
        debug_str = [debug_str]
    if isinstance(debug_str, (tuple, list)):
        from .bolt import sig_to_str # don't mind this we are in exception code
        debug_str = '.'.join(map(sig_to_str, debug_str))
    return debug_str

class ModReadError(ModError):
    """Mod Error: Attempt to read outside of buffer."""
    def __init__(self, in_name, debug_strs, try_pos, max_pos):
        ## type: (Path, str|bytes, int, int) -> None
        debug_str = _join_sigs(debug_strs)
        if try_pos < 0:
            message = f'{debug_str}: Attempted to read before ({try_pos}) ' \
                      f'beginning of file/buffer.'
        else:
            message = f'{debug_str}: Attempted to read past ({try_pos}) end ' \
                      f'({max_pos}) of file/buffer.'
        super(ModReadError, self).__init__(in_name, message)

class ModSizeError(ModError):
    """Mod Error: Record/subrecord has wrong size."""
    def __init__(self, in_name,
            debug_str: str | bytes | tuple[str | bytes, ...],
            expected_sizes: tuple[int, ...], actual_size: int):
        """Indicates that a record or subrecord has the wrong size.

        :type in_name: bolt.FName"""
        debug_str = _join_sigs(debug_str)
        message_form = (f'{debug_str}: Expected one of sizes '
                        f'{sorted(expected_sizes)}, but got {actual_size}')
        super().__init__(in_name, message_form)

class ModFidMismatchError(ModError):
    """Mod Error: Two FormIDs that should be equal are not."""
    def __init__(self, in_name, debug_str, fid_expected, fid_actual):
        debug_str = _join_sigs(debug_str)
        message_form = f'{debug_str}: FormIDs do not match - expected ' \
                       f'{fid_expected} but got {fid_actual}'
        super().__init__(in_name, message_form)

class ModSigMismatchError(ModError):
    """Mod Error: A record is getting overridden by a record with a different
    signature. This is undefined behavior."""
    def __init__(self, in_name, record):
        message_form = f'{record!r} is likely overriding or being ' \
                       f'overwritten by a record with the same FormID but a ' \
                       f'different type. This is undefined behavior and ' \
                       f'could lead to crashes.'
        super(ModSigMismatchError, self).__init__(in_name, message_form)


# BSA exceptions --------------------------------------------------------------
class BSAError(FileError): pass

class BSACompressionError(BSAError):
    def __init__(self, in_name, compression_type, orig_error):
        # type: (str, str, Exception) -> None
        super(BSACompressionError, self).__init__(in_name,
            f'{compression_type} error while compressing record: '
            f'{orig_error!r}')

class BSADecodingError(BSAError):
    def __init__(self, in_name: str, message: bytes | list[bytes]):
        super().__init__(in_name, f'Undecodable string(s) {message}')

class BSADecompressionError(BSAError):
    def __init__(self, in_name, compression_type, orig_error):
        # type: (str, str, Exception) -> None
        super(BSADecompressionError, self).__init__(
            in_name, u'{0} error while decompressing {0}-compressed record: '
                     u'{1}'.format(compression_type, repr(orig_error)))

class BSADecompressionSizeError(BSAError):
    def __init__(self, in_name, compression_type, expected_size, actual_size):
        super(BSADecompressionSizeError, self).__init__(in_name,
            f'{compression_type}-decompressed record size incorrect - '
            f'expected {expected_size}, but got {actual_size}')

class BSAFlagError(BSAError):
    def __init__(self, in_name, message, bsa_flag):
        # type: (str, str, int) -> None
        super(BSAFlagError, self).__init__(in_name,
            f'{message} (flag {bsa_flag}) unset')

# Cosave exceptions -----------------------------------------------------------
class CosaveError(FileError):
    """An error while handling cosaves."""

class InvalidCosaveError(CosaveError):
    """Invalid cosave."""
    def __init__(self, in_name, message):
        super(InvalidCosaveError, self).__init__(in_name,
                                                 f'Invalid cosave: {message}')

class UnsupportedCosaveError(CosaveError):
    """Unsupported cosave."""
    def __init__(self, in_name, message):
        super(UnsupportedCosaveError, self).__init__(in_name,
            f'Unsupported cosave: {message}')

# DDS exceptions --------------------------------------------------------------
class DDSError(Exception): pass

# Lexing/Parsing exceptions ---------------------------------------------------
class _ALPError(Exception):
    """Abstract base class for lexer and parser errors."""
    def __init__(self, err_msg: str, target_str: str | None = None,
            start_pos: int = -1, end_pos: int = -1, line_num: int = -1):
        """Creates a new error with the specified properties. All but err_msg
        are optional, and will simply add more details about where the error
        occurred.

        :param err_msg: The error message to show immediately after the error
            name.
        :param target_str: The string whose processing caused the error. Will
            be shown on a separate line after the error message.
        :param start_pos: The offset inside target_str at which the cause
            begins. Pointless without target_str. Adds a small '^' on a new
            line below the first problematic character in target_str.
        :param end_pos: The offset inside target_str at which the cause ends.
            Pointless without target_str and start_pos. Enhances the marker
            created by start_pos to show all problematic characters using the
            '^~~~' format commonly seen in compilers.
        :param line_num: The line number on which target_str was found. Will
            be shown on a separate line."""
        # Build up the final error message
        final_msg = err_msg
        if target_str:
            final_msg += f'\nOccurred here: {target_str}'
        if start_pos >= 0:
            # Offset by -1 to account for the '^' part of the marker
            end_pos = start_pos if end_pos < 0 else end_pos - 1
            # The whitespace before the ^~~~~ marker
            marker_offset = u' ' * (15 + start_pos)
            # The actual ^~~~~ marker itself
            line_marker = u'^' + u'~' * (end_pos - start_pos)
            final_msg += f'\n{marker_offset}{line_marker}'
        if line_num >= 0:
            final_msg += f'\nLine Number: {line_num}'
        super(_ALPError, self).__init__(final_msg)

class LexerError(_ALPError):
    """An error that occurred during lexical analysis (lexing)."""

class ParserError(_ALPError):
    """An error that occurred during parsing."""

class EvalError(_ALPError):
    """An error that occurred during the evaluation of some parsed code."""

class XMLParsingError(Exception):
    """An error that occurred during XML parsing."""

# Misc exceptions -------------------------------------------------------------
class InvalidPluginFlagsError(Exception):
    """Indicates that an attempt was made to create a plugin with invalid flags
    for the current game."""
    def __init__(self, flags):
        super().__init__(f'Attempted setting conflicting {flags=} to true')

class StateError(BoltError):
    """Error: Object is corrupted."""
    def __init__(self, message=u'Object is in a bad state.'):
        super(StateError, self).__init__(message)

class PluginsFullError(BoltError):
    """Usage Error: Attempt to add a mod to plugins when plugins is full."""
    def __init__(self, message=u'Load list is full.'):
        super(PluginsFullError, self).__init__(message)

class SkippedMergeablePluginsError(Exception):
    """Indicates that one or more mergeable plugins had to be skipped during a
    full load order activation."""

class MasterMapError(BoltError):
    """Attempt to map a fid when mapping does not exist."""
    def __init__(self, fid_to_map):
        super().__init__(f'No valid mapping for form id {fid_to_map!r}')

class SaveHeaderError(Exception): pass

class InstallerArchiveError(BoltError): pass

class EnvError(Exception):
    """Attempt to use a feature that is not available on this operating
    system."""
    def __init__(self, env_feature):
        super(EnvError, self).__init__(
            f"'{env_feature}' is not available on {platform.system()}")

class BPConfigError(Exception):
    """The configuration of the Bashed Patch is invalid in some way. Note that
    the error messages raised by this will be shown to the user in the GUI and
    so should be translated."""

# gui package exceptions ------------------------------------------------------
class GuiError(Exception):
    """Base class for exceptions thrown in the gui package."""
class UnknownListener(GuiError):
    """Trying to unsubscribe a listener that was not subscribed."""
class ListenerBound(GuiError):
    """Trying to bind a listener that is already subscribed to this event
    handler."""

# Web API errors --------------------------------------------------------------
class LimitReachedError(Exception):
    """Exception raised when the request rate limit has been reached."""
    def __init__(self):
        super().__init__('You have reached your request limit. Please wait '
                         'one hour before trying again.')

class RequestError(Exception):
    """Exception raised when a request returns an error code."""
    def __init__(self, status_code, msg):
        self.status_code = status_code
        self.orig_msg = msg
        super().__init__(f'Status Code {status_code} - {msg}')

class UnknownWebError(Exception):
    """Exception raised when some kind of error occurs in the underlying APIs
    used to establish connections etc."""
    def __init__(self):
        super().__init__('Failed to send request')

# Nexus API errrors -----------------------------------------------------------
class EndorsementError(Exception):
    """Base class for endorsement/disendorsement errors."""

class EndorsedWithoutDownloadError(EndorsementError):
    """Exception raised when a mod is endorsed or disendorsed without having
    been downloaded first."""

class EndorsedTooSoonError(EndorsementError):
    """Exception raised when a mod is endorsed or disendorsed without enough
    time having elapsed since it was downloaded."""
