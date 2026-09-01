"""Hover tooltip (moved from the old ``Tooltip`` class, kept API-compatible)."""

import tkinter as tk

TIP_BG = "#111214"
TIP_FG = "#e6e6e6"


class Tooltip:
    """Shows a small popup near a widget on hover."""

    def __init__(self, widget, text):
        self.widget = widget
        self.text = text
        self.tip = None
        widget.bind("<Enter>", self.show)
        widget.bind("<Leave>", self.hide)

    def show(self, event=None):
        if not self.text or self.tip:
            return
        x = self.widget.winfo_rootx() + 16
        y = self.widget.winfo_rooty() + self.widget.winfo_height() + 6
        self.tip = tk.Toplevel(self.widget)
        self.tip.wm_overrideredirect(True)
        self.tip.wm_geometry(f"+{x}+{y}")
        self.tip.attributes("-topmost", True)
        tip = tk.Label(self.tip, text=self.text, background=TIP_BG, fg=TIP_FG,
                       font=("Segoe UI", 10), padx=8, pady=4, justify="left")
        tip.pack()

    def hide(self, event=None):
        if self.tip:
            self.tip.destroy()
            self.tip = None