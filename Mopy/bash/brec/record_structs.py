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
"""Houses abstract base classes and some APIs for representing records and
subrecords in memory."""

import copy
import io
import zlib
from collections import defaultdict
from typing import Self

from . import utils_constants
from .basic_elements import SubrecordBlob, unpackSubHeader
from .mod_io import ModReader, RecordHeader
from .utils_constants import int_unpacker
from .. import bolt, exception
from ..bolt import decoder, flag, float_or_none, int_or_zero, sig_to_str, \
    str_or_none, struct_pack

def _str_to_bool(value, __falsy=frozenset(
    ['', 'none', 'false', 'no', '0', '0.0'])):
    return value.strip().lower() not in __falsy

# Cross game dict, mapping attribute -> csv (de)serializer/csv column header
attr_csv_struct = {
    'aimArc': [float_or_none, _('Aim Arc')],
    'ammoUse': [int_or_zero, _('Ammunition Use')],
    'animationAttackMultiplier': [float_or_none,
                                  _('Animation Attack Multiplier')],
    'animationMultiplier': [float_or_none, _('Animation Multiplier')],
    'armorRating': [int_or_zero, _('Armor Rating')],
    'attackShotsPerSec': [float_or_none, _('Attack Shots Per Second')],
    'baseVatsToHitChance': [int_or_zero, _('Base VATS To-Hit Chance')],
    'calc_max_level': [int_or_zero, _('CalcMax')],
    'calc_min_level': [int_or_zero, _('CalcMin')],
    'clipRounds': [int_or_zero, _('Clip Rounds')],
    'clipsize': [int_or_zero, _('Clip Size')],
    'criticalDamage': [int_or_zero, _('Critical Damage')],
    'criticalEffect': [int_or_zero, _('Critical Effect')],
    'criticalMultiplier': [float_or_none, _('Critical Multiplier')],
    'damage': [int_or_zero, _('Damage')],
    'dr': [int_or_zero, _('Damage Resistance')],
    'dt': [float_or_none, _('Damage Threshold')],
    'duration': [int_or_zero, _('Duration')],
    'eid': [str_or_none, _('Editor Id')],
    'enchantPoints': [int_or_zero, _('Enchantment Points')],
    'fireRate': [float_or_none, _('Fire Rate')],
    'flags': [int_or_zero, _('Flags')],
    'full': [str_or_none, _('Name')],
    'group_combat_reaction': [str_or_none, _('Group Combat Reaction')],
    'health': [int_or_zero, _('Health')],
    'iconPath': [str_or_none, _('Icon Path')],
    'impulseDist': [float_or_none, _('Impulse Distance')],
    'jamTime': [float_or_none, _('Jam Time')],
    'killImpulse': [float_or_none, _('Kill Impulse')],
    'level_offset': [int_or_zero, _('Offset')],
    'limbDmgMult': [float_or_none, _('Limb Damage Multiplier')],
    'maxRange': [float_or_none, _('Maximum Range')],
    'minRange': [float_or_none, _('Minimum Range')],
    'minSpread': [float_or_none, _('Minimum Spread')],
    'mod': [str_or_none, _('Modifier')],
    'model.modPath': [str_or_none, _('Model Path')],
    'model.modb': [float_or_none, _('Bound Radius')],
    'offset': [int_or_zero, _('Offset')],
    'overrideActionPoint': [float_or_none, _('Override - Action Point')],
    'overrideDamageToWeaponMult': [float_or_none,
        _('Override - Damage To Weapon Multiplier')],
    'projPerShot': [int_or_zero, _('Projectiles Per Shot')],
    'projectileCount': [int_or_zero, _('Projectile Count')],
    'quality': [float_or_none, _('Quality')],
    'reach': [float_or_none, _('Reach')],
    'regenRate': [float_or_none, _('Regeneration Rate')],
    'reloadTime': [float_or_none, _('Reload Time')],
    'rumbleDuration': [float_or_none, _('Rumble - Duration')],
    'rumbleLeftMotorStrength': [float_or_none,
                                _('Rumble - Left Motor Strength')],
    'rumbleRightMotorStrength': [float_or_none,
                                 _('Rumble - Right Motor Strength')],
    'rumbleWavelength': [float_or_none, _('Rumble - Wavelength')],
    'semiAutomaticFireDelayMax': [float_or_none,
                                  _('Maximum Semi-Automatic Fire Delay')],
    'semiAutomaticFireDelayMin': [float_or_none,
                                  _('Minumum Semi-Automatic Fire Delay')],
    'sightFov': [float_or_none, _('Sight Fov')],
    'sightUsage': [float_or_none, _('Sight Usage')],
    'skillReq': [int_or_zero, _('Skill Requirement')],
    'speed': [float_or_none, _('Speed')],
    'spell_cost': [int_or_zero, _('Cost')],
    'spell_flags': [int_or_zero, _('Spell Flags')],
    'spell_flags.no_absorb_reflect': [_str_to_bool,
                                      _('Disallow Absorb and Reflect')],
    'spell_flags.ignoreLOS': [_str_to_bool, _('Area Effect Ignores LOS')],
    'spell_flags.immune_to_silence': [_str_to_bool, _('Immune To Silence')],
    'spell_flags.manual_cost_calc': [_str_to_bool, _('Manual Cost')],
    'spell_flags.pc_start_spell': [_str_to_bool, _('Start Spell')],
    'spell_flags.script_effect_always_applies': [_str_to_bool,
                                                 _('Script Always Applies')],
    'spell_flags.touch_spell_explodes_without_target': [
        _str_to_bool, _('Touch Explodes Without Target')],
    'spell_level': [str_or_none, _('Level Type')],
    'spell_type': [str_or_none, _('Spell Type')],
    'spread': [float_or_none, _('Spread')],
    'stagger': [float_or_none, _('Stagger')],
    'strength': [int_or_zero, _('Strength')],
    'strengthReq': [int_or_zero, _('Strength Requirement')],
    'uses': [int_or_zero, _('Uses')], 'value': [int_or_zero, _('Value')],
    'vatsAp': [float_or_none, _('VATS AP')],
    'vatsDamMult': [float_or_none, _('VATS Damage Multiplier')],
    'vatsSkill': [float_or_none, _('VATS Skill')],
    'weight': [float_or_none, _('Weight')],
}

