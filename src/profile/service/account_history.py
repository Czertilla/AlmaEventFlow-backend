from dataclasses import replace
from profile.dto.account_history import (
    AccountLinkChangeDTO,
    AccountLinkChangeFilterDTO,
)
from profile.enum.account import PersonLinkAction
from profile.filter.account_history import AccountLinkChangeFilter
from profile.models.account import PersonAccountHistoryORM
from profile.uow.account import AccountUOW

from core.dto.base import dto_from_orm
from core.dto.pagination import PageDTO, PageParamDTO, PaginationDTO
from core.enum.profile import PersonLinkSource
from core.service.base import BaseService


class AccountHistoryService(BaseService[AccountUOW]):
    @staticmethod
    def _to_dto(change: PersonAccountHistoryORM) -> AccountLinkChangeDTO:
        dto = dto_from_orm(change, AccountLinkChangeDTO)
        return replace(
            dto,
            action=PersonLinkAction(dto.action),
            source=PersonLinkSource(dto.source),
        )

    async def search(
        self,
        filter: AccountLinkChangeFilterDTO,
        page_params: PageParamDTO = PageParamDTO(),
    ) -> PageDTO[AccountLinkChangeDTO]:
        async with self.uow as uow:
            changes, total = await uow.account_history.search(
                AccountLinkChangeFilter.from_dto(filter), page_params
            )
            return PageDTO(
                items=[self._to_dto(change) for change in changes],
                pagination=PaginationDTO(
                    page=page_params.page, limit=page_params.limit, total=total
                ),
            )
