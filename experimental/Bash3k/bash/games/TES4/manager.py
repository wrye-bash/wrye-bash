import os

from bash.common import norm_join, load_ini_settings
from bash.profiles import UserProfile
from bash.messages import *
fr = format_resource
fm = format_menu
fa = format_action
fc = format_container
fl = format_list
fp = format_program

#Some resources are hardcoded, and must be present:
#top_window
#text_context_menu

#Some resource ids are 'magic', they just have to be defined to be used:
#resource_id + '_string', used for any resource that needs a string
#resource_id + '_vstring', used for any resource that needs a volatile string

#action_ids are deliberately limiting to prevent excess code from creeping into the UI over time.
#If something complicated needs doing, use the SEND_MESSAGE action with bashim as the target process, and have the logic there.

class GameManager:
    """Responsible for loading, retrieving, and/or creating requested TES4 specific resources."""
    def __init__(self, game_directory):
        self.game_type = 'TES4'
        self.game_directory = game_directory
        self._resource_table = {}
        self._modify_table = {}
        self.init_resources()

    def init_resources(self):
        _resource_table = self._resource_table
        _modify_table = self._modify_table
        self.init_windows()
        self.init_menus()
        self.init_statusbar()

    def init_windows(self):
        _resource_table = self._resource_table
        _modify_table = self._modify_table

        def init_top_window():
            def modify_title(args):
                type, title = args
                return fr(RES_STRING, value='%s for Oblivion' % (title,))
            _modify_table['top_window_string'] = modify_title

        def init_tabs():
            pass

        def init_installers_tab_window():
            pass

        def init_mods_tab_window():
            pass

        def init_saves_tab_window():
            pass

        def init_pm_tab_window():
            pass

        def init_screenshots_tab_window():
            pass

        def init_people_tab_window():
            pass

        def init_ini_tab_window():
            pass

        init_top_window()
        init_tabs()
        init_installers_tab_window()
        init_mods_tab_window()
        init_saves_tab_window()
        init_pm_tab_window()
        init_screenshots_tab_window()
        init_people_tab_window()
        init_ini_tab_window()

    def init_menus(self):
        _resource_table = self._resource_table
        _modify_table = self._modify_table

        def init_top_window_menubar():
            pass

        def init_text_context_menu():
            pass

        init_top_window_menubar()
        init_text_context_menu()

    def init_statusbar(self):
        _resource_table = self._resource_table
        _modify_table = self._modify_table
        pass

    def get_resource(self, resource_name, resource):
        modify_function = self._modify_table.get(resource_name)
        if modify_function:
            return modify_function(resource)
        else:
            return self._resource_table.get(resource_name, resource)
