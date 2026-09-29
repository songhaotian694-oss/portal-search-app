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
"%PYTHON%" -m PyInstaller --noconfirm --clean --windowed --name EmploymentPortalSearch --icon "assets\app-icon.ico" ^
  --add-data "app\static;app\static" ^
  --add-data "frontend\dist;frontend\dist" ^
  --add-data "config\cities.txt;config" --add-data "config\majors.txt;config" ^
  --add-data "config\portal.example.yaml;config" --add-data "tests\fixtures;tests\fixtures" ^
  --collect-all playwright --collect-all rapidocr_onnxruntime --collect-all onnxruntime --collect-all cv2 launcher.py
if errorlevel 1 (
  echo EXE build failed.
  pause
  exit /b 1
)
echo EXE ready: dist\EmploymentPortalSearch\EmploymentPortalSearch.exe
pause
