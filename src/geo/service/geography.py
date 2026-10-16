"""Shared find-or-create logic for the Country -> Region -> City hierarchy --
used by the bootstrap job, the on-demand live-fetch (both resolving names
from OSM), and manual "cascade" address creation (resolving names a person
typed) alike, so all three agree on one row per real place instead of
drifting apart with duplicates."""

from sqlalchemy import select

from geo.models.city import CityORM
from geo.models.country import CountryORM
from geo.models.region import RegionORM
from geo.uow.address import AddressUOW


async def resolve_or_create_city(
    uow: AddressUOW,
    country_name: str,
    region_name: str,
    city_name: str,
    *,
    country_code: str | None = None,
) -> int:
    """Finds an existing Country/Region/City row by name, creating whichever
    levels are missing. Returns the resolved city_id. Names are stripped
    before lookup/creation so incidental whitespace doesn't spawn a
    duplicate row next to an otherwise-identical existing one."""
    session = uow.session
    country_name = country_name.strip()
    region_name = region_name.strip()
    city_name = city_name.strip()

    country = (
        await session.execute(select(CountryORM).where(CountryORM.name == country_name))
    ).scalar_one_or_none()
    if country is None:
        country = CountryORM(name=country_name, code=country_code)
        session.add(country)
        await session.flush()

    region = (
        await session.execute(
            select(RegionORM).where(
                RegionORM.country_id == country.id,
                RegionORM.name == region_name,
            )
        )
    ).scalar_one_or_none()
    if region is None:
        region = RegionORM(country_id=country.id, name=region_name)
        session.add(region)
        await session.flush()

    city = (
        await session.execute(
            select(CityORM).where(
                CityORM.region_id == region.id,
                CityORM.name == city_name,
            )
        )
    ).scalar_one_or_none()
    if city is None:
        city = CityORM(region_id=region.id, name=city_name)
        session.add(city)
        await session.flush()

    await session.commit()
    return city.id


_REGION_NOISE = frozenset({"республика", "область", "край", "автономный", "округ"})


def _region_key(name: str) -> str:
    words = name.casefold().replace("ё", "е").split()  # noqa: RUF001
    return " ".join(word for word in words if word not in _REGION_NOISE)


async def resolve_city_loose(
    uow: AddressUOW, country_name: str, region_name: str, city_name: str
) -> int:
    """``resolve_or_create_city`` that tolerates another spelling of the region."""
    stmt = (
        select(CityORM.id, RegionORM.name)
        .join(RegionORM, RegionORM.id == CityORM.region_id)
        .join(CountryORM, CountryORM.id == RegionORM.country_id)
        .where(
            CityORM.name == city_name.strip(),
            CountryORM.name == country_name.strip(),
        )
    )
    wanted = _region_key(region_name)
    for city_id, existing_region in (await uow.addresses.execute(stmt)).all():
        if _region_key(existing_region) == wanted:
            return city_id
    return await resolve_or_create_city(uow, country_name, region_name, city_name)
