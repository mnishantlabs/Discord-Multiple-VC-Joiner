"""Observable application state.

Consolidates the many ad-hoc attributes the old ``App`` carried (``selected``,
``anchor``, ``filters``, ``collapsed_groups``, ``selected_server``,
``selected_channel``, ``channels``, ``members_collapsed``, ``log_filter``,
``log_pause``) so that a single object is the source of truth and views can
subscribe to the few events that matter to them.

This file imports no tkinter.
"""

import threading
from typing import Any

from core.enums import TokenCategory, LogLevel

# Reserved filter keys (string values of TokenCategory).
_CATEGORY_VALUES = [c.value for c in TokenCategory]
_LOG_LEVEL_VALUES = [LogLevel.INFO.value, LogLevel.SUCCESS.value, LogLevel.WARN.value,
                     LogLevel.ERROR.value, LogLevel.RATE.value]


class AppState:
    def __init__(self) -> None:
        self._lock = threading.RLock()
        self.selected: set[str] = set()
        self.anchor: str | None = None
        self.view_filter: str = "all"  # "all" | "valid" | "invalid"
        self.collapsed_groups: dict[str, bool] = {k: False for k in _CATEGORY_VALUES}
        self.selected_server: dict[str, Any] | None = None
        self.selected_channel: dict[str, Any] | None = None
        self.channels: list[dict[str, Any]] = []
        self.members_collapsed: bool = True
        self.members_split: int = 158
        self.log_filter: str = "all"
        self.log_pause: bool = False

    # -- selection ----------------------------------------------------------------
    def select(self, token: str) -> None:
        with self._lock:
            self.selected = {token}
            self.anchor = token

    def toggle(self, token: str) -> None:
        with self._lock:
            if token in self.selected:
                self.selected.discard(token)
            else:
                self.selected.add(token)

    def select_all(self, tokens: list[str]) -> None:
        with self._lock:
            self.selected = set(tokens)

    def select_group(self, tokens: list[str]) -> None:
        with self._lock:
            self.selected.update(tokens)

    def invert(self, tokens: list[str]) -> None:
        with self._lock:
            self.selected = set(tokens) - self.selected

    def set_selected(self, tokens: set[str]) -> None:
        with self._lock:
            self.selected = set(tokens)

    def clear_selection(self) -> None:
        with self._lock:
            self.selected = set()
            self.anchor = None

    # -- server / channel ----------------------------------------------------------
    def set_target_server(self, name: str, guild_id: str) -> None:
        with self._lock:
            self.selected_server = {"name": name, "id": guild_id}
            self.selected_channel = None

    def set_target_channel(self, ch: dict[str, Any]) -> None:
        with self._lock:
            self.selected_channel = ch

    # -- log ------------------------------------------------------------------------
    @staticmethod
    def log_levels() -> list[str]:
        return _LOG_LEVEL_VALUES


__all__ = ["AppState"]