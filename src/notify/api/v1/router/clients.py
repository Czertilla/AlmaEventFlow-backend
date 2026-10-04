from uuid import UUID

from fastapi import APIRouter

from core.dependencies.auth import ActiveUserJWTDep
from core.schema.error import (
    ErrorCode,
    auth_responses,
    detail_400,
    entity_not_found_responses,
)
from notify.api.v1.schema.client import ClientCreate, ClientRead
from notify.dependency.client import ClientUOWDep
from notify.service.client import ClientService

router = APIRouter(prefix="/clients", tags=["notify"])


@router.get("/my", responses={**auth_responses()})
async def list_my_clients(
    user: ActiveUserJWTDep,
    uow: ClientUOWDep,
) -> list[ClientRead]:
    return [
        ClientRead.from_dto(client)
        for client in await ClientService(uow).list_my(user.id)
    ]


@router.post(
    "/my",
    responses={
        **auth_responses(),
        **detail_400(ErrorCode.NOTIFY_TRANSPORT_NOT_SUPPORTED),
        **detail_400(ErrorCode.WEBPUSH_CLIENT_INVALID),
    },
)
async def register_my_client(
    data: ClientCreate,
    user: ActiveUserJWTDep,
    uow: ClientUOWDep,
) -> ClientRead:
    """Registers a delivery endpoint (e.g. a browser web-push subscription)."""
    return ClientRead.from_dto(
        await ClientService(uow).register(user.id, data.to_dto())
    )


@router.delete(
    "/my/{client_id}",
    responses={**auth_responses(), **entity_not_found_responses("notify_client")},
)
async def delete_my_client(
    client_id: UUID,
    user: ActiveUserJWTDep,
    uow: ClientUOWDep,
) -> None:
    await ClientService(uow).delete(user.id, client_id)
