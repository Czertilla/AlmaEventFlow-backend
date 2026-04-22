from core.broker.kafka import broker, KafkaRouter
from core.enum.topic import AddressTopic
from core.schema.message.geo import (
    AddressCreatedEvent,
    AddressData,
    AddressDelete,
    AddressUpdatedEvent,
    AddressDeletedEvent,
)

router = KafkaRouter()

@router.publisher(AddressTopic.CREATED)
async def on_address_created(address: AddressData):
    await broker.publish(AddressCreatedEvent(data=address), AddressTopic.CREATED)

@router.publisher(AddressTopic.UPDATED)
async def on_address_updated(address: AddressData):
    await broker.publish(AddressUpdatedEvent(data=address), AddressTopic.UPDATED)

@router.publisher(AddressTopic.DELETED)
async def on_address_deleted(address_id: AddressDelete):
    await broker.publish(
        AddressDeletedEvent(data={"id": address_id}), AddressTopic.DELETED
    )