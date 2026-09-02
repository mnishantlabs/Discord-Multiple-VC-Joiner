"""Pure predicates operating on the runtime token-info dicts.

These functions used to live inside the view (``main.token_status``,
``main._categorize``). They have no side effects so they are trivially
testable and safe to call from any thread.
"""

from typing import Any

from core.enums import TokenCategory, TokenStatus


def status(info: dict[str, Any]) -> TokenStatus:
    """Derive the validity status of a token-info dict."""
    if info.get("user_id"):
        return TokenStatus.VALID
    err = (info.get("error") or "").upper()
    if "LOCK" in err or "FLAGGED" in err:
        return TokenStatus.LOCKED
    return TokenStatus.INVALID


def categorize(info: dict[str, Any]) -> TokenCategory:
    """Categorize a token into a display group (used for grouping/filters)."""
    if not info.get("user_id"):
        return TokenCategory.INVALID
    if status(info) is TokenStatus.LOCKED:
        return TokenCategory.LOCKED
    if info.get("premium_type", 0) > 0:
        return TokenCategory.NITRO
    if info.get("phone"):
        return TokenCategory.PHONE
    return TokenCategory.VALID


def pass_filters(info: dict[str, Any], view_filter: str) -> bool:
    """Return True when *info* survives the active list filter.

    ``view_filter`` is one of ``"all"`` (every token), ``"valid"`` (any token
    with a recognised user id, including Nitro/phone copies), or ``"invalid"``
    (dead/locked tokens). Presence of Nitro/phone is a style badge, not a
    filter.
    """
    if view_filter == "all":
        return True
    valid = status(info) is TokenStatus.VALID
    return valid if view_filter == "valid" else not valid


def match_search(info: dict[str, Any], query: str) -> bool:
    """Return True when *info* matches the free-text search query."""
    q = query.strip().lower()
    if not q:
        return True
    haystack_parts = [
        info.get("username", ""),
        info.get("user_id", ""),
        str(info.get("email") or ""),
        str(info.get("phone") or ""),
    ]
    for server in info.get("servers", []):
        haystack_parts.append(str(server.get("name", "")))
        haystack_parts.append(str(server.get("id", "")))
    return q in " ".join(haystack_parts).lower()


def display_name(info: dict[str, Any]) -> str:
    """Legacy display name ``username#discriminator``."""
    return f"{info.get('username', '?')}#{info.get('discriminator', '0')}"