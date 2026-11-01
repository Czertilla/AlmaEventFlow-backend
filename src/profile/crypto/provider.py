from dataclasses import dataclass
from enum import StrEnum
from typing import Protocol

from .errors import KeyUnwrapError

WRAPPED_FORMAT = 1


@dataclass(frozen=True, slots=True)
class KeyRef:
    name: str
    version: int


@dataclass(frozen=True, slots=True)
class WrappedKey:
    provider_id: str
    key_ref: KeyRef
    payload: bytes

    @property
    def ref(self) -> str:
        return f"{self.provider_id}:{self.key_ref.name}:{self.key_ref.version}"

    def to_bytes(self) -> bytes:
        provider = self.provider_id.encode("ascii")
        name = self.key_ref.name.encode("utf-8")
        if len(provider) > 255 or len(name) > 255:
            raise ValueError("provider id and key name are at most 255 bytes")
        return b"".join(
            (
                bytes((WRAPPED_FORMAT, len(provider))),
                provider,
                bytes((len(name),)),
                name,
                self.key_ref.version.to_bytes(4, "big"),
                self.payload,
            )
        )

    @classmethod
    def from_bytes(cls, raw: bytes) -> "WrappedKey":
        try:
            if raw[0] != WRAPPED_FORMAT:
                raise KeyUnwrapError("unknown wrapped key format")
            at = 2 + raw[1]
            provider = raw[2:at].decode("ascii")
            name_end = at + 1 + raw[at]
            name = raw[at + 1 : name_end].decode("utf-8")
            version = int.from_bytes(raw[name_end : name_end + 4], "big")
            payload = raw[name_end + 4 :]
        except (IndexError, UnicodeDecodeError):
            raise KeyUnwrapError("malformed wrapped key") from None
        if not provider or not name or len(raw) < name_end + 4 or not payload:
            raise KeyUnwrapError("malformed wrapped key")
        return cls(provider, KeyRef(name, version), payload)


class Health(StrEnum):
    OK = "ok"
    UNAVAILABLE = "unavailable"


class KeyProvider(Protocol):
    """Keeps the key-encryption keys and wraps data keys with them; nothing else
    in the service knows where the master keys live."""

    @property
    def provider_id(self) -> str: ...

    async def wrap(self, plaintext_key: bytes, context: bytes) -> WrappedKey: ...

    async def unwrap(self, wrapped: WrappedKey, context: bytes) -> bytes: ...

    async def current_key_ref(self) -> KeyRef: ...

    async def health(self) -> Health: ...

    async def close(self) -> None: ...
