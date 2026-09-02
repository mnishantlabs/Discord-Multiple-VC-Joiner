"""Voice channels panel: current server label, advanced panel (guild/channel ids,
delay/concurrency/retry/timeout), recent joined targets, and the voice channel list."""

import tkinter as tk

import customtkinter as ctk

from core.constants import RECENT_VOICE_SHOWN
from ui import theme
from ui.text import truncate
from ui.widgets import Tooltip
from utils.clipboard import clip_set


class VoiceView:
    def __init__(self, parent, ctx) -> None:
        self.ctx = ctx
        root = ctk.CTkFrame(parent, fg_color=theme.CARD, corner_radius=theme.RADIUS_PANEL)
        self._frame = root

        head = ctk.CTkFrame(root, fg_color="transparent")
        head.pack(fill="x", padx=theme.PAD_PANEL, pady=(10, 8))
        ctk.CTkLabel(head, text="🎤 VOICE CHANNELS", font=ctx.fonts["section"],
                     text_color=theme.SEC).pack(side="left")

        body = ctk.CTkFrame(root, fg_color="transparent")
        body.pack(fill="both", expand=True, padx=theme.PAD_PANEL, pady=(0, 12))

        ctk.CTkLabel(body, text="Current Server", font=ctx.fonts["caption"], text_color=theme.SEC,
                     anchor="w").pack(fill="x")
        self.voice_server_label = ctk.CTkLabel(body, text="No server selected", font=ctx.fonts["normal"],
                                               anchor="w", text_color=theme.MUTED)
        self.voice_server_label.pack(fill="x", pady=(2, 6))

        self.adv_button = ctk.CTkButton(body, text="▸  Advanced", height=26, font=ctx.fonts["caption"],
                                        fg_color=theme.HOVER, hover_color=ctx.accent_hover,
                                        command=self.toggle_advanced)
        self.adv_button.pack(fill="x", pady=(0, 4))
        self.adv_frame = ctk.CTkFrame(body, fg_color=theme.BG, corner_radius=6)

        self.guild_id_var = tk.StringVar()
        self.channel_id_var = tk.StringVar()
        self.guild_id_entry = ctk.CTkEntry(self.adv_frame, textvariable=self.guild_id_var,
                                           placeholder_text="Server / guild ID", height=28,
                                           corner_radius=6, fg_color=theme.CARD, border_width=0,
                                           font=ctx.fonts["caption"])
        self.guild_id_entry.pack(fill="x", padx=8, pady=3)
        self.channel_id_entry = ctk.CTkEntry(self.adv_frame, textvariable=self.channel_id_var,
                                             placeholder_text="Voice channel ID", height=28,
                                             corner_radius=6, fg_color=theme.CARD, border_width=0,
                                             font=ctx.fonts["caption"])
        self.channel_id_entry.pack(fill="x", padx=8, pady=3)
        self.adv_user_label = ctk.CTkLabel(self.adv_frame, text="User ID: -", font=ctx.fonts["caption"],
                                           text_color=theme.SEC)
        self.adv_user_label.pack(anchor="w", padx=8, pady=2)

        advrow = ctk.CTkFrame(self.adv_frame, fg_color="transparent")
        advrow.pack(fill="x", padx=8, pady=3)
        self.delay_var = tk.StringVar(value=str(ctx.settings.get("delay", 0.5)))
        self.conc_var = tk.StringVar(value=str(ctx.settings.get("concurrency", 5)))
        self.retry_var = tk.StringVar(value=str(ctx.settings.get("retry_delay", 3)))
        self.timeout_var = tk.StringVar(value=str(ctx.settings.get("api_timeout", 10)))
        for lab, var in [("Delay", self.delay_var), ("Conc", self.conc_var),
                         ("Retry", self.retry_var), ("Time", self.timeout_var)]:
            col = ctk.CTkFrame(advrow, fg_color="transparent")
            col.pack(side="left", padx=4)
            ctk.CTkLabel(col, text=lab, font=ctx.fonts["caption"], text_color=theme.MUTED).pack(anchor="w")
            e = ctk.CTkEntry(col, textvariable=var, width=52, height=24, fg_color=theme.CARD,
                             border_width=0, font=ctx.fonts["caption"])
            e.pack()
            e.bind("<FocusOut>", lambda *_a: self._commit_advanced())

        ctk.CTkLabel(body, text="Recently Joined", font=ctx.fonts["caption"], text_color=theme.SEC,
                     anchor="w").pack(fill="x", pady=(8, 2))
        self.recent_voice_frame = ctk.CTkFrame(body, fg_color=theme.BG, corner_radius=6)
        self.recent_voice_frame.pack(fill="x", pady=(0, 6))

        ctk.CTkLabel(body, text="Channels", font=ctx.fonts["caption"], text_color=theme.SEC,
                     anchor="w").pack(fill="x", pady=(0, 4))
        self.channel_list = ctk.CTkScrollableFrame(body, fg_color=theme.BG, corner_radius=8)
        self.channel_list.pack(fill="both", expand=True)
        self.voice_hint = ctk.CTkLabel(body, text="Select a server in the Server List",
                                       font=ctx.fonts["caption"], text_color=theme.MUTED)
        self.voice_hint.pack(pady=6)

        self._channels: list = []

    def pack(self, *args, **kwargs) -> None:
        self._frame.pack(*args, **kwargs)

    def grid(self, *args, **kwargs) -> None:
        self._frame.grid(*args, **kwargs)

    # ---- advanced ----------------------------------------------------------------
    def toggle_advanced(self) -> None:
        if self.adv_frame.winfo_manager():
            self.adv_button.configure(text="▸  Advanced")
            self.adv_frame.pack_forget()
        else:
            self.adv_button.configure(text="▾  Advanced")
            self.adv_frame.pack(fill="x", pady=(0, 6))

    def _commit_advanced(self) -> None:
        for key, var in [("delay", self.delay_var), ("concurrency", self.conc_var),
                         ("retry_delay", self.retry_var), ("api_timeout", self.timeout_var)]:
            try:
                value = float(var.get()) if key == "delay" else int(var.get())
                self.ctx.settings.set(key, value, persist=False)
            except ValueError:
                pass
        self.ctx.settings._repo.save()

    # ---- target/channel ------------------------------------------------------------
    def set_target_label(self, text) -> None:
        self.voice_server_label.configure(text=truncate(text, 26), text_color=theme.TXT)

    def set_channels(self, channels) -> None:
        self._channels = list(channels)
        self.render_channels()

    def render_channels(self) -> None:
        for w in self.channel_list.winfo_children():
            w.destroy()
        if not self._channels:
            self.voice_hint.configure(text="No voice channels found")
            return
        self.voice_hint.configure(text="")
        for ch in self._channels:
            sel = self.ctx.state.selected_channel and self.ctx.state.selected_channel["id"] == ch["id"]
            btn = ctk.CTkButton(self.channel_list, anchor="w", height=32,
                                text=f"🔊 {truncate(ch['name'], 24)}", font=self.ctx.fonts["normal"],
                                fg_color=self.ctx.accent if sel else theme.HOVER,
                                hover_color=self.ctx.accent_hover,
                                command=lambda c=ch: self.choose_channel(c))
            btn.pack(fill="x", pady=2)
            btn.bind("<Button-3>", lambda e, c=ch: self.channel_context(e, c))
            btn.bind("<Button-2>", lambda e, c=ch: clip_set(self._frame, c["id"]))
            Tooltip(btn, f"{ch['name']}\n({ch['id']})")

    def channel_context(self, event, ch) -> None:
        menu = tk.Menu(self._frame, tearoff=0)
        menu.add_command(label="Copy Channel ID", command=lambda: clip_set(self._frame, ch["id"]))
        menu.add_command(label="Copy Name", command=lambda: clip_set(self._frame, ch["name"]))
        menu.add_command(label="Join", command=lambda: self.choose_channel(ch))
        try:
            menu.tk_popup(getattr(event, "x_root", 0), getattr(event, "y_root", 0))
        finally:
            menu.grab_release()

    def choose_channel(self, ch) -> None:
        self.ctx.state.set_target_channel(ch)
        self.channel_id_var.set(ch["id"])
        self.ctx.log.info(f"Selected channel {ch['name']}")
        self.render_channels()

    def render_recent(self) -> None:
        for w in self.recent_voice_frame.winfo_children():
            w.destroy()
        rv = self.ctx.settings.recent_voice
        if not rv:
            ctk.CTkLabel(self.recent_voice_frame, text="None yet", font=self.ctx.fonts["caption"],
                         text_color=theme.MUTED).pack(anchor="w", padx=6, pady=3)
            return
        for item in rv[:RECENT_VOICE_SHOWN]:
            ctk.CTkButton(self.recent_voice_frame,
                          text=f"🔊 {truncate(item['channel_name'], 12)}  ·  {truncate(item['guild_name'], 12)}",
                          height=22, font=self.ctx.fonts["caption"], fg_color=theme.HOVER,
                          hover_color=self.ctx.accent_hover, corner_radius=4,
                          command=lambda i=item: self._set_recent_voice(i)).pack(fill="x", pady=1, padx=2)

    def _set_recent_voice(self, item) -> None:
        self.guild_id_var.set(item["guild_id"])
        self.channel_id_var.set(item["channel_id"])
        self.ctx.state.set_target_server(item["guild_name"], item["guild_id"])
        self.ctx.state.set_target_channel(item)
        self.voice_server_label.configure(text=truncate(item["guild_name"], 26), text_color=theme.TXT)
        self.ctx.log.info(f"Targeted {item['channel_name']} ({item['guild_name']})")

    def render(self) -> None:
        self.render_recent()