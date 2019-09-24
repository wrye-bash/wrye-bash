; pages.nsi
; Custom pages for the Wrye Bash NSIS installer / uninstaller

!include "macros.nsh"

;---------------------------- Install Locations Page
    Function PAGE_INSTALLLOCATIONS_ES
        !insertmacro MUI_HEADER_TEXT $(PAGE_INSTALLLOCATIONS_ES_TITLE) $(PAGE_INSTALLLOCATIONS_ES_SUBTITLE)
        GetFunctionAddress $Function_Browse OnClick_Browse

        nsDialogs::Create 1018
            Pop $Dialog

        ${If} $Dialog == error
            Abort
        ${EndIf}

        ${NSD_CreateLabel} 0 0 100% 24u "Select which Elder Scrolls Game(s) you would like to install Wrye Bash for.$\nAlso select which version(s) to install (Standalone exe (default) and/or Python version).$\nFallout Install Locations are on the next page."
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

        ${If} $Path_SkyrimSE != $Empty
            ${NSD_CreateCheckBox} 0 $0u 30% 13u "Install for SkyrimSE"
                Pop $Check_SkyrimSE
                ${NSD_SetState} $Check_SkyrimSE $CheckState_SkyrimSE
            ${NSD_CreateCheckBox} 30% $0u 40% 13u "Wrye Bash [Standalone]"
                Pop $Check_SkyrimSE_Exe
                ${NSD_AddStyle} $Check_SkyrimSE_Exe ${WS_GROUP}
                ${NSD_SetState} $Check_SkyrimSE_Exe $CheckState_SkyrimSE_Exe
            ${NSD_CreateCheckBox} 70% $0u 30% 13u "Wrye Bash [Python]"
                Pop $Check_SkyrimSE_Py
;                ${NSD_SetState} $Check_SkyrimSE_Py $CheckState_SkyrimSE_Py
            IntOp $0 $0 + 13
            ${NSD_CreateDirRequest} 0 $0u 90% 13u "$Path_SkyrimSE"
                Pop $PathDialogue_SkyrimSE
            ${NSD_CreateBrowseButton} -10% $0u 5% 13u "..."
                Pop $Browse_SkyrimSE
                nsDialogs::OnClick $Browse_SkyrimSE $Function_Browse
            IntOp $0 $0 + 13
        ${EndIf}

        ${If} $Path_Enderal != $Empty
            ${NSD_CreateCheckBox} 0 $0u 30% 13u "Install for Enderal"
                Pop $Check_Enderal
                ${NSD_SetState} $Check_Enderal $CheckState_Enderal
            ${NSD_CreateCheckBox} 30% $0u 40% 13u "Wrye Bash [Standalone]"
                Pop $Check_Enderal_Exe
                ${NSD_AddStyle} $Check_Enderal_Exe ${WS_GROUP}
                ${NSD_SetState} $Check_Enderal_Exe $CheckState_Enderal_Exe
            ${NSD_CreateCheckBox} 70% $0u 30% 13u "Wrye Bash [Python]"
                Pop $Check_Enderal_Py
