"""Top toolbar: title, icon buttons (import/paste/file/export/refresh/settings/about),
and a status label on the right."""

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

        self._add_icons(inner)

        self.status_label = ctk.CTkLabel(inner, text="Ready", font=ctx.fonts["caption"],
                                         text_color=theme.SEC)
        self.status_label.pack(side="right", padx=4)

    def _add_icons(self, inner) -> None:
        click = {
            "import": lambda: self.open_import(),
            "paste": lambda: self.open_paste(),
            "file": self.import_file,
            "export": self.export,
            "refresh": self.refresh,
            "settings": self.open_settings,
            "about": self.open_about,
        }
        icons = [
            ("📥", "Import tokens (Ctrl+I)", "import"),
            ("📋", "Paste tokens (Ctrl+V)", "paste"),
            ("📂", "Import from file", "file"),
            ("💾", "Export tokens", "export"),
            ("🔄", "Refresh (Ctrl+R)", "refresh"),
            ("⚙", "Settings", "settings"),
            ("ℹ", "About", "about"),
        ]
        for icon, tip, key in icons:
            btn = IconButton(
                inner, icon, tip, click[key],
                self.ctx.accent_hover, font=self.ctx.fonts["normal"],
            )
            btn.pack(side="left", padx=3)

    # ---- commands (delegated to dialogs defined elsewhere) -----------------------
    def open_import(self) -> None:
        from ui.dialogs.import_dialog import show_import_dialog
        show_import_dialog(self.parent, self.ctx)

    def open_paste(self) -> None:
        from ui.dialogs.import_dialog import show_paste_dialog
        show_paste_dialog(self.parent, self.ctx)

    def import_file(self) -> None:
        from ui.dialogs.import_dialog import show_file_import
        show_file_import(self.parent, self.ctx)

    def export(self) -> None:
        from ui.dialogs.export_dialog import show_export_dialog
        show_export_dialog(self.parent, self.ctx)

    def refresh(self) -> None:
        # Refresh is handled by the window; call the method through the context.
        self.parent.refresh_all()

    def open_settings(self) -> None:
        from ui.dialogs.settings_dialog import show_settings_dialog
        show_settings_dialog(self.parent, self.ctx)

    def open_about(self) -> None:
        from ui.dialogs.about import show_about
        show_about(self.parent, self.ctx)

    def pack(self, *args, **kwargs) -> None:
        self._frame.pack(*args, **kwargs)