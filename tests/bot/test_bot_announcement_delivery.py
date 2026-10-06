import logging
from datetime import UTC, datetime
from types import SimpleNamespace
from typing import Any
from uuid import UUID, uuid4

import pytest
from aiocache import SimpleMemoryCache  # pyright: ignore[reportMissingTypeStubs]
from aiogram.exceptions import (
    TelegramBadRequest,
    TelegramMigrateToChat,
    TelegramNetworkError,
    TelegramNotFound,
    TelegramRetryAfter,
)
from aiogram.methods import SendMessage

from bot.tg.text.localization import i18n_manager
from core.enum.mq import AnnouncementQueue
from core.schema.message.announcement import AnnouncementRequest, AnnouncementStage

CHAT_ID = -1001
NEW_CHAT_ID = -1002
COLLECTIVE_ID = uuid4()


def _method() -> SendMessage:
    return SendMessage(chat_id=CHAT_ID, text="x")


class FakeBot:
    def __init__(
        self,
        send_errors: list[Exception | None] | None = None,
        edit_errors: list[Exception | None] | None = None,
    ) -> None:
        self.send_errors = list(send_errors or [])
        self.edit_errors = list(edit_errors or [])
        self.attempts = 0
        self.sent: list[dict[str, Any]] = []
        self.edited: list[dict[str, Any]] = []
        self.pinned: list[dict[str, Any]] = []
        self.pin_error: Exception | None = None

    async def send_message(self, **kwargs: Any) -> SimpleNamespace:
        self.attempts += 1
        if self.send_errors:
            error = self.send_errors.pop(0)
            if error is not None:
                raise error
        self.sent.append(kwargs)
        return SimpleNamespace(message_id=500 + len(self.sent))

    async def pin_chat_message(self, **kwargs: Any) -> None:
        if self.pin_error is not None:
            raise self.pin_error
        self.pinned.append(kwargs)

    async def edit_message_text(self, **kwargs: Any) -> None:
        if self.edit_errors:
            error = self.edit_errors.pop(0)
            if error is not None:
                raise error
        self.edited.append(kwargs)


class FakeChatRepo:
    def __init__(self, chat: SimpleNamespace | None) -> None:
        self.chat = chat
        self.upserts: list[int] = []
        self.fail = False

    async def get_by_collective_id(
        self, collective_id: UUID
    ) -> SimpleNamespace | None:
        if self.fail:
            raise RuntimeError("database is down")
        return self.chat

    async def upsert(
        self,
        collective_id: UUID,
        chat_id: int,
        set_by_id: int,
        thread_id: int | None = None,
    ) -> SimpleNamespace:
        self.upserts.append(chat_id)
        self.chat = _chat(thread_id)
        self.chat.collective_id = collective_id
        self.chat.chat_id = chat_id
        self.chat.set_by_id = set_by_id
        return self.chat


class FakeMessageRepo:
    def __init__(self) -> None:
        self.rows: dict[tuple[str, int], SimpleNamespace] = {}

    async def get(
        self, correlation_key: str, chat_id: int
    ) -> SimpleNamespace | None:
        return self.rows.get((correlation_key, chat_id))

    async def upsert(
        self,
        correlation_key: str,
        chat_id: int,
        message_id: int,
        payload: dict[str, Any] | None = None,
    ) -> None:
        self.rows[(correlation_key, chat_id)] = SimpleNamespace(
            message_id=message_id, payload=payload
        )


class FakeUOW:
    def __init__(self, **repos: Any) -> None:
        self.__dict__.update(repos)

    async def __aenter__(self) -> "FakeUOW":
        return self

    async def __aexit__(self, *exc: object) -> None:
        return None

    async def commit(self, flush: bool = False) -> None:
        return None


class Harness:
    def __init__(
        self, module: Any, bot: FakeBot, chat: SimpleNamespace | None
    ) -> None:
        self.module = module
        self.bot = bot
        self.chats = FakeChatRepo(chat)
        self.messages = FakeMessageRepo()
        self.dead_letters: list[tuple[Any, str]] = []
        self.pauses: list[float] = []

    async def run(self, request: AnnouncementRequest) -> None:
        await self.module.deliver_announcement(
            request,
            uow=FakeUOW(messages=self.messages),
            chat_uow=FakeUOW(collective_chats=self.chats),
        )


def _chat(thread_id: int | None = None, **settings: Any) -> SimpleNamespace:
    row: dict[str, Any] = {
        "collective_id": COLLECTIVE_ID,
        "chat_id": CHAT_ID,
        "thread_id": thread_id,
        "set_by_id": 7,
        "announce_enabled": True,
        "silent": False,
        "pin_announcements": False,
        "detailed_updates": False,
        "language": None,
    }
    return SimpleNamespace(**(row | settings))


def _request(event_id: UUID | None = None) -> AnnouncementRequest:
    return AnnouncementRequest(
        collective_id=COLLECTIVE_ID,
        event_id=event_id or uuid4(),
        event_name="Concert",
        action_url="https://example.test/event/1",
    )


