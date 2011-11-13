import os
import re
import time
import locale

from bash.common import norm_join, load_ini_settings, read_text_file
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
    def __init__(self, game_directory, plugin_list):
        self.game_type = 'SKY'
        self.game_directory = game_directory
        self.game_data_directory = norm_join(game_directory, 'Data')
        self.active_files_path = plugin_list
        self._resource_table = {}
        self._modify_table = {}
        self._set_table = {}
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
                return fr(RES_STRING, value='%s for Skyrim' % (title,))
            _modify_table['top_window_string'] = modify_title

        def init_tabs():
            pass

        def init_installers_tab_window():
            pass

        def init_mods_tab_window():
            _resource_table['mods_list'] = fl(RES_LIST,
                                              columns=(('mods_list_file_column','File'),
                                                       ('mods_list_order_column','Load Order'),
                                                       ('mods_list_installer_column','Installer'),
                                                       ('mods_list_time_column','Modified'),
                                                       ('mods_list_size_column','Size'),
                                                       ('mods_list_status_column','Status')
                                                      ),
                                              tags=('mods_list_master',
                                                    'mods_list_plugin',),
                                              active_tag = 'mods_list_active',
                                              inactive_tag = 'mods_list_inactive',
                                              on_activate='mods_list_activate',
                                              on_deactivate='mods_list_deactivate',
                                              on_setorder='mods_list_setorder',
                                              packargs={'fill':'BOTH',
                                                        'expand':True},
                                             )
            self._set_table['mods_list_activate'] = self.activate_mods
            self._set_table['mods_list_deactivate'] = self.deactivate_mods
            self._set_table['mods_list_setorder'] = self.set_mods_order

            _resource_table['mods_list_master'] = fl(RES_LIST_TAG,
                                                     resourceargs={'foreground':'blue',
                                                                  },
                                                     #right_click='text_context_menu',#'mods_list_master_context_menu',
                                                    )
            _resource_table['mods_list_plugin'] = fl(RES_LIST_TAG,
                                                     resourceargs={'foreground':'orange',
                                                                  },
                                                     #right_click='mods_list_regular_context_menu',
                                                     )
            _resource_table['mods_list_active'] = fl(RES_LIST_TAG,
                                                     resourceargs={'background':'white',
                                                                  },
                                                     #right_click='mods_list_regular_context_menu',
                                                     )
            _resource_table['mods_list_inactive'] = fl(RES_LIST_TAG,
                                                     resourceargs={'background':'grey',
                                                                  },
                                                     #right_click='mods_list_regular_context_menu',
                                                     )
