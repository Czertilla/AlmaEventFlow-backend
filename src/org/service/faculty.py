from logging import getLogger
from uuid import UUID

from core.schema.message.org import OrganizationData
from core.service.base import BaseService, required_transaction
from org.exc.faculty import FacultyNotExistsException
from org.models.faculty import FacultyORM
from org.models.organization import OrganizationORM
from org.schema.faculty import (
    FacultyCreate,
    FacultyPatch,
    FacultyPut,
    FacultyRead,
)
from org.api.kafka.pub.organization import (
    on_organization_created,
    on_organization_deleted,
    on_organization_updated,
)
from org.uow.faculty import FacultyUOW

logger = getLogger(__name__)


class FacultyService(BaseService[FacultyUOW]):
    @required_transaction
    async def _create(self, faculty_create: FacultyCreate) -> FacultyORM:
        faculty = FacultyORM(**faculty_create.model_dump())
        self.uow.session.add(faculty)
        await self.uow.session.flush()
        return faculty

    @required_transaction
    async def _read(self, faculty_id: UUID) -> FacultyORM | None:
        faculty = await self.uow.faculties.get_by_id(faculty_id)
        if faculty is None:
            raise FacultyNotExistsException()
        return faculty

    @required_transaction
    async def _update(
        self,
        faculty_id: UUID,
        faculty_data: dict,
        *,
        flush: bool = False,
    ) -> FacultyORM:
        organization = await self.uow.session.get(OrganizationORM, faculty_id)
        if organization is None:
            raise FacultyNotExistsException()
        faculty = FacultyORM(**faculty_data, id=faculty_id)

        return await self.uow.session.merge(faculty)

    async def create(self, faculty_create: FacultyCreate) -> FacultyRead:
        async with self.uow as uow:
            result = FacultyRead.model_validate(
                await self._create(faculty_create)
            )
            await uow.commit()
        await on_organization_created(
            OrganizationData(**result.model_dump(), type="faculty")
        )
        return result

    async def read(self, faculty_id: UUID) -> FacultyRead:
        async with self.uow:
            return FacultyRead.model_validate(await self._read(faculty_id))

    async def patch(self, faculty_patch: FacultyPatch) -> FacultyRead:
        async with self.uow as uow:
            faculty_data = faculty_patch.model_dump()
            result = FacultyRead.model_validate(
                await self._update(faculty_data.pop("id"), faculty_data)
            )
            await uow.commit()
        await on_organization_updated(
            OrganizationData(**result.model_dump(), type="faculty")
        )
        return result

    async def put(self, faculty_put: FacultyPut) -> FacultyRead:
        async with self.uow as uow:
            result = FacultyRead.model_validate(
                await self.uow.session.merge(FacultyORM(faculty_put))
            )
            await uow.commit()
        await on_organization_updated(
            OrganizationData(
                OrganizationData(**result.model_dump(), type="faculty")
            )
        )
        return result

    async def delete(self, faculty_id: UUID) -> None:
        async with self.uow as uow:
            await self.uow.faculties.delete_one(faculty_id)
            await uow.commit()
        await on_organization_deleted(faculty_id)
