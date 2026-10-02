from core.dto.pagination import PageParamDTO
from geo.dto.address import AddressCreateDTO, AddressFilterDTO
from geo.dto.location import LocationCreateDTO, LocationFilterDTO
from geo.dto.point import PointDTO
from geo.service.address import AddressService
from geo.service.location import LocationService
from geo.uow.address import AddressUOW
from geo.uow.location import LocationUOW

STREETS = [
    "Тверская улица, 7",
    "Тверская улица, 70",
    "Большая Тверская-Ямская улица, 12",
    "улица Ленина, 1",
    "Ленинский проспект, 32",
    "Мясницкая улица, 20",
    "Покровка, 47к2",
]


async def _seed_addresses(sessionmaker_, city_id) -> dict:
    service = AddressService(AddressUOW(sessionmaker_))
    return {
        name: await service.create(AddressCreateDTO(city_id=city_id, name=name))
        for name in STREETS
    }


async def _address_names(sessionmaker_, query: str, **filters) -> list[str]:
    page = await AddressService(AddressUOW(sessionmaker_)).search(
        AddressFilterDTO(search=query, **filters), PageParamDTO()
    )
    return [item.name for item in page.items]


async def test_address_search_matches_word_forms(sessionmaker_, city_id, published):
    await _seed_addresses(sessionmaker_, city_id)

    assert "Мясницкая улица, 20" in await _address_names(
        sessionmaker_, "мясницкой улицы"
    )
    assert set(await _address_names(sessionmaker_, "тверской")) == {
        "Тверская улица, 7",
        "Тверская улица, 70",
        "Большая Тверская-Ямская улица, 12",
    }


async def test_address_search_is_prefix_aware_and_house_number_narrows(
    sessionmaker_, city_id, published
):
    await _seed_addresses(sessionmaker_, city_id)

    assert await _address_names(sessionmaker_, "покровк") == ["Покровка, 47к2"]
    assert await _address_names(sessionmaker_, "тверск 7") == [
        "Тверская улица, 7",
        "Тверская улица, 70",
    ]


async def test_exact_stem_outranks_longer_prefix_match(
    sessionmaker_, city_id, published
):
    await _seed_addresses(sessionmaker_, city_id)

    assert (await _address_names(sessionmaker_, "ленин"))[0] == "улица Ленина, 1"


async def test_address_search_tolerates_typos_only_when_nothing_matches(
    sessionmaker_, city_id, published
):
    await _seed_addresses(sessionmaker_, city_id)

    assert "Тверская улица, 7" in await _address_names(sessionmaker_, "твеская")
    assert await _address_names(sessionmaker_, "zzzz") == []
    assert await _address_names(sessionmaker_, "!!!") == []


async def test_address_search_respects_city_filter(sessionmaker_, city_id, published):
    await _seed_addresses(sessionmaker_, city_id)

    assert await _address_names(sessionmaker_, "тверская", city_id=city_id + 1) == []


async def test_location_search_matches_own_name_and_address_name(
    sessionmaker_, city_id, published
):
    addresses = await _seed_addresses(sessionmaker_, city_id)
    service = LocationService(LocationUOW(sessionmaker_))
    hall = await service.create(
        LocationCreateDTO(
            name="Актовый зал", address_id=addresses["Мясницкая улица, 20"].id
        )
    )
    bench = await service.create(
        LocationCreateDTO(
            name="Скамейка у фонтана", spot=PointDTO(lat=55.75, lon=37.62)
        )
    )
    proxy = await service.create_from_address(addresses["Тверская улица, 7"].id, None)

    async def found(**filter_kwargs) -> set:
        page = await service.search(LocationFilterDTO(**filter_kwargs), PageParamDTO())
        return {item.id for item in page.items}

    assert await found(search="актового зала") == {hall.id}
    assert await found(search="мясницкая") == {hall.id}
    assert await found(search="фонтан") == {bench.id}
    assert await found(search="тверская") == {proxy.id}
    assert await found(search="тверская", name__isnull=False) == set()
    assert await found(name__isnull=False) == {hall.id, bench.id}
    assert await found() == {hall.id, bench.id, proxy.id}


async def test_address_search_near_orders_by_distance(
    sessionmaker_, city_id, published
):
    service = AddressService(AddressUOW(sessionmaker_))
    near = await service.create(
        AddressCreateDTO(
            city_id=city_id, name="Рядом", spot=PointDTO(lat=55.751, lon=37.618)
        )
    )
    mid = await service.create(
        AddressCreateDTO(
            city_id=city_id, name="Средне", spot=PointDTO(lat=55.80, lon=37.618)
        )
    )
    far = await service.create(
        AddressCreateDTO(
            city_id=city_id, name="Далеко", spot=PointDTO(lat=56.5, lon=37.618)
        )
    )
    no_spot = await service.create(AddressCreateDTO(city_id=city_id, name="Без точки"))

    page = await service.search(
        AddressFilterDTO(), PageParamDTO(), near=PointDTO(lat=55.75, lon=37.6173)
    )

    assert [item.id for item in page.items] == [near.id, mid.id, far.id]
    assert no_spot.id not in {item.id for item in page.items}


async def test_address_search_near_is_ignored_when_search_text_is_given(
    sessionmaker_, city_id, published
):
    await _seed_addresses(sessionmaker_, city_id)

    page = await AddressService(AddressUOW(sessionmaker_)).search(
        AddressFilterDTO(search="тверской"), PageParamDTO(), near=PointDTO(lat=0, lon=0)
    )

    assert {item.name for item in page.items} == {
        "Тверская улица, 7",
        "Тверская улица, 70",
        "Большая Тверская-Ямская улица, 12",
    }


async def test_location_search_near_falls_back_to_address_spot(
    sessionmaker_, city_id, published
):
    address_service = AddressService(AddressUOW(sessionmaker_))
    location_service = LocationService(LocationUOW(sessionmaker_))
    near_address = await address_service.create(
        AddressCreateDTO(
            city_id=city_id, name="Рядом", spot=PointDTO(lat=55.751, lon=37.618)
        )
    )
    far_address = await address_service.create(
        AddressCreateDTO(
            city_id=city_id, name="Далеко", spot=PointDTO(lat=56.5, lon=37.618)
        )
    )
    hall = await location_service.create(
        LocationCreateDTO(name="Зал", address_id=near_address.id)
    )
    bench = await location_service.create(
        LocationCreateDTO(name="Скамейка", spot=PointDTO(lat=55.752, lon=37.619))
    )
    far_hall = await location_service.create(
        LocationCreateDTO(name="Дальний зал", address_id=far_address.id)
    )

    page = await location_service.search(
        LocationFilterDTO(), PageParamDTO(), near=PointDTO(lat=55.75, lon=37.6173)
    )

    ids = [item.id for item in page.items]
    assert ids[-1] == far_hall.id
    assert set(ids[:2]) == {hall.id, bench.id}
