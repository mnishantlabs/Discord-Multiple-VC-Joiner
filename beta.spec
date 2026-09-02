# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller spec: BETA build (single self-contained EXE).

This is the standalone experimental build. It always launches in beta mode
(the Material 'Clean Desktop' redesign) via ``main_beta.py``; no flag needed.

Build:  pyinstaller beta.spec --noconfirm
Output: dist/DiscordTokenManager-Beta.exe
"""

from build_common import EXCLUDES, HIDDEN_IMPORTS, ctk_binaries, ctk_datas

a = Analysis(
    ["main_beta.py"],
    pathex=["."],
    binaries=ctk_binaries,
    datas=ctk_datas + [("assets/icon.ico", ".")],
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
    name="DiscordTokenManager-Beta",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,
    icon="assets/icon.ico",
)