# Note: these two formats *must* remain in the %d/%s style! f-strings will
# break with Flags etc. due to them not implementing __format__
for _k, _v in attr_csv_struct.items():
    if _v[0] is int_or_zero: # should also cover Flags
        _v.append(lambda x: '"%d"' % x)
    else: # also covers floats which should be wrapped in Rounder (see __str__)
        _v.append(lambda x: '"%s"' % x)
del _k, _v
attr_csv_struct[u'enchantPoints'][2] = lambda x: ( # can be None
    '"None"' if x is None else f'"{x:d}"')

#------------------------------------------------------------------------------
# Mod Element Sets ------------------------------------------------------------
class MelSet(object):
    """Set of mod record elements."""

    def __init__(self,*elements):
        # Filter out None, produced by static deciders like fnv_only
        self.elements = [e for e in elements if e is not None]
        self.defaulters = {}
        self.loaders = {}
        self.formElements = set()
        self._sort_elements = []
        for element in self.elements:
            element.getDefaulters(self.defaulters,'')
            element.getLoaders(self.loaders)
            element.hasFids(self.formElements)
            if element.needs_sorting():
                self._sort_elements.append(element)
        for sig_candidate in self.loaders:
            if not isinstance(sig_candidate, bytes) or len(sig_candidate) != 4:
                raise SyntaxError(f"Invalid signature '{sig_candidate!r}': "
                                  f"Signatures must be bytestrings and 4 "
                                  f"bytes in length.")

    def getSlotsUsed(self):
        """This function returns all of the attributes used in record instances
        that use this instance."""
        # Use a set to discard duplicates - saves memory!
        return list({s for element in self.elements
                     for s in element.getSlotsUsed()})

    def check_duplicate_attrs(self, curr_rec_sig):
        """This will raise a SyntaxError if any record attributes occur in more
        than one element. However, this is sometimes intended behavior (e.g.
        Oblivion's MreSoun uses it to upgrade an old subrecord to a newer one).
        In such cases, set the MreRecord class variable _has_duplicate_attrs to
        True for that record type (after carefully checking that there are no
        unwanted duplicate attributes)."""
        all_slots = set()
        for element in self.elements:
            element_slots = set(element.getSlotsUsed())
            if duplicate_slots := (all_slots & element_slots):
                raise SyntaxError(
                    f'Duplicate element attributes in record type '
                    f'{curr_rec_sig}: {sorted(duplicate_slots)}. This '
                    f'most likely points at an attribute collision, '
                    f'make sure to choose unique attribute names!')
            all_slots.update(element_slots)

    def getDefault(self,attr):
        """Returns default instance of specified instance. Only useful for
        MelGroup and MelGroups."""
        return self.defaulters[attr].getDefault()

    def dumpData(self,record, out):
        """Dumps state into out. Called by getSize()."""
        for element in self.elements:
            try:
                element.dumpData(record,out)
            except:
                bolt.deprint(u'Error dumping data: ', traceback=True)
                bolt.deprint(u'Occurred while dumping '
                             u'<%(eid)s[%(signature)s:%(fid)s]>' % {
                    u'signature': record.rec_str,
                    u'fid': f'{record.fid}',
                    u'eid': (record.eid + u' ') if getattr(record, u'eid',
                                                           None) else u'',
                })
                bolt.deprint('element:', element)
                bolt.deprint('record flags:', getattr(record, 'flags1', None))
                for attr in record.__slots__:
                    attr1 = getattr(record, attr, None)
                    if attr1 is not None:
                        bolt.deprint(u'> %s: %r' % (attr, attr1))
                raise

    def mapFids(self, record, mapper, save_fids=False):
        """Maps fids of subelements."""
        for element in self.formElements:
            element.mapFids(record, mapper, save_fids)

    def sort_subrecords(self, record):
        """Sorts all subrecords of the specified record that need sorting."""
        for element in self._sort_elements:
            element.sort_subrecord(record)

    def with_distributor(self, distributor_config: dict) -> Self:
        """Adds a distributor to this MelSet. See _MelDistributor for more
        information. Convenience method that avoids having to import and
        explicitly construct a _MelDistributor. This is supposed to be chained
        immediately after MelSet.__init__.

        :param distributor_config: The config to pass to the distributor. If
            this is None, no distributor will be set and self will be returned
            unmodified.
        :return: self, for ease of construction."""
        if distributor_config is None:
            # Happens when using fnv_only etc. to have a decider for only one
            # game
            return self
        # Make a copy, that way one distributor config can be used for multiple
        # record classes. _MelDistributor may modify its parameter, so not
        # making a copy wouldn't be safe in such a scenario.
        from .advanced_elements import _MelDistributor # avoid circular import
        distributor = _MelDistributor(distributor_config.copy())
        self.elements += (distributor,)
        distributor.getLoaders(self.loaders)
        distributor.set_mel_set(self)
        return self

