from datetime import UTC, datetime
from typing import Any
from uuid import UUID, uuid4

import pytest
from support.geocoder import Maker

from geo.dto.location import LocationCreateDTO
from geo.dto.map import MapQueryDTO, MapViewDTO
from geo.dto.point import PointDTO
from geo.service.location import LocationService
from geo.service.map import MapService
from geo.service.viewport import bbox_ranges
from geo.uow.address import AddressUOW
from geo.uow.location import LocationUOW
from geo.uow.map import MapUOW

WEST, SOUTH, EAST, NORTH = 36.6, 55.2, 38.6, 56.2


async def _addresses(
    sessionmaker_: Maker,
    city_id: int,
    points: list[tuple[float, float]],
    *,
    prefix: str = "Адрес",
) -> list[UUID]:
    rows: list[dict[str, Any]] = [
        {
            "id": uuid4(),
            "city_id": city_id,
            "name": f"{prefix} {index}",
            "spot": {"lat": lat, "lon": lon},
            "source": "osm",
            "synced_at": datetime.now(UTC),
        }
        for index, (lat, lon) in enumerate(points)
    ]
    async with AddressUOW(sessionmaker_) as uow:
        await uow.addresses.upsert_many(rows)
        await uow.commit()
    return [row["id"] for row in rows]


async def _view(sessionmaker_: Maker, *, zoom: float, **options: Any) -> MapViewDTO:
    query = MapQueryDTO(
        west=WEST, south=SOUTH, east=EAST, north=NORTH, zoom=zoom, **options
    )
    return await MapService(MapUOW(sessionmaker_)).view(query)


def _dense_corner_and_sparse_points() -> tuple[
    list[tuple[float, float]], list[tuple[float, float]]
]:
    dense = [(55.2 + 0.0001 * n, 36.6 + 0.0001 * n) for n in range(300)]
    sparse = [
        (55.3 + 0.3 * row, 36.9 + 0.5 * col) for row in range(3) for col in range(4)
    ]
    return dense, sparse


async def test_a_dense_corner_does_not_crowd_out_the_rest_of_the_window(
    sessionmaker_: Maker, city_id: int
) -> None:
    dense, sparse = _dense_corner_and_sparse_points()
    await _addresses(sessionmaker_, city_id, dense, prefix="Плотный")
    await _addresses(sessionmaker_, city_id, sparse, prefix="Редкий")

    view = await _view(sessionmaker_, zoom=9)

    assert view.matched == len(dense) + len(sparse)
    assert sorted(entity.name for entity in view.entities) == sorted(
        f"Редкий {n}" for n in range(len(sparse))
    )
    assert [cluster.count for cluster in view.clusters] == [len(dense)]
    assert view.truncated is False
    assert len(view.entities) + sum(c.count for c in view.clusters) == view.matched


async def test_zooming_in_splits_a_cluster_and_the_deepest_zoom_lists_points(
    sessionmaker_: Maker, city_id: int
) -> None:
    near = [(55.7500, 37.6000), (55.7501, 37.6001), (55.7502, 37.6002)]
    await _addresses(sessionmaker_, city_id, near)

    far = await _view(sessionmaker_, zoom=12)
    closer = await _view(sessionmaker_, zoom=16)
    deepest = await _view(sessionmaker_, zoom=17)

    assert [c.count for c in far.clusters] == [3] and far.entities == []
    assert [c.count for c in closer.clusters] == [3]
    assert deepest.clusters == []
    assert len(deepest.entities) == 3
    assert {(e.lat, e.lon) for e in deepest.entities} == set(near)


async def test_a_larger_radius_merges_more_points_into_one_marker(
    sessionmaker_: Maker, city_id: int
) -> None:
    points = [(55.75, 37.50 + 0.02 * n) for n in range(10)]
    await _addresses(sessionmaker_, city_id, points)

    tight = await _view(sessionmaker_, zoom=11, radius_px=24)
    loose = await _view(sessionmaker_, zoom=11, radius_px=256)

    assert len(tight.clusters) + len(tight.entities) > len(loose.clusters) + len(
        loose.entities
    )
    assert tight.matched == loose.matched == 10


async def test_a_cluster_knows_its_centre_extent_and_what_it_is_made_of(
    sessionmaker_: Maker, city_id: int
) -> None:
    ids = await _addresses(
        sessionmaker_, city_id, [(55.7500, 37.6000), (55.7510, 37.6020)]
    )
    await LocationService(LocationUOW(sessionmaker_)).create(
        LocationCreateDTO(name="Скамейка", spot=PointDTO(lat=55.7505, lon=37.6010))
    )

    view = await _view(sessionmaker_, zoom=10)

    [cluster] = view.clusters
    assert (cluster.count, cluster.addresses, cluster.locations) == (3, 2, 1)
    assert cluster.lat == pytest.approx(55.7505)
    assert cluster.lon == pytest.approx(37.6010)
    assert (cluster.west, cluster.south, cluster.east, cluster.north) == (
        37.6000,
        55.7500,
        37.6020,
        55.7510,
    )
    assert len(ids) == 2