@pytest.fixture
def make_harness(monkeypatch: pytest.MonkeyPatch):
    import bot.api.kafka.sub.announcement as module

    monkeypatch.setattr(i18n_manager, "cache", SimpleMemoryCache())

    def make(bot: FakeBot, chat: SimpleNamespace | None = None) -> Harness:
        harness = Harness(module, bot, chat)

        async def pause(seconds: float) -> None:
            harness.pauses.append(seconds)

        class Recorder:
            async def publish(
                self, message: Any, topic: str, *args: Any, **kwargs: Any
            ) -> None:
                harness.dead_letters.append((message, topic))

        monkeypatch.setattr(module, "tg_bot", bot)
        monkeypatch.setattr(module, "_pause", pause, raising=False)
        monkeypatch.setattr(module, "broker", Recorder(), raising=False)
        return harness

    return make


async def test_announcement_is_sent_to_the_bound_chat(make_harness: Any) -> None:
    harness = make_harness(FakeBot(), _chat(thread_id=9))
    request = _request()

    await harness.run(request)

    assert len(harness.bot.sent) == 1
    sent = harness.bot.sent[0]
    assert sent["chat_id"] == CHAT_ID
    assert sent["message_thread_id"] == 9
    assert "Concert" in sent["text"]
    assert (str(request.event_id), CHAT_ID) in harness.messages.rows


async def test_collective_without_a_chat_is_skipped_and_explained(
    make_harness: Any, caplog: pytest.LogCaptureFixture
) -> None:
    harness = make_harness(FakeBot(), None)

    with caplog.at_level(logging.INFO):
        await harness.run(_request())

    assert harness.bot.attempts == 0
    assert str(COLLECTIVE_ID) in caplog.text
    assert "/setup_chat" in caplog.text


async def test_flood_control_is_waited_out_and_retried(make_harness: Any) -> None:
    flood = TelegramRetryAfter(_method(), "Too Many Requests", 3)
    harness = make_harness(FakeBot(send_errors=[flood, None]), _chat())

    await harness.run(_request())

    assert len(harness.bot.sent) == 1
    assert harness.pauses
    assert harness.pauses[0] >= 3


async def test_network_error_is_retried(make_harness: Any) -> None:
    harness = make_harness(
        FakeBot(send_errors=[TelegramNetworkError(_method(), "timeout"), None]),
        _chat(),
    )

    await harness.run(_request())

    assert len(harness.bot.sent) == 1
    assert len(harness.pauses) == 1


async def test_retries_are_bounded(
    make_harness: Any, caplog: pytest.LogCaptureFixture
) -> None:
    errors: list[Exception | None] = [
        TelegramNetworkError(_method(), "timeout") for _ in range(10)
    ]
    harness = make_harness(FakeBot(send_errors=errors), _chat())

    with caplog.at_level(logging.WARNING):
        await harness.run(_request())

    assert harness.bot.attempts == 3
    assert "announcement delivery failed" in caplog.text
    assert not harness.dead_letters


async def test_chat_that_does_not_exist_is_not_retried(make_harness: Any) -> None:
    gone = TelegramNotFound(_method(), "Not Found: chat not found")
    harness = make_harness(FakeBot(send_errors=[gone]), _chat())

    await harness.run(_request())

    assert harness.bot.attempts == 1
    assert not harness.pauses


async def test_group_upgraded_to_supergroup_is_rebound_and_resent(
    make_harness: Any,
) -> None:
    migrated = TelegramMigrateToChat(
        _method(), "group chat was upgraded to a supergroup chat", NEW_CHAT_ID
    )
    harness = make_harness(FakeBot(send_errors=[migrated, None]), _chat())
    request = _request()

    await harness.run(request)

    assert harness.chats.upserts == [NEW_CHAT_ID]
    assert [message["chat_id"] for message in harness.bot.sent] == [NEW_CHAT_ID]
    assert (str(request.event_id), NEW_CHAT_ID) in harness.messages.rows


async def test_deleted_announcement_is_replaced_instead_of_edited(
    make_harness: Any,
) -> None:
    gone = TelegramBadRequest(
        _method(), "Bad Request: message to edit not found"
    )
    harness = make_harness(FakeBot(edit_errors=[gone]), _chat())
    request = _request()
    key = (str(request.event_id), CHAT_ID)
    harness.messages.rows[key] = SimpleNamespace(message_id=42, payload=None)

    await harness.run(request)

    assert len(harness.bot.sent) == 1
    assert harness.bot.sent[0]["chat_id"] == CHAT_ID
    assert harness.messages.rows[key].message_id == 501


async def test_unexpected_failure_is_dead_lettered_not_raised(
    make_harness: Any, caplog: pytest.LogCaptureFixture
) -> None:
    harness = make_harness(FakeBot(), _chat())
    harness.chats.fail = True
    request = _request()

    with caplog.at_level(logging.ERROR):
        await harness.run(request)

    assert harness.dead_letters == [
        (request, AnnouncementQueue.COLLECTIVE_REQUESTED_DLQ)
    ]
    assert str(request.event_id) in caplog.text


