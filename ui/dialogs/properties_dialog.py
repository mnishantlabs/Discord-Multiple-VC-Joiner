"""Token properties dialog: read-only summary of a token account."""

import customtkinter as ctk

from ui import theme

_PREMIUM = {0: "None", 1: "Nitro Classic", 2: "Nitro", 3: "Nitro Basic", 4: "Nitro"}


class PropertiesDialog(ctk.CTkToplevel):
    """Modal top-level listing stored info for one token account."""

    def __init__(self, parent, ctx, token) -> None:
        super().__init__(parent)
        self.ctx = ctx
        info = ctx.store.get(token) or {}
        self.title(f"Properties — {ctx.username(info)}")
        self.geometry("480x600")
        self.configure(fg_color=theme.BG)

        body = ctk.CTkScrollableFrame(self, fg_color="transparent")
        body.pack(fill="both", expand=True, padx=14, pady=(14, 0))

        ctk.CTkLabel(body, text="TOKEN PROPERTIES", font=ctx.fonts["section"],
                     text_color=theme.SEC).pack(anchor="w", pady=(0, 8))

        def row(label, value):
            ctk.CTkLabel(body, text=label, font=ctx.fonts["caption"],
                         text_color=theme.MUTED).pack(anchor="w", pady=(6, 0))
            ctk.CTkLabel(body, text=value if value else "—", font=ctx.fonts["normal"],
                         text_color=theme.SEC, wraplength=420, justify="left").pack(anchor="w")

        token_shown = f"{token[:24]}…{token[-8:]}" if len(token) > 40 else token
        row("Name", ctx.username(info))
        row("Token", token_shown)
        row("User ID", info.get("user_id"))
        row("Email", info.get("email"))
        row("Phone", info.get("phone"))
        row("MFA Enabled", "Yes" if info.get("mfa_enabled") else "No")
        row("Bot", "Yes" if info.get("is_bot") else "No")
        row("Premium", _PREMIUM.get(info.get("premium_type"), "None"))
        row("Flags", ", ".join(map(str, info.get("flags") or [])) or "None")

        servers = info.get("servers") or []
        ctk.CTkLabel(body, text=f"SERVERS ({len(servers)})", font=ctx.fonts["section"],
                     text_color=theme.SEC).pack(anchor="w", pady=(14, 4))
        if servers:
            for s in servers:
                line = s.get("name", "?")
                ctk.CTkLabel(body, text=line, font=ctx.fonts["normal"],
                             text_color=theme.SEC,
                             wraplength=420, justify="left",
                             anchor="w").pack(fill="x", padx=(6, 0), pady=1)
        else:
            ctk.CTkLabel(body, text="No servers recorded.", font=ctx.fonts["caption"],
                         text_color=theme.MUTED).pack(anchor="w")

        ctk.CTkButton(self, text="Close", command=self.destroy, width=100, height=30,
                      fg_color=ctx.accent, hover_color=ctx.accent_hover,
                      font=ctx.fonts["normal"]).pack(pady=(10, 12))

        self.grab_set()
        self.transient(parent)


def show_properties(parent, ctx, token) -> None:
    PropertiesDialog(parent, ctx, token)