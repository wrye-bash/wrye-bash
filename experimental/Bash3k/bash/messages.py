# -*- coding: utf-8 -*-

#Using strings as messages for debugging.
#Switch to enum for production code (using message_id_to_str to convert to string as needed)
#all enums start at value = 1 so that a simple conditional test can distinguish it from False or None

##bashim_process_id = 1
##basher_process_id = 2
##parent_process_id = 3

bashim_process_id = 'BASHIM' #1
basher_process_id = 'GUI' #2
parent_process_id = 'PARENT' #3


message_id_to_str = ('SHUTDOWN','CLOSE_PROCESS','RESTART',
                     'IS_CONNECTION_READY','CONNECTION_READY',
                     'IS_ALIVE_REQ','IS_ALIVE_ACK',
                     'SET_RESOURCE','GET_RESOURCE',
                     'SET_SETTING','GET_SETTING',
                     'DISPLAY_RESOURCE','SEND_MESSAGE',
                     'REQUEST_VOLATILE_UPDATE','UPDATE_VOLATILE',
                     'TOGGLE_SETTING','LAUNCH_PROGRAM','CONDITIONAL_ACTION')

opt_id_to_str = ('SYSTEM_REQUEST','USER_REQUEST','SYSTEM_ERROR')

resource_id_to_str = ('RES_STRING','RES_VOLATILE_STRING','RES_IMAGE',
                      'RES_ROOT','RES_WINDOW','RES_FRAME',
                      'RES_NOTEBOOK','RES_NOTEBOOK_TAB',
                      'RES_MENU','RES_MENU_CASCADE',
                      'RES_MENU_COMMAND','RES_MENU_SEPARATOR',
                      'RES_MENU_CHECKBUTTON','RES_MENU_RADIOBUTTON',
                      'RES_BUTTON','RES_TOGGLE_BUTTON',
                      'RES_FRAME_SEPARATOR',
                      'RES_LABEL','RES_LABEL_FRAME',
                      'RES_LIST','RES_LIST_TAG',#'RES_LIST_COLUMN',
                      'RES_TEXT_ENTRY','RES_TEXT_LINE_ENTRY',
                      'RES_VOLATILE_UPDATE','RES_VOLATILE_BOOL',
                      'RES_GENERIC_DATA')

enums = (message_id_to_str, opt_id_to_str, resource_id_to_str)
for enum in enums:
    for value, attr in enumerate(enum, start=1):
    ##    vars()[attr] = value
        vars()[attr] = attr

del enums
del enum
del value
del attr

class TimeOutError(Exception):
    def __init__(self, value):
        self.value = value

    def __str__(self):
        return repr(self.value)

class ResourceError(Exception):
    def __init__(self, value):
        self.value = value

    def __str__(self):
        return "Unable to locate resource: '%s'" % (repr(self.value),)

def format_program(program_path, name=None, args=None, wd=None, icon=None):
    """Helper function for formatting launchable applications"""
    return (program_path, name, icon, args, wd)

def format_action(action,
                  target=None,
                  message=None,
                  text=None,
                  actionargs={},
                  variable=None,
                  true_result=None,
                  false_result=None):
    """Helper function for formatting containers (windows/frames/etc)"""
    if action == DISPLAY_RESOURCE:
        return (DISPLAY_RESOURCE,text)
    elif action == SEND_MESSAGE:
        return (SEND_MESSAGE,(target,message))
    elif action == REQUEST_VOLATILE_UPDATE:
        return (REQUEST_VOLATILE_UPDATE, target)
    elif action == CONDITIONAL_ACTION:
        return (CONDITIONAL_ACTION, (variable, true_result, false_result))

def format_keys(right_click=None,
                left_click=None,
                middle_click=None,
                right_down=None,
                left_down=None,
                middle_down=None,
                right_up=None,
                left_up=None,
                middle_up=None):
    """Helper function for formatting bound keys"""
    keys = {}
    if right_click is not None:
        keys['right_click'] = right_click
    if left_click is not None:
        keys['left_click'] = left_click
    if middle_click is not None:
        keys['middle_click'] = middle_click
    if right_down is not None:
        keys['right_down'] = right_down
    if left_down is not None:
        keys['left_down'] = left_down
    if middle_down is not None:
        keys['middle_down'] = middle_down
    if right_up is not None:
        keys['right_up'] = right_up
    if left_up is not None:
        keys['left_up'] = left_up
    if middle_up is not None:
        keys['middle_up'] = middle_up
    if not keys.keys():
        return None
    return keys

