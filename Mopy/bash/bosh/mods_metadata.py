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
#  Wrye Bash copyright (C) 2005-2009 Wrye, 2010-2019 Wrye Bash Team
#  https://github.com/wrye-bash
#
# =============================================================================
import errno
import os
import re

from ._mergeability import is_esl_capable
from .. import balt, bolt, bush, bass, load_order
from ..bolt import GPath, deprint, sio, struct_pack, struct_unpack
from ..brec import ModReader, MreRecord
from ..cint import ObBaseRecord, ObCollection
from ..exception import BoltError, CancelError, ModError
from ..patcher import getPatchesPath, getPatchesList

try:
    import loot_api
except ImportError as e:
    loot_api = None
    deprint(u'Failed to import the loot_api module: ({})'.format(e))

lootDb = None #--LootDb singleton

# Mod Config Help -------------------------------------------------------------
#------------------------------------------------------------------------------
class ModRuleSet:
    """A set of rules to be used in analyzing active and/or merged mods for errors."""

    class ModGroup:
        """A set of specific mods and rules that affect them."""
        def __init__(self):
            self.modAnds = []
            self.modNots = []
            self.notes = ''
            self.config = []
            self.suggest = []
            self.warn = []

        def hasRules(self):
            return bool(self.notes or self.config or self.suggest or self.warn)

        def isActive(self,actives):
            """Determines if modgroup is active based on its set of mods."""
            if not self.modAnds: return False
            for modNot,mods in zip(self.modNots,self.modAnds):
                if modNot:
                    for mod in mods:
                        if mod in actives: return False
                else:
                    for mod in mods:
                        if mod in actives: break
                    else: return False
            return True

        def getActives(self,actives):
            """Returns list of active mods."""
            out = []
            for modNot,mods in zip(self.modNots,self.modAnds):
                for mod in mods:
                    if mod in actives:
                        out.append(mod)
            return out

    class RuleParser:
        """A class for parsing ruleset files."""
        ruleBlockIds = (u'NOTES',u'CONFIG',u'SUGGEST',u'WARN')
        reComment = re.compile(u'##.*', re.U)
        reBlock   = re.compile(ur'^>>\s+([A-Z]+)\s*(.*)',re.U)
        reRule    = re.compile(ur'^(x|o|\+|-|-\+)\s+([^/]+)\s*(\[[^\]]+\])?\s*//(.*)',re.U)
        reExists  = re.compile(ur'^(e)\s+([^/]+)//(.*)',re.U)
        reMod = reModVersion = None

        def __init__(self,ruleSet):
            if self.__class__.reMod is None: # bush.game must have been set
                espmls = u'|'.join(map(re.escape, bush.game.espm_extensions))
                self.__class__.reMod = re.compile(
                    ur'\s*([\-|]?)(.+?(' + espmls + ur'))(\s*\[[^\]]\])?',
                    re.I | re.U)
                self.__class__.reModVersion = re.compile(
                    u'(.+(' + espmls + ur'))\s*(\[[^\]]+\])?', re.I | re.U)
            self.ruleSet = ruleSet
            #--Temp storage while parsing.
            self.assumed = []
            self.assumedNot = []
            self.curBlockId = None
            self.curDefineId = None
            self.mods = []
            self.modNots = []
            self.group = ModRuleSet.ModGroup()
            self.define = None

        def newBlock(self,newBlock=None):
            """Handle new blocks, finishing current block if present."""
            #--Subblock of IF block?
            if newBlock in self.ruleBlockIds:
                self.curBlockId = newBlock
                return
            curBlockId = self.curBlockId
            group = self.group
            if curBlockId is not None:
                if curBlockId == u'HEADER':
                    self.ruleSet.header = self.ruleSet.header.rstrip()
                elif curBlockId == u'ONLYONE':
                    self.ruleSet.onlyones.append(set(self.mods))
                elif curBlockId == u'ASSUME':
                    self.assumed = self.mods[:]
                    self.assumedNot = self.modNots[:]
                elif curBlockId in self.ruleBlockIds and self.mods and group.hasRules():
                    group.notes = group.notes.rstrip()
                    group.modAnds = self.assumed + self.mods
                    group.modNots = self.assumedNot + self.modNots
                    self.ruleSet.modGroups.append(group)
            self.curBlockId = newBlock
            self.curDefineId = None
            del self.mods[:]
            del self.modNots[:]
            self.group = ModRuleSet.ModGroup()

        def addGroupRule(self,op,mod,comment):
            """Adds a new rule to the modGroup."""
            maModVersion = self.reModVersion.match(mod)
            if not maModVersion: return
            getattr(self.group,self.curBlockId.lower()).append((op,GPath(maModVersion.group(1)),comment))

        def parse(self,rulePath):
            """Parse supplied ruleset."""
            #--Constants
            reComment = self.reComment
            reBlock   = self.reBlock
            reMod     = self.reMod
            reRule    = self.reRule
            reExists  = self.reExists
            reModVersion = self.reModVersion
            ruleSet   = self.ruleSet

            #--Clear info
            ruleSet.mtime = rulePath.mtime
            ruleSet.header = u''
            del ruleSet.onlyones[:]
            del ruleSet.modGroups[:]

            def stripped(list):
                return [(x or u'').strip() for x in list]

            with rulePath.open('r',encoding='utf-8-sig') as ins:
                for line in ins:
                    line = reComment.sub(u'',line)
                    maBlock = reBlock.match(line)
                    #--Block changers
                    if maBlock:
                        newBlock,more = stripped(maBlock.groups())
                        self.newBlock(newBlock)
                        if newBlock == u'HEADER':
                            self.ruleSet.header = (more or u'')+u'\n'
                        elif newBlock in (u'ASSUME',u'IF'):
                            maModVersion = more and reModVersion.match(more)
                            if maModVersion:
                                self.mods = [[GPath(maModVersion.group(1))]]
                                self.modNots = [False]
                            else:
                                self.mods = []
                                self.modNots = []
                    #--Block lists
                    elif self.curBlockId == u'HEADER':
                        self.ruleSet.header += line.rstrip()+u'\n'
                    elif self.curBlockId in (u'IF',u'ASSUME'):
                        maMod = reMod.match(line)
                        if maMod:
                            op,mod,version = stripped(maMod.groups())
                            mod = GPath(mod)
                            if op == u'|':
                                self.mods[-1].append(mod)
                            else:
                                self.mods.append([mod])
                                self.modNots.append(op == u'-')
                    elif self.curBlockId  == u'ONLYONE':
                        maMod = reMod.match(line)
                        if maMod:
                            if maMod.group(1): raise BoltError(
                                u"ONLYONE does not support %s operators." % maMod.group(1))
                            self.mods.append(GPath(maMod.group(2)))
                    elif self.curBlockId == u'NOTES':
                        self.group.notes += line.rstrip()+u'\n'
                    elif self.curBlockId in self.ruleBlockIds:
                        maRule = reRule.match(line)
                        maExists = reExists.match(line)
                        if maRule:
                            op,mod,version,text = maRule.groups()
                            self.addGroupRule(op,mod,text)
                        elif maExists and u'..' not in maExists.groups(2):
                            self.addGroupRule(*stripped(maExists.groups()))
                self.newBlock(None)

    #--------------------------------------------------------------------------
    def __init__(self):
        """Initialize ModRuleSet."""
        self.mtime = 0
        self.header = u''
        self.defineKeys = []
        self.onlyones = []
        self.modGroups = []

