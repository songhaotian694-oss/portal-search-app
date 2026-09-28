@echo off
setlocal
cd /d "%~dp0"
python -m PyInstaller --noconfirm --clean --windowed --name EmploymentPortalSearch ^
  --add-data "app\static;app\static" --add-data "config;config" ^
  --collect-all rapidocr_onnxruntime --collect-all onnxruntime --collect-all cv2 launcher.py
echo 打包完成：dist\EmploymentPortalSearch\EmploymentPortalSearch.exe
pause
