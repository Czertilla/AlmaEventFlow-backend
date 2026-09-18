from fastapi import Depends

from bot.service.account import AccountEventService
from bot.uow.user import UserUOW
from core.broker.kafka import KafkaRouter
from core.dependencies.redis import redis
from core.dependencies.uow import ModuleUOWDep
from core.enum.topic import AccountTopic
from core.schema.message.user import (
    AccountCreatedEvent,
    AccountUpdatedEvent,
    TelegramLinkCodeIssuedEvent,
)
from core.utils.telegram_link import TELEGRAM_LINK_REDIS_PREFIX

router = KafkaRouter()

UserUOWDep = Depends(ModuleUOWDep("bot")(UserUOW))


@router.subscriber(AccountTopic.CREATED)
async def on_account_created(event: AccountCreatedEvent, uow: UserUOW = UserUOWDep):
    await AccountEventService(uow).sync(event.data)


@router.subscriber(AccountTopic.UPDATED)
async def on_account_updated(event: AccountUpdatedEvent, uow: UserUOW = UserUOWDep):
    await AccountEventService(uow).sync(event.data)


@router.subscriber(AccountTopic.TELEGRAM_LINK_CODE_ISSUED)
async def on_telegram_link_code_issued(event: TelegramLinkCodeIssuedEvent):
    for issued in event.data:
        await redis.set(
            f"{TELEGRAM_LINK_REDIS_PREFIX}{issued.code}",
            str(issued.person_id),
            ex=issued.ttl,
        )
