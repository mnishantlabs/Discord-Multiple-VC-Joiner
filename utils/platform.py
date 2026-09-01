"""Platform-specific Tk binding helpers.

The old code bound middle-click to ``<Button-2>``, which is correct on
Windows/Linux but *right-click* on macOS. This module normalizes it.
"""

import sys
from typing import Any, Callable

IS_MAC = sys.platform == "darwin"

# On macOS the middle button reports as Button-3 (Button-2 is right-click).
MIDDLE_BUTTON = "<Button-3>" if IS_MAC else "<Button-2>"

# Tk event.state modifier masks for shift / control.
MOD_SHIFT = 0x1
MOD_CTRL = 0x4


def bind_middle_click(widget: Any, handler: Callable[[Any], None]) -> None:
    """Bind the platform-correct middle-button event."""
    widget.bind(MIDDLE_BUTTON, handler)


__all__ = ["MIDDLE_BUTTON", "MOD_SHIFT", "MOD_CTRL", "IS_MAC", "bind_middle_click"]