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
"""Common methods used by all platforms."""

import os
import stat
import sys
import warnings

def clear_read_only(filepath): # copied from bolt
    os.chmod(u'%s' % filepath, stat.S_IWUSR | stat.S_IWOTH)

# PY3: Remove, automatically done for us in the stdlib
_sentinel = object()
if sys.version_info >= (3,0):
    warnings.warn(u'Wrye Bash is running on Python 3, '
                  u'`set_env_var`, `get_env_var`, and `iter_env_vars` '
                  u'are no longer needed', DeprecationWarning)

    def _warn(deprecated_name, replacement_name):
        msg = u'Call to deprecated `%s`.  Use `%s` instead.' \
              % (deprecated_name, replacement_name)
        warnings.warn(msg, DeprecationWarning, stacklevel=2)

    # Mixed usages of bytes/unicode should be caught during our time
    # in Python 2, so only warn that these methods should be removed
    def set_env_var(env_key, env_value):
        _warn(u'set_env_var', u'os.environ[key] = value')
        os.environ[env_key] = env_value

    def get_env_var(env_key, default=_sentinel):
        if default is _sentinel:
            _warn(u'get_env_var', u'os.environ[key]')
            return os.environ[env_key]
        else:
            _warn(u'get_env_var', u'os.environ.get')
            return os.environ.get(env_key, default)

    def iter_env_vars():
        _warn(u'iter_env_vars', u'os.environ')
        return os.environ
else:
    # Python 2 version, encode/decode values, but warn if using bytes
    # to future proof for Python 3
    _fsencoding = sys.getfilesystemencoding()

    def _warn(msg):
        warnings.warn(msg, UnicodeWarning, stacklevel=2)

    def set_env_var(env_key, env_value):
        # Check for proper usage for the future Python 3:
        if isinstance(env_key, bytes):
            _warn(u'Environment variable keys should be unicode.')
        elif isinstance(env_key, unicode):
            # Expected, but os.environ uses bytes
            env_key = env_key.encode(_fsencoding)
        if isinstance(env_value, bytes):
            _warn(u'Environment variable values should be unicode.')
        elif isinstance(env_value, unicode):
            # Expceted, but os.environ uses bytes
            env_value = env_value.encode(_fsencoding)
        os.environ[env_key] = env_value

    def get_env_var(env_key, default=_sentinel):
        """Like os.environ.get and os.environ[key].  Here are the direct
           replacements:

           os.environ[key] -> get_env(key)
           os.environ.get(key) -> get_env(key, None)
           os.environ.get(key, default) -> get_env(key, default)
        """
        if isinstance(env_key, unicode):
            # Expected, but os.environ uses bytes
            env_key = env_key.encode(_fsencoding)
        elif isinstance(env_key, bytes):
            _warn(u'Environment variable keys should be unicode.')
        if default is _sentinel:
            # If no default is specified, act like os.environ[env_key]
            return os.environ[env_key].decode(_fsencoding)
        else:
            # Default specified, act like os.environ.get
            ret_val = os.environ.get(env_key, default)
            # default is commonly None, only decode bytes
            if isinstance(ret_val, bytes):
                ret_val.decode(_fsencoding)
            return ret_val

    def iter_env_vars():
        return (env_key.decode(_fsencoding) for env_key in os.environ)
