"""A toolbar icon button with a tooltip (compact, accent-aware)."""

import customtkinter as ctk

from ui.theme import HOVER
from ui.widgets.tooltip import Tooltip


class IconButton:
    """Wraps a small square CTkButton + tooltip for use in the toolbar."""

    def __init__(self, parent, text, tooltip, command, accent_hover,
                 width=34, height=30, font=None):
        self.button = ctk.CTkButton(
            parent, text=text, command=command, width=width, height=height,
            fg_color=HOVER, hover_color=accent_hover, corner_radius=6, font=font,
        )
        self._tooltip = Tooltip(self.button, tooltip)

    def pack(self, *args, **kwargs):
        self.button.pack(*args, **kwargs)


__all__ = ["IconButton"]