def format_container(resource,
                     resourceargs={},
                     packargs={},
                     windowargs={},
                     resources=(),
                     right_click=None,
                     left_click=None,
                     middle_click=None,
                     right_down=None,
                     left_down=None,
                     middle_down=None,
                     right_up=None,
                     left_up=None,
                     middle_up=None):
    """Helper function for formatting containers (windows/frames/etc)"""
    #tkinter window args (standard):
    # aspect, fullscreen, topmost, alpha, disabled, toolwindow,
    # transparentcolor, deiconify, focusmodel, iconbitmap,
    # iconify, iconposition, maxsize, minsize, WM_DELETE_WINDOW,
    # resizable, state, title
    #tkinter pack args (standard):
    # after, anchor, before, expand, fill, in_,
    # ipadx, ipady, padx, pady, side
    keys = format_keys(right_click,left_click,middle_click,right_down,left_down,middle_down,right_up,left_up,middle_up)
    if resource == RES_ROOT:
        #tkinter container args (standard):
        # cursor, takefocus,
        #tkinter container args (specific):
        # borderwidth (bd), relief, padx, pady, width, height,
        # menu, background (bg),
        # highlightbackground, highlightcolor,
        # highlightthickness
        #Notes:
        #title is automatically filled in by the resource_name_string resource unless it is manually set
        return (RES_ROOT,
                (resourceargs,
                 windowargs,
                 resources,
                 keys
                )
               )
    elif resource == RES_FRAME:
        #ttk container args (standard):
        # cursor, style, takefocus
        #ttk container args (specific):
        # borderwidth, relief, padding, width, height
        return (RES_FRAME,
                (resourceargs,
                 packargs,
                 resources,
                 keys
                )
               )
    elif resource == RES_LABEL_FRAME:
        #ttk container args (standard):
        # cursor, style, takefocus
        #ttk container args (specific):
        # labelanchor, text, underline, padding, labelwidget, width, height
        #Notes:
        #text is automatically filled in by the resource_name_string resource unless it is manually set
        return (RES_LABEL_FRAME,
                (resourceargs,
                 packargs,
                 resources,
                 keys
                )
               )
    elif resource == RES_NOTEBOOK:
        #ttk container args (standard):
        # cursor, style, takefocus
        #ttk container args (specific):
        # height, padding, width,
        #ttk custom args:
        # enableTraversal, tab_changed
        return (RES_NOTEBOOK,
                (resourceargs,
                 packargs,
                 windowargs,
                 resources,
                 keys
                )
               )
    elif resource == RES_NOTEBOOK_TAB:
        #ttk container args (override):
        # state, sticky, padding, text,
        # image, compound, underline
        #ttk custom args:
        # hidden, selected, tab_changed
        #Notes:
        #text is automatically filled in by the resource_name_string resource unless it is manually set
        return (RES_NOTEBOOK_TAB,
                (resourceargs,
                 windowargs,
                 resources, #resource_id of a container (typically a frame)
                 keys
                )
               )

def format_list(resource,
                resourceargs={},
                packargs={},
                customargs={},
                columnargs={},
                resources=(),
                columns=(),
                tags=(),
                active_tag=None,
                inactive_tag=None,
                on_activate=None,
                on_deactivate=None,
                on_setorder=None,
                right_click=None,
                left_click=None,
                middle_click=None,
                right_down=None,
                left_down=None,
                middle_down=None,
                right_up=None,
                left_up=None,
                middle_up=None):
    """Helper function for formatting list views"""
    keys = format_keys(right_click,left_click,middle_click,right_down,left_down,middle_down,right_up,left_up,middle_up)
    if resource == RES_LIST:
        #ttk container args (standard):
        # cursor, style, takefocus, xscrollcommand, yscrollcommand

        #ttk container args (specific):
        # columns, displaycolumns, height, padding, selectmode, show

        #ttk list args (override):
        # columns
        #Notes:
        #xscrollcommand, yscrollcommand are set to allow scrolling
        #columns format is overridden by a ((id,name),...) tuple
        #show is automatically set to "headings"
        return (RES_LIST,
                (resourceargs,
                 packargs,
                 columns,
                 tags,
                 (active_tag,inactive_tag),
                 (on_activate,on_deactivate),
                 on_setorder,
                 keys
                )
               )
    elif resource == RES_LIST_TAG:
        #ttk list args (specific):
        # foreground, background, font, image

        return (RES_LIST_TAG,
                (resourceargs,
                 keys
                )
               )


