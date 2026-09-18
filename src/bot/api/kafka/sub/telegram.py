from logging import getLogger

from fastapi import Depends

from bot.tg.dependency.bot import bot as tg_bot
from bot.tg.service.delivery import TelegramDeliveryService
from bot.tg.uow.message import TelegramMessageUOW
from core.broker.kafka import KafkaRouter, broker
from core.dependencies.uow import ModuleUOWDep
from core.enum.mq import NotifyDeliveryQueue
from core.schema.message.notify import TelegramDeliveryBatch

logger = getLogger(__name__)

router = KafkaRouter()

MessageUOWDep = Depends(ModuleUOWDep("bot")(TelegramMessageUOW))


@router.subscriber(NotifyDeliveryQueue.TELEGRAM)
async def deliver_telegram_batch(
    batch: TelegramDeliveryBatch, uow: TelegramMessageUOW = MessageUOWDep
) -> None:
    """Delegated telegram-transport batch from notify. Each item is delivered
    (sent or edited) independently and its own result reported back — a
    per-recipient failure never aborts the rest of the batch."""
    logger.info(
        "Telegram batch %s: %d deliveries", batch.message_id, len(batch.items)
    )
    service = TelegramDeliveryService(uow, tg_bot)
    try:
        for item in batch.items:
            result = await service.deliver(item)
            await broker.publish(result, NotifyDeliveryQueue.RESULT)
    except Exception:
        logger.exception("Telegram batch %s failed", batch.message_id)
        await broker.publish(batch, NotifyDeliveryQueue.TELEGRAM_DLQ)
