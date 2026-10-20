from collections.abc import Iterable
from profile.dto.diet import DietDTO
from profile.dto.reference import OrganizationRefDTO
from profile.dto.student import StudentDegreeDTO, StudentGroupDTO
from profile.exc.student import StudentDegreeNotExistsException
from profile.uow.my_profile import MyProfileUOW
from profile.uow.reference import ReferenceUOW
from profile.utils import org
from uuid import UUID

from core.dto.base import dto_from_orm
from core.service.base import BaseService
from core.utils.names import normalize_name


async def ensure_organizations(
    uow: ReferenceUOW | MyProfileUOW, organization_ids: Iterable[UUID | None]
) -> None:
    for organization_id in {i for i in organization_ids if i is not None}:
        async with uow:
            known = await uow.organizations.exists_id(organization_id)
        if known:
            continue
        ref = await org.get_organization(organization_id)
        async with uow:
            await uow.organizations.upsert({"id": ref.id, "type": ref.type})
            await uow.commit()


class ReferenceService(BaseService[ReferenceUOW]):
    async def _project(self, ref: OrganizationRefDTO) -> OrganizationRefDTO:
        async with self.uow:
            await self.uow.organizations.upsert({"id": ref.id, "type": ref.type})
            await self.uow.commit()
        return ref

    async def diet(self, name: str) -> DietDTO:
        name = normalize_name(name)
        async with self.uow:
            found = await self.uow.diets.find_by_name(name)
            if found is None:
                found = await self.uow.diets.add_n_return({"name": name})
                await self.uow.commit()
            return dto_from_orm(found, DietDTO)

    async def degree(self, name: str) -> StudentDegreeDTO:
        name = normalize_name(name)
        async with self.uow:
            found = await self.uow.student_degrees.find_by_name(name)
            if found is None:
                found = await self.uow.student_degrees.add_n_return({"name": name})
                await self.uow.commit()
            return dto_from_orm(found, StudentDegreeDTO)

    async def group(
        self, name: str, degree_id: int, faculty_id: UUID, grade: int
    ) -> StudentGroupDTO:
        name = normalize_name(name)
        await ensure_organizations(self.uow, [faculty_id])
        async with self.uow:
            found = await self.uow.student_groups.find(name, faculty_id)
            if found is None:
                if not await self.uow.student_degrees.exists_id(degree_id):
                    raise StudentDegreeNotExistsException()
                found = await self.uow.student_groups.add_n_return(
                    {
                        "name": name,
                        "degree_id": degree_id,
                        "faculty_id": faculty_id,
                        "grade": grade,
                    }
                )
                await self.uow.commit()
            return dto_from_orm(found, StudentGroupDTO)

    async def university(self, name: str) -> OrganizationRefDTO:
        return await self._project(await org.resolve_university(normalize_name(name)))

    async def faculty(self, name: str, university_id: UUID) -> OrganizationRefDTO:
        ref = await org.resolve_faculty(normalize_name(name), university_id)
        return await self._project(ref)

    async def organization(self, name: str) -> OrganizationRefDTO:
        return await self._project(await org.resolve_organization(normalize_name(name)))
