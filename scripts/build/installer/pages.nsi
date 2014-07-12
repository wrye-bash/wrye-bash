; pages.nsi
; Custom pages for the Wrye Bash NSIS installer / uninstaller


;---------------------------- Install Locations Page
    Function PAGE_INSTALLLOCATIONS
        !insertmacro MUI_HEADER_TEXT $(PAGE_INSTALLLOCATIONS_TITLE) $(PAGE_INSTALLLOCATIONS_SUBTITLE)
        GetFunctionAddress $Function_Browse OnClick_Browse
        GetFunctionAddress $Function_Extra OnClick_Extra
        nsDialogs::Create 1018
            Pop $Dialog

        ${If} $Dialog == error
            Abort
        ${EndIf}

        ${NSD_CreateLabel} 0 0 100% 24u "Select which Game(s)/Extra location(s) which you would like to install Wrye Bash for.$\nAlso select which version(s) to install (Standalone exe (default) and/or Python version)."
            Pop $Label
            IntOp $0 0 + 25
        ${If} $Path_OB != $Empty
            ${NSD_CreateCheckBox} 0 $0u 30% 13u "Install for Oblivion"
                Pop $Check_OB
                ${NSD_SetState} $Check_OB $CheckState_OB
            ${NSD_CreateCheckBox} 30% $0u 40% 13u "Wrye Bash [Standalone]"
                Pop $Check_OB_Exe
                ${NSD_AddStyle} $Check_OB_Exe ${WS_GROUP}
                ${NSD_SetState} $Check_OB_Exe  $CheckState_OB_Exe
            ${NSD_CreateCheckBox} 70% $0u 30% 13u "Wrye Bash [Python]"
                Pop $Check_OB_Py
;                ${NSD_SetState} $Check_OB_Py  $CheckState_OB_Py
            IntOp $0 $0 + 13
            ${NSD_CreateDirRequest} 0 $0u 90% 13u "$Path_OB"
                Pop $PathDialogue_OB
            ${NSD_CreateBrowseButton} -10% $0u 5% 13u "..."
                Pop $Browse_OB
                nsDialogs::OnClick $Browse_OB $Function_Browse
            IntOp $0 $0 + 13
        ${EndIf}
        ${If} $Path_Nehrim != $Empty
            ${NSD_CreateCheckBox} 0 $0u 30% 13u "Install for Nehrim"
                Pop $Check_Nehrim
                ${NSD_SetState} $Check_Nehrim $CheckState_Nehrim
            ${NSD_CreateCheckBox} 30% $0u 40% 13u "Wrye Bash [Standalone]"
                Pop $Check_Nehrim_Exe
                ${NSD_AddStyle} $Check_Nehrim_Exe ${WS_GROUP}
                ${NSD_SetState} $Check_Nehrim_Exe  $CheckState_Nehrim_Exe
            ${NSD_CreateCheckBox} 70% $0u 30% 13u "Wrye Bash [Python]"
                Pop $Check_Nehrim_Py
;                ${NSD_SetState} $Check_Nehrim_Py  $CheckState_Nehrim_Py
            IntOp $0 $0 + 13
            ${NSD_CreateDirRequest} 0 $0u 90% 13u "$Path_Nehrim"
                Pop $PathDialogue_Nehrim
            ${NSD_CreateBrowseButton} -10% $0u 5% 13u "..."
                Pop $Browse_Nehrim
                nsDialogs::OnClick $Browse_Nehrim $Function_Browse
            IntOp $0 $0 + 13
        ${EndIf}
        ${If} $Path_Skyrim != $Empty
            ${NSD_CreateCheckBox} 0 $0u 30% 13u "Install for Skyrim"
                Pop $Check_Skyrim
                ${NSD_SetState} $Check_Skyrim $CheckState_Skyrim
            ${NSD_CreateCheckBox} 30% $0u 40% 13u "Wrye Bash [Standalone]"
                Pop $Check_Skyrim_Exe
                ${NSD_AddStyle} $Check_Skyrim_Exe ${WS_GROUP}
                ${NSD_SetState} $Check_Skyrim_Exe $CheckState_Skyrim_Exe
            ${NSD_CreateCheckBox} 70% $0u 30% 13u "Wrye Bash [Python]"
                Pop $Check_Skyrim_Py
;                ${NSD_SetState} $Check_Skyrim_Py $CheckState_Skyrim_Py
            IntOp $0 $0 + 13
            ${NSD_CreateDirRequest} 0 $0u 90% 13u "$Path_Skyrim"
                Pop $PathDialogue_Skyrim
            ${NSD_CreateBrowseButton} -10% $0u 5% 13u "..."
                Pop $Browse_Skyrim
                nsDialogs::OnClick $Browse_Skyrim $Function_Browse
            IntOp $0 $0 + 13
        ${EndIf}
        ${NSD_CreateCheckBox} 0 $0u 100% 13u "Install to extra locations"
            Pop $Check_Extra
            ${NSD_SetState} $Check_Extra $CheckState_Extra
                nsDialogs::OnClick $Check_Extra $Function_Extra
                IntOp $0 $0 + 13
            ${NSD_CreateCheckBox} 0 $0u 30% 13u "Extra Location #1:"
                Pop $Check_Ex1
                ${NSD_SetState} $Check_Ex1 $CheckState_Ex1
                ${NSD_CreateCheckBox} 30% $0u 40% 13u "Wrye Bash [Standalone]"
                    Pop $Check_Ex1_Exe
                    ${NSD_AddStyle} $Check_Ex1_Exe ${WS_GROUP}
                    ${NSD_SetState} $Check_Ex1_Exe  $CheckState_Ex1_Exe
                ${NSD_CreateCheckBox} 70% $0u 30% 13u "Wrye Bash [Python]"
                    Pop $Check_Ex1_Py
;                    ${NSD_SetState} $Check_Ex1_Py  $CheckState_Ex1_Py
                IntOp $0 $0 + 13
                ${NSD_CreateDirRequest} 0 $0u 90% 13u "$Path_Ex1"
                    Pop $PathDialogue_Ex1
                ${NSD_CreateBrowseButton} -10% $0u 5% 13u "..."
                    Pop $Browse_Ex1
                    nsDialogs::OnClick $Browse_Ex1 $Function_Browse
                IntOp $0 $0 + 13
            ${NSD_CreateCheckBox} 0 $0u 30% 13u "Extra Location #2:"
                Pop $Check_Ex2
                ${NSD_SetState} $Check_Ex2 $CheckState_Ex2
                ${NSD_CreateCheckBox} 30% $0u 40% 13u "Wrye Bash [Standalone]"
                    Pop $Check_Ex2_Exe
                    ${NSD_AddStyle} $Check_Ex2_Exe ${WS_GROUP}
                    ${NSD_SetState} $Check_Ex2_Exe  $CheckState_Ex2_Exe
                ${NSD_CreateCheckBox} 70% $0u 30% 13u "Wrye Bash [Python]"
                    Pop $Check_Ex2_Py
