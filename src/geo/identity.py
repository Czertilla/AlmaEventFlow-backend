# ruff: noqa: RUF001
import re
from math import asin, cos, radians, sin, sqrt

from geo.dto.address import AddressFieldsDTO

AddressKey = tuple[str, str]

DUPLICATE_RADIUS_M = 150.0
"""Two rows with one address key closer than this are one real address."""

_STREET_TYPES = {
    "ул": "улица",
    "пр": "проспект",
    "пр-т": "проспект",
    "просп": "проспект",
    "пер": "переулок",
    "наб": "набережная",
    "пл": "площадь",
    "б-р": "бульвар",
    "бул": "бульвар",
    "ш": "шоссе",
    "пр-д": "проезд",
    "туп": "тупик",
}
STREET_TYPE_WORDS = frozenset(_STREET_TYPES) | frozenset(_STREET_TYPES.values())
_WORD = re.compile(r"[^\W_]+(?:-[^\W_]+)*")
_ORDINAL = re.compile(r"^\d+-(?:я|й|е|ая|ой|ий|го|ое)$")
_HOUSE_PREFIX = re.compile(r"^(?:дом|д)(?=\d)")
_UNIT_MARKERS = {"к", "корп", "корпус", "с", "стр", "строение"}
_UNITS = (
    ("корпус", "к"),
    ("корп", "к"),
    ("строение", "с"),
    ("стр", "с"),
    ("литера", "л"),
    ("лит", "л"),
)
_LATIN = str.maketrans("abcekmhopxty", "авсекмнорхту")


def _plain(text: str) -> str:
    return text.casefold().replace("ё", "е")


def place_words(text: str) -> list[str]:
    """Words of a settlement name: case, ё and hyphens do not matter."""
    found: list[str] = re.findall(r"[^\W_]+", _plain(text))
    return found


def starts_like(typed: list[str], name: list[str]) -> bool:
    """The typed words are the first whole words of the name.

    A word still being typed is not one: the name it may become is unknown.
    """
    return bool(typed) and name[: len(typed)] == typed


def street_key(street: str) -> str:
    found: list[str] = _WORD.findall(_plain(street))
    return " ".join(sorted(_STREET_TYPES.get(word, word) for word in found))


def house_key(house: str) -> str:
    text = _plain(house).translate(_LATIN)
    text = re.sub(r"[\s.,]+", "", text)
    text = _HOUSE_PREFIX.sub("", text)
    for long, short in _UNITS:
        text = text.replace(long, short)
    return text


def address_key(street: str, housenumber: str) -> AddressKey:
    return street_key(street), house_key(housenumber)


def stored_key(name: str, parsed: AddressFieldsDTO | None) -> AddressKey:
    """A manual row has no ``parsed`` street, only a name like "street, house"."""
    if parsed is not None and parsed.street and parsed.house:
        return address_key(parsed.street, parsed.house)
    head, comma, tail = name.rpartition(",")
    return address_key(head, tail) if comma else address_key(name, "")


def split_query(text: str) -> tuple[list[str], str | None]:
    """A typed "street house city" as (the words before the house number, its key)."""
    tokens = _plain(text).replace(",", " ").split()
    for index, token in enumerate(tokens):
        if not any(char.isdigit() for char in token) or _ORDINAL.match(token):
            continue
        parts = [token]
        rest = tokens[index + 1 :]
        while len(rest) >= 2 and rest[0].rstrip(".") in _UNIT_MARKERS:
            if not any(char.isdigit() for char in rest[1]):
                break
            parts += rest[:2]
            rest = rest[2:]
        return tokens[:index], house_key("".join(parts))
    return tokens, None


def query_house(text: str) -> str | None:
    return split_query(text)[1]


def street_words(words: list[str]) -> list[str]:
    """Words of a street name without its type ("улица", "пр-т", ...)."""
    kinds = STREET_TYPE_WORDS | {"д", "дом"}
    found: list[str] = _WORD.findall(" ".join(words))
    return [word for word in found if word not in kinds]


Box = tuple[float, float, float, float]


def box_around(lat: float, lon: float, radius_m: float) -> Box:
    """(min_lat, min_lon, max_lat, max_lon) of the square holding the circle."""
    d_lat = radius_m / 111_320.0
    d_lon = d_lat / max(cos(radians(lat)), 0.01)
    return lat - d_lat, lon - d_lon, lat + d_lat, lon + d_lon


def meters_between(lat_a: float, lon_a: float, lat_b: float, lon_b: float) -> float:
    d_lat = radians(lat_b - lat_a)
    d_lon = radians(lon_b - lon_a)
    half = (
        sin(d_lat / 2) ** 2
        + cos(radians(lat_a)) * cos(radians(lat_b)) * sin(d_lon / 2) ** 2
    )
    return 2 * 6_371_000.0 * asin(sqrt(half))
