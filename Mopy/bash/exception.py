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
#  Wrye Bash copyright (C) 2005-2009 Wrye, 2010-2015 Wrye Bash Team
#  https://github.com/wrye-bash
#
# =============================================================================
"""This module contains all custom exceptions for Wrye Bash."""

# NO LOCAL IMPORTS! This has to be importable from any module/package.

class BoltError(Exception):
    """Generic error with a string message."""
    def __init__(self, message):
        self.message = message
    def __str__(self):
        return self.message

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
    """TES4/Tes4SaveFile Error: File is corrupted."""
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

class PermissionError(BoltError):
    """Wrye Bash doesn't have permission to access the specified file/directory."""
    def __init__(self, message=u'Access is denied.'):
        super(PermissionError, self).__init__(message)

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
    def __init__(self, in_name, rec_type, read_size, max_size,
                 exact_size=True, old_skyrim=False):
        ## type: (Path, basestring, int, int, bool, bool) -> None
        self.rec_type = rec_type
        self.read_size = read_size
        self.max_size = max_size
        self.exact_size = exact_size
        if old_skyrim:
            message_form = (u'\nWrye Bash SSE expects a newer format for {} '
                            u'than found.\nLoad and save {} with the Skyrim '
                            u'SE CK\n'.format(rec_type, in_name))
        else: message_form = u''
        op = '==' if exact_size else '<='
        message_form += (u'{}: Expected size {} {}, but got: {}'
                         u''.format(rec_type, op, read_size, max_size))
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
            124, u'Invalid paths:\nsource: {}\ntarget: {}'.format(source, target))

class DirectoryFileCollisionError(FileOperationError):
    def __init__(self, source, dest):  ## type: (Path, Path) -> None
        super(DirectoryFileCollisionError, self).__init__(
            -1, u'collision: moving {} to {}'.format(source, dest))

class NonExistentDriveError(FileOperationError):
    def __init__(self, failed_paths):  ## type: (List[Path]) -> None
        self.failed_paths = failed_paths
        super(NonExistentDriveError, self).__init__(-1, u'non existent drive')

# BSA exceptions --------------------------------------------------------------
class BSAError(Exception): pass

class BSANotImplemented(BSAError): pass

class BSAVersionError(BSAError):
    def __init__(self, version, expected_version):
        super(BSAVersionError, self).__init__(
            u'Unexpected version {!r} - expected {!r}'.format(
                version, expected_version))

class BSAFlagError(BSAError):
    def __init__(self, message, flag):  # type: (unicode, int) -> None
        super(BSAFlagError, self).__init__(
            u'{} (flag {}) unset'.format(message, flag))

class BSADecodingError(BSAError):
    def __init__(self, text):  # type: (basestring) -> None
        super(BSADecodingError, self).__init__(
            u'Undecodable string {!r}'.format(text))

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
