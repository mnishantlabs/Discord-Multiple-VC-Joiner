"""Typed data models.

The on-disk JSON schema for tokens is stable and shared with older versions
of the application; ``Token.to_dict`` / ``Token.from_dict`` round-trip that
exact schema so no data migration is needed.
"""

from dataclasses import dataclass, field
from typing import Any


@dataclass(slots=True)
class ServerInfo:
    id: str
    name: str

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ServerInfo":
        return cls(id=str(data.get("id", "")), name=str(data.get("name", "")))

    def to_dict(self) -> dict[str, str]:
        return {"id": self.id, "name": self.name}


@dataclass(slots=True)
class ChannelInfo:
    id: str
    name: str
    type: int = 0

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ChannelInfo":
        return cls(id=str(data.get("id", "")), name=str(data.get("name", "")),
                   type=int(data.get("type", 0) or 0))

    def to_dict(self) -> dict[str, object]:
        return {"id": self.id, "name": self.name, "type": self.type}


@dataclass(slots=True)
class VoiceTarget:
    guild_id: str
    guild_name: str
    channel_id: str
    channel_name: str

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "VoiceTarget":
        return cls(
            guild_id=str(data.get("guild_id", "")),
            guild_name=str(data.get("guild_name", "")),
            channel_id=str(data.get("channel_id", "")),
            channel_name=str(data.get("channel_name", "")),
        )

    def to_dict(self) -> dict[str, str]:
        return {
            "guild_id": self.guild_id,
            "guild_name": self.guild_name,
            "channel_id": self.channel_id,
            "channel_name": self.channel_name,
        }


@dataclass(slots=True)
class Token:
    """A stored Discord token with the metadata the app tracks."""

    token: str
    username: str = "Unknown"
    discriminator: str = "0"
    user_id: str = ""
    email: str | None = None
    phone: str | None = None
    mfa_enabled: bool = False
    is_bot: bool = False
    is_verified: bool = False
    premium_type: int = 0
    flags: list[str] = field(default_factory=list)
    servers: list[ServerInfo] = field(default_factory=list)
    error: str = ""
    code: str = ""

    @classmethod
    def from_dict(cls, token: str, data: dict[str, Any]) -> "Token":
        servers = [ServerInfo.from_dict(s) for s in data.get("servers", [])]
        return cls(
            token=token,
            username=str(data.get("username", "Unknown")),
            discriminator=str(data.get("discriminator", "0")),
            user_id=str(data.get("user_id", "")),
            email=data.get("email"),
            phone=data.get("phone"),
            mfa_enabled=bool(data.get("mfa_enabled", False)),
            is_bot=bool(data.get("is_bot", False)),
            is_verified=bool(data.get("verified", False) or data.get("is_verified", False)),
            premium_type=int(data.get("premium_type", 0) or 0),
            flags=list(data.get("flags", []) or []),
            servers=servers,
            error=str(data.get("error", "")),
            code=str(data.get("code", "")),
        )

    def to_dict(self) -> dict[str, Any]:
        """Serialize to the stable on-disk schema."""
        return {
            "username": self.username,
            "discriminator": self.discriminator,
            "user_id": self.user_id,
            "email": self.email,
            "phone": self.phone,
            "mfa_enabled": self.mfa_enabled,
            "is_bot": self.is_bot,
            "premium_type": self.premium_type,
            "flags": self.flags,
            "servers": [s.to_dict() for s in self.servers],
        }

    def info_dict(self) -> dict[str, Any]:
        """Runtime info dict (same shape views historically indexed)."""
        data = self.to_dict()
        if self.error:
            data["error"] = self.error
        if self.code:
            data["code"] = self.code
        return data