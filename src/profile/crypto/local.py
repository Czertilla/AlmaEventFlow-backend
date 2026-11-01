import os
import sys
from logging import getLogger
from pathlib import Path
from re import fullmatch

from cryptography.exceptions import InvalidTag
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.kdf.argon2 import Argon2id
from cryptography.hazmat.primitives.kdf.hkdf import HKDF

from .errors import KeyConfigError, KeyUnwrapError
from .provider import Health, KeyRef, WrappedKey

logger = getLogger(__name__)

KEK_SIZE = 32
NONCE_SIZE = 12
SALT_SIZE = 16
KEY_NAME = "kek"
FILE_PATTERN = r"kek\.v([1-9][0-9]{0,8})"
WRAP_INFO = b"aef-profile/dek-wrap"
SEALED_MAGIC = b"AEFKEK1"
ARGON_MEMORY_KIB = 65536
ARGON_ITERATIONS = 3
ARGON_LANES = 4


def check_secret_file(path: Path) -> None:
    """Refuses a key file that the group or others may read, or that belongs to
    another user. Windows keeps rights in ACLs, not in mode bits: not checked."""
    if sys.platform == "win32":
        return
    info = path.stat()
    if info.st_mode & 0o077:
        raise KeyConfigError(f"{path} is open to its group or to others: chmod 0400")
    uid = os.geteuid()
    if uid != 0 and info.st_uid != uid:
        raise KeyConfigError(f"{path} must belong to the user of the service")


def _argon(salt: bytes, memory: int, iterations: int, lanes: int) -> Argon2id:
    return Argon2id(
        salt=salt,
        length=KEK_SIZE,
        iterations=iterations,
        lanes=lanes,
        memory_cost=memory,
    )


def seal_kek(kek: bytes, passphrase: bytes) -> bytes:
    salt = os.urandom(SALT_SIZE)
    header = b"".join(
        (
            SEALED_MAGIC,
            salt,
            ARGON_MEMORY_KIB.to_bytes(4, "big"),
            ARGON_ITERATIONS.to_bytes(4, "big"),
            ARGON_LANES.to_bytes(4, "big"),
        )
    )
    key = _argon(salt, ARGON_MEMORY_KIB, ARGON_ITERATIONS, ARGON_LANES).derive(
        passphrase
    )
    nonce = os.urandom(NONCE_SIZE)
    return header + nonce + AESGCM(key).encrypt(nonce, kek, header)


def open_kek(raw: bytes, passphrase: bytes) -> bytes:
    if not raw.startswith(SEALED_MAGIC):
        raise KeyConfigError("the key file is not protected by a passphrase")
    at = len(SEALED_MAGIC)
    salt = raw[at : at + SALT_SIZE]
    at += SALT_SIZE
    memory, iterations, lanes = (
        int.from_bytes(raw[at + 4 * i : at + 4 * i + 4], "big") for i in range(3)
    )
    header_end = at + 12
    header = raw[:header_end]
    nonce = raw[header_end : header_end + NONCE_SIZE]
    body = raw[header_end + NONCE_SIZE :]
    key = _argon(salt, memory, iterations, lanes).derive(passphrase)
    try:
        return AESGCM(key).decrypt(nonce, body, header)
    except InvalidTag:
        raise KeyConfigError("the passphrase does not open the key file") from None


def read_passphrase(path: str | Path) -> bytes:
    file = Path(path)
    if not file.is_file():
        raise KeyConfigError(f"no passphrase file {file}")
    check_secret_file(file)
    passphrase = file.read_bytes().rstrip(b"\r\n")
    if not passphrase:
        raise KeyConfigError(f"the passphrase file {file} is empty")
    return passphrase


def _load_kek(path: Path, passphrase: bytes | None) -> bytes:
    raw = path.read_bytes()
    kek = open_kek(raw, passphrase) if passphrase is not None else raw
    if len(kek) != KEK_SIZE:
        raise KeyConfigError(f"{path} must hold exactly {KEK_SIZE} random bytes")
    return kek


def _wrap_key(kek: bytes) -> AESGCM:
    derived = HKDF(
        algorithm=hashes.SHA256(), length=KEK_SIZE, salt=None, info=WRAP_INFO
    ).derive(kek)
    return AESGCM(derived)


class LocalKeyProvider:
    """Key-encryption keys in files `kek.v<N>` of one directory, outside the data,
    the image and the repository. Only keys derived from them for one purpose
    (HKDF, `info`) stay in memory. Keeps the key apart from the data: protects
    dumps and backups, not a compromised host or process."""

    provider_id = "local"

    def __init__(
        self,
        directory: str | Path,
        active: int,
        passphrase_file: str | Path | None = None,
    ) -> None:
        folder = Path(directory)
        if not folder.is_dir():
            raise KeyConfigError(f"LOCAL_KEK_DIR {folder} is not a directory")
        passphrase = read_passphrase(passphrase_file) if passphrase_file else None
        keys: dict[int, AESGCM] = {}
        for path in sorted(folder.iterdir()):
            match = fullmatch(FILE_PATTERN, path.name)
            if match is None or not path.is_file():
                continue
            check_secret_file(path)
            keys[int(match[1])] = _wrap_key(_load_kek(path, passphrase))
        if active not in keys:
            raise KeyConfigError(f"no key file kek.v{active} in {folder}")
        if sys.platform == "win32":
            logger.warning("The rights of the key files are not checked on Windows")
        self._active = active
        self._keys = keys

    @property
    def versions(self) -> tuple[int, ...]:
        return tuple(sorted(self._keys))

    async def wrap(self, plaintext_key: bytes, context: bytes) -> WrappedKey:
        nonce = os.urandom(NONCE_SIZE)
        sealed = self._keys[self._active].encrypt(nonce, plaintext_key, context)
        return WrappedKey(
            self.provider_id, KeyRef(KEY_NAME, self._active), nonce + sealed
        )

    async def unwrap(self, wrapped: WrappedKey, context: bytes) -> bytes:
        if (
            wrapped.provider_id != self.provider_id
            or wrapped.key_ref.name != KEY_NAME
        ):
            raise KeyUnwrapError("the key was not wrapped by this provider")
        key = self._keys.get(wrapped.key_ref.version)
        if key is None:
            raise KeyUnwrapError("the key version is not configured")
        nonce, body = wrapped.payload[:NONCE_SIZE], wrapped.payload[NONCE_SIZE:]
        try:
            return key.decrypt(nonce, body, context)
        except (InvalidTag, ValueError):
            raise KeyUnwrapError("unwrap failed") from None

    async def current_key_ref(self) -> KeyRef:
        return KeyRef(KEY_NAME, self._active)

    async def health(self) -> Health:
        return Health.OK

    async def close(self) -> None:
        return None
