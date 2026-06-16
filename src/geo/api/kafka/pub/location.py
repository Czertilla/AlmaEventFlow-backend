from uuid import UUID

from core.broker.kafka import broker, KafkaRouter
from core.enum.topic import LocationTopic
from core.schema.message.geo import (
    LocationCreatedEvent,
    LocationData,
    LocationUpdatedEvent,
    LocationDeletedEvent,
)

router = KafkaRouter()


@router.publisher(LocationTopic.CREATED)
async def on_location_created(locations: list[LocationData]):
    await broker.publish(
        LocationCreatedEvent(data=locations), LocationTopic.CREATED
    )


@router.publisher(LocationTopic.UPDATED)
async def on_location_updated(locations: list[LocationData]):
    await broker.publish(
        LocationUpdatedEvent(data=locations), LocationTopic.UPDATED
    )


@router.publisher(LocationTopic.DELETED)
async def on_location_deleted(location_ids: list[UUID]):
    await broker.publish(
        LocationDeletedEvent(
            data=[{"id": location_id} for location_id in location_ids]
        ),
        LocationTopic.DELETED,
    )
