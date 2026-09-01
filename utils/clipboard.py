"""Clipboard helpers without a synchronous event-pump drain.

The old code ended with ``self.update()`` on every copy — a full, synchronous
processing of all pending Tk events that caused jank and re-entrancy risks on
hot paths.
"""

from typing import Any


def clip_set(root: Any, text: str) -> None:
    """Put *text* on the clipboard. Empty text is ignored."""
    if not text:
        return
    try:
        root.clipboard_clear()
        root.clipboard_append(text)
    except Exception:
        pass


def clip_get(root: Any) -> str:
    """Read the clipboard, returning '' when empty/unavailable."""
    try:
        return root.clipboard_get()
    except Exception:
        return ""


__all__ = ["clip_set", "clip_get"]