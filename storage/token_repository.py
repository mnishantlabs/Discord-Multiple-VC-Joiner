"""Repository over ``tokens.json``.

The on-disk schema is stable (shared with older app versions). Each token is
keyed by the token string and its value is an info dict:

.. code-block:: json

    {"username": "...", "discriminator": "0", "user_id": "...", "servers": [...]}

The server map (a costly O(tokens x servers) view used by the UI) is memoized
and invalidated on every mutation.
"""

import json
import threading
from typing import Any, Callable, Iterator

from storage import paths


def _tokens_file() -> str:
    """Resolve the tokens path lazily so tests can redirect it."""
    return paths.TOKENS_FILE


class TokenRepository:
    """Stores and queries Discord tokens. Not thread-safe by itself; the caller
    serializes access (services run on the single async loop, views on Tk)."""

    def __init__(self) -> None:
        self.data: dict[str, dict[str, Any]] = {}
        self._lock = threading.RLock()
        self._server_cache: dict[str, dict[str, Any]] | None = None
        self.load()

    # ---- persistence -------------------------------------------------------------
    def load(self) -> None:
        try:
            with open(_tokens_file(), "r", encoding="utf-8") as f:
                stored = json.load(f)
            tokens = stored.get("tokens", {}) if isinstance(stored, dict) else {}
            if not isinstance(tokens, dict):
                tokens = {}
        except (OSError, ValueError):
            tokens = {}
        with self._lock:
            self.data = tokens
            self._server_cache = None

    def save(self) -> None:
        with self._lock:
            try:
                with open(_tokens_file(), "w", encoding="utf-8") as f:
                    json.dump({"tokens": self.data}, f, indent=2, ensure_ascii=False)
            except OSError:
                pass

    # ---- queries -----------------------------------------------------------------
    def get_all(self) -> dict[str, dict[str, Any]]:
        with self._lock:
            return dict(self.data)

    def get(self, token: str) -> dict[str, Any]:
        with self._lock:
            return self.data.get(token, {})

    def contains(self, token: str) -> bool:
        with self._lock:
            return token in self.data

    def __len__(self) -> int:
        with self._lock:
            return len(self.data)

    def __iter__(self) -> Iterator[str]:
        with self._lock:
            return iter(list(self.data.keys()))

    def items(self) -> Iterator[tuple[str, dict[str, Any]]]:
        with self._lock:
            return iter(list(self.data.items()))

    def get_server_map(self) -> dict[str, dict[str, Any]]:
        """Map ``{server_name: {"id": ..., "tokens": [{token, username}, ...]}}``."""
        with self._lock:
            if self._server_cache is not None:
                return dict(self._server_cache)
            smap: dict[str, dict[str, Any]] = {}
            for token, info in self.data.items():
                for server in info.get("servers", []):
                    name = server["name"]
                    entry = smap.get(name)
                    if entry is None:
                        entry = {"id": server["id"], "tokens": []}
                        smap[name] = entry
                    entry["tokens"].append({
                        "token": token,
                        "username": info.get("username", "Unknown"),
                    })
            self._server_cache = smap
            return dict(smap)

    # ---- mutations (all invalidate the memo) -------------------------------------
    def _invalidate(self) -> None:
        self._server_cache = None

    def add_token(self, token: str, info: dict[str, Any]) -> None:
        with self._lock:
            self.data[token] = self._normalize(info)
            self._invalidate()

    def update(self, token: str, info: dict[str, Any]) -> None:
        with self._lock:
            if token in self.data:
                self.data[token].update(info)
                self._invalidate()

    def rename(self, token: str, name: str) -> None:
        with self._lock:
            if token in self.data:
                self.data[token]["username"] = name
                self._invalidate()

    def remove_token(self, token: str) -> None:
        with self._lock:
            self.data.pop(token, None)
            self._invalidate()

    def remove_by_ids(self, ids: set[str]) -> int:
        with self._lock:
            to_remove = [t for t, i in self.data.items() if i.get("user_id") in ids]
            for t in to_remove:
                del self.data[t]
            self._invalidate()
            return len(to_remove)

    def remove_invalid(self) -> int:
        with self._lock:
            to_remove = [t for t, i in self.data.items() if not i.get("user_id")]
            for t in to_remove:
                del self.data[t]
            self._invalidate()
            return len(to_remove)

    def remove_locked(self) -> int:
        with self._lock:
            to_remove = [t for t, i in self.data.items()
                         if not i.get("user_id") and i.get("flags")]
            for t in to_remove:
                del self.data[t]
            self._invalidate()
            return len(to_remove)

    def export_json(self, tokens: dict[str, dict[str, Any]] | None = None) -> str:
        with self._lock:
            export = tokens if tokens is not None else self.data
            return json.dumps(export, indent=2, ensure_ascii=False)

    # ---- helpers -----------------------------------------------------------------
    @staticmethod
    def _normalize(info: dict[str, Any]) -> dict[str, Any]:
        """Persist only the stable schema fields (keeps old add_token behavior)."""
        return {
            "username": info.get("username", "Unknown"),
            "discriminator": info.get("discriminator", "0"),
            "user_id": info.get("user_id", ""),
            "email": info.get("email"),
            "phone": info.get("phone"),
            "mfa_enabled": info.get("mfa_enabled", False),
            "is_bot": info.get("is_bot", False),
            "is_verified": info.get("is_verified", False) or info.get("verified", False),
            "premium_type": info.get("premium_type", 0),
            "flags": info.get("flags", []),
            "servers": info.get("servers", []),
        }