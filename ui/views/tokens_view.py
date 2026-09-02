"""Token manager panel: search, All/Valid/Invalid filter, sort, grouped compact
token list, selection (shift/ctrl/plain, accent ring instead of checkboxes),
context menu, and validate-all. Per-account details moved to the
double-click Properties dialog.

Deliberately uses a CTk ``ScrollableFrame`` with grouped headers (group row
and token-row heights differ, so a uniform-height virtual list is not a fit).
The old performance bug was a full widget rebuild on *every* keystroke; that
is fixed here by debouncing search re-renders (only minor highlight work per
keystroke, a full rebuild after the user stops typing).
"""

import tkinter as tk

import customtkinter as ctk

from core.enums import SortMode, TokenStatus, TokenCategory, CATEGORY_ORDER, CATEGORY_LABELS
from core.predicates import status, categorize, pass_filters, match_search
from ui import theme
from ui.widgets import TokenCard, Tooltip, build_token_tooltip
from ui.widgets.token_card import CARD_HEIGHTS
from utils.clipboard import clip_set
from utils.platform import MOD_CTRL, MOD_SHIFT

SEARCH_DEBOUNCE_MS = 180

FILTER_LABELS = [("All", "all"), ("Valid", "valid"), ("Invalid", "invalid")]


class TokensView:
    def __init__(self, parent, ctx) -> None:
        self.ctx = ctx
        root = ctk.CTkFrame(parent, fg_color=theme.CARD, corner_radius=theme.RADIUS_PANEL)
        self._frame = root

        head = ctk.CTkFrame(root, fg_color="transparent")
        head.pack(fill="x", padx=theme.PAD_PANEL, pady=(10, 8))
        ctk.CTkLabel(head, text="👤 ACCOUNTS", font=ctx.fonts["section"],
                     text_color=theme.SEC).pack(side="left")

        body = ctk.CTkFrame(root, fg_color="transparent")
        body.pack(fill="both", expand=True, padx=theme.PAD_PANEL, pady=(0, 12))

        self.search_var = tk.StringVar()
        self.search_var.trace_add("write", lambda *a: self._on_search())
        self.search_entry = ctk.CTkEntry(body, textvariable=self.search_var,
                                         placeholder_text="🔍  Search accounts…", height=32,
                                         corner_radius=theme.RADIUS_CTRL, fg_color=theme.BG, border_width=0,
                                         font=ctx.fonts["normal"])
        self.search_entry.pack(fill="x", pady=(0, 6))

        row1 = ctk.CTkFrame(body, fg_color="transparent")
        row1.pack(fill="x", pady=(0, 8))
        ctk.CTkButton(row1, text="☑", command=self.select_all, width=22, height=24,
                      fg_color=theme.HOVER, hover_color=ctx.accent_hover,
                      corner_radius=5).pack(side="left", padx=1)
        ctk.CTkButton(row1, text="⇄", command=self.invert, width=22, height=24,
                      fg_color=theme.HOVER, hover_color=ctx.accent_hover,
                      corner_radius=5).pack(side="left", padx=1)

        self._filter_btns = {}
        for name, key in FILTER_LABELS:
            btn = ctk.CTkButton(row1, text=name, width=46, height=24,
                                font=ctx.fonts["caption"], corner_radius=theme.RADIUS_CTRL,
                                command=lambda k=key: self._set_view_filter(k))
            btn.pack(side="left", padx=1)
            self._filter_btns[key] = btn

        self.sort_var = tk.StringVar(value=SortMode.SERVER_COUNT.value)
        ctk.CTkOptionMenu(row1, values=[s.value for s in SortMode], variable=self.sort_var,
                          command=lambda *a: self.render(), width=100, height=24,
                          font=ctx.fonts["caption"], fg_color=theme.BG,
                          button_color=theme.HOVER, button_hover_color=theme.HOVER).pack(side="right")

        row2 = ctk.CTkFrame(body, fg_color="transparent")
        row2.pack(fill="x", pady=(0, 6))
        self.selected_label = ctk.CTkLabel(row2, text="Selected: 0 / 0", font=ctx.fonts["caption"],
                                           text_color=theme.SEC, anchor="w")
        self.selected_label.pack(side="left")
        ctk.CTkButton(row2, text="Validate All", width=96, height=24, font=ctx.fonts["caption"],
                      fg_color=theme.HOVER, hover_color=ctx.accent_hover,
                      command=self.validate_all).pack(side="right")

        self.canvas = ctk.CTkScrollableFrame(body, fg_color=theme.BG, corner_radius=theme.RADIUS_PANEL,
                                         width=110)
        self.canvas.pack(fill="both", expand=True)
        self.canvas.bind("<Configure>", self._on_configure)

        self._sync_filters()
        self._debounce_after = None
        self._configure_after = None
        self._last_width = 0
        self._rows: list = []

    def pack(self, *args, **kwargs) -> None:
        self._frame.pack(*args, **kwargs)

    def grid(self, *args, **kwargs) -> None:
        self._frame.grid(*args, **kwargs)

    @property
    def _density_height(self) -> int:
        density = self.ctx.settings.get("ui_density")
        if not density:
            density = "ultra" if self.ctx.settings.compact else "compact"
        return CARD_HEIGHTS.get(density, 58)

    # ---- search debounce ---------------------------------------------------------
    def _on_search(self) -> None:
        if self._debounce_after is not None:
            try:
                self._frame.after_cancel(self._debounce_after)
            except Exception:
                pass
        self._debounce_after = self._frame.after(SEARCH_DEBOUNCE_MS, self.render)

    # ---- resize debounce --------------------------------------------------------
    def _on_configure(self, _event=None) -> None:
        if self._configure_after is not None:
            try:
                self._frame.after_cancel(self._configure_after)
            except Exception:
                pass
        self._configure_after = self._frame.after(80, self._deferred_configure)

    def _deferred_configure(self) -> None:
        self._configure_after = None
        try:
            w = self._frame.winfo_width()
        except Exception:
            return
        if w > 0 and w != self._last_width:
            self._last_width = w
            self.render()

    def _set_view_filter(self, key: str) -> None:
        self.ctx.state.view_filter = key
        self._sync_filters()
        self.render()

    def _sync_filters(self) -> None:
        active = self.ctx.state.view_filter
        for key, btn in self._filter_btns.items():
            btn.configure(fg_color=self.ctx.accent if key == active else theme.HOVER,
                          hover_color=self.ctx.accent_hover)

    # ---- selection ---------------------------------------------------------------
    def select_all(self) -> None:
        self.ctx.state.set_selected(set(self.ctx.store.get_all().keys()))
        self.render()

    def invert(self) -> None:
        self.ctx.state.set_selected(set(self.ctx.store.get_all().keys()) - self.ctx.state.selected)
        self.render()

    def toggle_token(self, token: str) -> None:
        self.ctx.state.toggle(token)
        self.render()

    def validate_all(self) -> None:
        tokens = list(self.ctx.store.get_all().keys())
        if not tokens:
            self.ctx.log.info("No tokens to validate")
            return
        self.ctx.log.info(f"Validating {len(tokens)} token(s)")
        self._set_validating(True)
        self.ctx.validation.run(tokens, self._validation_done)

    def _set_validating(self, on: bool) -> None:
        win = self._frame.winfo_toplevel()
        if hasattr(win, "stats"):
            try:
                win.stats.set_validating(on)
            except Exception:
                pass

    def _validation_done(self) -> None:
        self._set_validating(False)
        self._refresh_window()

    def _refresh_window(self) -> None:
        # Find the window and refresh through it (avoids import cycle).
        win = self._frame.winfo_toplevel()
        if hasattr(win, "refresh_all"):
            win.refresh_all()

    # ---- model: build grouped rows --------------------------------------------------
    def _build_rows(self):
        tokens = {t: i for t, i in self.ctx.store.items()}
        query = self.search_var.get().lower().strip()
        buckets = {c: [] for c in CATEGORY_ORDER}
        for token, info in tokens.items():
            if not pass_filters(info, self.ctx.state.view_filter):
                continue
            if not match_search(info, query):
                continue
            buckets[categorize(info)].append((token, info))

        sort = self.sort_var.get()
        for key in buckets:
            if sort == SortMode.NAME.value:
                buckets[key].sort(key=lambda x: x[1].get("username", ""))
            elif sort == SortMode.USER_ID.value:
                buckets[key].sort(key=lambda x: x[1].get("user_id", ""))
            else:
                buckets[key].sort(key=lambda x: len(x[1].get("servers", [])), reverse=True)

        rows = []
        for key in CATEGORY_ORDER:
            items = buckets[key]
            if not items:
                continue
            collapsed = self.ctx.state.collapsed_groups.get(key.value, False)
            rows.append({"type": "group", "key": key, "label": CATEGORY_LABELS[key],
                         "count": len(items), "collapsed": collapsed})
            if not collapsed:
                for token, info in items:
                    rows.append({"type": "token", "token": token, "info": dict(info)})
        return rows

    # ---- render ---------------------------------------------------------------
    def render(self) -> None:
        for w in self.canvas.winfo_children():
            w.destroy()
        tokens = self.ctx.store.get_all()
        all_keys = list(tokens.keys())
        self._rows = self._build_rows()
        empty = True
        for row in self._rows:
            empty = False
            if row["type"] == "group":
                self._render_group_header(row)
            else:
                self._render_card(row["token"], row["info"], all_keys)
        if empty:
            ctk.CTkLabel(self.canvas, text="No accounts match", font=self.ctx.fonts["caption"],
                         text_color=theme.MUTED).pack(pady=14)
        self.selected_label.configure(
            text=f"Selected: {len(self.ctx.state.selected)} / {len(all_keys)}")

    def _render_group_header(self, row) -> None:
        head = ctk.CTkFrame(self.canvas, fg_color="transparent")
        head.pack(fill="x", pady=(4, 2))
        icon = "▾" if not row["collapsed"] else "▸"
        btn = ctk.CTkButton(head, text=f"{icon}  {row['label']}  ({row['count']})", anchor="w",
                            height=28, font=self.ctx.fonts["section"], fg_color=theme.HOVER,
                            hover_color=self.ctx.accent_hover,
                            command=lambda k=row['key']: self._toggle_group(k))
        btn.pack(side="left", fill="x", expand=True)
        ctk.CTkButton(head, text="Sel", width=46, height=28, font=self.ctx.fonts["caption"],
                      fg_color=theme.HOVER, hover_color=self.ctx.accent_hover,
                      command=lambda k=row['key']: self.select_group(k)).pack(side="right", padx=(4, 2))

    def _render_card(self, token, info, all_keys) -> None:
        selected = token in self.ctx.state.selected
        st = status(info)
        dot = theme.DOT_VALID if st is TokenStatus.VALID else (
            theme.DOT_LOCKED if st is TokenStatus.LOCKED else theme.DOT_INVALID)
        username = f"{info.get('username','?')}#{info.get('discriminator','0')}"
        card = TokenCard(
            self.canvas, info, selected, self.ctx.fonts, self.ctx.accent, self.ctx.accent_hover,
            self.ctx.settings.show_badges, self._density_height, dot,
            on_click=lambda e: self._on_token_click(e, token, all_keys),
            on_context=lambda e: self._token_context(e, token),
            on_properties=lambda t=token: self._open_properties(t),
            on_middle=lambda t=token: self._middle_copy(t),
            username_text=username,
            name_chars=self._name_chars(),
        )
        Tooltip(card.frame, build_token_tooltip(info, username))

    def _name_chars(self) -> int:
        """Max username characters that fit the current pane width (approx)."""
        w = self._frame.winfo_width()
        if w <= 0:
            return 30
        return max(14, min(60, int((w - 60) / 8)))

    def _toggle_group(self, key) -> None:
        self.ctx.state.collapsed_groups[key.value] = not self.ctx.state.collapsed_groups[key.value]
        self.render()

    def select_group(self, key) -> None:
        for token, info in self.ctx.store.items():
            if categorize(info) is key:
                self.ctx.state.selected.add(token)
        self.render()

    def select_group_by_value(self, value: str) -> None:
        self.select_group(TokenCategory(value))

    # ---- selection handler ---------------------------------------------------------
    def _on_token_click(self, event, token, all_tokens) -> None:
        state = getattr(event, "state", 0)
        if state & MOD_CTRL:
            self.ctx.state.toggle(token)
        elif state & MOD_SHIFT:
            if self.ctx.state.anchor is not None:
                try:
                    a = all_tokens.index(self.ctx.state.anchor)
                    i1 = all_tokens.index(token)
                    lo, hi = (a, i1) if a < i1 else (i1, a)
                    self.ctx.state.set_selected(
                        self.ctx.state.selected | set(all_tokens[lo:hi + 1]))
                except ValueError:
                    self.ctx.state.toggle(token)
            else:
                self.ctx.state.toggle(token)
        else:
            self.ctx.state.select(token)
        self.render()

    def _middle_copy(self, token) -> None:
        uid = self.ctx.store.get(token).get("user_id", "")
        clip_set(self._frame, uid)

    def _open_properties(self, token) -> None:
        from ui.dialogs.properties_dialog import show_properties
        show_properties(self._frame, self.ctx, token)

    # ---- context menu ------------------------------------------------------------
    def _token_context(self, event, token) -> None:
        if token not in self.ctx.state.selected:
            self.ctx.state.select(token)
        info = self.ctx.store.get(token)

        def validate_one_token():
            self._set_validating(True)
            self.ctx.validation.run([token], self._validation_done)

        def delete_one():
            import tkinter.messagebox as mb
            if mb.askyesno("Delete", f"Delete {self.ctx.username(info)}?"):
                self.ctx.store.remove_token(token)
                self.ctx.state.selected.discard(token)
                self.ctx.log.warning("Removed token")
                self._refresh_window()

        def rejoin():
            servers = info.get("servers", [])
            if not servers:
                self.ctx.log.warning("No servers on this token")
                return
            s = servers[0]
            self.ctx.state.set_selected({token})
            self.ctx.state.set_target_server(s["name"], s["id"])
            self.ctx.log.info(f"Rejoining {s['name']}")

        def open_profile():
            import webbrowser
            uid = info.get("user_id")
            if uid:
                webbrowser.open(f"https://discord.com/users/{uid}")

        menu = tk.Menu(self._frame, tearoff=0)
        menu.add_command(label="Properties", command=lambda: self._open_properties(token))
        menu.add_command(label="Validate", command=validate_one_token)
        menu.add_command(label="Rejoin First Server", command=rejoin)
        menu.add_separator()
        menu.add_command(label="Copy Token", command=lambda: clip_set(self._frame, token))
        menu.add_command(label="Copy User ID", command=lambda: clip_set(self._frame, info.get("user_id", "")))
        menu.add_command(label="Copy Username", command=lambda: clip_set(self._frame, self.ctx.username(info)))
        menu.add_command(label="Copy Email", command=lambda: clip_set(self._frame, info.get("email", "")))
        menu.add_separator()
        menu.add_command(label="Open Profile", command=open_profile)
        menu.add_command(label="Export", command=self._export_selected)
        menu.add_separator()
        menu.add_command(label="Delete", command=delete_one)
        try:
            menu.tk_popup(getattr(event, "x_root", 0), getattr(event, "y_root", 0))
        finally:
            menu.grab_release()

    def _export_selected(self) -> None:
        from ui.dialogs.export_dialog import show_export_selected
        show_export_selected(self.ctx, tokens=self.ctx.state.selected)