from faststream import Depends

from core.broker.kafka import KafkaRouter
from core.dependencies.sqlalchemy import UOWDep
from core.enum.topic import OrganizationTopic
from core.schema.message.org import (
    OrganizationCreatedEvent,
    OrganizationUpdatedEvent,
    OrganizationDeletedEvent,
)
from core.service.event.organization import OrganizationEventService
from core.uow.event.organization import OrganizationAUOW


def get_organization_event_router(
    service_cls: type[OrganizationEventService], uow_dep: UOWDep
) -> KafkaRouter:
    router = KafkaRouter()

    OrganizationUOWDep: OrganizationAUOW = Depends(uow_dep)
    OrganizationService = service_cls

    @router.subscriber(OrganizationTopic.CREATED)
    async def on_organization_created(
        event: OrganizationCreatedEvent, uow=OrganizationUOWDep
    ):
        await OrganizationService(uow).create(event.data)

    @router.subscriber(OrganizationTopic.UPDATED)
    async def on_organization_updated(
        event: OrganizationUpdatedEvent, uow=OrganizationUOWDep
    ):
        await OrganizationService(uow).update(event.data)

    @router.subscriber(OrganizationTopic.DELETED)
    async def on_organization_deleted(
        event: OrganizationDeletedEvent, uow=OrganizationUOWDep
    ):
        await OrganizationService(uow).delete(event.data)

    return router