#------------------------------------------------------------------------------
class ConfigHelpers:
    """Encapsulates info from mod configuration helper files (LOOT masterlist, etc.)"""

    def __init__(self):
        """bass.dir must have been initialized"""
        global lootDb
        if loot_api is not None:
            deprint(u'Using LOOT API version:', loot_api.Version.string())
            try:
                gameType = self.getLootApiGameType(bush.game.fsName)
                loot_api.initialise_locale('')
                loot_game = loot_api.create_game_handle(gameType, bass.dirs['app'].s)
                lootDb = loot_game.get_database()
            except (OSError, AttributeError):
                deprint(u'The LOOT API failed to initialize', traceback=True)
                lootDb = None
            except ValueError:
                deprint(u'The LOOT API does not support the current game.')
                lootDb = None
            except RuntimeError:
                deprint(u'Failed to create a LOOT API database.')
                lootDb = None
        else:
            lootDb = None
        # LOOT stores the masterlist/userlist in a %LOCALAPPDATA% subdirectory.
        self.lootMasterPath = bass.dirs['userApp'].join(
            os.pardir, u'LOOT', bush.game.fsName, u'masterlist.yaml')
        self.lootUserPath = bass.dirs['userApp'].join(
            os.pardir, u'LOOT', bush.game.fsName, u'userlist.yaml')
        self.lootMasterTime = None
        self.lootUserTime = None
        self.tagList = bass.dirs['defaultPatches'].join(u'taglist.yaml')
        self.tagListModTime = None
        #--Bash Tags
        self.tagCache = {}
        #--Mod Rules
        self.name_ruleSet = {}
        #--Refresh
        self.refreshBashTags()

    def refreshBashTags(self):
        """Reloads tag info if file dates have changed."""
        if lootDb is None: return
        path, userpath = self.lootMasterPath, self.lootUserPath
        #--Masterlist is present, use it
        if path.exists():
            if (path.mtime != self.lootMasterTime or
                (userpath.exists() and userpath.mtime != self.lootUserTime)):
                self.tagCache = {}
                self.lootMasterTime = path.mtime
                parsing = u'', u'%s' % path
                # noinspection PyBroadException
                try:
                    if userpath.exists():
                        parsing = u's', u'%s, %s' % (path, userpath)
                        self.lootUserTime = userpath.mtime
                        lootDb.load_lists(path.s,userpath.s)
                    else:
                        lootDb.load_lists(path.s)
                    return # we are done
                # unfortunately the pyd file throws generic Exception - see
                # http://pybind11.readthedocs.io/en/latest/advanced/exceptions.html#built-in-exception-translation
                except Exception:
                    deprint(u'An error occurred while parsing file%s %s:'
                            % parsing, traceback=True)
        #--No masterlist or an error occurred while reading it, use the taglist
        if not self.tagList.exists():
            raise BoltError(u'Mopy\\Bash Patches\\' + bush.game.fsName +
                u'\\taglist.yaml could not be found.  Please ensure Wrye '
                u'Bash is installed correctly.')
        if self.tagList.mtime == self.tagListModTime: return
        self.tagListModTime = self.tagList.mtime
        # noinspection PyBroadException
        try:
            self.tagCache = {}
            lootDb.load_lists(self.tagList.s)
        except Exception:
            deprint(u'An error occurred while parsing taglist.yaml:',
                    traceback=True)

    def getTagsInfoCache(self, modName):
        """Gets Bash tag info from the cache, or
           the LOOT API if it is not in cache."""
        if modName not in self.tagCache:
            if lootDb is None:
                tags = (set(), set(), set())
            else:
                tags = lootDb.get_plugin_tags(modName.s, True)
                tags = (tags.added, tags.removed, tags.userlist_modified)
            self.tagCache[modName] = tags
            return tags
        else:
            return self.tagCache[modName]

    @staticmethod
    def getLootApiGameType(fsName):
        if loot_api is None:
            return None
        if fsName == 'Oblivion':
            return loot_api.GameType.tes4
        # TODO See if LOOT adds a new GameType for Enderal
        elif fsName in ('Enderal', 'Skyrim'):
            return loot_api.GameType.tes5
        elif fsName == 'Skyrim Special Edition':
            return loot_api.GameType.tes5se
        elif fsName == 'Fallout3':
            return loot_api.GameType.fo3
        elif fsName == 'FalloutNV':
            return loot_api.GameType.fonv
        elif fsName == 'Fallout4':
            return loot_api.GameType.fo4
        else:
            return None

    @staticmethod
    def getDirtyMessage(modName):
        if lootDb is None:
            return False, u''
        if lootDb.get_plugin_cleanliness(modName.s, True) == loot_api.PluginCleanliness.dirty:
            return True, 'Contains dirty edits, needs cleaning.'
        else:
            return False, ''

    # BashTags dir ------------------------------------------------------------
    def get_tags_from_dir(self, plugin_name):
        """Retrieves a tuple containing a set of added and a set of deleted
        tags from the 'Data/BashTags/PLUGIN_NAME.txt' file, if it is
        present.

        :param plugin_name: The name of the plugin to check the tag file for.
        :return: A tuple containing two sets of added and deleted tags."""
        # Check if the file even exists first
        tag_files_dir = bass.dirs['tag_files']
        tag_file = tag_files_dir.join(plugin_name.body + u'.txt')
        if not tag_file.isfile(): return set(), set()
        removed, added = set(), set()
        with tag_file.open('r') as ins:
            for tag_line in ins:
                # Strip out comments and skip lines that are empty as a result
                tag_line = tag_line.split(u'#')[0].strip()
                if not tag_line: continue
                for tag_entry in tag_line.split(u','):
                    # Guard against things (e.g. typos) like 'TagA,,TagB'
                    if not tag_entry: continue
                    tag_entry = tag_entry.strip()
                    # If it starts with a minus, it's removing a tag
                    if tag_entry[0] == u'-':
                        # Guard against a typo like '- C.Water'
                        removed.add(tag_entry[1:].strip())
                    else:
                        added.add(tag_entry)
        return added, removed

    def save_tags_to_dir(self, plugin_name, plugin_tags, plugin_old_tags):
        """Compares plugin_tags to plugin_old_tags and saves the diff to
        Data/BashTags/PLUGIN_NAME.txt.

        :param plugin_name: The name of the plugin to modify the tag file for.
        :param plugin_tags: A set of all Bash Tags currently applied to the
            plugin in question.
        :param plugin_base_tags: A set of all Bash Tags applied to the plugin
            by its description and the LOOT masterlist / userlist."""
        tag_files_dir = bass.dirs['tag_files']
        tag_files_dir.makedirs()
        tag_file = tag_files_dir.join(plugin_name.body + u'.txt')
        # Calculate the diff and ignore the minus when sorting the result
        diff_tags = sorted(plugin_tags - plugin_old_tags |
                           {u'-' + t for t in plugin_old_tags - plugin_tags},
                           key=lambda t: t[1:] if t[0] == u'-' else t)
        with tag_file.open('w') as out:
            # Stick a header in there to indicate that it's machine-generated
            # Also print the version, which could be helpful
            out.write(u'# Generated by Wrye Bash %s\n' % bass.AppVersion)
            out.write(u', '.join(diff_tags) + u'\n')

    #--Mod Checker ------------------------------------------------------------
    def refreshRuleSets(self):
        """Reloads ruleSets if file dates have changed."""
        name_ruleSet = self.name_ruleSet
        reRulesFile = re.compile(u'Rules.txt$',re.I|re.U)
        ruleFiles = set(x for x in getPatchesList() if reRulesFile.search(x.s))
        for name in name_ruleSet.keys():
            if name not in ruleFiles: del name_ruleSet[name]
        for name in ruleFiles:
            path = getPatchesPath(name)
            ruleSet = name_ruleSet.get(name)
            if not ruleSet:
                ruleSet = name_ruleSet[name] = ModRuleSet()
            if path.mtime != ruleSet.mtime:
                ModRuleSet.RuleParser(ruleSet).parse(path)

    _cleaning_wiki_url = u'[[!https://tes5edit.github.io/docs/5-mod-cleaning' \
                         u'-and-error-checking.html|Tome of xEdit]]'

    def checkMods(self, showModList=False, showRuleSets=False, showNotes=False,
                  showConfig=True, showSuggest=True, showCRC=False,
                  showVersion=True, showWarn=True, mod_checker=None):
        """Checks currently loaded mods against ruleset.
           mod_checker should be the instance of ModChecker, to scan."""
        from . import modInfos
        active = set(load_order.cached_active_tuple())
        merged_ = modInfos.merged
        imported_ = modInfos.imported
        activeMerged = active | merged_
        removeEslFlag = set()
        warning = u'=== <font color=red>'+_(u'WARNING:')+u'</font> '
        #--Header
        with sio() as out:
            log = bolt.LogFile(out)
            log.setHeader(u'= '+_(u'Check Mods'),True)
            if bush.game.check_esl:
                log(_(u'This is a report on your currently installed or '
                      u'active mods.'))
            else:
                log(_(u'This is a report on your currently installed, active, '
                      u'or merged mods.'))
            #--Mergeable/NoMerge/Deactivate tagged mods
            if bush.game.check_esl:
                shouldMerge = modInfos.mergeable
            else:
                shouldMerge = active & modInfos.mergeable
            if bush.game.check_esl:
                for m, modinf in modInfos.items():
                    if not modinf.is_esl():
                        continue # we check .esl extension and ESL flagged mods
                    if not is_esl_capable(modinf, modInfos, reasons=None):
                        removeEslFlag.add(m)
            shouldDeactivateA, shouldDeactivateB = [], []
            for x in active:
                tags = modInfos[x].getBashTags()
                if u'Deactivate' in tags: shouldDeactivateA.append(x)
                if u'NoMerge' in tags and x in modInfos.mergeable:
                    shouldDeactivateB.append(x)
            shouldActivateA = [x for x in imported_ if x not in active and
                        u'MustBeActiveIfImported' in modInfos[x].getBashTags()]
            #--Mods with invalid TES4 version
            invalidVersion = [(x,unicode(round(modInfos[x].header.version,6))) for x in active if round(modInfos[x].header.version,6) not in bush.game.esp.validHeaderVersions]
            #--Look for dirty edits
            shouldClean = {}
            scan = []
            dirty_msgs = [(x, modInfos.getDirtyMessage(x)) for x in active]
            for x, y in dirty_msgs:
                if y[0]:
                    shouldClean[x] = y[1]
                elif mod_checker:
                    scan.append(modInfos[x])
            if mod_checker:
                try:
                    with balt.Progress(_(u'Scanning for Dirty Edits...'),u'\n'+u' '*60, parent=mod_checker, abort=True) as progress:
                        ret = ModCleaner.scan_Many(scan,ModCleaner.ITM|ModCleaner.UDR,progress)
                        for i,mod in enumerate(scan):
                            udrs,itms,fog = ret[i]
                            if mod.name == GPath(u'Unofficial Oblivion Patch.esp'): itms.discard((GPath(u'Oblivion.esm'),0x00AA3C))
                            if mod.isBP(): itms = set()
                            if udrs or itms:
                                cleanMsg = []
                                if udrs:
                                    cleanMsg.append(u'UDR(%i)' % len(udrs))
                                if itms:
                                    cleanMsg.append(u'ITM(%i)' % len(itms))
                                cleanMsg = u', '.join(cleanMsg)
                                shouldClean[mod.name] = cleanMsg
                except CancelError:
                    pass
            # below is always empty with current implementation
            shouldCleanMaybe = [(x, y[1]) for x, y in dirty_msgs if
                                not y[0] and y[1] != u'']
            for mod in tuple(shouldMerge):
                if u'NoMerge' in modInfos[mod].getBashTags():
                    shouldMerge.discard(mod)
            if shouldMerge:
                if bush.game.check_esl:
                    log.setHeader(u'=== '+_(u'ESL Capable'))
                    log(_(u'Following mods could be assigned an ESL flag but '
                          u'are not ESL flagged.'))
                else:
                    log.setHeader(u'=== ' + _(u'Mergeable'))
                    log(_(u'Following mods are active, but could be merged into '
                          u'the bashed patch.'))
                for mod in sorted(shouldMerge):
                    log(u'* __'+mod.s+u'__')
            if removeEslFlag:
                log.setHeader(u'=== ' + _(u'Potentially Incorrect ESL Flag'))
                log(_(u'Following mods have an ESL flag, but may not qualify. '
                      u'Run \'Check ESL Qualifications\' on them and/or check '
                      u'them with xEdit to be sure.'))
                for mod in sorted(removeEslFlag):
                    log(u'* __' + mod.s + u'__')
            if shouldDeactivateB:
                log.setHeader(u'=== '+_(u'NoMerge Tagged Mods'))
                log(_(u'Following mods are tagged NoMerge and should be '
                      u'deactivated and imported into the bashed patch but '
                      u'are currently active.'))
                for mod in sorted(shouldDeactivateB):
                    log(u'* __'+mod.s+u'__')
            if shouldDeactivateA:
                log.setHeader(u'=== '+_(u'Deactivate Tagged Mods'))
                log(_(u'Following mods are tagged Deactivate and should be '
                      u'deactivated and imported into the bashed patch but '
                      u'are currently active.'))
                for mod in sorted(shouldDeactivateA):
                    log(u'* __'+mod.s+u'__')
            if shouldActivateA:
                log.setHeader(u'=== '+_(u'MustBeActiveIfImported Tagged Mods'))
                log(_(u'Following mods to work correctly have to be active as '
                      u'well as imported into the bashed patch but are '
                      u'currently only imported.'))
                for mod in sorted(shouldActivateA):
                    log(u'* __'+mod.s+u'__')
            if shouldClean:
                log.setHeader(
                    u'=== ' + _(u'Mods that need cleaning with TES4Edit'))
                log(_(u'Following mods have identical to master (ITM) records,'
                      u' deleted records (UDR), or other issues that should be'
                      u' fixed with TES4Edit.  Visit the %(cleaning_wiki_url)s'
                      u' for more information.') % {
                        'cleaning_wiki_url': self._cleaning_wiki_url})
                for mod in sorted(shouldClean.keys()):
                    log(u'* __'+mod.s+u':__  %s' % shouldClean[mod])
            if shouldCleanMaybe:
                log.setHeader(
                    u'=== ' + _(u'Mods with special cleaning instructions'))
                log(_(u'Following mods have special instructions for cleaning '
                      u'with TES4Edit'))
                for mod in sorted(shouldCleanMaybe):
                    log(u'* __'+mod[0].s+u':__  '+mod[1])
            elif mod_checker and not shouldClean:
                log.setHeader(
                    u'=== ' + _(u'Mods that need cleaning with TES4Edit'))
                log(_(u'Congratulations all mods appear clean.'))
            if invalidVersion:
                ver_list = u', '.join(
                    sorted(bush.game.esp.validHeaderVersions))
                log.setHeader(
                    u'=== ' + _(u'Mods with non standard TES4 versions'))
                log(_(u"Following mods have a TES4 version that isn't "
                      u"recognized as (one of) the standard version(s) "
                      u"(%s).  It is untested what effect this can have on "
                      u"%s.") % (ver_list, bush.game.displayName))
                for mod in sorted(invalidVersion):
                    log(u'* __'+mod[0].s+u':__  '+mod[1])
            #--Missing/Delinquent Masters
            if showModList:
                log(u'\n'+modInfos.getModList(showCRC,showVersion,wtxt=True).strip())
            else:
                log.setHeader(warning+_(u'Missing/Delinquent Masters'))
                previousMods = set()
                for mod in load_order.cached_active_tuple():
                    loggedMod = False
                    for master in modInfos[mod].get_masters():
                        if master not in active:
                            label = _(u'MISSING')
                        elif master not in previousMods:
                            label = _(u'DELINQUENT')
                        else:
                            label = u''
                        if label:
                            if not loggedMod:
                                log(u'* '+mod.s)
                                loggedMod = True
                            log(u'  * __%s__ %s' %(label,master.s))
                    previousMods.add(mod)
            #--Rule Sets
            if showRuleSets:
                self.refreshRuleSets()
                for fileName in sorted(self.name_ruleSet):
                    ruleSet = self.name_ruleSet[fileName]
                    modRules = ruleSet.modGroups
                    log.setHeader(u'= ' + fileName.s[:-4],True)
                    if ruleSet.header: log(ruleSet.header)
                    #--One ofs
                    for modSet in ruleSet.onlyones:
                        modSet &= activeMerged
                        if len(modSet) > 1:
                            log.setHeader(warning+_(u'Only one of these should be active/merged'))
                            for mod in sorted(modSet):
                                log(u'* '+mod.s)
                    #--Mod Rules
                    for modGroup in ruleSet.modGroups:
                        if not modGroup.isActive(activeMerged): continue
                        modsList = u' + '.join([x.s for x in modGroup.getActives(activeMerged)])
                        if showNotes and modGroup.notes:
                            log.setHeader(u'=== '+_(u'NOTES: ') + modsList )
                            log(modGroup.notes)
                        if showConfig:
                            log.setHeader(u'=== '+_(u'CONFIGURATION: ') + modsList )
                            #    + _(u'\nLegend: x: Active, +: Merged, -: Inactive'))
                            for ruleType,ruleMod,comment in modGroup.config:
                                if ruleType != u'o': continue
                                if ruleMod in active: bullet = u'x'
                                elif ruleMod in merged_: bullet = u'+'
                                elif ruleMod in imported_: bullet = u'*'
                                else: bullet = u'o'
                                log(u'%s __%s__ -- %s' % (bullet,ruleMod.s,comment))
                        if showSuggest:
                            log.setHeader(u'=== '+_(u'SUGGESTIONS: ') + modsList)
                            for ruleType,ruleMod,comment in modGroup.suggest:
                                if ((ruleType == u'x' and ruleMod not in activeMerged) or
                                    (ruleType == u'+' and (ruleMod in active or ruleMod not in merged_)) or
                                    (ruleType == u'-' and ruleMod in activeMerged) or
                                    (ruleType == u'-+' and ruleMod in active)
                                    ):
                                    log(u'* __%s__ -- %s' % (ruleMod.s,comment))
                                elif ruleType == u'e' and not bass.dirs['mods'].join(ruleMod).exists():
                                    log(u'* '+comment)
                        if showWarn:
                            log.setHeader(warning + modsList)
                            for ruleType,ruleMod,comment in modGroup.warn:
                                if ((ruleType == u'x' and ruleMod not in activeMerged) or
                                    (ruleType == u'+' and (ruleMod in active or ruleMod not in merged_)) or
                                    (ruleType == u'-' and ruleMod in activeMerged) or
                                    (ruleType == u'-+' and ruleMod in active)
                                    ):
                                    log(u'* __%s__ -- %s' % (ruleMod.s,comment))
                                elif ruleType == u'e' and not bass.dirs['mods'].join(ruleMod).exists():
                                    log(u'* '+comment)
            return log.out.getvalue()

