"""Token import/export.

The persistence half of import/export is deliberately decoupled from dialogs:
it reads/writes plain strings and dicts, and the view owns file pickers /
paste boxes. Resolution of raw tokens (network) lives in a small async method
here that reuses :class:`ValidationService`.
"""

from typing import Any, Callable, Iterable

from core.events import EventBus, STORE_CHANGED
from services.validation_service import ValidationService
from storage.token_repository import TokenRepository
from utils.asyncs import AsyncBridge


def parse_lines(raw: Iterable[str]) -> list[str]:
    """Normalize + dedupe raw text lines into candidate tokens (pure)."""
    seen: set[str] = set()
    out: list[str] = []
    for line in raw:
        token = line.strip()
        if token and token not in seen:
            seen.add(token)
            out.append(token)
    return out


class ImportExportService:
    def __init__(
        self,
        bridge: AsyncBridge,
        bus: EventBus,
        repo: TokenRepository,
        validator: ValidationService,
        log: Callable[[str, str], None],
    ) -> None:
        self._bridge = bridge
        self._bus = bus
        self._repo = repo
        self._validator = validator
        self._log = log

    def export(self, tokens: dict[str, dict[str, Any]] | None = None) -> str:
        return self._repo.export_json(tokens)

    def resolve_import(
        self, raw: Iterable[str],
        on_progress: Callable[[int, int], None],
        on_done: Callable[[int], None],
    ) -> "Any":
        """Resolve pasted/loaded tokens, persist valid ones, count new entries."""
        candidates = parse_lines(raw)
        all_tokens = set(self._repo.get_all().keys())
        new_tokens = [t for t in candidates if t not in all_tokens]

        async def _run() -> None:
            added = 0
            total = len(new_tokens)
            for idx, token in enumerate(new_tokens):
                res = await self._validator._call_me(token)
                if res.get("valid"):
                    self._repo.add_token(token, res)
                    added += 1
                    self._bus.emit(STORE_CHANGED, {"imported": token})
                else:
                    self._repo.add_token(token, {
                        "user_id": "", "error": res.get("error", ""),
                        "code": res.get("code", ""),
                    })
                on_progress(idx + 1, total)
            on_done(added)

        return self._bridge.submit(_run())


__all__ = ["ImportExportService", "parse_lines"]