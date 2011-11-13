# -*- coding: utf-8 -*-

"""This module provides the GUI interface for Wrye Bash."""

from bash.messages import *

import tkinter
import tkinter.font
from tkinter import ttk
##from tkinter import tix

from time import time
from queue import Empty as QueueEmpty
from imp import reload
import bisect
import os
##print(dir())
##print()

class CustomTooltip:
    def __init__(self, widget, textvariable):
        self.textvariable = textvariable
        self.on_widget = False
        self.tip_displayed = False
        self.widget = widget
        widget.bind('<Enter>', self.on_enter, '+')
        widget.bind('<Leave>', self.on_leave, '+')
        widget.bind('<Motion>', self.on_motion, '+')

    def on_enter(self, event=None):
        if self.on_widget: return
        self.xpos, self.ypos = event.x_root, event.y_root
        self.on_widget = True
        self.widget.after(700, self.display)

    def display(self):
        if self.on_widget and not self.tip_displayed:
            self.tip_displayed = True
            self.tip_placer = tkinter.Toplevel(self.widget, padx=1, pady=1, background='#FFFFDD')
            self.tip_placer.attributes('-alpha', 0.0, '-topmost', 1)
            self.tip_placer.overrideredirect(True)
            frame = ttk.Frame(self.tip_placer, relief='ridge', borderwidth=2)
            frame.pack()
            ttk.Label(frame, font='TkTooltipFont', textvariable=self.textvariable, background = '#FFFFDD').pack()
            self.fade_alpha = 0.0
            self.fade_in()

    def fade_in(self):
        self.fade_alpha += 0.15
        if self.fade_alpha >= 1.0:
            self.tip_placer.attributes('-alpha', 1.0)
            return
        self.tip_placer.geometry('+%d+%d' %(self.xpos+10, self.ypos+10))
        self.tip_placer.attributes('-alpha', self.fade_alpha)
        self.tip_placer.after(20, self.fade_in)

    def fade_out(self):
        self.fade_alpha -= 0.15
        if self.fade_alpha <= 0.0:
            self.tip_placer.attributes('-alpha', 0.0)
            self.tip_placer.destroy()
            return
        self.tip_placer.attributes('-alpha', self.fade_alpha)
        self.tip_placer.after(20, self.fade_out)

    def on_leave(self, event=None):
        self.on_widget = False
        if self.tip_displayed:
            self.tip_displayed = False
            self.fade_alpha = 1.0
            self.fade_out()

    def on_motion(self, event=None):
        if self.tip_displayed: return
        self.xpos, self.ypos = event.x_root, event.y_root

    def set(self, value):
        """Set the variable to VALUE."""
        self.textvariable.set(value)

    def get(self):
        """Return value of variable as string."""
        return self.textvariable.get()

class AutoScrollbar(ttk.Scrollbar):
    # a scrollbar that hides itself if it's not needed.  only
    # works if you use the grid geometry manager.
    def set(self, lo, hi):
        if float(lo) <= 0.0 and float(hi) >= 1.0:
            if getattr(self, '_needed', True):
                self.tk.call("grid", "propagate", self.winfo_parent(), 0) #prevents UI from constantly resizing
                self.tk.call("grid", "remove", self)
                self._needed = False
        else:
            if not getattr(self, '_needed', True):
                self.tk.call("grid", "propagate", self.winfo_parent(), 1)
                self.grid()
                self._needed = True
        ttk.Scrollbar.set(self, lo, hi)

    def pack(self, **kw):
        raise TclError("cannot use pack with this widget")

    def place(self, **kw):
        raise TclError("cannot use place with this widget")

def ScrolledWidget(widget_type, master, yscrolling, xscrolling, **widgetargs):
    if not (yscrolling or xscrolling):
        return (widget_type(master, **widgetargs), None)
    frame = ttk.Frame(master, borderwidth=2, relief=tkinter.SUNKEN)
    xscrollbar = yscrollbar = None
    if xscrolling:
        hsb = AutoScrollbar(frame, orient=tkinter.HORIZONTAL)
        hsb.grid(column=0, row=1, sticky='ew', in_=frame)
        widgetargs['xscrollcommand'] = hsb.set
    if yscrolling:
        vsb = AutoScrollbar(frame, orient=tkinter.VERTICAL)
        vsb.grid(column=1, row=0, sticky='ns', in_=frame)
        widgetargs['yscrollcommand'] = vsb.set
    if 'bd' not in widgetargs:
        widgetargs['bd'] = 0
    widget = widget_type(frame, **widgetargs)
    widget.grid(column=0, row=0, sticky='nsew', in_=frame)
    frame.grid_columnconfigure(0, weight=1)
    frame.grid_rowconfigure(0, weight=1)
    if xscrolling:
        hsb.config(command=widget.xview)
    if yscrolling:
        vsb.config(command=widget.yview)
    return (widget, frame)

class CustomText(tkinter.Text):
    def __init__(self, master, **args):
        self.char_limit = args.get('maxchars',None)
        self.user_on_modified = args.get('onmodified',None)
        self.initial_text = args.get('text',None)
        if 'text' in args: del args['text']
        if 'maxchars' in args: del args['maxchars']
        if 'onmodified' in args: del args['onmodified']
        if self.char_limit: #account for null terminator
            self.char_limit -= 1

        tkinter.Text.__init__(self, master, **args)

        if self.initial_text: self.insert(1.0, self.initial_text)
        self.changed(False)
        self.bind('<<Modified>>', self.on_modified)
        self.bind('<Control-a>', self.select_all)

    def show_context(self, event):
        self.focus()
        self.context_menu.post(event.x_root, event.y_root)

    def select_all(self, event=None):
        event.widget.tag_add('sel','1.0','end -1 chars')#account for newline that tk always adds
        event.widget.mark_set('insert', '1.0')
        event.widget.see('insert')
        return 'break'

    def on_modified(self, event=None):
        if self._on_modified: return
        self.changed(False)
        text = self.get(1.0, 'end')[:-1]#account for newline that tk always adds
        if self.char_limit:
            diff = len(text) - self.char_limit
            if diff > 0:
                #should the results be truncated, the new text rejected (and error sound invoked), or what?
                #atm, results truncated on copy, and rejected on typing
                if diff == 1:
                    pos = self.index('insert -1 chars')
                    text = self.last_good
                if diff > 1:
                    pos = 'end'
                    text = text[:self.char_limit]
                self.delete(1.0, 'end')
                self.insert('end', text)
                self.mark_set('insert', pos)
                self.see(pos)
        if self.user_on_modified:
            self.user_on_modified(initial_text,text)
        self.last_good = text

    def changed(self, changed_flag=True):
        self._on_modified = not changed_flag #allow changed(True) to indirectly call on_modified, but block it on changed(False)
        self.tk.call(self._w, 'edit', 'modified', 1 if changed_flag else 0)
        self._on_modified = False

class CustomTextEntry(ttk.Entry):
    def __init__(self, master, **args):
        self.char_limit = args.get('maxchars',None)
        self.user_on_modified = args.get('onmodified',None)
        self.initial_text = args.get('text',None)
        self.validatecommand = args.get('validatecommand',None)
        self.invalidcommand = args.get('invalidcommand',None)

        if 'text' in args: del args['text']
        if 'maxchars' in args: del args['maxchars']
        if 'onmodified' in args: del args['onmodified']
        if 'validatecommand' in args: del args['validatecommand']
        if 'invalidcommand' in args: del args['invalidcommand']

        if self.user_on_modified and 'validate' not in args:
            args['validate'] = 'all'
        #vcmd = (self.root.register(self.OnValidate), '%d', '%i', '%P', '%s', '%S', '%v', '%V', '%W')

        args['validatecommand'] = self.is_valid
        args['invalidcommand'] = self.sanitize
        ttk.Entry.__init__(self, master, **args)

        if self.initial_text: self.insert(0.0, self.initial_text)

    def show_context(self, event):
        #s = ttk.Style()
        #print(s.theme_use())
        #print(s.theme_names())
        #self.theme_test = getattr(self, 'theme_test', 0)
        #s.theme_use(s.theme_names()[self.theme_test])
        #print(s.theme_names()[self.theme_test])
        #self.theme_test += 1
        #if self.theme_test >= len(s.theme_names()):
        #    self.theme_test = 0
        self.focus()
        self.context_menu.post(event.x_root, event.y_root)

    def is_valid(self):
        if self.validatecommand and not self.validatecommand():
            return False
        text = self.get()
        if self.char_limit and len(text) > self.char_limit:
            return False
        if self.user_on_modified:
            self.user_on_modified(initial_text,text)
        return True

    def sanitize(self):
        if self.invalidcommand:
            self.invalidcommand()
        text = self.get()
        text = text[:self.char_limit]
        self.delete(0.0, 'end')
        self.insert(0.0, text)

class CustomListView(ttk.Treeview):
    def __init__(self,
                 window,
                 columns,
                 get_data,
                 set_data,
                 activate_items,
                 deactivate_items,
                 active_tag,
                 inactive_tag,
                 refresh_item,
                 **args):
        args['show'] = 'headings'
        self.get_data = get_data
        self.raw_columns = columns
        self.column_ids = [id for id, name in columns]
        ttk.Treeview.__init__(self, window, **args)
        self.bind('<ButtonPress-3>', self.select_item)
        self.reversed_columns = set()
        self.build_tree()
        self._set_data = set_data
        self._activate_items = activate_items
        self._deactivate_items = deactivate_items
        self._refresh_item = refresh_item
        self.active_tag = active_tag
        self.inactive_tag = inactive_tag
        self.bind('<Double-ButtonRelease-1>', self.toggle_items)
        self.bind('<Control-Key-Up>', lambda event, direction='UP': self.reorder_items(event, direction))
        self.bind('<Control-Key-Down>', lambda event, direction='DOWN': self.reorder_items(event, direction))

    def set_data(self, data):
        self._set_data(data)

    def reorder_items(self, event, direction):
        selected = self.selection()
        if not selected: return
        all_items = list(self.get_children(''))
        max_index = len(all_items)
        did_reorder = False
        give_focus = selected[0]
        for item in selected:
            old_index = all_items.index(item)
            if direction == 'UP':
                new_index = old_index - 1
            else:
                new_index = old_index + 1
            if new_index < 0:
                continue
            if new_index >= max_index:
                continue
            all_items.pop(old_index)
            all_items.insert(new_index, item)
            self.move(item, '', new_index)
            did_reorder = True
        if did_reorder:
            self._set_data(all_items)
            self.selection_set(selected)
            self.focus(give_focus)
            self.refresh_items(all_items)
        return "break"

    def refresh_items(self, items):
        for item in items:
            item_data = self._refresh_item(item)
            item_values = [item_data.get(id,'') for id in self.column_ids]
            self.item(item, values=item_values)

    def toggle_items(self, event):
        if self.identify_region(event.x, event.y) != 'cell': return
        selected = self.selection()
        do_activate = False
        do_deactivate = False
        for item in selected:
            if self.tag_has(self.active_tag, item):
                do_deactivate = True
            if self.tag_has(self.inactive_tag, item):
                do_activate = True
            if do_deactivate and do_activate: #Mixed selection
                return #Do nothing
        if do_activate:
            self.activate_items(selected)
        else:
            self.deactivate_items(selected)
        self.refresh_items(selected)

    def activate_items(self, items):
        self.tk.call(self._w, 'tag','remove',self.inactive_tag, items)
        self.tk.call(self._w, 'tag','add',self.active_tag, items)
        self._activate_items(items)

    def deactivate_items(self, items):
        self.tk.call(self._w, 'tag','add',self.inactive_tag, items)
        self.tk.call(self._w, 'tag','remove',self.active_tag, items)
        self._deactivate_items(items)

    def select_item(self, event):
        identity = self.identify_row(event.y)
        if identity:
            self.selection_set('"%s"' % (identity),)
        return "continue"

    def build_tree(self):
        column_ids = self.column_ids
        self.configure(columns=column_ids)
        for id,name in self.raw_columns:
            self.heading(id, text=name, command=lambda c=id: self.sortby(c))
            self.column(id, width=tkinter.font.Font().measure(name))
        tree_data = self.get_data()
        for item in tree_data:
            item_values = [item.get(id,'') for id in self.column_ids]
            item_tags = item.get('tags',[])
            self.insert('', 'end', values=item_values, iid=item['id'], tags=item_tags)
            # adjust columns lengths if necessary
            for indx, val in enumerate(item_values):
                ilen = tkinter.font.Font().measure(val)
                if self.column(column_ids[indx], width=None) < ilen:
                    self.column(column_ids[indx], width=ilen)

    def sortby(self, col):
        """Sort tree contents when a column is clicked on."""
        return
        #temporarily disabled
