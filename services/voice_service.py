"""Voice orchestration: owns all live voice connections and their heartbeat
supervisor. All work is scheduled onto the shared ``AsyncBridge`` loop so a
connection is always created, connected, and disconnected on the loop that
owns it (fixing the cross-loop cancellation of the old design).
"""

import asyncio
from typing import Any, Callable, Coroutine, TypeVar

from core.constants import RECENT_VOICE_MAX
from core.events import EventBus, VOICE_STATE_CHANGED
from services.vc import VoiceConnection
from utils.asyncs import AsyncBridge

T = TypeVar("T")


class VoiceService:
    """Centralizes the voice connection registry and decouples it from the UI."""

    def __init__(self, bridge: AsyncBridge, bus: EventBus,
                 settings_repo: Any, log: Callable[[str, str], None]) -> None:
        self._bridge = bridge
        self._bus = bus
        self._settings = settings_repo
        self._log_cb = log
        self._connections: dict[str, VoiceConnection] = {}

    def submit(self, coro: Coroutine[Any, Any, T]) -> "asyncio.Future[T]":
        return self._bridge.submit(coro)

    @property
    def connected_count(self) -> int:
        return len(self._connections)

    def get_connections(self) -> dict[str, VoiceConnection]:
        return dict(self._connections)

    def _make_token_label(self, token: str) -> str:
        return f"{token[:8]}…"

    def join(self, token: str, guild_id: str, channel_id: str,
             mute: bool = False, deaf: bool = False) -> "asyncio.Future[dict[str, Any]]":
        async def _join() -> dict[str, Any]:
            vc = self._connections.get(token)
            if vc is None:
                vc = VoiceConnection(
                    token,
                    on_log=lambda m, l="info": self._log_cb(
                        f"{self._make_token_label(token)} {m}", l),
                )
                self._connections[token] = vc
            res = await vc.join_voice(guild_id, channel_id, mute=mute, deaf=deaf)
            if not res.get("success"):
                self._connections.pop(token, None)
            else:
                self._bus.emit(VOICE_STATE_CHANGED, {"type": "joined", "token": token})
            return res

        return self.submit(_join())

    def leave(self, token: str) -> "asyncio.Future[None]":
        async def _leave() -> None:
            vc = self._connections.pop(token, None)
            if vc is not None:
                await vc.disconnect()
                self._bus.emit(VOICE_STATE_CHANGED, {"type": "left", "token": token})

        return self.submit(_leave())

    def disconnect_all(self) -> "asyncio.Future[None]":
        async def _all() -> None:
            conns = list(self._connections.values())
            self._connections.clear()
            for vc in conns:
                await vc.disconnect()
            self._bus.emit(VOICE_STATE_CHANGED, {"type": "all_cleared"})

        return self.submit(_all())

    def push_recent(self, guild_id: str, guild_name: str,
                    channel_id: str, channel_name: str) -> None:
        recent = list(self._settings.get("recent_voice", []) or [])
        recent.insert(0, {
            "guild_id": guild_id,
            "guild_name": guild_name,
            "channel_id": channel_id,
            "channel_name": channel_name,
        })
        self._settings.set("recent_voice", recent[:RECENT_VOICE_MAX])
        self._settings.save()

    def target_from_recent(self, index: int = 0) -> dict[str, str] | None:
        recent = list(self._settings.get("recent_voice", []) or [])
        if 0 <= index < len(recent):
            return dict(recent[index])
        return None


__all__ = ["VoiceService"]