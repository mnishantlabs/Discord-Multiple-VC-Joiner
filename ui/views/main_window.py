"""Top-level application window and shared context.

This replaces the old ~1400-line ``App`` God class. ``MainWindow`` composes a
set of independent view classes (toolbar, stats, tokens, servers, voice,
actions, log, status) that each read from the shared :class:`AppContext`. The
views hold no domain state of their own; they render from the observable
``AppState`` and repositories, and initiate work via the bundled services.

Nothing here hard-codes per-widget layout beyond composing the panels; the
details live in each view class.
"""

import threading
import tkinter as tk

import customtkinter as ctk

from core.events import (
    EventBus,
    STORE_CHANGED,
    SELECTION_CHANGED,
    VALIDATION_PROGRESS,
    VOICE_STATE_CHANGED,
)
from controllers.actions import ActionsController
from services.app_state import AppState
from services.logging_service import LogService
from services.settings_service import SettingsService
from storage.token_repository import TokenRepository
from ui import theme
from utils.asyncs import AsyncBridge

# Adaptive sizing: the window shrinks to fit whatever screen it opens on.
DEFAULT_SIZE = (1380, 880)
MIN_SIZE = (760, 580)

# Resizable three-column layout. Panes are placed in grid columns
# 0 / 2 / 4 with a thin draggable sash in columns 1 / 3. Each pane keeps a
# minimum width and the user's proportions persist between sessions.
SASH_W = 6
MIN_ACCOUNTS = 170
MIN_SERVERS = 210
MIN_VOICE = 170
PANE_MINS = (MIN_ACCOUNTS, MIN_SERVERS, MIN_VOICE)
DEFAULT_PANE_FRACS = (0.27, 0.44, 0.29)

# Font size levels used by `_font_scale()`.
FONT_SIZES = {0: 12, 1: 13, 2: 15}


def frame(parent, color=theme.BG):
    """A plain centered-tk Frame with the app background color."""
    return tk.Frame(parent, bg=color)


class AppContext:
    """Shared services/state/fonts handed to every view."""

    def __init__(self, bridge, bus, state, store, settings, log, fonts) -> None:
        self.bridge: AsyncBridge = bridge
        self.bus: EventBus = bus
        self.state: AppState = state
        self.store: TokenRepository = store
        self.settings: SettingsService = settings
        self.log: LogService = log
        self.fonts: dict = fonts
        # Populated during MainWindow._init_modules():
        self.client = None
        self.validation = None
        self.join = None
        self.channels = None
        self.import_export = None
        self.voice = None
        self.actions = None
        # Populated during MainWindow._create_views():
        self.tokens_view = None
        self.servers_view = None
        self.voice_view = None

    @property
    def accent(self) -> str:
        return theme.ACCENTS.get(self.settings.accent, theme.ACCENT)

    @property
    def accent_hover(self) -> str:
        return theme.ACCENT_HOVERS.get(self.settings.accent, theme.ACCENT_HOVER)

    def username(self, info: dict) -> str:
        return f"{info.get('username', '?')}#{info.get('discriminator', '0')}"


