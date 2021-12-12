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
#  Wrye Bash copyright (C) 2005-2009 Wrye, 2010-2021 Wrye Bash Team
#  https://github.com/wrye-bash
#
# =============================================================================
"""Houses abstract base classes and some APIs for representing records and
subrecords in memory."""

from collections import defaultdict
import copy
import io
import zlib

from .basic_elements import SubrecordBlob, unpackSubHeader
from .mod_io import ModReader
from .utils_constants import strFid, _int_unpacker
from .. import bolt, exception
from ..bolt import decoder, struct_pack
from ..bolt import float_or_none, int_or_zero, str_or_none

def _str_to_bool(value, __falsy=frozenset(
    [u'', u'none', u'false', u'no', u'0', u'0.0'])):
    return value.strip().lower() not in __falsy

# Cross game dict, mapping attribute -> csv (de)serializer/csv column header
attr_csv_struct = {
    u'weight': [float_or_none, _(u'Weight')],
    u'rumbleRightMotorStrength': [
        float_or_none, _(u'Rumble - Right Motor Strength')],
    u'criticalDamage': [int_or_zero, _(u'Critical Damage')],
    u'aimArc': [float_or_none, _(u'Aim Arc')],
    u'dr': [int_or_zero, _(u'Damage Resistance')],
    u'duration': [int_or_zero, _(u'Duration')],
    u'attackShotsPerSec': [float_or_none, _(u'Attack Shots Per Second')],
    u'speed': [float_or_none, _(u'Speed')],
    u'semiAutomaticFireDelayMin': [
        float_or_none, _(u'Minumum Semi-Automatic Fire Delay')],
    u'minSpread': [float_or_none, _(u'Minimum Spread')],
    u'minRange': [float_or_none, _(u'Minimum Range')],
    u'baseVatsToHitChance': [int_or_zero, _(u'Base VATS To-Hit Chance')],
    u'clipsize': [int_or_zero, _(u'Clip Size')],
    u'reloadTime': [float_or_none, _(u'Reload Time')],
    u'rumbleDuration': [float_or_none, _(u'Rumble - Duration')],
    u'damage': [int_or_zero, _(u'Damage')],
    u'sightUsage': [float_or_none, _(u'Sight Usage')],
    u'sightFov': [float_or_none, _(u'Sight Fov')],
    u'strengthReq': [int_or_zero, _(u'Strength Requirement')],
    u'fireRate': [float_or_none, _(u'Fire Rate')],
    u'skillReq': [int_or_zero, _(u'Skill Requirement')],
    u'projPerShot': [int_or_zero, _(u'Projectiles Per Shot')],
    u'regenRate': [float_or_none, _(u'Regeneration Rate')],
    u'animationMultiplier': [float_or_none, _(u'Animation Multiplier')],
    u'spread': [float_or_none, _(u'Spread')],
    u'health': [int_or_zero, _(u'Health')],
    u'semiAutomaticFireDelayMax': [
        float_or_none, _(u'Maximum Semi-Automatic Fire Delay')],
    u'rumbleWavelength': [float_or_none, _(u'Rumble - Wavelength')],
    u'vatsSkill': [float_or_none, _(u'VATS Skill')],
    u'vatsDamMult': [float_or_none, _(u'VATS Damage Multiplier')],
    u'projectileCount': [int_or_zero, _(u'Projectile Count')],
    u'limbDmgMult': [float_or_none, _(u'Limb Damage Multiplier')],
    u'killImpulse': [float_or_none, _(u'Kill Impulse')],
    u'reach': [float_or_none, _(u'Reach')],
    u'vatsAp': [float_or_none, _(u'VATS AP')],
    u'clipRounds': [int_or_zero, _(u'Clip Rounds')],
    u'jamTime': [float_or_none, _(u'Jam Time')],
    u'dt': [float_or_none, _(u'Damage Threshold')],
    u'criticalMultiplier': [float_or_none, _(u'Critical Multiplier')],
    u'maxRange': [float_or_none, _(u'Maximum Range')],
    u'rumbleLeftMotorStrength': [
        float_or_none, _(u'Rumble - Left Motor Strength')],
    u'ammoUse': [int_or_zero, _(u'Ammunition Use')],
    u'value': [int_or_zero, _(u'Value')],
    u'eid': [str_or_none, u'EditorID'],
    u'animationAttackMultiplier': [
        float_or_none, _(u'Animation Attack Multiplier')],
    u'overrideActionPoint': [float_or_none, _(u'Override - Action Point')],
    u'impulseDist': [float_or_none, _(u'Impulse Distance')],
    u'overrideDamageToWeaponMult': [
        float_or_none, _(u'Override - Damage To Weapon Multiplier')],
    u'strength': [int_or_zero, _(u'Strength')],
    u'quality': [float_or_none, _(u'Quality')],
    u'enchantPoints': [int_or_zero, _(u'Enchantment Points')],
    u'uses': [int_or_zero, _(u'Uses')],
    u'armorRating': [int_or_zero, _(u'Armor Rating')],
    u'stagger': [float_or_none, _(u'Stagger')],
    u'critDamage': [int_or_zero, _(u'Critical Damage')],
    u'criticalEffect': [int_or_zero, _(u'Critical Effect')],
    # some that are not used in ItemStats
    u'offset': [int_or_zero, _(u'Offset')],
    u'calcMin': [int_or_zero, _(u'CalcMin')],
    u'calcMax': [int_or_zero, _(u'CalcMax')],
    u'full': [str_or_none, _(u'Name')],
    u'model.modPath': [str_or_none, _(u'Model Path')],
    u'model.modb': [float_or_none, _(u'Bound Radius')],
    u'iconPath': [str_or_none, _(u'Icon Path')],
    u'cost': [int_or_zero, _(u'Manual Cost')],
    u'level': [str_or_none, _(u'Level Type')],
    u'spellType': [str_or_none, _(u'Spell Type')],
    u'flags': [int_or_zero, _(u'Spell Flags')],
    u'level_offset': [int_or_zero, _(u'Offset')],
    u'flags.ignoreLOS': [_str_to_bool, _(u'Area Effect Ignores LOS')],
    u'flags.startSpell': [_str_to_bool, _(u'Start Spell')],
    u'flags.disallowAbsorbReflect': [
        _str_to_bool, _(u'Disallow Absorb and Reflect')],
    u'flags.noAutoCalc': [_str_to_bool, _(u'Manual Cost')],
    u'flags.immuneToSilence': [_str_to_bool, _(u'Immune To Silence')],
    u'flags.touchExplodesWOTarget': [
        _str_to_bool, _(u'Touch Explodes Without Target')],
    u'flags.scriptEffectAlwaysApplies': [
        _str_to_bool, _(u'Script Always Applies')],
}

