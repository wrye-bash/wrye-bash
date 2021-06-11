; Wrye Bash.nsi
Unicode true
ManifestDPIAware true

;-------------------------------- Includes:
    !addincludedir "${__FILEDIR__}"
    !include "MUI2.nsh"
    !include "x64.nsh"
    !include "LogicLib.nsh"
    !include "WinVer.nsh"
    !include "nsDialogs.nsh"
    !include "WordFunc.nsh"
    !include "StrFunc.nsh"
    !include "macros.nsh"
    ; declare used functions
    ${StrLoc}

    ; Variables are defined by the packaging script; just define failsafe values
    !ifndef WB_NAME
        !define WB_NAME "Wrye Bash (version unknown)"
    !endif
    !ifndef WB_OUTPUT
        !define WB_OUTPUT "dist"
    !endif
    !ifndef WB_FILEVERSION
        !define WB_FILEVERSION "0.0.0.0"
    !endif


;-------------------------------- Basic Installer Info:
    Name "${WB_NAME}"
    OutFile "${WB_OUTPUT}\${WB_NAME} - Installer.exe"
    ; Request application privileges for Windows Vista
    RequestExecutionLevel admin
    VIProductVersion ${WB_FILEVERSION}
    VIAddVersionKey /LANG=1033 "ProductName" "Wrye Bash"
    VIAddVersionKey /LANG=1033 "CompanyName" "Wrye Bash development team"
    VIAddVersionKey /LANG=1033 "LegalCopyright" "© Wrye"
    VIAddVersionKey /LANG=1033 "FileDescription" "Installer for ${WB_NAME}"
    VIAddVersionKey /LANG=1033 "FileVersion" "${WB_FILEVERSION}"
    SetCompressor /SOLID lzma


;-------------------------------- Variables:
    Var Dialog
    Var Label
    Var Empty
    Var True
    Var Path_OB
    Var Path_Nehrim
    Var Path_Skyrim
    Var Path_Fallout4
    Var Path_SkyrimSE
    Var Path_Fallout3
    Var Path_FalloutNV
    Var Path_Enderal
    Var Path_EnderalSE
    Var Path_Ex1
    Var Path_Ex2

    ;Game specific Data:
    Var Check_OB
    Var Check_Nehrim
    Var Check_Skyrim
    Var Check_Fallout4
    Var Check_SkyrimSE
    Var Check_Extra
    Var Check_Fallout3
    Var Check_FalloutNV
    Var Check_Enderal
    Var Check_EnderalSE
    Var Check_Ex1
    Var Check_Ex2
    Var CheckState_OB
    Var CheckState_Nehrim
    Var CheckState_Skyrim
    Var CheckState_Fallout4
    Var CheckState_SkyrimSE
    Var CheckState_Extra
    Var CheckState_Fallout3
    Var CheckState_FalloutNV
    Var CheckState_Enderal
    Var CheckState_EnderalSE
    Var CheckState_Ex1
    Var CheckState_Ex2
    Var PathDialogue_OB
    Var PathDialogue_Nehrim
    Var PathDialogue_Skyrim
    Var PathDialogue_Fallout4
    Var PathDialogue_SkyrimSE
    Var PathDialogue_Fallout3
    Var PathDialogue_FalloutNV
    Var PathDialogue_Enderal
    Var PathDialogue_EnderalSE
    Var PathDialogue_Ex1
    Var PathDialogue_Ex2
    Var Browse_OB
    Var Browse_Nehrim
    Var Browse_Skyrim
    Var Browse_Fallout4
    Var Browse_SkyrimSE
    Var Browse_Fallout3
    Var Browse_FalloutNV
    Var Browse_Enderal
    Var Browse_EnderalSE
    Var Browse_Ex1
    Var Browse_Ex2
    Var Check_Readme
    Var Check_DeleteOldFiles
    Var Function_Browse
    Var Function_Extra
    Var Function_DirPrompt
    Var unFunction_Browse


