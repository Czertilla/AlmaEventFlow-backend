from logging import getLogger
from uuid import UUID

from core.dto.base import dto_dict, dto_from_orm
from core.dto.pagination import PageDTO, PageParamDTO, PaginationDTO
from core.service.base import BaseService, required_transaction
from event.dto.role import (
    RoleCreateDTO,
    RoleDTO,
    RoleFilterDTO,
    RolePatchDTO,
    RolePutDTO,
)
from event.filter.role import RoleFilter
from event.models.role import RoleORM
from event.uow.role import RoleUOW

logger = getLogger(__name__)


class RoleService(BaseService[RoleUOW]):
    @staticmethod
    def _to_dto(role: RoleORM) -> RoleDTO:
        return dto_from_orm(role, RoleDTO)

    @required_transaction
    async def _create(self, role_create: RoleCreateDTO) -> RoleORM:
        role_data = dto_dict(role_create)
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

    async def create(self, role_create: RoleCreateDTO) -> RoleDTO:
        async with self.uow as uow:
            role = await self._create(role_create)
            result = self._to_dto(role)
            await uow.commit()
        return result

    async def read(self, role_id: UUID) -> RoleDTO:
        async with self.uow:
            role = await self._read(role_id)
            return self._to_dto(role)

    async def patch(self, role_patch: RolePatchDTO) -> RoleDTO:
        async with self.uow as uow:
            role_data = dto_dict(role_patch, only_set=True)
            role = await self._update(role_patch.id, role_data)
            result = self._to_dto(role)
            await uow.commit()
        return result

    async def put(self, role_put: RolePutDTO) -> RoleDTO:
        async with self.uow as uow:
            role_data = dto_dict(role_put, exclude={"id"})
            role = await self._update(role_put.id, role_data)
            result = self._to_dto(role)
            await uow.commit()
        return result

    async def delete(self, role_id: UUID) -> None:
        async with self.uow as uow:
            await self._delete(role_id)
            await uow.commit()

    async def search(
        self, filter: RoleFilterDTO, page_params: PageParamDTO = PageParamDTO()
    ) -> PageDTO[RoleDTO]:
        async with self.uow as uow:
            orm_filter = RoleFilter.from_dto(filter)
            items, total = await uow.roles.search(orm_filter, page_params)
            return PageDTO(
                items=[self._to_dto(item) for item in items],
                pagination=PaginationDTO(
                    page=page_params.page, limit=page_params.limit, total=total
                ),
            )
