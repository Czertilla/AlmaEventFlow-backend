from logging import getLogger
from uuid import UUID

from core.service.base import BaseService

from notify.exc import ClientNotExistsException, TransportNotSupportedException
from notify.schema.client import ClientCreate, ClientRead
from notify.transport import registry
from notify.uow.client import ClientUOW

logger = getLogger(__name__)


class ClientService(BaseService[ClientUOW]):
    async def list_my(self, user_id: UUID) -> list[ClientRead]:
        async with self.uow as uow:
            rows = await uow.clients.get_by_user(user_id)
            return [ClientRead.model_validate(row) for row in rows]

    async def register(self, user_id: UUID, data: ClientCreate) -> ClientRead:
        transport = registry.get(data.transport)
        if transport is None:
            raise TransportNotSupportedException()
        payload = transport.validate_client_payload(data.payload)
        async with self.uow as uow:
            existing = await uow.clients.get_by_endpoint(
                user_id, data.transport, data.endpoint
            )
            if existing is not None:
                row = await uow.clients.update_one(
                    existing.id,
                    {
                        "payload": payload,
                        "label": data.label,
                        "is_active": True,
                    },
                )
            else:
                row = await uow.clients.add_n_return(
                    {
                        "user_id": user_id,
                        "transport": data.transport,
                        "endpoint": data.endpoint,
                        "label": data.label,
                        "payload": payload,
                        "is_active": True,
                    }
                )
            await uow.commit()
        return ClientRead.model_validate(row)

    async def delete(self, user_id: UUID, client_id: UUID) -> None:
        async with self.uow as uow:
            existing = await uow.clients.get_by_id(client_id)
            if existing is None or existing.user_id != user_id:
                raise ClientNotExistsException()
            await uow.clients.delete_one(client_id)
            await uow.commit()
