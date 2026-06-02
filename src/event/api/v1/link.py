from uuid import UUID
from fastapi import APIRouter, Depends
from fastapi_filter import FilterDepends
from logging import getLogger

from core.dependencies.auth import SuperUserJWTDep, UserJWTDep
from core.schema.pagination import SPage, SPageParam
from event.dependency.link import LinkUOWDep
from event.filter.link import LinkFilter
from ...schema.link import (
    LinkCreate,
    LinkPatch,
    LinkPatchData,
    LinkPut,
    LinkPutData,
    LinkRead,
)
from event.service.link import LinkService

router = APIRouter(prefix="/links", tags=["link"])

logger = getLogger(__name__)


@router.get("")
async def get_links(
    uow: LinkUOWDep,
    user: UserJWTDep,
    filter: LinkFilter = FilterDepends(LinkFilter),
    page_param=Depends(SPageParam),
) -> SPage[LinkRead]:
    return await LinkService(uow).search(filter, page_param)


@router.post("")
async def create_link(
    link: LinkCreate, user: SuperUserJWTDep, uow: LinkUOWDep
) -> LinkRead:
    return await LinkService(uow).create(link)


@router.get("/{link_id}")
async def get_link(
    link_id: UUID, user: UserJWTDep, uow: LinkUOWDep
) -> LinkRead:
    return await LinkService(uow).read(link_id)


@router.put("/{link_id}")
async def put_link(
    link_id: UUID, link: LinkPut, user: SuperUserJWTDep, uow: LinkUOWDep
) -> LinkRead:
    return await LinkService(uow).put(
        LinkPutData(**link.model_dump(), id=link_id)
    )


@router.patch("/{link_id}")
async def patch_link(
    link_id: UUID, link: LinkPatch, user: SuperUserJWTDep, uow: LinkUOWDep
) -> LinkRead:
    return await LinkService(uow).patch(
        LinkPatchData(**link.model_dump(), id=link_id)
    )


@router.delete("/{link_id}")
async def delete_link(
    link_id: UUID, user: SuperUserJWTDep, uow: LinkUOWDep
) -> None:
    await LinkService(uow).delete(link_id)
