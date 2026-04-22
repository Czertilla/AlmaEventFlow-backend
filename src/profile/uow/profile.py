from core.uow.sqlalchemy import UnitOfWork
from profile.repository.profile import ProfileRepo
from profile.uow.contact import ContactMixin
from profile.uow.passport import PassportMixin
from profile.uow.person import PersonMixin


class ProfileMixin:
    profiles: ProfileRepo


class ProfileUOW(UnitOfWork, ProfileMixin): ...


class ProfilePassportUOW(UnitOfWork, ProfileMixin, PassportMixin): ...


class ProfileExtendedUOW(
    UnitOfWork, ProfileMixin, PersonMixin, ContactMixin, PassportMixin
): ...
