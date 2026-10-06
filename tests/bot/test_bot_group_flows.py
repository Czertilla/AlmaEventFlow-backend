from typing import Any
from uuid import UUID, uuid4

import pytest
from aiogram.exceptions import TelegramBadRequest
from aiogram.methods import AnswerCallbackQuery, EditMessageText, SendMessage
from support.telegram import BOT_ID, BOT_USERNAME, message_update

from bot.tg.model.collective_chat import CollectiveChatORM
from bot.tg.model.message import TelegramMessageORM
from bot.tg.model.user import TGUserORM
from bot.tg.utils.deeplink import StartKind, encode_start

GROUP = -1001000000777
LEADER, OTHER_LEADER, STRANGER, MEMBER = 601, 602, 603, 604
CLUB, RIVAL = uuid4(), uuid4()


def buttons(markup: Any) -> list[tuple[str, str | None, str | None]]:
    return [
        (b.text, b.callback_data, b.url)
        for row in markup.inline_keyboard
        for b in row
    ]


async def group(
    tg: Any, text: str, tgid: int, *, chat_id: int = GROUP, **kwargs: Any
) -> None:
    await tg.send(text, tgid, chat_id=chat_id, chat_type="supergroup", **kwargs)


@pytest.fixture
async def people(tg: Any, bot_seed: Any) -> dict[str, UUID]:
    leader, other, member = uuid4(), uuid4(), uuid4()
    await bot_seed.linked_tg_user(LEADER, leader)
    await bot_seed.linked_tg_user(OTHER_LEADER, other)
    await bot_seed.linked_tg_user(MEMBER, member)
    await bot_seed.tg_user(STRANGER)
    tg.lead(leader, (CLUB, "Chess <Club>"))
    tg.lead(other, (RIVAL, "Rival"))
    tg.join(member, (CLUB, "Chess <Club>"))
    tg.session.admins[GROUP] = {BOT_ID, LEADER, OTHER_LEADER, MEMBER, STRANGER}
    return {"leader": leader, "other": other, "member": member}


def ephemeral_to(call: SendMessage) -> int | None:
    params = call.ephemeral_message_parameters
    return params.receiver_user_id if params else None


async def test_a_stranger_trying_to_bind_a_chat_is_sent_to_connect_an_account(
    tg: Any, people: Any
) -> None:
    await group(tg, "/setup_chat", STRANGER)

    reply = tg.session.sent[-1]
    assert "привяжите Telegram" in reply.text
    assert ephemeral_to(reply) == STRANGER
    assert buttons(reply.reply_markup) == [
        ("🤖 Открыть бота", None, f"https://t.me/{BOT_USERNAME}?start=onboard")
    ]


async def test_a_private_reply_falls_back_to_an_ordinary_one(
    tg: Any, people: Any
) -> None:
    original = tg.session.make_request

    async def no_ephemeral(  # noqa: ASYNC109
        bot: Any, method: Any, timeout: Any = None
    ) -> Any:
        if isinstance(method, SendMessage) and method.ephemeral_message_parameters:
            raise TelegramBadRequest(method, "Bad Request: ephemeral not supported")
        return await original(bot, method, timeout)

    tg.session.make_request = no_ephemeral

    await group(tg, "/setup_chat", STRANGER)

    reply = tg.session.sent[-1]
    assert ephemeral_to(reply) is None
    assert reply.reply_parameters is not None
    assert "привяжите Telegram" in reply.text


async def test_a_linked_person_who_leads_nothing_cannot_bind_a_chat(
    tg: Any, people: Any
) -> None:
    await group(tg, "/setup_chat", MEMBER)

    assert "не руководите ни одним коллективом" in tg.last_text
    assert ephemeral_to(tg.session.sent[-1]) == MEMBER


async def test_a_leader_who_is_not_a_chat_admin_cannot_bind_it(
    tg: Any, people: Any
) -> None:
    tg.session.admins[GROUP] = {BOT_ID}

    await group(tg, "/setup_chat", LEADER)

    assert "Привязать этот чат могут только его администраторы" in tg.last_text


async def test_the_bot_must_be_an_admin_before_a_chat_is_bound(
    tg: Any, people: Any
) -> None:
    tg.session.admins[GROUP] = {LEADER}

    await group(tg, "/setup_chat", LEADER)

    assert "выдайте боту права администратора" in tg.last_text


