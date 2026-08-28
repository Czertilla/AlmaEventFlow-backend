from profile.repository.contact import ContactRepo

from core.uow.sqlalchemy import UnitOfWork


class ContactMixin:
    contacts: ContactRepo


class ContactUOW(UnitOfWork, ContactMixin): ...