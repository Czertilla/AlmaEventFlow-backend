import os
from datetime import date, datetime
from profile.crypto import DecryptionError, DekCache, cipher
from typing import Any
from uuid import uuid4

import pytest

DEK = os.urandom(32)
PERSON = uuid4()
ROW = uuid4()
HOME: dict[str, Any] = {
    "table": "passport",
    "column": "number",
    "person_id": PERSON,
    "row_id": ROW,
}


def _sealed(value: bytes = b"4510 123456") -> bytes:
    return cipher.seal(DEK, 1, value, **HOME)


@pytest.mark.parametrize(
    ("value", "kind"),
    [
        ("4510 123456", "text"),
        ("Ёлкин", "text"),
        (date(2031, 2, 3), "date"),
        (True, "bool"),
        (False, "bool"),
    ],
)
def test_every_kind_comes_back_as_it_went_in(value: Any, kind: Any) -> None:
    raw = cipher.encode(value, kind)
    blob = cipher.seal(DEK, 1, raw, **HOME)

    assert cipher.decode(cipher.open_sealed(DEK, blob, **HOME), kind) == value
    assert len(raw) < 4 or raw not in blob


def test_the_stored_form_starts_with_the_format_and_the_key_version() -> None:
    blob = cipher.seal(DEK, 7, b"x", **HOME)

    assert blob[0] == cipher.FORMAT_VERSION
    assert cipher.dek_version_of(blob) == 7
    assert len(blob) == cipher.HEADER_SIZE + 1 + 16


def test_the_same_value_is_never_stored_twice_the_same_way() -> None:
    assert _sealed() != _sealed()


@pytest.mark.parametrize(
    "elsewhere",
    [
        {"table": "student"},
        {"column": "issued_authority"},
        {"person_id": uuid4()},
        {"row_id": uuid4()},
    ],
)
def test_a_value_moved_to_another_place_does_not_open(
    elsewhere: dict[str, Any],
) -> None:
    with pytest.raises(DecryptionError):
        cipher.open_sealed(DEK, _sealed(), **{**HOME, **elsewhere})


@pytest.mark.parametrize("position", [0, 1, 5, -1])
def test_a_changed_byte_does_not_open(position: int) -> None:
    blob = bytearray(_sealed())
    blob[position] ^= 0x01

    with pytest.raises(DecryptionError):
        cipher.open_sealed(DEK, bytes(blob), **HOME)


def test_another_data_key_does_not_open() -> None:
    with pytest.raises(DecryptionError):
        cipher.open_sealed(os.urandom(32), _sealed(), **HOME)


@pytest.mark.parametrize(
    ("value", "kind"),
    [
        (datetime(2030, 1, 1), "date"),
        ("2030-01-01", "date"),
        (1, "bool"),
        (b"x", "text"),
    ],
)
def test_a_value_of_the_wrong_type_is_not_encoded(value: Any, kind: Any) -> None:
    with pytest.raises(TypeError):
        cipher.encode(value, kind)


def test_garbage_that_decrypted_is_not_a_value() -> None:
    with pytest.raises(DecryptionError):
        cipher.decode(b"yes", "bool")
    with pytest.raises(DecryptionError):
        cipher.decode(b"\xff", "text")


def test_the_cache_keeps_at_most_its_size_and_wipes_what_leaves() -> None:
    cache = DekCache(max_size=2, ttl_seconds=60)
    first, second, third = (uuid4(), 1), (uuid4(), 1), (uuid4(), 1)
    for key in (first, second, third):
        cache.put(key, bytearray(b"k" * 32))
    stored = cache._items[second][1]

    cache.drop(second[0])

    assert len(cache) == 1
    assert cache.get(first) is None
    assert stored == bytearray(32)


def test_the_cache_forgets_a_key_after_its_time() -> None:
    now = [0.0]
    cache = DekCache(max_size=8, ttl_seconds=60, clock=lambda: now[0])
    key = (uuid4(), 1)
    cache.put(key, bytearray(b"k" * 32))

    now[0] = 59.0
    assert cache.get(key) == bytearray(b"k" * 32)
    now[0] = 60.0
    assert cache.get(key) is None


def test_a_key_taken_from_the_cache_is_a_copy() -> None:
    cache = DekCache(max_size=1, ttl_seconds=60)
    key = (uuid4(), 1)
    cache.put(key, bytearray(b"k" * 32))
    taken = cache.get(key)

    cache.put((uuid4(), 1), bytearray(b"n" * 32))

    assert taken == bytearray(b"k" * 32)


@pytest.mark.parametrize(("size", "ttl"), [(0, 60), (8, 0)])
def test_a_cache_of_no_size_or_no_time_keeps_nothing(size: int, ttl: int) -> None:
    cache = DekCache(max_size=size, ttl_seconds=ttl)
    cache.put((uuid4(), 1), bytearray(b"k" * 32))

    assert len(cache) == 0
