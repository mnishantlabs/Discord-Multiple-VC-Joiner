"""Token validation orchestration.

Replaces the old ``validate_single/selected/all/_validate_worker`` methods on
the ``App`` class. Concurrency is a bounded semaphore on the shared loop; each
result is written back to the repository and an event is emitted per token so
the view can update its progress line by line.
"""

import asyncio
from typing import Any, Callable

from core.constants import API_BASE, FLAG_NAMES
from core.events import EventBus, VALIDATION_PROGRESS, STORE_CHANGED
from services.discord_client import DiscordClient
from storage.token_repository import TokenRepository
from utils.asyncs import AsyncBridge


class ValidationService:
    """Validates one or many tokens via the shared Discord client."""

    def __init__(
        self,
        bridge: AsyncBridge,
        bus: EventBus,
        client: DiscordClient,
        repo: TokenRepository,
        log: Callable[[str, str], None],
        semaphore_size: int = 10,
    ) -> None:
        self._bridge = bridge
        self._bus = bus
        self._client = client
        self._repo = repo
        self._log = log
        self._semaphore = asyncio.Semaphore(max(semaphore_size, 1))

    def run(self, tokens: list[str], on_done: Callable[[], None]) -> "asyncio.Future[None]":
        async def _run() -> None:
            async with asyncio.Semaphore(1):  # ensure `_run` waiting is trivial
                results = await asyncio.gather(*(self._validate_one(t) for t in tokens))
            self._bus.emit(STORE_CHANGED, {"validated": len(results)})
            on_done()

        return self._bridge.submit(_run())

    async def _validate_one(self, token: str) -> dict[str, Any]:
        async with self._semaphore:
            res = await self._call_me(token)
            if res.get("valid"):
                self._repo.add_token(token, res)
                self._log(f"{res.get('username', '?')} valid", "success")
            else:
                self._repo.update(token, {
                    "user_id": "",
                    "error": res.get("error", ""),
                    "code": res.get("code", ""),
                })
                self._log(f"{token[:8]}…: {res.get('error', '?')}", "error")
            self._bus.emit(VALIDATION_PROGRESS, {"token": token, "ok": bool(res.get("valid"))})
            return res

    async def _call_me(self, token: str) -> dict[str, Any]:
        try:
            async with self._client.session.get(
                f"{API_BASE}/users/@me", headers={"Authorization": token}
            ) as resp:
                return await self._interpret(resp, token)
        except Exception as exc:  # noqa: BLE001
            return {"valid": False, "error": str(exc)[:80], "code": "NETWORK"}

    async def _interpret(self, resp: Any, token: str) -> dict[str, Any]:
        if resp.status == 200:
            data = await resp.json()
            servers = await self._fetch_servers(token)
            flags_int = int(data.get("flags", 0) or 0)
            return {
                "valid": True,
                "username": data.get("username", "Unknown"),
                "discriminator": data.get("discriminator", "0"),
                "user_id": str(data.get("id", "")),
                "email": data.get("email"),
                "phone": data.get("phone"),
                "mfa_enabled": data.get("mfa_enabled", False),
                "is_bot": data.get("bot", False),
                "is_verified": data.get("verified", False),
                "premium_type": int(data.get("premium_type", 0) or 0),
                "flags": [name for bit, name in FLAG_NAMES.items() if flags_int & bit],
                "avatar": data.get("avatar"),
                "banner": data.get("banner"),
                "servers": servers,
            }
        if resp.status == 401:
            return {"valid": False, "error": "Invalid or expired token", "code": "INVALID"}
        if resp.status == 403:
            return {"valid": False, "error": "Locked (account flagged)", "code": "LOCKED"}
        if resp.status == 429:
            return {"valid": False, "error": "Rate limited", "code": "RATE_LIMIT"}
        return {"valid": False, "error": f"API error: {resp.status}", "code": str(resp.status)}

    async def _fetch_servers(self, token: str) -> list[dict[str, str]]:
        try:
            async with self._client.session.get(
                f"{API_BASE}/users/@me/guilds", headers={"Authorization": token}
            ) as resp:
                if resp.status == 200:
                    guilds = await resp.json()
                    return [{"id": str(g["id"]), "name": g["name"]} for g in guilds]
        except Exception:  # noqa: BLE001
            pass
        return []


__all__ = ["ValidationService"]