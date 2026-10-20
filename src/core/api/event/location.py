from fastapi import Depends

from core.broker.kafka import KafkaRouter
from core.dependencies.sqlalchemy import UOWDep
from core.enum.topic import LocationTopic
from core.schema.message.geo import (
    LocationCreatedEvent,
    LocationDeletedEvent,
    LocationUpdatedEvent,
)
from core.service.event.location import LocationEventService
from core.uow.event.location import LocationAUOW


def get_location_event_router(
    service_cls: type[LocationEventService], uow_dep: UOWDep
) -> KafkaRouter:
    router = KafkaRouter()

    location_uow: LocationAUOW = Depends(uow_dep)
    location_service = service_cls

    @router.subscriber(LocationTopic.CREATED)
    async def on_location_created(
        event: LocationCreatedEvent, uow=location_uow
    ):
        await location_service(uow).create(event.data)

    @router.subscriber(LocationTopic.UPDATED)
    async def on_location_updated(
        event: LocationUpdatedEvent, uow=location_uow
    ):
        await location_service(uow).update(event.data)

    @router.subscriber(LocationTopic.DELETED)
    async def on_location_deleted(
        event: LocationDeletedEvent, uow=location_uow
    ):
        await location_service(uow).delete(event.data)

    return router
