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
"""Useful functions when porting xEdit definitions over to WB and generally
working on record definitions."""
import re
from collections.abc import Iterable

_xe_regex = re.compile(
    r'(?:if\s+([^\s]+)\s+then\s+)?wbAddGroupOrder\((.{4})\);', re.I)

def gen_top_groups(wb_group_adds: str, conds: dict[str, bool] | None = None):
    """Generate the top_groups from xEdit's wbAddGroupOrder calls. Recommended
    way to use this is to import it in IPython and execute it from there, with
    the copy-pasted wbAddGroupOrders wrapped inside triple quotes.

    Can also handle conditions like IsSSE, just pass in e.g.
    conds={'IsSSE': True}."""
    if conds is None:
        conds = {}
    ret_list = []
    for l in wb_group_adds.splitlines():
        if '{' in l:
            l = l[:l.index('{')]
        if '//' in l:
            l = l[:l.index('//')]
        l = l.strip()
        if not l:
            continue
        l_ma = _xe_regex.match(l)
        if l_ma:
            cond = l_ma.group(1)
            sig = l_ma.group(2).encode('ascii')
            if cond:
                if cond not in conds:
                    raise RuntimeError(f'Need value for condition {cond}')
                elif not conds[cond]:
                    continue
            if sig == b'PLYR':
                continue # xEdit-internal signature, ignore
            ret_list.append(sig)
    return ret_list

