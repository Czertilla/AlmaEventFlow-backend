from fastapi import Depends
from core.broker.kafka import KafkaRouter
from core.dependencies.sqlalchemy import UOWDep
from core.enum.topic import AddressTopic
from core.schema.message.geo import (
    AddressCreatedEvent,
    AddressUpdatedEvent,
    AddressDeletedEvent,
)
from core.service.event.address import AddressEventService
from core.uow.event.address import AddressAUOW


def get_address_event_router(
    service_cls: type[AddressEventService], uow_dep: UOWDep
) -> KafkaRouter:
    router = KafkaRouter()

    AddressUOWDep: AddressAUOW = Depends(UOWDep(uow_dep))
    AddressService = service_cls

    @router.subscriber(AddressTopic.CREATED)
    async def on_address_created(event: AddressCreatedEvent, uow=AddressUOWDep):
        await AddressService(uow).create(event.data)

    @router.subscriber(AddressTopic.UPDATED)
    async def on_address_updated(event: AddressUpdatedEvent, uow=AddressUOWDep):
        await AddressService(uow).update(event.data)

    @router.subscriber(AddressTopic.DELETED)
    async def on_address_deleted(event: AddressDeletedEvent, uow=AddressUOWDep):
        await AddressService(uow).delete(event.data)

    return router
