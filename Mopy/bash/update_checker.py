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
#  Wrye Bash copyright (C) 2005-2009 Wrye, 2010-2023 Wrye Bash Team
#  https://github.com/wrye-bash
#
# =============================================================================
"""Implements a small update checker for Wrye Bash."""
from __future__ import annotations

__author__ = 'Infernio'

import base64
import json
import time
from dataclasses import dataclass, field
from threading import Thread

from . import bass
from .bolt import JsonParsable, LooseVersion, deprint, json_remap
from .exception import LimitReachedError, RequestError

# This won't work if requests isn't installed - in that case, we simply can't
# check for updates
try:
    from .web import ARestHandler
    can_check_updates = True
except ImportError as e:
    deprint(f'requests not installed, update checking functionality will not '
            f'be available (error: {e})')
    can_check_updates = False

# Constants -------------------------------------------------------------------
_GITHUB_API_URL = 'https://api.github.com/'
# The GitHub API version to use - bump this every once in a while after
# checking that nothing has broken
_GITHUB_API_VERSION = '2022-11-28'

# Internal API ----------------------------------------------------------------
def _decode_base64(b64_html: str | bytes) -> str:
    """Helper for decoding base64-encoded text. Used e.g. for storing a copy of
    the changelog inside the latest.json file."""
    return base64.b64decode(b64_html).decode('utf-8')

@dataclass(slots=True)
class _GHFile(JsonParsable):
    """Represents a file hosted on GitHub."""
    _parsers = {f'ghf_{x}': json_remap(x) for x in (
        'type', 'encoding', 'size', 'name', 'path', 'content', 'sha', 'url',
        'git_url', 'html_url', 'download_url')}
    ghf_type: str
    # This is not the file encoding (i.e. UTF-8 or something similar), it is
    # the encoding of the content below (usually base64)
    ghf_encoding: str
    ghf_size: int
    ghf_name: str
    ghf_path: str
    ghf_content: str = field(repr=False) # Massive base64 string
    ghf_sha: str
    ghf_url: str
    ghf_git_url: str
    ghf_html_url: str
    ghf_download_url: str
    # Ignore _links, we already have the URLs up above anyways

class _GitHub(ARestHandler):
    """Minimal GitHub REST API wrapper that implements only the parts of the
    GitHub API we actually need for the update check. Only uses the 'core' part
    of the API, so only rate limit info for that is implemented."""
    _base_url = _GITHUB_API_URL
    # The total number of allowed requests
    core_limit: int | None
    # The number of allowed requests before having to wait for a rate reset
    core_remaining: int | None
    # The UNIX timestamp at which the next rate reset will occur
    core_reset: int | None
    # The number of requests that have already been done in this cycle
    core_used: int | None

    def __init__(self):
        super().__init__(extra_headers={
            'accept': 'application/vnd.github+json',
            'x-github-api-version': _GITHUB_API_VERSION,
        })
        # Rate limiting information - set to None (= unknown) by default
        self.core_limit = None
        self.core_remaining = None
        self.core_reset = None
        self.core_used = None

    # Abstract API ------------------------------------------------------------
    def _handle_error_response(self, response):
        if (response.status_code == 403 and
                response.headers['x-ratelimit-remaining'] == 0):
            self._update_rate_limit_info(response.headers)
            raise LimitReachedError()
        raise RequestError(response.status_code, response.json()['message'])

    def _update_rate_limit_info(self, response_headers):
        self.core_limit = int(response_headers['x-ratelimit-limit'])
        self.core_remaining = int(response_headers['x-ratelimit-remaining'])
        self.core_reset = int(response_headers['x-ratelimit-reset'])
        self.core_used = int(response_headers['x-ratelimit-used'])

    # Public API --------------------------------------------------------------
    def get_file_from_path(self, gh_owner: str, gh_repo: str,
            gh_file_path: str) -> _GHFile:
        """Retrieves information about a file, including its base64-encoded
        contents, from a specified path in a repo. Note that only files are
        supported - trying to use this on a submodule, directory, symlink, etc.
        will probably break badly.

        :param gh_owner: The user or organization that owns the repo.
        :param gh_repo: The name of the repository in question.
        :param gh_file_path: The full path to the file in question."""
        return _GHFile.parse_single(self._send_get(
            f'repos/{gh_owner}/{gh_repo}/contents/{gh_file_path}'))

