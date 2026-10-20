# -*- mode: python ; coding: utf-8 -*-
import sys
import os
from PyInstaller.utils.hooks import collect_data_files, collect_submodules

block_cipher = None

# Collect assets
datas = [
    ('../assets', 'assets'),
]

# Hidden imports tailored per platform
hiddenimports = [
    'PyQt6',
    'PyQt6.QtCore',
    'PyQt6.QtGui',
    'PyQt6.QtWidgets',
    'PyQt6.QtNetwork',
    'pynput',
    'pynput.keyboard',
    'sounddevice',
    'numpy',
    'scipy',
    'scipy.io.wavfile',
    'groq',
    'dotenv',
    'pyperclip',
    'pyautogui',
    'plyer',
]

if sys.platform.startswith('linux'):
    hiddenimports.extend([
        'pynput.keyboard._xorg',
        'pynput.keyboard._uinput',
        'evdev',
        'evdev.ecodes',
    ])
elif sys.platform == 'win32':
    hiddenimports.extend([
        'pynput.keyboard._win32',
        'plyer.platforms.win.notification',
    ])
elif sys.platform == 'darwin':
    hiddenimports.extend([
        'pynput.keyboard._darwin',
        'plyer.platforms.macosx.notification',
    ])

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

exe_icon = None
if sys.platform.startswith('win'):
    exe_icon = '../assets/icon.ico'
elif sys.platform == 'darwin':
    exe_icon = '../assets/icon.png'

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
    icon=exe_icon,
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

# On macOS, generate native FreeFlow.app bundle
if sys.platform == 'darwin':
    app = BUNDLE(
        coll,
        name='FreeFlow.app',
        icon='../assets/icon.png',
        bundle_identifier='com.bheeshamks.freeflow',
        info_plist={
            'CFBundleName': 'FreeFlow',
            'CFBundleDisplayName': 'FreeFlow',
            'CFBundleIdentifier': 'com.bheeshamks.freeflow',
            'CFBundleVersion': '1.1.0',
            'CFBundleShortVersionString': '1.1.0',
            'NSMicrophoneUsageDescription': 'FreeFlow requires microphone access for voice dictation.',
            'NSAppleEventsUsageDescription': 'FreeFlow requires accessibility control to type transcribed text into active applications.',
            'LSUIElement': False,
            'NSHighResolutionCapable': True,
        }
    )
