"""Settings persistence with a corrected ``get``.

The old ``Config.get`` implementation was ``data.get(key, data.get(key, default))``
which never honored ``default``. That bug is fixed here.
"""

import json
from typing import Any

from storage import paths


def _config_file() -> str:
    return paths.CONFIG_FILE

DEFAULTS: dict[str, Any] = {
    "theme": "Dark",
    "accent": "blue",
    "concurrency": 5,
    "retry_delay": 3,
    "proxy": "",
    "api_timeout": 10,
    "auto_validate": False,
    "auto_save": True,
    "delay": 0.5,
    "show_badges": True,
    "show_ids": True,
    "pinned_servers": [],
    "recent_voice": [],
    "geometry": "",
    "compact": False,
}


class SettingsRepository:
    """Load/save typed-ish settings. Callers use :meth:`get`/:meth:`set`."""

    def __init__(self) -> None:
        self.data: dict[str, Any] = dict(DEFAULTS)
        self.load()

    def load(self) -> None:
        try:
            with open(_config_file(), "r", encoding="utf-8") as f:
                loaded = json.load(f)
            if isinstance(loaded, dict):
                for key in DEFAULTS:
                    if key in loaded:
                        self.data[key] = loaded[key]
        except (OSError, ValueError):
            pass

    def save(self) -> None:
        try:
            with open(_config_file(), "w", encoding="utf-8") as f:
                json.dump(self.data, f, indent=2, ensure_ascii=False)
        except OSError:
            pass

    def get(self, key: str, default: Any = None) -> Any:
        return self.data.get(key, default)

    def set(self, key: str, value: Any) -> None:
        self.data[key] = value

    def update(self, **kwargs: Any) -> None:
        self.data.update(kwargs)