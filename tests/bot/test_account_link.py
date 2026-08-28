from uuid import uuid4

import jwt
import pytest
from sqlalchemy.ext.asyncio import async_sessionmaker

from core.config.settings import settings


def _uow(bot_engine):
    from bot.tg.uow.account_link import AccountLinkUOW

    return AccountLinkUOW(async_sessionmaker(bot_engine, expire_on_commit=False))


def _mint(person_id, *, aud="telegram-link", lifetime=600):
    return jwt.encode(
        {"person_id": str(person_id), "aud": aud},
        settings.USER_SECRET.get_secret_value(),
        algorithm="HS256",
    )


def _expired(person_id):
    return jwt.encode(
        {
            "person_id": str(person_id),
            "aud": "telegram-link",
            "exp": 1,  # 1970-01-01T00:00:01Z, long expired
        },
        settings.USER_SECRET.get_secret_value(),
        algorithm="HS256",
    )


async def test_link_creates_account_and_sets_link(bot_engine, bot_seed):
    from bot.model.user import UserORM
    from bot.tg.model.user import TGUserORM
    from bot.tg.service.account_link import AccountLinkService

    tgid = 111
    await bot_seed.tg_user(tgid)
    person_id = uuid4()

    result = await AccountLinkService(_uow(bot_engine)).link(
        tgid, _mint(person_id)
    )

    assert result.id == tgid
    assert result.user_id is not None

    accounts = await bot_seed.all(UserORM)
    assert len(accounts) == 1
    assert accounts[0].person_id == person_id

    tg_rows = await bot_seed.all(TGUserORM)
    assert tg_rows[0].user_id == accounts[0].id


async def test_relink_replaces_previous_tgid(bot_engine, bot_seed):
    from bot.model.user import UserORM
    from bot.tg.model.user import TGUserORM
    from bot.tg.service.account_link import AccountLinkService

    old_tgid, new_tgid = 222, 333
    await bot_seed.tg_user(old_tgid)
    await bot_seed.tg_user(new_tgid)
    person_id = uuid4()
    service = AccountLinkService(_uow(bot_engine))

    await service.link(old_tgid, _mint(person_id))
    await service.link(new_tgid, _mint(person_id))

    accounts = await bot_seed.all(UserORM)
    assert len(accounts) == 1  # same AEF identity, not duplicated

    tg_rows = {row.tgid: row.user_id for row in await bot_seed.all(TGUserORM)}
    assert tg_rows[new_tgid] == accounts[0].id
    assert tg_rows[old_tgid] is None  # old link cleared


async def test_unlink_clears_link(bot_engine, bot_seed):
    from bot.tg.model.user import TGUserORM
    from bot.tg.service.account_link import AccountLinkService

    tgid = 444
    await bot_seed.tg_user(tgid)
    service = AccountLinkService(_uow(bot_engine))
    await service.link(tgid, _mint(uuid4()))

    result = await service.unlink(tgid)

    assert result.user_id is None
    tg_rows = await bot_seed.all(TGUserORM)
    assert tg_rows[0].user_id is None


async def test_unlink_unknown_tgid_returns_none(bot_engine, bot_seed):
    from bot.tg.service.account_link import AccountLinkService

    result = await AccountLinkService(_uow(bot_engine)).unlink(999)

    assert result is None


async def test_link_rejects_wrong_audience(bot_engine, bot_seed):
    from bot.exc.user import InvalidLinkTokenException
    from bot.tg.service.account_link import AccountLinkService

    tgid = 555
    await bot_seed.tg_user(tgid)
    bad_token = _mint(uuid4(), aud="invite")

    with pytest.raises(InvalidLinkTokenException):
        await AccountLinkService(_uow(bot_engine)).link(tgid, bad_token)


async def test_link_rejects_expired_token(bot_engine, bot_seed):
    from bot.exc.user import LinkTokenExpiredException
    from bot.tg.service.account_link import AccountLinkService

    tgid = 666
    await bot_seed.tg_user(tgid)

    with pytest.raises(LinkTokenExpiredException):
        await AccountLinkService(_uow(bot_engine)).link(
            tgid, _expired(uuid4())
        )


async def test_link_rejects_garbage_token(bot_engine, bot_seed):
    from bot.exc.user import InvalidLinkTokenException
    from bot.tg.service.account_link import AccountLinkService

    tgid = 777
    await bot_seed.tg_user(tgid)

    with pytest.raises(InvalidLinkTokenException):
        await AccountLinkService(_uow(bot_engine)).link(tgid, "not-a-jwt")
