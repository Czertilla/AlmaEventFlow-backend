from argparse import Namespace
from contextlib import AsyncExitStack, asynccontextmanager
from uuid import UUID, uuid4

import pytest
from aiohttp import web
from aiohttp.test_utils import TestServer
from sqlalchemy import func, select

from geo.bootstrap.run import Checkpoint, _run
from geo.bootstrap.sources import (
    OverpassError,
    OverpassSource,
    pick_administrative_names,
    resolve_mirror_urls,
)
from geo.models.address import AddressORM
from geo.models.location import LocationORM


def _node(node_id: int, street: str, house: str) -> dict:
    return {
        "type": "node",
        "id": node_id,
        "lat": 55.75,
        "lon": 37.6,
        "tags": {"addr:street": street, "addr:housenumber": house},
    }


class FakeMirror:
    def __init__(self, *responses: web.Response | dict, fallback: dict | None = None):
        self._queue = list(responses)
        self._fallback = fallback
        self.hits = 0

    async def handle(self, request: web.Request) -> web.Response:
        self.hits += 1
        item = self._queue.pop(0) if self._queue else self._fallback
        if isinstance(item, web.Response):
            return item
        return web.json_response(item if item is not None else {"elements": []})


@asynccontextmanager
async def serving(*mirrors: FakeMirror):
    async with AsyncExitStack() as stack:
        urls = []
        for mirror in mirrors:
            app = web.Application()
            app.router.add_post("/api", mirror.handle)
            server = TestServer(app)
            await server.start_server()
            stack.push_async_callback(server.close)
            urls.append(f"http://{server.host}:{server.port}/api")
        yield urls


async def _fetch_all(source: OverpassSource) -> list:
    return [raw async for raw in source.fetch((55.7, 37.5, 55.8, 37.7))]


def _source(urls: list[str], **kwargs) -> OverpassSource:
    return OverpassSource(urls=urls, timeout=5, attempts=kwargs.pop("attempts", 4), cooldown=0.01, **kwargs)


GOOD = {"elements": [_node(1, "Тверская улица", "7")]}


async def test_fails_over_from_a_broken_mirror():
    broken, healthy = FakeMirror(fallback=None), FakeMirror(fallback=GOOD)
    broken._queue = [web.Response(status=504)] * 5
    async with serving(broken, healthy) as urls:
        result = await _fetch_all(_source(urls))

    assert [raw.street for raw in result] == ["Тверская улица"]
    assert broken.hits >= 1 and healthy.hits >= 1


async def test_soft_runtime_errors_are_treated_as_failures_not_empty_results():
    timed_out = FakeMirror(
        {"elements": [], "remark": "runtime error: Query timed out in \"query\" at line 4"},
        fallback={"elements": [], "remark": "runtime error: Query timed out"},
    )
    healthy = FakeMirror(fallback=GOOD)
    async with serving(timed_out, healthy) as urls:
        result = await _fetch_all(_source(urls))

    assert len(result) == 1


async def test_client_errors_are_not_retried_on_other_mirrors():
    bad_query, untouched = FakeMirror(web.Response(status=400)), FakeMirror(fallback=GOOD)
    async with serving(bad_query, untouched) as urls:
        with pytest.raises(OverpassError):
            await _fetch_all(_source(urls))

    assert untouched.hits == 0


async def test_gives_up_after_the_configured_attempts():
    a, b = FakeMirror(), FakeMirror()
    a._queue, b._queue = [web.Response(status=504)] * 5, [web.Response(status=503)] * 5
    async with serving(a, b) as urls:
        with pytest.raises(OverpassError):
            await _fetch_all(_source(urls, attempts=3))

    assert a.hits + b.hits == 3


def test_pick_administrative_names_prefers_level_four_region_and_level_six_city():
    # Real data for a point in Kazan: admin_level isn't a fixed universal
    # scale, so a naive "deepest level available" pick would grab the
    # level-9 district instead of the level-6 city -- and the "городской
    # округ " administrative prefix is stripped from the winning name.
    levels = {
        2: "Россия",
        3: "Приволжский федеральный округ",
        4: "Татарстан",
        6: "городской округ Казань",
        9: "Вахитовский район",
    }
    assert pick_administrative_names(levels) == ("Россия", "Татарстан", "Казань")


def test_pick_administrative_names_prefers_settlement_over_its_district():
    # Real data for a point in Rostov Veliky (Yaroslavl oblast): the
    # level-6 entry is the *municipal district* around the town, not the
    # town itself -- the actual settlement is one level deeper. Picking
    # level 6 unconditionally would resolve "city" to the district's name.
    levels = {
        2: "Россия",
        3: "Центральный федеральный округ",
        4: "Ярославская область",
        6: "Ростовский муниципальный округ",
        8: "городское поселение Ростов",
    }
    assert pick_administrative_names(levels) == (
        "Россия",
        "Ярославская область",
        "Ростов",
    )