#------------------------------------------------------------------------------
# Records ---------------------------------------------------------------------
#------------------------------------------------------------------------------
class RecordType(type):
    """Metaclass responsible for adding slots in MreRecord type instances and
    collecting signature and type information on class creation."""
    # record sigs to class implementing them - collected at class creation
    sig_to_class = {}
    # Record types that *don't* have a complex child structure (e.g. CELL), are
    # *not* part of such a complex structure (e.g. REFR), or are *not* the file
    # header (TES3/TES4)
    simpleTypes = set()
    # Maps subrecord signatures to a set of record signatures that can contain
    # those subrecords
    subrec_sig_to_record_sig = defaultdict(set)
    # nested record types mapped to top record type they belong to
    nested_to_top = defaultdict(set)

    def __new__(cls, name, bases, classdict):
        slots = classdict.get('__slots__', ())
        classdict['__slots__'] = (*slots, *melSet.getSlotsUsed()) if (
            melSet := classdict.get('melSet', ())) else slots
        new = super(RecordType, cls).__new__(cls, name, bases, classdict)
        if rsig := getattr(new, 'rec_sig', None):
            cls.sig_to_class[rsig] = new
            if new.melSet:
                for sr_sig in new.melSet.loaders:
                    RecordType.subrec_sig_to_record_sig[sr_sig].add(rsig)
            for sig in new.nested_records_sigs():
                RecordType.nested_to_top[sig].add(rsig)
        return new

