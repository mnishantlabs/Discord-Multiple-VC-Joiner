"""Theme: palette, accent maps, spacing tokens, and display metadata.

The palette/accents were moved verbatim from the old ``main.py`` constants
(lines 21-54) so the visual identity is unchanged. The spacing tokens give the
views a single source for padding/radius so every panel matches at any window
size.
"""

FONT_FAMILY = "Segoe UI"

# ---- Layout tokens ----------------------------------------------------------
PAD_OUTER = 16        # window-level outer padding (toolbar/stats/actions/log)
PAD_PANEL = 14        # inner content padding inside a panel
RADIUS_PANEL = 8      # large card / panel corner radius
RADIUS_CTRL = 6       # buttons, entries, pill controls

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

ACCENTS = {
    "purple": "#8A63D2",
    "blue": "#5865F2",
    "blurple": "#5865F2",
    "green": "#23A55A",
    "orange": "#F47B20",
    "red": "#DA373C",
    "pink": "#EB459E",
}
ACCENT_HOVERS = {
    "purple": "#6E4FC0",
    "blue": "#4752C4",
    "blurple": "#4752C4",
    "green": "#1A8B4A",
    "orange": "#C96A1A",
    "red": "#A12828",
    "pink": "#C0247A",
}

# Order shown in the Appearance > Accent presets.
ACCENT_ORDER = ["purple", "blue", "blurple", "green", "orange", "red", "pink"]


def accent_hex(accent: str) -> str:
    """Resolve an accent name to its hex color; unknown/custom values are
    treated as literal hex colors."""
    return ACCENTS.get(accent, accent) if accent else ACCENT


def accent_hover_hex(accent: str) -> str:
    return ACCENT_HOVERS.get(accent, darken(accent_hex(accent), 0.18))


def blend(c1: str, c2: str, t: float) -> str:
    """Linear blend hex color *c1* toward *c2* by factor *t* (0..1)."""
    chan = lambda a, b: round(int(a, 16) + (int(b, 16) - int(a, 16)) * t)  # noqa: E731
    r = chan(c1[1:3], c2[1:3])
    g = chan(c1[3:5], c2[3:5])
    b = chan(c1[5:7], c2[5:7])
    return f"#{r:02X}{g:02X}{b:02X}"


def darken(hex_color: str, f: float = 0.18) -> str:
    return blend(hex_color, "#000000", f)


def selected_bg(accent: str) -> str:
    """Background tint for the selected row (accent barely over the panel)."""
    return blend(accent, CARD, 0.88)

DOT_VALID = GOOD
DOT_INVALID = DANGER
DOT_LOCKED = WARN

# ---- Activity log display metadata ----
LOG_ICON = {"success": "🟢", "info": "🔵", "warn": "🟡", "error": "🔴", "rate": "🔴"}
LOG_COLOR = {"success": GOOD, "info": SEC, "warn": WARN, "error": DANGER, "rate": SEC}
LOG_CAT = {"success": "SUCCESS", "info": "INFO", "warn": "WARNING", "error": "ERROR", "rate": "NETWORK"}


def build_fonts(ctk, size_title=20, size_normal=13, size_caption=11, size_section=11):
    """Create the standard CTkFont set (a dict of named fonts)."""
    family = FONT_FAMILY
    return {
        "title": ctk.CTkFont(family=family, size=size_title, weight="bold"),
        "section": ctk.CTkFont(family=family, size=size_section, weight="bold"),
        "normal": ctk.CTkFont(family=family, size=size_normal),
        "caption": ctk.CTkFont(family=family, size=size_caption),
    }