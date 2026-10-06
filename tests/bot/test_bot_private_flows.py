from typing import Any
from uuid import UUID, uuid4

import pytest
from aiogram.methods import EditMessageText, SetMyCommands
from sqlalchemy.ext.asyncio import AsyncEngine
from support.telegram import BOT_USERNAME

from bot.tg.model.user import TGUserORM
from bot.tg.utils.deeplink import StartKind, encode_start

ALICE = 501
LeadsOf = dict[str, list[tuple[UUID, str]]]


def buttons(markup: Any) -> list[tuple[str, str | None, str | None, str | None]]:
    return [
        (b.text, b.callback_data, b.url, b.style)
        for row in markup.inline_keyboard
        for b in row
    ]


def labels(markup: Any) -> list[str]:
    return [text for text, *_ in buttons(markup)]


def menu_commands(tg: Any, tgid: int) -> list[str]:
    calls = [
        call
        for call in tg.session.of(SetMyCommands)
        if getattr(call.scope, "chat_id", None) == tgid and call.language_code == "ru"
    ]
    return [command.command for command in calls[-1].commands] if calls else []


async def test_a_stranger_is_welcomed_and_offered_to_connect_an_account(
    tg: Any, bot_seed: Any
) -> None:
    await tg.send("/start", ALICE, user={"username": "alice"})

    assert "Добро пожаловать" in tg.texts[0]
    first = buttons(tg.last_markup())[0]
    assert first[1] == "LK" and first[3] == "primary"
    assert [row.id for row in await bot_seed.all(TGUserORM)] == [ALICE]
    assert menu_commands(tg, ALICE) == ["start", "link", "help", "language"]


async def test_the_missing_username_is_mentioned_once_and_after_the_answer(
    tg: Any,
) -> None:
    await tg.send("/start", ALICE, user={"username": None})
    await tg.send("/start", ALICE, user={"username": None})

    assert "Добро пожаловать" in tg.texts[0]
    assert "@username" in tg.texts[1]
    assert "Добро пожаловать" in tg.texts[2]
    assert len(tg.texts) == 3


async def test_the_missing_username_is_not_mentioned_in_a_group(tg: Any) -> None:
    await tg.send(
        "/help",
        ALICE,
        user={"username": None},
        chat_id=-100500,
        chat_type="supergroup",
    )

    assert all("@username" not in text for text in tg.texts)


async def test_the_connection_steps_link_to_the_website(tg: Any) -> None:
    await tg.send("/start", ALICE, user={"username": "alice"})

    await tg.press("LK", ALICE, user={"username": "alice"})

    edited = tg.session.of(EditMessageText)[-1]
    assert "Привязка аккаунта" in edited.text
    urls = [url for _, _, url, _ in buttons(edited.reply_markup) if url]
    assert any(url.endswith("/auth/login") for url in urls)
    assert any(url.endswith("/auth/register") for url in urls)
    assert any(url.endswith("/profile") for url in urls)


async def test_a_valid_link_code_connects_the_account_and_greets_by_role(
    tg: Any, bot_seed: Any, link_code: Any
) -> None:
    person = uuid4()
    club = uuid4()
    tg.lead(person, (club, "Chess <club>"))
    code = await link_code(person)

    await tg.send(f"/start {code}", ALICE, user={"username": "alice"})

    sent = tg.session.sent
    assert "привязан" in sent[0].text
    assert sent[0].message_effect_id is not None
    assert "Chess &lt;club&gt;" in sent[1].text
    assert "Вы руководите" in sent[1].text
    assert "Главное меню" in sent[2].text
    assert any(
        "Мои коллективы" in label for label in labels(sent[2].reply_markup)
    )
    assert menu_commands(tg, ALICE) == [
        "start",
        "account",
        "collectives",
        "help",
        "language",
    ]


