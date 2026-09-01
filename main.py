import asyncio
import threading
import os
import sys
import json
import random
import webbrowser
import datetime
import tkinter as tk
from tkinter import messagebox, filedialog
import customtkinter as ctk

from core import (
    Config, TokenStore, validate_token, join_server, get_channels,
    ping_api, VoiceConnection,
)

BASE = os.path.dirname(os.path.abspath(__file__))

# ---- Palette ----
BG = "#1E1F22"
CARD = "#2B2D31"
HOVER = "#35373C"
ACCENT = "#5865F2"
ACCENT_HOVER = "#4752C4"
TXT = "#FFFFFF"
SEC = "#B5BAC1"
MUTED = "#80848E"
GOOD = "#23A55A"
GOOD_HOVER = "#1A8B4A"
DANGER = "#DA373C"
DANGER_HOVER = "#A12828"
WARN = "#E0A500"

ACCENTS = {"blue": "#5865F2", "green": "#23A55A", "purple": "#8A63D2",
           "red": "#DA373C", "orange": "#F47B20", "pink": "#EB459E"}
ACCENT_HOVERS = {"blue": "#4752C4", "green": "#1A8B4A", "purple": "#6E4FC0",
                 "red": "#A12828", "orange": "#C96A1A", "pink": "#C0247A"}

DOT_VALID = GOOD
DOT_INVALID = DANGER
DOT_LOCKED = WARN

GROUPS = [
    ("invalid", "❌ Invalid"),
    ("locked", "🔒 Locked"),
    ("nitro", "⭐ Nitro"),
    ("phone", "📱 Phone Verified"),
    ("valid", "✅ Valid"),
]

LOG_ICON = {"success": "🟢", "info": "🔵", "warn": "🟡", "error": "🔴", "rate": "🔴"}
LOG_COLOR = {"success": GOOD, "info": SEC, "warn": WARN, "error": DANGER, "rate": SEC}
LOG_CAT = {"success": "SUCCESS", "info": "INFO", "warn": "WARNING", "error": "ERROR", "rate": "NETWORK"}


def ts():
    return datetime.datetime.now().strftime("%H:%M:%S")


def username(info):
    return f"{info.get('username', '?')}#{info.get('discriminator', '0')}"


def token_status(info):
    if info.get("user_id"):
        return "valid"
    err = (info.get("error") or "").upper()
    if "LOCK" in err or "FLAGGED" in err:
        return "locked"
    return "invalid"


def created_from_id(user_id):
    try:
        ms = (int(user_id) >> 22) + 1420070400000
        return datetime.datetime.utcfromtimestamp(ms / 1000).strftime("%Y-%m-%d")
    except Exception:
        return "?"


def process_memory_mb():
    try:
        import ctypes
        from ctypes import wintypes, c_size_t
        class RMM(ctypes.Structure):
            _fields_ = [("hProcess", wintypes.HANDLE), ("cb", wintypes.DWORD),
                        ("PageFaultCount", wintypes.DWORD), ("PeakWorkingSetSize", c_size_t),
                        ("WorkingSetSize", c_size_t), ("QuotaPeakPagedPoolUsage", c_size_t),
                        ("QuotaPagedPoolUsage", c_size_t), ("QuotaPeakNonPagedPoolUsage", c_size_t),
                        ("QuotaNonPagedPoolUsage", c_size_t)]
        pmi = RMM()
        psapi = ctypes.windll.psapi
        h = ctypes.windll.kernel32.GetCurrentProcess()
        psapi.K32GetProcessMemoryInfo(h, ctypes.byref(pmi), ctypes.sizeof(pmi))
        return pmi.WorkingSetSize / (1024 * 1024)
    except Exception:
        return 0


class Tooltip:
    def __init__(self, widget, text):
        self.widget = widget
        self.text = text
        self.tip = None
        widget.bind("<Enter>", self.show)
        widget.bind("<Leave>", self.hide)

    def show(self, event=None):
        if self.tip:
            return
        x = self.widget.winfo_rootx() + 16
        y = self.widget.winfo_rooty() + self.widget.winfo_height() + 6
        self.tip = tk.Toplevel(self.widget)
        self.tip.wm_overrideredirect(True)
        self.tip.wm_geometry(f"+{x}+{y}")
        self.tip.attributes("-topmost", True)
        tip = tk.Label(self.tip, text=self.text, background="#111214", fg="#e6e6e6",
                       font=("Segoe UI", 10), padx=8, pady=4, justify="left")
        tip.pack()

    def hide(self, event=None):
        if self.tip:
            self.tip.destroy()
            self.tip = None


