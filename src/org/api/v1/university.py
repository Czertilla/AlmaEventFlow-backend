from uuid import UUID
from fastapi import APIRouter
from logging import getLogger

from core.dependencies.auth import SuperUserJWTDep, UserJWTDep
from org.dependency.university import UniversityUOWDep
from org.schema.university import (
    UniversityCreate,
    UniversityPatch,
    UniversityPatchData,
    UniversityPut,
    UniversityPutData,
    UniversityRead,
)
from org.service.university import UniversityService

router = APIRouter(prefix="/universities", tags=["university"])

logger = getLogger(__name__)

@router.get("/{university_id}")
async def get_university(
    university_id: UUID, user: UserJWTDep, uow: UniversityUOWDep
) -> UniversityRead:
    return await UniversityService(uow).read(university_id)

@router.post("/new")
async def create_university(
    university: UniversityCreate,
    user: SuperUserJWTDep,
    uow: UniversityUOWDep,
) -> UniversityRead:
    return await UniversityService(uow).create(university)

@router.put("/{university_id}")
async def put_university(
    university_id: UUID,
    university: UniversityPutData,
    user: SuperUserJWTDep,
    uow: UniversityUOWDep,
) -> UniversityRead:
    return await UniversityService(uow).put(
        UniversityPut(id=university_id, **university.model_dump())
    )

@router.patch("/{university_id}")
async def patch_university(
    university_id: UUID,
    university: UniversityPatchData,
    user: SuperUserJWTDep,
    uow: UniversityUOWDep,
) -> UniversityRead:
    return await UniversityService(uow).patch(
        UniversityPatch(id=university_id, **university.model_dump())
    )

@router.delete("/{university_id}")
async def delete_university(
    university_id: UUID, user: SuperUserJWTDep, uow: UniversityUOWDep
) -> None:
    await UniversityService(uow).delete(university_id)