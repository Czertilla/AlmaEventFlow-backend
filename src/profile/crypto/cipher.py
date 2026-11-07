import os
from datetime import date, datetime
from profile.enum.value_kind import ValueKind as Kind
from uuid import UUID

from cryptography.exceptions import InvalidTag
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

from .errors import DecryptionError

FORMAT_VERSION = 1
NONCE_SIZE = 12
HEADER_SIZE = 2 + NONCE_SIZE
DEK_SIZE = 32
MAX_DEK_VERSION = 255

Plain = str | date | bool


def aad(
    table: str,
    column: str,
    person_id: UUID,
    row_id: UUID,
    format_version: int,
    dek_version: int,
) -> bytes:
    return (
        f"{table}|{column}|{person_id}|{row_id}|{format_version}|{dek_version}"
    ).encode()


def encode(value: Plain, kind: Kind) -> bytes:
    match kind:
        case "text" if isinstance(value, str):
            return value.encode("utf-8")
        case "date" if isinstance(value, date) and not isinstance(value, datetime):
            return value.isoformat().encode("ascii")
        case "bool" if isinstance(value, bool):
            return b"1" if value else b"0"
        case _:
            raise TypeError(f"a {type(value).__name__} is not a {kind} value")


def decode(raw: bytes, kind: Kind) -> Plain:
    try:
        match kind:
            case "text":
                return raw.decode("utf-8")
            case "date":
                return date.fromisoformat(raw.decode("ascii"))
            case "bool":
                if raw not in (b"0", b"1"):
                    raise ValueError
                return raw == b"1"
    except (UnicodeDecodeError, ValueError):
        raise DecryptionError("bad_plaintext") from None


def dek_version_of(blob: bytes) -> int:
    if len(blob) <= HEADER_SIZE or blob[0] != FORMAT_VERSION:
        raise DecryptionError("bad_format")
    return blob[1]


def seal(
    dek: bytes | bytearray,
    dek_version: int,
    plaintext: bytes,
    table: str,
    column: str,
    person_id: UUID,
    row_id: UUID,
) -> bytes:
    """`[format 1B][dek_version 1B][nonce 12B][ciphertext + tag]`; the AAD binds the
    value to its table, column, person, row and both versions of the header."""
    nonce = os.urandom(NONCE_SIZE)
    header = bytes((FORMAT_VERSION, dek_version))
    body = AESGCM(bytes(dek)).encrypt(
        nonce,
        plaintext,
        aad(table, column, person_id, row_id, FORMAT_VERSION, dek_version),
    )
    return header + nonce + body


def open_sealed(
    dek: bytes | bytearray,
    blob: bytes,
    table: str,
    column: str,
    person_id: UUID,
    row_id: UUID,
) -> bytes:
    dek_version_of(blob)
    nonce = blob[2:HEADER_SIZE]
    try:
        return AESGCM(bytes(dek)).decrypt(
            nonce,
            blob[HEADER_SIZE:],
            aad(table, column, person_id, row_id, blob[0], blob[1]),
        )
    except (InvalidTag, ValueError):
        raise DecryptionError("bad_tag") from None
