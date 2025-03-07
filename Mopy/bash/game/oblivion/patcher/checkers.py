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

import copy
import re
from collections import defaultdict
from itertools import chain

from ._shared import ExSpecial, cobl_main
from .... import bush
from ....brec import FormId, RecordType, null4

# Cobl Catalogs ---------------------------------------------------------------
_ingred_alchem = (
    (1, 0xCED, _("Salan's Catalog of Alchemical Ingredients I")),
    (2, 0xCEC, _("Salan's Catalog of Alchemical Ingredients II")),
    (3, 0xCEB, _("Salan's Catalog of Alchemical Ingredients III")),
    (4, 0xCE7, _("Salan's Catalog of Alchemical Ingredients IV")),
)
_effect_alchem = (
    (1, 0xCEA, _("Salan's Catalog of Alchemical Effects I")),
    (2, 0xCE9, _("Salan's Catalog of Alchemical Effects II")),
    (3, 0xCE8, _("Salan's Catalog of Alchemical Effects III")),
    (4, 0xCE6, _("Salan's Catalog of Alchemical Effects IV")),
)
_book_fids = {FormId.from_tuple((cobl_main, book_data[1]))
              for book_data in chain(_ingred_alchem, _effect_alchem)}

class CoblCatalogsPatcher(ExSpecial):
    """Updates COBL alchemical catalogs."""
    patcher_name = _(u'Cobl Catalogs')
    patcher_desc = u'\n\n'.join(
        [_(u"Update COBL's catalogs of alchemical ingredients and effects."),
         _(u'Will only run if Cobl Main.esm is loaded.')])
    _config_key = u'AlchemicalCatalogs'
    _read_sigs = (b'BOOK', b'INGR')
    _filter_in_patch = True

    @classmethod
    def gui_cls_vars(cls):
        cls_vars = super(CoblCatalogsPatcher, cls).gui_cls_vars()
        return cls_vars.update({u'default_isEnabled': True}) or cls_vars

    def __init__(self, p_name, p_file):
        super(CoblCatalogsPatcher, self).__init__(p_name, p_file)
        self.isActive = cobl_main in p_file.load_dict
        self.id_ingred = {}

    @property
    def active_write_sigs(self):
        return (b'BOOK',) if self.isActive else ()

    @property
    def _keep_ids(self):
        return _book_fids

    def scanModFile(self, modFile, progress, scan_sigs=None):
        """Index INGR then add BOOK records to patch file."""
        if ingr_block := modFile.tops.get(b'INGR'):
            for rid, record in ingr_block.iter_present_records():
                #--Ingredient must have name!
                ##: Skips OBME records - rework to support them
                if record.full and record.obme_record_version is None:
                    effects = record.getEffects()
                    if not (b'SEFF', 0) in effects:
                        self.id_ingred[rid] = (record.eid, record.full, effects)
        super().scanModFile(modFile, progress, [b'BOOK'])

    def buildPatch(self,log,progress):
        """Edits patch file as desired. Will write to log."""
        if not self.isActive: return
        #--Setup
        alt_names = copy.deepcopy(self.patchFile.getMgefName())
        attr_or_skill = f"({_('Attribute')}|{_('Skill')})"
        for mgef in alt_names:
            alt_names[mgef] = re.sub(attr_or_skill, u'', alt_names[mgef])
        actorEffects = RecordType.sig_to_class[b'MGEF'].generic_av_effects
        from ..records import actor_values
        keep = self.patchFile.getKeeper()
        patch_books = self.patchFile.tops[b'BOOK']
        def getBook(object_id, full):
            """Helper method for grabbing a BOOK record by object ID and making
            it ready for editing."""
            book_fid = FormId.from_tuple((cobl_main, object_id))
            if book_fid not in patch_books.id_records:
                return None # This shouldn't happen, but just in case...
            book = patch_books.id_records[book_fid]
            book.book_text = '<div align="left"><font face=3 color=4444>'
            book.book_text += full + '\r\n\r\n'
            if keep(book_fid, book):
                return book
        #--Ingredients Catalog
        id_ingred = self.id_ingred
        for (num, objectId, full) in _ingred_alchem:
            book = getBook(objectId, full)
            if book is None: continue
            effs = []
            for eid, eff_full, effects in sorted(id_ingred.values(),
                                                 key=lambda a: a[1].lower()):
                effs.append(eff_full)
                for mgef, actorValue in effects[:num]:
                    effectName = alt_names[mgef]
                    if mgef in actorEffects:
                        effectName += actor_values[actorValue]
                    effs.append(f'  {effectName}')
                effs.append('')
            book.book_text += '\r\n'.join(effs)
            book.book_text = re.sub('\r\n', '<br>\r\n', book.book_text)
        #--Get Ingredients by Effect
        effect_ingred = defaultdict(list)
        for _fid,(eid,full,effects) in id_ingred.items():
            for index,(mgef,actorValue) in enumerate(effects):
                effectName = alt_names[mgef]
                if mgef in actorEffects: effectName += actor_values[actorValue]
                effect_ingred[effectName].append((index,full))
        #--Effect catalogs
        for (num, objectId, full) in _effect_alchem:
            book = getBook(objectId, full)
            if book is None: continue
            effs = []
            for effectName in sorted(effect_ingred):
                effects = [indexFull for indexFull in
                           effect_ingred[effectName] if indexFull[0] < num]
                if effects:
                    effs.append(effectName)
                    for (index, eff_full) in sorted(effects, key=lambda a: a[
                        1].lower()):
                        exSpace = u' ' if index == 0 else u''
                        effs.append(f' {index + 1}{exSpace} {eff_full}')
                    effs.append('')
            book.book_text += '\r\n'.join(effs)
            book.book_text = re.sub('\r\n', '<br>\r\n', book.book_text)
        #--Log
        log.setHeader(u'= ' + self._patcher_name)
        log('* ' + _('Ingredients Cataloged: %(total_changed)d') % {
            'total_changed': len(id_ingred)})
        log('* ' + _('Effects Cataloged: %(total_changed)d') % {
            'total_changed': len(effect_ingred)})

