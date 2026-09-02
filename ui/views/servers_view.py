"""Server list panel: search, pinned-first server list, selected server info,
members toggle, and triggers channel loading in the voice panel."""

import tkinter as tk

import customtkinter as ctk

from ui import theme
from ui.text import truncate
from ui.widgets import Tooltip
from utils.clipboard import clip_set


class ServersView:
    def __init__(self, parent, ctx) -> None:
        self.ctx = ctx
        root = ctk.CTkFrame(parent, fg_color=theme.CARD, corner_radius=theme.RADIUS_PANEL)
        self._frame = root

        head = ctk.CTkFrame(root, fg_color="transparent")
        head.pack(fill="x", padx=theme.PAD_PANEL, pady=(10, 8))
        ctk.CTkLabel(head, text="🖥 SERVER LIST", font=ctx.fonts["section"],
                     text_color=theme.SEC).pack(side="left")

        body = ctk.CTkFrame(root, fg_color="transparent")
        body.pack(fill="both", expand=True, padx=theme.PAD_PANEL, pady=(0, 12))

        self.search_var = tk.StringVar()
        self.search_var.trace_add("write", lambda *a: self._on_search())
        self.search_entry = ctk.CTkEntry(body, textvariable=self.search_var,
                                         placeholder_text="🔍  Search Servers…", height=32,
                                         corner_radius=theme.RADIUS_CTRL, fg_color=theme.BG, border_width=0,
                                         font=ctx.fonts["normal"])
        self.search_entry.pack(fill="x", pady=(0, 8))

        self.server_list = ctk.CTkScrollableFrame(body, fg_color=theme.BG, corner_radius=theme.RADIUS_PANEL)
        self.server_list.pack(fill="both", expand=True)

        self.server_info_label = ctk.CTkLabel(body, text="", font=ctx.fonts["caption"],
                                              text_color=theme.SEC, anchor="w")
        self.server_info_label.pack(fill="x", pady=(8, 2))

        self.members_toggle = ctk.CTkButton(body, text="▸ Members", height=26, font=ctx.fonts["caption"],
                                            fg_color=theme.HOVER, hover_color=ctx.accent_hover,
                                            command=self.toggle_members)
        self.members_toggle.pack(fill="x", pady=(0, 2))
        self.server_members = ctk.CTkScrollableFrame(body, fg_color=theme.BG,
                                                     corner_radius=theme.RADIUS_PANEL, height=0)
        self.server_members.pack(fill="x")

        self._debounce = None

    def pack(self, *args, **kwargs) -> None:
        self._frame.pack(*args, **kwargs)

    def grid(self, *args, **kwargs) -> None:
        self._frame.grid(*args, **kwargs)

    def _on_search(self) -> None:
        if self._debounce is not None:
            try:
                self._frame.after_cancel(self._debounce)
            except Exception:
                pass
        self._debounce = self._frame.after(180, self.render)

    # ---- render ---------------------------------------------------------------
    def render(self) -> None:
        for w in self.server_list.winfo_children():
            w.destroy()
        smap = self.ctx.store.get_server_map()
        if not smap:
            ctk.CTkLabel(self.server_list, text="No servers found", font=self.ctx.fonts["caption"],
                         text_color=theme.MUTED).pack(pady=12)
            return
        query = self.search_var.get().lower().strip()
        pinned = self.ctx.settings.pinned_servers
        names = sorted(smap.keys(), key=lambda n: (n not in pinned, n.lower()))
        for name in names:
            if query and query not in name.lower():
                continue
            data = smap[name]
            sel = self.ctx.state.selected_server and self.ctx.state.selected_server["name"] == name
            star = "⭐" if name in pinned else "●"
            fg = self.ctx.accent if sel else theme.HOVER
            row = ctk.CTkFrame(self.server_list, fg_color=fg, corner_radius=theme.RADIUS_CTRL)
            row.pack(fill="x", pady=2, ipady=3)
            star_lbl = ctk.CTkLabel(row, text=star, font=self.ctx.fonts["caption"])
            star_lbl.pack(side="left", padx=(8, 2))
            name_lbl = ctk.CTkLabel(row, text=truncate(name, 28), font=self.ctx.fonts["normal"],
                                    anchor="w")
            name_lbl.pack(side="left", fill="x", expand=True)
            count_lbl = ctk.CTkLabel(row, text=str(len(data["tokens"])), font=self.ctx.fonts["caption"],
                                     text_color=theme.SEC)
            count_lbl.pack(side="right", padx=(2, 8))
            for w in (row, star_lbl, name_lbl, count_lbl):
                w.bind("<Button-1>", lambda e, n=name: self.select_server(n))
                w.bind("<Button-3>", lambda e, n=name: self.server_context(e, n))
                w.bind("<Button-2>", lambda e, n=name: self._copy_server_id(n))
            Tooltip(row, f"{name}\nTokens: {len(data['tokens'])}\n({data['id']})")

        if self.ctx.state.selected_server:
            smap2 = self.ctx.store.get_server_map()
            if self.ctx.state.selected_server["name"] in smap2:
                self._render_members(smap2[self.ctx.state.selected_server["name"]])
            else:
                self.ctx.state.selected_server = None
                self.ctx.state.selected_channel = None
                self._render_members(None)
                self.voice_label_reset()

        self._update_server_info()

    def voice_label_reset(self) -> None:
        try:
            self.ctx.voice_view.set_target_label("No server selected")
        except Exception:
            pass

    def _update_server_info(self) -> None:
        if not self.ctx.state.selected_server:
            self.server_info_label.configure(text="")
            return
        name = self.ctx.state.selected_server["name"]
        smap = self.ctx.store.get_server_map()
        data = smap.get(name, {})
        star = "⭐" if name in self.ctx.settings.pinned_servers else "●"
        self.server_info_label.configure(
            text=truncate(f"{star} {name}  •  {len(data.get('tokens', []))} tokens  •  ID {data.get('id', '')}", 64))

    # ---- selection ---------------------------------------------------------------
    def select_server(self, name) -> None:
        smap = self.ctx.store.get_server_map()
        data = smap.get(name)
        if not data:
            return
        self.ctx.state.set_target_server(name, data["id"])
        self.ctx.state.members_collapsed = False
        self._render_members(data)
        self.render()
        if data["tokens"]:
            self.ctx.channels.run(data["tokens"][0]["token"], data["id"],
                                  self._on_channels_loaded)

    def _on_channels_loaded(self, channels) -> None:
        self.ctx.voice_view.set_channels(channels)

    def toggle_members(self) -> None:
        self.ctx.state.members_collapsed = not self.ctx.state.members_collapsed
        if self.ctx.state.selected_server:
            data = self.ctx.store.get_server_map().get(self.ctx.state.selected_server["name"])
            if data:
                self._render_members(data)

    def _render_members(self, data) -> None:
        for w in self.server_members.winfo_children():
            w.destroy()
        tokens = data.get("tokens", []) if data else []
        if self.ctx.state.members_collapsed:
            self.members_toggle.configure(text=f"▸  Members ({len(tokens)})")
            self.server_members.pack_forget()
            return
        self.members_toggle.configure(text=f"▾  Members ({len(tokens)})")
        self.server_members.pack(fill="x")
        if not tokens:
            ctk.CTkLabel(self.server_members, text="No tokens", font=self.ctx.fonts["caption"],
                         text_color=theme.MUTED).pack(pady=8)
        for m in tokens:
            row = ctk.CTkFrame(self.server_members, fg_color=theme.CARD, corner_radius=theme.RADIUS_CTRL)
            row.pack(fill="x", pady=2)
            row.grid_columnconfigure(0, weight=1)
            ctk.CTkLabel(row, text=truncate(m["username"], 22), font=self.ctx.fonts["caption"],
                         anchor="w").grid(row=0, column=0, sticky="ew", padx=(6, 2), pady=3)
            ctk.CTkButton(row, text="Select", width=60, height=22, font=self.ctx.fonts["caption"],
                          fg_color=theme.HOVER, hover_color=self.ctx.accent_hover,
                          command=lambda t=m["token"]: self._select_member(t)).grid(row=0, column=1, pady=3)

    def _select_member(self, token) -> None:
        self.ctx.state.selected.add(token)
        self.ctx.log.info(f"Selected {self.ctx.username(self.ctx.store.get(token))}")
        self._refresh_tokens()

    def _refresh_tokens(self) -> None:
        win = self._frame.winfo_toplevel()
        if hasattr(win, "tokens_view"):
            win.tokens_view.render()

    # ---- context menu ------------------------------------------------------------
    def server_context(self, event, name) -> None:
        smap = self.ctx.store.get_server_map()
        if name not in smap:
            return
        gid = smap[name]["id"]
        pinned = name in self.ctx.settings.pinned_servers

        def toggle_pin():
            pinned_list = list(self.ctx.settings.pinned_servers)
            if name in pinned_list:
                pinned_list.remove(name)
            else:
                pinned_list.append(name)
            self.ctx.settings.set("pinned_servers", pinned_list)
            self.render()

        menu = tk.Menu(self._frame, tearoff=0)
        menu.add_command(label="Unpin" if pinned else "Pin", command=toggle_pin)
        menu.add_command(label="Copy Server ID", command=lambda: clip_set(self._frame, gid))
        menu.add_command(label="Copy Name", command=lambda: clip_set(self._frame, name))
        menu.add_command(label="Refresh Channels", command=lambda: self.select_server(name))
        menu.add_command(label="Join (set as target)", command=lambda: self.select_server(name))
        try:
            menu.tk_popup(getattr(event, "x_root", 0), getattr(event, "y_root", 0))
        finally:
            menu.grab_release()

    def _copy_server_id(self, name) -> None:
        smap = self.ctx.store.get_server_map()
        if name in smap:
            clip_set(self._frame, smap[name]["id"])
            self.ctx.log.info(f"Copied server ID for {name}")