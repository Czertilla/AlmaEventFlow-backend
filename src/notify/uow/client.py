from core.uow.sqlalchemy import UnitOfWork
from notify.repository.client import ClientRepo


class ClientMixin:
    clients: ClientRepo


class ClientUOW(UnitOfWork, ClientMixin): ...
