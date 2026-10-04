import os
from collections.abc import AsyncIterator
from typing import Any

os.environ.setdefault("OAUTH_GOOGLE_CLIENT_ID", "test")
os.environ.setdefault("OAUTH_GOOGLE_CLIENT_SECRET", "test")

import httpx
import pytest
from _outbox import Outbox
from sqlalchemy import text
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

_TABLES = '"user", oauth_account, person, session, refresh_token'

Maker = async_sessionmaker[AsyncSession]


@pytest.fixture
async def user_engine(test_database: None) -> AsyncIterator[AsyncEngine]:
    engine = create_async_engine(
        f"postgresql+asyncpg://{os.environ['DB_USER']}:{os.environ['DB_PASS']}"
        f"@{os.environ['DB_HOST']}:{os.environ['DB_PORT']}/user"
    )
    try:
        yield engine
    finally:
        async with engine.begin() as conn:
            await conn.execute(text(f"TRUNCATE {_TABLES} RESTART IDENTITY CASCADE"))
        await engine.dispose()


@pytest.fixture
def user_sessionmaker(user_engine: AsyncEngine) -> Maker:
    return async_sessionmaker(user_engine, expire_on_commit=True)


SERVICE = "user.service.user"

_EVENTS = {
    "publish_account_created": "created",
    "publish_account_updated": "updated",
    "publish_account_email_verified": "verified",
    "publish_account_deleted": "deleted",
    "publish_telegram_link_code_issued": "telegram_link_code",
}


@pytest.fixture
def outbox(monkeypatch: pytest.MonkeyPatch) -> Outbox:
    box = Outbox()

    def recorder(name: str) -> Any:
        async def record(*args: Any) -> None:
            box.events.append((name, args))

        return record

    async def verify(email: str, token: str, *_: Any, **__: Any) -> None:
        box.verify.append((email, token))

    async def reset(email: str, token: str, *_: Any, **__: Any) -> None:
        box.reset.append((email, token))

    async def notify(request: Any) -> None:
        box.notifications.append(request)

    for function, name in _EVENTS.items():
        monkeypatch.setattr(f"{SERVICE}.{function}", recorder(name))
    monkeypatch.setattr(f"{SERVICE}.send_verify_message", verify)
    monkeypatch.setattr(f"{SERVICE}.send_reset_message", reset)
    monkeypatch.setattr(f"{SERVICE}.send_notification", notify)
    return box


@pytest.fixture
async def client(
    user_sessionmaker: Maker, outbox: Outbox
) -> AsyncIterator[httpx.AsyncClient]:
    from user.app.app import app
    from user.dependencies.user import get_session_maker

    app.dependency_overrides[get_session_maker] = lambda: user_sessionmaker
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="https://test") as http:
        yield http
    app.dependency_overrides.pop(get_session_maker, None)