;                    ${NSD_SetState} $Check_Ex2_Py  $CheckState_Ex2_Py
                IntOp $0 $0 + 13
                ${NSD_CreateDirRequest} 0 $0u 90% 13u "$Path_Ex2"
                    Pop $PathDialogue_Ex2
                ${NSD_CreateBrowseButton} -10% $0u 5% 13u "..."
                    Pop $Browse_Ex2
                    nsDialogs::OnClick $Browse_Ex2 $Function_Browse
        ${If} $CheckState_Extra != ${BST_CHECKED}
            ShowWindow $Check_Ex1 ${SW_HIDE}
            ShowWindow $Check_Ex1_Py ${SW_HIDE}
            ShowWindow $Check_Ex1_Exe ${SW_HIDE}
            ShowWindow $PathDialogue_Ex1 ${SW_HIDE}
            ShowWindow $Browse_Ex1 ${SW_HIDE}
            ShowWindow $Check_Ex2 ${SW_HIDE}
            ShowWindow $Check_Ex2_Py ${SW_HIDE}
            ShowWindow $Check_Ex2_Exe ${SW_HIDE}
            ShowWindow $PathDialogue_Ex2 ${SW_HIDE}
            ShowWindow $Browse_Ex2 ${SW_HIDE}
        ${EndIf}
        nsDialogs::Show
    FunctionEnd

    Function PAGE_INSTALLLOCATIONS_Leave
        # in case the user goes back to this page and changes selections
        StrCpy $PythonVersionInstall $Empty
        StrCpy $ExeVersionInstall $Empty

        ; Game paths
        ${NSD_GetText} $PathDialogue_OB $Path_OB
        ${NSD_GetText} $PathDialogue_Nehrim $Path_Nehrim
        ${NSD_GetText} $PathDialogue_Skyrim $Path_Skyrim
        ${NSD_GetText} $PathDialogue_Ex1 $Path_Ex1
        ${NSD_GetText} $PathDialogue_Ex2 $Path_Ex2

        ; Game states
        ${NSD_GetState} $Check_OB $CheckState_OB
        ${NSD_GetState} $Check_Nehrim $CheckState_Nehrim
        ${NSD_GetState} $Check_Skyrim $CheckState_Skyrim
        ${NSD_GetState} $Check_Extra $CheckState_Extra
        ${NSD_GetState} $Check_Ex1 $CheckState_Ex1
        ${NSD_GetState} $Check_Ex2 $CheckState_Ex2

        ; Python states
        ${NSD_GetState} $Check_OB_Py $CheckState_OB_Py
        ${NSD_GetState} $Check_Nehrim_Py $CheckState_Nehrim_Py
        ${NSD_GetState} $Check_Skyrim_Py $CheckState_Skyrim_Py
        ${NSD_GetState} $Check_Ex1_Py $CheckState_Ex1_Py
        ${NSD_GetState} $Check_Ex2_Py $CheckState_Ex2_Py
        ${If} $CheckState_OB_Py == ${BST_CHECKED}
        ${AndIf} $CheckState_OB == ${BST_CHECKED}
            StrCpy $PythonVersionInstall $True
        ${Endif}
        ${If} $CheckState_Nehrim_Py == ${BST_CHECKED}
        ${AndIf} $CheckState_Nehrim == ${BST_CHECKED}
            StrCpy $PythonVersionInstall $True
        ${Endif}
        ${If} $CheckState_Skyrim_Py == ${BST_CHECKED}
        ${AndIf} $CheckState_Skyrim == ${BST_CHECKED}
            StrCpy $PythonVersionInstall $True
        ${EndIf}
        ${If} $CheckState_Ex1_Py == ${BST_CHECKED}
        ${AndIf} $CheckState_Extra == ${BST_CHECKED}
        ${AndIf} $CheckState_Ex1 == ${BST_CHECKED}
            StrCpy $PythonVersionInstall $True
        ${Endif}
        ${If} $CheckState_Ex2_Py == ${BST_CHECKED}
        ${AndIf} $CheckState_Extra == ${BST_CHECKED}
        ${AndIf} $CheckState_Ex2 == ${BST_CHECKED}
            StrCpy $PythonVersionInstall $True
        ${Endif}

        ; Standalone states
        ${NSD_GetState} $Check_OB_Exe $CheckState_OB_Exe
        ${NSD_GetState} $Check_Nehrim_Exe $CheckState_Nehrim_Exe
        ${NSD_GetState} $Check_Skyrim_Exe $CheckState_Skyrim_Exe
        ${NSD_GetState} $Check_Ex1_Exe $CheckState_Ex1_Exe
        ${NSD_GetState} $Check_Ex2_Exe $CheckState_Ex2_Exe
        ${If} $CheckState_OB_Exe == ${BST_CHECKED}
        ${AndIf} $CheckState_OB == ${BST_CHECKED}
            StrCpy $ExeVersionInstall $True
        ${Endif}
        ${If} $CheckState_Nehrim_Exe == ${BST_CHECKED}
        ${AndIf} $CheckState_Nehrim == ${BST_CHECKED}
            StrCpy $ExeVersionInstall $True
        ${Endif}
        ${If} $CheckState_Skyrim_Exe == ${BST_CHECKED}
        ${AndIf} $CheckState_Skyrim == ${BST_CHECKED}
            StrCpy $ExeVersionInstall $True
        ${EndIf}
        ${If} $CheckState_Ex1_Exe == ${BST_CHECKED}
        ${AndIf} $CheckState_Extra == ${BST_CHECKED}
        ${AndIf} $CheckState_Ex1 == ${BST_CHECKED}
            StrCpy $ExeVersionInstall $True
        ${Endif}
        ${If} $CheckState_Ex2_Exe == ${BST_CHECKED}
        ${AndIf} $CheckState_Extra == ${BST_CHECKED}
        ${AndIf} $CheckState_Ex2 == ${BST_CHECKED}
            StrCpy $ExeVersionInstall $True
        ${Endif}
    FunctionEnd


;---------------------------- Check Locations Page
    Function PAGE_CHECK_LOCATIONS
        !insertmacro MUI_HEADER_TEXT $(PAGE_CHECK_LOCATIONS_TITLE) $(PAGE_CHECK_LOCATIONS_SUBTITLE)

        ; test for installation in program files
        StrCpy $1 $Empty
        ${If} $CheckState_OB == ${BST_CHECKED}
            ${StrLoc} $0 $Path_OB "$PROGRAMFILES\" ">"
            ${If} "0" == $0
                StrCpy $1 $True
            ${Endif}
        ${Endif}
        ${If} $CheckState_Nehrim == ${BST_CHECKED}
            ${StrLoc} $0 $Path_Nehrim "$PROGRAMFILES\" ">"
            ${If} "0" == $0
                StrCpy $1 $True
            ${Endif}
        ${Endif}
        ${If} $CheckState_Skyrim == ${BST_CHECKED}
            ${StrLoc} $0 $Path_Skyrim "$PROGRAMFILES\" ">"
            ${If} "0" == $0
                StrCpy $1 $True
            ${EndIf}
        ${EndIf}
        ${If} $CheckState_Ex1 == ${BST_CHECKED}
            ${StrLoc} $0 $Path_Ex1 "$PROGRAMFILES\" ">"
            ${If} "0" == $0
                StrCpy $1 $True
            ${Endif}
        ${Endif}
        ${If} $CheckState_Ex2 == ${BST_CHECKED}
            ${StrLoc} $0 $Path_Ex2 "$PROGRAMFILES\" ">"
            ${If} "0" == $0
                StrCpy $1 $True
            ${Endif}
        ${Endif}

        ${If} $1 == $Empty
            ; nothing installed in program files: skip this page
            Abort
        ${Endif}

        nsDialogs::Create 1018
            Pop $Dialog
        ${If} $Dialog == error
            Abort
        ${EndIf}

        ${NSD_CreateLabel} 0 0 100% 24u "You are attempting to install Wrye Bash into the Program Files directory."
        Pop $Label
        SetCtlColors $Label "FF0000" "transparent"

        ${NSD_CreateLabel} 0 24 100% 128u "This is a very common cause of problems when using Wrye Bash. Highly recommended that you stop this installation now, reinstall (Oblivion/Skyrim/Steam) into another directory outside of Program Files, such as C:\Games\Oblivion, and install Wrye Bash at that location.$\n$\nThe problems with installing in Program Files stem from a feature of Windows that did not exist when Oblivion was released: User Access Controls (UAC).  If you continue with the install into Program Files, you may have trouble starting or using Wrye Bash, as it may not be able to access its own files."
        Pop $Label

        nsDialogs::Show
    FunctionEnd

    Function PAGE_CHECK_LOCATIONS_Leave
    FunctionEnd


