from profile.api.v2.docs import GRANT_APPROVE_ERRORS, GRANT_ERRORS
from profile.api.v2.schema.access_request import IncomingGrantRead
from profile.dependency.access_request import AccessRequestUOWDep
from profile.dependency.viewer import VerifiedViewerDep
from profile.service.grant import Decision, GrantService
from uuid import UUID

from fastapi import APIRouter, Depends

from core.schema.error import auth_responses
from core.schema.v1.pagination import PageParamV1, PageV1

router = APIRouter(prefix="/grants", tags=["grants"])


@router.get("/incoming", responses={**auth_responses()})
async def get_incoming_grants(
    viewer: VerifiedViewerDep,
    uow: AccessRequestUOWDep,
    page_params: PageParamV1 = Depends(PageParamV1),
) -> PageV1[IncomingGrantRead]:
    """Requests for the caller's data: who asks, in which collective, for what,
    why and until when; newest first."""
    return PageV1[IncomingGrantRead].from_dto(
        await GrantService(uow).incoming(viewer, page_params.to_dto())
    )


@router.post("/{grant_id}/approve", responses={**GRANT_APPROVE_ERRORS})
async def approve_grant(
    grant_id: UUID, viewer: VerifiedViewerDep, uow: AccessRequestUOWDep
) -> IncomingGrantRead:
    """Opens the asked fields to the leader until the request expires. Held back
    (`409 GRANT_COOLDOWN`) for a while after the account link changed."""
    return IncomingGrantRead.from_dto(
        await GrantService(uow).decide(grant_id, Decision.APPROVE, viewer)
    )


@router.post("/{grant_id}/decline", responses={**GRANT_ERRORS})
async def decline_grant(
    grant_id: UUID, viewer: VerifiedViewerDep, uow: AccessRequestUOWDep
) -> IncomingGrantRead:
    return IncomingGrantRead.from_dto(
        await GrantService(uow).decide(grant_id, Decision.DECLINE, viewer)
    )


@router.post("/{grant_id}/revoke", responses={**GRANT_ERRORS})
async def revoke_grant(
    grant_id: UUID, viewer: VerifiedViewerDep, uow: AccessRequestUOWDep
) -> IncomingGrantRead:
    """Closes an approved grant for good; a new request is needed to ask again."""
    return IncomingGrantRead.from_dto(
        await GrantService(uow).decide(grant_id, Decision.REVOKE, viewer)
    )
