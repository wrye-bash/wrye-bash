@ECHO OFF && PUSHD "%~dp0" && SETLOCAL EnableDelayedExpansion

:: Wrye Bash Debug.bat
::
:: Retrieves the Python executable path from the registry and runs Wrye Bash
:: with debugging turned on, redirecting all output to a log file.


:: initialize variables
SET OUTFILE=BashBugDump.log
SET PYPATH=


:: adapt to the output format of reg on the current OS in the current locale
:: use a known present key that has a known value for the format autodetection
SET REGCMD=reg query HKLM\SOFTWARE\Classes\.exe /ve >NUL
SET SKIPVAL=0
FOR /F "usebackq tokens=*" %%i in (`%REGCMD%`) do (
    SET LINE=%%i
    SET TESTSTR=!LINE:exefile=!
    IF NOT x"!TESTSTR!"==x"!LINE!" GOTO TOKENTEST
    SET /A SKIPVAL=SKIPVAL+1)

:TOKENTEST
SET TOKENS=2
FOR /F "skip=%SKIPVAL% usebackq tokens=%TOKENS%*" %%i in (`%REGCMD%`) do IF x"%%j"==x"exefile" GOTO TOKENTESTDONE
SET TOKENS=3
FOR /F "skip=%SKIPVAL% usebackq tokens=%TOKENS%*" %%i in (`%REGCMD%`) do IF x"%%j"==x"exefile" GOTO TOKENTESTDONE
SET TOKENS=4
FOR /F "skip=%SKIPVAL% usebackq tokens=%TOKENS%*" %%i in (`%REGCMD%`) do IF x"%%j"==x"exefile" GOTO TOKENTESTDONE
SET TOKENS=5
FOR /F "skip=%SKIPVAL% usebackq tokens=%TOKENS%*" %%i in (`%REGCMD%`) do IF x"%%j"==x"exefile" GOTO TOKENTESTDONE
:TOKENTESTDONE


:: get python path from registry
SET REGCMD=reg query HKLM\SOFTWARE\Wow6432Node\Python\PythonCore\2.7\InstallPath /ve
%REGCMD% >NUL 2>&1 && FOR /F "skip=%SKIPVAL% usebackq tokens=%TOKENS%*" %%i in (`%REGCMD%`) do SET PYPATH=%%j
IF NOT x"%PYPATH%"==x"" GOTO FOUND

SET REGCMD=reg query HKLM\SOFTWARE\Python\PythonCore\2.7\InstallPath /ve
%REGCMD% >NUL 2>&1 && FOR /F "skip=%SKIPVAL% usebackq tokens=%TOKENS%*" %%i in (`%REGCMD%`) do SET PYPATH=%%j
IF NOT x"%PYPATH%"==x"" GOTO FOUND

SET REGCMD=reg query HKCU\SOFTWARE\Wow6432Node\Python\PythonCore\2.7\InstallPath /ve
%REGCMD% >NUL 2>&1 && FOR /F "skip=%SKIPVAL% usebackq tokens=%TOKENS%*" %%i in (`%REGCMD%`) do SET PYPATH=%%j
IF NOT x"%PYPATH%"==x"" GOTO FOUND

SET REGCMD=reg query HKCU\SOFTWARE\Python\PythonCore\2.7\InstallPath /ve
%REGCMD% >NUL 2>&1 && FOR /F "skip=%SKIPVAL% usebackq tokens=%TOKENS%*" %%i in (`%REGCMD%`) do SET PYPATH=%%j
IF NOT x"%PYPATH%"==x"" GOTO FOUND

SET REGCMD=reg query HKLM\SOFTWARE\Wow6432Node\Python\PythonCore\2.6\InstallPath /ve
%REGCMD% >NUL 2>&1 && FOR /F "skip=%SKIPVAL% usebackq tokens=%TOKENS%*" %%i in (`%REGCMD%`) do SET PYPATH=%%j
IF NOT x"%PYPATH%"==x"" GOTO FOUND

SET REGCMD=reg query HKLM\SOFTWARE\Python\PythonCore\2.6\InstallPath /ve
%REGCMD% >NUL 2>&1 && FOR /F "skip=%SKIPVAL% usebackq tokens=%TOKENS%*" %%i in (`%REGCMD%`) do SET PYPATH=%%j
IF NOT x"%PYPATH%"==x"" GOTO FOUND

SET REGCMD=reg query HKCU\SOFTWARE\Wow6432Node\Python\PythonCore\2.6\InstallPath /ve
%REGCMD% >NUL 2>&1 && FOR /F "skip=%SKIPVAL% usebackq tokens=%TOKENS%*" %%i in (`%REGCMD%`) do SET PYPATH=%%j
IF NOT x"%PYPATH%"==x"" GOTO FOUND

SET REGCMD=reg query HKCU\SOFTWARE\Python\PythonCore\2.6\InstallPath /ve
%REGCMD% >NUL 2>&1 && FOR /F "skip=%SKIPVAL% usebackq tokens=%TOKENS%*" %%i in (`%REGCMD%`) do SET PYPATH=%%j
IF NOT x"%PYPATH%"==x"" GOTO FOUND


:: if all that failed, try querying the .py file association
SET REGCMD=reg query HKCR\Python.File\shell\open\command /ve
%REGCMD% >NUL 2>&1 || GOTO NOTFOUND
FOR /F "skip=%SKIPVAL% usebackq tokens=%TOKENS%*" %%i in (`%REGCMD%`) do SET PYASSOC=%%j
SET PYASSOC=!PYASSOC:"=?!
FOR /F "tokens=1 delims=?" %%i in ("%PYASSOC%") do SET PYTHON=%%i
IF NOT x"%PYTHON%"==x"" GOTO FOUNDPYTHON


:NOTFOUND
ECHO Python not found >%OUTFILE%
ECHO Python not found
GOTO END


:FOUND
SET PYTHON=%PYPATH%python.exe

:FOUNDPYTHON
ECHO Found Python at '%PYTHON%' >%OUTFILE%
ECHO Found Python at '%PYTHON%'
ECHO Launching wbtest >>%OUTFILE%
ECHO Launching wbtest
"%PYTHON%" "wbtest.py" -d >>%OUTFILE% 2>&1


:END
ENDLOCAL && EXIT /B
