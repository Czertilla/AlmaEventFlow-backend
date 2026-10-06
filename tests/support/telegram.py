from collections.abc import AsyncGenerator, Callable
from datetime import UTC, datetime
from itertools import count
from typing import Any

from aiogram import Bot, Dispatcher
from aiogram.client.session.base import BaseSession
from aiogram.methods import (
    AnswerCallbackQuery,
    DeleteMessage,
    EditMessageText,
    GetChat,
    GetChatMember,
    GetMe,
    SendMessage,
    TelegramMethod,
)
from aiogram.types import Message, Update, User

TOKEN = "123456:ABCdefGhIJKlmNoPQRsTUVwxyZ-0123456"
BOT_ID = 123456
BOT_USERNAME = "aef_test_bot"

_update_ids = count(1)
_message_ids = count(1000)


class RecordingSession(BaseSession):
    """Stands in for Telegram: records every call the bot makes and answers
    with canned data. ``admins`` maps a chat id to the user ids that are
    administrators there; ``failures`` maps a method type to an exception to
    raise instead of answering."""

    def __init__(self) -> None:
        super().__init__()
        self.calls: list[TelegramMethod[Any]] = []
        self.admins: dict[int, set[int]] = {}
        self.titles: dict[int, str] = {}
        self.failures: dict[type, Exception] = {}

    async def close(self) -> None:
        return None

    async def stream_content(
        self, *args: Any, **kwargs: Any
    ) -> AsyncGenerator[bytes]:
        yield b""

    def of(self, method: type[TelegramMethod[Any]]) -> list[Any]:
        return [call for call in self.calls if isinstance(call, method)]

    @property
    def sent(self) -> list[SendMessage]:
        return self.of(SendMessage)

    async def make_request(
        self,
        bot: Bot,
        method: TelegramMethod[Any],
        timeout: int | None = None,  # noqa: ASYNC109
    ) -> Any:
        self.calls.append(method)
        if type(method) in self.failures:
            raise self.failures[type(method)]
        if isinstance(method, GetMe):
            return User(
                id=BOT_ID,
                is_bot=True,
                first_name="AEF",
                username=BOT_USERNAME,
            )
        if isinstance(method, GetChatMember):
            return self._member(method)
        if isinstance(method, GetChat):
            return self._chat(bot, method)
        if isinstance(method, SendMessage | EditMessageText):
            return self._message(bot, method)
        if isinstance(method, AnswerCallbackQuery | DeleteMessage):
            return True
        return True

    def _member(self, method: GetChatMember) -> Any:
        from aiogram.types import ChatMemberAdministrator, ChatMemberMember

        user = User(id=method.user_id, is_bot=False, first_name="x")
        if method.user_id in self.admins.get(int(method.chat_id), set()):
            return ChatMemberAdministrator(
                user=user,
                can_be_edited=False,
                is_anonymous=False,
                can_manage_chat=True,
                can_delete_messages=True,
                can_manage_video_chats=False,
                can_restrict_members=False,
                can_promote_members=False,
                can_change_info=False,
                can_invite_users=True,
                can_post_stories=False,
                can_edit_stories=False,
                can_delete_stories=False,
                can_send_welcome_messages=False,
            )
        return ChatMemberMember(user=user)

    def _chat(self, bot: Bot, method: GetChat) -> Any:
        from aiogram.types import ChatFullInfo

        chat_id = int(method.chat_id)
        return ChatFullInfo.model_validate(
            {
                "id": chat_id,
                "type": "supergroup" if chat_id < 0 else "private",
                "title": self.titles.get(chat_id, "Group"),
                "accent_color_id": 0,
                "max_reaction_count": 0,
                "accepted_gift_types": {
                    "unlimited_gifts": False,
                    "limited_gifts": False,
                    "unique_gifts": False,
                    "premium_subscription": False,
                    "gifts_from_channels": False,
                },
            },
            context={"bot": bot},
        )

    @staticmethod
    def _message(bot: Bot, method: SendMessage | EditMessageText) -> Message:
        chat_id = getattr(method, "chat_id", 0) or 0
        return Message.model_validate(
            {
                "message_id": getattr(method, "message_id", None)
                or next(_message_ids),
                "date": int(datetime.now(UTC).timestamp()),
                "chat": {
                    "id": int(chat_id),
                    "type": "private" if int(chat_id) > 0 else "supergroup",
                },
                "text": getattr(method, "text", ""),
            },
            context={"bot": bot},
        )


