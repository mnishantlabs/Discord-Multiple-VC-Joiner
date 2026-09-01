"""Snowflake (Discord ID) helpers."""

import datetime

SNOWFLAKE_EPOCH = 1420070400000


def is_valid_snowflake(value: object) -> bool:
    """Return True if *value* looks like a Discord snowflake."""
    if isinstance(value, bool):
        return False
    try:
        return int(str(value)) > 0
    except (TypeError, ValueError):
        return False


def snowflake_time(user_id) -> datetime.datetime | None:
    """Return the UTC creation time of a Discord snowflake, or None."""
    try:
        ms = (int(user_id) >> 22) + SNOWFLAKE_EPOCH
        return datetime.datetime.fromtimestamp(ms / 1000, tz=datetime.timezone.utc)
    except (TypeError, ValueError, OverflowError):
        return None


def created_from_id(user_id) -> str:
    """Return a 'YYYY-MM-DD' string for a snowflake, or '?' when unparsable."""
    created = snowflake_time(user_id)
    return created.strftime("%Y-%m-%d") if created else "?"