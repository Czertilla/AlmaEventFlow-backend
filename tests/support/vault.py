import base64
import os
import secrets
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from pathlib import Path
from re import fullmatch
from typing import Any

from aiohttp import web
from aiohttp.test_utils import TestServer
from cryptography.exceptions import InvalidTag
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.kdf.hkdf import HKDF

KEY = "profile-kek"


class FakeVault:
    """Vault Transit as far as `VaultTransitProvider` uses it: AppRole login, a
    `derived=true` key with versions, `encrypt` and `decrypt`."""

    def __init__(self, folder: Path, ttl: int = 3600) -> None:
        self.role_id = secrets.token_hex(8)
        self.secret_id = secrets.token_hex(16)
        self.role_id_file = folder / "role_id"
        self.secret_id_file = folder / "secret_id"
        self.role_id_file.write_text(self.role_id, encoding="utf-8")
        self.secret_id_file.write_text(self.secret_id, encoding="utf-8")
        self.ttl = ttl
        self.versions: list[bytes] = [os.urandom(32)]
        self.tokens: set[str] = set()
        self.logins = 0
        self.calls: list[str] = []
        self.down = False
        self.url = ""

    def rotate(self) -> int:
        self.versions.append(os.urandom(32))
        return len(self.versions)

    def revoke_tokens(self) -> None:
        self.tokens.clear()

    def _key(self, version: int, context: bytes) -> AESGCM:
        derived = HKDF(
            algorithm=hashes.SHA256(), length=32, salt=None, info=context
        ).derive(self.versions[version - 1])
        return AESGCM(derived)

    def app(self) -> web.Application:
        app = web.Application()
        app.router.add_post("/v1/auth/approle/login", self._login)
        app.router.add_post(f"/v1/transit/encrypt/{KEY}", self._encrypt)
        app.router.add_post(f"/v1/transit/decrypt/{KEY}", self._decrypt)
        return app

    async def _body(self, request: web.Request) -> dict[str, Any]:
        if self.down:
            raise web.HTTPServiceUnavailable()
        body: dict[str, Any] = await request.json()
        return body

    def _authorized(self, request: web.Request) -> None:
        if request.headers.get("X-Vault-Token") not in self.tokens:
            raise web.HTTPForbidden(text='{"errors": ["permission denied"]}')

    async def _login(self, request: web.Request) -> web.Response:
        body = await self._body(request)
        given = (body.get("role_id"), body.get("secret_id"))
        if given != (self.role_id, self.secret_id):
            return web.json_response({"errors": ["invalid secret ID"]}, status=400)
        token = secrets.token_hex(12)
        self.tokens.add(token)
        self.logins += 1
        return web.json_response(
            {"auth": {"client_token": token, "lease_duration": self.ttl}}
        )

    async def _encrypt(self, request: web.Request) -> web.Response:
        body = await self._body(request)
        self._authorized(request)
        self.calls.append("encrypt")
        if "context" not in body:
            return web.json_response({"errors": ["missing context"]}, status=400)
        version = len(self.versions)
        nonce = os.urandom(12)
        sealed = self._key(version, base64.b64decode(body["context"])).encrypt(
            nonce, base64.b64decode(body["plaintext"]), None
        )
        ciphertext = f"vault:v{version}:" + base64.b64encode(nonce + sealed).decode()
        return web.json_response({"data": {"ciphertext": ciphertext}})

    async def _decrypt(self, request: web.Request) -> web.Response:
        body = await self._body(request)
        self._authorized(request)
        self.calls.append("decrypt")
        match = fullmatch(r"vault:v([0-9]+):(.+)", str(body.get("ciphertext", "")))
        if match is None or not 1 <= int(match[1]) <= len(self.versions):
            return web.json_response({"errors": ["invalid ciphertext"]}, status=400)
        try:
            raw = base64.b64decode(match[2], validate=True)
            plaintext = self._key(
                int(match[1]), base64.b64decode(body.get("context", ""))
            ).decrypt(raw[:12], raw[12:], None)
        except (InvalidTag, ValueError):
            return web.json_response(
                {"errors": ["cipher: message authentication failed"]}, status=400
            )
        return web.json_response(
            {"data": {"plaintext": base64.b64encode(plaintext).decode()}}
        )


@asynccontextmanager
async def fake_vault(folder: Path, ttl: int = 3600) -> AsyncGenerator[FakeVault]:
    vault = FakeVault(folder, ttl)
    server = TestServer(vault.app())
    await server.start_server()
    vault.url = str(server.make_url("")).rstrip("/")
    try:
        yield vault
    finally:
        await server.close()
