"""Stat card and a horizontal stat bar used at the top of the window."""

import customtkinter as ctk

from ui.theme import CARD, SEC, HOVER, GOOD


class StatCard:
    """A small card showing an icon, a numeric value, and a label."""

    def __init__(self, parent, icon, name, width=150, height=42, fonts=None):
        self.name = name
        card = ctk.CTkFrame(parent, width=width, height=height, corner_radius=8, fg_color=CARD)
        card.pack_propagate(False)
        self._frame = card
        row = ctk.CTkFrame(card, fg_color="transparent")
        row.pack(expand=True)
        ctk.CTkLabel(row, text=icon, font=fonts["normal"]).pack(side="left", padx=(10, 6))
        self.value_label = ctk.CTkLabel(row, text="0", font=fonts["title"])
        self.value_label.pack(side="left")
        ctk.CTkLabel(row, text=name, font=fonts["caption"], text_color=SEC).pack(side="left", padx=(6, 10))

    def set_value(self, text):
        self.value_label.configure(text=str(text))

    def pack(self, *args, **kwargs):
        self._frame.pack(*args, **kwargs)


class StatBar:
    """A horizontal row of StatCards plus a validation progress block."""

    def __init__(self, parent, fonts, accent):
        self._parent = parent
        self._specs = [("👤", "Total Tokens"), ("✅", "Valid"), ("🖥", "Servers"), ("🎯", "Selected")]
        self.cards = {}
        for icon, name in self._specs:
            card = StatCard(parent, icon, name, fonts=fonts)
            card.pack(side="left", padx=4, expand=True, fill="both")
            self.cards[name] = card

        prog = ctk.CTkFrame(parent, fg_color=CARD, corner_radius=8, height=42)
        prog.pack(side="left", padx=8, expand=True, fill="both")
        prog.pack_propagate(False)
        prow = ctk.CTkFrame(prog, fg_color="transparent")
        prow.pack(fill="x", expand=True, padx=12)
        ctk.CTkLabel(prow, text="Validation", font=fonts["caption"], text_color=SEC).pack(side="left")
        self.progress_label = ctk.CTkLabel(prow, text="0 / 0  0%", font=fonts["caption"], text_color=SEC)
        self.progress_label.pack(side="right")
        self.progress = ctk.CTkProgressBar(prog, height=6, corner_radius=3,
                                           fg_color=HOVER, progress_color=GOOD)
        self.progress.pack(fill="x", padx=12, pady=(0, 8))

    def set_stats(self, total, valid, servers, selected):
        self.cards["Total Tokens"].set_value(total)
        self.cards["Valid"].set_value(valid)
        self.cards["Servers"].set_value(servers)
        self.cards["Selected"].set_value(selected)
        pct = (valid / total * 100) if total else 0
        self.progress.set(pct / 100)
        self.progress_label.configure(text=f"{valid} / {total}  {pct:.0f}%")


__all__ = ["StatCard", "StatBar"]