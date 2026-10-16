from datetime import UTC, datetime, timedelta
from typing import Any

from support.geocoder import (
    Maker,
    Published,
    StubGeocoder,
    address_of,
    count_rows,
    moscow_house,
    row_of,
    store_address,
    unplaced_house,
)

from geo.bootstrap.run import address_id
from geo.dto.address import AddressCreateDTO
from geo.dto.point import PointDTO
from geo.dto.search import SearchQueryDTO
from geo.models.address import AddressORM
from geo.models.city import CityORM
from geo.service.address import AddressService
from geo.service.external import ExternalSearch
from geo.service.search import SearchService
from geo.uow.address import AddressUOW

ROSTOV = ("Россия", "Ярославская область", "Ростов")
REVOLUTION = (57.1850, 39.4140)
FEW_METERS = 0.0005
FAR = 0.004


def _search(
    sessionmaker_: Maker,
    geocoder: StubGeocoder | None = None,
    fallback: StubGeocoder | None = None,
) -> SearchService:
    return SearchService(
        AddressUOW(sessionmaker_),
        ExternalSearch(geocoder) if geocoder else None,
        ExternalSearch(fallback) if fallback else None,
    )


async def _revolution(sessionmaker_: Maker) -> AddressORM:
    return await store_address(
        sessionmaker_, ROSTOV, "Революционная улица", "1", REVOLUTION
    )


def _rostov_house(
    street: str = "Революционная улица",
    house: str = "1",
    *,
    lat: float = REVOLUTION[0],
    lon: float = REVOLUTION[1],
    city: str = "Ростов Великий",
) -> Any:
    return moscow_house(
        street,
        house,
        city=city,
        region="Ярославская область",
        source_id="node/77",
        lat=lat,
        lon=lon,
    )


async def test_a_hit_for_an_address_filed_under_another_city_name_reuses_that_row(
    sessionmaker_: Maker, city_id: int, published: Published
) -> None:
    stored = await _revolution(sessionmaker_)
    geocoder = StubGeocoder([_rostov_house(lat=REVOLUTION[0] + FEW_METERS)])

    result = await _search(sessionmaker_, geocoder).search(
        SearchQueryDTO(query="революционная 1 ростов")
    )

    assert [address_of(hit).id for hit in result.items] == [stored.id]
    assert (await row_of(sessionmaker_, stored.id)).source == "osm"
    assert address_of(result.items[0]).spot == PointDTO(
        lat=REVOLUTION[0], lon=REVOLUTION[1]
    )
    assert await count_rows(sessionmaker_, AddressORM) == 1
    assert await count_rows(sessionmaker_, CityORM) == 2
    assert [name for name, _ in published if name == "on_address_created"] == []


async def test_the_same_street_and_house_far_away_is_another_address(
    sessionmaker_: Maker, city_id: int, published: Published
) -> None:
    stored = await _revolution(sessionmaker_)
    geocoder = StubGeocoder([_rostov_house(lat=REVOLUTION[0] + FAR)])

    result = await _search(sessionmaker_, geocoder).search(
        SearchQueryDTO(query="революционная 1")
    )

    ids = {address_of(hit).id for hit in result.items}
    assert stored.id in ids
    assert len(ids) == 2
    assert await count_rows(sessionmaker_, AddressORM) == 2
    assert await count_rows(sessionmaker_, CityORM) == 3


async def test_the_street_type_and_the_word_order_do_not_make_a_new_address(
    sessionmaker_: Maker, city_id: int, published: Published
) -> None:
    stored = await store_address(
        sessionmaker_, ROSTOV, "Баумана улица", "43", REVOLUTION
    )
    geocoder = StubGeocoder([_rostov_house("улица Баумана", "43 ")])

    result = await _search(sessionmaker_, geocoder).search(
        SearchQueryDTO(query="ул. баумана 43 ростов")
    )

    assert [address_of(hit).id for hit in result.items] == [stored.id]
    assert await count_rows(sessionmaker_, AddressORM) == 1


async def test_another_house_next_door_is_not_a_twin(
    sessionmaker_: Maker, city_id: int, published: Published
) -> None:
    await _revolution(sessionmaker_)
    geocoder = StubGeocoder([_rostov_house(house="3", lat=REVOLUTION[0] + FEW_METERS)])

    await _search(sessionmaker_, geocoder).search(
        SearchQueryDTO(query="революционная 3 ростов")
    )

    assert await count_rows(sessionmaker_, AddressORM) == 2


async def test_a_photon_row_that_is_seen_again_takes_the_current_data(
    sessionmaker_: Maker, city_id: int, published: Published
) -> None:
    first = await _search(sessionmaker_, StubGeocoder()).search(
        SearchQueryDTO(query="тверская 7 москва")
    )
    stored = address_of(first.items[0])
    before = await row_of(sessionmaker_, stored.id)
    moved = moscow_house(
        "Тверская ул.", "7", source_id="way/5", lat=55.7585, lon=37.6118
    )

    second = await _search(sessionmaker_, StubGeocoder([moved])).search(
        SearchQueryDTO(query="тверская 7 москва", limit=10)
    )

    after = await row_of(sessionmaker_, stored.id)
    assert [address_of(hit).id for hit in second.items] == [stored.id]
    assert (after.name, after.source_id) == ("Тверская ул., 7", "way/5")
    assert after.synced_at and before.synced_at and after.synced_at > before.synced_at
    assert after.edited_at is not None
    assert await count_rows(sessionmaker_, AddressORM) == 1
    assert len([name for name, _ in published if name == "on_address_created"]) == 1


