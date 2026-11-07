from profile.api.v2.schema.access_log import AccessLogEntryRead
from profile.dependency.access_log import AccessLogUOWDep
from profile.dependency.account import CallerPersonDep
from profile.service.access_log import AccessLogService

from fastapi import APIRouter, Depends

from core.dependencies.auth import UserJWTDep
from core.schema.error import auth_responses
from core.schema.v1.pagination import PageParamV1, PageV1

router = APIRouter(prefix="/access-log", tags=["access-log"])


@router.get("/my", responses={**auth_responses()})
async def get_my_access_log(
    user: UserJWTDep,
    person_id: CallerPersonDep,
    uow: AccessLogUOWDep,
    page_params: PageParamV1 = Depends(PageParamV1),
) -> PageV1[AccessLogEntryRead]:
    """Who opened the caller's sensitive data, or tried to, and when; newest first.
    Empty for an account without a person."""
    return PageV1[AccessLogEntryRead].from_dto(
        await AccessLogService(uow).of_subject(person_id, page_params.to_dto())
    )
