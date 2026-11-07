import os
from collections.abc import AsyncIterator, Awaitable, Callable
from dataclasses import dataclass
from pathlib import Path
from profile.crypto import (
    Health,
    KeyProvider,
    KeyProviderUnavailableError,
    KeyRef,
    KeyUnwrapError,
    WrappedKey,
)
from profile.crypto.local import LocalKeyProvider
from profile.crypto.vault import AppRoleAuth, VaultTransitProvider

import pytest
from support.vault import fake_vault

CONTEXT = b"person_key|subject|1"


@dataclass
class Subject:
    provider: KeyProvider
    rotate: Callable[[], Awaitable[KeyProvider]]


def _kek(folder: Path, version: int) -> None:
    path = folder / f"kek.v{version}"
    path.write_bytes(os.urandom(32))
    path.chmod(0o400)


@pytest.fixture(params=["local", "vault"])
async def subject(
    request: pytest.FixtureRequest, tmp_path: Path
) -> AsyncIterator[Subject]:
    if request.param == "local":
        _kek(tmp_path, 1)

        async def rotate_local() -> KeyProvider:
            _kek(tmp_path, 2)
            return LocalKeyProvider(tmp_path, 2)

        yield Subject(LocalKeyProvider(tmp_path, 1), rotate_local)
        return
    async with fake_vault(tmp_path) as vault:
        provider = VaultTransitProvider(
            vault.url,
            auth=AppRoleAuth("approle", vault.role_id_file, vault.secret_id_file),
        )

        async def rotate_vault() -> KeyProvider:
            vault.rotate()
            return provider

        yield Subject(provider, rotate_vault)
        await provider.close()


async def test_a_wrapped_key_comes_back_through_its_stored_form(
    subject: Subject,
) -> None:
    key = os.urandom(32)

    wrapped = await subject.provider.wrap(key, CONTEXT)
    stored = WrappedKey.from_bytes(wrapped.to_bytes())

    assert stored == wrapped
    assert stored.provider_id == subject.provider.provider_id
    assert key not in wrapped.to_bytes()
    assert await subject.provider.unwrap(stored, CONTEXT) == key


async def test_another_context_does_not_unwrap(subject: Subject) -> None:
    wrapped = await subject.provider.wrap(os.urandom(32), CONTEXT)

    with pytest.raises(KeyUnwrapError):
        await subject.provider.unwrap(wrapped, b"person_key|other|1")


async def test_a_changed_payload_does_not_unwrap(subject: Subject) -> None:
    wrapped = await subject.provider.wrap(os.urandom(32), CONTEXT)
    payload = bytearray(wrapped.payload)
    payload[-3] ^= 0x01

    with pytest.raises(KeyUnwrapError):
        await subject.provider.unwrap(
            WrappedKey(wrapped.provider_id, wrapped.key_ref, bytes(payload)), CONTEXT
        )


async def test_a_key_of_another_provider_is_refused(subject: Subject) -> None:
    wrapped = await subject.provider.wrap(os.urandom(32), CONTEXT)

    with pytest.raises(KeyUnwrapError):
        await subject.provider.unwrap(
            WrappedKey("elsewhere", wrapped.key_ref, wrapped.payload), CONTEXT
        )


async def test_a_new_version_wraps_and_the_old_one_still_unwraps(
    subject: Subject,
) -> None:
    key = os.urandom(32)
    old = await subject.provider.wrap(key, CONTEXT)

    rotated = await subject.rotate()
    new = await rotated.wrap(key, CONTEXT)

    assert new.key_ref.name == old.key_ref.name
    assert new.key_ref.version > old.key_ref.version
    assert await rotated.current_key_ref() == new.key_ref
    assert await rotated.unwrap(old, CONTEXT) == key
    assert await rotated.unwrap(new, CONTEXT) == key


async def test_a_working_provider_is_healthy(subject: Subject) -> None:
    assert await subject.provider.health() == Health.OK


def test_a_malformed_stored_key_is_refused() -> None:
    good = WrappedKey("local", KeyRef("kek", 3), b"payload").to_bytes()

    for broken in (b"", b"\x02" + good[1:], good[:5], good[: len(good) - 7]):
        with pytest.raises(KeyUnwrapError):
            WrappedKey.from_bytes(broken)


