from profile.repository.account import PersonAccountRepo
from profile.repository.account_history import PersonAccountHistoryRepo

from core.uow.sqlalchemy import UnitOfWork


class AccountMixin:
    account_links: PersonAccountRepo
    account_history: PersonAccountHistoryRepo


class AccountUOW(UnitOfWork, AccountMixin): ...
