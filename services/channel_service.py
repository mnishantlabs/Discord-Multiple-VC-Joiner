"""Voice-channel listing with a tiny cache (replaces ``load_channels`` /
``get_channels`` calls from the view)."""

from typing import Any, Callable

from core.constants import API_BASE
from core.events import EventBus, CHANNELS_CHANGED
from services.discord_client import DiscordClient
from utils.asyncs import AsyncBridge


class ChannelService:
    """Lists the voice channels of a guild and caches the last result."""

    def __init__(self, bridge: AsyncBridge, bus: EventBus,
                 client: DiscordClient, log: Callable[[str, str], None]) -> None:
        self._bridge = bridge
        self._bus = bus
        self._client = client
        self._log = log
        self._cache: dict[str, list[dict[str, Any]]] = {}

    def run(self, token: str, guild_id: str, on_done: Callable[[list[dict[str, Any]]], None]) -> "Any":
        async def _load() -> None:
            channels: list[dict[str, Any]] = []
            try:
                async with self._client.session.get(
                    f"{API_BASE}/guilds/{guild_id}/channels", headers={"Authorization": token}
                ) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        channels = [
                            {"id": str(c["id"]), "name": c["name"], "type": c["type"]}
                            for c in data if c.get("type") in (0, 2, 4)
                        ]
            except Exception as exc:  # noqa: BLE001
                self._log(f"Channel load failed: {exc}", "error")
            voice = [{"id": c["id"], "name": c["name"]} for c in channels if c.get("type") == 2]
            self._cache[guild_id] = voice
            self._bus.emit(CHANNELS_CHANGED, {"guild_id": guild_id, "channels": voice})
            on_done(voice)

        # stagger repeated requests for the same guild
        async def _run() -> None:
            await _load()

        return self._bridge.submit(_run())

    def cached(self, guild_id: str) -> list[dict[str, Any]]:
        return list(self._cache.get(guild_id, []))


__all__ = ["ChannelService"]