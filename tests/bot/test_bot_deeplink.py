from uuid import UUID, uuid4

import pytest
from support.telegram import BOT_USERNAME, make_bot

from bot.tg.utils.deeplink import (
    GROUP_RIGHTS,
    StartKind,
    StartPayload,
    encode_start,
    parse_start,
    start_url,
    startgroup_url,
)

TELEGRAM_PAYLOAD_LIMIT = 64


def test_payloads_round_trip_and_fit_telegram_limits() -> None:
    collective = uuid4()

    for kind in (StartKind.bind, StartKind.lead):
        payload = encode_start(kind, collective)

        assert len(payload) <= TELEGRAM_PAYLOAD_LIMIT
        assert all(char.isalnum() or char in "_-" for char in payload)
        assert parse_start(payload) == StartPayload(kind, collective)
    assert parse_start(encode_start(StartKind.onboard)) == StartPayload(
        StartKind.onboard
    )


@pytest.mark.parametrize(
    "arg",
    [
        None,
        "",
        "0123456789abcdef",
        "bind_",
        "bind_xyz",
        "lead_" + "g" * 32,
        "bind_" + "a" * 31,
    ],
)
def test_anything_else_is_left_for_the_link_code_flow(arg: str | None) -> None:
    assert parse_start(arg) is None


def test_a_link_code_that_looks_like_a_payload_is_still_a_link_code() -> None:
    assert parse_start("bind_" + "z" * 32) is None
    assert parse_start("onboarding") is None


def test_a_collective_is_needed_for_bind_and_lead() -> None:
    with pytest.raises(ValueError):
        encode_start(StartKind.bind)


async def test_links_use_the_bot_username_and_request_admin_rights(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from core.config.settings import settings

    monkeypatch.setattr(settings, "BOT_TG_USERNAME", BOT_USERNAME)
    bot, _ = make_bot()
    collective = UUID(int=7)

    assert await start_url(bot) == f"https://t.me/{BOT_USERNAME}?start=onboard"
    assert await startgroup_url(bot, encode_start(StartKind.bind, collective)) == (
        f"https://t.me/{BOT_USERNAME}?startgroup=bind_{collective.hex}"
        f"&admin={'+'.join(GROUP_RIGHTS)}"
    )
    assert "&admin=" not in await startgroup_url(bot, "x", rights=())


async def test_the_username_is_asked_from_telegram_when_not_configured(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from core.config.settings import settings

    monkeypatch.setattr(settings, "BOT_TG_USERNAME", None)
    monkeypatch.setattr("bot.tg.utils.deeplink._usernames", {})
    bot, session = make_bot()

    assert await start_url(bot) == f"https://t.me/{BOT_USERNAME}?start=onboard"
    assert await start_url(bot) == f"https://t.me/{BOT_USERNAME}?start=onboard"
    assert len(session.calls) == 1
