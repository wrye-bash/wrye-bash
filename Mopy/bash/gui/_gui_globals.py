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
"""Collection of data structures the gui package needs from outside. Keep
those at minimum."""
from copy import copy
from itertools import product

from ..bolt import Path as _Path, empty_path

_gui_images = {} # todo defaultdict with fallback? mark final
_image_resource_dir = empty_path
_color_checks = None
_installer_icons = None
# The 'x' icon, in the status bar icon sizes - filled by init_image_resources
ERROR_ICONS = []

def init_image_resources(images_dir: _Path):
    global _image_resource_dir, _color_checks, _installer_icons
    # CI Hack we could move to caller or add a param
    _image_resource_dir = images_dir if images_dir.is_dir() else \
        _Path.getcwd().join('Mopy', 'bash', 'images')
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
        'purple': (b'#FAB0FF', b'#413252'),
        'red': (b'#FF9494', b'#570000'),
        'white': (b'#F4F4F4', b'#000000'),
        'yellow': (b'#FFFFBF', b'#575700'),
    }
    _installer_icons = dict(arrows)
    statuses = ['off', 'on']
    installer_types = {'': 'checkbox_box.svg', '.dir': 'checkbox_diamond.svg'}
    overlays = ['', '.wiz']
    imgkeys = [*product(statuses, installer_types, overlays)]
    for st, typ, overlay in imgkeys:
        layers = [installer_types[typ]]
        if st == 'on':
            layers.append('checkbox_plus.svg')
        if overlay == '.wiz':
            layers.append('checkbox_wand.svg')
        svg = _icc(layers[0])
        svg.composite(*layers)
        for col, (primary, secondary) in box_colors.items():
            _installer_icons[f'{st}.{col}{overlay}{typ}'] = svg.with_svg_vars(
                primary_color=primary, secondary_color=secondary)
    _installer_icons['corrupt'] = _icc('red_x.svg')
    _gui_images.update(_installer_icons)
    # collect color checks for the rest of the UILists
    _color_checks = dict(arrows)
    for col in box_colors.keys() - {'white', 'grey'}:
        # off and inc(luded) are the off and on boxes of the installers
        _color_checks[f'off.{col}'] = _installer_icons[f'off.{col}']
        _color_checks[f'inc.{col}'] = _installer_icons[f'on.{col}']
        primary, secondary = box_colors[col]
        for st, layer in (('imp', 'checkbox_dot.svg'),
                          ('on', 'checkbox_check.svg')):
            svg = _icc('checkbox_box.svg')
            svg.composite('checkbox_box.svg', layer)
            _color_checks[f'{st}.{col}'] = svg.with_svg_vars(
                primary_color=primary, secondary_color=secondary)
    _gui_images.update(_color_checks)
    # Checkboxes
    pixs = (16, 24, 32)
    for st, col, pix in product(['off', 'on'], ('blue', 'green', 'red'), pixs):
        svg = copy(_color_checks[f'{st}.{col}'])
        svg.set_icon_size(pix)
        _gui_images[f'checkbox.{col}.{st}.{pix}'] = svg
    # Modification time button
    _gui_images['calendar.16'] = _icc('calendar.svg')
    # DocumentViewer
    _gui_images['back.16'] = _icc('back.svg')
    _gui_images['forward.16'] = _icc('forward.svg')
    # Browse and Reset buttons
    _gui_images['folder.16'] = _icc('folder.svg')
    _gui_images['reset.16'] = _icc('reset.svg')
    # DocumentViewer and Restart, help, Settings button, Plugin Checker and
    # Doc Browser
    for (img_key, fname), pix in product((('reload', 'reload'),
            ('help', 'help'), ('settings_button', 'gear'),
            ('plugin_checker', 'checklist'), ('doc_browser', 'book')), pixs):
        _gui_images[f'{img_key}.{pix}'] = _icc(f'{fname}.svg', pix)
    # Checkmark/Cross - the cross in the status bar icon sizes too
    _gui_images['checkmark.16'] = _icc('checkmark.svg')
    ERROR_ICONS[:] = [_icc('error_cross.svg', pix) for pix in pixs]
    _gui_images['error_cross.16'] = ERROR_ICONS[0]
    # Minus/Plus for the Bash Tags popup
    _gui_images['minus.16'] = _icc('minus.svg')
    _gui_images['plus.16'] = _icc('plus.svg')
    # Warning icon in various GUIs
    _gui_images['warning.32'] = _icc('warning.svg', 32)
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
