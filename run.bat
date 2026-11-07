@echo off
rem Starts the Smart Parking server. Double-click this file.
rem Optional: run it from Command Prompt as  run.bat COM5  to choose the Arduino port.
cd /d "%~dp0"
where py >nul 2>nul && (set PY=py) || (set PY=python)
echo Installing / checking libraries (first time only)...
%PY% -m pip install -r requirements.txt
echo.
echo Starting the server. Keep this window open. Press Ctrl+C to stop.
%PY% server.py %*
echo.
pause