##        descending = col in self.reversed_columns
##        # grab values to sort
##        data = [(self.set(child, col), child) for child in self.get_children('')]
##        # reorder data
##        data.sort(reverse=descending)
##        for indx, item in enumerate(data):
##            self.move(item[1], '', indx)
##
##        if descending:
##            print('Descend sort!')
##            self.reversed_columns.remove(col)
##        else:
##            print('Ascend sort!')
##            self.reversed_columns.add(col)

class Sanitizer:
    """Collection of static methods for sanitizing messages."""
    @staticmethod
    def no_validation(value):
        return value

    @staticmethod
    def tkinter_bool(value):
        return tkinter.TRUE if value else tkinter.FALSE

    @staticmethod
    def tkinter_bool_empty(value):
        return tkinter.FALSE if not value else '' if value == '' else tkinter.TRUE

    @staticmethod
    def tkinter_int_or_empty(value):
        return '' if value == '' else int(value)

    @staticmethod
    def tkinter_tuple(valuetypes, values):
        return tuple(valuetype(value) for valuetype, value in zip(valuetypes, values))

    tkinter_relief_values = {'RAISED':tkinter.RAISED,
                             'SUNKEN':tkinter.SUNKEN,
                             'FLAT':tkinter.FLAT,
                             'RIDGE':tkinter.RIDGE,
                             'GROOVE':tkinter.GROOVE,
                             'SOLID':tkinter.SOLID}
    @staticmethod
    def tkinter_relief(value):
        return Sanitizer.tkinter_relief_values.get(value, tkinter.FLAT)

    tkinter_focusmodel_values = {'ACTIVE':'active',
                                 'PASSIVE':'passive'}
    @staticmethod
    def tkinter_focusmodel(value):
        return Sanitizer.tkinter_focusmodel_values.get(value, 'passive')

    tkinter_window_state_values = {'NORMAL':'normal',
                                   'ICONIC':'iconic',
                                   'WITHDRAWN':'withdrawn',
                                   'ZOOMED':'zoomed'}
    tkinter_window_state_values.update({'!%s' % (key,):'!%s' % (value,) for key, value in tkinter_window_state_values.items()})
    @staticmethod
    def tkinter_window_state(value):
        return Sanitizer.tkinter_window_state_values.get(value, 'normal')

    tkinter_menu_state_values = {'NORMAL':'normal',
                                 'ACTIVE':'active',
                                 'DISABLED':'disabled'}
    tkinter_menu_state_values.update({'!%s' % (key,):'!%s' % (value,) for key, value in tkinter_menu_state_values.items()})
    @staticmethod
    def tkinter_menu_state(value):
        return Sanitizer.tkinter_menu_state_values.get(value, 'normal')

    tkinter_fill_values = {'X':tkinter.X,
                           'Y':tkinter.Y,
                           'BOTH':tkinter.BOTH,
                           'NONE':tkinter.NONE}

    @staticmethod
    def tkinter_fill(value):
        return Sanitizer.tkinter_fill_values.get(value, tkinter.NONE)

    tkinter_side_values = {'LEFT':tkinter.LEFT,
                           'TOP':tkinter.TOP,
                           'RIGHT':tkinter.RIGHT,
                           'BOTTOM':tkinter.BOTTOM}

    @staticmethod
    def tkinter_side(value):
        return Sanitizer.tkinter_side_values.get(value, tkinter.TOP)

    tkinter_text_state_values = {'NORMAL':'normal',
                                 'DISABLED':'disabled'}
    tkinter_text_state_values.update({'!%s' % (key,):'!%s' % (value,) for key, value in tkinter_text_state_values.items()})
    @staticmethod
    def tkinter_text_state(value):
        return Sanitizer.tkinter_text_state_values.get(value, 'normal')

    tkinter_text_tabstyle_values = {'TABULAR':'tabular',
                                    'WORDPROCESSOR':'wordprocessor'}

    @staticmethod
    def tkinter_text_tabstyle(value):
        return Sanitizer.tkinter_text_tabstyle_values.get(value, 'tabular')

    tkinter_text_wrap_values = {'NONE':'none',
                                'CHAR':'char',
                                'WORD':'word'}

    @staticmethod
    def tkinter_text_wrap(value):
        return Sanitizer.tkinter_text_wrap_values.get(value, 'word')

    ttk_sticky_values = {'N':tkinter.N,'S':tkinter.S,
                         'E':tkinter.E,'W':tkinter.W,
                         'NW':tkinter.NW,'SW':tkinter.SW,
                         'NE':tkinter.NE,'SE':tkinter.SE,
                         'NS':tkinter.NS,'EW':tkinter.EW,
                         'NSEW':tkinter.NSEW}

    @staticmethod
    def ttk_sticky(value):
        return Sanitizer.ttk_sticky_values.get(value, tkinter.NSEW)

    ttk_anchor_values = {'N':tkinter.N,'S':tkinter.S,
                         'E':tkinter.E,'W':tkinter.W,
                         'NW':tkinter.NW,'SW':tkinter.SW,
                         'NE':tkinter.NE,'SE':tkinter.SE,
                         'CENTER':tkinter.CENTER}

    @staticmethod
    def ttk_anchor(value):
        return Sanitizer.ttk_anchor_values.get(value, tkinter.CENTER)

    ttk_labelframe_anchor_values = {'NW':tkinter.NW,
                                    'N':tkinter.N,
                                    'NE':tkinter.NE,
                                    'EN':'en',
                                    'E':tkinter.E,
                                    'ES':'es',
                                    'SE':tkinter.SE,
                                    'S':tkinter.S,
                                    'SW':tkinter.SW,
                                    'WS':'ws',
                                    'W':tkinter.W,
                                    'WN':'wn'}

    @staticmethod
    def ttk_labelframe_anchor(value):
        return Sanitizer.ttk_labelframe_anchor_values.get(value, tkinter.NW)

    ttk_tab_state_values = {'NORMAL':'normal',
                            'HIDDEN':'hidden',
                            'DISABLED':'disabled'}
    ttk_tab_state_values.update({'!%s' % (key,):'!%s' % (value,) for key, value in ttk_tab_state_values.items()})
    @staticmethod
    def ttk_tab_state(value):
        return Sanitizer.ttk_tab_state_values.get(value, 'normal')

    tkinter_compound_values = {'CENTER':tkinter.CENTER,
                               'TOP':tkinter.TOP,
                               'BOTTOM':tkinter.BOTTOM,
                               'LEFT':tkinter.LEFT,
                               'RIGHT':tkinter.RIGHT,
                               'NONE':tkinter.NONE}
    @staticmethod
    def tkinter_compound(value):
        return Sanitizer.tkinter_compound_values.get(value, tkinter.NONE)

    ttk_compound_values = {'TEXT':'text',
                           'IMAGE':'image',
                           'CENTER':tkinter.CENTER,
                           'TOP':tkinter.TOP,
                           'BOTTOM':tkinter.BOTTOM,
                           'LEFT':tkinter.LEFT,
                           'RIGHT':tkinter.RIGHT,
                           'NONE':tkinter.NONE}
    @staticmethod
    def ttk_compound(value):
        return Sanitizer.ttk_compound_values.get(value, tkinter.NONE)

    ttk_button_default_values = {'NORMAL':'normal',
                                 'ACTIVE':'active',
                                 'DISABLED':'disabled'}
    @staticmethod
    def ttk_button_default(value):
        return Sanitizer.ttk_button_default_values.get(value, 'normal')

    @staticmethod
    def ttk_image(values):
        #Specifies an image to display.
        #This is a list of 1 or more elements.
        #The first element is the default image name.
        #The rest of the list is a sequence of statespec / value pairs as per style map,
        # specifying different images to use when the widget is in a particular state
        # or combination of states.
        #All images in the list should have the same size.
        #Format:
        # (('state',...,image_id),...) where the default image has no 'state's
        imagespec = []
        for states in values:
            image_id = states[-1]
            states = [Sanitizer.ttk_standard_state(state) for state in states[:-1]]

            if not len(states):
                imagespec.insert(0, image_id)
            else:
                state_str = ' '.join(states)
                if len(states) > 1:
                    state_str = '{%s } %s' % (state_str, image_id)
                else:
                    state_str = '%s %s' % (state_str, image_id)
                imagespec.append(state_str)
        if len(imagespec) > 1:
            imagespec[0] = imagespec[0] + ' '
        return ''.join(imagespec)

    ttk_standard_state_values = {'ACTIVE':tkinter.ACTIVE,
                                 'DISABLED':tkinter.DISABLED,
                                 'FOCUS':'focus',
                                 'PRESSED':'pressed',
                                 'SELECTED':'selected',
                                 'BACKGROUND':'background',
                                 'READONLY':'readonly',
                                 'ALTERNATE':'alternate',
                                 'INVALID':'invalid',
                                 'HOVER':'hover'}
    ttk_standard_state_values.update({'!%s' % (key,):'!%s' % (value,) for key, value in ttk_standard_state_values.items()})
    @staticmethod
    def ttk_standard_state(value):
        return Sanitizer.ttk_standard_state_values.get(value, '!disabled')

    ttk_label_justify_values = {'LEFT':'left',
                                'CENTER':'center',
                                'RIGHT':'right'}
    @staticmethod
    def ttk_label_justify(value):
        return Sanitizer.ttk_label_justify_values.get(value, 'left')

    ttk_frame_separator_orient_values = {'HORIZONTAL':'horizontal',
                                         'VERTICAL':'vertical'}
    @staticmethod
    def ttk_frame_separator_orient(value):
        return Sanitizer.ttk_frame_separator_orient_values.get(value, 'vertical')

    ttk_list_selectmode_values = {'EXTENDED':'extended',
                                  'BROWSE':'browse',
                                  'NONE':'none'}
    @staticmethod
    def ttk_list_selectmode(value):
        return Sanitizer.ttk_list_selectmode_values.get(value, 'extended')

    ttk_text_entry_justify_values = {'LEFT':'left',
                                     'CENTER':'center',
                                     'RIGHT':'right'}
    @staticmethod
    def ttk_text_entry_justify(value):
        return Sanitizer.ttk_text_entry_justify_values.get(value, 'left')

    ttk_text_entry_state_values = {'NORMAL':'normal',
                                   'DISABLED':'disabled',
                                   'READONLY':'readonly'}
    ttk_text_entry_state_values.update({'!%s' % (key,):'!%s' % (value,) for key, value in ttk_text_entry_state_values.items()})
    @staticmethod
    def ttk_text_entry_state(value):
        return Sanitizer.ttk_text_entry_state_values.get(value, 'normal')

    ttk_text_entry_validate_values = {'FOCUS':'focus',
                                      'FOCUSIN':'focusin',
                                      'FOCUSOUT':'focusout',
                                      'KEY':'key',
                                      'ALL':'all',
                                      'NONE':'none'}
    @staticmethod
    def ttk_text_entry_validate(value):
        return Sanitizer.ttk_text_entry_validate_values.get(value, 'none')

    @staticmethod
    def sanitize(args, ttkinter_type):
        coerce_values, aliases = ttkinter_type
        sanitized = {}
        for key, value in args.items():
            key = key.lower()
            if key in aliases and aliases[key] in sanitized: continue
            if key in coerce_values:
                try:
                    sanitized[key] = coerce_values[key](value)
                except:
                    print(args, ttkinter_type)
                    print(key, value)
                    raise
        return sanitized

    tkinter_window_args = {'aspect':lambda x: Sanitizer.tkinter_tuple((tkinter_int_or_empty,) * 4, x),
                           'fullscreen':lambda x: Sanitizer.tkinter_bool(x),
                           'topmost':lambda x: Sanitizer.tkinter_bool(x),
                           'alpha':float,
                           'disabled':lambda x: Sanitizer.tkinter_bool(x),
                           'toolwindow':lambda x: Sanitizer.tkinter_bool(x),
                           'transparentcolor':lambda x: Sanitizer.no_validation(x),
                           'deiconify':lambda x: Sanitizer.tkinter_bool(x),
                           'focusmodel':lambda x: Sanitizer.tkinter_focusmodel(x),
                           'iconbitmap':lambda x: Sanitizer.no_validation(x), #resource_id
                           'iconify':lambda x: Sanitizer.tkinter_bool(x),
                           'iconposition':lambda x: Sanitizer.tkinter_tuple((tkinter_int_or_empty,) * 2, x),
                           'maxsize':lambda x: Sanitizer.tkinter_tuple((int,) * 2, x),
                           'minsize':lambda x: Sanitizer.tkinter_tuple((int,) * 2, x),
                           'WM_DELETE_WINDOW':lambda x: Sanitizer.no_validation(x), #action_resource_id
                           'resizable':lambda x: Sanitizer.tkinter_tuple((Sanitizer.tkinter_bool,) * 2, x),
                           'state':lambda x: Sanitizer.tkinter_window_state(x),
                           'title':lambda x: Sanitizer.no_validation(x)} #resource_id

    tkinter_standard_args = {'cursor':lambda x: Sanitizer.no_validation(x),
                             'takefocus':lambda x: Sanitizer.tkinter_bool_empty(x)}

    tkinter_root_args = {'borderwidth':int,
                         'bd':int,
                         'relief':lambda x: Sanitizer.tkinter_relief(x),
                         'padx':int,
                         'pady':int,
                         'width':int,
                         'height':int,
                         'menu':lambda x: Sanitizer.no_validation(x), #resource_id
                         'background':lambda x: Sanitizer.no_validation(x),
                         'bg':lambda x: Sanitizer.no_validation(x),
                         'highlightbackground':lambda x: Sanitizer.no_validation(x),
                         'highlightcolor':lambda x: Sanitizer.no_validation(x),
                         'highlightthickness':int}
    tkinter_root_args.update(tkinter_standard_args)
    tkinter_root_aliases = {'borderwidth':'bd', 'background':'bg',
                            'bd':'borderwidth', 'bg':'background'}

    tkinter_pack_args = {'after':lambda x: Sanitizer.no_validation(x),
                         'anchor':lambda x: Sanitizer.ttk_anchor(x),
                         'before':lambda x: Sanitizer.no_validation(x),
                         'expand':lambda x: Sanitizer.tkinter_bool(x),
                         'fill':lambda x: Sanitizer.tkinter_fill(x),
                         'in_':lambda x: Sanitizer.no_validation(x),
                         'ipadx':int,
                         'ipady':int,
                         'padx':int,
                         'pady':int,
                         'side':lambda x: Sanitizer.tkinter_side(x)}

    tkinter_menu_args = {'activebackground':lambda x: Sanitizer.no_validation(x),
                         'activeborderwidth':int,
                         'activeforeground':lambda x: Sanitizer.no_validation(x),
                         'background':lambda x: Sanitizer.no_validation(x),
                         'bg':lambda x: Sanitizer.no_validation(x),
                         'borderwidth':int,
                         'bd':int,
                         'disabledforeground':lambda x: Sanitizer.no_validation(x),
                         'font':lambda x: Sanitizer.no_validation(x),
                         'foreground':lambda x: Sanitizer.no_validation(x),
                         'fg':lambda x: Sanitizer.no_validation(x),
                         'relief':lambda x: Sanitizer.tkinter_relief(x),
                         'postcommand':lambda x: Sanitizer.no_validation(x), #action_resource_id
                         'selectcolor':lambda x: Sanitizer.no_validation(x),
                         'tearoff':lambda x: Sanitizer.tkinter_bool(x),
                         'tearoffcommand':lambda x: Sanitizer.no_validation(x), #action_resource_id
                         'title':lambda x: Sanitizer.no_validation(x)} #resource_id
    tkinter_menu_aliases = {'borderwidth':'bd', 'background':'bg', 'foreground':'fg',
                            'bd':'borderwidth', 'bg':'background', 'fg':'foreground'}
    tkinter_menu_args.update(tkinter_standard_args)
    tkinter_menu_custom_args = {'post_up':lambda x: Sanitizer.tkinter_bool(x)}

    tkinter_menu_separator_args = {'columnbreak':lambda x: Sanitizer.tkinter_bool(x),
                                   'hidemargin':lambda x: Sanitizer.tkinter_bool(x)}

    tkinter_menu_command_args = {'activebackground':lambda x: Sanitizer.no_validation(x),
                                 'activeforeground':lambda x: Sanitizer.no_validation(x),
                                 'accelerator':lambda x: Sanitizer.no_validation(x), #need to auto-bind on creation
                                 'background':lambda x: Sanitizer.no_validation(x),
                                 'bitmap':lambda x: Sanitizer.no_validation(x), #resource_id
                                 'columnbreak':lambda x: Sanitizer.tkinter_bool(x),
                                 'command':lambda x: Sanitizer.no_validation(x), #resource_id
                                 'compound':lambda x: Sanitizer.tkinter_compound(x),
                                 'font':lambda x: Sanitizer.no_validation(x),
                                 'foreground':lambda x: Sanitizer.no_validation(x),
                                 'hidemargin':lambda x: Sanitizer.tkinter_bool(x),
                                 'image':lambda x: Sanitizer.no_validation(x), #resource_id
                                 'label':lambda x: Sanitizer.no_validation(x), #resource_id
                                 'state':lambda x: Sanitizer.tkinter_menu_state(x),
                                 'underline':int}

    tkinter_menu_checkbutton_args = {'indicatoron':lambda x: Sanitizer.tkinter_bool(x),
                                     'offvalue':lambda x: Sanitizer.no_validation(x),
                                     'onvalue':lambda x: Sanitizer.no_validation(x),
                                     'variable':lambda x: Sanitizer.no_validation(x), #resource_id
                                    }
    tkinter_menu_checkbutton_args.update(tkinter_menu_command_args)

    tkinter_menu_cascade_args = {'menu':lambda x: Sanitizer.no_validation(x), #resource_id
                                }
    tkinter_menu_cascade_args.update(tkinter_menu_command_args)

    tkinter_text_args = {'background':lambda x: Sanitizer.no_validation(x),
                         'bg':lambda x: Sanitizer.no_validation(x),
                         'borderwidth':int,
                         'bd':int,
                         'exportselection':lambda x: Sanitizer.tkinter_bool(x),
                         'font':lambda x: Sanitizer.no_validation(x),
                         'foreground':lambda x: Sanitizer.no_validation(x),
                         'fg':lambda x: Sanitizer.no_validation(x),
                         'highlightbackground':lambda x: Sanitizer.no_validation(x),
                         'highlightcolor':lambda x: Sanitizer.no_validation(x),
                         'highlightthickness':int,
                         'insertbackground':lambda x: Sanitizer.no_validation(x),
                         'insertborderwidth':int,
                         'insertofftime':int,
                         'insertontime':int,
                         'insertwidth':int,
                         'padx':int,
                         'pady':int,
                         'relief':lambda x: Sanitizer.tkinter_relief(x),
                         'selectbackground':lambda x: Sanitizer.no_validation(x),
                         'selectborderwidth':int,
                         'selectforeground':lambda x: Sanitizer.no_validation(x),
                         'setgrid':lambda x: Sanitizer.tkinter_bool(x),
                         ##'xscrollcommand':lambda x: Sanitizer.no_validation(x), #resource_id
                         ##'yscrollcommand':lambda x: Sanitizer.no_validation(x), #resource_id
                         'autoseparators':lambda x: Sanitizer.tkinter_bool(x),
                         'blockcursor':lambda x: Sanitizer.tkinter_bool(x),
                         'endline':int,
                         'height':int,
                         'inactiveselectbackground':lambda x: Sanitizer.no_validation(x),
                         'maxundo':int,
                         'spacing1':int,
                         'spacing2':int,
                         'spacing3':int,
                         'startline':int,
                         'state':lambda x: Sanitizer.tkinter_text_state(x),
                         'tabs':lambda x: Sanitizer.no_validation(x),
                         'tabstyle':lambda x: Sanitizer.tkinter_text_tabstyle(x),
                         'undo':lambda x: Sanitizer.tkinter_bool(x),
                         'width':int,
                         'wrap':lambda x: Sanitizer.tkinter_text_wrap(x)}
    tkinter_text_aliases = {'borderwidth':'bd', 'background':'bg', 'foreground':'fg',
                            'bd':'borderwidth', 'bg':'background', 'fg':'foreground'}
    tkinter_text_args.update(tkinter_standard_args)
    tkinter_text_custom_args = {'text':lambda x: Sanitizer.no_validation(x), #resource_id
                                'maxchars':int,
                                'onmodified':lambda x: Sanitizer.no_validation(x), #resource_id
                                'xscrolling':lambda x: Sanitizer.tkinter_bool(x),
                                'yscrolling':lambda x: Sanitizer.tkinter_bool(x)}

    ttk_standard_args = {'cursor':lambda x: Sanitizer.no_validation(x),
                         'style':lambda x: Sanitizer.no_validation(x),
                         'takefocus':lambda x: Sanitizer.tkinter_bool_empty(x),
                         'state':lambda x: Sanitizer.ttk_standard_state(x)}

    ttk_scrollable_args = {'xscrollcommand':lambda x: Sanitizer.no_validation(x), #resource_id
                           'yscrollcommand':lambda x: Sanitizer.no_validation(x)} #resource_id

    ttk_standard_label_args = {'text':lambda x: Sanitizer.no_validation(x), #resource_id
                               'textvariable':lambda x: Sanitizer.no_validation(x), #resource_id
                               'underline':int,
                               'image':lambda x: Sanitizer.ttk_image(x), #resource_id(s)
                               'compound':lambda x: Sanitizer.ttk_compound(x),
                               'width':int}

    ttk_frame_args = {'borderwidth':int,
                      'relief':lambda x: Sanitizer.tkinter_relief(x),
                      'padding':lambda x: Sanitizer.tkinter_tuple((int,) * 4, x),
                      'width':int,
                      'height':int}
    ttk_frame_args.update(ttk_standard_args)

    ttk_labelframe_args = {'labelanchor':lambda x: Sanitizer.ttk_labelframe_anchor(x),
                           'text':lambda x: Sanitizer.no_validation(x), #resource_id
                           'underline':int,
                           'padding':lambda x: Sanitizer.tkinter_tuple((int,) * 4, x),
                           'labelwidget':lambda x: Sanitizer.no_validation(x), #resource_id
                           'width':int,
                           'height':int}
    ttk_labelframe_args.update(ttk_standard_args)

    ttk_notebook_args = {'height':int,
                         'padding':lambda x: Sanitizer.tkinter_tuple((int,) * 4, x),
                         'width':int}
    ttk_notebook_args.update(ttk_standard_args)
    ttk_notebook_custom_args = {'enableTraversal':lambda x: Sanitizer.tkinter_bool(x),
                                'tab_changed':lambda x: Sanitizer.no_validation(x)} #resource_id

    ttk_notebook_tab_args = {'state':lambda x: Sanitizer.ttk_tab_state(x),
                             'sticky':lambda x: Sanitizer.ttk_sticky(x),
                             'padding':lambda x: Sanitizer.tkinter_tuple((int,) * 4, x),
                             'text':lambda x: Sanitizer.no_validation(x), #resource_id
                             'image':lambda x: Sanitizer.ttk_image(x), #resource_id(s)
                             'compound':lambda x: Sanitizer.ttk_compound(x),
                             'underline':int}
    ttk_notebook_tab_custom_args = {'hidden':lambda x: Sanitizer.tkinter_bool(x),
                                    'selected':lambda x: Sanitizer.tkinter_bool(x),
                                    'tab_changed':lambda x: Sanitizer.no_validation(x)} #resource_id

    ttk_list_args = {'displaycolumns':lambda x: Sanitizer.no_validation(x),
                     'height':int,
                     'padding':lambda x: Sanitizer.tkinter_tuple((int,) * 4, x),
                     'selectmode':lambda x: Sanitizer.ttk_list_selectmode(x),}
                     ##'columns':int, #Both variables are auto-set, so ignore them
                     ##'show':int
    ttk_list_args.update(ttk_standard_args)
    ttk_list_tag_args = {'foreground':lambda x: Sanitizer.no_validation(x),
                         'background':lambda x: Sanitizer.no_validation(x),
                         'font':lambda x: Sanitizer.no_validation(x),
                         'image':lambda x: Sanitizer.no_validation(x)} #resource_id
    ##ttk_list_args.update(ttk_scrollable_args) #Both variables are auto-set, so ignore them
    ttk_list_header_args = {'text':lambda x: Sanitizer.no_validation(x), #resource_id
                            'image':lambda x: Sanitizer.no_validation(x), #resource_id
                            'anchor':lambda x: Sanitizer.ttk_anchor(x),
                            'command':lambda x: Sanitizer.no_validation(x)} #resource_id
    ttk_list_column_args = {'anchor':lambda x: Sanitizer.ttk_anchor(x),
                            'minwidth':int,
                            'stretch':lambda x: Sanitizer.tkinter_bool(x),
                            'width':int}

    ttk_button_args = {'command':lambda x: Sanitizer.no_validation(x), #resource_id
                       'default':lambda x: Sanitizer.ttk_button_default(x),
                       'width':int}
    ttk_button_args.update(ttk_standard_args)
    ttk_button_args.update(ttk_standard_label_args)
    ttk_button_custom_args = {'tooltip':lambda x: Sanitizer.no_validation(x)} #resource_id

    ttk_check_button_args = {'command':lambda x: Sanitizer.no_validation(x), #resource_id
                             'offvalue':lambda x: Sanitizer.ttk_button_default(x),
                             'onvalue':lambda x: Sanitizer.no_validation(x),
                             'variable':lambda x: Sanitizer.no_validation(x)} #resource_id
    ttk_check_button_args.update(ttk_standard_args)
    ttk_check_button_args.update(ttk_standard_label_args)
    ttk_check_button_custom_args = {'on_image':lambda x: Sanitizer.no_validation(x), #resource_id
                                    'off_image':lambda x: Sanitizer.no_validation(x), #resource_id
                                    'tooltip':lambda x: Sanitizer.no_validation(x)} #resource_id

    ttk_label_args = {'anchor':lambda x: Sanitizer.ttk_anchor(x),
                      'background':lambda x: Sanitizer.no_validation(x),
                      'font':lambda x: Sanitizer.no_validation(x),
                      'foreground':lambda x: Sanitizer.no_validation(x),
                      'justify':lambda x: Sanitizer.ttk_label_justify(x),
                      'padding':lambda x: Sanitizer.tkinter_tuple((int,) * 4, x),
                      'relief':lambda x: Sanitizer.tkinter_relief(x),
                      'wraplength':int}
    ttk_label_args.update(ttk_standard_args)
    ttk_label_args.update(ttk_standard_label_args)

    ttk_frame_separator_args = {'orient':lambda x: Sanitizer.ttk_frame_separator_orient(x),}
    ttk_frame_separator_args.update(ttk_standard_args)

    ttk_text_entry_args = {'cursor':lambda x: Sanitizer.no_validation(x),
                           'style':lambda x: Sanitizer.no_validation(x),
                           'takefocus':lambda x: Sanitizer.tkinter_bool_empty(x),
                           'exportselection':lambda x: Sanitizer.tkinter_bool(x),
                           'invalidcommand':lambda x: Sanitizer.no_validation(x), #resource_id
                           'justify':lambda x: Sanitizer.ttk_text_entry_justify(x),
                           'show':lambda x: Sanitizer.no_validation(x),
                           'state':lambda x: Sanitizer.ttk_text_entry_state(x),
                           'textvariable':lambda x: Sanitizer.no_validation(x), #resource_id
                           'validate':lambda x: Sanitizer.ttk_text_entry_validate(x),
                           'validatecommand':lambda x: Sanitizer.no_validation(x), #resource_id
                           'width':int,}

    ttk_text_entry_custom_args = {'text':lambda x: Sanitizer.no_validation(x), #resource_id
                                  'maxchars':int,
                                  'onmodified':lambda x: Sanitizer.no_validation(x), #resource_id
                                  'xscrolling':lambda x: Sanitizer.tkinter_bool(x)}

    tkinter_window = (tkinter_window_args, {})
    tkinter_root = (tkinter_root_args, tkinter_root_aliases)
    tkinter_pack = (tkinter_pack_args, {})
    tkinter_menu = (tkinter_menu_args, tkinter_menu_aliases)
    tkinter_menu_custom = (tkinter_menu_custom_args, {})
    tkinter_menu_separator = (tkinter_menu_separator_args, {})
    tkinter_menu_command = (tkinter_menu_command_args, {})
    tkinter_menu_checkbutton = (tkinter_menu_checkbutton_args, {})
    tkinter_menu_cascade = (tkinter_menu_cascade_args, {})
    tkinter_text = (tkinter_text_args, tkinter_text_aliases)
    tkinter_text_custom = (tkinter_text_custom_args, {})

    ttk_frame = (ttk_frame_args, {})
    ttk_labelframe = (ttk_labelframe_args, {})
    ttk_button = (ttk_button_args, {})
    ttk_button_custom = (ttk_button_custom_args, {})
    ttk_check_button = (ttk_check_button_args, {})
    ttk_check_button_custom = (ttk_check_button_custom_args, {})
    ttk_label = (ttk_label_args, {})
    ttk_frame_separator = (ttk_frame_separator_args, {})
    ttk_text_entry = (ttk_text_entry_args, {})
    ttk_text_entry_custom = (ttk_text_entry_custom_args, {})
    ttk_notebook = (ttk_notebook_args, {})
    ttk_notebook_custom = (ttk_notebook_custom_args, {})
    ttk_notebook_tab = (ttk_notebook_tab_args, {})
    ttk_notebook_tab_custom = (ttk_notebook_tab_custom_args, {})
    ttk_list = (ttk_list_args, {})
    ttk_list_tag = (ttk_list_tag_args, {})
    ttk_list_header = (ttk_list_header_args, {})
    ttk_list_column = (ttk_list_column_args, {})

    del tkinter_window_args
    del tkinter_standard_args
    del tkinter_root_aliases
    del tkinter_root_args
    del tkinter_pack_args
    del tkinter_menu_aliases
    del tkinter_menu_args
    del tkinter_menu_custom_args
    del tkinter_menu_separator_args
    del tkinter_menu_command_args
    del tkinter_menu_checkbutton_args
    del tkinter_menu_cascade_args
    del tkinter_text_args
    del tkinter_text_aliases
    del tkinter_text_custom_args

    del ttk_standard_args
    del ttk_scrollable_args
    del ttk_standard_label_args
    del ttk_frame_args
    del ttk_labelframe_args
    del ttk_button_args
    del ttk_button_custom_args
    del ttk_check_button_args
    del ttk_check_button_custom_args
    del ttk_label_args
    del ttk_frame_separator_args
    del ttk_text_entry_args
    del ttk_text_entry_custom_args
    del ttk_notebook_args
    del ttk_notebook_custom_args
    del ttk_notebook_tab_args
    del ttk_notebook_tab_custom_args
    del ttk_list_args
    del ttk_list_tag_args
    del ttk_list_header_args
    del ttk_list_column_args
    #for local in tuple(locals()):
    #    print(local)
    #print()