async def test_a_leader_binds_the_chat_and_is_pointed_to_the_settings(
    tg: Any, people: Any, bot_seed: Any
) -> None:
    await group(tg, "/setup_chat", LEADER)

    reply = tg.session.sent[-1]
    assert "Готово" in reply.text and "Chess &lt;Club&gt;" in reply.text
    assert reply.ephemeral_message_parameters is None
    settings_link = buttons(reply.reply_markup)[0][2]
    assert settings_link == (
        f"https://t.me/{BOT_USERNAME}?start={encode_start(StartKind.lead, CLUB)}"
    )
    rows = await bot_seed.all(CollectiveChatORM)
    assert [(r.collective_id, r.chat_id, r.thread_id) for r in rows] == [
        (CLUB, GROUP, None)
    ]


async def test_binding_inside_a_forum_topic_remembers_the_topic(
    tg: Any, people: Any, bot_seed: Any
) -> None:
    await group(tg, "/setup_chat", LEADER, thread_id=42)

    assert "Эта тема теперь" in tg.last_text
    rows = await bot_seed.all(CollectiveChatORM)
    assert rows[0].thread_id == 42


async def test_a_chat_cannot_belong_to_two_collectives(
    tg: Any, people: Any, bot_seed: Any
) -> None:
    await group(tg, "/setup_chat", LEADER)

    await group(tg, "/setup_chat", OTHER_LEADER)

    assert "уже является официальным чатом другого коллектива" in tg.last_text
    assert ephemeral_to(tg.session.sent[-1]) == OTHER_LEADER
    rows = await bot_seed.all(CollectiveChatORM)
    assert [r.collective_id for r in rows] == [CLUB]


async def test_repeating_the_command_reports_that_nothing_changed(
    tg: Any, people: Any
) -> None:
    await group(tg, "/setup_chat", LEADER)
    await group(tg, "/setup_chat", LEADER)

    assert "Уже настроено" in tg.last_text


async def test_a_leader_of_several_collectives_picks_one_from_buttons(
    tg: Any, people: Any, bot_seed: Any
) -> None:
    second = uuid4()
    tg.lead(people["leader"], (CLUB, "Chess"), (second, "Choir"))

    await group(tg, "/setup_chat", LEADER)

    reply = tg.session.sent[-1]
    assert "несколькими коллективами" in reply.text
    pick = buttons(reply.reply_markup)
    assert [text for text, *_ in pick] == ["Chess", "Choir"]

    await tg.press(pick[1][1] or "", LEADER, chat_id=GROUP, chat_type="supergroup")

    edited = tg.session.of(EditMessageText)[-1]
    assert "Готово" in edited.text and "Choir" in edited.text
    rows = await bot_seed.all(CollectiveChatORM)
    assert [r.collective_id for r in rows] == [second]


async def test_someone_elses_tap_on_the_picker_is_refused(
    tg: Any, people: Any, bot_seed: Any
) -> None:
    tg.lead(people["leader"], (CLUB, "Chess"), (uuid4(), "Choir"))
    await group(tg, "/setup_chat", LEADER)
    pick = buttons(tg.last_markup())[0][1] or ""

    await tg.press(pick, MEMBER, chat_id=GROUP, chat_type="supergroup")

    answer = tg.session.of(AnswerCallbackQuery)[-1]
    assert "не руководите" in (answer.text or "")
    assert answer.show_alert is True
    assert await bot_seed.all(CollectiveChatORM) == []


async def test_a_leader_of_both_collectives_confirms_replacing_the_binding(
    tg: Any, people: Any, bot_seed: Any
) -> None:
    second = uuid4()
    tg.lead(people["leader"], (CLUB, "Chess"), (second, "Choir"))
    await group(tg, f"/setup_chat {CLUB}", LEADER)

    await group(tg, f"/setup_chat {second}", LEADER)

    reply = tg.session.sent[-1]
    assert "Заменить на «Choir»" in reply.text
    replace = next(b for b in buttons(reply.reply_markup) if "Заменить" in b[0])

    await tg.press(replace[1] or "", LEADER, chat_id=GROUP, chat_type="supergroup")

    rows = await bot_seed.all(CollectiveChatORM)
    assert [r.collective_id for r in rows] == [second]


async def test_a_malformed_collective_id_is_reported(tg: Any, people: Any) -> None:
    await group(tg, "/setup_chat not-a-uuid", LEADER)

    assert "Некорректный collective_id" in tg.last_text


