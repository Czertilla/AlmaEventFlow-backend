from logging import getLogger
from uuid import UUID

from core.dto.base import dto_from_orm
from core.service.base import BaseService
from notify.dto.client import ClientCreateDTO, ClientDTO
from notify.exc import ClientNotExistsException, TransportNotSupportedException
from notify.transport import registry
from notify.uow.client import ClientUOW

logger = getLogger(__name__)


class ClientService(BaseService[ClientUOW]):
    async def list_my(self, user_id: UUID) -> list[ClientDTO]:
        async with self.uow as uow:
            rows = await uow.clients.get_by_user(user_id)
            return [dto_from_orm(row, ClientDTO) for row in rows]

    async def register(self, user_id: UUID, data: ClientCreateDTO) -> ClientDTO:
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
                if row is None:
                    raise ClientNotExistsException()
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
            result = dto_from_orm(row, ClientDTO)
            await uow.commit()
        return result

    async def delete(self, user_id: UUID, client_id: UUID) -> None:
        async with self.uow as uow:
            existing = await uow.clients.get_by_id(client_id)
            if existing is None or existing.user_id != user_id:
                raise ClientNotExistsException()
            await uow.clients.delete_one(client_id)
            await uow.commit()
