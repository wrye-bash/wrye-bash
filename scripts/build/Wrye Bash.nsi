; Wrye Bash.nsi

;-------------------------------- Includes:
    !include "MUI2.nsh"
    !include "x64.nsh"
    !include "LogicLib.nsh"
    !include "nsDialogs.nsh"
    !include "WordFunc.nsh"
    !include "StrFunc.nsh"
    ; declare used functions
    ${StrLoc}

    ; Variables are defined by the packaging script; just define failsafe values
    !ifndef WB_NAME
        !define WB_NAME "Wrye Bash (version unknown)"
    !endif
    !ifndef WB_FILEVERSION
        !define WB_FILEVERSION "0.0.0.0"
    !endif


;-------------------------------- Basic Installer Info:
    Name "${WB_NAME}"
    OutFile "scripts\dist\${WB_NAME} - Installer.exe"
    ; Request application privileges for Windows Vista
    RequestExecutionLevel admin
    VIProductVersion ${WB_FILEVERSION}
    VIAddVersionKey /LANG=${LANG_ENGLISH} "ProductName" "Wrye Bash"
    VIAddVersionKey /LANG=${LANG_ENGLISH} "CompanyName" "Wrye Bash development team"
    VIAddVersionKey /LANG=${LANG_ENGLISH} "LegalCopyright" "© Wrye"
    VIAddVersionKey /LANG=${LANG_ENGLISH} "FileDescription" "Installer for ${WB_NAME}"
    VIAddVersionKey /LANG=${LANG_ENGLISH} "FileVersion" "${WB_FILEVERSION}"
    SetCompressor /SOLID lzma


;-------------------------------- Variables:
    Var Dialog
    Var Label
    Var Empty
    Var True
    Var Path_OB
    Var Path_Nehrim
    Var Path_Skyrim
    Var Path_Ex1
    Var Path_Ex2

    ;Game specific Data:
    Var Check_OB
    Var Check_Nehrim
    Var Check_Skyrim
    Var Check_Extra
    Var Check_Ex1
    Var Check_Ex2
    Var CheckState_OB
    Var CheckState_Nehrim
    Var CheckState_Skyrim
    Var CheckState_Extra
    Var CheckState_Ex1
    Var CheckState_Ex2
    Var Check_OB_Py
    Var Check_Nehrim_Py
    Var Check_Skyrim_Py
    Var Check_Ex1_Py
    Var Check_Ex2_Py
    Var CheckState_OB_Py
    Var CheckState_Nehrim_Py
    Var CheckState_Skyrim_Py
    Var CheckState_Ex1_Py
    Var CheckState_Ex2_Py
    Var Check_OB_Exe
    Var Check_Nehrim_Exe
    Var Check_Skyrim_Exe
    Var Check_Ex1_Exe
    Var Check_Ex2_Exe
    Var CheckState_OB_Exe
    Var CheckState_Nehrim_Exe
    Var CheckState_Skyrim_Exe
    Var CheckState_Ex1_Exe
    Var CheckState_Ex2_Exe
    Var Reg_Value_OB_Py
    Var Reg_Value_Nehrim_Py
    Var Reg_Value_Skyrim_Py
    Var Reg_Value_Ex1_Py
    Var Reg_Value_Ex2_Py
    Var Reg_Value_OB_Exe
    Var Reg_Value_Nehrim_Exe
    Var Reg_Value_Skyrim_Exe
    Var Reg_Value_Ex1_Exe
    Var Reg_Value_Ex2_Exe
    Var PathDialogue_OB
    Var PathDialogue_Nehrim
    Var PathDialogue_Skyrim
    Var PathDialogue_Ex1
    Var PathDialogue_Ex2
    Var Browse_OB
    Var Browse_Nehrim
    Var Browse_Skyrim
    Var Browse_Ex1
    Var Browse_Ex2
    Var Check_Readme
    Var Check_DeleteOldFiles
    Var Function_Browse
    Var Function_Extra
    Var Function_DirPrompt
    Var unFunction_Browse
    Var Python_Path
    Var Python_Comtypes
    Var Python_pywin32
    Var Python_wx
    Var PythonVersionInstall
    Var ExeVersionInstall
    Var MinVersion_Comtypes
    Var MinVersion_wx
    Var MinVersion_pywin32


;-------------------------------- Page List:
    !define MUI_HEADERIMAGE
    !define MUI_HEADERIMAGE_BITMAP "Mopy\bash\images\nsis\wrye_monkey_150x57.bmp"
    !define MUI_HEADERIMAGE_RIGHT
    !define MUI_WELCOMEFINISHPAGE_BITMAP "Mopy\bash\images\nsis\wrye_monkey_164x314.bmp"
    !define MUI_UNWELCOMEFINISHPAGE_BITMAP "Mopy\bash\images\nsis\wrye_monkey_164x314.bmp"
    !insertmacro MUI_PAGE_WELCOME
    Page custom PAGE_INSTALLLOCATIONS PAGE_INSTALLLOCATIONS_Leave
    Page custom PAGE_CHECK_LOCATIONS PAGE_CHECK_LOCATIONS_Leave
    !insertmacro MUI_PAGE_COMPONENTS
    !insertmacro MUI_PAGE_INSTFILES
    Page custom PAGE_FINISH PAGE_FINISH_Leave

    !insertmacro MUI_UNPAGE_WELCOME
    UninstPage custom un.PAGE_SELECT_GAMES un.PAGE_SELECT_GAMES_Leave
    !insertmacro MUI_UNPAGE_INSTFILES


;-------------------------------- Initialize Variables as required:
    Function un.onInit
        StrCpy $Empty ""
        StrCpy $True "True"
        ReadRegStr $Path_OB              HKLM "Software\Wrye Bash" "Oblivion Path"
        ReadRegStr $Path_Nehrim          HKLM "Software\Wrye Bash" "Nehrim Path"
        ReadRegStr $Path_Skyrim          HKLM "Software\Wrye Bash" "Skyrim Path"
        ReadRegStr $Path_Ex1             HKLM "Software\Wrye Bash" "Extra Path 1"
        ReadRegStr $Path_Ex2             HKLM "Software\Wrye Bash" "Extra Path 2"
        ReadRegStr $Reg_Value_OB_Py      HKLM "Software\Wrye Bash" "Oblivion Python Version"
        ReadRegStr $Reg_Value_Nehrim_Py  HKLM "Software\Wrye Bash" "Nehrim Python Version"
        ReadRegStr $Reg_Value_Skyrim_Py  HKLM "Software\Wrye Bash" "Skyrim Python Version"
        ReadRegStr $Reg_Value_Ex1_Py     HKLM "Software\Wrye Bash" "Extra Path 1 Python Version"
        ReadRegStr $Reg_Value_Ex2_Py     HKLM "Software\Wrye Bash" "Extra Path 2 Python Version"
        ReadRegStr $Reg_Value_OB_Exe     HKLM "Software\Wrye Bash" "Oblivion Standalone Version"
        ReadRegStr $Reg_Value_Nehrim_Exe HKLM "Software\Wrye Bash" "Nehrim Standalone Version"
        ReadRegStr $Reg_Value_Skyrim_Exe HKLM "Software\Wrye Bash" "Skyrim Standalone Version"
        ReadRegStr $Reg_Value_Ex1_Exe    HKLM "Software\Wrye Bash" "Extra Path 1 Standalone Version"
        ReadRegStr $Reg_Value_Ex2_Exe    HKLM "Software\Wrye Bash" "Extra Path 2 Standalone Version"
    FunctionEnd

    Function .onInit
        StrCpy $Empty ""
        StrCpy $True "True"
        ReadRegStr $Path_OB              HKLM "Software\Wrye Bash" "Oblivion Path"
        ReadRegStr $Path_Nehrim          HKLM "Software\Wrye Bash" "Nehrim Path"
        ReadRegStr $Path_Skyrim          HKLM "Software\Wrye Bash" "Skyrim Path"
        ReadRegStr $Path_Ex1             HKLM "Software\Wrye Bash" "Extra Path 1"
        ReadRegStr $Path_Ex2             HKLM "Software\Wrye Bash" "Extra Path 2"
        ReadRegStr $Reg_Value_OB_Py      HKLM "Software\Wrye Bash" "Oblivion Python Version"
        ReadRegStr $Reg_Value_Nehrim_Py  HKLM "Software\Wrye Bash" "Nehrim Python Version"
        ReadRegStr $Reg_Value_Skyrim_Py  HKLM "Software\Wrye Bash" "Skyrim Python Version"
        ReadRegStr $Reg_Value_Ex1_Py     HKLM "Software\Wrye Bash" "Extra Path 1 Python Version"
        ReadRegStr $Reg_Value_Ex2_Py     HKLM "Software\Wrye Bash" "Extra Path 2 Python Version"
        ReadRegStr $Reg_Value_OB_Exe     HKLM "Software\Wrye Bash" "Oblivion Standalone Version"
        ReadRegStr $Reg_Value_Nehrim_Exe HKLM "Software\Wrye Bash" "Nehrim Standalone Version"
        ReadRegStr $Reg_Value_Skyrim_Exe HKLM "Software\Wrye Bash" "Skyrim Standalone Version"
        ReadRegStr $Reg_Value_Ex1_Exe    HKLM "Software\Wrye Bash" "Extra Path 1 Standalone Version"
        ReadRegStr $Reg_Value_Ex2_Exe    HKLM "Software\Wrye Bash" "Extra Path 2 Standalone Version"

        StrCpy $MinVersion_Comtypes '0.6.2'
        StrCpy $MinVersion_wx '2.8.12'
        StrCpy $MinVersion_pywin32 '217'
        StrCpy $Python_Comtypes "1"
        StrCpy $Python_wx "1"
        StrCpy $Python_pywin32 "1"

        ${If} $Path_OB == $Empty
            ReadRegStr $Path_OB HKLM "Software\Bethesda Softworks\Oblivion" "Installed Path"
            ${If} $Path_OB == $Empty
                ReadRegStr $Path_OB HKLM "SOFTWARE\Wow6432Node\Bethesda Softworks\Oblivion" "Installed Path"
            ${EndIf}
        ${EndIf}
        ${If} $Path_OB != $Empty
            StrCpy $CheckState_OB ${BST_CHECKED}
        ${EndIf}

        ${If} $Path_Nehrim == $Empty
            ReadRegStr $Path_Nehrim HKLM "SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall\Nehrim - At Fate's Edge_is1" "InstallLocation"
        ${EndIf}
        ${If} $Path_Nehrim != $Empty
            StrCpy $CheckState_Nehrim ${BST_CHECKED}
        ${EndIf}

        ${If} $Path_Skyrim == $Empty
            ReadRegStr $Path_Skyrim HKLM "Software\Bethesda Softworks\Skyrim" "Installed Path"
            ${If} $Path_Skyrim == $Empty
                ReadRegStr $Path_Skyrim HKLM "SOFTWARE\Wow6432Node\Bethesda Softworks\Skyrim" "Installed Path"
            ${EndIf}
        ${EndIf}
        ${If} $Path_Skyrim != $Empty
            StrCpy $CheckState_Skyrim ${BST_CHECKED}
        ${EndIf}

        ${If} $Path_Ex1 != $Empty
            StrCpy $CheckState_Extra ${BST_CHECKED}
            StrCpy $CheckState_Ex1 ${BST_CHECKED}
        ${EndIf}

        ${If} $Path_Ex2 != $Empty
            StrCpy $CheckState_Extra ${BST_CHECKED}
            StrCpy $CheckState_Ex2 ${BST_CHECKED}
        ${EndIf}

        ${If} $Reg_Value_OB_Exe == $True
        ${OrIf} $Reg_Value_OB_Py != $True
            StrCpy $CheckState_OB_Exe ${BST_CHECKED}
        ${EndIf}
        ${If} $Reg_Value_OB_Py == $True
            StrCpy $CheckState_OB_Py ${BST_CHECKED}
        ${EndIf}

        ${If} $Reg_Value_Nehrim_Exe == $True
        ${OrIf} $Reg_Value_Nehrim_Py != $True
            StrCpy $CheckState_Nehrim_Exe ${BST_CHECKED}
        ${EndIf}
        ${If} $Reg_Value_Nehrim_Py == $True
            StrCpy $CheckState_Nehrim_Py ${BST_CHECKED}
        ${EndIf}

        ${If} $Reg_Value_Skyrim_Exe == $True
        ${OrIf} $Reg_Value_Skyrim_Py != $True
            StrCpy $CheckState_Skyrim_Exe ${BST_CHECKED}
        ${EndIf}
        ${If} $Reg_Value_Skyrim_Py == $True
            StrCpy $CheckState_Skyrim_Py ${BST_CHECKED}
        ${EndIf}

        ${If} $Reg_Value_Ex1_Exe == $True
        ${OrIf} $Reg_Value_Ex1_Py != $True
            StrCpy $CheckState_Ex1_Exe ${BST_CHECKED}
        ${EndIf}

        ${If} $Reg_Value_Ex1_Py == $True
            StrCpy $CheckState_Ex1_Py ${BST_CHECKED}
        ${EndIf}
        ${If} $Reg_Value_Ex2_Exe == $True
        ${OrIf} $Reg_Value_Ex2_Py != $True
            StrCpy $CheckState_Ex2_Exe ${BST_CHECKED}
        ${EndIf}
        ${If} $Reg_Value_Ex2_Py == $True
            StrCpy $CheckState_Ex2_Py ${BST_CHECKED}
        ${EndIf}
    FunctionEnd


;-------------------------------- Install Locations Page
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


;-------------------------------- Check Locations Page
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

;-------------------------------- Finish Page
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
            ${EndIf}
        ${EndIf}
    FunctionEnd


;-------------------------------- Auxilliary Functions
    Function OnClick_Browse
        Pop $0
        ${If} $0 == $Browse_OB
            StrCpy $1 $PathDialogue_OB
        ${ElseIf} $0 == $Browse_Nehrim
            StrCpy $1 $PathDialogue_Nehrim
        ${ElseIf} $0 == $Browse_Skyrim
            StrCpy $1 $PathDialogue_Skyrim
        ${ElseIf} $0 == $Browse_Ex1
            StrCpy $1 $PathDialogue_Ex1
        ${ElseIf} $0 == $Browse_Ex2
            StrCpy $1 $PathDialogue_Ex2
        ${EndIf}
        ${NSD_GetText} $1 $Function_DirPrompt
        nsDialogs::SelectFolderDialog /NOUNLOAD "Please select a target directory" $Function_DirPrompt
        Pop $0

        ${If} $0 == error
            Abort
        ${EndIf}

        ${NSD_SetText} $1 $0
    FunctionEnd

    Function OnClick_Extra
        Pop $0
        ${NSD_GetState} $0 $CheckState_Extra
        ${If} $CheckState_Extra == ${BST_UNCHECKED}
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
        ${Else}
            ShowWindow $Check_Ex1 ${SW_SHOW}
            ShowWindow $Check_Ex1_Py ${SW_SHOW}
            ShowWindow $Check_Ex1_Exe ${SW_SHOW}
            ShowWindow $PathDialogue_Ex1 ${SW_SHOW}
            ShowWindow $Browse_Ex1 ${SW_SHOW}
            ShowWindow $Check_Ex2 ${SW_SHOW}
            ShowWindow $Check_Ex2_Py ${SW_SHOW}
            ShowWindow $Check_Ex2_Exe ${SW_SHOW}
            ShowWindow $PathDialogue_Ex2 ${SW_SHOW}
            ShowWindow $Browse_Ex2 ${SW_SHOW}
        ${EndIf}
    FunctionEnd


