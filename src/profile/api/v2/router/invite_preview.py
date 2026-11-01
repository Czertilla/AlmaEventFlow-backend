from profile.api.v2.schema.invite import InvitePreviewData, InvitePreviewRead
from profile.dependency.person import PersonUOWDep
from profile.service.invite import InviteService

from fastapi import APIRouter

from core.schema.error import ErrorCode, detail_400, detail_404

router = APIRouter(prefix="/invites", tags=["invite"])


@router.post(
    "/preview",
    responses={
        **detail_400(ErrorCode.INVITE_TOKEN_INVALID),
        **detail_404(ErrorCode.INVITE_PERSON_NOT_FOUND),
    },
)
async def preview_invite(
    data: InvitePreviewData, uow: PersonUOWDep
) -> InvitePreviewRead:
    """Whom an invitation is for, read by whoever holds the token.

    `400 INVITE_TOKEN_EXPIRED` for an old token and `400 PERSON_ALREADY_HAS_ACCOUNT`
    when the person has registered already.
    """
    return InvitePreviewRead.from_dto(await InviteService(uow).preview(data.token))
