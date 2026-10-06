from datetime import UTC, date, datetime
from typing import Any
from uuid import UUID, uuid4

import pytest
from aiocache import SimpleMemoryCache  # pyright: ignore[reportMissingTypeStubs]
from aiogram.exceptions import TelegramBadRequest
from aiogram.methods import EditMessageText, SendMessage

from bot.tg.service.announcement import (
    build_update_notice,
    describe_changes,
    request_from_payload,
)
from bot.tg.text.localization import i18n_manager
from core.schema.message.announcement import AnnouncementRequest, AnnouncementStage

COLLECTIVE, EVENT, CHAT = uuid4(), uuid4(), -1001000000555


@pytest.fixture
def memory_cache(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(i18n_manager, "cache", SimpleMemoryCache())


def _stage(name: str, hour: int, **extra: Any) -> AnnouncementStage:
    return AnnouncementStage(
        name=name, start_at=datetime(2026, 5, 1, hour, tzinfo=UTC), **extra
    )


def _request(**changes: Any) -> AnnouncementRequest:
    fields: dict[str, Any] = {
        "collective_id": COLLECTIVE,
        "event_id": EVENT,
        "event_name": "Concert",
        "event_date": date(2026, 5, 1),
        "event_description": "Bring a friend",
        "location": "Main hall",
        "organizer": "Choir",
        "stages": [_stage("Doors", 9)],
        "action_url": "https://example.test/event/1",
    }
    return AnnouncementRequest(**(fields | changes))


@pytest.mark.usefixtures("memory_cache")
class TestChanges:
    async def test_a_new_name_shows_the_old_one_struck_out(self) -> None:
        lines = await describe_changes(_request(), _request(event_name="Gala"), "en")

        assert lines == ["▪️ Name: <s>Concert</s> → <b>Gala</b>"]

    async def test_a_new_date_is_written_out(self) -> None:
        lines = await describe_changes(
            _request(), _request(event_date=date(2026, 5, 2)), "en"
        )

        assert lines == ["▪️ Date: <s>1 May 2026</s> → <b>2 May 2026</b>"]

    async def test_a_place_that_appears_or_goes_is_marked_with_a_dash(self) -> None:
        added = await describe_changes(
            _request(location=None), _request(location="Hall 2"), "en"
        )
        removed = await describe_changes(
            _request(), _request(location=None), "en"
        )

        assert added == ["▪️ Place: <s>—</s> → <b>Hall 2</b>"]
        assert removed == ["▪️ Place: <s>Main hall</s> → <b>—</b>"]

    async def test_a_new_organizer_is_reported(self) -> None:
        lines = await describe_changes(
            _request(), _request(organizer="Band"), "en"
        )

        assert lines == ["▪️ Organizer: <s>Choir</s> → <b>Band</b>"]

    async def test_a_new_description_is_reported_without_repeating_it(self) -> None:
        lines = await describe_changes(
            _request(), _request(event_description="Secret programme"), "en"
        )

        assert lines == ["▪️ The description changed"]

    async def test_a_moved_stage_shows_both_times_in_the_readers_zone(self) -> None:
        lines = await describe_changes(
            _request(), _request(stages=[_stage("Doors", 10)]), "en"
        )

        (line,) = lines
        before = int(datetime(2026, 5, 1, 9, tzinfo=UTC).timestamp())
        after = int(datetime(2026, 5, 1, 10, tzinfo=UTC).timestamp())
        assert line.startswith("🕒 Doors: ")
        assert f'<tg-time unix="{before}" format="dt">' in line
        assert f'<tg-time unix="{after}" format="dt">' in line

    async def test_stages_that_come_and_go_are_listed(self) -> None:
        lines = await describe_changes(
            _request(stages=[_stage("Doors", 9), _stage("Quiz", 11)]),
            _request(stages=[_stage("Doors", 9), _stage("Concert", 12)]),
            "en",
        )

        assert any(line.startswith("➕ Concert, ") for line in lines)
        assert "➖ <s>Quiz</s>" in lines
        assert len(lines) == 2

    async def test_a_stage_whose_text_changed_is_reported(self) -> None:
        lines = await describe_changes(
            _request(stages=[_stage("Doors", 9, description="Old")]),
            _request(stages=[_stage("Doors", 9, description="New")]),
            "en",
        )

        assert lines == ["✏️ Doors: the description changed"]

    async def test_user_text_is_escaped(self) -> None:
        lines = await describe_changes(
            _request(), _request(event_name="<b>Gala</b> & co"), "en"
        )

        assert lines == [
            "▪️ Name: <s>Concert</s> → <b>&lt;b&gt;Gala&lt;/b&gt; &amp; co</b>"
        ]

    async def test_identical_versions_have_nothing_to_report(self) -> None:
        assert await describe_changes(_request(), _request(), "en") == []


@pytest.mark.usefixtures("memory_cache")
class TestNotice:
    async def test_it_names_the_event_lists_changes_and_asks_for_a_recheck(
        self,
    ) -> None:
        notice = await build_update_notice(
            _request(),
            _request(event_name="Gala", location="Hall 2"),
            "en",
            detailed=True,
        )

        title, *rest = notice.split("\n")
        assert title == "🔄 <b>Gala</b> was updated"
        assert rest[:2] == [
            "▪️ Name: <s>Concert</s> → <b>Gala</b>",
            "▪️ Place: <s>Main hall</s> → <b>Hall 2</b>",
        ]
        assert notice.endswith("Check that your mark is still right 👇")

    async def test_an_unknown_earlier_version_still_gets_a_notice(self) -> None:
        notice = await build_update_notice(
            None, _request(event_name="Gala"), "en", detailed=True
        )

        assert notice.split("\n") == [
            "🔄 <b>Gala</b> was updated",
            "",
            "Check that your mark is still right 👇",
        ]

    async def test_a_long_list_of_changes_is_cut_short(self) -> None:
        old = _request(stages=[_stage(f"Old {n}", 9) for n in range(12)])
        new = _request(stages=[_stage(f"New {n}", 9) for n in range(12)])

        notice = await build_update_notice(old, new, "en", detailed=True)

        assert "…and 16 more" in notice
        assert len(notice) < 1500

    async def test_it_speaks_the_language_of_the_chat(self) -> None:
        notice = await build_update_notice(
            _request(), _request(event_name="Gala"), "ru", detailed=True
        )

        assert "мероприятие обновлено" in notice
        assert "Название: <s>Concert</s> → <b>Gala</b>" in notice

    async def test_the_brief_notice_only_says_the_event_was_updated(self) -> None:
        old, new = _request(), _request(event_name="Gala", location="Hall 2")

        assert await build_update_notice(old, new, "en", detailed=False) == (
            "🔄 Updated"
        )
        assert await build_update_notice(old, new, "ru", detailed=False) == (
            "🔄 Обновлено"
        )


def test_a_stored_snapshot_that_no_longer_fits_the_schema_is_ignored() -> None:
    assert request_from_payload(None) is None
    assert request_from_payload({"event_name": 5}) is None
    assert request_from_payload({}) is None
    restored = request_from_payload(_request().model_dump(mode="json"))
    assert restored == _request()


async def _announce(module: Any, request: AnnouncementRequest) -> None:
    from bot.tg.uow.collective_chat import CollectiveChatUOW
    from bot.tg.uow.message import TelegramMessageUOW

    await module.deliver_announcement(
        request, TelegramMessageUOW(), CollectiveChatUOW()
    )


@pytest.fixture
async def announced(tg: Any, monkeypatch: pytest.MonkeyPatch) -> Any:
    import bot.api.kafka.sub.announcement as module
    from bot.tg.uow.collective_chat import CollectiveChatUOW

    async with CollectiveChatUOW() as uow:
        await uow.collective_chats.upsert(COLLECTIVE, CHAT, 1)
        await uow.commit(True)
    monkeypatch.setattr(module, "tg_bot", tg.bot)

    async def send(request: AnnouncementRequest) -> None:
        await _announce(module, request)

    return send


async def _configure(**settings: Any) -> None:
    from bot.tg.uow.collective_chat import CollectiveChatUOW

    async with CollectiveChatUOW() as uow:
        await uow.collective_chats.update_settings(COLLECTIVE, settings)
        await uow.commit(True)


@pytest.fixture
async def detailed(announced: Any) -> None:
    await _configure(detailed_updates=True)


async def test_by_default_an_edit_is_followed_by_a_one_line_reply(
    tg: Any, announced: Any
) -> None:
    await announced(_request())

    await announced(_request(event_name="Gala", location="Hall 2"))

    (edited,) = tg.session.of(EditMessageText)
    assert "Gala" in edited.text
    _, reply = tg.session.of(SendMessage)
    assert reply.text == "🔄 Обновлено"
    assert reply.reply_markup is None
    assert reply.reply_parameters.message_id == edited.message_id


async def test_the_brief_reply_speaks_the_language_of_the_chat(
    tg: Any, announced: Any
) -> None:
    await _configure(language="en")
    await announced(_request())

    await announced(_request(event_name="Gala"))

    assert tg.session.of(SendMessage)[-1].text == "🔄 Updated"


async def test_switching_to_detailed_compares_with_what_brief_mode_remembered(
    tg: Any, announced: Any
) -> None:
    await announced(_request())
    await announced(_request(event_name="Gala"))
    assert tg.session.of(SendMessage)[-1].text == "🔄 Обновлено"
    await _configure(detailed_updates=True)

    await announced(_request(event_name="Gala", organizer="Band"))

    last = tg.session.of(SendMessage)[-1].text
    assert "Организатор: <s>Choir</s> → <b>Band</b>" in last
    assert "Название" not in last


@pytest.mark.usefixtures("detailed")
async def test_an_edited_event_edits_the_message_and_replies_with_what_changed(
    tg: Any, announced: Any
) -> None:
    await announced(_request())

    await announced(_request(event_name="Gala", location="Hall 2"))

    (edited,) = tg.session.of(EditMessageText)
    assert "Gala" in edited.text
    first, reply = tg.session.of(SendMessage)
    assert "Concert" in first.text
    assert reply.text.startswith("🔄 <b>Gala</b> — мероприятие обновлено")
    assert "Название: <s>Concert</s> → <b>Gala</b>" in reply.text
    assert "Место: <s>Main hall</s> → <b>Hall 2</b>" in reply.text
    assert reply.reply_parameters is not None
    assert reply.reply_parameters.message_id == edited.message_id


@pytest.mark.usefixtures("detailed")
async def test_the_reply_carries_the_attendance_buttons_so_people_can_recheck(
    tg: Any, announced: Any
) -> None:
    await announced(_request())

    await announced(_request(event_name="Gala"))

    reply = tg.session.of(SendMessage)[-1]
    first_row = reply.reply_markup.inline_keyboard[0]
    assert [button.style for button in first_row] == ["success", "danger"]
    assert all(
        button.callback_data.startswith("att:") for button in first_row
    )


@pytest.mark.usefixtures("detailed")
async def test_each_update_is_compared_with_the_one_before_it(
    tg: Any, announced: Any
) -> None:
    await announced(_request())
    await announced(_request(event_name="Gala"))

    await announced(_request(event_name="Gala", organizer="Band"))

    last = tg.session.of(SendMessage)[-1].text
    assert "Организатор: <s>Choir</s> → <b>Band</b>" in last
    assert "Название" not in last


@pytest.mark.usefixtures("detailed")
async def test_a_message_sent_before_snapshots_existed_still_gets_a_notice(
    tg: Any, announced: Any
) -> None:
    from bot.tg.uow.message import TelegramMessageUOW

    async with TelegramMessageUOW() as uow:
        await uow.messages.upsert(str(EVENT), CHAT, 77)
        await uow.commit(True)

    await announced(_request(event_name="Gala"))

    (reply,) = tg.session.of(SendMessage)
    assert reply.text.startswith("🔄 <b>Gala</b> — мероприятие обновлено")
    assert "Название" not in reply.text


async def test_the_update_notice_always_makes_a_sound_even_in_a_silent_chat(
    tg: Any, announced: Any
) -> None:
    from bot.tg.uow.collective_chat import CollectiveChatUOW

    async with CollectiveChatUOW() as uow:
        await uow.collective_chats.update_settings(COLLECTIVE, {"silent": True})
        await uow.commit(True)
    await announced(_request())

    await announced(_request(event_name="Gala"))

    first, reply = tg.session.of(SendMessage)
    assert first.disable_notification is True
    assert reply.disable_notification is None


async def test_a_notice_that_cannot_be_sent_does_not_fail_the_edit(
    tg: Any, announced: Any, caplog: pytest.LogCaptureFixture
) -> None:
    await announced(_request())
    original = tg.session.make_request

    async def refuse_replies(  # noqa: ASYNC109
        bot: Any, method: Any, timeout: Any = None
    ) -> Any:
        if isinstance(method, SendMessage) and method.reply_parameters:
            raise TelegramBadRequest(method, "Bad Request: have no rights")
        return await original(bot, method, timeout)

    tg.session.make_request = refuse_replies

    with caplog.at_level("WARNING"):
        await announced(_request(event_name="Gala"))

    assert len(tg.session.of(EditMessageText)) == 1
    assert "update notice failed" in caplog.text
    assert "announcement failed" not in caplog.text


async def test_the_snapshot_is_kept_with_the_sent_message(
    tg: Any, announced: Any, bot_seed: Any
) -> None:
    from bot.tg.model.message import TelegramMessageORM

    await announced(_request())
    await announced(_request(event_name="Gala"))

    (row,) = await bot_seed.all(TelegramMessageORM)
    assert row.payload["event_name"] == "Gala"
    assert UUID(row.payload["event_id"]) == EVENT