async def test_switched_off_announcements_are_not_sent(make_harness: Any) -> None:
    harness = make_harness(FakeBot(), _chat(announce_enabled=False))

    await harness.run(_request())

    assert harness.bot.sent == []
    assert harness.dead_letters == []


async def test_a_silent_chat_gets_a_quiet_announcement(make_harness: Any) -> None:
    harness = make_harness(FakeBot(), _chat(silent=True))

    await harness.run(_request())

    assert harness.bot.sent[0]["disable_notification"] is True


async def test_an_ordinary_chat_is_notified(make_harness: Any) -> None:
    harness = make_harness(FakeBot(), _chat())

    await harness.run(_request())

    assert harness.bot.sent[0]["disable_notification"] is None
    assert harness.bot.pinned == []


async def test_the_announcement_is_pinned_when_asked(make_harness: Any) -> None:
    harness = make_harness(FakeBot(), _chat(pin_announcements=True))

    await harness.run(_request())

    assert harness.bot.pinned == [
        {"chat_id": CHAT_ID, "message_id": 501, "disable_notification": True}
    ]


async def test_a_failed_pin_does_not_fail_the_delivery(
    make_harness: Any, caplog: pytest.LogCaptureFixture
) -> None:
    bot = FakeBot()
    bot.pin_error = TelegramBadRequest(_method(), "Bad Request: not enough rights")
    harness = make_harness(bot, _chat(pin_announcements=True))

    with caplog.at_level(logging.WARNING):
        await harness.run(_request())

    assert len(bot.sent) == 1
    assert harness.dead_letters == []
    assert "could not pin" in caplog.text


async def test_the_announcement_speaks_the_language_of_the_chat(
    make_harness: Any,
) -> None:
    harness = make_harness(FakeBot(), _chat(language="en"))

    await harness.run(_request())

    sent = harness.bot.sent[0]
    assert "Mark your attendance below" in sent["text"]
    first_row = sent["reply_markup"].inline_keyboard[0]
    assert [button.text for button in first_row] == ["✅ Going", "❌ Not going"]


async def test_attendance_buttons_are_coloured_and_link_to_the_event(
    make_harness: Any,
) -> None:
    harness = make_harness(FakeBot(), _chat())
    request = _request()

    await harness.run(request)

    rows = harness.bot.sent[0]["reply_markup"].inline_keyboard
    yes, no = rows[0]
    assert (yes.style, no.style) == ("success", "danger")
    assert yes.callback_data == f"att:{request.event_id.hex}:yes"
    assert no.callback_data == f"att:{request.event_id.hex}:no"
    assert rows[1][0].url == "https://example.test/event/1"
    assert rows[1][0].callback_data is None


async def test_an_edit_is_announced_in_the_language_of_the_chat(
    make_harness: Any,
) -> None:
    harness = make_harness(
        FakeBot(), _chat(language="en", detailed_updates=True)
    )
    request = _request()
    harness.messages.rows[(str(request.event_id), CHAT_ID)] = SimpleNamespace(
        message_id=42, payload=None
    )

    await harness.run(request)

    assert len(harness.bot.edited) == 1
    notice = harness.bot.sent[0]["text"]
    assert "was updated" in notice
    assert "Check that your mark is still right" in notice
    assert harness.bot.sent[0]["reply_markup"] is not None


async def test_an_edit_is_announced_briefly_unless_the_chat_wants_details(
    make_harness: Any,
) -> None:
    harness = make_harness(FakeBot(), _chat(language="en"))
    request = _request()
    harness.messages.rows[(str(request.event_id), CHAT_ID)] = SimpleNamespace(
        message_id=42, payload=None
    )

    await harness.run(request)

    assert len(harness.bot.edited) == 1
    assert harness.bot.sent[0]["text"] == "🔄 Updated"
    assert harness.bot.sent[0]["reply_markup"] is None


async def test_rejected_date_entities_are_resent_as_plain_text(
    make_harness: Any,
) -> None:
    rejected = TelegramBadRequest(
        _method(), "Bad Request: can't parse entities: unsupported tag"
    )
    harness = make_harness(FakeBot(send_errors=[rejected]), _chat())
    request = AnnouncementRequest(
        collective_id=COLLECTIVE_ID,
        event_id=uuid4(),
        event_name="Concert",
        stages=[
            AnnouncementStage(
                name="Doors", start_at=datetime(2026, 5, 1, 9, tzinfo=UTC)
            )
        ],
    )

    await harness.run(request)

    assert "<tg-time" not in harness.bot.sent[0]["text"]
    assert "09:00" in harness.bot.sent[0]["text"]
    assert harness.dead_letters == []


async def test_a_rejected_link_button_is_resent_without_links(
    make_harness: Any,
) -> None:
    rejected = TelegramBadRequest(_method(), "Bad Request: BUTTON_URL_INVALID")
    harness = make_harness(FakeBot(send_errors=[rejected]), _chat())

    await harness.run(_request())

    rows = harness.bot.sent[0]["reply_markup"].inline_keyboard
    assert len(rows) == 1
    assert [button.url for button in rows[0]] == [None, None]
