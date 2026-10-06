import os
from collections.abc import AsyncIterator, Awaitable, Callable, Sequence
from typing import Any
from uuid import UUID, uuid4

import pytest
from aiocache import SimpleMemoryCache  # pyright: ignore[reportMissingTypeStubs]
from aiogram import Bot
from aiogram.types import Update
from sqlalchemy import func, select, text
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from support.telegram import (
    RecordingSession,
    callback_update,
    feed,
    make_bot,
    member_update,
    message_update,
    user_json,
)

_BOT_TABLES = (
    'tg."user"',
    '"user"',
    "tg.collective_chat",
    "tg.message",
)

LinkCodeIssuer = Callable[..., Awaitable[str]]


def _bot_url() -> str:
    return (
        f"postgresql+asyncpg://{os.environ['DB_USER']}:{os.environ['DB_PASS']}"
        f"@{os.environ['DB_HOST']}:{os.environ['DB_PORT']}/bot"
    )


@pytest.fixture
async def bot_engine(test_database: None) -> AsyncIterator[AsyncEngine]:
    """Function-scoped engine on the migrated bot database. Created and
    disposed inside the test's event loop; every bot table is truncated on
    teardown for per-test isolation."""
    engine = create_async_engine(_bot_url())
    try:
        yield engine
    finally:
        async with engine.begin() as conn:
            await conn.execute(
                text("TRUNCATE " + ", ".join(_BOT_TABLES) + " RESTART IDENTITY CASCADE")
            )
        await engine.dispose()


@pytest.fixture(autouse=True)
async def link_code() -> AsyncIterator[LinkCodeIssuer]:
    from core.dependencies.redis import redis
    from core.utils.telegram_link import TELEGRAM_LINK_REDIS_PREFIX

    issued: list[str] = []

    async def issue(person_id: UUID | None = None, *, value: str | None = None) -> str:
        code = uuid4().hex
        stored = value if value is not None else str(person_id)
        await redis.set(f"{TELEGRAM_LINK_REDIS_PREFIX}{code}", stored, ex=600)
        issued.append(code)
        return code

    yield issue
    if issued:
        await redis.delete(*[f"{TELEGRAM_LINK_REDIS_PREFIX}{code}" for code in issued])
    await redis.connection_pool.disconnect()


@pytest.fixture(autouse=True)
def offline_aef_client(monkeypatch: pytest.MonkeyPatch) -> None:
    async def no_client(*args: object, **kwargs: object) -> None:
        return None

    monkeypatch.setattr("bot.tg.service.account_link.register_notify_client", no_client)
    monkeypatch.setattr("bot.tg.service.account_link.register_oauth_link", no_client)


@pytest.fixture
def bot_sessionmaker(
    bot_engine: AsyncEngine,
) -> async_sessionmaker[AsyncSession]:
    return async_sessionmaker(bot_engine, expire_on_commit=False)


@pytest.fixture
def bot_seed(
    bot_sessionmaker: async_sessionmaker[AsyncSession],
) -> "_BotSeeder":
    return _BotSeeder(bot_sessionmaker)


class _BotSeeder:
    def __init__(self, sessionmaker_: async_sessionmaker[AsyncSession]) -> None:
        self._sessionmaker = sessionmaker_

    async def tg_user(self, tgid: int, *, username: str | None = None) -> int:
        from bot.tg.model.user import TGUserORM

        async with self._sessionmaker() as session:
            session.add(
                TGUserORM(
                    id=tgid,
                    is_bot=False,
                    first_name=f"Test{tgid}",
                    username=username or f"test{tgid}",
                )
            )
            await session.commit()
        return tgid

    async def count(self, model: type[Any]) -> int:
        async with self._sessionmaker() as session:
            return (
                await session.execute(select(func.count()).select_from(model))
            ).scalar_one()

    async def all(self, model: type[Any]) -> Sequence[Any]:
        async with self._sessionmaker() as session:
            return (await session.execute(select(model))).scalars().all()

    @staticmethod
    def new_person_id() -> UUID:
        return uuid4()

    async def linked_tg_user(
        self, tgid: int, person_id: UUID, *, username: str | None = None
    ) -> int:
        from bot.model.user import UserORM
        from bot.tg.model.user import TGUserORM

        async with self._sessionmaker() as session:
            account = UserORM(person_id=person_id)
            session.add(account)
            await session.flush()
            session.add(
                TGUserORM(
                    id=tgid,
                    user_id=account.id,
                    is_bot=False,
                    first_name=f"Test{tgid}",
                    username=username or f"test{tgid}",
                    language_code="ru",
                )
            )
            await session.commit()
        return tgid