;-------------------------------- Page List:
    !define MUI_HEADERIMAGE
    !define MUI_HEADERIMAGE_BITMAP "${WB_CLEAN_MOPY}\bash\images\nsis\wrye_monkey_150x57.bmp"
    !define MUI_HEADERIMAGE_RIGHT
    !define MUI_WELCOMEFINISHPAGE_BITMAP "${WB_CLEAN_MOPY}\bash\images\nsis\wrye_monkey_164x314.bmp"
    !define MUI_UNWELCOMEFINISHPAGE_BITMAP "${WB_CLEAN_MOPY}\bash\images\nsis\wrye_monkey_164x314.bmp"
    !insertmacro MUI_PAGE_WELCOME
    Page custom PAGE_INSTALLLOCATIONS_ES PAGE_INSTALLLOCATIONS_ES_Leave
    Page custom PAGE_INSTALLLOCATIONS_FALLOUT PAGE_INSTALLLOCATIONS_FALLOUT_Leave
    Page custom PAGE_INSTALLLOCATIONS_EXTRA PAGE_INSTALLLOCATIONS_EXTRA_Leave
    Page custom PAGE_CHECK_LOCATIONS PAGE_CHECK_LOCATIONS_Leave
    !insertmacro MUI_PAGE_COMPONENTS
    !insertmacro MUI_PAGE_INSTFILES
    Page custom PAGE_FINISH PAGE_FINISH_Leave

    !insertmacro MUI_UNPAGE_WELCOME
    UninstPage custom un.PAGE_SELECT_GAMES_ES un.PAGE_SELECT_GAMES_ES_Leave
    UninstPage custom un.PAGE_SELECT_GAMES_FALLOUT un.PAGE_SELECT_GAMES_FALLOUT_Leave
    UninstPage custom un.PAGE_SELECT_GAMES_EXTRA un.PAGE_SELECT_GAMES_EXTRA_Leave
    !insertmacro MUI_UNPAGE_INSTFILES