;                ${NSD_SetState} $Check_Enderal_Py $CheckState_Enderal_Py
            IntOp $0 $0 + 13
            ${NSD_CreateDirRequest} 0 $0u 90% 13u "$Path_Enderal"
                Pop $PathDialogue_Enderal
            ${NSD_CreateBrowseButton} -10% $0u 5% 13u "..."
                Pop $Browse_Enderal
                nsDialogs::OnClick $Browse_Enderal $Function_Browse
            IntOp $0 $0 + 13
        ${EndIf}

        nsDialogs::Show
    FunctionEnd

    Function PAGE_INSTALLLOCATIONS_ES_Leave
        # in case the user goes back to this page and changes selections
        StrCpy $PythonVersionInstall $Empty
        StrCpy $ExeVersionInstall $Empty

        ; Game paths
        ${NSD_GetText} $PathDialogue_OB $Path_OB
        ${NSD_GetText} $PathDialogue_Nehrim $Path_Nehrim
        ${NSD_GetText} $PathDialogue_Skyrim $Path_Skyrim
        ${NSD_GetText} $PathDialogue_SkyrimSE $Path_SkyrimSE
        ${NSD_GetText} $PathDialogue_Enderal $Path_Enderal

        ; Game states
        ${NSD_GetState} $Check_OB $CheckState_OB
        ${NSD_GetState} $Check_Nehrim $CheckState_Nehrim
        ${NSD_GetState} $Check_Skyrim $CheckState_Skyrim
        ${NSD_GetState} $Check_SkyrimSE $CheckState_SkyrimSE
        ${NSD_GetState} $Check_Enderal $CheckState_Enderal

        ; Python states
        ${NSD_GetState} $Check_OB_Py $CheckState_OB_Py
        ${NSD_GetState} $Check_Nehrim_Py $CheckState_Nehrim_Py
        ${NSD_GetState} $Check_Skyrim_Py $CheckState_Skyrim_Py
        ${NSD_GetState} $Check_SkyrimSE_Py $CheckState_SkyrimSE_Py
        ${NSD_GetState} $Check_Enderal_Py $CheckState_Enderal_Py

        ${If} $CheckState_OB_Py == ${BST_CHECKED}
        ${AndIf} $CheckState_OB == ${BST_CHECKED}
            StrCpy $PythonVersionInstall $True
        ${EndIf}

        ${If} $CheckState_Nehrim_Py == ${BST_CHECKED}
        ${AndIf} $CheckState_Nehrim == ${BST_CHECKED}
            StrCpy $PythonVersionInstall $True
        ${EndIf}

        ${If} $CheckState_Skyrim_Py == ${BST_CHECKED}
        ${AndIf} $CheckState_Skyrim == ${BST_CHECKED}
            StrCpy $PythonVersionInstall $True
        ${EndIf}

        ${If} $CheckState_SkyrimSE_Py == ${BST_CHECKED}
        ${AndIf} $CheckState_SkyrimSE == ${BST_CHECKED}
            StrCpy $PythonVersionInstall $True
        ${EndIf}

        ${If} $CheckState_Enderal_Py == ${BST_CHECKED}
        ${AndIf} $CheckState_Enderal == ${BST_CHECKED}
            StrCpy $PythonVersionInstall $True
        ${EndIf}

        ; Standalone states
        ${NSD_GetState} $Check_OB_Exe $CheckState_OB_Exe
        ${NSD_GetState} $Check_Nehrim_Exe $CheckState_Nehrim_Exe
        ${NSD_GetState} $Check_Skyrim_Exe $CheckState_Skyrim_Exe
        ${NSD_GetState} $Check_SkyrimSE_Exe $CheckState_SkyrimSE_Exe
        ${NSD_GetState} $Check_Enderal_Exe $CheckState_Enderal_Exe

        ${If} $CheckState_OB_Exe == ${BST_CHECKED}
        ${AndIf} $CheckState_OB == ${BST_CHECKED}
            StrCpy $ExeVersionInstall $True
        ${EndIf}

        ${If} $CheckState_Nehrim_Exe == ${BST_CHECKED}
        ${AndIf} $CheckState_Nehrim == ${BST_CHECKED}
            StrCpy $ExeVersionInstall $True
        ${EndIf}

        ${If} $CheckState_Skyrim_Exe == ${BST_CHECKED}
        ${AndIf} $CheckState_Skyrim == ${BST_CHECKED}
            StrCpy $ExeVersionInstall $True
        ${EndIf}

        ${If} $CheckState_SkyrimSE_Exe == ${BST_CHECKED}
        ${AndIf} $CheckState_SkyrimSE == ${BST_CHECKED}
            StrCpy $ExeVersionInstall $True
        ${EndIf}

        ${If} $CheckState_Enderal_Exe == ${BST_CHECKED}
        ${AndIf} $CheckState_Enderal == ${BST_CHECKED}
            StrCpy $ExeVersionInstall $True
        ${EndIf}

    FunctionEnd

    Function PAGE_INSTALLLOCATIONS_FALLOUT
        !insertmacro MUI_HEADER_TEXT $(PAGE_INSTALLLOCATIONS_FALLOUT_TITLE) $(PAGE_INSTALLLOCATIONS_FALLOUT_SUBTITLE)
        GetFunctionAddress $Function_Browse OnClick_Browse

        nsDialogs::Create 1018
            Pop $Dialog

        ${If} $Dialog == error
            Abort
        ${EndIf}

        ${NSD_CreateLabel} 0 0 100% 24u "Select which Fallout Game(s) you would like to install Wrye Flash for.$\nAlso select which version(s) to install (Standalone exe (default) and/or Python version).$\nExtra Install Location are on the next page."
            Pop $Label
            IntOp $0 0 + 25

        ${If} $Path_Fallout3 != $Empty
            ${NSD_CreateCheckBox} 0 $0u 30% 13u "Install for Fallout3"
                Pop $Check_Fallout3
                ${NSD_SetState} $Check_Fallout3 $CheckState_Fallout3
            ${NSD_CreateCheckBox} 30% $0u 40% 13u "Wrye Bash [Standalone]"
                Pop $Check_Fallout3_Exe
                ${NSD_AddStyle} $Check_Fallout3_Exe ${WS_GROUP}
                ${NSD_SetState} $Check_Fallout3_Exe $CheckState_Fallout3_Exe
            ${NSD_CreateCheckBox} 70% $0u 30% 13u "Wrye Bash [Python]"
                Pop $Check_Fallout3_Py
