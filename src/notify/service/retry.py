from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

from core.enum.notify import DeliveryStatus

from notify.config.settings import settings


@dataclass
class RetryDecision:
    """Outcome of evaluating a temporary delivery failure."""

    status: DeliveryStatus
    next_attempt_at: datetime | None


class RetryPolicy:
    """Exponential backoff with a cap. Once the attempts budget is spent the
    delivery becomes terminally ``failed`` instead of being retried."""

    def __init__(self, base_seconds: float, cap_seconds: float) -> None:
        self._base = base_seconds
        self._cap = cap_seconds

    def after_failure(
        self, attempts_done: int, max_attempts: int
    ) -> RetryDecision:
        if attempts_done >= max_attempts:
            return RetryDecision(DeliveryStatus.failed, None)
        delay = min(self._cap, self._base * (2 ** (attempts_done - 1)))
        next_at = datetime.now(timezone.utc) + timedelta(seconds=delay)
        return RetryDecision(DeliveryStatus.retry_scheduled, next_at)


policy = RetryPolicy(
    settings.DELIVERY_RETRY_BACKOFF_BASE_SECONDS,
    settings.DELIVERY_RETRY_BACKOFF_CAP_SECONDS,
)