def dump_style(style):
    """GUI Process: debugging"""
    s = ttk.Style()
    print(style)
    print(s.layout(style))
    print()
    def dump_options(lay_out):
        for element in lay_out:
            if isinstance(element, tuple):
                name, options = element
                element_options = s.element_options(name)
                str = name + ' has '
                for option in element_options:
                    str += option + '(' + s.lookup(name, option) + ') '
                print(str)
                print()
                for option in options:
                    print(option, options[option])
                    if option == 'children':
                        dump_options(options[option])
                print()
                print()
            else:
                str = element + ' has '
                for option in s.element_options(element):
                    str += option + '(' + s.lookup(element, option) + ') '
                print(str)
                print()

    str = style + ' has '
    for option in s.element_options(style):
        str += option + '(' + s.lookup(style, option) + ') '
    print(str)
    print()
    dump_options(s.layout(style))
    print()
    print()

def dump_widget_style(widget):
    """GUI Process: debugging"""
    style = widget.cget('style')
    style = style if style else widget.winfo_class()
    dump_style(style)

registered_afters = {}
def after(root, ms, func=None, *args):
    """Use original implementation for one-off afters.

    Re-implemented to avoid registering/de-registering
    of func with every call.

    Call function once after given time.

    MS specifies the time in milliseconds. FUNC gives the
    function which shall be called. Additional parameters
    are given as parameters to the function call.  Return
    identifier to cancel scheduling with after_cancel."""
    global registered_afters
    name = registered_afters.get((func,args), None)
    def callit():
        func(*args)

    if name is None:
        name = root.register(callit)
        registered_afters[(func,args)] = name
    return root.tk.call('after', ms, name)

