from logging import getLogger
from profile.dto.person import PersonDTO
from profile.dto.student import (
    StudentCreateDTO,
    StudentDegreeCreateDTO,
    StudentDegreeDTO,
    StudentDegreeFilterDTO,
    StudentDegreePatchDTO,
    StudentDegreePutDTO,
    StudentDTO,
    StudentFilterDTO,
    StudentGroupCreateDTO,
    StudentGroupDTO,
    StudentGroupFilterDTO,
    StudentGroupPatchDTO,
    StudentGroupPutDTO,
    StudentPatchDTO,
    StudentPutDTO,
)
from profile.exc.profile import ProfileNotExistsException
from profile.exc.student import (
    StudentAlreadyExistsException,
    StudentDegreeAlreadyExistsException,
    StudentDegreeInUseException,
    StudentDegreeNotExistsException,
    StudentGroupAlreadyExistsException,
    StudentGroupInUseException,
    StudentGroupNotExistsException,
    StudentNotExistsException,
)
from profile.filter.student import (
    StudentDegreeFilter,
    StudentFilter,
    StudentGroupFilter,
)
from profile.models.student import StudentDegree, StudentGroupORM, StudentORM
from profile.service.profile import profile_to_dto
from profile.service.reference import ensure_organizations
from profile.uow.student import StudentGroupUOW, StudentUOW
from typing import Any
from uuid import UUID

from core.dto.base import dto_dict, dto_from_orm
from core.dto.pagination import PageDTO, PageParamDTO, PaginationDTO
from core.service.base import BaseService, required_transaction
from core.utils.names import normalize_name

logger = getLogger(__name__)


def _group_to_dto(group: StudentGroupORM) -> StudentGroupDTO:
    return dto_from_orm(group, StudentGroupDTO)


class StudentService(BaseService[StudentUOW]):
    @staticmethod
    def _to_dto(student: StudentORM) -> StudentDTO:
        person = student.person
        profile = student.profile
        group = student.group
        return StudentDTO(
            id=student.id,
            student_id=student.student_id,
            faculty_id=student.faculty_id,
            group_id=student.group_id,
            is_budget=student.is_budget,
            is_full=student.is_full,
            is_active=student.is_active,
            created_at=student.created_at,
            edited_at=student.edited_at,
            person=dto_from_orm(person, PersonDTO) if person else None,
            profile=profile_to_dto(profile) if profile else None,
            group=_group_to_dto(group) if group else None,
        )

    @required_transaction
    async def _ensure_profile(self, profile_id: UUID) -> None:
        if not await self.uow.profiles.exists_id(profile_id):
            raise ProfileNotExistsException()

    @required_transaction
    async def _create(self, student_create: StudentCreateDTO) -> UUID:
        await self._ensure_profile(student_create.id)
        if await self.uow.students.exists_id(student_create.id):
            raise StudentAlreadyExistsException()
        await self.uow.students.enroll(dto_dict(student_create))
        return student_create.id

    @required_transaction
    async def _read(self, student_id: UUID) -> StudentORM:
        student = await self.uow.students.get_by_id(
            student_id, self.uow.students.all_options
        )
        if student is None:
            raise StudentNotExistsException()
        return student

    @required_transaction
    async def _update(self, student_id: UUID, student_data: dict[str, Any]) -> UUID:
        if not await self.uow.students.update_enrollment(student_id, student_data):
            raise StudentNotExistsException()
        return student_id

    @required_transaction
    async def _upsert(self, student_put: StudentPutDTO) -> UUID:
        await self._ensure_profile(student_put.id)
        await self.uow.students.enroll_or_update(dto_dict(student_put))
        return student_put.id

    @required_transaction
    async def _delete(self, student_id: UUID) -> None:
        await self.uow.students.unenroll(student_id)

    async def create(self, student_create: StudentCreateDTO) -> StudentDTO:
        async with self.uow as uow:
            created_id = await self._create(student_create)
            result = self._to_dto(await self._read(created_id))
            await uow.commit()
        return result

    async def read(self, student_id: UUID) -> StudentDTO:
        async with self.uow:
            return self._to_dto(await self._read(student_id))

    async def search(
        self,
        filter: StudentFilterDTO,
        page_params: PageParamDTO = PageParamDTO(),
    ) -> PageDTO[StudentDTO]:
        async with self.uow as uow:
            students, total = await uow.students.search(
                StudentFilter.from_dto(filter),
                page_params,
                options=uow.students.all_options,
            )
            return PageDTO(
                items=[self._to_dto(student) for student in students],
                pagination=PaginationDTO(
                    page=page_params.page, limit=page_params.limit, total=total
                ),
            )

    async def patch(self, student_patch: StudentPatchDTO) -> StudentDTO:
        async with self.uow as uow:
            student_data = dto_dict(student_patch, only_set=True, exclude={"id"})
            updated_id = await self._update(student_patch.id, student_data)
            result = self._to_dto(await self._read(updated_id))
            await uow.commit()
        return result

    async def put(self, student_put: StudentPutDTO) -> StudentDTO:
        async with self.uow as uow:
            upserted_id = await self._upsert(student_put)
            result = self._to_dto(await self._read(upserted_id))
            await uow.commit()
        return result

    async def delete(self, student_id: UUID) -> None:
        async with self.uow as uow:
            await self._delete(student_id)
            await uow.commit()