;---------------------------- Finish Page
    Function PAGE_FINISH
        !insertmacro MUI_HEADER_TEXT $(PAGE_FINISH_TITLE) $(PAGE_FINISH_SUBTITLE)

        ReadRegStr $Path_OB HKLM "Software\Wrye Bash" "Oblivion Path"
        ReadRegStr $Path_Nehrim HKLM "Software\Wrye Bash" "Nehrim Path"
        ReadRegStr $Path_Skyrim HKLM "Software\Wrye Bash" "Skyrim Path"
        ReadRegStr $Path_Ex1 HKLM "Software\Wrye Bash" "Extra Path 1"
        ReadRegStr $Path_Ex2 HKLM "Software\Wrye Bash" "Extra Path 2"

        nsDialogs::Create 1018
            Pop $Dialog
        ${If} $Dialog == error
            Abort
        ${EndIf}

        IntOp $0 0 + 0
        ${NSD_CreateLabel} 0 0 100% 16u "Please select which Wrye Bash installation(s), if any, you would like to run right now:"
            Pop $Label
        IntOp $0 0 + 17
        ${If} $Path_OB != $Empty
            ${NSD_CreateCheckBox} 0 $0u 100% 8u "Oblivion"
                Pop $Check_OB
            IntOp $0 $0 + 9
        ${EndIf}
        ${If} $Path_Nehrim != $Empty
            ${NSD_CreateCheckBox} 0 $0u 100% 8u "Nehrim"
                Pop $Check_Nehrim
            IntOp $0 $0 + 9
        ${EndIf}
        ${If} $Path_Skyrim != $Empty
            ${NSD_CreateCheckBox} 0 $0u 100% 8u "Skyrim"
                Pop $Check_Skyrim
            IntOp $0 $0 + 9
        ${EndIf}
        ${If} $Path_Ex1 != $Empty
            ${NSD_CreateCheckBox} 0 $0u 100% 8u $Path_Ex1
                Pop $Check_Ex1
            IntOp $0 $0 + 9
        ${EndIf}
        ${If} $Path_Ex2 != $Empty
            ${NSD_CreateCheckBox} 0 $0u 100% 8u $Path_Ex2
                Pop $Check_Ex2
            IntOp $0 $0 + 9
        ${EndIf}
        IntOp $0 $0 + 9
        IntOp $1 0 + 0
        ${NSD_CreateCheckBox} $1% $0u 25% 8u "View Readme"
            Pop $Check_Readme
            ${NSD_SetState} $Check_Readme ${BST_CHECKED}
            IntOp $1 $1 + 25
        ${NSD_CreateCheckBox} $1% $0u 75% 8u "Delete files from old Bash versions"
            Pop $Check_DeleteOldFiles
            ${NSD_SetState} $Check_DeleteOldFiles ${BST_CHECKED}
        nsDialogs::Show
    FunctionEnd

    Function PAGE_FINISH_Leave
        ${NSD_GetState} $Check_OB $CheckState_OB
        ${NSD_GetState} $Check_Nehrim $CheckState_Nehrim
        ${NSD_GetState} $Check_Skyrim $CheckState_Skyrim
        ${NSD_GetState} $Check_Ex1 $CheckState_Ex1
        ${NSD_GetState} $Check_Ex2 $CheckState_Ex2

        ${If} $CheckState_OB == ${BST_CHECKED}
            SetOutPath "$Path_OB\Mopy"
            ${If} $CheckState_OB_Py == ${BST_CHECKED}
                ExecShell "open" '"$Path_OB\Mopy\Wrye Bash Launcher.pyw"'
            ${ElseIf} $CheckState_OB_Exe == ${BST_CHECKED}
                ExecShell "open" "$Path_OB\Mopy\Wrye Bash.exe"
            ${EndIf}
        ${EndIf}
        ${If} $CheckState_Nehrim == ${BST_CHECKED}
            SetOutPath "$Path_Nehrim\Mopy"
            ${If} $CheckState_Nehrim_Py == ${BST_CHECKED}
                ExecShell "open" '"$Path_Nehrim\Mopy\Wrye Bash Launcher.pyw"'
            ${ElseIf} $CheckState_Nehrim_Exe == ${BST_CHECKED}
                ExecShell "open" "$Path_Nehrim\Mopy\Wrye Bash.exe"
            ${EndIf}
        ${EndIf}
        ${If} $CheckState_Skyrim == ${BST_CHECKED}
            SetOutPath "$Path_Skyrim\Mopy"
            ${If} $CheckState_Skyrim_Py == ${BST_CHECKED}
                ExecShell "open" '"%Path_Skyrim\Mopy\Wrye Bash Launcher.pyw"'
            ${ElseIf} $CheckState_Skyrim_Exe == ${BST_CHECKED}
                ExecShell "open" "$Path_Skyrim\Mopy\Wrye Bash.exe"
            ${EndIf}
        ${EndIf}
        ${If} $CheckState_Ex1 == ${BST_CHECKED}
            SetOutPath "$Path_Ex1\Mopy"
            ${If} $CheckState_Ex1_Py == ${BST_CHECKED}
                ExecShell "open" '"$Path_Ex1\Mopy\Wrye Bash Launcher.pyw"'
            ${ElseIf} $CheckState_Ex1_Exe == ${BST_CHECKED}
                ExecShell "open" "$Path_Ex1\Mopy\Wrye Bash.exe"
            ${EndIf}
        ${EndIf}
        ${If} $CheckState_Ex2 == ${BST_CHECKED}
            SetOutPath "$Path_Ex2\Mopy"
            ${If} $CheckState_Ex2_Py == ${BST_CHECKED}
                ExecShell "open" '"$Path_Ex2\Mopy\Wrye Bash Launcher.pyw"'
            ${ElseIf} $CheckState_Ex2_Exe == ${BST_CHECKED}
                ExecShell "open" "$Path_Ex2\Mopy\Wrye Bash.exe"
            ${EndIf}
        ${EndIf}
        ${NSD_GetState} $Check_Readme $0
        ${If} $0 == ${BST_CHECKED}
            ${If} $Path_OB != $Empty
                ExecShell "open" "$Path_OB\Mopy\Docs\Wrye Bash General Readme.html"
            ${ElseIf} $Path_Nehrim != $Empty
                ExecShell "open" "$Path_Nehrim\Mopy\Docs\Wrye Bash General Readme.html"
            ${ElseIf} $Path_Skyrim != $Empty
                ExecShell "open" "$Path_Skyrim\Mopy\Docs\Wrye Bash General Readme.html"
            ${ElseIf} $Path_Ex1 != $Empty
                ExecShell "open" "$Path_Ex1\Mopy\Docs\Wrye Bash General Readme.html"
            ${ElseIf} $Path_Ex2 != $Empty
                ExecShell "open" "$Path_Ex2\Mopy\Docs\Wrye Bash General Readme.html"
            ${EndIf}
        ${EndIf}
        ${NSD_GetState} $Check_DeleteOldFiles $0
        ${If} $0 == ${BST_CHECKED}
            ${If} $Path_OB != $Empty
                Delete "$Path_OB\Mopy\Data\Actor Levels\*"
                Delete "$Path_OB\Data\Ini Tweaks\Sound, Enabled.ini"
                Delete "$Path_OB\Data\Ini Tweaks\Sound, Disabled.ini"
                Delete "$Path_OB\Data\Ini Tweaks\Sound Card Channels, 96.ini"
                Delete "$Path_OB\Data\Ini Tweaks\Sound Card Channels, 8.ini"
                Delete "$Path_OB\Data\Ini Tweaks\Sound Card Channels, 64.ini"
                Delete "$Path_OB\Data\Ini Tweaks\Sound Card Channels, 48.ini"
                Delete "$Path_OB\Data\Ini Tweaks\Sound Card Channels, 24.ini"
                Delete "$Path_OB\Data\Ini Tweaks\Sound Card Channels, 192.ini"
                Delete "$Path_OB\Data\Ini Tweaks\Sound Card Channels, 16.ini"
                Delete "$Path_OB\Data\Ini Tweaks\Sound Card Channels, 128.ini"
                Delete "$Path_OB\Data\Ini Tweaks\ShadowMapResolution, 256 [default].ini"
                Delete "$Path_OB\Data\Ini Tweaks\ShadowMapResolution, 1024.ini"
                Delete "$Path_OB\Data\Ini Tweaks\Screenshot, ~ENabled.ini"
                Delete "$Path_OB\Data\Ini Tweaks\Screenshot, ~Disabled.ini"
                Delete "$Path_OB\Data\Ini Tweaks\Save Backups, 5.ini"
                Delete "$Path_OB\Data\Ini Tweaks\Save Backups, 3.ini"
                Delete "$Path_OB\Data\Ini Tweaks\Save Backups, 2.ini"
                Delete "$Path_OB\Data\Ini Tweaks\Save Backups, 1.ini"
                Delete "$Path_OB\Data\Ini Tweaks\Refraction Shader, Disabled.ini"
                Delete "$Path_OB\Data\Ini Tweaks\Refraction Shader, ~Enabled.ini"
                Delete "$Path_OB\Data\Ini Tweaks\Music, Enabled.ini"
                Delete "$Path_OB\Data\Ini Tweaks\Music, Disabled.ini"
                Delete "$Path_OB\Data\Ini Tweaks\Local Map Shader, Disabled.ini"
                Delete "$Path_OB\Data\Ini Tweaks\Local Map Shader, ~Enabled.ini"
                Delete "$Path_OB\Data\Ini Tweaks\Joystick, ~Enabled.ini"
                Delete "$Path_OB\Data\Ini Tweaks\Joystick, ~Disabled.ini"
                Delete "$Path_OB\Data\Ini Tweaks\Intro Movies, Normal.ini"
                Delete "$Path_OB\Data\Ini Tweaks\Intro Movies, Disabled.ini"
                Delete "$Path_OB\Data\Ini Tweaks\Grass, Fade 4k-5k.ini"
                Delete "$Path_OB\Data\Ini Tweaks\Fonts, ~Default.ini"
                Delete "$Path_OB\Data\Ini Tweaks\Fonts 1, ~Default.ini"
                Delete "$Path_OB\Data\Ini Tweaks\Border Regions, Disabled.ini"
                Delete "$Path_OB\Data\Ini Tweaks\Border Regions, ~Enabled.ini"
                Delete "$Path_OB\Data\Ini Tweaks\Autosave, Never.ini"
                Delete "$Path_OB\Data\Ini Tweaks\Autosave, ~Always.ini"
                Delete "$Path_OB\Data\Docs\Bashed Lists.txt"
                Delete "$Path_OB\Data\Docs\Bashed Lists.html"
                Delete "$Path_OB\Data\Bash Patches\PTRoamingNPCs_Names.csv"
                Delete "$Path_OB\Data\Bash Patches\Crowded Roads Revisited_Names.csv"
                Delete "$Path_OB\Data\Bash Patches\Crowded Roads Revisited_Alternate_Names.csv"
                Delete "$Path_OB\Data\Bash Patches\Crowded Roads Revamped_Names.csv"
                Delete "$Path_OB\Data\Bash Patches\Crowded Cities 30_Names.csv"
                Delete "$Path_OB\Data\Bash Patches\Crowded Cities 30_Alternate_Names.csv"
                Delete "$Path_OB\Data\Bash Patches\Crowded Cities 15_Names.csv"
                Delete "$Path_OB\Data\Bash Patches\Crowded Cities 15_Alternate_Names.csv"
                RMDir  "$Path_OB\Mopy\Data\Actor Levels"
                ;As of 294 the below are obsolete locations or files.
                Delete "$Path_OB\Mopy\ScriptParser.p*"
                Delete "$Path_OB\Mopy\lzma.exe"
                Delete "$Path_OB\Mopy\images\*"
                Delete "$Path_OB\Mopy\gpl.txt"
                Delete "$Path_OB\Mopy\Extras\*"
                Delete "$Path_OB\Mopy\DebugLog(Python2.6).bat"
                Delete "$Path_OB\Mopy\Data\Russian.*"
                Delete "$Path_OB\Mopy\Data\pt_opt.*"
                Delete "$Path_OB\Mopy\Data\Oblivion_ids.pkl"
                Delete "$Path_OB\Mopy\Data\Italian.*"
                Delete "$Path_OB\Mopy\Data\de.*"
                Delete "$Path_OB\Mopy\Data\Actor Levels\OOO, 1.23 Uncapped.csv"
                Delete "$Path_OB\Mopy\Data\Actor Levels\OOO, 1.23 Mincapped.csv"
                Delete "$Path_OB\Mopy\cint.p*"
                Delete "$Path_OB\Mopy\CBash.dll"
                Delete "$Path_OB\Mopy\bush.p*"
                Delete "$Path_OB\Mopy\bosh.p*"
                Delete "$Path_OB\Mopy\bolt.p*"
                Delete "$Path_OB\Mopy\bish.p*"
                Delete "$Path_OB\Mopy\belt.p*"
                Delete "$Path_OB\Mopy\bashmon.p*"
                Delete "$Path_OB\Mopy\basher.p*"
                Delete "$Path_OB\Mopy\bash.p*"
                Delete "$Path_OB\Mopy\barg.p*"
                Delete "$Path_OB\Mopy\barb.p*"
                Delete "$Path_OB\Mopy\balt.p*"
                Delete "$Path_OB\Mopy\7z.*"
                RMDir  "$Path_OB\Mopy\images"
                RMDir  "$Path_OB\Mopy\Extras"
                RMDir  "$Path_OB\Mopy\Data\Actor Levels"
                RMDir  "$Path_OB\Mopy\Data"
                ;As of 297 the below are obsolete locations or files.
                Delete "$Path_OB\Mopy\Wrye Bash.txt"
                Delete "$Path_OB\Mopy\Wrye Bash.html"
                ;As of 301 the below are obsolete locations or files.
                Delete "$Path_OB\Mopy\macro\txt\*.txt"
                Delete "$Path_OB\Mopy\macro\py\*.py"
                Delete "$Path_OB\Mopy\macro\py\*.pyc"
                Delete "$Path_OB\Mopy\macro\*.py"
                Delete "$Path_OB\Mopy\macro\*.pyc"
                Delete "$Path_OB\Mopy\bash\installerstabtips.txt"
                Delete "$Path_OB\Mopy\bash\wizSTCo"
                Delete "$Path_OB\Mopy\bash\wizSTC.py"
                Delete "$Path_OB\Mopy\bash\wizSTC.pyc"
                Delete "$Path_OB\Mopy\bash\keywordWIZBAINo"
                Delete "$Path_OB\Mopy\bash\keywordWIZBAIN2o"
                Delete "$Path_OB\Mopy\bash\keywordWIZBAIN2.p*"
                Delete "$Path_OB\Mopy\bash\keywordWIZBAIN.p*"
                Delete "$Path_OB\Mopy\bash\settingsModule.p*"
                Delete "$Path_OB\Mopy\bash\settingsModuleo"
                Delete "$Path_OB\Mopy\bash\images\stc\*.*"
                RMDir  "$Path_OB\Mopy\macro\txt"
                RMDir  "$Path_OB\Mopy\macro\py"
                RMDir  "$Path_OB\Mopy\macro"
                RMDir  "$Path_OB\Mopy\bash\images\stc"
                ; As of 303 the below are obsolete locations or files.
                Delete "$Path_OB\Mopy\templates\Bashed Patch, Skyrim.esp"
                Delete "$Path_OB\Mopy\templates\Bashed Patch, Oblivion.esp"
                Delete "$Path_OB\Mopy\templates\Blank.esp"
                ; As of 305  the below are obsolete locations or files.
                Delete "$Path_OB\Mopy\bash\compiled\7z.exe"
                Delete "$Path_OB\Mopy\bash\compiled\7zUnicode.exe"
                Delete "$Path_OB\Mopy\bash\compiled\7z.dll"
                Delete "$Path_OB\Mopy\bash\compiled\7zCon.sfx"
                Delete "$Path_OB\Mopy\bash\compiled\Microsoft.VC80.CRT\Microsoft.VC80.CTR.manifest"
                Delete "$Path_OB\Mopy\bash\compiled\Microsoft.VC80.CRT\msvcr80.dll"
                RMDir  "$Path_OB\Mopy\bash\compiled\Microsoft.VC80.CRT"
            ${EndIf}
            ${If} $Path_Nehrim != $Empty
                Delete "$Path_Nehrim\Mopy\Data\Actor Levels\*"
                Delete "$Path_Nehrim\Data\Ini Tweaks\Sound, Enabled.ini"
                Delete "$Path_Nehrim\Data\Ini Tweaks\Sound, Disabled.ini"
                Delete "$Path_Nehrim\Data\Ini Tweaks\Sound Card Channels, 96.ini"
                Delete "$Path_Nehrim\Data\Ini Tweaks\Sound Card Channels, 8.ini"
                Delete "$Path_Nehrim\Data\Ini Tweaks\Sound Card Channels, 64.ini"
                Delete "$Path_Nehrim\Data\Ini Tweaks\Sound Card Channels, 48.ini"
                Delete "$Path_Nehrim\Data\Ini Tweaks\Sound Card Channels, 24.ini"
                Delete "$Path_Nehrim\Data\Ini Tweaks\Sound Card Channels, 192.ini"
                Delete "$Path_Nehrim\Data\Ini Tweaks\Sound Card Channels, 16.ini"
                Delete "$Path_Nehrim\Data\Ini Tweaks\Sound Card Channels, 128.ini"
                Delete "$Path_Nehrim\Data\Ini Tweaks\ShadowMapResolution, 256 [default].ini"
                Delete "$Path_Nehrim\Data\Ini Tweaks\ShadowMapResolution, 1024.ini"
                Delete "$Path_Nehrim\Data\Ini Tweaks\Screenshot, ~ENabled.ini"
                Delete "$Path_Nehrim\Data\Ini Tweaks\Screenshot, ~Disabled.ini"
                Delete "$Path_Nehrim\Data\Ini Tweaks\Save Backups, 5.ini"
                Delete "$Path_Nehrim\Data\Ini Tweaks\Save Backups, 3.ini"
                Delete "$Path_Nehrim\Data\Ini Tweaks\Save Backups, 2.ini"
                Delete "$Path_Nehrim\Data\Ini Tweaks\Save Backups, 1.ini"
                Delete "$Path_Nehrim\Data\Ini Tweaks\Refraction Shader, Disabled.ini"
                Delete "$Path_Nehrim\Data\Ini Tweaks\Refraction Shader, ~Enabled.ini"
                Delete "$Path_Nehrim\Data\Ini Tweaks\Music, Enabled.ini"
                Delete "$Path_Nehrim\Data\Ini Tweaks\Music, Disabled.ini"
                Delete "$Path_Nehrim\Data\Ini Tweaks\Local Map Shader, Disabled.ini"
                Delete "$Path_Nehrim\Data\Ini Tweaks\Local Map Shader, ~Enabled.ini"
                Delete "$Path_Nehrim\Data\Ini Tweaks\Joystick, ~Enabled.ini"
                Delete "$Path_Nehrim\Data\Ini Tweaks\Joystick, ~Disabled.ini"
                Delete "$Path_Nehrim\Data\Ini Tweaks\Intro Movies, Normal.ini"
                Delete "$Path_Nehrim\Data\Ini Tweaks\Intro Movies, Disabled.ini"
                Delete "$Path_Nehrim\Data\Ini Tweaks\Grass, Fade 4k-5k.ini"
                Delete "$Path_Nehrim\Data\Ini Tweaks\Fonts, ~Default.ini"
                Delete "$Path_Nehrim\Data\Ini Tweaks\Fonts 1, ~Default.ini"
                Delete "$Path_Nehrim\Data\Ini Tweaks\Border Regions, Disabled.ini"
                Delete "$Path_Nehrim\Data\Ini Tweaks\Border Regions, ~Enabled.ini"
                Delete "$Path_Nehrim\Data\Ini Tweaks\Autosave, Never.ini"
                Delete "$Path_Nehrim\Data\Ini Tweaks\Autosave, ~Always.ini"
                Delete "$Path_Nehrim\Data\Docs\Bashed Lists.txt"
                Delete "$Path_Nehrim\Data\Docs\Bashed Lists.html"
                Delete "$Path_Nehrim\Data\Bash Patches\PTRoamingNPCs_Names.csv"
                Delete "$Path_Nehrim\Data\Bash Patches\Crowded Roads Revisited_Names.csv"
                Delete "$Path_Nehrim\Data\Bash Patches\Crowded Roads Revisited_Alternate_Names.csv"
                Delete "$Path_Nehrim\Data\Bash Patches\Crowded Roads Revamped_Names.csv"
                Delete "$Path_Nehrim\Data\Bash Patches\Crowded Cities 30_Names.csv"
                Delete "$Path_Nehrim\Data\Bash Patches\Crowded Cities 30_Alternate_Names.csv"
                Delete "$Path_Nehrim\Data\Bash Patches\Crowded Cities 15_Names.csv"
                Delete "$Path_Nehrim\Data\Bash Patches\Crowded Cities 15_Alternate_Names.csv"
                RMDir "$Path_Nehrim\Mopy\Data\Actor Levels"
                ;As of 294 the below are obsolete locations or files.
                Delete "$Path_Nehrim\Mopy\ScriptParser.p*"
                Delete "$Path_Nehrim\Mopy\lzma.exe"
                Delete "$Path_Nehrim\Mopy\images\*"
                Delete "$Path_Nehrim\Mopy\gpl.txt"
                Delete "$Path_Nehrim\Mopy\Extras\*"
                Delete "$Path_Nehrim\Mopy\DebugLog(Python2.6).bat"
                Delete "$Path_Nehrim\Mopy\Data\Russian.*"
                Delete "$Path_Nehrim\Mopy\Data\pt_opt.*"
                Delete "$Path_Nehrim\Mopy\Data\Oblivion_ids.pkl"
                Delete "$Path_Nehrim\Mopy\Data\Italian.*"
                Delete "$Path_Nehrim\Mopy\Data\de.*"
                Delete "$Path_Nehrim\Mopy\Data\Actor Levels\OOO, 1.23 Uncapped.csv"
                Delete "$Path_Nehrim\Mopy\Data\Actor Levels\OOO, 1.23 Mincapped.csv"
                Delete "$Path_Nehrim\Mopy\cint.p*"
                Delete "$Path_Nehrim\Mopy\CBash.dll"
                Delete "$Path_Nehrim\Mopy\bush.p*"
                Delete "$Path_Nehrim\Mopy\bosh.p*"
                Delete "$Path_Nehrim\Mopy\bolt.p*"
                Delete "$Path_Nehrim\Mopy\bish.p*"
                Delete "$Path_Nehrim\Mopy\belt.p*"
                Delete "$Path_Nehrim\Mopy\bashmon.p*"
                Delete "$Path_Nehrim\Mopy\basher.p*"
                Delete "$Path_Nehrim\Mopy\bash.p*"
                Delete "$Path_Nehrim\Mopy\barg.p*"
                Delete "$Path_Nehrim\Mopy\barb.p*"
                Delete "$Path_Nehrim\Mopy\balt.p*"
                Delete "$Path_Nehrim\Mopy\7z.*"
                RMDir  "$Path_Nehrim\Mopy\images"
                RMDir  "$Path_Nehrim\Mopy\Extras"
                RMDir  "$Path_Nehrim\Mopy\Data\Actor Levels"
                RMDir  "$Path_Nehrim\Mopy\Data"
                ;As of 297 the below are obsolete locations or files.
                Delete "$Path_Nehrim\Mopy\Wrye Bash.txt"
                Delete "$Path_Nehrim\Mopy\Wrye Bash.html"
                ;As of 301 the below are obsolete locations or files.
                Delete "$Path_Nehrim\Mopy\macro\txt\*.txt"
                Delete "$Path_Nehrim\Mopy\macro\py\*.py"
                Delete "$Path_Nehrim\Mopy\macro\py\*.pyc"
                Delete "$Path_Nehrim\Mopy\macro\*.py"
                Delete "$Path_Nehrim\Mopy\macro\*.pyc"
                Delete "$Path_Nehrim\Mopy\bash\installerstabtips.txt"
                Delete "$Path_Nehrim\Mopy\bash\wizSTCo"
                Delete "$Path_Nehrim\Mopy\bash\wizSTC.py"
                Delete "$Path_Nehrim\Mopy\bash\wizSTC.pyc"
                Delete "$Path_Nehrim\Mopy\bash\keywordWIZBAINo"
                Delete "$Path_Nehrim\Mopy\bash\keywordWIZBAIN2o"
                Delete "$Path_Nehrim\Mopy\bash\keywordWIZBAIN2.p*"
                Delete "$Path_Nehrim\Mopy\bash\keywordWIZBAIN.p*"
                Delete "$Path_Nehrim\Mopy\bash\settingsModule.p*"
                Delete "$Path_Nehrim\Mopy\bash\settingsModuleo"
                Delete "$Path_Nehrim\Mopy\bash\images\stc\*.*"
                RMDir  "$Path_Nehrim\Mopy\macro\txt"
                RMDir  "$Path_Nehrim\Mopy\macro\py"
                RMDir  "$Path_Nehrim\Mopy\macro"
                RMDir  "$Path_Nehrim\Mopy\bash\images\stc"
                ; As of 303 the below are obsolete locations or files.
                Delete "$Path_Nehrim\Mopy\templates\Bashed Patch, Skyrim.esp"
                Delete "$Path_Nehrim\Mopy\templates\Bashed Patch, Oblivion.esp"
                Delete "$Path_Nehrim\Mopy\templates\Blank.esp"
                ; As of 305  the below are obsolete locations or files.
                Delete "$Path_OB\Mopy\bash\compiled\7z.exe"
                Delete "$Path_OB\Mopy\bash\compiled\7zUnicode.exe"
                Delete "$Path_OB\Mopy\bash\compiled\7z.dll"
                Delete "$Path_OB\Mopy\bash\compiled\7zCon.sfx"
                Delete "$Path_OB\Mopy\bash\compiled\Microsoft.VC80.CRT\Microsoft.VC80.CTR.manifest"
                Delete "$Path_OB\Mopy\bash\compiled\Microsoft.VC80.CRT\msvcr80.dll"
                RMDir  "$Path_OB\Mopy\bash\compiled\Microsoft.VC80.CRT"
            ${EndIf}
            ${If} $Path_Skyrim != $Empty
                Delete "$Path_Skyrim\Mopy\Data\Actor Levels\*"
                Delete "$Path_Skyrim\Data\Ini Tweaks\Sound, Enabled.ini"
                Delete "$Path_Skyrim\Data\Ini Tweaks\Sound, Disabled.ini"
                Delete "$Path_Skyrim\Data\Ini Tweaks\Sound Card Channels, 96.ini"
                Delete "$Path_Skyrim\Data\Ini Tweaks\Sound Card Channels, 8.ini"
                Delete "$Path_Skyrim\Data\Ini Tweaks\Sound Card Channels, 64.ini"
                Delete "$Path_Skyrim\Data\Ini Tweaks\Sound Card Channels, 48.ini"
                Delete "$Path_Skyrim\Data\Ini Tweaks\Sound Card Channels, 24.ini"
                Delete "$Path_Skyrim\Data\Ini Tweaks\Sound Card Channels, 192.ini"
                Delete "$Path_Skyrim\Data\Ini Tweaks\Sound Card Channels, 16.ini"
                Delete "$Path_Skyrim\Data\Ini Tweaks\Sound Card Channels, 128.ini"
                Delete "$Path_Skyrim\Data\Ini Tweaks\ShadowMapResolution, 256 [default].ini"
                Delete "$Path_Skyrim\Data\Ini Tweaks\ShadowMapResolution, 1024.ini"
                Delete "$Path_Skyrim\Data\Ini Tweaks\Screenshot, ~ENabled.ini"
                Delete "$Path_Skyrim\Data\Ini Tweaks\Screenshot, ~Disabled.ini"
                Delete "$Path_Skyrim\Data\Ini Tweaks\Save Backups, 5.ini"
                Delete "$Path_Skyrim\Data\Ini Tweaks\Save Backups, 3.ini"
                Delete "$Path_Skyrim\Data\Ini Tweaks\Save Backups, 2.ini"
                Delete "$Path_Skyrim\Data\Ini Tweaks\Save Backups, 1.ini"
                Delete "$Path_Skyrim\Data\Ini Tweaks\Refraction Shader, Disabled.ini"
                Delete "$Path_Skyrim\Data\Ini Tweaks\Refraction Shader, ~Enabled.ini"
                Delete "$Path_Skyrim\Data\Ini Tweaks\Music, Enabled.ini"
                Delete "$Path_Skyrim\Data\Ini Tweaks\Music, Disabled.ini"
                Delete "$Path_Skyrim\Data\Ini Tweaks\Local Map Shader, Disabled.ini"
                Delete "$Path_Skyrim\Data\Ini Tweaks\Local Map Shader, ~Enabled.ini"
                Delete "$Path_Skyrim\Data\Ini Tweaks\Joystick, ~Enabled.ini"
                Delete "$Path_Skyrim\Data\Ini Tweaks\Joystick, ~Disabled.ini"
                Delete "$Path_Skyrim\Data\Ini Tweaks\Intro Movies, Normal.ini"
                Delete "$Path_Skyrim\Data\Ini Tweaks\Intro Movies, Disabled.ini"
                Delete "$Path_Skyrim\Data\Ini Tweaks\Grass, Fade 4k-5k.ini"
                Delete "$Path_Skyrim\Data\Ini Tweaks\Fonts, ~Default.ini"
                Delete "$Path_Skyrim\Data\Ini Tweaks\Fonts 1, ~Default.ini"
                Delete "$Path_Skyrim\Data\Ini Tweaks\Border Regions, Disabled.ini"
                Delete "$Path_Skyrim\Data\Ini Tweaks\Border Regions, ~Enabled.ini"
                Delete "$Path_Skyrim\Data\Ini Tweaks\Autosave, Never.ini"
                Delete "$Path_Skyrim\Data\Ini Tweaks\Autosave, ~Always.ini"
                Delete "$Path_Skyrim\Data\Docs\Bashed Lists.txt"
                Delete "$Path_Skyrim\Data\Docs\Bashed Lists.html"
                Delete "$Path_Skyrim\Data\Bash Patches\PTRoamingNPCs_Names.csv"
                Delete "$Path_Skyrim\Data\Bash Patches\Crowded Roads Revisited_Names.csv"
                Delete "$Path_Skyrim\Data\Bash Patches\Crowded Roads Revisited_Alternate_Names.csv"
                Delete "$Path_Skyrim\Data\Bash Patches\Crowded Roads Revamped_Names.csv"
                Delete "$Path_Skyrim\Data\Bash Patches\Crowded Cities 30_Names.csv"
                Delete "$Path_Skyrim\Data\Bash Patches\Crowded Cities 30_Alternate_Names.csv"
                Delete "$Path_Skyrim\Data\Bash Patches\Crowded Cities 15_Names.csv"
                Delete "$Path_Skyrim\Data\Bash Patches\Crowded Cities 15_Alternate_Names.csv"
                Delete "$Path_Skyrim\Data\ArchiveInvalidationInvalidated!.bsa"
                RMDir  "$Path_Skyrim\Mopy\Data\Actor Levels"
                ;As of 294 the below are obsolete locations or files.
                Delete "$Path_Skyrim\Mopy\ScriptParser.p*"
                Delete "$Path_Skyrim\Mopy\lzma.exe"
                Delete "$Path_Skyrim\Mopy\images\*"
                Delete "$Path_Skyrim\Mopy\gpl.txt"
                Delete "$Path_Skyrim\Mopy\Extras\*"
                Delete "$Path_Skyrim\Mopy\DebugLog(Python2.6).bat"
                Delete "$Path_Skyrim\Mopy\Data\Russian.*"
                Delete "$Path_Skyrim\Mopy\Data\pt_opt.*"
                Delete "$Path_Skyrim\Mopy\Data\Oblivion_ids.pkl"
                Delete "$Path_Skyrim\Mopy\Data\Italian.*"
                Delete "$Path_Skyrim\Mopy\Data\de.*"
                Delete "$Path_Skyrim\Mopy\Data\Actor Levels\OOO, 1.23 Uncapped.csv"
                Delete "$Path_Skyrim\Mopy\Data\Actor Levels\OOO, 1.23 Mincapped.csv"
                Delete "$Path_Skyrim\Mopy\cint.p*"
                Delete "$Path_Skyrim\Mopy\CBash.dll"
                Delete "$Path_Skyrim\Mopy\bush.p*"
                Delete "$Path_Skyrim\Mopy\bosh.p*"
                Delete "$Path_Skyrim\Mopy\bolt.p*"
                Delete "$Path_Skyrim\Mopy\bish.p*"
                Delete "$Path_Skyrim\Mopy\belt.p*"
                Delete "$Path_Skyrim\Mopy\bashmon.p*"
                Delete "$Path_Skyrim\Mopy\basher.p*"
                Delete "$Path_Skyrim\Mopy\bash.p*"
                Delete "$Path_Skyrim\Mopy\barg.p*"
                Delete "$Path_Skyrim\Mopy\barb.p*"
                Delete "$Path_Skyrim\Mopy\balt.p*"
                Delete "$Path_Skyrim\Mopy\7z.*"
                RMDir  "$Path_Skyrim\Mopy\images"
                RMDir  "$Path_Skyrim\Mopy\Extras"
                RMDir  "$Path_Skyrim\Mopy\Data\Actor Levels"
                RMDir  "$Path_Skyrim\Mopy\Data"
                ;As of 297 the below are obsolete locations or files.
                Delete "$Path_Skyrim\Mopy\Wrye Bash.txt"
                Delete "$Path_Skyrim\Mopy\Wrye Bash.html"
                ;As of 301 the below are obsolete locations or files.
                Delete "$Path_Skyrim\Mopy\macro\txt\*.txt"
                Delete "$Path_Skyrim\Mopy\macro\py\*.py"
                Delete "$Path_Skyrim\Mopy\macro\py\*.pyc"
                Delete "$Path_Skyrim\Mopy\macro\*.py"
                Delete "$Path_Skyrim\Mopy\macro\*.pyc"
                Delete "$Path_Skyrim\Mopy\bash\installerstabtips.txt"
                Delete "$Path_Skyrim\Mopy\bash\wizSTCo"
                Delete "$Path_Skyrim\Mopy\bash\wizSTC.py"
                Delete "$Path_Skyrim\Mopy\bash\wizSTC.pyc"
                Delete "$Path_Skyrim\Mopy\bash\keywordWIZBAINo"
                Delete "$Path_Skyrim\Mopy\bash\keywordWIZBAIN2o"
                Delete "$Path_Skyrim\Mopy\bash\keywordWIZBAIN2.p*"
                Delete "$Path_Skyrim\Mopy\bash\keywordWIZBAIN.p*"
                Delete "$Path_Skyrim\Mopy\bash\settingsModule.p*"
                Delete "$Path_Skyrim\Mopy\bash\settingsModuleo"
                Delete "$Path_Skyrim\Mopy\bash\images\stc\*.*"
                RMDir  "$Path_Skyrim\Mopy\macro\txt"
                RMDir  "$Path_Skyrim\Mopy\macro\py"
                RMDir  "$Path_Skyrim\Mopy\macro"
                RMDir  "$Path_Skyrim\Mopy\bash\images\stc"
                ; As of 303 the below are obsolete locations or files.
                Delete "$Path_Skyrim\Mopy\templates\Bashed Patch, Skyrim.esp"
                Delete "$Path_Skyrim\Mopy\templates\Bashed Patch, Oblivion.esp"
                Delete "$Path_Skyrim\Mopy\templates\Blank.esp"
                ; As of 305  the below are obsolete locations or files.
                Delete "$Path_OB\Mopy\bash\compiled\7z.exe"
                Delete "$Path_OB\Mopy\bash\compiled\7zUnicode.exe"
                Delete "$Path_OB\Mopy\bash\compiled\7z.dll"
                Delete "$Path_OB\Mopy\bash\compiled\7zCon.sfx"
                Delete "$Path_OB\Mopy\bash\compiled\Microsoft.VC80.CRT\Microsoft.VC80.CTR.manifest"
                Delete "$Path_OB\Mopy\bash\compiled\Microsoft.VC80.CRT\msvcr80.dll"
                RMDir  "$Path_OB\Mopy\bash\compiled\Microsoft.VC80.CRT"
            ${EndIf}
            ${If} $Path_Ex1 != $Empty
                Delete "$Path_Ex1\Mopy\Data\Actor Levels\*"
                Delete "$Path_Ex1\Data\Ini Tweaks\Sound, Enabled.ini"
                Delete "$Path_Ex1\Data\Ini Tweaks\Sound, Disabled.ini"
                Delete "$Path_Ex1\Data\Ini Tweaks\Sound Card Channels, 96.ini"
                Delete "$Path_Ex1\Data\Ini Tweaks\Sound Card Channels, 8.ini"
                Delete "$Path_Ex1\Data\Ini Tweaks\Sound Card Channels, 64.ini"
                Delete "$Path_Ex1\Data\Ini Tweaks\Sound Card Channels, 48.ini"
                Delete "$Path_Ex1\Data\Ini Tweaks\Sound Card Channels, 24.ini"
                Delete "$Path_Ex1\Data\Ini Tweaks\Sound Card Channels, 192.ini"
                Delete "$Path_Ex1\Data\Ini Tweaks\Sound Card Channels, 16.ini"
                Delete "$Path_Ex1\Data\Ini Tweaks\Sound Card Channels, 128.ini"
                Delete "$Path_Ex1\Data\Ini Tweaks\ShadowMapResolution, 256 [default].ini"
                Delete "$Path_Ex1\Data\Ini Tweaks\ShadowMapResolution, 1024.ini"
                Delete "$Path_Ex1\Data\Ini Tweaks\Screenshot, ~ENabled.ini"
                Delete "$Path_Ex1\Data\Ini Tweaks\Screenshot, ~Disabled.ini"
                Delete "$Path_Ex1\Data\Ini Tweaks\Save Backups, 5.ini"
                Delete "$Path_Ex1\Data\Ini Tweaks\Save Backups, 3.ini"
                Delete "$Path_Ex1\Data\Ini Tweaks\Save Backups, 2.ini"
                Delete "$Path_Ex1\Data\Ini Tweaks\Save Backups, 1.ini"
                Delete "$Path_Ex1\Data\Ini Tweaks\Refraction Shader, Disabled.ini"
                Delete "$Path_Ex1\Data\Ini Tweaks\Refraction Shader, ~Enabled.ini"
                Delete "$Path_Ex1\Data\Ini Tweaks\Music, Enabled.ini"
                Delete "$Path_Ex1\Data\Ini Tweaks\Music, Disabled.ini"
                Delete "$Path_Ex1\Data\Ini Tweaks\Local Map Shader, Disabled.ini"
                Delete "$Path_Ex1\Data\Ini Tweaks\Local Map Shader, ~Enabled.ini"
                Delete "$Path_Ex1\Data\Ini Tweaks\Joystick, ~Enabled.ini"
                Delete "$Path_Ex1\Data\Ini Tweaks\Joystick, ~Disabled.ini"
                Delete "$Path_Ex1\Data\Ini Tweaks\Intro Movies, Normal.ini"
                Delete "$Path_Ex1\Data\Ini Tweaks\Intro Movies, Disabled.ini"
                Delete "$Path_Ex1\Data\Ini Tweaks\Grass, Fade 4k-5k.ini"
                Delete "$Path_Ex1\Data\Ini Tweaks\Fonts, ~Default.ini"
                Delete "$Path_Ex1\Data\Ini Tweaks\Fonts 1, ~Default.ini"
                Delete "$Path_Ex1\Data\Ini Tweaks\Border Regions, Disabled.ini"
                Delete "$Path_Ex1\Data\Ini Tweaks\Border Regions, ~Enabled.ini"
                Delete "$Path_Ex1\Data\Ini Tweaks\Autosave, Never.ini"
                Delete "$Path_Ex1\Data\Ini Tweaks\Autosave, ~Always.ini"
                Delete "$Path_Ex1\Data\Docs\Bashed Lists.txt"
                Delete "$Path_Ex1\Data\Docs\Bashed Lists.html"
                Delete "$Path_Ex1\Data\Bash Patches\PTRoamingNPCs_Names.csv"
                Delete "$Path_Ex1\Data\Bash Patches\Crowded Roads Revisited_Names.csv"
                Delete "$Path_Ex1\Data\Bash Patches\Crowded Roads Revisited_Alternate_Names.csv"
                Delete "$Path_Ex1\Data\Bash Patches\Crowded Roads Revamped_Names.csv"
                Delete "$Path_Ex1\Data\Bash Patches\Crowded Cities 30_Names.csv"
                Delete "$Path_Ex1\Data\Bash Patches\Crowded Cities 30_Alternate_Names.csv"
                Delete "$Path_Ex1\Data\Bash Patches\Crowded Cities 15_Names.csv"
                Delete "$Path_Ex1\Data\Bash Patches\Crowded Cities 15_Alternate_Names.csv"
                RMDir "$Path_Ex1\Mopy\Data\Actor Levels"
                ;As of 294 the below are obsolete locations or files.
                Delete "$Path_Ex1\Mopy\ScriptParser.p*"
                Delete "$Path_Ex1\Mopy\lzma.exe"
                Delete "$Path_Ex1\Mopy\images\*"
                Delete "$Path_Ex1\Mopy\gpl.txt"
                Delete "$Path_Ex1\Mopy\Extras\*"
                Delete "$Path_Ex1\Mopy\DebugLog(Python2.6).bat"
                Delete "$Path_Ex1\Mopy\Data\Russian.*"
                Delete "$Path_Ex1\Mopy\Data\pt_opt.*"
                Delete "$Path_Ex1\Mopy\Data\Oblivion_ids.pkl"
                Delete "$Path_Ex1\Mopy\Data\Italian.*"
                Delete "$Path_Ex1\Mopy\Data\de.*"
                Delete "$Path_Ex1\Mopy\Data\Actor Levels\OOO, 1.23 Uncapped.csv"
                Delete "$Path_Ex1\Mopy\Data\Actor Levels\OOO, 1.23 Mincapped.csv"
                Delete "$Path_Ex1\Mopy\cint.p*"
                Delete "$Path_Ex1\Mopy\CBash.dll"
                Delete "$Path_Ex1\Mopy\bush.p*"
                Delete "$Path_Ex1\Mopy\bosh.p*"
                Delete "$Path_Ex1\Mopy\bolt.p*"
                Delete "$Path_Ex1\Mopy\bish.p*"
                Delete "$Path_Ex1\Mopy\belt.p*"
                Delete "$Path_Ex1\Mopy\bashmon.p*"
                Delete "$Path_Ex1\Mopy\basher.p*"
                Delete "$Path_Ex1\Mopy\bash.p*"
                Delete "$Path_Ex1\Mopy\barg.p*"
                Delete "$Path_Ex1\Mopy\barb.p*"
                Delete "$Path_Ex1\Mopy\balt.p*"
                Delete "$Path_Ex1\Mopy\7z.*"
                RMDir  "$Path_Ex1\Mopy\images"
                RMDir  "$Path_Ex1\Mopy\Extras"
                RMDir  "$Path_Ex1\Mopy\Data\Actor Levels"
                RMDir  "$Path_Ex1\Mopy\Data"
                ;As of 297 the below are obsolete locations or files.
                Delete "$Path_Ex1\Mopy\Wrye Bash.txt"
                Delete "$Path_Ex1\Mopy\Wrye Bash.html"
                ;As of 301 the below are obsolete locations or files.
                Delete "$Path_Ex1\Mopy\macro\txt\*.txt"
                Delete "$Path_Ex1\Mopy\macro\py\*.py"
                Delete "$Path_Ex1\Mopy\macro\py\*.pyc"
                Delete "$Path_Ex1\Mopy\macro\*.py"
                Delete "$Path_Ex1\Mopy\macro\*.pyc"
                Delete "$Path_Ex1\Mopy\bash\installerstabtips.txt"
                Delete "$Path_Ex1\Mopy\bash\wizSTCo"
                Delete "$Path_Ex1\Mopy\bash\wizSTC.py"
                Delete "$Path_Ex1\Mopy\bash\wizSTC.pyc"
                Delete "$Path_Ex1\Mopy\bash\keywordWIZBAINo"
                Delete "$Path_Ex1\Mopy\bash\keywordWIZBAIN2o"
                Delete "$Path_Ex1\Mopy\bash\keywordWIZBAIN2.p*"
                Delete "$Path_Ex1\Mopy\bash\keywordWIZBAIN.p*"
                Delete "$Path_Ex1\Mopy\bash\settingsModule.p*"
                Delete "$Path_Ex1\Mopy\bash\settingsModuleo"
                Delete "$Path_Ex1\Mopy\bash\images\stc\*.*"
                RMDir  "$Path_Ex1\Mopy\macro\txt"
                RMDir  "$Path_Ex1\Mopy\macro\py"
                RMDir  "$Path_Ex1\Mopy\macro"
                RMDir  "$Path_Ex1\Mopy\bash\images\stc"
                ; As of 303 the below are obsolete locations or files.
                Delete "$Path_Ex1\Mopy\templates\Bashed Patch, Skyrim.esp"
                Delete "$Path_Ex1\Mopy\templates\Bashed Patch, Oblivion.esp"
                Delete "$Path_Ex1\Mopy\templates\Blank.esp"
                ; As of 305  the below are obsolete locations or files.
                Delete "$Path_OB\Mopy\bash\compiled\7z.exe"
                Delete "$Path_OB\Mopy\bash\compiled\7zUnicode.exe"
                Delete "$Path_OB\Mopy\bash\compiled\7z.dll"
                Delete "$Path_OB\Mopy\bash\compiled\7zCon.sfx"
                Delete "$Path_OB\Mopy\bash\compiled\Microsoft.VC80.CRT\Microsoft.VC80.CTR.manifest"
                Delete "$Path_OB\Mopy\bash\compiled\Microsoft.VC80.CRT\msvcr80.dll"
                RMDir  "$Path_OB\Mopy\bash\compiled\Microsoft.VC80.CRT"

            ${EndIf}
            ${If} $Path_Ex2 != $Empty
                Delete "$Path_Ex2\Mopy\Data\Actor Levels\*"
                Delete "$Path_Ex2\Data\Ini Tweaks\Sound, Enabled.ini"
                Delete "$Path_Ex2\Data\Ini Tweaks\Sound, Disabled.ini"
                Delete "$Path_Ex2\Data\Ini Tweaks\Sound Card Channels, 96.ini"
                Delete "$Path_Ex2\Data\Ini Tweaks\Sound Card Channels, 8.ini"
                Delete "$Path_Ex2\Data\Ini Tweaks\Sound Card Channels, 64.ini"
                Delete "$Path_Ex2\Data\Ini Tweaks\Sound Card Channels, 48.ini"
                Delete "$Path_Ex2\Data\Ini Tweaks\Sound Card Channels, 24.ini"
                Delete "$Path_Ex2\Data\Ini Tweaks\Sound Card Channels, 192.ini"
                Delete "$Path_Ex2\Data\Ini Tweaks\Sound Card Channels, 16.ini"
                Delete "$Path_Ex2\Data\Ini Tweaks\Sound Card Channels, 128.ini"
                Delete "$Path_Ex2\Data\Ini Tweaks\Sound Card Channels, ~ [Oblivion].ini"
                Delete "$Path_Ex2\Data\Ini Tweaks\Sound Card Channels,  [Oblivion].ini"
                Delete "$Path_Ex2\Data\Ini Tweaks\ShadowMapResolution, 256 [default].ini"
                Delete "$Path_Ex2\Data\Ini Tweaks\ShadowMapResolution, 1024.ini"
                Delete "$Path_Ex2\Data\Ini Tweaks\Screenshot, ~ENabled.ini"
                Delete "$Path_Ex2\Data\Ini Tweaks\Screenshot, ~Disabled.ini"
                Delete "$Path_Ex2\Data\Ini Tweaks\Save Backups, 5.ini"
                Delete "$Path_Ex2\Data\Ini Tweaks\Save Backups, 3.ini"
                Delete "$Path_Ex2\Data\Ini Tweaks\Save Backups, 2.ini"
                Delete "$Path_Ex2\Data\Ini Tweaks\Save Backups, 1.ini"
                Delete "$Path_Ex2\Data\Ini Tweaks\Refraction Shader, Disabled.ini"
                Delete "$Path_Ex2\Data\Ini Tweaks\Refraction Shader, ~Enabled.ini"
                Delete "$Path_Ex2\Data\Ini Tweaks\Music, Enabled.ini"
                Delete "$Path_Ex2\Data\Ini Tweaks\Music, Disabled.ini"
                Delete "$Path_Ex2\Data\Ini Tweaks\Local Map Shader, Disabled.ini"
                Delete "$Path_Ex2\Data\Ini Tweaks\Local Map Shader, ~Enabled.ini"
                Delete "$Path_Ex2\Data\Ini Tweaks\Joystick, ~Enabled.ini"
                Delete "$Path_Ex2\Data\Ini Tweaks\Joystick, ~Disabled.ini"
                Delete "$Path_Ex2\Data\Ini Tweaks\Intro Movies, Normal.ini"
                Delete "$Path_Ex2\Data\Ini Tweaks\Intro Movies, Disabled.ini"
                Delete "$Path_Ex2\Data\Ini Tweaks\Grass, Fade 4k-5k.ini"
                Delete "$Path_Ex2\Data\Ini Tweaks\Fonts, ~Default.ini"
                Delete "$Path_Ex2\Data\Ini Tweaks\Fonts 1, ~Default.ini"
                Delete "$Path_Ex2\Data\Ini Tweaks\Border Regions, Disabled.ini"
                Delete "$Path_Ex2\Data\Ini Tweaks\Border Regions, ~Enabled.ini"
                Delete "$Path_Ex2\Data\Ini Tweaks\Autosave, Never.ini"
                Delete "$Path_Ex2\Data\Ini Tweaks\Autosave, ~Always.ini"
                Delete "$Path_Ex2\Data\Docs\Bashed Lists.txt"
                Delete "$Path_Ex2\Data\Docs\Bashed Lists.html"
                Delete "$Path_Ex2\Data\Bash Patches\PTRoamingNPCs_Names.csv"
                Delete "$Path_Ex2\Data\Bash Patches\Crowded Roads Revisited_Names.csv"
                Delete "$Path_Ex2\Data\Bash Patches\Crowded Roads Revisited_Alternate_Names.csv"
                Delete "$Path_Ex2\Data\Bash Patches\Crowded Roads Revamped_Names.csv"
                Delete "$Path_Ex2\Data\Bash Patches\Crowded Cities 30_Names.csv"
                Delete "$Path_Ex2\Data\Bash Patches\Crowded Cities 30_Alternate_Names.csv"
                Delete "$Path_Ex2\Data\Bash Patches\Crowded Cities 15_Names.csv"
                Delete "$Path_Ex2\Data\Bash Patches\Crowded Cities 15_Alternate_Names.csv"
                RMDir "$Path_Ex2\Mopy\Data\Actor Levels"
                ;As of 294 the below are obsolete locations or files.
                Delete "$Path_Ex2\Mopy\ScriptParser.p*"
                Delete "$Path_Ex2\Mopy\lzma.exe"
                Delete "$Path_Ex2\Mopy\images\*"
                Delete "$Path_Ex2\Mopy\gpl.txt"
                Delete "$Path_Ex2\Mopy\Extras\*"
                Delete "$Path_Ex2\Mopy\DebugLog(Python2.6).bat"
                Delete "$Path_Ex2\Mopy\Data\Russian.*"
                Delete "$Path_Ex2\Mopy\Data\pt_opt.*"
                Delete "$Path_Ex2\Mopy\Data\Oblivion_ids.pkl"
                Delete "$Path_Ex2\Mopy\Data\Italian.*"
                Delete "$Path_Ex2\Mopy\Data\de.*"
                Delete "$Path_Ex2\Mopy\Data\Actor Levels\OOO, 1.23 Uncapped.csv"
                Delete "$Path_Ex2\Mopy\Data\Actor Levels\OOO, 1.23 Mincapped.csv"
                Delete "$Path_Ex2\Mopy\cint.p*"
                Delete "$Path_Ex2\Mopy\CBash.dll"
                Delete "$Path_Ex2\Mopy\bush.p*"
                Delete "$Path_Ex2\Mopy\bosh.p*"
                Delete "$Path_Ex2\Mopy\bolt.p*"
                Delete "$Path_Ex2\Mopy\bish.p*"
                Delete "$Path_Ex2\Mopy\belt.p*"
                Delete "$Path_Ex2\Mopy\bashmon.p*"
                Delete "$Path_Ex2\Mopy\basher.p*"
                Delete "$Path_Ex2\Mopy\bash.p*"
                Delete "$Path_Ex2\Mopy\barg.p*"
                Delete "$Path_Ex2\Mopy\barb.p*"
                Delete "$Path_Ex2\Mopy\balt.p*"
                Delete "$Path_Ex2\Mopy\7z.*"
                RMDir  "$Path_Ex2\Mopy\images"
                RMDir  "$Path_Ex2\Mopy\Extras"
                RMDir  "$Path_Ex2\Mopy\Data\Actor Levels"
                RMDir  "$Path_Ex2\Mopy\Data"
                ;As of 297 the below are obsolete locations or files.
                Delete "$Path_Ex2\Mopy\Wrye Bash.txt"
                Delete "$Path_Ex2\Mopy\Wrye Bash.html"
                ;As of 301 the below are obsolete locations or files.
                Delete "$Path_Ex2\Mopy\macro\txt\*.txt"
                Delete "$Path_Ex2\Mopy\macro\py\*.py"
                Delete "$Path_Ex2\Mopy\macro\py\*.pyc"
                Delete "$Path_Ex2\Mopy\macro\*.py"
                Delete "$Path_Ex2\Mopy\macro\*.pyc"
                Delete "$Path_Ex2\Mopy\bash\installerstabtips.txt"
                Delete "$Path_Ex2\Mopy\bash\wizSTCo"
                Delete "$Path_Ex2\Mopy\bash\wizSTC.py"
                Delete "$Path_Ex2\Mopy\bash\wizSTC.pyc"
                Delete "$Path_Ex2\Mopy\bash\keywordWIZBAINo"
                Delete "$Path_Ex2\Mopy\bash\keywordWIZBAIN2o"
                Delete "$Path_Ex2\Mopy\bash\keywordWIZBAIN2.p*"
                Delete "$Path_Ex2\Mopy\bash\keywordWIZBAIN.p*"
                Delete "$Path_Ex2\Mopy\bash\settingsModule.p*"
                Delete "$Path_Ex2\Mopy\bash\settingsModuleo"
                Delete "$Path_Ex2\Mopy\bash\images\stc\*.*"
                RMDir  "$Path_Ex2\Mopy\macro\txt"
                RMDir  "$Path_Ex2\Mopy\macro\py"
                RMDir  "$Path_Ex2\Mopy\macro"
                RMDir  "$Path_Ex2\Mopy\bash\images\stc"
                ; As of 303 the below are obsolete locations or files.
                Delete "$Path_Ex2\Mopy\templates\Bashed Patch, Skyrim.esp"
                Delete "$Path_Ex2\Mopy\templates\Bashed Patch, Oblivion.esp"
                Delete "$Path_Ex2\Mopy\templates\Blank.esp"
                ; As of 305  the below are obsolete locations or files.
                Delete "$Path_OB\Mopy\bash\compiled\7z.exe"
                Delete "$Path_OB\Mopy\bash\compiled\7zUnicode.exe"
                Delete "$Path_OB\Mopy\bash\compiled\7z.dll"
                Delete "$Path_OB\Mopy\bash\compiled\7zCon.sfx"
                Delete "$Path_OB\Mopy\bash\compiled\Microsoft.VC80.CRT\Microsoft.VC80.CTR.manifest"
                Delete "$Path_OB\Mopy\bash\compiled\Microsoft.VC80.CRT\msvcr80.dll"
                RMDir  "$Path_OB\Mopy\bash\compiled\Microsoft.VC80.CRT"
                ${EndIf}
        ${EndIf}
    FunctionEnd