async def test_a_celebration_effect_that_telegram_refuses_is_dropped(
    tg: Any, link_code: Any
) -> None:
    from aiogram.exceptions import TelegramBadRequest
    from aiogram.methods import SendMessage

    calls = {"count": 0}
    original = tg.session.make_request

    async def refuse_effect(  # noqa: ASYNC109
        bot: Any, method: Any, timeout: Any = None
    ) -> Any:
        if isinstance(method, SendMessage) and method.message_effect_id:
            calls["count"] += 1
            raise TelegramBadRequest(method, "Bad Request: effect not found")
        return await original(bot, method, timeout)

    tg.session.make_request = refuse_effect
    code = await link_code(uuid4())

    await tg.send(f"/start {code}", ALICE, user={"username": "alice"})

    assert calls["count"] == 1
    assert "привязан" in tg.texts[0]


async def test_an_expired_link_code_is_explained_and_the_menu_still_opens(
    tg: Any,
) -> None:
    await tg.send("/start nosuchcode", ALICE, user={"username": "alice"})

    assert "устарела" in tg.texts[0]
    assert "Добро пожаловать" in tg.texts[1]


async def test_a_linked_person_without_collectives_is_told_so(
    tg: Any, bot_seed: Any
) -> None:
    await bot_seed.linked_tg_user(ALICE, uuid4())

    await tg.send("/start", ALICE)

    assert "Вы пока не состоите ни в одном коллективе" in tg.texts[0]
    assert menu_commands(tg, ALICE) == ["start", "account", "help", "language"]


async def test_a_member_sees_their_collectives_and_no_leader_section(
    tg: Any, bot_seed: Any
) -> None:
    person = uuid4()
    await bot_seed.linked_tg_user(ALICE, person)
    tg.join(person, (uuid4(), "Choir"), (uuid4(), "Band"))

    await tg.send("/start", ALICE)

    assert "Участник: Band, Choir" in tg.texts[0]
    assert all("Мои коллективы" not in label for label in labels(tg.last_markup()))


async def test_collectives_the_person_cannot_load_are_not_reported_as_none(
    tg: Any, bot_seed: Any, monkeypatch: pytest.MonkeyPatch
) -> None:
    from bot.tg.utils.aef_client import AefClientError

    async def down(person_id: UUID) -> list[dict[str, Any]]:
        raise AefClientError("event is down")

    monkeypatch.setattr("bot.tg.service.actor.get_my_collectives", down)
    monkeypatch.setattr("bot.tg.service.actor.get_my_memberships", down)
    await bot_seed.linked_tg_user(ALICE, uuid4())

    await tg.send("/start", ALICE)

    assert "Не удалось загрузить ваши коллективы" in tg.texts[0]
    assert "ни в одном" not in tg.texts[0]


async def test_help_lists_the_commands_of_the_role(tg: Any, bot_seed: Any) -> None:
    await tg.send("/help", ALICE, user={"username": "a"})
    person = uuid4()
    await bot_seed.linked_tg_user(ALICE + 1, person)
    tg.lead(person, (uuid4(), "Club"))
    await tg.send("/help", ALICE + 1)

    assert "/link" in tg.texts[0] and "/collectives" not in tg.texts[0]
    assert "/collectives" in tg.texts[1] and "/link" not in tg.texts[1]
    assert "/setup_chat" in tg.texts[0]


async def test_the_account_screen_shows_notifications_and_toggles_them(
    tg: Any, bot_seed: Any, monkeypatch: pytest.MonkeyPatch
) -> None:
    person = uuid4()
    await bot_seed.linked_tg_user(ALICE, person)

    async def set_state(person_id: UUID, enabled: bool) -> None:
        tg.notifications = enabled

    async def get_state(person_id: UUID) -> bool:
        return tg.notifications

    monkeypatch.setattr(
        "bot.tg.api.router.callback.account.get_telegram_notifications_enabled",
        get_state,
    )
    monkeypatch.setattr(
        "bot.tg.api.router.callback.account.set_telegram_notifications_enabled",
        set_state,
    )
    await tg.send("/account", ALICE)
    assert "Уведомления в Telegram включены" in tg.texts[0]

    await tg.press("AC/n", ALICE)

    edited = tg.session.of(EditMessageText)[-1]
    assert "Уведомления в Telegram выключены" in edited.text
    assert tg.notifications is False


