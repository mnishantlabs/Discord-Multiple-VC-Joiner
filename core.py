import json
import os
import sys
import asyncio
import time
import shutil
import aiohttp
import websockets

API_BASE = "https://discord.com/api/v9"
GATEWAY_URL = "wss://gateway.discord.gg/?v=9&encoding=json"
BASE = os.path.dirname(os.path.abspath(__file__))
HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}


def _app_data_dir():
    if sys.platform == "win32":
        base = os.getenv("APPDATA") or os.path.join(os.path.expanduser("~"), "AppData", "Roaming")
    else:
        base = os.getenv("XDG_CONFIG_HOME") or os.path.join(os.path.expanduser("~"), ".config")
    return os.path.join(base, "DiscordTokenManager")


APP_DATA_DIR = _app_data_dir()


def _migrate_legacy_files():
    """Move tokens.json / config.json from the script folder to AppData once."""
    os.makedirs(APP_DATA_DIR, exist_ok=True)
    for name in ("tokens.json", "config.json"):
        legacy = os.path.join(BASE, name)
        target = os.path.join(APP_DATA_DIR, name)
        if os.path.exists(legacy) and not os.path.exists(target):
            try:
                shutil.copy2(legacy, target)
            except Exception:
                pass


_migrate_legacy_files()

TOKENS_FILE = os.path.join(APP_DATA_DIR, "tokens.json")
CONFIG_FILE = os.path.join(APP_DATA_DIR, "config.json")

FLAG_NAMES = {
    1: "Staff", 2: "Partner", 4: "Hypesquad", 8: "Bug Hunter",
    16384: "Bug Hunter Level 2", 131072: "Verified Developer", 262144: "Moderator Programs",
    1 << 18: "Active Developer",
}


class Config:
    def __init__(self):
        self.data = {
            "theme": "Dark",
            "accent": "blue",
            "concurrency": 5,
            "retry_delay": 3,
            "proxy": "",
            "api_timeout": 10,
            "auto_validate": False,
            "auto_save": True,
            "delay": 0.5,
            "show_badges": True,
            "show_ids": True,
            "pinned_servers": [],
            "recent_voice": [],
            "geometry": "",
            "compact": False,
        }
        self.load()

    def load(self):
        try:
            if os.path.exists(CONFIG_FILE):
                with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                    loaded = json.load(f)
                    for k in self.data:
                        if k in loaded:
                            self.data[k] = loaded[k]
        except Exception:
            pass

    def save(self):
        try:
            with open(CONFIG_FILE, "w", encoding="utf-8") as f:
                json.dump(self.data, f, indent=2)
        except Exception:
            pass

    def get(self, key, default=None):
        return self.data.get(key, self.data.get(key, default))


def _timeout(cfg):
    return aiohttp.ClientTimeout(total=cfg.get("api_timeout", 10))


def _connector(cfg):
    proxy = (cfg.get("proxy") or "").strip()
    if proxy:
        return aiohttp.TCPConnector(limit=cfg.get("concurrency", 5), force_close=True)
    return aiohttp.TCPConnector(limit=cfg.get("concurrency", 5))


def _proxy(cfg):
    proxy = (cfg.get("proxy") or "").strip()
    return {"proxy": proxy} if proxy else {}


