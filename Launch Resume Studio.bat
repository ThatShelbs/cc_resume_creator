@echo off
rem Double-click to start Resume Studio in your browser.
rem First run: creates a private Python environment (.venv) and installs what
rem it needs. After that it starts in a few seconds. Close this window to stop.
setlocal EnableExtensions
cd /d "%~dp0"
title Resume Studio

set "PY="
where py >nul 2>nul && set "PY=py -3"
if not defined PY (
  where python >nul 2>nul && set "PY=python"
)
if not defined PY (
  echo.
  echo   Resume Studio needs Python 3.10 or newer.
  echo   Opening python.org so you can install it. Tick "Add python.exe to PATH" in the installer.
  start "" "https://www.python.org/downloads/"
  pause
  exit /b 1
)

if not exist ".venv\Scripts\python.exe" (
  echo   First run: creating a private Python environment...
  %PY% -m venv .venv
  if errorlevel 1 (
    echo   Could not create the environment in .venv.
    pause
    exit /b 1
  )
)
set "VPY=.venv\Scripts\python.exe"

rem Reinstall packages whenever requirements.txt changes.
set "REQHASH="
for /f "skip=1 delims=" %%H in ('certutil -hashfile requirements.txt SHA256') do if not defined REQHASH set "REQHASH=%%H"
set "OLDHASH="
if exist ".venv\.req-hash" set /p OLDHASH=<".venv\.req-hash"
if not "%REQHASH%"=="%OLDHASH%" (
  echo   Installing Python packages. This happens once and takes a minute or two...
  "%VPY%" -m pip install --disable-pip-version-check --quiet -r requirements.txt
  if errorlevel 1 (
    echo   Installing packages failed. Check your internet connection and try again.
    pause
    exit /b 1
  )
  >".venv\.req-hash" echo %REQHASH%
)

"%VPY%" launcher.py %*
if errorlevel 1 pause
