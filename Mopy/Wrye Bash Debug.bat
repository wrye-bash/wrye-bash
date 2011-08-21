@ECHO OFF && PUSHD "%~dp0" && SETLOCAL

SET OUTFILE=BashBugDump.log
SET PYPATH=


:: determine whether reg has the newer or older response format
SET REGCMD=reg query HKLM\SOFTWARE\Classes\.exe /ve >NUL
FOR /F "skip=1 usebackq tokens=1" %%i in (`%REGCMD%`) do SET FORMATCHECK=%%i
SET SKIPVAL=1
SET TOKENS=2
IF x"%FORMATCHECK%"==x"<NO" SET SKIPVAL=4 && SET TOKENS=3


:: get python path from registry
SET REGCMD=reg query HKLM\SOFTWARE\Python\PythonCore\2.7\InstallPath /ve
%REGCMD% >NUL 2>&1 && FOR /F "skip=%SKIPVAL% usebackq tokens=%TOKENS%*" %%i in (`%REGCMD%`) do SET PYPATH=%%j
IF NOT x"%PYPATH%"==x"" GOTO FOUND

SET REGCMD=reg query HKCU\SOFTWARE\Python\PythonCore\2.7\InstallPath /ve
%REGCMD% >NUL 2>&1 && FOR /F "skip=%SKIPVAL% usebackq tokens=%TOKENS%*" %%i in (`%REGCMD%`) do SET PYPATH=%%j
IF NOT x"%PYPATH%"==x"" GOTO FOUND

SET REGCMD=reg query HKLM\SOFTWARE\Python\PythonCore\2.6\InstallPath /ve
%REGCMD% >NUL 2>&1 && FOR /F "skip=%SKIPVAL% usebackq tokens=%TOKENS%*" %%i in (`%REGCMD%`) do SET PYPATH=%%j
IF NOT x"%PYPATH%"==x"" GOTO FOUND

SET REGCMD=reg query HKCU\SOFTWARE\Python\PythonCore\2.6\InstallPath /ve
%REGCMD% >NUL 2>&1 && FOR /F "skip=%SKIPVAL% usebackq tokens=%TOKENS%*" %%i in (`%REGCMD%`) do SET PYPATH=%%j
IF NOT x"%PYPATH%"==x"" GOTO FOUND

ECHO Python not found >%OUTFILE%
ECHO Python not found
GOTO END

:FOUND
ECHO Found Python in '%PYPATH%' >%OUTFILE%
ECHO Found Python in '%PYPATH%'
ECHO Launching Wrye Bash in debug mode >>%OUTFILE%
ECHO Launching Wrye Bash in debug mode
"%PYPATH%"Python.exe "Wrye Bash Launcher.pyw" -d >>%OUTFILE% 2>&1

:END
ENDLOCAL && EXIT /B