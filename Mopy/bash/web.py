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
#
# Everything in this file is based on Ganda's pynxm
# (https://github.com/GandaG/pynxm). See also Mopy/LICENSE-THIRD-PARTY.
# Modifications have been made to fit Wrye Bash's code style, refactor it to
# take advantage of Python 3 features, create a higher-level API and make
# third-party dependencies optional.
#
# Original copyright notice and disclaimer:
# =============================================================================
# Copyright 2019 Daniel Nunes
#
# Licensed under the Apache License, Version 2.0 (the 'License');
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an 'AS IS' BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
# =============================================================================
"""Implements APIs for accessing Internet-based APIs (e.g. REST APIs)."""
from __future__ import annotations

__author__ = 'Ganda, Infernio'

import platform
from enum import Enum

from . import bass
from .exception import RequestError

# First see if we even have the dependencies necessary to use the web APIs
try:
    import requests
except ImportError as i_err:
    raise ImportError('requests missing, web API unavailable') from i_err

# Constants -------------------------------------------------------------------
_USER_AGENT = (f'WryeBash/{bass.AppVersion} ({platform.platform()}; '
               f'{platform.architecture()[0]}) '
               f'{platform.python_implementation()}/'
               f'{platform.python_version()}')

# Internal API ----------------------------------------------------------------
_OptStrDict = dict[str, str] | None

class _RestOp(Enum):
    """HTTP request methods."""
    DELETE = 'DELETE'
    GET = 'GET'
    POST = 'POST'

# Public API ------------------------------------------------------------------
class ARestHandler:
    """An abstract base class for APIs that need to use ."""
    # The base URL for the REST API you're using. Set in
    _base_url: str

    def __init__(self, extra_headers: dict[str, str] = None):
        """Initializes a new ARestHandler instance.

        :param extra_headers: A optional dict of extra HTTP headers to use for
            all requests in this session."""
        self._session = requests.Session()
        self._session.headers.update({
            'user-agent': _USER_AGENT,
        } | (extra_headers or {}))

    # Internal API ------------------------------------------------------------
    # Double underscore to differentiate it from the protected API below, which
    # is supposed to be used only by child classes - whereas this isn't even
    # intended to be used by those
    def __make_request(self, req_op: _RestOp, req_endpoint: str,
            req_payload: _OptStrDict = None, req_data: _OptStrDict = None,
            req_headers: _OptStrDict = None):
        """Performs an actual web request via the current session.

        :param req_op: The HTTP request method to use. See _Op.
        :param req_endpoint: The API endpoint to use. See your REST API's docs.
        :param req_payload: The parameters to send in the request's query
            string.
        :param req_data: The data to send in the body of the request.
        :param req_headers: The HTTP headers to send with the request."""
        if req_payload is None: req_payload = {}
        if req_data is None: req_data = {}
        if req_headers is None: req_headers = {}
        response = self._session.request(req_op.value,
            self._base_url + req_endpoint, params=req_payload, data=req_data,
            headers=req_headers, timeout=10)
        if response.status_code < 200 or response.status_code > 299:
            self._handle_error_response(response)
        self._update_rate_limit_info(response.headers)
        return response.json()

    # Abstract API ------------------------------------------------------------
    def _handle_error_response(self, response):
        """Handle a response with a status code that is not in the 200-299
        range. By default, raises a RequestError with an 'unknown error'
        message."""
        raise RequestError(response.status_code, 'Unknown error')

    def _update_rate_limit_info(self, response_headers):
        """Update the cached rate limit information from this new response.
        Does nothing by default, override to get a chance to retrieve
        appropriate rate limiting info for your specific REST API."""

    # Protected API -----------------------------------------------------------
    def _send_delete(self, req_endpoint: str, req_payload: _OptStrDict = None,
            req_data: _OptStrDict = None, req_headers: _OptStrDict = None):
        """Performs a DELETE request via the current session.

        :param req_endpoint: The API endpoint to use. See your REST API's docs.
        :param req_payload: The parameters to send in the request's query
            string.
        :param req_data: The data to send in the body of the request.
        :param req_headers: The HTTP headers to send with the request."""
        return self.__make_request(_RestOp.DELETE, req_endpoint, req_payload,
            req_data, req_headers)

    def _send_get(self, req_endpoint: str, req_payload: _OptStrDict = None,
            req_data: _OptStrDict = None, req_headers: _OptStrDict = None):
        """Performs a GET request via the current session.

        :param req_endpoint: The API endpoint to use. See your REST API's docs.
        :param req_payload: The parameters to send in the request's query
            string.
        :param req_data: The data to send in the body of the request.
        :param req_headers: The HTTP headers to send with the request."""
        return self.__make_request(_RestOp.GET, req_endpoint, req_payload,
            req_data, req_headers)

    def _send_post(self, req_endpoint: str, req_payload: _OptStrDict = None,
            req_data: _OptStrDict = None, req_headers: _OptStrDict = None):
        """Performs a POST request via the current session.

        :param req_endpoint: The API endpoint to use. See your REST API's docs.
        :param req_payload: The parameters to send in the request's query
            string.
        :param req_data: The data to send in the body of the request.
        :param req_headers: The HTTP headers to send with the request."""
        return self.__make_request(_RestOp.POST, req_endpoint, req_payload,
            req_data, req_headers)
