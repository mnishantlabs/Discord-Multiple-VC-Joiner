"""Token manager panel: search, filter pills, sort, grouped token list,
selection (shift/ctrl/plain), context menu, detail panel, validate all.

Deliberately uses a CTk ``ScrollableFrame`` with grouped headers (group row
and token-row heights differ, so a uniform-height virtual list is not a fit).
The old performance bug was a full widget rebuild on *every* keystroke; that
is fixed here by debouncing search re-renders (only minor highlight work per
keystroke, a full rebuild after the user stops typing).
"""

import tkinter as tk

import customtkinter as ctk

from core.enums import SortMode, TokenStatus, CATEGORY_ORDER, CATEGORY_LABELS
from core.ids import created_from_id
from core.predicates import status, categorize, pass_filters, match_search
from ui import theme
from ui.widgets import FilterPill, TokenCard, Tooltip, build_token_tooltip
from utils.clipboard import clip_set
from utils.platform import MOD_CTRL, MOD_SHIFT

SEARCH_DEBOUNCE_MS = 180


class TokensView:
    def __init__(self, parent, ctx) -> None:
        self.ctx = ctx
        root = ctk.CTkFrame(parent, fg_color=theme.CARD, corner_radius=8)
        self._frame = root

        head = ctk.CTkFrame(root, fg_color="transparent")
        head.pack(fill="x", padx=14, pady=(10, 8))
        ctk.CTkLabel(head, text="👤 TOKEN MANAGER", font=ctx.fonts["section"],
                     text_color=theme.SEC).pack(side="left")

        body = ctk.CTkFrame(root, fg_color="transparent")
        body.pack(fill="both", expand=True, padx=14, pady=(0, 12))

        self.search_var = tk.StringVar()
        self.search_var.trace_add("write", lambda *a: self._on_search())
        self.search_entry = ctk.CTkEntry(body, textvariable=self.search_var,
                                         placeholder_text="🔍  Search…", height=32,
                                         corner_radius=6, fg_color=theme.BG, border_width=0,
                                         font=ctx.fonts["normal"])
        self.search_entry.pack(fill="x", pady=(0, 6))

        row1 = ctk.CTkFrame(body, fg_color="transparent")
        row1.pack(fill="x", pady=(0, 8))
        ctk.CTkButton(row1, text="☑", command=self.select_all, width=30, height=26,
                      fg_color=theme.HOVER, hover_color=ctx.accent_hover,
                      corner_radius=5).pack(side="left", padx=2)
        ctk.CTkButton(row1, text="⇄", command=self.invert, width=30, height=26,
                      fg_color=theme.HOVER, hover_color=ctx.accent_hover,
                      corner_radius=5).pack(side="left", padx=2)

        self._pills = {}
        for name, key in [("Valid", "valid"), ("Invalid", "invalid"), ("Locked", "locked"),
                          ("Nitro", "nitro"), ("Phone", "phone")]:
            pill = FilterPill(row1, name, ctx.accent, ctx.accent_hover,
                              lambda active, k=key: self._set_filter(k, active), active=True,
                              font=ctx.fonts["caption"])
            pill.pack(side="left", padx=2)
            self._pills[key] = pill

        self.sort_var = tk.StringVar(value=SortMode.SERVER_COUNT.value)
        ctk.CTkOptionMenu(row1, values=[s.value for s in SortMode], variable=self.sort_var,
                          command=lambda *a: self.render(), width=120, height=26,
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

        self.canvas = ctk.CTkScrollableFrame(body, fg_color=theme.BG, corner_radius=8)
        self.canvas.pack(fill="both", expand=True)

        self.detail_frame = ctk.CTkFrame(body, fg_color=theme.BG, corner_radius=8)
        self.detail_frame.pack(fill="x", pady=(8, 0))

        self._debounce_after = None
        self._rows: list = []

    def pack(self, *args, **kwargs) -> None:
        self._frame.pack(*args, **kwargs)

    def grid(self, *args, **kwargs) -> None:
        self._frame.grid(*args, **kwargs)

    # ---- search debounce ---------------------------------------------------------
    def _on_search(self) -> None:
        if self._debounce_after is not None:
            try:
                self._frame.after_cancel(self._debounce_after)
            except Exception:
                pass
        self._debounce_after = self._frame.after(SEARCH_DEBOUNCE_MS, self.render)

    def _set_filter(self, key: str, active: bool) -> None:
        self.ctx.state.filters[key] = active
        self.render()

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
        self.ctx.log.info(f"Validating {len(tokens)} token(s)")
        self.ctx.validation.run(tokens, self._validation_done)

    def _validation_done(self) -> None:
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
            if not pass_filters(info, self.ctx.state.filters):
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
            ctk.CTkLabel(self.canvas, text="No tokens match", font=self.ctx.fonts["caption"],
                         text_color=theme.MUTED).pack(pady=14)
        self.selected_label.configure(
            text=f"Selected: {len(self.ctx.state.selected)} / {len(all_keys)}")
        self._render_details()

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
            self.ctx.settings.show_badges, self.ctx.settings.show_ids,
            self.ctx.settings.compact, dot,
            on_click=lambda e: self._on_token_click(e, token, all_keys),
            on_context=lambda e: self._token_context(e, token),
            on_rejoin=lambda t=token: self._dbl_token_join(t),
            on_middle=lambda t=token: self._middle_copy(t),
            on_toggle=lambda t=token: self.toggle_token(t),
            username_text=username,
        )
        Tooltip(card.frame, build_token_tooltip(info, username))

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

    def _dbl_token_join(self, token) -> None:
        info = self.ctx.store.get(token)
        servers = info.get("servers", [])
        if not servers:
            self.ctx.log.warning("No servers on this token to rejoin")
            return
        s = servers[0]
        self.ctx.state.set_selected({token})
        self.ctx.state.set_target_server(s["name"], s["id"])
        self.ctx.log.info(f"Rejoining {s['name']}")

    # ---- details panel -------------------------------------------------------------
    def _render_details(self):
        for w in self.detail_frame.winfo_children():
            w.destroy()
        uid_text = "-"
        if len(self.ctx.state.selected) == 1:
            token = next(iter(self.ctx.state.selected))
            info = self.ctx.store.get(token)
            uid_text = info.get("user_id", "-")
            ctk.CTkLabel(self.detail_frame, text="DETAILS", font=self.ctx.fonts["section"],
                         text_color=theme.SEC).pack(anchor="w", padx=8, pady=(6, 2))
            lines = [
                f"👤  {self.ctx.username(info)}",
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
                ctk.CTkLabel(self.detail_frame, text=line, font=self.ctx.fonts["caption"],
                             text_color=theme.SEC, anchor="w").pack(anchor="w", padx=8)
        else:
            ctk.CTkLabel(self.detail_frame, text="Select a single token to view details",
                         font=self.ctx.fonts["caption"], text_color=theme.MUTED).pack(
                             anchor="w", padx=8, pady=6)

    # ---- context menu ------------------------------------------------------------
    def _token_context(self, event, token) -> None:
        if token not in self.ctx.state.selected:
            self.ctx.state.select(token)
        info = self.ctx.store.get(token)

        def validate_one(name_mock=token):
            self.ctx.validation.run([token], self._validation_done)

        def delete_one(name_mock=token):
            import tkinter.messagebox as mb
            if mb.askyesno("Delete", f"Delete {self.ctx.username(info)}?"):
                self.ctx.store.remove_token(token)
                self.ctx.state.selected.discard(token)
                self.ctx.log.warning("Removed token")
                self._refresh_window()

        def open_profile():
            import webbrowser
            uid = info.get("user_id")
            if uid:
                webbrowser.open(f"https://discord.com/users/{uid}")

        menu = tk.Menu(self._frame, tearoff=0)
        menu.add_command(label="Validate", command=validate_one)
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