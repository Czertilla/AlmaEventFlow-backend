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
from org.dto.faculty import (
    FacultyCreateDTO,
    FacultyDTO,
    FacultyFilterDTO,
    FacultyPatchDTO,
    FacultyPutDTO,
)
from org.exc.faculty import FacultyNotExistsException
from org.filter.faculty import FacultyFilter
from org.models.faculty import FacultyORM
from org.uow.faculty import FacultyUOW

logger = getLogger(__name__)


class FacultyService(BaseService[FacultyUOW]):
    @staticmethod
    def _to_dto(faculty: FacultyORM) -> FacultyDTO:
        return dto_from_orm(faculty, FacultyDTO)

    @staticmethod
    def _event(faculty: FacultyDTO) -> OrganizationData:
        return OrganizationData(**dto_dict(faculty))

    @required_transaction
    async def _create(self, faculty_create: FacultyCreateDTO) -> FacultyORM:
        faculty = FacultyORM(**dto_dict(faculty_create))
        self.uow.session.add(faculty)
        await self.uow.session.flush()
        return faculty

    @required_transaction
    async def _read(self, faculty_id: UUID) -> FacultyORM:
        faculty = await self.uow.faculties.get_by_id(faculty_id)
        if faculty is None:
            raise FacultyNotExistsException()
        return faculty

    @required_transaction
    async def _update(
        self,
        faculty_id: UUID,
        faculty_data: dict[str, Any],
        *,
        flush: bool = False,
    ) -> FacultyORM:
        # merge() on a transient partial instance would null out unpatched columns
        faculty = await self.uow.faculties.get_by_id(faculty_id)
        if faculty is None:
            raise FacultyNotExistsException()
        for key, value in faculty_data.items():
            setattr(faculty, key, value)
        if flush:
            await self.uow.session.flush()
        return faculty

    @required_transaction
    async def _upsert(self, faculty_put: FacultyPutDTO) -> FacultyORM:
        faculty = await self.uow.faculties.get_by_id(faculty_put.id)
        faculty_data = dto_dict(faculty_put, exclude={"id"})
        if faculty is None:
            faculty = FacultyORM(id=faculty_put.id, **faculty_data)
            self.uow.session.add(faculty)
        else:
            for key, value in faculty_data.items():
                setattr(faculty, key, value)
        await self.uow.session.flush()
        return faculty

    @required_transaction
    async def _delete(self, faculty_id: UUID) -> None:
        await self.uow.faculties.delete_one(faculty_id)

    async def create(self, faculty_create: FacultyCreateDTO) -> FacultyDTO:
        async with self.uow as uow:
            result = self._to_dto(await self._create(faculty_create))
            await uow.commit()
        await on_organization_created([self._event(result)])
        return result

    async def read(self, faculty_id: UUID) -> FacultyDTO:
        async with self.uow:
            return self._to_dto(await self._read(faculty_id))

    async def patch(self, faculty_patch: FacultyPatchDTO) -> FacultyDTO:
        async with self.uow as uow:
            faculty_data = dto_dict(faculty_patch, only_set=True, exclude={"id"})
            result = self._to_dto(await self._update(faculty_patch.id, faculty_data))
            await uow.commit()
        await on_organization_updated([self._event(result)])
        return result

    async def put(self, faculty_put: FacultyPutDTO) -> FacultyDTO:
        async with self.uow as uow:
            result = self._to_dto(await self._upsert(faculty_put))
            await uow.commit()
        await on_organization_updated([self._event(result)])
        return result

    async def search(
        self, filter: FacultyFilterDTO, pagination: PageParamDTO
    ) -> PageDTO[FacultyDTO]:
        async with self.uow:
            items, total = await self.uow.faculties.search(
                FacultyFilter.from_dto(filter), pagination
            )
            return PageDTO(
                items=[self._to_dto(item) for item in items],
                pagination=PaginationDTO(
                    page=pagination.page,
                    limit=pagination.limit,
                    total=total,
                ),
            )

    async def delete(self, faculty_id: UUID) -> None:
        async with self.uow as uow:
            await self._delete(faculty_id)
            await uow.commit()
        await on_organization_deleted([faculty_id])
