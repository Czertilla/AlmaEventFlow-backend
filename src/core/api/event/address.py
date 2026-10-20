from fastapi import Depends

from core.broker.kafka import KafkaRouter
from core.dependencies.sqlalchemy import UOWDep
from core.enum.topic import AddressTopic
from core.schema.message.geo import (
    AddressCreatedEvent,
    AddressDeletedEvent,
    AddressUpdatedEvent,
)
from core.service.event.address import AddressEventService
from core.uow.event.address import AddressAUOW


def get_address_event_router(
    service_cls: type[AddressEventService], uow_dep: UOWDep
) -> KafkaRouter:
    router = KafkaRouter()

    address_uow: AddressAUOW = Depends(uow_dep)
    address_service = service_cls

    @router.subscriber(AddressTopic.CREATED)
    async def on_address_created(event: AddressCreatedEvent, uow=address_uow):
        await address_service(uow).create(event.data)

    @router.subscriber(AddressTopic.UPDATED)
    async def on_address_updated(event: AddressUpdatedEvent, uow=address_uow):
        await address_service(uow).update(event.data)

    @router.subscriber(AddressTopic.DELETED)
    async def on_address_deleted(event: AddressDeletedEvent, uow=address_uow):
        await address_service(uow).delete(event.data)

    return router
