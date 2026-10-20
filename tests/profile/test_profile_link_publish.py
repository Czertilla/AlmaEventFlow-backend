from typing import Any
from uuid import UUID, uuid4

import pytest

from core.enum.topic import PersonTopic
from core.schema.message.profile import PersonLinkChangedEvent, PersonLinkData

Sent =list[tuple[PersonLinkChangedEvent, str, Any]]


@pytest.fixture
def sent(monkeypatch: pytest.MonkeyPatch) -> Sent:
    messages: Sent = []

    async def publish(
        message: PersonLinkChangedEvent, topic: str, **kwargs: Any
    ) -> None:
        messages.append((message, topic, kwargs.get("key")))

    monkeypatch.setattr("profile.api.kafka.pub.person.broker.publish", publish)
    return messages


def _pairs(message: PersonLinkChangedEvent) -> list[tuple[UUID, UUID | None]]:
    return [(link.user_id, link.person_id) for link in message.data]


async def test_a_link_is_published_under_its_account_key(sent: Sent) -> None:
    from profile.api.kafka.pub.person import on_person_link_changed

    user_id, person_id = uuid4(), uuid4()

    await on_person_link_changed([PersonLinkData(user_id=user_id, person_id=person_id)])

    assert len(sent) == 1
    message, topic, key = sent[0]
    assert topic == PersonTopic.LINK_CHANGED
    assert key == str(user_id).encode()
    assert _pairs(message) == [(user_id, person_id)]


async def test_a_batch_is_split_per_account_and_keeps_the_order_of_each(
    sent: Sent,
) -> None:
    from profile.api.kafka.pub.person import on_person_link_changed

    first, second = uuid4(), uuid4()
    person_a, person_b = uuid4(), uuid4()

    await on_person_link_changed(
        [
            PersonLinkData(user_id=first, person_id=person_a),
            PersonLinkData(user_id=second, person_id=person_b),
            PersonLinkData(user_id=first, person_id=None),
        ]
    )

    assert [key for _, _, key in sent] == [str(first).encode(), str(second).encode()]
    assert [_pairs(message) for message, _, _ in sent] == [
        [(first, person_a), (first, None)],
        [(second, person_b)],
    ]