##    elif resource == RES_LIST_COLUMN:
##        #ttk heading args (override):
##        # text, image, anchor, command
##
##        #ttk column args (override):
##        # anchor, minwidth, stretch, width
##
##        #Notes:
##        #text is automatically filled in by the resource_name_string resource unless it is manually set
##        #command is defaulted to sort/reverse sort the list by that column
##        return (RES_LIST_COLUMN,
##                (resourceargs,
##                 columnargs,
##                 keys
##                )
##               )

def format_menu(resource, resourceargs={}, customargs={}, actions=(), resources=()):
    """Helper function for formatting menus"""
    if resource == RES_MENU:
        #tkinter resource args (standard):
        # activebackground, activeborderwidth,
        # activeforeground, background (bg),
        # borderwidth (bd), cursor,
        # disabledforeground, font,
        # foreground (fg), relief, takefocus
        #tkinter resource args (specific):
        # postcommand, selectcolor,
        # tearoff, tearoffcommand, title
        #tkinter resource args (custom):
        # post_up
        return (RES_MENU,
                (resourceargs,
                 customargs,
                 resources
                )
               )
    elif resource == RES_MENU_CASCADE:
        #tkinter resource args (specific):
        # activebackground, activeforeground,
        # accelerator, background,
        # bitmap, columnbreak,
        # command, compound,
        # font, foreground, hidemargin,
        # image, label,
        # menu, state, underline
        #Notes:
        #command is technically available, but doesn't work on windows, so isn't accepted
        #menu is automatically filled in based on the call hierarchy unless it is manually set
        return (RES_MENU_CASCADE,
                (resourceargs,
                 resources
                )
               )
    elif resource == RES_MENU_COMMAND:
        #tkinter resource args (specific):
        # activebackground, activeforeground,
        # accelerator, background,
        # bitmap, columnbreak,
        # command, compound,
        # font, foreground, hidemargin,
        # image, label, state, underline
        #Notes:
        #command is automatically filled in by a composite of actions unless it is manually set
        #label is automatically filled in by the resource_name_string resource unless it is manually set
        return (RES_MENU_COMMAND,
                (resourceargs,
                 actions
                )
               )
    elif resource == RES_MENU_SEPARATOR:
        #tkinter resource args (specific):
        # columnbreak, hidemargin
        return (RES_MENU_SEPARATOR,
                resourceargs
               )
    elif resource == RES_MENU_CHECKBUTTON:
        #tkinter resource args (specific):
        # activebackground, activeforeground,
        # accelerator, background,
        # bitmap, columnbreak,
        # command, compound,
        # font, foreground, hidemargin,
        # image, indicatoron, label,
        # offvalue, onvalue,
        # selectcolor, selectimage, state,
        # underline, variable
        #Notes:
        #command is automatically filled in by a composite of actions unless it is manually set
        #label is automatically filled in by the resource_name_string resource unless it is manually set
        return (RES_MENU_CHECKBUTTON,
                (resourceargs,
                 actions
                )
               )
    elif resource == RES_MENU_RADIOBUTTON:
        #tkinter resource args (specific):
        # activebackground, activeforeground,
        # accelerator, background,
        # bitmap, columnbreak,
        # command, compound,
        # font, foreground, hidemargin,
        # image, indicatoron, label,
        # selectcolor, selectimage, state,
        # underline, value, variable
        #Notes:
        #command is automatically filled in by a composite of actions unless it is manually set
        #label is automatically filled in by the resource_name_string resource unless it is manually set
        return (RES_MENU_RADIOBUTTON,
                (resourceargs,
                 actions
                )
               )

def format_resource(resource,
                    value=None,
                    resourceargs={},
                    packargs={},
                    customargs={},
                    actions=(),
                    resources=(),
                    right_click=None,
                    left_click=None,
                    middle_click=None,
                    right_down=None,
                    left_down=None,
                    middle_down=None,
                    right_up=None,
                    left_up=None,
                    middle_up=None):
    """Helper function for formatting resources"""
    #tkinter pack args (standard):
    # after, anchor, before, expand, fill, in_,
    # ipadx, ipady, padx, pady, side
