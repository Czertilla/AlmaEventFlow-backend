from core.uow.sqlalchemy import UnitOfWork
from profile.repository.contact import ContactRepo


class ContactMixin:
    contacts: ContactRepo


class ContactUOW(UnitOfWork, ContactMixin): ...