@echo off
rem Gets the newest version of Resume Taylor. Your resumes and settings live in
rem a separate folder (see Settings, "Your data") and are never touched.
setlocal
cd /d "%~dp0"
if exist ".git" (
  where git >nul 2>nul
  if not errorlevel 1 (
    git pull --ff-only
    rem The app was renamed from Resume Studio; point an old desktop shortcut at the new launcher.
    if exist "%USERPROFILE%\Desktop\Resume Studio.lnk" powershell -NoProfile -ExecutionPolicy Bypass -File "scripts\create_desktop_shortcut.ps1"
    if exist "%USERPROFILE%\OneDrive\Desktop\Resume Studio.lnk" powershell -NoProfile -ExecutionPolicy Bypass -File "scripts\create_desktop_shortcut.ps1"
    echo.
    echo   Updated. Double-click "Launch Resume Taylor.bat" to start.
    pause
    exit /b 0
  )
)
echo.
echo   This copy was downloaded as a ZIP, so it cannot update itself.
echo   To update: download the newest ZIP from the project page, unzip it to a NEW folder,
echo   and use that folder from now on. Your data is kept safe outside the folder.
start "" "https://github.com/ThatShelbs/cc_resume_creator"
pause