##            #tkinter grid args:
##            # anchor, expand, fill, in_, ipadx, ipady, padx, pady, side
##            #Warning: Never mix grid and pack in the same master window.
    keys = format_keys(right_click,left_click,middle_click,right_down,left_down,middle_down,right_up,left_up,middle_up)

    if resource == RES_FRAME_SEPARATOR:
        #ttk resource args (standard):
        # cursor, state, style, takefocus
        #ttk resource args (specific):
        # orient
        return (RES_FRAME_SEPARATOR,
                (resourceargs,
                 packargs
                )
               )
    elif resource == RES_BUTTON:
        #ttk resource args (standard):
        # compound, cursor, image, state,
        # style, takefocus, text, textvariable,
        # underline, width
        #ttk resource args (specific):
        # command, default
        #Notes:
        #text is automatically filled in by the resource_name_string resource unless it is manually set
        #textvariable is automatically filled in by the resource_name_vstring resource unless it is manually set
        #command is automatically filled in by a composite of actions unless it is manually set
        return (RES_BUTTON,
                (resourceargs,
                 packargs,
                 customargs,
                 actions,
                 keys
                )
               )
    elif resource == RES_TOGGLE_BUTTON:
        #ttk resource args (standard):
        # compound, cursor, image, state,
        # style, takefocus, text, textvariable,
        # underline, width
        #ttk resource args (specific):
        # command, offvalue, onvalue, variable
        #ttk resource args (custom):
        # on_image, off_image, tooltip
        #Notes:
        #text is automatically filled in by the resource_name_string resource unless it is manually set
        #textvariable is automatically filled in by the resource_name_vstring resource unless it is manually set
        #command is automatically filled in by a composite of actions unless it is manually set
        #image is automatically filled in by on_image, off_image unless it is manually set
        return (RES_TOGGLE_BUTTON,
                (resourceargs,
                 packargs,
                 customargs,
                 actions,
                 keys
                )
               )
    elif resource == RES_LABEL:
        #ttk resource args (standard):
        # compound, cursor, image, state,
        # style, takefocus, text, textvariable,
        # underline, width
        #ttk resource args (specific):
        # anchor, background, font, foreground,
        # justify, padding, relief, wraplength
        #Notes:
        #text is automatically filled in by the resource_name_string resource unless it is manually set
        #textvariable is automatically filled in by the resource_name_vstring resource unless it is manually set
        return (RES_LABEL,
                (resourceargs,
                 packargs,
                 keys
                )
               )
    elif resource == RES_TEXT_ENTRY:
        #tkinter resource args (standard):
        # background (bg), borderwidth (bd), cursor,
        # exportselection, font, foreground (fg), highlightbackground,
        # highlightcolor, highlightthickness, insertbackground,
        # insertborderwidth, insertofftime, insertontime,
        # insertwidth, padx, pady, relief, selectbackground,
        # selectborderwidth, selectforeground, setgrid, takefocus

        #tkinter resource args (specific):
        # autoseparators, blockcursor, endline, height,
        # inactiveselectbackground, maxundo, spacing1,
        # spacing2, spacing3, startline, state, tabs,
        # tabstyle, undo, width, wrap

        #tkinter resource args (custom):
        # text, maxchars, onmodified, xscrolling, yscrolling
        #Notes:
        #text is automatically filled in by the resource_name_string resource unless it is manually set
        #xscrollcommand is automatically set to support a scrollbar if xscrolling is true
        #yscrollcommand is automatically set to support a scrollbar if yscrolling is true
        return (RES_TEXT_ENTRY,
                (resourceargs,
                 packargs,
                 customargs,
                 keys
                )
               )
    elif resource == RES_TEXT_LINE_ENTRY:
        #ttk resource args (standard):
        # cursor, style, takefocus

        #tkinter resource args (specific):
        # exportselection, invalidcommand, justify,
        # show, state, textvariable, validate,
        # validatecommand, width

        #tkinter resource args (custom):
        # text, maxchars, onmodified, xscrolling
        #Notes:
        #text is automatically filled in by the resource_name_string resource unless it is manually set
        #xscrollcommand is automatically set to support a scrollbar if xscrolling is true
        #onmodified is only called if the entry is validated
        return (RES_TEXT_LINE_ENTRY,
                (resourceargs,
                 packargs,
                 customargs,
                 keys
                )
               )
    elif resource == RES_STRING:
        #Use will automatically set text of the associated resource
        return (RES_STRING, value)
    elif resource == RES_VOLATILE_STRING:
        #Use will automatically set textvariable of the associated resource
        return (RES_VOLATILE_STRING, value)
    elif resource == RES_VOLATILE_BOOL:
        return (RES_VOLATILE_BOOL, value)
    elif resource == RES_IMAGE:
        return (RES_IMAGE,
                (value,
                 keys
                )
               )
    elif resource == RES_VOLATILE_UPDATE:
        return (RES_VOLATILE_UPDATE, value)
    elif resource == RES_GENERIC_DATA:
        return (RES_GENERIC_DATA, value)
