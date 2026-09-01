"""Enums used across the application to avoid magic strings."""

from enum import Enum

# NOTE: string values of these two enums are the RESERVED keys used by the UI
# filter dict and the persisted categories. Do not rename without updating
# the filters and the config migration.


class TokenStatus(str, Enum):
    VALID = "valid"
    INVALID = "invalid"
    LOCKED = "locked"


class TokenCategory(str, Enum):
    INVALID = "invalid"
    LOCKED = "locked"
    NITRO = "nitro"
    PHONE = "phone"
    VALID = "valid"


CATEGORY_ORDER = [
    TokenCategory.INVALID,
    TokenCategory.LOCKED,
    TokenCategory.NITRO,
    TokenCategory.PHONE,
    TokenCategory.VALID,
]

CATEGORY_LABELS = {
    TokenCategory.INVALID: "❌ Invalid",
    TokenCategory.LOCKED: "🔒 Locked",
    TokenCategory.NITRO: "⭐ Nitro",
    TokenCategory.PHONE: "📱 Phone Verified",
    TokenCategory.VALID: "✅ Valid",
}


class LogLevel(str, Enum):
    INFO = "info"
    SUCCESS = "success"
    WARN = "warn"
    ERROR = "error"
    RATE = "rate"


LOG_LEVEL_LABELS = {
    LogLevel.SUCCESS: "SUCCESS",
    LogLevel.INFO: "INFO",
    LogLevel.WARN: "WARNING",
    LogLevel.ERROR: "ERROR",
    LogLevel.RATE: "NETWORK",
}


class ActionType(str, Enum):
    JOIN = "join"
    VOICE = "voice"


class SortMode(str, Enum):
    SERVER_COUNT = "Server Count"
    NAME = "Name"
    USER_ID = "User ID"


class Accent(str, Enum):
    BLUE = "blue"
    GREEN = "green"
    PURPLE = "purple"
    RED = "red"
    ORANGE = "orange"
    PINK = "pink"