from contextlib import AsyncExitStack, asynccontextmanager

from aiohttp import web
from aiohttp.test_utils import TestServer
from sqlalchemy import select

from geo.bootstrap.coverage import cell_of
from geo.bootstrap.sources import OverpassSource
from geo.dto.point import PointDTO
from geo.models.address import AddressORM
from geo.models.city import CityORM
from geo.service.live_fetch import _guarded_live_fetch, live_fetch
from geo.uow.address import AddressUOW


def _node(node_id: int, street: str, house: str, lat: float, lon: float) -> dict:
    return {
        "type": "node",
        "id": node_id,
        "lat": lat,
        "lon": lon,
        "tags": {"addr:street": street, "addr:housenumber": house},
    }


def _area(area_id: int, admin_level: int, name: str) -> dict:
    return {
        "type": "relation",
        "id": area_id,
        "tags": {
            "boundary": "administrative",
            "admin_level": str(admin_level),
            "name": name,
        },
    }


IS_IN_PAYLOAD = {
    "elements": [
        _area(1, 2, "Россия"),
        _area(2, 4, "Санкт-Петербург"),
    ]
}


class FakeMirror:
    """Responds to an ``is_in`` reverse-geocode query with ``is_in`` (when
    given) and to everything else with the usual queued/fallback address
    payload -- a real ``OverpassSource`` sends both kinds of requests to the
    same mirror pool."""

    def __init__(
        self,
        *responses: web.Response | dict,
        fallback: dict | None = None,
        is_in: dict | None = None,
    ):
        self._queue = list(responses)
        self._fallback = fallback
        self._is_in = is_in
        self.hits = 0

    async def handle(self, request: web.Request) -> web.Response:
        self.hits += 1
        body = await request.post()
        if self._is_in is not None and "is_in" in str(body.get("data", "")):
            return web.json_response(self._is_in)
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


def _source(urls: list[str]) -> OverpassSource:
    return OverpassSource(urls=urls, timeout=5, attempts=2, cooldown=0.01)


# Well outside CITY_BBOXES["moscow"] -- exercises the reverse-geocode path.
OUTSIDE = PointDTO(lat=59.93, lon=30.31)


def _payload_at(point: PointDTO) -> dict:
    return {"elements": [_node(1, "Невский проспект", "1", point.lat, point.lon)]}


def _mirror_at(point: PointDTO) -> FakeMirror:
    return FakeMirror(fallback=_payload_at(point), is_in=IS_IN_PAYLOAD)


async def test_live_fetch_resolves_the_real_city_and_marks_coverage(sessionmaker_):
    cell = cell_of(OUTSIDE.lat, OUTSIDE.lon)

    async with serving(_mirror_at(OUTSIDE)) as urls:
        await live_fetch(
            cell, OUTSIDE, sessionmaker=sessionmaker_, source=_source(urls)
        )

    async with sessionmaker_() as session:
        address = (await session.execute(select(AddressORM))).scalar_one()
        city = await session.get(CityORM, address.city_id)

    assert address.source == "osm"
    assert city.name == "Санкт-Петербург"

    async with AddressUOW(sessionmaker_) as uow:
        assert await uow.coverage.covered(*cell)


async def test_guarded_live_fetch_skips_a_covered_cell_but_fetches_an_uncovered_one(
    sessionmaker_,
):
    cell = cell_of(OUTSIDE.lat, OUTSIDE.lon)

    async with serving(_mirror_at(OUTSIDE)) as urls:
        await live_fetch(
            cell, OUTSIDE, sessionmaker=sessionmaker_, source=_source(urls)
        )

    elsewhere = PointDTO(lat=OUTSIDE.lat, lon=OUTSIDE.lon + 1.0)
    elsewhere_cell = cell_of(elsewhere.lat, elsewhere.lon)
    mirror = _mirror_at(elsewhere)
    async with serving(mirror) as retry_urls:
        retry_source = _source(retry_urls)

        await _guarded_live_fetch(cell, OUTSIDE, sessionmaker_, source=retry_source)
        assert mirror.hits == 0  # already covered -- never even requested

        await _guarded_live_fetch(
            elsewhere_cell, elsewhere, sessionmaker_, source=retry_source
        )
        assert mirror.hits == 2  # one is_in reverse-geocode + one address fetch

    async with AddressUOW(sessionmaker_) as uow:
        assert await uow.coverage.covered(*cell)
        assert await uow.coverage.covered(*elsewhere_cell)