async def validate_token(token, cfg=None):
    cfg = cfg or Config()
    token = token.strip()
    if not token:
        return {"valid": False, "error": "Empty token"}
    retries = 0
    connector = _connector(cfg)
    try:
        async with aiohttp.ClientSession(connector=connector) as session:
            while True:
                try:
                    headers = {**HEADERS, "Authorization": token}
                    async with session.get(f"{API_BASE}/users/@me", headers=headers, timeout=_timeout(cfg), **_proxy(cfg)) as resp:
                        if resp.status == 200:
                            data = await resp.json()
                            servers = await fetch_servers(session, token, cfg)
                            prem = data.get("premium_type", 0)
                            flags = data.get("flags", 0)
                            flag_names = [n for bit, n in FLAG_NAMES.items() if flags & bit]
                            return {
                                "valid": True,
                                "username": data.get("username", "Unknown"),
                                "discriminator": data.get("discriminator", "0"),
                                "user_id": data.get("id", ""),
                                "email": data.get("email"),
                                "phone": data.get("phone"),
                                "mfa_enabled": data.get("mfa_enabled", False),
                                "is_bot": data.get("bot", False),
                                "is_verified": data.get("verified", False),
                                "premium_type": prem,
                                "flags": flag_names,
                                "avatar": data.get("avatar"),
                                "banner": data.get("banner"),
                                "servers": servers,
                            }
                        elif resp.status == 401:
                            return {"valid": False, "error": "Invalid or expired token", "code": "INVALID"}
                        elif resp.status == 403:
                            return {"valid": False, "error": "Locked (account flagged)", "code": "LOCKED"}
                        elif resp.status == 429:
                            retry = float(resp.headers.get("Retry-After", cfg.get("retry_delay", 3)))
                            if retries >= 3:
                                return {"valid": False, "error": "Rate limited", "code": "RATE_LIMIT"}
                            await asyncio.sleep(retry)
                            retries += 1
                            continue
                        else:
                            return {"valid": False, "error": f"API error: {resp.status}", "code": str(resp.status)}
                except asyncio.TimeoutError:
                    if retries >= 3:
                        return {"valid": False, "error": "Timeout", "code": "TIMEOUT"}
                    retries += 1
                    await asyncio.sleep(cfg.get("retry_delay", 3))
                except aiohttp.ClientError as e:
                    if retries >= 3:
                        return {"valid": False, "error": str(e)[:80], "code": "NETWORK"}
                    retries += 1
                    await asyncio.sleep(cfg.get("retry_delay", 3))
    finally:
        await connector.close()


async def fetch_servers(session, token, cfg=None):
    headers = {**HEADERS, "Authorization": token}
    try:
        async with session.get(f"{API_BASE}/users/@me/guilds", headers=headers, timeout=_timeout(cfg), **_proxy(cfg)) as resp:
            if resp.status == 200:
                guilds = await resp.json()
                return [{"id": g["id"], "name": g["name"]} for g in guilds]
    except Exception:
        pass
    return []


async def join_server(token, invite_code, cfg=None):
    cfg = cfg or Config()
    invite_code = invite_code.strip().split("/")[-1]
    retries = 0
    connector = _connector(cfg)
    try:
        async with aiohttp.ClientSession(connector=connector) as session:
            while True:
                try:
                    headers = {**HEADERS, "Authorization": token}
                    async with session.post(f"{API_BASE}/invites/{invite_code}", headers=headers, timeout=_timeout(cfg), **_proxy(cfg)) as resp:
                        if resp.status == 200:
                            data = await resp.json()
                            return {
                                "success": True,
                                "guild_name": data.get("guild", {}).get("name", "Unknown"),
                                "guild_id": data.get("guild", {}).get("id", ""),
                                "channel_name": data.get("channel", {}).get("name", "Unknown"),
                            }
                        elif resp.status == 400:
                            return {"success": False, "error": "Invalid invite or already in server"}
                        elif resp.status == 404:
                            return {"success": False, "error": "Invite not found or expired"}
                        elif resp.status == 429:
                            retry = float(resp.headers.get("Retry-After", cfg.get("retry_delay", 3)))
                            if retries >= 3:
                                return {"success": False, "error": "Rate limited"}
                            await asyncio.sleep(retry)
                            retries += 1
                            continue
                        else:
                            text = await resp.text()
                            return {"success": False, "error": f"Error {resp.status}: {text[:80]}"}
                except asyncio.TimeoutError:
                    if retries >= 3:
                        return {"success": False, "error": "Timeout"}
                    retries += 1
                    await asyncio.sleep(cfg.get("retry_delay", 3))
                except aiohttp.ClientError as e:
                    if retries >= 3:
                        return {"success": False, "error": str(e)[:80]}
                    retries += 1
                    await asyncio.sleep(cfg.get("retry_delay", 3))
    finally:
        await connector.close()


