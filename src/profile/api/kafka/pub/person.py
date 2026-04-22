from core.broker.kafka import broker, KafkaRouter
from core.enum.topic import PersonTopic
from core.schema.message.profile import (
    PersonCreatedEvent,
    PersonData,
    PersonDelete,
    PersonUpdatedEvent,
    PersonDeletedEvent,
)

router = KafkaRouter()

@router.publisher(PersonTopic.CREATED)
async def on_person_created(person: PersonData):
    await broker.publish(PersonCreatedEvent(data=person), PersonTopic.CREATED)

@router.publisher(PersonTopic.UPDATED)
async def on_person_updated(person: PersonData):
    await broker.publish(PersonUpdatedEvent(data=person), PersonTopic.UPDATED)

@router.publisher(PersonTopic.DELETED)
async def on_person_deleted(person_id: PersonDelete):
    await broker.publish(
        PersonDeletedEvent(data={"id": person_id}), PersonTopic.DELETED
    )
