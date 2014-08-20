; macros.nsh
; Install/Uninstall macros for Wrye Bash NSIS installer.


; Prevent redefining the macro if included multiple times
!ifmacrondef InstallBashFiles
    !macro InstallBashFiles GameName GameTemplate GameDir RegValuePy RegValueExe RegPath DoPython DoExe DoAII
        ; Parameters:
        ;  GameName - name of the game files are being installed for.  This is used for registry entries
        ;  GameTemplate - name of the game that the template files are coming from (for example, Nehrim uses Oblivion files for templates)
        ;  GameDir - base directory for the game (one folder up from the Data directory)
        ;  RegValuePy - Registry value for the python version (Usually of the form $Reg_Value_OB_Py)
        ;  RegValueExe - Registry value for the standalone version
        ;  RegPath - Name of the registry string that will hold the path installing to
        ;  DoPython - Install python version of Wrye Bash (should be {BST_CHECKED} for true - this allows you to simple pass the state of the checkbox)
        ;  DoExe - Install the standalone version of Wrye Bash (should be {BST_CHECKED} for true)
        ;  IsExtra - true or false: if false, template files are not installed (since we don't know which type of game it is)
        ;  DoAII - true or false: if true, installs the ArchiveInvalidationInvalidated files (Oblivion based games)

        ; Install common files
        SetOutPath "${GameDir}\Mopy"
        File /r /x "*.bat" /x "*.py*" /x "w9xpopen.exe" /x "Wrye Bash.exe" "Mopy\*.*"
        ${If} ${DoAII} == true
            ; Some games don't use ArchiveInvalidationInvalidated
            SetOutPath "${GameDir}\Data"
            File /r "Mopy\templates\Oblivion\ArchiveInvalidationInvalidated!.bsa"
        ${EndIf}
        WriteRegStr HKLM "SOFTWARE\Wrye Bash" "${RegPath}" "${GameDir}"
        ${If} ${DoPython} == ${BST_CHECKED}
            ; Install Python only files
            SetOutPath "${GameDir}\Mopy"
            File /r "Mopy\*.py" "Mopy\*.pyw" "Mopy\*.bat"
            ; Write the installation path into the registry
            WriteRegStr HKLM "SOFTWARE\Wrye Bash" "${GameName} Python Version" "True"
        ${ElseIf} ${RegValuePy} == $Empty
            ; Only write this entry if it's never been installed before
            WriteRegStr HKLM "SOFTWARE\Wrye Bash" "${GameName} Python Version" ""
        ${EndIf}
        ${If} ${DoExe} == ${BST_CHECKED}
            ; Install the standalone only files
            SetOutPath "${GameDir}\Mopy"
            File "Mopy\Wrye Bash.exe"
            ${IfNot} ${AtLeastWinXP}
                # Running earlier than WinXP, need w9xpopen
                File "Mopy\w9xpopen.exe"
            ${EndIf}
            ; Write the installation path into the registry
            WriteRegStr HKLM "SOFTWARE\Wrye Bash" "${GameName} Standalone Version" "True"
        ${ElseIf} ${RegValueExe} == $Empty
            ; Only write this entry if it's never been installed before
            WriteRegStr HKLM "SOFTWARE\Wrye Bash" "${GameName} Standalone Version" ""
        ${EndIf}
    !macroend


    !macro RemoveRegistryEntries GameName
        ; Paramters:
        ;  GameName -  name of the game to remove registry entries for
        
        DeleteRegValue HKLM "SOFTWARE\Wrye Bash" "${GameName} Path"
        DeleteRegValue HKLM "SOFTWARE\Wrye Bash" "${GameName} Python Version"
        DeleteRegValue HKLM "SOFTWARE\Wrye Bash" "${GameName} Standalone Version"
    !macroend


    !macro RemoveOldFiles Path
        ; Old old files to delete (from before 294, the directory restructure)
        Delete "${Path}\Mopy\BashBugDump.log"
        Delete "${Path}\Mopy\DebugLog(Python2.7).bat"
        Delete "${Path}\Mopy\7zUnicode.exe"
        Delete "${Path}\Mopy\Wizard Images\Thumbs.db"
        Delete "${Path}\Data\Bashed Lists.txt"
        Delete "${Path}\Data\Bashed Lists.html"
        Delete "${Path}\Data\Ini Tweaks\Autosave, Never [Oblivion].ini"
        Delete "${Path}\Data\Ini Tweaks\Autosave, ~Always [Oblivion].ini"
        Delete "${Path}\Data\Ini Tweaks\Border Regions, Disabled [Oblivion].ini"
        Delete "${Path}\Data\Ini Tweaks\Border Regions, ~Enabled [Oblivion].ini"
        Delete "${Path}\Data\Ini Tweaks\Fonts 1, ~Default [Oblivion].ini"
        Delete "${Path}\Data\Ini Tweaks\Fonts, ~Default [Oblivion].ini"
        Delete "${Path}\Data\Ini Tweaks\Grass, Fade 4k-5k [Oblivion].ini"
        Delete "${Path}\Data\Ini Tweaks\Grass, ~Fade 2k-3k [Oblivion].ini"
        Delete "${Path}\Data\Ini Tweaks\Intro Movies, Disabled [Oblivion].ini"
        Delete "${Path}\Data\Ini Tweaks\Intro Movies, ~Normal [Oblivion].ini"
        Delete "${Path}\Data\Ini Tweaks\Joystick, Disabled [Oblivion].ini"
        Delete "${Path}\Data\Ini Tweaks\Joystick, ~Enabled [Oblivion].ini"
        Delete "${Path}\Data\Ini Tweaks\Local Map Shader, Disabled [Oblivion].ini"
        Delete "${Path}\Data\Ini Tweaks\Local Map Shader, ~Enabled [Oblivion].ini"
        Delete "${Path}\Data\Ini Tweaks\Music, Disabled [Oblivion].ini"
        Delete "${Path}\Data\Ini Tweaks\Music, ~Enabled [Oblivion].ini"
        Delete "${Path}\Data\Ini Tweaks\Refraction Shader, Disabled [Oblivion].ini"
        Delete "${Path}\Data\Ini Tweaks\Refraction Shader, ~Enabled [Oblivion].ini"
        Delete "${Path}\Data\Ini Tweaks\Save Backups, 1 [Oblivion].ini"
        Delete "${Path}\Data\Ini Tweaks\Save Backups, 2 [Oblivion].ini"
        Delete "${Path}\Data\Ini Tweaks\Save Backups, 3 [Oblivion].ini"
        Delete "${Path}\Data\Ini Tweaks\Save Backups, 5 [Oblivion].ini"
        Delete "${Path}\Data\Ini Tweaks\Screenshot, Enabled [Oblivion].ini"
        Delete "${Path}\Data\Ini Tweaks\Screenshot, ~Disabled [Oblivion].ini"
        Delete "${Path}\Data\Ini Tweaks\ShadowMapResolution, 10 [Oblivion].ini"
        Delete "${Path}\Data\Ini Tweaks\ShadowMapResolution, ~256 [Oblivion].ini"
        Delete "${Path}\Data\Ini Tweaks\ShadowMapResolution, 1024 [Oblivion].ini"
        Delete "${Path}\Data\Ini Tweaks\Sound Card Channels, 24 [Oblivion].ini"
        Delete "${Path}\Data\Ini Tweaks\Sound Card Channels, ~32 [Oblivion].ini"
        Delete "${Path}\Data\Ini Tweaks\Sound Card Channels, 128 [Oblivion].ini"
        Delete "${Path}\Data\Ini Tweaks\Sound Card Channels, 16 [Oblivion].ini"
        Delete "${Path}\Data\Ini Tweaks\Sound Card Channels, 192 [Oblivion].ini"
        Delete "${Path}\Data\Ini Tweaks\Sound Card Channels, 48 [Oblivion].ini"
        Delete "${Path}\Data\Ini Tweaks\Sound Card Channels, 64 [Oblivion].ini"
        Delete "${Path}\Data\Ini Tweaks\Sound Card Channels, 8 [Oblivion].ini"
        Delete "${Path}\Data\Ini Tweaks\Sound Card Channels, 96 [Oblivion].ini"
        Delete "${Path}\Data\Ini Tweaks\Sound, Disabled [Oblivion].ini"
        Delete "${Path}\Data\Ini Tweaks\Sound, ~Enabled [Oblivion].ini"
        Delete "${Path}\Data\Bash Patches\Assorted to Cobl.csv"
        Delete "${Path}\Data\Bash Patches\Assorted_Exhaust.csv"
        Delete "${Path}\Data\Bash Patches\Bash_Groups.csv"
        Delete "${Path}\Data\Bash Patches\Bash_MFact.csv"
        Delete "${Path}\Data\Bash Patches\ShiveringIsleTravellers_Names.csv"
        Delete "${Path}\Data\Bash Patches\TamrielTravellers_Names.csv"
        Delete "${Path}\Data\Bash Patches\Guard_Names.csv"
        Delete "${Path}\Data\Bash Patches\Kmacg94_Exhaust.csv"
        Delete "${Path}\Data\Bash Patches\P1DCandles_Formids.csv"
        Delete "${Path}\Data\Bash Patches\OOO_Potion_Names.csv"
        Delete "${Path}\Data\Bash Patches\Random_NPC_Alternate_Names.csv"
        Delete "${Path}\Data\Bash Patches\Random_NPC_Names.csv"
        Delete "${Path}\Data\Bash Patches\Rational_Names.csv"
        Delete "${Path}\Data\Bash Patches\TI to Cobl_Formids.csv"
        Delete "${Path}\Data\Bash Patches\taglist.txt"
        Delete "${Path}\Data\Bash Patches\OOO, 1.23 Mincapped_NPC_Levels.csv"
        Delete "${Path}\Data\Bash Patches\OOO, 1.23 Uncapped_NPC_Levels.csv"
        Delete "${Path}\Data\Bash Patches\Crowded Cities 15_Alternate_Names.csv"
        Delete "${Path}\Data\Bash Patches\Crowded Cities 15_Names.csv"
        Delete "${Path}\Data\Bash Patches\Crowded Cities 30_Alternate_Names.csv"
        Delete "${Path}\Data\Bash Patches\Crowded Cities 30_Names.csv"
        Delete "${Path}\Data\Bash Patches\Crowded Roads Revamped_Names.csv"
        Delete "${Path}\Data\Bash Patches\Crowded Roads Revisited_Alternate_Names.csv"
        Delete "${Path}\Data\Bash Patches\Crowded Roads Revisited_Names.csv"
        Delete "${Path}\Data\Bash Patches\PTRoamingNPCs_Names.csv"
        Delete "${Path}\Mopy\uninstall.exe"
        Delete "${Path}\Mopy\*.html"
        Delete "${Path}\Mopy\7z.*"
        Delete "${Path}\Mopy\*CBash.dll"
        Delete "${Path}\Mopy\DebugLog(Python2.6).bat"
        Delete "${Path}\Mopy\ScriptParser.p*"
        Delete "${Path}\Mopy\balt.p*"
        Delete "${Path}\Mopy\barb.p*"
        Delete "${Path}\Mopy\barg.p*"
        Delete "${Path}\Mopy\bash.p*"
        Delete "${Path}\Mopy\basher.p*"
        Delete "${Path}\Mopy\bashmon.p*"
        Delete "${Path}\Mopy\belt.p*"
        Delete "${Path}\Mopy\bish.p*"
        Delete "${Path}\Mopy\bolt.p*"
        Delete "${Path}\Mopy\bosh.p*"
        Delete "${Path}\Mopy\bush.p*"
        Delete "${Path}\Mopy\cint.p*"
        Delete "${Path}\Mopy\Wrye Bash Debug.p*"
        Delete "${Path}\Mopy\gpl.txt"
        Delete "${Path}\Mopy\lzma.exe"
        Delete "${Path}\Mopy\Wrye Bash.txt"
        Delete "${Path}\Mopy\Wrye Bash.exe.log"
        Delete "${Path}\Mopy\wizards.txt"
        Delete "${Path}\Mopy\patch_option_reference.txt"
        RMDir /r "${Path}\Mopy\Data"
        RMDir /r "${Path}\Mopy\Extra"
        RMDir /r "${Path}\Mopy\images"
        ; Some files from an older version of the Standalone that made non-standard
        ; compiled python file names (when loading python files present)
        Delete "${Path}\Mopy\bash\windowso"
        Delete "${Path}\Mopy\bash\libbsao"
        Delete "${Path}\Mopy\bash\cinto"
        Delete "${Path}\Mopy\bash\bwebo"
        Delete "${Path}\Mopy\bash\busho"
        Delete "${Path}\Mopy\bash\breco"
        Delete "${Path}\Mopy\bash\bosho"
        Delete "${Path}\Mopy\bash\bolto"
        Delete "${Path}\Mopy\bash\belto"
        Delete "${Path}\Mopy\bash\basso"
        Delete "${Path}\Mopy\bash\bashero"
        Delete "${Path}\Mopy\bash\basho"
        Delete "${Path}\Mopy\bash\bargo"
        Delete "${Path}\Mopy\bash\barbo"
        Delete "${Path}\Mopy\bash\bapio"
        Delete "${Path}\Mopy\bash\balto"
        ; As of 301 the following are obsolete:
        RMDir /r "${Path}\Mopy\macro"
        Delete "${Path}\Mopy\bash\installerstabtips.txt"
        Delete "${Path}\Mopy\bash\wizSTCo"
        Delete "${Path}\Mopy\bash\wizSTC.p*"
        Delete "${Path}\Mopy\bash\keywordWIZBAINo"
        Delete "${Path}\Mopy\bash\kwywordWIZBAIN.p*"
        Delete "${Path}\Mopy\bash\keywordWIZBAIN2o"
        Delete "${Path}\Mopy\bash\kwywordWIZBAIN2.p*"
        Delete "${Path}\Mopy\bash\settingsModuleo"
        Delete "${Path}\Mopy\bash\settingsModule.p*"
        RMDir /r "${Path}\Mopy\bash\images\stc"
        ; As of 303 the following are obsolete:
        Delete "${Path}\Mopy\templates\*.esp"
        ; As of 304.4 the following are obsolete
        Delete "${Path}\Mopy\bash\compiled\libloadorder32.dll"
        Delete "${Path}\Mopy\bash\compiled\boss32.dll"
        Delete "${Path}\Mopy\bash\bapi.p*"
        ; As of 305, the following are obsolete:
        RMDir /r "${Path}\Mopy\bash\compiled\Microsoft.VC80.CRT"
        Delete "${Path}\Mopy\bash\compiled\7zUnicode.exe"
        Delete "${Path}\Mopy\bash\compiled\7zCon.sfx"
        ${If} ${AtLeastWinXP}
            # Running XP or later, w9xpopen is only for 95/98/ME
            Delete "${Path}\Mopy\w9xpopen.exe"
        ${EndIf}
    !macroend


    !macro RemoveCurrentFiles Path
        ; Remove files belonging to current build
        RMDir /r "${Path}\Mopy"
        ; Do not remove ArchiveInvalidationInvalidated!, because if it's registeredDelete
        ; in the users INI file, this will cause problems
        ;;Delete "${Path}\Data\ArchiveInvalidationInvalidated!.bsa"
        RMDir "${Path}\Data\INI Tweaks"
        RMDir "${Path}\Data\Docs"
        RMDir "${Path}\Data\Bash Patches"
        Delete "$SMPROGRAMS\Wrye Bash\*oblivion*"
    !macroend

    !macro UninstallBash GamePath GameName
        !insertmacro RemoveOldFiles "${GamePath}"
        !insertmacro RemoveCurrentFiles "${GamePath}"
        !insertmacro RemoveRegistryEntries "${GameName}"
    !macroend
!endif