async def test_unlinking_returns_the_chat_to_the_stranger_menu(
    tg: Any, bot_seed: Any, monkeypatch: pytest.MonkeyPatch
) -> None:
    async def nothing(*args: Any, **kwargs: Any) -> None:
        return None

    monkeypatch.setattr("bot.tg.service.account_link.deregister_notify_client", nothing)
    monkeypatch.setattr("bot.tg.service.account_link.deregister_oauth_link", nothing)
    await bot_seed.linked_tg_user(ALICE, uuid4())
    await tg.send("/account", ALICE)

    await tg.press("AC/u/yes", ALICE)

    edited = tg.session.of(EditMessageText)[-1]
    assert "ещё не привязан" in edited.text
    assert menu_commands(tg, ALICE) == ["start", "link", "help", "language"]


async def test_collectives_command_for_a_stranger_shows_how_to_connect(
    tg: Any,
) -> None:
    await tg.send("/collectives", ALICE, user={"username": "a"})

    assert "Привязка аккаунта" in tg.texts[0]


async def test_collectives_command_for_a_non_leader_says_who_it_is_for(
    tg: Any, bot_seed: Any
) -> None:
    await bot_seed.linked_tg_user(ALICE, uuid4())

    await tg.send("/collectives", ALICE)

    assert "для руководителей" in tg.texts[0]


async def test_a_leader_sees_which_collectives_have_a_chat(
    tg: Any, bot_seed: Any
) -> None:
    person = uuid4()
    await bot_seed.linked_tg_user(ALICE, person)
    chess, choir = uuid4(), uuid4()
    tg.lead(person, (chess, "Chess"), (choir, "Choir"))

    await tg.send("/collectives", ALICE)

    assert labels(tg.last_markup()) == ["➕ Chess", "➕ Choir"]


async def test_the_collective_card_offers_to_connect_a_group_with_the_right_link(
    tg: Any, bot_seed: Any
) -> None:
    person, club = uuid4(), uuid4()
    await bot_seed.linked_tg_user(ALICE, person)
    tg.lead(person, (club, "Chess"))
    await tg.send("/collectives", ALICE)
    pick = buttons(tg.last_markup())[0][1]

    await tg.press(pick or "", ALICE)

    edited = tg.session.of(EditMessageText)[-1]
    assert "Чат не привязан" in edited.text
    rows = buttons(edited.reply_markup)
    bind = next(row for row in rows if row[2])
    assert bind[2] == (
        f"https://t.me/{BOT_USERNAME}?startgroup="
        f"{encode_start(StartKind.bind, club)}&admin=pin_messages"
    )
    assert all("Анонсы" not in text for text, *_ in rows)


async def test_a_leader_tunes_the_announcements_of_a_bound_chat(
    tg: Any, bot_seed: Any, bot_engine: AsyncEngine
) -> None:
    person, club = uuid4(), uuid4()
    await bot_seed.linked_tg_user(ALICE, person)
    tg.lead(person, (club, "Chess"))
    tg.session.admins[-1001] = {ALICE, 123456}
    tg.session.titles[-1001] = "Chess chat"
    await tg.send("/setup_chat", ALICE, chat_id=-1001, chat_type="supergroup")
    await tg.send("/collectives", ALICE)
    await tg.press(buttons(tg.last_markup())[0][1] or "", ALICE)
    card = tg.session.of(EditMessageText)[-1]
    assert "Чат: Chess chat" in card.text
    assert "Без звука: выкл" in card.text
    silent = next(b for b in buttons(card.reply_markup) if "Без звука" in b[0])

    await tg.press(silent[1] or "", ALICE)

    card = tg.session.of(EditMessageText)[-1]
    assert "Без звука: вкл" in card.text
    language = next(b for b in buttons(card.reply_markup) if "Язык" in b[0])
    await tg.press(language[1] or "", ALICE)
    card = tg.session.of(EditMessageText)[-1]
    assert "Язык: English" in card.text


