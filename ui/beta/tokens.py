"""Material 3 "Clean Desktop" redesign tokens.

This is the *beta* visual language, transcribed from ``beta/DESIGN.md``. It is
NOT the shipped theme. When the app is launched with ``--beta`` the values here
are grafted onto the shared ``ui.theme`` module at startup (before any widget is
built), so every existing view and dialog — which read ``theme.*`` attributes at
widget-construction time — renders in this style. The shipped ``ui/theme.py`` is
left untouched and the default (non-beta) run never imports this module.
"""

# ---- Typography ------------------------------------------------------------
FONT_FAMILY = "Inter"            # falls back gracefully to Segoe UI / system
MONO_FAMILY = "JetBrains Mono"   # used for ids / tokens / codes

# ---- Core palette (from DESIGN.md front-matter) ----------------------------
BG = "#F3F4F6"                   # Level 0 surface (default used by _frame)
CARD = "#FFFFFF"                 # Level 1 card / content surface
HOVER = "#E7E8EA"                # secondary buttons / row hover (surface-container)
ACCENT = "#5865F2"               # primary / blurple
ACCENT_HOVER = "#4752C4"         # darker primary
TXT = "#191C1E"                  # on-surface (near-black)
SEC = "#454655"                  # on-surface-variant
MUTED = "#767686"                # outline
    
GOOD = "#006E2F"                 # secondary (green) on-white
GOOD_HOVER = "#00531F"
DANGER = "#BA1A1A"               # error
DANGER_HOVER = "#93000A"
WARN = "#A95400"                 # amber tone, legible on white

# ---- Accent presets (reuse existing names; hue-adjusted for light bg) ------
ACCENTS = {
    "purple": "#7B5EA7",
    "blue": "#5865F2",
    "blurple": "#5865F2",
    "green": "#006E2F",
    "orange": "#C5441C",
    "red": "#BA1A1A",
    "pink": "#C0257B",
}
ACCENT_HOVERS = {
    "purple": "#674A8E",
    "blue": "#4752C4",
    "blurple": "#4752C4",
    "green": "#00531F",
    "orange": "#A43418",
    "red": "#93000A",
    "pink": "#9E1C63",
}
ACCENT_ORDER = ["purple", "blue", "blurple", "green", "orange", "red", "pink"]

# ---- Layout / shape tokens --------------------------------------------------
PAD_OUTER = 16
PAD_PANEL = 16
RADIUS_PANEL = 14               # cards / panels (0.875rem)
RADIUS_CTRL = 8                 # buttons / inputs (0.5rem)

# ---- Status indicator dots ---------------------------------------------------
DOT_VALID = GOOD
DOT_INVALID = DANGER
DOT_LOCKED = WARN

# ---- Activity log metadata ----------------------------------------------------
LOG_ICON = {"success": "●", "info": "●", "warn": "●", "error": "●", "rate": "●"}
LOG_COLOR = {"success": GOOD, "info": SEC, "warn": WARN, "error": DANGER, "rate": SEC}
LOG_CAT = {"success": "SUCCESS", "info": "INFO", "warn": "WARNING", "error": "ERROR", "rate": "NETWORK"}


def accent_hex(accent: str) -> str:
    return ACCENTS.get(accent, accent) if accent else ACCENT


def accent_hover_hex(accent: str) -> str:
    return ACCENT_HOVERS.get(accent, darken(accent_hex(accent), 0.18))


def blend(c1: str, c2: str, t: float) -> str:
    chan = lambda a, b: round(int(a, 16) + (int(b, 16) - int(a, 16)) * t)  # noqa: E731
    r = chan(c1[1:3], c2[1:3])
    g = chan(c1[3:5], c2[3:5])
    b = chan(c1[5:7], c2[5:7])
    return f"#{r:02X}{g:02X}{b:02X}"


def darken(hex_color: str, f: float = 0.18) -> str:
    return blend(hex_color, "#000000", f)


def selected_bg(accent: str) -> str:
    return blend(accent, CARD, 0.9)


def build_fonts(ctk, size_title=20, size_normal=13, size_caption=11, size_section=11):
    """Build the beta font set. Uppercase label styling is handled by callers
    via ``context.fonts`` metadata; here we keep the same key structure the
    shipped ``theme.build_fonts`` exposes so every view keeps working."""
    family = _available(ctk, FONT_FAMILY, "Segoe UI")
    mono = _available(ctk, MONO_FAMILY, "Consolas")
    return {
        "title": ctk.CTkFont(family=family, size=size_title, weight="bold"),
        "section": ctk.CTkFont(family=family, size=size_section, weight="bold"),
        "normal": ctk.CTkFont(family=family, size=size_normal),
        "caption": ctk.CTkFont(family=family, size=size_caption),
        "mono": ctk.CTkFont(family=mono, size=size_normal),
    }


def _available(ctk, preferred: str, fallback: str) -> str:
    """Pick ``preferred`` if the platform actually has it, else ``fallback``
    (avoids ugly font substitution when Inter/JetBrains Mono aren't installed)."""
    try:
        fams = set(ctk.font.families())
        return preferred if preferred in fams else fallback
    except Exception:
        return fallback