##            _resource_table['mods_list_regular_context_menu'] = fm(RES_MENU,
##                                                      resources=('text_context_undo','menu_separator','text_context_select_all')
##                                                     )
            #magic variable
            _resource_table['mods_list_populate'] = fr(RES_GENERIC_DATA, value=self.get_mods_list())

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

    def get_active_mods(self, lowered=False):
        mods_text = read_text_file(self.active_files_path)
        reComment = re.compile('#.*')

        modNames = set()
        active_mods = []
        for line in mods_text.splitlines():
            modName = reComment.sub('',line).strip()
            if not modName: continue
            if lowered:
                modName = modName.lower()
            if modName not in modNames: #--In case it's listed twice.
                active_mods.append(modName)
                modNames.add(modName)
        return active_mods

    def get_mods_list(self):
        active_mods = self.get_active_mods(lowered=True)
        present_esms = []
        present_esps = []
        for file in os.listdir(self.game_data_directory):
            abs_path = norm_join(self.game_data_directory, file)
            if os.path.isfile(abs_path):
                file_name, file_ext = os.path.splitext(file)
                file_ext = file_ext.lower()
                tags = []
                if file_ext == '.esm':
                    tags.append('mods_list_master')
                    is_master = True
                elif file_ext == '.esp':
                    tags.append('mods_list_plugin')
                    is_master = False
                else:
                    continue

                if file.lower() in active_mods:
                    tags.append('mods_list_active')
                    status = 'Active'
                else:
                    tags.append('mods_list_inactive')
                    status = 'Inactive'

                file_data = {'id':file,
                             'mods_list_file_column':file,
                             'tags':tuple(tags),
                             'mods_list_time_column':time.strftime('%c',time.localtime(os.path.getmtime(abs_path))),
                             'mods_list_size_column':'%s KB' % (locale.format('%d',int(os.path.getsize(abs_path) / 1024),1),),
                             'mods_list_installer_column':'',
                             'mods_list_status_column': status,
                             }
                self._resource_table[file] = fr(RES_GENERIC_DATA, value=file_data)
                if is_master:
                    present_esms.append(file_data)
                else:
                    present_esps.append(file_data)
        present_esms.sort(key=lambda file_data: file_data['mods_list_time_column'])
        present_esps.sort(key=lambda file_data: file_data['mods_list_time_column'])
        present_mods = present_esms + present_esps
        for index, file_data in enumerate(present_mods):
            file_data['mods_list_order_column'] = '%02X' % (index,)
        return tuple(present_mods)

    def set_mods_order(self, mods_list):
        mtime = time.mktime(time.strptime("11 11 2011", "%m %d %Y"))
        esms = []
        esps = []
        for mod in mods_list:
            file_name, file_ext = os.path.splitext(mod)
            file_ext = file_ext.lower()
            if file_ext == '.esm':
                esms.append(mod)
            else:
                esps.append(mod)

        for index, mod in enumerate(esms + esps):
            abs_path = norm_join(self.game_data_directory, mod)
            data_type, mod_data = self._resource_table[mod]
            atime = os.path.getatime(abs_path)
            os.utime(abs_path,(atime,int(mtime)))
            mod_data['mods_list_time_column'] = time.strftime('%c',time.localtime(os.path.getmtime(abs_path)))
            mod_data['mods_list_order_column'] = '%02X' % (index,)
            mtime += 60
            #print(mod, '%02X' % (index,))
            #print(mod, self._resource_table[mod])

        self.set_mods_list(mods_list)

    def set_mods_list(self, mods_list):
        mods_list.sort()
        temp_name = '%s_bash.tmp' % (self.active_files_path,)
        backup_name = '%s_bash.bak' % (self.active_files_path,)
        with open(temp_name, 'w') as out:
            out.write('# This file is used to tell Skyrim which data files to load.\n\n')
            for modName in mods_list:
                out.write('%s\n' % (modName,))
        if os.path.exists(backup_name):
            os.remove(backup_name)
        os.rename(self.active_files_path, backup_name)
        os.rename(temp_name, self.active_files_path)

    def get_resource(self, resource_name, resource):
        modify_function = self._modify_table.get(resource_name)
        if modify_function:
            return modify_function(resource)
        else:
            #print(resource_name)
            return self._resource_table.get(resource_name, resource)

    def activate_mods(self, mods):
        active_mods = self.get_active_mods()
        insensitive_active = set([plugin.lower() for plugin in active_mods])
        added = False
        for mod in mods:
            insensitive_mod = mod.lower()
            if insensitive_mod not in insensitive_active:
                active_mods.append(mod)
                insensitive_active.add(insensitive_mod)
                data_type, mod_data = self._resource_table[mod]
                mod_data['mods_list_status_column'] = 'Active'
                added = True
        if added:
            self.set_mods_list(active_mods)

    def deactivate_mods(self, mods):
        active_mods = self.get_active_mods()
        insensitive_active = set([plugin.lower() for plugin in active_mods])
        removed = False
        for mod in mods:
            insensitive_mod = mod.lower()
            if insensitive_mod in insensitive_active:
                active_mods.remove(mod)
                insensitive_active.remove(insensitive_mod)
                data_type, mod_data = self._resource_table[mod]
                mod_data['mods_list_status_column'] = 'Inactive'
                removed = True
        if removed:
            self.set_mods_list(active_mods)

    def set_resource(self, resource_name, value):
        set_function = self._set_table.get(resource_name)
        if resource_name in self._set_table:
            return set_function(value)
        return None
