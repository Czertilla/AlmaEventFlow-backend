from datetime import datetime, timezone

from core.enum.notify import DeliveryStatus
from notify.service.retry import RetryPolicy


def test_retry_scheduled_with_growing_backoff():
    policy = RetryPolicy(base_seconds=60, cap_seconds=3600)
    before = datetime.now(timezone.utc)

    first = policy.after_failure(attempts_done=1, max_attempts=5)
    second = policy.after_failure(attempts_done=2, max_attempts=5)

    assert first.status is DeliveryStatus.retry_scheduled
    assert second.status is DeliveryStatus.retry_scheduled
    first_delay = (first.next_attempt_at - before).total_seconds()
    second_delay = (second.next_attempt_at - before).total_seconds()
    assert first_delay < second_delay


def test_backoff_is_capped():
    policy = RetryPolicy(base_seconds=60, cap_seconds=120)
    before = datetime.now(timezone.utc)
    decision = policy.after_failure(attempts_done=4, max_attempts=10)
    delay = (decision.next_attempt_at - before).total_seconds()
    assert delay <= 121


def test_exhausted_budget_fails_terminally():
    policy = RetryPolicy(base_seconds=60, cap_seconds=3600)
    decision = policy.after_failure(attempts_done=5, max_attempts=5)
    assert decision.status is DeliveryStatus.failed
    assert decision.next_attempt_at is None
    assert decision.status in DeliveryStatus.terminal()
