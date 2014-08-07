; Wrye Bash.nsi
Unicode true

;-------------------------------- Includes:
    !addincludedir "scripts\build\installer"
    !include "MUI2.nsh"
    !include "x64.nsh"
    !include "LogicLib.nsh"
    !include "WinVer.nsh"
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

;-------------------------------- Include Local Script Files

    !include "macros.nsh"
    !include "pages.nsi"
    !include "install.nsi"
    !include "uninstall.nsi"

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