async def test_status_tells_who_the_chat_belongs_to(tg: Any, people: Any) -> None:
    await group(tg, "/setup_chat status", LEADER)
    assert "не привязан ни один коллектив" in tg.last_text

    await group(tg, "/setup_chat", LEADER)
    await group(tg, "/setup_chat status", LEADER)
    assert "Chess &lt;Club&gt;" in tg.last_text

    await group(tg, "/setup_chat status", OTHER_LEADER)
    assert "одного из коллективов" in tg.last_text


async def test_only_the_leader_can_unbind_the_chat(
    tg: Any, people: Any, bot_seed: Any
) -> None:
    await group(tg, "/setup_chat", LEADER)

    await group(tg, "/setup_chat off", OTHER_LEADER)
    assert "не был привязан к коллективу, которым вы руководите" in tg.last_text
    assert len(await bot_seed.all(CollectiveChatORM)) == 1

    await group(tg, "/setup_chat off", LEADER)
    assert "больше не привязан" in tg.last_text
    assert await bot_seed.all(CollectiveChatORM) == []


async def test_an_anonymous_admin_is_asked_to_show_themselves(
    tg: Any, people: Any
) -> None:
    anonymous = {
        "id": 1087968824,
        "is_bot": True,
        "first_name": "Group",
        "username": "GroupAnonymousBot",
    }
    update = message_update(
        tg.bot,
        "/setup_chat",
        user=anonymous,
        chat_id=GROUP,
        chat_type="supergroup",
        extra={"sender_chat": {"id": GROUP, "type": "supergroup"}},
    )

    await tg.deliver(update)

    assert "анонимный администратор" in tg.last_text


async def test_the_startgroup_link_binds_the_group_the_bot_was_added_to(
    tg: Any, people: Any, bot_seed: Any
) -> None:
    await group(tg, f"/start {encode_start(StartKind.bind, CLUB)}", LEADER)

    assert "Готово" in tg.last_text
    rows = await bot_seed.all(CollectiveChatORM)
    assert [r.collective_id for r in rows] == [CLUB]


async def test_a_plain_start_in_a_group_is_ignored(tg: Any, people: Any) -> None:
    await group(tg, "/start", LEADER)

    assert tg.texts == []


async def test_the_bot_greets_a_group_it_was_added_to_as_a_member(
    tg: Any, people: Any
) -> None:
    update = tg.member_change(
        chat_id=GROUP,
        chat_type="supergroup",
        actor={"id": LEADER, "is_bot": False, "first_name": "L", "language_code": "ru"},
        old="left",
        new="member",
    )

    await tg.deliver(update)

    assert "Я бот AlmaEventFlow" in tg.last_text
    assert "/setup_chat" in tg.last_text


async def test_the_bot_thanks_for_the_admin_rights(tg: Any, people: Any) -> None:
    update = tg.member_change(
        chat_id=GROUP,
        chat_type="supergroup",
        actor={"id": LEADER, "is_bot": False, "first_name": "L", "language_code": "ru"},
        old="member",
        new="administrator",
    )

    await tg.deliver(update)

    assert "Теперь руководитель коллектива может отправить /setup_chat" in tg.last_text


async def test_losing_admin_rights_in_a_bound_chat_is_announced(
    tg: Any, people: Any
) -> None:
    await group(tg, "/setup_chat", LEADER)
    before = len(tg.texts)
    update = tg.member_change(
        chat_id=GROUP,
        chat_type="supergroup",
        actor={"id": LEADER, "is_bot": False, "first_name": "L", "language_code": "ru"},
        old="administrator",
        new="member",
    )

    await tg.deliver(update)

    assert len(tg.texts) == before + 1
    assert "больше не администратор" in tg.last_text


async def test_losing_admin_rights_in_an_unbound_chat_is_silent(
    tg: Any, people: Any
) -> None:
    update = tg.member_change(
        chat_id=GROUP,
        chat_type="supergroup",
        actor={"id": LEADER, "is_bot": False, "first_name": "L", "language_code": "ru"},
        old="administrator",
        new="member",
    )

    await tg.deliver(update)

    assert tg.texts == []


async def test_removing_the_bot_frees_the_chat_and_tells_the_leader(
    tg: Any, people: Any, bot_seed: Any
) -> None:
    await group(tg, "/setup_chat", LEADER)
    update = tg.member_change(
        chat_id=GROUP,
        chat_type="supergroup",
        actor={"id": STRANGER, "is_bot": False, "first_name": "S"},
        old="administrator",
        new="kicked",
    )

    await tg.deliver(update)

    assert await bot_seed.all(CollectiveChatORM) == []
    notice = tg.session.sent[-1]
    assert notice.chat_id == LEADER
    assert "отвязан от коллектива «Chess &lt;Club&gt;»" in notice.text


