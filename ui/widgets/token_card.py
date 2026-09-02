"""A single compact token row component.

Replaces the old multi-line card (detail rows, checkbox, id snippet) with a
dense file-manager style row:

    🟢 yoruarc#0  [📱][⭐]         60 Servers

One click selects (accent border + tinted background, no checkbox), badges
(phone / nitro) are tiny glyphs, and double-click opens the Properties dialog.
The height follows the selected UI density: comfortable / compact / ultra.
"""

import tkinter as tk

import customtkinter as ctk

from ui.text import truncate
from ui.theme import (
    CARD,
    SEC,
    blend,
    accent_hover_hex,
    selected_bg,
)
from utils.platform import MOD_CTRL, MOD_SHIFT

# Density -> row height (px).
CARD_HEIGHTS = {"comfortable": 72, "compact": 58, "ultra": 40}


class TokenCard:
    """Builds and packs one compact token row into *parent*; returns the frame."""

    def __init__(
        self,
        parent,
        info: dict,
        selected: bool,
        fonts: dict,
        accent: str,
        accent_hover: str,
        show_badges: bool,
        height: int,
        status_dot: str,
        on_click=None,          # (event, token)  shift/ctrl handled by caller
        on_context=None,        # (event, token)
        on_properties=None,     # () on double-click
        on_middle=None,         # () on middle-click
        username_text="",
        name_chars=30,
    ):
        self._parent = parent
        self.info = info
        self.token = info.get("_token", "")
        self.selected = selected
        self.fonts = fonts
        self.accent = accent
        self.show_badges = show_badges
        self.height = height
        self.status_dot = status_dot
        self.on_click = on_click
        self.on_context = on_context
        self.on_properties = on_properties
        self.on_middle = on_middle
        self.username_text = username_text
        self.name_chars = name_chars
        self.frame = self._build()

    # -- rendering ----------------------------------------------------------------
    def _build(self):
        two_line = self.height >= 62
        accent_hover = accent_hover_hex(self.accent)
        card = ctk.CTkFrame(self._parent, fg_color=selected_bg(self.accent) if self.selected else CARD,
                            corner_radius=6, height=self.height)
        card.pack_propagate(False)
        card.pack(fill="x", pady=2)
        if self.selected:
            card.configure(border_width=2, border_color=blend(self.accent, "#FFFFFF", 0.15))

        inner = ctk.CTkFrame(card, fg_color="transparent")
        inner.pack(fill="both", padx=10, pady=2)

        ctk.CTkLabel(inner, text="●", text_color=self.status_dot,
                     font=ctk.CTkFont(size=12)).pack(side="left", padx=(0, 6))

        txt = ctk.CTkFrame(inner, fg_color="transparent")
        txt.pack(side="left", fill="x", expand=True)
        name_row = ctk.CTkFrame(txt, fg_color="transparent")
        name_row.pack(fill="x")
        ctk.CTkLabel(name_row, text=truncate(self.username_text, self.name_chars), font=self.fonts["normal"],
                    ).pack(side="left")

        if self.show_badges:
            for label, fg, bg in self._badges():
                ctk.CTkLabel(name_row, text=label, font=self.fonts["caption"],
                             text_color=fg, fg_color=bg, corner_radius=4, padx=4).pack(side="left", padx=3)

        servers_line = f"{len(self.info.get('servers', []))} Servers"
        if two_line:
            ctk.CTkLabel(txt, text=servers_line, font=self.fonts["caption"],
                         text_color=SEC, anchor="w").pack(anchor="w")
        else:
            ctk.CTkLabel(txt, text=servers_line, font=self.fonts["caption"],
                         text_color=SEC).pack(side="right")

        # event bindings
        bindings = [card, inner, txt, name_row]
        if self.on_click:
            for w in bindings:
                w.bind("<Button-1>", self.on_click)
        if self.on_context:
            for w in bindings:
                w.bind("<Button-3>", self.on_context)
        if self.on_properties:
            for w in bindings:
                w.bind("<Double-Button-1>", lambda e: self.on_properties())
        if self.on_middle:
            for w in bindings:
                w.bind("<Button-2>", lambda e: self.on_middle())

        return card

    def _badges(self):
        out = []
        if self.info.get("premium_type", 0) > 0:
            out.append(("⭐", "#B474F0", "#3A2E4A"))
        if self.info.get("phone"):
            out.append(("📱", "#7BD5FF", "#1E3A4A"))
        return out


def build_token_tooltip(info: dict, username: str) -> str:
    """Return the multi-line tooltip text for a token info dict."""
    from core.ids import created_from_id
    lines = [username]
    if info.get("premium_type", 0) > 0:
        lines.append("⭐ Nitro")
    if info.get("phone"):
        lines.append("📱 Phone Verified")
    if info.get("is_verified"):
        lines.append("✔ Verified (email)")
    lines.append(f"User ID: {info.get('user_id', '?')}")
    lines.append(f"Created: {created_from_id(info.get('user_id', '0'))}")
    lines.append(f"Servers: {len(info.get('servers', []))}")
    if info.get("email"):
        lines.append(f"Email: {info['email']}")
    if info.get("flags"):
        lines.append(f"Badges: {', '.join(info['flags'][:6])}")
    return "\n".join(lines)


__all__ = ["TokenCard", "build_token_tooltip", "CARD_HEIGHTS", "MOD_CTRL", "MOD_SHIFT"]