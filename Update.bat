@echo off
rem Gets the newest version of Resume Studio. Your resumes and settings live in
rem a separate folder (see Settings, "Your data") and are never touched.
setlocal
cd /d "%~dp0"
if exist ".git" (
  where git >nul 2>nul
  if not errorlevel 1 (
    git pull --ff-only
    echo.
    echo   Updated. Double-click "Launch Resume Studio.bat" to start.
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
