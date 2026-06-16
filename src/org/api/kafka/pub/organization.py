from uuid import UUID

from core.broker.kafka import broker, KafkaRouter
from core.enum.topic import OrganizationTopic
from core.schema.message.org import (
    OrganizationCreatedEvent,
    OrganizationData,
    OrganizationUpdatedEvent,
    OrganizationDeletedEvent,
)

router = KafkaRouter()


@router.publisher(OrganizationTopic.CREATED)
async def on_organization_created(organizations: list[OrganizationData]):
    await broker.publish(
        OrganizationCreatedEvent(data=organizations), OrganizationTopic.CREATED
    )


@router.publisher(OrganizationTopic.UPDATED)
async def on_organization_updated(organizations: list[OrganizationData]):
    await broker.publish(
        OrganizationUpdatedEvent(data=organizations), OrganizationTopic.UPDATED
    )


@router.publisher(OrganizationTopic.DELETED)
async def on_organization_deleted(organization_ids: list[UUID]):
    await broker.publish(
        OrganizationDeletedEvent(
            data=[{"id": organization_id} for organization_id in organization_ids]
        ),
        OrganizationTopic.DELETED,
    )
