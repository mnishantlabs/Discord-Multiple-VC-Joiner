"""Windows 11 native backdrop effects (Mica / Acrylic) via DWM.

Best-effort: returns False on any failure so older Windows builds simply keep
the plain background.
"""

import sys

try:
    import ctypes
    from ctypes import byref, c_int, sizeof
except Exception:  # pragma: no cover - non-Windows
    ctypes = None


DWMWA_SYSTEMBACKDROP_TYPE = 38
DWMSBT_NONE = 1
DWMSBT_MAINWINDOW = 2   # Mica
DWMSBT_TRANSIENTWINDOW = 3  # Acrylic

_BACKDROP = {"off": DWMSBT_NONE, "mica": DWMSBT_MAINWINDOW, "acrylic": DWMSBT_TRANSIENTWINDOW}


def apply_backdrop(window, mode: str) -> bool:
    """Apply the DWM system backdrop to *window*.

    ``mode`` is one of ``"off"``, ``"mica"``, ``"acrylic"``. Only effective on
    Windows 11 22621+; silently ignored elsewhere.
    """
    if sys.platform != "win32" or ctypes is None:
        return False
    try:
        hwnd = int(window.winfo_id())
        value = c_int(_BACKDROP.get(mode, DWMSBT_NONE))
        ok = ctypes.windll.dwmapi.DwmSetWindowAttribute(
            hwnd, DWMWA_SYSTEMBACKDROP_TYPE, byref(value), sizeof(value))
        return ok == 0
    except Exception:
        return False


__all__ = ["apply_backdrop"]