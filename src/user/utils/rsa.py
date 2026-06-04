from pathlib import Path
from functools import lru_cache
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.backends import default_backend

from core.config.settings import settings


@lru_cache
def _get_private_key_path() -> Path:
    return Path(settings.RSA_PRIVATE_KEY_PATH)


@lru_cache
def _get_public_key_path() -> Path:
    return Path(settings.RSA_PUBLIC_KEY_PATH)


def _ensure_keys_exist() -> None:
    private_path = _get_private_key_path()
    public_path = _get_public_key_path()
    if private_path.exists() and public_path.exists():
        return
    private_key = rsa.generate_private_key(
        public_exponent=65537, key_size=2048, backend=default_backend()
    )
    public_key = private_key.public_key()
    private_path.write_text(
        private_key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption(),
        ).decode()
    )
    public_path.write_text(
        public_key.public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo,
        ).decode()
    )


_ensure_keys_exist()


@lru_cache(maxsize=1)
def get_private_key_pem() -> str:
    return _get_private_key_path().read_text()


@lru_cache(maxsize=1)
def get_public_key_pem() -> str:
    return _get_public_key_path().read_text()
