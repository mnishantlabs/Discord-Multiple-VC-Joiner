"""Immutable network and application constants."""

API_BASE = "https://discord.com/api/v9"
GATEWAY_URL = "wss://gateway.discord.gg/?v=9&encoding=json"

USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0 Safari/537.36"
)
HEADERS = {"User-Agent": USER_AGENT}

FLAG_NAMES = {
    1: "Staff",
    2: "Partner",
    4: "Hypesquad",
    8: "Bug Hunter",
    16384: "Bug Hunter Level 2",
    131072: "Verified Developer",
    262144: "Moderator Programs",
    1 << 18: "Active Developer",
}

DEFAULT_GEOMETRY = "1380x880"
MIN_GEOMETRY = "1100x700"

LOG_BUFFER_SIZE = 1000          # ring buffer size for the activity log
RECENT_VOICE_MAX = 8            # voice targets remembered in config
INVITE_HISTORY_MAX = 4          # recent invites shown in the action bar
RECENT_VOICE_SHOWN = 3          # recent voice targets rendered in the voice panel
USER_ID_SNIPPET = 14            # characters of a user id shown on a token card
FLAGS_SNIPPET = 6               # badge names shown in tooltips/details