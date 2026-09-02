"""Export token dialogs: export all / selected to a JSON file via the
ImportExportService (no network work involved)."""

from tkinter import filedialog, messagebox

import customtkinter as ctk

from ui import theme


def _do_export(ctx, parent, tokens) -> None:
    path = filedialog.asksaveasfilename(parent=parent, defaultextension=".json",
                                        filetypes=[("JSON", "*.json")])
    if not path:
        return
    payload = ctx.import_export.export(tokens)
    with open(path, "w", encoding="utf-8") as f:
        f.write(payload)
    ctx.log.success(f"Exported {len(tokens)} token(s) to {path}")


def show_export_dialog(parent, ctx) -> None:
    tokens = ctx.store.get_all()
    if not tokens:
        messagebox.showinfo("Export", "No tokens to export.", parent=parent)
        return
    _do_export(ctx, parent, tokens)


def show_export_selected(ctx, parent=None, tokens=None) -> None:
    selection = tokens or ctx.store.get_all()
    if not selection:
        messagebox.showinfo("Export", "No tokens selected.", parent=parent)
        return
    _do_export(ctx, parent, selection)