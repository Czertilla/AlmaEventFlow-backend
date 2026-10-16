import re

from geo.bootstrap.sources import OverpassError, OverpassSource
from geo.dto.point import PointDTO
from geo.geocoder.base import GeocodedAddress, GeocoderError
from geo.identity import (
    box_around,
    house_key,
    meters_between,
    split_query,
    street_key,
    street_words,
)

_LEADING_DIGITS = re.compile(r"\d+")
_STEM_FROM = 5
_STEM_CUT = 2


class OverpassGeocoder:
    """Street and house number near a point, straight from OpenStreetMap.

    The element knows no city: the hit is placed by the addresses around it.
    """

    name = "overpass"

    def __init__(self, source: OverpassSource, *, radius_m: float = 2000.0):
        self.source = source
        self.radius_m = radius_m

    async def search(
        self, query: str, *, near: PointDTO | None, limit: int
    ) -> list[GeocodedAddress]:
        if near is None:
            return []
        before, wanted = split_query(query)
        words = [_stem(word) for word in street_words(before)]
        if not words:
            return []
        digits = _LEADING_DIGITS.match(wanted) if wanted else None
        try:
            found = await self.source.search(
                box_around(near.lat, near.lon, self.radius_m),
                words,
                digits.group() if digits else None,
                limit * 3,
            )
        except (OverpassError, ValueError) as exc:
            raise GeocoderError(str(exc) or type(exc).__name__) from exc
        hits = [
            raw
            for raw in found
            if wanted is None or house_key(raw.housenumber) == wanted
        ]
        names = street_words(before)
        hits.sort(
            key=lambda raw: (
                not set(names) <= set(street_key(raw.street).split()),
                meters_between(near.lat, near.lon, raw.lat, raw.lon),
            )
        )
        return [
            GeocodedAddress(
                source_id=raw.source_id,
                street=raw.street,
                housenumber=raw.housenumber,
                lat=raw.lat,
                lon=raw.lon,
                city="",
                region="",
                country="",
                source=raw.source,
            )
            for raw in hits[:limit]
        ]

def _stem(word: str) -> str:
    return word[:-_STEM_CUT] if len(word) >= _STEM_FROM else word