;                ${NSD_SetState} $Check_Fallout3_Py $CheckState_Fallout3_Py
            IntOp $0 $0 + 13
            ${NSD_CreateDirRequest} 0 $0u 90% 13u "$Path_Fallout3"
                Pop $PathDialogue_Fallout3
            ${NSD_CreateBrowseButton} -10% $0u 5% 13u "..."
                Pop $Browse_Fallout3
                nsDialogs::OnClick $Browse_Fallout3 $Function_Browse
            IntOp $0 $0 + 13
        ${EndIf}

        ${If} $Path_FalloutNV != $Empty
            ${NSD_CreateCheckBox} 0 $0u 30% 13u "Install for FalloutNV"
                Pop $Check_FalloutNV
                ${NSD_SetState} $Check_FalloutNV $CheckState_FalloutNV
            ${NSD_CreateCheckBox} 30% $0u 40% 13u "Wrye Bash [Standalone]"
                Pop $Check_FalloutNV_Exe
                ${NSD_AddStyle} $Check_FalloutNV_Exe ${WS_GROUP}
                ${NSD_SetState} $Check_FalloutNV_Exe $CheckState_FalloutNV_Exe
            ${NSD_CreateCheckBox} 70% $0u 30% 13u "Wrye Bash [Python]"
                Pop $Check_FalloutNV_Py
;                ${NSD_SetState} $Check_FalloutNV_Py $CheckState_FalloutNV_Py
            IntOp $0 $0 + 13
            ${NSD_CreateDirRequest} 0 $0u 90% 13u "$Path_FalloutNV"
                Pop $PathDialogue_FalloutNV
            ${NSD_CreateBrowseButton} -10% $0u 5% 13u "..."
                Pop $Browse_FalloutNV
                nsDialogs::OnClick $Browse_FalloutNV $Function_Browse
            IntOp $0 $0 + 13
        ${EndIf}

        ${If} $Path_Fallout4 != $Empty
            ${NSD_CreateCheckBox} 0 $0u 30% 13u "Install for Fallout4"
                Pop $Check_Fallout4
                ${NSD_SetState} $Check_Fallout4 $CheckState_Fallout4
            ${NSD_CreateCheckBox} 30% $0u 40% 13u "Wrye Bash [Standalone]"
                Pop $Check_Fallout4_Exe
                ${NSD_AddStyle} $Check_Fallout4_Exe ${WS_GROUP}
                ${NSD_SetState} $Check_Fallout4_Exe $CheckState_Fallout4_Exe
            ${NSD_CreateCheckBox} 70% $0u 30% 13u "Wrye Bash [Python]"
                Pop $Check_Fallout4_Py
