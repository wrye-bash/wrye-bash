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
#  Wrye Bash copyright (C) 2005-2009 Wrye, 2010-2024 Wrye Bash Team
#  https://github.com/wrye-bash
#
# =============================================================================
from __future__ import annotations

import io
from collections import Counter, defaultdict

from .. import bass, bolt, bush, load_order, initialization
from ..bolt import SubProgress, dict_sort, sig_to_str, structs_cache
from ..brec import ModReader, RecordHeader, RecordType, ShortFidWriteContext, \
    SubrecordBlob, unpack_header
from ..exception import CancelError
from ..plugin_types import MergeabilityCheck
from ..mod_files import ModHeaderReader
from ..wbtemp import TempFile

# Deprecated/Obsolete Bash Tags -----------------------------------------------
# Tags that have been removed from Wrye Bash and should be dropped from pickle
# files
_removed_tags = {'Merge', 'ScriptContents'}
# Indefinite backwards-compatibility aliases for deprecated tags
_tag_aliases = {
    'Actors.Perks.Add': {'NPC.Perks.Add'},
    'Actors.Perks.Change': {'NPC.Perks.Change'},
    'Actors.Perks.Remove': {'NPC.Perks.Remove'},
    'Body-F': {'R.Body-F'},
    'Body-M': {'R.Body-M'},
    'Body-Size-F': {'R.Body-Size-F'},
    'Body-Size-M': {'R.Body-Size-M'},
    'C.GridFlags': {'C.ForceHideLand'},
    'Derel': {'Relations.Remove'},
    'Eyes': {'R.Eyes'},
    'Eyes-D': {'R.Eyes'},
    'Eyes-E': {'R.Eyes'},
    'Eyes-R': {'R.Eyes'},
    'Factions': {'Actors.Factions'},
    'Hair': {'R.Hair'},
    'Invent': {'Invent.Add', 'Invent.Remove'},
    'InventOnly': {'IIM', 'Invent.Add', 'Invent.Remove'},
    'Npc.EyesOnly': {'NPC.Eyes'},
    'Npc.HairOnly': {'NPC.Hair'},
    'NpcFaces': {'NPC.Eyes', 'NPC.Hair', 'NPC.FaceGen'},
    'R.Relations': {'R.Relations.Add', 'R.Relations.Change',
                    'R.Relations.Remove'},
    'Relations': {'Relations.Add', 'Relations.Change'},
    'Voice-F': {'R.Voice-F'},
    'Voice-M': {'R.Voice-M'},
}

def process_tags(tag_set: set[str], drop_unknown=True) -> set[str]:
    """Removes obsolete tags from and resolves any tag aliases in the
    specified set of tags. See the comments above for more information. If
    drop_unknown is True, also removes any unknown tags (tags that are not
    currently used, obsolete or aliases)."""
    if not tag_set: return tag_set # fast path - nothing to process
    ret_tags = tag_set.copy()
    ret_tags -= _removed_tags
    for old_tag, replacement_tags in _tag_aliases.items():
        if old_tag in tag_set:
            ret_tags.discard(old_tag)
            ret_tags.update(replacement_tags)
    if drop_unknown:
        ret_tags &= bush.game.allTags
    return ret_tags

# Some wrappers to decouple other files from process_tags
def read_dir_tags(plugin_name, ci_cached_bt_contents=None):
    """Wrapper around get_tags_from_dir. See that method for docs."""
    added_tags, deleted_tags = get_tags_from_dir(plugin_name,
        ci_cached_bt_contents=ci_cached_bt_contents)
    return process_tags(added_tags), process_tags(deleted_tags)

def read_loot_tags(plugin_name):
    """Wrapper around get_tags_from_loot. See that method for docs."""
    added_tags, deleted_tags = initialization.lootDb.get_tags_from_loot(
        plugin_name)
    return process_tags(added_tags), process_tags(deleted_tags)

# BashTags dir ----------------------------------------------------------------
def get_tags_from_dir(plugin_name, ci_cached_bt_contents=None):
    """Retrieves a tuple containing a set of added and a set of deleted
    tags from the 'Data/BashTags/PLUGIN_NAME.txt' file, if it is
    present.

    :param plugin_name: The name of the plugin to check the tag file for.
    :param ci_cached_bt_contents: An optional set containing lower-case
        versions of the names of all files currently present in the BashTags
        directory. If specified, get_tags_from_dir avoids having to stat to
        figure out if the file in question exists.
    :return: A tuple containing two sets of added and deleted tags."""
    tag_file = None
    # Check if the file even exists first, using the cache if possible
    bt_file_name = f'{plugin_name.fn_body}.txt'
    if ci_cached_bt_contents is not None:
        if bt_file_name.lower() not in ci_cached_bt_contents:
            return set(), set()
    else:
        tag_file = bass.dirs['tag_files'].join(bt_file_name)
        if not tag_file.is_file():
            return set(), set()
    if tag_file is None: # If we hit the cache, we need to set tag_file here
        tag_file = bass.dirs['tag_files'].join(bt_file_name)
    removed, added = set(), set()
    add_removed = removed.add
    add_added = added.add
    # BashTags files must be in UTF-8 (or ASCII, obviously)
    with tag_file.open(u'r', encoding=u'utf-8') as ins:
        for tag_line in ins:
            # Strip out comments and skip lines that are empty as a result
            tag_line = tag_line.split(u'#')[0].strip()
            if not tag_line: continue
            for tag_entry in tag_line.split(u','):
                # Guard against things (e.g. typos) like 'TagA,,TagB'
                if not tag_entry: continue
                tag_entry = tag_entry.strip()
                # If it starts with a minus, it's removing a tag
                if tag_entry[0] == u'-':
                    # Guard against a typo like '- C.Water'
                    add_removed(tag_entry[1:].strip())
                else:
                    add_added(tag_entry)
    return added, removed

