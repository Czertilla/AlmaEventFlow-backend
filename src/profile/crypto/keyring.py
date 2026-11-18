import hmac
import logging
import os
from collections.abc import Iterable
from pathlib import Path
from typing import NoReturn

from core.config.settings import Settings, settings

from .errors import KeyConfigError, KeyProviderError, KeyUnwrapError
from .local import LocalKeyProvider
from .provider import Health, KeyProvider, WrappedKey
from .vault import AppRoleAuth, KubernetesAuth, VaultAuth, VaultTransitProvider

NOT_IMPLEMENTED = ("aws", "gcp", "yc", "azure")
SELF_TEST_CONTEXT = b"aef-profile/self-test"

logger = logging.getLogger(__name__)


def _config_error(message: str) -> NoReturn:
    logger.critical("Profile key configuration error: %s", message)
    raise KeyConfigError(message)


class KeyRing:
    """The active provider wraps every new data key; the others, configured while
    keys move between providers, only unwrap what they wrapped."""

    def __init__(
        self, active: KeyProvider, readers: Iterable[KeyProvider] = ()
    ) -> None:
        self.active = active
        self._providers: dict[str, KeyProvider] = {}
        for provider in (active, *readers):
            if provider.provider_id in self._providers:
                _config_error(
                    f"provider {provider.provider_id} is configured twice"
                )
            self._providers[provider.provider_id] = provider

    @property
    def providers(self) -> tuple[KeyProvider, ...]:
        return tuple(self._providers.values())

    def provider(self, provider_id: str) -> KeyProvider:
        provider = self._providers.get(provider_id)
        if provider is None:
            logger.critical(
                "Profile key provider %r is not configured", provider_id
            )
            raise KeyUnwrapError("the provider of the key is not configured")
        return provider

    async def wrap(self, plaintext_key: bytes, context: bytes) -> WrappedKey:
        return await self.active.wrap(plaintext_key, context)

    async def unwrap(self, wrapped: WrappedKey, context: bytes) -> bytes:
        return await self.provider(wrapped.provider_id).unwrap(wrapped, context)

    async def self_test(self) -> None:
        probe = os.urandom(32)
        for provider in self._providers.values():
            wrapped = WrappedKey.from_bytes(
                (await provider.wrap(probe, SELF_TEST_CONTEXT)).to_bytes()
            )
            if not hmac.compare_digest(
                await provider.unwrap(wrapped, SELF_TEST_CONTEXT), probe
            ):
                raise KeyProviderError(f"{provider.provider_id} round trip failed")

    async def health(self) -> Health:
        for provider in self._providers.values():
            if await provider.health() != Health.OK:
                return Health.UNAVAILABLE
        return Health.OK

    async def close(self) -> None:
        for provider in self._providers.values():
            await provider.close()


def _path(value: str | None, name: str) -> Path:
    if not value:
        _config_error(f"{name} is required")
    path = Path(value)
    if not path.is_file():
        _config_error(f"{name}: no file {path}")
    return path


def _vault_auth(config: Settings) -> VaultAuth:
    method = config.VAULT_AUTH_METHOD
    mount = config.VAULT_AUTH_MOUNT or method
    match method:
        case "approle":
            return AppRoleAuth(
                mount,
                _path(config.VAULT_APPROLE_ROLE_ID_FILE, "VAULT_APPROLE_ROLE_ID_FILE"),
                _path(
                    config.VAULT_APPROLE_SECRET_ID_FILE, "VAULT_APPROLE_SECRET_ID_FILE"
                ),
            )
        case "kubernetes":
            if not config.VAULT_K8S_ROLE:
                _config_error("VAULT_K8S_ROLE is required")
            return KubernetesAuth(
                mount,
                config.VAULT_K8S_ROLE,
                _path(config.VAULT_K8S_TOKEN_FILE, "VAULT_K8S_TOKEN_FILE"),
            )
        case _:
            _config_error("VAULT_AUTH_METHOD must be approle or kubernetes")


def build_provider(name: str, config: Settings = settings) -> KeyProvider:
    match name:
        case "local":
            if not config.LOCAL_KEK_DIR:
                _config_error("LOCAL_KEK_DIR is required for KEY_PROVIDER=local")
            return LocalKeyProvider(
                config.LOCAL_KEK_DIR,
                config.LOCAL_KEK_ACTIVE,
                config.LOCAL_KEK_PASSPHRASE_FILE,
            )
        case "vault":
            if not config.VAULT_ADDR:
                _config_error("VAULT_ADDR is required for KEY_PROVIDER=vault")
            return VaultTransitProvider(
                config.VAULT_ADDR,
                auth=_vault_auth(config),
                mount=config.VAULT_TRANSIT_MOUNT,
                key=config.VAULT_TRANSIT_KEY,
                timeout_seconds=config.VAULT_TIMEOUT_SECONDS,
                namespace=config.VAULT_NAMESPACE,
                ca_file=config.VAULT_CA_FILE,
            )
        case _ if name in NOT_IMPLEMENTED:
            _config_error(
                f"KEY_PROVIDER={name} is not implemented yet: use local or vault"
            )
        case _:
            _config_error(f"unknown key provider {name!r}: use local or vault")


def build_keyring(config: Settings = settings) -> KeyRing:
    if not config.KEY_PROVIDER:
        _config_error("KEY_PROVIDER is required: local or vault")
    readers = [
        name for name in config.KEY_PROVIDERS_READ if name != config.KEY_PROVIDER
    ]
    return KeyRing(
        build_provider(config.KEY_PROVIDER, config),
        [build_provider(name, config) for name in dict.fromkeys(readers)],
    )


_installed: KeyRing | None = None


def install_keyring(ring: KeyRing | None) -> None:
    global _installed
    _installed = ring


def keyring() -> KeyRing:
    global _installed
    if _installed is None:
        _installed = build_keyring()
    return _installed