class App(ctk.CTk):
    def __init__(self):
        super().__init__()
        ctk.set_appearance_mode("dark")
        self.cfg = Config()
        self.store = TokenStore()
        self.selected = set()
        self.anchor = None
        self.filters = {"valid": True, "invalid": True, "locked": True, "nitro": True, "phone": True}
        self.collapsed_groups = {k: False for k, _ in GROUPS}
        self.invite_history = []
        self.voice_connections = {}
        self.selected_server = None
        self.selected_channel = None
        self.channels = []
        self._current_members = []
        self.members_collapsed = True
        self.log_filter = "all"
        self.log_pause = False
        self._tick_count = 0

        self.configure(fg_color=BG)
        self.title("Discord Token Manager")
        try:
            self.geometry(self.cfg.get("geometry", "") or "1380x880")
        except Exception:
            self.geometry("1380x880")
        self.minsize(1100, 700)

        self._fonts()
        self._build_toolbar()
        self._build_stats()
        self._build_workflow()
        self._build_actions()
        self._build_log()
        self._build_statusbar()
        self._bind_shortcuts()

        self.protocol("WM_DELETE_WINDOW", self.on_close)
        self.refresh_all()
        self.check_api()
        self.after(1000, self._tick)

    # ---------- FONTS ----------
    def _fonts(self):
        self.F_TITLE = ctk.CTkFont(family="Segoe UI", size=20, weight="bold")
        self.F_SECTION = ctk.CTkFont(family="Segoe UI", size=11, weight="bold")
        self.F_NORMAL = ctk.CTkFont(family="Segoe UI", size=13)
        self.F_CAPTION = ctk.CTkFont(family="Segoe UI", size=11)

    def acc(self):
        return ACCENTS.get(self.cfg.get("accent", "blue"), ACCENT)

    def acc_h(self):
        return ACCENT_HOVERS.get(self.cfg.get("accent", "blue"), ACCENT_HOVER)

    # ---------- TOOLBAR ----------
    def _build_toolbar(self):
        bar = ctk.CTkFrame(self, fg_color="transparent")
        bar.pack(fill="x", padx=16, pady=(8, 2))
        inner = ctk.CTkFrame(bar, fg_color="transparent")
        inner.pack(fill="x")

        ctk.CTkLabel(inner, text="Discord Token Manager", font=self.F_TITLE).pack(side="left", padx=(0, 16))

        def icon_btn(text, tip, cmd):
            b = ctk.CTkButton(inner, text=text, command=cmd, width=34, height=30,
                              fg_color=HOVER, hover_color=self.acc_h(), corner_radius=6)
            b.pack(side="left", padx=3)
            Tooltip(b, tip)

        icon_btn("📥", "Import tokens (Ctrl+I)", self.open_import)
        icon_btn("📋", "Paste tokens (Ctrl+V)", lambda: self.open_paste(True))
        icon_btn("📂", "Import from file", self.import_file)
        icon_btn("💾", "Export tokens", self.export_tokens)
        icon_btn("🔄", "Refresh (Ctrl+R)", self.refresh_all)
        icon_btn("⚙", "Settings", self.open_settings)
        icon_btn("ℹ", "About", self.open_about)

        self.status_label = ctk.CTkLabel(inner, text="Ready", font=self.F_CAPTION, text_color=SEC)
        self.status_label.pack(side="right", padx=4)

    # ---------- STATS ----------
    def _build_stats(self):
        dash = ctk.CTkFrame(self, fg_color="transparent")
        dash.pack(fill="x", padx=16, pady=(4, 10))
        self.stat_vals = {}
        specs = [("👤", "Total Tokens"), ("✅", "Valid"), ("🖥", "Servers"), ("🎯", "Selected")]
        for icon, name in specs:
            card = ctk.CTkFrame(dash, width=150, height=42, corner_radius=8, fg_color=CARD)
            card.pack(side="left", padx=4, expand=True, fill="both")
            card.pack_propagate(False)
            row = ctk.CTkFrame(card, fg_color="transparent")
            row.pack(expand=True)
            ctk.CTkLabel(row, text=icon, font=self.F_NORMAL).pack(side="left", padx=(10, 6))
            val = ctk.CTkLabel(row, text="0", font=self.F_TITLE)
            val.pack(side="left")
            ctk.CTkLabel(row, text=name, font=self.F_CAPTION, text_color=SEC).pack(side="left", padx=(6, 10))
            self.stat_vals[name] = val

        prog = ctk.CTkFrame(dash, fg_color=CARD, corner_radius=8, height=42)
        prog.pack(side="left", padx=8, expand=True, fill="both")
        prog.pack_propagate(False)
        prow = ctk.CTkFrame(prog, fg_color="transparent")
        prow.pack(fill="x", expand=True, padx=12)
        ctk.CTkLabel(prow, text="Validation", font=self.F_CAPTION, text_color=SEC).pack(side="left")
        self.progress_label = ctk.CTkLabel(prow, text="0 / 0  0%", font=self.F_CAPTION, text_color=SEC)
        self.progress_label.pack(side="right")
        self.progress = ctk.CTkProgressBar(prog, height=6, corner_radius=3,
                                           fg_color=HOVER, progress_color=GOOD)
        self.progress.pack(fill="x", padx=12, pady=(0, 8))

    # ---------- WORKFLOW ----------
    def _panel(self, parent, icon, title):
        card = ctk.CTkFrame(parent, fg_color=CARD, corner_radius=8)
        head = ctk.CTkFrame(card, fg_color="transparent")
        head.pack(fill="x", padx=14, pady=(10, 8))
        ctk.CTkLabel(head, text=f"{icon} {title.upper()}", font=self.F_SECTION, text_color=SEC).pack(side="left")
        return card

    def _build_workflow(self):
        body = ctk.CTkFrame(self, fg_color="transparent")
        body.pack(fill="both", expand=True, padx=16, pady=4)

        left = self._panel(body, "👤", "Token Manager")
        left.pack(side="left", fill="both", expand=True, padx=4)
        self._build_tokens_panel(left)

        center = self._panel(body, "🖥", "Server List")
        center.pack(side="left", fill="both", expand=True, padx=4)
        self._build_servers_panel(center)

        right = self._panel(body, "🎤", "Voice Channels")
        right.pack(side="left", fill="both", expand=True, padx=4)
        self._build_voice_panel(right)

    # ---------- TOKENS PANEL ----------
    def _build_tokens_panel(self, parent):
        body = ctk.CTkFrame(parent, fg_color="transparent")
        body.pack(fill="both", expand=True, padx=14, pady=(0, 12))

        self.search_var = tk.StringVar()
        self.search_var.trace_add("write", lambda *a: self.refresh_token_list())
        self.search_entry = ctk.CTkEntry(body, textvariable=self.search_var,
                                         placeholder_text="🔍  Search…",
                                         height=32, corner_radius=6, fg_color=BG, border_width=0,
                                         font=self.F_NORMAL)
        self.search_entry.pack(fill="x", pady=(0, 6))

        row1 = ctk.CTkFrame(body, fg_color="transparent")
        row1.pack(fill="x", pady=(0, 8))
        ctk.CTkButton(row1, text="☑", command=self.select_all, width=30, height=26,
                      fg_color=HOVER, hover_color=self.acc_h(), corner_radius=5).pack(side="left", padx=2)
        ctk.CTkButton(row1, text="⇄", command=self.invert, width=30, height=26,
                      fg_color=HOVER, hover_color=self.acc_h(), corner_radius=5).pack(side="left", padx=2)

        self.filter_pills = {}
        for name, key in [("Valid", "valid"), ("Invalid", "invalid"), ("Locked", "locked"),
                          ("Nitro", "nitro"), ("Phone", "phone")]:
            b = ctk.CTkButton(row1, text=name, width=58, height=26, font=self.F_CAPTION,
                              fg_color=self.acc() if self.filters[key] else HOVER,
                              hover_color=self.acc_h(), command=lambda k=key: self.toggle_filter_pill(k))
            b.pack(side="left", padx=2)
            self.filter_pills[key] = b

        self.sort_var = tk.StringVar(value="Server Count")
        ctk.CTkOptionMenu(row1, values=["Server Count", "Name", "User ID"], variable=self.sort_var,
                          command=lambda *a: self.refresh_token_list(), width=120, height=26,
                          font=self.F_CAPTION, fg_color=BG, button_color=HOVER,
                          button_hover_color=HOVER).pack(side="right")

        row2 = ctk.CTkFrame(body, fg_color="transparent")
        row2.pack(fill="x", pady=(0, 6))
        self.selected_label = ctk.CTkLabel(row2, text="Selected: 0 / 0", font=self.F_CAPTION,
                                           text_color=SEC, anchor="w")
        self.selected_label.pack(side="left")
        ctk.CTkButton(row2, text="Validate All", width=96, height=24, font=self.F_CAPTION,
                      fg_color=HOVER, hover_color=self.acc_h(), command=self.validate_all).pack(side="right")

        self.token_canvas = ctk.CTkScrollableFrame(body, fg_color=BG, corner_radius=8)
        self.token_canvas.pack(fill="both", expand=True)

        self.detail_frame = ctk.CTkFrame(body, fg_color=BG, corner_radius=8)
        self.detail_frame.pack(fill="x", pady=(8, 0))

    def toggle_filter_pill(self, key):
        self.filters[key] = not self.filters[key]
        self.refresh_token_list()

    # ---------- SERVERS PANEL ----------
    def _build_servers_panel(self, parent):
        body = ctk.CTkFrame(parent, fg_color="transparent")
        body.pack(fill="both", expand=True, padx=14, pady=(0, 12))

        self.browser_search = tk.StringVar()
        self.browser_search.trace_add("write", lambda *a: self.refresh_servers())
        self.server_search_entry = ctk.CTkEntry(body, textvariable=self.browser_search,
                                                placeholder_text="🔍  Search Servers…",
                                                height=32, corner_radius=6, fg_color=BG, border_width=0,
                                                font=self.F_NORMAL)
        self.server_search_entry.pack(fill="x", pady=(0, 8))

        self.server_list = ctk.CTkScrollableFrame(body, fg_color=BG, corner_radius=8)
        self.server_list.pack(fill="both", expand=True)

        self.server_info_label = ctk.CTkLabel(body, text="", font=self.F_CAPTION, text_color=SEC, anchor="w")
        self.server_info_label.pack(fill="x", pady=(8, 2))

        self.members_toggle = ctk.CTkButton(body, text="▸ Members", height=26, font=self.F_CAPTION,
                                            fg_color=HOVER, hover_color=self.acc_h(),
                                            command=self.toggle_members)
        self.members_toggle.pack(fill="x", pady=(0, 2))
        self.server_members = ctk.CTkScrollableFrame(body, fg_color=BG, corner_radius=8, height=0)
        self.server_members.pack(fill="x")

    # ---------- VOICE PANEL ----------
    def _build_voice_panel(self, parent):
        body = ctk.CTkFrame(parent, fg_color="transparent")
        body.pack(fill="both", expand=True, padx=14, pady=(0, 12))

        ctk.CTkLabel(body, text="Current Server", font=self.F_CAPTION, text_color=SEC, anchor="w").pack(fill="x")
        self.voice_server_label = ctk.CTkLabel(body, text="No server selected", font=self.F_NORMAL,
                                               anchor="w", text_color=MUTED)
        self.voice_server_label.pack(fill="x", pady=(2, 6))

        self.adv_button = ctk.CTkButton(body, text="▸  Advanced", height=26, font=self.F_CAPTION,
                                        fg_color=HOVER, hover_color=self.acc_h(), command=self.toggle_advanced)
        self.adv_button.pack(fill="x", pady=(0, 4))
        self.adv_frame = ctk.CTkFrame(body, fg_color=BG, corner_radius=6)

        self.guild_id_var = tk.StringVar()
        self.guild_id_entry = ctk.CTkEntry(self.adv_frame, textvariable=self.guild_id_var,
                                           placeholder_text="Server / guild ID", height=28,
                                           corner_radius=6, fg_color=CARD, border_width=0, font=self.F_CAPTION)
        self.guild_id_entry.pack(fill="x", padx=8, pady=3)
        self.channel_id_var = tk.StringVar()
        self.channel_id_entry = ctk.CTkEntry(self.adv_frame, textvariable=self.channel_id_var,
                                             placeholder_text="Voice channel ID", height=28,
                                             corner_radius=6, fg_color=CARD, border_width=0, font=self.F_CAPTION)
        self.channel_id_entry.pack(fill="x", padx=8, pady=3)
        self.adv_user_label = ctk.CTkLabel(self.adv_frame, text="User ID: -", font=self.F_CAPTION, text_color=SEC)
        self.adv_user_label.pack(anchor="w", padx=8, pady=2)

        advrow = ctk.CTkFrame(self.adv_frame, fg_color="transparent")
        advrow.pack(fill="x", padx=8, pady=3)
        self.delay_var = tk.StringVar(value=str(self.cfg.get("delay", 0.5)))
        self.conc_var = tk.StringVar(value=str(self.cfg.get("concurrency", 5)))
        self.retry_var = tk.StringVar(value=str(self.cfg.get("retry_delay", 3)))
        self.timeout_var = tk.StringVar(value=str(self.cfg.get("api_timeout", 10)))
        labels = [("Delay", self.delay_var), ("Conc", self.conc_var), ("Retry", self.retry_var), ("Time", self.timeout_var)]
        for i, (lab, var) in enumerate(labels):
            col = ctk.CTkFrame(advrow, fg_color="transparent")
            col.pack(side="left", padx=4)
            ctk.CTkLabel(col, text=lab, font=self.F_CAPTION, text_color=MUTED).pack(anchor="w")
            e = ctk.CTkEntry(col, textvariable=var, width=52, height=24, fg_color=CARD,
                             border_width=0, font=self.F_CAPTION)
            e.pack()
            e.bind("<FocusOut>", lambda *_a: self._commit_advanced())

        ctk.CTkLabel(body, text="Recently Joined", font=self.F_CAPTION, text_color=SEC,
                     anchor="w").pack(fill="x", pady=(8, 2))
        self.recent_voice_frame = ctk.CTkFrame(body, fg_color=BG, corner_radius=6)
        self.recent_voice_frame.pack(fill="x", pady=(0, 6))

        ctk.CTkLabel(body, text="Channels", font=self.F_CAPTION, text_color=SEC, anchor="w").pack(fill="x", pady=(0, 4))
        self.channel_list = ctk.CTkScrollableFrame(body, fg_color=BG, corner_radius=8)
        self.channel_list.pack(fill="both", expand=True)
        self.voice_hint = ctk.CTkLabel(body, text="Select a server in the Server List",
                                       font=self.F_CAPTION, text_color=MUTED)
        self.voice_hint.pack(pady=6)

    # ---------- ACTIONS ----------
    def _build_actions(self):
        bar = ctk.CTkFrame(self, fg_color=CARD, corner_radius=8)
        bar.pack(fill="x", padx=16, pady=(0, 10))
        inner = ctk.CTkFrame(bar, fg_color="transparent")
        inner.pack(fill="x", padx=16, pady=10)

        s1 = ctk.CTkFrame(inner, fg_color="transparent")
        s1.pack(side="left", padx=(0, 28))
        ctk.CTkLabel(s1, text="INVITE", font=self.F_SECTION, text_color=SEC, anchor="w").pack(fill="x")
        r1 = ctk.CTkFrame(s1, fg_color="transparent")
        r1.pack(pady=(4, 0))
        self.invite_var = tk.StringVar()
        self.invite_entry = ctk.CTkEntry(r1, textvariable=self.invite_var,
                                         placeholder_text="Invite link or code", width=240,
                                         height=32, fg_color=BG, border_width=0, font=self.F_NORMAL)
        self.invite_entry.pack(side="left")
        self.invite_entry.bind("<Return>", lambda e: self.do_join())
        ctk.CTkButton(r1, text="📋", command=self.paste_invite, width=34, height=32,
                      fg_color=HOVER, hover_color=self.acc_h()).pack(side="left", padx=4)
        ctk.CTkButton(r1, text="Join", command=self.do_join, width=90, height=32,
                      fg_color=self.acc(), hover_color=self.acc_h(), font=self.F_NORMAL).pack(side="left")
        self.recent_frame = ctk.CTkFrame(s1, fg_color="transparent")
        self.recent_frame.pack(fill="x", pady=(6, 0))

        s2 = ctk.CTkFrame(inner, fg_color="transparent")
        s2.pack(side="left", padx=(0, 28))
        ctk.CTkLabel(s2, text="VOICE", font=self.F_SECTION, text_color=SEC, anchor="w").pack(fill="x")
        rb = ctk.CTkFrame(s2, fg_color="transparent")
        rb.pack(pady=(4, 0))
        self.mute_var = tk.BooleanVar()
        self.deaf_var = tk.BooleanVar()
        ctk.CTkCheckBox(rb, text="Mute", variable=self.mute_var, font=self.F_CAPTION,
                        fg_color=ACCENT, hover_color=ACCENT_HOVER,
                        checkbox_width=18, checkbox_height=18).pack(side="left", padx=6)
        ctk.CTkCheckBox(rb, text="Deaf", variable=self.deaf_var, font=self.F_CAPTION,
                        fg_color=ACCENT, hover_color=ACCENT_HOVER,
                        checkbox_width=18, checkbox_height=18).pack(side="left", padx=6)
        ctk.CTkButton(rb, text="Rejoin", command=self.do_rejoin, width=74, height=32,
                      fg_color=HOVER, hover_color=self.acc_h(), font=self.F_CAPTION).pack(side="left", padx=4)
        ctk.CTkButton(rb, text="Random", command=self.do_join_random, width=74, height=32,
                      fg_color=HOVER, hover_color=self.acc_h(), font=self.F_CAPTION).pack(side="left", padx=4)
        ctk.CTkButton(rb, text="Join VC", command=self.do_join_voice, width=84, height=32,
                      fg_color=GOOD, hover_color=GOOD_HOVER, font=self.F_NORMAL).pack(side="left", padx=4)
        ctk.CTkButton(rb, text="Leave", command=self.do_leave_voice, width=74, height=32,
                      fg_color=DANGER, hover_color=DANGER_HOVER, font=self.F_NORMAL).pack(side="left")

        s3 = ctk.CTkFrame(inner, fg_color="transparent")
        s3.pack(side="left")
        ctk.CTkLabel(s3, text="SELECTED", font=self.F_SECTION, text_color=SEC, anchor="w").pack(fill="x")
        d1 = ctk.CTkFrame(s3, fg_color="transparent")
        d1.pack(pady=(4, 0))
        ctk.CTkButton(d1, text="✔ Validate", command=self.validate_selected, width=110, height=32,
                      fg_color=GOOD, hover_color=GOOD_HOVER, font=self.F_NORMAL).pack(side="left", padx=4)
        ctk.CTkButton(d1, text="📤 Export", command=self.export_selected, width=90, height=32,
                      fg_color=HOVER, hover_color=self.acc_h(), font=self.F_NORMAL).pack(side="left", padx=4)
        ctk.CTkButton(d1, text="🗑 Delete", command=self.remove_selected_confirm, width=90, height=32,
                      fg_color=DANGER, hover_color=DANGER_HOVER, font=self.F_NORMAL).pack(side="left", padx=4)

    # ---------- LOG ----------
    def _build_log(self):
        panel = ctk.CTkFrame(self, fg_color=CARD, corner_radius=8)
        panel.pack(fill="x", padx=16, pady=(0, 4))
        head = ctk.CTkFrame(panel, fg_color="transparent")
        head.pack(fill="x", padx=14, pady=(8, 0))
        ctk.CTkLabel(head, text="📜  ACTIVITY", font=self.F_SECTION, text_color=SEC).pack(side="left")

        self.log_search = tk.StringVar()
        self.log_search.trace_add("write", lambda *a: self._render_logs())
        ls = ctk.CTkEntry(head, textvariable=self.log_search, placeholder_text="🔍  Search logs…",
                          width=200, height=26, fg_color=BG, border_width=0, font=self.F_CAPTION)
        ls.pack(side="left", padx=8)
        ctk.CTkButton(head, text="📋 Copy", height=22, width=52, font=self.F_CAPTION,
                      fg_color=HOVER, hover_color=self.acc_h(), command=self._copy_logs).pack(side="left", padx=2)
        ctk.CTkButton(head, text="💾 Save", height=22, width=52, font=self.F_CAPTION,
                      fg_color=HOVER, hover_color=self.acc_h(), command=self._export_logs).pack(side="left", padx=2)
        self.pause_btn = ctk.CTkButton(head, text="⏸", height=22, width=34, font=self.F_CAPTION,
                                       fg_color=HOVER, hover_color=self.acc_h(), command=self.toggle_pause_log)
        self.pause_btn.pack(side="left", padx=2)
        ft = ctk.CTkFrame(head, fg_color="transparent")
        ft.pack(side="right")
        for name, key in [("All", "all"), ("INFO", "info"), ("SUCCESS", "success"),
                          ("WARNING", "warn"), ("ERROR", "error"), ("NETWORK", "rate")]:
            ctk.CTkButton(ft, text=name, height=22, width=58, font=self.F_CAPTION,
                          fg_color=HOVER, hover_color=self.acc_h(),
                          command=lambda k=key: self.set_log_filter(k)).pack(side="left", padx=2)

        self.log_text = ctk.CTkTextbox(panel, height=150, state="disabled", wrap="none",
                                       fg_color=BG, text_color=TXT, border_width=0, font=self.F_NORMAL)
        self.log_text.pack(fill="x", padx=14, pady=(6, 12))
        self.log_lines = []

    # ---------- STATUS BAR ----------
    def _build_statusbar(self):
        bar = ctk.CTkFrame(self, fg_color=CARD, corner_radius=0, height=26)
        bar.pack(fill="x", side="bottom")
        inner = ctk.CTkFrame(bar, fg_color="transparent")
        inner.pack(fill="x", padx=16, pady=2)
        self.foot_status = ctk.CTkLabel(inner, text="🟢 Ready", font=self.F_CAPTION, text_color=GOOD)
        self.foot_status.pack(side="left", padx=10)
        self.foot_tokens = ctk.CTkLabel(inner, text="👤 0 Tokens", font=self.F_CAPTION, text_color=SEC)
        self.foot_tokens.pack(side="left", padx=10)
        self.foot_servers = ctk.CTkLabel(inner, text="🖥 0 Servers", font=self.F_CAPTION, text_color=SEC)
        self.foot_servers.pack(side="left", padx=10)
        self.mem_label = ctk.CTkLabel(inner, text="🧠 -- MB", font=self.F_CAPTION, text_color=SEC)
        self.mem_label.pack(side="left", padx=10)
        self.foot_voice = ctk.CTkLabel(inner, text="📶 Idle", font=self.F_CAPTION, text_color=SEC)
        self.foot_voice.pack(side="left", padx=10)
        self.api_status = ctk.CTkLabel(inner, text="● Checking...", font=self.F_CAPTION, text_color=WARN)
        self.api_status.pack(side="right", padx=10)
        self.time_label = ctk.CTkLabel(inner, text=ts(), font=self.F_CAPTION, text_color=SEC)
        self.time_label.pack(side="right", padx=10)

    # ---------- KEYBOARD ----------
    def _focus_in_input(self):
        w = self.focus_get()
        return isinstance(w, (ctk.CTkEntry, ctk.CTkTextbox, tk.Entry, tk.Text))

    def _bind_shortcuts(self):
        self.bind("<Control-r>", lambda e: self.refresh_all())
        self.bind("<Control-i>", lambda e: self.open_import())
        self.bind("<Control-v>", lambda e: self.open_paste(True) if not self._focus_in_input() else None)
        self.bind("<Control-f>", lambda e: (self.search_entry.focus_set(), self.search_entry.select_range(0, "end")))
        self.bind("<Control-a>", lambda e: self.select_all() if not self._focus_in_input() else None)
        self.bind("<Delete>", lambda e: self.remove_selected_confirm() if not self._focus_in_input() else None)
        self.bind("<Return>", lambda e: self.do_join_voice() if not self._focus_in_input() else None)
        self.bind("<Control-c>", lambda e: self.copy_selected_ids() if not self._focus_in_input() else None)
        self.bind("<Control-Shift-C>", lambda e: self.copy_selected_usernames() if not self._focus_in_input() else None)
        self.bind("<Control-o>", lambda e: self.open_import())

    def on_close(self):
        try:
            self.cfg.data["geometry"] = self.geometry()
            self.cfg.save()
        except Exception:
            pass
        self.destroy()

    # ---------- LOG API ----------
    def set_log_filter(self, key):
        self.log_filter = key
        self._render_logs()

    def clear_logs(self):
        self.log_lines = []
        self._render_logs()

    def toggle_pause_log(self):
        self.log_pause = not self.log_pause
        self.pause_btn.configure(text="▶" if self.log_pause else "⏸")

    def log(self, msg, kind="info"):
        self.log_lines.append((ts(), msg, kind))
        self._render_logs(autoscroll=not self.log_pause)

    def _visible_logs(self):
        q = self.log_search.get().lower().strip()
        out = []
        for t, msg, kind in self.log_lines:
            if self.log_filter != "all" and self.log_filter != kind:
                continue
            if q and q not in msg.lower():
                continue
            out.append((t, msg, kind))
        return out

    def _render_logs(self, autoscroll=False):
        self.log_text.configure(state="normal")
        self.log_text.delete("1.0", "end")
        for t, msg, kind in self._visible_logs():
            icon = LOG_ICON.get(kind, "🔵")
            self.log_text.insert("end", f"{t}  ", ("ts",))
            self.log_text.insert("end", f"{icon} {msg}\n", (kind,))
        self.log_text.tag_config("ts", foreground=MUTED)
        for k, c in LOG_COLOR.items():
            self.log_text.tag_config(k, foreground=c)
        self.log_text.configure(state="disabled")
        if autoscroll:
            self.log_text.see("end")

    def _copy_logs(self):
        lines = "\n".join(f"{t} {m}" for t, m, k in self._visible_logs())
        if lines:
            self.clipboard_put(lines)
            self.log("Logs copied to clipboard", "info")

    def _export_logs(self):
        path = filedialog.asksaveasfilename(parent=self, defaultextension=".txt",
                                            filetypes=[("Text", "*.txt")])
        if path:
            with open(path, "w", encoding="utf-8") as f:
                for t, m, k in self._visible_logs():
                    f.write(f"[{LOG_CAT.get(k, 'INFO')}] {t} {m}\n")
            self.log(f"Logs saved to {path}", "success")

    # ---------- REFRESH ----------
    def refresh_all(self):
        self.refresh_stats()
        self.refresh_token_list()
        self.refresh_servers()
        self.refresh_recent()
        self.refresh_recent_voice()

    def refresh_stats(self):
        tokens = self.store.get_all()
        valid = sum(1 for t, i in tokens.items() if token_status(i) == "valid")
        servers = {s["id"] for t, i in tokens.items() for s in i.get("servers", [])}
        self.stat_vals["Total Tokens"].configure(text=str(len(tokens)))
        self.stat_vals["Valid"].configure(text=str(valid))
        self.stat_vals["Servers"].configure(text=str(len(servers)))
        self.stat_vals["Selected"].configure(text=str(len(self.selected)))
        pct = (valid / len(tokens) * 100) if tokens else 0
        self.progress.set(pct / 100)
        self.progress_label.configure(text=f"{valid} / {len(tokens)}  {pct:.0f}%")
        self.foot_tokens.configure(text=f"👤 {len(tokens)} Tokens")
        self.foot_servers.configure(text=f"🖥 {len(servers)} Servers")
        self.foot_voice.configure(text=f"📶 {len(self.voice_connections)} Connected"
                                      if self.voice_connections else "📶 Idle")

    def check_api(self):
        def worker():
            try:
                ok = self._run_async(ping_api(self.cfg))
                self.after(0, lambda: self.api_status.configure(
                    text="● API: Online" if ok else "● API: Offline",
                    text_color=GOOD if ok else DANGER))
            except Exception:
                pass
        threading.Thread(target=worker, daemon=True).start()

    def _tick(self):
        self.time_label.configure(text=ts())
        self._tick_count += 1
        if self._tick_count % 5 == 0:
            self.mem_label.configure(text=f"🧠 {process_memory_mb():.0f} MB")
        self.after(1000, self._tick)

    # ---------- TOKEN LIST ----------
    def _categorize(self, info):
        if not info.get("user_id"):
            return "invalid"
        if token_status(info) == "locked":
            return "locked"
        if info.get("premium_type", 0) > 0:
            return "nitro"
        if info.get("phone"):
            return "phone"
        return "valid"

    def refresh_token_list(self):
        for w in self.token_canvas.winfo_children():
            w.destroy()
        tokens = self.store.get_all()
        query = self.search_var.get().lower().strip()

        buckets = {k: [] for k, _ in GROUPS}
        for token, info in tokens.items():
            st = token_status(info)
            if st == "valid" and not self.filters["valid"]:
                continue
            if st == "locked" and not self.filters["locked"]:
                continue
            if st == "invalid" and not self.filters["invalid"]:
                continue
            if info.get("premium_type", 0) > 0 and not self.filters["nitro"]:
                continue
            if info.get("phone") and not self.filters["phone"]:
                continue
            # search: username, user id, server names, server ids, email, phone
            hay = " ".join([
                info.get("username", ""), info.get("user_id", ""),
                str(info.get("email") or ""), str(info.get("phone") or ""),
                " ".join(s["name"] for s in info.get("servers", [])),
                " ".join(s["id"] for s in info.get("servers", [])),
            ]).lower()
            if query and query not in hay:
                continue
            buckets[self._categorize(info)].append((token, info))

        sort = self.sort_var.get()
        for key in buckets:
            if sort == "Name":
                buckets[key].sort(key=lambda x: x[1].get("username", ""))
            elif sort == "User ID":
                buckets[key].sort(key=lambda x: x[1].get("user_id", ""))
            else:
                buckets[key].sort(key=lambda x: len(x[1].get("servers", [])), reverse=True)

        all_keys = list(tokens.keys())
        empty = True
        for key, label in GROUPS:
            items = buckets[key]
            if not items:
                continue
            empty = False
            row = ctk.CTkFrame(self.token_canvas, fg_color="transparent")
            row.pack(fill="x", pady=(4, 2))
            icon = "▾" if not self.collapsed_groups[key] else "▸"
            btn = ctk.CTkButton(row, text=f"{icon}  {label}  ({len(items)})", anchor="w", height=28,
                                font=self.F_SECTION, fg_color=HOVER, hover_color=self.acc_h(),
                                command=lambda k=key: self.toggle_group(k))
            btn.pack(side="left", fill="x", expand=True)
            ctk.CTkButton(row, text="Sel", width=46, height=28, font=self.F_CAPTION,
                          fg_color=HOVER, hover_color=self.acc_h(),
                          command=lambda k=key: self.select_group(k)).pack(side="right", padx=(4, 2))
            if not self.collapsed_groups[key]:
                for i, (token, info) in enumerate(items):
                    self._render_token_card(token, info, all_keys)

        if empty:
            ctk.CTkLabel(self.token_canvas, text="No tokens match", font=self.F_CAPTION,
                         text_color=MUTED).pack(pady=14)

        self.selected_label.configure(text=f"Selected: {len(self.selected)} / {len(tokens)}")
        self._set_pills()
        self._render_details()
        self.refresh_stats()

    def toggle_group(self, key):
        self.collapsed_groups[key] = not self.collapsed_groups[key]
        self.refresh_token_list()

    def select_group(self, key):
        tokens = self.store.get_all()
        for token, info in tokens.items():
            if self._categorize(info) == key and info.get("user_id") is not None:
                self.selected.add(token)
            elif self._categorize(info) == key and key in ("invalid", "locked"):
                self.selected.add(token)
        self.refresh_token_list()

    def _set_pills(self):
        for key, b in self.filter_pills.items():
            b.configure(fg_color=self.acc() if self.filters[key] else HOVER,
                        hover_color=self.acc_h())

    def _token_row_count(self):
        return 130 if not self.cfg.get("compact") else 50

    def _render_token_card(self, token, info, all_tokens):
        st = token_status(info)
        dot = {"valid": DOT_VALID, "invalid": DOT_INVALID, "locked": DOT_LOCKED}[st]
        card = ctk.CTkFrame(self.token_canvas, fg_color=CARD, corner_radius=8)
        height = self._token_row_count()
        card.configure(height=height)
        card.pack_propagate(False)
        card.pack(fill="x", pady=3)
        card.configure(border_width=2 if token in self.selected else 0, border_color=self.acc())

        inner = ctk.CTkFrame(card, fg_color="transparent")
        inner.pack(fill="both", padx=10, pady=6)

        ctk.CTkLabel(inner, text="●", text_color=dot, font=ctk.CTkFont(size=13)).pack(side="left", padx=(0, 8))

        txt = ctk.CTkFrame(inner, fg_color="transparent")
        txt.pack(side="left", fill="x", expand=True)
        name_row = ctk.CTkFrame(txt, fg_color="transparent")
        name_row.pack(fill="x")
        ctk.CTkLabel(name_row, text=username(info), font=self.F_NORMAL).pack(side="left")
        if self.cfg.get("show_badges", True):
            badges = []
            if info.get("premium_type", 0) > 0:
                badges.append(("Nitro", "#B474F0", "#3A2E4A"))
            if info.get("is_verified"):
                badges.append(("✔", "#7BD5FF", "#1E3A4A"))
            if info.get("phone"):
                badges.append(("📱", "#7BD5FF", "#1E3A4A"))
            for label, fg, bg in badges:
                ctk.CTkLabel(name_row, text=label, font=self.F_CAPTION, text_color=fg,
                             fg_color=bg, corner_radius=4, padx=4).pack(side="left", padx=3)
        meta = f"{len(info.get('servers', []))} Servers"
        ctk.CTkLabel(txt, text=meta, font=self.F_CAPTION, text_color=SEC, anchor="w").pack(anchor="w")
        if self.cfg.get("show_ids", True):
            uid = info.get("user_id", "?")
            ctk.CTkLabel(txt, text=f"ID {uid[:14]}...", font=self.F_CAPTION, text_color=MUTED,
                         anchor="w").pack(anchor="w")

        cb = ctk.CTkCheckBox(inner, text="", width=8,
                             variable=tk.BooleanVar(value=token in self.selected),
                             command=lambda: self.toggle_token(token),
                             checkbox_width=18, checkbox_height=18,
                             fg_color=ACCENT, hover_color=ACCENT_HOVER)
        cb.pack(side="right", padx=2)

        for w in (card, inner, txt, name_row):
            w.bind("<Button-1>", lambda e, t=token, l=all_tokens: self.on_token_click(e, t, l))
            w.bind("<Button-3>", lambda e, t=token: self.token_context(e, t))
            w.bind("<Double-Button-1>", lambda e, t=token: self.dbl_token_join(t))
            w.bind("<Button-2>", lambda e, t=token: self.clipboard_put(self.store.get(t).get("user_id", "")))
        Tooltip(card, self._token_tooltip_text(info))

    def _token_tooltip_text(self, info):
        lines = [username(info)]
        if info.get("premium_type", 0) > 0:
            lines.append("⭐ Nitro")
        if info.get("phone"):
            lines.append("📱 Phone Verified")
        if info.get("is_verified"):
            lines.append("✔ Verified (email)")
        lines.append(f"User ID: {info.get('user_id', '?')}")
        lines.append(f"Created: {created_from_id(info.get('user_id', '0'))}")
        lines.append(f"Servers: {len(info.get('servers', []))}")
        if info.get("email"):
            lines.append(f"Email: {info['email']}")
        if info.get("flags"):
            lines.append(f"Badges: {', '.join(info['flags'][:6])}")
        return "\n".join(lines)

    def dbl_token_join(self, token):
        info = self.store.get(token)
        servers = info.get("servers", [])
        if not servers:
            self.log("No servers on this token to rejoin", "warn")
            return
        s = servers[0]
        self.selected = {token}
        self.guild_id_var.set(s["id"])
        self.selected_server = {"id": s["id"], "name": s["name"]}
        self.voice_server_label.configure(text=s["name"], text_color=TXT)
        self.refresh_token_list()
        self.do_join_voice()

    # ---------- DETAILS ----------
    def _render_details(self):
        for w in self.detail_frame.winfo_children():
            w.destroy()
        uid_text = "-"
        if len(self.selected) == 1:
            token = next(iter(self.selected))
            info = self.store.get(token)
            uid_text = info.get("user_id", "-")
            ctk.CTkLabel(self.detail_frame, text="DETAILS", font=self.F_SECTION,
                         text_color=SEC).pack(anchor="w", padx=8, pady=(6, 2))
            lines = [
                f"👤  {username(info)}",
                f"🆔  {info.get('user_id', '?')}",
                f"📅  Created {created_from_id(info.get('user_id', '0'))}",
                f"🖥  {len(info.get('servers', []))} servers",
            ]
            if info.get("email"):
                lines.append(f"📧  {info['email']}")
            if info.get("phone"):
                lines.append(f"📱  {info['phone']}")
            if info.get("premium_type", 0) > 0:
                lines.append(f"⭐  Nitro (tier {info['premium_type']})")
            if info.get("mfa_enabled"):
                lines.append("🔐  MFA enabled")
            if info.get("flags"):
                lines.append(f"🎖  {', '.join(info['flags'][:6])}")
            for line in lines:
                ctk.CTkLabel(self.detail_frame, text=line, font=self.F_CAPTION,
                             text_color=SEC, anchor="w").pack(anchor="w", padx=8)
        else:
            ctk.CTkLabel(self.detail_frame, text="Select a single token to view details",
                         font=self.F_CAPTION, text_color=MUTED).pack(anchor="w", padx=8, pady=6)
        self.adv_user_label.configure(text=f"User ID: {uid_text}")

    # ---------- TOKEN SELECTION ----------
    def on_token_click(self, event, token, all_tokens):
        if event.state & 0x4:
            self._toggle(token)
        elif event.state & 0x1:
            if self.anchor is not None:
                try:
                    a = all_tokens.index(self.anchor)
                    i1 = all_tokens.index(token)
                    lo, hi = (a, i1) if a < i1 else (i1, a)
                    self.selected.update(all_tokens[lo:hi + 1])
                except ValueError:
                    self.selected.add(token)
            else:
                self.selected.add(token)
        else:
            self.anchor = token
            self.selected = {token}
        self.refresh_token_list()

    def _toggle(self, token):
        if token in self.selected:
            self.selected.discard(token)
        else:
            self.selected.add(token)

    def toggle_token(self, token):
        self._toggle(token)
        self.refresh_token_list()

    def select_all(self):
        self.selected = set(self.store.get_all().keys())
        self.refresh_token_list()

    def invert(self):
        self.selected = set(self.store.get_all().keys()) - self.selected
        self.refresh_token_list()

    def copy_selected_ids(self):
        ids = [self.store.get(t).get("user_id", "") for t in self.selected if self.store.get(t).get("user_id")]
        if ids:
            self.clipboard_put("\n".join(ids))
            self.log(f"Copied {len(ids)} user ID(s)", "info")

    def copy_selected_usernames(self):
        names = [username(self.store.get(t)) for t in self.selected]
        if names:
            self.clipboard_put("\n".join(names))
            self.log(f"Copied {len(names)} username(s)", "info")

    def remove_selected_confirm(self):
        if not self.selected:
            messagebox.showwarning("No Selection", "Select tokens first")
            return
        if messagebox.askyesno("Delete", f"Delete {len(self.selected)} selected token(s)?"):
            for t in list(self.selected):
                self.store.remove_token(t)
            self.selected.clear()
            self.log("Removed selected tokens", "warn")
            self.refresh_all()

    def remove_single_confirm(self, token):
        if messagebox.askyesno("Delete", f"Delete {username(self.store.get(token))}?"):
            self.store.remove_token(token)
            self.selected.discard(token)
            self.log("Removed token", "warn")
            self.refresh_all()

    def token_context(self, event, token):
        if token not in self.selected:
            self.selected = {token}
        info = self.store.get(token)
        menu = tk.Menu(self, tearoff=0)
        menu.add_command(label="Validate", command=lambda: self.validate_single(token))
        menu.add_command(label="Copy Token", command=lambda: self.copy(token))
        menu.add_command(label="Copy User ID", command=lambda: self.clipboard_put(info.get("user_id", "")))
        menu.add_command(label="Copy Username", command=lambda: self.clipboard_put(username(info)))
        menu.add_command(label="Copy Email", command=lambda: self.clipboard_put(info.get("email", "")))
        menu.add_separator()
        menu.add_command(label="Open Profile", command=lambda: self.open_profile(info))
        menu.add_command(label="Export", command=self.export_selected)
        menu.add_separator()
        menu.add_command(label="Delete", command=lambda: self.remove_single_confirm(token))
        try:
            menu.tk_popup(self.winfo_pointerx(), self.winfo_pointery())
        finally:
            menu.grab_release()

    def open_profile(self, info):
        uid = info.get("user_id")
        if uid:
            webbrowser.open(f"https://discord.com/users/{uid}")

    def copy(self, token):
        self.clipboard_put(token)
        self.log("Copied token to clipboard", "info")

    def clipboard_put(self, s):
        self.clipboard_clear()
        self.clipboard_append(s)
        self.update()

    # ---------- SERVERS ----------
    def is_pinned(self, name):
        return name in self.cfg.get("pinned_servers", [])

    def _pin_servers(self):
        return self.cfg.get("pinned_servers", [])

    def toggle_pin(self, name):
        pinned = self.cfg.get("pinned_servers", [])
        if name in pinned:
            pinned.remove(name)
        else:
            pinned.append(name)
        self.cfg.data["pinned_servers"] = pinned
        self.cfg.save()
        self.refresh_servers()

    def refresh_servers(self):
        for w in self.server_list.winfo_children():
            w.destroy()
        smap = self.store.get_server_map()
        query = self.browser_search.get().lower().strip()
        if not smap:
            ctk.CTkLabel(self.server_list, text="No servers found", font=self.F_CAPTION,
                         text_color=MUTED).pack(pady=12)
        pinned = self._pin_servers()
        names = sorted(smap.keys(), key=lambda n: (n not in pinned, n.lower()))
        for name in names:
            if query and query not in name.lower():
                continue
            data = smap[name]
            sel = self.selected_server and self.selected_server["name"] == name
            star = "⭐" if name in pinned else "●"
            btn = ctk.CTkButton(self.server_list, anchor="w", height=38,
                                text=f"{star}  {name}    {len(data['tokens'])}",
                                font=self.F_NORMAL,
                                fg_color=self.acc() if sel else HOVER,
                                hover_color=self.acc_h(),
                                command=lambda n=name: self.select_server(n))
            btn.pack(fill="x", pady=2)
            btn.bind("<Button-3>", lambda e, n=name: self.server_context(e, n))
            btn.bind("<Button-2>", lambda e, n=name: self._copy_server_id(n))
            Tooltip(btn, f"{name}\nTokens: {len(data['tokens'])}\n({data['id']})")
        if self.selected_server:
            smap2 = self.store.get_server_map()
            if self.selected_server["name"] in smap2:
                self._render_members(smap2[self.selected_server["name"]])
            else:
                self.selected_server = None
                self.selected_channel = None
                self._render_members(None)
                self.voice_server_label.configure(text="No server selected", text_color=MUTED)

    def _copy_server_id(self, name):
        smap = self.store.get_server_map()
        if name in smap:
            self.clipboard_put(smap[name]["id"])
            self.log(f"Copied server ID for {name}", "info")

    def server_context(self, event, name):
        smap = self.store.get_server_map()
        if name not in smap:
            return
        gid = smap[name]["id"]
        menu = tk.Menu(self, tearoff=0)
        pin = "Unpin" if self.is_pinned(name) else "Pin"
        menu.add_command(label=pin, command=lambda: self.toggle_pin(name))
        menu.add_command(label="Copy Server ID", command=lambda: self.clipboard_put(gid))
        menu.add_command(label="Copy Name", command=lambda: self.clipboard_put(name))
        menu.add_command(label="Refresh Channels", command=lambda: self.select_server(name))
        menu.add_command(label="Join (set as target)", command=lambda: self.select_server(name))
        try:
            menu.tk_popup(self.winfo_pointerx(), self.winfo_pointery())
        finally:
            menu.grab_release()

    def select_server(self, name):
        smap = self.store.get_server_map()
        data = smap.get(name)
        if not data:
            return
        self.selected_server = {"id": data["id"], "name": name}
        self.selected_channel = None
        self.guild_id_var.set(data["id"])
        self.voice_server_label.configure(text=name, text_color=TXT)
        self.voice_hint.configure(text="Loading channels...")
        self.members_collapsed = False
        self._render_members(data)
        self.refresh_servers()
        if data["tokens"]:
            self.load_channels(data["tokens"][0]["token"], data["id"])
        self._update_server_info()

    def _update_server_info(self):
        if not self.selected_server:
            self.server_info_label.configure(text="")
            return
        name = self.selected_server["name"]
        smap = self.store.get_server_map()
        data = smap.get(name, {})
        created = created_from_id(data.get("id", "0"))
        star = "⭐ Pinned" if self.is_pinned(name) else "●"
        self.server_info_label.configure(
            text=f"{star} {name}  |  ID {data.get('id','')}  |  Created {created}  |  {len(data.get('tokens',[]))} tokens")

    def toggle_members(self):
        self.members_collapsed = not self.members_collapsed
        if self.selected_server:
            smap = self.store.get_server_map()
            data = smap.get(self.selected_server["name"])
            if data:
                self._render_members(data)

    def _render_members(self, data):
        self._current_members = data
        for w in self.server_members.winfo_children():
            w.destroy()
        tokens = data.get("tokens", []) if data else []
        if self.members_collapsed:
            self.members_toggle.configure(text=f"▸  Members ({len(tokens)})")
            self.server_members.pack_forget()
            return
        self.members_toggle.configure(text=f"▾  Members ({len(tokens)})")
        self.server_members.pack(fill="x")
        if not tokens:
            ctk.CTkLabel(self.server_members, text="No tokens", font=self.F_CAPTION,
                         text_color=MUTED).pack(pady=8)
        for m in tokens:
            row = ctk.CTkFrame(self.server_members, fg_color=CARD)
            row.pack(fill="x", pady=2)
            ctk.CTkLabel(row, text=m["username"], font=self.F_CAPTION, anchor="w").pack(side="left", fill="x", expand=True, padx=6, pady=3)
            ctk.CTkButton(row, text="Select", width=60, height=22, font=self.F_CAPTION,
                          fg_color=HOVER, hover_color=self.acc_h(),
                          command=lambda t=m["token"]: self._select_member(t)).pack(side="right", pady=3, padx=4)

    def _select_member(self, token):
        self.selected.add(token)
        self.log(f"Selected {username(self.store.get(token))}", "info")
        self.refresh_token_list()

    def load_channels(self, token, guild_id):
        def worker():
            channels = self._run_async(get_channels(token, guild_id, self.cfg))
            voice = [c for c in channels if c["type"] == 2]
            self.channels = [{"id": c["id"], "name": c["name"]} for c in voice]
            self.after(0, self.render_channels)
        threading.Thread(target=worker, daemon=True).start()

    def render_channels(self):
        for w in self.channel_list.winfo_children():
            w.destroy()
        if not self.channels:
            self.voice_hint.configure(text="No voice channels found")
            return
        self.voice_hint.configure(text="")
        for ch in self.channels:
            sel = self.selected_channel and self.selected_channel["id"] == ch["id"]
            btn = ctk.CTkButton(self.channel_list, anchor="w", height=32,
                                text=f"🔊 {ch['name']}", font=self.F_NORMAL,
                                fg_color=self.acc() if sel else HOVER,
                                hover_color=self.acc_h(),
                                command=lambda c=ch: self.choose_channel(c))
            btn.pack(fill="x", pady=2)
            btn.bind("<Button-3>", lambda e, c=ch: self.channel_context(e, c))
            btn.bind("<Button-2>", lambda e, c=ch: self.clipboard_put(c["id"]))
            Tooltip(btn, f"{ch['name']}\n({ch['id']})")

    def channel_context(self, event, ch):
        menu = tk.Menu(self, tearoff=0)
        menu.add_command(label="Copy Channel ID", command=lambda: self.clipboard_put(ch["id"]))
        menu.add_command(label="Copy Name", command=lambda: self.clipboard_put(ch["name"]))
        menu.add_command(label="Join", command=lambda: self.choose_channel(ch))
        try:
            menu.tk_popup(self.winfo_pointerx(), self.winfo_pointery())
        finally:
            menu.grab_release()

    def choose_channel(self, ch):
        self.selected_channel = ch
        self.channel_id_var.set(ch["id"])
        self.log(f"Selected channel {ch['name']}", "info")
        self.render_channels()

    # ---------- ADVANCED ----------
    def toggle_advanced(self):
        if self.adv_frame.winfo_manager():
            self.adv_button.configure(text="▸  Advanced")
            self.adv_frame.pack_forget()
        else:
            self.adv_button.configure(text="▾  Advanced")
            self.adv_frame.pack(fill="x", pady=(0, 6))

    def _commit_advanced(self):
        try:
            self.cfg.data["delay"] = float(self.delay_var.get())
        except ValueError:
            pass
        try:
            self.cfg.data["concurrency"] = int(self.conc_var.get())
        except ValueError:
            pass
        try:
            self.cfg.data["retry_delay"] = int(self.retry_var.get())
        except ValueError:
            pass
        try:
            self.cfg.data["api_timeout"] = int(self.timeout_var.get())
        except ValueError:
            pass
        self.cfg.save()

    # ---------- RECENT VOICE ----------
    def refresh_recent_voice(self):
        for w in self.recent_voice_frame.winfo_children():
            w.destroy()
        rv = self.cfg.get("recent_voice", [])
        if not rv:
            ctk.CTkLabel(self.recent_voice_frame, text="None yet", font=self.F_CAPTION,
                         text_color=MUTED).pack(anchor="w", padx=6, pady=3)
            return
        for item in rv[:3]:
            ctk.CTkButton(self.recent_voice_frame, text=f"🔊 {item['channel_name']}  ·  {item['guild_name']}",
                          height=22, font=self.F_CAPTION, fg_color=HOVER, hover_color=self.acc_h(),
                          corner_radius=4,
                          command=lambda i=item: self._set_recent_voice(i)).pack(fill="x", pady=1, padx=2)

    def _set_recent_voice(self, item):
        self.guild_id_var.set(item["guild_id"])
        self.channel_id_var.set(item["channel_id"])
        self.selected_server = {"id": item["guild_id"], "name": item["guild_name"]}
        self.selected_channel = {"id": item["channel_id"], "name": item["channel_name"]}
        self.voice_server_label.configure(text=item["guild_name"], text_color=TXT)
        self.log(f"Targeted {item['channel_name']} ({item['guild_name']})", "info")

    def _push_recent_voice(self, guild_id, guild_name, channel_id, channel_name):
        rv = self.cfg.get("recent_voice", [])
        rv.insert(0, {"guild_id": guild_id, "guild_name": guild_name,
                      "channel_id": channel_id, "channel_name": channel_name})
        self.cfg.data["recent_voice"] = rv[:8]
        self.cfg.save()
        self.refresh_recent_voice()

    # ---------- JOIN SERVER ----------
    def paste_invite(self):
        try:
            self.invite_var.set(self.clipboard_get().strip())
        except Exception:
            pass

    def refresh_recent(self):
        for w in self.recent_frame.winfo_children():
            w.destroy()
        if not self.invite_history:
            return
        ctk.CTkLabel(self.recent_frame, text="Recent:", font=self.F_CAPTION,
                     text_color=SEC).pack(side="left", padx=(0, 4))
        for inv in self.invite_history[:4]:
            ctk.CTkButton(self.recent_frame, text=inv, height=20, width=96,
                          font=self.F_CAPTION, fg_color=HOVER, hover_color=self.acc_h(), corner_radius=4,
                          command=lambda i=inv: self.invite_var.set(i)).pack(side="left", padx=3)

    def do_join(self):
        tokens = list(self.selected)
        invite = self.invite_var.get().strip()
        if not tokens:
            messagebox.showwarning("No Selection", "Select tokens first (Token Manager)")
            return
        if not invite:
            messagebox.showwarning("No Invite", "Enter an invite link or code")
            return
        if invite not in self.invite_history:
            self.invite_history.insert(0, invite)
            self.refresh_recent()
        self.log(f"Joining {len(tokens)} token(s) to invite {invite}", "info")
        self._run_batch(tokens, "join", invite=invite)

    # ---------- VOICE ----------
    def do_join_voice(self):
        tokens = list(self.selected)
        if not tokens:
            messagebox.showwarning("No Selection", "Select tokens first (Token Manager)")
            return
        guild_id = self.guild_id_var.get().strip()
        channel_id = self.channel_id_var.get().strip()
        if not guild_id or not channel_id:
            messagebox.showwarning("Missing IDs",
                                   "Enter the Server ID and Voice Channel ID\n(or select a server/channel in the panels)")
            return
        sname = self.selected_server["name"] if self.selected_server else guild_id
        cname = self.selected_channel["name"] if self.selected_channel else channel_id
        self.log(f"Connecting {len(tokens)} token(s) to {cname} ({sname})", "info")
        self._run_batch(tokens, "voice", guild_id=guild_id, channel_id=channel_id,
                        mute=self.mute_var.get(), deaf=self.deaf_var.get())

    def do_rejoin(self):
        rv = self.cfg.get("recent_voice", [])
        if not rv:
            messagebox.showinfo("Rejoin", "No previous voice connection found")
            return
        self._set_recent_voice(rv[0])
        self.do_join_voice()

    def do_join_random(self):
        if not self.channels:
            messagebox.showinfo("Random", "Load channels from a server first")
            return
        ch = random.choice(self.channels)
        self.selected_channel = ch
        self.channel_id_var.set(ch["id"])
        self.render_channels()
        self.do_join_voice()

    def do_leave_voice(self):
        n = 0
        for token in list(self.voice_connections.keys()):
            try:
                self._run_async(self.voice_connections.pop(token).disconnect())
                n += 1
            except Exception:
                pass
        self.log(f"Left voice on {n} token(s)", "warn")
        self.refresh_stats()

    # ---------- BATCH ----------
    def _run_batch(self, tokens, action, **kwargs):
        def worker():
            from concurrent.futures import ThreadPoolExecutor
            delay = float(self.cfg.get("delay", 0.5) or 0)
            with ThreadPoolExecutor(max_workers=self.cfg.get("concurrency", 5)) as ex:
                futs = []
                for t in tokens:
                    futs.append(ex.submit(self._do_action, t, action, **kwargs))
                    if delay > 0:
                        import time as _t
                        _t.sleep(delay)
                for fut in futs:
                    try:
                        msg, kind = fut.result()
                        self.after(0, lambda m=msg, k=kind: self.log(m, k))
                    except Exception as e:
                        self.after(0, lambda: self.log(f"Error: {e}", "error"))
            self.after(0, self.refresh_all)
        threading.Thread(target=worker, daemon=True).start()

    def _do_action(self, token, action, **kwargs):
        uname = username(self.store.get(token))
        if action == "join":
            res = self._run_async(join_server(token, kwargs["invite"], self.cfg))
            if res["success"]:
                info = self.store.get(token)
                servers = info.get("servers", [])
                if not any(s["id"] == res["guild_id"] for s in servers):
                    servers.append({"id": res["guild_id"], "name": res["guild_name"]})
                    self.store.update(token, {"servers": servers})
                return f"{uname} joined {res['guild_name']}", "success"
            return f"{uname}: {res.get('error', '?')}", "error"
        elif action == "voice":
            vc = VoiceConnection(token, self.cfg, on_log=lambda m, k="info": self.log(m, k))
            res = self._run_async(vc.join_voice(kwargs["guild_id"], kwargs["channel_id"],
                                                kwargs.get("mute", False), kwargs.get("deaf", False)))
            if res["success"]:
                self.voice_connections[token] = vc
                gname = self.selected_server["name"] if self.selected_server else kwargs["guild_id"]
                cname = self.selected_channel["name"] if self.selected_channel else kwargs["channel_id"]
                self._push_recent_voice(kwargs["guild_id"], gname, kwargs["channel_id"], cname)
                return f"{uname} connected to {cname}", "success"
            try:
                self._run_async(vc.disconnect())
            except Exception:
                pass
            return f"{uname}: {res.get('error', '?')}", "error"
        return "", "info"

    # ---------- VALIDATION ----------
    def validate_single(self, token):
        threading.Thread(target=lambda: self._validate_worker([token]), daemon=True).start()

    def validate_selected(self):
        tokens = list(self.selected)
        if not tokens:
            messagebox.showwarning("No Selection", "Select tokens first")
            return
        self.log(f"Validating {len(tokens)} selected token(s)", "info")
        threading.Thread(target=lambda: self._validate_worker(tokens), daemon=True).start()

    def validate_all(self):
        tokens = list(self.store.get_all().keys())
        self.foot_status.configure(text="🟡 Validating...", text_color=WARN)
        self.log(f"Validating {len(tokens)} token(s)", "info")
        threading.Thread(target=lambda: self._validate_worker(tokens), daemon=True).start()

    def _validate_worker(self, tokens):
        for token in tokens:
            uname = username(self.store.get(token))
            res = self._run_async(validate_token(token, self.cfg))
            if res.get("valid"):
                self.store.add_token(token, res)
                self.after(0, lambda r=res: self.log(f"{r['username']} valid", "success"))
            else:
                self.store.update(token, {"user_id": "", "error": res.get("error", ""),
                                          "code": res.get("code", "")})
                self.after(0, lambda r=res: self.log(f"{uname}: {r.get('error', '?')}", "error"))
        self.after(0, lambda: (self.refresh_all(),
                               self.foot_status.configure(text="🟢 Ready", text_color=GOOD)))

    # ---------- IMPORT / EXPORT ----------
    def open_import(self):
        self.open_paste(False)

    def open_paste(self, prefill=False):
        win = ctk.CTkToplevel(self)
        win.title("Import Tokens")
        win.geometry("560x440")
        win.transient(self)
        win.configure(fg_color=BG)
        ctk.CTkLabel(win, text="IMPORT TOKENS", font=self.F_SECTION, text_color=SEC).pack(anchor="w", padx=14, pady=(14, 6))
        box = ctk.CTkTextbox(win, height=250, fg_color=CARD, border_width=0, font=self.F_NORMAL)
        box.pack(fill="both", expand=True, padx=14, pady=6)
        if prefill:
            try:
                box.insert("1.0", self.clipboard_get())
            except Exception:
                pass
        def do_file():
            path = filedialog.askopenfilename(parent=win)
            if path:
                try:
                    with open(path, "r", encoding="utf-8") as f:
                        box.delete("1.0", "end")
                        box.insert("1.0", f.read())
                except Exception as e:
                    messagebox.showerror("Error", str(e), parent=win)
        def submit():
            self._import_lines(box.get("1.0", "end").splitlines(), win)
        row = ctk.CTkFrame(win, fg_color="transparent")
        row.pack(fill="x", padx=14, pady=10)
        ctk.CTkButton(row, text="📂 File", command=do_file, width=110, fg_color=HOVER,
                      hover_color=self.acc_h(), height=32, font=self.F_NORMAL).pack(side="left", padx=4)
        ctk.CTkButton(row, text="📋 Clipboard", command=lambda: box.insert("1.0", self._clip()),
                      width=110, fg_color=HOVER, hover_color=self.acc_h(), height=32, font=self.F_NORMAL).pack(side="left", padx=4)
        ctk.CTkButton(row, text="📥 Import", command=submit, width=110, fg_color=self.acc(),
                      hover_color=self.acc_h(), height=32, font=self.F_NORMAL).pack(side="left", padx=4)

    def _clip(self):
        try:
            return self.clipboard_get()
        except Exception:
            return ""

    def import_file(self):
        path = filedialog.askopenfilename(parent=self)
        if path:
            try:
                with open(path, "r", encoding="utf-8") as f:
                    self._import_lines(f.read().splitlines(), self)
            except Exception as e:
                messagebox.showerror("Error", str(e))

    def _import_lines(self, raw, parent):
        tokens = []
        for line in raw:
            line = line.strip()
            if line and line not in tokens:
                tokens.append(line)
        if not tokens:
            messagebox.showwarning("Empty", "No tokens found", parent=parent)
            return
        self.foot_status.configure(text="🟡 Importing...", text_color=WARN)
        self.log(f"Analyzing {len(tokens)} token(s)...", "info")
        if isinstance(parent, ctk.CTkToplevel):
            parent.destroy()

        existing = set(self.store.get_all().keys())
        def worker():
            added = 0
            for token in tokens:
                if token in existing:
                    continue
                res = self._run_async(validate_token(token, self.cfg))
                if res.get("valid"):
                    self.store.add_token(token, res)
                    added += 1
                    self.after(0, lambda r=res: self.log(f"{r['username']} imported", "success"))
                else:
                    self.store.add_token(token, {"user_id": "", "error": res.get("error", "")})
                    self.after(0, lambda r=res: self.log(f"Rejected: {r.get('error', '?')}", "error"))
            self.after(0, lambda: (self.refresh_all(),
                                   self.foot_status.configure(text="🟢 Ready", text_color=GOOD),
                                   self.status_label.configure(text=f"Imported {added}"),
                                   messagebox.showinfo("Done", f"Imported {added} valid token(s)")))
        threading.Thread(target=worker, daemon=True).start()

    def export_tokens(self):
        path = filedialog.asksaveasfilename(parent=self, defaultextension=".json",
                                            filetypes=[("JSON", "*.json")])
        if path:
            with open(path, "w", encoding="utf-8") as f:
                json.dump(self.store.get_all(), f, indent=2, ensure_ascii=False)
            self.log(f"Exported {len(self.store.get_all())} tokens", "success")

    def export_selected(self):
        data = {t: self.store.get(t) for t in self.selected}
        path = filedialog.asksaveasfilename(parent=self, defaultextension=".json",
                                            filetypes=[("JSON", "*.json")])
        if path:
            with open(path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            self.log(f"Exported {len(data)} selected token(s)", "success")

    # ---------- SETTINGS ----------
    def open_settings(self):
        win = ctk.CTkToplevel(self)
        win.title("Settings")
        win.geometry("460x640")
        win.transient(self)
        win.configure(fg_color=BG)
        ctk.CTkLabel(win, text="SETTINGS", font=self.F_SECTION, text_color=SEC).pack(anchor="w", padx=14, pady=(14, 2))

        def field(label, var, tip=None):
            ctk.CTkLabel(win, text=label, font=self.F_CAPTION, text_color=SEC).pack(anchor="w", padx=14, pady=(8, 2))
            e = ctk.CTkEntry(win, textvariable=var, width=300, height=30, fg_color=CARD,
                             border_width=0, font=self.F_NORMAL)
            e.pack(anchor="w", padx=14)
            if tip:
                Tooltip(e, tip)

        accent_var = tk.StringVar(value=self.cfg.get("accent", "blue"))
        ctk.CTkLabel(win, text="Accent", font=self.F_CAPTION, text_color=SEC).pack(anchor="w", padx=14, pady=(8, 2))
        ctk.CTkOptionMenu(win, values=list(ACCENTS.keys()), variable=accent_var, width=160, height=28,
                          fg_color=CARD, font=self.F_NORMAL).pack(anchor="w", padx=14)

        conc_var = tk.StringVar(value=str(self.cfg.get("concurrency", 5)))
        field("Concurrency (parallel workers)", conc_var)
        retry_var = tk.StringVar(value=str(self.cfg.get("retry_delay", 3)))
        field("Retry Delay (seconds)", retry_var)
        timeout_var = tk.StringVar(value=str(self.cfg.get("api_timeout", 10)))
        field("API Timeout (seconds)", timeout_var)
        delay_var = tk.StringVar(value=str(self.cfg.get("delay", 0.5)))
        field("Action Delay (seconds)", delay_var)
        proxy_var = tk.StringVar(value=self.cfg.get("proxy", ""))
        field("Proxy (http://ip:port)", proxy_var)

        show_badges = tk.BooleanVar(value=self.cfg.get("show_badges", True))
        show_ids = tk.BooleanVar(value=self.cfg.get("show_ids", True))
        compact = tk.BooleanVar(value=self.cfg.get("compact", False))
        auto_save = tk.BooleanVar(value=self.cfg.get("auto_save", True))
        for label, var in [("Show Badges", show_badges), ("Show IDs", show_ids),
                           ("Compact Token Cards", compact), ("Auto Save", auto_save)]:
            ctk.CTkCheckBox(win, text=label, variable=var, font=self.F_NORMAL,
                            fg_color=ACCENT, hover_color=ACCENT_HOVER).pack(anchor="w", padx=14, pady=3)

        def save():
            try:
                self.cfg.data["accent"] = accent_var.get()
                self.cfg.data["concurrency"] = int(conc_var.get())
                self.cfg.data["retry_delay"] = int(retry_var.get())
                self.cfg.data["api_timeout"] = int(timeout_var.get())
                self.cfg.data["delay"] = float(delay_var.get())
                self.cfg.data["proxy"] = proxy_var.get()
                self.cfg.data["show_badges"] = show_badges.get()
                self.cfg.data["show_ids"] = show_ids.get()
                self.cfg.data["compact"] = compact.get()
                self.cfg.data["auto_save"] = auto_save.get()
                self.cfg.save()
                self.refresh_all()
                self.delay_var.set(self.cfg.data["delay"])
                self.conc_var.set(str(self.cfg.data["concurrency"]))
                self.retry_var.set(str(self.cfg.data["retry_delay"]))
                self.timeout_var.set(str(self.cfg.data["api_timeout"]))
                self.log("Settings saved", "success")
                win.destroy()
            except ValueError:
                messagebox.showerror("Invalid", "Numbers must be numeric", parent=win)

        ctk.CTkButton(win, text="Save", command=save, height=36, fg_color=self.acc(),
                      hover_color=self.acc_h(), font=self.F_NORMAL).pack(padx=14, pady=10, fill="x")

    def open_about(self):
        messagebox.showinfo(
            "About",
            "Discord Token Manager\n\n"
            "Validate tokens, manage servers, and connect to voice channels.\n"
            "All data is stored locally in your AppData folder.\n\n"
            "Shortcuts: Ctrl+I import · Ctrl+V paste · Ctrl+R refresh ·\n"
            "Ctrl+F search · Ctrl+A select all · Delete remove · Ctrl+C copy IDs\n"
            "Double-click token = rejoin voice · Middle-click = copy ID",
        )

    def _run_async(self, coro):
        try:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            return loop.run_until_complete(coro)
        finally:
            loop.close()


if __name__ == "__main__":
    app = App()
    app.mainloop()