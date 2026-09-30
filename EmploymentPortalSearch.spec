# -*- mode: python ; coding: utf-8 -*-
from PyInstaller.utils.hooks import collect_all, collect_data_files

datas = [('frontend/dist', 'frontend/dist'), ('config/cities.txt', 'config'), ('config/majors.txt', 'config'), ('config/portal.example.yaml', 'config'), ('config/portal.profile.yaml', 'config'), ('tests/fixtures', 'tests/fixtures')]
datas += [('config/search_rules.json', 'config')]
binaries = []
hiddenimports = []
tmp_ret = collect_all('playwright')
datas += tmp_ret[0]; binaries += tmp_ret[1]; hiddenimports += tmp_ret[2]
# Keep OCR models/configuration; standard hooks collect ONNX/OpenCV libraries.
datas += collect_data_files('rapidocr_onnxruntime', includes=['models/*.onnx', 'config.yaml'])
hiddenimports += ['rapidocr_onnxruntime', 'onnxruntime', 'cv2']


a = Analysis(
    ['launcher.py'],
    pathex=[],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=['torch', 'torchvision', 'torchaudio', 'sentence_transformers',
              'transformers', 'scipy', 'sklearn', 'pandas', 'matplotlib',
              'onnxruntime.tools', 'onnxruntime.datasets', 'pytest', 'IPython'],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='EmploymentPortalSearch',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=['assets/app-icon.ico'],
)
coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='EmploymentPortalSearch',
)
