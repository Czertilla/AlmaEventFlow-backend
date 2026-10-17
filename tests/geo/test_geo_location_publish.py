from typing import Any

import pytest

from core.schema.message.geo import LocationData
from geo.dto.address import AddressCreateDTO, AddressPatchDTO
from geo.dto.location import LocationCreateDTO
from geo.dto.point import PointDTO
from geo.service.address import AddressService
from geo.service.location import LocationService
from geo.uow.address import AddressUOW
from geo.uow.location import LocationUOW

Published = list[tuple[str, list[Any]]]

ARBAT = PointDTO(lat=55.7522, lon=37.5921)


def _sent(published: Published, name: str) -> list[LocationData]:
    return [item for event, batch in published if event == name for item in batch]


async def _address(sessionmaker_: Any, city_id: int, spot: PointDTO | None = ARBAT):
    return await AddressService(AddressUOW(sessionmaker_)).create(
        AddressCreateDTO(city_id=city_id, name="Арбат, 10", spot=spot)
    )


async def test_a_location_on_a_point_tells_where_it_is(
    sessionmaker_: Any, city_id: int, published: Published
) -> None:
    created = await LocationService(LocationUOW(sessionmaker_)).create(
        LocationCreateDTO(name="Скамейка", spot=PointDTO(lat=55.75, lon=37.62))
    )

    (sent,) = _sent(published, "on_location_created")
    assert (sent.id, sent.name) == (created.id, "Скамейка")
    assert (sent.lat, sent.lon) == (pytest.approx(55.75), pytest.approx(37.62))


async def test_a_location_at_an_address_tells_where_the_address_is(
    sessionmaker_: Any, city_id: int, published: Published
) -> None:
    address = await _address(sessionmaker_, city_id)

    await LocationService(LocationUOW(sessionmaker_)).create_from_address(
        address.id, None
    )

    (sent,) = _sent(published, "on_location_created")
    assert sent.name == "Арбат, 10"
    assert (sent.lat, sent.lon) == (pytest.approx(ARBAT.lat), pytest.approx(ARBAT.lon))


async def test_its_own_point_wins_over_the_address(
    sessionmaker_: Any, city_id: int, published: Published
) -> None:
    address = await _address(sessionmaker_, city_id)

    await LocationService(LocationUOW(sessionmaker_)).create(
        LocationCreateDTO(
            name="Служебный вход",
            address_id=address.id,
            spot=PointDTO(lat=55.7501, lon=37.6001),
        )
    )

    (sent,) = _sent(published, "on_location_created")
    assert (sent.lat, sent.lon) == (pytest.approx(55.7501), pytest.approx(37.6001))


async def test_a_location_with_nothing_on_a_map_says_so(
    sessionmaker_: Any, city_id: int, published: Published
) -> None:
    await LocationService(LocationUOW(sessionmaker_)).create_from_address(
        (await _address(sessionmaker_, city_id, spot=None)).id, None
    )
    await LocationService(LocationUOW(sessionmaker_)).find_or_create_text_only(
        "ул. Пушкина, 10, Казань"
    )

    told = [(i.name, i.lat, i.lon) for i in _sent(published, "on_location_created")]
    assert told == [
        ("Арбат, 10", None, None),
        ("ул. Пушкина, 10, Казань", None, None),
    ]


async def test_moving_an_address_tells_the_locations_at_it(
    sessionmaker_: Any, city_id: int, published: Published
) -> None:
    address = await _address(sessionmaker_, city_id)
    locations = LocationService(LocationUOW(sessionmaker_))
    proxy = await locations.create_from_address(address.id, None)
    hall = await locations.create_from_address(address.id, "Актовый зал")
    elsewhere = await locations.create(
        LocationCreateDTO(name="Скамейка", spot=PointDTO(lat=55.0, lon=37.0))
    )
    published.clear()

    await AddressService(AddressUOW(sessionmaker_)).patch(
        AddressPatchDTO(
            id=address.id,
            name="Арбат, 12",
            spot=PointDTO(lat=55.76, lon=37.6),
            fields_set=frozenset({"name", "spot"}),
        )
    )

    told = {item.id: item for item in _sent(published, "on_location_updated")}
    assert set(told) == {proxy.id, hall.id}
    assert elsewhere.id not in told
    assert told[proxy.id].name == "Арбат, 12"
    assert told[hall.id].name == "Актовый зал"
    for item in told.values():
        assert (item.lat, item.lon) == (pytest.approx(55.76), pytest.approx(37.6))


async def test_an_address_nobody_uses_tells_no_location(
    sessionmaker_: Any, city_id: int, published: Published
) -> None:
    address = await _address(sessionmaker_, city_id)
    published.clear()

    await AddressService(AddressUOW(sessionmaker_)).patch(
        AddressPatchDTO(
            id=address.id, name="Арбат, 12", fields_set=frozenset({"name"})
        )
    )

    assert _sent(published, "on_location_updated") == []
    assert [event for event, _ in published] == ["on_address_updated"]
