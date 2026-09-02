"""Beta-specific view variants.

These subclass the shipped views and only override the parts the experimental
Material redesign changes — no shipped UI source is modified. When launched with
``--beta``, :func:`ui.beta.apply_beta` swaps these in for the standard views; the
default run keeps the originals.

Keeping the deltas small inside subclasses also makes them trivial to port into
``ui/views`` if the beta design is adopted in a future release.
"""

from ui.views.servers_view import ServersView

__all__ = ["BetaServersView"]


class BetaServersView(ServersView):
    """Server list with the members sub-panel removed so the server list uses the
    full column height (selected-server info stays pinned at the bottom)."""

    def __init__(self, parent, ctx) -> None:
        super().__init__(parent, ctx)
        # Collapse the members panel: hide its toggle, sash, and list so the
        # server list + info label fill the whole server column.
        for w in (self.members_toggle, self.members_sash, self.server_members):
            try:
                w.grid_forget()
            except Exception:
                pass
        try:
            body = self.server_list.master
            body.grid_rowconfigure(2, weight=0, minsize=0)   # no sash row
            body.grid_rowconfigure(1, weight=3)              # server list expands
            self.server_list.grid(row=1, column=0, rowspan=5, sticky="nsew")
        except Exception:
            pass

    # ---- members panel: disabled in beta -------------------------------------
    def _render_members(self, _data) -> None:
        pass

    def _apply_members_layout(self) -> None:
        pass

    def toggle_members(self) -> None:
        pass

    def _members_press(self, _event) -> None:
        pass

    def _members_drag(self, _event) -> None:
        pass

    def _members_release(self, _event=None) -> None:
        pass

    def _members_reset(self, _event=None) -> None:
        pass

    def _adjust_members_height(self, _delta) -> None:
        pass

    def _cap_members_height(self) -> None:
        pass

    def _persist_members_height(self) -> None:
        pass
