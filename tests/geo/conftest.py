import os

import geo.api  # noqa: F401  (must load before geo.service.*, else circular import)
import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

_GEO_TABLES = ("location", "address", "city", "region", "country")

_PUBLISHERS = {
    "geo.service.address": (
        "on_address_created",
        "on_address_updated",
        "on_address_deleted",
        "on_location_deleted",
    ),
    "geo.service.location": (
        "on_location_created",
        "on_location_updated",
        "on_location_deleted",
    ),
}


def _geo_url() -> str:
    return (
        f"postgresql+asyncpg://{os.environ['DB_USER']}:{os.environ['DB_PASS']}"
        f"@{os.environ['DB_HOST']}:{os.environ['DB_PORT']}/geo"
    )


@pytest.fixture
async def geo_engine(test_database):
    engine = create_async_engine(_geo_url())
    try:
        yield engine
    finally:
        async with engine.begin() as conn:
            await conn.execute(
                text(
                    "TRUNCATE "
                    + ", ".join(_GEO_TABLES)
                    + " RESTART IDENTITY CASCADE"
                )
            )
        await engine.dispose()


@pytest.fixture
def sessionmaker_(geo_engine):
    return async_sessionmaker(geo_engine, expire_on_commit=False)


@pytest.fixture
async def city_id(geo_engine) -> int:
    async with geo_engine.begin() as conn:
        await conn.execute(
            text("INSERT INTO country (name, code) VALUES ('Россия', 'RU')")
        )
        await conn.execute(
            text("INSERT INTO region (country_id, name) VALUES (1, 'Москва')")
        )
        return (
            await conn.execute(
                text(
                    "INSERT INTO city (region_id, name) "
                    "VALUES (1, 'Москва') RETURNING id"
                )
            )
        ).scalar_one()


@pytest.fixture
def published(monkeypatch) -> list[tuple[str, list]]:
    events: list[tuple[str, list]] = []

    def recorder(name: str):
        async def publish(payload):
            events.append((name, payload))

        return publish

    for module, names in _PUBLISHERS.items():
        for name in names:
            monkeypatch.setattr(f"{module}.{name}", recorder(name))
    return events
