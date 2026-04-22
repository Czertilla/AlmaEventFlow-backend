from uuid import UUID
from fastapi import APIRouter
from logging import getLogger

from core.dependencies.auth import SuperUserJWTDep, UserJWTDep
from org.dependency.faculty import FacultyUOWDep
from org.schema.faculty import (
    FacultyCreate,
    FacultyPatch,
    FacultyPatchData,
    FacultyPut,
    FacultyPutData,
    FacultyRead,
)
from org.service.faculty import FacultyService

router = APIRouter(prefix="/faculties", tags=["faculty"])

logger = getLogger(__name__)

@router.get("/{faculty_id}")
async def get_faculty(
    faculty_id: UUID, user: UserJWTDep, uow: FacultyUOWDep
) -> FacultyRead:
    return await FacultyService(uow).read(faculty_id)

@router.post("/new")
async def create_faculty(
    faculty: FacultyCreate,
    user: SuperUserJWTDep,
    uow: FacultyUOWDep,
) -> FacultyRead:
    return await FacultyService(uow).create(faculty)

@router.put("/{faculty_id}")
async def put_faculty(
    faculty_id: UUID,
    faculty: FacultyPutData,
    user: SuperUserJWTDep,
    uow: FacultyUOWDep,
) -> FacultyRead:
    return await FacultyService(uow).put(
        FacultyPut(id=faculty_id, **faculty.model_dump())
    )

@router.patch("/{faculty_id}")
async def patch_faculty(
    faculty_id: UUID,
    faculty: FacultyPatchData,
    user: SuperUserJWTDep,
    uow: FacultyUOWDep,
) -> FacultyRead:
    return await FacultyService(uow).patch(
        FacultyPatch(id=faculty_id, **faculty.model_dump())
    )

@router.delete("/{faculty_id}")
async def delete_faculty(
    faculty_id: UUID, user: SuperUserJWTDep, uow: FacultyUOWDep
) -> None:
    await FacultyService(uow).delete(faculty_id)