async def test_a_lone_point_comes_back_as_the_entity_itself(
    sessionmaker_: Maker, city_id: int
) -> None:
    [address_id] = await _addresses(sessionmaker_, city_id, [(55.75, 37.6)])

    view = await _view(sessionmaker_, zoom=8)

    [entity] = view.entities
    assert (entity.kind, entity.id, entity.name, entity.locality) == (
        "address",
        address_id,
        "Адрес 0",
        "Москва, Россия",
    )
    assert (entity.lat, entity.lon) == (55.75, 37.6)
    assert view.clusters == []


async def test_an_unnamed_address_location_is_not_a_second_marker(
    sessionmaker_: Maker, city_id: int
) -> None:
    [address_id] = await _addresses(sessionmaker_, city_id, [(55.75, 37.6)])
    locations = LocationService(LocationUOW(sessionmaker_))
    await locations.create_from_address(address_id, None)
    named = await locations.create_from_address(address_id, "Актовый зал")

    view = await _view(sessionmaker_, zoom=17)

    assert {(e.kind, e.id) for e in view.entities} == {
        ("address", address_id),
        ("location", named.id),
    }
    assert view.matched == 2


async def test_kinds_limit_what_is_drawn(sessionmaker_: Maker, city_id: int) -> None:
    await _addresses(sessionmaker_, city_id, [(55.75, 37.6)])
    await LocationService(LocationUOW(sessionmaker_)).create(
        LocationCreateDTO(name="Скамейка", spot=PointDTO(lat=55.8, lon=37.7))
    )

    only_locations = await _view(sessionmaker_, zoom=14, kinds=("location",))
    only_addresses = await _view(sessionmaker_, zoom=14, kinds=("address",))

    assert [e.kind for e in only_locations.entities] == ["location"]
    assert [e.kind for e in only_addresses.entities] == ["address"]


async def test_places_without_a_point_never_appear(
    sessionmaker_: Maker, city_id: int
) -> None:
    async with AddressUOW(sessionmaker_) as uow:
        await uow.addresses.add_one({"city_id": city_id, "name": "Без точки"})
        await uow.commit()

    view = await _view(sessionmaker_, zoom=10)

    assert (view.matched, view.entities, view.clusters) == (0, [], [])


async def test_a_full_window_returns_the_biggest_markers_and_says_it_was_cut(
    sessionmaker_: Maker, city_id: int
) -> None:
    points = [
        (55.2 + 0.1 * row, 36.7 + 0.1 * col) for row in range(9) for col in range(15)
    ]
    await _addresses(sessionmaker_, city_id, points)
    await _addresses(sessionmaker_, city_id, [(55.2001, 36.7001)] * 5, prefix="Лишний")

    view = await _view(sessionmaker_, zoom=13, limit=7)

    assert len(view.entities) + len(view.clusters) == 7
    assert view.truncated is True
    assert view.matched == len(points) + 5
    assert view.clusters[0].count == 6


async def test_a_window_across_the_antimeridian_sees_both_sides(
    sessionmaker_: Maker, city_id: int
) -> None:
    await _addresses(
        sessionmaker_, city_id, [(65.0, 179.9), (65.0, -179.9), (65.0, 170.0)]
    )
    across = MapQueryDTO(west=179.0, south=64.0, east=-179.0, north=66.0, zoom=8)
    west_only = MapQueryDTO(west=-180.0, south=64.0, east=-179.0, north=66.0, zoom=8)

    service = MapService(MapUOW(sessionmaker_))
    both = await service.view(across)
    one = await service.view(west_only)

    assert both.matched == 2
    assert one.matched == 1


@pytest.mark.parametrize(
    ("west", "east", "expected"),
    [
        (10.0, 20.0, [(10.0, 20.0)]),
        (-180.0, 180.0, [(-180.0, 180.0)]),
        (170.0, -170.0, [(170.0, 180.0), (-180.0, -170.0)]),
        (15.0, 15.0, [(15.0, 15.0)]),
    ],
)
def test_bbox_ranges_split_a_window_that_crosses_the_antimeridian(
    west: float, east: float, expected: list[tuple[float, float]]
) -> None:
    assert bbox_ranges(west, east) == expected
