from logging import getLogger
from uuid import UUID

from core.service.base import BaseService, required_transaction
from event.models.role import RoleORM
from event.schema.role import (
    RoleCreate,
    RolePatch,
    RolePut,
    RoleRead,
)
from event.uow.role import RoleUOW

logger = getLogger(__name__)


class RoleService(BaseService[RoleUOW]):
    @required_transaction
    async def _create(self, role_create: RoleCreate) -> RoleORM:
        role_data = role_create.model_dump()
        role = await self.uow.roles.add_n_return(data=role_data)
        await self.uow.session.flush(objects=[role])
        return role

    @required_transaction
    async def _read(self, role_id: UUID) -> RoleORM | None:
        role = await self.uow.roles.get_by_id(role_id)
        return role

    @required_transaction
    async def _update(
        self, role_id: UUID, role_data: dict, *, flush: bool = False
    ) -> RoleORM:
        role = await self.uow.roles.update_one(role_id, role_data, flush)
        return role

    @required_transaction
    async def _delete(self, role_id: UUID) -> None:
        await self.uow.roles.delete_one(role_id)

    async def create(self, role_create: RoleCreate) -> RoleRead:
        async with self.uow as uow:
            role = await self._create(role_create)
            result = RoleRead.model_validate(role)
            await uow.commit()
        return result

    async def read(self, role_id: UUID) -> RoleRead:
        async with self.uow:
            role = await self._read(role_id)
            return RoleRead.model_validate(role)

    async def patch(self, role_patch: RolePatch) -> RoleRead:
        async with self.uow as uow:
            role_data = role_patch.model_dump(exclude_unset=True)
            role = await self._update(role_patch.id, role_data)
            result = RoleRead.model_validate(role)
            await uow.commit()
        return result

    async def put(self, role_put: RolePut) -> RoleRead:
        async with self.uow as uow:
            role_data = role_put.model_dump()
            role_id = role_data.pop("id")
            role = await self._update(role_id, role_data)
            result = RoleRead.model_validate(role)
            await uow.commit()
        return result

    async def delete(self, role_id: UUID) -> None:
        async with self.uow as uow:
            await self._delete(role_id)
            await uow.commit()
