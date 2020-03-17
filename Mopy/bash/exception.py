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
"""This module contains all custom exceptions for Wrye Bash."""

import sys
import traceback
# NO LOCAL IMPORTS! This has to be importable from any module/package.

class BoltError(Exception):
    """Generic error with a string message."""
    def __init__(self, message):
        self.message = message
    def __str__(self):
        return self.message

def raise_bolt_error(msg, exc=BoltError):
    extype, ex, tb = sys.exc_info()
    formatted = traceback.format_exception_only(extype, ex)[-1]
    raise exc, u'%s caused by %s' % (msg, formatted), tb

# Code errors -----------------------------------------------------------------
class AbstractError(BoltError):
    """Coding Error: Abstract code section called."""
    def __init__(self, message=u'Abstract section called.'):
        super(AbstractError, self).__init__(message)

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
        ## type: (Union[Path, unicode], unicode) -> None
        super(FileError, self).__init__(message)
        self.in_name = in_name

    def __str__(self):
        return u'{}: {}'.format((self.in_name or u'Unknown File'),
                                self.message)

class SaveFileError(FileError):
    """Save File Error: File is corrupted."""
    pass

class FileEditError(BoltError):
    """Unable to edit a file"""
    def __init__(self, file_path, message=None):
        ## type: (Path, basestring) -> None
        message = message or (u'Unable to edit file {}.'.format(file_path.s))
        super(FileEditError, self).__init__(message)
        self.filePath = file_path

# Mod I/O Errors --------------------------------------------------------------
class ModError(FileError):
    """Mod Error: File is corrupted."""
    pass

class ModReadError(ModError):
    """Mod Error: Attempt to read outside of buffer."""
    def __init__(self, in_name, rec_type, try_pos, max_pos):
        ## type: (Path, basestring, int, int) -> None
        self.rec_type = rec_type
        self.try_pos = try_pos
        self.max_pos = max_pos
        if try_pos < 0:
            message = (u'{}: Attempted to read before ({}) beginning of '
                       u'file/buffer.'.format(rec_type, try_pos))
        else:
            message = (u'{}: Attempted to read past ({}) end ({}) of '
                       u'file/buffer.'.format(rec_type, try_pos, max_pos))
        super(ModReadError, self).__init__(in_name.s, message)

class ModSizeError(ModError):
    """Mod Error: Record/subrecord has wrong size."""
    def __init__(self, in_name, rec_type, expected_sizes, actual_size):
        """Indicates that a record or subrecord has the wrong size.

        :type in_name: bolt.Path
        :type rec_type: basestring
        :type expected_sizes: tuple[int]
        :type actual_size: int"""
        self.rec_type = rec_type
        self.expected_sizes = expected_sizes
        self.actual_size = actual_size
        message_form = (u'%s: Expected one of sizes [%s], but got %u' % (
            rec_type, u', '.join([u'%s' % x for x in expected_sizes]),
            actual_size))
        super(ModSizeError, self).__init__(in_name.s, message_form)

# Shell (OS) File Operation exceptions ----------------------------------------
class FileOperationError(OSError):
    def __init__(self, error_code, message=None):
        # type: (int, unicode) -> None
        self.errno = error_code
        Exception.__init__(self, u'FileOperationError: {}'.format(
                                    message or unicode(error_code)))

class AccessDeniedError(FileOperationError):
    def __init__(self):
        super(AccessDeniedError, self).__init__(5, u'Access Denied')

class InvalidPathsError(FileOperationError):
    def __init__(self, source, target): # type: (unicode, unicode) -> None
        super(InvalidPathsError, self).__init__(
            124, u'Invalid paths:\nsource: %s\ntarget: %s' % (source, target))

class DirectoryFileCollisionError(FileOperationError):
    def __init__(self, source, dest):  ## type: (Path, Path) -> None
        super(DirectoryFileCollisionError, self).__init__(
            -1, u'collision: moving {} to {}'.format(source, dest))

