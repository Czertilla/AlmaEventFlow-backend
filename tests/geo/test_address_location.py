import asyncio
from uuid import uuid4

import pytest
from sqlalchemy import select

from core.dto.pagination import PageParamDTO
from geo.dto.address import (
    AddressCascadeCreateDTO,
    AddressCreateDTO,
    AddressFieldsDTO,
    AddressPatchDTO,
)
from geo.dto.city import CityCascadeCreateDTO
from geo.dto.location import LocationCreateDTO, LocationFilterDTO
from geo.dto.point import PointDTO
from geo.exc.address import AddressNotExistsException
from geo.models.city import CityORM
from geo.service.address import AddressService
from geo.service.location import LocationService
from geo.uow.address import AddressUOW
from geo.uow.location import LocationUOW


async def _address(sessionmaker_, city_id, name="Арбат, 10"):
    return await AddressService(AddressUOW(sessionmaker_)).create(
        AddressCreateDTO(city_id=city_id, name=name)
    )


async def test_address_name_is_composed_from_parsed_fields(
    sessionmaker_, city_id, published
):
    created = await AddressService(AddressUOW(sessionmaker_)).create(
        AddressCreateDTO(
            city_id=city_id,
            parsed=AddressFieldsDTO(
                street="Тверская улица", house="7", building="стр. 1"
            ),
        )
    )

    assert created.name == "Тверская улица, 7, стр. 1"


async def test_create_cascade_creates_the_city_hierarchy_when_missing(
    sessionmaker_, published
):
    service = AddressService(AddressUOW(sessionmaker_))
    created = await service.create_cascade(
        AddressCascadeCreateDTO(
            street="Невский проспект",
            house="1",
            city=CityCascadeCreateDTO(
                name="Санкт-Петербург", region="Санкт-Петербург", country="Россия"
            ),
        )
    )

    assert created.name == "Невский проспект, 1"
    async with sessionmaker_() as session:
        city = (
            await session.execute(
                select(CityORM).where(CityORM.name == "Санкт-Петербург")
            )
        ).scalar_one()
    assert city.id == created.city_id


async def test_create_cascade_reuses_an_existing_city_by_name(
    sessionmaker_, city_id, published
):
    service = AddressService(AddressUOW(sessionmaker_))
    created = await service.create_cascade(
        AddressCascadeCreateDTO(
            street="Арбат",
            house="1",
            city=CityCascadeCreateDTO(name="Москва", region="Москва", country="Россия"),
        )
    )

    assert created.city_id == city_id


async def test_patch_updates_name_spot_and_recomposes_name_from_parsed(
    sessionmaker_, city_id, published
):
    service = AddressService(AddressUOW(sessionmaker_))
    created = await _address(sessionmaker_, city_id, "Старое имя")

    renamed = await service.patch(
        AddressPatchDTO(
            id=created.id,
            name="Новое имя",
            spot=PointDTO(lat=55.75, lon=37.6),
            fields_set=frozenset({"name", "spot"}),
        )
    )
    assert renamed.name == "Новое имя"
    assert renamed.spot.lat == pytest.approx(55.75)

    reparsed = await service.patch(
        AddressPatchDTO(
            id=created.id,
            parsed=AddressFieldsDTO(street="Арбат", house="11"),
            fields_set=frozenset({"parsed"}),
        )
    )
    assert reparsed.name == "Арбат, 11"
    assert reparsed.spot.lon == pytest.approx(37.6)


async def test_patch_ignores_explicit_null_for_required_columns(
    sessionmaker_, city_id, published
):
    service = AddressService(AddressUOW(sessionmaker_))
    created = await _address(sessionmaker_, city_id)

    patched = await service.patch(
        AddressPatchDTO(
            id=created.id,
            name=None,
            city_id=None,
            fields_set=frozenset({"name", "city_id"}),
        )
    )

    assert (patched.name, patched.city_id) == ("Арбат, 10", city_id)


