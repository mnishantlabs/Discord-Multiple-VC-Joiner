"""Top stat bar: four StatCards + a validation progress block."""

import customtkinter as ctk

from ui import theme
from ui.widgets import StatCard, StatBar
from core.predicates import status
from core.enums import TokenStatus


class StatsBarView:
    """Renders the four counters and validation progress from the store."""

    def __init__(self, parent, ctx) -> None:
        self.ctx = ctx
        self._holder = ctk.CTkFrame(parent, fg_color="transparent")
        self.bar = StatBar(self._holder, ctx.fonts, ctx.accent)

    def pack(self, *args, **kwargs) -> None:
        self._holder.pack(*args, **kwargs)

    def render(self) -> None:
        tokens = self.ctx.store.get_all()
        valid = sum(1 for _, info in tokens.items() if status(info) is TokenStatus.VALID)
        servers = {s["id"] for _, info in tokens.items() for s in info.get("servers", [])}
        self.bar.set_stats(
            total=len(tokens),
            valid=valid,
            servers=len(servers),
            selected=len(self.ctx.state.selected),
        )