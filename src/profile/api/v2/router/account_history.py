from profile.api.v2.schema.account_history import AccountLinkChangeRead
from profile.dependency.account import AccountUOWDep
from profile.filter.account_history import AccountLinkChangeFilter
from profile.service.account_history import AccountHistoryService

from fastapi import APIRouter, Depends

from core.dependencies.auth import SuperUserJWTDep
from core.filter.depends import FilterDepends
from core.schema.error import auth_responses
from core.schema.v1.pagination import PageParamV1, PageV1

router = APIRouter(prefix="/account-links", tags=["account-link"])


@router.get("/history", responses={**auth_responses()})
async def get_account_link_history(
    user: SuperUserJWTDep,
    uow: AccountUOWDep,
    filter: AccountLinkChangeFilter = FilterDepends(AccountLinkChangeFilter),
    page_params: PageParamV1 = Depends(PageParamV1),
) -> PageV1[AccountLinkChangeRead]:
    """Who linked, moved or unlinked which account, how and when; newest first.

    `person_id` matches a change that took the person from an account or gave
    it to one.
    """
    return PageV1[AccountLinkChangeRead].from_dto(
        await AccountHistoryService(uow).search(filter.to_dto(), page_params.to_dto())
    )
