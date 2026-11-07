from profile.api.v2.docs import (
    ACCESS_EXPORT_ERRORS,
    ACCESS_REQUEST_CREATE_ERRORS,
    ACCESS_REQUEST_ERRORS,
)
from profile.api.v2.schema.access_log import AccessFieldRead
from profile.api.v2.schema.access_request import (
    AccessExportCreate,
    AccessExportRead,
    AccessRequestCreate,
    AccessRequestRead,
)
from profile.dependency.access_request import (
    AccessRequestUOWDep,
    ExportLimitDep,
    RequestLimitDep,
)
from profile.dependency.viewer import VerifiedViewerDep
from profile.dto.access_request import AccessExportCreateDTO
from profile.service.access_request import AccessRequestService
from uuid import UUID

from fastapi import APIRouter, Depends, Response, status

from core.dependencies.auth import UserJWTDep
from core.schema.error import auth_responses
from core.schema.v1.pagination import PageParamV1, PageV1

router = APIRouter(prefix="/access-requests", tags=["access-requests"])


@router.get("/fields", responses={**auth_responses()})
async def get_access_fields(user: UserJWTDep) -> list[AccessFieldRead]:
    """The fields a leader may ask the members of a collective for."""
    return [
        AccessFieldRead.model_validate(field, from_attributes=True)
        for field in AccessRequestService.fields()
    ]


@router.post(
    "",
    status_code=status.HTTP_201_CREATED,
    responses={**ACCESS_REQUEST_CREATE_ERRORS},
)
async def create_access_request(
    data: AccessRequestCreate,
    viewer: VerifiedViewerDep,
    limit: RequestLimitDep,
    uow: AccessRequestUOWDep,
) -> AccessRequestRead:
    """The leader of a confirmed collective asks its active members for fields, with
    a comment that says why. Every member gets a pending grant and a notice; the
    request, its fields, comment and term never change."""
    return AccessRequestRead.from_dto(
        await AccessRequestService(uow).create(data.to_dto(), viewer)
    )


@router.get("", responses={**auth_responses()})
async def get_my_access_requests(
    viewer: VerifiedViewerDep,
    uow: AccessRequestUOWDep,
    collective_id: UUID | None = None,
    page_params: PageParamV1 = Depends(PageParamV1),
) -> PageV1[AccessRequestRead]:
    """The caller's own requests, newest first."""
    return PageV1[AccessRequestRead].from_dto(
        await AccessRequestService(uow).mine(
            viewer, collective_id, page_params.to_dto()
        )
    )


@router.get("/{request_id:uuid}", responses={**ACCESS_REQUEST_ERRORS})
async def get_access_request(
    request_id: UUID, viewer: VerifiedViewerDep, uow: AccessRequestUOWDep
) -> AccessRequestRead:
    """How each member answered; no data. Only for the one who asked."""
    return AccessRequestRead.from_dto(
        await AccessRequestService(uow).read(request_id, viewer)
    )


@router.post("/{request_id:uuid}/export", responses={**ACCESS_EXPORT_ERRORS})
async def export_access_request(
    request_id: UUID,
    response: Response,
    viewer: VerifiedViewerDep,
    limit: ExportLimitDep,
    uow: AccessRequestUOWDep,
    data: AccessExportCreate | None = None,
) -> AccessExportRead:
    """The fields of the members whose grant is active, for the leader who asked
    while they still lead the collective and the members still belong to it. The
    rest are listed in `skipped`. Each export is journaled and told to every member
    it covers."""
    exported = await AccessRequestService(uow).export(
        request_id, data.to_dto() if data else AccessExportCreateDTO(), viewer
    )
    response.headers["Cache-Control"] = "no-store"
    return AccessExportRead.from_dto(exported)
