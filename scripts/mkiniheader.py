#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# GPL License and Copyright Notice ============================================
#
#  This file is free software; you can redistribute it and/or
#  modify it under the terms of the GNU General Public License
#  as published by the Free Software Foundation; either version 2
#  of the License, or (at your option) any later version.
#
#  This file is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
#
#  MCow Bash.ini ASCII Art Maker copyright (C) 2011 Metallicow
#
# =============================================================================

import argparse


_lines = []
_lines.append(";#   ____            _       _       _   ")
_lines.append(";#  |  _ \          | |     (_)     (_)  ")
_lines.append(";#  | |_) | __ _ ___| |__    _ _ __  _   ")
_lines.append(";#  |  _ < / _` / __| '_ \  | | '_ \| |  ")
_lines.append(";#  | |_) | (_| \__ \ | | |_| | | | | |  ")
_lines.append(";#  |____/ \__,_|___/_| |_(_)_|_| |_|_|  ")

def one(lines):
    lines[0] += ' __  '
    lines[1] += '/_ | '
    lines[2] += ' | | '
    lines[3] += ' | | '
    lines[4] += ' | | '
    lines[5] += ' |_| '

def two(lines):
    lines[0] += ' ___   '
    lines[1] += '|__ \  '
    lines[2] += '   ) | '
    lines[3] += '  / /  '
    lines[4] += ' / /_  '
    lines[5] += '|____| '

def three(lines):
    lines[0] += ' ____   '
    lines[1] += '|___ \  '
    lines[2] += '  __) | '
    lines[3] += ' |__ <  '
    lines[4] += ' ___) | '
    lines[5] += '|____/  '

def four(lines):
    lines[0] += '        '
    lines[1] += '| | | | '
    lines[2] += '| |_| | '
    lines[3] += '|___  | '
    lines[4] += '    | | '
    lines[5] += '    |_| '

def five(lines):
    lines[0] += ' _____  '
    lines[1] += '| ____| '
    lines[2] += '| |__   '
    lines[3] += '|___ \  '
    lines[4] += ' ___) | '
    lines[5] += '|____/  '

def six(lines):
    lines[0] += '   __   '
    lines[1] += '  / /   '
    lines[2] += ' / /_   '
    lines[3] += '|  _ \  '
    lines[4] += '| (_) | '
    lines[5] += ' \___/  '

def seven(lines):
    lines[0] += ' ______  '
    lines[1] += '|____  ) '
    lines[2] += '    / /  '
    lines[3] += '   / /   '
    lines[4] += '  / /    '
    lines[5] += ' /_/     '

def eight(lines):
    lines[0] += '  ___   '
    lines[1] += ' / _ \  '
    lines[2] += '( (_) ) '
    lines[3] += ' ) _ (  '
    lines[4] += '( (_) ) '
    lines[5] += ' \___/  '

def nine(lines):
    lines[0] += '  ___   '
    lines[1] += ' / _ \  '
    lines[2] += '( (_) | '
    lines[3] += ' \__, | '
    lines[4] += '   / /  '
    lines[5] += '  /_/   '

def zero(lines):
    lines[0] += '  ___   '
    lines[1] += ' / _ \  '
    lines[2] += '| | | | '
    lines[3] += '| | | | '
    lines[4] += '| |_| | '
    lines[5] += ' \___/  '

def dot(lines):
    remove_one_trailing_space(lines)
    lines[0] += '   '
    lines[1] += '   '
    lines[2] += '   '
    lines[3] += '   '
    lines[4] += ' _ '
    lines[5] += '(_)'

def remove_one_trailing_space(lines):
    for line in _lines:
        if not line.endswith(' '):
            return
    lines[0] = lines[0][:-1]
    lines[1] = lines[1][:-1]
    lines[2] = lines[2][:-1]
    lines[3] = lines[3][:-1]
    lines[4] = lines[4][:-1]
    lines[5] = lines[5][:-1]


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='The Wrye Bash INI file header generator.')
    parser.add_argument('verStr', metavar='VERSION', type=str, help='the version string')

    options = parser.parse_args()
    for char in options.verStr:
        if   '1' == char: one(_lines)
        elif '2' == char: two(_lines)
        elif '3' == char: three(_lines)
        elif '4' == char: four(_lines)
        elif '5' == char: five(_lines)
        elif '6' == char: six(_lines)
        elif '7' == char: seven(_lines)
        elif '8' == char: eight(_lines)
        elif '9' == char: nine(_lines)
        elif '.' == char: dot(_lines)
        else: print "unhandled character: '%s'" % char

    for line in _lines:
        print line.rstrip()
