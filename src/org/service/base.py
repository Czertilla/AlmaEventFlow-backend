from typing import Any, ClassVar
from uuid import UUID

from core.dto.base import dto_dict, dto_from_orm
from core.dto.pagination import PageDTO, PageParamDTO, PaginationDTO
from core.schema.message.org import OrganizationData
from core.service.base import BaseService, required_transaction
from core.uow.sqlalchemy import UnitOfWork
from org.api.kafka.pub.organization import (
    on_organization_created,
    on_organization_deleted,
    on_organization_updated,
)


class OrgEntityService[U: UnitOfWork](BaseService[U]):
    """CRUD of an organization-like entity; every change is announced as an
    organization event after the commit.

    A subclass names its ORM model, DTO, filter, not-found exception and the UoW
    repository (``repo_name``). The entities are joined-table children of the
    organization, so rows are written through ORM instances, not Core inserts.
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

    @staticmethod
    def _event(entity: Any) -> OrganizationData:
        return OrganizationData(**dto_dict(entity))

    @required_transaction
    async def _create(self, create: Any) -> Any:
        return await self._repo.add_entity(self.model(**dto_dict(create)))

    @required_transaction
    async def _read(self, entity_id: UUID) -> Any:
        entity = await self._repo.get_by_id(entity_id)
        if entity is None:
            raise self.not_found()
        return entity

    @required_transaction
    async def _update(self, entity_id: UUID, data: dict[str, Any]) -> Any:
        # merge() on a transient partial instance would null out unpatched columns
        entity = await self._read(entity_id)
        for key, value in data.items():
            setattr(entity, key, value)
        return await self._repo.add_entity(entity)

    @required_transaction
    async def _upsert(self, put: Any) -> Any:
        entity = await self._repo.get_by_id(put.id)
        data = dto_dict(put, exclude={"id"})
        if entity is None:
            entity = self.model(id=put.id, **data)
        else:
            for key, value in data.items():
                setattr(entity, key, value)
        return await self._repo.add_entity(entity)

    @required_transaction
    async def _delete(self, entity_id: UUID) -> None:
        await self._repo.delete_one(entity_id)

    @required_transaction
    async def _search(
        self, filter: Any, pagination: PageParamDTO
    ) -> PageDTO[Any]:
        items, total = await self._repo.search(
            self.filter_cls.from_dto(filter), pagination
        )
        return PageDTO(
            items=[self._to_dto(item) for item in items],
            pagination=PaginationDTO(
                page=pagination.page, limit=pagination.limit, total=total
            ),
        )

    async def create(self, create: Any) -> Any:
        async with self.uow as uow:
            result = self._to_dto(await self._create(create))
            await uow.commit()
        await on_organization_created([self._event(result)])
        return result

    async def read(self, entity_id: UUID) -> Any:
        async with self.uow:
            return self._to_dto(await self._read(entity_id))

    async def patch(self, patch: Any) -> Any:
        async with self.uow as uow:
            data = dto_dict(patch, only_set=True, exclude={"id"})
            result = self._to_dto(await self._update(patch.id, data))
            await uow.commit()
        await on_organization_updated([self._event(result)])
        return result

    async def put(self, put: Any) -> Any:
        async with self.uow as uow:
            result = self._to_dto(await self._upsert(put))
            await uow.commit()
        await on_organization_updated([self._event(result)])
        return result

    async def search(self, filter: Any, pagination: PageParamDTO) -> PageDTO[Any]:
        async with self.uow:
            return await self._search(filter, pagination)

    async def delete(self, entity_id: UUID) -> None:
        async with self.uow as uow:
            await self._delete(entity_id)
            await uow.commit()
        await on_organization_deleted([entity_id])
