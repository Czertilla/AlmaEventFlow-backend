import asyncio
import base64
import os
import ssl
import time
from collections.abc import Callable
from dataclasses import dataclass
from logging import getLogger
from pathlib import Path
from re import fullmatch
from typing import Any, Protocol, cast

import aiohttp

from .errors import (
    KeyConfigError,
    KeyProviderError,
    KeyProviderUnavailableError,
    KeyUnwrapError,
)
from .provider import Health, KeyRef, WrappedKey

logger = getLogger(__name__)

PROBE_CONTEXT = b"aef-profile/probe"


def _read_secret(path: Path) -> str:
    try:
        value = path.read_text(encoding="utf-8").strip()
    except OSError:
        raise KeyProviderUnavailableError(f"cannot read {path}") from None
    if not value:
        raise KeyProviderUnavailableError(f"{path} is empty")
    return value


class VaultAuth(Protocol):
    @property
    def mount(self) -> str: ...

    def login_body(self) -> dict[str, str]: ...


@dataclass(frozen=True, slots=True)
class AppRoleAuth:
    mount: str
    role_id_file: Path
    secret_id_file: Path

    def login_body(self) -> dict[str, str]:
        return {
            "role_id": _read_secret(self.role_id_file),
            "secret_id": _read_secret(self.secret_id_file),
        }


@dataclass(frozen=True, slots=True)
class KubernetesAuth:
    mount: str
    role: str
    token_file: Path

    def login_body(self) -> dict[str, str]:
        return {"role": self.role, "jwt": _read_secret(self.token_file)}


def _b64(value: bytes) -> str:
    return base64.b64encode(value).decode("ascii")


@dataclass(slots=True)
class _Client:
    loop: asyncio.AbstractEventLoop
    session: aiohttp.ClientSession
    lock: asyncio.Lock


class VaultTransitProvider:
    """Vault Transit: the key `profile-kek` (`derived=true`) encrypts and decrypts
    data keys, never the data. Logs in with AppRole or Kubernetes auth, keeps the
    short-lived token and logs in again before it expires or when Vault refuses it.
    The policy needs only `encrypt` and `decrypt` on the key."""

    provider_id = "vault"

    def __init__(
        self,
        address: str,
        *,
        auth: VaultAuth,
        mount: str = "transit",
        key: str = "profile-kek",
        timeout_seconds: float = 2.0,
        namespace: str | None = None,
        ca_file: str | None = None,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        if not address.startswith(("http://", "https://")):
            raise KeyConfigError("VAULT_ADDR must be an http(s) address")
        self._address = address.rstrip("/")
        self._auth = auth
        self._mount = mount.strip("/")
        self._key = key
        self._timeout = timeout_seconds
        self._namespace = namespace
        self._ssl: ssl.SSLContext | bool = (
            ssl.create_default_context(cafile=ca_file) if ca_file else True
        )
        self._clock = clock
        self._client: _Client | None = None
        self._token: str | None = None
        self._expires = 0.0

    def _connection(self) -> _Client:
        loop = asyncio.get_running_loop()
        client = self._client
        if client is None or client.loop is not loop or client.session.closed:
            client = _Client(
                loop,
                aiohttp.ClientSession(
                    timeout=aiohttp.ClientTimeout(total=self._timeout)
                ),
                asyncio.Lock(),
            )
            self._client = client
            self._token = None
        return client

    async def _post(
        self, path: str, body: dict[str, str], token: str | None
    ) -> tuple[int, dict[str, Any]]:
        client = self._connection()
        headers: dict[str, str] = {}
        if self._namespace:
            headers["X-Vault-Namespace"] = self._namespace
        if token is not None:
            headers["X-Vault-Token"] = token
        try:
            async with client.session.post(
                f"{self._address}/v1/{path}", json=body, headers=headers, ssl=self._ssl
            ) as response:
                status = response.status
                data: Any = await response.json(content_type=None)
        except (aiohttp.ClientError, TimeoutError, ValueError) as exc:
            logger.warning("Vault did not answer: %s", type(exc).__name__)
            raise KeyProviderUnavailableError("vault did not answer") from None
        return status, cast("dict[str, Any]", data) if isinstance(data, dict) else {}

    async def _login(self) -> str:
        status, data = await self._post(
            f"auth/{self._auth.mount}/login", self._auth.login_body(), None
        )
        try:
            if status != 200:
                raise KeyError
            auth: dict[str, Any] = data["auth"]
            token = str(auth["client_token"])
            ttl = float(auth.get("lease_duration") or 0)
        except (KeyError, TypeError, ValueError):
            logger.warning("Vault refused the login: %s", status)
            raise KeyProviderUnavailableError("vault refused the login") from None
        margin = min(max(ttl * 0.1, 30.0), ttl / 2)
        self._token = token
        self._expires = self._clock() + ttl - margin if ttl else float("inf")
        return token

    async def _current_token(self) -> str:
        client = self._connection()
        async with client.lock:
            if self._token is None or self._clock() >= self._expires:
                return await self._login()
            return self._token

    async def _call(
        self, path: str, body: dict[str, str]
    ) -> tuple[int, dict[str, Any]]:
        status, data = await self._post(path, body, await self._current_token())
        if status == 403:
            self._token = None
            status, data = await self._post(path, body, await self._current_token())
        return status, data

    async def wrap(self, plaintext_key: bytes, context: bytes) -> WrappedKey:
        status, data = await self._call(
            f"{self._mount}/encrypt/{self._key}",
            {"plaintext": _b64(plaintext_key), "context": _b64(context)},
        )
        try:
            if status != 200:
                raise KeyError
            ciphertext = str(data["data"]["ciphertext"])
            match = fullmatch(r"vault:v([0-9]+):.+", ciphertext)
            if match is None:
                raise KeyError
        except (KeyError, TypeError):
            logger.warning("Vault refused to encrypt: %s", status)
            raise KeyProviderUnavailableError("vault refused to encrypt") from None
        return WrappedKey(
            self.provider_id,
            KeyRef(self._key, int(match[1])),
            ciphertext.encode("ascii"),
        )

    async def unwrap(self, wrapped: WrappedKey, context: bytes) -> bytes:
        if wrapped.provider_id != self.provider_id or wrapped.key_ref.name != self._key:
            raise KeyUnwrapError("the key was not wrapped by this provider")
        try:
            ciphertext = wrapped.payload.decode("ascii")
        except UnicodeDecodeError:
            raise KeyUnwrapError("malformed wrapped key") from None
        status, data = await self._call(
            f"{self._mount}/decrypt/{self._key}",
            {"ciphertext": ciphertext, "context": _b64(context)},
        )
        if status == 400:
            raise KeyUnwrapError("vault could not decrypt")
        try:
            if status != 200:
                raise KeyError
            return base64.b64decode(str(data["data"]["plaintext"]), validate=True)
        except (KeyError, TypeError, ValueError):
            logger.warning("Vault refused to decrypt: %s", status)
            raise KeyProviderUnavailableError("vault refused to decrypt") from None

    async def current_key_ref(self) -> KeyRef:
        return (await self.wrap(os.urandom(32), PROBE_CONTEXT)).key_ref

    async def health(self) -> Health:
        try:
            await self.current_key_ref()
        except KeyProviderError:
            return Health.UNAVAILABLE
        return Health.OK

    async def close(self) -> None:
        client, self._client = self._client, None
        if client is not None and not client.session.closed:
            try:
                running = asyncio.get_running_loop()
            except RuntimeError:
                return
            if client.loop is running:
                await client.session.close()
