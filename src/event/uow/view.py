from core.uow.sqlalchemy import UnitOfWork
from event.repository.view import ViewRepo


class ViewMixin:
    view: ViewRepo


class ViewUOW(UnitOfWork, ViewMixin): ...
