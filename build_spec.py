# -*- mode: python ; coding: utf-8 -*-
"""
PyInstaller spec file for SSDiff GUI.

Build the executable with:
    pyinstaller build_spec.py --clean --noconfirm

Or from the ssdiff_gui directory:
    pyinstaller --name SSDiffGUI --onefile --windowed main.py
"""

import sys
from pathlib import Path

block_cipher = None

# Get the directory containing this spec file
SPEC_DIR = Path(SPECPATH) if 'SPECPATH' in dir() else Path('.')

a = Analysis(
    ['ssdiff_gui/main.py'],
    pathex=[str(SPEC_DIR)],
    binaries=[],
    datas=[
        # Include resources folder if it exists
        ('ssdiff_gui/resources', 'resources'),
    ],
    hiddenimports=[
        # Core packages
        'ssdiff',
        'ssdiff.core',
        'ssdiff.preprocessing',
        'ssdiff.embeddings',
        'ssdiff.lexicon',

        # GUI
        'PySide6',
        'PySide6.QtCore',
        'PySide6.QtGui',
        'PySide6.QtWidgets',

        # Data processing
        'pandas',
        'numpy',
        'scipy',
        'scipy.sparse',
        'scipy.spatial',

        # NLP
        'gensim',
        'gensim.models',
        'gensim.models.keyedvectors',
        'spacy',

        # ML
        'sklearn',
        'sklearn.cluster',
        'sklearn.decomposition',
        'sklearn.metrics',

        # Export
        'docx',

        # Standard library that might be missed
        'pickle',
        'json',
        'pathlib',
        'datetime',
        'dataclasses',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        # Exclude unnecessary packages to reduce size
        'tkinter',
        'matplotlib',
        'seaborn',
        'IPython',
        'jupyter',
        'pytest',
        # Conflicting Qt bindings
        'PyQt5',
        'PyQt6',
        # Heavy packages pulled in transitively
        'torch',
        'torchvision',
        'torchaudio',
        'sphinx',
        'docutils',
        'babel',
        'pygments',
        'numba',
        'llvmlite',
        'dask',
        'distributed',
        'xarray',
        'botocore',
        'boto3',
        'zmq',
        'pygame',
    ],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='SSDiffGUI',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,  # No console window (windowed app)
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon='ssdiff_gui/resources/icon.ico',
)
