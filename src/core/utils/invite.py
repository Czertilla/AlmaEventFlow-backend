from datetime import UTC, datetime, timedelta
from pathlib import Path
from uuid import UUID

import jwt

from core.config.settings import settings

INVITE_AUDIENCE = "invite"
INVITE_ISSUER = "profile"
INVITE_ALGORITHM = "RS256"


class InviteSigningUnavailableError(Exception):
    """The private key of `profile` is not on this host."""


def _read(path: str) -> str | None:
    try:
        return Path(path).read_text()
    except OSError:
        return None


def encode_invite_token(person_id: UUID, lifetime: int) -> tuple[str, int]:
    private_key = _read(settings.PROFILE_RSA_PRIVATE_KEY_PATH)
    if private_key is None:
        raise InviteSigningUnavailableError()
    expires_at = datetime.now(UTC) + timedelta(seconds=lifetime)
    token = jwt.encode(
        {
            "person_id": str(person_id),
            "aud": [INVITE_AUDIENCE],
            "iss": INVITE_ISSUER,
            "exp": expires_at,
        },
        private_key,
        algorithm=INVITE_ALGORITHM,
    )
    return token, int(expires_at.timestamp())


def decode_invite_token(token: str) -> UUID:
    """Raises `jwt.ExpiredSignatureError` or `jwt.InvalidTokenError`."""
    public_key = _read(settings.PROFILE_RSA_PUBLIC_KEY_PATH)
    if public_key is None:
        raise jwt.InvalidTokenError("The public key of the invitations is missing")
    data = jwt.decode(
        token,
        public_key,
        audience=[INVITE_AUDIENCE],
        issuer=INVITE_ISSUER,
        algorithms=[INVITE_ALGORITHM],
    )
    try:
        return UUID(data["person_id"])
    except (KeyError, TypeError, ValueError):
        raise jwt.InvalidTokenError("The invitation names no person") from None
