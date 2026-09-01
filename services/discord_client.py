"""Shared async Discord HTTP client with a global rate limiter.

The old code created a fresh aiohttp connector + session per API call, which
opened a new connection pool each time and had no shared rate limiting — so
multi-account batches reliably tripped Discord's 429s. This client holds one
session for the whole app and serializes requests through a token-bucket plus
handles ``Retry-After``.
"""

import asyncio
import time
from typing import Any

import aiohttp

from core.constants import API_BASE, HEADERS
from storage.settings_repository import SettingsRepository


class RateLimiter:
    """Simple token-bucket limiter; one instance shared across all tokens."""

    def __init__(self, per_second: float = 40.0, burst: int = 10) -> None:
        self._rate = per_second
        self._burst = burst
        self._tokens = float(burst)
        self._updated = time.monotonic()

    async def acquire(self) -> None:
        while True:
            now = time.monotonic()
            self._tokens = min(
                self._burst,
                self._tokens + (now - self._updated) * self._rate,
            )
            self._updated = now
            if self._tokens >= 1.0:
                self._tokens -= 1.0
                return
            await asyncio.sleep((1.0 - self._tokens) / self._rate)


class DiscordClient:
    """Thin async wrapper over the Discord REST API operating on one session."""

    def __init__(
        self,
        settings: SettingsRepository,
        connector_kwargs: dict[str, Any] | None = None,
    ) -> None:
        self._settings = settings
        self._connector_kwargs = connector_kwargs or {}
        self._session: aiohttp.ClientSession | None = None
        self._limiter = RateLimiter()

    async def start(self) -> None:
        if self._session is None:
            self._session = aiohttp.ClientSession(
                connector=aiohttp.TCPConnector(
                    limit=int(self._settings.get("concurrency", 5) or 5)
                )
            )

    @property
    def session(self) -> aiohttp.ClientSession:
        if self._session is None:
            raise RuntimeError("DiscordClient.start() must be called first")
        return self._session

    @property
    def limiter(self) -> RateLimiter:
        return self._limiter

    def _proxy_kwargs(self) -> dict[str, str]:
        proxy = str(self._settings.get("proxy", "") or "").strip()
        return {"proxy": proxy} if proxy else {}

    def _timeout(self) -> aiohttp.ClientTimeout:
        return aiohttp.ClientTimeout(total=float(self._settings.get("api_timeout", 10) or 10))

    async def _request(self, method: str, path: str, token: str | None,
                       **kwargs: Any) -> aiohttp.ClientResponse:
        session = self.session
        headers = dict(HEADERS)
        if token:
            headers["Authorization"] = token
        for attempt in range(4):
            await self._limiter.acquire()
            async with session.request(
                method, f"{API_BASE}{path}", headers=headers,
                timeout=self._timeout(), **self._proxy_kwargs(), **kwargs
            ) as resp:
                if resp.status == 429:
                    retry = float(resp.headers.get("Retry-After", 3.0) or 3.0)
                    await asyncio.sleep(retry)
                    continue
                return resp
        # exhausted retries; manufacture a minimal resp-like signal
        return _RateLimitedResponse()


class _RateLimitedResponse:
    status = 429
    headers = {}

    async def json(self) -> dict:
        return {}

    async def text(self) -> str:
        return "Rate limited"


async def close_client(client: DiscordClient) -> None:
    if client._session is not None:
        await client._session.close()
        client._session = None


__all__ = ["DiscordClient", "RateLimiter", "close_client"]