async def get_channels(token, guild_id, cfg=None):
    cfg = cfg or Config()
    connector = _connector(cfg)
    try:
        async with aiohttp.ClientSession(connector=connector) as session:
            headers = {**HEADERS, "Authorization": token}
            async with session.get(f"{API_BASE}/guilds/{guild_id}/channels", headers=headers, timeout=_timeout(cfg), **_proxy(cfg)) as resp:
                if resp.status == 200:
                    channels = await resp.json()
                    return [
                        {"id": c["id"], "name": c["name"], "type": c["type"]}
                        for c in channels if c["type"] in (0, 2, 4)
                    ]
    except Exception:
        pass
    return []


async def get_guild_preview(guild_id, cfg=None):
    cfg = cfg or Config()
    connector = _connector(cfg)
    try:
        async with aiohttp.ClientSession(connector=connector) as session:
            async with session.get(f"{API_BASE}/guilds/{guild_id}/preview", timeout=_timeout(cfg), **_proxy(cfg)) as resp:
                if resp.status == 200:
                    d = await resp.json()
                    return {
                        "name": d.get("name"),
                        "icon": d.get("icon"),
                        "members": d.get("approximate_member_count", 0),
                        "online": d.get("approximate_presence_count", 0),
                        "boosts": d.get("premium_subscription_count", 0),
                        "channels": len(d.get("channels", [])) + len(d.get("categories", [])),
                    }
    except Exception:
        pass
    return None


async def leave_guild(token, guild_id, cfg=None):
    cfg = cfg or Config()
    connector = _connector(cfg)
    try:
        async with aiohttp.ClientSession(connector=connector) as session:
            headers = {**HEADERS, "Authorization": token}
            async with session.delete(f"{API_BASE}/users/@me/guilds/{guild_id}", headers=headers, timeout=_timeout(cfg), **_proxy(cfg)) as resp:
                return resp.status in (200, 204)
    finally:
        await connector.close()


async def ping_api(cfg=None):
    cfg = cfg or Config()
    connector = _connector(cfg)
    try:
        async with aiohttp.ClientSession(connector=connector) as session:
            async with session.get(f"{API_BASE}/gateway", timeout=_timeout(cfg), **_proxy(cfg)) as resp:
                return 200 <= resp.status < 500
    except Exception:
        return False
    finally:
        await connector.close()


class VoiceConnection:
    def __init__(self, token, cfg=None, on_log=None):
        self.token = token
        self.ws = None
        self.heartbeat_task = None
        self.heartbeat_interval = None
        self.session_id = None
        self.sequence = 0
        self.connected = False
        self.on_log = on_log or (lambda m, c="info": None)
        self.cfg = cfg or Config()

    async def connect(self):
        try:
            self.ws = await websockets.connect(
                GATEWAY_URL,
                additional_headers=HEADERS,
                user_agent_header=HEADERS["User-Agent"],
                max_size=None,
            )
            hello = json.loads(await self.ws.recv())
            if hello["op"] == 10:
                self.heartbeat_interval = hello["d"]["heartbeat_interval"] / 1000
            identify = {
                "op": 2,
                "d": {
                    "token": self.token,
                    "properties": {"$os": "windows", "$browser": "chrome", "$device": "chrome"},
                    "presence": {"status": "online", "afk": False},
                },
            }
            await self.ws.send(json.dumps(identify))
            self.heartbeat_task = asyncio.create_task(self._heartbeat())
            deadline = time.time() + 15
            while time.time() < deadline:
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
        except Exception as e:
            self.on_log(f"Connection failed: {e}", "error")
            return False

    async def _heartbeat(self):
        try:
            while self.connected and self.ws:
                await self.ws.send(json.dumps({"op": 1, "d": self.sequence}))
                await asyncio.sleep(self.heartbeat_interval)
        except Exception:
            self.connected = False

    async def join_voice(self, guild_id, channel_id, mute=False, deaf=False):
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
            deadline = time.time() + 12
            while time.time() < deadline:
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
        except Exception as e:
            return {"success": False, "error": str(e)}

    async def leave_voice(self, guild_id):
        if not self.connected:
            return
        try:
            await self.ws.send(json.dumps({
                "op": 4,
                "d": {"guild_id": guild_id, "channel_id": None, "self_mute": False, "self_deaf": False},
            }))
        except Exception:
            pass

    async def disconnect(self):
        self.connected = False
        if self.heartbeat_task:
            self.heartbeat_task.cancel()
        if self.ws:
            try:
                await self.ws.close()
            except Exception:
                pass
            self.ws = None
        self.on_log("Disconnected", "info")


