"""Bottom status bar: status, token/server/foot counts, memory, voice, API, clock."""

import tkinter as tk

import customtkinter as ctk

from ui import theme


def process_memory_mb() -> float:
    """Return current process working-set size in MB (Windows-only, graceful)."""
    try:
        import ctypes
        from ctypes import wintypes, c_size_t

        class RMM(ctypes.Structure):
            _fields_ = [
                ("hProcess", wintypes.HANDLE),
                ("cb", wintypes.DWORD),
                ("PageFaultCount", wintypes.DWORD),
                ("PeakWorkingSetSize", c_size_t),
                ("WorkingSetSize", c_size_t),
                ("QuotaPeakPagedPoolUsage", c_size_t),
                ("QuotaPagedPoolUsage", c_size_t),
                ("QuotaPeakNonPagedPoolUsage", c_size_t),
                ("QuotaNonPagedPoolUsage", c_size_t),
            ]

        pmi = RMM()
        psapi = ctypes.windll.psapi
        h = ctypes.windll.kernel32.GetCurrentProcess()
        psapi.K32GetProcessMemoryInfo(h, ctypes.byref(pmi), ctypes.sizeof(pmi))
        return pmi.WorkingSetSize / (1024 * 1024)
    except Exception:
        return 0.0


def _now() -> str:
    from datetime import datetime
    return datetime.now().strftime("%H:%M:%S")


class StatusBarView:
    """Renders counts, voice state, api status, memory, and a running clock."""

    def __init__(self, parent, ctx) -> None:
        self.ctx = ctx
        bar = ctk.CTkFrame(parent, fg_color=theme.CARD, corner_radius=0, height=26)
        self._frame = bar
        inner = ctk.CTkFrame(bar, fg_color="transparent")
        inner.pack(fill="x", padx=16, pady=2)

        self.foot_status = ctk.CTkLabel(inner, text="🟢 Ready", font=ctx.fonts["caption"], text_color=theme.GOOD)
        self.foot_status.pack(side="left", padx=10)
        self.foot_tokens = ctk.CTkLabel(inner, text="👤 0 Tokens", font=ctx.fonts["caption"], text_color=theme.SEC)
        self.foot_tokens.pack(side="left", padx=10)
        self.foot_servers = ctk.CTkLabel(inner, text="🖥 0 Servers", font=ctx.fonts["caption"], text_color=theme.SEC)
        self.foot_servers.pack(side="left", padx=10)
        self.mem_label = ctk.CTkLabel(inner, text="🧠 -- MB", font=ctx.fonts["caption"], text_color=theme.SEC)
        self.mem_label.pack(side="left", padx=10)
        self.foot_voice = ctk.CTkLabel(inner, text="📶 Idle", font=ctx.fonts["caption"], text_color=theme.SEC)
        self.foot_voice.pack(side="left", padx=10)

        self.api_status = ctk.CTkLabel(inner, text="● Checking...", font=ctx.fonts["caption"], text_color=theme.WARN)
        self.api_status.pack(side="right", padx=10)
        self.time_label = ctk.CTkLabel(inner, text=_now(), font=ctx.fonts["caption"], text_color=theme.SEC)
        self.time_label.pack(side="right", padx=10)

        self._tick_count = 0
        self._start_tick()

    def pack(self, *args, **kwargs) -> None:
        self._frame.pack(*args, **kwargs)

    def _start_tick(self) -> None:
        def tick() -> None:
            self._tick_count += 1
            self.time_label.configure(text=_now())
            if self._tick_count % 5 == 0:
                self.mem_label.configure(text=f"🧠 {process_memory_mb():.0f} MB")
            if self._frame.winfo_exists():
                self._frame.after(1000, tick)
        self._frame.after(1000, tick)

    def render(self) -> None:
        tokens = self.ctx.store.get_all()
        servers = {s["id"] for _, info in tokens.items() for s in info.get("servers", [])}
        self.foot_tokens.configure(text=f"👤 {len(tokens)} Tokens")
        self.foot_servers.configure(text=f"🖥 {len(servers)} Servers")
        connected = 0
        try:
            connected = self.ctx.voice.connected_count if self.ctx.voice else 0
        except Exception:
            connected = 0
        self.foot_voice.configure(text=f"📶 {connected} Connected" if connected else "📶 Idle")

    def set_api(self, ok: bool) -> None:
        self.api_status.configure(
            text="● API: Online" if ok else "● API: Offline",
            text_color=theme.GOOD if ok else theme.DANGER,
        )