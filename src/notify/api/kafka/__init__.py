from core.broker.kafka import KafkaRouter

from notify.api.kafka.sub.account import router as account_router
from notify.api.kafka.sub.notify import router as notify_router
from notify.api.kafka.sub.result import router as result_router
from notify.api.kafka.sub.webpush import router as webpush_router

router = KafkaRouter()
router.include_router(account_router)
router.include_router(notify_router)
router.include_router(webpush_router)
router.include_router(result_router)