class Application:
    """GUI Process: The GUI"""
    def __init__(self, root, to_parent_queue, to_gui_queue, to_bashim_queue):
        self.root = root
        self.to_parent_queue = to_parent_queue
        self.to_gui_queue = to_gui_queue
        self.to_bashim_queue = to_bashim_queue
        self._command_table = {}
        self._closed_reason = None
        self._images = {}
        self._resources = {}#{'top_window':self.root}
        self._retrieved_resources = set()
        self._retrieved_settings = {}

        #Before the connection is used, bind all messages that might be received
        self.bind_message(CLOSE_PROCESS, self.close_app)
        self.make_resources()
        self.is_alive()
        #Delay any initial messages until the other connection is ready
        self.bind_message(CONNECTION_READY, self.initialize)
        self.to_bashim_queue.put((CONNECTION_READY, None, None))
        self.incoming()

    def initialize(self, args):
        """All message bindings should be placed here, to be made after the connection is ready."""
        #Rebind CONNECTION_READY to signal that this side is ready without re-initializing
        self.bind_message(CONNECTION_READY, lambda args: self.to_bashim_queue.put((CONNECTION_READY, None, None)))
        self.to_bashim_queue.put((IS_ALIVE_REQ, (self.last_is_alive_sent,), None))
        self.pre_window_init()
        self.request_resource('top_window', block=True)
        #Pop the window to the front on start
        self.root.attributes('-topmost', 1)
        self.root.focus()
        self.root.after(20, lambda: self.root.attributes('-topmost', 0))
        #for key, value in sorted(self._resources.items()):
        #    print(key,':',value)

    def close_app(self, args):
        self._closed_reason = args[0]
        self.root.quit()
        self.root.destroy()

    def bind_message(self, command_id, command_func):
        self._command_table[command_id] = command_func

    def unbind_message(self, command_id):
        if command_id in self._command_table:
            del self._command_table[command_id]

    def pre_window_init(self):
        """Initialize anything that is GUI dependent, and must be initialized after the GUI starts but before any windows are created."""
        styler = ttk.Style()
        def make_styles():

            #Adds a tabselect icon to the right of the tabs, but currently unable to manipulate it once placed
            ##tabstyle.element_create('tabselect', 'image', 'tab_close_active',
            ##    ('active', 'pressed', '!disabled', 'tab_close_pressed'),
            ##    ('active', '!disabled', 'tab_close_active'), border=10, sticky='')
            try:
                #see if vsapi is available (XP, Vista, 7)
                ##raise AttributeError() #simulate no vsapi
                self.root.tk.call('ttk::style','element','create','close','vsapi','WINDOW', 19, 'disabled 4 {active pressed } 3 active 2')
            except:
                #vsapi unavailable, use images
                #tkinter will lookup image names in its own database, so we have to ensure the images are created
                #otherwise, ideally, get_image would be used directly when an image is needed
                self.request_resource('tab_close')
                self.request_resource('tab_close_pressed')
                self.request_resource('tab_close_active')
                self.wait_for_resources(['tab_close','tab_close_pressed','tab_close_active'])
                styler.element_create('close', 'image', 'tab_close',
                    ('active', 'pressed', '!disabled', 'tab_close_pressed'),
                    ('active', '!disabled', 'tab_close_active'), border=10, sticky='')
            styler.layout('ButtonNotebook', [
                ('ButtonNotebook.client', {'sticky': 'nswe',}),])
                ##('ButtonNotebook.tabselect', {'side': 'right', 'sticky': 'ne'})])
            styler.layout('ButtonNotebook.Tab', [
                            ('ButtonNotebook.tab', {'sticky': 'nswe', 'children':
                                [('ButtonNotebook.padding', {'side': 'top', 'sticky': 'nswe', 'children':
                                    [('ButtonNotebook.focus', {'side': 'top', 'sticky': 'nswe','children':
                                        [('ButtonNotebook.label', {'side': 'left', 'sticky': ''}),
                                         ('ButtonNotebook.padding', {'side': 'top', 'sticky': 'nswe','children':
                                             [('ButtonNotebook.close', {'side': 'right', 'sticky': ''})]}
                                          )]}
                                      )]}
                                  )]}
                             )])
            styler.layout('FlatToolbutton', [('FlatToolbutton.border', {'side': 'top', 'sticky': 'nswe','children':
                                                [('FlatToolbutton.padding', {'side': 'top', 'sticky': 'nswe','children':
                                                    [('FlatToolbutton.label', {'side': 'left', 'sticky': ''})]}
                                                  )]}
                                              )])
            styler.configure('FlatToolbutton', padding=0)
            styler.map('FlatImageButton', relief=[('disabled', 'flat'),('pressed','sunken'),('active','ridge'),('selected', 'flat'),('!active','!selected','flat')])
            styler.layout('FlatImageButton', [('FlatImageButton.border', {'side': 'top', 'sticky': 'nswe','children':
                                                [('FlatImageButton.padding', {'side': 'top', 'sticky': 'nswe','children':
                                                    [('FlatImageButton.label', {'side': 'left', 'sticky': ''})]}
                                                  )]}
                                              )])
            styler.configure('FlatImageButton', padding=0)
            styler.map('FlatImageButton', relief=[('disabled', 'flat'),('pressed','sunken'),('active','groove'),('selected', 'flat'),('!active','!selected','flat')])
        #def test():
            #pass
            #dump_widget_style(ttk.Entry())
            #styler.configure('Entry.padding', relief=tkinter.SUNKEN)
        #test()
        make_styles()

    def incoming(self, reregister=True):
        """Handle all the messages currently in the queue (if any)."""
        while True:
            try:
                command, args, response_to = self.to_gui_queue.get_nowait() #Non-blocking
            except QueueEmpty:
                break
