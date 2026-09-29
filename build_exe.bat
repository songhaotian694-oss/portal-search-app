@echo off
setlocal
cd /d "%~dp0"
if exist ".venv\Scripts\python.exe" (
  set "PYTHON=.venv\Scripts\python.exe"
) else (
  set "PYTHON=python"
)
"%PYTHON%" -m PyInstaller --noconfirm --clean --windowed --name EmploymentPortalSearch --icon "assets\app-icon.ico" ^
  --add-data "app\static;app\static" ^
  --add-data "config\cities.txt;config" --add-data "config\majors.txt;config" ^
  --add-data "config\portal.example.yaml;config" --add-data "tests\fixtures;tests\fixtures" ^
  --collect-all playwright --collect-all rapidocr_onnxruntime --collect-all onnxruntime --collect-all cv2 launcher.py
if errorlevel 1 (
  echo 打包失败。
  pause
  exit /b 1
)
echo 打包完成：dist\EmploymentPortalSearch\EmploymentPortalSearch.exe
pause
