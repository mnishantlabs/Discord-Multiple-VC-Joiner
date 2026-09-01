"""A reusable row list used for servers, channels, recent invites, etc.

Replaces the repeated ``for w in frame.winfo_children(): w.destroy()`` +
rebuild loops. Keeps an item list and rebuilds on demand; supports per-item
click, right-click, and middle-click callbacks plus a tooltip renderer.
"""

from typing import Any, Callable

import customtkinter as ctk


class ButtonList:
    """Renders a vertical list of tappable rows inside a scrollable frame."""

    def __init__(self, parent, row_height=38, font=None, fg_color=None):
        self.container = ctk.CTkScrollableFrame(parent, fg_color=fg_color, corner_radius=8)
        self._row_height = row_height
        self._font = font
        self._items: list[Any] = []
        self._render_row: Callable[[Any], dict] | None = None
        self._widgets = []

    def pack(self, *args, **kwargs):
        self.container.pack(*args, **kwargs)

    def set_renderer(self, renderer: Callable[[Any], dict]) -> None:
        """``renderer(item)`` returns a dict of row options for CTkButton."""
        self._render_row = renderer

    def set_items(self, items: list[Any]) -> None:
        self._items = items
        self.rebuild()

    def clear(self) -> None:
        for w in self._widgets:
            w.destroy()
        self._widgets = []

    def rebuild(self) -> None:
        self.clear()
        if self._render_row is None:
            return
        for item in self._items:
            opts = self._render_row(item)
            btn = ctk.CTkButton(
                self.container, anchor="w", height=self._row_height,
                font=self._font, **opts,
            )
            btn.pack(fill="x", pady=2)
            self._widgets.append(btn)

    def add_row(self, item: Any):
        opts = self._render_row(item) if self._render_row else {}
        btn = ctk.CTkButton(self.container, anchor="w", height=self._row_height,
                            font=self._font, **opts)
        btn.pack(fill="x", pady=2)
        self._widgets.append(btn)
        return btn


__all__ = ["ButtonList"]