import asyncio
import contextlib
from logging import getLogger
from uuid import uuid4

from fastapi import Depends

from bot.tg.dependency.bot import bot as tg_bot
from bot.tg.model.collective_chat import CollectiveChatORM
from bot.tg.service.announcement import build_announcement_text
from bot.tg.service.delivery import (
    RETRY_AFTER_PREFIX,
    ChatMigratedError,
    TelegramDeliveryService,
)
from bot.tg.uow.collective_chat import CollectiveChatUOW
from bot.tg.uow.message import TelegramMessageUOW
from core.broker.kafka import KafkaRouter, broker
from core.dependencies.uow import ModuleUOWDep
from core.enum.mq import AnnouncementQueue
from core.enum.notify import DeliveryStatus
from core.schema.message.announcement import AnnouncementRequest
from core.schema.message.notify import (
    DeliveryResult,
    TelegramButton,
    TelegramDeliveryItem,
)

logger = getLogger(__name__)

router = KafkaRouter()

MessageUOWDep = Depends(ModuleUOWDep("bot")(TelegramMessageUOW))
CollectiveChatUOWDep = Depends(ModuleUOWDep("bot")(CollectiveChatUOW))

MAX_ATTEMPTS = 3
_BACKOFF = (2.0, 5.0)
_MAX_RETRY_AFTER = 30.0


def _buttons(event_id) -> list[list[TelegramButton]]:
    return [
        [
            TelegramButton(text="✅ Буду", callback_data=f"att:{event_id}:yes"),
            TelegramButton(
                text="❌ Не буду", callback_data=f"att:{event_id}:no"
            ),
        ]
    ]


async def _pause(seconds: float) -> None:
    await asyncio.sleep(seconds)


def _retry_delay(result: DeliveryResult, attempt: int) -> float:
    delay = _BACKOFF[min(attempt, len(_BACKOFF)) - 1]
    if result.error and result.error.startswith(RETRY_AFTER_PREFIX):
        with contextlib.suppress(ValueError):
            requested = float(result.error[len(RETRY_AFTER_PREFIX) :])
            return min(max(requested, delay), _MAX_RETRY_AFTER)
    return delay


@router.subscriber(AnnouncementQueue.COLLECTIVE_REQUESTED)
async def deliver_announcement(
    request: AnnouncementRequest,
    uow: TelegramMessageUOW = MessageUOWDep,
    chat_uow: CollectiveChatUOW = CollectiveChatUOWDep,
) -> None:
    """Group-chat announcement — entirely outside notify. Looks up the
    collective's chat itself; a collective with no chat set up is simply
    skipped (not an error, just nothing to do yet). Never raises: an
    unexpected failure is logged and the request dead-lettered."""
    logger.info(
        "announcement received: event=%s collective=%s stages=%d",
        request.event_id,
        request.collective_id,
        len(request.stages),
    )
    try:
        await _deliver(request, uow, chat_uow)
    except Exception:
        logger.exception(
            "announcement failed: event=%s collective=%s, dead-lettering",
            request.event_id,
            request.collective_id,
        )
        await _dead_letter(request)


async def _dead_letter(request: AnnouncementRequest) -> None:
    try:
        await broker.publish(request, AnnouncementQueue.COLLECTIVE_REQUESTED_DLQ)
    except Exception:
        logger.exception(
            "could not dead-letter announcement for event %s",
            request.event_id,
        )


async def _rebind(
    chat_uow: CollectiveChatUOW,
    request: AnnouncementRequest,
    chat: CollectiveChatORM,
    new_chat_id: int,
) -> None:
    async with chat_uow as scope:
        await scope.collective_chats.upsert(
            request.collective_id,
            new_chat_id,
            chat.set_by_id,
            thread_id=chat.thread_id,
        )
        await scope.commit(True)
    logger.warning(
        "chat %s was migrated to %s, collective %s rebound",
        chat.chat_id,
        new_chat_id,
        request.collective_id,
    )


async def _deliver(
    request: AnnouncementRequest,
    uow: TelegramMessageUOW,
    chat_uow: CollectiveChatUOW,
) -> None:
    async with chat_uow as scope:
        chat = await scope.collective_chats.get_by_collective_id(
            request.collective_id
        )
    if chat is None:
        logger.info(
            "no chat bound to collective %s, announcement for event %s "
            "skipped (bind one with /setup_chat in the group)",
            request.collective_id,
            request.event_id,
        )
        return
    logger.info(
        "announcement target: event=%s collective=%s chat=%s thread=%s",
        request.event_id,
        request.collective_id,
        chat.chat_id,
        chat.thread_id,
    )

    item = TelegramDeliveryItem(
        delivery_id=uuid4(),
        chat_id=str(chat.chat_id),
        text=await build_announcement_text(request),
        buttons=_buttons(request.event_id),
        correlation_key=str(request.event_id),
        message_thread_id=chat.thread_id,
    )
    service = TelegramDeliveryService(uow, tg_bot)
    migrated = False
    attempt = 1
    while True:
        try:
            result = await service.deliver(item)
        except ChatMigratedError as exc:
            if migrated:
                raise
            migrated = True
            await _rebind(chat_uow, request, chat, exc.new_chat_id)
            item = item.model_copy(update={"chat_id": str(exc.new_chat_id)})
            continue
        if (
            result.status != DeliveryStatus.retry_scheduled
            or attempt >= MAX_ATTEMPTS
        ):
            break
        delay = _retry_delay(result, attempt)
        logger.warning(
            "announcement delivery to chat %s will be retried in %.0f s "
            "(attempt %d/%d): %s",
            item.chat_id,
            delay,
            attempt,
            MAX_ATTEMPTS,
            result.error,
        )
        await _pause(delay)
        attempt += 1

    if result.status not in (DeliveryStatus.sent, DeliveryStatus.delivered):
        logger.warning(
            "announcement delivery failed for collective %s, event %s, "
            "chat %s: status=%s error=%s",
            request.collective_id,
            request.event_id,
            item.chat_id,
            result.status,
            result.error,
        )
        return
    logger.info(
        "announcement delivered: event=%s collective=%s chat=%s message=%s",
        request.event_id,
        request.collective_id,
        item.chat_id,
        result.provider_message_id,
    )
