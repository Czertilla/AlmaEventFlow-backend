from datetime import UTC, datetime, timedelta
from pathlib import Path
from uuid import uuid4

import jwt
import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa

from core.config.settings import settings
from core.utils.invite import (
    InviteSigningUnavailableError,
    decode_invite_token,
    encode_invite_token,
)


def _claims(**override: object) -> dict[str, object]:
    return {
        "person_id": str(uuid4()),
        "aud": ["invite"],
        "iss": "profile",
        "exp": datetime.now(UTC) + timedelta(hours=1),
        **override,
    }


def _own_private_key() -> str:
    return Path(settings.PROFILE_RSA_PRIVATE_KEY_PATH).read_text()


def _foreign_private_key() -> str:
    return (
        rsa.generate_private_key(public_exponent=65537, key_size=2048)
        .private_bytes(
            serialization.Encoding.PEM,
            serialization.PrivateFormat.PKCS8,
            serialization.NoEncryption(),
        )
        .decode()
    )


def test_a_token_reads_back_as_the_person_it_names() -> None:
    person_id = uuid4()

    token, expires_at = encode_invite_token(person_id, 3600)

    assert decode_invite_token(token) == person_id
    assert expires_at > datetime.now(UTC).timestamp()


def test_a_token_of_the_old_shared_secret_is_refused() -> None:
    token = jwt.encode(_claims(), "SECRET", algorithm="HS256")

    with pytest.raises(jwt.InvalidTokenError):
        decode_invite_token(token)


def test_a_token_signed_with_another_key_is_refused() -> None:
    token = jwt.encode(_claims(), _foreign_private_key(), algorithm="RS256")

    with pytest.raises(jwt.InvalidTokenError):
        decode_invite_token(token)


def test_a_token_of_another_issuer_or_audience_is_refused() -> None:
    other_issuer = jwt.encode(
        _claims(iss="user"), _own_private_key(), algorithm="RS256"
    )
    other_audience = jwt.encode(
        _claims(aud=["fastapi-users:auth"]), _own_private_key(), algorithm="RS256"
    )

    for token in (other_issuer, other_audience):
        with pytest.raises(jwt.InvalidTokenError):
            decode_invite_token(token)


def test_an_expired_token_is_told_apart() -> None:
    token, _ = encode_invite_token(uuid4(), -60)

    with pytest.raises(jwt.ExpiredSignatureError):
        decode_invite_token(token)


def test_a_token_without_a_person_is_refused() -> None:
    claims = _claims()
    del claims["person_id"]
    token = jwt.encode(claims, _own_private_key(), algorithm="RS256")

    with pytest.raises(jwt.InvalidTokenError):
        decode_invite_token(token)


def test_a_host_without_the_public_key_accepts_nothing(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    token, _ = encode_invite_token(uuid4(), 3600)
    monkeypatch.setattr(
        settings, "PROFILE_RSA_PUBLIC_KEY_PATH", str(tmp_path / "no.pem")
    )

    with pytest.raises(jwt.InvalidTokenError):
        decode_invite_token(token)


def test_a_host_without_the_private_key_cannot_sign(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setattr(
        settings, "PROFILE_RSA_PRIVATE_KEY_PATH", str(tmp_path / "no.pem")
    )

    with pytest.raises(InviteSigningUnavailableError):
        encode_invite_token(uuid4(), 3600)
