"""Bottom action bar: server/channel/server-id/user-id target display, per-token
voice control buttons, and the master Join button."""

import tkinter as tk

import customtkinter as ctk

from ui import theme
from ui.text import truncate


class ActionsBarView:
    def __init__(self, parent, ctx) -> None:
        self.ctx = ctx
        root = ctk.CTkFrame(parent, fg_color=theme.CARD, corner_radius=theme.RADIUS_PANEL)
        self._frame = root

        row = ctk.CTkFrame(root, fg_color="transparent")
        row.pack(fill="x", padx=theme.PAD_PANEL, pady=10)
        row.grid_columnconfigure(0, weight=1)

        self.target_label = ctk.CTkLabel(row, text="No target", font=ctx.fonts["normal"],
                                         text_color=theme.MUTED, anchor="w")
        self.target_label.grid(row=0, column=0, sticky="w", padx=(0, 8))

        self.disconnect_btn = ctk.CTkButton(row, text="Disconnect", width=90, height=30,
                                            font=ctx.fonts["caption"], fg_color=theme.HOVER,
                                            hover_color=ctx.accent_hover, command=self.disconnect)
        self.disconnect_btn.grid(row=0, column=1, padx=(0, 6))

        self.join_btn = ctk.CTkButton(row, text="JOIN", width=72, height=30,
                                      font=ctx.fonts["section"], fg_color=ctx.accent,
                                      hover_color=ctx.accent_hover, command=self.join)
        self.join_btn.grid(row=0, column=2)

    def pack(self, *args, **kwargs) -> None:
        self._frame.pack(*args, **kwargs)

    def render(self) -> None:
        s = self.ctx.state
        if s.selected_channel and s.selected_server:
            text = f"Targeted: ▶ {truncate(s.selected_channel['name'], 24)}  •  {truncate(s.selected_server['name'], 20)}"
            color = theme.TXT
        elif len(s.selected) == 1:
            token = next(iter(s.selected))
            text = f"Selected: {truncate(self.ctx.username(self.ctx.store.get(token)), 32)}"
            color = self.ctx.accent
        elif s.selected:
            text = f"Selected: {len(s.selected)} accounts"
            color = self.ctx.accent
        else:
            text = "Ready"
            color = theme.MUTED
        self.target_label.configure(text=text, text_color=color)

    def join(self) -> None:
        self.ctx.actions.join_selected()

    def disconnect(self) -> None:
        self.ctx.actions.disconnect_all()