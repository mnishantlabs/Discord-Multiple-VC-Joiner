# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller spec: PORTABLE build (onedir folder).

Build:  pyinstaller DiscordTokenManager.spec --noconfirm
Output: dist/DiscordTokenManager/DiscordTokenManager.exe
Zip that folder to distribute "portable" edition.
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
    exclude_binaries=True,
    name="DiscordTokenManager",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,
    icon=None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=False,
    name="DiscordTokenManager",
)