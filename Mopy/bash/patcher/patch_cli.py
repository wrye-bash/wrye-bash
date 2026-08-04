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
#  Wrye Bash copyright (C) 2005-2009 Wrye, 2010-2026 Wrye Bash Team
#  https://github.com/wrye-bash
#
# =============================================================================
"""Command line support for building a Bashed Patch."""
from __future__ import annotations

from .. import bass, bolt, wrye_text
from ..exception import BoltError
from ..wbtemp import TempDir, TempFile

def _get_target_patch(mod_infos, patch_name):
    if patch_name in mod_infos:
        return mod_infos[patch_name]
    created = mod_infos.create_new_mod(patch_name, selected=(),
        wanted_masters=[], author_str='BASHED PATCH')
    if created is None:
        raise BoltError(_('Failed to create %(patch_name)s.') % {
            'patch_name': patch_name})
    return created

def _save_patch_file(patch_file):
    patch_file.fileInfo.makeBackup()
    with TempFile(bolt_path=True) as temp_plugin:
        patch_file.save(temp_plugin)
        if patch_file.fileInfo.ftime is not None:
            temp_plugin.mtime = patch_file.fileInfo.ftime
        patch_file.fileInfo.abs_path.replace_with_temp(temp_plugin)
    patch_file.fileInfo.extras.clear()

def _write_readme(log_value, patch_name, mod_infos):
    data_docs_dir = mod_infos.store_dir.join('Docs')
    data_docs_dir.makedirs()
    readme = data_docs_dir.join(patch_name.fn_body + '.txt')
    readme_html = readme.root + '.html'
    docs_dir = bass.dirs[u'mopy'].join(u'Docs')
    with TempDir(temp_prefix='Docs', bolt_path=True) as temp_readme_dir:
        temp_readme = temp_readme_dir.join(patch_name.fn_body + '.txt')
        with temp_readme.open_bom('w') as readme_file:
            readme_file.write(log_value)
        wrye_text.genHtml(temp_readme, None, docs_dir)
        temp_readme.moveTo(readme)
        (temp_readme.root + '.html').moveTo(readme_html)
    return readme_html

def build_bashed_patch_cli(patch_name, mod_infos):
    """Build a Bashed Patch and persist the resulting state."""
    from .patch_builder import build_bashed_patch, finalize_patch_log, \
        load_patcher_configs, prepare_patch_files, refresh_patch_files
    from .patch_files import PatchFile
    patch_info = _get_target_patch(mod_infos, patch_name)
    bashed_patch = PatchFile(patch_info, mod_infos)
    patch_configs = patch_info.get_table_prop('bash.patch.configs', {})
    config_patchers = load_patcher_configs(bashed_patch, patch_configs)
    progress = bolt.HeadlessProgress(patch_name)
    patch_log, build_start = build_bashed_patch(
        bashed_patch, config_patchers, progress)
    patch_files = prepare_patch_files(bashed_patch)
    unneeded_parts = bashed_patch.find_unneded_parts(patch_files)
    if unneeded_parts:
        bolt.deprint('Obsolete Bashed Patch parts were left in place: '
                     f'{", ".join(map(str, unneeded_parts))}')
    progress(0.9, _('Saving...'))
    for patch_file in patch_files:
        _save_patch_file(patch_file)
    log_value = finalize_patch_log(patch_log, build_start)
    readme_html = _write_readme(log_value, patch_name, mod_infos)
    refresh_patch_files(bashed_patch, patch_files, readme_html)
    mod_infos.save_pickle()
    bass.settings.save()
