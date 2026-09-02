"""Settings dialog backed by :class:`services.settings_service.SettingsService`.

Ported from the old ``App.open_settings`` (main.py) but writes through the
service so ``SETTINGS_CHANGED`` is emitted and the config stays consistent.
"""

import tkinter as tk
from tkinter import messagebox

import customtkinter as ctk

from ui import theme


class SettingsDialog(ctk.CTkToplevel):
    """Modal top-level with all configurable options."""

    def __init__(self, parent, ctx) -> None:
        super().__init__(parent)
        self.ctx = ctx
        settings = ctx.settings
        self.title("Settings")
        self.geometry("460x660")
        self.configure(fg_color=theme.BG)

        ctk.CTkLabel(self, text="SETTINGS", font=ctx.fonts["section"],
                     text_color=theme.SEC).pack(anchor="w", padx=14, pady=(14, 2))

        def field(label, var, tip=None):
            ctk.CTkLabel(self, text=label, font=ctx.fonts["caption"],
                         text_color=theme.SEC).pack(anchor="w", padx=14, pady=(8, 2))
            e = ctk.CTkEntry(self, textvariable=var, width=300, height=30,
                             fg_color=theme.CARD, border_width=0, font=ctx.fonts["normal"])
            e.pack(anchor="w", padx=14)
            if tip:
                from ui.widgets import Tooltip
                Tooltip(e, tip)

        self.accent_var = tk.StringVar(value=settings.accent)
        ctk.CTkLabel(self, text="Accent", font=ctx.fonts["caption"],
                     text_color=theme.SEC).pack(anchor="w", padx=14, pady=(8, 2))
        ctk.CTkOptionMenu(self, values=list(theme.ACCENTS.keys()), variable=self.accent_var,
                          width=160, height=28, fg_color=theme.CARD,
                          font=ctx.fonts["normal"]).pack(anchor="w", padx=14)

        self.conc_var = tk.StringVar(value=str(settings.concurrency))
        field("Concurrency (parallel workers)", self.conc_var)
        self.retry_var = tk.StringVar(value=str(settings.get("retry_delay", 3)))
        field("Retry Delay (seconds)", self.retry_var)
        self.timeout_var = tk.StringVar(value=str(settings.api_timeout))
        field("API Timeout (seconds)", self.timeout_var)
        self.delay_var = tk.StringVar(value=str(settings.delay))
        field("Action Delay (seconds)", self.delay_var)
        self.proxy_var = tk.StringVar(value=settings.proxy)
        field("Proxy (http://ip:port)", self.proxy_var)

        self.show_badges = tk.BooleanVar(value=settings.show_badges)
        self.show_ids = tk.BooleanVar(value=settings.show_ids)
        self.compact = tk.BooleanVar(value=settings.compact)
        for label, var in [("Show Badges", self.show_badges), ("Show IDs", self.show_ids),
                           ("Compact Token Cards", self.compact)]:
            ctk.CTkCheckBox(self, text=label, variable=var, font=ctx.fonts["normal"],
                            fg_color=theme.ACCENT, hover_color=theme.ACCENT_HOVER
                            ).pack(anchor="w", padx=14, pady=3)

        ctk.CTkButton(self, text="Save", command=self._save, height=36,
                      fg_color=ctx.accent, hover_color=ctx.accent_hover,
                      font=ctx.fonts["normal"]).pack(padx=14, pady=10, fill="x")

        self.grab_set()
        self.transient(parent)

    def _save(self) -> None:
        try:
            updates = {
                "accent": self.accent_var.get(),
                "concurrency": int(self.conc_var.get()),
                "retry_delay": int(self.retry_var.get()),
                "api_timeout": int(self.timeout_var.get()),
                "delay": float(self.delay_var.get()),
                "proxy": self.proxy_var.get(),
                "show_badges": self.show_badges.get(),
                "show_ids": self.show_ids.get(),
                "compact": self.compact.get(),
            }
        except ValueError:
            messagebox.showerror("Invalid", "Numbers must be numeric", parent=self)
            return
        self.ctx.settings.update(**updates)
        self.ctx.log.success("Settings saved")
        self.destroy()


def show_settings_dialog(parent, ctx) -> None:
    SettingsDialog(parent, ctx)