@echo off
rem Checks that everything Resume Taylor needs is in place. Safe to paste the output in a bug report.
cd /d "%~dp0"
set "PATH=%USERPROFILE%\.local\bin;%PATH%"
if exist ".venv\Scripts\python.exe" ( ".venv\Scripts\python.exe" scripts\doctor.py ) else ( where py >nul 2>nul && ( py -3 scripts\doctor.py ) || ( python scripts\doctor.py ) )
echo.
pause
