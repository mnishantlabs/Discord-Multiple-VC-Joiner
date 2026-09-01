"""A toggleable filter pill (used for Valid/Invalid/Locked/Nitro/Phone)."""

import customtkinter as ctk

from ui.theme import HOVER


class FilterPill:
    def __init__(self, parent, label, active_color, hover_color,
                 on_toggle, active=True, font=None):
        self._active = active
        self._on_toggle = on_toggle
        self._active_color = active_color
        self._hover_color = hover_color
        self._font = font
        self._parent = parent
        self.button = ctk.CTkButton(
            parent, text=label, width=58, height=26, font=font,
            fg_color=active_color if active else HOVER,
            hover_color=hover_color, command=self._flip,
        )

    def _flip(self):
        self._active = not self._active
        self.button.configure(fg_color=self._active_color if self._active else HOVER,
                              hover_color=self._hover_color)
        self._on_toggle(self._active)

    def pack(self, *args, **kwargs):
        self.button.pack(*args, **kwargs)


__all__ = ["FilterPill"]