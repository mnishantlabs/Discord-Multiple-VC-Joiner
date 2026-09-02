"""Top bar: three compact stat pills (Accounts / Servers / Selected) plus a
status label. The validation progress bar is only shown while a validation
run is active, never parked on a static 100%."""

import customtkinter as ctk

from ui import theme
from core.predicates import status
from core.enums import TokenStatus


class StatsBarView:
    """Renders the counters as small pills and a transient validation row."""

    def __init__(self, parent, ctx) -> None:
        self.ctx = ctx
        self._holder = ctk.CTkFrame(parent, fg_color="transparent")
        self._pills: dict[str, ctk.CTkLabel] = {}

        for icon, name in [("👤", "Accounts"), ("🖥", "Servers"), ("🎯", "Selected")]:
            pill = ctk.CTkFrame(self._holder, fg_color=theme.CARD, corner_radius=theme.RADIUS_PANEL)
            pill.pack(side="left", padx=(0, 6), pady=2)
            ctk.CTkLabel(pill, text=icon, font=ctx.fonts["caption"]).pack(side="left", padx=(8, 4))
            lbl = ctk.CTkLabel(pill, text="0", font=ctx.fonts["normal"], text_color=theme.TXT)
            lbl.pack(side="left")
            ctk.CTkLabel(pill, text=name, font=ctx.fonts["caption"],
                         text_color=theme.SEC).pack(side="left", padx=(4, 8))
            self._pills[name] = lbl

        self.status_label = ctk.CTkLabel(self._holder, text="Ready", font=ctx.fonts["caption"],
                                         text_color=theme.MUTED)
        self.status_label.pack(side="right", padx=(6, 2), pady=2)

        self._progress_row = ctk.CTkFrame(self._holder, fg_color=theme.CARD, corner_radius=theme.RADIUS_PANEL)
        self._progress_label = ctk.CTkLabel(self._progress_row, text="0 / 0  0%", font=ctx.fonts["caption"],
                                            text_color=theme.SEC)
        self._progress_label.pack(side="right", padx=8, pady=4)
        self.progress = ctk.CTkProgressBar(self._progress_row, width=140, height=6, corner_radius=3,
                                           fg_color=theme.HOVER, progress_color=theme.GOOD)
        self.progress.pack(side="right", pady=(0, 0))
        self.progress.set(0)
        self._validating = False

    def pack(self, *args, **kwargs) -> None:
        self._holder.pack(*args, **kwargs)

    def set_validating(self, on: bool) -> None:
        if on == self._validating:
            return
        self._validating = on
        if on:
            self.progress.set(0)
            self._progress_label.configure(text="0 / 0  0%")
            self._progress_row.pack(side="right", padx=(0, 6), pady=2)
        else:
            self._progress_row.pack_forget()
        self.status_label.configure(text="Validating…" if on else "Ready")

    def render(self) -> None:
        tokens = self.ctx.store.get_all()
        valid = sum(1 for _, info in tokens.items() if status(info) is TokenStatus.VALID)
        servers = {s["id"] for _, info in tokens.items() for s in info.get("servers", [])}
        self._pills["Accounts"].configure(text=str(len(tokens)))
        self._pills["Servers"].configure(text=str(len(servers)))
        self._pills["Selected"].configure(text=str(len(self.ctx.state.selected)))
        if not self._validating:
            self.status_label.configure(text="Ready")