##            print('basher - ',command, args, response_to)
            self._command_table[command](args)
        if reregister: after(self.root, 100, self.incoming)

    def is_alive(self):
        """Periodically polls to_bashim_queue to make sure there's a listener."""
        self.last_is_alive_sent = 0
        self.last_is_alive_received = 0
        def got_ack(args):
            self.last_is_alive_received = args[0]
        def got_req(args):
            send_ack(args)
        def send_req(args=None):
            last_is_alive_sent = self.last_is_alive_sent
            if self.last_is_alive_sent != self.last_is_alive_received:
                self.to_parent_queue.put((SHUTDOWN, (SYSTEM_REQUEST,), None))
                raise EnvironmentError('The Bash GUI is unable to communicate with the rest of Bash. A support process may have crashed or been terminated by the user.')
            last_is_alive_sent += 1
            if last_is_alive_sent > 60:
                last_is_alive_sent = 0
            self.to_bashim_queue.put((IS_ALIVE_REQ, (last_is_alive_sent,), None))
            self.last_is_alive_sent = last_is_alive_sent
            after(self.root, 10000, send_req)
        def send_ack(args):
            self.to_bashim_queue.put((IS_ALIVE_ACK, args, None))
        self.bind_message(IS_ALIVE_ACK, got_ack)
        self.bind_message(IS_ALIVE_REQ, got_req)

    def make_resources(self):
        _retrieved_resources = self._retrieved_resources
        _retrieved_settings = self._retrieved_settings
        self._resource_table = {}
        _resource_table = self._resource_table
        self._action_table = {}
        _action_table = self._action_table
        _images = self._images
        _resources = self._resources
        menus = []
        containers = []
        containers_boundkeys = []
        button_ids = {'left_down'   : '<ButtonPress-1>',
                      'left_up'     : '<ButtonRelease-1>',
                      'left_click'  : ('<ButtonPress-1>','<ButtonRelease-1>','<<ButtonDownUp-1>>'),
                      'middle_down' : '<ButtonPress-2>',
                      'middle_up'   : '<ButtonRelease-2>',
                      'middle_click': ('<ButtonPress-2>','<ButtonRelease-2>','<<ButtonDownUp-2>>'),
                      'right_down'  : '<ButtonPress-3>',
                      'right_up'    : '<ButtonRelease-3>',
                      'right_click' : ('<ButtonPress-3>','<ButtonRelease-3>','<<ButtonDownUp-3>>'),
                     }
        bound_events = set()

        def tkinter_down(event):
            x, y, widget = event.x, event.y, event.widget
            widget.pressed_indentity = id(widget)

        def tkinter_up(event, virtual_event=None):
            x, y, widget = event.x, event.y, event.widget
            widget = widget.winfo_containing(event.x_root, event.y_root)
            if not hasattr(widget, 'pressed_indentity'):
                return
            if widget.pressed_indentity == id(widget):
                widget.event_generate(virtual_event, rootx=event.x_root, rooty=event.y_root, x=event.x, y=event.y)
            del widget.pressed_indentity

        def list_down(event):
            x, y, widget = event.x, event.y, event.widget
            identity = widget.identify_row(y)
            if identity:
                widget.pressed_indentity = identity
                print('down',widget.pressed_indentity)
            #return 'break'

        def list_up(event, virtual_event=None):
            x, y, widget = event.x, event.y, event.widget
            widget = widget.winfo_containing(event.x_root, event.y_root)
            if not hasattr(widget, 'pressed_indentity'):
                return
            if widget.pressed_indentity == widget.identify_row(y):
                print('up',widget.pressed_indentity)
                #click_event(event)
                widget.event_generate(virtual_event, rootx=event.x_root, rooty=event.y_root, x=event.x, y=event.y)
            del widget.pressed_indentity

        def ttk_down(event):
            x, y, widget = event.x, event.y, event.widget
            indentity = widget.identify(x, y)

            widget.state(['pressed'])
            widget.pressed_indentity = indentity

        def ttk_up(event, virtual_event=None):
            x, y, widget = event.x, event.y, event.widget
            if not widget.instate(['pressed']):
                return
            indentity = widget.identify(x, y)
            if widget.pressed_indentity == indentity:
                widget.event_generate(virtual_event, rootx=event.x_root, rooty=event.y_root, x=event.x, y=event.y)

            widget.state(['!pressed'])
            widget.pressed_indentity = None

        def set_resource(args):
            nonlocal _resource_table, _resources, _retrieved_resources
            resource_name, type_resource = args
            _retrieved_resources.add(resource_name)
            if type_resource is None: return
            resource_type, resource = _resources[resource_name] = type_resource
            _resource_table[resource_type](resource_name, resource)

        def set_setting(args):
            nonlocal _retrieved_settings
            setting_name, setting_value = args
            _retrieved_settings[setting_name] = setting_value

        def bind_keys(widget, boundkeys, down_func=ttk_down, up_func=ttk_up):
            nonlocal _resources, button_ids, bound_events
            if boundkeys is None: return
            def show_context(event, menu):
                widget.focus()
                post_up = getattr(menu, 'post_up', False)
                if post_up:
                    borderwidth = int(str(menu.cget('borderwidth'))) * 2
                    menu.post(event.x_root, event.y_root - menu.winfo_reqheight() + borderwidth - 4) #Not sure where the - 4 is coming from. Forgetting to account for something.
                else:
                    menu.post(event.x_root, event.y_root)

            for key, resource_id in boundkeys.items():
                resource = self.request_resource(resource_id, block=True)

                if isinstance(resource, tkinter.Menu):
                    resource = _resources[resource_id] = lambda event, menu=resource: show_context(event, menu)
                bound_event = button_ids[key]
                if isinstance(bound_event, tuple):
                    press_event, release_event, bound_event = bound_event
                    widget.bind(press_event, down_func)
                    widget.bind(release_event, lambda event, virtualevent=bound_event: up_func(event,virtualevent))
                widget.bind(bound_event, resource)

        def process_windowargs(window, args):
            resources = [args[key] for key in {'iconbitmap','WM_DELETE_WINDOW','title'} if key in args]
            commands = {'aspect':lambda x: window.aspect(*x),
                        'fullscreen':lambda x: window.attributes('-fullscreen %d' % (x,)),
                        'topmost':lambda x: window.attributes('-topmost %d' % (x,)),
                        'alpha':lambda x: window.attributes('-alpha %f' % (x,)),
                        'disabled':lambda x: window.attributes('-disabled %d' % (x,)),
                        'toolwindow':lambda x: window.attributes('-toolwindow %d' % (x,)),
                        'transparentcolor':lambda x: window.attributes('-transparentcolor %s' % (x,)),
                        'deiconify':lambda x: window.deiconify() if x else None,
                        'focusmodel':window.focusmodel,
                        'iconbitmap':lambda x: window.iconbitmap(_resources[x]),
                        'iconify':lambda x: window.iconify() if x else None,
                        'iconposition':lambda x: window.iconposition(*x),
                        'maxsize':lambda x: window.maxsize(*x),
                        'minsize':lambda x: window.minsize(*x),
                        'WM_DELETE_WINDOW':lambda x: window.protocol('WM_DELETE_WINDOW', _resources[x]),
                        'resizable':lambda x: window.resizable(*x),
                        'state':window.state,
                        'title':lambda x: window.title(_resources[x])
                       }
            for resource in resources:
                self.request_resource(resource)
            self.wait_for_resources(resources)
            for key, value in args.items():
                commands[key](value)

        def make_root(resource_name, args):
            nonlocal _resources, containers
            resource_keys = {'menu',}
            def process_rootargs(rootargs):
                nonlocal _resources
                for key, value in rootargs.items():
                    self.root[key] = _resources[value] if key in resource_keys else value
            resourceargs, windowargs, resources, boundkeys = args
            resourceargs = Sanitizer.sanitize(resourceargs, Sanitizer.tkinter_root)
            windowargs = Sanitizer.sanitize(windowargs, Sanitizer.tkinter_window)
            if 'title' not in windowargs:
                windowargs['title'] = resource_name + '_string'

            containers.append((self.root, boundkeys))
            resources += tuple(resourceargs[key] for key in resource_keys if key in resourceargs)
            for resource in resources:
                self.request_resource(resource, block=True)
            assert(containers.pop() == (self.root, boundkeys))
            _resources[resource_name] = self.root
            process_rootargs(resourceargs)
            process_windowargs(self.root, windowargs)
            bind_keys(self.root, boundkeys)

        def make_frame(resource_name, args):
            nonlocal _resources, containers
            parent, parentkeys = containers[-1]
            resourceargs, packargs, resources, boundkeys = args
            resourceargs = Sanitizer.sanitize(resourceargs, Sanitizer.ttk_frame)
            packargs = Sanitizer.sanitize(packargs, Sanitizer.tkinter_pack)
            frame = ttk.Frame(parent, **resourceargs)
            _resources[resource_name] = frame
            containers.append((frame, boundkeys))
            for resource in resources:
                self.request_resource(resource, block=True)
            frame.pack(**packargs)
            assert(containers.pop() == (frame, boundkeys))
            bind_keys(frame, parentkeys)
            bind_keys(frame, boundkeys)

        def make_labelframe(resource_name, args):
            nonlocal _resources, containers
            parent, parentkeys = containers[-1]
            resourceargs, packargs, resources, boundkeys = args
            resourceargs = Sanitizer.sanitize(resourceargs, Sanitizer.ttk_labelframe)
            packargs = Sanitizer.sanitize(packargs, Sanitizer.tkinter_pack)
            resource_keys = {'text','labelwidget'}
            if 'text' not in resourceargs:
                resourceargs['text'] = resource_name + '_string'
            resources_self = tuple(resourceargs[key] for key in resource_keys if key in resourceargs)
            for resource in resources_self:
                self.request_resource(resource)
            self.wait_for_resources(resources_self)

            for key in resource_keys:
                if key in resourceargs:
                    resource_id = resourceargs[key]
                    if resource_id in _resources:
                        resource = _resources[resource_id]
                        if resource is None:
                            del _resources[resourceargs[key]]
                            del resourceargs[key]
                        else:
                            resourceargs[key] = resource
                    else:
                        del resourceargs[key]

            frame = ttk.LabelFrame(parent, **resourceargs)
            _resources[resource_name] = frame
            containers.append((frame, boundkeys))
            for resource in resources:
                self.request_resource(resource, block=True)

            frame.pack(**packargs)
            assert(containers.pop() == (frame, boundkeys))
            bind_keys(frame, parentkeys)
            bind_keys(frame, boundkeys)

        def make_menu(resource_name, args):
            nonlocal _resources, menus, containers
            menu_resourceargs, menu_customargs, menu_resources = args
            menu_resourceargs = Sanitizer.sanitize(menu_resourceargs, Sanitizer.tkinter_menu)
            menu_customargs = Sanitizer.sanitize(menu_customargs, Sanitizer.tkinter_menu_custom)

            if 'tearoff' not in menu_resourceargs:
                menu_resourceargs['tearoff'] = 0
            menu = tkinter.Menu(containers[-1][0], **menu_resourceargs)
            post_up = menu_customargs.get('post_up')
            if post_up:
                menu.post_up = post_up
            def make_menuseparator(resource_name, args):
                nonlocal menus
                args = Sanitizer.sanitize(args, Sanitizer.tkinter_menu_separator)
                menus[-1].add_separator(**args)
                del _resources[resource_name]

            def make_menucommand(resource_name, args):
                nonlocal _resources, menus
                resourceargs, actions = args
                resourceargs = Sanitizer.sanitize(resourceargs, Sanitizer.tkinter_menu_command)
                resource_keys = {'bitmap','image','label'}#,'command' must be handled separately
                if 'label' not in resourceargs:
                    resourceargs['label'] = resource_name + '_string'
                resources = tuple(resourceargs[key] for key in resource_keys if key in resourceargs) + actions
                for resource in resources:
                    self.request_resource(resource)
                self.wait_for_resources(resources)
                for key in resource_keys:
                    if key in resourceargs:
                        resource_id = resourceargs[key]
                        if resource_id in _resources:
                            resource = _resources[resource_id]
                            if resource is None:
                                del _resources[resourceargs[key]]
                                del resourceargs[key]
                            else:
                                resourceargs[key] = resource
                        else:
                            del resourceargs[key]

                if 'command' not in resourceargs:
                    resourceargs['command'] = lambda args=None,funcs=[_resources[action] for action in actions]: [func(args) for func in funcs]

                menus[-1].add_command(**resourceargs)
                del _resources[resource_name]

            def make_menucheckbutton(resource_name, args):
                nonlocal _resources, menus
                resourceargs, actions = args
                if 'indicatoron' not in resourceargs:
                    resourceargs['indicatoron'] = 1
                resourceargs = Sanitizer.sanitize(resourceargs, Sanitizer.tkinter_menu_checkbutton)
                resource_keys = {'variable','bitmap','image','label'}#,'command' must be handled separately
                if 'label' not in resourceargs:
                    resourceargs['label'] = resource_name + '_string'
                resources = tuple(resourceargs[key] for key in resource_keys if key in resourceargs) + actions
                for resource in resources:
                    self.request_resource(resource)
                self.wait_for_resources(resources)
                for key in resource_keys:
                    if key in resourceargs:
                        resource_id = resourceargs[key]
                        if resource_id in _resources:
                            resource = _resources[resource_id]
                            if resource is None:
                                del _resources[resourceargs[key]]
                                del resourceargs[key]
                            else:
                                resourceargs[key] = resource
                        else:
                            del resourceargs[key]

                if 'command' not in resourceargs:
                    resourceargs['command'] = lambda args=None,funcs=[_resources[action] for action in actions]: [func(args) for func in funcs]

                menus[-1].add_checkbutton(**resourceargs)
                del _resources[resource_name]

            def make_menucascade(resource_name, args):
                nonlocal _resources, menus
                resourceargs, resources = args
                cascadeargs = Sanitizer.sanitize(resourceargs, Sanitizer.tkinter_menu_cascade)
                menuargs = Sanitizer.sanitize(resourceargs, Sanitizer.tkinter_menu)
                resource_keys = {'bitmap','image','label','menu'}
                if 'label' not in cascadeargs:
                    cascadeargs['label'] = resource_name + '_string'
                if 'tearoff' not in menuargs:
                    menuargs['tearoff'] = 0
                menu = tkinter.Menu(menus[-1], **menuargs)
                menus.append(menu)
                resources = tuple(cascadeargs[key] for key in resource_keys if key in cascadeargs) + resources
                for resource in resources:
                    self.request_resource(resource, block=True)
                self.wait_for_resources(resources)
                assert(menus.pop() == menu)
                for key in resource_keys:
                    if key in cascadeargs:
                        resource_id = cascadeargs[key]
                        if resource_id in _resources:
                            resource = _resources[resource_id]
                            if resource is None:
                                del _resources[cascadeargs[key]]
                                del cascadeargs[key]
                            else:
                                cascadeargs[key] = resource
                        else:
                            del cascadeargs[key]

                if 'menu' not in cascadeargs:
                    cascadeargs['menu'] = menu
                _resources[resource_name] = menu
                menus[-1].add_cascade(**cascadeargs)

            bind_resource(RES_MENU_SEPARATOR, make_menuseparator)
            bind_resource(RES_MENU_COMMAND, make_menucommand)
            bind_resource(RES_MENU_CHECKBUTTON, make_menucheckbutton)