;-------------------------------- The Installation Sections:

    Section "Prerequisites" Prereq
        SectionIn RO
        ; Both Python and Standalone versions require the MSVC 2013 redist, so check for that and download/install if necessary.
        ; Thanks to the pcsx2 installer for providing this!

        ; Detection made easy: Unlike previous redists, VC2013 now generates a platform
        ; independent key for checking availability.
        ; HKEY_LOCAL_MACHINE\SOFTWARE\Wow6432Node\Microsoft\VisualStudio\12.0\VC\Runtimes\x86  for x64 Windows
        ; HKEY_LOCAL_MACHINE\SOFTWARE\Microsoft\VisualStudio\12.0\VC\Runtimes\x86  for x86 Windows

        ; Download from:
        ; http://download.microsoft.com/download/2/E/6/2E61CFA4-993B-4DD4-91DA-3737CD5CD6E3/vcredist_x86.exe

        ClearErrors

        ${If} ${RunningX64}
            ReadRegDword $R0 HKLM "SOFTWARE\Wow6432Node\Microsoft\VisualStudio\12.0\VC\Runtimes\x86" "Installed"
        ${Else}
            ReadRegDword $R0 HKLM "SOFTWARE\Microsoft\VisualStudio\12.0\VC\Runtimes\x86" "Installed"
        ${EndIf}

        ${If} $R0 == "1"
            DetailPrint "Visual C++ 2013 Redistributable is already installed; skipping!"
        ${Else}
            DetailPrint "Visual C++ 2013 Redistributable registry key was not found; assumed to be uninstalled."
            DetailPrint "Downloading Visual C++ 2013 Redistributable Setup..."
            SetOutPath $TEMP
            NSISdl::download "http://download.microsoft.com/download/2/E/6/2E61CFA4-993B-4DD4-91DA-3737CD5CD6E3/vcredist_x86.exe" "vcredist_x86.exe"

            Pop $R0 ;Get the return value
            ${If} $R0 == "success"
                DetailPrint "Running Visual C++ 2013 Redistributable Setup..."
                Sleep 2000
                HideWindow
                ExecWait '"$TEMP\vcredist_x86.exe" /qb'
                BringToFront
                DetailPrint "Finished Visual C++ 2013 SP1 Redistributable Setup"
                
                Delete "$TEMP\vcredist_x86.exe"
            ${Else}
                DetailPrint "Could not contact Microsoft.com, or the file has been (re)moved!"
            ${EndIf}
        ${EndIf}
        
        ; Standalone version also requires the MSVC 2008 redist.
        ${If} $ExeVersionInstall == $True
            StrCpy $9 $Empty
            ${If} ${FileExists} "$SYSDIR\MSVCR90.DLL"
            ${OrIf} ${FileExists} "$COMMONFILES\Microsoft Shared\VC\msdia90.dll"
                StrCpy $9 "Installed"
            ${EndIf}
            ${If} $9 == $Empty
                ; MSVC 2008 (x86): http://download.microsoft.com/download/d/d/9/dd9a82d0-52ef-40db-8dab-795376989c03/vcredist_x86.exe
                DetailPrint "Visual C++ 2008 Redistributable was not found; assumed to be uninstalled."
                DetailPrint "Downloading Visual C++ 2008 Redistributable Setup..."
                SetOutPath $TEMP
                NSISdl::download "http://download.microsoft.com/download/d/d/9/dd9a82d0-52ef-40db-8dab-795376989c03/vcredist_x86.exe" "vcredist_x86.exe"
                
                Pop $R0 ;Get the return value
                ${If} $R0 == "success"
                    DetailPrint "Running Visual C++ 2008 Redistributable Setup..."
                    Sleep 2000
                    HideWindow
                    ExecWait '"$TEMP\vcredist_x86.exe" /qb'
                    BringToFront
                    DetailPrint "Finished Visual C++ 2008 SP1 Redistributable Setup"
                    
                    Delete "$TEMP\vcredist_x86.exe"
                ${Else}
                    DetailPrint "Could not contact Microsoft.com, or the file has been (re)moved!"
                ${EndIf}
            ${Else}
                DetailPrint "Visual C++ 2008 Redistributable is already installed; skipping!"
            ${EndIf}
        ${EndIf}
        
        ; Python version also requires Python, wxPython, Python Comtypes and PyWin32.
        ${If} $PythonVersionInstall == $True
            ; Look for Python.
            ReadRegStr $Python_Path HKLM "SOFTWARE\Wow6432Node\Python\PythonCore\2.7\InstallPath" ""
            ${If} $Python_Path == $Empty
                ReadRegStr $Python_Path HKLM "SOFTWARE\Python\PythonCore\2.7\InstallPath" ""
            ${EndIf}
            ${If} $Python_Path == $Empty
                ReadRegStr $Python_Path HKCU "SOFTWARE\Wow6432Node\Python\PythonCore\2.7\InstallPath" ""
            ${EndIf}
            ${If} $Python_Path == $Empty
                ReadRegStr $Python_Path HKCU "SOFTWARE\Python\PythonCore\2.7\InstallPath" ""
            ${EndIf}

            ;Detect Python Components:
            ${If} $Python_Path != $Empty
                ;Detect Comtypes:
                ${If} ${FileExists} "$Python_Path\Lib\site-packages\comtypes\__init__.py"
                    FileOpen $2 "$Python_Path\Lib\site-packages\comtypes\__init__.py" r
                    FileRead $2 $1
                    FileRead $2 $1
                    FileRead $2 $1
                    FileRead $2 $1
                    FileRead $2 $1
                    FileRead $2 $1
                    FileClose $2
                    StrCpy $Python_Comtypes $1 5 -8
                    ${VersionConvert} $Python_Comtypes "" $Python_Comtypes
                    ${VersionCompare} $MinVersion_Comtypes $Python_Comtypes $Python_Comtypes
                ${EndIf}
                
                ; Detect wxPython.
                ReadRegStr $Python_wx HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\wxPython2.8-unicode-py27_is1" "DisplayVersion"
                ${If} $Python_wx == $Empty
                    ReadRegStr $Python_wx HKCU "Software\Microsoft\Windows\CurrentVersion\Uninstall\wxPython2.8-unicode-py27_is1" "DisplayVersion"
                ${EndIf}
                ; Detect PyWin32.
                ReadRegStr $1         HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\pywin32-py2.7" "DisplayName"
                ${If} $1 == $Empty
                    ReadRegStr $1         HKCU "Software\Microsoft\Windows\CurrentVersion\Uninstall\pywin32-py2.7" "DisplayName"
                ${EndIf}
                StrCpy $Python_pywin32 $1 3 -3
                
                ; Compare versions.
                ${VersionCompare} $MinVersion_pywin32 $Python_pywin32 $Python_pywin32
                ${VersionConvert} $Python_wx "+" $Python_wx
                ${VersionCompare} $MinVersion_wx $Python_wx $Python_wx
            ${EndIf}
        
            ; Download and install missing requirements.
            ${If} $Python_Path == $Empty
                SetOutPath "$TEMP\PythonInstallers"
                DetailPrint "Python 2.7.3 - Downloading..."
                NSISdl::download http://python.org/ftp/python/2.7.3/python-2.7.3.msi "$TEMP\PythonInstallers\python-2.7.3.msi"
                Pop $R0
                ${If} $R0 == "success"
                    DetailPrint "Python 2.7.3 - Installing..."
                    Sleep 2000
                    HideWindow
                    ExecWait '"msiexec" /i "$TEMP\PythonInstallers\python-2.7.3.msi"'
                    BringToFront
                    DetailPrint "Python 2.7.3 - Installed."
                ${Else}
                    DetailPrint "Python 2.7.3 - Download Failed!"
                    MessageBox MB_OK "Python download failed, please try running installer again or manually downloading."
                    Abort
                ${EndIf}
            ${Else}
                DetailPrint "Python 2.7.3 is already installed; skipping!"
            ${EndIf}
            ${If} $Python_wx == "1"
                SetOutPath "$TEMP\PythonInstallers"
                DetailPrint "wxPython 2.8.12.1 - Downloading..."
                NSISdl::download http://downloads.sourceforge.net/wxpython/wxPython2.8-win32-unicode-2.8.12.1-py27.exe "$TEMP\PythonInstallers\wxPython.exe"
                Pop $R0
                ${If} $R0 == "success"
                    DetailPrint "wxPython 2.8.12.1 - Installing..."
                    Sleep 2000
                    HideWindow
                    ExecWait '"$TEMP\PythonInstallers\wxPython.exe"'; /VERYSILENT'
                    BringToFront
                    DetailPrint "wxPython 2.8.12.1 - Installed."
                ${Else}
                    DetailPrint "wxPython 2.8.12.1 - Download Failed!"
                    MessageBox MB_OK "wxPython download failed, please try running installer again or manually downloading."
                    Abort
                ${EndIf}
            ${Else}
                DetailPrint "wxPython 2.8.12.1 is already installed; skipping!"
            ${EndIf}
            ${If} $Python_Comtypes == "1"
                SetOutPath "$TEMP\PythonInstallers"
                DetailPrint "Comtypes 0.6.2 - Downloading..."
                NSISdl::download http://downloads.sourceforge.net/project/comtypes/comtypes/0.6.2/comtypes-0.6.2.win32.exe?r=http%3A%2F%2Fsourceforge.net%2Fprojects%2Fcomtypes%2F&ts=1291561083&use_mirror=softlayer "$TEMP\PythonInstallers\comtypes.exe"
                Pop $R0
                ${If} $R0 == "success"
                    DetailPrint "Comtypes 0.6.2 - Installing..."
                    Sleep 2000
                    HideWindow
                    ExecWait  '"$TEMP\PythonInstallers\comtypes.exe"'
                    BringToFront
                    DetailPrint "Comtypes 0.6.2 - Installed."
                ${Else}
                    DetailPrint "Comtypes 0.6.2 - Download Failed!"
                    MessageBox MB_OK "Comtypes download failed, please try running installer again or manually downloading: $0."
                    Abort
                ${EndIf}
            ${Else}
                DetailPrint "Comtypes 0.6.2 is already installed; skipping!"
            ${EndIf}
            ${If} $Python_pywin32 == "1"
                SetOutPath "$TEMP\PythonInstallers"
                DetailPrint "PyWin32 - Downloading..."
                NSISdl::download http://downloads.sourceforge.net/project/pywin32/pywin32/Build%20218/pywin32-218.win32-py2.7.exe?r=&ts=1352752073&use_mirror=iweb "$TEMP\PythonInstallers\pywin32.exe"
                Pop $R0
                ${If} $R0 == "success"
                    DetailPrint "PyWin32 - Installing..."
                    Sleep 2000
                    HideWindow
                    ExecWait  '"$TEMP\PythonInstallers\pywin32.exe"'
                    BringToFront
                    DetailPrint "PyWin32 - Installed."
                ${Else}
                    DetailPrint "PyWin32 - Download Failed!"
                    MessageBox MB_OK "PyWin32 download failed, please try running installer again or manually downloading."
                    Abort
                ${EndIf}
            ${Else}
                DetailPrint "PyWin32 is already installed; skipping!"
            ${EndIf}
        ${EndIf}
    SectionEnd
    
    Section "Wrye Bash" Main
        SectionIn RO

        ${If} $CheckState_OB == ${BST_CHECKED}
            ; Install resources:
            ${If} Path_OB != $Empty
                SetOutPath $Path_OB\Mopy
                File /r /x "*.svn*" /x "*.bat" /x "*.py*" /x "w9xpopen.exe" /x "Wrye Bash.exe" "Mopy\*.*"
                SetOutPath $Path_OB\Data
                File /r "Mopy\templates\Oblivion\ArchiveInvalidationInvalidated!.bsa"
                SetOutPath "$Path_OB\Mopy\Bash Patches\Oblivion"
                File /r "Mopy\Bash Patches\Oblivion\*.*"
                SetOutPath $Path_OB\Data\Docs
                SetOutPath "$Path_OB\Mopy\INI Tweaks\Oblivion"
                File /r "Mopy\INI Tweaks\Oblivion\*.*"
                ; Write the installation path into the registry
                WriteRegStr HKLM "SOFTWARE\Wrye Bash" "Oblivion Path" "$Path_OB"
                ${If} $CheckState_OB_Py == ${BST_CHECKED}
                    SetOutPath "$Path_OB\Mopy"
                    File /r "Mopy\*.py" "Mopy\*.pyw" "Mopy\*.bat"
                    ; Write the installation path into the registry
                    WriteRegStr HKLM "SOFTWARE\Wrye Bash" "Oblivion Python Version" "True"
                ${Else}
                    ${If} $Reg_Value_OB_Py == $Empty ; ie don't overwrite it if it is installed but just not being installed that way this time.
                        WriteRegStr HKLM "SOFTWARE\Wrye Bash" "Oblivion Python Version" ""
                    ${EndIf}
                ${EndIf}
                ${If} $CheckState_OB_Exe == ${BST_CHECKED}
                    SetOutPath "$Path_OB\Mopy"
                    File "Mopy\w9xpopen.exe" "Mopy\Wrye Bash.exe"
                    ; Write the installation path into the registry
                    WriteRegStr HKLM "SOFTWARE\Wrye Bash" "Oblivion Standalone Version" "True"
                ${Else}
                    ${If} $Reg_Value_OB_Exe == $Empty ; ie don't overwrite it if it is installed but just not being installed that way this time.
                        WriteRegStr HKLM "SOFTWARE\Wrye Bash" "Oblivion Standalone Version" ""
                    ${EndIf}
                ${EndIf}
            ${EndIf}
        ${EndIf}
        ${If} $CheckState_Nehrim == ${BST_CHECKED}
            ; Install resources:
            ${If} Path_Nehrim != $Empty
                SetOutPath $Path_Nehrim\Mopy
                File /r /x "*.svn*" /x "*.bat" /x "*.py*" /x "w9xpopen.exe" /x "Wrye Bash.exe" "Mopy\*.*"
                SetOutPath $Path_Nehrim\Data
                File /r "Mopy\templates\Oblivion\ArchiveInvalidationInvalidated!.bsa"
                SetOutPath "$Path_Nehrim\Mopy\Bash Patches\Oblivion"
                File /r "Mopy\Bash Patches\Oblivion\*.*"
                SetOutPath $Path_Nehrim\Data\Docs
                SetOutPath "$Path_Nehrim\Mopy\INI Tweaks\Oblivion"
                File /r "Mopy\INI Tweaks\Oblivion\*.*"
                ; Write the installation path into the registry
                WriteRegStr HKLM "SOFTWARE\Wrye Bash" "Nehrim Path" "$Path_Nehrim"
                ${If} $CheckState_Nehrim_Py == ${BST_CHECKED}
                    SetOutPath "$Path_Nehrim\Mopy"
                    File /r "Mopy\*.py" "Mopy\*.pyw" "Mopy\*.bat"
                    ; Write the installation path into the registry
                    WriteRegStr HKLM "SOFTWARE\Wrye Bash" "Nehrim Python Version" "True"
                ${Else}
                    ${If} $Reg_Value_Nehrim_Py == $Empty ; ie don't overwrite it if it is installed but just not being installed that way this time.
                        WriteRegStr HKLM "SOFTWARE\Wrye Bash" "Nehrim Python Version" ""
                    ${EndIf}
                ${EndIf}
                ${If} $CheckState_Nehrim_Exe == ${BST_CHECKED}
                    SetOutPath "$Path_Nehrim\Mopy"
                    File "Mopy\w9xpopen.exe" "Mopy\Wrye Bash.exe"
                    ; Write the installation path into the registry
                    WriteRegStr HKLM "SOFTWARE\Wrye Bash" "Nehrim Standalone Version" "True"
                ${Else}
                    ${If} $Reg_Value_Nehrim_Exe == $Empty ; ie don't overwrite it if it is installed but just not being installed that way this time.
                        WriteRegStr HKLM "SOFTWARE\Wrye Bash" "Nehrim Standalone Version" ""
                    ${EndIf}
                ${EndIf}
            ${EndIf}
        ${EndIf}
        ${If} $CheckState_Skyrim == ${BST_CHECKED}
            ; Install resources:
            ${If} Path_Skyrim != $Empty
                SetOutPath $Path_Skyrim\Mopy
                File /r /x "*.svn*" /x "*.bat" /x "*.py*" /x "w9xpopen.exe" /x "Wrye Bash.exe" "Mopy\*.*"
                SetOutPath "$Path_Skyrim\Mopy\Bash Patches\Skyrim"
                File /r "Mopy\Bash Patches\Skyrim\*.*"
                SetOutPath $Path_Skyrim\Data\Docs
                SetOutPath "$Path_Skyrim\Mopy\INI Tweaks\Skyrim"
                File /r "Mopy\INI Tweaks\Skyrim\*.*"
                ; Write the installation path into the registry
                WriteRegStr HKLM "SOFTWARE\Wrye Bash" "Skyrim Path" "$Path_Skyrim"
                ${If} $CheckState_Skyrim == ${BST_CHECKED}
                    SetOutPath "$Path_Skyrim\Mopy"
                    File /r "Mopy\*.py" "Mopy\*.pyw" "Mopy\*.bat"
                    ; Write the installation path into the registry
                    WriteRegStr HKLM "SOFTWARE\Wrye Bash" "Skyrim Python Version" "True"
                ${ElseIf} $Reg_Value_Skyrim_Py == $Empty ; id don't overwrite it if it is installed but just not being installed that way this time.
                    WriteRegStr HKLM "SOFTWARE\Wrye Bash" "Skyrim Python Version" ""
                ${EndIf}
                ${If} $CheckState_Skyrim_Exe == ${BST_CHECKED}
                    SetOutPath "$Path_Skyrim\Mopy"
                    File "Mopy\w9xpopen.exe" "Mopy\Wrye Bash.exe"
                    ; Write the installation path into the registry
                    WriteRegStr HKLM "SOFTWARE\Wrye Bash" "Skyrim Standalone Version" "True"
                ${ElseIf} $Reg_Value_Skyrim_Exe == $Empty ; ie don't overwrite it if it is installed but just not being installed that way this time.
                    WriteRegStr HKLM "SOFTWARE\Wrye Bash" "Skyrim Standalond Version" ""
                ${EndIf}
            ${EndIf}
        ${EndIf}
        ${If} $CheckState_Ex1 == ${BST_CHECKED}
            ; Install resources:
            ${If} Path_Ex1 != $Empty
                SetOutPath $Path_Ex1\Mopy
                File /r /x "*.svn*" /x "*.bat" /x "*.py*" /x "w9xpopen.exe" /x "Wrye Bash.exe" "Mopy\*.*"
                ; Write the installation path into the registry
                WriteRegStr HKLM "SOFTWARE\Wrye Bash" "Extra Path 1" "$Path_Ex1"
                ${If} $CheckState_Ex1_Py == ${BST_CHECKED}
                    SetOutPath "$Path_Ex1\Mopy"
                    File /r "Mopy\*.py" "Mopy\*.pyw" "Mopy\*.bat"
                    ; Write the installation path into the registry
                    WriteRegStr HKLM "SOFTWARE\Wrye Bash" "Extra Path 1 Python Version" "True"
                ${Else}
                    ${If} $Reg_Value_Ex1_Py == $Empty ; ie don't overwrite it if it is installed but just not being installed that way this time.
                        WriteRegStr HKLM "SOFTWARE\Wrye Bash" "Extra Path 1 Python Version" ""
                    ${EndIf}
                ${EndIf}
                ${If} $CheckState_Ex1_Exe == ${BST_CHECKED}
                    SetOutPath "$Path_Ex1\Mopy"
                    File "Mopy\w9xpopen.exe" "Mopy\Wrye Bash.exe"
                    ; Write the installation path into the registry
                    WriteRegStr HKLM "SOFTWARE\Wrye Bash" "Extra Path 1 Standalone Version" "True"
                ${Else}
                    ${If} $Reg_Value_Ex1_Exe == $Empty ; ie don't overwrite it if it is installed but just not being installed that way this time.
                        WriteRegStr HKLM "SOFTWARE\Wrye Bash" "Extra Path 1 Standalone Version" ""
                    ${EndIf}
                ${EndIf}
            ${EndIf}
        ${EndIf}
        ${If} $CheckState_Ex2 == ${BST_CHECKED}
            ; Install resources:
            ${If} Path_Ex2 != $Empty
                SetOutPath $Path_Ex2\Mopy
                File /r /x "*.svn*" /x "*.bat" /x "*.py*" /x "w9xpopen.exe" /x "Wrye Bash.exe" "Mopy\*.*"
                ; Write the installation path into the registry
                WriteRegStr HKLM "SOFTWARE\Wrye Bash" "Extra Path 2" "$Path_Ex2"
                ${If} $CheckState_Ex2_Py == ${BST_CHECKED}
                    SetOutPath "$Path_Ex2\Mopy"
                    File /r "Mopy\*.py" "Mopy\*.pyw" "Mopy\*.bat"
                    ; Write the installation path into the registry
                    WriteRegStr HKLM "SOFTWARE\Wrye Bash" "Extra Path 2 Python Version" "True"
                ${Else}
                    ${If} $Reg_Value_Ex2_Py == $Empty ; ie don't overwrite it if it is installed but just not being installed that way this time.
                        WriteRegStr HKLM "SOFTWARE\Wrye Bash" "Extra Path 2 Python Version" ""
                    ${EndIf}
                ${EndIf}
                ${If} $CheckState_Ex2_Exe == ${BST_CHECKED}
                    SetOutPath "$Path_Ex2\Mopy"
                    File "Mopy\w9xpopen.exe" "Mopy\Wrye Bash.exe"
                    ; Write the installation path into the registry
                    WriteRegStr HKLM "SOFTWARE\Wrye Bash" "Extra Path 2 Standalone Version" "True"
                ${Else}
                    ${If} $Reg_Value_Ex2_Exe == $Empty ; ie don't overwrite it if it is installed but just not being installed that way this time.
                        WriteRegStr HKLM "SOFTWARE\Wrye Bash" "Extra Path 2 Standalone Version" ""
                    ${EndIf}
                ${EndIf}
            ${EndIf}
        ${EndIf}
        ; Write the uninstall keys for Windows
        SetOutPath "$COMMONFILES\Wrye Bash"
        WriteRegStr HKLM "Software\Wrye Bash" "Installer Path" "$EXEPATH"
        WriteRegStr HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\Wrye Bash" "DisplayName" "Wrye Bash"
        WriteRegStr HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\Wrye Bash" "UninstallString" '"$COMMONFILES\Wrye Bash\uninstall.exe"'
        WriteRegStr HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\Wrye Bash" "URLInfoAbout" 'http://oblivion.nexusmods.com/mods/22368'
        WriteRegStr HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\Wrye Bash" "HelpLink" 'http://forums.bethsoft.com/topic/1376871-rel-wrye-bash/'
        WriteRegStr HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\Wrye Bash" "Publisher" 'Wrye & Wrye Bash Development Team'
        WriteRegStr HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\Wrye Bash" "DisplayVersion" '${WB_FILEVERSION}'
        WriteRegDWORD HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\Wrye Bash" "NoModify" 1
        WriteRegDWORD HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\Wrye Bash" "NoRepair" 1
        CreateDirectory "$COMMONFILES\Wrye Bash"
        WriteUninstaller "$COMMONFILES\Wrye Bash\uninstall.exe"
    SectionEnd

    Section "Start Menu Shortcuts" Shortcuts_SM

        CreateDirectory "$SMPROGRAMS\Wrye Bash"
        CreateShortCut "$SMPROGRAMS\Wrye Bash\Uninstall.lnk" "$COMMONFILES\Wrye Bash\uninstall.exe" "" "$COMMONFILES\Wrye Bash\uninstall.exe" 0

        ${If} $CheckState_OB == ${BST_CHECKED}
            ${If} Path_OB != $Empty
                SetOutPath $Path_OB\Mopy
                ${If} $CheckState_OB_Py == ${BST_CHECKED}
                    CreateShortCut "$SMPROGRAMS\Wrye Bash\Wrye Bash - Oblivion.lnk" "$Path_OB\Mopy\Wrye Bash Launcher.pyw" "" "$Path_OB\Mopy\bash\images\bash_32.ico" 0
                    CreateShortCut "$SMPROGRAMS\Wrye Bash\Wrye Bash - Oblivion (Debug Log).lnk" "$Path_OB\Mopy\Wrye Bash Debug.bat" "" "$Path_OB\Mopy\bash\images\bash_32.ico" 0
                    ${If} $CheckState_OB_Exe == ${BST_CHECKED}
                        CreateShortCut "$SMPROGRAMS\Wrye Bash\Wrye Bash (Standalone) - Oblivion.lnk" "$Path_OB\Mopy\Wrye Bash.exe"
                        CreateShortCut "$SMPROGRAMS\Wrye Bash\Wrye Bash (Standalone) - Oblivion (Debug Log).lnk" "$Path_OB\Mopy\Wrye Bash.exe" "-d"
                    ${EndIf}
                ${ElseIf} $CheckState_OB_Exe == ${BST_CHECKED}
                    CreateShortCut "$SMPROGRAMS\Wrye Bash\Wrye Bash - Oblivion.lnk" "$Path_OB\Mopy\Wrye Bash.exe"
                    CreateShortCut "$SMPROGRAMS\Wrye Bash\Wrye Bash - Oblivion (Debug Log).lnk" "$Path_OB\Mopy\Wrye Bash.exe" "-d"
                ${EndIf}
            ${EndIf}
        ${EndIf}
        ${If} $CheckState_Nehrim == ${BST_CHECKED}
            ${If} Path_Nehrim != $Empty
                SetOutPath $Path_Nehrim\Mopy
                ${If} $CheckState_Nehrim_Py == ${BST_CHECKED}
                    CreateShortCut "$SMPROGRAMS\Wrye Bash\Wrye Bash - Nehrim.lnk" "$Path_Nehrim\Mopy\Wrye Bash Launcher.pyw" "" "$Path_Nehrim\Mopy\bash\images\bash_32.ico" 0
                    CreateShortCut "$SMPROGRAMS\Wrye Bash\Wrye Bash - Nehrim (Debug Log).lnk" "$Path_Nehrim\Mopy\Wrye Bash Debug.bat" "" "$Path_Nehrim\Mopy\bash\images\bash_32.ico" 0
                    ${If} $CheckState_Nehrim_Exe == ${BST_CHECKED}
                        CreateShortCut "$SMPROGRAMS\Wyre Bash\Wrye Bash (Standalone) - Nehrim.lnk" "$Path_Nehrim\Mopy\Wrye Bash.exe"
                        CreateShortCut "$SMPROGRAMS\Wrye Bash\Wrye Bash (Standalone) - Nehrim (Debug Log).lnk" "$Path_Nehrim\Mopy\Wrye Bash.exe" "-d"
                    ${EndIf}
                ${ElseIf} $CheckState_Nehrim_Exe == ${BST_CHECKED}
                    CreateShortCut "$SMPROGRAMS\Wyre Bash\Wrye Bash - Nehrim.lnk" "$Path_Nehrim\Mopy\Wrye Bash.exe"
                    CreateShortCut "$SMPROGRAMS\Wyre Bash\Wrye Bash - Nehrim (Debug Log).lnk" "$Path_Nehrim\Mopy\Wrye Bash.exe" "-d"
                ${EndIf}
            ${EndIf}
        ${EndIf}
        ${If} $CheckState_Skyrim == ${BST_CHECKED}
            ${If} Path_Skyrim != $Empty
                SetOutPath $Path_Skyrim\Mopy
                ${If} $CheckState_Skyrim_Py == ${BST_CHECKED}
                    CreateShortCut "$SMPROGRAMS\Wrye Bash\Wrye Bash - Skyrim.lnk" "$Path_Skyrim\Mopy\Wrye Bash Launcher.pyw" "" "$Path_Skyrim\Mopy\bash\images\bash_32.ico" 0
                    CreateShortCut "$SMPROGRAMS\Wrye Bash\Wrye Bash - Skyrim (Debug Log).lnk" "$Path_Skyrim\Mopy\Wrye Bash Debug.bat" "" "$Path_Skyrim\Mopy\bash\images\bash_32.ico" 0
                    ${If} $CheckState_Skyrim_Exe == ${BST_CHECKED}
                        CreateShortCut "$SMPROGRAMS\Wrye Bash\Wrye Bash (Standalone) - Skyrim.lnk" "$Path_Skyrim\Mopy\Wrye Bash.exe"
                        CreateShortCut "$SMPROGRAMS\Wrye Bash\Wrye Bash (Standalone) - Skyrim (Debug Log).lnk" "$Path_Skyrim\Mopy\Wrye Bash.exe" "-d"
                    ${EndIf}
                ${ElseIf} $CheckState_Skyrim_Exe == ${BST_CHECKED}
                    CreateShortCut "$SMPROGRAMS\Wrye Bash\Wrye Bash - Skyrim.lnk" "$Path_Skyrim\Mopy\Wrye Bash.exe"
                    CreateShortCut "$SMPROGRAMS\Wrye Bash\Wrye Bash - Skyrim (Debug Log).lnk" "$Path_Skyrim\Mopy\Wrye Bash.exe" "-d"
                ${EndIf}
            ${EndIf}
        ${EndIf}
        ${If} $CheckState_Ex1 == ${BST_CHECKED}
            ${If} Path_Ex1 != $Empty
                SetOutPath $Path_Ex1\Mopy
                ${If} $CheckState_Ex1_Py == ${BST_CHECKED}
                    CreateShortCut "$SMPROGRAMS\Wrye Bash\Wrye Bash - Extra 1.lnk" "$Path_Ex1\Mopy\Wrye Bash Launcher.pyw" "" "$Path_Ex1\Mopy\bash\images\bash_32.ico" 0
                    CreateShortCut "$SMPROGRAMS\Wrye Bash\Wrye Bash - Extra 1 (Debug Log).lnk" "$Path_Ex1\Mopy\Wrye Bash Debug.bat" "" "$Path_Ex1\Mopy\bash\images\bash_32.ico" 0
                    ${If} $CheckState_Ex1_Exe == ${BST_CHECKED}
                        CreateShortCut "$SMPROGRAMS\Wrye Bash\Wrye Bash (Standalone) - Extra 1.lnk" "$Path_Ex1\Mopy\Wrye Bash.exe"
                        CreateShortCut "$SMPROGRAMS\Wrye Bash\Wrye Bash (Standalone) - Extra 1 (Debug Log).lnk" "$Path_Ex1\Mopy\Wrye Bash.exe" "-d"
                    ${EndIf}
                ${ElseIf} $CheckState_Ex1_Exe == ${BST_CHECKED}
                    CreateShortCut "$SMPROGRAMS\Wrye Bash\Wrye Bash - Extra 1.lnk" "$Path_Ex1\Mopy\Wrye Bash.exe"
                    CreateShortCut "$SMPROGRAMS\Wrye Bash\Wrye Bash - Extra 1 (Debug Log).lnk" "$Path_Ex1\Mopy\Wrye Bash.exe" "-d"
                ${EndIf}
            ${EndIf}
        ${EndIf}
        ${If} $CheckState_Ex2 == ${BST_CHECKED}
            ${If} Path_Ex2 != $Empty
                SetOutPath $Path_Ex2\Mopy
                ${If} $CheckState_Ex2_Py == ${BST_CHECKED}
                    CreateShortCut "$SMPROGRAMS\Wrye Bash\Wrye Bash - Extra 2.lnk" "$Path_Ex2\Mopy\Wrye Bash Launcher.pyw" "" "$Path_Ex2\Mopy\bash\images\bash_32.ico" 0
                    CreateShortCut "$SMPROGRAMS\Wrye Bash\Wrye Bash - Extra 2 (Debug Log).lnk" "$Path_Ex2\Mopy\Wrye Bash Debug.bat" "" "$Path_Ex2\Mopy\bash\images\bash_32.ico" 0
                    ${If} $CheckState_Ex2_Exe == ${BST_CHECKED}
                        CreateShortCut "$SMPROGRAMS\Wrye Bash\Wrye Bash (Standalone) - Extra 2.lnk" "$Path_Ex2\Mopy\Wrye Bash.exe"
                        CreateShortCut "$SMPROGRAMS\Wrye Bash\Wrye Bash (Standalone) - Extra 2 (Debug Log).lnk" "$Path_Ex2\Mopy\Wrye Bash.exe" "-d"
                    ${EndIf}
                ${ElseIf} $CheckState_Ex2_Exe == ${BST_CHECKED}
                    CreateShortCut "$SMPROGRAMS\Wrye Bash\Wrye Bash - Extra 2.lnk" "$Path_Ex2\Mopy\Wrye Bash.exe"
                    CreateShortCut "$SMPROGRAMS\Wrye Bash\Wrye Bash - Extra 2 (Debug Log).lnk" "$Path_Ex2\Mopy\Wrye Bash.exe" "-d"
                ${EndIf}
            ${EndIf}
        ${EndIf}
    SectionEnd

