import os
from bash.common import norm_path, norm_join, load_ini_settings
from collections import OrderedDict
from bash.messages import *
fp = format_program

class UserProfile:
    """Collection of attributes unique to each profile."""
    def __init__(self, profile_dir):
        self.applications = []
        self._settings = {}
        self.profile_dir = profile_dir
        self.profile_uid = r'Profiles_%s' % (os.path.basename(profile_dir.rstrip(os.sep)),)
        self.apps_dir = None
        self.is_active = False
        self.bash_vars = {}

    def set_active(self):
        if self.is_active: return
        self.is_active = True
        self.init_settings()
        self.init_apps()

    def set_inactive(self):
        if not self.is_active: return
        self.is_active = False
        self.applications = []
        self._settings = {}

    def init_settings(self):
        """Load settings from the profile path. Create an empty profile if none exist."""
        profile_path = norm_join(self.profile_dir, 'profile.ini')
        _settings = self._settings = load_ini_settings(profile_path)
        if 'Profile.AppsDirectory' not in _settings:
            _settings['Profile.AppsDirectory'] = 'Apps'
        self.apps_dir = norm_join(self.profile_dir, _settings['Profile.AppsDirectory'])
        self.game_type = _settings['Game.Type']
        self.game_directory = norm_path(_settings['Game.Directory'])
        self.game_plugin_list = norm_path(_settings['Game.PluginList'])
        self.bash_vars['%GameDirectory%'] = self.game_directory

    def init_apps(self):
        """Load valid apps."""
        applications = self.applications
        apps_dir = self.apps_dir

        game_app_paths = ['Game', 'Editor'] #Make the game and associated editor be listed first

        try:
            #Enable use of .lnk files if win32com is present
            import win32com.client
            shell = win32com.client.Dispatch("WScript.Shell")
        except:
            shell = None
        ungrouped_app_paths = []
        app_paths = game_app_paths + os.listdir(apps_dir)
        loaded_groups = set()
        for app_rel_path in app_paths:
            app_path = norm_join(apps_dir, app_rel_path)
            if os.path.isfile(app_path) and app_path.endswith('.lnk'):
                #Ungrouped shortcut. User convenience, auto-place in new dirs after rest are processed.
                ungrouped_app_paths.append(app_path)
            elif app_path not in loaded_groups and os.path.isdir(app_path):
                grouped_app_uid = r'%s_%s' % (self.profile_uid, os.path.basename(app_rel_path.rstrip(os.sep)),)
                loaded_groups.add(app_path)
                apps_ini_path = norm_join(app_path, 'apps.ini')
                apps_settings = {}
                grouped_app = OrderedDict()
                default_sections = []
                auto_quit = False
                if os.path.exists(apps_ini_path):
                    apps_settings = load_ini_settings(apps_ini_path, self.bash_vars)
                    app_sections = []
                    for key in apps_settings.keys():
                        section, sep, item = key.partition('.')
                        if section in {'Common', 'Apps'}:
                            continue
                        if section not in app_sections:
                            app_sections.append(section)

                    default_sections = apps_settings.get('Apps.Default', [])
                    auto_quit = apps_settings.get('Apps.AutoQuit', False)
                    for app_section in app_sections:
                        grouped_app_path = apps_settings.get('%s.Path' % (app_section,))
                        if grouped_app_path is None:
                            continue
                        grouped_app_path = os.path.expandvars(grouped_app_path)
                        if not os.path.exists(grouped_app_path):
                            continue
                        grouped_app_wd, grouped_app_name = os.path.split(grouped_app_path)
                        grouped_app_name = apps_settings.get('%s.Name' % (app_section,), grouped_app_name)
                        grouped_app_args = apps_settings.get('%s.Args' % (app_section,), None)
                        grouped_app_wd = apps_settings.get('%s.WorkingDirectoryOverride' % (app_section,), grouped_app_wd)
                        grouped_app_wd = os.path.expandvars(grouped_app_wd)
                        grouped_app_wd = os.path.dirname(grouped_app_wd)
                        grouped_app_icon = apps_settings.get('%s.IconOverride' % (app_section,), grouped_app_path)
                        grouped_app_icon = os.path.expandvars(grouped_app_icon)
                        grouped_app[app_section] = fp(grouped_app_path,
                                                      name=grouped_app_name,
                                                      args=grouped_app_args,
                                                      wd=grouped_app_wd,
                                                      icon=grouped_app_icon)

                auto_quit_id = '%s_Apps.AutoQuit' % (grouped_app_uid,)
                self._settings[auto_quit_id] = auto_quit
                if shell is not None:
                    for grouped_app_path in sorted(os.listdir(app_path)):
                        grouped_app_path = norm_join(app_path, grouped_app_path)
                        if os.path.isfile(grouped_app_path) and grouped_app_path.endswith('.lnk'):
                            grouped_app_name = os.path.basename(grouped_app_path)[:-4]
                            shortcut = shell.CreateShortCut(grouped_app_path)

                            grouped_app_path = shortcut.TargetPath
                            grouped_app_path = os.path.expandvars(grouped_app_path)
                            if not os.path.exists(grouped_app_path):
                                continue
                            grouped_app_args = shortcut.Arguments
                            grouped_app_wd = shortcut.WorkingDirectory
                            grouped_app_wd = os.path.expandvars(grouped_app_wd)
                            grouped_app_wd = os.path.dirname(grouped_app_wd)
                            grouped_app_icon = shortcut.TargetPath
                            grouped_app_icon = os.path.expandvars(grouped_app_icon)
                            grouped_app[grouped_app_name] = fp(grouped_app_path,
                                                               name=grouped_app_name,
                                                               args=grouped_app_args,
                                                               wd=grouped_app_wd,
                                                               icon=grouped_app_icon)

                for key in default_sections:
                    if key in grouped_app:
                        grouped_app.move_to_end(key, last=False)
                        break

                if len(grouped_app):
                    applications.append((grouped_app_uid,[value for key, value in grouped_app.items()]))

        for ungrouped_app_path in ungrouped_app_paths:
            print('Unimplemented! Need to add %s to a grouped app path' % (ungrouped_app_path,))
        if shell:
            del shell
            del win32com.client
            del win32com
