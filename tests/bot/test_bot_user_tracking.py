from typing import Any

from aiogram.types import User as AiogramUser
from sqlalchemy import update
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker


def _sessionmaker(bot_engine: AsyncEngine) -> async_sessionmaker[AsyncSession]:
    return async_sessionmaker(bot_engine, expire_on_commit=False)


def _service(bot_engine: AsyncEngine) -> Any:
    from bot.tg.service.user import TelegramUserService
    from bot.tg.uow.user import UserUOW

    return TelegramUserService(UserUOW(_sessionmaker(bot_engine)))


def _tg_user(tgid: int, **extra: Any) -> AiogramUser:
    return AiogramUser(id=tgid, is_bot=False, first_name=f"User{tgid}", **extra)


async def test_a_user_first_seen_outside_start_is_registered(
    bot_engine: AsyncEngine, bot_seed: Any
) -> None:
    from bot.tg.model.user import TGUserORM

    result = await _service(bot_engine).update_user(
        _tg_user(900, language_code="ru")
    )

    assert result.id == 900
    assert [row.id for row in await bot_seed.all(TGUserORM)] == [900]


async def test_a_user_without_a_language_code_can_be_seen_repeatedly(
    bot_engine: AsyncEngine,
) -> None:
    service = _service(bot_engine)
    user = _tg_user(901)

    first = await service.update_user(user)
    second = await service.update_user(user)

    assert first.language_code is None
    assert second.id == 901


async def test_a_language_chosen_in_the_bot_survives_later_updates(
    bot_engine: AsyncEngine,
) -> None:
    from bot.tg.model.user import TGUserORM

    service = _service(bot_engine)
    await service.update_user(_tg_user(902, language_code="ru"))
    async with _sessionmaker(bot_engine)() as session:
        await session.execute(
            update(TGUserORM).where(TGUserORM.id == 902).values(language_code="EN")
        )
        await session.commit()

    result = await service.update_user(_tg_user(902, language_code="ru"))

    assert result.language_code == "en"
    assert result._is_lang_modified is True


async def test_a_user_who_wrote_again_becomes_active_again(
    bot_engine: AsyncEngine, bot_seed: Any
) -> None:
    from bot.tg.model.user import TGUserORM

    service = _service(bot_engine)
    await service.update_user(_tg_user(903))
    async with _sessionmaker(bot_engine)() as session:
        await session.execute(
            update(TGUserORM).where(TGUserORM.id == 903).values(is_active=False)
        )
        await session.commit()

    await service.update_user(_tg_user(903))

    assert [row.is_active for row in await bot_seed.all(TGUserORM)] == [True]
