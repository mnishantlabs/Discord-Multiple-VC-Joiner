"""Activity log view: subscribes to log events and appends without a full
re-render (fixing the old quadratic ``_render_logs``). Filters/search rebuild
only on demand."""

import tkinter as tk

import customtkinter as ctk

from core.constants import LOG_BUFFER_SIZE
from core.events import LOG_EVENT
from ui import theme
from ui.widgets import Tooltip
from utils import clipboard


class LogView:
    def __init__(self, parent, ctx) -> None:
        self.ctx = ctx
        self.log_filter = "all"
        self.log_search = tk.StringVar()
        self.log_search.trace_add("write", lambda *a: self._rebuild())

        panel = ctk.CTkFrame(parent, fg_color=theme.CARD, corner_radius=theme.RADIUS_PANEL)
        self._frame = panel
        head = ctk.CTkFrame(panel, fg_color="transparent")
        head.pack(fill="x", padx=theme.PAD_PANEL, pady=(8, 0))
        ctk.CTkLabel(head, text="📜  ACTIVITY", font=ctx.fonts["section"], text_color=theme.SEC).pack(side="left")

        ls = ctk.CTkEntry(head, textvariable=self.log_search, placeholder_text="🔍  Search logs…",
                          width=150, height=26, fg_color=theme.BG, border_width=0, font=ctx.fonts["caption"])
        ls.pack(side="left", padx=8)
        ctk.CTkButton(head, text="📋 Copy", height=22, width=52, font=ctx.fonts["caption"],
                      fg_color=theme.HOVER, hover_color=ctx.accent_hover, command=self._copy).pack(side="left", padx=2)
        ctk.CTkButton(head, text="💾 Save", height=22, width=52, font=ctx.fonts["caption"],
                      fg_color=theme.HOVER, hover_color=ctx.accent_hover, command=self._save).pack(side="left", padx=2)
        self.pause_btn = ctk.CTkButton(head, text="⏸", height=22, width=34, font=ctx.fonts["caption"],
                                       fg_color=theme.HOVER, hover_color=ctx.accent_hover, command=self._toggle_pause)
        self.pause_btn.pack(side="left", padx=2)
        self.collapse_btn = ctk.CTkButton(head, text="▾", height=22, width=24, font=ctx.fonts["caption"],
                                          fg_color=theme.HOVER, hover_color=ctx.accent_hover,
                                          command=self._toggle_collapse)
        self.collapse_btn.pack(side="left", padx=(2, 0))
        self.collapsed = False

        ft = ctk.CTkFrame(head, fg_color="transparent")
        ft.pack(side="right")
        for name, key in [("All", "all"), ("INFO", "info"), ("SUCCESS", "success"),
                          ("WARNING", "warn"), ("ERROR", "error"), ("NETWORK", "rate")]:
            ctk.CTkButton(ft, text=name, height=22, width=48, font=ctx.fonts["caption"],
                          fg_color=theme.HOVER, hover_color=ctx.accent_hover,
                          command=lambda k=key: self._set_filter(k)).pack(side="left", padx=2)

        self.text = ctk.CTkTextbox(panel, height=110, state="disabled", wrap="none",
                                   fg_color=theme.BG, text_color=theme.TXT, border_width=0,
                                   font=ctx.fonts["normal"])
        self.text.pack(fill="x", padx=theme.PAD_PANEL, pady=(6, 12))
        self.paused = False
        self._autoscroll = True

        ctx.bus.subscribe(LOG_EVENT, self._on_event)

    def pack(self, *args, **kwargs) -> None:
        self._frame.pack(*args, **kwargs)

    def _toggle_collapse(self) -> None:
        self.collapsed = not self.collapsed
        if self.collapsed:
            self.text.pack_forget()
            self.collapse_btn.configure(text="▸")
        else:
            self.text.pack(fill="x", padx=theme.PAD_PANEL, pady=(6, 12))
            self.collapse_btn.configure(text="▾")

    # ---- event handling ----------------------------------------------------------
    def _on_event(self, record) -> None:
        if self.paused:
            return
        if self.log_filter != "all" and record.level != self.log_filter:
            return
        self._append(record)

    def _append(self, record) -> None:
        self.text.configure(state="normal")
        icon = theme.LOG_ICON.get(record.level, "🔵")
        self.text.insert("end", f"{record.timestamp}  ", ("ts",))
        self.text.insert("end", f"{icon} {record.message}\n", (record.level,))
        self.text.configure(state="disabled")
        if self._autoscroll:
            self.text.see("end")

    def _rebuild(self) -> None:
        self.text.configure(state="normal")
        self.text.delete("1.0", "end")
        q = self.log_search.get().lower().strip()
        for record in self.ctx.log.iter_all():
            if self.log_filter != "all" and record.level != self.log_filter:
                continue
            if q and q not in record.message.lower():
                continue
            self._append(record)
        self.text.configure(state="disabled")

    def _set_filter(self, key) -> None:
        self.log_filter = key
        self._rebuild()

    def _toggle_pause(self) -> None:
        self.paused = not self.paused
        self.pause_btn.configure(text="▶" if self.paused else "⏸")

    def _copy(self) -> None:
        lines = [f"{r.timestamp} {r.message}" for r in self._visible()]
        if lines:
            clipboard.clip_set(self.text, "\n".join(lines))

    def _save(self) -> None:
        from tkinter import filedialog
        path = filedialog.asksaveasfilename(parent=self.text, defaultextension=".txt",
                                            filetypes=[("Text", "*.txt")])
        if not path:
            return
        with open(path, "w", encoding="utf-8") as f:
            for r in self._visible():
                f.write(f"[{theme.LOG_CAT.get(r.level, 'INFO')}] {r.timestamp} {r.message}\n")
        self.ctx.log.info(f"Logs saved to {path}")

    def _visible(self):
        q = self.log_search.get().lower().strip()
        out = []
        for r in self.ctx.log.iter_all():
            if self.log_filter != "all" and r.level != self.log_filter:
                continue
            if q and q not in r.message.lower():
                continue
            out.append(r)
        return out