from profile.dependency._uow import UOWDep
from profile.uow.person import PersonUOW

from fastapi import Depends

from core.broker.kafka import KafkaRouter
from core.broker.rpc import rpc_respond
from core.enum.rpc import ProfileRPC
from core.schema.message.core import Ack, MQResponse
from core.schema.message.profile import LinkAccountRequest

router = KafkaRouter()

PersonUOWDep = Depends(UOWDep(PersonUOW))


@router.subscriber(ProfileRPC.LINK_ACCOUNT)
async def on_link_account(
    request: LinkAccountRequest, uow: PersonUOW = PersonUOWDep
) -> MQResponse[Ack]:
    from profile.service.account import PersonAccountService

    async def _call() -> Ack:
        await PersonAccountService(uow).link(
            request.user_id, request.person_id, replace=request.replace
        )
        return Ack()

    return await rpc_respond(_call())
