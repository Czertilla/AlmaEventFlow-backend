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
