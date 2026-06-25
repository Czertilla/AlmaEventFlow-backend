from logging import getLogger
from uuid import UUID

from pydantic import EmailStr

from core.broker.kafka import broker
from core.enum.topic import AccountTopic
from core.schema.message.user import (
    AccountCreatedEvent,
    AccountData,
    AccountDelete,
    AccountDeletedEvent,
    AccountEmailVerifiedEvent,
    AccountUpdatedEvent,
    AccountVerified,
)

logger = getLogger(__name__)


async def publish_account_created(
    user_id: UUID,
    email: EmailStr,
    is_verified: bool = False,
    person_id: UUID | None = None,
) -> None:
    logger.debug("Publishing account.created for %s", user_id)
    await broker.publish(
        AccountCreatedEvent(
            data=[
                AccountData(
                    id=user_id,
                    email=email,
                    is_verified=is_verified,
                    person_id=person_id,
                )
            ]
        ),
        AccountTopic.CREATED,
    )


async def publish_account_updated(
    user_id: UUID,
    email: EmailStr,
    is_verified: bool,
    person_id: UUID | None = None,
) -> None:
    logger.debug("Publishing account.updated for %s", user_id)
    await broker.publish(
        AccountUpdatedEvent(
            data=[
                AccountData(
                    id=user_id,
                    email=email,
                    is_verified=is_verified,
                    person_id=person_id,
                )
            ]
        ),
        AccountTopic.UPDATED,
    )


async def publish_account_email_verified(user_id: UUID) -> None:
    logger.debug("Publishing account.email_verified for %s", user_id)
    await broker.publish(
        AccountEmailVerifiedEvent(data=[AccountVerified(id=user_id)]),
        AccountTopic.EMAIL_VERIFIED,
    )


async def publish_account_deleted(user_id: UUID) -> None:
    logger.debug("Publishing account.deleted for %s", user_id)
    await broker.publish(
        AccountDeletedEvent(data=[AccountDelete(id=user_id)]),
        AccountTopic.DELETED,
    )
