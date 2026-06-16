from logging import getLogger
from uuid import UUID

from core.service.base import BaseService, required_transaction

from profile.exc.student import StudentNotExistsException
from profile.models.student import StudentORM
from profile.schema.student import (
    StudentCreate,
    StudentGroupCreate,
    StudentGroupPatch,
    StudentGroupPut,
    StudentGroupRead,
    StudentPatch,
    StudentPut,
    StudentRead,
    StudentDegreeCreate,
    StudentDegreePatch,
    StudentDegreePut,
    StudentDegreeRead,
)
from profile.uow.student import StudentUOW


logger = getLogger(__name__)


class StudentService(BaseService[StudentUOW]):
    @required_transaction
    async def _create(self, student_create: StudentCreate) -> StudentORM:
        return await self.uow.students.add_n_return(
            data=student_create.model_dump()
        )

    @required_transaction
    async def _read(self, student_id: UUID) -> StudentORM | None:
        student = await self.uow.students.get_by_id(student_id)
        if student is None:
            raise StudentNotExistsException()
        return student

    @required_transaction
    async def _update(
        self, student_id: UUID, student_data: dict, *, flush: bool = False
    ) -> StudentORM:
        student = await self.uow.students.update_one(
            student_id, student_data, flush
        )
        if student is None:
            raise StudentNotExistsException()
        return student

    @required_transaction
    async def _upsert(self, student_put: StudentPut) -> StudentORM:
        return await self.uow.students.upsert(student_put.model_dump())

    @required_transaction
    async def _delete(self, student_id: UUID) -> None:
        await self.uow.students.delete_one(student_id)

    async def create(self, student_create: StudentCreate) -> StudentRead:
        async with self.uow as uow:
            result = StudentRead.model_validate(
                await self._create(student_create)
            )
            await uow.commit()
        return result

    async def read(self, student_id: UUID) -> StudentRead:
        async with self.uow:
            return StudentRead.model_validate(await self._read(student_id))

    async def patch(self, student_patch: StudentPatch) -> StudentRead:
        async with self.uow as uow:
            student_data = student_patch.model_dump()
            result = StudentRead.model_validate(
                await self._update(student_data.pop("id"), student_data)
            )
            await uow.commit()
        return result

    async def put(self, student_put: StudentPut) -> StudentRead:
        async with self.uow as uow:
            result = StudentRead.model_validate(
                await self._upsert(student_put)
            )
            await uow.commit()
        return result

    async def delete(self, student_id: UUID) -> None:
        async with self.uow as uow:
            await self._delete(student_id)
            await uow.commit()


class StudentDegreeService(BaseService[StudentUOW]):
    @required_transaction
    async def _create(self, degree_create: StudentDegreeCreate) -> StudentORM:
        return await self.uow.student_degrees.add_n_return(
            data=degree_create.model_dump()
        )

    @required_transaction
    async def _read(self, degree_id: UUID) -> StudentORM | None:
        degree = await self.uow.student_degrees.get_by_id(degree_id)
        if degree is None:
            raise StudentNotExistsException()
        return degree

    @required_transaction
    async def _update(
        self, degree_id: UUID, degree_data: dict, *, flush: bool = False
    ) -> StudentORM:
        degree = await self.uow.student_degrees.update_one(
            degree_id, degree_data, flush
        )
        if degree is None:
            raise StudentNotExistsException()
        return degree

    @required_transaction
    async def _upsert(self, degree_put: StudentDegreePut) -> StudentORM:
        return await self.uow.student_degrees.upsert(degree_put.model_dump())

    @required_transaction
    async def _delete(self, degree_id: UUID) -> None:
        await self.uow.student_degrees.delete_one(degree_id)

    async def create(self, degree_create: StudentDegreeCreate) -> StudentDegreeRead:
        async with self.uow as uow:
            result = StudentDegreeRead.model_validate(
                await self._create(degree_create)
            )
            await uow.commit()
        return result

    async def read(self, degree_id: UUID) -> StudentDegreeRead:
        async with self.uow:
            return StudentDegreeRead.model_validate(await self._read(degree_id))

    async def patch(self, degree_patch: StudentDegreePatch) -> StudentDegreeRead:
        async with self.uow as uow:
            degree_data = degree_patch.model_dump()
            result = StudentDegreeRead.model_validate(
                await self._update(degree_data.pop("id"), degree_data)
            )
            await uow.commit()
        return result

    async def put(self, degree_put: StudentDegreePut) -> StudentDegreeRead:
        async with self.uow as uow:
            result = StudentDegreeRead.model_validate(
                await self._upsert(degree_put)
            )
            await uow.commit()
        return result

    async def delete(self, degree_id: UUID) -> None:
        async with self.uow as uow:
            await self._delete(degree_id)
            await uow.commit()


class StudentGroupService(BaseService[StudentUOW]):
    @required_transaction
    async def _create(self, group_create: StudentGroupCreate) -> StudentORM:
        return await self.uow.student_groups.add_n_return(
            data=group_create.model_dump()
        )

    @required_transaction
    async def _read(self, group_id: UUID) -> StudentORM | None:
        group = await self.uow.student_groups.get_by_id(group_id)
        if group is None:
            raise StudentNotExistsException()
        return group

    @required_transaction
    async def _update(
        self, group_id: UUID, group_data: dict, *, flush: bool = False
    ) -> StudentORM:
        group = await self.uow.student_groups.update_one(
            group_id, group_data, flush
        )
        if group is None:
            raise StudentNotExistsException()
        return group

    @required_transaction
    async def _upsert(self, group_put: StudentGroupPut) -> StudentORM:
        return await self.uow.student_groups.upsert(group_put.model_dump())

    @required_transaction
    async def _delete(self, group_id: UUID) -> None:
        await self.uow.student_groups.delete_one(group_id)

    async def create(self, group_create: StudentGroupCreate) -> StudentGroupRead:
        async with self.uow as uow:
            result = StudentGroupRead.model_validate(
                await self._create(group_create)
            )
            await uow.commit()
        return result

    async def read(self, group_id: UUID) -> StudentGroupRead:
        async with self.uow:
            return StudentGroupRead.model_validate(await self._read(group_id))

    async def patch(self, group_patch: StudentGroupPatch) -> StudentGroupRead:
        async with self.uow as uow:
            group_data = group_patch.model_dump()
            result = StudentGroupRead.model_validate(
                await self._update(group_data.pop("id"), group_data)
            )
            await uow.commit()
        return result

    async def put(self, group_put: StudentGroupPut) -> StudentGroupRead:
        async with self.uow as uow:
            result = StudentGroupRead.model_validate(
                await self._upsert(group_put)
            )
            await uow.commit()
        return result

    async def delete(self, group_id: UUID) -> None:
        async with self.uow as uow:
            await self._delete(group_id)
            await uow.commit()