#------------------------------------------------------------------------------
_ob_path = bush.game.master_file
class SEWorldTestsPatcher(ExSpecial):
    """Suspends Cyrodiil quests while in Shivering Isles."""
    patcher_name = _('SEWorld Tests')
    patcher_desc = _("Suspends Cyrodiil quests while in Shivering Isles. "
                     "I.e. re-instates GetPlayerInSEWorld tests as necessary.")
    _config_key = 'SEWorldEnforcer'
    _read_sigs = (b'QUST',)

    @classmethod
    def gui_cls_vars(cls):
        cls_vars = super(SEWorldTestsPatcher, cls).gui_cls_vars()
        return cls_vars.update({u'default_isEnabled': True}) or cls_vars

    def __init__(self, p_name, p_file):
        super(SEWorldTestsPatcher, self).__init__(p_name, p_file)
        self.cyrodiilQuests = set()
        p_file.update_read_factories(self._read_sigs, [_ob_path])

    def initData(self,progress):
        if _ob_path in self.patchFile.load_dict: # read Oblivion quests
            modFile = self.patchFile.get_loaded_mod(_ob_path)
            for rid, record in modFile.tops[b'QUST'].iter_present_records():
                for condition in record.conditions:
                    if condition.ifunc == 365 and condition.compValue == 0:
                        self.cyrodiilQuests.add(rid)
                        break
        self.isActive = bool(self.cyrodiilQuests)

    def scanModFile(self, modFile, progress, scan_sigs=None):
        if modFile.fileInfo.fn_key == _ob_path: return
        super().scanModFile(modFile, progress, scan_sigs)

    @property
    def _keep_ids(self):
        return self.cyrodiilQuests

    def _add_to_patch(self, rid, record, top_sig):  #--365: playerInSeWorld
        return all(condition.ifunc != 365 for condition in record.conditions)

    def buildPatch(self,log,progress):
        """Edits patch file as desired. Will write to log."""
        if not self.isActive: return
        cyrodiilQuests = self.cyrodiilQuests
        keep = self.patchFile.getKeeper()
        patched = []
        for rid, record in self.patchFile.tops[b'QUST'].id_records.items():
            if rid not in cyrodiilQuests: continue
            for condition in record.conditions:
                if condition.ifunc == 365: break #--365: playerInSeWorld
            else:
                condition = record.get_mel_object_for_group('conditions')
                condition.ifunc = 365
                # Set parameters etc. needed for this function (no parameters
                # and a float comparison value)
                condition.param2 = condition.param1 = null4
                condition.compValue = 0.0
                record.conditions.insert(0, condition)
                if keep(rid, record):
                    patched.append(record.eid)
        log.setHeader(f'= {self._patcher_name}')
        log('===' + _('Quests Patched: %(total_changed)d') % {
            'total_changed': len(patched)})
