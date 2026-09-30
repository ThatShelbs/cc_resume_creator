@echo off
rem Double-click to install (first time only) and start Resume Taylor in your browser.
rem It sets up Python packages and the Claude tool for you, then opens the app.
rem Close this window to stop the app. Run "Doctor.bat" if something goes wrong.
setlocal EnableExtensions
cd /d "%~dp0"
title Resume Taylor

echo.
echo   ==============================================
echo    Resume Taylor - starting up
echo   ==============================================
echo.

rem The Claude tool installs here; make sure this window can find it.
set "PATH=%USERPROFILE%\.local\bin;%PATH%"

rem ---------------------------------------------------------------- Step 1: Python
echo   [1 of 4] Checking Python...
call :findpy
if not defined PY (
  echo.
  echo   Resume Taylor needs Python 3.10 or newer, and it was not found.
  where winget >nul 2>nul
  if not errorlevel 1 (
    choice /c YN /m "   Install Python 3.12 now (about 1 minute, no admin needed)"
    if not errorlevel 2 (
      winget install -e --id Python.Python.3.12 --scope user --accept-package-agreements --accept-source-agreements
      call :findpy
    )
  )
)
if not defined PY (
  echo.
  echo   Please install Python from https://www.python.org/downloads/
  echo   and tick "Add python.exe to PATH" in the installer. Then double-click this file again.
  start "" "https://www.python.org/downloads/"
  pause
  exit /b 1
)

rem ---------------------------------------------------------------- Step 2: packages
echo   [2 of 4] Checking the app's packages...
if not exist ".venv\Scripts\python.exe" (
  echo            First run: creating a private Python environment...
  %PY% -m venv .venv
  if errorlevel 1 (
    echo.
    echo   Could not create the .venv folder. Try moving this whole folder to a short
    echo   path such as C:\ResumeTaylor, then double-click this file again.
    pause
    exit /b 1
  )
)
set "VPY=.venv\Scripts\python.exe"

rem Reinstall packages whenever backend\pyproject.toml (the dependency list) changes.
set "REQHASH="
for /f "skip=1 delims=" %%H in ('certutil -hashfile backend\pyproject.toml SHA256') do if not defined REQHASH set "REQHASH=%%H"
set "OLDHASH="
if exist ".venv\.req-hash" set /p OLDHASH=<".venv\.req-hash"
if not "%REQHASH%"=="%OLDHASH%" (
  echo            Installing packages. This happens once and takes a minute or two...
  "%VPY%" -m pip install --disable-pip-version-check --quiet -e backend
  if errorlevel 1 (
    echo.
    echo   Installing packages failed. Check your internet connection and try again.
    pause
    exit /b 1
  )
  >".venv\.req-hash" echo %REQHASH%
)

rem ---------------------------------------------------------------- Step 3: settings file
echo   [3 of 4] Checking your settings file...
if not exist ".env" if exist ".env.example" copy /y ".env.example" ".env" >nul

rem ---------------------------------------------------------------- Step 4: Claude
echo   [4 of 4] Checking Claude...
where claude >nul 2>nul
if errorlevel 1 (
  echo.
  echo   The Claude tool is needed to write your resumes and it is not installed yet.
  choice /c YN /m "   Install it now (official installer from claude.ai, about 1 minute)"
  if not errorlevel 2 (
    powershell -NoProfile -ExecutionPolicy Bypass -Command "irm https://claude.ai/install.ps1 | iex"
  )
)
where claude >nul 2>nul
if errorlevel 1 (
  echo.
  echo   Claude is still not installed. You can open and edit everything in the app,
  echo   but you cannot generate resumes until it is. See the README for help.
  echo.
) else (
  call :checklogin
)

echo.
echo   Starting Resume Taylor. Your browser will open in a moment.
echo   Keep this window open while you use the app; close it to stop.
echo.
"%VPY%" launcher.py %*
if errorlevel 1 pause
exit /b 0

rem ---------------------------------------------------------------- helpers
:findpy
set "PY="
for %%C in ("py -3" "python") do (
  if not defined PY (
    %%~C -c "import sys; sys.exit(0 if sys.version_info >= (3, 10) else 1)" >nul 2>nul
    if not errorlevel 1 set "PY=%%~C"
  )
)
if not defined PY (
  for %%D in ("%LOCALAPPDATA%\Programs\Python\Python312\python.exe" "%LOCALAPPDATA%\Programs\Python\Python313\python.exe" "%LOCALAPPDATA%\Programs\Python\Python311\python.exe") do (
    if not defined PY if exist "%%~D" set PY="%%~D"
  )
)
exit /b 0

:checklogin
rem A saved API key (in .env or the app) means no login is needed.
findstr /b /r /c:"ANTHROPIC_API_KEY=sk-" ".env" >nul 2>nul
if not errorlevel 1 exit /b 0
if exist "%LOCALAPPDATA%\ResumeTaylor\secrets.json" exit /b 0
claude auth status 2>nul | findstr /c:"\"loggedIn\": true" >nul
if not errorlevel 1 exit /b 0
echo.
echo   You are not signed in to Claude yet.
echo   Choose Y to sign in with your Claude account now (a browser window opens).
echo   Choose N if you will paste an Anthropic API key in the app's Settings instead.
choice /c YN /m "   Sign in now"
if not errorlevel 2 (
  claude auth login
)
exit /b 0
