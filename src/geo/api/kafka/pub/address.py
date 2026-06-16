from uuid import UUID

from core.broker.kafka import broker, KafkaRouter
from core.enum.topic import AddressTopic
from core.schema.message.geo import (
    AddressCreatedEvent,
    AddressData,
    AddressUpdatedEvent,
    AddressDeletedEvent,
)

router = KafkaRouter()

@router.publisher(AddressTopic.CREATED)
async def on_address_created(addresses: list[AddressData]):
    await broker.publish(AddressCreatedEvent(data=addresses), AddressTopic.CREATED)

@router.publisher(AddressTopic.UPDATED)
async def on_address_updated(addresses: list[AddressData]):
    await broker.publish(AddressUpdatedEvent(data=addresses), AddressTopic.UPDATED)

@router.publisher(AddressTopic.DELETED)
async def on_address_deleted(address_ids: list[UUID]):
    await broker.publish(
        AddressDeletedEvent(data=[{"id": address_id} for address_id in address_ids]),
        AddressTopic.DELETED,
    )