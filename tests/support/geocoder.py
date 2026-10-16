import asyncio
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from geo.bootstrap.run import address_id
from geo.dto.address import AddressDTO
from geo.dto.location import LocationDTO
from geo.dto.point import PointDTO
from geo.dto.search import SearchHitDTO
from geo.geocoder.base import GeocodedAddress
from geo.models.address import AddressORM
from geo.service.geography import resolve_or_create_city
from geo.uow.address import AddressUOW

Maker = async_sessionmaker[AsyncSession]
Published = list[tuple[str, list[Any]]]


def address_of(hit: SearchHitDTO) -> AddressDTO:
    assert hit.address is not None
    return hit.address


def location_of(hit: SearchHitDTO) -> LocationDTO:
    assert hit.location is not None
    return hit.location


def place_of(hit: SearchHitDTO) -> AddressDTO | LocationDTO:
    return address_of(hit) if hit.kind == "address" else location_of(hit)


def moscow_house(
    street: str = "Тверская улица",
    housenumber: str = "7",
    *,
    source_id: str = "node/1",
    city: str = "Москва",
    region: str = "Москва",
    country: str = "Россия",
    lat: float = 55.7583,
    lon: float = 37.6116,
    source: str = "photon",
) -> GeocodedAddress:
    return GeocodedAddress(
        source_id, street, housenumber, lat, lon, city, region, country, source
    )


def unplaced_house(
    street: str = "Тверская улица",
    housenumber: str = "7",
    *,
    source_id: str = "node/1",
    lat: float = 55.7583,
    lon: float = 37.6116,
) -> GeocodedAddress:
    """An OpenStreetMap element: it names no city."""
    return moscow_house(
        street,
        housenumber,
        source_id=source_id,
        city="",
        region="",
        country="",
        lat=lat,
        lon=lon,
        source="osm",
    )


class StubGeocoder:
    def __init__(
        self,
        found: list[GeocodedAddress] | None = None,
        *,
        error: Exception | None = None,
        delay: float = 0.0,
        name: str = "stub",
    ):
        self.name = name
        self.found = [moscow_house()] if found is None else found
        self.error = error
        self.delay = delay
        self.calls: list[tuple[str, PointDTO | None, int]] = []

    async def search(
        self, query: str, *, near: PointDTO | None, limit: int
    ) -> list[GeocodedAddress]:
        self.calls.append((query, near, limit))
        if self.delay:
            await asyncio.sleep(self.delay)
        if self.error:
            raise self.error
        return list(self.found)


class Clock:
    def __init__(self) -> None:
        self.now = 1000.0

    def __call__(self) -> float:
        return self.now


class DatedStubGeocoder(StubGeocoder):
    def __init__(self, *args: Any, built: datetime | None = None, **kwargs: Any):
        super().__init__(*args, **kwargs)
        self.built = built

    async def imported_at(self) -> datetime | None:
        return self.built


async def count_rows(sessionmaker_: Maker, model: type[Any]) -> int:
    async with sessionmaker_() as session:
        return (
            await session.execute(select(func.count()).select_from(model))
        ).scalar_one()


async def row_of(sessionmaker_: Maker, row_id: Any) -> AddressORM:
    async with sessionmaker_() as session:
        return (
            await session.execute(select(AddressORM).where(AddressORM.id == row_id))
        ).scalar_one()


async def store_address(
    sessionmaker_: Maker,
    city: tuple[str, str, str],
    street: str,
    house: str,
    point: tuple[float, float],
    *,
    source: str | None = "osm",
    synced_at: datetime | None = None,
) -> AddressORM:
    """An address filed under ``city`` (country, region, name) like an import would."""
    async with AddressUOW(sessionmaker_) as uow:
        city_id = await resolve_or_create_city(uow, *city)
    row_id = address_id(city_id, street.casefold(), house.casefold())
    async with AddressUOW(sessionmaker_) as uow:
        await uow.addresses.upsert_many(
            [
                {
                    "id": row_id,
                    "city_id": city_id,
                    "name": f"{street}, {house}",
                    "spot": {"lat": point[0], "lon": point[1]},
                    "parsed": {"street": street, "house": house},
                    "source": source,
                    "source_id": "node/9",
                    "synced_at": synced_at or datetime.now(UTC),
                }
            ]
        )
        await uow.commit()
    return await row_of(sessionmaker_, row_id)
