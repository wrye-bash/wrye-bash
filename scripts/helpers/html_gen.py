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

"""This module exports formatting functions for the forums and the doc files we
are generating."""

# MARKDOWN ========================================
def markdown_list(items, f=lambda x: x):
    for i in items:
        yield '- ' + f(i)

def markdown_link(text, href):
    return '[%s](%s)' % (text, href)

# https://www.markdownguide.org/basic-syntax/#escaping-characters
_md_escapes = {
    '\\': '\\\\',
    '`':  '\\`',
    '*':  '\\*',
    '_':  '\\_',
    '{':  '\\{',
    '}':  '\\}',
    '[':  '\\[',
    ']':  '\\]',
    '(':  '\\(',
    ')':  '\\)',
    '#':  '\\#',
    '+':  '\\+',
    '-':  '\\-',
    '.':  '\\.',
    '!':  '\\!',
    '|':  '\\|',
}

def markdown_escape(text):
    for target, sub in _md_escapes.items():
        text = text.replace(target, sub)
    return text

# BBCODE ========================================
def li(text):
    return '[*]' + text + '[/*]'

def bb_list(items):
    yield '[LIST]'
    for i in items:
        yield li(i)
    yield '[/LIST]'

def spoiler(text):
    yield '[spoiler]'
    yield text
    yield '[/spoiler]'

def size(num, text):
    return '[size=' + str(num) + ']' + text + '[/size]'

# HTML ========================================
def h3(text):
    return '<h3>' + text + '</h3>'

def ul(items, f=lambda x: x):
    yield '\n<ul>'
    for i in items:
        yield '<li>' + f(i) + '</li>'
    yield '</ul>'

def a(text, href):
    return '<a href="%s">%s</a>' % (href, text)

def closed_issue(issue):
    """String representation of a closed issue with assignee."""
    assignees = ''
    if issue.assignees:
        assignees = ' [%s]' % ', '.join(
            sorted(assignee.login for assignee in issue.assignees))
    return '#%u: ' % issue.number + issue.title + assignees