def make_bot() -> tuple[Bot, RecordingSession]:
    session = RecordingSession()
    return Bot(token=TOKEN, session=session), session


def user_json(
    user_id: int,
    *,
    username: str | None = None,
    language: str | None = "ru",
    first_name: str | None = None,
) -> dict[str, Any]:
    data: dict[str, Any] = {
        "id": user_id,
        "is_bot": False,
        "first_name": first_name or f"User{user_id}",
    }
    if username:
        data["username"] = username
    if language:
        data["language_code"] = language
    return data


def _entities(text: str) -> list[dict[str, Any]]:
    if not text.startswith("/"):
        return []
    length = len(text.split(maxsplit=1)[0])
    return [{"type": "bot_command", "offset": 0, "length": length}]


def message_update(
    bot: Bot,
    text: str,
    *,
    user: dict[str, Any],
    chat_id: int | None = None,
    chat_type: str = "private",
    thread_id: int | None = None,
    extra: dict[str, Any] | None = None,
) -> Update:
    message: dict[str, Any] = {
        "message_id": next(_message_ids),
        "date": int(datetime.now(UTC).timestamp()),
        "chat": {
            "id": chat_id if chat_id is not None else user["id"],
            "type": chat_type,
        },
        "from": user,
        "text": text,
        "entities": _entities(text),
    }
    if thread_id is not None:
        message["message_thread_id"] = thread_id
        message["is_topic_message"] = True
    message.update(extra or {})
    return Update.model_validate(
        {"update_id": next(_update_ids), "message": message},
        context={"bot": bot},
    )


def callback_update(
    bot: Bot,
    data: str,
    *,
    user: dict[str, Any],
    chat_id: int | None = None,
    chat_type: str = "private",
    thread_id: int | None = None,
) -> Update:
    message: dict[str, Any] = {
        "message_id": next(_message_ids),
        "date": int(datetime.now(UTC).timestamp()),
        "chat": {
            "id": chat_id if chat_id is not None else user["id"],
            "type": chat_type,
        },
        "from": {
            "id": BOT_ID,
            "is_bot": True,
            "first_name": "AEF",
            "username": BOT_USERNAME,
        },
        "text": "menu",
    }
    if thread_id is not None:
        message["message_thread_id"] = thread_id
        message["is_topic_message"] = True
    return Update.model_validate(
        {
            "update_id": next(_update_ids),
            "callback_query": {
                "id": str(next(_update_ids)),
                "from": user,
                "chat_instance": "ci",
                "data": data,
                "message": message,
            },
        },
        context={"bot": bot},
    )


def member_update(
    bot: Bot,
    *,
    chat_id: int,
    chat_type: str,
    actor: dict[str, Any],
    old: str,
    new: str,
) -> Update:
    def member(status: str) -> dict[str, Any]:
        data: dict[str, Any] = {
            "status": status,
            "user": {
                "id": BOT_ID,
                "is_bot": True,
                "first_name": "AEF",
                "username": BOT_USERNAME,
            },
        }
        if status == "administrator":
            data |= {
                "can_be_edited": False,
                "is_anonymous": False,
                "can_manage_chat": True,
                "can_delete_messages": True,
                "can_manage_video_chats": False,
                "can_restrict_members": False,
                "can_promote_members": False,
                "can_change_info": False,
                "can_invite_users": True,
                "can_post_stories": False,
                "can_edit_stories": False,
                "can_delete_stories": False,
                "can_send_welcome_messages": False,
            }
        if status == "kicked":
            data["until_date"] = 0
        return data

    return Update.model_validate(
        {
            "update_id": next(_update_ids),
            "my_chat_member": {
                "chat": {"id": chat_id, "type": chat_type},
                "from": actor,
                "date": int(datetime.now(UTC).timestamp()),
                "old_chat_member": member(old),
                "new_chat_member": member(new),
            },
        },
        context={"bot": bot},
    )


_dispatcher: Dispatcher | None = None


def dispatcher() -> Dispatcher:
    """The bot's real dispatcher, built once: its routers can be attached to
    a single parent only."""
    global _dispatcher
    if _dispatcher is None:
        from aiogram3_di import setup_di  # pyright: ignore[reportMissingTypeStubs]

        from bot.tg.api.router import register_routers

        dp = Dispatcher()
        register_routers(dp)
        setup_di(dp)
        _dispatcher = dp
    return _dispatcher


async def feed(bot: Bot, update: Update) -> Any:
    return await dispatcher().feed_update(bot, update)


Responder = Callable[[TelegramMethod[Any]], Any]