async def test_a_manual_row_is_never_refreshed_by_a_provider(
    sessionmaker_: Maker, city_id: int, published: Published
) -> None:
    manual = await AddressService(AddressUOW(sessionmaker_)).create(
        AddressCreateDTO(
            city_id=city_id,
            name="Тверская улица, 7",
            spot=PointDTO(lat=55.7583, lon=37.6116),
        )
    )

    await _search(sessionmaker_, StubGeocoder([moscow_house(lat=55.7584)])).search(
        SearchQueryDTO(query="телеграф")
    )

    row = await row_of(sessionmaker_, manual.id)
    assert (row.name, row.source, row.synced_at) == ("Тверская улица, 7", None, None)
    assert await count_rows(sessionmaker_, AddressORM) == 1


async def test_the_house_the_query_names_comes_first_when_the_local_list_is_full(
    sessionmaker_: Maker, city_id: int, published: Published
) -> None:
    addresses = AddressService(AddressUOW(sessionmaker_))
    for number in (70, 71, 72):
        await addresses.create(
            AddressCreateDTO(city_id=city_id, name=f"Тверская улица, {number}")
        )
    geocoder = StubGeocoder([moscow_house("Тверская улица", "7")])

    result = await _search(sessionmaker_, geocoder).search(
        SearchQueryDTO(query="тверская 7", limit=3)
    )

    assert address_of(result.items[0]).name == "Тверская улица, 7"
    assert len(result.items) == 3
    assert result.items[0].origin == "external"
    assert len(geocoder.calls) == 1


async def test_a_full_local_list_with_the_named_house_does_not_ask_a_provider(
    sessionmaker_: Maker, city_id: int, published: Published
) -> None:
    addresses = AddressService(AddressUOW(sessionmaker_))
    for number in (2, 21, 22):
        await addresses.create(
            AddressCreateDTO(city_id=city_id, name=f"Тверская улица, {number}")
        )
    geocoder = StubGeocoder()

    result = await _search(sessionmaker_, geocoder).search(
        SearchQueryDTO(query="тверская 2", limit=3)
    )

    assert geocoder.calls == []
    assert result.external.state == "skipped"


async def test_the_fallback_is_asked_when_photon_found_nothing(
    sessionmaker_: Maker, city_id: int, published: Published
) -> None:
    neighbour = await AddressService(AddressUOW(sessionmaker_)).create(
        AddressCreateDTO(
            city_id=city_id,
            name="Невский проспект, 1",
            spot=PointDTO(lat=55.7580, lon=37.6110),
        )
    )
    photon = StubGeocoder([], name="photon")
    overpass = StubGeocoder(
        [unplaced_house("Невский проспект", "28", lat=55.7590, lon=37.6120)],
        name="overpass",
    )

    result = await _search(sessionmaker_, photon, overpass).search(
        SearchQueryDTO(
            query="невский проспект 28", near=PointDTO(lat=55.759, lon=37.612)
        )
    )

    found = [address_of(hit) for hit in result.items if hit.origin == "external"]
    assert [(a.name, a.source, a.city_id) for a in found] == [
        ("Невский проспект, 28", "osm", neighbour.city_id)
    ]
    assert (result.external.state, result.external.provider) == ("ok", "overpass")
    assert (len(photon.calls), len(overpass.calls)) == (1, 1)
    assert found[0].id == address_id(city_id, "невский проспект", "28")


async def test_the_fallback_is_left_alone_when_photon_found_the_house(
    sessionmaker_: Maker, city_id: int, published: Published
) -> None:
    photon = StubGeocoder([moscow_house()], name="photon")
    overpass = StubGeocoder([unplaced_house()], name="overpass")

    result = await _search(sessionmaker_, photon, overpass).search(
        SearchQueryDTO(query="тверская 7 москва", limit=1)
    )

    assert overpass.calls == []
    assert result.external.provider == "photon"


async def test_a_hit_that_names_no_city_and_has_no_neighbour_is_dropped(
    sessionmaker_: Maker, city_id: int, published: Published
) -> None:
    await AddressService(AddressUOW(sessionmaker_)).create(
        AddressCreateDTO(
            city_id=city_id,
            name="Невский проспект, 1",
            spot=PointDTO(lat=55.7580, lon=37.6110),
        )
    )
    overpass = StubGeocoder(
        [unplaced_house("Невский проспект", "28", lat=55.80, lon=37.70)],
        name="overpass",
    )

    result = await _search(sessionmaker_, None, overpass).search(
        SearchQueryDTO(query="невский проспект 28")
    )

    assert [h.origin for h in result.items] == ["local"]
    assert await count_rows(sessionmaker_, AddressORM) == 1
    assert result.external.state == "ok"


async def test_an_unplaced_hit_that_is_already_stored_is_the_stored_row(
    sessionmaker_: Maker, city_id: int, published: Published
) -> None:
    stored = await store_address(
        sessionmaker_,
        ("Россия", "Москва", "Москва"),
        "Тверская улица",
        "7",
        (55.7583, 37.6116),
    )
    overpass = StubGeocoder([unplaced_house(lat=55.7584)], name="overpass")

    result = await _search(sessionmaker_, None, overpass).search(
        SearchQueryDTO(query="телеграф", limit=1)
    )

    assert [address_of(h).id for h in result.items] == [stored.id]
    assert await count_rows(sessionmaker_, AddressORM) == 1


async def test_rows_are_stamped_when_they_are_seen(
    sessionmaker_: Maker, city_id: int, published: Published
) -> None:
    started = datetime.now(UTC) - timedelta(seconds=5)

    result = await _search(sessionmaker_, StubGeocoder()).search(
        SearchQueryDTO(query="тверская 7 москва")
    )

    row = await row_of(sessionmaker_, address_of(result.items[0]).id)
    assert row.synced_at is not None and row.synced_at > started
