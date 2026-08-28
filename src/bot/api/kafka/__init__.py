from bot.api.kafka.sub.account import router as account_router
from bot.api.kafka.sub.announcement import router as announcement_router
from bot.api.kafka.sub.telegram import router as telegram_router
from core.broker.kafka import KafkaRouter

router = KafkaRouter()
router.include_router(telegram_router)
router.include_router(announcement_router)
router.include_router(account_router)
