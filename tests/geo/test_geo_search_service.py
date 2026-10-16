from datetime import UTC, datetime
from typing import Any

from sqlalchemy import func, select
from support.geocoder import (
    Maker,
    Published,
    StubGeocoder,
    address_of,
    location_of,
    moscow_house,
    place_of,
)

from geo.bootstrap.run import address_id
from geo.dto.address import AddressCascadeCreateDTO, AddressCreateDTO
from geo.dto.city import CityCascadeCreateDTO
from geo.dto.location import LocationCreateDTO
from geo.dto.point import PointDTO
from geo.dto.search import SearchQueryDTO
from geo.geocoder.base import GeocoderError
from geo.models.address import AddressORM
from geo.models.city import CityORM
from geo.service.address import AddressService
from geo.service.external import ExternalSearch
from geo.service.location import LocationService
from geo.service.search import SearchService
from geo.uow.address import AddressUOW
from geo.uow.location import LocationUOW

KAZAN = CityCascadeCreateDTO(
    name="Казань", region="Республика Татарстан", country="Россия"
)


def _search(
    sessionmaker_: Maker, geocoder: StubGeocoder | None = None, **options: Any
) -> SearchService:
    external = ExternalSearch(geocoder, **options) if geocoder else None
    return SearchService(AddressUOW(sessionmaker_), external)


async def _count(sessionmaker_: Maker, model: type[Any]) -> int:
    async with sessionmaker_() as session:
        return (
            await session.execute(select(func.count()).select_from(model))
        ).scalar_one()


def _created_events(published: Published) -> list[Any]:
    return [payload for name, payload in published if name == "on_address_created"]


async def test_an_empty_local_result_is_filled_from_the_external_geocoder_and_stored(
    sessionmaker_: Maker, city_id: int, published: Published
) -> None:
    geocoder = StubGeocoder()

    result = await _search(sessionmaker_, geocoder).search(
        SearchQueryDTO(query="тверская 7 москва")
    )

    [hit] = result.items
    assert (hit.kind, hit.origin, result.external.state) == (
        "address",
        "external",
        "ok",
    )
    assert (address_of(hit).name, address_of(hit).locality) == (
        "Тверская улица, 7",
        "Москва, Россия",
    )
    assert (address_of(hit).source, address_of(hit).city_id) == ("photon", city_id)
    assert await _count(sessionmaker_, AddressORM) == 1
    assert await _count(sessionmaker_, CityORM) == 1
    assert [[item.id for item in batch] for batch in _created_events(published)] == [
        [address_of(hit).id]
    ]


async def test_a_stored_external_address_is_found_locally_the_next_time(
    sessionmaker_: Maker, city_id: int, published: Published
) -> None:
    geocoder = StubGeocoder()
    service = _search(sessionmaker_, geocoder)
    query = SearchQueryDTO(query="тверская 7 москва")

    first = await service.search(query)
    second = await service.search(query)

    assert [address_of(h).id for h in second.items] == [
        address_of(h).id for h in first.items
    ]
    assert [(h.origin, second.external.state) for h in second.items] == [
        ("local", "cached")
    ]
    assert len(geocoder.calls) == 1
    assert await _count(sessionmaker_, AddressORM) == 1
    assert len(_created_events(published)) == 1


async def test_an_address_that_is_already_stored_is_neither_duplicated_nor_rewritten(
    sessionmaker_: Maker, city_id: int, published: Published
) -> None:
    existing_id = address_id(city_id, "тверская улица", "7")
    async with AddressUOW(sessionmaker_) as uow:
        await uow.addresses.upsert_many(
            [
                {
                    "id": existing_id,
                    "city_id": city_id,
                    "name": "Тверская улица, 7",
                    "spot": {"lat": 55.0, "lon": 37.0},
                    "source": "osm",
                    "source_id": "node/9",
                    "synced_at": datetime.now(UTC),
                }
            ]
        )
        await uow.commit()

    result = await _search(sessionmaker_, StubGeocoder()).search(
        SearchQueryDTO(query="телеграф")
    )

    [hit] = result.items
    assert address_of(hit).id == existing_id
    assert (address_of(hit).source, address_of(hit).spot) == (
        "osm",
        PointDTO(lat=55.0, lon=37.0),
    )
    assert await _count(sessionmaker_, AddressORM) == 1
    assert _created_events(published) == []


