@echo off
setlocal
cd /d "%~dp0"
where pnpm.cmd >nul 2>nul
if errorlevel 1 (
  echo pnpm not found. Install pnpm and frontend dependencies first.
  pause
  exit /b 1
)
pushd frontend
call pnpm.cmd build
if errorlevel 1 (
  popd
  echo Frontend build failed.
  pause
  exit /b 1
)
popd
if exist ".venv\Scripts\python.exe" (
  set "PYTHON=.venv\Scripts\python.exe"
) else (
  set "PYTHON=python"
)
rem Use the reviewed spec; do not overwrite it with generated default settings.
rem A short staging path also avoids damaging an existing running package.
set "STAGING=%TEMP%\portal-build-%RANDOM%-%RANDOM%"
"%PYTHON%" -m PyInstaller --noconfirm --distpath "%STAGING%" EmploymentPortalSearch.spec
if errorlevel 1 (
  echo EXE build failed.
  pause
  exit /b 1
)
if exist "dist\EmploymentPortalSearch" (
  move "dist\EmploymentPortalSearch" "dist\EmploymentPortalSearch.previous-%RANDOM%" >nul
  if errorlevel 1 (
    echo Close the old app before replacing it. New complete package: %STAGING%\EmploymentPortalSearch
    pause
    exit /b 1
  )
)
if not exist dist mkdir dist
robocopy "%STAGING%\EmploymentPortalSearch" "dist\EmploymentPortalSearch" /E /R:1 /W:1 /NFL /NDL /NJH /NJS /NP >nul
if errorlevel 8 (
  echo Copy failed. Complete package: %STAGING%\EmploymentPortalSearch
  pause
  exit /b 1
)
echo EXE ready: dist\EmploymentPortalSearch\EmploymentPortalSearch.exe
pause
