"""Shared PyInstaller analysis inputs used by the release spec files.

The app imports services/controllers/dialogs lazily inside methods, so plain
bytecode scanning misses them; we collect every project package + the
customtkinter assets explicitly instead.
"""

from PyInstaller.utils.hooks import collect_all, collect_submodules

ctk_datas, ctk_binaries, ctk_hidden = collect_all("customtkinter")

package_hidden = []
for pkg in ("core", "services", "storage", "controllers", "ui", "utils"):
    package_hidden += collect_submodules(pkg)

HIDDEN_IMPORTS = package_hidden + ctk_hidden + ["winwintrace"]
EXCLUDES = ["PyQt5", "PyQt6", "PySide2", "PySide6", "matplotlib", "numpy"]