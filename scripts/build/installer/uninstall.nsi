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

        ${If} $CheckState_Fallout4 == ${BST_CHECKED}
            ${If} $Path_Fallout4 != $Empty
                !insertmacro UninstallBash $Path_Fallout4 "Fallout4"
            ${EndIf}
        ${EndIf}

        ${If} $CheckState_SkyrimSE == ${BST_CHECKED}
            ${If} $Path_SkyrimSE != $Empty
                !insertmacro UninstallBash $Path_SkyrimSE "SkyrimSE"
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


        ;If it is a complete uninstall, remove the shared data:
        ;Added support for 64-bit operating systems --fireundubh

        ReadRegStr $Path_OB       HKLM "SOFTWARE\Wrye Bash" "Oblivion Path"
        ${If} $Path_OB == $Empty
            ReadRegStr $Path_OB HKLM "SOFTWARE\WOW6432Node\Wrye Bash" "Oblivion Path"
        ${EndIf}

        ReadRegStr $Path_Nehrim   HKLM "Software\Wrye Bash" "Nehrim Path"
        ${If} $Path_Nehrim == $Empty
            ReadRegStr $Path_Nehrim HKLM "SOFTWARE\WOW6432Node\Wrye Bash" "Nehrim Path"
        ${EndIf}

        ReadRegStr $Path_Skyrim   HKLM "Software\Wrye Bash" "Skyrim Path"
        ${If} $Path_Skyrim == $Empty
            ReadRegStr $Path_Skyrim HKLM "SOFTWARE\WOW6432Node\Wrye Bash" "Skyrim Path"
        ${EndIf}

        ReadRegStr $Path_Fallout4 HKLM "SOFTWARE\Wrye Bash" "Fallout4 Path"
        ${If} $Path_Fallout4 == $Empty
            ReadRegStr $Path_Fallout4 HKLM "SOFTWARE\WOW6432Node\Wrye Bash" "Fallout4 Path"
        ${EndIf}

        ReadRegStr $Path_SkyrimSE HKLM "SOFTWARE\Wrye Bash" "SkyrimSE Path"
        ${If} $Path_SkyrimSE == $Empty
            ReadRegStr $Path_SkyrimSE HKLM "SOFTWARE\WOW6432Node\Wrye Bash" "SkyrimSE Path"
        ${EndIf}

        ReadRegStr $Path_Ex1      HKLM "SOFTWARE\Wrye Bash" "Extra Path 1"
        ${If} $Path_Ex1 == $Empty
            ReadRegStr $Path_Ex1 HKLM "SOFTWARE\WOW6432Node\Wrye Bash" "Extra Path 1"
        ${EndIf}

        ReadRegStr $Path_Ex2      HKLM "SOFTWARE\Wrye Bash" "Extra Path 2"
        ${If} $Path_Ex2 == $Empty
            ReadRegStr $Path_Ex2 HKLM "SOFTWARE\WOW6432Node\Wrye Bash" "Extra Path 2"
        ${EndIf}

        ${If} $Path_OB == $Empty
            ${AndIf} $Path_Nehrim == $Empty
            ${AndIf} $Path_Skyrim == $Empty
            ${AndIf} $Path_Fallout4 == $Empty
            ${AndIf} $Path_SkyrimSE == $Empty
            ${AndIf} $Path_Ex1 == $Empty
            ${AndIf} $Path_Ex2 == $Empty
                DeleteRegKey HKLM "SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall\Wrye Bash"
                ReadRegStr $0 HKLM "SOFTWARE\Wrye Bash" "Installer Path"
                ${If} $0 == $Empty
                    ReadRegStr $0 HKLM "SOFTWARE\WOW6432Node\Wrye Bash" "Installer Path"
                    DeleteRegKey HKLM "SOFTWARE\WOW6432Node\Wrye Bash"
                ${Else}
                    DeleteRegKey HKLM "SOFTWARE\Wrye Bash"
                ${EndIf}
                ;Delete stupid Windows created registry keys:
                DeleteRegKey HKCU "SOFTWARE\Microsoft\Windows\CurrentVersion\App Management\ARPCache\Wrye Bash"
                DeleteRegValue HKCR "Local Settings\Software\Microsoft\Windows\Shell\MuiCache" "$COMMONFILES\Wrye Bash\Uninstall.exe"
                DeleteRegValue HKCU "SOFTWARE\Classes\Local Settings\Software\Microsoft\Windows\Shell\MuiCache" "$COMMONFILES\Wrye Bash\Uninstall.exe"
                DeleteRegValue HKCU "SOFTWARE\Microsoft\Windows\ShellNoRoam\MuiCache" "$COMMONFILES\Wrye Bash\Uninstall.exe"
                DeleteRegValue HKCR "Local Settings\Software\Microsoft\Windows\Shell\MuiCache" "$0"
                DeleteRegValue HKCU "SOFTWARE\Classes\Local Settings\Software\Microsoft\Windows\Shell\MuiCache" "$0"
                DeleteRegValue HKCU "SOFTWARE\Microsoft\Windows\ShellNoRoam\MuiCache" "$0"
                Delete "$SMPROGRAMS\Wrye Bash\*.*"
                RMDir "$SMPROGRAMS\Wrye Bash"
                Delete "$COMMONFILES\Wrye Bash\*.*"
                RMDir "$COMMONFILES\Wrye Bash"
            ${EndIf}
        SectionEnd
