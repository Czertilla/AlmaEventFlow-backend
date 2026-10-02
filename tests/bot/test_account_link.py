from collections.abc import Awaitable, Callable
from typing import Any
from uuid import uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncEngine, async_sessionmaker

LinkCodeIssuer = Callable[..., Awaitable[str]]


def _uow(bot_engine: AsyncEngine) -> Any:
    from bot.tg.uow.account_link import AccountLinkUOW

    return AccountLinkUOW(async_sessionmaker(bot_engine, expire_on_commit=False))


async def test_link_creates_account_and_sets_link(
    bot_engine: AsyncEngine, bot_seed: Any, link_code: LinkCodeIssuer
) -> None:
    from bot.model.user import UserORM
    from bot.tg.model.user import TGUserORM
    from bot.tg.service.account_link import AccountLinkService

    tgid = 111
    await bot_seed.tg_user(tgid)
    person_id = uuid4()

    result = await AccountLinkService(_uow(bot_engine)).link(
        tgid, await link_code(person_id)
    )

    assert result.id == tgid
    assert result.user_id is not None

    accounts = await bot_seed.all(UserORM)
    assert len(accounts) == 1
    assert accounts[0].person_id == person_id

    tg_rows = await bot_seed.all(TGUserORM)
    assert tg_rows[0].user_id == accounts[0].id


async def test_relink_replaces_previous_tgid(
    bot_engine: AsyncEngine, bot_seed: Any, link_code: LinkCodeIssuer
) -> None:
    from bot.model.user import UserORM
    from bot.tg.model.user import TGUserORM
    from bot.tg.service.account_link import AccountLinkService

    old_tgid, new_tgid = 222, 333
    await bot_seed.tg_user(old_tgid)
    await bot_seed.tg_user(new_tgid)
    person_id = uuid4()
    service = AccountLinkService(_uow(bot_engine))

    await service.link(old_tgid, await link_code(person_id))
    await service.link(new_tgid, await link_code(person_id))

    accounts = await bot_seed.all(UserORM)
    assert len(accounts) == 1  # same AEF identity, not duplicated

    tg_rows = {row.id: row.user_id for row in await bot_seed.all(TGUserORM)}
    assert tg_rows[new_tgid] == accounts[0].id
    assert tg_rows[old_tgid] is None  # old link cleared


async def test_unlink_clears_link(
    bot_engine: AsyncEngine, bot_seed: Any, link_code: LinkCodeIssuer
) -> None:
    from bot.tg.model.user import TGUserORM
    from bot.tg.service.account_link import AccountLinkService

    tgid = 444
    await bot_seed.tg_user(tgid)
    service = AccountLinkService(_uow(bot_engine))
    await service.link(tgid, await link_code(uuid4()))

    result = await service.unlink(tgid)

    assert result.user_id is None
    tg_rows = await bot_seed.all(TGUserORM)
    assert tg_rows[0].user_id is None


async def test_unlink_unknown_tgid_returns_none(
    bot_engine: AsyncEngine, bot_seed: Any
) -> None:
    from bot.tg.service.account_link import AccountLinkService

    result = await AccountLinkService(_uow(bot_engine)).unlink(999)

    assert result is None


async def test_link_code_can_only_be_used_once(
    bot_engine: AsyncEngine, bot_seed: Any, link_code: LinkCodeIssuer
) -> None:
    from bot.exc.user import LinkTokenExpiredException
    from bot.tg.service.account_link import AccountLinkService

    tgid = 555
    await bot_seed.tg_user(tgid)
    service = AccountLinkService(_uow(bot_engine))
    code = await link_code(uuid4())
    await service.link(tgid, code)

    with pytest.raises(LinkTokenExpiredException):
        await service.link(tgid, code)


async def test_link_rejects_an_unknown_or_expired_code(
    bot_engine: AsyncEngine, bot_seed: Any
) -> None:
    from bot.exc.user import LinkTokenExpiredException
    from bot.tg.service.account_link import AccountLinkService

    tgid = 666
    await bot_seed.tg_user(tgid)

    with pytest.raises(LinkTokenExpiredException):
        await AccountLinkService(_uow(bot_engine)).link(tgid, "no-such-code")


async def test_link_rejects_a_code_without_a_person_id(
    bot_engine: AsyncEngine, bot_seed: Any, link_code: LinkCodeIssuer
) -> None:
    from bot.exc.user import InvalidLinkTokenException
    from bot.tg.service.account_link import AccountLinkService

    tgid = 777
    await bot_seed.tg_user(tgid)
    code = await link_code(value="not-a-uuid")

    with pytest.raises(InvalidLinkTokenException):
        await AccountLinkService(_uow(bot_engine)).link(tgid, code)
