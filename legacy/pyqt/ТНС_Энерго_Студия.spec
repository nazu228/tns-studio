# Build with a bounded DLL search path; unrelated desktop tools must not be bundled.
import os
import sys
from pathlib import Path
python_root=Path(sys.base_prefix)
windows_root=Path(os.environ.get('SystemRoot',r'C:\Windows'))
os.environ['PATH']=os.pathsep.join(map(str,[python_root,python_root/'DLLs',windows_root/'System32',windows_root]))

# -*- mode: python ; coding: utf-8 -*-


a = Analysis(
    ['app_gui.py'],
    pathex=[],
    binaries=[],
    datas=[],
    hiddenimports=['openpyxl', 'boto3', 'botocore', 'sqlite3', 'sync_manager', 'ui_sync_components', 'core_engine'],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='ТНС_Энерго_Студия',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
