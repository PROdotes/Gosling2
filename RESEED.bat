@echo off
echo [GOSLING] Re-seeding database from fixtures...
del /f /q sqldb\gosling2.db
".venv\Scripts\python.exe" "tests\tools\inject_fixtures.py"
echo [DONE] Database has been reset.
