"""Domain layer: pure business rules, models, enums, and the event bus.

Nothing in this package imports tkinter, aiohttp, or websockets. It has no
knowledge of the outside world and is fully unit-testable.
"""

from core.constants import (
    API_BASE,
    GATEWAY_URL,
    HEADERS,
    USER_AGENT,
    FLAG_NAMES,
)
from core.enums import (
    TokenStatus,
    TokenCategory,
    LogLevel,
    ActionType,
    SortMode,
    Accent,
    CATEGORY_ORDER,
    CATEGORY_LABELS,
    LOG_LEVEL_LABELS,
)
from core.ids import snowflake_time, created_from_id, is_valid_snowflake
from core.models import ServerInfo, ChannelInfo, VoiceTarget, Token
from core.predicates import status, categorize, pass_filters, match_search, display_name
from core import events

__all__ = [
    "API_BASE",
    "GATEWAY_URL",
    "HEADERS",
    "USER_AGENT",
    "FLAG_NAMES",
    "TokenStatus",
    "TokenCategory",
    "LogLevel",
    "ActionType",
    "SortMode",
    "Accent",
    "CATEGORY_ORDER",
    "CATEGORY_LABELS",
    "LOG_LEVEL_LABELS",
    "snowflake_time",
    "created_from_id",
    "is_valid_snowflake",
    "ServerInfo",
    "ChannelInfo",
    "VoiceTarget",
    "Token",
    "status",
    "categorize",
    "pass_filters",
    "match_search",
    "display_name",
    "events",
]