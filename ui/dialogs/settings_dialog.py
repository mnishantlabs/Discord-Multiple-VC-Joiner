"""Tabbed settings dialog backed by ``SettingsService``. Writes go through
the service so ``SETTINGS_CHANGED`` is emitted and the config stays
consistent; appearance changes are re-applied live where possible.
"""

import os
import sys
import tkinter as tk
from tkinter import messagebox

import customtkinter as ctk

from ui import theme
from ui.widgets import Tooltip

TABS = ["General", "Appearance", "Validation", "Voice", "Network", "Activity", "Advanced", "About"]


class SettingsDialog(ctk.CTkToplevel):
    """Modal top-level with grouped, tabbed configuration."""

    def __init__(self, parent, ctx) -> None:
        super().__init__(parent)
        self.ctx = ctx
        self.parent = parent
        self._vars: list = []
        self.title("Settings")
        self.geometry("520x640")
        self.configure(fg_color=theme.BG)
        self.protocol("WM_DELETE_WINDOW", self.destroy)

        tv = ctk.CTkTabview(self, corner_radius=theme.RADIUS_PANEL, fg_color=theme.CARD,
                            segmented_button_fg_color=theme.HOVER,
                            segmented_button_selected_color=ctx.accent,
                            segmented_button_selected_hover_color=ctx.accent_hover)
        tv.pack(fill="both", expand=True, padx=12, pady=12)
        for name in TABS:
            tv.add(name)

        self._build_general(tv.tab("General"))
        self._build_appearance(tv.tab("Appearance"))
        self._build_validation(tv.tab("Validation"))
        self._build_voice(tv.tab("Voice"))
        self._build_network(tv.tab("Network"))
        self._build_activity(tv.tab("Activity"))
        self._build_advanced(tv.tab("Advanced"))
        self._build_about(tv.tab("About"))

        bar = ctk.CTkFrame(self, fg_color="transparent")
        bar.pack(fill="x", padx=12, pady=(0, 12))
        ctk.CTkButton(bar, text="Cancel", width=120, height=34, fg_color=theme.HOVER,
                      hover_color=theme.HOVER, font=ctx.fonts["normal"],
                      command=self.destroy).pack(side="left")
        ctk.CTkButton(bar, text="Save", width=160, height=34, fg_color=ctx.accent,
                      hover_color=ctx.accent_hover, font=ctx.fonts["normal"],
                      command=self._save).pack(side="right")

        self.grab_set()
        self.transient(parent)

    # ---- helpers ---------------------------------------------------------------
    def _caption(self, tab, text):
        ctk.CTkLabel(tab, text=text, font=self.ctx.fonts["section"],
                     text_color=theme.SEC).pack(anchor="w", pady=(10, 4))

    def _check(self, tab, label, key, default=True, tip=None):
        var = tk.BooleanVar(value=bool(self.ctx.settings.get(key, default)))
        cb = ctk.CTkCheckBox(tab, text=label, variable=var, font=self.ctx.fonts["normal"],
                             fg_color=self.ctx.accent, hover_color=self.ctx.accent_hover)
        cb.pack(anchor="w", pady=3)
        self._vars.append((key, var))
        if tip:
            Tooltip(cb, tip)
        return var

    def _option(self, tab, label, key, values, default, tip=None):
        ctk.CTkLabel(tab, text=label, font=self.ctx.fonts["caption"],
                     text_color=theme.SEC).pack(anchor="w", pady=(8, 2))
        var = tk.StringVar(value=str(self.ctx.settings.get(key, default)))
        opt = ctk.CTkOptionMenu(tab, values=list(values), variable=var, width=180, height=28,
                                font=self.ctx.fonts["normal"], fg_color=theme.BG,
                                button_color=theme.HOVER, button_hover_color=theme.HOVER)
        opt.pack(anchor="w")
        self._vars.append((key, var))
        if tip:
            Tooltip(opt, tip)
        return var

    def _number(self, tab, label, key, default, tip=None):
        ctk.CTkLabel(tab, text=label, font=self.ctx.fonts["caption"],
                     text_color=theme.SEC).pack(anchor="w", pady=(8, 2))
        var = tk.StringVar(value=str(self.ctx.settings.get(key, default)))
        e = ctk.CTkEntry(tab, textvariable=var, width=220, height=30, fg_color=theme.BG,
                         border_width=0, font=self.ctx.fonts["normal"])
        e.pack(anchor="w")
        self._vars.append((key, var))
        if tip:
            Tooltip(e, tip)
        return var

    # ---- tabs ------------------------------------------------------------------
    def _build_general(self, tab):
        self._caption(tab, "Startup")
        self._check(tab, "Auto-validate on startup", "auto_validate", False)
        self._check(tab, "Launch on Windows startup", "launch_on_startup", False,
                    tip="Adds a HKCU Run entry; requires writing the registry on save")
        self._caption(tab, "Tokens")
        self._number(tab, "Validation concurrency (workers)", "concurrency", 5,
                     "Parallel requests during Validate All")

    def _build_appearance(self, tab):
        self._caption(tab, "Theme")
        self._option(tab, "Theme mode", "appearance_mode",
                     ["system", "dark", "light"], "dark", "Restarts pick up font changes")
        self._option(tab, "UI density (token rows)", "ui_density",
                     ["comfortable", "compact", "ultra"], "compact")
        self._option(tab, "Corner radius", "border_radius",
                     ["small", "medium", "large"], "medium")
        self._option(tab, "Font size", "font_size",
                     ["small", "medium", "large"], "medium",
                     "Applied at startup; restart to change")
        self._option(tab, "Transparency (Windows 11)",
                     "transparency", ["off", "mica", "acrylic"], "off",
                     "Native Mica/Acrylic backdrop; requires Win11 22621+")
        self._option(tab, "Sidebar width", "sidebar_width",
                     ["narrow", "medium", "wide"], "medium")

        self._caption(tab, "Accent")
        row = ctk.CTkFrame(tab, fg_color="transparent")
        row.pack(fill="x", pady=(4, 4))
        self.accent_var = tk.StringVar(value=self.ctx.settings.accent)
        for name in theme.ACCENT_ORDER:
            color = theme.accent_hex(name)
            b = ctk.CTkButton(row, text="", width=28, height=26, fg_color=color,
                              hover_color=theme.accent_hover_hex(name),
                              command=lambda n=name: self.accent_var.set(n))
            b.pack(side="left", padx=3)
            Tooltip(b, name.capitalize())
        self._vars.append(("accent", self.accent_var))

        self._caption(tab, "Extras")
        self._check(tab, "Show IDs", "show_ids", True)
        self._check(tab, "Show badges", "show_badges", True)
        self._check(tab, "Animations", "animations", True,
                    tip="Some window effects may need a restart")

    def _build_validation(self, tab):
        self._number(tab, "Retry delay (seconds)", "retry_delay", 3)
        self._number(tab, "API timeout (seconds)", "api_timeout", 10)

    def _build_voice(self, tab):
        self._number(tab, "Delay between joins (seconds)", "delay", 0.5)
        self._check(tab, "Auto rejoin on disconnect", "auto_rejoin", False)
        self._check(tab, "Auto unmute on join", "auto_unmute", False)
        self._check(tab, "Auto deafen on join", "auto_deafen", False)
        self._check(tab, "Auto go-live", "auto_golive", False)
        self._number(tab, "Reconnect attempts", "reconnect_attempts", 3)

    def _build_network(self, tab):
        ctk.CTkLabel(tab, text="Proxy (http://ip:port)", font=self.ctx.fonts["caption"],
                     text_color=theme.SEC).pack(anchor="w", pady=(10, 2))
        var = tk.StringVar(value=self.ctx.settings.proxy)
        e = ctk.CTkEntry(tab, textvariable=var, width=300, height=30, fg_color=theme.BG,
                         border_width=0, font=self.ctx.fonts["normal"])
        e.pack(anchor="w")
        self._vars.append(("proxy", var))
        Tooltip(e, "Applied to future API requests; empty = direct")

    def _build_activity(self, tab):
        self._check(tab, "Clear activity log on exit", "clear_log", False)
        ctk.CTkButton(tab, text="Recover activity from log file", height=30,
                      fg_color=theme.HOVER, hover_color=self.ctx.accent_hover,
                      font=self.ctx.fonts["caption"],
                      command=self._recover_activity).pack(anchor="w", pady=(10, 4))
        ctk.CTkButton(tab, text="Clear recent voice targets", height=30,
                      fg_color=theme.HOVER, hover_color=self.ctx.accent_hover,
                      font=self.ctx.fonts["caption"],
                      command=self._clear_recent).pack(anchor="w", pady=4)

    def _recover_activity(self):
        parent = self.parent
        if hasattr(parent, "recover_activity"):
            parent.recover_activity()
        else:
            self.ctx.log.info("Activity recovery requires a restart")
        messagebox.showinfo("Recover", "Activity recovery queued", parent=self)

    def _clear_recent(self):
        self.ctx.settings.set("recent_voice", [])
        self.ctx.log.info("Cleared recent voice targets")

    def _build_advanced(self, tab):
        ctk.CTkButton(tab, text="Open data folder", height=32,
                      fg_color=theme.HOVER, hover_color=self.ctx.accent_hover,
                      font=self.ctx.fonts["caption"],
                      command=self._open_data_folder).pack(anchor="w", pady=(12, 4))
        ctk.CTkButton(tab, text="Reset appearance to defaults", height=32,
                      fg_color=theme.HOVER, hover_color=self.ctx.accent_hover,
                      font=self.ctx.fonts["caption"],
                      command=self._reset_appearance).pack(anchor="w", pady=4)

    def _open_data_folder(self):
        repo_path = self.ctx.settings._repo.file_path
        folder = os.path.dirname(os.path.abspath(repo_path))
        try:
            if sys.platform == "win32":
                os.startfile(folder)
            else:
                import subprocess
                subprocess.Popen(["xdg-open", folder])
        except Exception:
            self.ctx.log.warning("Could not open data folder")

    def _reset_appearance(self):
        self.ctx.settings.update(
            appearance_mode="dark", ui_density="compact", border_radius="medium",
            font_size="medium", transparency="off", accent="blue",
            show_ids=True, show_badges=True, animations=True)
        messagebox.showinfo("Appearance", "Appearance reset — save to keep", parent=self)

    def _build_about(self, tab):
        ctk.CTkLabel(tab, text="Discord Token Manager", font=self.ctx.fonts["title"],
                     text_color=theme.TXT).pack(anchor="w", pady=(16, 2))
        ctk.CTkLabel(tab, text="A desktop utility for validating and organising "
                               "Discord tokens offline-first.",
                     font=self.ctx.fonts["caption"], text_color=theme.SEC,
                     wraplength=440, justify="left").pack(anchor="w", pady=(0, 8))
        ctk.CTkLabel(tab, text="Discord: @notzastence", font=self.ctx.fonts["normal"],
                     text_color=theme.TXT).pack(anchor="w", pady=2)
        ctk.CTkLabel(tab, text="GitHub & support:  link in menu",
                     font=self.ctx.fonts["normal"], text_color=theme.TXT).pack(anchor="w", pady=2)

    # ---- save ------------------------------------------------------------------
    def _save(self) -> None:
        updates = {}
        for key, var in self._vars:
            value = var.get()
            if isinstance(var, tk.BooleanVar):
                value = bool(value)
            else:
                for int_key in ("concurrency", "retry_delay", "api_timeout",
                                "reconnect_attempts"):
                    if key == int_key:
                        try:
                            value = int(value)
                        except ValueError:
                            messagebox.showerror("Invalid", f"{key} must be a number", parent=self)
                            return
                if key == "delay":
                    try:
                        value = float(value)
                    except ValueError:
                        messagebox.showerror("Invalid", "Delay must be a number", parent=self)
                        return
            updates[key] = value

        self.ctx.settings.update(**updates)
        self._apply_startup_setting()
        self.ctx.log.success("Settings saved")
        if hasattr(self.parent, "apply_appearance"):
            self.parent.apply_appearance()
        if hasattr(self.parent, "refresh_all"):
            self.parent.refresh_all()
        self.destroy()

    def _apply_startup_setting(self):
        launch = bool(self.ctx.settings.get("launch_on_startup", False))
        try:
            import winreg
            key_path = r"Software\Microsoft\Windows\CurrentVersion\Run"
            cmd = f'"{sys.executable}" "{os.path.abspath(sys.argv[0])}"'
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, key_path, 0, winreg.KEY_SET_VALUE) as k:
                if launch:
                    winreg.SetValueEx(k, "DiscordTokenManager", 0, winreg.REG_SZ, cmd)
                else:
                    try:
                        winreg.DeleteValue(k, "DiscordTokenManager")
                    except FileNotFoundError:
                        pass
        except Exception:
            self.ctx.log.warning("Could not update startup entry (registry)")


def show_settings_dialog(parent, ctx) -> None:
    SettingsDialog(parent, ctx)