def test_pick_administrative_names_falls_back_to_region_with_no_city_level():
    # Real data for a point in Saint Petersburg: a federal city has no
    # level-6 entry, and levels 5/8 are sub-city boroughs, not the city.
    levels = {
        2: "Россия",
        3: "Северо-Западный федеральный округ",
        4: "Санкт-Петербург",
        5: "Центральный район",
        8: "Дворцовый округ",
    }
    assert pick_administrative_names(levels) == (
        "Россия",
        "Санкт-Петербург",
        "Санкт-Петербург",
    )


def test_pick_administrative_names_falls_back_to_country_with_nothing_finer():
    assert pick_administrative_names({2: "Монако"}) == ("Монако", "Монако", "Монако")


def test_pick_administrative_names_requires_some_data():
    with pytest.raises(OverpassError):
        pick_administrative_names({})


def test_resolve_mirror_urls_mixes_known_names_and_raw_urls():
    servers = "z, http://46.36.220.238:8080/api/interpreter ,main"
    assert resolve_mirror_urls(servers) == [
        "https://z.overpass-api.de/api/interpreter",
        "http://46.36.220.238:8080/api/interpreter",
        "https://overpass-api.de/api/interpreter",
    ]


def test_checkpoint_roundtrip_and_signature_mismatch(tmp_path):
    path = tmp_path / "state.json"
    checkpoint = Checkpoint.load(path, "moscow|grid8")
    checkpoint.done.update({1, 5})
    checkpoint.save()

    assert Checkpoint.load(path, "moscow|grid8").done == {1, 5}
    assert Checkpoint.load(path, "moscow|grid9").done == set()
    assert Checkpoint.load(tmp_path / "missing.json", "x").done == set()


def _args(urls: list[str], state, **overrides) -> Namespace:
    values = {
        "city": "moscow",
        "min_lat": None,
        "min_lon": None,
        "max_lat": None,
        "max_lon": None,
        "grid": 2,
        "batch_size": 1000,
        "servers": ",".join(urls),
        "concurrency": 3,
        "timeout": 5.0,
        "attempts": 4,
        "cooldown": 0.01,
        "state": str(state),
        "fresh": False,
        "prune_stale": False,
    }
    return Namespace(**{**values, **overrides})


async def _address_count(sessionmaker_) -> int:
    async with sessionmaker_() as session:
        return (await session.execute(select(func.count()).select_from(AddressORM))).scalar_one()


async def test_run_imports_dedupes_and_resumes_from_checkpoint(sessionmaker_, tmp_path):
    payload = {
        "elements": [
            _node(1, "Тверская улица", "7"),
            _node(2, "тверская улица", "7"),
            _node(3, "Арбат", "10"),
        ]
    }
    flaky = FakeMirror(web.Response(status=504), fallback=payload)
    steady = FakeMirror(fallback=payload)
    state = tmp_path / "state.json"

    async with serving(flaky, steady) as urls:
        first = await _run(_args(urls, state), sessionmaker_)
        hits_after_first = flaky.hits + steady.hits
        second = await _run(_args(urls, state), sessionmaker_)
        hits_after_second = flaky.hits + steady.hits
        third = await _run(_args(urls, state, fresh=True), sessionmaker_)

    assert (first.done, first.failed) == (4, [])
    assert await _address_count(sessionmaker_) == 2
    assert second.total == 0 and hits_after_second == hits_after_first
    assert third.done == 4 and flaky.hits + steady.hits > hits_after_second


async def test_reimport_keeps_the_same_row_when_the_upstream_element_id_changes(
    sessionmaker_, tmp_path
):
    first = FakeMirror(fallback={"elements": [_node(1, "Тверская улица", "7")]})
    async with serving(first) as urls:
        await _run(_args(urls, tmp_path / "state1.json"), sessionmaker_)

    async with sessionmaker_() as session:
        stored = (await session.execute(select(AddressORM))).scalar_one()
        first_id, first_spot = stored.id, stored.spot

    # Same real-world address, but OSM re-mapped it under a different
    # element id (redrawn way, node retagged, ...) and the coordinates
    # shifted slightly -- a reimport must update the existing row, not
    # insert a second one.
    moved = FakeMirror(
        fallback={
            "elements": [
                {
                    "type": "way",
                    "id": 999,
                    "center": {"lat": 55.751, "lon": 37.601},
                    "tags": {"addr:street": "Тверская улица", "addr:housenumber": "7"},
                }
            ]
        }
    )
    async with serving(moved) as urls:
        await _run(_args(urls, tmp_path / "state2.json"), sessionmaker_)

    assert await _address_count(sessionmaker_) == 1
    async with sessionmaker_() as session:
        stored = (await session.execute(select(AddressORM))).scalar_one()
        assert stored.id == first_id
        assert stored.spot != first_spot


