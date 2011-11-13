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

class ResourceManager:
    """Responsible for loading, retrieving, and/or creating requested resources."""
    def __init__(self, top_working_dir):
        self.top_working_dir = top_working_dir
        self._resource_table = {}
        self._app_table = {}
        self.profiles = []
        self.current_profile = None
        self.profiles_dir = None
        self.init_profiles()
        self.init_resources()
        game_type = self.current_profile.game_type
        if game_type == 'TES3':
            from bash.games.TES3.manager import GameManager
        elif game_type == 'TES4':
            from bash.games.TES4.manager import GameManager
        elif game_type == 'FO3':
            from bash.games.FO3.manager import GameManager
        elif game_type == 'FNV':
            from bash.games.FNV.manager import GameManager
        elif game_type == 'SKY':
            from bash.games.SKY.manager import GameManager
        self.game_manager = GameManager(self.current_profile.game_directory, self.current_profile.game_plugin_list)
        del GameManager

    def init_profiles(self):
        """Load profiles. Create an empty profile if none exist."""
        profiles = self.profiles
        self.profiles_dir = norm_join(self.top_working_dir, 'Profiles')
        profile_base_settings_path = norm_join(self.profiles_dir, 'profiles.ini')

        profiles_settings = load_ini_settings(profile_base_settings_path)

        loaded_profiles = set()
        profile_paths = profiles_settings['Global.DisplayOrder'] + [profile for profile in os.listdir(self.profiles_dir) if os.path.isdir(norm_join(self.profiles_dir, profile))]
        for profile in profile_paths:
            profile_dir = norm_join(self.profiles_dir, profile)
            profile_settings_path = norm_join(profile_dir, 'profile.ini')
            if profile_settings_path not in loaded_profiles and os.path.exists(profile_settings_path):
                loaded_profiles.add(profile_settings_path)
                loaded_profile = UserProfile(profile_dir)
                profiles.append(loaded_profile)
                if profile == profiles_settings['Global.Active']:
                    loaded_profile.set_active()
                    self.current_profile = loaded_profile
                elif self.current_profile is None:
                    self.current_profile = loaded_profile

    def toggle_setting(self, resource_id):
        _settings = self.current_profile._settings
        _settings[resource_id] = not _settings[resource_id]

    def get_setting(self, setting_id, setting_value):
        _settings = self.current_profile._settings
        return _settings.get(setting_id, setting_value)

    def init_resources(self):
        _resource_table = self._resource_table
        img_dir = norm_join(self.top_working_dir,'bash','games','images')
        _resource_table['img_dir'] = fr(RES_STRING, value=img_dir)

        _resource_table['tab_close'] = fr(RES_IMAGE, norm_join(img_dir, 'transparent16.gif'))
        _resource_table['tab_close_active'] = fr(RES_IMAGE, norm_join(img_dir, 'checkbox_green_off.gif'))
        _resource_table['tab_close_pressed'] = fr(RES_IMAGE, norm_join(img_dir, 'checkbox_green_on.gif'))
        _resource_table['drag_placer'] = fr(RES_IMAGE, norm_join(img_dir, 'fat_up.gif'))

        self.init_windows()
        self.init_menus()
        self.init_statusbar()

    def init_windows(self):
        _resource_table = self._resource_table
        _settings = self.current_profile._settings
        def init_top_window():
            def make_title():
                #return _settings['Profile.Name']
                return 'Wrye Bash3k Pre-Alpha: %s' % (_settings['Profile.Name'],)
            _resource_table['top_window'] = fc(RES_ROOT,
                                               windowargs={'minsize':(640, 480)},
                                               resourceargs={'menu':'top_window_menubar'},
                                               resources=('top_window_tabs','top_window_statusbar')
                                              )
            _resource_table['top_window_string'] = fr(RES_STRING, value=make_title())
            _resource_table['top_window_tabs'] = fc(RES_NOTEBOOK,
                                                    resourceargs={'height':200},
                                                    packargs={'expand':True,
                                                              'anchor':'N',
                                                              'fill':'BOTH',
                                                              'side':'TOP'},
                                                    resources=('installers_tab','mods_tab',
                                                               'saves_tab','pm_tab','screenshots_tab',
                                                               'people_tab','ini_tab')
                                                   )
        def init_tabs():
            _resource_table['installers_tab'] = fc(RES_NOTEBOOK_TAB,
                                                   resourceargs={'state':'DISABLED'},
                                                   resources='installers_tab_window'
                                                  )
            _resource_table['installers_tab_string'] = fr(RES_STRING, value='Installers    ')
            _resource_table['mods_tab'] = fc(RES_NOTEBOOK_TAB,
                                             windowargs={'selected':True},
                                             resources='mods_tab_window'
                                            )
            _resource_table['mods_tab_string'] = fr(RES_STRING, value='Mods    ')
            _resource_table['saves_tab'] = fc(RES_NOTEBOOK_TAB,
                                              resourceargs={'state':'DISABLED'},
                                              resources='saves_tab_window'
                                             )
            _resource_table['saves_tab_string'] = fr(RES_STRING, value='Saves    ')
            _resource_table['pm_tab'] = fc(RES_NOTEBOOK_TAB,
                                           resourceargs={'state':'DISABLED'},
                                           resources='pm_tab_window'
                                          )
            _resource_table['pm_tab_string'] = fr(RES_STRING, value='PM Archive    ')
            _resource_table['screenshots_tab'] = fc(RES_NOTEBOOK_TAB,
                                                    resourceargs={'state':'DISABLED'},
                                                    resources='screenshots_tab_window'
                                                   )
            _resource_table['screenshots_tab_string'] = fr(RES_STRING, value='Screenshots    ')
            _resource_table['people_tab'] = fc(RES_NOTEBOOK_TAB,
                                               resourceargs={'state':'DISABLED'},
                                               resources='people_tab_window'
                                              )
            _resource_table['people_tab_string'] = fr(RES_STRING, value='People    ')
            _resource_table['ini_tab'] = fc(RES_NOTEBOOK_TAB,
                                            resourceargs={'state':'DISABLED'},
                                            resources='ini_tab_window'
                                           )
            _resource_table['ini_tab_string'] = fr(RES_STRING, value='INI Edits    ')
        def init_installers_tab_window():
            _resource_table['installers_tab_window'] = fc(RES_FRAME)
        def init_mods_tab_window():
            _resource_table['mods_tab_window'] = fc(RES_FRAME,
                                                    packargs={'side':'TOP',
                                                              'fill':'BOTH',
                                                              'expand':True},
                                                    resources=('mods_tab_mods',
                                                               #'mods_tab_details'
                                                              )
                                                   )
            _resource_table['mods_tab_mods'] = fc(RES_LABEL_FRAME,
                                                  packargs={'side':'LEFT',
                                                            'fill':'BOTH',
                                                            'expand':True},
                                                  resources=('mods_list',)
                                                 )
            _resource_table['mods_tab_mods_string'] = fr(RES_STRING, value='Mods')
            #mods_list defined in the GameManager

