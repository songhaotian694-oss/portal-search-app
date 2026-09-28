@echo off
setlocal EnableExtensions
rem Double-click in Explorer or run in cmd.exe. Git Bash does not parse .bat syntax.
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0run.ps1"
if errorlevel 1 pause
