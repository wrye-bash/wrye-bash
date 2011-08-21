@ECHO OFF && PUSHD "%~dp0" && SETLOCAL

SET OUTFILE=BashBugDump.log
SET PYPATH=

:: get python path from registry
SET REGCMD=reg query HKLM\SOFTWARE\Python\PythonCore\2.7\InstallPath /ve
%REGCMD% >NUL 2>&1 && FOR /F "skip=4 usebackq tokens=3*" %%i in (`%REGCMD%`) do SET PYPATH=%%j
IF NOT x"%PYPATH%"==x"" GOTO FOUND

SET REGCMD=reg query HKCU\SOFTWARE\Python\PythonCore\2.7\InstallPath /ve
%REGCMD% >NUL 2>&1 && FOR /F "skip=4 usebackq tokens=3*" %%i in (`%REGCMD%`) do SET PYPATH=%%j
IF NOT x"%PYPATH%"==x"" GOTO FOUND

SET REGCMD=reg query HKLM\SOFTWARE\Python\PythonCore\2.6\InstallPath /ve
%REGCMD% >NUL 2>&1 && FOR /F "skip=4 usebackq tokens=3*" %%i in (`%REGCMD%`) do SET PYPATH=%%j
IF NOT x"%PYPATH%"==x"" GOTO FOUND

SET REGCMD=reg query HKCU\SOFTWARE\Python\PythonCore\2.6\InstallPath /ve
%REGCMD% >NUL 2>&1 && FOR /F "skip=4 usebackq tokens=3*" %%i in (`%REGCMD%`) do SET PYPATH=%%j
IF NOT x"%PYPATH%"==x"" GOTO FOUND

ECHO Python not found >%OUTFILE%
GOTO END

:FOUND
"%PYPATH%"Python.exe "Wrye Bash Launcher.pyw" -d >%OUTFILE% 2>&1

:END
ENDLOCAL && EXIT /B