;-------------------------------- Custom Uninstallation Pages and their Functions:
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

    Function un.OnClick_Browse
        Pop $0
        ${If} $0 == $Browse_OB
            StrCpy $1 $PathDialogue_OB
        ${ElseIf} $0 == $Browse_Nehrim
            StrCpy $1 $PathDialogue_Nehrim
        ${ElseIf} $0 == $Browse_Skyrim
            StrCpy $1 $PathDialogue_Skyrim
        ${ElseIf} $0 == $Browse_Ex1
            StrCpy $1 $PathDialogue_Ex1
        ${ElseIf} $0 == $Browse_Ex2
            StrCpy $1 $PathDialogue_Ex2
        ${EndIf}
        ${NSD_GetText} $1 $Function_DirPrompt
        nsDialogs::SelectFolderDialog /NOUNLOAD "Please select a target directory" $Function_DirPrompt
        Pop $0

        ${If} $0 == error
            Abort
        ${EndIf}

        ${NSD_SetText} $1 $0
    FunctionEnd


;-------------------------------- The Uninstallation Code:
    Section "Uninstall"
        ; Remove files and Directories - Directories are only deleted if empty.
        ${If} $CheckState_OB == ${BST_CHECKED}
            ${If} $Path_OB != $Empty
                DeleteRegValue HKLM "SOFTWARE\Wrye Bash" "Oblivion Path"
                DeleteRegValue HKLM "SOFTWARE\Wrye Bash" "Oblivion Python Version"
                DeleteRegValue HKLM "SOFTWARE\Wrye Bash" "Oblivion Standalone Version"
                ;First delete OLD version files:
                Delete "$Path_OB\Data\Docs\Bashed Lists.txt"
                Delete "$Path_OB\Data\Docs\Bashed Lists.html"
                Delete "$Path_OB\Mopy\uninstall.exe"
                Delete "$Path_OB\Data\Ini Tweaks\Autosave, Never [Oblivion].ini"
                Delete "$Path_OB\Data\Ini Tweaks\Autosave, ~Always [Oblivion].ini"
                Delete "$Path_OB\Data\Ini Tweaks\Border Regions, Disabled [Oblivion].ini"
                Delete "$Path_OB\Data\Ini Tweaks\Border Regions, ~Enabled [Oblivion].ini"
                Delete "$Path_OB\Data\Ini Tweaks\Fonts 1, ~Default [Oblivion].ini"
                Delete "$Path_OB\Data\Ini Tweaks\Fonts, ~Default [Oblivion].ini"
                Delete "$Path_OB\Data\Ini Tweaks\Grass, Fade 4k-5k [Oblivion].ini"
                Delete "$Path_OB\Data\Ini Tweaks\Grass, ~Fade 2k-3k [Oblivion].ini"
                Delete "$Path_OB\Data\Ini Tweaks\Intro Movies, Disabled [Oblivion].ini"
                Delete "$Path_OB\Data\Ini Tweaks\Intro Movies, ~Normal [Oblivion].ini"
                Delete "$Path_OB\Data\Ini Tweaks\Joystick, Disabled [Oblivion].ini"
                Delete "$Path_OB\Data\Ini Tweaks\Joystick, ~Enabled [Oblivion].ini"
                Delete "$Path_OB\Data\Ini Tweaks\Local Map Shader, Disabled [Oblivion].ini"
                Delete "$Path_OB\Data\Ini Tweaks\Local Map Shader, ~Enabled [Oblivion].ini"
                Delete "$Path_OB\Data\Ini Tweaks\Music, Disabled [Oblivion].ini"
                Delete "$Path_OB\Data\Ini Tweaks\Music, ~Enabled [Oblivion].ini"
                Delete "$Path_OB\Data\Ini Tweaks\Refraction Shader, Disabled [Oblivion].ini"
                Delete "$Path_OB\Data\Ini Tweaks\Refraction Shader, ~Enabled [Oblivion].ini"
                Delete "$Path_OB\Data\Ini Tweaks\Save Backups, 1 [Oblivion].ini"
                Delete "$Path_OB\Data\Ini Tweaks\Save Backups, 2 [Oblivion].ini"
                Delete "$Path_OB\Data\Ini Tweaks\Save Backups, 3 [Oblivion].ini"
                Delete "$Path_OB\Data\Ini Tweaks\Save Backups, 5 [Oblivion].ini"
                Delete "$Path_OB\Data\Ini Tweaks\Screenshot, Enabled [Oblivion].ini"
                Delete "$Path_OB\Data\Ini Tweaks\Screenshot, ~Disabled [Oblivion].ini"
                Delete "$Path_OB\Data\Ini Tweaks\ShadowMapResolution, 10 [Oblivion].ini"
                Delete "$Path_OB\Data\Ini Tweaks\ShadowMapResolution, ~256 [Oblivion].ini"
                Delete "$Path_OB\Data\Ini Tweaks\ShadowMapResolution, 1024 [Oblivion].ini"
                Delete "$Path_OB\Data\Ini Tweaks\Sound Card Channels, 24 [Oblivion].ini"
                Delete "$Path_OB\Data\Ini Tweaks\Sound Card Channels, ~32 [Oblivion].ini"
                Delete "$Path_OB\Data\Ini Tweaks\Sound Card Channels, 128 [Oblivion].ini"
                Delete "$Path_OB\Data\Ini Tweaks\Sound Card Channels, 16 [Oblivion].ini"
                Delete "$Path_OB\Data\Ini Tweaks\Sound Card Channels, 192 [Oblivion].ini"
                Delete "$Path_OB\Data\Ini Tweaks\Sound Card Channels, 48 [Oblivion].ini"
                Delete "$Path_OB\Data\Ini Tweaks\Sound Card Channels, 64 [Oblivion].ini"
                Delete "$Path_OB\Data\Ini Tweaks\Sound Card Channels, 8 [Oblivion].ini"
                Delete "$Path_OB\Data\Ini Tweaks\Sound Card Channels, 96 [Oblivion].ini"
                Delete "$Path_OB\Data\Ini Tweaks\Sound, Disabled [Oblivion].ini"
                Delete "$Path_OB\Data\Ini Tweaks\Sound, ~Enabled [Oblivion].ini"
                Delete "$Path_OB\Data\Bash Patches\Assorted to Cobl.csv"
                Delete "$Path_OB\Data\Bash Patches\Assorted_Exhaust.csv"
                Delete "$Path_OB\Data\Bash Patches\Bash_Groups.csv"
                Delete "$Path_OB\Data\Bash Patches\Bash_MFact.csv"
                Delete "$Path_OB\Data\Bash Patches\ShiveringIsleTravellers_Names.csv"
                Delete "$Path_OB\Data\Bash Patches\TamrielTravellers_Names.csv"
                Delete "$Path_OB\Data\Bash Patches\Guard_Names.csv"
                Delete "$Path_OB\Data\Bash Patches\Kmacg94_Exhaust.csv"
                Delete "$Path_OB\Data\Bash Patches\P1DCandles_Formids.csv"
                Delete "$Path_OB\Data\Bash Patches\OOO_Potion_Names.csv"
                Delete "$Path_OB\Data\Bash Patches\Random_NPC_Alternate_Names.csv"
                Delete "$Path_OB\Data\Bash Patches\Random_NPC_Names.csv"
                Delete "$Path_OB\Data\Bash Patches\Rational_Names.csv"
                Delete "$Path_OB\Data\Bash Patches\TI to Cobl_Formids.csv"
                Delete "$Path_OB\Data\Bash Patches\taglist.txt"
                Delete "$Path_OB\Data\Bash Patches\OOO, 1.23 Mincapped_NPC_Levels.csv"
                Delete "$Path_OB\Data\Bash Patches\OOO, 1.23 Uncapped_NPC_Levels.csv"
                Delete "$Path_OB\Data\Bash Patches\Crowded Cities 15_Alternate_Names.csv"
                Delete "$Path_OB\Data\Bash Patches\Crowded Cities 15_Names.csv"
                Delete "$Path_OB\Data\Bash Patches\Crowded Cities 30_Alternate_Names.csv"
                Delete "$Path_OB\Data\Bash Patches\Crowded Cities 30_Names.csv"
                Delete "$Path_OB\Data\Bash Patches\Crowded Roads Revamped_Names.csv"
                Delete "$Path_OB\Data\Bash Patches\Crowded Roads Revisited_Alternate_Names.csv"
                Delete "$Path_OB\Data\Bash Patches\Crowded Roads Revisited_Names.csv"
                Delete "$Path_OB\Data\Bash Patches\PTRoamingNPCs_Names.csv"
                Delete "$Path_OB\Mopy\Wrye Bash Advanced Readme.html"
                Delete "$Path_OB\Mopy\Wrye Bash General Readme.html"
                Delete "$Path_OB\Mopy\Wrye Bash Technical Readme.html"
                Delete "$Path_OB\Mopy\Wrye Bash Version History.html"
                ;As of 294 the below are obselete locations or files.
                Delete "$Path_OB\Mopy\7z.*"
                Delete "$Path_OB\Mopy\CBash.dll"
                Delete "$Path_OB\Mopy\Data\Italian.*"
                Delete "$Path_OB\Mopy\Data\Oblivion_ids.pkl"
                Delete "$Path_OB\Mopy\Data\Russian.*"
                Delete "$Path_OB\Mopy\Data\de.*"
                Delete "$Path_OB\Mopy\Data\pt_opt.*"
                Delete "$Path_OB\Mopy\Data\Actor Levels\OOO, 1.23 Mincapped.csv"
                Delete "$Path_OB\Mopy\Data\Actor Levels\OOO, 1.23 Uncapped.csv"
                RMDir  "$Path_OB\Mopy\Data\Actor Levels"
                RMDir  "$Path_OB\Mopy\Data"
                Delete "$Path_OB\Mopy\DebugLog(Python2.6).bat"
                Delete "$Path_OB\Mopy\Extras\*"
                Delete "$Path_OB\Mopy\ScriptParser.p*"
                Delete "$Path_OB\Mopy\balt.p*"
                Delete "$Path_OB\Mopy\barb.p*"
                Delete "$Path_OB\Mopy\barg.p*"
                Delete "$Path_OB\Mopy\bash.p*"
                Delete "$Path_OB\Mopy\basher.p*"
                Delete "$Path_OB\Mopy\bashmon.p*"
                Delete "$Path_OB\Mopy\belt.p*"
                Delete "$Path_OB\Mopy\bish.p*"
                Delete "$Path_OB\Mopy\bolt.p*"
                Delete "$Path_OB\Mopy\bosh.p*"
                Delete "$Path_OB\Mopy\bush.p*"
                Delete "$Path_OB\Mopy\cint.p*"
                Delete "$Path_OB\Mopy\gpl.txt"
                Delete "$Path_OB\Mopy\images\*"
                RMDir  "$Path_OB\Mopy\images"
                Delete "$Path_OB\Mopy\lzma.exe"
                ;Current files:
                Delete "$Path_OB\Mopy\Wrye Bash.txt"
                Delete "$Path_OB\Mopy\Wrye Bash.html"
                Delete "$Path_OB\Mopy\Wrye Bash.exe"
                Delete "$Path_OB\Mopy\Wrye Bash.exe.log"
                Delete "$Path_OB\Mopy\Wrye Bash Launcher.p*"
                Delete "$Path_OB\Mopy\Wrye Bash Debug.p*"
                Delete "$Path_OB\Mopy\wizards.txt"
                Delete "$Path_OB\Mopy\wizards.html"
                Delete "$Path_OB\Mopy\Wizard Images\*.*"
                Delete "$Path_OB\Mopy\w9xpopen.exe"
                Delete "$Path_OB\Mopy\templates\skyrim\*.*"
                Delete "$Path_OB\Mopy\templates\oblivion\*.*"
                Delete "$Path_OB\Mopy\templates\*.*"
                Delete "$Path_OB\Mopy\templates\*"
                Delete "$Path_OB\Mopy\patch_option_reference.txt"
                Delete "$Path_OB\Mopy\patch_option_reference.html"
                Delete "$Path_OB\Mopy\license.txt"
                Delete "$Path_OB\Mopy\Ini Tweaks\Skyrim\*.*"
                Delete "$Path_OB\Mopy\Ini Tweaks\Oblivion\*.*"
                Delete "$Path_OB\Mopy\Docs\Wrye Bash Version History.html"
                Delete "$Path_OB\Mopy\Docs\Wrye Bash Technical Readme.html"
                Delete "$Path_OB\Mopy\Docs\Wrye Bash General Readme.html"
                Delete "$Path_OB\Mopy\Docs\Wrye Bash Advanced Readme.html"
                Delete "$Path_OB\Mopy\Docs\Bash Readme Template.txt"
                Delete "$Path_OB\Mopy\Docs\Bash Readme Template.html"
                Delete "$Path_OB\Mopy\Docs\wtxt_teal.css"
                Delete "$Path_OB\Mopy\Docs\wtxt_sand_small.css"
                Delete "$Path_OB\Mopy\bash\windows.pyo"
                Delete "$Path_OB\Mopy\bash\ScriptParsero"
                Delete "$Path_OB\Mopy\bash\ScriptParsero.py"
                Delete "$Path_OB\Mopy\bash\ScriptParser.p*"
                Delete "$Path_OB\Mopy\bash\Rename_CBash.dll"
                Delete "$Path_OB\Mopy\bash\l10n\Russian.*"
                Delete "$Path_OB\Mopy\bash\l10n\pt_opt.*"
                Delete "$Path_OB\Mopy\bash\l10n\Italian.*"
                Delete "$Path_OB\Mopy\bash\l10n\de.*"
                Delete "$Path_OB\Mopy\bash\l10n\Chinese*.*"
                Delete "$Path_OB\Mopy\bash\liblo.pyo"
                Delete "$Path_OB\Mopy\bash\libbsa.pyo"
                Delete "$Path_OB\Mopy\bash\libbsa.py"
                Delete "$Path_OB\Mopy\bash\images\tools\*.*"
                Delete "$Path_OB\Mopy\bash\images\readme\*.*"
                Delete "$Path_OB\Mopy\bash\images\nsis\*.*"
                Delete "$Path_OB\Mopy\bash\images\*"
                Delete "$Path_OB\Mopy\bash\gpl.txt"
                Delete "$Path_OB\Mopy\bash\game\*"
                Delete "$Path_OB\Mopy\bash\db\Skyrim_ids.pkl"
                Delete "$Path_OB\Mopy\bash\db\Oblivion_ids.pkl"
                Delete "$Path_OB\Mopy\bash\compiled\Microsoft.VC80.CRT\*"
                Delete "$Path_OB\Mopy\bash\compiled\*"
                Delete "$Path_OB\Mopy\bash\windowso"
                Delete "$Path_OB\Mopy\bash\libbsao"
                Delete "$Path_OB\Mopy\bash\cinto"
                Delete "$Path_OB\Mopy\bash\cint.p*"
                Delete "$Path_OB\Mopy\bash\chardet\*"
                Delete "$Path_OB\Mopy\bash\bwebo"
                Delete "$Path_OB\Mopy\bash\bweb.p*"
                Delete "$Path_OB\Mopy\bash\busho"
                Delete "$Path_OB\Mopy\bash\bush.p*"
                Delete "$Path_OB\Mopy\bash\breco"
                Delete "$Path_OB\Mopy\bash\brec.p*"
                Delete "$Path_OB\Mopy\bash\bosho"
                Delete "$Path_OB\Mopy\bash\bosh.p*"
                Delete "$Path_OB\Mopy\bash\Bolto"
                Delete "$Path_OB\Mopy\bash\bolt.p*"
                Delete "$Path_OB\Mopy\bash\bish.p*"
                Delete "$Path_OB\Mopy\bash\belto"
                Delete "$Path_OB\Mopy\bash\belt.p*"
                Delete "$Path_OB\Mopy\bash\basso"
                Delete "$Path_OB\Mopy\bash\bass.p*"
                Delete "$Path_OB\Mopy\bash\basho"
                Delete "$Path_OB\Mopy\bash\bashmon.p*"
                Delete "$Path_OB\Mopy\bash\bashero"
                Delete "$Path_OB\Mopy\bash\basher.p*"
                Delete "$Path_OB\Mopy\bash\bash.p*"
                Delete "$Path_OB\Mopy\bash\bargo"
                Delete "$Path_OB\Mopy\bash\barg.p*"
                Delete "$Path_OB\Mopy\bash\barbo"
                Delete "$Path_OB\Mopy\bash\barb.p*"
                Delete "$Path_OB\Mopy\bash\bapio"
                Delete "$Path_OB\Mopy\bash\bapi.p*"
                Delete "$Path_OB\Mopy\bash\balto"
                Delete "$Path_OB\Mopy\bash\balt.p*"
                Delete "$Path_OB\Mopy\bash\*.pyc"
                Delete "$Path_OB\Mopy\bash\*.py"
                Delete "$Path_OB\Mopy\bash\*.bat"
                Delete "$Path_OB\Mopy\bash\__init__.p*"
                Delete "$Path_OB\Mopy\bash.ini"
                Delete "$Path_OB\Mopy\bash_default.ini"
                Delete "$Path_OB\Mopy\bash_default_Russian.ini"
                Delete "$Path_OB\Mopy\Bash Patches\Skyrim\*.*"
                Delete "$Path_OB\Mopy\Bash Patches\Oblivion\*.*"
                Delete "$Path_OB\Mopy\*.log"
                Delete "$Path_OB\Mopy\*.bat"
                Delete "$Path_OB\Mopy\bash.ico"
                Delete "$Path_OB\Data\Docs\Bashed patch*.*"
                Delete "$Path_OB\Data\ArchiveInvalidationInvalidated!.bsa"
                RMDir  "$Path_OB\Mopy\Wizard Images"
                RMDir  "$Path_OB\Mopy\templates\skyrim"
                RMDir  "$Path_OB\Mopy\templates\oblivion"
                RMDir  "$Path_OB\Mopy\templates"
                RMDir  "$Path_OB\Mopy\Ini Tweaks\Skyrim"
                RMDir  "$Path_OB\Mopy\Ini Tweaks\Oblivion"
                RMDir  "$Path_OB\Mopy\Ini Tweaks"
                RMDir  "$Path_OB\Mopy\Docs"
                RMDir  "$Path_OB\Mopy\bash\l10n"
                RMDir  "$Path_OB\Mopy\bash\images\tools"
                RMDir  "$Path_OB\Mopy\bash\images\readme"
                RMDir  "$Path_OB\Mopy\bash\images\nsis"
                RMDir  "$Path_OB\Mopy\bash\images"
                RMDir  "$Path_OB\Mopy\bash\game"
                RMDir  "$Path_OB\Mopy\bash\db"
                RMDir  "$Path_OB\Mopy\bash\compiled\Microsoft.VC80.CRT"
                RMDir  "$Path_OB\Mopy\bash\compiled"
                RMDir  "$Path_OB\Mopy\bash\chardet"
                RMDir  "$Path_OB\Mopy\bash"
                RMDir  "$Path_OB\Mopy\Bash Patches\Skyrim"
                RMDir  "$Path_OB\Mopy\Bash Patches\Oblivion"
                RMDir  "$Path_OB\Mopy\Bash Patches"
                RMDir  "$Path_OB\Mopy\Apps"
                RMDir  "$Path_OB\Mopy"
                RMDir  "$Path_OB\Data\Ini Tweaks"
                RMDir  "$Path_OB\Data\Docs"
                RMDir  "$Path_OB\Data\Bash Patches"
                Delete "$SMPROGRAMS\Wrye Bash\*oblivion*"
            ${EndIf}
        ${EndIf}
        ${If} $CheckState_Nehrim == ${BST_CHECKED}
            ${If} $Path_Nehrim != $Empty
                DeleteRegValue HKLM "SOFTWARE\Wrye Bash" "Nehrim Path"
                DeleteRegValue HKLM "SOFTWARE\Wrye Bash" "Nehrim Python Version"
                DeleteRegValue HKLM "SOFTWARE\Wrye Bash" "Nehrim Standalone Version"
                ;First delete OLD version files:
                Delete "$Path_Nehrim\Data\Docs\Bashed Lists.txt"
                Delete "$Path_Nehrim\Data\Docs\Bashed Lists.html"
                Delete "$Path_Nehrim\Mopy\uninstall.exe"
                Delete "$Path_Nehrim\Data\Ini Tweaks\Autosave, Never.ini"
                Delete "$Path_Nehrim\Data\Ini Tweaks\Autosave, ~Always.ini"
                Delete "$Path_Nehrim\Data\Ini Tweaks\Border Regions, Disabled.ini"
                Delete "$Path_Nehrim\Data\Ini Tweaks\Border Regions, ~Enabled.ini"
                Delete "$Path_Nehrim\Data\Ini Tweaks\Fonts 1, ~Default.ini"
                Delete "$Path_Nehrim\Data\Ini Tweaks\Fonts, ~Default.ini"
                Delete "$Path_Nehrim\Data\Ini Tweaks\Grass, Fade 4k-5k.ini"
                Delete "$Path_Nehrim\Data\Ini Tweaks\Intro Movies, Disabled.ini"
                Delete "$Path_Nehrim\Data\Ini Tweaks\Intro Movies, Normal.ini"
                Delete "$Path_Nehrim\Data\Ini Tweaks\Joystick, ~Disabled.ini"
                Delete "$Path_Nehrim\Data\Ini Tweaks\Joystick, ~Enabled.ini"
                Delete "$Path_Nehrim\Data\Ini Tweaks\Local Map Shader, Disabled.ini"
                Delete "$Path_Nehrim\Data\Ini Tweaks\Local Map Shader, ~Enabled.ini"
                Delete "$Path_Nehrim\Data\Ini Tweaks\Music, Disabled.ini"
                Delete "$Path_Nehrim\Data\Ini Tweaks\Music, Enabled.ini"
                Delete "$Path_Nehrim\Data\Ini Tweaks\Refraction Shader, Disabled.ini"
                Delete "$Path_Nehrim\Data\Ini Tweaks\Refraction Shader, ~Enabled.ini"
                Delete "$Path_Nehrim\Data\Ini Tweaks\Save Backups, 1.ini"
                Delete "$Path_Nehrim\Data\Ini Tweaks\Save Backups, 2.ini"
                Delete "$Path_Nehrim\Data\Ini Tweaks\Save Backups, 3.ini"
                Delete "$Path_Nehrim\Data\Ini Tweaks\Save Backups, 5.ini"
                Delete "$Path_Nehrim\Data\Ini Tweaks\Screenshot, ~Disabled.ini"
                Delete "$Path_Nehrim\Data\Ini Tweaks\Screenshot, ~ENabled.ini"
                Delete "$Path_Nehrim\Data\Ini Tweaks\ShadowMapResolution, 1024.ini"
                Delete "$Path_Nehrim\Data\Ini Tweaks\ShadowMapResolution, 256 [default].ini"
                Delete "$Path_Nehrim\Data\Ini Tweaks\Sound Card Channels, 8.ini"
                Delete "$Path_Nehrim\Data\Ini Tweaks\Sound Card Channels, 16.ini"
                Delete "$Path_Nehrim\Data\Ini Tweaks\Sound Card Channels, 24.ini"
                Delete "$Path_Nehrim\Data\Ini Tweaks\Sound Card Channels, 48.ini"
                Delete "$Path_Nehrim\Data\Ini Tweaks\Sound Card Channels, 64.ini"
                Delete "$Path_Nehrim\Data\Ini Tweaks\Sound Card Channels, 96.ini"
                Delete "$Path_Nehrim\Data\Ini Tweaks\Sound Card Channels, 128.ini"
                Delete "$Path_Nehrim\Data\Ini Tweaks\Sound Card Channels, 192.ini"
                Delete "$Path_Nehrim\Data\Ini Tweaks\Sound Card Channels, ~ [Oblivion].ini"
                Delete "$Path_Nehrim\Data\Ini Tweaks\Sound Card Channels,  [Oblivion].ini"
                Delete "$Path_Nehrim\Data\Ini Tweaks\Sound, Disabled.ini"
                Delete "$Path_Nehrim\Data\Ini Tweaks\Sound, Enabled.ini"
                Delete "$Path_Nehrim\Data\Bash Patches\Crowded Cities 15_Alternate_Names.csv"
                Delete "$Path_Nehrim\Data\Bash Patches\Crowded Cities 15_Names.csv"
                Delete "$Path_Nehrim\Data\Bash Patches\Crowded Cities 30_Alternate_Names.csv"
                Delete "$Path_Nehrim\Data\Bash Patches\Crowded Cities 30_Names.csv"
                Delete "$Path_Nehrim\Data\Bash Patches\Crowded Roads Revamped_Names.csv"
                Delete "$Path_Nehrim\Data\Bash Patches\Crowded Roads Revisited_Alternate_Names.csv"
                Delete "$Path_Nehrim\Data\Bash Patches\Crowded Roads Revisited_Names.csv"
                Delete "$Path_Nehrim\Data\Bash Patches\PTRoamingNPCs_Names.csv"
                Delete "$Path_Nehrim\Mopy\Wrye Bash Advanced Readme.html"
                Delete "$Path_Nehrim\Mopy\Wrye Bash General Readme.html"
                Delete "$Path_Nehrim\Mopy\Wrye Bash Technical Readme.html"
                Delete "$Path_Nehrim\Mopy\Wrye Bash Version History.html"
                ;As of 294 the below are obselete locations or files.
                Delete "$Path_Nehrim\Mopy\7z.*"
                Delete "$Path_Nehrim\Mopy\CBash.dll"
                Delete "$Path_Nehrim\Mopy\Data\Italian.*"
                Delete "$Path_Nehrim\Mopy\Data\Oblivion_ids.pkl"
                Delete "$Path_Nehrim\Mopy\Data\Russian.*"
                Delete "$Path_Nehrim\Mopy\Data\de.*"
                Delete "$Path_Nehrim\Mopy\Data\pt_opt.*"
                Delete "$Path_Nehrim\Mopy\Data\Actor Levels\OOO, 1.23 Mincapped.csv"
                Delete "$Path_Nehrim\Mopy\Data\Actor Levels\OOO, 1.23 Uncapped.csv"
                RMDir  "$Path_Nehrim\Mopy\Data\Actor Levels"
                RMDir  "$Path_Nehrim\Mopy\Data"
                Delete "$Path_Nehrim\Mopy\DebugLog(Python2.6).bat"
                Delete "$Path_Nehrim\Mopy\Extras\*"
                Delete "$Path_Nehrim\Mopy\ScriptParser.p*"
                Delete "$Path_Nehrim\Mopy\balt.p*"
                Delete "$Path_Nehrim\Mopy\barb.p*"
                Delete "$Path_Nehrim\Mopy\barg.p*"
                Delete "$Path_Nehrim\Mopy\bash.p*"
                Delete "$Path_Nehrim\Mopy\basher.p*"
                Delete "$Path_Nehrim\Mopy\bashmon.p*"
                Delete "$Path_Nehrim\Mopy\belt.p*"
                Delete "$Path_Nehrim\Mopy\bish.p*"
                Delete "$Path_Nehrim\Mopy\bolt.p*"
                Delete "$Path_Nehrim\Mopy\bosh.p*"
                Delete "$Path_Nehrim\Mopy\bush.p*"
                Delete "$Path_Nehrim\Mopy\cint.p*"
                Delete "$Path_Nehrim\Mopy\bash\keywordWIZBAIN.p*"
                Delete "$Path_Nehrim\Mopy\bash\keywordWIZBAIN2.p*"
                Delete "$Path_Nehrim\Mopy\gpl.txt"
                Delete "$Path_Nehrim\Mopy\images\*"
                RMDir  "$Path_Nehrim\Mopy\images"
                Delete "$Path_Nehrim\Mopy\lzma.exe"
                ;Current files:
                Delete "$Path_Nehrim\Mopy\Wrye Bash.txt"
                Delete "$Path_Nehrim\Mopy\Wrye Bash.html"
                Delete "$Path_Nehrim\Mopy\Wrye Bash.exe"
                Delete "$Path_Nehrim\Mopy\Wrye Bash.exe.log"
                Delete "$Path_Nehrim\Mopy\Wrye Bash Launcher.p*"
                Delete "$Path_Nehrim\Mopy\Wrye Bash Debug.p*"
                Delete "$Path_Nehrim\Mopy\wizards.txt"
                Delete "$Path_Nehrim\Mopy\wizards.html"
                Delete "$Path_Nehrim\Mopy\Wizard Images\*.*"
                Delete "$Path_Nehrim\Mopy\w9xpopen.exe"
                Delete "$Path_Nehrim\Mopy\templates\skyrim\*.*"
                Delete "$Path_Nehrim\Mopy\templates\oblivion\*.*"
                Delete "$Path_Nehrim\Mopy\templates\*.*"
                Delete "$Path_Nehrim\Mopy\templates\*"
                Delete "$Path_Nehrim\Mopy\patch_option_reference.txt"
                Delete "$Path_Nehrim\Mopy\patch_option_reference.html"
                Delete "$Path_Nehrim\Mopy\license.txt"
                Delete "$Path_Nehrim\Mopy\Ini Tweaks\Skyrim\*.*"
                Delete "$Path_Nehrim\Mopy\Ini Tweaks\Oblivion\*.*"
                Delete "$Path_Nehrim\Mopy\Docs\Wrye Bash Version History.html"
                Delete "$Path_Nehrim\Mopy\Docs\Wrye Bash Technical Readme.html"
                Delete "$Path_Nehrim\Mopy\Docs\Wrye Bash General Readme.html"
                Delete "$Path_Nehrim\Mopy\Docs\Wrye Bash Advanced Readme.html"
                Delete "$Path_Nehrim\Mopy\Docs\wtxt_teal.css"
                Delete "$Path_Nehrim\Mopy\Docs\wtxt_sand_small.css"
                Delete "$Path_Nehrim\Mopy\Docs\Bash Readme Template.txt"
                Delete "$Path_Nehrim\Mopy\Docs\Bash Readme Template.html"
                Delete "$Path_Nehrim\Mopy\bash\windows.pyo"
                Delete "$Path_Nehrim\Mopy\bash\ScriptParsero"
                Delete "$Path_Nehrim\Mopy\bash\ScriptParsero.py"
                Delete "$Path_Nehrim\Mopy\bash\ScriptParser.p*"
                Delete "$Path_Nehrim\Mopy\bash\Rename_CBash.dll"
                Delete "$Path_Nehrim\Mopy\bash\l10n\Russian.*"
                Delete "$Path_Nehrim\Mopy\bash\l10n\pt_opt.*"
                Delete "$Path_Nehrim\Mopy\bash\l10n\Italian.*"
                Delete "$Path_Nehrim\Mopy\bash\l10n\de.*"
                Delete "$Path_Nehrim\Mopy\bash\l10n\Chinese*.*"
                Delete "$Path_Nehrim\Mopy\bash\liblo.pyo"
                Delete "$Path_Nehrim\Mopy\bash\libbsa.pyo"
                Delete "$Path_Nehrim\Mopy\bash\libbsa.py"
                Delete "$Path_Nehrim\Mopy\bash\images\tools\*.*"
                Delete "$Path_Nehrim\Mopy\bash\images\readme\*.*"
                Delete "$Path_Nehrim\Mopy\bash\images\nsis\*.*"
                Delete "$Path_Nehrim\Mopy\bash\images\*"
                Delete "$Path_Nehrim\Mopy\bash\gpl.txt"
                Delete "$Path_Nehrim\Mopy\bash\game\*"
                Delete "$Path_Nehrim\Mopy\bash\db\Skyrim_ids.pkl"
                Delete "$Path_Nehrim\Mopy\bash\db\Oblivion_ids.pkl"
                Delete "$Path_Nehrim\Mopy\bash\compiled\Microsoft.VC80.CRT\*"
                Delete "$Path_Nehrim\Mopy\bash\compiled\*"
                Delete "$Path_Nehrim\Mopy\bash\windowso"
                Delete "$Path_Nehrim\Mopy\bash\libbsao"
                Delete "$Path_Nehrim\Mopy\bash\cinto"
                Delete "$Path_Nehrim\Mopy\bash\cint.p*"
                Delete "$Path_Nehrim\Mopy\bash\chardet\*"
                Delete "$Path_Nehrim\Mopy\bash\bwebo"
                Delete "$Path_Nehrim\Mopy\bash\bweb.p*"
                Delete "$Path_Nehrim\Mopy\bash\busho"
                Delete "$Path_Nehrim\Mopy\bash\bush.p*"
                Delete "$Path_Nehrim\Mopy\bash\breco"
                Delete "$Path_Nehrim\Mopy\bash\brec.p*"
                Delete "$Path_Nehrim\Mopy\bash\bosho"
                Delete "$Path_Nehrim\Mopy\bash\bosh.p*"
                Delete "$Path_Nehrim\Mopy\bash\Bolto"
                Delete "$Path_Nehrim\Mopy\bash\bolt.p*"
                Delete "$Path_Nehrim\Mopy\bash\bish.p*"
                Delete "$Path_Nehrim\Mopy\bash\belto"
                Delete "$Path_Nehrim\Mopy\bash\belt.p*"
                Delete "$Path_Nehrim\Mopy\bash\basso"
                Delete "$Path_Nehrim\Mopy\bash\bass.p*"
                Delete "$Path_Nehrim\Mopy\bash\basho"
                Delete "$Path_Nehrim\Mopy\bash\bashmon.p*"
                Delete "$Path_Nehrim\Mopy\bash\bashero"
                Delete "$Path_Nehrim\Mopy\bash\basher.p*"
                Delete "$Path_Nehrim\Mopy\bash\bash.p*"
                Delete "$Path_Nehrim\Mopy\bash\bargo"
                Delete "$Path_Nehrim\Mopy\bash\barg.p*"
                Delete "$Path_Nehrim\Mopy\bash\barbo"
                Delete "$Path_Nehrim\Mopy\bash\barb.p*"
                Delete "$Path_Nehrim\Mopy\bash\bapio"
                Delete "$Path_Nehrim\Mopy\bash\bapi.p*"
                Delete "$Path_Nehrim\Mopy\bash\balto"
                Delete "$Path_Nehrim\Mopy\bash\balt.p*"
                Delete "$Path_Nehrim\Mopy\bash\*.pyc"
                Delete "$Path_Nehrim\Mopy\bash\*.py"
                Delete "$Path_Nehrim\Mopy\bash\*.bat"
                Delete "$Path_Nehrim\Mopy\bash\__init__.p*"
                Delete "$Path_Nehrim\Mopy\bash.ini"
                Delete "$Path_Nehrim\Mopy\bash_default.ini"
                Delete "$Path_Nehrim\Mopy\bash_default_Russian.ini"
                Delete "$Path_Nehrim\Mopy\Bash Patches\Skyrim\*.*"
                Delete "$Path_Nehrim\Mopy\Bash Patches\Oblivion\*.*"
                Delete "$Path_Nehrim\Mopy\*.log"
                Delete "$Path_Nehrim\Mopy\*.bat"
                Delete "$Path_Nehrim\Mopy\bash.ico"
                Delete "$Path_Nehrim\Data\Docs\Bashed patch*.*"
                Delete "$Path_Nehrim\Data\ArchiveInvalidationInvalidated!.bsa"
                RMDir  "$Path_Nehrim\Mopy\Wizard Images"
                RMDir  "$Path_Nehrim\Mopy\templates\skyrim"
                RMDir  "$Path_Nehrim\Mopy\templates\oblivion"
                RMDir  "$Path_Nehrim\Mopy\templates"
                RMDir  "$Path_Nehrim\Mopy\Ini Tweaks\Skyrim"
                RMDir  "$Path_Nehrim\Mopy\Ini Tweaks\Oblivion"
                RMDir  "$Path_Nehrim\Mopy\Ini Tweaks"
                RMDir  "$Path_Nehrim\Mopy\Docs"
                RMDir  "$Path_Nehrim\Mopy\bash\l10n"
                RMDir  "$Path_Nehrim\Mopy\bash\images\tools"
                RMDir  "$Path_Nehrim\Mopy\bash\images\readme"
                RMDir  "$Path_Nehrim\Mopy\bash\images\nsis"
                RMDir  "$Path_Nehrim\Mopy\bash\images"
                RMDir  "$Path_Nehrim\Mopy\bash\game"
                RMDir  "$Path_Nehrim\Mopy\bash\db"
                RMDir  "$Path_Nehrim\Mopy\bash\compiled\Microsoft.VC80.CRT"
                RMDir  "$Path_Nehrim\Mopy\bash\compiled"
                RMDir  "$Path_Nehrim\Mopy\bash\chardet"
                RMDir  "$Path_Nehrim\Mopy\bash"
                RMDir  "$Path_Nehrim\Mopy\Bash Patches\Skyrim"
                RMDir  "$Path_Nehrim\Mopy\Bash Patches\Oblivion"
                RMDir  "$Path_Nehrim\Mopy\Bash Patches"
                RMDir  "$Path_Nehrim\Mopy\Apps"
                RMDir  "$Path_Nehrim\Mopy"
                RMDir  "$Path_Nehrim\Data\Ini Tweaks"
                RMDir  "$Path_Nehrim\Data\Docs"
                RMDir  "$Path_Nehrim\Data\Bash Patches"
                Delete "$SMPROGRAMS\Wrye Bash\*Nehrim*"
            ${EndIf}
        ${EndIf}
        ${If} $CheckState_Skyrim == ${BST_CHECKED}
            ${If} $Path_Skyrim != $Empty
                DeleteRegValue HKLM "SOFTWARE\Wrye Bash" "Skyrim Path"
                DeleteRegValue HKLM "SOFTWARE\Wrye Bash" "Skyrim Python Version"
                DeleteRegValue HKLM "SOFTWARE\Wrye Bash" "Skyrim Standalone Version"
                ;First delete OLD version files:
                Delete "$Path_Skyrim\Data\Docs\Bashed Lists.txt"
                Delete "$Path_Skyrim\Data\Docs\Bashed Lists.html"
                Delete "$Path_Skyrim\Mopy\uninstall.exe"
                Delete "$Path_Skyrim\Data\ArchiveInvalidationInvalidated!.bsa"
                Delete "$Path_Skyrim\Data\Bash Patches\Assorted to Cobl.csv"
                Delete "$Path_Skyrim\Data\Bash Patches\Assorted_Exhaust.csv"
                Delete "$Path_Skyrim\Data\Bash Patches\Bash_Groups.csv"
                Delete "$Path_Skyrim\Data\Bash Patches\Bash_MFact.csv"
                Delete "$Path_Skyrim\Data\Bash Patches\ShiveringIsleTravellers_Names.csv"
                Delete "$Path_Skyrim\Data\Bash Patches\TamrielTravellers_Names.csv"
                Delete "$Path_Skyrim\Data\Bash Patches\Guard_Names.csv"
                Delete "$Path_Skyrim\Data\Bash Patches\Kmacg94_Exhaust.csv"
                Delete "$Path_Skyrim\Data\Bash Patches\P1DCandles_Formids.csv"
                Delete "$Path_Skyrim\Data\Bash Patches\OOO_Potion_Names.csv"
                Delete "$Path_Skyrim\Data\Bash Patches\Random_NPC_Alternate_Names.csv"
                Delete "$Path_Skyrim\Data\Bash Patches\Random_NPC_Names.csv"
                Delete "$Path_Skyrim\Data\Bash Patches\Rational_Names.csv"
                Delete "$Path_Skyrim\Data\Bash Patches\TI to Cobl_Formids.csv"
                Delete "$Path_Skyrim\Data\Bash Patches\taglist.txt"
                Delete "$Path_Skyrim\Data\Bash Patches\OOO, 1.23 Mincapped_NPC_Levels.csv"
                Delete "$Path_Skyrim\Data\Bash Patches\OOO, 1.23 Uncapped_NPC_Levels.csv"
                Delete "$Path_Skyrim\Data\Ini Tweaks\Autosave, Never.ini"
                Delete "$Path_Skyrim\Data\Ini Tweaks\Autosave, ~Always.ini"
                Delete "$Path_Skyrim\Data\Ini Tweaks\Border Regions, Disabled.ini"
                Delete "$Path_Skyrim\Data\Ini Tweaks\Border Regions, ~Enabled.ini"
                Delete "$Path_Skyrim\Data\Ini Tweaks\Fonts 1, ~Default.ini"
                Delete "$Path_Skyrim\Data\Ini Tweaks\Fonts, ~Default.ini"
                Delete "$Path_Skyrim\Data\Ini Tweaks\Grass, Fade 4k-5k.ini"
                Delete "$Path_Skyrim\Data\Ini Tweaks\Intro Movies, Disabled.ini"
                Delete "$Path_Skyrim\Data\Ini Tweaks\Intro Movies, Normal.ini"
                Delete "$Path_Skyrim\Data\Ini Tweaks\Joystick, ~Disabled.ini"
                Delete "$Path_Skyrim\Data\Ini Tweaks\Joystick, ~Enabled.ini"
                Delete "$Path_Skyrim\Data\Ini Tweaks\Local Map Shader, Disabled.ini"
                Delete "$Path_Skyrim\Data\Ini Tweaks\Local Map Shader, ~Enabled.ini"
                Delete "$Path_Skyrim\Data\Ini Tweaks\Music, Disabled.ini"
                Delete "$Path_Skyrim\Data\Ini Tweaks\Music, Enabled.ini"
                Delete "$Path_Skyrim\Data\Ini Tweaks\Refraction Shader, Disabled.ini"
                Delete "$Path_Skyrim\Data\Ini Tweaks\Refraction Shader, ~Enabled.ini"
                Delete "$Path_Skyrim\Data\Ini Tweaks\Save Backups, 1.ini"
                Delete "$Path_Skyrim\Data\Ini Tweaks\Save Backups, 2.ini"
                Delete "$Path_Skyrim\Data\Ini Tweaks\Save Backups, 3.ini"
                Delete "$Path_Skyrim\Data\Ini Tweaks\Save Backups, 5.ini"
                Delete "$Path_Skyrim\Data\Ini Tweaks\Screenshot, ~Disabled.ini"
                Delete "$Path_Skyrim\Data\Ini Tweaks\Screenshot, ~ENabled.ini"
                Delete "$Path_Skyrim\Data\Ini Tweaks\ShadowMapResolution, 1024.ini"
                Delete "$Path_Skyrim\Data\Ini Tweaks\ShadowMapResolution, 256 [default].ini"
                Delete "$Path_Skyrim\Data\Ini Tweaks\Sound Card Channels, 8.ini"
                Delete "$Path_Skyrim\Data\Ini Tweaks\Sound Card Channels, 16.ini"
                Delete "$Path_Skyrim\Data\Ini Tweaks\Sound Card Channels, 24.ini"
                Delete "$Path_Skyrim\Data\Ini Tweaks\Sound Card Channels, 48.ini"
                Delete "$Path_Skyrim\Data\Ini Tweaks\Sound Card Channels, 64.ini"
                Delete "$Path_Skyrim\Data\Ini Tweaks\Sound Card Channels, 96.ini"
                Delete "$Path_Skyrim\Data\Ini Tweaks\Sound Card Channels, 128.ini"
                Delete "$Path_Skyrim\Data\Ini Tweaks\Sound Card Channels, 192.ini"
                Delete "$Path_Skyrim\Data\Ini Tweaks\Sound Card Channels, ~ [Oblivion].ini"
                Delete "$Path_Skyrim\Data\Ini Tweaks\Sound Card Channels,  [Oblivion].ini"
                Delete "$Path_Skyrim\Data\Ini Tweaks\Sound, Disabled.ini"
                Delete "$Path_Skyrim\Data\Ini Tweaks\Sound, Enabled.ini"
                Delete "$Path_Skyrim\Data\Bash Patches\Crowded Cities 15_Alternate_Names.csv"
                Delete "$Path_Skyrim\Data\Bash Patches\Crowded Cities 15_Names.csv"
                Delete "$Path_Skyrim\Data\Bash Patches\Crowded Cities 30_Alternate_Names.csv"
                Delete "$Path_Skyrim\Data\Bash Patches\Crowded Cities 30_Names.csv"
                Delete "$Path_Skyrim\Data\Bash Patches\Crowded Roads Revamped_Names.csv"
                Delete "$Path_Skyrim\Data\Bash Patches\Crowded Roads Revisited_Alternate_Names.csv"
                Delete "$Path_Skyrim\Data\Bash Patches\Crowded Roads Revisited_Names.csv"
                Delete "$Path_Skyrim\Data\Bash Patches\PTRoamingNPCs_Names.csv"
                Delete "$Path_Skyrim\Mopy\Wrye Bash Advanced Readme.html"
                Delete "$Path_Skyrim\Mopy\Wrye Bash General Readme.html"
                Delete "$Path_Skyrim\Mopy\Wrye Bash Technical Readme.html"
                Delete "$Path_Skyrim\Mopy\Wrye Bash Version History.html"
                ;As of 294 the below are obselete locations or files.
                Delete "$Path_Skyrim\Mopy\7z.*"
                Delete "$Path_Skyrim\Mopy\CBash.dll"
                Delete "$Path_Skyrim\Mopy\Data\Italian.*"
                Delete "$Path_Skyrim\Mopy\Data\Oblivion_ids.pkl"
                Delete "$Path_Skyrim\Mopy\Data\Russian.*"
                Delete "$Path_Skyrim\Mopy\Data\de.*"
                Delete "$Path_Skyrim\Mopy\Data\pt_opt.*"
                Delete "$Path_Skyrim\Mopy\Data\Actor Levels\OOO, 1.23 Mincapped.csv"
                Delete "$Path_Skyrim\Mopy\Data\Actor Levels\OOO, 1.23 Uncapped.csv"
                RMDir  "$Path_Skyrim\Mopy\Data\Actor Levels"
                RMDir  "$Path_Skyrim\Mopy\Data"
                Delete "$Path_Skyrim\Mopy\DebugLog(Python2.6).bat"
                Delete "$Path_Skyrim\Mopy\Extras\*"
                Delete "$Path_Skyrim\Mopy\ScriptParser.p*"
                Delete "$Path_Skyrim\Mopy\balt.p*"
                Delete "$Path_Skyrim\Mopy\barb.p*"
                Delete "$Path_Skyrim\Mopy\barg.p*"
                Delete "$Path_Skyrim\Mopy\bash.p*"
                Delete "$Path_Skyrim\Mopy\basher.p*"
                Delete "$Path_Skyrim\Mopy\bashmon.p*"
                Delete "$Path_Skyrim\Mopy\belt.p*"
                Delete "$Path_Skyrim\Mopy\bish.p*"
                Delete "$Path_Skyrim\Mopy\bolt.p*"
                Delete "$Path_Skyrim\Mopy\bosh.p*"
                Delete "$Path_Skyrim\Mopy\bush.p*"
                Delete "$Path_Skyrim\Mopy\cint.p*"
                Delete "$Path_Skyrim\Mopy\gpl.txt"
                Delete "$Path_Skyrim\Mopy\images\*"
                RMDir  "$Path_Skyrim\Mopy\images"
                Delete "$Path_Skyrim\Mopy\lzma.exe"
                ;Current files:
                Delete "$Path_Skyrim\Mopy\Wrye Bash.txt"
                Delete "$Path_Skyrim\Mopy\Wrye Bash.html"
                Delete "$Path_Skyrim\Mopy\Wrye Bash.exe"
                Delete "$Path_Skyrim\Mopy\Wrye Bash.exe.log"
                Delete "$Path_Skyrim\Mopy\Wrye Bash Launcher.p*"
                Delete "$Path_Skyrim\Mopy\Wrye Bash Debug.p*"
                Delete "$Path_Skyrim\Mopy\wizards.txt"
                Delete "$Path_Skyrim\Mopy\wizards.html"
                Delete "$Path_Skyrim\Mopy\Wizard Images\*.*"
                Delete "$Path_Skyrim\Mopy\w9xpopen.exe"
                Delete "$Path_Skyrim\Mopy\templates\skyrim\*.*"
                Delete "$Path_Skyrim\Mopy\templates\oblivion\*.*"
                Delete "$Path_Skyrim\Mopy\templates\*.*"
                Delete "$Path_Skyrim\Mopy\templates\*"
                Delete "$Path_Skyrim\Mopy\patch_option_reference.txt"
                Delete "$Path_Skyrim\Mopy\patch_option_reference.html"
                Delete "$Path_Skyrim\Mopy\license.txt"
                Delete "$Path_Skyrim\Mopy\Ini Tweaks\Skyrim\*.*"
                Delete "$Path_Skyrim\Mopy\Ini Tweaks\Oblivion\*.*"
                Delete "$Path_Skyrim\Mopy\Docs\Wrye Bash Version History.html"
                Delete "$Path_Skyrim\Mopy\Docs\Wrye Bash Technical Readme.html"
                Delete "$Path_Skyrim\Mopy\Docs\Wrye Bash General Readme.html"
                Delete "$Path_Skyrim\Mopy\Docs\Wrye Bash Advanced Readme.html"
                Delete "$Path_Skyrim\Mopy\Docs\wtxt_teal.css"
                Delete "$Path_Skyrim\Mopy\Docs\wtxt_sand_small.css"
                Delete "$Path_Skyrim\Mopy\Docs\Bash Readme Template.txt"
                Delete "$Path_Skyrim\Mopy\Docs\Bash Readme Template.html"
                Delete "$Path_Skyrim\Mopy\bash\windows.pyo"
                Delete "$Path_Skyrim\Mopy\bash\ScriptParsero"
                Delete "$Path_Skyrim\Mopy\bash\ScriptParsero.py"
                Delete "$Path_Skyrim\Mopy\bash\ScriptParser.p*"
                Delete "$Path_Skyrim\Mopy\bash\Rename_CBash.dll"
                Delete "$Path_Skyrim\Mopy\bash\l10n\Russian.*"
                Delete "$Path_Skyrim\Mopy\bash\l10n\pt_opt.*"
                Delete "$Path_Skyrim\Mopy\bash\l10n\Italian.*"
                Delete "$Path_Skyrim\Mopy\bash\l10n\de.*"
                Delete "$Path_Skyrim\Mopy\bash\l10n\Chinese*.*"
                Delete "$Path_Skyrim\Mopy\bash\liblo.pyo"
                Delete "$Path_Skyrim\Mopy\bash\libbsa.pyo"
                Delete "$Path_Skyrim\Mopy\bash\libbsa.py"
                Delete "$Path_Skyrim\Mopy\bash\images\tools\*.*"
                Delete "$Path_Skyrim\Mopy\bash\images\readme\*.*"
                Delete "$Path_Skyrim\Mopy\bash\images\nsis\*.*"
                Delete "$Path_Skyrim\Mopy\bash\images\*"
                Delete "$Path_Skyrim\Mopy\bash\gpl.txt"
                Delete "$Path_Skyrim\Mopy\bash\game\*"
                Delete "$Path_Skyrim\Mopy\bash\db\Skyrim_ids.pkl"
                Delete "$Path_Skyrim\Mopy\bash\db\Oblivion_ids.pkl"
                Delete "$Path_Skyrim\Mopy\bash\compiled\Microsoft.VC80.CRT\*"
                Delete "$Path_Skyrim\Mopy\bash\compiled\*"
                Delete "$Path_Skyrim\Mopy\bash\windowso"
                Delete "$Path_Skyrim\Mopy\bash\libbsao"
                Delete "$Path_Skyrim\Mopy\bash\cinto"
                Delete "$Path_Skyrim\Mopy\bash\cint.p*"
                Delete "$Path_Skyrim\Mopy\bash\chardet\*"
                Delete "$Path_Skyrim\Mopy\bash\bwebo"
                Delete "$Path_Skyrim\Mopy\bash\bweb.p*"
                Delete "$Path_Skyrim\Mopy\bash\busho"
                Delete "$Path_Skyrim\Mopy\bash\bush.p*"
                Delete "$Path_Skyrim\Mopy\bash\breco"
                Delete "$Path_Skyrim\Mopy\bash\brec.p*"
                Delete "$Path_Skyrim\Mopy\bash\bosho"
                Delete "$Path_Skyrim\Mopy\bash\bosh.p*"
                Delete "$Path_Skyrim\Mopy\bash\Bolto"
                Delete "$Path_Skyrim\Mopy\bash\bolt.p*"
                Delete "$Path_Skyrim\Mopy\bash\bish.p*"
                Delete "$Path_Skyrim\Mopy\bash\belto"
                Delete "$Path_Skyrim\Mopy\bash\belt.p*"
                Delete "$Path_Skyrim\Mopy\bash\basso"
                Delete "$Path_Skyrim\Mopy\bash\bass.p*"
                Delete "$Path_Skyrim\Mopy\bash\basho"
                Delete "$Path_Skyrim\Mopy\bash\bashmon.p*"
                Delete "$Path_Skyrim\Mopy\bash\bashero"
                Delete "$Path_Skyrim\Mopy\bash\basher.p*"
                Delete "$Path_Skyrim\Mopy\bash\bash.p*"
                Delete "$Path_Skyrim\Mopy\bash\bargo"
                Delete "$Path_Skyrim\Mopy\bash\barg.p*"
                Delete "$Path_Skyrim\Mopy\bash\barbo"
                Delete "$Path_Skyrim\Mopy\bash\barb.p*"
                Delete "$Path_Skyrim\Mopy\bash\bapio"
                Delete "$Path_Skyrim\Mopy\bash\bapi.p*"
                Delete "$Path_Skyrim\Mopy\bash\balto"
                Delete "$Path_Skyrim\Mopy\bash\balt.p*"
                Delete "$Path_Skyrim\Mopy\bash\*.pyc"
                Delete "$Path_Skyrim\Mopy\bash\*.py"
                Delete "$Path_Skyrim\Mopy\bash\*.bat"
                Delete "$Path_Skyrim\Mopy\bash\__init__.p*"
                Delete "$Path_Skyrim\Mopy\bash.ini"
                Delete "$Path_Skyrim\Mopy\bash_default.ini"
                Delete "$Path_Skyrim\Mopy\bash_default_Russian.ini"
                Delete "$Path_Skyrim\Mopy\Bash Patches\Skyrim\*.*"
                Delete "$Path_Skyrim\Mopy\Bash Patches\Oblivion\*.*"
                Delete "$Path_Skyrim\Mopy\*.log"
                Delete "$Path_Skyrim\Mopy\*.bat"
                Delete "$Path_Skyrim\Mopy\bash.ico"
                Delete "$Path_Skyrim\Data\Docs\Bashed patch*.*"
                Delete "$Path_Skyrim\Data\ArchiveInvalidationInvalidated!.bsa"
                RMDir  "$Path_Skyrim\Mopy\Wizard Images"
                RMDir  "$Path_Skyrim\Mopy\templates\skyrim"
                RMDir  "$Path_Skyrim\Mopy\templates\oblivion"
                RMDir  "$Path_Skyrim\Mopy\templates"
                RMDir  "$Path_Skyrim\Mopy\Ini Tweaks\Skyrim"
                RMDir  "$Path_Skyrim\Mopy\Ini Tweaks\Oblivion"
                RMDir  "$Path_Skyrim\Mopy\Ini Tweaks"
                RMDir  "$Path_Skyrim\Mopy\Docs"
                RMDir  "$Path_Skyrim\Mopy\bash\l10n"
                RMDir  "$Path_Skyrim\Mopy\bash\images\tools"
                RMDir  "$Path_Skyrim\Mopy\bash\images\readme"
                RMDir  "$Path_Skyrim\Mopy\bash\images\nsis"
                RMDir  "$Path_Skyrim\Mopy\bash\images"
                RMDir  "$Path_Skyrim\Mopy\bash\game"
                RMDir  "$Path_Skyrim\Mopy\bash\db"
                RMDir  "$Path_Skyrim\Mopy\bash\compiled\Microsoft.VC80.CRT"
                RMDir  "$Path_Skyrim\Mopy\bash\compiled"
                RMDir  "$Path_Skyrim\Mopy\bash\chardet"
                RMDir  "$Path_Skyrim\Mopy\bash"
                RMDir  "$Path_Skyrim\Mopy\Bash Patches\Skyrim"
                RMDir  "$Path_Skyrim\Mopy\Bash Patches\Oblivion"
                RMDir  "$Path_Skyrim\Mopy\Bash Patches"
                RMDir  "$Path_Skyrim\Mopy\Apps"
                RMDir  "$Path_Skyrim\Mopy"
                RMDir  "$Path_Skyrim\Data\Ini Tweaks"
                RMDir  "$Path_Skyrim\Data\Docs"
                RMDir  "$Path_Skyrim\Data\Bash Patches"
                Delete "$SMPROGRAMS\Wrye Bash\*Skyrim*"
            ${EndIf}
        ${EndIf}
        ${If} $CheckState_Ex1 == ${BST_CHECKED}
            ${If} $Path_Ex1 != $Empty
                DeleteRegValue HKLM "SOFTWARE\Wrye Bash" "Extra Path 1"
                DeleteRegValue HKLM "SOFTWARE\Wrye Bash" "Extra Path 1 Python Version"
                DeleteRegValue HKLM "SOFTWARE\Wrye Bash" "Extra Path 1 Standalone Version"
                ;First delete OLD version files:
                Delete "$Path_Ex1\Data\Docs\Bashed Lists.txt"
                Delete "$Path_Ex1\Data\Docs\Bashed Lists.html"
                Delete "$Path_Ex1\Mopy\uninstall.exe"
                Delete "$Path_Ex1\Data\Ini Tweaks\Autosave, Never.ini"
                Delete "$Path_Ex1\Data\Ini Tweaks\Autosave, ~Always.ini"
                Delete "$Path_Ex1\Data\Ini Tweaks\Border Regions, Disabled.ini"
                Delete "$Path_Ex1\Data\Ini Tweaks\Border Regions, ~Enabled.ini"
                Delete "$Path_Ex1\Data\Ini Tweaks\Fonts 1, ~Default.ini"
                Delete "$Path_Ex1\Data\Ini Tweaks\Fonts, ~Default.ini"
                Delete "$Path_Ex1\Data\Ini Tweaks\Grass, Fade 4k-5k.ini"
                Delete "$Path_Ex1\Data\Ini Tweaks\Intro Movies, Disabled.ini"
                Delete "$Path_Ex1\Data\Ini Tweaks\Intro Movies, Normal.ini"
                Delete "$Path_Ex1\Data\Ini Tweaks\Joystick, ~Disabled.ini"
                Delete "$Path_Ex1\Data\Ini Tweaks\Joystick, ~Enabled.ini"
                Delete "$Path_Ex1\Data\Ini Tweaks\Local Map Shader, Disabled.ini"
                Delete "$Path_Ex1\Data\Ini Tweaks\Local Map Shader, ~Enabled.ini"
                Delete "$Path_Ex1\Data\Ini Tweaks\Music, Disabled.ini"
                Delete "$Path_Ex1\Data\Ini Tweaks\Music, Enabled.ini"
                Delete "$Path_Ex1\Data\Ini Tweaks\Refraction Shader, Disabled.ini"
                Delete "$Path_Ex1\Data\Ini Tweaks\Refraction Shader, ~Enabled.ini"
                Delete "$Path_Ex1\Data\Ini Tweaks\Save Backups, 1.ini"
                Delete "$Path_Ex1\Data\Ini Tweaks\Save Backups, 2.ini"
                Delete "$Path_Ex1\Data\Ini Tweaks\Save Backups, 3.ini"
                Delete "$Path_Ex1\Data\Ini Tweaks\Save Backups, 5.ini"
                Delete "$Path_Ex1\Data\Ini Tweaks\Screenshot, ~Disabled.ini"
                Delete "$Path_Ex1\Data\Ini Tweaks\Screenshot, ~ENabled.ini"
                Delete "$Path_Ex1\Data\Ini Tweaks\ShadowMapResolution, 1024.ini"
                Delete "$Path_Ex1\Data\Ini Tweaks\ShadowMapResolution, 256 [default].ini"
                Delete "$Path_Ex1\Data\Ini Tweaks\Sound Card Channels, 8.ini"
                Delete "$Path_Ex1\Data\Ini Tweaks\Sound Card Channels, 16.ini"
                Delete "$Path_Ex1\Data\Ini Tweaks\Sound Card Channels, 24.ini"
                Delete "$Path_Ex1\Data\Ini Tweaks\Sound Card Channels, 48.ini"
                Delete "$Path_Ex1\Data\Ini Tweaks\Sound Card Channels, 64.ini"
                Delete "$Path_Ex1\Data\Ini Tweaks\Sound Card Channels, 96.ini"
                Delete "$Path_Ex1\Data\Ini Tweaks\Sound Card Channels, 128.ini"
                Delete "$Path_Ex1\Data\Ini Tweaks\Sound Card Channels, 192.ini"
                Delete "$Path_Ex1\Data\Ini Tweaks\Sound Card Channels, ~ [Oblivion].ini"
                Delete "$Path_Ex1\Data\Ini Tweaks\Sound Card Channels,  [Oblivion].ini"
                Delete "$Path_Ex1\Data\Ini Tweaks\Sound, Disabled.ini"
                Delete "$Path_Ex1\Data\Ini Tweaks\Sound, Enabled.ini"
                Delete "$Path_Ex1\Data\Bash Patches\Crowded Cities 15_Alternate_Names.csv"
                Delete "$Path_Ex1\Data\Bash Patches\Crowded Cities 15_Names.csv"
                Delete "$Path_Ex1\Data\Bash Patches\Crowded Cities 30_Alternate_Names.csv"
                Delete "$Path_Ex1\Data\Bash Patches\Crowded Cities 30_Names.csv"
                Delete "$Path_Ex1\Data\Bash Patches\Crowded Roads Revamped_Names.csv"
                Delete "$Path_Ex1\Data\Bash Patches\Crowded Roads Revisited_Alternate_Names.csv"
                Delete "$Path_Ex1\Data\Bash Patches\Crowded Roads Revisited_Names.csv"
                Delete "$Path_Ex1\Data\Bash Patches\PTRoamingNPCs_Names.csv"
                Delete "$Path_Ex1\Mopy\Wrye Bash Advanced Readme.html"
                Delete "$Path_Ex1\Mopy\Wrye Bash General Readme.html"
                Delete "$Path_Ex1\Mopy\Wrye Bash Technical Readme.html"
                Delete "$Path_Ex1\Mopy\Wrye Bash Version History.html"
                ;As of 294 the below are obselete locations or files.
                Delete "$Path_Ex1\Mopy\7z.*"
                Delete "$Path_Ex1\Mopy\CBash.dll"
                Delete "$Path_Ex1\Mopy\Data\Italian.*"
                Delete "$Path_Ex1\Mopy\Data\Oblivion_ids.pkl"
                Delete "$Path_Ex1\Mopy\Data\Russian.*"
                Delete "$Path_Ex1\Mopy\Data\de.*"
                Delete "$Path_Ex1\Mopy\Data\pt_opt.*"
                Delete "$Path_Ex1\Mopy\Data\Actor Levels\OOO, 1.23 Mincapped.csv"
                Delete "$Path_Ex1\Mopy\Data\Actor Levels\OOO, 1.23 Uncapped.csv"
                RMDir  "$Path_Ex1\Mopy\Data\Actor Levels"
                RMDir  "$Path_Ex1\Mopy\Data"
                Delete "$Path_Ex1\Mopy\DebugLog(Python2.6).bat"
                Delete "$Path_Ex1\Mopy\Extras\*"
                Delete "$Path_Ex1\Mopy\ScriptParser.p*"
                Delete "$Path_Ex1\Mopy\balt.p*"
                Delete "$Path_Ex1\Mopy\barb.p*"
                Delete "$Path_Ex1\Mopy\barg.p*"
                Delete "$Path_Ex1\Mopy\bash.p*"
                Delete "$Path_Ex1\Mopy\basher.p*"
                Delete "$Path_Ex1\Mopy\bashmon.p*"
                Delete "$Path_Ex1\Mopy\belt.p*"
                Delete "$Path_Ex1\Mopy\bish.p*"
                Delete "$Path_Ex1\Mopy\bolt.p*"
                Delete "$Path_Ex1\Mopy\bosh.p*"
                Delete "$Path_Ex1\Mopy\bush.p*"
                Delete "$Path_Ex1\Mopy\cint.p*"
                Delete "$Path_Ex1\Mopy\gpl.txt"
                Delete "$Path_Ex1\Mopy\images\*"
                RMDir  "$Path_Ex1\Mopy\images"
                Delete "$Path_Ex1\Mopy\lzma.exe"
                ;Current files:
                Delete "$Path_Ex1\Mopy\Wrye Bash.txt"
                Delete "$Path_Ex1\Mopy\Wrye Bash.html"
                Delete "$Path_Ex1\Mopy\Wrye Bash.exe"
                Delete "$Path_Ex1\Mopy\Wrye Bash.exe.log"
                Delete "$Path_Ex1\Mopy\Wrye Bash Launcher.p*"
                Delete "$Path_Ex1\Mopy\Wrye Bash Debug.p*"
                Delete "$Path_Ex1\Mopy\wizards.txt"
                Delete "$Path_Ex1\Mopy\wizards.html"
                Delete "$Path_Ex1\Mopy\Wizard Images\*.*"
                Delete "$Path_Ex1\Mopy\w9xpopen.exe"
                Delete "$Path_Ex1\Mopy\templates\skyrim\*.*"
                Delete "$Path_Ex1\Mopy\templates\oblivion\*.*"
                Delete "$Path_Ex1\Mopy\templates\*.*"
                Delete "$Path_Ex1\Mopy\templates\*"
                Delete "$Path_Ex1\Mopy\patch_option_reference.txt"
                Delete "$Path_Ex1\Mopy\patch_option_reference.html"
                Delete "$Path_Ex1\Mopy\license.txt"
                Delete "$Path_Ex1\Mopy\Ini Tweaks\Skyrim\*.*"
                Delete "$Path_Ex1\Mopy\Ini Tweaks\Oblivion\*.*"
                Delete "$Path_Ex1\Mopy\Docs\Wrye Bash Version History.html"
                Delete "$Path_Ex1\Mopy\Docs\Wrye Bash Technical Readme.html"
                Delete "$Path_Ex1\Mopy\Docs\Wrye Bash General Readme.html"
                Delete "$Path_Ex1\Mopy\Docs\Wrye Bash Advanced Readme.html"
                Delete "$Path_Ex1\Mopy\Docs\wtxt_teal.css"
                Delete "$Path_Ex1\Mopy\Docs\wtxt_sand_small.css"
                Delete "$Path_Ex1\Mopy\Docs\Bash Readme Template.txt"
                Delete "$Path_Ex1\Mopy\Docs\Bash Readme Template.html"
                Delete "$Path_Ex1\Mopy\bash\windows.pyo"
                Delete "$Path_Ex1\Mopy\bash\ScriptParsero"
                Delete "$Path_Ex1\Mopy\bash\ScriptParsero.py"
                Delete "$Path_Ex1\Mopy\bash\ScriptParser.p*"
                Delete "$Path_Ex1\Mopy\bash\Rename_CBash.dll"
                Delete "$Path_Ex1\Mopy\bash\l10n\Russian.*"
                Delete "$Path_Ex1\Mopy\bash\l10n\pt_opt.*"
                Delete "$Path_Ex1\Mopy\bash\l10n\Italian.*"
                Delete "$Path_Ex1\Mopy\bash\l10n\de.*"
                Delete "$Path_Ex1\Mopy\bash\l10n\Chinese*.*"
                Delete "$Path_Ex1\Mopy\bash\liblo.pyo"
                Delete "$Path_Ex1\Mopy\bash\libbsa.pyo"
                Delete "$Path_Ex1\Mopy\bash\libbsa.py"
                Delete "$Path_Ex1\Mopy\bash\images\tools\*.*"
                Delete "$Path_Ex1\Mopy\bash\images\readme\*.*"
                Delete "$Path_Ex1\Mopy\bash\images\nsis\*.*"
                Delete "$Path_Ex1\Mopy\bash\images\*"
                Delete "$Path_Ex1\Mopy\bash\gpl.txt"
                Delete "$Path_Ex1\Mopy\bash\game\*"
                Delete "$Path_Ex1\Mopy\bash\db\Skyrim_ids.pkl"
                Delete "$Path_Ex1\Mopy\bash\db\Oblivion_ids.pkl"
                Delete "$Path_Ex1\Mopy\bash\compiled\Microsoft.VC80.CRT\*"
                Delete "$Path_Ex1\Mopy\bash\compiled\*"
                Delete "$Path_Ex1\Mopy\bash\windowso"
                Delete "$Path_Ex1\Mopy\bash\libbsao"
                Delete "$Path_Ex1\Mopy\bash\cinto"
                Delete "$Path_Ex1\Mopy\bash\cint.p*"
                Delete "$Path_Ex1\Mopy\bash\chardet\*"
                Delete "$Path_Ex1\Mopy\bash\bwebo"
                Delete "$Path_Ex1\Mopy\bash\bweb.p*"
                Delete "$Path_Ex1\Mopy\bash\busho"
                Delete "$Path_Ex1\Mopy\bash\bush.p*"
                Delete "$Path_Ex1\Mopy\bash\breco"
                Delete "$Path_Ex1\Mopy\bash\brec.p*"
                Delete "$Path_Ex1\Mopy\bash\bosho"
                Delete "$Path_Ex1\Mopy\bash\bosh.p*"
                Delete "$Path_Ex1\Mopy\bash\Bolto"
                Delete "$Path_Ex1\Mopy\bash\bolt.p*"
                Delete "$Path_Ex1\Mopy\bash\bish.p*"
                Delete "$Path_Ex1\Mopy\bash\belto"
                Delete "$Path_Ex1\Mopy\bash\belt.p*"
                Delete "$Path_Ex1\Mopy\bash\basso"
                Delete "$Path_Ex1\Mopy\bash\bass.p*"
                Delete "$Path_Ex1\Mopy\bash\basho"
                Delete "$Path_Ex1\Mopy\bash\bashmon.p*"
                Delete "$Path_Ex1\Mopy\bash\bashero"
                Delete "$Path_Ex1\Mopy\bash\basher.p*"
                Delete "$Path_Ex1\Mopy\bash\bash.p*"
                Delete "$Path_Ex1\Mopy\bash\bargo"
                Delete "$Path_Ex1\Mopy\bash\barg.p*"
                Delete "$Path_Ex1\Mopy\bash\barbo"
                Delete "$Path_Ex1\Mopy\bash\barb.p*"
                Delete "$Path_Ex1\Mopy\bash\bapio"
                Delete "$Path_Ex1\Mopy\bash\bapi.p*"
                Delete "$Path_Ex1\Mopy\bash\balto"
                Delete "$Path_Ex1\Mopy\bash\balt.p*"
                Delete "$Path_Ex1\Mopy\bash\*.pyc"
                Delete "$Path_Ex1\Mopy\bash\*.py"
                Delete "$Path_Ex1\Mopy\bash\*.bat"
                Delete "$Path_Ex1\Mopy\bash\__init__.p*"
                Delete "$Path_Ex1\Mopy\bash.ini"
                Delete "$Path_Ex1\Mopy\bash_default.ini"
                Delete "$Path_Ex1\Mopy\bash_default_Russian.ini"
                Delete "$Path_Ex1\Mopy\Bash Patches\Skyrim\*.*"
                Delete "$Path_Ex1\Mopy\Bash Patches\Oblivion\*.*"
                Delete "$Path_Ex1\Mopy\*.log"
                Delete "$Path_Ex1\Mopy\*.bat"
                Delete "$Path_Ex1\Mopy\bash.ico"
                Delete "$Path_Ex1\Data\Docs\Bashed patch*.*"
                Delete "$Path_Ex1\Data\ArchiveInvalidationInvalidated!.bsa"
                RMDir  "$Path_Ex1\Mopy\Wizard Images"
                RMDir  "$Path_Ex1\Mopy\templates\skyrim"
                RMDir  "$Path_Ex1\Mopy\templates\oblivion"
                RMDir  "$Path_Ex1\Mopy\templates"
                RMDir  "$Path_Ex1\Mopy\Ini Tweaks\Skyrim"
                RMDir  "$Path_Ex1\Mopy\Ini Tweaks\Oblivion"
                RMDir  "$Path_Ex1\Mopy\Ini Tweaks"
                RMDir  "$Path_Ex1\Mopy\Docs"
                RMDir  "$Path_Ex1\Mopy\bash\l10n"
                RMDir  "$Path_Ex1\Mopy\bash\images\tools"
                RMDir  "$Path_Ex1\Mopy\bash\images\readme"
                RMDir  "$Path_Ex1\Mopy\bash\images\nsis"
                RMDir  "$Path_Ex1\Mopy\bash\images"
                RMDir  "$Path_Ex1\Mopy\bash\game"
                RMDir  "$Path_Ex1\Mopy\bash\db"
                RMDir  "$Path_Ex1\Mopy\bash\compiled\Microsoft.VC80.CRT"
                RMDir  "$Path_Ex1\Mopy\bash\compiled"
                RMDir  "$Path_Ex1\Mopy\bash\chardet"
                RMDir  "$Path_Ex1\Mopy\bash"
                RMDir  "$Path_Ex1\Mopy\Bash Patches\Skyrim"
                RMDir  "$Path_Ex1\Mopy\Bash Patches\Oblivion"
                RMDir  "$Path_Ex1\Mopy\Bash Patches"
                RMDir  "$Path_Ex1\Mopy\Apps"
                RMDir  "$Path_Ex1\Mopy"
                RMDir  "$Path_Ex1\Data\Ini Tweaks"
                RMDir  "$Path_Ex1\Data\Docs"
                RMDir  "$Path_Ex1\Data\Bash Patches"
                Delete "$SMPROGRAMS\Wrye Bash\*Extra 1*"
            ${EndIf}
        ${EndIf}
        ${If} $CheckState_Ex2 == ${BST_CHECKED}
            ${If} $Path_Ex2 != $Empty
                DeleteRegValue HKLM "SOFTWARE\Wrye Bash" "Extra Path 2"
                DeleteRegValue HKLM "SOFTWARE\Wrye Bash" "Extra Path 2 Python Version"
                DeleteRegValue HKLM "SOFTWARE\Wrye Bash" "Extra Path 2 Standalone Version"
                ;First delete OLD version files:
                Delete "$Path_Ex2\Data\Docs\Bashed Lists.txt"
                Delete "$Path_Ex2\Data\Docs\Bashed Lists.html"
                Delete "$Path_Ex2\Mopy\uninstall.exe"
                Delete "$Path_Ex2\Data\Ini Tweaks\Autosave, Never.ini"
                Delete "$Path_Ex2\Data\Ini Tweaks\Autosave, ~Always.ini"
                Delete "$Path_Ex2\Data\Ini Tweaks\Border Regions, Disabled.ini"
                Delete "$Path_Ex2\Data\Ini Tweaks\Border Regions, ~Enabled.ini"
                Delete "$Path_Ex2\Data\Ini Tweaks\Fonts 1, ~Default.ini"
                Delete "$Path_Ex2\Data\Ini Tweaks\Fonts, ~Default.ini"
                Delete "$Path_Ex2\Data\Ini Tweaks\Grass, Fade 4k-5k.ini"
                Delete "$Path_Ex2\Data\Ini Tweaks\Intro Movies, Disabled.ini"
                Delete "$Path_Ex2\Data\Ini Tweaks\Intro Movies, Normal.ini"
                Delete "$Path_Ex2\Data\Ini Tweaks\Joystick, ~Disabled.ini"
                Delete "$Path_Ex2\Data\Ini Tweaks\Joystick, ~Enabled.ini"
                Delete "$Path_Ex2\Data\Ini Tweaks\Local Map Shader, Disabled.ini"
                Delete "$Path_Ex2\Data\Ini Tweaks\Local Map Shader, ~Enabled.ini"
                Delete "$Path_Ex2\Data\Ini Tweaks\Music, Disabled.ini"
                Delete "$Path_Ex2\Data\Ini Tweaks\Music, Enabled.ini"
                Delete "$Path_Ex2\Data\Ini Tweaks\Refraction Shader, Disabled.ini"
                Delete "$Path_Ex2\Data\Ini Tweaks\Refraction Shader, ~Enabled.ini"
                Delete "$Path_Ex2\Data\Ini Tweaks\Save Backups, 1.ini"
                Delete "$Path_Ex2\Data\Ini Tweaks\Save Backups, 2.ini"
                Delete "$Path_Ex2\Data\Ini Tweaks\Save Backups, 3.ini"
                Delete "$Path_Ex2\Data\Ini Tweaks\Save Backups, 5.ini"
                Delete "$Path_Ex2\Data\Ini Tweaks\Screenshot, ~Disabled.ini"
                Delete "$Path_Ex2\Data\Ini Tweaks\Screenshot, ~ENabled.ini"
                Delete "$Path_Ex2\Data\Ini Tweaks\ShadowMapResolution, 1024.ini"
                Delete "$Path_Ex2\Data\Ini Tweaks\ShadowMapResolution, 256 [default].ini"
                Delete "$Path_Ex2\Data\Ini Tweaks\Sound Card Channels, 8.ini"
                Delete "$Path_Ex2\Data\Ini Tweaks\Sound Card Channels, 16.ini"
                Delete "$Path_Ex2\Data\Ini Tweaks\Sound Card Channels, 24.ini"
                Delete "$Path_Ex2\Data\Ini Tweaks\Sound Card Channels, 48.ini"
                Delete "$Path_Ex2\Data\Ini Tweaks\Sound Card Channels, 64.ini"
                Delete "$Path_Ex2\Data\Ini Tweaks\Sound Card Channels, 96.ini"
                Delete "$Path_Ex2\Data\Ini Tweaks\Sound Card Channels, 128.ini"
                Delete "$Path_Ex2\Data\Ini Tweaks\Sound Card Channels, 192.ini"
                Delete "$Path_Ex2\Data\Ini Tweaks\Sound Card Channels, ~ [Oblivion].ini"
                Delete "$Path_Ex2\Data\Ini Tweaks\Sound Card Channels,  [Oblivion].ini"
                Delete "$Path_Ex2\Data\Ini Tweaks\Sound, Disabled.ini"
                Delete "$Path_Ex2\Data\Ini Tweaks\Sound, Enabled.ini"
                Delete "$Path_Ex2\Data\Bash Patches\Crowded Cities 15_Alternate_Names.csv"
                Delete "$Path_Ex2\Data\Bash Patches\Crowded Cities 15_Names.csv"
                Delete "$Path_Ex2\Data\Bash Patches\Crowded Cities 30_Alternate_Names.csv"
                Delete "$Path_Ex2\Data\Bash Patches\Crowded Cities 30_Names.csv"
                Delete "$Path_Ex2\Data\Bash Patches\Crowded Roads Revamped_Names.csv"
                Delete "$Path_Ex2\Data\Bash Patches\Crowded Roads Revisited_Alternate_Names.csv"
                Delete "$Path_Ex2\Data\Bash Patches\Crowded Roads Revisited_Names.csv"
                Delete "$Path_Ex2\Data\Bash Patches\PTRoamingNPCs_Names.csv"
                Delete "$Path_Ex2\Mopy\Wrye Bash Advanced Readme.html"
                Delete "$Path_Ex2\Mopy\Wrye Bash General Readme.html"
                Delete "$Path_Ex2\Mopy\Wrye Bash Technical Readme.html"
                Delete "$Path_Ex2\Mopy\Wrye Bash Version History.html"
                ;As of 294 the below are obselete locations or files.
                Delete "$Path_Ex2\Mopy\7z.*"
                Delete "$Path_Ex2\Mopy\CBash.dll"
                Delete "$Path_Ex2\Mopy\Data\Italian.*"
                Delete "$Path_Ex2\Mopy\Data\Oblivion_ids.pkl"
                Delete "$Path_Ex2\Mopy\Data\Russian.*"
                Delete "$Path_Ex2\Mopy\Data\de.*"
                Delete "$Path_Ex2\Mopy\Data\pt_opt.*"
                Delete "$Path_Ex2\Mopy\Data\Actor Levels\OOO, 1.23 Mincapped.csv"
                Delete "$Path_Ex2\Mopy\Data\Actor Levels\OOO, 1.23 Uncapped.csv"
                RMDir  "$Path_Ex2\Mopy\Data\Actor Levels"
                RMDir  "$Path_Ex2\Mopy\Data"
                Delete "$Path_Ex2\Mopy\DebugLog(Python2.6).bat"
                Delete "$Path_Ex2\Mopy\Extras\*"
                Delete "$Path_Ex2\Mopy\ScriptParser.p*"
                Delete "$Path_Ex2\Mopy\balt.p*"
                Delete "$Path_Ex2\Mopy\barb.p*"
                Delete "$Path_Ex2\Mopy\barg.p*"
                Delete "$Path_Ex2\Mopy\bash.p*"
                Delete "$Path_Ex2\Mopy\basher.p*"
                Delete "$Path_Ex2\Mopy\bashmon.p*"
                Delete "$Path_Ex2\Mopy\belt.p*"
                Delete "$Path_Ex2\Mopy\bish.p*"
                Delete "$Path_Ex2\Mopy\bolt.p*"
                Delete "$Path_Ex2\Mopy\bosh.p*"
                Delete "$Path_Ex2\Mopy\bush.p*"
                Delete "$Path_Ex2\Mopy\cint.p*"
                Delete "$Path_Ex2\Mopy\gpl.txt"
                Delete "$Path_Ex2\Mopy\images\*"
                RMDir  "$Path_Ex2\Mopy\images"
                Delete "$Path_Ex2\Mopy\lzma.exe"
                ;Current files:
                Delete "$Path_Ex2\Mopy\Wrye Bash.txt"
                Delete "$Path_Ex2\Mopy\Wrye Bash.html"
                Delete "$Path_Ex2\Mopy\Wrye Bash.exe"
                Delete "$Path_Ex2\Mopy\Wrye Bash.exe.log"
                Delete "$Path_Ex2\Mopy\Wrye Bash Launcher.p*"
                Delete "$Path_Ex2\Mopy\Wrye Bash Debug.p*"
                Delete "$Path_Ex2\Mopy\wizards.txt"
                Delete "$Path_Ex2\Mopy\wizards.html"
                Delete "$Path_Ex2\Mopy\Wizard Images\*.*"
                Delete "$Path_Ex2\Mopy\w9xpopen.exe"
                Delete "$Path_Ex2\Mopy\templates\skyrim\*.*"
                Delete "$Path_Ex2\Mopy\templates\oblivion\*.*"
                Delete "$Path_Ex2\Mopy\templates\*.*"
                Delete "$Path_Ex2\Mopy\templates\*"
                Delete "$Path_Ex2\Mopy\patch_option_reference.txt"
                Delete "$Path_Ex2\Mopy\patch_option_reference.html"
                Delete "$Path_Ex2\Mopy\license.txt"
                Delete "$Path_Ex2\Mopy\Ini Tweaks\Skyrim\*.*"
                Delete "$Path_Ex2\Mopy\Ini Tweaks\Oblivion\*.*"
                Delete "$Path_Ex2\Mopy\Docs\Wrye Bash Version History.html"
                Delete "$Path_Ex2\Mopy\Docs\Wrye Bash Technical Readme.html"
                Delete "$Path_Ex2\Mopy\Docs\Wrye Bash General Readme.html"
                Delete "$Path_Ex2\Mopy\Docs\Wrye Bash Advanced Readme.html"
                Delete "$Path_Ex2\Mopy\Docs\wtxt_teal.css"
                Delete "$Path_Ex2\Mopy\Docs\wtxt_sand_small.css"
                Delete "$Path_Ex2\Mopy\Docs\Bash Readme Template.txt"
                Delete "$Path_Ex2\Mopy\Docs\Bash Readme Template.html"
                Delete "$Path_Ex2\Mopy\bash\windows.pyo"
                Delete "$Path_Ex2\Mopy\bash\ScriptParsero"
                Delete "$Path_Ex2\Mopy\bash\ScriptParsero.py"
                Delete "$Path_Ex2\Mopy\bash\ScriptParser.p*"
                Delete "$Path_Ex2\Mopy\bash\Rename_CBash.dll"
                Delete "$Path_Ex2\Mopy\bash\l10n\Russian.*"
                Delete "$Path_Ex2\Mopy\bash\l10n\pt_opt.*"
                Delete "$Path_Ex2\Mopy\bash\l10n\Italian.*"
                Delete "$Path_Ex2\Mopy\bash\l10n\de.*"
                Delete "$Path_Ex2\Mopy\bash\l10n\Chinese*.*"
                Delete "$Path_Ex2\Mopy\bash\liblo.pyo"
                Delete "$Path_Ex2\Mopy\bash\libbsa.pyo"
                Delete "$Path_Ex2\Mopy\bash\libbsa.py"
                Delete "$Path_Ex2\Mopy\bash\images\tools\*.*"
                Delete "$Path_Ex2\Mopy\bash\images\readme\*.*"
                Delete "$Path_Ex2\Mopy\bash\images\nsis\*.*"
                Delete "$Path_Ex2\Mopy\bash\images\*"
                Delete "$Path_Ex2\Mopy\bash\gpl.txt"
                Delete "$Path_Ex2\Mopy\bash\game\*"
                Delete "$Path_Ex2\Mopy\bash\db\Skyrim_ids.pkl"
                Delete "$Path_Ex2\Mopy\bash\db\Oblivion_ids.pkl"
                Delete "$Path_Ex2\Mopy\bash\compiled\Microsoft.VC80.CRT\*"
                Delete "$Path_Ex2\Mopy\bash\compiled\*"
                Delete "$Path_Ex2\Mopy\bash\windowso"
                Delete "$Path_Ex2\Mopy\bash\libbsao"
                Delete "$Path_Ex2\Mopy\bash\cinto"
                Delete "$Path_Ex2\Mopy\bash\cint.p*"
                Delete "$Path_Ex2\Mopy\bash\chardet\*"
                Delete "$Path_Ex2\Mopy\bash\bwebo"
                Delete "$Path_Ex2\Mopy\bash\bweb.p*"
                Delete "$Path_Ex2\Mopy\bash\busho"
                Delete "$Path_Ex2\Mopy\bash\bush.p*"
                Delete "$Path_Ex2\Mopy\bash\breco"
                Delete "$Path_Ex2\Mopy\bash\brec.p*"
                Delete "$Path_Ex2\Mopy\bash\bosho"
                Delete "$Path_Ex2\Mopy\bash\bosh.p*"
                Delete "$Path_Ex2\Mopy\bash\Bolto"
                Delete "$Path_Ex2\Mopy\bash\bolt.p*"
                Delete "$Path_Ex2\Mopy\bash\bish.p*"
                Delete "$Path_Ex2\Mopy\bash\belto"
                Delete "$Path_Ex2\Mopy\bash\belt.p*"
                Delete "$Path_Ex2\Mopy\bash\basso"
                Delete "$Path_Ex2\Mopy\bash\bass.p*"
                Delete "$Path_Ex2\Mopy\bash\basho"
                Delete "$Path_Ex2\Mopy\bash\bashmon.p*"
                Delete "$Path_Ex2\Mopy\bash\bashero"
                Delete "$Path_Ex2\Mopy\bash\basher.p*"
                Delete "$Path_Ex2\Mopy\bash\bash.p*"
                Delete "$Path_Ex2\Mopy\bash\bargo"
                Delete "$Path_Ex2\Mopy\bash\barg.p*"
                Delete "$Path_Ex2\Mopy\bash\barbo"
                Delete "$Path_Ex2\Mopy\bash\barb.p*"
                Delete "$Path_Ex2\Mopy\bash\bapio"
                Delete "$Path_Ex2\Mopy\bash\bapi.p*"
                Delete "$Path_Ex2\Mopy\bash\balto"
                Delete "$Path_Ex2\Mopy\bash\balt.p*"
                Delete "$Path_Ex2\Mopy\bash\*.pyc"
                Delete "$Path_Ex2\Mopy\bash\*.py"
                Delete "$Path_Ex2\Mopy\bash\*.bat"
                Delete "$Path_Ex2\Mopy\bash\__init__.p*"
                Delete "$Path_Ex2\Mopy\bash.ini"
                Delete "$Path_Ex2\Mopy\bash_default.ini"
                Delete "$Path_Ex2\Mopy\bash_default_Russian.ini"
                Delete "$Path_Ex2\Mopy\Bash Patches\Skyrim\*.*"
                Delete "$Path_Ex2\Mopy\Bash Patches\Oblivion\*.*"
                Delete "$Path_Ex2\Mopy\*.log"
                Delete "$Path_Ex2\Mopy\*.bat"
                Delete "$Path_Ex2\Mopy\bash.ico"
                Delete "$Path_Ex2\Data\Docs\Bashed patch*.*"
                Delete "$Path_Ex2\Data\ArchiveInvalidationInvalidated!.bsa"
                RMDir  "$Path_Ex2\Mopy\Wizard Images"
                RMDir  "$Path_Ex2\Mopy\templates\skyrim"
                RMDir  "$Path_Ex2\Mopy\templates\oblivion"
                RMDir  "$Path_Ex2\Mopy\templates"
                RMDir  "$Path_Ex2\Mopy\Ini Tweaks\Skyrim"
                RMDir  "$Path_Ex2\Mopy\Ini Tweaks\Oblivion"
                RMDir  "$Path_Ex2\Mopy\Ini Tweaks"
                RMDir  "$Path_Ex2\Mopy\Docs"
                RMDir  "$Path_Ex2\Mopy\bash\l10n"
                RMDir  "$Path_Ex2\Mopy\bash\images\tools"
                RMDir  "$Path_Ex2\Mopy\bash\images\readme"
                RMDir  "$Path_Ex2\Mopy\bash\images\nsis"
                RMDir  "$Path_Ex2\Mopy\bash\images"
                RMDir  "$Path_Ex2\Mopy\bash\game"
                RMDir  "$Path_Ex2\Mopy\bash\db"
                RMDir  "$Path_Ex2\Mopy\bash\compiled\Microsoft.VC80.CRT"
                RMDir  "$Path_Ex2\Mopy\bash\compiled"
                RMDir  "$Path_Ex2\Mopy\bash\chardet"
                RMDir  "$Path_Ex2\Mopy\bash"
                RMDir  "$Path_Ex2\Mopy\Bash Patches\Skyrim"
                RMDir  "$Path_Ex2\Mopy\Bash Patches\Oblivion"
                RMDir  "$Path_Ex2\Mopy\Bash Patches"
                RMDir  "$Path_Ex2\Mopy\Apps"
                RMDir  "$Path_Ex2\Mopy"
                RMDir  "$Path_Ex2\Data\Ini Tweaks"
                RMDir  "$Path_Ex2\Data\Docs"
                RMDir  "$Path_Ex2\Data\Bash Patches"
                Delete "$SMPROGRAMS\Wrye Bash\*Extra 2*"
            ${EndIf}
        ${EndIf}


        ;If it is a complete uninstall remove the shared data:
        ReadRegStr $Path_OB HKLM "Software\Wrye Bash" "Oblivion Path"
        ReadRegStr $Path_Nehrim HKLM "Software\Wrye Bash" "Nehrim Path"
        ReadRegStr $Path_Skyrim HKLM "Software\Wrye Bash" "Skyrim Path"
        ReadRegStr $Path_Ex1 HKLM "Software\Wrye Bash" "Extra Path 1"
        ReadRegStr $Path_Ex2 HKLM "Software\Wrye Bash" "Extra Path 2"
        ${If} $Path_OB == $Empty
            ${AndIf} $Path_Nehrim == $Empty
            ${AndIf} $Path_Skyrim == $Empty
            ${AndIf} $Path_Ex1 == $Empty
            ${AndIf} $Path_Ex2 == $Empty
                DeleteRegKey HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\Wrye Bash"
                ReadRegStr $0 HKLM "Software\Wrye Bash" "Installer Path"
                DeleteRegKey HKLM "SOFTWARE\Wrye Bash"
                ;Delete stupid Windows created registry keys:
                DeleteRegKey HKCU "Software\Microsoft\Windows\CurrentVersion\App Management\ARPCache\Wrye Bash"
                DeleteRegValue HKCR "Local Settings\Software\Microsoft\Windows\Shell\MuiCache" "$COMMONFILES\Wrye Bash\Uninstall.exe"
                DeleteRegValue HKCU "Software\Classes\Local Settings\Software\Microsoft\Windows\Shell\MuiCache" "$COMMONFILES\Wrye Bash\Uninstall.exe"
                DeleteRegValue HKCU "Software\Microsoft\Windows\ShellNoRoam\MuiCache" "$COMMONFILES\Wrye Bash\Uninstall.exe"
                DeleteRegValue HKCR "Local Settings\Software\Microsoft\Windows\Shell\MuiCache" "$0"
                DeleteRegValue HKCU "Software\Classes\Local Settings\Software\Microsoft\Windows\Shell\MuiCache" "$0"
                DeleteRegValue HKCU "Software\Microsoft\Windows\ShellNoRoam\MuiCache" "$0"
                Delete "$SMPROGRAMS\Wrye Bash\*.*"
                RMDir "$SMPROGRAMS\Wrye Bash"
                Delete "$COMMONFILES\Wrye Bash\*.*"
                RMDir "$COMMONFILES\Wrye Bash"
            ${EndIf}
        SectionEnd