class TgHarness:
    """Feeds updates to the bot's real dispatcher and records what it sends
    back. Telegram, the other services (RPC) and the database are stood in
    for, everything between them is the production code."""

    def __init__(self, bot: Bot, session: RecordingSession) -> None:
        self.bot = bot
        self.session = session
        self.led: dict[str, list[tuple[UUID, str]]] = {}
        self.member_of: dict[str, list[tuple[UUID, str]]] = {}
        self.notifications = True
        self.errors: list[BaseException] = []
        self.touched: set[int] = set()

    def lead(self, person_id: UUID, *collectives: tuple[UUID, str]) -> None:
        self.led[str(person_id)] = list(collectives)

    def join(self, person_id: UUID, *collectives: tuple[UUID, str]) -> None:
        self.member_of[str(person_id)] = list(collectives)

    async def send(self, text: str, tgid: int, **kwargs: Any) -> None:
        self.touched.add(tgid)
        user = user_json(tgid, **({"username": f"u{tgid}"} | kwargs.pop("user", {})))
        await feed(self.bot, message_update(self.bot, text, user=user, **kwargs))

    async def press(self, data: str, tgid: int, **kwargs: Any) -> None:
        self.touched.add(tgid)
        user = user_json(tgid, **({"username": f"u{tgid}"} | kwargs.pop("user", {})))
        await feed(self.bot, callback_update(self.bot, data, user=user, **kwargs))

    async def deliver(self, update: Update) -> None:
        await feed(self.bot, update)

    def member_change(self, **kwargs: Any) -> Update:
        return member_update(self.bot, **kwargs)

    @property
    def texts(self) -> list[str]:
        return [str(call.text) for call in self.session.sent]

    @property
    def last_text(self) -> str:
        return self.texts[-1]

    def last_markup(self) -> Any:
        return self.session.sent[-1].reply_markup


@pytest.fixture
async def tg(
    bot_engine: AsyncEngine, monkeypatch: pytest.MonkeyPatch
) -> AsyncIterator[TgHarness]:
    from support.telegram import BOT_USERNAME

    from bot.tg.api.middleware.error import ErrorHandlerMiddleware
    from bot.tg.text.localization import i18n_manager
    from core.config.settings import settings
    from core.dependencies.redis import redis

    monkeypatch.setattr(settings, "BOT_TG_USERNAME", BOT_USERNAME)
    monkeypatch.setattr(settings, "FRONTEND_URL", "https://aef.example.test")
    sessionmaker = async_sessionmaker(bot_engine, expire_on_commit=False)
    monkeypatch.setattr("bot.uow.base._sessionmaker", sessionmaker)
    monkeypatch.setattr(i18n_manager, "cache", SimpleMemoryCache())

    bot, session = make_bot()
    harness = TgHarness(bot, session)

    def rows(registry: dict[str, list[tuple[UUID, str]]]) -> Callable[..., Any]:
        async def fetch(person_id: UUID) -> list[dict[str, Any]]:
            return [
                {"id": str(cid), "name": name}
                for cid, name in registry.get(str(person_id), [])
            ]

        return fetch

    led, joined = rows(harness.led), rows(harness.member_of)
    monkeypatch.setattr("bot.tg.service.actor.get_my_collectives", led)
    monkeypatch.setattr("bot.tg.service.collective_chat.get_my_collectives", led)
    monkeypatch.setattr("bot.tg.service.actor.get_my_memberships", joined)

    async def notifications_enabled(person_id: UUID) -> bool:
        return harness.notifications

    monkeypatch.setattr(
        "bot.tg.utils.notifications.get_telegram_notifications_enabled",
        notifications_enabled,
    )

    original = ErrorHandlerMiddleware._handle_unexpected_error  # pyright: ignore[reportPrivateUsage]

    async def record(self: Any, exc_type: Any, exc: BaseException, *args: Any) -> None:
        harness.errors.append(exc)
        await original(self, exc_type, exc, *args)

    monkeypatch.setattr(ErrorHandlerMiddleware, "_handle_unexpected_error", record)

    yield harness

    keys = [f"tg:hint:username:{tgid}" for tgid in harness.touched] + [
        f"tg:commands:{tgid}" for tgid in harness.touched
    ]
    if keys:
        await redis.delete(*keys)
    await redis.connection_pool.disconnect()
    await bot.session.close()
    assert not harness.errors, harness.errors