class MreRecord(metaclass=RecordType):
    """Generic Record. See the Wrye Bash wiki for information on all possible
    header flags:
    https://github.com/wrye-bash/wrye-bash/wiki/%5Bdev%5D-Record-Header-Flags
    """
    __slots__ = ('header', '_rec_sig', 'fid', 'flags1', 'changed', 'data',
                 'inName')
    subtype_attr = {b'EDID': u'eid', b'FULL': u'full', b'MODL': u'model'}
    isKeyedByEid = False

    class HeaderFlags(bolt.Flags):
        """Common flags to all (most) record types, based on Oblivion flags.
        NOTE: Use explicit indices here and in subclasses, otherwise the order
        can be messed up (due to type hints being saved in dicts which are
        ordered by insertion order, not update order)."""
        deleted: bool = flag(5)
        ignored: bool = flag(12)
        compressed: bool = flag(18)
        ##: PARTIAL_FORM_HACK: so that we can performantly access this in
        # should_skip et al
        partial_form = False

    def __init__(self, header, ins=None, *, do_unpack=True):
        self.header = header # type: RecHeader
        self._rec_sig: bytes = header.recType
        self.fid: utils_constants.FormId = header.fid
        flags1_class = RecordType.sig_to_class[self._rec_sig].HeaderFlags
        self.flags1: MreRecord.HeaderFlags = flags1_class(header.flags1)
        self.changed: bool = False
        self.data: bytes | None = None
        self.inName: str | None = ins and ins.inName
        if ins: # Load data from ins stream
            file_offset = ins.tell()
            ##: Couldn't we toss this data if we unpacked it? (memory!)
            self.data = ins.read(header.blob_size, self._rec_sig,
                                 file_offset=file_offset)
            if not do_unpack: return  #--Read, but don't analyze.
            if self.__class__ is MreRecord: return  # nothing to be done
            ins_ins, ins_size = ins.ins, ins.size
            ins_debug_offset = ins.debug_offset
            try: # swap the wrapped io stream with our (decompressed) data
                ins.ins, ins.size = self.getDecompressed()
                ins.debug_offset = ins_debug_offset + file_offset
                self.loadData(ins, ins.size, file_offset=file_offset)
            finally: # restore the wrapped stream to read next record
                ins.ins, ins.size = ins_ins, ins_size
                ins.debug_offset = ins_debug_offset

    @classmethod
    def nested_records_sigs(cls):
        return set()

    def __repr__(self):
        reid = (self.eid + ' ') if getattr(self, 'eid', None) else ''
        return f'<{reid}[{self.rec_str}:{self.fid}]>'

    # Group element API -------------------------------------------------------
    def should_skip(self):
        """Returns True if this record should be skipped by most processing,
        i.e. if it is ignored or deleted."""
        ##: PARTIAL_FORM_HACK: We shouldn't skip these, since some of their
        # data still gets applied
        return (self.flags1.ignored or self.flags1.deleted or
                self.flags1.partial_form)

    def group_key(self): ##: we need an MreRecord mixin - too many ifs
        """Return a key for indexing the record on the parent (MobObjects)
        grup."""
        record_id = self.fid
        if self.isKeyedByEid and record_id.is_null():
            record_id = self.eid
        return record_id

    @staticmethod
    def get_num_headers():
        """Hacky way of simplifying _AMobBase API."""
        return 1

    def getTypeCopy(self):
        """Return a copy of self - MreRecord base class will find and return an
        instance of the appropriate subclass (!)"""
        subclass = type(self).sig_to_class[self._rec_sig]
        myCopy = subclass(self.header)
        myCopy.data = self.data
        with ModReader(self.inName, *self.getDecompressed()) as reader:
            myCopy.loadData(reader, reader.size) # load the data to rec attrs
        myCopy.changed = True
        myCopy.data = None
        return myCopy

    def keep_fids(self, keep_plugins):
        """Filter specific record elements that contain fids to only keep
        those whose fids come from keep_plugins. E.g. for a list record
        element, items coming from mods not in keep_plugins will be removed
        from the list."""

    def getDecompressed(self, *, __unpacker=int_unpacker):
        """Return (decompressed if necessary) record data wrapped in BytesIO.
        Return also the length of the data."""
        if not self.flags1.compressed:
            return io.BytesIO(self.data), len(self.data)
        decompressed_size, = __unpacker(self.data[:4])
        decomp = zlib.decompress(self.data[4:])
        if len(decomp) != decompressed_size:
            raise exception.ModError(self.inName,
                f'Mis-sized compressed data. Expected {decompressed_size}, '
                f'got {len(decomp)}.')
        return io.BytesIO(decomp), len(decomp)

    def loadData(self, ins, endPos, *, file_offset=0):
        """Loads data from input stream. Called by load().

        Subclasses should actually read the data, but MreRecord just skips over
        it (assuming that the raw data has already been read to itself. To force
        reading data into an array of subrecords, use iterate_subrecords())."""
        ins.seek(endPos)

    def iterate_subrecords(self, mel_sigs=frozenset()):
        """This is for MreRecord only. Iterates over data unpacking them to
        subrecords - DEPRECATED.

        :type mel_sigs: set"""
        if not self.data: return
        with ModReader(self.inName, *self.getDecompressed()) as reader:
            _rec_sig_ = self._rec_sig
            readAtEnd = reader.atEnd
            while not readAtEnd(reader.size,_rec_sig_):
                subrec = SubrecordBlob(reader, _rec_sig_, mel_sigs)
                if not mel_sigs or subrec.mel_sig in mel_sigs:
                    yield subrec

    def updateMasters(self, masterset_add):
        """Updates set of master names according to masters actually used."""
        raise NotImplementedError(
            f'updateMasters called on skipped type {self.rec_str}')

    def setChanged(self,value=True):
        """Sets changed attribute to value. [Default = True.]"""
        self.changed = value

    def getSize(self):
        """Return size of self.data, (after, if necessary, packing it) PLUS the
        size of the record header."""
        if not self.changed:
            return self.header.blob_size + RecordHeader.rec_header_size
        #--Pack data and return size.
        out = io.BytesIO()
        self._sort_subrecords()
        self.dumpData(out)
        self.data = out.getvalue()
        if self.flags1.compressed:
            dataLen = len(self.data)
            comp = zlib.compress(self.data,6)
            self.data = struct_pack('=I', dataLen) + comp
        self.header.blob_size = len(self.data)
        self.setChanged(False)
        return self.header.blob_size + RecordHeader.rec_header_size

    def dumpData(self,out):
        """Dumps state into data. Called by getSize(). This default version
        just calls subrecords to dump to out."""
        if self.data is None:
            raise exception.StateError(f'Dumping empty record. [{self.inName}:'
                                       f' {self.rec_str} {self.fid}]')
        for subrecord in self.iterate_subrecords():
            subrecord.packSub(out, subrecord.mel_data)

    def _sort_subrecords(self):
        """Sorts all subrecords of this record that need sorting. Default
        implementation does nothing."""

    @property
    def rec_str(self):
        """Decoded record signature - **only** use in exceptions and co."""
        return sig_to_str(self._rec_sig)

    def dump(self,out):
        """Dumps all data to output stream."""
        if self.changed:
            raise exception.StateError(f'Data changed: {self.rec_str}')
        if not self.data and not self.flags1.deleted and \
                self.header.blob_size > 0:
            raise exception.StateError(
                f'Data undefined: {self.rec_str} {self.fid}')
        #--Update the header so it 'packs' correctly
        self.header.flags1 = self.flags1
        self.header.fid = self.fid
        out.write(self.header.pack_head())
        if self.header.blob_size > 0: out.write(self.data)

    #--Accessing subrecords ---------------------------------------------------
    def getSubString(self, mel_sig_):
        """Returns the (stripped) string for a zero-terminated string
        record."""
        # Common subtype expanded in self?
        attr = MreRecord.subtype_attr.get(mel_sig_)
        value = None # default
        # If not MreRecord, then we will have info in data.
        if self.__class__ != MreRecord:
            if attr not in self.__slots__: return value
            return getattr(self, attr)
        for subrec in self.iterate_subrecords(mel_sigs={mel_sig_}):
            value = bolt.cstrip(subrec.mel_data)
            break
        return decoder(value)

    # Classmethods ------------------------------------------------------------
    @classmethod
    def parse_csv_line(cls, csv_fields, index_dict, reuse=False):
        if not reuse:
            attr_dict = {att: attr_csv_struct[att][0](csv_fields[dex]) for
                         att, dex in index_dict.items()}
            return attr_dict
        else:
            for att, dex in index_dict.items():
                index_dict[att] = attr_csv_struct[att][0](csv_fields[dex])
            return index_dict

