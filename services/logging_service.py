"""Activity logging: a ring buffer plus an interface for the GUI.

This replaces the old quadratic ``_render_logs`` path (delete + re-insert all
lines on every append). The service keeps a bounded buffer; the view renders
incrementally and only rebuilds on filter/search changes.
"""

import string
from collections import deque
from datetime import datetime

from core.enums import LogLevel
from core.events import EventBus, LOG_EVENT
from core.constants import LOG_BUFFER_SIZE


class LogRecord:
    __slots__ = ("timestamp", "message", "level")

    def __init__(self, timestamp: str, message: str, level: str) -> None:
        self.timestamp = timestamp
        self.message = message
        self.level = level

    def __iter__(self):
        return iter((self.timestamp, self.message, self.level))


def _now() -> str:
    return datetime.now().strftime("%H:%M:%S")


class LogService:
    """Thread-safe ring-buffer of activity messages emitted on the bus."""

    def __init__(self, bus: EventBus, size: int = LOG_BUFFER_SIZE) -> None:
        self._bus = bus
        self._buffer: deque[LogRecord] = deque(maxlen=size)

    def log(self, message: str, level: str = LogLevel.INFO.value) -> None:
        record = LogRecord(_now(), message, level)
        self._buffer.append(record)
        self._bus.emit(LOG_EVENT, record)

    def warning(self, message: str) -> None:
        self.log(message, LogLevel.WARN.value)

    def error(self, message: str) -> None:
        self.log(message, LogLevel.ERROR.value)

    def success(self, message: str) -> None:
        self.log(message, LogLevel.SUCCESS.value)

    def info(self, message: str) -> None:
        self.log(message, LogLevel.INFO.value)

    def rate(self, message: str) -> None:
        self.log(message, LogLevel.RATE.value)

    def iter_all(self):
        return list(self._buffer)

    @property
    def count(self) -> int:
        return len(self._buffer)

    def clear(self) -> None:
        self._buffer.clear()


__all__ = ["LogService", "LogRecord"]