class TokenStore:
    def __init__(self):
        self.data = {"tokens": {}}
        self.load()

    def load(self):
        try:
            if os.path.exists(TOKENS_FILE):
                with open(TOKENS_FILE, "r", encoding="utf-8") as f:
                    self.data = json.load(f)
        except Exception:
            self.data = {"tokens": {}}

    def save(self):
        try:
            with open(TOKENS_FILE, "w", encoding="utf-8") as f:
                json.dump(self.data, f, indent=2, ensure_ascii=False)
        except Exception:
            pass

    def add_token(self, token, info):
        self.data["tokens"][token] = {
            "username": info.get("username", "Unknown"),
            "discriminator": info.get("discriminator", "0"),
            "user_id": info.get("user_id", ""),
            "email": info.get("email"),
            "phone": info.get("phone"),
            "mfa_enabled": info.get("mfa_enabled", False),
            "is_bot": info.get("is_bot", False),
            "premium_type": info.get("premium_type", 0),
            "flags": info.get("flags", []),
            "servers": info.get("servers", []),
        }
        self.save()

    def remove_token(self, token):
        self.data["tokens"].pop(token, None)
        self.save()

    def remove_by_ids(self, ids):
        to_remove = [t for t, i in self.data["tokens"].items() if i.get("user_id") in ids]
        for t in to_remove:
            del self.data["tokens"][t]
        self.save()
        return len(to_remove)

    def remove_invalid(self):
        to_remove = [t for t, i in self.data["tokens"].items() if not i.get("user_id")]
        for t in to_remove:
            del self.data["tokens"][t]
        self.save()
        return len(to_remove)

    def remove_locked(self):
        to_remove = [t for t, i in self.data["tokens"].items() if not i.get("user_id") and i.get("flags")]
        for t in to_remove:
            del self.data["tokens"][t]
        self.save()
        return len(to_remove)

    def rename(self, token, name):
        if token in self.data["tokens"]:
            self.data["tokens"][token]["username"] = name
            self.save()

    def update(self, token, info):
        if token in self.data["tokens"]:
            self.data["tokens"][token].update(info)
            self.save()

    def get_all(self):
        return dict(self.data["tokens"])

    def get(self, token):
        return self.data["tokens"].get(token, {})

    def get_server_map(self):
        server_map = {}
        for token, info in self.data["tokens"].items():
            for server in info.get("servers", []):
                sname = server["name"]
                if sname not in server_map:
                    server_map[sname] = {"id": server["id"], "tokens": []}
                server_map[sname]["tokens"].append({
                    "token": token,
                    "username": info.get("username", "Unknown"),
                })
        return server_map

    def export_json(self, tokens=None):
        tokens = tokens or self.data["tokens"]
        return json.dumps(tokens, indent=2, ensure_ascii=False)
