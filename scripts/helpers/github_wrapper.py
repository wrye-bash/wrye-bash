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
#  Wrye Bash copyright (C) 2005-2009 Wrye, 2010-2020 Wrye Bash Team
#  https://github.com/wrye-bash
#
# =============================================================================
"""This module wraps github API calls. Features caching."""

from configparser import ConfigParser, NoOptionError, NoSectionError
import os

import github

from .utils import ALL_ISSUES, SCRIPTS_PATH

DEFAULT_ISSUE_STATE = ALL_ISSUES
DEFAULT_MILESTONE = None

def get_repo(org_name, repo_name):
    """Get a githubapi repository object for the specified repository.
        git: github.Github object for the user
        orgName: display name of the orginizations for the repository
                 (not the link name, ie Wrye Bash is the name, but
                  wrye-bash is the link to access it).  If orgName is
                  None, assumes personal repos.
        repoName: name of the repository to get
    """
    access_token = None
    try:
        # Look if we've got a token to use
        parser = ConfigParser()
        parser.read(os.path.join(SCRIPTS_PATH, 'github.ini'))
        token = parser.get('OAuth', 'token')
        if token != 'CHANGEME':
            access_token = token
    except (NoOptionError, NoSectionError, OSError):
        pass # File is invalid or could not be found, proceed without token
    git = github.Github(access_token)
    repo = git.get_repo(org_name + '/' + repo_name)
    try:
        # The github library returns a repo object even if the repo
        # doesn't exist.  Test to see if it's a valid repository by
        # attempting to access one of its attributes.  Then the
        # github library will report the error.
        # noinspection PyStatementEffect
        repo.full_name
        return repo
    except github.UnknownObjectException:
        return None

def get_milestone(repo, ms_title):
    """Returns the github.Milestone object for a specified milestone."""
    for m in repo.get_milestones(state='all'):
        if m.title == ms_title:
            return m
    return None

class _IssueCache(object):
    CACHE = {} # key: an IssueFilter --> value: a list of issues
    ALL_LABELS = {} # key is an IssueFilter (TODO but only Repo matters)
    # and value a list of issue labels for this repo - should be a set probably
    counter = 0

    class IssueFilter(object):
        def __init__(self, repo, milestone=None, state=None):
            self.repo = repo
            self.milestone = milestone
            self._state = state

        @property
        def state(self):
            if not self._state:  # disallow None - API's fault
                return DEFAULT_ISSUE_STATE
            return self._state

        def __key(self):  # http://stackoverflow.com/a/2909119/281545
            return self.repo.full_name, self.milestone.title, self.state

        def __eq__(self, other):  # add `self is other` optimization ?
            return isinstance(other, type(self)) and (
                    self.__key() == other.__key())

        def __ne__(self, other):  # needed ?
            return not self.__eq__(other)

        def __hash__(self):
            return hash(self.__key())

        def __lt__(self, other):
            if self.repo != other.repo: return False
            if self.state != other.state and other.state != \
                    DEFAULT_ISSUE_STATE: return False
            if self.milestone != other.milestone and other.milestone:
                return False
            return True

    @staticmethod
    def hit(repo, milestone, state):
        issue_filter = _IssueCache.IssueFilter(repo, milestone, state)
        current = _IssueCache.CACHE.get(issue_filter)
        if not current:
            # search in the cache for some superset of issues already fetched
            super_ = None
            for key, issues in _IssueCache.CACHE.items():
                if issue_filter < key:
                    super_ = issues
                    break
            if super_:
                if not milestone and not state: current = super_
                elif not milestone:
                    current = [x for x in super_ if x.state == state]
                elif not state:
                    current = [x for x in super_ if x.milestone == milestone]
                else:
                    current = [x for x in super_ if
                               x.state == state and x.milestone == milestone]
                _IssueCache._update(repo, milestone, state, current)
                return current
            # else fetch them...
            _IssueCache.counter += 1
            print('Hitting github %u time(s)' % _IssueCache.counter)
            if milestone:  # FIXME - API won't let me specify None for all
                # milestone=github.GithubObject.NotSet ...
                current = repo.get_issues(milestone, state=issue_filter.state,
                    sort='created', direction='desc')
            else:
                current = repo.get_issues(state=issue_filter.state,
                    sort='created', direction='desc')
            _IssueCache._update(repo, milestone, state, current)
        return current

    @staticmethod
    def _update(repo, milestone, state, issues):  # not thread safe
        issue_filter = _IssueCache.IssueFilter(repo, milestone, state)
        _IssueCache.CACHE[issue_filter] = issues

def get_issues(repo, milestone=None, keep_labels=frozenset(), state=None):
    """Return a _list_ of applicable issues for the given game and milestone
        repo: github.Repository object
        milestone: github.Milestone object
        keep_labels: set of labels an issue must partake to, to be included
          in the results - by default all labels including no labels at all
        state: open or closed - by default 'all'
       return: a list of issues
        :rtype: github.PaginatedList.PaginatedList[github.Issue.Issue]
    TODO: add sort, direction as needed, list comprehensions
    """
    current = _IssueCache.hit(repo, milestone, state)
    if not keep_labels: # no label filters, return All
        return current
    # return only issues that partake in keep_labels
    result = []
    for issue in current:
        labels = {x.name for x in issue.labels}
        if keep_labels & labels:
            result.append(issue)
    return result

def get_closed_issues(repo, milestone, keep_labels=frozenset(['M-relnotes'])):
    """Return a list of closed issues for the given milestone
        repo: github.Repository object
        milestone: github.Milestone object
        keep_labels: set of labels for result to partake
       return:
        issue fixed in this milestone."""
    return get_issues(repo, milestone, keep_labels=keep_labels,
        state='closed')
