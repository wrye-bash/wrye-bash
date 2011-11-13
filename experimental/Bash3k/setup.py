from cx_Freeze import setup, Executable

exe = Executable(
    script="Wrye Bash Launcher.pyw",
    base="Win32GUI",
    )

setup(
    name = "Wrye Bash3k",
    version = "0.1",
    description = "Mod management tool for TES3/4/5 and FO3/FNV",
    executables = [exe]
    )
