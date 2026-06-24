from uuid import uuid4

import pytest

from core.enum.notify import NotificationCategory, TransportTypeEnum
from notify.config.settings import settings
from notify.schema.account import AccountRead
from notify.schema.client import ClientTarget
from notify.schema.notification import NotificationContent
from notify.service.batching import build_outbox_rows, chunked
from notify.transport.base import DeliveryDraft, DeliveryTarget, PlanContext

NOTIFICATION_ID = uuid4()


def _content() -> NotificationContent:
    return NotificationContent(
        title="Title",
        body="Body",
        action_url=None,
        category=NotificationCategory.system,
        data={},
    )


def _email_draft() -> DeliveryDraft:
    ctx = PlanContext(
        notification_id=NOTIFICATION_ID,
        user_id=uuid4(),
        content=_content(),
        account=AccountRead(id=uuid4(), email="user@example.com"),
        expires_at=None,
    )
    return DeliveryDraft(delivery_id=uuid4(), ctx=ctx, target=DeliveryTarget())


def _webpush_draft() -> DeliveryDraft:
    ctx = PlanContext(
        notification_id=NOTIFICATION_ID,
        user_id=uuid4(),
        content=_content(),
        account=None,
        expires_at=None,
    )
    client = ClientTarget(
        id=uuid4(),
        transport=TransportTypeEnum.webpush,
        endpoint="https://push.example/x",
        payload={"p256dh": "a", "auth": "b"},
    )
    return DeliveryDraft(
        delivery_id=uuid4(), ctx=ctx, target=DeliveryTarget(client=client)
    )


def _rows(drafts):
    return list(build_outbox_rows(NOTIFICATION_ID, drafts))


def test_chunked_splits_evenly_and_remainder():
    assert [list(c) for c in chunked(list(range(5)), 2)] == [[0, 1], [2, 3], [4]]
    assert list(chunked([], 10)) == []


def test_thirty_emails_one_batch_when_size_at_least_thirty(monkeypatch):
    monkeypatch.setattr(settings, "EMAIL_DELIVERY_BATCH_SIZE", 100)
    drafts = {TransportTypeEnum.email: [_email_draft() for _ in range(30)]}
    rows = _rows(drafts)
    assert len(rows) == 1
    payload = rows[0].payload
    assert payload["transport"] == TransportTypeEnum.email.value
    assert len(payload["delivery_ids"]) == 30
    assert len(payload["items"]) == 30


def test_seventy_emails_split_into_two_batches(monkeypatch):
    monkeypatch.setattr(settings, "EMAIL_DELIVERY_BATCH_SIZE", 50)
    drafts = {TransportTypeEnum.email: [_email_draft() for _ in range(70)]}
    rows = _rows(drafts)
    assert len(rows) == 2
    sizes = sorted(len(row.payload["delivery_ids"]) for row in rows)
    assert sizes == [20, 50]
    total = sum(len(row.payload["delivery_ids"]) for row in rows)
    assert total == 70


def test_email_batch_delivery_ids_match_items(monkeypatch):
    monkeypatch.setattr(settings, "EMAIL_DELIVERY_BATCH_SIZE", 100)
    drafts = {TransportTypeEnum.email: [_email_draft() for _ in range(3)]}
    payload = _rows(drafts)[0].payload
    item_ids = [item["delivery_id"] for item in payload["items"]]
    assert payload["delivery_ids"] == item_ids


def test_web_push_emits_one_delivery_per_batch():
    drafts = {TransportTypeEnum.webpush: [_webpush_draft() for _ in range(3)]}
    rows = _rows(drafts)
    assert len(rows) == 3
    for row in rows:
        assert row.payload["transport"] == TransportTypeEnum.webpush.value
        assert len(row.payload["delivery_ids"]) == 1
        assert "items" not in row.payload


def test_message_envelope_shape(monkeypatch):
    monkeypatch.setattr(settings, "EMAIL_DELIVERY_BATCH_SIZE", 100)
    drafts = {TransportTypeEnum.email: [_email_draft()]}
    payload = _rows(drafts)[0].payload
    for key in ("message_id", "notification_id", "transport", "delivery_ids", "created_at"):
        assert key in payload
    assert payload["notification_id"] == str(NOTIFICATION_ID)
