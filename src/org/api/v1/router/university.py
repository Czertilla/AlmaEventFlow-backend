from logging import getLogger
from uuid import UUID

from fastapi import APIRouter, Depends
from fastapi_filter import FilterDepends

from core.dependencies.auth import SuperUserJWTDep, UserJWTDep
from core.schema.error import auth_responses, entity_not_found_responses
from core.schema.v1.pagination import PageParamV1, PageV1
from org.api.v1.schema.university import (
    UniversityCreate,
    UniversityPatch,
    UniversityPatchData,
    UniversityPut,
    UniversityPutData,
    UniversityRead,
)
from org.dependency.university import UniversityUOWDep
from org.filter.university import UniversityFilter
from org.service.university import UniversityService

router = APIRouter(prefix="/universities", tags=["university"])

logger = getLogger(__name__)


@router.get("", responses={**auth_responses()})
async def list_universities(
    uow: UniversityUOWDep,
    user: UserJWTDep,
    filter: UniversityFilter = FilterDepends(UniversityFilter),
    page_param: PageParamV1 = Depends(PageParamV1),
) -> PageV1[UniversityRead]:
    return PageV1[UniversityRead].from_dto_with_page_count(
        await UniversityService(uow).search(filter.to_dto(), page_param.to_dto())
    )


@router.get(
    "/{university_id}",
    responses={**auth_responses(), **entity_not_found_responses("university")},
)
async def get_university(
    university_id: UUID, user: UserJWTDep, uow: UniversityUOWDep
) -> UniversityRead:
    return UniversityRead.from_dto(await UniversityService(uow).read(university_id))


@router.post("", responses={**auth_responses()})
async def create_university(
    university: UniversityCreate,
    user: SuperUserJWTDep,
    uow: UniversityUOWDep,
) -> UniversityRead:
    return UniversityRead.from_dto(
        await UniversityService(uow).create(university.to_dto())
    )


@router.put(
    "/{university_id}",
    responses={**auth_responses(), **entity_not_found_responses("university")},
)
async def put_university(
    university_id: UUID,
    university: UniversityPutData,
    user: SuperUserJWTDep,
    uow: UniversityUOWDep,
) -> UniversityRead:
    return UniversityRead.from_dto(
        await UniversityService(uow).put(
            UniversityPut.model_validate(
                {"id": university_id, **university.model_dump()}
            ).to_dto()
        )
    )


@router.patch(
    "/{university_id}",
    responses={**auth_responses(), **entity_not_found_responses("university")},
)
async def patch_university(
    university_id: UUID,
    university: UniversityPatchData,
    user: SuperUserJWTDep,
    uow: UniversityUOWDep,
) -> UniversityRead:
    return UniversityRead.from_dto(
        await UniversityService(uow).patch(
            UniversityPatch.model_validate(
                {"id": university_id, **university.model_dump(exclude_unset=True)}
            ).to_dto()
        )
    )


@router.delete(
    "/{university_id}",
    responses={**auth_responses(), **entity_not_found_responses("university")},
)
async def delete_university(
    university_id: UUID, user: SuperUserJWTDep, uow: UniversityUOWDep
) -> None:
    await UniversityService(uow).delete(university_id)
