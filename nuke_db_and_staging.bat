@echo off
echo Nuking Staging Folder...
if exist "C:\Users\glazb\PycharmProjects\gosling2\temp\library\staging" (
    rmdir /S /Q "C:\Users\glazb\PycharmProjects\gosling2\temp\library\staging"
    echo Staging folder deleted.
) else (
    echo Staging folder not found, skipping.
)

echo.
echo Nuking Database...
if exist "C:\Users\glazb\PycharmProjects\gosling2\sqldb\gosling2.db" (
    del /f /q "C:\Users\glazb\PycharmProjects\gosling2\sqldb\gosling2.db"
    echo Database deleted.
) else (
    echo Database not found, skipping.
)

echo.
echo Nuke complete. Restart main.py and happy bug hunting!
pause