async def test_run_reports_cells_that_no_mirror_could_serve(sessionmaker_, tmp_path):
    dead = FakeMirror()
    dead._queue = [web.Response(status=504)] * 50
    state = tmp_path / "state.json"

    async with serving(dead) as urls:
        progress = await _run(_args(urls, state, attempts=2), sessionmaker_)

    assert progress.done == 0 and sorted(progress.failed) == [1, 2, 3, 4]
    assert not state.exists()


async def _addresses_by_street(sessionmaker_) -> dict[str, AddressORM]:
    async with sessionmaker_() as session:
        rows = (await session.execute(select(AddressORM))).scalars().all()
        return {row.parsed.street: row for row in rows if row.parsed}


async def _address_ids(sessionmaker_) -> set[UUID]:
    async with sessionmaker_() as session:
        return set((await session.execute(select(AddressORM.id))).scalars())


async def _insert_manual_address(sessionmaker_, city_id: int) -> UUID:
    address_id = uuid4()
    async with sessionmaker_() as session:
        session.add(AddressORM(id=address_id, city_id=city_id, name="Ручной адрес, 1"))
        await session.commit()
    return address_id


async def _attach_location(sessionmaker_, address_id: UUID) -> None:
    async with sessionmaker_() as session:
        session.add(LocationORM(address_id=address_id, name="Актовый зал"))
        await session.commit()


async def test_resync_prunes_gone_addresses_but_protects_referenced_and_manual_ones(
    sessionmaker_, tmp_path, published
):
    first_payload = {
        "elements": [
            _node(1, "Улица А", "1"),
            _node(2, "Улица Б", "2"),
            _node(3, "Улица В", "3"),
        ]
    }
    async with serving(FakeMirror(fallback=first_payload)) as urls:
        await _run(_args(urls, tmp_path / "state1.json", fresh=True), sessionmaker_)

    before = await _addresses_by_street(sessionmaker_)
    manual_id = await _insert_manual_address(sessionmaker_, before["Улица А"].city_id)
    await _attach_location(sessionmaker_, before["Улица Б"].id)

    # Second run's upstream payload has lost "Улица В" entirely -- a
    # resync must delete it, but "Улица Б" survives despite also being
    # missing here because a location still points at it, and the manual
    # address is never touched since it has no source at all.
    second_payload = {"elements": [_node(1, "Улица А", "1")]}
    async with serving(FakeMirror(fallback=second_payload)) as urls:
        await _run(
            _args(urls, tmp_path / "state2.json", fresh=True, prune_stale=True),
            sessionmaker_,
        )

    after = await _addresses_by_street(sessionmaker_)
    assert set(after) == {"Улица А", "Улица Б"}
    assert await _address_ids(sessionmaker_) >= {manual_id}
    assert ("on_address_deleted", [before["Улица В"].id]) in published
    assert not any(name == "on_location_deleted" for name, _ in published)


async def test_prune_stale_requires_fresh(tmp_path):
    with pytest.raises(ValueError):
        await _run(_args([], tmp_path / "state.json", prune_stale=True))


async def test_prune_stale_rejects_manual_bbox_override(tmp_path):
    with pytest.raises(ValueError):
        await _run(
            _args(
                [],
                tmp_path / "state.json",
                fresh=True,
                prune_stale=True,
                min_lat=55.7,
                min_lon=37.5,
                max_lat=55.8,
                max_lon=37.7,
            )
        )


async def test_prune_stale_run_twice_is_a_noop(sessionmaker_, tmp_path):
    payload = {"elements": [_node(1, "Улица А", "1"), _node(2, "Улица Б", "2")]}
    state = tmp_path / "state.json"

    async with serving(FakeMirror(fallback=payload)) as urls:
        await _run(_args(urls, state, fresh=True, prune_stale=True), sessionmaker_)
        ids_first = await _address_ids(sessionmaker_)
        await _run(_args(urls, state, fresh=True, prune_stale=True), sessionmaker_)
        ids_second = await _address_ids(sessionmaker_)

    assert ids_first == ids_second and len(ids_first) == 2
