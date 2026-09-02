"""Top toolbar: title, everyday quick actions (Import / Validate / Refresh /
Remove), and on the right a View menu (view-only toggles), Settings, About
and the status label."""

import tkinter as tk

import customtkinter as ctk

from ui import theme
from ui.widgets import IconButton


class ToolbarView:
    def __init__(self, parent, ctx) -> None:
        self.ctx = ctx
        self.parent = parent
        bar = ctk.CTkFrame(parent, fg_color="transparent")
        self._frame = bar
        inner = ctk.CTkFrame(bar, fg_color="transparent")
        inner.pack(fill="x")

        ctk.CTkLabel(inner, text="Discord Token Manager",
                     font=ctx.fonts["title"]).pack(side="left", padx=(0, 16))

        for text, cmd, tip in [
            ("➕  Import", self.open_import, "Import tokens (Ctrl+I)"),
            ("✔  Validate", self.validate_all, "Validate every account"),
            ("🔄  Refresh", self.refresh, "Refresh (Ctrl+R)"),
            ("🗑  Remove", self.remove_selected, "Delete selected accounts"),
        ]:
            btn = ctk.CTkButton(inner, text=text, height=28, font=ctx.fonts["caption"],
                                fg_color=theme.CARD, hover_color=ctx.accent_hover,
                                corner_radius=theme.RADIUS_CTRL, command=cmd)
            btn.pack(side="left", padx=3)
            from ui.widgets import Tooltip
            Tooltip(btn, tip)

        self.status_label = ctk.CTkLabel(inner, text="Ready", font=ctx.fonts["caption"],
                                         text_color=theme.SEC)
        self.status_label.pack(side="right", padx=4)

        ctk.CTkButton(inner, text="⚙  Settings", height=28, font=ctx.fonts["caption"],
                      fg_color=theme.CARD, hover_color=ctx.accent_hover,
                      corner_radius=theme.RADIUS_CTRL, command=self.open_settings).pack(side="right", padx=3)

        self.view_btn = ctk.CTkButton(inner, text="View ▾", height=28, font=ctx.fonts["caption"],
                                      fg_color=theme.CARD, hover_color=ctx.accent_hover,
                                      corner_radius=theme.RADIUS_CTRL, command=self._view_menu)
        self.view_btn.pack(side="right", padx=3)

        IconButton(inner, "ℹ", "About", self.open_about, ctx.accent_hover,
                   font=ctx.fonts["normal"]).pack(side="right", padx=3)

    def pack(self, *args, **kwargs) -> None:
        self._frame.pack(*args, **kwargs)

    # ---- quick actions -----------------------------------------------------------
    def validate_all(self) -> None:
        win = self.parent
        if hasattr(win, "tokens_view"):
            win.tokens_view.validate_all()
        else:
            self.ctx.log.warning("Token view not ready")

    def remove_selected(self) -> None:
        parent = self.parent
        if hasattr(parent, "delete_selected"):
            parent.delete_selected()
        else:
            self.ctx.log.warning("Window not ready")

    def refresh(self) -> None:
        # Refresh is handled by the window; call the method through the parent.
        self.parent.refresh_all()

    # ---- view menu (view-only toggles, not app settings) ------------------------
    def _view_menu(self) -> None:
        menu = tk.Menu(self._frame, tearoff=0)

        def add_toggle(label, key, default=True):
            var = tk.BooleanVar(value=bool(self.ctx.settings.get(key, default)))
            menu.add_checkbutton(
                label=label, variable=var,
                command=lambda: self._toggle_view(key, var.get()))

        add_toggle("Compact Cards", "compact", True)
        add_toggle("Show IDs", "show_ids", True)
        add_toggle("Show Badges", "show_badges", True)
        menu.add_separator()
        menu.add_command(label="Toggle Command Palette…", command=lambda: self._palette())
        try:
            menu.tk_popup(self._frame.winfo_rootx() + 8, self._frame.winfo_rooty() + 44)
        finally:
            menu.grab_release()

    def _toggle_view(self, key: str, value) -> None:
        self.ctx.settings.set(key, value)
        self.parent.refresh_all()

    def _palette(self) -> None:
        if hasattr(self.parent, "open_command_palette"):
            self.parent.open_command_palette()

    # ---- dialogs (delegated to dialogs defined elsewhere) -----------------------
    def open_import(self) -> None:
        from ui.dialogs.import_dialog import show_import_dialog
        show_import_dialog(self.parent, self.ctx)

    def open_paste(self) -> None:
        from ui.dialogs.import_dialog import show_paste_dialog
        show_paste_dialog(self.parent, self.ctx)

    def open_settings(self) -> None:
        from ui.dialogs.settings_dialog import show_settings_dialog
        show_settings_dialog(self.parent, self.ctx)

    def open_about(self) -> None:
        from ui.dialogs.about import show_about
        show_about(self.parent, self.ctx)