@echo off
REM Water Reach Task - open the graphical interface
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" (
  echo  First run setup_windows.bat
  pause
  exit /b 1
)
".venv\Scripts\python.exe" run.py
if errorlevel 1 pause
