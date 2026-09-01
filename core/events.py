"""A small, thread-safe event bus.

Background workers and the single async loop emit events; the GUI layer
injects a *scheduler* so every handler always runs on the main thread
(``root.after``). This keeps ``core`` free of tkinter while guaranteeing
widgets are only ever touched from the Tk thread.
"""

from collections import defaultdict
from threading import RLock
from typing import Any, Callable

# Topic identifiers -----------------------------------------------------------------
STORE_CHANGED = "store.changed"                 # token data mutated
SELECTION_CHANGED = "selection.changed"         # token selection / anchor altered
VALIDATION_PROGRESS = "validation.progress"     # one token finished validating
VOICE_STATE_CHANGED = "voice.state.changed"     # voice connections changed
CHANNELS_CHANGED = "channels.changed"           # channel list for target server
SERVER_SELECTED = "server.selected"
SETTINGS_CHANGED = "settings.changed"
LOG_EVENT = "log.event"
FILTERS_CHANGED = "filters.changed"

_ALL_TOPICS = (
    STORE_CHANGED,
    SELECTION_CHANGED,
    VALIDATION_PROGRESS,
    VOICE_STATE_CHANGED,
    CHANNELS_CHANGED,
    SERVER_SELECTED,
    SETTINGS_CHANGED,
    LOG_EVENT,
    FILTERS_CHANGED,
)

Handler = Callable[[Any], None]
Scheduler = Callable[[Callable[[], None]], None]


class EventBus:
    """Topic-based pub/sub bus. Emit may be called from any thread."""

    def __init__(self) -> None:
        self._subs: dict[str, list[Handler]] = defaultdict(list)
        self._lock = RLock()
        self._scheduler: Scheduler | None = None

    def set_scheduler(self, scheduler: Scheduler | None) -> None:
        """Install a callable that runs a thunk on the main thread."""
        with self._lock:
            self._scheduler = scheduler

    def subscribe(self, topic: str, handler: Handler) -> Handler:
        """Register *handler* for *topic*; returns it (for convenient storage)."""
        with self._lock:
            self._subs[topic].append(handler)
        return handler

    def unsubscribe(self, topic: str, handler: Handler) -> None:
        with self._lock:
            try:
                self._subs[topic].remove(handler)
            except ValueError:
                pass

    def emit(self, topic: str, payload: Any = None) -> None:
        with self._lock:
            handlers = list(self._subs.get(topic, ()))
            scheduler = self._scheduler
        for handler in handlers:
            if scheduler is None:
                handler(payload)
            else:
                scheduler(lambda h=handler: h(payload))


__all__ = [
    "EventBus",
    "Handler",
    "Scheduler",
    "STORE_CHANGED",
    "SELECTION_CHANGED",
    "VALIDATION_PROGRESS",
    "VOICE_STATE_CHANGED",
    "CHANNELS_CHANGED",
    "SERVER_SELECTED",
    "SETTINGS_CHANGED",
    "LOG_EVENT",
    "FILTERS_CHANGED",
    "_ALL_TOPICS",
]