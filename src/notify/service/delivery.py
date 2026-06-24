from logging import getLogger

from core.enum.notify import DeliveryStatus
from core.schema.message.notify import DeliveryResult
from core.service.base import BaseService, required_transaction

from notify.service.retry import policy
from notify.uow.delivery import DeliveryResultUOW

logger = getLogger(__name__)


class DeliveryService(BaseService[DeliveryResultUOW]):
    """Applies delivery outcomes reported by external workers over the result
    topic. Idempotent: results for already-terminal deliveries are ignored. A
    reported ``retry_scheduled`` is run through the backoff policy, which may
    downgrade it to terminal ``failed`` once the attempts budget is spent."""

    async def apply_result(self, result: DeliveryResult) -> None:
        async with self.uow as uow:
            await self._apply(result)
            await uow.commit()

    @required_transaction
    async def _apply(self, result: DeliveryResult) -> None:
        delivery = await self.uow.deliveries.get_by_id(result.delivery_id)
        if delivery is None:
            logger.warning("Result for unknown delivery %s", result.delivery_id)
            return
        if delivery.status in DeliveryStatus.terminal():
            return
        attempts_done = delivery.attempts + 1
        status = result.status
        next_attempt_at = None
        if status == DeliveryStatus.retry_scheduled:
            decision = policy.after_failure(attempts_done, delivery.max_attempts)
            status = decision.status
            next_attempt_at = decision.next_attempt_at
        await self.uow.deliveries.update_one(
            result.delivery_id,
            {
                "status": status,
                "attempts": attempts_done,
                "last_error": result.error,
                "provider_message_id": result.provider_message_id,
                "next_attempt_at": next_attempt_at,
            },
        )
