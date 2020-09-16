# -*- coding: utf-8 -*-
#
# GPL License and Copyright Notice ============================================
#  This file is part of Wrye Bash.
#
#  Wrye Bash is free software; you can redistribute it and/or
#  modify it under the terms of the GNU General Public License
#  as published by the Free Software Foundation; either version 2
#  of the License, or (at your option) any later version.
#
#  Wrye Bash is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
#
#  You should have received a copy of the GNU General Public License
#  along with Wrye Bash; if not, write to the Free Software Foundation,
#  Inc., 59 Temple Place - Suite 330, Boston, MA  02111-1307, USA.
#
#  Wrye Bash copyright (C) 2005-2009 Wrye, 2010-2020 Wrye Bash Team
#  https://github.com/wrye-bash
#
# =============================================================================
"""Builds on the rest of brec to provide full definitions and base classes for
some commonly needed records."""

from __future__ import division, print_function
import cPickle as pickle  # PY3
import re
import struct
from operator import attrgetter

from .advanced_elements import AttrExistsDecider, AttrValDecider, MelArray, \
    MelUnion
from .basic_elements import MelBase, MelFid, MelFids, MelFloat, MelGroups, \
    MelLString, MelNull, MelStruct, MelUInt32, MelSInt32
from .common_subrecords import MelEdid
from .record_structs import MelRecord, MelSet
from .utils_constants import FID
from .. import bass, bolt, exception
from ..bolt import decode, encode, GPath, sio
from ..exception import StateError

#------------------------------------------------------------------------------
class MreHeaderBase(MelRecord):
    """File header.  Base class for all 'TES4' like records"""
    class MelMasterNames(MelBase):
        """Handles both MAST and DATA, but turns them into two separate lists.
        This is done to make updating the master list much easier."""
        def __init__(self):
            self._debug = False
            self.subType = b'MAST' # just in case something is expecting this

        def getLoaders(self, loaders):
            loaders[b'MAST'] = loaders[b'DATA'] = self

        def getSlotsUsed(self):
            return (u'masters', u'master_sizes')

        def setDefault(self, record):
            record.masters = []
            record.master_sizes = []

        def loadData(self, record, ins, sub_type, size_, readId,
                     __unpacker=struct.Struct(u'Q').unpack):
            if sub_type == b'MAST':
                # Don't use ins.readString, because it will try to use
                # bolt.pluginEncoding for the filename. This is one case where
                # we want to use automatic encoding detection
                master_name = decode(bolt.cstrip(ins.read(size_, readId)),
                                     avoidEncodings=(u'utf8', u'utf-8'))
                record.masters.append(GPath(master_name))
            else: # sub_type == 'DATA'
                # DATA is the size for TES3, but unknown/unused for later games
                record.master_sizes.append(
                    ins.unpack(__unpacker, size_, readId)[0])

        def dumpData(self,record,out):
            pack1 = out.packSub0
            pack2 = out.packSub
            # Truncate or pad the sizes with zeroes as needed
            # TODO(inf) For Morrowind, this will have to query the files for
            #  their size and then store that
            num_masters = len(record.masters)
            num_sizes = len(record.master_sizes)
            record.master_sizes = record.master_sizes[:num_masters] + [0] * (
                    num_masters - num_sizes)
            for master_name, master_size in zip(record.masters,
                                                record.master_sizes):
                pack1(b'MAST', encode(master_name.s, firstEncoding=u'cp1252'))
                pack2(b'DATA', u'Q', master_size)

    def loadData(self, ins, endPos):
        super(MreHeaderBase, self).loadData(ins, endPos)
        num_masters = len(self.masters)
        num_sizes = len(self.master_sizes)
        # Just in case, truncate or pad the sizes with zeroes as needed
        self.master_sizes = self.master_sizes[:num_masters] + [0] * (
                num_masters - num_sizes)

    def getNextObject(self):
        """Gets next object index and increments it for next time."""
        self.changed = True
        self.nextObject += 1
        return self.nextObject -1

    __slots__ = []

