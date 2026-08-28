from faststream import Depends

from core.broker.kafka import KafkaRouter
from core.broker.rpc import rpc_respond
from core.enum.rpc import NotifyRPC
from core.schema.message.core import Ack, MQResponse
from core.schema.message.notify import (
    ClientData,
    DeregisterClientRequest,
    GetPreferencesRequest,
    PreferenceItemData,
    PreferencesData,
    RegisterClientRequest,
    SetPreferencesRequest,
)
from notify.dependency._uow import UOWDep
from notify.schema.client import ClientCreate
from notify.schema.preference import PreferenceItem, PreferencesUpdate
from notify.service.client import ClientService
from notify.service.preference import PreferenceService
from notify.uow.client import ClientUOW
from notify.uow.preference import PreferenceUOW

router = KafkaRouter()

ClientUOWDep = Depends(UOWDep(ClientUOW))
PreferenceUOWDep = Depends(UOWDep(PreferenceUOW))


@router.subscriber(NotifyRPC.REGISTER_CLIENT)
async def on_register_client(
    request: RegisterClientRequest, uow=ClientUOWDep
) -> MQResponse[ClientData]:
    async def _call() -> ClientData:
        client = await ClientService(uow).register(
            request.user_id,
            ClientCreate(
                transport=request.transport,
                endpoint=request.endpoint,
                label=request.label,
                payload=request.payload,
            ),
        )
        return ClientData.model_validate(client)

    return await rpc_respond(_call())


@router.subscriber(NotifyRPC.DEREGISTER_CLIENT)
async def on_deregister_client(
    request: DeregisterClientRequest, uow=ClientUOWDep
) -> MQResponse[Ack]:
    async def _call() -> Ack:
        await ClientService(uow).delete(request.user_id, request.client_id)
        return Ack()

    return await rpc_respond(_call())


@router.subscriber(NotifyRPC.GET_PREFERENCES)
async def on_get_preferences(
    request: GetPreferencesRequest, uow=PreferenceUOWDep
) -> MQResponse[PreferencesData]:
    async def _call() -> PreferencesData:
        prefs = await PreferenceService(uow).get_my(request.user_id)
        return PreferencesData(
            preferences=[
                PreferenceItemData.model_validate(p) for p in prefs.preferences
            ]
        )

    return await rpc_respond(_call())


@router.subscriber(NotifyRPC.SET_PREFERENCES)
async def on_set_preferences(
    request: SetPreferencesRequest, uow=PreferenceUOWDep
) -> MQResponse[PreferencesData]:
    async def _call() -> PreferencesData:
        update = PreferencesUpdate(
            preferences=[
                PreferenceItem(transport=item.transport, is_enabled=item.is_enabled)
                for item in request.preferences
            ]
        )
        prefs = await PreferenceService(uow).set_my(request.user_id, update)
        return PreferencesData(
            preferences=[
                PreferenceItemData.model_validate(p) for p in prefs.preferences
            ]
        )

    return await rpc_respond(_call())
