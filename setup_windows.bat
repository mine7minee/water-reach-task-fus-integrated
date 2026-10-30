@echo off
REM ==================================================================
REM  Water Reach Task - one-time setup for Windows
REM  Creates a private Python environment (.venv) in this folder and
REM  installs the required packages. Run it once after downloading.
REM ==================================================================
cd /d "%~dp0"
echo.
echo  Water Reach Task - setup
echo  ------------------------
set "PY="
where py >nul 2>&1 && set "PY=py -3"
if not defined PY (
  where python >nul 2>&1 && set "PY=python"
)
if not defined PY (
  echo  Python was not found.
  echo  Install Python 3.11 from https://www.python.org/downloads/
  echo  and TICK "Add python.exe to PATH" in the installer, then run this file again.
  pause
  exit /b 1
)
%PY% --version
if not exist ".venv\Scripts\python.exe" (
  echo  Creating virtual environment .venv ...
  %PY% -m venv .venv
  if errorlevel 1 (
    echo  Could not create the virtual environment.
    pause
    exit /b 1
  )
)
echo  Installing packages ...
".venv\Scripts\python.exe" -m pip install --upgrade pip
".venv\Scripts\python.exe" -m pip install -r requirements.txt
if errorlevel 1 (
  echo  Package installation failed. Check the internet connection and try again.
  pause
  exit /b 1
)
if not exist "config.json" copy "config.example.json" "config.json" >nul
echo.
echo  Setup complete. Double-click START.bat to open the program.
echo.
pause
