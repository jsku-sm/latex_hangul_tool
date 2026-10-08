@echo off
chcp 65001 >nul
cd /d "%~dp0"
echo LaTeX to Hangul - Windows setup
where py >nul 2>nul
if errorlevel 1 (
  echo Python 3.10 or newer is required. Install Python from https://www.python.org/downloads/
  pause
  exit /b 1
)
py -3 -c "import sys; sys.exit(0 if sys.version_info >= (3,10) else 1)"
if errorlevel 1 (
  echo Python 3.10 or newer is required.
  pause
  exit /b 1
)
py -3 -m venv .venv
if errorlevel 1 goto failed
".venv\Scripts\python.exe" -m pip install -r requirements-windows.txt
if errorlevel 1 goto failed
echo Setup completed. Open run_windows.cmd.
pause
exit /b 0
:failed
echo Setup failed. Check the error above. HWPX export needs only Python with tkinter.
pause
exit /b 1
