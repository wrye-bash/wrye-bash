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
"""This module implements an event propagation framework on top of wx's
framework. The point here is that doing this allows us to build in some
convenience features to save a lot of code.

Note: You probably want to read this docstring in the actual file instead of in
the PyCharm popup, some parts break in the popup.

There are four main differences between this system and wx's:
  1. This one is mostly just syntax: We call 'callbacks' 'listeners',
     'binding' is 'subscribing' and 'triggering' an event is 'posting' an
     event. The reason for this change in terminology is to visually distance
     the code from wx, even just at a glance.
  2. Instead of passing wx's event classes directly to listeners, we apply
     'processors' to them beforehand. A good example is the text processor
     used for _ATextInput.on_text_changed. When a EVT_TEXT (i.e. text changed)
     event is triggered by wx, this processor is used to send the new text
     instead of the event itself to subscribers.
  3. We deviate from wx's default event behavior by always continuing to
     process listeners unless we are explicitly asked not to. In wx, this is
     the other way around - event.Skip() has to be called, unless you want to
     swallow the event (which is rarely wanted and can easily lead to bugs).
     Nearly all of WB's need for wx event objects was just to call
     event.Skip().
  4. Multiple listeners can subscribe to one event. wx allows just one binding,
     and attempting to bind a new callback will remove the old binding.

Subscribing:
  To subscribe to an event, simply call subscribe() on the EventHandler
  instance provided by the GUI component you're using. For example:
    >>> parent = # ...
    >>> def on_text(new_text):
    >>>     # do something with new_text here
    >>> from gui import TextArea
    >>> txt_area = TextArea(parent)
    >>> txt_area.on_text_changed.subscribe(on_text)
  Now, whenever the text changes in txt_area changes, on_text will get called
  with the new text. GUI components will always provide their event handlers
  with names following that scheme (on_something_happened). See also the next
  section.

Creating Event Handlers:
  If you're designing or modifying a GUI component and want to provide an event
  handler, you'll have to make a few decisions. This section will walk through
  an example for implementing a event handler for the EVT_SIZE event (triggered
  when a component is resized).
    1. Create the event handler inside your __init__. As mentioned above, the
       name should always follow the on_something_happened scheme, for
       consistency in the codebase and to make using event handlers easier:
         from gui import EventHandler
         # ...
         self.on_resized = self._evt_handler(_wx.EVT_SIZE)
    2. Decide what processor is needed. By default, null_processor is used,
       which will simply discard the event object. In this case, we can come up
       with a useful processor:
         def size_processor(event):
             return [event.width, event.height]
       This processor will transform the event into two integers. A matching
       listener might look like this:
         def on_author_field_resized(new_width, new_height):
             # rescale some components, wrap text, etc.
       Note that processors must always return a list. The list is then
       unpacked via Python's * operator and fed to the listeners.
    3. Pass the processor to the event handler (in your __init__):
         self.on_resized = self._evt_handler(_wx.EVT_SIZE, size_processor)
    4. You should place some documentation in the docstring of your GUI
       component's class indicating what events it offers and with what
       signatures to subscribe to them (note that I'm using # here, but these
       should be part of the docstring of your class):
         # Events:
         #  - on_resized(new_weight: int, new_height: int): Posted when this
         #    component is resized. ...
       Following the format indicated above is highly recommended for all GUI
       components.

Return Values:
  All listeners defined above have returned nothing. However, listeners may
  return one of three values defined in gui.events.EventResult. If nothing is
  returned, then EventHandler interprets this as the same as returning
  EventResult.CONTINUE, meaning that the event will simply be propagated to the
  next listener, if one exists. The three values are:
    1. EventResult.CONTINUE: Same as no return value. See above.
    2. EventResult.FINISH: Indicates that the event was successfully handled,
       but that it shouldn't be propagated to the next listener, if one exists.
    3. EventResult.CANCEL: Indicates that the event should not be allowed to
       execute. Only events that explicitly mention it in their documentation
       can be canceled, all others will raise a RuntimeError instead."""

__author__ = u'Infernio'

from enum import Enum

from ..exception import UnknownListener, ListenerBound
# no other imports, everything else needs to be able to import this

def null_processor(_event):
    """Argument processor that simply discards the event."""
    return []

