from fastapi import Depends

from core.broker.kafka import KafkaRouter
from core.broker.rpc import rpc_respond
from core.dependencies.uow import ModuleUOWDep
from core.enum.rpc import UserRPC
from core.schema.message.core import Ack, MQResponse
from core.schema.message.user import LinkPersonRequest
from user.service.user import UserService
from user.uow.user import UserUOW

router = KafkaRouter()

UserUOWDep = Depends(ModuleUOWDep("user")(UserUOW))


@router.subscriber(UserRPC.LINK_PERSON)
async def on_link_person(
    request: LinkPersonRequest, uow: UserUOW = UserUOWDep
) -> MQResponse[Ack]:
    async def _call() -> Ack:
        await UserService(uow).link_created_person(request.user_id, request.person_id)
        return Ack()

    return await rpc_respond(_call())
