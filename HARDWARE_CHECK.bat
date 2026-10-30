@echo off
REM Water Reach Task - step-by-step hardware check (no animal)
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" (
  echo  First run setup_windows.bat
  pause
  exit /b 1
)
".venv\Scripts\python.exe" tools\hardware_check.py
pause
