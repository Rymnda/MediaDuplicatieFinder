# -*- mode: python ; coding: utf-8 -*-

import sys

sys.setrecursionlimit(sys.getrecursionlimit() * 5)


a = Analysis(
    ['MediaDuplicatieFinder.py'],
    pathex=[],
    binaries=[],
    datas=[
        ('check_white.svg', '.'),
        ('lang', 'lang'),
        ('background.jpg', '.'),
        ('BG.png', '.'),
        ('logo_flat.png', '.'),
        ('intro.mp4', '.'),
        ('Intro_about.mp4', '.'),
    ],
    hiddenimports=[],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        'torch',
        'torchvision',
        'torchaudio',
        'tensorflow',
        'keras',
        'jax',
        'pandas',
        'matplotlib',
        'numba',
        'llvmlite',
        'pyarrow',
        'sqlalchemy',
        'PyQt5',
        'PyQt6',
        'qtpy',
        'IPython',
        'pytest',
        'openvino',
    ],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='MediaDuplicatieFinder',
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
    icon=['icon.ico'],
)
coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='MediaDuplicatieFinder',
)
