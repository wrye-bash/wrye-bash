; uninstall.nsi
; Uninstallation script for Wrye Bash NSIS uninstaller.

; !include 'macro_uninstall.nsh' ; Already included from pages.nsi

;-------------------------------- The Uninstallation Code:
    Section "Uninstall"
        ; Remove files and Directories - Directories are only deleted if empty.
        ${If} $CheckState_OB == ${BST_CHECKED}
            ${If} $Path_OB != $Empty
                !insertmacro UninstallBash $Path_OB "Oblivion"
            ${EndIf}
        ${EndIf}
        ${If} $CheckState_Nehrim == ${BST_CHECKED}
            ${If} $Path_Nehrim != $Empty
                !insertmacro UninstallBash $Path_Nehrim "Nehrim"
            ${EndIf}
        ${EndIf}
        ${If} $CheckState_Skyrim == ${BST_CHECKED}
            ${If} $Path_Skyrim != $Empty
                !insertmacro UninstallBash $Path_Skyrim "Skyrim"
            ${EndIf}
        ${EndIf}
        ${If} $CheckState_Ex1 == ${BST_CHECKED}
            ${If} $Path_Ex1 != $Empty
                !insertmacro UninstallBash $Path_Ex1 "Extra Path 1"
            ${EndIf}
        ${EndIf}
        ${If} $CheckState_Ex2 == ${BST_CHECKED}
            ${If} $Path_Ex2 != $Empty
                !insertmacro UninstallBash $Path_Ex2 "Extra Path 2"
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