_rt_names = {
    b'AACT': 'Action',
    b'ACHR': 'Placed NPC',
    b'ACRE': 'Placed Creature',
    b'ACTI': 'Activator',
    b'ADDN': 'Addon Node',
    b'AECH': 'Audio Effect Chain',
    b'ALCH': 'Ingestible',
    b'ALOC': 'Media Location Controller',
    b'AMDL': 'Aim Model',
    b'AMEF': 'Ammo Effect',
    b'AMMO': 'Ammunition',
    b'ANIO': 'Animated Object',
    b'AORU': 'Attraction Rule',
    b'APPA': 'Alchemical Apparatus',
    b'ARMA': 'Armor Addon',
    b'ARMO': 'Armor',
    b'ARTO': 'Art Object',
    b'ASPC': 'Acoustic Space',
    b'ASTP': 'Association Type',
    b'AVIF': 'Actor Value Information',
    b'BNDS': 'Bendable Spline',
    b'BOOK': 'Book',
    b'BPTD': 'Body Part Data',
    b'BSGN': 'Birthsign',
    b'CAMS': 'Camera Shot',
    b'CCRD': 'Caravan Card',
    b'CDCK': 'Caravan Deck',
    b'CELL': 'Cell',
    b'CHAL': 'Challenge',
    b'CHIP': 'Casino Chip',
    b'CLAS': 'Class',
    b'CLFM': 'Color',
    b'CLMT': 'Climate',
    b'CLOT': 'Clothing',
    b'CMNY': 'Caravan Money',
    b'CMPO': 'Component',
    b'COBJ': 'Constructible Object',
    b'COLL': 'Collision Layer',
    b'CONT': 'Container',
    b'CPTH': 'Camera Path',
    b'CREA': 'Creature',
    b'CSNO': 'Casino',
    b'CSTY': 'Combat Style',
    b'DEBR': 'Debris',
    b'DEHY': 'Dehydration Stage',
    b'DFOB': 'Default Object',
    b'DIAL': 'Dialogue',
    b'DLBR': 'Dialog Branch',
    b'DLVW': 'Dialog View',
    b'DMGT': 'Damage Type',
    b'DOBJ': 'Default Object Manager',
    b'DOOR': 'Door',
    b'DUAL': 'Dual Cast Data',
    b'ECZN': 'Encounter Zone',
    b'EFSH': 'Effect Shader',
    b'ENCH': 'Enchantment',
    b'EQUP': 'Equip Type',
    b'EXPL': 'Explosion',
    b'EYES': 'Eyes',
    b'FACT': 'Faction',
    b'FLOR': 'Flora',
    b'FLST': 'FormID List',
    b'FSTP': 'Footstep',
    b'FSTS': 'Footstep Set',
    b'FURN': 'Furniture',
    b'GDRY': 'God Rays',
    b'GLOB': 'Global',
    b'GMST': 'Game Setting',
    b'GRAS': 'Grass',
    b'HAIR': 'Hair',
    b'HAZD': 'Hazard',
    b'HDPT': 'Head Part',
    b'HUNG': 'Hunger Stage',
    b'IDLE': 'Idle Animation',
    b'IDLM': 'Idle Marker',
    b'IMAD': 'Image Space Adapter',
    b'IMGS': 'Image Space',
    b'IMOD': 'Item Mod',
    b'INFO': 'Dialog Response',
    b'INGR': 'Ingredient',
    b'INNR': 'Instance Naming Rules',
    b'IPCT': 'Impact',
    b'IPDS': 'Impact Dataset',
    b'KEYM': 'Key',
    b'KSSM': 'Sound Keyword Mapping',
    b'KYWD': 'Keyword',
    b'LAND': 'Landscape',
    b'LAYR': 'Layer',
    b'LCRT': 'Location Reference Type',
    b'LCTN': 'Location',
    b'LENS': 'Lens Flare',
    b'LGTM': 'Lighting Template',
    b'LIGH': 'Light',
    b'LSCR': 'Load Screen',
    b'LSCT': 'Load Screen Type',
    b'LTEX': 'Landscape Texture',
    b'LVLC': 'Leveled Creature',
    b'LVLI': 'Leveled Item',
    b'LVLN': 'Leveled NPC',
    b'LVSP': 'Leveled Spell',
    b'MATO': 'Material Object',
    b'MATT': 'Material Type',
    b'MESG': 'Message',
    b'MGEF': 'Magic Effect',
    b'MICN': 'Menu Icon',
    b'MISC': 'Misc. Item',
    b'MOVT': 'Movement Type',
    b'MSET': 'Media Set',
    b'MSTT': 'Moveable Static',
    b'MSWP': 'Material Swap',
    b'MUSC': 'Music Type',
    b'MUST': 'Music Track',
    b'NAVI': 'Navigation Mesh Info Map',
    b'NAVM': 'Navigation Mesh',
    b'NOCM': 'Navigation Mesh Obstacle Manager',
    b'NOTE': 'Note',
    b'NPC_': 'Non-Player Character',
    b'OMOD': 'Object Modification',
    b'OTFT': 'Outfit',
    b'OVIS': 'Object Visibility Manager',
    b'PACK': 'Package',
    b'PERK': 'Perk',
    b'PGRD': 'Path Grid',
    b'PGRE': 'Placed Grenade',
    b'PKIN': 'Pack-In',
    b'PMIS': 'Placed Missile',
    b'PROJ': 'Projectile',
    b'PWAT': 'Placeable Water',
    b'QUST': 'Quest',
    b'RACE': 'Race',
    b'RADS': 'Radiation Stage',
    b'RCCT': 'Recipe Category',
    b'RCPE': 'Recipe',
    b'REFR': 'Placed Object',
    b'REGN': 'Region',
    b'RELA': 'Relationship',
    b'REPU': 'Reputation',
    b'REVB': 'Reverb Parameters',
    b'RFCT': 'Visual Effect',
    b'RFGP': 'Reference Group',
    b'RGDL': 'Ragdoll',
    b'ROAD': 'Road',
    b'SBSP': 'Subspace',
    b'SCCO': 'Scene Collection',
    b'SCEN': 'Scene',
    b'SCOL': 'Static Collection',
    b'SCPT': 'Script',
    b'SCRL': 'Scroll',
    b'SCSN': 'Audio Category Snapshot',
    b'SGST': 'Sigil Stone',
    b'SHOU': 'Shout',
    b'SKIL': 'Skill',
    b'SLGM': 'Soul Gem',
    b'SLPD': 'Sleep Deprivation Stage',
    b'SMBN': 'Story Manager Branch Node',
    b'SMEN': 'Story Manager Event Node',
    b'SMQN': 'Story Manager Quest Node',
    b'SNCT': 'Sound Category',
    b'SNDR': 'Sound Descriptor',
    b'SOPM': 'Sound Output Model',
    b'SOUN': 'Sound Marker',
    b'SPEL': 'Spell',
    b'SPGD': 'Shader Particle Geometry',
    b'STAG': 'Animation Sound Tag Set',
    b'STAT': 'Static',
    b'TACT': 'Talking Activator',
    b'TERM': 'Terminal',
    b'TREE': 'Tree',
    b'TXST': 'Texture Set',
    b'VOLI': 'Volumetric Lighting',
    b'VTYP': 'Voice Type',
    b'WATR': 'Water',
    b'WEAP': 'Weapon',
    b'WOOP': 'Word of Power',
    b'WRLD': 'Worldspace',
    b'WTHR': 'Weather',
}

def mk_html_list(rt_sigs: Iterable[bytes]):
    """Generate an HTML list for the specified WB patcher record types
    definition (e.g. keywords_types). Useful when porting a patcher over and
    wanting to generate HTML docs for the definition."""
    print('                <ul>')
    for s in sorted(rt_sigs):
        print(f"                    <li>({s.decode('ascii')}) "
              f"{_rt_names[s]}</li>")
    print('                </ul>')
