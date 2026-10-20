from fastapi import Depends

from core.broker.kafka import KafkaRouter
from core.dependencies.sqlalchemy import UOWDep
from core.enum.topic import OrganizationTopic
from core.schema.message.org import (
    OrganizationCreatedEvent,
    OrganizationDeletedEvent,
    OrganizationUpdatedEvent,
)
from core.service.event.organization import OrganizationEventService
from core.uow.event.organization import OrganizationAUOW


def get_organization_event_router[U: OrganizationAUOW](
    service_cls: type[OrganizationEventService[U]], uow_dep: UOWDep
) -> KafkaRouter:
    router = KafkaRouter()

    organization_uow: U = Depends(uow_dep)
    organization_service = service_cls

    @router.subscriber(OrganizationTopic.CREATED)
    async def on_organization_created(
        event: OrganizationCreatedEvent, uow: U = organization_uow
    ):
        await organization_service(uow).create(event.data)

    @router.subscriber(OrganizationTopic.UPDATED)
    async def on_organization_updated(
        event: OrganizationUpdatedEvent, uow: U = organization_uow
    ):
        await organization_service(uow).update(event.data)

    @router.subscriber(OrganizationTopic.DELETED)
    async def on_organization_deleted(
        event: OrganizationDeletedEvent, uow: U = organization_uow
    ):
        await organization_service(uow).delete(event.data)

    return router
