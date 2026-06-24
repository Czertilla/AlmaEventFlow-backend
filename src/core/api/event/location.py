from faststream import Depends
from core.broker.kafka import KafkaRouter
from core.dependencies.sqlalchemy import UOWDep
from core.enum.topic import LocationTopic
from core.schema.message.geo import (
    LocationCreatedEvent,
    LocationUpdatedEvent,
    LocationDeletedEvent,
)
from core.service.event.location import LocationEventService
from core.uow.event.location import LocationAUOW


def get_location_event_router(
    service_cls: type[LocationEventService], uow_dep: UOWDep
) -> KafkaRouter:
    router = KafkaRouter()

    LocationUOWDep: LocationAUOW = Depends(uow_dep)
    LocationService = service_cls

    @router.subscriber(LocationTopic.CREATED)
    async def on_location_created(
        event: LocationCreatedEvent, uow=LocationUOWDep
    ):
        await LocationService(uow).create(event.data)

    @router.subscriber(LocationTopic.UPDATED)
    async def on_location_updated(
        event: LocationUpdatedEvent, uow=LocationUOWDep
    ):
        await LocationService(uow).update(event.data)

    @router.subscriber(LocationTopic.DELETED)
    async def on_location_deleted(
        event: LocationDeletedEvent, uow=LocationUOWDep
    ):
        await LocationService(uow).delete(event.data)

    return router