def save_tags_to_dir(plugin_name, plugin_tag_diff):
    """Compares plugin_tags to plugin_old_tags and saves the diff to
    Data/BashTags/PLUGIN_NAME.txt.

    :param plugin_name: The name of the plugin to modify the tag file for.
    :param plugin_tag_diff: A tuple of two sets, as returned by diff_tags,
        representing a diff of all bash tags currently applied to the
        plugin in question vs. all bash tags applied to the plugin
        by its description and the LOOT masterlist / userlist.."""
    tag_files_dir = bass.dirs['tag_files']
    tag_files_dir.makedirs()
    tag_file = tag_files_dir.join(f'{plugin_name.fn_body}.txt')
    # Calculate the diff and ignore the minus when sorting the result
    tag_diff_add, tag_diff_del = plugin_tag_diff
    processed_diff = sorted(tag_diff_add | {f'-{t}' for t in tag_diff_del},
                            key=lambda t: t[1:] if t[0] == '-' else t)
    # While all our tags are ASCII, the comment at the top can be localized, so
    # use UTF-8
    with tag_file.open('w', encoding='utf-8') as out:
        # Stick a header in there to indicate that it's machine-generated
        # Also print the version, which could be helpful
        out.write(f"# {_('Generated by Wrye Bash %(wb_version)s')}\n" % {
            'wb_version': bass.AppVersion})
        out.write(', '.join(processed_diff) + '\n')

def diff_tags(plugin_new_tags, plugin_old_tags):
    """Returns two sets, the first containing all added tags and the second all
    removed tags."""
    return plugin_new_tags - plugin_old_tags, plugin_old_tags - plugin_new_tags

#--Plugin Checker -------------------------------------------------------------
_cleaning_wiki_url = (u'[[!https://tes5edit.github.io/docs/7-mod-cleaning-and'
                      u'-error-checking.html|Tome of xEdit]]')

