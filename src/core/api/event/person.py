

from fastapi import Depends

from core.broker.kafka import KafkaRouter
from core.dependencies.sqlalchemy import UOWDep
from core.enum.topic import PersonTopic
from core.schema.message.profile import (
    PersonCreatedEvent,
    PersonDeletedEvent,
    PersonUpdatedEvent,
)
from core.service.event.person import PersonEventService
from core.uow.event.person import PersonAUOW


def get_person_event_router[U: PersonAUOW](
    service_cls: type[PersonEventService[U]], uow_depends: UOWDep
) -> KafkaRouter:
    router = KafkaRouter()

    person_uow: U = Depends(uow_depends)
    person_service = service_cls

    @router.subscriber(PersonTopic.CREATED)
    async def on_person_created(event: PersonCreatedEvent, uow: U = person_uow):
        await person_service(uow).create(event.data)

    @router.subscriber(PersonTopic.UPDATED)
    async def on_person_updated(event: PersonUpdatedEvent, uow: U = person_uow):
        await person_service(uow).update(event.data)

    @router.subscriber(PersonTopic.DELETED)
    async def on_person_deleted(event: PersonDeletedEvent, uow: U = person_uow):
        await person_service(uow).delete(event.data)

    return router
