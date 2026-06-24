from faststream import Depends

from core.broker.kafka import KafkaRouter
from core.dependencies.uow import ModuleUOWDep
from core.enum.topic import AccountTopic
from core.schema.message.user import (
    AccountCreatedEvent,
    AccountDeletedEvent,
    AccountEmailVerifiedEvent,
    AccountUpdatedEvent,
)

from notify.service.account import AccountEventService
from notify.uow.account import AccountUOW

router = KafkaRouter()

AccountUOWDep = Depends(ModuleUOWDep("notify")(AccountUOW))


@router.subscriber(AccountTopic.CREATED)
async def on_account_created(event: AccountCreatedEvent, uow=AccountUOWDep):
    await AccountEventService(uow).create(event.data)


@router.subscriber(AccountTopic.UPDATED)
async def on_account_updated(event: AccountUpdatedEvent, uow=AccountUOWDep):
    await AccountEventService(uow).update(event.data)


@router.subscriber(AccountTopic.EMAIL_VERIFIED)
async def on_account_email_verified(
    event: AccountEmailVerifiedEvent, uow=AccountUOWDep
):
    await AccountEventService(uow).mark_verified(event.data)


@router.subscriber(AccountTopic.DELETED)
async def on_account_deleted(event: AccountDeletedEvent, uow=AccountUOWDep):
    await AccountEventService(uow).delete(event.data)
