from logging import getLogger
from typing import Any

from aiogram.enums import ChatType
from aiogram.exceptions import TelegramAPIError
from aiogram.types import EphemeralMessageParameters, Message

logger = getLogger(__name__)

_GROUPS = {ChatType.GROUP, ChatType.SUPERGROUP}


async def reply_to_sender(
    message: Message, text: str, *, user_id: int | None = None, **kwargs: Any
) -> Message | None:
    """Answers so that only the sender sees it, where Telegram allows that:
    an ephemeral message in a group. Delivery of those is not guaranteed and
    the feature is new, so any failure falls back to an ordinary reply."""
    receiver = user_id or (message.from_user.id if message.from_user else None)
    if message.chat.type in _GROUPS and receiver is not None:
        try:
            return await message.bot.send_message(  # pyright: ignore[reportOptionalMemberAccess]
                chat_id=message.chat.id,
                text=text,
                message_thread_id=message.message_thread_id
                if message.is_topic_message
                else None,
                ephemeral_message_parameters=EphemeralMessageParameters(
                    receiver_user_id=receiver
                ),
                **kwargs,
            )
        except TelegramAPIError:
            logger.info(
                "ephemeral reply to %s in chat %s failed, replying openly",
                receiver,
                message.chat.id,
                exc_info=True,
            )
    return await message.reply(text, **kwargs)