for _k, _v in attr_csv_struct.items():
    if _v[0] is int_or_zero: # should also cover Flags
        _v.append(lambda x: u'"%d"' % x)
    else: # also covers floats which should be wrapped in Rounder (see __str__)
        _v.append(lambda x: u'"%s"' % x)
del _k, _v
attr_csv_struct[u'enchantPoints'][2] = lambda x: ( # can be None
            u'"%d"' % x) if x is not None else u'"None"'

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
        for element in self.elements:
            element.getDefaulters(self.defaulters,'')
            element.getLoaders(self.loaders)
            element.hasFids(self.formElements)
        for sig_candidate in self.loaders:
            if len(sig_candidate) != 4 or not isinstance(sig_candidate, bytes):
                raise SyntaxError(u"Invalid signature '%s': Signatures must "
                                  u'be bytestrings and 4 bytes in '
                                  u'length.' % sig_candidate)

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
            duplicate_slots = sorted(all_slots & element_slots)
            if duplicate_slots:
                raise SyntaxError(
                    u'Duplicate element attributes in record type %s: %s. '
                    u'This most likely points at an attribute collision, make '
                    u'sure to choose unique attribute names!' % (
                        curr_rec_sig, repr(duplicate_slots)))
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
                    u'fid': strFid(record.fid),
                    u'eid': (record.eid + u' ') if getattr(record, u'eid',
                                                           None) else u'',
                })
                for attr in record.__slots__:
                    attr1 = getattr(record, attr, None)
                    if attr1 is not None:
                        bolt.deprint(u'> %s: %r' % (attr, attr1))
                raise

    def mapFids(self,record,mapper,save=False):
        """Maps fids of subelements."""
        for element in self.formElements:
            element.mapFids(record,mapper,save)

    def convertFids(self,record, mapper,toLong):
        """Converts fids between formats according to mapper.
        toLong should be True if converting to long format or False if converting to short format."""
        if record.longFids == toLong: return
        record.fid = mapper(record.fid)
        for element in self.formElements:
            element.mapFids(record,mapper,True)
        record.longFids = toLong
        record.setChanged()

    def updateMasters(self, record, masterset_add):
        """Updates set of master names according to masters actually used."""
        if not record.longFids: raise exception.StateError(
            u'Fids not in long format')
        masterset_add(record.fid)
        for element in self.formElements:
            element.mapFids(record, masterset_add)

    def with_distributor(self, distributor_config):
        # type: (dict) -> MelSet
        """Adds a distributor to this MelSet. See _MelDistributor for more
        information. Convenience method that avoids having to import and
        explicitly construct a _MelDistributor. This is supposed to be chained
        immediately after MelSet.__init__.

        :param distributor_config: The config to pass to the distributor.
        :return: self, for ease of construction."""
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
class MreRecord(object):
    """Generic Record. flags1 are game specific see comments."""
    subtype_attr = {b'EDID': u'eid', b'FULL': u'full', b'MODL': u'model'}
    flags1_ = bolt.Flags(0, bolt.Flags.getNames(
        # {Sky}, {FNV} 0x00000000 ACTI: Collision Geometry (default)
        ( 0,'esm'), # {0x00000001}
        # {Sky}, {FNV} 0x00000004 ARMO: Not playable
        ( 2,'isNotPlayable'), # {0x00000004}
        # {FNV} 0x00000010 ????: Form initialized (Runtime only)
        ( 4,'formInitialized'), # {0x00000010}
        ( 5,'deleted'), # {0x00000020}
        # {Sky}, {FNV} 0x00000040 ACTI: Has Tree LOD
        # {Sky}, {FNV} 0x00000040 REGN: Border Region
        # {Sky}, {FNV} 0x00000040 STAT: Has Tree LOD
        # {Sky}, {FNV} 0x00000040 REFR: Hidden From Local Map
        # {TES4} 0x00000040 ????:  Actor Value
        # Constant HiddenFromLocalMap BorderRegion HasTreeLOD ActorValue
        ( 6,'borderRegion'), # {0x00000040}
        # {Sky} 0x00000080 TES4: Localized
        # {Sky}, {FNV} 0x00000080 PHZD: Turn Off Fire
        # {Sky} 0x00000080 SHOU: Treat Spells as Powers
        # {Sky}, {FNV} 0x00000080 STAT: Add-on LOD Object
        # {TES4} 0x00000080 ????:  Actor Value
        # Localized IsPerch AddOnLODObject TurnOffFire TreatSpellsAsPowers  ActorValue
        ( 7,'turnFireOff'), # {0x00000080}
        ( 7,'hasStrings'), # {0x00000080}
        # {Sky}, {FNV} 0x00000100 ACTI: Must Update Anims
        # {Sky}, {FNV} 0x00000100 REFR: Inaccessible
        # {Sky}, {FNV} 0x00000100 REFR for LIGH: Doesn't light water
        # MustUpdateAnims Inaccessible DoesntLightWater
        ( 8,'inaccessible'), # {0x00000100}
        # {Sky}, {FNV} 0x00000200 ACTI: Local Map - Turns Flag Off, therefore it is Hidden
        # {Sky}, {FNV} 0x00000200 REFR: MotionBlurCastsShadows
        # HiddenFromLocalMap StartsDead MotionBlur CastsShadows
        ( 9,'castsShadows'), # {0x00000200}
        # New Flag for FO4 and SSE used in .esl files
        ( 9, 'eslFile'), # {0x00000200}
        # {Sky}, {FNV} 0x00000400 LSCR: Displays in Main Menu
        # PersistentReference QuestItem DisplaysInMainMenu
        (10,'questItem'), # {0x00000400}
        (10,'persistent'), # {0x00000400}
        (11,'initiallyDisabled'), # {0x00000800}
        (12,'ignored'), # {0x00001000}
        # {FNV} 0x00002000 ????: No Voice Filter
        (13,'noVoiceFilter'), # {0x00002000}
        # {FNV} 0x00004000 STAT: Cannot Save (Runtime only) Ignore VC info
        (14,'cannotSave'), # {0x00004000}
        # {Sky}, {FNV} 0x00008000 STAT: Has Distant LOD
        (15,'visibleWhenDistant'), # {0x00008000}
        # {Sky}, {FNV} 0x00010000 ACTI: Random Animation Start
        # {Sky}, {FNV} 0x00010000 REFR light: Never fades
        # {FNV} 0x00010000 REFR High Priority LOD
        # RandomAnimationStart NeverFades HighPriorityLOD
        (16,'randomAnimationStart'), # {0x00010000}
        # {Sky}, {FNV} 0x00020000 ACTI: Dangerous
        # {Sky}, {FNV} 0x00020000 REFR light: Doesn't light landscape
        # {Sky} 0x00020000 SLGM: Can hold NPC's soul
        # {Sky}, {FNV} 0x00020000 STAT: Use High-Detail LOD Texture
        # {FNV} 0x00020000 STAT: Radio Station (Talking Activator)
        # {FNV} 0x00020000 STAT: Off limits (Interior cell)
        # Dangerous OffLimits DoesntLightLandscape HighDetailLOD CanHoldNPC RadioStation
        (17,'dangerous'), # {0x00020000}
        (18,'compressed'), # {0x00040000}
        # {Sky}, {FNV} 0x00080000 STAT: Has Currents
        # {FNV} 0x00080000 STAT: Platform Specific Texture
        # {FNV} 0x00080000 STAT: Dead
        # CantWait HasCurrents PlatformSpecificTexture Dead
        (19,'cantWait'), # {0x00080000}
        # {Sky}, {FNV} 0x00100000 ACTI: Ignore Object Interaction
        (20,'ignoreObjectInteraction'), # {0x00100000}
        # {???} 0x00200000 ????: Used in Memory Changed Form
        # {Sky}, {FNV} 0x00800000 ACTI: Is Marker
        (23,'isMarker'), # {0x00800000}
        # {FNV} 0x01000000 ????: Destructible (Runtime only)
        (24,'destructible'), # {0x01000000} {FNV}
        # {Sky}, {FNV} 0x02000000 ACTI: Obstacle
        # {Sky}, {FNV} 0x02000000 REFR: No AI Acquire
        (25,'obstacle'), # {0x02000000}
        # {Sky}, {FNV} 0x04000000 ACTI: Filter
        (26,'navMeshFilter'), # {0x04000000}
        # {Sky}, {FNV} 0x08000000 ACTI: Bounding Box
        # NavMesh BoundingBox
        (27,'boundingBox'), # {0x08000000}
        # {Sky}, {FNV} 0x10000000 STAT: Show in World Map
        # {FNV} 0x10000000 STAT: Reflected by Auto Water
        # {FNV} 0x10000000 STAT: Non-Pipboy
        # MustExitToTalk ShowInWorldMap NonPipboy',
        (28,'nonPipboy'), # {0x10000000}
        # {Sky}, {FNV} 0x20000000 ACTI: Child Can Use
        # {Sky}, {FNV} 0x20000000 REFR: Don't Havok Settle
        # {FNV} 0x20000000 REFR: Refracted by Auto Water
        # ChildCanUse DontHavokSettle RefractedbyAutoWater
        (29,'refractedbyAutoWater'), # {0x20000000}
        # {Sky}, {FNV} 0x40000000 ACTI: GROUND
        # {Sky}, {FNV} 0x40000000 REFR: NoRespawn
        # NavMeshGround NoRespawn
        (30,'noRespawn'), # {0x40000000}
        # {Sky}, {FNV} 0x80000000 REFR: MultiBound
        # MultiBound
        (31,'multiBound'), # {0x80000000}
        ))
    __slots__ = [u'header', u'_rec_sig', u'fid', u'flags1', u'size', u'flags2',
                 u'changed', u'data', u'inName', u'longFids']
    isKeyedByEid = False
    #--Set at end of class data definitions.
    type_class = {}
    simpleTypes = set()
    # Maps subrecord signatures to a set of record signatures that can contain
    # those subrecords
    subrec_sig_to_record_sig = defaultdict(set)

    def __init__(self, header, ins=None, do_unpack=False):
        self.header = header
        self._rec_sig = header.recType
        self.fid = header.fid
        self.flags1 = MreRecord.flags1_(header.flags1)
        self.size = header.size
        self.flags2 = header.flags2
        self.longFids = False #--False: Short (numeric); True: Long (espname,objectindex)
        self.changed = False
        self.data = None
        self.inName = ins and ins.inName
        if ins: self.load(ins, do_unpack)

    def __repr__(self):
        return u'<%(eid)s[%(signature)s:%(fid)s]>' % {
            u'signature': self.rec_str,
            u'fid': strFid(self.fid),
            u'eid': (
                (self.eid + u' ') if getattr(self, u'eid', None) else u''),
        }

    def getTypeCopy(self):
        """Returns a type class copy of self"""
        if self.__class__ == MreRecord:
            fullClass = MreRecord.type_class[self._rec_sig]
            myCopy = fullClass(self.header)
            myCopy.data = self.data
            myCopy.load(do_unpack=True)
        else:
            myCopy = copy.deepcopy(self)
        myCopy.changed = True
        myCopy.data = None
        return myCopy

    def mergeFilter(self,modSet):
        """This method is called by the bashed patch mod merger. The intention is
        to allow a record to be filtered according to the specified modSet. E.g.
        for a list record, items coming from mods not in the modSet could be
        removed from the list."""
        pass

    def getDecompressed(self, __unpacker=_int_unpacker):
        """Return self.data, first decompressing it if necessary."""
        if not self.flags1.compressed: return self.data
        decompressed_size, = __unpacker(self.data[:4])
        decomp = zlib.decompress(self.data[4:])
        if len(decomp) != decompressed_size:
            raise exception.ModError(self.inName,
                u'Mis-sized compressed data. Expected %d, got %d.'
                                     % (decompressed_size,len(decomp)))
        return decomp

    def load(self, ins=None, do_unpack=False):
        """Load data from ins stream or internal data buffer."""
        #--Read, but don't analyze.
        if not do_unpack:
            self.data = ins.read(self.size, self._rec_sig)
        #--Unbuffered analysis?
        elif ins and not self.flags1.compressed:
            inPos = ins.tell()
            self.data = ins.read(self.size, self._rec_sig)
            ins.seek(inPos,0,self._rec_sig,u'_REWIND') # _rec_sig,'_REWIND' is just for debug
            self.loadData(ins,inPos+self.size)
        #--Buffered analysis (subclasses only)
        else:
            if ins:
                self.data = ins.read(self.size,self._rec_sig)
            if not self.__class__ == MreRecord:
                with self.getReader() as reader:
                    # Check This
                    if ins and ins.hasStrings: reader.setStringTable(ins.strings)
                    self.loadData(reader,reader.size)
        #--Discard raw data?
        if do_unpack == 2:
            self.data = None
            self.changed = True

    def loadData(self,ins,endPos):
        """Loads data from input stream. Called by load().

        Subclasses should actually read the data, but MreRecord just skips over
        it (assuming that the raw data has already been read to itself. To force
        reading data into an array of subrecords, use iterate_subrecords()."""
        ins.seek(endPos)

    def iterate_subrecords(self, mel_sigs=frozenset()):
        """This is for MreRecord only. Iterates over data unpacking them to
        subrecords - DEPRECATED.

        :type mel_sigs: set"""
        if not self.data: return
        with self.getReader() as reader:
            _rec_sig_ = self._rec_sig
            readAtEnd = reader.atEnd
            while not readAtEnd(reader.size,_rec_sig_):
                subrec = SubrecordBlob(reader, _rec_sig_, mel_sigs)
                if not mel_sigs or subrec.mel_sig in mel_sigs:
                    yield subrec

    def convertFids(self,mapper,toLong):
        """Converts fids between formats according to mapper.
        toLong should be True if converting to long format or False if converting to short format."""
        self.fid = mapper(self.fid)

    def updateMasters(self, masterset_add):
        """Updates set of master names according to masters actually used."""
        raise exception.AbstractError(u'updateMasters called on skipped type '
                                      u'%s' % self.rec_str)

    def setChanged(self,value=True):
        """Sets changed attribute to value. [Default = True.]"""
        self.changed = value

    def getSize(self):
        """Return size of self.data, after, if necessary, packing it."""
        if not self.changed: return self.size
        if self.longFids: raise exception.StateError(
            u'Packing Error: %s %s: Fids in long format.'
            % (self.rec_str, self.fid))
        #--Pack data and return size.
        out = io.BytesIO()
        self.dumpData(out)
        self.data = out.getvalue()
        if self.flags1.compressed:
            dataLen = len(self.data)
            comp = zlib.compress(self.data,6)
            self.data = struct_pack('=I', dataLen) + comp
        self.size = len(self.data)
        self.setChanged(False)
        return self.size

    def dumpData(self,out):
        """Dumps state into data. Called by getSize(). This default version
        just calls subrecords to dump to out."""
        if self.data is None:
            raise exception.StateError(u'Dumping empty record. [%s: %s %08X]' %
                                       (self.inName, self.rec_str, self.fid))
        for subrecord in self.iterate_subrecords():
            subrecord.packSub(out, subrecord.mel_data)

    @property
    def rec_str(self):
        """Decoded record signature - **only** use in exceptions and co."""
        return self._rec_sig.decode(u'ascii')

    def dump(self,out):
        """Dumps all data to output stream."""
        if self.changed:
            raise exception.StateError(
                u'Data changed: %s' % self.rec_str)
        if not self.data and not self.flags1.deleted and self.size > 0:
            raise exception.StateError(u'Data undefined: %s %s' % (
                self.rec_str, hex(self.fid)))
        #--Update the header so it 'packs' correctly
        self.header.size = self.size
        if self._rec_sig != b'GRUP':
            self.header.flags1 = self.flags1
            self.header.fid = self.fid
        out.write(self.header.pack_head())
        if self.size > 0: out.write(self.data)

    def getReader(self):
        """Returns a ModReader wrapped around (decompressed) self.data."""
        return ModReader(self.inName, io.BytesIO(self.getDecompressed()))

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
    melSet = None # type: MelSet
    rec_sig = None # type: bytes
    # If set to False, skip the check for duplicate attributes for this
    # subrecord. See MelSet.check_duplicate_attrs for more information.
    _has_duplicate_attrs = False
    __slots__ = []

    def __init__(self, header, ins=None, do_unpack=False):
        if self.__class__.rec_sig != header.recType:
            raise ValueError(u'Initialize %s with header.recType %s' % (
                type(self), header.recType))
        for element in self.__class__.melSet.elements:
            element.setDefault(self)
        MreRecord.__init__(self, header, ins, do_unpack)

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

    def loadData(self, ins, endPos):
        """Loads data from input stream. Called by load()."""
        loaders = self.__class__.melSet.loaders
        # Load each subrecord
        ins_at_end = ins.atEnd
        while not ins_at_end(endPos, self._rec_sig):
            sub_type, sub_size = unpackSubHeader(ins, self._rec_sig)
            try:
                loaders[sub_type].load_mel(self, ins, sub_type, sub_size,
                    self._rec_sig, sub_type)# *debug_strs
            except KeyError:
                # Wrap this error to make it more understandable
                self.handle_load_error(exception.ModError(ins.inName,
                    u'Unexpected subrecord: %s.%s' % (
                        self.rec_str, sub_type.decode(u'ascii'))),
                    ins, sub_type, sub_size)
            except Exception as error:
                self.handle_load_error(error, ins, sub_type, sub_size)

    def handle_load_error(self, error, ins, sub_type, sub_size):
        eid = getattr(self, u'eid', u'<<NO EID>>')
        bolt.deprint(u'Error loading %r record and/or subrecord: %08X' %
                     (self.rec_str, self.fid))
        bolt.deprint(u'  eid = %r' % eid)
        bolt.deprint(u'  subrecord = %r' % sub_type)
        bolt.deprint(u'  subrecord size = %d' % sub_size)
        bolt.deprint(u'  file pos = %d' % ins.tell(), traceback=True)
        raise exception.ModError(ins.inName, repr(error))

    def dumpData(self,out):
        """Dumps state into out. Called by getSize()."""
        self.__class__.melSet.dumpData(self,out)

    def mapFids(self,mapper,save):
        """Applies mapper to fids of sub-elements. Will replace fid with mapped value if save == True."""
        self.__class__.melSet.mapFids(self,mapper,save)

    def convertFids(self,mapper,toLong):
        """Converts fids between formats according to mapper.
        toLong should be True if converting to long format or False if converting to short format."""
        self.__class__.melSet.convertFids(self,mapper,toLong)

    def updateMasters(self, masterset_add):
        """Updates set of master names according to masters actually used."""
        self.__class__.melSet.updateMasters(self, masterset_add)
