from logging import getLogger
from uuid import UUID

from core.schema.message.org import OrganizationData
from core.schema.pagination import SPage, SPageParam, SPagination
from core.service.base import BaseService, required_transaction
from org.exc.university import UniversityNotExistsException
from org.filter.university import UniversityFilter
from org.models.university import UniversityORM
from org.models.organization import OrganizationORM
from org.schema.university import (
    UniversityCreate,
    UniversityPatch,
    UniversityPut,
    UniversityRead,
)
from org.api.kafka.pub.organization import (
    on_organization_created,
    on_organization_deleted,
    on_organization_updated,
)
from org.uow.university import UniversityUOW

logger = getLogger(__name__)


class UniversityService(BaseService[UniversityUOW]):
    @required_transaction
    async def _create(
        self, university_create: UniversityCreate
    ) -> UniversityORM:
        university = UniversityORM(**university_create.model_dump())
        self.uow.session.add(university)
        await self.uow.session.flush([university])
        return university

    @required_transaction
    async def _read(self, university_id: UUID) -> UniversityORM | None:
        university = await self.uow.universities.get_by_id(university_id)
        if university is None:
            raise UniversityNotExistsException()
        return university

    @required_transaction
    async def _update(
        self,
        university_id: UUID,
        university_data: dict,
        *,
        flush: bool = False,
    ) -> UniversityORM:
        organization = await self.uow.session.get(
            OrganizationORM, university_id
        )
        if organization is None:
            raise UniversityNotExistsException()
        university = UniversityORM(**university_data, id=university_id)
        return await self.uow.session.merge(university)

    @required_transaction
    async def _upsert(self, university_put: UniversityPut) -> UniversityORM:
        return await self.uow.universities.upsert(university_put.model_dump())

    @required_transaction
    async def _delete(self, university_id: UUID) -> None:
        await self.uow.universities.delete_one(university_id)

    async def create(
        self, university_create: UniversityCreate
    ) -> UniversityRead:
        async with self.uow as uow:
            result = UniversityRead.model_validate(
                await self._create(university_create)
            )
            await uow.commit()
        await on_organization_created(
            [OrganizationData(**result.model_dump(exclude={"type"}), type="university")]
        )
        return result

    async def read(self, university_id: UUID) -> UniversityRead:
        async with self.uow:
            return UniversityRead.model_validate(
                await self._read(university_id)
            )

    async def patch(self, university_patch: UniversityPatch) -> UniversityRead:
        async with self.uow as uow:
            university_data = university_patch.model_dump()
            result = UniversityRead.model_validate(
                await self._update(university_data.pop("id"), university_data)
            )
            await uow.commit()
        await on_organization_updated(
            [OrganizationData(**result.model_dump(exclude={"type"}), type="university")]
        )
        return result

    async def put(self, university_put: UniversityPut) -> UniversityRead:
        async with self.uow as uow:
            result = UniversityRead.model_validate(
                await self._upsert(university_put)
            )
            await uow.commit()
        await on_organization_updated(
            [OrganizationData(**result.model_dump())]
        )
        return result

    async def search(
        self, filter: UniversityFilter, pagination: SPageParam
    ) -> SPage[UniversityRead]:
        async with self.uow:
            items, total = await self.uow.universities.search(
                filter, pagination
            )
            return SPage(
                items=[UniversityRead.model_validate(item) for item in items],
                pagination=SPagination.sql_validate(
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
