from uuid import UUID

from core.broker.kafka import KafkaRouter, broker
from core.enum.topic import PersonTopic
from core.schema.message.profile import (
    PersonCreatedEvent,
    PersonData,
    PersonDeletedEvent,
    PersonUpdatedEvent,
)

router = KafkaRouter()

@router.publisher(PersonTopic.CREATED)
async def on_person_created(persons: list[PersonData]):
    await broker.publish(PersonCreatedEvent(data=persons), PersonTopic.CREATED)

@router.publisher(PersonTopic.UPDATED)
async def on_person_updated(persons: list[PersonData]):
    await broker.publish(PersonUpdatedEvent(data=persons), PersonTopic.UPDATED)

@router.publisher(PersonTopic.DELETED)
async def on_person_deleted(person_ids: list[UUID]):
    await broker.publish(
        PersonDeletedEvent(data=[{"id": person_id} for person_id in person_ids]),
        PersonTopic.DELETED,
    )
