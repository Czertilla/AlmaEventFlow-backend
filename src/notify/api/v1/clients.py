from uuid import UUID

from fastapi import APIRouter

from core.dependencies.auth import ActiveUserJWTDep
from core.schema.error import (
    ErrorCode,
    auth_responses,
    detail_400,
    entity_not_found_responses,
)

from notify.dependency.client import ClientUOWDep
from notify.schema.client import ClientCreate, ClientRead
from notify.service.client import ClientService

router = APIRouter(prefix="/clients", tags=["notify"])


@router.get("/my", responses={**auth_responses()})
async def list_my_clients(
    user: ActiveUserJWTDep,
    uow: ClientUOWDep,
) -> list[ClientRead]:
    return await ClientService(uow).list_my(user.id)


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
    return await ClientService(uow).register(user.id, data)


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
