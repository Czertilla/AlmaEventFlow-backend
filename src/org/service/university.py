from logging import getLogger
from typing import Any
from uuid import UUID

from core.dto.base import dto_dict, dto_from_orm
from core.dto.pagination import PageDTO, PageParamDTO, PaginationDTO
from core.schema.message.org import OrganizationData
from core.service.base import BaseService, required_transaction
from org.api.kafka.pub.organization import (
    on_organization_created,
    on_organization_deleted,
    on_organization_updated,
)
from org.dto.university import (
    UniversityCreateDTO,
    UniversityDTO,
    UniversityFilterDTO,
    UniversityPatchDTO,
    UniversityPutDTO,
)
from org.exc.university import UniversityNotExistsException
from org.filter.university import UniversityFilter
from org.models.university import UniversityORM
from org.uow.university import UniversityUOW

logger = getLogger(__name__)


class UniversityService(BaseService[UniversityUOW]):
    @staticmethod
    def _to_dto(university: UniversityORM) -> UniversityDTO:
        return dto_from_orm(university, UniversityDTO)

    @staticmethod
    def _event(university: UniversityDTO) -> OrganizationData:
        return OrganizationData(**dto_dict(university))

    @required_transaction
    async def _create(self, university_create: UniversityCreateDTO) -> UniversityORM:
        university = UniversityORM(**dto_dict(university_create))
        self.uow.session.add(university)
        await self.uow.session.flush()
        return university

    @required_transaction
    async def _read(self, university_id: UUID) -> UniversityORM:
        university = await self.uow.universities.get_by_id(university_id)
        if university is None:
            raise UniversityNotExistsException()
        return university

    @required_transaction
    async def _update(
        self,
        university_id: UUID,
        university_data: dict[str, Any],
    ) -> UniversityORM:
        # merge() on a transient partial instance would null out unpatched columns
        university = await self.uow.universities.get_by_id(university_id)
        if university is None:
            raise UniversityNotExistsException()
        for key, value in university_data.items():
            setattr(university, key, value)
        await self.uow.session.flush()
        return university

    @required_transaction
    async def _upsert(self, university_put: UniversityPutDTO) -> UniversityORM:
        university = await self.uow.universities.get_by_id(university_put.id)
        university_data = dto_dict(university_put, exclude={"id"})
        if university is None:
            university = UniversityORM(id=university_put.id, **university_data)
            self.uow.session.add(university)
        else:
            for key, value in university_data.items():
                setattr(university, key, value)
        await self.uow.session.flush()
        return university

    @required_transaction
    async def _delete(self, university_id: UUID) -> None:
        await self.uow.universities.delete_one(university_id)

    async def create(self, university_create: UniversityCreateDTO) -> UniversityDTO:
        async with self.uow as uow:
            result = self._to_dto(await self._create(university_create))
            await uow.commit()
        await on_organization_created([self._event(result)])
        return result

    async def read(self, university_id: UUID) -> UniversityDTO:
        async with self.uow:
            return self._to_dto(await self._read(university_id))

    async def patch(self, university_patch: UniversityPatchDTO) -> UniversityDTO:
        async with self.uow as uow:
            university_data = dto_dict(university_patch, only_set=True, exclude={"id"})
            result = self._to_dto(
                await self._update(university_patch.id, university_data)
            )
            await uow.commit()
        await on_organization_updated([self._event(result)])
        return result

    async def put(self, university_put: UniversityPutDTO) -> UniversityDTO:
        async with self.uow as uow:
            result = self._to_dto(await self._upsert(university_put))
            await uow.commit()
        await on_organization_updated([self._event(result)])
        return result

    async def search(
        self, filter: UniversityFilterDTO, pagination: PageParamDTO
    ) -> PageDTO[UniversityDTO]:
        async with self.uow:
            items, total = await self.uow.universities.search(
                UniversityFilter.from_dto(filter), pagination
            )
            return PageDTO(
                items=[self._to_dto(item) for item in items],
                pagination=PaginationDTO(
                    page=pagination.page,
                    limit=pagination.limit,
                    total=total,
                ),
            )

    async def delete(self, university_id: UUID) -> None:
        async with self.uow as uow:
            await self._delete(university_id)
            await uow.commit()
        await on_organization_deleted([university_id])
