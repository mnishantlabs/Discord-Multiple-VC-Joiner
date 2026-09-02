"""Beta icon layer: crisp colored glyphs rendered with Pillow.

The shipped UI relies on Unicode emoji rendered in the system font. This module
provides PIL-rendered vector-ish glyphs (status dots, log traffic lights) so the
experimental Material "Clean Desktop" UI can swap to sharp single-color marks
that match the DESIGN.md "status indicators are 10px circles with a 2px donut
border" spec.

It builds on Pillow, which CustomTkinter already bundles, so no new dependency.

Note: the beta's status dots / log indicators are wired through ``theme.DOT_*``
and ``theme.LOG_*`` (already replaced by ``ui.beta.tokens``), so this module is
a reference asset for beta-specific widgets rather than a required import today.
"""

from PIL import Image, ImageDraw


def draw_circle(
    size: int,
    fill: str,
    border: str = "#FFFFFF",
    border_width: int = 2,
) -> Image.Image:
    """A filled circle with a light 'donut' border, per the DESIGN.md status
    indicator spec. Returns an RGBA image ``size`` x ``size``."""
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    margin = max(1, border_width)
    d.ellipse([margin, margin, size - margin, size - margin], fill=fill, outline=border,
              width=border_width)
    return img


def traffic_dot(color: str, size: int = 10, *args) -> Image.Image:
    """Small status dot (no border) used inside dense lists / log rows."""
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    d.ellipse([0, 0, size - 1, size - 1], fill=color)
    return img


def to_ctk_image(img: Image.Image, scale: float = 1.0):
    """Wrap a PIL image into a CustomTkinter-compatible ``CTkImage``."""
    import customtkinter as ctk

    return ctk.CTkImage(light_image=img, dark_image=img, size=(
        int(img.width * scale), int(img.height * scale)))
