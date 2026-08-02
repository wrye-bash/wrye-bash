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
"""Backend helpers for building Bashed Patches."""
from __future__ import annotations

import re
import time
from datetime import timedelta

from .config_patchers import all_patcher_types
from .. import bolt, bush
from ..bolt import RefrIn, SubProgress
from ..exception import BoltError

class BPTooManyMastersError(BoltError):
    """Raised when one top group exceeds the game's master limit."""

class BPSplitError(BoltError):
    """Raised when a Bashed Patch cannot be split within the master limit."""

def load_patcher_configs(bashed_patch, patch_configs):
    """Instantiate the available patcher configs and load saved settings."""
    config_patchers = [p_type(bashed_patch) for p_type in all_patcher_types]
    for config_patcher in config_patchers:
        config_patcher.import_config(patch_configs)
    return config_patchers

def save_patcher_configs(config_patchers):
    """Return the persistent Bashed Patch configuration."""
    patch_configs = {u'ImportedMods': set()}
    for config_patcher in config_patchers:
        config_patcher.saveConfig(patch_configs)
    return patch_configs

def build_bashed_patch(bashed_patch, config_patchers, progress):
    """Run configured patchers and return their log and start time."""
    build_start = time.time_ns()
    bashed_patch.fileInfo.set_table_prop(
        'bash.patch.configs', save_patcher_configs(config_patchers))
    patch_log = bolt.LogFile()
    enabled_patchers = [
        p.get_patcher_instance(bashed_patch) for p in config_patchers
        if p.isEnabled]
    bashed_patch.init_patchers_data(
        enabled_patchers, SubProgress(progress, 0, 0.1))
    bashed_patch.initFactories(SubProgress(progress, 0.1, 0.2))
    bashed_patch.scanLoadMods(SubProgress(progress, 0.2, 0.8))
    bashed_patch.buildPatch(patch_log, SubProgress(progress, 0.8, 0.9))
    progress(1.0, _('Compiled.'))
    return patch_log, build_start

def prepare_patch_files(bashed_patch):
    """Set patch attributes, splitting the patch if the master limit requires
    it."""
    master_limit = bush.game.Esp.master_limit
    all_bp_masters = set()
    for top_sig, top_masters in bashed_patch.used_masters_by_top().items():
        if len(top_masters) > master_limit:
            raise BPTooManyMastersError(_(
                'Congratulations on managing to get a single top group to '
                '>%(max_num_masters)d masters (you got '
                '%(curr_num_masters)d in top grup %(top_group_sig)s)! Please '
                'post to the Wrye Bash Discord (including your BashBugDump), '
                'we seriously did not think anyone would manage this. This '
                'error is fatal by the way, Wrye Bash currently does not '
                'support splitting the Bashed Patch within a top group.') % {
                    'max_num_masters': master_limit,
                    'curr_num_masters': len(top_masters),
                    'top_group_sig': bolt.sig_to_str(top_sig),
                })
        all_bp_masters |= top_masters
    if len(all_bp_masters) <= master_limit:
        bashed_patch.set_attributes()
        return [bashed_patch]
    patch_files = bashed_patch.split_patch()
    if patch_files is None:
        raise BPSplitError(_(
            'Failed to split the Bashed Patch. The simple algorithm used for '
            'splitting it right now cannot handle the situation we have '
            'encountered here. Please post to the Wrye Bash Discord '
            '(including your BashBugDump).'))
    for part_index, patch_file in enumerate(patch_files):
        patch_file.set_attributes(was_split=True, split_part=part_index)
    return patch_files

def finalize_patch_log(patch_log, build_start):
    """Finalize the patch log and insert the elapsed build time."""
    patch_log.setHeader(None)
    patch_log(u'{{CSS:wtxt_sand_small.css}}')
    log_value = patch_log.out.getvalue()
    elapsed_seconds = round(
        (time.time_ns() - build_start) / 1_000_000_000, 3)
    elapsed = str(timedelta(seconds=elapsed_seconds)).rstrip('0')
    return re.sub(u'TIMEPLACEHOLDER', elapsed, log_value, 1)

def refresh_patch_files(bashed_patch, patch_files, readme_html):
    """Refresh saved patch infos and return their names and refresh data."""
    patch_name = bashed_patch.fileInfo.fn_key
    patch_names = (p_file.fileInfo.fn_key for p_file in patch_files)
    patch_attrs = {'doc': readme_html, 'crc': None, 'mergeInfo': None,
                   'bp_split_parent': None}
    attrs = {next(patch_names): patch_attrs}
    split_attrs = {**patch_attrs, 'bp_split_parent': str(patch_name)}
    attrs.update((part_name, split_attrs) for part_name in patch_names)
    minfos = bashed_patch.p_file_minfos
    refresh_in = RefrIn.from_tabled_infos(minfos, attrs, ghosts=True)
    return list(attrs), minfos.refresh(
        refresh_in, force_update=True)
