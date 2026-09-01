"""Keyboard shortcut definitions and a binder helper.

Storing shortcuts as data (rather than scattered ``bind`` calls in the old
``App._bind_shortcuts``) makes them easy to audit and extend. The binder is
generic over a Tk-compatible root widget.
"""

from typing import Any, Callable

from utils.platform import MOD_CTRL, MOD_SHIFT

# Each entry: (label, keysym, modifier_mask, handler)
# ``mods`` combines MOD_CTRL / MOD_SHIFT.
SHORTCUTS: list[tuple[str, str, int, Callable[[], None]]] = []

Validator = Callable[[], None]


def define(label: str, keysym: str, mods: int, handler: Validator) -> None:
    SHORTCUTS.append((label, keysym, mods, handler))


def template(keysym: str, mods: int) -> str:
    """Build the Tk binding string for a keysym + modifier mask."""
    parts = []
    if mods & MOD_CTRL:
        parts.append("Control")
    if mods & MOD_SHIFT:
        parts.append("Shift")
    parts.append(keysym)
    return "<" + "-".join(parts) + ">"


def bind_shortcuts(root: Any, entries: list[tuple[str, str, int, Validator]]) -> None:
    """Bind every shortcut entry onto *root*."""
    for _label, keysym, mods, handler in entries:
        root.bind(template(keysym, mods), lambda _e, h=handler: h())


# --- default shortcuts (mirror the original app) --------------------------------
def register_defaults(handlers: dict[str, Callable[[], None]]) -> None:
    SHORTCUTS.clear()
    define("Refresh", "r", MOD_CTRL, handlers["refresh"])
    define("Import", "i", MOD_CTRL, handlers["import_"])
    define("Focus search", "f", MOD_CTRL, handlers["search"])
    define("Select all", "a", MOD_CTRL, handlers["select_all"])
    define("Delete", "Delete", 0, handlers["delete"])
    define("Join voice", "Return", 0, handlers["join_voice"])
    define("Copy IDs", "c", MOD_CTRL, handlers["copy_ids"])
    define("Open import", "o", MOD_CTRL, handlers["import_"])


__all__ = ["SHORTCUTS", "define", "template", "bind_shortcuts", "register_defaults", "MOD_CTRL", "MOD_SHIFT"]