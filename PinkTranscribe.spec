# -*- mode: python ; coding: utf-8 -*-


a = Analysis(
    ['E:\\Projects\\Pink Transcribe\\main.py'],
    pathex=[],
    binaries=[],
    datas=[('E:\\Projects\\Pink Transcribe\\app\\ui\\styles.qss', 'app/ui'), ('E:\\Projects\\Pink Transcribe\\app\\ui\\app_icon.jpg', 'app/ui'), ('E:\\Projects\\Pink Transcribe\\venv\\Lib\\site-packages\\faster_whisper\\assets', 'faster_whisper/assets'), ('E:\\Projects\\Pink Transcribe\\venv\\Lib\\site-packages\\nvidia\\cublas\\bin', 'nvidia/cublas/bin'), ('E:\\Projects\\Pink Transcribe\\venv\\Lib\\site-packages\\nvidia\\cudnn\\bin', 'nvidia/cudnn/bin')],
    hiddenimports=['sounddevice', 'faster_whisper', 'PySide6.QtCore', 'PySide6.QtWidgets', 'PySide6.QtGui'],
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
    [],
    exclude_binaries=True,
    name='PinkTranscribe',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='PinkTranscribe',
)
