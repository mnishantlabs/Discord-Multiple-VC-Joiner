"""High-level UI actions (join selected tokens to the voice target, etc.).

This sits above the raw services and wires AppState + VoiceService together so
view buttons can delegate their intent without knowing the service plumbing.
"""

from typing import Any

from core.events import EventBus, VOICE_STATE_CHANGED


class ActionsController:
    """Bundles the operations the action bar buttons invoke."""

    def __init__(self, ctx: Any, voice: Any, log: Any) -> None:
        self._ctx = ctx
        self._voice = voice
        self._log = log

    def join_selected(self) -> None:
        state = self._ctx.state
        target = state.selected_channel
        if not target:
            self._log("Select a voice channel first", "warn")
            return
        tokens = list(state.selected) or list(self._ctx.store.get_all().keys())
        guild_id = state.selected_server["id"] if state.selected_server else target.get("guild_id", "")
        self._log(f"Joining {len(tokens)} token(s) to {target['name']}", "info")
        result_summary = []
        for token in tokens:
            fut = self._voice.join(token, guild_id, target["id"])
            fut.add_done_callback(lambda f: self._on_join_done(f, result_summary))
        if not (state.selected_server and state.selected_channel):
            self._voice.push_recent(guild_id, state.selected_server["name"] if state.selected_server else "",
                                    target["id"], target["name"])

    def _on_join_done(self, fut, result_summary) -> None:
        try:
            res = fut.result()
            if res.get("success"):
                result_summary.append(res)
        except Exception as exc:  # noqa: BLE001
            self._ctx.log.error(f"Join failed: {exc}")

    def disconnect_all(self) -> None:
        self._voice.disconnect_all()
        self._log("Disconnected from all voice channels", "warn")