##            _resource_table['mods_tab_details'] = fc(RES_LABEL_FRAME,
##                                                     packargs={'side':'RIGHT',
##                                                               'fill':'BOTH',
##                                                               'expand':False},
##                                                     resources=('details_file_version',
##                                                                'details_file_entry',
##                                                                'details_author',
##                                                                'details_author_entry',
##                                                                'details_modified',
##                                                                'details_modified_entry',
##                                                                'details_description',
##                                                                'details_description_entry',
##                                                                'details_masters',
##                                                                'details_masters_entry',
##                                                                'details_save_cancel',
##                                                                'details_bash_tags',
##                                                                'details_bash_tags_entry',
##                                                                )
##                                                    )
##            _resource_table['mods_tab_details_string'] = fr(RES_STRING, value='Mod Details')
##
##            _resource_table['details_file_version'] = fc(RES_FRAME,
##                                                         packargs={'side':'TOP',
##                                                                   'fill':'X',
##                                                                   'padx':0,
##                                                                   'pady':0
##                                                                  },
##                                                         resources=('details_file',
##                                                                    'details_version'
##                                                                   )
##                                                        )
##
##            _resource_table['details_file'] = fr(RES_LABEL,
##                                                 resourceargs={'anchor':'W'},
##                                                 packargs={'side':'LEFT',
##                                                           'fill':'X',
##                                                           'padx':0,
##                                                           'pady':0,
##                                                           'anchor':'NW'
##                                                          }
##                                                )
##            _resource_table['details_file_string'] = fr(RES_STRING, value='File:')
##
##            _resource_table['details_version'] = fr(RES_LABEL,
##                                                    resourceargs={'anchor':'E'},
##                                                    packargs={'side':'RIGHT',
##                                                              'fill':'X',
##                                                              'padx':0,
##                                                              'pady':0,
##                                                              'anchor':'NE'
##                                                             }
##                                                   )
##            _resource_table['details_version_vstring'] = fr(RES_VOLATILE_STRING, value='v1.0')
##
##            _resource_table['details_file_entry'] = fr(RES_TEXT_LINE_ENTRY,
##                                                       resourceargs={'width':35},
##                                                       packargs={'side':'TOP', 'fill':'X','padx':0, 'pady':0}
##                                                      )
##
##            _resource_table['details_author'] = fr(RES_LABEL,
##                                                   resourceargs={'anchor':'W'},
##                                                   packargs={'side':'TOP',
##                                                             'fill':'X',
##                                                             'padx':0,
##                                                             'pady':0,
##                                                             'anchor':'NW'
##                                                            }
##                                                  )
##            _resource_table['details_author_string'] = fr(RES_STRING, value='Author:')
##            _resource_table['details_author_entry'] = fr(RES_TEXT_LINE_ENTRY,
##                                                         resourceargs={'width':35},
##                                                         packargs={'side':'TOP', 'fill':'X','padx':0, 'pady':0}
##                                                        )
##
##            _resource_table['details_modified'] = fr(RES_LABEL,
##                                                     resourceargs={'anchor':'W'},
##                                                     packargs={'side':'TOP',
##                                                               'fill':'X',
##                                                               'padx':0,
##                                                               'pady':0,
##                                                               'anchor':'NW'
##                                                              }
##                                                    )
##            _resource_table['details_modified_string'] = fr(RES_STRING, value='Modified:')
##            _resource_table['details_modified_entry'] = fr(RES_TEXT_LINE_ENTRY,
##                                                           resourceargs={'width':35},
##                                                           packargs={'side':'TOP', 'fill':'X','padx':0, 'pady':0}
##                                                          )
##
##            _resource_table['details_description'] = fr(RES_LABEL,
##                                                        resourceargs={'anchor':'W'},
##                                                        packargs={'side':'TOP',
##                                                                  'fill':'X',
##                                                                  'padx':0,
##                                                                  'pady':0,
##                                                                  'anchor':'NW'
##                                                                 }
##                                                       )
##            _resource_table['details_description_string'] = fr(RES_STRING, value='Description:')
##            _resource_table['details_description_entry'] = fr(RES_TEXT_ENTRY,
##                                                              resourceargs={'height':1,
##                                                                            'wrap':'WORD',
##                                                                            'width':24},
##                                                              packargs={'side':'TOP',
##                                                                        'fill':'BOTH',
##                                                                        'padx':0,
##                                                                        'pady':0,
##                                                                        'expand':True
##                                                                       },
##                                                              customargs={'maxchars':512,
##                                                                          'yscrolling':True}
##                                                             )
##
##            _resource_table['details_masters'] = fr(RES_LABEL,
##                                                    resourceargs={'anchor':'W'},
##                                                    packargs={'side':'TOP',
##                                                              'fill':'X',
##                                                              'padx':0,
##                                                              'pady':0,
##                                                              'anchor':'NW'
##                                                             }
##                                                   )
##            _resource_table['details_masters_string'] = fr(RES_STRING, value='Masters:')
##            _resource_table['details_masters_entry'] = fl(RES_LIST,
##                                                          resources=('details_masters_file',
##                                                                     'details_masters_index',
##                                                                     'details_masters_order'),
##                                                          resourceargs={'height':3},
##                                                          packargs={'side':'TOP',
##                                                                    'fill':'BOTH',
##                                                                    'padx':0,
##                                                                    'pady':0,
##                                                                    'expand':False
##                                                                   }
##                                                         )
##
##            _resource_table['details_masters_file'] = fl(RES_LIST_COLUMN)
##            _resource_table['details_masters_file_string'] = fr(RES_STRING, value='File')
##
##            _resource_table['details_masters_index'] = fl(RES_LIST_COLUMN)
##            _resource_table['details_masters_index_string'] = fr(RES_STRING, value='MI')
##
##            _resource_table['details_masters_order'] = fl(RES_LIST_COLUMN)
##            _resource_table['details_masters_order_string'] = fr(RES_STRING, value='Current LO')
##
##            _resource_table['details_save_cancel'] = fc(RES_FRAME,
##                                                        packargs={'side':'TOP',
##                                                                  'fill':'X',
##                                                                  'padx':0,
##                                                                  'pady':0
##                                                                 },
##                                                        resources=('details_save',
##                                                                   'details_cancel'
##                                                                  )
##                                                       )
##
##            _resource_table['details_save'] = fr(RES_BUTTON,
##                                                 packargs={'side':'LEFT',
##                                                           'padx':0,
##                                                           'pady':0,
##                                                           'anchor':'NW'},
##                                                 actions=('update_status_label',)
##                                                )
##            _resource_table['details_save_string'] = fr(RES_STRING, value='Save')
##
##            _resource_table['details_cancel'] = fr(RES_BUTTON,
##                                                   packargs={'side':'LEFT',
##                                                             'padx':0,
##                                                             'pady':0,
##                                                             'anchor':'NE'},
##                                                   actions=('update_status_label',)
##                                                  )
##            _resource_table['details_cancel_string'] = fr(RES_STRING, value='Cancel')
##
##            _resource_table['details_bash_tags'] = fr(RES_LABEL,
##                                                      resourceargs={'anchor':'W'},
##                                                      packargs={'side':'TOP',
##                                                                'fill':'X',
##                                                                'padx':0,
##                                                                'pady':0,
##                                                                'anchor':'NW'
##                                                               }
##                                                     )
##            _resource_table['details_bash_tags_string'] = fr(RES_STRING, value='Bash Tags:')
##            _resource_table['details_bash_tags_entry'] = fr(RES_TEXT_ENTRY,
##                                                            resourceargs={'height':1,
##                                                                          'wrap':'WORD',
##                                                                          'width':24},
##                                                            packargs={'side':'TOP',
##                                                                      'fill':'BOTH',
##                                                                      'padx':0,
##                                                                      'pady':0,
##                                                                      'expand':True
##                                                                     },
##                                                            customargs={'yscrolling':True}
##                                                           )

        def init_saves_tab_window():
            _resource_table['saves_tab_window'] = fc(RES_FRAME)
        def init_pm_tab_window():
            _resource_table['pm_tab_window'] = fc(RES_FRAME)
        def init_screenshots_tab_window():
            _resource_table['screenshots_tab_window'] = fc(RES_FRAME)
        def init_people_tab_window():
            _resource_table['people_tab_window'] = fc(RES_FRAME)
        def init_ini_tab_window():
            _resource_table['ini_tab_window'] = fc(RES_FRAME)

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
        _resource_table['menu_separator'] = fm(RES_MENU_SEPARATOR)
        def init_top_window_menubar():
            _resource_table['top_window_menubar'] = fm(RES_MENU,
                                                       resources=('file_menu',
                                                                  #'view_menu',
                                                                  #'settings_menu',
                                                                  #'help_menu',
                                                                  #'menu_separator','restart_all_menu','restart_gui_menu','restart_bashim_menu',
                                                                  'quit_menu')
                                                       )

            _resource_table['debug_action'] = fa(DISPLAY_RESOURCE, text='debug_DISPLAY_RESOURCE!')
            _resource_table['shutdown_action'] = fa(SEND_MESSAGE, target=parent_process_id, message=(SHUTDOWN, (USER_REQUEST,), None))
            _resource_table['restart_all_action'] = fa(SEND_MESSAGE, target=parent_process_id, message=(RESTART, ('ALL',), None))
            _resource_table['restart_gui_action'] = fa(SEND_MESSAGE, target=parent_process_id, message=(RESTART, (basher_process_id,), None))
            _resource_table['restart_bashim_action'] = fa(SEND_MESSAGE, target=parent_process_id, message=(RESTART, (bashim_process_id,), None))


            _resource_table['file_menu'] = fm(RES_MENU_CASCADE,
                                              resources=(#'open_menu',
                                                         #'save_menu',
                                                         #'menu_separator',
                                                         'quit_menu',))
            _resource_table['file_menu_string'] = fr(RES_STRING, value='File')
            _resource_table['open_menu'] = fm(RES_MENU_COMMAND, actions=('debug_action',))
            _resource_table['open_menu_string'] = fr(RES_STRING, value='Open')
            _resource_table['save_menu'] = fm(RES_MENU_COMMAND, actions=('debug_action',))
            _resource_table['save_menu_string'] = fr(RES_STRING, value='Save')
            _resource_table['quit_menu'] = fm(RES_MENU_COMMAND, actions=('shutdown_action',))
            _resource_table['quit_menu_string'] = fr(RES_STRING, value='Quit!')

            _resource_table['view_menu'] = fm(RES_MENU_CASCADE,
                                              resources=('apps_menu','tabs_menu'))
            _resource_table['view_menu_string'] = fr(RES_STRING, value='Save')
            _resource_table['apps_menu'] = fm(RES_MENU_COMMAND, actions=('debug_action',))
            _resource_table['apps_menu_string'] = fr(RES_STRING, value='Apps')
            _resource_table['tabs_menu'] = fm(RES_MENU_COMMAND, actions=('debug_action',))
            _resource_table['tabs_menu_string'] = fr(RES_STRING, value='Tabs')

            _resource_table['settings_menu'] = fm(RES_MENU_CASCADE,
                                                  resources=('global_menu','tab_specific_menu'))
            _resource_table['settings_menu_string'] = fr(RES_STRING, value='Settings')
            _resource_table['global_menu'] = fm(RES_MENU_COMMAND, actions=('debug_action',))
            _resource_table['global_menu_string'] = fr(RES_STRING, value='Global')
            _resource_table['tab_specific_menu'] = fm(RES_MENU_COMMAND, actions=('debug_action',))
            _resource_table['tab_specific_menu_string'] = fr(RES_STRING, value='Tab Specific')

            _resource_table['help_menu'] = fm(RES_MENU_CASCADE,
                                              resources=('docs_menu','about_menu'))
            _resource_table['help_menu_string'] = fr(RES_STRING, value='Help')
            _resource_table['docs_menu'] = fm(RES_MENU_COMMAND, actions=('debug_action',))
            _resource_table['docs_menu_string'] = fr(RES_STRING, value='Bash Docs')
            _resource_table['about_menu'] = fm(RES_MENU_COMMAND, actions=('debug_action',))
            _resource_table['about_menu_string'] = fr(RES_STRING, value='About')

            _resource_table['restart_all_menu'] = fm(RES_MENU_COMMAND, actions=('restart_all_action',))
            _resource_table['restart_all_menu_string'] = fr(RES_STRING, value='Restart Everything!')
            _resource_table['restart_gui_menu'] = fm(RES_MENU_COMMAND, actions=('restart_gui_action',))
            _resource_table['restart_gui_menu_string'] = fr(RES_STRING, value='Restart GUI!')
            _resource_table['restart_bashim_menu'] = fm(RES_MENU_COMMAND, actions=('restart_bashim_action',))
            _resource_table['restart_bashim_menu_string'] = fr(RES_STRING, value='Restart Bashim!')

        def init_text_context_menu():
            _resource_table['text_context_menu'] = fm(RES_MENU,
                                                      resources=('text_context_undo','menu_separator','text_context_cut',
                                                                 'text_context_copy','text_context_paste','text_context_delete',
                                                                 'menu_separator','text_context_select_all')
                                                     )
            _resource_table['text_context_undo'] = fm(RES_MENU_COMMAND, actions=('restart_all_action',))
            _resource_table['text_context_undo_string'] = fr(RES_STRING, value='Undo')
            _resource_table['text_context_cut'] = fm(RES_MENU_COMMAND, actions=('restart_all_action',))
            _resource_table['text_context_cut_string'] = fr(RES_STRING, value='Cut')
            _resource_table['text_context_copy'] = fm(RES_MENU_COMMAND, actions=('restart_all_action',))
            _resource_table['text_context_copy_string'] = fr(RES_STRING, value='Copy')
            _resource_table['text_context_paste'] = fm(RES_MENU_COMMAND, actions=('restart_all_action',))
            _resource_table['text_context_paste_string'] = fr(RES_STRING, value='Paste')
            _resource_table['text_context_delete'] = fm(RES_MENU_COMMAND, actions=('restart_all_action',))
            _resource_table['text_context_delete_string'] = fr(RES_STRING, value='Delete')
            _resource_table['text_context_select_all'] = fm(RES_MENU_COMMAND, actions=('restart_all_action',))
            _resource_table['text_context_select_all_string'] = fr(RES_STRING, value='Select All')

        init_top_window_menubar()
        init_text_context_menu()

    def init_statusbar(self):
        _resource_table = self._resource_table
        _app_table = self._app_table
        _settings = self.current_profile._settings

        _resource_table['update_status_label'] = fa(REQUEST_VOLATILE_UPDATE, target='status_label_vstring')
        _resource_table['update_mods_label'] = fa(REQUEST_VOLATILE_UPDATE, target='mods_label_vstring')

        _resource_table['top_window_statusbar'] = fc(RES_FRAME,
                                                     packargs={'side':'BOTTOM',
                                                               'fill':'X'},
                                                     resources=('app_buttons',
                                                                'app_status_separator',
                                                                'status_label',
                                                                'status_mods_separator',
                                                                'mods_label',
                                                                )
                                                    )

        def init_app_buttons():
            app_resources = []
            for grouped_app_uid, grouped_apps in self.current_profile.applications:
                default_app = grouped_apps.pop(0)
                program_path, name, icon, args, wd = default_app
                launch_action_id = 'app_%s' % (grouped_app_uid,)
                launch_id = '%s_button' % (launch_action_id,)
                launch_tooltip_id = '%s_tooltip' % (launch_action_id,)
                launch_menu_id = '%s_menu' % (launch_action_id,)
                launch_image_id = '%s_image' % (launch_action_id,)
                launch_autoquit_setting_id = '%s_Apps.AutoQuit' % (grouped_app_uid,)
                conditional_shutdown_id = '%s_autoquit' % (launch_action_id,)
                _resource_table[conditional_shutdown_id] = fa(CONDITIONAL_ACTION,
                                                              variable=launch_autoquit_setting_id,
                                                              true_result='shutdown_action',
                                                              false_result=None)

                _resource_table[launch_image_id] = fr(RES_IMAGE, icon)
                _resource_table[launch_id] = fr(RES_BUTTON,
                                                resourceargs={'image':((launch_image_id,),),
                                                              'style':'FlatImageButton'},
                                                customargs={'tooltip':launch_tooltip_id},
                                                packargs={'side':'LEFT', 'padx':0, 'pady':0},
                                                actions=(launch_action_id,conditional_shutdown_id),
                                                right_click=launch_menu_id,
                                                )
                _resource_table[launch_tooltip_id] = fr(RES_VOLATILE_STRING, value='Launch %s' % (name,),)
                _resource_table[launch_action_id] = fa(SEND_MESSAGE, target=bashim_process_id, message=(LAUNCH_PROGRAM, default_app, None))

                launch_autoquit_menu = '%s_autoquit_menu' % (launch_action_id,)
                launch_autoquit_toggle_id = '%s_autoquit_toggle' % (launch_action_id,)
                launch_autoquit_menu_string_id = '%s_string' % (launch_autoquit_menu,)
                launch_autoquit_menu_vbool_id = '%s_vbool' % (launch_autoquit_menu,)
                is_active = self.get_setting(launch_autoquit_setting_id, False)
                _resource_table[launch_autoquit_menu] = fm(RES_MENU_CHECKBUTTON,
                                                           resourceargs={'variable':launch_autoquit_menu_vbool_id},
                                                           actions=((launch_autoquit_toggle_id,))
                                                          )
                _resource_table[launch_autoquit_toggle_id] = fa(SEND_MESSAGE,
                                                                target=bashim_process_id,
                                                                message=(TOGGLE_SETTING, (launch_autoquit_setting_id,), None))
                _resource_table[launch_autoquit_menu_string_id] = fr(RES_STRING, value='Auto-Quit')
                _resource_table[launch_autoquit_menu_vbool_id] = fr(RES_VOLATILE_BOOL, value=is_active)

                launch_menu_resources = [launch_autoquit_menu,'menu_separator']
                grouped_apps.append(default_app)
                use_separator = len(grouped_apps) > 1
                for app_index, grouped_app in enumerate(grouped_apps):
                    if use_separator and grouped_app == default_app:
                        launch_menu_resources.append('menu_separator')
                    menuchoice_program_path, menuchoice_name, menuchoice_icon, menuchoice_args, menuchoice_wd = grouped_app
                    menuchoice_id = '%s_%s_menu' % (grouped_app_uid, app_index,)
                    menuchoice_string_id = '%s_string' % (menuchoice_id,)
                    menuchoice_action_id = '%s_launch' % (menuchoice_id,)
                    _resource_table[menuchoice_id] = fm(RES_MENU_COMMAND, actions=(menuchoice_action_id,conditional_shutdown_id))
                    _resource_table[menuchoice_action_id] = fa(SEND_MESSAGE, target=bashim_process_id, message=(LAUNCH_PROGRAM, grouped_app, None))
                    _resource_table[menuchoice_string_id] = fr(RES_STRING, value='Launch %s' % (menuchoice_name,))
                    launch_menu_resources.append(menuchoice_id)

                _resource_table[launch_menu_id] = fm(RES_MENU,
                                                     customargs={'post_up':1},
                                                     resources=launch_menu_resources)
                app_resources.append(launch_id)
            return app_resources

        app_buttons = init_app_buttons()

        _resource_table['app_buttons'] = fc(RES_FRAME,
                                               packargs={'side':'LEFT',
                                                         'fill':'X'},
                                               resources=app_buttons
                                              )

        _resource_table['app_status_separator'] = fr(RES_FRAME_SEPARATOR,
                                                      resourceargs={'orient':'VERTICAL'},
                                                       packargs={'side':'LEFT', 'fill':'Y'}
                                                     )
        _resource_table['status_mods_separator'] = _resource_table['app_status_separator']

        _resource_table['mods_label'] = fr(RES_LABEL,
                                           resourceargs={'anchor':'CENTER', 'width':20},
                                           packargs={'side':'LEFT', 'fill':'X', 'padx':0, 'pady':0}
                                          )
        _resource_table['mods_label_vstring'] = fr(RES_VOLATILE_STRING, value='')

        _resource_table['status_label'] = fr(RES_LABEL,
                                             resourceargs={'anchor':'SW'},
                                             packargs={'side':'LEFT', 'fill':'X', 'expand':True}
                                            )

        _resource_table['status_label_vstring'] = fr(RES_VOLATILE_STRING, value='')

    def get_resource(self, resource_name, resource):
        resource = self._resource_table.get(resource_name, resource)
        return self.game_manager.get_resource(resource_name, resource)

    def set_resource(self, resource_name, resource_value):
##        resource = self._resource_table.get(resource_name, resource)
##        if resource_name in self._resource_table:
##            self._resource_table[resource_name] = resource_value
        return self.game_manager.set_resource(resource_name, resource_value)
