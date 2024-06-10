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
"""Collection of data structures the gui package needs from outside. Keep
those at minimum."""
import os
from copy import copy
from itertools import product

from ..bolt import Path as _Path

_gui_images = {} # todo defaultdict with fallback? mark final
_image_resource_dir = ''
_color_checks = None
_installer_icons = None

def init_image_resources(images_dir):
    global _image_resource_dir, _color_checks, _installer_icons
    _image_resource_dir = images_dir
    if not os.path.isdir(images_dir): # CI Hack we could move to caller or add a param
        _image_resource_dir = _Path.getcwd().join('Mopy', 'bash', 'images')
    from .images import GuiImage
    def _icc(fname, bm_px_size=16):
        """Creates an Image wrapper.

        :param fname: The image' filename, relative to bash/images.
        :param bm_px_size: The size of the resulting bitmap, in
            device-independent pixels (DIP)."""
        return GuiImage.from_path(fname, iconSize=bm_px_size)
    # Up/Down arrows for UIList columns
    arrows = {}
    for arr in ['up', 'down']:
        arrows[f'arrow.{arr}.16'] = _icc(f'arrow_{arr}.svg')
    # collect the installer icons
    box_colors = { # name: (primary, secondary)
        'blue': (b'#B3D9FF', b'#003D7A'),
        'green': (b'#C1FFC1', b'#005700'),
        'grey': (b'#C0C0C0', b'#000000'),
        'orange': (b'#FFD5AA', b'#663300'),
        'purple': (b'#FAB0FF', b'#FAB0FF'),
        'red': (b'#FF9494', b'#570000'),
        'white': (b'#F4F4F4', b'#000000'),
        'yellow': (b'#FFFFBF', b'#575700'),
    }
    _installer_icons = dict(arrows)
    statuses = ['off', 'on']
    installer_types = ['', '.dir']
    overlays = ['', '.wiz']
    imgkeys = [*product(statuses, installer_types, overlays)]
    for st, typ, overlay in imgkeys:
        if typ == '.dir':
            layers = ['checkbox_diamond.svg']
        else:
            layers = ['checkbox_box.svg']
        if st == 'on':
            layers.append('checkbox_plus.svg')
        if overlay == '.wiz':
            layers.append('checkbox_wand.svg')
        svg = _icc(layers[0])
        svg.composite(*layers)
        for col, (primary, secondary) in box_colors.items():
            _installer_icons[f'{st}.{col}{typ}{overlay}'] = svg.with_svg_vars(
                primary_color=primary, secondary_color=secondary)
    _installer_icons['corrupt'] = _icc('red_x.svg')
    _gui_images.update(_installer_icons)
    # collect color checks for the rest of the UILists
    _color_checks = dict(arrows)
    for st, col in product(['imp', 'inc', 'off', 'on'],
                           box_colors.keys() - {'white', 'grey'}):
        inst_key = 'on' if st == 'inc' else ('inc' if st == 'on' else st)
        if inst_key in _installer_icons:
            colored_check = _installer_icons[f'{inst_key}.{col}']
        else:
            layers = ['checkbox_box.svg']
            if st == 'imp':
                layers.append('checkbox_dot.svg')
            elif st == 'inc':
                layers.append('checkbox_check.svg')
            elif st == 'on':
                layers.append('checkbox_check.svg')
            svg = _icc(layers[0])
            svg.composite(*layers)
            primary, secondary = box_colors[col]
            colored_check = svg.with_svg_vars(primary_color=primary,
                                              secondary_color=secondary)
        _color_checks[f'{st}.{col}'] = colored_check
    _gui_images.update(_color_checks)
    # PNGs --------------------------------------------------------------------
    # Checkboxes
    pixs = (16, 24, 32)
    for st, col, pix in product(['off', 'on'], ('blue', 'green', 'red'), pixs):
        svg = copy(_color_checks[f'{st}.{col}'])
        svg.set_icon_size(pix)
        _gui_images[f'checkbox.{col}.{st}.{pix}'] = svg
    # SVGs --------------------------------------------------------------------
    # Modification time button
    _gui_images['calendar.16'] = _icc('calendar.svg')
    # DocumentViewer
    _gui_images['back.16'] = _icc('back.svg')
    _gui_images['forward.16'] = _icc('forward.svg')
    # Browse and Reset buttons
    _gui_images['folder.16'] = _icc('folder.svg')
    _gui_images['reset.16'] = _icc('reset.svg')
    # DocumentViewer, Restart and help
    for fname, pix in product(('reload', 'help'), pixs):
        _gui_images[f'{fname}.{pix}'] = _icc(f'{fname}.svg', pix)
    # Checkmark/Cross
    _gui_images['checkmark.16'] = _icc('checkmark.svg')
    _gui_images['error_cross.16'] = _icc('error_cross.svg')
    # Minus/Plus for the Bash Tags popup
    _gui_images['minus.16'] = _icc('minus.svg')
    _gui_images['plus.16'] = _icc('plus.svg')
    # Warning icon in various GUIs
    _gui_images['warning.32'] = _icc('warning.svg', 32)
    # Settings button
    _gui_images['settings_button.16'] = _icc('gear.svg')
    _gui_images['settings_button.24'] = _icc('gear.svg', 24)
    _gui_images['settings_button.32'] = _icc('gear.svg', 32)
    # Plugin Checker
    _gui_images['plugin_checker.16'] = _icc('checklist.svg')
    _gui_images['plugin_checker.24'] = _icc('checklist.svg', 24)
    _gui_images['plugin_checker.32'] = _icc('checklist.svg', 32)
    # Doc Browser
    _gui_images['doc_browser.16'] = _icc('book.svg')
    _gui_images['doc_browser.24'] = _icc('book.svg', 24)
    _gui_images['doc_browser.32'] = _icc('book.svg', 32)
    # Check/Uncheck All buttons
    _gui_images['square_empty.16'] = _icc('square_empty.svg')
    _gui_images['square_check.16'] = _icc('square_checked.svg')
    # Deletion dialog button
    _gui_images['trash_can.32'] = _icc('trash_can.svg', 32)

def get_image(img_key):
    return _gui_images[img_key]

def get_image_dir():
    return _image_resource_dir

def get_color_checks():
    return _color_checks

def get_installer_color_checks():
    return _installer_icons