;----------------------------- Custom Uninstallation Pages and their Functions:
    Function un.PAGE_SELECT_GAMES
        !insertmacro MUI_HEADER_TEXT $(PAGE_INSTALLLOCATIONS_TITLE) $(unPAGE_SELECT_GAMES_SUBTITLE)
        GetFunctionAddress $unFunction_Browse un.OnClick_Browse

        nsDialogs::Create 1018
            Pop $Dialog
        ${If} $Dialog == error
            Abort
            ${EndIf}

        ${NSD_CreateLabel} 0 0 100% 8u "Please select which game(s)/extra location(s) and version(s) to uninstall Wrye Bash from:"
        Pop $Label

        IntOp $0 0 + 9
        ${If} $Path_OB != $Empty
            ${NSD_CreateCheckBox} 0 $0u 100% 13u "&Oblivion"
                Pop $Check_OB
                ${NSD_SetState} $Check_OB $CheckState_OB
            IntOp $0 $0 + 13
            ${NSD_CreateDirRequest} 0 $0u 90% 13u "$Path_OB"
                Pop $PathDialogue_OB
            ${NSD_CreateBrowseButton} -10% $0u 5% 13u "..."
                Pop $Browse_OB
                nsDialogs::OnClick $Browse_OB $Function_Browse
            IntOp $0 $0 + 13
        ${EndIf}
        ${If} $Path_Nehrim != $Empty
            ${NSD_CreateCheckBox} 0 $0u 100% 13u "Nehrim"
                Pop $Check_Nehrim
                ${NSD_SetState} $Check_Nehrim $CheckState_Nehrim
            IntOp $0 $0 + 13
            ${NSD_CreateDirRequest} 0 $0u 90% 13u "$Path_Nehrim"
                Pop $PathDialogue_Nehrim
            ${NSD_CreateBrowseButton} -10% $0u 5% 13u "..."
                Pop $Browse_Nehrim
                nsDialogs::OnClick $Browse_Nehrim $Function_Browse
            IntOp $0 $0 + 13
        ${EndIf}
        ${If} $Path_Skyrim != $Empty
            ${NSD_CreateCheckBox} 0 $0u 100% 13u "&Skyrim"
                Pop $Check_Skyrim
                ${NSD_SetState} $Check_Skyrim $CheckState_Skyrim
            IntOp $0 $0 + 13
            ${NSD_CreateDirRequest} 0 $0u 90% 13u "$Path_Skyrim"
                Pop $PathDialogue_Skyrim
            ${NSD_CreateBrowseButton} -10% %0u 5% 13u "..."
                Pop $Browse_Skyrim
                nsDialogs::OnClick $Browse_Skyrim $Function_Browse
            IntOp $0 $0 + 13
        ${EndIf}
        ${If} $Path_Ex1 != $Empty
            ${NSD_CreateCheckBox} 0 $0u 100% 13u "Extra Location 1"
                Pop $Check_Ex1
                ${NSD_SetState} $Check_Ex1 $CheckState_Ex1
            IntOp $0 $0 + 13
            ${NSD_CreateDirRequest} 0 $0u 90% 13u "$Path_Ex1"
                Pop $PathDialogue_Ex1
            ${NSD_CreateBrowseButton} -10% $0u 5% 13u "..."
                Pop $Browse_Ex1
                nsDialogs::OnClick $Browse_Ex1 $Function_Browse
            IntOp $0 $0 + 13
        ${EndIf}
        ${If} $Path_Ex2 != $Empty
            ${NSD_CreateCheckBox} 0 $0u 100% 13u "Extra Location 2"
                Pop $Check_Ex2
                ${NSD_SetState} $Check_Ex2 $CheckState_Ex2
            IntOp $0 $0 + 13
            ${NSD_CreateDirRequest} 0 $0u 90% 13u "$Path_Ex2"
                Pop $PathDialogue_Ex2
            ${NSD_CreateBrowseButton} -10% $0u 5% 13u "..."
                Pop $Browse_Ex2
                nsDialogs::OnClick $Browse_Ex2 $Function_Browse
            IntOp $0 $0 + 13
        ${EndIf}
        ;${NSD_CreateCheckBox} 0 $0u 100% 13u "Uninstall userfiles/Bash data."
        ;    Pop $Check_RemoveUserFiles
        ;    ${NSD_SetState} $Check_RemoveUserFiles ${BST_CHECKED}
        nsDialogs::Show
    FunctionEnd

    Function un.PAGE_SELECT_GAMES_Leave
        ${NSD_GetText} $PathDialogue_OB $Path_OB
        ${NSD_GetText} $PathDialogue_Nehrim $Path_Nehrim
        ${NSD_GetText} $PathDialogue_Skyrim $Path_Skyrim
        ${NSD_GetText} $PathDialogue_Ex1 $Path_Ex1
        ${NSD_GetText} $PathDialogue_Ex2 $Path_Ex2
        ${NSD_GetState} $Check_OB $CheckState_OB
        ${NSD_GetState} $Check_Nehrim $CheckState_Nehrim
        ${NSD_GetState} $Check_Skyrim $CheckState_Skyrim
        ${NSD_GetState} $Check_Extra $CheckState_Extra
        ${NSD_GetState} $Check_Ex1 $CheckState_Ex1
        ${NSD_GetState} $Check_Ex2 $CheckState_Ex2
    FunctionEnd
