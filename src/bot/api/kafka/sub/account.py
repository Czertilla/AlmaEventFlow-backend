from fastapi import Depends

from bot.service.account import AccountEventService
from bot.uow.user import UserUOW
from core.broker.kafka import KafkaRouter
from core.dependencies.uow import ModuleUOWDep
from core.enum.topic import AccountTopic
from core.schema.message.user import AccountCreatedEvent, AccountUpdatedEvent

router = KafkaRouter()

UserUOWDep = Depends(ModuleUOWDep("bot")(UserUOW))


@router.subscriber(AccountTopic.CREATED)
async def on_account_created(event: AccountCreatedEvent, uow: UserUOW = UserUOWDep):
    await AccountEventService(uow).sync(event.data)


@router.subscriber(AccountTopic.UPDATED)
async def on_account_updated(event: AccountUpdatedEvent, uow: UserUOW = UserUOWDep):
    await AccountEventService(uow).sync(event.data)
