; uninstall.nsi
; Uninstallation script for Wrye Bash NSIS uninstaller.

; !include 'macro_uninstall.nsh' ; Already included from pages.nsi

;-------------------------------- The Uninstallation Code:
    Section "Uninstall"

        ; Ensure that we're working with current registry paths
        !insertmacro UpdateRegistryPaths

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

        ${If} $CheckState_Fallout3 == ${BST_CHECKED}
            ${If} $Path_Fallout3 != $Empty
                !insertmacro UninstallBash $Path_Fallout3 "Fallout3"
            ${EndIf}
        ${EndIf}

        ${If} $CheckState_FalloutNV == ${BST_CHECKED}
            ${If} $Path_FalloutNV != $Empty
                !insertmacro UninstallBash $Path_FalloutNV "FalloutNV"
            ${EndIf}
        ${EndIf}

        ${If} $CheckState_Enderal == ${BST_CHECKED}
            ${If} $Path_Enderal != $Empty
                !insertmacro UninstallBash $Path_Enderal "Enderal"
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

        ; Refresh the registry paths
        !insertmacro UpdateRegistryPaths

        ; If it is a complete uninstall, remove the shared data:
        ; all registry paths must be clear for the application to completely uninstall
        ; WARNING: if the uninstaller is not cleaned up, then uninstallation failed

        ${If} $Path_OB == $Empty
        ${AndIf} $Path_Nehrim == $Empty
        ${AndIf} $Path_Skyrim == $Empty
        ${AndIf} $Path_Fallout4 == $Empty
        ${AndIf} $Path_SkyrimSE == $Empty
        ${AndIf} $Path_Fallout3 == $Empty
        ${AndIf} $Path_FalloutNV == $Empty
        ${AndIf} $Path_Enderal == $Empty
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
