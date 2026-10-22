import logging
import os
import subprocess
import sys
from pathlib import Path

import pytest

from core.config.settings import settings
from core.utils.jwt import create_jwt_auth, create_optional_jwt_auth
from core.utils.keys import KeyMissingError

SRC = Path(__file__).resolve().parents[2] / "src"
REQUIRED = {
    "MAIL_ADMIN_EMAIL": "admin@example.com",
    "MAIL_ADMIN_USERNAME": "admin",
    "MAIL_ADMIN_PASSWORD": "admin",
    "OAUTH_GOOGLE_CLIENT_ID": "id",
    "OAUTH_GOOGLE_CLIENT_SECRET": "secret",
}


def _start(code: str, **env: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, "-c", code],
        env={**REQUIRED, **os.environ, "PYTHONPATH": str(SRC), **env},
        capture_output=True,
        text=True,
        timeout=120,
        check=False,
    )


def test_a_missing_public_key_is_not_replaced_by_a_shared_secret(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    caplog: pytest.LogCaptureFixture,
) -> None:
    monkeypatch.setattr(settings, "RSA_PUBLIC_KEY_PATH", str(tmp_path / "no.pem"))

    with caplog.at_level(logging.CRITICAL), pytest.raises(KeyMissingError):
        create_jwt_auth()
    with pytest.raises(KeyMissingError):
        create_optional_jwt_auth()

    assert any(r.levelno == logging.CRITICAL for r in caplog.records)


def test_a_service_that_verifies_tokens_does_not_start_without_the_public_key(
    tmp_path: Path,
) -> None:
    result = _start(
        "import core.dependencies.auth",
        RSA_PUBLIC_KEY_PATH=str(tmp_path / "no.pem"),
    )

    assert result.returncode != 0
    assert "The public key of the access tokens is not readable" in result.stderr


def test_user_outside_the_monolith_does_not_make_keys_of_its_own(
    tmp_path: Path,
) -> None:
    result = _start(
        "import user.utils.rsa",
        MONOLITH="false",
        RSA_PRIVATE_KEY_PATH=str(tmp_path / "private.pem"),
        RSA_PUBLIC_KEY_PATH=str(tmp_path / "public.pem"),
    )

    assert result.returncode != 0
    assert "KeyMissingError" in result.stderr
    assert not (tmp_path / "private.pem").exists()


def test_user_outside_the_monolith_needs_the_public_key_of_the_invitations(
    tmp_path: Path,
) -> None:
    result = _start(
        "import user.utils.rsa",
        MONOLITH="false",
        PROFILE_RSA_PUBLIC_KEY_PATH=str(tmp_path / "no.pem"),
    )

    assert result.returncode != 0
    assert "The public key of the invitations is not readable" in result.stderr


def test_a_fresh_monolith_makes_every_key_before_anything_needs_it(
    tmp_path: Path,
) -> None:
    keys = {
        "RSA_PRIVATE_KEY_PATH": tmp_path / "rsa_private.pem",
        "RSA_PUBLIC_KEY_PATH": tmp_path / "rsa_public.pem",
        "PROFILE_RSA_PRIVATE_KEY_PATH": tmp_path / "profile_private.pem",
        "PROFILE_RSA_PUBLIC_KEY_PATH": tmp_path / "profile_public.pem",
    }

    result = _start(
        "import aef.main",
        MONOLITH="true",
        **{name: str(path) for name, path in keys.items()},
    )

    assert result.returncode == 0, result.stderr[-800:]
    assert all(path.exists() for path in keys.values())


def test_profile_outside_the_monolith_does_not_start_without_its_pair(
    tmp_path: Path,
) -> None:
    result = _start(
        "import profile.main",
        MONOLITH="false",
        PROFILE_RSA_PRIVATE_KEY_PATH=str(tmp_path / "private.pem"),
        PROFILE_RSA_PUBLIC_KEY_PATH=str(tmp_path / "public.pem"),
    )

    assert result.returncode != 0
    assert "The invitation keys of profile are not both at" in result.stderr
    assert not (tmp_path / "private.pem").exists()
