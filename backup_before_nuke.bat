@echo off
set DEST=C:\temp\gosling2_backup
set SRC=%~dp0

echo Backing up to %DEST%...
mkdir "%DEST%" 2>nul

xcopy /E /I /Y "%SRC%sqldb" "%DEST%\sqldb"
xcopy /E /I /Y "%SRC%ffmpeg" "%DEST%\ffmpeg"
copy /Y "%SRC%gosling2.exe" "%DEST%\gosling2.exe"

echo Done. Safe to nuke the project folder.
pause
