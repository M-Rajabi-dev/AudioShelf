# -*- mode: python ; coding: utf-8 -*-
import sys
import os
sys.path.insert(0, os.path.abspath(os.getcwd()))
import create_version

# Generate version_info.txt dynamically based on the VERSION file
version_str = "1.0.0"
if os.path.exists('VERSION'):
    with open('VERSION', 'r', encoding='utf-8') as f:
        version_str = f.read().strip()

create_version.generate_version_file(version_str)

block_cipher = None

# External dependencies required for runtime
app_data_files = [
    ('libmpv-2.dll', '.'),
    ('AudioShelf.ico', '.'),
    ('VERSION', '.'),
]

a = Analysis(
    ['AudioShelf.py'],
    pathex=[],
    binaries=[],
    datas=app_data_files,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
    optimize=2,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='AudioShelf',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon='AudioShelf.ico',
    version='version_info.txt',
    contents_directory='_libs'
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name='AudioShelf',
)