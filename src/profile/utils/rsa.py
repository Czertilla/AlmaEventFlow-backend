from logging import getLogger
from pathlib import Path

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa

from core.config.settings import settings
from core.utils.keys import KeyMissingError

logger = getLogger(__name__)


def ensure_invite_keys() -> None:
    private_path = Path(settings.PROFILE_RSA_PRIVATE_KEY_PATH)
    public_path = Path(settings.PROFILE_RSA_PUBLIC_KEY_PATH)
    present = (private_path.exists(), public_path.exists())
    if all(present):
        return
    if settings.MONOLITH and not any(present):
        _generate(private_path, public_path)
        return
    message = (
        "The invitation keys of profile are not both at "
        f"{private_path} and {public_path}"
    )
    logger.critical(message)
    raise KeyMissingError(message)


def _generate(private_path: Path, public_path: Path) -> None:
    private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    private_path.write_bytes(
        private_key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption(),
        )
    )
    private_path.chmod(0o600)
    public_path.write_bytes(
        private_key.public_key().public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo,
        )
    )

