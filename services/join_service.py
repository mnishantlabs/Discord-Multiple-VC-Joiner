"""Server-join orchestration (replaces the ``_do_action`` 'join' branch)."""

from typing import Any, Callable

from core.constants import API_BASE
from core.events import EventBus, STORE_CHANGED
from services.discord_client import DiscordClient
from storage.token_repository import TokenRepository
from utils.asyncs import AsyncBridge


class JoinService:
    """Joins one or more tokens to an invite via the shared Discord client."""

    def __init__(
        self,
        bridge: AsyncBridge,
        bus: EventBus,
        client: DiscordClient,
        repo: TokenRepository,
        log: Callable[[str, str], None],
    ) -> None:
        self._bridge = bridge
        self._bus = bus
        self._client = client
        self._repo = repo
        self._log = log

    def run(self, tokens: list[str], invite: str, on_done: Callable[[], None]) -> "Any":
        code = invite.strip().split("/")[-1]

        async def _join_one(token: str) -> tuple[str, str]:
            uname = self._repo.get(token).get("username", "Unknown")
            result = await self._call(code, token)
            if result.get("success"):
                guild_id = str(result.get("guild_id", ""))
                guild_name = result.get("guild_name", "Unknown")
                servers = list(self._repo.get(token).get("servers", []))
                if not any(s.get("id") == guild_id for s in servers):
                    servers.append({"id": guild_id, "name": guild_name})
                    self._repo.update(token, {"servers": servers})
                return f"{uname} joined {guild_name}", "success"
            return f"{uname}: {result.get('error', '?')}", "error"

        async def _run() -> None:
            from concurrent.futures import ThreadPoolExecutor
            # simple sequential-with-delay loop preserving original semantics
            for token in tokens:
                msg, level = await _join_one(token)
                self._log(msg, level)
            self._bus.emit(STORE_CHANGED, {"joined": len(tokens)})
            on_done()

        return self._bridge.submit(_run())

    async def _call(self, code: str, token: str) -> dict[str, Any]:
        try:
            async with self._client.session.post(
                f"{API_BASE}/invites/{code}", headers={"Authorization": token}
            ) as resp:
                return await self._interpret(resp)
        except Exception as exc:  # noqa: BLE001
            return {"success": False, "error": str(exc)[:80]}

    async def _interpret(self, resp: Any) -> dict[str, Any]:
        if resp.status == 200:
            data = await resp.json()
            return {
                "success": True,
                "guild_name": data.get("guild", {}).get("name", "Unknown"),
                "guild_id": str(data.get("guild", {}).get("id", "")),
                "channel_name": data.get("channel", {}).get("name", "Unknown"),
            }
        if resp.status == 400:
            return {"success": False, "error": "Invalid invite or already in server"}
        if resp.status == 404:
            return {"success": False, "error": "Invite not found or expired"}
        if resp.status == 429:
            return {"success": False, "error": "Rate limited"}
        text = await resp.text()
        return {"success": False, "error": f"Error {resp.status}: {text[:80]}"}


__all__ = ["JoinService"]