;-------------------------------- Initialize Variables as required:
    Function un.onInit
        StrCpy $Empty ""
        StrCpy $True "True"

        !insertmacro InitializeRegistryPaths
    FunctionEnd

    Function .onInit
        StrCpy $Empty ""
        StrCpy $True "True"

        !insertmacro InitializeRegistryPaths

        ${If} $Path_OB == $Empty
            ReadRegStr $Path_OB HKLM "SOFTWARE\Bethesda Softworks\Oblivion" "Installed Path"
            ${If} $Path_OB == $Empty
                ReadRegStr $Path_OB HKLM "SOFTWARE\WOW6432Node\Bethesda Softworks\Oblivion" "Installed Path"
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
            ReadRegStr $Path_Skyrim HKLM "SOFTWARE\Bethesda Softworks\Skyrim" "Installed Path"
            ${If} $Path_Skyrim == $Empty
                ReadRegStr $Path_Skyrim HKLM "SOFTWARE\WOW6432Node\Bethesda Softworks\Skyrim" "Installed Path"
            ${EndIf}
        ${EndIf}
        ${If} $Path_Skyrim != $Empty
            StrCpy $CheckState_Skyrim ${BST_CHECKED}
        ${EndIf}

        ${If} $Path_Fallout4 == $Empty
            ReadRegStr $Path_Fallout4 HKLM "SOFTWARE\Bethesda Softworks\Fallout4" "Installed Path"
            ${If} $Path_Fallout4 == $Empty
                ReadRegStr $Path_Fallout4 HKLM "SOFTWARE\WOW6432Node\Bethesda Softworks\Fallout4" "Installed Path"
            ${EndIf}
        ${EndIf}
        ${If} $Path_Fallout4 != $Empty
            StrCpy $CheckState_Fallout4 ${BST_CHECKED}
        ${EndIf}

        ${If} $Path_SkyrimSE == $Empty
            ReadRegStr $Path_SkyrimSE HKLM "SOFTWARE\Bethesda Softworks\Skyrim Special Edition" "Installed Path"
            ${If} $Path_SkyrimSE == $Empty
                ReadRegStr $Path_SkyrimSE HKLM "SOFTWARE\WOW6432Node\Bethesda Softworks\Skyrim Special Edition" "Installed Path"
            ${EndIf}
        ${EndIf}
        ${If} $Path_SkyrimSE != $Empty
            StrCpy $CheckState_SkyrimSE ${BST_CHECKED}
        ${EndIf}

        ${If} $Path_Fallout3 == $Empty
            ReadRegStr $Path_Fallout3 HKLM "SOFTWARE\Bethesda Softworks\Fallout3" "Installed Path"
            ${If} $Path_Fallout3 == $Empty
                ReadRegStr $Path_Fallout3 HKLM "SOFTWARE\WOW6432Node\Bethesda Softworks\Fallout3" "Installed Path"
            ${EndIf}
        ${EndIf}
        ${If} $Path_Fallout3 != $Empty
            StrCpy $CheckState_Fallout3 ${BST_CHECKED}
        ${EndIf}

        ${If} $Path_FalloutNV == $Empty
            ReadRegStr $Path_FalloutNV HKLM "SOFTWARE\Bethesda Softworks\FalloutNV" "Installed Path"
            ${If} $Path_FalloutNV == $Empty
                ReadRegStr $Path_FalloutNV HKLM "SOFTWARE\WOW6432Node\Bethesda Softworks\FalloutNV" "Installed Path"
            ${EndIf}
        ${EndIf}
        ${If} $Path_FalloutNV != $Empty
            StrCpy $CheckState_FalloutNV ${BST_CHECKED}
        ${EndIf}

        ${If} $Path_Enderal == $Empty
            ReadRegStr $Path_Enderal HKCU "Software\SureAI\Enderal" "Install_Path"
            ${If} $Path_Enderal == $Empty
                ReadRegStr $Path_Enderal HKCU "SOFTWARE\WOW6432Node\SureAI\Enderal" "Install_Path"
            ${EndIf}
        ${EndIf}
        ${If} $Path_Enderal != $Empty
            StrCpy $CheckState_Enderal ${BST_CHECKED}
        ${EndIf}

        ${If} $Path_EnderalSE == $Empty
            ; This is in HKCU. There's also one in HKLM that uses
            ; 'SureAI\Enderal SE' for some reason
            ReadRegStr $Path_EnderalSE HKCU "Software\SureAI\EnderalSE" "Install_Path"
            ${If} $Path_EnderalSE == $Empty
                ReadRegStr $Path_EnderalSE HKCU "SOFTWARE\WOW6432Node\SureAI\EnderalSE" "Install_Path"
            ${EndIf}
        ${EndIf}
        ${If} $Path_EnderalSE != $Empty
            StrCpy $CheckState_EnderalSE ${BST_CHECKED}
        ${EndIf}

        ${If} $Path_Ex1 != $Empty
            StrCpy $CheckState_Extra ${BST_CHECKED}
            StrCpy $CheckState_Ex1 ${BST_CHECKED}
        ${EndIf}

        ${If} $Path_Ex2 != $Empty
            StrCpy $CheckState_Extra ${BST_CHECKED}
            StrCpy $CheckState_Ex2 ${BST_CHECKED}
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
        ${ElseIf} $0 == $Browse_Fallout4
            StrCpy $1 $PathDialogue_Fallout4
        ${ElseIf} $0 == $Browse_SkyrimSE
            StrCpy $1 $PathDialogue_SkyrimSE
        ${ElseIf} $0 == $Browse_Fallout3
            StrCpy $1 $PathDialogue_Fallout3
        ${ElseIf} $0 == $Browse_FalloutNV
            StrCpy $1 $PathDialogue_FalloutNV
        ${ElseIf} $0 == $Browse_Enderal
            StrCpy $1 $PathDialogue_Enderal
        ${ElseIf} $0 == $Browse_EnderalSE
            StrCpy $1 $PathDialogue_EnderalSE
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
            ShowWindow $PathDialogue_Ex1 ${SW_HIDE}
            ShowWindow $Browse_Ex1 ${SW_HIDE}
            ShowWindow $Check_Ex2 ${SW_HIDE}
            ShowWindow $PathDialogue_Ex2 ${SW_HIDE}
            ShowWindow $Browse_Ex2 ${SW_HIDE}
        ${Else}
            ShowWindow $Check_Ex1 ${SW_SHOW}
            ShowWindow $PathDialogue_Ex1 ${SW_SHOW}
            ShowWindow $Browse_Ex1 ${SW_SHOW}
            ShowWindow $Check_Ex2 ${SW_SHOW}
            ShowWindow $PathDialogue_Ex2 ${SW_SHOW}
            ShowWindow $Browse_Ex2 ${SW_SHOW}
        ${EndIf}
    FunctionEnd

    Function un.OnClick_Browse
        Pop $0
        ${If} $0 == $Browse_OB
            StrCpy $1 $PathDialogue_OB
        ${ElseIf} $0 == $Browse_Nehrim
            StrCpy $1 $PathDialogue_Nehrim
        ${ElseIf} $0 == $Browse_Skyrim
            StrCpy $1 $PathDialogue_Skyrim
        ${ElseIf} $0 == $Browse_Fallout4
            StrCpy $1 $PathDialogue_Fallout4
        ${ElseIf} $0 == $Browse_SkyrimSE
            StrCpy $1 $PathDialogue_SkyrimSE
        ${ElseIf} $0 == $Browse_Fallout3
            StrCpy $1 $PathDialogue_Fallout3
        ${ElseIf} $0 == $Browse_FalloutNV
            StrCpy $1 $PathDialogue_FalloutNV
        ${ElseIf} $0 == $Browse_Enderal
            StrCpy $1 $PathDialogue_Enderal
        ${ElseIf} $0 == $Browse_EnderalSE
            StrCpy $1 $PathDialogue_EnderalSE
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