def checkMods(progress, modInfos, showModList=False, showCRC=False,
              showVersion=True, scan_plugins=True):
    """Checks currently loaded mods for certain errors / warnings."""
    if not bush.game.Esp.canBash:
        # If we can't load plugins, then trying to do so will obviously fail
        scan_plugins = False
    # Setup some commonly used collections of plugin info
    full_acti = load_order.cached_active_tuple()
    full_lo = load_order.cached_lo_tuple()
    plugin_to_acti_index = {p: i for i, p in enumerate(full_acti)}
    all_present_plugins = set(full_lo)
    all_present_minfs = {x: modInfos[x] for x in full_lo} #ascending load order
    all_active_plugins = set(full_acti)
    game_master_name = bush.game.master_file
    vanilla_masters = bush.game.bethDataFiles
    log = bolt.LogFile(io.StringIO())
    # -------------------------------------------------------------------------
    # The header we'll be showing at the start of the log. Separate so that we
    # can check if the log is empty
    log_header = u'= ' + _(u'Check Plugins') + u'\n'
    log_header += _(u'This is a report of any problems Wrye Bash was able to '
                    u'identify in your currently installed plugins.')
    # -------------------------------------------------------------------------
    # Check for corrupt plugins
    all_corrupted = modInfos.corrupted
    # -------------------------------------------------------------------------
    # Don't show NoMerge-tagged plugins as mergeable and remove ones that have
    # already been merged into a BP
    mergeable = MergeabilityCheck.MERGE.cached_types(modInfos)[0]
    can_merge = {m for m, inf in modInfos.items() if inf in mergeable and
        m not in modInfos.merged and 'NoMerge' not in inf.getBashTags()}
    # -------------------------------------------------------------------------
    # Check for ESL-flagged plugins that aren't ESL-capable and Overlay-flagged
    # plugins that shouldn't be Overlay-flagged. Also check for conflicts
    # between ESL and Overlay flags.
    pflags = bush.game.scale_flags
    flag_errors = {k: {h_msg: set() for h_msg in v} for k, v in
                   pflags.error_msgs.items()}
    for m, modinf in modInfos.items():
        for pflag in pflags:
            if pflag in pflags.error_msgs and pflag.cached_type(modinf):
                pflag.validate_type(modinf, flag_errors[pflag].values())
    # -------------------------------------------------------------------------
    # Check for Deactivate-tagged plugins that are active and
    # MustBeActiveIfImported-tagged plugins that are imported, but inactive.
    should_deactivate = []
    should_activate = []
    for plugin_fn, p_minf in all_present_minfs.items():
        p_active = plugin_fn in all_active_plugins
        p_imported = plugin_fn in modInfos.imported
        p_tags = p_minf.getBashTags()
        if u'Deactivate' in p_tags and p_active:
            should_deactivate.append(plugin_fn)
        if u'MustBeActiveIfImported' in p_tags and not p_active and p_imported:
            should_activate.append(plugin_fn)
    # -------------------------------------------------------------------------
    # Check for missing or delinquent masters
    seen_plugins = set()
    cannot_scan_overrides = set()
    p_missing_masters = set()
    p_delinquent_masters = set()
    p_circular_masters = set()
    for p_fn_key, p in all_present_minfs.items():
        if p.has_circular_masters():
            # The plugin depends on itself (possibly transitively) -> report
            p_circular_masters.add(p_fn_key)
        if p_fn_key in all_active_plugins:
            for p_master in p.masterNames:
                if p_master not in all_present_plugins:
                    # The plugin is active and a master is missing -> report
                    p_missing_masters.add(p_fn_key)
                else:
                    if p_master not in seen_plugins:
                        # The plugin is active and one of its masters hasn't
                        # been checked, so that master is delinquent -> report
                        p_delinquent_masters.add(p_fn_key)
                    if p_master not in all_active_plugins:
                        # Inactive master -> needed for scanning later
                        cannot_scan_overrides.add(p_fn_key)
        else:
            for p_master in p.masterNames:
                if p_master not in all_active_plugins:
                    # Inactive master -> needed for scanning later
                    cannot_scan_overrides.add(p_fn_key)
        seen_plugins.add(p_fn_key)
    cannot_scan_overrides |= p_missing_masters
    # -------------------------------------------------------------------------
    # Check for plugins with invalid TES4 version.
    valid_vers = bush.game.Esp.validHeaderVersions
    invalid_tes4_versions = {
        p: f'{p_ver}' for p in all_active_plugins
        if (p_ver := modInfos[p].header.version) not in valid_vers}
    # -------------------------------------------------------------------------
    # Check for older form versions, which may point to improperly converted
    # plugins
    old_fvers = modInfos.older_form_versions
    # -------------------------------------------------------------------------
    # Check for cleaning information from LOOT.
    cleaning_messages = {}
    scan_for_cleaning = set()
    dirty_msgs = [(k, m.getDirtyMessage(scan_beth=True)) for k, m in
                  all_present_minfs.items()]
    num_dirty_vanilla = 0
    for x, y in dirty_msgs:
        if y:
            if isinstance(y, str):
                cleaning_messages[x] = y
            else: # Don't report vanilla plugins if the ignore setting is on
                num_dirty_vanilla += 1
        elif scan_plugins:
            scan_for_cleaning.add(x)
    # -------------------------------------------------------------------------
    # Scan plugins to collect data for more detailed analysis.
    scanning_canceled = False
    all_unneeded_deletions = defaultdict(list) # fn_key -> list[(fid, sig)]
    all_deleted_refs = defaultdict(list) # fn_key -> list[fid]
    all_deleted_navms = defaultdict(list) # fn_key -> list[fid]
    all_deleted_others = defaultdict(list) # fn_key -> list[fid]
    old_weapon_records = defaultdict(list) # fn_key -> list[fid]
    null_formid_records = defaultdict(list) # fn_key -> list[(eid, sig)]
    plgn_header_sig = bush.game.Esp.plugin_header_sig
    # fid -> (is_injected, orig_plugin, list[(eid, sig, plugin)])
    record_type_collisions = {}
    # fid -> (orig_plugin, list[(eid, sig, plugin)])
    probable_injected_collisions = {}
    duplicate_formids = defaultdict(dict) # fid -> plugin -> int
    all_hitmes = defaultdict(list) # fn_key -> list[fid]
    if scan_plugins:
        try:
            # Extract data for all plugins (we'll need the context from all of
            # them, even the game master)
            load_progress = SubProgress(progress, 0, 0.7)
            load_progress.setFull(len(all_present_minfs))
            all_extracted_data = {}
            for i, (k, present_minf) in enumerate(all_present_minfs.items()):
                mod_progress = SubProgress(load_progress, i, i + 1)
                ext_data = ModHeaderReader.extract_mod_data(present_minf,
                                                            mod_progress)
                all_extracted_data[k] = ext_data
            # Run over all plugin data once for efficiency, collecting
            # information such as deleted records and overrides
            scan_progress = SubProgress(progress, 0.7, 0.9)
            scan_progress.setFull(len(all_extracted_data))
            all_ref_types = RecordType.sig_to_class[b'CELL'].ref_types
            # Temporary place to collect (eid, sig, plugin)-lists
            all_record_versions: dict[int, list] = defaultdict(list)
            # Whether or not the game uses SSE's form version (44)
            game_has_v44 = RecordHeader.plugin_form_version == 44
            for i, (plugin_fn, ext_data) in enumerate(
                    all_extracted_data.items()):
                scan_progress(i, _('Scanning: %(scanning_plugin)s') % {
                    'scanning_plugin': plugin_fn})
                # Two situations where we can skip checking deleted records:
                # 1. The game master can't have deleted records (deleting a
                #    record from the master file that introduced it just
                #    removes the record from existence entirely).
                # 2. If we have a LOOT report for a plugin, we can skip every
                #    deleted reference and deleted navmesh and just use the
                #    LOOT report.
                scan_deleted = (plugin_fn != game_master_name and
                                plugin_fn in scan_for_cleaning)
                # We have to skip checking overrides if the plugin is inactive
                # or has inactive (or missing) masters because a whole-LO
                # FormID is not a valid concept for inactive (or missing)
                # plugins. Plus, collisions from inactive plugins are either
                # harmless (if the plugin really is inactive) or will show up
                # in the BP (if the plugin is actually merged into the BP).
                scan_overrides = (plugin_fn in all_active_plugins and
                                  plugin_fn not in cannot_scan_overrides)
                # Skip checking for old WEAP records if the game is not based
                # on SSE or the plugin is one of the vanilla masters (none of
                # the vanilla masters have old weapon records, plus they
                # couldn't be fixed even if they did)
                scan_old_weapons = (game_has_v44 and
                                    plugin_fn not in vanilla_masters)
                add_unneeded_del = all_unneeded_deletions[plugin_fn].append
                add_deleted_ref = all_deleted_refs[plugin_fn].append
                add_deleted_navm = all_deleted_navms[plugin_fn].append
                add_deleted_rec = all_deleted_others[plugin_fn].append
                add_old_weapon = old_weapon_records[plugin_fn].append
                add_hitme = all_hitmes[plugin_fn].append
                add_null_fid = null_formid_records[plugin_fn].append
                p_masters = (*modInfos[plugin_fn].masterNames, plugin_fn)
                p_num_masters = len(p_masters)
                for r, d in ext_data.items():
                    for r_header, r_eid in d:
                        r_fid = r_header.fid
                        w_rec_type = r_header.recType
                        if (r_fid.object_dex == 0 and
                                w_rec_type != plgn_header_sig):
                            add_null_fid((w_rec_type, r_eid))
                        r_mod_index = r_fid.mod_dex
                        if scan_deleted:
                            # Check the deleted flag - unpacking flags is too
                            # expensive
                            if r_header.flags1 & 0x00000020:
                                if r_mod_index == p_num_masters - 1:
                                    add_unneeded_del((r_fid, w_rec_type))
                                elif w_rec_type == b'NAVM':
                                    add_deleted_navm(r_fid)
                                elif w_rec_type in all_ref_types:
                                    add_deleted_ref(r_fid)
                                else:
                                    add_deleted_rec(r_fid)
                        # p_masters includes self, so >=
                        is_hitme = r_mod_index >= p_num_masters
                        if is_hitme:
                            add_hitme(r_fid)
                        if scan_overrides:
                            # Convert into a load order FormID - ugly but fast,
                            # inlined and hand-optimized from various methods.
                            # Calling them would be way too slow.
                            lo_fid = (r_fid.object_dex | plugin_to_acti_index[
                                p_masters[p_num_masters - 1 if is_hitme else
                                r_mod_index]] << 24)
                            all_record_versions[lo_fid].append(
                                (r_eid, r_header.recType, plugin_fn))
                        if (scan_old_weapons and w_rec_type == b'WEAP' and
                                r_header.form_version < 44):
                            add_old_weapon(r_fid)
            # Check for record type collisions, i.e. overrides where the record
            # type of at least one override does not match the base record's
            # type and probable injected collisions, i.e. injected records
            # where the EDID of at least one version does not match the EDIDs
            # of the other versions
            collision_progress = SubProgress(progress, 0.9, 1)
            # We can't get an accurate progress bar here, because the loop
            # below is far too hot. Instead, at least make sure the progress
            # bar updates on each collision by bumping the state.
            collision_progress.setFull(len(all_record_versions))
            prog_msg = f'{_("Looking for collisions…")}\n'
            num_collisions = 0
            collision_progress(num_collisions, prog_msg + game_master_name)
            for r_fid, r_versions in all_record_versions.items():
                first_eid, first_sig, first_plugin = r_versions[0]
                duplicates_counter = Counter()
                # These FormIDs are whole-LO and HITMEs are truncated, so this
                # is safe
                orig_plugin = full_acti[r_fid >> 24]
                # Record versions are sorted by load order, so if the first
                # version's originating plugin does not match the plugin that
                # the whole-LO FormID points to, this record must be injected
                is_injected = orig_plugin != first_plugin
                definite_collision = False
                probable_collision = False
                duplicates_counter[first_plugin] = 1
                for r_eid, r_sig, r_plugin in r_versions[1:]:
                    # Keep track of duplicate FormIDs in all record versions
                    duplicates_counter[r_plugin] += 1
                    if first_sig != r_sig:
                        # At least one override has a different record type,
                        # this is for sure a collision.
                        definite_collision = True
                    if is_injected and first_eid != r_eid:
                        # This is an injected record and at least one override
                        # has a different EDID, this is probably a collision.
                        probable_collision = True
                # Keep only duplicate FormIDs when we actually have >1
                trimmed_counter = {p: c for p, c in duplicates_counter.items()
                                   if c > 1}
                if trimmed_counter:
                    duplicate_formids[r_fid] = trimmed_counter
                if definite_collision:
                    num_collisions += 1
                    record_type_collisions[r_fid] = (is_injected, orig_plugin,
                                                     r_versions)
                    collision_progress(num_collisions, prog_msg + first_plugin)
                elif probable_collision:
                    num_collisions += 1
                    probable_injected_collisions[r_fid] = (orig_plugin,
                                                           r_versions)
                    collision_progress(num_collisions, prog_msg + first_plugin)
        except CancelError:
            scanning_canceled = True
    # -------------------------------------------------------------------------
    # Check for unnecessary deletions, i.e. new records that have the Deleted
    # flag set and should probably just be removed entirely instead
    unnecessary_dels = {}
    if all_unneeded_deletions:
        for plugin_fn, ud_data in all_unneeded_deletions.items():
            # .esu files created by xEdit use deleted records on purpose to
            # mark records that exist in one plugin but not in the other
            plugin_is_esu = plugin_fn.fn_ext == '.esu'
            if ud_data and not plugin_is_esu:
                unnecessary_dels[plugin_fn] = ud_data
    # -------------------------------------------------------------------------
    # Check for deleted references
    if all_deleted_refs:
        for plugin_fn, deleted_refrs in all_deleted_refs.items():
            # Rely on LOOT for detecting deleted references in vanilla files
            plugin_is_vanilla = plugin_fn in vanilla_masters
            # .esu files created by xEdit use deleted records on purpose to
            # mark records that exist in one plugin but not in the other
            plugin_is_esu = plugin_fn.fn_ext == '.esu'
            if deleted_refrs and not plugin_is_vanilla and not plugin_is_esu:
                num_deleted = len(deleted_refrs)
                if num_deleted == 1: # I hate natural languages :/
                    del_msg = _('1 deleted reference')
                else:
                    del_msg = _('%(num_del_refs)d deleted references') % {
                        'num_del_refs': num_deleted}
                cleaning_messages[plugin_fn] = del_msg
    # -------------------------------------------------------------------------
    # Check for deleted navmeshes
    deleted_navmeshes = {}
    if all_deleted_navms:
        for plugin_fn, deleted_navms in all_deleted_navms.items():
            # Deleted navmeshes can't and shouldn't be fixed in vanilla files,
            # so don't show warnings for them
            plugin_is_vanilla = plugin_fn in vanilla_masters
            # .esu files created by xEdit use deleted records on purpose to
            # mark records that exist in one plugin but not in the other
            plugin_is_esu = plugin_fn.fn_ext == '.esu'
            if deleted_navms and not plugin_is_vanilla and not plugin_is_esu:
                num_deleted = len(deleted_navms)
                if num_deleted == 1:
                    del_msg = _('1 deleted navmesh')
                else:
                    del_msg = _('%(num_del_navms)d deleted navmeshes') % {
                        'num_del_navms': num_deleted}
                deleted_navmeshes[plugin_fn] = del_msg
    # -------------------------------------------------------------------------
    # Check for deleted base records
    deleted_base_recs = {}
    if all_deleted_others:
        for plugin_fn, deleted_others in all_deleted_others.items():
            # Deleted navmeshes can't and shouldn't be fixed in vanilla files,
            # so don't show warnings for them
            plugin_is_vanilla = plugin_fn in vanilla_masters
            # .esu files created by xEdit use deleted records on purpose to
            # mark records that exist in one plugin but not in the other
            plugin_is_esu = plugin_fn.fn_ext == '.esu'
            if deleted_others and not plugin_is_vanilla and not plugin_is_esu:
                num_deleted = len(deleted_others)
                if num_deleted == 1:
                    del_msg = _('1 deleted base record')
                else:
                    del_msg = _('%(num_del_bases)d deleted base records') % {
                        'num_del_bases': num_deleted}
                deleted_base_recs[plugin_fn] = del_msg
    # -------------------------------------------------------------------------
    # Check for old (form version < 44) WEAP records, which the game can't load
    # properly and which cannot be converted safely by the CK
    old_weaps = {}
    if old_weapon_records:
        for plugin_fn, weap_recs in old_weapon_records.items():
            if weap_recs:
                num_weaps = len(weap_recs)
                if num_weaps == 1:
                    weap_msg = _('1 old weapon record')
                else:
                    weap_msg = _('%(num_old_weaps)d old weapon records') % {
                        'num_old_weaps': num_weaps}
                old_weaps[plugin_fn] = weap_msg
    # -------------------------------------------------------------------------
    # Check for NULL FormIDs, i.e. records beside the main file header that
    # have a FormID of 0x00000000
    null_fids = {}
    if null_formid_records:
        for plugin_fn, null_data in null_formid_records.items():
            if null_data:
                null_fids[plugin_fn] = null_data
    # -------------------------------------------------------------------------
    # Check for HITMEs, i.e. records with a mod index that is > the number of
    # masters that the containing plugin has
    hitmes = {}
    if all_hitmes:
        for plugin_fn, found_hitmes in all_hitmes.items():
            # HITMEs can't and shouldn't be fixed in vanilla files, so don't
            # show warnings for them
            plugin_is_vanilla = plugin_fn in vanilla_masters
            if found_hitmes and not plugin_is_vanilla:
                num_hitmes = len(found_hitmes)
                # No point in making these translatable, HITME is a fixed term
                if num_hitmes == 1:
                    hitme_msg = _('1 HITME')
                else:
                    hitme_msg = _('%(num_hitmes)d HITMEs') % {
                        'num_hitmes': num_hitmes}
                hitmes[plugin_fn] = hitme_msg
    # -------------------------------------------------------------------------
    # Some helpers for building the log
    p_header_str = sig_to_str(plgn_header_sig)
    def _log_plugins(head_, msg_, plugin_list_):
        """Logs a simple list of plugins."""
        log.setHeader(head_)
        log(msg_)
        for p in sorted(plugin_list_):
            log(f'* __{p}__')
    def log_plugin_messages(plugin_dict):
        """Logs a list of plugins with a message after each plugin."""
        for p, p_msg in dict_sort(plugin_dict):
            log(f'* __{p}:__  {p_msg}')
    def log_whole_lo_fid_note():
        """Log a note telling users that FormIDs in this section are relative
        to the whole LO, not individual plugins."""
        first_msg = _(
            'Note: the FormIDs in this section are relative to the whole load '
            'order, not any individual plugin.')
        second_msg = _(
            "To view the records with these FormIDs in %(xedit_name)s, make "
            "sure to load your entire load order (simply accept the 'Module "
            "Selection' prompt in %(xedit_name)s with OK).") % {
            'xedit_name': bush.game.Xe.full_name,
        }
        log(f'~~{first_msg}~~ {second_msg}')
    def log_rel_fid_note():
        """Log a note telling users that FormIDs in this section are relative
        to individual plugins, not the whole LO."""
        first_msg = _(
            'Note: the FormIDs in this section are relative to each '
            'individual listed plugin, not the whole load order.')
        second_msg = _(
            "To view the records with these FormIDs in %(xedit_name)s, "
            "double-click the plugin in the 'Module Selection' prompt in "
            "%(xedit_name)s.") % {'xedit_name': bush.game.Xe.full_name}
        log(f'~~{first_msg}~~ {second_msg}')
    def format_record(raw_sig: bytes, fmt_fid: str, raw_eid=''):
        """Format a record identifier, with a given signature, formatted FormID
        and (optionally) Editor ID."""
        ret_fmt = f'[{sig_to_str(raw_sig)}:{fmt_fid}]'
        if raw_eid:
            ret_fmt = f'{raw_eid} {ret_fmt}'
        return ret_fmt
    format_fid = pflags.format_fid
    def log_collision(coll_fid, coll_inj, coll_plugin, coll_versions):
        """Logs a single collision with the specified FormID, injected status,
        origin plugin and collision info."""
        # FormIDs must be in long format at this point
        proper_fid = format_fid(coll_fid, coll_plugin)
        if coll_inj:
            log('* ' + _('%(injected_formid)s injected into '
                         '%(injection_target)s, colliding versions:') % {
                'injected_formid': proper_fid,
                'injection_target': coll_plugin})
        else:
            log('* ' + _('%(overriden_formid)s from %(source_plugin)s, '
                         'colliding versions:') % {
                'overriden_formid': proper_fid, 'source_plugin': coll_plugin})
        for ver_eid, ver_sig, ver_orig_plugin in coll_versions:
            fmt_record = format_record(ver_sig, proper_fid, ver_eid)
            # Mark the base record if the record wasn't injected
            if not coll_inj and ver_orig_plugin == coll_plugin:
                msg = _('%(colliding_formid)s from %(colliding_plugin)s '
                        '(base record)')
            else:
                msg = _('%(colliding_formid)s from %(colliding_plugin)s')
            log('  * ' + msg % {'colliding_formid': fmt_record,
                                'colliding_plugin': ver_orig_plugin})
    # -------------------------------------------------------------------------
    # From here on we have data on all plugin problems, so it's purely a matter
    # of building the log
    if scanning_canceled:
        log.setHeader(u'=== ' + _(u'Plugin Loading Canceled'))
        log(_(u'The loading of plugins was canceled and the resulting report '
              u"may not be accurate. You can use the 'Update' button to load "
              u'plugins and generate a new report.'))
    if all_corrupted:
        log.setHeader(u'=== ' + _(u'Corrupted'))
        log(_(u'Wrye Bash could not read the follow plugins. They most likely '
              u'have corrupt or otherwise malformed headers.'))
        log_plugin_messages(all_corrupted) ##: Just _log_plugins?
    for pflag in pflags:
        if pflag.merge_check is not None:
            minfos_cache, head, msg = pflag.merge_check.cached_types(modInfos)
            if minfos_cache:
                _log_plugins(head, msg, minfos_cache)
        for (head, msg), pl_set in flag_errors.get(pflag, {}).items():
            if pl_set:
                _log_plugins(head, msg, pl_set)
    if can_merge:
        _log_plugins('=== ' + _('Mergeable'), _(
            'The following plugins could be merged into a Bashed Patch, but '
            'are currently not merged.'), can_merge)
    if should_deactivate:
        _log_plugins('=== ' + _(u'Deactivate-tagged But Active'), _(
            "The following plugins are tagged with 'Deactivate' and should "
            'be deactivated and imported into the Bashed Patch.'),
                    should_deactivate)
    if should_activate:
        _log_plugins('=== '+_(u'MustBeActiveIfImported-tagged But Inactive'),
            _("The following plugins are tagged with 'MustBeActiveIfImported' "
              "and should be activated if they are also imported into the "
              'Bashed Patch. They are currently imported, but not active.'),
                    should_activate)
    if p_missing_masters:
        _log_plugins('=== ' + _('Missing Masters'), _(
            'The following plugins have missing masters and are active. This '
            'will cause a CTD at the main menu and must be corrected by '
            'installing the missing plugins or removing the plugins with '
            'missing masters.'), p_missing_masters)
    if p_delinquent_masters:
        _log_plugins('=== ' + _('Delinquent Masters'), _(
            'The following plugins have delinquent masters, i.e. masters '
            'that are set to load after their dependent plugins. The game '
            'will try to force them to load before the dependent plugins, '
            'which can lead to unpredictable or undefined behavior and must '
            'be corrected. You should correct the load order.'),
                    p_delinquent_masters)
    if p_circular_masters:
        _log_plugins('=== ' + _('Circular Masters'), _(
            "The following plugins have circular masters, i.e. they depend "
            "on themselves. This can happen either directly (%(example_a)s "
            "has %(example_a)s as a master) or transitively (%(example_a)s "
            "has %(example_b)s as a master, which, in turn, has %("
            "example_a)s as a master - such a chain may be even longer). "
            "Resolving this is impossible for the game, which will most "
            "likely crash when trying to load these plugins. You can try to "
            "investigate by using the 'Change To…' command to reassign the "
            "circular master so that the plugin can be opened in "
            "%(xedit_name)s.") % {'example_a': 'foo.esp',
                                  'example_b': 'bar.esp',
                                  'xedit_name': bush.game.Xe.full_name},
                    p_circular_masters)
    if invalid_tes4_versions:
        ver_list = ', '.join(
            sorted(str(v) for v in bush.game.Esp.validHeaderVersions))
        log.setHeader('=== ' + _('Invalid %(file_header_label)s versions') % {
            'file_header_label': p_header_str})
        log(_("The following plugins have a %(file_header_label)s version "
              "that isn't recognized as one of the versions created by the "
              "%(ck_name)s (%(accepted_header_versions)s). This is undefined "
              "behavior and most likely indicates the plugin was created for "
              "a different game.") % {'file_header_label': p_header_str,
                                      'ck_name': bush.game.Ck.long_name,
                                      'accepted_header_versions': ver_list})
        log_plugin_messages(invalid_tes4_versions)
    if old_fvers:
        _log_plugins('=== ' + _('Old Header Form Versions'), _(
            'The following have a form version on their headers that is '
            'older than the minimum version created by the %(ck_name)s. This '
            'probably means that the plugin was not properly converted to '
            'work with %(game_name)s.') % {'ck_name': bush.game.Ck.long_name,
                        'game_name': bush.game.display_name, }, old_fvers)
    if cleaning_messages:
        log.setHeader('=== ' + _('Cleaning With %(xedit_name)s Needed') % {
            'xedit_name': bush.game.Xe.full_name})
        log(_('The following plugins have deleted references or other issues '
              'that can and should be fixed with %(xedit_name)s. Visit the '
              '%(tome_of_xedit)s for more information.') % {
            'tome_of_xedit': _cleaning_wiki_url,
            'xedit_name': bush.game.Xe.full_name})
        log_plugin_messages(cleaning_messages)
        if num_dirty_vanilla:
            log('\n' + _("Additionally, %(num_ignored_vanilla)d vanilla "
                         "plugins were reported dirty by LOOT. They were "
                         "ignored because you have enabled 'Ignore Dirty "
                         "Vanilla Files'.") % {
                'num_ignored_vanilla': num_dirty_vanilla})
    if deleted_navmeshes:
        log.setHeader(u'=== ' + _(u'Deleted Navmeshes'))
        log(_('The following plugins have deleted navmeshes. They will cause '
              'a CTD if another plugin references the deleted navmesh or a '
              'nearby navmesh. They can only be fixed manually, which should '
              'usually be done by the mod author. Failing that, the safest '
              'course of action is to uninstall the plugins.'))
        log_plugin_messages(deleted_navmeshes)
    if deleted_base_recs:
        log.setHeader(u'=== ' + _(u'Deleted Base Records'))
        log(_('The following plugins have deleted base records. If another '
              'plugin references the deleted record, the resulting behavior '
              'is undefined. It may CTD, fail to delete the record or do any '
              'number of other things. They can only be fixed manually, '
              'which should usually be done by the mod author. Failing that, '
              'the safest course of action is to uninstall the plugins.'))
        log_plugin_messages(deleted_base_recs)
    if unnecessary_dels:
        log.setHeader('=== ' + _('Unnecessary Deleted Records'))
        log(_('The following plugins have unnecessary deleted records. These '
              'are new records introduced by the plugin that also have the '
              'Deleted flag set. This is most likely a mistake by the mod '
              'author. If the record was not intended to be used (e.g. if it '
              'is a leftover from an abandoned idea), this can be corrected '
              'by simply removing the entire record in %(xedit_name)s. In any '
              'case, the mod author should be notified so they can figure out '
              'what they meant to do here and correct it properly.') % {
            'xedit_name': bush.game.Xe.full_name,
        })
        log_rel_fid_note()
        for p, ud_data in dict_sort(unnecessary_dels):
            log(f'* __{p}__')
            for ud_fid, ud_sig in ud_data:
                log(f'  * {format_record(ud_sig, str(ud_fid))}')
    if old_weaps:
        log.setHeader(u'=== ' + _(u'Old Weapon Records'))
        log(_('The following plugins have old weapon (WEAP) records. These '
              'cannot be loaded by %(game_name)s and the %(ck_name)s cannot '
              'automatically fix them by resaving. They have to be manually '
              'fixed in the %(ck_name)s by changing the critical data (CRDT) '
              'subrecord to restore the correct data, which should usually be '
              'done by the mod author. Failing that, the safest course of '
              'action is to uninstall the plugins.') % {
            'game_name': bush.game.display_name,
            u'ck_name': bush.game.Ck.long_name,
        })
        log_plugin_messages(old_weaps)
    if null_fids:
        log.setHeader('=== ' + _('NULL FormIDs'))
        log(_('The following plugins have records with NULL (00000000) '
              'FormIDs besides the main file header (%(main_file_sig)s). This '
              'is undefined behavior, as the NULL FormID is a special '
              'reserved value, and may result in the records not working '
              'correctly or causing CTDs. This is most likely a sign that the '
              'mod author broke something via scripted edits. They can only '
              'be fixed manually, by assigning them a new FormID (or removing '
              'them if the records are unnecessary), which should usually be '
              'done by the mod author. Failing that, the safest course of '
              'action is to uninstall the plugins.') % {
            'main_file_sig': p_header_str,
        })
        log_rel_fid_note()
        for p, null_data in dict_sort(null_fids):
            log(f'* __{p}__')
            for nd_sig, nd_eid in null_data:
                log(f'  * {format_record(nd_sig, "00000000", nd_eid)}')
    if hitmes:
        # Let people translate 'HITMEs' because acronym plurals may be
        # different in some languages
        log.setHeader('=== ' + _('HITMEs'))
        log(_('The following plugins have HITMEs (%(hitme_acronym)s), which '
              'most commonly occur when the %(ck_name)s or an advanced mode '
              'of %(xedit_name)s were used to improperly remove a master. '
              'The behavior of these plugins is undefined and may lead to '
              'them not working correctly or causing CTDs. Such a plugin is '
              'usually beyond saving and mod authors should revert to a '
              'backup from before the plugin was corrupted. The safest course '
              'of action for a user is to uninstall it.') % {
            'hitme_acronym': '__H__igher __I__ndex __T__han __M__asterlist '
                             '__E__ntries',
            'ck_name': bush.game.Ck.long_name,
            'xedit_name': bush.game.Xe.full_name,
        })
        log_plugin_messages(hitmes)
    if duplicate_formids:
        log.setHeader('=== ' + _('Duplicate FormIDs'))
        log(_('The following FormIDs occur twice (or more) in the listed '
              'plugins. This is undefined behavior and may result in CTDs or '
              'unpredictable issues at runtime. Such problems can only be '
              'fixed manually, which should usually be done by the mod '
              'author. Failing that, the safest course of action is to '
              'uninstall the plugins.'))
        log_whole_lo_fid_note()
        for orig_fid, duplicates_counter in duplicate_formids.items():
            for orig_plugin, dupe_count in duplicates_counter.items():
                log('* ' + _('%(full_fid)s in %(orig_plugin)s: '
                             'occurs %(num_duplicates)d times') % {
                    'full_fid': format_fid(orig_fid, orig_plugin),
                    'orig_plugin': orig_plugin,
                    'num_duplicates': dupe_count,
                })
    if record_type_collisions:
        log.setHeader(u'=== ' + _(u'Record Type Collisions'))
        log(_('The following records override each other, but have different '
              'record types. This is undefined behavior, but will almost '
              'certainly lead to CTDs. Such conflicts can only be fixed '
              'manually, which should usually be done by the mod author. '
              'Failing that, the safest course of action is to uninstall the '
              'plugins.'))
        log_whole_lo_fid_note()
        for orig_fid, (is_inj, orig_plugin, coll_info) in dict_sort(
                record_type_collisions):
            log_collision(orig_fid, is_inj, orig_plugin, coll_info)
    if probable_injected_collisions:
        log.setHeader(u'=== ' + _(u'Probable Injected Collisions'))
        log(_('The following injected records override each other, but have '
              'different Editor IDs (EDIDs). This probably means that two '
              'different injected records have collided, but have the same '
              'record signature. The resulting behavior depends on what the '
              'injecting plugins are trying to do with the record, but they '
              'will most likely not work as intended. Such conflicts can '
              'only be fixed manually, which should usually be done by the '
              'mod author. Failing that, the safest course of action is to '
              'uninstall the plugins.'))
        log_whole_lo_fid_note()
        for orig_fid, (orig_plugin, coll_info) in dict_sort(
                probable_injected_collisions):
            log_collision(orig_fid, True, orig_plugin, coll_info)
    # If we haven't logged anything (remember, the header is a separate
    # variable) then let the user know they have no problems.
    temp_log = log.out.getvalue()
    if not temp_log:
        log.setHeader(u'=== ' + _(u'No Problems Found'))
        # Don't annoy the user with this message if we can't load plugins
        if not scan_plugins and bush.game.Esp.canBash:
            log(_(u'Wrye Bash did not find any problems with your installed '
                  u'plugins without loading them. Turning on loading of '
                  u'plugins may find more problems.'))
        else:
            log(_(u'Wrye Bash did not find any problems with your installed '
                  u'plugins. Congratulations!'))
    # We already logged missing or delinquent masters up above, so don't
    # duplicate that info in the mod list
    if showModList:
        log(u'\n' + modInfos.getModList(showCRC, showVersion, wtxt=True,
                                        log_problems=False).strip())
    return log_header + u'\n\n' + log.out.getvalue()

