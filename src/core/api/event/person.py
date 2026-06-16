

from fastapi import Depends

from core.broker.kafka import KafkaRouter
from core.dependencies.sqlalchemy import UOWDep
from core.enum.topic import PersonTopic
from core.schema.message.profile import (
    PersonCreatedEvent,
    PersonUpdatedEvent,
    PersonDeletedEvent,
)
from core.service.event.person import PersonEventService
from core.uow.event.person import PersonAUOW


def get_person_event_router(
    service_cls: type[PersonEventService], uow_depends: UOWDep
) -> KafkaRouter:
    router = KafkaRouter()

    PersonUOWDep: PersonAUOW = Depends(uow_depends)
    PersonService = service_cls

    @router.subscriber(PersonTopic.CREATED)
    async def on_person_created(event: PersonCreatedEvent, uow=PersonUOWDep):
        await PersonService(uow).create(event.data)

    @router.subscriber(PersonTopic.UPDATED)
    async def on_person_updated(event: PersonUpdatedEvent, uow=PersonUOWDep):
        await PersonService(uow).update(event.data)

    @router.subscriber(PersonTopic.DELETED)
    async def on_person_deleted(event: PersonDeletedEvent, uow=PersonUOWDep):
        await PersonService(uow).delete(event.data)

    return router
