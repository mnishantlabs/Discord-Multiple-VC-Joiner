"""A virtualized vertical list rendering only the visible slice of items.

Replaces the old ``CTkScrollableFrame`` token canvas that destroyed and
recreated every card model on each render (freezing at a few hundred tokens).
This Canvas-based list computes the visible window from the scroll position
and only instantiates a small set of row widgets, recycling them as you
scroll, so thousands of tokens render smoothly.
"""

import tkinter as tk

from ui.theme import BG

# row-height budget; overlapped rows beyond this are acceptable since only the
# visible window is instantiated.
OVERSCAN = 2


class VirtualList:
    """A scrollable virtualized list of identically-sized rows.

    ``render_row(item, parent, index)`` must return a widget that has already
    been ``pack``ed into *parent* by the caller (the widget's lifecycle is the
    caller's responsibility; this class only tracks and recycles row slots).
    """

    def __init__(self, parent, row_height, fg_color=BG, on_select=None):
        self.row_height = row_height
        self.on_select = on_select
        self.items: list = []
        self.render_row = None
        self._widgets: dict[int, tk.Widget] = {}

        self._frame = tk.Frame(parent, bg=fg_color)
        self.canvas = tk.Canvas(self._frame, bg=fg_color, highlightthickness=0)
        self.vsb = tk.Scrollbar(self._frame, orient="vertical", command=self.canvas.yview)
        self.canvas.configure(yscrollcommand=self.vsb.set)
        self.canvas.pack(side="left", fill="both", expand=True)
        self.vsb.pack(side="right", fill="y")

        self.canvas.bind("<Configure>", self._on_resize)
        self.canvas.bind("<MouseWheel>", self._on_wheel)

    def pack(self, *args, **kwargs):
        self._frame.pack(*args, **kwargs)

    def grid(self, *args, **kwargs):
        self._frame.grid(*args, **kwargs)

    def forget(self):
        self._frame.pack_forget()

    # -- sizing --------------------------------------------------------------------
    def _total_height(self):
        return len(self.items) * self.row_height

    def _first_visible(self):
        first = int(self.canvas.yview()[0] * max(self._total_height(), 1))
        return max(0, first // self.row_height - OVERSCAN)

    def _last_visible(self):
        view_height = max(self._frame.winfo_height(), 100)
        first = self._first_visible()
        visible_rows = view_height // max(self.row_height, 1)
        return first + visible_rows + OVERSCAN * 2

    def _on_resize(self, _event):
        self._update_scrollregion()
        self._refresh()

    def _on_wheel(self, event):
        self.canvas.yview_scroll(-1 * (event.delta // 120), "units")

    def _update_scrollregion(self):
        self.canvas.configure(scrollregion=(0, 0, 0, max(self._total_height(), 1)))

    # -- data ---------------------------------------------------------------
    def set_renderer(self, renderer):
        """``renderer(item) -> tk.Widget`` returning a pre-packed row."""
        self.render_row = renderer

    def set_items(self, items):
        self.items = items
        self._clear_all()
        self._update_scrollregion()
        self._refresh()

    def _clear_all(self):
        for w in self._widgets.values():
            try:
                w.destroy()
            except Exception:
                pass
        self._widgets.clear()
        try:
            self.canvas.delete("all")
        except Exception:
            pass

    def _refresh(self):
        if self.render_row is None:
            return
        first, last = self._first_visible(), self._last_visible()
        # drop out-of-window rows
        for idx in [k for k in self._widgets if k < first or k > last]:
            try:
                self._widgets.pop(idx).destroy()
            except Exception:
                pass
        # create missing rows in range
        for idx in range(first, last + 1):
            if idx < 0 or idx >= len(self.items):
                continue
            if idx in self._widgets:
                continue
            item = self.items[idx]
            widget = self.render_row(item)
            self.canvas.create_window(
                0,
                idx * self.row_height,
                anchor="nw",
                width=self.canvas.winfo_width() if self.canvas.winfo_width() > 1 else 9999,
                window=widget,
            )
            self._widgets[idx] = widget


__all__ = ["VirtualList"]