# Public API ------------------------------------------------------------------
@dataclass(slots=True)
class DownloadInfo(JsonParsable):
    """Represents a single download link for Wrye Bash."""
    _parsers = {
        'download_name': json_remap('name'),
        'download_url': json_remap('url'),
    }
    download_name: str
    download_url: str

@dataclass(slots=True)
class LatestVersion(JsonParsable):
    """Represents the latest stable Wrye Bash version that is currently
    available."""
    _parsers = {
        'wb_version': lambda d, a: LooseVersion(d['version']),
        'wb_changes': lambda d, a: _decode_base64(d['changes']),
        'wb_downloads': lambda d, a: DownloadInfo.parse_many(d['downloads']),
    }
    wb_version: LooseVersion
    wb_changes: str
    wb_downloads: list[DownloadInfo]

    def __repr__(self):
        return (f'LatestVersion<{self.wb_version}, {len(self.wb_downloads)} '
                f'download links>')

class UpdateChecker:
    """The main class through which update checking functionality can be
    accessed."""
    def __init__(self):
        self._gh_api = _GitHub()

    # Internal API ------------------------------------------------------------
    def _get_latest_version(self) -> LatestVersion | None:
        """Retrieves information about the latest release from GitHub."""
        try:
            ver_file_data = self._gh_api.get_file_from_path(gh_owner='wrye-bash',
                gh_repo='wb_status', gh_file_path='latest.json')
        except LimitReachedError:
            deprint('Reached GitHub rate limit, setting next update check '
                    'post-rate-reset')
            # Set the last check timestamp to the next time we get a reset,
            # that way we won't pointlessly ping GitHub only to get the same
            # rate limit errors over and over
            next_reset = self._gh_api.core_reset + 1
            bass.settings['bash.update_check.last_checked'] = next_reset
            return None
        except RequestError:
            deprint('Failed to contact GitHub for update check')
            # Try again in 5 minutes, maybe it'll be fixed by then
            next_try = int(time.time()) + (5 * 60)
            bass.settings['bash.update_check.last_checked'] = next_try
            return None
        lv_json_str = _decode_base64(ver_file_data.ghf_content)
        return LatestVersion.parse_single(json.loads(lv_json_str))

    @staticmethod
    def _should_check_for_updates():
        """Returns True if enough time has elapsed since the last update check
        that we should check again."""
        if not bass.settings['bash.update_check.enabled']:
            return False # User has disabled update checking
        lc_cooldown = bass.settings['bash.update_check.cooldown']
        lc_timestamp = bass.settings['bash.update_check.last_checked']
        # The next UNIX timestamp at which we should check
        next_check = lc_timestamp + (lc_cooldown * 60 * 60)
        return time.time() > next_check

    # Public API --------------------------------------------------------------
    def check_for_updates(self, force_check=False) -> LatestVersion | None:
        """Checks for updates if necessary. Returns a LatestVersion object
        representing a newer version than what the user has installed, or None
        if update checking is disabled, we're on cooldown, a connection problem
        occurred or no new version is available.

        :param force_check: If set to True, check for updates even if the user
            has disabled update checking or we're on cooldown. With this set,
            the only way the method will return None is a connection problem or
            no new version being available."""
        if not can_check_updates:
            return None # no requests, no update checking
        if force_check or self._should_check_for_updates():
            lv = self._get_latest_version()
            # lv is None if we ran into a GitHub error. In that case, the last
            # checked timestamp will have already been changed
            if lv:
                # We've done the check, remember the timestamp so we don't use
                # up the user's entire GitHub API budget (unless they set the
                # cooldown to 0 of course, in which case they *want* to use up
                # their budget)
                next_check = int(time.time())
                bass.settings['bash.update_check.last_checked'] = next_check
                if lv.wb_version > LooseVersion(bass.AppVersion):
                    return lv
        return None

class UCThread(Thread):
    """A threaded version of UpdateChecker. Pass it a custom event sender
    created by _AComponent._make_custom_event, which will be used to send the
    result back to the main thread."""
    def __init__(self, send_version: callable):
        super().__init__(daemon=True)
        self._send_version = send_version

    def run(self) -> None:
        if not can_check_updates:
            return # no requests, no update checking
        newer_version = UpdateChecker().check_for_updates()
        # Don't spam this at the user immediately, give it a bit
        time.sleep(0.5)
        # Have to pass via kwargs since this came from _make_custom_event
        self._send_version(newer_version=newer_version)