#------------------------------------------------------------------------------
class ModCleaner:
    """Class for cleaning ITM and UDR edits from mods.
       ITM detection requires CBash to work."""
    UDR     = 0x01  # Deleted references
    ITM     = 0x02  # Identical to master records
    FOG     = 0x04  # Nvidia Fog Fix
    ALL = UDR|ITM|FOG
    DEFAULT = UDR|ITM

    class UdrInfo(object):
        # UDR info
        # (UDR fid, UDR Type, UDR Parent Fid, UDR Parent Type, UDR Parent Parent Fid, UDR Parent Block, UDR Paren SubBlock)
        def __init__(self,fid,Type=None,parentFid=None,parentEid=u'',
                     parentType=None,parentParentFid=None,parentParentEid=u'',
                     pos=None):
            if isinstance(fid,ObBaseRecord):
                # CBash - passed in the record instance
                record = fid
                parent = record.Parent
                self.fid = record.fid
                self.type = record._Type
                self.parentFid = parent.fid
                self.parentEid = parent.eid
                if parent.IsInterior:
                    self.parentType = 0
                    self.parentParentFid = None
                    self.parentParentEid = u''
                    self.pos = None
                else:
                    self.parentType = 1
                    self.parentParentFid = parent.Parent.fid
                    self.parentParentEid = parent.Parent.eid
                    self.pos = (record.posX,record.posY)
            else:
                self.fid = fid
                self.type = Type
                self.parentFid = parentFid
                self.parentEid = parentEid
                self.parentType = parentType
                self.pos = pos
                self.parentParentFid = parentParentFid
                self.parentParentEid = parentParentEid

        def __cmp__(self,other):
            return cmp(self.fid,other.fid)

    def __init__(self,modInfo):
        self.modInfo = modInfo
        self.itm = set()    # Fids for Identical To Master records
        self.udr = set()    # Fids for Deleted Reference records
        self.fog = set()    # Fids for Cells needing the Nvidia Fog Fix

    def scan(self,what=ALL,progress=bolt.Progress(),detailed=False):
        """Scan this mod for dirty edits.
           return (UDR,ITM,FogFix)"""
        udr,itm,fog = ModCleaner.scan_Many([self.modInfo],what,progress,detailed)[0]
        if what & ModCleaner.UDR:
            self.udr = udr
        if what & ModCleaner.ITM:
            self.itm = itm
        if what & ModCleaner.FOG:
            self.fog = fog
        return udr,itm,fog

    @staticmethod
    def scan_Many(modInfos,what=DEFAULT,progress=bolt.Progress(),detailed=False):
        """Scan multiple mods for dirty edits"""
        if len(modInfos) == 0: return []
        if not bass.settings['bash.CBashEnabled']:
            return ModCleaner._scan_Python(modInfos,what,progress,detailed)
        else:
            return ModCleaner._scan_CBash(modInfos,what,progress)

    def clean(self,what=UDR|FOG,progress=bolt.Progress(),reScan=False):
        """reScan:
             True: perform scans before cleaning
             False: only perform scans if itm/udr is empty
             """
        ModCleaner.clean_Many([self],what,progress,reScan)

    @staticmethod
    def clean_Many(cleaners,what,progress=bolt.Progress(),reScan=False):
        """Accepts either a list of ModInfo's or a list of ModCleaner's"""
        from . import ModInfos
        if isinstance(cleaners[0],ModInfos):
            reScan = True
            cleaners = [ModCleaner(x) for x in cleaners]
        if bass.settings['bash.CBashEnabled']:
            #--CBash
            #--Scan?
            if reScan:
                ret = ModCleaner._scan_CBash([x.modInfo for x in cleaners],what,progress)
                for i,cleaner in enumerate(cleaners):
                    udr,itm,fog = ret[i]
                    if what & ModCleaner.UDR:
                        cleaner.udr = udr
                    if what & ModCleaner.ITM:
                        cleaner.itm = itm
                    if what & ModCleaner.FOG:
                        cleaner.fog = fog
            #--Clean
            ModCleaner._clean_CBash(cleaners,what,progress)
        else:
            ModCleaner._clean_Python(cleaners,what,progress)

    @staticmethod
    def _scan_CBash(modInfos,what,progress):
        """Scan multiple mods for problems"""
        if not (what & ModCleaner.ALL):
            return [(set(),set(),set())] * len(modInfos)
        # There are scans to do
        doUDR = bool(what & ModCleaner.UDR)
        doITM = bool(what & ModCleaner.ITM)
        doFog = bool(what & ModCleaner.FOG)
        # If there are more than 255 mods, we have to break it up into
        # smaller groups.  We'll do groups of 200 for now, to allow for
        # added files due to implicitly loading masters.
        modInfos = [x.modInfo if isinstance(x,ModCleaner) else x for x in modInfos]
        numMods = len(modInfos)
        if numMods > 255:
            ModsPerGroup = 200
            numGroups = numMods / ModsPerGroup
            if numMods % ModsPerGroup:
                numGroups += 1
        else:
            ModsPerGroup = 255
            numGroups = 1
        progress.setFull(numGroups)
        ret = []
        for i in range(numGroups):
            #--Load
            progress(i,_(u'Loading...'))
            groupModInfos = modInfos[i*ModsPerGroup:(i+1)*ModsPerGroup]
            with ObCollection(ModsPath=bass.dirs['mods'].s) as Current:
                for mod in groupModInfos:
                    if len(mod.masterNames) == 0: continue
                    path = mod.getPath()
                    Current.addMod(path.stail)
                Current.load()
                #--Scan
                subprogress1 = bolt.SubProgress(progress,i,i+1)
                subprogress1.setFull(max(len(groupModInfos),1))
                for j,modInfo in enumerate(groupModInfos):
                    subprogress1(j,_(u'Scanning...') + u'\n' + modInfo.name.s)
                    udr = set()
                    itm = set()
                    fog = set()
                    if len(modInfo.masterNames) > 0:
                        path = modInfo.getPath()
                        modFile = Current.LookupModFile(path.stail)
                        if modFile:
                            udrRecords = []
                            fogRecords = []
                            if doUDR:
                                udrRecords += modFile.ACRES + modFile.ACHRS + modFile.REFRS
                            if doFog:
                                fogRecords += modFile.CELL
                            if doITM:
                                itm |= set([x.fid for x in modFile.GetRecordsIdenticalToMaster()])
                            total = len(udrRecords) + len(fogRecords)
                            subprogress2 = bolt.SubProgress(subprogress1,j,j+1)
                            subprogress2.setFull(max(total,1))
                            #--Scan UDR
                            for record in udrRecords:
                                subprogress2.plus()
                                if record.IsDeleted:
                                    udr.add(ModCleaner.UdrInfo(record))
                            #--Scan fog
                            for record in fogRecords:
                                subprogress2.plus()
                                if not (record.fogNear or record.fogFar or record.fogClip):
                                    fog.add(record.fid)
                            modFile.Unload()
                    ret.append((udr,itm,fog))
        return ret

    @staticmethod
    def _scan_Python(modInfos,what,progress,detailed=False):
        if not (what & (ModCleaner.UDR|ModCleaner.FOG)):
            return [(set(), set(), set())] * len(modInfos)
        # Python can't do ITM scanning
        doUDR = what & ModCleaner.UDR
        doFog = what & ModCleaner.FOG
        progress.setFull(max(len(modInfos),1))
        ret = []
        for i,modInfo in enumerate(modInfos):
            progress(i,_(u'Scanning...') + u'\n' + modInfo.name.s)
            itm = set()
            fog = set()
            #--UDR stuff
            udr = {}
            parents_to_scan = {}
            if len(modInfo.masterNames) > 0:
                subprogress = bolt.SubProgress(progress,i,i+1)
                if detailed:
                    subprogress.setFull(max(modInfo.size*2,1))
                else:
                    subprogress.setFull(max(modInfo.size,1))
                #--File stream
                path = modInfo.getPath()
                #--Scan
                parentType = None
                parentFid = None
                parentParentFid = None
                # Location (Interior = #, Exteror = (X,Y)
                with ModReader(modInfo.name,path.open('rb')) as ins:
                    try:
                        insAtEnd = ins.atEnd
                        insTell = ins.tell
                        insUnpackRecHeader = ins.unpackRecHeader
                        insUnpackSubHeader = ins.unpackSubHeader
                        insRead = ins.read
                        insUnpack = ins.unpack
                        headerSize = ins.recHeader.rec_header_size
                        while not insAtEnd():
                            subprogress(insTell())
                            header = insUnpackRecHeader()
                            rtype,hsize = header.recType,header.size
                            #(type,size,flags,fid,uint2) = ins.unpackRecHeader()
                            if rtype == 'GRUP':
                                groupType = header.groupType
                                if groupType == 0 and header.label not in {'CELL','WRLD'}:
                                    # Skip Tops except for WRLD and CELL groups
                                    insRead(hsize-headerSize)
                                elif detailed:
                                    if groupType == 1:
                                        # World Children
                                        parentParentFid = header.label
                                        parentType = 1 # Exterior Cell
                                        parentFid = None
                                    elif groupType == 2:
                                        # Interior Cell Block
                                        parentType = 0 # Interior Cell
                                        parentParentFid = parentFid = None
                                    elif groupType in {6,8,9,10}:
                                        # Cell Children, Cell Persisten Children,
                                        # Cell Temporary Children, Cell VWD Children
                                        parentFid = header.label
                                    else: # 3,4,5,7 - Topic Children
                                        pass
                            else:
                                if doUDR and header.flags1 & 0x20 and rtype in (
                                    'ACRE',               #--Oblivion only
                                    'ACHR','REFR',        #--Both
                                    'NAVM','PHZD','PGRE', #--Skyrim only
                                    ):
                                    if not detailed:
                                        udr[header.fid] = ModCleaner.UdrInfo(header.fid)
                                    else:
                                        fid = header.fid
                                        udr[fid] = ModCleaner.UdrInfo(fid,rtype,parentFid,u'',parentType,parentParentFid,u'',None)
                                        parents_to_scan.setdefault(parentFid,set())
                                        parents_to_scan[parentFid].add(fid)
                                        if parentParentFid:
                                            parents_to_scan.setdefault(parentParentFid,set())
                                            parents_to_scan[parentParentFid].add(fid)
                                if doFog and rtype == 'CELL':
                                    nextRecord = insTell() + hsize
                                    while insTell() < nextRecord:
                                        (nextType,nextSize) = insUnpackSubHeader()
                                        if nextType != 'XCLL':
                                            insRead(nextSize)
                                        else:
                                            color,near,far,rotXY,rotZ,fade,clip = insUnpack('=12s2f2l2f',nextSize,'CELL.XCLL')
                                            if not (near or far or clip):
                                                fog.add(header.fid)
                                else:
                                    insRead(hsize)
                        if parents_to_scan:
                            # Detailed info - need to re-scan for CELL and WRLD infomation
                            ins.seek(0)
                            baseSize = modInfo.size
                            while not insAtEnd():
                                subprogress(baseSize+insTell())
                                header = insUnpackRecHeader()
                                rtype,hsize = header.recType,header.size
                                if rtype == 'GRUP':
                                    if header.groupType == 0 and header.label not in {'CELL','WRLD'}:
                                        insRead(hsize-headerSize)
                                else:
                                    fid = header.fid
                                    if fid in parents_to_scan:
                                        record = MreRecord(header,ins,True)
                                        record.loadSubrecords()
                                        eid = u''
                                        for subrec in record.subrecords:
                                            if subrec.subType == 'EDID':
                                                eid = bolt.decode(subrec.data)
                                            elif subrec.subType == 'XCLC':
                                                pos = struct_unpack(
                                                    '=2i', subrec.data[:8])
                                        for udrFid in parents_to_scan[fid]:
                                            if rtype == 'CELL':
                                                udr[udrFid].parentEid = eid
                                                if udr[udrFid].parentType == 1:
                                                    # Exterior Cell, calculate position
                                                    udr[udrFid].pos = pos
                                            elif rtype == 'WRLD':
                                                udr[udrFid].parentParentEid = eid
                                    else:
                                        insRead(hsize)
                    except CancelError:
                        raise
                    except:
                        deprint(u'Error scanning %s, file read pos: %i:\n' % (modInfo.name.s,ins.tell()),traceback=True)
                        udr = itm = fog = None
                #--Done
            ret.append((udr.values() if udr is not None else None,itm,fog))
        return ret

    @staticmethod
    def _clean_CBash(cleaners,what,progress):
        if not (what & ModCleaner.ALL): return
        # There are scans to do
        doUDR = bool(what & ModCleaner.UDR)
        doITM = bool(what & ModCleaner.ITM)
        doFog = bool(what & ModCleaner.FOG)
        # If there are more than 255 mods, we have to break it up into
        # smaller groups.  We'll do groups of 200 for now, to allow for
        # added files due to implicitly loading masters.
        numMods = len(cleaners)
        if numMods > 255:
            ModsPerGroup = 200
            numGroups = numMods / ModsPerGroup
            if numMods % ModsPerGroup:
                numGroups += 1
        else:
            ModsPerGroup = 255
            numGroups = 1
        progress.setFull(numGroups)
        for i in range(numGroups):
            #--Load
            progress(i,_(u'Loading...'))
            groupCleaners = cleaners[i*ModsPerGroup:(i+1)*ModsPerGroup]
            with ObCollection(ModsPath=bass.dirs['mods'].s) as Current:
                for cleaner in groupCleaners:
                    if len(cleaner.modInfo.masterNames) == 0: continue
                    path = cleaner.modInfo.getPath()
                    Current.addMod(path.stail)
                Current.load()
                #--Clean
                subprogress1 = bolt.SubProgress(progress,i,i+1)
                subprogress1.setFull(max(len(groupCleaners),1))
                for j,cleaner in enumerate(groupCleaners):
                    subprogress1(j,_(u'Cleaning...') + u'\n' + cleaner.modInfo.name.s)
                    path = cleaner.modInfo.getPath()
                    modFile = Current.LookupModFile(path.stail)
                    changed = False
                    if modFile:
                        total = sum([len(cleaner.udr)*doUDR,len(cleaner.fog)*doFog,len(cleaner.itm)*doITM])
                        subprogress2 = bolt.SubProgress(subprogress1,j,j+1)
                        subprogress2.setFull(max(total,1))
                        if doUDR:
                            for udr in cleaner.udr:
                                fid = udr.fid
                                subprogress2.plus()
                                record = modFile.LookupRecord(fid)
                                if record and record._Type in ('ACRE','ACHR','REFR') and record.IsDeleted:
                                    changed = True
                                    record.IsDeleted = False
                                    record.IsIgnored = True
                        if doFog:
                            for fid in cleaner.fog:
                                subprogress2.plus()
                                record = modFile.LookupRecord(fid)
                                if record and record._Type == 'CELL':
                                    if not (record.fogNear or record.fogFar or record.fogClip):
                                        record.fogNear = 0.0001
                                        changed = True
                        if doITM:
                            for fid in cleaner.itm:
                                subprogress2.plus()
                                record = modFile.LookupRecord(fid)
                                if record:
                                    record.DeleteRecord()
                                    changed = True
                        #--Save
                        if changed:
                            modFile.save(False)

    @staticmethod
    def _clean_Python(cleaners,what,progress):
        if not (what & (ModCleaner.UDR|ModCleaner.FOG)): return
        doUDR = what & ModCleaner.UDR
        doFog = what & ModCleaner.FOG
        progress.setFull(max(len(cleaners),1))
        #--Clean
        for i,cleaner in enumerate(cleaners):
            progress(i,_(u'Cleaning...')+u'\n'+cleaner.modInfo.name.s)
            subprogress = bolt.SubProgress(progress,i,i+1)
            subprogress.setFull(max(cleaner.modInfo.size,1))
            #--File stream
            path = cleaner.modInfo.getPath()
            #--Scan & clean
            with ModReader(cleaner.modInfo.name,path.open('rb')) as ins:
                with path.temp.open('wb') as out:
                    def copy(size):
                        out.write(ins.read(size))
                    def copyPrev(size):
                        ins.seek(-size,1)
                        out.write(ins.read(size))
                    changed = False
                    while not ins.atEnd():
                        subprogress(ins.tell())
                        header = ins.unpackRecHeader()
                        rec_type,rec_size = header.recType,header.size
                        #(rec_type,rec_size,flags,fid,uint2) = ins.unpackRecHeader()
                        if rec_type == 'GRUP':
                            if header.groupType != 0:
                                pass
                            elif header.label not in ('CELL','WRLD'):
                                copy(rec_size-header.__class__.rec_header_size)
                        else:
                            if doUDR and header.flags1 & 0x20 and rec_type in {
                                'ACRE',               #--Oblivion only
                                'ACHR','REFR',        #--Both
                                'NAVM','PGRE','PHZD', #--Skyrim only
                                }:
                                header.flags1 = (header.flags1 & ~0x20) | 0x1000
                                out.seek(-header.__class__.rec_header_size,1)
                                out.write(header.pack())
                                changed = True
                            if doFog and rec_type == 'CELL':
                                nextRecord = ins.tell() + rec_size
                                while ins.tell() < nextRecord:
                                    subprogress(ins.tell())
                                    (nextType,nextSize) = ins.unpackSubHeader()
                                    copyPrev(6)
                                    if nextType != 'XCLL':
                                        copy(nextSize)
                                    else:
                                        color,near,far,rotXY,rotZ,fade,clip = ins.unpack('=12s2f2l2f',rec_size,'CELL.XCLL')
                                        if not (near or far or clip):
                                            near = 0.0001
                                            changed = True
                                        out.write(struct_pack('=12s2f2l2f', color, near, far, rotXY, rotZ, fade, clip))
                            else:
                                copy(rec_size)
            #--Save
            retry = _(u'Bash encountered an error when saving %s.') + u'\n\n' \
                + _(u'The file is in use by another process such as TES4Edit.'
                ) + u'\n' + _(u'Please close the other program that is '
                              u'accessing %s.') + u'\n\n' + _(u'Try again?')
            if changed:
                cleaner.modInfo.makeBackup()
                try:
                    path.untemp()
                except OSError as werr:
                    while werr.errno == errno.EACCES and balt.askYes(
                            None, retry % (path.stail, path.stail),
                            path.stail + _(u' - Save Error')):
                        try:
                            path.untemp()
                            break
                        except OSError as werr:
                            continue
                    else:
                        raise
                cleaner.modInfo.setmtime(crc_changed=True) # cleaned mod
            else:
                path.temp.remove()