class NonExistentDriveError(FileOperationError):
    def __init__(self, failed_paths):  ## type: (List[Path]) -> None
        self.failed_paths = failed_paths
        super(NonExistentDriveError, self).__init__(-1, u'non existent drive')

# BSA exceptions --------------------------------------------------------------
class BSAError(FileError): pass

class BSACompressionError(BSAError):
    def __init__(self, in_name, compression_type, orig_error):
        # type: (unicode, unicode, Exception) -> None
        super(BSACompressionError, self).__init__(
            in_name, u'{} error while compressing record: {}'.format(
                compression_type, repr(orig_error)))

class BSADecodingError(BSAError):
    def __init__(self, in_name, message): # type: (unicode, unicode) -> None
        super(BSADecodingError, self).__init__(
            in_name, u'Undecodable string {!r}'.format(message))

class BSADecompressionError(BSAError):
    def __init__(self, in_name, compression_type, orig_error):
        # type: (unicode, unicode, Exception) -> None
        super(BSADecompressionError, self).__init__(
            in_name, u'{0} error while decompressing {0}-compressed record: '
                     u'{1}'.format(compression_type, repr(orig_error)))

class BSADecompressionSizeError(BSAError):
    def __init__(self, in_name, compression_type, expected_size, actual_size):
        super(BSADecompressionSizeError, self).__init__(
            in_name, u'{}-decompressed record size incorrect - expected {}, '
                     u'but got {}'.format(
                compression_type, expected_size, actual_size))

class BSAFlagError(BSAError):
    def __init__(self, in_name, message, flag):
        # type: (unicode, unicode, int) -> None
        super(BSAFlagError, self).__init__(
            in_name, u'{} (flag {}) unset'.format(message, flag))

# DDS exceptions --------------------------------------------------------------
class DDSError(Exception): pass

# Lexing/Parsing exceptions ---------------------------------------------------
class _ALPError(Exception):
    """Abstract base class for lexer and parser errors."""
    def __init__(self, err_msg, target_str=None, start_pos=-1, end_pos=-1,
                 line_num=-1):
        # type: (unicode, unicode, int, int) -> None
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
            final_msg += u'\nOccurred here: {}'.format(target_str)
        if start_pos >= 0:
            # Offset by -1 to account for the '^' part of the marker
            end_pos = start_pos if end_pos < 0 else end_pos - 1
            # The whitespace before the ^~~~~ marker
            marker_offset = u' ' * (15 + start_pos)
            # The actual ^~~~~ marker itself
            line_marker = u'^' + u'~' * (end_pos - start_pos)
            final_msg += u'\n{}{}'.format(marker_offset, line_marker)
        if line_num >= 0:
            final_msg += u'\nLine Number: {}'.format(
            line_num)
        super(_ALPError, self).__init__(final_msg)

class LexerError(_ALPError):
    """An error that ocurred during lexical analysis (lexing)."""

class ParserError(_ALPError):
    """An error that ocurred during parsing."""

# Misc exceptions -------------------------------------------------------------
class StateError(BoltError):
    """Error: Object is corrupted."""
    def __init__(self, message=u'Object is in a bad state.'):
        super(StateError, self).__init__(message)

class PluginsFullError(BoltError):
    """Usage Error: Attempt to add a mod to plugins when plugins is full."""
    def __init__(self, message=u'Load list is full.'):
        super(PluginsFullError, self).__init__(message)

class MasterMapError(BoltError):
    """Attempt to map a fid when mapping does not exist."""
    def __init__(self, modIndex):  # type: (int) -> None
        super(MasterMapError, self).__init__(
            u'No valid mapping for mod index 0x{:02X}'.format(modIndex))

class SaveHeaderError(Exception): pass

class InstallerArchiveError(BoltError): pass

# gui package exceptions ------------------------------------------------------
class GuiError(Exception):
    """Base class for exceptions thrown in the gui package."""
class UnknownListener(GuiError):
    """Trying to unsubscribe a listener that was not subscribed."""
class ListenerBound(GuiError):
    """Trying to bind a listener that is already subscribed to this event
    handler."""
