from base64 import urlsafe_b64decode as decode
from base64 import urlsafe_b64encode as encode
from uuid import UUID, uuid4


def uuid_to_utf8(uuid: UUID) -> bytes:
    return encode(uuid.bytes).rstrip(b'=')


def utf8_to_uuid(utf8: bytes) -> UUID:
    return UUID(bytes=decode(utf8.decode()+"=="))


if __name__ == "__main__":
    for i in range(2048**2):
        uuid = uuid4()
        encoded = uuid_to_utf8(uuid)
        decoded = utf8_to_uuid(encoded)
        if uuid != decoded:
            raise ValueError(f"UUID encoding/decoding failed for {uuid}")
