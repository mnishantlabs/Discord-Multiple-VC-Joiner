# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller spec: COMPACT build (single self-contained EXE).

Build:  pyinstaller compact.spec --noconfirm
Output: dist/DiscordTokenManager-compact.exe
"""

from build_common import EXCLUDES, HIDDEN_IMPORTS, ctk_binaries, ctk_datas

a = Analysis(
    ["main.py"],
    pathex=["."],
    binaries=ctk_binaries,
    datas=ctk_datas,
    hiddenimports=HIDDEN_IMPORTS,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=EXCLUDES,
    noarchive=False,
    optimize=1,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    name="DiscordTokenManager-compact",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,
    icon="assets/icon.ico",
)