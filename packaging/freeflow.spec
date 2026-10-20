# -*- mode: python ; coding: utf-8 -*-
import sys
import os
from PyInstaller.utils.hooks import collect_data_files, collect_submodules

block_cipher = None

# Collect assets
datas = [
    ('../assets', 'assets'),
]

# Hidden imports for cross-platform modules
hiddenimports = [
    'PyQt6',
    'PyQt6.QtCore',
    'PyQt6.QtGui',
    'PyQt6.QtWidgets',
    'PyQt6.QtNetwork',
    'pynput',
    'pynput.keyboard',
    'pynput.keyboard._xorg',
    'pynput.keyboard._uinput',
    'pynput.keyboard._win32',
    'pynput.keyboard._darwin',
    'sounddevice',
    'numpy',
    'scipy',
    'scipy.io.wavfile',
    'groq',
    'dotenv',
    'pyperclip',
    'pyautogui',
    'plyer',
    'plyer.platforms',
]

if sys.platform.startswith('linux'):
    hiddenimports.extend(['evdev', 'evdev.ecodes'])

a = Analysis(
    ['../app.py'],
    pathex=['..'],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=['tkinter', 'matplotlib', 'pandas', 'IPython'],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='freeflow',
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
    icon='../assets/icon.png' if not sys.platform.startswith('win') else '../assets/icon.ico',
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='freeflow',
)
