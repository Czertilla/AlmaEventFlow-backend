import os
import sys
from pathlib import Path
from profile.crypto import (
    KeyConfigError,
    KeyProviderError,
    KeyRing,
    KeyUnwrapError,
    WrappedKey,
    build_keyring,
)
from profile.crypto.keygen import main as keygen
from profile.crypto.local import LocalKeyProvider
from profile.crypto.vault import AppRoleAuth, VaultTransitProvider

import pytest
from cryptography.exceptions import InvalidTag
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from support.vault import fake_vault

from core.config.settings import Settings

CONTEXT = b"person_key|subject|1"
POSIX_ONLY = pytest.mark.skipif(
    sys.platform == "win32", reason="Windows keeps file rights in ACLs"
)


def _settings(**values: object) -> Settings:
    return Settings.model_validate(values)


def test_keygen_writes_a_32_byte_key_and_refuses_to_overwrite(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    assert keygen([str(tmp_path), "--version", "2"]) == 0
    assert keygen([str(tmp_path), "--version", "2"]) == 1

    assert len((tmp_path / "kek.v2").read_bytes()) == 32
    assert "already exists" in capsys.readouterr().err


@POSIX_ONLY
def test_keygen_makes_the_file_readable_by_its_owner_only(tmp_path: Path) -> None:
    keygen([str(tmp_path)])

    assert (tmp_path / "kek.v1").stat().st_mode & 0o777 == 0o400


@POSIX_ONLY
@pytest.mark.parametrize("mode", [0o440, 0o404, 0o604])
def test_a_key_file_open_to_others_stops_the_start(tmp_path: Path, mode: int) -> None:
    keygen([str(tmp_path)])
    (tmp_path / "kek.v1").chmod(mode)

    with pytest.raises(KeyConfigError, match="chmod 0400"):
        LocalKeyProvider(tmp_path, 1)


def test_a_missing_directory_or_version_stops_the_start(tmp_path: Path) -> None:
    keygen([str(tmp_path)])

    with pytest.raises(KeyConfigError, match="not a directory"):
        LocalKeyProvider(tmp_path / "nowhere", 1)
    with pytest.raises(KeyConfigError, match=r"kek\.v2"):
        LocalKeyProvider(tmp_path, 2)


def test_a_key_file_of_the_wrong_size_stops_the_start(tmp_path: Path) -> None:
    (tmp_path / "kek.v1").write_bytes(os.urandom(16))

    with pytest.raises(KeyConfigError, match="32 random bytes"):
        LocalKeyProvider(tmp_path, 1)


async def test_a_key_sealed_with_a_passphrase_opens_with_it_only(
    tmp_path: Path,
) -> None:
    keys = tmp_path / "keys"
    passphrase = tmp_path / "passphrase"
    wrong = tmp_path / "wrong"
    passphrase.write_bytes(b"correct horse battery staple\n")
    wrong.write_bytes(b"incorrect")
    for path in (passphrase, wrong):
        path.chmod(0o400)
    keygen([str(keys), "--passphrase-file", str(passphrase)])

    provider = LocalKeyProvider(keys, 1, passphrase)
    wrapped = await provider.wrap(b"k" * 32, CONTEXT)

    assert await LocalKeyProvider(keys, 1, passphrase).unwrap(wrapped, CONTEXT) == (
        b"k" * 32
    )
    with pytest.raises(KeyConfigError, match="passphrase does not open"):
        LocalKeyProvider(keys, 1, wrong)
    with pytest.raises(KeyConfigError, match="32 random bytes"):
        LocalKeyProvider(keys, 1)


async def test_the_key_file_is_not_used_as_the_wrapping_key_itself(
    tmp_path: Path,
) -> None:
    keygen([str(tmp_path)])
    raw = (tmp_path / "kek.v1").read_bytes()
    wrapped = await LocalKeyProvider(tmp_path, 1).wrap(b"k" * 32, CONTEXT)

    with pytest.raises(InvalidTag):
        AESGCM(raw).decrypt(wrapped.payload[:12], wrapped.payload[12:], CONTEXT)


async def test_a_version_that_is_gone_does_not_unwrap(tmp_path: Path) -> None:
    keygen([str(tmp_path), "--version", "1"])
    keygen([str(tmp_path), "--version", "2"])
    old = await LocalKeyProvider(tmp_path, 1).wrap(b"k" * 32, CONTEXT)
    (tmp_path / "kek.v1").chmod(0o600)
    (tmp_path / "kek.v1").unlink()

    with pytest.raises(KeyUnwrapError):
        await LocalKeyProvider(tmp_path, 2).unwrap(old, CONTEXT)


@pytest.mark.parametrize(
    ("values", "message"),
    [
        ({}, "KEY_PROVIDER is required"),
        ({"KEY_PROVIDER": "aws"}, "not implemented"),
        ({"KEY_PROVIDER": "hsm"}, "unknown key provider"),
        ({"KEY_PROVIDER": "local", "LOCAL_KEK_DIR": None}, "LOCAL_KEK_DIR is required"),
        ({"KEY_PROVIDER": "vault"}, "VAULT_ADDR is required"),
        (
            {"KEY_PROVIDER": "vault", "VAULT_ADDR": "http://vault:8200"},
            "VAULT_APPROLE_ROLE_ID_FILE is required",
        ),
        (
            {
                "KEY_PROVIDER": "vault",
                "VAULT_ADDR": "http://vault:8200",
                "VAULT_AUTH_METHOD": "token",
            },
            "approle or kubernetes",
        ),
    ],
)
def test_a_wrong_configuration_stops_the_start(
    values: dict[str, object], message: str
) -> None:
    with pytest.raises(KeyConfigError, match=message):
        build_keyring(_settings(**{"KEY_PROVIDER": None, **values}))


async def test_a_ring_wraps_with_the_active_provider_and_unwraps_with_the_others(
    tmp_path: Path,
) -> None:
    keygen([str(tmp_path / "keys")])
    async with fake_vault(tmp_path) as vault:
        config = _settings(
            KEY_PROVIDER="local",
            KEY_PROVIDERS_READ=["vault"],
            LOCAL_KEK_DIR=str(tmp_path / "keys"),
            VAULT_ADDR=vault.url,
            VAULT_APPROLE_ROLE_ID_FILE=str(vault.role_id_file),
            VAULT_APPROLE_SECRET_ID_FILE=str(vault.secret_id_file),
        )
        ring = build_keyring(config)
        by_vault = await ring.provider("vault").wrap(b"v" * 32, CONTEXT)
        await ring.self_test()

        fresh = await ring.wrap(b"n" * 32, CONTEXT)
        stored = WrappedKey.from_bytes(by_vault.to_bytes())
        restored = await ring.unwrap(stored, CONTEXT)
        await ring.close()

    assert fresh.provider_id == "local"
    assert restored == b"v" * 32
    with pytest.raises(KeyUnwrapError):
        await ring.unwrap(WrappedKey("aws", by_vault.key_ref, b"x"), CONTEXT)


async def test_the_self_test_fails_when_a_provider_does_not_answer(
    tmp_path: Path,
) -> None:
    async with fake_vault(tmp_path) as vault:
        provider = VaultTransitProvider(
            vault.url,
            auth=AppRoleAuth("approle", vault.role_id_file, vault.secret_id_file),
        )
        vault.down = True

        with pytest.raises(KeyProviderError):
            await KeyRing(provider).self_test()
        await provider.close()


def test_a_provider_configured_twice_is_refused(tmp_path: Path) -> None:
    keygen([str(tmp_path)])
    provider = LocalKeyProvider(tmp_path, 1)

    with pytest.raises(KeyConfigError, match="twice"):
        KeyRing(provider, [LocalKeyProvider(tmp_path, 1)])
