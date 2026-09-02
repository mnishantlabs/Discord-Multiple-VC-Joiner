"""Beta UI layer: a runtime re-theme of the shipped interface.

When launched with ``--beta``, :func:`apply_beta` grafts the Material 3
"Clean Desktop" tokens (``ui.beta.tokens``) onto the shared ``ui.theme`` module
*before* any widget/view/dialog module is imported. Every view and dialog
resolves its colors/fonts/radii through ``ui.theme`` — either via the module
object (``from ui import theme``) or via ``from ui.theme import ...`` which is
evaluated when each module is imported. Because ``apply_beta`` runs first, all
of those reads observe the beta values.

The default (non-beta) run never imports this package, so the main tool is
completely unaffected.
"""

from ui import theme as _theme
from ui.beta import tokens as _tokens

# Names on ui.theme whose values the beta tokens fully replace.
_SWAP_NAMES = (
    "FONT_FAMILY", "BG", "CARD", "HOVER", "ACCENT", "ACCENT_HOVER", "TXT",
    "SEC", "MUTED", "GOOD", "GOOD_HOVER", "DANGER", "DANGER_HOVER", "WARN",
    "ACCENTS", "ACCENT_HOVERS", "ACCENT_ORDER", "DOT_VALID", "DOT_INVALID",
    "DOT_LOCKED", "LOG_ICON", "LOG_COLOR", "LOG_CAT",
    "PAD_OUTER", "PAD_PANEL", "RADIUS_PANEL", "RADIUS_CTRL",
    "accent_hex", "accent_hover_hex", "blend", "darken", "selected_bg",
)


def apply_beta() -> None:
    """Replace the shipped theme constants with the beta design language.

    Must be called before any ``ui`` widget/view/dialog module is imported.
    Safe to call once; it overwrites attributes on the ``ui.theme`` module
    object in place, so all existing ``theme.X`` references see the new values.
    """
    for name in _SWAP_NAMES:
        value = getattr(_tokens, name, None)
        if value is not None:
            setattr(_theme, name, value)

    _theme.build_fonts = _tokens.build_fonts

    # Force a light appearance mode so CustomTkinter's internal colors
    # (scrollbars, button defaults, transparent surfaces) match the light
    # "Clean Desktop" palette. Beta-only; the shipped SettingsService is
    # restored implicitly because default runs never call apply_beta().
    from services.settings_service import SettingsService

    _orig_get = SettingsService.get

    def _beta_get(self, key: str, default=None):
        if key == "appearance_mode":
            return "light"
        return _orig_get(self, key, default)

    SettingsService.get = _beta_get

    # Every button/label in the app omits an explicit ``text_color`` and relies
    # on CustomTkinter's theme default, which is a light gray (#DCE4EE) in both
    # appearance modes. On the beta's light surfaces (white cards, light-gray
    # secondary buttons) that made text/button labels nearly invisible. Override
    # the shared CTk theme defaults to dark text so all default-text widgets are
    # readable on the light palette. Runs before any widget is constructed, so
    # every view and dialog picks it up.
    from customtkinter.windows.widgets.theme import ThemeManager as _CTkTheme

    _DARK = ["#191C1E", "#191C1E"]
    for _w in ("CTkButton", "CTkLabel", "CTkEntry", "CTkTextbox",
               "CTkCheckBox", "CTkRadioButton", "CTkSwitch",
               "CTkSegmentedButton", "CTkOptionMenu"):
        try:
            _CTkTheme.theme[_w]["text_color"] = _DARK
        except Exception:
            pass
    try:
        _CTkTheme.theme["CTkButton"]["text_color_disabled"] = ["gray40", "gray50"]
    except Exception:
        pass


def is_beta_argv(argv) -> bool:
    """True when ``--beta`` (or ``beta``) appears in the CLI args."""
    return any(a == "--beta" or a.lower() == "beta" for a in argv)
