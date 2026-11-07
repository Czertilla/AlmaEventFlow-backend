import os
from collections.abc import AsyncIterator
from profile.enum.audience import Audience
from profile.registry import Column, PersonalField, Source
from profile.registry import fields as registry_module
from typing import Any
from uuid import NAMESPACE_URL, UUID, uuid5

import httpx
import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from support.event import FakeEvent
from support.http import AsPerson, api_client, principal
from support.org import FakeOrg

_PUBLISHERS = {
    "on_person_created": ("person", "my_profile"),
    "on_person_updated": ("person", "my_profile"),
    "on_person_deleted": ("person",),
    "on_person_link_changed": ("person", "account", "my_profile"),
}


@pytest.fixture(autouse=True)
def org(monkeypatch: pytest.MonkeyPatch) -> FakeOrg:
    fake = FakeOrg()
    monkeypatch.setattr("profile.utils.org.rpc_call", fake)
    return fake


@pytest.fixture(autouse=True)
def event(monkeypatch: pytest.MonkeyPatch) -> FakeEvent:
    fake = FakeEvent()
    monkeypatch.setattr("profile.utils.event.rpc_call", fake)
    return fake


@pytest.fixture
async def profile_engine(test_database: None) -> AsyncIterator[AsyncEngine]:
    engine = create_async_engine(
        f"postgresql+asyncpg://{os.environ['DB_USER']}:{os.environ['DB_PASS']}"
        f"@{os.environ['DB_HOST']}:{os.environ['DB_PORT']}/profile"
    )
    try:
        yield engine
    finally:
        async with engine.begin() as conn:
            await conn.execute(
                text(
                    "TRUNCATE person, person_account_history, organization, diet, "
                    "student_degree, notification_outbox "
                    "RESTART IDENTITY CASCADE"
                )
            )
        await engine.dispose()


@pytest.fixture
def profile_sessionmaker(
    profile_engine: AsyncEngine,
) -> async_sessionmaker[AsyncSession]:
    return async_sessionmaker(profile_engine, expire_on_commit=False)


@pytest.fixture
def as_person(profile_engine: AsyncEngine) -> AsPerson:
    async def make(person_id: UUID) -> dict[str, str]:
        user_id = uuid5(NAMESPACE_URL, str(person_id))
        async with profile_engine.begin() as conn:
            await conn.execute(
                text(
                    "INSERT INTO person_account (person_id, user_id, created_at) "
                    "VALUES (:person, :user, now()) ON CONFLICT DO NOTHING"
                ),
                {"person": person_id, "user": user_id},
            )
        return principal(person_id=person_id, user_id=user_id)

    return make


@pytest.fixture
def published(monkeypatch: pytest.MonkeyPatch) -> list[tuple[str, Any]]:
    events: list[tuple[str, Any]] = []

    def recorder(name: str) -> Any:
        async def publish(payload: Any) -> None:
            events.append((name, payload))

        return publish

    for name, modules in _PUBLISHERS.items():
        for module in modules:
            monkeypatch.setattr(f"profile.service.{module}.{name}", recorder(name))
    return events


@pytest.fixture
async def api(
    profile_sessionmaker: async_sessionmaker[AsyncSession],
    published: list[tuple[str, Any]],
) -> AsyncIterator[httpx.AsyncClient]:
    from profile.app.app import app

    async with api_client(app, profile_sessionmaker) as client:
        yield client


SECRET_NOTE = PersonalField(
    key="secret_note.content",
    label="Секретная заметка",
    columns=(
        Column("secret_note", "body"),
        Column("secret_note", "due", kind="date"),
        Column("secret_note", "flag", kind="bool"),
    ),
    audience_default=Audience.PRIVATE,
    audience_min=Audience.PRIVATE,
    audience_max=Audience.PRIVATE,
    encrypted=True,
)


@pytest.fixture
async def secret_note(
    profile_engine: AsyncEngine, monkeypatch: pytest.MonkeyPatch
) -> AsyncIterator[PersonalField]:
    monkeypatch.setattr(
        registry_module,
        "_BY_KEY",
        {**registry_module._BY_KEY, SECRET_NOTE.key: SECRET_NOTE},  # pyright: ignore[reportPrivateUsage]
    )
    monkeypatch.setattr(
        registry_module,
        "_SOURCES",
        {
            **registry_module._SOURCES,  # pyright: ignore[reportPrivateUsage]
            "secret_note": Source("secret_note", person="person_id"),
        },
    )
    async with profile_engine.begin() as conn:
        await conn.execute(
            text(
                "CREATE TABLE secret_note (id uuid PRIMARY KEY, person_id uuid, "
                "body bytea, due bytea, flag bytea)"
            )
        )
    try:
        yield SECRET_NOTE
    finally:
        async with profile_engine.begin() as conn:
            await conn.execute(text("DROP TABLE IF EXISTS secret_note"))
