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
"""This module lists the files installed in the Data folder in a completely
vanilla Enderal SE setup."""
import os

# Entries for other languages manually added from SteamDB:
# https://steamdb.info/app/976620/depots/
vanilla_files = {f.replace('\\', os.sep) for f in {
    'Enderal - Forgotten Stories.ini',
    'Enderal Credits.txt',
    'Enderal SE v2.0.12.4 Changelog.txt',
    'Interface\\00E_heromenu.swf',
    'Interface\\1.5.9.0patchnote and Japanes localization updates.txt',
    'Interface\\controls\\pc\\controlmap.txt',
    'Interface\\credits.txt',
    'Interface\\credits_plru.txt',
    'Interface\\dialoguemenu.swf',
    'Interface\\Enderal_jpfp.swf',
    'Interface\\Enderal_jpfp_console.swf',
    'Interface\\Enderal_jpfp_Handwritten.swf',
    'Interface\\Enderal_jpfp_Menu.swf',
    'Interface\\exported\\hudmenu.gfx',
    'Interface\\exported\\widgets\\skyui\\followerpanel.swf',
    'Interface\\FangZhengKaiTi_GBK.swf',
    'Interface\\fontconfig.txt',
    'Interface\\fonts_en2.swf',
    'Interface\\hudmenu.swf',
    'Interface\\Japanese_Credits.txt',
    'Interface\\quest_journal.swf',
    'Interface\\skyui\\icons_category_psychosteve.swf',
    'Interface\\startmenu.swf',
    'Interface\\statssheetmenu.swf',
    'Interface\\translate_english.txt',
    'Interface\\translate_chinese.txt',
    'Interface\\translate_german.txt',
    'Interface\\translate_italian.txt',
    'Interface\\translate_japanese.txt',
    'Interface\\translate_korean.txt',
    'Interface\\translate_russian.txt',
    'Interface\\translate_spanish.txt',
    'Interface\\translations\\buriedtreasure_chinese.txt',
    'Interface\\translations\\buriedtreasure_french.txt',
    'Interface\\translations\\buriedtreasure_italian.txt',
    'Interface\\translations\\buriedtreasure_japanese.txt',
    'Interface\\translations\\buriedtreasure_korean.txt',
    'Interface\\translations\\skyui_se_chinese.txt',
    'Interface\\translations\\skyui_se_japanese.txt',
    'Interface\\translations\\skyui_se_korean.txt',
    'Interface\\translations\\taverngames_chinese.txt',
    'Interface\\translations\\taverngames_french.txt',
    'Interface\\translations\\taverngames_german.txt',
    'Interface\\translations\\taverngames_italian.txt',
    'Interface\\translations\\taverngames_japanese.txt',
    'Interface\\translations\\taverngames_russian.txt',
    'Interface\\translations\\taverngames_spanish.txt',
    'Interface\\translations\\uiextensions_chinese.txt',
    'Interface\\translations\\uiextensions_french.txt',
    'Interface\\translations\\uiextensions_german.txt',
    'Interface\\translations\\uiextensions_italian.txt',
    'Interface\\translations\\uiextensions_japanese.txt',
    'Interface\\translations\\uiextensions_korean.txt',
    'meshes\\actors\\character\\animations\\enderal\\1hm_shout_exhale_medium.hkx',
    'meshes\\actors\\character\\animations\\enderal\\bagpipe.hkx',
    'meshes\\actors\\character\\animations\\enderal\\cannibal_feedcrouching.hkx',
    'meshes\\actors\\character\\animations\\enderal\\cast_magic_easy.hkx',
    'meshes\\actors\\character\\animations\\enderal\\cast_to_target.hkx',
    'meshes\\actors\\character\\animations\\enderal\\chair_idlecrosslegged_enter.hkx',
    'meshes\\actors\\character\\animations\\enderal\\chair_idlecrosslegged_exit.hkx',
    'meshes\\actors\\character\\animations\\enderal\\chair_idlecrosslegged_loop.hkx',
    'meshes\\actors\\character\\animations\\enderal\\child_birdplay.hkx',
    'meshes\\actors\\character\\animations\\enderal\\child_cartwheels.hkx',
    'meshes\\actors\\character\\animations\\enderal\\child_jumping_backandforth.hkx',
    'meshes\\actors\\character\\animations\\enderal\\child_jumping_onspot.hkx',
    'meshes\\actors\\character\\animations\\enderal\\child_playing_bird.hkx',
    'meshes\\actors\\character\\animations\\enderal\\dancing_belly.hkx',
    'meshes\\actors\\character\\animations\\enderal\\dancing_chacha.hkx',
    'meshes\\actors\\character\\animations\\enderal\\dancing_chinese.hkx',
    'meshes\\actors\\character\\animations\\enderal\\dancing_onspot_enthusiastic.hkx',
    'meshes\\actors\\character\\animations\\enderal\\dancing_onspot_side.hkx',
    'meshes\\actors\\character\\animations\\enderal\\dancing_onspot_slow.hkx',
    'meshes\\actors\\character\\animations\\enderal\\dancing_samba_a.hkx',
    'meshes\\actors\\character\\animations\\enderal\\dancing_samba_base.hkx',
    'meshes\\actors\\character\\animations\\enderal\\dancing_sensual_a.hkx',
    'meshes\\actors\\character\\animations\\enderal\\dancing_sensual_b.hkx',
    'meshes\\actors\\character\\animations\\enderal\\dancing_sensual_b_base.hkx',
    'meshes\\actors\\character\\animations\\enderal\\dancing_shaman.hkx',
    'meshes\\actors\\character\\animations\\enderal\\desperate.hkx',
    'meshes\\actors\\character\\animations\\enderal\\examine_wall.hkx',
    'meshes\\actors\\character\\animations\\enderal\\faint.hkx',
    'meshes\\actors\\character\\animations\\enderal\\fallingdown.hkx',
    'meshes\\actors\\character\\animations\\enderal\\fit_of_rage.hkx',
    'meshes\\actors\\character\\animations\\enderal\\fnis_enderal_list.txt',
    'meshes\\actors\\character\\animations\\enderal\\mq105_braced painshort.hkx',
    'meshes\\actors\\character\\animations\\enderal\\mq105_silentbow.hkx',
    'meshes\\actors\\character\\animations\\enderal\\mt_shout_exhale.hkx',
    'meshes\\actors\\character\\animations\\enderal\\mt_shout_exhale_long.hkx',
    'meshes\\actors\\character\\animations\\enderal\\mt_shout_exhale_medium.hkx',
    'meshes\\actors\\character\\animations\\enderal\\paired_calia_massacre.hkx',
    'meshes\\actors\\character\\animations\\enderal\\paired_hugb.hkx',
    'meshes\\actors\\character\\animations\\enderal\\paired_kiss_2female.hkx',
    'meshes\\actors\\character\\animations\\enderal\\paired_kiss_2male.hkx',
    'meshes\\actors\\character\\animations\\enderal\\paired_kiss_female_male.hkx',
    'meshes\\actors\\character\\animations\\enderal\\paired_kiss_male_female.hkx',
    'meshes\\actors\\character\\animations\\enderal\\pa_calia_massacre.hkx',
    'meshes\\actors\\character\\animations\\enderal\\pipesmokingcrosslegged.hkx',
    'meshes\\actors\\character\\animations\\enderal\\pipesmokingcrossleggedblazed.hkx',
    'meshes\\actors\\character\\animations\\enderal\\pipesmokingcrossleggedenter.hkx',
    'meshes\\actors\\character\\animations\\enderal\\pipesmokingcrossleggedexit.hkx',
    'meshes\\actors\\character\\animations\\enderal\\pipesmokingcrossleggedstartblaze.hkx',
    'meshes\\actors\\character\\animations\\enderal\\shadowboxing.hkx',
    'meshes\\actors\\character\\animations\\enderal\\shout_casttotarget.hkx',
    'meshes\\actors\\character\\animations\\enderal\\sing_and_drink.hkx',
    'meshes\\actors\\character\\animations\\enderal\\sneak1hm_shout_exhale.hkx',
    'meshes\\actors\\character\\animations\\enderal\\sneak1hm_shout_exhale_long.hkx',
    'meshes\\actors\\character\\animations\\enderal\\sneak1hm_shout_exhale_medium.hkx',
    'meshes\\actors\\character\\animations\\enderal\\sneak1hm_whirlwindsprint_long.hkx',
    'meshes\\actors\\character\\animations\\enderal\\sneak1hm_whirlwindsprint_longest.hkx',
    'meshes\\actors\\character\\animations\\enderal\\sneak1hm_whirlwindsprint_medium.hkx',
    'meshes\\actors\\character\\animations\\enderal\\special_chinesedance.hkx',
    'meshes\\actors\\character\\animations\\enderal\\special_cicerodance1.hkx',
    'meshes\\actors\\character\\animations\\enderal\\special_cicerodance2.hkx',
    'meshes\\actors\\character\\animations\\enderal\\special_cicerodance3.hkx',
    'meshes\\actors\\character\\animations\\enderal\\special_cicerohappy.hkx',
    'meshes\\actors\\character\\animations\\enderal\\special_waveover.hkx',
    'meshes\\actors\\character\\animations\\enderal\\stomp.hkx',
    'meshes\\actors\\character\\animations\\enderal\\testidle.hkx',
    'meshes\\actors\\character\\animations\\enderal\\wall_pipesmoking.hkx',
    'meshes\\actors\\character\\animations\\enderal\\wall_pipesmoking_blaze.hkx',
    'meshes\\actors\\character\\animations\\enderal\\wall_pipesmoking_enter.hkx',
    'meshes\\actors\\character\\animations\\enderal\\wall_pipesmoking_exit.hkx',
    'meshes\\actors\\character\\animations\\enderal\\wall_pipesmoking_loop.hkx',
    'meshes\\actors\\character\\animations\\enderal\\whirlwindsprint_long - kopie.hkx',
    'meshes\\actors\\character\\animations\\enderal\\whirlwindsprint_long - original.hkx',
    'meshes\\actors\\character\\animations\\enderal\\whirlwindsprint_long.hkx',
    'meshes\\actors\\character\\animations\\enderal\\whirlwindsprint_longest - original.hkx',
    'meshes\\actors\\character\\animations\\enderal\\whirlwindsprint_longest.hkx',
    'meshes\\actors\\character\\animations\\enderal\\whirlwindsprint_medium.hkx',
    'meshes\\actors\\character\\animations\\enderal\\whirlwindsprint_short.hkx',
    'meshes\\actors\\character\\animations\\enderal\\wounded_enter.hkx',
    'meshes\\actors\\character\\animations\\enderal\\wounded_exit.hkx',
    'meshes\\actors\\character\\animations\\enderal\\wounded_idle.hkx',
    'meshes\\actors\\character\\animations\\enderal\\_00e_bedrollfrontexit.hkx',
    'meshes\\actors\\character\\animations\\enderal\\_00e_bedroll_frontexit.hkx',
    'meshes\\actors\\character\\animations\\enderal\\_00e_catch_breath.hkx',
    'meshes\\actors\\character\\animations\\enderal\\_00e_gamblingchairsittingenter.hkx',
    'meshes\\actors\\character\\animations\\enderal\\_00e_gamblingchairsittingidle.hkx',
    'meshes\\actors\\character\\animations\\enderal\\_00e_gamblingchairsittingplaying.hkx',
    'meshes\\actors\\character\\animations\\enderal\\_00e_throw.hkx',
    'meshes\\actors\\character\\animations\\pipesmoking\\fnis_pipesmoking_list.txt',
    'meshes\\actors\\character\\animations\\pipesmoking\\pipesmokingcrosslegged.hkx',
    'meshes\\actors\\character\\animations\\pipesmoking\\pipesmokingcrossleggedblazed.hkx',
    'meshes\\actors\\character\\animations\\pipesmoking\\pipesmokingcrossleggedenter.hkx',
    'meshes\\actors\\character\\animations\\pipesmoking\\pipesmokingcrossleggedexit.hkx',
    'meshes\\actors\\character\\animations\\pipesmoking\\pipesmokingcrossleggedstartblaze.hkx',
    'meshes\\actors\\character\\behaviors\\0_master.hkx',
    'meshes\\actors\\character\\behaviors\\1hm_behavior.hkx',
    'meshes\\actors\\character\\behaviors\\FNIS_Enderal_Behavior.hkx',
    'meshes\\actors\\character\\behaviors\\FNIS_FNISBase_Behavior.hkx',
    'meshes\\actors\\character\\behaviors\\FNIS_PaleTest04_Behavior.hkx',
    'meshes\\actors\\character\\behaviors\\FNIS_PipeSmoking_Behavior.hkx',
    'meshes\\actors\\character\\behaviors\\idlebehavior.hkx',
    'meshes\\actors\\character\\behaviors\\mt_behavior.hkx',
    'meshes\\actors\\character\\behaviors\\sprintbehavior.hkx',
    'meshes\\actors\\character\\character assets\\skeleton.hkx',
    'meshes\\actors\\character\\character assets\\skeleton.nif',
    'meshes\\actors\\character\\character assets\\skeleton.xml',
    'meshes\\actors\\character\\character assets\\skeletonbeast.nif',
    'meshes\\actors\\character\\character assets female\\skeletonbeast_female.nif',
    'meshes\\actors\\character\\character assets female\\skeleton_female.hkx',
    'meshes\\actors\\character\\character assets female\\skeleton_female.nif',
    'meshes\\actors\\character\\character assets female\\skeleton_female.xml',
    'meshes\\actors\\character\\characters\\defaultmale.hkx',
    'meshes\\actors\\character\\characters female\\defaultfemale.hkx',
    'meshes\\actors\\character\\_1stperson\\skeleton.nif',
    'meshes\\animationdatasinglefile.txt',
    'meshes\\animationsetdatasinglefile.txt',
    'meshes\\terrain\\Vyn\\vyn.32.-5.9.btr',
    'Report a bug in Enderal SE.url',
    'Scripts\\ActiveMagicEffect.pex',
    'Scripts\\Actor.pex',
    'Scripts\\ActorBase.pex',
    'Scripts\\ActorValueInfo.pex',
    'Scripts\\Alias.pex',
    'Scripts\\Ammo.pex',
    'Scripts\\Apparatus.pex',
    'Scripts\\Armor.pex',
    'Scripts\\ArmorAddon.pex',
    'Scripts\\Art.pex',
    'Scripts\\Book.pex',
    'Scripts\\Camera.pex',
    'Scripts\\Cell.pex',
    'Scripts\\ColorComponent.pex',
    'Scripts\\ColorForm.pex',
    'Scripts\\CombatStyle.pex',
    'Scripts\\ConstructibleObject.pex',
    'Scripts\\DefaultObjectManager.pex',
    'Scripts\\Enchantment.pex',
    'Scripts\\EquipSlot.pex',
    'Scripts\\Faction.pex',
    'Scripts\\Flora.pex',
    'Scripts\\Form.pex',
    'Scripts\\FormList.pex',
    'Scripts\\FormType.pex',
    'Scripts\\Game.pex',
    'Scripts\\GameData.pex',
    'Scripts\\HeadPart.pex',
    'Scripts\\Ingredient.pex',
    'Scripts\\Input.pex',
    'Scripts\\JArray.pex',
    'Scripts\\JAtomic.pex',
    'Scripts\\JContainers.pex',
    'Scripts\\JContainers_DomainExample.pex',
    'Scripts\\JDB.pex',
    'Scripts\\JFormDB.pex',
    'Scripts\\JFormMap.pex',
    'Scripts\\JIntMap.pex',
    'Scripts\\JLua.pex',
    'Scripts\\JMap.pex',
    'Scripts\\JString.pex',
    'Scripts\\JValue.pex',
    'Scripts\\Keyword.pex',
    'Scripts\\LeveledActor.pex',
    'Scripts\\LeveledItem.pex',
    'Scripts\\LeveledSpell.pex',
    'Scripts\\Location.pex',
    'Scripts\\MagicEffect.pex',
    'Scripts\\Math.pex',
    'Scripts\\ModEvent.pex',
    'Scripts\\NetImmerse.pex',
    'Scripts\\objectreference.pex',
    'Scripts\\Outfit.pex',
    'Scripts\\Perk.pex',
    'Scripts\\potion.pex',
    'Scripts\\Quest.pex',
    'Scripts\\Race.pex',
    'Scripts\\Scroll.pex',
    'Scripts\\Shout.pex',
    'Scripts\\SKI_ConfigMenu.pex',
    'Scripts\\ski_favoritesmanager.pex',
    'Scripts\\SKSE.pex',
    'Scripts\\SoulGem.pex',
    'Scripts\\Sound.pex',
    'Scripts\\SoundDescriptor.pex',
    'Scripts\\Source\\ActiveMagicEffect.psc',
    'Scripts\\Source\\Actor.psc',
    'Scripts\\Source\\ActorBase.psc',
    'Scripts\\Source\\ActorValueInfo.psc',
    'Scripts\\Source\\Alias.psc',
    'Scripts\\Source\\Ammo.psc',
    'Scripts\\Source\\Apparatus.psc',
    'Scripts\\Source\\Armor.psc',
    'Scripts\\Source\\ArmorAddon.psc',
    'Scripts\\Source\\Art.psc',
    'Scripts\\Source\\Book.psc',
    'Scripts\\Source\\Camera.psc',
    'Scripts\\Source\\Cell.psc',
    'Scripts\\Source\\ColorComponent.psc',
    'Scripts\\Source\\ColorForm.psc',
    'Scripts\\Source\\CombatStyle.psc',
    'Scripts\\Source\\ConstructibleObject.psc',
    'Scripts\\Source\\DefaultObjectManager.psc',
    'Scripts\\Source\\Enchantment.psc',
    'Scripts\\Source\\EquipSlot.psc',
    'Scripts\\Source\\Faction.psc',
    'Scripts\\Source\\Flora.psc',
    'Scripts\\Source\\Form.psc',
    'Scripts\\Source\\FormList.psc',
    'Scripts\\Source\\FormType.psc',
    'Scripts\\Source\\Game.psc',
    'Scripts\\Source\\GameData.psc',
    'Scripts\\Source\\HeadPart.psc',
    'Scripts\\Source\\Ingredient.psc',
    'Scripts\\Source\\Input.psc',
    'Scripts\\Source\\JArray.psc',
    'Scripts\\Source\\JAtomic.psc',
    'Scripts\\Source\\JContainers.psc',
    'Scripts\\Source\\JContainers_DomainExample.psc',
    'Scripts\\Source\\JDB.psc',
    'Scripts\\Source\\JFormDB.psc',
    'Scripts\\Source\\JFormMap.psc',
    'Scripts\\Source\\JIntMap.psc',
    'Scripts\\Source\\JLua.psc',
    'Scripts\\Source\\JMap.psc',
    'Scripts\\Source\\JString.psc',
    'Scripts\\Source\\JValue.psc',
    'Scripts\\Source\\Keyword.psc',
    'Scripts\\Source\\LeveledActor.psc',
    'Scripts\\Source\\LeveledItem.psc',
    'Scripts\\Source\\LeveledSpell.psc',
    'Scripts\\Source\\Location.psc',
    'Scripts\\Source\\MagicEffect.psc',
    'Scripts\\Source\\Math.psc',
    'Scripts\\Source\\ModEvent.psc',
    'Scripts\\Source\\NetImmerse.psc',
    'Scripts\\Source\\ObjectReference.psc',
    'Scripts\\Source\\Outfit.psc',
    'Scripts\\Source\\Perk.psc',
    'Scripts\\Source\\Potion.psc',
    'Scripts\\Source\\Quest.psc',
    'Scripts\\Source\\Race.psc',
    'Scripts\\Source\\Scroll.psc',
    'Scripts\\Source\\Shout.psc',
    'Scripts\\Source\\ski_favoritesmanager.psc',
    'Scripts\\Source\\SKSE.psc',
    'Scripts\\Source\\SoulGem.psc',
    'Scripts\\Source\\Sound.psc',
    'Scripts\\Source\\SoundDescriptor.psc',
    'Scripts\\Source\\SpawnerTask.psc',
    'Scripts\\Source\\Spell.psc',
    'Scripts\\Source\\StringUtil.psc',
    'Scripts\\Source\\TextureSet.psc',
    'Scripts\\Source\\TreeObject.psc',
    'Scripts\\Source\\UI.psc',
    'Scripts\\Source\\UICallback.psc',
    'Scripts\\Source\\Utility.psc',
    'Scripts\\Source\\Weapon.psc',
    'Scripts\\Source\\Weather.psc',
    'Scripts\\Source\\WornObject.psc',
    'Scripts\\SpawnerTask.pex',
    'Scripts\\Spell.pex',
    'Scripts\\StringUtil.pex',
    'Scripts\\TextureSet.pex',
    'Scripts\\TreeObject.pex',
    'Scripts\\UI.pex',
    'Scripts\\UICallback.pex',
    'Scripts\\Utility.pex',
    'Scripts\\Weapon.pex',
    'Scripts\\Weather.pex',
    'Scripts\\WornObject.pex',
    'SKSE\\Plugins\\EnderalSE.dll',
    'SKSE\\Plugins\\EnderalSE.ini',
    'SKSE\\Plugins\\EnderalSteam.ini',
    'SKSE\\Plugins\\EnderalVersion.ini',
    'SKSE\\Plugins\\EngineFixes.dll',
    'SKSE\\Plugins\\EngineFixes.toml',
    'SKSE\\Plugins\\EngineFixes_preload.txt',
    'SKSE\\Plugins\\EngineFixes_SNCT.toml',
    'SKSE\\Plugins\\FlatMapMarkersSSE.dll',
    'SKSE\\Plugins\\FlatMapMarkersSSE.json',
    'SKSE\\Plugins\\fs.dll',
    'SKSE\\Plugins\\fs_src.7z',
    'SKSE\\Plugins\\fs_steam.dll',
    'SKSE\\Plugins\\JCData\\Domains\\.force-install',
    'SKSE\\Plugins\\JCData\\InternalLuaScripts\\api_for_lua.h',
    'SKSE\\Plugins\\JCData\\InternalLuaScripts\\init.lua',
    'SKSE\\Plugins\\JCData\\InternalLuaScripts\\jc.lua',
    'SKSE\\Plugins\\JCData\\lua\\jc\\init.lua',
    'SKSE\\Plugins\\JCData\\lua\\testing\\basic.lua',
    'SKSE\\Plugins\\JCData\\lua\\testing\\init.lua',
    'SKSE\\Plugins\\JCData\\lua\\testing\\jc-tests.lua',
    'SKSE\\Plugins\\JCData\\lua\\testing\\misc.lua',
    'SKSE\\Plugins\\JCData\\lua\\testing\\test.lua',
    'SKSE\\Plugins\\JContainers64.dll',
    'SKSE\\Plugins\\SkyrimRedirector.dll',
    'SKSE\\Plugins\\SkyrimRedirector.ini',
    'SKSE\\Plugins\\SkyrimRedirector.log',
    'SKSE\\Plugins\\SSEDisplayTweaks.dll',
    'SKSE\\Plugins\\SSEDisplayTweaks.ini',
    'SKSE\\Plugins\\version-1-5-16-0.bin',
    'SKSE\\Plugins\\version-1-5-23-0.bin',
    'SKSE\\Plugins\\version-1-5-3-0.bin',
    'SKSE\\Plugins\\version-1-5-39-0.bin',
    'SKSE\\Plugins\\version-1-5-50-0.bin',
    'SKSE\\Plugins\\version-1-5-53-0.bin',
    'SKSE\\Plugins\\version-1-5-62-0.bin',
    'SKSE\\Plugins\\version-1-5-73-0.bin',
    'SKSE\\Plugins\\version-1-5-80-0.bin',
    'SKSE\\Plugins\\version-1-5-97-0.bin',
    'SKSE\\Plugins\\YesImSure.dll',
    'SKSE\\Plugins\\YesImSure.json',
    'SKSE\\SKSE.ini',
    'SkyUI_SE.ini',
    'Source\\Scripts\\ActiveMagicEffect.psc',
    'Source\\Scripts\\Actor.psc',
    'Source\\Scripts\\ActorBase.psc',
    'Source\\Scripts\\ActorValueInfo.psc',
    'Source\\Scripts\\Alias.psc',
    'Source\\Scripts\\Ammo.psc',
    'Source\\Scripts\\Apparatus.psc',
    'Source\\Scripts\\Armor.psc',
    'Source\\Scripts\\ArmorAddon.psc',
    'Source\\Scripts\\Art.psc',
    'Source\\Scripts\\Book.psc',
    'Source\\Scripts\\Camera.psc',
    'Source\\Scripts\\Cell.psc',
    'Source\\Scripts\\ColorComponent.psc',
    'Source\\Scripts\\ColorForm.psc',
    'Source\\Scripts\\CombatStyle.psc',
    'Source\\Scripts\\ConstructibleObject.psc',
    'Source\\Scripts\\DefaultObjectManager.psc',
    'Source\\Scripts\\Enchantment.psc',
    'Source\\Scripts\\EquipSlot.psc',
    'Source\\Scripts\\Faction.psc',
    'Source\\Scripts\\Flora.psc',
    'Source\\Scripts\\Form.psc',
    'Source\\Scripts\\FormList.psc',
    'Source\\Scripts\\FormType.psc',
    'Source\\Scripts\\Game.psc',
    'Source\\Scripts\\GameData.psc',
    'Source\\Scripts\\HeadPart.psc',
    'Source\\Scripts\\Ingredient.psc',
    'Source\\Scripts\\Input.psc',
    'Source\\Scripts\\JArray.psc',
    'Source\\Scripts\\JAtomic.psc',
    'Source\\Scripts\\JContainers.psc',
    'Source\\Scripts\\JContainers_DomainExample.psc',
    'Source\\Scripts\\JDB.psc',
    'Source\\Scripts\\JFormDB.psc',
    'Source\\Scripts\\JFormMap.psc',
    'Source\\Scripts\\JIntMap.psc',
    'Source\\Scripts\\JLua.psc',
    'Source\\Scripts\\JMap.psc',
    'Source\\Scripts\\JString.psc',
    'Source\\Scripts\\JValue.psc',
    'Source\\Scripts\\Keyword.psc',
    'Source\\Scripts\\LeveledActor.psc',
    'Source\\Scripts\\LeveledItem.psc',
    'Source\\Scripts\\LeveledSpell.psc',
    'Source\\Scripts\\Location.psc',
    'Source\\Scripts\\MagicEffect.psc',
    'Source\\Scripts\\Math.psc',
    'Source\\Scripts\\ModEvent.psc',
    'Source\\Scripts\\NetImmerse.psc',
    'Source\\Scripts\\ObjectReference.psc',
    'Source\\Scripts\\Outfit.psc',
    'Source\\Scripts\\Perk.psc',
    'Source\\Scripts\\Potion.psc',
    'Source\\Scripts\\Quest.psc',
    'Source\\Scripts\\Race.psc',
    'Source\\Scripts\\Scroll.psc',
    'Source\\Scripts\\Shout.psc',
    'Source\\Scripts\\SKSE.psc',
    'Source\\Scripts\\SoulGem.psc',
    'Source\\Scripts\\Sound.psc',
    'Source\\Scripts\\SoundDescriptor.psc',
    'Source\\Scripts\\SpawnerTask.psc',
    'Source\\Scripts\\Spell.psc',
    'Source\\Scripts\\StringUtil.psc',
    'Source\\Scripts\\TextureSet.psc',
    'Source\\Scripts\\TreeObject.psc',
    'Source\\Scripts\\UI.psc',
    'Source\\Scripts\\UICallback.psc',
    'Source\\Scripts\\Utility.psc',
    'Source\\Scripts\\Weapon.psc',
    'Source\\Scripts\\Weather.psc',
    'Source\\Scripts\\WornObject.psc',
    'Strings\\enderal - forgotten stories_chinese.dlstrings',
    'Strings\\enderal - forgotten stories_chinese.ilstrings',
    'Strings\\enderal - forgotten stories_chinese.strings',
    'Strings\\enderal - forgotten stories_english.dlstrings',
    'Strings\\enderal - forgotten stories_english.ilstrings',
    'Strings\\enderal - forgotten stories_english.strings',
    'Strings\\enderal - forgotten stories_french.dlstrings',
    'Strings\\enderal - forgotten stories_french.ilstrings',
    'Strings\\enderal - forgotten stories_french.strings',
    'Strings\\enderal - forgotten stories_german.dlstrings',
    'Strings\\enderal - forgotten stories_german.ilstrings',
    'Strings\\enderal - forgotten stories_german.strings',
    'Strings\\enderal - forgotten stories_italian.dlstrings',
    'Strings\\enderal - forgotten stories_italian.ilstrings',
    'Strings\\enderal - forgotten stories_italian.strings',
    'Strings\\enderal - forgotten stories_japanese.dlstrings',
    'Strings\\enderal - forgotten stories_japanese.ilstrings',
    'Strings\\enderal - forgotten stories_japanese.strings',
    'Strings\\enderal - forgotten stories_korean.dlstrings',
    'Strings\\enderal - forgotten stories_korean.ilstrings',
    'Strings\\enderal - forgotten stories_korean.strings',
    'Strings\\enderal - forgotten stories_russian.dlstrings',
    'Strings\\enderal - forgotten stories_russian.ilstrings',
    'Strings\\enderal - forgotten stories_russian.strings',
    'Strings\\enderal - forgotten stories_spanish.dlstrings',
    'Strings\\enderal - forgotten stories_spanish.ilstrings',
    'Strings\\enderal - forgotten stories_spanish.strings',
    'Strings\\skyrim_chinese.dlstrings',
    'Strings\\skyrim_chinese.ilstrings',
    'Strings\\skyrim_chinese.strings',
    'Strings\\skyrim_english.dlstrings',
    'Strings\\skyrim_english.ilstrings',
    'Strings\\skyrim_english.strings',
    'Strings\\skyrim_french.dlstrings',
    'Strings\\skyrim_french.ilstrings',
    'Strings\\skyrim_french.strings',
    'Strings\\skyrim_german.dlstrings',
    'Strings\\skyrim_german.ilstrings',
    'Strings\\skyrim_german.strings',
    'Strings\\skyrim_italian.dlstrings',
    'Strings\\skyrim_italian.ilstrings',
    'Strings\\skyrim_italian.strings',
    'Strings\\skyrim_japanese.dlstrings',
    'Strings\\skyrim_japanese.ilstrings',
    'Strings\\skyrim_japanese.strings',
    'Strings\\skyrim_korean.dlstrings',
    'Strings\\skyrim_korean.ilstrings',
    'Strings\\skyrim_korean.strings',
    'Strings\\skyrim_russian.dlstrings',
    'Strings\\skyrim_russian.ilstrings',
    'Strings\\skyrim_russian.strings',
    'Strings\\skyrim_spanish.dlstrings',
    'Strings\\skyrim_spanish.ilstrings',
    'Strings\\skyrim_spanish.strings',
    'Video\\EnderalIntro.bik',
    'Video\\Enderal_Credits.bik',
    'Video\\MQ17BlackGuardian.bik',
    'Video\\MQP03NearDeathExperience.bik',
    '_Enderal - Forgotten Stories.ini',
}}
