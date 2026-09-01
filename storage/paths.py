"""Application data paths (AppData on Windows, XDG on POSIX).

Includes one-time migration of legacy project-folder json files so long-time
users keep their existing tokens and settings.
"""

import os
import shutil
import sys

__all__ = ["app_data_dir", "APP_DATA_DIR", "TOKENS_FILE", "CONFIG_FILE", "migrate_legacy_files"]


def app_data_dir() -> str:
    """Resolve the per-user data directory for this application."""
    if sys.platform == "win32":
        base = os.getenv("APPDATA") or os.path.join(os.path.expanduser("~"), "AppData", "Roaming")
    else:
        base = os.getenv("XDG_CONFIG_HOME") or os.path.join(os.path.expanduser("~"), ".config")
    return os.path.join(base, "DiscordTokenManager")


APP_DATA_DIR = app_data_dir()

# Legacy files that used to live next to the script.
_BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_LEGACY_FILES = ("tokens.json", "config.json")

TOKENS_FILE = os.path.join(APP_DATA_DIR, "tokens.json")
CONFIG_FILE = os.path.join(APP_DATA_DIR, "config.json")


def migrate_legacy_files() -> None:
    """Copy legacy tokens/config next to the script into AppData once."""
    os.makedirs(APP_DATA_DIR, exist_ok=True)
    for name in _LEGACY_FILES:
        legacy = os.path.join(_BASE, name)
        target = os.path.join(APP_DATA_DIR, name)
        if os.path.exists(legacy) and not os.path.exists(target):
            try:
                shutil.copy2(legacy, target)
            except OSError:
                pass


migrate_legacy_files()