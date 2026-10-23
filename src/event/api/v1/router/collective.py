from uuid import UUID

from fastapi import APIRouter, Depends

from core.dependencies.auth import SuperUserJWTDep
from core.filter.depends import FilterDepends
from core.schema.error import auth_responses, entity_not_found_responses
from core.schema.v1.pagination import PageParamV1, PageV1
from event.api.v1.schema.collective import (
    EventCollectivePatch,
    EventCollectivePatchData,
    EventCollectiveRead,
)
from event.dependency.collective import CollectiveUOWDep
from event.filter.collective import CollectiveFilter
from event.service.collective import CollectiveService

router = APIRouter(prefix="/collectives", tags=["collective"])


@router.get("", responses={**auth_responses()})
async def get_collectives(
    uow: CollectiveUOWDep,
    user: SuperUserJWTDep,
    filter: CollectiveFilter = FilterDepends(CollectiveFilter),
    page_param: PageParamV1 = Depends(PageParamV1),
) -> PageV1[EventCollectiveRead]:
    return PageV1[EventCollectiveRead].from_dto(
        await CollectiveService(uow).search(filter.to_dto(), page_param.to_dto())
    )


@router.get(
    "/{collective_id}",
    responses={**auth_responses(), **entity_not_found_responses("collective")},
)
async def get_collective(
    collective_id: UUID, user: SuperUserJWTDep, uow: CollectiveUOWDep
) -> EventCollectiveRead:
    return EventCollectiveRead.from_dto(
        await CollectiveService(uow).read(collective_id)
    )


@router.patch(
    "/{collective_id}",
    responses={**auth_responses(), **entity_not_found_responses("collective")},
)
async def patch_collective(
    collective_id: UUID,
    collective: EventCollectivePatchData,
    user: SuperUserJWTDep,
    uow: CollectiveUOWDep,
) -> EventCollectiveRead:
    """Confirms a collective (or takes the confirmation back): only a confirmed one can
    create events, a superuser can regardless."""
    result = await CollectiveService(uow).patch(
        EventCollectivePatch.model_validate(
            {"id": collective_id, **collective.model_dump()}
        ).to_dto()
    )
    return EventCollectiveRead.from_dto(result)