#------------------------------------------------------------------------------
class MelRecord(MreRecord):
    """Mod record built from mod record elements."""
    #--Subclasses must define as MelSet(*mels)
    melSet: MelSet = None
    rec_sig: bytes = None
    # If set to False, skip the check for duplicate attributes for this
    # subrecord. See MelSet.check_duplicate_attrs for more information.
    _has_duplicate_attrs = False
    # The record attribute and flag name needed to find out if a piece of armor
    # is non-playable. Locations differ in TES4, FO3/FNV and TES5.
    not_playable_flag = ('flags1', 'not_playable')

    def __init__(self, header, ins=None, *, do_unpack=True):
        if self.__class__.rec_sig != header.recType:
            raise ValueError(f'Initialize {type(self)} with header.recType '
                             f'{header.recType}')
        for element in self.__class__.melSet.elements:
            element.setDefault(self)
        MreRecord.__init__(self, header, ins, do_unpack=do_unpack)

    def getTypeCopy(self):
        """Return a copy of self - we must be loaded, data will be discarded"""
        myCopy = copy.deepcopy(self)
        myCopy.changed = True
        myCopy.data = None
        return myCopy

    @classmethod
    def validate_record_syntax(cls):
        """Performs validations on this record's definition."""
        if not cls._has_duplicate_attrs:
            cls.melSet.check_duplicate_attrs(cls.rec_sig)

    @classmethod
    def getDefault(cls, attr):
        """Returns default instance of specified instance. Only useful for
        MelGroup and MelGroups."""
        return cls.melSet.getDefault(attr)

    def loadData(self, ins, endPos, *, file_offset=0):
        """Loads data from input stream."""
        loaders = self.__class__.melSet.loaders
        # Load each subrecord
        ins_at_end = ins.atEnd
        while not ins_at_end(endPos, self._rec_sig):
            sub_type, sub_size = unpackSubHeader(ins, self._rec_sig,
                                                 file_offset=file_offset)
            try:
                loader = loaders[sub_type]
                try:
                    loader.load_mel(self, ins, sub_type, sub_size,
                                    self._rec_sig, sub_type) # *debug_strs
                    continue
                except Exception as er:
                    error = er
            except KeyError: # loaders[sub_type]
                # Wrap this error to make it more understandable
                error = f'Unexpected subrecord: {self.rec_str}.' \
                        f'{sig_to_str(sub_type)}'
            file_offset += ins.tell()
            bolt.deprint(self.error_string('loading', file_offset, sub_size,
                                           sub_type, self.flags1))
            if isinstance(error, str):
                raise exception.ModError(ins.inName, error)
            raise exception.ModError(ins.inName, f'{error!r}') from error
        # Sort once we're done - sorting during loading is obviously a bad idea
        self._sort_subrecords()

    def error_string(self, op, file_offset=None, sub_size=None, sub_type=None, header_flags=None):
        """Return a human-readable description of this record to use in error
        messages."""
        msg = f'Error {op} {self.rec_str} record and/or subrecord: ' \
              f'{self.fid}\n  eid = {getattr(self, "eid", "<<NO EID>>")}'
        if file_offset is None:
            return msg
        li = [msg, f'subrecord = {sig_to_str(sub_type)}',
              f'subrecord size = {sub_size}', f'file pos = {file_offset}',
              f'header flags = {header_flags}']
        return '\n  '.join(li)

    def dumpData(self,out):
        """Dumps state into out. Called by getSize()."""
        self.__class__.melSet.dumpData(self,out)

    def mapFids(self, mapper, save_fids):
        """Applies mapper to fids of sub-elements. Will replace fid with mapped
        value if save == True."""
        self.__class__.melSet.mapFids(self, mapper, save_fids)

    def _sort_subrecords(self):
        """Sorts all subrecords of this record that need sorting."""
        self.__class__.melSet.sort_subrecords(self)

    def updateMasters(self, masterset_add):
        """Updates set of master names according to masters actually used."""
        masterset_add(self.fid)
        for element in self.__class__.melSet.formElements:
            element.mapFids(self, masterset_add)

    # Hacky patcher API - these should really be mixins in the record hierarchy
    def is_not_playable(self):
        """Return True if this record is marked as nonplayable."""
        np_flag_attr, np_flag_name = self.not_playable_flag
        return getattr(getattr(self, np_flag_attr), np_flag_name)

    def set_playable(self):
        """Set the _not playable flag_ to _False_ - there."""
        np_flag_attr, np_flag_name = self.not_playable_flag
        setattr(getattr(self, np_flag_attr), np_flag_name, False)