class StudentDegreeService(BaseService[StudentUOW]):
    @staticmethod
    def _to_dto(degree: StudentDegree) -> StudentDegreeDTO:
        return dto_from_orm(degree, StudentDegreeDTO)

    @required_transaction
    async def _ensure_name_free(self, name: str, own_id: int | None = None) -> None:
        found = await self.uow.student_degrees.find_by_name(name)
        if found is not None and found.id != own_id:
            raise StudentDegreeAlreadyExistsException()

    @required_transaction
    async def _create(self, degree_create: StudentDegreeCreateDTO) -> StudentDegree:
        name = normalize_name(degree_create.name)
        await self._ensure_name_free(name)
        return await self.uow.student_degrees.add_n_return(data={"name": name})

    @required_transaction
    async def _read(self, degree_id: int) -> StudentDegree:
        degree = await self.uow.student_degrees.get_by_id(degree_id)
        if degree is None:
            raise StudentDegreeNotExistsException()
        return degree

    @required_transaction
    async def _update(
        self,
        degree_id: int,
        degree_data: dict[str, Any],
        *,
        flush: bool = False,
    ) -> StudentDegree:
        current = await self._read(degree_id)
        data = {k: v for k, v in degree_data.items() if v is not None}
        if "name" in data:
            data["name"] = normalize_name(data["name"])
            await self._ensure_name_free(data["name"], degree_id)
        if not data:
            return current
        degree = await self.uow.student_degrees.update_one(degree_id, data, flush)
        if degree is None:
            raise StudentDegreeNotExistsException()
        return degree

    @required_transaction
    async def _upsert(self, degree_put: StudentDegreePutDTO) -> StudentDegree:
        name = normalize_name(degree_put.name)
        await self._ensure_name_free(name, degree_put.id)
        degree = await self.uow.student_degrees.upsert(
            {"id": degree_put.id, "name": name}
        )
        if degree is None:
            raise StudentDegreeNotExistsException()
        return degree

    @required_transaction
    async def _delete(self, degree_id: int) -> None:
        if await self.uow.student_groups.exists_with_degree(degree_id):
            raise StudentDegreeInUseException()
        await self.uow.student_degrees.delete_one(degree_id)

    async def create(self, degree_create: StudentDegreeCreateDTO) -> StudentDegreeDTO:
        async with self.uow as uow:
            result = self._to_dto(await self._create(degree_create))
            await uow.commit()
        return result

    async def read(self, degree_id: int) -> StudentDegreeDTO:
        async with self.uow:
            return self._to_dto(await self._read(degree_id))

    async def search(
        self,
        filter: StudentDegreeFilterDTO,
        page_params: PageParamDTO = PageParamDTO(),
    ) -> PageDTO[StudentDegreeDTO]:
        async with self.uow as uow:
            degrees, total = await uow.student_degrees.search(
                StudentDegreeFilter.from_dto(filter), page_params
            )
            return PageDTO(
                items=[self._to_dto(degree) for degree in degrees],
                pagination=PaginationDTO(
                    page=page_params.page, limit=page_params.limit, total=total
                ),
            )

    async def patch(self, degree_patch: StudentDegreePatchDTO) -> StudentDegreeDTO:
        async with self.uow as uow:
            degree_data = dto_dict(degree_patch, only_set=True, exclude={"id"})
            result = self._to_dto(await self._update(degree_patch.id, degree_data))
            await uow.commit()
        return result

    async def put(self, degree_put: StudentDegreePutDTO) -> StudentDegreeDTO:
        async with self.uow as uow:
            result = self._to_dto(await self._upsert(degree_put))
            await uow.commit()
        return result

    async def delete(self, degree_id: int) -> None:
        async with self.uow as uow:
            await self._delete(degree_id)
            await uow.commit()