async def test_another_spelling_of_a_region_reuses_the_existing_city(
    sessionmaker_: Maker, city_id: int, published: Published
) -> None:
    kazan = await AddressService(AddressUOW(sessionmaker_)).create_cascade(
        AddressCascadeCreateDTO(city=KAZAN, street="Баумана улица", house="1")
    )
    geocoder = StubGeocoder(
        [
            moscow_house(
                "Пушкина улица",
                "5",
                city="Казань",
                region="Татарстан",
                source_id="node/5",
            )
        ]
    )

    result = await _search(sessionmaker_, geocoder).search(
        SearchQueryDTO(query="пушкина 5 казань")
    )

    [hit] = result.items
    assert address_of(hit).city_id == kazan.city_id
    assert address_of(hit).locality == "Казань, Республика Татарстан, Россия"
    assert await _count(sessionmaker_, CityORM) == 2


async def test_the_same_city_name_in_another_region_is_a_different_city(
    sessionmaker_: Maker, city_id: int, published: Published
) -> None:
    await AddressService(AddressUOW(sessionmaker_)).create_cascade(
        AddressCascadeCreateDTO(
            city=CityCascadeCreateDTO(
                name="Железнодорожный", region="Московская область", country="Россия"
            ),
            street="Ленина улица",
            house="1",
        )
    )
    geocoder = StubGeocoder(
        [
            moscow_house(
                "Ленина улица",
                "1",
                city="Железнодорожный",
                region="Курская область",
                source_id="node/7",
            )
        ]
    )

    result = await _search(sessionmaker_, geocoder).search(
        SearchQueryDTO(query="ленина 1 железнодорожный")
    )

    assert {address_of(h).locality for h in result.items} >= {
        "Железнодорожный, Курская область, Россия"
    }
    assert await _count(sessionmaker_, CityORM) == 3


async def test_the_external_geocoder_is_left_alone_when_it_is_not_needed(
    sessionmaker_: Maker, city_id: int, published: Published
) -> None:
    addresses = AddressService(AddressUOW(sessionmaker_))
    for number in (1, 2, 3):
        await addresses.create(
            AddressCreateDTO(city_id=city_id, name=f"Тверская улица, {number}")
        )
    geocoder = StubGeocoder()
    service = _search(sessionmaker_, geocoder)

    enough = await service.search(SearchQueryDTO(query="тверская", limit=3))
    disabled = await service.search(SearchQueryDTO(query="телеграф", external=False))
    too_short = await service.search(SearchQueryDTO(query="тв"))
    only_places = await service.search(
        SearchQueryDTO(query="телеграф", kinds=("location",))
    )

    assert geocoder.calls == []
    assert [r.external.state for r in (enough, disabled, too_short, only_places)] == [
        "skipped"
    ] * 4


async def test_a_failing_geocoder_leaves_the_local_answer_and_reports_why(
    sessionmaker_: Maker, city_id: int, published: Published
) -> None:
    await AddressService(AddressUOW(sessionmaker_)).create(
        AddressCreateDTO(city_id=city_id, name="Мясницкая улица, 20")
    )

    failed = await _search(
        sessionmaker_, StubGeocoder(error=GeocoderError("HTTP 503"))
    ).search(SearchQueryDTO(query="мясницкая"))
    slow = await _search(sessionmaker_, StubGeocoder(delay=1.0), timeout=0.05).search(
        SearchQueryDTO(query="мясницкая")
    )

    assert [address_of(h).name for h in failed.items] == ["Мясницкая улица, 20"]
    assert [address_of(h).name for h in slow.items] == ["Мясницкая улица, 20"]
    assert (failed.external.state, slow.external.state) == ("error", "timeout")


