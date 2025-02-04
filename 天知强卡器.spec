# -*- mode: python ; coding: utf-8 -*-


a = Analysis(
    ['TenchiCardEnhancer.py'],
    pathex=[],
    binaries=[],
    datas=[('GUI', 'GUI'), ('items', 'items')],
    hiddenimports=['plyer.platforms.win.notification'],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=['PyQt6.QtQuickWidgets', 'PyQt6.QtOpenGL', 'PyQt6.QtPositioning', 'PyQt6.QtQml'],
    noarchive=False,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='天知强卡器',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=['items\\icon\\furina.ico'],
)
