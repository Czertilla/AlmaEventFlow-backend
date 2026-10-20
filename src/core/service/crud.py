from typing import Any, ClassVar
from uuid import UUID

from core.dto.base import dto_dict, dto_from_orm
from core.dto.pagination import PageDTO, PageParamDTO, PaginationDTO
from core.service.base import BaseService, required_transaction
from core.uow.sqlalchemy import UnitOfWork


class CRUDService[U: UnitOfWork](BaseService[U]):
    """Plain CRUD over one repository of the UoW (``repo_name``).

    A subclass names its model, DTO, filter and not-found exception, and adds
    whatever its entity does beyond storing rows. Unlike ``OrgEntityService``
    nothing is announced to other services.
    """

    model: ClassVar[type[Any]]
    dto: ClassVar[type[Any]]
    filter_cls: ClassVar[type[Any]]
    not_found: ClassVar[type[Exception]]
    repo_name: ClassVar[str]

    @property
    def _repo(self) -> Any:
        return getattr(self.uow, self.repo_name)

    def _to_dto(self, entity: Any) -> Any:
        return dto_from_orm(entity, self.dto)

    @required_transaction
    async def _create(self, create: Any) -> Any:
        return await self._repo.add_n_return(data=dto_dict(create))

    @required_transaction
    async def _read(self, entity_id: UUID) -> Any | None:
        return await self._repo.get_by_id(entity_id)

    @required_transaction
    async def _update(
        self, entity_id: UUID, data: dict[str, Any], *, flush: bool = False
    ) -> Any:
        entity = await self._repo.update_one(entity_id, data, flush)
        if entity is None:
            raise self.not_found()
        return entity

    @required_transaction
    async def _delete(self, entity_id: UUID) -> None:
        await self._repo.delete_one(entity_id)

    async def create(self, create: Any) -> Any:
        async with self.uow as uow:
            result = self._to_dto(await self._create(create))
            await uow.commit()
        return result

    async def read(self, entity_id: UUID) -> Any:
        async with self.uow:
            entity = await self._read(entity_id)
            if entity is None:
                raise self.not_found()
            return self._to_dto(entity)

    async def patch(self, patch: Any) -> Any:
        async with self.uow as uow:
            data = dto_dict(patch, only_set=True)
            result = self._to_dto(await self._update(patch.id, data))
            await uow.commit()
        return result

    async def put(self, put: Any) -> Any:
        async with self.uow as uow:
            data = dto_dict(put, exclude={"id"})
            result = self._to_dto(await self._update(put.id, data))
            await uow.commit()
        return result

    async def delete(self, entity_id: UUID) -> None:
        async with self.uow as uow:
            await self._delete(entity_id)
            await uow.commit()

    async def search(
        self, filter: Any, page_params: PageParamDTO = PageParamDTO()
    ) -> PageDTO[Any]:
        async with self.uow:
            items, total = await self._repo.search(
                self.filter_cls.from_dto(filter), page_params
            )
            return PageDTO(
                items=[self._to_dto(item) for item in items],
                pagination=PaginationDTO(
                    page=page_params.page, limit=page_params.limit, total=total
                ),
            )