class MainWindow(ctk.CTk):
    """Top-level Tk window; composes the view columns and wires services."""

    def __init__(self) -> None:
        super().__init__()
        self._init_modules()

    # ------------------------------------------------------------------
    def _init_modules(self) -> None:
        from storage.settings_repository import SettingsRepository

        bus = EventBus()
        self.bridge = AsyncBridge()
        self.store = TokenRepository()
        self.settings = SettingsService(SettingsRepository(), bus)
        ctk.set_appearance_mode(self.settings.get("appearance_mode", "dark"))
        self.log = LogService(bus)
        self.ctx = AppContext(
            bridge=self.bridge,
            bus=bus,
            state=AppState(),
            store=self.store,
            settings=self.settings,
            log=self.log,
            fonts=theme.build_fonts(ctk, size_normal=self._font_scale()),
        )

        from services.discord_client import DiscordClient
        from services.validation_service import ValidationService
        from services.join_service import JoinService
        from services.channel_service import ChannelService
        from services.voice_service import VoiceService
        from services.import_export_service import ImportExportService

        client = DiscordClient(self.settings_repo_backend())
        self.ctx.client = client
        self.ctx.validation = ValidationService(
            self.bridge, bus, client, self.store, self.log.log,
        )
        self.ctx.join = JoinService(self.bridge, bus, client, self.store, self.log.log)
        self.ctx.channels = ChannelService(self.bridge, bus, client, self.log.log)
        self.ctx.voice = VoiceService(self.bridge, bus, self.settings_repo_backend(), self.log.log)
        self.ctx.import_export = ImportExportService(
            self.bridge, bus, self.store, self.ctx.validation, self.log.log,
        )
        self.ctx.actions = ActionsController(
            self.ctx, self.ctx.voice, self.log.log,
        )

        self._start_client(client)

        self._configure_window()
        self._create_views()
        self._subscribe()
        bus.set_scheduler(self._schedule_main)
        self.after(0, self._startup)

    def _start_client(self, client) -> None:
        """Create the shared aiohttp session on the async loop (fire-and-forget)."""

        def _done(fut) -> None:
            try:
                fut.result()
            except Exception as exc:  # noqa: BLE001
                try:
                    self.log.log(f"Client start failed: {exc}", "error")
                except Exception:
                    pass

        fut = self.bridge.submit(client.start())
        fut.add_done_callback(_done)

    def settings_repo_backend(self):
        # The SettingsService wraps a repository that also backs the client /
        # voice service. To avoid duplicated config-file writers we expose the
        # underlying repository.
        return self.settings._repo

    def _schedule_main(self, thunk) -> None:
        try:
            if self.winfo_exists():
                self.after(0, thunk)
        except Exception:
            pass

    def _configure_window(self) -> None:
        self.configure(fg_color=theme.BG)
        self.title("Discord Token Manager")
        sw, sh = self.winfo_screenwidth(), self.winfo_screenheight()
        saved = self.ctx.settings.geometry
        if saved and self._geometry_fits(saved, sw, sh):
            geometry = saved
        else:
            geometry = self._adaptive_geometry(sw, sh)
        try:
            self.geometry(geometry)
        except Exception:
            self.geometry(f"{DEFAULT_SIZE[0]}x{DEFAULT_SIZE[1]}")
        self.minsize(min(MIN_SIZE[0], sw), min(MIN_SIZE[1], sh))
        self.protocol("WM_DELETE_WINDOW", self.on_close)

    @staticmethod
    def _geometry_fits(geometry: str, sw: int, sh: int) -> bool:
        """Accept a saved geometry only if it is a sane window (not smaller
        than our minimum) and does not overflow the current screen."""
        try:
            w, h = geometry.split("+", 1)[0].lower().split("x")
            w, h = int(w), int(h)
        except Exception:
            return False
        return MIN_SIZE[0] <= w <= sw and MIN_SIZE[1] <= h <= sh

    @staticmethod
    def _adaptive_geometry(sw: int, sh: int) -> str:
        w = min(DEFAULT_SIZE[0], max(MIN_SIZE[0], sw - 80))
        h = min(DEFAULT_SIZE[1], max(MIN_SIZE[1], sh - 100))
        x = max(0, (sw - w) // 2)
        y = max(0, (sh - h) // 3)
        return f"{w}x{h}+{x}+{y}"

    def _load_pane_fracs(self) -> list[float]:
        fracs = self.ctx.settings.columns_layout
        if fracs is None:
            return list(DEFAULT_PANE_FRACS)
        total = sum(fracs)
        return [f / total for f in fracs]

    def _make_sash(self, index: int) -> tk.Frame:
        """A thin vertical grab bar between panes. Click-drag resizes;
        double-click resets to the default layout."""
        sash = frame(self._body, color=theme.HOVER)
        sash.configure(cursor="sb_h_double_arrow")
        sash._sash_index = index
        sash.bind("<ButtonPress-1>", self._sash_press)
        sash.bind("<B1-Motion>", self._sash_drag)
        sash.bind("<ButtonRelease-1>", self._sash_release)
        sash.bind("<Double-Button-1>", self._sash_reset)
        return sash

    def _sash_press(self, event) -> None:
        self._drag = {
            "index": getattr(event.widget, "_sash_index", 0),
            "start_x": self._body.winfo_pointerx(),
            "fracs": list(self._pane_fracs),
            "moved": False,
        }

    def _sash_drag(self, event) -> None:
        if not self._drag:
            return
        started = self._drag["start_x"]
        delta = (self._body.winfo_pointerx() - started) / max(1, self._body.winfo_width())
        self._drag["moved"] = True
        self._apply_delta(self._drag["index"], self._drag["fracs"], delta)

    def _sash_release(self, _event=None) -> None:
        if not self._drag:
            return
        if self._drag["moved"]:
            self._place_panes()
            self._persist_pane_fracs()
        self._drag = None

    def _sash_reset(self, _event=None) -> None:
        self._drag = None
        self._pane_fracs = list(DEFAULT_PANE_FRACS)
        self._place_panes()
        self._persist_pane_fracs()

    def _apply_delta(self, index: int, base, delta: float) -> None:
        """Shift the divider: pane ``index`` grows, ``index+1`` shrinks, with
        per-pane minimum widths clamped on the body's real width."""
        bw = self._body.winfo_width()
        total_avail = bw - 2 * SASH_W
        mins = list(PANE_MINS)

        fracs = list(base)
        p0 = max(mins[index] / total_avail, min(0.999, fracs[index] + delta))
        p1 = fracs[index + 1] - (p0 - fracs[index])
        if p1 < mins[index + 1] / total_avail:
            p1 = mins[index + 1] / total_avail
            p0 = fracs[index] + fracs[index + 1] - p1
        fracs[index] = p0
        fracs[index + 1] = p1
        self._pane_fracs = fracs
        self._place_panes()

    def _on_body_configure(self, _event=None) -> None:
        if self._drag:
            return
        if getattr(self, "_layout_guard", False):
            return
        self._layout_guard = True
        try:
            self._place_panes()
        finally:
            self._layout_guard = False

    def _applied_widths(self):
        return [int(f.winfo_width()) for f in self._panes]

    def _compute_widths(self, body_w: int) -> list[int]:
        """Three pane widths (plus sashes) from the user's fractions, clamped
        to per-pane minimums that sum to the available body width."""
        total_avail = max(1, body_w - 2 * SASH_W)
        mins = list(PANE_MINS)
        fracs = self._pane_fracs
        widths = [int(total_avail * f / max(1.0, sum(fracs))) for f in fracs]
        for i in range(3):
            if widths[i] < mins[i]:
                width_i = mins[i]
                j = max((k for k in range(3) if k != i),
                        key=lambda k: widths[k] - mins[k])
                deficit = width_i - widths[i]
                widths[i] = width_i
                widths[j] -= deficit
        surplus = sum(widths) - total_avail
        if surplus > 0:
            widths[max(range(3), key=lambda k: widths[k])] -= surplus
        for i in range(3):
            widths[i] = max(mins[i], widths[i])
        return [int(w) for w in widths]

    def _place_panes(self) -> None:
        """Exact geometry via .place() — fully controls each pane's width
        regardless of the requested size of its children. Idempotent: no-op
        when the pane widths are already correct."""
        bw = self._body.winfo_width()
        if bw <= 0:
            return
        widths = self._compute_widths(bw)
        if widths == self._applied_widths():
            return
        heights = self._body.winfo_height()
        x = 0
        for i in range(3):
            if i > 0:
                self._sashes[i - 1].place(x=x, y=0, width=SASH_W, height=heights)
                x += SASH_W
            self._panes[i].place(x=x, y=0, width=widths[i], height=heights)
            x += widths[i]

    def _persist_pane_fracs(self) -> None:
        try:
            self.ctx.settings.set_columns_layout(self._pane_fracs)
        except Exception:
            pass

    def _create_views(self) -> None:
        from ui.views.toolbar import ToolbarView
        from ui.views.stats_bar import StatsBarView
        from ui.views.tokens_view import TokensView
        from ui.views.servers_view import ServersView
        from ui.views.voice_view import VoiceView
        from ui.views.actions_bar import ActionsBarView
        from ui.views.log_view import LogView
        from ui.views.status_bar import StatusBarView

        self.toolbar = ToolbarView(self, self.ctx)
        self.toolbar.pack(fill="x", padx=theme.PAD_OUTER, pady=(8, 2))

        stats_holder = frame(self)
        stats_holder.pack(fill="x", padx=theme.PAD_OUTER, pady=(4, 10))
        self.stats = StatsBarView(stats_holder, self.ctx)
        self.stats.pack(fill="x")

        self._body = frame(self)
        self._body.pack(fill="both", expand=True, padx=theme.PAD_OUTER, pady=4)

        self._pane_fracs = self._load_pane_fracs()
        self._drag = None

        self._holders = [frame(self._body) for _ in range(3)]
        self.tokens_view = TokensView(self._holders[0], self.ctx)
        self.servers_view = ServersView(self._holders[1], self.ctx)
        self.voice_view = VoiceView(self._holders[2], self.ctx)
        self.tokens_view.pack(fill="both", expand=True, in_=self._holders[0])
        self.servers_view.pack(fill="both", expand=True, in_=self._holders[1])
        self.voice_view.pack(fill="both", expand=True, in_=self._holders[2])
        self.ctx.tokens_view = self.tokens_view
        self.ctx.servers_view = self.servers_view
        self.ctx.voice_view = self.voice_view

        self._panes = self._holders
        self._sashes = [self._make_sash(0), self._make_sash(1)]

        self._body.bind("<Configure>", self._on_body_configure)
        self._place_panes()

        self.actions = ActionsBarView(self, self.ctx)
        self.actions.pack(fill="x", padx=theme.PAD_OUTER, pady=(0, 10))

        self.log_view = LogView(self, self.ctx)
        self.log_view.pack(fill="x", padx=theme.PAD_OUTER, pady=(0, 4))

        self.status = StatusBarView(self, self.ctx)
        self.status.pack(fill="x", side="bottom")

    def _subscribe(self) -> None:
        self.ctx.bus.subscribe(STORE_CHANGED, lambda _: self.refresh_all())
        self.ctx.bus.subscribe(STORE_CHANGED, lambda _: self.stats.set_validating(False))
        self.ctx.bus.subscribe(STORE_CHANGED, lambda _: self.actions.render())
        self.ctx.bus.subscribe(SELECTION_CHANGED, lambda _: self.tokens_view.render())
        self.ctx.bus.subscribe(SELECTION_CHANGED, lambda _: self.actions.render())
        self.ctx.bus.subscribe(STORE_CHANGED, lambda _: self.status.render())
        self.ctx.bus.subscribe(VALIDATION_PROGRESS, lambda p: self._on_validation(p))
        self.ctx.bus.subscribe(VALIDATION_PROGRESS, lambda _p: self.stats.set_validating(True))
        self.ctx.bus.subscribe(VOICE_STATE_CHANGED, lambda _: self.status.render())

    def _on_validation(self, payload) -> None:
        self._update_validation_progress(payload)
        self.refresh_all()
        self.stats.set_validating(True)

    def _update_validation_progress(self, payload) -> None:
        """Forward (done, total) to the stats bar compact progress row."""
        try:
            done, total = payload
            pct = (done / total) if total else 0.0
            self.stats.progress.set(pct)
            self.stats._progress_label.configure(text=f"{done} / {total}  {int(pct * 100)}%")
        except Exception:
            pass

    def _startup(self) -> None:
        self._bind_shortcuts()
        self.apply_appearance()
        self.refresh_all()
        self._spawn_api_check()
        if self.ctx.settings.get("auto_validate", False):
            self.after(400, self.tokens_view.validate_all)

    def _font_scale(self) -> int:
        size = self.settings.get("font_size", 1)
        return FONT_SIZES.get(size, 13)

    def apply_appearance(self) -> None:
        """Apply theme mode + native backdrop. Font size is baked into the
        font dict at startup, so a live change needs an app restart."""
        mode = self.ctx.settings.get("appearance_mode", "dark")
        ctk.set_appearance_mode(mode)
        try:
            from ui.effects import apply_backdrop
            apply_backdrop(self, self.ctx.settings.get("transparency", "off"))
        except Exception:
            pass

    def delete_selected(self) -> None:
        if not self.ctx.state.selected:
            self.ctx.log.warning("No selection")
            return
        from tkinter import messagebox
        if messagebox.askyesno("Delete", f"Delete {len(self.ctx.state.selected)} selected token(s)?"):
            for t in list(self.ctx.state.selected):
                self.ctx.store.remove_token(t)
            self.ctx.state.clear_selection()
            self.ctx.log.warning("Removed selected tokens")
            self.refresh_all()

    def open_command_palette(self) -> None:
        from ui.dialogs.command_palette import CommandPalette
        CommandPalette(self).show()

    def _bind_shortcuts(self) -> None:
        from controllers.shortcuts import SHORTCUTS, bind_shortcuts, register_defaults

        def in_input() -> bool:
            w = self.focus_get()
            return isinstance(w, (tk.Entry, tk.Text))

        def focus_search() -> None:
            self.tokens_view.search_entry.focus_set()
            self.tokens_view.search_entry.select_range(0, "end")

        def delete_selected() -> None:
            if in_input():
                return
            self.delete_selected()

        def copy_ids() -> None:
            if in_input():
                return
            ids = []
            for token in self.ctx.state.selected:
                uid = self.ctx.store.get(token).get("user_id", "")
                if uid:
                    ids.append(uid)
            if ids:
                from utils.clipboard import clip_set
                clip_set(self, "\n".join(ids))
                self.ctx.log.info(f"Copied {len(ids)} user ID(s)")

        def copy_usernames() -> None:
            if in_input():
                return
            names = [self.ctx.username(self.ctx.store.get(t)) for t in self.ctx.state.selected]
            if names:
                from utils.clipboard import clip_set
                clip_set(self, "\n".join(names))
                self.ctx.log.info(f"Copied {len(names)} username(s)")

        def join_voice() -> None:
            if in_input():
                return
            self.ctx.actions.join_selected()

        def select_all_guarded() -> None:
            if not in_input():
                self.tokens_view.select_all()

        register_defaults({
            "refresh": self.refresh_all,
            "import_": self.toolbar.open_paste,
            "search": focus_search,
            "select_all": select_all_guarded,
            "delete": delete_selected,
            "join_voice": join_voice,
            "copy_ids": copy_ids,
        })
        bind_shortcuts(self, SHORTCUTS)
        self.bind("<Control-v>", lambda _e: self._paste_shortcut())
        self.bind("<Control-Shift-C>", lambda _e: copy_usernames())
        self.bind("<Control-Shift-P>", lambda _e: self.open_command_palette())

    def _paste_shortcut(self) -> None:
        w = self.focus_get()
        if isinstance(w, (tk.Entry, tk.Text)):
            return
        self.toolbar.open_paste()

    def _spawn_api_check(self) -> None:
        def worker():
            try:
                ok = self._check_api_now()
            except Exception:
                ok = False
            try:
                if self.winfo_exists():
                    self.after(0, lambda: self.status.set_api(ok))
            except Exception:
                pass
        threading.Thread(target=worker, daemon=True).start()

    def _check_api_now(self) -> bool:
        return bool(self.ctx.bridge.submit(_ping()).result(timeout=5))

    # ---- refresh / actions -------------------------------------------------------
    def refresh_all(self) -> None:
        self.stats.render()
        self.tokens_view.render()
        self.servers_view.render()
        self.voice_view.render()

    def on_close(self) -> None:
        try:
            self.ctx.settings.set_geometry(self.geometry())
        except Exception:
            pass
        try:
            self.ctx.voice.disconnect_all()
        except Exception:
            pass
        try:
            self.bridge.shutdown(timeout=2)
        except Exception:
            pass
        self.destroy()


async def _ping():
    import aiohttp
    from core.constants import API_BASE, HEADERS
    try:
        async with aiohttp.ClientSession() as s:
            async with s.get(f"{API_BASE}/gateway", headers=HEADERS) as r:
                return 200 <= r.status < 500
    except Exception:
        return False