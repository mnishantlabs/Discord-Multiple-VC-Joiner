"""About dialog."""

import customtkinter as ctk

from ui import theme


class AboutDialog(ctk.CTkToplevel):
    def __init__(self, parent, ctx) -> None:
        super().__init__(parent)
        self.title("About")
        self.geometry("460x300")
        self.configure(fg_color=theme.BG)

        ctk.CTkLabel(self, text="Discord Token Manager", font=ctx.fonts["title"]).pack(pady=(20, 4))
        ctk.CTkLabel(self, text="Validate tokens, manage servers, and connect to voice channels.",
                     font=ctx.fonts["normal"], text_color=theme.SEC).pack(pady=4)
        ctk.CTkLabel(self, text="All data is stored locally in your AppData folder.",
                     font=ctx.fonts["caption"], text_color=theme.MUTED).pack(pady=2)
        ctk.CTkLabel(self, text="Shortcuts: Ctrl+I import · Ctrl+V paste · Ctrl+R refresh ·\n"
                                "Ctrl+F search · Ctrl+A select all · Delete remove · Ctrl+C copy IDs\n"
                                "Double-click token = rejoin voice · Middle-click = copy ID",
                     font=ctx.fonts["caption"], text_color=theme.MUTED,
                     justify="center").pack(pady=12)
        ctk.CTkButton(self, text="OK", width=100, height=30, fg_color=ctx.accent,
                      hover_color=ctx.accent_hover, command=self.destroy).pack(pady=10)

        self.grab_set()
        self.transient(parent)


def show_about(parent, ctx) -> None:
    AboutDialog(parent, ctx)