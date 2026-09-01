"""Threading helpers used by the GUI layer.

The heavy concurrency lives in the async services (asyncio.Semaphore).
This module only carries thin Tk-friendly helpers for blocking calls that
must not run on the UI thread.
"""

from typing import Any, Callable, TypeVar

T = TypeVar("T")


class UiDispatcher:
    """Wraps a Tk root so background callbacks land on the main thread.

    The old code called ``self.after(0, ...)`` from worker threads, which is
    technically supported by Tkinter but easy to misuse; this class makes the
    intent explicit and testable.
    """

    def __init__(self, root: Any) -> None:
        self._root = root

    def call_after(self, delay_ms: int, fn: Callable[[], None], *args: Any) -> None:
        self._root.after(delay_ms, fn, *args)

    def on_ui(self, fn: Callable[[], None]) -> None:
        """Schedule *fn* as the next idle job on the Tk thread."""
        self._root.after(0, fn)


__all__ = ["UiDispatcher", "T"]