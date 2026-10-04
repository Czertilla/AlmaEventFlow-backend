from logging import getLogger
from uuid import UUID

from fastapi import APIRouter, Depends

from core.dependencies.auth import SuperUserJWTDep, UserJWTDep
from core.filter.depends import FilterDepends
from core.schema.error import auth_responses, entity_not_found_responses
from core.schema.v1.pagination import PageParamV1, PageV1
from org.api.v1.schema.faculty import (
    FacultyCreate,
    FacultyPatch,
    FacultyPatchData,
    FacultyPut,
    FacultyPutData,
    FacultyRead,
)
from org.dependency.faculty import FacultyUOWDep
from org.filter.faculty import FacultyFilter
from org.service.faculty import FacultyService

router = APIRouter(prefix="/faculties", tags=["faculty"])

logger = getLogger(__name__)


@router.get("", responses={**auth_responses()})
async def list_faculties(
    uow: FacultyUOWDep,
    user: UserJWTDep,
    filter: FacultyFilter = FilterDepends(FacultyFilter),
    page_param: PageParamV1 = Depends(PageParamV1),
) -> PageV1[FacultyRead]:
    return PageV1[FacultyRead].from_dto_with_page_count(
        await FacultyService(uow).search(filter.to_dto(), page_param.to_dto())
    )


@router.get(
    "/{faculty_id}",
    responses={**auth_responses(), **entity_not_found_responses("faculty")},
)
async def get_faculty(
    faculty_id: UUID, user: UserJWTDep, uow: FacultyUOWDep
) -> FacultyRead:
    return FacultyRead.from_dto(await FacultyService(uow).read(faculty_id))


@router.post("", responses={**auth_responses()})
async def create_faculty(
    faculty: FacultyCreate,
    user: SuperUserJWTDep,
    uow: FacultyUOWDep,
) -> FacultyRead:
    return FacultyRead.from_dto(await FacultyService(uow).create(faculty.to_dto()))


@router.put(
    "/{faculty_id}",
    responses={**auth_responses(), **entity_not_found_responses("faculty")},
)
async def put_faculty(
    faculty_id: UUID,
    faculty: FacultyPutData,
    user: SuperUserJWTDep,
    uow: FacultyUOWDep,
) -> FacultyRead:
    return FacultyRead.from_dto(
        await FacultyService(uow).put(
            FacultyPut.model_validate(
                {"id": faculty_id, **faculty.model_dump()}
            ).to_dto()
        )
    )


@router.patch(
    "/{faculty_id}",
    responses={**auth_responses(), **entity_not_found_responses("faculty")},
)
async def patch_faculty(
    faculty_id: UUID,
    faculty: FacultyPatchData,
    user: SuperUserJWTDep,
    uow: FacultyUOWDep,
) -> FacultyRead:
    return FacultyRead.from_dto(
        await FacultyService(uow).patch(
            FacultyPatch.model_validate(
                {"id": faculty_id, **faculty.model_dump()}
            ).to_dto()
        )
    )


@router.delete(
    "/{faculty_id}",
    responses={**auth_responses(), **entity_not_found_responses("faculty")},
)
async def delete_faculty(
    faculty_id: UUID, user: SuperUserJWTDep, uow: FacultyUOWDep
) -> None:
    await FacultyService(uow).delete(faculty_id)
