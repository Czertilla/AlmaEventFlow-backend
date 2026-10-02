from logging import getLogger
from uuid import UUID

from fastapi import APIRouter, Depends
from fastapi_filter import FilterDepends

from core.dependencies.auth import SuperUserJWTDep, UserJWTDep
from core.schema.error import auth_responses, entity_not_found_responses
from core.schema.v1.pagination import PageParamV1, PageV1
from event.api.v1.schema.link import (
    LinkCreate,
    LinkPatch,
    LinkPatchData,
    LinkPut,
    LinkPutData,
    LinkRead,
)
from event.dependency.link import LinkUOWDep
from event.filter.link import LinkFilter
from event.service.link import LinkService

router = APIRouter(prefix="/links", tags=["link"])

logger = getLogger(__name__)


@router.get("", responses={**auth_responses()})
async def get_links(
    uow: LinkUOWDep,
    user: UserJWTDep,
    filter: LinkFilter = FilterDepends(LinkFilter),
    page_param: PageParamV1 = Depends(PageParamV1),
) -> PageV1[LinkRead]:
    return PageV1[LinkRead].from_dto(
        await LinkService(uow).search(filter.to_dto(), page_param.to_dto())
    )


@router.post("", responses={**auth_responses()})
async def create_link(
    link: LinkCreate, user: SuperUserJWTDep, uow: LinkUOWDep
) -> LinkRead:
    return LinkRead.from_dto(await LinkService(uow).create(link.to_dto()))


@router.get(
    "/{link_id}", responses={**auth_responses(), **entity_not_found_responses("link")}
)
async def get_link(
    link_id: UUID, user: UserJWTDep, uow: LinkUOWDep
) -> LinkRead:
    return LinkRead.from_dto(await LinkService(uow).read(link_id))


@router.put(
    "/{link_id}", responses={**auth_responses(), **entity_not_found_responses("link")}
)
async def put_link(
    link_id: UUID, link: LinkPutData, user: SuperUserJWTDep, uow: LinkUOWDep
) -> LinkRead:
    result = await LinkService(uow).put(
        LinkPut(id=link_id, **link.model_dump()).to_dto()
    )
    return LinkRead.from_dto(result)


@router.patch(
    "/{link_id}", responses={**auth_responses(), **entity_not_found_responses("link")}
)
async def patch_link(
    link_id: UUID, link: LinkPatchData, user: SuperUserJWTDep, uow: LinkUOWDep
) -> LinkRead:
    result = await LinkService(uow).patch(
        LinkPatch(id=link_id, **link.model_dump()).to_dto()
    )
    return LinkRead.from_dto(result)


@router.delete(
    "/{link_id}", responses={**auth_responses(), **entity_not_found_responses("link")}
)
async def delete_link(
    link_id: UUID, user: SuperUserJWTDep, uow: LinkUOWDep
) -> None:
    await LinkService(uow).delete(link_id)
