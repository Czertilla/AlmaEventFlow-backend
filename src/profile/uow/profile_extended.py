from core.uow.sqlalchemy import UnitOfWork
from profile.repository.profile import ProfileRepo
from profile.uow.person import PersonMixin
from profile.uow.contact import ContactMixin
from profile.uow.passport import PassportMixin


class ProfileExtendedMixin:
    profiles: ProfileRepo


class ProfileExtendedUOW(UnitOfWork, ProfileExtendedMixin, PersonMixin, ContactMixin, PassportMixin): ...