;-------------------------------- Include Local Script Files

    !include "pages.nsi"
    !include "install.nsi"
    !include "uninstall.nsi"

;-------------------------------- Descriptions/Subtitles/Language Strings:
  ;Language strings
  !insertmacro MUI_LANGUAGE "English"
  LangString DESC_Main ${LANG_ENGLISH} "The main Wrye Bash files."
  LangString DESC_Shortcuts_SM ${LANG_ENGLISH} "Start Menu shortcuts for the uninstaller and each launcher."

  LangString PAGE_INSTALLLOCATIONS_ES_TITLE ${LANG_ENGLISH} "Elder Scrolls Installation Location(s)"
  LangString PAGE_INSTALLLOCATIONS_ES_SUBTITLE ${LANG_ENGLISH} "Please select installation path(s) for Wrye Bash."

  LangString PAGE_INSTALLLOCATIONS_FALLOUT_TITLE ${LANG_ENGLISH} "Fallout Installation Location(s)"
  LangString PAGE_INSTALLLOCATIONS_FALLOUT_SUBTITLE ${LANG_ENGLISH} "Please select installation path(s) for Wrye Flash."

  LangString PAGE_INSTALLLOCATIONS_EXTRA_TITLE ${LANG_ENGLISH} "Extra Installation Location(s)"
  LangString PAGE_INSTALLLOCATIONS_EXTRA_SUBTITLE ${LANG_ENGLISH} "Please select additional installation path(s) for Wrye Bash/Flash, if desired."

  LangString PAGE_CHECK_LOCATIONS_TITLE ${LANG_ENGLISH} "Installation Location Check"
  LangString PAGE_CHECK_LOCATIONS_SUBTITLE ${LANG_ENGLISH} "A risky installation location has been detected."
  LangString unPAGE_SELECT_GAMES_ES_SUBTITLE ${LANG_ENGLISH} "Please select which locations you want to uninstall Wrye Bash from."
  LangString unPAGE_SELECT_GAMES_FALLOUT_SUBTITLE ${LANG_ENGLISH} "Please select which locations you want to uninstall Wrye Flash from."
  LangString unPAGE_SELECT_GAMES_EXTRA_SUBTITLE ${LANG_ENGLISH} "Please select which additional locations you want to uninstall Wrye Bash/Flash from."
  LangString PAGE_FINISH_TITLE ${LANG_ENGLISH} "Finished installing ${WB_NAME}"
  LangString PAGE_FINISH_SUBTITLE ${LANG_ENGLISH} "Please select post-install tasks."

  ;Assign language strings to sections
  !insertmacro MUI_FUNCTION_DESCRIPTION_BEGIN
        !insertmacro MUI_DESCRIPTION_TEXT ${Main} $(DESC_Main)
        !insertmacro MUI_DESCRIPTION_TEXT ${Shortcuts_SM} $(DESC_Shortcuts_SM)
  !insertmacro MUI_FUNCTION_DESCRIPTION_END
