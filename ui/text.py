"""Small text helpers for the UI layer.

``CTkLabel`` has no native ellipsis, so long names (usernames, servers,
channels) overflow their column as the window gets narrower. ``truncate`` is a
character-based ellipsis that keeps every rendered label inside its column.
"""

__all__ = ["truncate"]

ELLIPSIS = "…"


def truncate(text: str, max_chars: int) -> str:
    """Return *text* shortened to at most *max_chars* characters with an
    ellipsis appended when it had to be cut. ``None``/short input passes
    through unchanged."""
    text = text or ""
    if max_chars <= 0 or len(text) <= max_chars:
        return text
    if max_chars <= 1:
        return ELLIPSIS
    return text[: max_chars - 1] + ELLIPSIS