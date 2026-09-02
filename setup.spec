# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller spec: SETUP/INSTALLER build.

Build order matters: run the portable (onedir) build first so the payload at
dist/DiscordTokenManager exists, then:

    pyinstaller setup.spec --noconfirm

Output: dist/DiscordTokenManager-setup.exe  (one-file installer)
"""

from PyInstaller.utils.hooks import collect_all

a = Analysis(
    ["installer_main.py"],
    pathex=["."],
    binaries=[],
    datas=[("dist/DiscordTokenManager", "appdata")],
    hiddenimports=["winwintrace", "winreg"],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=["PyQt5", "PyQt6", "PySide2", "PySide6", "matplotlib", "numpy",
              "customtkinter"],
    noarchive=False,
    optimize=1,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    name="DiscordTokenManager-setup",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,
    icon=None,
)