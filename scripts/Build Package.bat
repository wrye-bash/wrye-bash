@Echo off
title Wrye Bash Release Build Script v2

:Choice
CLS
ECHO.
ECHO.
ECHO.
ECHO Type a, Build and package the Installer and Manual packages
ECHO Type i, Build just the Installer version of Wrye Bash
ECHO Type w, Build and package the Standalone version of Wrye Bash
ECHO Type m, Build and package the Source version of Wrye Bash
ECHO Type h, Help
ECHO Type q, Quit
ECHO.
SET Choice=
SET /P Choice=No, I dont do coffee, make a choice and press enter:
IF NOT '%Choice%'=='' SET Choice=%Choice:~0,1%
IF /I '%Choice%'=='A' GOTO TheWorks
IF /I '%Choice%'=='I' GOTO Installer
IF /I '%Choice%'=='W' GOTO WBSAPackage
IF /I '%Choice%'=='M' GOTO SourcePackage
IF /I '%Choice%'=='H' GOTO Help
IF /I '%Choice%'=='Q' GOTO End
ECHO.
ECHO.
ECHO Erm "%Choice%" ? .. haha funny (snore). Please choose a,i,w,m,h or q.
ECHO.
PAUSE
GOTO Choice

:Help
CLS
ECHO.
ECHO.
ECHO                                    Wrye Bash Release Build Help
ECHO -----------------------------------------------------------------------
ECHO            You need help? Here's a few coins go phone someone :)
ECHO.
ECHO If this script fails to produce the desired packages you will need ..
ECHO Nullsoft Scriptable Install System (NSIS) - installed
ECHO You will also need Python 2.7.3, wxPython, comtypes, pywin32 and py2exe
ECHO Also copy from the svn Wrye Bash\scripts\zipextimporter.py into ..
ECHO "C:\Python27\Lib\site-packages\" .. In here (overwrite the old one).
ECHO.
ECHO After making your choice, you will find the new builds on completion in
ECHO svn "Wrye Bash\scripts\Dist\"
ECHO.
ECHO     end of help. No, really, thats it. Go home, nothing to see here
ECHO -----------------------------------------------------------------------
ECHO.
ECHO.
PAUSE
GOTO Choice

:TheWorks
CLS
ECHO.
ECHO.
ECHO.
ECHO                    Building Wrye Bash packages, patience Avatar ...
ECHO.
"C:\Python27\python.exe" package_for_release.py
ECHO.
ECHO.
ECHO                                       All Done! Hopefully ...
ECHO.
GOTO End

:Installer
CLS
ECHO.
ECHO.
ECHO.
ECHO                    Building Wrye Bash packages, patience Avatar ...
ECHO.
"C:\Python27\python.exe" package_for_release.py -i
ECHO.
ECHO.
ECHO                                       All Done! Hopefully ...
ECHO.
GOTO End

:WBSAPackage
CLS
ECHO.
ECHO.
ECHO.
ECHO                    Building Wrye Bash packages, patience Avatar ...
ECHO.
"C:\Python27\python.exe" package_for_release.py -w
ECHO.
ECHO.
ECHO                                       All Done! Hopefully ...
ECHO.
GOTO End

:SourcePackage
CLS
ECHO.
ECHO.
ECHO.
ECHO                    Building Wrye Bash packages, patience Avatar ...
ECHO.
"C:\Python27\python.exe" package_for_release.py -m
ECHO.
ECHO.
ECHO                                       All Done! Hopefully ...
ECHO.

:End
ECHO.
ECHO                    Exiting script, pleasure to be of service.
ECHO.
ECHO.
PAUSE
EXIT