async def test_address_proxy_location_is_idempotent_and_publishes_once(
    sessionmaker_, city_id, published
):
    address = await _address(sessionmaker_, city_id)
    service = LocationService(LocationUOW(sessionmaker_))

    first = await service.create_from_address(address.id, None)
    second = await service.create_from_address(address.id, None)
    third = await service.create(LocationCreateDTO(address_id=address.id))

    assert first.id == second.id == third.id
    assert first.name is None and first.address.name == "Арбат, 10"
    assert [name for name, _ in published].count("on_location_created") == 1
    [(_, [sent])] = [
        (name, payload) for name, payload in published if name == "on_location_created"
    ]
    assert sent.name == "Арбат, 10"


async def test_concurrent_address_picks_resolve_to_one_proxy(
    sessionmaker_, city_id, published
):
    address = await _address(sessionmaker_, city_id)

    locations = await asyncio.gather(
        *(
            LocationService(LocationUOW(sessionmaker_)).create_from_address(
                address.id, None
            )
            for _ in range(8)
        )
    )

    assert len({location.id for location in locations}) == 1


async def test_named_locations_at_one_address_are_allowed(
    sessionmaker_, city_id, published
):
    address = await _address(sessionmaker_, city_id)
    service = LocationService(LocationUOW(sessionmaker_))

    hall = await service.create_from_address(address.id, "Актовый зал")
    lab = await service.create_from_address(address.id, "Лаборатория")
    proxy = await service.create_from_address(address.id, None)

    assert len({hall.id, lab.id, proxy.id}) == 3


async def test_location_from_missing_address_is_not_found(
    sessionmaker_, city_id, published
):
    with pytest.raises(AddressNotExistsException):
        await LocationService(LocationUOW(sessionmaker_)).create_from_address(
            uuid4(), None
        )


async def test_deleting_address_removes_dependent_locations_and_publishes(
    sessionmaker_, city_id, published
):
    address_service = AddressService(AddressUOW(sessionmaker_))
    location_service = LocationService(LocationUOW(sessionmaker_))
    address = await _address(sessionmaker_, city_id)
    proxy = await location_service.create_from_address(address.id, None)
    hall = await location_service.create_from_address(address.id, "Актовый зал")
    standalone = await location_service.create(
        LocationCreateDTO(name="Скамейка", spot=PointDTO(lat=55.75, lon=37.62))
    )
    published.clear()

    await address_service.delete(address.id)

    remaining = await location_service.search(LocationFilterDTO(), PageParamDTO())
    assert [item.id for item in remaining.items] == [standalone.id]
    deleted_locations = next(
        payload for name, payload in published if name == "on_location_deleted"
    )
    assert set(deleted_locations) == {proxy.id, hall.id}
    assert ("on_address_deleted", [address.id]) in published


async def test_location_can_refine_an_address_with_its_own_spot(
    sessionmaker_, city_id, published
):
    address = await AddressService(AddressUOW(sessionmaker_)).create(
        AddressCreateDTO(
            city_id=city_id, name="Арбат, 10", spot=PointDTO(lat=55.75, lon=37.6)
        )
    )
    service = LocationService(LocationUOW(sessionmaker_))

    entrance = await service.create(
        LocationCreateDTO(
            name="Служебный вход",
            address_id=address.id,
            spot=PointDTO(lat=55.7501, lon=37.6001),
        )
    )

    assert entrance.address_id == address.id
    assert entrance.spot.lat == pytest.approx(55.7501)
    assert entrance.spot.lon == pytest.approx(37.6001)


async def test_upsert_many_inserts_then_updates_in_place(
    sessionmaker_, city_id, published
):
    ids = [uuid4(), uuid4()]

    def rows(prefix: str) -> list[dict]:
        return [
            {
                "id": address_id,
                "city_id": city_id,
                "name": f"{prefix} {i}",
                "spot": {"lat": 55.75, "lon": 37.6 + i / 100},
                "parsed": {"street": prefix, "house": str(i)},
            }
            for i, address_id in enumerate(ids)
        ]

    for prefix in ("Старая", "Новая"):
        async with AddressUOW(sessionmaker_) as uow:
            await uow.addresses.upsert_many(rows(prefix))
            await uow.commit()

    async with AddressUOW(sessionmaker_) as uow:
        stored = [await uow.addresses.get_by_id(address_id) for address_id in ids]

    assert [address.name for address in stored] == ["Новая 0", "Новая 1"]
