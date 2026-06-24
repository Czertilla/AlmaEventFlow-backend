from core.uow.sqlalchemy import UnitOfWork
from notify.repository.account import AccountRepo


class AccountMixin:
    accounts: AccountRepo


class AccountUOW(UnitOfWork, AccountMixin): ...
