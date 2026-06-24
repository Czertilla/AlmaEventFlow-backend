from logging import getLogger
from uuid import UUID

from core.schema.message.user import (
    AccountData,
    AccountDelete,
    AccountVerified,
)
from core.service.base import BaseService, required_transaction

from notify.uow.account import AccountUOW

logger = getLogger(__name__)


class AccountEventService(BaseService[AccountUOW]):
    """Maintains the local ``account`` projection from ``user`` events."""

    @required_transaction
    async def _upsert(self, account: AccountData) -> None:
        await self.uow.accounts.upsert(account.model_dump())

    @required_transaction
    async def _delete(self, account_id: UUID) -> None:
        await self.uow.accounts.delete_one(account_id)

    async def create(self, accounts: list[AccountData]) -> None:
        async with self.uow as uow:
            for account in accounts:
                await self._upsert(account)
            await uow.commit()

    async def update(self, accounts: list[AccountData]) -> None:
        async with self.uow as uow:
            for account in accounts:
                await self._upsert(account)
            await uow.commit()

    async def mark_verified(self, accounts: list[AccountVerified]) -> None:
        async with self.uow as uow:
            await uow.accounts.set_verified([account.id for account in accounts])
            await uow.commit()

    async def delete(self, accounts: list[AccountDelete]) -> None:
        async with self.uow as uow:
            for account in accounts:
                await self._delete(account.id)
            await uow.commit()