async def test_the_point_pulls_equal_text_matches_towards_itself(
    sessionmaker_: Maker, city_id: int, published: Published
) -> None:
    addresses = AddressService(AddressUOW(sessionmaker_))
    moscow = await addresses.create(
        AddressCreateDTO(
            city_id=city_id,
            name="Тверская улица, 7",
            spot=PointDTO(lat=55.7583, lon=37.6116),
        )
    )
    kazan_city = (
        await addresses.create_cascade(
            AddressCascadeCreateDTO(city=KAZAN, street="Баумана улица", house="1")
        )
    ).city_id
    kazan = await addresses.create(
        AddressCreateDTO(
            city_id=kazan_city,
            name="Тверская улица, 7",
            spot=PointDTO(lat=55.7887, lon=49.1221),
        )
    )
    service = _search(sessionmaker_)

    near_kazan = await service.search(
        SearchQueryDTO(query="тверская 7", near=PointDTO(lat=55.79, lon=49.12))
    )
    near_moscow = await service.search(
        SearchQueryDTO(query="тверская 7", near=PointDTO(lat=55.76, lon=37.61))
    )

    assert [address_of(h).id for h in near_kazan.items] == [kazan.id, moscow.id]
    assert [address_of(h).id for h in near_moscow.items] == [moscow.id, kazan.id]


async def test_a_point_without_text_lists_the_nearest_places_of_both_kinds(
    sessionmaker_: Maker, city_id: int, published: Published
) -> None:
    addresses = AddressService(AddressUOW(sessionmaker_))
    locations = LocationService(LocationUOW(sessionmaker_))
    far = await addresses.create(
        AddressCreateDTO(
            city_id=city_id, name="Далеко", spot=PointDTO(lat=56.5, lon=37.6)
        )
    )
    close = await addresses.create(
        AddressCreateDTO(
            city_id=city_id, name="Рядом", spot=PointDTO(lat=55.7501, lon=37.6)
        )
    )
    bench = await locations.create(
        LocationCreateDTO(name="Скамейка", spot=PointDTO(lat=55.751, lon=37.6))
    )

    result = await _search(sessionmaker_).search(
        SearchQueryDTO(near=PointDTO(lat=55.75, lon=37.6))
    )

    assert [(h.kind, place_of(h).id) for h in result.items] == [
        ("address", close.id),
        ("location", bench.id),
        ("address", far.id),
    ]
    assert {h.score for h in result.items} == {None}


async def test_a_request_with_neither_text_nor_point_finds_nothing(
    sessionmaker_: Maker, city_id: int, published: Published
) -> None:
    result = await _search(sessionmaker_).search(SearchQueryDTO())

    assert result.items == []


async def test_named_locations_are_found_by_the_city_of_their_address(
    sessionmaker_: Maker, city_id: int, published: Published
) -> None:
    addresses = AddressService(AddressUOW(sessionmaker_))
    locations = LocationService(LocationUOW(sessionmaker_))
    address = await addresses.create(
        AddressCreateDTO(city_id=city_id, name="Мясницкая улица, 20")
    )
    hall = await locations.create(
        LocationCreateDTO(name="Актовый зал", address_id=address.id)
    )
    proxy = await locations.create_from_address(address.id, None)
    service = _search(sessionmaker_)

    named = await service.search(
        SearchQueryDTO(query="мясницкая москва", kinds=("location",))
    )
    with_proxies = await service.search(
        SearchQueryDTO(
            query="мясницкая москва", kinds=("location",), named_locations_only=False
        )
    )

    assert [location_of(h).id for h in named.items] == [hall.id]
    assert {location_of(h).id for h in with_proxies.items} == {hall.id, proxy.id}


async def test_the_city_filter_narrows_both_kinds(
    sessionmaker_: Maker, city_id: int, published: Published
) -> None:
    addresses = AddressService(AddressUOW(sessionmaker_))
    locations = LocationService(LocationUOW(sessionmaker_))
    moscow = await addresses.create(
        AddressCreateDTO(city_id=city_id, name="Тверская улица, 7")
    )
    kazan = await addresses.create_cascade(
        AddressCascadeCreateDTO(city=KAZAN, street="Тверская улица", house="7")
    )
    await locations.create(LocationCreateDTO(name="Тверской зал", address_id=moscow.id))
    kazan_hall = await locations.create(
        LocationCreateDTO(name="Тверской зал", address_id=kazan.id)
    )

    result = await _search(sessionmaker_).search(
        SearchQueryDTO(query="тверская", city_id=kazan.city_id)
    )

    assert {(h.kind, place_of(h).id) for h in result.items} == {
        ("address", kazan.id),
        ("location", kazan_hall.id),
    }