#------------------------------------------------------------------------------
class MreFlst(MelRecord):
    """FormID List."""
    rec_sig = b'FLST'

    melSet = MelSet(
        MelEdid(),
        MelFids(b'LNAM', u'formIDInList'),
    )

    __slots__ = melSet.getSlotsUsed() + [u'mergeOverLast', u'mergeSources',
                                         u'items', u'de_records',
                                         u're_records']

    def __init__(self, header, ins=None, do_unpack=False):
        super(MreFlst, self).__init__(header, ins, do_unpack)
        self.mergeOverLast = False #--Merge overrides last mod merged
        self.mergeSources = None #--Set to list by other functions
        self.items  = None #--Set of items included in list
        #--Set of items deleted by list (Deflst mods) unused for Skyrim
        self.de_records = None #--Set of items deleted by list (Deflst mods)
        self.re_records = None # unused, needed by patcher

    def mergeFilter(self, modSet):
        if not self.longFids: raise StateError(u'Fids not in long format')
        self.formIDInList = [f for f in self.formIDInList if f[0] in modSet]

    def mergeWith(self,other,otherMod):
        """Merges newLevl settings and entries with self.
        Requires that: self.items, other.de_records be defined."""
        if not self.longFids or not other.longFids:
            raise StateError(u'Fids not in long format')
        #--Remove items based on other.removes
        if other.de_records:
            removeItems = self.items & other.de_records
            self.formIDInList = [fi for fi in self.formIDInList if fi not in removeItems]
            self.items = (self.items | other.de_records)
        #--Add new items from other
        newItems = set()
        formIDInListAppend = self.formIDInList.append
        newItemsAdd = newItems.add
        for fi in other.formIDInList:
            if fi not in self.items:
                formIDInListAppend(fi)
                newItemsAdd(fi)
        if newItems:
            self.items |= newItems
        #--Is merged list different from other? (And thus written to patch.)
        if len(self.formIDInList) != len(other.formIDInList):
            self.mergeOverLast = True
        else:
            for selfEntry,otherEntry in zip(self.formIDInList,other.formIDInList):
                if selfEntry != otherEntry:
                    self.mergeOverLast = True
                    break
            else:
                self.mergeOverLast = False
        if self.mergeOverLast:
            self.mergeSources.append(otherMod)
        else:
            self.mergeSources = [otherMod]
        self.setChanged()

#------------------------------------------------------------------------------
class MreGlob(MelRecord):
    """Global record.  Rather stupidly all values, despite their designation
       (short,long,float), are stored as floats -- which means that very large
       integers lose precision."""
    rec_sig = b'GLOB'
    melSet = MelSet(
        MelEdid(),
        MelStruct('FNAM','s',('format','s')),
        MelFloat('FLTV', 'value'),
    )
    __slots__ = melSet.getSlotsUsed()

#------------------------------------------------------------------------------
class MreGmstBase(MelRecord):
    """Game Setting record.  Base class, each game should derive from this
    class."""
    Ids = None
    rec_sig = b'GMST'

    melSet = MelSet(
        MelEdid(),
        MelUnion({
            u'b': MelUInt32(b'DATA', u'value'), # actually a bool
            u'f': MelFloat(b'DATA', u'value'),
            u's': MelLString(b'DATA', u'value'),
        }, decider=AttrValDecider(
            u'eid', transformer=lambda eid: decode(eid[0]) if eid else u'i'),
            fallback=MelSInt32(b'DATA', u'value')
        ),
    )
    __slots__ = melSet.getSlotsUsed()

    def getGMSTFid(self):
        """Returns <Oblivion/Skyrim/etc>.esm fid in long format for specified
           eid."""
        cls = self.__class__
        from .. import bosh # Late import to avoid circular imports
        if not cls.Ids:
            from .. import bush
            fname = bass.dirs[u'db'].join(bush.game.pklfile)
            try:
                with fname.open(u'rb') as pkl_file:
                    cls.Ids = pickle.load(pkl_file)[cls.rec_sig]
            except:
                old = bolt.deprintOn
                bolt.deprintOn = True
                bolt.deprint(u'Error loading %s:' % fname, traceback=True)
                bolt.deprintOn = old
                raise
        return bosh.modInfos.masterName,cls.Ids[self.eid]