##            bind_resource(RES_MENU_RADIOBUTTON, make_menuradiobutton)
            bind_resource(RES_MENU_CASCADE, make_menucascade)
            menus.append(menu)
            for resource in menu_resources:
                self.request_resource(resource, block=True)
            assert(menus.pop() == menu)
            _resources[resource_name] = menu

        def make_notebook(resource_name, args):
            nonlocal _resources, containers
            parent, parentkeys = containers[-1]
            def process_customargs(widget, args):
                resources = [args[key] for key in {'tab_changed',} if key in args]
                commands = {'enableTraversal':lambda x: widget.enable_traversal() if x else None,
                            'tab_changed':lambda x: widget.bind('<<NotebookTabChanged>>', _resources[x]),
                           }
                for resource in resources:
                    self.request_resource(resource)
                self.wait_for_resources(resources)
                for key, value in args.items():
                    commands[key](value)

            def make_notebooktab(resource_name, args):
                nonlocal _resources, containers
                parent, parentkeys = containers[-1]
                def process_customargs(widget, args):
                    resources = [args[key] for key in {'tab_changed',} if key in args]
                    commands = {'hidden':lambda x: parent.hide(widget) if x else None,
                                'selected':lambda x: parent.select(widget) if x else None,
                                'tab_changed':lambda x: widget.bind('<<NotebookTabChanged>>', _resources[x]),
                               }
                    for resource in resources:
                        self.request_resource(resource)
                    self.wait_for_resources(resources)
                    for key, value in args.items():
                        commands[key](value)
                resourceargs, customargs, container, boundkeys = args
                resources = (container,)
                if 'image' in resourceargs:
                    resources += tuple(image_tuple[-1] for image_tuple in resourceargs['image'])

                resourceargs = Sanitizer.sanitize(resourceargs, Sanitizer.ttk_notebook_tab)
                customargs = Sanitizer.sanitize(customargs, Sanitizer.ttk_notebook_tab_custom)

                resource_keys = {'text',} #'image' must be handled separately before sanitizing occurs
                if 'text' not in resourceargs:
                    resourceargs['text'] = resource_name + '_string'
                resources += tuple(resourceargs[key] for key in resource_keys if key in resourceargs)
                for resource in resources:
                    self.request_resource(resource, block=True)
                tab = _resources[container]
                for key in resource_keys:
                    if key in resourceargs:
                        resource_id = resourceargs[key]
                        if resource_id in _resources:
                            resource = _resources[resource_id]
                            if resource is None:
                                del _resources[resourceargs[key]]
                                del resourceargs[key]
                            else:
                                resourceargs[key] = resource
                        else:
                            del resourceargs[key]
                parent.add(tab, **resourceargs)
                process_customargs(tab, customargs)
                bind_keys(tab, parentkeys)
                bind_keys(tab, boundkeys)

            resourceargs, packargs, customargs, resources, boundkeys = args
            resourceargs = Sanitizer.sanitize(resourceargs, Sanitizer.ttk_notebook)
            packargs = Sanitizer.sanitize(packargs, Sanitizer.tkinter_pack)
            customargs = Sanitizer.sanitize(customargs, Sanitizer.ttk_notebook_custom)
            if 'style' not in resourceargs:
                resourceargs['style'] = 'ButtonNotebook'
            bind_resource(RES_NOTEBOOK_TAB, make_notebooktab)
            notebook = _resources[resource_name] = ttk.Notebook(parent, **resourceargs)
            notebook.pack(**packargs)
            containers.append((notebook,boundkeys))
            for resource in resources:
                self.request_resource(resource, block=True)
            assert(containers.pop() == (notebook,boundkeys))
            process_customargs(notebook, customargs)
            bind_keys(notebook, parentkeys)
            bind_keys(notebook, boundkeys)
            notebook.bind('<ButtonPress-3>', lambda event, container=notebook: self.drag_start(event, container))
            notebook.bind('<ButtonRelease-3>', lambda event, container=notebook: self.drag_end(event, container))
            notebook.bind('<B3-Motion>', lambda event, container=notebook: self.drag_in_progress(event, container))

        def make_list(resource_name, args):
            nonlocal _resources, containers
            parent, parentkeys = containers[-1]
            resourceargs, packargs, columns, tags, active_inactive_tags, on_activate_deactivate, on_setorder, boundkeys = args
            active_tag, inactive_tag = active_inactive_tags
            on_activate, on_deactivate = on_activate_deactivate
            resourceargs = Sanitizer.sanitize(resourceargs, Sanitizer.ttk_list)
            #customargs = Sanitizer.sanitize(customargs, Sanitizer.ttk_list_custom)
            packargs = Sanitizer.sanitize(packargs, Sanitizer.tkinter_pack)
            def make_listtag(resource_name, args):
                nonlocal _resources, containers
                parent, parentkeys = containers[-1]
                resourceargs, boundkeys = args
                resourceargs = Sanitizer.sanitize(resourceargs, Sanitizer.ttk_list_tag)
                resource_keys = {'image',}
                parent.tag_configure(resource_name, **resourceargs)
                def tag_bind(widget, tag, boundkeys, down_func=list_down, up_func=list_up):
                    nonlocal _resources, button_ids, bound_events
                    if boundkeys is None: return
                    def show_context(event, menu):
                        widget.focus()
                        post_up = getattr(menu, 'post_up', False)
                        if post_up:
                            borderwidth = int(str(menu.cget('borderwidth'))) * 2
                            menu.post(event.x_root, event.y_root - menu.winfo_reqheight() + borderwidth - 4) #Not sure where the - 4 is coming from. Forgetting to account for something.
                        else:
                            menu.post(event.x_root, event.y_root)

                    for key, resource_id in boundkeys.items():
                        resource = self.request_resource(resource_id, block=True)

                        if isinstance(resource, tkinter.Menu):
                            resource = _resources[resource_id] = lambda event, menu=resource: show_context(event, menu)
                        bound_event = button_ids[key]
                        if isinstance(bound_event, tuple):
                            press_event, release_event, bound_event = bound_event
                            widget.bind(press_event, down_func)
                            widget.bind(release_event, lambda event, virtual_event=bound_event: up_func(event,virtual_event), '+')
                            print(press_event, release_event, bound_event)
                        widget.tag_bind(tag, bound_event, resource)
                        #widget.bind(bound_event, lambda event=None: print(event))
                        #widget.bind(bound_event, lambda event=None: print(event))
                        #widget.tag_bind(tag, bound_event, lambda event=None: print(event))
                        #print(tag, bound_event, resource)
                tag_bind(parent, resource_name, boundkeys)

            bind_resource(RES_LIST_TAG, make_listtag)
            def nocache(resource_name):
                value = self.request_resource(resource_name, block=True)
                del self._resources[resource_name]
                return value
            list_view = CustomListView(parent,
                                       columns,
                                       get_data=lambda id='%s_populate' % (resource_name,): self.request_resource(id, block=True),
                                       set_data=lambda value, id=on_setorder: self.set_resource(id, value),
                                       activate_items=lambda items, id=on_activate: self.set_resource(id, items),
                                       deactivate_items=lambda items, id=on_deactivate: self.set_resource(id, items),
                                       active_tag=active_tag,
                                       inactive_tag=inactive_tag,
                                       refresh_item=lambda id=resource_name: nocache(id),
                                       **resourceargs)
            list_view.pack(**packargs)
            containers.append((list_view,boundkeys))
            resources = tags + (active_tag, inactive_tag,)
            for resource in resources:
                self.request_resource(resource, block=True)
            assert(containers.pop() == (list_view,boundkeys))
            bind_keys(list_view, parentkeys)
            bind_keys(list_view, boundkeys)
            #list_view.bind('<ButtonPress-3>', lambda event, container=notebook: self.drag_start(event, container))
            #list_view.bind('<ButtonRelease-3>', lambda event, container=notebook: self.drag_end(event, container))
            #list_view.bind('<B3-Motion>', lambda event, container=notebook: self.drag_in_progress(event, container))

        def make_button(resource_name, args):
            nonlocal _resources, containers
            parent, parentkeys = containers[-1]
            resourceargs, packargs, customargs, actions, boundkeys = args
            resources = ()
            if 'image' in resourceargs:
                resources += tuple(image_tuple[-1] for image_tuple in resourceargs['image'])
            resourceargs = Sanitizer.sanitize(resourceargs, Sanitizer.ttk_button)
            customargs = Sanitizer.sanitize(customargs, Sanitizer.ttk_button_custom)
            packargs = Sanitizer.sanitize(packargs, Sanitizer.tkinter_pack)
            resource_keys = {'text','textvariable','tooltip'} #'image','command' must be handled separately before sanitizing occurs
            if 'text' not in resourceargs:
                resourceargs['text'] = resource_name + '_string'
            if 'textvariable' not in resourceargs:
                resourceargs['textvariable'] = resource_name + '_vstring'

            tooltip = customargs.get('tooltip')
            if tooltip:
                resources += (tooltip,)
            resources += tuple(resourceargs[key] for key in resource_keys if key in resourceargs) + actions
            for resource in resources:
                self.request_resource(resource)
            self.wait_for_resources(resources)

            for key in resource_keys:
                for args in [resourceargs, customargs]:
                    if key in args:
                        resource_id = args[key]
                        if resource_id in _resources:
                            resource = _resources[resource_id]
                            if resource is None:
                                del _resources[args[key]]
                                del args[key]
                            else:
                                args[key] = resource
                        else:
                            del args[key]

            if 'command' not in resourceargs:
                resourceargs['command'] = lambda args=None,funcs=[_resources[action] for action in actions]: [func(args) for func in funcs]

            button = ttk.Button(parent, **resourceargs)
            button.pack(**packargs)
            _resources[resource_name] = button
            bind_keys(button, parentkeys)
            bind_keys(button, boundkeys)

            if tooltip:
                _resources[tooltip] = CustomTooltip(button, _resources[tooltip])

        def make_checkbutton(resource_name, args):
            nonlocal _resources, containers
            parent, parentkeys = containers[-1]
            resourceargs, packargs, customargs, actions, boundkeys = args
            resources = ()
            customargs = Sanitizer.sanitize(customargs, Sanitizer.ttk_check_button_custom)
            packargs = Sanitizer.sanitize(packargs, Sanitizer.tkinter_pack)

            if 'image' not in resourceargs:
                images = ()
                if 'off_image' in customargs:
                    if 'on_image' in customargs:
                        images = ((customargs['off_image'],),('SELECTED',customargs['on_image']))
                    else:
                        images = ((customargs['off_image'],),)
                elif 'on_image' in customargs:
                    images = (('SELECTED',customargs['on_image']))
                if images:
                    resourceargs['style'] = 'FlatToolbutton'
                    resourceargs['image'] = images
            if 'image' in resourceargs:
                resources += tuple(image_tuple[-1] for image_tuple in resourceargs['image'])

            resourceargs = Sanitizer.sanitize(resourceargs, Sanitizer.ttk_check_button)
            resource_keys = {'text','textvariable','variable','tooltip'} #'image','command','on_image','off_image', must be handled separately before sanitizing occurs
            if 'text' not in resourceargs:
                resourceargs['text'] = resource_name + '_string'
            if 'textvariable' not in resourceargs:
                resourceargs['textvariable'] = resource_name + '_vstring'

            tooltip = customargs.get('tooltip')
            if tooltip:
                resources += (tooltip,)
            resources += tuple(resourceargs[key] for key in resource_keys if key in resourceargs) + actions
            for resource in resources:
                self.request_resource(resource)
            self.wait_for_resources(resources)

            for key in resource_keys:
                for args in [resourceargs, customargs]:
                    if key in args:
                        resource_id = args[key]
                        if resource_id in _resources:
                            resource = _resources[resource_id]
                            if resource is None:
                                del _resources[args[key]]
                                del args[key]
                            else:
                                args[key] = resource
                        else:
                            del args[key]

            if 'command' not in resourceargs:
                resourceargs['command'] = lambda args=None,funcs=[_resources[action] for action in actions]: [func(args) for func in funcs]
            button = ttk.Checkbutton(parent, **resourceargs)
            button.pack(**packargs)
            _resources[resource_name] = button
            bind_keys(button, parentkeys)
            bind_keys(button, boundkeys)

            if tooltip:
                _resources[tooltip] = CustomTooltip(button, _resources[tooltip])

        def make_label(resource_name, args):
            nonlocal _resources, containers
            parent, parentkeys = containers[-1]
            resourceargs, packargs, boundkeys = args
            resources = ()
            if 'image' in resourceargs:
                resources += tuple(image_tuple[-1] for image_tuple in resourceargs['image'])
            resourceargs = Sanitizer.sanitize(resourceargs, Sanitizer.ttk_label)
            packargs = Sanitizer.sanitize(packargs, Sanitizer.tkinter_pack)
            resource_keys = {'text','textvariable'} #'image' must be handled separately before sanitizing occurs
            if 'text' not in resourceargs:
                resourceargs['text'] = resource_name + '_string'
            if 'textvariable' not in resourceargs:
                resourceargs['textvariable'] = resource_name + '_vstring'
            resources += tuple(resourceargs[key] for key in resource_keys if key in resourceargs)
            for resource in resources:
                self.request_resource(resource)
            self.wait_for_resources(resources)

            for key in resource_keys:
                if key in resourceargs:
                    resource_id = resourceargs[key]
                    if resource_id in _resources:
                        resource = _resources[resource_id]
                        if resource is None:
                            del _resources[resourceargs[key]]
                            del resourceargs[key]
                        else:
                            resourceargs[key] = resource
                    else:
                        del resourceargs[key]

            label = ttk.Label(parent, **resourceargs)
            label.pack(**packargs)
            _resources[resource_name] = label
            bind_keys(label, parentkeys)
            bind_keys(label, boundkeys)

        def make_frameseparator(resource_name, args):
            nonlocal _resources, containers
            parent, parentkeys = containers[-1]
            resourceargs, packargs = args
            resourceargs = Sanitizer.sanitize(resourceargs, Sanitizer.ttk_frame_separator)
            packargs = Sanitizer.sanitize(packargs, Sanitizer.tkinter_pack)
            separator = ttk.Separator(parent, **resourceargs)
            separator.pack(**packargs)
            _resources[resource_name] = separator

        def make_text(resource_name, args):
            nonlocal _resources, containers
            parent, parentkeys = containers[-1]
            resourceargs, packargs, customargs, boundkeys = args
            resourceargs = Sanitizer.sanitize(resourceargs, Sanitizer.tkinter_text)
            packargs = Sanitizer.sanitize(packargs, Sanitizer.tkinter_pack)
            customargs = Sanitizer.sanitize(customargs, Sanitizer.tkinter_text_custom)

            resource_keys = {'text','onmodified'}
            if 'text' not in customargs:
                customargs['text'] = resource_name + '_string'
            resources = tuple(customargs[key] for key in resource_keys if key in customargs)
            for resource in resources:
                self.request_resource(resource)
            self.wait_for_resources(resources)

            for key in resource_keys:
                if key in customargs:
                    resource_id = customargs[key]
                    if resource_id in _resources:
                        resource = _resources[resource_id]
                        if resource is None:
                            del _resources[resourceargs[key]]
                            del customargs[key]
                        else:
                            customargs[key] = resource
                    else:
                        del customargs[key]

            if 'text' in customargs:
                resourceargs['text'] = customargs['text']
            if 'maxchars' in customargs:
                resourceargs['maxchars'] = customargs['maxchars']
            if 'onmodified' in customargs:
                resourceargs['onmodified'] = customargs['onmodified']
            text, text_parent = ScrolledWidget(CustomText, parent, customargs.get('yscrolling'), customargs.get('xscrolling'), **resourceargs)
            if text_parent:
                text_parent.pack(**packargs)
            else:
                text.pack(**packargs)

            _resources[resource_name] = text
            text.bind('<ButtonPress-3>', tkinter_down)
            text.bind('<ButtonRelease-3>', lambda event, virtualevent='<<ButtonDownUp-3>>': tkinter_up(event,virtualevent))

            text.context_menu = self.request_resource('text_context_menu', block=True)
            text.bind('<<ButtonDownUp-3>>', lambda event: text.show_context(event))
            bind_keys(text, parentkeys, tkinter_down, tkinter_up)
            bind_keys(text, boundkeys, tkinter_down, tkinter_up)

        def make_textentry(resource_name, args):
            nonlocal _resources, containers
            parent, parentkeys = containers[-1]
            resourceargs, packargs, customargs, boundkeys = args
            resourceargs = Sanitizer.sanitize(resourceargs, Sanitizer.ttk_text_entry)
            packargs = Sanitizer.sanitize(packargs, Sanitizer.tkinter_pack)
            customargs = Sanitizer.sanitize(customargs, Sanitizer.ttk_text_entry_custom)

            resource_keys = {'invalidcommand','textvariable','validatecommand','text','onmodified'}
            if 'text' not in customargs:
                customargs['text'] = resource_name + '_string'
            if 'textvariable' not in resourceargs:
                resourceargs['textvariable'] = resource_name + '_vstring'
            resources = tuple(customargs[key] for key in resource_keys if key in customargs)
            resources += tuple(resourceargs[key] for key in resource_keys if key in resourceargs)
            for resource in resources:
                self.request_resource(resource)
            self.wait_for_resources(resources)

            for key in resource_keys:
                if key in resourceargs:
                    resource_id = resourceargs[key]
                    if resource_id in _resources:
                        resource = _resources[resource_id]
                        if resource is None:
                            del _resources[resourceargs[key]]
                            del resourceargs[key]
                        else:
                            resourceargs[key] = resource
                    else:
                        del resourceargs[key]

            for key in resource_keys:
                if key in customargs:
                    resource_id = customargs[key]
                    if resource_id in _resources:
                        resource = _resources[resource_id]
                        if resource is None:
                            del _resources[customargs[key]]
                            del customargs[key]
                        else:
                            customargs[key] = resource
                    else:
                        del customargs[key]

            if 'text' in customargs:
                resourceargs['text'] = customargs['text']
            if 'maxchars' in customargs:
                resourceargs['maxchars'] = customargs['maxchars']
            if 'onmodified' in customargs:
                resourceargs['onmodified'] = customargs['onmodified']

            text, text_parent = ScrolledWidget(CustomTextEntry, parent, None, customargs.get('xscrolling'), **resourceargs)
            if text_parent:
                text_parent.pack(**packargs)
            else:
                text.pack(**packargs)
            _resources[resource_name] = text
            text.bind('<ButtonPress-3>', tkinter_down)
            text.bind('<ButtonRelease-3>', lambda event, virtualevent='<<ButtonDownUp-3>>': tkinter_up(event,virtualevent))

            text.context_menu = self.request_resource('text_context_menu', block=True)
            text.bind('<<ButtonDownUp-3>>', lambda event: text.show_context(event))
            bind_keys(text, parentkeys, tkinter_down, tkinter_up)
            bind_keys(text, boundkeys, tkinter_down, tkinter_up)

        def make_send_function(resource_name, args):
            nonlocal _resources
            target, message = args
            if target == bashim_process_id:
                _resources[resource_name] = lambda args=None: self.to_bashim_queue.put(message)
            elif target == basher_process_id:
                _resources[resource_name] = lambda args=None: self.to_gui_queue.put(message)
            elif target == parent_process_id:
                _resources[resource_name] = lambda args=None: self.to_parent_queue.put(message)

        def make_display_function(resource_name, string_to_display):
            nonlocal _resources
            _resources[resource_name] = lambda args=None: print(string_to_display)

        def make_update_function(resource_name, target):
            _resources[resource_name] = lambda args=None: self.to_bashim_queue.put((REQUEST_VOLATILE_UPDATE,(target,), None))

        def make_conditional_function(resource_name, args):
            nonlocal _resources
            variable, true_result, false_result = args
            def conditional_function(args, variable, true_result, false_result):
                result = true_result if self.request_setting(variable) else false_result
                if result:
                    func = self.request_resource(result, block=True)
                    if func:
                        func(args)
            _resources[resource_name] = lambda args=None, variable=variable, true_result=true_result, false_result=false_result: conditional_function(args, variable, true_result, false_result)

        def make_string(resource_name, resource):
            _resources[resource_name] = resource

        def make_generic(resource_name, resource):
            _resources[resource_name] = resource

        def make_volatilestring(resource_name, resource):
            _resources[resource_name] = tkinter.StringVar(value=resource)

        def make_volatilebool(resource_name, resource):
            _resources[resource_name] = tkinter.BooleanVar(value=resource)

        def update_volatile_resource(args):
            nonlocal _resources
            resource_name, type_resource = args
            resource_type, resource = type_resource
            _resources[resource_name].set(resource)

        def bind_resource(resource_type, resource_func):
            _resource_table[resource_type] = resource_func
        def debind_resource(resource_type):
            if resource_type in _resource_table:
                del _resource_table[resource_type]

        def make_image(resource_name, args):
            nonlocal _resources, _images
            if resource_name in _images:
                return _images[resource_name]
            path, boundkeys = args

            if path.endswith('.gif'):
                image = tkinter.PhotoImage(resource_name, file=path)
            else:
                cwd = os.getcwd()
                dir, file = os.path.split(path)
                os.chdir(dir)
                image = self.root.tk.eval('::shellicon::get -large "%s" "%s"' % (file,resource_name))
                #print(cwd, dir, file)
                os.chdir(cwd)

            #A reference to each tkinter.PhotoImage has to be manually kept
            #Otherwise it will be garbage collected without ever being displayed
            #Stashing them in the images dict just to make sure
            _images[resource_name] = image
            _resources[resource_name] = image
            bind_keys(image, boundkeys)

        bind_resource(RES_ROOT, make_root)
        bind_resource(RES_FRAME, make_frame)
        bind_resource(RES_LABEL_FRAME, make_labelframe)
        bind_resource(RES_MENU, make_menu)
        bind_resource(RES_NOTEBOOK, make_notebook)
        bind_resource(RES_LIST, make_list)
        bind_resource(RES_BUTTON, make_button)
        bind_resource(RES_TOGGLE_BUTTON, make_checkbutton)
        bind_resource(RES_LABEL, make_label)
        bind_resource(RES_FRAME_SEPARATOR, make_frameseparator)
        bind_resource(RES_TEXT_ENTRY, make_text)
        bind_resource(RES_TEXT_LINE_ENTRY, make_textentry)

        bind_resource(RES_STRING, make_string)
        bind_resource(RES_VOLATILE_STRING, make_volatilestring)
        bind_resource(RES_VOLATILE_BOOL, make_volatilebool)
        bind_resource(RES_IMAGE, make_image)
        bind_resource(RES_GENERIC_DATA, make_generic)

        bind_resource(SEND_MESSAGE, make_send_function)
        bind_resource(DISPLAY_RESOURCE, make_display_function)
        bind_resource(REQUEST_VOLATILE_UPDATE, make_update_function)
        bind_resource(CONDITIONAL_ACTION, make_conditional_function)

        self.bind_message(UPDATE_VOLATILE, update_volatile_resource)
        self.bind_message(SET_RESOURCE, set_resource)
        self.bind_message(SET_SETTING, set_setting)

    def request_resource(self, resource_name, block=False, timeout=1.0, force_refresh=False):
        """Conditional blocking: requests a resource."""
        if resource_name in self._resources:
            if force_refresh: del self._resources[resource_name]
            else: return self._resources[resource_name]
        #message format: command, args, response_to
        self._retrieved_resources.discard(resource_name)
        self.to_bashim_queue.put((GET_RESOURCE, (resource_name,), None))
        if block:
            self.wait_for_resources(resource_name, timeout)
            return self._resources[resource_name] if resource_name in self._resources else None

    def request_setting(self, setting_name, timeout=1.0):
        """Blocking: requests a setting."""
        #message format: command, args, response_to
        self._retrieved_settings.pop(setting_name, None)
        self.to_bashim_queue.put((GET_SETTING, (setting_name,), None))
        end_time = time() + timeout
        while setting_name not in self._retrieved_settings:
            if time() - end_time >= 0:
                raise TimeOutError('Timeout (%f) expired: setting "%s" not found!' % (timeout, setting_name))
            self.incoming(reregister=False) #Force updates until the request has been processed
        return self._retrieved_settings.pop(setting_name)

    def wait_for_resources(self, resource_names, timeout=1.0):
        """Blocks the process until all resources have been retrieved."""
        if not isinstance(resource_names, (tuple, list)):
            resource_names = [resource_names]
        resource_names = [resource_name for resource_name in resource_names if resource_name not in self._retrieved_resources]
        for resource_name in resource_names:
            end_time = time() + timeout
            while resource_name not in self._retrieved_resources:
                if time() - end_time >= 0:
                    raise TimeOutError('Timeout (%f) expired: resource "%s" not found!' % (timeout, resource_name))
                self.incoming(reregister=False) #Force updates until the request has been processed

    def set_resource(self, resource_name, value):
        """Sets a resource."""
        #message format: command, args, response_to
        self.to_bashim_queue.put((SET_RESOURCE, (resource_name,value), None))

    def drag_start(self, event, container):
        """Setup the container for tab dragging. Bit more expensive than optimal, but works."""
        x, y, widget = event.x, event.y, event.widget
        index = widget.index('@%d,%d' % (x, y))
        widget.dest_index = widget.start_index = index
        if index == '':
            return
        container.configure(cursor='hand2')

        drag_placer = self.request_resource('drag_placer', block=True)
        widget.image_placer = tkinter.Toplevel(background='#FFFFFF')
        ttk.Label(widget.image_placer, image=drag_placer, background = '#FFFFFF').pack()
        widget.image_placer.attributes('-transparentcolor', '#FFFFFF', '-alpha', 0.0)
        widget.image_placer.overrideredirect(True)

        widget.text_placer = tkinter.Toplevel(background='#FFFFFF')
        txt = ttk.Label(widget.text_placer, text=widget.tab(index, 'text'), background = '#FFFFFF')
        txt.pack()
        widget.text_placer.attributes('-transparentcolor', '#FFFFFF')
        widget.text_placer.overrideredirect(True)

        #find the bottom edge of the tabs
        testy = y
        testindex = index
        while testindex != '':
            testy += 1
            testindex = widget.index('@%d,%d' % (x, testy))
        widget.bottom_y = testy

        #find the edges of each tabs
        widget.edges = []
        widget.edge_tab = []
        testx = x
        testindex = index
        last_index = index
        while testindex != '':
            if testindex != last_index:
                widget.edges.append(testx)
                widget.edge_tab.append(last_index)
                last_index = testindex
            testx += 1
            testindex = widget.index('@%d,%d' % (testx, y))
        widget.edges.append(testx) #rightmost edge
        testx = x
        testindex = index
        last_index = index
        while testindex != '':
            if testindex != last_index:
                widget.edges.insert(0, testx)
                widget.edge_tab.insert(0, last_index)
                last_index = testindex
            testx -= 1
            testindex = widget.index('@%d,%d' % (testx, y))
        widget.edges.insert(0, testx) #leftmost edge
        widget.edge_tab.append(len(widget.edge_tab))
        widget.edge_tab.insert(0, 0)
        txt_width, txt_height, width, height, xoffset, yoffset = txt.winfo_reqwidth(), txt.winfo_reqheight(), drag_placer.width(), drag_placer.height(), self.root.winfo_rootx(), self.root.winfo_rooty()
        widget.drag_offsets = [txt_width, txt_height, width, height, xoffset, yoffset]
        widget.text_placer.geometry('%dx%d+%d+%d' %(txt_width, txt_height, xoffset+x+width, yoffset+y))

    def drag_end(self, event, container):
        x, y, widget = event.x, event.y, event.widget
        if widget.start_index == '': #dragging disabled
            del widget.start_index
            del widget.dest_index
            return
        if widget.dest_index != widget.start_index:
            container.insert(widget.dest_index, widget.start_index)
        widget.image_placer.destroy()
        widget.text_placer.destroy()
        del widget.image_placer
        del widget.text_placer
        del widget.edges
        del widget.start_index
        del widget.dest_index
        del widget.edge_tab
        del widget.drag_offsets
        container.configure(cursor='')

    def drag_in_progress(self, event, container):
        x, y, widget = event.x, event.y, event.widget
        if widget.start_index == '': #dragging disabled
            return
        index = widget.index('@%d,%d' % (x, widget.bottom_y - 1))
        txt_width, txt_height, width, height, xoffset, yoffset = widget.drag_offsets
        widget.text_placer.geometry('%dx%d+%d+%d' %(txt_width, txt_height, xoffset+x+width, yoffset+y))
        if index == widget.start_index:
            widget.image_placer.attributes('-alpha', 0.0)
            return
        edge = bisect.bisect_left(widget.edges, x)
        max_edge = len(widget.edges) - 1
        if edge > max_edge: edge = max_edge
        left_edge = widget.edges[edge - 1]
        right_edge = widget.edges[edge]
        middle = (left_edge + right_edge) // 2
        if x < middle: edge -= 1
        if edge < 0: edge = 0
        marked_edge = widget.edges[edge]
        widget.dest_index = widget.edge_tab[edge]
        widget.image_placer.attributes('-alpha', 1.0)
        widget.image_placer.geometry('%dx%d+%d+%d' %(width, height, marked_edge+xoffset-(width//2 + 1), widget.bottom_y+yoffset))

def pre_init():
    """Main Process: Initialize anything that is GUI dependent, and must be initialized before the GUI starts."""
    global resources, images, registered_afters
    resources = {} #GUI agnostic resources
    images = {} #GUI dependent resource
    registered_afters = {}

def main(top_working_dir, to_parent_queue, to_gui_queue, to_bashim_queue):
    """Main Process: Start the GUI"""
    pre_init()
    root = tkinter.Tk()
    cwd = os.getcwd()
    os.chdir(os.path.join(top_working_dir,'bash','compiled'))
    root.tk.eval('load shellicon.dll')
    os.chdir(cwd)
    app = Application(root, to_parent_queue, to_gui_queue, to_bashim_queue)
    root.mainloop()
    if not app._closed_reason:
        app.to_parent_queue.put((SHUTDOWN, (SYSTEM_REQUEST,), None))
        app._closed_reason = SYSTEM_REQUEST
    return app._closed_reason
