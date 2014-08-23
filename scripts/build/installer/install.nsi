; install.nsi
; Installation script for Wrye Bash NSIS installer.


;-------------------------------- The Installation Sections:

    Section "Prerequisites" Prereq
        SectionIn RO

        ClearErrors
        
        ; Python version requires Python, wxPython, Python Comtypes and PyWin32.
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
                DetailPrint "Python 2.7.8 - Downloading..."
                inetc::get /NOCANCEL /RESUME "" "https://www.python.org/ftp/python/2.7.8/python-2.7.8.msi" "$TEMP\PythonInstallers\python-2.7.8.msi"
                Pop $R0
                ${If} $R0 == "OK"
                    DetailPrint "Python 2.7.8 - Installing..."
                    Sleep 2000
                    HideWindow
                    ExecWait '"msiexec" /i "$TEMP\PythonInstallers\python-2.7.8.msi"'
                    BringToFront
                    DetailPrint "Python 2.7.8 - Installed."
                ${Else}
                    DetailPrint "Python 2.7.8 - Download Failed!"
                    MessageBox MB_OK "Python download failed, please try running installer again or manually downloading."
                    Abort
                ${EndIf}
            ${Else}
                DetailPrint "Python 2.7 is already installed; skipping!"
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
                NSISdl::download http://downloads.sourceforge.net/project/comtypes/comtypes/0.6.2/comtypes-0.6.2.win32.exe "$TEMP\PythonInstallers\comtypes.exe"
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
                NSISdl::download http://downloads.sourceforge.net/project/pywin32/pywin32/Build%20218/pywin32-218.win32-py2.7.exe "$TEMP\PythonInstallers\pywin32.exe"
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
                !insertmacro InstallBashFiles "Oblivion" "Oblivion" "$Path_OB" $Reg_Value_OB_Py $Reg_Value_OB_Exe "Oblivion Path" $CheckState_OB_Py $CheckState_OB_Exe true
            ${EndIf}
        ${EndIf}
        ${If} $CheckState_Nehrim == ${BST_CHECKED}
            ; Install resources:
            ${If} Path_Nehrim != $Empty
                !insertmacro InstallBashFiles "Nehrim" "Oblivion" "$Path_Nehrim" $Reg_Value_Nehrim_Py $Reg_Value_Nehrim_Exe "Nehrim Path" $CheckState_Nehrim_Py $CheckState_Nehrim_Exe true
            ${EndIf}
        ${EndIf}
        ${If} $CheckState_Skyrim == ${BST_CHECKED}
            ; Install resources:
            ${If} Path_Skyrim != $Empty
                !insertmacro InstallBashFiles "Skyrim" "Skyrim" "$Path_Skyrim" $Reg_Value_Skyrim_Py $Reg_Value_Skyrim_Exe "Skyrim Path" $CheckState_Skyrim_Py $CheckState_Skyrim_Exe false
            ${EndIf}
        ${EndIf}
        ${If} $CheckState_Ex1 == ${BST_CHECKED}
            ; Install resources:
            ${If} Path_Ex1 != $Empty
                !insertmacro InstallBashFiles "Extra Path 1" "" $Path_Ex1 $Reg_Value_Ex1_Py $Reg_Value_Ex1_Exe "Extra Path 1" $CheckState_Ex1_Py $CheckState_Ex1_Exe false
            ${EndIf}
        ${EndIf}
        ${If} $CheckState_Ex2 == ${BST_CHECKED}
            ; Install resources:
            ${If} Path_Ex2 != $Empty
                !insertmacro InstallBashFiles "Extra Path 2" "" $Path_Ex2 $Reg_Value_Ex2_Py $Reg_Value_Ex2_Exe "Extra Path 2" $CheckState_Ex2_Py $CheckState_Ex2_Exe false
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
