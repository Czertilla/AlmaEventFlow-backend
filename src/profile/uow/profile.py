from profile.repository.profile import ProfileRepo
from profile.uow.contact import ContactMixin
from profile.uow.passport import PassportMixin
from profile.uow.person import PersonMixin

from core.uow.sqlalchemy import UnitOfWork


class ProfileMixin:
    profiles: ProfileRepo


class ProfileUOW(UnitOfWork, ProfileMixin): ...


class ProfilePassportUOW(UnitOfWork, ProfileMixin, PassportMixin): ...


class ProfileExtendedUOW(
    UnitOfWork, ProfileMixin, PersonMixin, ContactMixin, PassportMixin
): ...
