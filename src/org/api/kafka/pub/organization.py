from core.broker.kafka import broker, KafkaRouter
from core.enum.topic import OrganizationTopic
from core.schema.message.org import (
    OrganizationCreatedEvent,
    OrganizationData,
    OrganizationDelete,
    OrganizationUpdatedEvent,
    OrganizationDeletedEvent,
)

router = KafkaRouter()


@router.publisher(OrganizationTopic.CREATED)
async def on_organization_created(organization: OrganizationData):
    await broker.publish(
        OrganizationCreatedEvent(data=organization), OrganizationTopic.CREATED
    )


@router.publisher(OrganizationTopic.UPDATED)
async def on_organization_updated(organization: OrganizationData):
    await broker.publish(
        OrganizationUpdatedEvent(data=organization), OrganizationTopic.UPDATED
    )


@router.publisher(OrganizationTopic.DELETED)
async def on_organization_deleted(organization_id: OrganizationDelete):
    await broker.publish(
        OrganizationDeletedEvent(data={"id": organization_id}),
        OrganizationTopic.DELETED,
    )
