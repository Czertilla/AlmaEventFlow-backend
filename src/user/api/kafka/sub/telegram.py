from faststream import Depends

from core.broker.kafka import KafkaRouter
from core.broker.rpc import rpc_respond
from core.dependencies.uow import ModuleUOWDep
from core.enum.rpc import UserRPC
from core.schema.message.core import Ack, MQResponse
from core.schema.message.user import (
    LinkTelegramOAuthRequest,
    ResolveUserIdRequest,
    UnlinkTelegramOAuthRequest,
    UserIdResponse,
)
from user.exceptions.user import UserNotFound
from user.services.user import UserService
from user.uow.user import UserUOW

router = KafkaRouter()

UserUOWDep = Depends(ModuleUOWDep("user")(UserUOW))


@router.subscriber(UserRPC.RESOLVE_USER_ID)
async def on_resolve_user_id(
    request: ResolveUserIdRequest, uow=UserUOWDep
) -> MQResponse[UserIdResponse]:
    async def _call() -> UserIdResponse:
        user = await UserService(uow).get_by_person_id(request.person_id)
        if user is None:
            raise UserNotFound()
        return UserIdResponse(user_id=user.id)

    return await rpc_respond(_call())


@router.subscriber(UserRPC.LINK_TELEGRAM_OAUTH)
async def on_link_telegram_oauth(
    request: LinkTelegramOAuthRequest, uow=UserUOWDep
) -> MQResponse[Ack]:
    async def _call() -> Ack:
        await UserService(uow).link_telegram_oauth(
            request.person_id, request.telegram_id, request.username
        )
        return Ack()

    return await rpc_respond(_call())


@router.subscriber(UserRPC.UNLINK_TELEGRAM_OAUTH)
async def on_unlink_telegram_oauth(
    request: UnlinkTelegramOAuthRequest, uow=UserUOWDep
) -> MQResponse[Ack]:
    async def _call() -> Ack:
        await UserService(uow).unlink_telegram_oauth(request.person_id)
        return Ack()

    return await rpc_respond(_call())
