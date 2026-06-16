import hashlib
import secrets


class CalendarTokenService:
    """Generates and hashes calendar feed tokens.

    The raw token is never stored — only its SHA-256 hash is kept in the
    database, so the plaintext token is shown to the user only once, at
    creation / rotation time.
    """

    _NBYTES = 32

    @staticmethod
    def generate() -> str:
        return secrets.token_urlsafe(CalendarTokenService._NBYTES)

    @staticmethod
    def hash(token: str) -> str:
        return hashlib.sha256(token.encode("utf-8")).hexdigest()