async def test_unbinding_from_the_card_frees_the_chat_and_tells_it(
    tg: Any, bot_seed: Any
) -> None:
    person, club = uuid4(), uuid4()
    await bot_seed.linked_tg_user(ALICE, person)
    tg.lead(person, (club, "Chess"))
    tg.session.admins[-1001] = {ALICE, 123456}
    await tg.send("/setup_chat", ALICE, chat_id=-1001, chat_type="supergroup")
    await tg.send("/collectives", ALICE)
    await tg.press(buttons(tg.last_markup())[0][1] or "", ALICE)
    card = tg.session.of(EditMessageText)[-1]
    unbind = next(b for b in buttons(card.reply_markup) if "Отвязать" in b[0])

    await tg.press(unbind[1] or "", ALICE)

    assert labels(tg.session.of(EditMessageText)[-1].reply_markup) == [
        "➕ Chess",
        "◀️ Назад",
    ]
    assert "больше не является официальным" in tg.texts[-1]
    assert tg.session.sent[-1].chat_id == -1001


async def test_someone_elses_collective_card_is_refused(
    tg: Any, bot_seed: Any
) -> None:
    from bot.tg.enum.callbacks import LeaderAction, LeaderCB

    person = uuid4()
    await bot_seed.linked_tg_user(ALICE, person)
    tg.lead(person, (uuid4(), "Mine"))
    stranger_card = LeaderCB(action=LeaderAction.card, collective_id=uuid4()).pack()

    await tg.press(stranger_card, ALICE)

    edited = tg.session.of(EditMessageText)[-1]
    assert "Мои коллективы" in edited.text


async def test_text_the_bot_does_not_understand_gets_a_hint_and_the_menu(
    tg: Any,
) -> None:
    await tg.send("what is this", ALICE, user={"username": "alice"})

    assert "Не понял" in tg.texts[0]
    assert buttons(tg.last_markup())


async def test_ordinary_group_chatter_is_ignored(tg: Any) -> None:
    await tg.send("hello all", ALICE, chat_id=-100500, chat_type="supergroup")

    assert tg.texts == []


async def test_the_language_command_opens_the_language_menu(tg: Any) -> None:
    await tg.send("/language", ALICE, user={"username": "alice"})

    assert "Выберите язык" in tg.texts[0]


async def test_an_unexpected_failure_shows_a_code_but_not_the_internals(
    tg: Any, monkeypatch: pytest.MonkeyPatch
) -> None:
    async def broken(self: Any, actor: Any) -> Any:
        raise RuntimeError("secret internal detail")

    monkeypatch.setattr("bot.tg.usecase.menu.MenuUseCase.on_help", broken)

    await tg.send("/help", ALICE, user={"username": "alice"})

    assert "Что-то пошло не так" in tg.texts[0]
    assert "secret internal detail" not in tg.texts[0]
    assert "<code>" in tg.texts[0]
    assert len(tg.errors) == 1
    tg.errors.clear()


async def test_services_that_time_out_degrade_instead_of_failing(
    tg: Any, bot_seed: Any, monkeypatch: pytest.MonkeyPatch
) -> None:
    async def silent(person_id: UUID) -> list[dict[str, Any]]:
        raise TimeoutError("no answer in 5 s")

    async def silent_state(person_id: UUID) -> bool:
        raise TimeoutError("no answer in 5 s")

    monkeypatch.setattr("bot.tg.service.actor.get_my_collectives", silent)
    monkeypatch.setattr("bot.tg.service.actor.get_my_memberships", silent)
    monkeypatch.setattr(
        "bot.tg.utils.notifications.get_telegram_notifications_enabled",
        silent_state,
    )
    await bot_seed.linked_tg_user(ALICE, uuid4())

    await tg.send("/account", ALICE)

    assert "Не удалось загрузить ваши коллективы" in tg.texts[0]
    assert "Уведомления в Telegram" not in tg.texts[0]


async def test_the_group_command_in_private_points_to_a_group(tg: Any) -> None:
    await tg.send("/setup_chat", ALICE)

    assert "работает в групповых чатах" in tg.texts[0]
    assert "Не понял" not in tg.texts[0]