#------------------------------------------------------------------------------
class NvidiaFogFixer:
    """Fixes cells to avoid nvidia fog problem."""
    def __init__(self,modInfo):
        self.modInfo = modInfo
        self.fixedCells = set()

    def fix_fog(self, progress):
        """Duplicates file, then walks through and edits file as necessary."""
        progress.setFull(self.modInfo.size)
        fixedCells = self.fixedCells
        fixedCells.clear()
        #--File stream
        path = self.modInfo.getPath()
        #--Scan/Edit
        with ModReader(self.modInfo.name,path.open('rb')) as ins:
            with path.temp.open('wb') as  out:
                def copy(size):
                    buff = ins.read(size)
                    out.write(buff)
                def copyPrev(size):
                    ins.seek(-size,1)
                    buff = ins.read(size)
                    out.write(buff)
                while not ins.atEnd():
                    progress(ins.tell())
                    header = ins.unpackRecHeader()
                    type,size = header.recType,header.size
                    #(type,size,str0,fid,uint2) = ins.unpackRecHeader()
                    copyPrev(header.__class__.rec_header_size)
                    if type == 'GRUP':
                        if header.groupType != 0: #--Ignore sub-groups
                            pass
                        elif header.label not in ('CELL','WRLD'):
                            copy(size-header.__class__.rec_header_size)
                    #--Handle cells
                    elif type == 'CELL':
                        nextRecord = ins.tell() + size
                        while ins.tell() < nextRecord:
                            (type,size) = ins.unpackSubHeader()
                            copyPrev(6)
                            if type != 'XCLL':
                                copy(size)
                            else:
                                color,near,far,rotXY,rotZ,fade,clip = ins.unpack('=12s2f2l2f',size,'CELL.XCLL')
                                if not (near or far or clip):
                                    near = 0.0001
                                    fixedCells.add(header.fid)
                                out.write(struct_pack('=12s2f2l2f', color, near, far, rotXY, rotZ, fade,clip))
                    #--Non-Cells
                    else:
                        copy(size)
        #--Done
        if fixedCells:
            self.modInfo.makeBackup()
            path.untemp()
            self.modInfo.setmtime(crc_changed=True) # fog fixes
        else:
            path.temp.remove()

