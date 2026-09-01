"""Command grouping for user-intent actions decoupled from widgets.

Each method takes a :class:`CommandContext` that bundles the services/state a
command needs. Nothing here imports tkinter, so commands are testable and can
be triggered from menus, toolbars, and keyboard shortcuts alike.
"""

from typing import Any


class CommandContext:
    """Aggregates the dependencies (services + state accessors) a command needs."""

    def __init__(
        self,
        state: Any,
        log: Any,
        voice: Any,
        store: Any,
        clipboard_set: Any,
        refresh: Any,
    ) -> None:
        self.state = state            # AppState
        self.log = log                # LogService.log(message, level)
        self.voice = voice            # VoiceService
        self.store = store            # TokenRepository
        self.clipboard_set = clipboard_set
        self.refresh = refresh        # callable to re-render the UI

    # ---- voice -----------------------------------------------------------------
    def leave_voice(self) -> None:
        tokens = list(self.voice.get_connections().keys())
        self.voice.disconnect_all()
        self.log(f"Left voice on {len(tokens)} token(s)", "warn")
        self.refresh()


class Commands:
    """Method-group of command implementations."""

    @staticmethod
    def leave_voice(cmd: CommandContext) -> None:
        cmd.leave_voice()

    @staticmethod
    def copy_selected_ids(cmd: CommandContext) -> None:
        ids = []
        for token in cmd.state.selected:
            uid = cmd.store.get(token).get("user_id", "")
            if uid:
                ids.append(uid)
        if ids:
            cmd.clipboard_set("\n".join(ids))
            cmd.log(f"Copied {len(ids)} user ID(s)", "info")

    @staticmethod
    def copy_selected_usernames(cmd: CommandContext) -> None:
        names = []
        for token in cmd.state.selected:
            info = cmd.store.get(token)
            names.append(f"{info.get('username', '?')}#{info.get('discriminator', '0')}")
        if names:
            cmd.clipboard_set("\n".join(names))
            cmd.log(f"Copied {len(names)} username(s)", "info")


__all__ = ["Commands", "CommandContext"]