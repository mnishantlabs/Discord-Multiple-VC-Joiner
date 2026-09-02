"""Typed access to application settings.

Every consumer should go through this class instead of mutating
``repository.data[...]`` directly (the old ``App`` did that at 12+ call
sites). It emits a ``SETTINGS_CHANGED`` event on save.
"""

from typing import Any

from core.events import EventBus, SETTINGS_CHANGED
from storage.settings_repository import SettingsRepository


class SettingsService:
    def __init__(self, repository: SettingsRepository, bus: EventBus) -> None:
        self._repo = repository
        self._bus = bus

    def get(self, key: str, default: Any = None) -> Any:
        return self._repo.get(key, default)

    def set(self, key: str, value: Any, persist: bool = True) -> None:
        self._repo.set(key, value)
        if persist:
            self._repo.save()
            self._bus.emit(SETTINGS_CHANGED, {key: value})

    def update(self, persist: bool = True, **kwargs: Any) -> None:
        self._repo.update(**kwargs)
        if persist:
            self._repo.save()
            self._bus.emit(SETTINGS_CHANGED, kwargs)

    # ---- convenience accessors (used by views/services frequently) --------------
    @property
    def concurrency(self) -> int:
        return int(self._repo.get("concurrency", 5) or 5)

    @property
    def delay(self) -> float:
        return float(self._repo.get("delay", 0.5) or 0)

    @property
    def proxy(self) -> str:
        return str(self._repo.get("proxy", "") or "")

    @property
    def api_timeout(self) -> int:
        return int(self._repo.get("api_timeout", 10) or 10)

    @property
    def accent(self) -> str:
        return str(self._repo.get("accent", "blue") or "blue")

    @property
    def show_badges(self) -> bool:
        return bool(self._repo.get("show_badges", True))

    @property
    def show_ids(self) -> bool:
        return bool(self._repo.get("show_ids", True))

    @property
    def compact(self) -> bool:
        return bool(self._repo.get("compact", False))

    @property
    def geometry(self) -> str:
        return str(self._repo.get("geometry", "") or "")

    @property
    def pinned_servers(self) -> list[str]:
        return list(self._repo.get("pinned_servers", []) or [])

    @property
    def recent_voice(self) -> list[dict[str, Any]]:
        return list(self._repo.get("recent_voice", []) or [])

    @property
    def columns_layout(self) -> list[float] | None:
        value = self._repo.get("layout_columns")
        if value and len(value) == 3 and all(
                isinstance(x, (int, float)) and x > 0 for x in value):
            return [float(x) for x in value]
        return None

    def set_columns_layout(self, fractions: list[float]) -> None:
        self._repo.set("layout_columns", [round(float(f), 4) for f in fractions])
        self._repo.save()

    def set_geometry(self, geometry: str) -> None:
        self._repo.set("geometry", geometry)
        self._repo.save()


__all__ = ["SettingsService"]