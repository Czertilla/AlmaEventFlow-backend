from typing import Any
from uuid import uuid4

import pytest
from sqlalchemy import select
from support.geocoder import Maker, Published

from core.dto.pagination import PageParamDTO
from geo.dto.address import (
    AddressCascadeCreateDTO,
    AddressCreateDTO,
    AddressFilterDTO,
    AddressPatchDTO,
)
from geo.dto.city import CityCascadeCreateDTO
from geo.dto.location import LocationCreateDTO, LocationFilterDTO
from geo.locality import compose_locality
from geo.models.address import AddressORM
from geo.service.address import AddressService
from geo.service.location import LocationService
from geo.uow.address import AddressUOW
from geo.uow.location import LocationUOW

KAZAN = CityCascadeCreateDTO(
    name="Казань", region="Республика Татарстан", country="Россия"
)
MOSCOW_TVERSKAYA = "Тверская улица, 7 | Москва, Россия"
KAZAN_TVERSKAYA = "Тверская улица, 7 | Казань, Республика Татарстан, Россия"
KAZAN_BAUMANA = "Баумана улица, 1 | Казань, Республика Татарстан, Россия"


@pytest.mark.parametrize(
    ("city", "region", "country", "expected"),
    [
        ("Москва", "Москва", "Россия", "Москва, Россия"),
        (
            "Казань",
            "Республика Татарстан",
            "Россия",
            "Казань, Республика Татарстан, Россия",
        ),
        ("Химки", "Московская область", "Россия", "Химки, Московская область, Россия"),
        ("Monaco", "Monaco", "Monaco", "Monaco"),
        ("Минск", "Минск", "Беларусь", "Минск, Беларусь"),
        (
            "  Казань ",
            " Республика Татарстан",
            "Россия ",
            "Казань, Республика Татарстан, Россия",
        ),
    ],
)
def test_compose_locality_drops_repeated_names(
    city: str, region: str, country: str, expected: str
) -> None:
    assert compose_locality(city, region, country) == expected


async def _names(sessionmaker_: Maker, query: str, **filters: Any) -> list[str]:
    page = await AddressService(AddressUOW(sessionmaker_)).search(
        AddressFilterDTO(search=query, **filters), PageParamDTO()
    )
    return [f"{item.name} | {item.locality}" for item in page.items]


async def _two_cities(sessionmaker_: Maker, city_id: int) -> None:
    service = AddressService(AddressUOW(sessionmaker_))
    await service.create(AddressCreateDTO(city_id=city_id, name="Тверская улица, 7"))
    await service.create(AddressCreateDTO(city_id=city_id, name="Мясницкая улица, 20"))
    await service.create_cascade(
        AddressCascadeCreateDTO(city=KAZAN, street="Тверская улица", house="7")
    )
    await service.create_cascade(
        AddressCascadeCreateDTO(city=KAZAN, street="Баумана улица", house="1")
    )


async def test_address_gets_a_locality_string_next_to_its_clean_name(
    sessionmaker_: Maker, city_id: int, published: Published
) -> None:
    service = AddressService(AddressUOW(sessionmaker_))

    created = await service.create(
        AddressCreateDTO(city_id=city_id, name="Тверская улица, 7")
    )
    cascaded = await service.create_cascade(
        AddressCascadeCreateDTO(city=KAZAN, street="Баумана улица", house="1")
    )

    assert created.name == "Тверская улица, 7"
    assert created.locality == "Москва, Россия"
    assert cascaded.name == "Баумана улица, 1"
    assert cascaded.locality == "Казань, Республика Татарстан, Россия"
    assert (await service.read(created.id)).locality == "Москва, Россия"


