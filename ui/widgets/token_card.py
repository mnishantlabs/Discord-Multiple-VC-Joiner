"""A single token card component.

Ports the old ``App._render_token_card`` (main.py:738) faithfully: status
dot, username + badges, server count, snippet ID, a checkbox, and the four
event bindings (click / right-click / double-click / middle-click). The card
renders from an opaque ``info`` dict so the component stays domain-agnostic
and the actual commands are injected by the caller.
"""

import tkinter as tk

import customtkinter as ctk

from ui.theme import CARD, ACCENT, ACCENT_HOVER, DOT_VALID, DOT_INVALID, DOT_LOCKED, TXT, SEC, MUTED
from ui.widgets.tooltip import Tooltip
from utils.platform import MOD_CTRL, MOD_SHIFT


class TokenCard:
    """Builds and packs one token row into *parent*; returns the frame."""

    def __init__(
        self,
        parent,
        info: dict,
        selected: bool,
        fonts: dict,
        accent: str,
        accent_hover: str,
        show_badges: bool,
        show_ids: bool,
        compact: bool,
        status_dot: str,
        on_click=None,          # (event, token)  shift/ctrl handled by caller
        on_context=None,        # (event, token)
        on_rejoin=None,         # () on double-click
        on_middle=None,         # () on middle-click
        on_toggle=None,         # () checkbox
        username_text="",
    ):
        self._parent = parent
        self.info = info
        self.token = info.get("_token", "")
        self.selected = selected
        self.fonts = fonts
        self.show_badges = show_badges
        self.show_ids = show_ids
        self.compact = compact
        self.accent = accent
        self.accent_hover = accent_hover
        self.status_dot = status_dot
        self.on_click = on_click
        self.on_context = on_context
        self.on_rejoin = on_rejoin
        self.on_middle = on_middle
        self.on_toggle = on_toggle
        self.username_text = username_text
        self.frame = self._build()

    # -- rendering ----------------------------------------------------------------
    def _build(self):
        height = 50 if self.compact else 130
        card = ctk.CTkFrame(self._parent, fg_color=CARD, corner_radius=8, height=height)
        card.pack_propagate(False)
        card.pack(fill="x", pady=3)
        card.configure(border_width=2 if self.selected else 0,
                       border_color=self.accent if self.selected else "transparent")

        inner = ctk.CTkFrame(card, fg_color="transparent")
        inner.pack(fill="both", padx=10, pady=6)

        ctk.CTkLabel(inner, text="●", text_color=self.status_dot,
                     font=ctk.CTkFont(size=13)).pack(side="left", padx=(0, 8))

        txt = ctk.CTkFrame(inner, fg_color="transparent")
        txt.pack(side="left", fill="x", expand=True)
        name_row = ctk.CTkFrame(txt, fg_color="transparent")
        name_row.pack(fill="x")
        ctk.CTkLabel(name_row, text=self.username_text, font=self.fonts["normal"]).pack(side="left")

        if self.show_badges:
            for label, fg, bg in self._badges():
                ctk.CTkLabel(name_row, text=label, font=self.fonts["caption"],
                             text_color=fg, fg_color=bg, corner_radius=4, padx=4).pack(side="left", padx=3)

        ctk.CTkLabel(txt, text=f"{len(self.info.get('servers', []))} Servers",
                     font=self.fonts["caption"], text_color=SEC, anchor="w").pack(anchor="w")
        if self.show_ids:
            uid = self.info.get("user_id", "?")
            ctk.CTkLabel(txt, text=f"ID {str(uid)[:14]}...", font=self.fonts["caption"],
                         text_color=MUTED, anchor="w").pack(anchor="w")

        cb = ctk.CTkCheckBox(inner, text="", width=8,
                             variable=tk.BooleanVar(value=self.selected),
                             command=self.on_toggle, checkbox_width=18, checkbox_height=18,
                             fg_color=ACCENT, hover_color=ACCENT_HOVER)
        cb.pack(side="right", padx=2)

        # event bindings
        if self.on_click:
            for w in (card, inner, txt, name_row):
                w.bind("<Button-1>", self.on_click)
        if self.on_context:
            for w in (card, inner, txt, name_row):
                w.bind("<Button-3>", self.on_context)
        if self.on_rejoin:
            for w in (card, inner, txt, name_row):
                w.bind("<Double-Button-1>", lambda e: self.on_rejoin())
        if self.on_middle:
            for w in (card, inner, txt, name_row):
                w.bind("<Button-2>", lambda e: self.on_middle())

        return card

    def _badges(self):
        out = []
        if self.info.get("premium_type", 0) > 0:
            out.append(("Nitro", "#B474F0", "#3A2E4A"))
        if self.info.get("is_verified"):
            out.append(("✔", "#7BD5FF", "#1E3A4A"))
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


__all__ = ["TokenCard", "build_token_tooltip", "MOD_CTRL", "MOD_SHIFT"]