async def test_a_user_who_blocks_the_bot_is_marked_inactive_until_they_return(
    tg: Any, people: Any, bot_seed: Any
) -> None:
    def private(old: str, new: str) -> Any:
        return tg.member_change(
            chat_id=LEADER,
            chat_type="private",
            actor={"id": LEADER, "is_bot": False, "first_name": "L"},
            old=old,
            new=new,
        )

    await tg.deliver(private("member", "kicked"))
    rows = await bot_seed.all(TGUserORM)
    assert not next(r for r in rows if r.id == LEADER).is_active

    await tg.deliver(private("kicked", "member"))
    assert next(r for r in await bot_seed.all(TGUserORM) if r.id == LEADER).is_active


async def test_an_upgraded_group_keeps_its_binding_and_message_history(
    tg: Any, people: Any, bot_seed: Any
) -> None:
    from bot.tg.uow.message import TelegramMessageUOW

    await group(tg, "/setup_chat", LEADER)
    async with TelegramMessageUOW() as uow:
        await uow.messages.upsert("event-1", GROUP, 55)
        await uow.commit(True)
    supergroup = -1009999999999

    await tg.send(
        "",
        LEADER,
        chat_id=GROUP,
        chat_type="group",
        extra={"migrate_to_chat_id": supergroup},
    )

    assert [r.chat_id for r in await bot_seed.all(CollectiveChatORM)] == [supergroup]
    assert [r.chat_id for r in await bot_seed.all(TelegramMessageORM)] == [supergroup]


@pytest.fixture
def attendance(monkeypatch: pytest.MonkeyPatch) -> dict[str, Any]:
    state: dict[str, Any] = {"rows": [], "patched": []}
    event_member, event_attendance = str(uuid4()), str(uuid4())

    async def fetch(person_id: UUID, event_id: UUID) -> list[dict[str, Any]]:
        return state["rows"] and [{"member_id": event_member, "id": event_attendance}]

    async def patch(
        person_id: UUID, member_id: UUID, attendance_id: UUID, *, is_attended: bool
    ) -> dict[str, Any]:
        state["patched"].append((member_id, attendance_id, is_attended))
        return {}

    module = "bot.tg.api.router.callback.attendance"
    monkeypatch.setattr(f"{module}.get_my_attendance", fetch)
    monkeypatch.setattr(f"{module}.patch_my_attendance", patch)
    state["ids"] = (event_member, event_attendance)
    return state


async def test_an_unlinked_person_tapping_going_is_taken_to_the_bot(
    tg: Any, people: Any, attendance: Any
) -> None:
    event = uuid4()

    await tg.press(
        f"att:{event.hex}:yes", STRANGER, chat_id=GROUP, chat_type="supergroup"
    )

    answer = tg.session.of(AnswerCallbackQuery)[-1]
    assert answer.url == f"https://t.me/{BOT_USERNAME}?start=onboard"
    assert "Сначала привяжите Telegram" in (answer.text or "")


async def test_someone_who_is_not_in_the_event_is_told_so(
    tg: Any, people: Any, attendance: Any
) -> None:
    await tg.press(
        f"att:{uuid4().hex}:yes", MEMBER, chat_id=GROUP, chat_type="supergroup"
    )

    answer = tg.session.of(AnswerCallbackQuery)[-1]
    assert "не участвуете" in (answer.text or "")
    assert attendance["patched"] == []


async def test_a_participant_marks_attendance_in_both_callback_formats(
    tg: Any, people: Any, attendance: Any
) -> None:
    attendance["rows"] = [1]
    event = uuid4()

    where = {"chat_id": GROUP, "chat_type": "supergroup"}
    await tg.press(f"att:{event.hex}:yes", MEMBER, **where)
    await tg.press(f"att:{event}:no", MEMBER, **where)

    member_id, attendance_id = attendance["ids"]
    assert attendance["patched"] == [
        (UUID(member_id), UUID(attendance_id), True),
        (UUID(member_id), UUID(attendance_id), False),
    ]
    texts = [a.text for a in tg.session.of(AnswerCallbackQuery)]
    assert texts == ["Отмечено: буду ✅", "Отмечено: не буду ❌"]