async def test_locality_follows_the_city_when_it_changes(
    sessionmaker_: Maker, city_id: int, published: Published
) -> None:
    service = AddressService(AddressUOW(sessionmaker_))
    moscow = await service.create(
        AddressCreateDTO(city_id=city_id, name="Тверская улица, 7")
    )
    kazan = await service.create_cascade(
        AddressCascadeCreateDTO(city=KAZAN, street="Баумана улица", house="1")
    )

    moved = await service.patch(
        AddressPatchDTO(
            id=moscow.id, city_id=kazan.city_id, fields_set=frozenset({"city_id"})
        )
    )

    assert moved.locality == "Казань, Республика Татарстан, Россия"


async def test_bulk_upsert_stamps_locality_for_every_row(
    sessionmaker_: Maker, city_id: int, published: Published
) -> None:
    rows: list[dict[str, Any]] = [
        {"city_id": city_id, "name": f"Арбат, {number}", "spot": None}
        for number in range(1, 4)
    ]
    for row in rows:
        row["id"] = uuid4()
    async with AddressUOW(sessionmaker_) as uow:
        await uow.addresses.upsert_many(rows)
        await uow.commit()

    async with sessionmaker_() as session:
        localities = set((await session.execute(select(AddressORM.locality))).scalars())

    assert localities == {"Москва, Россия"}


async def test_search_takes_the_city_into_account(
    sessionmaker_: Maker, city_id: int, published: Published
) -> None:
    await _two_cities(sessionmaker_, city_id)

    assert await _names(sessionmaker_, "тверская москва") == [MOSCOW_TVERSKAYA]
    assert await _names(sessionmaker_, "москва тверская 7") == [MOSCOW_TVERSKAYA]
    assert await _names(sessionmaker_, "тверская казань") == [KAZAN_TVERSKAYA]
    assert await _names(sessionmaker_, "баумана татарстан") == [KAZAN_BAUMANA]


async def test_city_alone_lists_that_citys_addresses(
    sessionmaker_: Maker, city_id: int, published: Published
) -> None:
    await _two_cities(sessionmaker_, city_id)

    assert set(await _names(sessionmaker_, "москва")) == {
        MOSCOW_TVERSKAYA,
        "Мясницкая улица, 20 | Москва, Россия",
    }


async def test_street_match_outranks_a_city_only_match(
    sessionmaker_: Maker, city_id: int, published: Published
) -> None:
    service = AddressService(AddressUOW(sessionmaker_))
    await service.create(AddressCreateDTO(city_id=city_id, name="Улица Москворечье, 1"))
    await service.create(AddressCreateDTO(city_id=city_id, name="Арбат, 10"))

    assert (await _names(sessionmaker_, "москв"))[0].startswith("Улица Москворечье")


async def test_search_tolerates_a_typo_in_the_city(
    sessionmaker_: Maker, city_id: int, published: Published
) -> None:
    await _two_cities(sessionmaker_, city_id)

    assert (await _names(sessionmaker_, "тверская масква"))[0] == MOSCOW_TVERSKAYA


async def test_city_filter_still_narrows_a_city_search(
    sessionmaker_: Maker, city_id: int, published: Published
) -> None:
    await _two_cities(sessionmaker_, city_id)

    assert await _names(sessionmaker_, "тверская", city_id=city_id) == [
        MOSCOW_TVERSKAYA
    ]


async def test_location_search_takes_the_city_of_its_address_into_account(
    sessionmaker_: Maker, city_id: int, published: Published
) -> None:
    addresses = AddressService(AddressUOW(sessionmaker_))
    moscow = await addresses.create(
        AddressCreateDTO(city_id=city_id, name="Мясницкая улица, 20")
    )
    kazan = await addresses.create_cascade(
        AddressCascadeCreateDTO(city=KAZAN, street="Баумана улица", house="1")
    )
    service = LocationService(LocationUOW(sessionmaker_))
    hall = await service.create(
        LocationCreateDTO(name="Актовый зал", address_id=moscow.id)
    )
    await service.create(LocationCreateDTO(name="Актовый зал", address_id=kazan.id))

    page = await service.search(
        LocationFilterDTO(search="актовый зал москва"), PageParamDTO()
    )

    assert [item.id for item in page.items] == [hall.id]