#------------------------------------------------------------------------------
class NvidiaFogFixer(object):
    """Fixes cells to avoid nvidia fog problem."""
    def __init__(self,modInfo):
        self.modInfo = modInfo
        self.fixedCells = set()

    def fix_fog(self, progress, __unpacker=structs_cache[u'=12s2f2l2f'].unpack,
                __packer=structs_cache[u'12s2f2l2f'].pack):
        """Duplicates file, then walks through and edits file as necessary."""
        progress.setFull(self.modInfo.fsize)
        fixedCells = self.fixedCells
        fixedCells.clear()
        #--File stream
        #--Scan/Edit
        with TempFile() as out_path:
            with ModReader.from_info(self.modInfo) as ins:
                with ShortFidWriteContext(out_path) as out:
                    while not ins.atEnd():
                        progress(ins.tell())
                        header = unpack_header(ins)
                        _rsig = header.recType
                        # Copy the GRUP/record header
                        out.write(header.pack_head())
                        # Treat CELL block subgroups record by record - analyze
                        # CELLs but just copy cell-children records over. If
                        # _rsig == GRUP no need to do anything (copied above)
                        if ((header.is_top_group_header and
                             header.label != b'CELL') or
                                _rsig != b'GRUP' and _rsig != b'CELL'):
                            buff = ins.read(header.blob_size)
                            out.write(buff)
                        #--Handle cells
                        elif _rsig == b'CELL':
                            next_header = ins.tell() + header.blob_size
                            while ins.tell() < next_header:
                                subrec = SubrecordBlob(ins, _rsig)
                                if subrec.mel_sig == b'XCLL':
                                    color, near, far, rotXY, rotZ, fade, \
                                        clip = __unpacker(subrec.mel_data)
                                    if not (near or far or clip):
                                        near = 0.0001
                                        subrec.mel_data = __packer(color, near,
                                            far, rotXY, rotZ, fade, clip)
                                        fixedCells.add(header.fid)
                                subrec.packSub(out, subrec.mel_data)
            if fixedCells:
                self.modInfo.makeBackup()
                self.modInfo.abs_path.replace_with_temp(out_path)
                self.modInfo.setmtime(crc_changed=True) # fog fixes