;-------------------------------- Descriptions/Subtitles/Language Strings:
  ;Language strings
  !insertmacro MUI_LANGUAGE "English"
  LangString DESC_Main ${LANG_ENGLISH} "The main Wrye Bash files."
  LangString DESC_Shortcuts_SM ${LANG_ENGLISH} "Start Menu shortcuts for the uninstaller and each launcher."
  LangString DESC_Prereq ${LANG_ENGLISH} "The files that Wrye Bash requires to run."
  LangString PAGE_INSTALLLOCATIONS_TITLE ${LANG_ENGLISH} "Installation Location(s)"
  LangString PAGE_INSTALLLOCATIONS_SUBTITLE ${LANG_ENGLISH} "Please select main installation path for Wrye Bash and, if desired, extra locations in which to install Wrye Bash."
  LangString PAGE_CHECK_LOCATIONS_TITLE ${LANG_ENGLISH} "Installation Location Check"
  LangString PAGE_CHECK_LOCATIONS_SUBTITLE ${LANG_ENGLISH} "A risky installation location has been detected."
  LangString PAGE_REQUIREMENTS_TITLE ${LANG_ENGLISH} "Installation Prerequisites"
  LangString PAGE_REQUIREMENTS_SUBTITLE ${LANG_ENGLISH} "Checking for requirements"
  LangString unPAGE_SELECT_GAMES_SUBTITLE ${LANG_ENGLISH} "Please select which locations you want to uninstall Wrye Bash from."
  LangString PAGE_FINISH_TITLE ${LANG_ENGLISH} "Finished installing ${WB_NAME}"
  LangString PAGE_FINISH_SUBTITLE ${LANG_ENGLISH} "Please select post-install tasks."

  ;Assign language strings to sections
  !insertmacro MUI_FUNCTION_DESCRIPTION_BEGIN
        !insertmacro MUI_DESCRIPTION_TEXT ${Main} $(DESC_Main)
        !insertmacro MUI_DESCRIPTION_TEXT ${Shortcuts_SM} $(DESC_Shortcuts_SM)
        !insertmacro MUI_DESCRIPTION_TEXT ${Prereq} $(DESC_Prereq)
  !insertmacro MUI_FUNCTION_DESCRIPTION_END
