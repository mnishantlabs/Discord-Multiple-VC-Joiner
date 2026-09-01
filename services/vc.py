"""The Discord gateway voice connection.

Critically, a connection owns its asyncio loop: it must be created, connected,
and disconnected all from the *same* loop (the shared ``AsyncBridge`` loop).
The heartbeat task lives on that loop and survives the call that performed the
join, which was the bug in the old design where the heartbeat died when its
event loop was closed after a one-shot call.
"""

import asyncio
import json
from typing import Any, Callable

import websockets

from core.constants import GATEWAY_URL, HEADERS

LogCallback = Callable[[str, str], None]


class VoiceConnection:
    """A single gateway connection used to join/leave one voice channel."""

    def __init__(
        self,
        token: str,
        on_log: LogCallback | None = None,
        settings: Any | None = None,
        loop: asyncio.AbstractEventLoop | None = None,
    ) -> None:
        self.token = token
        self.on_log = on_log or (lambda m, c="info": None)
        self.settings = settings
        self.loop = loop
        self.ws: websockets.WebSocketClientProtocol | None = None
        self.heartbeat_task: asyncio.Task | None = None
        self.heartbeat_interval: float = 0.0
        self.session_id: str | None = None
        self.sequence: int = 0
        self.connected = False

    async def connect(self) -> bool:
        try:
            self.ws = await websockets.connect(
                GATEWAY_URL,
                additional_headers=HEADERS,
                user_agent_header=HEADERS["User-Agent"],
                max_size=None,
            )
            hello = json.loads(await self.ws.recv())
            if hello.get("op") == 10:
                self.heartbeat_interval = float(hello["d"]["heartbeat_interval"]) / 1000.0
            identify = {
                "op": 2,
                "d": {
                    "token": self.token,
                    "properties": {"$os": "windows", "$browser": "chrome", "$device": "chrome"},
                    "presence": {"status": "online", "afk": False},
                },
            }
            await self.ws.send(json.dumps(identify))
            self.heartbeat_task = asyncio.ensure_future(self._heartbeat())
            deadline = self._loop().time() + 15
            while self._loop().time() < deadline:
                try:
                    msg = await asyncio.wait_for(self.ws.recv(), timeout=5)
                    data = json.loads(msg)
                    if data.get("op") == 9:
                        self.on_log("Invalid session (token rejected)", "error")
                        return False
                    if data.get("op") == 0:
                        self.sequence = data.get("s", self.sequence)
                        if data.get("t") == "READY":
                            self.session_id = data["d"].get("session_id", "")
                            self.connected = True
                            self.on_log("Gateway ready", "success")
                            return True
                except asyncio.TimeoutError:
                    continue
                except Exception:
                    self.on_log("Connection closed before ready (invalid token?)", "error")
                    return False
            self.connected = True
            return True
        except Exception as e:  # noqa: BLE001
            self.on_log(f"Connection failed: {e}", "error")
            return False

    def _loop(self) -> asyncio.AbstractEventLoop:
        if self.loop is not None:
            return self.loop
        return asyncio.get_event_loop()

    async def _heartbeat(self) -> None:
        try:
            while self.connected and self.ws is not None:
                await self.ws.send(json.dumps({"op": 1, "d": self.sequence}))
                await asyncio.sleep(self.heartbeat_interval)
        except Exception:  # noqa: BLE001
            self.connected = False

    async def join_voice(self, guild_id: str, channel_id: str,
                         mute: bool = False, deaf: bool = False) -> dict[str, Any]:
        if not self.connected:
            ok = await self.connect()
            if not ok:
                return {"success": False, "error": "Failed to connect to gateway"}
        try:
            await self.ws.send(json.dumps({
                "op": 4,
                "d": {
                    "guild_id": guild_id,
                    "channel_id": channel_id,
                    "self_mute": mute,
                    "self_deaf": deaf,
                },
            }))
            deadline = self._loop().time() + 12
            while self._loop().time() < deadline:
                try:
                    msg = await asyncio.wait_for(self.ws.recv(), timeout=5)
                    data = json.loads(msg)
                    op = data.get("op")
                    if op == 0:
                        t = data.get("t")
                        if t == "VOICE_STATE_UPDATE":
                            self.session_id = data["d"].get("session_id", self.session_id)
                        elif t == "VOICE_SERVER_UPDATE":
                            self.on_log(f"Voice connected to channel {channel_id}", "success")
                            return {"success": True, "session_id": self.session_id}
                    elif op == 11:
                        self.sequence = data["d"]
                except asyncio.TimeoutError:
                    continue
            return {"success": False, "error": "Voice handshake timed out"}
        except Exception as e:  # noqa: BLE001
            return {"success": False, "error": str(e)}

    async def leave_voice(self, guild_id: str) -> None:
        if not self.connected:
            return
        try:
            await self.ws.send(json.dumps({
                "op": 4,
                "d": {"guild_id": guild_id, "channel_id": None,
                      "self_mute": False, "self_deaf": False},
            }))
        except Exception:  # noqa: BLE001
            pass

    async def disconnect(self) -> None:
        self.connected = False
        if self.heartbeat_task is not None:
            self.heartbeat_task.cancel()
            self.heartbeat_task = None
        if self.ws is not None:
            try:
                await self.ws.close()
            except Exception:  # noqa: BLE001
                pass
            self.ws = None
        self.on_log("Disconnected", "info")


__all__ = ["VoiceConnection"]