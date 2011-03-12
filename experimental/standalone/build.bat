@echo off
echo Wrye Bash Standalone Creator

echo Copying required files...
copy "setup.py" ".\Mopy\setup.py" > build.log
copy "bash.ico" ".\Mopy\bash.ico" > build.log

echo Executing py2exe script
cd Mopy
setup.py > "..\build.log"
cd..

echo Moving files to temp dir
xcopy ".\Mopy\dist\*.*" ".\temp\" /E /Y >> build.log

echo Deleting old files
del /S /Q ".\Mopy" >> build.log
rmdir /S /Q ".\Mopy"

rename temp Mopy

echo Fixing exe icon
reshacker -addoverwrite Mopy\Wrye Bash Launcher.exe, Mopy\Wrye Bash.exe, bash.ico, icon, 101, 0

echo Compressing exe
upx -9 ".\Mopy\Wrye Bash.exe" >> build.log

echo Cleaning up
del /Q ".\Mopy\Wrye Bash Launcher.exe"
del /Q "reshacker.ini"
del /Q "reshacker.log"

echo Done