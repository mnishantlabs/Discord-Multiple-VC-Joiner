"""Ctrl+Shift+P command palette: a fuzzy-filtered list of the most useful
actions, driven purely by the keyboard."""

import tkinter as tk

import customtkinter as ctk

from ui import theme

PALETTE_WIDTH = 440
MAX_ROWS = 10


class CommandPalette(ctk.CTkToplevel):
    def __init__(self, root) -> None:
        super().__init__(root, fg_color=theme.BG)
        self._root = root
        self._commands: list[tuple[str, object]] = self._build_commands()
        self._buttons: list[ctk.CTkButton] = []
        self._active = 0

        self.withdraw()
        self.title("Command Palette")
        self.overrideredirect(True)
        self.attributes("-topmost", True)

        self.entry_var = tk.StringVar()
        self.entry_var.trace_add("write", lambda *a: self._filter())
        self.entry = ctk.CTkEntry(self, textvariable=self.entry_var,
                                  placeholder_text="Type a command…", height=34,
                                  fg_color=theme.CARD, border_width=1,
                                  border_color=theme.HOVER, corner_radius=theme.RADIUS_CTRL)
        self.entry.pack(fill="x", padx=10, pady=(10, 6))

        self.listbox = ctk.CTkFrame(self, fg_color=theme.CARD, corner_radius=theme.RADIUS_PANEL)
        self.listbox.pack(fill="both", expand=True, padx=10, pady=(0, 10))

        hint = ctk.CTkLabel(self, text="↑↓ navigate   ·   Enter run   ·   Esc close",
                            font=self._root.ctx.fonts["caption"], text_color=theme.MUTED)
        hint.pack(pady=(0, 8))

        self.bind("<Escape>", lambda _e: self.destroy())
        self.bind("<Up>", lambda _e: self._move(-1))
        self.bind("<Down>", lambda _e: self._move(1))
        self.entry.bind("<Return>", lambda _e: self._run_active())
        self.entry.bind("<Up>", lambda _e: self._move(-1))
        self.entry.bind("<Down>", lambda _e: self._move(1))

    def _build_commands(self) -> list[tuple[str, object]]:
        tok = self._root.tokens_view
        commands = [
            ("Import tokens", self._root.toolbar.open_import),
            ("Paste tokens", self._root.toolbar.open_paste),
            ("Validate all", tok.validate_all),
            ("Refresh", self._root.refresh_all),
            ("Remove selected", self._root.delete_selected),
            ("Settings", self._root.toolbar.open_settings),
            ("About", self._root.toolbar.open_about),
            ("Properties…", lambda: tok._open_properties(next(iter(self._root.ctx.state.selected)))
             if self._root.ctx.state.selected else None),
            ("Focus search", lambda: (tok.search_entry.focus_set(),
                                      tok.search_entry.select_range(0, "end"))),
        ]
        for key in ("all", "valid", "invalid"):
            commands.append((f"Filter: {key.capitalize()}", lambda k=key: tok._set_view_filter(k)))
        commands.append(("Toggle compact cards",
                         lambda: self._toggle_setting("compact", tok)))
        commands.append(("Toggle show IDs",
                         lambda: self._toggle_setting("show_ids", tok)))
        commands.append(("Toggle show badges",
                         lambda: self._toggle_setting("show_badges", tok)))
        return commands

    def _toggle_setting(self, key: str, tok) -> None:
        self._root.ctx.settings.set(key, not self._root.ctx.settings.get(key, True))
        self._root.refresh_all()
        self._root.ctx.log.info(f"{key.replace('_', ' ')}: "
                                f"{'on' if self._root.ctx.settings.get(key, True) else 'off'}")

    def show(self) -> None:
        self._center_over_parent()
        self.deiconify()
        self._filter()
        self.entry.focus_set()

    def _center_over_parent(self) -> None:
        self.update_idletasks()
        pw, ph = self._root.winfo_width(), self._root.winfo_height()
        px, py = self._root.winfo_rootx(), self._root.winfo_rooty()
        w = _palette_geometry(self)
        x = px + (pw - w[0]) // 2
        y = py + (ph - w[1]) // 3
        self.geometry(f"{w[0]}x{w[1]}+{x}+{y}")

    def _filter(self) -> None:
        for b in self._buttons:
            b.destroy()
        self._buttons.clear()
        query = self.entry_var.get().lower().strip()
        scores = []
        for label, action in self._commands:
            text = label.lower()
            if query:
                if query in text:
                    scores.append((0, label, action))
                else:
                    score = self._fuzzy(text, query)
                    if score is not None:
                        scores.append((score, label, action))
            else:
                scores.append((0, label, action))
        scores.sort(key=lambda t: (t[0], t[1]))
        shown = scores[:MAX_ROWS]
        for score, label, action in shown:
            btn = ctk.CTkButton(self.listbox, text=label, anchor="w", height=28,
                                font=self._root.ctx.fonts["normal"],
                                fg_color="transparent", hover_color=theme.HOVER,
                                corner_radius=4,
                                command=lambda a=action: a())
            btn.pack(fill="x", padx=2, pady=1)
            self._buttons.append(btn)
        self._active = 0
        self._highlight()

    def _fuzzy(self, text: str, query: str) -> int | None:
        """Cheap subsequence score: -1 per skipped char, None if not a subsequence."""
        i = 0
        cost = 0
        for ch in query:
            j = text.find(ch, i)
            if j < 0:
                return None
            cost += j - i
            i = j + 1
        return cost

    def _highlight(self) -> None:
        for idx, btn in enumerate(self._buttons):
            btn.configure(fg_color=self._root.ctx.accent if idx == self._active
                          else "transparent")

    def _move(self, delta: int) -> None:
        if not self._buttons:
            return
        self._active = (self._active + delta) % len(self._buttons)
        self._highlight()

    def _run_active(self) -> None:
        if self._buttons:
            self._buttons[self._active].invoke()


def _palette_geometry(palette: CommandPalette) -> tuple[int, int]:
    """The palette window is withdrawn, so update_idletasks gives 1x1.
    Compute a sane width and a height from the current result list."""
    h = 60 + len(palette._buttons) * 30
    return PALETTE_WIDTH, min(h, 60 + MAX_ROWS * 30)