class EventResult(Enum):
    """Implements the return values for EventHandler listeners."""
    CONTINUE = 0
    """This return value indicates that the event was successfully processed,
    but other listeners may still be interested in and capable of handling it.
    This is similar to calling event.Skip() in wx. It is default here because
    wx's default behavior can easily lead to bugs."""
    FINISH = 1
    """This return value indicates that the event was successfully processed
    and that no other listener needs to or can handle it. This is similar to
    the default behavior in wx."""
    CANCEL = 2
    """This return value indicates that the event should be canceled. Only
    events that clearly state so in their documentation may be canceled, all
    others will raise a RuntimeError instead."""

class _EHPauseSubcription(object):
    """Helper for EventHandler.pause_subscription."""
    def __init__(self, event_handler, listener):
        self._event_handler = event_handler
        self._listener = listener

    def __enter__(self):
        self._event_handler.unsubscribe(self._listener)

    def __exit__(self, exc_type, exc_val, exc_tb):
        self._event_handler.subscribe(self._listener)

class EventHandler(object):
    """This class implements the actual event processing, catching native wx
    events, applying processors to them and posting the results to all relevant
    listeners."""
    def __init__(self, wx_owner, wx_event_id, arg_processor):
        """Creates a new EventHandler wrapping the specified wx event.

        :param wx_owner: The wx object that the event is based on. This is what
                         Bind() will be called on.
        :param wx_event_id: The wx ID of the event in question. For example,
                            wx.EVT_TEXT.
        :param arg_processor: The processor that should be applied to the event
                              object before passing it on to the listeners."""
        self._arg_processor = arg_processor
        self._listeners = []
        self._wx_owner = wx_owner
        self._wx_event_id = wx_event_id
        self._is_bound = False

    def _post(self, event):
        """Catches a wx event, applies the argument processor and posts the
        result to all listeners that have subscribed to this event handler. The
        order in which the listeners are processed is guaranteed to be the same
        as the order in which they subscribed. Also checks the return value of
        the listener and reacts accordingly.

        :param event: The event that occurred."""
        listener_args = self._arg_processor(event)
        for listener in self._listeners:
            result = listener(*listener_args)
            # result will be None if method didn't return anything
            if result is None or result is EventResult.CONTINUE:
                continue
            elif result is EventResult.FINISH:
                return # to avoid event.Skip()
            elif result is EventResult.CANCEL:
                try:
                    event.Veto()
                    return # to avoid event.Skip()
                except AttributeError:
                    raise RuntimeError(u'An attempt was made to cancel a type '
                                       u'of event (%r) that cannot be '
                                       u'canceled.' % event.__class__)
            else:
                raise RuntimeError(u'Incorrect return value (%r) for '
                                   u'EventHandler listener.' % result)
        # Need to propagate it up the wx chain
        event.Skip()

    def subscribe(self, listener):
        """Subscribes the specified listener to this event handler. The order
        in which the listeners are processed is guaranteed to be the same as
        the order in which they subscribed.

        :param listener: The listener to subscribe."""
        if listener in self._listeners:
            raise ListenerBound(
                u'Listener %s already bound on %r' % (listener, self))
        self._listeners.append(listener)
        self._update_wx_binding()

    def unsubscribe(self, listener):
        """Unsubscribes the specified listener from this event handler.

        :param listener: The listener to unsubscribe."""
        try:
            self._listeners.remove(listener)
        except ValueError:
            raise UnknownListener(
                u'Listener %s not subscribed on %r' % (listener, self))
        self._update_wx_binding()

    def pause_subscription(self, listener):
        """Unsubscribe to the specified listener for this event handler,
           for use with a context manager (with statement).

           :param listener: The listener to unsubscribe."""
        return _EHPauseSubcription(self, listener)

    def _update_wx_binding(self):
        """Creates or removes a wx binding if necessary. If we have listeners
        but no wx binding, we have to create one. If we have no listeners but
        have a wx binding, we should unbind ourselves.

        We do this lazily to minimize the number of wx bindings we actually
        create, since each wx binding means more stress on wx's event
        system."""
        # Ordered to cater to the most common case in which the first if is
        # True (_is_bound is False and _listeners is nonempty)
        if not self._is_bound and self._listeners:
            self._wx_owner.Bind(self._wx_event_id, self._post)
            self._is_bound = True
        elif not self._listeners and self._is_bound:
            self._wx_owner.Unbind(self._wx_event_id)
            self._is_bound = False

    def __repr__(self):
        return u'%s(%s, %s)' % (
            type(self).__name__, self._wx_owner, self._wx_event_id)