#------------------------------------------------------------------------------
class MreLand(MelRecord):
    """Land structure. Part of exterior cells."""
    rec_sig = b'LAND'

    melSet = MelSet(
        MelBase('DATA', 'unknown'),
        MelBase('VNML', 'vertex_normals'),
        MelBase('VHGT', 'vertex_height_map'),
        MelBase('VCLR', 'vertex_colors'),
        MelGroups('layers',
            # Start a new layer each time we hit one of these
            MelUnion({
                b'ATXT': MelStruct(b'ATXT', u'IBsh', (FID, u'atxt_texture'),
                    u'quadrant', u'unknown', u'layer'),
                b'BTXT': MelStruct(b'BTXT', u'IBsh', (FID, u'btxt_texture'),
                    u'quadrant', u'unknown', u'layer'),
            }),
            # VTXT only exists for ATXT layers
            MelUnion({
                True:  MelBase(b'VTXT', u'alpha_layer_data'),
                False: MelNull(b'VTXT'),
            }, decider=AttrExistsDecider(u'atxt_texture')),
        ),
        MelArray('vertex_textures',
            MelFid('VTEX', 'vertex_texture'),
        ),
    )
    __slots__ = melSet.getSlotsUsed()

#------------------------------------------------------------------------------
class MreLeveledListBase(MelRecord):
    """Base type for leveled item/creature/npc/spells.
       it requires the base class to use the following:
       classAttributes:
          top_copy_attrs -> List of attributes to modify by copying when
                            merging
          entry_copy_attrs -> List of attributes to modify by copying for each
                              list entry when merging
       instanceAttributes:
          entries -> List of items, with the following attributes:
              listId
              level
              count
          chanceNone
          flags
    """
    _flags = bolt.Flags(0,bolt.Flags.getNames(
        (0, 'calcFromAllLevels'),
        (1, 'calcForEachItem'),
        (2, 'useAllSpells'),
        (3, 'specialLoot'),
        ))
    top_copy_attrs = ()
    # TODO(inf) Only overriden for FO3/FNV right now - Skyrim/FO4?
    entry_copy_attrs = ('listId', 'level', 'count')
    __slots__ = ['mergeOverLast', 'mergeSources', 'items', 'de_records',
                 're_records']
                # + ['flags', 'entries'] # define those in the subclasses

    def __init__(self, header, ins=None, do_unpack=False):
        super(MreLeveledListBase, self).__init__(header, ins, do_unpack)
        self.mergeOverLast = False #--Merge overrides last mod merged
        self.mergeSources = None #--Set to list by other functions
        self.items  = None #--Set of items included in list
        self.de_records = None #--Set of items deleted by list (Delev and Relev mods)
        self.re_records = None #--Set of items relevelled by list (Relev mods)

    def mergeFilter(self,modSet):
        if not self.longFids: raise StateError(u'Fids not in long format')
        self.entries = [entry for entry in self.entries if entry.listId[0] in modSet]

    def mergeWith(self,other,otherMod):
        """Merges newLevl settings and entries with self.
        Requires that self.items, other.de_records and other.re_records be
        defined."""
        if not self.longFids or not other.longFids:
            raise exception.StateError(u'Fids not in long format')
        #--Relevel or not?
        if other.re_records:
            for attr in self.__class__.top_copy_attrs:
                self.__setattr__(attr,other.__getattribute__(attr))
            self.flags = other.flags()
        else:
            for attr in self.__class__.top_copy_attrs:
                otherAttr = other.__getattribute__(attr)
                if otherAttr is not None:
                    self.__setattr__(attr, otherAttr)
            self.flags |= other.flags
        #--Remove items based on other.removes
        if other.de_records or other.re_records:
            removeItems = self.items & (other.de_records | other.re_records)
            self.entries = [entry for entry in self.entries if entry.listId not in removeItems]
            self.items = (self.items | other.de_records) - other.re_records
        hasOldItems = bool(self.items)
        #--Add new items from other
        newItems = set()
        entriesAppend = self.entries.append
        newItemsAdd = newItems.add
        for entry in other.entries:
            if entry.listId not in self.items:
                entriesAppend(entry)
                newItemsAdd(entry.listId)
        # Check if merging exceeded the counter's limit and, if so, truncate it
        # and warn. Note that pre-Skyrim games do not have this limitation.
        from .. import bush
        max_lvl_size = bush.game.Esp.max_lvl_list_size
        if max_lvl_size and len(self.entries) > max_lvl_size:
            # TODO(inf) In the future, offer an option to auto-split these into
            #  multiple sub-lists instead
            bolt.deprint(u"Merging changes from mod '%s' to leveled list %r "
                         u'caused it to exceed %u entries. Truncating back '
                         u'to %u, you will have to fix this manually!' %
                         (otherMod.s, self, max_lvl_size, max_lvl_size))
            self.entries = self.entries[:max_lvl_size]
        entry_copy_attrs_key = attrgetter(*self.__class__.entry_copy_attrs)
        if newItems:
            self.items |= newItems
            self.entries.sort(key=entry_copy_attrs_key)
        #--Is merged list different from other? (And thus written to patch.)
        if ((len(self.entries) != len(other.entries)) or
                (self.flags != other.flags)):
            self.mergeOverLast = True
        else:
            my_val = self.__getattribute__
            other_val = other.__getattribute__
            # Check copy-attributes first, break if they are different
            for attr in self.__class__.top_copy_attrs:
                if my_val(attr) != other_val(attr):
                    self.mergeOverLast = True
                    break
            else:
                # Then, check the sort-attributes, same story
                otherlist = other.entries
                otherlist.sort(key=entry_copy_attrs_key)
                for selfEntry,otherEntry in zip(self.entries,otherlist):
                    my_val = selfEntry.__getattribute__
                    other_val = otherEntry.__getattribute__
                    for attr in self.__class__.entry_copy_attrs:
                        if my_val(attr) != other_val(attr):
                            break
                    else:
                        # attributes are identical, try next entry
                        continue
                    # attributes differ, no need to look at more entries
                    self.mergeOverLast = True
                    break
                else:
                    # Neither one had different attributes
                    self.mergeOverLast = False
        if self.mergeOverLast:
            self.mergeSources.append(otherMod)
        else:
            self.mergeSources = [otherMod]
        self.setChanged(self.mergeOverLast)

