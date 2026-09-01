"""Theme: palette, accent maps, and display metadata.

Moved verbatim from the old ``main.py`` constants (lines 21-54) so the visual
identity is unchanged. A single ``theme.py`` is the anchor point for a future
theme engine.
"""

FONT_FAMILY = "Segoe UI"

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
    "blue": "#5865F2",
    "green": "#23A55A",
    "purple": "#8A63D2",
    "red": "#DA373C",
    "orange": "#F47B20",
    "pink": "#EB459E",
}
ACCENT_HOVERS = {
    "blue": "#4752C4",
    "green": "#1A8B4A",
    "purple": "#6E4FC0",
    "red": "#A12828",
    "orange": "#C96A1A",
    "pink": "#C0247A",
}

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