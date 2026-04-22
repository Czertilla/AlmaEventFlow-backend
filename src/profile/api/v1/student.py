from uuid import UUID
from fastapi import APIRouter
from logging import getLogger

from core.dependencies.auth import ActiveUserJWTDep, SuperUserJWTDep, UserJWTDep
from profile.dependency.student import StudentUOWDep
from profile.schema.student import (
    StudentCreate,
    StudentDegreeCreate,
    StudentDegreePatch,
    StudentDegreePatchData,
    StudentDegreePut,
    StudentDegreePutData,
    StudentDegreeRead,
    StudentGroupCreate,
    StudentGroupPatch,
    StudentGroupPatchData,
    StudentGroupPut,
    StudentGroupPutData,
    StudentGroupRead,
    StudentPatch,
    StudentPatchData,
    StudentPut,
    StudentPutData,
    StudentRead,
)
from profile.service.student import (
    StudentDegreeService,
    StudentGroupService,
    StudentService,
)

router = APIRouter(prefix="/students", tags=["student"])

logger = getLogger(__name__)


@router.get("/{student_id}")
async def get_student(
    student_id: UUID, user: ActiveUserJWTDep, uow: StudentUOWDep
) -> StudentRead:
    return await StudentService(uow).read(student_id)


@router.post("/new")
async def create_student(
    student: StudentCreate, user: UserJWTDep, uow: StudentUOWDep
) -> StudentRead:
    return await StudentService(uow).create(student)


@router.put("/{student_id}")
async def put_student(
    student_id: UUID,
    student: StudentPutData,
    user: SuperUserJWTDep,
    uow: StudentUOWDep,
) -> StudentRead:
    return await StudentService(uow).put(
        StudentPut(id=student_id, **student.model_dump())
    )


@router.patch("/{student_id}")
async def patch_student(
    student_id: UUID,
    student: StudentPatchData,
    user: SuperUserJWTDep,
    uow: StudentUOWDep,
) -> StudentRead:
    return await StudentService(uow).patch(
        StudentPatch(id=student_id, **student.model_dump())
    )


@router.delete("/{student_id}")
async def delete_student(
    student_id: UUID, user: SuperUserJWTDep, uow: StudentUOWDep
) -> None:
    await StudentService(uow).delete(student_id)


# Student Degrees Router
degree_router = APIRouter(prefix="/degrees", tags=["student", "degree"])


@degree_router.get("/{degree_id}")
async def get_student_degree(
    degree_id: UUID, user: UserJWTDep, uow: StudentUOWDep
) -> StudentDegreeRead:
    return await StudentDegreeService(uow).read(degree_id)


@degree_router.post("/new")
async def create_student_degree(
    degree: StudentDegreeCreate, user: SuperUserJWTDep, uow: StudentUOWDep
) -> StudentDegreeRead:
    return await StudentDegreeService(uow).create(degree)


@degree_router.put("/{degree_id}")
async def put_student_degree(
    degree_id: UUID,
    degree: StudentDegreePutData,
    user: SuperUserJWTDep,
    uow: StudentUOWDep,
) -> StudentDegreeRead:
    return await StudentDegreeService(uow).put(
        StudentDegreePut(id=degree_id, **degree.model_dump())
    )


@degree_router.patch("/{degree_id}")
async def patch_student_degree(
    degree_id: UUID,
    degree: StudentDegreePatchData,
    user: SuperUserJWTDep,
    uow: StudentUOWDep,
) -> StudentDegreeRead:
    return await StudentDegreeService(uow).patch(
        StudentDegreePatch(id=degree_id, **degree.model_dump())
    )


@degree_router.delete("/{degree_id}")
async def delete_student_degree(
    degree_id: UUID, user: SuperUserJWTDep, uow: StudentUOWDep
) -> None:
    await StudentDegreeService(uow).delete(degree_id)


# Student Groups Router
group_router = APIRouter(prefix="/groups", tags=["student", "group"])


@group_router.get("/{group_id}")
async def get_student_group(
    group_id: UUID, user: UserJWTDep, uow: StudentUOWDep
) -> StudentGroupRead:
    return await StudentGroupService(uow).read(group_id)


@group_router.post("/new")
async def create_student_group(
    group: StudentGroupCreate, user: SuperUserJWTDep, uow: StudentUOWDep
) -> StudentGroupRead:
    return await StudentGroupService(uow).create(group)


@group_router.put("/{group_id}")
async def put_student_group(
    group_id: UUID,
    group: StudentGroupPutData,
    user: SuperUserJWTDep,
    uow: StudentUOWDep,
) -> StudentGroupRead:
    return await StudentGroupService(uow).put(
        StudentGroupPut(id=group_id, **group.model_dump())
    )


@group_router.patch("/{group_id}")
async def patch_student_group(
    group_id: UUID,
    group: StudentGroupPatchData,
    user: SuperUserJWTDep,
    uow: StudentUOWDep,
) -> StudentGroupRead:
    return await StudentGroupService(uow).patch(
        StudentGroupPatch(id=group_id, **group.model_dump())
    )


@group_router.delete("/{group_id}")
async def delete_student_group(
    group_id: UUID, user: SuperUserJWTDep, uow: StudentUOWDep
) -> None:
    await StudentGroupService(uow).delete(group_id)


# Include sub-routers
router.include_router(degree_router)
router.include_router(group_router)
