from html import escape
from logging import getLogger
from uuid import uuid4

from fastapi import Depends

from bot.tg.dependency.bot import bot as tg_bot
from bot.tg.service.delivery import TelegramDeliveryService
from bot.tg.uow.collective_chat import CollectiveChatUOW
from bot.tg.uow.message import TelegramMessageUOW
from core.broker.kafka import KafkaRouter
from core.dependencies.uow import ModuleUOWDep
from core.enum.mq import AnnouncementQueue
from core.enum.notify import DeliveryStatus
from core.schema.message.announcement import AnnouncementRequest
from core.schema.message.notify import TelegramButton, TelegramDeliveryItem

logger = getLogger(__name__)

router = KafkaRouter()

MessageUOWDep = Depends(ModuleUOWDep("bot")(TelegramMessageUOW))
CollectiveChatUOWDep = Depends(ModuleUOWDep("bot")(CollectiveChatUOW))


def _buttons(event_id) -> list[list[TelegramButton]]:
    return [
        [
            TelegramButton(text="✅ Буду", callback_data=f"att:{event_id}:yes"),
            TelegramButton(
                text="❌ Не буду", callback_data=f"att:{event_id}:no"
            ),
        ]
    ]


@router.subscriber(AnnouncementQueue.COLLECTIVE_REQUESTED)
async def deliver_announcement(
    request: AnnouncementRequest,
    uow: TelegramMessageUOW = MessageUOWDep,
    chat_uow: CollectiveChatUOW = CollectiveChatUOWDep,
) -> None:
    """Group-chat announcement — entirely outside notify. Looks up the
    collective's chat itself; a collective with no chat set up is simply
    skipped (not an error, just nothing to do yet)."""
    async with chat_uow as scope:
        chat = await scope.collective_chats.get_by_collective_id(
            request.collective_id
        )
    if chat is None:
        logger.debug(
            "no chat set up for collective %s, skipping announcement",
            request.collective_id,
        )
        return

    item = TelegramDeliveryItem(
        delivery_id=uuid4(),
        chat_id=str(chat.chat_id),
        text=f"<b>{escape(request.title)}</b>\n\n{escape(request.body)}",
        buttons=_buttons(request.event_id),
        correlation_key=str(request.event_id),
        message_thread_id=chat.thread_id,
    )
    result = await TelegramDeliveryService(uow, tg_bot).deliver(item)
    if result.status not in (DeliveryStatus.sent, DeliveryStatus.delivered):
        logger.warning(
            "announcement delivery failed for collective %s, event %s: %s",
            request.collective_id,
            request.event_id,
            result.error,
        )
