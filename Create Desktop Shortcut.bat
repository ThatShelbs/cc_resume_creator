@echo off
rem Puts a Resume Studio icon on your desktop.
cd /d "%~dp0"
powershell -NoProfile -ExecutionPolicy Bypass -File "scripts\create_desktop_shortcut.ps1"
echo.
pause
