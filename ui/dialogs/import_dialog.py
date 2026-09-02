"""Import token dialogs: paste box / file picker, then resolve via the
ImportExportService (which validates new tokens and persists them)."""

import tkinter as tk
from tkinter import filedialog, messagebox

import customtkinter as ctk

from ui import theme


class ImportDialog(ctk.CTkToplevel):
    """Modal top-level with a paste box and Import / Cancel buttons."""

    def __init__(self, parent, ctx, title="Import Tokens") -> None:
        super().__init__(parent)
        self.ctx = ctx
        self.result = None
        self.title(title)
        self.geometry("560x380")
        self.configure(fg_color=theme.BG)

        ctk.CTkLabel(self, text="Paste tokens (one per line):",
                     font=ctx.fonts["normal"], text_color=theme.SEC).pack(anchor="w", padx=14, pady=(12, 6))

        self.textbox = ctk.CTkTextbox(self, fg_color=theme.CARD, text_color=theme.TXT,
                                      border_width=0, corner_radius=8, font=ctx.fonts["normal"])
        self.textbox.pack(fill="both", expand=True, padx=14)

        btnrow = ctk.CTkFrame(self, fg_color="transparent")
        btnrow.pack(fill="x", padx=14, pady=10)
        ctk.CTkButton(btnrow, text="Import", width=100, height=30, fg_color=ctx.accent,
                      hover_color=ctx.accent_hover, command=self._import).pack(side="right", padx=3)
        ctk.CTkButton(btnrow, text="Cancel", width=90, height=30, fg_color=theme.HOVER,
                      hover_color=theme.HOVER, command=self.destroy).pack(side="right", padx=3)

        self.grab_set()
        self.transient(parent)

    def _import(self) -> None:
        raw = self.textbox.get("1.0", "end").splitlines()
        if not any(r.strip() for r in raw):
            messagebox.showwarning("Import", "Nothing to import.", parent=self)
            return
        self._run(raw)

    def _run(self, raw) -> None:
        def on_done(added: int) -> None:
            self.result = added
            self.ctx.log.success(f"Imported {added} new token(s)")
            self.after(0, self._refresh_and_close)

        def on_progress(cur: int, total: int) -> None:
            pass

        self.ctx.import_export.resolve_import(raw, on_progress, on_done)

    def _refresh_and_close(self) -> None:
        win = self.master
        if hasattr(win, "refresh_all"):
            win.refresh_all()
        self.destroy()


def show_import_dialog(parent, ctx) -> None:
    ImportDialog(parent, ctx, "Import Tokens")


def show_paste_dialog(parent, ctx) -> None:
    ImportDialog(parent, ctx, "Paste Tokens")


def show_file_import(parent, ctx) -> None:
    path = filedialog.askopenfilename(parent=parent, filetypes=[("Text", "*.txt *.log"), ("All", "*.*")])
    if not path:
        return
    try:
        with open(path, "r", encoding="utf-8") as f:
            raw = f.read().splitlines()
    except Exception as exc:  # noqa: BLE001
        messagebox.showerror("Import", f"Could not read file:\n{exc}", parent=parent)
        return
    if not any(r.strip() for r in raw):
        messagebox.showwarning("Import", "File is empty.", parent=parent)
        return
    dlg = ImportDialog(parent, ctx, f"Importing {path}")
    dlg.textbox.insert("1.0", "\n".join(raw))
    dlg._run(raw)