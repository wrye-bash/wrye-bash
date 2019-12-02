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
"""Wrye Bash **temporary** Python 2 to 3 migration module
   The utilities in here are meant as a temporary measure for some specific
   porting measures.  For example, what prompted this was replacing bolt.Path
   with pathlib.Path.
   
   To that end, most of the utilites in here are meant for use during a WIP
   refactorings, like function renames, to help catch any missed renames of
   usages.  For example, the @replaces wrapper is used to wrap the bolt.Path
   class with a dictionary of functions or attributes that have been renamed.
"""
## TODO(lojack): make sure this module is Python 2/3 compatible, as it may
##               remain in use until *after* the switch to 3.
from __future__ import print_function

import functools
import warnings
import inspect


def replaces(new_to_old_dict):
    """Wraps a class that has been refactored to be backwards compatible,
       but raise warnings when the old method names are called.

       new_to_old_dict is a dictionary mapping
         new_method_name : old_method_name

       The new method is untouched, but a wrapped copy is added to the
       class that redirects to the new name, but emits a warning.

       This is implemented as a class decorator rather than a function
       decorator because there is not a clean way to add new methods
       to the parent class when used as a function decorator.
    """
    def class_decorator(cls):
        if not inspect.isclass(cls):
            # For now, just a class wrapper
            raise TypeError(type(cls))
        # First define the decorator for the old functions
        def decorator(func, old_name):
            if func is None:
                return None
            msg = 'Call to deprecated function `{cls}.{old_name}`.' \
                  ' Use `{cls}.{new_name}` instead.'
            msg = msg.format(cls=cls.__name__,
                             old_name=old_name,
                             new_name=func.__name__)
            @functools.wraps(func)
            def wraps(*args, **kwargs):
                # Note: potential side effects by modifying logging filters,
                #       should we worry about this?
                # default -> show the warning only once per call site
                warnings.simplefilter('default', DeprecationWarning)
                warnings.warn(msg, category=DeprecationWarning,
                              stacklevel=2,  # Unwind the stack to the call site
                              )
                return func(*args, **kwargs)
            return wraps

        # iterate through all the new function names,
        # provide the old ones wrapped with the decorator
        for new_name, old_name in new_to_old_dict.iteritems():
            new_func = getattr(cls, new_name)
            if inspect.ismethod(new_func):
                if new_func.__self__ is cls:
                    # Class method
                    old_func = classmethod(decorator(new_func, old_name))
                    setattr(cls, old_name, old_func)
                else:
                    # Instance method
                    old_func = decorator(new_func, old_name)
                    setattr(cls, old_name, old_func)
            elif inspect.isfunction(new_func):
                # static method
                old_func = staticmethod(decorator(new_func, old_name))
                setattr(cls, old_name, old_func)
            elif isinstance(new_func, property):
                # property method
                old_func = property(decorator(new_func.fget, old_name),
                                    decorator(new_func.fset, old_name),
                                    decorator(new_func.fdel, old_name),
                                    )
                setattr(cls, old_name, old_func)
            else:
                warnings.warn(
                    '@replaces wrapper, class: %s, unknown function type: %s -> %s' % (
                        cls.__name__, new_name, type(new_func)))
        return cls
    return class_decorator