class StudentGroupService(BaseService[StudentGroupUOW]):
    @staticmethod
    def _to_dto(group: StudentGroupORM) -> StudentGroupDTO:
        return _group_to_dto(group)

    @required_transaction
    async def _ensure_degree(self, degree_id: int) -> None:
        if not await self.uow.student_degrees.exists_id(degree_id):
            raise StudentDegreeNotExistsException()

    @required_transaction
    async def _ensure_name_free(
        self, name: str, faculty_id: UUID, own_id: int | None = None
    ) -> None:
        found = await self.uow.student_groups.find(name, faculty_id)
        if found is not None and found.id != own_id:
            raise StudentGroupAlreadyExistsException()

    @required_transaction
    async def _create(self, group_create: StudentGroupCreateDTO) -> StudentGroupORM:
        data = dto_dict(group_create) | {"name": normalize_name(group_create.name)}
        await self._ensure_degree(group_create.degree_id)
        await self._ensure_name_free(data["name"], group_create.faculty_id)
        return await self.uow.student_groups.add_n_return(data=data)

    @required_transaction
    async def _read(self, group_id: int) -> StudentGroupORM:
        group = await self.uow.student_groups.get_by_id(group_id)
        if group is None:
            raise StudentGroupNotExistsException()
        return group

    @required_transaction
    async def _update(
        self,
        group_id: int,
        group_data: dict[str, Any],
        *,
        flush: bool = False,
    ) -> StudentGroupORM:
        current = await self._read(group_id)
        data = {k: v for k, v in group_data.items() if v is not None}
        if "name" in data:
            data["name"] = normalize_name(data["name"])
        if "degree_id" in data:
            await self._ensure_degree(data["degree_id"])
        if "name" in data or "faculty_id" in data:
            await self._ensure_name_free(
                data.get("name", current.name),
                data.get("faculty_id", current.faculty_id),
                group_id,
            )
        if not data:
            return current
        group = await self.uow.student_groups.update_one(group_id, data, flush)
        if group is None:
            raise StudentGroupNotExistsException()
        return group

    @required_transaction
    async def _upsert(self, group_put: StudentGroupPutDTO) -> StudentGroupORM:
        data = dto_dict(group_put) | {"name": normalize_name(group_put.name)}
        await self._ensure_degree(group_put.degree_id)
        await self._ensure_name_free(data["name"], group_put.faculty_id, group_put.id)
        group = await self.uow.student_groups.upsert(data)
        if group is None:
            raise StudentGroupNotExistsException()
        return group

    @required_transaction
    async def _delete(self, group_id: int) -> None:
        if await self.uow.students.exists_in_group(group_id):
            raise StudentGroupInUseException()
        await self.uow.student_groups.delete_one(group_id)

    async def create(self, group_create: StudentGroupCreateDTO) -> StudentGroupDTO:
        await ensure_organizations(self.uow, [group_create.faculty_id])
        async with self.uow as uow:
            result = self._to_dto(await self._create(group_create))
            await uow.commit()
        return result

    async def read(self, group_id: int) -> StudentGroupDTO:
        async with self.uow:
            return self._to_dto(await self._read(group_id))

    async def search(
        self,
        filter: StudentGroupFilterDTO,
        page_params: PageParamDTO = PageParamDTO(),
    ) -> PageDTO[StudentGroupDTO]:
        async with self.uow as uow:
            groups, total = await uow.student_groups.search(
                StudentGroupFilter.from_dto(filter), page_params
            )
            return PageDTO(
                items=[self._to_dto(group) for group in groups],
                pagination=PaginationDTO(
                    page=page_params.page, limit=page_params.limit, total=total
                ),
            )

    async def patch(self, group_patch: StudentGroupPatchDTO) -> StudentGroupDTO:
        group_data = dto_dict(group_patch, only_set=True, exclude={"id"})
        await ensure_organizations(self.uow, [group_data.get("faculty_id")])
        async with self.uow as uow:
            result = self._to_dto(await self._update(group_patch.id, group_data))
            await uow.commit()
        return result

    async def put(self, group_put: StudentGroupPutDTO) -> StudentGroupDTO:
        await ensure_organizations(self.uow, [group_put.faculty_id])
        async with self.uow as uow:
            result = self._to_dto(await self._upsert(group_put))
            await uow.commit()
        return result

    async def delete(self, group_id: int) -> None:
        async with self.uow as uow:
            await self._delete(group_id)
            await uow.commit()