async def test_vault_logs_in_again_when_its_token_expires(tmp_path: Path) -> None:
    now = [0.0]
    async with fake_vault(tmp_path, ttl=600) as vault:
        provider = VaultTransitProvider(
            vault.url,
            auth=AppRoleAuth("approle", vault.role_id_file, vault.secret_id_file),
            clock=lambda: now[0],
        )
        await provider.wrap(os.urandom(32), CONTEXT)
        now[0] = 500.0
        await provider.wrap(os.urandom(32), CONTEXT)
        now[0] = 541.0
        await provider.wrap(os.urandom(32), CONTEXT)
        await provider.close()

    assert vault.logins == 2


async def test_vault_logs_in_again_when_it_refuses_the_token(tmp_path: Path) -> None:
    async with fake_vault(tmp_path) as vault:
        provider = VaultTransitProvider(
            vault.url,
            auth=AppRoleAuth("approle", vault.role_id_file, vault.secret_id_file),
        )
        wrapped = await provider.wrap(b"k" * 32, CONTEXT)
        vault.revoke_tokens()

        assert await provider.unwrap(wrapped, CONTEXT) == b"k" * 32
        await provider.close()

    assert vault.logins == 2


async def test_a_silent_vault_is_unavailable_not_empty(tmp_path: Path) -> None:
    async with fake_vault(tmp_path) as vault:
        provider = VaultTransitProvider(
            vault.url,
            auth=AppRoleAuth("approle", vault.role_id_file, vault.secret_id_file),
        )
        wrapped = await provider.wrap(os.urandom(32), CONTEXT)
        vault.down = True

        with pytest.raises(KeyProviderUnavailableError):
            await provider.unwrap(wrapped, CONTEXT)
        assert await provider.health() == Health.UNAVAILABLE
        await provider.close()


async def test_an_unreachable_vault_is_unavailable(tmp_path: Path) -> None:
    (tmp_path / "role").write_text("r", encoding="utf-8")
    (tmp_path / "secret").write_text("s", encoding="utf-8")
    provider = VaultTransitProvider(
        "http://127.0.0.1:9",
        auth=AppRoleAuth("approle", tmp_path / "role", tmp_path / "secret"),
        timeout_seconds=0.5,
    )

    with pytest.raises(KeyProviderUnavailableError):
        await provider.wrap(os.urandom(32), CONTEXT)
    await provider.close()


async def test_a_wrong_secret_is_a_refused_login(tmp_path: Path) -> None:
    async with fake_vault(tmp_path) as vault:
        vault.secret_id_file.write_text("wrong", encoding="utf-8")
        provider = VaultTransitProvider(
            vault.url,
            auth=AppRoleAuth("approle", vault.role_id_file, vault.secret_id_file),
        )

        with pytest.raises(KeyProviderUnavailableError):
            await provider.wrap(os.urandom(32), CONTEXT)
        await provider.close()


@pytest.mark.skipif(
    not os.environ.get("VAULT_TEST_ADDR"),
    reason="set VAULT_TEST_ADDR, VAULT_TEST_ROLE_ID_FILE, VAULT_TEST_SECRET_ID_FILE",
)
async def test_a_real_vault_wraps_unwraps_and_checks_the_context() -> None:
    provider = VaultTransitProvider(
        os.environ["VAULT_TEST_ADDR"],
        auth=AppRoleAuth(
            os.environ.get("VAULT_TEST_APPROLE_MOUNT", "approle"),
            Path(os.environ["VAULT_TEST_ROLE_ID_FILE"]),
            Path(os.environ["VAULT_TEST_SECRET_ID_FILE"]),
        ),
        key=os.environ.get("VAULT_TEST_KEY", "profile-kek"),
    )
    key = os.urandom(32)
    try:
        wrapped = WrappedKey.from_bytes((await provider.wrap(key, CONTEXT)).to_bytes())
        assert await provider.unwrap(wrapped, CONTEXT) == key
        with pytest.raises(KeyUnwrapError):
            await provider.unwrap(wrapped, b"person_key|other|1")
        assert await provider.health() == Health.OK
    finally:
        await provider.close()