#------------------------------------------------------------------------------
class MreHasEffects(object):
    """Mixin class for magic items."""
    __slots__ = []

    def getEffects(self):
        """Returns a summary of effects. Useful for alchemical catalog."""
        from .. import bush
        effects = []
        effectsAppend = effects.append
        for effect in self.effects:
            mgef, actorValue = effect.name, effect.actorValue
            if mgef not in bush.game.generic_av_effects:
                actorValue = 0
            effectsAppend((mgef,actorValue))
        return effects

    def getSpellSchool(self):
        """Returns the school based on the highest cost spell effect."""
        from .. import bush
        spellSchool = [0,0]
        for effect in self.effects:
            school = bush.game.mgef_school[effect.name]
            effectValue = bush.game.mgef_basevalue[effect.name]
            if effect.magnitude:
                effectValue *= effect.magnitude
            if effect.area:
                effectValue *= (effect.area // 10)
            if effect.duration:
                effectValue *= effect.duration
            if spellSchool[0] < effectValue:
                spellSchool = [effectValue,school]
        return spellSchool[1]

    def getEffectsSummary(self):
        """Return a text description of magic effects."""
        from .. import bush
        with sio() as buff:
            avEffects = bush.game.generic_av_effects
            aValues = bush.game.actor_values
            buffWrite = buff.write
            if self.effects:
                school = self.getSpellSchool()
                buffWrite(aValues[20+school] + u'\n')
            for index,effect in enumerate(self.effects):
                if effect.scriptEffect:
                    effectName = effect.scriptEffect.full or u'Script Effect'
                else:
                    effectName = bush.game.mgef_name[effect.name]
                    if effect.name in avEffects:
                        effectName = re.sub(_(u'(Attribute|Skill)'),aValues[effect.actorValue],effectName)
                buffWrite(u'o+*'[effect.recipient]+u' '+effectName)
                if effect.magnitude: buffWrite(u' %sm'%effect.magnitude)
                if effect.area: buffWrite(u' %sa'%effect.area)
                if effect.duration > 1: buffWrite(u' %sd'%effect.duration)
                buffWrite(u'\n')
            return buff.getvalue()

#------------------------------------------------------------------------------
class MreWithItems(MelRecord):
    """Base class for record types that contain a list of items (MelItems)."""
    __slots__ = []

    def mergeFilter(self, modSet):
        if not self.longFids: raise StateError(u'Fids not in long format')
        self.items = [i for i in self.items if i.item[0] in modSet]

#------------------------------------------------------------------------------
class MreActorBase(MreWithItems):
    """Base class for Creatures and NPCs."""
    __slots__ = []

    def mergeFilter(self, modSet):
        super(MreActorBase, self).mergeFilter(modSet)
        self.spells = [x for x in self.spells if x[0] in modSet]
        self.factions = [x for x in self.factions if x.faction[0] in modSet]
