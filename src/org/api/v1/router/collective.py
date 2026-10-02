from logging import getLogger
from uuid import UUID

from fastapi import APIRouter, Depends
from fastapi_filter import FilterDepends

from core.dependencies.auth import SuperUserJWTDep, UserJWTDep
from core.schema.error import auth_responses, entity_not_found_responses
from core.schema.v1.pagination import PageParamV1, PageV1
from org.api.v1.schema.collective import (
    CollectiveCreate,
    CollectivePatch,
    CollectivePatchData,
    CollectivePut,
    CollectivePutData,
    CollectiveRead,
)
from org.dependency.collective import CollectiveUOWDep
from org.filter.collective import CollectiveFilter
from org.service.collective import CollectiveService

router = APIRouter(prefix="/collectives", tags=["collective"])

logger = getLogger(__name__)


@router.get("", responses={**auth_responses()})
async def list_collectives(
    uow: CollectiveUOWDep,
    user: UserJWTDep,
    filter: CollectiveFilter = FilterDepends(CollectiveFilter),
    page_param: PageParamV1 = Depends(PageParamV1),
) -> PageV1[CollectiveRead]:
    return PageV1[CollectiveRead].from_dto_with_page_count(
        await CollectiveService(uow).search(filter.to_dto(), page_param.to_dto())
    )


@router.get(
    "/{collective_id}",
    responses={**auth_responses(), **entity_not_found_responses("collective")},
)
async def get_collective(
    collective_id: UUID, user: UserJWTDep, uow: CollectiveUOWDep
) -> CollectiveRead:
    return CollectiveRead.from_dto(await CollectiveService(uow).read(collective_id))


@router.post("", responses={**auth_responses()})
async def create_collective(
    collective: CollectiveCreate,
    user: SuperUserJWTDep,
    uow: CollectiveUOWDep,
) -> CollectiveRead:
    return CollectiveRead.from_dto(
        await CollectiveService(uow).create(collective.to_dto())
    )


@router.put(
    "/{collective_id}",
    responses={**auth_responses(), **entity_not_found_responses("collective")},
)
async def put_collective(
    collective_id: UUID,
    collective: CollectivePutData,
    user: SuperUserJWTDep,
    uow: CollectiveUOWDep,
) -> CollectiveRead:
    return CollectiveRead.from_dto(
        await CollectiveService(uow).put(
            CollectivePut.model_validate(
                {"id": collective_id, **collective.model_dump()}
            ).to_dto()
        )
    )


@router.patch(
    "/{collective_id}",
    responses={**auth_responses(), **entity_not_found_responses("collective")},
)
async def patch_collective(
    collective_id: UUID,
    collective: CollectivePatchData,
    user: SuperUserJWTDep,
    uow: CollectiveUOWDep,
) -> CollectiveRead:
    return CollectiveRead.from_dto(
        await CollectiveService(uow).patch(
            CollectivePatch.model_validate(
                {"id": collective_id, **collective.model_dump()}
            ).to_dto()
        )
    )


@router.delete(
    "/{collective_id}",
    responses={**auth_responses(), **entity_not_found_responses("collective")},
)
async def delete_collective(
    collective_id: UUID, user: SuperUserJWTDep, uow: CollectiveUOWDep
) -> None:
    await CollectiveService(uow).delete(collective_id)