#------------------------------------------------------------------------------
class ModDetails:
    """Details data for a mods file. Similar to TesCS Details view."""
    def __init__(self):
        self.group_records = {} #--group_records[group] = [(fid0,eid0),(fid1,eid1),...]

    def readFromMod(self, modInfo, progress=None):
        """Extracts details from mod file."""
        def getRecordReader(flags, size):
            """Decompress record data as needed."""
            if not MreRecord.flags1_(flags).compressed:
                return ins,ins.tell()+size
            else:
                import zlib
                sizeCheck, = struct_unpack('I', ins.read(4))
                decomp = zlib.decompress(ins.read(size-4))
                if len(decomp) != sizeCheck:
                    raise ModError(ins.inName,
                        u'Mis-sized compressed data. Expected %d, got %d.' % (size,len(decomp)))
                reader = ModReader(modInfo.name,sio(decomp))
                return reader,sizeCheck
        progress = progress or bolt.Progress()
        group_records = self.group_records = {}
        records = group_records[bush.game_mod.records.MreHeader.classType] = []
        with ModReader(modInfo.name,modInfo.getPath().open('rb')) as ins:
            while not ins.atEnd():
                header = ins.unpackRecHeader()
                recType, rec_siz = header.recType, header.size
                if recType == 'GRUP':
                    # FIXME(ut): monkey patch for fallout QUST GRUP
                    if bush.game.fsName == u'Fallout4' and header.groupType == 10:
                        ins.seek(rec_siz - header.__class__.rec_header_size, 1)
                        continue
                    label = header.label
                    progress(1.0*ins.tell()/modInfo.size,_(u"Scanning: ")+label)
                    records = group_records.setdefault(label,[])
                    if label in ('CELL', 'WRLD', 'DIAL'): # skip these groups
                        ins.seek(rec_siz - header.__class__.rec_header_size, 1)
                elif recType != 'GRUP':
                    eid = u''
                    nextRecord = ins.tell() + rec_siz
                    recs, endRecs = getRecordReader(header.flags1, rec_siz)
                    while recs.tell() < endRecs:
                        (recType, rec_siz) = recs.unpackSubHeader()
                        if recType == 'EDID':
                            eid = recs.readString(rec_siz)
                            break
                        recs.seek(rec_siz, 1)
                    records.append((header.fid,eid))
                    ins.seek(nextRecord)
        del group_records[bush.game_mod.records.MreHeader.classType]
