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
"""Menu items for the _item_ menu of the BSAs tab - their window attribute
points to BashFrame.bsaList singleton."""

from .. import archives, bass, balt
from ..balt import ItemLink, Progress
from ..bolt import GPath, SubProgress

__all__ = ['BSA_ExtractToProject', 'BSA_ListContents']

class BSA_ExtractToProject(ItemLink):
    """Extracts one or more BSAs into projects."""
    _text = _(u'Extract to Project(s)...')
    _help = _(u'Extracts the contents of the selected BSA(s) into one or more '
              u'projects, where they can be edited.')

    # TODO(inf) This is almost entirely copy-pasted from
    #  InstallerArchive_Unpack! Should be absorbed by a base class
    def Execute(self):
        selected_bsas = [x for x in self.iselected_infos()]
        if len(selected_bsas) == 1:
            bsa_path = selected_bsas[0].abs_path
            result = self._askText(
                _(u'Extract %s to Project:') % bsa_path.tail,
                default=bsa_path.body.s)
            if not result: return
            # Error checking
            project = GPath(result).tail
            if not project.s or project.cext in archives.readExts:
                self._showWarning(_(u'%s is not a valid project name.') %
                                  result)
                return
            to_unpack = [(project.s, selected_bsas[0])]
        else:
            to_unpack = [(bsa_inf.abs_path.body.s, bsa_inf) for bsa_inf
                         in selected_bsas]
        # More error checking
        # TODO(inf) Maybe create bosh.installers_data singleton?
        for project, _bsa_inf in to_unpack:
            proj_path = bass.dirs[u'installers'].join(project)
            if proj_path.isfile():
                self._showWarning(_(u'%s is a file.') % project)
                return
            if proj_path.isdir():
                if not self._askYes(
                        _(u'%s already exists. Overwrite it?') % project,
                        default=False): return
                # Clear existing project, user wanted to overwrite it
                proj_path.rmtree(safety=u'Installers')
        # All error checking is done, proceed to extract
        with Progress(_(u'Extracting BSAs...')) as prog:
            prog_curr = 0.0
            step_size = 1.0 / len(to_unpack)
            prog_next = prog_curr + step_size
            for project, bsa_inf in to_unpack:
                # Extract every file in the BSA
                # TODO(inf) This loads the BSA twice! Create a dedicated API
                #  method instead
                bsa_inf.extract_assets(
                    bsa_inf.assets, bass.dirs[u'installers'].join(project).s,
                    progress=SubProgress(prog, prog_curr, prog_next))
                prog_curr += step_size
                prog_next += step_size
        self._showOk(_(u'Successfully extracted all selected BSAs. Open the '
                       u'Installers tab to view and manage the created '
                       u'project(s).'),
                     _(u'Extraction Completed'))

class BSA_ListContents(ItemLink):
    """Lists the contents of one or more BSAs."""
    _text = _(u'List Contents...')
    _help = _(u'Lists the contents of each selected BSA and copies it to the '
              u'clipboard.')

    def Execute(self):
        full_text = u'=== Selected BSA Contents:'
        full_text += u'\n[spoiler]'
        for bsa_inf in self.iselected_infos():
            full_text += u'\n\n* %s:\n' % bsa_inf.abs_path.tail
            full_text += u'\n'.join(sorted(bsa_inf.assets))
        full_text += u'\n[/spoiler]'
        balt.copyToClipboard(full_text)
        self._showLog(full_text, _(u'BSA Contents'))