;                ${NSD_SetState} $Check_Fallout4_Py $CheckState_Fallout4_Py
            IntOp $0 $0 + 13
            ${NSD_CreateDirRequest} 0 $0u 90% 13u "$Path_Fallout4"
                Pop $PathDialogue_Fallout4
            ${NSD_CreateBrowseButton} -10% $0u 5% 13u "..."
                Pop $Browse_Fallout4
                nsDialogs::OnClick $Browse_Fallout4 $Function_Browse
            IntOp $0 $0 + 13
        ${EndIf}

        nsDialogs::Show
    FunctionEnd

    Function PAGE_INSTALLLOCATIONS_FALLOUT_Leave
        # in case the user goes back to this page and changes selections
        StrCpy $PythonVersionInstall $Empty
        StrCpy $ExeVersionInstall $Empty

        ; Game paths
        ${NSD_GetText} $PathDialogue_Fallout3 $Path_Fallout3
        ${NSD_GetText} $PathDialogue_FalloutNV $Path_FalloutNV
        ${NSD_GetText} $PathDialogue_Fallout4 $Path_Fallout4

        ; Game states
        ${NSD_GetState} $Check_Fallout3 $CheckState_Fallout3
        ${NSD_GetState} $Check_FalloutNV $CheckState_FalloutNV
        ${NSD_GetState} $Check_Fallout4 $CheckState_Fallout4
        ${NSD_GetState} $Check_Extra $CheckState_Extra

        ; Python states
        ${NSD_GetState} $Check_Fallout3_Py $CheckState_Fallout3_Py
        ${NSD_GetState} $Check_FalloutNV_Py $CheckState_FalloutNV_Py
        ${NSD_GetState} $Check_Fallout4_Py $CheckState_Fallout4_Py

        ${If} $CheckState_Fallout3_Py == ${BST_CHECKED}
        ${AndIf} $CheckState_Fallout3 == ${BST_CHECKED}
            StrCpy $PythonVersionInstall $True
        ${EndIf}

        ${If} $CheckState_FalloutNV_Py == ${BST_CHECKED}
        ${AndIf} $CheckState_FalloutNV == ${BST_CHECKED}
            StrCpy $PythonVersionInstall $True
        ${EndIf}

        ${If} $CheckState_Fallout4_Py == ${BST_CHECKED}
        ${AndIf} $CheckState_Fallout4 == ${BST_CHECKED}
            StrCpy $PythonVersionInstall $True
        ${EndIf}

        ; Standalone states
        ${NSD_GetState} $Check_Fallout3_Exe $CheckState_Fallout3_Exe
        ${NSD_GetState} $Check_FalloutNV_Exe $CheckState_FalloutNV_Exe
        ${NSD_GetState} $Check_Fallout4_Exe $CheckState_Fallout4_Exe

        ${If} $CheckState_Fallout3_Exe == ${BST_CHECKED}
        ${AndIf} $CheckState_Fallout3 == ${BST_CHECKED}
            StrCpy $ExeVersionInstall $True
        ${EndIf}

        ${If} $CheckState_FalloutNV_Exe == ${BST_CHECKED}
        ${AndIf} $CheckState_FalloutNV == ${BST_CHECKED}
            StrCpy $ExeVersionInstall $True
        ${EndIf}

        ${If} $CheckState_Fallout4_Exe == ${BST_CHECKED}
        ${AndIf} $CheckState_Fallout4 == ${BST_CHECKED}
            StrCpy $ExeVersionInstall $True
        ${EndIf}
    FunctionEnd

    Function PAGE_INSTALLLOCATIONS_EXTRA
        !insertmacro MUI_HEADER_TEXT $(PAGE_INSTALLLOCATIONS_FALLOUT_TITLE) $(PAGE_INSTALLLOCATIONS_FALLOUT_SUBTITLE)
        GetFunctionAddress $Function_Browse OnClick_Browse
        GetFunctionAddress $Function_Extra OnClick_Extra

        nsDialogs::Create 1018
            Pop $Dialog

        ${If} $Dialog == error
            Abort
        ${EndIf}

        ${NSD_CreateLabel} 0 0 100% 24u "Select which Extra location(s) you would like to install Wrye Bash/Flash for.$\nAlso select which version(s) to install (Standalone exe (default) and/or Python version)."
            Pop $Label
            IntOp $0 0 + 25

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

    Function PAGE_INSTALLLOCATIONS_EXTRA_Leave
        # in case the user goes back to this page and changes selections
        StrCpy $PythonVersionInstall $Empty
        StrCpy $ExeVersionInstall $Empty

        ; Game paths
        ${NSD_GetText} $PathDialogue_Ex1 $Path_Ex1
        ${NSD_GetText} $PathDialogue_Ex2 $Path_Ex2

        ; Game states
        ${NSD_GetState} $Check_Extra $CheckState_Extra
        ${NSD_GetState} $Check_Ex1 $CheckState_Ex1
        ${NSD_GetState} $Check_Ex2 $CheckState_Ex2

        ; Python states
        ${NSD_GetState} $Check_Ex1_Py $CheckState_Ex1_Py
        ${NSD_GetState} $Check_Ex2_Py $CheckState_Ex2_Py

        ${If} $CheckState_Ex1_Py == ${BST_CHECKED}
        ${AndIf} $CheckState_Extra == ${BST_CHECKED}
        ${AndIf} $CheckState_Ex1 == ${BST_CHECKED}
            StrCpy $PythonVersionInstall $True
        ${EndIf}

        ${If} $CheckState_Ex2_Py == ${BST_CHECKED}
        ${AndIf} $CheckState_Extra == ${BST_CHECKED}
        ${AndIf} $CheckState_Ex2 == ${BST_CHECKED}
            StrCpy $PythonVersionInstall $True
        ${EndIf}

        ; Standalone states
        ${NSD_GetState} $Check_Ex1_Exe $CheckState_Ex1_Exe
        ${NSD_GetState} $Check_Ex2_Exe $CheckState_Ex2_Exe

        ${If} $CheckState_Ex1_Exe == ${BST_CHECKED}
        ${AndIf} $CheckState_Extra == ${BST_CHECKED}
        ${AndIf} $CheckState_Ex1 == ${BST_CHECKED}
            StrCpy $ExeVersionInstall $True
        ${EndIf}

        ${If} $CheckState_Ex2_Exe == ${BST_CHECKED}
        ${AndIf} $CheckState_Extra == ${BST_CHECKED}
        ${AndIf} $CheckState_Ex2 == ${BST_CHECKED}
            StrCpy $ExeVersionInstall $True
        ${EndIf}
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
            ${EndIf}
        ${EndIf}

        ${If} $CheckState_Nehrim == ${BST_CHECKED}
            ${StrLoc} $0 $Path_Nehrim "$PROGRAMFILES\" ">"
            ${If} "0" == $0
                StrCpy $1 $True
            ${EndIf}
        ${EndIf}

        ${If} $CheckState_Skyrim == ${BST_CHECKED}
            ${StrLoc} $0 $Path_Skyrim "$PROGRAMFILES\" ">"
            ${If} "0" == $0
                StrCpy $1 $True
            ${EndIf}
        ${EndIf}

        ${If} $CheckState_Fallout4 == ${BST_CHECKED}
            ${StrLoc} $0 $Path_Fallout4 "$PROGRAMFILES\" ">"
            ${If} "0" == $0
                StrCpy $1 $True
            ${EndIf}
        ${EndIf}

        ${If} $CheckState_SkyrimSE == ${BST_CHECKED}
            ${StrLoc} $0 $Path_SkyrimSE "$PROGRAMFILES\" ">"
            ${If} "0" == $0
                StrCpy $1 $True
            ${EndIf}
        ${EndIf}

        ${If} $CheckState_Enderal == ${BST_CHECKED}
            ${StrLoc} $0 $Path_Enderal "$PROGRAMFILES\" ">"
            ${If} "0" == $0
                StrCpy $1 $True
            ${EndIf}
        ${EndIf}

        ${If} $CheckState_Fallout3 == ${BST_CHECKED}
            ${StrLoc} $0 $Path_Fallout3 "$PROGRAMFILES\" ">"
            ${If} "0" == $0
                StrCpy $1 $True
            ${EndIf}
        ${EndIf}

        ${If} $CheckState_FalloutNV == ${BST_CHECKED}
            ${StrLoc} $0 $Path_FalloutNV "$PROGRAMFILES\" ">"
            ${If} "0" == $0
                StrCpy $1 $True
            ${EndIf}
        ${EndIf}

        ${If} $CheckState_Ex1 == ${BST_CHECKED}
            ${StrLoc} $0 $Path_Ex1 "$PROGRAMFILES\" ">"
            ${If} "0" == $0
                StrCpy $1 $True
            ${EndIf}
        ${EndIf}

        ${If} $CheckState_Ex2 == ${BST_CHECKED}
            ${StrLoc} $0 $Path_Ex2 "$PROGRAMFILES\" ">"
            ${If} "0" == $0
                StrCpy $1 $True
            ${EndIf}
        ${EndIf}

        ${If} $1 == $Empty
            ; nothing installed in program files: skip this page
            Abort
        ${EndIf}

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

        !insertmacro UpdateRegistryPaths

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

        ${If} $Path_SkyrimSE != $Empty
            ${NSD_CreateCheckBox} 0 $0u 100% 8u "SkyrimSE"
                Pop $Check_SkyrimSE
            IntOp $0 $0 + 9
        ${EndIf}

        ${If} $Path_Enderal != $Empty
            ${NSD_CreateCheckBox} 0 $0u 100% 8u "Enderal"
                Pop $Check_Enderal
            IntOp $0 $0 + 9
        ${EndIf}

        ${If} $Path_Fallout3 != $Empty
            ${NSD_CreateCheckBox} 0 $0u 100% 8u "Fallout3"
                Pop $Check_Fallout3
            IntOp $0 $0 + 9
        ${EndIf}

        ${If} $Path_FalloutNV != $Empty
            ${NSD_CreateCheckBox} 0 $0u 100% 8u "FalloutNV"
                Pop $Check_FalloutNV
            IntOp $0 $0 + 9
        ${EndIf}

        ${If} $Path_Fallout4 != $Empty
            ${NSD_CreateCheckBox} 0 $0u 100% 8u "Fallout4"
                Pop $Check_Fallout4
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
            EnableWindow $Check_DeleteOldFiles 0 ; always delete old files
            ${NSD_SetState} $Check_DeleteOldFiles ${BST_CHECKED}

        nsDialogs::Show
    FunctionEnd

    Function PAGE_FINISH_Leave
        ${NSD_GetState} $Check_OB $CheckState_OB
        ${NSD_GetState} $Check_Nehrim $CheckState_Nehrim
        ${NSD_GetState} $Check_Skyrim $CheckState_Skyrim
        ${NSD_GetState} $Check_Fallout4 $CheckState_Fallout4
        ${NSD_GetState} $Check_SkyrimSE $CheckState_SkyrimSE
        ${NSD_GetState} $Check_Enderal $CheckState_Enderal
        ${NSD_GetState} $Check_Fallout3 $CheckState_Fallout3
        ${NSD_GetState} $Check_FalloutNV $CheckState_FalloutNV
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
                ExecShell "open" '"$Path_Skyrim\Mopy\Wrye Bash Launcher.pyw"'
            ${ElseIf} $CheckState_Skyrim_Exe == ${BST_CHECKED}
                ExecShell "open" "$Path_Skyrim\Mopy\Wrye Bash.exe"
            ${EndIf}
        ${EndIf}

        ${If} $CheckState_Fallout4 == ${BST_CHECKED}
            SetOutPath "$Path_Fallout4\Mopy"
            ${If} $CheckState_Fallout4_Py == ${BST_CHECKED}
                ExecShell "open" '"$Path_Fallout4\Mopy\Wrye Bash Launcher.pyw"'
            ${ElseIf} $CheckState_Fallout4_Exe == ${BST_CHECKED}
                ExecShell "open" "$Path_Fallout4\Mopy\Wrye Bash.exe"
            ${EndIf}
        ${EndIf}

        ${If} $CheckState_SkyrimSE == ${BST_CHECKED}
            SetOutPath "$Path_SkyrimSE\Mopy"
            ${If} $CheckState_SkyrimSE_Py == ${BST_CHECKED}
                ExecShell "open" '"$Path_SkyrimSE\Mopy\Wrye Bash Launcher.pyw"'
            ${ElseIf} $CheckState_SkyrimSE_Exe == ${BST_CHECKED}
                ExecShell "open" "$Path_SkyrimSE\Mopy\Wrye Bash.exe"
            ${EndIf}
        ${EndIf}

        ${If} $CheckState_Enderal == ${BST_CHECKED}
            SetOutPath "$Path_Enderal\Mopy"
            ${If} $CheckState_Enderal_Py == ${BST_CHECKED}
                ExecShell "open" '"$Path_Enderal\Mopy\Wrye Bash Launcher.pyw"'
            ${ElseIf} $CheckState_Enderal_Exe == ${BST_CHECKED}
                ExecShell "open" "$Path_Enderal\Mopy\Wrye Bash.exe"
            ${EndIf}
        ${EndIf}

        ${If} $CheckState_Fallout3 == ${BST_CHECKED}
            SetOutPath "$Path_Fallout3\Mopy"
            ${If} $CheckState_Fallout3_Py == ${BST_CHECKED}
                ExecShell "open" '"$Path_Fallout3\Mopy\Wrye Bash Launcher.pyw"'
            ${ElseIf} $CheckState_Fallout3_Exe == ${BST_CHECKED}
                ExecShell "open" "$Path_Fallout3\Mopy\Wrye Bash.exe"
            ${EndIf}
        ${EndIf}

        ${If} $CheckState_FalloutNV == ${BST_CHECKED}
            SetOutPath "$Path_FalloutNV\Mopy"
            ${If} $CheckState_FalloutNV_Py == ${BST_CHECKED}
                ExecShell "open" '"$Path_FalloutNV\Mopy\Wrye Bash Launcher.pyw"'
            ${ElseIf} $CheckState_FalloutNV_Exe == ${BST_CHECKED}
                ExecShell "open" "$Path_FalloutNV\Mopy\Wrye Bash.exe"
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
            ${ElseIf} $Path_Fallout4 != $Empty
                ExecShell "open" "$Path_Fallout4\Mopy\Docs\Wrye Bash General Readme.html"
            ${ElseIf} $Path_SkyrimSE != $Empty
                ExecShell "open" "$Path_SkyrimSE\Mopy\Docs\Wrye Bash General Readme.html"
            ${ElseIf} $Path_Enderal != $Empty
                ExecShell "open" "$Path_Enderal\Mopy\Docs\Wrye Bash General Readme.html"
            ${ElseIf} $Path_Fallout3 != $Empty
                ExecShell "open" "$Path_Fallout3\Mopy\Docs\Wrye Bash General Readme.html"
            ${ElseIf} $Path_FalloutNV != $Empty
                ExecShell "open" "$Path_FalloutNV\Mopy\Docs\Wrye Bash General Readme.html"
            ${ElseIf} $Path_Ex1 != $Empty
                ExecShell "open" "$Path_Ex1\Mopy\Docs\Wrye Bash General Readme.html"
            ${ElseIf} $Path_Ex2 != $Empty
                ExecShell "open" "$Path_Ex2\Mopy\Docs\Wrye Bash General Readme.html"
            ${EndIf}
        ${EndIf}

        ${NSD_GetState} $Check_DeleteOldFiles $0

        ${If} $0 == ${BST_CHECKED}
            ${If} $Path_OB != $Empty
                !insertmacro RemoveOldFiles "$Path_OB"
            ${EndIf}
            ${If} $Path_Nehrim != $Empty
                !insertmacro RemoveOldFiles "$Path_Nehrim"
            ${EndIf}
            ${If} $Path_Skyrim != $Empty
                !insertmacro RemoveOldFiles "$Path_Skyrim"
            ${EndIf}
            ${If} $Path_Fallout4 != $Empty
                !insertmacro RemoveOldFiles "$Path_Fallout4"
            ${EndIf}
            ${If} $Path_SkyrimSE != $Empty
                !insertmacro RemoveOldFiles "$Path_SkyrimSE"
            ${EndIf}
            ${If} $Path_Enderal != $Empty
                !insertmacro RemoveOldFiles "$Path_Enderal"
            ${EndIf}
            ${If} $Path_Fallout3 != $Empty
                !insertmacro RemoveOldFiles "$Path_Fallout3"
            ${EndIf}
            ${If} $Path_FalloutNV != $Empty
                !insertmacro RemoveOldFiles "$Path_FalloutNV"
            ${EndIf}
            ${If} $Path_Ex1 != $Empty
                !insertmacro RemoveOldFiles "$Path_Ex1"
            ${EndIf}
            ${If} $Path_Ex2 != $Empty
                !insertmacro RemoveOldFiles "$Path_Ex2"
            ${EndIf}
        ${EndIf}
    FunctionEnd


