@echo off
echo [GOSLING] Re-seeding database from fixtures...
".venv\Scripts\python.exe" "tests\tools\inject_fixtures.py"
echo [DONE] Database has been reset.
pause
