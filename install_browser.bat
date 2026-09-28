@echo off
setlocal EnableExtensions
cd /d "%~dp0"

if not exist ".venv\Scripts\python.exe" (
    echo Project virtual environment was not found.
    echo Install the project dependencies first.
    pause
    exit /b 1
)

echo Installing the Chromium browser required by Playwright...
".venv\Scripts\python.exe" -m playwright install chromium
if errorlevel 1 (
    echo.
    echo Installation failed. Check the network and try again.
    pause
    exit /b 1
)

echo.
echo Chromium installation completed. You can now run run.bat.
pause