;----------------------------- Custom Uninstallation Pages and their Functions:
    Function un.PAGE_SELECT_GAMES_ES
        !insertmacro MUI_HEADER_TEXT $(PAGE_INSTALLLOCATIONS_ES_TITLE) $(unPAGE_SELECT_GAMES_SUBTITLE)
        GetFunctionAddress $unFunction_Browse un.OnClick_Browse

        nsDialogs::Create 1018
            Pop $Dialog

        ${If} $Dialog == error
            Abort
        ${EndIf}

        ${NSD_CreateLabel} 0 0 100% 8u "Please select which game(s) and version(s) to uninstall Wrye Bash from:"
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
                nsDialogs::OnClick $Browse_OB $unFunction_Browse
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
                nsDialogs::OnClick $Browse_Nehrim $unFunction_Browse
            IntOp $0 $0 + 13
        ${EndIf}

        ${If} $Path_Skyrim != $Empty
            ${NSD_CreateCheckBox} 0 $0u 100% 13u "&Skyrim"
                Pop $Check_Skyrim
                ${NSD_SetState} $Check_Skyrim $CheckState_Skyrim
            IntOp $0 $0 + 13
            ${NSD_CreateDirRequest} 0 $0u 90% 13u "$Path_Skyrim"
                Pop $PathDialogue_Skyrim
            ${NSD_CreateBrowseButton} -10% $0u 5% 13u "..."
                Pop $Browse_Skyrim
                nsDialogs::OnClick $Browse_Skyrim $unFunction_Browse
            IntOp $0 $0 + 13
        ${EndIf}

        ${If} $Path_SkyrimSE != $Empty
            ${NSD_CreateCheckBox} 0 $0u 100% 13u "&SkyrimSE"
                Pop $Check_SkyrimSE
                ${NSD_SetState} $Check_SkyrimSE $CheckState_SkyrimSE
            IntOp $0 $0 + 13
            ${NSD_CreateDirRequest} 0 $0u 90% 13u "$Path_SkyrimSE"
                Pop $PathDialogue_SkyrimSE
            ${NSD_CreateBrowseButton} -10% $0u 5% 13u "..."
                Pop $Browse_SkyrimSE
                nsDialogs::OnClick $Browse_SkyrimSE $unFunction_Browse
            IntOp $0 $0 + 13
        ${EndIf}

        ${If} $Path_Enderal != $Empty
            ${NSD_CreateCheckBox} 0 $0u 100% 13u "&Enderal"
                Pop $Check_Enderal
                ${NSD_SetState} $Check_Enderal $CheckState_Enderal
            IntOp $0 $0 + 13
            ${NSD_CreateDirRequest} 0 $0u 90% 13u "$Path_Enderal"
                Pop $PathDialogue_Enderal
            ${NSD_CreateBrowseButton} -10% $0u 5% 13u "..."
                Pop $Browse_Enderal
                nsDialogs::OnClick $Browse_Enderal $unFunction_Browse
            IntOp $0 $0 + 13
        ${EndIf}

        ;${NSD_CreateCheckBox} 0 $0u 100% 13u "Uninstall userfiles/Bash data."
        ;    Pop $Check_RemoveUserFiles
        ;    ${NSD_SetState} $Check_RemoveUserFiles ${BST_CHECKED}
        nsDialogs::Show
    FunctionEnd

    Function un.PAGE_SELECT_GAMES_ES_Leave
        ${NSD_GetText} $PathDialogue_OB $Path_OB
        ${NSD_GetText} $PathDialogue_Nehrim $Path_Nehrim
        ${NSD_GetText} $PathDialogue_Skyrim $Path_Skyrim
        ${NSD_GetText} $PathDialogue_SkyrimSE $Path_SkyrimSE
        ${NSD_GetText} $PathDialogue_Enderal $Path_Enderal
        ${NSD_GetState} $Check_OB $CheckState_OB
        ${NSD_GetState} $Check_Nehrim $CheckState_Nehrim
        ${NSD_GetState} $Check_Skyrim $CheckState_Skyrim
        ${NSD_GetState} $Check_SkyrimSE $CheckState_SkyrimSE
        ${NSD_GetState} $Check_Enderal $CheckState_Enderal
    FunctionEnd

    Function un.PAGE_SELECT_GAMES_FALLOUT
        !insertmacro MUI_HEADER_TEXT $(PAGE_INSTALLLOCATIONS_FALLOUT_TITLE) $(unPAGE_SELECT_GAMES_SUBTITLE)
        GetFunctionAddress $unFunction_Browse un.OnClick_Browse

        nsDialogs::Create 1018
            Pop $Dialog
        ${If} $Dialog == error
            Abort
            ${EndIf}

        ${NSD_CreateLabel} 0 0 100% 16u "Please select which game(s) and version(s) to uninstall Wrye Flash from:"
            Pop $Label
            IntOp $0 0 + 17

        ${If} $Path_Fallout3 != $Empty
            ${NSD_CreateCheckBox} 0 $0u 100% 13u "&Fallout3"
                Pop $Check_Fallout3
                ${NSD_SetState} $Check_Fallout3 $CheckState_Fallout3
            IntOp $0 $0 + 13
            ${NSD_CreateDirRequest} 0 $0u 90% 13u "$Path_Fallout3"
                Pop $PathDialogue_Fallout3
            ${NSD_CreateBrowseButton} -10% $0u 5% 13u "..."
                Pop $Browse_Fallout3
                nsDialogs::OnClick $Browse_Fallout3 $unFunction_Browse
            IntOp $0 $0 + 13
        ${EndIf}

        ${If} $Path_FalloutNV != $Empty
            ${NSD_CreateCheckBox} 0 $0u 100% 13u "&FalloutNV"
                Pop $Check_FalloutNV
                ${NSD_SetState} $Check_FalloutNV $CheckState_FalloutNV
            IntOp $0 $0 + 13
            ${NSD_CreateDirRequest} 0 $0u 90% 13u "$Path_FalloutNV"
                Pop $PathDialogue_FalloutNV
            ${NSD_CreateBrowseButton} -10% $0u 5% 13u "..."
                Pop $Browse_FalloutNV
                nsDialogs::OnClick $Browse_FalloutNV $unFunction_Browse
            IntOp $0 $0 + 13
        ${EndIf}

        ${If} $Path_Fallout4 != $Empty
            ${NSD_CreateCheckBox} 0 $0u 100% 13u "&Fallout4"
                Pop $Check_Fallout4
                ${NSD_SetState} $Check_Fallout4 $CheckState_Fallout4
            IntOp $0 $0 + 13
            ${NSD_CreateDirRequest} 0 $0u 90% 13u "$Path_Fallout4"
                Pop $PathDialogue_Fallout4
            ${NSD_CreateBrowseButton} -10% $0u 5% 13u "..."
                Pop $Browse_Fallout4
                nsDialogs::OnClick $Browse_Fallout4 $unFunction_Browse
            IntOp $0 $0 + 13
        ${EndIf}

        ;${NSD_CreateCheckBox} 0 $0u 100% 13u "Uninstall userfiles/Bash data."
        ;    Pop $Check_RemoveUserFiles
        ;    ${NSD_SetState} $Check_RemoveUserFiles ${BST_CHECKED}
        nsDialogs::Show
    FunctionEnd

    Function un.PAGE_SELECT_GAMES_FALLOUT_Leave
        ${NSD_GetText} $PathDialogue_Fallout3 $Path_Fallout3
        ${NSD_GetText} $PathDialogue_FalloutNV $Path_FalloutNV
        ${NSD_GetText} $PathDialogue_Fallout4 $Path_Fallout4
        ${NSD_GetState} $Check_Fallout3 $CheckState_Fallout3
        ${NSD_GetState} $Check_FalloutNV $CheckState_FalloutNV
        ${NSD_GetState} $Check_Fallout4 $CheckState_Fallout4
    FunctionEnd

    Function un.PAGE_SELECT_GAMES_EXTRA
        !insertmacro MUI_HEADER_TEXT $(PAGE_INSTALLLOCATIONS_EXTRA_TITLE) $(unPAGE_SELECT_GAMES_SUBTITLE)
        GetFunctionAddress $unFunction_Browse un.OnClick_Browse

        nsDialogs::Create 1018
            Pop $Dialog
        ${If} $Dialog == error
            Abort
            ${EndIf}

        ${NSD_CreateLabel} 0 0 100% 16u "Please select which extra location(s) and version(s) to uninstall Wrye Bash/Flash from:"
            Pop $Label
            IntOp $0 0 + 17

        ${If} $Path_Ex1 != $Empty
            ${NSD_CreateCheckBox} 0 $0u 100% 13u "Extra Location 1"
                Pop $Check_Ex1
                ${NSD_SetState} $Check_Ex1 $CheckState_Ex1
            IntOp $0 $0 + 13
            ${NSD_CreateDirRequest} 0 $0u 90% 13u "$Path_Ex1"
                Pop $PathDialogue_Ex1
            ${NSD_CreateBrowseButton} -10% $0u 5% 13u "..."
                Pop $Browse_Ex1
                nsDialogs::OnClick $Browse_Ex1 $unFunction_Browse
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
                nsDialogs::OnClick $Browse_Ex2 $unFunction_Browse
            IntOp $0 $0 + 13
        ${EndIf}

        ;${NSD_CreateCheckBox} 0 $0u 100% 13u "Uninstall userfiles/Bash data."
        ;    Pop $Check_RemoveUserFiles
        ;    ${NSD_SetState} $Check_RemoveUserFiles ${BST_CHECKED}
        nsDialogs::Show
    FunctionEnd

    Function un.PAGE_SELECT_GAMES_EXTRA_Leave
        ${NSD_GetState} $Check_Extra $CheckState_Extra
        ${NSD_GetText} $PathDialogue_Ex1 $Path_Ex1
        ${NSD_GetText} $PathDialogue_Ex2 $Path_Ex2
        ${NSD_GetState} $Check_Ex1 $CheckState_Ex1
        ${NSD_GetState} $Check_Ex2 $CheckState_Ex2
    FunctionEnd
