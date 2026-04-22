from core.broker.kafka import broker, KafkaRouter
from core.enum.topic import LocationTopic
from core.schema.message.geo import (
    LocationCreatedEvent,
    LocationData,
    LocationDelete,
    LocationUpdatedEvent,
    LocationDeletedEvent,
)

router = KafkaRouter()


@router.publisher(LocationTopic.CREATED)
async def on_location_created(location: LocationData):
    await broker.publish(
        LocationCreatedEvent(data=location), LocationTopic.CREATED
    )


@router.publisher(LocationTopic.UPDATED)
async def on_location_updated(location: LocationData):
    await broker.publish(
        LocationUpdatedEvent(data=location), LocationTopic.UPDATED
    )


@router.publisher(LocationTopic.DELETED)
async def on_location_deleted(location_id: LocationDelete):
    await broker.publish(
        LocationDeletedEvent(data={"id": location_id}), LocationTopic.DELETED
    )
