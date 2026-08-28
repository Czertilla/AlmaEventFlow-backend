from logging import getLogger

from bot.uow.user import UserUOW
from core.schema.message.user import AccountData
from core.service.base import BaseService, required_transaction

logger = getLogger(__name__)


class AccountEventService(BaseService[UserUOW]):
    """Caches ``email``/``is_verified`` from ``user``-service's ``account.*``
    events into the bot's own ``UserORM`` row for that person, so the data is
    already there by the time (if ever) that person links Telegram via
    ``/start`` — an account with no ``person_id`` yet can't be cached here and
    is silently skipped."""

    @required_transaction
    async def _upsert(self, account: AccountData) -> None:
        if account.person_id is None:
            return
        await self.uow.users.upsert(
            {
                "person_id": account.person_id,
                "email": account.email,
                "is_verified": account.is_verified,
            }
        )

    async def sync(self, accounts: list[AccountData]) -> None:
        async with self.uow as uow:
            for account in accounts:
                await self._upsert(account)
            await uow.commit()
